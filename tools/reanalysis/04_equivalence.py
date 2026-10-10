#!/usr/bin/env python3
"""Item 5: equivalence tests (TOST, margin +/-5 points) for the two results the
paper reports as nulls from overlapping intervals.

  (a) contamination: canonical (results/sweep5v2-live) vs anonymized
      (results/sweep6-live), no-tools arm, harness `success` (for no-tools rows
      this is the online grade of the model's own full answer, exact on every
      row). Delta = anonymized - canonical, the paper's sign convention.
  (b) serving version: vLLM 0.22.0 vs 0.20.2 on the one cell that exists at
      both versions (Qwen3.5-0.8B, think=off, with-tools, canonical, 9,120
      trials). The two 0.22.0 runs survive only as backups under
      results/vllm0220-backup/*.v0220-bak (moved there on 2026-10-10 from
      results/sweep5-cluster-20260601; NUMBERS.md "Serving environment").

Method, following the steering-control prereg conventions already used in the
paper: trials are paired on the exact trial key; the interval is a 90%
cluster-robust t interval on the paired difference; both the domain (k=20) and
the problem clustering are computed and the WIDER one governs. The criterion is
met when the governing 90% interval lies wholly inside (-5, +5), which is the
two one-sided tests at alpha = 0.05 each. A cell whose baseline rate is below
10% or above 90% is flagged: the criterion can be met there with almost no
information (a floor or ceiling cannot move 5 points in one direction).

Wording rule: "criterion met" / "criterion not met (unresolved)". Never
"equivalent" from a point estimate.

Run:  .venv/bin/python tools/reanalysis/04_equivalence.py
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

from common import (HEADLINE, MODELS, NEUT, OUT, RESULTS, STER, TASKS,
                    cluster_boot, cluster_stat, load_cell, load_trials)

MARGIN = 5.0
SHORT = {"solve": "solve", "validate_domain": "v_dom", "validate_problem": "v_prob",
         "validate_plan": "v_plan", "simulate": "sim", "pooled": "pooled (5 tasks)"}


def tost(a: np.ndarray, b: np.ndarray, dom: np.ndarray, prob: np.ndarray) -> dict:
    """a, b: paired 0/1 outcomes (reference, comparison). Delta = b - a in points."""
    d = b - a
    out = dict(n=len(d), ra=100 * a.mean(), rb=100 * b.mean(), est=100 * d.mean())
    res = {}
    for nm, cl in (("domain", dom), ("problem", prob)):
        c = cluster_stat(d, cl, alpha=0.10)
        se = 100 * c["se"]
        if se > 0:
            p_lo = float(stats.t.sf((out["est"] + MARGIN) / se, c["k"] - 1))   # H0: delta <= -5
            p_hi = float(stats.t.cdf((out["est"] - MARGIN) / se, c["k"] - 1))  # H0: delta >= +5
            p = max(p_lo, p_hi)
        else:
            p = 0.0 if abs(out["est"]) < MARGIN else 1.0
        res[nm] = dict(lo=100 * c["lo"], hi=100 * c["hi"], k=c["k"], p=p, se=se)
    gov = max(res, key=lambda k: res[k]["hi"] - res[k]["lo"])
    g = res[gov]
    bl, bh = cluster_boot(d, dom, alpha=0.10)
    out.update(lo=g["lo"], hi=g["hi"], gov=gov, k=g["k"], p=g["p"], hw=(g["hi"] - g["lo"]) / 2,
               boot=(100 * bl, 100 * bh), other=res["problem" if gov == "domain" else "domain"])
    out["met"] = (g["lo"] > -MARGIN) and (g["hi"] < MARGIN)
    out["flag"] = ("floor" if out["ra"] < 10 else "ceiling" if out["ra"] > 90 else "")
    # the paper's current evidence: do two separate Wilson 95% intervals overlap?
    return out


def label(r: dict) -> str:
    if r["met"]:
        return "criterion met" + (f" ({r['flag']}: low information)" if r["flag"] else "")
    return "criterion not met (unresolved)"


def row(name: str, r: dict) -> str:
    return (f"| {name} | {r['n']} | {r['ra']:.1f} | {r['rb']:.1f} | {r['est']:+.2f} | "
            f"[{r['lo']:+.2f}, {r['hi']:+.2f}] | {r['gov']} (k={r['k']}) | "
            f"[{r['boot'][0]:+.2f}, {r['boot'][1]:+.2f}] | {r['hw']:.2f} | "
            f"{r['p']:.3f} | {label(r)} |")


HEAD = ("| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | "
        "90% domain bootstrap | half-width | TOST p | verdict at +/-5 |\n|---|---|---|---|---|---|---|---|---|---|---|")


def paired_arrays(ra: dict, rb: dict, sel):
    keys = [k for k in ra if k in rb and sel(k)]
    a = np.array([float(bool(ra[k]["success"])) for k in keys])
    b = np.array([float(bool(rb[k]["success"])) for k in keys])
    dom = np.array([k[2] for k in keys])
    prob = np.array([f"{k[2]}|{k[3]}" for k in keys])
    return a, b, dom, prob


def trials(corpus_dir, name):
    t = load_trials(corpus_dir / name)
    return {k: v for k, v in t.items() if not v.get("infra_failure")}


def main() -> None:
    L = []
    # ------------------------------------------------------------ (a)
    L.append("## (a) Contamination: anonymized minus canonical, no-tools\n")
    summary = []
    for th in ("off", "on"):
        L.append(f"### think={th}\n")
        L.append(HEAD)
        for m in MODELS:
            name = f"slurm_vllm_{m}_{th}_no-tools"
            can = trials(RESULTS / "sweep5v2-live", name)
            anon = trials(RESULTS / "sweep6-live", name)
            for t in TASKS + ["pooled"]:
                sel = (lambda k: True) if t == "pooled" else (lambda k, t=t: k[1] == t)
                r = tost(*paired_arrays(can, anon, sel))
                L.append(row(f"{MODELS[m]} {SHORT[t]}", r))
                summary.append((th, m, t, r))
        L.append("")
    L.append("### Count, think=off\n")
    L.append("| set | cells | criterion met | of which floor/ceiling (low information) | not met (unresolved) |")
    L.append("|---|---|---|---|---|")
    for nm, sel in (("headline 3 models x 5 tasks", lambda m, t: m in HEADLINE and t != "pooled"),
                    ("all 5 models x 5 tasks", lambda m, t: t != "pooled"),
                    ("headline 3 models, pooled", lambda m, t: m in HEADLINE and t == "pooled"),
                    ("all 5 models, pooled", lambda m, t: t == "pooled")):
        rr = [r for th, m, t, r in summary if th == "off" and sel(m, t)]
        L.append(f"| {nm} | {len(rr)} | {sum(r['met'] for r in rr)} | "
                 f"{sum(r['met'] and bool(r['flag']) for r in rr)} | {sum(not r['met'] for r in rr)} |")
    L.append("")

    # ------------------------------------------------------------ (b)
    L.append("## (b) Serving version: vLLM 0.20.2 minus 0.22.0, Qwen3.5-0.8B think=off with-tools\n")
    old = RESULTS / "vllm0220-backup"
    base = "slurm_vllm_Qwen3_5_0_8B_off_tools_all_minimal"
    r1 = trials(old, base + "_sweep5v2.v0220-bak")
    r2 = trials(old, base + "_sweep5v2.v0220-2nd-bak")
    live = trials(RESULTS / "sweep5v2-live", base)
    L.append(f"Rows: 0.22.0 run 1 = {len(r1)}, 0.22.0 run 2 = {len(r2)}, 0.20.2 = {len(live)}; "
             f"shared keys run1/live = {len(set(r1) & set(live))}.\n")
    for title, ra, rb in (("0.20.2 (live) minus 0.22.0 run 1 - the comparison NUMBERS.md quotes", r1, live),
                          ("0.20.2 (live) minus 0.22.0 run 2", r2, live),
                          ("0.22.0 run 2 minus 0.22.0 run 1 - same version twice (run-to-run noise)", r1, r2)):
        L.append(f"### {title}\n")
        L.append(HEAD)
        nmet = ncell = 0
        for t in TASKS:
            for arm, vs in (("plain", NEUT), ("steered", STER)):
                r = tost(*paired_arrays(ra, rb, lambda k, t=t, vs=vs: k[1] == t and k[5] in vs))
                L.append(row(f"{SHORT[t]} / {arm}", r))
                ncell += 1
                nmet += r["met"]
        r = tost(*paired_arrays(ra, rb, lambda k: True))
        L.append(row("pooled (9,120)", r))
        L.append(f"\nTask x arm cells meeting the criterion: {nmet}/{ncell}; pooled: {label(r)}.\n")
        # flip counts: how many individual trials changed outcome
        keys = [k for k in ra if k in rb]
        flips = sum(bool(ra[k]["success"]) != bool(rb[k]["success"]) for k in keys)
        L.append(f"Individual trials whose outcome differs between the two runs: {flips}/{len(keys)} "
                 f"({100 * flips / len(keys):.1f}%).\n")

    text = "\n".join(L)
    OUT.mkdir(exist_ok=True)
    (OUT / "04_equivalence.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
