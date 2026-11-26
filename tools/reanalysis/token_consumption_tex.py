#!/usr/bin/env python3
"""LaTeX rows of the paper's optional token table, from out/token_consumption.json.

    python -m tools.reanalysis.token_consumption_tex [--json FILE] [--out FILE]

Reads only the output of `tools/reanalysis/token_consumption.py` (descriptive, post hoc,
no registration). No trial is read and nothing is computed again: each cell is a figure
of that file, formatted. Halts unless the file records the four frozen package hashes.

Writes `tools/reanalysis/out/tex/tok_main.tex`, the rows between \\midrule and
\\bottomrule of Table `tab:tokens` in `paper/main.tex`: the three open-weight models by
the five tasks (solve and simulate from the matched run, the three validation tasks from
the October rerun; tools arm = plain wording), then a group label and the two Claude
models by the five tasks. Columns:

  1. tokens per trial, no tools (mean, thousands, one decimal)
  2. tokens per trial, tools (same)
  3. tokens per right answer, tools over no tools, at full price (c = 1), 95% interval
  4. the same at cache price c = 0.1 (point value; for the open models the estimate,
     whose band from the bounds on the cached share is in the json and md only)
  5. break-even token budget (thousands; a dash where there is none)

`paper/main.tex` holds a pasted copy; after a new output, run this again and paste again.
Never edit a number in the tex by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.reanalysis.rq1_tex import MODELS as RQ1_MODELS

HERE = Path(__file__).resolve().parent
FROZEN = {
    "frontier55": "0cbb69b7f810d039734b0aba15096bda91a6f97c6c334dfd2a0ec8ed59cbb497",
    "matched_run": "1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d",
    "delivered_rerun": "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9",
    "control": "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79",
}
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
OPEN = tuple((m, name) for m, name in RQ1_MODELS if not m.startswith("Claude"))
CLAUDE = (("Claude Haiku 5.5", "Claude Haiku~5.5"), ("Claude Sonnet 5.5", "Claude Sonnet~5.5"))
N_COLS = 7
GROUP_LABEL = r"\multicolumn{7}{@{}l}{\emph{Claude run (a separate corpus)}} \\"
CACHE_PRICE = 0.1


class Halt(Exception):
    pass


def corpus_of(model: str, task: str) -> str:
    if model.startswith("Claude"):
        return "claude"
    return "matched" if task in ("solve", "simulate") else "rerun"


def tool_arm(model: str) -> str:
    return "tools" if model.startswith("Claude") else "plain"


def thousands(x: float) -> str:
    return f"${x / 1000:.1f}$"


def mult_ci(b: dict) -> str:
    return f"${b['est']:.2f}$ {{\\scriptsize$[{b['lo']:.2f},\\,{b['hi']:.2f}]$}}"


def mult_point(b: dict) -> str:
    return f"${b['est']:.2f}$"


def budget(v) -> str:
    """A break-even budget in thousands; a dash where there is none ("none" in the json,
    the tools arm behind at no limit)."""
    if v is None or v == "none" or (isinstance(v, float) and v == float("inf")):
        return "--"
    return f"${float(v) / 1000:.1f}$"


def read(path: Path) -> dict:
    res = json.loads(path.read_text())
    if res.get("hashes") != FROZEN:
        raise Halt(f"{path} does not record the four frozen package hashes")
    return res


def lookup(res: dict):
    cells = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in res["cells"]}
    cache = {(x["corpus"], x["model"], x["task"], x["arm"], x["c"]): x for x in res["caching"]["rows"]
             if x["scenario"] == "own hits" and x["refused_request"] == "kept" and x["p"] == 1.0}
    pairs = {(p["corpus"], p["model"], p["task"], p["arm"]): p for p in res["coverage"]["pairs"]
             if p["unit"] == "raw"}
    return cells, cache, pairs


def row(res_maps, model: str, name: str, task: str, first: bool) -> str:
    cells, cache, pairs = res_maps
    cp, arm = corpus_of(model, task), tool_arm(model)
    try:
        none, tools = cells[(cp, model, task, "none")], cells[(cp, model, task, arm)]
        full, cached = cache[(cp, model, task, arm, 1.0)], cache[(cp, model, task, arm, CACHE_PRICE)]
        be = pairs[(cp, model, task, arm)]["break_even"]["est"]
    except KeyError as e:
        raise Halt(f"no cell for {model}/{task}: {e}") from e
    if full["mult"] is None or cached["mult"] is None:
        raise Halt(f"{model}/{task}: no multiplier (an arm without a right answer)")
    task_tex = "\\emph{" + task.replace("_", "\\_") + "}"
    return " & ".join([name if first else "", task_tex, thousands(none["total"]["est"]),
                       thousands(tools["total"]["est"]), mult_ci(full["mult"]),
                       mult_point(cached["mult"]), budget(be)]) + r" \\"


def rows(res: dict) -> str:
    maps = lookup(res)
    out = []
    for i, (m, name) in enumerate(OPEN):
        if i:
            out.append(r"\addlinespace")
        out += [row(maps, m, name, t, j == 0) for j, t in enumerate(TASKS)]
    out += [r"\addlinespace", GROUP_LABEL]
    for i, (m, name) in enumerate(CLAUDE):
        if i:
            out.append(r"\addlinespace")
        out += [row(maps, m, name, t, j == 0) for j, t in enumerate(TASKS)]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=HERE / "out" / "token_consumption.json")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "tex" / "tok_main.tex")
    args = ap.parse_args(argv)
    try:
        text = rows(read(args.json))
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
