#!/usr/bin/env python3
"""Shared loading + clustered-inference helpers for the 2026-10 statistics
re-analysis (development/reanalysis_statistics.md, weakness C9).

Read-only over results. Self-contained on purpose: it imports nothing from the
hash-pinned prereg scripts (tools/ntster_*.py) so it can never perturb them, but
it follows their conventions:

  * trial key layout  [model, task, domain, problem, plan_label, variant,
                       with_tools, think, tool_filter, prompt_style]
  * dedup = last row wins
  * the delivered surface (`e2e_strict` in the overlay) is TRI-STATE:
    True / False / "indeterminate". Indeterminate rows (censored at the
    response-snapshot cap, or no ground truth) are bounds, never successes and
    never failures. Compare with `is True`, never by truthiness.

Two surfaces are analysed everywhere:

  mech  "mechanism layer" = the harness `success` field in trials.jsonl.
        With tools this is TOOL-VERIFIED success (the tool was called and its
        result matched ground truth); without tools it is the online grade of
        the model's own answer. Exact on every row.
  dlv   "delivered" = overlay `e2e_strict` (the final answer the user gets).
        Carried as a (low, high) pair per row: determinate rows have low==high,
        indeterminate rows have low=0, high=1.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results"
OVERLAY = RESULTS / "derived" / "e2e_overlay"
OUT = Path(__file__).resolve().parent / "out"

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]
MODELS = {  # dirname tag -> paper name
    "Qwen3_5_0_8B": "Qwen3.5-0.8B",
    "Qwen3_5_4B": "Qwen3.5-4B",
    "Qwen3_5_9B": "Qwen3.5-9B",
    "gemma4_26b-a4b": "Gemma-26B",
    "qwen3_6_35b": "Qwen3.6-35B",
}
HEADLINE = ["Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"]
NEUT = (11, 12, 13)
STER = (14, 15, 16)
Z95 = 1.959963984540054
DEFF = 2.7
SEED = 20261002
B_BOOT = 10_000


# ---------------------------------------------------------------- loading
def read_jsonl(fp: Path) -> list[dict]:
    rows, bad = [], 0
    with fp.open() as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                bad += 1
    if bad:
        print(f"  [warn] {fp}: {bad} unparseable line(s) skipped")
    return rows


def load_trials(cell_dir: Path) -> dict[tuple, dict]:
    """trials.jsonl -> {trial_key: result}, last wins."""
    out: dict[tuple, dict] = {}
    for rec in read_jsonl(cell_dir / "trials.jsonl"):
        out[tuple(rec["key"])] = rec["result"]
    return out


def load_overlay(fp: Path) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for r in read_jsonl(fp):
        out[tuple(r["trial_key"])] = r
    return out


def cell_name(model: str, think: str, tools: bool) -> str:
    return f"slurm_vllm_{model}_{think}_" + ("tools_all_minimal" if tools else "no-tools")


def load_cell(corpus: str, model: str, think: str, tools: bool) -> list[dict]:
    """One (corpus, model, think, condition) cell as flat rows.

    Each row: task, domain, problem, plan, variant, mech (0/1), called (0/1 or
    None), lo/hi (delivered bounds 0/1), censored (bool).
    """
    name = cell_name(model, think, tools)
    trials = load_trials(RESULTS / corpus / name)
    ov = load_overlay(OVERLAY / corpus / f"{name}.e2e.jsonl")
    rows = []
    missing = 0
    for key, res in trials.items():
        if res.get("infra_failure"):
            continue
        o = ov.get(key)
        if o is None:
            missing += 1
            continue
        es = o["e2e_strict"]
        if es is True:
            lo = hi = 1
        elif es is False:
            lo = hi = 0
        else:  # "indeterminate"
            lo, hi = 0, 1
        ts = res.get("tool_selected")
        rows.append(dict(
            task=key[1], domain=key[2], problem=key[3], plan=key[4],
            variant=key[5], mech=int(bool(res["success"])),
            called=None if ts is None else int(bool(ts)),
            lo=lo, hi=hi, censored=(lo != hi),
            reason=res.get("failure_reason")))
    if missing:
        print(f"  [warn] {corpus}/{name}: {missing} trial(s) without an overlay row")
    return rows


# ---------------------------------------------------------------- intervals
def wilson(x: float, n: float, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def cluster_stat(values: np.ndarray, clusters: np.ndarray, alpha: float = 0.05):
    """Mean of `values` with a cluster-robust (cluster-sum, CR1) SE and a
    t interval on k-1 df. Works for unbalanced clusters. Returns dict."""
    n = len(values)
    mean = float(values.mean())
    labels, inv = np.unique(clusters, return_inverse=True)
    k = len(labels)
    sums = np.bincount(inv, weights=values, minlength=k)
    sizes = np.bincount(inv, minlength=k)
    resid = sums - sizes * mean
    if k < 2:
        return dict(est=mean, se=math.nan, lo=math.nan, hi=math.nan, k=k, p=math.nan)
    se = math.sqrt(k / (k - 1) * float((resid ** 2).sum())) / n
    tcrit = float(stats.t.ppf(1 - alpha / 2, k - 1))
    if se > 0:
        p = float(2 * stats.t.sf(abs(mean) / se, k - 1))
    else:
        p = 1.0 if mean == 0 else 0.0
    return dict(est=mean, se=se, lo=mean - tcrit * se, hi=mean + tcrit * se,
                k=k, p=p, resid=resid, sums=sums, sizes=sizes)


def cluster_boot(values: np.ndarray, clusters: np.ndarray, *, b: int = B_BOOT,
                 alpha: float = 0.05, seed: int = SEED) -> tuple[float, float]:
    """Percentile cluster bootstrap of the row-level mean (ratio estimator:
    resample whole clusters, recompute sum/size)."""
    labels, inv = np.unique(clusters, return_inverse=True)
    k = len(labels)
    sums = np.bincount(inv, weights=values, minlength=k)
    sizes = np.bincount(inv, minlength=k).astype(float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, k, size=(b, k))
    boot = sums[draws].sum(axis=1) / sizes[draws].sum(axis=1)
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def signflip_exact_p(cluster_sums: np.ndarray) -> float:
    """Exact two-sided sign-flip (randomisation) test on integer cluster sums of
    paired differences: under H0 each cluster's summed difference is symmetric
    about 0. Enumerates all 2^k sign patterns by dynamic programming."""
    s = np.rint(cluster_sums).astype(int)
    s = np.abs(s[s != 0])
    if len(s) == 0:
        return 1.0
    obs = abs(int(np.rint(cluster_sums).sum()))
    total = int(s.sum())
    dist = np.zeros(2 * total + 1)
    dist[total] = 1.0
    for v in s:
        new = np.zeros_like(dist)
        new[v:] += 0.5 * dist[:-v]
        new[:-v] += 0.5 * dist[v:]
        dist = new
    support = np.arange(-total, total + 1)
    return float(min(1.0, dist[np.abs(support) >= obs].sum()))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar on discordant counts. IGNORES clustering; shown
    as a reference only."""
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5)))


def holm(pvals: dict, alpha: float = 0.05) -> dict:
    """Holm step-down. Returns name -> adjusted p (monotone)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        out[name] = running
    return out


# ---------------------------------------------------------------- pairing
def index_rows(rows: list[dict], variants) -> dict[tuple, dict]:
    return {(r["task"], r["domain"], r["problem"], r["plan"], r["variant"]): r
            for r in rows if r["variant"] in variants}


def build_pairs(rows_a: list[dict], rows_b: list[dict], va, vb) -> list[tuple]:
    """Fixture-matched pairs. Arm A variant va[j] <-> arm B variant vb[j] on the
    same (task, domain, problem, plan). Returns (row_a, row_b) tuples."""
    ia, ib = index_rows(rows_a, va), index_rows(rows_b, vb)
    off = {a: b for a, b in zip(va, vb)}
    pairs = []
    for (t, d, p, pl, v), ra in ia.items():
        rb = ib.get((t, d, p, pl, off[v]))
        if rb is not None:
            pairs.append((ra, rb))
    return pairs


def fmt(x: float, nd: int = 1) -> str:
    return "nan" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.{nd}f}"


def fmtp(p: float) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "nan"
    return f"{p:.3f}" if p >= 0.001 else f"{p:.1e}"
