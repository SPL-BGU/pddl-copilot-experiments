"""Interval and multiplicity helpers.

Method reused from tools/reanalysis/common.py (2026-10-02, branch
docs/reanalysis-and-rerun-prereg): percentile cluster bootstrap with the
ratio estimator (resample whole domains with replacement, recompute
sum / size), and Holm step-down. Reimplemented here rather than imported:
that module is not on the harness branch this package is built on, and it
reads overlay files this analysis must not depend on.

All inputs are 0/1 (or -1/0/1 paired differences) per row; all outputs are
in percentage points.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pddl_eval.summary import wilson_ci

from . import constants as C


@dataclass(frozen=True)
class Boot:
    est: float          # point estimate, points
    lo: float           # percentile interval, points
    hi: float
    level: float
    k: int              # number of clusters
    n: int              # number of rows


def cluster_bootstrap(values: list[float], clusters: list[str], level: float,
                      k_expected: int, what: str = "") -> Boot:
    """Domain-cluster percentile bootstrap of a row-level mean (§3, §4).

    `B_BOOT` resamples, a fresh generator seeded with `SEED` per call (the
    convention of tools/reanalysis/common.py cluster_boot), clusters ordered
    by name so the draw is reproducible. Asserts the registered cluster
    count.
    """
    if len(values) != len(clusters) or not values:
        raise C.RegisteredCheckFailed(f"{what}: bootstrap needs a non-empty, aligned sample")
    v = np.asarray(values, dtype=float)
    labels, inv = np.unique(np.asarray(clusters), return_inverse=True)
    k = len(labels)
    if k != k_expected:
        raise C.RegisteredCheckFailed(
            f"{what}: domain-cluster bootstrap over {k} domains, registered {k_expected}: "
            f"a domain is missing from this comparison (present: {list(labels)})")
    sums = np.bincount(inv, weights=v, minlength=k)
    sizes = np.bincount(inv, minlength=k).astype(float)
    rng = np.random.default_rng(C.SEED)
    draws = rng.integers(0, k, size=(C.B_BOOT, k))
    boot = sums[draws].sum(axis=1) / sizes[draws].sum(axis=1)
    alpha = 1.0 - level
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
    return Boot(est=100 * float(v.mean()), lo=100 * float(lo), hi=100 * float(hi),
                level=level, k=k, n=len(v))


def domain_sums(values: list[int], clusters: list[str]) -> list[int]:
    """Integer per-domain sums of paired differences, domains in name order."""
    out: dict[str, int] = {}
    for v, c in zip(values, clusters):
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"paired difference must be an int, got {v!r}")
        out[c] = out.get(c, 0) + v
    return [out[c] for c in sorted(out)]


def signflip_exact_p(sums: list[int]) -> float:
    """Exact two-sided sign-flip (randomisation) test on the domain sums of
    paired differences: under H0 each domain's summed difference is
    symmetric about 0. Enumerates all 2^k sign patterns by dynamic
    programming. Same test as tools/reanalysis/common.py signflip_exact_p.
    The p-values that enter Holm (§4 E2/E3)."""
    s = [abs(int(x)) for x in sums if x != 0]
    if not s:
        return 1.0
    obs = abs(int(sum(sums)))
    total = sum(s)
    dist = np.zeros(2 * total + 1)
    dist[total] = 1.0
    for v in s:
        new = np.zeros_like(dist)
        new[v:] += 0.5 * dist[:-v]
        new[:-v] += 0.5 * dist[v:]
        dist = new
    support = np.arange(-total, total + 1)
    return float(min(1.0, dist[np.abs(support) >= obs].sum()))


def tost_met(b: Boot) -> bool:
    """§3 'the 90% confidence interval of Δ ... lies inside [−5, +5]'.

    Inclusive bounds, as tools/iss024d_parity.py (the earlier parity prereg)
    implemented TOST.
    """
    if b.level != C.CI_PARITY:
        raise C.RegisteredCheckFailed(f"TOST needs the {C.CI_PARITY} interval, got {b.level}")
    return b.lo >= -C.MARGIN and b.hi <= C.MARGIN


def newcombe(k1: int, n1: int, k2: int, n2: int, z: float = C.Z90) -> tuple[float, float, float]:
    """Newcombe hybrid Wilson-score interval for p1 − p2, in points.

    Same formula as tools/iss024d_parity.py `newcombe` (§3 secondary,
    'the unpaired Newcombe 90% interval used by the iss024d parity prereg').
    """
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_ci(k1, n1, z=z)
    l2, u2 = wilson_ci(k2, n2, z=z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return 100 * d, 100 * lo, 100 * hi


def holm(pvals: dict, family_size: int) -> dict:
    """Holm step-down adjusted p (monotone), over exactly `family_size` tests."""
    if len(pvals) != family_size:
        raise C.RegisteredCheckFailed(f"Holm family has {len(pvals)} tests, registered "
                                      f"{family_size}")
    items = sorted(pvals.items(), key=lambda kv: (kv[1], str(kv[0])))
    m = len(items)
    out, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = running
    return out
