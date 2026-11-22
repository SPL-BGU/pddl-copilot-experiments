#!/usr/bin/env python3
"""Figures for the RQ1 metrics, drawn from tools/reanalysis/out/rq1_metrics.json.

    python -m tools.reanalysis.rq1_figures [--json FILE] [--out DIR]

Reads only the JSON that `rq1_metrics.py` wrote (no results data), so a figure
can never differ from the tables in NUMBERS.md. Writes a vector PDF and a PNG
of each figure into tools/reanalysis/out/figs/ (not into paper/figures/: a
figure moves there when the paper section that uses it is written).

  rq1_validate_plan_errors   false negatives and false positives, by model and arm
  rq1_simulate_by_length     share of states right against trace length
                             (strict score on top, lenient score below)
  rq1_solve_by_length        delivered solve success against reference plan length

Arms keep one colour, line style and marker everywhere: no tools (grey,
dashed, circle), tools with the plain prompt (blue, square), tools with the
steered prompt (orange, triangle). The Claude tool arm ran the plain prompt
only. Whiskers are the 95% domain-cluster bootstrap intervals of the tables.
The three colours pass the colour-blind and normal-vision separation checks of
the dataviz validator; the grey is a deliberate neutral for the baseline arm.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SPINE, GRID = "#1B2430", "#BBC1CA", "#E6E9EE"
ARMS = {  # arm -> (label, colour, line style, marker)
    "none": ("no tools", "#5E5E5E", (0, (4, 2)), "o"),
    "plain": ("tools, plain prompt", "#1F93C9", "-", "s"),
    "tools": ("tools, plain prompt", "#1F93C9", "-", "s"),
    "steered": ("tools, steered prompt", "#D9722E", "-", "^"),
}
MODELS = ("Qwen3.5-9B", "Gemma-26B", "Qwen3.6-35B", "Claude Haiku 4.5", "Claude Sonnet 4.6")
BINS = ("1–5", "6–10", "11–20", "21–40", "41+")

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.labelsize": 9,
    "axes.labelcolor": INK, "axes.edgecolor": SPINE, "axes.linewidth": 0.9, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "grid.color": GRID, "grid.linewidth": 0.8, "legend.fontsize": 8.5, "legend.frameon": False,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
})


def arms_of(cells: list[dict], model: str) -> list[str]:
    return [a for a in ("none", "plain", "tools", "steered")
            if any(c["model"] == model and c["arm"] == a for c in cells)]


def legend(fig, arms=("none", "plain", "steered")) -> None:
    handles = [plt.Line2D([], [], color=ARMS[a][1], ls=ARMS[a][2], marker=ARMS[a][3], ms=5,
                          lw=1.8, label=ARMS[a][0]) for a in arms]
    fig.legend(handles=handles, loc="upper center", ncol=len(arms), bbox_to_anchor=(0.5, 1.0))


def save(fig, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(out / f"{name}.png", bbox_inches="tight", dpi=170)
    plt.close(fig)
    print(f"wrote {out / name}.{{pdf,png}}")


def whisker(b: dict) -> tuple[float, float]:
    return b["est"] - b["lo"], b["hi"] - b["est"]


def fig_errors(res: dict, out: Path) -> None:
    cells = {(c["model"], c["arm"]): c for c in res["m1"]["cells"]}
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.5), sharey=True)
    w = 0.25
    for ax, key, title in ((axes[0], "fn_rate", "False negatives: valid plans rejected"),
                           (axes[1], "fp_rate", "False positives: broken plans accepted")):
        for i, m in enumerate(MODELS):
            arms = arms_of(res["m1"]["cells"], m)
            for j, a in enumerate(arms):
                b = cells[(m, a)][key]
                x = i + (j - (len(arms) - 1) / 2) * (w + 0.03)
                lo, hi = whisker(b)
                ax.bar(x, b["est"], w, color=ARMS[a][1], edgecolor="white", linewidth=0.6,
                       zorder=3)
                ax.errorbar(x, b["est"], yerr=[[lo], [hi]], fmt="none", ecolor=INK,
                            elinewidth=0.8, capsize=2, zorder=4)
        ax.set_xticks(range(len(MODELS)))
        ax.set_xticklabels([m.replace("Claude ", "Claude\n") for m in MODELS])
        ax.set_title(title)
        ax.grid(axis="y", zorder=0)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("share of plans (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=ARMS[a][1], label=ARMS[a][0])
               for a in ("none", "plain", "steered")]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.08))
    save(fig, out, "rq1_validate_plan_errors")


def line_panels(axes, cells: list[dict], field: str, bins=BINS) -> None:
    by = {(c["model"], c["arm"], c["bin"]): c for c in cells}
    x = np.arange(len(bins))
    for ax, m in zip(axes, MODELS):
        arms = arms_of(cells, m)
        for j, a in enumerate(arms):
            pts = [(i, by[(m, a, b)][field]) for i, b in enumerate(bins) if (m, a, b) in by]
            xs = np.array([p[0] for p in pts]) + (j - (len(arms) - 1) / 2) * 0.07
            ys = [p[1]["est"] for p in pts]
            err = np.array([whisker(p[1]) for p in pts]).T
            _lab, col, ls, mk = ARMS[a]
            ax.errorbar(xs, ys, yerr=err, color=col, ls=ls, marker=mk, ms=4.5, lw=1.8,
                        elinewidth=0.8, capsize=1.5, markeredgecolor="white",
                        markeredgewidth=0.6, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(bins)
        ax.set_ylim(-3, 103)
        ax.grid(axis="y", zorder=0)
        ax.set_axisbelow(True)


def fig_simulate(res: dict, out: Path) -> None:
    fig, axes = plt.subplots(2, 5, figsize=(13.4, 5.6), sharey=True, sharex=True)
    for row, (field, label) in enumerate((("states", "states right, strict (%)"),
                                          ("states_salvaged", "states right, lenient (%)"))):
        line_panels(axes[row], res["m2"]["cells"], field)
        axes[row][0].set_ylabel(label)
    for ax, m in zip(axes[0], MODELS):
        ax.set_title(m)
    for ax in axes[1]:
        ax.set_xlabel("trace length (actions)")
    legend(fig)
    fig.subplots_adjust(top=0.88, hspace=0.12, wspace=0.08)
    save(fig, out, "rq1_simulate_by_length")


def fig_solve(res: dict, out: Path) -> None:
    fig, axes = plt.subplots(1, 5, figsize=(13.4, 3.1), sharey=True)
    line_panels(axes, res["m3"]["by_length"], "solved")
    for ax, m in zip(axes, MODELS):
        ax.set_title(m)
        ax.set_xlabel("reference plan length (actions)")
    axes[0].set_ylabel("problems solved (%)")
    legend(fig)
    fig.subplots_adjust(top=0.80, wspace=0.08)
    save(fig, out, "rq1_solve_by_length")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=HERE / "out" / "rq1_metrics.json")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "figs")
    args = ap.parse_args(argv)
    res = json.loads(args.json.read_text())
    fig_errors(res, args.out)
    fig_simulate(res, args.out)
    fig_solve(res, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
