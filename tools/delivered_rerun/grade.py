"""Delivered grading of one with-tools final answer (§4, "delivered success").

"The final answer graded against the oracle, with the normalisation of §2
delta 3, exact (no censoring bounds)."

Why a new grader instead of `tools/e2e_regrade.regrade_row` (hash-pinned, not
edited, partly imported):

* `regrade_row` censors at a snapshot cap. Here every row is asserted uncut
  by the loader (`response_truncated_by_storage is False`), so there is no
  censoring branch at all: every row is True or False.
* Its markdown-tolerant solve fallback (`extract_plan_lines_tolerant`, D7/D9a)
  reads the RAW text, so a leaked `<|channel>thought\\n<channel|>` prefix glued
  to the first backticked action drops that action. Prereg delta 3 removes the
  prefix from "the text the grader reads". Below, the harness extractors
  (which strip the prefix once themselves) run on the raw text, and the
  tolerant / table fallbacks run on the once-stripped text: one strip on every
  path, never two (a doubled marker is model output, scoring.py:121).
* `regrade_row` returns "indeterminate" on a missing oracle or a validator
  transport error. Here both raise: an exact grade has no third value.
* The "delivered" surface is the overlay's `e2e_strict` (NUMBERS.md "Frontier
  e2e": delivered is the primary surface, `e2e_strict`): an empty final
  answer fails, including after a correct tool call (no delegation credit).
* §8b item 12: the same rule, with the same markdown tolerances, grades the
  no-tools rows of Part C. `e2e_regrade` passes no-tools solve/validate rows
  through their strict online grade instead; here both arms go through
  `grade()` unchanged.

Imported unchanged from e2e_regrade (pure helpers, behaviour exactly as
needed): `truth_for`, `simulate_candidates`, `oracle_canon_for`,
`_TOLERANT_ACTION_RE`, `_table_plan_lines`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from pddl_eval.schemas import SolveResponse, ValidateResponse
from pddl_eval.scoring import (
    _normalize_trajectory,
    _safe_pydantic_validate,
    extract_plan_lines,
    extract_verdict,
    strip_leaked_channel_prefix,
)
from tools.e2e_regrade import (
    _TOLERANT_ACTION_RE,
    _table_plan_lines,
    oracle_canon_for,
    simulate_candidates,
    truth_for,
)

from . import constants as C
from .schema import Row, SchemaError

assert C.LEAKED_PREFIX == "<|channel>thought\n<channel|>"
assert strip_leaked_channel_prefix(C.LEAKED_PREFIX + "x") == "x"

VALIDATE_TASKS = ("validate_domain", "validate_problem", "validate_plan")

# Every reason a delivered grade can carry. Readers compare `ok is True`.
REASONS = frozenset({
    "verdict_stated_ok", "verdict_stated_wrong", "no_verdict_stated",
    "plan_valid", "plan_invalid", "no_plan_extracted",
    "trajectory_ok", "trajectory_mismatch", "simulate_empty", "format_parse_fail",
    "empty_stop", "truncated_empty", "no_room",
})

PlanKey = tuple[str, str, tuple[str, ...]]   # (domain, problem, plan lines)


@dataclass(frozen=True)
class Delivered:
    ok: bool
    reason: str
    extraction: str | None
    plan: tuple[str, ...] | None      # solve: the extracted plan
    verdict: bool | None              # validate_*: the stated verdict
    prefix_stripped: bool             # the answer carried the leaked prefix


def has_prefix(text: str) -> bool:
    return text.startswith(C.LEAKED_PREFIX)


def solve_plan(response: str) -> tuple[tuple[str, ...], str | None]:
    """Plan lines of a delivered solve answer, and how they were found.

    Order (as e2e_regrade): structured JSON, strict harness lines, D7
    tolerant lines, D9a table lines. A parsed JSON answer is final even when
    its plan is empty (e2e_regrade does the same).
    """
    parsed = _safe_pydantic_validate(SolveResponse, response)
    if parsed is not None:
        return tuple(parsed.plan), "json"
    lines = extract_plan_lines(response)
    if lines:
        return tuple(lines), "strict_lines"
    view = strip_leaked_channel_prefix(response)
    plan: list[str] = []
    for line in view.splitlines():
        if not _TOLERANT_ACTION_RE.match(line):
            continue
        inner = line[line.find("("):]
        inner = inner[: inner.find(")") + 1]
        plan.append(" ".join(inner.split()).lower())
    if plan:
        return tuple(plan), "tolerant_lines"
    table = _table_plan_lines(view)
    if table:
        return tuple(table), "table_lines"
    return (), None


def stated_verdict(response: str) -> bool | None:
    """The no-tools two-stage verdict parse (e2e_regrade.response_verdict)."""
    parsed = _safe_pydantic_validate(ValidateResponse, response)
    if parsed is not None:
        return parsed.verdict == "VALID"
    return extract_verdict(response)


def _empty(row: Row, prefix: bool) -> Delivered:
    if row.no_room:
        reason = "no_room"                      # §8a, reported separately
    elif row.done_reason == "length":
        reason = "truncated_empty"
    else:
        reason = "empty_stop"
    return Delivered(False, reason, None, None, None, prefix)


def grade(row: Row, gt_cache: dict, plan_verdicts: Mapping[PlanKey, bool]) -> Delivered:
    """Delivered grade of one rerun row (tools or Part C no-tools: the same
    rule for both, §8b item 12). Raises on anything not exact."""
    if row.layer != "rerun":
        raise SchemaError("grade() reads full-storage rerun rows only; canonical "
                          "answers are 500-character snapshots")
    resp = row.response
    prefix = has_prefix(resp)
    if not strip_leaked_channel_prefix(resp).strip():
        return _empty(row, prefix)

    if row.task in VALIDATE_TASKS:
        truth = truth_for({"task": row.task, "problem_name": row.problem,
                           "plan_label": row.plan_label})
        if truth is None:
            raise SchemaError(f"no ground truth for {row.trial_key}")
        verdict = stated_verdict(resp)
        if verdict is None:
            return Delivered(False, "no_verdict_stated", None, None, None, prefix)
        ok = verdict == truth
        return Delivered(ok, "verdict_stated_ok" if ok else "verdict_stated_wrong",
                         None, None, verdict, prefix)

    if row.task == "solve":
        plan, mode = solve_plan(resp)
        if not plan:
            return Delivered(False, "no_plan_extracted", mode, plan, None, prefix)
        key = (row.domain, row.problem, plan)
        if key not in plan_verdicts:
            raise SchemaError(f"no validator verdict for {key[:2]} plan of "
                              f"{len(plan)} actions")
        ok = plan_verdicts[key]
        if not isinstance(ok, bool):
            raise SchemaError(f"validator verdict for {key[:2]} is {ok!r}, not a bool")
        return Delivered(ok, "plan_valid" if ok else "plan_invalid", mode, plan,
                         None, prefix)

    if row.task == "simulate":
        oracle = oracle_canon_for(gt_cache, {"domain_name": row.domain,
                                             "problem_name": row.problem})
        if oracle is None:
            raise SchemaError(f"no oracle trajectory for {row.domain}/{row.problem}")
        graded = []
        for steps, mode in simulate_candidates(resp):
            canon = _normalize_trajectory(steps)
            if canon is None:
                continue
            if canon == oracle:
                return Delivered(True, "trajectory_ok", mode, None, None, prefix)
            graded.append((steps, mode))
        if graded:
            steps, mode = max(graded, key=lambda g: len(g[0]))
            return Delivered(False, "trajectory_mismatch" if steps else "simulate_empty",
                             mode, None, None, prefix)
        return Delivered(False, "format_parse_fail", None, None, None, prefix)

    raise SchemaError(f"unknown task {row.task!r}")


def solve_plans_to_validate(rows) -> set[PlanKey]:
    """Every (domain, problem, plan) a solve grade will need a verdict for."""
    need: set[PlanKey] = set()
    for r in rows:
        if r.task == "solve" and strip_leaked_channel_prefix(r.response).strip():
            plan, _ = solve_plan(r.response)
            if plan:
                need.add((r.domain, r.problem, plan))
    return need
