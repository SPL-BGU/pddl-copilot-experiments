#!/usr/bin/env python3
"""
Reproduce experiments from:
  "Toward PDDL Planning Copilot" (Benyamin et al., 2025)
  https://arxiv.org/abs/2509.12987

Evaluates Ollama LLMs with and without MCP planning tools on 5 PDDL tasks:
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
  python3 run_experiment.py --marketplace-path /path/to/pddl-copilot --tasks solve validate_plan --chains
"""

import argparse
import asyncio
import os
import random
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import ollama

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
    WITH_TOOLS_SYSTEM,
    WITHOUT_TOOLS_SYSTEM,
)
from pddl_eval.runner import (
    DEFAULT_CONCURRENCY,
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_CTX_THINKING,
    DEFAULT_NUM_PREDICT,
    OLLAMA_TOOL_PARSE_SIGNATURE,
    RESPONSE_SNAPSHOT_LEN,
    TASK_TOOLS,
    TASKS,
    THINKING_SNAPSHOT_LEN,
    TaskResult,
    _expand_conditions,
    _resolve_num_predict,
    _shard_filter,
    evaluate_one,
    run_chain_experiment,
    run_single_task_experiment,
)
from pddl_eval.scoring import (
    FR_EXCEPTION,
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
    _apply_truncation_override,
    _classify_step_failure,
    _extract_plan_from_tool_result,
    _get_tool_results,
    _tool_error_seen,
    _used_tool,
    _validate_model_plan,
    check_success,
    extract_plan_lines,
    extract_verdict,
)
from pddl_eval.summary import (
    print_chain_table,
    print_fail_reasons_table,
    print_per_variant_table,
    print_single_task_table,
    save_results,
    summarize_chains,
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

TOOL_FILTER_CHOICES = ("all", "per-task")
# `guided` retired from the active sweep on 2026-04-27 — the 26042026 sweep
# (`checkpoints/cluster-26042026/prompt_variant_stats.md` §5) showed
# minimal-vs-guided shifts results by ≤4pp per model with every CI crossing
# zero. The 3 active prompt variants already cover paraphrase robustness;
# the prompt-style axis was paying for ~0pp of additional signal. The
# `_GUIDED_SUFFIX` constant and `WITH_TOOLS_SYSTEM["guided"]` entry are
# kept as code documentation so the suffix wording is preserved if a
# future sweep wants to re-enable it (re-add "guided" to this tuple).
PROMPT_STYLE_CHOICES = ("minimal",)
CONDITION_CHOICES = ("tools", "no-tools", "both")


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

    host = args.ollama_host or ""
    if args.models is None:
        args.models = list(DEFAULT_MODELS)

    # Smoke output dir is keyed on the source SHA + a wall-clock timestamp,
    # so the diff harness can pair pre-/post-refactor runs by commit. Done
    # here (after model resolution, before the banner) so the printed
    # path matches what's eventually written.
    if smoke_mode:
        sha_tag = _git_short_sha_dirty()
        ts_tag = time.strftime("%Y%m%d_%H%M%S")
        smoke_label = "smoke_shuffle" if args.smoke_shuffle else "smoke"
        args.output_dir = str(
            RESULTS_DIR / f"{smoke_label}_{sha_tag}_{ts_tag}"
        )

    num_parallel_env = os.environ.get("OLLAMA_NUM_PARALLEL", "unset")

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
        print(f"  Conditions: smoke (think=on→both [tools 8192 / no-tools {args.num_ctx_thinking}, sub-pass split], think=off→both [8192 throughout])")
    else:
        print(f"  Conditions: {args.conditions}")
    print(f"  Tool filter:{args.tool_filter}")
    print(f"  Prompt:     {args.prompt_style}")
    print(f"  num_predict:{args.num_predict if args.num_predict is not None else 'per-task defaults'}")
    print(f"  num_ctx:    {args.num_ctx}")
    print(f"  num_ctx_thinking:{args.num_ctx_thinking} (active for think!=off + no-tools cells; sub-pass split)")
    print(f"  think:      {args.think}")
    print(f"  Concurrency:{args.concurrency} (OLLAMA_NUM_PARALLEL={num_parallel_env})")
    if args.concurrency > 1 and num_parallel_env == "unset":
        print("  WARNING: OLLAMA_NUM_PARALLEL is not set — Ollama may queue "
              "concurrent requests server-side, negating the speedup. "
              "Export OLLAMA_NUM_PARALLEL>=concurrency before the run.")
    print(f"  Ollama host:{host or '(library default: http://localhost:11434)'}")
    if smoke_mode:
        print(f"  Smoke:      "
              f"{'shuffle (random per-cell d/p)' if args.smoke_shuffle else 'fixed (blocksworld/p01)'}"
              f" → {args.output_dir}")
    if args.shard_n > 1:
        print(f"  Shard:      {args.shard_i}/{args.shard_n} "
              "(SHA-256 partitioning of single-task jobs; chains run only on shard 0)")

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
    if not domains:
        sys.exit(
            f"No domains/problems remain after filtering "
            f"(--domains={args.domains}, --problems={args.problems})"
        )
    n_problems = sum(len(d["problems"]) for d in domains.values())
    print(f"\n  Loaded {len(domains)} domains, {n_problems} problems total")
    for dname, dinfo in domains.items():
        print(f"    {dname} ({dinfo['type']}): {len(dinfo['problems'])} problems")

    # Connect MCP
    print("\nConnecting to MCP servers...")
    mcp = MCPPlanner()
    await mcp.connect(plugin_dirs)

    # Validate TASK_TOOLS against actual MCP tools (catch typos early)
    available_tools = {t["function"]["name"] for t in mcp.tools}
    for task, allowed in TASK_TOOLS.items():
        missing = set(allowed) - available_tools
        if missing:
            sys.exit(f"TASK_TOOLS['{task}'] references unknown tools: {missing}")

    client_kwargs: dict = {}
    if args.ollama_host:
        client_kwargs["host"] = args.ollama_host
    client = ollama.AsyncClient(**client_kwargs)

    single_results: list[TaskResult] = []
    chain_results: list[dict] = []
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
        # flipping num_ctx mid-call deadlocks Ollama under concurrency
        # (smoke job 17244356, 2026-04-28). With sequential sub-passes,
        # the model reloads between them while no requests are in flight.
        # Total wallclock is unchanged (same job count, same concurrency).
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
                    think=think_value, concurrency=args.concurrency,
                    conditions=sub_cond, temperature=args.temperature,
                    shard_i=args.shard_i, shard_n=args.shard_n,
                    cell_assignment=cell_assignment,
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

        # Multi-task chains. Skipped when sharding (chains run only on
        # shard 0), when --chain-samples=0 (smoke pre-sets this), or when
        # think=off (ISS-018: think=off is a single-task ablation against
        # think=on/default — chain results under it aren't part of any
        # planned comparison).
        if args.chains and args.shard_i == 0 and args.chain_samples > 0 and args.think != "off":
            print("\n--- Multi-Task Chain Evaluation ---")
            for cond_with_tools in _expand_conditions(args.conditions):
                # No-tools is single-task-only: chains require artifact
                # propagation across steps, which the model can't do
                # honestly without tools. See EXPERIMENTS_FLOW.md §4.3.
                if not cond_with_tools:
                    print("\n  Skipping chain phase for no-tools (single-task-only)")
                    continue
                print(f"\n  Condition: {'tools' if cond_with_tools else 'no-tools'}")
                chain_results += await run_chain_experiment(
                    client=client,
                    models=args.models,
                    domains=domains,
                    ground_truth=ground_truth,
                    mcp=mcp,
                    samples=args.chain_samples,
                    tool_filter=args.tool_filter,
                    with_tools=cond_with_tools,
                    prompt_style=args.prompt_style,
                    num_predict_override=args.num_predict,
                    num_ctx=args.num_ctx,
                    num_ctx_thinking=args.num_ctx_thinking,
                    think=think_override,
                    temperature=args.temperature,
                    concurrency=args.concurrency,
                )
            print_chain_table(chain_results)
        elif args.chains and args.think == "off":
            print("\n--- Multi-Task Chain Evaluation ---")
            print("  Skipping chain phase: --think=off is single-task-only "
                  "(ISS-018; mirrors the no-tools rule). Pass --think=on or "
                  "--think=default to run chains.")

    except KeyboardInterrupt:
        print("\n\nInterrupted — saving partial results...")

    finally:
        if single_results:
            meta = {
                "host": host or "localhost",
                "conditions": args.conditions,
                "models": args.models,
                "tasks": args.tasks,
                "num_variants": args.num_variants,
                "prompt_variants_active": list(ACTIVE_PROMPT_VARIANTS[:args.num_variants]),
                "temperature": args.temperature,
                "num_ctx": args.num_ctx,
                "num_ctx_thinking": args.num_ctx_thinking,
                "num_predict": args.num_predict,
                "think": args.think,
            }
            # tool_filter and prompt_style are with-tools-only knobs; record
            # them only when with-tools actually ran, so a no-tools-only
            # summary isn't mislabelled with a stale default.
            if args.conditions in ("tools", "both"):
                meta["tool_filter"] = args.tool_filter
                meta["prompt_style"] = args.prompt_style
            save_results(single_results, chain_results, Path(args.output_dir), meta=meta)
        await mcp.close()
        # ollama.AsyncClient wraps an httpx.AsyncClient; close it to release
        # connections cleanly. Guarded because some builds expose
        # aclose/close differently.
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
                   help=f"Ollama model names to evaluate. Default: paper set {DEFAULT_MODELS}. "
                        "Cluster sweeps pass an explicit list via --models or the MODELS env "
                        "in run_condition_rtx.sbatch.")
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
                        f"ACTIVE_PROMPT_VARIANTS in pddl_eval/prompts.py. Paper "
                        f"sweep used 5; the 26042026 sensitivity analysis "
                        f"dropped v3/v4.")
    p.add_argument("--temperature", type=float, default=TEMPERATURE,
                   help="LLM sampling temperature (paper uses 0)")
    p.add_argument("--conditions", choices=list(CONDITION_CHOICES), default="both",
                   help="Which conditions to run. 'both' (default) reproduces the paper. "
                        "'tools'/'no-tools' split the sweep so the no-tools condition can be "
                        "run once per model instead of redundantly for every (filter,style) "
                        "combo — no-tools results are invariant under those knobs.")
    p.add_argument("--tool-filter", choices=list(TOOL_FILTER_CHOICES), default="all",
                   help="'all' exposes every connected MCP tool every turn (reproduces paper). "
                        "'per-task' restricts tools per task via TASK_TOOLS allowlist, reducing "
                        "tool-selection noise from unrelated tools.")
    p.add_argument("--prompt-style", choices=list(PROMPT_STYLE_CHOICES), default="minimal",
                   help="System prompt style. 'minimal' (paper-aligned) is the only "
                        "active choice as of 2026-04-27 — 'guided' was retired "
                        "(see PROMPT_STYLE_CHOICES comment in run_experiment.py). "
                        "Re-enable by re-adding 'guided' to PROMPT_STYLE_CHOICES.")
    p.add_argument("--num-predict", type=int, default=None,
                   help="Override max output tokens per chat turn for ALL tasks. "
                        "Default: per-task caps (solve=8192, simulate=1536, validate_*=1024). "
                        "Caps the qwen3 thinking-mode spiral that stalls runs for ~4 minutes.")
    p.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX,
                   help=f"Ollama context window tokens. Default {DEFAULT_NUM_CTX}.")
    p.add_argument("--num-ctx-thinking", type=int, default=DEFAULT_NUM_CTX_THINKING,
                   help=f"Ollama context window tokens used ONLY when think!=off "
                        f"AND condition=no-tools. Default "
                        f"{DEFAULT_NUM_CTX_THINKING}. Tool-condition runs "
                        f"and think=off use --num-ctx (default {DEFAULT_NUM_CTX}). "
                        f"`async_main` runs tools and no-tools as separate "
                        f"sub-passes when both apply — keeps num_ctx constant "
                        f"per call (mid-call flips deadlock Ollama under "
                        f"concurrency).")
    p.add_argument("--think", choices=("on", "off", "default"), default="default",
                   help="Override qwen3/DeepSeek thinking mode. 'default' leaves the "
                        "model's default behaviour (reproduces paper). 'off' passes "
                        "think=False, 'on' passes think=True. Ablation only — do NOT "
                        "mix with reproduction runs.")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                   help=f"Max concurrent Ollama chat requests during the single-task "
                        f"sweep. Default {DEFAULT_CONCURRENCY}. Pair with "
                        f"OLLAMA_NUM_PARALLEL>=concurrency on the server.")
    p.add_argument("--ollama-host",
                   default=os.environ.get("OLLAMA_HOST"),
                   help="Ollama base URL. Default: library default "
                        "(http://localhost:11434). Cluster runs use the "
                        "self-deployed Apptainer Ollama on a unique port "
                        "set by run_condition_rtx.sbatch.")
    p.add_argument("--chains", action="store_true",
                   help="Also run multi-task chain evaluation")
    p.add_argument("--chain-samples", type=int, default=20,
                   help="Samples per chain length")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for chain sampling and --smoke-shuffle")
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
                        "--problems p01 --num-variants 1 --chain-samples 0 "
                        "--conditions both, and iterates --think={on,off} "
                        "internally. Output dir: results/smoke_<git-sha>_<ts>/.")
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
                        "comparisons stay together. Chains are emitted "
                        "only when i==0. Default: no sharding.")
    args = p.parse_args()

    # Route SIGTERM through the same path as Ctrl-C so a `kill` from
    # run_background.sh triggers the KeyboardInterrupt cleanup branch in
    # async_main (which tears down MCP subprocesses via AsyncExitStack).
    # Without this, SIGTERM bypasses `finally` and MCP servers orphan.
    signal.signal(signal.SIGTERM, signal.default_int_handler)

    if args.smoke and args.smoke_shuffle:
        sys.exit("--smoke and --smoke-shuffle are mutually exclusive")

    # Smoke pre-resolves several knobs before the num-variants range check.
    # Setting --num-variants 1 here keeps the existing check trivially valid
    # and saves the user from having to pass it explicitly with --smoke.
    if args.smoke or args.smoke_shuffle:
        args.num_variants = 1
        args.chain_samples = 0
        args.chains = False
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
