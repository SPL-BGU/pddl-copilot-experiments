"""PlanBench-WT confirmatory analysis (prereg §3/§6 as ratified + amendment K).

Implements exactly the pre-registered spec:
- endpoint: delivered `llm_correct`, treatment-policy (missing/empty = failure),
  denominator = full realized 600 per cell (audit asserts realized n).
- PRIMARY family: two paired exact McNemar tests (clean, mystery), Holm, alpha=.05.
- band verdict on mystery WT successes at n=600: NO-RESCUE x<=19 / PARTIAL 41..275 /
  RESCUE >=325 / else INCONCLUSIVE (amendment K cutpoints).
- conjunctive ruling per prereg (significant x band).
- clean-t1 apparatus criterion: extraction >=90% AND P(correct|extracted) >=90%.
- extraction-injection audit on every cell (required before any NO-RESCUE call).
- delegation + loop_exhausted per tools cell (side-logs).
- paired clean-vs-mystery WT delta with CI, reported against the +-7.5pp margin.

Usage (cwd = external/LLMs-Planning/plan-bench):
  .venv-planbench-wt/bin/python .local/wt_run/analyze_confirmatory.py
"""
import json
import math
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, ".")
from tarski.io import PDDLReader  # noqa: E402
from utils.text_to_pddl import text_to_plan  # noqa: E402

WT = "pddl_copilot__anthropic-tools__claude-haiku-4-5"
NT = "pddl_copilot__anthropic-scaffold__claude-haiku-4-5"
ARMS = {"clean": ["blocksworld", "blocksworld_3"],
        "mystery": ["mystery_blocksworld", "mystery_blocksworld_3"]}
SIDELOG = Path(os.environ.get("WT_SIDELOG_DIR",
    Path(__file__).resolve().parents[2] / "results/planbench/wt-anthropic-20260801/sidelogs"))

# amendment K cutpoints, n=600
BANDS = [("NO-RESCUE", lambda x: x <= 19), ("PARTIAL", lambda x: 41 <= x <= 275),
         ("RESCUE", lambda x: x >= 325)]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def mcnemar_exact(b, c):
    """Two-sided exact binomial test on discordant pairs."""
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    p = sum(math.comb(n, i) for i in range(k + 1)) * 0.5 ** n
    return min(1.0, 2 * p)


def load_cell(cfg, engine):
    """Return {instance_id: {correct, delivered, extracted, injected}} on the FULL pool."""
    data = yaml.safe_load(open(f"configs/{cfg}.yaml"))
    dom = f"./instances/{data['domain_file']}"
    tpl = f"./instances/{data['instance_dir']}/{data['instances_template']}"
    res = json.load(open(f"results/{cfg}/{engine}/task_1_plan_generation.json"))
    rows = {r["instance_id"]: r for r in res["instances"]}
    lo, hi = data["start"] + 1, data["end"] + 1  # pool ids are 2..end+1
    out = {}
    for iid in range(lo, hi + 1):
        r = rows.get(iid, {})
        text = r.get("llm_raw_response") or ""
        delivered = bool(text)
        extracted_n = injected = 0
        if delivered:
            reader = PDDLReader(raise_on_error=True)
            reader.parse_domain(dom)
            problem = reader.parse_instance(tpl.format(iid))
            plan, _ = text_to_plan(text, problem.actions, "llm_plan_an", data)
            ext = [ln for ln in plan.splitlines() if ln.strip()]
            extracted_n = len(ext)
            if "[PLAN]" in text:
                body = text.split("[PLAN]", 1)[1].split("[PLAN END]", 1)[0]
                listed = [ln for ln in body.splitlines() if ln.strip()]
            else:
                listed = []
            injected = int(len(ext) > len(listed))
        out[iid] = {
            "correct": int(r.get("llm_correct", 0)),
            "delivered": int(delivered),
            "extracted": int(extracted_n > 0),
            "injected": injected,
        }
    return out


def sidelog_stats(cfg):
    f = SIDELOG / f"{cfg}__anthropic-tools.jsonl"
    byid = {}
    for ln in open(f):
        r = json.loads(ln)
        byid[r["instance_id"]] = r
    rows = list(byid.values())
    deleg = sum(1 for r in rows if "classic_planner" in (r.get("tool_names") or []))
    le = sum(bool(r.get("loop_exhausted")) for r in rows)
    return len(rows), deleg, le


def main():
    cells = {}   # (arm, engine) -> merged {(cfg,iid): rec}
    for arm, cfgs in ARMS.items():
        for engine, tag in ((WT, "WT"), (NT, "NT")):
            merged = {}
            for cfg in cfgs:
                cell = load_cell(cfg, engine)
                assert len(cell) in (500, 100), (cfg, len(cell))
                for iid, rec in cell.items():
                    merged[(cfg, iid)] = rec
            assert len(merged) == 600, (arm, engine, len(merged))  # trap-2 audit
            cells[(arm, tag)] = merged

    print("== Per-cell (delivered endpoint, denominator = realized 600) ==")
    summary = {}
    for (arm, tag), m in sorted(cells.items()):
        x = sum(r["correct"] for r in m.values())
        dlv = sum(r["delivered"] for r in m.values())
        ext = sum(r["extracted"] for r in m.values())
        inj = sum(r["injected"] for r in m.values())
        lo, hi = wilson(x, 600)
        summary[(arm, tag)] = x
        cge = 100 * x / ext if ext else 0.0
        print(f"{arm:8s} {tag}: correct {x}/600 = {x/6:.1f}% "
              f"[{100*lo:.1f},{100*hi:.1f}]  delivered {dlv}  extracted {ext} "
              f"({100*ext/600:.1f}%)  P(corr|ext) {cge:.1f}%  injected {inj}")

    print("\n== Tools-cell mediators (side-logs) ==")
    for arm, cfgs in ARMS.items():
        n = d = le = 0
        for cfg in cfgs:
            a, b, c = sidelog_stats(cfg)
            n, d, le = n + a, d + b, le + c
        print(f"{arm:8s} WT: n={n} delegation {100*d/n:.1f}%  loop_exhausted {le} ({100*le/n:.1f}%)")

    print("\n== PRIMARY confirmatory family: paired exact McNemar, Holm ==")
    ps = {}
    for arm in ("clean", "mystery"):
        wt, nt = cells[(arm, "WT")], cells[(arm, "NT")]
        b = sum(1 for k in wt if wt[k]["correct"] and not nt[k]["correct"])
        c = sum(1 for k in wt if not wt[k]["correct"] and nt[k]["correct"])
        p = mcnemar_exact(b, c)
        ps[arm] = p
        dwt, dnt = summary[(arm, "WT")], summary[(arm, "NT")]
        delta = (dwt - dnt) / 6
        # CI on paired delta (Wald on difference of paired proportions)
        n = 600
        p1, p2 = dwt / n, dnt / n
        se = math.sqrt((b + c) / n**2 - ((b - c) / n) ** 2 / n)
        print(f"{arm:8s}: WT {dwt}/600 vs NT {dnt}/600  paired Δ={delta:+.1f}pp "
              f"[{100*((p1-p2)-1.959964*se):+.1f},{100*((p1-p2)+1.959964*se):+.1f}] "
              f"b={b} c={c}  exact p={p:.3g}")
    holm = {}
    order = sorted(ps, key=lambda a: ps[a])
    for i, arm in enumerate(order):
        holm[arm] = min(1.0, ps[arm] * (2 - i))
    for j in range(1, len(order)):  # monotonicity
        holm[order[j]] = max(holm[order[j]], holm[order[j - 1]])
    for arm in ("clean", "mystery"):
        print(f"{arm:8s}: Holm-adjusted p = {holm[arm]:.3g} -> "
              f"{'SIGNIFICANT' if holm[arm] < 0.05 else 'not significant'} at .05")

    print("\n== Band verdict, mystery WT (amendment K, n=600) ==")
    x = summary[("mystery", "WT")]
    verdict = next((v for v, f in BANDS if f(x)), "INCONCLUSIVE")
    print(f"mystery WT successes x={x} -> {verdict}")
    print(f"conjunctive ruling input: mystery Holm-significant={holm['mystery']<0.05}, band={verdict}")

    print("\n== Clean-t1 apparatus criterion (outcome-neutral) ==")
    m = cells[("clean", "WT")]
    ext = sum(r["extracted"] for r in m.values())
    x = sum(r["correct"] for r in m.values())
    a_ok = ext / 600 >= 0.90
    b_ok = (x / ext if ext else 0) >= 0.90
    print(f"(a) extraction {ext}/600 = {100*ext/600:.1f}% -> {'PASS' if a_ok else 'FAIL'}")
    print(f"(b) P(correct|extracted) {x}/{ext} = {100*x/ext:.1f}% -> {'PASS' if b_ok else 'FAIL'}")

    print("\n== Paired clean-vs-mystery WT delta (margin ±7.5pp reference) ==")
    cw, mw = cells[("clean", "WT")], cells[("mystery", "WT")]
    # pair by pool position: (cfg base, iid) — mystery cfgs are renames of clean cfgs
    diffs_b = diffs_c = 0
    for (cfg, iid), r in cw.items():
        mr = mw[(("mystery_" + cfg), iid)]
        if r["correct"] and not mr["correct"]:
            diffs_b += 1
        elif mr["correct"] and not r["correct"]:
            diffs_c += 1
    d = (summary[("clean", "WT")] - summary[("mystery", "WT")]) / 6
    print(f"|clean_WT - mystery_WT| = {abs(d):.1f}pp (b={diffs_b}, c={diffs_c}, "
          f"exact p={mcnemar_exact(diffs_b, diffs_c):.3g})")


if __name__ == "__main__":
    main()
