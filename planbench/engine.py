"""PlanBench engine adapter for the pddl-copilot model fleet.

Engine name format: ``pddl_copilot__<backend>__<model>``
  - backend: ``ollama`` | ``vllm`` | ``vllm-base`` | ``vllm-tools`` |
             ``anthropic`` | ``anthropic-tools`` | ``anthropic-scaffold`` |
             ``anthropic-directive`` (the authoritative set lives in
             ``_parse_engine_name``; the three ``anthropic-*`` arms are the
             PlanBench-WT prereg cells, t1-only).
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
  ``PDDL_COPILOT_TOOLLOG`` — (``vllm-tools`` and all ``anthropic-*`` arms,
                    optional) path to append a per-instance tool-call JSONL
                    side-log; a one-line summary always goes to stderr
                    regardless, for content-validation. For the PlanBench-WT
                    arms this file is the sole carrier of the prereg §4 join
                    keys — give every (config, arm) pair its OWN path; records
                    self-describe via ``backend``/``model``/``ts`` fields.
  ``PDDL_COPILOT_INSTANCE_ID`` — set per-instance by the patched upstream
                    ``response_generation.py`` (``apply_patches.py`` patch 6);
                    read into every side-log record as the join key. Absent
                    stamp ⇒ ``instance_id: null`` on every record and the §4
                    formalization metric is unmeasurable.
  ``PDDL_COPILOT_TASK`` — task tag (``t1``/``t3``/...); gates the
                    ``vllm-tools`` per-task system prompt and Approach-A
                    rendering, and is recorded in the side-log. The
                    ``anthropic-*`` WT arms are t1-only and refuse other values.
  ``PDDL_COPILOT_NUM_PREDICT`` — per-turn output-token cap override (default
                    floor 4096). Applies to EVERY backend path, including the
                    ``anthropic-*`` WT arms — a stray value silently changes
                    the WT apparatus, so the effective cap is recorded in each
                    side-log record.
  ``ANTHROPIC_API_KEY`` — required by all ``anthropic*`` backends.
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

import hashlib
import json
import os
from datetime import datetime, timezone
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

    ``PDDL_COPILOT_NUM_PREDICT`` overrides the 4096 floor (EVERY backend path
    flows through here, including the three ``anthropic-*`` PlanBench-WT arms —
    the WT confirmatory runs used the bare 4096 default, so a stray override in
    the shell silently changes that apparatus; the effective value is recorded
    per record in the side-log). The t1 tools smoke (job
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
    backends = {
        "ollama",
        "vllm",
        "vllm-base",
        "vllm-tools",
        "anthropic",
        # PlanBench-WT prereg arms (prereg §10-R, tag prereg-planbench-wt-v1):
        # the tools cell and its matched no-tools control. Separate engine names
        # so neither can overwrite the graded 06-22 bare-NT corpus, which lives
        # under the plain ``anthropic`` backend.
        "anthropic-tools",
        "anthropic-scaffold",
        # §9-A sensitivity arm (amendment A third rung): the WT scaffold with
        # its dangling tool directive but NO tools attached — pure availability
        # control. Mystery t1 only.
        "anthropic-directive",
    }
    if backend not in backends:
        # Derive the message from the set so it can never go stale again (the
        # pre-review text listed 5 of 8 backends, and this error is what the
        # blanket except in pddl_copilot_send_query prints on a typo'd name).
        raise ValueError(
            f"unsupported backend {backend!r}; expected one of "
            f"{', '.join(sorted(backends))}"
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


def _anthropic_done_reason(stop_reason) -> str:
    """Normalize an Anthropic stop_reason to the repo's done_reason vocabulary.

    Byte-for-byte the normalization in ``tools/frontier_runner.py`` (the
    ``"length" if stop_reason == "max_tokens" else (stop_reason or "stop")``
    line), so a ``done_reason == "length"`` truncation filter — the documented
    convention (EXPERIMENTS_FLOW.md, ``pddl_eval/vllm_client.py``) — sees the
    anthropic PlanBench cells too. Pre-review records carried the raw
    ``max_tokens`` value; corpora written before 2026-08-06 need
    ``done_reason in ("length", "max_tokens")`` for truncation counts.
    """
    return "length" if stop_reason == "max_tokens" else (stop_reason or "stop")


def _log_tool_calls(
    query, model_text, final_text, rendered, tool_calls_log, done_reason,
    loop_exhausted, usage=None, error=None, backend=None, model=None,
    num_predict=None,
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
            # JOIN KEYS — prereg §4 build precondition. ``query_head`` alone has
            # ONE distinct value across all 500 instances (every prompt opens
            # with the same domain intro), so the side-log was unjoinable and the
            # formalization-boundary metric was unmeasurable. The instance id is
            # stamped into the environment by the response_generation patch
            # (planbench/apply_patches.py, patch 6); ``query_sha256`` is a
            # belt-and-braces fallback that works even without that patch.
            "instance_id": os.environ.get("PDDL_COPILOT_INSTANCE_ID"),
            "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
            "task": os.environ.get("PDDL_COPILOT_TASK"),
            # SELF-DESCRIPTION — arm identity used to live only in the
            # filename an (uncommitted) run script chose, and append-mode
            # resumes left duplicate instance_ids with nothing to order them
            # by (realized: 518 records / 500 ids on bw-WT). Older records
            # lack these keys — consumers must .get().
            "backend": backend,
            "model": model,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "num_predict": num_predict,
            "usage": usage,
            "error": error,
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


# ---------------------------------------------------------------------------
# PlanBench-WT prereg arms (ratified 2026-07-30, tag prereg-planbench-wt-v1)
# ---------------------------------------------------------------------------
#
# Two engines, one shared scaffold. Amendment A (prereg §9-A) requires a
# COHERENT control: the NL→PDDL step and the task-format clause are shared
# BYTE-IDENTICALLY across arms, the tool-use policy sentence is MIRRORED rather
# than reused (the with-tools wording asserts "your ONLY way ... is by calling
# the provided tools", which with an empty tool list would assert a false
# premise and forbid the only available action), and NO tool name appears in the
# shared clause. The measured contrast is therefore a package contrast:
# tool list + directive.
#
# The format clause is written against the MEASURED upstream extractor, which
# biases against the tools arm (prereg §3, handoff trap 3): a plan pasted from
# ``classic_planner`` extracts to nothing because ``(unstack a b)`` tokenizes as
# ``(unstack``; markdown bolding extracts to nothing; shorthand action names
# extract to nothing; and ONE narrating sentence before the plan injects a
# duplicated action that VAL then rejects. Hence "entire answer", "no preamble",
# "no markdown", "no PDDL" — identical in both arms so the contrast stays
# unbiased.
#
# FREEZE STATUS: v2 FROZEN by Omer 2026-08-01 (prereg §10-R restart record 1,
# which quotes this text verbatim). Any further change voids the affected cells
# and restarts them (prereg §2). The ~$1.10 calibration re-run must pass
# extraction ≥90% on all four cells before the confirmatory run.

# AMENDMENT N (2026-07-30): the NL→PDDL formalization step lives in the TOOLS
# policy, not the shared block. D-J3 as accepted named both the formalization
# step and the task-format clause as shared; only the format clause is shared
# now. Reason, and it is a bias-direction argument rather than an aesthetic one:
# formalizing has a purpose only when there is a planner to receive the PDDL, so
# a shared "translate into PDDL" instruction hands the no-tools arm something it
# structurally cannot satisfy — it is told to produce PDDL and, two sentences
# later, that its entire answer must be the plan with nothing before it (and one
# sentence of preamble is MEASURED to make the upstream extractor inject a
# duplicated action that VAL rejects). Any compliance drop that causes would
# depress arm B for a reason unrelated to tools and INFLATE the WT−NT delta in
# our own hypothesis's favour — precisely the failure mode §9-A exists to stop.
# The format clause stays shared because it is the instrument, not the method:
# both arms must answer in a shape the extractor can read.
#
# Consequence, declared rather than hidden: arm A's system prompt is ~176 chars
# longer, and that difference IS the treatment (the prereg already calls this a
# package contrast — tool list + directive). Arm B is deliberately NOT padded to
# match length; filler text to hit a character count would be worse than a
# declared asymmetry.

_PB_POLICY_TOOLS = (
    "You are a PDDL planning assistant with access to planning tools. "
    "Your ONLY way to get information or solve problems is by calling the "
    "provided tools ONE AT A TIME — never guess or create plan details yourself. "
    "The task is given in natural language: translate the relevant parts into "
    "PDDL — the domain, the problem, and the plan where one is given — and get "
    "the answer from the tools."
)
_PB_POLICY_NOTOOLS = (
    "You are a PDDL planning assistant working without planning tools. "
    "Your ONLY way to get information or solve problems is by reasoning it "
    "through yourself ONE STEP AT A TIME — never guess or skip plan details."
)
# The ONLY shared block: byte-identical across arms, no tool name, no tool
# reference, and nothing either arm cannot satisfy. Written against the MEASURED
# extractor (see the arm header above).
#
# v2 (2026-08-01, calibration gate restart — planbench_wt_calibration_20260730.md):
# v1's "using exactly the action wording of the in-context example" did not stop
# either measured failure. Defect 1: the Mystery tools arm collapsed to PDDL
# shorthand ("attack g" for "attack object e"), so v2 demands every word of the
# example's action lines and bans abbreviation. Defect 2: the Mystery matched-NT
# arm narrated before [PLAN] and the extractor parsed extra actions out of the
# narration, so v2 pins the answer's first characters to [PLAN].
# Disambiguated pre-freeze (08-01): "phrased exactly as the example phrases its
# actions", not "copying the example word for word" — the copy phrasing could
# read as copy-the-example-PLAN, a defect the outcome-blind gate cannot detect
# (a copied plan extracts cleanly; accuracy is outside the decision function).
_PB_SHARED_T1_FORMAT = (
    " Your entire answer must be the plan and nothing else. The very first "
    "characters of your answer must be [PLAN] — no introduction, explanation, or "
    "summary before it. Give one action per line, phrased exactly as the "
    "in-context example phrases its actions: keep every word the example's action "
    "lines use (including words such as 'object' and 'from'), and never "
    "abbreviate or shorten an action line. End with [PLAN END] and write nothing "
    "after it. Do not use markdown emphasis. Do not put PDDL in the answer."
)


def _pb_scaffold(with_tools: bool) -> str:
    """The PlanBench-WT system scaffold for one arm (amendment N shape).

    t1-only by construction: ``_PB_SHARED_T1_FORMAT`` demands a [PLAN] block,
    so on any other task the model is mis-prompted while the upstream grader
    (e.g. t3's "plan is valid/invalid" phrase match) grades a clean, believable
    0.0. build_table renders t3 columns for these rows, which makes that cell
    look like a capability result. Refuse loudly instead — SystemExit, not an
    Exception, so ``pddl_copilot_send_query``'s blanket handler cannot swallow
    it into 500 empty answers.
    """
    task = os.environ.get("PDDL_COPILOT_TASK", "").strip().lower()
    if task and task != "t1":
        raise SystemExit(
            f"PB-WT anthropic-* arms are t1-only (_PB_SHARED_T1_FORMAT is "
            f"t1-specific); got PDDL_COPILOT_TASK={task!r}"
        )
    policy = _PB_POLICY_TOOLS if with_tools else _PB_POLICY_NOTOOLS
    return policy + _PB_SHARED_T1_FORMAT


_PB_ANTHROPIC_RUNTIME = None


def _get_pb_anthropic_runtime():
    """Lazily build the persistent (loop, MCPPlanner, AsyncAnthropic) singleton.

    Same lifetime argument as ``_get_tools_runtime``: the MCP stdio contexts and
    the SDK's httpx pool must live on ONE event loop, so we make that loop here,
    connect MCP once, and run every instance's tool loop on it. Reconnecting MCP
    per instance would relaunch the plugin server subprocesses 600×.
    """
    global _PB_ANTHROPIC_RUNTIME
    if _PB_ANTHROPIC_RUNTIME is not None:
        return _PB_ANTHROPIC_RUNTIME

    import asyncio
    import atexit

    import anthropic

    from pddl_eval.chat import MCPPlanner

    # Fail fast BEFORE side effects, mirroring the twin's VLLM_BASE guard:
    # the SDK tolerates a missing key at construction and only fails per
    # request, which the dispatch's blanket handler would turn into a full
    # run of empty answers — after mcp.connect had already spawned plugin
    # subprocesses. Either env credential the SDK reads is accepted (the
    # confirmatory runs exported ANTHROPIC_API_KEY from the launching shell).
    if not (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    ):
        raise RuntimeError(
            "backend=anthropic-tools requires ANTHROPIC_API_KEY (or "
            "ANTHROPIC_AUTH_TOKEN) in the environment"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    plugin_dirs = _resolve_tool_plugin_dirs()
    print(
        f"[pddl_copilot pb-wt] connecting MCP plugins: {[d.name for d in plugin_dirs]}",
        file=sys.stderr,
    )
    mcp = MCPPlanner()
    loop.run_until_complete(mcp.connect(plugin_dirs))
    client = anthropic.AsyncAnthropic()

    _PB_ANTHROPIC_RUNTIME = (loop, mcp, client)
    atexit.register(_teardown_pb_anthropic_runtime)
    return _PB_ANTHROPIC_RUNTIME


def _teardown_pb_anthropic_runtime() -> None:
    global _PB_ANTHROPIC_RUNTIME
    if _PB_ANTHROPIC_RUNTIME is None:
        return
    loop, mcp, client = _PB_ANTHROPIC_RUNTIME
    for coro in (mcp.close(), client.close()):
        try:
            loop.run_until_complete(coro)
        except Exception:
            pass
    try:
        loop.close()
    except Exception:
        pass
    _PB_ANTHROPIC_RUNTIME = None


def _pb_runner_tools(mcp, log: list[dict]) -> list:
    """Wrap each MCP tool as an SDK runnable tool with its ORIGINAL schema.

    Byte-for-byte the same shape as ``tools/frontier_runner.py:runner_tools`` —
    same ``MCPPlanner.call_tool`` execution path and the same
    ``"Tool error: {exc}"`` string on failure — so the harness's tool-call
    semantics and the PlanBench arm's are identical instruments.
    """
    from anthropic.lib.tools import beta_async_tool

    out = []
    for t in mcp.tools:
        fn = t["function"]

        def make(tool_name: str):
            async def _call(**kwargs) -> str:
                try:
                    result = await mcp.call_tool(tool_name, kwargs or {})
                except Exception as exc:
                    result = f"Tool error: {exc}"
                log.append(
                    {"name": tool_name, "arguments": kwargs or {}, "result": result}
                )
                return result

            return _call

        out.append(
            beta_async_tool(
                make(fn["name"]),
                name=fn["name"],
                description=fn["description"],
                input_schema=fn["parameters"],
            )
        )
    return out


def _anthropic_tools_chat(query: str, model: str, max_tokens: int) -> str:
    """One PlanBench instance through the SDK Tool Runner (prereg §2 backend).

    Returns the model's DELIVERED final message. Tool-result rendering is
    deliberately not consulted on this path — the prereg endpoint is the
    delivered answer graded by the patched upstream evaluator (D-J2), so
    ``_render_answer_from_tools`` is bypassed structurally rather than by env
    var. That makes handoff trap 1 (``PDDL_COPILOT_RENDER_FROM_TOOLS`` defaults
    to ``"1"``, which would silently measure tool-verified instead of delivered)
    unreachable for these cells.
    """
    from pddl_eval.chat import MAX_TOOL_LOOPS

    loop, mcp, client = _get_pb_anthropic_runtime()
    tool_calls_log: list[dict] = []

    async def _run():
        runner = client.beta.messages.tool_runner(
            model=model,
            max_tokens=_effective_num_predict(max_tokens),
            temperature=_TEMPERATURE,
            system=_pb_scaffold(with_tools=True),
            messages=[{"role": "user", "content": query}],
            tools=_pb_runner_tools(mcp, tool_calls_log),
            max_iterations=MAX_TOOL_LOOPS,
            # Breakpoints across the agentic loop, so each turn re-reads the
            # prior turns' prefix at cache-read rates. Prompt caching is a
            # BILLING-layer property only and is explicitly outside the
            # "identical apparatus" clause (prereg §9-C): PlanBench prompts sit
            # on a ~5% margin over Haiku 4.5's 4096-token cacheable minimum, and
            # the matched-NT arm cannot cache at all. The calibration gate
            # records the runner's ACTIVE / NET-LOSS / INACTIVE verdict.
            cache_control={"type": "ephemeral"},
        )
        usage = {"in": 0, "out": 0, "cache_write": 0, "cache_read": 0, "turns": 0}
        last = None
        try:
            async for message in runner:
                last = message
                u = message.usage
                usage["in"] += u.input_tokens
                usage["out"] += u.output_tokens
                usage["cache_write"] += u.cache_creation_input_tokens or 0
                usage["cache_read"] += u.cache_read_input_tokens or 0
                usage["turns"] += 1
        except Exception as exc:
            # Context overflow is a REAL trial outcome, not infra: a single
            # tool result can push a later turn past the window. Mirror
            # frontier_runner — keep the tool-call evidence and partial usage.
            if "prompt is too long" not in str(exc):
                raise
            return "", "max_tokens", False, usage, str(exc)[:300]

        stop_reason = last.stop_reason if last else ""
        # Same exhaustion criterion as the harness loop: the loop ended while
        # the model was still asking for a tool (no tool-call-free final turn).
        loop_exhausted = stop_reason == "tool_use"
        text = (
            ""
            if last is None or loop_exhausted
            else "".join(b.text for b in last.content if b.type == "text")
        )
        # Refusal-terminated turns end the SDK runner early and hand back the
        # refusal prose as the final message. Grading stays delivered-text
        # (treatment policy: a refusal is a delivered failure), but mark it in
        # the side-log the way frontier_runner does ("stop_reason=refusal") so
        # analyzers can partition it from honest wrong plans. Zero realized in
        # the 08-02/03 confirmatory corpora.
        err = "stop_reason=refusal" if stop_reason == "refusal" else None
        return text, stop_reason, loop_exhausted, usage, err

    try:
        text, stop_reason, loop_exhausted, usage, err = loop.run_until_complete(
            _run()
        )
    except Exception as exc:
        # Non-overflow API failures used to unwind past the side-log entirely
        # (the dispatch's blanket handler returns "" with no record), leaving
        # infra failures indistinguishable from model failures in the graded
        # corpus. Write the record, then re-raise — outward behavior unchanged.
        _log_tool_calls(
            query, "", "", False, tool_calls_log, "error", False,
            usage=None, error=str(exc)[:300], backend="anthropic-tools",
            model=model, num_predict=_effective_num_predict(max_tokens),
        )
        raise
    _log_tool_calls(
        query, text, text, False, tool_calls_log,
        _anthropic_done_reason(stop_reason), loop_exhausted,
        usage=usage, error=err, backend="anthropic-tools", model=model,
        num_predict=_effective_num_predict(max_tokens),
    )
    # NOTE (realized on the 08-01/02 bw-WT resume): returning "" here for a
    # loop-exhausted/overflowed instance means upstream response_generation
    # never sets llm_raw_response, and its skip-existing resume guard treats
    # the instance as NOT DONE — any re-invocation re-rolls exactly the failed
    # instances, silently turning single-shot trials into best-of-N for the
    # tools arm only (18 re-rolled ids, 11 flipped at temp 0). Do not resume a
    # WT cell without accounting for this; see planbench_wt_results_20260803.md
    # deviation 1.
    return (text or "").strip()


def _anthropic_scaffold_chat(query: str, model: str, max_tokens: int) -> str:
    """The matched no-tools control: identical scaffold, mirrored policy, no tools.

    Deliberately NOT ``_anthropic_chat`` — that path answers the bare upstream
    prompt with no system scaffold and is the already-graded 06-22 layer. This
    cell exists so the confirmatory contrast isolates tool availability instead
    of confounding it with prompt shape.
    """
    import anthropic

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=_effective_num_predict(max_tokens),
            temperature=_TEMPERATURE,
            system=_pb_scaffold(with_tools=False),
            messages=[{"role": "user", "content": query}],
        )
    except Exception as exc:
        # Same rationale as _anthropic_tools_chat: record the infra failure
        # in the side-log before the dispatch's blanket handler eats it.
        _log_tool_calls(
            query, "", "", False, [], "error", False,
            usage=None, error=str(exc)[:300], backend="anthropic-scaffold",
            model=model, num_predict=_effective_num_predict(max_tokens),
        )
        raise
    text = "".join(b.text for b in resp.content if b.type == "text")
    u = resp.usage
    _log_tool_calls(
        query, text, text, False, [],
        _anthropic_done_reason(resp.stop_reason), False,
        usage={
            "in": u.input_tokens,
            "out": u.output_tokens,
            "cache_write": u.cache_creation_input_tokens or 0,
            "cache_read": u.cache_read_input_tokens or 0,
            "turns": 1,
        },
        error=(
            "stop_reason=refusal" if resp.stop_reason == "refusal" else None
        ),
        backend="anthropic-scaffold", model=model,
        num_predict=_effective_num_predict(max_tokens),
    )
    return text.strip()


def _anthropic_directive_chat(query: str, model: str, max_tokens: int) -> str:
    """§9-A sensitivity arm: the WT scaffold, verbatim, with NO tools attached.

    Pure-availability control (amendment A third rung, prereg §9-A): the system
    prompt is byte-identical to the tools cell's — including the directive that
    asserts "Your ONLY way ... is by calling the provided tools", which dangles
    because no tools exist on this path. Per the pre-registered wire
    substitution, the ``tools`` parameter is OMITTED rather than sent as an
    empty list. One ``create()`` call, mirroring ``_anthropic_scaffold_chat``.
    """
    import anthropic

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=_effective_num_predict(max_tokens),
            temperature=_TEMPERATURE,
            system=_pb_scaffold(with_tools=True),
            messages=[{"role": "user", "content": query}],
        )
    except Exception as exc:
        # Same rationale as _anthropic_tools_chat: record the infra failure
        # in the side-log before the dispatch's blanket handler eats it.
        _log_tool_calls(
            query, "", "", False, [], "error", False,
            usage=None, error=str(exc)[:300], backend="anthropic-directive",
            model=model, num_predict=_effective_num_predict(max_tokens),
        )
        raise
    text = "".join(b.text for b in resp.content if b.type == "text")
    u = resp.usage
    _log_tool_calls(
        query, text, text, False, [],
        _anthropic_done_reason(resp.stop_reason), False,
        usage={
            "in": u.input_tokens,
            "out": u.output_tokens,
            "cache_write": u.cache_creation_input_tokens or 0,
            "cache_read": u.cache_read_input_tokens or 0,
            "turns": 1,
        },
        error=(
            "stop_reason=refusal" if resp.stop_reason == "refusal" else None
        ),
        backend="anthropic-directive", model=model,
        num_predict=_effective_num_predict(max_tokens),
    )
    return text.strip()


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
    ``--run_till_completion``. CAVEAT (PlanBench-WT arms): the prereg run
    recipe FORBIDS ``--run_till_completion`` for the ``anthropic-*`` cells — a
    deterministic failure (context overflow, loop exhaustion) would retry
    forever at API prices, and even plain re-invocation re-rolls empty
    instances (see the resume note in ``_anthropic_tools_chat``).
    """
    try:
        backend, model_tag = _parse_engine_name(engine)
        if backend == "ollama":
            return _ollama_chat(query, model_tag, max_tokens, stop)
        if backend == "anthropic":
            return _anthropic_chat(query, model_tag, max_tokens, stop)
        # The three PB-WT arms do NOT forward ``stop`` ("[STATEMENT]"), unlike
        # the bare ``anthropic`` arm above, which sends it as a stop sequence.
        # Wire-level asymmetry, frozen with the v2 apparatus (runs 08-01..03):
        # the WT<->matched-NT contrast is symmetric (neither sends it), but
        # ladder comparisons against the bare arm carry this extra wire diff.
        # Measured post-[PLAN END] text: bare 73/500 bw, 290/500 mystery vs
        # 0 in the scaffold/directive corpora (v2 format clause held).
        if backend == "anthropic-tools":
            return _anthropic_tools_chat(query, model_tag, max_tokens)
        if backend == "anthropic-scaffold":
            return _anthropic_scaffold_chat(query, model_tag, max_tokens)
        if backend == "anthropic-directive":
            return _anthropic_directive_chat(query, model_tag, max_tokens)
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
