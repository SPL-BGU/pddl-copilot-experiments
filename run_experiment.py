#!/usr/bin/env python3
"""
Reproduce experiments from:
  "Toward PDDL Planning Copilot" (Benyamin et al., 2025)
  https://arxiv.org/abs/2509.12987

Evaluates vLLM-served LLMs with and without MCP planning tools on 5 PDDL tasks:
  1. solve           — find a plan for a domain+problem
  2. validate_domain — check domain PDDL syntax
  3. validate_problem— check problem PDDL syntax
  4. validate_plan   — verify a plan is correct
  5. simulate        — produce a state-transition trace

Requires the pddl-copilot marketplace plugins (pddl-solver, pddl-validator).
Clone https://github.com/SPL-BGU/pddl-copilot and point --marketplace-path at it.

Usage:
  pip3 install -r requirements.txt
  python3 run_experiment.py --marketplace-path /path/to/pddl-copilot --models qwen3:0.6b qwen3:4b
  python3 run_experiment.py --marketplace-path /path/to/pddl-copilot --tasks solve validate_plan
"""

import argparse
import asyncio
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from pddl_eval.chat import (
    MCPPlanner,
    TEMPERATURE,
    _parse_validation_verdict,
    _safe_json_loads,
)
from pddl_eval.domains import (
    _build_plan_str,
    generate_ground_truth,
    load_domains,
)
from pddl_eval.prompts import (
    ACTIVE_PROMPT_VARIANTS,
    PROMPT_TEMPLATES,
)
from pddl_eval.resume import load_progress
from pddl_eval.runner import (
    DEFAULT_CONCURRENCY,
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_CTX_THINKING,
    DEFAULT_NUM_PREDICT,
    DEFAULT_NUM_PREDICT_THINK,
    RESPONSE_SNAPSHOT_LEN,
    TASKS,
    THINKING_SNAPSHOT_LEN,
    TaskResult,
    _expand_conditions,
    _resolve_num_predict,
    _shard_filter,
    evaluate_one,
    run_single_task_experiment,
)
from pddl_eval.scoring import (
    FR_EXCEPTION,
    FR_FORMAT_PARSE_FAIL,
    FR_LOOP_EXHAUSTED,
    FR_NO_VERDICT_PARSED,
    FR_OK,
    FR_OLLAMA_PARSE_ERROR,
    FR_PLAN_INVALID,
    FR_RESULT_MISMATCH,
    FR_SIMULATE_EMPTY,
    FR_THINK_OVERFLOW,
    FR_TOOL_ERROR,
    FR_TOOL_NOT_SELECTED,
    FR_TRUNCATED_NO_ANSWER,
    FR_UNKNOWN,
    FR_VERDICT_MISMATCH,
    FR_WRONG_TOOL,
    _apply_truncation_override,
    _classify_step_failure,
    _extract_plan_from_tool_result,
    _get_tool_results,
    _normalize_trajectory,
    _tool_error_seen,
    _used_tool,
    _validate_model_plan,
    check_success,
    extract_plan_lines,
    extract_verdict,
)
from pddl_eval.summary import (
    print_fail_reasons_table,
    print_per_variant_table,
    print_simulate_q1_table,
    print_single_task_table,
    save_results,
    summarize_single_task,
    wilson_ci,
)


# Re-exports above keep `tests/test_*.py` working without edits — they
# `import run_experiment as rx` and reach into module-level names.
# `MAX_TOOL_LOOPS`, `KEEP_ALIVE`, `MCPPlanner`, etc. are re-exported via the
# from-imports above; CLI-only constants (paths + choice tuples) live
# below.


# ---------------------------------------------------------------------------
# Paths + plugin discovery (CLI-side)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DOMAINS_DIR = SCRIPT_DIR / "domains"
RESULTS_DIR = SCRIPT_DIR / "results"

REQUIRED_PLUGINS = ["pddl-solver", "pddl-validator"]


def _git_short_sha_dirty() -> str:
    # The smoke output dir uses `<short-sha>[-dirty]` so the diff harness
    # can pair pre/post-refactor runs by commit. Falls back to "nogit" so
    # the runner still works outside a git checkout (e.g. tarballed tests).
    try:
        sha = subprocess.run(
            ["git", "-C", str(SCRIPT_DIR), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=2,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return "nogit"
    try:
        dirty = subprocess.run(
            ["git", "-C", str(SCRIPT_DIR), "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=2,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        dirty = ""
    return f"{sha}-dirty" if dirty else sha


def resolve_plugin_dirs(marketplace_path: str | Path) -> list[Path]:
    """Discover MCP plugin directories under the marketplace clone."""
    base = Path(marketplace_path).expanduser().resolve()
    plugins_dir = base / "plugins"
    if not plugins_dir.is_dir():
        sys.exit(f"--marketplace-path: plugins/ not found under {base}")
    found = []
    for name in REQUIRED_PLUGINS:
        candidate = plugins_dir / name
        if not candidate.is_dir():
            sys.exit(f"--marketplace-path: required plugin '{name}' missing under {plugins_dir}")
        found.append(candidate)
    return found


# ---------------------------------------------------------------------------
# CLI-side defaults + argparse choice tuples
# ---------------------------------------------------------------------------

DEFAULT_MODELS = ["qwen3:0.6b", "qwen3:4b"]

TOOL_FILTER_CHOICES = ("all",)
PROMPT_STYLE_CHOICES = ("minimal",)
CONDITION_CHOICES = ("tools", "no-tools", "both")


def _apply_partial_subset(domains: dict, k: int) -> dict:
    """Cap each domain to first-K positive + first-K negative fixtures.

    Used by `--partial K` to produce a fast feedback slice across all domains
    without touching scoring or the resume-key shape. The helper rebuilds the
    `domains` dict so a `dict.copy()` of caller state is unaffected; ground
    truth is generated against the returned subset, so partial sweeps don't
    pay GT-generation cost on dropped fixtures.

    Resume-key invariant: the 10-tuple `(model, task, dname, pname,
    plan_label, ...)` is meta-dim agnostic, so a partial run's trials.jsonl
    transfers cleanly into a full run via `--continue-partial`, provided the
    meta-dimensions (`tool_filter`, `prompt_style`, `think`, `conditions`)
    match. Mismatched cells re-run silently.
    """
    if k <= 0:
        return domains
    out: dict = {}
    for dname, dinfo in domains.items():
        kept_pnames = list(dinfo["problems"].keys())[:k]
        if not kept_pnames:
            continue
        kept_set = set(kept_pnames)
        new_problems = {p: dinfo["problems"][p] for p in kept_pnames}
        new_negatives = None
        negs = dinfo.get("negatives")
        if negs is not None:
            new_negatives = {
                "domain": negs.get("domain"),
                "problems": (negs.get("problems") or [])[:k],
                "plans_per_problem": {
                    p: {
                        "valid": (v.get("valid") or [])[:k],
                        "invalid": (v.get("invalid") or [])[:k],
                    }
                    for p, v in (negs.get("plans_per_problem") or {}).items()
                    if p in kept_set
                },
            }
        out[dname] = {**dinfo, "problems": new_problems}
        if new_negatives is not None:
            out[dname]["negatives"] = new_negatives
    return out


# ---------------------------------------------------------------------------
# Main async entry
# ---------------------------------------------------------------------------


async def async_main(args):
    smoke_mode = bool(args.smoke or args.smoke_shuffle)

    # Resolve the think-mode override once. "default" → None → don't pass
    # the kwarg, preserving the model's default (= paper reproduction).
    # In smoke mode the inner loop iterates think={on, off} explicitly;
    # `think_override` here only matters as a fallback for the existing
    # log lines.
    think_override: bool | None
    if args.think == "on":
        think_override = True
    elif args.think == "off":
        think_override = False
    else:
        think_override = None

    host = args.llm_base_url or ""
    if args.models is None:
        args.models = list(DEFAULT_MODELS)

    # Auto-name the output dir for bare invocations (`--output-dir` left at
    # its default `RESULTS_DIR`). Sweeps land under one of three buckets
    # depending on flags: `partial/` for `--partial K`, `smoke/` for
    # `--smoke[-shuffle]`, `full/` otherwise. Cluster + laptop driver
    # scripts pass an explicit `--output-dir` and bypass this block.
    if args.output_dir == str(RESULTS_DIR):
        sha_tag = _git_short_sha_dirty()
        ts_tag = time.strftime("%Y%m%d_%H%M%S")
        if args.partial > 0:
            bucket, name = "partial", f"{sha_tag}_{ts_tag}"
        elif smoke_mode:
            smoke_label = "shuffle" if args.smoke_shuffle else "fixed"
            bucket, name = "smoke", f"{smoke_label}_{sha_tag}_{ts_tag}"
        else:
            bucket, name = "full", f"{sha_tag}_{ts_tag}"
        args.output_dir = str(RESULTS_DIR / bucket / name)

    print("=" * 60)
    print("PDDL Planning Copilot — Experiment Runner")
    print("Reproducing: Benyamin et al., 2025 (arXiv:2509.12987)")
    print("=" * 60)
    print(f"  Marketplace:{args.marketplace_path}")
    print(f"  Models:     {args.models}")
    print(f"  Tasks:      {args.tasks}")
    print(f"  Domains:    {args.domains_dir}")
    active_variants = list(ACTIVE_PROMPT_VARIANTS[:args.num_variants])
    print(f"  Variants:   {active_variants} (selected from {list(ACTIVE_PROMPT_VARIANTS)})")
    print(f"  Temperature:{args.temperature}")
    if smoke_mode:
        print(f"  Conditions: smoke (think=on→both [tools {args.num_ctx} / no-pddl-tools {args.num_ctx_thinking}, sub-pass split], think=off→both [{args.num_ctx} throughout])")
    else:
        # CLI flag value stays "no-tools" for back-compat; banner uses
        # the user-facing "no-pddl-tools" label introduced in PR-4.
        cond_display = (
            "no-pddl-tools" if args.conditions == "no-tools" else args.conditions
        )
        print(f"  Conditions: {cond_display}")
    print(f"  Tool filter:{args.tool_filter}")
    print(f"  Prompt:     {args.prompt_style}")
    if args.num_predict is not None:
        np_str = str(args.num_predict)
    else:
        np_str = (f"per-task defaults (solve={DEFAULT_NUM_PREDICT['solve']}, "
                  f"validate_*={DEFAULT_NUM_PREDICT['validate_plan']}, "
                  f"simulate={DEFAULT_NUM_PREDICT['simulate']})")
    print(f"  num_predict:{np_str}")
    print(f"  num_ctx:    {args.num_ctx} (single-task; tools cells + think=off no-pddl-tools)")
    print(f"  num_ctx_thinking:{args.num_ctx_thinking} (single-task no-pddl-tools when think!=off; sub-pass split)")
    if args.num_ctx == args.num_ctx_thinking:
        print(f"              ^ equal to num_ctx for tools/no-pddl-tools fairness in 'tools save tokens' headline")
    print(f"  think:      {args.think}")
    if args.decoupled_budget:
        _np_think = args.num_predict_think or DEFAULT_NUM_PREDICT_THINK
        _np_ans = args.num_predict_answer if args.num_predict_answer is not None else "per-task"
        print(f"  decoupled-budget: ON (think={_np_think} / answer={_np_ans}; no-tools think=on only)")
    print(f"  Concurrency:{args.concurrency}")
    print(f"  vLLM URL:   {host or '(default: http://localhost:8000)'}")
    if smoke_mode:
        print(f"  Smoke:      "
              f"{'shuffle (random per-cell d/p)' if args.smoke_shuffle else 'fixed (blocksworld/p01)'}"
              f" → {args.output_dir}")
    if args.shard_n > 1:
        print(f"  Shard:      {args.shard_i}/{args.shard_n} "
              "(SHA-256 partitioning of single-task jobs)")

    # Resolve plugins
    plugin_dirs = resolve_plugin_dirs(args.marketplace_path)

    # Load domains
    domains = load_domains(Path(args.domains_dir))
    if not domains:
        sys.exit(f"No domains found in {args.domains_dir}")
    # Optional --domains / --problems filter (applied post-`load_domains`,
    # so paths and ground_truth indices stay consistent). `--smoke` pins
    # both flags to (blocksworld, p01) up front; `--smoke-shuffle` leaves
    # them None so the shuffler sees the full grid.
    if args.domains is not None:
        domains = {d: dinfo for d, dinfo in domains.items() if d in set(args.domains)}
    if args.problems is not None:
        keep = set(args.problems)
        filtered: dict = {}
        for d, dinfo in domains.items():
            kept_problems = {p: ppddl for p, ppddl in dinfo["problems"].items() if p in keep}
            if not kept_problems:
                continue
            negs = dinfo.get("negatives") or {}
            kept_plans_per_problem = {
                p: pp for p, pp in (negs.get("plans_per_problem") or {}).items() if p in keep
            }
            filtered[d] = {
                **dinfo,
                "problems": kept_problems,
                "negatives": {**negs, "plans_per_problem": kept_plans_per_problem},
            }
        domains = filtered
    # `--partial K` is the last filter: caps each remaining domain to first-K
    # positives, first-K negatives, and first-K valid/invalid plans per kept
    # positive. Applied here so ground truth is generated only for the subset.
    if args.partial > 0:
        domains = _apply_partial_subset(domains, args.partial)
    if not domains:
        sys.exit(
            f"No domains/problems remain after filtering "
            f"(--domains={args.domains}, --problems={args.problems}, "
            f"--partial={args.partial})"
        )
    n_problems = sum(len(d["problems"]) for d in domains.values())
    if args.partial > 0:
        print(f"\n  --partial {args.partial}: subsetting to first-K fixtures per domain")
    print(f"\n  Loaded {len(domains)} domains, {n_problems} problems total")
    for dname, dinfo in domains.items():
        print(f"    {dname} ({dinfo['type']}): {len(dinfo['problems'])} problems")

    # Connect MCP
    print("\nConnecting to MCP servers...")
    mcp = MCPPlanner()
    await mcp.connect(plugin_dirs)

    # vllm_client.VLLMClient adapts vLLM's OpenAI /v1/chat/completions to
    # the wire shape pddl_eval.chat consumes (dict-form tool_call args,
    # message.thinking, done_reason, prompt_eval_count, …).
    from pddl_eval.vllm_client import VLLMClient
    client = VLLMClient(base_url=args.llm_base_url)

    # Resume / skip-existing setup. `trials.jsonl` lives next to the
    # canonical end-of-run JSONs in `output_dir`. When it exists, the
    # harness re-loads completed trials, builds a `done_keys` set, and
    # passes both into `run_single_task_experiment` so a TIMEOUT / scancel
    # / scratch-OOM only loses the trial that was in flight at the time
    # — every prior trial is replayed from the JSONL into `single_results`
    # and only the missing trials are re-executed. `--no-resume` deletes
    # the JSONL up front so the run truly starts fresh — without that,
    # the runner's append-mode writes would mix new trials into the old
    # file, and a subsequent default-mode run would resurrect what
    # --no-resume was meant to discard.
    output_dir_path = Path(args.output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir_path / "trials.jsonl"
    if getattr(args, "no_resume", False):
        if progress_path.exists():
            progress_path.unlink()
            print(f"\n  --no-resume: removed existing {progress_path}")
    # `--continue-partial` seeds the new sweep's trials.jsonl with a previous
    # partial sweep's progress file so its completed trials transfer into
    # this run via the existing 10-tuple resume key. Strictly sugar over
    # `cp` + `--resume`, but with named UX + error semantics.
    if args.continue_partial:
        src = Path(args.continue_partial) / "trials.jsonl"
        if not src.exists():
            sys.exit(f"--continue-partial: {src} not found")
        if progress_path.exists() and progress_path.stat().st_size > 0:
            sys.exit(
                f"--continue-partial: {progress_path} already non-empty; "
                f"pass --no-resume to overwrite"
            )
        shutil.copy2(src, progress_path)
        print(f"\n  --continue-partial: seeded {progress_path} from {src}")
    # Load all prior trials as `dict[TrialKey, TaskResult]`. The runner
    # filters this to in-scope (matching this run's meta-dims + post-partial
    # fixture set) before merging into the saved results, so trials seeded
    # from a multi-cell merged source don't pollute the cell's summary.
    restored_by_key = load_progress(progress_path)
    if restored_by_key:
        print(
            f"\n  Resume: loaded {len(restored_by_key)} previously-completed "
            f"trials from {progress_path} (in-scope subset will be filtered "
            f"by the runner)"
        )

    single_results: list[TaskResult] = []
    try:
        # Ground truth
        print("\nGenerating ground truth (solving all problems with planners)...")
        ground_truth = await generate_ground_truth(mcp, domains)

        # Build the (model, task) → (dname, pname) cell assignment for
        # `--smoke-shuffle`. Drawn from the FULL filtered grid using the
        # CLI seed so re-runs with the same seed reproduce the slice.
        cell_assignment: dict[tuple[str, str], tuple[str, str]] | None = None
        if args.smoke_shuffle:
            full_keys = [
                (d, p) for d, dinfo in domains.items() for p in dinfo["problems"]
            ]
            if not full_keys:
                sys.exit("--smoke-shuffle: no (domain, problem) keys in the filtered grid")
            rng = random.Random(args.seed)
            cell_assignment = {
                (m, t): rng.choice(full_keys)
                for m in args.models
                for t in args.tasks
            }

        # Single-task evaluation. When `think != off` AND both conditions
        # are requested, we MUST split the call into (tools then no-tools)
        # sub-passes — `evaluate_one` picks `effective_num_ctx` per
        # condition (8192 for tools, num_ctx_thinking for no-tools), and
        # num_ctx must stay constant per call to keep the sub-pass
        # architecture sound (historical trigger: smoke job 17244356,
        # 2026-04-28, where flipping num_ctx mid-call deadlocked the
        # then-active Ollama backend under concurrency). With sequential
        # sub-passes, the server reloads between them while no requests
        # are in flight. Total wallclock is unchanged (same job count,
        # same concurrency).
        async def _run_single_task_split(
            think_value: bool | None, cond: str, label: str = ""
        ) -> list:
            """Run single-task with sub-pass splitting if num_ctx would flip mid-call."""
            sub_results: list = []
            split_required = (cond == "both") and (think_value is not False)
            sub_conditions = ("tools", "no-tools") if split_required else (cond,)
            for sub_cond in sub_conditions:
                if label:
                    print(f"\n  {label} (conditions={sub_cond})")
                rs = await run_single_task_experiment(
                    client=client, models=args.models, tasks=args.tasks,
                    domains=domains, ground_truth=ground_truth, mcp=mcp,
                    num_variants=args.num_variants, tool_filter=args.tool_filter,
                    prompt_style=args.prompt_style,
                    num_predict_override=args.num_predict,
                    num_ctx=args.num_ctx, num_ctx_thinking=args.num_ctx_thinking,
                    think=think_value,
                    decoupled_budget=args.decoupled_budget,
                    num_predict_think=args.num_predict_think,
                    num_predict_answer=args.num_predict_answer,
                    concurrency=args.concurrency,
                    conditions=sub_cond, temperature=args.temperature,
                    shard_i=args.shard_i, shard_n=args.shard_n,
                    cell_assignment=cell_assignment,
                    progress_path=progress_path,
                    restored_by_key=restored_by_key,
                    include_no_tools_steered=args.include_no_tools_steered,
                )
                sub_results.extend(rs)
            return sub_results

        print("\n--- Single-Task Evaluation ---")
        if smoke_mode:
            # Smoke iterates think={on, off}. The think=on pass is split
            # into (tools, no-tools) sub-passes by _run_single_task_split
            # because num_ctx differs (8192 vs num_ctx_thinking). The
            # think=off pass uses 8192 throughout so no split.
            think_passes: list[tuple[str, bool, str]] = [
                ("on",  True,  "both"),
                ("off", False, "both"),
            ]
            for tm_label, tm_value, cond in think_passes:
                single_results.extend(
                    await _run_single_task_split(
                        tm_value, cond, label=f"Smoke pass: think={tm_label}, conditions={cond}",
                    )
                )
        else:
            single_results = await _run_single_task_split(think_override, args.conditions)
        print_single_task_table(single_results)
        print_per_variant_table(single_results)
        print_fail_reasons_table(single_results)
        print_simulate_q1_table(single_results)

    except KeyboardInterrupt:
        print("\n\nInterrupted — saving partial results...")

    finally:
        # `single_results` already contains the in-scope restored trials
        # (returned by `run_single_task_experiment`, in JSONL append order)
        # followed by trials newly run this process. Restored trials whose
        # 10-tuple key falls outside this run's scope (different model /
        # think mode / prompt style / dropped fixture under --partial K)
        # were filtered out by the runner — preventing per-cell summary
        # pollution when a cell's `trials.jsonl` was seeded from a
        # multi-cell merged source.
        all_single = single_results
        if all_single:
            meta = {
                "host": host or "localhost",
                "conditions": args.conditions,
                "models": args.models,
                "tasks": args.tasks,
                "num_variants": args.num_variants,
                "prompt_variants_active": list(ACTIVE_PROMPT_VARIANTS[:args.num_variants]),
                "include_no_tools_steered": args.include_no_tools_steered,
                "temperature": args.temperature,
                "num_ctx": args.num_ctx,
                "num_ctx_thinking": args.num_ctx_thinking,
                "num_predict": args.num_predict,
                "think": args.think,
            }
            # Decoupled-budget run-meta: only record when actually engaged so a
            # baseline summary isn't mislabelled. The corpus is a distinct A/B
            # arm vs the shared-budget think=on baseline.
            if args.decoupled_budget:
                meta["decoupled_budget"] = True
                meta["num_predict_think"] = args.num_predict_think or DEFAULT_NUM_PREDICT_THINK
                meta["num_predict_answer"] = args.num_predict_answer
            # tool_filter and prompt_style are with-tools-only knobs; record
            # them only when with-tools actually ran, so a no-tools-only
            # summary isn't mislabelled with a stale default.
            if args.conditions in ("tools", "both"):
                meta["tool_filter"] = args.tool_filter
                meta["prompt_style"] = args.prompt_style
            if args.partial > 0:
                meta["partial"] = args.partial
            # `resumed_count` is the count of in-scope restored trials
            # actually folded into this run's saved output, not the raw
            # JSONL line count — the latter over-counts when the JSONL
            # was seeded from a multi-cell merged source. The runner
            # passed the same TaskResult instances through, so identity
            # checks against the loaded values suffice.
            if restored_by_key:
                restored_ids = {id(v) for v in restored_by_key.values()}
                resumed = sum(1 for r in all_single if id(r) in restored_ids)
                if resumed:
                    meta["resumed_count"] = resumed
            save_results(all_single, Path(args.output_dir), meta=meta)
        await mcp.close()
        # VLLMClient wraps openai.AsyncOpenAI's httpx pool; close to release.
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close is not None:
            try:
                await close()
            except Exception:
                pass


def main():
    p = argparse.ArgumentParser(
        description="Reproduce PDDL Planning Copilot experiments (arXiv:2509.12987)",
    )
    p.add_argument("--marketplace-path",
                   default=os.environ.get("PDDL_MARKETPLACE_PATH"),
                   required="PDDL_MARKETPLACE_PATH" not in os.environ,
                   help="Path to cloned pddl-copilot marketplace repo (or set PDDL_MARKETPLACE_PATH)")
    p.add_argument("--models", nargs="+", default=None,
                   help=f"Model tags (matched in cluster-experimenting/lib/defaults.sh:vllm_lookup). "
                        f"Default: paper set {DEFAULT_MODELS}. Cluster sweeps pass an explicit "
                        "list via --models or the MODELS env in run_condition_vllm_rtx.sbatch.")
    p.add_argument("--tasks", nargs="+", default=TASKS, choices=TASKS,
                   help="Tasks to evaluate")
    p.add_argument("--domains-dir", default=str(DOMAINS_DIR),
                   help="Path to domains directory")
    p.add_argument("--output-dir", default=str(RESULTS_DIR),
                   help="Path to save result JSON files")
    p.add_argument("--num-variants", type=int, default=len(ACTIVE_PROMPT_VARIANTS),
                   help=f"How many of the active prompt variants to run, "
                        f"taken from the front of ACTIVE_PROMPT_VARIANTS "
                        f"={list(ACTIVE_PROMPT_VARIANTS)}. Must be in "
                        f"[1, {len(ACTIVE_PROMPT_VARIANTS)}]. Default "
                        f"{len(ACTIVE_PROMPT_VARIANTS)} (run all active "
                        f"variants). To go above this cap, edit "
                        f"ACTIVE_PROMPT_VARIANTS in pddl_eval/prompts.py. "
                        f"Sweep-5 (current) active set is v11/v12/v13 "
                        f"(neutral) + v14/v15/v16 (steered) under marketplace "
                        f"1.4.0; sweep-4 used v5/v6/v7; sweep-3 used v0/v1/v2.")
    p.add_argument("--include-no-tools-steered", action="store_true", default=False,
                   help="Sweep-5 control flag. Why this arm exists: the "
                        "steered prompt tells the model 'use the tool', but "
                        "if no tool is actually available, does just adding "
                        "that sentence still change the answer? We need to "
                        "know — otherwise we can't tell whether the "
                        "with-tools steering benefit comes from the tool "
                        "being callable or just from the prompt wording. "
                        "By default (False) the (no-tools, v14/v15/v16) "
                        "cells are skipped at emit. Set this flag for the "
                        "sweep-5 control submit to emit those cells as the "
                        "4th arm (H4 falsification check). See "
                        "development/sweep_prompt_bank_design.md §0 / §2.6.")
    p.add_argument("--temperature", type=float, default=TEMPERATURE,
                   help="LLM sampling temperature (paper uses 0)")
    p.add_argument("--conditions", choices=list(CONDITION_CHOICES), default="both",
                   help="Which conditions to run. 'both' (default) reproduces the paper. "
                        "'tools'/'no-tools' split the sweep so the no-tools condition can be "
                        "run once per model instead of redundantly for every (filter,style) "
                        "combo — no-tools results are invariant under those knobs.")
    p.add_argument("--tool-filter", choices=list(TOOL_FILTER_CHOICES), default="all",
                   help="'all' exposes every connected MCP tool every turn (paper-aligned).")
    p.add_argument("--prompt-style", choices=list(PROMPT_STYLE_CHOICES), default="minimal",
                   help="System prompt style. 'minimal' is the active choice.")
    p.add_argument("--num-predict", type=int, default=None,
                   help=f"Override max output tokens per chat turn for ALL tasks. "
                        f"Default: per-task caps (solve={DEFAULT_NUM_PREDICT['solve']}, "
                        f"simulate={DEFAULT_NUM_PREDICT['simulate']}, "
                        f"validate_*={DEFAULT_NUM_PREDICT['validate_plan']}). "
                        f"Non-solve caps raised 1024->4096 on 2026-04-29 after "
                        f"observing 33-41%% truncation in the cluster-26042026 sweep, "
                        f"then 4096->6144 same-day after job 17266087 still showed "
                        f"residual Hermes XML truncations on nemotron-3-nano:30b "
                        f"validate_*/think=off cells. Smoke 17274424 (2026-04-30) "
                        f"falsified the budget-cliff hypothesis (same 4 cells failed "
                        f"post-bump); nemotron-3-nano:30b dropped from active roster, "
                        f"6144 retained as harmless headroom (DEFAULT_NUM_PREDICT comment).")
    p.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX,
                   help=f"Context window tokens for single-task tools cells. "
                        f"Default {DEFAULT_NUM_CTX}.")
    p.add_argument("--num-ctx-thinking", type=int, default=DEFAULT_NUM_CTX_THINKING,
                   help=f"Context window tokens used ONLY when think!=off "
                        f"AND condition=no-tools. Default "
                        f"{DEFAULT_NUM_CTX_THINKING}. Tool-condition runs "
                        f"and think=off use --num-ctx (default {DEFAULT_NUM_CTX}). "
                        f"`async_main` runs tools and no-tools as separate "
                        f"sub-passes when both apply so num_ctx stays constant "
                        f"per call (sub-pass isolation; preserved for corpus "
                        f"comparability).")
    p.add_argument("--think", choices=("on", "off", "default"), default="default",
                   help="Override qwen3/DeepSeek thinking mode. 'default' leaves the "
                        "model's default behaviour (reproduces paper). 'off' passes "
                        "think=False, 'on' passes think=True. Ablation only — do NOT "
                        "mix with reproduction runs.")
    p.add_argument("--decoupled-budget", action="store_true", default=False,
                   help="Decoupled-budget think=on (iter-2 T6 / reviewer ask [8]). "
                        "Splits each no-tools think=on trial into a 2-call "
                        "continuation so the reasoning and the answer get SEPARATE "
                        "token budgets — a reasoning spiral can no longer starve the "
                        "answer. Requires --think on; no-op (and rejected at startup) "
                        "otherwise. Tools cells are unaffected. New corpus / new "
                        "RUN_TAG — never pool into a shared-budget baseline.")
    p.add_argument("--num-predict-think", type=int, default=None,
                   help=f"Reasoning-phase budget for --decoupled-budget (Call 1, "
                        f"stop=</think>). Default {DEFAULT_NUM_PREDICT_THINK}.")
    p.add_argument("--num-predict-answer", type=int, default=None,
                   help="Answer-phase budget for --decoupled-budget (Call 2, "
                        "continuation). Default: the per-task --num-predict cap "
                        "(solve=8192, others=6144). DECISION C runs pass 4096.")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                   help=f"Max concurrent chat requests during the single-task "
                        f"sweep. Default {DEFAULT_CONCURRENCY}. Pair with "
                        f"vLLM `--max-num-seqs>=concurrency` on the server.")
    p.add_argument("--llm-base-url",
                   default=os.environ.get("LLM_BASE_URL"),
                   help="vLLM /v1 base URL. Default: http://localhost:8000. "
                        "Cluster runs use a per-job port set by "
                        "run_condition_vllm_rtx.sbatch.")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for --smoke-shuffle cell assignment")
    # Single-task domain/problem filters (applied post-`load_domains`). Used
    # by `--smoke` to constrain to one problem; useful standalone for
    # `--shard` debugging.
    p.add_argument("--domains", nargs="+", default=None,
                   help="Restrict to these domain names (subdir names under "
                        "--domains-dir). Default: all domains found.")
    p.add_argument("--problems", nargs="+", default=None,
                   help="Restrict to these problem stems (e.g. 'p01'). "
                        "Applied within each filtered domain. Default: all.")
    # Smoke harness — fixed slice for the PR-1 byte-equal anchor gate.
    # Auto-overrides several flags inside async_main; see EXPERIMENTS_FLOW
    # / development/FRAMEWORK_EXTENSION_PLAN.md §3.1.
    p.add_argument("--smoke", action="store_true",
                   help="Run the smoke slice: 1 domain × 1 problem × 1 prompt "
                        "variant × 5 tasks × 2 conditions × 2 think modes × "
                        "current model set. Auto-sets --domains blocksworld "
                        "--problems p01 --num-variants 1 --conditions both, "
                        "and iterates --think={on,off} internally. "
                        "Output dir: results/smoke/fixed_<git-sha>_<ts>/.")
    p.add_argument("--smoke-shuffle", action="store_true",
                   help="Like --smoke but picks a random (domain, problem) "
                        "per (model, task) cell using --seed; ~same eval "
                        "count, broader coverage across runs. Mutually "
                        "exclusive with --smoke.")
    # Sharding — deterministic SHA-256 partitioner for cluster parallelism.
    p.add_argument("--shard", default=None, metavar="i/N",
                   help="Run only shard i of N (0-indexed). Hash is "
                        "SHA-256 of (model|task|domain|problem|variant) "
                        "modulo N; with_tools is excluded so paired "
                        "comparisons stay together. Default: no sharding.")
    p.add_argument("--no-resume", action="store_true",
                   help="Delete any existing trials.jsonl in --output-dir "
                        "and start a fresh single-task sweep. Default: if "
                        "trials.jsonl exists, completed trials are loaded "
                        "and skipped on re-run, so a TIMEOUT/scancel only "
                        "loses the trial in flight at the time.")
    # Partial-sweep flags. `--partial K` produces a fast feedback slice
    # (first-K positives / negatives / valid-plans / invalid-plans per
    # domain). `--continue-partial PATH` seeds a full-sweep run with that
    # slice's trials.jsonl so completed trials transfer via the resume key.
    p.add_argument("--partial", type=int, default=0, metavar="K",
                   help="Subset each domain to first-K positive problems, "
                        "first-K negative problems, and first-K valid + "
                        "first-K invalid plans per kept positive problem. "
                        "Default 0 (off, full set). Single-task only by "
                        "convention; pair with `--conditions both` for the "
                        "fast feedback grid. Default --output-dir lands "
                        "under results/partial/.")
    p.add_argument("--continue-partial", type=str, default=None, metavar="PATH",
                   help="Seed --output-dir/trials.jsonl with PATH/trials.jsonl "
                        "before resume kicks in, so a partial sweep's "
                        "completed trials transfer into a follow-up full "
                        "sweep. Required: identical meta-dimensions "
                        "(--tool-filter, --prompt-style, --think, "
                        "--conditions) between the two runs — mismatched "
                        "cells re-run silently. Refuses if dest already "
                        "non-empty unless --no-resume is also set.")
    args = p.parse_args()

    # Route SIGTERM through the same path as Ctrl-C so a `scancel` /
    # SLURM TIMEOUT SIGTERM triggers the KeyboardInterrupt cleanup branch
    # in async_main (which tears down MCP subprocesses via AsyncExitStack).
    # Without this, SIGTERM bypasses `finally` and MCP servers orphan.
    signal.signal(signal.SIGTERM, signal.default_int_handler)

    if args.smoke and args.smoke_shuffle:
        sys.exit("--smoke and --smoke-shuffle are mutually exclusive")

    # --decoupled-budget only acts on the no-tools think=on path. Reject the
    # combinations where it would silently no-op rather than letting an
    # operator believe a decoupled corpus was produced.
    if args.decoupled_budget:
        if args.think != "on":
            sys.exit("--decoupled-budget requires --think on (it splits the "
                     "reasoning vs answer budget of think=on trials)")
        if args.conditions == "tools":
            sys.exit("--decoupled-budget has no effect with --conditions tools "
                     "(it is a no-tools-only intervention); use no-tools or both")

    # Smoke pre-resolves several knobs before the num-variants range check.
    # Setting --num-variants 1 here keeps the existing check trivially valid
    # and saves the user from having to pass it explicitly with --smoke.
    if args.smoke or args.smoke_shuffle:
        args.num_variants = 1
        # `--smoke` pins the slice to (blocksworld, p01); `--smoke-shuffle`
        # leaves --domains/--problems unset so the shuffle picker sees the
        # full grid.
        if args.smoke:
            if args.domains is None:
                args.domains = ["blocksworld"]
            if args.problems is None:
                args.problems = ["p01"]
        # Both modes want the full think × conditions cross-product; the
        # existing think-conditions gate is bypassed for smoke inside
        # async_main and the loop runs both think modes explicitly.
        args.conditions = "both"

    # Parse --shard "i/N" once, surface as args.shard_i / args.shard_n
    # (defaults 0/1 = no filter).
    args.shard_i, args.shard_n = 0, 1
    if args.shard is not None:
        m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", args.shard)
        if not m:
            sys.exit(f"--shard must be 'i/N' (got: {args.shard!r})")
        i, n = int(m.group(1)), int(m.group(2))
        if n < 1 or not 0 <= i < n:
            sys.exit(f"--shard {i}/{n}: need N>=1 and 0<=i<N")
        args.shard_i, args.shard_n = i, n

    if not 1 <= args.num_variants <= len(ACTIVE_PROMPT_VARIANTS):
        sys.exit(
            f"--num-variants={args.num_variants} out of range "
            f"[1, {len(ACTIVE_PROMPT_VARIANTS)}]. ACTIVE_PROMPT_VARIANTS "
            f"={list(ACTIVE_PROMPT_VARIANTS)}; edit that tuple in "
            f"pddl_eval/prompts.py to widen the pool."
        )

    random.seed(args.seed)
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
