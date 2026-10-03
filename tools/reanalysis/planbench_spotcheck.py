"""Spot-check helper for the corrected-extractor regrade (Q2).

Two independent checks on rows.jsonl written by planbench_corrected_extractor.py:

1. FULL cross-check: every corrected plan (all 2400 trials) is re-validated by
   a small pure-Python STRIPS simulator of the 4-operator Blocksworld / Mystery
   domain, reading init and goal straight from the instance .pddl files. It
   shares no code with VAL, tarski or the upstream utils. Any disagreement
   with the VAL verdict is listed.

2. HAND sample: prints, for a fixed list of targeted trials plus a seeded
   random draw, the tail of the raw response (the model's plan block), the
   shipped extraction, the corrected extraction, the gold plan and the raw
   VAL output from a direct subprocess call, so a human can read them.

Usage (repo root):
  python3 tools/reanalysis/planbench_spotcheck.py ROWS_DIR [--show]
"""
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARCHIVE = REPO / "results/planbench/wt-anthropic-20260801"
PB = Path(os.environ.get("PLANBENCH_DIR", REPO / "external/LLMs-Planning/plan-bench"))
VAL = Path(os.environ.get(
    "VAL", REPO / "external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables")) / "validate"
INST = {"blocksworld": "blocksworld/generated_basic",
        "blocksworld_3": "blocksworld/generated_basic_3",
        "mystery_blocksworld": "blocksworld/mystery/generated_basic",
        "mystery_blocksworld_3": "blocksworld/mystery/generated_basic_3"}
DOM = {"clean": "blocksworld/generated_domain.pddl",
       "mystery": "blocksworld/mystery/generated_domain.pddl"}
ENG = {"NT": "pddl_copilot__anthropic-scaffold__claude-haiku-4-5",
       "WT": "pddl_copilot__anthropic-tools__claude-haiku-4-5"}
# mystery -> clean vocabulary (the rename, from the two domain files)
REN = {"attack": "pick-up", "succumb": "put-down", "overcome": "stack", "feast": "unstack",
       "province": "clear", "planet": "ontable", "harmony": "handempty",
       "pain": "holding", "craves": "on"}


def read_instance(cfg, iid):
    txt = (PB / "instances" / INST[cfg] / f"instance-{iid}.pddl").read_text().lower()
    init = txt.split("(:init", 1)[1].split("(:goal", 1)[0]
    goal = txt.split("(:goal", 1)[1]
    atoms = lambda s: {tuple(REN.get(w, w) for w in m.split())
                       for m in re.findall(r"\(([a-z][a-z0-9\- ]*)\)", s) if m.strip() != "and"}
    return atoms(init), atoms(goal)


def simulate(cfg, iid, plan):
    """True iff the plan is executable and reaches the goal (4-op Blocksworld)."""
    state, goal = read_instance(cfg, iid)
    steps = [ln.strip("() \n").split() for ln in plan.splitlines() if ln.strip()]
    if not steps:
        return False
    for st in steps:
        a, args = REN.get(st[0], st[0]), st[1:]
        if a == "pick-up":
            x, = args
            pre = {("clear", x), ("ontable", x), ("handempty",)}
            add, dele = {("holding", x)}, pre
        elif a == "put-down":
            x, = args
            pre = {("holding", x)}
            add, dele = {("clear", x), ("handempty",), ("ontable", x)}, pre
        elif a == "stack":
            x, y = args
            pre = {("clear", y), ("holding", x)}
            add, dele = {("handempty",), ("clear", x), ("on", x, y)}, pre
        elif a == "unstack":
            x, y = args
            pre = {("on", x, y), ("clear", x), ("handempty",)}
            add, dele = {("holding", x), ("clear", y)}, pre
        else:
            return False
        if not pre <= state:
            return False
        state = (state - dele) | add
    return goal <= state


def direct_val(row):
    with tempfile.NamedTemporaryFile("w", suffix=".plan", delete=False) as f:
        f.write(row["plan"])
    out = subprocess.run(
        [str(VAL), str(PB / "instances" / DOM[row["kind"]]),
         str(PB / "instances" / INST[row["cfg"]] / f"instance-{row['iid']}.pddl"), f.name],
        capture_output=True, text=True).stdout
    os.unlink(f.name)
    return out


def main():
    d = Path(sys.argv[1])
    show = "--show" in sys.argv
    rows = [json.loads(ln) for ln in open(d / "rows.jsonl")]

    dis = [r for r in rows if r["delivered"] and simulate(r["cfg"], r["iid"], r["plan"]) != r["corrected"]]
    dis_ship = [r for r in rows if r["delivered"]
                and simulate(r["cfg"], r["iid"], r["shipped_plan"]) != r["shipped"]]
    print(f"independent simulator vs VAL, corrected plans: {len(dis)} disagreements "
          f"over {sum(r['delivered'] for r in rows)} delivered trials")
    print(f"independent simulator vs VAL, shipped plans:   {len(dis_ship)} disagreements")
    for r in dis + dis_ship:
        print("  DISAGREE", r["cfg"], r["arm"], r["iid"])

    key = lambda r: (r["cfg"], r["arm"], r["iid"])
    by = {key(r): r for r in rows}
    rng = random.Random(20261002)
    groups = {
        "mystery WT, lost to dialect, now correct":
            [r for r in rows if r["kind"] == "mystery" and r["arm"] == "WT"
             and r["shipped_n"] == 0 and r["corrected"]],
        "mystery WT, injected, now correct":
            [r for r in rows if r["kind"] == "mystery" and r["arm"] == "WT"
             and r["shipped_n"] > 0 and not r["shipped"] and r["corrected"]],
        "mystery WT, delivered, still wrong":
            [r for r in rows if r["kind"] == "mystery" and r["arm"] == "WT"
             and r["delivered"] and not r["corrected"]],
        "mystery NT, 0 -> 1":
            [r for r in rows if r["kind"] == "mystery" and r["arm"] == "NT" and r["corrected"]],
        "mystery NT, injected, still wrong":
            [r for r in rows if r["kind"] == "mystery" and r["arm"] == "NT"
             and r["injected"] and not r["corrected"]],
        "clean WT, 0 -> 1":
            [r for r in rows if r["kind"] == "clean" and r["arm"] == "WT"
             and not r["shipped"] and r["corrected"]],
        "clean WT, unparsed lines in block":
            [r for r in rows if r["kind"] == "clean" and r["arm"] == "WT" and r["n_unparsed"]],
        "clean NT, unchanged": [r for r in rows if r["kind"] == "clean" and r["arm"] == "NT"],
        "two plan blocks": [r for r in rows if r["corrected"] != r["corrected_first"]],
    }
    take = {"mystery WT, lost to dialect, now correct": 8, "mystery WT, injected, now correct": 3,
            "mystery WT, delivered, still wrong": 3, "mystery NT, 0 -> 1": 4,
            "mystery NT, injected, still wrong": 3, "clean WT, 0 -> 1": 11,
            "clean WT, unparsed lines in block": 2, "clean NT, unchanged": 2,
            "two plan blocks": 3}
    n = 0
    for g, rs in groups.items():
        rs = sorted(rs, key=key)
        pick = rs if len(rs) <= take[g] else rng.sample(rs, take[g])
        print(f"\n######## {g}: {len(rs)} trials, showing {len(pick)}")
        for r in sorted(pick, key=key):
            n += 1
            sim = simulate(r["cfg"], r["iid"], r["plan"])
            v = direct_val(r) if r["plan"] else "(no plan, VAL not called)"
            verdict = "Plan valid" if "Plan valid" in v else "not valid"
            print(f"[{n:02d}] {r['cfg']} {r['arm']} #{r['iid']}: shipped={int(r['shipped'])} "
                  f"shipped_block={int(r['shipped_block'])} corrected={int(r['corrected'])} "
                  f"| direct VAL: {verdict} | simulator: {sim} | actions shipped/corrected "
                  f"{r['shipped_n']}/{r['n_actions']} | unparsed {r['unparsed']}")
            if show:
                res = json.load(open(ARCHIVE / f"graded/{r['cfg']}/{ENG[r['arm']]}/task_1_plan_generation.json"))
                rec = next(x for x in res["instances"] if int(x["instance_id"]) == r["iid"])
                t = rec["llm_raw_response"]
                i = t.rfind("[PLAN]")
                print("   --- response tail (from 200 chars before the last [PLAN]) ---")
                print("   " + t[max(0, i - 200):][:900].replace("\n", "\n   "))
                print("   --- shipped extraction:  ", r["shipped_plan"].replace("\n", " "))
                print("   --- corrected extraction:", r["plan"].replace("\n", " "))
                print("   --- gold plan:           ", rec["ground_truth_plan"].replace("\n", " "))


if __name__ == "__main__":
    main()
