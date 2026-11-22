"""Unit tests for the pure helpers of tools/reanalysis/rq1_metrics.py.

No results/ data is read: the tests cover the per-state scorer, the cut-off
trace salvage, the confusion counts, the plan-argument parser and the bins.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pddl_eval.scoring import _normalize_trajectory  # noqa: E402
from tools.reanalysis import rq1_metrics as R  # noqa: E402


def step(i, action, true_preds, numeric=None):
    return {"step": i, "action": action,
            "state": {"boolean": list(true_preds), "numeric": numeric or {}}}


ORACLE_RAW = [step(0, "", ["(on a b)"]), step(1, "(unstack a b)", ["(holding a)"]),
              step(2, "(put_down a)", ["(ontable a)"], {"(cost)": 2.0})]
ORACLE = _normalize_trajectory(ORACLE_RAW)


def test_state_score_exact_and_missing():
    assert R.state_score(ORACLE, ORACLE) == {"n_states": 3, "matched": 3, "prefix": 3,
                                             "answer_states": 3}
    assert R.state_score(None, ORACLE)["matched"] == 0
    assert R.state_score([], ORACLE)["prefix"] == 0


def test_state_score_ignores_action_label_and_step_number():
    relabelled = _normalize_trajectory(
        [step(7, "(noop)", ["(on a b)"]), step(8, "(x)", ["(holding a)"]),
         step(9, "(y)", ["(ontable a)"], {"(cost)": 2.0})])
    assert R.state_score(relabelled, ORACLE)["matched"] == 3


def test_state_score_prefix_stops_at_first_wrong_state():
    wrong_middle = _normalize_trajectory(
        [ORACLE_RAW[0], step(1, "(unstack a b)", ["(clear a)"]), ORACLE_RAW[2]])
    s = R.state_score(wrong_middle, ORACLE)
    assert (s["matched"], s["prefix"]) == (2, 1)
    short = _normalize_trajectory(ORACLE_RAW[:2])
    s = R.state_score(short, ORACLE)
    assert (s["matched"], s["prefix"], s["answer_states"]) == (2, 2, 2)


def test_best_state_score_reads_a_whole_json_answer():
    s = R.best_state_score(json.dumps({"trajectory": ORACLE_RAW}), ORACLE)
    assert s["parsed"] and s["matched"] == 3 and not s["salvaged"]
    assert s["salvaged_matched"] == 3 and not s["shift_gain"]


def test_best_state_score_flags_an_off_by_one_trace():
    shifted = json.dumps({"trajectory": ORACLE_RAW[1:]})
    s = R.best_state_score(shifted, ORACLE)
    assert s["parsed"] and s["matched"] == 0 and s["shift_gain"]


def test_salvage_reads_complete_steps_of_a_cut_off_trace():
    whole = json.dumps({"trajectory": ORACLE_RAW})
    cut = whole[: whole.index('"step": 2')]          # third step is incomplete
    strict = R.best_state_score(cut, ORACLE)
    assert not strict["parsed"] and strict["matched"] == 0
    assert strict["salvaged"] and strict["salvaged_matched"] == 2
    assert R.salvage_steps("no trace here") is None
    assert R.salvage_steps('{"trajectory": [') is None


def test_salvage_is_not_used_when_the_answer_is_readable():
    wrong = json.dumps({"trajectory": [step(0, "", ["(clear z)"])]})
    s = R.best_state_score(wrong, ORACLE)
    assert s["parsed"] and not s["salvaged"] and s["salvaged_matched"] == s["matched"] == 0


def test_confusion_counts():
    truths = [True, True, True, False, False, False]
    verdicts = [True, False, None, False, True, None]
    assert R.confusion(truths, verdicts) == {"n_valid": 3, "n_broken": 3, "fn": 1,
                                             "valid_none": 1, "fp": 1, "broken_none": 1}


@pytest.mark.parametrize("arg", [
    '["(unstack b2 b1)", "(put_down b2)"]', '["unstack b2 b1", "put_down  B2"]',
    "(unstack b2 b1)\n(put_down b2)\n", ["(Unstack b2 b1)", "(put_down b2)"]])
def test_plan_argument_forms_normalise_alike(arg):
    assert R.plan_argument(arg) == ("unstack b2 b1", "put_down b2")


def test_plan_argument_rejects_empty():
    assert R.plan_argument(None) is None and R.plan_argument("") is None
    assert R.plan_argument([]) is None


def test_bins_cover_every_length():
    assert [R.bin_of(n) for n in (1, 5, 6, 20, 21, 40, 41, 500)] == \
        ["1–5", "1–5", "6–10", "11–20", "21–40", "21–40", "41+", "41+"]
    assert R.bin_labels() == ["1–5", "6–10", "11–20", "21–40", "41+"]
    with pytest.raises(ValueError):
        R.bin_of(0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
