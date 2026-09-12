"""Regenerate the paper's Results figures as vector PDFs — DELIVERED surface.

D-J2 batch 2 (2026-09-08, development/job2_delivered_reframe_worknote.md §7b):
every success-type figure now draws the DELIVERED rate (`e2e_strict`, the
paper's single primary surface) read through the analyzer's shared overlay
aggregator (`e2e_overlay.load_e2e_cells` over results/derived/e2e_overlay/),
so no figure can drift from the pooled table. Tool-verified stays visible
only as the labeled mechanism layer (faint ticks; Fig. mechanism).

Value shapes follow the paper's how-to-read table: an exact cell draws a
solid bar with a Wilson 95% whisker; a censoring bound <low, high> draws a
solid bar to `low` with a hatched extension to `high` — never a point.

Outputs (vector PDF, into this directory):
  funnel.pdf                         — Fig 1, within-arm cascade per tier
                                        (CALL -> tool-correct -> delivered;
                                        NEED = no-tools reference line);
                                        open-roster validate_* panels;
                                        PlanBench panel with the FORMALIZE bar
  solve.pdf, simulate.pdf            — success by arm on the delivered surface
  mechanism_validate_plan.pdf        — unchanged (mechanism layer, exact)
  token_quadrant.pdf                 — tokens vs DELIVERED success
  failure_taxonomy.pdf               — delivered-surface outcome composition

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


def _savepdf(fig, name: str) -> Path:
    p = OUT / name
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {p.relative_to(REPO)}")
    return p


# ----------------------------------------------------------------------------
# Delivered data layer (overlay = the only source of e2e verdicts)
# ----------------------------------------------------------------------------
_E2E: dict[str, dict] = {}


def e2e_cells(corpus: str) -> dict:
    if corpus not in _E2E:
        _E2E[corpus] = load_e2e_cells(corpus, OVERLAY)
    return _E2E[corpus]


def deliv(model: str, task: str, arm: str, *, corpus: str = "sweep5v2-live",
          think: str = THINK, run_tag: str = "") -> dict | None:
    cond = "no-tools" if arm == "nt-neut" else "tools_all_minimal"
    return e2e_cells(corpus).get((model, think, cond, run_tag, arm, task))


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


def overlay_rows(model: str, cond: str, corpus: str = "sweep5v2-live",
                 think: str = THINK) -> list[dict]:
    p = OVERLAY / corpus / f"slurm_vllm_{model}_{think}_{cond}.e2e.jsonl"
    return [json.loads(ln) for ln in p.open()]


# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def bar_cell(ax, x, cell: dict | None, w: float, color: str, *, label=None,
             zorder=3, show_ci=True):
    """Delivered bar for one cell: solid to `low`; hatched `low..high` when the
    cell is a censoring bound; Wilson whisker when exact. Returns the bar."""
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
    """NEED = the no-tools delivered reference, a line (exact) or a translucent
    band (bound). Never a bar: arms are never pooled."""
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
                   colors, ymax=108, legend=False):
    """groups: list of per-group dicts {stage_name: cell_or_rate}; stages: the
    ordered stage keys; need: per-group cell for the reference line."""
    ax.set_axisbelow(True)
    k = len(stages)
    w = 0.8 / k
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
        need_line(ax, x[gi] - 0.45, x[gi] + 0.45, need[gi],
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
    # Row 2: open roster validate_* (plain arm, canonical, think=off)
    vtasks = ["validate_domain", "validate_problem", "validate_plan"]
    for ax, m in zip(axes[1], rq.MODELS_9B):
        groups, need = [], []
        for t in vtasks:
            d = deliv(m, t, "tl-neut")
            groups.append({"call": rq.cell_toolsel(m, t, "tl-neut").rate,
                           "tv": d["tv_ok"] / d["tv_n"], "deliv": d})
            need.append(deliv(m, t, "nt-neut"))
        _cascade_panel(ax, groups, ["call", "tv", "deliv"], need,
                       title=f"{rq.MODEL_DISP[m]} · with-tools (plain), canonical, think=off",
                       xlabels=[TASK_SHORT[t] for t in vtasks],
                       stage_labels=["tool called (CALL)", "tool result correct",
                                     "delivered correct"],
                       colors=[C_CALL, C_TV, C_DELIV])
    axes[0][0].set_ylabel("share of with-tools trials (%)")
    axes[1][0].set_ylabel("share of with-tools trials (%)")
    fig.suptitle("The funnel: of every with-tools trial, how many call the tool, get a "
                 "correct tool result, and deliver a correct answer  ·  dashed = no-tools "
                 "delivered (NEED); hatched = censoring bound",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.01)
    fig.legend(handles, labels, loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.5, -0.045), fontsize=8)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig — success by arm on the delivered surface (solve / simulate)
# ----------------------------------------------------------------------------
def _roster_panel(ax, task: str, *, corpus: str, run_tag: str, think: str,
                  models: list[str], arms: list[str], title: str, tv_ticks=True,
                  legend=True):
    ax.set_axisbelow(True)
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
            cell = deliv(m, task, arm, corpus=corpus, think=think, run_tag=run_tag)
            bar_cell(ax, cx, cell, w * 0.95, rq.ARM_COLOR[arm],
                     label=(rq.ARM_DISP[arm] if j == 0 else None))
            _label_top(ax, cx, cell, ymax=YMAX)
            if tv_ticks and cell and cell.get("tv_n") and arm != "nt-neut":
                tv_tick(ax, cx, w * 0.95, cell["tv_ok"] / cell["tv_n"] * 100)
    ax.set_xticks(x)
    ax.set_xticklabels([rq.MODEL_DISP[m] for m in models], rotation=12)
    ax.set_title(title, fontsize=9.5)
    ax.grid(axis="y")
    rq._despine(ax)
    if legend:
        ax.legend(loc="upper left", fontsize=7, framealpha=0.92)


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
    ax.grid(axis="y")
    rq._despine(ax)
    ax.legend(loc="upper left", fontsize=7, framealpha=0.92)


def fig_solve(save_name: str) -> Path:
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 4.2),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    _roster_panel(axL, "solve", corpus="sweep5v2-live", run_tag="", think=THINK,
                  models=rq.CHART_MODELS, arms=rq.ARMS,
                  title=f"open-weight roster · canonical corpus · think={THINK}")
    _frontier_panel(axR, "solve", title="frontier tiers · canonical · prompt v11")
    axL.set_ylabel("delivered success (%)")
    fig.suptitle("solve — delivered success by arm  ·  hatched = censoring bound; "
                 "dotted tick = tool-verified (mechanism layer)",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.02)
    fig.tight_layout()
    return _savepdf(fig, save_name)


def fig_simulate(save_name: str) -> Path:
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 4.2),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    # Canonical open-roster simulate is censored on both arms (vacuous bounds),
    # so the open-roster delivered picture is the independent full-storage
    # rerun (iss024d, think=on, parser off) — a separate apparatus, labeled.
    _roster_panel(axL, "simulate", corpus="iss024d-e2e-live", run_tag="iss024d-e2e",
                  think="on", models=rq.CHART_MODELS, arms=["tl-neut", "tl-ster"],
                  title="open-weight roster · independent full-storage rerun "
                        "(think=on, separate apparatus)")
    _frontier_panel(axR, "simulate", title="frontier tiers · canonical · prompt v11")
    axL.set_ylabel("delivered success (%)")
    fig.suptitle("simulate — delivered success by arm  ·  hatched = censoring bound; "
                 "dotted tick = tool-verified (mechanism layer)",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.02)
    fig.tight_layout()
    return _savepdf(fig, save_name)


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
    for ax, metric, fn in ((axL, "tool-use rate (tool_selected %)", rq.cell_toolsel),
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
    axL.set_title(f"{rq.TASK_DISP[task]} — tool-use rate")
    axR.set_title("…raises the tool path (mechanism layer)")
    axR.legend(loc="lower right", framealpha=0.92)
    fig.suptitle(f"{rq.TASK_DISP[task]} mechanism: steering raises tool-calling, "
                 f"which raises the tool path  ·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=rq.C_INK, y=1.02)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig — token quadrant on the delivered surface
# ----------------------------------------------------------------------------
def _pooled_deliv(task: str, arm: str) -> dict:
    """Pooled (≥9B) delivered aggregate: n, ok, cens, low, high."""
    n = ok = cens = 0
    for m in rq.MODELS_9B:
        c = deliv(m, task, arm)
        if c:
            n += c["n"]; ok += c["ok"]; cens += c["cens"]
    return {"n": n, "ok": ok, "cens": cens, "low": ok / n if n else 0.0,
            "high": (ok + cens) / n if n else 0.0}


def _pooled_tokens(task: str, arm: str) -> int:
    rows = [r for r in rq._pooled_rows(rq.MODELS_9B, arm)
            if r["task"] == task and r.get("tokens")]
    return sum(int(r["tokens"].get("prompt", 0) or 0)
               + int(r["tokens"].get("completion", 0) or 0) for r in rows)


def _cop_range(task: str, arm: str) -> tuple[float, float]:
    """Delivered cost-of-pass as a range: Σtokens ÷ (ok+cens) .. Σtokens ÷ ok."""
    d, tok = _pooled_deliv(task, arm), _pooled_tokens(task, arm)
    lo = tok / (d["ok"] + d["cens"]) if d["ok"] + d["cens"] else float("inf")
    hi = tok / d["ok"] if d["ok"] else float("inf")
    return lo, hi


def fig_token_quadrant(save_name: str) -> Path:
    fig, axes = plt.subplots(1, len(rq.ALL_TASKS), figsize=(13.2, 3.6), sharey=True)
    for ax, task in zip(axes, rq.ALL_TASKS):
        ax.set_axisbelow(True)
        for m in rq.MODELS_9B:
            st0 = bd.token_stats(bd.CELLS.get((m, THINK, "nt-neut"), []), task)
            st1 = bd.token_stats(bd.CELLS.get((m, THINK, "tl-ster"), []), task)
            c0, c1 = deliv(m, task, "nt-neut"), deliv(m, task, "tl-ster")
            if not (st0["n"] and st1["n"] and c0 and c1):
                continue
            x0, y0, y0h = st0["total"], c0["low"] * 100, c0["high"] * 100
            x1, y1, y1h = st1["total"], c1["low"] * 100, c1["high"] * 100
            col = rq.MODEL_COLOR[m]
            ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=3,
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6,
                                        shrinkA=4, shrinkB=4, alpha=0.9))
            for xx, yy, yh in ((x0, y0, y0h), (x1, y1, y1h)):
                if yh > yy + 1e-9:   # censoring bound: vertical hatched range
                    ax.vlines(xx, yy, yh, color=col, lw=3.5, alpha=0.25, zorder=2)
            ax.scatter([x0], [y0], s=26, color="white", edgecolor=col,
                       linewidth=1.4, zorder=4)
            ax.scatter([x1], [y1], s=30, color=col, edgecolor="white",
                       linewidth=0.8, zorder=4,
                       label=rq.MODEL_DISP[m] if task == rq.ALL_TASKS[0] else None)
        nt_lo, nt_hi = _cop_range(task, "nt-neut")
        tl_lo, tl_hi = _cop_range(task, "tl-ster")
        if nt_hi == float("inf") or tl_hi == float("inf"):
            label, col = "cost-of-pass: censored on canonical", rq.C_SOFT
        else:
            m_lo, m_hi = tl_lo / nt_hi, tl_hi / nt_lo
            col = "#2E7D32" if m_hi < 1 else rq.C_SOFT
            label = (f"cost-of-pass {m_lo:.1f}×" if abs(m_hi - m_lo) < 0.05
                     else f"cost-of-pass {m_lo:.1f}–{m_hi:.1f}×")
        ax.text(0.5, 0.045, label, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=7.5, fontweight="bold", color=col,
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=rq.C_RULE,
                          lw=0.7, alpha=0.92), zorder=6)
        ax.set_xscale("log")
        ax.set_xlim(500, 60000)
        ax.set_ylim(-4, 106)
        ax.set_title(rq.TASK_DISP[task], fontsize=9.5)
        ax.set_xlabel("tokens/trial (log)", fontsize=8)
        ax.xaxis.set_major_locator(mticker.LogLocator(base=10, numticks=6))
        ax.xaxis.set_major_formatter(mticker.LogFormatterMathtext(base=10))
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())
        ax.grid(True, which="major", axis="both")
        rq._despine(ax)
    axes[0].set_ylabel("delivered success (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.09), fontsize=8)
    fig.suptitle("What the tokens buy — total tokens/trial vs DELIVERED success, "
                 f"arrows run no-tools (open) to +tool steered (filled)  ·  ≥9B, think={THINK}; "
                 "translucent bars = censoring bound",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.05)
    fig.tight_layout()
    return _savepdf(fig, save_name)


# ----------------------------------------------------------------------------
# Fig — failure taxonomy on the delivered surface (per task × arm, pooled ≥9B)
# ----------------------------------------------------------------------------
# Delivered outcome categories. Tool-arm rows come from the overlay e2e_reason;
# no-tools rows on the canonical corpus keep their online (already delivered)
# grade, whose failure_reason is read from the raw trial.
E2E_TO_CAT = {
    "verdict_stated_ok": "delivered ok", "plan_valid": "delivered ok",
    "trajectory_ok": "delivered ok",
    "censored_at_snapshot_cap": "censored (bound)",
    "truncated_empty": "truncated",
    "delegation_terminal_credit": "tool call, no answer",
    "empty_stop_not_tool_verified": "tool call, no answer",
    "empty_response": "unparseable",
    "format_parse_fail": "unparseable", "no_plan_extracted": "unparseable",
    "no_verdict_stated": "unparseable",
    "verdict_stated_wrong": "wrong content", "plan_invalid": "wrong content",
    "trajectory_mismatch": "wrong content",
    "no_ground_truth": "censored (bound)",
    "plan_validation_transport_error": "censored (bound)",
}
FR_TO_CAT = {
    "truncated_no_answer": "truncated", "think_overflow": "truncated",
    "format_parse_fail": "unparseable", "verdict_mismatch": "wrong content",
    "plan_invalid": "wrong content", "result_mismatch": "wrong content",
}
CAT_ORDER = ["delivered ok", "censored (bound)", "truncated", "tool call, no answer",
             "unparseable", "wrong content"]
CAT_COLOR = {
    "delivered ok": "#6A994E", "censored (bound)": "#D9DEE5", "truncated": "#9AA3AE",
    "tool call, no answer": "#E07B39", "unparseable": "#8E5572", "wrong content": "#C44E52",
}


def _raw_index(model: str, cond: str) -> dict:
    """Raw trials of one (model, think=off, cond) keyed by trial identity, for
    the no-tools rows whose overlay reason is `stored_online_grade`."""
    arms = ["nt-neut"] if cond == "no-tools" else ["tl-neut", "tl-ster"]
    idx = {}
    for arm in arms:
        for r in bd.CELLS.get((model, THINK, arm), []):
            idx[(r["task"], r["domain_name"], r["problem_name"],
                 r.get("plan_label") or "", r["prompt_variant"])] = r
    return idx


def _cell_failure_mix(task: str, arm: str) -> dict:
    counts = {c: 0 for c in CAT_ORDER}
    n = 0
    for m in rq.MODELS_9B:
        cond = "no-tools" if arm == "nt-neut" else "tools_all_minimal"
        raw = _raw_index(m, cond)
        for r in overlay_rows(m, cond):
            if r["task"] != task:
                continue
            pv = r["prompt_variant"]
            if arm == "tl-neut" and pv >= 14 or arm == "tl-ster" and pv <= 13:
                continue
            n += 1
            reason = r["e2e_reason"]
            if reason == "stored_online_grade":
                if r["e2e_strict"] is True:
                    cat = "delivered ok"
                else:
                    fr = raw.get((task, r["domain_name"], r["problem_name"],
                                  r.get("plan_label") or "", pv), {}).get("failure_reason")
                    cat = FR_TO_CAT.get(fr, "wrong content")
            else:
                cat = E2E_TO_CAT.get(reason)
                if cat is None:
                    raise KeyError(f"unmapped e2e_reason {reason!r}")
            counts[cat] += 1
    return {c: (counts[c] / n * 100 if n else 0.0) for c in CAT_ORDER} | {"n": n}


def fig_failure_taxonomy(save_name: str) -> Path:
    arms = rq.ARMS
    # legend shows only categories with mass somewhere in this figure
    all_mixes = [_cell_failure_mix(t, a) for t in rq.ALL_TASKS for a in arms]
    present = {c for c in CAT_ORDER if any(mx[c] > 0 for mx in all_mixes)}
    fig, axes = plt.subplots(1, len(rq.ALL_TASKS), figsize=(13.2, 3.7), sharey=True)
    for ax, task in zip(axes, rq.ALL_TASKS):
        ax.set_axisbelow(True)
        x = np.arange(len(arms))
        bottoms = np.zeros(len(arms))
        mixes = [_cell_failure_mix(task, a) for a in arms]
        for cat in CAT_ORDER:
            vals = np.array([mx[cat] for mx in mixes])
            ax.bar(x, vals, 0.74, bottom=bottoms, color=CAT_COLOR[cat],
                   edgecolor="white", linewidth=0.5, zorder=3,
                   hatch=(HATCH if cat == "censored (bound)" else None),
                   label=cat if (task == rq.ALL_TASKS[0] and cat in present) else None)
            bottoms += vals
        ax.set_xticks(x)
        ax.set_xticklabels(["no-tools", "+plain", "+steered"], rotation=18, fontsize=7.5)
        ax.set_ylim(0, 100)
        ax.set_title(rq.TASK_DISP[task], fontsize=9.5)
        ax.grid(axis="y")
        rq._despine(ax)
    axes[0].set_ylabel("share of trials (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(present), frameon=False,
               bbox_to_anchor=(0.5, -0.06), fontsize=8)
    fig.suptitle("How answers fail on the delivered surface — per-trial outcome composition "
                 f"by task and arm  ·  ≥9B, think={THINK}, canonical corpus",
                 fontsize=10.5, fontweight="bold", color=rq.C_INK, y=1.04)
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
    print("\ndelivered cost-of-pass multipliers (tl-ster ÷ nt-neut, pooled ≥9B, range):")
    for t in rq.ALL_TASKS:
        nt_lo, nt_hi = _cop_range(t, "nt-neut"); tl_lo, tl_hi = _cop_range(t, "tl-ster")
        if nt_hi == float("inf") or tl_hi == float("inf"):
            print(f"  {t:18s} censored on canonical")
        else:
            print(f"  {t:18s} {tl_lo/nt_hi:.2f}–{tl_hi/nt_lo:.2f}×")
    print("\ndelivered failure mix (≥9B, no-tools):")
    for t in rq.ALL_TASKS:
        mix = _cell_failure_mix(t, "nt-neut")
        print(f"  {t:18s} " + ", ".join(f"{c} {mix[c]:.1f}%" for c in CAT_ORDER if mix[c] > 0.5))
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
