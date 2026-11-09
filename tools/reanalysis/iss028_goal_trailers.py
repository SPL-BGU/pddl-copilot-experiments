#!/usr/bin/env python3
"""ISS-028: solve answers that copy the tool's plan and then list the goal facts.

    python3 tools/reanalysis/iss028_goal_trailers.py --results <results root> \\
        [--plan-verdicts <results>/delivered-rerun-secondary/plan_verdicts.json] \\
        [--marketplace ../pddl-copilot]

Read-only over results; post hoc and descriptive. The frozen readout
(`development/reference/delivered_rerun_readout.json`) stays the record.

What it does, in order (any failed check halts with a message, nothing written):

1. Loads the delivered rerun with the frozen loader (`tools.delivered_rerun.run
   .load_all`, package hash 822aace... checked) and grades every Part A (tool) and
   Part C (no tools) solve row with the frozen delivered grader (`grade.grade`).
   Plan verdicts come from the cached table when given, else from the
   pddl-validator plugin imported in process with pddl-pyvalidator 0.1.5 (the
   release the corpora were graded with), through the frozen
   `scoring._validate_model_plan`.
2. Self-check against the frozen readout: per model and arm, the E1 solve
   delivered count and reason counts, the Part C solve delivered count (from E2),
   and the E4 solve category and sub-label counts must all be equal.
3. Classifies each solve row the frozen `e4.classify` labels WRONG_FACTS with a
   fixed rule (`iss028_029_common.classify_wrong_facts`; first match wins):
     (a) goal_trailer: the extracted plan is the tool's last planner plan, action
         for action, then one or more extra lines, each a positive atom of the
         problem's goal (lower case, whitespace collapsed);
     (b) copy_error: as many actions as the tool's plan, at least one different;
     (c) other: anything else (C4 shape kept: extra lines before the plan, a
         trailer that is not all goal facts, a different length).
   Self-check: (a) + (b) + (c) equals the frozen WRONG_FACTS total. The C4 rule
   (PR #128: each extra line is a substring of the goal text) is run beside rule
   (a) and any difference is printed.
4. Post hoc extractor rule, every Part A and Part C solve row graded
   `plan_invalid`: drop the trailing run of goal atoms (`strip_goal_trailer`) and
   validate what is left. A row flips when that plan is valid. Delivered counts
   per cell are printed as frozen -> post hoc; the frozen figure is not replaced.
5. Frontier Haiku 4.5 (with tools, sweep5v2): lists the solve rows the e2e
   overlay grades `plan_invalid` (the "three transcription errors" of
   `paper/main.tex` and `reference/sonnet_wt_vs_haiku_e2e_memo.md`) and says
   whether depot p02 is one. When the raw trials file is present, each of those
   rows is also classified by the same rule.

Outputs (tools/reanalysis/out/): iss028_goal_trailers.json, .md, and the
NUMBERS.md block numbers_iss028.md (also printed to stdout).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import iss028_029_common as K  # noqa: E402

REPO = K.REPO
SRC = "`tools/reanalysis/iss028_goal_trailers.py`"
HAIKU_OVERLAY = "derived/e2e_overlay/haiku-frontier/sweep5v2-with-tools.e2e.jsonl"
HAIKU_RAW = "haiku-frontier/sweep5v2-with-tools/trials.jsonl"


def solve_rows(cells, C):
    a = [r for m in C.PART_A_MODELS for r in cells["rerun_a"][m].rows if r.task == "solve"]
    c = [r for m in C.PART_A_MODELS for r in cells["rerun_c"][m].rows if r.task == "solve"]
    return a, c


def check_readout(ro, rows_a, rows_c, grades, gt_cache, C, E4) -> dict:
    """The frozen readout's E1 / Part C / E4 solve figures, reproduced exactly."""
    bad, n_checks = [], 0
    for e in ro["e1"]:
        if e["task"] != "solve":
            continue
        rs = [r for r in rows_a if r.model_tag == e["model"] and r.arm == e["arm"]]
        g = [grades[(r.cell, r.trial_key)] for r in rs]
        got = (len(rs), sum(x.ok for x in g), dict(sorted(Counter(x.reason for x in g).items())))
        want = (e["n"], e["delivered_k"], e["reasons"])
        n_checks += 1
        if got != want:
            bad.append(f"E1 {e['model']}/{e['arm']}: {got} != {want}")
    for e in ro["e2"]:
        if e["task"] != "solve" or e["name"] != "E2":
            continue
        rs = [r for r in rows_c if r.model_tag == e["model"]]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        n_checks += 1
        if e["unpaired_a"] or len(rs) != e["n_pairs"] or abs(100 * k / len(rs) - e["a_pct"]) > 1e-9:
            bad.append(f"Part C {e['model']}: {k}/{len(rs)} != {e['a_pct']}%")
    for e in ro["e4"]:
        if e["task"] != "solve":
            continue
        rs = [r for r in rows_a if r.model_tag == e["model"] and r.arm == e["arm"]
              and r.success is True and grades[(r.cell, r.trial_key)].ok is False]
        cats, subs = Counter(), Counter()
        for r in rs:
            cat, sub = E4.classify(r, grades[(r.cell, r.trial_key)], gt_cache)
            cats[cat] += 1
            subs[f"{cat}: {sub}"] += 1
        n_checks += 1
        if ({c: cats[c] for c in E4.CATS} != e["categories"] or dict(sorted(subs.items())) != e["subs"]
                or len(rs) != e["n_gap"]):
            bad.append(f"E4 {e['model']}/{e['arm']}: {dict(cats)} != {e['categories']}")
    if bad:
        raise K.Halt("the frozen grades do not reproduce the readout:\n  " + "\n  ".join(bad))
    return {"checks": n_checks, "equal": n_checks}


def haiku_check(results: Path, domains: dict, verdict_fn) -> dict:
    """The frontier Haiku solve rows graded plan_invalid by the e2e overlay."""
    from tools.delivered_rerun import grade as G
    ov = results / HAIKU_OVERLAY
    if not ov.exists():
        return {"overlay": None, "note": f"{HAIKU_OVERLAY} not found"}
    rows = [json.loads(ln) for ln in ov.read_text().splitlines() if ln.strip()]
    solve = [r for r in rows if r["task"] == "solve"]
    reasons = Counter(r["e2e_reason"] for r in solve)
    invalid = sorted((r["domain_name"], r["problem_name"]) for r in solve
                     if r["e2e_reason"] == "plan_invalid")
    out = {"overlay": HAIKU_OVERLAY, "solve_rows": len(solve), "reasons": K.counter_dict(reasons),
           "plan_invalid": [f"{d} {p}" for d, p in invalid],
           "depot_p02_is_counted": ("depot", "p02") in invalid, "raw": None, "rows": []}
    raw = results / HAIKU_RAW
    if not raw.exists():
        out["note"] = (f"{HAIKU_RAW} not found: the shape of these rows is not checked "
                       "here, only their membership")
        return out
    out["raw"] = HAIKU_RAW
    from tools.delivered_rerun import e4 as E4
    for ln in raw.read_text().splitlines():
        if not ln.strip():
            continue
        res = json.loads(ln)["result"]
        if res["task"] != "solve" or not res["with_tools"] or \
                (res["domain_name"], res["problem_name"]) not in invalid:
            continue
        plan, mode = G.solve_plan(res["response"])
        ans = tuple(K.norm_action(a) for a in plan)
        tool = ()
        for tc in res["tool_calls"]:
            p = E4._safe_json_loads(tc.get("result"))
            if tc.get("name") in E4.PLANNERS and isinstance(p, dict) and \
                    isinstance(p.get("plan"), list) and p["plan"]:
                tool = tuple(K.norm_action(a) for a in p["plan"])
        d, pn = res["domain_name"], res["problem_name"]
        goals = K.goal_atoms(domains[d]["problems"][pn])
        cls, shape = K.classify_wrong_facts(tool, ans, goals)
        stripped = K.strip_goal_trailer(ans, goals)
        out["rows"].append({"domain": d, "problem": pn, "extraction": mode, "class": cls,
                            "shape": shape, "tool_len": len(tool), "answer_len": len(ans),
                            "extra": list(ans[len(tool):]) if cls == K.GOAL_TRAILER else None,
                            "stripped_valid": (verdict_fn({(d, pn, stripped)})[(d, pn, stripped)]
                                               if stripped else None)})
    return out


def analyse(args) -> dict:
    from pddl_eval.domains import load_domains
    from tools.delivered_rerun import constants as C
    from tools.delivered_rerun import e4 as E4
    from tools.delivered_rerun import grade as G

    ro = K.load_readout(args.readout)
    cells = K.load_frozen(args.results, args.domains_dir)
    domains = load_domains(args.domains_dir)
    rows_a, rows_c = solve_rows(cells, C)
    rows = rows_a + rows_c
    need = G.solve_plans_to_validate(rows)
    verdicts, src = K.plan_verdicts(need, args.plan_verdicts, args.marketplace, domains)
    # solve rows never read the ground-truth cache; E4 reads it for simulate only
    gt_cache: dict = {}
    grades = {(r.cell, r.trial_key): G.grade(r, gt_cache, verdicts) for r in rows}
    self_check = check_readout(ro, rows_a, rows_c, grades, gt_cache, C, E4)

    # --- classification of the E4 WRONG_FACTS solve rows
    frozen_wf = sum(e["categories"]["WRONG_FACTS"] for e in ro["e4"] if e["task"] == "solve")
    wf = []
    for r in rows_a:
        g = grades[(r.cell, r.trial_key)]
        if not (r.success is True and g.ok is False):
            continue
        if E4.classify(r, g, gt_cache)[0] != E4.WRONG_FACTS:
            continue
        tool = E4._last_tool_plan(r)
        ans = tuple(K.norm_action(a) for a in g.plan)
        ppddl = domains[r.domain]["problems"][r.problem]
        goals = K.goal_atoms(ppddl)
        cls, shape = K.classify_wrong_facts(tool, ans, goals)
        wf.append({"id": K.row_id(r), "model": r.model_tag, "arm": r.arm, "domain": r.domain,
                   "problem": r.problem, "class": cls, "shape": shape, "tool_len": len(tool),
                   "answer_len": len(ans), "c4_rule": K.c4_goal_rule(tool, ans, ppddl),
                   "extra": list(ans[len(tool):]) if cls == K.GOAL_TRAILER else None})
    by_class = Counter(x["class"] for x in wf)
    if sum(by_class.values()) != frozen_wf or len(wf) != frozen_wf:
        raise K.Halt(f"classes sum to {sum(by_class.values())}, the frozen WRONG_FACTS "
                     f"total is {frozen_wf}")
    c4_diff = [x["id"] for x in wf if x["c4_rule"] != (x["class"] == K.GOAL_TRAILER)]

    # --- post hoc: trailing goal atoms dropped, every plan_invalid solve row
    strip_need, stripped_of = set(), {}
    for r in rows:
        g = grades[(r.cell, r.trial_key)]
        if g.reason != "plan_invalid":
            continue
        s = K.strip_goal_trailer(tuple(g.plan), K.goal_atoms(domains[r.domain]["problems"][r.problem]))
        if s is not None:
            stripped_of[(r.cell, r.trial_key)] = s
            strip_need.add((r.domain, r.problem, s))
    sv, src2 = K.plan_verdicts(strip_need, args.plan_verdicts, args.marketplace, domains)
    verdicts.update(sv)
    flips = defaultdict(list)
    still_invalid = Counter()
    for r in rows:
        s = stripped_of.get((r.cell, r.trial_key))
        if s is None:
            continue
        part = "A" if r.with_tools else "C"
        cell = (part, r.model_tag, r.arm if r.with_tools else "unaided")
        if verdicts[(r.domain, r.problem, s)]:
            flips[cell].append(K.row_id(r))
        else:
            still_invalid[cell] += 1
    wf_ids = {x["id"]: x for x in wf}
    a_flip_ids = {i for c, ids in flips.items() if c[0] == "A" for i in ids}
    for x in wf:
        x["stripped_valid"] = x["id"] in a_flip_ids if x["class"] == K.GOAL_TRAILER else None
    trailer_not_flipped = [x["id"] for x in wf if x["class"] == K.GOAL_TRAILER
                           and not x["stripped_valid"]]
    outside_wf = sorted(i for i in a_flip_ids if i not in wf_ids)
    # Every (a) row's stripped plan is the tool plan by construction.
    for x in wf:
        if x["class"] == K.GOAL_TRAILER and x["answer_len"] - len(x["extra"]) != x["tool_len"]:
            raise K.Halt(f"{x['id']}: stripped plan is not the tool plan")

    cells_out = []
    for part, model, arm in sorted({(("A",) + (m, a)) for m in C.PART_A_MODELS for a in C.ARMS}
                                   | {("C", m, "unaided") for m in C.PART_A_MODELS}):
        rs = [r for r in (rows_a if part == "A" else rows_c)
              if r.model_tag == model and (part == "C" or r.arm == arm)]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        cells_out.append({"part": part, "model": model, "arm": arm, "n": len(rs), "k_frozen": k,
                          "flips": len(flips[(part, model, arm)]),
                          "flip_ids": sorted(flips[(part, model, arm)]),
                          "stripped_still_invalid": still_invalid[(part, model, arm)]})

    # --- figures built on these cells: E2 and E3 solve (point estimates) and R4
    k_of = {(c["part"], c["model"], c["arm"]): (c["k_frozen"], c["k_frozen"] + c["flips"], c["n"])
            for c in cells_out}
    flip_set = {i for ids in flips.values() for i in ids}
    derived = []
    for name_, pairs in (("E2", lambda m: (("C", m, "unaided"), ("A", m, "plain"))),
                         ("E3", lambda m: (("A", m, "plain"), ("A", m, "steered")))):
        for e in ro[name_.lower()]:
            if e["task"] != "solve" or e["name"] != name_:
                continue
            a, b = pairs(e["model"])
            (a0, a1, na), (b0, b1, nb) = k_of[a], k_of[b]
            if e["unpaired_a"] or e["unpaired_b"] or not (na == nb == e["n_pairs"]) \
                    or abs(100 * (b0 - a0) / na - e["delta"]) > 1e-9:
                raise K.Halt(f"{name_} {e['model']}: frozen delta not reproduced")
            derived.append({"figure": name_, "model": e["model"], "frozen": 100 * (b0 - a0) / na,
                            "post_hoc": 100 * (b1 - a1) / na})
    for m, v in ro["readings"]["R4"]["per_model"].items():
        rs = [r for r in rows_a if r.model_tag == m and r.success is True
              and r.done_reason != "length" and not r.no_room
              and r.response_truncated_by_storage is False]
        k0 = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        if (len(rs), k0) != (v["n"], v["delivered_k"]):
            raise K.Halt(f"R4 {m}: {(len(rs), k0)} != {(v['n'], v['delivered_k'])}")
        k1 = k0 + sum(K.row_id(r) in flip_set for r in rs)
        derived.append({"figure": "R4", "model": m, "n": len(rs), "k_frozen": k0, "k_post_hoc": k1,
                        "frozen": 100 * k0 / len(rs), "post_hoc": 100 * k1 / len(rs)})
    self_check["checks"] += len(derived)
    self_check["equal"] += len(derived)

    haiku = haiku_check(args.results, domains,
                        lambda need: K.plan_verdicts(need, None, args.marketplace, domains)[0])

    return {"self_check": self_check, "verdict_source": {"frozen_plans": src, "stripped_plans": src2},
            "frozen_wrong_facts": frozen_wf, "by_class": {c: by_class[c] for c in K.CLASSES},
            "by_class_model": {c: K.counter_dict(Counter(x["model"] for x in wf if x["class"] == c))
                               for c in K.CLASSES},
            "other_by_shape": K.counter_dict(Counter(x["shape"] for x in wf if x["class"] == K.OTHER)),
            "c4_rule_differs": c4_diff, "trailer_rows_not_flipped": trailer_not_flipped,
            "tool_arm_flips_outside_wrong_facts": outside_wf,
            "rows": sorted(wf, key=lambda x: x["id"]), "cells": cells_out, "derived": derived,
            "haiku": haiku}


# ------------------------------------------------------------------ rendering
def render_numbers(res: dict, name) -> str:
    bc, bm = res["by_class"], res["by_class_model"]
    moved = [c for c in res["cells"] if c["flips"]]

    def cell_txt(c):
        what = f"solve {c['arm']}" if c["part"] == "A" else "solve unaided (Part C)"
        return (f"{name(c['model'])} {what} {c['k_frozen']}/{c['n']} ({K.pct(c['k_frozen'], c['n'])}%) → "
                f"{c['k_frozen'] + c['flips']}/{c['n']} ({K.pct(c['k_frozen'] + c['flips'], c['n'])}%)")
    der = [x for x in res["derived"] if abs(x["post_hoc"] - x["frozen"]) > 1e-9]

    def der_txt(x):
        label = {"E2": "E2 solve (tools plain − unaided)", "E3": "E3 solve (steered − plain)",
                 "R4": "R4 (tool-verified, full answer, delivered)"}[x["figure"]]
        if x["figure"] == "R4":
            return (f"{label} {name(x['model'])} {x['frozen']:.1f}% of {x['n']} → "
                    f"{x['post_hoc']:.1f}%")
        return f"{label} {name(x['model'])} {x['frozen']:+.1f} → {x['post_hoc']:+.1f}"
    h = res["haiku"]
    if h.get("overlay"):
        hk = (f"Frontier Haiku 4.5 with tools: the overlay grades {len(h['plan_invalid'])} of "
              f"{h['solve_rows']} solve rows `plan_invalid` ({', '.join(h['plan_invalid'])}); these are "
              "the \"three transcription errors\" of the paper's delivery-gap paragraph, so depot p02 "
              + ("**is one of them**" if h["depot_p02_is_counted"] else "is **not** one of them"))
        if h["raw"]:
            hk += ". By the rule above (raw trials read): " + "; ".join(
                f"{x['domain']} {x['problem']} {x['class']} ({x['answer_len']} plan lines "
                f"extracted, tool plan {x['tool_len']} actions"
                + (", trailing goal facts dropped: valid" if x["stripped_valid"] else "")
                + ")" for x in h["rows"]) + (
                f"; {sum(x['class'] == K.COPY_ERROR for x in h['rows'])} of "
                f"{len(h['rows'])} are copying errors by this rule, "
                f"{sum(x['class'] == K.OTHER and x['answer_len'] < x['tool_len'] for x in h['rows'])} "
                "write fewer lines than the tool plan has actions.")
        else:
            hk += (". Its shape (C4: the tool plan, then two goal facts) is not re-checked by the "
                   "script here: the raw Haiku with-tools trials are not in this checkout.")
    else:
        hk = "Frontier Haiku: overlay not found, not checked."
    lines = [
        f"*Generated by {SRC} (output `tools/reanalysis/out/iss028_goal_trailers.{{json,md}}`); "
        "do not edit between the markers, rerun the script. Self-check: the frozen grader "
        f"reproduces the readout's solve figures (E1, Part C, E2, E3, E4, R4: {res['self_check']['equal']} "
        f"of {res['self_check']['checks']} equal), and the three classes sum to the frozen total.*",
        "",
        f"**ISS-028, post hoc (goal facts after a correct plan; the frozen values above stay).** "
        f"Of the **{res['frozen_wrong_facts']}** solve rows the frozen E4 labels WRONG_FACTS: "
        f"**{bc[K.GOAL_TRAILER]}** repeat the tool's plan exactly and then list goal facts ("
        + ", ".join(f"{name(m)} {n}" for m, n in bm[K.GOAL_TRAILER].items())
        + f"); **{bc[K.COPY_ERROR]}** are copying errors (the tool plan's length, some actions "
        f"changed; " + ", ".join(f"{name(m)} {n}" for m, n in bm[K.COPY_ERROR].items())
        + f"); **{bc[K.OTHER]}** are other shapes ("
        + "; ".join(f"{s} {n}" for s, n in res["other_by_shape"].items()) + "). "
        "With the trailing goal facts dropped and the plan validated again (post hoc extractor "
        "rule, every solve row graded `plan_invalid`), delivered solve moves in these cells: "
        + ("; ".join(cell_txt(c) for c in moved) if moved else "none")
        + ". No other rerun solve cell moves"
        + (f" ({sum(c['stripped_still_invalid'] for c in res['cells'])} more rows lose a goal "
           "trailer but stay invalid)" if any(c["stripped_still_invalid"] for c in res["cells"]) else "")
        + (". Figures built on these cells, point estimates only (intervals, p-values and readings "
           "not recomputed): " + "; ".join(der_txt(x) for x in der) if der else "")
        + ". Do NOT quote a post hoc value in place of the frozen E1 / E2 / E3 / E4 / R4 figure, or "
        "\"transcription errors\" for all " + str(res["frozen_wrong_facts"]) + " rows. " + hk,
    ]
    return "\n".join(lines) + "\n"


def render_md(res: dict, name) -> str:
    L = ["# ISS-028: goal facts after a correct plan (post hoc)", "",
         f"Generated by {SRC}. Read-only, descriptive; the frozen readout is the record.", "",
         "## Verdict source", "", "```json", json.dumps(res["verdict_source"], indent=1), "```", "",
         "## Classes of the frozen E4 WRONG_FACTS solve rows", "",
         "| class | rows | by model |", "|---|---|---|"]
    for c in K.CLASSES:
        L.append(f"| {c} | {res['by_class'][c]} | "
                 + ", ".join(f"{name(m)} {n}" for m, n in res["by_class_model"][c].items()) + " |")
    L += ["", f"Other, by shape: {res['other_by_shape']}.", "",
          f"C4 rule (substring of the goal text) differs from rule (a) on: {res['c4_rule_differs'] or 'no row'}.",
          f"Goal-trailer rows whose stripped plan does not validate: {res['trailer_rows_not_flipped'] or 'none'}.",
          f"Tool-arm rows that flip but are not E4 WRONG_FACTS: {res['tool_arm_flips_outside_wrong_facts'] or 'none'}.",
          "", "## Post hoc delivered solve per cell (trailing goal facts dropped)", "",
          "| part | model | arm | n | frozen | flips | post hoc | stripped, still invalid |",
          "|---|---|---|---|---|---|---|---|"]
    for c in res["cells"]:
        L.append(f"| {c['part']} | {name(c['model'])} | {c['arm']} | {c['n']} | {c['k_frozen']} | "
                 f"{c['flips']} | {c['k_frozen'] + c['flips']} | {c['stripped_still_invalid']} |")
    L += ["", "## Figures built on these cells (point estimates)", "",
          "| figure | model | frozen | post hoc |", "|---|---|---|---|"]
    for x in res["derived"]:
        L.append(f"| {x['figure']} | {name(x['model'])} | {x['frozen']:.2f} | {x['post_hoc']:.2f} |")
    L += ["", "## Rows", "", "| id | class | shape | tool actions | answer lines | extra lines |",
          "|---|---|---|---|---|---|"]
    for x in res["rows"]:
        L.append(f"| `{K.md_cell(x['id'])}` | {x['class']} | {x['shape']} | {x['tool_len']} | {x['answer_len']} | "
                 + (", ".join(f"`{e}`" for e in x["extra"]) if x["extra"] else "") + " |")
    L += ["", "## Frontier Haiku 4.5, with tools", "", "```json", json.dumps(res["haiku"], indent=1), "```"]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--plan-verdicts", type=Path, default=None,
                    help="delivered-rerun-secondary/plan_verdicts.json (optional cache)")
    ap.add_argument("--marketplace", type=Path, default=REPO.parent / "pddl-copilot")
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--readout", type=Path,
                    default=REPO / "development/reference/delivered_rerun_readout.json")
    ap.add_argument("--out-dir", type=Path, default=K.OUT)
    args = ap.parse_args(argv)
    try:
        res = analyse(args)
    except K.Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    import gen_common
    name = gen_common.model_name
    numbers = render_numbers(res, name)
    md = render_md(res, name)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "iss028_goal_trailers.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    (args.out_dir / "iss028_goal_trailers.md").write_text(md)
    (args.out_dir / "numbers_iss028.md").write_text(numbers)
    print(numbers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
