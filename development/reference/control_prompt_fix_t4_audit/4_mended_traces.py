"""Audit only, not a registered reading: if the bracket slips in the 47 malformed blocks
are mended at the point where the JSON parser stops, does the trace equal the oracle?"""
import sys, json, re, pickle, argparse, collections
from pathlib import Path
import tools.reanalysis.control_prompt_fix as M
import tools.delivered_rerun.grade as G
ap = argparse.ArgumentParser(); M.R1.add_data_args(ap); ap.add_argument("--pkl")
ap.add_argument("--marketplace", type=Path)
ap.add_argument("--regrade-json", type=Path, default=Path(M.__file__).resolve().parent/"out"/"rq1_layout_regrade.json")
args = ap.parse_args(); M.R1.fill_data_args(args)
rr = M.load_rerun_live(args)
rows = pickle.load(open(args.pkl, "rb"))[("gemma4_26b-a4b", "B", "simulate")]
FENCE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.S)
res = collections.Counter()
for r in rows:
    body = FENCE.findall(r["response"])[-1][1].strip()
    fixes = 0; v = None
    for _ in range(4):
        try: v = json.loads(body); break
        except json.JSONDecodeError as e:
            fixes += 1
            if e.msg.startswith("Expecting ','"): body = body[:e.pos] + "}" + body[e.pos:]
            elif e.msg == "Extra data": body = body[:e.pos-1] + body[e.pos:] if body[e.pos-1] in "}]" else body[:e.pos]
            else: break
    kind = "well-formed as written" if fixes == 0 else f"mended"
    if v is None: res[(kind, "still not JSON")] += 1; continue
    steps = v.get("trajectory") if isinstance(v, dict) else None
    canon = G._normalize_trajectory(steps) if steps is not None else None
    oracle = G.oracle_canon_for(rr.gt_cache, {"domain_name": r["domain"], "problem_name": r["problem"]})
    res[(kind, "not a trace the grader accepts" if canon is None else ("equals oracle" if canon == oracle else "differs from oracle"))] += 1
for k, n in sorted(res.items()): print(n, k)
