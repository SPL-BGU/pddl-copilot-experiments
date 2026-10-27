"""Study 1 calling (invocation) rates: `tool_selected` per model x think x task x arm,
canonical corpus results/sweep5v2-live (and sweep6-live for the twin), with Wilson 95%
and the domain-cluster bootstrap 95% (k=20, 10,000 resamples, seed 20261002) used by
tools/reanalysis/02_cluster_paired_multiplicity.py. Also P(correct | call) and the count
of successes without a call (must be 0 on the mechanism layer)."""
import csv, sys
import numpy as np
from common import MODELS, NEUT, STER, TASKS, cluster_boot, load_cell, wilson, OUT
corpus = sys.argv[1] if len(sys.argv) > 1 else "sweep5v2-live"
rows_out = []
for m in MODELS:
    for th in ("off", "on"):
        tl = load_cell(corpus, m, th, True)
        for t in TASKS:
            for arm, vs in (("tl-neut", NEUT), ("tl-ster", STER)):
                rr = [r for r in tl if r["task"] == t and r["variant"] in vs]
                n = len(rr)
                c = np.array([r["called"] for r in rr], float)
                dom = np.array([r["domain"] for r in rr])
                k = int(c.sum())
                wl, wh = wilson(k, n)
                bl, bh = cluster_boot(c, dom)
                okc = sum(r["mech"] for r in rr if r["called"])
                ok_nocall = sum(r["mech"] for r in rr if not r["called"])
                rows_out.append(dict(corpus=corpus, model=m, think=th, task=t, arm=arm, n=n, called=k,
                    rate=100 * k / n, wilson_lo=100 * wl, wilson_hi=100 * wh, boot_dom_lo=100 * bl,
                    boot_dom_hi=100 * bh, tv_ok=sum(r["mech"] for r in rr), ok_given_call=okc,
                    p_ok_given_call=(100 * okc / k) if k else float("nan"), ok_without_call=ok_nocall,
                    ndom=len(set(dom))))
fp = OUT / f"s1_calling_{corpus}.csv"
with fp.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0]), lineterminator="\n")
    w.writeheader()
    for r in rows_out:
        w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
for r in rows_out:
    print(f'{r["model"]:15s} {r["think"]} {r["task"]:17s} {r["arm"]} n={r["n"]:4d} call={r["called"]:4d} '
          f'{r["rate"]:5.1f} W[{r["wilson_lo"]:.1f},{r["wilson_hi"]:.1f}] D[{r["boot_dom_lo"]:.1f},{r["boot_dom_hi"]:.1f}] '
          f'tv={r["tv_ok"]} P(c|call)={r["p_ok_given_call"]:.1f} okNoCall={r["ok_without_call"]} k={r["ndom"]}')
