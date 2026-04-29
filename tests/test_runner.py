"""Unit tests for pddl_eval.runner internals.

Run standalone: `python3 tests/test_runner.py`
Or via the shell wrapper: `bash tests/verify.sh`

Pure-Python tests: no MCP, no Ollama, no fixture I/O.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from pddl_eval.runner import _shard_filter


def test_plan_label_in_shard_key_spreads_across_shards(r: TestResults) -> None:
    """v1..v5/b1..b5 must not all cluster in shard 0.

    Regression guard for the PR-3 shard-key change that added `plan_label`
    to the key so v1..v5 / b1..b5 spread across shards instead of all
    landing in shard 0 alongside the underlying (model, task, dname, pname)
    cell.
    """
    base = ("llama3.2:3b", "validate_plan", "blocksworld", "p01")
    plan_labels = ["v1", "v2", "v3", "v4", "v5", "b1", "b2", "b3", "b4", "b5"]
    shard_n = 4
    selected: set[int] = set()
    for label in plan_labels:
        key = (*base, label, "False")
        for shard_i in range(shard_n):
            if _shard_filter(shard_i, shard_n, key):
                selected.add(shard_i)
                break
    r.check(
        "plan_label disperses keys across >1 shard",
        len(selected) > 1,
        f"all {len(plan_labels)} labels landed in shards={sorted(selected)} (expected >1)",
    )


def test_shard_filter_partitions_keys(r: TestResults) -> None:
    """Each key lands in exactly one shard (well-defined partition)."""
    key = ("m", "validate_plan", "d", "p01", "v1", "False")
    for shard_n in (2, 4, 8):
        hits = [
            shard_i
            for shard_i in range(shard_n)
            if _shard_filter(shard_i, shard_n, key)
        ]
        r.check_eq(f"shard_n={shard_n} key lands in 1 shard", len(hits), 1)


def test_shard_filter_single_shard_passes_all(r: TestResults) -> None:
    """`shard_n <= 1` is a no-op: every key passes."""
    for key in [("a",), ("b", "c"), ("x", "y", "z")]:
        r.check(
            f"shard_n=1 passes key={key}",
            _shard_filter(0, 1, key),
        )


if __name__ == "__main__":
    r = TestResults("test_runner")
    test_plan_label_in_shard_key_spreads_across_shards(r)
    test_shard_filter_partitions_keys(r)
    test_shard_filter_single_shard_passes_all(r)
    r.report_and_exit()
