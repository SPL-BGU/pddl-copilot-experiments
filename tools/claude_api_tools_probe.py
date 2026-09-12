#!/usr/bin/env python3
"""LIVE with-tools probe for Sonnet 4.6 — cost + token-consumption estimator.

Companion to `tools/claude_api_batch.py` (the no-tools Batches runner). With-tools
is a multi-turn agentic loop: the model calls an MCP tool, *we* execute it
locally (pddl-solver / pddl-validator), feed the result back, and loop until it
answers (cap = `chat.MAX_TOOL_LOOPS`). The Anthropic **Batches API is
single-pass** and cannot execute our local MCP tools mid-conversation, so
with-tools MUST run live — at **list price ($3 / $15 per MTok), no −50% batch
discount.** That is the load-bearing cost difference vs the no-tools run.

This script runs a small stratified sample (the same `--keys-file`s used for the
no-tools cost probing) through the live loop, grades each trial with the same
`check_success(..., with_tools=True)` path the harness uses, and reports
measured tokens + turns + projected full-corpus cost. It is a COST/EFFICIENCY
probe, not the full experiment.

Corpus identity is preserved by reusing the harness builders, exactly like
claude_api_batch:
  * `runner.build_jobs(conditions="tools")` — the with_tools=True grid
  * `runner.build_messages(..., with_tools=True)` — the with-tools prompts
  * `scoring.check_success(..., with_tools=True)` — the with-tools grader
  * `summary.save_results` — the harness output shape

Usage:
  claude_api_tools_probe.py --corpus canonical --marketplace-path ../pddl-copilot \
      --keys-file A.jsonl [--keys-file B.jsonl ...] --out .local/sonnet/tools_probe
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
# The simulate-directive / solve-schema backend adaptations + the per-task
# format-fidelity rule are shared with tools/claude_api_batch.py via format_for so
# the no-tools mode here cannot drift from the batch path.
from tools._claude_api_common import format_for

# MODEL + the live prices are overridden from --model at runtime (see main()).
# (Trivially-stable dups vs claude_api_batch — CORPUS_DOMAINS + the J_* job-tuple
# indices — are kept inline; only the non-trivial request-shaping moved out.)
MODEL = "claude-sonnet-4-6"

# LIVE list price per model — with-tools cannot batch, so NO −50% discount.
# (in_per_tok, out_per_tok). Haiku 4.5 = $1/$5, Sonnet 4.6 = $3/$15.
PRICES = {
    "claude-sonnet-4-6": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude-haiku-4-5": (1.0 / 1_000_000, 5.0 / 1_000_000),
}
LIST_INPUT_PRICE_PER_TOK, LIST_OUTPUT_PRICE_PER_TOK = PRICES[MODEL]
# Batch (no-tools) price = list / 2 (the −50% Batch discount); derived at
# report time from the runtime-resolved LIST_* so it tracks --model correctly.

CORPUS_DOMAINS = {"canonical": "domains", "anon": "domains-anon"}

# Job tuple indices (runner.build_jobs):
#   0 model 1 task 2 dname 3 dpddl 4 pname 5 ppddl 6 pv 7 with_tools
#   8 gt 9 np 10 plan_label
J_TASK, J_DNAME, J_DPDDL, J_PNAME, J_PPDDL, J_PV = 1, 2, 3, 4, 5, 6
J_GT, J_NP, J_PLAN = 8, 9, 10


def _anthropic_tools(mcp: MCPPlanner) -> list[dict]:
    """Convert mcp.tools (OpenAI function shape) -> Anthropic tools shape."""
    out = []
    for t in mcp.tools:
        fn = t["function"]
        out.append({
            "name": fn["name"],
            "description": fn["description"],
            "input_schema": fn["parameters"],
        })
    return out


def _assistant_content(resp) -> list[dict]:
    """Reconstruct the assistant turn's content blocks for replay."""
    blocks = []
    for b in resp.content:
        if b.type == "text":
            blocks.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            blocks.append({"type": "tool_use", "id": b.id,
                           "name": b.name, "input": b.input})
    return blocks


async def _run_one(client, mcp, anthropic_tools, job) -> dict:
    """Run one live with-tools agentic loop; return raw outcome dict."""
    task, dpddl, ppddl = job[J_TASK], job[J_DPDDL], job[J_PPDDL]
    pv, gt, max_tokens = job[J_PV], job[J_GT], job[J_NP]

    msgs = build_messages(task, dpddl, ppddl, pv, with_tools=True, gt=gt)
    system_text = msgs[0]["content"]
    # vLLM's with-tools branch passes NO format constraint, so format_for adds
    # nothing here (no simulate directive): simulate WT is graded from the
    # get_state_transition tool result, not the model's text, and a "return ONLY
    # JSON" directive could suppress the tool call check_success requires.
    user_text, _ = format_for(task, msgs[1]["content"], with_tools=True)

    messages = [{"role": "user", "content": user_text}]
    tool_calls_log: list[dict] = []
    in_tok = out_tok = turns = 0
    stop_reason = ""

    for _ in range(MAX_TOOL_LOOPS):
        resp = await client.messages.create(
            model=MODEL, max_tokens=max_tokens, temperature=0,
            system=system_text, messages=messages, tools=anthropic_tools,
        )
        in_tok += resp.usage.input_tokens
        out_tok += resp.usage.output_tokens
        turns += 1
        stop_reason = resp.stop_reason

        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return {"text": text, "tool_calls": tool_calls_log,
                    "stop_reason": stop_reason, "in_tok": in_tok,
                    "out_tok": out_tok, "turns": turns, "loop_exhausted": False}

        messages.append({"role": "assistant", "content": _assistant_content(resp)})
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            try:
                result_text = await mcp.call_tool(b.name, b.input or {})
            except Exception as exc:
                result_text = f"Tool error: {exc}"
            tool_calls_log.append({"name": b.name, "arguments": b.input or {},
                                   "result": result_text})
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": result_text})
        messages.append({"role": "user", "content": results})

    # Fell out of the loop without a tool-call-free answer.
    return {"text": "", "tool_calls": tool_calls_log, "stop_reason": stop_reason,
            "in_tok": in_tok, "out_tok": out_tok, "turns": turns,
            "loop_exhausted": True}


async def _run_one_notools(client, job) -> dict:
    """Single live no-tools call. Mirrors claude_api_batch._build_request shapes via
    the shared format_for (the vLLM guided_json analog: simulate JSON directive +
    solve structured output). No MCP tool loop (the model has no planning tools)."""
    task, dpddl, ppddl = job[J_TASK], job[J_DPDDL], job[J_PPDDL]
    pv, gt, max_tokens = job[J_PV], job[J_GT], job[J_NP]

    msgs = build_messages(task, dpddl, ppddl, pv, with_tools=False, gt=gt)
    user_text, output_config = format_for(task, msgs[1]["content"], with_tools=False)
    kwargs = dict(model=MODEL, max_tokens=max_tokens, temperature=0,
                  system=msgs[0]["content"],
                  messages=[{"role": "user", "content": user_text}])
    if output_config:
        kwargs["output_config"] = output_config
    resp = await client.messages.create(**kwargs)
    text = "".join(b.text for b in resp.content if b.type == "text")
    return {"text": text, "tool_calls": [], "stop_reason": resp.stop_reason,
            "in_tok": resp.usage.input_tokens, "out_tok": resp.usage.output_tokens,
            "turns": 1, "loop_exhausted": False}


async def _grade(job, outcome, mcp, with_tools: bool = True) -> TaskResult:
    """Grade a probe outcome into a harness TaskResult (with- or no-tools)."""
    task = job[J_TASK]
    stop_reason = outcome["stop_reason"]
    done_reason = "length" if stop_reason == "max_tokens" else (stop_reason or "stop")
    text = outcome["text"]
    loop_exhausted = outcome["loop_exhausted"]

    if stop_reason == "refusal":
        tool_selected, success, failure_reason = None, False, FR_EXCEPTION
        truncated, error = False, "stop_reason=refusal"
    else:
        tool_selected, success, failure_reason = await check_success(
            task, text, outcome["tool_calls"], job[J_GT], mcp,
            job[J_DPDDL], job[J_PPDDL], with_tools=with_tools,
        )
        failure_reason, truncated = _classify_step_failure(
            success, done_reason, loop_exhausted, failure_reason,
            thinking_text="", response_text=text, error="",
        )
        error = ""

    return TaskResult(
        model=MODEL, task=task, domain_name=job[J_DNAME],
        problem_name=job[J_PNAME], prompt_variant=job[J_PV], with_tools=with_tools,
        success=success, tool_selected=tool_selected,
        response=(text or "")[:RESPONSE_SNAPSHOT_LEN], thinking="",
        tool_calls=outcome["tool_calls"],
        tokens={"prompt": outcome["in_tok"], "completion": outcome["out_tok"],
                "turns": outcome["turns"], "total_duration_ns": 0,
                "eval_duration_ns": 0},
        duration_s=0.0, error=error, tool_filter="all", prompt_style="minimal",
        failure_reason=failure_reason, truncated=truncated,
        done_reason=done_reason, plan_label=job[J_PLAN], infra_failure=False,
    )


def _failed_result(job, err: str, with_tools: bool = True) -> TaskResult:
    """Record a per-trial API failure (e.g. Haiku 200K context overflow on a
    giant-trajectory simulate) as a graded failure so one bad trial doesn't
    abort the probe. infra_failure=True keeps it out of capability stats."""
    return TaskResult(
        model=MODEL, task=job[J_TASK], domain_name=job[J_DNAME],
        problem_name=job[J_PNAME], prompt_variant=job[J_PV], with_tools=with_tools,
        success=False, tool_selected=(False if with_tools else None),
        response="", thinking="",
        tool_calls=[], tokens={"prompt": 0, "completion": 0, "turns": 0,
                               "total_duration_ns": 0, "eval_duration_ns": 0},
        duration_s=0.0, error=err[:300], tool_filter="all",
        prompt_style="minimal", failure_reason=FR_EXCEPTION, truncated=False,
        done_reason="error", plan_label=job[J_PLAN], infra_failure=True,
    )


async def main_async(args) -> None:
    import anthropic

    domains_dir = CORPUS_DOMAINS[args.corpus]
    domains = load_domains(Path(domains_dir))
    if not domains:
        sys.exit(f"[probe] no domains under {domains_dir}")

    # Selection keys (same shape as claude_api_batch --keys-file).
    wanted = set()
    for kf in args.keys_file:
        for line in Path(kf).read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            wanted.add((d["task"], d["domain_name"], d["problem_name"],
                        d.get("plan_label", ""), int(d["prompt_variant"])))

    wt = not args.no_tools
    conditions = "tools" if wt else "no-tools"
    # MCP is needed either way: ground-truth generation + solve grading both call
    # it (solve no-tools validates the model's plan through the validator MCP).
    print(f"[probe] corpus={args.corpus} condition={conditions} "
          f"keys={len(wanted)} — connecting MCP...")
    mcp = MCPPlanner()
    await mcp.connect(resolve_plugin_dirs(args.marketplace_path))
    anthropic_tools = _anthropic_tools(mcp) if wt else None
    client = anthropic.AsyncAnthropic()

    try:
        ground_truth = await generate_ground_truth(mcp, domains)
        jobs, _ = build_jobs(
            models=[MODEL], tasks=args.tasks, domains=domains,
            ground_truth=ground_truth, num_variants=len(ACTIVE_PROMPT_VARIANTS),
            conditions=conditions, tool_filter="all", prompt_style="minimal",
            think_tag="off",
        )
        # full N per task (this condition's grid) for cost projection.
        full_by_task: dict[str, int] = {}
        for j in jobs:
            full_by_task[j[J_TASK]] = full_by_task.get(j[J_TASK], 0) + 1

        selected = [j for j in jobs
                    if (j[J_TASK], j[J_DNAME], j[J_PNAME], j[J_PLAN], j[J_PV]) in wanted]
        print(f"[probe] selected {len(selected)} live trials "
              f"(of {len(jobs)} {conditions} grid)\n")

        results: list[TaskResult] = []
        for i, job in enumerate(selected, 1):
            try:
                if wt:
                    outcome = await _run_one(client, mcp, anthropic_tools, job)
                else:
                    outcome = await _run_one_notools(client, job)
                r = await _grade(job, outcome, mcp, with_tools=wt)
            except Exception as exc:
                # A depleted balance is fatal (every later trial would fail the
                # same way) — stop so we keep what we have. Any other API error
                # (e.g. Haiku context overflow) is recorded as a failed trial.
                if "credit balance" in str(exc).lower():
                    print(f"  [{i:3d}/{len(selected)}] STOP — credit balance too low")
                    break
                r = _failed_result(job, str(exc), with_tools=wt)
                results.append(r)
                print(f"  [{i:3d}/{len(selected)}] {job[J_TASK]:16s} "
                      f"{job[J_DNAME]}/{job[J_PNAME]}  ERR {str(exc)[:70]}")
                continue
            results.append(r)
            print(f"  [{i:3d}/{len(selected)}] {r.task:16s} "
                  f"{r.domain_name}/{r.problem_name}{('/'+r.plan_label) if r.plan_label else '':6s} "
                  f"turns={outcome['turns']:2d} in={outcome['in_tok']:6d} "
                  f"out={outcome['out_tok']:5d} "
                  f"{'OK ' if r.success else 'x  '}{r.failure_reason}")
    finally:
        await mcp.close()
        await client.close()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "trials.jsonl").open("w") as fh:
        for r in results:
            key = list(_trial_key(MODEL, r.task, r.domain_name, r.problem_name,
                                  r.plan_label, r.prompt_variant, r.with_tools,
                                  "off", "all", "minimal"))
            fh.write(json.dumps({"key": key, "result": asdict(r)}) + "\n")
    save_results(results, out_dir, meta={
        "model": MODEL, "conditions": conditions, "think": "off", "temperature": 0,
        "backend": "anthropic-live", "corpus": args.corpus,
    })

    # Cost report: with-tools can't batch -> LIST price; no-tools IS batchable,
    # so its real full-run cost is projected at BATCH (-50%) price.
    in_price = LIST_INPUT_PRICE_PER_TOK if wt else LIST_INPUT_PRICE_PER_TOK / 2
    out_price = LIST_OUTPUT_PRICE_PER_TOK if wt else LIST_OUTPUT_PRICE_PER_TOK / 2
    print(f"\n[probe] {len(results)} trials -> {out_dir}  (model={MODEL}, "
          f"{'LIST' if wt else 'BATCH'} price "
          f"${in_price*1e6:.1f}/${out_price*1e6:.1f} per MTok)")
    agg: dict[str, dict] = {}
    for r in results:
        a = agg.setdefault(r.task, {"n": 0, "succ": 0, "turns": 0, "in": 0, "out": 0})
        a["n"] += 1
        a["succ"] += int(r.success)
        a["turns"] += r.tokens["turns"]
        a["in"] += r.tokens["prompt"]
        a["out"] += r.tokens["completion"]
    total_obs = total_proj = 0.0
    for task in sorted(agg):
        a = agg[task]
        cost = a["in"] * in_price + a["out"] * out_price
        full = full_by_task.get(task)
        proj = cost * (full / a["n"]) if full and a["n"] else 0.0
        total_obs += cost
        total_proj += proj
        print(f"  {task:18s} n={a['n']:3d} succ={a['succ']/a['n']*100:5.1f}% "
              f"turns/trial={a['turns']/a['n']:4.1f} "
              f"in={a['in']:7d} out={a['out']:6d} "
              f"cost=${cost:.3f}  proj_full({full})=${proj:.2f}")
    print(f"  {'TOTAL':18s} observed=${total_obs:.3f}  "
          f"projected_full_{conditions}=${total_proj:.2f}")


def main() -> None:
    global MODEL, LIST_INPUT_PRICE_PER_TOK, LIST_OUTPUT_PRICE_PER_TOK
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", choices=list(CORPUS_DOMAINS), default="canonical")
    p.add_argument("--model", choices=list(PRICES), default=MODEL,
                   help="claude-sonnet-4-6 ($3/$15) or claude-haiku-4-5 ($1/$5)")
    p.add_argument("--no-tools", action="store_true",
                   help="run the no-tools condition (single live call, no MCP "
                        "tool loop) instead of the with-tools agentic loop")
    p.add_argument("--marketplace-path", required=True)
    p.add_argument("--keys-file", action="append", required=True,
                   help="stratified selection (repeatable)")
    p.add_argument("--tasks", nargs="+",
                   default=["solve", "simulate", "validate_plan",
                            "validate_problem", "validate_domain"])
    p.add_argument("--out", default=".local/sonnet/tools_probe")
    args = p.parse_args()
    MODEL = args.model
    LIST_INPUT_PRICE_PER_TOK, LIST_OUTPUT_PRICE_PER_TOK = PRICES[MODEL]
    print(f"[probe] model={MODEL} price=${PRICES[MODEL][0]*1e6:.0f}/"
          f"${PRICES[MODEL][1]*1e6:.0f} per MTok")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
