"""Unit tests for the pure helpers of tools/reanalysis/rq23_metrics.py (no results data)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.reanalysis import rq23_metrics as Q  # noqa: E402


def test_right_tool_per_task():
    assert Q.right_tool("validate_plan", None) == "validate_plan"
    assert Q.right_tool("simulate", "classical") == "get_state_transition"
    assert Q.right_tool("solve", "classical") == "classic_planner"
    assert Q.right_tool("solve", "numeric") == "numeric_planner"
    with pytest.raises(ValueError):
        Q.right_tool("solve", None)


@pytest.mark.parametrize("names,cls", [
    ([], "none"),
    (["validate_plan"], "right_only"),
    (["validate_plan", "validate_plan"], "right_only"),
    (["validate_plan", "validate_domain"], "right_plus"),
    (["validate_domain"], "other_only"),
])
def test_classes_are_exclusive_and_by_tool_set(names, cls):
    c = Q.classify("validate_plan", "classical", names)
    assert c["cls"] == cls
    assert c["harness_called"] == ("validate_plan" in names)
    assert not c["other_planner"] and not c["plan_check_only"]


def test_solve_is_stricter_than_the_harness_rule():
    wrong = Q.classify("solve", "classical", ["numeric_planner"])
    assert wrong["cls"] == "other_only" and wrong["harness_called"] and wrong["other_planner"]
    both = Q.classify("solve", "numeric", ["classic_planner", "numeric_planner"])
    assert both["cls"] == "right_plus" and both["other_planner"] and not both["plan_check_only"]


def test_plan_check_after_the_planner_is_marked():
    c = Q.classify("solve", "classical", ["classic_planner", "validate_plan"])
    assert c["cls"] == "right_plus" and c["plan_check_only"] and not c["other_planner"]
    c = Q.classify("solve", "classical", ["classic_planner", "validate_plan", "save_plan"])
    assert c["cls"] == "right_plus" and not c["plan_check_only"]


def test_arm_of_variant():
    assert [Q.arm_of(v) for v in (11, 13, 14, 16)] == ["plain", "plain", "steered", "steered"]
    with pytest.raises(ValueError):
        Q.arm_of(17)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
