#!/usr/bin/env python3
"""Final decoupled think=on no-tools A/B rollup (all 4 Qwens, all 5 tasks).

Produced the "LINE COMPLETE" section in decoupled_run_handoff.md (2026-07-11).
Runs entirely on the synced trial dirs — no cluster / MCP needed.

Prereq: the 8 cell dirs under results/decoupled-rollup/ (gitignored). Re-sync
from the cluster if absent (4 decoupled + 4 sweep5v2 baseline cells):
  results/decoupled-rollup/slurm_vllm_<slug>_on_no-tools_decoupled-thinkon/trials.jsonl
  results/decoupled-rollup/slurm_vllm_<slug>_on_no-tools_sweep5v2/trials.jsonl

Matched join on trial `key`. Reports, per model x task:
  - baseline success (state-tracking) vs decoupled success, delta
  - Wilson 95% CIs for each side + CI-disjoint flag
  - empties, answer-truncation (done_reason==length), think_truncated (dec)
For simulate only:
  - decoupled Q1 three metrics: state-tracking / format-compliance / strict
  - baseline Q1-coercibility upper bound (pure _coerce_simulate_trajectory):
    baseline Q1 success <= coercible%, bounding the pre-Q1-vs-Q1 grader confound.
"""
import json, math, collections, sys
sys.path.insert(0, ".")
from pddl_eval.scoring import _coerce_simulate_trajectory

ROOT = "results/decoupled-rollup"
MODELS = [
    ("Qwen3.5:0.8B", "Qwen3_5_0_8B"),
    ("Qwen3.5:4B",   "Qwen3_5_4B"),
    ("Qwen3.5:9B",   "Qwen3_5_9B"),
    ("qwen3.6:35b",  "qwen3_6_35b"),
]
TASKS = ["validate_domain", "validate_problem", "validate_plan", "solve", "simulate"]


def load(path):
    out = {}
    for ln in open(path):
        ln = ln.strip()
        if not ln:
            continue
        rec = json.loads(ln)
        k = rec.get("key")
        k = tuple(k) if isinstance(k, list) else k
        out[k] = rec.get("result", rec)
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def empty(r):
    return not (r.get("response") or "").strip()


def pct(x):
    return f"{100*x:5.1f}"


sim_cross = []  # cross-model simulate summary

for disp, slug in MODELS:
    D = load(f"{ROOT}/slurm_vllm_{slug}_on_no-tools_decoupled-thinkon/trials.jsonl")
    B = load(f"{ROOT}/slurm_vllm_{slug}_on_no-tools_sweep5v2/trials.jsonl")
    common = [k for k in D if k in B]
    bytask = collections.defaultdict(list)
    for k in common:
        bytask[D[k].get("task")].append(k)

    print(f"\n{'='*104}\n{disp}   (matched keys: {len(common)} | dec-only "
          f"{len(D)-len(common)} | base-only {len(B)-len(common)})\n{'='*104}")
    print(f"{'task':<17}{'n':>5}  {'base%':>6} {'dec%':>6} {'delta':>6}  "
          f"{'base CI':>13} {'dec CI':>13}  disj  {'empt b->d':>10} {'trunc d':>8} {'think d':>8}")
    for t in TASKS:
        ks = bytask.get(t, [])
        if not ks:
            continue
        d = [D[k] for k in ks]
        b = [B[k] for k in ks]
        n = len(ks)
        bs = sum(1 for r in b if r.get("success") is True)
        ds = sum(1 for r in d if r.get("success") is True)
        b_lo, b_hi = wilson(bs, n)
        d_lo, d_hi = wilson(ds, n)
        disj = "yes" if (d_lo > b_hi or b_lo > d_hi) else "no"
        be = sum(1 for r in b if empty(r))
        de = sum(1 for r in d if empty(r))
        dtrunc = sum(1 for r in d if r.get("done_reason") == "length")
        dthink = sum(1 for r in d if r.get("think_truncated") is True)
        delta = 100 * (ds - bs) / n
        print(f"{t:<17}{n:>5}  {pct(bs/n)} {pct(ds/n)} {delta:>+6.1f}  "
              f"[{pct(b_lo)},{pct(b_hi)}] [{pct(d_lo)},{pct(d_hi)}]  {disj:>4}  "
              f"{be:>4}->{de:<4} {dtrunc:>8} {dthink:>8}")

        if t == "simulate":
            d_fc = sum(1 for r in d if r.get("format_compliant") is True)
            d_strict = sum(1 for r in d
                           if r.get("success") is True and r.get("format_compliant") is True)
            b_coerce = sum(1 for r in b
                           if _coerce_simulate_trajectory(r.get("response") or "")[0] is not None)
            sim_cross.append((disp, n, bs, ds, b_coerce, d_fc, d_strict))

print(f"\n{'#'*104}\nSIMULATE - cross-model capability gradient + Q1 apples-to-apples\n{'#'*104}")
print(f"{'model':<15}{'n':>5}  {'base succ (stored)':>19} {'base Q1<=coerce':>15}  "
      f"{'DEC state-track':>16} {'DEC fmt-compl':>13} {'DEC strict':>11}")
for disp, n, bs, ds, bc, dfc, dstrict in sim_cross:
    print(f"{disp:<15}{n:>5}  {bs:>4} ({pct(bs/n)}%)     "
          f"<={bc} ({pct(bc/n)}%)     "
          f"{ds:>4} ({pct(ds/n)}%)   {dfc:>4} ({pct(dfc/n)}%)  {dstrict:>4} ({pct(dstrict/n)}%)")
print("\n  base Q1<=coerce = upper bound on baseline state-tracking under the Q1 grader")
print("  (a non-coercible response cannot be a success). Confirms the simulate lift is")
print("  NOT a grader artifact: baseline stays ~0% even re-graded with Q1.")
