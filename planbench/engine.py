"""PlanBench engine adapter for the pddl-copilot model fleet.

Engine name format: ``pddl_copilot__<backend>__<model>``
  - backend: ``ollama`` | ``vllm`` | ``vllm-tools``
  - model:   the model tag, e.g. ``qwen3:0.6b`` (colons preserved by the
             double-underscore separator).

The ``vllm-tools`` backend is the v2 (MCP-tools-on) arm (ISS-022): instead of
a single ``/chat/completions`` call, it routes the per-instance query through
``pddl_eval.chat.chat_with_tools`` so the model can consult the pddl-copilot
MCP planner / validator before answering. PlanBench stays single-turn from its
own perspective — the tool-loop happens *inside* one ``send_query`` call. The
returned answer is, for tasks with a clean structured-output mapping (t3),
*rendered deterministically from the tool's result* rather than read off the
model's final free-form turn — see ``_render_answer_from_tools`` (Approach A):
it stops a truncated/empty model turn from discarding a correct tool outcome.
Tasks without a clean mapping fall back to the model's final assistant text.
The ``vllm-tools`` token (rather
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
  ``PDDL_COPILOT_RENDER_FROM_TOOLS`` — (``vllm-tools``) ``1``/``0`` (default
                    ``1``). When on, the t3 answer is rendered from the last
                    ``validate_plan`` verdict instead of the model's final turn
                    (Approach A — fixes the truncate-to-empty failure mode). Set
                    ``0`` for the model-authored ablation.

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
    fall back to 4096 (matches `pddl_eval/runner.py` non-solve defaults).

    ``PDDL_COPILOT_NUM_PREDICT`` overrides the 4096 floor (BOTH the ``vllm``
    and ``vllm-tools`` paths flow through here). The t1 tools smoke (job
    18019718) truncated final answers at 4096 (``done_reason=length``); set
    this to the single-task sweep's ``solve`` cap (8192; sweep5v2/sweep6) so
    plan-generation answers complete and the tools/no-tools comparison shares
    one budget."""
    floor = _DEFAULT_NUM_PREDICT
    override = os.environ.get("PDDL_COPILOT_NUM_PREDICT")
    if override:
        try:
            floor = int(override)
        except ValueError:
            print(
                f"[pddl_copilot] ignoring non-int PDDL_COPILOT_NUM_PREDICT={override!r}",
                file=sys.stderr,
            )
    return max(int(planbench_max_tokens or 0), floor)


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
    if backend not in {"ollama", "vllm", "vllm-base", "vllm-tools", "anthropic"}:
        raise ValueError(
            f"unsupported backend {backend!r}; expected 'ollama', 'vllm', "
            f"'vllm-base', 'vllm-tools', or 'anthropic'"
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


def _anthropic_chat(query: str, model: str, max_tokens: int, stop: str) -> str:
    """Single live Anthropic Messages call — the no-tools frontier PlanBench arm.

    Mirrors ``_vllm_chat`` (one prompt in, final text out) but hits the Anthropic
    API instead of a self-served vLLM endpoint, so the frontier no-tools rows need
    no GPU/cluster — just ``ANTHROPIC_API_KEY``. think=off (no ``thinking`` param;
    Claude does not think unless asked), temperature 0. ``model`` is the API id
    (e.g. ``claude-haiku-4-5``). The few-shot delimiter ``stop`` is forwarded as a
    stop sequence, matching the vLLM path; VAL's parser extracts the answer block
    from the returned text. Import is lazy (the v1 slim venv lacks ``anthropic``).
    """
    import anthropic

    client = anthropic.Anthropic()
    kwargs = dict(
        model=model,
        max_tokens=_effective_num_predict(max_tokens),
        temperature=_TEMPERATURE,
        messages=[{"role": "user", "content": query}],
    )
    if stop:
        kwargs["stop_sequences"] = [stop]
    resp = client.messages.create(**kwargs)
    return "".join(b.text for b in resp.content if b.type == "text").strip()


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

# FORCING tool-use directive (smoke 2026-06-06 finding: a soft "you may use
# tools" nudge let 9B/35B ignore the tools and answer t1 directly). We reuse
# the paper's exact validated directive (pddl_eval.prompts.WITH_TOOLS_SYSTEM)
# for methodological consistency with the 5-task tools arm, then add the step
# the paper's arm doesn't need: PlanBench hands the model NATURAL LANGUAGE, so
# it must formalise NL→PDDL before it can call a tool. Still NO PDDL injection
# (LLM-as-formalizer; keeps tools-vs-no-tools unconfounded).
#
# Per-task output-format clause, keyed on PDDL_COPILOT_TASK (set per task by
# the sbatch loop) — the answer must match what PlanBench's grader parses:
#   t3 (plan verification) → "plan is (in)valid" verdict (validate_plan)
#   t7 (plan execution)    → the resulting state    (get_state_transition)
#   else (plan generation) → [PLAN]…[PLAN END]       (classic_planner)
_TOOLS_NL_FORMALIZE = (
    " The task is given in natural language: first translate the relevant "
    "parts into PDDL (domain, problem, and the plan where one is given), then "
    "call the appropriate tool, and base your FINAL answer ONLY on the tool's "
    "result."
)
_TOOLS_TASK_FORMAT: dict[str, str] = {
    "t3": (
        " This is a plan-verification task: use validate_plan to check whether "
        "the given plan solves the problem, then answer with exactly "
        "'The plan is valid.' or 'The plan is invalid.'"
    ),
    "t7": (
        " This is a plan-execution task: use the state-transition tool to "
        "compute the state reached after executing the plan, then report that "
        "resulting state using the same wording and format as the example in "
        "the task."
    ),
}
_TOOLS_DEFAULT_FORMAT = (
    " Use classic_planner to produce the plan, then give the plan between "
    "[PLAN] and [PLAN END], matching the action wording of the in-context "
    "example."
)


def _tools_system_prompt() -> str:
    """Forcing tool-use system prompt for the current PlanBench task.

    Paper's WITH_TOOLS_SYSTEM (byte-identical) + NL→PDDL formalisation step +
    a task-specific output-format clause (PDDL_COPILOT_TASK)."""
    from pddl_eval.prompts import WITH_TOOLS_SYSTEM

    task = os.environ.get("PDDL_COPILOT_TASK", "").strip().lower()
    fmt = _TOOLS_TASK_FORMAT.get(task, _TOOLS_DEFAULT_FORMAT)
    return WITH_TOOLS_SYSTEM + _TOOLS_NL_FORMALIZE + fmt

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


# ---------------------------------------------------------------------------
# Approach A — render the answer from the tool result (not the model's prose)
# ---------------------------------------------------------------------------
#
# Truncation finding (run 18162382, qwen3.6:35b): the tool loop fires correctly
# (validate_plan dominant, loop_exhausted=0) but ~66% of instances length-
# truncate the model's FINAL answer turn to empty — the model gets a good tool
# result, then rambles past num_predict before emitting the verdict. num_predict
# is not the lever (4096->8192 just doubled output). Fix: for a task whose
# answer is a deterministic function of the tool's structured output, render
# that answer here and never read the model's final turn, so a truncated/empty
# turn can't discard a correct tool outcome.
#
# Scope: t3 only for now. t3's answer ("The plan is valid/invalid.") is a pure
# boolean->string with no grounding/format dependency, and t3 is the cleanest
# tools target. The plan tasks (t1/t2/t4-t8) and t7 need PlanBench's PDDL->NL
# templating + object grounding to render faithfully; until that lands they
# fall back to the model's own text (no regression).


def _render_answer_from_tools(tool_calls_log: list[dict]) -> str | None:
    """Render PlanBench's expected answer from the relevant tool result.

    Returns the rendered answer string, or ``None`` when there is no renderable
    tool result for this task (the caller then falls back to the model's own
    final text — rendering is strictly additive, never a regression). Gated by
    ``PDDL_COPILOT_RENDER_FROM_TOOLS`` (default on); set ``0`` for the
    model-authored ablation.
    """
    if os.environ.get("PDDL_COPILOT_RENDER_FROM_TOOLS", "1").strip().lower() in (
        "0", "false", "off", "no",
    ):
        return None
    task = os.environ.get("PDDL_COPILOT_TASK", "").strip().lower()
    if task == "t3":
        return _render_t3_verdict(tool_calls_log)
    return None


def _render_t3_verdict(tool_calls_log: list[dict]) -> str | None:
    """t3 plan-verification: 'The plan is valid.' / 'The plan is invalid.'

    Taken from the LAST ``validate_plan`` call whose result parses to a verdict
    (the model's final validation is its conclusion — it may have repaired the
    plan and re-validated). Reuses the harness's canonical verdict parser so the
    mapping stays consistent with the 5-task arm. Returns ``None`` if no
    validate_plan call produced a parseable verdict (→ model-text fallback). The
    literal phrase matches what PlanBench's t3 grader keys on.
    """
    from pddl_eval.chat import _parse_validation_verdict

    for tc in reversed(tool_calls_log):
        if tc.get("name") != "validate_plan":
            continue
        verdict = _parse_validation_verdict(tc.get("result") or "")
        if verdict is None:
            continue
        return "The plan is valid." if verdict else "The plan is invalid."
    return None


def _log_tool_calls(
    query, model_text, final_text, rendered, tool_calls_log, done_reason, loop_exhausted
) -> None:
    """Emit a per-instance tool-call record.

    A one-line summary always goes to stderr (lands in the sbatch log) so the
    smoke can be content-validated even without the file. The full JSONL record
    is appended to ``PDDL_COPILOT_TOOLLOG`` when that env var is set. This is
    the guard against a false-green smoke: ``send_query`` returns only the final
    answer, so a run where NO tool ever fired would otherwise look identical to
    a working one. ``model_text`` is the model's own final turn (may be empty on
    truncation); ``final_text`` is what we actually return — when ``rendered``
    is True they differ, which is exactly the Approach-A win to keep visible.
    """
    names = [tc.get("name") for tc in tool_calls_log]
    print(
        f"[pddl_copilot tools] instance done: tool_calls={len(tool_calls_log)} "
        f"names={names} done_reason={done_reason!r} loop_exhausted={loop_exhausted} "
        f"rendered={rendered} model_text_len={len(model_text)} "
        f"final_text_len={len(final_text)}",
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
            "rendered": rendered,
            "model_text_head": model_text[:500],
            "model_text_len": len(model_text),
            "final_text_head": final_text[:500],
            "final_text_len": len(final_text),
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
    returns the final answer. For t3 (any task with a clean structured mapping)
    that answer is rendered deterministically from the tool's result
    (Approach A, ``_render_answer_from_tools``); otherwise it is the model's
    final assistant text. The few-shot ``stop`` PlanBench passes is
    intentionally not forwarded — chat_with_tools is a multi-turn chat loop
    where the model emits a final tool-call-free answer and stops naturally;
    VAL's parser extracts the [PLAN] block from the full text.
    """
    from pddl_eval.chat import chat_with_tools

    loop, mcp, client = _get_tools_runtime()
    messages = [
        {"role": "system", "content": _tools_system_prompt()},
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
    model_text = text or ""
    # Approach A: prefer the answer rendered from the tool's structured result,
    # so a truncated/empty model final turn can't discard a correct tool
    # outcome. Falls back to the model's own text when there's nothing to render
    # (non-t3 tasks, or no parseable verdict).
    rendered_answer = _render_answer_from_tools(tool_calls_log)
    final_text = rendered_answer if rendered_answer is not None else model_text
    _log_tool_calls(
        query, model_text, final_text, rendered_answer is not None,
        tool_calls_log, done_reason, loop_exhausted,
    )
    return final_text.strip()


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
        if backend == "anthropic":
            return _anthropic_chat(query, model_tag, max_tokens, stop)
        if backend == "vllm-tools":
            return _vllm_tools_chat(query, model_tag, max_tokens)
        # vllm-base is byte-identical no-tools inference to vllm; it exists only
        # to give the v2 no-tools-at-higher-num_predict baseline its OWN engine
        # name / results dir so it never collides with v1's frozen vllm__ 4096
        # leaderboard corpus (the GPT-4-comparable anchor).
        return _vllm_chat(query, model_tag, max_tokens, stop)
    except Exception as exc:
        print(f"[-] pddl_copilot engine failed for {engine!r}: {exc}", file=sys.stderr)
        return ""
