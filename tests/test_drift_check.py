"""Tests for .claude/skills/analyzer/scripts/drift_check.py.

drift_check.py exits with code 1 when any cell drifts below baseline; that
exit code is consumed by scripted gating that decides whether to keep a
12h GPU sweep running. Silent bugs in `_classify_drift`, `_load_cell`'s
summary-vs-JSONL precedence, or `_aggregate_trials_jsonl`'s dedup would
let a regressing sweep continue chewing compute. This file covers the
load-bearing pure-Python paths.
"""

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude/skills/analyzer/scripts"))

from tests._helpers import TestResults
from drift_check import (
    _aggregate_trials_jsonl,
    _classify_drift,
    _load_cell,
    wilson_ci,
)
from pddl_eval.runner import TRIAL_KEY_LEN


def _ten_tuple(model="m", task="solve", dname="d", pname="p",
               plan_label="", pv=0, with_tools=True,
               think="on", tool_filter="all", prompt_style="minimal"):
    """Build a JSON-serialisable list of length TRIAL_KEY_LEN (10)."""
    return [model, task, dname, pname, plan_label, pv, with_tools,
            think, tool_filter, prompt_style]


def test_wilson_ci_zero_n_returns_zero_zero(r: TestResults) -> None:
    """Guards the early-return — drift_check must not divide by zero."""
    r.check_eq("zero n returns (0.0, 0.0)", wilson_ci(0, 0), (0.0, 0.0))


def test_wilson_ci_known_values(r: TestResults) -> None:
    """Hand-computed bounds at (k=8, n=10) and (k=0, n=10), tol=1e-3.

    Locks the formula against accidental drift if the canonical
    implementation in pddl_eval.summary ever migrates.
    """
    lo, hi = wilson_ci(8, 10)
    r.check("8/10 lo ≈ 0.4902", abs(lo - 0.4902) < 1e-3, f"got lo={lo}")
    r.check("8/10 hi ≈ 0.9433", abs(hi - 0.9433) < 1e-3, f"got hi={hi}")
    lo, hi = wilson_ci(0, 10)
    r.check("0/10 lo == 0.0", lo == 0.0, f"got lo={lo}")
    r.check("0/10 hi ≈ 0.2775", abs(hi - 0.2775) < 1e-3, f"got hi={hi}")


def test_classify_drift_inside_ci_returns_none(r: TestResults) -> None:
    """Current point inside baseline 95% CI → 'none' (no drift)."""
    r.check_eq(
        "(base 8/10, cur 7/10) -> none",
        _classify_drift(base_n=10, base_k=8, cur_n=10, cur_k=7),
        "none",
    )


def test_classify_drift_below_baseline(r: TestResults) -> None:
    """Current point below baseline lower bound → 'below' (gating fires)."""
    r.check_eq(
        "(base 9/10, cur 1/10) -> below",
        _classify_drift(base_n=10, base_k=9, cur_n=10, cur_k=1),
        "below",
    )


def test_classify_drift_above_baseline(r: TestResults) -> None:
    """Current point above baseline upper bound → 'above' (good news)."""
    r.check_eq(
        "(base 1/10, cur 9/10) -> above",
        _classify_drift(base_n=10, base_k=1, cur_n=10, cur_k=9),
        "above",
    )


def test_classify_drift_no_data(r: TestResults) -> None:
    """Either side n=0 → 'no-data', not a spurious 'none' or division error."""
    r.check_eq(
        "base n=0 -> no-data",
        _classify_drift(base_n=0, base_k=0, cur_n=10, cur_k=5),
        "no-data",
    )
    r.check_eq(
        "cur n=0 -> no-data",
        _classify_drift(base_n=10, base_k=5, cur_n=0, cur_k=0),
        "no-data",
    )


def test_load_cell_prefers_summary_over_jsonl(r: TestResults) -> None:
    """When both summary_*.json and trials.jsonl exist, summary wins.

    The JSONL is meant as a mid-sweep fallback. If a summary has been
    written, it represents the canonical end-of-run aggregation and
    drift_check must use it.
    """
    with tempfile.TemporaryDirectory() as d:
        cell = Path(d)
        # Summary says 7/10 for 'solve'. Trials JSONL says 0/1 (would
        # poison the read if it were preferred).
        (cell / "summary_20260501T120000.json").write_text(json.dumps({
            "single_task": [{"task": "solve", "n": 10, "successes": 7}],
        }))
        rec = {"key": _ten_tuple(), "result": {"task": "solve", "success": False}}
        (cell / "trials.jsonl").write_text(json.dumps(rec) + "\n")
        loaded = _load_cell(cell)
        r.check("returns non-None", loaded is not None, f"got {loaded}")
        src, per_task = loaded
        r.check_eq("source == summary", src, "summary")
        r.check_eq("solve.n from summary", per_task["solve"]["n"], 10)
        r.check_eq("solve.successes from summary", per_task["solve"]["successes"], 7)


def test_load_cell_falls_back_to_jsonl(r: TestResults) -> None:
    """No summary_*.json yet → aggregate from trials.jsonl directly.

    This is the load-bearing case for in-flight drift detection: a 12h
    cell that's still running has no summary but has accumulated trials.
    """
    with tempfile.TemporaryDirectory() as d:
        cell = Path(d)
        records = [
            {"key": _ten_tuple(pname="p1"), "result": {"task": "solve", "success": True}},
            {"key": _ten_tuple(pname="p2"), "result": {"task": "solve", "success": True}},
            {"key": _ten_tuple(pname="p3"), "result": {"task": "solve", "success": False}},
        ]
        (cell / "trials.jsonl").write_text("".join(json.dumps(rec) + "\n" for rec in records))
        loaded = _load_cell(cell)
        r.check("returns non-None", loaded is not None, f"got {loaded}")
        src, per_task = loaded
        r.check_eq("source == trials", src, "trials")
        r.check_eq("solve.n from JSONL", per_task["solve"]["n"], 3)
        r.check_eq("solve.successes from JSONL", per_task["solve"]["successes"], 2)


def test_load_cell_returns_none_when_empty(r: TestResults) -> None:
    """Empty cell dir (no summary, no JSONL) → None, callers skip it."""
    with tempfile.TemporaryDirectory() as d:
        r.check_eq("empty dir -> None", _load_cell(Path(d)), None)


def test_aggregate_trials_jsonl_dedups_repeated_keys(r: TestResults) -> None:
    """Same trial key twice → counted once; matches _load_progress policy.

    Defensive against accidental file concatenation (cluster sync race,
    manual cat). First-seen wins; conflicting later records ignored.
    """
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "trials.jsonl"
        same_key = _ten_tuple()
        records = [
            {"key": same_key, "result": {"task": "solve", "success": True}},
            {"key": same_key, "result": {"task": "solve", "success": False}},
        ]
        path.write_text("".join(json.dumps(rec) + "\n" for rec in records))
        out = _aggregate_trials_jsonl(path)
        r.check_eq("dedup -> n=1", out["solve"]["n"], 1)
        r.check_eq("first-seen wins -> successes=1", out["solve"]["successes"], 1)


def test_aggregate_trials_jsonl_drops_wrong_length_keys(r: TestResults) -> None:
    """Wrong-length key tuples are silently dropped (not raised).

    drift_check is a read-only analyzer; loud failure here would block
    drift checks against a cell that has a perfectly good summary
    alongside a stale JSONL. _load_progress in run_experiment.py raises
    by design (writer-side); here we degrade gracefully.
    """
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "trials.jsonl"
        good = _ten_tuple()
        bad_short = ["m", "solve", "d", "p"]  # length 4, not TRIAL_KEY_LEN
        records = [
            {"key": bad_short, "result": {"task": "solve", "success": True}},
            {"key": good, "result": {"task": "solve", "success": True}},
        ]
        path.write_text("".join(json.dumps(rec) + "\n" for rec in records))
        # Sanity-check the constants are aligned so the test is meaningful.
        r.check("TRIAL_KEY_LEN unchanged at 10", TRIAL_KEY_LEN == 10,
                f"TRIAL_KEY_LEN={TRIAL_KEY_LEN}; bad_short len would need to be ≠ this")
        out = _aggregate_trials_jsonl(path)
        r.check_eq("only good key counted", out["solve"]["n"], 1)
        r.check_eq("good key counted as success", out["solve"]["successes"], 1)


if __name__ == "__main__":
    r = TestResults("test_drift_check")
    test_wilson_ci_zero_n_returns_zero_zero(r)
    test_wilson_ci_known_values(r)
    test_classify_drift_inside_ci_returns_none(r)
    test_classify_drift_below_baseline(r)
    test_classify_drift_above_baseline(r)
    test_classify_drift_no_data(r)
    test_load_cell_prefers_summary_over_jsonl(r)
    test_load_cell_falls_back_to_jsonl(r)
    test_load_cell_returns_none_when_empty(r)
    test_aggregate_trials_jsonl_dedups_repeated_keys(r)
    test_aggregate_trials_jsonl_drops_wrong_length_keys(r)
    r.report_and_exit()
