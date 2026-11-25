#!/usr/bin/env python3
"""RQ1 solve and simulate tables and figures on the corrected-prompt control.

    python -m tools.reanalysis.rq1_control_metrics --marketplace ../pddl-copilot
        [--results DIR] [--figs DIR]

The reporting rule of `development/reference/control_prompt_fix_prereg.md` (section 6)
makes cell B of the control (answer format stated) the no-tools baseline of the three
open-weight models on solve and simulate, and quotes both arms under the second
reading. This script rebuilds the three RQ1 measures that use those two tasks
(`rq1_metrics.metric2`, `metric3`, `metric4`) on that basis:

  no tools        cell B of the control                       second reading
  tools, plain    Part A of the rerun, plain wordings         second reading
  tools, steered  Part A of the rerun, steered wordings       second reading
  Claude rows     as filed by `rq1_metrics.py` (not part of the control)

The second reading is the registered one of the control's analysis, called through
`control_prompt_fix.second_reading`: on solve the plan in the last code block decides
when that block holds a plan; on simulate a trace written one JSON object per line
also counts when it equals the answer key. On simulate the per-state scores read that
same line trace as one more candidate, so that a trace the second reading counts as
exact also scores all of its states.

These measures are descriptive, as the measures of `rq1_metrics.py` are. No file of a
frozen package is edited: the functions are imported, and `best_state_score` is
replaced at run time for the call to `metric2` only. Before any table is written the
script checks its counts against the control's frozen analysis output
(`out/control_prompt_fix.json`) and halts on any difference.

Writes `out/rq1_control_metrics.{json,md}`, the table rows in `out/tex/rq1c_*.tex` and
the two by-length figures in `out/figs/` under the names `rq1c_*`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.reanalysis import control_prompt_fix as M
from tools.reanalysis import rq1_figures as FIG
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq1_tex as TEX
from tools.reanalysis import rq3_context_pilot as PILOT
from tools.reanalysis.gen_common import model_name

HERE = Path(__file__).resolve().parent
FROZEN = "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79"
TASKS = ("solve", "simulate")


class Halt(Exception):
    pass


def second_rec(r, g, arm: str, verdict, gt_cache) -> dict:
    """One row as `rq1_metrics.rec` builds it, with `ok` and `plan` under the second
    reading."""
    second, _folded, _layout = M.second_reading(r, g, verdict, gt_cache)
    plan = None
    if r.task == "solve":
        bp = M.RG.block_plan(r.response)
        plan = bp[0] if bp is not None else g.plan
    return R1.rec(model_name(r.model if hasattr(r, "model") else ""), arm, r.task, r.domain,
                  r.problem, r.plan_label, r.variant, bool(second), None, plan, r.response,
                  [(c.name, c.arguments, c.result) for c in r.tool_calls])


_frozen_best = R1.best_state_score


def best_state_score_second(response: str, oracle: list[dict]) -> dict:
    """`rq1_metrics.best_state_score`, with the line trace of the second reading as one
    more candidate. It wins when it matches more states (ties: longer right prefix)."""
    best = _frozen_best(response, oracle)
    steps = PILOT.line_reader_steps(response)
    if steps:
        s = R1.state_score(steps, oracle)
        if not best["parsed"] or (s["matched"], s["prefix"]) > (best["matched"], best["prefix"]):
            s.update(parsed=True, shift_gain=best["shift_gain"], salvaged=False,
                     salvaged_matched=s["matched"])
            best = s
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--marketplace", type=Path, required=True)
    ap.add_argument("--figs", type=Path, default=HERE / "out" / "figs")
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    if M.package_sha256() != FROZEN:
        raise Halt("the control's frozen package changed")
    filed = json.loads((args.out / "control_prompt_fix.json").read_text())
    if filed["package_sha256"] != FROZEN or filed["mode"] != "live":
        raise Halt("out/control_prompt_fix.json is not the frozen live analysis output")

    # The rerun through the frozen package, the frontier rows, the problem facts: as
    # rq1_metrics.main builds them.
    cells, grades, gt_cache = R1.load_rerun_cells(args)
    rerun_rows, _ = R1.load_rerun(args)
    frontier, notes = R1.load_frontier(args)
    facts = R1.problem_facts(rerun_rows, gt_cache, args.domains_dir)
    if any(f["objects"] is None for f in facts.values()):
        raise Halt("a solvable problem has no readable (:objects ...) block")

    verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
    design = M.REGISTERED
    root = args.results / M.RUN_TAG
    tags, _r2 = M.resolve_tags(root, design, "")
    control = M.load_control(root, design, tags)

    rows = []
    for m in M.MODEL_ORDER:
        name = model_name(m)
        for r, g in M.frozen_grades(control[m]["B"].rows, verdict, gt_cache):
            if r.task in TASKS:
                d = second_rec(r, g, "none", verdict, gt_cache)
                d["model"] = name
                rows.append(d)
        for r in cells["rerun_a"][m].rows:
            if r.task in TASKS:
                d = second_rec(r, grades[(r.cell, r.trial_key)], r.arm, verdict, gt_cache)
                d["model"] = name
                rows.append(d)

    # Checks against the frozen analysis output, on all 300 trials of a cell.
    want = {(r["model"], r["task"], r["cell"]): r["second"]["right"] for r in filed["rates"]}
    bad = []
    for m in M.MODEL_ORDER:
        for t in TASKS:
            for arm, cell in (("none", "B"), ("plain", "Part A")):
                got = [x for x in rows if x["model"] == model_name(m) and x["task"] == t
                       and x["arm"] == arm]
                k = sum(x["ok"] for x in got)
                if (k, len(got)) != (want[(m, t, cell)], 300):
                    bad.append(f"{m}/{t}/{arm}: {k}/{len(got)} vs {want[(m, t, cell)]}/300")
    if bad:
        raise Halt("counts differ from the frozen analysis output:\n  " + "\n  ".join(bad))

    # Simulate: the open-weight rows with the line trace as one more candidate, the
    # Claude rows exactly as rq1_metrics scores them; the two results are joined.
    claude = [r for r in frontier if r["task"] in TASKS]
    R1.best_state_score = best_state_score_second
    try:
        m2 = R1.metric2(rows, gt_cache, facts)
    finally:
        R1.best_state_score = _frozen_best
    m2c = R1.metric2(claude, gt_cache, facts)
    if (m2c["skipped_problems"], m2c["undetermined_problems"]) != (
            m2["skipped_problems"], m2["undetermined_problems"]):
        raise Halt("the two simulate passes leave out different problems")
    m2["overall"] += m2c["overall"]
    m2["cells"] += m2c["cells"]
    rows += claude
    res = {"control_package_sha256": FROZEN, "frontier_notes": notes,
           "reading": "second reading; no-tools rows of the open-weight models are cell B "
                      "of the corrected-prompt control; Claude rows as filed",
           "m2": m2, "m3": R1.metric3(rows, facts), "m4": R1.metric4(rows, facts)}

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq1_control_metrics.json").write_text(json.dumps(res, indent=1) + "\n")
    tex = args.out / "tex"
    tex.mkdir(parents=True, exist_ok=True)
    (tex / "rq1c_simulate.tex").write_text(TEX.rows(res["m2"]["overall"], lambda c: [
        TEX.ci(c["exact"]) + ("" if c["exact_known"] == c["n"]
                              else f"$^{{\\ddagger{c['n'] - c['exact_known']}}}$"),
        TEX.ci(c["states"]), TEX.ci(c["states_salvaged"]), f"${c['no_trace']}$ / ${c['n']}$",
        TEX.rho(c["rho_states"])]))
    (tex / "rq1c_solve.tex").write_text(TEX.rows(res["m3"]["corr"], lambda c: [
        TEX.ci(c["solved"]), TEX.rho(c["rho_len"]), TEX.rho(c["rho_obj"]),
        TEX.rho(c["rho_time"])]))
    (tex / "rq1c_planlen.tex").write_text(TEX.rows(res["m4"]["cells"], lambda c: [
        f"${c['n_valid']}$ / ${c['n_trials']}$", f"${c['mean_len']:.1f}$",
        f"${c['mean_ref_len']:.1f}$", f"${c['median_ratio']:.2f}$",
        f"${c['shorter']}$ / ${c['equal']}$ / ${c['longer']}$", f"${c['max_ratio']:.1f}$",
        (f"${c['same_len_as_tool_plan']}$ / ${c['with_tool_plan']}$"
         if c["with_tool_plan"] else "--")]))

    # Figures: the functions of rq1_figures, written under the rq1c_ names.
    save = FIG.save
    FIG.save = lambda fig, out, name: save(fig, out, name.replace("rq1_", "rq1c_"))
    try:
        FIG.fig_simulate(res, args.figs)
        FIG.fig_solve(res, args.figs)
    finally:
        FIG.save = save

    L = ["*Generated by `tools/reanalysis/rq1_control_metrics.py`. RQ1 solve and simulate "
         "with cell B of the corrected-prompt control as the no-tools rows of the three "
         "open-weight models, every open-weight arm under the second reading; Claude rows "
         "as filed. Descriptive. Intervals are 95% domain-cluster bootstrap.*", "",
         "#### Solve: solved, and Spearman rho with hardness", "",
         "| model | arm | solved | rho plan length | rho objects | rho planner time |",
         "|---|---|---|---|---|---|"]
    for c in res["m3"]["corr"]:
        L.append(f"| {c['model']} | {R1.ARM_NAMES[c['arm']]} | {R1.cell(c['solved'])} | "
                 f"{R1.rho_cell(c['rho_len'])} | {R1.rho_cell(c['rho_obj'])} | "
                 f"{R1.rho_cell(c['rho_time'])} |")
    L += ["", "#### Solve: solved by reference plan length", "",
          "| model | arm | bin | trials | solved |", "|---|---|---|---|---|"]
    for c in res["m3"]["by_length"]:
        L.append(f"| {c['model']} | {R1.ARM_NAMES[c['arm']]} | {c['bin']} | {c['n']} | "
                 f"{R1.cell(c['solved'])} |")
    L += ["", f"#### Simulate ({len(facts) - len(res['m2']['skipped_problems'])} problems; left out: "
          f"{', '.join(res['m2']['skipped_problems'])})", "",
          "| model | arm | trials | exact trace | states, strict | states, lenient | no trace | "
          "rho (strict, trace length) |", "|---|---|---|---|---|---|---|---|"]
    for c in res["m2"]["overall"]:
        L.append(f"| {c['model']} | {R1.ARM_NAMES[c['arm']]} | {c['n']} | {R1.cell(c['exact'])} | "
                 f"{R1.cell(c['states'])} | {R1.cell(c['states_salvaged'])} | {c['no_trace']} | "
                 f"{R1.rho_cell(c['rho_states'])} |")
    L += ["", "#### Simulate: by trace length", "",
          "| model | arm | bin | trials | exact trace | states, strict | states, lenient |",
          "|---|---|---|---|---|---|---|"]
    for c in res["m2"]["cells"]:
        L.append(f"| {c['model']} | {R1.ARM_NAMES[c['arm']]} | {c['bin']} | {c['n']} | "
                 f"{R1.cell(c['exact'])} | {R1.cell(c['states'])} | "
                 f"{R1.cell(c['states_salvaged'])} |")
    L += ["", "#### Plan length of the valid delivered plans", "",
          "| model | arm | valid plans | mean length | mean reference | median ratio | "
          "shorter / equal / longer | max ratio | same length as the tool's plan |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in res["m4"]["cells"]:
        L.append(f"| {c['model']} | {R1.ARM_NAMES[c['arm']]} | {c['n_valid']} / {c['n_trials']} | "
                 f"{R1.f2(c['mean_len'])} | {R1.f2(c['mean_ref_len'])} | "
                 f"{R1.f2(c['median_ratio'])} | {c['shorter']} / {c['equal']} / {c['longer']} | "
                 f"{R1.f2(c['max_ratio'])} | {c['same_len_as_tool_plan']} / {c['with_tool_plan']} |")
    (args.out / "rq1_control_metrics.md").write_text("\n".join(L) + "\n")
    print(f"wrote {args.out}/rq1_control_metrics.{{json,md}} and {tex}/rq1c_*.tex")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Halt, M.Halt, R1.Halt) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
