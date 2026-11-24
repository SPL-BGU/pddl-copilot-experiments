"""Audit of tripwire T4 (Gemma, cell B, simulate). Reuses the frozen module's own
functions without editing them; reads the control only with the frozen package hash."""
import sys, json, argparse, re, collections, pickle
from pathlib import Path
import tools.reanalysis.control_prompt_fix as M
M_ = M
ap = argparse.ArgumentParser(); M.R1.add_data_args(ap)
ap.add_argument("--marketplace", type=Path); ap.add_argument("--regrade-json", type=Path,
    default=Path(M.__file__).resolve().parent/"out"/"rq1_layout_regrade.json")
ap.add_argument("--serve-logs", type=Path)
args = ap.parse_args(sys.argv[1:]); M.R1.fill_data_args(args)
assert M.package_sha256() == "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79"
design = M.REGISTERED
root = args.results / M.RUN_TAG
tags, _ = M.resolve_tags(root, design, "")
control = M.load_control(root, design, tags)
rr = M.load_rerun_live(args)
verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
out = {}
for m in M.MODEL_ORDER:
    for cell in M.CELLS:
        rows = control[m][cell].rows
        pairs = M.frozen_grades(rows, verdict, rr.gt_cache)
        graded = M.grade_rows(pairs, verdict, rr.gt_cache)
        for r, g in pairs:
            x = graded[r.trial_key]
            if x.unread:
                out.setdefault((m, cell, r.task), []).append(
                    dict(key=list(r.trial_key), domain=r.domain, problem=r.problem, variant=r.variant,
                         reason=x.reason, layout=x.layout, completion=x.completion, response=r.response))
print({ "|".join(k): len(v) for k, v in out.items()})
pickle.dump(out, open(sys.argv[0].replace(".py", ".pkl"), "wb"))
