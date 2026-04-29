"""Per-task success / failure classification (Section 4.3 evaluation criteria).

Owns the `FR_*` failure-reason vocabulary, the regex/JSON helpers that
turn a model response into structured artefacts, and `check_success` —
the single function that decides `(tool_selected, result_correct,
failure_reason)` for one (task, response, tool_calls, gt) tuple.

DAG: scoring → chat. (No dependency on `domains` — `_validate_model_plan`
joins plan lines directly rather than reusing `domains._build_plan_str`,
which operates on a different shape.)
"""

import re

from .chat import (
    MCPPlanner,
    _parse_validation_verdict,
    _safe_json_loads,
)


# ---------------------------------------------------------------------------
# Failure-reason vocabulary used on TaskResult.failure_reason. "ok" iff
# success; otherwise one of the FR_* tags below names which classifier
# rejected the run. Stable identifiers — never rename in place; if a tag
# splits, add a new constant and migrate downstream consumers explicitly.
# ---------------------------------------------------------------------------

FR_OK = "ok"
FR_EXCEPTION = "exception"
FR_OLLAMA_PARSE_ERROR = "ollama_parse_error"
FR_TRUNCATED_NO_ANSWER = "truncated_no_answer"
FR_THINK_OVERFLOW = "think_overflow"
FR_TOOL_NOT_SELECTED = "tool_not_selected"
FR_TOOL_ERROR = "tool_error"
FR_LOOP_EXHAUSTED = "loop_exhausted"
FR_PLAN_INVALID = "plan_invalid"
FR_VERDICT_MISMATCH = "verdict_mismatch"
FR_NO_VERDICT_PARSED = "no_verdict_parsed"
FR_SIMULATE_EMPTY = "simulate_empty"
FR_RESULT_MISMATCH = "result_mismatch"
FR_UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Tool-call introspection helpers
# ---------------------------------------------------------------------------


def _used_tool(tool_calls: list[dict], name: str) -> bool:
    return any(tc["name"] == name for tc in tool_calls)


def _get_tool_results(tool_calls: list[dict], name: str) -> list[str]:
    """Return result strings from all calls to *name*."""
    return [tc["result"] for tc in tool_calls if tc["name"] == name and "result" in tc]


def _call_matches_validate_task(tc: dict, task: str) -> bool:
    """True iff a `validate_pddl_syntax` call's argument shape matches *task*.

    The tool is polymorphic — its `valid` field reflects whichever PDDL
    layer was supplied. A {domain}-only call returns the domain's verdict
    even when the model is being graded on plan validity; mismatch the
    shape and every solvable benchmark trivially scores FR_OK. This
    function is the gate. Caller is expected to have already filtered on
    `tc["name"] == "validate_pddl_syntax"`.

      validate_domain  — neither `problem` nor `plan` may be present.
      validate_problem — `problem` required, `plan` forbidden.
      validate_plan    — `plan` required.
    """
    args = tc.get("arguments", {}) or {}
    has_problem = bool(args.get("problem"))
    has_plan = bool(args.get("plan"))
    if task == "validate_domain":
        return not has_problem and not has_plan
    if task == "validate_problem":
        return has_problem and not has_plan
    if task == "validate_plan":
        return has_plan
    return False


def _extract_plan_from_tool_result(raw: str) -> list[str]:
    """Extract plan action list from a planner tool's JSON result."""
    data = _safe_json_loads(raw)
    if isinstance(data, dict) and isinstance(data.get("plan"), list):
        return data["plan"]
    return []


# Matches `(action arg1 arg2 ...)` action lines, optionally preceded by step
# numbering like "1." / "1:" or a bullet ("- ", "* "). Conservatively
# requires at least the action name as an identifier.
_ACTION_LINE_RE = re.compile(
    r"""
    ^\s*
    (?:\d+[.):]\s*|[-*]\s+)?    # optional step numbering OR bullet
    \(\s*
        ([A-Za-z][\w-]*)        # action name
        (?:\s+[\w\-?@.]+)*      # zero or more simple argument tokens
    \s*\)
    \s*$
    """,
    re.VERBOSE,
)

# Matches a VERDICT: VALID / INVALID line anywhere in the response.
_VERDICT_RE = re.compile(r"VERDICT\s*:\s*(VALID|INVALID)\b", re.IGNORECASE)

# Defensive: thinking-capable models occasionally inline a <think>...</think>
# block in `message.content` rather than (or in addition to) routing it to
# the structured `message.thinking` field. We strip it before parsing so
# extractors don't trip on action-shaped lines or VERDICT: tokens that
# appear inside the reasoning block.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def extract_plan_lines(response: str) -> list[str]:
    """Extract `(action args...)` lines from a model response.

    Strips optional step-number prefixes and keeps one action per line. Returns
    them normalized as `"(name arg1 arg2)"` (single spaces, lowercased).
    """
    if not response:
        return []
    response = _THINK_BLOCK_RE.sub("", response)
    plan: list[str] = []
    for line in response.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            continue
        m = _ACTION_LINE_RE.match(line)
        if not m:
            continue
        paren_start = line.find("(", m.start())
        inner = line[paren_start:] if paren_start >= 0 else stripped
        plan.append(" ".join(inner.split()).lower())
    return plan


def extract_verdict(response: str) -> bool | None:
    """Return True for VALID, False for INVALID, None if no verdict line found.

    Takes the last VERDICT: line in the response (model may discuss before it).
    """
    if not response:
        return None
    response = _THINK_BLOCK_RE.sub("", response)
    matches = _VERDICT_RE.findall(response)
    if not matches:
        return None
    return matches[-1].upper() == "VALID"


async def _validate_model_plan(
    mcp: MCPPlanner, domain_pddl: str, problem_pddl: str, plan_lines: list[str],
) -> bool | None:
    """Call validate_pddl_syntax on the model's extracted plan.

    Returns True iff pyvalidator reports valid, False if the plan is empty
    or pyvalidator reports invalid, None if the MCP transport failed or the
    tool returned an error-shape response. None lets callers distinguish a
    genuinely invalid plan (FR_PLAN_INVALID) from a validator that could
    not be reached (FR_TOOL_ERROR).
    """
    if not plan_lines:
        return False
    plan_str = "\n".join(plan_lines)
    try:
        raw = await mcp.call_tool(
            "validate_pddl_syntax",
            {"domain": domain_pddl, "problem": problem_pddl, "plan": plan_str},
        )
    except Exception:
        return None
    return _parse_validation_verdict(raw)


def _tool_error_seen(tool_calls: list[dict], name: str) -> bool:
    """True if any call to *name* failed.

    Two error shapes are recognized:
      - MCP transport errors, surfaced as strings prefixed with "Tool error".
      - Plugin-side errors, returned as JSON like {"error": true, "message": ...}.
        The pddl-solver / pddl-validator plugins use this shape for things
        like bad arguments, missing files, planner timeouts, etc.
    """
    for tc in tool_calls:
        if tc.get("name") != name:
            continue
        raw = tc.get("result", "")
        if isinstance(raw, str) and raw.startswith("Tool error"):
            return True
        parsed = _safe_json_loads(raw)
        if isinstance(parsed, dict) and parsed.get("error"):
            return True
    return False


async def check_success(
    task: str,
    response: str,
    tool_calls: list[dict],
    gt: dict,
    mcp: MCPPlanner,
    domain_pddl: str,
    problem_pddl: str,
    with_tools: bool,
) -> tuple[bool | None, bool, str]:
    """Decide whether a model response counts as task success.

    Returns (tool_selected, result_correct, failure_reason):
      tool_selected  — True/False for with-tools, None for no-tools.
      result_correct — end-to-end correctness of the produced artifact.
      failure_reason — FR_OK on success; one of the FR_* tags otherwise,
                       naming which classifier rejected the run.

    With-tools: check tool selection AND validate the tool result against
    ground truth (plan validity, verdict match, non-error trace).
    Without-tools: validate the actual artifact the model produced:
      - solve           → extract a plan, send it to pyvalidator, require valid==True
      - validate_*      → extract VERDICT: VALID|INVALID, compare to ground truth
      - simulate        → loose keyword check (state trace structure not graded here)
    """
    # With-tools but the model emitted zero tool calls → it answered from
    # the text alone, which is tool_not_selected regardless of how plausible
    # the text is. Without this short-circuit the per-task branches would
    # fall through to the no-tools grading path and return tool_selected=None,
    # violating the documented schema (EXPERIMENTS_FLOW.md §4.1/§9).
    if with_tools and not tool_calls:
        return False, False, FR_TOOL_NOT_SELECTED

    resp_lower = (response or "").lower()

    if task == "solve":
        if tool_calls:
            selected = _used_tool(tool_calls, "classic_planner") or _used_tool(
                tool_calls, "numeric_planner"
            )
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            planner_results = _get_tool_results(
                tool_calls, "classic_planner"
            ) + _get_tool_results(tool_calls, "numeric_planner")
            any_transport_error = False
            for raw in planner_results:
                plan_lines = _extract_plan_from_tool_result(raw)
                if not plan_lines:
                    continue
                verdict = await _validate_model_plan(
                    mcp, domain_pddl, problem_pddl, plan_lines
                )
                if verdict is True:
                    return True, True, FR_OK
                if verdict is None:
                    any_transport_error = True
            if any_transport_error or _tool_error_seen(
                tool_calls, "classic_planner"
            ) or _tool_error_seen(tool_calls, "numeric_planner"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_PLAN_INVALID
        plan_lines = extract_plan_lines(response or "")
        verdict = await _validate_model_plan(mcp, domain_pddl, problem_pddl, plan_lines)
        if verdict is True:
            return None, True, FR_OK
        if verdict is None:
            return None, False, FR_TOOL_ERROR
        return None, False, FR_PLAN_INVALID

    if task in ("validate_domain", "validate_problem", "validate_plan"):
        gt_key = {
            "validate_domain": "domain_valid",
            "validate_problem": "problem_valid",
            "validate_plan": "plan_valid",
        }[task]
        truth = gt.get(gt_key)

        if tool_calls:
            selected = _used_tool(tool_calls, "validate_pddl_syntax")
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            if truth is None:
                return True, False, FR_UNKNOWN
            # The verdict check must match the call's argument shape to the
            # task — see _call_matches_validate_task for the rule and why.
            for tc in tool_calls:
                if tc.get("name") != "validate_pddl_syntax":
                    continue
                if not _call_matches_validate_task(tc, task):
                    continue
                verdict = _parse_validation_verdict(tc.get("result", ""))
                if verdict == truth:
                    return True, True, FR_OK
            if _tool_error_seen(tool_calls, "validate_pddl_syntax"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_VERDICT_MISMATCH

        verdict = extract_verdict(response or "")
        if verdict is None:
            return None, False, FR_NO_VERDICT_PARSED
        if truth is None:
            return None, False, FR_UNKNOWN
        if verdict == truth:
            return None, True, FR_OK
        return None, False, FR_VERDICT_MISMATCH

    if task == "simulate":
        if tool_calls:
            selected = _used_tool(tool_calls, "get_state_transition")
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            # `valid` in the tool response is a PDDL-syntactic check, not a
            # simulation-correctness signal — a partial trajectory with
            # valid=false would satisfy it. Compare against the oracle
            # trajectory from gt["trace"] (same plan, same plugin → dicts
            # are byte-equal when the model passed identical inputs).
            oracle_trace = _safe_json_loads(gt.get("trace"))
            oracle_traj = oracle_trace.get("trajectory") if isinstance(oracle_trace, dict) else None
            if oracle_traj is None:
                return True, False, FR_UNKNOWN
            for raw in _get_tool_results(tool_calls, "get_state_transition"):
                parsed = _safe_json_loads(raw)
                if not isinstance(parsed, dict) or parsed.get("error"):
                    continue
                if parsed.get("trajectory") == oracle_traj:
                    return True, True, FR_OK
            if _tool_error_seen(tool_calls, "get_state_transition"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_RESULT_MISMATCH
        if "state" in resp_lower and ("after" in resp_lower or "step" in resp_lower):
            return None, True, FR_OK
        return None, False, FR_SIMULATE_EMPTY

    return None, False, FR_UNKNOWN


# ---------------------------------------------------------------------------
# Truncation / loop-exhaust overrides
# ---------------------------------------------------------------------------


# Failure reasons that should be overridden to FR_TRUNCATED_NO_ANSWER when
# the model hit its output-token cap. An "output was empty" classifier is
# misleading when the model was simply cut off mid-sentence.
_TRUNCATION_OVERRIDE_REASONS = (
    FR_PLAN_INVALID,
    FR_NO_VERDICT_PARSED,
    FR_SIMULATE_EMPTY,
    FR_UNKNOWN,
)


def _apply_truncation_override(success: bool, truncated: bool, failure_reason: str) -> str:
    """Reclassify a failure as truncated when the cap cut the model off mid-output.

    Only applies when the downstream classifier was one of the
    empty-output-looking reasons. Already-informative tags like
    FR_VERDICT_MISMATCH, FR_TOOL_ERROR, and FR_TOOL_NOT_SELECTED are
    preserved — the model had enough output for the classifier to reach a
    decision, so the truncation wasn't the proximate cause.
    """
    if success or not truncated:
        return failure_reason
    if failure_reason in _TRUNCATION_OVERRIDE_REASONS:
        return FR_TRUNCATED_NO_ANSWER
    return failure_reason


def _classify_step_failure(
    success: bool,
    done_reason: str,
    loop_exhausted: bool,
    failure_reason: str,
    *,
    thinking_text: str = "",
    response_text: str = "",
    error: str = "",
) -> tuple[str, bool]:
    """Apply THINK_OVERFLOW / LOOP_EXHAUSTED / truncation overrides.

    Returns (failure_reason, truncated). Owns the full override-precedence
    chain so callers don't have to interleave checks in the right order:

      1. FR_THINK_OVERFLOW — set when the cap fired with non-empty thinking
         and empty response, and no exception/tool-error already populated
         `error`. Skipped under loop_exhausted (FR_LOOP_EXHAUSTED is the
         more specific tag for tool-loop cap-hits).
      2. FR_LOOP_EXHAUSTED — overrides whatever the classifier returned
         when the tool loop ran out without producing an answer.
      3. Truncation override — relabels empty-output reasons
         (FR_PLAN_INVALID, FR_NO_VERDICT_PARSED, FR_SIMULATE_EMPTY,
         FR_UNKNOWN) to FR_TRUNCATED_NO_ANSWER when done_reason=="length".

    Used by both the single-task and chain paths so step records share
    failure-tag semantics. The `thinking_text`/`response_text`/`error`
    kwargs default to empty strings; chain callers that don't pass them
    skip the FR_THINK_OVERFLOW step (matches pre-2026-04-29 behavior —
    chain steps land in FR_TRUNCATED_NO_ANSWER instead).
    """
    if (not success
        and not error
        and not loop_exhausted
        and done_reason == "length"
        and thinking_text
        and not response_text):
        failure_reason = FR_THINK_OVERFLOW
    if loop_exhausted and not success:
        failure_reason = FR_LOOP_EXHAUSTED
    truncated = done_reason == "length"
    failure_reason = _apply_truncation_override(success, truncated, failure_reason)
    return failure_reason, truncated
