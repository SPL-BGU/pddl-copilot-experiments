"""Regenerate the paper's Results figures as vector PDFs.

Reuses the analyzer deck's data + metric layer (build_deck.load_all,
rq_deck.cell_success / cell_toolsel / cell_cost_of_pass / _pooled_rows / theme)
so every number is byte-identical to the locked deck — this script only changes
how the figures are DRAWN, never how the data is computed. Read-only over
`results/`.

Outputs (vector PDF, into this directory):
  solve.pdf, simulate.pdf            — Fig 1, success-by-arm, y-axis capped ~105
  mechanism_validate_plan.pdf        — Fig 2, + faded P(correct|call) reference
  token_quadrant.pdf                 — Fig 3, + cost-of-pass labels, clean 10^k ticks
  failure_taxonomy.pdf               — NEW, per-task x arm failure-mode stacked bars

Run from anywhere:
  python3 paper/figures/make_paper_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / ".claude/skills/analyzer/scripts"
sys.path.insert(0, str(SCRIPTS))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

import build_deck as bd          # noqa: E402
import rq_deck as rq             # noqa: E402  (also sets the shared rcParams theme)

OUT = HERE
THINK = rq.THINK                 # "off" — the unconfounded headline read


def _savepdf(fig, name: str) -> Path:
    p = OUT / name
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {p.relative_to(REPO)}")
    return p


# ----------------------------------------------------------------------------
# Fig 1 — success by arm, y-axis capped at ~105 (was 122; cuts wasted whitespace)
# ----------------------------------------------------------------------------
def fig_success_by_arm(task: str, save_name: str) -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.set_axisbelow(True)
    x = np.arange(len(rq.CHART_MODELS))
    w = 0.26
    YMAX = 105
    ax.set_ylim(0, YMAX)
    band_lo = min(rq.CHART_MODELS.index(m) for m in rq.MODELS_9B) - 0.5
    ax.axvspan(band_lo, len(rq.CHART_MODELS) - 0.5, color=rq.C_BRAND, alpha=0.05, zorder=0)
    ax.axvline(band_lo, ls=(0, (4, 3)), lw=0.9, color=rq.C_SPINE, zorder=1)
    for i, arm in enumerate(rq.ARMS):
        rates, errs = [], [[], []]
        for m in rq.CHART_MODELS:
            c = rq.cell_success(m, task, arm)
            r = c.rate * 100 if c.n else np.nan
            rates.append(r)
            errs[0].append(max(0.0, (c.rate - c.lo) * 100) if c.n else 0)
            errs[1].append(max(0.0, (c.hi - c.rate) * 100) if c.n else 0)
        bars = ax.bar(x + (i - 1) * w, rates, w, label=rq.ARM_DISP[arm],
                      color=rq.ARM_COLOR[arm], yerr=errs, capsize=2,
                      edgecolor="white", linewidth=0.5, zorder=3,
                      error_kw=dict(lw=0.8, ecolor="#555"))
        rq._bar_value_labels(ax, bars, rates, ymax=YMAX)
    ax.set_xticks(x)
    ax.set_xticklabels([rq.MODEL_DISP[m] for m in rq.CHART_MODELS], rotation=12)
    ax.set_ylabel("success rate (%)")
    ax.set_title(f"{rq.TASK_DISP[task]} — success by arm  ·  think={THINK}")
    ax.text(len(rq.CHART_MODELS) - 0.5, YMAX - 2, "≥9B headline", ha="right",
            va="top", fontsize=7, style="italic", color=rq.C_SOFT)
    # legend below the axes — there is no interior whitespace once y is capped.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3,
              frameon=False)
    ax.grid(axis="y")
    rq._despine(ax)
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig 2 — validate_plan mechanism + faded P(correct|call) reference on success
# ----------------------------------------------------------------------------
def _correct_given_call(model: str, task: str, arm: str) -> float:
    rows = [r for r in bd.CELLS.get((model, THINK, arm), [])
            if r["task"] == task and r.get("with_tools") and r.get("tool_selected")]
    n = len(rows)
    s = sum(1 for r in rows if r["success"])
    return (s / n * 100) if n else float("nan")


def fig_mechanism(task: str, save_name: str) -> Path:
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.4, 4.0))
    x = np.arange(len(rq.MODELS_9B))
    w = 0.38
    arms = ("tl-neut", "tl-ster")
    for ax, metric, fn in ((axL, "tool-use rate (tool_selected %)", rq.cell_toolsel),
                           (axR, "success rate (%)", rq.cell_success)):
        ax.set_axisbelow(True)
        ax.set_ylim(0, 112)
        for i, arm in enumerate(arms):
            vals = [getattr(fn(m, task, arm), "rate") * 100 if fn(m, task, arm).n
                    else np.nan for m in rq.MODELS_9B]
            bars = ax.bar(x + (i - 0.5) * w, vals, w, color=rq.ARM_COLOR[arm],
                          label=rq.ARM_DISP[arm], edgecolor="white", linewidth=0.5,
                          zorder=3)
            rq._bar_value_labels(ax, bars, vals)
        ax.set_xticks(x)
        ax.set_xticklabels([rq.MODEL_DISP[m] for m in rq.MODELS_9B], rotation=12)
        ax.set_ylabel(metric)
        ax.grid(axis="y")
        rq._despine(ax)
    # Faded reference: accuracy *when the validator is called*. It sits at ~99%
    # for every model/arm, so wherever the success bar is short the gap is
    # silence (no call), not error.
    ref_label_done = False
    for i, arm in enumerate(arms):
        for j, m in enumerate(rq.MODELS_9B):
            pcc = _correct_given_call(m, task, arm)
            if pcc != pcc:
                continue
            cx = x[j] + (i - 0.5) * w
            axR.hlines(pcc, cx - w / 2, cx + w / 2, color=rq.C_INK, alpha=0.55,
                       lw=1.4, ls=(0, (2, 1.4)), zorder=5,
                       label=("accuracy when called" if not ref_label_done else None))
            ref_label_done = True
    axL.set_title(f"{rq.TASK_DISP[task]} — tool-use rate")
    axR.set_title("…raises success")
    axR.legend(loc="lower right", framealpha=0.92)
    fig.suptitle(f"{rq.TASK_DISP[task]} mechanism: steering raises tool-calling, "
                 f"which raises success  ·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=rq.C_INK, y=1.02)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig 3 — token quadrant + cost-of-pass multiplier per panel + clean 10^k ticks
# ----------------------------------------------------------------------------
def _pooled_cop(task: str, arm: str) -> float:
    """Pooled (≥9B) cost-of-pass = Σ total tokens ÷ #successes. inf when the arm
    produced no success (a floored baseline cannot be priced)."""
    rows = [r for r in rq._pooled_rows(rq.MODELS_9B, arm)
            if r["task"] == task and r.get("tokens")]
    tok = sum(int(r["tokens"].get("prompt", 0) or 0)
              + int(r["tokens"].get("completion", 0) or 0) for r in rows)
    s = sum(1 for r in rows if r["success"])
    return (tok / s) if s else float("inf")


def fig_token_quadrant(save_name: str) -> Path:
    fig, axes = plt.subplots(1, len(rq.ALL_TASKS), figsize=(13.2, 3.6), sharey=True)
    for ax, task in zip(axes, rq.ALL_TASKS):
        ax.set_axisbelow(True)
        for m in rq.MODELS_9B:
            st0 = bd.token_stats(bd.CELLS.get((m, THINK, "nt-neut"), []), task)
            st1 = bd.token_stats(bd.CELLS.get((m, THINK, "tl-ster"), []), task)
            c0 = rq.cell_success(m, task, "nt-neut")
            c1 = rq.cell_success(m, task, "tl-ster")
            if not (st0["n"] and st1["n"] and c0.n and c1.n):
                continue
            x0, y0 = st0["total"], c0.rate * 100
            x1, y1 = st1["total"], c1.rate * 100
            col = rq.MODEL_COLOR[m]
            ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=3,
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6,
                                        shrinkA=4, shrinkB=4, alpha=0.9))
            ax.scatter([x0], [y0], s=26, color="white", edgecolor=col,
                       linewidth=1.4, zorder=4)
            ax.scatter([x1], [y1], s=30, color=col, edgecolor="white",
                       linewidth=0.8, zorder=4,
                       label=rq.MODEL_DISP[m] if task == rq.ALL_TASKS[0] else None)
        # cost-of-pass multiplier: tool-steered ÷ no-tools, pooled ≥9B.
        cop_nt, cop_tl = _pooled_cop(task, "nt-neut"), _pooled_cop(task, "tl-ster")
        if cop_nt == float("inf"):
            label, col = "cost-of-pass: tool-only", rq.C_BRAND
        else:
            mult = cop_tl / cop_nt
            col = "#2E7D32" if mult < 1 else rq.C_SOFT
            label = f"cost-of-pass {mult:.1f}×"
        ax.text(0.5, 0.045, label, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=7.5, fontweight="bold", color=col,
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=rq.C_RULE,
                          lw=0.7, alpha=0.92), zorder=6)
        ax.set_xscale("log")
        ax.set_xlim(500, 60000)
        ax.set_ylim(-4, 106)
        ax.set_title(rq.TASK_DISP[task], fontsize=9.5)
        ax.set_xlabel("tokens/trial (log)", fontsize=8)
        # clean 10^3 / 10^4 major ticks; suppress the cluttered minor labels
        ax.xaxis.set_major_locator(mticker.LogLocator(base=10, numticks=6))
        ax.xaxis.set_major_formatter(mticker.LogFormatterMathtext(base=10))
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())
        ax.grid(True, which="major", axis="both")
        rq._despine(ax)
    axes[0].set_ylabel("success rate (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.09), fontsize=8)
    fig.suptitle("What the tokens buy — total tokens/trial vs success, "
                 f"arrows run no-tools (open) to +tool steered (filled)  ·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=rq.C_INK, y=1.05)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# NEW Fig — failure-mode taxonomy, per task × arm (100%-stacked, pooled ≥9B)
# ----------------------------------------------------------------------------
# Each trial maps to exactly one category by (success, failure_reason); the
# split separates budget truncation from silence from genuine content errors.
FR_TO_CAT = {
    "truncated_no_answer": "truncated",
    "tool_not_selected":   "no tool call",
    "format_parse_fail":   "unparseable",
    "verdict_mismatch":    "wrong content",
    "plan_invalid":        "wrong content",
    "result_mismatch":     "wrong content",
    "tool_error":          "tool-call error",
    "wrong_tool":          "tool-call error",
    "loop_exhausted":      "tool-call error",
}
CAT_ORDER = ["success", "truncated", "no tool call", "unparseable",
             "wrong content", "tool-call error"]
CAT_COLOR = {
    "success":         "#6A994E",   # green
    "truncated":       "#9AA3AE",   # grey  — budget exhaustion
    "no tool call":    "#E07B39",   # orange — silence (the mechanism)
    "unparseable":     "#8E5572",   # mauve
    "wrong content":   "#C44E52",   # red   — parseable but wrong
    "tool-call error": "#4C72B0",   # blue  — tool mechanics
}


def _cell_failure_mix(task: str, arm: str) -> dict:
    rows = [r for r in rq._pooled_rows(rq.MODELS_9B, arm) if r["task"] == task]
    n = len(rows)
    counts = {c: 0 for c in CAT_ORDER}
    for r in rows:
        if r["success"]:
            counts["success"] += 1
        else:
            counts[FR_TO_CAT.get(r.get("failure_reason"), "tool-call error")] += 1
    return {c: (counts[c] / n * 100 if n else 0.0) for c in CAT_ORDER} | {"n": n}


def fig_failure_taxonomy(save_name: str) -> Path:
    arms = rq.ARMS
    fig, axes = plt.subplots(1, len(rq.ALL_TASKS), figsize=(13.2, 3.7), sharey=True)
    for ax, task in zip(axes, rq.ALL_TASKS):
        ax.set_axisbelow(True)
        x = np.arange(len(arms))
        bottoms = np.zeros(len(arms))
        for cat in CAT_ORDER:
            vals = np.array([_cell_failure_mix(task, a)[cat] for a in arms])
            ax.bar(x, vals, 0.74, bottom=bottoms, color=CAT_COLOR[cat],
                   edgecolor="white", linewidth=0.5, zorder=3,
                   label=cat if task == rq.ALL_TASKS[0] else None)
            bottoms += vals
        ax.set_xticks(x)
        ax.set_xticklabels(["no-tools", "+plain", "+steered"], rotation=18,
                           fontsize=7.5)
        ax.set_ylim(0, 100)
        ax.set_title(rq.TASK_DISP[task], fontsize=9.5)
        ax.grid(axis="y")
        rq._despine(ax)
    axes[0].set_ylabel("share of trials (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.5, -0.06), fontsize=8)
    fig.suptitle("How models fail — per-trial outcome composition by task and arm "
                 f"·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=rq.C_INK, y=1.04)
    fig.tight_layout()
    return _savepdf(fig, save_name)


def main() -> int:
    bd.CELLS = bd.load_all(rq.RESULTS_ROOT)
    print(f"loaded {sum(len(v) for v in bd.CELLS.values())} trials "
          f"from {rq.RESULTS_ROOT.relative_to(REPO)}")
    fig_success_by_arm("solve", "solve.pdf")
    fig_success_by_arm("simulate", "simulate.pdf")
    fig_mechanism("validate_plan", "mechanism_validate_plan.pdf")
    fig_token_quadrant("token_quadrant.pdf")
    fig_failure_taxonomy("failure_taxonomy.pdf")
    # sanity prints for the paper text
    print("\ncost-of-pass multipliers (tl-ster ÷ nt-neut, pooled ≥9B):")
    for t in rq.ALL_TASKS:
        nt, tl = _pooled_cop(t, "nt-neut"), _pooled_cop(t, "tl-ster")
        m = "tool-only" if nt == float("inf") else f"{tl/nt:.2f}×"
        print(f"  {t:18s} {m}")
    print("\nsimulate no-tools failure mix (≥9B):")
    mix = _cell_failure_mix("simulate", "nt-neut")
    for c in CAT_ORDER:
        if mix[c] > 0.05:
            print(f"  {c:16s} {mix[c]:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
