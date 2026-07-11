#!/usr/bin/env python3
"""Stratified keys-file generator for the stage-1 paired A-vs-B harness probe.

Emits the ~100-trial selection-key JSONL consumed by both probe arms
(`tools/frontier_runner.py --keys-file` and
`tools/claude_api_tools_probe.py --keys-file`), per the stage-1 plan in
development/frontier_rerun_handoff.md. One line per trial:

    {"task": ..., "domain_name": ..., "problem_name": ...,
     "plan_label": ..., "prompt_variant": 11}

Stratification (default --per-task 20 over the 20-domain corpus):
  * every task gets one trial per domain, so all 20 domains are covered in
    all 5 tasks;
  * within a task, fixture slots are quota-balanced then shuffled with a
    fixed seed before pairing with domains, so no fixture systematically
    co-occurs with the same domains:
      - solve / simulate      p01..p05 x4 each
      - validate_domain       p01 x4, p02..p05 x3, domain_neg x4
                              (grid ratio is 1/6 negative; 4/20 keeps the
                              invalid-domain path visibly represented)
      - validate_problem      p01..p05 + n01..n05 x2 each (grid is 50/50)
      - validate_plan         plan labels b1..b5 + v1..v5 x2 each (50/50
                              buggy/valid), problems p01..p05 x4 each
  * prompt_variant pinned (default 11 — the variant the old A-probe keys
    files used, and one of the old Sonnet NT corpus's v11-13, so the
    "slice the old corpus to the matching variant" comparison per frontier
    D3 stays available).

Every emitted key is asserted to exist in the real tools grid (enumerated
via the same `build_jobs` both consumers use, on the cached GT — selection
keys carry no GT payload, so the cache is fine here even though the live
probe must generate GT fresh).

Usage:
    python tools/make_stage1_keys.py --out .local/frontier/stage1_keys.jsonl
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pddl_eval.domains import load_domains
from pddl_eval.prompts import ACTIVE_PROMPT_VARIANTS
from pddl_eval.runner import build_jobs

J_TASK, J_DNAME, J_PNAME, J_PV, J_PLAN = 1, 2, 4, 6, 10
TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan",
         "simulate"]


def slot_quotas(n: int, values: list[str]) -> list[str]:
    """n slots spread over `values`: floor(n/len) each, remainder to the
    ends of the sorted list (deterministic, documented in the header)."""
    base, extra = divmod(n, len(values))
    slots = []
    for i, v in enumerate(values):
        # remainder goes to the first `extra` values after sorting with the
        # negative fixture(s) first, so invalid paths never lose slots
        slots.extend([v] * (base + (1 if i < extra else 0)))
    return slots


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--variant", type=int, default=11)
    p.add_argument("--per-task", type=int, default=20)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--gt-cache", default="results/derived/gt_cache.json")
    p.add_argument("--out", default=".local/frontier/stage1_keys.jsonl")
    args = p.parse_args()

    gt_path = Path(args.gt_cache)
    if not gt_path.exists():
        sys.exit(f"[keys] needs {gt_path} (build with tools/build_gt_cache.py)")
    domains = load_domains(Path("domains"))
    ground_truth = json.loads(gt_path.read_text())
    jobs, _ = build_jobs(
        models=["claude-haiku-4-5"], tasks=TASKS, domains=domains,
        ground_truth=ground_truth, num_variants=len(ACTIVE_PROMPT_VARIANTS),
        conditions="tools", tool_filter="all", prompt_style="minimal",
        think_tag="off",
    )
    grid = {(j[J_TASK], j[J_DNAME], j[J_PNAME], j[J_PLAN])
            for j in jobs if j[J_PV] == args.variant}
    if not grid:
        sys.exit(f"[keys] variant {args.variant} not in the tools grid")

    # per-task fixture inventory from the grid itself (no hardcoded names)
    by_task_problems: dict[str, list[str]] = {}
    by_task_labels: dict[str, list[str]] = {}
    domain_names = sorted({d for _, d, _, _ in grid})
    for t in TASKS:
        probs = sorted({pn for tt, _, pn, _ in grid if tt == t})
        # negative fixtures first so quota remainders land on them
        probs.sort(key=lambda s: (not (s.startswith("n") or "neg" in s), s))
        by_task_problems[t] = probs
        by_task_labels[t] = sorted({pl for tt, _, _, pl in grid if tt == t})

    n = args.per_task
    if n % len(domain_names):
        sys.exit(f"[keys] --per-task {n} must be a multiple of "
                 f"{len(domain_names)} domains (one-per-domain design)")
    rng = random.Random(args.seed)

    keys = []
    for t in TASKS:
        prob_slots = slot_quotas(n, by_task_problems[t])
        label_slots = slot_quotas(n, by_task_labels[t])
        rng.shuffle(prob_slots)
        rng.shuffle(label_slots)
        doms = domain_names * (n // len(domain_names))
        for d, pn, pl in zip(doms, prob_slots, label_slots):
            k = (t, d, pn, pl)
            assert k in grid, f"generated key not in grid: {k}"
            keys.append({"task": t, "domain_name": d, "problem_name": pn,
                         "plan_label": pl, "prompt_variant": args.variant})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for k in keys:
            fh.write(json.dumps(k) + "\n")

    print(f"[keys] wrote {len(keys)} keys -> {out}  "
          f"(variant={args.variant}, seed={args.seed})")
    for t in TASKS:
        tk = [k for k in keys if k["task"] == t]
        probs = Counter(k["problem_name"] for k in tk)
        labels = Counter(k["plan_label"] for k in tk if k["plan_label"])
        doms = len({k["domain_name"] for k in tk})
        line = (f"  {t:18s} n={len(tk):3d} domains={doms} "
                f"problems={dict(sorted(probs.items()))}")
        if labels:
            line += f" labels={dict(sorted(labels.items()))}"
        print(line)


if __name__ == "__main__":
    main()
