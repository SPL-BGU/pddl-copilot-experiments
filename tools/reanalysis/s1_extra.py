"""Study 1 extras: (1) P(correct | call) with a domain-cluster bootstrap 95%; (2) validate_domain
balanced accuracy (mean of per-class accuracy; positives p01-p05, negative domain_neg) with a
domain-cluster bootstrap 95% (per-class ratio estimator, same seed and resamples); (3) the
failure-reason mix of the unaided cells (at-cap handling). Headline models, think=off,
results/sweep5v2-live."""
import collections
import numpy as np
from common import HEADLINE, MODELS, NEUT, STER, TASKS, SEED, B_BOOT, cluster_boot, load_cell, wilson

def bal_boot(rows):
    doms = sorted({r["domain"] for r in rows})
    idx = {d: i for i, d in enumerate(doms)}
    k = len(doms)
    sp, np_, sn, nn = (np.zeros(k) for _ in range(4))
    for r in rows:
        i = idx[r["domain"]]
        if r["problem"] == "domain_neg":
            sn[i] += r["mech"]; nn[i] += 1
        else:
            sp[i] += r["mech"]; np_[i] += 1
    est = 50 * (sp.sum() / np_.sum() + sn.sum() / nn.sum())
    rng = np.random.default_rng(SEED)
    d = rng.integers(0, k, size=(B_BOOT, k))
    b = 50 * (sp[d].sum(1) / np_[d].sum(1) + sn[d].sum(1) / nn[d].sum(1))
    lo, hi = np.quantile(b, [0.025, 0.975])
    return est, lo, hi, 100 * sp.sum() / np_.sum(), 100 * sn.sum() / nn.sum(), int(np_.sum()), int(nn.sum()), k

for m in HEADLINE:
    nt = load_cell("sweep5v2-live", m, "off", False)
    tl = load_cell("sweep5v2-live", m, "off", True)
    for t in TASKS:
        for arm, rows0, vs in (("nt-neut", nt, NEUT), ("tl-neut", tl, NEUT), ("tl-ster", tl, STER)):
            rr = [r for r in rows0 if r["task"] == t and r["variant"] in vs]
            if arm != "nt-neut":
                cr = [r for r in rr if r["called"]]
                v = np.array([r["mech"] for r in cr], float)
                dom = np.array([r["domain"] for r in cr])
                lo, hi = cluster_boot(v, dom)
                print(f"PCALL {m} {t} {arm} n_call={len(cr)} ok={int(v.sum())} {100*v.mean():.1f} D[{100*lo:.1f},{100*hi:.1f}] k={len(set(dom))}")
            else:
                mix = collections.Counter(r["reason"] for r in rr)
                print(f"MIX {m} {t} n={len(rr)} {dict(mix)}")
            if t == "validate_domain":
                est, lo, hi, tpr, tnr, npos, nneg, k = bal_boot(rr)
                print(f"BAL {m} {arm} {est:.1f} D[{lo:.1f},{hi:.1f}] valid-class {tpr:.1f} (n={npos}) invalid-class {tnr:.1f} (n={nneg}) k={k}")
