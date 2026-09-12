"""Stripped-block regrade of the injected Mystery matched-NT trials (audit 2 hardening).

For each of the 600 Mystery matched-NT trials (engine anthropic-scaffold, configs
mystery_blocksworld + mystery_blocksworld_3), re-extract a plan using ONLY the text
inside the model's [PLAN]..[PLAN END] block (no block or empty block = failure),
convert with the SAME text_to_plan the grader uses, and validate with the SAME VAL
via utils.validate_plan. Read-only on the graded corpora; writes a throwaway plan
file `llm_plan_stripped` in cwd.

Block semantics match the injection audit in analyze_confirmatory.py exactly:
split on "[PLAN]", take up to "[PLAN END]" if present (rest of text otherwise;
counted separately as no_plan_end). The injection cross-check reproduces the
audit's definition on every delivered trial (no block => listed = []), so its
total should tie to the memo's 479/600.

Usage (cwd = external/LLMs-Planning/plan-bench, VAL + PYTHONPATH per grade_all.sh):
  .venv-planbench-wt/bin/python .local/wt_run/stripped_block_regrade.py
"""
import json
import math
import sys

import yaml

sys.path.insert(0, ".")
from tarski.io import PDDLReader  # noqa: E402
from utils import validate_plan  # noqa: E402
from utils.text_to_pddl import text_to_plan  # noqa: E402

NT = "pddl_copilot__anthropic-scaffold__claude-haiku-4-5"
CFGS = ["mystery_blocksworld", "mystery_blocksworld_3"]
PLAN_FILE = "llm_plan_stripped"


def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def main():
    totals = {"n": 0, "delivered": 0, "no_block": 0, "empty_block": 0,
              "no_plan_end": 0, "parsed_empty": 0, "val_run": 0,
              "stripped_correct": 0, "orig_correct": 0, "injected": 0, "flips": []}
    for cfg in CFGS:
        data = yaml.safe_load(open(f"configs/{cfg}.yaml"))
        dom = f"./instances/{data['domain_file']}"
        tpl = f"./instances/{data['instance_dir']}/{data['instances_template']}"
        res = json.load(open(f"results/{cfg}/{NT}/task_1_plan_generation.json"))
        rows = {r["instance_id"]: r for r in res["instances"]}
        lo, hi = data["start"] + 1, data["end"] + 1  # pool ids are 2..end+1
        cell_correct = cell_n = 0
        for iid in range(lo, hi + 1):
            r = rows.get(iid, {})
            text = r.get("llm_raw_response") or ""
            orig = int(r.get("llm_correct", 0))
            totals["n"] += 1
            cell_n += 1
            totals["orig_correct"] += orig
            correct = 0
            body = None
            if text:
                totals["delivered"] += 1
                reader = PDDLReader(raise_on_error=True)
                reader.parse_domain(dom)
                problem = reader.parse_instance(tpl.format(iid))
                # injection cross-check, audit definition on every delivered trial
                full_plan, _ = text_to_plan(text, problem.actions, PLAN_FILE, data)
                n_full = len([ln for ln in full_plan.splitlines() if ln.strip()])
                if "[PLAN]" in text:
                    after = text.split("[PLAN]", 1)[1]
                    if "[PLAN END]" not in after:
                        totals["no_plan_end"] += 1
                    body = after.split("[PLAN END]", 1)[0]
                    listed = [ln for ln in body.splitlines() if ln.strip()]
                else:
                    listed = []
                totals["injected"] += int(n_full > len(listed))
            if body is None:
                totals["no_block"] += 1
            elif not body.strip():
                totals["empty_block"] += 1
            else:
                plan, _ = text_to_plan(body, problem.actions, PLAN_FILE, data)
                if not plan.strip():
                    totals["parsed_empty"] += 1
                else:
                    totals["val_run"] += 1
                    correct = int(validate_plan(dom, tpl.format(iid), PLAN_FILE))
            totals["stripped_correct"] += correct
            cell_correct += correct
            if correct != orig:
                totals["flips"].append((cfg, iid, orig, correct))
        print(f"{cfg}: stripped correct {cell_correct}/{cell_n}")

    n, k = totals["n"], totals["stripped_correct"]
    lo, hi = wilson(k, n)
    print(f"\nPooled stripped-block regrade (Mystery matched-NT, n={n}):")
    print(f"  stripped correct {k}/{n} = {100*k/n:.1f}% "
          f"[{100*lo:.1f},{100*hi:.1f}]  (graded corpus: {totals['orig_correct']}/{n})")
    print(f"  delivered: {totals['delivered']}   no [PLAN] block: {totals['no_block']}   "
          f"empty block: {totals['empty_block']}   missing [PLAN END]: {totals['no_plan_end']}")
    print(f"  block parsed to empty plan: {totals['parsed_empty']}   "
          f"VAL invocations: {totals['val_run']}")
    print(f"  injection cross-check (audit definition, delivered trials): "
          f"{totals['injected']}/{totals['delivered']}")
    if totals["flips"]:
        print(f"  FLIPS vs graded corpus ({len(totals['flips'])}):")
        for cfg, iid, orig, new in totals["flips"]:
            print(f"    {cfg} #{iid}: graded {orig} -> stripped {new}")
    else:
        print("  no flips vs graded corpus")


if __name__ == "__main__":
    main()
