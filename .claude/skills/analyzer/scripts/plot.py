"""Paper-style plots from a results root. Auto-discovers series from dir
names + summary metadata; no hardcoded SERIES table.

Usage:
    python3 plot.py                                    # auto-pick latest root
    python3 plot.py results/full-cluster-run1          # explicit root
    python3 plot.py results/cluster-20260421 --group-by think
    python3 plot.py results/cluster-20260424 --figs 1,4,5 --no-ci

Figures written to <root>/plots/:
    fig1_single_task.png       — tasks × series bars (Wilson CI whiskers)
    fig3_tool_selection.png    — classical vs numeric planner-selection rate
    fig4_failure_breakdown.png — 100%-stacked failure reasons per task × series
    fig5_domain_heatmap.png    — (series × 10 domains) heatmap per task
    fig6_tool_adherence.png    — per-task tool_selected_rate (with-tools only)

Valid --figs: 1, 3, 4, 5, 6 (2 and 7 are reserved gaps).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _constants import (  # noqa: E402,F401
    ACTIVE_ARMS,
    ALL_ARMS,
    CLASSICAL,
    COND_HATCH,
    CONDITIONS,
    DOMAINS,
    FAILURE_COLORS,
    FAILURE_REASONS,
    LEGACY_ARMS,
    MODEL_COLORS,
    NEUTRAL_VARIANTS,
    NUMERIC,
    RETIRED_CONDS,
    STEERED_VARIANTS,
    TASK_LABELS,
    TASKS,
    THINK_LIGHTEN,
    _lighten,
    arm_for,
    find_default_root,
    iter_cells,
    latest_single_task,
    latest_summary,
    parse_dirname_plotshape as parse_dirname,
    wilson_ci,
)


def load_series(root: Path, include_legacy: bool,
                include_retired: bool = False) -> list[dict]:
    entries = []
    for d, info in iter_cells(root, include_retired=include_retired,
                               include_legacy=include_legacy,
                               parser="plotshape"):
        summary = latest_summary(d)
        if summary is None:
            continue
        info["summary"] = summary
        info["instances"] = latest_single_task(d) or []
        info["dir"] = d
        entries.append(info)
    return entries


def label(info: dict, group_by: str) -> str:
    """Build a compact legend label. group_by controls the emphasis."""
    cond_short = info["cond"].replace("tools_", "").replace("no-tools", "no-tools")
    if info["think"] == "default":
        return f"{info['model']} · {cond_short}"
    return f"{info['model']} · {info['think']} · {cond_short}"


def style(info: dict) -> tuple[str, str | None]:
    # One base color per model across all conds; cond is encoded by hatch
    # (no-tools=stripes, per-task=dots, all=solid). think modulates lightness.
    base = MODEL_COLORS.get(info["model"], "#888888")
    color = _lighten(base, THINK_LIGHTEN.get(info["think"], 0.0))
    hatch = COND_HATCH.get(info["cond"])
    return color, hatch


def _wilson_err(rate: float, lo: float, hi: float) -> tuple[float, float]:
    """Return (err_lo, err_hi) for matplotlib errorbar yerr (always ≥0)."""
    return max(0.0, rate - lo), max(0.0, hi - rate)


from _constants import (  # noqa: E402
    arm_side as _arm_side,
    arm_variant_set as _arm_variant_set,
)


def split_series_by_arm(series: list[dict]) -> list[dict]:
    """Split each loaded series into per-arm series by pooling per_variant
    cells and filtering instances.

    Sweep-5 design (development/sweep_prompt_bank_design.md §0) frames result
    comparisons by arm — `(no-tools|with-tools) × (neutral|steered)`. The
    existing series is one-per-dir (i.e. per condition); after this split it
    becomes one-per-(dir, arm). Wilson CIs are recomputed on the pooled
    arm-level counts, NOT averaged from per-variant CIs (proper interval at
    n=pooled).

    Legacy corpora (sweep-3/4: v0-v10) collapse to a single `*-legacy` arm
    so the existing fig1/3/4/5/6 stay renderable.
    """
    out: list[dict] = []
    for s in series:
        side = _arm_side(s["cond"])
        summary = s.get("summary", {}) or {}
        st_rows = summary.get("single_task", []) or []
        # Collect variants present in this cell.
        variants_present: set[int] = set()
        for rec in st_rows:
            for vk in (rec.get("per_variant", {}) or {}).keys():
                try:
                    variants_present.add(int(vk))
                except (TypeError, ValueError):
                    continue
        # Determine which arm suffixes apply.
        suffixes: list[str] = []
        if variants_present & NEUTRAL_VARIANTS:
            suffixes.append("neut")
        if variants_present & STEERED_VARIANTS:
            suffixes.append("ster")
        if variants_present and not (variants_present & (NEUTRAL_VARIANTS | STEERED_VARIANTS)):
            suffixes.append("legacy")
        if not suffixes:
            # No per_variant data at all (very-old corpus). Treat the whole
            # cell as a single legacy arm so the plot still renders.
            suffixes.append("legacy")
        for suffix in suffixes:
            arm = f"{side}-{suffix}"
            target = _arm_variant_set(suffix)
            pooled_single: list[dict] = []
            for rec in st_rows:
                if rec.get("n", 0) == 0:
                    continue
                pv = rec.get("per_variant", {}) or {}
                # Pool successes / n / tool_selected / truncated across the
                # arm-matching per_variant cells.
                if pv:
                    k = n = trunc = tool_k = 0
                    for vk, cell in pv.items():
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
                else:
                    # Pre-per_variant corpus: legacy arm consumes the whole cell;
                    # active arms see zero data (skipped via continue below).
                    if suffix != "legacy":
                        continue
                    k = rec.get("successes", 0)
                    n = rec.get("n", 0)
                    trunc = rec.get("truncated", 0)
                    tool_k = rec.get("tool_selected", 0) or 0
                if n == 0:
                    continue
                lo, hi = wilson_ci(k, n)
                ts_lo, ts_hi = wilson_ci(tool_k, n)
                pooled = {
                    "model": s["model"], "task": rec["task"], "condition": arm,
                    "successes": k, "n": n,
                    "success_rate": round(k / n, 4),
                    "ci_lo": lo, "ci_hi": hi,
                    "truncated": trunc,
                    # Failure-reason counts are not arm-tagged in summary_*.json
                    # (the per_variant cells don't carry them). Synthesizing
                    # arm-level FR shares from the whole-cell counts would be a
                    # silent mis-attribution — leave empty so fig4 falls through
                    # to "other" rather than mis-bucketing. Per-arm FR breakdowns
                    # require trials.jsonl (build_deck / plot_focused path).
                    "failure_reasons": {},
                    "tool_selected": tool_k,
                    "tool_selected_rate": round(tool_k / n, 4),
                    "tool_selected_ci_lo": ts_lo,
                    "tool_selected_ci_hi": ts_hi,
                }
                pooled_single.append(pooled)
            if not pooled_single:
                continue
            # Filter instances by arm so fig3/fig5 (which read trial rows)
            # also see arm-isolated data. Legacy arm gets v0-v10 instances;
            # active arms get their variant set.
            kept_instances = []
            for inst in s.get("instances", []):
                pv = inst.get("prompt_variant")
                if pv is None:
                    continue
                if target is None:
                    if pv in (NEUTRAL_VARIANTS | STEERED_VARIANTS):
                        continue
                elif pv not in target:
                    continue
                kept_instances.append(inst)
            out.append({
                "model": s["model"], "think": s["think"],
                # Putting the arm in the `cond` slot keeps every existing
                # fig builder (which keys off `s["cond"]`) operational
                # without a deeper rewrite. The legend / hatch maps already
                # include the arm tags above.
                "cond": arm,
                "jobid": s.get("jobid", ""),
                "summary": {"single_task": pooled_single,
                            "meta": summary.get("meta", {})},
                "instances": kept_instances,
            })
    return out


def merge_series(series: list[dict]) -> list[dict]:
    """Pool tools_* series by (model, think); pass no-tools through unchanged.

    Counts (successes, n, truncated, tool_selected, failure_reasons) are
    summed across the tools_* condition variants and rates + Wilson CIs are
    recomputed on the pooled totals — that gives
    proper CIs at n≈4× per cell, which averaging rates would not. no-tools
    rows are passed through so they remain as the baseline alongside the
    merged tools series; pooling them would be a no-op (one no-tools cond
    per (model, think)) and would also mask the cond="no-tools" tag that
    fig3 / fig6 use to filter the baseline out of tool-adherence panels.
    """
    tools_runs        = [s for s in series if s["cond"] != "no-tools"]
    no_tools_passthru = [dict(s) for s in series if s["cond"] == "no-tools"]

    groups: dict[tuple[str, str], list[dict]] = {}
    for s in tools_runs:
        groups.setdefault((s["model"], s["think"]), []).append(s)

    merged: list[dict] = list(no_tools_passthru)
    for (model, think), group in groups.items():
        pooled_single: list[dict] = []
        for task in TASKS:
            k = n = trunc = tool_k = 0
            fr: dict[str, int] = {}
            for s in group:
                rec = next((r for r in s["summary"]["single_task"]
                            if r["task"] == task and r["n"] > 0), None)
                if rec is None:
                    continue
                k += rec["successes"]
                n += rec["n"]
                trunc += rec.get("truncated", 0)
                tool_k += rec.get("tool_selected", 0) or 0
                for kk, vv in rec.get("failure_reasons", {}).items():
                    fr[kk] = fr.get(kk, 0) + vv
            if n == 0:
                continue
            lo, hi = wilson_ci(k, n)
            ts_lo, ts_hi = wilson_ci(tool_k, n)
            pooled_single.append({
                "model": model, "task": task, "condition": "merged",
                "successes": k, "n": n,
                "success_rate": round(k / n, 4),
                "ci_lo": lo, "ci_hi": hi,
                "truncated": trunc,
                "failure_reasons": fr,
                "tool_selected": tool_k,
                "tool_selected_rate": round(tool_k / n, 4),
                "tool_selected_ci_lo": ts_lo,
                "tool_selected_ci_hi": ts_hi,
            })

        instances: list = []
        for s in group:
            instances += s.get("instances", [])

        merged.append({
            "model": model, "think": think,
            # 'cond' is the key existing figs use for filtering/styling.
            # Use a tools_* prefix so fig3/fig6 keep it; no hatch mapped.
            "cond": "tools_merged",
            "jobid": "merged",
            "summary": {"single_task": pooled_single,
                        "meta": {}},
            "instances": instances,
        })
    return merged


def grouped_bars(ax, x, series, width, get_vals, annotate=True, get_err=None):
    n = len(series)
    for i, s in enumerate(series):
        offset = (i - (n - 1) / 2) * width
        vals = get_vals(s)
        color, hatch = style(s)
        bars = ax.bar(x + offset, vals, width,
                      label=s["_label"], color=color,
                      edgecolor="black", linewidth=0.5, hatch=hatch)
        if get_err is not None:
            err_lo, err_hi = get_err(s)
            vals_arr = np.asarray(vals, dtype=float)
            lo_arr = np.asarray(err_lo, dtype=float)
            hi_arr = np.asarray(err_hi, dtype=float)
            # Skip whiskers on value=0 bars: the bar is invisible, so the
            # whisker floats alone at the baseline and reads as noise next
            # to neighboring non-zero bars.
            mask = vals_arr > 0
            if mask.any():
                xc = x + offset
                ax.errorbar(
                    xc[mask], vals_arr[mask],
                    yerr=np.array([lo_arr[mask], hi_arr[mask]]),
                    fmt="none", ecolor="black", elinewidth=0.7,
                    capsize=2, capthick=0.7,
                )
        if annotate:
            for b, v in zip(bars, vals):
                if v > 0.02:
                    ax.text(b.get_x() + b.get_width() / 2, v + 0.012,
                            f"{int(round(v * 100))}",
                            ha="center", va="bottom", fontsize=6)


def fig1(series, out_path, draw_ci):
    x = np.arange(len(TASKS))
    n = max(1, len(series))
    width = 0.95 / n
    fig, ax = plt.subplots(figsize=(max(9.0, 1.1 * n + 6), 4.3))

    def vals(s):
        rates = {r["task"]: r["success_rate"]
                 for r in s["summary"]["single_task"] if r["n"] > 0}
        return [rates.get(t, 0.0) for t in TASKS]

    def err(s):
        by_task = {r["task"]: r for r in s["summary"]["single_task"] if r["n"] > 0}
        lo, hi = [], []
        for t in TASKS:
            r = by_task.get(t)
            if r is None:
                lo.append(0.0); hi.append(0.0)
            else:
                el, eh = _wilson_err(r["success_rate"], r["ci_lo"], r["ci_hi"])
                lo.append(el); hi.append(eh)
        return lo, hi

    grouped_bars(ax, x, series, width, vals, get_err=err if draw_ci else None)
    ax.set_xticks(x)
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS])
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1.0)
    ax.set_title("Single-task success rate" + (" (Wilson 95% CI)" if draw_ci else ""))
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, framealpha=0.9, ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _is_no_tools_series(s: dict) -> bool:
    """True if this series is a no-tools cell or a no-tools arm. Handles
    both the legacy cond shape ('no-tools') and the arm-split cond shape
    ('nt-neut' / 'nt-ster' / 'nt-legacy').
    """
    c = s.get("cond", "")
    return c == "no-tools" or c.startswith("nt-")


def fig3(series, out_path):
    tool_series = [s for s in series if not _is_no_tools_series(s)]
    if not tool_series:
        return
    x = np.arange(2)  # classical, numeric
    n = len(tool_series)
    width = 0.95 / n
    fig, ax = plt.subplots(figsize=(max(7.5, 0.9 * n + 4), 4.3))

    classical_set = set(CLASSICAL)
    numeric_set = set(NUMERIC)

    def vals(s):
        c_tot = c_sel = nu_tot = nu_sel = 0
        for r in s.get("instances", []):
            if r["task"] != "solve" or not r.get("with_tools", False):
                continue
            dn = r["domain_name"]
            if dn in classical_set:
                c_tot += 1
                if r.get("tool_selected"):
                    c_sel += 1
            elif dn in numeric_set:
                nu_tot += 1
                if r.get("tool_selected"):
                    nu_sel += 1
        return [c_sel / c_tot if c_tot else 0.0,
                nu_sel / nu_tot if nu_tot else 0.0]

    grouped_bars(ax, x, tool_series, width, vals)
    ax.set_xticks(x)
    ax.set_xticklabels(["classical", "numeric"])
    ax.set_ylabel("Tool-selected rate on solve")
    ax.set_ylim(0, 1.0)
    ax.set_title("Correct-planner selection, classical vs numeric"
                 "\n[tools-only — no-tools cells excluded]")
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, framealpha=0.9, ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig4(series, out_path):
    """1×5 grid of 100%-stacked horizontal bars; one row per series per task."""
    if not series:
        return
    # Gather the set of reasons that actually appear, keep canonical order.
    reasons_seen: set[str] = set()
    for s in series:
        for r in s["summary"]["single_task"]:
            if r["n"] > 0:
                reasons_seen.update(r.get("failure_reasons", {}).keys())
    if not reasons_seen:
        # Per-arm series synthesized by split_series_by_arm carry empty
        # failure_reasons by design (the per_variant cells in summary_*.json
        # don't store arm-tagged FR counts). Skip fig4 in that mode rather
        # than calling fig.legend(ncol=0). Per-arm FR breakdowns live in
        # build_deck / plot_focused, which read trials.jsonl directly.
        print(f"  fig4 skipped: empty failure_reasons across all series",
              file=sys.stderr)
        return
    known = set(FAILURE_REASONS)
    order = [fr for fr in FAILURE_REASONS if fr in reasons_seen]
    if reasons_seen - known:
        order.append("other")  # bucket unknown reasons

    labels = [s["_label"] for s in series]
    y = np.arange(len(series))
    fig, axes = plt.subplots(
        1, len(TASKS),
        figsize=(max(14.0, 2.6 * len(TASKS)), max(4.5, 0.22 * len(series) + 3.0)),
        sharey=True,
    )

    for ax, task in zip(axes, TASKS):
        left = np.zeros(len(series))
        for fr in order:
            vals = []
            for s in series:
                rec = next((r for r in s["summary"]["single_task"]
                            if r["task"] == task and r["n"] > 0), None)
                if rec is None:
                    vals.append(0.0); continue
                total = rec["n"]
                if fr == "other":
                    cnt = sum(v for k, v in rec.get("failure_reasons", {}).items()
                              if k not in known)
                else:
                    cnt = rec.get("failure_reasons", {}).get(fr, 0)
                vals.append(cnt / total if total else 0.0)
            arr = np.array(vals)
            ax.barh(y, arr, left=left, color=FAILURE_COLORS[fr],
                    edgecolor="white", linewidth=0.3)
            left += arr
        ax.set_xlim(0, 1.0)
        ax.set_title(TASK_LABELS[task], fontsize=9)
        ax.set_xlabel("share", fontsize=8)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=6)
        ax.invert_yaxis()
        ax.xaxis.grid(True, linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)

    handles = [mpatches.Patch(color=FAILURE_COLORS[fr], label=fr) for fr in order]
    fig.legend(handles=handles, loc="lower center", ncol=min(7, len(order)),
               fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Failure-reason breakdown per task (normalized)", fontsize=11)
    fig.tight_layout(rect=[0, 0.05, 1, 0.96])
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig5(series, out_path):
    """1×5 heatmap grid: (series × 10 domains) per task, cell = success_rate."""
    if not series:
        return
    labels = [s["_label"] for s in series]
    y = np.arange(len(series))
    x = np.arange(len(DOMAINS))
    # Width formula bumped to ~22+ inches so 10-domain × 5-task cells are
    # wide enough that the "k/n" annotation doesn't run into the next column.
    fig, axes = plt.subplots(
        1, len(TASKS),
        figsize=(max(22.0, 3.2 * len(TASKS) + 6),
                 max(4.5, 0.32 * len(series) + 3.0)),
        sharey=True,
    )

    im = None
    for ax, task in zip(axes, TASKS):
        grid = np.full((len(series), len(DOMAINS)), np.nan)
        counts: list[list[tuple[int, int] | None]] = \
            [[None] * len(DOMAINS) for _ in range(len(series))]
        for i, s in enumerate(series):
            for j, dom in enumerate(DOMAINS):
                k = n = 0
                for r in s.get("instances", []):
                    if r["task"] != task or r["domain_name"] != dom:
                        continue
                    n += 1
                    if r.get("success"):
                        k += 1
                if n > 0:
                    grid[i, j] = k / n
                    counts[i][j] = (k, n)
        im = ax.imshow(grid, cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
        ax.set_xticks(x)
        ax.set_xticklabels(DOMAINS, rotation=60, ha="right", fontsize=7)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_title(TASK_LABELS[task], fontsize=9)
        for i in range(len(series)):
            for j in range(len(DOMAINS)):
                c = counts[i][j]
                if c is None:
                    continue
                k, n = c
                cell = grid[i, j]
                # Three-channel text: pct on the top line for at-a-glance read,
                # raw k/n on a second line so the sample size is visible.
                pct = int(round(cell * 100))
                # White on dark (low rate), black on bright (high rate).
                color = "white" if cell < 0.45 else "black"
                ax.text(j, i - 0.18, f"{pct}%", ha="center", va="center",
                        color=color, fontsize=7, fontweight="bold")
                ax.text(j, i + 0.22, f"{k}/{n}", ha="center", va="center",
                        color=color, fontsize=5.5)
    if im is not None:
        fig.colorbar(im, ax=axes, shrink=0.7, pad=0.02, label="success rate (0=purple → 1=yellow)")
    fig.suptitle("Per-domain success rate (rows=series, cols=domain)"
                 "\nEach cell: top = pass% (bold); bottom = k / n. Color: viridis 0→1.",
                 fontsize=11)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig6(series, out_path, draw_ci):
    """Per-task tool_selected_rate across with-tools series."""
    tool_series = [s for s in series if not _is_no_tools_series(s)]
    if not tool_series:
        return
    x = np.arange(len(TASKS))
    n = max(1, len(tool_series))
    width = 0.95 / n
    fig, ax = plt.subplots(figsize=(max(9.0, 1.1 * n + 6), 4.3))

    def vals(s):
        by_task = {r["task"]: r for r in s["summary"]["single_task"] if r["n"] > 0}
        return [by_task.get(t, {}).get("tool_selected_rate", 0.0) for t in TASKS]

    def err(s):
        by_task = {r["task"]: r for r in s["summary"]["single_task"] if r["n"] > 0}
        lo, hi = [], []
        for t in TASKS:
            r = by_task.get(t)
            if r is None or "tool_selected_ci_lo" not in r:
                lo.append(0.0); hi.append(0.0)
            else:
                el, eh = _wilson_err(r["tool_selected_rate"],
                                     r["tool_selected_ci_lo"],
                                     r["tool_selected_ci_hi"])
                lo.append(el); hi.append(eh)
        return lo, hi

    grouped_bars(ax, x, tool_series, width, vals, get_err=err if draw_ci else None)
    ax.set_xticks(x)
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS])
    ax.set_ylabel("Tool-selected rate")
    ax.set_ylim(0, 1.0)
    ax.set_title("Per-task tool-adherence" +
                 (" (Wilson 95% CI)" if draw_ci else "") +
                 "\n[tools-only — no-tools cells excluded]")
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, framealpha=0.9, ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _parse_figs(spec: str) -> set[int]:
    if spec == "all":
        return {1, 3, 4, 5, 6}
    out = set()
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            n = int(piece)
        except ValueError:
            sys.exit(f"--figs: expected 'all' or comma-separated ints, got {spec!r}")
        if n not in (1, 3, 4, 5, 6):
            sys.exit(f"--figs: unknown fig number {n}; valid: 1, 3, 4, 5, 6")
        out.add(n)
    if not out:
        sys.exit("--figs: no figure numbers parsed")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", type=Path, default=None)
    ap.add_argument("--group-by", default="model", choices=("model", "think", "cond"),
                    help="controls legend ordering / label emphasis")
    ap.add_argument("--include-legacy", action="store_true", default=True,
                    help="include legacy (no-think) dirs as think=default (default: on)")
    ap.add_argument("--figs", default="all",
                    help="comma list of fig numbers to render (1, 3, 4, 5, 6), "
                         "or 'all' (default)")
    ap.add_argument("--no-ci", dest="ci", action="store_false", default=True,
                    help="omit Wilson CI error bars on figs 1, 6")
    ap.add_argument("--merge", action="store_true", default=False,
                    help="pool tool_filter × prompt_style into one tools_merged "
                         "series per (model, think); no-tools series pass "
                         "through unchanged as baselines. writes to "
                         "<root>/plots/merged/")
    ap.add_argument("--by-arm", action="store_true", default=False,
                    help="split each cell into per-arm series (sweep-5 four-arm "
                         "matrix: nt-neut/nt-ster/tl-neut/tl-ster). Pools "
                         "per_variant cells into arm-level counts, recomputing "
                         "Wilson CIs on the pooled n. Legacy v0-v10 corpora "
                         "collapse to *-legacy arms. Mutually exclusive with "
                         "--merge. Writes to <root>/plots/by_arm/")
    ap.add_argument("--arms", default=None,
                    help="comma-separated arm filter applied after --by-arm "
                         "(e.g. 'nt-neut,tl-neut' for the H1 isolation view "
                         "or 'tl-neut,tl-ster' for H2). Requires --by-arm; "
                         "see development/sweep_prompt_bank_design.md §0 for "
                         "the hypothesis mapping.")
    args = ap.parse_args()

    if args.arms and not args.by_arm:
        sys.exit("--arms requires --by-arm")
    if args.merge and args.by_arm:
        sys.exit("--merge and --by-arm are mutually exclusive")

    root = args.root or find_default_root()
    series = load_series(root, args.include_legacy)
    if not series:
        sys.exit(f"no parseable slurm_* dirs under {root}")

    if args.by_arm:
        series = split_series_by_arm(series)
        if args.arms:
            wanted = {a.strip() for a in args.arms.split(",") if a.strip()}
            unknown = wanted - set(ALL_ARMS)
            if unknown:
                sys.exit(f"--arms: unknown arm tag(s) {sorted(unknown)}; "
                         f"valid: {list(ALL_ARMS)}")
            series = [s for s in series if s["cond"] in wanted]
        if not series:
            sys.exit(f"no arm-tagged series under {root} "
                     f"(arms filter: {args.arms or 'none'})")
        # Stable legend ordering: model → think → arm.
        arm_rank = {a: i for i, a in enumerate(ALL_ARMS)}
        series.sort(key=lambda s: (s["model"], s["think"],
                                    arm_rank.get(s["cond"], 99)))
        for s in series:
            if s["think"] == "default":
                s["_label"] = f"{s['model']} · {s['cond']}"
            else:
                s["_label"] = f"{s['model']} · {s['think']} · {s['cond']}"
        # Suffix the output dir by the H1/H2 filter so back-to-back runs
        # don't overwrite each other (a common analyzer pattern).
        sub = "by_arm"
        if args.arms:
            sub = "by_arm_" + "_".join(sorted(wanted))
        out = root / "plots" / sub
    elif args.merge:
        series = merge_series(series)
        # Within a (model, think) the no-tools baseline reads first, then
        # the merged tools row — keeps legend ordering natural.
        series.sort(key=lambda s: (
            s["model"], s["think"],
            0 if s["cond"] == "no-tools" else 1,
        ))
        for s in series:
            cond_short = "no-tools" if s["cond"] == "no-tools" else "tools"
            if s["think"] == "default":
                s["_label"] = f"{s['model']} · {cond_short}"
            else:
                s["_label"] = f"{s['model']} · {s['think']} · {cond_short}"
        out = root / "plots" / "merged"
    else:
        order_key = {
            "model": lambda s: (s["model"], s["think"], s["cond"]),
            "think": lambda s: (s["think"], s["model"], s["cond"]),
            "cond":  lambda s: (s["cond"], s["model"], s["think"]),
        }[args.group_by]
        series.sort(key=order_key)
        for s in series:
            s["_label"] = label(s, args.group_by)
        out = root / "plots"
    out.mkdir(exist_ok=True, parents=True)
    figs = _parse_figs(args.figs)
    written = []
    if 1 in figs:
        fig1(series, out / "fig1_single_task.png", args.ci); written.append("fig1")
    if 3 in figs:
        fig3(series, out / "fig3_tool_selection.png"); written.append("fig3")
    if 4 in figs:
        fig4(series, out / "fig4_failure_breakdown.png"); written.append("fig4")
    if 5 in figs:
        fig5(series, out / "fig5_domain_heatmap.png"); written.append("fig5")
    if 6 in figs:
        fig6(series, out / "fig6_tool_adherence.png", args.ci); written.append("fig6")
    print(f"wrote {len(series)} series → {out}/[{','.join(written)}]")


if __name__ == "__main__":
    main()
