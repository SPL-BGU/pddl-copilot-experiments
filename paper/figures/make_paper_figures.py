"""Regenerate the figures of the supplement material, and the funnel figure the
PlanBench section of the paper uses, as vector PDFs.

The text these figures belong to moved from main.tex to supplement_source.tex on
2026-11-25 (all but funnel.pdf, which main.tex still includes).

What each corpus supports (table "What each corpus stored", now in
supplement_source.tex):

  * Open-weight main sweep (results/sweep5v2-live). The final answer was stored
    only up to 500 characters, so the sweep gives NO delivered rate for its tool
    arms. These figures draw three exact quantities from it and nothing else:
    the unaided rate (the harness's run-time grade of the full answer), the
    calling rate and the tool-verified rate. The delivered bounds that the e2e
    overlay computed from the snapshots are retired for the open-weight models
    and are not drawn anywhere (redraw of 2026-11-22). The code that drew them
    (hatched open-weight bars, the cost-of-pass ranges of `_cop_range`, the
    overlay failure mix) last existed at commit 6c7de81.
  * Frontier runs (Claude Haiku 4.5, Sonnet 4.6) and PlanBench. Delivered
    rates, read through the analyzer's overlay aggregator
    (`e2e_overlay.load_e2e_cells`). Exact, except frontier simulate, which is a
    censoring bound <low, high>: solid bar to `low`, hatched extension to
    `high`, never a point.

The delivered comparison for the open-weight models has its own figures, drawn
by tools/reanalysis: rq1_figures.py -> rq1_validate_plan_errors.pdf (and the
rerun's by-length figures rq1_*_by_length.pdf, kept for the supplement), and
rq1_control_metrics.py -> rq1c_*_by_length.pdf, the two by-length figures
main.tex includes.

Outputs (vector PDF, into this directory):
  funnel.pdf                  top row: frontier and PlanBench cascades
                              (CALL -> tool-verified -> delivered; NEED = the
                              no-tools reference line); bottom row: open-weight
                              validate_* cells, CALL and tool-verified only
  solve.pdf, simulate.pdf     open-weight panel: unaided and tool-verified
                              rates; frontier panel: delivered success by arm
  mechanism_validate_plan.pdf calling and tool-verified rates (exact)
  token_quadrant.pdf          mean total tokens per trial by arm (file name
                              kept for the tex; no success axis any more)
  failure_taxonomy.pdf        outcome of the unaided trials, run-time grade

Run from anywhere:
  python3 paper/figures/make_paper_figures.py
Read-only over results/.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
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
from _constants import wilson_ci  # noqa: E402
from e2e_overlay import load_e2e_cells  # noqa: E402

OUT = HERE
THINK = rq.THINK                 # "off" — the unconfounded headline read
OVERLAY = REPO / "results/derived/e2e_overlay"
HATCH = "////"
TASK_SHORT = {"validate_domain": "val.\ndomain", "validate_problem": "val.\nproblem",
              "validate_plan": "val.\nplan", "solve": "solve", "simulate": "simulate"}
TIERS = [("haiku", "Claude Haiku 4.5", "haiku-frontier"),
         ("sonnet", "Claude Sonnet 4.6", "sonnet-frontier")]
C_CALL, C_TV, C_DELIV, C_NEED = "#BBC1CA", "#8FB8D6", rq.C_BRAND, rq.C_INK
SWEEP_ARM_LABEL = {"nt-neut": "no-tools: unaided rate",
                   "tl-neut": "+tool (plain): tool-verified rate",
                   "tl-ster": "+tool (steered): tool-verified rate"}


def _savepdf(fig, name: str) -> Path:
    p = OUT / name
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {p.relative_to(REPO)}")
    return p


# ----------------------------------------------------------------------------
# Open-weight main sweep: exact run-time quantities only (no delivered rate)
# ----------------------------------------------------------------------------
def _exact(c) -> dict:
    """rq.Cell -> the exact-cell dict the drawing helpers take."""
    return {"n": c.n, "ok": c.s, "cens": 0, "low": c.rate, "high": c.rate,
            "exact": True}


def sweep_rate(model: str, task: str, arm: str) -> dict:
    """Main sweep, think=off. no-tools arm: the unaided rate (the harness's
    grade of the full answer, made at run time). Tool arms: the tool-verified
    rate (a tool response held a correct result). Both exact."""
    return _exact(rq.cell_success(model, task, arm))


# ----------------------------------------------------------------------------
# Frontier delivered data layer (overlay = the only source of e2e verdicts)
# ----------------------------------------------------------------------------
_E2E: dict[str, dict] = {}


def e2e_cells(corpus: str) -> dict:
    if corpus not in _E2E:
        _E2E[corpus] = load_e2e_cells(corpus, OVERLAY)
    return _E2E[corpus]


def frontier_wt(tier_corpus: str, task: str) -> dict:
    return e2e_cells(tier_corpus)[(tier_corpus, "default", "tools_all_minimal",
                                   "sweep5v2", "tl-neut", task)]


def frontier_nt_v11(tier_corpus: str, task: str) -> dict:
    """No-tools reference sliced to prompt v11 (frontier D3: the with-tools
    cells are v11-only, so the arm contrast is within one prompt)."""
    n = ok = cens = 0
    for ln in (OVERLAY / tier_corpus / "sweep5v2.e2e.jsonl").open():
        r = json.loads(ln)
        if r["task"] != task or r["prompt_variant"] != 11:
            continue
        n += 1
        ok += r["e2e_strict"] is True
        cens += r["e2e_strict"] == "indeterminate"
    return {"n": n, "ok": ok, "cens": cens, "low": ok / n, "high": (ok + cens) / n,
            "exact": cens == 0}


def frontier_call(tier_corpus: str, task: str) -> tuple[int, int]:
    n = c = 0
    for ln in (REPO / "results" / tier_corpus / "sweep5v2-with-tools/trials.jsonl").open():
        r = json.loads(ln)["result"]
        if r["task"] != task:
            continue
        n += 1
        c += bool(r.get("tool_selected"))
    return c, n


# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def bar_cell(ax, x, cell: dict | None, w: float, color: str, *, label=None,
             zorder=3, show_ci=True):
    """Bar for one cell: solid to `low`; hatched `low..high` when the cell is
    a censoring bound (frontier simulate only); Wilson whisker when exact.
    Returns the bar."""
    if not cell or not cell.get("n"):
        return None
    lo, hi = cell["low"] * 100, cell["high"] * 100
    b = ax.bar(x, lo, w, color=color, label=label, edgecolor="white", linewidth=0.5,
               zorder=zorder)
    if hi > lo + 1e-9:
        ax.bar(x, hi - lo, w, bottom=lo, facecolor="none", edgecolor=color,
               hatch=HATCH, linewidth=0.6, zorder=zorder)
    elif show_ci:
        wl, wh = wilson_ci(cell["ok"], cell["n"])
        ax.errorbar(x, lo, yerr=[[max(0.0, lo - wl * 100)], [max(0.0, wh * 100 - lo)]],
                    fmt="none", ecolor="#555", elinewidth=0.8, capsize=2, zorder=zorder + 1)
    return b


def need_line(ax, x0, x1, cell: dict | None, *, label=None):
    """NEED = the no-tools reference, a line (exact) or a translucent band
    (bound, frontier simulate only). Never a bar: arms are never pooled."""
    if not cell or not cell.get("n"):
        return
    lo, hi = cell["low"] * 100, cell["high"] * 100
    if hi > lo + 1e-9:
        ax.fill_between([x0, x1], lo, hi, color=C_NEED, alpha=0.10, zorder=2,
                        linewidth=0, label=label)
        ax.hlines([lo, hi], x0, x1, color=C_NEED, lw=0.8, ls=(0, (2, 1.5)), zorder=4)
    else:
        ax.hlines(lo, x0, x1, color=C_NEED, lw=1.4, ls=(0, (3, 1.5)), zorder=4,
                  label=label)


def tv_tick(ax, x, w, rate_pct: float):
    """Mechanism-layer reference (tool-verified) as a faint tick."""
    ax.hlines(rate_pct, x - w / 2, x + w / 2, color=rq.C_INK, alpha=0.5, lw=1.2,
              ls=(0, (1.2, 1.0)), zorder=5)


def _label_top(ax, x, cell: dict | None, *, fmt_exact="{:.0f}", fs=6.5, ymax=105):
    if not cell or not cell.get("n"):
        return
    lo, hi = cell["low"] * 100, cell["high"] * 100
    if hi <= lo + 1e-9:
        txt = fmt_exact.format(lo)
    elif round(lo) == round(hi):
        txt = f"{lo:.1f}–{hi:.1f}"
    else:
        txt = f"{lo:.0f}–{hi:.0f}"
    ax.text(x, min(hi, ymax - 3) + 1.2, txt, ha="center", va="bottom", fontsize=fs,
            color=rq.C_INK, zorder=6)


# ----------------------------------------------------------------------------
# Fig 1 — the funnel: within-arm cascade per tier (D-J1 spec, memo §2)
# ----------------------------------------------------------------------------
PB_ROWS = REPO / "results/planbench/wt-anthropic-20260801/sidelogs/formalization_match_rows.jsonl"
# First-draw delivered counts (NUMBERS.md PlanBench block; the rows file
# carries last-attempt 418/431 — asserted below so drift is loud).
PB_DELIVERED_FIRSTDRAW = {"clean": 410, "mystery": 431}
PB_LAST_ATTEMPT = {"clean": 418, "mystery": 431}
PB_NEED = {"clean": 287 / 600, "mystery": 0.0}   # matched-NT delivered (47.8 / 0.0)


def planbench_stages() -> dict[str, dict]:
    st = {k: Counter() for k in ("clean", "mystery")}
    for ln in PB_ROWS.open():
        r = json.loads(ln)
        c = st[r["kind"]]
        c["n"] += 1
        c["formalize"] += bool(r["match"])
        c["call"] += bool(r["delegated"])
        c["plan_found"] += bool(r["solvable"])
        c["delivered_last"] += bool(r["llm_correct"])
    for k, c in st.items():
        assert c["n"] == 600, (k, c["n"])
        assert c["delivered_last"] == PB_LAST_ATTEMPT[k], (k, c["delivered_last"])
    return st


def _cascade_panel(ax, groups, stages, need, *, title, xlabels, stage_labels,
                   colors, ymax=108, legend=False, slots=None):
    """groups: list of per-group dicts {stage_name: cell_or_rate}; stages: the
    ordered stage keys; need: per-group cell for the reference line. `slots`
    sets the bar width to 0.8/slots when a panel draws fewer stages than the
    other row (the open-weight row has two), so its bars do not grow fat."""
    ax.set_axisbelow(True)
    k = len(stages)
    w = 0.8 / (slots or k)
    half = k * w / 2 + 0.05
    x = np.arange(len(groups))
    for si, (skey, slabel, col) in enumerate(zip(stages, stage_labels, colors)):
        for gi, g in enumerate(groups):
            cx = x[gi] + (si - (k - 1) / 2) * w
            cell = g.get(skey)
            if cell is None:
                continue
            if isinstance(cell, dict):
                bar_cell(ax, cx, cell, w * 0.95, col, label=(slabel if gi == 0 else None),
                         show_ci=False)
                _label_top(ax, cx, cell)
            else:
                ax.bar(cx, cell * 100, w * 0.95, color=col, edgecolor="white",
                       linewidth=0.5, zorder=3, label=(slabel if gi == 0 else None))
                ax.text(cx, min(cell * 100, ymax - 3) + 1.2, f"{cell*100:.0f}",
                        ha="center", va="bottom", fontsize=6.5, color=rq.C_INK, zorder=6)
    for gi, g in enumerate(groups):
        need_line(ax, x[gi] - half, x[gi] + half, need[gi],
                  label=("no-tools (NEED)" if gi == 0 else None))
    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, fontsize=7.5)
    ax.set_ylim(0, ymax)
    ax.set_title(title, fontsize=9.5)
    ax.grid(axis="y")
    rq._despine(ax)
    return ax.get_legend_handles_labels()


def fig_funnel(save_name: str) -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(13.2, 6.6))
    tasks = rq.ALL_TASKS
    # Row 1: frontier tiers
    for ax, (tier, disp, corpus) in zip(axes[0][:2], TIERS):
        groups, need = [], []
        for t in tasks:
            wt = frontier_wt(corpus, t)
            c, n = frontier_call(corpus, t)
            groups.append({"call": c / n, "tv": wt["tv_ok"] / wt["tv_n"], "deliv": wt})
            need.append(frontier_nt_v11(corpus, t))
        h, l = _cascade_panel(ax, groups, ["call", "tv", "deliv"], need,
                              title=f"{disp} · with-tools (plain), canonical, prompt v11",
                              xlabels=[TASK_SHORT[t] for t in tasks],
                              stage_labels=["tool called (CALL)", "tool result correct",
                                            "delivered correct"],
                              colors=[C_CALL, C_TV, C_DELIV])
        if tier == "haiku":
            handles, labels = list(h), list(l)
    # Row 1, panel 3: PlanBench (Haiku 4.5) with the FORMALIZE leading bar
    st = planbench_stages()
    ax = axes[0][2]
    groups = []
    for k in ("clean", "mystery"):
        c = st[k]
        groups.append({"formalize": c["formalize"] / c["n"], "call": c["call"] / c["n"],
                       "plan": c["plan_found"] / c["n"],
                       "deliv": {"n": c["n"], "ok": PB_DELIVERED_FIRSTDRAW[k], "cens": 0,
                                 "low": PB_DELIVERED_FIRSTDRAW[k] / c["n"],
                                 "high": PB_DELIVERED_FIRSTDRAW[k] / c["n"], "exact": True}})
    need = [{"n": 600, "ok": int(round(PB_NEED[k] * 600)), "cens": 0, "low": PB_NEED[k],
             "high": PB_NEED[k], "exact": True} for k in ("clean", "mystery")]
    h, l = _cascade_panel(ax, groups, ["formalize", "call", "plan", "deliv"], need,
                          title="PlanBench · Claude Haiku 4.5 with tools (n=600 per pool)",
                          xlabels=["Blocksworld", "Mystery Blocksworld"],
                          stage_labels=["FORMALIZE (problem = gold)", "tool called",
                                        "tool plan found", "delivered correct"],
                          colors=["#D9D2E9", C_CALL, C_TV, C_DELIV])
    for hh, ll in zip(h, l):
        if ll.startswith("FORMALIZE") or ll == "tool plan found":
            handles.append(hh); labels.append(ll)
    # Row 2: open roster validate_* (plain arm, canonical, think=off). CALL and
    # tool-verified only: the main sweep has no delivered rate for these cells.
    vtasks = ["validate_domain", "validate_problem", "validate_plan"]
    for ax, m in zip(axes[1], rq.MODELS_9B):
        groups, need = [], []
        for t in vtasks:
            groups.append({"call": rq.cell_toolsel(m, t, "tl-neut").rate,
                           "tv": rq.cell_success(m, t, "tl-neut").rate})
            need.append(sweep_rate(m, t, "nt-neut"))
        _cascade_panel(ax, groups, ["call", "tv"], need,
                       title=f"{rq.MODEL_DISP[m]} · with-tools (plain), canonical, think=off",
                       xlabels=[TASK_SHORT[t] for t in vtasks],
                       stage_labels=["tool called (CALL)", "tool result correct"],
                       colors=[C_CALL, C_TV], slots=2.5)
    axes[0][0].set_ylabel("share of with-tools trials (%)")
    axes[1][0].set_ylabel("share of with-tools trials (%)")
    fig.suptitle("The funnel: share of with-tools trials that call the tool, get a "
                 "correct tool result and (top row) deliver a correct answer  ·  dashed = "
                 "no-tools rate (NEED); hatched = censoring bound",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.01)
    fig.legend(handles, labels, loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.5, -0.045), fontsize=8)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig — solve / simulate: open-weight sweep panel beside the frontier panel
# ----------------------------------------------------------------------------
def _sweep_panel(ax, task: str, *, models: list[str], title: str):
    """Open-weight panel, main sweep, think=off. Grey bar = unaided rate;
    coloured bars = TOOL-VERIFIED rate of each tool arm. Every cell is exact:
    solid bar, Wilson 95% whisker, value above the whisker. No delivered
    quantity is drawn here (the sweep has none for its tool arms)."""
    ax.set_axisbelow(True)
    arms = rq.ARMS
    x = np.arange(len(models))
    w = 0.8 / len(arms)
    YMAX = 108
    ax.set_ylim(0, YMAX)
    if set(models) >= set(rq.MODELS_9B) and len(models) > len(rq.MODELS_9B):
        band_lo = min(models.index(m) for m in rq.MODELS_9B) - 0.5
        ax.axvspan(band_lo, len(models) - 0.5, color=rq.C_BRAND, alpha=0.05, zorder=0)
        ax.axvline(band_lo, ls=(0, (4, 3)), lw=0.9, color=rq.C_SPINE, zorder=1)
    for i, arm in enumerate(arms):
        for j, m in enumerate(models):
            cx = x[j] + (i - (len(arms) - 1) / 2) * w
            cell = sweep_rate(m, task, arm)
            bar_cell(ax, cx, cell, w * 0.95, rq.ARM_COLOR[arm],
                     label=(SWEEP_ARM_LABEL[arm] if j == 0 else None))
            top = wilson_ci(cell["ok"], cell["n"])[1] * 100
            ax.text(cx, min(top, YMAX - 5) + 1.0, f"{cell['low'] * 100:.0f}",
                    ha="center", va="bottom", fontsize=6.5, color=rq.C_INK, zorder=6)
    ax.set_xticks(x)
    ax.set_xticklabels([rq.MODEL_DISP[m] for m in models], rotation=12)
    ax.set_title(title, fontsize=9.5)
    ax.set_ylabel("unaided rate / tool-verified rate (%)")
    ax.grid(axis="y")
    rq._despine(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=7,
              frameon=False, columnspacing=1.4, handlelength=1.4)


def _frontier_panel(ax, task: str, *, title: str):
    ax.set_axisbelow(True)
    x = np.arange(len(TIERS))
    w = 0.36
    YMAX = 108
    ax.set_ylim(0, YMAX)
    for j, (tier, disp, corpus) in enumerate(TIERS):
        nt, wt = frontier_nt_v11(corpus, task), frontier_wt(corpus, task)
        bar_cell(ax, x[j] - w / 2, nt, w * 0.95, rq.ARM_COLOR["nt-neut"],
                 label=("no-tools" if j == 0 else None))
        _label_top(ax, x[j] - w / 2, nt, ymax=YMAX)
        bar_cell(ax, x[j] + w / 2, wt, w * 0.95, rq.ARM_COLOR["tl-neut"],
                 label=("+tool (plain)" if j == 0 else None))
        _label_top(ax, x[j] + w / 2, wt, ymax=YMAX)
        tv_tick(ax, x[j] + w / 2, w * 0.95, wt["tv_ok"] / wt["tv_n"] * 100)
    ax.set_xticks(x)
    ax.set_xticklabels([d for _, d, _ in TIERS], rotation=0)
    ax.set_title(title, fontsize=9.5)
    ax.set_ylabel("delivered success (%)")
    ax.grid(axis="y")
    rq._despine(ax)
    ax.legend(loc="upper left", fontsize=7, framealpha=0.92)


def _fig_sweep_and_frontier(task: str, save_name: str, *, frontier_note: str) -> Path:
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 4.2),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    _sweep_panel(axL, task, models=rq.CHART_MODELS,
                 title=f"open-weight models · main sweep · think={THINK} · "
                       "tool bars are tool-verified rates")
    _frontier_panel(axR, task, title="frontier tiers · canonical · prompt v11")
    fig.suptitle(f"{task}  ·  open-weight: unaided and tool-verified rates  ·  "
                 f"frontier: delivered success ({frontier_note})",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.02)
    fig.tight_layout()
    return _savepdf(fig, save_name)


def fig_solve(save_name: str) -> Path:
    return _fig_sweep_and_frontier("solve", save_name,
                                   frontier_note="dotted tick = tool-verified")


def fig_simulate(save_name: str) -> Path:
    # Open-weight panel: the main sweep's own unaided rate (0 format-exact on
    # every model) and tool-verified rates. The earlier think=on full-storage
    # rerun (iss024d) that this panel used to draw is no longer in the paper.
    return _fig_sweep_and_frontier(
        "simulate", save_name,
        frontier_note="hatched = censoring bound; dotted tick = tool-verified")


# ----------------------------------------------------------------------------
# Fig — validate_plan mechanism (UNCHANGED: mechanism layer, exact everywhere)
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
    for ax, metric, fn in ((axL, "invocation rate (tool_selected %)", rq.cell_toolsel),
                           (axR, "tool-verified success (%)", rq.cell_success)):
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
    axL.set_title(f"{rq.TASK_DISP[task]} — invocation rate")
    axR.set_title("…raises the tool path (mechanism layer)")
    axR.legend(loc="lower right", framealpha=0.92)
    fig.suptitle(f"{rq.TASK_DISP[task]} mechanism: steering raises tool-calling, "
                 f"which raises the tool path  ·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=rq.C_INK, y=1.02)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig — tokens per trial by arm (tokens only; no success axis)
# ----------------------------------------------------------------------------
# Two-colour categorical pair for the tool arms, validated with the dataviz
# skill's validate_palette.js on a white surface (all pairs: CVD dE 24.7,
# normal-vision dE 33.6, both >= 3:1). The no-tools arm carries no hue: it is
# the ink-coloured start tick. Marker shape repeats the arm identity.
TOK_C = {"tl-neut": "#2a78d6", "tl-ster": "#eb6834"}
TOK_MARK = {"tl-neut": "o", "tl-ster": "D"}
TOK_LANE = {"tl-neut": -0.17, "tl-ster": +0.17}   # plain above, steered below


def _mean_tokens(model: str, task: str, arm: str) -> float:
    """Mean total tokens per trial (input + output, summed over turns)."""
    st = bd.token_stats(bd.CELLS.get((model, THINK, arm), []), task)
    assert st["n"], (model, task, arm)
    return st["total"]


def fig_token_quadrant(save_name: str) -> Path:
    """Dumbbell per (model, task): the tick is the no-tools arm, and one line
    runs from it to each tool arm's marker. One panel per model, one row per
    task, one shared log axis."""
    from matplotlib.lines import Line2D
    tasks = rq.ALL_TASKS
    fig, axes = plt.subplots(1, len(rq.MODELS_9B), figsize=(8.6, 2.9), sharey=True)
    y = np.arange(len(tasks))
    for ax, m in zip(axes, rq.MODELS_9B):
        ax.set_axisbelow(True)
        for i, task in enumerate(tasks):
            x0 = _mean_tokens(m, task, "nt-neut")
            ax.vlines(x0, i - 0.32, i + 0.32, color=rq.C_INK, lw=2.0, zorder=4,
                      capstyle="round")
            for arm in ("tl-neut", "tl-ster"):
                x1, yy = _mean_tokens(m, task, arm), i + TOK_LANE[arm]
                ax.hlines(yy, x0, x1, color=rq.C_SPINE, lw=1.3, zorder=2)
                ax.scatter([x1], [yy], s=(34 if arm == "tl-neut" else 28),
                           marker=TOK_MARK[arm], color=TOK_C[arm], edgecolor="white",
                           linewidth=1.0, zorder=5)
        ax.set_xscale("log")
        ax.set_xlim(1000, 32000)
        ax.set_xticks([1000, 2000, 5000, 10000, 20000])
        ax.set_xticklabels(["1K", "2K", "5K", "10K", "20K"])
        ax.xaxis.set_minor_locator(mticker.NullLocator())
        ax.set_ylim(len(tasks) - 0.45, -0.55)
        ax.set_yticks(y)
        ax.set_yticklabels([rq.TASK_DISP[t] for t in tasks])
        ax.set_title(rq.MODEL_DISP[m], fontsize=9.5)
        ax.grid(True, which="major", axis="x")
        rq._despine(ax)
    axes[1].set_xlabel("mean total tokens per trial (log scale)")
    handles = [
        Line2D([], [], color=rq.C_INK, marker="|", markersize=10, markeredgewidth=2.0,
               linestyle="none", label="no-tools"),
        Line2D([], [], color=TOK_C["tl-neut"], marker=TOK_MARK["tl-neut"], markersize=6,
               markeredgecolor="white", linestyle="none", label="+tool (plain)"),
        Line2D([], [], color=TOK_C["tl-ster"], marker=TOK_MARK["tl-ster"], markersize=5.5,
               markeredgecolor="white", linestyle="none", label="+tool (steered)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.08), fontsize=8)
    fig.suptitle("Tokens per trial by arm (input + output, summed over turns)  ·  "
                 f"≥9B, think={THINK}, main sweep",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.03)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig — outcome of the unaided trials (per task, pooled ≥9B, run-time grade)
# ----------------------------------------------------------------------------
# No-tools arm only. The harness graded each unaided answer in full while the
# run was in progress, so every trial is correct or carries one failure_reason.
# The tool arms are not drawn: the main sweep has no delivered grade for them.
FR_TO_CAT = {
    "truncated_no_answer": "truncated", "think_overflow": "truncated",
    "format_parse_fail": "unparseable", "verdict_mismatch": "wrong content",
    "plan_invalid": "wrong content", "result_mismatch": "wrong content",
}
CAT_ORDER = ["correct", "truncated", "unparseable", "wrong content"]
CAT_COLOR = {"correct": "#6A994E", "truncated": "#9AA3AE", "unparseable": "#8E5572",
             "wrong content": "#C44E52"}
CAT_INK = {"correct": "white", "truncated": rq.C_INK, "unparseable": "white",
           "wrong content": "white"}


def _unaided_outcome_mix(task: str) -> dict:
    counts = {c: 0 for c in CAT_ORDER}
    n = 0
    for m in rq.MODELS_9B:
        for r in bd.CELLS.get((m, THINK, "nt-neut"), []):
            if r["task"] != task:
                continue
            n += 1
            if r["success"]:
                cat = "correct"
            else:
                fr = r.get("failure_reason")
                if fr not in FR_TO_CAT:
                    raise KeyError(f"unmapped failure_reason {fr!r}")
                cat = FR_TO_CAT[fr]
            counts[cat] += 1
    assert n, task
    return {c: counts[c] / n * 100 for c in CAT_ORDER} | {"n": n}


def fig_failure_taxonomy(save_name: str) -> Path:
    tasks = rq.ALL_TASKS
    mixes = [_unaided_outcome_mix(t) for t in tasks]
    fig, ax = plt.subplots(figsize=(8.6, 2.7))
    ax.set_axisbelow(True)
    y = np.arange(len(tasks))
    left = np.zeros(len(tasks))
    for cat in CAT_ORDER:
        vals = np.array([mx[cat] for mx in mixes])
        ax.barh(y, vals, 0.66, left=left, color=CAT_COLOR[cat], edgecolor="white",
                linewidth=0.8, zorder=3, label=cat)
        for yi, v, l0 in zip(y, vals, left):
            if v >= 5.0:          # print the share only where it fits the segment
                ax.text(l0 + v / 2, yi, f"{v:.0f}", ha="center", va="center",
                        fontsize=7, color=CAT_INK[cat], zorder=5)
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels([rq.TASK_DISP[t] for t in tasks])
    ax.set_ylim(len(tasks) - 0.45, -0.55)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of no-tools trials (%)")
    ax.grid(axis="x")
    rq._despine(ax)
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=len(CAT_ORDER),
               frameon=False, bbox_to_anchor=(0.5, -0.07), fontsize=8)
    fig.suptitle("Outcome of the unaided (no-tools) trials by task, graded at run time  ·  "
                 f"≥9B, think={THINK}, canonical corpus",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.03)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
def main() -> int:
    bd.CELLS = bd.load_all(rq.RESULTS_ROOT)
    print(f"loaded {sum(len(v) for v in bd.CELLS.values())} trials "
          f"from {rq.RESULTS_ROOT.relative_to(REPO)}")
    fig_funnel("funnel.pdf")
    fig_solve("solve.pdf")
    fig_simulate("simulate.pdf")
    fig_mechanism("validate_plan", "mechanism_validate_plan.pdf")
    fig_token_quadrant("token_quadrant.pdf")
    fig_failure_taxonomy("failure_taxonomy.pdf")
    # sanity prints for the paper text (verify-claims anchors)
    print("\nmean total tokens per trial (≥9B, think=off): no-tools / plain / steered")
    for m in rq.MODELS_9B:
        for t in rq.ALL_TASKS:
            a, b, c = (_mean_tokens(m, t, arm) for arm in rq.ARMS)
            print(f"  {m:16s} {t:18s} {a:7.0f} / {b:7.0f} / {c:7.0f}   "
                  f"x{b / a:.1f} plain, x{c / a:.1f} steered")
    print("\nunaided outcome mix (≥9B pooled, no-tools, run-time grade):")
    for t in rq.ALL_TASKS:
        mix = _unaided_outcome_mix(t)
        print(f"  {t:18s} n={mix['n']:5d}  "
              + ", ".join(f"{c} {mix[c]:.1f}%" for c in CAT_ORDER if mix[c] > 0))
    print("\nopen-weight sweep cells drawn in solve.pdf / simulate.pdf "
          "(unaided / tool-verified plain / tool-verified steered):")
    for t in ("solve", "simulate"):
        for m in rq.CHART_MODELS:
            print(f"  {t:9s} {m:16s} "
                  + " / ".join(f"{sweep_rate(m, t, a)['low'] * 100:5.1f}" for a in rq.ARMS))
    print("\nfrontier funnel (CALL / tool-correct / delivered low–high / NEED v11):")
    for tier, disp, corpus in TIERS:
        for t in rq.ALL_TASKS:
            wt, nt = frontier_wt(corpus, t), frontier_nt_v11(corpus, t)
            c, n = frontier_call(corpus, t)
            print(f"  {tier:6s} {t:17s} {c/n*100:5.1f} / {wt['tv_ok']/wt['tv_n']*100:5.1f} / "
                  f"{wt['low']*100:5.1f}–{wt['high']*100:5.1f} / {nt['low']*100:5.1f}–{nt['high']*100:5.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
