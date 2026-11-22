#!/usr/bin/env python3
"""LaTeX table bodies for the paper's RQ2 and RQ3 sections, from out/rq23_metrics.json.

    python -m tools.reanalysis.rq23_tex

Writes tools/reanalysis/out/tex/rq2_choice.tex (three panels: exactly the right
tool, the right tool called, another tool called; rerun and Claude, thinking
off), rq2_thinking.tex (main sweep, plain prompt, the right tool called, thinking
off and on) and rq3_lost.tex (share of correct tool results lost). `paper/main.tex`
holds a pasted copy; regenerate and paste again after a rerun of
`rq23_metrics.py`, and never edit a number in the tex by hand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = ("validate_domain", "validate_problem", "validate_plan", "solve", "simulate")
NAMES = {"Qwen3.5-0.8B": "Qwen3.5-0.8B", "Qwen3.5-4B": "Qwen3.5-4B", "Qwen3.5-9B": "Qwen3.5-9B",
         "Gemma-26B": "Gemma-MoE-26B", "Qwen3.6-35B": "Qwen3.6-35B",
         "Claude Haiku 4.5": "Claude Haiku~4.5", "Claude Sonnet 4.6": "Claude Sonnet~4.6"}
ROWS = (("rerun", "Qwen3.5-9B"), ("rerun", "Gemma-26B"), ("rerun", "Qwen3.6-35B"),
        ("Claude", "Claude Haiku 4.5"), ("Claude", "Claude Sonnet 4.6"))
ARMS = (("plain", "plain"), ("steered", "steered"))


def ci(b: dict) -> str:
    return f"${b['est']:.1f}$ {{\\scriptsize$[{b['lo']:.1f},\\,{b['hi']:.1f}]$}}"


def block(lines: list[list[str]]) -> str:
    return "\n".join(" & ".join(r) + r" \\" for r in lines) + "\n"


def choice_panel(by: dict, field: str) -> list[list[str]]:
    out = []
    for corpus, m in ROWS:
        first = True
        for a, arm in ARMS:
            if (corpus, m, "off", a, TASKS[0]) not in by:
                continue
            out.append([NAMES[m] if first else "", arm,
                        *[ci(by[(corpus, m, "off", a, t)][field]) for t in TASKS]])
            first = False
    return out


def main() -> int:
    res = json.loads((HERE / "out" / "rq23_metrics.json").read_text())
    out = HERE / "out" / "tex"
    out.mkdir(parents=True, exist_ok=True)
    by = {(c["corpus"], c["model"], c["think"], c["arm"], c["task"]): c
          for c in res["rq2"]["cells"]}
    panels = []
    for field, title in (("exactly_right", "Exactly the right tool and no other (\\%)"),
                         ("right_called", "The right tool was called (\\%)"),
                         ("other_called", "Another tool was called (\\%)")):
        panels.append(f"\\multicolumn{{7}}{{@{{}}l}}{{\\emph{{{title}}}}} \\\\\n"
                      + block(choice_panel(by, field)))
    (out / "rq2_choice.tex").write_text("\\addlinespace\n".join(panels))
    think = []
    for m in ("Qwen3.5-0.8B", "Qwen3.5-4B", "Qwen3.5-9B", "Gemma-26B", "Qwen3.6-35B"):
        for i, th in enumerate(("off", "on")):
            think.append([NAMES[m] if i == 0 else "", th,
                          *[ci(by[("main sweep", m, th, "plain", t)]["right_called"])
                            for t in TASKS]])
    (out / "rq2_thinking.tex").write_text(block(think))
    by3 = {(c["corpus"], c["model"], c["arm"], c["task"]): c
           for corpus in ("rerun", "Claude") for c in res["rq3"][corpus]}
    lost = []
    for corpus, m in ROWS:
        first = True
        for a, arm in ARMS:
            if (corpus, m, a, TASKS[0]) not in by3:
                continue
            cells = []
            for t in TASKS:
                c = by3[(corpus, m, a, t)]
                cells.append(ci(c["lost"]) + (f"$^{{\\ddagger{c['n_unknown']}}}$"
                                              if c["n_unknown"] else ""))
            lost.append([NAMES[m] if first else "", arm, *cells])
            first = False
    (out / "rq3_lost.tex").write_text(block(lost))
    print(f"wrote {out}/rq2_choice.tex, rq2_thinking.tex, rq3_lost.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
