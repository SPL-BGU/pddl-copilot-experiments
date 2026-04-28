"""Per-eval runner + single-task / chain sweep orchestration.

Owns:
  * `TaskResult` — the universal record; everything downstream just reads
    its fields.
  * `evaluate_one` — produce one TaskResult for (model, task, domain,
    problem, prompt_variant, with_tools).
  * `run_single_task_experiment` — full single-task sweep with bounded
    Ollama concurrency, --shard partitioning, and --smoke-shuffle cell
    assignment.
  * `run_chain_experiment` — multi-task chain sweep (Section 4.4).

DAG: runner → prompts, chat, domains, scoring.
"""

import asyncio
import hashlib
import random
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .chat import (
    MCPPlanner,
    TEMPERATURE,
    chat_with_tools,
    chat_without_tools,
)
from .domains import _build_plan_str
from .prompts import (
    ACTIVE_PROMPT_VARIANTS,
    PROMPT_TEMPLATES,
    WITH_TOOLS_SYSTEM,
    WITHOUT_TOOLS_SYSTEM,
)
from .scoring import (
    FR_EXCEPTION,
    FR_OK,
    FR_OLLAMA_PARSE_ERROR,
    FR_THINK_OVERFLOW,
    FR_TOOL_ERROR,
    _classify_step_failure,
    _safe_json_loads,
    check_success,
)

if TYPE_CHECKING:
    import ollama


# ---------------------------------------------------------------------------
# Defaults (from the paper)
# ---------------------------------------------------------------------------

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]

# Per-task output caps. Chosen well above the longest legitimate plan/trace
# seen in the domains set but low enough that a thinking-mode spiral is cut
# off in seconds instead of minutes. Override via --num-predict.
DEFAULT_NUM_PREDICT: dict[str, int] = {
    "solve":            8192,
    "validate_domain":  1024,
    "validate_problem": 1024,
    "validate_plan":    1024,
    "simulate":         1536,
}
DEFAULT_NUM_CTX = 8192
# Larger context budget used only when (think != False AND with_tools=False)
# — the no-PDDL-tools + thinking cell where the model has to inline its
# reasoning instead of farming it out to MCP tools. Calibrated on
# 2026-04-28 against blocksworld/p01 with qwen3:0.6b (max prompt+eval =
# 8680, hit num_predict=8192 cap on solve) and qwen3:4b (max p+e = 6303);
# 12288 gives ~1.4× headroom over the observed max without bloating KV
# cache the way 16384 would. Override via --num-ctx-thinking.
DEFAULT_NUM_CTX_THINKING = 12288
DEFAULT_CONCURRENCY = 4

# Cap on stored response/exception strings in result records. The full text
# is reproducible by re-running the prompt; the stored snippet only needs to
# be enough for downstream analyses (df.groupby("error"), failure-mode
# inspection). 500 chars is the empirically-sufficient cutoff observed
# across qwen3 / gpt-oss / gemma traces in the 2026-04-20 sweep.
RESPONSE_SNAPSHOT_LEN = 500
# Cap on stored `thinking` snippet in result records. Asymmetric vs
# RESPONSE_SNAPSHOT_LEN (4096 vs 500) because thinking spirals are
# structurally longer than graded responses (calibration 2026-04-28
# observed thinking_chars up to ~30K on qwen3:0.6b solve); 4096 captures
# the relevant tail for failure-mode inspection without bloating per-
# record JSON. Full content is reproducible by re-running the prompt.
THINKING_SNAPSHOT_LEN = 4096

# Substring signature of Ollama's server-side tool-call JSON parser failure
# (emitted by ollama/server/routes.go when it can't parse tool-call arguments,
# e.g. multi-line PDDL strings with gpt-oss). Matched against the exception
# text to route these into FR_OLLAMA_PARSE_ERROR instead of generic FR_EXCEPTION.
OLLAMA_TOOL_PARSE_SIGNATURE = "error parsing tool call"

# Per-task tool allowlists. When --tool-filter=per-task, only these tool names
# are exposed to the model for the given task, controlling for tool-selection
# noise when the connected MCP servers expose unrelated tools.
TASK_TOOLS: dict[str, list[str]] = {
    "solve":            ["classic_planner", "numeric_planner"],
    "validate_domain":  ["validate_pddl_syntax"],
    "validate_problem": ["validate_pddl_syntax"],
    "validate_plan":    ["validate_pddl_syntax"],
    "simulate":         ["get_state_transition"],
}


def _expand_conditions(conditions: str) -> tuple[bool, ...]:
    """Map a --conditions value to the with_tools iteration order.

    'both' keeps the (True, False) order that predated the flag so existing
    run IDs and progress logs remain byte-comparable for reproductions.
    """
    if conditions == "tools":
        return (True,)
    if conditions == "no-tools":
        return (False,)
    return (True, False)


def _resolve_num_predict(override: int | None, task: str) -> int:
    """Return the per-task num_predict cap, honouring the CLI override."""
    return override if override is not None else DEFAULT_NUM_PREDICT[task]


def _shard_filter(shard_i: int, shard_n: int, key_parts: tuple[str, ...]) -> bool:
    # Returns True when the key belongs in shard `shard_i` of `shard_n`.
    # Stable across hosts (sha256, not Python's PYTHONHASHSEED-salted hash).
    if shard_n <= 1:
        return True
    key = "|".join(key_parts).encode()
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % shard_n
    return bucket == shard_i


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    model: str
    task: str
    domain_name: str
    problem_name: str
    prompt_variant: int
    with_tools: bool
    success: bool
    tool_selected: bool | None = None  # True/False for with-tools, None for no-tools
    response: str = ""
    thinking: str = ""                   # last-turn message.thinking, capped at THINKING_SNAPSHOT_LEN
    tool_calls: list = field(default_factory=list)
    tokens: dict = field(default_factory=dict)  # {prompt, completion, turns, total_duration_ns, eval_duration_ns}
    duration_s: float = 0.0
    error: str = ""
    tool_filter: str = "all"
    prompt_style: str = "minimal"
    failure_reason: str = FR_OK          # FR_* constant — "ok" iff success
    truncated: bool = False              # done_reason == "length" on any turn
    done_reason: str = ""                # raw done_reason from the last chat turn


# ---------------------------------------------------------------------------
# Single-task evaluation
# ---------------------------------------------------------------------------


async def evaluate_one(
    client: "ollama.AsyncClient",
    model: str,
    task: str,
    domain_name: str,
    domain_pddl: str,
    problem_name: str,
    problem_pddl: str,
    prompt_variant: int,
    with_tools: bool,
    mcp: MCPPlanner,
    gt: dict,
    num_predict: int,
    num_ctx: int,
    num_ctx_thinking: int,
    think: bool | None,
    tool_filter: str = "all",
    prompt_style: str = "minimal",
    temperature: float = TEMPERATURE,
) -> TaskResult:
    template = PROMPT_TEMPLATES[task][prompt_variant % len(PROMPT_TEMPLATES[task])]

    plan_str = _build_plan_str(gt) if task in ("validate_plan", "simulate") else ""

    prompt = template.format(domain=domain_pddl, problem=problem_pddl, plan=plan_str)
    system = WITH_TOOLS_SYSTEM[prompt_style] if with_tools else WITHOUT_TOOLS_SYSTEM
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    t0 = time.time()
    tool_calls: list[dict] = []
    error = ""
    response_text = ""
    thinking_text = ""
    tokens: dict = {}
    done_reason = ""
    loop_exhausted = False

    allowed = TASK_TOOLS.get(task) if tool_filter == "per-task" else None

    # Bigger context window when thinking is on (or default), regardless of
    # condition. think values: True=on, False=off, None=model-default. The
    # wider budget targets thinking spirals; flipping num_ctx WITHIN a
    # think-pass causes Ollama to reload the model mid-batch, which
    # deadlocks under concurrency (smoke job 17244356 hung at the
    # tools→no-tools boundary on think=on, 2026-04-28). Keeping num_ctx
    # constant within a pass costs a few extra KB of KV cache on
    # tool-condition runs, well under the wallclock cost of a hang.
    effective_num_ctx = num_ctx_thinking if (think is not False) else num_ctx

    try:
        if with_tools:
            response_text, tool_calls, done_reason, loop_exhausted, tokens, thinking_text = await chat_with_tools(
                client, model, messages, mcp,
                num_predict=num_predict, num_ctx=effective_num_ctx,
                allowed_tools=allowed, think=think,
                temperature=temperature,
            )
        else:
            response_text, done_reason, tokens, thinking_text = await chat_without_tools(
                client, model, messages,
                num_predict=num_predict, num_ctx=effective_num_ctx, think=think,
                temperature=temperature,
            )
    except Exception as exc:
        error = str(exc)
        print(f"[exception] {type(exc).__name__}: {error}", file=sys.stderr, flush=True)

    duration = time.time() - t0
    tool_selected: bool | None = None
    failure_reason = FR_OK
    if error:
        success = False
        # Ollama's server-side tool-call JSON parser chokes on multi-line
        # strings in tool arguments (observed heavily with gpt-oss on PDDL
        # domains). Classify separately so analysis can quantify the upstream
        # parser-bug rate instead of lumping it into generic exceptions.
        if OLLAMA_TOOL_PARSE_SIGNATURE in error:
            failure_reason = FR_OLLAMA_PARSE_ERROR
        else:
            failure_reason = FR_EXCEPTION
    else:
        try:
            tool_selected, success, failure_reason = await check_success(
                task, response_text, tool_calls, gt, mcp, domain_pddl, problem_pddl,
                with_tools=with_tools,
            )
        except Exception as exc:
            success = False
            error = f"scoring error: {exc}"
            print(f"[scoring exception] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            failure_reason = FR_EXCEPTION

        # Populate the record's `error` field with the first tool-level error
        # message when the run was rejected as FR_TOOL_ERROR. The information
        # is already in `tool_calls[i].result` but leaving `error` empty makes
        # downstream `df.groupby("error")` analyses blind to the 202 records
        # in run #1 that landed here.
        if failure_reason == FR_TOOL_ERROR and not error:
            for tc in tool_calls:
                parsed = _safe_json_loads(tc.get("result"))
                if isinstance(parsed, dict) and parsed.get("error"):
                    error = f"tool={tc.get('name')}: {parsed.get('message','')}"
                    break

    # FR_THINK_OVERFLOW: thinking spiral consumed the completion budget,
    # leaving an empty `content` string. More-specific tag than
    # FR_TRUNCATED_NO_ANSWER. Detect inline (before _classify_step_failure)
    # so the truncation override doesn't relabel it generically. Skip when
    # loop_exhausted is set — that's a tool-loop cap-hit, not a thinking
    # spiral, and FR_LOOP_EXHAUSTED is the more specific tag for that case
    # (precedence taken inside _classify_step_failure).
    if (not error
        and not loop_exhausted
        and done_reason == "length"
        and thinking_text
        and not response_text):
        failure_reason = FR_THINK_OVERFLOW

    # The model kept tool-calling until the MAX_TOOL_LOOPS cap fired without
    # emitting an assistant answer. `chat_with_tools` returned empty text in
    # that case, so `response` is already correct. Relabel the failure so
    # "gave up after 10 tool calls" is distinguishable from real capability
    # failures (see ISS-005 Batch 2 / cluster-run1 analysis).
    failure_reason, truncated = _classify_step_failure(
        success, done_reason, loop_exhausted, failure_reason,
    )

    return TaskResult(
        model=model,
        task=task,
        domain_name=domain_name,
        problem_name=problem_name,
        prompt_variant=prompt_variant,
        with_tools=with_tools,
        success=success,
        tool_selected=tool_selected,
        response=response_text[:RESPONSE_SNAPSHOT_LEN],
        thinking=thinking_text[:THINKING_SNAPSHOT_LEN] if thinking_text else "",
        tool_calls=tool_calls,
        tokens=tokens,
        duration_s=round(duration, 2),
        error=error,
        tool_filter=tool_filter,
        prompt_style=prompt_style,
        failure_reason=failure_reason,
        truncated=truncated,
        done_reason=done_reason,
    )


def _format_progress(done: int, total: int, scheduled_idx: int, r: TaskResult) -> str:
    """One-line completion log entry, safe for concurrent out-of-order prints.

    `done` is the running completion count; `scheduled_idx` is the 0-based
    enumerate order from the jobs list so the label is stable across runs.
    """
    cond = "tools" if r.with_tools else "no-tools"
    idx_width = len(str(total))
    mark = "OK" if r.success else "FAIL"
    suffix = "" if r.success else f" ({r.failure_reason})"
    return (
        f"  [{done:>{idx_width}}/{total} | {r.duration_s:>6.1f}s | #{scheduled_idx}] "
        f"{r.model} {cond} {r.task} {r.domain_name}/{r.problem_name} v{r.prompt_variant}"
        f" -> {mark}{suffix}"
    )


async def run_single_task_experiment(
    client: "ollama.AsyncClient",
    models: list[str],
    tasks: list[str],
    domains: dict,
    ground_truth: dict,
    mcp: MCPPlanner,
    num_variants: int = len(ACTIVE_PROMPT_VARIANTS),
    tool_filter: str = "all",
    prompt_style: str = "minimal",
    num_predict_override: int | None = None,
    num_ctx: int = DEFAULT_NUM_CTX,
    num_ctx_thinking: int = DEFAULT_NUM_CTX_THINKING,
    think: bool | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    conditions: str = "both",
    temperature: float = TEMPERATURE,
    shard_i: int = 0,
    shard_n: int = 1,
    cell_assignment: dict[tuple[str, str], tuple[str, str]] | None = None,
) -> list[TaskResult]:
    """Run the full single-task sweep with bounded Ollama concurrency.

    Jobs are enumerated up-front so `[i/N]` numbering is stable across
    reorderings; completions are printed as they finish via
    `asyncio.as_completed`. Partial results can be collected by the caller
    on KeyboardInterrupt — remaining tasks are cancelled and whatever
    finished is returned.
    """
    # Build the full job list up-front. Skipping unsolvable validate_plan/
    # simulate is cheaper here than inside the coroutine and keeps the
    # denominator accurate.
    Job = tuple  # (model, task, dname, domain_pddl, pname, ppddl, pv, with_tools, gt, np)
    jobs: list[Job] = []
    with_tools_values = _expand_conditions(conditions)
    # Map each negative-fixture kind to the single task it tests. Keep this
    # in sync with `generate_ground_truth`'s `_negatives` slot keys.
    NEGATIVE_KINDS: tuple[tuple[str, str, str], ...] = (
        ("domain",  "validate_domain",  "domain_0"),
        ("problem", "validate_problem", "problem_0"),
        ("plan",    "validate_plan",    "plan_0"),
    )
    for model in models:
        for with_tools in with_tools_values:
            for task in tasks:
                # No-tools is graded for `solve` and `validate_*` (the
                # latter became discriminative once balanced negative
                # fixtures landed; see ISS-001). `simulate` no-tools
                # stays excluded — its grader (a literal keyword check
                # at `check_success` in this file) is non-discriminative
                # regardless of negatives.
                if not with_tools and task == "simulate":
                    continue
                np_for_task = _resolve_num_predict(num_predict_override, task)
                # `--smoke-shuffle` constrains each (model, task) cell to a
                # single random (domain, problem) pick; iterate only that
                # pair instead of the full grid.
                if cell_assignment is not None:
                    pick = cell_assignment.get((model, task))
                    if pick is None:
                        continue
                    pick_dname, pick_pname = pick
                    domain_iter = (
                        [(pick_dname, domains[pick_dname])]
                        if pick_dname in domains else []
                    )
                else:
                    domain_iter = list(domains.items())
                # ---- Positive jobs (one per (dname, pname, prompt-variant)) ----
                for dname, dinfo in domain_iter:
                    if cell_assignment is not None:
                        ppddl = dinfo["problems"].get(pick_pname)
                        problem_iter = (
                            [(pick_pname, ppddl)] if ppddl is not None else []
                        )
                    else:
                        problem_iter = list(dinfo["problems"].items())
                    for pname, ppddl in problem_iter:
                        gt = ground_truth.get(dname, {}).get(pname, {})
                        if task in ("validate_plan", "simulate") and not gt.get("plan"):
                            continue
                        for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                            # `with_tools` is intentionally OUT of the shard
                            # key so paired (tools / no-tools) comparisons
                            # for the same (m, t, d, p, pv) land in the
                            # same shard.
                            if not _shard_filter(
                                shard_i, shard_n,
                                (model, task, dname, pname, str(pv)),
                            ):
                                continue
                            jobs.append((
                                model, task, dname, dinfo["domain"],
                                pname, ppddl, pv, with_tools, gt, np_for_task,
                            ))
                # ---- Negative jobs (task-targeted; ISS-001) ----
                # Each negative fixture joins exactly one task and carries
                # an inline `gt` fragment so we sidestep the by-`pname` GT
                # lookup above (two negatives could otherwise collide).
                for kind, target_task, neg_pname in NEGATIVE_KINDS:
                    if target_task != task:
                        continue
                    # Mirror the (model, task) → (dname, pname) cell
                    # assignment used by `--smoke-shuffle` for positive
                    # jobs: one negative per cell, drawn from the assigned
                    # domain's `_negatives` slot.
                    if cell_assignment is not None:
                        pick = cell_assignment.get((model, task))
                        if pick is None:
                            continue
                        neg_domain_iter = (
                            [(pick[0], domains[pick[0]])]
                            if pick[0] in domains else []
                        )
                    else:
                        neg_domain_iter = list(domains.items())
                    for dname, dinfo in neg_domain_iter:
                        neg_slot = (
                            ground_truth.get(dname, {})
                            .get("_negatives", {})
                            .get(kind)
                        )
                        if neg_slot is None:
                            continue
                        # Single-positive-per-domain assumption (paper
                        # dataset). Mirrors the choice in
                        # `generate_ground_truth`'s negatives pass; if
                        # multi-problem datasets ever land, swap this for
                        # the designated-primary lookup proposed there.
                        positive_p01 = next(iter(dinfo["problems"].values()))
                        if kind == "domain":
                            d_pddl = neg_slot["domain_pddl"]
                            p_pddl = positive_p01
                            gt_frag = {
                                "domain_valid": False,
                                "problem_valid": True,
                                "plan_valid": None,
                            }
                        elif kind == "problem":
                            d_pddl = dinfo["domain"]
                            p_pddl = neg_slot["problem_pddl"]
                            gt_frag = {
                                "domain_valid": True,
                                "problem_valid": False,
                                "plan_valid": None,
                            }
                        else:  # kind == "plan"
                            d_pddl = dinfo["domain"]
                            p_pddl = positive_p01
                            gt_frag = {
                                "domain_valid": True,
                                "problem_valid": True,
                                "plan_valid": False,
                                "plan": neg_slot["plan"],
                            }
                        for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                            if not _shard_filter(
                                shard_i, shard_n,
                                (model, target_task, dname, neg_pname, str(pv)),
                            ):
                                continue
                            jobs.append((
                                model, target_task, dname, d_pddl,
                                neg_pname, p_pddl, pv, with_tools, gt_frag, np_for_task,
                            ))

    total = len(jobs)
    results: list[TaskResult | None] = [None] * total
    if total == 0:
        return []

    sem = asyncio.Semaphore(max(1, concurrency))

    async def run_one(idx: int) -> tuple[int, TaskResult]:
        (
            model, task, dname, dpddl, pname, ppddl, pv,
            with_tools, gt, np_for_task,
        ) = jobs[idx]
        async with sem:
            r = await evaluate_one(
                client, model, task, dname, dpddl,
                pname, ppddl, pv, with_tools, mcp, gt,
                num_predict=np_for_task, num_ctx=num_ctx,
                num_ctx_thinking=num_ctx_thinking, think=think,
                tool_filter=tool_filter, prompt_style=prompt_style,
                temperature=temperature,
            )
            return idx, r

    aws = [asyncio.create_task(run_one(i)) for i in range(total)]
    done_count = 0
    try:
        for coro in asyncio.as_completed(aws):
            idx, r = await coro
            results[idx] = r
            done_count += 1
            print(_format_progress(done_count, total, idx, r), flush=True)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n  Cancelling pending tasks...", flush=True)
        for t in aws:
            if not t.done():
                t.cancel()
        # Drain cancellations so close paths don't hang; results already
        # written to `results[idx]` via completed futures are kept.
        await asyncio.gather(*aws, return_exceptions=True)
        raise

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Multi-task chain evaluation (Section 4.4)
# ---------------------------------------------------------------------------


async def run_chain_experiment(
    client: "ollama.AsyncClient",
    models: list[str],
    domains: dict,
    ground_truth: dict,
    mcp: MCPPlanner,
    chain_lengths: tuple[int, ...] = (2, 3, 4, 5),
    samples: int = 20,
    tool_filter: str = "all",
    with_tools: bool = True,
    prompt_style: str = "minimal",
    num_predict_override: int | None = None,
    num_ctx: int = DEFAULT_NUM_CTX,
    num_ctx_thinking: int = DEFAULT_NUM_CTX_THINKING,
    think: bool | None = None,
    temperature: float = TEMPERATURE,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> list[dict]:
    results: list[dict] = []
    domain_items = list(domains.items())
    system_prompt = WITH_TOOLS_SYSTEM[prompt_style] if with_tools else WITHOUT_TOOLS_SYSTEM
    cond_label = "tools" if with_tools else "no-tools"

    async def run_sample(
        model: str,
        i: int,
        dname: str,
        dinfo: dict,
        pname: str,
        ppddl: str,
        chain_tasks: list[str],
        step_templates: list[str],
    ) -> dict:
        gt = ground_truth.get(dname, {}).get(pname, {})
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        chain_ok = True
        step_records: list[dict] = []
        sample_exception: dict | None = None

        for step_index, task in enumerate(chain_tasks):
            # Mirror the single-task guard (run_single_task_experiment,
            # above): if the oracle never produced a plan for this
            # problem, validate_plan/simulate have no ground truth to
            # grade against and would deterministically fail the chain
            # as a ground-truth-coverage artifact rather than a model
            # signal. Skip the step and keep the chain alive. Skipped
            # steps are not appended to step_records, so
            # len(step_records) gives the effective chain length
            # (ISS-011).
            if task in ("validate_plan", "simulate") and not gt.get("plan"):
                continue
            template = step_templates[step_index]
            plan_str = _build_plan_str(gt) if task in ("validate_plan", "simulate") else ""
            prompt = template.format(
                domain=dinfo["domain"], problem=ppddl, plan=plan_str,
            )
            messages.append({"role": "user", "content": prompt})

            np_for_task = _resolve_num_predict(num_predict_override, task)
            allowed = TASK_TOOLS.get(task) if tool_filter == "per-task" else None
            step_loop_exhausted = False
            # Mirror evaluate_one's effective_num_ctx rule (think-only,
            # not condition-dependent — see the runner.py:evaluate_one
            # comment for why mid-pass num_ctx flips deadlock Ollama).
            effective_num_ctx = num_ctx_thinking if (think is not False) else num_ctx
            try:
                if with_tools:
                    resp_text, tc, step_done_reason, step_loop_exhausted, _tokens, _thinking = await chat_with_tools(
                        client, model, messages, mcp,
                        num_predict=np_for_task, num_ctx=effective_num_ctx,
                        allowed_tools=allowed, think=think,
                        temperature=temperature,
                    )
                else:
                    resp_text, step_done_reason, _tokens, _thinking = await chat_without_tools(
                        client, model, messages,
                        num_predict=np_for_task, num_ctx=effective_num_ctx, think=think,
                        temperature=temperature,
                    )
                    tc = []
                _sel, step_ok, step_fr = await check_success(
                    task, resp_text, tc, gt, mcp, dinfo["domain"], ppddl,
                    with_tools=with_tools,
                )
                # Mirror single-task semantics (evaluate_one): when the
                # cap cut the model off mid-output, relabel empty-output
                # reasons as FR_TRUNCATED_NO_ANSWER so step_records is
                # directly comparable to single_task_*.json failure
                # reasons. Aggregate success_rate is unaffected — only
                # the string on already-failing steps changes.
                step_fr, step_truncated = _classify_step_failure(
                    step_ok, step_done_reason, step_loop_exhausted, step_fr,
                )
                step_records.append({
                    "step_index": step_index,
                    "task": task,
                    "success": step_ok,
                    "failure_reason": step_fr,
                    "tool_calls_count": len(tc),
                    "truncated": step_truncated,
                    "loop_exhausted": step_loop_exhausted,
                })
                if not step_ok:
                    chain_ok = False
                    break
            except Exception as exc:
                exc_text = str(exc)
                sample_exception = {
                    "step_index": step_index,
                    "task": task,
                    "exc_type": type(exc).__name__,
                    "exc_message": exc_text[:RESPONSE_SNAPSHOT_LEN],
                    # Classify upstream Ollama tool-call JSON parser
                    # failures so chain analysis can separate them
                    # from other exception types (matches
                    # FR_OLLAMA_PARSE_ERROR in evaluate_one).
                    "is_ollama_parse_error": OLLAMA_TOOL_PARSE_SIGNATURE in exc_text,
                }
                print(
                    f"[chain exception] {type(exc).__name__}: {exc_text}",
                    file=sys.stderr, flush=True,
                )
                chain_ok = False
                break

        return {
            "idx": i,
            "domain": dname,
            "problem": pname,
            "chain_tasks": chain_tasks,
            "step_records": step_records,
            "final_success": chain_ok,
            "exception": sample_exception,
        }

    for model in models:
        for n in chain_lengths:
            # Pre-sample all randomness before fan-out so RNG order is
            # deterministic w.r.t. serial execution. Without this, coroutines
            # interleave random.choice calls and runs become non-reproducible
            # even at temperature=0.
            sample_plans: list[tuple] = []
            for i in range(samples):
                dname, dinfo = random.choice(domain_items)
                pname = random.choice(list(dinfo["problems"].keys()))
                ppddl = dinfo["problems"][pname]
                chain_tasks = random.choices(TASKS, k=n)
                # Sample only from ACTIVE_PROMPT_VARIANTS so chains use the
                # same variant pool as the single-task sweep (otherwise random
                # picks from disabled v3/v4 would reintroduce the variants we
                # decided to drop on 2026-04-27).
                #
                # Compute-time-saving decision for the following iterations:
                # the chain phase is intentionally left at the trimmed pool
                # (3 paraphrases) rather than the full 5 so each chain step
                # samples from the faster set. This shrinks chain-phase
                # paraphrase variance slightly but keeps wall time bounded.
                # Extend back to all 5 variants later (e.g. for the final
                # paper sweep) by sampling from `range(len(PROMPT_TEMPLATES[t]))`.
                step_templates = [
                    PROMPT_TEMPLATES[t][random.choice(ACTIVE_PROMPT_VARIANTS)]
                    for t in chain_tasks
                ]
                sample_plans.append((model, i, dname, dinfo, pname, ppddl, chain_tasks, step_templates))

            sem = asyncio.Semaphore(max(1, concurrency))

            async def bounded_sample(plan: tuple) -> dict:
                async with sem:
                    return await run_sample(*plan)

            aws = [asyncio.create_task(bounded_sample(p)) for p in sample_plans]
            samples_detail: list[dict] = []
            successes = 0
            try:
                for coro in asyncio.as_completed(aws):
                    detail = await coro
                    samples_detail.append(detail)
                    if detail["final_success"]:
                        successes += 1
                    mark = "OK" if detail["final_success"] else "FAIL"
                    print(
                        f"  {model}|{cond_label} chain={n} "
                        f"[{len(samples_detail)}/{samples}] {mark}"
                    )
            except (KeyboardInterrupt, asyncio.CancelledError):
                for t in aws:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*aws, return_exceptions=True)
                raise

            # Restore dispatch order so samples_detail indices are stable
            # across runs (matters for any post-hoc analysis that joins by
            # sample idx). as_completed yields in completion order, which
            # is nondeterministic under concurrency.
            samples_detail.sort(key=lambda d: d["idx"])

            results.append({
                "model": model,
                "with_tools": with_tools,
                "chain_length": n,
                "samples": samples,
                "successes": successes,
                "success_rate": round(successes / samples, 2),
                "tool_filter": tool_filter,
                "prompt_style": prompt_style,
                "samples_detail": samples_detail,
            })
    return results
