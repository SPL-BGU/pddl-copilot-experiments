"""PlanBench engine adapter for the pddl-copilot model fleet.

Engine name format: ``pddl_copilot__<backend>__<model>``
  - backend: ``ollama`` | ``vllm`` | ``vllm-tools``
  - model:   the model tag, e.g. ``qwen3:0.6b`` (colons preserved by the
             double-underscore separator).

The ``vllm-tools`` backend is the v2 (MCP-tools-on) arm (ISS-022): instead of
a single ``/chat/completions`` call, it routes the per-instance query through
``pddl_eval.chat.chat_with_tools`` so the model can consult the pddl-copilot
MCP planner / validator before answering. PlanBench stays single-turn from its
own perspective — the tool-loop happens *inside* one ``send_query`` call, and
only the FINAL assistant text is returned. The ``vllm-tools`` token (rather
than the handoff's literal ``pddl_copilot_tools__`` engine name) keeps the
``pddl_copilot__`` prefix so PlanBench's already-patched dispatch branch
(``engine.startswith('pddl_copilot__')``) catches it with no re-clone /
re-patch of the cluster checkout.

Env vars:
  ``OLLAMA_HOST`` — Ollama server URL (default ``http://localhost:11434``).
                    Ollama backend retired 2026-05-18; kept for archaeology.
  ``VLLM_BASE``   — vLLM ``/v1`` base URL (required for ``vllm`` / ``vllm-tools``).
  ``VLLM_API_KEY``— optional bearer token for vLLM (``vllm`` backend only;
                    ``vllm-tools`` uses ``VLLMClient`` which assumes open auth).
  ``PDDL_COPILOT_THINK`` — ``on`` | ``off`` | ``default`` (default ``off``).
                    Toggles qwen3 thinking via
                    ``chat_template_kwargs.enable_thinking``; ``default``
                    omits the kwarg. PlanBench baselines are non-thinking.
  ``PDDL_MARKETPLACE_PATH`` — (``vllm-tools``) the pddl-copilot marketplace
                    clone holding ``plugins/`` (default ``~/pddl-copilot``).
  ``PDDL_PLANBENCH_PLUGINS`` — (``vllm-tools``) space-separated plugin names to
                    expose (default ``pddl-solver pddl-validator``).
  ``PDDL_COPILOT_TOOLLOG`` — (``vllm-tools``, optional) path to append a
                    per-instance tool-call JSONL side-log; a one-line summary
                    always goes to stderr regardless, for content-validation.

PlanBench's ``send_query`` is sync; this is sync too. PlanBench iterates
instances itself — one request per call. For ``vllm-tools`` the async
MCP/chat machinery is driven on ONE module-level persistent event loop with a
lazily-connected ``MCPPlanner`` (one connect, not one-per-instance); see
``_get_tools_runtime``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


_DEFAULT_NUM_PREDICT = 4096
_TEMPERATURE = 0.0
_KEEP_ALIVE = "1h"
_DEFAULT_TIMEOUT_S = 600


def _effective_num_predict(planbench_max_tokens: int) -> int:
    """PlanBench passes ``self.max_gpt_response_length = 500`` (a legacy
    OpenAI-completion cap). Thinking-capable models (qwen3.x, qwen3.6) eat
    most of that budget on the reasoning trace and emit empty content —
    smoke against qwen3:0.6b at 500 returned ``""``. Use 500 as a floor;
    fall back to 4096 (matches `pddl_eval/runner.py` non-solve defaults)."""
    return max(int(planbench_max_tokens or 0), _DEFAULT_NUM_PREDICT)


def _parse_engine_name(engine: str) -> tuple[str, str]:
    """``pddl_copilot__ollama__qwen3:0.6b`` -> ``('ollama', 'qwen3:0.6b')``."""
    if not engine.startswith("pddl_copilot__"):
        raise ValueError(f"engine name must start with 'pddl_copilot__': {engine!r}")
    rest = engine[len("pddl_copilot__") :]
    parts = rest.split("__", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"engine name must be 'pddl_copilot__<backend>__<model>': {engine!r}"
        )
    backend, model = parts
    if backend not in {"ollama", "vllm", "vllm-tools"}:
        raise ValueError(
            f"unsupported backend {backend!r}; expected 'ollama', 'vllm', or 'vllm-tools'"
        )
    return backend, model


def _ollama_chat(query: str, model: str, max_tokens: int, stop: str) -> str:
    import ollama

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)
    # Only honor the caller-supplied stop (PlanBench passes "[STATEMENT]",
    # the few-shot delimiter). We deliberately do NOT add "[PLAN END]" as a
    # stop: stop strings match against the model's hidden thinking trace
    # too, and qwen3.x / qwen3.6 echo "[PLAN END]" while reasoning about
    # the prompt — generation halts before any content is emitted (smoke
    # 2026-05-18 reproduced empty content on qwen3:0.6b). The parser
    # already extracts the [PLAN]…[PLAN END] block from full output.
    stops = [stop] if stop else []
    resp = client.chat(
        model=model,
        messages=[{"role": "user", "content": query}],
        options={
            "temperature": _TEMPERATURE,
            "num_predict": _effective_num_predict(max_tokens),
            "stop": stops,
        },
        keep_alive=_KEEP_ALIVE,
    )
    return resp["message"].get("content", "").strip()


def _vllm_chat(query: str, model: str, max_tokens: int, stop: str) -> str:
    import httpx

    base = os.environ.get("VLLM_BASE")
    if not base:
        raise RuntimeError("backend=vllm requires VLLM_BASE env var")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("VLLM_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    # Only honor the caller-supplied stop (PlanBench passes "[STATEMENT]",
    # the few-shot delimiter). We deliberately do NOT add "[PLAN END]" as a
    # stop: stop strings match against the model's hidden thinking trace
    # too, and qwen3.x / qwen3.6 echo "[PLAN END]" while reasoning about
    # the prompt — generation halts before any content is emitted (smoke
    # 2026-05-18 reproduced empty content on qwen3:0.6b). The parser
    # already extracts the [PLAN]…[PLAN END] block from full output.
    stops = [stop] if stop else []
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "temperature": _TEMPERATURE,
        "max_tokens": _effective_num_predict(max_tokens),
        "stop": stops,
    }
    # PlanBench's published baselines are non-thinking. PDDL_COPILOT_THINK
    # (set by run_planbench_rtx.sbatch from THINK) toggles qwen3's reasoning
    # trace through the chat template, mirroring pddl_eval.vllm_client's
    # extra_body.chat_template_kwargs.enable_thinking. "default" omits the
    # kwarg (model default); gemma4 has no <think> tokens and silently
    # ignores it. The kwarg is a vLLM extra-body field on the OpenAI API.
    think = os.environ.get("PDDL_COPILOT_THINK", "off").strip().lower()
    if think in ("on", "off"):
        payload["chat_template_kwargs"] = {"enable_thinking": think == "on"}
    url = base.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=_DEFAULT_TIMEOUT_S) as client:
        r = client.post(url, headers=headers, content=json.dumps(payload))
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# vllm-tools backend (v2, ISS-022) — MCP tool-loop
# ---------------------------------------------------------------------------
#
# All third-party / package imports for this path are LAZY (inside the
# functions below), never at module top: PlanBench's v1 slim venv has neither
# `mcp` nor `openai>=1.0`, and the v1 (`vllm` / `ollama`) paths must keep
# importing `planbench.engine` cleanly there. The tools path runs only under
# the dedicated `.venv-tools` (planbench deps + openai>=1.0 + mcp).

# Server-side context is fixed via --max-model-len (16384 on the PlanBench
# sbatch); VLLMClient ignores num_ctx, so this value is documentary only.
_NUM_CTX = 16384

# Minimal tool-use nudge. Deliberately does NOT inject the PDDL domain/problem
# (that would test "given PDDL" not "given a planner" and confound the
# tools-vs-no-tools comparison). The model formalises the NL task itself
# (LLM-as-formalizer), calls the planner/validator, then renders the answer in
# the task's own format. Kept task-general; t1 is plan-generation ([PLAN]…).
_TOOLS_SYSTEM_PROMPT = (
    "You have access to PDDL planning tools: a classical planner and PDDL "
    "validators. To solve the task you may translate it into a PDDL domain and "
    "problem, call the planner to obtain a verified plan, and validate it "
    "before answering. Then give your FINAL answer in the exact format the "
    "task asks for — matching the wording and layout of the in-context "
    "example (for plan-generation tasks, the plan enclosed between [PLAN] and "
    "[PLAN END])."
)

# (loop, mcp, client) singleton — built once on first vllm-tools call so the
# MCP connection (and its launched plugin server subprocesses) persists across
# all of a task's instances instead of reconnecting 500×.
_TOOLS_RUNTIME = None


def _resolve_tool_plugin_dirs() -> list[Path]:
    """Discover the MCP plugin dirs to expose to the tools loop.

    Reads ``PDDL_MARKETPLACE_PATH`` (the pddl-copilot clone) and
    ``PDDL_PLANBENCH_PLUGINS``. Self-contained (does NOT import
    run_experiment) so the tools path stays importable without the heavy
    experiment package.
    """
    base = Path(
        os.environ.get("PDDL_MARKETPLACE_PATH", str(Path.home() / "pddl-copilot"))
    ).expanduser().resolve()
    plugins_dir = base / "plugins"
    if not plugins_dir.is_dir():
        raise RuntimeError(
            f"PDDL_MARKETPLACE_PATH: plugins/ not found under {base}"
        )
    names = os.environ.get(
        "PDDL_PLANBENCH_PLUGINS", "pddl-solver pddl-validator"
    ).split()
    dirs: list[Path] = []
    for name in names:
        candidate = plugins_dir / name
        if not candidate.is_dir():
            raise RuntimeError(f"required plugin {name!r} missing under {plugins_dir}")
        dirs.append(candidate)
    return dirs


def _get_tools_runtime():
    """Lazily build the persistent (loop, MCPPlanner, VLLMClient) singleton.

    The async MCP stdio contexts and VLLMClient's httpx pool must live on ONE
    event loop for their whole lifetime; we create that loop here, connect MCP
    once, and run every instance's tool-loop on it via run_until_complete.
    """
    global _TOOLS_RUNTIME
    if _TOOLS_RUNTIME is not None:
        return _TOOLS_RUNTIME

    import asyncio
    import atexit

    from pddl_eval.chat import MCPPlanner
    from pddl_eval.vllm_client import VLLMClient

    base = os.environ.get("VLLM_BASE")
    if not base:
        raise RuntimeError("backend=vllm-tools requires VLLM_BASE env var")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    plugin_dirs = _resolve_tool_plugin_dirs()
    print(
        f"[pddl_copilot tools] connecting MCP plugins: {[d.name for d in plugin_dirs]}",
        file=sys.stderr,
    )
    mcp = MCPPlanner()
    loop.run_until_complete(mcp.connect(plugin_dirs))

    # VLLMClient normalises base_url to end in /v1 (VLLM_BASE already does).
    # Its AsyncOpenAI httpx client is created on first await — on this loop.
    client = VLLMClient(base_url=base)

    _TOOLS_RUNTIME = (loop, mcp, client)
    atexit.register(_teardown_tools_runtime)
    return _TOOLS_RUNTIME


def _teardown_tools_runtime() -> None:
    """Best-effort close of the MCP connection, vLLM client, and loop at exit."""
    global _TOOLS_RUNTIME
    if _TOOLS_RUNTIME is None:
        return
    loop, mcp, client = _TOOLS_RUNTIME
    for coro in (mcp.close(), client.aclose()):
        try:
            loop.run_until_complete(coro)
        except Exception:
            pass
    try:
        loop.close()
    except Exception:
        pass
    _TOOLS_RUNTIME = None


def _log_tool_calls(query, text, tool_calls_log, done_reason, loop_exhausted) -> None:
    """Emit a per-instance tool-call record.

    A one-line summary always goes to stderr (lands in the sbatch log) so the
    smoke can be content-validated even without the file. The full JSONL record
    is appended to ``PDDL_COPILOT_TOOLLOG`` when that env var is set. This is
    the guard against a false-green smoke: ``send_query`` returns only final
    text, so a run where NO tool ever fired would otherwise look identical to a
    working one.
    """
    names = [tc.get("name") for tc in tool_calls_log]
    print(
        f"[pddl_copilot tools] instance done: tool_calls={len(tool_calls_log)} "
        f"names={names} done_reason={done_reason!r} loop_exhausted={loop_exhausted} "
        f"final_text_len={len(text)}",
        file=sys.stderr,
    )
    path = os.environ.get("PDDL_COPILOT_TOOLLOG")
    if not path:
        return
    try:
        rec = {
            "query_head": query[:200],
            "query_len": len(query),
            "n_tool_calls": len(tool_calls_log),
            "tool_names": names,
            "done_reason": done_reason,
            "loop_exhausted": loop_exhausted,
            "final_text_head": text[:500],
            "final_text_len": len(text),
            "tool_calls": [
                {
                    "name": tc.get("name"),
                    "arguments": tc.get("arguments"),
                    "result_head": (tc.get("result") or "")[:500],
                }
                for tc in tool_calls_log
            ],
        }
        with open(path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception as exc:
        print(f"[pddl_copilot tools] side-log write failed: {exc}", file=sys.stderr)


def _vllm_tools_chat(query: str, model: str, max_tokens: int) -> str:
    """Route one PlanBench instance through the MCP tool-loop.

    Builds a FRESH message list per call (chat_with_tools mutates in place),
    drives it on the persistent loop, logs the tool-call transcript, and
    returns ONLY the final assistant text. The few-shot ``stop`` PlanBench
    passes is intentionally not forwarded — chat_with_tools is a multi-turn
    chat loop where the model emits a final tool-call-free answer and stops
    naturally; VAL's parser extracts the [PLAN] block from the full text.
    """
    from pddl_eval.chat import chat_with_tools

    loop, mcp, client = _get_tools_runtime()
    messages = [
        {"role": "system", "content": _TOOLS_SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    think = os.environ.get("PDDL_COPILOT_THINK", "off").strip().lower()
    think_flag = {"on": True, "off": False}.get(think, None)
    num_predict = _effective_num_predict(max_tokens)

    text, tool_calls_log, done_reason, loop_exhausted, _tokens, _thinking = (
        loop.run_until_complete(
            chat_with_tools(
                client=client,
                model=model,
                messages=messages,
                mcp=mcp,
                num_predict=num_predict,
                num_ctx=_NUM_CTX,
                think=think_flag,
            )
        )
    )
    _log_tool_calls(query, text or "", tool_calls_log, done_reason, loop_exhausted)
    return (text or "").strip()


def pddl_copilot_send_query(
    query: str,
    engine: str,
    max_tokens: int,
    model=None,  # PlanBench passes the preloaded handle here; we ignore it.
    stop: str = "[STATEMENT]",
) -> str:
    """PlanBench-compatible ``send_query`` for the pddl-copilot model fleet.

    Returns the model's full response (stripped). Empty string on failure —
    PlanBench treats ``""`` as a failed instance and retries with
    ``--run_till_completion``.
    """
    try:
        backend, model_tag = _parse_engine_name(engine)
        if backend == "ollama":
            return _ollama_chat(query, model_tag, max_tokens, stop)
        if backend == "vllm-tools":
            return _vllm_tools_chat(query, model_tag, max_tokens)
        return _vllm_chat(query, model_tag, max_tokens, stop)
    except Exception as exc:
        print(f"[-] pddl_copilot engine failed for {engine!r}: {exc}", file=sys.stderr)
        return ""
