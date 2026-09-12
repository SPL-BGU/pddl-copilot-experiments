"""Verify the committed PlanBench-WT archive reproduces the published numbers.

Data-only (no VAL, no tarski, stdlib + pyyaml): re-derives every count, CI, and
McNemar test quoted in development/planbench/planbench_wt_results_20260803.md
and the paper integration plan from the files committed under
results/planbench/wt-anthropic-20260801/, including the FIRST-DRAW reading
(decision 2026-08-06: Act 4 quotes first-draw; the 18 resume re-draws in the
clean-WT side-log count as failures).

What needs VAL and is therefore NOT re-run here (independently verified
2026-08-06, evidence under .../verification/): the stripped-block regrade
(26/600; 8/8 flip IDs VAL-confirmed) and the old-stack regrade (200/200
identical verdicts).

Usage (repo root):  python3 planbench/analysis/verify_promotion.py
Exits non-zero on any mismatch.
"""
import hashlib
import json
import math
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
D = R / "results/planbench/wt-anthropic-20260801"

BARE = "pddl_copilot__anthropic__claude-haiku-4-5"
SCAFFOLD = "pddl_copilot__anthropic-scaffold__claude-haiku-4-5"
TOOLS = "pddl_copilot__anthropic-tools__claude-haiku-4-5"
DIRECTIVE = "pddl_copilot__anthropic-directive__claude-haiku-4-5"
ARMS = {"clean": ["blocksworld", "blocksworld_3"],
        "mystery": ["mystery_blocksworld", "mystery_blocksworld_3"]}

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        FAILS.append(name)


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * (c - h) / d, 1), round(100 * (c + h) / d, 1)


def mcnemar_exact(b, c):
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) * 0.5 ** n)


def pool_ids(cfg):
    data = yaml.safe_load(open(D / f"configs/{cfg}.yaml"))
    return range(data["start"] + 1, data["end"] + 2)  # ids are 2..end+1


def cell(cfg, engine, task="task_1_plan_generation"):
    """{instance_id(int): correct(bool)} on the full pool, treatment policy."""
    res = json.load(open(D / f"graded/{cfg}/{engine}/{task}.json"))
    rows = {int(r["instance_id"]): bool(r.get("llm_correct")) for r in res["instances"]}
    return {iid: rows.get(iid, False) for iid in pool_ids(cfg)}


def arm(engine, cfgs):
    out = {}
    for cfg in cfgs:
        for iid, ok in cell(cfg, engine).items():
            out[(cfg.replace("mystery_", ""), iid)] = ok
    return out


def main():
    print("== graded cells (delivered endpoint, denominator = declared pool) ==")
    clean_wt = arm(TOOLS, ARMS["clean"])
    clean_nt = arm(SCAFFOLD, ARMS["clean"])
    myst_wt = arm(TOOLS, ARMS["mystery"])
    myst_nt = arm(SCAFFOLD, ARMS["mystery"])
    myst_dir = arm(DIRECTIVE, ARMS["mystery"])
    for name, m, want in (("clean WT (last-attempt)", clean_wt, 418),
                          ("clean matched-NT", clean_nt, 287),
                          ("mystery WT", myst_wt, 431),
                          ("mystery matched-NT", myst_nt, 0)):
        check(f"{name} n", len(m), 600)
        check(f"{name} correct", sum(m.values()), want)
    check("mystery directive n", len(myst_dir), 600)
    print(f"INFO  mystery directive correct: {sum(myst_dir.values())}/600")
    check("bare-NT clean completion half (bw_3)",
          sum(cell("blocksworld_3", BARE).values()), 58)
    check("bare-NT mystery completion half (mbw_3)",
          sum(cell("mystery_blocksworld_3", BARE).values()), 0)

    print("\n== clean-WT side-log: resume re-draws and the first-draw reading ==")
    recs = [json.loads(ln) for ln in open(D / "sidelogs/blocksworld__anthropic-tools.jsonl")]
    ids = [int(r["instance_id"]) for r in recs]
    first = {}
    for r in recs:
        first.setdefault(int(r["instance_id"]), r)
    dups = sorted(i for i in set(ids) if ids.count(i) > 1)
    check("records", len(recs), 518)
    check("unique ids", len(set(ids)), 500)
    check("re-drawn ids", len(dups), 18)
    check("all 18 first draws loop-exhausted, empty",
          all(first[i]["loop_exhausted"] and first[i]["final_text_len"] == 0 for i in dups), True)
    fd = dict(clean_wt)
    for i in dups:
        fd[("blocksworld", i)] = False  # first draw delivered nothing
    check("clean WT (first-draw) correct", sum(fd.values()), 410)
    for cfg in ("blocksworld_3", "mystery_blocksworld", "mystery_blocksworld_3"):
        lines = [json.loads(ln) for ln in open(D / f"sidelogs/{cfg}__anthropic-tools.jsonl")]
        check(f"{cfg} tools side-log single-record",
              len(lines) == len({r["instance_id"] for r in lines}), True)

    print("\n== delegation (last record per id, classic_planner called) ==")
    for cfg in ("blocksworld", "blocksworld_3", "mystery_blocksworld", "mystery_blocksworld_3"):
        last = {}
        for ln in open(D / f"sidelogs/{cfg}__anthropic-tools.jsonl"):
            r = json.loads(ln)
            last[r["instance_id"]] = r
        deleg = sum("classic_planner" in (r.get("tool_names") or []) for r in last.values())
        check(f"{cfg} delegation", f"{deleg}/{len(last)}", f"{len(last)}/{len(last)}")

    print("\n== Wilson CIs (1 dp) ==")
    check("418/600", wilson(418, 600), (65.9, 73.2))
    check("410/600", wilson(410, 600), (64.5, 71.9))
    check("431/600", wilson(431, 600), (68.1, 75.3))
    check("287/600", wilson(287, 600), (43.9, 51.8))
    check("0/600", wilson(0, 600), (0.0, 0.6))

    print("\n== paired exact McNemar (WT vs matched-NT, paired by (cfg, id)) ==")
    for name, wt, blog10 in (("clean last-attempt", clean_wt, None),
                             ("clean FIRST-DRAW", fd, None)):
        b = sum(1 for k in wt if wt[k] and not clean_nt[k])
        c = sum(1 for k in wt if not wt[k] and clean_nt[k])
        p = mcnemar_exact(b, c)
        want = {"clean last-attempt": (206, 75, -14.56), "clean FIRST-DRAW": (202, 79, -12.86)}[name]
        check(f"{name} b,c", (b, c), want[:2])
        check(f"{name} log10(p)", round(math.log10(p), 2), want[2])
    b = sum(1 for k in myst_wt if myst_wt[k] and not myst_nt[k])
    c = sum(1 for k in myst_wt if not myst_wt[k] and myst_nt[k])
    check("mystery b,c", (b, c), (431, 0))
    check("mystery log10(p)", round(math.log10(mcnemar_exact(b, c)), 2), -129.44)

    print("\n== formalization_match rows (mechanism layer) ==")
    rows = [json.loads(ln) for ln in open(D / "sidelogs/formalization_match_rows.jsonl")]
    check("rows", len(rows), 1200)
    m_clean = [r for r in rows if r["kind"] == "clean" and r["match"]]
    m_myst = [r for r in rows if r["kind"] == "mystery" and r["match"]]
    check("clean match", len(m_clean), 578)
    check("mystery match", len(m_myst), 587)
    check("P(correct|match) clean", sum(r["llm_correct"] for r in m_clean), 418)
    check("P(correct|match) mystery", sum(r["llm_correct"] for r in m_myst), 431)
    check("no-match trials", sum(1 for r in rows if not r["match"]), 35)
    check("no-match correct", sum(r["llm_correct"] for r in rows if not r["match"]), 0)
    check("delegated all", all(r["delegated"] for r in rows), True)

    print("\n== archive integrity (MANIFEST.sha256) ==")
    bad = n = 0
    for ln in open(D / "MANIFEST.sha256"):
        digest, rel = ln.strip().split("  ", 1)
        n += 1
        if hashlib.sha256((D / rel).read_bytes()).hexdigest() != digest:
            bad += 1
            print(f"FAIL  hash mismatch: {rel}")
    check(f"manifest ({n} files)", bad, 0)

    print()
    if FAILS:
        raise SystemExit(f"{len(FAILS)} check(s) FAILED: {FAILS}")
    print("ALL CHECKS PASS")


if __name__ == "__main__":
    main()
