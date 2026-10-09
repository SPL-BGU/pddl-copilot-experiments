"""vLLM client that exposes the wire shape pddl_eval.chat consumes.

The harness in pddl_eval/{chat,runner,scoring}.py reads response dicts with
dict-form tool_call arguments, message.thinking, and top-level
prompt_eval_count / eval_count / done_reason / total_duration. vLLM speaks
OpenAI's chat-completions shape (string-form tool_call arguments,
finish_reason, usage.prompt_tokens, optional reasoning_content). This module
adapts the wire formats so the existing chat loop works unchanged.

Historical: the field names (prompt_eval_count, done_reason, …) are
inherited from the Ollama backend that was retired in 2026-05; they are the
internal contract chat.py was built around, kept stable for corpus
comparability.

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
  * stop=[...]                → stop (OpenAI standard sampling param)
  * vllm_extra={...}          → merged into extra_body verbatim. Carries
    vLLM-only request fields the decoupled-budget think path needs:
    continue_final_message / add_generation_prompt (2-call continuation)
    and include_stop_str_in_output. See chat_without_tools_decoupled.

Streaming is forced off — tracks vLLM/Qwen3 hermes streaming bug
vllm-project/vllm#31871 (May 2026) where partial tool_call XML can be
mis-extracted on token boundaries. The harness never reads streamed deltas
either, so non-streaming is the safe default.

Context-overflow handling: vLLM rejects prompt_tokens + max_tokens >
max_model_len with HTTP 400 BadRequestError. chat() catches the specific
overflow body, MEASURES the real prompt size with a 1-token request, clips
max_tokens to the real remaining room, and retries (see
`_retry_after_ctx_overflow`). The first request is always sent with the
caller's full allowance, so a trial that fits is unaffected. A clipped
response carries `num_predict_requested` / `num_predict_clipped_to`. Only
the degenerate case where the prompt alone leaves no room returns a
synthetic length-truncation response with empty content (see
`_synthesize_overflow_response`, flagged `ctx_overflow_no_room`),
preserving the existing chat.py classifier for `done_reason="length"`
truncation.
"""

import json
import re
import time

from openai import AsyncOpenAI, BadRequestError


_DEFAULT_BASE_URL = "http://localhost:8000"

# Match vLLM's context-overflow rejection so we can retry with a clipped
# max_tokens instead of bubbling a BadRequestError up as an `exception`
# trial. Two body shapes observed in the wild:
#   Old (pre-mid-2026):
#     "prompt contains at least 8193 input tokens"
#   New (current vLLM):
#     "your prompt contains 407867 characters (more than 317440 characters,
#      which is the upper bound for 10240 input tokens)"
# Group 1 = max_model_len; group 2 = prompt_tokens reported by the server.
#
# Drift history (PR-#66 contamfix, 2026-05-20):
#   * The single-quantifier regex `prompt contains at least N` silently
#     missed the new format. Every overflow bubbled up as `FR_EXCEPTION`
#     with `tokens={}` instead of being retry-clipped or synthesized as a
#     length-truncated response. The audit found 24 600 such rows across
#     the corpus. The `(?:at least|upper bound for)` alternation below
#     matches both shapes; regression test in tests/test_vllm_client.py.
_CTX_OVERFLOW_RE = re.compile(
    r"maximum context length is (\d+) tokens.*?"
    r"(?:at least|upper bound for) (\d+) input tokens",
    re.DOTALL,
)
# The prompt-token count in vLLM's 400 body is a LOWER BOUND, not a
# measurement: "your prompt contains at least N input tokens" is derived as
# N = max_model_len − max_tokens + 1, i.e. "one more than what would have
# fit next to the allowance you asked for". It says nothing about how big
# the prompt really is.
#
# History of misreading it (attempt-1 reported prompt → attempt-2 reported):
#   * 17478753 sweep (sweep-3): read as a "+9 drift"; safety = 32.
#   * sweep4-cluster-20260519: 8193 → 8226 on solve, 10241 → 10274 on
#     validate-style, read as a "+33 template drift"; safety raised to 128
#     and a second retry added. +33 is exactly safety(32) + 1: the server
#     was re-deriving N from the clipped max_tokens we had just sent.
#   * 2026-10-02 (development/reanalysis_transcripts.md §3.3): with
#     new_max = max_ctx − N − 128, each retry lowered max_tokens by only
#     129, so the two retries covered prompts within 258 tokens of the
#     limit and nothing else. In the sweep5v2 headline tool arms 1,987
#     trials had their FINAL turn (conversation + tool result) refused this
#     way and were recorded as an empty answer with done_reason="length",
#     the give-up prompt count being exactly 8193+258 = 8451 (solve) or
#     10241+258 = 10499 (validate_*), although the model had thousands of
#     tokens of room.
#
# The fix measures instead of guessing: after the first overflow, the same
# request is re-sent with max_tokens=1. Its `usage.prompt_tokens` is the
# true prompt size under the identical chat template / tools / template
# kwargs (no dependence on a separate tokenize endpoint agreeing with the
# chat endpoint), and the real request is then sent with max_tokens =
# max_model_len − prompt_tokens. With --enable-prefix-caching the probe's
# prompt processing is reused by that request.
#
# If the server rejects that exact clip, small step-downs come before any
# halving (see `_clip_candidates`).
#
# Fallback when the probe returns no usage: start from the old first clip
# (lower bound + this safety margin — right when the prompt really is
# within the margin of the limit) and halve until a request fits.
_CTX_RETRY_SAFETY = 128
# Smallest max_tokens worth sending. Below this the prompt alone fills the
# window and the turn gets the synthetic empty length-truncation response.
_CTX_MIN_MAX_TOKENS = 1
# Small step-downs tried (in this order, each relative to the measured room)
# when the server rejects max_tokens = max_model_len − measured prompt. They
# absorb an off-by-a-few disagreement between usage.prompt_tokens and the
# server's own pre-flight count at a cost of at most 64 tokens of room,
# instead of jumping straight to half.
_CTX_CLIP_STEP_DOWNS = (1, 8, 64)


def _clip_candidates(base: int, fine: bool) -> list[int]:
    """max_tokens values to try, in order, after a context overflow.

    `base` is the first clip. With `fine` (the prompt was measured) the next
    tries are base−1, base−8, base−64; after that the last value tried is
    halved repeatedly. Values below `_CTX_MIN_MAX_TOKENS` are dropped, so an
    empty list means there is no room at all. Bounded: at most
    3 + log2(max_model_len) entries.
    """
    out: list[int] = []
    if base >= _CTX_MIN_MAX_TOKENS:
        out.append(base)
    last = base
    if fine:
        for step in _CTX_CLIP_STEP_DOWNS:
            if base - step >= _CTX_MIN_MAX_TOKENS:
                out.append(base - step)
                last = base - step
    last //= 2
    while last >= _CTX_MIN_MAX_TOKENS:
        out.append(last)
        last //= 2
    return out


class VLLMClient:
    """Async vLLM client exposing chat() / aclose()."""

    def __init__(self, base_url: str | None = None):
        base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
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
        stop: list[str] | None = None,
        vllm_extra: dict | None = None,
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
        # vLLM-only request fields (continue_final_message, add_generation_prompt,
        # include_stop_str_in_output). Merged last so callers can override the
        # think/format defaults above when a 2-call continuation needs to.
        if vllm_extra:
            extra_body.update(vllm_extra)
        if extra_body:
            kwargs["extra_body"] = extra_body
        # `stop` is a standard OpenAI sampling param (top-level, not extra_body).
        # vLLM excludes the matched stop string from the output unless
        # include_stop_str_in_output=True is passed via vllm_extra.
        if stop:
            kwargs["stop"] = stop

        # vLLM strictly enforces prompt_tokens + max_tokens ≤ max_model_len
        # and rejects with HTTP 400. The first request always carries the
        # caller's full allowance; only when it is rejected for context
        # overflow do we enter the measure-and-clip path.
        t0 = time.perf_counter_ns()
        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            parsed = _parse_ctx_overflow(e)
            if parsed is None:
                raise
            return await self._retry_after_ctx_overflow(kwargs, parsed, t0)
        wall_ns = time.perf_counter_ns() - t0
        return _to_ollama_response(resp, wall_ns)

    async def _retry_after_ctx_overflow(
        self, kwargs: dict, parsed: tuple[int, int], t0: int,
    ) -> dict:
        """Re-send a context-overflow-rejected request with max_tokens clipped
        to the real remaining room.

        `parsed` is (max_model_len, lower-bound prompt count) from the 400
        body. Returns the model's real response annotated with
        `num_predict_requested` / `num_predict_clipped_to`, or the synthetic
        empty length-truncation response when the prompt alone leaves no
        room. Non-overflow 400s raised along the way propagate unchanged.
        """
        max_ctx, reported_prompt = parsed
        requested = kwargs.get("max_tokens")

        # Step 1 — measure. A 1-token completion of the identical request
        # reports the true prompt size in usage.prompt_tokens. If even that
        # is rejected, the prompt alone fills the window: genuine overflow.
        try:
            probe = await self._client.chat.completions.create(
                **{**kwargs, "max_tokens": _CTX_MIN_MAX_TOKENS}
            )
        except BadRequestError as e:
            probe_parsed = _parse_ctx_overflow(e)
            if probe_parsed is None:
                raise
            wall_ns = time.perf_counter_ns() - t0
            return _synthesize_overflow_response(probe_parsed[1], wall_ns)
        usage = getattr(probe, "usage", None)
        measured_prompt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0

        # Step 2 — clip to the measured room and re-send. If the measured
        # clip is itself rejected (e.g. the server's own check counts a token
        # or a few more than usage.prompt_tokens reports), step down by small
        # amounts first so the model keeps essentially all of its room;
        # halving is the last resort. Without a measurement the small steps
        # are meaningless against a lower bound, so that path halves directly.
        if measured_prompt > 0:
            candidates = _clip_candidates(max_ctx - measured_prompt, fine=True)
        else:
            candidates = _clip_candidates(
                max_ctx - reported_prompt - _CTX_RETRY_SAFETY, fine=False
            )
        for candidate in candidates:
            try:
                resp = await self._client.chat.completions.create(
                    **{**kwargs, "max_tokens": candidate}
                )
            except BadRequestError as e:
                retry_parsed = _parse_ctx_overflow(e)
                if retry_parsed is None:
                    raise
                reported_prompt = retry_parsed[1]
                continue
            wall_ns = time.perf_counter_ns() - t0
            out = _to_ollama_response(resp, wall_ns)
            # Present ONLY on clipped turns, so readers of unclipped
            # responses (and of every pre-2026-10-02 corpus) see no change.
            # `num_predict_measured_prompt` is the probe's measurement (None
            # when the probe carried no usage), so analysis can check
            # prompt + clip against the window and see how far below it a
            # stepped-down clip landed.
            out["num_predict_requested"] = requested
            out["num_predict_clipped_to"] = candidate
            out["num_predict_measured_prompt"] = measured_prompt or None
            return out

        wall_ns = time.perf_counter_ns() - t0
        return _synthesize_overflow_response(
            measured_prompt or reported_prompt, wall_ns
        )

    async def aclose(self) -> None:
        await self._client.close()


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
    output, so grading sees a truncation rather than an exception.
    `prompt_tokens` is the measured prompt size when the probe got that far,
    else the server's lower bound. `ctx_overflow_no_room` marks the turn as
    never generated (as opposed to a model that wrote until its cap) so
    analysis can count these directly."""
    return {
        "message": {"role": "assistant", "content": "", "thinking": ""},
        "done_reason": "length",
        "prompt_eval_count": int(prompt_tokens),
        "eval_count": 0,
        "total_duration": int(wall_ns),
        "eval_duration": int(wall_ns),
        "ctx_overflow_no_room": True,
    }
