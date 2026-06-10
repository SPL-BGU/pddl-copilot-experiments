"""Paper-ready single-tool-use RQ analysis + slideshow for sweep5v2.

Regenerates every RQ figure from `results/sweep5v2-live/` and emits a PPTX:
hook (simulate 0%→tool) → scorecard → onboarding → signed-significance →
Answer→Evidence blocks for RQ0.1–0.4 (question folded into the Answer slide;
mechanism slide only where +tool(plain) under-calls the tool) → small-model
caveat (0.8B, pulled out of the main charts) → token section (quadrant
tokens-vs-success figure, input/output inversion figure, cost-of-pass dumbbell
grouped by baseline regime, exact decomposition, censoring + turns latency
proxy) → think=on cliff → RQ0.5 → RQ0.6 (single slide; null result) →
contamination footnote → out-of-scope → backup (detailed token tables incl.
the secondary completion-only lens, RQ0.6 bin table). Read-only over `results/`.
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
import math
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
# Efficiency section only (≥4B): one extra model below the ≥9B headline. Kept
# SEPARATE from MODELS_9B on purpose — MODELS_9B drives the locked RQ verdicts
# (claim_counts) and the phase-2 oracle, which must not move.
EFF_MODELS = ["Qwen3_5_4B"] + MODELS_9B
# Main evidence charts/tables show ≥4B only — 0.8B's tool-mishandling rows
# widened every figure while contributing one caveat; it gets its own slide
# (`_small_model_table`). The think=on cliff figure keeps all 5 models (it is
# ABOUT small-model budget behaviour), and MODEL_ORDER still drives load_all.
CHART_MODELS = EFF_MODELS
SMALL_MODEL = "Qwen3_5_0_8B"
# Per-model colours for the token quadrant figure (distinct from arm colours).
MODEL_COLOR = {"Qwen3_5_9B": "#3F7CAC", "gemma4_26b-a4b": "#6A994E",
               "qwen3_6_35b": "#8E5572"}

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
# Canonical 5-task order for the cross-cutting per-token efficiency table.
ALL_TASKS = ["solve", "validate_domain", "validate_problem",
             "validate_plan", "simulate"]
# The efficiency tables are 5 tasks × 4 models = 21 rows, which overflow one
# slide (LibreOffice floors table-row height at ~0.29"). Split each across two
# slides so every row stays above the footer at the normal table font.
EFF_TASK_GROUPS = [(ALL_TASKS[:3], "1/2"), (ALL_TASKS[3:], "2/2")]

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


@dataclass
class Eff:
    """Per-token efficiency over one cell's token-bearing trials for a task.

    `idx` = successes per 1,000 ACTION tokens = (s / tok) * 1000. Because s, n
    and tok are all over the SAME token-bearing subset, this equals
    succ_rate / mean_tok * 1000 exactly (the n cancels) — the user's literal
    "success rate ÷ action tokens", just scaled for readability.
    """
    idx: float      # successes per 1k action tokens (the headline ratio)
    succ: float     # success rate over the token-bearing subset
    lo: float       # Wilson 95% on succ (component CI; the idx itself has none)
    hi: float
    mean_tok: float  # mean action (completion) tokens per trial
    s: int
    n: int
    tok: int        # total action (completion) tokens over the subset


def cell_success(model: str, task: str, arm: str, think: str | None = None) -> Cell:
    think = think or THINK
    rows = bd.CELLS.get((model, think, arm), [])
    rate, s, n = bd.task_success_rate(rows, task)
    lo, hi = wilson_ci(s, n)
    return Cell(rate, lo, hi, s, n)


def cell_toolsel(model: str, task: str, arm: str, think: str | None = None) -> Cell:
    think = think or THINK
    rows = bd.CELLS.get((model, think, arm), [])
    rate, s, n = bd.tool_selected_rate(rows, task)
    lo, hi = wilson_ci(s, n)
    return Cell(rate, lo, hi, s, n)


def cell_efficiency(model: str, task: str, arm: str, think: str | None = None) -> Eff:
    """Per-token "tool intelligence" = success ÷ action tokens for one cell.

    ACTION tokens = OUTPUT (completion) tokens, summed across the model's turns
    (the agent tool-loop runs up to MAX_TOOL_LOOPS=10 turns; no-tools runs 1).
    Computed over the token-bearing subset only — trials with an empty `tokens`
    dict are infra-failure placeholders, excluded the same way bd.token_stats
    does — so the numerator (s) and denominator (tok) share one trial set and
    the s/tok identity holds.

    think=off ONLY for the headline: under think=off the model emits no separate
    reasoning trace, so output IS action. Under think=on completion = thinking +
    action, so it is NOT pure action tokens — a think=on read needs a
    thinking/action split and is deferred (see the framing slide).
    """
    think = think or THINK
    rows = [r for r in bd.CELLS.get((model, think, arm), [])
            if r["task"] == task and r.get("tokens")]
    n = len(rows)
    s = sum(1 for r in rows if r["success"])
    tok = sum(int((r["tokens"].get("completion", 0) or 0)) for r in rows)
    succ = s / n if n else float("nan")
    lo, hi = wilson_ci(s, n)
    idx = (s / tok * 1000) if tok else float("nan")
    mean_tok = (tok / n) if n else float("nan")
    return Eff(idx, succ, lo, hi, mean_tok, s, n, tok)


@dataclass
class CostPerSuccess:
    mean: float   # mean action tokens spent ON A CORRECT ANSWER (lower = better)
    lo: float     # bootstrap 95% on the mean
    hi: float
    n: int        # number of successful trials priced


def _bootstrap_ci_mean(xs: list[int], B: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for the mean of `xs`. Deterministic (fixed
    seed) so the deck regenerates byte-stable. Token-per-success is right-skewed
    (a t-interval would understate the tail), so resample the mean instead."""
    a = np.asarray(xs, dtype=float)
    if a.size == 0:
        return float("nan"), float("nan")
    if a.size == 1:
        return float(a[0]), float(a[0])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(B, a.size))
    means = a[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def cell_cost_per_success(model: str, task: str, arm: str,
                          think: str | None = None) -> CostPerSuccess:
    """Cost per correct answer = mean action (completion) tokens over the
    SUCCESSFUL trials only — "when the model gets it right, how many tokens did
    that take?". LOWER is better. This is the documented H3 (cost-per-success),
    the complement of `cell_efficiency` (success-per-cost): restricting to
    successes removes the failed-attempt tokens, so it is NOT just the index
    flipped, and (unlike a bare ratio) the mean carries a real CI. Returns n=0
    when the arm produced no correct answer to price (e.g. floored baselines)."""
    think = think or THINK
    toks = [int((r["tokens"].get("completion", 0) or 0))
            for r in bd.CELLS.get((model, think, arm), [])
            if r["task"] == task and r.get("tokens") and r.get("success")]
    n = len(toks)
    if n == 0:
        return CostPerSuccess(float("nan"), float("nan"), float("nan"), 0)
    lo, hi = _bootstrap_ci_mean(toks)
    return CostPerSuccess(sum(toks) / n, lo, hi, n)


def _bootstrap_ci_ratio(toks: list[int], succ: list[int],
                        B: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for cost-of-pass = Σtokens ÷ Σsuccesses, a
    ratio of two trial-level sums. Resample TRIALS (each carries its token cost
    and a 0/1 success) and recompute the ratio, so the interval reflects variation
    in both the token bill and the hit rate. Resamples with zero successes are
    dropped (the ratio is undefined). Deterministic via fixed seed."""
    tok = np.asarray(toks, dtype=float)
    suc = np.asarray(succ, dtype=float)
    if tok.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, tok.size, size=(B, tok.size))
    num = tok[idx].sum(axis=1)
    den = suc[idx].sum(axis=1)
    ok = den > 0
    if not ok.any():
        return float("nan"), float("nan")
    ratios = num[ok] / den[ok]
    return float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5))


@dataclass
class CostOfPass:
    """Cost-of-pass = expected tokens per SUCCESS over a cell's token-bearing
    trials = Σtokens ÷ #successes (≡ mean tokens/trial ÷ success rate). Unlike
    `CostPerSuccess` (mean over successful trials only), this charges the tokens
    burned on FAILED attempts to the success count — the true 'what does one
    correct answer cost end-to-end?' metric. LOWER is better."""
    cop: float       # tokens per success (point estimate)
    lo: float        # bootstrap 95%
    hi: float
    n_succ: int      # successes priced
    n: int           # token-bearing trials in the cell
    mean_tok: float  # mean tokens/trial (numerator ÷ n) — for the decomposition
    succ: float      # success rate over the token-bearing subset


def cell_cost_of_pass(model: str, task: str, arm: str,
                      denom: str = "total", think: str | None = None) -> CostOfPass:
    """cost-of-pass for one cell. denom='total' (prompt+completion, the default —
    real consumption per success) or 'completion' (output-only). Computed over the
    token-bearing subset so numerator and denominator share one trial set, exactly
    as `cell_efficiency` does. Returns n_succ=0 (unpriceable) for floored arms."""
    think = think or THINK
    rows = [r for r in bd.CELLS.get((model, think, arm), [])
            if r["task"] == task and r.get("tokens")]
    n = len(rows)
    if denom == "completion":
        toks = [int((r["tokens"].get("completion", 0) or 0)) for r in rows]
    else:
        toks = [int((r["tokens"].get("prompt", 0) or 0))
                + int((r["tokens"].get("completion", 0) or 0)) for r in rows]
    flags = [1 if r["success"] else 0 for r in rows]
    s = sum(flags)
    mean_tok = (sum(toks) / n) if n else float("nan")
    succ = (s / n) if n else float("nan")
    if s == 0:
        return CostOfPass(float("nan"), float("nan"), float("nan"), 0, n, mean_tok, succ)
    lo, hi = _bootstrap_ci_ratio(toks, flags)
    return CostOfPass(sum(toks) / s, lo, hi, s, n, mean_tok, succ)


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

def run_gate(think: str | None = None) -> list[str]:
    """Verify (a) the FastMCP relabel is INERT on this corpus and (b) the
    validate_plan +tool(plain) low raw-success is a TOOL-CALLING artifact
    (acc_decided≈99, fp≈0, huge no_ans), not a verdict collapse. Returns the
    human-readable gate report lines; raises on violation. The acc_decided
    floor is asserted only for think=off (the locked headline); for think=on
    the lines are descriptive — under-calling is even more extreme there
    (Gemma plain tool_selected ≈1%) and the decided subset can be tiny."""
    think = think or THINK
    # The two models whose +tool(plain) arm under-calls on this mode's corpus.
    gate_models = ("gemma4_26b-a4b", "Qwen3_5_0_8B") if think == "off" else \
                  ("gemma4_26b-a4b", "Qwen3_5_9B")
    lines = []
    for model in gate_models:
        cond = "tools_all_minimal"
        cell = RESULTS_ROOT / f"slurm_vllm_{model}_{think}_{cond}"
        cms = {}
        for relabel in (False, True):
            rows = [r for r in iter_trials(cell, relabel=relabel, think_mode=think)
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
        raw = cell_success(model, "validate_plan", "tl-neut", think)
        decided = cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"]
        answered = decided / (decided + cm["no_ans"]) * 100 if (decided + cm["no_ans"]) else float("nan")
        lines.append(
            f"{MODEL_DISP[model]} — raw success {raw.rate*100:.0f}%, but it only produces a verdict on "
            f"{answered:.0f}% of trials; when it DOES answer, accuracy is {acc*100:.0f}% "
            f"(false-positives: {cm['fp']}).")
        if think == "off":
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
    """Per-task raw success across the ≥4B chart models × 3 arms, Wilson 95%
    whiskers. 0.8B is deliberately excluded (own caveat slide)."""
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.set_axisbelow(True)
    x = np.arange(len(CHART_MODELS))
    w = 0.26
    ax.set_ylim(0, 122)
    # gentle band behind the ≥9B headline set
    band_lo = min(CHART_MODELS.index(m) for m in MODELS_9B) - 0.5
    ax.axvspan(band_lo, len(CHART_MODELS) - 0.5, color=C_BRAND, alpha=0.05, zorder=0)
    ax.axvline(band_lo, ls=(0, (4, 3)), lw=0.9, color=C_SPINE, zorder=1)
    for i, arm in enumerate(ARMS):
        rates, errs = [], [[], []]
        for m in CHART_MODELS:
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
    ax.set_xticklabels([MODEL_DISP[m] for m in CHART_MODELS], rotation=12)
    ax.set_ylabel("success rate (%)")
    ax.set_title(f"{TASK_DISP[task]} — success by arm  ·  think={THINK}")
    ax.text(len(CHART_MODELS) - 0.5, 119, "≥9B headline", ha="right", va="top",
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
                 f"which raises success  ·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=C_INK, y=1.02)
    fig.tight_layout()
    return _save(fig, save_name)


def _pooled_rows(models: list[str], arm: str, think: str | None = None) -> list[dict]:
    """Concatenate the trial rows of `models` for one arm (cross-model pooling
    for the token figures; the RQ verdicts never pool — this is descriptive)."""
    think = think or THINK
    out: list[dict] = []
    for m in models:
        out.extend(bd.CELLS.get((m, think, arm), []))
    return out


def fig_token_quadrant(save_name: str) -> Path:
    """The lead token visual: tokens-vs-success quadrant, one panel per task.
    x = mean TOTAL tokens/trial (log), y = success %; an arrow per ≥9B model
    from no-tools → +tool(steered). Every arrow that goes up-and-right reads
    'pay ~4× the tokens, buy the success gap' — cost and quality in one view,
    so the consumption multiple can't be quoted without its return."""
    fig, axes = plt.subplots(1, len(ALL_TASKS), figsize=(13.2, 3.4), sharey=True)
    for ax, task in zip(axes, ALL_TASKS):
        ax.set_axisbelow(True)
        for m in MODELS_9B:
            st0 = bd.token_stats(bd.CELLS.get((m, THINK, "nt-neut"), []), task)
            st1 = bd.token_stats(bd.CELLS.get((m, THINK, "tl-ster"), []), task)
            c0 = cell_success(m, task, "nt-neut")
            c1 = cell_success(m, task, "tl-ster")
            if not (st0["n"] and st1["n"] and c0.n and c1.n):
                continue
            x0, y0 = st0["total"], c0.rate * 100
            x1, y1 = st1["total"], c1.rate * 100
            col = MODEL_COLOR[m]
            ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=3,
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6,
                                        shrinkA=4, shrinkB=4, alpha=0.9))
            ax.scatter([x0], [y0], s=26, color="white", edgecolor=col,
                       linewidth=1.4, zorder=4)
            ax.scatter([x1], [y1], s=30, color=col, edgecolor="white",
                       linewidth=0.8, zorder=4,
                       label=MODEL_DISP[m] if task == ALL_TASKS[0] else None)
        ax.set_xscale("log")
        ax.set_xlim(500, 60000)
        ax.set_ylim(-4, 106)
        ax.set_title(TASK_DISP[task], fontsize=9.5)
        ax.set_xlabel("tokens/trial (log)", fontsize=8)
        ax.grid(True, which="major", axis="both")
        _despine(ax)
    axes[0].set_ylabel("success rate (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.07), fontsize=8)
    fig.suptitle("What the tokens buy — total tokens/trial vs success, "
                 f"arrows run no-tools (open) to +tool steered (filled)  ·  ≥9B, think={THINK}",
                 fontsize=11, fontweight="bold", color=C_INK, y=1.04)
    fig.tight_layout()
    return _save(fig, save_name)


def fig_token_profile(save_name: str) -> Path:
    """The input/output inversion, shown instead of asserted: stacked mean
    input (prompt) + output (completion) tokens per trial, per task × arm,
    pooled over the ≥9B models. no-tools is output-dominated; the tool arms
    are input-dominated (re-fed schemas + tool outputs across turns)."""
    fig, ax = plt.subplots(figsize=(10.6, 4.0))
    ax.set_axisbelow(True)
    w = 0.26
    x = np.arange(len(ALL_TASKS))
    for i, arm in enumerate(ARMS):
        ins, outs = [], []
        for task in ALL_TASKS:
            st = bd.token_stats(_pooled_rows(MODELS_9B, arm), task)
            ins.append(st["prompt"] if st["n"] else np.nan)
            outs.append(st["completion"] if st["n"] else np.nan)
        xs = x + (i - 1) * w
        ax.bar(xs, ins, w, color=ARM_COLOR[arm], edgecolor="white",
               linewidth=0.5, zorder=3, label=f"{ARM_DISP[arm]} — input")
        ax.bar(xs, outs, w, bottom=ins, color=ARM_COLOR[arm], alpha=0.38,
               edgecolor="white", linewidth=0.5, zorder=3,
               label=f"{ARM_DISP[arm]} — output")
        for xi, (p, c) in zip(xs, zip(ins, outs)):
            if p != p:
                continue
            ratio = p / c if c else float("inf")
            ax.text(xi, p + (c if c == c else 0) + 320, f"{ratio:.1f}:1",
                    ha="center", va="bottom", fontsize=6.6, color=C_SOFT,
                    rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels([TASK_DISP[t] for t in ALL_TASKS])
    ax.set_ylabel("mean tokens / trial")
    ax.set_title("Tools invert the token profile — input (solid) vs output (pale); "
                 f"label = input:output ratio  ·  ≥9B pooled, think={THINK}")
    ax.legend(loc="upper right", ncol=3, fontsize=7)
    ax.grid(axis="y")
    _despine(ax)
    return _save(fig, save_name)


def fig_cop_dumbbell(save_name: str, regimes: bool = True) -> Path:
    """Cost-of-pass as a dumbbell chart grouped by baseline regime — the
    grouping IS the finding: where the no-tools baseline is strong the tool
    costs MORE per success; where it is floored the tool is cheaper (solve) or
    the only producer of successes at all (simulate, no-tools unpriceable).

    `regimes=False` (think=on): the per-TASK banners are dropped — under
    reasoning mode the regime is per-MODEL (35B's baseline survives the budget,
    9B/Gemma's drown), so a task-level banner would mislead; the slide caption
    carries that story instead."""
    strong = ["validate_domain", "validate_problem", "validate_plan"]
    floored = ["solve", "simulate"]
    order = strong + floored
    fig, ax = plt.subplots(figsize=(9.8, 5.2))
    ax.set_axisbelow(True)
    yticks, ylabels = [], []
    y = 0
    for gi, task in enumerate(order):
        for m in MODELS_9B:
            nt = cell_cost_of_pass(m, task, "nt-neut")
            st = cell_cost_of_pass(m, task, "tl-ster")
            if st.n_succ:
                ax.scatter([st.cop], [y], s=46, color=ARM_COLOR["tl-ster"],
                           edgecolor="white", linewidth=0.8, zorder=4)
            if nt.n_succ and st.n_succ:
                ax.plot([nt.cop, st.cop], [y, y], color=C_SPINE, lw=1.3, zorder=2)
            if nt.n_succ:
                ax.scatter([nt.cop], [y], s=46, color=ARM_COLOR["nt-neut"],
                           edgecolor="white", linewidth=0.8, zorder=4)
            else:
                ax.annotate("no-tools never succeeds (cost = ∞)", (st.cop, y),
                            xytext=(8, -2), textcoords="offset points",
                            fontsize=6.6, color=C_SOFT, va="center")
            yticks.append(y)
            ylabels.append(f"{TASK_DISP[task]} · {MODEL_DISP[m]}")
            y += 1
        if task != order[-1]:
            ax.axhline(y - 0.5, color=C_RULE, lw=0.8, zorder=1)
        y += 0.4
    # regime banners (think=off only — see docstring)
    if regimes:
        n_strong = len(strong) * len(MODELS_9B) + 0.4 * (len(strong) - 1)
        ax.axhspan(-0.5, n_strong - 0.5 + 0.2, color="#B0413E", alpha=0.04, zorder=0)
        ax.axhspan(n_strong - 0.5 + 0.2, y - 0.9, color="#2E7D52", alpha=0.05, zorder=0)
        ax.text(0.99, 0.985, "baseline strong: tool costs more per success",
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                style="italic", color="#9E3B38")
        ax.text(0.02, 0.30, "baseline floored: tool cheaper, or the only\nway to get a success at all",
                transform=ax.transAxes, ha="left", va="top", fontsize=8,
                style="italic", color="#1F6B43")
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("cost-of-pass — total tokens per success (log; lower = better)")
    ax.set_title(f"Cost-of-pass — no-tools (grey) vs +tool steered (orange)  ·  ≥9B, think={THINK}")
    ax.grid(axis="x", which="major")
    _despine(ax)
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
AMBER_TINT, AMBER_INK = _rgb("#F6ECD9"), _rgb("#8A5E14")  # MIXED verdict chip

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
                  notes: str | None = None, badge: tuple | None = None) -> None:
    slide = _blank(prs)
    _chrome(slide, title, badge=badge)
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


def S_hook_slide(prs, title: str, stats: list[tuple[str, str]], lead: str,
                 closing: str) -> None:
    """Opening hook: a row of oversized stat blocks (value + label) between a
    lead line and a closing line — the one-glance version of the result."""
    slide = _blank(prs)
    _chrome(slide, title)
    lb = slide.shapes.add_textbox(MARGIN, BODY_TOP, SLIDE_W - 2 * MARGIN, Inches(0.6))
    lp = lb.text_frame.paragraphs[0]
    lb.text_frame.word_wrap = True
    lr = lp.add_run()
    lr.text = lead
    lr.font.size = Pt(16)
    lr.font.color.rgb = INK
    n = len(stats)
    block_w = (SLIDE_W_IN - 2 * MARGIN_IN - 0.3 * (n - 1)) / n
    for i, (value, label) in enumerate(stats):
        x = MARGIN_IN + i * (block_w + 0.3)
        vb = slide.shapes.add_textbox(Inches(x), Inches(2.55), Inches(block_w), Inches(1.5))
        vp = vb.text_frame.paragraphs[0]
        vp.alignment = PP_ALIGN.CENTER
        vr = vp.add_run()
        vr.text = value
        vr.font.size = Pt(54)
        vr.font.bold = True
        vr.font.color.rgb = (SOFT if i == 0 else ACCENT)
        cb = slide.shapes.add_textbox(Inches(x), Inches(3.95), Inches(block_w), Inches(0.9))
        ctf = cb.text_frame
        ctf.word_wrap = True
        cp = ctf.paragraphs[0]
        cp.alignment = PP_ALIGN.CENTER
        cr = cp.add_run()
        cr.text = label
        cr.font.size = Pt(13)
        cr.font.color.rgb = SOFT
    eb = slide.shapes.add_textbox(MARGIN, Inches(5.3), SLIDE_W - 2 * MARGIN, Inches(1.4))
    etf = eb.text_frame
    etf.word_wrap = True
    ep = etf.paragraphs[0]
    er = ep.add_run()
    er.text = closing
    er.font.size = Pt(15)
    er.font.color.rgb = INK


def _delta_tint(text: str):
    """Tint semantic cells. Returns (fill, ink) or None.

    Three families of keys, mutually exclusive across the deck's tables:
    - scorecard verdict chips: exact YES / NO / MIXED;
    - token-table direction words: 'cheaper'/'fewer tokens'/'more right' →
      green, 'costlier'/'more tokens'/'less right' → red (plain words instead
      of the old ↑/↓ glyphs, whose arrow direction fought the colour);
    - signed-significant Δ cells: '*' with the sign giving the direction."""
    t = text.strip()
    if t in ("YES", "NO", "MIXED"):
        return {"YES": (GREEN_TINT, GREEN_INK), "NO": (RED_TINT, RED_INK),
                "MIXED": (AMBER_TINT, AMBER_INK)}[t]
    # cross-mode (--think compare) class chips — exclusive to the compare deck
    if "budget-dep" in text:
        return AMBER_TINT, AMBER_INK
    if "robust" in text or "sole-source" in text:
        return GREEN_TINT, GREEN_INK
    if any(k in text for k in ("cheaper", "fewer tokens", "more right")):
        return GREEN_TINT, GREEN_INK
    if any(k in text for k in ("costlier", "more tokens", "less right")):
        return RED_TINT, RED_INK
    if "*" not in text:
        return None
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
        lr.text = FOOTER_TEXT + f" · think={THINK}"
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

def _cf(c: Cell) -> str:
    return f"{c.rate*100:.0f} [{c.lo*100:.0f},{c.hi*100:.0f}]" if c.n else "–"


def _gf(g: dict) -> str:
    mark = "*" if g["significant"] else ""
    return f"{g['gap']:+.0f}{mark}" if g["gap"] == g["gap"] else "–"


def _arm_table(task: str, models: list[str] | None = None
               ) -> tuple[list[str], list[list[str]]]:
    headers = ["model", "no-tools", "+tool(plain)", "+tool(steered)",
               "avail Δ", "steer Δ"]
    rows = []
    for m in (models or CHART_MODELS):
        nt = cell_success(m, task, "nt-neut")
        pl = cell_success(m, task, "tl-neut")
        st = cell_success(m, task, "tl-ster")
        av = signed_gap(m, task, "nt-neut", "tl-neut")
        sv = signed_gap(m, task, "tl-neut", "tl-ster")
        rows.append([MODEL_DISP[m], _cf(nt), _cf(pl), _cf(st), _gf(av), _gf(sv)])
    return headers, rows


def _small_model_table() -> tuple[list[str], list[list[str]]]:
    """0.8B across all 5 tasks × 3 arms — the caveat slide's evidence. The
    smallest model is the only one where tool availability REVERSES sign."""
    headers = ["task", "no-tools", "+tool(plain)", "+tool(steered)",
               "avail Δ", "steer Δ"]
    rows = []
    for task in ALL_TASKS:
        nt = cell_success(SMALL_MODEL, task, "nt-neut")
        pl = cell_success(SMALL_MODEL, task, "tl-neut")
        st = cell_success(SMALL_MODEL, task, "tl-ster")
        av = signed_gap(SMALL_MODEL, task, "nt-neut", "tl-neut")
        sv = signed_gap(SMALL_MODEL, task, "tl-neut", "tl-ster")
        rows.append([TASK_DISP[task], _cf(nt), _cf(pl), _cf(st), _gf(av), _gf(sv)])
    return headers, rows


def _rq_head_task(rq: str) -> str:
    tasks = RQ_TASKS[rq]
    return tasks[-1] if rq == "RQ0.1" else tasks[0]


def _phase1_verdict(rq: str) -> tuple[str, dict, dict]:
    """Computed signed verdict + the two claim tallies for one phase-1 RQ.
    For think=off the verdict is asserted against the LOCKED scorecard; for
    think=on the same rule runs but the result is computed, not locked."""
    head = _rq_head_task(rq)
    avail = claim_counts(head, "nt-neut", "tl-neut", MODELS_9B)
    steer = claim_counts(head, "tl-neut", "tl-ster", MODELS_9B)
    verdict = derive_verdict(avail)
    if THINK == "off":
        assert verdict == RQ_VERDICT[rq], (
            f"{rq}: computed verdict {verdict} != locked scorecard {RQ_VERDICT[rq]} "
            f"(avail fav={avail['fav_sig']} against={avail['against_sig']})")
    return verdict, avail, steer


def _phase2_headroom_task(key: str) -> str:
    """The headroom-gated task whose gap trend carries the RQ0.5/0.6 verdict.
    think=off: validate_plan / validate_problem (locked analysis). think=on:
    the budget moves the headroom — solve's baseline declines with length while
    the tool holds, so solve is the rq05 case; validate_problem stays for rq06."""
    if key == "rq05":
        return "validate_plan" if THINK == "off" else "solve"
    return "validate_problem"


def _phase2_verdict(summary: dict, key: str) -> str:
    """YES when any task's gap WIDENS materially with difficulty (last−first
    ≥10pp without an initial dip), else NO. Reproduces the locked think=off
    verdicts (rq05 YES via validate_plan +5→+27; rq06 NO, all flat) and is
    asserted against them on the off build."""
    tasks = [k.split("/", 1)[1] for k in summary if k.startswith(key + "/")]
    widens = any(
        (summary[f"{key}/{t}"]["gaps"][2] - summary[f"{key}/{t}"]["gaps"][0]) >= 10
        and summary[f"{key}/{t}"]["gaps"][1] >= summary[f"{key}/{t}"]["gaps"][0] - 2
        for t in tasks)
    verdict = "YES" if widens else "NO"
    if THINK == "off":
        locked = {"rq05": "YES", "rq06": "NO"}[key]
        assert verdict == locked, f"{key}: computed {verdict} != locked {locked}"
    return verdict


def _scorecard_rows(summary: dict) -> list[list[str]]:
    """One row per RQ: verdict chip + a computed one-line evidence summary.
    Verdicts come from the same signed rule the Answer slides use (locked +
    asserted on think=off, computed on think=on)."""
    rows = []
    v, ev = {}, {}
    for rq in RQ_TASKS:
        verdict, a, _ = _phase1_verdict(rq)
        v[rq] = verdict
        ev[rq] = (f"availability {a['gap_min']:+.0f}…{a['gap_max']:+.0f}pp; "
                  f"{a['fav_sig']}/3 sig-for, {a['against_sig']}/3 sig-against")
    t5 = _phase2_headroom_task("rq05")
    t6 = _phase2_headroom_task("rq06")
    d5, d6 = summary[f"rq05/{t5}"], summary[f"rq06/{t6}"]
    rows.append(["RQ0.1", "does the tool help validate domain/problem files?", v["RQ0.1"], ev["RQ0.1"]])
    rows.append(["RQ0.2", "does the tool help SOLVE?", v["RQ0.2"], ev["RQ0.2"]])
    rows.append(["RQ0.3", "does the tool help check a plan?", v["RQ0.3"], ev["RQ0.3"]])
    rows.append(["RQ0.4", "does the tool help track state (simulate)?", v["RQ0.4"], ev["RQ0.4"]])
    v5 = _phase2_verdict(summary, "rq05")
    v6 = _phase2_verdict(summary, "rq06")
    rows.append(["RQ0.5", "does the advantage grow with plan length?", v5,
                 f"{t5} gap " + ("widens " if v5 == "YES" else "flat ")
                 + " → ".join(f"{d5['gaps'][b]:+.0f}" for b in range(3)) + "pp"])
    rows.append(["RQ0.6", "does the advantage track object count?", v6,
                 f"{t6} gap " + ("widens " if v6 == "YES" else "flat ")
                 + "(" + " / ".join(f"{d6['gaps'][b]:+.0f}" for b in range(3)) + "pp)"])
    return rows


def build_pptx(summary: dict, gate_lines: list[str]) -> Path:
    prs = bd._make_pptx()
    on = THINK == "on"

    # --- title ---
    S_title_slide(
        prs,
        "Does a planning tool help LLMs on PDDL tasks?" if not on else
        "Does the planning tool survive reasoning mode? — think=on",
        "5 language models · 5 PDDL planning tasks · with vs. without a real "
        "planner/validator tool · success rates with 95% confidence intervals"
        + (" · think=on companion to the think=off headline deck" if on else ""))

    # --- hook: the single most dramatic result, before any methodology ---
    if not on:
        sim_nt = [cell_success(m, "simulate", "nt-neut") for m in MODEL_ORDER]
        sim_pl = [cell_success(m, "simulate", "tl-neut") for m in MODELS_9B]
        sim_st = [cell_success(m, "simulate", "tl-ster") for m in MODELS_9B]
        nt_n = sum(c.n for c in sim_nt)
        nt_max = max(c.rate for c in sim_nt if c.n) * 100
        S_hook_slide(
            prs, "The headline result — simulate",
            [(f"{nt_max:.0f}%", f"no-tools — every model, all {nt_n:,} trials"),
             (f"{min(c.rate for c in sim_pl)*100:.0f}–{max(c.rate for c in sim_pl)*100:.0f}%",
              "tool merely available (≥9B)"),
             (f"{min(c.rate for c in sim_st)*100:.0f}–{max(c.rate for c in sim_st)*100:.0f}%",
              "tool + one steering sentence (≥9B)")],
            "Tracking world state through a plan — the simulate task — simply does not "
            "happen without the tool:",
            "solve is nearly as stark: 8–11% without the tool, 63–99% with it. The rest of "
            "this deck quantifies that pattern across all five tasks — and what it costs in tokens.")
    else:
        # the think=on hook is the budget: the unaided model reasons past the cap
        trunc = []
        for task in ALL_TASKS:
            sub = [r for r in _pooled_rows(MODELS_9B, "nt-neut") if r["task"] == task]
            trunc.append(sum(1 for r in sub if r.get("truncated")) / len(sub) * 100)
        vp_off = cell_success("Qwen3_5_9B", "validate_plan", "nt-neut", "off")
        vp_on = cell_success("Qwen3_5_9B", "validate_plan", "nt-neut", "on")
        vp_st = cell_success("Qwen3_5_9B", "validate_plan", "tl-ster", "on")
        S_hook_slide(
            prs, "The headline result — the baseline reasons itself to death",
            [(f"{min(trunc):.0f}–{max(trunc):.0f}%",
              "of no-tools think=on trials hit the 8,192-token cap (≥9B, by task)"),
             (f"{vp_off.rate*100:.0f}% → {vp_on.rate*100:.0f}%",
              "validate_plan, Qwen3.5-9B — no-tools success, think=off → think=on"),
             (f"{vp_st.rate*100:.0f}%",
              "the same think=on cell with the tool + nudge")],
            "Reasoning mode shares one 8,192-token decode budget with the answer — and the "
            "unaided model spends it thinking instead of answering:",
            "The exception is solve, where reasoning genuinely helps the unaided baseline "
            "(9B 11→27%, 35B 9→38% vs think=off). Everywhere else the tool arms barely "
            "notice reasoning mode — the tool call replaces the long derivation. Every "
            "think=on number is budget-confounded; the think=off deck is the clean read.")

    # --- executive scorecard: all six verdicts on one slide, up front ---
    S_table_slide(
        prs, "Scorecard — six research questions, six verdicts",
        ["RQ", "question", "verdict", f"evidence (≥9B, think={THINK})"],
        _scorecard_rows(summary),
        notes=("Verdicts are locked and asserted against the computed signed CI counts at "
               "build time." if not on else
               "Verdicts computed by the SAME signed-CI rule as the locked think=off deck "
               "(not independently locked). The verdict pattern matches think=off — but the "
               "availability gaps are inflated by the truncation-collapsed no-tools baseline.")
        + " Availability = +tool(plain) vs no-tools on the headline task of each "
        "RQ; RQ0.5/0.6 from the phase-2 difficulty bins (no-tools vs +tool steered).")

    # --- plain-language onboarding: give a reader who has never seen this
    #     experiment the context + a decoder for the short labels used later. ---
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

    S_text_slide(prs, "How to read the results", [
        "• success rate — how often the model's answer matched the known-correct answer, 0–100%. It is the "
        "only score shown; arms are scored separately and never pooled.",
        "• Error bars (charts) and [low, high] brackets (tables) are Wilson 95% confidence intervals. When two "
        "ranges don't overlap, the difference is real rather than noise; a “*” on a gap marks exactly that. "
        "Green = the tool helped, red = the tool hurt.",
        "• “≥9B” — headline conclusions use the larger models (Qwen3.5-9B, Gemma-MoE-26B, Qwen3.6-35B); "
        "Qwen3.5-4B is shown for context and the 0.8B failure mode gets its own slide.",
        ("• “think=off” — the model answers directly. think=on (reasons first) is a caveat slide, not the headline."
         if not on else
         "• “think=on” — the model reasons before answering, and reasoning + answer SHARE one 8,192-token "
         "decode budget. Every number in this deck sits under that budget (next slide); the think=off deck "
         "is the clean, unconfounded read."),
        "• “difficulty bins” (RQ0.5/0.6) — problems split into easy / medium / hard thirds, no-tools vs tool + "
        "nudge, to see whether the tool's advantage changes as problems get harder.",
        "• A contamination re-run on disguised problems (sweep-6) left the no-tools baseline unchanged (footnote).",
    ])

    # --- think=on: the budget cliff is the reading frame, so it comes FIRST ---
    if on:
        cliff = fig_think_on_cliff("think_on_cliff.png")
        S_image_slide(
            prs, "Read this first — every think=on number sits under a shared decode budget",
            cliff,
            caption="Left: solve tool-use rate — neutral think=on collapses tool-calling vs think=off "
            "(Gemma-MoE-26B 100→23, Qwen3.5-9B 100→59); steering partly restores it. Right: solve truncation "
            "spikes under think=on. Consequence for everything that follows: the no-tools baseline often burns "
            "the whole 8,192-token budget reasoning and never answers, so availability gaps are inflated by "
            "baseline truncation — budget exhaustion, not ability.")

    # --- the verdict rule deserves its own beat: direction, not just disjointness ---
    g_gem = signed_gap("gemma4_26b-a4b", "validate_plan", "nt-neut", "tl-neut")
    S_text_slide(prs, "Why the verdicts count direction — signed significance", [
        "A gap counts toward a YES only when the two arms' 95% intervals are disjoint AND the gap points the "
        "hypothesised way (the tool helps). Significant gaps pointing the other way are tallied separately as "
        "significant-AGAINST — they are findings, not noise.",
        "",
        f"• The case that makes this matter: on validate_plan, merely making the tool available moves "
        f"Gemma-MoE-26B by {g_gem['gap']:+.0f}pp — significant, and AGAINST the tool ("
        + ("it stops answering)." if not on else
           "it reasons instead of calling the tool — tool_selected ≈1% — and answers almost nothing)."),
        "• A sign-blind test would count that gap as evidence the tool 'has an effect' and read RQ0.3 as YES. "
        "The signed rule reads it as MIXED — which is what the data actually says.",
        ("• The build asserts the computed signed verdicts equal the locked scorecard, so the deck cannot "
         "silently drift from this rule." if not on else
         "• think=on verdicts are computed by this same rule at build time; only the think=off verdicts are "
         "locked. That the pattern (YES/YES/MIXED/YES) reproduces under reasoning mode is itself a finding."),
    ])

    # --- RQ0.1–0.4 ---
    # The RQ0.3 gate (validate_plan tool-calling artifact) is emitted INSIDE the
    # RQ0.3 section, right before its evidence chart — it is the reading-guide for
    # the surprising low +tool(plain) bar, so it belongs next to it, not orphaned
    # up front after Methods.
    for rq, tasks in RQ_TASKS.items():
        _add_phase1_rq(prs, rq, tasks, summary, gate_lines)

    # --- small-model caveat: 0.8B pulled out of the main charts, shown once ---
    sm_h, sm_r = _small_model_table()
    S_table_slide(
        prs,
        "Small-model caveat — Qwen3.5-0.8B mishandles the tool" if not on else
        "Small-model record — Qwen3.5-0.8B under think=on",
        sm_h, sm_r,
        notes=("The smallest model is the only one where tool AVAILABILITY reverses sign "
               "(validate_problem −25pp*, validate_plan −27pp*): it cannot drive the tool-call "
               "protocol, so the tool becomes a distraction. Every headline conclusion is ≥9B; "
               "the YES verdicts hold from 4B up." if not on else
               "Under think=on the 0.8B no-tools baseline is at the floor on every task (it reasons "
               "past the budget), so the think=off availability REVERSALS disappear — there is no "
               "baseline left to lose. The tool lifts it modestly where it can still drive the call "
               "protocol. Headline conclusions remain ≥9B.")
        + " Excluded from the main charts to keep them readable — this slide is its complete record.")

    # --- cross-cutting token cost + efficiency lens ---
    # Sits after the RQ0.1–0.4 success blocks (it reframes the same phase-1 tasks
    # through token consumption). Figures lead; full tables live in the backup.
    _add_token_section(prs)

    # --- think=on caveat (off deck only — the on deck opened with the cliff) ---
    if not on:
        cliff = fig_think_on_cliff("think_on_cliff.png")
        S_image_slide(
            prs, "Caveat — think=on is a decode-budget cliff (Gemma-MoE-26B & 9B hardest)",
            cliff,
            caption="Left: solve tool-use rate across budget states — neutral think=on collapses tool-calling vs "
            "think=off, worst on Gemma-MoE-26B (100→23) and Qwen3.5-9B (100→59), NOT strictly the smallest model "
            "(0.8B 97→46); steering partly restores it. Right: solve truncation rate spikes under think=on. The "
            "headline uses think=off; the think=on degradation is budget exhaustion, not ability.")

    # --- RQ0.5 (question folded into the Answer slide) ---
    rq05 = fig_phase2(summary, "rq05",
                      ["solve", "validate_plan", "simulate"],
                      "RQ0.5 — does the tool advantage change with PLAN LENGTH? "
                      f"(no-tools vs +tool steered, ≥9B, think={THINK})", "phase2_rq05.png")
    t5 = _phase2_headroom_task("rq05")
    d5 = summary[f"rq05/{t5}"]
    if not on:
        rq05_answer = "YES for validate_plan — the advantage GROWS with plan length."
        rq05_bullets = [
            "validate_plan is the headroom-gated case (both arms have room to move): the "
            "no-tools − tool gap widens from +5pp (short plans) to +27pp (long plans) as no-tools "
            "degrades while the tool holds. This is the generalisation claim: the harder the "
            "instance, the more the tool is worth.",
            "solve and simulate are framed as tool-arm robustness: no-tools is floored (~0–12%) at "
            "every length, so the ~87–99pp gap is large but does not 'grow' — there is no no-tools "
            "headroom to lose."]
    else:
        rq05_answer = "YES — and under think=on the headroom case moves to SOLVE."
        rq05_bullets = [
            f"solve is now headroom-gated: reasoning gives the unaided baseline a real solve rate on short "
            f"plans ({d5['nt'][0][0]:.0f}%) that fades with length ({d5['nt'][1][0]:.0f}→{d5['nt'][2][0]:.0f}%), "
            f"while the tool arm holds ({d5['tl'][0][0]:.0f}→{d5['tl'][2][0]:.0f}%) — the gap widens "
            f"{d5['gaps'][0]:+.0f}→{d5['gaps'][2]:+.0f}pp. Open-ended reasoning runs out of budget exactly "
            "where plans get long; the tool does not.",
            "validate_plan widens mildly (+38→+45pp); simulate stays tool-arm-only (no-tools floored at 0%)."]
    _add_phase2_rq(prs, "RQ0.5", "Does the planning tool's advantage CHANGE as instances get harder "
                   "(longer reference / plan length)?",
                   rq05_answer, rq05_bullets, rq05, summary, "rq05",
                   ["solve", "validate_plan", "simulate"])

    # --- RQ0.6: a null result gets ONE slide (figure + verdict badge); its
    #     difficulty-bin table moves to the backup. ---
    rq06 = fig_phase2(summary, "rq06",
                      ["solve", "validate_problem", "validate_plan", "simulate"],
                      "RQ0.6 — does the tool advantage change with OBJECT COUNT? "
                      f"(no-tools vs +tool steered, ≥9B, think={THINK})", "phase2_rq06.png")
    d6 = summary["rq06/validate_problem"]
    v6 = _phase2_verdict(summary, "rq06")
    S_image_slide(
        prs, "RQ0.6 — object count does not move the advantage", rq06,
        badge=(v6, VERDICT_COLOR[v6]),
        caption="Headroom case (validate_problem): gap "
        + " → ".join(f"{d6['labels'][b]}: Δ{d6['gaps'][b]:+.0f}" for b in range(3))
        + "pp — essentially flat; the other tasks are also flat (no-tools floored or already "
        "separated). Object count is not a difficulty axis the tool's advantage tracks. "
        "Full bin table in the backup.")

    # --- robustness footnote (sweep-6) ---
    S_text_slide(prs, "Robustness footnote — contamination probe (sweep-6)", [
        "• A separate anonymised-corpus sweep (sweep-6) re-ran the matrix on structurally-identical domains "
        "with every surface name renamed, to test memorisation.",
        "• Headline (think=off): the clean no-tools-neutral probe is near-null — Δ(canonical − anon) success "
        "≤1.3pp mean |Δ|, zero CI-disjoint task cells. No broad train-set contamination of the pure-model "
        "baseline where it has headroom.",
    ] + (["• Implication for this deck: the no-tools baselines that the tool's value is measured against are not "
          "inflated by memorisation, so the availability gaps reported here are not a contamination artifact.",
          ] if not on else
         ["• think=on caveat: the probe's only CI-disjoint cells (validate_plan, think=on) were a TOKENISATION "
          "artifact — anonymised prompts ran ~5% longer, so more trials truncated under the shared budget; "
          "success-given-completion was equal. Not memorisation — but a live demonstration of how budget "
          "exhaustion, not ability, moves think=on numbers.",
          ]))

    # --- out-of-scope ---
    S_text_slide(prs, "Out of scope (phase-3)", [
        "• Cross-benchmark generalisation (PlanBench) and comparison to published SOTA formalizer baselines "
        "(e.g. Huang & Zhang, ACL 2025) are deliberately OUT OF SCOPE for this single-tool-use deck.",
        "• This deck answers: within our 5-model × 5-task matrix, does giving the model a planning/validation "
        "tool (and steering it to use the tool) raise success, and does that advantage track difficulty?",
    ])

    # --- backup: the full per-model token tables + RQ0.6 bins ---
    _add_backup_section(prs, summary)

    _finalize_footers(prs)
    PPTX_OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(PPTX_OUT))
    return PPTX_OUT


def _add_gate_slide(prs, gate_lines: list[str]) -> None:
    """The RQ0.3 reading-guide: +tool(plain)'s low raw-success on validate_plan is
    a tool-calling artifact (no verdict emitted), not a verdict collapse. Placed
    immediately before the RQ0.3 evidence chart it explains."""
    S_text_slide(prs, "Reading guide — the low +tool(plain) bar is silence, not error",
                 ["On validate_plan the +tool(plain) arm often produces NO verdict at all — the model "
                  "fails to call the tool and answers nothing. When it does answer, it is near-perfect:"]
                 + [f"• {ln}" for ln in gate_lines]
                 + ["→ So the collapse is a tool-CALLING failure, not a verdict failure — and steering, "
                    "which raises tool-calling, repairs it (mechanism slide after the evidence)."])


def _add_phase1_rq(prs, rq: str, tasks: list[str], summary: dict,
                   gate_lines: list[str]) -> None:
    task_label = " + ".join(TASK_DISP[t] for t in tasks)
    question = {
        "RQ0.1": "Does giving the model a validation tool help it validate PDDL domains and problems?",
        "RQ0.2": "Does giving the model a planning tool help it SOLVE PDDL problems?",
        "RQ0.3": "Does giving the model a validation tool help it CHECK whether a plan is valid?",
        "RQ0.4": "Does giving the model a simulation tool help it TRACK state (simulate a plan)?",
    }[rq]

    # (1) answer slide — question folded in as the lead line, signed verdict badge
    head_task = _rq_head_task(rq)
    verdict, avail9, steer9 = _phase1_verdict(rq)
    bullets = [
        f"{question}  ({task_label})",
        "",
        f"• Availability ({TASK_DISP[head_task]}, ≥9B): gap {avail9['gap_min']:+.0f}…{avail9['gap_max']:+.0f}pp; "
        f"{avail9['fav_sig']}/3 favorable-significant, {avail9['against_sig']}/3 significant-against (95% CIs).",
        f"• Steering ({TASK_DISP[head_task]}, ≥9B): gap {steer9['gap_min']:+.0f}…{steer9['gap_max']:+.0f}pp; "
        f"{steer9['fav_sig']}/3 favorable-significant.",
    ]
    bullets += _rq_headline_notes(rq)
    S_text_slide(prs, f"{rq} — {task_label}", bullets,
                 badge=(verdict, VERDICT_COLOR[verdict]))

    # (1.5) RQ0.3 gate — reading-guide for the low +tool(plain) bar, right before it
    if rq == "RQ0.3":
        _add_gate_slide(prs, gate_lines)

    # (2) evidence: success-by-arm plot + table, per task
    for task in tasks:
        png = fig_success_by_arm(task, f"{task}.png")
        S_image_slide(
            prs, f"{rq} — Evidence: {TASK_DISP[task]} success by arm", png,
            caption="Grey=no-tools, blue=+tool(plain), orange=+tool(steered). Whiskers=Wilson 95% CI. "
            "Shaded band marks the ≥9B headline set. 0.8B is excluded (own caveat slide).")
        headers, table_rows = _arm_table(task)
        S_table_slide(prs, f"{rq} — {TASK_DISP[task]} success table (rate [Wilson 95%], * = CI-disjoint)",
                      headers, table_rows)

    # (3) mechanism — only where +tool(plain) actually under-calls the tool, so
    # steering has something to repair. Data-driven: skip when every ≥9B model
    # already calls the tool ≥97% of the time on the plain arm (think=off RQ0.1
    # — a mechanism slide there would contradict its own title; under think=on
    # Gemma under-calls even on validation, so the slide returns).
    min_toolsel = min(cell_toolsel(m, head_task, "tl-neut").rate for m in MODELS_9B)
    if min_toolsel < 0.97:
        mech = fig_mechanism(head_task, f"mechanism_{head_task}.png")
        S_image_slide(
            prs, f"{rq} — Mechanism: steering raises tool-calling → raises success",
            mech,
            caption=f"{TASK_DISP[head_task]}, ≥9B. Left: tool-use rate (tool_selected) plain vs steered. "
            "Right: success. Where +tool(plain) under-calls the tool, steering raises tool-calling, and "
            "success rises with it — the tool's value is gated on the model actually invoking it.")


def _rq_headline_notes(rq: str) -> list[str]:
    """Mode-specific headline prose under the computed evidence bullets. The
    think=on notes are written against the think=on corpus numbers (see
    paper_notes 2026-06-10) — do not reuse the off prose there."""
    if THINK == "off":
        return {
            "RQ0.1": ["", "Caveat: at 0.8B the availability gap REVERSES on validate_problem (−25pp) — the "
                      "smallest model mishandles the tool (see the small-model slide). YES holds from 4B up."],
            "RQ0.2": ["", "Decisive: no-tools is floored (~8–11%); +tool lifts ≥9B to 63–99%. Steering adds a "
                      "large further lift where plain left headroom (Qwen3.6-35B +29pp)."],
            "RQ0.3": ["", "MIXED: the model alone is already strong on validate_plan (75–90%). At +tool(plain) the "
                      "availability gap is significant-AGAINST for Gemma-MoE (−67pp: it stops answering) and "
                      "Qwen3.6-35B (−9pp); only Qwen3.5-9B is favorable. Steering RECOVERS and beats no-tools "
                      "(Gemma 21→93%), but the net tool benefit over a strong baseline is small/mixed."],
            "RQ0.4": ["", "Decisive: no-tools is 0% everywhere (state-tracking by hand fails); +tool reaches "
                      "65–92% on ≥9B, with steering adding +18–22pp."],
        }[rq]
    return {
        "RQ0.1": ["", "The no-tools baseline COLLAPSES under reasoning mode (validate_domain: 9B 26→3%, "
                  "Gemma 78→0% vs think=off; 55–65% of baseline trials truncate), so the huge availability "
                  "gaps are baseline-confounded — the honest read is that the tool arms are nearly immune "
                  "to reasoning mode (≥9B steered 87–98%) while the unaided model is not. The 0.8B reversal "
                  "from think=off disappears: its baseline is at the floor too."],
        "RQ0.2": ["", "solve is the one task where reasoning HELPS the unaided baseline (9B 11→27%, 35B "
                  "9→38% vs think=off). Tools still add +19…+40pp, and steering is now significant on all "
                  "three models (Gemma 23→74%): under the shared budget, plain tool-calling is fragile — "
                  "the model reasons instead of calling — and the nudge repairs it."],
        "RQ0.3": ["", "Still MIXED, more extreme: Gemma's plain arm collapses to 0.6% (tool_selected ≈1% — "
                  "it reasons instead of calling; gate slide next). Steering recovers it to 44% — still BELOW "
                  "its own think=off no-tools 88%. The strong unaided baseline that made this RQ mixed at "
                  "think=off is itself destroyed by reasoning (9B 80→21%, Gemma 88→10%); only 35B's survives "
                  "(85%) and it is the one favourable-but-small cell."],
        "RQ0.4": ["", "Identical to think=off in kind: no-tools is 0% everywhere — reasoning does not buy "
                  "state-tracking, it just burns the budget (83% truncation). +tool reaches 44–96% plain; "
                  "steering rescues Gemma (44→91%)."],
    }[rq]


def _mult_str(tool: float, base: float) -> str:
    """A tool arm's success rate as a MULTIPLE of the no-tools baseline, in
    plain words ('more right' green / 'less right' red via `_delta_tint`) —
    the old ↑/↓ glyphs made the reader decode arrow-vs-colour semantics.
    Empty when the baseline is floored (≈0): the ratio is then degenerate (†)."""
    if tool != tool or base != base or base <= 0:
        return ""
    m = tool / base
    if m >= 1.05:
        return f"{m:.1f}× more right"
    if m <= 0.95:
        return f"{m:.1f}× less right"
    return f"{m:.1f}× (same)"


def _task_floored(task: str) -> bool:
    """True when no-tools success ≈ 0 across the ≥9B set — the ratio is then
    degenerate (tool does work per token, baseline ≈none), not a like-for-like
    per-token comparison. Marked † in the table (and the ×multiplier is hidden,
    since dividing by a ≈0 baseline is meaningless)."""
    cells = [cell_efficiency(m, task, "nt-neut") for m in EFF_MODELS]
    cells = [e for e in cells if e.n]
    return bool(cells) and all(e.succ < 0.02 for e in cells)


def _cost_cell(c: CostPerSuccess) -> str:
    """mean [bootstrap 95% CI] action tokens per correct answer; '— (0 succ)'
    when the arm produced no success to price."""
    if c is None or not c.n:
        return "— (0 succ)"
    return f"{bd._fmt_tokens(c.mean)} [{bd._fmt_tokens(c.lo)},{bd._fmt_tokens(c.hi)}]"


def _cost_table(tasks: list[str]) -> tuple[list[str], list[list[str]]]:
    headers = ["task", "model", "no-tools", "+tool(plain)", "+tool(steered)"]
    rows: list[list[str]] = []
    for task in tasks:
        for i, m in enumerate(EFF_MODELS):
            cells = [_cost_cell(cell_cost_per_success(m, task, arm)) for arm in ARMS]
            rows.append([TASK_DISP[task] if i == 0 else "", MODEL_DISP[m], *cells])
    return headers, rows


def _cost_mult_str(tool: float, base: float) -> str:
    """A +tool arm's TOKEN COST as a multiple of the no-tools baseline, in plain
    words. LOWER is better: 'cheaper' (green via `_delta_tint`) / 'costlier'
    (red) / '(same)' within ±5%. The number is the raw cost multiple
    (2.8× = the tool spends 2.8× the tokens); the word carries good/bad, so no
    arrow-vs-colour decoding is needed."""
    if tool != tool or base != base or base <= 0 or tool <= 0:
        return ""
    m = tool / base
    fmt = f"{m:.2f}×" if m < 0.1 else f"{m:.1f}×"  # 0.01× not a rounded-to-zero "0.0×"
    if m <= 0.95:
        return f"{fmt} cheaper"
    if m >= 1.05:
        return f"{fmt} costlier"
    return f"{fmt} (same)"


def _tokcost_cell(st: dict, base_total: float | None = None) -> str:
    """One arm's mean total tokens/trial, shown as total (input+output); a +tool
    arm also gets ×vs-no-tools on total (pass base_total)."""
    if not st["n"] or st["total"] != st["total"]:
        return "–"
    s = (f"{bd._fmt_tokens(st['total'])} "
         f"({bd._fmt_tokens(st['prompt'])}+{bd._fmt_tokens(st['completion'])})")
    if base_total is not None:
        mult = _cost_mult_str(st["total"], base_total)
        if mult:
            s = f"{s}  {mult}"
    return s


def _cop_cell(c: CostOfPass, base: CostOfPass | None = None) -> str:
    """cost-of-pass = tokens per success [bootstrap 95% CI]; '— (0 succ)' when the
    arm never succeeds. A +tool arm also gets ×vs-no-tools (cost multiple)."""
    if c is None or not c.n_succ or c.cop != c.cop:
        return "— (0 succ)"
    s = f"{bd._fmt_tokens(c.cop)} [{bd._fmt_tokens(c.lo)},{bd._fmt_tokens(c.hi)}]"
    if base is not None and base.n_succ and base.cop == base.cop:
        mult = _cost_mult_str(c.cop, base.cop)
        if mult:
            s = f"{s}  {mult}"
    return s


def _token_cost_table(tasks: list[str]) -> tuple[list[str], list[list[str]]]:
    headers = ["task", "model", "no-tools", "+tool(plain)", "+tool(steered)"]
    rows: list[list[str]] = []
    for task in tasks:
        for i, m in enumerate(EFF_MODELS):
            st_nt = bd.token_stats(bd.CELLS.get((m, THINK, "nt-neut"), []), task)
            st_tl = bd.token_stats(bd.CELLS.get((m, THINK, "tl-neut"), []), task)
            st_st = bd.token_stats(bd.CELLS.get((m, THINK, "tl-ster"), []), task)
            base = st_nt["total"] if st_nt["n"] else None
            rows.append([TASK_DISP[task] if i == 0 else "", MODEL_DISP[m],
                         _tokcost_cell(st_nt),
                         _tokcost_cell(st_tl, base),
                         _tokcost_cell(st_st, base)])
    return headers, rows


def _censoring_table() -> tuple[list[str], list[list[str]]]:
    """Censoring + latency-proxy evidence, ≥9B pooled: per task × arm, the share
    of trials hitting the 8,192 output cap, mean turns (round-trips — the only
    defensible latency proxy on a batched server), and the token means the rest
    of the section quotes."""
    headers = ["task", "arm", "truncated %", "mean turns",
               "output tok/trial", "total tok/trial"]
    rows: list[list[str]] = []
    for task in ALL_TASKS:
        for j, arm in enumerate(ARMS):
            sub = [r for r in _pooled_rows(MODELS_9B, arm) if r["task"] == task]
            n = len(sub)
            tr = (sum(1 for r in sub if r.get("truncated")) / n * 100) if n else float("nan")
            st = bd.token_stats(sub)
            rows.append([TASK_DISP[task] if j == 0 else "", ARM_DISP[arm],
                         f"{tr:.0f}%" if tr == tr else "–",
                         f"{st['turns']:.1f}" if st["n"] else "–",
                         bd._fmt_tokens(st["completion"]) if st["n"] else "–",
                         bd._fmt_tokens(st["total"]) if st["n"] else "–"])
    return headers, rows


def _add_token_section(prs) -> None:
    """The token story, figures first: (1) what tools consume AND what that buys
    (quadrant), (2) why output-only is the wrong denominator (profile inversion),
    (3) quality-adjusted efficiency (cost-of-pass dumbbell by baseline regime),
    (4) the exact decomposition, (5) censoring + the turns latency proxy.
    Full per-model tables live in the backup."""
    on = THINK == "on"
    S_text_slide(prs, "What do tools cost? — token consumption", [
        "Token cost = TOTAL tokens a trial consumes — input (prompt) + output (completion), summed across "
        f"the model's turns. The whole bill, not just generated text. Scope: ≥9B, think={THINK}.",
        ("• Tools raise per-trial consumption ~4–15× — but consumption alone is half the story: the next "
         "figure holds cost and success in one view so neither number is quoted without the other."
         if not on else
         "• Under think=on tools cost only ~2× per trial — not because tools got cheaper, but because the "
         "no-tools baseline now burns ~5–6k output tokens reasoning (and usually truncates). The next figure "
         "holds cost and success in one view."),
        "• Quality-adjusted efficiency is cost-of-pass = total tokens ÷ correct answers: every token burned "
        "on a failed attempt is charged to the successes. LOWER is better.",
        "",
        "→ Caveats: (1) prefix caching (~90% on this roster) makes the re-sent tool INPUT cheap in server "
        "compute — but it is still real context-budget consumption, and tool OUTPUTS across turns are "
        "novel/uncached; the raw total is the honest accounting number. (2) Output is right-censored at the "
        "8,192-token cap with arm-dependent truncation (evidence slide at the end of this section). "
        + ("(3) A completion-only view flatters tools — kept as a labelled secondary lens in the backup."
           if not on else
           "(3) Under think=on, completion = REASONING + answer in one number — the runner logs no "
           "thinking/answer split (vLLM strips the trace server-side), so output tokens cannot be read as "
           "answer length; totals remain the honest bill. The completion-only lens stays in the backup."),
    ])
    S_image_slide(
        prs,
        "What the tokens buy — pay ~4–15× per trial, buy +5…+100pp" if not on else
        "What the tokens buy — pay ~2× per trial, buy +14…+97pp",
        fig_token_quadrant("token_quadrant.png"),
        caption="Each arrow is one ≥9B model on one task, from no-tools ○ to +tool(steered) ● — x = mean "
        "total tokens/trial (log), y = success. "
        + ("Every arrow points up-and-right: the tool always costs more per trial; the success it buys is "
           "decisive where the baseline is floored (solve, simulate) and modest where the baseline is "
           "already strong (validate_*). Per-model tables in the backup." if not on else
           "Arrows are short on the x-axis (the baseline already burns its budget reasoning) and long on "
           "the y-axis: under think=on the tool buys large success gaps at a modest ~2× per-trial premium. "
           "Per-model tables in the backup."))
    S_image_slide(
        prs, "Tools invert the token profile — the cost is input, not output",
        fig_token_profile("token_profile.png"),
        caption="Mean input (solid) vs output (pale) tokens per trial, ≥9B pooled. no-tools is output-heavy ("
        + ("~0.3:1 input:output — it reasons in the open); the tool arms are input-heavy (~5:1)" if not on else
           "~0.2:1 input:output — the reasoning trace is all output); the tool arms are input-heavy (~3–5:1)")
        + " because tool schemas + tool outputs are re-fed every turn. That re-fed input is the real token "
        "cost of tools — an output-only comparison hides it entirely, which is why the headline metric is the total.")
    S_image_slide(
        prs,
        "Cost-of-pass — the tool pays for itself exactly where the model can't do the task" if not on else
        "Cost-of-pass — under think=on the regime is per-MODEL, and the tool wins almost everywhere",
        fig_cop_dumbbell("cop_dumbbell.png", regimes=not on),
        caption="Total tokens per success (log; lower = better), no-tools ○ vs +tool(steered) ●, bootstrap "
        "point estimates. "
        + ("Where the baseline is strong (validate_*) the tool is ~3–11× costlier per success; where the "
           "baseline is floored, the tool is ~3× cheaper (solve) or the only source of successes at all "
           "(simulate — no-tools never succeeds, so its cost-of-pass is infinite)." if not on else
           "The think=off task-regime split dissolves into a per-MODEL one: where reasoning drowns the "
           "baseline (9B validate_domain 200k→11k, Gemma ∞→12k tokens/success) the tool is far cheaper or "
           "the only producer; only Qwen3.6-35B — whose baseline survives the budget — still pays a tool "
           "premium on validate_* (e.g. 6k→15k). simulate is ∞ without the tool for every model."))
    h2, r2 = _cop_decomp_table([t for t in ALL_TASKS if t != "simulate"])
    S_table_slide(
        prs,
        "Why efficiency moves — (tokens/trial) ÷ (more often right) = cost-per-success",
        h2, r2,
        notes=f"Exact factorisation of the steered-vs-no-tools cost-of-pass multiple, ≥4B think={THINK}: "
        "(total-token cost ratio) ÷ (success-rate ratio) = cost-per-success ratio. "
        + ("On solve the tool spends ~4× the tokens but is ~10× more often right → ~3× cheaper per success; "
           "on the validate_* tasks the baseline is already cheap and right, so the same token premium is "
           "not paid back. simulate is omitted: no-tools never succeeds, the ratios are undefined (†) — "
           "see the dumbbell." if not on else
           "Under think=on the 'more often right' factor explodes wherever the baseline truncates (e.g. "
           "validate_domain 9B ~30×), overwhelming the ~2× token premium. Rows show '—' where the no-tools "
           "arm produced no success to price (Gemma validate_domain). simulate omitted (no-tools never "
           "succeeds) — see the dumbbell."))
    h3, r3 = _censoring_table()
    S_table_slide(
        prs, "Are the token numbers comparable? — truncation, turns, latency proxy",
        h3, r3,
        notes=f"≥9B pooled, think={THINK}. 'truncated %' = trials hitting the 8,192 output cap — truncation is "
        "arm-dependent, so completion-token means are budget-bounded counts, not free generation lengths. "
        + ("" if not on else "Under think=on the NO-TOOLS arms truncate most (55–83%): the reasoning trace "
           "eats the budget before an answer lands — this is the confound behind every think=on gap. ")
        + "'mean turns' (round-trips) × output tokens is the only defensible latency proxy here: wall-clock "
        "duration_s is confounded by the batched vLLM server; a concurrency=1 TTFT/TPOT micro-benchmark is "
        "future work.")


def _cost_of_pass_table(tasks: list[str]) -> tuple[list[str], list[list[str]]]:
    headers = ["task", "model", "no-tools", "+tool(plain)", "+tool(steered)"]
    rows: list[list[str]] = []
    for task in tasks:
        for i, m in enumerate(EFF_MODELS):
            nt = cell_cost_of_pass(m, task, "nt-neut")
            tl = cell_cost_of_pass(m, task, "tl-neut")
            st = cell_cost_of_pass(m, task, "tl-ster")
            base = nt if nt.n_succ else None
            rows.append([TASK_DISP[task] if i == 0 else "", MODEL_DISP[m],
                         _cop_cell(nt),
                         _cop_cell(tl, base),
                         _cop_cell(st, base)])
    return headers, rows


def _cop_decomp_cells(model: str, task: str, floored: bool) -> tuple[str, str, str]:
    """Factor the steered-vs-no-tools cost-of-pass EXACTLY: cost-of-pass = mean
    tokens/trial ÷ success rate, so the ratio st÷nt = (token-cost ratio) ÷
    (success-rate ratio). Cost factors use `_cost_mult_str` (↓red = worse);
    the hit-rate factor uses `_mult_str` (↑green = better)."""
    nt = cell_cost_of_pass(model, task, "nt-neut")
    st = cell_cost_of_pass(model, task, "tl-ster")
    if (floored or not nt.n_succ or not st.n_succ
            or nt.mean_tok <= 0 or st.mean_tok <= 0 or nt.succ <= 0 or st.succ <= 0):
        return ("—", "—", "—")
    return (_cost_mult_str(st.mean_tok, nt.mean_tok),  # tokens/trial (↓red if pricier)
            _mult_str(st.succ, nt.succ),               # more often right (↑green if better)
            _cost_mult_str(st.cop, nt.cop))            # = cost-per-success ratio (the quotient)


def _cop_decomp_table(tasks: list[str]) -> tuple[list[str], list[list[str]]]:
    headers = ["task", "model", "tokens/trial ×", "more often right ×", "= cost-per-success ×"]
    rows: list[list[str]] = []
    for task in tasks:
        floored = _task_floored(task)
        tlabel = TASK_DISP[task] + (" †" if floored else "")
        for i, m in enumerate(EFF_MODELS):
            a, b, c = _cop_decomp_cells(m, task, floored)
            rows.append([tlabel if i == 0 else "", MODEL_DISP[m], a, b, c])
    return headers, rows


def _phase2_bin_table(summary: dict, key: str, tasks: list[str]
                      ) -> tuple[list[str], list[list[str]]]:
    headers = ["task", "bin", "no-tools", "+tool(steered)", "Δ (pp)", "n/arm"]
    rows = []
    for task in tasks:
        dd = summary[f"{key}/{task}"]
        for b in range(3):
            rows.append([TASK_DISP[task] if b == 0 else "", dd["labels"][b],
                         f"{dd['nt'][b][0]:.0f} [{dd['nt'][b][1]:.0f},{dd['nt'][b][2]:.0f}]",
                         f"{dd['tl'][b][0]:.0f} [{dd['tl'][b][1]:.0f},{dd['tl'][b][2]:.0f}]",
                         f"{dd['gaps'][b]:+.0f}", str(dd['nt'][b][3])])
    return headers, rows


def _add_backup_section(prs, summary: dict) -> None:
    """Backup: the full per-model token tables behind the token section's
    figures, the secondary completion-only lens, and the RQ0.6 bin table.
    Presented slides carry the message; these carry the numbers."""
    S_text_slide(prs, "Backup — detailed tables", [
        "The slides that follow hold the full per-model numbers behind the token section:",
        "• total tokens/trial (input+output) per task × model × arm, with cost multiples vs no-tools;",
        "• cost-of-pass (total tokens per success) with bootstrap 95% CIs;",
        "• the secondary completion-only generation-cost lens — output tokens over successes only. It "
        "excludes the re-fed tool input (the dominant tool cost) and failed-attempt tokens, so it flatters "
        "tools; it is a generation-length diagnostic, never the consumption headline;",
        "• the RQ0.6 difficulty-bin table.",
    ])
    for grp, part in EFF_TASK_GROUPS:
        headers, rows = _token_cost_table(grp)
        S_table_slide(
            prs, f"Backup — total tokens/trial (input+output)  ·  ≥4B, think={THINK}  ·  {part}",
            headers, rows,
            notes=f"Mean prompt+completion tokens over token-bearing trials, think={THINK}, summed across turns. "
            "Cost multiple vs no-tools on the total. Tool arms are input-dominated (re-fed schemas + tool "
            "outputs); prefix cache (~90%) discounts the COMPUTE cost of that input but not the raw count.")
    for grp, part in EFF_TASK_GROUPS:
        h, r = _cost_of_pass_table(grp)
        S_table_slide(
            prs, f"Backup — cost-of-pass, tokens per success [bootstrap 95% CI]  ·  ≥4B, think={THINK}  ·  {part}",
            h, r,
            notes=f"cost-of-pass = Σ(prompt+completion) over ALL token-bearing trials ÷ #successes, think={THINK} "
            "(≡ mean total tokens/trial ÷ success rate). Charges failed-attempt tokens to the success count. "
            "95% CI = 2000-sample fixed-seed trial-level bootstrap of the ratio. '— (0 succ)' = arm produced "
            "no success to price. LOWER is better.")
    for grp, part in EFF_TASK_GROUPS:
        h, r = _cost_table(grp)
        S_table_slide(
            prs, f"Backup — completion-only output tokens per success (secondary, tool-flattering)  ·  {part}",
            h, r,
            notes=f"Mean completion (output) tokens over SUCCESSFUL trials only, ≥4B think={THINK}; 95% CI = "
            "2000-sample fixed-seed bootstrap. Output-only and successes-only — EXCLUDES the re-fed tool input "
            "and failed-attempt tokens, so it flatters tools; ≈30–70% of long-task successes hit the 8,192 cap, "
            "pinning the means toward the budget. Use the total-token and cost-of-pass tables for consumption "
            "and efficiency claims.")
    h6, r6 = _phase2_bin_table(summary, "rq06",
                               ["solve", "validate_problem", "validate_plan", "simulate"])
    S_table_slide(prs, "Backup — RQ0.6 difficulty-binned success (object count)",
                  h6, r6,
                  notes="No-tools vs +tool(steered), ≥9B think=off, per object-count tertile. The gap is flat "
                  "on every task — the null result summarised on the single RQ0.6 slide.")


def _add_phase2_rq(prs, rq: str, question: str, answer: str, bullets: list[str],
                   png: Path, summary: dict, key: str, tasks: list[str]) -> None:
    gap_tbl_task = _phase2_headroom_task(key)
    d = summary[f"{key}/{gap_tbl_task}"]
    gap_line = " → ".join(f"{d['labels'][b]}: Δ{d['gaps'][b]:+.0f}" for b in range(3))
    kw = answer.split()[0].strip(",.").upper()
    badge = (kw, VERDICT_COLOR[kw]) if kw in VERDICT_COLOR else None
    S_text_slide(prs, f"{rq} — does the advantage track difficulty?",
                 [f"{question}", "", answer, "",
                  f"Headroom case ({gap_tbl_task}) gap by bin:  {gap_line}."]
                 + [f"• {b}" for b in bullets]
                 + ["", "Phase-2 is headroom-gated: an advantage can only be seen to CHANGE where both "
                    f"arms have room to move. ≥9B, think={THINK}, no-tools vs +tool(steered)."],
                 badge=badge)
    S_image_slide(prs, f"{rq} — Evidence", png,
                  caption="Per difficulty bin: no-tools (grey) vs +tool steered (orange), Wilson 95% CIs; "
                  "Δ = tool − no-tools over each bin (shaded = the advantage).")
    headers, rows = _phase2_bin_table(summary, key, tasks)
    S_table_slide(prs, f"{rq} — difficulty-binned success (no-tools vs +tool steered)",
                  headers, rows)


# ---------------- Cross-mode aggregation (--think compare) ----------------
# A THIRD artifact that aggregates the locked think=off headline deck and its
# think=on companion WITHOUT touching either. Hard rule (corpus identity is
# load-bearing): never pool raw trials across arms or across think modes into one
# rate — every rate here is a single (model, task, arm, mode) cell, and we combine
# ONLY at the level of per-cell statistics (differences / Δ-of-differences / min).
# CIs follow the house convention: Wilson per rate, then Newcombe's MOVER for a
# difference of two proportions (a Wilson-consistent gap interval) and the nested
# MOVER-D for the difference of two INDEPENDENT gaps (off and on are disjoint
# corpora). The cross-mode spine is the REALIZABLE benefit = success(+tool steered)
# − success(no-tools): we lead with the steered arm because under think=on the
# plain arm stops calling the tool (it reasons instead), so plain availability
# conflates baseline collapse with a tool-calling failure (justified on-slide).

COMPARE_OUT = REPO / "checkpoints/rq-sweep5v2-compare"
COMPARE_PPTX = COMPARE_OUT / "pddl_copilot_rq_sweep5v2_compare.pptx"
# Cross-mode marker per task for the off-vs-on scatter (arm carries the colour).
TASK_MARKER = {"solve": "o", "validate_domain": "s", "validate_problem": "^",
               "validate_plan": "D", "simulate": "v"}
COMPARE_ORDER = ["solve", "simulate", "validate_domain",
                 "validate_problem", "validate_plan"]  # robust regimes first


def _mover_gap(hi: Cell, lo: Cell) -> tuple[float, float, float]:
    """Newcombe MOVER 95% CI (in pp) for succ(hi) − succ(lo), recovered from the
    two cells' Wilson intervals by square-and-add (Newcombe 1998, method 10) —
    the Wilson-consistent difference-of-proportions interval. Returns
    (gap, lo, hi) in pp; all-nan if either cell is empty."""
    if not (hi.n and lo.n):
        return float("nan"), float("nan"), float("nan")
    g = (hi.rate - lo.rate) * 100
    lo_off = math.sqrt((hi.rate - hi.lo) ** 2 + (lo.hi - lo.rate) ** 2) * 100
    hi_off = math.sqrt((hi.hi - hi.rate) ** 2 + (lo.rate - lo.lo) ** 2) * 100
    return g, g - lo_off, g + hi_off


def _mover_delta(gon: tuple, goff: tuple) -> tuple[float, float, float]:
    """Nested MOVER-D 95% CI (pp) for Δ = gon − goff, two INDEPENDENT gaps
    (think=off and think=on are disjoint corpora). Each gap arrives as its own
    MOVER interval (gap, lo, hi); recover its variance from that interval and
    square-add (Donner & Zou MOVER-D). '*' significance = CI excludes 0."""
    if gon[0] != gon[0] or goff[0] != goff[0]:
        return float("nan"), float("nan"), float("nan")
    d = gon[0] - goff[0]
    lo = d - math.sqrt((gon[0] - gon[1]) ** 2 + (goff[2] - goff[0]) ** 2)
    hi = d + math.sqrt((gon[2] - gon[0]) ** 2 + (goff[0] - goff[1]) ** 2)
    return d, lo, hi


def _realizable_gap(model: str, task: str, think: str) -> tuple[float, float, float]:
    """Realizable benefit = success(+tool steered) − success(no-tools), as a
    MOVER gap (pp) for one model×task×mode. The 'tool used properly' benefit —
    immune to the plain arm's under-calling collapse under think=on."""
    return _mover_gap(cell_success(model, task, "tl-ster", think),
                      cell_success(model, task, "nt-neut", think))


def _avail_gap(model: str, task: str, think: str) -> tuple[float, float, float]:
    """Availability gap = success(+tool plain) − success(no-tools), MOVER (pp)."""
    return _mover_gap(cell_success(model, task, "tl-neut", think),
                      cell_success(model, task, "nt-neut", think))


def _realizable_cross(task: str) -> list[dict]:
    """Per ≥9B model: realizable benefit off & on (MOVER gaps) + the MOVER-D
    Δ(on−off) + the robust floor (min over modes)."""
    out = []
    for m in MODELS_9B:
        goff = _realizable_gap(m, task, "off")
        gon = _realizable_gap(m, task, "on")
        d = _mover_delta(gon, goff)
        floor = min(goff[0], gon[0]) if (goff[0] == goff[0] and gon[0] == gon[0]) else float("nan")
        out.append(dict(model=m, off=goff, on=gon, delta=d, floor=floor))
    return out


def _baseline_floored_both(task: str) -> bool:
    """True when no-tools success < 2% across the ≥9B set in BOTH modes — the
    tool is the SOLE source of any success (simulate), so cross-mode invariance
    is categorical, not a magnitude comparison."""
    for think in ("off", "on"):
        for m in MODELS_9B:
            c = cell_success(m, task, "nt-neut", think)
            if c.n and c.rate >= 0.02:
                return False
    return True


def _mode_class(task: str) -> tuple[str, float, list[dict]]:
    """Classify a task's cross-mode tool value over ≥9B from the realizable
    benefit. 'sole-source' = baseline floored both modes; 'robust' = floor
    (min over modes) ≥ 30pp (a large win regardless of mode); 'budget-dep' =
    floor < 30pp (the large think=on gap is a truncated-baseline artifact;
    the honest mode-invariant benefit is the small floor)."""
    cross = _realizable_cross(task)
    floors = [r["floor"] for r in cross if r["floor"] == r["floor"]]
    floor = min(floors) if floors else float("nan")
    if _baseline_floored_both(task):
        return "sole-source", floor, cross
    if floor >= 30:
        return "robust", floor, cross
    return "budget-dep", floor, cross


# ---- cross-mode figures ----

def fig_mode_scatter(save_name: str) -> Path:
    """off (x) vs on (y) success, one point per ≥9B model × task × arm; colour =
    arm (grey no-tools, orange +tool steered), marker = task. The y=x diagonal is
    'unchanged across modes': the tool arm clusters ON it (mode-robust), the
    baseline falls far BELOW on validation (collapses under think=on) and rises
    ABOVE on solve (reasoning helps). No ○/→ glyphs (Helvetica Neue lacks them)."""
    from matplotlib.lines import Line2D
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    ax.set_axisbelow(True)
    ax.plot([0, 100], [0, 100], ls=(0, (4, 3)), lw=1.0, color=C_SPINE, zorder=1)
    arm_cfg = [("nt-neut", "no-tools", ARM_COLOR["nt-neut"]),
               ("tl-ster", "+tool (steered)", ARM_COLOR["tl-ster"])]
    for arm, _lab, col in arm_cfg:
        for task in ALL_TASKS:
            for m in MODELS_9B:
                co = cell_success(m, task, arm, "off")
                cn = cell_success(m, task, arm, "on")
                if not (co.n and cn.n):
                    continue
                ax.scatter([co.rate * 100], [cn.rate * 100], marker=TASK_MARKER[task],
                           s=50, color=col, edgecolor="white", linewidth=0.7,
                           zorder=3, alpha=0.92)
    ax.set_xlim(-3, 103)
    ax.set_ylim(-3, 103)
    ax.set_aspect("equal")  # so the y=x diagonal is a true 45° (label aligns)
    ax.set_xlabel("success rate, think=off (%)")
    ax.set_ylabel("success rate, think=on (%)")
    ax.set_title("Across modes: the tool arm holds, the baseline swings  ·  ≥9B")
    # single diagonal label in the empty upper-left triangle (no point collisions);
    # the below/above-diagonal reading is spelled out in the slide caption.
    ax.text(30, 36, "y = x: unchanged across modes", rotation=45,
            rotation_mode="anchor", ha="left", va="bottom", fontsize=7.5,
            style="italic", color=C_SOFT)
    arm_handles = [Line2D([0], [0], marker="o", ls="none", color=col,
                          markeredgecolor="white", label=lab)
                   for arm, lab, col in arm_cfg]
    task_handles = [Line2D([0], [0], marker=TASK_MARKER[t], ls="none",
                           color=C_SOFT, markeredgecolor="white", label=TASK_DISP[t])
                    for t in ALL_TASKS]
    # both legends sit in the empty left band so they never cover data points
    leg1 = ax.legend(handles=arm_handles, loc="upper left", fontsize=8,
                     title="arm (colour)", title_fontsize=8, framealpha=0.92)
    leg1._legend_box.align = "left"
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=task_handles, loc="center left", fontsize=7.5,
                     title="task (marker)", title_fontsize=8, framealpha=0.92,
                     bbox_to_anchor=(0.0, 0.42))
    leg2._legend_box.align = "left"
    _despine(ax)
    fig.tight_layout()
    return _save(fig, save_name)


def fig_realizable_dumbbell(save_name: str) -> Path:
    """Realizable benefit (+tool steered − no-tools, pp) per ≥9B model × task,
    think=off (open) connected to think=on (filled), MOVER 95% whiskers. Grouped
    by cross-mode class (robust large / sole-source / budget-dependent). The
    leftmost marker of each pair is the robust floor; a long connector = the
    benefit is budget-sensitive, a short one = mode-invariant."""
    from matplotlib.lines import Line2D
    class_band = {"robust": ("#2E7D52", 0.05), "sole-source": ("#3F7CAC", 0.05),
                  "budget-dep": ("#C0801A", 0.06)}
    fig, ax = plt.subplots(figsize=(9.8, 5.6))
    ax.set_axisbelow(True)
    yticks, ylabels = [], []
    y = 0.0
    band_spans = []
    for task in COMPARE_ORDER:
        cls, _floor, cross = _mode_class(task)
        y0 = y - 0.5
        for r in cross:
            goff, gon = r["off"], r["on"]
            if goff[0] == goff[0] and gon[0] == gon[0]:
                ax.plot([goff[0], gon[0]], [y, y], color=C_SPINE, lw=1.4, zorder=2)
            if gon[0] == gon[0]:
                ax.errorbar([gon[0]], [y],
                            xerr=[[gon[0] - gon[1]], [gon[2] - gon[0]]],
                            fmt="o", ms=7, color=ARM_COLOR["tl-ster"],
                            mec="white", mew=0.8, ecolor=ARM_COLOR["tl-ster"],
                            elinewidth=0.8, capsize=2, zorder=4)
            if goff[0] == goff[0]:
                ax.errorbar([goff[0]], [y],
                            xerr=[[goff[0] - goff[1]], [goff[2] - goff[0]]],
                            fmt="o", ms=7, mfc="white", mec=ARM_COLOR["nt-neut"],
                            mew=1.4, ecolor=ARM_COLOR["nt-neut"], elinewidth=0.8,
                            capsize=2, zorder=4)
            yticks.append(y)
            ylabels.append(f"{TASK_DISP[task]} · {MODEL_DISP[r['model']]}")
            y += 1
        band_spans.append((y0, y - 0.5, cls))
        ax.axhline(y - 0.5, color=C_RULE, lw=0.8, zorder=1)
        y += 0.4
    for lo, hi, cls in band_spans:
        col, a = class_band[cls]
        ax.axhspan(lo, hi, color=col, alpha=a, zorder=0)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("realizable benefit — success(+tool steered) − success(no-tools), pp "
                  "(MOVER 95%); leftmost marker per pair = the robust floor")
    ax.set_title("Realizable tool benefit across modes — think=off (open) to think=on (filled)  ·  ≥9B")
    handles = [Line2D([0], [0], marker="o", ls="none", mfc="white",
                      mec=ARM_COLOR["nt-neut"], mew=1.4, label="think=off"),
               Line2D([0], [0], marker="o", ls="none", color=ARM_COLOR["tl-ster"],
                      mec="white", label="think=on")]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.92)
    ax.grid(axis="x", which="major")
    _despine(ax)
    fig.tight_layout()
    return _save(fig, save_name)


# ---- cross-mode tables ----

def _gap_ci_cell(g: tuple) -> str:
    if g[0] != g[0]:
        return "–"
    return f"{g[0]:+.0f} [{g[1]:+.0f},{g[2]:+.0f}]"


def _delta_ci_cell(d: tuple) -> str:
    """Δ(on−off) [MOVER-D 95% CI]; '*' = CI excludes 0 (signed significance).
    The leading sign drives `_delta_tint` (green if + & sig, red if − & sig)."""
    if d[0] != d[0]:
        return "–"
    sig = "*" if not (d[1] <= 0 <= d[2]) else ""
    return f"{d[0]:+.0f}{sig} [{d[1]:+.0f},{d[2]:+.0f}]"


def _mode_summary_table() -> tuple[list[str], list[list[str]]]:
    """One row per task: realizable-benefit range off/on across ≥9B, the robust
    floor (min over modes), the Δ(on−off) range with a k/3-significant count, and
    the cross-mode class chip — the crisp combined claim in one table."""
    headers = ["task", "benefit off (pp)", "benefit on (pp)", "robust floor",
               "Δ(on−off) pp", "k/3 sig", "mode class"]
    rows = []
    for task in ALL_TASKS:
        cls, floor, cross = _mode_class(task)
        offs = [r["off"][0] for r in cross if r["off"][0] == r["off"][0]]
        ons = [r["on"][0] for r in cross if r["on"][0] == r["on"][0]]
        ds = [r["delta"][0] for r in cross if r["delta"][0] == r["delta"][0]]
        ksig = sum(1 for r in cross if r["delta"][0] == r["delta"][0]
                   and not (r["delta"][1] <= 0 <= r["delta"][2]))
        rows.append([
            TASK_DISP[task],
            f"{min(offs):+.0f}…{max(offs):+.0f}" if offs else "–",
            f"{min(ons):+.0f}…{max(ons):+.0f}" if ons else "–",
            f"{floor:+.0f}" if floor == floor else "–",
            f"{min(ds):+.0f}…{max(ds):+.0f}" if ds else "–",
            f"{ksig}/3",
            cls,
        ])
    return headers, rows


def _realizable_detail_table(tasks: list[str]) -> tuple[list[str], list[list[str]]]:
    """Per task × ≥9B model: realizable benefit off [MOVER 95%], on [MOVER 95%],
    Δ(on−off) [MOVER-D 95%, * = excludes 0]."""
    headers = ["task", "model", "benefit off [95%]", "benefit on [95%]",
               "Δ(on−off) [95%]"]
    rows = []
    for task in tasks:
        cross = _realizable_cross(task)
        for i, r in enumerate(cross):
            rows.append([TASK_DISP[task] if i == 0 else "", MODEL_DISP[r["model"]],
                         _gap_ci_cell(r["off"]), _gap_ci_cell(r["on"]),
                         _delta_ci_cell(r["delta"])])
    return headers, rows


def _cop_cross_table() -> tuple[list[str], list[list[str]]]:
    """Cost-of-pass (total tokens per success) cross-mode, ≥9B: no-tools off→on
    and +tool(steered) off→on. Shows the regime flip from task-determined (off)
    to model-determined (on). '∞' = arm produced no success to price."""
    headers = ["task", "model", "no-tools off→on", "+tool(steered) off→on"]
    rows = []

    def f(c):
        return bd._fmt_tokens(c.cop) if c.n_succ else "∞"

    for task in ALL_TASKS:
        for i, m in enumerate(MODELS_9B):
            nt_off = cell_cost_of_pass(m, task, "nt-neut", "total", "off")
            nt_on = cell_cost_of_pass(m, task, "nt-neut", "total", "on")
            st_off = cell_cost_of_pass(m, task, "tl-ster", "total", "off")
            st_on = cell_cost_of_pass(m, task, "tl-ster", "total", "on")
            rows.append([TASK_DISP[task] if i == 0 else "", MODEL_DISP[m],
                         f"{f(nt_off)}→{f(nt_on)}", f"{f(st_off)}→{f(st_on)}"])
    return headers, rows


def _trunc_cross_table() -> tuple[list[str], list[list[str]]]:
    """Truncation (8,192-cap) by task × arm × mode, ≥9B pooled across MODELS only
    (the established `_censoring_table` convention — arms and modes stay
    separate, never pooled). The baseline arm's truncation explodes off→on; the
    steered tool arm barely moves — the budget confound behind every think=on gap."""
    headers = ["task", "arm", "truncated% off", "truncated% on", "Δ trunc (pp)"]
    rows = []

    def tr(task, arm, think):
        sub = [r for r in _pooled_rows(MODELS_9B, arm, think) if r["task"] == task]
        n = len(sub)
        return (sum(1 for r in sub if r.get("truncated")) / n * 100) if n else float("nan")

    for task in ALL_TASKS:
        for j, arm in enumerate(("nt-neut", "tl-ster")):
            o = tr(task, arm, "off")
            n = tr(task, arm, "on")
            rows.append([TASK_DISP[task] if j == 0 else "", ARM_DISP[arm],
                         f"{o:.0f}%" if o == o else "–",
                         f"{n:.0f}%" if n == n else "–",
                         f"{n - o:+.0f}" if (o == o and n == n) else "–"])
    return headers, rows


def _compare_asserts() -> None:
    """Cross-mode consistency gate for `--think compare --check`: the MOVER
    helpers must reproduce the raw per-cell differences, bracket their own point
    estimates, and the MOVER-D point must equal on−off exactly — catches a helper
    regression without re-deriving the whole pipeline."""
    n_ok = 0
    for task in ALL_TASKS:
        for m in MODELS_9B:
            goff = _realizable_gap(m, task, "off")
            gon = _realizable_gap(m, task, "on")
            raw_off = (cell_success(m, task, "tl-ster", "off").rate
                       - cell_success(m, task, "nt-neut", "off").rate) * 100
            assert goff[0] != goff[0] or abs(goff[0] - raw_off) < 1e-9, (m, task)
            assert goff[0] != goff[0] or goff[1] - 1e-9 <= goff[0] <= goff[2] + 1e-9, (m, task)
            d = _mover_delta(gon, goff)
            assert d[0] != d[0] or abs(d[0] - (gon[0] - goff[0])) < 1e-9, (m, task)
            assert d[0] != d[0] or d[1] - 1e-9 <= d[0] <= d[2] + 1e-9, (m, task)
            n_ok += 1
    print(f"  compare: MOVER point/CI consistency OK ({n_ok} cells)", file=sys.stderr)


def build_compare_pptx(gate_off: list[str], gate_on: list[str]) -> Path:
    """Standalone cross-mode deck. Reads both corpora at the per-cell-statistic
    level only; the off and on decks are untouched."""
    prs = bd._make_pptx()

    S_title_slide(
        prs, "Where is the tool's value mode-invariant — and where is it just budget?",
        "cross-mode aggregation of the think=off headline deck and the think=on companion · "
        "≥9B · realizable benefit = success(+tool steered) − success(no-tools) · "
        "Newcombe MOVER 95% CIs on every gap and cross-mode difference")

    # --- bottom line up front: the three regimes ---
    S_text_slide(prs, "Bottom line — three cross-mode regimes", [
        "Aggregated across reasoning modes, the planning tool's value (≥9B, realizable benefit = "
        "+tool steered − no-tools) splits cleanly into three regimes:",
        "",
        "• Sole capability — simulate: the unaided model scores 0% in BOTH modes, so the tool is the "
        "only way to track state. Benefit +83…+97pp, identical off and on — mode-invariant by construction.",
        "• Robust large win — solve: the tool wins big in both modes (robust floor +46pp). The headline "
        "gap SHRINKS under think=on (off +83…+91 → on +46…+71) only because reasoning rescues the unaided "
        "baseline (9B 11→27%, 35B 9→38%), not because the tool weakens.",
        "• Budget-dependent — validate_domain / validate_problem / validate_plan: the robust floor is SMALL "
        "(+5…+25pp). The large think=on gaps are an artifact — the unaided baseline truncates 78–100% and "
        "collapses (Gemma validate_domain 78→0%). For the one model whose baseline survives the budget "
        "(Qwen3.6-35B, ≤11% truncation) the benefit is small and the SAME across modes (validate_plan +8 off / +14 on).",
        "",
        "→ The tool is a categorical or large win on solve/simulate regardless of reasoning mode; on the "
        "validation tasks the honest, mode-invariant benefit over a competent baseline is small, and only "
        "LOOKS large when reasoning drowns that baseline under the fixed 8,192-token decode budget.",
    ])

    # --- method / how-to-read ---
    S_text_slide(prs, "How the cross-mode view is built", [
        "This deck aggregates the locked think=off deck and its think=on companion at the level of per-cell "
        "statistics ONLY — raw trials are NEVER pooled across arms or across reasoning modes. Every rate is "
        "a single (model, task, arm, mode) cell; we combine only their differences.",
        "• Realizable benefit = success(+tool steered) − success(no-tools), per model×task×mode. We lead with "
        "the STEERED arm, not plain availability: under think=on the plain arm stops calling the tool (it "
        "reasons instead), so the plain gap conflates baseline collapse with a tool-calling failure (slide near the end).",
        "• A gap's CI uses Newcombe's MOVER method (a Wilson-consistent difference-of-proportions interval); "
        "the cross-mode change Δ(on−off) uses the nested MOVER-D for a difference of two INDEPENDENT gaps "
        "(off and on are disjoint corpora). A “*” marks a Δ whose 95% CI excludes zero.",
        "• Robust floor = min over the two modes of the realizable benefit — the benefit claimable regardless "
        "of reasoning mode (the budget-insensitive lower bound).",
        "→ The budget confound is carried throughout: under think=on reasoning + answer share one 8,192-token "
        "decode budget; truncation differs by arm and mode (caveat slide); completion = reasoning + answer "
        "with no logged split; latency is only a turns×output-token proxy.",
    ])

    # --- figure 1: the mechanism (tool holds, baseline swings) ---
    S_image_slide(
        prs, "The mechanism — the tool arm is mode-robust, the baseline is not",
        fig_mode_scatter("mode_scatter.png"),
        caption="Each point is one ≥9B model × task × arm: think=off success (x) vs think=on success (y). "
        "Orange (+tool steered) clusters on the diagonal — the tool delivers similar success in both modes. "
        "Grey (no-tools) falls far below the diagonal on the validation tasks (the baseline reasons past the "
        "8,192-token cap and collapses) and sits above it on solve (reasoning helps the unaided model). The "
        "gap therefore moves with the BASELINE, not the tool.")

    # --- figure 2: the WHERE (realizable benefit dumbbell) ---
    S_image_slide(
        prs, "Where the benefit is mode-invariant vs budget-amplified",
        fig_realizable_dumbbell("realizable_dumbbell.png"),
        caption="Realizable benefit (+tool steered − no-tools, pp) per model × task, think=off (open) "
        "connected to think=on (filled), MOVER 95% whiskers. Short connector = mode-invariant benefit "
        "(simulate, and 35B everywhere); long connector = budget-sensitive (9B/Gemma on validation, where "
        "the think=off baseline still had room and the think=on baseline truncated). The leftmost marker of "
        "each pair is the robust floor.")

    # --- the crisp summary table ---
    h, r = _mode_summary_table()
    S_table_slide(
        prs, "Cross-mode summary — robust floor and what moves, per task", h, r,
        notes="≥9B. Benefit = realizable (steered − no-tools) MOVER point per model, ranged across the 3 "
        "models. Robust floor = min over BOTH modes AND models = the budget-insensitive lower bound on the "
        "tool's value. Δ(on−off) ranged across models; 'k/3 sig' = models whose MOVER-D 95% CI excludes 0. "
        "Class: robust = floor ≥30pp (large win both modes); sole-source = baseline floored both modes; "
        "budget-dep = floor <30pp (the large think=on gap is a truncated-baseline artifact).")

    # --- per-model rigorous detail (split 3 + 2 tasks to avoid row overflow) ---
    for grp, part in EFF_TASK_GROUPS:
        hh, rr = _realizable_detail_table(grp)
        S_table_slide(
            prs, f"Cross-mode detail — realizable benefit off / on / Δ, per model  ·  ≥9B  ·  {part}",
            hh, rr,
            notes="Realizable benefit = success(+tool steered) − success(no-tools), pp. off/on = Newcombe "
            "MOVER 95% CI; Δ(on−off) = nested MOVER-D 95% CI, '*' = excludes 0 (green if a significant "
            "increase under think=on, red if a significant decrease). The Δ is large-and-positive exactly "
            "where the no-tools baseline truncates under think=on (9B/Gemma validation); near-zero where the "
            "baseline is mode-stable (Qwen3.6-35B) or floored both modes (simulate).")

    # --- why steered, not plain ---
    S_text_slide(prs, "Why the realizable (steered) benefit, not plain availability", [
        "Under think=on the PLAIN tool arm becomes unreliable — the model spends its decode budget reasoning "
        "instead of issuing the tool call. tool_selected (plain) collapses: Gemma-MoE-26B solve 100→23%, "
        "validate_plan 21→1%, validate_domain 100→52%; Qwen3.5-9B solve 100→59%. Qwen3.6-35B mostly holds (≥78%).",
        "• So the think=on AVAILABILITY gap (plain − no-tools) mixes two confounds: a truncation-collapsed "
        "baseline AND an under-calling tool arm. It is not a clean measure of the tool's value.",
        "• Steering repairs the under-calling, so the REALIZABLE benefit (steered − no-tools) isolates what "
        "the tool is worth when actually invoked. This is why steering matters MORE under think=on — solve "
        "plain→steered lift is Gemma 23→74% under think=on (vs an already-~99% plain arm at think=off).",
        "→ Caveat: even the steered arm pays a residual budget tax under think=on for some cells "
        "(Gemma validate_plan steered 93→44%, solve 99→74%), so the tool arm is MOSTLY, not perfectly, "
        "mode-invariant. Qwen3.6-35B's steered arm is fully mode-invariant.",
    ])

    # --- cost-of-pass regime flip ---
    hc, rc = _cop_cross_table()
    S_table_slide(
        prs, "Cost-of-pass flips from task-determined to model-determined", hc, rc,
        notes="Total tokens per success (lower = better), no-tools and +tool(steered), each off→on, ≥9B. "
        "think=off: cost-of-pass is TASK-determined — floored tasks (solve, simulate) the tool is ~3× "
        "cheaper, strong-baseline tasks (validate_*) 3–11× costlier. think=on: the split becomes "
        "MODEL-determined — where reasoning drowns the baseline (9B validate_domain 9.3k→200k, Gemma →∞) the "
        "tool is far cheaper or the only producer; only Qwen3.6-35B (baseline survives the budget) still "
        "pays the validate_* premium (≈6k→15k). Bootstrap point estimates; output right-censored at 8,192.")

    # --- the budget confound made concrete ---
    ht, rt = _trunc_cross_table()
    S_table_slide(
        prs, "The budget confound, made concrete — truncation by arm × mode", ht, rt,
        notes="Share of trials hitting the 8,192-token output cap, ≥9B pooled across MODELS only (arms and "
        "modes never pooled). The NO-TOOLS arm's truncation explodes off→on — the baseline reasons past the "
        "cap before answering — while the +tool(steered) arm barely moves (the tool call replaces the long "
        "derivation). Every inflated think=on gap traces to that baseline-truncation column. Under think=on "
        "completion = reasoning + answer with no logged split; latency only via turns × output tokens.")

    # --- recap / paper claim ---
    S_text_slide(prs, "Combined claim for the paper", [
        "• The verdict PATTERN is mode-invariant: YES / YES / MIXED / YES, RQ0.5 YES, RQ0.6 NO reproduce "
        "under reasoning mode — the tool's value is not an artifact of direct-answer mode.",
        "• WHERE the value is mode-invariant: simulate (sole capability) and solve (large win, robust floor "
        "+46pp) — robust regardless of reasoning mode.",
        "• WHERE it is budget-dependent: the validation tasks. The robust floor over modes is small "
        "(+5…+25pp); the dramatic think=on gaps are a decode-budget artifact (the baseline truncates "
        "78–100% and collapses), confirmed by the budget-robust Qwen3.6-35B showing the SAME small benefit "
        "in both modes.",
        "→ Report think=off as the clean headline; cite the cross-mode floor as the mode-robust claim; flag "
        "the validation-task think=on gaps as budget-confounded, not extra tool skill. A cap-raised think=on "
        "rerun (to test whether a larger budget closes the baseline gap) remains the open follow-up.",
    ])

    _finalize_footers(prs)
    COMPARE_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(COMPARE_PPTX))
    return COMPARE_PPTX


# ---------------- Main ----------------

def main() -> int:
    global THINK, OUT_DIR, PLOT_DIR, PHASE2_JSON, PPTX_OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="run gates + phase-2 assertion only; do not render plots/pptx")
    ap.add_argument("--no-assert-oracle", action="store_true",
                    help="skip the byte-equality assertion against the existing phase2_summary.json oracle")
    ap.add_argument("--think", choices=("off", "on", "compare"), default="off",
                    help="thinking mode of the deck. 'off' = the locked headline deck "
                    "(verdicts + phase-2 oracle asserted). 'on' = the companion deck over "
                    "the think=on corpus: same signed rule, verdicts computed not locked, "
                    "oracle skipped (it is think=off-only), outputs under "
                    "checkpoints/rq-sweep5v2-think-on/. 'compare' = the cross-mode "
                    "aggregation deck (off vs on, realizable benefit + MOVER CIs), outputs "
                    "under checkpoints/rq-sweep5v2-compare/ — leaves both other decks untouched.")
    args = ap.parse_args()

    THINK = args.think
    if THINK == "on":
        OUT_DIR = REPO / "checkpoints/rq-sweep5v2-think-on"
        PLOT_DIR = OUT_DIR / "plots"
        PHASE2_JSON = OUT_DIR / "phase2_summary.json"
        PPTX_OUT = OUT_DIR / "pddl_copilot_rq_sweep5v2_think_on.pptx"
    elif THINK == "compare":
        OUT_DIR = COMPARE_OUT
        PLOT_DIR = OUT_DIR / "plots"

    print(f"loading {RESULTS_ROOT} ...", file=sys.stderr)
    bd.CELLS = bd.load_all(RESULTS_ROOT)
    bd.MODEL_ORDER = MODEL_ORDER

    # --- cross-mode aggregation: a standalone deck over BOTH corpora; the off
    #     and on decks are not touched. Both gates run (descriptive) + the MOVER
    #     consistency asserts; no phase-2 oracle (off-only) and no locked verdict
    #     asserts (those are per-mode). ---
    if THINK == "compare":
        print("=== CROSS-MODE COMPARE: gates (off + on) + MOVER asserts ===", file=sys.stderr)
        gate_off = run_gate("off")
        gate_on = run_gate("on")
        for ln in gate_off + gate_on:
            print("  " + ln, file=sys.stderr)
        _compare_asserts()
        if args.check:
            print("--check: cross-mode asserts + both gates passed; skipping render",
                  file=sys.stderr)
            return 0
        print("=== RENDER (compare) ===", file=sys.stderr)
        out = build_compare_pptx(gate_off, gate_on)
        n_slides = len(__import__("pptx").Presentation(str(out)).slides._sldIdLst)
        print(f"wrote {out}  ({n_slides} slides)", file=sys.stderr)
        print(f"plots → {PLOT_DIR}", file=sys.stderr)
        return 0

    print(f"=== GATE: RQ0.3 validate_plan tool-calling artifact (think={THINK}) ===", file=sys.stderr)
    gate_lines = run_gate(THINK)
    for ln in gate_lines:
        print("  " + ln, file=sys.stderr)

    print("=== PHASE-2 ===", file=sys.stderr)
    summary = build_phase2()
    if THINK == "off" and not args.no_assert_oracle:
        if PHASE2_EXPECTED.exists():
            assert_phase2_matches(summary, PHASE2_EXPECTED)
            print(f"  phase2 reproduces tracked {PHASE2_EXPECTED.name} exactly "
                  f"(7 keys × 3 bins)", file=sys.stderr)
        else:
            print(f"  warn: no tracked oracle at {PHASE2_EXPECTED} — skipping "
                  f"regression assertion", file=sys.stderr)
    elif THINK == "on":
        print("  think=on: phase-2 computed fresh (tracked oracle is think=off-only)", file=sys.stderr)
    # verdict-rule sanity for both modes (asserts the lock only on think=off)
    for rq in RQ_TASKS:
        _phase1_verdict(rq)
    for key in ("rq05", "rq06"):
        _phase2_verdict(summary, key)
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
