"""C12 — success per prompt wording (the paper pools the three wordings).

For each headline open model (think off) x task x arm, the three wordings are
reported separately:

  no-tools       v11 / v12 / v13
  tools-plain    v11 / v12 / v13   (same user text as no-tools)
  tools-steered  v14 / v15 / v16   (v11/12/13 + one "use the X tool" sentence)

Two scores per cell (see bc_common.py docstring):
  harness    stored `success` (tool-verified on tool arms; strict online grade
             of the final answer on the no-tools arm), exact, Wilson 95%.
  delivered  overlay e2e_strict; a point with Wilson 95% when no row is
             censored, otherwise the bound <low, high> with the censored count.

Spread = max - min over the three wordings. For a censored delivered cell three
numbers are given: spread of the low ends, spread of the high ends, and the
"guaranteed" spread max(0, max low - min high), i.e. the gap that survives
every way of resolving the censored rows.

    python3 tools/reanalysis/bc_per_wording.py [--corpus sweep5v2-live]

Writes out/breakdowns_cost/per_wording_<corpus>.{csv,md}.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bc_common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="sweep5v2-live")
    args = ap.parse_args()
    cells = C.open_cells(args.corpus)
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_rows = []
    md = [f"# Per-wording success, {args.corpus}, think off", ""]
    for task in C.TASKS:
        md += [f"## {task}", ""]
        trows = []
        for mkey, mdisp in C.HEADLINE:
            for arm in C.ARMS:
                per = {}
                for w in ("w1", "w2", "w3"):
                    rows = [r for r in cells[mkey]
                            if r["task"] == task and r["arm"] == arm
                            and C.WORDING[r["pv"]] == w]
                    per[w] = C.agg(rows)
                    a = per[w]
                    pv = sorted({r["pv"] for r in rows})
                    lo, hi = C.wilson(a["harness_ok"], a["n"])
                    csv_rows.append({
                        "corpus": args.corpus, "model": mkey, "task": task, "arm": arm,
                        "wording": w, "prompt_variant": pv[0] if pv else "",
                        "n": a["n"], "harness_ok": a["harness_ok"],
                        "harness_rate": round(a["harness_ok"] / a["n"], 4),
                        "harness_wilson_lo": round(lo, 4), "harness_wilson_hi": round(hi, 4),
                        "called": a["called"] if arm != "nt-neut" else "",
                        "delivered_ok": a["ok"], "delivered_censored": a["cens"],
                        "delivered_low": round(a["ok"] / a["n"], 4),
                        "delivered_high": round((a["ok"] + a["cens"]) / a["n"], 4),
                    })
                n = per["w1"]["n"]
                h = [100 * per[w]["harness_ok"] / per[w]["n"] for w in per]
                lows = [100 * per[w]["ok"] / per[w]["n"] for w in per]
                highs = [100 * (per[w]["ok"] + per[w]["cens"]) / per[w]["n"] for w in per]
                any_cens = any(per[w]["cens"] for w in per)
                label = "tool-verified" if arm != "nt-neut" else "final answer, strict"
                trows.append([mdisp, C.ARM_DISP[arm], label, n]
                             + [C.fmt_rate(per[w]["harness_ok"], per[w]["n"]) for w in per]
                             + [f"{max(h) - min(h):.1f}"])
                if arm != "nt-neut" or any_cens:
                    if any_cens:
                        sp = (f"low {max(lows) - min(lows):.1f} / high "
                              f"{max(highs) - min(highs):.1f} / guaranteed "
                              f"{max(0.0, max(lows) - min(highs)):.1f}")
                    else:
                        sp = f"{max(lows) - min(lows):.1f}"
                    trows.append(["", "", "delivered", n]
                                 + [C.fmt_deliv(per[w]) for w in per] + [sp])
                if arm != "nt-neut":
                    trows.append(["", "", "tool called", n]
                                 + [C.fmt_rate(per[w]["called"], per[w]["n"]) for w in per]
                                 + [f"{max(100 * per[w]['called'] / per[w]['n'] for w in per) - min(100 * per[w]['called'] / per[w]['n'] for w in per):.1f}"])
        md.append(C.md_table(
            ["model", "arm", "score", "n per wording", "wording 1 (v11/v14)",
             "wording 2 (v12/v15)", "wording 3 (v13/v16)", "max-min (pp)"], trows))
        md.append("")

    # Frontier: the only frontier arm run with all three wordings is Sonnet
    # no-tools (v11-13). Every frontier tool run, and Haiku no-tools, is v11 only.
    fr_corpus_cell = {"sweep5v2-live": "sweep5v2", "sweep6-live": "sweep6"}[args.corpus]
    md += [f"## Frontier: which wordings exist ({fr_corpus_cell} prompt corpus)", ""]
    inv = []
    for corpus in ("sonnet-frontier", "haiku-frontier"):
        for cell in (fr_corpus_cell, f"{fr_corpus_cell}-with-tools"):
            if not (C.OVERLAY / corpus / f"{cell}.e2e.jsonl").exists():
                inv.append([corpus, cell, "not run", ""])
                continue
            rows = C.load_cell(corpus, cell)
            pvs = sorted({r["pv"] for r in rows})
            inv.append([corpus, cell, ", ".join(f"v{v}" for v in pvs), len(rows)])
    md += [C.md_table(["tier", "cell", "wordings present", "trials"], inv), "",
           "## Sonnet 4.6 no-tools, per wording (delivered)", ""]
    srows = C.load_cell("sonnet-frontier", fr_corpus_cell)
    trows = []
    for task in C.TASKS:
        per = {v: C.agg([r for r in srows if r["task"] == task and r["pv"] == v])
               for v in C.NEUTRAL}
        lows = [100 * a["ok"] / a["n"] for a in per.values()]
        highs = [100 * (a["ok"] + a["cens"]) / a["n"] for a in per.values()]
        if any(a["cens"] for a in per.values()):
            sp = (f"low {max(lows) - min(lows):.1f} / high {max(highs) - min(highs):.1f} / "
                  f"guaranteed {max(0.0, max(lows) - min(highs)):.1f}")
        else:
            sp = f"{max(lows) - min(lows):.1f}"
        trows.append([task, per[11]["n"]] + [C.fmt_deliv(per[v]) for v in C.NEUTRAL] + [sp])
        for v in C.NEUTRAL:
            a = per[v]
            csv_rows.append({
                "corpus": f"sonnet-frontier/{fr_corpus_cell}", "model": "claude-sonnet-4-6",
                "task": task, "arm": "nt-neut", "wording": C.WORDING[v], "prompt_variant": v,
                "n": a["n"], "harness_ok": a["harness_ok"],
                "harness_rate": round(a["harness_ok"] / a["n"], 4),
                "harness_wilson_lo": round(C.wilson(a["harness_ok"], a["n"])[0], 4),
                "harness_wilson_hi": round(C.wilson(a["harness_ok"], a["n"])[1], 4),
                "called": "", "delivered_ok": a["ok"], "delivered_censored": a["cens"],
                "delivered_low": round(a["ok"] / a["n"], 4),
                "delivered_high": round((a["ok"] + a["cens"]) / a["n"], 4),
            })
    md += [C.md_table(["task", "n per wording", "wording 1 (v11)", "wording 2 (v12)",
                       "wording 3 (v13)", "max-min (pp)"], trows), ""]

    out_csv = C.OUT_DIR / f"per_wording_{args.corpus}.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)
    out_md = C.OUT_DIR / f"per_wording_{args.corpus}.md"
    out_md.write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"wrote {out_csv.relative_to(C.REPO)} and {out_md.relative_to(C.REPO)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
