#!/usr/bin/env python3
"""Body tables and the verdict-error figure without the rows of the earlier Claude runs.

    python -m tools.reanalysis.open_weight_tex [--out DIR] [--figs DIR]

Since 2026-11-26 the hosted Claude models stand in a section of their own, on a new run
(`frontier55_tex.py`), and the rows of the earlier Claude runs (Haiku 4.5, Sonnet 4.6)
are in `paper/supplement_source.tex`. Three body tables and one figure are written by
generators that print those rows beside the open-weight ones: `rq1_tex.py`
(rq1_verdicts.tex) and `rq1_figures.py` are files of a frozen package and are not
edited, and `rq23_tex.py` (rq2_choice.tex, rq3_lost.tex) writes all its rows in one
pass. This script filters what they wrote. It reads no trial and computes nothing:

  out/tex/rq1_verdicts.tex  ->  out/tex/rq1_verdicts_open.tex
  out/tex/rq2_choice.tex    ->  out/tex/rq2_choice_open.tex
  out/tex/rq3_lost.tex      ->  out/tex/rq3_lost_open.tex

Each `_open` file holds the lines of its source, in order and unchanged, minus the rows
of a Claude model and minus an `\\addlinespace` left with no row after it. The script
halts when a row names a model it does not know or when a source holds no Claude row.

The figure `out/figs/rq1_validate_plan_errors_open.{pdf,png}` is drawn by
`rq1_figures.fig_errors` from `out/rq1_metrics.json`, with the model list of that
module replaced for the one call.

The three `rq1m_` tables and the two by-length figures have their own switch:
`rq1_matched_metrics.py --open-only`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.reanalysis import rq1_figures as FIG
from tools.reanalysis import rq1_tex as TEX

HERE = Path(__file__).resolve().parent
CLAUDE = ("Claude Haiku 4.5", "Claude Sonnet 4.6")
NAMES = dict(TEX.MODELS)                      # json name -> name in the tex
CLAUDE_TEX = tuple(NAMES[m] for m in CLAUDE)
OPEN_TEX = tuple(v for k, v in NAMES.items() if k not in CLAUDE)
TABLES = ("rq1_verdicts", "rq2_choice", "rq3_lost")
RULE = r"\addlinespace"


class Halt(Exception):
    pass


def split(text: str) -> tuple[str, str]:
    """(the open-weight form, the removed Claude rows) of a generated row file.

    A row is a line with cells; its first cell names the model, and an empty first cell
    continues the model of the row above. Every other line (a panel title, an
    `\\addlinespace`) is kept, except an `\\addlinespace` that the removal leaves at the
    start, at the end or directly after another one."""
    kept, removed, model = [], [], None
    for line in text.splitlines():
        if " & " not in line or line.startswith(r"\multicolumn"):
            kept.append(line)
            model = None
            continue
        first = line.split(" & ")[0]
        if first:
            if first not in CLAUDE_TEX + OPEN_TEX:
                raise Halt(f"a row names a model this script does not know: {first!r}")
            model = first
        if model is None:
            raise Halt(f"a row continues a model, and no row stands above it: {line[:60]!r}")
        (removed if model in CLAUDE_TEX else kept).append(line)
    if not removed:
        raise Halt("the source holds no Claude row")
    out = []
    for i, line in enumerate(kept):
        if line == RULE and (not out or out[-1] == RULE
                             or all(x == RULE for x in kept[i:])):
            continue
        out.append(line)
    return "\n".join(out) + "\n", "\n".join(removed) + "\n"


def write_tables(tex: Path) -> dict:
    """Writes the three `_open` files; returns {table: rows removed}."""
    n = {}
    for name in TABLES:
        kept, removed = split((tex / f"{name}.tex").read_text())
        (tex / f"{name}_open.tex").write_text(kept)
        n[name] = len(removed.splitlines())
    return n


def fig_errors_open(res: dict, figs: Path) -> None:
    """`rq1_figures.fig_errors` over the open-weight models, saved as `..._open`."""
    cells = [c for c in res["m1"]["cells"] if c["model"] not in CLAUDE]
    if len(cells) == len(res["m1"]["cells"]) or not cells:
        raise Halt("out/rq1_metrics.json does not hold both Claude and open-weight cells")
    models, save = FIG.MODELS, FIG.save

    def save_open(fig, out, name):
        fig.set_size_inches(7.6, 3.5)         # three groups of bars in place of five
        save(fig, out, name + "_open")

    FIG.MODELS = tuple(m for m in models if m not in CLAUDE)
    FIG.save = save_open
    try:
        FIG.fig_errors({"m1": {"cells": cells}}, figs)
    finally:
        FIG.MODELS, FIG.save = models, save


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "out")
    ap.add_argument("--figs", type=Path, default=HERE / "out" / "figs")
    args = ap.parse_args(argv)
    n = write_tables(args.out / "tex")
    print("wrote " + ", ".join(f"{k}_open.tex ({v} Claude rows left out)" for k, v in n.items()))
    fig_errors_open(json.loads((args.out / "rq1_metrics.json").read_text()), args.figs)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        sys.exit(2)
