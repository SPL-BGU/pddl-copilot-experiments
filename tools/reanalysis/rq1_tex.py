#!/usr/bin/env python3
"""LaTeX table bodies for the paper's RQ1 section, from out/rq1_metrics.json.

    python -m tools.reanalysis.rq1_tex

Writes tools/reanalysis/out/tex/rq1_{verdicts,simulate,solve,planlen}.tex: the
rows between \\midrule and \\bottomrule of each table. `paper/main.tex` holds a
pasted copy (the Overleaf project is one file), so after a rerun of
`rq1_metrics.py` regenerate these and paste them again; never edit a number in
the tex by hand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = (("Qwen3.5-9B", "Qwen3.5-9B"), ("Gemma-26B", "Gemma-MoE-26B"),
          ("Qwen3.6-35B", "Qwen3.6-35B"), ("Claude Haiku 4.5", "Claude Haiku~4.5"),
          ("Claude Sonnet 4.6", "Claude Sonnet~4.6"))
ARMS = (("none", "no-tools"), ("plain", "+tool (plain)"), ("tools", "+tool (plain)"),
        ("steered", "+tool (steered)"))


def ci(b: dict) -> str:
    return f"${b['est']:.1f}$ {{\\scriptsize$[{b['lo']:.1f},\\,{b['hi']:.1f}]$}}"


def rho(s: dict) -> str:
    return "--" if s["rho"] is None else f"${s['rho']:+.2f}$"


def rows(cells: list[dict], fmt) -> str:
    by = {(c["model"], c["arm"]): c for c in cells}
    out = []
    for i, (m, name) in enumerate(MODELS):
        first = True
        for a, arm in ARMS:
            if (m, a) not in by:
                continue
            out.append(" & ".join([name if first else "", arm, *fmt(by[(m, a)])]) + r" \\")
            first = False
        if i < len(MODELS) - 1:
            out.append(r"\addlinespace")
    return "\n".join(out) + "\n"


def main() -> int:
    res = json.loads((HERE / "out" / "rq1_metrics.json").read_text())
    out = HERE / "out" / "tex"
    out.mkdir(parents=True, exist_ok=True)
    (out / "rq1_verdicts.tex").write_text(rows(res["m1"]["cells"], lambda c: [
        ci(c["fn_rate"]), ci(c["fp_rate"]),
        f"${c['valid_none'] + c['broken_none']}$ / ${c['n_valid'] + c['n_broken']}$",
        ci(c["correct"])]))
    (out / "rq1_simulate.tex").write_text(rows(res["m2"]["overall"], lambda c: [
        ci(c["exact"]) + ("" if c["exact_known"] == c["n"]
                          else f"$^{{\\ddagger{c['n'] - c['exact_known']}}}$"),
        ci(c["states"]), ci(c["states_salvaged"]), f"${c['no_trace']}$ / ${c['n']}$",
        rho(c["rho_states"])]))
    (out / "rq1_solve.tex").write_text(rows(res["m3"]["corr"], lambda c: [
        ci(c["solved"]), rho(c["rho_len"]), rho(c["rho_obj"]), rho(c["rho_time"])]))
    (out / "rq1_planlen.tex").write_text(rows(res["m4"]["cells"], lambda c: [
        f"${c['n_valid']}$ / ${c['n_trials']}$", f"${c['mean_len']:.1f}$",
        f"${c['mean_ref_len']:.1f}$", f"${c['median_ratio']:.2f}$",
        f"${c['shorter']}$ / ${c['equal']}$ / ${c['longer']}$", f"${c['max_ratio']:.1f}$",
        (f"${c['same_len_as_tool_plan']}$ / ${c['with_tool_plan']}$"
         if c["with_tool_plan"] else "--")]))
    print(f"wrote {out}/rq1_{{verdicts,simulate,solve,planlen}}.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
