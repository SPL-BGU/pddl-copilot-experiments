#!/usr/bin/env python3
"""Build the synthetic fixture of the matched-run analysis (freeze gate 4).

    python3 tests/fixtures/matched_run/build_fixture.py [OUT_DIR]

Writes (default: this directory) SYNTHETIC_FIXTURE, design.json, gt_cache.json,
plan_verdicts.json (the stored verdicts the rerun's frozen grade used),
route/plan_verdicts.json (the injected validator route), filed_readout.json,
filed_regrade.json and filed_control.json (what the earlier rows must reproduce),
domains/<track>/<domain>/<problem>.pddl (objects and tracks for the measures of section
6), matched/<6 cell folders> (trials, audit log, client settings, summary), rerun/<3 Part
A cells>, control/<3 cell B folders with their audit log> and serve_logs/.
`build_smoke(OUT)` writes a clean mini smoke of six folders under the smoke run tag,
with its own serve logs.

Everything is synthetic: 20 invented domains d01..d20 (d01 to d10 classical with a
reference plan of 2 actions, d11 to d20 numeric with one of 7), one delivered plan and
one trace for all of them. No row of any real corpus is read or copied.
tests/test_matched_run.py rebuilds into a temp dir and checks the committed files are
byte-identical.

Layout: 60 trials per model, task and arm, 3 per domain; 120 rows per N folder (wordings
v11 to v13), 240 per tools folder (v11 to v16). Every domain holds three trials of an
arm, in three "slots". d01 to d18 have one problem, p01, on the three wordings. d19 and
d20 have two problems, so that a pairing key without the problem would collide:

    d19: (p01, v11), (p02, v11), (p01, v12)
    d20: (p02, v12), (p01, v13), (p02, v13)

Each wording still has 20 rows per task and every domain 3 trials per arm, so the
bootstrap arithmetic of the test file holds. A steered trial is its plain trial plus 3.

Default row: right under every grade (solve: the plan as action lines; simulate: the
trace as one JSON object); a tools row calls the right tool once and the tool is right.
The planted deviations are PLANTS below; the hand-computed consequences are in the test
file. The answer texts are those of the control's fixture builder, imported.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from pddl_eval import control_prompts as CP  # noqa: E402
from pddl_eval.prompts import WITH_TOOLS_SYSTEM_BY_TASK  # noqa: E402


def _load(name: str, path: Path):
    """Both builders are called build_fixture.py; load by path under its own name."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


CBF = _load("control_prompt_fix_build_fixture",
            HERE.parent / "control_prompt_fix" / "build_fixture.py")

MODELS = dict(CBF.MODELS)
Q9, G, Q35 = "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"
TASKS = ("solve", "simulate")
PLAIN, STEERED = (11, 12, 13), (14, 15, 16)
DOMAINS = CBF.DOMAINS
CLASSICAL, NUMERIC = DOMAINS[:10], DOMAINS[10:]
SLOTS = {d: (("p01", 11), ("p01", 12), ("p01", 13)) for d in DOMAINS[:18]}
SLOTS["d19"] = (("p01", 11), ("p02", 11), ("p01", 12))
SLOTS["d20"] = (("p02", 12), ("p01", 13), ("p02", 13))
PROBLEMS = tuple((d, p) for d in DOMAINS for p in sorted({s[0] for s in SLOTS[d]}))
TOKENS = {"N": "no-tools-sysformat", "T": "tools_all_minimal"}
CAP = CBF.CAP
RUN_TAG, SMOKE_TAG, R2_TAG = "matched-run", "matched-run-smoke", "matched-run-r2"
CLUSTER = CBF.CLUSTER
# design.json: the problems that stand in for "the prompt's plan can differ from the
# cached key" (section 3). d20/p02 has two trials per arm, d20/p01 (not listed) one.
KEY_PLAN_DIFFERS = [["d02", "p01"], ["d20", "p02"]]

# ------------------------------------------------------------------ answers and references
PLAN, WRONG, CAPS, TRIED = CBF.PLAN, CBF.WRONG, CBF.CAPS, CBF.TRIED
TRAJ, ORACLE = CBF.TRAJ, CBF.ORACLE
ANSWERS = {
    **CBF.ANSWERS,
    # The whole answer is one JSON object with the plan in capitals and no code block:
    # the frozen reader takes it as written (invalid on release 0.1.5); in lower case it
    # is the valid plan.
    "caps_json": json.dumps({"plan": CAPS}),
}
STORAGE_TEXT = CBF.STORAGE_TEXT
REF_LONG = [f"(go l{i} l{i + 1})" for i in range(1, 7)] + ["(stop r)"]     # 7 actions
TRACE = json.dumps({"valid": True, "trajectory": ORACLE})


def ref_plan(dom: str) -> list[str]:
    """The reference plan of the ground-truth cache: 2 actions in d01..d10, 7 in d11..d20."""
    return PLAN if dom in CLASSICAL else REF_LONG


def right_planner(dom: str) -> str:
    return "classic_planner" if dom in CLASSICAL else "numeric_planner"


# ------------------------------------------------------------------ plants
# (model, task, group) -> {(domain, problem, wording): spec}. Groups: N, P, S (the matched
# run), B (cell B of the control), AP and AS (Part A of the rerun, plain and steered). A
# spec is an answer kind, or (kind, how). `how` for a tools row: "none" (no tool call),
# "classic" (the classic planner whatever the domain), "noroom" (the final turn refused:
# the prompt and the tool output filled the window; the answer is empty), "clipped" (the
# final turn ran out of a clipped allowance), "atcap" (the answer ended at the output cap
# with room), "cut" (no tool call; the answer stopped at the cap and was cut by storage).
# `how` for a no-tools row: "scoring" (the harness grader raised: a scoring-exception row
# that keeps its answer).
def _all(spec, wording):
    """One trial per domain: the slot of this wording (v11/v14 the first, v12/v15 the
    second, v13/v16 the third)."""
    i, off = (wording - 11) % 3, 3 if wording >= 14 else 0
    return {(d, SLOTS[d][i][0], SLOTS[d][i][1] + off): spec for d in DOMAINS}


def _some(spec, wording, domains):
    return {(d, "p01", wording): spec for d in domains}


D4 = DOMAINS[:4]
PLANTS = {
    # A. Qwen3.5-9B solve: N wrong on the second slot of every domain. d05 v12 is a
    # scoring-exception row (1 of 120, kept) whose stored answer is a right plan in a
    # code block: wrong under the registered and the frozen grade, read as right by the
    # descriptive second reading. S calls the classic planner on the second slot.
    (Q9, "solve", "N"): {**_all("wrong_lines", 12), ("d05", "p01", 12): ("json_block", "scoring")},
    (Q9, "solve", "B"): _all("wrong_lines", 12),
    (Q9, "solve", "S"): _all(("right", "classic"), 15),
    (Q9, "solve", "AS"): _all(("right", "classic"), 15),
    # B. Qwen3.5-9B simulate: N wrong on v11 in d01..d04; S wrong on v14 in d01..d04 with
    # no tool call (the pairing trap: v14 pairs with v11, so S minus N is 0 on every
    # trial); the d01 answer stopped at the cap and was cut by storage (accepted). The
    # earlier rows are all right.
    (Q9, "simulate", "N"): _some("trace_wrong", 11, D4),
    (Q9, "simulate", "S"): {**_some(("trace_wrong", "none"), 14, D4),
                            ("d01", "p01", 14): ("prose", "cut")},
    # C. Gemma solve: N ends the first slot with a JSON plan in a code block (the frozen
    # reader misses it); P ends it with a JSON plan in capitals in a code block (right
    # only in lower case).
    (G, "solve", "N"): _all("json_block", 11),
    (G, "solve", "B"): _all("json_block", 11),
    (G, "solve", "P"): _all("caps_block", 11),
    (G, "solve", "AP"): _all("caps_block", 11),
    # D. Gemma simulate: S wrong on v16 in d01..d04 although the tool was right: d01 and
    # d02 had no room for the final turn, d03 ran out of a clipped allowance, d04 gave a
    # wrong trace that ended at the output cap.
    **{(G, "simulate", g): {("d01", "p01", 16): ("trace", "noroom"),
                            ("d02", "p01", 16): ("trace", "noroom"),
                            ("d03", "p01", 16): ("trace_wrong", "clipped"),
                            ("d04", "p01", 16): ("trace_wrong", "atcap")} for g in ("S", "AS")},
    # E. Qwen3.6-35B solve: N has unread final answers on d01 (three wordings: 3 of 60,
    # exactly at the tripwire's threshold); P calls no tool on the third slot and is
    # still right; S answers the third slot with a bare JSON plan in capitals (the frozen
    # reader takes it; right only in lower case).
    (Q35, "solve", "N"): {("d01", "p01", v): "unread_solve" for v in PLAIN},
    (Q35, "solve", "P"): _all(("right", "none"), 13),
    (Q35, "solve", "AP"): _all(("right", "none"), 13),
    (Q35, "solve", "S"): _all("caps_json", 16),
    (Q35, "solve", "AS"): _all("caps_json", 16),
    # F. Qwen3.6-35B simulate: N writes the right trace one object per line on v11 in
    # d01..d04; Part A plain is wrong on d07 v12.
    (Q35, "simulate", "N"): _some("per_line", 11, D4),
    (Q35, "simulate", "B"): _some("per_line", 11, D4),
    (Q35, "simulate", "AP"): {("d07", "p01", 12): "trace_wrong"},
}
# The user text of this trial of the control's cell B differs from this run's (a
# difference the analysis reports beside K1 and does not halt on).
CONTROL_USER_DIFFERS = {(Q35, "simulate", "d07", "p01", 12)}


def spec_of(model, task, group, dom, prob, v):
    s = PLANTS.get((model, task, group), {}).get((dom, prob, v))
    if s is None:
        s = "right" if task == "solve" else "trace"
    return s if isinstance(s, tuple) else (s, "right")


# ------------------------------------------------------------------ rows
def tool_call(task, dom, tool):
    if task == "solve":
        name = "classic_planner" if tool == "classic" else right_planner(dom)
        return {"name": name, "arguments": {"domain": "(define)", "problem": "(define)"},
                "result": json.dumps({"plan": PLAN, "solve_time": 0.5})}
    return {"name": "get_state_transition",
            "arguments": {"domain": "(define)", "problem": "(define)",
                          "plan": "\n".join(ref_plan(dom))},
            "result": TRACE}


def make_row(model, task, dom, v, kind, with_tools=False, tool="right", prob="p01"):
    """One result record. No tools: the control builder's row. Tools: a row whose stored
    grade is the tool-verified one (right when a tool was called), whatever the answer."""
    if kind == "exception" or not with_tools:
        base = kind if kind in CBF.ANSWERS or kind in ("exception", "storage_cut") else "prose"
        row = CBF.make_row(model, task, dom, v, base, with_tools)
        row["problem_name"] = prob
        if base != kind:           # an answer kind only this builder has
            row["response"] = ANSWERS[kind]
        if tool == "scoring":      # runner.py "scoring error": the answer and tokens stay
            row.update(success=False, tool_selected=None, failure_reason="exception",
                       error="scoring error: boom", format_compliant=None)
        return row
    called = tool not in ("none", "cut")
    row = {
        "model": MODELS[model], "task": task, "domain_name": dom, "problem_name": prob,
        "prompt_variant": v, "with_tools": True, "success": called, "tool_selected": called,
        "format_compliant": None, "response": ANSWERS[kind],
        "response_truncated_by_storage": False, "thinking": "",
        "tool_calls": [tool_call(task, dom, tool)] if called else [],
        "tokens": {"prompt": 900, "completion": 80 if called else 40,
                   "turns": 2 if called else 1, "total_duration_ns": 1, "eval_duration_ns": 1},
        "duration_s": 1.0, "error": "", "tool_filter": "all", "prompt_style": "minimal",
        "failure_reason": "ok" if called else "tool_not_selected", "truncated": False,
        "done_reason": "stop", "think_truncated": None, "plan_label": "",
        "infra_failure": False}
    if tool in ("noroom", "clipped", "atcap", "cut"):
        row.update(done_reason="length", truncated=True)
    if tool == "noroom":
        row["response"] = ""
        row["tokens"]["ctx_no_room_turns"] = 1
    elif tool == "clipped":
        row["tokens"].update(completion=140, ctx_clipped_turns=1,
                             ctx_clip_last_turn_max_tokens=100,
                             ctx_clip_last_turn_prompt_tokens=16_000)
    elif tool == "atcap":
        row["tokens"]["completion"] = CAP[task] + 40
    elif tool == "cut":
        row.update(response=STORAGE_TEXT, response_truncated_by_storage=True)
        row["tokens"]["completion"] = CAP[task]
    return row


def group_rows(model, group, wordings, with_tools, plants=True):
    off = wordings[0] - 11
    rows = []
    for w in wordings:
        for task in TASKS:
            for dom in DOMAINS:
                for prob, v in SLOTS[dom]:
                    if v + off != w:
                        continue
                    kind, tool = spec_of(model, task, group, dom, prob, w) if plants else (
                        "right" if task == "solve" else "trace", "right")
                    rows.append(make_row(model, task, dom, w, kind, with_tools, tool, prob))
    return rows


def n_rows(model, group="N", plants=True):
    return group_rows(model, group, PLAIN, False, plants)


def tools_rows(model, plain="P", steered="S", plants=True):
    return (group_rows(model, plain, PLAIN, True, plants)
            + group_rows(model, steered, STEERED, True, plants))


key_of, write_trials, sha = CBF.key_of, CBF.write_trials, CBF.sha


def system_text(folder, task):
    if folder == "N":
        return CP.NO_TOOLS_SYSTEM_CONTROL["format-stated"][task]
    return WITH_TOOLS_SYSTEM_BY_TASK[task]


def user_text(r, differs=False):
    """The user message of a trial: a steered wording is its plain wording plus one
    sentence, so v11 to v13 are the same text in the N and the tools cell."""
    v = r["prompt_variant"]
    base = f"user prompt {r['task']} {r['domain_name']} {r['problem_name']} v{v - 3 if v > 13 else v}"
    return base + (" Use the tool." if v > 13 else "") + (" (another plan)" if differs else "")


def audit_line(folder, model, r, differs=False):
    text = system_text(folder, r["task"])
    return {"mode": "format-stated" if folder == "N" else "registered",
            "swapped": folder == "N", "system_sha256": sha(text),
            "user_sha256": sha(user_text(r, differs)), "model": MODELS[model],
            "has_tools": folder == "T"}


def write_audit(path: Path, folder, model, rows, differs=frozenset()):
    """One line per request, the shape of vllm_client._write_audit: one line for a
    no-tools trial, one line per turn of the tool loop for a tools trial."""
    seen = set()
    with (path / "system_prompt_audit.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            other = (model, r["task"], r["domain_name"], r["problem_name"],
                     r["prompt_variant"]) in differs
            for _turn in range(max(1, r["tokens"].get("turns", 1))):
                line = audit_line(folder, model, r, other)
                if line["system_sha256"] not in seen:
                    line["system_text"] = system_text(folder, r["task"])
                    seen.add(line["system_sha256"])
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")


def write_settings(path: Path, folder, model, job):
    s = {"think_mode_token": "off", "reasoning_effort": None, "store_reasoning": False,
         "cond": TOKENS[folder], "tool_call_id_style": "call", "max_model_len": 16384,
         "harmony_system_line": None, "hf_model": MODELS[model], "hf_revision": None,
         "slurm_job_id": job,
         "no_tools_system": "format-stated" if folder == "N" else "not-applicable-with-tools",
         "system_audit_log": f"{CLUSTER}/{path.name}/system_prompt_audit.jsonl",
         "reasoning_effort_sent": False}
    (path / "client_settings.json").write_text(json.dumps(s, indent=1) + "\n")


def write_summary(path: Path, folder, model):
    meta = {"host": "http://localhost:11500",
            "conditions": "no-tools" if folder == "N" else "tools",
            "models": [MODELS[model]], "tasks": list(TASKS), "num_variants": 6,
            "prompt_variants_active": list(PLAIN + STEERED), "include_no_tools_steered": False,
            "temperature": 0.0, "num_ctx": 16384, "num_ctx_thinking": 16384,
            "num_predict": None, "think": "off", "resumed_count": 0}
    if folder == "T":
        meta.update(tool_filter="all", prompt_style="minimal")
    (path / "summary_20261201_120000.json").write_text(
        json.dumps({"single_task": {}, "meta": meta}, indent=1) + "\n")


def folder(model, fo, tag):
    return f"slurm_vllm_{model}_off_{TOKENS[fo]}_{tag}"


# A request re-sent after a resume: the audit log of this N cell holds the line of its
# row at this index twice (section 7 item 5 allows it and counts it).
RESENT = {Q35: 5}
# A record half-written when a job was killed, left at the end of this tools cell's
# trials file: counted and skipped, as the frozen loader does.
TORN = {G}


def write_cell(root: Path, logs: Path, model, fo, tag, job, rows, resent=None, torn=False):
    d = root / folder(model, fo, tag)
    write_trials(d, rows)
    if torn:
        with (d / "trials.jsonl").open("a") as fh:
            fh.write('{"key": ["half-written\n')
    write_audit(d, fo, model, rows)
    if resent is not None:
        with (d / "system_prompt_audit.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(audit_line(fo, model, rows[resent]), ensure_ascii=False) + "\n")
    write_settings(d, fo, model, job)
    write_summary(d, fo, model)
    CBF.write_serve_log(logs, job, model)


# ------------------------------------------------------------------ filed records
# Hand-computed from PLANTS (60 trials per cell; see the test file): (n, frozen, second
# reading, case folded). Part A in the shape of tools/reanalysis/out/rq1_layout_regrade.json,
# cell B in the shape of the rates of tools/reanalysis/out/control_prompt_fix.json.
FILED_REGRADE = {
    (Q9, "solve", "plain"): (60, 60, 60, 60), (Q9, "solve", "steered"): (60, 60, 60, 60),
    (Q9, "simulate", "plain"): (60, 60, 60, 60), (Q9, "simulate", "steered"): (60, 60, 60, 60),
    (G, "solve", "plain"): (60, 40, 40, 60), (G, "solve", "steered"): (60, 60, 60, 60),
    (G, "simulate", "plain"): (60, 60, 60, 60), (G, "simulate", "steered"): (60, 56, 56, 56),
    (Q35, "solve", "plain"): (60, 60, 60, 60), (Q35, "solve", "steered"): (60, 40, 40, 60),
    (Q35, "simulate", "plain"): (60, 59, 59, 59), (Q35, "simulate", "steered"): (60, 60, 60, 60),
}
FILED_CONTROL_B = {
    (Q9, "solve"): (60, 40, 40, 40), (Q9, "simulate"): (60, 60, 60, 60),
    (G, "solve"): (60, 40, 60, 60), (G, "simulate"): (60, 60, 60, 60),
    (Q35, "solve"): (60, 60, 60, 60), (Q35, "simulate"): (60, 56, 60, 60),
}


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "SYNTHETIC_FIXTURE").write_text(
        "Synthetic fixture for tests/test_matched_run.py. Not experiment data.\n")
    design = {"per_task_arm": 60, "n_folder": 120, "tools_folder": 240, "per_wording": 40,
              "per_task_wording": 20, "k_domains": 20, "domains": list(DOMAINS),
              "key_plan_differs": KEY_PLAN_DIFFERS}
    (out / "design.json").write_text(json.dumps(design, indent=1, sort_keys=True) + "\n")
    gt: dict = {}
    for d, p in PROBLEMS:
        gt.setdefault(d, {})[p] = {"plan": ref_plan(d), "trace": TRACE}
        path = out / "domains" / ("classical" if d in CLASSICAL else "numeric") / d
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{p}.pddl").write_text(
            f"(define (problem {p}) (:domain {d})\n  (:objects r - robot l1 l2 l3 - place)\n"
            f"  (:init (at r l1)) (:goal (at r l2)))\n")
    (out / "gt_cache.json").write_text(json.dumps(gt, indent=1, sort_keys=True) + "\n")
    # Stored verdicts of the plans the frozen grade read on the Part A rows (the capitals
    # of the bare JSON plan among them); the route also knows the tried-step plan.
    stored = [{"domain": d, "problem": p, "plan": pl, "valid": ok} for d, p in PROBLEMS
              for pl, ok in ((PLAN, True), (WRONG, False), (CAPS, False))]
    (out / "plan_verdicts.json").write_text(json.dumps(stored, indent=1) + "\n")
    route = stored + [{"domain": d, "problem": p, "plan": TRIED, "valid": False}
                      for d, p in PROBLEMS]
    (out / "route").mkdir(exist_ok=True)
    (out / "route" / "plan_verdicts.json").write_text(json.dumps(route, indent=1) + "\n")
    job = 26000001
    for m in MODELS:
        write_cell(out / "matched", out / "serve_logs", m, "N", RUN_TAG, str(job), n_rows(m),
                   RESENT.get(m))
        write_cell(out / "matched", out / "serve_logs", m, "T", RUN_TAG, str(job + 1),
                   tools_rows(m), torn=m in TORN)
        job += 2
        b = out / "control" / f"slurm_vllm_{m}_off_no-tools-sysformat_control-promptfix"
        write_trials(b, n_rows(m, "B"))
        write_audit(b, "N", m, n_rows(m, "B"), CONTROL_USER_DIFFERS)
        write_trials(out / "rerun" / f"slurm_vllm_{m}_off_tools_all_minimal_delivered-rerun",
                     tools_rows(m, "AP", "AS"))
    e1 = [{"model": m, "task": t, "arm": arm, "delivered_k": fz, "n": n}
          for (m, t, arm), (n, fz, _tl, _fd) in sorted(FILED_REGRADE.items())]
    (out / "filed_readout.json").write_text(json.dumps(
        {"package_sha256": "fixture", "e1": e1}, indent=1) + "\n")
    cells = [{"tag": m, "task": t, "arm": arm, "n": n, "frozen_k": fz, "tolerant_k": tl,
              "folded_k": fd} for (m, t, arm), (n, fz, tl, fd) in sorted(FILED_REGRADE.items())]
    (out / "filed_regrade.json").write_text(json.dumps({"cells": cells}, indent=1) + "\n")
    rates = [{"model": m, "task": t, "cell": "B", "n": n, "frozen": {"right": fz},
              "second": {"right": sc}, "folded": {"right": fd}}
             for (m, t), (n, fz, sc, fd) in sorted(FILED_CONTROL_B.items())]
    (out / "filed_control.json").write_text(json.dumps(
        {"package_sha256": "fixture", "mode": "fixture", "rates": rates}, indent=1) + "\n")


def build_smoke(out: Path) -> None:
    """A clean mini smoke: every answer right, 120 and 240 rows, audits in order."""
    job = 27000001
    for m in MODELS:
        write_cell(out, out / "serve_logs", m, "N", SMOKE_TAG, str(job),
                   n_rows(m, plants=False))
        write_cell(out, out / "serve_logs", m, "T", SMOKE_TAG, str(job + 1),
                   tools_rows(m, plants=False))
        job += 2


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
