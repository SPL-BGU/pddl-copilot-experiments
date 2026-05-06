"""Master pivot table from a results root. Emits Markdown, CSV, and LaTeX.

Rows: one per completed run — (model, think, tool_filter, prompt_style, cond,
host, jobid), sorted deterministically.

Column groups:
  * per-task × 5 tasks: succ% [lo–hi], tool_sel%, trunc%
  * aggregate: ST mean %, total n

Chain-phase columns (L=2..5) were dropped 2026-05-05 when the chain phase
was archived from the active flow; legacy `chains` rows in old summary_*.json
are ignored here.

Outputs default to <root>/tables/master.{md,csv,tex}.

Imports `parse_dirname`, `find_default_root`, `load_summaries`, `host_tag`
from the sibling `aggregate.py` — same conventions, no duplication.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from aggregate import (  # type: ignore[import-not-found]
    find_default_root,
    host_tag,
    load_summaries,
)

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
TASK_LABELS = {
    "solve": "Solve",
    "validate_domain": "Val-Dom",
    "validate_problem": "Val-Prob",
    "validate_plan": "Val-Plan",
    "simulate": "Simulate",
}
META_COLS = ["model", "think", "tool_filter", "prompt_style", "cond", "host", "jobid"]


def _cond_parts(cond: str) -> tuple[str, str]:
    """Extract (tool_filter, prompt_style) from a dir-name cond string.

    Fallback only — prefer summary.meta values when present.
    """
    if cond == "no-tools" or not cond.startswith("tools_"):
        return "-", "-"
    parts = cond[len("tools_"):].rsplit("_", 1)
    if len(parts) != 2:
        return "-", "-"
    return parts[0], parts[1]


def _row_meta(info: dict, data: dict) -> dict:
    tf_fallback, ps_fallback = _cond_parts(info["cond"])
    meta = data.get("meta", {}) or {}
    tf = meta.get("tool_filter", tf_fallback)
    ps = meta.get("prompt_style", ps_fallback)
    cond_short = "no-tools" if info["cond"] == "no-tools" else "tools"
    return {
        "model": info["model"],
        "think": info["think"],
        "tool_filter": tf,
        "prompt_style": ps,
        "cond": cond_short,
        "host": info.get("host", "?"),
        "jobid": info["jobid"],
    }


def _single_task_cells(data: dict, task: str) -> dict:
    rec = next((r for r in data.get("single_task", [])
                if r.get("task") == task and r.get("n", 0) > 0), None)
    if rec is None:
        return {"succ": None, "lo": None, "hi": None,
                "tool_sel": None, "trunc": None, "n": 0}
    return {
        "succ": rec["success_rate"],
        "lo": rec.get("ci_lo"),
        "hi": rec.get("ci_hi"),
        "tool_sel": rec.get("tool_selected_rate"),
        "trunc": (rec.get("truncated", 0) / rec["n"]) if rec["n"] else None,
        "n": rec["n"],
    }


def _st_mean(data: dict) -> tuple[float | None, int]:
    rates = [r["success_rate"] for r in data.get("single_task", []) if r.get("n", 0) > 0]
    total_n = sum(r["n"] for r in data.get("single_task", []) if r.get("n", 0) > 0)
    if not rates:
        return None, 0
    return sum(rates) / len(rates), total_n


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{int(round(x * 100))}"


def _succ_ci(succ: float | None, lo: float | None, hi: float | None) -> str:
    if succ is None:
        return "—"
    if lo is None or hi is None:
        return f"{int(round(succ * 100))}"
    return f"{int(round(succ * 100))} [{lo * 100:.1f}–{hi * 100:.1f}]"


def build_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    for info, data in load_summaries(root):
        info["host"] = host_tag(data.get("meta", {}))
        meta = _row_meta(info, data)
        cells: dict = dict(meta)
        for t in TASKS:
            st = _single_task_cells(data, t)
            cells[f"{t}__succ"] = st["succ"]
            cells[f"{t}__lo"] = st["lo"]
            cells[f"{t}__hi"] = st["hi"]
            cells[f"{t}__tool_sel"] = st["tool_sel"]
            cells[f"{t}__trunc"] = st["trunc"]
        mean, total_n = _st_mean(data)
        cells["st_mean"] = mean
        cells["total_n"] = total_n
        rows.append(cells)
    rows.sort(key=lambda r: (r["model"], r["think"], r["tool_filter"],
                             r["prompt_style"], r["cond"], r["jobid"]))
    return rows


def write_md(rows: list[dict], path: Path) -> None:
    group_row = [""] * len(META_COLS)
    sub_row = list(META_COLS)
    for t in TASKS:
        group_row += [TASK_LABELS[t], "", ""]
        sub_row += ["succ% [lo–hi]", "tool%", "trunc%"]
    group_row += ["agg", ""]
    sub_row += ["ST mean%", "n"]

    def fmt_row(r: dict) -> list[str]:
        out = [str(r.get(k, "")) for k in META_COLS]
        for t in TASKS:
            out.append(_succ_ci(r[f"{t}__succ"], r[f"{t}__lo"], r[f"{t}__hi"]))
            out.append(_pct(r[f"{t}__tool_sel"]))
            out.append(_pct(r[f"{t}__trunc"]))
        out.append(_pct(r["st_mean"]))
        out.append(str(r["total_n"]))
        return out

    lines = [
        "# Master pivot — PDDL copilot sweep",
        "",
        "| " + " | ".join(group_row) + " |",
        "| " + " | ".join(sub_row) + " |",
        "|" + "|".join(["---"] * len(sub_row)) + "|",
    ]
    for r in rows:
        lines.append("| " + " | ".join(fmt_row(r)) + " |")
    lines.append("")
    lines.append(f"_{len(rows)} run(s). succ% [lo–hi] is Wilson 95% CI; "
                 f"tool% is tool_selected_rate; trunc% is truncated/n._")
    path.write_text("\n".join(lines))


def write_csv(rows: list[dict], path: Path) -> None:
    header = list(META_COLS)
    for t in TASKS:
        header += [f"{t}_succ", f"{t}_ci_lo", f"{t}_ci_hi",
                   f"{t}_tool_sel", f"{t}_trunc"]
    header += ["st_mean", "total_n"]

    def cell(x):
        return "" if x is None else x

    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            row = [r.get(k, "") for k in META_COLS]
            for t in TASKS:
                row += [cell(r[f"{t}__succ"]), cell(r[f"{t}__lo"]),
                        cell(r[f"{t}__hi"]), cell(r[f"{t}__tool_sel"]),
                        cell(r[f"{t}__trunc"])]
            row += [cell(r["st_mean"]), r["total_n"]]
            w.writerow(row)


def _tex_escape(s: str) -> str:
    """Minimal LaTeX escape — underscores/ampersands appear in model names."""
    return (s.replace("\\", r"\textbackslash{}")
             .replace("&", r"\&")
             .replace("%", r"\%")
             .replace("_", r"\_")
             .replace("#", r"\#")
             .replace("–", "--"))


def write_tex(rows: list[dict], path: Path) -> None:
    col_spec = "l" * len(META_COLS) + "rrr" * len(TASKS) + "rr"

    header_groups = [r"\multicolumn{1}{l}{}"] * len(META_COLS)
    for t in TASKS:
        header_groups.append(r"\multicolumn{3}{c}{" + _tex_escape(TASK_LABELS[t]) + "}")
    header_groups.append(r"\multicolumn{2}{c}{agg}")

    sub = list(META_COLS)
    for _ in TASKS:
        sub += ["succ", "tool", "trunc"]
    sub += ["ST-mean", "n"]

    lines = [
        "% Master pivot — PDDL copilot sweep (auto-generated by scripts/table.py)",
        r"\begin{tabular}{" + col_spec + "}",
        r"\toprule",
        " & ".join(header_groups) + r" \\",
        r"\midrule",
        " & ".join(_tex_escape(x) for x in sub) + r" \\",
        r"\midrule",
    ]
    for r in rows:
        row = [_tex_escape(str(r.get(k, ""))) for k in META_COLS]
        for t in TASKS:
            row.append(_tex_escape(_succ_ci(r[f"{t}__succ"], r[f"{t}__lo"], r[f"{t}__hi"])))
            row.append(_tex_escape(_pct(r[f"{t}__tool_sel"])))
            row.append(_tex_escape(_pct(r[f"{t}__trunc"])))
        row.append(_tex_escape(_pct(r["st_mean"])))
        row.append(str(r["total_n"]))
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", type=Path, default=None)
    ap.add_argument("--formats", default="md,csv,tex",
                    help="comma list of output formats (md,csv,tex); default all")
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir (default: <root>/tables/)")
    args = ap.parse_args()

    root = args.root or find_default_root()
    rows = build_rows(root)
    if not rows:
        sys.exit(f"no summary_*.json rows found under {root}")

    out = args.out or (root / "tables")
    out.mkdir(exist_ok=True, parents=True)
    fmts = {f.strip() for f in args.formats.split(",") if f.strip()}
    written: list[str] = []
    if "md" in fmts:
        p = out / "master.md"; write_md(rows, p); written.append(str(p))
    if "csv" in fmts:
        p = out / "master.csv"; write_csv(rows, p); written.append(str(p))
    if "tex" in fmts:
        p = out / "master.tex"; write_tex(rows, p); written.append(str(p))
    print(f"wrote {len(rows)} rows → " + ", ".join(written))


if __name__ == "__main__":
    main()
