#!/usr/bin/env python3
"""Build the synthetic delivered-rerun fixture (freeze gate 4).

    python3 tests/fixtures/delivered_rerun/build_fixture.py [OUT_DIR]

Writes (default: this directory) design.json, gt_cache.json,
plan_verdicts.json, rerun/SYNTHETIC_FIXTURE, rerun/<4 cells>/trials.jsonl and
canonical/<6 cells>/trials.jsonl. Everything is synthetic: two invented
domains `dA`, `dB`, one problem each, invented plans and trajectories. No row
of any real corpus is read or copied. The committed files are this script's
output; tests/test_delivered_rerun_analysis.py rebuilds into a temp dir and
checks they are byte-identical.

Layout per Part A cell (72 rows = 6 variants x 12):
  solve            (dA,p01) (dB,p01)                          2 per variant
  validate_domain  (dA,p01)=VALID (dB,domain_neg)=INVALID     2
  validate_problem (dA,p01)=VALID (dB,n01)=INVALID            2
  validate_plan    (dA,p01,v1) (dA,p01,b1) (dB,p01,v1) (dB,p01,b1)   4
  simulate         (dA,p01) (dB,p01)                          2
Part B: Gemma validate_plan only, 24 rows. Part C (no tools, full storage) and
canonical no-tools: v11-13, 36 rows each.

Default row: the right tool is called, its result is right (tool-verified),
and the final answer is right. The planted deviations are listed in PLANTS
below; the hand-computed consequences are in the test file.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFIX = "<|channel>thought\n<channel|>"

MODELS = {
    "gemma4_26b-a4b": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
    "Qwen3_5_9B": "Qwen/Qwen3.5-9B",
    "qwen3_6_35b": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
}
G, Q9, Q35 = "gemma4_26b-a4b", "Qwen3_5_9B", "qwen3_6_35b"
VARIANTS = (11, 12, 13, 14, 15, 16)
FIXTURES = {
    "solve": [("dA", "p01", ""), ("dB", "p01", "")],
    "validate_domain": [("dA", "p01", ""), ("dB", "domain_neg", "")],
    "validate_problem": [("dA", "p01", ""), ("dB", "n01", "")],
    "validate_plan": [("dA", "p01", "v1"), ("dA", "p01", "b1"),
                      ("dB", "p01", "v1"), ("dB", "p01", "b1")],
    "simulate": [("dA", "p01", ""), ("dB", "p01", "")],
}
TRUTH = {("validate_domain", "p01"): True, ("validate_domain", "domain_neg"): False,
         ("validate_problem", "p01"): True, ("validate_problem", "n01"): False}
TOOL = {"solve": "classic_planner", "validate_domain": "validate_domain",
        "validate_problem": "validate_problem", "validate_plan": "validate_plan",
        "simulate": "get_state_transition"}
PLANS = {"dA": ["(a x)", "(b y)"], "dB": ["(c z)", "(d w)", "(e v)"]}
ORACLE = {
    "dA": [
        {"step": 0, "action": None, "boolean_fluents": {"at(r,l1)": True, "clear(l2)": True,
                                                        "stopped(r)": False}, "numeric_fluents": {}},
        {"step": 1, "action": "(move r l1 l2)",
         "boolean_fluents": {"at(r,l2)": True, "clear(l1)": True, "stopped(r)": False},
         "numeric_fluents": {}},
        {"step": 2, "action": "(stop r)",
         "boolean_fluents": {"at(r,l2)": True, "clear(l1)": True, "stopped(r)": True},
         "numeric_fluents": {}},
    ],
    "dB": [
        {"step": 0, "action": None, "boolean_fluents": {"at(t,a)": True},
         "numeric_fluents": {"fuel(t)": 5}},
        {"step": 1, "action": "(drive t a b)", "boolean_fluents": {"at(t,b)": True},
         "numeric_fluents": {"fuel(t)": 3}},
    ],
}


def truth(task, problem, label):
    if task == "validate_plan":
        return label.startswith("v")
    return TRUTH[(task, problem)]


def model_traj(dom, drop_step=None, drop_numeric=False, wrong_fact=False):
    out = []
    for st in ORACLE[dom]:
        if drop_step is not None and st["step"] == drop_step:
            continue
        boolean = ["(" + k.replace("(", " ").replace(",", " ").replace(")", "").strip() + ")"
                   for k, v in st["boolean_fluents"].items() if v]
        if wrong_fact and st["step"] == 1:
            boolean = boolean + ["(broken t)"]
        numeric = {} if drop_numeric else {k: float(v) for k, v in st["numeric_fluents"].items()}
        out.append({"step": st["step"], "action": st["action"] or "",
                    "state": {"boolean": boolean, "numeric": numeric}})
    return {"trajectory": out}


def tool_call(task, dom, problem, label, *, wrong=False):
    name = TOOL[task]
    if task == "solve":
        res = {"plan": PLANS[dom]}
    elif task == "simulate":
        traj = copy.deepcopy(ORACLE[dom])
        if wrong:
            traj[-1]["boolean_fluents"] = {"at(t,a)": True}
        res = {"valid": True, "steps": len(traj), "trajectory": traj}
    else:
        t = truth(task, problem, label)
        res = {"valid": t, "status": "VALID" if t else "INVALID", "report": ""}
    return {"name": name, "arguments": {"domain": f"(define (domain {dom}))"},
            "result": json.dumps(res)}


def right_answer(task, dom, problem, label):
    if task == "solve":
        return "\n".join(PLANS[dom])
    if task == "simulate":
        return json.dumps(model_traj(dom))
    return "VERDICT: " + ("VALID" if truth(task, problem, label) else "INVALID")


def wrong_verdict(task, problem, label):
    return "VERDICT: " + ("INVALID" if truth(task, problem, label) else "VALID")


def base_tokens(turns):
    return {"prompt": 100, "completion": 10, "turns": turns,
            "total_duration_ns": 1, "eval_duration_ns": 1}


def make_row(model, task, fx, v, style="minimal"):
    dom, problem, label = fx
    return {
        "model": MODELS[model], "task": task, "domain_name": dom, "problem_name": problem,
        "prompt_variant": v, "with_tools": True, "success": True, "tool_selected": True,
        "format_compliant": None, "response": right_answer(task, dom, problem, label),
        "response_truncated_by_storage": False, "thinking": "",
        "tool_calls": [tool_call(task, dom, problem, label)], "tokens": base_tokens(2),
        "duration_s": 1.0, "error": "", "tool_filter": "all", "prompt_style": style,
        "failure_reason": "ok", "truncated": False, "done_reason": "stop",
        "think_truncated": None, "plan_label": label, "infra_failure": False,
    }


def not_invoked(row, response):
    row.update(success=False, tool_selected=False, tool_calls=[], tokens=base_tokens(1),
               failure_reason="tool_not_selected", response=response)


# ------------------------------------------------------------------ plants
# Each entry: (model, task, domain, problem, label, variant) -> mutation.
def _p(row, **kw):
    row.update(kw)


PLANTS = {
    # Gemma validate_plan plain: only (dA,v1,v11) calls the tool; the rest
    # answer unaided and WRONG. Canonical differs on (dA,v1,v11) (see CANON).
    **{(G, "validate_plan", d, "p01", l, v): (
        lambda row, d=d, l=l: not_invoked(row, wrong_verdict("validate_plan", "p01", l)))
       for d in ("dA", "dB") for l in ("v1", "b1") for v in (11, 12, 13)
       if not (d == "dA" and l == "v1" and v == 11)},
    # Gemma solve plain dA v11: right plan behind the leaked prefix, strict lines.
    (G, "solve", "dA", "p01", "", 11): lambda row: _p(
        row, response=PREFIX + "(a x)\n(b y)"),
    # Gemma solve steered dA v14: prefix glued to a backticked numbered list
    # (the tolerant path must read the stripped text).
    (G, "solve", "dA", "p01", "", 14): lambda row: _p(
        row, response=PREFIX + "1. `(a x)` - pick\n2. `(b y)` - put"),
    # Gemma solve plain dB v13: final turn clipped and cut (REFUSED_OR_CLIPPED_FINAL).
    (G, "solve", "dB", "p01", "", 13): lambda row: _p(
        row, response="(c z)", done_reason="length", truncated=True,
        tokens={**base_tokens(2), "ctx_clipped_turns": 1,
                "ctx_clip_last_turn_max_tokens": 500,
                "ctx_clip_last_turn_prompt_tokens": 15884}),
    # Gemma simulate plain dB v12: no-room final turn (§8a).
    (G, "simulate", "dB", "p01", "", 12): lambda row: _p(
        row, response="", done_reason="length", truncated=True,
        tokens={**base_tokens(2), "ctx_no_room_turns": 1}),
    # Gemma simulate steered dA v14: prose answer, no JSON (NEEDS_READING).
    (G, "simulate", "dA", "p01", "", 14): lambda row: _p(
        row, response="The robot moves to l2 and stops."),
    # 9B solve plain dB v13: plan restated without its last action (ABRIDGED).
    (Q9, "solve", "dB", "p01", "", 13): lambda row: _p(row, response="(c z)\n(d w)"),
    # 9B validate_problem plain dA v11: empty answer after the tool (NO_FINAL_ANSWER).
    (Q9, "validate_problem", "dA", "p01", "", 11): lambda row: _p(row, response=""),
    # 9B simulate plain dB v12: numeric fluents left out (NUMERIC_OMITTED).
    (Q9, "simulate", "dB", "p01", "", 12): lambda row: _p(
        row, response=json.dumps(model_traj("dB", drop_numeric=True))),
    # 9B simulate steered dA v15: a step skipped (ABRIDGED).
    (Q9, "simulate", "dA", "p01", "", 15): lambda row: _p(
        row, response=json.dumps(model_traj("dA", drop_step=2))),
    # 35B solve steered dB v14: no tool call, wrong plan (tool-verified False).
    (Q35, "solve", "dB", "p01", "", 14): lambda row: not_invoked(row, "(z z)"),
    # 35B solve steered dA v15: plan in prose (WRONG_WRAPPER).
    (Q35, "solve", "dA", "p01", "", 15): lambda row: _p(
        row, response="Plan: a x, then b y."),
    # 35B solve steered dB v15: no plan at all (SUMMARY_ONLY).
    (Q35, "solve", "dB", "p01", "", 15): lambda row: _p(
        row, response="I solved it with the planner."),
    # 35B validate_domain plain dA v12: no verdict line (NEEDS_READING).
    (Q35, "validate_domain", "dA", "p01", "", 12): lambda row: _p(
        row, response="The domain looks fine to me."),
    # 35B validate_problem steered: zero-success arm on both surfaces, no calls.
    **{(Q35, "validate_problem", d, p, "", v): (
        lambda row, p=p: not_invoked(row, wrong_verdict("validate_problem", p, "")))
       for d, p in (("dA", "p01"), ("dB", "n01")) for v in (14, 15, 16)},
    # 35B validate_plan steered dB b1 v16: stated verdict contradicts the tool (WRONG_FACTS).
    (Q35, "validate_plan", "dB", "p01", "b1", 16): lambda row: _p(
        row, response="VERDICT: VALID"),
    # 35B simulate plain dA v11: an earlier turn was clipped before a tool call.
    (Q35, "simulate", "dA", "p01", "", 11): lambda row: _p(
        row, tokens={**base_tokens(3), "ctx_clipped_turns": 2,
                     "ctx_clip_last_turn_max_tokens": 1000,
                     "ctx_clip_last_turn_prompt_tokens": 15384}),
    # 35B simulate plain dB v13: last tool call sent a changed plan; the answer
    # restates that wrong trajectory (TOOL_INPUT_ERROR).
    (Q35, "simulate", "dB", "p01", "", 13): lambda row: _p(
        row, tool_calls=[tool_call("simulate", "dB", "p01", ""),
                         tool_call("simulate", "dB", "p01", "", wrong=True)],
        response=json.dumps({"trajectory": [
            {"step": 0, "action": "", "state": {"boolean": ["(at t a)"],
                                               "numeric": {"fuel(t)": 5.0}}},
            {"step": 1, "action": "(drive t a b)", "state": {"boolean": ["(at t a)"],
                                                            "numeric": {"fuel(t)": 3.0}}}]})),
    # 35B simulate steered dB v16: one extra fact (WRONG_FACTS).
    (Q35, "simulate", "dB", "p01", "", 16): lambda row: _p(
        row, response=json.dumps(model_traj("dB", wrong_fact=True))),
}

# Canonical tool-verified differences (parity plants).
CANON = {
    # Gemma vplan plain: canonical never called the tool on (dA,v1,v11).
    (G, "validate_plan", "dA", "p01", "v1", 11): "uninvoked",
    # 35B solve steered: discordant in both directions (Δ̂ = 0, wide CI).
    (Q35, "solve", "dA", "p01", "", 14): "uninvoked",
    (Q35, "solve", "dB", "p01", "", 14): "invoked",
}
# 9B validate_domain plain: canonical (dA,p01,v11) recorded under problem p02
# -> 1 unpaired row on each side -> 2/7 > 1% -> VOID.
CANON_RENAME = {(Q9, "validate_domain", "dA", "p01", "", 11): "p02"}

# Canonical no-tools stored grades: default right; these are wrong.
NT_WRONG = {(Q35, "validate_plan", d, "p01", l, 11)
            for d in ("dA", "dB") for l in ("v1", "b1")}


def rerun_a_rows(model):
    rows = []
    for v in VARIANTS:
        for task, fxs in FIXTURES.items():
            for fx in fxs:
                row = make_row(model, task, fx, v)
                plant = PLANTS.get((model, task, *fx, v))
                if plant:
                    plant(row)
                rows.append(row)
    return rows


def rerun_b_rows():
    rows = []
    for v in VARIANTS:
        for fx in FIXTURES["validate_plan"]:
            row = make_row(G, "validate_plan", fx, v, style="neutral")
            if v in (11, 12, 13):
                # Neutral system prompt, plain wording: no call, right answer.
                not_invoked(row, right_answer("validate_plan", *fx))
            rows.append(row)
    return rows


CANONICAL_KEYS_DROP = ("format_compliant", "response_truncated_by_storage", "think_truncated")


def to_canonical(row, model):
    c = {k: v for k, v in copy.deepcopy(row).items() if k not in CANONICAL_KEYS_DROP}
    c["tokens"] = {k: v for k, v in c["tokens"].items() if not k.startswith("ctx_")}
    key = (model, c["task"], c["domain_name"], c["problem_name"], c["plan_label"],
           c["prompt_variant"])
    what = CANON.get(key)
    if what == "uninvoked":
        not_invoked(c, c["response"])
    elif what == "invoked":
        dom, problem, label = c["domain_name"], c["problem_name"], c["plan_label"]
        c.update(success=True, tool_selected=True, failure_reason="ok",
                 tool_calls=[tool_call(c["task"], dom, problem, label)])
    if key in CANON_RENAME:
        c["problem_name"] = CANON_RENAME[key]
    return c


def no_tools_rows(model):
    rows = []
    for v in (11, 12, 13):
        for task, fxs in FIXTURES.items():
            for dom, problem, label in fxs:
                ok = (model, task, dom, problem, label, v) not in NT_WRONG
                if task == "simulate":
                    ok, resp, fr = False, '{"trajectory": []}', "simulate_empty"
                elif task == "solve":
                    resp, fr = json.dumps({"plan": PLANS[dom]}), "ok"
                else:
                    t = truth(task, problem, label)
                    verdict = ("VALID" if t else "INVALID") if ok else ("INVALID" if t else "VALID")
                    resp = json.dumps({"verdict": verdict, "reason": ""})
                    fr = "ok" if ok else "verdict_mismatch"
                rows.append({
                    "model": MODELS[model], "task": task, "domain_name": dom,
                    "problem_name": problem, "prompt_variant": v, "with_tools": False,
                    "success": ok, "tool_selected": None, "response": resp, "thinking": "",
                    "tool_calls": [], "tokens": base_tokens(1), "duration_s": 1.0,
                    "error": "", "tool_filter": "all", "prompt_style": "minimal",
                    "failure_reason": fr, "truncated": False, "done_reason": "stop",
                    "plan_label": label, "infra_failure": False})
    return rows


# Part C (no-tools rerun) plants on top of the default "right answer" row.
PART_C_PLANTS = {
    # Gemma solve dA v12: the right plan as a backticked numbered list. The
    # strict online grade fails it (format_parse_fail, stored success False);
    # the delivered grader's tolerant path passes it (prereg 8b item 12).
    (G, "solve", "dA", "p01", "", 12): dict(
        response="1. `(a x)` - pick" + chr(10) + "2. `(b y)` - put", success=False,
        failure_reason="format_parse_fail"),
    # 9B simulate dA v11: one extra fact at step 1 (wrong trajectory).
    (Q9, "simulate", "dA", "p01", "", 11): dict(
        response=json.dumps(model_traj("dA", wrong_fact=True)), success=False,
        failure_reason="result_mismatch"),
}


def part_c_rows(model):
    """No-tools rerun rows. Simulate answers use s-expression atoms ("(at r l1)")
    against the functional-notation oracle ("at(r,l1)"), which only the current
    normaliser (`_canon_atom`) equates."""
    rows = []
    for v in (11, 12, 13):
        for task, fxs in FIXTURES.items():
            for dom, problem, label in fxs:
                if task == "solve":
                    resp = json.dumps({"plan": PLANS[dom]})
                elif task == "simulate":
                    resp = json.dumps(model_traj(dom))
                else:
                    t = truth(task, problem, label)
                    resp = json.dumps({"verdict": "VALID" if t else "INVALID", "reason": ""})
                row = {
                    "model": MODELS[model], "task": task, "domain_name": dom,
                    "problem_name": problem, "prompt_variant": v, "with_tools": False,
                    "success": True, "tool_selected": None,
                    "format_compliant": True if task == "simulate" else None,
                    "response": resp, "response_truncated_by_storage": False, "thinking": "",
                    "tool_calls": [], "tokens": base_tokens(1), "duration_s": 1.0,
                    "error": "", "tool_filter": "all", "prompt_style": "minimal",
                    "failure_reason": "ok", "truncated": False, "done_reason": "stop",
                    "think_truncated": None, "plan_label": label, "infra_failure": False}
                if (model, task, dom, problem, label, v) in NT_WRONG:
                    t = truth(task, problem, label)
                    row.update(success=False, failure_reason="verdict_mismatch",
                               response=json.dumps({"verdict": "INVALID" if t else "VALID",
                                                    "reason": ""}))
                row.update(PART_C_PLANTS.get((model, task, dom, problem, label, v), {}))
                rows.append(row)
    return rows


def write_cell(path: Path, rows):
    path.mkdir(parents=True, exist_ok=True)
    with (path / "trials.jsonl").open("w") as fh:
        for r in rows:
            key = [r["model"], r["task"], r["domain_name"], r["problem_name"], r["plan_label"],
                   r["prompt_variant"], r["with_tools"], "off", r["tool_filter"],
                   r["prompt_style"]]
            fh.write(json.dumps({"key": key, "result": r}) + "\n")


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rerun, canon = out / "rerun", out / "canonical"
    rerun.mkdir(exist_ok=True)
    (rerun / "SYNTHETIC_FIXTURE").write_text(
        "Synthetic fixture for tests/test_delivered_rerun_analysis.py. Not experiment data.\n")
    for m in MODELS:
        a = rerun_a_rows(m)
        write_cell(rerun / f"slurm_vllm_{m}_off_tools_all_minimal_delivered-rerun", a)
        write_cell(canon / f"slurm_vllm_{m}_off_tools_all_minimal",
                   [to_canonical(r, m) for r in a])
        write_cell(canon / f"slurm_vllm_{m}_off_no-tools", no_tools_rows(m))
        write_cell(rerun / f"slurm_vllm_{m}_off_no-tools_delivered-rerun", part_c_rows(m))
    write_cell(rerun / "slurm_vllm_gemma4_26b-a4b_off_tools_all_neutral_delivered-rerun-neutral",
               rerun_b_rows())
    gt = {d: {"p01": {"trace": json.dumps({"valid": True, "trajectory": ORACLE[d]})}}
          for d in ORACLE}
    (out / "gt_cache.json").write_text(json.dumps(gt, indent=1, sort_keys=True) + "\n")
    verdicts = [
        {"domain": "dA", "problem": "p01", "plan": PLANS["dA"], "valid": True},
        {"domain": "dB", "problem": "p01", "plan": PLANS["dB"], "valid": True},
        {"domain": "dB", "problem": "p01", "plan": ["(c z)", "(d w)"], "valid": False},
        {"domain": "dB", "problem": "p01", "plan": ["(c z)"], "valid": False},
        {"domain": "dB", "problem": "p01", "plan": ["(z z)"], "valid": False},
    ]
    (out / "plan_verdicts.json").write_text(json.dumps(verdicts, indent=1) + "\n")
    # Bands wide open ([0, 100]) so the base fixture never trips T4; the test
    # narrows one to check the tripwire. n must equal the canonical cell size.
    counts = {}
    for m in MODELS:
        for t, fxs in FIXTURES.items():
            for arm in ("plain", "steered"):
                n = 3 * len(fxs)
                counts[f"{m}|{t}|{arm}"] = [n, 0, n]
    design = {"n_part_a_cell": 72, "n_part_b": 24, "per_variant_a": 12, "per_variant_b": 4,
              "per_task_variant": {t: len(f) for t, f in FIXTURES.items()},
              "k_domains": 2, "n_no_tools_cell": 36,
              "canonical_delivered_counts": counts}
    (out / "design.json").write_text(json.dumps(design, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
