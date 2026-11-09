#!/usr/bin/env python3
"""C3a: generate the Study 1 breakdown tables of development/NUMBERS.md (and .tex fragments).

    python3 tools/reanalysis/s1_breakdowns_md.py --results /abs/path/to/results [--check-only]

Study 1 = the main sweep, canonical corpus `results/sweep5v2-live`, headline models,
thinking off. Per wording, classical against numeric, and per domain, on the
mechanism layer only: unaided (the no-tools cell's online grade), calling
(`tool_selected`) and tool-verified (`success` on the tools cell). Rows are loaded
by `common.load_cell`, the loader of the Study 1 block (T1-T5), so the pooled
counts are those of T1 and T2.

The delivered tool-arm columns of the older breakdown scripts (`bc_per_wording.py`,
`bc_per_domain.py`: the overlay's `e2e_strict` bounds) are left out on purpose: that
surface is retired for the open models in Study 1 (Study 1 block, "Rules"), and the
Study 2 tables carry the delivered surface on the fixed setup.

Writes the block between the `s1_breakdowns_md.py` markers of NUMBERS.md,
tools/reanalysis/out/s1_breakdowns.md and tools/reanalysis/out/tex/s1_*.tex. The
self-checks run first and halt on a mismatch (exit 2): pooled counts equal the T1
and T2 rows of NUMBERS.md, and the per-wording, per-track and per-domain counts
equal the committed `out/breakdowns_cost/*_sweep5v2-live.csv` of the earlier scripts,
the 35B main-sweep calling rates quoted from T8a equal the pooled counts here, and the
"from" values of the ISS-027 caveat equal the pooled counts here.

Three caveats are rendered with the tables (md and the `.tex` notes): the unaided
simulate cells carry the format-exact qualifier of the Job 2 row (marked ¶); the success
cells are frozen grades under ISS-027 (the plan grader's case fault); and the 35B calling
cells come from the main sweep alone, while the 35B calling rate is quoted as both runs
(STATUS.md, decided 2026-11-09; T8a and T8c).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import gen_common as G  # noqa: E402
from bc_common import domain_track  # noqa: E402

TAG = "s1_breakdowns_md.py"
CORPUS = "sweep5v2-live"
TASK_ORDER = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
BC_ARM = {"unaided": "nt-neut", "plain": "tl-neut", "steered": "tl-ster"}
WORD = {11: "w1", 12: "w2", 13: "w3", 14: "w1", 15: "w2", 16: "w3"}
QWEN35 = "qwen3_6_35b"

# Unaided simulate on the shared-budget corpus: the qualifier of the Job 2 row of NUMBERS.md.
QUAL_MARK = "¶"
QUAL_NOTE = ("¶ = unaided simulate, format-exact on the shared-budget corpus (the qualifier of the "
             "Job 2 row: \"0/3,000 format-exact on the shared-budget corpus\"). An answer cut by "
             "the output budget counts as a failure, so never read this 0 as a capability floor; "
             "the capability figure is the decoupled control, 22–40% content-correct at ≥4B.")

# ISS-027 (OPEN_ISSUES.md, scope checked 2026-11-09 on branch analysis/iss027-scope):
# trials of these pooled think=off cells that pass once the grader case-folds names, and
# the pooled rate before and after as the scope record states it (self-checked here).
ISS027_MOVES = {("gemma4_26b-a4b", "simulate", "plain"): (10, 91.7, 95.0),
                ("gemma4_26b-a4b", "simulate", "steered"): (10, 90.7, 94.0),
                ("Qwen3_5_9B", "solve", "unaided"): (2, 10.7, 11.3)}


class Halt(Exception):
    pass


def task_key(t):
    return (TASK_ORDER.index(t) if t in TASK_ORDER else len(TASK_ORDER), t)


def load(models):
    """{model: {"unaided": rows, "tools": rows}} for think=off."""
    return {m: {"unaided": common.load_cell(CORPUS, m, "off", False),
                "tools": common.load_cell(CORPUS, m, "off", True)} for m in models}


def arm_rows(cell, arm, task, variants=None, pred=None):
    rows = cell["unaided"] if arm == "unaided" else cell["tools"]
    vs = variants if variants is not None else (common.NEUT if arm != "steered" else common.STER)
    return [r for r in rows if r["task"] == task and r["variant"] in vs and (pred is None or pred(r))]


def stat(rows, field):
    """(k, n, cell string) for a 0/1 field with the domain bootstrap 95%."""
    n = len(rows)
    if n == 0:
        return 0, 0, "–"
    v = np.array([r[field] for r in rows], float)
    k = int(v.sum())
    if 0 < k < n:
        lo, hi = common.cluster_boot(v, np.array([r["domain"] for r in rows]))
    else:
        lo = hi = 0.0
    return k, n, G.rate_cell(k, n, 100 * lo, 100 * hi)


def compute(cells, models, tasks, track):
    """Every count and cell string the tables need, keyed for the self-checks."""
    res = {"wording": {}, "track": {}, "domain": {}, "pooled": {}}
    tracks = sorted(set(track.values()))
    for m in models:
        c = cells[m]
        for t in tasks:
            for arm in ("unaided", "plain", "steered"):
                rr = arm_rows(c, arm, t)
                res["pooled"][(m, t, arm, "mech")] = stat(rr, "mech")[:2]
                if arm != "unaided":
                    res["pooled"][(m, t, arm, "called")] = stat(rr, "called")[:2]
            for i, v in enumerate(common.NEUT):
                for arm, vv in (("unaided", v), ("plain", v), ("steered", common.STER[i])):
                    rr = arm_rows(c, arm, t, (vv,))
                    res["wording"][(m, t, arm, WORD[vv], "mech")] = stat(rr, "mech")
                    if arm != "unaided":
                        res["wording"][(m, t, arm, WORD[vv], "called")] = stat(rr, "called")
            for tr in tracks:
                for arm in ("unaided", "plain", "steered"):
                    rr = arm_rows(c, arm, t, pred=lambda r, tr=tr: track[r["domain"]] == tr)
                    res["track"][(m, t, arm, tr, "mech")] = stat(rr, "mech")
                    if arm != "unaided":
                        res["track"][(m, t, arm, tr, "called")] = stat(rr, "called")
            doms = sorted({r["domain"] for r in c["tools"] if r["task"] == t})
            for d in doms:
                for arm in ("unaided", "plain", "steered"):
                    rr = arm_rows(c, arm, t, pred=lambda r, d=d: r["domain"] == d)
                    k = sum(r["mech"] for r in rr)
                    kc = sum(r["called"] or 0 for r in rr) if arm != "unaided" else None
                    res["domain"][(m, t, arm, d)] = (k, len(rr), kc)
    return res


# ------------------------------------------------------------------ self-checks
def parse_numbers_t1_t2(text: str) -> dict:
    """Counts of the T1 and T2 tables of NUMBERS.md: {(name, task, arm, field): (k, n)}."""
    out = {}
    sec = text.split("#### T1.", 1)[1].split("#### T3.", 1)[0]
    t1, t2 = sec.split("#### T2.", 1)
    for ln in t1.splitlines():
        p = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(p) == 6 and p[1] in TASK_ORDER:
            n = int(p[2].replace(",", ""))
            for arm, cell in zip(("unaided", "plain", "steered"), p[3:]):
                out[(p[0], p[1], arm, "mech")] = (int(re.search(r"\((\d+)\)$", cell).group(1)), n)
    for ln in t2.splitlines():
        p = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(p) == 6 and p[1] in TASK_ORDER:
            for arm, cell in zip(("plain", "steered"), p[2:4]):
                k, n = re.search(r"\((\d+)/(\d+)\)$", cell).groups()
                out[(p[0], p[1], arm, "called")] = (int(k), int(n))
    return out


def parse_numbers_t8a_calling(text: str) -> dict:
    """Calling column of T8a: {(name, task, arm): (main, rerun, delta string)}."""
    sec = text.split("#### T8a.", 1)[1].split("#### T8b.", 1)[0]
    out = {}
    for ln in sec.splitlines():
        p = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(p) == 9 and p[1] in TASK_ORDER:
            m = re.match(r"([\d.]+) → ([\d.]+) \((.+)\)$", p[8])
            if m:
                out[(p[0], p[1], p[2])] = (float(m.group(1)), float(m.group(2)), m.group(3))
    return out


def self_checks(res, numbers_text, bc_dir: Path, models, tasks) -> list[str]:
    ok, bad = [], []
    # 35B calling, main sweep: the T8a main values equal the pooled counts here
    if QWEN35 in models:
        t8a = parse_numbers_t8a_calling(numbers_text)
        seen = 0
        for (name, t, arm), (main, _, _) in t8a.items():
            if name != G.model_name(QWEN35) or t not in tasks:
                continue
            k, n = res["pooled"][(QWEN35, t, arm, "called")]
            seen += 1
            (ok if round(100 * k / n, 1) == main else bad).append(
                f"T8a calling main {name} {t} {arm}: {100 * k / n:.1f} vs {main}")
        if seen != len(tasks) * 2:
            bad.append(f"T8a: found {seen} 35B calling rows, expected {len(tasks) * 2}")
    # ISS-027 caveat: the scope record's before/after rates follow from the pooled counts here
    for (m, t, arm), (add, before, after) in ISS027_MOVES.items():
        if m not in models or t not in tasks:
            continue
        k, n = res["pooled"][(m, t, arm, "mech")]
        got = (round(100 * k / n, 1), round(100 * (k + add) / n, 1))
        (ok if got == (before, after) else bad).append(
            f"ISS-027 {m} {t} {arm}: {got} vs {(before, after)}")
    want = parse_numbers_t1_t2(numbers_text)
    for (m, t, arm, f), got in res["pooled"].items():
        key = (G.model_name(m), t, arm, f)
        if key in want:
            (ok if tuple(got) == want[key] else bad).append(f"NUMBERS T1/T2 {key}: {got} vs {want[key]}")
    if len([x for x in ok if x.startswith("NUMBERS")]) != len(models) * len(tasks) * 5:
        bad.append("not every pooled cell was found in the NUMBERS T1/T2 tables")
    # per wording vs bc_per_wording CSV
    for r in csv.DictReader(open(bc_dir / f"per_wording_{CORPUS}.csv")):
        if r["model"] not in models:
            continue
        arm = {v: k for k, v in BC_ARM.items()}[r["arm"]]
        k, n, _ = res["wording"][(r["model"], r["task"], arm, r["wording"], "mech")]
        (ok if (k, n) == (int(r["harness_ok"]), int(r["n"])) else bad).append(
            f"per wording {r['model']} {r['task']} {arm} {r['wording']} success")
        if arm != "unaided":
            kc = res["wording"][(r["model"], r["task"], arm, r["wording"], "called")][0]
            (ok if kc == int(r["called"]) else bad).append(
                f"per wording {r['model']} {r['task']} {arm} {r['wording']} calling")
    for r in csv.DictReader(open(bc_dir / f"track_{CORPUS}.csv")):
        arm = {v: k for k, v in BC_ARM.items()}[r["arm"]]
        k, n, _ = res["track"][(r["model"], r["task"], arm, r["track"], "mech")]
        same = (k, n) == (int(r["harness_ok"]), int(r["n"]))
        if arm != "unaided":
            same &= res["track"][(r["model"], r["task"], arm, r["track"], "called")][0] == int(r["called"])
        (ok if same else bad).append(f"per track {r['model']} {r['task']} {arm} {r['track']}")
    for r in csv.DictReader(open(bc_dir / f"per_domain_{CORPUS}.csv")):
        arm = {v: k for k, v in BC_ARM.items()}[r["arm"]]
        k, n, kc = res["domain"][(r["model"], r["task"], arm, r["domain"])]
        same = (k, n) == (int(r["harness_ok"]), int(r["n"]))
        if arm != "unaided":
            same &= kc == int(r["called"])
        (ok if same else bad).append(f"per domain {r['model']} {r['task']} {arm} {r['domain']}")
    if bad:
        raise Halt("self-check failed:\n  " + "\n  ".join(bad[:40]))
    return ok


# ------------------------------------------------------------------ rendering
def render(res, models, tasks, track, checks, tex_dir: Path | None, numbers_text: str = "") -> str:
    L, tex = [], {}

    def table(name, headers, rows, notes=()):
        L.append(G.md_table(headers, rows))
        L.append("")
        note = ""
        if notes:
            note = "\n".join(["Caveats the wrapping caption must carry (NUMBERS.md, Study 1 breakdowns):"]
                             + [f"- {x}" for x in notes])
        tex[name] = G.tex_table(headers, rows, source=f"tools/reanalysis/{TAG}", note=note)

    W = res["wording"]
    words = sorted({k[3] for k in W})
    P = res["pooled"]

    def q(t, arm, s):
        """The format-exact qualifier on every unaided simulate cell."""
        return f"{s}{QUAL_MARK}" if t == "simulate" and arm == "unaided" else s

    def prate(m, t, arm, f="mech", add=0):
        k, n = P[(m, t, arm, f)]
        return f"{100 * (k + add) / n:.1f}"

    iss_moves = [(m, t, arm, d[0]) for (m, t, arm), d in ISS027_MOVES.items()
                 if m in models and t in tasks]
    iss_list = "; ".join(f"{G.model_name(m)} {t} {'unaided' if arm == 'unaided' else 'tool-verified ' + arm} "
                         f"{prate(m, t, arm)} → {prate(m, t, arm, add=d)} (+{d} trials)"
                         for m, t, arm, d in iss_moves)
    ISS027_NOTE = ("ISS-027 (open, `OPEN_ISSUES.md`): the plan grader (pyval 0.1.5) is case-sensitive on "
                   "object and action names, and PDDL is case-insensitive, so a plan that copies the "
                   "capitals of the satellite p02–p05 or pogo_stick fixtures is graded wrong. This hits "
                   "unaided solve and the simulate and validate_plan tool arms. The success cells are the "
                   "frozen grades; a corrected figure goes beside them post hoc. Pooled cells that would "
                   "move (think=off): " + iss_list + ". Every other pooled frozen figure here moves by "
                   "1 point or less, but a single wording or domain cell can move more. Calling is not "
                   "affected.")
    t8a = parse_numbers_t8a_calling(numbers_text) if QWEN35 in models else {}
    moved = [(t, arm, v) for (name, t, arm), v in t8a.items()
             if name == G.model_name(QWEN35) and abs(v[1] - v[0]) >= 1.0]
    CALL35_NOTE = ("Qwen3.6-35B calling cells: main sweep alone. The 35B calling rate is quoted as both "
                   "runs, main sweep and delivered rerun (decided 2026-11-09, `STATUS.md`), and \"bigger "
                   "calls less\" stays a direction only; see S1-Q, T8a and T8c (call-state flips).")
    tracks = sorted(set(track.values()))
    n_ok = len(checks)
    n_num = sum(c.startswith("NUMBERS") for c in checks)
    n_t8a = sum(c.startswith("T8a") for c in checks)
    n_iss = sum(c.startswith("ISS-027") for c in checks)
    L += [f"*Generated by `tools/reanalysis/{TAG}`; do not edit between the markers, rerun the "
          f"script. Self-check: {n_ok} of {n_ok} pass ({n_num} pooled counts equal T1 and T2 "
          "above; every per-wording, per-track and per-domain count equals the committed "
          f"`tools/reanalysis/out/breakdowns_cost/*_{CORPUS}.csv` of `bc_per_wording.py` and "
          f"`bc_per_domain.py`; {n_t8a} 35B main-sweep calling rates equal the T8a calling "
          f"column; {n_iss} ISS-027 before/after rates follow from the pooled counts).*", ""]
    L += [f"**Apparatus: Study 1 only** (main sweep, `results/{CORPUS}`, think=off, the "
          "headline models; never pooled with a Study 2 table). **Mechanism layer only**: "
          "*unaided* = the no-tools cell's online grade (wordings v11–13); *calling* = "
          "`tool_selected` (the task's own tool was called); *tool-verified* = `success` on the "
          "tools cell. **Why no delivered tool-arm column**: the breakdowns of 2026-10-02 "
          "(`reference/reanalysis_breakdowns_cost.md`) also showed the overlay's delivered "
          "bounds for the tool arms; that surface is retired for the open models in Study 1 "
          "(Rules above), and on the main sweep many of those cells are wide censoring bounds "
          "set by the 500-character answer storage. The delivered surface on the fixed setup is "
          "in the Study 2 tables below. Intervals as in the Rules above (domain bootstrap 95%; "
          "† = Wilson at 0 or 100%); a track subset resamples only its own domains.", "",
          f"**Unaided simulate.** {QUAL_NOTE}", "",
          f"**Grader caveat.** {ISS027_NOTE}", "",
          f"**35B calling.** {CALL35_NOTE}", ""]

    # quote summary (values computed here)
    def by_word(m, t, arm, f):
        return " · ".join(f"{w} **{100 * W[(m, t, arm, w, f)][0] / W[(m, t, arm, w, f)][1]:.1f}** "
                          f"({W[(m, t, arm, w, f)][0]}/{W[(m, t, arm, w, f)][1]})" for w in words)
    g = "gemma4_26b-a4b"
    qrows = []
    if g in models and "validate_plan" in tasks:
        qrows.append(["Gemma validate_plan calling, plain, by wording (descriptive)",
                      by_word(g, "validate_plan", "plain", "called")
                      + "; pooled (T2) {:.1f}%, their mean (equal n)".format(
                          100 * res["pooled"][(g, "validate_plan", "plain", "called")][0]
                          / res["pooled"][(g, "validate_plan", "plain", "called")][1]),
                      "\"21%\" without its wording range; a single wording's rate as a test"])
    if "solve" in tasks:
        qrows.append(["unaided solve, by wording (descriptive)",
                      "; ".join(f"{G.model_name(m)} " + by_word(m, "solve", "unaided", "mech")
                                for m in models)
                      + "".join(f" (frozen grades; ISS-027 would add {d} {G.model_name(m)} trials "
                                "over the three wordings)" for m, t, arm, d in iss_moves
                                if t == "solve" and arm == "unaided"),
                      "the pooled unaided solve rate (T1) as if it did not depend on the wording"])
    if moved:
        qrows.append([f"{G.model_name(QWEN35)} calling, any cell of S1-W, S1-T or S1-D",
                      "no single-run figure. Quote both runs: "
                      + "; ".join(f"{t} {arm} **{v[0]:.1f}** (main sweep) and **{v[1]:.1f}** "
                                  f"(delivered rerun), Δ {v[2]}" for t, arm, v in moved)
                      + " (T8a; the trials that flip are in T8c). \"Bigger calls less\" is a "
                      "direction only (decided 2026-11-09, `STATUS.md`)",
                      "a 35B per-wording, per-track or per-domain calling rate from the main sweep "
                      "alone; the 9B-vs-35B size inversion as a measured effect"])
    if iss_moves:
        qrows.append(["success cells hit by ISS-027 (grader case fault)",
                      "the frozen value, with the ISS-027 caveat; corrected value beside it, post hoc: "
                      + iss_list,
                      "a re-graded value in place of the frozen one; the frozen value without the "
                      "caveat"])
    qrows.append(["unaided simulate cells (¶)",
                  "0.0 **format-exact on the shared-budget corpus**, always with that qualifier "
                  "(Job 2 row)", "a bare 0.0 or 0% read as a capability floor"])
    qrows.append(["tool-arm figures in these tables", "tool-verified and calling only",
                  "any Study 1 delivered tool-arm figure from `bc_per_wording.py` or "
                  "`bc_per_domain.py` (retired surface)"])
    L += ["#### S1-Q. What to quote from these tables", "",
          G.md_table(["figure", "**quote this**", "do NOT quote"], qrows), ""]

    # wording
    L += ["#### S1-W. Per wording: calling beside success (think=off)", "",
          "Wording w1 = plain v11 / steered v14 (v14 is v11 plus one sentence naming the tool), "
          "w2 = v12 / v15, w3 = v13 / v16; unaided uses the plain wording. ¶, ISS-027 and the "
          "35B calling cells: see the caveats above.", ""]
    rows = []
    for m in models:
        for t in tasks:
            for w in words:
                rows.append([G.model_name(m), t, w, W[(m, t, "plain", w, "mech")][1],
                             q(t, "unaided", W[(m, t, "unaided", w, "mech")][2]),
                             W[(m, t, "plain", w, "called")][2], W[(m, t, "plain", w, "mech")][2],
                             W[(m, t, "steered", w, "called")][2], W[(m, t, "steered", w, "mech")][2]])
    table("s1_per_wording", ["model", "task", "wording", "n", "unaided", "calling, plain",
                             "tool-verified, plain", "calling, steered", "tool-verified, steered"], rows,
          [QUAL_NOTE, ISS027_NOTE, CALL35_NOTE])

    L += ["Range over the three wordings, low–high (max − min, points):", ""]
    rows = []
    for m in models:
        for t in tasks:
            def rng(arm, f):
                xs = [100 * W[(m, t, arm, w, f)][0] / W[(m, t, arm, w, f)][1] for w in words]
                return f"{min(xs):.1f}–{max(xs):.1f} ({max(xs) - min(xs):.1f})"
            rows.append([G.model_name(m), t, q(t, "unaided", rng("unaided", "mech")),
                         rng("plain", "called"),
                         rng("plain", "mech"), rng("steered", "called"), rng("steered", "mech")])
    table("s1_per_wording_range", ["model", "task", "unaided", "calling, plain",
                                   "tool-verified, plain", "calling, steered",
                                   "tool-verified, steered"], rows,
          [QUAL_NOTE, ISS027_NOTE, CALL35_NOTE])

    # track
    T = res["track"]
    L += ["#### S1-T. Classical against numeric (think=off, pooled over wordings)", "",
          "Track = the top-level folder under `domains/` (the harness's own label; it picks the "
          "oracle planner). " + ", ".join(f"{tr}: {sum(v == tr for v in track.values())} domains"
                                          for tr in tracks) + ". ¶, ISS-027 and the 35B "
          "calling cells: see the caveats above.", ""]
    rows = []
    for m in models:
        for t in tasks:
            for tr in tracks:
                rows.append([G.model_name(m), t, tr, T[(m, t, "plain", tr, "mech")][1],
                             q(t, "unaided", T[(m, t, "unaided", tr, "mech")][2]),
                             T[(m, t, "plain", tr, "called")][2], T[(m, t, "plain", tr, "mech")][2],
                             T[(m, t, "steered", tr, "called")][2], T[(m, t, "steered", tr, "mech")][2]])
    table("s1_by_track", ["model", "task", "track", "n per arm", "unaided", "calling, plain",
                          "tool-verified, plain", "calling, steered", "tool-verified, steered"], rows,
          [QUAL_NOTE, ISS027_NOTE, CALL35_NOTE])

    # domain
    D = res["domain"]
    doms = sorted({k[3] for k in D}, key=lambda d: (track[d], d))
    nper = {t: sorted({v[1] for k, v in D.items() if k[1] == t}) for t in tasks}
    L += ["#### S1-D. Per domain (think=off, pooled over wordings)", "",
          "Rows per domain and arm: " + ", ".join(f"{t} {'/'.join(str(x) for x in nper[t])}"
                                                   for t in tasks)
          + ". Too few for single-domain claims; read for pattern. Counts and Wilson intervals: "
          f"`tools/reanalysis/out/breakdowns_cost/per_domain_{CORPUS}.csv` (its delivered "
          "columns are the retired surface).", "",
          "**Success %, unaided / tool-verified plain / tool-verified steered** (¶ and ISS-027: "
          "see the caveats above; the ISS-027 moves sit in the satellite and pogo_stick rows):", ""]

    def p(k, n):
        return "–" if not n else f"{100 * k / n:.0f}"
    rows = []
    for d in doms:
        for m in models:
            r_ = [d, track[d][:3], G.model_name(m)]
            for t in tasks:
                r_.append(" / ".join(q(t, a, p(*D[(m, t, a, d)][:2])) if (m, t, a, d) in D else "–"
                                     for a in ("unaided", "plain", "steered")))
            rows.append(r_)
    table("s1_per_domain_success", ["domain", "track", "model"] + tasks, rows,
          [QUAL_NOTE, ISS027_NOTE])
    L += ["**Calling %, plain / steered** (35B cells: see the caveats above):", ""]
    rows = []
    for d in doms:
        for m in models:
            r_ = [d, track[d][:3], G.model_name(m)]
            for t in tasks:
                r_.append(" / ".join(p(D[(m, t, a, d)][2], D[(m, t, a, d)][1])
                                     if (m, t, a, d) in D else "–" for a in ("plain", "steered")))
            rows.append(r_)
    table("s1_per_domain_calling", ["domain", "track", "model"] + tasks, rows, [CALL35_NOTE])

    if tex_dir is not None:
        tex_dir.mkdir(parents=True, exist_ok=True)
        for name, body in tex.items():
            (tex_dir / f"{name}.tex").write_text(body)
    return "\n".join(L).rstrip("\n") + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=common.RESULTS,
                    help="results root holding sweep5v2-live/ and derived/e2e_overlay/ (read-only)")
    ap.add_argument("--models", nargs="+", default=list(common.HEADLINE))
    ap.add_argument("--numbers", type=Path, default=common.REPO / "development/NUMBERS.md")
    ap.add_argument("--out-dir", type=Path, default=HERE / "out")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args(argv)
    common.RESULTS = args.results
    common.OVERLAY = args.results / "derived" / "e2e_overlay"
    try:
        cells = load(args.models)
        tasks = sorted({r["task"] for m in args.models for r in cells[m]["tools"]}, key=task_key)
        track = domain_track()
        res = compute(cells, args.models, tasks, track)
        numbers_text = args.numbers.read_text()
        checks = self_checks(res, numbers_text, args.out_dir / "breakdowns_cost", args.models, tasks)
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    print(f"self-check: {len(checks)} of {len(checks)} pass", file=sys.stderr)
    if args.check_only:
        return 0
    body = render(res, args.models, tasks, track, checks, args.out_dir / "tex", numbers_text)
    (args.out_dir / "s1_breakdowns.md").write_text(body)
    changed = G.write_numbers(args.numbers, TAG, body)
    print(f"wrote {args.out_dir}/s1_breakdowns.md, {args.out_dir}/tex/s1_*.tex; "
          f"NUMBERS.md {'updated' if changed else 'unchanged'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
