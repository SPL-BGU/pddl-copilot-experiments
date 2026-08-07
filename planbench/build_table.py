#!/usr/bin/env python3
"""Render the PlanBench v1 (no-tools vanilla) accuracy table from a synced
canonical results tree.

Usage:
    python3 planbench/build_table.py <results-root> [<results-root> ...]
    # <results-root> = a dir containing <config>/<engine>/task_*.json
    # (rsync of external/LLMs-Planning/plan-bench/results/)
    # Multiple roots are searched in order, first hit per cell wins. This
    # matters because the graded corpora are SPLIT across trees: the bare-NT
    # t1 headline lives in results/haiku-frontier/planbench/, the WT prereg
    # arms live in external/LLMs-Planning/plan-bench/results/, and
    # results/planbench/canonical/ holds the vllm rows — no single tree can
    # render every OURS row (review finding, 2026-08-06).

Per-task metric: ``llm_correct_binary`` for t3 (plan verification), else
``llm_correct``. TWO numbers are emitted per cell:
  * Accuracy (PlanBench-comparable) = correct / TOTAL attempted; an empty /
    loop-exhausted instance (metric field unset) is scored INCORRECT, never
    dropped. This is the published PlanBench convention — correct over the full
    instance set — used for the gpt-4 / davinci baselines in this very table,
    so our rows sit on the SAME denominator as the literature numbers beside
    them. (A drop-empties denominator silently put our rows on a more lenient
    yardstick than the baselines printed next to them, overstating the tools
    arm exactly where it truncates to empty; see paper_notes_discussions.md
    2026-06-14.)
  * Success-given-completion (diagnostic) = correct / COMPLETED instances
    (those that produced a gradeable answer). Isolates the NL->PDDL
    formalization wall: low accuracy with high success-given-completion means
    the model fails by not answering, not by being wrong. NEVER cite this
    beside the literature.
For the v1 no-tools vanilla engines every instance is graded, so the two
coincide (the v1 table is unchanged by this fix); they diverge exactly where
the tools arm truncates to empty.

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
from functools import lru_cache

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
# Per-config footnotes: the `_3` extension pools are n=100 PER CELL (vs 500 in
# the base pools) — without this flag a reader compares 49.0 (n=100) against
# 31.4 (n=500) as if they were the same measurement. The published number is
# the UNION of the pool pair (amendment K: gpt-4 clean 157/500 + 49/100 =
# 206/600 = 34.3%); this table renders the pools separately and the union is
# computed in the results doc, not here. The mystery gpt-4 caveat is
# prereg-declared: that t3 corpus is a DIFFERENT candidate-plan draw (0/500
# identical queries), so its number is context, never a controlled contrast.
CONFIG_NOTES = {
    "blocksworld_3": "all cells n=100; union with BLOCKSWORLD = the published "
                     "600-pool (amendment K)",
    "mystery_blocksworld_3": "all cells n=100; union with MYSTERY_BLOCKSWORLD "
                             "= the 600-pool (amendment K)",
    "mystery_blocksworld": "gpt-4_chat here is t3-only and a DIFFERENT "
                           "candidate-plan corpus (prereg: non-comparable "
                           "context, not a contrast)",
}

OURS = [
    ("pddl_copilot__vllm__Qwen3.5:0.8B", "ours: Qwen3.5-0.8B"),
    ("pddl_copilot__vllm__Qwen3.5:4B", "ours: Qwen3.5-4B"),
    ("pddl_copilot__vllm__Qwen3.5:9B", "ours: Qwen3.5-9B"),
    ("pddl_copilot__vllm__qwen3.6:35b", "ours: Qwen3.6-35B"),
    # Frontier rows. `anthropic` = the graded 06-22 bare-NT layer (Act 4
    # headline). The two below are the PlanBench-WT prereg arms (ratified
    # 2026-07-30): tools, and its matched-scaffold no-tools control. Presentation
    # rule (prereg §7): WT rows must NOT be read across the separator against the
    # gpt-4 baseline as a controlled contrast — the controlled contrast is
    # WT vs matched-NT within Haiku. See amendment M for the reference-line rule.
    ("pddl_copilot__anthropic__claude-haiku-4-5", "ours: Haiku-4.5 (bare NT)"),
    ("pddl_copilot__anthropic-scaffold__claude-haiku-4-5", "ours: Haiku-4.5 matched-NT"),
    # §9-A ladder rung 3 (amendment A): the WT scaffold with its dangling
    # directive, NO tools. Graded corpora exist for the mystery pools only
    # (the arm is Mystery-t1-only by design) — clean-pool cells render '-'.
    # Was missing from this list while its 600 graded instances sat on disk
    # (review finding, 2026-08-06).
    ("pddl_copilot__anthropic-directive__claude-haiku-4-5", "ours: Haiku-4.5 +directive"),
    ("pddl_copilot__anthropic-tools__claude-haiku-4-5", "ours: Haiku-4.5 +tools"),
]
# Baseline rows per config — every engine with a graded file on disk for that
# config (audited 2026-08-06): gpt-4_chat has t1+t2+t3(+...) for blocksworld
# (n=500) and blocksworld_3 (n=100), but ONLY t3 for the two mystery configs;
# text-davinci-002 exists for blocksworld (500) and blocksworld_3 (100).
# Union across each pool pair is the published 600 (gpt-4 clean t1:
# 157 + 49 = 206 = 34.3%), which is why amendment K redefined the sample as
# both pools together. Fresh list per key — a shared list object would let a
# later in-place edit mutate several configs at once.
def _gpt4():
    return [("gpt-4_chat", "PlanBench: gpt-4_chat")]


def _davinci():
    return [("text-davinci-002", "PlanBench: davinci-002")]


BASELINES = {
    "blocksworld": _gpt4() + _davinci(),
    "blocksworld_3": _gpt4() + _davinci(),
    "mystery_blocksworld": _gpt4(),
    "mystery_blocksworld_3": _gpt4(),
}


def _metric(task: str) -> str:
    return "llm_correct_binary" if "verification" in task else "llm_correct"


def _find(roots: tuple[str, ...], config: str, eng: str, pattern: str):
    """First matching file across the ordered roots (see module docstring:
    the graded corpora are split across trees)."""
    for root in roots:
        fs = glob.glob(os.path.join(root, config, eng, pattern))
        if fs:
            return fs[0]
    return None


@lru_cache(maxsize=None)
def acc(roots: tuple[str, ...], config: str, eng: str, task: str):
    """Return (acc_total, acc_completed, n_total, n_completed).

    acc_total     = correct / total attempted; empty / loop-exhausted instances
                    (metric field unset) count as INCORRECT, never dropped. The
                    PlanBench-comparable number (same denominator as the gpt-4 /
                    davinci baselines).
    acc_completed = correct / instances that produced a gradeable answer.
                    Diagnostic ONLY (isolates the formalization wall); never cite
                    beside the literature.
    Returns (None, None, 0, 0) when the cell has no file / no dict instances.
    Cached: render() re-reads every cell once per view and completion_rate
    re-reads all nine tasks per engine — ~4x re-parsing without the cache.
    """
    f_path = _find(roots, config, eng, task + ".json")
    if f_path is None:
        return None, None, 0, 0
    with open(f_path) as fh:
        d = json.load(fh)
    insts = [i for i in d.get("instances", d if isinstance(d, list) else [])
             if isinstance(i, dict)]
    if not insts:
        return None, None, 0, 0
    f = _metric(task)
    completed = [i for i in insts if i.get(f) is not None]
    correct = sum(1 for i in insts if i.get(f))
    n_total, n_done = len(insts), len(completed)
    acc_total = 100 * correct / n_total
    acc_done = 100 * correct / n_done if n_done else None
    return acc_total, acc_done, n_total, n_done


@lru_cache(maxsize=None)
def emit_rate(roots: tuple[str, ...], config: str, eng: str):
    """t3 verdict-emission rate: fraction of non-empty responses that parsed
    into a valid/invalid verdict (extracted_llm_plan['valid'] is not None)."""
    f_path = _find(roots, config, eng, "task_3_*.json")
    if f_path is None:
        return None
    with open(f_path) as fh:
        d = json.load(fh)
    insts = d.get("instances", d if isinstance(d, list) else [])
    ne = [i for i in insts if isinstance(i, dict) and str(i.get("llm_raw_response", "")).strip()]
    if not ne:
        return None
    em = [i for i in ne if isinstance(i.get("extracted_llm_plan"), dict)
          and i["extracted_llm_plan"].get("valid") is not None]
    return 100 * len(em) / len(ne)


def completion_rate(roots: tuple[str, ...], config: str, eng: str):
    """Overall answered/attempted across all tasks for one engine — the size of
    the formalization wall. Returns (pct, n_attempted) or (None, 0)."""
    done = tot = 0
    for t in TASKS:
        _, _, n_total, n_done = acc(roots, config, eng, t)
        done += n_done
        tot += n_total
    return (100 * done / tot, tot) if tot else (None, 0)


def _cells(roots: tuple[str, ...], config: str, eng: str, pick: int):
    """One row of formatted cells; pick=0 -> acc_total, pick=1 -> acc_completed."""
    out = []
    for t in TASKS:
        a = acc(roots, config, eng, t)[pick]
        out.append("  -  " if a is None else f"{a:5.1f}")
    return out


# Two views per config: the headline (PlanBench-comparable, total denominator)
# and the diagnostic (success-given-completion) that exposes the NL->PDDL wall.
VIEWS = [
    (0, "acc %: PlanBench-comparable — correct / TOTAL N (empty/exhausted = INCORRECT)"),
    (1, "success-given-completion % — correct / COMPLETED (DIAGNOSTIC, not literature-comparable)"),
]


def render(roots: tuple[str, ...]) -> None:
    hdr = "{:26s} ".format("engine \\ task") + " ".join(f"{s:>5s}" for s in SHORT)
    # blocksworld + blocksworld_3 together are the published 600-instance pool
    # (amendment K); the mystery variants are their pure-rename counterparts.
    for config in ("blocksworld", "blocksworld_3", "mystery_blocksworld",
                   "mystery_blocksworld_3", "logistics"):
        rows = OURS + ([("__sep__", "")] + BASELINES[config] if config in BASELINES else [])
        for pick, title in VIEWS:
            print("\n" + "=" * len(hdr))
            print(f"  PlanBench {config.upper()}  ({title}; t3=correct_binary)")
            print("=" * len(hdr))
            print(hdr)
            print("-" * len(hdr))
            for eng, lab in rows:
                if eng == "__sep__":
                    print("-" * len(hdr))
                    continue
                print(f"{lab:26s} " + " ".join(_cells(roots, config, eng, pick)))
            print("-" * len(hdr))
        # Footnotes (shared by both views for this config)
        print("  * t7 (plan_execution) EXCLUDED: PlanBench's exact-match state parser")
        print("    can't read verbose/markdown output (scores 0 even when the predicted")
        print("    state is correct); not a fair cell for any engine — see findings doc.")
        if config in CONFIG_NOTES:
            print(f"  * {CONFIG_NOTES[config]}")
        crs = []
        for eng, lab in OURS:
            cr, _ = completion_rate(roots, config, eng)
            if cr is not None and cr < 100:
                crs.append(f"{lab.split(': ')[1]} {cr:.0f}%")
        if crs:
            print("  * completion rate (answered / attempted; <100% = formalization wall — the")
            print(f"    gap between the two tables above): {' | '.join(crs)}")
        _short = dict(zip(TASKS, SHORT))
        small = [f"{_short.get(t, t)} n={n}" for (cfg, t), n in SMALL_N.items() if cfg == config]
        if small:
            print(f"  * small-n (PlanBench ships few instances): {', '.join(small)}")
        ems = []
        for eng, lab in OURS:
            e = emit_rate(roots, config, eng)
            if e is not None:
                ems.append(f"{lab.split(': ')[1]} {e:.0f}%")
        if ems:
            print(f"  * t3 verdict-emission rate (format adherence): {' | '.join(ems)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: build_table.py <results-root> [<results-root> ...]")
    render(tuple(sys.argv[1:]))
