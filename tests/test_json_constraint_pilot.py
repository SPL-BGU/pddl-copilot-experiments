"""Unit tests for the pure helpers of tools/reanalysis/json_constraint_pilot.py (no results data)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.delivered_rerun import constants as C  # noqa: E402
from tools.delivered_rerun import grade as G  # noqa: E402
from tools.reanalysis import json_constraint_pilot as J  # noqa: E402

CUT = '{\n  "verdict": "INVALID",\n  "reason": "The plan is invalid because it attempts to'
WHOLE = '{"verdict": "VALID", "reason": "every precondition holds"}'


def row(response, task="validate_plan", plan_label="v1", domain="barman", done_reason="length",
        completion=10):
    return SimpleNamespace(response=response, task=task, problem="p01", plan_label=plan_label,
                           domain=domain, done_reason=done_reason,
                           tokens=SimpleNamespace(completion=completion))


def grade(ok, reason):
    return G.Delivered(ok, reason, None, None, None, False)


def test_verdict_field_reads_a_leading_field_only():
    assert J.verdict_field(CUT) is False
    assert J.verdict_field(WHOLE) is True
    assert J.verdict_field(C.LEAKED_PREFIX + CUT) is False
    assert J.verdict_field("VERDICT: VALID. The plan works.") is None
    assert J.verdict_field('The answer is {"verdict": "VALID"}') is None
    assert J.verdict_field('{"reason": "x", "verdict": "VALID"}') is None
    assert J.verdict_field('{"verdict": "MAYBE"') is None
    assert J.verdict_field("") is None


def test_starts_json():
    assert J.starts_json('  {"plan": []}')
    assert J.starts_json(C.LEAKED_PREFIX + '{"plan": []}')
    assert not J.starts_json('```json\n{"plan": []}\n```')
    assert not J.starts_json("")


def test_lenient_reads_only_answers_without_a_frozen_verdict():
    none = grade(False, "no_verdict_stated")
    # the plan is valid (label v1): a cut answer that opens with INVALID stays wrong
    assert not J.lenient_ok(row(CUT), none)
    # the plan is broken (label b1): the same answer is right once its field is read
    assert J.lenient_ok(row(CUT, plan_label="b1"), none)
    # no verdict field: nothing to read
    assert not J.lenient_ok(row("The plan seems", plan_label="b1"), none)
    # a verdict the frozen grader did read is never changed
    assert not J.lenient_ok(row(CUT, plan_label="b1"), grade(False, "verdict_stated_wrong"))
    assert J.lenient_ok(row(CUT), grade(True, "verdict_stated_ok"))
    # tasks without a verdict are never touched
    assert not J.lenient_ok(row(CUT, task="solve", plan_label=""),
                            grade(False, "no_plan_extracted"))


def test_paired_difference_and_counts():
    doms = ["a", "a", "b", "b"]
    rows = [row("x", domain=d) for d in doms]
    before = [grade(True, "verdict_stated_ok"), grade(True, "verdict_stated_ok"),
              grade(False, "verdict_stated_wrong"), grade(False, "verdict_stated_wrong")]
    after = [grade(False, "verdict_stated_wrong"), grade(True, "verdict_stated_ok"),
             grade(True, "verdict_stated_ok"), grade(False, "verdict_stated_wrong")]
    d = J.paired(rows, before, rows, after)
    assert (d["lost"], d["gained"], d["n"], d["k"]) == (1, 1, 4, 2)
    assert d["est"] == 0.0 and d["lo"] <= 0.0 <= d["hi"]
    worse = J.paired(rows, before, rows, [grade(False, "verdict_stated_wrong")] * 4)
    assert worse["est"] == -50.0 and (worse["lost"], worse["gained"]) == (2, 0)


def test_summarise_counts():
    rows = [row(WHOLE, done_reason="stop", completion=20, domain="a"),
            row(CUT, completion=40, domain="b")]
    s = J.summarise(rows, [grade(True, "verdict_stated_ok"), grade(False, "no_verdict_stated")])
    assert (s["n"], s["right"], s["starts_json"], s["at_output_cap"]) == (2, 1, 2, 1)
    assert s["mean_completion_tokens"] == 30
    assert s["delivered"]["est"] == 50.0
    assert s["reasons"] == {"no_verdict_stated": 1, "verdict_stated_ok": 1}
    # the cut answer opens with INVALID and the plan is valid: still wrong when read
    assert s["delivered_verdict_field"]["est"] == 50.0
