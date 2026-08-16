#!/usr/bin/env python3
"""ISS-024(b) guided_json audit, v2 — mechanism + affected-row fraction.

A working vLLM `guided_json` constraint makes schema-violating output
IMPOSSIBLE: the decoder cannot emit a token that leaves the grammar. So any
stored no-tools response that is (a) not JSON, or (b) JSON that violates
TASK_SCHEMAS[task], is direct proof the constraint did not bind on that row.

Truncation handling: generation- or storage-truncated rows cannot be judged
(a valid JSON prefix may have been cut), so they are reported separately and
excluded from the decidable denominator. Empty responses likewise.

Read-only. Canonical corpora only.
"""
import json, glob, os, sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
from pddl_eval.schemas import TASK_SCHEMAS  # noqa: E402
from pddl_eval import schemas as S  # noqa: E402
from pydantic import ValidationError  # noqa: E402

MODELS = {"solve": S.SolveResponse, "validate_domain": S.ValidateResponse,
          "validate_problem": S.ValidateResponse, "validate_plan": S.ValidateResponse,
          "simulate": S.SimulateResponse}

ROOTS = {"sweep5v2-live": "results/sweep5v2-live",
         "sweep6-live": "results/sweep6-live",
         "decoupled": "results/decoupled-rollup"}

def classify(resp, task, truncated, cap):
    """-> one of: empty, undecidable, not_json, bad_json, schema_violation, schema_ok"""
    r = resp.strip()
    if not r:
        return "empty"
    if not r.startswith("{"):
        # truncation cannot turn JSON into a non-JSON FIRST character
        return "not_json"
    if truncated or len(resp) >= cap - 1:
        return "undecidable"
    try:
        obj = json.loads(r)
    except json.JSONDecodeError:
        return "bad_json"
    try:
        MODELS[task].model_validate(obj)
    except ValidationError:
        return "schema_violation"
    return "schema_ok"

def main():
    caps = {}
    for corpus, root in ROOTS.items():
        mx = 0
        for path in glob.glob(os.path.join(root, "*", "trials.jsonl")):
            with open(path) as f:
                for i, line in enumerate(f):
                    if i > 4000:
                        break
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    r = r.get("result", r)
                    mx = max(mx, len(r.get("response") or ""))
        caps[corpus] = (500 if mx <= 512 else 16384)
    print("inferred response-snapshot caps:", caps, "\n")

    stats = defaultdict(lambda: defaultdict(int))
    for corpus, root in ROOTS.items():
        cap = caps[corpus]
        for path in sorted(glob.glob(os.path.join(root, "*", "trials.jsonl"))):
            for line in open(path):
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                r = rec.get("result", rec)
                if r.get("with_tools") is not False or r.get("infra_failure"):
                    continue
                task = r.get("task")
                if task not in MODELS:
                    continue
                c = classify(r.get("response") or "", task,
                             bool(r.get("truncated")), cap)
                stats[(corpus, task)][c] += 1
                stats[(corpus, "ALL")][c] += 1

    hdr = f"{'corpus':<15}{'task':<18}{'decidable':>10}{'schema_ok':>11}{'violation':>11}{'not_json':>10}{'bad_json':>10}  {'BOUND?':>8}"
    print(hdr); print("-" * len(hdr))
    for (corpus, task) in sorted(stats):
        s = stats[(corpus, task)]
        dec = s["not_json"] + s["bad_json"] + s["schema_violation"] + s["schema_ok"]
        if not dec:
            continue
        ok = s["schema_ok"]
        line = (f"{corpus:<15}{task:<18}{dec:>10}{100*ok/dec:>10.1f}%"
                f"{100*s['schema_violation']/dec:>10.1f}%{100*s['not_json']/dec:>9.1f}%"
                f"{100*s['bad_json']/dec:>9.1f}%")
        print(line + f"  {'no' if ok/dec < 0.999 else 'YES':>8}")
    print()
    for (corpus, task) in sorted(stats):
        if task != "ALL":
            continue
        s = stats[(corpus, task)]
        tot = sum(s.values())
        dec = s["not_json"] + s["bad_json"] + s["schema_violation"] + s["schema_ok"]
        print(f"{corpus}: {tot} no-tools rows | decidable {dec} "
              f"({100*dec/tot:.1f}%) | undecidable(truncated/at-cap) {s['undecidable']} "
              f"| empty {s['empty']} | schema-conformant {s['schema_ok']} "
              f"({100*s['schema_ok']/dec:.2f}% of decidable)")

if __name__ == "__main__":
    main()
