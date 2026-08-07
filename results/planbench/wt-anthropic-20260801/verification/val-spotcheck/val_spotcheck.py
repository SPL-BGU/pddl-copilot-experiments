"""Independent VAL spot-check of 8 of the 26 stripped-block regrade flips.

Does NOT import or call stripped_block_regrade.py. Re-derives the stripped-block
extraction from its own reading of the doc/script (text strictly between the FIRST
"[PLAN]" and the FIRST subsequent "[PLAN END]", case as-is, same as the audited
script), re-implements it independently here, and calls VAL directly via subprocess
(not through utils.validate_plan, to avoid depending on the audited script's plumbing
at all -- though the same shell-out shape is used since that's how VAL is invoked).

Usage (cwd must be external/LLMs-Planning/plan-bench, VAL env set):
  VAL=$REPO/external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables \
  PYTHONPATH=$REPO \
  $REPO/.venv-planbench-wt/bin/python /path/to/val_spotcheck.py
"""
import json
import os
import subprocess
import sys

import yaml

sys.path.insert(0, ".")
from tarski.io import PDDLReader  # noqa: E402
from utils.text_to_pddl import text_to_plan  # noqa: E402

NT = "pddl_copilot__anthropic-scaffold__claude-haiku-4-5"

OUT_DIR = "/private/tmp/claude-501/-Users-omereliyahu-personal-pddl-copilot-experiments/4721bdc4-1a3f-4ecb-86e9-672fa71b56d1/scratchpad/val-spotcheck"

# 8 of the 26 flip IDs from stripped_block_regrade.out, spread across the ordered
# flip list (index 1,4,8,11,15,18,22,26 of 26) and across both configs.
SAMPLE = [
    ("mystery_blocksworld", 5),
    ("mystery_blocksworld", 61),
    ("mystery_blocksworld", 142),
    ("mystery_blocksworld", 164),
    ("mystery_blocksworld", 233),
    ("mystery_blocksworld", 428),
    ("mystery_blocksworld_3", 73),
    ("mystery_blocksworld_3", 100),
]


def extract_stripped_body(text):
    """Independent re-implementation of the script's block semantics:
    split on first "[PLAN]", take up to first "[PLAN END]" after that (else rest
    of text), body = that slice."""
    if "[PLAN]" not in text:
        return None
    after = text.split("[PLAN]", 1)[1]
    if "[PLAN END]" in after:
        body = after.split("[PLAN END]", 1)[0]
    else:
        body = after
    return body


def main():
    results = []
    for cfg, iid in SAMPLE:
        data = yaml.safe_load(open(f"configs/{cfg}.yaml"))
        dom = os.path.abspath(f"./instances/{data['domain_file']}")
        tpl = os.path.abspath(f"./instances/{data['instance_dir']}/{data['instances_template']}")
        prob = tpl.format(iid)
        res = json.load(open(f"results/{cfg}/{NT}/task_1_plan_generation.json"))
        rows = {r["instance_id"]: r for r in res["instances"]}
        r = rows.get(iid)
        assert r is not None, f"instance {iid} not found in {cfg} corpus"
        text = r.get("llm_raw_response") or ""
        orig_correct = int(r.get("llm_correct", 0))
        assert text, f"{cfg} #{iid}: expected a delivered response (non-empty), got empty"

        body = extract_stripped_body(text)
        assert body is not None, f"{cfg} #{iid}: no [PLAN] block found (unexpected for a flip)"

        reader = PDDLReader(raise_on_error=True)
        reader.parse_domain(dom)
        problem = reader.parse_instance(prob)

        plan_file = os.path.join(OUT_DIR, f"plan_{cfg}_{iid}.txt")
        plan, readable_plan = text_to_plan(body, problem.actions, plan_file, data)

        # Save raw response + extracted body alongside, for audit trail.
        with open(os.path.join(OUT_DIR, f"raw_{cfg}_{iid}.txt"), "w") as f:
            f.write(text)
        with open(os.path.join(OUT_DIR, f"body_{cfg}_{iid}.txt"), "w") as f:
            f.write(body)

        val_dir = os.environ["VAL"]
        cmd = [f"{val_dir}/validate", dom, prob, plan_file]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        with open(os.path.join(OUT_DIR, f"val_out_{cfg}_{iid}.txt"), "w") as f:
            f.write(f"CMD: {' '.join(cmd)}\n\n{out}")

        val_verdict = "VALID" if "Plan valid" in out else "INVALID"
        problem_in_domain = "Problem in domain" in out

        results.append({
            "cfg": cfg, "iid": iid, "orig_correct": orig_correct,
            "plan_lines": len([ln for ln in plan.splitlines() if ln.strip()]),
            "readable_plan": readable_plan.strip(),
            "val_verdict": val_verdict,
            "problem_in_domain_error": problem_in_domain,
        })
        print(f"{cfg} #{iid}: plan_lines={results[-1]['plan_lines']} "
              f"val={val_verdict} orig_graded_correct={orig_correct} "
              f"problem_in_domain_err={problem_in_domain}")
        print(f"  readable plan: {readable_plan.strip().splitlines()}")

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"{r['cfg']:24s} #{r['iid']:4d}  orig_graded={r['orig_correct']}  "
              f"stripped_plan_lines={r['plan_lines']:3d}  VAL={r['val_verdict']}")

    with open(os.path.join(OUT_DIR, "spotcheck_summary.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
