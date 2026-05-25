"""Master pivot table from a results root. Emits Markdown, CSV, and LaTeX.

Rows: one per completed run — (model, think, tool_filter, prompt_style, cond,
host, jobid), sorted deterministically.

Column groups:
  * per-task × 5 tasks: succ% [lo–hi], tool_sel%, trunc%
  * aggregate: ST mean %, total n

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
    _arm_side,
    _arm_variant_set,
    _arms_present,
    find_default_root,
    host_tag,
    load_summaries,
)

# Wilson CI lives in pddl_eval/summary.py; re-export through the same sys.path
# entry aggregate.py already set up.
from pddl_eval.summary import wilson_ci  # type: ignore[import-not-found]  # noqa: E402
from pddl_eval.prompts import STEERED_VARIANTS  # type: ignore[import-not-found]  # noqa: E402
from pddl_eval.summary import NEUTRAL_VARIANTS  # type: ignore[import-not-found]  # noqa: E402

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
TASK_LABELS = {
    "solve": "Solve",
    "validate_domain": "Val-Dom",
    "validate_problem": "Val-Prob",
    "validate_plan": "Val-Plan",
    "simulate": "Simulate",
}
# `arm` is the sweep-5 four-arm dimension (nt-neut/nt-ster/tl-neut/tl-ster +
# *-legacy fallback for sweep-3/4 corpora). One pivot row per (cell × arm).
META_COLS = ["model", "think", "tool_filter", "prompt_style", "cond", "arm",
             "host", "jobid"]


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


def _row_meta(info: dict, data: dict, arm: str) -> dict:
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
        "arm": arm,
        "host": info.get("host", "?"),
        "jobid": info["jobid"],
    }


def _pool_per_variant(rec: dict, arm: str) -> dict:
    """Pool per_variant cells matching `arm` into one cell. Wilson CI recomputed
    on the pooled n. Mirrors aggregate._pool_arm but also surfaces tool_selected,
    truncated, and the output-token median (sweep-5 H3 primary outcome — pooled
    as the n-weighted mean of per-variant medians because medians don't sum).

    For pre-per_variant corpora, falls back to the whole-cell totals.
    """
    suffix = arm.split("-", 1)[1] if "-" in arm else "legacy"
    target = _arm_variant_set(suffix)
    pv_dict = rec.get("per_variant", {}) or {}
    if not pv_dict:
        n = rec.get("n", 0)
        if suffix != "legacy" or n == 0:
            return {"succ": None, "lo": None, "hi": None,
                    "tool_sel": None, "trunc": None, "n": 0,
                    "out_median": None}
        tokens = rec.get("tokens", {}) or {}
        return {
            "succ": rec.get("success_rate"),
            "lo": rec.get("ci_lo"),
            "hi": rec.get("ci_hi"),
            "tool_sel": rec.get("tool_selected_rate"),
            "trunc": (rec.get("truncated", 0) / n) if n else None,
            "n": n,
            "out_median": tokens.get("completion_median") or None,
        }
    k = n = trunc = tool_k = 0
    # The per-variant median can't be averaged unweighted across variants
    # (medians don't compose) so we approximate the arm-level median as the
    # n-weighted mean of the per-variant medians. For sweep-5 each arm has
    # 3 variants with similar n, so the weighting is close to uniform; the
    # number is meant to be a coarse paper-comparable summary, not a
    # distribution-level statistic.
    weighted_med = 0.0
    weighted_med_n = 0
    for vk, cell in pv_dict.items():
        try:
            v = int(vk)
        except (TypeError, ValueError):
            continue
        if target is None:
            if v in (NEUTRAL_VARIANTS | STEERED_VARIANTS):
                continue
        elif v not in target:
            continue
        k += cell.get("successes", 0)
        n += cell.get("n", 0)
        trunc += cell.get("truncated", 0)
        tool_k += cell.get("tool_selected", 0) or 0
        med = (cell.get("tokens", {}) or {}).get("completion_median")
        if med is not None:
            tn = cell.get("tokens", {}).get("n", 0)
            if tn > 0:
                weighted_med += med * tn
                weighted_med_n += tn
    if n == 0:
        return {"succ": None, "lo": None, "hi": None,
                "tool_sel": None, "trunc": None, "n": 0,
                "out_median": None}
    lo, hi = wilson_ci(k, n)
    out_median = (weighted_med / weighted_med_n) if weighted_med_n else None
    return {
        "succ": round(k / n, 4),
        "lo": round(lo, 4),
        "hi": round(hi, 4),
        "tool_sel": round(tool_k / n, 4),
        "trunc": round(trunc / n, 4),
        "n": n,
        "out_median": round(out_median, 1) if out_median is not None else None,
    }


def _single_task_cells(data: dict, task: str, arm: str) -> dict:
    rec = next((r for r in data.get("single_task", [])
                if r.get("task") == task and r.get("n", 0) > 0), None)
    if rec is None:
        return {"succ": None, "lo": None, "hi": None,
                "tool_sel": None, "trunc": None, "n": 0,
                "out_median": None}
    return _pool_per_variant(rec, arm)


def _st_mean_arm(data: dict, arm: str) -> tuple[float | None, int]:
    """ST-mean across tasks at the arm level: mean of per-arm task rates,
    summing the per-arm n. Tasks with zero arm-matching trials are skipped.
    """
    rates: list[float] = []
    total_n = 0
    for rec in data.get("single_task", []) or []:
        if rec.get("n", 0) == 0:
            continue
        cell = _pool_per_variant(rec, arm)
        if cell["n"] == 0 or cell["succ"] is None:
            continue
        rates.append(cell["succ"])
        total_n += cell["n"]
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


ARM_RANK = {
    "nt-neut": 0, "nt-ster": 1, "tl-neut": 2, "tl-ster": 3,
    "nt-legacy": 4, "tl-legacy": 5,
}


def build_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    for info, data in load_summaries(root):
        info["host"] = host_tag(data.get("meta", {}))
        for arm in _arms_present(data, info["cond"]):
            meta = _row_meta(info, data, arm)
            cells: dict = dict(meta)
            for t in TASKS:
                st = _single_task_cells(data, t, arm)
                cells[f"{t}__succ"] = st["succ"]
                cells[f"{t}__lo"] = st["lo"]
                cells[f"{t}__hi"] = st["hi"]
                cells[f"{t}__tool_sel"] = st["tool_sel"]
                cells[f"{t}__trunc"] = st["trunc"]
                cells[f"{t}__out_med"] = st["out_median"]
            mean, total_n = _st_mean_arm(data, arm)
            cells["st_mean"] = mean
            cells["total_n"] = total_n
            rows.append(cells)
    rows.sort(key=lambda r: (r["model"], r["think"], r["tool_filter"],
                             r["prompt_style"], r["cond"],
                             ARM_RANK.get(r["arm"], 99), r["jobid"]))
    return rows


def _med_str(x: float | None) -> str:
    """Format an output-token median; '—' on None, integer otherwise."""
    if x is None:
        return "—"
    return f"{int(round(x))}"


def write_md(rows: list[dict], path: Path) -> None:
    group_row = [""] * len(META_COLS)
    sub_row = list(META_COLS)
    for t in TASKS:
        # 4-column per task: succ-with-CI, tool%, trunc%, out-token median.
        group_row += [TASK_LABELS[t], "", "", ""]
        sub_row += ["succ% [lo–hi]", "tool%", "trunc%", "out-med"]
    group_row += ["agg", ""]
    sub_row += ["ST mean%", "n"]

    def fmt_row(r: dict) -> list[str]:
        out = [str(r.get(k, "")) for k in META_COLS]
        for t in TASKS:
            out.append(_succ_ci(r[f"{t}__succ"], r[f"{t}__lo"], r[f"{t}__hi"]))
            out.append(_pct(r[f"{t}__tool_sel"]))
            out.append(_pct(r[f"{t}__trunc"]))
            out.append(_med_str(r[f"{t}__out_med"]))
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
    lines.append(f"_{len(rows)} arm row(s). succ% [lo–hi] is Wilson 95% CI; "
                 f"tool% is tool_selected_rate; trunc% is truncated/n; "
                 f"out-med is output-token median (sweep-5 H3, n-weighted "
                 f"across arm variants)._")
    path.write_text("\n".join(lines))


def write_csv(rows: list[dict], path: Path) -> None:
    header = list(META_COLS)
    for t in TASKS:
        header += [f"{t}_succ", f"{t}_ci_lo", f"{t}_ci_hi",
                   f"{t}_tool_sel", f"{t}_trunc", f"{t}_out_med"]
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
                        cell(r[f"{t}__trunc"]), cell(r[f"{t}__out_med"])]
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
    col_spec = "l" * len(META_COLS) + "rrrr" * len(TASKS) + "rr"

    header_groups = [r"\multicolumn{1}{l}{}"] * len(META_COLS)
    for t in TASKS:
        header_groups.append(r"\multicolumn{4}{c}{" + _tex_escape(TASK_LABELS[t]) + "}")
    header_groups.append(r"\multicolumn{2}{c}{agg}")

    sub = list(META_COLS)
    for _ in TASKS:
        sub += ["succ", "tool", "trunc", "out-med"]
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
            row.append(_tex_escape(_med_str(r[f"{t}__out_med"])))
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
