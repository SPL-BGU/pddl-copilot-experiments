#!/usr/bin/env python3
"""Items 1, 2 and 4 of the statistics re-analysis (weakness C9).

  1. Domain-cluster (k=20) and problem-cluster bootstrap for every headline arm
     rate and arm difference, next to the paper's Wilson and Wilson x sqrt(2.7).
  2. Paired, clustered tests for the two arm contrasts
        availability = no-tools (v11-13)      -> tools-plain (v11-13)
        steering     = tools-plain (v11-13)   -> tools-steered (v14-16)
     instead of "do two separate intervals overlap".
  4. Holm / Bonferroni on top of the clustered paired tests.

Two surfaces (see common.py): `mech` (harness success; tool-verified in the tool
arms) and `dlv` (delivered, bounded where the stored answer is censored).

Run:  .venv/bin/python tools/reanalysis/02_cluster_paired_multiplicity.py
Writes tools/reanalysis/out/02_*.{csv,md}
"""
from __future__ import annotations

import csv
import math

import numpy as np

from common import (DEFF, HEADLINE, MODELS, NEUT, OUT, STER, TASKS, Z95,
                    build_pairs, cluster_boot, cluster_stat, fmtp, holm,
                    load_cell, mcnemar_exact, signflip_exact_p, wilson)

ZINF = Z95 * math.sqrt(DEFF)
SHORT = {"solve": "solve", "validate_domain": "v_dom", "validate_problem": "v_prob",
         "validate_plan": "v_plan", "simulate": "sim"}


def keys(rows):
    dom = np.array([r["domain"] for r in rows])
    prob = np.array([f'{r["domain"]}|{r["problem"]}' for r in rows])
    inst = np.array([f'{r["domain"]}|{r["problem"]}|{r["plan"]}' for r in rows])
    return dom, prob, inst


# ------------------------------------------------------------------ rates
def rate_block(rows, field_lo, field_hi):
    """Interval set for one arm rate. For a bounded cell the reported interval
    is the outer envelope: lower limit computed on the low end, upper limit on
    the high end (the paper's claim-adverse convention)."""
    n = len(rows)
    lo_v = np.array([r[field_lo] for r in rows], float)
    hi_v = np.array([r[field_hi] for r in rows], float)
    dom, prob, inst = keys(rows)
    out = dict(n=n, low=100 * lo_v.mean(), high=100 * hi_v.mean(),
               cens=int((lo_v != hi_v).sum()))
    out["wilson"] = (100 * wilson(lo_v.sum(), n)[0], 100 * wilson(hi_v.sum(), n)[1])
    out["wilson_inf"] = (100 * wilson(lo_v.sum(), n, ZINF)[0], 100 * wilson(hi_v.sum(), n, ZINF)[1])
    for nm, cl in (("inst", inst), ("prob", prob), ("dom", dom)):
        out[f"boot_{nm}"] = (100 * cluster_boot(lo_v, cl)[0], 100 * cluster_boot(hi_v, cl)[1])
    a, b = cluster_stat(lo_v, dom), cluster_stat(hi_v, dom)
    out["t_dom"] = (100 * a["lo"], 100 * b["hi"])
    # design effect of domain clustering, on the determinate (low) series
    p = lo_v.mean()
    binom = p * (1 - p) / n
    out["deff_dom"] = (a["se"] ** 2 / binom) if binom > 0 else math.nan
    ai = cluster_stat(lo_v, inst)
    out["deff_inst"] = (ai["se"] ** 2 / binom) if binom > 0 else math.nan
    return out


# ------------------------------------------------------------------ contrasts
def paper_rule_mech(xa, na, xb, nb, z):
    la, ua = wilson(xa, na, z)
    lb, ub = wilson(xb, nb, z)
    if lb > ua:
        return "FAV"
    if ub < la:
        return "AGAINST"
    return "NS"


def paper_rule_dlv(a_ok, a_c, na, b_ok, b_c, nb, z):
    """job2 worknote sect. 1: claim-adverse end of each bound, Wilson on it."""
    if wilson(b_ok, nb, z)[0] > wilson(a_ok + a_c, na, z)[1]:
        return "FAV"
    if wilson(b_ok + b_c, nb, z)[1] < wilson(a_ok, na, z)[0]:
        return "AGAINST"
    return "UNDECIDED" if (a_c or b_c) else "NS"


def clustered(d, dom, prob):
    """Paired difference series d -> governing (wider) clustered 95% interval,
    bootstrap intervals, and tests."""
    td, tp = cluster_stat(d, dom), cluster_stat(d, prob)
    gov = td if (td["hi"] - td["lo"]) >= (tp["hi"] - tp["lo"]) else tp
    gov_name = "domain" if gov is td else "problem"
    bd, bp = cluster_boot(d, dom), cluster_boot(d, prob)
    return dict(est=100 * td["est"],
                t_dom=(100 * td["lo"], 100 * td["hi"]), t_prob=(100 * tp["lo"], 100 * tp["hi"]),
                boot_dom=(100 * bd[0], 100 * bd[1]), boot_prob=(100 * bp[0], 100 * bp[1]),
                gov=(100 * gov["lo"], 100 * gov["hi"]), gov_name=gov_name,
                k_dom=td["k"], k_prob=tp["k"],
                p_gov=max(td["p"], tp["p"]), p_dom=td["p"], p_prob=tp["p"],
                p_flip=signflip_exact_p(td["sums"] - 0.0) if True else None)


def verdict_from(lo, hi):
    return "FAV" if lo > 0 else "AGAINST" if hi < 0 else "NS"


def contrast(pairs, surface):
    a_rows = [p[0] for p in pairs]
    b_rows = [p[1] for p in pairs]
    dom, prob, _ = keys(a_rows)
    n = len(pairs)
    res = dict(n=n, surface=surface)
    if surface == "mech":
        a = np.array([r["mech"] for r in a_rows], float)
        b = np.array([r["mech"] for r in b_rows], float)
        d = b - a
        res.update(a_lo=100 * a.mean(), a_hi=100 * a.mean(), b_lo=100 * b.mean(), b_hi=100 * b.mean(),
                   cens_a=0, cens_b=0)
        res["paper"] = paper_rule_mech(a.sum(), n, b.sum(), n, Z95)
        res["paper_inf"] = paper_rule_mech(a.sum(), n, b.sum(), n, ZINF)
        c = clustered(d, dom, prob)
        res.update(d_lo=c["est"], d_hi=c["est"], c_lo=c, c_hi=c)
        res["new"] = verdict_from(*c["gov"])
        res["p"] = c["p_gov"]
        res["p_flip"] = c["p_flip"]
        res["mcnemar"] = mcnemar_exact(int((d == 1).sum()), int((d == -1).sum()))
        res["disc"] = (int((d == 1).sum()), int((d == -1).sum()))
        res["ci"] = c["gov"]
        res["ci_boot_dom"] = c["boot_dom"]
        res["ci_boot_prob"] = c["boot_prob"]
        res["ci_t_dom"] = c["t_dom"]
        res["ci_t_prob"] = c["t_prob"]
        res["gov_name"] = c["gov_name"]
        return res
    # delivered: bounds. worst case for "b helps" = censored b fails, censored a succeeds
    a_lo = np.array([r["lo"] for r in a_rows], float)
    a_hi = np.array([r["hi"] for r in a_rows], float)
    b_lo = np.array([r["lo"] for r in b_rows], float)
    b_hi = np.array([r["hi"] for r in b_rows], float)
    d_worst, d_best = b_lo - a_hi, b_hi - a_lo
    ca, cb = int((a_lo != a_hi).sum()), int((b_lo != b_hi).sum())
    res.update(a_lo=100 * a_lo.mean(), a_hi=100 * a_hi.mean(), b_lo=100 * b_lo.mean(),
               b_hi=100 * b_hi.mean(), cens_a=ca, cens_b=cb)
    res["paper"] = paper_rule_dlv(a_lo.sum(), ca, n, b_lo.sum(), cb, n, Z95)
    res["paper_inf"] = paper_rule_dlv(a_lo.sum(), ca, n, b_lo.sum(), cb, n, ZINF)
    cw, cbst = clustered(d_worst, dom, prob), clustered(d_best, dom, prob)
    res.update(d_lo=cw["est"], d_hi=cbst["est"], c_lo=cw, c_hi=cbst)
    # envelope interval: lower limit from the worst-case series, upper from the best-case
    res["ci"] = (cw["gov"][0], cbst["gov"][1])
    res["ci_boot_dom"] = (cw["boot_dom"][0], cbst["boot_dom"][1])
    res["ci_boot_prob"] = (cw["boot_prob"][0], cbst["boot_prob"][1])
    res["ci_t_dom"] = (cw["t_dom"][0], cbst["t_dom"][1])
    res["ci_t_prob"] = (cw["t_prob"][0], cbst["t_prob"][1])
    res["gov_name"] = cw["gov_name"] if cw["est"] > 0 else cbst["gov_name"]
    v = verdict_from(*res["ci"])
    res["new"] = v if v != "NS" else ("UNDECIDED" if (ca or cb) else "NS")
    if cw["est"] > 0:        # even the worst case points up: test it
        res["p"], res["p_flip"] = cw["p_gov"], cw["p_flip"]
    elif cbst["est"] < 0:    # even the best case points down
        res["p"], res["p_flip"] = cbst["p_gov"], cbst["p_flip"]
    else:                    # the bounds straddle zero: no test can be run
        res["p"], res["p_flip"] = 1.0, 1.0
    res["mcnemar"] = math.nan
    res["disc"] = (0, 0)
    return res


def iv(t, nd=1):
    return f"[{t[0]:.{nd}f}, {t[1]:.{nd}f}]"


def rng_or_pt(lo, hi):
    return f"{lo:.1f}" if abs(lo - hi) < 1e-9 else f"<{lo:.1f}, {hi:.1f}>"


def main():
    OUT.mkdir(exist_ok=True)
    rate_rows, con_rows = [], []
    for m in MODELS:
        for th in ("off", "on"):
            nt = load_cell("sweep5v2-live", m, th, False)
            tl = load_cell("sweep5v2-live", m, th, True)
            for t in TASKS:
                arms = {"nt-neut": [r for r in nt if r["task"] == t and r["variant"] in NEUT],
                        "tl-neut": [r for r in tl if r["task"] == t and r["variant"] in NEUT],
                        "tl-ster": [r for r in tl if r["task"] == t and r["variant"] in STER]}
                for arm, rows in arms.items():
                    for surface, flo, fhi in (("mech", "mech", "mech"), ("dlv", "lo", "hi")):
                        rb = rate_block(rows, flo, fhi)
                        rate_rows.append(dict(model=m, think=th, task=t, arm=arm, surface=surface, **rb))
                nt_t = [r for r in nt if r["task"] == t]
                tl_t = [r for r in tl if r["task"] == t]
                for cname, pairs in (("availability", build_pairs(nt_t, tl_t, NEUT, NEUT)),
                                     ("steering", build_pairs(tl_t, tl_t, NEUT, STER))):
                    for surface in ("mech", "dlv"):
                        c = contrast(pairs, surface)
                        con_rows.append(dict(model=m, think=th, task=t, contrast=cname, **c))

    # ---------------- multiplicity (item 4)
    def fam(rows, sel):
        return {(r["model"], r["think"], r["task"], r["contrast"], r["surface"]): r["p"]
                for r in rows if sel(r)}

    families = {
        "H30_dlv": lambda r: r["think"] == "off" and r["model"] in HEADLINE and r["surface"] == "dlv",
        "H30_mech": lambda r: r["think"] == "off" and r["model"] in HEADLINE and r["surface"] == "mech",
        "H60_both": lambda r: r["think"] == "off" and r["model"] in HEADLINE,
        "R100_off_both": lambda r: r["think"] == "off",
        "R200_all": lambda r: True,
    }
    holm_adj = {name: holm(fam(con_rows, sel)) for name, sel in families.items()}
    for r in con_rows:
        k = (r["model"], r["think"], r["task"], r["contrast"], r["surface"])
        for name in families:
            r[f"holm_{name}"] = holm_adj[name].get(k, math.nan)

    def after(r, name):
        """Verdict after Holm at 0.05 in family `name` (direction from the clustered verdict)."""
        if r["new"] not in ("FAV", "AGAINST"):
            return r["new"]
        return r["new"] if r[f"holm_{name}"] <= 0.05 else "ns-after-Holm"

    # ---------------- CSVs
    with (OUT / "02_rates.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "think", "task", "arm", "surface", "n", "censored", "low_pct", "high_pct",
                    "wilson_lo", "wilson_hi", "wilson_x_sqrt2.7_lo", "wilson_x_sqrt2.7_hi",
                    "boot_instance_lo", "boot_instance_hi", "boot_problem_lo", "boot_problem_hi",
                    "boot_domain_lo", "boot_domain_hi", "t_domain_lo", "t_domain_hi",
                    "deff_instance", "deff_domain"])
        for r in rate_rows:
            w.writerow([r["model"], r["think"], r["task"], r["arm"], r["surface"], r["n"], r["cens"],
                        *(round(x, 3) for x in (r["low"], r["high"], *r["wilson"], *r["wilson_inf"],
                                                *r["boot_inst"], *r["boot_prob"], *r["boot_dom"],
                                                *r["t_dom"], r["deff_inst"], r["deff_dom"]))])
    with (OUT / "02_contrasts.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "think", "task", "contrast", "surface", "n_pairs", "cens_a", "cens_b",
                    "a_low", "a_high", "b_low", "b_high", "delta_low", "delta_high",
                    "ci_gov_lo", "ci_gov_hi", "governing", "ci_t_domain_lo", "ci_t_domain_hi",
                    "ci_t_problem_lo", "ci_t_problem_hi", "ci_boot_domain_lo", "ci_boot_domain_hi",
                    "ci_boot_problem_lo", "ci_boot_problem_hi", "p_cluster_t_gov", "p_signflip_domain",
                    "p_mcnemar_unclustered", "discordant_up", "discordant_down",
                    "verdict_paper_wilson", "verdict_paper_wilson_x_sqrt2.7", "verdict_clustered_paired",
                    *[f"holm_p_{n}" for n in families]])
        for r in con_rows:
            w.writerow([r["model"], r["think"], r["task"], r["contrast"], r["surface"], r["n"],
                        r["cens_a"], r["cens_b"],
                        *(round(x, 3) for x in (r["a_lo"], r["a_hi"], r["b_lo"], r["b_hi"], r["d_lo"],
                                                r["d_hi"], *r["ci"])), r["gov_name"],
                        *(round(x, 3) for x in (*r["ci_t_dom"], *r["ci_t_prob"], *r["ci_boot_dom"],
                                                *r["ci_boot_prob"])),
                        r["p"], r["p_flip"], r["mcnemar"], *r["disc"],
                        r["paper"], r["paper_inf"], r["new"], *[r[f"holm_{n}"] for n in families]])

    # ---------------- markdown
    L = []
    hl = lambda r: r["think"] == "off" and r["model"] in HEADLINE  # noqa: E731

    L.append("## Table A. Headline arm rates: paper intervals vs cluster bootstrap (think=off)\n")
    L.append("Percent. `<a, b>` is a censoring bound. For a bounded cell every interval is the outer "
             "envelope (lower limit on the low end, upper limit on the high end). `deff` = variance "
             "inflation relative to independent trials, on the determinate series.\n")
    for surface, title in (("mech", "mechanism layer (harness success; tool-verified in the tool arms)"),
                           ("dlv", "delivered surface")):
        L.append(f"### {title}\n")
        L.append("| model | task | arm | rate | Wilson | Wilson x sqrt(2.7) | boot: instance | "
                 "boot: problem | boot: domain (k=20) | widest | deff inst | deff domain |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in rate_rows:
            if not hl(r) or r["surface"] != surface:
                continue
            widths = {"Wilson x sqrt(2.7)": r["wilson_inf"][1] - r["wilson_inf"][0],
                      "problem": r["boot_prob"][1] - r["boot_prob"][0],
                      "domain": r["boot_dom"][1] - r["boot_dom"][0]}
            widest = max(widths, key=widths.get)
            L.append(f"| {MODELS[r['model']]} | {SHORT[r['task']]} | {r['arm']} | "
                     f"{rng_or_pt(r['low'], r['high'])} | {iv(r['wilson'])} | {iv(r['wilson_inf'])} | "
                     f"{iv(r['boot_inst'])} | {iv(r['boot_prob'])} | {iv(r['boot_dom'])} | {widest} | "
                     f"{r['deff_inst']:.1f} | {r['deff_dom']:.1f} |")
        L.append("")

    for surface, title in (("mech", "mechanism layer"), ("dlv", "delivered surface")):
        L.append(f"## Table B ({surface}). Paired arm contrasts, {title}, think=off, headline models\n")
        L.append("Delta = second arm minus first arm, in points, over fixture-matched pairs. "
                 "`governing CI` = the wider of the domain-clustered (k=20) and problem-clustered "
                 "95% t intervals. p = cluster-t p of the governing clustering; `flip` = exact "
                 "sign-flip test on the 20 domain sums. Holm column = verdict after Holm at 0.05 over "
                 "the 30 headline contrasts on this surface.\n")
        L.append("| model | task | contrast | arm A | arm B | Delta | governing CI | by | boot domain | "
                 "boot problem | p | flip p | paper (Wilson) | paper (x sqrt 2.7) | clustered paired | after Holm (30) |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in con_rows:
            if not hl(r) or r["surface"] != surface:
                continue
            dl = (f"{r['d_lo']:+.1f}" if abs(r["d_lo"] - r["d_hi"]) < 1e-9
                  else f"<{r['d_lo']:+.1f}, {r['d_hi']:+.1f}>")
            L.append(f"| {MODELS[r['model']]} | {SHORT[r['task']]} | {r['contrast'][:5]} | "
                     f"{rng_or_pt(r['a_lo'], r['a_hi'])} | {rng_or_pt(r['b_lo'], r['b_hi'])} | {dl} | "
                     f"{iv(r['ci'])} | {r['gov_name'][:4]} | {iv(r['ci_boot_dom'])} | {iv(r['ci_boot_prob'])} | "
                     f"{fmtp(r['p'])} | {fmtp(r['p_flip'])} | {r['paper']} | {r['paper_inf']} | "
                     f"{r['new']} | {after(r, 'H30_' + surface)} |")
        L.append("")

    L.append("## Table C. Verdict changes\n")
    L.append("Rows where the paper's rule (Wilson disjointness, widened by sqrt(2.7)) and the clustered "
             "paired test disagree, or where Holm removes a clustered verdict. All models, both modes.\n")
    L.append("| model | think | task | contrast | surface | Delta | governing CI | paper (x sqrt 2.7) | "
             "clustered paired | Holm 30 | Holm 60 | Holm 100 | Holm 200 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in con_rows:
        f30 = "H30_" + r["surface"]
        in30 = hl(r)
        changed = (r["paper_inf"] != r["new"]) or (r["new"] in ("FAV", "AGAINST") and
                                                    r["holm_R200_all"] > 0.05)
        if not changed:
            continue
        dl = (f"{r['d_lo']:+.1f}" if abs(r["d_lo"] - r["d_hi"]) < 1e-9
              else f"<{r['d_lo']:+.1f}, {r['d_hi']:+.1f}>")
        L.append(f"| {MODELS[r['model']]} | {r['think']} | {SHORT[r['task']]} | {r['contrast'][:5]} | "
                 f"{r['surface']} | {dl} | {iv(r['ci'])} | {r['paper_inf']} | {r['new']} | "
                 f"{after(r, f30) if in30 else '-'} | {after(r, 'H60_both') if in30 else '-'} | "
                 f"{after(r, 'R100_off_both') if r['think'] == 'off' else '-'} | {after(r, 'R200_all')} |")
    L.append("")

    L.append("## Table D. Family sizes and survival counts\n")
    L.append("| family | m | Bonferroni per-test alpha | two-sided z | clustered verdicts before | "
             "survive Holm | survive Bonferroni |")
    L.append("|---|---|---|---|---|---|---|")
    from scipy import stats as _st
    for name, sel in families.items():
        rows = [r for r in con_rows if sel(r)]
        m_ = len(rows)
        sig = [r for r in rows if r["new"] in ("FAV", "AGAINST")]
        sh = sum(r[f"holm_{name}"] <= 0.05 for r in sig)
        sb = sum(r["p"] <= 0.05 / m_ for r in sig)
        L.append(f"| {name} | {m_} | {0.05 / m_:.2e} | {_st.norm.isf(0.025 / m_):.2f} | "
                 f"{len(sig)} | {sh} | {sb} |")
    L.append("")

    L.append("## Table E. How large is the clustering really? (think=off, headline, mechanism layer)\n")
    L.append("Median and max design effect per clustering level over the 45 headline arm cells "
             "with a non-degenerate rate.\n")
    de_i = [r["deff_inst"] for r in rate_rows if hl(r) and r["surface"] == "mech" and not math.isnan(r["deff_inst"])]
    de_d = [r["deff_dom"] for r in rate_rows if hl(r) and r["surface"] == "mech" and not math.isnan(r["deff_dom"])]
    L.append("| clustering | cells | median deff | max deff | cells with deff > 2.7 |")
    L.append("|---|---|---|---|---|")
    for nm, de in (("instance (3 wordings)", de_i), ("domain (k=20)", de_d)):
        L.append(f"| {nm} | {len(de)} | {np.median(de):.2f} | {max(de):.1f} | {sum(x > 2.7 for x in de)} |")
    L.append("")

    text = "\n".join(L)
    (OUT / "02_tables.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
