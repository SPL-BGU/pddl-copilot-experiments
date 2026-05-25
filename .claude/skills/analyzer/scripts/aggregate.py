"""Aggregate every summary_*.json under a results root into Markdown tables.

Default root = the most recent results/cluster-* or results/full-cluster-run*.
Override with a positional arg.

Handles three naming schemes:
- Cell-keyed (current, post 2026-05-01): slurm_<model>_<think>_<cond>
  One dir per cell; resubmits accumulate timestamped summary_*.json files
  inside, and the latest one wins (sorted glob).
- With-jobid (pre 2026-05-01):           slurm_<model>_<think>_<cond>_<jobid>
- Legacy (pre think axis):               slurm_<model>_<cond>_<jobid>
  (treated as think=default with a header warning)

Outputs (to stdout):
  1) Single-task success-rate matrix: (model, think, cond) × task
  2) Failure-reason totals per cell
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

from _constants import (  # noqa: E402
    CONDITIONS,
    NEUTRAL_VARIANTS,
    RETIRED_CONDS,
    STEERED_VARIANTS,
    TASKS,
    arm_side as _arm_side,
    arm_variant_set as _arm_variant_set,
    find_default_root,
    host_tag,
    parse_dirname_full as parse_dirname,
)

# Maps an analyzer arm suffix → the prompt_variant set whose per_variant cells
# pool into that arm. Pairs with the side prefix (nt/tl) derived from the cell
# dir's condition. `legacy` = "anything not in v11..v16" (sweep-3/4 corpora).
ARM_SUFFIXES = ("neut", "ster", "legacy")


def load_summaries(root: Path, include_retired: bool = False):
    """Load every cell's latest `summary_*.json` into (info, data) tuples.

    `include_retired=True` re-includes pre-2026-05 checkpoints that legitimately
    contain `tools_per-task_*` / `tools_all_guided` cells — matches the
    signature of `plot.load_series`. `drift_check` re-aggregating a sweep-3
    baseline should set this to True so per-task cells aren't silently dropped.
    """
    rows = []
    for d in sorted(root.glob("slurm_*")):
        if not d.is_dir():
            continue
        sfs = sorted(d.glob("summary_*.json"))
        if not sfs:
            continue
        info = parse_dirname(d.name)
        if not include_retired and info.get("cond") in RETIRED_CONDS:
            continue
        with sfs[-1].open() as f:
            data = json.load(f)
        info["host"] = host_tag(data.get("meta", {}))
        rows.append((info, data))
    return rows


def fmt_pct(num: int, n: int) -> str:
    if n == 0:
        return "—"
    return f"{(num / n) * 100:.0f}%"


def _variants_present(data: dict) -> set[int]:
    """Union of prompt_variant keys across every per_variant cell in the summary.

    Empty for pre-per_variant corpora (the analyzer falls back to a single
    *-legacy row in that case).
    """
    out: set[int] = set()
    for rec in data.get("single_task", []):
        for k in (rec.get("per_variant", {}) or {}).keys():
            try:
                out.add(int(k))
            except (TypeError, ValueError):
                continue
    return out


def _arms_present(data: dict, cond: str) -> list[str]:
    """List of arm labels (e.g. 'tl-neut', 'tl-ster') that have at least one
    per_variant cell in this summary. Falls back to '*-legacy' for corpora
    without a `per_variant` field or whose variants are all v0-v10.
    """
    side = _arm_side(cond)
    present = _variants_present(data)
    arms: list[str] = []
    if present & NEUTRAL_VARIANTS:
        arms.append(f"{side}-neut")
    if present & STEERED_VARIANTS:
        arms.append(f"{side}-ster")
    if present and not (present & (NEUTRAL_VARIANTS | STEERED_VARIANTS)):
        arms.append(f"{side}-legacy")
    if not arms:
        arms.append(f"{side}-legacy")
    return arms


def _pool_arm(data: dict, task: str, arm: str) -> tuple[int, int, dict[str, int]]:
    """Pool per_variant cells matching this arm. Returns (successes, n, fr_counts).

    The pooling sums k and n across variants — the rate is the pooled
    point-estimate (Wilson CI applied downstream in plot/table; aggregate
    only renders %).
    """
    rec = next((r for r in data.get("single_task", [])
                if r["task"] == task and r["n"] > 0), None)
    if rec is None:
        return 0, 0, {}
    pv_dict = rec.get("per_variant", {}) or {}
    if not pv_dict:
        # Legacy corpus: no per_variant — treat the whole cell as one arm.
        return rec["successes"], rec["n"], rec.get("failure_reasons", {}) or {}
    suffix = arm.split("-", 1)[1] if "-" in arm else "legacy"
    target = _arm_variant_set(suffix)
    k = n = 0
    fr: dict[str, int] = {}
    for vk, cell in pv_dict.items():
        try:
            v = int(vk)
        except (TypeError, ValueError):
            continue
        if target is None:
            # legacy bucket pools everything outside v11..v16
            if v in (NEUTRAL_VARIANTS | STEERED_VARIANTS):
                continue
        else:
            if v not in target:
                continue
        k += cell.get("successes", 0)
        n += cell.get("n", 0)
        # per_variant cells do not carry failure_reasons — those live on the
        # whole-cell record. We approximate by scaling whole-cell counts by
        # n_pooled / n_whole; safer to leave per-arm FR pooling to the
        # trials.jsonl readers (build_deck, plot_focused). aggregate.md
        # shows whole-cell FR totals only.
    return k, n, fr


def row_prefix(info: dict, arm: str) -> str:
    return (f"| {info['model']} | {info['think']} | {info['cond']} | {arm} "
            f"| {info['host']} | {info['jobid']} |")


def print_single_task_table(rows):
    print("## Single-task success rates (per-arm, pooled from per_variant)")
    print()
    header = "| model | think | cond | arm | host | jobid | " + " | ".join(TASKS) + " |"
    print(header)
    print("|" + "|".join(["---"] * (6 + len(TASKS))) + "|")

    for info, data in rows:
        for arm in _arms_present(data, info["cond"]):
            cells = []
            for t in TASKS:
                k, n, _ = _pool_arm(data, t, arm)
                cells.append(fmt_pct(k, n) if n > 0 else "—")
            print(f"{row_prefix(info, arm)} " + " | ".join(cells) + " |")
    print()


def print_failure_reasons(rows):
    print("## Failure reason totals (whole-cell across 5 tasks; arms not split)")
    print("_FR_* counts come from the whole-cell `failure_reasons` field, which is_")
    print("_not arm-tagged in summary_*.json. Per-arm FR breakdowns require_")
    print("_trials.jsonl ingest (see build_deck.py / plot_focused.py)._")
    print()
    print("| model | think | cond | host | jobid | top 3 reasons (count) |")
    print("|---|---|---|---|---|---|")
    for info, data in rows:
        agg: dict[str, int] = {}
        for r in data["single_task"]:
            if r["n"] == 0:
                continue
            for k, v in r.get("failure_reasons", {}).items():
                if k == "ok":
                    continue
                agg[k] = agg.get(k, 0) + v
        top = sorted(agg.items(), key=lambda kv: -kv[1])[:3]
        top_s = ", ".join(f"{k}={v}" for k, v in top) if top else "(none)"
        # The FR table keeps its pre-arm prefix so legacy callers still parse;
        # arm-aware FR breakdown lives in the per-trial scripts.
        prefix = (f"| {info['model']} | {info['think']} | {info['cond']} "
                  f"| {info['host']} | {info['jobid']} |")
        print(f"{prefix} {top_s} |")
    print()


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else find_default_root()
    rows = load_summaries(root)
    if not rows:
        sys.exit(f"no summary_*.json found under {root}")

    has_legacy = any(info.get("_legacy") for info, _ in rows)
    print(f"# Aggregate — `{root}`")
    print()
    print(f"_{len(rows)} completed job(s)_")
    if has_legacy:
        print()
        print("> ⚠︎ Mixed legacy results present (no `<think>` segment). Legacy rows show as `think=default`.")
    print()
    print_single_task_table(rows)
    print_failure_reasons(rows)


if __name__ == "__main__":
    main()
