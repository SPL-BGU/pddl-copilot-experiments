#!/usr/bin/env python3
"""RQ1 solve and simulate tables and figures on the matched run.

    python -m tools.reanalysis.rq1_matched_metrics --marketplace ../pddl-copilot
        [--results DIR] [--serve-logs DIR] [--figs DIR] [--numbers]

The reporting rule of `development/reference/matched_run_prereg.md` (section 6) makes
the matched run what the paper reports for RQ1 on solve and simulate, for the three
open-weight models. This script rebuilds the three RQ1 measures that use those two
tasks (`rq1_metrics.metric2`, `metric3`, `metric4`) on that run, as
`rq1_control_metrics.py` built them on the control and the rerun:

  no tools        arm N of the matched run (format-stated system message)
  tools, plain    arm P of the matched run
  tools, steered  arm S of the matched run
  Claude rows     as filed by `rq1_metrics.py` (not part of the matched run)

A trial is right under the matched run's registered grade (prereg section 3), built by
the frozen `matched_run.grade_trials`: on solve the plan in the last closed code block
when that block holds a plan, otherwise the plan the rerun's grader reads, validated
in lower case; on simulate the trace the rerun's grader reads, or a trace written one
JSON object per line, equal to the answer key. The plan whose length is measured is
the plan that grade read. On simulate the per-state scores read the line trace as one
more candidate (`rq1_control_metrics.best_state_score_second`), as section 6 rule 4
registers.

Problem facts (reference plan length, trace length, planner runtime, the problems left
out of the simulate tables) are read from the matched run's own rows for the
open-weight rows, as the frozen `matched_run.breakdowns` does, and from the rerun's
rows for the Claude rows, as `rq1_control_metrics.py` does. So the Claude rows come out
as that script filed them, and this script halts if they do not.

These measures are descriptive. No file of a frozen package is edited: the functions
are imported, and `best_state_score` is replaced at run time for one call to `metric2`
only. Before anything is written the script checks, and halts on any difference:

  - the matched run's package hash, and that `out/matched_run.json` is the live output
    of that package;
  - the right count and the 300 trials of all 18 cells (3 models x 2 tasks x 3 arms)
    against `out/matched_run.json`;
  - the by-length solve table and the simulate table (exact trace, states strict,
    states lenient; per bin and overall) against the `breakdowns` of that file and
    against the two tables of `out/matched_run.md`, to the printed decimal;
  - the Claude cells against `out/rq1_control_metrics.json`.

Writes `out/rq1_matched_metrics.{json,md}`, the table rows in `out/tex/rq1m_*.tex`
(`rq1m_contrasts.tex` is built from `out/matched_run.json` alone, with no
recomputation) and the two by-length figures in `out/figs/` under the names `rq1m_*`.
With --numbers the markdown is spliced into development/NUMBERS.md (tag
RQ1-MATCHED-METRICS).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.reanalysis import control_prompt_fix as M
from tools.reanalysis import matched_run as MR
from tools.reanalysis import rq1_control_metrics as RC
from tools.reanalysis import rq1_figures as FIG
from tools.reanalysis import rq1_layout_regrade as RG
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq1_tex as TEX
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FROZEN = "1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d"
TAG = "RQ1-MATCHED-METRICS"
TASKS = MR.TASKS
CLAUDE = tuple(R1.FRONTIER)
NOT_AFTER_HOLM = "(not after Holm)"
CONTRAST_HEADS = {"M1": "plain minus no tools", "M2": "steered minus no tools",
                  "M3": "steered minus plain"}


class Halt(Exception):
    pass


# ------------------------------------------------------------------ the filed output
def read_filed(path: Path) -> dict:
    """`out/matched_run.json`, or a halt when it is not the frozen live output."""
    filed = json.loads(path.read_text())
    if filed.get("package_sha256") != FROZEN or filed.get("mode") != "live":
        raise Halt(f"{path} is not the live output of the matched run's frozen package")
    return filed


def filed_rates(filed: dict) -> dict:
    """{(model tag, task, arm): the registered-grade rate} for the 18 cells of the run."""
    out = {(r["model"], r["task"], r["cell"]): r[MR.REGISTERED_GRADE]
           for r in filed["rates"] if r["this_run"]}
    want = {(m, t, a) for m in MR.MODEL_ORDER for t in TASKS for a in MR.ARMS}
    if set(out) != want:
        raise Halt("the filed output does not hold the 18 cells of the matched run")
    return out


def filed_contrasts(filed: dict) -> dict:
    """{(name, model tag, task): contrast} for M1 to M3 under the registered grade."""
    out = {(c["name"], c["model"], c["task"]): c for c in filed["contrasts"]
           if c["grade"] == MR.REGISTERED_GRADE}
    want = {(n, m, t) for n in MR.CONTRASTS for m in MR.MODEL_ORDER for t in TASKS}
    if set(out) != want:
        raise Halt("the filed output does not hold the 18 registered contrasts")
    return out


# ------------------------------------------------------------------ checks
def check_counts(rows: list[dict], filed: dict, per_cell: int = 300) -> list[dict]:
    """All 18 cells: the right count and the trial count of `rows` (records of
    `rq1_metrics.rec`) equal the filed registered-grade counts, and every cell holds
    `per_cell` trials. Returns the table; halts on any difference."""
    want = filed_rates(filed)
    table, bad = [], []
    for m in MR.MODEL_ORDER:
        for t in TASKS:
            for arm in MR.ARMS:
                got = [x for x in rows if x["model"] == model_name(m) and x["task"] == t
                       and x["arm"] == MR.ARM_REC[arm]]
                k, w = sum(x["ok"] is True for x in got), want[(m, t, arm)]
                table.append({"model": m, "task": t, "arm": arm, "right": k, "n": len(got),
                              "filed_right": w["right"], "filed_n": w["n"]})
                if (k, len(got)) != (w["right"], w["n"]) or len(got) != per_cell:
                    bad.append(f"{m}/{t}/{arm}: {k}/{len(got)} vs {w['right']}/{w['n']} "
                               f"(a cell holds {per_cell} trials)")
    if bad:
        raise Halt("counts differ from the matched run's filed output:\n  " + "\n  ".join(bad))
    return table


def _printed(cells: list[dict], fields: tuple[str, ...]) -> dict:
    return {(c["model"], c["arm"], c.get("bin", "all")):
            (c["n"], *[R1.cell(c[f]) for f in fields]) for c in cells}


def breakdown_tables(m2: dict, m3: dict) -> tuple[str, str]:
    """The two by-length tables as `matched_run.render` prints them."""
    solve = md_table(["model", "arm", "bin", "trials", "solved"],
                     [[c["model"], R1.ARM_NAMES[c["arm"]], c["bin"], c["n"], R1.cell(c["solved"])]
                      for c in m3["by_length"]])
    sim = md_table(["model", "arm", "bin", "trials", "exact trace", "states, strict",
                    "states, lenient"],
                   [[c["model"], R1.ARM_NAMES[c["arm"]], c.get("bin", "all"), c["n"],
                     R1.cell(c["exact"]), R1.cell(c["states"]), R1.cell(c["states_salvaged"])]
                    for c in m2["overall"] + m2["cells"]])
    return solve, sim


def check_breakdowns(m2: dict, m3: dict, filed: dict, filed_md: str | None = None) -> int:
    """The open-weight by-length cells against the `breakdowns` of the filed output: the
    same cells, the same trial counts, the same figures to the printed decimal; the same
    problems left out. With `filed_md`, the two tables must also stand in it as printed.
    Returns the number of cells compared; halts on any difference."""
    b = filed["breakdowns"]
    sim = ("exact", "states", "states_salvaged")
    bad, n = [], 0
    for name, mine, theirs, fields in (
            ("solve by reference plan length", m3["by_length"],
             b["solve_by_reference_length"], ("solved",)),
            ("solve, all problems", m3["corr"], b["solve_overall"], ("solved",)),
            ("simulate, all problems", m2["overall"], b["simulate_overall"], sim),
            ("simulate by trace length", m2["cells"], b["simulate_by_trace_length"], sim)):
        got = _printed([{"n": c["solved"]["n"], **c} if "n" not in c else c for c in mine],
                       fields)
        want = _printed([{"n": c["solved"]["n"], **c} if "n" not in c else c for c in theirs],
                        fields)
        for key in sorted(set(got) | set(want)):
            n += 1
            if got.get(key) != want.get(key):
                bad.append(f"{name}, {' / '.join(key)}: {got.get(key)} vs filed {want.get(key)}")
    for name, mine, theirs in (
            ("problems left out", m2["skipped_problems"], b["simulate_left_out"]),
            ("problems with no determined plan", m2["undetermined_problems"],
             b["simulate_undetermined"])):
        if list(mine) != list(theirs):
            bad.append(f"simulate, {name}: {list(mine)} vs filed {list(theirs)}")
    if filed_md is not None:
        for name, table in zip(("solved by reference plan length",
                                "simulate by trace length and the lenient score"),
                               breakdown_tables(m2, m3)):
            if table not in filed_md:
                bad.append(f"the table \"{name}\" does not stand in out/matched_run.md as "
                           f"printed here")
    if bad:
        raise Halt("by-length breakdowns differ from the matched run's filed output:\n  "
                   + "\n  ".join(bad))
    return n


def check_claude(res: dict, filed_control: dict) -> int:
    """The Claude cells equal those `rq1_control_metrics.py` filed. Returns the number
    of cells compared; halts on any difference."""
    n, bad = 0, []
    for name, mine, theirs in (
            ("simulate, all problems", res["m2"]["overall"], filed_control["m2"]["overall"]),
            ("simulate by trace length", res["m2"]["cells"], filed_control["m2"]["cells"]),
            ("solve", res["m3"]["corr"], filed_control["m3"]["corr"]),
            ("solve by reference plan length", res["m3"]["by_length"],
             filed_control["m3"]["by_length"]),
            ("plan length", res["m4"]["cells"], filed_control["m4"]["cells"])):
        got = {(c["model"], c["arm"], c.get("bin", "all")): json.loads(json.dumps(c))
               for c in mine if c["model"] in CLAUDE}
        want = {(c["model"], c["arm"], c.get("bin", "all")): c
                for c in theirs if c["model"] in CLAUDE}
        for key in sorted(set(got) | set(want)):
            n += 1
            if got.get(key) != want.get(key):
                bad.append(f"{name}, {' / '.join(key)}")
    if bad or n == 0:
        raise Halt("the Claude cells differ from those filed by rq1_control_metrics.py:\n  "
                   + "\n  ".join(bad or ["no Claude cell found"]))
    return n


# ------------------------------------------------------------------ tex
def diff(b: dict) -> str:
    """A paired difference in points, formatted as `rq1_tex.ci` formats a rate, signed."""
    return f"${b['est']:+.1f}$ {{\\scriptsize$[{b['lo']:+.1f},\\,{b['hi']:+.1f}]$}}"


def not_after_holm(c: dict) -> bool:
    """The interval excludes zero and the Holm-adjusted p is 0.05 or more. Read from the
    filed label (the words "not after Holm"); the filed interval and adjusted p must say
    the same, or the output is not what this script takes it for."""
    marked = NOT_AFTER_HOLM in (c["label"] or "")
    numbers = (c["lo"] > 0 or c["hi"] < 0) and c["p_holm"] >= MR.HOLM_ALPHA
    if marked != numbers:
        raise Halt(f"{c['name']} {c['model']}/{c['task']}: the label {c['label']!r} and the "
                   f"interval with its Holm-adjusted p disagree")
    return marked


def contrast_rows(filed: dict) -> str:
    """Rows of the contrasts table, from the filed output alone: per task and model the
    three arm rates and M1, M2, M3 with intervals; a dagger on a difference whose
    interval excludes zero and whose Holm-adjusted p is 0.05 or more."""
    rates, cons = filed_rates(filed), filed_contrasts(filed)
    names = dict(TEX.MODELS)
    out = []
    for ti, t in enumerate(TASKS):
        out.append(f"\\multicolumn{{7}}{{@{{}}l}}{{\\emph{{{t}}}}} \\\\")
        for m in MR.MODEL_ORDER:
            cells = [TEX.ci(rates[(m, t, a)]) for a in MR.ARMS]
            for name in MR.CONTRASTS:
                c = cons[(name, m, t)]
                cells.append(diff(c) + ("$^{\\dagger}$" if not_after_holm(c) else ""))
            out.append(" & ".join([names[model_name(m)], *cells]) + r" \\")
        if ti < len(TASKS) - 1:
            out.append(r"\addlinespace")
    return "\n".join(out) + "\n"


def write_tex(res: dict, filed: dict, tex: Path) -> None:
    tex.mkdir(parents=True, exist_ok=True)
    (tex / "rq1m_simulate.tex").write_text(TEX.rows(res["m2"]["overall"], lambda c: [
        TEX.ci(c["exact"]) + ("" if c["exact_known"] == c["n"]
                              else f"$^{{\\ddagger{c['n'] - c['exact_known']}}}$"),
        TEX.ci(c["states"]), TEX.ci(c["states_salvaged"]), f"${c['no_trace']}$ / ${c['n']}$",
        TEX.rho(c["rho_states"])]))
    (tex / "rq1m_solve.tex").write_text(TEX.rows(res["m3"]["corr"], lambda c: [
        TEX.ci(c["solved"]), TEX.rho(c["rho_len"]), TEX.rho(c["rho_obj"]),
        TEX.rho(c["rho_time"])]))
    (tex / "rq1m_planlen.tex").write_text(TEX.rows(res["m4"]["cells"], lambda c: [
        f"${c['n_valid']}$ / ${c['n_trials']}$", f"${c['mean_len']:.1f}$",
        f"${c['mean_ref_len']:.1f}$", f"${c['median_ratio']:.2f}$",
        f"${c['shorter']}$ / ${c['equal']}$ / ${c['longer']}$", f"${c['max_ratio']:.1f}$",
        (f"${c['same_len_as_tool_plan']}$ / ${c['with_tool_plan']}$"
         if c["with_tool_plan"] else "--")]))
    (tex / "rq1m_contrasts.tex").write_text(contrast_rows(filed))


# ------------------------------------------------------------------ the matched run
def matched_records(args, filed: dict, gt_cache: dict) -> list[dict]:
    """The 5,400 trials of the matched run as records of `rq1_metrics.rec`, loaded and
    graded by the frozen functions of `matched_run.py` in the order of its live mode:
    run tags, the six cell folders through the typed loader, the audit preconditions,
    the validator environment, the frozen grade, the registered grade."""
    design = MR.REGISTERED
    root = args.matched_root
    r2 = ",".join(m for m, tag in filed["run_tags"].items() if tag == MR.R2_TAG)
    tags, _found = MR.resolve_tags(root, design, r2)
    if tags != filed["run_tags"]:
        raise Halt(f"run tags {tags} are not those of the filed output")
    folders = MR.load_matched(root, design, tags)
    # Item 7 of the audit: the vLLM version from the serve logs; the tools repo commit
    # leaves no trace in the files, so the note recorded with the filed output is passed.
    MR.audit_matched(root, folders, args.serve_logs, filed["audit"].get("version_note"),
                     filed["audit"].get("tools_repo_note"))
    MR.validator_env(args)
    arms = MR.arm_rows(folders)
    verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
    recs = []
    for m in MR.MODEL_ORDER:
        for fo in MR.FOLDERS:
            rows = [r for arm in MR.ARMS if MR.ARM_FOLDER[arm] == fo for r in arms[m][arm]]
            pairs = M.frozen_grades(rows, verdict, gt_cache)
            frozen = {r.trial_key: g for r, g in pairs}
            trials = MR.grade_trials(pairs, verdict, gt_cache)
            for arm in MR.ARMS:
                if MR.ARM_FOLDER[arm] != fo:
                    continue
                for r in arms[m][arm]:
                    g = frozen[r.trial_key]
                    plan = None
                    if r.task == "solve":       # the plan the registered grade read
                        bp = RG.block_plan(r.response)
                        plan = bp[0] if bp is not None else g.plan
                    recs.append(R1.rec(
                        model_name(m), MR.ARM_REC[arm], r.task, r.domain, r.problem,
                        r.plan_label, r.variant, trials[r.trial_key].registered, None, plan,
                        r.response, [(c.name, c.arguments, c.result) for c in r.tool_calls]))
    return recs


def problem_facts(rows: list[dict], gt_cache: dict, domains_dir: Path) -> dict:
    facts = R1.problem_facts(rows, gt_cache, domains_dir)
    missing = sorted({(x["domain"], x["problem"]) for x in rows if x["task"] in TASKS}
                     - set(facts))
    if missing:
        raise Halt(f"no reference plan in the ground-truth cache for {missing[:5]}")
    if any(f["objects"] is None for f in facts.values()):
        raise Halt("a solvable problem has no readable (:objects ...) block")
    return facts


def measures(rows: list[dict], claude: list[dict], gt_cache: dict, facts: dict,
             facts_claude: dict) -> dict:
    """m2, m3 and m4 of the open-weight rows (line trace as one more candidate on
    simulate) joined with those of the Claude rows, scored as `rq1_metrics` scores them."""
    frozen_best = R1.best_state_score
    R1.best_state_score = RC.best_state_score_second
    try:
        m2 = R1.metric2(rows, gt_cache, facts)
    finally:
        R1.best_state_score = frozen_best
    m3, m4 = R1.metric3(rows, facts), R1.metric4(rows, facts)
    open_only = {"m2": {k: list(v) for k, v in m2.items()},
                 "m3": {"by_length": list(m3["by_length"]), "corr": list(m3["corr"])}}
    m2c = R1.metric2(claude, gt_cache, facts_claude)
    if (m2c["skipped_problems"], m2c["undetermined_problems"]) != (
            m2["skipped_problems"], m2["undetermined_problems"]):
        raise Halt("the two simulate passes leave out different problems")
    m3c, m4c = R1.metric3(claude, facts_claude), R1.metric4(claude, facts_claude)
    m2["overall"] += m2c["overall"]
    m2["cells"] += m2c["cells"]
    m3 = {"corr": m3["corr"] + m3c["corr"], "by_length": m3["by_length"] + m3c["by_length"],
          "hardness": m3["hardness"], "hardness_claude_rows": m3c["hardness"],
          "by_time_open_weight": m3["by_time"], "by_objects_open_weight": m3["by_objects"]}
    return {"m2": m2, "m3": m3, "m4": {"cells": m4["cells"] + m4c["cells"]},
            "open_only": open_only}


# ------------------------------------------------------------------ markdown
def render(res: dict) -> str:
    h = res["m3"]["hardness"]
    L = ["*Generated by `tools/reanalysis/rq1_matched_metrics.py`. RQ1 solve and simulate "
         "on the matched run: for the three open-weight models the no-tools, plain and "
         "steered rows are arms N, P and S of that run, right under its registered grade "
         f"(package hash `{res['matched_package_sha256'][:12]}...`); Claude rows as filed. "
         "Descriptive. Intervals are 95% domain-cluster bootstrap. Checked before writing: "
         f"the right count and the 300 trials of all {len(res['count_check'])} cells against "
         f"`out/matched_run.json`; {res['breakdown_cells_checked']} by-length and overall "
         "cells against its breakdowns and the two tables of `out/matched_run.md`, to the "
         f"printed decimal; {res['claude_cells_checked']} Claude cells against "
         "`out/rq1_control_metrics.json`.*", "",
         "#### Count check: right answers per cell, registered grade", "",
         md_table(["model", "task", "arm", "right here", "trials here", "right, filed",
                   "trials, filed"],
                  [[model_name(c["model"]), c["task"], c["arm"], c["right"], c["n"],
                    c["filed_right"], c["filed_n"]] for c in res["count_check"]]), "",
         "#### Solve: solved, and Spearman rho with hardness", "",
         f"Planner runtime of the open-weight rows: the median `solve_time` of the planner "
         f"calls of the matched run on the problem ({h['problems_timed']} problems timed, "
         f"{R1.f2(h['time_min_s'])} s to {R1.f2(h['time_max_s'])} s; thirds cut at "
         f"{R1.f2(h['time_cuts_s'][0])} s and {R1.f2(h['time_cuts_s'][1])} s). Of the Claude "
         f"rows: the planner calls of the rerun, as filed.", "",
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
    L += ["", f"#### Simulate ({res['problems'] - len(res['m2']['skipped_problems'])} problems; "
          f"left out: {', '.join(res['m2']['skipped_problems'])})", "",
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
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--marketplace", type=Path, required=True,
                    help="the pddl-copilot checkout at the registered commit")
    ap.add_argument("--matched-root", type=Path)
    ap.add_argument("--serve-logs", type=Path,
                    help="serve logs of the matched run (default: <matched root>/serve-logs)")
    ap.add_argument("--regrade-json", type=Path, default=HERE / "out" / "rq1_layout_regrade.json")
    ap.add_argument("--figs", type=Path, default=HERE / "out" / "figs")
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    args.matched_root = args.matched_root or args.results / MR.RUN_TAG
    args.serve_logs = args.serve_logs or args.matched_root / "serve-logs"
    if MR.package_sha256() != FROZEN:
        raise Halt("the matched run's frozen package changed")
    filed = read_filed(args.out / "matched_run.json")
    filed_md = (args.out / "matched_run.md").read_text()
    filed_control = json.loads((args.out / "rq1_control_metrics.json").read_text())

    # The rerun through its frozen package, the Claude rows and the problem facts they
    # are scored with: as rq1_control_metrics.main builds them.
    rerun_rows, gt_cache = R1.load_rerun(args)
    frontier, notes = R1.load_frontier(args)
    facts_claude = problem_facts(rerun_rows, gt_cache, args.domains_dir)
    claude = [r for r in frontier if r["task"] in TASKS]

    rows = matched_records(args, filed, gt_cache)
    counts = check_counts(rows, filed)
    facts = problem_facts(rows, gt_cache, args.domains_dir)

    res = measures(rows, claude, gt_cache, facts, facts_claude)
    open_only = res.pop("open_only")
    n_breakdown = check_breakdowns(open_only["m2"], open_only["m3"], filed, filed_md)
    n_claude = check_claude(res, filed_control)
    res = {"matched_package_sha256": FROZEN, "frontier_notes": notes,
           "reading": "registered grade of the matched run; the no-tools, plain and steered "
                      "rows of the open-weight models are its arms N, P and S; Claude rows "
                      "as filed",
           "count_check": counts, "breakdown_cells_checked": n_breakdown,
           "claude_cells_checked": n_claude, "problems": len(facts), **res}

    md = render(res)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq1_matched_metrics.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.out / "rq1_matched_metrics.md").write_text(md)
    write_tex(res, filed, args.out / "tex")

    # Figures: the functions of rq1_figures, written under the rq1m_ names.
    save = FIG.save
    FIG.save = lambda fig, out, name: save(fig, out, name.replace("rq1_", "rq1m_"))
    try:
        FIG.fig_simulate(res, args.figs)
        FIG.fig_solve(res, args.figs)
    finally:
        FIG.save = save
    print(f"checked {len(counts)} cells, {n_breakdown} breakdown cells, {n_claude} Claude cells")
    print(f"wrote {args.out}/rq1_matched_metrics.{{json,md}} and {args.out}/tex/rq1m_*.tex")
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Halt, M.Halt, R1.Halt, RC.Halt, MR.S.SchemaError, MR.C.RegisteredCheckFailed,
            MR.RUN.Halt) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
