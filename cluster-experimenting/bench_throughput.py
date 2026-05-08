"""Throughput probe for Ollama vs vLLM on representative PDDL prompts.

Builds a fixed prompt mix from pddl_eval.prompts × pddl_eval.domains so the
length distribution matches a real eval cell, then sends them concurrently
through an OpenAI-compatible /v1/chat/completions endpoint. Both Ollama and
vLLM expose this endpoint; the probe is backend-agnostic at the wire level.

Reports per (backend, concurrency):
    - wallclock total (s)
    - prompt tokens/s aggregate
    - completion tokens/s aggregate
    - TTFT mean / p50 / p95 (ms)

Output: JSON line per (backend, concurrency) cell to --out path; also pretty-
printed to stdout. The sbatch driver runs this twice (once per backend) into
the same --out file so post-mortem can diff matched cells.

Usage:
    python bench_throughput.py \\
        --backend {ollama,vllm} \\
        --base-url http://localhost:11400 \\
        --model <model_id> \\
        --concurrency 1,2,4 \\
        --n-prompts 30 --n-warmup 3 \\
        --max-tokens 512 \\
        --out bench.jsonl

This script is throughput-only: no MCP, no tool calls, no scoring. The
question it answers is "does vLLM saturate the GPU better than Ollama on
prompts of this shape at concurrency 4?". Score parity is a separate
investigation that requires the full chat.py adapter (deferred).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

import openai

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pddl_eval.domains import load_domains, _build_plan_str  # noqa: E402
from pddl_eval.prompts import (  # noqa: E402
    PROMPT_TEMPLATES,
    WITH_TOOLS_SYSTEM,
    WITHOUT_TOOLS_SYSTEM,
)


def build_prompt_mix(domains_dir: Path, n: int) -> list[list[dict]]:
    """Construct n representative (system, user) message pairs.

    Round-robins across (task, domain) so token-length distribution
    approximates a real eval cell. No tools — we want pure model throughput,
    not MCP-augmented generation.
    """
    domains = load_domains(domains_dir)
    if not domains:
        raise RuntimeError(f"No domains loaded from {domains_dir}")

    tasks_with_plan = ("validate_plan", "simulate")
    tasks_no_plan = ("solve", "validate_domain", "validate_problem")

    rotations: list[tuple[str, str, str, str]] = []
    for dname, d in domains.items():
        first_problem = next(iter(d["problems"]))
        problem_pddl = d["problems"][first_problem]
        domain_pddl = d["domain"]

        for task in tasks_no_plan:
            rotations.append((task, dname, domain_pddl, problem_pddl))

        plans = d["negatives"]["plans_per_problem"].get(first_problem, {})
        valid_plans = plans.get("valid", [])
        if valid_plans:
            plan_str = _build_plan_str({"plan": valid_plans[0]})
            for task in tasks_with_plan:
                rotations.append((task, dname, domain_pddl, problem_pddl))

    if not rotations:
        raise RuntimeError("No (task, domain) rotations could be built")

    out: list[list[dict]] = []
    for i in range(n):
        task, dname, domain_pddl, problem_pddl = rotations[i % len(rotations)]
        template = PROMPT_TEMPLATES[task][0]
        plan_str = ""
        if task in tasks_with_plan:
            d = domains[dname]
            first_problem = next(iter(d["problems"]))
            valid_plans = d["negatives"]["plans_per_problem"].get(
                first_problem, {}).get("valid", [])
            if valid_plans:
                plan_str = _build_plan_str({"plan": valid_plans[0]})
        try:
            user = template.format(
                domain=domain_pddl, problem=problem_pddl, plan=plan_str)
        except KeyError:
            user = template.format(domain=domain_pddl, problem=problem_pddl)
        out.append([
            {"role": "system", "content": WITHOUT_TOOLS_SYSTEM},
            {"role": "user", "content": user},
        ])
    return out


async def one_request(
    client: openai.AsyncOpenAI, model: str, messages: list[dict],
    max_tokens: int,
) -> dict:
    """Single streamed request. Returns timing + token counts."""
    t_start = time.perf_counter()
    ttft: float | None = None
    completion_tokens = 0
    prompt_tokens = 0
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
        stream=True,
        stream_options={"include_usage": True},
    )
    async for chunk in stream:
        if ttft is None and chunk.choices and chunk.choices[0].delta.content:
            ttft = time.perf_counter() - t_start
        if chunk.usage is not None:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens
    t_end = time.perf_counter()
    return {
        "wall": t_end - t_start,
        "ttft": ttft if ttft is not None else (t_end - t_start),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


async def run_cell(
    client: openai.AsyncOpenAI, model: str,
    prompts: list[list[dict]], concurrency: int, max_tokens: int,
) -> dict:
    """Run len(prompts) requests at the given concurrency cap."""
    sem = asyncio.Semaphore(concurrency)

    async def gated(msgs):
        async with sem:
            return await one_request(client, model, msgs, max_tokens)

    t0 = time.perf_counter()
    results = await asyncio.gather(*(gated(m) for m in prompts))
    wall = time.perf_counter() - t0

    ttfts_ms = [r["ttft"] * 1000 for r in results]
    prompt_total = sum(r["prompt_tokens"] for r in results)
    completion_total = sum(r["completion_tokens"] for r in results)
    return {
        "concurrency": concurrency,
        "n_requests": len(prompts),
        "wall_s": wall,
        "prompt_tokens_total": prompt_total,
        "completion_tokens_total": completion_total,
        "prompt_tps": prompt_total / wall if wall else 0,
        "completion_tps": completion_total / wall if wall else 0,
        "ttft_mean_ms": statistics.mean(ttfts_ms),
        "ttft_p50_ms": statistics.median(ttfts_ms),
        "ttft_p95_ms": statistics.quantiles(ttfts_ms, n=20)[-1] if len(ttfts_ms) >= 20 else max(ttfts_ms),
    }


async def main_async(args):
    domains_dir = Path(args.domains_dir).resolve()
    prompts = build_prompt_mix(domains_dir, args.n_prompts + args.n_warmup)
    warmup_prompts = prompts[:args.n_warmup]
    measure_prompts = prompts[args.n_warmup:]

    client = openai.AsyncOpenAI(
        base_url=f"{args.base_url.rstrip('/')}/v1",
        api_key="dummy",
        timeout=600.0,
    )

    concurrencies = [int(c) for c in args.concurrency.split(",")]

    print(f"[{args.backend}] warmup: {args.n_warmup} prompts at concurrency=1")
    await run_cell(client, args.model, warmup_prompts, 1, args.max_tokens)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        for c in concurrencies:
            print(f"[{args.backend}] measuring {len(measure_prompts)} prompts at concurrency={c}")
            cell = await run_cell(client, args.model, measure_prompts, c, args.max_tokens)
            cell["backend"] = args.backend
            cell["model"] = args.model
            cell["max_tokens"] = args.max_tokens
            f.write(json.dumps(cell) + "\n")
            f.flush()
            print(f"  wall={cell['wall_s']:.1f}s  "
                  f"prompt_tps={cell['prompt_tps']:.0f}  "
                  f"completion_tps={cell['completion_tps']:.0f}  "
                  f"ttft_p50={cell['ttft_p50_ms']:.0f}ms  "
                  f"ttft_p95={cell['ttft_p95_ms']:.0f}ms")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backend", required=True, choices=["ollama", "vllm"])
    p.add_argument("--base-url", required=True,
                   help="e.g. http://localhost:11400")
    p.add_argument("--model", required=True,
                   help="Ollama tag (e.g. Qwen3.5:0.8B) or HF id (e.g. Qwen/Qwen3.5-0.8B-Instruct)")
    p.add_argument("--concurrency", default="1,2,4",
                   help="Comma-separated list of concurrency caps to sweep")
    p.add_argument("--n-prompts", type=int, default=30)
    p.add_argument("--n-warmup", type=int, default=3)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--domains-dir", default=str(PROJECT_ROOT / "domains"))
    p.add_argument("--out", required=True,
                   help="JSONL output path; appended to (one line per cell)")
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
