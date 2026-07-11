#!/usr/bin/env python3
"""Frontier with-tools runner on the Anthropic SDK Tool Runner (framework B).

Implements frontier D1=B (development/frontier_rerun_framework_decision.md,
decided 2026-07-11): the agent loop is owned by the official SDK
(`client.beta.messages.tool_runner`, beta surface — the exact `anthropic`
package version is recorded in the run meta), built as the shared module for
the Haiku+Sonnet single-tool rerun and, later, the PlanBench with-tools
backend. `tools/claude_api_tools_probe.py` is the frozen bare-loop comparison
arm (framework A) for the paired harness probe.

Deliberate design choices (audit §2.2 conditions,
development/decision_audit_grading_and_frontier.md):
  * Corpus identity — same harness builders as the A probe: `build_jobs`,
    `build_messages`, `check_success(with_tools=True)`, `save_results`,
    standard trials.jsonl rows (16K response snapshots).
  * Tool execution stays on the harness `MCPPlanner` (same servers, same
    result strings, same "Tool error: {exc}" shape as A) — the SDK runner owns
    ONLY the loop, so the A-vs-B probe isolates the loop-owner effect. The
    SDK's own MCP helpers remain an option for PlanBench later.
  * `max_iterations=MAX_TOOL_LOOPS` counts API round-trips, the same unit as
    the A loop's `for _ in range(MAX_TOOL_LOOPS)`; loop_exhausted is detected
    identically (final message still asking for tools).
  * Prompt caching ON: `cache_control` on the system block caches tools+system
    (tools render first). Per-trial cache read/write tokens are logged and the
    summary reports whether caching is actually active (Haiku's minimum
    cacheable prefix is 4096 tokens — below it the API silently no-ops).

Usage (stage-1 probe, paired with the A arm on the same keys):
  frontier_runner.py --model claude-haiku-4-5 --marketplace-path ../pddl-copilot \
      --keys-file <same-as-A>.jsonl --out .local/frontier/b_probe
Full-grid mode: omit --keys-file (optionally --variant N per frontier D3).
"""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pddl_eval.chat import MAX_TOOL_LOOPS, MCPPlanner
from pddl_eval.domains import generate_ground_truth, load_domains
from pddl_eval.prompts import ACTIVE_PROMPT_VARIANTS
from pddl_eval.runner import (
    RESPONSE_SNAPSHOT_LEN,
    TaskResult,
    _trial_key,
    build_jobs,
    build_messages,
)
from pddl_eval.scoring import FR_EXCEPTION, _classify_step_failure, check_success
from pddl_eval.summary import save_results
from run_experiment import resolve_plugin_dirs
from tools._claude_api_common import format_for

# (in, out) list $/tok; cache write = 1.25x in, cache read = 0.1x in.
PRICES = {
    "claude-sonnet-4-6": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude-haiku-4-5": (1.0 / 1_000_000, 5.0 / 1_000_000),
}
CORPUS_DOMAINS = {"canonical": "domains", "anon": "domains-anon"}

# Job tuple indices (runner.build_jobs) — same as the A probe.
J_TASK, J_DNAME, J_DPDDL, J_PNAME, J_PPDDL, J_PV = 1, 2, 3, 4, 5, 6
J_GT, J_NP, J_PLAN = 8, 9, 10


def runner_tools(mcp: MCPPlanner, log: list[dict]) -> list:
    """Wrap each MCP tool as an SDK runnable tool with its ORIGINAL JSON
    schema. Execution goes through the same MCPPlanner.call_tool as the
    harness/A-probe, including the identical "Tool error: {exc}" string on
    failure, and every call is appended to `log` in the standard
    tool_calls[] row shape."""
    from anthropic.lib.tools import beta_async_tool

    out = []
    for t in mcp.tools:
        fn = t["function"]

        def make(tool_name: str):
            async def _call(**kwargs) -> str:
                try:
                    result = await mcp.call_tool(tool_name, kwargs or {})
                except Exception as exc:
                    result = f"Tool error: {exc}"
                log.append({"name": tool_name, "arguments": kwargs or {},
                            "result": result})
                return result
            return _call

        out.append(beta_async_tool(
            make(fn["name"]),
            name=fn["name"],
            description=fn["description"],
            input_schema=fn["parameters"],
        ))
    return out


async def run_one(client, mcp, model: str, job) -> dict:
    """One with-tools trial through the SDK Tool Runner; raw outcome dict
    (same shape as the A probe's _run_one)."""
    task, dpddl, ppddl = job[J_TASK], job[J_DPDDL], job[J_PPDDL]
    pv, gt, max_tokens = job[J_PV], job[J_GT], job[J_NP]

    msgs = build_messages(task, dpddl, ppddl, pv, with_tools=True, gt=gt)
    user_text, _ = format_for(task, msgs[1]["content"], with_tools=True)

    tool_calls_log: list[dict] = []
    runner = client.beta.messages.tool_runner(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        system=msgs[0]["content"],
        messages=[{"role": "user", "content": user_text}],
        tools=runner_tools(mcp, tool_calls_log),
        max_iterations=MAX_TOOL_LOOPS,
        # The runner places breakpoints across the agentic loop so each turn
        # re-reads the prior turns' prefix at cache-read rates. This is the
        # multi-turn saving that matters here: the big tokens are the
        # domain/problem in the user turn (~59K) resent every loop iteration,
        # NOT the small system block (which is below Haiku's 4096-tok minimum
        # and no-ops if cached alone).
        cache_control={"type": "ephemeral"},
    )

    in_tok = out_tok = cache_write = cache_read = turns = 0
    last = None
    async for message in runner:
        last = message
        u = message.usage
        in_tok += u.input_tokens
        out_tok += u.output_tokens
        cache_write += u.cache_creation_input_tokens or 0
        cache_read += u.cache_read_input_tokens or 0
        turns += 1

    stop_reason = last.stop_reason if last else ""
    # Same exhaustion criterion as the A loop: the loop ended while the model
    # was still asking for a tool (no tool-call-free final answer).
    loop_exhausted = stop_reason == "tool_use"
    text = ("" if last is None or loop_exhausted
            else "".join(b.text for b in last.content if b.type == "text"))
    return {"text": text, "tool_calls": tool_calls_log,
            "stop_reason": stop_reason, "in_tok": in_tok, "out_tok": out_tok,
            "cache_write": cache_write, "cache_read": cache_read,
            "turns": turns, "loop_exhausted": loop_exhausted}


async def grade(job, outcome, mcp, model: str) -> TaskResult:
    """Grade a runner outcome into a harness TaskResult (parity with the A
    probe's _grade; with_tools=True only — the no-tools arm goes via
    tools/claude_api_batch.py)."""
    task = job[J_TASK]
    stop_reason = outcome["stop_reason"]
    done_reason = "length" if stop_reason == "max_tokens" else (stop_reason or "stop")
    text = outcome["text"]

    if stop_reason == "refusal":
        tool_selected, success, failure_reason = None, False, FR_EXCEPTION
        truncated, error = False, "stop_reason=refusal"
    else:
        tool_selected, success, failure_reason = await check_success(
            task, text, outcome["tool_calls"], job[J_GT], mcp,
            job[J_DPDDL], job[J_PPDDL], with_tools=True,
        )
        failure_reason, truncated = _classify_step_failure(
            success, done_reason, outcome["loop_exhausted"], failure_reason,
            thinking_text="", response_text=text, error="",
        )
        error = ""

    return TaskResult(
        model=model, task=task, domain_name=job[J_DNAME],
        problem_name=job[J_PNAME], prompt_variant=job[J_PV], with_tools=True,
        success=success, tool_selected=tool_selected,
        response=(text or "")[:RESPONSE_SNAPSHOT_LEN], thinking="",
        tool_calls=outcome["tool_calls"],
        tokens={"prompt": outcome["in_tok"], "completion": outcome["out_tok"],
                "turns": outcome["turns"],
                "cache_write": outcome["cache_write"],
                "cache_read": outcome["cache_read"],
                "total_duration_ns": 0, "eval_duration_ns": 0},
        duration_s=0.0, error=error, tool_filter="all", prompt_style="minimal",
        failure_reason=failure_reason, truncated=truncated,
        done_reason=done_reason, plan_label=job[J_PLAN], infra_failure=False,
    )


def failed_result(job, err: str, model: str) -> TaskResult:
    return TaskResult(
        model=model, task=job[J_TASK], domain_name=job[J_DNAME],
        problem_name=job[J_PNAME], prompt_variant=job[J_PV], with_tools=True,
        success=False, tool_selected=False, response="", thinking="",
        tool_calls=[], tokens={"prompt": 0, "completion": 0, "turns": 0,
                               "cache_write": 0, "cache_read": 0,
                               "total_duration_ns": 0, "eval_duration_ns": 0},
        duration_s=0.0, error=err[:300], tool_filter="all",
        prompt_style="minimal", failure_reason=FR_EXCEPTION, truncated=False,
        done_reason="error", plan_label=job[J_PLAN], infra_failure=True,
    )


def select_jobs(jobs, args):
    if args.keys_file:
        wanted = set()
        for kf in args.keys_file:
            for line in Path(kf).read_text().splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                wanted.add((d["task"], d["domain_name"], d["problem_name"],
                            d.get("plan_label", ""), int(d["prompt_variant"])))
        selected = [j for j in jobs
                    if (j[J_TASK], j[J_DNAME], j[J_PNAME], j[J_PLAN], j[J_PV])
                    in wanted]
    else:
        selected = list(jobs)
    if args.variant is not None:
        selected = [j for j in selected if j[J_PV] == args.variant]
    # Group by task so the per-task tools+system cache prefix stays hot
    # (5-minute TTL) across consecutive trials.
    selected.sort(key=lambda j: (j[J_TASK], j[J_DNAME], j[J_PNAME],
                                 j[J_PLAN], j[J_PV]))
    if args.limit:
        selected = selected[:args.limit]
    return selected


async def main_async(args) -> None:
    import anthropic

    model = args.model
    in_price, out_price = PRICES[model]
    domains = load_domains(Path(CORPUS_DOMAINS[args.corpus]))
    if not domains:
        sys.exit(f"[frontier-B] no domains under {CORPUS_DOMAINS[args.corpus]}")

    # --dry-run is fully offline: no MCP, no solver, no API. It reuses the
    # cached ground truth (tools/build_gt_cache.py) so job selection/counts
    # match the live path without the heavy generate_ground_truth prelude.
    if args.dry_run:
        gt_path = Path(args.gt_cache)
        if not gt_path.exists():
            sys.exit(f"[frontier-B] --dry-run needs {gt_path} "
                     "(build with tools/build_gt_cache.py)")
        ground_truth = json.loads(gt_path.read_text())
        jobs, _ = build_jobs(
            models=[model], tasks=args.tasks, domains=domains,
            ground_truth=ground_truth,
            num_variants=len(ACTIVE_PROMPT_VARIANTS),
            conditions="tools", tool_filter="all", prompt_style="minimal",
            think_tag="off",
        )
        selected = select_jobs(jobs, args)
        by_task: dict[str, int] = {}
        for j in selected:
            by_task[j[J_TASK]] = by_task.get(j[J_TASK], 0) + 1
        print(f"[frontier-B] model={model} DRY-RUN selected {len(selected)} "
              f"trials (of {len(jobs)} tools grid), no API calls")
        for t, n in sorted(by_task.items()):
            print(f"  {t:18s} n={n}")
        return

    print(f"[frontier-B] model={model} loop=sdk-tool-runner "
          f"anthropic=={anthropic.__version__} corpus={args.corpus}")
    mcp = MCPPlanner()
    await mcp.connect(resolve_plugin_dirs(args.marketplace_path))
    client = anthropic.AsyncAnthropic()

    try:
        if args.use_cached_gt:
            # Skip the heavy generate_ground_truth solver prelude by loading
            # the cache (identical output of build_gt_cache.py). MCP stays
            # connected for tool execution + solve-plan grading. Opt-in: the
            # full run / paired probe should generate fresh so both arms share
            # one GT source (generate is deterministic given fixed plugins).
            gt_path = Path(args.gt_cache)
            if not gt_path.exists():
                sys.exit(f"[frontier-B] --use-cached-gt needs {gt_path}")
            ground_truth = json.loads(gt_path.read_text())
            print(f"[frontier-B] ground truth: cached ({gt_path})")
        else:
            ground_truth = await generate_ground_truth(mcp, domains)
            print("[frontier-B] ground truth: freshly generated")
        jobs, _ = build_jobs(
            models=[model], tasks=args.tasks, domains=domains,
            ground_truth=ground_truth,
            num_variants=len(ACTIVE_PROMPT_VARIANTS),
            conditions="tools", tool_filter="all", prompt_style="minimal",
            think_tag="off",
        )
        selected = select_jobs(jobs, args)
        print(f"[frontier-B] selected {len(selected)} trials "
              f"(of {len(jobs)} tools grid)")

        results: list[TaskResult] = []
        for i, job in enumerate(selected, 1):
            try:
                outcome = await run_one(client, mcp, model, job)
                r = await grade(job, outcome, mcp, model)
            except Exception as exc:
                if "credit balance" in str(exc).lower():
                    print(f"  [{i:3d}/{len(selected)}] STOP — credit balance too low")
                    break
                r = failed_result(job, str(exc), model)
                results.append(r)
                print(f"  [{i:3d}/{len(selected)}] {job[J_TASK]:16s} "
                      f"{job[J_DNAME]}/{job[J_PNAME]}  ERR {str(exc)[:70]}")
                continue
            results.append(r)
            print(f"  [{i:3d}/{len(selected)}] {r.task:16s} "
                  f"{r.domain_name}/{r.problem_name}"
                  f"{('/' + r.plan_label) if r.plan_label else '':6s} "
                  f"turns={outcome['turns']:2d} in={outcome['in_tok']:6d} "
                  f"out={outcome['out_tok']:5d} "
                  f"cw={outcome['cache_write']:5d} cr={outcome['cache_read']:6d} "
                  f"{'OK ' if r.success else 'x  '}{r.failure_reason}")
    finally:
        await mcp.close()
        await client.close()

    if not results:
        print("[frontier-B] no results")
        return
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "trials.jsonl").open("w") as fh:
        for r in results:
            key = list(_trial_key(model, r.task, r.domain_name, r.problem_name,
                                  r.plan_label, r.prompt_variant, r.with_tools,
                                  "off", "all", "minimal"))
            fh.write(json.dumps({"key": key, "result": asdict(r)}) + "\n")
    save_results(results, out_dir, meta={
        "model": model, "conditions": "tools", "think": "off", "temperature": 0,
        "backend": "anthropic-tool-runner",
        "sdk_version": __import__("anthropic").__version__,
        "max_iterations": MAX_TOOL_LOOPS, "corpus": args.corpus,
        "prompt_caching": "system-block (tools+system prefix)",
        "ground_truth": "cached" if args.use_cached_gt else "generated",
    })

    # Cost + caching report. Effective input cost prices cached tokens at
    # their real rates; the "no-cache" figure is the counterfactual.
    agg: dict[str, dict] = {}
    for r in results:
        a = agg.setdefault(r.task, {"n": 0, "succ": 0, "turns": 0,
                                    "in": 0, "out": 0, "cw": 0, "cr": 0})
        a["n"] += 1
        a["succ"] += int(r.success)
        a["turns"] += r.tokens["turns"]
        a["in"] += r.tokens["prompt"]
        a["out"] += r.tokens["completion"]
        a["cw"] += r.tokens.get("cache_write", 0)
        a["cr"] += r.tokens.get("cache_read", 0)
    print(f"\n[frontier-B] {len(results)} trials -> {out_dir}")
    tot = tot_nc = 0.0
    for task in sorted(agg):
        a = agg[task]
        cost = ((a["in"] * in_price) + (a["cw"] * 1.25 * in_price)
                + (a["cr"] * 0.1 * in_price) + (a["out"] * out_price))
        no_cache = (a["in"] + a["cw"] + a["cr"]) * in_price + a["out"] * out_price
        tot += cost
        tot_nc += no_cache
        print(f"  {task:18s} n={a['n']:4d} succ={a['succ'] / a['n'] * 100:5.1f}% "
              f"turns/trial={a['turns'] / a['n']:4.1f} "
              f"cache_read/trial={a['cr'] / a['n']:7.0f} "
              f"cost=${cost:.3f} (no-cache ${no_cache:.3f})")
    active = sum(a["cr"] for a in agg.values()) > 0
    delta = (tot / tot_nc - 1) * 100 if tot_nc else 0  # +% = caching costs MORE
    if not active:
        note = ("INACTIVE — cacheable prefix below the model minimum "
                "(Haiku: 4096 tok) or no reuse; caching no-ops")
    elif delta > 0:
        note = (f"ACTIVE but NET LOSS (+{delta:.0f}% vs no-cache) — write "
                "premium not recouped; too few turns / unique per-trial context")
    else:
        note = f"ACTIVE, saves {-delta:.0f}%"
    print(f"  TOTAL ${tot:.3f} (no-cache ${tot_nc:.3f})  caching {note}")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", choices=list(PRICES), default="claude-haiku-4-5")
    p.add_argument("--corpus", choices=list(CORPUS_DOMAINS), default="canonical")
    p.add_argument("--marketplace-path", default="../pddl-copilot",
                   help="plugins root for live MCP tool execution "
                        "(unused with --dry-run)")
    p.add_argument("--gt-cache", default="results/derived/gt_cache.json",
                   help="cached ground truth (used by --dry-run and "
                        "--use-cached-gt)")
    p.add_argument("--use-cached-gt", action="store_true",
                   help="live run: load GT from --gt-cache instead of the "
                        "generate_ground_truth solver prelude (smoke/dev; the "
                        "full run + paired probe should generate fresh)")
    p.add_argument("--keys-file", action="append", default=None,
                   help="stratified selection (repeatable); omit for full grid")
    p.add_argument("--variant", type=int, default=None,
                   help="restrict to one prompt variant (frontier D3)")
    p.add_argument("--tasks", nargs="+",
                   default=["solve", "simulate", "validate_plan",
                            "validate_problem", "validate_domain"])
    p.add_argument("--limit", type=int, default=None,
                   help="cap the number of trials (smoke)")
    p.add_argument("--dry-run", action="store_true",
                   help="build + select jobs, print counts, no API calls")
    p.add_argument("--out", default=".local/frontier/b_runner")
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
