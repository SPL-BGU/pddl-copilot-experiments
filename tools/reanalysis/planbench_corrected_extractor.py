"""Q2 re-analysis: PlanBench regrade with a corrected plan extractor (C15).

Post hoc sensitivity analysis. NOT the preregistered instrument and NOT a
replacement for the shipped grader: the shipped upstream extractor
(external/LLMs-Planning/plan-bench/utils/text_to_pddl.py) and the pinned
analysis code under planbench/ are imported and run, never modified.

The shipped extractor has two known faults on this corpus:
  1. it scans the WHOLE response, so action-like lines in the model's
     reasoning are injected into the plan (479/600 Mystery no-tools trials);
  2. it only recognises the benchmark's long English phrasing with the full
     object name ("feast object b from object c", "pick up the red block"),
     so a plan written in PDDL shorthand ("feast b c", "(feast b c)",
     "pick-up yellow") extracts to nothing (125/569 delivered Mystery
     with-tools plans).

The corrected extractor (rules fixed in this file, same for every cell):
  R1. Scope = the text between the LAST "[PLAN]" tag and the "[PLAN END]"
      that follows it (end of text if the closing tag is missing). No block,
      or a block with no parseable action = failure (no validator call).
  R2. One action per line. Lower-case; strip list numbering/bullets,
      markdown emphasis, back-ticks, surrounding parentheses, trailing
      punctuation.
  R3. The line must START with an action name. Clean: pick up / pick-up /
      pickup / pick_up, put down / put-down / putdown / put_down, stack,
      unstack. Mystery: attack, succumb, overcome, feast.
  R4. After the action name, filler words (the, from, on, top, of, onto, to,
      table, block, object, a few more) are dropped. What remains must be
      exactly as many object tokens as the action has parameters. Clean
      objects are colour words (config `encoded_objects`); Mystery objects
      are single letters a..l, also accepted as object_a / object-a.
      Arguments are taken in order of appearance (same convention as the
      shipped extractor).
  R5. A non-empty line in the block that does not parse is skipped and
      counted. (Sensitivity `strict`: any such line fails the trial.)
  R6. The plan is written in the shipped format, "(action x y)" per line,
      and validated by the pipeline's own `utils.validate_plan` (same VAL
      binary, same domain and instance files).

Variants graded for every trial:
  shipped_full   shipped extractor, whole response  (must reproduce llm_correct)
  shipped_block  shipped extractor, first-block text (the pinned
                 stripped_block_regrade.py definition; fixes fault 1 only)
  corrected      R1-R6, last block                   (PRIMARY corrected reading)
  corrected_first  R1-R6 but FIRST block             (sensitivity)
  corrected_strict R1-R6 + strict R5                 (sensitivity)

Clean with-tools is reported in two readings: first-draw (the 18 resume
re-draws count as failures; the paper's reading) and last-attempt.

Usage (repo root; needs the patched upstream tree and its venv):
  .venv-planbench-wt/bin/python tools/reanalysis/planbench_corrected_extractor.py \
      --out /path/to/outdir
Environment (defaults shown):
  PLANBENCH_DIR = <repo>/external/LLMs-Planning/plan-bench
  VAL           = <repo>/external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables
"""
import argparse
import contextlib
import importlib.util
import io
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
ARCHIVE = REPO / "results/planbench/wt-anthropic-20260801"
PB = Path(os.environ.get("PLANBENCH_DIR", REPO / "external/LLMs-Planning/plan-bench"))
os.environ.setdefault(
    "VAL", str(REPO / "external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables"))

ENGINES = {"NT": "pddl_copilot__anthropic-scaffold__claude-haiku-4-5",
           "WT": "pddl_copilot__anthropic-tools__claude-haiku-4-5"}
DOMAINS = {"clean": ["blocksworld", "blocksworld_3"],
           "mystery": ["mystery_blocksworld", "mystery_blocksworld_3"]}

# ---------------------------------------------------------------- extractor
FILLER = {"the", "from", "on", "top", "of", "onto", "to", "table", "block",
          "object", "off", "upon"}
CLEAN_ACTIONS = {"pick-up": 1, "put-down": 1, "stack": 2, "unstack": 2}
MYSTERY_ACTIONS = {"attack": 1, "succumb": 1, "overcome": 2, "feast": 2}
_PREFIX = re.compile(r"^\s*(?:step\s*\d+\s*[:.)-]\s*|\d+\s*[.):-]\s*|[-*•>]+\s+)")
_CLEAN_HEAD = [
    (re.compile(r"^pick[\s_-]?up\b"), "pick-up"),
    (re.compile(r"^put[\s_-]?down\b"), "put-down"),
    (re.compile(r"^unstack\b"), "unstack"),
    (re.compile(r"^stack\b"), "stack"),
]


def plan_block(text, which="last"):
    """Return the plan-block body, or None when the response has no [PLAN] tag."""
    if "[PLAN]" not in text:
        return None
    after = text.rsplit("[PLAN]", 1)[1] if which == "last" else text.split("[PLAN]", 1)[1]
    return after.split("[PLAN END]", 1)[0]


def _clean_line(line):
    line = line.strip().lower()
    line = re.sub(r"[*`\"']", "", line)
    prev = None
    while prev != line:
        prev = line
        line = _PREFIX.sub("", line).strip()
    line = line.strip("()[] \t")
    return line.rstrip(".;,:").strip()


def parse_line(line, kind, colours):
    """Return (action, [objs]) in PDDL names, or None if the line is not an action."""
    line = _clean_line(line)
    if not line:
        return "blank"
    if kind == "clean":
        action = None
        for rx, name in _CLEAN_HEAD:
            m = rx.match(line)
            if m:
                action, rest = name, line[m.end():]
                break
        if action is None:
            return None
        arity = CLEAN_ACTIONS[action]
    else:
        m = re.match(r"^(attack|succumb|overcome|feast)\b", line)
        if not m:
            return None
        action, rest = m.group(1), line[m.end():]
        arity = MYSTERY_ACTIONS[action]
    toks = [t for t in re.split(r"[\s,()]+", rest) if t]
    objs = []
    for t in toks:
        t = t.strip(".;:")
        if not t or t in FILLER:
            continue
        if kind == "clean":
            if t in colours:
                objs.append(colours[t])
            else:
                return None
        else:
            m = re.fullmatch(r"(?:object[_-]?)?([a-l])", t)
            if m:
                objs.append(m.group(1))
            else:
                return None
    if len(objs) != arity:
        return None
    return action, objs


def corrected_extract(text, kind, colours, which="last"):
    """Return dict(plan=str, n_actions, n_unparsed, unparsed=[...], status)."""
    body = plan_block(text, which)
    if body is None:
        return dict(plan="", n_actions=0, n_unparsed=0, unparsed=[], status="no_block")
    acts, bad = [], []
    for raw in body.splitlines():
        got = parse_line(raw, kind, colours)
        if got == "blank":
            continue
        if got is None:
            bad.append(raw.strip())
        else:
            acts.append("({} {})".format(got[0], " ".join(got[1])))
    status = "ok" if acts else ("empty_block" if not bad else "no_action_in_block")
    return dict(plan="".join(a + "\n" for a in acts), n_actions=len(acts),
                n_unparsed=len(bad), unparsed=bad, status=status)


# ---------------------------------------------------------------- statistics
def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - h) / d, 100 * (c + h) / d)


def mcnemar_exact(b, c):
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    # log-space to survive tiny p-values
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + n * math.log(0.5) for i in range(k + 1)]
    m = max(logs)
    return min(1.0, 2 * math.exp(m) * sum(math.exp(x - m) for x in logs))


def _load_tost():
    spec = importlib.util.spec_from_file_location(
        "pb_tost", Path(__file__).with_name("planbench_equivalence_tost.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- grading
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="output dir (rows.jsonl, summary.json)")
    args = ap.parse_args()
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="pb_regrade_"))
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="pb_plans_"))
    plan_file = str(tmp / "plan")

    os.chdir(PB)
    sys.path.insert(0, ".")
    with contextlib.redirect_stderr(io.StringIO()):
        from tarski.io import PDDLReader
        from utils import validate_plan
        from utils.text_to_pddl import text_to_plan

    def val(dom, inst, plan):
        if not plan.strip():
            return False
        Path(plan_file).write_text(plan)
        return bool(validate_plan(dom, inst, plan_file))

    # first-draw: ids re-drawn on the 08-01 resume (first draw delivered nothing)
    recs = [json.loads(ln) for ln in open(ARCHIVE / "sidelogs/blocksworld__anthropic-tools.jsonl")]
    ids = [int(r["instance_id"]) for r in recs]
    redrawn = {i for i in set(ids) if ids.count(i) > 1}

    rows = []
    for kind, cfgs in DOMAINS.items():
        for cfg in cfgs:
            data = yaml.safe_load(open(f"configs/{cfg}.yaml"))
            dom = f"./instances/{data['domain_file']}"
            tpl = f"./instances/{data['instance_dir']}/{data['instances_template']}"
            colours = {v.split()[0]: k for k, v in data["encoded_objects"].items()} \
                if kind == "clean" else {}
            for arm, engine in ENGINES.items():
                res = json.load(open(ARCHIVE / f"graded/{cfg}/{engine}/task_1_plan_generation.json"))
                by_id = {int(r["instance_id"]): r for r in res["instances"]}
                for iid in range(data["start"] + 1, data["end"] + 2):  # ids 2..end+1
                    r = by_id.get(iid, {})
                    text = r.get("llm_raw_response") or ""
                    inst = tpl.format(iid)
                    row = dict(kind=kind, cfg=cfg, arm=arm, iid=iid,
                               pair=(cfg.replace("mystery_", ""), iid),
                               delivered=bool(text),
                               shipped=bool(r.get("llm_correct")),
                               redrawn=(cfg == "blocksworld" and arm == "WT" and iid in redrawn))
                    for k in ("shipped_full", "shipped_block", "corrected",
                              "corrected_first", "corrected_strict"):
                        row[k] = False
                    row.update(status="not_delivered", n_actions=0, n_unparsed=0,
                               unparsed=[], plan="", shipped_plan="", injected=False,
                               shipped_n=0, block_lines=0)
                    if text:
                        reader = PDDLReader(raise_on_error=True)
                        reader.parse_domain(dom)
                        problem = reader.parse_instance(inst)
                        try:
                            sp, _ = text_to_plan(text, problem.actions, plan_file, data)
                        except Exception:
                            sp = ""
                        row["shipped_plan"] = sp
                        row["shipped_n"] = len([x for x in sp.splitlines() if x.strip()])
                        row["shipped_full"] = val(dom, inst, sp)
                        fb = plan_block(text, "first")
                        listed = [x for x in (fb or "").splitlines() if x.strip()]
                        row["block_lines"] = len(listed)
                        row["injected"] = row["shipped_n"] > len(listed)  # audit definition
                        if fb is not None and fb.strip():
                            try:
                                bp, _ = text_to_plan(fb, problem.actions, plan_file, data)
                            except Exception:
                                bp = ""
                            row["shipped_block"] = val(dom, inst, bp)
                        ce = corrected_extract(text, kind, colours, "last")
                        row.update(status=ce["status"], n_actions=ce["n_actions"],
                                   n_unparsed=ce["n_unparsed"], unparsed=ce["unparsed"],
                                   plan=ce["plan"])
                        row["corrected"] = val(dom, inst, ce["plan"])
                        row["corrected_strict"] = row["corrected"] and ce["n_unparsed"] == 0
                        cf = corrected_extract(text, kind, colours, "first")
                        row["corrected_first"] = (row["corrected"] if cf["plan"] == ce["plan"]
                                                  else val(dom, inst, cf["plan"]))
                    rows.append(row)
            print(f"graded {cfg}", file=sys.stderr)

    with open(out / "rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    report(rows, out)


def report(rows, out):
    tost = _load_tost()
    VARS = ["shipped", "shipped_full", "shipped_block", "corrected",
            "corrected_first", "corrected_strict"]

    def cellmap(kind, arm, var, reading="first-draw"):
        m = {}
        for r in rows:
            if r["kind"] == kind and r["arm"] == arm:
                ok = bool(r[var])
                if reading == "first-draw" and r["redrawn"]:
                    ok = False
                m[tuple(r["pair"])] = ok
        assert len(m) == 600, (kind, arm, len(m))
        return m

    summary = {"cells": [], "contrasts": [], "checks": {}}
    mism = sum(r["shipped"] != r["shipped_full"] for r in rows)
    summary["checks"]["shipped_full_vs_archive_mismatches"] = mism
    print(f"\nCHECK shipped extractor re-run vs archived llm_correct: "
          f"{mism} mismatches over {len(rows)} trials")

    print("\n== cells (n = 600 each; clean WT shown in both readings) ==")
    for kind in ("clean", "mystery"):
        for arm in ("NT", "WT"):
            readings = ["first-draw", "last-attempt"] if (kind, arm) == ("clean", "WT") else ["first-draw"]
            for reading in readings:
                tag = f"{kind} {arm}" + (f" ({reading})" if len(readings) > 1 else "")
                for var in VARS:
                    k = sum(cellmap(kind, arm, var, reading).values())
                    lo, hi = wilson(k, 600)
                    print(f"{tag:28s} {var:17s} {k:3d}/600 = {k/6:5.1f}  [{lo:.1f}, {hi:.1f}]")
                    summary["cells"].append(dict(kind=kind, arm=arm, reading=reading,
                                                 variant=var, k=k, n=600, pct=k / 6,
                                                 wilson=[lo, hi]))
                print()

    print("== extraction bookkeeping (corrected extractor, last block) ==")
    for kind in ("clean", "mystery"):
        for arm in ("NT", "WT"):
            rs = [r for r in rows if r["kind"] == kind and r["arm"] == arm]
            st = {}
            for r in rs:
                st[r["status"]] = st.get(r["status"], 0) + 1
            b = dict(
                delivered=sum(r["delivered"] for r in rs),
                shipped_extracted=sum(r["shipped_n"] > 0 for r in rs),
                corrected_extracted=sum(r["n_actions"] > 0 for r in rs),
                injected_audit_def=sum(r["injected"] for r in rs),
                lost_to_dialect=sum(r["delivered"] and r["shipped_n"] == 0 and r["n_actions"] > 0 for r in rs),
                trials_with_unparsed_lines=sum(r["n_unparsed"] > 0 for r in rs),
                unparsed_lines=sum(r["n_unparsed"] for r in rs),
                flips_0_to_1=sum((not r["shipped"]) and r["corrected"] for r in rs),
                flips_1_to_0=sum(r["shipped"] and not r["corrected"] for r in rs),
                status=st)
            summary["checks"][f"{kind}_{arm}"] = b
            print(f"{kind} {arm}: {b}")

    print("\n== paired contrasts ==")

    def contrast(name, m1, m2, margins=()):
        a = sum(m1[k] and m2[k] for k in m1)
        b = sum(m1[k] and not m2[k] for k in m1)
        c = sum((not m1[k]) and m2[k] for k in m1)
        d = 600 - a - b - c
        p = mcnemar_exact(b, c)
        (lo, hi), _ = tost.tango(a, b, c, d, 0.075)  # 90% score CI
        zsave = tost.Z90
        tost.Z90 = 1.959964
        (lo95, hi95), _ = tost.tango(a, b, c, d, 0.075)
        tost.Z90 = zsave
        rec = dict(name=name, b=b, c=c, delta_pts=100 * (b - c) / 600, mcnemar_p=p,
                   ci95=[100 * lo95, 100 * hi95], ci90=[100 * lo, 100 * hi], tost={})
        line = (f"{name:58s} delta {100*(b-c)/600:+6.2f}  b={b:3d} c={c:3d}  "
                f"95% CI [{100*lo95:+.1f}, {100*hi95:+.1f}]  McNemar p={p:.3g}")
        for mg in margins:
            for mname, fn in (("Wald", tost.wald), ("Tango", tost.tango)):
                (l, u), tp = fn(a, b, c, d, mg)
                met = -mg < l and u < mg
                rec["tost"][f"{mname}_{100*mg:g}"] = dict(ci90=[100 * l, 100 * u], p=tp, met=met)
                line += (f"\n      TOST +-{100*mg:g} {mname}: 90% CI [{100*l:+.2f}, {100*u:+.2f}] "
                         f"p={tp:.4f} -> {'criterion met' if met else 'criterion not met'}")
        print(line)
        summary["contrasts"].append(rec)

    for var in ("shipped", "shipped_block", "corrected", "corrected_first", "corrected_strict"):
        for reading in ("first-draw", "last-attempt"):
            contrast(f"[{var}] clean WT vs NT ({reading})",
                     cellmap("clean", "WT", var, reading), cellmap("clean", "NT", var))
        contrast(f"[{var}] mystery WT vs NT",
                 cellmap("mystery", "WT", var), cellmap("mystery", "NT", var))
        for reading in ("first-draw", "last-attempt"):
            contrast(f"[{var}] clean WT vs mystery WT ({reading})",
                     cellmap("clean", "WT", var, reading), cellmap("mystery", "WT", var),
                     margins=(0.075, 0.10))
        contrast(f"[{var}] clean NT vs mystery NT",
                 cellmap("clean", "NT", var), cellmap("mystery", "NT", var))
        print()

    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(f"rows + summary written to {out}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--report-only":
        d = Path(sys.argv[2])
        report([json.loads(ln) for ln in open(d / "rows.jsonl")], d)
    else:
        main()
