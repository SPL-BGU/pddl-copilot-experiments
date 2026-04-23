"""Paper-style plots from a results root. Auto-discovers series from dir
names + summary metadata; no hardcoded SERIES table.

Usage:
    python3 plot.py                                    # auto-pick latest root
    python3 plot.py results/full-cluster-run1          # explicit root
    python3 plot.py results/cluster-20260421 --group-by think

Three figures written to <root>/plots/:
    fig1_single_task.png    — tasks × series bars
    fig2_chain.png          — chain length × series bars (chain=1 is ST mean)
    fig3_tool_selection.png — classical vs numeric planner-selection rate
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

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
CLASSICAL = {"barman", "blocksworld", "depots", "rovers", "satellite"}
NUMERIC = {"counters", "depot", "farmland", "pogo_stick", "sailing"}

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


def grouped_bars(ax, x, series, width, get_vals, annotate=True):
    n = len(series)
    for i, s in enumerate(series):
        offset = (i - (n - 1) / 2) * width
        vals = get_vals(s)
        color, hatch = style(s)
        bars = ax.bar(x + offset, vals, width,
                      label=s["_label"], color=color,
                      edgecolor="black", linewidth=0.5, hatch=hatch)
        if annotate:
            for b, v in zip(bars, vals):
                if v > 0.02:
                    ax.text(b.get_x() + b.get_width() / 2, v + 0.012,
                            f"{int(round(v * 100))}",
                            ha="center", va="bottom", fontsize=6)


def fig1(series, out_path):
    x = np.arange(len(TASKS))
    n = max(1, len(series))
    width = 0.95 / n
    fig, ax = plt.subplots(figsize=(max(9.0, 1.1 * n + 6), 4.3))

    def vals(s):
        rates = {r["task"]: r["success_rate"]
                 for r in s["summary"]["single_task"] if r["n"] > 0}
        return [rates.get(t, 0.0) for t in TASKS]

    grouped_bars(ax, x, series, width, vals)

    ax.set_xticks(x)
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS])
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1.0)
    ax.set_title("Single-task success rate")
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, framealpha=0.9, ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig2(series, out_path):
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

    grouped_bars(ax, x, series, width, vals)

    ax.set_xticks(x)
    ax.set_xticklabels(["1", "2", "3", "4", "5"])
    ax.set_xlabel("Number of tasks in chain")
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1.0)
    ax.set_title("Chained-task success (chain=1 is single-task mean)")
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

    def vals(s):
        c_tot = c_sel = nu_tot = nu_sel = 0
        for r in s.get("instances", []):
            if r["task"] != "solve" or not r.get("with_tools", False):
                continue
            dn = r["domain_name"]
            if dn in CLASSICAL:
                c_tot += 1
                if r.get("tool_selected"):
                    c_sel += 1
            elif dn in NUMERIC:
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", type=Path, default=None)
    ap.add_argument("--group-by", default="model", choices=("model", "think", "cond"),
                    help="controls legend ordering / label emphasis")
    ap.add_argument("--include-legacy", action="store_true", default=True,
                    help="include legacy (no-think) dirs as think=default (default: on)")
    args = ap.parse_args()

    root = args.root or find_default_root()
    series = load_series(root, args.include_legacy)
    if not series:
        sys.exit(f"no parseable slurm_* dirs under {root}")

    order_key = {
        "model": lambda s: (s["model"], s["think"], s["cond"]),
        "think": lambda s: (s["think"], s["model"], s["cond"]),
        "cond":  lambda s: (s["cond"], s["model"], s["think"]),
    }[args.group_by]
    series.sort(key=order_key)
    for s in series:
        s["_label"] = label(s, args.group_by)

    out = root / "plots"
    out.mkdir(exist_ok=True)
    fig1(series, out / "fig1_single_task.png")
    fig2(series, out / "fig2_chain.png")
    fig3(series, out / "fig3_tool_selection.png")
    print(f"wrote {len(series)} series → {out}/fig[1-3]_*.png")


if __name__ == "__main__":
    main()
