"""Shared constants and helpers for the analyzer scripts.

Co-locating these here avoids per-script copies of TASKS, condition lists,
color/hatch maps, dirname parsing, and the `sys.path` bootstrap. Three
`parse_dirname_*` variants are kept distinct because their callers depend on
divergent return shapes — see each docstring.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Repo-root bootstrap so `from pddl_eval.* import …` resolves when the
# scripts run from the repo root. Each analyzer script imports from this
# module first, inheriting the path setup.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pddl_eval.prompts import STEERED_VARIANTS  # noqa: E402,F401
from pddl_eval.scoring import (  # noqa: E402,F401
    relabel_tool_arg_error_taxonomy,
    relabel_truncated_taxonomy,
)
from pddl_eval.summary import NEUTRAL_VARIANTS, arm_for, wilson_ci  # noqa: E402,F401


# ---------------------------------------------------------------------------
# Tasks + cells
# ---------------------------------------------------------------------------

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]

# Short labels used in plot/table/build_deck. `TASK_LABEL` is an alias kept
# for build_deck.py's singular spelling.
TASK_LABELS = {
    "solve": "Solve",
    "validate_domain": "Val-Dom",
    "validate_problem": "Val-Prob",
    "validate_plan": "Val-Plan",
    "simulate": "Simulate",
}
TASK_LABEL = TASK_LABELS

CONDITIONS = ["no-tools",
              "tools_per-task_minimal", "tools_per-task_guided",
              "tools_all_minimal", "tools_all_guided"]

# Conds the active analysis pipeline ignores (retired axes). `per-task` retired
# in sweep-5; `guided` is disabled in the runner. Loaders filter these out by
# default; pass `include_retired=True` to re-include them for pre-2026-05
# checkpoints.
RETIRED_CONDS = {
    "tools_per-task_minimal",
    "tools_per-task_guided",
    "tools_all_guided",
}

CLASSICAL = ["barman", "blocksworld", "depots", "rovers", "satellite"]
NUMERIC = ["counters", "depot", "farmland", "pogo_stick", "sailing"]
DOMAINS = CLASSICAL + NUMERIC

ACTIVE_ARMS = ("nt-neut", "nt-ster", "tl-neut", "tl-ster")
LEGACY_ARMS = ("nt-legacy", "tl-legacy")
ALL_ARMS = ACTIVE_ARMS + LEGACY_ARMS


# ---------------------------------------------------------------------------
# Style maps (model colors, condition hatches, think-mode lightening)
# ---------------------------------------------------------------------------

# One base color per model across all conds; cond is encoded by hatch.
# Keys are the underscore-tagged model form produced by `parse_dirname_*`
# (submit_with_rtx.sh does `tr '/:.' '___'`).
MODEL_COLORS = {
    "Qwen3_5_0_8B":   "#d4c96b",
    "Qwen3_5_4B":     "#a89535",
    "Qwen3_5_9B":     "#7a6b1c",
    "Qwen3_5_27b":    "#b89d2a",
    "qwen3_6_27b":    "#c97d3b",
    "qwen3_6_35b":    "#7b3f1d",
    "gpt-oss_20b":    "#5c7fb3",
    "gpt-oss_120b":   "#1a2e4f",
    "gemma4_31b":     "#6f4a8a",
    "gemma4_26b-a4b": "#9173b0",
}

COND_HATCH = {
    "no-tools":               "////",
    "tools_all_minimal":      None,
    "tools_per-task_minimal": "....",
    # Retained for back-compat re-plots of pre-2026-05 checkpoints.
    "tools_all_guided":       None,
    "tools_per-task_guided":  None,
    # Sweep-5 arms (used when split_series_by_arm replaces cond with an arm tag).
    "nt-neut":   "////",
    "nt-ster":   "xx",
    "tl-neut":   None,
    "tl-ster":   "...",
    "nt-legacy": "////",
    "tl-legacy": None,
}

# think-mode shade: on → lighter tint of the model base color.
THINK_LIGHTEN = {"off": 0.0, "default": 0.0, "on": 0.55}


def lighten(hex_color: str, factor: float) -> str:
    """Blend `hex_color` toward white by `factor` ∈ [0, 1]."""
    if factor <= 0.0:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


# Alias for legacy imports.
_lighten = lighten


# ---------------------------------------------------------------------------
# Failure-reason palette (unified on the vLLM-era ordering from build_deck.py)
# ---------------------------------------------------------------------------

# Canonical display order. Unknown reasons fall into 'other' / 'unknown'.
# `ollama_parse_error` is still emitted by the active vLLM runner for
# hermes/qwen3_xml/gemma4 tool-call-parser failures (see runner.py:74) — the
# tag name was retained for corpus continuity, not deprecated.
FAILURE_REASONS = [
    "ok", "think_overflow", "truncated_no_answer", "format_parse_fail",
    "verdict_mismatch", "result_mismatch", "no_verdict_parsed",
    "plan_invalid", "simulate_empty",
    "tool_not_selected", "tool_error", "wrong_tool", "ollama_parse_error",
    "loop_exhausted", "exception", "unknown",
]

FAILURE_COLORS = {
    "ok":                  "#2ca02c",
    "think_overflow":      "#f7b6d2",
    "truncated_no_answer": "#aec7e8",
    "format_parse_fail":   "#c49c94",
    "verdict_mismatch":    "#e377c2",
    "result_mismatch":     "#7f7f7f",
    "no_verdict_parsed":   "#9edae5",
    "plan_invalid":        "#1f77b4",
    "simulate_empty":      "#bcbd22",
    "tool_not_selected":   "#d62728",
    "tool_error":          "#ff7f0e",
    "wrong_tool":          "#fbb4b9",
    "ollama_parse_error":  "#9467bd",
    "loop_exhausted":      "#8c564b",
    "exception":           "#17becf",
    "unknown":             "#cccccc",
    "other":               "#dddddd",
}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def find_default_root() -> Path:
    """Most-recent results/cluster-* or results/full-cluster-run* dir."""
    results = _REPO_ROOT / "results"
    candidates = sorted(
        list(results.glob("cluster-*")) + list(results.glob("full-cluster-run*")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(f"no results/cluster-* or results/full-cluster-run* dirs under {results}")
    return candidates[0]


def host_tag(meta: dict) -> str:
    h = (meta or {}).get("host", "")
    if "localhost" in h or "ise-" in h or "cs-" in h:
        return "rtx"
    return h or "?"


# ---------------------------------------------------------------------------
# Dirname parsing — 3 variants kept distinct (callers expect different shapes)
# ---------------------------------------------------------------------------

def parse_dirname_full(name: str) -> dict:
    """`aggregate.py`-shape parser. Always returns a dict, even on miss.

    Misses come back as `{"raw": stem, "model": rest, "think": "?", "cond": "?",
    "jobid": ..., "backend": ...}` so loaders can surface them as warnings
    rather than silently dropping the dir.
    """
    stem = name.removeprefix("slurm_")
    if stem.startswith("vllm_"):
        backend = "vllm"
        stem = stem.removeprefix("vllm_")
    else:
        backend = "ollama"
    m = re.match(r"^(.*)_(\d+)$", stem)
    if m:
        rest, jobid = m.group(1), m.group(2)
    else:
        rest, jobid = stem, ""
    for cond in CONDITIONS:
        suf = "_" + cond
        if rest.endswith(suf):
            pre = rest[: -len(suf)]
            for think in ("on", "off", "default"):
                s = "_" + think
                if pre.endswith(s):
                    model = pre[: -len(s)]
                    return {"raw": stem, "model": model, "think": think,
                            "cond": cond, "jobid": jobid, "backend": backend}
            return {"raw": stem, "model": pre, "think": "default",
                    "cond": cond, "jobid": jobid, "backend": backend,
                    "_legacy": True}
    return {"raw": stem, "model": rest, "think": "?", "cond": "?",
            "jobid": jobid, "backend": backend}


def parse_dirname_plotshape(name: str) -> dict | None:
    """`plot.py`-shape parser. Returns None on no-match; flatter dict on match.

    Distinct from `parse_dirname_full` because plot loaders skip non-matches
    rather than carrying them through as warnings.
    """
    stem = name.removeprefix("slurm_")
    if stem.startswith("vllm_"):
        backend = "vllm"
        stem = stem.removeprefix("vllm_")
    else:
        backend = "ollama"
    m = re.match(r"^(.*)_(\d+)$", stem)
    if m:
        rest, jobid = m.group(1), m.group(2)
    else:
        rest, jobid = stem, ""
    for cond in CONDITIONS:
        suf = "_" + cond
        if rest.endswith(suf):
            pre = rest[: -len(suf)]
            for think in ("on", "off", "default"):
                s = "_" + think
                if pre.endswith(s):
                    model = pre[: -len(s)]
                    return {"model": model, "think": think, "cond": cond,
                            "jobid": jobid, "backend": backend}
            return {"model": pre, "think": "default", "cond": cond,
                    "jobid": jobid, "backend": backend, "legacy": True}
    return None


def parse_cell_name_tuple(name: str) -> tuple[str, str, str] | None:
    """`build_deck.py`-shape parser. Returns (model, think, cond) or None."""
    info = parse_dirname_plotshape(name)
    if info is None:
        return None
    return (info["model"], info["think"], info["cond"])


# ---------------------------------------------------------------------------
# Arm helpers (used by aggregate.py + plot.py)
# ---------------------------------------------------------------------------

def arm_side(cond: str) -> str:
    """Map condition dir name → arm side prefix (nt | tl)."""
    return "nt" if cond == "no-tools" else "tl"


def arm_variant_set(suffix: str) -> set[int] | None:
    """Variant set behind an arm suffix. None for 'legacy' (any non-active variant)."""
    if suffix == "neut":
        return set(NEUTRAL_VARIANTS)
    if suffix == "ster":
        return set(STEERED_VARIANTS)
    return None


# Aliases for legacy imports.
_arm_side = arm_side
_arm_variant_set = arm_variant_set


# ---------------------------------------------------------------------------
# Loader helpers — shared `slurm_*` directory walk + file pickers
# ---------------------------------------------------------------------------
#
# Five scripts walk `<root>/slurm_*` cells and read summary_*.json /
# single_task_*.json / trials.jsonl with subtly different filters. The
# helpers below cover the directory walk + file picking + trial streaming
# so each script only owns the part of the shape it actually needs.

import json  # noqa: E402


def iter_cells(root: Path, *, include_retired: bool = False,
               include_legacy: bool = True, parser: str = "full"):
    """Yield `(cell_dir, info)` for every `slurm_*` subdirectory of `root`.

    Parameters mirror the per-script signatures the loaders previously used
    inline:

    - `parser`: which `parse_dirname_*` variant to apply.
      - `"full"` (default) → `parse_dirname_full`; misses come back with
        `cond="?"` and the caller can warn.
      - `"plotshape"` → `parse_dirname_plotshape`; misses are skipped silently
        (loader convention in plot.py / plot_focused.py).
    - `include_retired`: when False (default), drops cells whose `cond` is in
      `RETIRED_CONDS` (per-task / guided arms retired in sweep-5).
    - `include_legacy`: when False, drops cells flagged with `legacy=True`
      from the plotshape parser (pre-think axis).

    The walk uses `sorted(root.glob("slurm_*"))` to keep output deterministic
    across callers.
    """
    for d in sorted(root.glob("slurm_*")):
        if not d.is_dir():
            continue
        if parser == "full":
            info = parse_dirname_full(d.name)
            if not include_retired and info.get("cond") in RETIRED_CONDS:
                continue
        elif parser == "plotshape":
            info = parse_dirname_plotshape(d.name)
            if info is None:
                continue
            if info.get("legacy") and not include_legacy:
                continue
            if not include_retired and info.get("cond") in RETIRED_CONDS:
                continue
        else:
            raise ValueError(f"unknown parser: {parser!r}")
        yield d, info


def latest_summary(cell_dir: Path) -> dict | None:
    """Load the newest `summary_*.json` in `cell_dir`, or None if absent."""
    sfs = sorted(cell_dir.glob("summary_*.json"))
    if not sfs:
        return None
    with sfs[-1].open() as f:
        return json.load(f)


def latest_single_task(cell_dir: Path) -> list | None:
    """Load the newest `single_task_*.json` in `cell_dir`, or None if absent."""
    stfs = sorted(cell_dir.glob("single_task_*.json"))
    if not stfs:
        return None
    with stfs[-1].open() as f:
        return json.load(f)


def iter_trials(cell_dir: Path, *, relabel: bool = False,
                think_mode: str | None = None):
    """Stream parsed `result` dicts from `cell_dir/trials.jsonl`.

    Bad lines (partial tail, malformed JSON, missing `result` key) are
    dropped silently — same policy as `pddl_eval.resume.load_progress`.

    When `relabel=True`, applies the two read-time taxonomy fixes that
    `build_deck.load_all` historically did inline:
      1. FR_TRUNCATED_NO_ANSWER → FR_THINK_OVERFLOW when response was empty
         under think=on (requires `think_mode`; pass the cell's think tag).
      2. FastMCP arg-validation strings → FR_TOOL_ERROR (pre-`_tool_error_seen`
         corpora).
    trials.jsonl is never mutated; the relabel mutates the in-memory dict
    only.
    """
    fp = cell_dir / "trials.jsonl"
    if not fp.exists():
        return
    with fp.open() as f:
        for line in f:
            try:
                r = json.loads(line)["result"]
            except (json.JSONDecodeError, KeyError):
                continue
            if relabel:
                r["failure_reason"] = relabel_truncated_taxonomy(
                    r.get("failure_reason", ""),
                    truncated=bool(r.get("truncated")),
                    response=r.get("response") or "",
                    think_mode=think_mode or r.get("think", ""),
                )
                r["failure_reason"] = relabel_tool_arg_error_taxonomy(
                    r["failure_reason"],
                    task=r.get("task", ""),
                    tool_calls=r.get("tool_calls") or [],
                )
            yield r


def decompose_cond(cond: str) -> tuple[str, str]:
    """Split a tools-condition slug into (tool_filter, prompt_style) parts.

    `no-tools` returns `("-", "-")`. `tools_all_minimal` → `("all", "minimal")`,
    `tools_per-task_guided` → `("per-task", "guided")`. Inverse of
    `f"tools_{tf}_{ps}"` for active conds.
    """
    if cond == "no-tools":
        return ("-", "-")
    if cond.startswith("tools_"):
        rest = cond[len("tools_"):]
        # tool_filter is up to the last underscore; prompt_style is the suffix.
        idx = rest.rfind("_")
        if idx > 0:
            return (rest[:idx], rest[idx + 1:])
        return ("-", "-")
    return ("-", "-")
