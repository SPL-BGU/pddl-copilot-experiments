"""Unit tests for the pure helpers of tools/reanalysis/rq1_layout_regrade.py (no results data)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.delivered_rerun import constants as C  # noqa: E402
from tools.delivered_rerun import grade as G  # noqa: E402
from tools.reanalysis import rq1_layout_regrade as Q  # noqa: E402

PLAN = ["(unstack b1 b3)", "(put_down b1)", "(pick_up b3)", "(stack b3 b2)"]
REASONING = ("Let me think.\n1. (unstack b1 b3)\n2. (put_down b1)\n3. (pick_up b3)\n"
             "4. (put_down b3)\nThat undoes nothing, so instead:\n")


def fenced(body, tag="json"):
    return f"```{tag}\n{body}\n```"


def test_json_list_and_plan_object_in_the_last_block():
    as_list = REASONING + fenced(json.dumps(PLAN, indent=2))
    as_obj = REASONING + fenced(json.dumps({"plan": PLAN}, indent=2))
    assert Q.block_plan(as_list) == (tuple(PLAN), Q.JSON_BLOCK)
    assert Q.block_plan(as_obj) == (tuple(PLAN), Q.JSON_BLOCK)
    # the frozen grader reads the reasoning lines too, so it sees another plan
    frozen, mode = G.solve_plan(as_obj)
    assert mode in ("strict_lines", "tolerant_lines") and tuple(PLAN) != frozen


def test_json_keeps_case_and_collapses_whitespace():
    plan, kind = Q.block_plan(fenced(json.dumps(["(Take_Image  Star0 cam)"])))
    assert plan == ("(Take_Image Star0 cam)",) and kind == Q.JSON_BLOCK
    assert Q.lower(plan) == ("(take_image star0 cam)",)


def test_action_lines_block_is_read_like_the_frozen_tolerant_reader():
    body = "1. (Unstack b1 b3)\n- `(put_down   b1)` - put it on the table\n(pick_up b3)"
    plan, kind = Q.block_plan("The plan:\n" + fenced(body, tag=""))
    assert kind == Q.LINES_BLOCK
    assert plan == ("(unstack b1 b3)", "(put_down b1)", "(pick_up b3)")


def test_only_the_last_block_counts():
    first = fenced(json.dumps(["(wrong a)"]))
    answer = first + "\nOn reflection:\n" + fenced(json.dumps(PLAN)) + "\nDone."
    assert Q.block_plan(answer)[0] == tuple(PLAN)
    # a last block that is not a plan leaves the answer to the frozen grade
    assert Q.block_plan(fenced(json.dumps(PLAN)) + "\n" + fenced("(define (problem p))",
                                                                 tag="pddl")) is None


def test_what_is_not_a_plan_block():
    assert Q.block_plan("") is None
    assert Q.block_plan(None) is None
    assert Q.block_plan("(unstack b1 b3)\n(put_down b1)") is None          # no fence
    assert Q.block_plan("```json\n" + json.dumps(PLAN)) is None             # fence left open
    assert Q.block_plan(fenced("[]")) is None
    assert Q.block_plan(fenced(json.dumps({"plan": []}))) is None
    assert Q.block_plan(fenced(json.dumps({"steps": PLAN}))) is None
    assert Q.block_plan(fenced(json.dumps([1, 2]))) is None
    assert Q.block_plan(fenced(json.dumps(["(a b)", " "]))) is None
    assert Q.block_plan(fenced(json.dumps(["b1", "b2"]))) is None           # not actions
    assert Q.block_plan(fenced(json.dumps(["1. (a b)"]))) is None
    assert Q.block_plan(fenced("(pick_up b3)\nthen stack it")) is None      # a prose line


def test_the_leaked_prefix_is_stripped_first():
    assert Q.block_plan(C.LEAKED_PREFIX + fenced(json.dumps(PLAN)))[0] == tuple(PLAN)


def test_paired_diff_counts_both_directions():
    a = [True, False, False, True]
    b = [True, True, True, False]
    d = Q.paired_diff(a, b, ["d1", "d1", "d2", "d2"])
    assert d["wrong_to_right"] == 2 and d["right_to_wrong"] == 1
    assert abs(d["est"] - 25.0) < 1e-9
