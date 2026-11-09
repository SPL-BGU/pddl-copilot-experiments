"""Tests for the ISS-027 checks (tools/reanalysis/iss027_common.py, iss027_unaided.py,
iss027_replay.py).

No results data and no validator needed: the pure helpers are tested directly, and
the committed outputs (tools/reanalysis/out/iss027_*.json) are checked against the
figures reproduced in the review of PR #130 and against the committed NUMBERS.md
block files. The scripts' own self-checks cover the data path.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools" / "reanalysis"))
import iss027_common as C  # noqa: E402
import iss027_replay as RP  # noqa: E402
import iss027_unaided as UN  # noqa: E402

OUT = REPO / "tools" / "reanalysis" / "out"


def _load():
    return (json.loads((OUT / "iss027_replay.json").read_text()),
            json.loads((OUT / "iss027_unaided.json").read_text()))


# ------------------------------------------------------------------ pure helpers
def test_affected_and_arms():
    assert C.affected("satellite", "p02") and C.affected("pogo_stick", "p01")
    assert not C.affected("satellite", "p01") and not C.affected("blocksworld", "p02")
    assert C.arm_of({"with_tools": False, "prompt_variant": 12}) == "unaided"
    assert C.arm_of({"with_tools": True, "prompt_variant": 13}) == "plain"
    assert C.arm_of({"with_tools": True, "prompt_variant": 14}) == "steered"


def test_at_cap_uses_the_flag_first_then_the_corpus_cap():
    assert C.at_cap({"response": "x" * 500}, "sweep5v2-live")
    assert not C.at_cap({"response": "x" * 503}, "sweep5v2-live")     # the resumed 9B row
    assert not C.at_cap({"response": "x" * 500, "response_truncated_by_storage": False},
                        "delivered-rerun")                              # the two rerun cells
    assert C.at_cap({"response": "", "response_truncated_by_storage": True}, "delivered-rerun")
    assert C.at_cap({"response": "x" * 16384}, "iss024d-e2e-live")
    assert set(C.SNAPSHOT_CAP) == {"sweep5v2-live", "sweep6-live", "iss024d-e2e-live", "delivered-rerun"}


def test_declared_names_and_capitals():
    dom = "(define (domain d) (:action CRAFT_PLANK :parameters ()) ; Comment Word\n)"
    prob = "(define (problem p) (:objects Star0 sat1 - thing))"
    assert C.upper_declared(dom, prob) == {"craft_plank": "CRAFT_PLANK", "star0": "Star0"}
    low = C.declared_lower(dom, prob)
    assert "comment" not in low and "star0" in low
    assert C.writes_capitals(["(turn_to sat1 Star0)"], low)
    assert C.writes_capitals("(Sat1)", low)                    # any declared name written with a capital
    assert not C.writes_capitals(["(turn_to sat1 star0)", "(Unknown x)"], low)


def test_lower_plan_and_has_upper():
    assert C.lower_plan(["(A b)", 3]) == ["(a b)", 3]
    assert C.lower_plan("(A b)\n(C d)") == "(a b)\n(c d)"
    assert C.lower_plan(None) is None
    assert C.has_upper(["(a B)"]) and not C.has_upper("(a b)")


def test_norm_result_masks_the_request_directory():
    a = '{"valid": false, "report": "parse \'/tmp/pddl/33c15ed6/domain.pddl\'"}'
    b = '{"valid": false, "report": "parse \'/var/folders/x/T/iss027_q/0ab91a1d/domain.pddl\'"}'
    assert C.norm_result(a) == C.norm_result(b)
    assert C.norm_result("Error executing tool x") == "Error executing tool x"
    assert C.norm_result(a) != C.norm_result(a.replace("false", "true"))


def test_parse_cell():
    assert C.parse_cell("slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_delivered-rerun") == {
        "model": "gemma4_26b-a4b", "think": "off", "tools": True, "style": "minimal"}
    assert C.parse_cell("slurm_vllm_Qwen3_5_0_8B_on_no-tools")["tools"] is False
    with pytest.raises(ValueError):
        C.parse_cell("not_a_cell")


def test_fixture_scan_finds_exactly_the_affected_files():
    assert set(C.upper_case_fixtures(REPO / "domains")) == C.expected_upper_files()
    assert C.upper_case_fixtures(REPO / "domains-anon") == {}


def test_check_environment():
    env = {"pyval": "0.1.5", "validator_server_modified": False}
    assert C.check_environment(env) == []
    assert C.check_environment({**env, "pyval": "0.1.6"})
    assert C.check_environment({**env, "validator_server_modified": True})


def test_at_cap_candidate_needs_plan_invalid_json_and_a_capital():
    declared = {"star0", "sat1", "turn_to"}
    row = {"success": False, "failure_reason": "plan_invalid",
           "response": '{\n  "plan": [\n    "(turn_to sat1 Star0)",\n    "(tu'}
    assert UN.at_cap_candidate(row, declared)
    assert not UN.at_cap_candidate({**row, "failure_reason": "format_parse_fail"}, declared)
    assert not UN.at_cap_candidate({**row, "failure_reason": "truncated_no_answer"}, declared)
    assert not UN.at_cap_candidate({**row, "success": True}, declared)
    assert not UN.at_cap_candidate({**row, "response": "(turn_to sat1 Star0)"}, declared)   # not JSON
    assert not UN.at_cap_candidate({**row, "response": row["response"].replace("Star0", "star0")}, declared)


def test_harness_pass_matches_the_with_tools_rule():
    assert RP.harness_pass("validate_plan", ['{"valid": true}'], True, None)
    assert not RP.harness_pass("validate_plan", ['{"valid": false, "status": "STRUCTURE_ERROR"}'], True, None)
    assert not RP.harness_pass("validate_plan", ['{"valid": true}'], None, None)   # no answer key
    assert not RP.harness_pass("simulate", ['{"trajectory": []}'], None, None)     # no oracle
    assert not RP.harness_pass("simulate", ['{"error": true, "trajectory": []}'], None, [])


def test_known_difference_differs_only_in_report():
    a = {"valid": False, "status": "SYNTAX_ERROR", "report": "x"}
    assert RP.same_but_report(a, {**a, "report": "y"})
    assert not RP.same_but_report(a, {**a, "status": "STRUCTURE_ERROR"})
    assert not RP.same_but_report("text", a)
    assert len(RP.KNOWN_DIFFERENCES) == 1


# ------------------------------------------------------------------ committed outputs
# The figures reproduced in the review of PR #130 (2026-11-09).
EXPECTED_TOOL = {  # (corpus, model, think, task, arm): (n, stored k, added)
    ("sweep5v2-live", "gemma4_26b-a4b", "off", "simulate", "plain"): (300, 275, 10),
    ("sweep5v2-live", "gemma4_26b-a4b", "off", "simulate", "steered"): (300, 272, 10),
    ("sweep5v2-live", "gemma4_26b-a4b", "on", "simulate", "plain"): (300, 132, 6),
    ("sweep5v2-live", "gemma4_26b-a4b", "on", "simulate", "steered"): (300, 273, 2),
    ("delivered-rerun", "gemma4_26b-a4b", "off", "simulate", "plain"): (300, 272, 9),
    ("delivered-rerun", "gemma4_26b-a4b", "off", "simulate", "steered"): (300, 272, 9),
    ("delivered-rerun", "qwen3_6_35b", "off", "simulate", "plain"): (300, 282, 2),
    ("delivered-rerun", "qwen3_6_35b", "off", "simulate", "steered"): (300, 287, 2),
    ("iss024d-e2e-live", "gemma4_26b-a4b", "on", "simulate", "plain"): (300, 132, 4),
    ("iss024d-e2e-live", "gemma4_26b-a4b", "on", "simulate", "steered"): (300, 276, 3),
}
EXPECTED_UNAIDED = {  # (model, think): (stored k of 300, low, high)
    ("Qwen3_5_9B", "off"): (32, 2, 2), ("Qwen3_5_9B", "on"): (81, 1, 5),
    ("qwen3_6_35b", "on"): (115, 6, 7), ("qwen3_6_35b", "off"): (28, 0, 0),
    ("gemma4_26b-a4b", "off"): (23, 0, 0), ("gemma4_26b-a4b", "on"): (11, 0, 0),
    ("Qwen3_5_0_8B", "off"): (0, 0, 0), ("Qwen3_5_0_8B", "on"): (0, 0, 0),
}


def test_outputs_record_the_frozen_grader_and_pass_their_checks():
    replay, unaided = _load()
    for js in (replay, unaided):
        assert js["env"]["pyval"] == C.PYVAL_EXPECTED
        assert not js["env"]["validator_server_modified"]
        assert len(js["env"]["marketplace_head"]) == 40
    sc = replay["self_check"]
    assert sc["calls_equal"] + sc["calls_known_difference"] == sc["calls_replayed"]
    assert sc["calls_known_difference"] == len(replay["known_differences"]) == len(RP.KNOWN_DIFFERENCES)
    assert unaided["self_check"]["regrade_equals_stored"] == unaided["self_check"]["regraded_rows"] > 3000
    assert all(f["affected"] for f in replay["flips"] + unaided["flips"])
    assert all(f["direction"] == "fail -> pass" for f in replay["flips"])


def test_tool_arm_moves_equal_the_review():
    replay, unaided = _load()
    T = C.cell_table(replay, unaided)
    for key, (n, k, add) in EXPECTED_TOOL.items():
        v = T[key]
        assert (v["n"], v["k"], v["lo"], v["hi"]) == (n, k, add, add), key
    g = T[("sweep5v2-live", "gemma4_26b-a4b", "off", "simulate", "plain")]
    assert (g["called"], round(100 * g["k"] / g["called"], 1), round(100 * (g["k"] + 10) / g["called"], 1)) == \
        (299, 92.0, 95.3)                                   # correct given a call, plain
    assert round(100 * 285 / 300, 1) == 95.0 and round(100 * 282 / 300, 1) == 94.0


def test_unaided_ranges_equal_the_review():
    replay, unaided = _load()
    T = C.cell_table(replay, unaided)
    for (m, th), (k, lo, hi) in EXPECTED_UNAIDED.items():
        v = T[("sweep5v2-live", m, th, "solve", "unaided")]
        assert (v["n"], v["k"], v["lo"], v["hi"]) == (300, k, lo, hi), (m, th)
    partc = [c for c in unaided["cells"] if c["corpus"] == "delivered-rerun" and c["task"] == "solve"]
    assert sum(c["n_affected"] for c in partc if not c["tools"]) == 81
    assert sum(c.get("online_flips", 0) + c.get("delivered_flips", 0) for c in partc) == 0
    for c in unaided["cells"]:
        if c["corpus"] == "sweep6-live" and c["task"] == "solve":
            assert c.get("online_flips", 0) == c.get("at_cap_candidates", 0) == 0


def test_s1_moves_and_numbers_blocks_are_up_to_date():
    replay, unaided = _load()
    assert C.s1_moves(OUT) == {
        ("Qwen3_5_9B", "solve", "unaided"): (2, 10.7, 11.3),
        ("Qwen3_5_9B", "simulate", "plain"): (1, 65.0, 65.3),
        ("gemma4_26b-a4b", "simulate", "plain"): (10, 91.7, 95.0),
        ("gemma4_26b-a4b", "simulate", "steered"): (10, 90.7, 94.0),
        ("gemma4_26b-a4b", "validate_plan", "steered"): (1, 92.6, 92.6)}
    blocks = C.render_numbers(replay, unaided)
    assert set(blocks) == set(C.NUMBERS_FILES)
    for name, text in blocks.items():
        assert (OUT / C.NUMBERS_FILES[name]).read_text() == text.rstrip("\n") + "\n", name
    assert "0.0 → 95.0" not in blocks["iss027_t5"] and "+91.7 → +95.0" in blocks["iss027_t5"]
    assert "44.0% (132 of 300) reads 45.3% (136 of 300" in blocks["iss027_mech"]
    import numbers_fill
    for name, files in numbers_fill.BLOCKS.items():
        if name.startswith("iss027"):
            assert files == [C.NUMBERS_FILES[name]]
    assert set(C.NUMBERS_FILES) <= set(numbers_fill.BLOCKS)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
