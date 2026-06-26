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
from .schemas import (
    SimulateResponse,
    SolveResponse,
    StateStep,
    ValidateResponse,
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
FR_WRONG_TOOL = "wrong_tool"
FR_TOOL_ERROR = "tool_error"
FR_LOOP_EXHAUSTED = "loop_exhausted"
FR_PLAN_INVALID = "plan_invalid"
FR_VERDICT_MISMATCH = "verdict_mismatch"
FR_NO_VERDICT_PARSED = "no_verdict_parsed"
FR_SIMULATE_EMPTY = "simulate_empty"
FR_RESULT_MISMATCH = "result_mismatch"
FR_FORMAT_PARSE_FAIL = "format_parse_fail"
FR_UNKNOWN = "unknown"

# The three task-aligned validator tools (marketplace 1.4.0). A `validate_*`
# trial that invoked one of these but not the task-matching one is graded
# FR_WRONG_TOOL — distinct from FR_TOOL_NOT_SELECTED (no validator-family
# call at all) and FR_VERDICT_MISMATCH (right tool, wrong verdict).
_VALIDATE_TOOL_NAMES = frozenset({
    "validate_domain",
    "validate_problem",
    "validate_plan",
})


# ---------------------------------------------------------------------------
# Tool-call introspection helpers
# ---------------------------------------------------------------------------


def _used_tool(tool_calls: list[dict], name: str) -> bool:
    return any(tc["name"] == name for tc in tool_calls)


def _get_tool_results(tool_calls: list[dict], name: str) -> list[str]:
    """Return result strings from all calls to *name*."""
    return [tc["result"] for tc in tool_calls if tc["name"] == name and "result" in tc]


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


# Predicate / atom syntax bridge. The no-PDDL-tools model emits PDDL
# s-expressions `(ontable shaker1)` while the oracle (and the with-tools
# `get_state_transition` result) emit functional `ontable(shaker1)`. Both denote
# the same atom; canonicalise to one space-joined `name arg1 arg2` token so the
# simulate grader's deep-equality compares content, not notation.
_ATOM_RE = re.compile(r"^\(?\s*([a-z0-9_\-]+)\s*\(?\s*([^()]*)\)?\s*\)?$")


def _canon_atom(s) -> str:
    """Canonicalise one predicate / fluent-key / action string.

    `(name a b)`, `name(a, b)`, `(handempty)`, `handempty` and `handempty()` all
    map to `"name a b"` / `"handempty"`. Argument *order* is preserved — it is
    semantically load-bearing (`on(a,b) != on(b,a)`). A string that does not
    match the atom shape falls back to the prior whitespace-collapsed,
    lower-cased form, so a genuinely-wrong trajectory still mismatches: the
    bridge reconciles notation, it never silently widens equality. Idempotent.
    """
    t = " ".join(str(s).split()).lower()
    m = _ATOM_RE.match(t)
    if not m:
        return t
    name, rest = m.group(1), m.group(2).strip()
    args = [a for a in re.split(r"[\s,]+", rest) if a]
    return " ".join([name, *args])


def _normalize_trajectory(traj) -> list[dict] | None:
    """Canonicalise a trajectory list to a comparable shape.

    Bridges three field-shape variants (PR-4):
      - oracle (`get_state_transition` plugin): per step
        `{step, action, boolean_fluents: dict[str, bool], numeric_fluents: dict}`.
        `boolean_fluents` is the full predicate map; `action` is None on step 0.
      - model (no-PDDL-tools `format=SimulateResponse`): per step
        `{step, action, state: {boolean: list[str], numeric: dict}}`.
        `boolean` is the list of TRUE predicates only.
      - bare/legacy: per step `{step, action, boolean: list, numeric: dict}`.

    All three collapse to `{step, action, boolean, numeric}` where
    `boolean` is a sorted list of TRUE predicate strings and `numeric` is
    a dict[str, float]. Predicate strings, numeric keys, and the action
    are each run through `_canon_atom`, so s-expression `(on a b)` and
    functional `on(a, b)` notation compare equal (notation is bridged;
    argument order and content are not). None or missing `action` becomes
    "". Equality of two normalised trajectories is the grader's success
    signal.

    Returns None when *traj* is not a list or any entry has the wrong
    shape — callers tag this as FR_FORMAT_PARSE_FAIL (model side) or
    FR_UNKNOWN (oracle side; see check_success).
    """
    if not isinstance(traj, list):
        return None
    out: list[dict] = []
    for entry in traj:
        if not isinstance(entry, dict):
            return None
        # If a `state` key is present, it MUST be a dict (model schema is
        # `state: StateSnapshot`). A non-dict `state` is malformed model
        # output that the format constraint failed to reject — refuse to
        # silently canonicalise it to an empty state, which would be a
        # false-positive equality match against an empty oracle init.
        if "state" in entry and not isinstance(entry["state"], dict):
            return None
        nested = entry.get("state")
        if isinstance(nested, dict):
            booleans = nested.get("boolean")
            numerics = nested.get("numeric") or {}
        else:
            booleans = entry.get("boolean_fluents")
            if booleans is None:
                booleans = entry.get("boolean")
            numerics = entry.get("numeric_fluents")
            if numerics is None:
                numerics = entry.get("numeric") or {}

        if isinstance(booleans, dict):
            # Oracle shape: every predicate with its truth value. Keep only
            # true entries to match the model-side {true predicates} list.
            boolean_items = [k for k, v in booleans.items() if v]
        elif isinstance(booleans, list):
            boolean_items = booleans
        elif booleans is None:
            boolean_items = []
        else:
            return None
        if not isinstance(numerics, dict):
            return None

        boolean_canon = sorted(_canon_atom(b) for b in boolean_items)
        numeric_canon: dict[str, float] = {}
        for k, v in numerics.items():
            try:
                numeric_canon[_canon_atom(k)] = float(v)
            except (TypeError, ValueError):
                return None
        action_raw = entry.get("action")
        action_canon = "" if action_raw is None else _canon_atom(action_raw)
        out.append({
            "step": entry.get("step"),
            "action": action_canon,
            "boolean": boolean_canon,
            "numeric": numeric_canon,
        })
    return out


def _strip_md_fence(raw: str) -> str:
    """Strip a leading ```/```json fence line and any trailing ``` fence.

    Models emit fenced JSON even under a `format=` constraint. Stripping a
    known markdown wrapper is NOT prose/regex extraction — the entire
    remaining text must still parse as one JSON value. Shared by
    `_safe_pydantic_validate` and the Q1 `_coerce_simulate_trajectory` so both
    tolerate fences identically.
    """
    text = raw.strip()
    if text.startswith("```"):
        nl = text.find("\n")
        if nl >= 0:
            text = text[nl + 1:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _validate_model(model_cls, data):
    """pydantic-validate already-parsed JSON data; return instance or None.

    Mirrors `_safe_pydantic_validate`'s broad catch but takes a parsed value
    (dict/list) rather than a raw string, so the Q1 coercion whitelist can try
    multiple target shapes against one parse without re-serialising.
    """
    try:
        return model_cls.model_validate(data)
    except Exception:
        return None


def _safe_pydantic_validate(model_cls, raw: str):
    """Try to JSON-parse + pydantic-validate; return instance or None.

    Used in no-PDDL-tools grading to attempt the structured path before
    falling back to free-text extractors. Tolerates raw strings wrapped
    in markdown code fences (```json ... ```), which some models emit
    even under `format=` constraint.
    """
    if not isinstance(raw, str):
        return None
    data = _safe_json_loads(_strip_md_fence(raw))
    if data is None:
        return None
    return _validate_model(model_cls, data)


# Q1 two-metric simulate grader (2026-06-25; pre-registered in
# development/simulate_decisions_and_next_steps.md + q1_grader_plan.md).
#
# The pre-PR grader required the no-tools simulate output to validate as the
# schema-exact {"trajectory":[...]} wrapper; a clean top-level step list or a
# single step object — content possibly correct — was binned FR_FORMAT_PARSE_FAIL
# (the "strict-wrapper sub-artifact"). The bounded-coercion whitelist below
# separates two metrics: state-tracking accuracy (the primary `success`, graded
# on coerced content) and format-compliance (did the output emit the exact
# wrapper). FROZEN rules — never widen without a dated decision:
#   1. parse the ENTIRE output as ONE JSON value (markdown fence tolerated);
#      no prose/regex extraction, ever;
#   2. dict with `trajectory` key -> SimulateResponse -> compliant=True;
#   3. bare top-level list -> wrap -> list[StateStep] -> accept (not compliant);
#   4. single dict that is a valid StateStep -> wrap -> accept (not compliant);
#   5. anything else -> parse-fail. Never invent or repair a field.


def _coerce_simulate_trajectory(response) -> tuple[list[dict] | None, bool]:
    """Bounded wrapper-tolerant parse for no-tools simulate (Q1 whitelist).

    Returns `(trajectory_steps, format_compliant)`:
      * `trajectory_steps` — list of `StateStep.model_dump()` dicts ready for
        `_normalize_trajectory`, or `None` iff the output is not coercible
        (caller tags `FR_FORMAT_PARSE_FAIL`).
      * `format_compliant` — `True` only when the output was the schema-exact
        `{"trajectory":[...]}` wrapper (rule 2); the coerced list/single-step
        shapes are accepted but NOT compliant.
    """
    if not isinstance(response, str):
        return None, False
    data = _safe_json_loads(_strip_md_fence(response))
    if data is None:
        return None, False
    # Rule 2: schema-exact wrapper. A present `trajectory` key signals intent
    # to comply, so a malformed one is a parse-fail (NOT a fall-through to the
    # single-step rule) — we never repair it.
    if isinstance(data, dict) and "trajectory" in data:
        parsed = _validate_model(SimulateResponse, data)
        if parsed is None:
            return None, False
        return [s.model_dump() for s in parsed.trajectory], True
    # Rule 3: bare top-level list of valid steps -> wrap.
    if isinstance(data, list):
        parsed = _validate_model(SimulateResponse, {"trajectory": data})
        if parsed is None:
            return None, False
        return [s.model_dump() for s in parsed.trajectory], False
    # Rule 4: single valid step object -> wrap.
    if isinstance(data, dict):
        step = _validate_model(StateStep, data)
        if step is None:
            return None, False
        return [step.model_dump()], False
    # Rule 5: JSON scalar / anything else -> not coercible.
    return None, False


def simulate_format_compliant(response) -> bool:
    """Format-compliance metric: True iff a no-tools simulate response emitted
    the schema-exact `{"trajectory":[...]}` wrapper (coerced shapes and
    parse-fails are False). Pure; shares `_coerce_simulate_trajectory` with
    `check_success` so the two metrics can never drift. Callers only invoke
    this for no-tools simulate trials; `TaskResult.format_compliant` stays
    `None` (not applicable) elsewhere.
    """
    _steps, compliant = _coerce_simulate_trajectory(response)
    return compliant


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
    """Validate a model-emitted plan via the validator MCP tool.

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
            "validate_plan",
            {"domain": domain_pddl, "problem": problem_pddl, "plan": plan_str},
        )
    except Exception:
        return None
    return _parse_validation_verdict(raw)


_TOOL_ERROR_PREFIXES = ("Tool error", "Error executing tool")


def _tool_error_seen(tool_calls: list[dict], name: str) -> bool:
    """True if any call to *name* failed.

    Three error shapes are recognized:
      - MCP transport errors, surfaced as strings prefixed with "Tool error".
      - FastMCP argument-validation errors, surfaced as strings prefixed with
        "Error executing tool" (e.g. model omits a required pydantic field,
        or wraps args as `_raw_arguments`). Without this branch the unparseable
        result falls through to FR_VERDICT_MISMATCH / FR_RESULT_MISMATCH and
        gets credited to the model as a confident-wrong prediction.
      - Plugin-side errors, returned as JSON like {"error": true, "message": ...}.
        The pddl-solver / pddl-validator plugins use this shape for things
        like bad arguments, missing files, planner timeouts, etc.
    """
    for tc in tool_calls:
        if tc.get("name") != name:
            continue
        raw = tc.get("result", "")
        if isinstance(raw, str) and raw.startswith(_TOOL_ERROR_PREFIXES):
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
    Without-tools (PR-4: now "no-PDDL-tools" — the model still has
    Ollama `format=<json_schema>` constraint enforcement, but no
    planning/validation/simulation MCP tools): grade the structured JSON
    artifact when present, fall back to free-text extractors when JSON
    parse fails (`FR_FORMAT_PARSE_FAIL` only when both paths fail):
      - solve           → SolveResponse.plan → pyvalidator, require valid==True
      - validate_*      → ValidateResponse.verdict → compare to ground truth
      - simulate        → SimulateResponse.trajectory → normalize and deep-equal
                          against oracle gt["trace"].trajectory
    """
    # With-tools but the model emitted zero tool calls → it answered from
    # the text alone, which is tool_not_selected regardless of how plausible
    # the text is. Without this short-circuit the per-task branches would
    # fall through to the no-tools grading path and return tool_selected=None,
    # violating the documented schema (EXPERIMENTS_FLOW.md §4.1/§9).
    if with_tools and not tool_calls:
        return False, False, FR_TOOL_NOT_SELECTED

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
        # PR-4: structured-output path first (Ollama `format=SolveResponse`),
        # free-text extractor as fallback. Both routed through the same
        # _validate_model_plan call so the grading rule is identical to the
        # pre-PR-4 behaviour once a plan list is in hand.
        parsed = _safe_pydantic_validate(SolveResponse, response or "")
        plan_lines = parsed.plan if parsed else extract_plan_lines(response or "")
        verdict = await _validate_model_plan(mcp, domain_pddl, problem_pddl, plan_lines)
        if verdict is True:
            return None, True, FR_OK
        if verdict is None:
            return None, False, FR_TOOL_ERROR
        if not plan_lines:
            # Distinguish "couldn't extract anything" (parse failure on
            # both JSON and free-text paths) from "model emitted clean
            # JSON with an empty plan" (model gave up under a successful
            # format constraint). The latter is a genuine plan invalidity
            # signal, not a parse failure.
            return None, False, FR_PLAN_INVALID if parsed is not None else FR_FORMAT_PARSE_FAIL
        return None, False, FR_PLAN_INVALID

    if task in ("validate_domain", "validate_problem", "validate_plan"):
        gt_key = {
            "validate_domain": "domain_valid",
            "validate_problem": "problem_valid",
            "validate_plan": "plan_valid",
        }[task]
        truth = gt.get(gt_key)

        if tool_calls:
            # Task name == expected validator-tool name (1:1 since the
            # marketplace 1.4.0 split). Three failure modes are now
            # distinguished — see the FR vocabulary comment block above.
            if _used_tool(tool_calls, task):
                if truth is None:
                    return True, False, FR_UNKNOWN
                for tc in tool_calls:
                    if tc.get("name") != task:
                        continue
                    verdict = _parse_validation_verdict(tc.get("result", ""))
                    if verdict == truth:
                        return True, True, FR_OK
                if _tool_error_seen(tool_calls, task):
                    return True, False, FR_TOOL_ERROR
                return True, False, FR_VERDICT_MISMATCH
            if any(tc.get("name") in _VALIDATE_TOOL_NAMES for tc in tool_calls):
                return False, False, FR_WRONG_TOOL
            return False, False, FR_TOOL_NOT_SELECTED

        # PR-4: try structured ValidateResponse.verdict first, then the
        # free-text VERDICT: regex as fallback. FR_FORMAT_PARSE_FAIL only
        # fires when neither path produces a verdict.
        parsed = _safe_pydantic_validate(ValidateResponse, response or "")
        if parsed is not None:
            verdict: bool | None = parsed.verdict == "VALID"
        else:
            verdict = extract_verdict(response or "")
            if verdict is None:
                return None, False, FR_FORMAT_PARSE_FAIL
        if truth is None:
            return None, False, FR_UNKNOWN
        if verdict == truth:
            return None, True, FR_OK
        return None, False, FR_VERDICT_MISMATCH

    if task == "simulate":
        # Both branches normalise via _normalize_trajectory so the no-PDDL-
        # tools (PR-4) and with-tools paths share one canonical-form
        # equality rule (Risks list — "Simulate trajectory normalization
        # mismatch" mitigation).
        oracle_trace = _safe_json_loads(gt.get("trace"))
        oracle_traj = oracle_trace.get("trajectory") if isinstance(oracle_trace, dict) else None
        oracle_canon = _normalize_trajectory(oracle_traj)

        if tool_calls:
            selected = _used_tool(tool_calls, "get_state_transition")
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            # `valid` in the tool response is a PDDL-syntactic check, not a
            # simulation-correctness signal — a partial trajectory with
            # valid=false would satisfy it.
            if oracle_canon is None:
                return True, False, FR_UNKNOWN
            for raw in _get_tool_results(tool_calls, "get_state_transition"):
                parsed = _safe_json_loads(raw)
                if not isinstance(parsed, dict) or parsed.get("error"):
                    continue
                if _normalize_trajectory(parsed.get("trajectory")) == oracle_canon:
                    return True, True, FR_OK
            if _tool_error_seen(tool_calls, "get_state_transition"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_RESULT_MISMATCH

        # PR-4 / Q1 (2026-06-25): no-PDDL-tools simulate. Bounded
        # wrapper-tolerant parse via `_coerce_simulate_trajectory` — the ENTIRE
        # output must be one JSON value; the schema-exact {"trajectory":[...]}
        # wrapper, a bare top-level step list, or a single step object are all
        # accepted (state-tracking is graded on content), anything else is
        # FR_FORMAT_PARSE_FAIL. No free-text fallback (ISS-002). `success`
        # returned here is STATE-TRACKING accuracy (the primary metric);
        # format-compliance is the SEPARATE `simulate_format_compliant` /
        # `TaskResult.format_compliant` channel.
        if oracle_canon is None:
            return None, False, FR_UNKNOWN
        model_steps, _compliant = _coerce_simulate_trajectory(response or "")
        if model_steps is None:
            return None, False, FR_FORMAT_PARSE_FAIL
        if not model_steps:
            # Coerced cleanly to an empty trajectory (e.g. {"trajectory": []}).
            # Distinct from a wrong trajectory — and FR_SIMULATE_EMPTY is a
            # truncation-override reason, so a budget cut-off is relabelled.
            return None, False, FR_SIMULATE_EMPTY
        model_canon = _normalize_trajectory(model_steps)
        if model_canon is None:
            return None, False, FR_FORMAT_PARSE_FAIL
        if model_canon == oracle_canon:
            return None, True, FR_OK
        return None, False, FR_RESULT_MISMATCH

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
    FR_FORMAT_PARSE_FAIL,
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


# Reasons that *could* be the legacy-empty-output bucket — the runtime
# classifier emits FR_TRUNCATED_NO_ANSWER for these via _apply_truncation_override,
# so they're the only ones a read-time relabel can confidently re-bucket.
_LEGACY_RELABEL_CANDIDATES = (FR_TRUNCATED_NO_ANSWER,) + _TRUNCATION_OVERRIDE_REASONS


def relabel_truncated_taxonomy(
    failure_reason: str,
    *,
    truncated: bool,
    response: str,
    think_mode: str,
    decoupled: bool = False,
) -> str:
    """Read-time relabel: split FR_TRUNCATED_NO_ANSWER into think_overflow vs
    truncated_no_answer based on whether the model emitted any visible response.

    Pure, side-effect-free. Used by analyzers (summary.py, build_deck.py) to
    re-bucket counts when reading legacy trials produced before the runtime
    predicate fix lands. Does NOT mutate trials.jsonl. The runtime classifier
    in `_classify_step_failure` is intentionally unchanged here so a sweep
    that's still in flight keeps a homogeneous corpus identity.

    Predicate:
        truncated AND failure_reason ∈ {truncated_no_answer, plan_invalid,
            no_verdict_parsed, simulate_empty, format_parse_fail, unknown}
        AND response == "" AND think_mode == "on"
        → FR_THINK_OVERFLOW

    The think_mode gate avoids tagging think=off rows where an empty-response
    truncation has no reasoning-spiral explanation (the small Qwen3.5 sizes
    occasionally hit this; ~0.34% of trials).

    `decoupled=True` (decoupled-budget think=on corpus — caller passes it per
    row via `TaskResult.think_truncated is not None`) DISABLES this relabel:
    an empty-answer truncation there is an answer-budget cap-hit, not a
    reasoning spiral, so it must stay FR_TRUNCATED_NO_ANSWER (mirrors the
    write-time guard in `_classify_step_failure`).
    """
    if decoupled:
        return failure_reason
    if not truncated:
        return failure_reason
    if failure_reason not in _LEGACY_RELABEL_CANDIDATES:
        return failure_reason
    if (response or "").strip():
        return failure_reason
    if think_mode != "on":
        return failure_reason
    return FR_THINK_OVERFLOW


_ARG_ERROR_RELABEL_CANDIDATES = frozenset({
    FR_VERDICT_MISMATCH,
    FR_RESULT_MISMATCH,
    FR_PLAN_INVALID,
})

_ARG_ERROR_TOOL_NAMES_BY_TASK: dict[str, tuple[str, ...]] = {
    "validate_plan": ("validate_plan",),
    "validate_domain": ("validate_domain",),
    "validate_problem": ("validate_problem",),
    "simulate": ("get_state_transition",),
    "solve": ("classic_planner", "numeric_planner"),
}


def relabel_tool_arg_error_taxonomy(
    failure_reason: str,
    *,
    task: str,
    tool_calls: list[dict],
) -> str:
    """Read-time relabel: FastMCP arg-validation errors mis-binned as
    FR_VERDICT_MISMATCH / FR_RESULT_MISMATCH / FR_PLAN_INVALID get moved to
    FR_TOOL_ERROR.

    Mirrors `relabel_truncated_taxonomy`: pure, side-effect-free, used by
    analyzers (build_deck.py) to recover trials emitted before the runtime
    `_tool_error_seen` recognized the "Error executing tool ..." prefix. Does
    NOT mutate trials.jsonl. The runtime classifier in `check_success` now
    bins the same shape as FR_TOOL_ERROR going forward; this relabel is for
    in-flight / legacy corpora only.

    Predicate:
        failure_reason ∈ {verdict_mismatch, result_mismatch, plan_invalid}
        AND task is in the known task→tool map
        AND some tool_call for one of the task-relevant tool names has a
            result string prefixed with one of `_TOOL_ERROR_PREFIXES`
        → FR_TOOL_ERROR
    """
    if failure_reason not in _ARG_ERROR_RELABEL_CANDIDATES:
        return failure_reason
    names = _ARG_ERROR_TOOL_NAMES_BY_TASK.get(task)
    if not names:
        return failure_reason
    for tc in tool_calls or ():
        if tc.get("name") not in names:
            continue
        raw = tc.get("result", "")
        if isinstance(raw, str) and raw.startswith(_TOOL_ERROR_PREFIXES):
            return FR_TOOL_ERROR
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
    decoupled: bool = False,
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

    The `thinking_text`/`response_text`/`error` kwargs default to empty
    strings; callers that don't pass them skip the FR_THINK_OVERFLOW step.

    `decoupled=True` (decoupled-budget think=on path) SUPPRESSES the
    FR_THINK_OVERFLOW step: there `thinking_text` is the *completed* reasoning
    fed to the answer phase and `done_reason` is the ANSWER phase's, so an
    empty-answer length-truncation is an ANSWER-budget cap-hit
    (FR_TRUNCATED_NO_ANSWER), NOT a reasoning spiral. The reasoning-cap signal
    is carried separately in `TaskResult.think_truncated`. Without this guard
    the path would mislabel the exact phenomenon it exists to drive down.
    """
    if (not decoupled
        and not success
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
