#!/usr/bin/env python3
"""Ground-truth cache gate for the nt-ster H4 run (prereg §8 item 10).

Ground truth is regenerated live by MCP at every run start and never persisted
(`run_experiment.py:415`), trial rows store no plan text, and the cache was for a
long time an untracked artifact with no provenance. A live-vs-cache divergence
would therefore be silent and unauditable. This module is the audit point: the
analysis entry points call `assert_gate()` before reading any trial, so an
analysis run against a cache that does not match its stamp fails loudly instead
of producing quietly wrong numbers.

WHY THE GATE IS NOT THE FILE'S sha256
-------------------------------------
`domain_validation_raw` stores the validator's `[WARNING]` lines in a
process-dependent order. Measured 2026-08-17 across all 100 problems: identical
warning multiset, identical string length, different line order — so the file
hash changes on every rebuild while the ground truth does not. That field is
written at `pddl_eval/domains.py:174` and is read by no grading code. The gate is
therefore a canonical hash over every field EXCEPT that one, which is exactly the
set of values a grader can observe.

Usage:
    python tools/gt_cache_gate.py                      # verify cache against stamp
    python tools/gt_cache_gate.py --print-hash         # just emit the canonical hash
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_CACHE = Path("results/derived/gt_cache.json")
DEFAULT_STAMP = Path("results/derived/gt_cache_stamp.json")

# Written at pddl_eval/domains.py:174, consumed nowhere. Its serialization order
# is process-dependent, so it is excluded from the canonical hash.
UNSTABLE_DIAGNOSTIC_FIELDS = ("domain_validation_raw",)


def canonical_hash(gt: dict) -> str:
    """sha256 over the grading-relevant view of a ground-truth mapping."""
    o = copy.deepcopy(gt)
    for domain in o.values():
        if not isinstance(domain, dict):
            continue
        for entry in domain.values():
            if isinstance(entry, dict):
                for field in UNSTABLE_DIAGNOSTIC_FIELDS:
                    entry.pop(field, None)
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def load_gate(cache_path: Path = DEFAULT_CACHE,
              stamp_path: Path = DEFAULT_STAMP) -> tuple[str, str]:
    """Return `(actual_hash, expected_hash)` without asserting."""
    if not cache_path.exists():
        raise SystemExit(f"gt gate: cache not found: {cache_path}")
    if not stamp_path.exists():
        raise SystemExit(
            f"gt gate: stamp not found: {stamp_path}\n"
            "The cache is unstamped, so its provenance is unknown. Rebuild with "
            "tools/build_gt_cache.py and stamp it before running any analysis."
        )
    actual = canonical_hash(json.loads(cache_path.read_text()))
    expected = json.loads(stamp_path.read_text())["gate"]["value"]
    return actual, expected


def assert_gate(cache_path: Path = DEFAULT_CACHE,
                stamp_path: Path = DEFAULT_STAMP) -> str:
    """Hard-fail unless the cache matches its stamp. Returns the verified hash."""
    actual, expected = load_gate(cache_path, stamp_path)
    if actual != expected:
        raise SystemExit(
            "gt gate: FAIL — the ground-truth cache does not match its stamp.\n"
            f"  expected {expected}\n"
            f"  actual   {actual}\n"
            "Ground truth moved since the stamp was written, so any number derived "
            "from it is not comparable to the pre-registered apparatus. Do not "
            "proceed: rebuild, re-diff against the backup, and re-stamp explicitly."
        )
    return actual


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--stamp", type=Path, default=DEFAULT_STAMP)
    ap.add_argument("--print-hash", action="store_true",
                    help="print the cache's canonical hash and exit 0 without gating")
    args = ap.parse_args()

    if args.print_hash:
        print(canonical_hash(json.loads(args.cache.read_text())))
        return 0

    verified = assert_gate(args.cache, args.stamp)
    stamp = json.loads(args.stamp.read_text())
    print(f"gt gate: PASS  {verified}")
    print(f"  built {stamp['built_at']} from marketplace "
          f"{stamp['provenance']['marketplace_repo']['head'][:7]} "
          f"(oracle subtrees identical to pin "
          f"{stamp['provenance']['marketplace_repo']['pinned_commit'][:7]})")
    print(f"  domains tree {stamp['provenance']['experiments_repo']['domains_tree'][:12]}")
    c = stamp["contents"]
    print(f"  {c['domains']} domains / {c['problems']} problems / "
          f"{c['negative_fixtures']} negative fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
