"""Focused, supervisor-friendly plots from a results root.

Companion to plot.py: the original 7 figures pack every (model × think × cond)
combination into shared axes (up to 50 bars per task), which is overwhelming
for a non-specialist audience. Each focused figure here answers ONE question
with at most two bars per model.

Usage:
    python3 plot_focused.py                               # auto: cluster-26042026
    python3 plot_focused.py checkpoints/cluster-26042026
    python3 plot_focused.py <root> --figs 1,5,7
    python3 plot_focused.py <root> --no-ci

Outputs go to <root>/plots/focused/.

Reuses helpers from plot.py to keep aesthetics consistent.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Reuse plot.py helpers/constants. plot.py lives in the same dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot import (  # noqa: E402
    CLASSICAL,
    MODEL_COLORS,
    MODEL_COLORS_NO_TOOLS,
    NUMERIC,
    TASK_LABELS,
    TASKS,
    THINK_LIGHTEN,
    _lighten,
    _wilson_err,
    load_series,
    parse_dirname,
    wilson_ci,
)

MODEL_ORDER = ["Qwen3_5_0_8B", "Qwen3_5_27b", "gemma4_31b", "gpt-oss_20b", "gpt-oss_120b"]
MODEL_LABELS = {
    "Qwen3_5_0_8B":  "Qwen3.5:0.8B",
    "Qwen3_5_27b":   "Qwen3.5:27B",
    "gemma4_31b":    "Gemma4:31B",
    "gpt-oss_20b":   "gpt-oss:20B",
    "gpt-oss_120b":  "gpt-oss:120B",
}
MCP_TOOLS = ["classic_planner", "numeric_planner", "validate_pddl_syntax",
             "get_state_transition", "save_plan"]
MCP_TOOL_LABELS = {
    "classic_planner":      "classic_planner",
    "numeric_planner":      "numeric_planner",
    "validate_pddl_syntax": "validate_syntax",
    "get_state_transition": "state_transition",
    "save_plan":            "save_plan",
}
DEFAULT_CHECKPOINT = "checkpoints/cluster-26042026"

CLASSICAL_SET = set(CLASSICAL)
NUMERIC_SET = set(NUMERIC)


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def find_repo_root() -> Path:
    """plot_focused.py lives at <repo>/.claude/skills/cluster-ops/scripts/."""
    return Path(__file__).resolve().parents[4]


def resolve_root(arg: Path | None) -> Path:
    """Pick a results root. Prefer the user-supplied path; else the default
    checkpoint. Auto-extracts results.zip into results_extracted/ if needed."""
    if arg is not None:
        root = arg
    else:
        root = find_repo_root() / DEFAULT_CHECKPOINT
    if not root.exists():
        sys.exit(f"results root does not exist: {root}")

    # Two layouts: (a) cluster-* dir with slurm_* subdirs directly (results/);
    # (b) checkpoint with results.zip + results_extracted/ subdir.
    # Match only directories (slurm_logs.zip would otherwise spoof slurm_*).
    def _has_slurm_dirs(d: Path) -> bool:
        return any(p.is_dir() for p in d.glob("slurm_*"))
    if _has_slurm_dirs(root):
        return root
    extracted = root / "results_extracted"
    if extracted.exists() and _has_slurm_dirs(extracted):
        return extracted
    zip_path = root / "results.zip"
    if zip_path.exists():
        print(f"extracting {zip_path} → {extracted}", file=sys.stderr)
        extracted.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extracted)
        return extracted
    sys.exit(f"no slurm_* dirs under {root} (and no results.zip to extract)")


def load_records(root: Path) -> list[dict]:
    """Load every slurm_* run + flatten into a per-trial record list with
    enriched fields (model, think, tool_filter, prompt_style)."""
    series = load_series(root, include_legacy=False)
    records: list[dict] = []
    for s in series:
        info = {"model": s["model"], "think": s["think"], "cond": s["cond"]}
        # Decompose cond into (with_tools, tool_filter, prompt_style).
        if s["cond"] == "no-tools":
            tf, ps, with_tools = "-", "-", False
        else:
            # cond = "tools_<filter>_<style>"
            parts = s["cond"].split("_", 2)
            # parts = ["tools", "all"|"per-task", "minimal"|"guided"]
            tf, ps, with_tools = parts[1], parts[2], True
        for inst in s.get("instances", []):
            rec = dict(inst)
            rec.setdefault("model_dir", info["model"])  # underscore form
            rec["think"] = info["think"]
            rec["cond"] = s["cond"]
            rec["tool_filter_dir"] = tf
            rec["prompt_style_dir"] = ps
            rec["with_tools_dir"] = with_tools
            records.append(rec)
    return records


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _models_present(records: list[dict]) -> list[str]:
    seen = {r["model_dir"] for r in records}
    return [m for m in MODEL_ORDER if m in seen]


def _agg_rate(records: list[dict], success_field: str = "success") -> tuple[int, int]:
    n = len(records)
    k = sum(1 for r in records if r.get(success_field))
    return k, n


def _bar_with_ci(ax, x, k, n, color, hatch=None, label=None,
                 width=0.4, edgecolor="black", linewidth=0.5, draw_ci=True):
    rate = (k / n) if n else 0.0
    ax.bar([x], [rate], width, color=color, edgecolor=edgecolor,
           linewidth=linewidth, hatch=hatch, label=label)
    if draw_ci and n > 0 and rate > 0:
        lo, hi = wilson_ci(k, n)
        el, eh = _wilson_err(rate, lo, hi)
        ax.errorbar([x], [rate], yerr=[[el], [eh]], fmt="none",
                    ecolor="black", elinewidth=0.7, capsize=2, capthick=0.7)
    if n == 0:
        return  # genuinely missing data — leave empty
    pct = int(round(rate * 100))
    if rate >= 0.92:
        # Put label inside the bar so it doesn't collide with the figure title.
        ax.text(x, rate - 0.04, f"{pct}", ha="center", va="top",
                fontsize=7, color="white", fontweight="bold")
    elif rate > 0.02:
        ax.text(x, rate + 0.012, f"{pct}", ha="center", va="bottom", fontsize=7)
    else:
        # Zero-bars are invisible against the axis; draw the baseline tick + 0
        # label so the reader sees this is data, not absent data.
        ax.plot([x - width / 2, x + width / 2], [0.003, 0.003],
                color=color, linewidth=2.0, solid_capstyle="butt")
        ax.text(x, 0.020, "0", ha="center", va="bottom", fontsize=6.5,
                color="#444")


def _setup_rate_axes(ax, model_centers, models, title, ylabel="Success rate"):
    ax.set_xticks(model_centers)
    ax.set_xticklabels([MODEL_LABELS[m] for m in models], rotation=15, ha="right",
                       fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_title(title, fontsize=10)
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)


def _legend_handle(color, label, hatch=None):
    from matplotlib.patches import Patch
    return Patch(facecolor=color, edgecolor="black", linewidth=0.5,
                 hatch=hatch, label=label)


def _color_for(model: str, think: str = "off", with_tools: bool = True) -> str:
    base = (MODEL_COLORS if with_tools else MODEL_COLORS_NO_TOOLS).get(model, "#888888")
    return _lighten(base, THINK_LIGHTEN.get(think, 0.0))


# ---------------------------------------------------------------------------
# fig 1: tools, think on vs off — one PNG per task
# ---------------------------------------------------------------------------

def fig1(records: list[dict], outdir: Path, draw_ci: bool):
    tools = [r for r in records if r["with_tools_dir"]]
    models = _models_present(tools)
    width = 0.40
    written = []
    for task in TASKS:
        sub = [r for r in tools if r["task"] == task]
        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        centers = []
        for i, m in enumerate(models):
            for j, think in enumerate(("off", "on")):
                cell = [r for r in sub if r["model_dir"] == m and r["think"] == think]
                k, n = _agg_rate(cell)
                x = i + (j - 0.5) * width * 1.05
                color = _color_for(m, think, with_tools=True)
                _bar_with_ci(ax, x, k, n, color, label=None, width=width, draw_ci=draw_ci)
            centers.append(i)
        handles = [
            _legend_handle("#555555", "think = off  (saturated)"),
            _legend_handle("#bbbbbb", "think = on   (lightened)"),
        ]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
                  fontsize=8, framealpha=0.9)
        _setup_rate_axes(ax, centers, models,
                         f"Task: {TASK_LABELS[task]} — does extended thinking help?\n"
                         f"with-tools, pooled across tool-filter and prompt-style"
                         + ("  (Wilson 95% CI)" if draw_ci else ""))
        out = outdir / f"plot1_tools_think_vs_nothink__{task}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=160, bbox_inches="tight")
        plt.close(fig)
        written.append(out.name)
        # stderr report of n's used
        ns = [(m, len([r for r in sub if r["model_dir"] == m and r["think"] == "off"]),
                  len([r for r in sub if r["model_dir"] == m and r["think"] == "on"]))
              for m in models]
        print(f"  plot1[{task}] n(off,on) per model: {ns}", file=sys.stderr)
    return written


# ---------------------------------------------------------------------------
# fig 2: with-tools vs no-tools at think=off — per task
# ---------------------------------------------------------------------------

def fig2(records: list[dict], outdir: Path, draw_ci: bool):
    off = [r for r in records if r["think"] == "off"]
    models = _models_present(off)
    width = 0.40
    written = []
    for task in TASKS:
        sub = [r for r in off if r["task"] == task]
        # Skip tasks where the no-tools condition wasn't run — empty bars
        # would mislead the reader into seeing 0% rather than "missing".
        if not any(not r["with_tools_dir"] for r in sub):
            print(f"  plot2[{task}] skipped (no no-tools trials)", file=sys.stderr)
            continue
        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        centers = []
        for i, m in enumerate(models):
            wt_cell = [r for r in sub if r["model_dir"] == m and r["with_tools_dir"]]
            nt_cell = [r for r in sub if r["model_dir"] == m and not r["with_tools_dir"]]
            for j, (cell, with_tools) in enumerate(((nt_cell, False), (wt_cell, True))):
                k, n = _agg_rate(cell)
                x = i + (j - 0.5) * width * 1.05
                color = _color_for(m, "off", with_tools=with_tools)
                _bar_with_ci(ax, x, k, n, color, label=None, width=width, draw_ci=draw_ci)
            centers.append(i)
        handles = [
            _legend_handle("#777777", "no-tools     (per-model dark variant)"),
            _legend_handle("#444477", "with-tools   (per-model base color)"),
        ]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
                  fontsize=8, framealpha=0.9)
        _setup_rate_axes(ax, centers, models,
                         f"Task: {TASK_LABELS[task]} — do tools help?\n"
                         f"think=off, with-tools (pooled) vs no-tools"
                         + ("  (Wilson 95% CI)" if draw_ci else ""))
        out = outdir / f"plot2_with_vs_no_tools_nothink__{task}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=160, bbox_inches="tight")
        plt.close(fig)
        written.append(out.name)
        ns = [(m, len([r for r in sub if r["model_dir"] == m and not r["with_tools_dir"]]),
                  len([r for r in sub if r["model_dir"] == m and r["with_tools_dir"]]))
              for m in models]
        print(f"  plot2[{task}] n(no-tools,with-tools) per model: {ns}", file=sys.stderr)
    return written


# ---------------------------------------------------------------------------
# fig 3: chain success, focused — 1×5 panels per model
# ---------------------------------------------------------------------------

def fig3(root: Path, outdir: Path, draw_ci: bool):
    """Re-load summary chain data per (model, think). Pool across tool variants.
    Drop no-tools (no chain data exists). x = chain length 1..5; lines for
    think on/off. L=1 is the single-task mean rate."""
    series = load_series(root, include_legacy=False)
    # Pool tool_* by (model, think) for chains and ST.
    bucket: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "st_k": {t: 0 for t in TASKS}, "st_n": {t: 0 for t in TASKS},
        "ch_k": {L: 0 for L in (2, 3, 4, 5)},
        "ch_n": {L: 0 for L in (2, 3, 4, 5)},
    })
    for s in series:
        if s["cond"] == "no-tools":
            continue
        key = (s["model"], s["think"])
        b = bucket[key]
        for r in s["summary"]["single_task"]:
            t = r["task"]
            if t in b["st_k"]:
                b["st_k"][t] += r["successes"]
                b["st_n"][t] += r["n"]
        for c in s["summary"].get("chains", []):
            L = c.get("chain_length")
            if L in b["ch_k"]:
                b["ch_k"][L] += c["successes"]
                b["ch_n"][L] += c["samples"]

    models = [m for m in MODEL_ORDER if any(m == k[0] for k in bucket)]
    if not models:
        print("  plot3: no chain data, skipping", file=sys.stderr)
        return []
    fig, axes = plt.subplots(1, len(models), figsize=(2.6 * len(models) + 0.6, 4.0),
                             sharey=True)
    if len(models) == 1:
        axes = [axes]
    Lx = [1, 2, 3, 4, 5]
    for ax, m in zip(axes, models):
        for think in ("off", "on"):
            b = bucket.get((m, think))
            if b is None:
                continue
            # L=1 from ST mean of rates (counts unequal across tasks; use mean
            # of per-task rates to match existing fig2 semantics)
            l1_rates = [b["st_k"][t] / b["st_n"][t] for t in TASKS if b["st_n"][t] > 0]
            l1 = float(np.mean(l1_rates)) if l1_rates else 0.0
            ys = [l1] + [
                (b["ch_k"][L] / b["ch_n"][L]) if b["ch_n"][L] > 0 else 0.0
                for L in (2, 3, 4, 5)
            ]
            color = _color_for(m, think)
            ax.plot(Lx, ys, marker="o", markersize=5, linewidth=1.5,
                    color=color, label=f"think = {think}")
            if draw_ci:
                lo_ys, hi_ys = [0.0], [0.0]
                for L in (2, 3, 4, 5):
                    if b["ch_n"][L] > 0:
                        lo, hi = wilson_ci(b["ch_k"][L], b["ch_n"][L])
                        lo_ys.append(lo); hi_ys.append(hi)
                    else:
                        lo_ys.append(0.0); hi_ys.append(0.0)
                ax.fill_between(Lx, lo_ys, hi_ys, color=color, alpha=0.13,
                                edgecolor="none")
        ax.set_xticks(Lx)
        ax.set_xlim(0.7, 5.3)
        ax.set_ylim(0, 1.0)
        ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax.set_title(MODEL_LABELS[m], fontsize=9)
        ax.set_xlabel("chain length L", fontsize=8)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Success rate", fontsize=9)
    handles = [
        _legend_handle("#555555", "think = off  (saturated)"),
        _legend_handle("#bbbbbb", "think = on   (lightened)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, -0.04), fontsize=8, frameon=False)
    fig.suptitle("Chained-task success vs chain length — tools pooled, per model"
                 + ("  (Wilson 95% CI ribbons)" if draw_ci else ""),
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    out = outdir / "plot3_chain_focused.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return [out.name]


# ---------------------------------------------------------------------------
# fig 4: tool_filter all vs per-task, per task
# ---------------------------------------------------------------------------

def fig4(records: list[dict], outdir: Path, draw_ci: bool):
    tools = [r for r in records if r["with_tools_dir"]]
    models = _models_present(tools)
    width = 0.40
    written = []
    for task in TASKS:
        sub = [r for r in tools if r["task"] == task]
        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        centers = []
        for i, m in enumerate(models):
            for j, tf in enumerate(("all", "per-task")):
                cell = [r for r in sub if r["model_dir"] == m and r["tool_filter_dir"] == tf]
                k, n = _agg_rate(cell)
                x = i + (j - 0.5) * width * 1.05
                color = _color_for(m, "off")  # neutral think; tool_filter shown via hatch
                hatch = None if tf == "all" else "...."
                _bar_with_ci(ax, x, k, n, color, hatch=hatch, label=None,
                             width=width, draw_ci=draw_ci)
            centers.append(i)
        handles = [
            _legend_handle("#888888", "all tools",          hatch=None),
            _legend_handle("#888888", "per-task allowlist", hatch="...."),
        ]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
                  fontsize=8, framealpha=0.9)
        _setup_rate_axes(ax, centers, models,
                         f"Task: {TASK_LABELS[task]} — what tools is the agent exposed to?\n"
                         f"all tools vs per-task allowlist (pooled across think and prompt-style)"
                         + ("  (Wilson 95% CI)" if draw_ci else ""))
        out = outdir / f"plot4_all_vs_pertask__{task}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=160, bbox_inches="tight")
        plt.close(fig)
        written.append(out.name)
    return written


# ---------------------------------------------------------------------------
# fig 5: classical vs numeric correct planner pick on solve, think on/off
# ---------------------------------------------------------------------------

def _correct_planner_first(rec: dict) -> bool | None:
    """For a solve trial in a tools condition, did the FIRST tool call invoke
    the right planner for the domain class? Returns None if not applicable
    (no-tools, no tool calls, or non-classical/numeric domain)."""
    if rec["task"] != "solve" or not rec["with_tools_dir"]:
        return None
    calls = rec.get("tool_calls") or []
    if not calls:
        return False  # tool was available but never invoked → wrong choice
    first_name = calls[0].get("name")
    dom = rec.get("domain_name")
    if dom in CLASSICAL_SET:
        return first_name == "classic_planner"
    if dom in NUMERIC_SET:
        return first_name == "numeric_planner"
    return None


def fig5(records: list[dict], outdir: Path, draw_ci: bool):
    tools = [r for r in records if r["with_tools_dir"] and r["task"] == "solve"]
    models = _models_present(tools)
    width = 0.40
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), sharey=True)
    for ax, dom_class, dom_set in zip(axes, ("classical", "numeric"),
                                      (CLASSICAL_SET, NUMERIC_SET)):
        sub = [r for r in tools if r["domain_name"] in dom_set]
        centers = []
        for i, m in enumerate(models):
            for j, think in enumerate(("off", "on")):
                cell = [r for r in sub if r["model_dir"] == m and r["think"] == think]
                k = sum(1 for r in cell if _correct_planner_first(r))
                n = len(cell)
                x = i + (j - 0.5) * width * 1.05
                color = _color_for(m, think)
                _bar_with_ci(ax, x, k, n, color, label=None, width=width, draw_ci=draw_ci)
            centers.append(i)
        _setup_rate_axes(ax, centers, models,
                         f"{dom_class.capitalize()} domains",
                         ylabel="Correct-planner-pick rate" if dom_class == "classical" else "")
    handles = [
        _legend_handle("#555555", "think = off  (saturated)"),
        _legend_handle("#bbbbbb", "think = on   (lightened)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, -0.02), fontsize=8, frameon=False)
    fig.suptitle("Correct planner selection on solve — classical needs classic_planner, "
                 "numeric needs numeric_planner"
                 + ("  (Wilson 95% CI)" if draw_ci else ""),
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    out = outdir / "plot5_planner_pick__solve.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return [out.name]


# ---------------------------------------------------------------------------
# fig 6: minimal vs guided prompt, per task
# ---------------------------------------------------------------------------

def fig6(records: list[dict], outdir: Path, draw_ci: bool):
    tools = [r for r in records if r["with_tools_dir"]]
    models = _models_present(tools)
    width = 0.40
    written = []
    for task in TASKS:
        sub = [r for r in tools if r["task"] == task]
        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        centers = []
        for i, m in enumerate(models):
            for j, ps in enumerate(("minimal", "guided")):
                cell = [r for r in sub if r["model_dir"] == m and r["prompt_style_dir"] == ps]
                k, n = _agg_rate(cell)
                x = i + (j - 0.5) * width * 1.05
                color = _color_for(m, "off")
                hatch = None if ps == "minimal" else "////"
                _bar_with_ci(ax, x, k, n, color, hatch=hatch, label=None,
                             width=width, draw_ci=draw_ci)
            centers.append(i)
        handles = [
            _legend_handle("#888888", "minimal prompt", hatch=None),
            _legend_handle("#888888", "guided prompt",  hatch="////"),
        ]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
                  fontsize=8, framealpha=0.9)
        _setup_rate_axes(ax, centers, models,
                         f"Task: {TASK_LABELS[task]} — does prompt nudging help?\n"
                         f"minimal vs guided (pooled across think and tool-filter)"
                         + ("  (Wilson 95% CI)" if draw_ci else ""))
        out = outdir / f"plot6_minimal_vs_guided__{task}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=160, bbox_inches="tight")
        plt.close(fig)
        written.append(out.name)
    return written


# ---------------------------------------------------------------------------
# fig 7: tools-used pivot table (md + heatmap PNG)
# ---------------------------------------------------------------------------

def _tool_invocations_per_cell(records: list[dict]) -> dict:
    """Return {(model, task, think): {tool_name: invocation_count_in_>=1_trial}}.
    Note: we count "trials in which this tool was invoked at least once",
    not raw call counts, since multiple calls within a trial don't add new
    information here."""
    counts: dict = defaultdict(lambda: defaultdict(int))
    for r in records:
        if not r["with_tools_dir"]:
            continue
        key = (r["model_dir"], r["task"], r["think"])
        seen_in_trial = set()
        for c in r.get("tool_calls") or []:
            name = c.get("name")
            if name in MCP_TOOLS and name not in seen_in_trial:
                seen_in_trial.add(name)
                counts[key][name] += 1
    return counts


def fig7(records: list[dict], outdir: Path, draw_ci: bool):
    counts = _tool_invocations_per_cell(records)
    models = _models_present([r for r in records if r["with_tools_dir"]])

    # Markdown table
    md_lines = []
    md_lines.append("# Plot 7 — Tools used per (model, task), think on vs off")
    md_lines.append("")
    md_lines.append("Each cell shows `(off / on)`: number of trials (out of "
                    "100 per cell — 50 minimal + 50 guided × 2 tool-filters / 2) "
                    "in which the tool was invoked at least once. "
                    "`+` = ≥1 trial used the tool; `−` = never used.")
    md_lines.append("")
    md_lines.append("## Boolean view (+/−)")
    md_lines.append("")
    header = "| model | task | " + " | ".join(MCP_TOOL_LABELS[t] for t in MCP_TOOLS) + " |"
    sep    = "|---|---|" + "|".join("---" for _ in MCP_TOOLS) + "|"
    md_lines.append(header); md_lines.append(sep)
    for m in models:
        for task in TASKS:
            cells = []
            for t in MCP_TOOLS:
                off = counts[(m, task, "off")].get(t, 0)
                on  = counts[(m, task, "on")].get(t, 0)
                cells.append(f"{'+' if off else '−'} / {'+' if on else '−'}")
            md_lines.append(f"| {MODEL_LABELS[m]} | {TASK_LABELS[task]} | "
                            + " | ".join(cells) + " |")
    md_lines.append("")
    md_lines.append("## Count view (off / on)")
    md_lines.append("")
    md_lines.append(header); md_lines.append(sep)
    for m in models:
        for task in TASKS:
            cells = []
            for t in MCP_TOOLS:
                off = counts[(m, task, "off")].get(t, 0)
                on  = counts[(m, task, "on")].get(t, 0)
                cells.append(f"{off} / {on}")
            md_lines.append(f"| {MODEL_LABELS[m]} | {TASK_LABELS[task]} | "
                            + " | ".join(cells) + " |")
    md_path = outdir / "plot7_tools_used_think_vs_nothink.md"
    md_path.write_text("\n".join(md_lines) + "\n")

    # Heatmap PNG: rows = (model × task), cols = tool × think_mode
    # Cell color = invocation count
    rows = [(m, t) for m in models for t in TASKS]
    cols = [(tool, th) for tool in MCP_TOOLS for th in ("off", "on")]
    grid = np.zeros((len(rows), len(cols)), dtype=float)
    for i, (m, task) in enumerate(rows):
        for j, (tool, th) in enumerate(cols):
            grid[i, j] = counts[(m, task, th)].get(tool, 0)
    fig, ax = plt.subplots(figsize=(11.0, max(5.0, 0.30 * len(rows) + 1.2)))
    vmax = max(1.0, float(grid.max()))
    im = ax.imshow(grid, cmap="Blues", aspect="auto", vmin=0, vmax=vmax)
    # Tick labels
    row_labels = [f"{MODEL_LABELS[m]} · {TASK_LABELS[t]}" for m, t in rows]
    col_labels = [f"{MCP_TOOL_LABELS[tool]}\n(think={th})" for tool, th in cols]
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels(row_labels, fontsize=6.5)
    ax.set_title("Tools invoked at least once — counts per (model × task) × (tool × think)",
                 fontsize=10)
    # Cell annotations: count, with +/- styling
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = int(grid[i, j])
            if v == 0:
                txt = "−"
                color = "#888"
            else:
                txt = str(v)
                color = "white" if v > vmax * 0.5 else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=6, color=color)
    # Group separators between tools
    for k in range(1, len(MCP_TOOLS)):
        ax.axvline(2 * k - 0.5, color="white", linewidth=1.2)
    # Group separators between models
    for k in range(1, len(models)):
        ax.axhline(len(TASKS) * k - 0.5, color="white", linewidth=1.2)
    fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02, label="trials with ≥1 invocation")
    fig.tight_layout()
    out = outdir / "plot7_tools_used_think_vs_nothink.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return [md_path.name, out.name]


# ---------------------------------------------------------------------------
# fig 8: extra plots (a) think delta, (b) guided delta, (c) planner misuse
# ---------------------------------------------------------------------------

def fig8a(records: list[dict], outdir: Path, draw_ci: bool):
    """Δ = success(think=on) − success(think=off), tools merged. x=model,
    one bar per task per model."""
    tools = [r for r in records if r["with_tools_dir"]]
    models = _models_present(tools)
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    width = 0.95 / len(TASKS)
    centers = []
    for i, m in enumerate(models):
        for j, task in enumerate(TASKS):
            off_cell = [r for r in tools if r["model_dir"] == m
                        and r["task"] == task and r["think"] == "off"]
            on_cell  = [r for r in tools if r["model_dir"] == m
                        and r["task"] == task and r["think"] == "on"]
            ko, no = _agg_rate(off_cell)
            kn, nn = _agg_rate(on_cell)
            ro = (ko / no) if no else 0.0
            rn = (kn / nn) if nn else 0.0
            delta = rn - ro
            x = i + (j - (len(TASKS) - 1) / 2) * width
            color = "#2ca02c" if delta >= 0 else "#d62728"
            ax.bar([x], [delta], width, color=color,
                   edgecolor="black", linewidth=0.5)
            if abs(delta) > 0.02:
                ax.text(x, delta + (0.012 if delta >= 0 else -0.018),
                        f"{int(round(delta * 100)):+d}",
                        ha="center", va="bottom" if delta >= 0 else "top",
                        fontsize=6.5)
        centers.append(i)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(centers)
    ax.set_xticklabels([MODEL_LABELS[m] for m in models], rotation=15, ha="right",
                       fontsize=8)
    ax.set_ylabel("Δ success rate (think=on − think=off)", fontsize=9)
    ax.set_ylim(-0.8, 0.85)
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    # Inline task ticks via secondary text (per model group)
    handles = []
    from matplotlib.patches import Patch
    handles.append(Patch(facecolor="#2ca02c", edgecolor="black", linewidth=0.5,
                         label="think helped"))
    handles.append(Patch(facecolor="#d62728", edgecolor="black", linewidth=0.5,
                         label="think hurt"))
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    # Annotate each in-group bar with task initial below x-axis
    for i, _ in enumerate(models):
        for j, task in enumerate(TASKS):
            x = i + (j - (len(TASKS) - 1) / 2) * width
            ax.text(x, -0.83, TASK_LABELS[task][0:3], ha="center", va="top",
                    fontsize=5.5, color="#444")
    ax.set_title("Where does extended thinking actually pay off? "
                 "Δ success per (model × task), tools pooled", fontsize=10)
    fig.tight_layout()
    out = outdir / "plot8a_think_benefit_delta.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return [out.name]


def fig8b(records: list[dict], outdir: Path, draw_ci: bool):
    """Δ = success(guided) − success(minimal), tools pooled, per (model, task)."""
    tools = [r for r in records if r["with_tools_dir"]]
    models = _models_present(tools)
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    width = 0.95 / len(TASKS)
    centers = []
    for i, m in enumerate(models):
        for j, task in enumerate(TASKS):
            min_cell = [r for r in tools if r["model_dir"] == m
                        and r["task"] == task and r["prompt_style_dir"] == "minimal"]
            gui_cell = [r for r in tools if r["model_dir"] == m
                        and r["task"] == task and r["prompt_style_dir"] == "guided"]
            km, nm = _agg_rate(min_cell)
            kg, ng = _agg_rate(gui_cell)
            rm = (km / nm) if nm else 0.0
            rg = (kg / ng) if ng else 0.0
            delta = rg - rm
            x = i + (j - (len(TASKS) - 1) / 2) * width
            color = "#1f77b4" if delta >= 0 else "#ff7f0e"
            ax.bar([x], [delta], width, color=color,
                   edgecolor="black", linewidth=0.5)
            if abs(delta) > 0.02:
                ax.text(x, delta + (0.012 if delta >= 0 else -0.018),
                        f"{int(round(delta * 100)):+d}",
                        ha="center", va="bottom" if delta >= 0 else "top",
                        fontsize=6.5)
        centers.append(i)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(centers)
    ax.set_xticklabels([MODEL_LABELS[m] for m in models], rotation=15, ha="right",
                       fontsize=8)
    ax.set_ylabel("Δ success rate (guided − minimal)", fontsize=9)
    ax.set_ylim(-0.8, 0.85)
    ax.yaxis.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor="#1f77b4", edgecolor="black", linewidth=0.5, label="guided helped"),
        Patch(facecolor="#ff7f0e", edgecolor="black", linewidth=0.5, label="guided hurt"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    for i, _ in enumerate(models):
        for j, task in enumerate(TASKS):
            x = i + (j - (len(TASKS) - 1) / 2) * width
            ax.text(x, -0.83, TASK_LABELS[task][0:3], ha="center", va="top",
                    fontsize=5.5, color="#444")
    ax.set_title("Does the guided prompt nudge help? "
                 "Δ success per (model × task), tool variants pooled", fontsize=10)
    fig.tight_layout()
    out = outdir / "plot8b_guided_benefit_delta.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return [out.name]


def fig8c(records: list[dict], outdir: Path, draw_ci: bool):
    """Wrong-planner rate: classic_planner picked on numeric domain, or
    numeric_planner picked on classical domain. solve task, with-tools."""
    tools = [r for r in records if r["with_tools_dir"] and r["task"] == "solve"]
    models = _models_present(tools)
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), sharey=True)
    width = 0.40
    for ax, dom_class, dom_set, wrong_planner in zip(
        axes,
        ("classical", "numeric"),
        (CLASSICAL_SET, NUMERIC_SET),
        ("numeric_planner", "classic_planner"),
    ):
        sub = [r for r in tools if r["domain_name"] in dom_set]
        centers = []
        for i, m in enumerate(models):
            for j, think in enumerate(("off", "on")):
                cell = [r for r in sub if r["model_dir"] == m and r["think"] == think]
                k = sum(1 for r in cell if (r.get("tool_calls") or [{}])[0].get("name") == wrong_planner)
                n = len(cell)
                x = i + (j - 0.5) * width * 1.05
                color = _color_for(m, think)
                _bar_with_ci(ax, x, k, n, color, label=None, width=width, draw_ci=draw_ci)
            centers.append(i)
        _setup_rate_axes(ax, centers, models,
                         f"{dom_class.capitalize()} domains — picked {wrong_planner}",
                         ylabel="Wrong-planner-pick rate" if dom_class == "classical" else "")
    handles = [
        _legend_handle("#555555", "think = off  (saturated)"),
        _legend_handle("#bbbbbb", "think = on   (lightened)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2,
               bbox_to_anchor=(0.5, -0.02), fontsize=8, frameon=False)
    fig.suptitle("Planner-mismatch failures on solve "
                 "(classical → numeric_planner, numeric → classic_planner)"
                 + ("  (Wilson 95% CI)" if draw_ci else ""),
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    out = outdir / "plot8c_planner_misuse.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return [out.name]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

FIG_KEYS = ("1", "2", "3", "4", "5", "6", "7", "8a", "8b", "8c", "8")


def _parse_figs(spec: str) -> set[str]:
    if spec == "all":
        out = {"1", "2", "3", "4", "5", "6", "7", "8a", "8b", "8c"}
        return out
    out: set[str] = set()
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if piece == "8":
            out.update({"8a", "8b", "8c"})
        elif piece in FIG_KEYS:
            out.add(piece)
        else:
            sys.exit(f"--figs: unknown {piece!r}; valid: {sorted(FIG_KEYS)} or 'all'")
    if not out:
        sys.exit("--figs: no figure keys parsed")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", type=Path, default=None,
                    help=f"results root (default: <repo>/{DEFAULT_CHECKPOINT})")
    ap.add_argument("--figs", default="all",
                    help="comma list (1,2,3,4,5,6,7,8a,8b,8c or 8 for all 8x); 'all'")
    ap.add_argument("--no-ci", dest="ci", action="store_false", default=True,
                    help="omit Wilson 95%% CI whiskers / ribbons")
    args = ap.parse_args()

    raw_root = args.root
    root = resolve_root(raw_root)
    print(f"results root: {root}", file=sys.stderr)

    records = load_records(root)
    print(f"loaded {len(records)} per-trial records "
          f"from {len({(r['model_dir'], r['think'], r['cond']) for r in records})} cells",
          file=sys.stderr)

    # Output dir is sibling to the (already-extracted) results root: we want
    # checkpoints/<name>/plots/focused/, not results_extracted/plots/focused/.
    if root.name == "results_extracted":
        outdir = root.parent / "plots" / "focused"
    else:
        outdir = root / "plots" / "focused"
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"writing to: {outdir}", file=sys.stderr)

    figs = _parse_figs(args.figs)
    written: list[str] = []

    if "1" in figs: written += fig1(records, outdir, args.ci)
    if "2" in figs: written += fig2(records, outdir, args.ci)
    if "3" in figs: written += fig3(root,    outdir, args.ci)
    if "4" in figs: written += fig4(records, outdir, args.ci)
    if "5" in figs: written += fig5(records, outdir, args.ci)
    if "6" in figs: written += fig6(records, outdir, args.ci)
    if "7" in figs: written += fig7(records, outdir, args.ci)
    if "8a" in figs: written += fig8a(records, outdir, args.ci)
    if "8b" in figs: written += fig8b(records, outdir, args.ci)
    if "8c" in figs: written += fig8c(records, outdir, args.ci)

    print(f"wrote {len(written)} files → {outdir}", file=sys.stderr)
    for f in written:
        print(f"  {f}")


if __name__ == "__main__":
    main()
