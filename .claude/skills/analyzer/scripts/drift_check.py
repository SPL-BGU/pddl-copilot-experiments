#!/usr/bin/env python3
"""Drift check: compare an in-flight or completed sweep against a baseline.

Walks two results roots (`--baseline` + `--current`), aligns per-cell rows by
(model, think, cond, task), and flags cells where the current sweep's point
estimate falls outside the baseline's Wilson 95% CI. Use to verify an ongoing
sweep isn't drifting from a prior reference run before letting it consume more
compute, or to spot-check a finished sweep against a paper-target.

For each cell, prefers the latest `summary_*.json` if present; falls back to
aggregating `trials.jsonl` directly so cells that haven't yet hit `save_results`
(mid-sweep, pre-TIMEOUT) still surface a current estimate. Cells without either
file are listed as "no data".

Usage:
  python3 drift_check.py --baseline results/cluster-20260427 \
                         --current  results/cluster-20260501

  # Bound the comparison to specific tasks:
  python3 drift_check.py --baseline ... --current ... --tasks solve validate_plan

  # Only print drifted rows (default also prints "no drift" summary line):
  python3 drift_check.py --baseline ... --current ... --quiet
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Sibling-script imports (parse_dirname) and harness imports (wilson_ci,
# TRIAL_KEY_LEN). Both path inserts run unconditionally — the analyzer
# scripts are designed to be invoked from the repo root, where pddl_eval/
# is importable; aggregate.py sits next to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from aggregate import parse_dirname  # noqa: E402
from pddl_eval.runner import TRIAL_KEY_LEN  # noqa: E402
from pddl_eval.summary import wilson_ci  # noqa: E402

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]


def _aggregate_trials_jsonl(path: Path) -> dict[str, dict[str, int]]:
    """Read trials.jsonl, group by task, return {task: {n, successes}}.

    Used as a mid-sweep fallback when no summary_*.json exists yet. The
    JSONL is per-trial, so n/successes are exact for whatever trials
    have completed so far. Bad lines (partial tail, malformed) are
    dropped silently — same policy as pddl_eval.resume.load_progress.
    Wrong-length keys are also dropped silently rather than raising
    (the loader in pddl_eval/resume.py raises; here we degrade to
    "summary_*.json wins" so an old JSONL doesn't block drift checks
    on a cell that does have a current summary).
    """
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "successes": 0})
    seen_keys: set[tuple] = set()
    with path.open("r") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
                key = tuple(rec["key"])
                result = rec["result"]
                task = result["task"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            if len(key) != TRIAL_KEY_LEN:
                continue
            if key in seen_keys:
                continue
            seen_keys.add(key)
            out[task]["n"] += 1
            if result.get("success"):
                out[task]["successes"] += 1
    return dict(out)


def _load_cell(cell_dir: Path) -> tuple[str, dict[str, dict[str, int]]] | None:
    """Return (source, {task: {n, successes}}) for one slurm_* dir.

    Source is "summary" if a summary_*.json was used, "trials" if the
    JSONL was aggregated, "empty" if neither yields any data. Returns
    None when the dir contains nothing aggregable.
    """
    summaries = sorted(cell_dir.glob("summary_*.json"))
    if summaries:
        with summaries[-1].open() as f:
            data = json.load(f)
        per_task: dict[str, dict[str, int]] = {}
        for r in data.get("single_task", []):
            t = r.get("task")
            n = r.get("n", 0)
            if not t or n == 0:
                continue
            per_task[t] = {"n": n, "successes": r.get("successes", 0)}
        if per_task:
            return ("summary", per_task)
    trials_file = cell_dir / "trials.jsonl"
    if trials_file.exists() and trials_file.stat().st_size > 0:
        per_task = _aggregate_trials_jsonl(trials_file)
        if per_task:
            return ("trials", per_task)
    return None


def _load_root(root: Path) -> dict[tuple, tuple[str, dict[str, dict[str, int]]]]:
    """Walk root, return {(model, think, cond): (source, {task: counts})}."""
    rows: dict[tuple, tuple[str, dict[str, dict[str, int]]]] = {}
    for d in sorted(root.glob("slurm_*")):
        if not d.is_dir():
            continue
        info = parse_dirname(d.name)
        if not info or info.get("model") in ("?", None) or info.get("cond") == "?":
            continue
        cell_data = _load_cell(d)
        if cell_data is None:
            continue
        rows[(info["model"], info["think"], info["cond"])] = cell_data
    return rows


def _classify_drift(
    base_n: int, base_k: int,
    cur_n: int, cur_k: int,
) -> str:
    """Return 'none' if current point estimate is inside baseline CI, else direction."""
    if base_n == 0 or cur_n == 0:
        return "no-data"
    cur_p = cur_k / cur_n
    base_lo, base_hi = wilson_ci(base_k, base_n)
    if base_lo <= cur_p <= base_hi:
        return "none"
    return "below" if cur_p < base_lo else "above"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--baseline", required=True, type=Path,
                   help="Reference results root (e.g. a finished sweep).")
    p.add_argument("--current", required=True, type=Path,
                   help="Sweep being checked. Can be in-flight (uses trials.jsonl per cell) or finished.")
    p.add_argument("--tasks", nargs="+", default=TASKS, choices=TASKS,
                   help="Tasks to check. Default: all 5.")
    p.add_argument("--quiet", action="store_true",
                   help="Only print drifted rows; suppress the 'no drift' summary.")
    args = p.parse_args()

    if not args.baseline.is_dir():
        sys.exit(f"--baseline: {args.baseline} is not a directory")
    if not args.current.is_dir():
        sys.exit(f"--current:  {args.current} is not a directory")

    base = _load_root(args.baseline)
    cur = _load_root(args.current)

    if not cur:
        sys.exit(f"--current: no parseable slurm_* cells under {args.current}")

    drifted: list[dict] = []
    checked = 0
    skipped_no_baseline = 0
    for cell, (cur_src, cur_tasks) in cur.items():
        if cell not in base:
            skipped_no_baseline += 1
            continue
        _, base_tasks = base[cell]
        for task in args.tasks:
            base_t = base_tasks.get(task)
            cur_t = cur_tasks.get(task)
            if not base_t or not cur_t:
                continue
            checked += 1
            verdict = _classify_drift(
                base_t["n"], base_t["successes"],
                cur_t["n"], cur_t["successes"],
            )
            if verdict in ("none", "no-data"):
                continue
            base_lo, base_hi = wilson_ci(base_t["successes"], base_t["n"])
            drifted.append({
                "cell": cell, "task": task, "src": cur_src,
                "base_p": base_t["successes"] / base_t["n"],
                "base_n": base_t["n"], "base_lo": base_lo, "base_hi": base_hi,
                "cur_p": cur_t["successes"] / cur_t["n"],
                "cur_n": cur_t["n"], "verdict": verdict,
            })

    print(f"# Drift check — `{args.current}` vs `{args.baseline}`")
    print(f"\n_Compared {checked} (cell, task) pairs; "
          f"{skipped_no_baseline} current cells had no baseline counterpart._\n")

    if not drifted:
        if not args.quiet:
            print(f"**No drift detected** — every checked pair has the current point "
                  f"estimate inside the baseline's Wilson 95% CI.")
        return 0

    print(f"**{len(drifted)} drifted (cell, task) pair(s)** — current point estimate "
          f"outside baseline 95% CI.\n")
    print("| model | think | cond | task | src | baseline (n) | baseline 95% CI | current (n) | direction |")
    print("|---|---|---|---|---|---|---|---|---|")
    for d in drifted:
        m, th, c = d["cell"]
        print(
            f"| {m} | {th} | {c} | {d['task']} | {d['src']} | "
            f"{d['base_p']*100:.0f}% (n={d['base_n']}) | "
            f"[{d['base_lo']*100:.0f}%–{d['base_hi']*100:.0f}%] | "
            f"{d['cur_p']*100:.0f}% (n={d['cur_n']}) | "
            f"**{d['verdict']}** |"
        )
    print()
    print("_`src` is the data source for the current row: `summary` = latest "
          "`summary_*.json`, `trials` = aggregated `trials.jsonl` (sweep is "
          "still in flight). `direction=above` is uniformly good news; "
          "`below` warrants investigation._")
    return 1 if any(d["verdict"] == "below" for d in drifted) else 0


if __name__ == "__main__":
    sys.exit(main())
