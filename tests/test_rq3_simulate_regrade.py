"""Unit tests for the pure helpers of tools/reanalysis/rq3_simulate_regrade.py (no results data)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pddl_eval.scoring import _normalize_trajectory  # noqa: E402
from tools.delivered_rerun import e4 as E4  # noqa: E402
from tools.reanalysis import rq3_context_pilot as P  # noqa: E402
from tools.reanalysis import rq3_simulate_regrade as Q  # noqa: E402

STEPS = [
    {"step": 0, "action": "", "state": {"boolean": ["(clear a)", "(ontable a)", "(handempty)"],
                                        "numeric": {}}},
    {"step": 1, "action": "(pick_up a)", "state": {"boolean": ["(holding a)"], "numeric": {}}},
    {"step": 2, "action": "(put_down a)",
     "state": {"boolean": ["(clear a)", "(ontable a)", "(handempty)"], "numeric": {}}},
]
ORACLE = _normalize_trajectory(STEPS)
# what get_state_transition returns: every predicate with true or false
TOOL = {"trajectory": [
    {"step": 0, "action": None, "boolean_fluents": {"clear(a)": True, "ontable(a)": True,
                                                    "handempty": True, "holding(a)": False},
     "numeric_fluents": {}},
    {"step": 1, "action": "(pick_up a)",
     "boolean_fluents": {"clear(a)": False, "ontable(a)": False, "handempty": False,
                         "holding(a)": True}, "numeric_fluents": {}},
    {"step": 2, "action": "(put_down a)",
     "boolean_fluents": {"clear(a)": True, "ontable(a)": True, "handempty": True,
                         "holding(a)": False}, "numeric_fluents": {}},
]}


def row(response, done_reason="stop"):
    call = SimpleNamespace(name="get_state_transition", arguments={}, result=json.dumps(TOOL))
    return SimpleNamespace(response=response, done_reason=done_reason, tool_calls=(call,))


def as_array(steps):
    return "```json\n" + json.dumps(steps) + "\n```"


def as_lines(steps):
    return "The trace:\n" + "\n".join(json.dumps(s) for s in steps)


def changed(i, boolean):
    out = json.loads(json.dumps(STEPS))
    out[i]["state"]["boolean"] = boolean
    return out


def test_the_tool_map_fixture_is_the_answer_key():
    assert _normalize_trajectory(TOOL["trajectory"]) == ORACLE
    assert Q.tool_maps(row(""))[1] == {"clear a": False, "ontable a": False,
                                       "handempty": False, "holding a": True}


def test_line_reader_reads_layout_and_keeps_content_strict():
    assert P.line_reader_exact(as_lines(STEPS), ORACLE)
    assert P.line_reader_steps(as_lines(STEPS)) == ORACLE
    assert not P.line_reader_exact(as_lines(changed(1, ["(holding a)", "(handempty)"])), ORACLE)
    assert P.line_reader_steps("no trace here") is None
    assert not P.line_reader_exact("no trace here", ORACLE)
    assert not P.line_reader_exact(as_lines(STEPS), None)


def test_read_traces_uses_both_readers():
    assert [m for _t, m in Q.read_traces(as_lines(STEPS))] == ["json_lines"]
    assert "fenced_block" in [m for _t, m in Q.read_traces(as_array(STEPS))]
    assert Q.read_traces("the plan works") == []


def test_best_trace_prefers_matches_then_the_key_length():
    short = _normalize_trajectory(STEPS[:2])
    wrong = _normalize_trajectory(changed(1, ["(handempty)"]))
    assert Q.best_trace([(short, "a"), (wrong, "b")], ORACLE)[1] == "b"     # 2 matches each
    assert Q.best_trace([(short, "a"), (ORACLE, "c")], ORACLE)[1] == "c"
    assert Q.best_trace([], ORACLE) is None


@pytest.mark.parametrize("cat", [E4.REFUSED_OR_CLIPPED_FINAL, E4.NO_FINAL_ANSWER])
def test_frozen_no_room_and_empty_come_first(cat):
    c = Q.classify_still_lost(row(as_array(changed(1, []))), cat, ORACLE)
    assert c == {"cls": "no_room_or_empty", "key_from_another_plan": False}


def test_no_room_row_on_a_problem_whose_key_is_another_plans():
    other = _normalize_trajectory(changed(1, ["(handempty)"]))
    c = Q.classify_still_lost(row(""), E4.REFUSED_OR_CLIPPED_FINAL, other)
    assert c == {"cls": "no_room_or_empty", "key_from_another_plan": True}


def test_class_order_after_the_frozen_categories():
    assert Q.classify_still_lost(row("x"), E4.TOOL_INPUT_ERROR, ORACLE)["cls"] == \
        "tool_ran_another_plan"
    assert Q.classify_still_lost(row(as_array(STEPS[:2]), "length"), E4.ABRIDGED,
                                 ORACLE)["cls"] == "cut_at_output_cap"
    assert Q.classify_still_lost(row("| step | state |\n|---|---|"), E4.NEEDS_READING,
                                 ORACLE)["cls"] == "unreadable"
    short = Q.classify_still_lost(row(as_array(STEPS[:2])), E4.ABRIDGED, ORACLE)
    assert short["cls"] == "wrong_length" and short["shorter"] and not short["drops_first_state"]
    tail = Q.classify_still_lost(row(as_lines(STEPS[1:])), E4.NEEDS_READING, ORACLE)
    assert tail["cls"] == "wrong_length" and tail["drops_first_state"]
    # a trace equal to the key cannot be lost; if it ever is, it is reported, not hidden
    assert Q.classify_still_lost(row(as_array(STEPS)), E4.WRONG_FACTS, ORACLE)["cls"] == "other"


def test_false_predicate_listed_as_true_is_conversion_only():
    ans = changed(1, ["(holding a)", "(handempty)"])          # handempty is false in the tool's map
    c = Q.classify_still_lost(row(as_lines(ans)), E4.NEEDS_READING, ORACLE)
    assert c["cls"] == "same_length" and c["mode"] == "json_lines"
    assert c["differs_in"] == "facts" and c["conversion_only"]
    assert c["facts_kind"] == "false listed as true"
    assert (c["extra_false_in_map"], c["extra_not_in_map"], c["omitted_true"]) == (1, 0, 0)


def test_true_predicate_left_out_is_conversion_only():
    c = Q.classify_still_lost(row(as_array(changed(2, ["(clear a)", "(ontable a)"]))),
                              E4.WRONG_FACTS, ORACLE)
    assert c["conversion_only"] and c["facts_kind"] == "true omitted" and c["omitted_true"] == 1


def test_predicate_the_tool_never_returned_is_not_conversion_only():
    c = Q.classify_still_lost(row(as_array(changed(1, ["(holding a)", "(on a b)"]))),
                              E4.WRONG_FACTS, ORACLE)
    assert c["cls"] == "same_length" and not c["conversion_only"]
    assert c["facts_kind"] == "lists a predicate the tool's map does not hold"


def test_other_parts_of_a_step():
    twice = Q.classify_still_lost(row(as_array(changed(1, ["(holding a)", "(holding a)"]))),
                                  E4.WRONG_FACTS, ORACLE)
    assert twice["differs_in"] == "a fact listed twice" and not twice["conversion_only"]
    nums = json.loads(json.dumps(STEPS))
    key = json.loads(json.dumps(STEPS))
    for s in key:
        s["state"]["numeric"] = {"(total-cost)": 1}
    left_out = Q.describe_same_length(_normalize_trajectory(nums), _normalize_trajectory(key), None)
    assert left_out["differs_in"] == "numbers" and left_out["numbers_kind"] == "numbers left out"
    nums[2]["state"]["numeric"] = {"(total-cost)": 7}
    wrong = Q.describe_same_length(_normalize_trajectory(nums), _normalize_trajectory(key), None)
    assert wrong["numbers_kind"] == "a number wrong" and not wrong["map"]
    relabel = json.loads(json.dumps(STEPS))
    relabel[1]["action"] = "(pickup a)"
    for i, s in enumerate(relabel):
        s["step"] = i + 1
    d = Q.describe_same_length(_normalize_trajectory(relabel), ORACLE, None)
    assert d["differs_in"] == "step numbers + action"


def test_shifted_by_one_step():
    four = STEPS + [{"step": 3, "action": "(pick_up a)",
                     "state": {"boolean": ["(holding a)"], "numeric": {}}}]
    key = _normalize_trajectory(four)
    late = json.loads(json.dumps(four))
    for i in range(3, 0, -1):
        late[i]["state"] = four[i - 1]["state"]
    d = Q.describe_same_length(_normalize_trajectory(late), key, None)
    assert d["shifted_by_one"]
    assert not Q.describe_same_length(_normalize_trajectory(changed(1, [])), ORACLE,
                                      None)["shifted_by_one"]


def test_hand_read_id_matches_the_stored_ids():
    r = SimpleNamespace(model_tag="Qwen3_5_9B", task="simulate", arm="plain",
                        domain="block-grouping", problem="p03", plan_label="", variant=11)
    assert Q.hand_read_id(r) == "Qwen3_5_9B|simulate|plain|block-grouping|p03||v11"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
