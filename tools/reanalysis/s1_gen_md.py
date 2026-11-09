"""Generate the markdown tables of the NUMBERS.md Study 1 block from the re-run outputs."""
import csv, json, importlib.util, sys
from pathlib import Path
import numpy as np
from common import (HEADLINE, MODELS, NEUT, STER, TASKS, SEED, B_BOOT, RESULTS, OUT,
                    cluster_boot, load_cell, wilson)
spec = importlib.util.spec_from_file_location("eq", Path(__file__).parent / "04_equivalence.py")
eq = importlib.util.module_from_spec(spec); spec.loader.exec_module(eq)
S = Path(sys.argv[1])
SH = {"solve": "solve", "validate_domain": "validate_domain", "validate_problem": "validate_problem",
      "validate_plan": "validate_plan", "simulate": "simulate"}
NM = {"Qwen3_5_9B": "Qwen3.5-9B", "gemma4_26b-a4b": "Gemma-26B", "qwen3_6_35b": "Qwen3.6-35B",
      "Qwen3_5_0_8B": "Qwen3.5-0.8B", "Qwen3_5_4B": "Qwen3.5-4B"}

def cell(rate, blo, bhi, k, n):
    """rate with the domain bootstrap 95%; Wilson (marked †) when the rate is exactly 0 or 100."""
    if k == 0 or k == n:
        wl, wh = wilson(k, n)
        return f"{rate:.1f} [{100*wl:.1f}, {100*wh:.1f}]†"
    return f"{rate:.1f} [{blo:.1f}, {bhi:.1f}]"

spec2 = importlib.util.spec_from_file_location("m02", Path(__file__).parent / "02_cluster_paired_multiplicity.py")
m02 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(m02)
from common import build_pairs, holm
rates = {}
CONS = []
for m in HEADLINE:
    nt = load_cell("sweep5v2-live", m, "off", False); tl = load_cell("sweep5v2-live", m, "off", True)
    for t in TASKS:
        for arm, rows0, vs in (("nt-neut", nt, NEUT), ("tl-neut", tl, NEUT), ("tl-ster", tl, STER)):
            rr = [r for r in rows0 if r["task"] == t and r["variant"] in vs]
            b = m02.rate_block(rr, "mech", "mech")
            rates[(m, "off", t, arm)] = dict(n=b["n"], low_pct=b["low"], boot_domain_lo=b["boot_dom"][0], boot_domain_hi=b["boot_dom"][1])
        nt_t = [r for r in nt if r["task"] == t]; tl_t = [r for r in tl if r["task"] == t]
        for cname, pairs in (("availability", build_pairs(nt_t, tl_t, NEUT, NEUT)), ("steering", build_pairs(tl_t, tl_t, NEUT, STER))):
            c = m02.contrast(pairs, "mech"); c.update(model=m, task=t, contrast=cname); CONS.append(c)
call = {}
for r in csv.DictReader(open(OUT / "s1_calling_sweep5v2-live.csv")):
    call[(r["model"], r["think"], r["task"], r["arm"])] = r

def rcell(m, th, t, arm):
    r = rates[(m, th, t, arm)]
    n = int(r["n"]); k = round(float(r["low_pct"]) * n / 100)
    return cell(float(r["low_pct"]), float(r["boot_domain_lo"]), float(r["boot_domain_hi"]), k, n), k, n

L = []
L.append("#### T1. Unaided and tool-verified success (think=off)\n")
L.append("| model | task | n per arm | unaided | tool-verified, plain | tool-verified, steered |")
L.append("|---|---|---|---|---|---|")
for m in HEADLINE:
    for t in TASKS:
        a, ka, n = rcell(m, "off", t, "nt-neut"); b, kb, _ = rcell(m, "off", t, "tl-neut"); c, kc, _ = rcell(m, "off", t, "tl-ster")
        L.append(f"| {NM[m]} | {t} | {n:,} | {a} ({ka}) | {b} ({kb}) | {c} ({kc}) |")
L.append("")

# calling + P(correct | call)
def pcall(m, th, t, arm):
    tl = CACHE[(m, th)]
    vs = NEUT if arm == "tl-neut" else STER
    cr = [r for r in tl if r["task"] == t and r["variant"] in vs and r["called"]]
    v = np.array([r["mech"] for r in cr], float); dom = np.array([r["domain"] for r in cr])
    lo, hi = cluster_boot(v, dom)
    k = int(v.sum()); n = len(cr)
    s = cell(100 * v.mean(), 100 * lo, 100 * hi, k, n)
    return s + ("‡" if len(set(dom)) < 20 else ""), k, n
CACHE = {(m, th): load_cell("sweep5v2-live", m, th, True) for m in HEADLINE for th in ("off",)}
def ccell(m, th, t, arm):
    r = call[(m, th, t, arm)]
    n, k = int(r["n"]), int(r["called"])
    return cell(float(r["rate"]), float(r["boot_dom_lo"]), float(r["boot_dom_hi"]), k, n), k, n
L.append("#### T2. Calling, and correct given a call (think=off)\n")
L.append("| model | task | calling, plain | calling, steered | correct given a call, plain | correct given a call, steered |")
L.append("|---|---|---|---|---|---|")
for m in HEADLINE:
    for t in TASKS:
        a, ka, n = ccell(m, "off", t, "tl-neut"); b, kb, _ = ccell(m, "off", t, "tl-ster")
        c, kc, nc = pcall(m, "off", t, "tl-neut"); d, kd, nd = pcall(m, "off", t, "tl-ster")
        L.append(f"| {NM[m]} | {t} | {a} ({ka}/{n}) | {b} ({kb}/{n}) | {c} ({kc}/{nc}) | {d} ({kd}/{nd}) |")
L.append("")
L.append("#### T3. Calling with thinking on (think=on; plain / steered)\n")
L.append("| model | arm | solve | validate_domain | validate_problem | validate_plan | simulate |")
L.append("|---|---|---|---|---|---|---|")
for m in HEADLINE:
    for arm, an in (("tl-neut", "plain"), ("tl-ster", "steered")):
        L.append(f"| {NM[m]} | {an} | " + " | ".join(ccell(m, "on", t, arm)[0] for t in TASKS) + " |")
L.append("")
L.append("For comparison, think=off plain validate_plan: 9B 97.9, Gemma 20.7, 35B 82.9 (T2).\n")

# balanced accuracy
def bal(rows):
    doms = sorted({r["domain"] for r in rows}); idx = {d: i for i, d in enumerate(doms)}; k = len(doms)
    sp, npp, sn, nn = (np.zeros(k) for _ in range(4))
    for r in rows:
        i = idx[r["domain"]]
        if r["problem"] == "domain_neg": sn[i] += r["mech"]; nn[i] += 1
        else: sp[i] += r["mech"]; npp[i] += 1
    est = 50 * (sp.sum() / npp.sum() + sn.sum() / nn.sum())
    rng = np.random.default_rng(SEED); d = rng.integers(0, k, size=(B_BOOT, k))
    b = 50 * (sp[d].sum(1) / npp[d].sum(1) + sn[d].sum(1) / nn[d].sum(1))
    lo, hi = np.quantile(b, [0.025, 0.975])
    return est, lo, hi, 100 * sp.sum() / npp.sum(), 100 * sn.sum() / nn.sum()
L.append("#### T4. validate_domain balanced accuracy (think=off)\n")
L.append("| model | unaided | tool-verified, plain | tool-verified, steered |")
L.append("|---|---|---|---|")
for m in HEADLINE:
    nt = load_cell("sweep5v2-live", m, "off", False); tl = CACHE[(m, "off")]
    out = []
    for rows0, vs in ((nt, NEUT), (tl, NEUT), (tl, STER)):
        rr = [r for r in rows0 if r["task"] == "validate_domain" and r["variant"] in vs]
        e, lo, hi, tp, tn = bal(rr)
        out.append(f"{e:.1f} [{lo:.1f}, {hi:.1f}] (valid {tp:.1f} / invalid {tn:.1f})")
    L.append(f"| {NM[m]} | " + " | ".join(out) + " |")
L.append("")

# paired tests
L.append("#### T5. Paired, domain-clustered, Holm-corrected tests (think=off, mechanism layer)\n")
L.append("| model | task | contrast | first → second arm | Δ | clustered 95% CI | p | Holm p, m=30 | after Holm, m=30 | after Holm, m=60 | paper rule × √2.7 |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|")
def vv(v, p):
    if v not in ("FAV", "AGAINST"): return "NS"
    return v if p <= 0.05 else "**not significant**"
def fp(p): return f"{p:.3f}" if p >= 0.001 else f"{p:.1e}"
H30 = holm({(c["model"], c["task"], c["contrast"]): c["p"] for c in CONS})
H60csv = {(r["model"], r["task"], r["contrast"]): float(r["holm_p_H60_both"]) for r in csv.DictReader(open(OUT / "02_contrasts.csv")) if r["think"] == "off" and r["surface"] == "mech" and r["model"] in HEADLINE}
for c in CONS:
    key = (c["model"], c["task"], c["contrast"])
    r = dict(model=c["model"], task=c["task"], contrast=c["contrast"], verdict_clustered_paired=c["new"],
             holm_p_H30_mech=H30[key], holm_p_H60_both=H60csv[key], a_low=c["a_lo"], b_low=c["b_lo"], delta_low=c["d_lo"],
             ci_gov_lo=c["ci"][0], ci_gov_hi=c["ci"][1], governing=c["gov_name"], p_cluster_t_gov=c["p"])
    r["verdict_paper_wilson_x_sqrt2.7"] = c["paper_inf"]
    v = r["verdict_clustered_paired"]
    h30, h60 = float(r["holm_p_H30_mech"]), float(r["holm_p_H60_both"])
    pr = r["verdict_paper_wilson_x_sqrt2.7"]
    mark = "**" if (pr != v) else ""
    FAILREP = {("Qwen3_5_9B", "simulate"), ("qwen3_6_35b", "solve"), ("qwen3_6_35b", "simulate")}
    rep = " §" if (r["model"], r["task"]) in FAILREP else ""
    L.append(f"| {NM[r['model']]} | {r['task']} | {r['contrast'][:5].replace('avail','avail.').replace('steer','steer.')} | "
             f"{float(r['a_low']):.1f} → {float(r['b_low']):.1f} | {float(r['delta_low']):+.1f}{rep} | "
             f"[{float(r['ci_gov_lo']):+.1f}, {float(r['ci_gov_hi']):+.1f}]{'' if r['governing']=='domain' else ' (problem)'} | "
             f"{fp(float(r['p_cluster_t_gov']))} | {fp(h30)} | {mark}{vv(v, h30)}{mark} | {vv(v, h60)} | {pr} |")
L.append("")

# contamination
L.append("#### T7. Contamination: anonymized − canonical, unaided\n")
L.append("| model | cell | think | canonical | anonymized | Δ | governing 90% CI | verdict at ±5 |")
L.append("|---|---|---|---|---|---|---|---|")
for th in ("off", "on"):
    for m in MODELS:
        name = f"slurm_vllm_{m}_{th}_no-tools"
        can = eq.trials(RESULTS / "sweep5v2-live", name); anon = eq.trials(RESULTS / "sweep6-live", name)
        cells = (TASKS + ["pooled"]) if (th == "off" and m in HEADLINE) else ["pooled"]
        for t in cells:
            sel = (lambda k: True) if t == "pooled" else (lambda k, t=t: k[1] == t)
            r = eq.tost(*eq.paired_arrays(can, anon, sel))
            gov = "" if r["gov"] == "domain" else " (problem)"
            lab = eq.label(r)
            if t == "pooled": lab = f"**{lab}**"
            L.append(f"| {NM[m]} | {'pooled, 5 tasks' if t=='pooled' else t} | {th} | {r['ra']:.1f} | {r['rb']:.1f} | "
                     f"{r['est']:+.2f} | [{r['lo']:+.2f}, {r['hi']:+.2f}]{gov} | {lab} |")
L.append("")

# replication
par = json.loads((S / "parity_rederive.json").read_text())
cr = {(c["model"], c["task"], c["arm"]): c["sel"] for c in json.loads((S / "calling_rerun_vs_main.json").read_text())}
L.append("#### T8a. Tool cells: tool-verified success, rerun vs main sweep\n")
L.append("| model | task | arm | main sweep | rerun | Δ (rerun − main) | 90% CI | ±5 criterion | calling, main → rerun (Δ) |")
L.append("|---|---|---|---|---|---|---|---|---|")
for c in par["cells"]:
    met = c["verdict"] == "criterion met"
    q = cr[(c["model"], c["task"], c["arm"])]
    L.append(f"| {NM[c['model']]} | {c['task']} | {c['arm']} | {c['canon']:.1f} | {c['rerun']:.1f} | {c['delta']:+.1f} | "
             f"[{c['lo']:+.1f}, {c['hi']:+.1f}] | {'met' if met else '**not met (unresolved)**'} | "
             f"{q['main']:.1f} → {q['rerun']:.1f} ({q['delta']:+.1f} [{q['lo']:+.1f}, {q['hi']:+.1f}]) |")
L.append("")
L.append("#### T8b. Unaided cells: harness online grade, rerun Part C vs main sweep (simulate excluded)\n")
L.append("| model | task | main sweep | rerun | Δ (rerun − main) | 90% CI | ±5 criterion |")
L.append("|---|---|---|---|---|---|---|")
for c in par["part_c"]:
    met = c["verdict"] == "criterion met"
    L.append(f"| {NM[c['model']]} | {c['task']} | {c['canon']:.1f} | {c['rerun']:.1f} | {c['delta']:+.1f} | "
             f"[{c['lo']:+.1f}, {c['hi']:+.1f}] | {'met' if met else '**not met (unresolved)**'} |")
L.append("")
pt = sum(abs(c["delta"]) <= 5 for c in par["cells"]); pc = sum(abs(c["delta"]) <= 5 for c in par["part_c"])
mt = sum(c["verdict"] == "criterion met" for c in par["cells"]); mc = sum(c["verdict"] == "criterion met" for c in par["part_c"])
L.append(f"COUNTS: tool met {mt}/30, |Δ|<=5 {pt}/30; unaided met {mc}/12, |Δ|<=5 {pc}/12; unpaired rows total "
         f"{sum(c['ur']+c['uc'] for c in par['cells'] + par['part_c'])}")
(S / "s1_tables.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
