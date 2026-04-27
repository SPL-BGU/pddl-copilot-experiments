#!/usr/bin/env python3
"""One-cycle fix for the 2026-04-27 cluster sweep no-tools summary bug.

Symptom: aggregators (master.csv, plot.py) read no-tools `summary_*.json` and
report `n=0/succ=0.0` for every cell, even though the underlying
`single_task_*.json` carries valid records.

Root cause (in `run_experiment.py`'s summary writer): for a single-condition
run, the writer emits stub `single_task` entries for the OTHER condition with
`n=0`. In a no-tools run, four `condition='tools'` stubs land BEFORE the four
real `condition='no-tools'` rows, and any aggregator that matches by
(model, task) without filtering on condition picks the empty stub first.

This script repairs the symptom in-place for the 2026-04-27 cycle by keeping
only the `single_task` entries whose `condition` matches the run's configured
`meta.conditions`. The original file is preserved at `<name>.preclean` and
the script is idempotent (skips files that already have a `.preclean`
sibling).

SCOPE — IMPORTANT:
- This is a one-time fix for the 2026-04-27 cycle of experiments only. Do
  NOT keep it in the regular pipeline. The root cause should be fixed in
  `run_experiment.py`'s summary writer separately so future cycles don't
  emit the stubs in the first place.
- Defaults to no-tools result dirs only (`slurm_*_no-tools_*`). Pass
  `--scope=all` to also clean tools dirs (which carry symmetric stub
  `condition='no-tools'` rows that don't currently break aggregation but
  are still dead data).

Usage:
    # Default: clean no-tools summaries under results/cluster-20260427/
    python3 cluster-experimenting/cleanup_notools_summaries_cycle_20260427.py

    # Preview without writing
    python3 cluster-experimenting/cleanup_notools_summaries_cycle_20260427.py --dry-run

    # Override the results root
    python3 cluster-experimenting/cleanup_notools_summaries_cycle_20260427.py --root results/cluster-20260427

    # Also clean tools dirs (symmetric stubs)
    python3 cluster-experimenting/cleanup_notools_summaries_cycle_20260427.py --scope all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "results" / "cluster-20260427"


def iter_summary_files(root: Path, scope: str):
    """Yield (dir, summary_path) pairs under `root` matching the requested scope."""
    if not root.exists():
        sys.exit(f"Error: results root not found: {root}")
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not d.name.startswith("slurm_"):
            continue
        if scope == "no-tools" and "_no-tools_" not in d.name:
            continue
        for s in sorted(d.glob("summary_*.json")):
            if s.name.endswith(".preclean"):
                continue
            yield d, s


def clean_one(summary_path: Path, dry_run: bool) -> tuple[int, int, str]:
    """Filter a single summary file. Returns (kept, dropped, status)."""
    backup = summary_path.with_suffix(summary_path.suffix + ".preclean")
    if backup.exists():
        return 0, 0, "skip-already-cleaned"

    data = json.loads(summary_path.read_text())
    target_cond = data.get("meta", {}).get("conditions")
    if not target_cond:
        return 0, 0, "skip-no-meta-conditions"

    original = data.get("single_task", [])
    kept = [r for r in original if r.get("condition") == target_cond]
    dropped = len(original) - len(kept)
    if dropped == 0:
        return len(kept), 0, "noop-no-stubs"

    if dry_run:
        return len(kept), dropped, "would-clean"

    backup.write_text(summary_path.read_text())
    data["single_task"] = kept
    summary_path.write_text(json.dumps(data, indent=2))
    return len(kept), dropped, "cleaned"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help=f"Results root (default: {DEFAULT_ROOT.relative_to(REPO_ROOT)})")
    ap.add_argument("--scope", choices=("no-tools", "all"), default="no-tools",
                    help="Which summary dirs to clean (default: no-tools)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would change without writing")
    args = ap.parse_args()

    cleaned = skipped = noop = 0
    total_dropped = 0
    rows = []
    for d, s in iter_summary_files(args.root, args.scope):
        kept, dropped, status = clean_one(s, args.dry_run)
        total_dropped += dropped
        if status in ("cleaned", "would-clean"):
            cleaned += 1
        elif status == "noop-no-stubs":
            noop += 1
        else:
            skipped += 1
        rows.append((d.name, status, kept, dropped))

    width = max(len(r[0]) for r in rows) if rows else 0
    print(f"{'dir':<{width}}  status              kept  dropped")
    for name, status, kept, dropped in rows:
        print(f"{name:<{width}}  {status:<18}  {kept:>4}  {dropped:>7}")
    print()
    verb = "would-clean" if args.dry_run else "cleaned"
    print(f"summary: {verb}={cleaned}  noop={noop}  skipped={skipped}  "
          f"total stub rows {'would be ' if args.dry_run else ''}dropped={total_dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
