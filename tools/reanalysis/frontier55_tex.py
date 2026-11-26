#!/usr/bin/env python3
"""LaTeX rows of the paper's Claude table, from the filed output of the Claude run.

    python -m tools.reanalysis.frontier55_tex [--json FILE] [--out FILE]

Reads only `tools/reanalysis/out/frontier55.json`, the output that the frozen analysis
`frontier55.py` filed for the registration `development/reference/frontier55_prereg.md`.
No trial is read and no number is computed again: each cell is a figure of that file,
formatted. The script halts unless the file is the live output of the frozen package.

Writes `tools/reanalysis/out/tex/frontier55_main.tex`, the rows between \\midrule and
\\bottomrule of Table `tab:claude` in `paper/main.tex`: ten rows, two models by five
tasks in the paper's order, with the columns

  1. delivered right, no tools (%, 95% interval)
  2. delivered right, tools offered (%, 95% interval)
  3. tools minus no tools, paired on the trial (points, 95% interval); a dagger where
     the filed reading carries the words "not after Holm"
  4. exactly the right tool called (% of the classed tool-arm trials, 95% interval)
  5. tool right and final answer wrong: count / tool-right trials, and the share (%;
     its interval is in the filed output and is left out of the table for width)

`paper/main.tex` holds a pasted copy; after a new filed output, run this again and
paste again. Never edit a number in the tex by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.reanalysis.rq1_tex import ci

HERE = Path(__file__).resolve().parent
FROZEN = "0cbb69b7f810d039734b0aba15096bda91a6f97c6c334dfd2a0ec8ed59cbb497"
MODELS = (("claude-haiku-5-5", "Claude Haiku~5.5"), ("claude-sonnet-5-5", "Claude Sonnet~5.5"))
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
ARMS = ("no-tools", "tools")
NOT_AFTER_HOLM = "not after Holm"
HOLM_ALPHA = 0.05          # section 5 of the registration


class Halt(Exception):
    pass


def read_filed(path: Path) -> dict:
    """The filed output, or a halt when it is not the frozen live one."""
    filed = json.loads(path.read_text())
    if filed.get("package_sha256") != FROZEN or filed.get("mode") != "live":
        raise Halt(f"{path} is not the live output of the Claude run's frozen package")
    return filed


def diff(b: dict) -> str:
    """A paired difference in points, formatted as `rq1_tex.ci` formats a rate, signed."""
    return f"${b['est']:+.1f}$ {{\\scriptsize$[{b['lo']:+.1f},\\,{b['hi']:+.1f}]$}}"


def not_after_holm(c: dict) -> bool:
    """The filed reading carries the words "not after Holm". The filed interval and
    adjusted p must say the same (interval excludes zero, adjusted p 0.05 or more), or
    the file is not what this script takes it for."""
    marked = NOT_AFTER_HOLM in (c["label"] or "")
    numbers = (c["lo"] > 0 or c["hi"] < 0) and c["p_holm"] >= HOLM_ALPHA
    if marked != numbers:
        raise Halt(f"{c['model']}/{c['task']}: the reading {c['label']!r} and the interval "
                   f"with its Holm-adjusted p disagree")
    return marked


def _keyed(filed: dict, name: str, key, want: set) -> dict:
    out = {key(x): x for x in filed[name]}
    if len(out) != len(filed[name]) or set(out) != want:
        raise Halt(f"the filed output does not hold the {len(want)} cells of \"{name}\" "
                   f"(two models, five tasks)")
    return out


def task_tex(task: str) -> str:
    return "\\emph{" + task.replace("_", "\\_") + "}"


def rows(filed: dict) -> str:
    """The ten rows. Halts when a cell is missing, doubled or of another model or task."""
    cells = {(m, t) for m, _ in MODELS for t in TASKS}
    rates = _keyed(filed, "rates", lambda r: (r["model"], r["task"], r["arm"]),
                   {(m, t, a) for m, t in cells for a in ARMS})
    cons = _keyed(filed, "contrasts", lambda c: (c["model"], c["task"]), cells)
    choice = _keyed(filed, "tool_choice", lambda c: (c["model"], c["task"]), cells)
    lost = _keyed(filed, "tool_right_answer_wrong", lambda c: (c["model"], c["task"]), cells)
    out = []
    for mi, (m, name) in enumerate(MODELS):
        for ti, t in enumerate(TASKS):
            c, w = cons[(m, t)], lost[(m, t)]
            if w["answer_wrong"]["n"] != w["n_tool_right"]:
                raise Halt(f"{m}/{t}: the share of wrong answers is not over the tool-right "
                           f"trials")
            out.append(" & ".join([
                name if ti == 0 else "", task_tex(t),
                ci(rates[(m, t, "no-tools")]), ci(rates[(m, t, "tools")]),
                diff(c) + ("$^{\\dagger}$" if not_after_holm(c) else ""),
                ci(choice[(m, t)]["exactly_right"]),
                f"${w['n_answer_wrong']}$ / ${w['n_tool_right']}$",
                f"${w['answer_wrong']['est']:.1f}$"]) + r" \\")
        if mi < len(MODELS) - 1:
            out.append(r"\addlinespace")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=HERE / "out" / "frontier55.json")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "tex" / "frontier55_main.tex")
    args = ap.parse_args(argv)
    text = rows(read_filed(args.json))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        sys.exit(2)
