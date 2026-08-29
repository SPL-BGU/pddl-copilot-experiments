#!/usr/bin/env python3
"""D2b strict (i) vs delegation-credit (B) comparison over an existing e2e
overlay (output of tools/e2e_regrade.py).

Pure arithmetic, no regrade, no MCP: the two rules differ only on rows whose
e2e_reason is "delegation_terminal_credit", so both columns derive from the
stored overlay rows (works on overlays written before e2e_regrade.py emitted
the explicit e2e_strict column).

For each model x task it prints the no-tools reference bounds, the with-tools
bounds under both rules, the delegation-credit mass, and the tool-lift verdict
under each rule; rows where the verdict differs between rules are flagged
FLIP. Decision support for D2b — see
development/reference/decision_audit_grading_and_frontier.md §1.3.

Verdict semantics (per-row means; censoring bounds, not sampling CIs):
  lift      tools lower bound > no-tools upper bound
  inverted  tools upper bound < no-tools lower bound
  straddle  the intervals overlap — the corpus cannot decide the cell
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

TASK_ORDER = ("validate_domain", "validate_problem", "validate_plan",
              "solve", "simulate")
DELEG = "delegation_terminal_credit"


def load_overlay(overlay_dir: Path) -> list[dict]:
    rows = []
    for f in sorted(overlay_dir.glob("*.e2e.jsonl")):
        for ln in f.open():
            rows.append(json.loads(ln))
    return rows


def bounds(rs: list[dict], strict: bool) -> tuple[float, float]:
    n = len(rs)
    lo = sum(1 for r in rs
             if r["e2e"] is True and not (strict and r["e2e_reason"] == DELEG))
    ind = sum(1 for r in rs if r["e2e"] == "indeterminate")
    return lo / n, (lo + ind) / n


def verdict(nt: tuple[float, float], tl: tuple[float, float]) -> str:
    if tl[0] > nt[1]:
        return "lift"
    if tl[1] < nt[0]:
        return "inverted"
    return "straddle"


def compare(overlay_dir: Path) -> None:
    rows = load_overlay(overlay_dir)
    cells = defaultdict(list)
    for r in rows:
        arm = "tools" if r["with_tools"] else "nt"
        cells[(r["model"], r["task"], arm)].append(r)

    flips = 0
    deleg_total = sum(1 for r in rows if r["e2e_reason"] == DELEG)
    print(f"\n{'=' * 124}\n{overlay_dir.name}: D2b strict (i) vs "
          f"delegation-credit (B) — {deleg_total} credited rows of "
          f"{len(rows)} total\n{'=' * 124}")
    print(f"{'model':34s} {'task':17s} {'n':>5s} {'no-tools':>13s} "
          f"{'strict[lo,hi]':>14s} {'B[lo,hi]':>14s} {'deleg':>6s} "
          f"{'v(strict)':>9s} {'v(B)':>9s}")
    models = sorted({m for m, _, _ in cells})
    for model in models:
        for task in TASK_ORDER:
            tl = cells.get((model, task, "tools"))
            nt = cells.get((model, task, "nt"))
            if not tl or not nt:
                continue
            nt_b = bounds(nt, strict=False)  # no-tools has no deleg rows
            s_b = bounds(tl, strict=True)
            b_b = bounds(tl, strict=False)
            deleg = sum(1 for r in tl if r["e2e_reason"] == DELEG) / len(tl)
            vs, vb = verdict(nt_b, s_b), verdict(nt_b, b_b)
            flag = "  FLIP" if vs != vb else ""
            if flag:
                flips += 1
            print(f"{model:34s} {task:17s} {len(tl):5d} "
                  f"[{100 * nt_b[0]:5.1f},{100 * nt_b[1]:5.1f}] "
                  f"[{100 * s_b[0]:5.1f},{100 * s_b[1]:5.1f}] "
                  f"[{100 * b_b[0]:5.1f},{100 * b_b[1]:5.1f}] "
                  f"{100 * deleg:6.1f} {vs:>9s} {vb:>9s}{flag}")
    print(f"\nverdict flips strict-vs-B: {flips}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("overlays", nargs="*",
                    default=["results/derived/e2e_overlay/sweep5v2-live"],
                    help="overlay dirs (results/derived/e2e_overlay/<corpus>)")
    args = ap.parse_args()
    for d in args.overlays:
        p = Path(d)
        if p.is_dir():
            compare(p)
        else:
            print(f"skip (not a dir): {d}")


if __name__ == "__main__":
    main()
