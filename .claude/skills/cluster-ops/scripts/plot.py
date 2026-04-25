"""Paper-style plots from a results root. Auto-discovers series from dir
names + summary metadata; no hardcoded SERIES table.

Usage:
    python3 plot.py                                    # auto-pick latest root
    python3 plot.py results/full-cluster-run1          # explicit root
    python3 plot.py results/cluster-20260421 --group-by think
    python3 plot.py results/cluster-20260424 --figs 1,4,5 --no-ci

Figures written to <root>/plots/:
    fig1_single_task.png       — tasks × series bars (Wilson CI whiskers)
    fig2_chain.png             — chain length × series bars (chain=1 is ST mean)
    fig3_tool_selection.png    — classical vs numeric planner-selection rate
    fig4_failure_breakdown.png — 100%-stacked failure reasons per task × series
    fig5_domain_heatmap.png    — (series × 10 domains) heatmap per task
    fig6_tool_adherence.png    — per-task tool_selected_rate (with-tools only)
    fig7_chain_step_survival.png — P(reach step k) per chain length L=2..5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
TASK_LABELS = {
    "solve": "Solve",
    "validate_domain": "Val-Dom",
    "validate_problem": "Val-Prob",
    "validate_plan": "Val-Plan",
    "simulate": "Simulate",
}
CONDITIONS = ["no-tools",
              "tools_per-task_minimal", "tools_per-task_guided",
              "tools_all_minimal", "tools_all_guided"]
CLASSICAL = ["barman", "blocksworld", "depots", "rovers", "satellite"]
NUMERIC = ["counters", "depot", "farmland", "pogo_stick", "sailing"]
DOMAINS = CLASSICAL + NUMERIC

# Colors by family, hatching by tool condition.
# Keys are the underscore-tagged model form produced by parse_dirname
# (submit_all.sh does `tr '/:.' '___'`), which is what we see in dir names.
MODEL_COLORS = {
    "Qwen3_5_0_8B":  "#d4c96b",
    "Qwen3_5_27b":   "#b89d2a",
    "gpt-oss_20b":   "#5c7fb3",
    "gpt-oss_120b":  "#1a2e4f",
    "gemma4_31b":    "#6f4a8a",
}
COND_HATCH = {
    "no-tools":               None,
    "tools_all_minimal":      "///",
    "tools_all_guided":       "\\\\\\",
    "tools_per-task_minimal": "...",
    "tools_per-task_guided":  "+++",
}
# think-mode shade: on → lighter tint of the model base color.
# off / default keep the base color unchanged.
THINK_LIGHTEN = {"off": 0.0, "default": 0.0, "on": 0.55}

# Canonical order + color for failure reasons in fig4. Unknown reasons
# bucket into 'other'. Keep in sync with FR_* constants in run_experiment.py.
FAILURE_REASONS = [
    "ok", "tool_not_selected", "tool_error", "ollama_parse_error",
    "loop_exhausted", "verdict_mismatch", "result_mismatch",
    "no_verdict_parsed", "simulate_empty", "plan_invalid",
    "truncated_no_answer", "exception", "unknown", "other",
]
FAILURE_COLORS = {
    "ok":                  "#2ca02c",
    "tool_not_selected":   "#d62728",
    "tool_error":          "#ff7f0e",
    "ollama_parse_error":  "#9467bd",
    "loop_exhausted":      "#8c564b",
    "verdict_mismatch":    "#e377c2",
    "result_mismatch":     "#7f7f7f",
    "no_verdict_parsed":   "#bcbd22",
    "simulate_empty":      "#17becf",
    "plan_invalid":        "#1f77b4",
    "truncated_no_answer": "#aec7e8",
    "exception":           "#ff9896",
    "unknown":             "#c5b0d5",
    "other":               "#dddddd",
}


def _lighten(hex_color: str, factor: float) -> str:
    """Blend `hex_color` toward white by `factor` ∈ [0, 1]."""
    if factor <= 0.0:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def find_default_root() -> Path:
    repo = Path(__file__).resolve().parents[4]
    results = repo / "results"
    candidates = sorted(
        list(results.glob("cluster-*")) + list(results.glob("full-cluster-run*")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(f"no results/cluster-* or results/full-cluster-run* dirs under {results}")
    return candidates[0]


def parse_dirname(name: str) -> dict | None:
    stem = name.removeprefix("slurm_")
    m = re.match(r"^(.*)_(\d+)$", stem)
    if not m:
        return None
    rest, jobid = m.group(1), m.group(2)
    for cond in CONDITIONS:
        suf = "_" + cond
        if rest.endswith(suf):
            pre = rest[: -len(suf)]
            for think in ("on", "off", "default"):
                s = "_" + think
                if pre.endswith(s):
                    model = pre[: -len(s)]
                    return {"model": model, "think": think, "cond": cond, "jobid": jobid}
            return {"model": pre, "think": "default", "cond": cond, "jobid": jobid, "legacy": True}
    return None


def load_series(root: Path, include_legacy: bool) -> list[dict]:
    entries = []
    for d in sorted(root.glob("slurm_*")):
        if not d.is_dir():
            continue
        info = parse_dirname(d.name)
        if info is None:
            continue
        if info.get("legacy") and not include_legacy:
            continue
        sfs = sorted(d.glob("summary_*.json"))
        if not sfs:
            continue
        stfs = sorted(d.glob("single_task_*.json"))
        with sfs[-1].open() as f:
            summary = json.load(f)
        instances = []
        if stfs:
            with stfs[-1].open() as f:
                instances = json.load(f)
        info["summary"] = summary
        info["instances"] = instances
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
    base = MODEL_COLORS.get(info["model"], "#888888")
    color = _lighten(base, THINK_LIGHTEN.get(info["think"], 0.0))
    hatch = COND_HATCH.get(info["cond"])
    return color, hatch


def _wilson_err(rate: float, lo: float, hi: float) -> tuple[float, float]:
    """Return (err_lo, err_hi) for matplotlib errorbar yerr (always ≥0)."""
    return max(0.0, rate - lo), max(0.0, hi - rate)


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval at the given z (default 95%). Matches run_experiment.py."""
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = (z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)


def merge_series(series: list[dict]) -> list[dict]:
    """Pool tools_* series by (model, think); pass no-tools through unchanged.

    Counts (successes, n, truncated, tool_selected, failure_reasons, chain
    successes/samples) are summed across the tools_* condition variants and
    rates + Wilson CIs are recomputed on the pooled totals — that gives
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

        pooled_chains: list[dict] = []
        for L in (2, 3, 4, 5):
            k = total = 0
            details: list = []
            for s in group:
                c = next((c for c in s["summary"].get("chains", [])
                          if c.get("chain_length") == L and c.get("samples", 0) > 0), None)
                if c is None:
                    continue
                k += c["successes"]
                total += c["samples"]
                details += c.get("samples_detail", [])
            if total == 0:
                continue
            lo, hi = wilson_ci(k, total)
            pooled_chains.append({
                "model": model, "with_tools": True,
                "chain_length": L, "samples": total, "successes": k,
                "success_rate": round(k / total, 4),
                "ci_lo": lo, "ci_hi": hi,
                "tool_filter": "merged", "prompt_style": "merged",
                "samples_detail": details,
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
                        "chains": pooled_chains, "meta": {}},
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


def fig2(series, out_path, draw_ci):
    x = np.arange(5)  # chain length 1..5 (1 = ST mean)
    n = max(1, len(series))
    width = 0.95 / n
    fig, ax = plt.subplots(figsize=(max(9.0, 1.1 * n + 6), 4.3))

    def vals(s):
        st_rates = [r["success_rate"] for r in s["summary"]["single_task"] if r["n"] > 0]
        l1 = float(np.mean(st_rates)) if st_rates else 0.0
        chains = {c["chain_length"]: c["success_rate"]
                  for c in s["summary"].get("chains", []) if c.get("samples", 0) > 0}
        return [l1] + [chains.get(k, 0.0) for k in (2, 3, 4, 5)]

    def err(s):
        # L=1 is a mean of rates, not a binomial — skip CI there.
        chains = {c["chain_length"]: c for c in s["summary"].get("chains", [])
                  if c.get("samples", 0) > 0}
        lo = [0.0]; hi = [0.0]
        for k in (2, 3, 4, 5):
            c = chains.get(k)
            if c is None:
                lo.append(0.0); hi.append(0.0)
            else:
                el, eh = _wilson_err(c["success_rate"], c["ci_lo"], c["ci_hi"])
                lo.append(el); hi.append(eh)
        return lo, hi

    grouped_bars(ax, x, series, width, vals, get_err=err if draw_ci else None)
    ax.set_xticks(x)
    ax.set_xticklabels(["1", "2", "3", "4", "5"])
    ax.set_xlabel("Number of tasks in chain")
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1.0)
    ax.set_title("Chained-task success (chain=1 is single-task mean)" +
                 (" (Wilson 95% CI)" if draw_ci else ""))
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, framealpha=0.9, ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig3(series, out_path):
    tool_series = [s for s in series if s["cond"] != "no-tools"]
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
    ax.set_title("Correct-planner selection, classical vs numeric")
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
    if len(TASKS) == 1:
        axes = [axes]

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
    fig, axes = plt.subplots(
        1, len(TASKS),
        figsize=(max(16.0, 1.8 * len(TASKS) + 6),
                 max(4.5, 0.22 * len(series) + 3.0)),
        sharey=True,
    )
    if len(TASKS) == 1:
        axes = [axes]

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
        ax.set_xticklabels(DOMAINS, rotation=60, ha="right", fontsize=6)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=6)
        ax.set_title(TASK_LABELS[task], fontsize=9)
        for i in range(len(series)):
            for j in range(len(DOMAINS)):
                c = counts[i][j]
                if c is None:
                    continue
                k, n = c
                cell = grid[i, j]
                color = "white" if cell < 0.45 else "black"
                ax.text(j, i, f"{k}/{n}", ha="center", va="center",
                        color=color, fontsize=5)
    if im is not None:
        fig.colorbar(im, ax=axes, shrink=0.7, pad=0.02, label="success rate")
    fig.suptitle("Per-domain success rate (rows=series, cols=domain)", fontsize=11)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig6(series, out_path, draw_ci):
    """Per-task tool_selected_rate across with-tools series."""
    tool_series = [s for s in series if s["cond"] != "no-tools"]
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
    ax.set_title("Per-task tool-adherence (with-tools runs)" +
                 (" (Wilson 95% CI)" if draw_ci else ""))
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, framealpha=0.9, ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig7(series, out_path):
    """Chain-step survival: P(step k succeeded & all earlier steps succeeded)."""
    chain_series = [s for s in series if any(
        c.get("samples", 0) > 0 for c in s["summary"].get("chains", []))]
    if not chain_series:
        return
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.0), sharey=True)
    lengths = [2, 3, 4, 5]

    for ax, L in zip(axes.flat, lengths):
        ax.set_title(f"Chain length L={L}", fontsize=9)
        ax.set_xlabel("step index k (1-based)")
        ax.set_ylabel("P(survive through step k)")
        ax.set_ylim(-0.02, 1.02)
        ax.set_xticks(list(range(1, L + 1)))
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
        for s in chain_series:
            chain = next((c for c in s["summary"].get("chains", [])
                          if c.get("chain_length") == L and c.get("samples", 0) > 0), None)
            if chain is None:
                continue
            total = chain["samples"]
            details = chain.get("samples_detail", [])
            survival = []
            for k in range(1, L + 1):
                count = 0
                for sample in details:
                    steps = sample.get("step_records", [])
                    if len(steps) >= k and all(
                            steps[j].get("success", False) for j in range(k)):
                        count += 1
                survival.append(count / total if total else 0.0)
            color, _ = style(s)
            ax.plot(range(1, L + 1), survival,
                    marker="o", markersize=4, linewidth=1.2,
                    color=color, label=s["_label"])
    handles, labels_ = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels_, loc="center right",
                   fontsize=6, framealpha=0.9, bbox_to_anchor=(1.02, 0.5))
    fig.suptitle("Chain step survival (every earlier step must also succeed)",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 0.85, 0.96])
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _parse_figs(spec: str) -> set[int]:
    if spec == "all":
        return {1, 2, 3, 4, 5, 6, 7}
    out = set()
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            n = int(piece)
        except ValueError:
            sys.exit(f"--figs: expected 'all' or comma-separated ints, got {spec!r}")
        if n not in (1, 2, 3, 4, 5, 6, 7):
            sys.exit(f"--figs: unknown fig number {n}; valid: 1..7")
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
                    help="comma list of fig numbers to render (1..7), or 'all' (default)")
    ap.add_argument("--no-ci", dest="ci", action="store_false", default=True,
                    help="omit Wilson CI error bars on figs 1, 2, 6")
    ap.add_argument("--merge", action="store_true", default=False,
                    help="pool tool_filter × prompt_style into one tools_merged "
                         "series per (model, think); no-tools series pass "
                         "through unchanged as baselines. writes to "
                         "<root>/plots/merged/")
    args = ap.parse_args()

    root = args.root or find_default_root()
    series = load_series(root, args.include_legacy)
    if not series:
        sys.exit(f"no parseable slurm_* dirs under {root}")

    if args.merge:
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
    if 2 in figs:
        fig2(series, out / "fig2_chain.png", args.ci); written.append("fig2")
    if 3 in figs:
        fig3(series, out / "fig3_tool_selection.png"); written.append("fig3")
    if 4 in figs:
        fig4(series, out / "fig4_failure_breakdown.png"); written.append("fig4")
    if 5 in figs:
        fig5(series, out / "fig5_domain_heatmap.png"); written.append("fig5")
    if 6 in figs:
        fig6(series, out / "fig6_tool_adherence.png", args.ci); written.append("fig6")
    if 7 in figs:
        fig7(series, out / "fig7_chain_step_survival.png"); written.append("fig7")
    print(f"wrote {len(series)} series → {out}/[{','.join(written)}]")


if __name__ == "__main__":
    main()
