"""Re-derive the delivered-rerun parity tables (prereg §3 and §2 Part C) through the
frozen package's own loader and parity functions, read-only. Stops before any
delivered grading (no MCP). Run from the repo root with PYTHONDONTWRITEBYTECODE=1."""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.delivered_rerun import analysis as A, constants as C, run as R
print("package sha256:", R.package_sha256())
design = C.REGISTERED
cells = R.load_all(design, REPO / "results" / "delivered-rerun", REPO / "results" / "sweep5v2-live")
k = design.k_domains
par = A.parity(cells["rerun_a"], cells["canon_tools"], k)
parc = A.part_c_parity(cells["rerun_c"], cells["canon_nt"], k)
out = {"job": par.job, "qwen_met": par.qwen_met, "gross": par.gross_cells,
       "cells": [dict(model=c.model, task=c.task, arm=c.arm, n=c.n_paired,
                      ur=c.unpaired_rerun, uc=c.unpaired_canonical,
                      rerun=c.tv_rerun_pct, canon=c.tv_canonical_pct, delta=c.delta,
                      lo=c.ci90.lo, hi=c.ci90.hi, verdict=c.verdict) for c in par.cells],
       "part_c": [dict(model=c.model, task=c.task, n=c.n_paired, ur=c.unpaired_rerun,
                       uc=c.unpaired_canonical, rerun=c.tv_rerun_pct, canon=c.tv_canonical_pct,
                       delta=c.delta, lo=c.ci90.lo, hi=c.ci90.hi, verdict=c.verdict) for c in parc]}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
print(par.job, "qwen_met", par.qwen_met, "gross", par.gross_cells)
for c in out["cells"]:
    print(f'{c["model"]:15s} {c["task"]:17s} {c["arm"]:8s} n={c["n"]} rerun={c["rerun"]:.1f} canon={c["canon"]:.1f} d={c["delta"]:+.1f} [{c["lo"]:.1f}, {c["hi"]:.1f}] {c["verdict"]}')
print("Part C")
for c in out["part_c"]:
    print(f'{c["model"]:15s} {c["task"]:17s} n={c["n"]} rerun={c["rerun"]:.1f} canon={c["canon"]:.1f} d={c["delta"]:+.1f} [{c["lo"]:.1f}, {c["hi"]:.1f}] {c["verdict"]}')
