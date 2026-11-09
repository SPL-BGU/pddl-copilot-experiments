#!/usr/bin/env python3
"""C3b: generate the Study 2 part 1 tables of development/NUMBERS.md (and .tex fragments).

    python3 tools/reanalysis/s2_gen_md.py --results /abs/path/to/results [--check-only]

Study 2 part 1 = the delivered rerun (`results/delivered-rerun`, frozen package
822aace…, readout `development/reference/delivered_rerun_readout.json`). Inputs, all
read-only:

  * secondary.json (`development/reference/delivered_rerun_secondary/`), written by
    tools/delivered_rerun_secondary.py on the frozen package: per-wording, per-track
    and per-domain delivered counts and the E4 hand reads. Its grades reproduce the
    readout's E1 and E4 counts exactly (that script checks it).
  * the frozen readout JSON: E1 cell counts (self-check) and the frozen E4 categories.
  * the trial rows, loaded by the frozen loader (`tools.delivered_rerun.schema
    .load_cell`), for the tokens of the cost-of-pass split by track. Nothing is graded
    here: delivered successes per domain come from secondary.json `per_domain`.

Every cell list (models, tasks, wordings, domains, tracks, E4 categories) is read from
the data, so a later rerun (plan step D4) only reruns this script. Writes:

  * the block between the `s2_gen_md.py` markers in development/NUMBERS.md;
  * tools/reanalysis/out/s2_tables.md (the same block, standalone);
  * tools/reanalysis/out/tex/s2_*.tex (booktabs fragments; never into paper/).

Self-checks run first and halt the script on any mismatch (exit 2): the per-wording,
per-track and per-domain counts sum to the readout's E1 counts; the all-domain cost
rows reproduce secondary.json `cost` exactly; and a list of figures already in
NUMBERS.md is reproduced.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.delivered_rerun import constants as C  # noqa: E402  (frozen, read-only)
from tools.delivered_rerun import run as RUN  # noqa: E402
from tools.delivered_rerun import schema as S  # noqa: E402
from tools.reanalysis import gen_common as G  # noqa: E402

FROZEN_SHA = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"
TAG = "s2_gen_md.py"
RATIOS = (1, 2, 3, 4, 5)                      # output : input price ratio
TASK_ORDER = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
ARM_NAME = {"plain": "tools, plain", "steered": "tools, steered", "none": "unaided (Part C)"}


class Halt(Exception):
    pass


def task_key(t: str):
    return (TASK_ORDER.index(t) if t in TASK_ORDER else len(TASK_ORDER), t)


def ordered(seq):
    """Unique values in order of first appearance."""
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def bci(entry_boot: dict, k: int, n: int) -> str:
    return G.rate_cell(k, n, entry_boot["lo"], entry_boot["hi"])


def k_of(boot: dict) -> int:
    return int(round(boot["est"] * boot["n"] / 100))


# ------------------------------------------------------------------ inputs
def load_inputs(args):
    sec = json.loads(args.secondary.read_text())
    ro = json.loads(args.readout.read_text())
    if sec.get("frozen_package_sha256") != FROZEN_SHA or ro.get("package_sha256") != FROZEN_SHA:
        raise Halt("secondary.json or the readout is not from the frozen package 822aace…")
    if RUN.package_sha256() != FROZEN_SHA:
        raise Halt("the frozen package tools/delivered_rerun changed (hash is not 822aace…)")
    return sec, ro


def load_token_rows(rerun_root: Path, models: list[str]) -> dict:
    """{(model, task, arm, domain): [input tokens, output tokens, rows]} over Part A and
    Part C, through the frozen loader."""
    tok = defaultdict(lambda: [0, 0, 0])
    for m in models:
        for spec in (S.spec_rerun_a(C.REGISTERED, m), S.spec_rerun_c(C.REGISTERED, m)):
            lc = S.load_cell(rerun_root, spec)
            for r in lc.rows:
                arm = r.arm if r.with_tools else "none"
                t = tok[(m, r.task, arm, r.domain)]
                t[0] += r.tokens.prompt
                t[1] += r.tokens.completion
                t[2] += 1
    return tok


# ------------------------------------------------------------------ computations
def cost_by_track(sec, tok, models, tasks):
    """Cost-of-pass multiplier, tool arm ÷ Part C, per model (and pooled) × task ×
    track (classical, numeric, all), at every ratio in RATIOS."""
    track = sec["track"]
    succ = defaultdict(int)
    for e in sec["per_domain"]:
        if e["part"] in ("A", "C"):
            succ[(e["model"], e["task"], e["arm"], e["domain"])] += e["delivered_k"]
    out = []
    for m in list(models) + ["pooled"]:
        ms = models if m == "pooled" else [m]
        for t in tasks:
            doms_all = sorted({d for (x, tt, a, d) in tok if x in ms and tt == t and a == "none"})
            for tr in ("classical", "numeric", "all"):
                doms = [d for d in doms_all if tr == "all" or track[d] == tr]
                rec = {"model": m, "task": t, "track": tr, "k_domains": len(doms), "arms": {},
                       "multiplier": {}}
                for arm in ("plain", "steered", "none"):
                    inp = sum(tok[(x, t, arm, d)][0] for x in ms for d in doms)
                    outp = sum(tok[(x, t, arm, d)][1] for x in ms for d in doms)
                    n = sum(tok[(x, t, arm, d)][2] for x in ms for d in doms)
                    k = sum(succ[(x, t, arm, d)] for x in ms for d in doms)
                    rec["arms"][arm] = {"n": n, "delivered_k": k, "input_tokens": inp,
                                        "output_tokens": outp}
                for arm in ("plain", "steered"):
                    rec["multiplier"][arm] = {}
                    for q in RATIOS:
                        def per_dom(a):
                            c = [sum(tok[(x, t, a, d)][0] + q * tok[(x, t, a, d)][1] for x in ms)
                                 for d in doms]
                            s = [sum(succ[(x, t, a, d)] for x in ms) for d in doms]
                            return c, s
                        ct, st = per_dom(arm)
                        cn, sn = per_dom("none")
                        rec["multiplier"][arm][q] = G.multiplier_boot(ct, st, cn, sn, seed=C.SEED,
                                                                      b=C.B_BOOT)
                out.append(rec)
    return out


def e4_table(ro, sec):
    """Per task × category: frozen E4 count, hand-read count, folded count."""
    frozen = defaultdict(Counter)
    gap = Counter()
    for e in ro["e4"]:
        gap[e["task"]] += e["n_gap"]
        frozen[e["task"]].update(e["categories"])
    hand = defaultdict(Counter)
    right = defaultdict(Counter)
    for r in sec["e4_readings"]["rows"]:
        hand[r["task"]][r["category"]] += 1
        right[r["task"]][r["category"]] += r["human_correct"] == "yes"
    nr = "NEEDS_READING"
    cats = ordered([c for e in ro["e4"] for c in e["categories"]]
                   + [c for t in hand for c in hand[t]])
    tasks = sorted({e["task"] for e in ro["e4"]}, key=task_key)
    rows = []
    for t in tasks + ["all"]:
        ts = tasks if t == "all" else [t]
        fz = sum((frozen[x] for x in ts), Counter())
        hd = sum((hand[x] for x in ts), Counter())
        rt = sum((right[x] for x in ts), Counter())
        g = sum(gap[x] for x in ts)
        for c in cats:
            f, h = fz.get(c, 0), hd.get(c, 0)
            folded = 0 if c == nr else f + h
            if f == 0 and h == 0:
                continue
            rows.append({"task": t, "gap": g, "category": c, "frozen": f, "hand": h,
                         "folded": folded, "right": rt.get(c, 0)})
    return rows, gap


# ------------------------------------------------------------------ self-checks
def self_checks(sec, ro, cost, e4rows) -> list[str]:
    bad, ok = [], []
    e1 = {(e["model"], e["task"], e["arm"]): (e["delivered_k"], e["n"]) for e in ro["e1"]}
    # per wording sums to E1
    pw = defaultdict(lambda: [0, 0])
    for e in sec["per_wording"]:
        if e["part"] == "A":
            arm = "plain" if e["variant"] in C.PLAIN else "steered"
            pw[(e["model"], e["task"], arm)][0] += e["delivered_k"]
            pw[(e["model"], e["task"], arm)][1] += e["n"]
    for key, v in e1.items():
        (ok if tuple(pw[key]) == v else bad).append(f"per-wording sum = E1 {key}")
    # per track and per domain sum to E1
    tr = defaultdict(lambda: [0, 0])
    for e in sec["by_track"]:
        if e["arm"] != "none":
            tr[(e["model"], e["task"], e["arm"])][0] += k_of(e["delivered"])
            tr[(e["model"], e["task"], e["arm"])][1] += e["n"]
    pdm = defaultdict(lambda: [0, 0])
    for e in sec["per_domain"]:
        if e["part"] == "A":
            pdm[(e["model"], e["task"], e["arm"])][0] += e["delivered_k"]
            pdm[(e["model"], e["task"], e["arm"])][1] += e["n"]
    for key, v in e1.items():
        (ok if tuple(tr[key]) == v else bad).append(f"per-track sum = E1 {key}")
        (ok if tuple(pdm[key]) == v else bad).append(f"per-domain sum = E1 {key}")
    # cost, all domains, reproduces secondary.json exactly
    ref = {(e["model"], e["task"]): e for e in sec["cost"]}
    for rec in cost:
        if rec["track"] != "all":
            continue
        e = ref[(rec["model"], rec["task"])]
        for arm in ("plain", "steered", "none"):
            a, b = rec["arms"][arm], e["arms"][arm]
            same = all(a[x] == b[x] for x in ("n", "delivered_k", "input_tokens", "output_tokens"))
            (ok if same else bad).append(f"cost tokens/successes {rec['model']} {rec['task']} {arm}")
        for arm in ("plain", "steered"):
            for q, mm in e["multiplier"][arm].items():
                mine = rec["multiplier"][arm][int(q)]
                if mm is None or mine is None:
                    (ok if mm is None and mine is None else bad).append(
                        f"cost multiplier {rec['model']} {rec['task']} {arm} {q}:1 (none)")
                    continue
                same = all(abs(mine[x] - mm[x]) < 1e-9 for x in ("est", "lo", "hi")) and \
                    mine["draws_with_zero_successes"] == mm["draws_with_zero_successes"]
                (ok if same else bad).append(f"cost multiplier {rec['model']} {rec['task']} {arm} {q}:1")
    # figures already in NUMBERS.md (the descriptive secondary analyses block of the rerun)
    pwx = {(e["part"], e["model"], e["task"], e["variant"]): e for e in sec["per_wording"]}
    g = C.PART_B_MODEL
    inv = [f"{pwx[('A', g, 'validate_plan', v)]['invocation']['est']:.1f}" for v in C.PLAIN]
    invb = [f"{pwx[('B', g, 'validate_plan', v)]['invocation']['est']:.1f}" for v in C.PLAIN]
    c_pool = {r["task"]: r for r in cost if r["model"] == "pooled" and r["track"] == "all"}
    m = c_pool["solve"]["multiplier"]
    fx = lambda d: f"{d['est']:.2f} [{d['lo']:.2f}, {d['hi']:.2f}]"  # noqa: E731
    e4all = {r["category"]: r for r in e4rows if r["task"] == "all"}
    e4sim = {r["category"]: r for r in e4rows if r["task"] == "simulate"}
    hand_rows = sec["e4_readings"]["rows"]
    v35 = [r for r in hand_rows if r["model"] == "qwen3_6_35b" and r["task"] == "validate_plan"]
    gap35 = sum(e["n_gap"] for e in ro["e4"] if e["model"] == "qwen3_6_35b"
                and e["task"] == "validate_plan")
    expect = [
        ("Gemma validate_plan invocation by wording, plain", inv, ["31.0", "25.1", "3.9"]),
        ("same, Part B neutral", invb, ["44.2", "29.7", "6.7"]),
        ("pooled solve plain x 1:1", fx(m["plain"][1]), "1.48 [0.89, 2.27]"),
        ("pooled solve plain x 5:1", fx(m["plain"][5]), "0.58 [0.35, 0.90]"),
        ("pooled solve steered x 1:1", fx(m["steered"][1]), "1.32 [0.80, 2.06]"),
        ("pooled solve steered x 5:1", fx(m["steered"][5]), "0.51 [0.31, 0.80]"),
        ("E4 hand-read rows", sum(r["hand"] for r in e4all.values()), 290),
        ("E4 hand-read WRONG_WRAPPER", e4all["WRONG_WRAPPER"]["hand"], 218),
        ("E4 hand-read right to a human reader", sum(r["right"] for r in e4all.values()), 180),
        ("simulate gap rows", e4sim["REFUSED_OR_CLIPPED_FINAL"]["gap"], 1266),
        ("simulate hand-read right", sum(r["right"] for r in e4sim.values()), 154),
        ("simulate REFUSED_OR_CLIPPED_FINAL", e4sim["REFUSED_OR_CLIPPED_FINAL"]["folded"], 843),
        ("simulate full trajectories in an unread form (WRONG_WRAPPER, right)",
         e4sim["WRONG_WRAPPER"]["right"], 148),
        ("simulate change lists or missing constants (right)",
         e4sim["ABRIDGED"]["right"] + e4sim["NUMERIC_OMITTED"]["right"], 6),
        ("35B validate_plan gap rows / hand-read right", (gap35, sum(r["human_correct"] == "yes"
                                                                   for r in v35)), (32, 25)),
    ]
    for name, got, want in expect:
        (ok if got == want else bad).append(f"NUMBERS figure: {name}: got {got}, want {want}")
    if bad:
        raise Halt("self-check failed:\n  " + "\n  ".join(bad))
    return ok


# ------------------------------------------------------------------ rendering
def render(sec, ro, cost, e4rows, checks, tex_dir: Path | None) -> str:
    pw = {(e["part"], e["model"], e["task"], e["variant"]): e for e in sec["per_wording"]}
    models = ordered(e["model"] for e in sec["per_wording"] if e["part"] == "A")
    tasks = sorted({e["task"] for e in sec["per_wording"] if e["part"] == "A"}, key=task_key)
    variants = sorted({e["variant"] for e in sec["per_wording"] if e["part"] == "A"})
    plain = [v for v in variants if v in C.PLAIN]
    track = sec["track"]
    L = []
    tex = {}

    def table(name, headers, rows, note=""):
        L.append(G.md_table(headers, rows))
        L.append("")
        tex[name] = G.tex_table(headers, rows, source=f"tools/reanalysis/{TAG}", note=note)

    n_checks = len(checks)
    n_fig = sum(c.startswith("NUMBERS figure") for c in checks)
    L += [f"*Generated by `tools/reanalysis/{TAG}`; do not edit between the markers, rerun the "
          "script. Inputs: `reference/delivered_rerun_secondary/secondary.json` (per wording, "
          "per track, per domain, hand reads), `reference/delivered_rerun_readout.json` (E1, "
          "E4), and the trial rows of `results/delivered-rerun/` through the frozen loader "
          f"(package `{FROZEN_SHA[:7]}…`, tokens only). Self-check: {n_checks} of {n_checks} "
          "checks pass (counts sum to the readout's E1 in all cells; the all-domain cost rows "
          f"equal `secondary.json` to 1e-9; {n_fig} figures already in this file are reproduced).*",
          ""]
    L += ["**Apparatus: Study 2 part 1 only** (the delivered rerun: full answer storage, the "
          "final-request retry, the leaked-prefix strip, vLLM 0.20.2, the delivered grader of the "
          "frozen package). Separate-apparatus replication: never pooled with a Study 1 table, "
          "and no figure here is the exact delivered rate of a canonical cell. *Delivered* = the "
          "frozen grader's verdict on the final answer. *Invocation* = any tool call (the "
          "readout's measure; Study 1 *calling* counts only the task's own tool, and the two "
          "differ in three cells, T8a note). Intervals: domain-cluster percentile bootstrap 95% "
          "from the frozen `stats.cluster_bootstrap` (k = the domains in the subset); † = Wilson "
          "95% where the rate is exactly 0 or 100%.", ""]

    # ---- quote summary
    g = C.PART_B_MODEL
    vp = "validate_plan"
    inv = [pw[("A", g, vp, v)]["invocation"]["est"] for v in plain]
    invb = [pw[("B", g, vp, v)]["invocation"]["est"] for v in plain if ("B", g, vp, v) in pw]
    cp = {(r["task"], r["track"]): r for r in cost if r["model"] == "pooled"}

    def mx(t, tr, arm, q):
        return G.mult_cell(cp[(t, tr)]["multiplier"][arm][q])
    L += ["#### S2-Q. What to quote from these tables", ""]
    qrows = [
        ["Gemma validate_plan invocation by wording, plain (descriptive)",
         " · ".join(f"v{v} **{x:.1f}**" for v, x in zip(plain, inv))
         + (f"; Part B neutral {' / '.join(f'{x:.1f}' for x in invb)}" if invb else ""),
         "one pooled invocation rate as if wording did not matter"],
        ["pooled solve cost-of-pass multiplier, tools-plain ÷ unaided, by track (descriptive)",
         f"classical **{mx('solve', 'classical', 'plain', 1)}** at 1:1, "
         f"{mx('solve', 'classical', 'plain', 5)} at 5:1; numeric **{mx('solve', 'numeric', 'plain', 1)}**"
         f" at 1:1, {mx('solve', 'numeric', 'plain', 5)} at 5:1",
         "a track figure without the price ratio; a track figure as a test (k = "
         + " / ".join(str(v) for v in sorted(set(Counter(track.values()).values())))
         + " domains a track)"],
        ["delivery gap, E4 folded with the hand reads", "the S2-E table, with the frozen E4 "
         "column beside it", "a folded count as the readout's E4 (the frozen E4 is the record)"],
    ]
    L += [G.md_table(["figure", "**quote this**", "do NOT quote"], qrows), ""]

    # ---- per wording
    L += ["#### S2-W. Per wording: delivered beside invocation (Part A tools, Part C unaided)", "",
          "Wording i pairs plain v1i with steered v1(i+3) (the steered prompt is the plain one "
          "plus one sentence naming the tool) and with unaided Part C on the plain wording.", ""]
    hdr = ["model", "task", "wording", "n", "delivered, plain", "invocation, plain",
           "delivered, steered", "invocation, steered", "delivered, unaided"]
    rows = []
    for m in models:
        for t in tasks:
            for v in plain:
                a, s, c = pw[("A", m, t, v)], pw.get(("A", m, t, v + C.STEER_OFFSET)), pw.get(("C", m, t, v))
                rows.append([G.model_name(m), t, f"v{v} / v{v + C.STEER_OFFSET}", a["n"],
                             bci(a["delivered"], a["delivered_k"], a["n"]),
                             bci(a["invocation"], a["invocation_k"], a["n"]),
                             bci(s["delivered"], s["delivered_k"], s["n"]) if s else "–",
                             bci(s["invocation"], s["invocation_k"], s["n"]) if s else "–",
                             bci(c["delivered"], c["delivered_k"], c["n"]) if c else "–"])
    for (part, m, t, v), e in sorted(pw.items(), key=lambda kv: (kv[0][1], task_key(kv[0][2]), kv[0][3])):
        if part != "B" or v not in C.PLAIN:
            continue
        s = pw.get(("B", m, t, v + C.STEER_OFFSET))
        rows.append([f"{G.model_name(m)}, Part B (neutral prompt)", t, f"v{v} / v{v + C.STEER_OFFSET}",
                     e["n"], bci(e["delivered"], e["delivered_k"], e["n"]),
                     bci(e["invocation"], e["invocation_k"], e["n"]),
                     bci(s["delivered"], s["delivered_k"], s["n"]) if s else "–",
                     bci(s["invocation"], s["invocation_k"], s["n"]) if s else "–", "–"])
    table("s2_per_wording", hdr, rows)

    L += ["Spread over the three wordings (max − min, points):", ""]
    rows = []
    for m in models:
        for t in tasks:
            def spread(part, vs, key):
                xs = [pw[(part, m, t, v)][key]["est"] for v in vs if (part, m, t, v) in pw]
                return f"{min(xs):.1f}–{max(xs):.1f} ({max(xs) - min(xs):.1f})" if xs else "–"
            st = [v + C.STEER_OFFSET for v in plain]
            rows.append([G.model_name(m), t, spread("A", plain, "invocation"),
                         spread("A", plain, "delivered"), spread("A", st, "invocation"),
                         spread("A", st, "delivered"), spread("C", plain, "delivered")])
    table("s2_per_wording_spread", ["model", "task", "invocation, plain", "delivered, plain",
                                    "invocation, steered", "delivered, steered",
                                    "delivered, unaided"], rows)

    # ---- per track
    tk = {(e["model"], e["task"], e["arm"], e["track"]): e for e in sec["by_track"]}
    tracks = ordered(e["track"] for e in sec["by_track"])
    ndom = Counter(track.values())
    L += ["#### S2-T. Classical against numeric (pooled over wordings)", "",
          "Domains per track: " + ", ".join(f"{tr} {ndom[tr]}" for tr in tracks)
          + ". The bootstrap resamples the domains of one track only.", ""]
    rows = []
    for m in models:
        for t in tasks:
            for tr in tracks:
                cells = [G.model_name(m), t, tr, tk[(m, t, "plain", tr)]["n"]]
                for arm in ("plain", "steered"):
                    e = tk[(m, t, arm, tr)]
                    cells += [bci(e["delivered"], k_of(e["delivered"]), e["n"]),
                              bci(e["invocation"], k_of(e["invocation"]), e["n"])]
                e = tk[(m, t, "none", tr)]
                cells.append(bci(e["delivered"], k_of(e["delivered"]), e["n"]))
                rows.append(cells)
    table("s2_by_track", ["model", "task", "track", "n per arm", "delivered, plain",
                          "invocation, plain", "delivered, steered", "invocation, steered",
                          "delivered, unaided"], rows)

    # ---- per domain, compact
    pd_ = {(e["part"], e["model"], e["task"], e["arm"], e["domain"]): e for e in sec["per_domain"]}
    doms = sorted({e["domain"] for e in sec["per_domain"]}, key=lambda d: (track[d], d))
    nper = {t: ordered(e["n"] for e in sec["per_domain"] if e["part"] == "A" and e["task"] == t)
            for t in tasks}
    L += ["#### S2-D. Per domain, delivered % (plain / steered / unaided), pooled over wordings",
          "", "Rows per domain and arm: " + ", ".join(
              f"{t} {'/'.join(str(x) for x in nper[t])}" for t in tasks)
          + ". Too few for single-domain claims; read for pattern. Counts, Wilson intervals "
          "and invocation: `reference/delivered_rerun_secondary/per_domain.csv`.", ""]
    rows = []
    for d in doms:
        for m in models:
            r_ = [d, track[d][:3], G.model_name(m)]
            for t in tasks:
                vals = [pd_.get(("A", m, t, "plain", d)), pd_.get(("A", m, t, "steered", d)),
                        pd_.get(("C", m, t, "none", d))]
                r_.append(" / ".join("–" if v is None else f"{v['delivered_pct']:.0f}" for v in vals))
            rows.append(r_)
    table("s2_per_domain", ["domain", "track", "model"] + tasks, rows)

    # ---- cost by track
    L += ["#### S2-C. Cost-of-pass multiplier by price ratio, split by track (delivered score)", "",
          "Cost-of-pass = (input + r × output tokens, summed over all turns) / delivered "
          "successes; multiplier = tool arm ÷ unaided Part C (same run, same grader, same "
          "fixtures); below 1 the tool arm is cheaper per delivered success. r = output:input "
          "price ratio. Domain-cluster bootstrap 95%, the same domain draw for both arms (seed "
          f"{C.SEED}, {C.B_BOOT:,} draws); draws where an arm has no success are dropped and "
          "counted. Track *all* reproduces `secondary.json` at 1, 3, 4 and 5:1; 2:1 and the "
          "track split are new here. Tokens per trial in the last columns.", ""]
    for arm in ("plain", "steered"):
        rows = []
        for rec in cost:
            a = rec["arms"]
            rows.append([G.model_name(rec["model"]), rec["task"], rec["track"], rec["k_domains"]]
                        + [G.mult_cell(rec["multiplier"][arm][q]) for q in RATIOS]
                        + [f"{(a[arm]['input_tokens'] + a[arm]['output_tokens']) / a[arm]['n']:,.0f}",
                           f"{(a['none']['input_tokens'] + a['none']['output_tokens']) / a['none']['n']:,.0f}"])
        L += [f"**{ARM_NAME[arm]} ÷ unaided**", ""]
        table(f"s2_cost_{arm}", ["model", "task", "track", "domains"]
              + [f"× at {q}:1" for q in RATIOS] + ["tokens/trial, tools", "tokens/trial, unaided"], rows)

    # ---- E4
    L += ["#### S2-E. Delivery gap: frozen E4 categories beside the hand reads", "",
          "Gap rows = the tool returned the right result but the delivered answer is graded "
          "wrong (readout E4). *E4 frozen* = the readout's mechanical category (the record). "
          "*Hand read* = the category two independent readers and a third reading gave the "
          "NEEDS_READING rows (`reference/delivered_rerun_secondary/hand_reads/`). *Folded* = "
          "E4 with each NEEDS_READING row moved to its hand-read category: **descriptive, not a "
          "registered reading**. *Right to a reader* = hand-read rows a human reader judges "
          "right.", ""]
    rows = [[r["task"], r["gap"], r["category"], r["frozen"], r["hand"] or "",
             r["folded"], r["right"] or ""] for r in e4rows]
    table("s2_e4_gap", ["task", "gap rows", "category", "E4 frozen (record)", "hand read",
                        "folded (descriptive)", "right to a reader"], rows)

    if tex_dir is not None:
        tex_dir.mkdir(parents=True, exist_ok=True)
        for name, body in tex.items():
            (tex_dir / f"{name}.tex").write_text(body)
    return "\n".join(L).rstrip("\n") + "\n"


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=REPO / "results",
                    help="results root holding delivered-rerun/ (read-only)")
    ap.add_argument("--secondary", type=Path,
                    default=REPO / "development/reference/delivered_rerun_secondary/secondary.json")
    ap.add_argument("--readout", type=Path,
                    default=REPO / "development/reference/delivered_rerun_readout.json")
    ap.add_argument("--numbers", type=Path, default=REPO / "development/NUMBERS.md")
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent / "out")
    ap.add_argument("--check-only", action="store_true", help="run the self-checks, write nothing")
    args = ap.parse_args(argv)
    try:
        sec, ro = load_inputs(args)
        models = ordered(e["model"] for e in sec["per_wording"] if e["part"] == "A")
        tasks = sorted({e["task"] for e in sec["per_wording"] if e["part"] == "A"}, key=task_key)
        tok = load_token_rows(args.results / "delivered-rerun", models)
        cost = cost_by_track(sec, tok, models, tasks)
        e4rows, _gap = e4_table(ro, sec)
        checks = self_checks(sec, ro, cost, e4rows)
    except (Halt, RUN.Halt, S.SchemaError) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"self-check: {len(checks)} of {len(checks)} pass", file=sys.stderr)
    if args.check_only:
        return 0
    body = render(sec, ro, cost, e4rows, checks, args.out_dir / "tex")
    (args.out_dir / "s2_tables.md").write_text(body)
    (args.out_dir / "s2_cost_by_track.json").write_text(json.dumps(cost, indent=1) + "\n")
    changed = G.write_numbers(args.numbers, TAG, body)
    print(f"wrote {args.out_dir}/s2_tables.md, {args.out_dir}/tex/s2_*.tex; "
          f"NUMBERS.md {'updated' if changed else 'unchanged'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
