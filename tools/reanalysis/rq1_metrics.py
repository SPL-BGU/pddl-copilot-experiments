#!/usr/bin/env python3
"""RQ1 metrics: do PDDL tools help an LLM do planning-related tasks?

    python -m tools.reanalysis.rq1_metrics [--numbers]

Post hoc and descriptive (development/roadmap.md, milestone M2). Read-only over
results/. Nothing here is a registered endpoint: the frozen readout of the
delivered rerun stays the record, and every table below is exploratory.

The four metrics the advisors asked for (2026-11-22), each on the DELIVERED
final answer, with and without tools:

  1. validate_plan: false positives (a broken plan accepted) and false
     negatives (a valid plan rejected). A trial with no readable verdict is
     its own column, not an error of either kind.
  2. simulate: share of states that are right, against the trace length.
     Two scores per trial: "exact" (the whole trace equals the oracle: the
     frozen grade) and "states" (share of the oracle's states that the answer
     has right at the same position; state = the true predicates and the
     numeric values, the step number and action label are not compared).
     Many answers are cut off mid-trace and so are not readable JSON; the
     frozen grader reads nothing from them. A third score, "states,
     salvaged", also reads the complete leading steps of such a cut-off
     trace (`salvage_steps`). It is more lenient than the frozen grader and
     is reported beside the strict score, never instead of it.
  3. solve: delivered success against the hardness of the problem. Hardness
     is the reference plan length, and the planner's own runtime (median
     `solve_time` of the planner calls the models made on that problem; the
     solver plugin returns it with every plan).
  4. solve: plan length of the valid delivered plans against the reference
     plan (the answer key's plan, found by the same planners with their
     default, any-plan settings; it is not a shortest plan).

Data. Open models: the delivered rerun only (full answers stored), loaded and
graded by the frozen package `tools/delivered_rerun` (hash 822aace...); the
script halts if the package, the ground-truth cache or the delivered counts of
the frozen readout do not match. The main sweep is never read here: it kept
the first 500 characters of each answer. Claude (Sonnet 4.6, Haiku 4.5): the
frontier runs, delivered validity taken from the e2e overlay (`e2e_strict`),
never pooled with the open models. Claude tables use wording v11 in both arms
(the only wording the Claude tool arm ran).

Simulate caveat (ISS-029): on a few problems the plan in the run's prompt was
not the cached plan the oracle trace belongs to. Those problems are detected
from the tool rows (the plan passed to `get_state_transition`) and left out of
metric 2; the list is printed.

Outputs (tools/reanalysis/out/): rq1_metrics.json, rq1_metrics.md; with
--numbers the markdown is spliced into development/NUMBERS.md (tag RQ1-METRICS).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats as sps

from pddl_eval.scoring import (_coerce_simulate_trajectory, _normalize_trajectory,
                               _safe_json_loads, strip_leaked_channel_prefix)
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.delivered_rerun.stats import cluster_bootstrap
from tools.e2e_regrade import oracle_canon_for, simulate_candidates, truth_for
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
FROZEN_SHA = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"
TAG = "RQ1-METRICS"
LEN_BINS = ((1, 5), (6, 10), (11, 20), (21, 40), (41, 10_000))
PLANNERS = ("classic_planner", "numeric_planner")
FRONTIER = {  # paper name -> (unaided corpus, tool corpus)
    "Claude Sonnet 4.6": ("sonnet-frontier/sweep5v2", "sonnet-frontier/sweep5v2-with-tools"),
    "Claude Haiku 4.5": ("haiku-frontier/sweep5v2", "haiku-frontier/sweep5v2-with-tools"),
}
FRONTIER_VARIANT = 11
OBJ_BINS = ("fewest objects", "middle third", "most objects")
SIM_PLAN_AGREEMENT = 0.9   # share of tool rows that must pass one same plan (as ISS-029)
ARM_NAMES = {"none": "no tools", "plain": "tools, plain", "steered": "tools, steered",
             "tools": "tools"}


class Halt(Exception):
    pass


# ------------------------------------------------------------------ pure helpers
def bin_of(n: int, bins=LEN_BINS) -> str:
    for lo, hi in bins:
        if lo <= n <= hi:
            return f"{lo}–{hi}" if hi < 10_000 else f"{lo}+"
    raise ValueError(f"length {n} is in no bin")


def bin_labels(bins=LEN_BINS) -> list[str]:
    return [f"{lo}–{hi}" if hi < 10_000 else f"{lo}+" for lo, hi in bins]


def state_of(step: dict) -> tuple:
    """The comparable state of one normalised step: true predicates and numeric
    values. The step number and the action label are left out on purpose."""
    return (tuple(step.get("boolean") or ()), tuple(sorted((step.get("numeric") or {}).items())))


def state_score(model: list[dict] | None, oracle: list[dict]) -> dict:
    """Per-state score of one answer against the oracle trace (both normalised).

    matched: oracle positions where the answer has the same state.
    prefix:  number of leading positions that are right (stops at the first
             wrong or missing state).
    A missing answer scores 0 on both."""
    n = len(oracle)
    if not model:
        return {"n_states": n, "matched": 0, "prefix": 0, "answer_states": 0}
    same = [i < len(model) and state_of(model[i]) == state_of(oracle[i]) for i in range(n)]
    prefix = next((i for i, ok in enumerate(same) if not ok), n)
    return {"n_states": n, "matched": sum(same), "prefix": prefix, "answer_states": len(model)}


def salvage_steps(response: str) -> list[dict] | None:
    """The complete leading steps of a trace that was cut off mid-JSON.

    Finds the first `[` (after a `"trajectory"` key when there is one), then
    decodes one JSON object after another until one fails. The decoded steps
    go through the same coercion as a whole answer
    (`_coerce_simulate_trajectory`), so a malformed step still yields nothing.
    Returns None when no complete step can be read."""
    text = strip_leaked_channel_prefix(response or "")
    start = text.find('"trajectory"')
    start = text.find("[", start if start >= 0 else 0)
    if start < 0:
        return None
    dec, i, objs = json.JSONDecoder(), start + 1, []
    while True:
        while i < len(text) and text[i] in " \t\r\n,":
            i += 1
        if i >= len(text) or text[i] != "{":
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            break
        objs.append(obj)
    if not objs:
        return None
    steps, _compliant = _coerce_simulate_trajectory(json.dumps(objs))
    return steps


def best_state_score(response: str, oracle: list[dict]) -> dict:
    """Score every trajectory candidate the frozen grader would read
    (`simulate_candidates`) and keep the one with most matched states (ties:
    the longer correct prefix). No candidate: the zero score.

    Extra fields: `salvaged_matched` (the same score when, for an answer with
    no readable trace, the complete leading steps of a cut-off trace are read
    too; equal to `matched` otherwise), `salvaged` (that happened), and
    `shift_gain` (moving the answer by one position would match more states)."""
    best = state_score(None, oracle)
    best["parsed"] = False
    cands = []
    for steps, _mode in simulate_candidates(response):
        canon = _normalize_trajectory(steps)
        if canon is None:
            continue
        cands.append(canon)
        s = state_score(canon, oracle)
        s["parsed"] = True
        if not best["parsed"] or (s["matched"], s["prefix"]) > (best["matched"], best["prefix"]):
            best = s
    best["shift_gain"] = any(
        state_score(shifted, oracle)["matched"] > best["matched"]
        for c in cands for shifted in (c[1:], [{}] + c))
    best["salvaged"], best["salvaged_matched"] = False, best["matched"]
    if not best["parsed"]:
        canon = _normalize_trajectory(salvage_steps(response))
        if canon:
            best["salvaged"] = True
            best["salvaged_matched"] = state_score(canon, oracle)["matched"]
    return best


def confusion(truths: list[bool], verdicts: list[bool | None]) -> dict:
    """Counts for one cell. FP = broken plan accepted, FN = valid plan rejected."""
    c = Counter()
    for t, v in zip(truths, verdicts):
        kind = "valid" if t else "broken"
        said = "none" if v is None else ("accept" if v else "reject")
        c[(kind, said)] += 1
    n_v = sum(c[("valid", s)] for s in ("accept", "reject", "none"))
    n_b = sum(c[("broken", s)] for s in ("accept", "reject", "none"))
    return {"n_valid": n_v, "n_broken": n_b,
            "fn": c[("valid", "reject")], "valid_none": c[("valid", "none")],
            "fp": c[("broken", "accept")], "broken_none": c[("broken", "none")]}


def count_objects(problem_text: str) -> int | None:
    """Objects declared in a problem's `(:objects ...)` block: `o1 o2 - type o3`
    counts o1, o2 and o3 (the token after each `-` is a type). Comments are
    dropped first. None when there is no such block. Same rule as the
    analyzer's `gen_meta.obj_count`."""
    text = re.sub(r";[^\n]*", "", problem_text)
    m = re.search(r"\(:objects\b([^()]*)\)", text, re.IGNORECASE)
    if m is None:
        return None
    count, expect_type = 0, False
    for tok in m.group(1).split():
        if tok == "-":
            expect_type = True
        elif expect_type:
            expect_type = False
        else:
            count += 1
    return count


def tercile_namer(values: list[float], names=("low third", "middle third", "high third")):
    """A function that names the third a value falls in (cuts at the 1/3 and
    2/3 quantiles of `values`), and the two cuts."""
    cuts = [float(np.quantile(sorted(values), q)) for q in (1 / 3, 2 / 3)] if values else []

    def name(v):
        if v is None or not cuts:
            return None
        return names[0] if v <= cuts[0] else (names[1] if v <= cuts[1] else names[2])
    return name, cuts


def norm_action(a: str) -> str:
    return " ".join(str(a).replace("(", " ").replace(")", " ").lower().split())


def plan_argument(plan) -> tuple[str, ...] | None:
    """The plan a model passed to `get_state_transition`, as normalised actions.
    Models pass a JSON list (with or without parentheses) or plain lines."""
    if isinstance(plan, str):
        parsed = _safe_json_loads(plan)
        plan = parsed if isinstance(parsed, list) else [ln for ln in plan.splitlines() if ln.strip()]
    if not isinstance(plan, list) or not plan:
        return None
    out = tuple(norm_action(a) for a in plan if isinstance(a, str) and norm_action(a))
    return out or None


def boot(values, clusters) -> dict:
    """Frozen domain-cluster bootstrap (95%); k is whatever this subset holds."""
    if not values:
        return {"est": None, "lo": None, "hi": None, "k": 0, "n": 0}
    b = cluster_bootstrap([float(v) for v in values], list(clusters), 0.95, len(set(clusters)))
    return {"est": b.est, "lo": b.lo, "hi": b.hi, "k": b.k, "n": b.n}


def cell(b: dict) -> str:
    if b["est"] is None:
        return "–"
    return f"{b['est']:.1f} [{b['lo']:.1f}, {b['hi']:.1f}]"


def diff_cell(b: dict) -> str:
    if b["est"] is None:
        return "–"
    return f"{b['est']:+.1f} [{b['lo']:+.1f}, {b['hi']:+.1f}]"


def spearman(xs, ys) -> dict:
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return {"rho": None, "p": None, "n": len(xs)}
    r = sps.spearmanr(xs, ys)
    return {"rho": float(r.statistic), "p": float(r.pvalue), "n": len(xs)}


def rho_cell(s: dict) -> str:
    return "–" if s["rho"] is None else f"{s['rho']:+.2f} (p={s['p']:.3f})"


# ------------------------------------------------------------------ records
def rec(model, arm, task, domain, problem, plan_label, variant, ok, verdict, plan, response,
        tool_calls) -> dict:
    return {"model": model, "arm": arm, "task": task, "domain": domain, "problem": problem,
            "plan_label": plan_label, "variant": variant, "ok": ok, "verdict": verdict,
            "plan": plan, "response": response, "tool_calls": tool_calls}


def load_rerun_cells(args) -> tuple[dict, dict, dict]:
    """The delivered rerun through the frozen package: (cells, grades, gt_cache).

    `cells` is `run.load_all` (rerun_a = tools, rerun_b = Gemma neutral prompt,
    rerun_c = no tools); `grades` maps (cell name, trial key) to the frozen
    delivered grade of every rerun row. Halts unless the package hash, the
    pinned ground-truth cache and the readout's E1 and E2 delivered counts all
    reproduce."""
    if RUN.package_sha256() != FROZEN_SHA:
        raise Halt("the frozen package tools/delivered_rerun changed (hash is not 822aace...)")
    RUN.check_domains(args.domains_dir)
    from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash
    gt_cache = json.loads(args.gt_cache.read_text())
    if canonical_hash(gt_cache) != PREREG_PINNED_HASH:
        raise Halt("ground-truth cache does not match the pinned canonical hash")
    design = C.REGISTERED
    C.assert_registered(design)
    cells = RUN.load_all(design, args.rerun_root, args.canonical_root)
    rerun_a, rerun_b, rerun_c = cells["rerun_a"], cells["rerun_b"], cells["rerun_c"]
    rows = ([r for lc in rerun_a.values() for r in lc.rows] + list(rerun_b.rows)
            + [r for lc in rerun_c.values() for r in lc.rows])
    need = G.solve_plans_to_validate(rows)
    table = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
             for e in json.loads(args.plan_verdicts.read_text())}
    missing = need - set(table)
    if missing:
        raise Halt(f"{len(missing)} delivered solve plans have no cached validator verdict in "
                   f"{args.plan_verdicts}; run tools/delivered_rerun_secondary.py first")
    grades = {(r.cell, r.trial_key): G.grade(r, gt_cache, table) for r in rows}

    readout = json.loads(args.readout_json.read_text())
    if readout.get("package_sha256") != FROZEN_SHA:
        raise Halt("--readout-json is not the frozen live readout")
    bad = []
    for e in readout["e1"]:
        rs = [r for r in rerun_a[e["model"]].rows if r.task == e["task"] and r.arm == e["arm"]]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        if (k, len(rs)) != (e["delivered_k"], e["n"]):
            bad.append(f"E1 {e['model']}/{e['task']}/{e['arm']}: {k}/{len(rs)} vs "
                       f"{e['delivered_k']}/{e['n']}")
    for e in readout["e2"]:
        rs = [r for r in rerun_c[e["model"]].rows if r.task == e["task"]]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        if abs(100 * k / len(rs) - e["a_pct"]) > 1e-9:
            bad.append(f"E2 no-tools {e['model']}/{e['task']}: {100 * k / len(rs):.4f} vs "
                       f"{e['a_pct']:.4f}")
    if bad:
        raise Halt("grades do not reproduce the frozen readout:\n  " + "\n  ".join(bad))
    return cells, grades, gt_cache


def load_rerun(args) -> tuple[list[dict], dict]:
    cells, grades, gt_cache = load_rerun_cells(args)
    out = []
    for part, cellmap in (("A", cells["rerun_a"]), ("C", cells["rerun_c"])):
        for m, lc in cellmap.items():
            for r in lc.rows:
                g = grades[(r.cell, r.trial_key)]
                out.append(rec(model_name(m), "none" if part == "C" else r.arm, r.task, r.domain,
                               r.problem, r.plan_label, r.variant, bool(g.ok), g.verdict,
                               g.plan, r.response,
                               [(c.name, c.arguments, c.result) for c in r.tool_calls]))
    return out, gt_cache


def read_trials(fp: Path) -> dict[tuple, dict]:
    out = {}
    with fp.open() as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except json.JSONDecodeError:
                continue
            out[tuple(d["key"])] = d["result"]
    return out


def load_frontier(args) -> tuple[list[dict], dict]:
    """Claude rows, wording v11. Delivered validity = overlay `e2e_strict`
    (tri-state); the verdict and the plan are read from the stored answer with
    the same extractors the rerun grader uses. Self-check: on validate_plan the
    extracted verdict must agree with the overlay on every determinate row."""
    out, notes = [], {}
    for name, corpora in FRONTIER.items():
        for arm, corpus in zip(("none", "tools"), corpora):
            trials = read_trials(args.results / corpus / "trials.jsonl")
            ov = {}
            with (args.results / "derived" / "e2e_overlay" / f"{corpus}.e2e.jsonl").open() as fh:
                for ln in fh:
                    if ln.strip():
                        o = json.loads(ln)
                        ov[tuple(o["trial_key"])] = o
            n_ind = n_bad = n = 0
            for key, res in trials.items():
                if int(key[5]) != FRONTIER_VARIANT or res.get("infra_failure"):
                    continue
                o = ov.get(key)
                if o is None:
                    raise Halt(f"{corpus}: trial {key} has no overlay row")
                es = o["e2e_strict"]
                task = res["task"]
                resp = res.get("response") or ""
                verdict = plan = None
                if task in G.VALIDATE_TASKS:
                    verdict = G.stated_verdict(resp) if resp.strip() else None
                    truth = truth_for({"task": task, "problem_name": res["problem_name"],
                                       "plan_label": res.get("plan_label") or ""})
                    if es in (True, False) and (verdict is not None and verdict == truth) != es:
                        n_bad += 1
                elif task == "solve" and resp.strip():
                    plan, _mode = G.solve_plan(resp)
                n += 1
                n_ind += es not in (True, False)
                out.append(rec(name, arm, task, res["domain_name"], res["problem_name"],
                               res.get("plan_label") or "", int(key[5]),
                               None if es not in (True, False) else bool(es), verdict, plan,
                               resp, [(c.get("name"), c.get("arguments"), c.get("result"))
                                      for c in (res.get("tool_calls") or [])]))
            notes[f"{name} / {ARM_NAMES[arm]}"] = {"rows": n, "indeterminate": n_ind,
                                                   "verdict_disagrees_with_overlay": n_bad}
            if n_bad:
                raise Halt(f"{corpus}: {n_bad} validate rows where the extracted verdict "
                           "disagrees with the overlay's delivered grade")
    return out, notes


# ------------------------------------------------------------------ hardness
def problem_facts(rows: list[dict], gt_cache: dict, domains_dir: Path | None = None) -> dict:
    """Per solve/simulate problem: reference plan length, oracle trace length,
    planner runtime (median solve_time over the planner calls that returned a
    plan), and whether the run's simulate plan differs from the cached one."""
    times = defaultdict(list)
    sim_plans = defaultdict(Counter)
    for r in rows:
        for name, arguments, result in r["tool_calls"]:
            if r["task"] == "solve" and name in PLANNERS:
                d = _safe_json_loads(result) if isinstance(result, str) else result
                if isinstance(d, dict) and d.get("plan") and "solve_time" in d:
                    times[(r["domain"], r["problem"])].append(float(d["solve_time"]))
            if r["task"] == "simulate" and name == "get_state_transition":
                plan = plan_argument(arguments.get("plan") if isinstance(arguments, dict) else None)
                if plan:
                    sim_plans[(r["domain"], r["problem"])][plan] += 1
                break
    objects = {}
    if domains_dir is not None:
        for fp in domains_dir.glob("*/*/p[0-9]*.pddl"):
            objects[(fp.parent.name, fp.stem)] = count_objects(fp.read_text())
    facts = {}
    for d, probs in gt_cache.items():
        for p, e in probs.items():
            if not (isinstance(e, dict) and e.get("plan")):
                continue
            oracle = oracle_canon_for(gt_cache, {"domain_name": d, "problem_name": p})
            ref = tuple(norm_action(a) for a in e["plan"])
            seen = sim_plans.get((d, p))
            run_plan, undetermined = None, False
            if seen:
                top, k = seen.most_common(1)[0]
                if k >= SIM_PLAN_AGREEMENT * sum(seen.values()):
                    run_plan = top
                else:
                    undetermined = True
            ts = times.get((d, p), [])
            facts[(d, p)] = {
                "ref_len": len(e["plan"]),
                "objects": objects.get((d, p)),
                "trace_actions": (len(oracle) - 1) if oracle else None,
                "planner_time": statistics.median(ts) if ts else None,
                "planner_calls": len(ts),
                "sim_plan_differs": run_plan is not None and run_plan != ref,
                "sim_plan_undetermined": undetermined,
            }
    return facts


# ------------------------------------------------------------------ metrics
def groups(rows: list[dict], task: str):
    by = defaultdict(list)
    for r in rows:
        if r["task"] == task:
            by[(r["model"], r["arm"])].append(r)
    order = {"none": 0, "plain": 1, "steered": 2, "tools": 1}
    return sorted(by.items(), key=lambda kv: (kv[0][0], order[kv[0][1]]))


def metric1(rows: list[dict]) -> dict:
    cells, by_label, contrasts = [], [], []
    for (m, arm), rs in groups(rows, "validate_plan"):
        truths = [r["plan_label"].startswith("v") for r in rs]
        c = confusion(truths, [r["verdict"] for r in rs])
        valid = [r for r, t in zip(rs, truths) if t]
        broken = [r for r, t in zip(rs, truths) if not t]
        c.update(model=m, arm=arm,
                 fn_rate=boot([r["verdict"] is False for r in valid], [r["domain"] for r in valid]),
                 fp_rate=boot([r["verdict"] is True for r in broken], [r["domain"] for r in broken]),
                 correct=boot([r["ok"] is True for r in rs], [r["domain"] for r in rs]))
        cells.append(c)
        for lab in sorted({r["plan_label"] for r in broken}):
            sub = [r for r in broken if r["plan_label"] == lab]
            by_label.append({"model": m, "arm": arm, "label": lab, "n": len(sub),
                             "fp": sum(r["verdict"] is True for r in sub)})
    # paired: tools minus no tools on the same plan and wording (plain arm only)
    idx = defaultdict(dict)
    for r in rows:
        if r["task"] == "validate_plan":
            idx[(r["model"], r["arm"])][(r["domain"], r["problem"], r["plan_label"],
                                         r["variant"])] = r
    for m in sorted({k[0] for k in idx}):
        tool_arm = "plain" if (m, "plain") in idx else "tools"
        a, b = idx.get((m, "none"), {}), idx.get((m, tool_arm), {})
        for kind, err in (("valid", False), ("broken", True)):
            keys = [k for k in a if k in b and k[2].startswith("v") == (kind == "valid")]
            d = [(b[k]["verdict"] is err) - (a[k]["verdict"] is err) for k in keys]
            contrasts.append({"model": m, "tool_arm": tool_arm,
                              "error": "FN" if kind == "valid" else "FP", "n_pairs": len(keys),
                              "delta": boot(d, [k[0] for k in keys])})
    return {"cells": cells, "by_label": by_label, "contrasts": contrasts}


def metric2(rows: list[dict], gt_cache: dict, facts: dict) -> dict:
    skipped = sorted(f"{d}/{p}" for (d, p), f in facts.items() if f["sim_plan_differs"])
    undetermined = sorted(f"{d}/{p}" for (d, p), f in facts.items()
                          if f["sim_plan_undetermined"])
    cells, overall = [], []
    for (m, arm), rs in groups(rows, "simulate"):
        scored = []
        for r in rs:
            f = facts[(r["domain"], r["problem"])]
            if f["sim_plan_differs"]:
                continue
            oracle = oracle_canon_for(gt_cache, {"domain_name": r["domain"],
                                                 "problem_name": r["problem"]})
            s = best_state_score(r["response"], oracle)
            if r["ok"] is True and s["matched"] != s["n_states"]:
                raise Halt(f"simulate {m}/{arm}/{r['domain']}/{r['problem']}: graded exact "
                           f"but only {s['matched']} of {s['n_states']} states match")
            scored.append((r, f["trace_actions"], s))

        def summarise(sub):
            dom = [r["domain"] for r, _, _ in sub]
            return {"n": len(sub),
                    "exact_known": sum(r["ok"] is not None for r, _, _ in sub),
                    "exact": boot([r["ok"] is True for r, _, _ in sub], dom),
                    "states": boot([s["matched"] / s["n_states"] for _, _, s in sub], dom),
                    "states_salvaged": boot([s["salvaged_matched"] / s["n_states"]
                                             for _, _, s in sub], dom),
                    "prefix": boot([s["prefix"] / s["n_states"] for _, _, s in sub], dom),
                    "no_trace": sum(not s["parsed"] for _, _, s in sub),
                    "salvaged": sum(s["salvaged"] for _, _, s in sub),
                    "shift_gain": sum(s["shift_gain"] for _, _, s in sub),
                    "partly_right": sum(s["parsed"] and s["matched"] != s["n_states"]
                                        for _, _, s in sub)}
        o = summarise(scored)
        o.update(model=m, arm=arm,
                 rho_states=spearman([n for _, n, _ in scored],
                                     [s["matched"] / s["n_states"] for _, _, s in scored]))
        overall.append(o)
        for lab in bin_labels():
            sub = [x for x in scored if bin_of(x[1]) == lab]
            if sub:
                c = summarise(sub)
                c.update(model=m, arm=arm, bin=lab)
                cells.append(c)
    return {"skipped_problems": skipped, "undetermined_problems": undetermined,
            "overall": overall, "cells": cells}


def metric3(rows: list[dict], facts: dict) -> dict:
    solve = [r for r in rows if r["task"] == "solve"]
    tvals = sorted(f["planner_time"] for f in facts.values() if f["planner_time"] is not None)
    tbin, cuts = tercile_namer(tvals, ("fast third", "middle third", "slow third"))
    ovals = sorted(f["objects"] for f in facts.values())
    obin, ocuts = tercile_namer(ovals, OBJ_BINS)
    cells_len, cells_time, cells_obj, corr = [], [], [], []
    for (m, arm), rs in groups(solve, "solve"):
        for lab in bin_labels():
            sub = [r for r in rs if bin_of(facts[(r["domain"], r["problem"])]["ref_len"]) == lab]
            if sub:
                cells_len.append({"model": m, "arm": arm, "bin": lab, "n": len(sub),
                                  "problems": len({(r["domain"], r["problem"]) for r in sub}),
                                  "solved": boot([r["ok"] is True for r in sub],
                                                 [r["domain"] for r in sub])})
        for lab in ("fast third", "middle third", "slow third"):
            sub = [r for r in rs if tbin(facts[(r["domain"], r["problem"])]["planner_time"]) == lab]
            if sub:
                cells_time.append({"model": m, "arm": arm, "bin": lab, "n": len(sub),
                                   "problems": len({(r["domain"], r["problem"]) for r in sub}),
                                   "solved": boot([r["ok"] is True for r in sub],
                                                  [r["domain"] for r in sub])})
        for lab in OBJ_BINS:
            sub = [r for r in rs if obin(facts[(r["domain"], r["problem"])]["objects"]) == lab]
            if sub:
                cells_obj.append({"model": m, "arm": arm, "bin": lab, "n": len(sub),
                                  "problems": len({(r["domain"], r["problem"]) for r in sub}),
                                  "solved": boot([r["ok"] is True for r in sub],
                                                 [r["domain"] for r in sub])})
        per = defaultdict(list)
        for r in rs:
            per[(r["domain"], r["problem"])].append(r["ok"] is True)
        keys = sorted(per)
        share = [sum(per[k]) / len(per[k]) for k in keys]
        tk = [k for k in keys if facts[k]["planner_time"] is not None]
        corr.append({"model": m, "arm": arm, "problems": len(keys),
                     "solved": boot([r["ok"] is True for r in rs], [r["domain"] for r in rs]),
                     "rho_len": spearman([facts[k]["ref_len"] for k in keys], share),
                     "rho_obj": spearman([facts[k]["objects"] for k in keys], share),
                     "rho_time": spearman([facts[k]["planner_time"] for k in tk],
                                          [sum(per[k]) / len(per[k]) for k in tk])})
    hard = {"time_cuts_s": cuts, "problems_timed": len(tvals),
            "object_cuts": ocuts, "objects_min": ovals[0], "objects_max": ovals[-1],
            "rho_len_objects": spearman([f["ref_len"] for f in facts.values()],
                                        [f["objects"] for f in facts.values()]),
            "time_min_s": tvals[0] if tvals else None, "time_max_s": tvals[-1] if tvals else None,
            "rho_len_time": spearman(
                [f["ref_len"] for f in facts.values() if f["planner_time"] is not None],
                [f["planner_time"] for f in facts.values() if f["planner_time"] is not None])}
    return {"by_length": cells_len, "by_time": cells_time, "by_objects": cells_obj, "corr": corr,
            "hardness": hard}


def last_tool_plan(r: dict) -> tuple[list | None, str | None]:
    """The last non-empty plan a planner call returned in this trial, and the
    search strategy of that call ("default" when the model passed none)."""
    out = (None, None)
    for name, arguments, result in r["tool_calls"]:
        if name in PLANNERS:
            d = _safe_json_loads(result) if isinstance(result, str) else result
            if isinstance(d, dict) and d.get("plan"):
                strat = arguments.get("strategy") if isinstance(arguments, dict) else None
                out = (d["plan"], f"{name}:{strat or 'default'}")
    return out


def metric4(rows: list[dict], facts: dict) -> dict:
    cells = []
    for (m, arm), rs in groups(rows, "solve"):
        good = [r for r in rs if r["ok"] is True and r["plan"]]
        ref = [facts[(r["domain"], r["problem"])]["ref_len"] for r in good]
        got = [len(r["plan"]) for r in good]
        tool = [last_tool_plan(r) for r in good]
        with_tool = [(g, t) for g, (t, _s) in zip(got, tool) if t]
        long_strats = Counter(s for g, rf, (t, s) in zip(got, ref, tool) if t and g > rf)
        cells.append({
            "with_tool_plan": len(with_tool),
            "same_len_as_tool_plan": sum(g == len(t) for g, t in with_tool),
            "strategies": dict(Counter(s for t, s in tool if t)),
            "strategies_when_longer": dict(long_strats),
            "model": m, "arm": arm, "n_trials": len(rs), "n_valid": len(good),
            "mean_len": float(np.mean(got)) if got else None,
            "mean_ref_len": float(np.mean(ref)) if ref else None,
            "ratio_of_sums": (sum(got) / sum(ref)) if ref else None,
            "median_ratio": float(np.median([g / r for g, r in zip(got, ref)])) if ref else None,
            "shorter": sum(g < r for g, r in zip(got, ref)),
            "equal": sum(g == r for g, r in zip(got, ref)),
            "longer": sum(g > r for g, r in zip(got, ref)),
            "max_ratio": max((g / r for g, r in zip(got, ref)), default=None)})
    return {"cells": cells}


# ------------------------------------------------------------------ render
def f2(x) -> str:
    return "–" if x is None else f"{x:.2f}"


def render(res: dict) -> str:
    L = []
    w = L.append
    w("*Generated by `tools/reanalysis/rq1_metrics.py`. Post hoc and descriptive; delivered "
      "final answers only. Open models: the delivered rerun (thinking off; no tools = Part C, "
      "tools = Part A), graded by the frozen package. Claude: the frontier runs, wording v11, "
      "never pooled with the open models. Intervals are 95% domain-cluster bootstrap "
      "percentile intervals, in percent (or points for differences). The no-tools arm "
      "asks for its answer format in the prompt only (JSON on solve and simulate, a verdict "
      "line on the validation tasks); the JSON-schema constraint meant for that arm never "
      "took effect, so an unaided failure can be a failure of format as well as of "
      "content.*")
    w("")
    w("#### RQ1-1. validate_plan: false positives and false negatives")
    w("")
    w("FN = a valid plan rejected (share of valid plans). FP = a broken plan accepted (share "
      "of broken plans). \"No verdict\" = the final answer states no readable verdict; it is "
      "counted in neither rate.")
    w("")
    w(md_table(["model", "arm", "valid plans", "FN", "FN rate", "no verdict", "broken plans",
                "FP", "FP rate", "no verdict", "verdict right"],
               [[c["model"], ARM_NAMES[c["arm"]], c["n_valid"], c["fn"], cell(c["fn_rate"]),
                 c["valid_none"], c["n_broken"], c["fp"], cell(c["fp_rate"]), c["broken_none"],
                 cell(c["correct"])] for c in res["m1"]["cells"]]))
    w("")
    w("Paired change, tools minus no tools, on the same plan and wording (points; negative "
      "= fewer errors with tools):")
    w("")
    w(md_table(["model", "tool arm", "error", "pairs", "change"],
               [[c["model"], ARM_NAMES[c["tool_arm"]], c["error"], c["n_pairs"],
                 diff_cell(c["delta"])] for c in res["m1"]["contrasts"]]))
    w("")
    labs = sorted({c["label"] for c in res["m1"]["by_label"]})
    by = {(c["model"], c["arm"], c["label"]): c for c in res["m1"]["by_label"]}
    w("False positives by broken-plan label (accepted / shown):")
    w("")
    w(md_table(["model", "arm", *labs],
               [[m, ARM_NAMES[a], *[f"{by[(m, a, l)]['fp']}/{by[(m, a, l)]['n']}"
                                    if (m, a, l) in by else "–" for l in labs]]
                for m, a in dict.fromkeys((c["model"], c["arm"]) for c in res["m1"]["by_label"])]))
    w("")
    w("#### RQ1-2. simulate: share of states right, against trace length")
    w("")
    sk = res["m2"]["skipped_problems"]
    w(f"\"Exact\" = the whole trace equals the oracle (the frozen grade). \"States\" = mean "
      f"share of the oracle's states that the answer has right at the same position. "
      f"\"Prefix\" = mean share of the trace that is right before the first wrong state. "
      f"\"No trace\" = answers with no readable trace (they score 0 on all three). "
      f"\"States, salvaged\" = the same as \"states\", but for an answer cut off mid-trace "
      f"the complete leading steps are read too (\"salvaged\" counts those answers); it is "
      f"more lenient than the frozen grader. Trace length = number of actions. Left out (ISS-029, the run's plan is not the cached plan): "
      f"{', '.join(sk) if sk else 'none'}. Run plan undetermined (kept): "
      f"{', '.join(res['m2']['undetermined_problems']) or 'none'}.")
    w("")
    w(md_table(["model", "arm", "trials", "exact", "states", "prefix", "no trace",
                "states, salvaged", "salvaged", "Spearman, states vs length"],
               [[c["model"], ARM_NAMES[c["arm"]], c["n"], cell(c["exact"]) +
                 ("" if c["exact_known"] == c["n"] else f" ‡{c['n'] - c['exact_known']}"),
                 cell(c["states"]), cell(c["prefix"]), c["no_trace"],
                 cell(c["states_salvaged"]), c["salvaged"], rho_cell(c["rho_states"])]
                for c in res["m2"]["overall"]]))
    sg = sum(c["shift_gain"] for c in res["m2"]["overall"])
    pr = sum(c["partly_right"] for c in res["m2"]["overall"])
    w("")
    w(f"States are compared position by position. Moving the answer by one position would "
      f"match more states in {sg} of the {pr} readable answers that are not exact, so an "
      f"off-by-one trace is not what drives these scores.")
    w("")
    w("‡ n = Claude answers cut at the storage cap, exact grade unknown (counted as not exact "
      "here; their states are scored on what was stored).")
    w("")
    by = {(c["model"], c["arm"], c["bin"]): c for c in res["m2"]["cells"]}
    for what, title in (("states", "states"), ("states_salvaged", "states, salvaged"),
                        ("exact", "exact")):
        w(f"Mean share by trace length, \"{title}\" (trials in the bin):")
        w("")
        w(md_table(["model", "arm", *[f"{b} actions" for b in bin_labels()]],
                   [[m, ARM_NAMES[a], *[f"{cell(by[(m, a, b)][what])} ({by[(m, a, b)]['n']})"
                                        if (m, a, b) in by else "–" for b in bin_labels()]]
                    for m, a in dict.fromkeys((c["model"], c["arm"])
                                              for c in res["m2"]["cells"])]))
        w("")
    w("#### RQ1-3. solve: delivered success against problem hardness")
    w("")
    h = res["m3"]["hardness"]
    w(f"Hardness 1: reference plan length (actions). Hardness 2: the planner's own runtime, "
      f"the median `solve_time` over the planner calls the rerun models made on the problem "
      f"({h['problems_timed']} problems timed, {f2(h['time_min_s'])} s to "
      f"{f2(h['time_max_s'])} s; thirds cut at {f2(h['time_cuts_s'][0])} s and "
      f"{f2(h['time_cuts_s'][1])} s). Plan length and planner runtime: Spearman "
      f"{rho_cell(h['rho_len_time'])}. Second view: the number of objects in the problem "
      f"({h['objects_min']} to {h['objects_max']}; thirds cut at {h['object_cuts'][0]:.0f} and "
      f"{h['object_cuts'][1]:.0f}); plan length and object count: Spearman "
      f"{rho_cell(h['rho_len_objects'])}. The planner solves every problem in this corpus, "
      f"so the hard end, where the planner itself fails, is not covered.")
    w("")
    w(md_table(["model", "arm", "solved", "Spearman, solved vs plan length",
                "Spearman, solved vs planner runtime", "Spearman, solved vs object count"],
               [[c["model"], ARM_NAMES[c["arm"]], cell(c["solved"]), rho_cell(c["rho_len"]),
                 rho_cell(c["rho_time"]), rho_cell(c["rho_obj"])] for c in res["m3"]["corr"]]))
    w("")
    for key, title, labs in (("by_length", "reference plan length", bin_labels()),
                             ("by_time", "planner runtime",
                              ["fast third", "middle third", "slow third"]),
                             ("by_objects", "number of objects", list(OBJ_BINS))):
        by = {(c["model"], c["arm"], c["bin"]): c for c in res["m3"][key]}
        w(f"Solved, by {title} (trials in the bin):")
        w("")
        w(md_table(["model", "arm", *labs],
                   [[m, ARM_NAMES[a], *[f"{cell(by[(m, a, b)]['solved'])} ({by[(m, a, b)]['n']})"
                                        if (m, a, b) in by else "–" for b in labs]]
                    for m, a in dict.fromkeys((c["model"], c["arm"]) for c in res["m3"][key])]))
        w("")
    w("#### RQ1-4. solve: length of the valid delivered plans")
    w("")
    w("Only trials whose delivered plan is valid. Reference = the answer key's plan for the "
      "same problem (the planners' default any-plan search, not a shortest plan). Ratio of "
      "sums = total delivered actions / total reference actions over those trials.")
    w("")
    w(md_table(["model", "arm", "valid plans / trials", "mean length", "mean reference length",
                "ratio of sums", "median ratio", "shorter", "equal", "longer", "largest ratio",
                "same length as the tool's plan"],
               [[c["model"], ARM_NAMES[c["arm"]], f"{c['n_valid']}/{c['n_trials']}",
                 f2(c["mean_len"]), f2(c["mean_ref_len"]), f2(c["ratio_of_sums"]),
                 f2(c["median_ratio"]), c["shorter"], c["equal"], c["longer"],
                 f2(c["max_ratio"]),
                 f"{c['same_len_as_tool_plan']}/{c['with_tool_plan']}" if c["with_tool_plan"]
                 else "–"] for c in res["m4"]["cells"]]))
    w("")
    w("\"Same length as the tool's plan\" = of the valid delivered plans in a trial where a "
      "planner call returned a plan, how many have that plan's length. The planner's plan "
      "can be much longer than the reference when the model picks another search strategy "
      "or the search takes another path; planner calls behind the valid plans, by strategy "
      "(all / those longer than the reference):")
    w("")
    w(md_table(["model", "arm", "planner calls by strategy", "of which longer than reference"],
               [[c["model"], ARM_NAMES[c["arm"]],
                 ", ".join(f"{k} {v}" for k, v in sorted(c["strategies"].items())) or "–",
                 ", ".join(f"{k} {v}" for k, v in sorted(c["strategies_when_longer"].items()))
                 or "–"] for c in res["m4"]["cells"] if c["arm"] != "none"]))
    w("")
    w("Claude rows read: " + "; ".join(
        f"{k}: {v['rows']} rows, {v['indeterminate']} with an unknown delivered grade"
        for k, v in res["frontier_notes"].items()) + ".")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def add_data_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--results", type=Path, default=REPO / "results")
    ap.add_argument("--rerun-root", type=Path)
    ap.add_argument("--canonical-root", type=Path)
    ap.add_argument("--gt-cache", type=Path)
    ap.add_argument("--plan-verdicts", type=Path)
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--readout-json", type=Path,
                    default=REPO / "development/reference/delivered_rerun_readout.json")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "out")
    ap.add_argument("--numbers", action="store_true",
                    help="splice the tables into development/NUMBERS.md")


def fill_data_args(args) -> None:
    args.rerun_root = args.rerun_root or args.results / "delivered-rerun"
    args.canonical_root = args.canonical_root or args.results / "sweep5v2-live"
    args.gt_cache = args.gt_cache or args.results / "derived" / "gt_cache.json"
    args.plan_verdicts = (args.plan_verdicts
                          or args.results / "delivered-rerun-secondary" / "plan_verdicts.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_data_args(ap)
    args = ap.parse_args(argv)
    fill_data_args(args)
    try:
        rerun, gt_cache = load_rerun(args)
        frontier, notes = load_frontier(args)
        facts = problem_facts(rerun, gt_cache, args.domains_dir)
        if any(f["objects"] is None for f in facts.values()):
            raise Halt("a solvable problem has no readable (:objects ...) block")
        rows = rerun + frontier
        res = {"frozen_package_sha256": FROZEN_SHA, "frontier_notes": notes,
               "m1": metric1(rows), "m2": metric2(rows, gt_cache, facts),
               "m3": metric3(rows, facts), "m4": metric4(rows, facts),
               "problem_facts": {f"{d}/{p}": f for (d, p), f in sorted(facts.items())}}
    except (Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    md = render(res)
    (args.out / "rq1_metrics.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.out / "rq1_metrics.md").write_text(md)
    print(f"wrote {args.out}/rq1_metrics.{{json,md}}")
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
