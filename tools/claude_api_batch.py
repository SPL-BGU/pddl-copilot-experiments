#!/usr/bin/env python3
"""Offline Anthropic Batch-API runner for the Sonnet-4.6 frontier no-tools experiment.

Implements the LOCKED experiment in `paper/REVIEW_AND_REWRITES.md` §7A
(DECIDED 2026-06-18): Claude Sonnet 4.6, **no-tools**, **think=off**, full N,
over the *exact* sweep5v2 (canonical) + sweep6 (anonymized) fixtures, prompts,
and graders, via the Anthropic **Message Batches API** (−50%). It backs two
paper claims: sole-source holds at the frontier (Sonnet floored unaided on
`simulate`) and the no-tools baseline's contamination control extends to a
strong proprietary model (canonical−anon Δ on `validate_plan`/`validate_problem`).

Why a separate offline tool, not a `client.chat()` backend:
  * The Batch API is submit → wait (~1–24 h) → fetch, not request/response.
    The −50% discount is what fits the run inside the ~$145 budget.
  * Per the project's Anthropic guidance, this uses the official `anthropic`
    SDK (`client.messages.batches.*`), NOT an OpenAI-compatible base_url shim.

Corpus identity (load-bearing) is preserved by reusing the harness's own
enumeration + prompt builders:
  * `pddl_eval.runner.build_jobs`     — identical fixture/variant/condition grid
  * `pddl_eval.runner.build_messages` — byte-identical system/user prompts
  * `pddl_eval.scoring.check_success` — identical grader
  * `pddl_eval.summary.save_results`  — identical output JSON shape
The anonymized corpus is just `--corpus anon` (→ `domains-anon/`, the committed
sweep6 fixture set); no re-anonymization.

Backend adaptations (documented; do not affect the canonical−anon Δ, which is
within-Sonnet on identical prompts both corpora):
  * `validate_*` corpus prompts already mandate a `VERDICT: VALID/INVALID`
    footer, so `check_success` grades them via its free-text fallback — no
    structured-output feature needed.
  * `simulate`'s corpus prompt defers the top-level JSON shape to "the format
    constraint" (the open models' vLLM guided_json), which has no Anthropic
    equivalent here; we append one JSON-only directive so Sonnet emits the
    `{"trajectory": [...]}` wrapper `check_success` parses. simulate is the
    floored sole-source task, so this only makes the test fairer.
  * think=off = omit the `thinking` param (Sonnet 4.6 does not think unless
    asked); temperature=0 (allowed on Sonnet 4.6; sampling params are only
    removed at Opus 4.7+); `max_tokens` = the harness per-task `num_predict`.

Subcommands (one "batch dir" == one Anthropic batch):
  build  --corpus {canonical,anon} --marketplace-path P --out DIR
         [--tasks ...] [--max-per-task N]   # N → pilot subset
  submit --batch-dir DIR
  poll   --batch-dir DIR
  grade  --batch-dir DIR [--out-results DIR]

Pilot gate (§7A): build the pilot (`--tasks validate_plan --max-per-task 50
--corpus canonical`), submit, poll, grade — confirm think=off + parsing and
that `grade`'s projected full cost ≤ budget BEFORE building/submitting the
full corpora.
"""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pddl_eval.chat import MCPPlanner
from pddl_eval.domains import generate_ground_truth, load_domains
from pddl_eval.runner import (
    DEFAULT_NUM_PREDICT,
    RESPONSE_SNAPSHOT_LEN,
    TaskResult,
    _trial_key,
    build_jobs,
    build_messages,
)
from pddl_eval.scoring import (
    FR_EXCEPTION,
    _classify_step_failure,
    check_success,
    simulate_format_compliant,
)
from pddl_eval.summary import save_results
from run_experiment import resolve_plugin_dirs
from tools._claude_api_common import format_for

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default model; overridden by --model at runtime (see main()). The frontier
# no-tools arm covers Sonnet 4.6 (done) and Haiku 4.5 (this phase).
MODEL = "claude-sonnet-4-6"

# LIST price per model, $/MTok (input, output). The Batch API halves both, so
# the batch per-token rates are list/2, re-derived once --model resolves.
LIST_PRICES = {
    "claude-sonnet-4-6": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude-haiku-4-5": (1.0 / 1_000_000, 5.0 / 1_000_000),
}
BATCH_INPUT_PRICE_PER_TOK = LIST_PRICES[MODEL][0] / 2
BATCH_OUTPUT_PRICE_PER_TOK = LIST_PRICES[MODEL][1] / 2

# Task set. §7A's decision was the 4 tasks simulate + validate_plan +
# validate_problem + validate_domain (validate_domain added +$5 for the §1
# balanced-accuracy fix). `solve` was added 2026-06-18 (user request) as a
# SECOND sole-source data point — the canonical planning task ("a frontier
# model can't produce a plan unaided"). solve is floored, so it carries NO
# contamination signal, only sole-source. Note: solve no-tools grading
# validates the model's plan via MCP, so `grade` needs --marketplace-path
# whenever solve trials are present.
DEFAULT_TASKS = ["solve", "simulate", "validate_plan", "validate_problem", "validate_domain"]

# The output-shape backend adaptations (simulate JSON directive, solve schema)
# live in tools/_claude_api_common.format_for so this no-tools builder and the live
# with-tools probe cannot drift. format_for mirrors the vLLM per-task format
# handling: the guided_json analog in no-tools, nothing in with-tools.

# Anonymized corpus == the committed sweep6 fixture set under domains-anon/.
CORPUS_DOMAINS = {
    "canonical": "domains",
    "anon": "domains-anon",
}

# Job tuple field indices (see runner.build_jobs):
#   0 model 1 task 2 dname 3 dpddl 4 pname 5 ppddl 6 pv 7 with_tools
#   8 gt_frag 9 np_for_task 10 plan_label
J_TASK, J_DNAME, J_DPDDL, J_PNAME, J_PPDDL, J_PV = 1, 2, 3, 4, 5, 6
J_GT, J_NP, J_PLAN = 8, 9, 10


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable without MCP or the API)
# ---------------------------------------------------------------------------


def _build_request(custom_id: str, job: tuple) -> tuple[dict, dict]:
    """Build one Anthropic batch request + its grading sidecar from a job tuple.

    Returns (request, sidecar). `request` is the `{custom_id, params}` dict
    the Batches API consumes; `sidecar` carries everything `grade` needs to
    map the response back and re-grade with `check_success`.
    """
    task = job[J_TASK]
    dpddl, ppddl = job[J_DPDDL], job[J_PPDDL]
    pv, gt, plan_label = job[J_PV], job[J_GT], job[J_PLAN]
    np_for_task = job[J_NP]

    messages = build_messages(task, dpddl, ppddl, pv, with_tools=False, gt=gt)
    system_text = messages[0]["content"]
    user_text, output_config = format_for(task, messages[1]["content"], with_tools=False)

    params = {
        "model": MODEL,
        "max_tokens": np_for_task,
        "temperature": 0,
        "system": system_text,
        "messages": [{"role": "user", "content": user_text}],
    }
    if output_config:
        params["output_config"] = output_config
    request = {"custom_id": custom_id, "params": params}
    sidecar = {
        "custom_id": custom_id,
        "task": task,
        "domain_name": job[J_DNAME],
        "problem_name": job[J_PNAME],
        "prompt_variant": pv,
        "plan_label": plan_label,
        "num_predict": np_for_task,
        "domain_pddl": dpddl,
        "problem_pddl": ppddl,
        "gt": gt,
    }
    return request, sidecar


async def _grade_one(
    meta: dict,
    text: str | None,
    stop_reason: str | None,
    in_tok: int,
    out_tok: int,
    error: str = "",
    mcp=None,
) -> TaskResult:
    """Grade one batch response into a harness `TaskResult` (no-tools path).

    Mirrors `evaluate_one`'s post-call sequence: `check_success` then
    `_classify_step_failure` (truncation / think-overflow overrides).
    `mcp` may be None for validate_*/simulate (their no-tools graders never
    call MCP). `solve` no-tools DOES validate the model's plan via MCP, so a
    live `mcp` must be passed when grading solve trials.
    """
    task = meta["task"]
    done_reason = "length" if stop_reason == "max_tokens" else (stop_reason or "stop")

    format_compliant: bool | None = None
    if error or text is None or stop_reason == "refusal":
        success = False
        tool_selected = None
        failure_reason = FR_EXCEPTION
        truncated = False
        if not error:
            error = f"stop_reason={stop_reason}" if stop_reason else "empty response"
        response_text = text or ""
    else:
        response_text = text
        tool_selected, success, failure_reason = await check_success(
            task, response_text, [], meta["gt"], mcp,
            meta["domain_pddl"], meta["problem_pddl"], with_tools=False,
        )
        failure_reason, truncated = _classify_step_failure(
            success, done_reason, False, failure_reason,
            thinking_text="", response_text=response_text, error="",
        )
        # Q1 format-compliance (no-tools simulate secondary metric), mirroring
        # evaluate_one so a re-grade carries the same field.
        if task == "simulate":
            format_compliant = simulate_format_compliant(response_text)

    return TaskResult(
        model=MODEL,
        task=task,
        domain_name=meta["domain_name"],
        problem_name=meta["problem_name"],
        prompt_variant=meta["prompt_variant"],
        with_tools=False,
        success=success,
        tool_selected=tool_selected,
        format_compliant=format_compliant,
        response=response_text[:RESPONSE_SNAPSHOT_LEN],
        thinking="",
        tool_calls=[],
        tokens={
            "prompt": int(in_tok or 0),
            "completion": int(out_tok or 0),
            "turns": 1,
            "total_duration_ns": 0,
            "eval_duration_ns": 0,
        },
        duration_s=0.0,
        error=error,
        tool_filter="all",
        prompt_style="minimal",
        failure_reason=failure_reason,
        truncated=truncated,
        done_reason=done_reason,
        plan_label=meta["plan_label"],
        infra_failure=False,
    )


def _trial_key_for(meta: dict) -> list:
    """10-tuple resume key for a graded trial (no-tools, think=off)."""
    return list(_trial_key(
        MODEL, meta["task"], meta["domain_name"], meta["problem_name"],
        meta["plan_label"], meta["prompt_variant"], False,
        "off", "all", "minimal",
    ))


def _project_cost(per_task: dict, counts: dict | None) -> dict:
    """Per-task observed cost + projection to full N (from counts.json)."""
    out = {}
    for task, agg in sorted(per_task.items()):
        cost = (agg["in_tok"] * BATCH_INPUT_PRICE_PER_TOK
                + agg["out_tok"] * BATCH_OUTPUT_PRICE_PER_TOK)
        full = (counts or {}).get(task, {}).get("full")
        selected = agg["n"] or 1
        projected = cost * (full / selected) if full else None
        out[task] = {
            "n": agg["n"],
            "success": agg["success"],
            "in_tok": agg["in_tok"],
            "out_tok": agg["out_tok"],
            "observed_cost_usd": round(cost, 4),
            "full_n": full,
            "projected_full_cost_usd": round(projected, 2) if projected else None,
        }
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


async def cmd_build(args) -> None:
    domains_dir = CORPUS_DOMAINS[args.corpus] if args.corpus else args.domains_dir
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[build] corpus={args.corpus} domains-dir={domains_dir} tasks={args.tasks}")
    domains = load_domains(Path(domains_dir))
    if not domains:
        sys.exit(f"[build] no domains under {domains_dir}")

    print("[build] connecting MCP for ground-truth generation...")
    mcp = MCPPlanner()
    await mcp.connect(resolve_plugin_dirs(args.marketplace_path))
    try:
        ground_truth = await generate_ground_truth(mcp, domains)
    finally:
        await mcp.close()

    # Reuse the harness enumerator. conditions="no-tools" + the full active
    # variant set auto-selects the plain variants (11-13): build_jobs skips
    # the steered (14-16) no-tools cells, exactly like the open-model corpus.
    from pddl_eval.prompts import ACTIVE_PROMPT_VARIANTS
    # --num-variants 0 = all active plain variants (Sonnet's default → v11-13
    # after the no-tools steered-skip); 1 = single plain prompt v11, the
    # frontier single-prompt setting that cuts the grid ~3×.
    num_variants = args.num_variants or len(ACTIVE_PROMPT_VARIANTS)
    jobs, _ = build_jobs(
        models=[MODEL], tasks=args.tasks, domains=domains,
        ground_truth=ground_truth, num_variants=num_variants,
        conditions="no-tools", tool_filter="all", prompt_style="minimal",
        think_tag="off",
    )

    # Optional explicit key set (stratified pilot selection): restrict to
    # specific (task, domain, problem, plan_label, variant) trials. `full`
    # stays the TRUE full-grid count per task so cost projection still
    # extrapolates the pilot to the real full N.
    wanted = None
    if args.keys_file:
        wanted = set()
        for line in Path(args.keys_file).read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            wanted.add((d["task"], d["domain_name"], d["problem_name"],
                        d.get("plan_label", ""), int(d["prompt_variant"])))

    # Group by task (preserving enumeration order) for per-task counts and the
    # deterministic pilot subset (--keys-file selection and/or first-N cap).
    by_task: dict[str, list] = {}
    for j in jobs:
        by_task.setdefault(j[J_TASK], []).append(j)

    counts: dict[str, dict] = {}
    selected: list[tuple] = []
    for task, tjobs in by_task.items():
        full = len(tjobs)
        pool = tjobs
        if wanted is not None:
            pool = [
                j for j in tjobs
                if (j[J_TASK], j[J_DNAME], j[J_PNAME], j[J_PLAN], j[J_PV]) in wanted
            ]
        take = pool[: args.max_per_task] if args.max_per_task else pool
        counts[task] = {"full": full, "selected": len(take)}
        selected.extend(take)

    requests, sidecars = [], []
    for idx, job in enumerate(selected):
        cid = f"t{idx:06d}"
        req, side = _build_request(cid, job)
        requests.append(req)
        sidecars.append(side)

    (out / "batch_requests.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in requests)
    )
    (out / "sidecar.jsonl").write_text(
        "".join(json.dumps(s) + "\n" for s in sidecars)
    )
    (out / "counts.json").write_text(json.dumps({
        "model": MODEL, "corpus": args.corpus, "domains_dir": domains_dir,
        "tasks": args.tasks, "max_per_task": args.max_per_task,
        "num_variants": num_variants,
        "per_task": counts, "total_requests": len(requests),
    }, indent=2))

    print(f"[build] wrote {len(requests)} requests -> {out}")
    for task in args.tasks:
        c = counts.get(task, {"full": 0, "selected": 0})
        print(f"  {task:18s} full={c['full']:5d}  selected={c['selected']:5d}")
    print("[build] cross-check `full` against the open-model sweep5v2/sweep6 "
          "no-tools/off/plain cell counts before submitting.")


# ---------------------------------------------------------------------------
# submit / poll (lazy-import anthropic)
# ---------------------------------------------------------------------------


def cmd_submit(args) -> None:
    import anthropic  # lazy: build/grade don't need the SDK

    bdir = Path(args.batch_dir)
    reqs = [json.loads(l) for l in (bdir / "batch_requests.jsonl").read_text().splitlines() if l]
    if not reqs:
        sys.exit(f"[submit] no requests in {bdir}")
    print(f"[submit] creating batch with {len(reqs)} requests ({MODEL})...")
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=reqs)
    (bdir / "batch_id.txt").write_text(batch.id + "\n")
    print(f"[submit] batch_id={batch.id} status={batch.processing_status}")
    print(f"[submit] -> {bdir / 'batch_id.txt'}; run `poll --batch-dir {bdir}` to fetch.")


def cmd_poll(args) -> None:
    import time

    import anthropic

    bdir = Path(args.batch_dir)
    batch_id = (bdir / "batch_id.txt").read_text().strip()
    client = anthropic.Anthropic()
    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        rc = b.request_counts
        print(f"[poll] {b.processing_status}: processing={rc.processing} "
              f"succeeded={rc.succeeded} errored={rc.errored}")
        time.sleep(args.interval)

    n = 0
    with (bdir / "results.jsonl").open("w") as fh:
        for res in client.messages.batches.results(batch_id):
            rec = {"custom_id": res.custom_id, "type": res.result.type}
            if res.result.type == "succeeded":
                msg = res.result.message
                rec["text"] = "".join(
                    b.text for b in msg.content if b.type == "text"
                )
                rec["stop_reason"] = msg.stop_reason
                rec["input_tokens"] = msg.usage.input_tokens
                rec["output_tokens"] = msg.usage.output_tokens
            else:
                rec["error"] = str(getattr(res.result, "error", res.result.type))
            fh.write(json.dumps(rec) + "\n")
            n += 1
    print(f"[poll] ended; wrote {n} results -> {bdir / 'results.jsonl'}")


# ---------------------------------------------------------------------------
# grade
# ---------------------------------------------------------------------------


async def cmd_grade(args) -> None:
    bdir = Path(args.batch_dir)
    sidecar = {}
    for l in (bdir / "sidecar.jsonl").read_text().splitlines():
        if l:
            s = json.loads(l)
            sidecar[s["custom_id"]] = s
    results_raw = [
        json.loads(l) for l in (bdir / "results.jsonl").read_text().splitlines() if l
    ]
    counts = None
    if (bdir / "counts.json").exists():
        counts = json.loads((bdir / "counts.json").read_text()).get("per_task")

    out_dir = Path(args.out_results) if args.out_results else (bdir / "graded")
    out_dir.mkdir(parents=True, exist_ok=True)

    # `solve` no-tools grading validates the model's plan via MCP; the other
    # four tasks grade offline. Connect MCP only when solve trials are present.
    mcp = None
    if any(s["task"] == "solve" for s in sidecar.values()):
        if not args.marketplace_path:
            sys.exit("[grade] solve trials present — pass --marketplace-path "
                     "(MCP is needed to validate the model's generated plans).")
        print("[grade] solve present — connecting MCP to validate model plans...")
        mcp = MCPPlanner()
        await mcp.connect(resolve_plugin_dirs(args.marketplace_path))

    task_results: list[TaskResult] = []
    per_task: dict[str, dict] = {}
    try:
        with (out_dir / "trials.jsonl").open("w") as trials_fh:
            for rec in results_raw:
                meta = sidecar.get(rec["custom_id"])
                if meta is None:
                    print(f"[grade] WARN: no sidecar for {rec['custom_id']}", file=sys.stderr)
                    continue
                if rec["type"] == "succeeded":
                    r = await _grade_one(
                        meta, rec.get("text"), rec.get("stop_reason"),
                        rec.get("input_tokens", 0), rec.get("output_tokens", 0),
                        mcp=mcp,
                    )
                else:
                    r = await _grade_one(
                        meta, None, None, 0, 0,
                        error=rec.get("error", rec["type"]), mcp=mcp,
                    )
                task_results.append(r)
                trials_fh.write(json.dumps(
                    {"key": _trial_key_for(meta), "result": asdict(r)}
                ) + "\n")
                agg = per_task.setdefault(
                    r.task, {"n": 0, "success": 0, "in_tok": 0, "out_tok": 0}
                )
                agg["n"] += 1
                agg["success"] += int(r.success)
                agg["in_tok"] += r.tokens["prompt"]
                agg["out_tok"] += r.tokens["completion"]
    finally:
        if mcp is not None:
            await mcp.close()

    meta_block = {
        "model": MODEL, "conditions": "no-tools", "think": "off",
        "temperature": 0, "backend": "anthropic-batch",
        "corpus": (json.loads((bdir / "counts.json").read_text()).get("corpus")
                   if (bdir / "counts.json").exists() else None),
        "tasks": sorted(per_task.keys()),
    }
    save_results(task_results, out_dir, meta=meta_block)

    proj = _project_cost(per_task, counts)
    print(f"\n[grade] graded {len(task_results)} trials -> {out_dir}")
    total_obs = total_proj = 0.0
    for task, p in proj.items():
        rate = (p["success"] / p["n"]) if p["n"] else 0.0
        line = (f"  {task:18s} n={p['n']:5d} succ={rate:5.1%} "
                f"in={p['in_tok']:>9d} out={p['out_tok']:>8d} "
                f"cost=${p['observed_cost_usd']:.3f}")
        if p["projected_full_cost_usd"] is not None:
            line += f"  proj_full(${p['full_n']})=${p['projected_full_cost_usd']:.2f}"
            total_proj += p["projected_full_cost_usd"]
        total_obs += p["observed_cost_usd"]
        print(line)
    print(f"  {'TOTAL':18s} observed=${total_obs:.3f}"
          + (f"  projected_full=${total_proj:.2f}" if total_proj else ""))
    if total_proj:
        print("[grade] PILOT GATE: release the full batch only if projected_full ≤ budget.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    global MODEL, BATCH_INPUT_PRICE_PER_TOK, BATCH_OUTPUT_PRICE_PER_TOK
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", choices=list(LIST_PRICES), default=MODEL,
                   help="claude-sonnet-4-6 ($3/$15) or claude-haiku-4-5 ($1/$5); "
                        "batch price = list/2. Goes before the subcommand. Pass it "
                        "to build; grade reads the built model back from counts.json.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="enumerate jobs + write batch request file")
    b.add_argument("--corpus", choices=list(CORPUS_DOMAINS), default=None,
                   help="canonical (domains/) or anon (domains-anon/). "
                        "Overrides --domains-dir.")
    b.add_argument("--domains-dir", default="domains",
                   help="explicit domains dir if --corpus not given")
    b.add_argument("--marketplace-path", required=True,
                   help="path to the pddl-copilot marketplace (for ground truth)")
    b.add_argument("--tasks", nargs="+", default=DEFAULT_TASKS)
    b.add_argument("--max-per-task", type=int, default=0,
                   help="cap each task to first-N jobs (pilot subset); 0 = full")
    b.add_argument("--num-variants", type=int, default=0,
                   help="how many ACTIVE_PROMPT_VARIANTS to enumerate (0 = all "
                        "active plain variants, the Sonnet default; 1 = single "
                        "plain prompt v11, the frontier single-prompt setting)")
    b.add_argument("--keys-file", default=None,
                   help="JSONL of {task,domain_name,problem_name,plan_label,prompt_variant} "
                        "to restrict the build to (stratified pilot selection). Per-task "
                        "`full` counts stay the true full-grid size, so cost projection "
                        "still extrapolates the pilot to the real full N.")
    b.add_argument("--out", required=True, help="batch dir to write")

    s = sub.add_parser("submit", help="create the Anthropic batch")
    s.add_argument("--batch-dir", required=True)

    pl = sub.add_parser("poll", help="poll until ended, fetch results")
    pl.add_argument("--batch-dir", required=True)
    pl.add_argument("--interval", type=int, default=120, help="poll seconds")

    g = sub.add_parser("grade", help="map results -> check_success -> trials + summary")
    g.add_argument("--batch-dir", required=True)
    g.add_argument("--out-results", default=None,
                   help="output dir for trials.jsonl + summary (default: <batch-dir>/graded)")
    g.add_argument("--marketplace-path", default=None,
                   help="pddl-copilot marketplace path; REQUIRED when the batch "
                        "contains `solve` trials (MCP validates the model's plans). "
                        "Unused for the other four tasks.")

    args = p.parse_args()
    MODEL = args.model
    # For grade, the corpus's built model (counts.json) is authoritative so the
    # trial keys + cost projection match what was actually submitted, even if
    # --model is omitted on the grade call.
    if args.cmd == "grade":
        cj = Path(args.batch_dir) / "counts.json"
        if cj.exists():
            built = json.loads(cj.read_text()).get("model")
            if built in LIST_PRICES and built != MODEL:
                print(f"[grade] using built model {built} from counts.json "
                      f"(overrides --model {MODEL})")
                MODEL = built
    BATCH_INPUT_PRICE_PER_TOK = LIST_PRICES[MODEL][0] / 2
    BATCH_OUTPUT_PRICE_PER_TOK = LIST_PRICES[MODEL][1] / 2
    if args.cmd == "build":
        asyncio.run(cmd_build(args))
    elif args.cmd == "submit":
        cmd_submit(args)
    elif args.cmd == "poll":
        cmd_poll(args)
    elif args.cmd == "grade":
        asyncio.run(cmd_grade(args))


if __name__ == "__main__":
    main()
