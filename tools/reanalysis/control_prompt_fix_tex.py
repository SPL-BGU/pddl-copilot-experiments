"""LaTeX rows for the corrected-prompt control, from the generated analysis output
(`tools/reanalysis/out/control_prompt_fix.json`). Reads no trial; changes no number.

    python -m tools.reanalysis.control_prompt_fix_tex

Writes three row files next to the JSON; the paper's tables hold their contents.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
MODELS = [("Qwen3_5_9B", "Qwen3.5-9B"), ("gemma4_26b-a4b", "Gemma-MoE-26B"),
          ("qwen3_6_35b", "Qwen3.6-35B")]
TASKS = ["solve", "simulate"]
CELLS = [("O", "registered text"), ("A", "reference removed"), ("B", "format stated")]
CONTRASTS = [("C1", "reference removed minus registered"),
             ("C2", "format stated minus registered"),
             ("C4", "+tool (plain) minus format stated")]


def rate(b: dict) -> str:
    return (f"${b['est']:.1f}$ {{\\scriptsize$[{b['lo']:.1f},\\,{b['hi']:.1f}]$}}")


def diff(b: dict) -> str:
    return (f"${b['est']:+.1f}$ {{\\scriptsize$[{b['lo']:+.1f},\\,{b['hi']:+.1f}]$}}")


def main() -> int:
    d = json.loads((OUT / "control_prompt_fix.json").read_text())
    rates = {(r["model"], r["task"], r["cell"]): r for r in d["rates"]}
    cons = {(c["name"], c["model"], c["task"], c["reading"]): c for c in d["contrasts"]}
    assert len(rates) == len(d["rates"]) and len(cons) == len(d["contrasts"])

    main_rows, cell_rows, con_rows = [], [], []
    for mi, (m, name) in enumerate(MODELS):
        for ti, t in enumerate(TASKS):
            b, a = rates[(m, t, "B")], rates[(m, t, "Part A")]
            c4 = cons[("C4", m, t, "second")]
            main_rows.append(f"{name if ti == 0 else ''} & \\emph{{{t}}} & {rate(b['second'])} & "
                             f"{rate(a['second'])} & {diff(c4)} \\\\")
            for ci, (cell, label) in enumerate(CELLS):
                r = rates[(m, t, cell)]
                cell_rows.append(f"{name if (ti, ci) == (0, 0) else ''} & "
                                 f"{'\\emph{' + t + '}' if ci == 0 else ''} & {label} & "
                                 f"{rate(r['frozen'])} & {rate(r['second'])} \\\\")
        if mi < len(MODELS) - 1:
            main_rows.append("\\addlinespace")
            cell_rows.append("\\addlinespace")
    for ki, (c, label) in enumerate(CONTRASTS):
        for mi, (m, name) in enumerate(MODELS):
            for t in TASKS:
                con_rows.append(f"{label if (mi, t) == (0, 'solve') else ''} & {name if t == 'solve' else ''} & "
                                f"\\emph{{{t}}} & {diff(cons[(c, m, t, 'frozen')])} & "
                                f"{diff(cons[(c, m, t, 'second')])} \\\\")
        if ki < len(CONTRASTS) - 1:
            con_rows.append("\\addlinespace")
    for fn, rows in [("control_prompt_fix_main.tex", main_rows),
                     ("control_prompt_fix_cells.tex", cell_rows),
                     ("control_prompt_fix_contrasts.tex", con_rows)]:
        (OUT / fn).write_text("\n".join(rows) + "\n")
        print(f"wrote {OUT / fn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
