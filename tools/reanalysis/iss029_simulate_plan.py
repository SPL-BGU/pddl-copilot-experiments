#!/usr/bin/env python3
"""ISS-029: simulate problems whose prompt plan is not the cached plan.

    python3 tools/reanalysis/iss029_simulate_plan.py --results <results root> \\
        [--gt-cache <results>/derived/gt_cache.json]

Read-only over results; post hoc and descriptive. The frozen readout
(`development/reference/delivered_rerun_readout.json`) stays the record.

The harness builds each simulate prompt from the planner's plan, computed live at
run start; the frozen delivered grader compares answers with the trajectory in
the pinned ground-truth cache (`results/derived/gt_cache.json`). The prompt is
not stored, so the run's plan is read from the rows:

  run plan of a problem = the plan the with-tools rows (Part A, 3 models x 2
  arms) passed in their first `get_state_transition` call that has a `plan`
  argument (actions compared with parentheses, case and spacing ignored, as
  C4 `plan_actions`), when at least 90% of those rows passed one same plan;
  otherwise the problem is "undetermined" and listed.

Steps (any failed check halts, nothing written):

1. Gates: frozen package hash (822aace...), domains manifest, and the cache's
   canonical hash equal to the prereg pin (`tools/gt_cache_gate.py`).
2. Grades every Part A and Part C simulate row with the frozen `grade.grade`
   and checks the readout: per model and arm the E1 simulate delivered count and
   reasons, the Part C simulate delivered count (E2), the E4 simulate category
   and sub-label counts.
3. Lists the problems whose run plan differs from the cache's plan, and the Part
   C rows that the stored online grade passes (graded at run time against the
   run-start ground truth) and the frozen delivered grade fails. Self-check:
   every such row is on a listed problem and its answer's actions are the run
   plan; otherwise halt (the row would be another fault).
4. Post hoc: each listed Part C row graded again by the frozen grader with only
   the oracle swapped for the trajectory the tool returned for the run plan (the
   last `get_state_transition` result of the with-tools rows that passed the run
   plan and are tool-verified; all of them must agree). The with-tools rows on
   the listed problems that the online grade passes, that had room for a final
   turn, and that the delivered grade fails are listed too.

`--diagnostic-unpinned` runs on a cache whose hash is not the pin (for example a
cache rebuilt elsewhere): readout differences are reported instead of halting,
outputs go to iss029_simulate_plan.diagnostic.{json,md}, and no NUMBERS.md
block is written. A diagnostic run is never a figure.

Outputs (tools/reanalysis/out/): iss029_simulate_plan.json, .md, and the
NUMBERS.md block numbers_iss029.md (also printed to stdout).
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
from c4_select_transcripts import answer_actions, plan_actions  # noqa: E402

REPO = K.REPO
SRC = "`tools/reanalysis/iss029_simulate_plan.py`"
MODAL_SHARE = 0.9


def passed_plan(row) -> tuple | None:
    """The plan of the row's first get_state_transition call with a plan argument."""
    for tc in row.tool_calls:
        if tc.name == "get_state_transition" and isinstance(tc.arguments, dict) \
                and "plan" in tc.arguments:
            return plan_actions(tc.arguments["plan"])
    return None


def run_plans(rows) -> dict:
    """{(domain, problem): {"plan": tuple | None, "rows": n, "with_plan": n, "modal": n}}."""
    by = defaultdict(Counter)
    n_rows = Counter()
    for r in rows:
        n_rows[(r.domain, r.problem)] += 1
        p = passed_plan(r)
        if p is not None:
            by[(r.domain, r.problem)][p] += 1
    out = {}
    for k in sorted(n_rows):
        c = by.get(k, Counter())
        if not c:
            out[k] = {"plan": None, "rows": n_rows[k], "with_plan": 0, "modal": 0}
            continue
        top, n = c.most_common(1)[0]
        tot = sum(c.values())
        out[k] = {"plan": top if n >= MODAL_SHARE * tot else None, "rows": n_rows[k],
                  "with_plan": tot, "modal": n}
    return out


def check_readout(ro, rows_a, rows_c, grades, gt_cache, E4) -> list[str]:
    bad, n = [], 0
    for e in ro["e1"]:
        if e["task"] != "simulate":
            continue
        rs = [r for r in rows_a if r.model_tag == e["model"] and r.arm == e["arm"]]
        g = [grades[(r.cell, r.trial_key)] for r in rs]
        got = (len(rs), sum(x.ok for x in g), dict(Counter(x.reason for x in g)))
        n += 1
        if got != (e["n"], e["delivered_k"], e["reasons"]):
            bad.append(f"E1 {e['model']}/{e['arm']}: {got[:2]} != {(e['n'], e['delivered_k'])}")
    for e in ro["e2"]:
        if e["task"] != "simulate" or e["name"] != "E2":
            continue
        rs = [r for r in rows_c if r.model_tag == e["model"]]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        n += 1
        if e["unpaired_a"] or len(rs) != e["n_pairs"] or abs(100 * k / len(rs) - e["a_pct"]) > 1e-9:
            bad.append(f"Part C {e['model']}: {k}/{len(rs)} != {round(e['a_pct'] * e['n_pairs'] / 100)}"
                       f"/{e['n_pairs']}")
    for e in ro["e4"]:
        if e["task"] != "simulate":
            continue
        rs = [r for r in rows_a if r.model_tag == e["model"] and r.arm == e["arm"]
              and r.success is True and grades[(r.cell, r.trial_key)].ok is False]
        subs = Counter()
        for r in rs:
            cat, sub = E4.classify(r, grades[(r.cell, r.trial_key)], gt_cache)
            subs[f"{cat}: {sub}"] += 1
        n += 1
        if dict(sorted(subs.items())) != e["subs"]:
            bad.append(f"E4 {e['model']}/{e['arm']}: categories differ")
    return bad, n


def analyse(args) -> dict:
    from tools.delivered_rerun import constants as C
    from tools.delivered_rerun import e4 as E4
    from tools.delivered_rerun import grade as G
    from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash

    ro = K.load_readout(args.readout)
    cells = K.load_frozen(args.results, args.domains_dir)
    if not args.gt_cache.exists():
        raise K.Halt(f"{args.gt_cache} not found: the cached plan and trajectory are needed "
                     "(run on the machine that holds results/derived/gt_cache.json)")
    gt_cache = json.loads(args.gt_cache.read_text())
    pinned = canonical_hash(gt_cache) == PREREG_PINNED_HASH
    if not pinned and not args.diagnostic_unpinned:
        raise K.Halt("the ground-truth cache does not match the pinned canonical hash")
    rows_a = [r for m in C.PART_A_MODELS for r in cells["rerun_a"][m].rows if r.task == "simulate"]
    rows_c = [r for m in C.PART_A_MODELS for r in cells["rerun_c"][m].rows if r.task == "simulate"]
    grades = {(r.cell, r.trial_key): G.grade(r, gt_cache, {}) for r in rows_a + rows_c}
    bad, n_checks = check_readout(ro, rows_a, rows_c, grades, gt_cache, E4)
    if bad and pinned:
        raise K.Halt("the frozen grades do not reproduce the readout:\n  " + "\n  ".join(bad))

    plans = run_plans(rows_a)
    problems = []
    for (d, p), v in plans.items():
        cache = plan_actions(gt_cache[d][p]["plan"])
        v.update(domain=d, problem=p, cache_len=len(cache),
                 run_len=len(v["plan"]) if v["plan"] else None,
                 differs=v["plan"] is not None and v["plan"] != cache)
        problems.append(v)
    differ = {(v["domain"], v["problem"]): v for v in problems if v["differs"]}
    undetermined = [f"{v['domain']} {v['problem']}" for v in problems if v["plan"] is None]

    # Part C rows: online grade passes, frozen delivered grade fails
    flagged = [r for r in rows_c if r.success is True and grades[(r.cell, r.trial_key)].ok is False]
    other_fault = [K.row_id(r) for r in flagged
                   if (r.domain, r.problem) not in differ
                   or answer_actions(r.response) != differ[(r.domain, r.problem)]["plan"]]
    if other_fault and pinned:
        raise K.Halt(f"Part C rows graded wrong for another reason: {other_fault}")

    # post hoc: the frozen grader with the oracle swapped for the run plan's trajectory
    post = []
    for r in flagged:
        k = (r.domain, r.problem)
        if k not in differ:
            continue
        donors = [x for x in rows_a if (x.domain, x.problem) == k and x.success is True
                  and passed_plan(x) == differ[k]["plan"]]
        trajs = {json.dumps(E4._last_tool_trajectory(x), sort_keys=True) for x in donors}
        if len(trajs) != 1 or not donors:
            raise K.Halt(f"{k}: {len(donors)} tool-verified rows give {len(trajs)} trajectories")
        donor = sorted(donors, key=K.row_id)[0]
        text = next(tc.result for tc in reversed(donor.tool_calls)
                    if tc.name == "get_state_transition"
                    and isinstance(E4._safe_json_loads(tc.result), dict)
                    and not E4._safe_json_loads(tc.result).get("error"))
        alt = {r.domain: {r.problem: {"trace": text}}}
        g2 = G.grade(r, alt, {})
        post.append({"id": K.row_id(r), "model": r.model_tag, "frozen": grades[(r.cell, r.trial_key)].reason,
                     "post_hoc": g2.reason, "post_hoc_ok": g2.ok, "oracle_from": K.row_id(donor),
                     "donor_rows": len(donors)})
    tool_rows = [K.row_id(r) for r in rows_a if (r.domain, r.problem) in differ
                 and r.success is True and not r.no_room and grades[(r.cell, r.trial_key)].ok is False]
    part_c_cells = []
    for m in C.PART_A_MODELS:
        rs = [r for r in rows_c if r.model_tag == m]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        up = sum(1 for x in post if x["model"] == m and x["post_hoc_ok"])
        part_c_cells.append({"model": m, "n": len(rs), "k_frozen": k, "flips": up})
    return {"pinned_cache": pinned, "readout_checks": n_checks, "readout_differences": bad,
            "problems_total": len(problems), "differ": [
                {k_: v[k_] for k_ in ("domain", "problem", "rows", "with_plan", "modal",
                                      "run_len", "cache_len")}
                | {"no_room_rows": sum(r.no_room for r in rows_a
                                       if (r.domain, r.problem) == (v["domain"], v["problem"]))}
                for v in differ.values()],
            "undetermined": undetermined, "part_c_rows": len(rows_c),
            "part_c_online_ok_delivered_wrong": [K.row_id(r) for r in flagged],
            "part_c_other_fault": other_fault, "post_hoc": post,
            "tool_rows_ok_with_room_delivered_wrong": tool_rows, "part_c_cells": part_c_cells}


def render_numbers(res: dict, name) -> str:
    d = res["differ"]
    moved = [c for c in res["part_c_cells"] if c["flips"]]
    return "\n".join([
        f"*Generated by {SRC} (output `tools/reanalysis/out/iss029_simulate_plan.{{json,md}}`); do not "
        "edit between the markers, rerun the script. Self-check: the ground-truth cache matches the "
        f"pinned hash; the frozen grader reproduces the readout's simulate E1, Part C and E4 rows "
        f"({res['readout_checks']} cells); every Part C row the online grade passes and the delivered "
        "grade fails is on a listed problem and simulates the run's plan.*", "",
        f"**ISS-029, post hoc (simulate prompt plan vs cached plan; the frozen values above stay).** "
        f"For **{len(d)} of {res['problems_total']}** simulate problems the plan the run's with-tools rows "
        "passed to the tool (so the plan in the prompt) is not the cached plan the delivered grader uses: "
        + ", ".join(f"{x['domain']} {x['problem']} ({x['run_len']} vs {x['cache_len']} actions)" for x in d)
        + f". Of the {res['part_c_rows']} Part C simulate rows, **{len(res['part_c_online_ok_delivered_wrong'])}** "
        "pass the online grade and fail the delivered grade: "
        + ", ".join(f"`{i}`" for i in res["part_c_online_ok_delivered_wrong"])
        + ". Graded against the run plan's trajectory: "
        + ("; ".join(f"{name(c['model'])} simulate unaided (Part C) {c['k_frozen']}/{c['n']} "
                     f"({K.pct(c['k_frozen'], c['n'])}%) → {c['k_frozen'] + c['flips']}/{c['n']} "
                     f"({K.pct(c['k_frozen'] + c['flips'], c['n'])}%)" for c in moved) or "no cell moves")
        + f". With-tools rows on these problems that pass online, had room and fail delivered: "
        f"{len(res['tool_rows_ok_with_room_delivered_wrong'])}. Do NOT quote the post hoc count in place "
        "of the frozen E2 simulate figure."]) + "\n"


def render_md(res: dict, name) -> str:
    L = ["# ISS-029: simulate prompt plan vs cached plan (post hoc)", "",
         f"Generated by {SRC}. Read-only, descriptive; the frozen readout is the record.",
         f"Pinned cache: {res['pinned_cache']}. Readout differences: {res['readout_differences'] or 'none'}.", "",
         "| problem | rows | rows passing a plan | rows passing the run plan | run plan actions | "
         "cache plan actions | rows with no room |", "|---|---|---|---|---|---|---|"]
    for x in res["differ"]:
        L.append(f"| {x['domain']} {x['problem']} | {x['rows']} | {x['with_plan']} | {x['modal']} | "
                 f"{x['run_len']} | {x['cache_len']} | {x['no_room_rows']} |")
    L += ["", f"Undetermined (no plan passed by at least {int(MODAL_SHARE * 100)}% of the rows): "
          f"{', '.join(res['undetermined']) or 'none'}.", "",
          f"Part C rows, online ok and delivered wrong: {res['part_c_online_ok_delivered_wrong']}.",
          f"Of those, another fault: {res['part_c_other_fault'] or 'none'}.", "",
          "| row | frozen | post hoc | oracle from | tool-verified rows that passed the run plan |",
          "|---|---|---|---|---|"]
    for x in res["post_hoc"]:
        L.append(f"| `{K.md_cell(x['id'])}` | {x['frozen']} | {x['post_hoc']} | `{K.md_cell(x['oracle_from'])}` | {x['donor_rows']} |")
    L += ["", f"With-tools rows on these problems, online ok, room for a final turn, delivered wrong: "
          f"{res['tool_rows_ok_with_room_delivered_wrong'] or 'none'}."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--gt-cache", type=Path, default=None,
                    help="default: <results>/derived/gt_cache.json")
    ap.add_argument("--diagnostic-unpinned", action="store_true")
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--readout", type=Path,
                    default=REPO / "development/reference/delivered_rerun_readout.json")
    ap.add_argument("--out-dir", type=Path, default=K.OUT)
    args = ap.parse_args(argv)
    if args.gt_cache is None:
        args.gt_cache = args.results / "derived" / "gt_cache.json"
    try:
        res = analyse(args)
    except K.Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    import gen_common
    name = gen_common.model_name
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = "iss029_simulate_plan" + ("" if res["pinned_cache"] else ".diagnostic")
    (args.out_dir / f"{stem}.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    (args.out_dir / f"{stem}.md").write_text(render_md(res, name))
    if res["pinned_cache"]:
        numbers = render_numbers(res, name)
        (args.out_dir / "numbers_iss029.md").write_text(numbers)
        print(numbers)
    else:
        print("DIAGNOSTIC (cache not the pinned one): no NUMBERS.md block written; never a figure.")
        print(render_md(res, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
