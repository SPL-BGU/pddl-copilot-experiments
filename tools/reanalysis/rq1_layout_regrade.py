#!/usr/bin/env python3
"""RQ1 delivered rates on solve and simulate, read again with layout-tolerant readers
(post hoc, exploratory).

    .venv/bin/python -m tools.reanalysis.rq1_layout_regrade [--numbers] \
        [--results /abs/results] [--marketplace ../pddl-copilot]

Why. The frozen delivered grader reads a solve plan as JSON only when the whole
answer is the JSON object. Otherwise it collects every action-shaped line of the
answer, wherever it stands. An answer that reasons first, listing candidate steps,
and then gives its plan in a code block is therefore graded on the reasoning lines
and the plan together, or, when the plan is a JSON list and the reasoning has no
action-shaped line, on no plan at all. Most unaided solve answers of the delivered
rerun have that shape: the unaided system prompt points to a JSON schema the model
never received (`pddl_eval/prompts.py`, `WITHOUT_TOOLS_SYSTEM_BY_TASK`).

What this script does. It keeps every frozen grade and adds one reading beside it,
on the full delivered rerun (three open models, thinking off), for the unaided arm
(Part C) and for both tool arms (Part A), with the same reader on every arm.
Nothing is re-graded in place: the frozen column is recomputed with the frozen
functions and must equal the filed readout, or the script halts.

  solve      "last code block": when the answer has fenced code blocks and the LAST
             one holds a plan, that plan is the delivered plan and replaces the
             frozen reading, whether the frozen grade was right or wrong. A block
             holds a plan when (a) it parses as JSON and is a non-empty list of
             strings, or an object whose `plan` is such a list, or (b) every
             non-empty line of it is one action line (the frozen tolerant pattern,
             `tools.e2e_regrade._TOLERANT_ACTION_RE`). In (a) every string must
             be one parenthesised action. Any other answer keeps its frozen
             grade. A fence left open is not a block, so in an answer cut at the
             output cap inside a block the last CLOSED block is read, when there
             is one. The output counts the answers read this way that stopped at
             the cap.
  simulate   the RQ3 line reader beside the frozen grade
             (`rq3_context_pilot.line_reader_exact`): a trace written one JSON
             object per line counts when it equals the answer key exactly.

Both readers are lenient about layout only. A plan must still pass the validator
and a trace must still equal the answer key.

What the solve reading does not rescue. A final plan written as a list in prose,
with earlier action-shaped lines above it and no code block, is still graded by the
frozen reader on all those lines together. The layout-tolerant figure is therefore
a lower bound on the plans the answers hold. A block of action lines is lower-cased,
as the frozen line readers do; a JSON block keeps the model's capitals, as the
frozen JSON reader does, so only the "case folded" column treats the two alike.

Validator. The frozen readout graded plans with pddl-pyvalidator 0.1.5 behind the
pddl-validator plugin. Block plans with no stored verdict are validated here in
process with the same plugin server and the same release (the script halts on
another release), and before that the script checks that this route returns the
stored verdict for every plan the frozen grade used on these rows. Release 0.1.5
rejects a plan that writes a name with a capital letter (ISS-027). The column "case
folded" gives the reading with every deciding plan sent in lower case, which is
what a case-insensitive validator returns.

Contrast. "Tools minus unaided" is the readout's E2: the plain tool arm minus the
unaided arm, paired on the trial key (the two share their user prompts). The frozen
column must equal the filed E2 estimate.

Outputs (tools/reanalysis/out/): rq1_layout_regrade.json and .md, and
tex/rq1_layout_regrade.tex (the rows of the paper's solve table); with --numbers
the markdown is spliced into development/NUMBERS.md (tag RQ1-LAYOUT-REGRADE).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path

from pddl_eval.scoring import _parse_validation_verdict, strip_leaked_channel_prefix
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.e2e_regrade import _FENCED_BLOCK_RE, _TOLERANT_ACTION_RE, oracle_canon_for
from tools.reanalysis import iss027_common as C27
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq3_context_pilot as PILOT
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
TAG = "RQ1-LAYOUT-REGRADE"
TASKS = ("solve", "simulate")
ARMS = ("unaided", "plain", "steered")
ARM_WORDS = {"unaided": "no tools", "plain": "tools, plain", "steered": "tools, steered"}
JSON_BLOCK, LINES_BLOCK = "JSON plan in the last block", "action lines in the last block"
_ACTION = re.compile(r"\(\s*[A-Za-z][\w-]*(?:\s+[\w\-?@.]+)*\s*\)")   # as the frozen line patterns


# ------------------------------------------------------------------ readers
def block_plan(response: str) -> tuple[tuple[str, ...], str] | None:
    """The plan in the last fenced code block of an answer, and its kind, or None
    when the answer has no closed block or the last one does not hold a plan."""
    blocks = _FENCED_BLOCK_RE.findall(strip_leaked_channel_prefix(response or ""))
    if not blocks:
        return None
    last = blocks[-1]
    try:
        obj = json.loads(last)
    except (json.JSONDecodeError, ValueError):
        obj = None
    if isinstance(obj, dict):
        obj = obj.get("plan")
    if isinstance(obj, list):
        if obj and all(isinstance(x, str) and _ACTION.fullmatch(x.strip()) for x in obj):
            return tuple(" ".join(x.split()) for x in obj), JSON_BLOCK
        return None
    lines = [ln for ln in last.splitlines() if ln.strip()]
    if lines and all(_TOLERANT_ACTION_RE.match(ln) for ln in lines):
        plan = []
        for ln in lines:                      # as the frozen tolerant reader normalises
            inner = ln[ln.find("("):]
            inner = inner[: inner.find(")") + 1]
            plan.append(" ".join(inner.split()).lower())
        return tuple(plan), LINES_BLOCK
    return None


def lower(plan) -> tuple[str, ...]:
    return tuple(x.lower() for x in plan)


def arm_of(part: str, row) -> str:
    return "unaided" if part == "rerun_c" else row.arm


# ------------------------------------------------------------------ statistics
def paired_diff(a: list[bool], b: list[bool], doms: list[str]) -> dict:
    """b minus a over the same trials, in points, with the domain-cluster interval."""
    d = R1.boot([float(y) - float(x) for x, y in zip(a, b)], doms)
    d["wrong_to_right"] = sum((not x) and y for x, y in zip(a, b))
    d["right_to_wrong"] = sum(x and not y for x, y in zip(a, b))
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--marketplace", type=Path, default=REPO.parent / "pddl-copilot")
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    try:
        env = C27.environment(args.marketplace)
        bad = C27.check_environment(env)
        if bad:
            raise R1.Halt("; ".join(bad))
        cells, grades, gt_cache = R1.load_rerun_cells(args)
        stored = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
                  for e in json.loads(args.plan_verdicts.read_text())}
        from pddl_eval.domains import load_domains
        domains = load_domains(args.domains_dir)
        vs = C27.load_validator(args.marketplace)
        live: dict = {}

        async def verdict(d: str, p: str, plan: tuple[str, ...]) -> bool:
            """The harness's `_validate_model_plan`, in process, on release 0.1.5."""
            if not plan:
                return False
            key = (d, p, plan)
            if key not in live:
                raw = await C27.call_tool(vs, "validate_plan", {
                    "domain": domains[d]["domain"], "problem": domains[d]["problems"][p],
                    "plan": "\n".join(plan)})
                v = _parse_validation_verdict(raw)
                if v is None:
                    raise R1.Halt(f"validator gave no verdict for {d}/{p}: {str(raw)[:200]}")
                live[key] = v
            return live[key]

        rows = []                                    # (part, model, row, frozen grade)
        for part in ("rerun_c", "rerun_a"):
            for m in C.PART_A_MODELS:
                for r in cells[part][m].rows:
                    if r.task in TASKS:
                        rows.append((part, m, r, grades[(r.cell, r.trial_key)]))

        async def grade_all() -> tuple[dict, int, int]:
            # 1. the in-process route must return the stored verdict of every plan
            #    the frozen grade used on these rows
            checked = 0
            for _part, _m, r, g in rows:
                if r.task == "solve" and g.plan:
                    key = (r.domain, r.problem, tuple(g.plan))
                    if key in live:
                        continue
                    if await verdict(*key) != stored[key]:
                        raise R1.Halt(f"in-process validator disagrees with the stored verdict "
                                      f"for {key[:2]} ({len(key[2])} actions)")
                    checked += 1
            # 2. the tolerant readings
            out, new, new_plans = {}, 0, set()
            for part, m, r, g in rows:
                rec = {"frozen": bool(g.ok), "tolerant": bool(g.ok), "folded": bool(g.ok),
                       "kind": None, "same_plan": None, "cap": r.done_reason == "length"}
                if r.task == "solve":
                    bp = block_plan(r.response)
                    plan = tuple(g.plan) if g.plan else ()
                    if bp is not None:
                        plan, rec["kind"] = bp
                        rec["same_plan"] = plan == (tuple(g.plan) if g.plan else ())
                        if (r.domain, r.problem, plan) not in stored:
                            new += 1
                            new_plans.add((r.domain, r.problem, plan))
                        rec["tolerant"] = await verdict(r.domain, r.problem, plan)
                    rec["folded"] = (await verdict(r.domain, r.problem, lower(plan))
                                     if plan and C27.has_upper(list(plan)) else rec["tolerant"])
                else:
                    oracle = oracle_canon_for(gt_cache, {"domain_name": r.domain,
                                                         "problem_name": r.problem})
                    if not g.ok and PILOT.line_reader_exact(r.response, oracle):
                        rec["tolerant"] = rec["folded"] = True
                        rec["kind"] = "one JSON object per line"
                out[(part, m, r.task, r.trial_key)] = rec
            return out, checked, new, len(new_plans)

        recs, n_checked, n_new, n_new_plans = asyncio.run(grade_all())

        table = []
        for m in C.PART_A_MODELS:
            for task in TASKS:
                for arm in ARMS:
                    part = "rerun_c" if arm == "unaided" else "rerun_a"
                    sel = [(r, g, recs[(part, m, task, r.trial_key)]) for p, mm, r, g in rows
                           if p == part and mm == m and r.task == task and arm_of(p, r) == arm]
                    doms = [r.domain for r, _, _ in sel]
                    fz = [x["frozen"] for _, _, x in sel]
                    tl = [x["tolerant"] for _, _, x in sel]
                    fd = [x["folded"] for _, _, x in sel]
                    flips = Counter(f"{g.reason} ({g.extraction or 'no plan read'})"
                                    if task == "solve" else g.reason
                                    for _, g, x in sel if x["tolerant"] and not x["frozen"])
                    table.append({
                        "model": model_name(m), "tag": m, "task": task, "arm": arm, "n": len(sel),
                        "frozen_k": sum(fz), "frozen": R1.boot(fz, doms),
                        "tolerant_k": sum(tl), "tolerant": R1.boot(tl, doms),
                        "difference": paired_diff(fz, tl, doms),
                        "folded_k": sum(fd), "folded": R1.boot(fd, doms),
                        "kinds": dict(Counter(x["kind"] for _, _, x in sel if x["kind"])),
                        "block_same_plan_as_frozen": sum(x["same_plan"] is True for _, _, x in sel),
                        "at_output_cap": sum(x["cap"] for _, _, x in sel),
                        "decided_at_output_cap": sum(x["cap"] for _, _, x in sel if x["kind"]),
                        "turned_right_at_output_cap": sum(
                            x["cap"] for _, _, x in sel if x["tolerant"] and not x["frozen"]),
                        "wrong_to_right_by_frozen_reason": dict(sorted(
                            flips.items(), key=lambda kv: (-kv[1], kv[0]))),
                    })

        # E2: plain tool arm minus unaided, paired on the trial key
        readout = json.loads(args.readout_json.read_text())
        filed = {(e["model"], e["task"]): e for e in readout["e2"]}
        contrasts, bad = [], []
        for m in C.PART_A_MODELS:
            for task in TASKS:
                c_rows = {r.trial_key: recs[("rerun_c", m, task, r.trial_key)]
                          for p, mm, r, _ in rows if p == "rerun_c" and mm == m and r.task == task}
                a_rows = {r.trial_key: (r, recs[("rerun_a", m, task, r.trial_key)])
                          for p, mm, r, _ in rows if p == "rerun_a" and mm == m
                          and r.task == task and r.arm == "plain"}
                keys = sorted(set(c_rows) & set(a_rows))
                doms = [a_rows[k][0].domain for k in keys]
                e = {"model": model_name(m), "tag": m, "task": task, "n_pairs": len(keys)}
                for name in ("frozen", "tolerant", "folded"):
                    e[name] = R1.boot([float(a_rows[k][1][name]) - float(c_rows[k][name])
                                       for k in keys], doms)
                f = filed[(m, task)]
                if len(keys) != f["n_pairs"] or abs(e["frozen"]["est"] - f["delta"]) > 1e-9:
                    bad.append(f"E2 {m}/{task}: {e['frozen']['est']:.4f} over {len(keys)} pairs "
                               f"vs filed {f['delta']:.4f} over {f['n_pairs']}")
                e["filed_ci"] = [f["ci95"]["lo"], f["ci95"]["hi"]]
                contrasts.append(e)
        if bad:
            raise R1.Halt("the frozen contrast does not reproduce the readout:\n  "
                          + "\n  ".join(bad))
    except (R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    def kinds_text(c: dict) -> str:
        return "; ".join(f"{k} {v}" for k, v in sorted(c["kinds"].items())) or "–"

    L = [f"*Generated by `tools/reanalysis/rq1_layout_regrade.py`. **Post hoc and exploratory; "
         f"the frozen readout is the record and nothing here replaces it.** Delivered rerun, "
         f"three open models, thinking off, solve and simulate, all 100 problems, 300 trials "
         f"per cell. \"Frozen\" = the frozen delivered grade, recomputed with the frozen "
         f"functions (it equals the filed readout or the script halts). \"Layout-tolerant\" = "
         f"on solve, the plan in the last code block of the answer when that block holds a "
         f"plan (a JSON list of actions, an object with a `plan` list, or action lines only) "
         f"replaces the frozen reading, whichever way that moves the grade; on simulate, a "
         f"trace written one JSON object per line also counts when it equals the answer key. "
         f"The same reader on every arm. \"Difference\" = layout-tolerant minus frozen on the "
         f"same trials, in points. \"Case folded\" = layout-tolerant with every deciding plan "
         f"sent to the validator in lower case (ISS-027). Intervals are 95% domain-cluster "
         f"bootstrap. Validator: pddl-pyvalidator {env['pyval']} in process through the "
         f"plugin server at sibling commit `{env['marketplace_head'][:7]}`; it returned the "
         f"stored verdict for all {n_checked} plans of the frozen grade before any new plan "
         f"was read; answers whose block plan had no stored verdict: {n_new} "
         f"({n_new_plans} distinct plans). \"Stopped at the output cap\" counts, among the "
         f"answers the tolerant reader decides, those cut at the cap after their last closed "
         f"block, and how many of them turn right.*", ""]
    L.append("#### RQ1 layout re-grade: delivered right, frozen beside the layout-tolerant "
             "reading")
    L.append("")
    L.append(md_table(
        ["model", "task", "arm", "trials", "frozen (record)", "layout-tolerant",
         "difference (points)", "wrong to right / right to wrong", "case folded",
         "answers the tolerant reader decides", "of those, stopped at the output cap (turn right)"],
        [[c["model"], c["task"], ARM_WORDS[c["arm"]], c["n"],
          f"{c['frozen_k']} · {R1.cell(c['frozen'])}",
          f"{c['tolerant_k']} · {R1.cell(c['tolerant'])}", R1.diff_cell(c["difference"]),
          f"{c['difference']['wrong_to_right']} / {c['difference']['right_to_wrong']}",
          f"{c['folded_k']} · {R1.cell(c['folded'])}" if c["task"] == "solve" else "–",
          kinds_text(c),
          f"{c['decided_at_output_cap']} ({c['turned_right_at_output_cap']})"]
         for c in table]))
    L.append("")
    L.append("#### RQ1 layout re-grade: tools (plain prompt) minus no tools, paired on the "
             "trial key (the readout's E2)")
    L.append("")
    L.append(md_table(
        ["model", "task", "pairs", "frozen (equals the filed E2)", "layout-tolerant",
         "layout-tolerant, case folded"],
        [[e["model"], e["task"], e["n_pairs"], R1.diff_cell(e["frozen"]),
          R1.diff_cell(e["tolerant"]),
          R1.diff_cell(e["folded"]) if e["task"] == "solve" else "–"] for e in contrasts]))
    L.append("")
    L.append("#### RQ1 layout re-grade: the frozen grade of the answers the tolerant reading "
             "turns right")
    L.append("")
    L.append(md_table(
        ["model", "task", "arm", "turned right", "their frozen reason (how the frozen grader "
         "read the plan)"],
        [[c["model"], c["task"], ARM_WORDS[c["arm"]], c["difference"]["wrong_to_right"],
          "; ".join(f"{k} {v}" for k, v in c["wrong_to_right_by_frozen_reason"].items()) or "–"]
         for c in table if c["difference"]["wrong_to_right"]]))
    md = "\n".join(L) + "\n"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq1_layout_regrade.json").write_text(json.dumps(
        {"cells": table, "contrasts": contrasts, "environment": env,
         "stored_verdicts_reproduced": n_checked, "answers_with_new_block_plan": n_new,
         "distinct_new_block_plans": n_new_plans},
        indent=1) + "\n")
    (args.out / "rq1_layout_regrade.md").write_text(md)

    # tex rows of the paper's solve table (Table rq1-regrade): pasted, never edited by hand
    def tex_cell(b: dict, signed: bool = False) -> str:
        f = "+.1f" if signed else ".1f"
        return f"${b['est']:{f}}$ {{\\scriptsize$[{b['lo']:{f}},\\,{b['hi']:{f}}]$}}"

    paper_names = {"Gemma-26B": "Gemma-MoE-26B"}
    by = {(c["tag"], c["task"], c["arm"]): c for c in table}
    e2 = {(e["tag"], e["task"]): e for e in contrasts}
    tex = []
    for m in ("Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"):       # the order of Table rq1-solve
        u, t, d = by[(m, "solve", "unaided")], by[(m, "solve", "plain")], e2[(m, "solve")]
        tex.append(" & ".join([
            paper_names.get(u["model"], u["model"]),
            tex_cell(u["frozen"]), tex_cell(u["tolerant"]),
            tex_cell(t["frozen"]), tex_cell(t["tolerant"]),
            tex_cell(d["frozen"], signed=True), tex_cell(d["tolerant"], signed=True)]) + r" \\")
    (args.out / "tex").mkdir(exist_ok=True)
    (args.out / "tex" / "rq1_layout_regrade.tex").write_text("\n".join(tex) + "\n")
    print(md)
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
