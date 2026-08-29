#!/usr/bin/env python3
"""Proof: with-tools success is graded on the TOOL CALL RESULT, not the model's
final answer — and the model's own answer deviates (under-specifies) ~29-36% of
the time on tool-graded validate_* successes (2026-07-11).

Code proof (pddl_eval/scoring.py check_success): the with-tools branches read
the tool's own output via `_get_tool_results` / `tc.get("result")`
  - validate_*  :528-536   - solve :473-492   - simulate :575-583
  - helper `_get_tool_results` :74 returns tc["result"] verbatim
The model `response` text is read ONLY in the no-tools fallback paths
(:497-498 solve, :544-548 validate, :596 simulate). So with-tools success =
"right tool selected AND tool returned the ground-truth answer", NOT "model
correctly conveyed that answer".

This script quantifies the deviation on validate_* (verdict is binary +
extractable from response). For each with-tools trial we scored success via the
TOOL result, it compares the model's OWN final verdict (extract_verdict on
`response`) to the tool's verdict:
  - faithful   : model restates the tool verdict
  - contradict : model states the OPPOSITE verdict (scored correct anyway)
  - no-verdict : model states no checkable verdict (credited on the tool alone),
                 split by done_reason (stop = completed yet silent; length = truncated)

Runs on the local canonical corpus; no cluster/MCP needed.
"""
import json, sys, collections
sys.path.insert(0, ".")
from pddl_eval.scoring import _parse_validation_verdict, extract_verdict

CELLS = [
    ("qwen3.6:35b", "results/sweep5v2-live/slurm_vllm_qwen3_6_35b_on_tools_all_minimal/trials.jsonl"),
    ("Qwen3.5:4B",  "results/sweep5v2-live/slurm_vllm_Qwen3_5_4B_on_tools_all_minimal/trials.jsonl"),
]
VAL = {"validate_domain", "validate_problem", "validate_plan"}

for disp, path in CELLS:
    faithful = contra = 0
    nv_dr = collections.Counter()
    tot = 0
    for ln in open(path):
        res = json.loads(ln).get("result", {})
        if res.get("task") not in VAL or res.get("success") is not True:
            continue
        # tool verdict = the validate tool's own result (the surface we graded on)
        tv = None
        for tc in res.get("tool_calls") or []:
            if tc.get("name") == res["task"]:
                v = _parse_validation_verdict(tc.get("result", ""))
                if v is not None:
                    tv = v
        if tv is None:
            continue  # not a tool-graded success case
        tot += 1
        mv = extract_verdict(res.get("response") or "")  # model's OWN stated verdict
        if mv is None:
            nv_dr[res.get("done_reason")] += 1
        elif mv != tv:
            contra += 1
        else:
            faithful += 1
    nv = sum(nv_dr.values())
    print("=" * 88)
    print(f"{disp} — with-tools validate_* successes graded via the TOOL result: n={tot}")
    if tot:
        print(f"  model restates tool verdict (faithful) : {faithful:5d} ({100*faithful/tot:4.1f}%)")
        print(f"  model states CONTRADICTORY verdict      : {contra:5d} ({100*contra/tot:4.1f}%)  <- scored correct anyway")
        print(f"  model states NO checkable verdict       : {nv:5d} ({100*nv/tot:4.1f}%)  <- credited on the tool alone")
        print(f"       split by done_reason               : {dict(nv_dr)}  (stop=completed-yet-silent, length=truncated)")
