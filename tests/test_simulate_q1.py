"""Unit tests for the Q1 two-metric simulate grader (2026-06-25).

Run standalone: `python3 tests/test_simulate_q1.py`
Or via the shell wrapper: `bash tests/verify.sh`

Covers the frozen bounded-coercion whitelist (`_coerce_simulate_trajectory`),
the `simulate_format_compliant` metric, and the no-tools simulate branch of
`check_success` end-to-end (no MCP needed — that path never calls a tool).
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from pddl_eval.scoring import (
    FR_FORMAT_PARSE_FAIL,
    FR_OK,
    FR_RESULT_MISMATCH,
    FR_SIMULATE_EMPTY,
    _coerce_simulate_trajectory,
    check_success,
    simulate_format_compliant,
)


# --- fixtures: a tiny 2-step oracle + matching model trajectory ---------------

_ORACLE = {
    "trajectory": [
        {"step": 0, "action": None, "boolean_fluents": {"(ontable a)": True}, "numeric_fluents": {}},
        {"step": 1, "action": "(pick-up a)", "boolean_fluents": {"(holding a)": True}, "numeric_fluents": {}},
    ]
}
_GT = {"trace": json.dumps(_ORACLE)}

_STEPS = [
    {"step": 0, "action": "", "state": {"boolean": ["(ontable a)"], "numeric": {}}},
    {"step": 1, "action": "(pick-up a)", "state": {"boolean": ["(holding a)"], "numeric": {}}},
]
_WRAPPED = json.dumps({"trajectory": _STEPS})       # rule 2 — compliant
_BARE_LIST = json.dumps(_STEPS)                       # rule 3 — coerced
_SINGLE = json.dumps(_STEPS[0])                       # rule 4 — coerced


def _grade(response):
    return asyncio.run(check_success(
        "simulate", response, [], _GT, None, "", "", with_tools=False,
    ))


def test_coerce_rule2_wrapper(r: TestResults) -> None:
    steps, compliant = _coerce_simulate_trajectory(_WRAPPED)
    r.check_eq("wrapper compliant", compliant, True)
    r.check_eq("wrapper step count", len(steps), 2)


def test_coerce_rule3_bare_list(r: TestResults) -> None:
    steps, compliant = _coerce_simulate_trajectory(_BARE_LIST)
    r.check_eq("bare list accepted", len(steps), 2)
    r.check_eq("bare list NOT compliant", compliant, False)


def test_coerce_rule4_single_step(r: TestResults) -> None:
    steps, compliant = _coerce_simulate_trajectory(_SINGLE)
    r.check_eq("single step wrapped to len 1", len(steps), 1)
    r.check_eq("single step NOT compliant", compliant, False)


def test_coerce_fence_tolerant(r: TestResults) -> None:
    fenced = "```json\n" + _WRAPPED + "\n```"
    steps, compliant = _coerce_simulate_trajectory(fenced)
    r.check_eq("fenced wrapper accepted", len(steps), 2)
    r.check_eq("fenced wrapper still compliant", compliant, True)


def test_coerce_rule5_prose_fails(r: TestResults) -> None:
    prose = "Here is the trajectory:\n" + _WRAPPED
    steps, compliant = _coerce_simulate_trajectory(prose)
    r.check_eq("prose-wrapped -> parse-fail", steps, None)
    r.check_eq("prose-wrapped not compliant", compliant, False)


def test_coerce_never_repairs(r: TestResults) -> None:
    # A step missing the required `state` field must NOT be coerced to validity.
    broken = json.dumps([{"step": 0, "action": ""}])
    steps, _c = _coerce_simulate_trajectory(broken)
    r.check_eq("missing-field step -> parse-fail", steps, None)
    # A dict carrying a `trajectory` key but a malformed value is a parse-fail,
    # NOT a fall-through to the single-step rule.
    malformed_wrapper = json.dumps({"trajectory": "not a list"})
    steps2, _c2 = _coerce_simulate_trajectory(malformed_wrapper)
    r.check_eq("malformed wrapper -> parse-fail", steps2, None)


def test_coerce_scalar_and_nonstring(r: TestResults) -> None:
    r.check_eq("json scalar -> parse-fail", _coerce_simulate_trajectory("42")[0], None)
    r.check_eq("non-string -> parse-fail", _coerce_simulate_trajectory(None)[0], None)


def test_format_compliant_helper(r: TestResults) -> None:
    r.check_eq("wrapper compliant", simulate_format_compliant(_WRAPPED), True)
    r.check_eq("bare list not compliant", simulate_format_compliant(_BARE_LIST), False)
    r.check_eq("prose not compliant", simulate_format_compliant("nope " + _WRAPPED), False)


def test_check_success_wrapper_correct(r: TestResults) -> None:
    tool_sel, success, fr = _grade(_WRAPPED)
    r.check_eq("no-tools -> tool_selected None", tool_sel, None)
    r.check_eq("wrapper+correct success", success, True)
    r.check_eq("wrapper+correct FR_OK", fr, FR_OK)


def test_check_success_bare_list_correct(r: TestResults) -> None:
    # The headline Q1 win: a clean top-level list of correct steps now SUCCEEDS
    # (state-tracking) where the strict-wrapper grader binned it format_parse_fail.
    _ts, success, fr = _grade(_BARE_LIST)
    r.check_eq("bare-list correct -> success", success, True)
    r.check_eq("bare-list correct -> FR_OK", fr, FR_OK)
    r.check_eq("but compliance is False", simulate_format_compliant(_BARE_LIST), False)


def test_check_success_wrong_content_mismatch(r: TestResults) -> None:
    wrong = json.dumps({"trajectory": [
        {"step": 0, "action": "", "state": {"boolean": ["(holding a)"], "numeric": {}}},
    ]})
    _ts, success, fr = _grade(wrong)
    r.check_eq("wrong content not success", success, False)
    r.check_eq("wrong content -> result_mismatch", fr, FR_RESULT_MISMATCH)


def test_check_success_prose_parse_fail(r: TestResults) -> None:
    _ts, success, fr = _grade("The trajectory is: " + _WRAPPED)
    r.check_eq("prose not success", success, False)
    r.check_eq("prose -> format_parse_fail", fr, FR_FORMAT_PARSE_FAIL)


def test_check_success_empty_trajectory(r: TestResults) -> None:
    _ts, success, fr = _grade(json.dumps({"trajectory": []}))
    r.check_eq("empty not success", success, False)
    r.check_eq("empty -> simulate_empty", fr, FR_SIMULATE_EMPTY)


if __name__ == "__main__":
    r = TestResults("test_simulate_q1")
    test_coerce_rule2_wrapper(r)
    test_coerce_rule3_bare_list(r)
    test_coerce_rule4_single_step(r)
    test_coerce_fence_tolerant(r)
    test_coerce_rule5_prose_fails(r)
    test_coerce_never_repairs(r)
    test_coerce_scalar_and_nonstring(r)
    test_format_compliant_helper(r)
    test_check_success_wrapper_correct(r)
    test_check_success_bare_list_correct(r)
    test_check_success_wrong_content_mismatch(r)
    test_check_success_prose_parse_fail(r)
    test_check_success_empty_trajectory(r)
    r.report_and_exit()
