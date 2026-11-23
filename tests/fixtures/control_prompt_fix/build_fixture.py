#!/usr/bin/env python3
"""Build the synthetic fixture of the control-prompt analysis (freeze gate 4).

    python3 tests/fixtures/control_prompt_fix/build_fixture.py [OUT_DIR]

Writes (default: this directory) SYNTHETIC_FIXTURE, design.json, gt_cache.json,
plan_verdicts.json (the stored verdicts the rerun's frozen grade used),
route/plan_verdicts.json (the injected validator route), filed_readout.json and
filed_regrade.json (what the rerun's rows must reproduce), control/<9 cell
folders> (trials, audit log, client settings, summary), rerun/<3 Part C and 3
Part A cells> and serve_logs/. `build_smoke(OUT)` writes a clean mini smoke of
nine folders under the smoke run tag, with its own serve logs.

Everything is synthetic: 20 invented domains d01..d20 with one problem p01
each, one plan and one trace for all of them. No row of any real corpus is
read or copied. tests/test_control_prompt_fix.py rebuilds into a temp dir and
checks the committed files are byte-identical.

Layout: the smoke layout (20 domains, one problem, three wordings, two tasks):
60 trials per model, task and cell; 120 rows per cell folder.

Default row: right under every reading (solve: the plan as action lines;
simulate: the trace as one JSON object). The planted deviations are PLANTS
below; the hand-computed consequences are in the test file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from pddl_eval import control_prompts as CP  # noqa: E402
from pddl_eval.prompts import WITHOUT_TOOLS_SYSTEM_BY_TASK  # noqa: E402

MODELS = {
    "Qwen3_5_9B": "Qwen/Qwen3.5-9B",
    "gemma4_26b-a4b": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
    "qwen3_6_35b": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
}
Q9, G, Q35 = "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"
TASKS = ("solve", "simulate")
WORDINGS = (11, 12, 13)
DOMAINS = tuple(f"d{i:02d}" for i in range(1, 21))
CELLS = ("O", "A", "B")
WRAPPER = {"O": "registered", "A": "no-pointer", "B": "format-stated"}
TOKENS = {"O": "no-tools", "A": "no-tools-syspointer-off", "B": "no-tools-sysformat"}
CAP = {"solve": 8192, "simulate": 6144}
RUN_TAG, SMOKE_TAG = "control-promptfix", "control-promptfix-smoke"
CLUSTER = "/home/omereliy/pddl-copilot-experiments/results"

# ------------------------------------------------------------------ answers
PLAN = ["(go l1 l2)", "(stop r)"]          # valid in every domain
WRONG = ["(go l1 l3)"]                     # invalid
CAPS = ["(Go L1 L2)", "(Stop R)"]          # invalid on release 0.1.5; lower case is PLAN
TRIED = ["(go l1 l3)", "(go l1 l2)", "(stop r)"]   # a tried step read with the final plan
TRAJ = [{"step": 0, "action": "", "state": {"boolean": ["(at r l1)"], "numeric": {}}},
        {"step": 1, "action": "(go l1 l2)", "state": {"boolean": ["(at r l2)"], "numeric": {}}}]
TRAJ_WRONG = [TRAJ[0], {"step": 1, "action": "(go l1 l2)",
                        "state": {"boolean": ["(at r l2)", "(broken r)"], "numeric": {}}}]
ORACLE = [{"step": 0, "action": None, "boolean_fluents": {"at(r,l1)": True},
           "numeric_fluents": {}},
          {"step": 1, "action": "(go l1 l2)", "boolean_fluents": {"at(r,l2)": True},
           "numeric_fluents": {}}]
FENCE = "```"
ANSWERS = {
    # solve
    "right": "\n".join(PLAN),
    # the frozen reader misses a JSON plan behind prose (frozen wrong, second right)
    "json_block": ("I move the robot from l1 to l2, then stop.\n" + FENCE + "json\n"
                   + json.dumps({"plan": PLAN}) + "\n" + FENCE),
    "wrong_lines": "\n".join(WRONG),
    # a wrong plan in a JSON block (read by the second reading, wrong both ways)
    "wrong_block": "Plan:\n" + FENCE + "json\n" + json.dumps(WRONG) + "\n" + FENCE,
    # unread final answer, solve: a tried step, then the final plan as action lines
    # with no block; the frozen reader takes all action lines together (invalid)
    "unread_solve": "(go l1 l3)\nNo, that fails.\n" + "\n".join(PLAN),
    # a JSON plan with capitals in the last block (second wrong, case folded right)
    "caps_block": "Here is the plan.\n" + FENCE + "json\n" + json.dumps(CAPS) + "\n" + FENCE,
    # right action lines, then a wrong JSON plan in the last block (right to wrong)
    "right_to_wrong": ("\n".join(PLAN) + "\n\nA shorter plan:\n" + FENCE + "json\n"
                       + json.dumps(WRONG) + "\n" + FENCE),
    # a block of action lines (both readings read the same plan)
    "lines_block": "Plan:\n" + FENCE + "\n" + "\n".join(PLAN) + "\n" + FENCE,
    # a fence left open at the output cap (not a block; the frozen grade stays)
    "unclosed": "Thinking about the goal.\n" + FENCE + "json\n" + json.dumps({"plan": PLAN})[:-2],
    "prose": "I could not find a plan for this problem.",
    # simulate
    "trace": json.dumps({"trajectory": TRAJ}),
    "trace_wrong": json.dumps({"trajectory": TRAJ_WRONG}),
    "per_line": "\n".join(json.dumps(s) for s in TRAJ),
    "per_line_wrong": "\n".join(json.dumps(s) for s in TRAJ_WRONG),
    # unread final answer, simulate: prose, then the right trace on its last line
    # (neither reader reads it: not one JSON value, and one line is no trace)
    "unread_sim": "The final trajectory is:\n" + json.dumps({"trajectory": TRAJ}),
}
# Answers the frozen grade counts right (for the stored online grade fields only).
STORED_OK = {"right", "right_to_wrong", "lines_block", "trace"}
AT_CAP = {"unclosed", "storage_cut"}
STORAGE_TEXT = ("I am still thinking about where the robot should go next. " * 1200)[:65_536]


# ------------------------------------------------------------------ plants
# (model, task, cell) -> {(domain, wording): answer}. Cells: O, A, B (control),
# C (Part C of the rerun), P (Part A of the rerun, plain wording).
def _all(kind, wording, domains=DOMAINS):
    return {(d, wording): kind for d in domains}


SPECIAL_Q9_SOLVE = {("d10", 13): "caps_block", ("d11", 13): "right_to_wrong",
                    ("d12", 13): "lines_block", ("d13", 13): "unclosed"}
PLANTS = {
    # Gemma solve: O, B and Part C end v11 with a JSON plan in a code block.
    (G, "solve", "O"): _all("json_block", 11),
    (G, "solve", "B"): _all("json_block", 11),
    (G, "solve", "C"): _all("json_block", 11),
    # Gemma simulate: O and Part C give a wrong trace on v11; in O, d05 v11 is a
    # harness exception row (1 of 120, kept and graded as it is) and d01..d03 v11
    # are unread final answers (3 of 60: exactly the fourth tripwire's threshold).
    (G, "simulate", "O"): {**_all("trace_wrong", 11), ("d05", 11): "exception",
                           **_all("unread_sim", 11, DOMAINS[:3])},
    (G, "simulate", "C"): _all("trace_wrong", 11),
    # Qwen3.5-9B solve: the four layout plants in every cell; A wrong on v12.
    (Q9, "solve", "O"): dict(SPECIAL_Q9_SOLVE),
    (Q9, "solve", "A"): {**_all("wrong_block", 12), **SPECIAL_Q9_SOLVE},
    (Q9, "solve", "B"): dict(SPECIAL_Q9_SOLVE),
    (Q9, "solve", "C"): dict(SPECIAL_Q9_SOLVE),
    (Q9, "solve", "P"): dict(SPECIAL_Q9_SOLVE),
    # Qwen3.5-9B simulate: one wrong trace in O and Part C (d01 v11); a wrong
    # trace written one object per line in every cell (d20 v13).
    (Q9, "simulate", "O"): {("d01", 11): "trace_wrong", ("d20", 13): "per_line_wrong"},
    (Q9, "simulate", "A"): {("d20", 13): "per_line_wrong"},
    (Q9, "simulate", "B"): {("d20", 13): "per_line_wrong"},
    (Q9, "simulate", "C"): {("d01", 11): "trace_wrong", ("d20", 13): "per_line_wrong"},
    (Q9, "simulate", "P"): {("d20", 13): "per_line_wrong"},
    # Qwen3.6-35B solve: O has no plan on d01 (v11 is cut by storage at the
    # output cap: accepted and counted); Part A wrong on v13.
    # d01 v12 is an unread final answer.
    (Q35, "solve", "O"): {("d01", 11): "storage_cut", ("d01", 12): "unread_solve",
                          ("d01", 13): "prose"},
    (Q35, "solve", "P"): _all("wrong_lines", 13),
    # Qwen3.6-35B simulate: O and Part C write the right trace one object per line
    # on d01..d04 v11.
    (Q35, "simulate", "O"): _all("per_line", 11, DOMAINS[:4]),
    (Q35, "simulate", "C"): _all("per_line", 11, DOMAINS[:4]),
}


def answer_of(model, task, cell, dom, v):
    kind = PLANTS.get((model, task, cell), {}).get((dom, v))
    return kind or ("right" if task == "solve" else "trace")


# ------------------------------------------------------------------ rows
def tokens(task, kind):
    if kind == "exception":
        return {}
    done_at_cap = kind in AT_CAP
    return {"prompt": 900, "completion": CAP[task] if done_at_cap else 40, "turns": 1,
            "total_duration_ns": 1, "eval_duration_ns": 1}


def make_row(model, task, dom, v, kind, with_tools=False):
    if kind == "exception":
        return {
            "model": MODELS[model], "task": task, "domain_name": dom, "problem_name": "p01",
            "prompt_variant": v, "with_tools": with_tools, "success": False,
            "tool_selected": None, "format_compliant": None, "response": "",
            "response_truncated_by_storage": False, "thinking": "", "tool_calls": [],
            "tokens": {}, "duration_s": 1.0, "error": "boom: the server raised",
            "tool_filter": "all", "prompt_style": "minimal", "failure_reason": "exception",
            "truncated": False, "done_reason": "", "think_truncated": None, "plan_label": "",
            "infra_failure": False}
    ok = kind in STORED_OK
    at_cap = kind in AT_CAP
    resp = STORAGE_TEXT if kind == "storage_cut" else ANSWERS[kind]
    fc = None
    if task == "simulate" and not with_tools:
        fc = kind in ("trace", "trace_wrong")
    return {
        "model": MODELS[model], "task": task, "domain_name": dom, "problem_name": "p01",
        "prompt_variant": v, "with_tools": with_tools, "success": ok,
        "tool_selected": True if with_tools else None, "format_compliant": fc,
        "response": resp, "response_truncated_by_storage": kind == "storage_cut",
        "thinking": "",
        "tool_calls": ([{"name": "classic_planner" if task == "solve" else
                         "get_state_transition", "arguments": {"domain": "(define)"},
                         "result": "{}"}] if with_tools else []),
        "tokens": {**tokens(task, kind), **({"turns": 2} if with_tools else {})},
        "duration_s": 1.0, "error": "", "tool_filter": "all", "prompt_style": "minimal",
        "failure_reason": "ok" if ok else ("format_parse_fail" if task == "solve"
                                           else "result_mismatch"),
        "truncated": at_cap, "done_reason": "length" if at_cap else "stop",
        "think_truncated": None, "plan_label": "", "infra_failure": False}


def cell_rows(model, cell, with_tools=False, plants=True):
    rows = []
    for v in WORDINGS:
        for task in TASKS:
            for dom in DOMAINS:
                kind = answer_of(model, task, cell, dom, v) if plants else (
                    "right" if task == "solve" else "trace")
                rows.append(make_row(model, task, dom, v, kind, with_tools))
    return rows


def key_of(r):
    return [r["model"], r["task"], r["domain_name"], r["problem_name"], r["plan_label"],
            r["prompt_variant"], r["with_tools"], "off", r["tool_filter"], r["prompt_style"]]


def write_trials(path: Path, rows):
    path.mkdir(parents=True, exist_ok=True)
    with (path / "trials.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps({"key": key_of(r), "result": r}) + "\n")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def system_text(cell, task):
    if cell == "O":
        return WITHOUT_TOOLS_SYSTEM_BY_TASK[task]
    return CP.NO_TOOLS_SYSTEM_CONTROL[WRAPPER[cell]][task]


def user_text(r):
    return f"user prompt {r['task']} {r['domain_name']} {r['problem_name']} v{r['prompt_variant']}"


def write_audit(path: Path, model, cell, rows):
    """One line per chat call, the shape of vllm_client._write_audit."""
    seen = set()
    with (path / "system_prompt_audit.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            text = system_text(cell, r["task"])
            line = {"mode": WRAPPER[cell], "swapped": cell != "O", "system_sha256": sha(text),
                    "user_sha256": sha(user_text(r)), "model": MODELS[model],
                    "has_tools": False}
            if sha(text) not in seen:
                line["system_text"] = text
                seen.add(sha(text))
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")


def write_settings(path: Path, model, cell, job):
    """The keys cluster-experimenting/reasoning_settings.py write-settings records."""
    s = {"think_mode_token": "off", "reasoning_effort": None, "store_reasoning": False,
         "cond": TOKENS[cell], "tool_call_id_style": "call", "max_model_len": 16384,
         "harmony_system_line": None, "hf_model": MODELS[model], "hf_revision": None,
         "slurm_job_id": job, "no_tools_system": WRAPPER[cell],
         "system_audit_log": f"{CLUSTER}/{path.name}/system_prompt_audit.jsonl",
         "reasoning_effort_sent": False}
    (path / "client_settings.json").write_text(json.dumps(s, indent=1) + "\n")


def write_summary(path: Path, model):
    meta = {"host": "http://localhost:11500", "conditions": "no-tools",
            "models": [MODELS[model]], "tasks": list(TASKS), "num_variants": 3,
            "prompt_variants_active": list(WORDINGS), "include_no_tools_steered": False,
            "temperature": 0.0, "num_ctx": 16384, "num_ctx_thinking": 16384,
            "num_predict": None, "think": "off", "resumed_count": 0}
    (path / "summary_20261127_120000.json").write_text(
        json.dumps({"single_task": {}, "meta": meta}, indent=1) + "\n")


def write_serve_log(logs: Path, job, model):
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{job}-vllm-{model}.log").write_text(
        f"INFO 11-27 12:00:00 [core.py:93] Initializing a V1 LLM engine (v0.20.2) with "
        f"config: model='{MODELS[model]}', max_seq_len=16384\n"
        f"INFO 11-27 12:01:00 [api_server.py:1] Starting vLLM server on http://0.0.0.0:11500\n")


def folder(model, cell, tag):
    return f"slurm_vllm_{model}_off_{TOKENS[cell]}_{tag}"


# A request re-sent after a resume: the audit log of this cell holds the line of
# its row at this index twice (section 7 item 5 allows it and counts it).
RESENT = {(Q35, "A"): 5}


def write_cell(root: Path, logs: Path, model, cell, tag, job, rows, resent=None):
    d = root / folder(model, cell, tag)
    write_trials(d, rows)
    write_audit(d, model, cell, rows)
    if resent is not None:
        r = rows[resent]
        line = {"mode": WRAPPER[cell], "swapped": cell != "O",
                "system_sha256": sha(system_text(cell, r["task"])),
                "user_sha256": sha(user_text(r)), "model": MODELS[model], "has_tools": False}
        with (d / "system_prompt_audit.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    write_settings(d, model, cell, job)
    write_summary(d, model)
    write_serve_log(logs, job, model)


# ------------------------------------------------------------------ filed records
# Hand-computed from PLANTS (60 trials per cell; see the test file): (n, frozen,
# second reading, case folded) of the rerun's rows, the shape of
# tools/reanalysis/out/rq1_layout_regrade.json.
FILED_REGRADE = {
    (G, "solve", "unaided"): (60, 40, 60, 60), (G, "solve", "plain"): (60, 60, 60, 60),
    (G, "simulate", "unaided"): (60, 40, 40, 40), (G, "simulate", "plain"): (60, 60, 60, 60),
    (Q9, "solve", "unaided"): (60, 58, 57, 58), (Q9, "solve", "plain"): (60, 58, 57, 58),
    (Q9, "simulate", "unaided"): (60, 58, 58, 58), (Q9, "simulate", "plain"): (60, 59, 59, 59),
    (Q35, "solve", "unaided"): (60, 60, 60, 60), (Q35, "solve", "plain"): (60, 40, 40, 40),
    (Q35, "simulate", "unaided"): (60, 56, 60, 60), (Q35, "simulate", "plain"): (60, 60, 60, 60),
}


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "SYNTHETIC_FIXTURE").write_text(
        "Synthetic fixture for tests/test_control_prompt_fix.py. Not experiment data.\n")
    design = {"per_task_cell": 60, "per_folder": 120, "per_wording": 40,
              "per_task_wording": 20, "k_domains": 20, "domains": list(DOMAINS)}
    (out / "design.json").write_text(json.dumps(design, indent=1, sort_keys=True) + "\n")
    gt = {d: {"p01": {"trace": json.dumps({"valid": True, "trajectory": ORACLE})}}
          for d in DOMAINS}
    (out / "gt_cache.json").write_text(json.dumps(gt, indent=1, sort_keys=True) + "\n")
    stored = [e for d in DOMAINS for e in (
        {"domain": d, "problem": "p01", "plan": PLAN, "valid": True},
        {"domain": d, "problem": "p01", "plan": WRONG, "valid": False})]
    (out / "plan_verdicts.json").write_text(json.dumps(stored, indent=1) + "\n")
    route = stored + [{"domain": d, "problem": "p01", "plan": pl, "valid": False}
                      for d in DOMAINS for pl in (CAPS, TRIED)]
    (out / "route").mkdir(exist_ok=True)
    (out / "route" / "plan_verdicts.json").write_text(json.dumps(route, indent=1) + "\n")
    job = 24000001
    for m in MODELS:
        for cell in CELLS:
            write_cell(out / "control", out / "serve_logs", m, cell, RUN_TAG, str(job),
                       cell_rows(m, cell), RESENT.get((m, cell)))
            job += 1
        write_trials(out / "rerun" / f"slurm_vllm_{m}_off_no-tools_delivered-rerun",
                     cell_rows(m, "C"))
        write_trials(out / "rerun" / f"slurm_vllm_{m}_off_tools_all_minimal_delivered-rerun",
                     cell_rows(m, "P", with_tools=True))
    e1, e2 = [], []
    for (m, t, arm), (n, fz, _tl, _fd) in sorted(FILED_REGRADE.items()):
        if arm == "plain":
            e1.append({"model": m, "task": t, "arm": "plain", "delivered_k": fz, "n": n})
        else:
            e2.append({"model": m, "task": t, "a_pct": 100 * fz / n})
    (out / "filed_readout.json").write_text(json.dumps(
        {"package_sha256": "fixture", "e1": e1, "e2": e2}, indent=1) + "\n")
    cells = [{"tag": m, "task": t, "arm": arm, "n": n, "frozen_k": fz, "tolerant_k": tl,
              "folded_k": fd} for (m, t, arm), (n, fz, tl, fd) in sorted(FILED_REGRADE.items())]
    (out / "filed_regrade.json").write_text(json.dumps({"cells": cells}, indent=1) + "\n")


def build_smoke(out: Path) -> None:
    """A clean mini smoke: every answer right, 120 rows per folder, audits in order."""
    job = 25000001
    for m in MODELS:
        for cell in CELLS:
            write_cell(out, out / "serve_logs", m, cell, SMOKE_TAG, str(job),
                       cell_rows(m, cell, plants=False))
            job += 1


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
