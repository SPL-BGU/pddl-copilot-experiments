#!/usr/bin/env python3
"""RQ2 and RQ3 metrics: does the model choose the right tool, and does it use
the tool's output properly?

    python -m tools.reanalysis.rq23_metrics [--numbers]

Post hoc and descriptive (development/reference/roadmap.md, milestone M4). Read-only over
results/. Nothing here is a registered endpoint.

RQ2 (tool choice). Every with-tools trial offered all seven tools. Each trial
falls in exactly one of four classes, by the set of tools it called:

  no call        no tool was called;
  right only     only the task's right tool (any number of times);
  right + other  the right tool and at least one other tool;
  other only     tools were called, the right one never.

The advisors' three figures follow: "exactly the right tool and no other" =
right only; "the right tool was called" = right only + right + other; "other
tools were called as well" = right + other + other only.

The right tool: validate_domain, validate_problem, validate_plan for the three
validation tasks; get_state_transition for simulate; for solve the planner that
fits the domain (classic_planner on a classical domain, numeric_planner on a
numeric one). This is stricter on solve than the harness, whose `tool_selected`
accepts either planner. Self-check: the harness rule applied to the stored
calls equals the stored `tool_selected` on every row. For solve, two kinds of
"other" call are shown on their own: the other planner, and a plan check
(validate_plan) with nothing else beside the right planner.

RQ2 reads the stored tool calls, which every corpus kept in full, so it covers
the main sweep (five open models, thinking off and on), the delivered rerun
(three models, thinking off; and Gemma under the neutral system prompt) and
the Claude runs. The three are separate apparatus and are never pooled.

RQ3 (use of the output). Among the trials where the tool returned the right
result (tool-verified: the stored harness grade on a with-tools row), the
share whose delivered final answer is wrong. It needs the full final answer,
so it is computed on the rerun and the Claude runs only. For the rerun this is
the frozen readout's E4 cell (same rows, same grades, same categories); the
script recomputes it with the frozen functions and halts unless every cell
equals the readout. For Claude the delivered grade is the e2e overlay's
`e2e_strict`; an answer cut at the storage cap has an unknown grade and makes
the share a range.

Outputs (tools/reanalysis/out/): rq23_metrics.json, rq2_metrics.md,
rq3_metrics.md; with --numbers the two markdown files are spliced into
development/NUMBERS.md (tags RQ2-METRICS and RQ3-METRICS).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tools.delivered_rerun import analysis as A
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis.bc_common import domain_track
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
PLANNERS = ("classic_planner", "numeric_planner")
HARNESS_TOOLS = {"solve": set(PLANNERS), "validate_domain": {"validate_domain"},
                 "validate_problem": {"validate_problem"}, "validate_plan": {"validate_plan"},
                 "simulate": {"get_state_transition"}}
CLASSES = ("none", "right_only", "right_plus", "other_only")
MAIN_MODELS = ("Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b")
PLAIN, STEERED = (11, 12, 13), (14, 15, 16)
E4_WORDS = {
    "REFUSED_OR_CLIPPED_FINAL": "final turn refused or clipped (no room left)",
    "NO_FINAL_ANSWER": "no final answer",
    "TOOL_INPUT_ERROR": "tool input error",
    "SUMMARY_ONLY": "a summary, not the output",
    "ABRIDGED": "output shortened",
    "WRONG_WRAPPER": "right content, unreadable format",
    "NUMERIC_OMITTED": "numeric values left out",
    "WRONG_FACTS": "content differs from the tool's",
    "NEEDS_READING": "not decidable by rule",
}


# ------------------------------------------------------------------ pure helpers
def right_tool(task: str, track: str | None) -> str:
    """The one right tool of a trial (for solve it depends on the domain)."""
    if task == "solve":
        if track not in ("classical", "numeric"):
            raise ValueError(f"solve needs the domain track, got {track!r}")
        return "classic_planner" if track == "classical" else "numeric_planner"
    (only,) = HARNESS_TOOLS[task]
    return only


def classify(task: str, track: str | None, names: list[str]) -> dict:
    """Class of one trial by the set of tools it called, plus the solve notes."""
    called = set(names)
    right = right_tool(task, track)
    if not called:
        cls = "none"
    elif right in called:
        cls = "right_only" if called == {right} else "right_plus"
    else:
        cls = "other_only"
    others = called - {right}
    return {
        "cls": cls,
        "harness_called": bool(called & HARNESS_TOOLS[task]),
        "other_planner": task == "solve" and bool(others & set(PLANNERS)),
        "plan_check_only": task == "solve" and cls == "right_plus" and others == {"validate_plan"},
    }


def arm_of(variant: int) -> str:
    if variant in PLAIN:
        return "plain"
    if variant in STEERED:
        return "steered"
    raise ValueError(f"variant {variant} is in no arm")


# ------------------------------------------------------------------ RQ2 rows
def row2(corpus, model, think, arm, task, domain, names, tool_selected, track) -> dict:
    c = classify(task, track.get(domain), names)
    c.update(corpus=corpus, model=model, think=think, arm=arm, task=task, domain=domain,
             tool_selected=tool_selected)
    return c


def rq2_rows(args, cells) -> list[dict]:
    track = domain_track()
    out = []
    for m in MAIN_MODELS:                                   # main sweep
        for think in ("off", "on"):
            cell = args.canonical_root / f"slurm_vllm_{m}_{think}_tools_all_minimal"
            for key, res in R1.read_trials(cell / "trials.jsonl").items():
                if res.get("infra_failure"):
                    continue
                out.append(row2("main sweep", model_name(m), think, arm_of(int(key[5])), key[1],
                                key[2], [c["name"] for c in (res.get("tool_calls") or [])],
                                res.get("tool_selected"), track))
    for m, lc in cells["rerun_a"].items():                  # delivered rerun
        for r in lc.rows:
            out.append(row2("rerun", model_name(m), "off", r.arm, r.task, r.domain,
                            [c.name for c in r.tool_calls], r.tool_selected, track))
    for r in cells["rerun_b"].rows:                         # Gemma, neutral system prompt
        out.append(row2("rerun", model_name(C.PART_B_MODEL), "off", f"neutral, {r.arm}", r.task,
                        r.domain, [c.name for c in r.tool_calls], r.tool_selected, track))
    for name, (_nt, corpus) in R1.FRONTIER.items():         # Claude
        for key, res in R1.read_trials(args.results / corpus / "trials.jsonl").items():
            if int(key[5]) != R1.FRONTIER_VARIANT or res.get("infra_failure"):
                continue
            out.append(row2("Claude", name, "off", "plain", key[1], key[2],
                            [c.get("name") for c in (res.get("tool_calls") or [])],
                            res.get("tool_selected"), track))
    bad = [r for r in out if r["tool_selected"] is not None
           and bool(r["tool_selected"]) != r["harness_called"]]
    if bad:
        ex = bad[0]
        raise R1.Halt(f"{len(bad)} rows where the harness rule on the stored calls differs from "
                      f"the stored tool_selected (first: {ex['corpus']} {ex['model']} "
                      f"{ex['task']} {ex['domain']})")
    return out


def rq2(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[(r["corpus"], r["model"], r["think"], r["arm"], r["task"])].append(r)
    cells = []
    for (corpus, m, think, arm, task), rs in by.items():
        dom = [r["domain"] for r in rs]
        k = Counter(r["cls"] for r in rs)
        cells.append({
            "corpus": corpus, "model": m, "think": think, "arm": arm, "task": task, "n": len(rs),
            "counts": {c: k[c] for c in CLASSES},
            "exactly_right": R1.boot([r["cls"] == "right_only" for r in rs], dom),
            "right_called": R1.boot([r["cls"] in ("right_only", "right_plus") for r in rs], dom),
            "other_called": R1.boot([r["cls"] in ("right_plus", "other_only") for r in rs], dom),
            "no_call": R1.boot([r["cls"] == "none" for r in rs], dom),
            "other_planner": sum(r["other_planner"] for r in rs),
            "plan_check_only": sum(r["plan_check_only"] for r in rs),
        })
    return {"cells": cells, "rows": len(rows)}


# ------------------------------------------------------------------ RQ3
def rq3_rerun(cells, grades, gt_cache, readout) -> list[dict]:
    want = {(e["model"], e["task"], e["arm"]): e for e in readout["e4"]}
    out, bad = [], []
    for m, lc in cells["rerun_a"].items():
        rows = list(lc.rows)
        for task in C.TASKS:
            for arm in C.ARMS:
                g = A.e4_cell(rows, grades, gt_cache, m, task, arm)
                e = want.get((m, task, arm))
                if e is None or (g.n_tool_correct, g.n_gap, g.categories) != (
                        e["n_tool_correct"], e["n_gap"], e["categories"]):
                    bad.append(f"E4 {m}/{task}/{arm}")
                tv = [r for r in rows if r.task == task and r.arm == arm and r.success is True]
                lost = [grades[(r.cell, r.trial_key)].ok is False for r in tv]
                out.append({"corpus": "rerun", "model": model_name(m), "arm": arm, "task": task,
                            "n_trials": sum(r.task == task and r.arm == arm for r in rows),
                            "n_tool_right": g.n_tool_correct, "n_lost": g.n_gap, "n_unknown": 0,
                            "lost": R1.boot(lost, [r.domain for r in tv]),
                            "why": {k: v for k, v in g.categories.items() if v}})
    if bad:
        raise R1.Halt("RQ3 cells do not reproduce the frozen readout's E4:\n  " + "\n  ".join(bad))
    return out


def rq3_claude(args) -> list[dict]:
    out = []
    for name, (_nt, corpus) in R1.FRONTIER.items():
        by = defaultdict(list)
        with (args.results / "derived" / "e2e_overlay" / f"{corpus}.e2e.jsonl").open() as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                o = json.loads(ln)
                if int(o["prompt_variant"]) != R1.FRONTIER_VARIANT or o.get("infra_failure"):
                    continue
                by[o["task"]].append(o)
        for task in TASKS:
            rs = by.get(task, [])
            tv = [o for o in rs if o["tool_verified"] is True]
            known = [o for o in tv if o["e2e_strict"] in (True, False)]
            lost = [o for o in known if o["e2e_strict"] is False]
            out.append({"corpus": "Claude", "model": name, "arm": "plain", "task": task,
                        "n_trials": len(rs), "n_tool_right": len(tv), "n_lost": len(lost),
                        "n_unknown": len(tv) - len(known),
                        "lost": R1.boot([o["e2e_strict"] is False for o in tv],
                                        [o["domain_name"] for o in tv]),
                        "why": dict(Counter(o["e2e_reason"] for o in lost))})
    return out


# ------------------------------------------------------------------ render
ARM_WORDS = {"plain": "plain", "steered": "steered", "neutral, plain": "neutral prompt, plain",
             "neutral, steered": "neutral prompt, steered"}
CORPORA = (("main sweep", "Main sweep (Study 1), five open models, thinking off and on"),
           ("rerun", "Delivered rerun (Study 2), thinking off"),
           ("Claude", "Claude runs, wording v11"))


def render_rq2(res: dict) -> str:
    L = []
    w = L.append
    w("*Generated by `tools/reanalysis/rq23_metrics.py`. Post hoc and descriptive. Every "
      "with-tools trial offered all seven tools. Rates are percent of the cell's trials with "
      "95% domain-cluster bootstrap percentile intervals. The three corpora are separate "
      "apparatus and are never pooled. \"Plain\" = tools offered with no instruction to use "
      "one; \"steered\" = one added sentence naming the tool; \"neutral prompt\" = the system "
      "prompt without its use-the-tool policy sentence (Gemma, validate_plan only). "
      "Self-check: the harness rule applied to the stored calls equals the stored "
      f"`tool_selected` on all {res['rows']} rows.*")
    w("")
    cells = res["cells"]
    for corpus, title in CORPORA:
        sub = [c for c in cells if c["corpus"] == corpus]
        by = {(c["model"], c["think"], c["arm"], c["task"]): c for c in sub}
        keys = list(dict.fromkeys((c["model"], c["think"], c["arm"]) for c in sub))
        tasks = [t for t in TASKS if any(c["task"] == t for c in sub)]
        w(f"#### RQ2. {title}")
        w("")
        for field, name in (("exactly_right", "exactly the right tool and no other (higher is better)"),
                            ("right_called", "the right tool was called (higher is better)"),
                            ("other_called", "another tool was called, with or without the right one (lower is better)"),
                            ("no_call", "no tool was called")):
            w(f"Share of trials where {name}:")
            w("")
            w(md_table(["model", "thinking", "prompt", *tasks],
                       [[m, th, ARM_WORDS[a], *[R1.cell(by[(m, th, a, t)][field])
                                                if (m, th, a, t) in by else "–" for t in tasks]]
                        for m, th, a in keys]))
            w("")
        solve = [c for c in sub if c["task"] == "solve"]
        w("Solve, counts behind the shares (trials; the right tool is the planner that fits "
          "the domain):")
        w("")
        w(md_table(["model", "thinking", "prompt", "trials", "no call", "right only",
                    "right + other", "other only", "called the other planner",
                    "right planner + a plan check only"],
                   [[c["model"], c["think"], ARM_WORDS[c["arm"]], c["n"], c["counts"]["none"],
                     c["counts"]["right_only"], c["counts"]["right_plus"],
                     c["counts"]["other_only"], c["other_planner"], c["plan_check_only"]]
                    for c in solve]))
        w("")
    return "\n".join(L) + "\n"


def render_rq3(res: dict) -> str:
    L = []
    w = L.append
    w("*Generated by `tools/reanalysis/rq23_metrics.py`. Post hoc and descriptive. \"Tool "
      "right\" = trials where the right tool returned the right result (tool-verified). "
      "\"Lost\" = of those, the delivered final answer is wrong; share in percent with a 95% "
      "domain-cluster bootstrap percentile interval. Rerun cells are the frozen readout's E4 "
      "cells (the script halts unless all 30 reproduce); the \"why\" column is E4's frozen "
      "categories in plain words. Claude: delivered grade from the e2e overlay; \"unknown\" = "
      "answers cut at the 16,384-character storage cap, counted as not lost in the share, so "
      "the true share lies between lost and lost + unknown. Open models and Claude are never "
      "pooled. Frozen grades: ISS-028 (a correct plan followed by the goal facts counts as "
      "lost on solve) is not corrected here; its post hoc split is the ISS-028 line under "
      "\"Delivered rerun — readout\".*")
    w("")
    for corpus, title in (("rerun", "Delivered rerun, three open models, thinking off"),
                          ("Claude", "Claude runs, wording v11")):
        w(f"#### RQ3. {title}")
        w("")
        rows = []
        for c in res[corpus]:
            if corpus == "rerun":
                why = "; ".join(f"{E4_WORDS[k]} {v}" for k, v in
                                sorted(c["why"].items(), key=lambda kv: -kv[1]))
            else:
                why = "; ".join(f"{k} {v}" for k, v in
                                sorted(c["why"].items(), key=lambda kv: -kv[1]))
            rows.append([c["model"], ARM_WORDS[c["arm"]], c["task"], c["n_trials"],
                         c["n_tool_right"], c["n_lost"],
                         *([c["n_unknown"]] if corpus == "Claude" else []),
                         R1.cell(c["lost"]) if c["n_tool_right"] else "–", why or "–"])
        w(md_table(["model", "prompt", "task", "trials", "tool right", "lost",
                    *(["unknown"] if corpus == "Claude" else []), "lost, share of tool right",
                    "why (count)"], rows))
        w("")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    try:
        cells, grades, gt_cache = R1.load_rerun_cells(args)
        readout = json.loads(args.readout_json.read_text())
        res2 = rq2(rq2_rows(args, cells))
        res3 = {"rerun": rq3_rerun(cells, grades, gt_cache, readout), "Claude": rq3_claude(args)}
    except (R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed, ValueError) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    md2, md3 = render_rq2(res2), render_rq3(res3)
    (args.out / "rq23_metrics.json").write_text(
        json.dumps({"frozen_package_sha256": R1.FROZEN_SHA, "rq2": res2, "rq3": res3},
                   indent=1) + "\n")
    (args.out / "rq2_metrics.md").write_text(md2)
    (args.out / "rq3_metrics.md").write_text(md3)
    print(f"wrote {args.out}/rq23_metrics.json, rq2_metrics.md, rq3_metrics.md")
    if args.numbers:
        numbers = REPO / "development" / "NUMBERS.md"
        changed = [write_numbers(numbers, "RQ2-METRICS", md2),
                   write_numbers(numbers, "RQ3-METRICS", md3)]
        print("NUMBERS.md " + ("updated" if any(changed) else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
