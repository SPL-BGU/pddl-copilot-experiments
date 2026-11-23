#!/usr/bin/env python3
"""Pilot: what does a JSON-schema constraint that takes effect do to the unaided answers?

    python -m tools.reanalysis.json_constraint_pilot [--numbers] [--marketplace ../pddl-copilot]

Post hoc and descriptive. The unaided arm of the main sweep and of the delivered
rerun was meant to decode under a per-task JSON schema. The request field the
client sent (`guided_json`) is dropped by vLLM 0.20.2, so the format was asked
for in the prompt only. The D1d probe of 2026-10-27 ran the same 480 unaided
trials of Qwen3.5-9B twice in one window, thinking off, the first problem of
every domain:

  prompt only   the request as the rerun sent it (`*_no-tools_d1d-probe`);
  constraint    the same request plus `structured_outputs={"json": schema}`,
                the field that binds (`*_no-tools-jsonbound_d1d-probe`).

Prompts, model, serving version, window and output cap are the same in both
cells. This script pairs the two cells on the trial key and grades every row
with the frozen delivered grader. Beside it, for the same trial keys, it prints
the frozen grade of the delivered rerun's unaided cell (a check that the probe's
prompt-only cell behaves like the rerun).

One reading is added beside the frozen grade and marked post hoc. The frozen
grader reads a validation verdict from a complete JSON answer or from a
`VERDICT:` line. A constrained answer that stops at the output cap inside its
`reason` field is neither, although its verdict is written at the start. The
column "verdict field read" also takes the verdict of such an answer from its
leading `"verdict"` field.

Rows cut by storage are refused by the frozen loader. The probe holds such rows
only where the answer also stopped at the output cap; they are graded on their
stored 65,536 characters and counted in the output.

Limits, stated with the table: one model; 60 to 120 trials per task from the
first problem of each of 20 domains; three wordings; nothing here was
registered. It is a pilot. The intervals are not adjusted for the five tasks.

Outputs (tools/reanalysis/out/): json_constraint_pilot.json, json_constraint_pilot.md,
tex/json_constraint_pilot.tex; with --numbers spliced into development/NUMBERS.md
(tag JSON-CONSTRAINT-PILOT).
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import re
import sys
from collections import Counter
from pathlib import Path

from pddl_eval.scoring import strip_leaked_channel_prefix
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.e2e_regrade import truth_for
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
MODEL = "Qwen3_5_9B"
TAG = "JSON-CONSTRAINT-PILOT"
PLAIN, BOUND = "prompt only", "constraint"
CELLS = ((PLAIN, f"slurm_vllm_{MODEL}_off_no-tools_d1d-probe"),
         (BOUND, f"slurm_vllm_{MODEL}_off_no-tools-jsonbound_d1d-probe"))
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
_VERDICT_FIELD = re.compile(r'\s*\{\s*"verdict"\s*:\s*"(VALID|INVALID)"')


def verdict_field(response: str) -> bool | None:
    """The verdict an answer opens with as a JSON field, complete or not.
    None when the answer does not begin with `{"verdict": "VALID"|"INVALID"`."""
    m = _VERDICT_FIELD.match(strip_leaked_channel_prefix(response or ""))
    return None if m is None else m.group(1) == "VALID"


def starts_json(response: str) -> bool:
    return strip_leaked_channel_prefix(response or "").lstrip().startswith("{")


def probe_rows(root: Path, cell: str) -> tuple[dict, set]:
    """One probe cell through the frozen loader: ({trial key: Row}, storage-cut keys).

    The frozen `schema.parse_row` reads every record with the registered Part C
    checks. It refuses a row whose answer was cut by storage; such a row is
    accepted here only when the answer also stopped at the output cap, read on
    its stored characters, and its key is returned so the count is reported."""
    spec = dataclasses.replace(S.spec_rerun_c(C.REGISTERED, MODEL), name=cell)
    rows, cut = {}, set()
    with (root / cell / "trials.jsonl").open() as fh:
        for i, ln in enumerate(fh, 1):
            if not ln.strip():
                continue
            obj = json.loads(ln)
            r = obj.get("result") or {}
            was_cut = r.get("response_truncated_by_storage") is True
            if was_cut:
                if r.get("done_reason") != "length":
                    raise R1.Halt(f"{cell}:{i}: a storage-cut answer that did not stop at "
                                  f"the output cap")
                obj = {"key": obj["key"], "result": {**r, "response_truncated_by_storage": False}}
            row = S.parse_row(obj, spec, f"{cell}:{i}")
            if row.infra_failure or row.is_exception:
                raise R1.Halt(f"{cell}:{i}: an infrastructure or exception row")
            if row.trial_key in rows:
                raise R1.Halt(f"{cell}:{i}: trial key {row.trial_key} twice")
            rows[row.trial_key] = row
            if was_cut:
                cut.add(row.trial_key)
    return rows, cut


def lenient_ok(row, grade) -> bool:
    """The frozen grade, except that a validation answer the frozen grader finds
    no verdict in is read from its leading `"verdict"` field when it has one."""
    if grade.ok or row.task not in G.VALIDATE_TASKS or grade.reason != "no_verdict_stated":
        return bool(grade.ok)
    v = verdict_field(row.response)
    if v is None:
        return False
    return v == truth_for({"task": row.task, "problem_name": row.problem,
                           "plan_label": row.plan_label})


def summarise(rows: list, grades: list) -> dict:
    """One cell of the table: counts and the domain-cluster interval of a set of rows."""
    doms = [r.domain for r in rows]
    return {
        "n": len(rows),
        "right": sum(bool(g.ok) for g in grades),
        "delivered": R1.boot([bool(g.ok) for g in grades], doms),
        "delivered_verdict_field": R1.boot([lenient_ok(r, g) for r, g in zip(rows, grades)], doms),
        "starts_json": sum(starts_json(r.response) for r in rows),
        "at_output_cap": sum(r.done_reason == "length" for r in rows),
        "mean_completion_tokens": (sum(r.tokens.completion for r in rows) / len(rows)
                                   if rows else None),
        "reasons": dict(sorted(Counter(g.reason for g in grades).items(),
                               key=lambda kv: (-kv[1], kv[0]))),
    }


def paired(rows_a: list, grades_a: list, rows_b: list, grades_b: list, lenient=False) -> dict:
    """Difference b minus a over the same trials, in points, with its interval."""
    if lenient:
        a = [lenient_ok(r, g) for r, g in zip(rows_a, grades_a)]
        b = [lenient_ok(r, g) for r, g in zip(rows_b, grades_b)]
    else:
        a, b = [bool(g.ok) for g in grades_a], [bool(g.ok) for g in grades_b]
    d = R1.boot([float(y) - float(x) for x, y in zip(a, b)], [r.domain for r in rows_a])
    d["lost"] = sum(x and not y for x, y in zip(a, b))
    d["gained"] = sum(y and not x for x, y in zip(a, b))
    return d


def reasons_text(d: dict) -> str:
    return "; ".join(f"{k} {v}" for k, v in d.items()) or "–"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--smoke-root", type=Path)
    ap.add_argument("--marketplace", type=Path, default=REPO.parent / "pddl-copilot")
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    smoke_root = args.smoke_root or args.results / "d1-smokes"
    try:
        cells, grades16, gt_cache = R1.load_rerun_cells(args)
        data, cuts = {}, {}
        for name, cell in CELLS:
            data[name], cuts[name] = probe_rows(smoke_root, cell)
        if set(data[PLAIN]) != set(data[BOUND]):
            raise R1.Halt("the two probe cells do not hold the same trial keys")
        keys = sorted(data[PLAIN])
        table = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
                 for e in json.loads(args.plan_verdicts.read_text())}
        need = set()
        for name, _ in CELLS:
            need |= G.solve_plans_to_validate(data[name].values())
        missing = need - set(table)
        if missing:
            table.update(asyncio.run(RUN.live_verdicts(missing, args.domains_dir,
                                                       args.marketplace)))
        graded = {name: {k: G.grade(data[name][k], gt_cache, table) for k in keys}
                  for name, _ in CELLS}
        rerun = {r.trial_key: r for r in cells["rerun_c"][MODEL].rows}

        out = []

        def block(label: str, ks: list) -> dict:
            ra, rb = [data[PLAIN][k] for k in ks], [data[BOUND][k] for k in ks]
            ga, gb = [graded[PLAIN][k] for k in ks], [graded[BOUND][k] for k in ks]
            anchor_keys = [k for k in ks if k in rerun]
            anchor_rows = [rerun[k] for k in anchor_keys]
            return {
                "task": ks[0][0], "label": label, "n": len(ks),
                "domains": len({k[1] for k in ks}),
                PLAIN: summarise(ra, ga), BOUND: summarise(rb, gb),
                "difference": paired(ra, ga, rb, gb),
                "difference_verdict_field": paired(ra, ga, rb, gb, lenient=True),
                "transitions": {f"{a} -> {b}": n for (a, b), n in sorted(
                    Counter((x.reason, y.reason) for x, y in zip(ga, gb)).items(),
                    key=lambda kv: (-kv[1], kv[0]))},
                "rerun_same_trials": summarise(
                    anchor_rows, [grades16[(r.cell, r.trial_key)] for r in anchor_rows]),
                "storage_cut": {n: sum(k in cuts[n] for k in ks) for n, _ in CELLS},
            }

        for task in TASKS:
            ks = [k for k in keys if k[0] == task]
            out.append(block("all", ks))
            if task == "validate_plan":
                for lab, name in (("v", "valid plans"), ("b", "broken plans")):
                    out.append(block(name, [k for k in ks if k[3].startswith(lab)]))
    except (R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    def task_name(c: dict) -> str:
        return c["task"] if c["label"] == "all" else f"{c['task']}, {c['label']}"

    n_cut = {n: len(cuts[n]) for n, _ in CELLS}
    L = [f"*Generated by `tools/reanalysis/json_constraint_pilot.py`. Post hoc pilot, "
         f"descriptive. {model_name(MODEL)}, unaided, thinking off, the first problem of each "
         f"domain, three wordings; the D1d probe of 2026-10-27, both cells run in one window "
         f"(jobs 23630577 and 23630578). \"Prompt only\" = the request as the rerun sent it "
         f"(the JSON schema field is dropped by the server). \"Constraint\" = the same request "
         f"with the schema sent in the field that binds. The two cells are paired on the "
         f"trial key ({len(keys)} trials) and every row is graded by the frozen delivered "
         f"grader. \"Difference\" = constraint minus prompt only, in points. Intervals are 95% "
         f"domain-cluster bootstrap, not adjusted for the five tasks. \"Verdict field read\" "
         f"is post hoc: a validation answer in which the frozen grader finds no verdict is "
         f"read from its leading `\"verdict\"` field when it has one (a constrained answer "
         f"that stops at the output cap inside its reason). \"Rerun, same trials\" = the "
         f"frozen grade of the delivered rerun's unaided cell on the same trial keys. One "
         f"model, the first problem of each of 20 domains, nothing registered. Answers cut by storage (all stopped at the "
         f"output cap; graded on the stored 65,536 characters): prompt only {n_cut[PLAIN]}, "
         f"constraint {n_cut[BOUND]}. Solve plans validated live for this table: "
         f"{len(missing)}.*", ""]
    L.append("#### JSON constraint pilot: delivered right, prompt only against a constraint "
             "that takes effect")
    L.append("")
    L.append(md_table(
        ["task", "trials", "answers that begin with `{` (prompt only / constraint)",
         "delivered right, prompt only", "delivered right, constraint", "difference (points)",
         "trials lost / gained", "rerun, same trials"],
        [[task_name(c), c["n"], f"{c[PLAIN]['starts_json']} / {c[BOUND]['starts_json']}",
          R1.cell(c[PLAIN]["delivered"]), R1.cell(c[BOUND]["delivered"]),
          R1.diff_cell(c["difference"]),
          f"{c['difference']['lost']} / {c['difference']['gained']}",
          f"{R1.cell(c['rerun_same_trials']['delivered'])} (n={c['rerun_same_trials']['n']})"]
         for c in out]))
    L.append("")
    L.append("#### JSON constraint pilot: why answers fail, and their length")
    L.append("")
    L.append(md_table(
        ["task", "cell", "trials", "stopped at the output cap", "mean answer tokens",
         "frozen grade reasons"],
        [[task_name(c), n, c[n]["n"], c[n]["at_output_cap"],
          f"{c[n]['mean_completion_tokens']:.0f}", reasons_text(c[n]["reasons"])]
         for c in out for n, _ in CELLS]))
    L.append("")
    L.append("#### JSON constraint pilot: validation tasks with the verdict field read "
             "(post hoc)")
    L.append("")
    L.append(md_table(
        ["task", "trials", "prompt only", "constraint, frozen grade",
         "constraint, verdict field read", "difference with the verdict field read (points)"],
        [[task_name(c), c["n"], R1.cell(c[PLAIN]["delivered_verdict_field"]),
          R1.cell(c[BOUND]["delivered"]), R1.cell(c[BOUND]["delivered_verdict_field"]),
          R1.diff_cell(c["difference_verdict_field"])]
         for c in out if c["task"] in G.VALIDATE_TASKS]))
    L.append("")
    L.append("#### JSON constraint pilot: how each solve and simulate trial moved "
             "(prompt only -> constraint)")
    L.append("")
    L.append(md_table(["task", "frozen grade reason, prompt only -> constraint", "trials"],
                      [[c["task"], k, v] for c in out if c["task"] in ("solve", "simulate")
                       for k, v in c["transitions"].items()]))
    md = "\n".join(L) + "\n"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "json_constraint_pilot.json").write_text(json.dumps(
        {"model": model_name(MODEL), "trials": len(keys), "cells": out,
         "storage_cut": n_cut, "live_validated": len(missing)}, indent=1) + "\n")
    (args.out / "json_constraint_pilot.md").write_text(md)

    def tex_cell(b: dict, signed=False) -> str:
        f = "+.1f" if signed else ".1f"
        return (f"${b['est']:{f}}$ {{\\scriptsize$[{b['lo']:{f}},\\,{b['hi']:{f}}]$}}"
                .replace("-", "{-}"))

    tex = []
    for c in out:
        name = (f"\\emph{{{c['task'].replace('_', chr(92) + '_')}}}" if c["label"] == "all"
                else f"\\quad {c['label']}")
        tex.append(" & ".join([name, f"${c['n']}$", tex_cell(c[PLAIN]["delivered"]),
                               tex_cell(c[BOUND]["delivered"]),
                               tex_cell(c["difference"], signed=True)]) + r" \\")
    (args.out / "tex").mkdir(exist_ok=True)
    (args.out / "tex" / "json_constraint_pilot.tex").write_text("\n".join(tex) + "\n")
    print(md)
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
