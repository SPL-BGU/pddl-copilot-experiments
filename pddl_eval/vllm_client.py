"""vLLM OpenAI-compatible client adapter that mimics ollama.AsyncClient.

Smoke-probe scaffold (2026-05-09) — see development/CHANGELOG.md. The harness
in pddl_eval/{chat,runner,scoring}.py reads Ollama-shaped response dicts
(message.tool_calls with dict-form arguments, message.thinking, top-level
prompt_eval_count / eval_count / done_reason / total_duration). vLLM speaks
OpenAI's chat-completions shape (string-form tool_call arguments,
finish_reason, usage.prompt_tokens, optional reasoning_content). This module
adapts the wire formats so the existing chat loop works unchanged.

Wire-format adaptations:
  * tool_calls[].function.arguments: JSON string  ↔  dict
  * message.reasoning_content (--reasoning-parser qwen3) → message.thinking
  * choice.finish_reason → done_reason ("stop" / "length" / "tool_calls")
  * usage.{prompt,completion}_tokens → prompt_eval_count / eval_count
  * total_duration / eval_duration synthesised from wallclock perf_counter
  * Multi-turn tool replay: assistant tool_calls get synthetic call_ids, then
    consecutive role=tool messages reuse them in FIFO order so vLLM's
    OpenAI server accepts the multi-turn replay.

Knobs translated:
  * options.temperature       → temperature
  * options.num_predict       → max_tokens
  * options.num_ctx           → ignored (server-side via --max-model-len)
  * keep_alive                → ignored (server-side via TTL or none)
  * think (qwen3 thinking)    → extra_body.chat_template_kwargs.enable_thinking
  * format=<schema dict>      → extra_body.guided_json
  * format="json"             → response_format={"type": "json_object"}

Streaming is forced off — tracks vLLM/Qwen3 hermes streaming bug
vllm-project/vllm#31871 (May 2026) where partial tool_call XML can be
mis-extracted on token boundaries. The harness never reads streamed deltas
either, so non-streaming is the safe default.

Context-overflow handling: vLLM rejects prompt_tokens + max_tokens >
max_model_len with HTTP 400 BadRequestError, where Ollama silently
truncates or returns done_reason="length". chat() catches the specific
overflow body, clips max_tokens to the remaining budget, and retries —
restoring response-shape parity with the Ollama corpus. The degenerate
prompt ≥ max_model_len case returns a synthetic length-truncation
response with empty content (see `_synthesize_overflow_response`).
"""

import json
import re
import time

from openai import AsyncOpenAI, BadRequestError


_DEFAULT_BASE_URL = "http://localhost:8000"

# Match vLLM's context-overflow rejection so we can retry with a clipped
# max_tokens instead of bubbling a BadRequestError up as an `exception`
# trial. Example body:
#   "This model's maximum context length is 16384 tokens. However, you
#    requested 8192 output tokens and your prompt contains at least 8193
#    input tokens, for a total of at least 16385 tokens."
# Group 1 = max_model_len; group 2 = prompt_tokens reported by the server.
_CTX_OVERFLOW_RE = re.compile(
    r"maximum context length is (\d+) tokens.*?"
    r"prompt contains at least (\d+) input tokens",
    re.DOTALL,
)
# Slack between (max_model_len − prompt_tokens) and the clipped max_tokens
# we re-send. Guards against rare 1-token drift between the server-side
# tokenizer count and the count it used when computing the budget. 8
# covers tokenizer-version skew across vllm-openai:latest refreshes; the
# observed drift is ±1 token, so this is ~4σ of headroom for ~0 cost.
_CTX_RETRY_SAFETY = 8


class VLLMOllamaClient:
    """Async client exposing ollama.AsyncClient.chat() / aclose() shape."""

    def __init__(self, host: str | None = None):
        base_url = (host or _DEFAULT_BASE_URL).rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = base_url + "/v1"
        # api_key is required by the openai client but vLLM's OpenAI server
        # accepts any value when auth isn't configured.
        self._client = AsyncOpenAI(base_url=base_url, api_key="EMPTY")

    async def chat(
        self,
        model: str,
        messages: list,
        tools: list | None = None,
        options: dict | None = None,
        keep_alive: str | None = None,  # noqa: ARG002 — server-side concept
        think: bool | None = None,
        format: dict | str | None = None,
    ) -> dict:
        oa_messages = _to_openai_messages(messages)

        kwargs: dict = {
            "model": model,
            "messages": oa_messages,
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        opts = options or {}
        if "temperature" in opts:
            kwargs["temperature"] = opts["temperature"]
        if "num_predict" in opts:
            kwargs["max_tokens"] = opts["num_predict"]
        # num_ctx is fixed server-side via --max-model-len; drop silently.

        extra_body: dict = {}
        if think is not None:
            extra_body["chat_template_kwargs"] = {"enable_thinking": bool(think)}
        if isinstance(format, dict):
            extra_body["guided_json"] = format
        elif format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        if extra_body:
            kwargs["extra_body"] = extra_body

        t0 = time.perf_counter_ns()
        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            # vLLM strictly enforces prompt_tokens + max_tokens ≤ max_model_len
            # and rejects with HTTP 400. Ollama silently truncates / returns
            # done_reason="length" on the same overflow. To keep response-shape
            # parity across backends, catch the specific context-overflow body,
            # clip max_tokens to the remaining headroom, and retry.
            parsed = _parse_ctx_overflow(e)
            if parsed is None:
                raise
            max_ctx, prompt_tokens = parsed
            new_max = max_ctx - prompt_tokens - _CTX_RETRY_SAFETY
            if new_max <= 0:
                # Prompt alone consumes (or exceeds) max_model_len — no output
                # budget to negotiate. Surface as a length-truncation response
                # with empty content; the harness already buckets done_reason
                # ="length" as truncation, matching how Ollama would treat a
                # context window fully consumed by the prompt.
                wall_ns = time.perf_counter_ns() - t0
                return _synthesize_overflow_response(prompt_tokens, wall_ns)
            kwargs["max_tokens"] = new_max
            resp = await self._client.chat.completions.create(**kwargs)
        wall_ns = time.perf_counter_ns() - t0
        return _to_ollama_response(resp, wall_ns)

    async def aclose(self) -> None:
        await self._client.close()

    # ollama.AsyncClient also exposes a sync close() alias on some builds —
    # run_experiment.py guards getattr(client, "aclose", None) or
    # getattr(client, "close", None), so providing aclose alone suffices.


def _to_openai_messages(messages: list) -> list:
    """Translate harness-shape messages into OpenAI chat-completions shape.

    Synthetic tool_call_ids are minted per assistant turn so subsequent
    role=tool messages (which the harness emits without an id) can attach to
    the matching call by FIFO order. This mirrors how the harness's tool loop
    appends tool results immediately after the assistant turn that produced
    the calls — a queue-style match is sufficient.
    """
    out: list = []
    pending_ids: list[str] = []
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            new_calls = []
            pending_ids = []
            for i, tc in enumerate(m["tool_calls"]):
                fn = tc.get("function") or {}
                args = fn.get("arguments", {})
                args_str = args if isinstance(args, str) else json.dumps(args)
                tcid = tc.get("id") or f"call_{len(out)}_{i}"
                pending_ids.append(tcid)
                new_calls.append({
                    "id": tcid,
                    "type": "function",
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": args_str,
                    },
                })
            out.append({
                "role": "assistant",
                "content": m.get("content") or "",
                "tool_calls": new_calls,
            })
        elif role == "tool":
            tcid = m.get("tool_call_id") or (
                pending_ids.pop(0) if pending_ids else "call_unknown"
            )
            out.append({
                "role": "tool",
                "tool_call_id": tcid,
                "content": m.get("content", ""),
            })
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def _to_ollama_response(resp, wall_ns: int) -> dict:
    """Translate an OpenAI ChatCompletion into the dict shape the harness reads."""
    choice = resp.choices[0]
    msg = choice.message

    tool_calls_out: list = []
    if getattr(msg, "tool_calls", None):
        for tc in msg.tool_calls:
            args_str = tc.function.arguments or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except (ValueError, TypeError):
                # Surface unparseable args verbatim so scoring's tool-error
                # path catches it instead of pretending the call succeeded.
                args_dict = {"_raw_arguments": args_str}
            tool_calls_out.append({
                "function": {
                    "name": tc.function.name,
                    "arguments": args_dict,
                },
            })

    # `--reasoning-parser qwen3` populates message.reasoning_content; without
    # it, Qwen3's <think>…</think> remains inline in content and scoring's
    # extract_* fallback handles the inline form.
    thinking = getattr(msg, "reasoning_content", None) or ""

    out_msg: dict = {
        "role": "assistant",
        "content": msg.content or "",
        "thinking": thinking,
    }
    if tool_calls_out:
        out_msg["tool_calls"] = tool_calls_out

    usage = getattr(resp, "usage", None)
    prompt_tok = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    completion_tok = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0

    return {
        "message": out_msg,
        # OpenAI finish_reason values: "stop", "length", "tool_calls",
        # "content_filter". The harness only branches on "length" (truncation
        # signal) and treats anything else as natural stop.
        "done_reason": choice.finish_reason or "",
        "prompt_eval_count": prompt_tok,
        "eval_count": completion_tok,
        # vLLM doesn't expose prompt-vs-decode timing splits via the OpenAI
        # endpoint. Synthesising both from wallclock loses the ability to
        # compute pure decode tok/s downstream — analyzers that derive it
        # should clamp to (eval_count / wall_s) on this backend.
        "total_duration": int(wall_ns),
        "eval_duration": int(wall_ns),
    }


def _parse_ctx_overflow(err: BadRequestError) -> tuple[int, int] | None:
    """Return (max_model_len, prompt_tokens) if `err` is vLLM's context-overflow
    rejection, else None so the caller re-raises unrelated 400s untouched."""
    m = _CTX_OVERFLOW_RE.search(str(err))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _synthesize_overflow_response(prompt_tokens: int, wall_ns: int) -> dict:
    """Ollama-shaped response for the degenerate prompt ≥ max_model_len case.

    Same shape as `_to_ollama_response` with empty content and
    done_reason="length". Mirrors Ollama's behaviour when num_ctx is fully
    consumed by the prompt — the trial completes but the model produces no
    output, so grading sees a truncation rather than an exception."""
    return {
        "message": {"role": "assistant", "content": "", "thinking": ""},
        "done_reason": "length",
        "prompt_eval_count": int(prompt_tokens),
        "eval_count": 0,
        "total_duration": int(wall_ns),
        "eval_duration": int(wall_ns),
    }
