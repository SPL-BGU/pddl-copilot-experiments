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
import json
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
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
from .schemas import TASK_SCHEMAS
from .scoring import (
    FR_EXCEPTION,
    FR_OK,
    FR_OLLAMA_PARSE_ERROR,
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
#
# Non-solve caps raised from 1024/1536 -> 4096 on 2026-04-29 after the
# cluster-26042026 sweep showed truncation rates of 40.9% (validate_plan),
# 37.1% (simulate), 32.7% (validate_problem), 17.4% (validate_domain) at
# the old caps -- thinking-mode reasoning + tool-call XML emissions were
# being cut mid-stream, biasing accuracy and producing the bulk of
# `ollama_parse_error` records (Hermes/harmony XML parser fails on
# truncated <function><parameter> tags).
#
# Non-solve caps further raised 4096 -> 6144 on 2026-04-29 (same-day follow-
# up) after the post-bump nemotron-3-nano:30b smoke (job 17266087) emitted
# 4 residual Hermes <function><parameter> XML truncations on
# validate_problem/validate_plan in think=off+tools cells. The bump
# hypothesised the failures were a num_predict cliff. Smoke 17274424
# (2026-04-30, post-bump) returned the SAME 4 cells with the SAME failure
# signature, falsifying the cliff hypothesis -- the failures are content-
# dependent, not budget-dependent. nemotron-3-nano:30b was subsequently
# dropped from the active roster (CHANGELOG 2026-04-30). 6144 is retained
# as harmless additional emission headroom for the surviving 4 models
# (Qwen3.5:0.8B, qwen3.6:27b, qwen3.6:35b, gemma4:31b); reverting to 4096
# is a separate decision left for after fresh post-trim wall measurements.
# 6144 still fits inside DEFAULT_NUM_CTX (16384) with single-task PDDL
# prompts (~0.5-1.5K tokens), leaving ~8K of think+output headroom for
# thinking models. Chain runs use DEFAULT_NUM_CTX_CHAIN below.
# `solve` stays at 8192 (paper-default; raise alongside num_ctx if a
# future model lineup hits the cap).
DEFAULT_NUM_PREDICT: dict[str, int] = {
    "solve":            8192,
    "validate_domain":  6144,
    "validate_problem": 6144,
    "validate_plan":    6144,
    "simulate":         6144,
}
DEFAULT_NUM_CTX = 16384
# Held equal to DEFAULT_NUM_CTX on 2026-04-29: the "tools save tokens"
# headline requires identical ctx budgets across tools/no-tools, so
# tools+think_on must not be starved of the headroom that no-tools+think_on
# gets. Bumped from 8192/12288 to 16384 after qwen3.6:27b /
# nemotron-3-nano:30b smokes (2026-04-29) showed think_overflow at 12288
# (nemotron later dropped 2026-04-30; the ctx evidence still applies via
# qwen3.6:27b) on val_problem/val_plan (6/12 and 10/20 fail rates in both tools and
# no-tools cells — every miss was think_overflow). The pre-2026-04-28
# rationale (12288 covered qwen3:0.6b max p+e = 8680) no longer holds
# for the new qwen3.6 generation. Kept as a separate constant
# so the asymmetric branch in evaluate_one remains a no-op rather than
# getting deleted; future asymmetric experiments can override one
# without touching the other. Override via --num-ctx-thinking.
DEFAULT_NUM_CTX_THINKING = 16384
# Archived 2026-05-05 — chain phase is no longer wired into the active
# experiment flow (see CHANGELOG). Constant kept importable for any future
# resurrection of `run_chain_experiment` below.
#
# Context budget for multi-task chain runs. Chains accumulate the full
# message history (system + N×(user+assistant+tool_calls+tool_results))
# across steps, so step-4 prompts can reach ~6-8K tokens before generation
# even on small problems. Held equal to DEFAULT_NUM_CTX (16384) by the
# 2026-04-29 follow-up bump: applying the single-task think_overflow
# evidence (qwen3.6:27b / nemotron-3-nano:30b at 12288 ctx hit
# FR_THINK_OVERFLOW on 50% of validate_problem/validate_plan cells;
# nemotron later dropped 2026-04-30) to a
# chain step running the same task gives WORSE headroom, not better,
# because chain prompts include accumulated history. At 12288 chain ctx,
# step-3 validate_plan would have ~8K think+output budget vs ~11K in
# single-task -- the regime that already failed. 16384 brings step-3 to
# ~12K (comparable to single-task at 16384) and step-4 to ~8-10K (still
# tighter than single-task; raise to 20480 if a chain sweep surfaces
# step-4 think_overflow). Chains are tools-only (ISS-018), so this is
# condition-independent.
DEFAULT_NUM_CTX_CHAIN = 16384
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

# Substring signatures of Ollama's server-side tool-call parser failures.
# Matched against the exception text to route these into FR_OLLAMA_PARSE_ERROR
# instead of generic FR_EXCEPTION. Two parser families produce the bucket:
#   "error parsing tool call" — JSON tool-arg parser, emitted by
#       ollama/server/routes.go on multi-line PDDL strings (gpt-oss, 2026-04-21).
#   "XML syntax error"        — Hermes/harmony chat-template XML parser, emitted
#       on malformed/truncated <function><parameter>... tool-call emissions
#       (nemotron-3-nano:30b on validate_problem/validate_plan, 2026-04-29;
#       smoke 17274424 on 2026-04-30 confirmed identical 4-cell signature
#       across the 4096->6144 num_predict bump, establishing the failure as
#       content-dependent rather than budget-dependent — model dropped from
#       active roster, signature retained for future models with the same
#       tool-call template family).
OLLAMA_TOOL_PARSE_SIGNATURES: tuple[str, ...] = (
    "error parsing tool call",
    "XML syntax error",
)

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
    # Plan-variant label for `validate_plan` jobs (PR-3): "v1".."v5" for
    # the 5 valid plans per problem, "b1".."b5" for the 5 invalid plans.
    # "" for tasks that don't take a plan input (solve, validate_domain,
    # validate_problem) and for `simulate` (which uses only the canonical
    # planner-generated plan + trace).
    plan_label: str = ""


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
    plan_label: str = "",
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

    # Bigger context window only when (a) thinking is on (or default), AND
    # (b) the model has no PDDL tools to externalise plan/state/verdict
    # computation to. think values: True=on, False=off, None=model-default.
    # The wider budget targets the no-PDDL-tools+think cell where the model
    # inlines its reasoning into context; tool runs and think=off keep the
    # paper-default 8192. The mid-pass num_ctx flip that this rule used to
    # cause is now avoided at the caller level — `async_main` splits
    # `(conditions=both, think!=off)` into two sequential
    # `run_single_task_experiment` calls (one per condition) so num_ctx is
    # constant within each call. See CHANGELOG 2026-04-28 (PR-2 hotfix v2).
    effective_num_ctx = num_ctx_thinking if (think is not False and not with_tools) else num_ctx

    try:
        if with_tools:
            response_text, tool_calls, done_reason, loop_exhausted, tokens, thinking_text = await chat_with_tools(
                client, model, messages, mcp,
                num_predict=num_predict, num_ctx=effective_num_ctx,
                allowed_tools=allowed, think=think,
                temperature=temperature,
            )
        else:
            # PR-4: no-PDDL-tools = format-constrained sampling. Per-task
            # JSON schema enforced via Ollama format=. Free-text fallback
            # in scoring.check_success keeps tiny models scoring above
            # zero when sampling degenerates under the constraint.
            response_text, done_reason, tokens, thinking_text = await chat_without_tools(
                client, model, messages,
                num_predict=num_predict, num_ctx=effective_num_ctx, think=think,
                temperature=temperature,
                format=TASK_SCHEMAS.get(task),
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
        if any(sig in error for sig in OLLAMA_TOOL_PARSE_SIGNATURES):
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

    # `_classify_step_failure` owns the full override chain:
    # FR_THINK_OVERFLOW → FR_LOOP_EXHAUSTED → truncation. Pass the texts so
    # it can fire the think-overflow override; the chain step path doesn't
    # pass them and stays on the legacy FR_TRUNCATED_NO_ANSWER tag for
    # think-spiral steps (see ISS-005 Batch 2 / cluster-run1 analysis).
    failure_reason, truncated = _classify_step_failure(
        success, done_reason, loop_exhausted, failure_reason,
        thinking_text=thinking_text,
        response_text=response_text,
        error=error,
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
        plan_label=plan_label,
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
    plan_tag = f"/{r.plan_label}" if r.plan_label else ""
    return (
        f"  [{done:>{idx_width}}/{total} | {r.duration_s:>6.1f}s | #{scheduled_idx}] "
        f"{r.model} {cond} {r.task} {r.domain_name}/{r.problem_name}{plan_tag} v{r.prompt_variant}"
        f" -> {mark}{suffix}"
    )


# Trial-key shape used by the resume / skip-existing path. The 10-tuple
# is the minimal set of discriminators that uniquely identifies a single-
# task trial across all run configurations the harness emits today: job-
# level coordinates (model, task, dname, pname, plan_label, pv, with_tools)
# plus run-level coordinates (think_str, tool_filter, prompt_style) so
# smoke-mode multi-think runs and tool_filter sweeps don't collide in the
# same `trials.jsonl`. `_trial_key` is the single source of truth for the
# tuple shape; `TRIAL_KEY_LEN` is asserted by the loader so a future
# refactor that lengthens or reorders the tuple fails loudly on existing
# JSONLs instead of silently re-running every trial.
TrialKey = tuple[str, str, str, str, str, int, bool, str, str, str]
TRIAL_KEY_LEN = 10


def _think_str(think: bool | None) -> str:
    """Serialise the 3-valued `think` flag for inclusion in trial keys."""
    if think is True:
        return "on"
    if think is False:
        return "off"
    return "default"


def _trial_key(
    model: str, task: str, dname: str, pname: str, plan_label: str,
    pv: int, with_tools: bool,
    think_tag: str, tool_filter: str, prompt_style: str,
) -> TrialKey:
    """Build the 10-tuple resume key. See `TrialKey` shape comment.

    Module-level (not nested) so the loader and tests can reconstruct keys
    via the same code path the writer uses — a refactor that breaks the
    shape now breaks both call sites at once instead of silently desyncing.
    """
    return (
        model, task, dname, pname, plan_label, int(pv), bool(with_tools),
        think_tag, tool_filter, prompt_style,
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
    progress_path: Path | None = None,
    restored_by_key: dict[TrialKey, TaskResult] | None = None,
) -> list[TaskResult]:
    """Run the full single-task sweep with bounded Ollama concurrency.

    Jobs are enumerated up-front so `[i/N]` numbering is stable across
    reorderings; completions are printed as they finish via
    `asyncio.as_completed`. Partial results can be collected by the caller
    on KeyboardInterrupt — remaining tasks are cancelled and whatever
    finished is returned.

    Resume / skip-existing + scope filter: when `progress_path` is set,
    every completed trial is appended as one JSONL line
    `{"key": [...], "result": {...}}` so a TIMEOUT/preempt/scancel doesn't
    lose mid-run trials. When `restored_by_key` is provided (loaded by the
    caller from the same JSONL), each emission key is checked against the
    dict; matching jobs are skipped (not re-executed) and the restored
    TaskResult is captured for the return list. Restored trials whose key
    falls OUTSIDE this run's intended scope (different model, different
    think mode, dropped fixture under `--partial K`, etc.) are silently
    omitted — preventing per-cell summary pollution when a cell's
    `trials.jsonl` was seeded from a multi-cell merged source. The return
    list is ordered: restored-in-scope first (in JSONL append order),
    then newly-run trials (in completion order).
    """
    # Build the full job list up-front. Skipping unsolvable validate_plan/
    # simulate is cheaper here than inside the coroutine and keeps the
    # denominator accurate.
    # Job tuple shape (PR-3): adds plan_label as the last field.
    Job = tuple  # (model, task, dname, domain_pddl, pname, ppddl, pv,
                 #  with_tools, gt, np_for_task, plan_label)
    jobs: list[Job] = []
    with_tools_values = _expand_conditions(conditions)

    think_tag = _think_str(think)

    # In-scope keys this emission would have produced if there were no
    # resume. Used to filter `restored_by_key` to only those trials that
    # belong to the current run's slice (same meta-dims, same post-partial
    # fixture set, same shard). Out-of-scope restored trials are dropped
    # so the cell's final summary doesn't get polluted by trials seeded
    # from a multi-cell merged source.
    in_scope_keys: set[TrialKey] = set()

    def _emit_job(
        *, model, task, dname, dpddl, pname, ppddl, pv, with_tools,
        gt_frag, np_for_task, plan_label,
    ) -> None:
        # `with_tools` is intentionally OUT of the shard key so paired
        # (tools / no-tools) comparisons for the same logical key land
        # in the same shard. `plan_label` IS in the key so v1..v5 / b1..b5
        # spread across shards rather than clustering all in shard 0.
        if not _shard_filter(
            shard_i, shard_n,
            (model, task, dname, pname, plan_label, str(pv)),
        ):
            return
        key = _trial_key(
            model, task, dname, pname, plan_label, pv, with_tools,
            think_tag, tool_filter, prompt_style,
        )
        in_scope_keys.add(key)
        if restored_by_key is not None and key in restored_by_key:
            return
        jobs.append((
            model, task, dname, dpddl, pname, ppddl, pv,
            with_tools, gt_frag, np_for_task, plan_label,
        ))

    for model in models:
        for with_tools in with_tools_values:
            for task in tasks:
                # PR-4: no-PDDL-tools simulate re-enabled. Grading is now
                # JSON-trajectory deep-equality against the oracle (same
                # canonical form as the with-tools branch via
                # _normalize_trajectory), replacing the keyword-check
                # grader that ISS-002 originally dropped.
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
                # ---- Positive jobs ----
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
                        # `validate_plan` positive: emit one job per
                        # committed valid plan (v1..vN). The plan
                        # content overrides gt["plan"]/gt["plan_valid"]
                        # via gt_frag so the grader sees the labelled
                        # plan, not the planner's canonical one.
                        # `simulate`: 1 job per problem, gt unchanged
                        # (uses planner-canonical plan + trace).
                        # Other tasks: 1 job per problem.
                        if task == "validate_plan":
                            valid_plans = gt.get("valid_plans") or []
                            for i, plan_entry in enumerate(valid_plans):
                                gt_frag = {
                                    **gt,
                                    "plan": plan_entry["plan"],
                                    "plan_valid": plan_entry["plan_valid"],
                                }
                                for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                                    _emit_job(
                                        model=model, task=task, dname=dname,
                                        dpddl=dinfo["domain"], pname=pname,
                                        ppddl=ppddl, pv=pv,
                                        with_tools=with_tools, gt_frag=gt_frag,
                                        np_for_task=np_for_task,
                                        plan_label=f"v{i+1}",
                                    )
                        else:
                            for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                                _emit_job(
                                    model=model, task=task, dname=dname,
                                    dpddl=dinfo["domain"], pname=pname,
                                    ppddl=ppddl, pv=pv,
                                    with_tools=with_tools, gt_frag=gt,
                                    np_for_task=np_for_task, plan_label="",
                                )
                # ---- Negative jobs (task-targeted; ISS-001) ----
                # Each negative fixture joins exactly one task and carries
                # an inline `gt` fragment so we sidestep the by-`pname` GT
                # lookup above (different negatives could otherwise collide).
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
                    negs = ground_truth.get(dname, {}).get("_negatives") or {}
                    if not negs:
                        continue
                    if task == "validate_domain":
                        neg = negs.get("domain")
                        if neg is None:
                            continue
                        # The negative-domain fixture pairs with any
                        # positive problem (validator wants a problem
                        # arg in some shapes); pick the first by
                        # iteration order — same convention as the
                        # generate_ground_truth pass.
                        positive_first = next(iter(dinfo["problems"].values()))
                        gt_frag = {
                            "domain_valid": False,
                            "problem_valid": True,
                            "plan_valid": None,
                        }
                        for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                            _emit_job(
                                model=model, task=task, dname=dname,
                                dpddl=neg["domain_pddl"],
                                pname="domain_neg", ppddl=positive_first, pv=pv,
                                with_tools=with_tools, gt_frag=gt_frag,
                                np_for_task=np_for_task, plan_label="",
                            )
                    elif task == "validate_problem":
                        for i, neg in enumerate(negs.get("problems") or []):
                            gt_frag = {
                                "domain_valid": True,
                                "problem_valid": False,
                                "plan_valid": None,
                            }
                            for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                                _emit_job(
                                    model=model, task=task, dname=dname,
                                    dpddl=dinfo["domain"],
                                    pname=f"n{i+1:02d}",
                                    ppddl=neg["problem_pddl"], pv=pv,
                                    with_tools=with_tools, gt_frag=gt_frag,
                                    np_for_task=np_for_task, plan_label="",
                                )
                    elif task == "validate_plan":
                        per_problem = negs.get("plans_per_problem") or {}
                        for pname, neg_list in per_problem.items():
                            ppddl = dinfo["problems"].get(pname)
                            if ppddl is None:
                                continue
                            for i, neg in enumerate(neg_list):
                                gt_frag = {
                                    "domain_valid": True,
                                    "problem_valid": True,
                                    "plan_valid": False,
                                    "plan": neg["plan"],
                                }
                                for pv in ACTIVE_PROMPT_VARIANTS[:num_variants]:
                                    _emit_job(
                                        model=model, task=task, dname=dname,
                                        dpddl=dinfo["domain"], pname=pname,
                                        ppddl=ppddl, pv=pv,
                                        with_tools=with_tools, gt_frag=gt_frag,
                                        np_for_task=np_for_task,
                                        plan_label=f"b{i+1}",
                                    )

    total = len(jobs)
    results: list[TaskResult | None] = [None] * total
    if total == 0:
        # No jobs to run, but in-scope restored trials still need to be
        # surfaced (e.g. a fully-resumed cell where every trial in
        # `restored_by_key` matched a skipped emission).
        if restored_by_key:
            return [tr for k, tr in restored_by_key.items() if k in in_scope_keys]
        return []

    sem = asyncio.Semaphore(max(1, concurrency))

    async def run_one(idx: int) -> tuple[int, TaskResult]:
        (
            model, task, dname, dpddl, pname, ppddl, pv,
            with_tools, gt, np_for_task, plan_label,
        ) = jobs[idx]
        async with sem:
            r = await evaluate_one(
                client, model, task, dname, dpddl,
                pname, ppddl, pv, with_tools, mcp, gt,
                num_predict=np_for_task, num_ctx=num_ctx,
                num_ctx_thinking=num_ctx_thinking, think=think,
                tool_filter=tool_filter, prompt_style=prompt_style,
                temperature=temperature,
                plan_label=plan_label,
            )
            return idx, r

    aws = [asyncio.create_task(run_one(i)) for i in range(total)]
    done_count = 0
    # Open the resume JSONL once for the lifetime of this sweep call. asyncio
    # is single-threaded, so writes between coroutine yields cannot interleave;
    # line-buffered + flush per write is enough to make a TIMEOUT-mid-trial
    # leave behind only complete prior lines (the in-progress trial is lost,
    # which is fine — it'll be redone on resume).
    progress_handle = None
    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        # Heal a missing trailing newline. If a previous run was killed while
        # mid-write, the file may end without "\n" and the next append would
        # concatenate onto that partial line, corrupting the next valid record.
        # Padding with one "\n" terminates the partial so it stays parseable
        # as one JSONDecodeError (silently dropped by load_progress) without
        # taking the next-good record down with it.
        if progress_path.exists() and progress_path.stat().st_size > 0:
            with progress_path.open("rb") as _check:
                _check.seek(-1, 2)
                if _check.read(1) != b"\n":
                    with progress_path.open("a") as _heal:
                        _heal.write("\n")
        progress_handle = progress_path.open("a", buffering=1)
    try:
        for coro in asyncio.as_completed(aws):
            idx, r = await coro
            results[idx] = r
            if progress_handle is not None:
                (
                    j_model, j_task, j_dname, _j_dpddl, j_pname, _j_ppddl,
                    j_pv, j_wt, _j_gt, _j_np, j_plan_label,
                ) = jobs[idx]
                key = _trial_key(
                    j_model, j_task, j_dname, j_pname, j_plan_label, j_pv, j_wt,
                    think_tag, tool_filter, prompt_style,
                )
                progress_handle.write(
                    json.dumps({"key": list(key), "result": asdict(r)}) + "\n"
                )
                progress_handle.flush()
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
    finally:
        if progress_handle is not None:
            progress_handle.close()

    # Filter `restored_by_key` to in-scope and prepend in JSONL append order
    # (dict iteration preserves insertion order = first-completion order),
    # then append newly-run trials in completion order. Restored-first
    # ordering matches the pre-refactor merge semantics so downstream
    # `single_task_*.json` byte-stability across resumes is preserved.
    new_results = [r for r in results if r is not None]
    if restored_by_key:
        in_scope_restored = [
            tr for k, tr in restored_by_key.items() if k in in_scope_keys
        ]
        return in_scope_restored + new_results
    return new_results


# ---------------------------------------------------------------------------
# Multi-task chain evaluation (Section 4.4)
#
# Archived 2026-05-05 — `run_experiment.py` no longer dispatches into this
# function. Body preserved verbatim so the chain phase can be re-wired without
# rebuilding the orchestration; see CHANGELOG 2026-05-05 for context.
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
    num_ctx_chain: int = DEFAULT_NUM_CTX_CHAIN,
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
            # Chains are tools-only (no-tools chains skipped; ISS-018), so
            # this resolves to `num_ctx_chain` for every step today; the
            # num_ctx_thinking branch is preserved for forward-compat if
            # no-tools chains ever come back. `num_ctx_chain` (12288 by
            # default) leaves prompt headroom after the 2026-04-29 bump of
            # non-solve num_predict caps to 4096 -- step-4 prompts in
            # chains accumulate ~6-8K tokens of history.
            effective_num_ctx = num_ctx_thinking if (think is not False and not with_tools) else num_ctx_chain
            try:
                if with_tools:
                    resp_text, tc, step_done_reason, step_loop_exhausted, _tokens, _thinking = await chat_with_tools(
                        client, model, messages, mcp,
                        num_predict=np_for_task, num_ctx=effective_num_ctx,
                        allowed_tools=allowed, think=think,
                        temperature=temperature,
                    )
                else:
                    # PR-4: thread the per-task format schema through here
                    # too so that if no-tools chains ever come back (today
                    # gated upstream by ISS-018), `check_success`'s
                    # JSON-first grader doesn't silently fall to the
                    # free-text path / FR_FORMAT_PARSE_FAIL on simulate.
                    resp_text, step_done_reason, _tokens, _thinking = await chat_without_tools(
                        client, model, messages,
                        num_predict=np_for_task, num_ctx=effective_num_ctx, think=think,
                        temperature=temperature,
                        format=TASK_SCHEMAS.get(task),
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
                    "is_ollama_parse_error": any(
                        sig in exc_text for sig in OLLAMA_TOOL_PARSE_SIGNATURES
                    ),
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
