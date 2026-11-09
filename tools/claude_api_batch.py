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

Request-setting options (D5a, added 2026-11-09; every default reproduces the
reference request byte for byte, tests/test_claude_api_batch.py proves it):
  --model {claude-sonnet-4-6, claude-haiku-4-5, claude-sonnet-5-5}
  build --thinking {off,on,between_tools}   off = no `thinking` key (reference)
        --temperature-mode {zero,default}   zero = temperature 0 (reference);
                                            default = omit it (the API's 1.0)
        --thinking-budget N                 budget_tokens for thinking=on on
                                            Sonnet 4.6 and Haiku 4.5
        --effort LEVEL                      output_config.effort (Sonnet 5.5
                                            only; the API defaults it to
                                            high, D5a policy sends it
                                            explicitly)
        --max-tokens N                      alias of --num-predict
        --limit N --seed S                  alias of --max-per-task; with
                                            --seed the pool is shuffled first
        --repeats R                         R requests per selected trial
        --prompt-file PATH                  alternative user prompt template
                                            (solve only; no system prompt and
                                            no structured output)
        --exclude-domains D ...             drop these domains from the pool
        --gt-cache PATH                     cached ground truth (no MCP)
  A batch built with any non-default request setting cannot be graded with
  `grade` (it would write think=off trial keys); grading such cells is wired
  when their prereg registers them. `poll` additionally writes
  results_full.jsonl (thinking text, usage incl. thinking tokens, stop reason,
  model id, SDK version, request settings per row) and batch_info.json.
"""

import argparse
import asyncio
import hashlib
import io
import json
import random
import string
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
from tools._run_manifest import (
    MANIFEST_NAME,
    ManifestError,
    build_manifest,
    ensure_manifest,
    file_sha256,
    ground_truth_sha256,
    read_manifest,
    write_manifest,
)

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
    # D5a (2026-11-09), claude-api skill model table: $2 / $10 per MTok.
    "claude-sonnet-5-5": (2.0 / 1_000_000, 10.0 / 1_000_000),
}
BATCH_INPUT_PRICE_PER_TOK = LIST_PRICES[MODEL][0] / 2
BATCH_OUTPUT_PRICE_PER_TOK = LIST_PRICES[MODEL][1] / 2

# ---------------------------------------------------------------------------
# Request settings (D5a). DEFAULT_SETTINGS is the reference apparatus: no
# `thinking` key, temperature 0, the harness system + user prompts.
# ---------------------------------------------------------------------------
THINKING_MODES = ("off", "on", "between_tools")
TEMPERATURE_MODES = ("zero", "default")
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_SETTINGS = {
    "thinking": "off",
    "temperature_mode": "zero",
    "thinking_budget": None,
    "effort": None,
    "prompt_file": None,
}
# Sonnet 4.6 and Haiku 4.5 turn thinking on with a manual budget ({type:
# enabled, budget_tokens}). Sonnet 4.6 also accepts adaptive thinking, but
# budget_tokens is used on both so their thinking cells match
# (development/draft_D5_cost_and_correa.md, assumption 4).
# Sonnet 5.5: `{type: disabled}`, budget_tokens and any non-default temperature
# return a 400; omitting `thinking` runs adaptive thinking. Its two settings
# are adaptive (thinking on) and between_tools (no extended thinking, effort
# `high` or below). Effort is sent explicitly on both.
ADAPTIVE_MODELS = ("claude-sonnet-5-5",)
BETWEEN_TOOLS_MAX_EFFORT = ("low", "medium", "high")

# Header terminator of a --prompt-file template (tools/prompts/*.txt).
PROMPT_HEADER_END = "# ---- END HEADER: template body follows verbatim ----"
PROMPT_BODY_SHA_PREFIX = "# body-sha256: "

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


def is_default_settings(settings: dict | None) -> bool:
    """True when `settings` is the reference apparatus (or None)."""
    return settings is None or {**DEFAULT_SETTINGS, **settings} == DEFAULT_SETTINGS


def validate_settings(model: str, settings: dict, tasks=None) -> None:
    """Refuse a request-setting combination the API would reject or that
    would mislabel the cell. Raises ValueError with the reason.

    Per-trial limits (budget < max_tokens) are checked in `_build_request`.
    """
    s = {**DEFAULT_SETTINGS, **settings}
    unknown = set(s) - set(DEFAULT_SETTINGS)
    if unknown:
        raise ValueError(f"unknown request settings: {sorted(unknown)}")
    if s["thinking"] not in THINKING_MODES:
        raise ValueError(f"thinking must be one of {THINKING_MODES}")
    if s["temperature_mode"] not in TEMPERATURE_MODES:
        raise ValueError(f"temperature_mode must be one of {TEMPERATURE_MODES}")
    if s["effort"] is not None and s["effort"] not in EFFORT_LEVELS:
        raise ValueError(f"effort must be one of {EFFORT_LEVELS}")
    if model not in LIST_PRICES:
        raise ValueError(f"unknown model {model!r}")
    if model in ADAPTIVE_MODELS:
        if s["thinking"] == "off":
            raise ValueError(
                f"{model}: thinking 'off' is not available (`disabled` is a 400 and "
                "omitting `thinking` runs adaptive thinking); use 'between_tools'")
        if s["temperature_mode"] != "default":
            raise ValueError(f"{model} rejects a non-default temperature; "
                             "use --temperature-mode default")
        if s["thinking_budget"] is not None:
            raise ValueError(f"{model} rejects budget_tokens; control depth with --effort")
        if s["effort"] is None:
            raise ValueError(f"{model}: send --effort explicitly (D5a: 'high' on both arms)")
        if s["thinking"] == "between_tools" and s["effort"] not in BETWEEN_TOOLS_MAX_EFFORT:
            raise ValueError("between_tools is accepted only at effort high or below")
    else:
        if s["thinking"] == "between_tools":
            raise ValueError(f"{model}: between_tools is a Sonnet 5.5 setting only")
        if s["effort"] is not None:
            raise ValueError(f"{model}: --effort is not used on this model in D5a")
        if s["thinking"] == "on":
            if s["thinking_budget"] is None or int(s["thinking_budget"]) < 1024:
                raise ValueError(f"{model}: thinking 'on' needs --thinking-budget >= 1024")
            if s["temperature_mode"] != "default":
                raise ValueError("thinking 'on' requires --temperature-mode default "
                                 "(the API rejects temperature 0 with thinking)")
        elif s["thinking_budget"] is not None:
            raise ValueError("--thinking-budget is only used with --thinking on")
    if s["prompt_file"] is not None and tasks is not None and set(tasks) != {"solve"}:
        raise ValueError("--prompt-file is a solve-only option")


def load_prompt_template(path) -> dict:
    """Read a --prompt-file template: header lines up to PROMPT_HEADER_END are
    never sent; the body is everything after that line. When the header
    records `# body-sha256: <hex>`, the body must match it."""
    raw = Path(path).read_bytes().decode("utf-8")
    marker = PROMPT_HEADER_END + "\n"
    if marker not in raw:
        raise ValueError(f"{path}: no '{PROMPT_HEADER_END}' line")
    header, body = raw.split(marker, 1)
    body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    recorded = None
    for line in header.splitlines():
        if line.startswith(PROMPT_BODY_SHA_PREFIX):
            recorded = line[len(PROMPT_BODY_SHA_PREFIX):].strip()
    if recorded is not None and recorded != body_sha:
        raise ValueError(f"{path}: body sha256 {body_sha} != recorded {recorded}")
    return {
        "path": str(path),
        "body": body,
        "body_sha256": body_sha,
        "file_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def fill_prompt_template(body: str, name: str, domain_pddl: str, problem_pddl: str) -> str:
    """Fill a template the way Corrêa et al.'s create_end_to_end_prompt does:
    $name = our domain folder name (it differs from the PDDL `(domain X)` name
    for 9 of the 20 domains; see the template header); $domain = domain file
    minus every line whose stripped text starts with ';'; $instance = the
    problem file unchanged."""
    lines = io.StringIO(domain_pddl).readlines()
    domain = "".join(l for l in lines if not l.strip().startswith(";"))
    return string.Template(body).substitute(
        {"name": name, "domain": domain, "instance": problem_pddl})


def _thinking_param(model: str, s: dict) -> dict | None:
    if s["thinking"] == "off":
        return None
    if s["thinking"] == "between_tools":
        return {"type": "between_tools"}
    if model in ADAPTIVE_MODELS:
        # display defaults to "omitted" (empty thinking text) on Sonnet 5.5;
        # "summarized" returns the readable summary. Billing is the same.
        return {"type": "adaptive", "display": "summarized"}
    return {"type": "enabled", "budget_tokens": int(s["thinking_budget"])}


def _build_request(custom_id: str, job: tuple, settings: dict | None = None,
                   template: dict | None = None) -> tuple[dict, dict]:
    """Build one Anthropic batch request + its grading sidecar from a job tuple.

    Returns (request, sidecar). `request` is the `{custom_id, params}` dict
    the Batches API consumes; `sidecar` carries everything `grade` needs to
    map the response back and re-grade with `check_success`.

    `settings=None` (or DEFAULT_SETTINGS) is the reference request: the same
    keys, values and key order as before the D5a options existed.
    `template` is a `load_prompt_template` result when --prompt-file is set.
    """
    s = {**DEFAULT_SETTINGS, **(settings or {})}
    task = job[J_TASK]
    dpddl, ppddl = job[J_DPDDL], job[J_PPDDL]
    pv, gt, plan_label = job[J_PV], job[J_GT], job[J_PLAN]
    np_for_task = job[J_NP]

    if template is not None:
        if task != "solve":
            raise ValueError("--prompt-file is a solve-only option")
        system_text = None
        user_text = fill_prompt_template(template["body"], job[J_DNAME], dpddl, ppddl)
        output_config = None
    else:
        messages = build_messages(task, dpddl, ppddl, pv, with_tools=False, gt=gt)
        system_text = messages[0]["content"]
        user_text, output_config = format_for(task, messages[1]["content"], with_tools=False)

    thinking = _thinking_param(MODEL, s)
    if thinking and thinking.get("type") == "enabled" and \
            thinking["budget_tokens"] >= np_for_task:
        raise ValueError(f"budget_tokens {thinking['budget_tokens']} must be below "
                         f"max_tokens {np_for_task}")

    params = {
        "model": MODEL,
        "max_tokens": np_for_task,
    }
    if s["temperature_mode"] == "zero":
        params["temperature"] = 0
    if system_text is not None:
        params["system"] = system_text
    params["messages"] = [{"role": "user", "content": user_text}]
    if thinking is not None:
        params["thinking"] = thinking
    if s["effort"] is not None:
        output_config = dict(output_config or {}, effort=s["effort"])
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
    if not is_default_settings(s):
        sidecar["request_settings"] = dict(s)
        if template is not None:
            sidecar["prompt_file_body_sha256"] = template["body_sha256"]
    return request, sidecar


def request_settings_record(params: dict) -> dict:
    """Every request setting of one request except the prompt text itself."""
    rec = {k: v for k, v in params.items() if k not in ("system", "messages")}
    rec["has_system_prompt"] = "system" in params
    return rec


def worst_case_list_cost(requests: list[dict], model: str,
                         chars_per_token: float = 2.0) -> dict:
    """Upper bound on the list-price cost of a batch: every request bills its
    full max_tokens as output, and input is bounded by prompt characters /
    `chars_per_token` (2.0 is below every measured ratio: 2.95 on Sonnet 4.6,
    about 2.3 after Sonnet 5.5's ~1.3x tokenizer)."""
    in_price, out_price = LIST_PRICES[model]
    in_tok = out_tok = 0
    for r in requests:
        p = r["params"]
        chars = len(p.get("system", "")) + sum(
            len(m["content"]) for m in p["messages"])
        in_tok += int(chars / chars_per_token) + 1
        out_tok += int(p["max_tokens"])
    return {
        "n": len(requests),
        "input_tokens_bound": in_tok,
        "output_tokens_bound": out_tok,
        "list_usd": round(in_tok * in_price + out_tok * out_price, 4),
    }


def _result_row(res, req_params: dict | None, side: dict | None,
                sdk_version: str | None) -> dict:
    """One results_full.jsonl row: the full answer, the thinking text, the
    usage block as the API returned it (incl. output_tokens_details
    .thinking_tokens when present), stop reason, model id, SDK version and
    the request settings. No grading."""
    row = {"custom_id": res.custom_id, "type": res.result.type,
           "sdk_version": sdk_version}
    if side is not None:
        for k in ("task", "domain_name", "problem_name", "prompt_variant",
                  "plan_label", "repeat"):
            if k in side:
                row[k] = side[k]
    if req_params is not None:
        row["request_settings"] = request_settings_record(req_params)
    if res.result.type != "succeeded":
        row["error"] = str(getattr(res.result, "error", res.result.type))
        return row
    msg = res.result.message
    blocks = list(msg.content)
    row["model_id"] = getattr(msg, "model", None)
    row["stop_reason"] = msg.stop_reason
    sd = getattr(msg, "stop_details", None)
    row["stop_details"] = sd.model_dump(mode="json") if hasattr(sd, "model_dump") else sd
    row["content_types"] = [b.type for b in blocks]
    row["answer"] = "".join(b.text for b in blocks if b.type == "text")
    row["thinking_text"] = "\n\n".join(
        (getattr(b, "thinking", "") or "") for b in blocks if b.type == "thinking")
    row["n_thinking_blocks"] = sum(1 for b in blocks if b.type == "thinking")
    row["n_redacted_thinking_blocks"] = sum(
        1 for b in blocks if b.type == "redacted_thinking")
    usage = msg.usage
    row["usage"] = usage.model_dump(mode="json") if hasattr(usage, "model_dump") else dict(vars(usage))
    row["input_tokens"] = usage.input_tokens
    row["output_tokens"] = usage.output_tokens
    details = getattr(usage, "output_tokens_details", None)
    thinking_tokens = getattr(details, "thinking_tokens", None) if details is not None else None
    row["thinking_tokens"] = thinking_tokens
    # The API documents output_tokens - thinking_tokens as the non-reasoning
    # output; both numbers come from usage.
    row["visible_output_tokens"] = (usage.output_tokens - thinking_tokens
                                    if thinking_tokens is not None else None)
    return row


async def _grade_one(
    meta: dict,
    text: str | None,
    stop_reason: str | None,
    in_tok: int,
    out_tok: int,
    error: str = "",
    mcp=None,
    snapshot_len: int = RESPONSE_SNAPSHOT_LEN,
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
        response=response_text[:snapshot_len],
        thinking="",
        tool_calls=[],
        tokens={
            "prompt": int(in_tok or 0),
            "completion": int(out_tok or 0),
            # Single-turn path: the final turn IS the only turn. Recorded
            # separately anyway so every frontier corpus carries the field
            # the budget-probe truncation tripwire reads.
            "completion_final": int(out_tok or 0),
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


def _batch_manifest(*, corpus: str | None, domains_dir: str, tasks: list[str],
                    prompt_variants: list[int], num_predict: int | None,
                    snapshot_len: int | None, gt_sha: str,
                    keys_file: str | None, max_per_task: int,
                    extra: dict | None = None, gt_cache_sha: str | None = None,
                    gt_cache_path: str | None = None) -> dict:
    """Manifest for the no-tools Batches path (single turn, no streaming; the
    ground truth is generated at build time unless --gt-cache is given).

    `extra` is None for the reference apparatus, so its manifest keeps exactly
    the fields it always had. A non-default build passes the D5a request
    settings there and its temperature / think fields name them."""
    temperature, think, sdk_version = 0, "off", None
    if extra is not None:
        s = extra["request_settings"]
        temperature = 0 if s["temperature_mode"] == "zero" else "default (omitted)"
        think = s["thinking"]
        sdk_version = extra.get("sdk_version")
    return build_manifest(
        backend="anthropic-batch", model=MODEL, with_tools=False,
        tasks=list(tasks), corpus=corpus or "explicit", domains_dir=domains_dir,
        prompt_variants=prompt_variants, num_predict=num_predict,
        snapshot_len=snapshot_len, max_iterations=1, stream=False,
        temperature=temperature, think=think,
        ground_truth_source="cached" if gt_cache_sha else "generated",
        ground_truth_sha256=gt_sha, gt_cache_sha256=gt_cache_sha,
        gt_cache_path=gt_cache_path,
        sdk_version=sdk_version,
        keys_files=[keys_file] if keys_file else None,
        limit=max_per_task or None,
        extra=extra,
    )


def seeded_order(jobs: list, seed: int) -> list:
    """Deterministic shuffle of `jobs`: sort by the trial key first so the
    result depends only on the set and the seed, not on enumeration order."""
    pool = sorted(jobs, key=lambda j: (j[J_TASK], j[J_DNAME], j[J_PNAME],
                                       j[J_PLAN], j[J_PV]))
    random.Random(seed).shuffle(pool)
    return pool


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

    settings = {
        "thinking": args.thinking,
        "temperature_mode": args.temperature_mode,
        "thinking_budget": args.thinking_budget,
        "effort": args.effort,
        "prompt_file": args.prompt_file,
    }
    try:
        validate_settings(MODEL, settings, tasks=args.tasks)
    except ValueError as exc:
        sys.exit(f"[build] {exc}")
    template = load_prompt_template(args.prompt_file) if args.prompt_file else None
    nondefault = (not is_default_settings(settings) or args.repeats != 1
                  or args.seed is not None or bool(args.exclude_domains))

    print(f"[build] corpus={args.corpus} domains-dir={domains_dir} tasks={args.tasks}")
    domains = load_domains(Path(domains_dir))
    if not domains:
        sys.exit(f"[build] no domains under {domains_dir}")

    gt_cache_sha = None
    if args.gt_cache:
        gt_path = Path(args.gt_cache)
        ground_truth = json.loads(gt_path.read_text())
        gt_cache_sha = file_sha256(gt_path)
        print(f"[build] ground truth: cached ({gt_path}, sha256 {gt_cache_sha[:12]}...)")
    else:
        if not args.marketplace_path:
            sys.exit("[build] pass --marketplace-path (ground-truth generation) "
                     "or --gt-cache")
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
        think_tag="off", num_predict_override=args.num_predict,
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
        if args.exclude_domains:
            pool = [j for j in pool if j[J_DNAME] not in set(args.exclude_domains)]
        if args.seed is not None:
            pool = seeded_order(pool, args.seed)
        take = pool[: args.max_per_task] if args.max_per_task else pool
        counts[task] = {"full": full, "selected": len(take)}
        selected.extend(take)

    requests, sidecars = [], []
    idx = 0
    for job in selected:
        for rep in range(args.repeats):
            cid = f"t{idx:06d}"
            idx += 1
            try:
                req, side = _build_request(cid, job, settings, template)
            except ValueError as exc:
                sys.exit(f"[build] {exc}")
            if args.repeats != 1:
                side["repeat"] = rep
            requests.append(req)
            sidecars.append(side)

    (out / "batch_requests.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in requests)
    )
    (out / "sidecar.jsonl").write_text(
        "".join(json.dumps(s) + "\n" for s in sidecars)
    )
    gt_sha = ground_truth_sha256(ground_truth)
    counts_doc = {
        "model": MODEL, "corpus": args.corpus, "domains_dir": domains_dir,
        "tasks": args.tasks, "max_per_task": args.max_per_task,
        "num_variants": num_variants,
        # Budget-probe pin (development/frontier_budget_probe_prereg.md §2.3);
        # None = the per-task DEFAULT_NUM_PREDICT reference behavior.
        "num_predict": args.num_predict,
        "ground_truth_sha256": gt_sha,
        "per_task": counts, "total_requests": len(requests),
    }
    extra = None
    if nondefault:
        import anthropic  # recorded only; build sends nothing
        extra = {
            "request_settings": {**DEFAULT_SETTINGS, **settings},
            "repeats": args.repeats,
            "seed": args.seed,
            "exclude_domains": sorted(args.exclude_domains or []),
            "prompt_file_body_sha256": template["body_sha256"] if template else None,
            "prompt_file_sha256": template["file_sha256"] if template else None,
            "sdk_version": anthropic.__version__,
            "anthropic_version_header": "2023-06-01",
        }
        counts_doc.update(extra)
        (out / "request_settings.json").write_text(json.dumps(
            dict(extra, model=MODEL,
                 first_request_settings=request_settings_record(requests[0]["params"])
                 if requests else None,
                 worst_case=worst_case_list_cost(requests, MODEL)),
            indent=2) + "\n")
    (out / "counts.json").write_text(json.dumps(counts_doc, indent=2))
    # Run manifest (prereg §2.3 item 5), persisted in the batch dir BEFORE
    # `submit` — the first API call — so the settings the requests were built
    # under are on disk before any money moves. `grade` carries it into the
    # results dir with the snapshot length filled in.
    write_manifest(out, _batch_manifest(
        corpus=args.corpus, domains_dir=domains_dir, tasks=args.tasks,
        prompt_variants=sorted({j[J_PV] for j in selected}),
        num_predict=args.num_predict, snapshot_len=None, gt_sha=gt_sha,
        keys_file=args.keys_file, max_per_task=args.max_per_task,
        extra=extra, gt_cache_sha=gt_cache_sha,
        gt_cache_path=str(args.gt_cache) if args.gt_cache else None,
    ))
    if nondefault:
        wc = worst_case_list_cost(requests, MODEL)
        print(f"[build] worst case (every request at max_tokens, list price): "
              f"${wc['list_usd']:.2f} over {wc['n']} requests")

    print(f"[build] wrote {len(requests)} requests + {MANIFEST_NAME} -> {out}")
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
    manifest = read_manifest(bdir)
    if manifest is None:
        sys.exit(f"[submit] {bdir} has no {MANIFEST_NAME} — rebuild with the "
                 "current `build` so the settings are on disk before submission")
    if manifest["model"] != MODEL:
        sys.exit(f"[submit] batch was built for {manifest['model']}, not {MODEL}")
    if args.max_list_cost is not None:
        # Spend guard: the worst case (every request at max_tokens, list
        # price) plus what earlier batches already cost at list price must
        # stay under the cap, or nothing is sent.
        wc = worst_case_list_cost(reqs, MODEL)
        spent = args.already_spent_list_usd or 0.0
        total = wc["list_usd"] + spent
        print(f"[submit] worst case ${wc['list_usd']:.2f} + already spent "
              f"${spent:.2f} = ${total:.2f} (cap ${args.max_list_cost:.2f}, list price)")
        if total >= args.max_list_cost:
            sys.exit("[submit] refused: the worst case would reach the spend cap")
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

    # results.jsonl keeps its reference shape (the answer text only, what
    # `grade` reads). results_full.jsonl is additive: thinking text, the
    # usage block, stop details, model id, SDK version, request settings.
    params_by_id = {}
    for l in (bdir / "batch_requests.jsonl").read_text().splitlines():
        if l:
            r = json.loads(l)
            params_by_id[r["custom_id"]] = r["params"]
    side_by_id = {}
    if (bdir / "sidecar.jsonl").exists():
        for l in (bdir / "sidecar.jsonl").read_text().splitlines():
            if l:
                sd = json.loads(l)
                side_by_id[sd["custom_id"]] = sd
    n = 0
    with (bdir / "results.jsonl").open("w") as fh, \
            (bdir / "results_full.jsonl").open("w") as full_fh:
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
            full_fh.write(json.dumps(_result_row(
                res, params_by_id.get(res.custom_id), side_by_id.get(res.custom_id),
                anthropic.__version__)) + "\n")
            n += 1
    rc = b.request_counts
    (bdir / "batch_info.json").write_text(json.dumps({
        "batch_id": b.id,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "ended_at": b.ended_at.isoformat() if b.ended_at else None,
        "wall_seconds": ((b.ended_at - b.created_at).total_seconds()
                         if b.created_at and b.ended_at else None),
        "request_counts": {"succeeded": rc.succeeded, "errored": rc.errored,
                           "canceled": rc.canceled, "expired": rc.expired,
                           "processing": rc.processing},
        "sdk_version": anthropic.__version__,
    }, indent=2) + "\n")
    print(f"[poll] ended; wrote {n} results -> {bdir / 'results.jsonl'} "
          "(+ results_full.jsonl, batch_info.json)")


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
    # Carry the build-time manifest into the results dir with the snapshot
    # length filled in; refuse to grade into a dir written under different
    # settings (a re-grade into the same dir under the same settings is fine).
    built = read_manifest(bdir)
    if built is None:
        sys.exit(f"[grade] {bdir} has no {MANIFEST_NAME}; rebuild + resubmit "
                 "so the results carry verifiable settings")
    if "request_settings" in built:
        # D5a: the trial keys and meta below are the think=off / T=0 reference
        # apparatus. A cell built with other request settings is graded only
        # once its prereg registers it and this path is extended for it.
        sys.exit(f"[grade] {bdir} was built with non-default request settings "
                 f"{built['request_settings']}; grading such cells is not wired "
                 "(the D5a pilot is outcome-blind)")
    requested = dict(built, snapshot_len=args.snapshot_len)
    try:
        manifest = ensure_manifest(out_dir, requested)
    except ManifestError as exc:
        sys.exit(f"[grade] {exc}")

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
                        mcp=mcp, snapshot_len=args.snapshot_len,
                    )
                else:
                    r = await _grade_one(
                        meta, None, None, 0, 0,
                        error=rec.get("error", rec["type"]), mcp=mcp,
                        snapshot_len=args.snapshot_len,
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
        # Budget-probe pins (development/frontier_budget_probe_prereg.md §2.4);
        # None / the default = the reference apparatus.
        "num_predict": (json.loads((bdir / "counts.json").read_text()).get("num_predict")
                        if (bdir / "counts.json").exists() else None),
        "snapshot_len": args.snapshot_len,
        "ground_truth_sha256": manifest["ground_truth_sha256"],
        "manifest": MANIFEST_NAME,
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
                   help="claude-sonnet-4-6 ($3/$15), claude-haiku-4-5 ($1/$5) or "
                        "claude-sonnet-5-5 ($2/$10); "
                        "batch price = list/2. Goes before the subcommand. Pass it "
                        "to build; grade reads the built model back from counts.json.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="enumerate jobs + write batch request file")
    b.add_argument("--corpus", choices=list(CORPUS_DOMAINS), default=None,
                   help="canonical (domains/) or anon (domains-anon/). "
                        "Overrides --domains-dir.")
    b.add_argument("--domains-dir", default="domains",
                   help="explicit domains dir if --corpus not given")
    b.add_argument("--marketplace-path", default=None,
                   help="path to the pddl-copilot marketplace (for ground truth); "
                        "required unless --gt-cache is given")
    b.add_argument("--gt-cache", default=None,
                   help="load ground truth from this JSON (tools/build_gt_cache.py "
                        "output) instead of generating it over MCP")
    b.add_argument("--tasks", nargs="+", default=DEFAULT_TASKS)
    b.add_argument("--max-per-task", "--limit", dest="max_per_task", type=int, default=0,
                   help="cap each task to first-N jobs (pilot subset); 0 = full")
    b.add_argument("--seed", type=int, default=None,
                   help="with --limit: shuffle each task's pool with this seed "
                        "(after sorting by trial key) before taking the first N")
    b.add_argument("--repeats", type=int, default=1,
                   help="requests per selected trial (default 1)")
    b.add_argument("--exclude-domains", nargs="+", default=None,
                   help="drop these domain names from the pool")
    b.add_argument("--thinking", choices=THINKING_MODES, default="off",
                   help="off = no thinking key (reference); on = budget_tokens "
                        "(Sonnet 4.6, Haiku 4.5) or adaptive with summarized "
                        "display (Sonnet 5.5); between_tools = Sonnet 5.5 only")
    b.add_argument("--temperature-mode", choices=TEMPERATURE_MODES, default="zero",
                   help="zero = temperature 0 (reference); default = omit it (1.0)")
    b.add_argument("--thinking-budget", type=int, default=None,
                   help="budget_tokens for --thinking on (Sonnet 4.6, Haiku 4.5)")
    b.add_argument("--effort", choices=EFFORT_LEVELS, default=None,
                   help="output_config.effort (Sonnet 5.5 only; the API defaults it to "
                        "high, and D5a policy sends it explicitly)")
    b.add_argument("--prompt-file", default=None,
                   help="alternative user prompt template (tools/prompts/*.txt); "
                        "solve only; sent as the only message, no system prompt, "
                        "no structured output")
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
    b.add_argument("--num-predict", "--max-tokens", dest="num_predict", type=int,
                   default=None,
                   help="override the per-task max_tokens (frontier budget probe "
                        "legs C/D: 64000); default = DEFAULT_NUM_PREDICT[task]")

    s = sub.add_parser("submit", help="create the Anthropic batch")
    s.add_argument("--batch-dir", required=True)
    s.add_argument("--max-list-cost", type=float, default=None,
                   help="refuse to send unless worst case (every request at "
                        "max_tokens, list price) + --already-spent-list-usd "
                        "stays below this many dollars")
    s.add_argument("--already-spent-list-usd", type=float, default=0.0,
                   help="list-price spend of earlier batches under the same cap")

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
    g.add_argument("--snapshot-len", type=int, default=RESPONSE_SNAPSHOT_LEN,
                   help="stored-response snapshot length in characters "
                        f"(default {RESPONSE_SNAPSHOT_LEN}; budget probe: 262144)")

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
