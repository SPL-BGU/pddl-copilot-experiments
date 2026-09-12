"""Prereg §4 precondition re-check, extended to the full amendment-K pool.

The prereg's 500/500 claims were verified on the NT query files
(results/haiku-frontier). The confirmatory WT run graded 600/cell
(500-pool + _3 pool). Before formalization_match may use the gold
instance files as reference, re-verify on the ACTUAL WT queries:

  1. NL->gold reconstruction EXACT (init/goal literal-set equality vs the
     gold instance file, objects covered) for every instance in all four
     WT response files (blocksworld{,_3}, mystery_blocksworld{,_3}).
  2. Side-log join integrity: for every deduped side-log record (LAST
     record per instance_id -- the 08-01 pause/resume wrote duplicates),
     query_sha256 matches the response file's query for that instance.

Logic is the recovered 07-2x evidence-workflow code (formalize_check2.py /
myst_check.py, workflow wf_08c98872-d6e): the query embeds a one-shot
example, so the LAST [STATEMENT] block is the test item.
"""
import hashlib
import json
import os
import re
from pathlib import Path

R = Path(__file__).resolve().parents[2]
SIDELOG = Path(os.environ.get("WT_SIDELOG_DIR",
    R / "results/planbench/wt-anthropic-20260801/sidelogs"))
PB = R / "external/LLMs-Planning/plan-bench"
ENGINE = "pddl_copilot__anthropic-tools__claude-haiku-4-5"

CONFIGS = {
    "blocksworld": "blocksworld/generated_basic",
    "blocksworld_3": "blocksworld/generated_basic_3",
    "mystery_blocksworld": "blocksworld/mystery/generated_basic",
    "mystery_blocksworld_3": "blocksworld/mystery/generated_basic_3",
}

OBJ = {"a": "red block", "b": "blue block", "c": "orange block", "d": "yellow block",
       "e": "white block", "f": "magenta block", "g": "black block", "h": "cyan block",
       "i": "green block", "j": "violet block", "k": "silver block", "l": "gold block"}
NL2OBJ = {v: k for k, v in OBJ.items()}
OBJRE = "|".join(sorted(map(re.escape, NL2OBJ), key=len, reverse=True))

LIT_RX = r"\(([a-z][\w-]*(?:\s+[\w-]+)*)\)"


def gold_sets(inst_dir, n):
    t = (PB / "instances" / inst_dir / f"instance-{n}.pddl").read_text()

    def blk(name):
        i = t.index(f"(:{name}")
        d = 0
        for j in range(i, len(t)):
            if t[j] == "(":
                d += 1
            elif t[j] == ")":
                d -= 1
                if d == 0:
                    return t[i:j + 1]

    init = frozenset(re.findall(LIT_RX, blk("init")))
    goal = frozenset(re.findall(LIT_RX, blk("goal")))
    objs = frozenset(re.search(r"\(:objects([^)]*)\)", t).group(1).split())
    return objs, init, goal


def bw_literals(seg):
    out = set()
    objs = set()
    for cl in re.split(r",|\band\b", seg):
        cl = cl.strip().rstrip(".")
        if not cl:
            continue
        m = re.match(rf"the ({OBJRE}) is on top of the ({OBJRE})$", cl)
        if m:
            out.add(f"on {NL2OBJ[m[1]]} {NL2OBJ[m[2]]}")
            objs |= {NL2OBJ[m[1]], NL2OBJ[m[2]]}
            continue
        m = re.match(rf"the ({OBJRE}) is clear$", cl)
        if m:
            out.add(f"clear {NL2OBJ[m[1]]}")
            objs.add(NL2OBJ[m[1]])
            continue
        m = re.match(rf"the ({OBJRE}) is on the table$", cl)
        if m:
            out.add(f"ontable {NL2OBJ[m[1]]}")
            objs.add(NL2OBJ[m[1]])
            continue
        m = re.match(rf"the hand is currently holding (?:the )?({OBJRE})$", cl)
        if m:
            out.add(f"holding {NL2OBJ[m[1]]}")
            objs.add(NL2OBJ[m[1]])
            continue
        if cl == "the hand is empty":
            out.add("handempty")
            continue
        out.add("UNPARSED::" + cl)
    return frozenset(out), objs


def myst_literals(seg):
    out = set()
    for cl in re.split(r",|\band\b", seg):
        cl = cl.strip().rstrip(".")
        if not cl:
            continue
        cl = cl.replace("object ", "")
        m = re.match(r"([a-l]) craves ([a-l])$", cl)
        if m:
            out.add(f"craves {m[1]} {m[2]}")
            continue
        m = re.match(r"(planet|province|pain) ([a-l])$", cl)
        if m:
            out.add(f"{m[1]} {m[2]}")
            continue
        if cl == "harmony":
            out.add("harmony")
            continue
        out.add("UNPARSED::" + cl)
    return frozenset(out)


def check_config(config, inst_dir):
    resp = json.load(open(
        PB / "responses" / config / ENGINE / "task_1_plan_generation.json"))
    mystery = "mystery" in config
    ok = bad = unp = 0
    n = 0
    bad_ids = []
    sha_by_id = {}
    for inst in resp["instances"]:
        q = inst["query"]
        sha_by_id[str(inst["instance_id"])] = hashlib.sha256(q.encode()).hexdigest()
        blocks = re.findall(
            r"\[STATEMENT\]\s*As initial conditions I have that,(.*?)"
            r"My goal is to have that(.*?)\n", q, re.S)
        if not blocks:
            bad_ids.append((inst["instance_id"], "no [STATEMENT] block"))
            continue
        n += 1
        iseg, gseg = blocks[-1]
        gobjs, ginit, ggoal = gold_sets(inst_dir, inst["instance_id"])
        if mystery:
            init, goal = myst_literals(iseg), myst_literals(gseg)
            o_ok = True
        else:
            (init, o1), (goal, o2) = bw_literals(iseg), bw_literals(gseg)
            o_ok = (o1 | o2) <= gobjs
        if any(x.startswith("UNPARSED") for x in init | goal):
            unp += 1
            bad_ids.append((inst["instance_id"], "unparsed clause"))
            continue
        if init == ginit and goal == ggoal and o_ok:
            ok += 1
        else:
            bad += 1
            bad_ids.append((inst["instance_id"], "set mismatch"))
    return n, ok, bad, unp, bad_ids, sha_by_id


def check_sidelog_join(config, sha_by_id):
    """Dedupe (LAST record per instance_id) and check sha256 join."""
    path = SIDELOG / f"{config}__anthropic-tools.jsonl"
    last = {}
    total = 0
    for line in open(path):
        rec = json.loads(line)
        last[str(rec["instance_id"])] = rec
        total += 1
    mismatch = [iid for iid, rec in last.items()
                if sha_by_id.get(iid) != rec["query_sha256"]]
    missing = sorted(set(sha_by_id) - set(last), key=int)
    return total, len(last), mismatch, missing


if __name__ == "__main__":
    grand_ok = grand_n = 0
    for config, inst_dir in CONFIGS.items():
        n, ok, bad, unp, bad_ids, sha_by_id = check_config(config, inst_dir)
        grand_ok += ok
        grand_n += n
        print(f"{config}: parseable [STATEMENT] {n} | reconstruction EXACT {ok} "
              f"| mismatch {bad} | unparsed {unp}")
        for iid, why in bad_ids[:5]:
            print(f"    instance {iid}: {why}")
        total, dedup, mismatch, missing = check_sidelog_join(config, sha_by_id)
        print(f"  side-log: {total} records -> {dedup} deduped | "
              f"sha mismatches {len(mismatch)} | response-instances missing "
              f"from side-log {len(missing)}{missing[:5] if missing else ''}")
    print(f"\nTOTAL reconstruction: {grand_ok}/{grand_n}")
