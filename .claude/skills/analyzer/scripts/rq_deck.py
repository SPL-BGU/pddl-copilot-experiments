"""Paper-ready single-tool-use RQ analysis + slideshow for sweep5v2.

Regenerates every RQ figure from `results/sweep5v2-live/` and emits a
Question→Answer→Evidence PPTX answering RQ0.1–0.6. Read-only over `results/`.
Reuses the metric layer in `build_deck.py` (load_all / task_success_rate /
tool_selected_rate / confusion / metrics_from_cm) and its python-pptx helpers,
plus `wilson_ci` — never recomputes success from aggregate.py/table.py.

RQ map (single-tool-use track, ≥9B headline, think=off):
  RQ0.1  validate_domain + validate_problem  — does the tool help validation?
  RQ0.2  solve                               — does the tool help planning?
  RQ0.3  validate_plan                        — does the tool help plan-checking?
  RQ0.4  simulate                             — does the tool help state-tracking?
  RQ0.5  difficulty × plan length (ref_len / plan_len) — does the advantage CHANGE?
  RQ0.6  difficulty × object count (obj_count)          — does the advantage CHANGE?

Three arms, never pooled (locked design):
  nt-neut  = no-tools                (neutral prompt, no tools)
  tl-neut  = +tool (plain)           (neutral prompt, tools available)
  tl-ster  = +tool (steered)         (steered prompt, tools available)
Two gaps per RQ0.1–0.4: availability (tl-neut − nt-neut, byte-identical wording)
and steering (tl-ster − tl-neut). Phase-2 (RQ0.5/0.6) compares nt-neut vs tl-ster.

Usage:
    python3 .claude/skills/analyzer/scripts/rq_deck.py            # full deck
    python3 .claude/skills/analyzer/scripts/rq_deck.py --check    # gates+asserts only, no render
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import build_deck as bd  # noqa: E402  metric layer + python-pptx helpers
from _constants import iter_trials, wilson_ci  # noqa: E402

# ---------------- Configuration ----------------

RESULTS_ROOT = REPO / "results/sweep5v2-live"
META_PATH = HERE.parent / "data/meta_sweep5v2.json"  # .claude/skills/analyzer/data/
OUT_DIR = REPO / "checkpoints/rq-sweep5v2"
PLOT_DIR = OUT_DIR / "plots"
PHASE2_JSON = OUT_DIR / "phase2_summary.json"            # regenerated output (gitignored)
# Frozen, TRACKED regression oracle — byte-identical to the original scratch
# phase2_summary.json. The recomputation asserts against THIS (not the output
# it just wrote), so the guard survives a clean checkout and is not a tautology.
PHASE2_EXPECTED = HERE.parent / "data/phase2_expected_sweep5v2.json"
PPTX_OUT = OUT_DIR / "pddl_copilot_rq_sweep5v2.pptx"

MODEL_ORDER = ["Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B",
               "gemma4_26b-a4b", "qwen3_6_35b"]
MODEL_DISP = {
    "Qwen3_5_0_8B": "Qwen3.5-0.8B",
    "Qwen3_5_4B": "Qwen3.5-4B",
    "Qwen3_5_9B": "Qwen3.5-9B",
    "gemma4_26b-a4b": "Gemma-MoE-26B",
    "qwen3_6_35b": "Qwen3.6-35B",
}
MODELS_9B = ["Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"]  # ≥9B headline set

ARMS = ["nt-neut", "tl-neut", "tl-ster"]
ARM_DISP = {"nt-neut": "no-tools", "tl-neut": "+tool (plain)",
            "tl-ster": "+tool (steered)"}
ARM_COLOR = {"nt-neut": "#888888", "tl-neut": "#2E86AB", "tl-ster": "#E07B39"}

# RQ0.1–0.4 → phase-1 task(s)
RQ_TASKS = {
    "RQ0.1": ["validate_domain", "validate_problem"],
    "RQ0.2": ["solve"],
    "RQ0.3": ["validate_plan"],
    "RQ0.4": ["simulate"],
}
# Locked scorecard verdicts the deck must defend (asserted against computed counts).
RQ_VERDICT = {"RQ0.1": "YES", "RQ0.2": "YES", "RQ0.3": "MIXED", "RQ0.4": "YES"}
TASK_DISP = {"solve": "solve", "validate_domain": "validate_domain",
             "validate_problem": "validate_problem",
             "validate_plan": "validate_plan", "simulate": "simulate"}

VALID_PLAN_LABELS = {"v1", "v2", "v3", "v4", "v5"}
THINK = "off"

# ---------------- Shared visual theme (figures + slides) ----------------
# Palette — the figure colours double as slide-accent colours so the chrome
# and the charts read as one design system.
C_INK    = "#1B2430"   # near-black navy — titles, body text
C_SOFT   = "#5A6473"   # secondary text / captions
C_BRAND  = "#2E86AB"   # +tool(plain) blue — primary accent
C_ACCENT = "#E07B39"   # +tool(steered) orange — secondary accent
C_GREY   = "#888888"   # no-tools grey (matches ARM_COLOR)
C_RULE   = "#D9DEE5"   # hairlines
C_GRID   = "#E7EAEF"   # gridlines
C_SPINE  = "#BBC1CA"   # axis spines

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlepad": 9,
    "axes.labelsize": 9,
    "axes.labelcolor": C_INK,
    "axes.edgecolor": C_SPINE,
    "axes.linewidth": 0.9,
    "text.color": C_INK,
    "xtick.color": C_INK,
    "ytick.color": C_INK,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "grid.color": C_GRID,
    "grid.linewidth": 0.9,
    "legend.fontsize": 8,
    "legend.framealpha": 0.92,
    "legend.edgecolor": C_RULE,
    "legend.fancybox": False,
})


def _despine(ax) -> None:
    """Drop the top/right spines and soften the rest — clean academic look."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(C_SPINE)
    ax.tick_params(length=0)


def _bar_value_labels(ax, bars, vals, ymax=None, fmt="{:.0f}") -> None:
    """Label bars without the above-bar crowding that merges near-equal
    neighbours (e.g. 99/100). Tall bars get a white label tucked inside the
    top; short bars get a haloed label above so they stay legible over grid."""
    ymax = ymax or ax.get_ylim()[1]
    thresh = 0.16 * ymax
    for b, v in zip(bars, vals):
        if v != v:  # nan
            continue
        cx = b.get_x() + b.get_width() / 2
        if v >= thresh:
            ax.text(cx, v - 0.022 * ymax, fmt.format(v), ha="center", va="top",
                    fontsize=7, fontweight="bold", color="white", zorder=5)
        else:
            ax.text(cx, v + 0.015 * ymax, fmt.format(v), ha="center", va="bottom",
                    fontsize=7, color=C_INK, zorder=5,
                    bbox=dict(boxstyle="round,pad=0.08", fc="white",
                              ec="none", alpha=0.72))


# ---------------- Metric layer (reuses build_deck) ----------------

@dataclass
class Cell:
    rate: float
    lo: float
    hi: float
    s: int
    n: int


def cell_success(model: str, task: str, arm: str, think: str = THINK) -> Cell:
    rows = bd.CELLS.get((model, think, arm), [])
    rate, s, n = bd.task_success_rate(rows, task)
    lo, hi = wilson_ci(s, n)
    return Cell(rate, lo, hi, s, n)


def cell_toolsel(model: str, task: str, arm: str, think: str = THINK) -> Cell:
    rows = bd.CELLS.get((model, think, arm), [])
    rate, s, n = bd.tool_selected_rate(rows, task)
    lo, hi = wilson_ci(s, n)
    return Cell(rate, lo, hi, s, n)


def signed_gap(model: str, task: str, lo_arm: str, hi_arm: str) -> dict:
    """gap = succ(hi_arm) − succ(lo_arm), with signed significance.

    `significant` = the two arms' Wilson 95% intervals are disjoint.
    `favorable`   = gap > 0 (the hypothesised direction: tool/steering helps).
    A sign-blind disjointness test would mis-read RQ0.3 (validate_plan), where
    Gemma's availability gap is large, significant, and AGAINST the tool.
    """
    a = cell_success(model, task, lo_arm)
    b = cell_success(model, task, hi_arm)
    gap = (b.rate - a.rate) * 100 if (a.n and b.n) else float("nan")
    disjoint = (a.n and b.n) and (a.hi < b.lo or b.hi < a.lo)
    return dict(gap=gap, significant=bool(disjoint), favorable=gap > 0,
                lo=a, hi=b)


def claim_counts(task: str, lo_arm: str, hi_arm: str,
                 models: list[str]) -> dict:
    """Signed k/N tally over `models` for one claim (availability or steering)."""
    fav = ag = 0
    gaps = []
    for m in models:
        g = signed_gap(m, task, lo_arm, hi_arm)
        if g["lo"].n and g["hi"].n:
            gaps.append(g["gap"])
        if g["significant"]:
            if g["favorable"]:
                fav += 1
            else:
                ag += 1
    finite = [x for x in gaps if x == x]
    return dict(fav_sig=fav, against_sig=ag, n=len(models),
                gap_min=min(finite) if finite else float("nan"),
                gap_max=max(finite) if finite else float("nan"),
                gap_med=float(np.median(finite)) if finite else float("nan"))


def derive_verdict(avail: dict) -> str:
    """Verdict rule on the ≥9B availability claim (Claim A)."""
    if avail["fav_sig"] >= 1 and avail["against_sig"] >= 1:
        return "MIXED"
    if avail["against_sig"] == 0 and avail["fav_sig"] >= 2:
        return "YES"
    if avail["fav_sig"] == 0 and avail["against_sig"] >= 1:
        return "NO"
    return "INCONCLUSIVE"


# ---------------- Gate (relabel + RQ0.3 mechanism) ----------------

def run_gate() -> list[str]:
    """Verify (a) the FastMCP relabel is INERT on this corpus and (b) the
    validate_plan +tool(plain) low raw-success is a TOOL-CALLING artifact
    (acc_decided≈99, fp≈0, huge no_ans), not a verdict collapse. Returns the
    human-readable gate report lines; raises on violation."""
    lines = []
    for model in ("gemma4_26b-a4b", "Qwen3_5_0_8B"):
        cond = "tools_all_minimal"
        cell = RESULTS_ROOT / f"slurm_vllm_{model}_off_{cond}"
        cms = {}
        for relabel in (False, True):
            rows = [r for r in iter_trials(cell, relabel=relabel, think_mode="off")
                    if r.get("task") == "validate_plan"
                    and int(r.get("prompt_variant", -1)) in (11, 12, 13)]
            cms[relabel] = bd.confusion(rows, "validate_plan")
        cm = cms[True]
        m = bd.metrics_from_cm(cm)
        # (a) relabel inert on sweep5v2-live (corpus generated post check_success fix)
        assert cms[False] == cms[True], \
            f"relabel changed the confusion matrix for {model} — gate premise broken"
        # (b) plain-arm failures are no_ans (tool-calling), not verdict errors
        acc = m["accuracy_decided"]
        raw = cell_success(model, "validate_plan", "tl-neut")
        decided = cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"]
        lines.append(
            f"{MODEL_DISP[model]:16s} val_plan +tool(plain): raw_success={raw.rate*100:4.1f}%  "
            f"acc_decided={acc*100:4.1f}%  fp={cm['fp']}  no_ans={cm['no_ans']}  "
            f"(relabel inert: {cms[False] == cms[True]})")
        assert acc > 0.65, f"acc_decided unexpectedly low for {model}"
    return lines


# ---------------- Phase-2 (RQ0.5 / RQ0.6) ----------------

_META = None


def meta() -> dict:
    global _META
    if _META is None:
        _META = json.loads(META_PATH.read_text())["instances"]
    return _META


def _binvar(r: dict, rq: str):
    m = meta().get(f"{r.get('domain_name')}/{r.get('problem_name')}")
    if not m:
        return None
    if rq == "rq06":
        return m.get("obj_count")
    if r["task"] in ("solve", "simulate"):
        return m.get("ref_len")
    return m.get("plan_len", {}).get(r.get("plan_label"))  # validate_plan


def _phase2_rows(rq: str, task: str):
    rows = []
    for mo in MODELS_9B:
        for arm in ("nt-neut", "tl-ster"):
            for r in bd.CELLS.get((mo, THINK, arm), []):
                if r["task"] != task:
                    continue
                if task == "validate_plan" and r.get("plan_label") not in VALID_PLAN_LABELS:
                    continue  # difficulty = length of a CORRECT plan only
                v = _binvar(r, rq)
                if v is not None:
                    rows.append((v, bool(r["success"]), arm))
    return rows


def phase2_one(rq: str, task: str) -> dict:
    rows = _phase2_rows(rq, task)
    vals = np.array([x[0] for x in rows])
    c1, c2 = (float(x) for x in np.floor(np.quantile(vals, [1 / 3, 2 / 3])))
    labels = [f"≤{int(c1)}", f"{int(c1)}–{int(c2)}", f">{int(c2)}"]

    def bi(v):
        return 0 if v <= c1 else (1 if v <= c2 else 2)

    out = {"cuts": [c1, c2], "labels": labels, "nt": [], "tl": []}
    for arm, k in (("nt-neut", "nt"), ("tl-ster", "tl")):
        for b in range(3):
            sub = [s for v, s, a in rows if a == arm and bi(v) == b]
            n = len(sub)
            s = sum(sub)
            lo, hi = wilson_ci(s, n)
            out[k].append([100 * s / n if n else float("nan"),
                           100 * lo, 100 * hi, n])
    out["gaps"] = [out["tl"][b][0] - out["nt"][b][0] for b in range(3)]
    return out


def build_phase2() -> dict:
    summary = {}
    for rq, tasks in (("rq05", ["solve", "validate_plan", "simulate"]),
                      ("rq06", ["solve", "validate_plan", "validate_problem", "simulate"])):
        for task in tasks:
            summary[f"{rq}/{task}"] = phase2_one(rq, task)
    return summary


def assert_phase2_matches(summary: dict, oracle_path: Path) -> bool:
    """Hard-assert byte-equivalent reproduction of a prior phase2 oracle, if present."""
    if not oracle_path.exists():
        return False
    oracle = json.loads(oracle_path.read_text())
    if set(oracle) != set(summary):
        raise AssertionError(f"phase2 key mismatch: {set(oracle) ^ set(summary)}")
    for key, o in oracle.items():
        m = summary[key]
        if m["cuts"] != o["cuts"]:
            raise AssertionError(f"{key}: cuts {m['cuts']} != oracle {o['cuts']}")
        for arm in ("nt", "tl"):
            for b in range(3):
                for j in range(4):
                    a, e = m[arm][b][j], o[arm][b][j]
                    if abs(a - e) > 1e-6:
                        raise AssertionError(f"{key}/{arm}[{b}][{j}]: {a} != {e}")
    return True


# ---------------- Figures ----------------

def _save(fig, name: str) -> Path:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    p = PLOT_DIR / name
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_success_by_arm(task: str, save_name: str) -> Path:
    """Per-task raw success across 5 models × 3 arms, Wilson 95% whiskers."""
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.set_axisbelow(True)
    x = np.arange(len(MODEL_ORDER))
    w = 0.26
    ax.set_ylim(0, 122)
    # gentle band behind the ≥9B headline set (right of Qwen3.5-4B)
    ax.axvspan(1.5, len(MODEL_ORDER) - 0.5, color=C_BRAND, alpha=0.05, zorder=0)
    ax.axvline(1.5, ls=(0, (4, 3)), lw=0.9, color=C_SPINE, zorder=1)
    for i, arm in enumerate(ARMS):
        rates, errs = [], [[], []]
        for m in MODEL_ORDER:
            c = cell_success(m, task, arm)
            r = c.rate * 100 if c.n else np.nan
            rates.append(r)
            errs[0].append(max(0.0, (c.rate - c.lo) * 100) if c.n else 0)
            errs[1].append(max(0.0, (c.hi - c.rate) * 100) if c.n else 0)
        bars = ax.bar(x + (i - 1) * w, rates, w, label=ARM_DISP[arm],
                      color=ARM_COLOR[arm], yerr=errs, capsize=2,
                      edgecolor="white", linewidth=0.5, zorder=3,
                      error_kw=dict(lw=0.8, ecolor="#555"))
        _bar_value_labels(ax, bars, rates)
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_DISP[m] for m in MODEL_ORDER], rotation=12)
    ax.set_ylabel("success rate (%)")
    ax.set_title(f"{TASK_DISP[task]} — success by arm  ·  think=off")
    ax.text(len(MODEL_ORDER) - 0.5, 119, "≥9B headline", ha="right", va="top",
            fontsize=7, style="italic", color=C_SOFT)
    ax.legend(loc="upper center", ncol=3, framealpha=0.92)
    ax.grid(axis="y")
    _despine(ax)
    return _save(fig, save_name)


def fig_mechanism(task: str, save_name: str) -> Path:
    """Mechanism: tool-use rate (tool_selected) plain vs steered beside success,
    ≥9B. Shows steering lifts success by getting the model to CALL the tool."""
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.4, 4.0))
    x = np.arange(len(MODELS_9B))
    w = 0.38
    for ax, metric, fn in ((axL, "tool-use rate (tool_selected %)", cell_toolsel),
                           (axR, "success rate (%)", cell_success)):
        ax.set_axisbelow(True)
        ax.set_ylim(0, 112)
        for i, arm in enumerate(("tl-neut", "tl-ster")):
            vals = [getattr(fn(m, task, arm), "rate") * 100 if fn(m, task, arm).n
                    else np.nan for m in MODELS_9B]
            bars = ax.bar(x + (i - 0.5) * w, vals, w, color=ARM_COLOR[arm],
                          label=ARM_DISP[arm], edgecolor="white", linewidth=0.5,
                          zorder=3)
            _bar_value_labels(ax, bars, vals)
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_DISP[m] for m in MODELS_9B], rotation=12)
        ax.set_ylabel(metric)
        ax.grid(axis="y")
        _despine(ax)
    axL.set_title(f"{TASK_DISP[task]} — tool-use rate")
    axR.set_title("…raises success")
    axR.legend(loc="lower right")
    fig.suptitle(f"{TASK_DISP[task]} mechanism: steering raises tool-calling, "
                 f"which raises success  ·  ≥9B, think=off",
                 fontsize=11, fontweight="bold", color=C_INK, y=1.02)
    fig.tight_layout()
    return _save(fig, save_name)


def fig_think_on_cliff(save_name: str) -> Path:
    """think=on decode-budget cliff: small models' tool-use collapses under
    neutral think=on (over-reasoning eats the budget before the tool call) and
    is partly restored by steering — a BUDGET effect, not an ability one.
    Truncation rate annotated. Headline task = solve."""
    task = "solve"
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.6, 4.0))
    C_RED = "#B0413E"
    states = [("off", "tl-neut", "off / plain", C_BRAND),
              ("on", "tl-neut", "on / plain", C_RED),
              ("on", "tl-ster", "on / steered", C_ACCENT)]
    x = np.arange(len(MODEL_ORDER))
    w = 0.26
    axL.set_axisbelow(True)
    axL.set_ylim(0, 112)
    # left: tool-use rate across the 3 budget states
    for i, (think, arm, lab, col) in enumerate(states):
        vals = []
        for m in MODEL_ORDER:
            rows = bd.CELLS.get((m, think, arm), [])
            rate, s, n = bd.tool_selected_rate(rows, task)
            vals.append(rate * 100 if n else np.nan)
        bars = axL.bar(x + (i - 1) * w, vals, w, color=col, label=lab,
                       edgecolor="white", linewidth=0.5, zorder=3)
        _bar_value_labels(axL, bars, vals)
    axL.set_title("solve tool-use rate — the think=on cliff")
    axL.set_ylabel("tool_selected (%)")
    axL.legend(loc="lower left")
    # right: truncation rate (budget exhaustion) off vs on, +tool(plain)
    axR.set_axisbelow(True)
    series = []
    for i, think in enumerate(("off", "on")):
        vals = []
        for m in MODEL_ORDER:
            rows = [r for r in bd.CELLS.get((m, think, "tl-neut"), [])
                    if r["task"] == task]
            n = len(rows)
            tr = sum(1 for r in rows if r.get("truncated")) / n * 100 if n else np.nan
            vals.append(tr)
        bars = axR.bar(x + (i - 0.5) * 0.4, vals, 0.4,
                       color=(C_BRAND if think == "off" else C_RED),
                       label=f"think={think}", edgecolor="white", linewidth=0.5,
                       zorder=3)
        series.append((bars, vals))
    finite = [v for _, vals in series for v in vals if v == v]
    axR.set_ylim(0, max(8.0, (max(finite) if finite else 0) * 1.28))
    for bars, vals in series:
        _bar_value_labels(axR, bars, vals)
    axR.set_title("solve truncation rate — budget exhaustion")
    axR.set_ylabel("trials truncated (%)")
    axR.legend(loc="upper right")
    for ax in (axL, axR):
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_DISP[m] for m in MODEL_ORDER], rotation=12)
        ax.grid(axis="y")
        _despine(ax)
    fig.suptitle("Reasoning-mode budget caveat: think=on collapses tool-calling — "
                 "Gemma-MoE-26B & 9B hit hardest (budget, not ability)",
                 fontsize=11, fontweight="bold", color=C_INK, y=1.02)
    fig.tight_layout()
    return _save(fig, save_name)


def fig_phase2(summary: dict, rq: str, tasks: list[str], title: str,
               save_name: str) -> Path:
    """Success vs difficulty bin, no-tools vs +tool(steered), per task panel,
    with the (tl − nt) gap annotated over each bin."""
    fig, axes = plt.subplots(1, len(tasks), figsize=(3.7 * len(tasks), 4.0),
                             squeeze=False)
    for ax, task in zip(axes[0], tasks):
        ax.set_axisbelow(True)
        d = summary[f"{rq}/{task}"]
        xb = np.arange(3)
        nt_rates = [d["nt"][b][0] for b in range(3)]
        tl_rates = [d["tl"][b][0] for b in range(3)]
        # shade the advantage (the tool − no-tools gap) between the two lines
        ax.fill_between(xb, nt_rates, tl_rates, color=ARM_COLOR["tl-ster"],
                        alpha=0.10, zorder=1)
        for arm, k, col in (("no-tools", "nt", ARM_COLOR["nt-neut"]),
                            ("+tool (steered)", "tl", ARM_COLOR["tl-ster"])):
            rates = [d[k][b][0] for b in range(3)]
            err = [[max(0.0, d[k][b][0] - d[k][b][1]) for b in range(3)],
                   [max(0.0, d[k][b][2] - d[k][b][0]) for b in range(3)]]
            ax.errorbar(xb, rates, yerr=err, marker="o", markersize=6,
                        markeredgecolor="white", markeredgewidth=0.8, capsize=3,
                        lw=2.0, color=col, label=arm, zorder=3)
        for b in range(3):
            g = d["gaps"][b]
            ytop = max(d["nt"][b][0], d["tl"][b][0])
            ha = "left" if b == 0 else ("right" if b == 2 else "center")
            ax.annotate(f"Δ{g:+.0f}", (b, ytop + 3.5), ha=ha, fontsize=8,
                        fontweight="bold", color=C_ACCENT, zorder=4,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white",
                                  ec="none", alpha=0.75))
        ax.set_xticks(xb)
        ax.set_xticklabels(d["labels"])
        ax.set_xlim(-0.45, 2.45)
        ax.set_ylim(0, 116)
        ax.set_title(TASK_DISP[task])
        ax.grid(axis="y")
        ax.set_xlabel("difficulty bin")
        _despine(ax)
    axes[0][0].set_ylabel("success rate (%)")
    axes[0][-1].legend(loc="lower left")
    fig.suptitle(title, fontsize=12, fontweight="bold", color=C_INK)
    fig.tight_layout()
    return _save(fig, save_name)


# ---------------- Deck styling (self-contained fork of build_deck chrome) ----------------
# A local styling layer so the look stays in THIS deck — build_deck's helpers are
# shared by build()/build_compare_deck.py and are deliberately left untouched.
# Presentation only: never touches the metric layer, the asserts, or which numbers render.

from pptx.util import Inches, Pt, Emu  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402


def _rgb(h: str) -> RGBColor:
    return RGBColor(int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


INK, SOFT = _rgb(C_INK), _rgb(C_SOFT)
BRAND, ACCENT = _rgb(C_BRAND), _rgb(C_ACCENT)
RULE_C = _rgb(C_RULE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
NAVY = _rgb("#21384E")        # table / header band
ROW_ALT = _rgb("#EEF2F7")     # zebra stripe
GREEN_TINT, GREEN_INK = _rgb("#E3F1E8"), _rgb("#1F6B43")  # favorable-significant Δ
RED_TINT, RED_INK = _rgb("#F7E3E1"), _rgb("#9E3B38")      # significant-against Δ

VERDICT_COLOR = {
    "YES": _rgb("#2E7D52"), "MIXED": _rgb("#C0801A"),
    "NO": _rgb("#B0413E"), "INCONCLUSIVE": _rgb("#6B7280"),
}

# Layout geometry kept as inch floats — all arithmetic happens in inches and is
# wrapped in Inches() only at the call boundary (mixing EMU ints with inch floats
# silently throws shapes off-canvas).
SLIDE_W_IN, SLIDE_H_IN = 13.333, 7.5
MARGIN_IN = 0.62
STRIPE_IN = 0.13
BODY_TOP_IN = 1.46
FOOTER_Y_IN = 7.06
CAPTION_TOP_IN = 6.46

SLIDE_W, SLIDE_H = Inches(SLIDE_W_IN), Inches(SLIDE_H_IN)
MARGIN = Inches(MARGIN_IN)
STRIPE_W = Inches(STRIPE_IN)
TITLE_TOP, TITLE_H = Inches(0.34), Inches(0.82)
RULE_Y = Inches(1.22)
BODY_TOP = Inches(BODY_TOP_IN)
FOOTER_Y = Inches(FOOTER_Y_IN)
FOOTER_TEXT = "PDDL Planning Copilot · single-tool-use evaluation · sweep5v2 · Wilson 95% CIs"


def _no_shadow(shape):
    """Kill the soft drop-shadow autoshapes inherit. The shadow rides on the
    shape's theme <p:style> effectRef, which an empty effectLst on spPr does NOT
    override in LibreOffice — so drop the style element outright (fill/line are
    set explicitly on spPr, so nothing is lost)."""
    sp = shape._element
    style = sp.find(qn("p:style"))
    if style is not None:
        sp.remove(style)
    spPr = sp.spPr
    for el in spPr.findall(qn("a:effectLst")):
        spPr.remove(el)
    spPr.append(spPr.makeelement(qn("a:effectLst"), {}))
    return shape


def _rect(slide, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    return _no_shadow(shp)


def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _badge(slide, keyword: str, color: RGBColor):
    """Pill-shaped verdict chip in the top-right; returns its left edge so the
    title can be clipped short of it."""
    kw = keyword.upper()
    w = Inches(max(1.05, 0.34 + 0.135 * len(kw)))
    h = Inches(0.54)
    x = SLIDE_W - MARGIN - w
    shp = _rect(slide, x, Inches(0.40), w, h, color, MSO_SHAPE.ROUNDED_RECTANGLE)
    try:
        shp.adjustments[0] = 0.5  # full pill corners
    except Exception:
        pass
    tf = shp.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_top = tf.margin_bottom = Pt(2)
    tf.margin_left = tf.margin_right = Pt(8)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = kw
    r.font.size = Pt(20)
    r.font.bold = True
    r.font.color.rgb = WHITE
    return x


def _chrome(slide, title: str, badge: tuple | None = None) -> None:
    """Left accent stripe + title + hairline rule (+ optional verdict badge)."""
    _rect(slide, 0, 0, STRIPE_W, SLIDE_H, BRAND)
    title_right = SLIDE_W - MARGIN
    if badge:
        title_right = _badge(slide, badge[0], badge[1]) - Inches(0.2)
    tb = slide.shapes.add_textbox(MARGIN, TITLE_TOP, title_right - MARGIN, TITLE_H)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(22)
    r.font.bold = True
    r.font.color.rgb = INK
    # hairline rule, with a short brand lead tick at the left
    _rect(slide, MARGIN, RULE_Y, SLIDE_W - 2 * MARGIN, Pt(1.4), RULE_C)
    _rect(slide, MARGIN, RULE_Y - Pt(0.9), Inches(1.5), Pt(3.2), BRAND)


def S_title_slide(prs, title: str, subtitle: str) -> None:
    slide = _blank(prs)
    _rect(slide, 0, 0, SLIDE_W, Inches(0.30), BRAND)              # top band
    _rect(slide, (SLIDE_W - Inches(1.7)) / 2, Inches(2.28),
          Inches(1.7), Pt(4.5), ACCENT)                          # accent tick
    tb = slide.shapes.add_textbox(Inches(1.0), Inches(2.48), SLIDE_W - Inches(2.0), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = title
    r.font.size = Pt(38)
    r.font.bold = True
    r.font.color.rgb = INK
    sb = slide.shapes.add_textbox(Inches(1.0), Inches(3.72), SLIDE_W - Inches(2.0), Inches(0.8))
    stf = sb.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.alignment = PP_ALIGN.CENTER
    sr = sp.add_run()
    sr.text = subtitle
    sr.font.size = Pt(17)
    sr.font.color.rgb = SOFT
    band = _rect(slide, 0, Inches(6.98), SLIDE_W, Inches(0.52), BRAND)  # bottom band
    btf = band.text_frame
    btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    bp = btf.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    br = bp.add_run()
    br.text = "PDDL Planning Copilot   ·   arXiv:2509.12987"
    br.font.size = Pt(11.5)
    br.font.color.rgb = WHITE


def _emit_bullets(tf, bullets: list[str]) -> None:
    """Render bullets with a light visual hierarchy:
       •-lines → top bullet (brand ▸ glyph),  indented/–-lines → sub-bullet,
       →-lines → accent callout, blank → spacer, anything else → plain lead text."""
    first = True

    def para():
        nonlocal first
        if first:
            first = False
            return tf.paragraphs[0]
        return tf.add_paragraph()

    for b in bullets:
        s = b.strip()
        p = para()
        if s == "":
            p.space_after = Pt(3)
            continue
        p.line_spacing = 1.1
        p.space_after = Pt(4)
        if s.startswith("→"):                       # accent callout
            p.space_before = Pt(4)
            r = p.add_run()
            r.text = s
            r.font.size = Pt(14)
            r.font.bold = True
            r.font.color.rgb = ACCENT
        elif b.startswith(" ") or s[0] in "–-":      # sub-bullet
            _indent(p, Inches(0.46), Inches(-0.18))
            g = p.add_run()
            g.text = "–  "
            g.font.size = Pt(13)
            g.font.color.rgb = SOFT
            r = p.add_run()
            r.text = s.lstrip("–- ").strip()
            r.font.size = Pt(13)
            r.font.color.rgb = SOFT
        elif s.startswith("•"):                      # top bullet
            _indent(p, Inches(0.28), Inches(-0.28))
            p.space_before = Pt(3)
            g = p.add_run()
            g.text = "▸  "
            g.font.size = Pt(13)
            g.font.bold = True
            g.font.color.rgb = BRAND
            r = p.add_run()
            r.text = s.lstrip("• ").strip()
            r.font.size = Pt(14)
            r.font.color.rgb = INK
        else:                                        # plain lead text
            r = p.add_run()
            r.text = s
            r.font.size = Pt(15)
            r.font.color.rgb = INK


def _indent(p, marL, indent) -> None:
    """Set paragraph left margin / hanging indent (EMU) on the pPr element."""
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(marL)))
    pPr.set("indent", str(int(indent)))


def S_text_slide(prs, title: str, bullets: list[str], badge: tuple | None = None) -> None:
    slide = _blank(prs)
    _chrome(slide, title, badge=badge)
    body = slide.shapes.add_textbox(MARGIN, BODY_TOP, SLIDE_W - 2 * MARGIN,
                                    FOOTER_Y - BODY_TOP - Inches(0.1))
    tf = body.text_frame
    tf.word_wrap = True
    _emit_bullets(tf, bullets)


def S_image_slide(prs, title: str, image_path, caption: str | None = None,
                  notes: str | None = None) -> None:
    slide = _blank(prs)
    _chrome(slide, title)
    cap_top_in = CAPTION_TOP_IN if caption else FOOTER_Y_IN
    band_top = BODY_TOP_IN
    band_h = cap_top_in - band_top
    from PIL import Image
    with Image.open(image_path) as im:
        w_px, h_px = im.size
    aspect = w_px / h_px
    max_w = SLIDE_W_IN - 2 * MARGIN_IN
    max_h = band_h - 0.08
    if max_w / aspect <= max_h:
        w_in, h_in = max_w, max_w / aspect
    else:
        h_in, w_in = max_h, max_h * aspect
    left = (SLIDE_W_IN + STRIPE_IN) / 2 - w_in / 2   # centre in the area right of the stripe
    top = band_top + (band_h - h_in) / 2
    slide.shapes.add_picture(str(image_path), Inches(left), Inches(top),
                             width=Inches(w_in), height=Inches(h_in))
    if caption:
        cb = slide.shapes.add_textbox(MARGIN, Inches(cap_top_in), SLIDE_W - 2 * MARGIN, Inches(0.55))
        ctf = cb.text_frame
        ctf.word_wrap = True
        p = ctf.paragraphs[0]
        r = p.add_run()
        r.text = caption
        r.font.size = Pt(10.5)
        r.font.color.rgb = SOFT
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def _delta_tint(text: str):
    """Tint the CI-disjoint (signed-significant) Δ cells: green = favorable,
    red = against. Returns (fill, ink) or None."""
    if "*" not in text:
        return None
    t = text.strip()
    if t.startswith("+"):
        return GREEN_TINT, GREEN_INK
    if t.startswith("-") or t.startswith("−"):
        return RED_TINT, RED_INK
    return None


def S_table_slide(prs, title: str, headers: list[str], rows: list[list[str]],
                  notes: str | None = None) -> None:
    slide = _blank(prs)
    _chrome(slide, title)
    n_rows, n_cols = len(rows) + 1, len(headers)
    table_h = Inches(min(5.4, 0.34 * n_rows + 0.3))
    gfx = slide.shapes.add_table(n_rows, n_cols, MARGIN, BODY_TOP,
                                 SLIDE_W - 2 * MARGIN, table_h)
    table = gfx.table
    table.first_row = False        # disable the built-in style banding; we paint it
    table.horz_banding = False
    # first column gets more room for model / task names (inch arithmetic)
    col0_in = 2.5
    rest_in = (SLIDE_W_IN - 2 * MARGIN_IN - col0_in) / (n_cols - 1)
    table.columns[0].width = Inches(col0_in)
    for j in range(1, n_cols):
        table.columns[j].width = Inches(rest_in)
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_top = cell.margin_bottom = Pt(2)
        tfc = cell.text_frame
        tfc.word_wrap = True
        p = tfc.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        r = p.add_run()
        r.text = h
        r.font.size = Pt(10)
        r.font.bold = True
        r.font.color.rgb = WHITE
    # Zebra by GROUP: a new band starts whenever the first column is non-empty.
    # Per-model tables (every row labelled) → plain alternating; the phase-2 table
    # (task name only on its first bin row) → one band per 3-bin task block.
    group = -1
    for i, row in enumerate(rows, start=1):
        if str(row[0]).strip():
            group += 1
        base = WHITE if group % 2 == 0 else ROW_ALT
        for j, v in enumerate(row):
            v = str(v)
            cell = table.cell(i, j)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_top = cell.margin_bottom = Pt(1)
            ink, fill = INK, base
            tint = _delta_tint(v) if j >= 1 else None
            if tint:
                fill, ink = tint
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = v
            r.font.size = Pt(9.5)
            r.font.color.rgb = ink
            if j == 0 or tint:
                r.font.bold = True
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def _finalize_footers(prs) -> None:
    slides = list(prs.slides)
    n = len(slides)
    for i, slide in enumerate(slides, start=1):
        if i == 1:
            continue  # cover slide carries its own band
        _rect(slide, MARGIN, FOOTER_Y, SLIDE_W - 2 * MARGIN, Pt(0.8), RULE_C)
        lf = slide.shapes.add_textbox(MARGIN, FOOTER_Y + Inches(0.03),
                                      Inches(10.0), Inches(0.3))
        lp = lf.text_frame.paragraphs[0]
        lr = lp.add_run()
        lr.text = FOOTER_TEXT
        lr.font.size = Pt(8.5)
        lr.font.color.rgb = SOFT
        pn = slide.shapes.add_textbox(SLIDE_W - MARGIN - Inches(1.3),
                                      FOOTER_Y + Inches(0.03), Inches(1.3), Inches(0.3))
        pp = pn.text_frame.paragraphs[0]
        pp.alignment = PP_ALIGN.RIGHT
        pr = pp.add_run()
        pr.text = f"{i} / {n}"
        pr.font.size = Pt(8.5)
        pr.font.color.rgb = SOFT


# ---------------- PPTX assembly (Q→A→Evidence) ----------------

def _arm_table(task: str) -> tuple[list[str], list[list[str]]]:
    headers = ["model", "no-tools", "+tool(plain)", "+tool(steered)",
               "avail Δ", "steer Δ"]
    rows = []
    for m in MODEL_ORDER:
        nt = cell_success(m, task, "nt-neut")
        pl = cell_success(m, task, "tl-neut")
        st = cell_success(m, task, "tl-ster")
        av = signed_gap(m, task, "nt-neut", "tl-neut")
        sv = signed_gap(m, task, "tl-neut", "tl-ster")
        def cf(c):
            return f"{c.rate*100:.0f} [{c.lo*100:.0f},{c.hi*100:.0f}]" if c.n else "–"
        def gf(g):
            mark = "*" if g["significant"] else ""
            return f"{g['gap']:+.0f}{mark}" if g["gap"] == g["gap"] else "–"
        rows.append([MODEL_DISP[m], cf(nt), cf(pl), cf(st), gf(av), gf(sv)])
    return headers, rows


def build_pptx(summary: dict, gate_lines: list[str]) -> Path:
    prs = bd._make_pptx()

    # --- title ---
    S_title_slide(
        prs, "Does a planning tool help LLMs on PDDL tasks?",
        "5 language models · 5 PDDL planning tasks · with vs. without a real "
        "planner/validator tool · success rates with 95% confidence intervals")

    # --- plain-language onboarding (slides 2–4): give a reader who has never seen
    #     this experiment the context + a decoder for the short labels used later.
    #     The technical methods slide that follows is the optional deeper layer. ---
    S_text_slide(prs, "What we're testing", [
        "PDDL is the standard formal language AI planners use to describe a world, the actions "
        "allowed in it, a goal to reach, and step-by-step plans. We give a language model five "
        "PDDL jobs:",
        "• solve — find a plan (a sequence of actions) that reaches the goal",
        "• validate_domain — check that the file defining the world and its actions is correct PDDL",
        "• validate_problem — check that the file listing the objects, the start state and the goal is correct PDDL",
        "• validate_plan — decide whether a given plan actually works (a yes/no verdict)",
        "• simulate — track how the world changes as a plan is run, one action at a time",
        "",
        "The question: do models do these jobs better when we also let them call a real "
        "planner/validator program — a “tool” — instead of answering only from their own knowledge?",
    ])

    S_text_slide(prs, "The three setups we compare", [
        "Every job is run in three setups (we call them “arms”), and we never mix their results:",
        "• no-tools — the model answers on its own, with no external help.  This is the baseline.",
        "• tool available — exactly the same request, but now a real planner/validator is there for the model to call if it chooses to.",
        "• tool + nudge — the tool is available AND we append one sentence explicitly telling the model to use it (we call this “steered”).",
        "",
        "Comparing neighbouring arms answers two separate questions:",
        "      – Does simply having the tool help?  (no-tools  vs  tool available — the wording is otherwise identical)",
        "      – Or did the model just need to be told to use it?  (tool available  vs  tool + nudge)",
        "",
        "In the tables these arms appear as the short codes  nt-neut · tl-neut · tl-ster  (same order).",
    ])

    S_text_slide(prs, "How to read the charts & tables", [
        "• success rate — how often the model's answer matched the known-correct answer, 0–100%. It is the only score shown.",
        "• Error bars (charts) and the [low, high] brackets (tables) are 95% confidence intervals: the range the true rate is "
        "likely in, given how many trials we ran. When two ranges don't overlap, the difference is real rather than noise.",
        "• A “*” on a gap in a table means exactly that — the two ranges don't overlap.  Green = the tool helped, red = the tool hurt.",
        "• “≥9B” — the headline conclusions use the larger models (9 billion parameters and up: Qwen3.5-9B, Gemma-MoE-26B, "
        "Qwen3.6-35B). The two smaller models are shown for context.",
        "• “think=off” — the model answers directly. We also tested “think=on” (it reasons first); that is treated as a caveat, not the headline.",
        "• “difficulty bins” (later slides) — we split the problems into easy / medium / hard thirds to see whether the tool's "
        "advantage changes as problems get harder.",
    ])

    # --- methods (technical deeper layer) ---
    S_text_slide(prs, "Methods — the technical details", [
        "• Metric is raw task success with Wilson 95% confidence intervals; the three arms (nt-neut / tl-neut / tl-ster) "
        "are scored separately and never pooled.",
        "• “Significant” is SIGNED: a gap is counted only when the two arms' 95% intervals are disjoint AND it points the "
        "hypothesised way (the tool helps). Gaps that are significant but point the OTHER way are reported separately — this is "
        "why RQ0.3 reads MIXED rather than YES.",
        "• Two known caveats get their own slides: the validate_plan tool-calling artifact (the RQ0.3 “Gate”) and the "
        "think=on decode-budget cliff. A contamination re-run on disguised problems (sweep-6) left the baseline unchanged (footnote).",
        "• Phase-2 (RQ0.5 / RQ0.6) compares no-tools vs tool + nudge on the ≥9B models, splitting trials by problem difficulty.",
    ])

    # --- RQ0.1–0.4 ---
    # The RQ0.3 gate (validate_plan tool-calling artifact) is emitted INSIDE the
    # RQ0.3 section, right before its evidence chart — it is the reading-guide for
    # the surprising low +tool(plain) bar, so it belongs next to it, not orphaned
    # up front after Methods.
    for rq, tasks in RQ_TASKS.items():
        _add_phase1_rq(prs, rq, tasks, summary, gate_lines)

    # --- think=on caveat ---
    cliff = fig_think_on_cliff("think_on_cliff.png")
    S_image_slide(
        prs, "Caveat — think=on is a decode-budget cliff (Gemma-MoE-26B & 9B hardest)",
        cliff,
        caption="Left: solve tool-use rate across budget states — neutral think=on collapses tool-calling vs "
        "think=off, worst on Gemma-MoE-26B (100→23) and Qwen3.5-9B (100→59), NOT strictly the smallest model "
        "(0.8B 97→46); steering partly restores it. Right: solve truncation rate spikes under think=on. The "
        "headline uses think=off; the think=on degradation is budget exhaustion, not ability.")

    # --- RQ0.5 ---
    rq05 = fig_phase2(summary, "rq05",
                      ["solve", "validate_plan", "simulate"],
                      "RQ0.5 — does the tool advantage change with PLAN LENGTH? "
                      "(no-tools vs +tool steered, ≥9B)", "phase2_rq05.png")
    _add_phase2_rq(prs, "RQ0.5", "Does the planning tool's advantage CHANGE as instances get harder "
                   "(longer reference / plan length)?",
                   "YES for validate_plan — the advantage GROWS with plan length.",
                   ["validate_plan is the headroom-gated case (both arms have room to move): the "
                    "no-tools − tool gap widens from +5pp (short plans) to +27pp (long plans) as no-tools "
                    "degrades while the tool holds.",
                    "solve and simulate are framed as tool-arm robustness: no-tools is floored (~0–12%) at "
                    "every length, so the ~87–99pp gap is large but does not 'grow' — there is no no-tools "
                    "headroom to lose."],
                   rq05, summary, "rq05",
                   ["solve", "validate_plan", "simulate"])

    # --- RQ0.6 ---
    rq06 = fig_phase2(summary, "rq06",
                      ["solve", "validate_problem", "validate_plan", "simulate"],
                      "RQ0.6 — does the tool advantage change with OBJECT COUNT? "
                      "(no-tools vs +tool steered, ≥9B)", "phase2_rq06.png")
    _add_phase2_rq(prs, "RQ0.6", "Does the tool's advantage CHANGE as the problem's object count (arity) grows?",
                   "NO clear effect — the gap is flat across object-count bins.",
                   ["validate_problem is the headroom-gated case for arity; its gap is ~22pp and essentially "
                    "constant across ≤5 / 5–13 / >13 objects.",
                    "solve / validate_plan / simulate gaps are also flat across object count (no-tools floored "
                    "or already separated). Object count is not a difficulty axis that the tool's advantage "
                    "tracks."],
                   rq06, summary, "rq06",
                   ["solve", "validate_problem", "validate_plan", "simulate"])

    # --- robustness footnote (sweep-6) ---
    S_text_slide(prs, "Robustness footnote — contamination probe (sweep-6)", [
        "• A separate anonymised-corpus sweep (sweep-6) re-ran the matrix on structurally-identical domains "
        "with every surface name renamed, to test memorisation.",
        "• Headline (think=off): the clean no-tools-neutral probe is near-null — Δ(canonical − anon) success "
        "≤1.3pp mean |Δ|, zero CI-disjoint task cells. No broad train-set contamination of the pure-model "
        "baseline where it has headroom.",
        "• Implication for this deck: the no-tools baselines that the tool's value is measured against are not "
        "inflated by memorisation, so the availability gaps reported here are not a contamination artifact.",
    ])

    # --- out-of-scope ---
    S_text_slide(prs, "Out of scope (phase-3)", [
        "• Cross-benchmark generalisation (PlanBench) and comparison to published SOTA formalizer baselines "
        "(e.g. Huang & Zhang, ACL 2025) are deliberately OUT OF SCOPE for this single-tool-use deck.",
        "• This deck answers: within our 5-model × 5-task matrix, does giving the model a planning/validation "
        "tool (and steering it to use the tool) raise success, and does that advantage track difficulty?",
    ])

    _finalize_footers(prs)
    PPTX_OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(PPTX_OUT))
    return PPTX_OUT


def _add_gate_slide(prs, gate_lines: list[str]) -> None:
    """The RQ0.3 reading-guide: +tool(plain)'s low raw-success on validate_plan is
    a tool-calling artifact (no verdict emitted), not a verdict collapse. Placed
    immediately before the RQ0.3 evidence chart it explains."""
    S_text_slide(prs, "Gate — RQ0.3 validate_plan is a tool-calling artifact (not a verdict collapse)",
                 ["Relabel verified inert; +tool(plain) raw-success is low because the model often "
                  "produces NO verdict (huge no_ans), but is near-perfect when it DOES answer:"]
                 + [f"• {ln}" for ln in gate_lines]
                 + ["→ Steering fixes this by getting the model to call the tool (RQ0.3 mechanism slide)."])


def _add_phase1_rq(prs, rq: str, tasks: list[str], summary: dict,
                   gate_lines: list[str]) -> None:
    task_label = " + ".join(TASK_DISP[t] for t in tasks)
    question = {
        "RQ0.1": "Does giving the model a validation tool help it validate PDDL domains and problems?",
        "RQ0.2": "Does giving the model a planning tool help it SOLVE PDDL problems?",
        "RQ0.3": "Does giving the model a validation tool help it CHECK whether a plan is valid?",
        "RQ0.4": "Does giving the model a simulation tool help it TRACK state (simulate a plan)?",
    }[rq]

    # (1) question slide
    S_text_slide(prs, f"{rq} — Question", [
        f"Task(s): {task_label}", "", question, "",
        "Answered on the larger models in direct-answer mode, using the two comparisons from the "
        "setup slide: does simply having the tool help (no-tools → tool available), and did the model "
        "need to be nudged to use it (tool available → tool + nudge)?",
    ])

    # (2) answer slide — signed verdict
    head_task = tasks[-1] if rq == "RQ0.1" else tasks[0]
    avail9 = claim_counts(head_task, "nt-neut", "tl-neut", MODELS_9B)
    steer9 = claim_counts(head_task, "tl-neut", "tl-ster", MODELS_9B)
    computed = derive_verdict(avail9)
    locked = RQ_VERDICT[rq]
    assert computed == locked, (
        f"{rq}: computed verdict {computed} != locked scorecard {locked} "
        f"(avail fav={avail9['fav_sig']} against={avail9['against_sig']})")
    bullets = [
        f"Availability ({TASK_DISP[head_task]}, ≥9B): gap {avail9['gap_min']:+.0f}…{avail9['gap_max']:+.0f}pp; "
        f"{avail9['fav_sig']}/3 favorable-significant, {avail9['against_sig']}/3 significant-against (95% CIs).",
        f"Steering ({TASK_DISP[head_task]}, ≥9B): gap {steer9['gap_min']:+.0f}…{steer9['gap_max']:+.0f}pp; "
        f"{steer9['fav_sig']}/3 favorable-significant.",
    ]
    bullets += _rq_headline_notes(rq)
    S_text_slide(prs, f"{rq} — Answer", bullets,
                 badge=(locked, VERDICT_COLOR[locked]))

    # (2.5) RQ0.3 gate — reading-guide for the low +tool(plain) bar, right before it
    if rq == "RQ0.3":
        _add_gate_slide(prs, gate_lines)

    # (3) evidence: success-by-arm plot + table, per task
    for task in tasks:
        png = fig_success_by_arm(task, f"{task}.png")
        S_image_slide(
            prs, f"{rq} — Evidence: {TASK_DISP[task]} success by arm", png,
            caption="Grey=no-tools, blue=+tool(plain), orange=+tool(steered). Whiskers=Wilson 95% CI. "
            "Shaded band marks the ≥9B headline set (right of Qwen3.5-4B).")
        headers, table_rows = _arm_table(task)
        S_table_slide(prs, f"{rq} — {TASK_DISP[task]} success table (rate [Wilson 95%], * = CI-disjoint)",
                      headers, table_rows)

    # (4) mechanism
    mech = fig_mechanism(head_task, f"mechanism_{head_task}.png")
    S_image_slide(
        prs, f"{rq} — Mechanism: steering raises tool-calling → raises success",
        mech,
        caption=f"{TASK_DISP[head_task]}, ≥9B. Left: tool-use rate (tool_selected) plain vs steered. "
        "Right: success. Where +tool(plain) under-calls the tool, steering raises tool-calling, and "
        "success rises with it — the tool's value is gated on the model actually invoking it.")


def _rq_headline_notes(rq: str) -> list[str]:
    return {
        "RQ0.1": ["", "Caveat: at 0.8B the availability gap REVERSES on validate_problem (−25pp) — the "
                  "smallest model mishandles the tool. YES holds from 4B up."],
        "RQ0.2": ["", "Decisive: no-tools is floored (~8–11%); +tool lifts ≥9B to 63–99%. Steering adds a "
                  "large further lift where plain left headroom (Qwen3.6-35B +29pp)."],
        "RQ0.3": ["", "MIXED: the model alone is already strong on validate_plan (75–90%). At +tool(plain) the "
                  "availability gap is significant-AGAINST for Gemma-MoE (−67pp: it stops answering) and "
                  "Qwen3.6-35B (−9pp); only Qwen3.5-9B is favorable. Steering RECOVERS and beats no-tools "
                  "(Gemma 21→93%), but the net tool benefit over a strong baseline is small/mixed."],
        "RQ0.4": ["", "Decisive: no-tools is 0% everywhere (state-tracking by hand fails); +tool reaches "
                  "65–92% on ≥9B, with steering adding +18–22pp."],
    }[rq]


def _add_phase2_rq(prs, rq: str, question: str, answer: str, bullets: list[str],
                   png: Path, summary: dict, key: str, tasks: list[str]) -> None:
    S_text_slide(prs, f"{rq} — Question", [question, "",
                 "Phase-2 is headroom-gated: an advantage can only be seen to CHANGE where both arms "
                 "have room to move. ≥9B, think=off, no-tools vs +tool(steered)."])
    gap_tbl_task = "validate_plan" if rq == "RQ0.5" else "validate_problem"
    d = summary[f"{key}/{gap_tbl_task}"]
    gap_line = " → ".join(f"{d['labels'][b]}: Δ{d['gaps'][b]:+.0f}" for b in range(3))
    kw = answer.split()[0].strip(",.").upper()
    badge = (kw, VERDICT_COLOR[kw]) if kw in VERDICT_COLOR else None
    S_text_slide(prs, f"{rq} — Answer", [answer, "",
                 f"Headroom case ({gap_tbl_task}) gap by bin:  {gap_line}."] + [""] + bullets,
                 badge=badge)
    S_image_slide(prs, f"{rq} — Evidence", png,
                  caption="Per difficulty bin: no-tools (grey) vs +tool steered (orange), Wilson 95% CIs; "
                  "Δ = tool − no-tools over each bin (shaded = the advantage).")
    headers = ["task", "bin", "no-tools", "+tool(steered)", "Δ (pp)", "n/arm"]
    rows = []
    for task in tasks:
        dd = summary[f"{key}/{task}"]
        for b in range(3):
            rows.append([TASK_DISP[task] if b == 0 else "", dd["labels"][b],
                         f"{dd['nt'][b][0]:.0f} [{dd['nt'][b][1]:.0f},{dd['nt'][b][2]:.0f}]",
                         f"{dd['tl'][b][0]:.0f} [{dd['tl'][b][1]:.0f},{dd['tl'][b][2]:.0f}]",
                         f"{dd['gaps'][b]:+.0f}", str(dd['nt'][b][3])])
    S_table_slide(prs, f"{rq} — difficulty-binned success (no-tools vs +tool steered)",
                  headers, rows)


# ---------------- Main ----------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="run gates + phase-2 assertion only; do not render plots/pptx")
    ap.add_argument("--no-assert-oracle", action="store_true",
                    help="skip the byte-equality assertion against the existing phase2_summary.json oracle")
    args = ap.parse_args()

    print(f"loading {RESULTS_ROOT} ...", file=sys.stderr)
    bd.CELLS = bd.load_all(RESULTS_ROOT)
    bd.MODEL_ORDER = MODEL_ORDER

    print("=== GATE: RQ0.3 validate_plan tool-calling artifact ===", file=sys.stderr)
    gate_lines = run_gate()
    for ln in gate_lines:
        print("  " + ln, file=sys.stderr)

    print("=== PHASE-2 ===", file=sys.stderr)
    summary = build_phase2()
    if not args.no_assert_oracle:
        if PHASE2_EXPECTED.exists():
            assert_phase2_matches(summary, PHASE2_EXPECTED)
            print(f"  phase2 reproduces tracked {PHASE2_EXPECTED.name} exactly "
                  f"(7 keys × 3 bins)", file=sys.stderr)
        else:
            print(f"  warn: no tracked oracle at {PHASE2_EXPECTED} — skipping "
                  f"regression assertion", file=sys.stderr)
    PHASE2_JSON.parent.mkdir(parents=True, exist_ok=True)
    PHASE2_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")

    if args.check:
        print("--check: gates + phase-2 assertion passed; skipping render", file=sys.stderr)
        return 0

    print("=== RENDER ===", file=sys.stderr)
    out = build_pptx(summary, gate_lines)
    n_slides = len(out and __import__("pptx").Presentation(str(out)).slides._sldIdLst)
    print(f"wrote {out}  ({n_slides} slides)", file=sys.stderr)
    print(f"plots → {PLOT_DIR}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
