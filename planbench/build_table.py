#!/usr/bin/env python3
"""Render the PlanBench v1 (no-tools vanilla) accuracy table from a synced
canonical results tree.

Usage:
    python3 planbench/build_table.py <results-root>
    # <results-root> = a dir containing <config>/<engine>/task_*.json
    # (rsync of external/LLMs-Planning/plan-bench/results/)

Per-task metric: ``llm_correct_binary`` for t3 (plan verification), else
``llm_correct``. Accuracy = correct / graded, where graded = instances with
the metric field set (matches PlanBench's published convention; for our
engines every generated instance is graded).

Caveat surfaced by --emit: PlanBench grades by exact-format string match
(``text_to_plan`` / ``text_to_state``). Models that wrap the answer in
reasoning / markdown instead of the bare few-shot template are penalised even
when the underlying content is correct (esp. t7 plan-execution: a verbose
state description pollutes the extracted state with spurious tokens). Read low
vanilla scores as a *strict-format* result, not pure planning incapability.
"""
from __future__ import annotations

import glob
import json
import os
import sys

# t7 (plan_execution) is EXCLUDED from the comparison: PlanBench grades it by
# exact-match on an extracted STATE (text_to_state), which cannot read the
# verbose/markdown output our models emit — the extractor scrapes spurious
# tokens and scores 0 even when the predicted state is correct (verified:
# Qwen3.6-35B's extracted set == ground truth + one stray bare 'clear'). The
# same parser graded gpt-4 (28.4), so t7 is not a fair cell for ANY engine
# here; it is reported as n/a* with the confound called out, not as a 0.
TASKS = [
    "task_1_plan_generation", "task_2_plan_optimality", "task_3_plan_verification",
    "task_4_plan_reuse", "task_5_plan_generalization", "task_6_replanning",
    "task_8_1_goal_shuffling", "task_8_2_full_to_partial", "task_8_3_partial_to_full",
]
SHORT = ["t1", "t2", "t3", "t4", "t5", "t6", "t8_1", "t8_2", "t8_3"]
# Cells with non-standard instance counts, flagged in the footnote.
SMALL_N = {("logistics", "task_5_plan_generalization"): 12}

OURS = [
    ("pddl_copilot__vllm__Qwen3.5:0.8B", "ours: Qwen3.5-0.8B"),
    ("pddl_copilot__vllm__Qwen3.5:4B", "ours: Qwen3.5-4B"),
    ("pddl_copilot__vllm__Qwen3.5:9B", "ours: Qwen3.5-9B"),
    ("pddl_copilot__vllm__qwen3.6:35b", "ours: Qwen3.6-35B"),
]
BASELINES = {"blocksworld": [("gpt-4_chat", "PlanBench: gpt-4_chat"),
                             ("text-davinci-002", "PlanBench: davinci-002")]}


def _metric(task: str) -> str:
    return "llm_correct_binary" if "verification" in task else "llm_correct"


def acc(root: str, config: str, eng: str, task: str):
    """Return (accuracy_pct, n_graded) or (None, 0) if no file/data."""
    fs = glob.glob(os.path.join(root, config, eng, task + ".json"))
    if not fs:
        return None, 0
    d = json.load(open(fs[0]))
    insts = d.get("instances", d if isinstance(d, list) else [])
    f = _metric(task)
    g = [i for i in insts if isinstance(i, dict) and i.get(f) is not None]
    if not g:
        return None, 0
    return 100 * sum(1 for i in g if i[f]) / len(g), len(g)


def emit_rate(root: str, config: str, eng: str):
    """t3 verdict-emission rate: fraction of non-empty responses that parsed
    into a valid/invalid verdict (extracted_llm_plan['valid'] is not None)."""
    fs = glob.glob(os.path.join(root, config, eng, "task_3_*.json"))
    if not fs:
        return None
    d = json.load(open(fs[0]))
    insts = d.get("instances", d if isinstance(d, list) else [])
    ne = [i for i in insts if isinstance(i, dict) and str(i.get("llm_raw_response", "")).strip()]
    if not ne:
        return None
    em = [i for i in ne if isinstance(i.get("extracted_llm_plan"), dict)
          and i["extracted_llm_plan"].get("valid") is not None]
    return 100 * len(em) / len(ne)


def render(root: str) -> None:
    hdr = "{:26s} ".format("engine \\ task") + " ".join(f"{s:>5s}" for s in SHORT)
    for config in ("blocksworld", "logistics"):
        print("\n" + "=" * len(hdr))
        print(f"  PlanBench {config.upper()}  (no-tools vanilla; acc % over graded; t3=correct_binary)")
        print("=" * len(hdr))
        print(hdr)
        print("-" * len(hdr))
        rows = OURS + ([("__sep__", "")] + BASELINES[config] if config in BASELINES else [])
        for eng, lab in rows:
            if eng == "__sep__":
                print("-" * len(hdr))
                continue
            cells = []
            for t in TASKS:
                a, _ = acc(root, config, eng, t)
                cells.append("  -  " if a is None else f"{a:5.1f}")
            print(f"{lab:26s} " + " ".join(cells))
        # Footnotes
        print("-" * len(hdr))
        print("  * t7 (plan_execution) EXCLUDED: PlanBench's exact-match state parser")
        print("    can't read verbose/markdown output (scores 0 even when the predicted")
        print("    state is correct); not a fair cell for any engine — see findings doc.")
        _short = dict(zip(TASKS, SHORT))
        small = [f"{_short.get(t, t)} n={n}" for (cfg, t), n in SMALL_N.items() if cfg == config]
        if small:
            print(f"  * small-n (PlanBench ships few instances): {', '.join(small)}")
        ems = []
        for eng, lab in OURS:
            e = emit_rate(root, config, eng)
            if e is not None:
                ems.append(f"{lab.split(': ')[1]} {e:.0f}%")
        if ems:
            print(f"  * t3 verdict-emission rate (format adherence): {' | '.join(ems)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: build_table.py <results-root>")
    render(sys.argv[1])
