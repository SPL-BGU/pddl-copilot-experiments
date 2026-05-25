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

# Canonical arm classifier lives in pddl_eval/summary.py. Run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from pddl_eval.summary import NEUTRAL_VARIANTS  # noqa: E402
from pddl_eval.prompts import STEERED_VARIANTS  # noqa: E402

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
CONDITIONS = ["no-tools",
              "tools_per-task_minimal", "tools_per-task_guided",
              "tools_all_minimal", "tools_all_guided"]
# Active analysis ignores retired axes (per-task → sweep-5 retirement;
# guided → disabled in runner). `load_summaries` skips these by default.
RETIRED_CONDS = {
    "tools_per-task_minimal",
    "tools_per-task_guided",
    "tools_all_guided",
}

# Maps an analyzer arm suffix → the prompt_variant set whose per_variant cells
# pool into that arm. Pairs with the side prefix (nt/tl) derived from the cell
# dir's condition. Kept here instead of importing because `aggregate.py` is
# imported by `table.py` and we want the two to share one definition;
# legacy = "anything not in v11..v16" (sweep-3/4 corpora).
ARM_SUFFIXES = ("neut", "ster", "legacy")

# Filter/prompt encoded in the `condition` summary field for with-tools runs;
# we reconstruct the original condition label from dir name.


def find_default_root() -> Path:
    repo = Path(__file__).resolve().parents[4]
    results = repo / "results"
    candidates = sorted(
        list(results.glob("cluster-*")) + list(results.glob("full-cluster-run*")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(f"no results/cluster-* or results/full-cluster-run* dirs under {results}")
    return candidates[0]


def parse_dirname(name: str) -> dict:
    """Extract (model, think, cond, backend) from 'slurm_<…>' dir name.

    Accepts the cell-keyed layout (no trailing jobid; current), the
    pre-2026-05-01 with-jobid layout, and the pre-think-axis legacy
    layout. Model tag is the dotted form with ':' → '_' → '.' restored
    as '_' (we can't always recover exactly; store the raw tag and the
    reconstructed name).

    Backend prefix: 2026-05-11 added `slurm_vllm_<model>_<think>_<cond>/`
    for vLLM-served cells (see CHANGELOG). Strip the `vllm_` prefix
    BEFORE the cond/think suffix-match so model isn't silently captured
    with the prefix attached. Absent prefix → backend="ollama".
    """
    stem = name.removeprefix("slurm_")
    if stem.startswith("vllm_"):
        backend = "vllm"
        stem = stem.removeprefix("vllm_")
    else:
        backend = "ollama"
    # Optional trailing _<jobid>: present in pre-cell-keyed dirs, absent
    # in cell-keyed dirs (post 2026-05-01). When absent, fall through with
    # the full stem so the same suffix-matching logic finds <think>/<cond>.
    m = re.match(r"^(.*)_(\d+)$", stem)
    if m:
        rest, jobid = m.group(1), m.group(2)
    else:
        rest, jobid = stem, ""

    # Try current layout first: look for trailing _<cond> where cond ∈ CONDITIONS
    for cond in CONDITIONS:
        suf = "_" + cond
        if rest.endswith(suf):
            pre = rest[: -len(suf)]
            # remaining pre is <model>_<think> or <model>
            for think in ("on", "off", "default"):
                s = "_" + think
                if pre.endswith(s):
                    model = pre[: -len(s)]
                    return {"raw": stem, "model": model, "think": think,
                            "cond": cond, "jobid": jobid, "backend": backend}
            # legacy: no think segment
            return {"raw": stem, "model": pre, "think": "default",
                    "cond": cond, "jobid": jobid, "backend": backend,
                    "_legacy": True}
    return {"raw": stem, "model": rest, "think": "?", "cond": "?",
            "jobid": jobid, "backend": backend}


def host_tag(meta: dict) -> str:
    h = (meta or {}).get("host", "")
    if "localhost" in h or "ise-" in h or "cs-" in h:
        return "rtx"
    return h or "?"


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


def _arm_side(cond: str) -> str:
    """Map condition dir name → arm side prefix (nt | tl)."""
    return "nt" if cond == "no-tools" else "tl"


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


def _arm_variant_set(suffix: str) -> set[int] | None:
    """Variant set behind an arm suffix. None for 'legacy' (any non-active variant)."""
    if suffix == "neut":
        return set(NEUTRAL_VARIANTS)
    if suffix == "ster":
        return set(STEERED_VARIANTS)
    return None  # legacy = everything not in the active sets


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
