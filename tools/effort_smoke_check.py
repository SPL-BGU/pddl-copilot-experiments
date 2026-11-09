#!/usr/bin/env python3
"""Pass/fail read of the gpt-oss reasoning-effort smoke (2026-11-09).

The smoke is one array job of four cells, gpt-oss:20b at effort-low and at
default (Harmony's medium), each in no-tools and tools_all_minimal, with
--store-reasoning. Point this at the results root that holds the four
cells; it reads only, and prints one block per cond plus a verdict.

Pass criteria (all three, per cond):
  1. completion tokens fall at low effort: on the trials both cells ran
     (matched on task, domain, problem, plan label, variant), the median of
     (low minus default) completion tokens is below 0;
  2. the served Harmony system line shows the effort: client_settings.json
     records `Reasoning: low` for the low cell and `Reasoning: medium` for
     the default cell;
  3. the trace field fills: at least 90% of the rows that did not hit the
     output cap have a non-empty `thinking` in each cell.

Descriptive only (a handful of trials, no intervals); not a result.

    python3 tools/effort_smoke_check.py RESULTS_ROOT [--tag effort-smoke]
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

MODEL_TAG = "gpt-oss_20b"
CONDS = ("no-tools", "tools_all_minimal")


def load_rows(cell: Path) -> dict:
    rows = {}
    with (cell / "trials.jsonl").open(errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)["result"]
            except (ValueError, KeyError):
                continue   # tolerate a torn line
            key = (r["task"], r["domain_name"], r["problem_name"],
                   r.get("plan_label", ""), r["prompt_variant"])
            rows[key] = r
    return rows


def settings_line(cell: Path) -> str:
    p = cell / "client_settings.json"
    if not p.exists():
        return ""
    return json.loads(p.read_text()).get("harmony_system_line") or ""


def trace_share(rows: dict) -> tuple[int, int]:
    done = [r for r in rows.values() if r.get("done_reason") != "length"]
    return sum(1 for r in done if r.get("thinking")), len(done)


def check_cond(root: Path, cond: str, tag: str) -> bool:
    low_dir = root / f"slurm_vllm_{MODEL_TAG}_effort-low_{cond}_{tag}"
    def_dir = root / f"slurm_vllm_{MODEL_TAG}_default_{cond}_{tag}"
    print(f"== {cond}")
    for d in (low_dir, def_dir):
        if not (d / "trials.jsonl").exists():
            print(f"  missing {d}")
            return False
    low, base = load_rows(low_dir), load_rows(def_dir)
    keys = sorted(set(low) & set(base))
    diffs = [low[k]["tokens"].get("completion", 0) - base[k]["tokens"].get("completion", 0)
             for k in keys]
    med = statistics.median(diffs) if diffs else None
    mean_low = statistics.mean(low[k]["tokens"].get("completion", 0) for k in keys) if keys else 0
    mean_def = statistics.mean(base[k]["tokens"].get("completion", 0) for k in keys) if keys else 0
    ok1 = med is not None and med < 0
    print(f"  matched trials {len(keys)}; mean completion tokens low {mean_low:.0f} / "
          f"default {mean_def:.0f}; median(low - default) {med}  -> {'ok' if ok1 else 'FAIL'}")
    line_low, line_def = settings_line(low_dir), settings_line(def_dir)
    ok2 = "Reasoning: low (expected low)" in line_low and \
          "Reasoning: medium (expected medium)" in line_def
    print(f"  system line low:     {line_low or '(none recorded)'}")
    print(f"  system line default: {line_def or '(none recorded)'}  -> {'ok' if ok2 else 'FAIL'}")
    ok3 = True
    for name, rows in (("low", low), ("default", base)):
        filled, n = trace_share(rows)
        share = filled / n if n else 0.0
        ok3 = ok3 and n > 0 and share >= 0.9
        print(f"  trace filled ({name}): {filled}/{n} rows not at the cap ({100 * share:.1f}%)")
    print(f"  trace check -> {'ok' if ok3 else 'FAIL'}")
    return ok1 and ok2 and ok3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("--tag", default="effort-smoke")
    args = ap.parse_args(argv)
    results = [check_cond(args.root, c, args.tag) for c in CONDS]
    verdict = all(results)
    print(f"\nsmoke {'PASSED' if verdict else 'FAILED'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
