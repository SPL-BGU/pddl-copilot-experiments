#!/usr/bin/env python3
"""nt-ster H4 — frozen entry point 1 of 2: the noise-floor control F (§3.2).

F is computed from the ANCHOR arm alone (v11/v12/v13), so it is blind to the
steered arm by construction. It must be produced **before** the H4 contrast is
read; `ntster_h4.py` refuses to run without the JSON this script writes, which
makes "F before the contrast" an enforced order rather than a promise.

WHAT F IS
    F = max |Δ̂| over the three within-anchor paraphrase pairs — v11-v12,
    v11-v13, v12-v13. These contrasts are designed nulls: same fixtures, same
    arm, only the paraphrase differs. Whatever they move is not steering.

WHERE IT BINDS (§3.2, as amended 2026-07-25)
    * At POOLED granularity F is a bank-validity check, not the operative noise.
      With equal n per variant the pooled Δ is exactly (1/3)Σ[p(v+3) − p(v)], so
      the paraphrase main effect cancels arithmetically and F measures what the
      design already removes. The "F ≥ margin ⇒ UNINFORMATIVE" clause is retained
      there but is not expected to fire.
    * At every granularity where a verdict is read, F is a **gate**. On canonical
      no-tools data the same designed-null pairs move `solve` by 6.0-30.0pp in
      all six cells. A model × mode × task cell whose own F ≥ the margin is
      UNINFORMATIVE and cannot contribute a FAIL. Without this the §3.4 decision
      rule is a false-FAIL machine.

Usage:
    python tools/ntster_f_gate.py --overlay-dir results/derived/e2e_overlay/ntster-h4-live
    python tools/ntster_f_gate.py ... --out results/derived/ntster_f_gate.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ntster_common import (  # noqa: E402  (sibling module, same dir)
    ALPHA, MARGIN_PP, NEUTRAL_VARIANTS, TASKS,
    Cell, arm_rate, build_pairs, completeness_gate, delivered, legacy,
    load_overlay_cells, paired_cluster_ci, pct,
)

DEFAULT_OUT = Path("results/derived/ntster_f_gate.json")


def _paraphrase_pairs() -> list[tuple[int, int]]:
    return list(itertools.combinations(NEUTRAL_VARIANTS, 2))


def f_for(cell: Cell, *, task: str | None) -> dict:
    """Compute F at one granularity, plus the per-pair detail behind it."""
    detail = []
    for vlo, vhi in _paraphrase_pairs():
        pairs = build_pairs(cell, lo=(vlo,), hi=(vhi,), surface=delivered, task=task)
        ci_dom = paired_cluster_ci(pairs, lambda p: p.domain, method="domain")
        xlo, nlo = _variant_rate(cell, vlo, task)
        xhi, nhi = _variant_rate(cell, vhi, task)
        detail.append({
            "pair": f"v{vlo}-v{vhi}",
            "delta_pp": ci_dom.estimate_pp,
            "abs_delta_pp": abs(ci_dom.estimate_pp),
            "half_width_pp": ci_dom.half_width_pp,
            "rate_lo_pp": pct(xlo, nlo),
            "rate_hi_pp": pct(xhi, nhi),
            "n_pairs": len(pairs),
        })
    finite = [d["abs_delta_pp"] for d in detail if not math.isnan(d["abs_delta_pp"])]
    f_value = max(finite) if finite else math.nan
    return {
        "F_pp": f_value,
        "F_ge_margin": (not math.isnan(f_value)) and f_value >= MARGIN_PP,
        "driving_pair": max(detail, key=lambda d: (-1.0 if math.isnan(d["abs_delta_pp"])
                                                   else d["abs_delta_pp"]))["pair"],
        "pairs": detail,
    }


def _variant_rate(cell: Cell, variant: int, task: str | None) -> tuple[int, int]:
    return arm_rate(cell, (variant,), task=task, surface=delivered)


def analyse(cell: Cell) -> dict:
    gate = completeness_gate(cell)
    out = {
        "cell": cell.name,
        "model": cell.model,
        "think": cell.think,
        "rows": cell.n,
        "duplicates_dropped": cell.duplicates_dropped,
        "completeness": {"ok": gate.ok, "lines": gate.lines,
                         "reweighting_needed": gate.reweighting_needed},
        "anchor_rate_pp": {},
        "granularity": {},
    }
    x, n = arm_rate(cell, NEUTRAL_VARIANTS, surface=delivered)
    out["anchor_rate_pp"]["pooled"] = pct(x, n)
    xl, nl = arm_rate(cell, NEUTRAL_VARIANTS, surface=legacy)
    out["anchor_rate_pp"]["pooled_legacy"] = pct(xl, nl)
    out["granularity"]["pooled"] = f_for(cell, task=None)

    for task in TASKS:
        xt, nt = arm_rate(cell, NEUTRAL_VARIANTS, task=task, surface=delivered)
        out["anchor_rate_pp"][task] = pct(xt, nt)
        out["granularity"][task] = f_for(cell, task=task)
    return out


def render(results: list[dict]) -> str:
    lines = ["# nt-ster H4 — F gate (§3.2)", "",
             f"Anchor arm only (v{'/v'.join(map(str, NEUTRAL_VARIANTS))}); "
             f"margin ±{MARGIN_PP:g}pp; {int((1-ALPHA)*100)}% intervals; "
             "surface = delivered.", "",
             "F = max |Δ̂| over the three designed-null paraphrase pairs. A cell "
             "whose own F ≥ the margin is UNINFORMATIVE at that granularity and "
             "cannot contribute a FAIL.", ""]

    for r in results:
        lines.append(f"## {r['cell']}")
        lines.append("")
        status = "COMPLETE" if r["completeness"]["ok"] else "INCOMPLETE — NOT ANALYSABLE"
        lines.append(f"- completeness: **{status}**")
        for ln in r["completeness"]["lines"]:
            lines.append(f"  - {ln}")
        lines.append("")
        lines.append("| granularity | anchor rate | F | driving pair | verdict |")
        lines.append("|---|---:|---:|---|---|")
        for gname in ["pooled"] + TASKS:
            g = r["granularity"][gname]
            anchor = r["anchor_rate_pp"][gname]
            # A granularity with no rows must never render as "usable" — that is
            # how a silent shortfall gets read as a pass.
            if math.isnan(anchor) or math.isnan(g["F_pp"]):
                lines.append(f"| {gname} | — | — | — | **NO DATA** |")
                continue
            verdict = "UNINFORMATIVE (F ≥ margin)" if g["F_ge_margin"] else "usable"
            lines.append(f"| {gname} | {anchor:.1f}% | {g['F_pp']:.2f}pp | "
                         f"{g['driving_pair']} | {verdict} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--overlay-dir", type=Path, required=True,
                    help="e.g. results/derived/e2e_overlay/ntster-h4-live")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--markdown", type=Path, default=None,
                    help="also write the rendered table here")
    args = ap.parse_args()

    cells = load_overlay_cells(args.overlay_dir)
    print(f"loaded {len(cells)} cell(s) from {args.overlay_dir}")

    results = [analyse(c) for c in cells]
    payload = {
        "produced_by": "tools/ntster_f_gate.py",
        "prereg": "development/ntster_h4_prereg.md §3.2",
        "overlay_dir": str(args.overlay_dir),
        "margin_pp": MARGIN_PP,
        "alpha": ALPHA,
        "surface": "delivered (overlay e2e)",
        "anchor_variants": list(NEUTRAL_VARIANTS),
        "cells": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"F gate written: {args.out}")

    md = render(results)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(md + "\n")
        print(f"markdown written: {args.markdown}")
    print()
    print(md)

    incomplete = [r["cell"] for r in results if not r["completeness"]["ok"]]
    if incomplete:
        print("\nWARNING: incomplete cell(s) — INCONCLUSIVE, not analysable on the "
              "surviving subset (§3.1): " + ", ".join(incomplete))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
