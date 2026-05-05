"""Backfill the per-cell `tokens` summary block into existing summary_*.json.

The runner has always written per-trial `tokens` into `trials.jsonl`, but the
aggregator only began surfacing them in the summary after the
`feat/summary-token-stats` change. This script reuses
`pddl_eval.resume.load_progress` to round-trip the JSONL into `TaskResult`
objects (so the dataclass shape matches what fresh runs would produce),
then calls `summarize_single_task` and grafts the new `tokens` keys onto
each row of the existing summary file in place.

Idempotent — overwrites existing `tokens` keys; doesn't touch any other
field. Skips dirs whose `summary_*.json` is missing (in-progress cells).

Usage:
    python -m tools.backfill_token_stats <results_root>
    # results_root contains slurm_<...>/ subdirs with trials.jsonl + summary_*.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python tools/backfill_token_stats.py ...` from the repo root in
# addition to `python -m tools.backfill_token_stats ...`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pddl_eval.resume import load_progress
from pddl_eval.summary import summarize_single_task


def _index_rows(rows: list[dict]) -> dict[tuple, dict]:
    return {(r["model"], r["condition"], r["task"]): r for r in rows}


def backfill_dir(cell_dir: Path) -> str:
    """Backfill every summary_*.json in *cell_dir* using its trials.jsonl.

    Returns a one-line status string for the caller to print. Each summary
    file in the dir is rewritten in place (multiple files happen when a
    cell was rerun and accumulated timestamps); they all see the same
    aggregated tokens because trials.jsonl is the single source of truth.
    """
    trials = cell_dir / "trials.jsonl"
    summaries = sorted(cell_dir.glob("summary_*.json"))
    if not summaries:
        return f"  skip {cell_dir.name}: no summary_*.json"
    if not trials.exists():
        return f"  skip {cell_dir.name}: no trials.jsonl"

    restored = list(load_progress(trials).values())
    if not restored:
        return f"  skip {cell_dir.name}: trials.jsonl empty"

    rows = summarize_single_task(restored)
    by_key = _index_rows(rows)

    for sf in summaries:
        with sf.open() as f:
            data = json.load(f)
        single = data.get("single_task", [])
        merged = 0
        for row in single:
            key = (row.get("model"), row.get("condition"), row.get("task"))
            src = by_key.get(key)
            if not src:
                continue
            row["tokens"] = src["tokens"]
            for var_key, cell in row.get("per_variant", {}).items():
                src_var = src.get("per_variant", {}).get(var_key)
                if src_var and "tokens" in src_var:
                    cell["tokens"] = src_var["tokens"]
            merged += 1
        sf.write_text(json.dumps(data, indent=2))
        last_msg = f"  {cell_dir.name} <- {sf.name}: merged tokens into {merged}/{len(single)} rows"
    return last_msg


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <results_root>", file=sys.stderr)
        sys.exit(2)
    root = Path(sys.argv[1])
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")

    cell_dirs = sorted(d for d in root.glob("slurm_*") if d.is_dir())
    if not cell_dirs:
        sys.exit(f"no slurm_* subdirs under {root}")

    print(f"Backfilling token stats under {root} ({len(cell_dirs)} cell dirs)")
    for d in cell_dirs:
        print(backfill_dir(d))


if __name__ == "__main__":
    main()
