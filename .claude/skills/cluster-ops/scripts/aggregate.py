"""Aggregate every summary_*.json under a results root into Markdown tables.

Default root = the most recent results/cluster-* or results/full-cluster-run*.
Override with a positional arg.

Handles both naming schemes:
- Current: slurm_<model>_<think>_<cond>_<jobid>
- Legacy:  slurm_<model>_<cond>_<jobid>   (treated as think=default with a header warning)

Outputs (to stdout):
  1) Single-task success-rate matrix: (model, think, cond) × task
  2) Chain success-rate matrix:       (model, think, cond) × chain_length
  3) Failure-reason totals per cell
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
CONDITIONS = ["no-tools",
              "tools_per-task_minimal", "tools_per-task_guided",
              "tools_all_minimal", "tools_all_guided"]
CHAIN_LENGTHS = [2, 3, 4, 5]

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
    """Extract (model, think, cond) from 'slurm_<…>' dir name.

    Accepts both current (with <think>) and legacy (without) layouts. Model
    tag is the dotted form with ':' → '_' → '.' restored as '_' (we can't
    always recover exactly; store the raw tag and the reconstructed name).
    """
    stem = name.removeprefix("slurm_")
    # trailing _<jobid>
    m = re.match(r"^(.*)_(\d+)$", stem)
    if not m:
        return {"raw": stem, "model": stem, "think": "?", "cond": "?", "jobid": "?"}
    rest, jobid = m.group(1), m.group(2)

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
                            "cond": cond, "jobid": jobid}
            # legacy: no think segment
            return {"raw": stem, "model": pre, "think": "default",
                    "cond": cond, "jobid": jobid, "_legacy": True}
    return {"raw": stem, "model": rest, "think": "?", "cond": "?", "jobid": jobid}


def host_tag(meta: dict) -> str:
    h = (meta or {}).get("host", "")
    if "localhost" in h or "ise-" in h or "cs-" in h:
        return "rtx"
    return h or "?"


def load_summaries(root: Path):
    rows = []
    for d in sorted(root.glob("slurm_*")):
        if not d.is_dir():
            continue
        sfs = sorted(d.glob("summary_*.json"))
        if not sfs:
            continue
        with sfs[-1].open() as f:
            data = json.load(f)
        info = parse_dirname(d.name)
        info["host"] = host_tag(data.get("meta", {}))
        rows.append((info, data))
    return rows


def fmt_pct(num: int, n: int) -> str:
    if n == 0:
        return "—"
    return f"{(num / n) * 100:.0f}%"


def row_prefix(info: dict) -> str:
    return f"| {info['model']} | {info['think']} | {info['cond']} | {info['host']} | {info['jobid']} |"


def print_single_task_table(rows):
    print("## Single-task success rates (n=50 per task)")
    print()
    header = "| model | think | cond | host | jobid | " + " | ".join(TASKS) + " |"
    print(header)
    print("|" + "|".join(["---"] * (5 + len(TASKS))) + "|")

    for info, data in rows:
        cells = []
        for t in TASKS:
            rec = next((r for r in data["single_task"]
                        if r["task"] == t and r["n"] > 0), None)
            cells.append(fmt_pct(rec["successes"], rec["n"]) if rec else "—")
        print(f"{row_prefix(info)} " + " | ".join(cells) + " |")
    print()


def print_chain_table(rows):
    print("## Chain success rates")
    print()
    header = "| model | think | cond | host | jobid | " + " | ".join(f"L={L}" for L in CHAIN_LENGTHS) + " |"
    print(header)
    print("|" + "|".join(["---"] * (5 + len(CHAIN_LENGTHS))) + "|")

    for info, data in rows:
        cells = []
        for L in CHAIN_LENGTHS:
            rec = next((c for c in data.get("chains", [])
                        if c["chain_length"] == L and c.get("samples", 0) > 0), None)
            cells.append(fmt_pct(rec["successes"], rec["samples"]) if rec else "—")
        print(f"{row_prefix(info)} " + " | ".join(cells) + " |")
    print()


def print_failure_reasons(rows):
    print("## Failure reason totals (single-task, across all 5 tasks)")
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
        print(f"{row_prefix(info)} {top_s} |")
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
        print("> ⚠︎ Mixed legacy results present (no `<think>` segment). Legacy rows show as `think=default`. "
              "Chain sample counts may differ (legacy=20, current=100).")
    print()
    print_single_task_table(rows)
    print_chain_table(rows)
    print_failure_reasons(rows)


if __name__ == "__main__":
    main()
