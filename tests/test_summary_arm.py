"""Unit tests for the sweep-5 arm classifier and the completion_median
extension to the token aggregator.

Run standalone: `python3 tests/test_summary_arm.py`
Or via the shell wrapper: `bash tests/verify.sh`

Why this file: the sweep-5 design doc (development/sweep_prompt_bank_design.md
§0) defines four analysis arms — nt-neut / nt-ster / tl-neut / tl-ster — that
the analyzer must classify consistently across plot.py, table.py, aggregate.py,
and build_deck.py. A single classifier in pddl_eval/summary.py is the source
of truth; this file pins its contract. The token-median test pins the
schema bump that filter_variants regen surfaces into summary_*.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval.summary import (  # noqa: E402
    NEUTRAL_VARIANTS,
    _add_tokens,
    _new_token_agg,
    _token_row,
    arm_for,
    summarize_single_task,
)
from pddl_eval.prompts import STEERED_VARIANTS  # noqa: E402
from pddl_eval.runner import TaskResult  # noqa: E402
from pddl_eval.scoring import FR_OK  # noqa: E402
from tests._helpers import TestResults  # noqa: E402


def test_arm_for_matrix(r: TestResults):
    # Sweep-5 active arms.
    r.check_eq("arm tl-neut v11", arm_for(True, 11), "tl-neut")
    r.check_eq("arm tl-neut v12", arm_for(True, 12), "tl-neut")
    r.check_eq("arm tl-neut v13", arm_for(True, 13), "tl-neut")
    r.check_eq("arm nt-neut v11", arm_for(False, 11), "nt-neut")
    r.check_eq("arm tl-ster v14", arm_for(True, 14), "tl-ster")
    r.check_eq("arm tl-ster v15", arm_for(True, 15), "tl-ster")
    r.check_eq("arm tl-ster v16", arm_for(True, 16), "tl-ster")
    r.check_eq("arm nt-ster v14", arm_for(False, 14), "nt-ster")
    # Legacy fallback (sweep-3/4 corpora — v0-v10).
    for v in (0, 1, 2, 5, 6, 7, 10):
        r.check_eq(f"arm tl-legacy v{v}", arm_for(True, v), "tl-legacy")
        r.check_eq(f"arm nt-legacy v{v}", arm_for(False, v), "nt-legacy")


def test_arm_for_disjoint_sets(r: TestResults):
    # The classifier's correctness rests on NEUTRAL_VARIANTS and STEERED_VARIANTS
    # being disjoint. If they ever overlap, arm_for would return tl-ster (the
    # first branch) for the overlapping variant, silently masking a config bug.
    overlap = NEUTRAL_VARIANTS & STEERED_VARIANTS
    r.check_eq("neutral and steered disjoint", overlap, frozenset())


def test_token_agg_median_round_trip(r: TestResults):
    agg = _new_token_agg()
    for completion in (10, 20, 30, 40, 50):
        _add_tokens(agg, {
            "prompt": 100,
            "completion": completion,
            "turns": 1,
            "eval_duration_ns": 1_000_000_000,
        })
    row = _token_row(agg)
    r.check_eq("median 5 samples", row["completion_median"], 30.0)
    r.check_eq("mean 5 samples", row["completion_mean"], 30.0)
    r.check_eq("n 5 samples", row["n"], 5)
    # Schema invariant: completion_samples (the internal list) must NEVER
    # appear in the serialized row — only the computed median.
    r.check("completion_samples not in row", "completion_samples" not in row,
            f"row keys={sorted(row.keys())}")
    # JSON-serializable.
    json.dumps(row)


def test_token_agg_empty_cell(r: TestResults):
    # A cell with zero token-bearing trials still serializes cleanly. Consumers
    # plot the field unconditionally; the median default must be 0.0, never
    # statistics.StatisticsError.
    row = _token_row(_new_token_agg())
    r.check_eq("empty median", row["completion_median"], 0.0)
    r.check_eq("empty n", row["n"], 0)


def test_token_agg_skips_empty_tokens(r: TestResults):
    # Trials with missing/empty tokens dicts (e.g. infra failures) are not
    # appended to the samples list — keeps the median honest.
    agg = _new_token_agg()
    _add_tokens(agg, {"prompt": 10, "completion": 100, "turns": 1, "eval_duration_ns": 0})
    _add_tokens(agg, {})  # skipped
    _add_tokens(agg, None or {})  # skipped
    _add_tokens(agg, {"prompt": 10, "completion": 200, "turns": 1, "eval_duration_ns": 0})
    row = _token_row(agg)
    r.check_eq("median skips empties", row["completion_median"], 150.0)
    r.check_eq("n skips empties", row["n"], 2)


def _result(model: str, with_tools: bool, prompt_variant: int,
            success: bool, completion: int) -> TaskResult:
    # Minimal TaskResult for summarize_single_task — only fields the function
    # reads are set; everything else takes its dataclass default.
    return TaskResult(
        model=model,
        domain_name="blocksworld",
        problem_name="p01",
        task="solve",
        prompt_variant=prompt_variant,
        with_tools=with_tools,
        success=success,
        tool_selected=False,
        truncated=False,
        failure_reason=FR_OK if success else "exception",
        tokens={
            "prompt": 100,
            "completion": completion,
            "turns": 1,
            "eval_duration_ns": 1_000_000_000,
        },
    )


def test_per_variant_arm_pooling_invariant(r: TestResults):
    # The analyzer reads summary_*.json's per_variant dict and pools across
    # arm-matching variants (v11/v12/v13 → neut; v14/v15/v16 → ster). This
    # test pins that the per_variant cells stay disjoint at the source —
    # summarize_single_task must NOT silently mix variants into a single
    # bucket. Reason: the corpus-identity feedback memory
    # (feedback_pushback_on_methodology_shortcuts) says arms cannot be mixed.
    trials = [
        _result("m1", True, 11, True,  100),
        _result("m1", True, 12, True,  120),
        _result("m1", True, 13, False, 140),
        _result("m1", True, 14, True,  200),
        _result("m1", True, 15, True,  220),
        _result("m1", True, 16, False, 240),
    ]
    rows = summarize_single_task(trials)
    tools_solve = next(r for r in rows
                       if r["model"] == "m1" and r["task"] == "solve"
                       and r["condition"] == "tools")
    pv = tools_solve["per_variant"]
    r.check_eq("variants present", sorted(pv.keys()),
               ["11", "12", "13", "14", "15", "16"])
    # Each variant cell has n=1 — no cross-variant pooling at the source.
    for v in ("11", "12", "13", "14", "15", "16"):
        r.check_eq(f"v{v} n=1", pv[v]["n"], 1)
    # Arm-pooling at the analyzer layer must add to the whole-cell totals.
    neut_n = sum(pv[v]["n"] for v in ("11", "12", "13"))
    ster_n = sum(pv[v]["n"] for v in ("14", "15", "16"))
    r.check_eq("neut+ster == whole cell", neut_n + ster_n, tools_solve["n"])
    # Each per_variant cell carries its own median (sweep-5 H3).
    for v in ("11", "12", "13", "14", "15", "16"):
        r.check("per-variant median present", "completion_median" in pv[v]["tokens"],
                f"pv[{v}]['tokens'] keys={sorted(pv[v]['tokens'].keys())}")


def main():
    r = TestResults("test_summary_arm")
    test_arm_for_matrix(r)
    test_arm_for_disjoint_sets(r)
    test_token_agg_median_round_trip(r)
    test_token_agg_empty_cell(r)
    test_token_agg_skips_empty_tokens(r)
    test_per_variant_arm_pooling_invariant(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
