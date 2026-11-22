#!/usr/bin/env python3
"""RQ3 pilot: does the loss of correct tool results shrink when the context window grows?

    python -m tools.reanalysis.rq3_context_pilot [--numbers] [--marketplace ../pddl-copilot]

Post hoc and descriptive. The D1c smoke of 2026-10-27 reran the solve and
simulate tool trials of the first problem of every domain (20 problems, six
wordings, 120 trials per model and task) with a 32K and a 64K context window
(`results/d1-smokes/*_d1c-ctx{32k,64k}`). The delivered rerun ran the same
trials at 16K. This script compares the three windows on exactly the trial keys
all three hold, with the frozen delivered grader on every row:

  tool right   the stored harness grade (the right tool returned the right result);
  lost         of those, the delivered final answer is wrong (the RQ3 measure);
  empty        the final answer is empty.

Simulate problems whose run plan is not the cached plan in any of the three
runs are left out (ISS-029; they cannot be graded against the cached trace).
Solve verdicts come from the cached table of the rerun where the plan is in it,
else from the live validator through the frozen `run.live_verdicts`.

Limits, stated with the table: 120 trials per cell from 20 problems; the 16K
run and the two smoke runs are separate jobs weeks apart; nothing here was
registered. It is a pilot.

Outputs (tools/reanalysis/out/): rq3_context_pilot.json, rq3_context_pilot.md;
with --numbers spliced into development/NUMBERS.md (tag RQ3-CONTEXT-PILOT).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from pddl_eval.scoring import (_coerce_simulate_trajectory, _normalize_trajectory,
                               strip_leaked_channel_prefix)
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import e4 as E4
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.e2e_regrade import oracle_canon_for
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
TASKS = ("solve", "simulate")
WINDOWS = (("16K", None), ("32K", "d1c-ctx32k"), ("64K", "d1c-ctx64k"))


def smoke_rows(root: Path, model: str, tag: str) -> list:
    """Rows of one smoke cell as frozen-package `Row` objects.

    The frozen loader (`schema.parse_row`) cannot read these cells: it refuses
    any row whose prompt exceeds the registered 16,384-token window, which is
    the point of this run. The rows are therefore built field by field from
    the stored JSON, with the same field meanings, and then go through the
    frozen grader unchanged. Rows cut by storage or lost to infrastructure
    halt the script."""
    cell = f"slurm_vllm_{model}_off_tools_all_minimal_{tag}"
    rows = {}
    with (root / cell / "trials.jsonl").open() as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            key, r = obj["key"], obj["result"]
            t = r.get("tokens") or {}
            if r.get("infra_failure") or r.get("response_truncated_by_storage"):
                raise R1.Halt(f"{cell}: an infrastructure or storage-cut row ({key[1:4]})")
            row = S.Row(
                layer=S.RERUN, cell=cell, model_tag=model, task=key[1], domain=key[2],
                problem=key[3], plan_label=key[4] or "", variant=int(key[5]), with_tools=True,
                prompt_style="minimal", success=bool(r["success"]),
                tool_selected=r.get("tool_selected"), response=r.get("response") or "",
                response_truncated_by_storage=False,
                tool_calls=tuple(S.ToolCall(c.get("name"), c.get("arguments"),
                                            c.get("result") or "")
                                 for c in (r.get("tool_calls") or [])),
                tokens=S.Tokens(
                    prompt=int(t.get("prompt") or 0), completion=int(t.get("completion") or 0),
                    turns=int(t.get("turns") or 0),
                    ctx_clipped_turns=int(t.get("ctx_clipped_turns") or 0),
                    ctx_clip_last_turn_max_tokens=t.get("ctx_clip_last_turn_max_tokens"),
                    ctx_clip_last_turn_prompt_tokens=t.get("ctx_clip_last_turn_prompt_tokens"),
                    ctx_no_room_turns=int(t.get("ctx_no_room_turns") or 0)),
                error=r.get("error") or "", failure_reason=r.get("failure_reason") or "",
                truncated=bool(r.get("truncated")), done_reason=r.get("done_reason") or "",
                infra_failure=False)
            rows[row.trial_key] = row
    return list(rows.values())


def line_reader_steps(response: str) -> list[dict] | None:
    """The trace an answer holds when every line that is one JSON object is taken
    as one step, normalised like every other trace. None when no such line is
    found or the lines do not form a trace."""
    objs = []
    for ln in strip_leaked_channel_prefix(response or "").splitlines():
        ln = ln.strip().rstrip(",")
        if not (ln.startswith("{") and ln.endswith("}")):
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            objs.append(o)
    if not objs:
        return None
    steps, _compliant = _coerce_simulate_trajectory(json.dumps(objs))
    return None if steps is None else _normalize_trajectory(steps)


def line_reader_exact(response: str, oracle) -> bool:
    """A more lenient reading than the frozen grader: every line that is one JSON
    object is taken as one step, and the steps must equal the oracle trace exactly.
    The frozen grader reads a single JSON value only, so a trace written one object
    per line fails it whatever its content. This is the mechanical aid the hand
    read of the rerun's undecided rows used (reference/delivered_rerun_secondary)."""
    if oracle is None:
        return False
    steps = line_reader_steps(response)
    return steps is not None and steps == oracle


def run_plan(rows) -> dict:
    """problem -> the plan most simulate rows passed to get_state_transition."""
    seen = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r.task != "simulate":
            continue
        for c in r.tool_calls:
            if c.name == "get_state_transition":
                p = R1.plan_argument(c.arguments.get("plan") if isinstance(c.arguments, dict) else None)
                if p:
                    seen[(r.domain, r.problem)][p] += 1
                break
    out = {}
    for k, v in seen.items():
        top = max(v, key=v.get)
        if v[top] >= R1.SIM_PLAN_AGREEMENT * sum(v.values()):   # same rule as rq1_metrics
            out[k] = top
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--smoke-root", type=Path)
    ap.add_argument("--marketplace", type=Path, default=REPO.parent / "pddl-copilot")
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    smoke_root = args.smoke_root or args.results / "d1-smokes"
    try:
        cells, grades16, gt_cache = R1.load_rerun_cells(args)
        data = {}                                   # (model, window) -> rows
        for m in C.PART_A_MODELS:
            data[(m, "16K")] = [r for r in cells["rerun_a"][m].rows
                                if r.task in TASKS and r.problem == "p01"]
            for w, tag in WINDOWS[1:]:
                data[(m, w)] = [r for r in smoke_rows(smoke_root, m, tag) if r.task in TASKS]
        table = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
                 for e in json.loads(args.plan_verdicts.read_text())}
        need = set()
        for (m, w), rows in data.items():
            if w != "16K":
                need |= G.solve_plans_to_validate(rows)
        missing = need - set(table)
        live = 0
        if missing:
            table.update(asyncio.run(RUN.live_verdicts(missing, args.domains_dir,
                                                       args.marketplace)))
            live = len(missing)
        ref = {(d, p): tuple(R1.norm_action(a) for a in e["plan"])
               for d, probs in gt_cache.items() for p, e in probs.items()
               if isinstance(e, dict) and e.get("plan")}
        out, skipped = [], {}
        for m in C.PART_A_MODELS:
            bad = set()
            for w, _ in WINDOWS:
                for k, plan in run_plan(data[(m, w)]).items():
                    if plan != ref.get(k):
                        bad.add(k)
            skipped[model_name(m)] = sorted(f"{d}/{p}" for d, p in bad)
            for task in TASKS:
                per = {}
                for w, _ in WINDOWS:
                    per[w] = {r.trial_key: r for r in data[(m, w)] if r.task == task
                              and not (task == "simulate" and (r.domain, r.problem) in bad)}
                keys = set(per["16K"]) & set(per["32K"]) & set(per["64K"])
                for w, _ in WINDOWS:
                    rs = [per[w][k] for k in sorted(keys)]
                    g = [grades16[(r.cell, r.trial_key)] if w == "16K"
                         else G.grade(r, gt_cache, table) for r in rs]
                    tool_right = [(r, x) for r, x in zip(rs, g) if r.success is True]
                    lost = [x.ok is False for _, x in tool_right]
                    why = defaultdict(int)
                    rescued = 0
                    for r, x in tool_right:
                        if x.ok is False:
                            why[E4.classify(r, x, gt_cache)[0]] += 1
                            if task == "simulate" and line_reader_exact(
                                    r.response, oracle_canon_for(gt_cache, {
                                        "domain_name": r.domain, "problem_name": r.problem})):
                                rescued += 1
                    lenient = [(x.ok is False) and not (task == "simulate" and line_reader_exact(
                        r.response, oracle_canon_for(gt_cache, {"domain_name": r.domain,
                                                                "problem_name": r.problem})))
                               for r, x in tool_right]
                    out.append({
                        "model": model_name(m), "task": task, "window": w, "n": len(rs),
                        "empty": sum(not strip_leaked_channel_prefix(r.response).strip()
                                     for r in rs),
                        "tool_right": len(tool_right), "lost": sum(lost),
                        "why": dict(sorted(why.items(), key=lambda kv: -kv[1])),
                        "right_under_line_reader": rescued,
                        "lost_share_lenient": R1.boot(lenient, [r.domain for r, _ in tool_right]),
                        "lost_cut_by_output_cap": sum(
                            1 for r, x in tool_right if x.ok is False
                            and r.done_reason == "length"),
                        "lost_share": R1.boot(lost, [r.domain for r, _ in tool_right]),
                        "delivered": R1.boot([x.ok is True for x in g],
                                             [r.domain for r in rs])})
    except (R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    L = ["*Generated by `tools/reanalysis/rq3_context_pilot.py`. Post hoc pilot, descriptive. "
         "Solve and simulate tool trials (plain and steered wordings together) of the first "
         "problem of each domain, on the trial keys that the 16K delivered rerun and the 32K "
         "and 64K smoke runs of 2026-10-27 all hold; every row graded by the frozen delivered "
         "grader. \"Tool right\" = the right tool returned the right result. \"Lost\" = of "
         "those, the delivered final answer is wrong. Intervals are 95% domain-cluster "
         "bootstrap. Separate jobs weeks apart, 20 problems, nothing registered. The "
         "categories are those of the frozen readout's E4 (`tools/delivered_rerun/e4.py`); "
         "NEEDS_READING marks answers a fixed rule cannot decide. \"After also reading one "
         "object per line\" is a more lenient grade than the frozen one: a trace written as "
         "one JSON object per line counts when it equals the oracle trace exactly. Simulate "
         "problems left out because a run's plan is not the cached plan: "
         + "; ".join(f"{k}: {', '.join(v) or 'none'}" for k, v in skipped.items())
         + f". Solve plans validated live for this table: {live}.*", ""]
    L.append(md_table(["model", "task", "window", "trials", "empty final answer", "tool right",
                       "lost", "lost, share of tool right", "delivered right",
                       "lost, share after also reading one object per line",
                       "lost answers by registered category",
                       "lost answers that stopped at the output cap"],
                      [[c["model"], c["task"], c["window"], c["n"],
                        f"{c['empty']} ({100 * c['empty'] / c['n']:.1f}%)", c["tool_right"],
                        c["lost"], R1.cell(c["lost_share"]), R1.cell(c["delivered"]),
                        R1.cell(c["lost_share_lenient"]) if c["task"] == "simulate" else "–",
                        "; ".join(f"{k} {v}" for k, v in c["why"].items()) or "–",
                        c["lost_cut_by_output_cap"]]
                       for c in out]))
    md = "\n".join(L) + "\n"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq3_context_pilot.json").write_text(
        json.dumps({"cells": out, "skipped": skipped, "live_validated": live}, indent=1) + "\n")
    (args.out / "rq3_context_pilot.md").write_text(md)
    names = {"Gemma-26B": "Gemma-MoE-26B"}
    by = {(c["model"], c["task"], c["window"]): c for c in out}
    tex = []
    for m in ("Qwen3.5-9B", "Gemma-26B", "Qwen3.6-35B"):
        for i, t in enumerate(("solve", "simulate")):
            cs = [by[(m, t, w)] for w, _ in WINDOWS]
            tex.append(" & ".join(
                [names.get(m, m) if i == 0 else "", f"\\emph{{{t}}}", f"${cs[0]['n']}$",
                 *[f"${100 * c['empty'] / c['n']:.1f}$" for c in cs],
                 *[f"${c['lost_share']['est']:.1f}$ {{\\scriptsize$[{c['lost_share']['lo']:.1f},"
                   f"\\,{c['lost_share']['hi']:.1f}]$}}" for c in cs]]) + r" \\")
    (args.out / "tex").mkdir(exist_ok=True)
    (args.out / "tex" / "rq3_context_pilot.tex").write_text("\n".join(tex) + "\n")
    print(md)
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", "RQ3-CONTEXT-PILOT", md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
