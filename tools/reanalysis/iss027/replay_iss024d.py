"""Replay tool-arm validate_plan / get_state_transition calls on affected problems with a case-folded plan."""
import json, re, sys, os, tempfile
from collections import Counter, defaultdict
from pathlib import Path
REPO = Path("/Users/omereliyahu/personal/pddl-copilot-experiments")
sys.path.insert(0, str(REPO))
sys.path.insert(0, "/Users/omereliyahu/personal/pddl-copilot/plugins/pddl-validator/server")
os.environ.setdefault("PDDL_TEMP_DIR", tempfile.mkdtemp())
from pddl_eval.scoring import _normalize_trajectory, _parse_validation_verdict, _safe_json_loads, _tool_error_seen
from tools.e2e_regrade import truth_for, oracle_canon_for
import validator_server as vs
gt = json.load(open(REPO/"results/derived/gt_cache.json"))
AFF = {("satellite", p) for p in ("p02","p03","p04","p05")}
def lower_plan(p):
    if isinstance(p, list): return [str(x).lower() for x in p]
    if isinstance(p, str): return p.lower()
    return p
def has_upper(p):
    s = json.dumps(p) if not isinstance(p, str) else p
    return bool(re.search(r"[A-Z]", s))
def call(name, args, lower):
    a = {k: v for k, v in args.items() if k in ("domain","problem","plan","verbose")}
    if not all(k in a for k in ("domain","problem","plan")): return None
    if lower: a["plan"] = lower_plan(a["plan"])
    fn = vs.validate_plan if name == "validate_plan" else vs.get_state_transition
    try: return json.dumps(fn(**a))
    except Exception as e: return json.dumps({"error": True, "message": str(e)})
res = []
for corpus in ("iss024d-e2e-live",):
    for cell in sorted((REPO/"results"/corpus).iterdir()):
        if "no-tools" in cell.name: continue
        rows = {}
        for ln in open(cell/"trials.jsonl", errors="replace"):
            try: o = json.loads(ln)
            except Exception: continue
            rows[tuple(o["key"])] = o["result"]
        st = Counter()
        for k, r in rows.items():
            d, p, task = r["domain_name"], r["problem_name"], r["task"]
            if corpus != "sweep6-live" and not ((d, p) in AFF or d == "pogo_stick"): continue
            if task not in ("validate_plan", "simulate") or r.get("infra_failure"): continue
            tname = "validate_plan" if task == "validate_plan" else "get_state_transition"
            tcs = [tc for tc in (r.get("tool_calls") or []) if tc.get("name") == tname]
            cased = [tc for tc in tcs if isinstance(tc.get("arguments"), dict) and has_upper(tc["arguments"].get("plan"))]
            if not cased: continue
            arm = "steered" if k[5] >= 14 else "plain"
            st[(task, arm, "rows_with_uppercase_plan_call")] += 1
            if r["success"]: continue
            st[(task, arm, "failed")] += 1
            if corpus == "sweep6-live": continue
            # replay every call of the task tool, as-is and case-folded, re-apply the harness rule
            new_results_asis, new_results_low = [], []
            for tc in tcs:
                a = tc.get("arguments") if isinstance(tc.get("arguments"), dict) else {}
                ra = call(tname, a, False); rl = call(tname, a, True)
                new_results_asis.append(ra if ra is not None else tc.get("result", ""))
                new_results_low.append(rl if rl is not None else tc.get("result", ""))
            def passes(results):
                if task == "validate_plan":
                    truth = truth_for(r)
                    return any(_parse_validation_verdict(x) == truth for x in results)
                oc = oracle_canon_for(gt, r)
                for x in results:
                    pj = _safe_json_loads(x)
                    if isinstance(pj, dict) and not pj.get("error") and _normalize_trajectory(pj.get("trajectory")) == oc:
                        return True
                return False
            pa, pl = passes(new_results_asis), passes(new_results_low)
            st[(task, arm, "asis_replay_pass")] += pa
            if pl and not pa:
                st[(task, arm, "would_flip")] += 1
                res.append((corpus, cell.name, task, arm, k[2], k[3], k[4], k[5], r["failure_reason"]))
        if st: print(corpus, cell.name, dict(sorted(st.items())), flush=True)
print("\nFLIPS")
for x in res: print(x)
