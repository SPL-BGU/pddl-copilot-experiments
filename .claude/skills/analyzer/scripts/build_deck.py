"""Build a PowerPoint deck (.pptx) from a filtered results root.

Promoted from .local/pptx_sweep4_v5_v7_first/build_deck.py. Slide order and
chart functions live here; everything that varies per checkpoint (results
root, model list, captions, output path) is loaded from a small Python
config module passed via --config.

Usage:
    python3 .claude/skills/analyzer/scripts/build_deck.py \\
        --config checkpoints/<name>/deck_config.py \\
        --out    checkpoints/<name>/pddl_copilot_<name>.pptx

Config module contract (see checkpoints/sweep4-v5-v7-first/deck_config.py
for a worked example):

  REQUIRED attributes
    RESULTS       : str | Path  — results root (relative to repo or absolute)
    MODEL_ORDER   : list[str]   — slurm-dir model slugs in display order
    MODEL_DISP    : dict[str,str] — slug → presentation label
    COND_ORDER    : list[str]   — cond slugs in display order
    COND_DISP     : dict[str,str] — slug → presentation label
    TITLE         : str         — title-slide title
    SUBTITLE      : str         — title-slide subtitle

  OPTIONAL attributes
    OUT_PPTX      : str | Path  — output file (CLI --out overrides)
    FIG_DIR       : str | Path  — where to drop intermediate PNGs
                                  (default: <out_pptx>.figs/)
    SLIDE_CAPTIONS: dict[str,str] — override default captions by slide key
                                    (see DEFAULT_CAPTIONS below for keys)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

REPO = Path(__file__).resolve().parents[4]

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
TASK_LABEL = {
    "solve": "solve",
    "validate_domain": "val-dom",
    "validate_problem": "val-prob",
    "validate_plan": "val-plan",
    "simulate": "simulate",
}

# Caption key → default text. Override any of these by setting SLIDE_CAPTIONS
# in the deck_config module.
DEFAULT_CAPTIONS = {
    "success_off": "Per-task success per cell. Multi-model view. Missing bars = cell not yet complete.",
    "success_on":  "Same chart, think=on.",
    "tool_selection": "% of with-tools trials where the model invoked the expected planner/validator tool.",
    "successful_tool_use":
        "Light bar = % of with-tools trials where the model called the matching tool. "
        "Dark bar = % where both (a) the right tool was called AND (b) the result was scored success. "
        "The (sel% − dark%) gap is the failure mode after tool selection: "
        "verdict_mismatch / tool_error / loop_exhausted.",
    "confusion_off":
        "One row per model; columns = validate_domain, validate_problem, validate_plan. "
        "TP = correctly predicted VALID, TN = correctly predicted INVALID. "
        "'no-ans' counts truncated / parse-fail trials excluded from prec/rec/acc.",
    "confusion_on":
        "think=on bloats output budget — note the no-ans count: at this corpus the entire response is "
        "reasoning text with no JSON verdict (truncated_no_answer + format_parse_fail dominate).",
    "tokens_all":
        "Left column = INPUT tokens (prompt_eval_count), right column = OUTPUT tokens (eval_count). "
        "Bar label = % of trials in that cell with success=False. "
        "With-tools cells run ~2 turns so input is roughly 2× no-tools — expected (per-turn cost is comparable).",
    "tokens_succ":
        "Same metric, but the mean is computed only on success=True trials. "
        "Side label is still the FULL-cell failure rate so you can see how much data is excluded.",
    "tokens_solve":
        "Bars = mean input / output tokens per `solve` trial. Bar label = failure%. "
        "no-tools is cheap but solves almost nothing; with-tools pays a ~2× input premium for the planner round-trip.",
    "tokens_validate_domain":
        "Bars = mean input / output tokens per `validate_domain` trial. Bar label = failure%.",
    "tokens_validate_problem":
        "Bars = mean input / output tokens per `validate_problem` trial. Bar label = failure%.",
    "tokens_validate_plan":
        "Bars = mean input / output tokens per `validate_plan` trial. Bar label = failure%. "
        "Larger plans inflate the input prompt; think=on roughly doubles output tokens.",
    "tokens_simulate":
        "Bars = mean input / output tokens per `simulate` trial. Bar label = failure%. "
        "Long step-by-step traces drive output; no-tools failure% is ~100% across the board.",
    "latency_all":
        "Bar height = mean wall-clock seconds per trial. "
        "Bar-top label = % of trials with success=False (whatever the reason).",
    "latency_succ":
        "Same chart but the mean is computed on trials that succeeded. "
        "Side label still shows the original failure rate so you can see how much data we're excluding.",
}

TOKEN_NOTE_BULLETS = [
    "• Definitions:  input tokens = Ollama `prompt_eval_count` (the prompt the model reads).  "
    "output tokens = Ollama `eval_count` (tokens the model generates).",
    "• A `trial` = one harness call for one (model, task, problem, prompt-variant). "
    "For with-tools cells the harness runs a 2-turn agent loop: turn-1 asks the model, "
    "turn-2 feeds the tool result back.",
    "• The per-trial input/output numbers shown are SUMMED across every turn of that trial "
    "(pddl_eval/chat.py:290 — the counters are `+=`).  They are NOT per single prompt.",
    "• A with-tools trial doing 2 turns naturally costs ~2× the no-tools input figure: "
    "Ollama re-evaluates the growing chat history end-to-end on each call.",
    "• Bar labels on the next slides = full-cell failure% so you can tell whether expensive cells "
    "are actually delivering successful trials.",
    "• For a per-single-prompt view, divide each bar by `tokens.turns` (≈1 for no-tools, "
    "≈2 for tools). Per-turn cost is roughly comparable; the tool-loop multiplier is structural.",
]


# ---------------- Config loader ----------------

REQUIRED_CONFIG = ("RESULTS", "MODEL_ORDER", "MODEL_DISP",
                   "COND_ORDER", "COND_DISP", "TITLE", "SUBTITLE")


def _load_config(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("deck_config", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"could not load config module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [a for a in REQUIRED_CONFIG if not hasattr(mod, a)]
    if missing:
        raise SystemExit(f"deck_config {path} missing required attributes: {missing}")
    return mod


def _resolve_path(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (REPO / p).resolve()


# ---------------- Loading ----------------

def _cell_name(d: str) -> tuple[str, str, str] | None:
    """Parse slurm cell directory name into (model, think, cond)."""
    m = re.match(r"slurm_(?:vllm_)?(?P<model>.+?)_(?P<think>on|off)_(?P<cond>.+)$", d)
    if not m:
        return None
    return m.group("model"), m.group("think"), m.group("cond")


def load_all(results_root: Path) -> dict[tuple[str, str, str], list[dict]]:
    out: dict[tuple[str, str, str], list[dict]] = {}
    for child in sorted(results_root.iterdir()):
        if not child.is_dir() or not child.name.startswith("slurm_"):
            continue
        parsed = _cell_name(child.name)
        if not parsed:
            continue
        fp = child / "trials.jsonl"
        if not fp.exists():
            continue
        rows: list[dict] = []
        with fp.open() as f:
            for line in f:
                try:
                    rows.append(json.loads(line)["result"])
                except (json.JSONDecodeError, KeyError):
                    pass
        out[parsed] = rows
    return out


# ---------------- Per-cell statistics ----------------
#
# CELLS, MODEL_ORDER, MODEL_DISP, COND_ORDER, COND_DISP are populated by
# main() from the deck_config module before the figure builders run.
# Module-level globals are used so figure builders stay verbatim copies
# of the original .local/build_deck.py — easier to debug visually.

CELLS: dict[tuple[str, str, str], list[dict]] = {}
MODEL_ORDER: list[str] = []
MODEL_DISP: dict[str, str] = {}
COND_ORDER: list[str] = []
COND_DISP: dict[str, str] = {}


def task_success_rate(rows: list[dict], task: str) -> tuple[float, int, int]:
    sub = [r for r in rows if r["task"] == task]
    if not sub:
        return float("nan"), 0, 0
    s = sum(1 for r in sub if r["success"])
    return s / len(sub), s, len(sub)


def tool_selected_rate(rows: list[dict], task: str) -> tuple[float, int, int]:
    sub = [r for r in rows if r["task"] == task and r.get("with_tools") and r.get("tool_selected") is not None]
    if not sub:
        return float("nan"), 0, 0
    s = sum(1 for r in sub if r["tool_selected"])
    return s / len(sub), s, len(sub)


def truth_for(r: dict) -> bool | None:
    task = r["task"]
    pname = r["problem_name"] or ""
    pl = r.get("plan_label") or ""
    if task == "validate_domain":
        return False if pname == "domain_neg" else True
    if task == "validate_problem":
        return False if pname.startswith("n0") else True
    if task == "validate_plan":
        if pl.startswith("v"):
            return True
        if pl.startswith("b"):
            return False
    return None


def confusion(rows: list[dict], task: str) -> dict:
    tp = tn = fp = fn = no_ans = 0
    for r in rows:
        if r["task"] != task:
            continue
        truth = truth_for(r)
        if truth is None:
            continue
        fr = r.get("failure_reason")
        if r["success"]:
            pred = truth
        elif fr == "verdict_mismatch":
            pred = not truth
        else:
            no_ans += 1
            continue
        if truth and pred:
            tp += 1
        elif not truth and not pred:
            tn += 1
        elif not truth and pred:
            fp += 1
        elif truth and not pred:
            fn += 1
    return dict(tp=tp, tn=tn, fp=fp, fn=fn, no_ans=no_ans,
                n=tp + tn + fp + fn + no_ans)


def metrics_from_cm(cm: dict) -> dict:
    tp, tn, fp, fn = cm["tp"], cm["tn"], cm["fp"], cm["fn"]
    n_decided = tp + tn + fp + fn
    n_total = n_decided + cm["no_ans"]
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    acc_dec = (tp + tn) / n_decided if n_decided else float("nan")
    acc_all = (tp + tn) / n_total if n_total else float("nan")
    return dict(precision=prec, recall=rec, accuracy_decided=acc_dec, accuracy_all=acc_all)


def token_stats(rows: list[dict], task: str | None = None,
                only_success: bool = False) -> dict:
    sub = [r for r in rows if (task is None or r["task"] == task)]
    if only_success:
        sub = [r for r in sub if r.get("success")]
    if not sub:
        return dict(prompt=float("nan"), completion=float("nan"),
                    total=float("nan"), per_turn_prompt=float("nan"),
                    per_turn_total=float("nan"), turns=float("nan"),
                    fail_pct=float("nan"), n=0)
    p = [r.get("tokens", {}).get("prompt", 0) or 0 for r in sub]
    c = [r.get("tokens", {}).get("completion", 0) or 0 for r in sub]
    t = [r.get("tokens", {}).get("turns", 1) or 1 for r in sub]
    per_turn_p = [pi / ti for pi, ti in zip(p, t)]
    per_turn_pc = [(pi + ci) / ti for pi, ci, ti in zip(p, c, t)]
    base = [r for r in rows if (task is None or r["task"] == task)]
    n_fail = sum(1 for r in base if not r.get("success"))
    fail_pct = (n_fail / len(base) * 100) if base else float("nan")
    return dict(
        prompt=float(np.mean(p)), completion=float(np.mean(c)),
        total=float(np.mean(p) + np.mean(c)),
        per_turn_prompt=float(np.mean(per_turn_p)),
        per_turn_total=float(np.mean(per_turn_pc)),
        turns=float(np.mean(t)),
        fail_pct=fail_pct,
        n=len(sub),
    )


def latency_stats(rows: list[dict], task: str | None = None) -> dict:
    sub = [r for r in rows if (task is None or r["task"] == task)]
    durs = [r.get("duration_s", 0.0) or 0.0 for r in sub]
    n_err = sum(1 for r in sub if r.get("error"))
    n_fail = sum(1 for r in sub if not r["success"])
    durs_ok = [r.get("duration_s", 0.0) or 0.0 for r in sub if not r.get("error")]
    durs_succ = [r.get("duration_s", 0.0) or 0.0 for r in sub if r["success"]]
    return dict(
        mean_all=float(np.mean(durs)) if durs else float("nan"),
        mean_no_err=float(np.mean(durs_ok)) if durs_ok else float("nan"),
        mean_succ=float(np.mean(durs_succ)) if durs_succ else float("nan"),
        n=len(sub), n_err=n_err, n_fail=n_fail,
    )


# ---------------- Figure builders ----------------

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})


def _fmt_tokens(v: float) -> str:
    if np.isnan(v):
        return ""
    if v >= 10000:
        return f"{v/1000:.0f}k"
    if v >= 1000:
        return f"{v/1000:.1f}k"
    return f"{v:.0f}"


def _annotate_bars(ax, bars, primary_vals, secondary_vals,
                   primary_fmt=_fmt_tokens, secondary_fmt=lambda v: f"f:{v:.0f}%"):
    for b, pv, sv in zip(bars, primary_vals, secondary_vals):
        h = b.get_height()
        if np.isnan(h):
            continue
        if not np.isnan(pv):
            ax.text(b.get_x() + b.get_width() / 2, h, primary_fmt(pv),
                    ha="center", va="bottom", fontsize=7, color="#222")
        if sv is not None and not np.isnan(sv) and h > 0:
            y_in = h * 0.92
            ax.text(b.get_x() + b.get_width() / 2, y_in, secondary_fmt(sv),
                    ha="center", va="top", fontsize=6.5,
                    color="white")


def models_present(think: str) -> list[str]:
    return [m for m in MODEL_ORDER if any((m, think, c) in CELLS for c in COND_ORDER)]


_COND_COLORS = {
    "tools_all_minimal": "#2E86AB",
    "tools_per-task_minimal": "#A23B72",
    "no-tools": "#888888",
}


def _color_for_cond(cond: str) -> str:
    return _COND_COLORS.get(cond, "#1f77b4")


def fig_success_by_cond_per_task(think: str, save_path: Path) -> Path:
    models = models_present(think)
    n = len(models)
    cols = min(3, n)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 3.4 * rows), squeeze=False)
    width = 0.25
    x = np.arange(len(TASKS))
    for i, m in enumerate(models):
        ax = axes[i // cols][i % cols]
        for j, cond in enumerate(COND_ORDER):
            rows_ = CELLS.get((m, think, cond), [])
            vals = [task_success_rate(rows_, t)[0] * 100 for t in TASKS]
            ax.bar(x + (j - 1) * width, vals, width,
                   label=COND_DISP[cond], color=_color_for_cond(cond))
        ax.set_xticks(x)
        ax.set_xticklabels([TASK_LABEL[t] for t in TASKS], rotation=20, ha="right")
        ax.set_ylim(0, 105)
        ax.set_ylabel("success %")
        ax.set_title(MODEL_DISP[m])
        ax.grid(axis="y", linestyle=":", alpha=0.4)
    for k in range(n, rows * cols):
        axes[k // cols][k % cols].axis("off")
    handles = [plt.Rectangle((0, 0), 1, 1, color=_color_for_cond(c)) for c in COND_ORDER]
    labels = [COND_DISP[c] for c in COND_ORDER]
    fig.legend(handles, labels, loc="lower center", ncol=len(COND_ORDER),
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"Single-task success by condition (think={think})", y=0.995, fontsize=12)
    fig.tight_layout(rect=[0, 0.04, 1, 0.97])
    fig.savefig(save_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return save_path


def fig_tool_selection(save_path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    for ax, think in zip(axes, ["off", "on"]):
        models = models_present(think)
        x = np.arange(len(TASKS))
        width = 0.6 / max(1, len(models))
        for k, m in enumerate(models):
            rows_ = CELLS.get((m, think, "tools_all_minimal"), [])
            vals = [tool_selected_rate(rows_, t)[0] * 100 if rows_ else float("nan")
                    for t in TASKS]
            offset = (k - (len(models) - 1) / 2) * width
            ax.bar(x + offset, vals, width, label=MODEL_DISP[m])
        ax.set_xticks(x)
        ax.set_xticklabels([TASK_LABEL[t] for t in TASKS], rotation=20, ha="right")
        ax.set_title(f"think={think}")
        ax.set_ylim(0, 105)
        ax.set_ylabel("tool_selected %")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        if think == "off" and len(models) > 1:
            ax.legend(fontsize=8, loc="lower right")
    fig.suptitle("Tool-selection rate per task — all-tools condition", fontsize=12)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return save_path


def fig_successful_tool_use(save_path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    for ax, think in zip(axes, ["off", "on"]):
        models = models_present(think)
        x = np.arange(len(models))
        width = 0.4
        all_vals, sel_vals = [], []
        for m in models:
            rows_ = CELLS.get((m, think, "tools_all_minimal"), [])
            n_total = sum(1 for r in rows_ if r.get("with_tools"))
            n_succ = sum(1 for r in rows_ if r.get("with_tools") and r.get("tool_selected") and r.get("success"))
            n_sel  = sum(1 for r in rows_ if r.get("with_tools") and r.get("tool_selected"))
            all_vals.append(n_succ / n_total * 100 if n_total else float("nan"))
            sel_vals.append(n_sel / n_total * 100 if n_total else float("nan"))
        ax.bar(x - width / 2, sel_vals, width, label="tool_selected%", color="#A6CEE3")
        ax.bar(x + width / 2, all_vals, width, label="selected ∧ success%", color="#1F78B4")
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_DISP[m] for m in models], rotation=20, ha="right")
        ax.set_ylim(0, 110)
        ax.set_ylabel("% of with-tools trials")
        ax.set_title(f"think={think}")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.legend(fontsize=8)
    fig.suptitle("Tool-selection vs successful tool use — pooled across 5 tasks (all-tools cond)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return save_path


def fig_confusion_grid(save_path: Path, think: str) -> Path:
    models = models_present(think)
    if not models:
        # Empty figure rather than crash on a checkpoint with no cells for this think.
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.axis("off")
        ax.text(0.5, 0.5, f"(no cells for think={think})",
                ha="center", va="center", fontsize=12, color="#888")
        fig.savefig(save_path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        return save_path
    fig, axes = plt.subplots(len(models), 3, figsize=(11, 3.0 * len(models)))
    if len(models) == 1:
        axes = axes[None, :]
    for i, m in enumerate(models):
        rows_ = CELLS.get((m, think, "no-tools"), [])
        for j, task in enumerate(["validate_domain", "validate_problem", "validate_plan"]):
            ax = axes[i, j]
            cm = confusion(rows_, task)
            mx = np.array([[cm["tp"], cm["fn"]], [cm["fp"], cm["tn"]]])
            ax.imshow(mx, cmap="Blues")
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(["pred VALID", "pred INVALID"])
            ax.set_yticklabels(["true VALID", "true INVALID"])
            metr = metrics_from_cm(cm)
            for (r_, c_), v in np.ndenumerate(mx):
                color = "white" if v > mx.max() / 2 else "black"
                ax.text(c_, r_, str(v), ha="center", va="center", color=color)
            ax.set_title(
                f"{MODEL_DISP[m]} · {task}\n"
                f"prec={metr['precision']:.2f} rec={metr['recall']:.2f} "
                f"acc={metr['accuracy_all']:.2f}  no-ans={cm['no_ans']}",
                fontsize=8,
            )
    fig.suptitle(f"Confusion matrices · validation tasks · no-tools · think={think}", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(save_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return save_path


def fig_tokens(save_path: Path, only_success: bool = False,
               task: str | None = None) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    kinds = [("prompt", "input"), ("completion", "output")]
    for col, (key, disp) in enumerate(kinds):
        for row, think in enumerate(["off", "on"]):
            ax = axes[row, col]
            models = models_present(think)
            x = np.arange(len(models))
            width = 0.25
            for j, cond in enumerate(COND_ORDER):
                vals, fails = [], []
                for m in models:
                    rows_ = CELLS.get((m, think, cond), [])
                    ts = token_stats(rows_, task=task, only_success=only_success) if rows_ else None
                    vals.append(ts[key] if ts else float("nan"))
                    fails.append(ts["fail_pct"] if ts else float("nan"))
                bars = ax.bar(x + (j - 1) * width, vals, width,
                              label=COND_DISP[cond], color=_color_for_cond(cond))
                _annotate_bars(ax, bars, vals, fails)
            ax.set_xticks(x)
            ax.set_xticklabels([MODEL_DISP[m] for m in models], rotation=20, ha="right")
            ax.set_title(f"mean {disp} tokens · think={think}")
            ax.set_ylabel(f"{disp} tokens per trial")
            ax.margins(y=0.10)
            ax.grid(axis="y", linestyle=":", alpha=0.4)
            if row == 0 and col == 0:
                ax.legend(fontsize=8)
    sub = "successful trials only" if only_success else "all trials"
    scope = f"task = {task}" if task else "pooled across all 5 tasks"
    fig.suptitle(
        f"Input / output tokens per trial · {scope} · {sub}.  "
        f"Bar height = tokens (label on top).  Inset `f:NN%` = cell failure% (side metric).  "
        f"With-tools trials run a 2-turn agent loop so values are summed across both turns.",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(save_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return save_path


def fig_latency(save_path: Path, exclude_failures: bool) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, think in zip(axes, ["off", "on"]):
        models = models_present(think)
        x = np.arange(len(models))
        width = 0.25
        for j, cond in enumerate(COND_ORDER):
            vals, frates = [], []
            for m in models:
                rows_ = CELLS.get((m, think, cond), [])
                ls = latency_stats(rows_)
                if exclude_failures:
                    vals.append(ls["mean_succ"])
                else:
                    vals.append(ls["mean_all"])
                frates.append((ls["n_fail"] / ls["n"]) * 100 if ls["n"] else float("nan"))
            bars = ax.bar(x + (j - 1) * width, vals, width,
                          label=COND_DISP[cond], color=_color_for_cond(cond))
            _annotate_bars(ax, bars, vals, frates,
                           primary_fmt=lambda v: f"{v:.0f}s")
        ax.margins(y=0.10)
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_DISP[m] for m in models], rotation=20, ha="right")
        ax.set_title(f"think={think}")
        ax.set_ylabel("seconds (mean)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        if think == "off":
            ax.legend(fontsize=8)
    sub = "errors+failures excluded" if exclude_failures else "all trials, failures included"
    fig.suptitle(
        f"Time-to-response — {sub}.  "
        f"Bar height = mean seconds (top label).  Inset `f:NN%` = cell failure% (side metric).",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(save_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return save_path


def find_malformed_simulate_samples() -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for (m, t, c), rows_ in CELLS.items():
        if c != "no-tools":
            continue
        sims = [r for r in rows_ if r["task"] == "simulate"]
        if not sims:
            continue
        fr_counts: Counter = Counter(r.get("failure_reason") for r in sims)
        ranked = [fr for fr, _ in fr_counts.most_common() if fr and fr != "ok"]
        if not ranked:
            continue
        dom = ranked[0]
        candidates = [r for r in sims if r.get("failure_reason") == dom]
        candidates.sort(key=lambda r: len((r.get("response") or "")))
        non_empty = [r for r in candidates if (r.get("response") or "").strip()]
        pick = non_empty[0] if non_empty else candidates[0]
        out[(m, t)] = {"pick": pick, "fr_counts": fr_counts, "n_total": len(sims)}
    return out


def prettify_response(resp: str, max_lines: int = 16) -> str:
    text = (resp or "").strip()
    if not text:
        return "(empty response)"
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        if text.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            stripped = re.sub(r"\n?```\s*$", "", stripped)
            try:
                parsed = json.loads(stripped)
            except Exception:
                parsed = None
    if parsed is not None:
        text = json.dumps(parsed, indent=2, ensure_ascii=False)
    text = re.sub(r"\n{3,}", "\n\n", text).replace("\t", "  ")
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... [+{len(text.splitlines()) - max_lines} more lines]"]
    return "\n".join(lines)


# ---------------- PPTX writers ----------------

def _make_pptx() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    BLANK = prs.slide_layouts[6]
    slide = prs.slides.add_slide(BLANK)
    tx = slide.shapes.add_textbox(Inches(0.5), Inches(2.0), Inches(12.3), Inches(2.0))
    tf = tx.text_frame
    tf.text = title
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    tf.paragraphs[0].runs[0].font.size = Pt(36)
    tf.paragraphs[0].runs[0].font.bold = True
    p = tf.add_paragraph()
    p.text = subtitle
    p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size = Pt(18)
    p.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def add_image_slide(prs: Presentation, title: str, image_path: Path,
                    notes: str | None = None, caption: str | None = None) -> None:
    BLANK = prs.slide_layouts[6]
    slide = prs.slides.add_slide(BLANK)
    tbox = slide.shapes.add_textbox(Inches(0.3), Inches(0.15), Inches(12.7), Inches(0.5))
    tf = tbox.text_frame
    tf.text = title
    tf.paragraphs[0].runs[0].font.size = Pt(22)
    tf.paragraphs[0].runs[0].font.bold = True
    from PIL import Image
    with Image.open(image_path) as im:
        w_px, h_px = im.size
    max_w, max_h = 12.7, 6.2 if caption else 6.6
    aspect = w_px / h_px
    if max_w / aspect <= max_h:
        w_in = max_w
        h_in = max_w / aspect
    else:
        h_in = max_h
        w_in = max_h * aspect
    left = Inches((13.333 - w_in) / 2)
    top = Inches(0.75)
    slide.shapes.add_picture(str(image_path), left, top, width=Inches(w_in), height=Inches(h_in))
    if caption:
        cb = slide.shapes.add_textbox(Inches(0.4), prs.slide_height - Inches(0.85),
                                      Inches(12.5), Inches(0.7))
        ctf = cb.text_frame
        ctf.word_wrap = True
        ctf.text = caption
        for r in ctf.paragraphs[0].runs:
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def add_text_slide(prs: Presentation, title: str, bullets: list[str]) -> None:
    BLANK = prs.slide_layouts[6]
    slide = prs.slides.add_slide(BLANK)
    tbox = slide.shapes.add_textbox(Inches(0.3), Inches(0.15), Inches(12.7), Inches(0.5))
    tbox.text_frame.text = title
    tbox.text_frame.paragraphs[0].runs[0].font.size = Pt(22)
    tbox.text_frame.paragraphs[0].runs[0].font.bold = True
    body = slide.shapes.add_textbox(Inches(0.5), Inches(0.85), Inches(12.3), Inches(6.4))
    btf = body.text_frame
    btf.word_wrap = True
    for i, b in enumerate(bullets):
        p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
        p.text = b
        for run in p.runs:
            run.font.size = Pt(14)


def add_table_slide(prs: Presentation, title: str, headers: list[str],
                    rows: list[list[str]], notes: str | None = None) -> None:
    BLANK = prs.slide_layouts[6]
    slide = prs.slides.add_slide(BLANK)
    tbox = slide.shapes.add_textbox(Inches(0.3), Inches(0.15), Inches(12.7), Inches(0.5))
    tbox.text_frame.text = title
    tbox.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    tbox.text_frame.paragraphs[0].runs[0].font.bold = True
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table_w = Inches(12.7)
    table_h = Inches(min(6.4, 0.32 * n_rows + 0.4))
    table = slide.shapes.add_table(n_rows, n_cols, Inches(0.3), Inches(0.8),
                                   table_w, table_h).table
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(10)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0x33, 0x55, 0x88)
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(v)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def add_simulate_proof_slide(prs: Presentation, title: str, picks_by_cell: dict,
                              models_subset: list[str], think: str) -> None:
    from pptx.enum.shapes import MSO_SHAPE
    BLANK = prs.slide_layouts[6]
    slide = prs.slides.add_slide(BLANK)
    tbox = slide.shapes.add_textbox(Inches(0.3), Inches(0.1), Inches(12.7), Inches(0.45))
    tbox.text_frame.text = title
    tbox.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    tbox.text_frame.paragraphs[0].runs[0].font.bold = True

    n = len(models_subset)
    top0 = 0.60
    panel_h = (7.5 - top0 - 0.15) / max(n, 1)
    for i, m in enumerate(models_subset):
        info = picks_by_cell.get((m, think))
        panel_top = top0 + i * panel_h
        hdr = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.25), Inches(panel_top),
            Inches(12.83), Inches(0.36),
        )
        hdr.line.fill.background()
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = RGBColor(0x33, 0x55, 0x88)
        htf = hdr.text_frame
        htf.margin_left = Inches(0.12); htf.margin_right = Inches(0.12)
        htf.margin_top = Inches(0.02);  htf.margin_bottom = Inches(0.02)
        if info is None:
            label = f"{MODEL_DISP[m]} · no simulate trials in this cell"
        else:
            pk = info["pick"]
            fr = pk.get("failure_reason")
            n_fr = info["fr_counts"][fr]
            n_total = info["n_total"]
            label = (f"{MODEL_DISP[m]}  ·  failure_reason = {fr}  "
                     f"({n_fr}/{n_total} simulate trials, "
                     f"{n_fr/n_total*100:.0f}%)  ·  "
                     f"{pk['domain_name']}/{pk['problem_name']}")
        htf.text = label
        run = htf.paragraphs[0].runs[0]
        run.font.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        body_top = panel_top + 0.38
        body_h = panel_h - 0.42
        body = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.25), Inches(body_top),
            Inches(12.83), Inches(body_h),
        )
        body.line.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        body.line.width = Pt(0.5)
        body.fill.solid()
        body.fill.fore_color.rgb = RGBColor(0xF6, 0xF6, 0xF8)
        btf = body.text_frame
        btf.word_wrap = True
        btf.margin_left = Inches(0.15); btf.margin_right = Inches(0.15)
        btf.margin_top = Inches(0.08);  btf.margin_bottom = Inches(0.08)

        if info is None:
            btf.text = "(no simulate trials)"
            for r in btf.paragraphs[0].runs:
                r.font.size = Pt(11)
                r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
            continue
        max_lines = max(8, int(body_h / 0.18))
        snippet = prettify_response(info["pick"].get("response") or "", max_lines=max_lines)
        btf.text = snippet
        for para in btf.paragraphs:
            for r in para.runs:
                r.font.name = "Menlo"
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(0x11, 0x11, 0x22)


# ---------------- Slide composition ----------------

def build(out_pptx: Path, fig_dir: Path, captions: dict[str, str]) -> Presentation:
    fig_dir.mkdir(parents=True, exist_ok=True)
    prs = _make_pptx()

    add_title_slide(prs, TITLE, SUBTITLE)

    p_off = fig_success_by_cond_per_task("off", fig_dir / "success_by_cond_off.png")
    p_on  = fig_success_by_cond_per_task("on",  fig_dir / "success_by_cond_on.png")
    add_image_slide(prs, "Success rates: by condition (think=off)", p_off,
                    caption=captions["success_off"])
    add_image_slide(prs, "Success rates: by condition (think=on)", p_on,
                    caption=captions["success_on"])

    ts_path = fig_tool_selection(fig_dir / "tool_selection.png")
    add_image_slide(prs, "Tool selection rate (tool_selected_rate) per task", ts_path,
                    caption=captions["tool_selection"])

    su_path = fig_successful_tool_use(fig_dir / "successful_tool_use.png")
    add_image_slide(prs, "Tool-selection vs successful tool use (pooled across 5 tasks)", su_path,
                    caption=captions["successful_tool_use"])

    cm_off = fig_confusion_grid(fig_dir / "confusion_no_tools_off.png", "off")
    cm_on  = fig_confusion_grid(fig_dir / "confusion_no_tools_on.png", "on")
    add_image_slide(prs, "Validation tasks · no-tools · confusion matrices (think=off)", cm_off,
                    caption=captions["confusion_off"])
    add_image_slide(prs, "Validation tasks · no-tools · confusion matrices (think=on)", cm_on,
                    caption=captions["confusion_on"])

    for think in ["off", "on"]:
        headers = ["model", "task", "TP", "FP", "FN", "TN", "no-ans", "prec", "rec", "acc"]
        rows_out = []
        for m in models_present(think):
            for task in ["validate_domain", "validate_problem", "validate_plan"]:
                cm = confusion(CELLS.get((m, think, "no-tools"), []), task)
                metr = metrics_from_cm(cm)
                rows_out.append([
                    MODEL_DISP[m], TASK_LABEL[task],
                    str(cm["tp"]), str(cm["fp"]), str(cm["fn"]), str(cm["tn"]), str(cm["no_ans"]),
                    f"{metr['precision']:.2f}" if not np.isnan(metr['precision']) else "—",
                    f"{metr['recall']:.2f}" if not np.isnan(metr['recall']) else "—",
                    f"{metr['accuracy_all']:.2f}" if not np.isnan(metr['accuracy_all']) else "—",
                ])
        add_table_slide(prs, f"Validation-task metrics · no-tools · think={think}",
                        headers, rows_out,
                        notes="prec=TP/(TP+FP), rec=TP/(TP+FN), acc=(TP+TN)/all trials including no-ans.")

    picks = find_malformed_simulate_samples()
    all_models_with_data = [m for m in MODEL_ORDER
                            if any((m, t) in picks for t in ("off", "on"))]
    if all_models_with_data:
        add_simulate_proof_slide(prs,
            "Simulate · no-tools · failure proofs (think=off) — raw model output",
            picks, all_models_with_data, "off")
        add_simulate_proof_slide(prs,
            "Simulate · no-tools · failure proofs (think=on) — raw model output",
            picks, all_models_with_data, "on")

    add_text_slide(prs, "Note on token accounting (read before the next 6 slides)", TOKEN_NOTE_BULLETS)

    tok_path    = fig_tokens(fig_dir / "tokens.png", only_success=False)
    tok_ok_path = fig_tokens(fig_dir / "tokens_success_only.png", only_success=True)
    add_image_slide(prs, "Input / output tokens per trial · all trials (failures included)", tok_path,
                    caption=captions["tokens_all"])
    add_image_slide(prs, "Input / output tokens per trial · successful trials only", tok_ok_path,
                    caption=captions["tokens_succ"])

    for task in TASKS:
        fp = fig_dir / f"tokens_task_{task}.png"
        fig_tokens(fp, only_success=False, task=task)
        add_image_slide(prs, f"Tokens · {TASK_LABEL[task]} (input / output per trial)", fp,
                        caption=captions[f"tokens_{task}"])

    lat_all = fig_latency(fig_dir / "latency_all.png", exclude_failures=False)
    lat_ok  = fig_latency(fig_dir / "latency_ok.png",  exclude_failures=True)
    add_image_slide(prs, "Time-to-response · all trials (failures included)", lat_all,
                    caption=captions["latency_all"])
    add_image_slide(prs, "Time-to-response · successes only", lat_ok,
                    caption=captions["latency_succ"])

    prs.save(out_pptx)
    return prs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", required=True, type=Path,
                    help="path to a deck_config.py module (see docstring)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output .pptx path (overrides config.OUT_PPTX)")
    args = ap.parse_args()

    cfg = _load_config(args.config.resolve())

    out_pptx = args.out or getattr(cfg, "OUT_PPTX", None)
    if out_pptx is None:
        raise SystemExit("must set --out or config.OUT_PPTX")
    out_pptx = _resolve_path(out_pptx)
    out_pptx.parent.mkdir(parents=True, exist_ok=True)

    fig_dir = getattr(cfg, "FIG_DIR", None)
    fig_dir = _resolve_path(fig_dir) if fig_dir else out_pptx.with_suffix("").parent / (out_pptx.stem + "_figs")

    results_root = _resolve_path(cfg.RESULTS)
    if not results_root.is_dir():
        raise SystemExit(f"RESULTS dir does not exist: {results_root}")

    captions: dict[str, str] = dict(DEFAULT_CAPTIONS)
    captions.update(getattr(cfg, "SLIDE_CAPTIONS", {}) or {})

    # Populate module globals consumed by figure builders.
    global CELLS, MODEL_ORDER, MODEL_DISP, COND_ORDER, COND_DISP, TITLE, SUBTITLE
    CELLS = load_all(results_root)
    MODEL_ORDER = list(cfg.MODEL_ORDER)
    MODEL_DISP = dict(cfg.MODEL_DISP)
    COND_ORDER = list(cfg.COND_ORDER)
    COND_DISP = dict(cfg.COND_DISP)
    TITLE = cfg.TITLE
    SUBTITLE = cfg.SUBTITLE

    # Fail loud, not silent. A cell whose model slug isn't in MODEL_DISP would
    # KeyError deep in models_present() — we'd rather catch it at config load
    # and tell the user exactly which cells / slugs need adding. Silent drop
    # is the failure mode this skill is supposed to prevent post 2026-05.
    cell_models = {m for (m, _, _) in CELLS}
    unknown = sorted(cell_models - set(MODEL_DISP))
    if unknown:
        offending_cells = sorted(
            f"{m}/{th}/{c}" for (m, th, c) in CELLS if m in unknown
        )
        raise SystemExit(
            f"deck_config {args.config} is missing MODEL_DISP entries for "
            f"{len(unknown)} model slug(s) present in {results_root.relative_to(REPO)}:\n"
            + "\n".join(f"  - {m}" for m in unknown)
            + "\noffending cells:\n"
            + "\n".join(f"  - {c}" for c in offending_cells)
        )

    print(f"loaded {len(CELLS)} cells from {results_root.relative_to(REPO)}")
    print(f"models: {MODEL_ORDER}")
    print(f"conds:  {COND_ORDER}")
    print(f"output: {out_pptx.relative_to(REPO) if out_pptx.is_relative_to(REPO) else out_pptx}")

    build(out_pptx, fig_dir, captions)
    print("wrote", out_pptx)


if __name__ == "__main__":
    main()
