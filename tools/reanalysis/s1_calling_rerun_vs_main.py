"""Descriptive (not a registered parity test): calling, main sweep vs delivered rerun, paired on the
trial key, through the frozen package's loader and its domain-cluster bootstrap (90%, seed 20261002).
Two definitions: `tool_selected` (the task's own tool; Study 1 / tex) and any tool call (the rerun
readout's 'invocation'). Read-only; run with PYTHONDONTWRITEBYTECODE=1."""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.delivered_rerun import constants as C, run as R
from tools.delivered_rerun.stats import cluster_bootstrap
cells = R.load_all(C.REGISTERED, REPO / "results" / "delivered-rerun", REPO / "results" / "sweep5v2-live")
out = []
for m in C.PART_A_MODELS:
    rr = {r.trial_key: r for r in cells["rerun_a"][m].rows}
    cc = {r.trial_key: r for r in cells["canon_tools"][m].rows}
    for t in C.TASKS:
        for a in C.ARMS:
            keys = sorted(k for k in set(rr) & set(cc) if rr[k].task == t and rr[k].arm == a)
            row = dict(model=m, task=t, arm=a, n=len(keys))
            for nm, f in (("sel", lambda r: int(bool(r.tool_selected))), ("any", lambda r: int(r.invoked))):
                d = [f(rr[k]) - f(cc[k]) for k in keys]
                b = cluster_bootstrap(d, [k[1] for k in keys], 0.90, 20, what=f"{m}/{t}/{a}/{nm}")
                row[nm] = dict(main=100 * sum(f(cc[k]) for k in keys) / len(keys),
                               rerun=100 * sum(f(rr[k]) for k in keys) / len(keys), delta=b.est, lo=b.lo, hi=b.hi)
            out.append(row)
            s, y = row["sel"], row["any"]
            print(f'{m:15s} {t:17s} {a:8s} n={row["n"]} SEL main={s["main"]:.1f} rerun={s["rerun"]:.1f} d={s["delta"]:+.1f} [{s["lo"]:.1f},{s["hi"]:.1f}] | ANY main={y["main"]:.1f} rerun={y["rerun"]:.1f} d={y["delta"]:+.1f}')
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
