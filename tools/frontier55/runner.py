#!/usr/bin/env python3
"""Runner of the Claude run of 2026-11 (Haiku 5.5 and Sonnet 5.5).

Registration: development/reference/frontier55_prereg.md.

    python -m tools.frontier55.runner dry-run  [--pilot] [--marketplace-path P]
    python -m tools.frontier55.runner batch-submit --model M --out ROOT [--pilot]
    python -m tools.frontier55.runner batch-fetch  --model M --out ROOT --marketplace-path P [--wait]
    python -m tools.frontier55.runner live         --model M --out ROOT --marketplace-path P [--pilot]

Two arms per model, 4,560 trials each (five tasks, wordings v11 to v13):
  no tools   one Message Batches request per trial (`batch-submit`, `batch-fetch`)
  tools      live calls, a manual tool loop of at most MAX_TOOL_LOOPS round trips (`live`)

Each arm of a model has its own folder under ROOT:
  <model>_no-tools/   <model>_tools/
holding
  trials.jsonl       one row per trial, in the harness's row shape
  trial_meta.jsonl   one line per trial: model id returned, API version sent, times,
                     request ids, raw stop reason, usage and content blocks of every turn
  attempts.jsonl     every failed attempt that left a trial undone (it is run again)
  run_manifest.json  the settings; a resume under other settings is refused
and, in the batch arm, batches.json, batch_requests_<n>.jsonl, custom_id_map.json and
batch_results_<n>.jsonl (the raw results, so grading again costs nothing).

Nothing here edits a pinned file. Prompts come from `pddl_eval.runner.build_messages`, the
format-stated no-tools text from `pddl_eval.control_prompts.swap_system`, plans from the
pinned ground-truth cache, tools from local MCP servers through `MCPPlanner`.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pddl_eval import control_prompts as CP  # noqa: E402
from pddl_eval.chat import MAX_TOOL_LOOPS, MCPPlanner, _safe_json_loads  # noqa: E402
from pddl_eval.domains import load_domains  # noqa: E402
from pddl_eval.prompts import ACTIVE_PROMPT_VARIANTS  # noqa: E402
from pddl_eval.runner import (  # noqa: E402
    DEFAULT_NUM_PREDICT,
    RESPONSE_SNAPSHOT_LEN,
    THINKING_SNAPSHOT_LEN,
    TaskResult,
    _trial_key,
    build_jobs,
    build_messages,
)
from pddl_eval.scoring import (  # noqa: E402
    FR_EXCEPTION,
    FR_TOOL_ERROR,
    _classify_step_failure,
    check_success,
    simulate_format_compliant,
)
from tools import _run_manifest as RM  # noqa: E402
from tools.delivered_rerun import constants as RC  # noqa: E402
from tools.delivered_rerun import schema as RS  # noqa: E402
from tools.frontier55 import anthropic_requests as AR  # noqa: E402

# ------------------------------------------------------------------ registered constants
RUN = "frontier55"
MODELS = AR.MODELS
TASKS: tuple[str, ...] = ("solve", "validate_domain", "validate_problem",
                          "validate_plan", "simulate")
WORDINGS: tuple[int, ...] = (11, 12, 13)
ARMS: tuple[str, ...] = ("no-tools", "tools")
PER_TASK_PER_ARM = {"solve": 300, "validate_domain": 360, "validate_problem": 600,
                    "validate_plan": 3000, "simulate": 300}
N_PER_ARM = 4560
# The pilot is its own short list, not a share of the full run: per domain, the first
# problem on solve and simulate; the valid first problem and the first broken problem on
# validate_problem; the valid domain and the broken domain on validate_domain; the first
# valid and the first broken plan of the first problem on validate_plan. Wording v11.
PILOT_PER_TASK_PER_ARM = {"solve": 20, "validate_domain": 40, "validate_problem": 40,
                          "validate_plan": 40, "simulate": 20}
PILOT_PER_ARM = 160
PILOT_WORDING = 11
PILOT_PLAN_LABELS = ("v1", "b1")
BROKEN_DOMAIN = "domain_neg"
BATCH_MAX_REQUESTS = 100_000          # the provider's limits per batch
BATCH_MAX_BYTES = 256 * 1024 * 1024
OUTPUT_CAP = {"solve": 8192, "validate_domain": 6144, "validate_problem": 6144,
              "validate_plan": 6144, "simulate": 6144}
STORAGE_CAP = 65_536
GT_CACHE_REL = "results/derived/gt_cache.json"
GT_CACHE_SHA256 = "77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e"
MARKETPLACE_COMMIT = "5e4f9c0"
PYVALIDATOR = "0.1.5"
INFRA_ABORT = 7            # consecutive undone trials before the live arm stops
THINK_TAG, TOOL_FILTER, PROMPT_STYLE = "off", "all", "minimal"

# sha256 (utf-8) of every system text the run sends. The no-tools texts of solve and
# simulate are the format-stated texts of the control (its cell B); the two with-tools
# digests of solve and simulate are those of the matched run's registration.
SYSTEM_SHA256 = {
    "no-tools": {
        "solve": "3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588",
        "simulate": "7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9",
        "validate_domain": "ab1ffd2abc5e6deab5f37668366b09be3e78d9060646e1aac8ec944fd64d0c36",
        "validate_problem": "f8bea04b4d9e1aac588db14775254f8ef1f77465d1b1f7ec3705441488b9f201",
        "validate_plan": "dcbd1189e28a7f5ace9bcdba92236e6945bd71c9b8b9feed349ceeec09c5c538",
    },
    "tools": {
        "solve": "9b179ca12c2cd2220b46c5478bc637f6dd47356a2f81a4795d3541ecdf6dbb2c",
        "simulate": "ebf8e7fe9d55ab56b9d2d4ba02be4f2b7770fe1b9fdd4d77bba790a68a0d0ac6",
        "validate_domain": "2351f7b2257621ca0155af5206a4304ba7bef79caf974712ac2563101dda839d",
        "validate_problem": "fa18dc28613de2ae12a75efca36bd2aaeb3950fd6f6b6cf7d176295a6a88c54e",
        "validate_plan": "dae2e397c4fc933163608debcab8a6004c170db9f1242ea53b1953909a616f0f",
    },
}

# Job tuple of pddl_eval.runner.build_jobs.
J_TASK, J_DNAME, J_DPDDL, J_PNAME, J_PPDDL, J_PV = 1, 2, 3, 4, 5, 6
J_GT, J_NP, J_PLAN = 8, 9, 10

# Outcome labels of one trial (counted in run_counts.json).
ANSWER, LOOP_EXHAUSTED, OVERFLOW = "answer", "loop_exhausted", "overflow"
REFUSAL, PAUSE_TURN, UNKNOWN_STOP = "refusal", "pause_turn", "unknown_stop"
ERROR_ROW_OUTCOMES = (REFUSAL, PAUSE_TURN, UNKNOWN_STOP)


class Halt(Exception):
    """The run stops; nothing more is sent."""


class MarketplaceRefused(Halt):
    """The tools checkout is not the registered one."""


class ApparatusError(Halt):
    """A request or a row is not what the registration says: a fault of this code."""


class InfraError(Exception):
    """A trial could not be completed for a reason outside the model (rate limit,
    server error, connection). The trial stays undone and is run again."""


def check_constants() -> None:
    def need(cond, what):
        if not cond:
            raise ApparatusError(f"registered constant does not hold: {what}")
    need(MAX_TOOL_LOOPS == 10, "MAX_TOOL_LOOPS == 10")
    need(RESPONSE_SNAPSHOT_LEN == STORAGE_CAP == RC.STORAGE_CAP, "storage cap 65,536")
    need(all(DEFAULT_NUM_PREDICT[t] == OUTPUT_CAP[t] for t in TASKS), "output caps")
    need(tuple(ACTIVE_PROMPT_VARIANTS[:3]) == WORDINGS == tuple(RC.PLAIN), "plain wordings")
    need(sum(PER_TASK_PER_ARM.values()) == N_PER_ARM, "4,560 per arm")
    need(sum(PILOT_PER_TASK_PER_ARM.values()) == PILOT_PER_ARM == 160, "pilot 160 per arm")
    need(SYSTEM_SHA256["no-tools"]["solve"] == CP.SYSTEM_TEXT_SHA256["format-stated"]["solve"]
         and SYSTEM_SHA256["no-tools"]["simulate"]
         == CP.SYSTEM_TEXT_SHA256["format-stated"]["simulate"], "format-stated digests")
    need(set(MODELS) == {"claude-haiku-5-5", "claude-sonnet-5-5"}, "the two models")
    need(RC.THINK == THINK_TAG and RC.TOOL_FILTER == TOOL_FILTER
         and RC.STYLE_A == PROMPT_STYLE, "key tags")


# ------------------------------------------------------------------ small helpers
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def append_jsonl(path: Path, obj: dict) -> None:
    with Path(path).open("a") as fh:
        fh.write(json.dumps(obj) + "\n")
        fh.flush()


def read_jsonl(path: Path) -> tuple[list[dict], int]:
    """(parsed lines, count of unreadable lines). A torn last line is skipped."""
    out, torn = [], 0
    if not Path(path).exists():
        return out, torn
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            torn += 1
    return out, torn


def cell_dir(root: Path, model: str, arm: str) -> Path:
    return Path(root) / f"{model}_{arm}"


# ------------------------------------------------------------------ ground truth and grid
def find_gt_cache(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    return REPO_ROOT / GT_CACHE_REL


def load_gt_cache(path: Path) -> dict:
    """The pinned cache, or a halt. The run never generates ground truth."""
    path = Path(path)
    if not path.exists():
        raise Halt(f"ground-truth cache not found: {path}")
    got = RM.file_sha256(path)
    if got != GT_CACHE_SHA256:
        raise Halt(f"{path}: sha256 {got} is not the pinned {GT_CACHE_SHA256}")
    return json.loads(path.read_text())


def first_problems(domains: dict) -> dict[str, str]:
    """Per domain, its first valid problem (the pilot's problem)."""
    return {d: sorted(p for p in info["problems"])[0] for d, info in domains.items()}


def in_pilot(job: tuple, first: dict[str, str], first_broken: dict[str, str | None]) -> bool:
    """The pilot's list (see PILOT_PER_TASK_PER_ARM)."""
    task, dname, pname = job[J_TASK], job[J_DNAME], job[J_PNAME]
    if job[J_PV] != PILOT_WORDING:
        return False
    if task in ("solve", "simulate"):
        return pname == first[dname]
    if task == "validate_problem":
        return pname in (first[dname], first_broken[dname])
    if task == "validate_domain":
        return pname in (first[dname], BROKEN_DOMAIN)
    return pname == first[dname] and job[J_PLAN] in PILOT_PLAN_LABELS


def build_grid(model: str, arm: str, domains: dict, ground_truth: dict,
               pilot: bool = False) -> list[tuple]:
    """The trials of one model and arm, in a fixed order, counts checked."""
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}")
    jobs, _ = build_jobs(
        models=[model], tasks=list(TASKS), domains=domains, ground_truth=ground_truth,
        num_variants=len(ACTIVE_PROMPT_VARIANTS), conditions=arm, tool_filter=TOOL_FILTER,
        prompt_style=PROMPT_STYLE, think_tag=THINK_TAG)
    jobs = [j for j in jobs if j[J_PV] in WORDINGS]
    want, total = PER_TASK_PER_ARM, N_PER_ARM
    if pilot:
        first = first_problems(domains)
        broken = {d: min((j[J_PNAME] for j in jobs if j[J_DNAME] == d
                          and j[J_TASK] == "validate_problem" and j[J_PNAME] != first[d]
                          and not j[J_PNAME].startswith("p")), default=None)
                  for d in domains}
        jobs = [j for j in jobs if in_pilot(j, first, broken)]
        want, total = PILOT_PER_TASK_PER_ARM, PILOT_PER_ARM
    got = Counter(j[J_TASK] for j in jobs)
    if dict(got) != want or len(jobs) != total:
        raise ApparatusError(f"{model} {arm}: grid is {dict(got)} ({len(jobs)}), "
                             f"registered {want} ({total})")
    jobs.sort(key=lambda j: (TASKS.index(j[J_TASK]), j[J_DNAME], j[J_PNAME],
                             j[J_PLAN], j[J_PV]))
    keys = [tuple(trial_key(model, j, arm == "tools")) for j in jobs]
    if len(set(keys)) != len(keys):
        raise ApparatusError(f"{model} {arm}: duplicate trial keys")
    return jobs


def trial_key(model: str, job: tuple, with_tools: bool) -> list:
    return list(_trial_key(model, job[J_TASK], job[J_DNAME], job[J_PNAME], job[J_PLAN],
                           job[J_PV], with_tools, THINK_TAG, TOOL_FILTER, PROMPT_STYLE))


def custom_id(key: list) -> str:
    """A short stable id of a trial key: letters and digits only, 25 characters."""
    return "t" + hashlib.sha256(json.dumps(key, sort_keys=False).encode("utf-8")).hexdigest()[:24]


def system_and_user(job: tuple, with_tools: bool) -> tuple[str, str]:
    """The system and user text of a trial, from the harness. The no-tools system text of
    solve and simulate is swapped for the format-stated text. Digests are checked."""
    task = job[J_TASK]
    msgs = build_messages(task, job[J_DPDDL], job[J_PPDDL], job[J_PV], with_tools,
                          job[J_GT], prompt_style=PROMPT_STYLE)
    if not with_tools and task in CP.CONTROL_TASKS:
        msgs, _ = CP.swap_system(msgs, "format-stated")
    system, user = msgs[0]["content"], msgs[1]["content"]
    arm = "tools" if with_tools else "no-tools"
    if sha256_text(system) != SYSTEM_SHA256[arm][task]:
        raise ApparatusError(f"system text of {arm} {task} does not match its registered sha256")
    return system, user


def first_request(model: str, job: tuple, with_tools: bool,
                  tools: list[dict] | None) -> dict:
    system, user = system_and_user(job, with_tools)
    if with_tools and tools is None:
        raise ApparatusError("the tool arm needs the tool list")
    return AR.build_params(model, system, [AR.user_message(user)], OUTPUT_CAP[job[J_TASK]],
                           tools if with_tools else None)


def tools_sha256(tools: list[dict]) -> str:
    return sha256_text(json.dumps(tools, sort_keys=True))


# ------------------------------------------------------------------ the tools checkout
def _git(path: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise MarketplaceRefused(f"git {' '.join(args)} failed in {path}: {p.stderr.strip()}")
    return p.stdout


def plugin_freeze(marketplace: Path) -> dict[str, list[str]]:
    """Per plugin that has an environment: its installed packages, `name==version`,
    sorted. Read through the environment's own Python, so it needs no pip there."""
    code = ("import importlib.metadata as m; print('\\n'.join(sorted({f\"{d.metadata['Name']}"
            "=={d.version}\" for d in m.distributions() if d.metadata['Name']})))")
    out = {}
    for plugin in sorted((Path(marketplace) / "plugins").iterdir()):
        py = plugin / ".venv" / "bin" / "python3"
        if not py.exists():
            continue
        p = subprocess.run([str(py), "-c", code], capture_output=True, text=True)
        if p.returncode != 0:
            raise MarketplaceRefused(f"cannot list the packages of {plugin.name}: "
                                     f"{p.stderr.strip()[-300:]}")
        out[plugin.name] = [ln for ln in p.stdout.splitlines() if ln.strip()]
    return out


def pyvalidator_version(marketplace: Path) -> str:
    py = Path(marketplace) / "plugins" / "pddl-validator" / ".venv" / "bin" / "python3"
    if not py.exists():
        raise MarketplaceRefused(
            f"no validator environment at {py}; build it and pin pddl-pyvalidator=={PYVALIDATOR}")
    p = subprocess.run(
        [str(py), "-c",
         "import importlib.metadata as m; print(m.version('pddl-pyvalidator'))"],
        capture_output=True, text=True)
    if p.returncode != 0:
        raise MarketplaceRefused(f"cannot read the validator release: {p.stderr.strip()[-300:]}")
    return p.stdout.strip()


def check_marketplace(path: str | Path) -> dict:
    """Refuse unless the tools checkout is the open models' suite: HEAD at 5e4f9c0, nothing
    changed under plugins/, validator release 0.1.5."""
    path = Path(path).expanduser().resolve()
    if not (path / "plugins").is_dir():
        raise MarketplaceRefused(f"no plugins/ under {path}")
    head = _git(path, "rev-parse", "HEAD").strip()
    if not head.startswith(MARKETPLACE_COMMIT):
        raise MarketplaceRefused(
            f"{path} is at {head[:12]}; the registered tools commit is {MARKETPLACE_COMMIT}")
    dirty = [ln for ln in _git(path, "status", "--porcelain", "--", "plugins").splitlines()
             if ln.strip()]
    if dirty:
        raise MarketplaceRefused(f"{path}/plugins has uncommitted changes: {dirty[:5]}")
    pyval = pyvalidator_version(path)
    if pyval != PYVALIDATOR:
        raise MarketplaceRefused(
            f"validator release is {pyval}; the registered release is {PYVALIDATOR}")
    return {"path": str(path), "commit": head, "pyvalidator": pyval,
            "freeze": plugin_freeze(path)}


async def connect_mcp(marketplace: str | Path) -> MCPPlanner:
    from run_experiment import resolve_plugin_dirs
    mcp = MCPPlanner()
    await mcp.connect(resolve_plugin_dirs(marketplace))
    return mcp


# ------------------------------------------------------------------ one response
def turn_record(turn: int, message: dict, *, requested_at: str | None, received_at: str | None,
                request_id: str | None, version_sent: str | None,
                request: dict | None = None) -> dict:
    """What the sidecar keeps of one request and its response. `request` is the request's
    settings (`AR.request_settings`): every field but the texts and the tool list."""
    return {
        "turn": turn,
        "request": request,
        "requested_at_utc": requested_at,
        "received_at_utc": received_at,
        "request_id": request_id,
        "anthropic_version_sent": version_sent,
        "message_id": message.get("id"),
        "model": message.get("model"),
        "stop_reason": message.get("stop_reason"),
        "stop_details": message.get("stop_details"),
        "usage": message.get("usage"),
        "content": message.get("content") or [],
    }


def message_dict(message) -> dict:
    """A response object as a dict that holds what the API returned."""
    if isinstance(message, dict):
        return message
    d = message.model_dump(mode="json", exclude_unset=True, by_alias=True)
    d["content"] = AR.blocks_as_returned(message)
    return d


async def call_messages(client, params: dict, turn: int) -> dict:
    """One live request. Returns the sidecar record of the response. Raises InfraError for
    a failure outside the model, Halt for a request the API rejects, and passes the
    'prompt is too long' rejection up as the BadRequestError it is."""
    import anthropic
    AR.check_params(params)
    requested = utc_now()
    try:
        raw = await client.messages.with_raw_response.create(**params)
    except anthropic.BadRequestError as exc:
        if AR.is_overflow_error(exc):
            raise
        if "credit balance" in str(exc).lower():
            raise Halt(f"credit balance too low: {exc}") from exc
        raise ApparatusError(f"the API rejected the request: {exc}") from exc
    except (anthropic.APIConnectionError, anthropic.RateLimitError,
            anthropic.InternalServerError) as exc:
        raise InfraError(f"{type(exc).__name__}: {exc}") from exc
    except anthropic.APIStatusError as exc:
        if exc.status_code in (408, 409) or exc.status_code >= 500:
            raise InfraError(f"{type(exc).__name__}: {exc}") from exc
        raise ApparatusError(f"the API rejected the request: {exc}") from exc
    received = utc_now()
    msg = message_dict(raw.parse())
    return turn_record(
        turn, msg, requested_at=requested, received_at=received,
        request_id=raw.headers.get("request-id"),
        version_sent=raw.http_response.request.headers.get("anthropic-version"),
        request=AR.request_settings(params))


def _sum_tokens(turns: list[dict]) -> tuple[int, int]:
    return (sum(AR.input_tokens_of(t["usage"]) for t in turns),
            sum(AR.output_tokens_of(t["usage"]) for t in turns))


def outcome_of(turns: list[dict], tool_calls: list[dict], tool_results: list[dict], *,
               kind: str | None = None, overflow_error: str = "", wall_ns: int = 0) -> dict:
    """The outcome of a finished trial from its turn records."""
    last = turns[-1] if turns else None
    stop = last["stop_reason"] if last else None
    blocks = last["content"] if last else []
    if kind is None:
        if stop == AR.STOP_REFUSAL:
            kind = REFUSAL
        elif stop == AR.STOP_PAUSE:
            kind = PAUSE_TURN
        elif stop == AR.STOP_WINDOW:
            kind = OVERFLOW
        elif stop in (AR.STOP_END, AR.STOP_MAX_TOKENS, AR.STOP_SEQUENCE):
            kind = ANSWER
        else:
            # includes tool_use where no tool loop goes on (the no-tools arm)
            kind = UNKNOWN_STOP
    text = AR.text_of(blocks) if kind == ANSWER else ""
    in_tok, out_tok = _sum_tokens(turns)
    return {"kind": kind, "stop_reason": stop, "text": text,
            "thinking_last": AR.thinking_of(blocks) if kind == ANSWER else "",
            "tool_calls": tool_calls, "tool_results": tool_results, "turns": turns,
            "in_tok": in_tok, "out_tok": out_tok, "wall_ns": int(wall_ns),
            "overflow_error": overflow_error}


async def run_tools_trial(client, mcp, model: str, job: tuple, tools: list[dict]) -> dict:
    """One trial of the tool arm: at most MAX_TOOL_LOOPS round trips."""
    params = first_request(model, job, True, tools)
    messages = list(params["messages"])
    turns: list[dict] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    t0 = time.perf_counter_ns()

    def done(kind=None, overflow_error=""):
        return outcome_of(turns, tool_calls, tool_results, kind=kind,
                          overflow_error=overflow_error,
                          wall_ns=time.perf_counter_ns() - t0)

    import anthropic
    for i in range(MAX_TOOL_LOOPS):
        # How many `thinking` blocks the last response held, and how many of them this
        # request carries back unchanged (the plumbing check compares the two numbers).
        prev = [b for b in turns[-1]["content"] if b.get("type") == "thinking"] if turns else []
        sent_back = messages[-2]["content"] if turns else []
        try:
            rec = await call_messages(client, dict(params, messages=messages), i + 1)
        except anthropic.BadRequestError as exc:
            # The conversation no longer fits the model's window: an outcome of the
            # trial, recorded with what the tools returned so far.
            return done(OVERFLOW, str(exc)[:500])
        rec["thinking_blocks_in_previous_response"] = len(prev)
        rec["thinking_blocks_passed_back"] = sum(1 for b in prev if b in sent_back)
        turns.append(rec)
        if rec["stop_reason"] != AR.STOP_TOOL_USE:
            return done()
        blocks = rec["content"]
        messages = messages + [AR.assistant_turn(blocks)]
        results = []
        for b in AR.tool_uses(blocks):
            args = b.get("input") or {}
            is_error = False
            try:
                result_text = await mcp.call_tool(b["name"], args)
            except Exception as exc:  # the harness's rule (pddl_eval/chat.py)
                result_text, is_error = f"Tool error: {exc}", True
            tool_calls.append({"name": b["name"], "arguments": args, "result": result_text})
            tool_results.append({"turn": i + 1, "tool_use_id": b["id"], "name": b["name"],
                                 "is_error": is_error})
            results.append(AR.tool_result_block(b["id"], result_text, is_error))
        messages = messages + [AR.tool_results_turn(results)]
    return done(LOOP_EXHAUSTED)


# ------------------------------------------------------------------ rows
def loader_check(row_obj: dict, with_tools: bool) -> None:
    """Pass the row through the rerun's frozen loader with the model field swapped for a
    registered open model (the loader knows only those three ids). Every other check of
    the loader applies unchanged. A row cut by storage is refused there by design."""
    tag = RC.PART_A_MODELS[0] if hasattr(RC, "PART_A_MODELS") else next(iter(RC.MODEL_IDS))
    obj = copy.deepcopy(row_obj)
    obj["result"]["model"] = RC.MODEL_IDS[tag]
    obj["key"][0] = RC.MODEL_IDS[tag]
    spec = RS.CellSpec(name=RUN, layer=RS.RERUN, model_tag=tag, with_tools=with_tools,
                       prompt_style=PROMPT_STYLE, tasks=TASKS, variants=WORDINGS, n_rows=0,
                       per_variant=0, per_task_variant={}, k_domains=0)
    RS.parse_row(obj, spec, RUN)


async def make_row(model: str, job: tuple, with_tools: bool, outcome: dict, mcp) -> dict:
    """The trials.jsonl record of a finished trial: {"key", "result"}."""
    task = job[J_TASK]
    kind = outcome["kind"]
    base = dict(model=model, task=task, domain_name=job[J_DNAME], problem_name=job[J_PNAME],
                prompt_variant=job[J_PV], with_tools=with_tools, tool_filter=TOOL_FILTER,
                prompt_style=PROMPT_STYLE, plan_label=job[J_PLAN], infra_failure=False,
                think_truncated=None, duration_s=round(outcome["wall_ns"] / 1e9, 2))
    if kind in ERROR_ROW_OUTCOMES:
        # The shape the harness writes when the client call raised; the loader counts it
        # as an exception row. What the model did return is in the sidecar.
        r = TaskResult(**base, success=False, tool_selected=None, format_compliant=None,
                       response="", response_truncated_by_storage=False, thinking="",
                       tool_calls=[], tokens={}, error=f"stop_reason={outcome['stop_reason']}",
                       failure_reason=FR_EXCEPTION, truncated=False, done_reason="")
    else:
        text = outcome["text"]
        loop_exhausted = kind == LOOP_EXHAUSTED
        if kind == OVERFLOW:
            done_reason = "length"
        elif loop_exhausted:
            done_reason = "tool_calls"
        else:
            done_reason = AR.DONE_REASON_OF_STOP[outcome["stop_reason"]]
        tool_calls = outcome["tool_calls"]
        thinking = outcome["thinking_last"]
        error = ""
        tool_selected: bool | None = None
        fmt: bool | None = None
        try:
            tool_selected, success, failure_reason = await check_success(
                task, text, tool_calls, job[J_GT], mcp, job[J_DPDDL], job[J_PPDDL],
                with_tools=with_tools)
        except Exception as exc:  # as pddl_eval.runner.evaluate_one
            success, failure_reason = False, FR_EXCEPTION
            tool_selected = None
            error = f"scoring error: {exc}"
        else:
            if task == "simulate" and not with_tools:
                fmt = simulate_format_compliant(text)
            if failure_reason == FR_TOOL_ERROR:
                for tc in tool_calls:
                    parsed = _safe_json_loads(tc.get("result"))
                    if isinstance(parsed, dict) and parsed.get("error"):
                        error = f"tool={tc.get('name')}: {parsed.get('message', '')}"
                        break
        failure_reason, truncated = _classify_step_failure(
            success, done_reason, loop_exhausted, failure_reason,
            thinking_text=thinking, response_text=text, error=error)
        if kind == OVERFLOW and not error:
            error = "api: prompt is too long"
        wall = int(outcome["wall_ns"])
        tokens = {"prompt": outcome["in_tok"], "completion": outcome["out_tok"],
                  "turns": len(outcome["turns"]), "total_duration_ns": wall,
                  "eval_duration_ns": wall}
        if kind == OVERFLOW:
            # As the harness writes for an open model whose window is full: one turn was
            # never generated. The frozen loader's `no_room` is then true for this row.
            tokens["ctx_no_room_turns"] = 1
        r = TaskResult(**base, success=success, tool_selected=tool_selected,
                       format_compliant=fmt, response=text[:STORAGE_CAP],
                       response_truncated_by_storage=len(text) > STORAGE_CAP,
                       thinking=thinking[:THINKING_SNAPSHOT_LEN], tool_calls=tool_calls,
                       tokens=tokens,
                       error=error, failure_reason=failure_reason, truncated=truncated,
                       done_reason=done_reason)
    obj = {"key": trial_key(model, job, with_tools), "result": asdict(r)}
    try:
        loader_check(obj, with_tools)
    except RS.RefusedRow:
        if not r.response_truncated_by_storage:
            raise
    except RS.SchemaError as exc:
        raise ApparatusError(f"row not accepted by the frozen loader: {exc}") from exc
    return obj


def make_meta(model: str, job: tuple, with_tools: bool, outcome: dict, row: dict, *,
              transport: str, batch_id: str | None = None, sdk_version: str | None = None,
              extra: dict | None = None) -> dict:
    """The trial_meta.jsonl line of a finished trial."""
    turns = outcome["turns"]
    last = turns[-1] if turns else {}
    key = row["key"]
    meta = {
        "key": key,
        "custom_id": custom_id(key),
        "run": RUN,
        "arm": "tools" if with_tools else "no-tools",
        "transport": transport,
        "model_requested": model,
        "model_ids_returned": sorted({t["model"] for t in turns if t.get("model")}),
        "anthropic_version_sent": sorted({t["anthropic_version_sent"] for t in turns
                                          if t.get("anthropic_version_sent")}),
        "sdk_version": sdk_version,
        "settings": {"thinking": AR.MODEL_SETTINGS[model]["thinking"],
                     "effort": AR.MODEL_SETTINGS[model]["effort"],
                     "max_tokens": OUTPUT_CAP[job[J_TASK]],
                     "system_sha256": SYSTEM_SHA256["tools" if with_tools else "no-tools"]
                     [job[J_TASK]]},
        "batch_id": batch_id,
        "request_ids": [t.get("request_id") for t in turns],
        "n_turns": len(turns),
        "outcome": outcome["kind"],
        "stop_reason": outcome["stop_reason"],
        "stop_details": last.get("stop_details"),
        "overflow_error": outcome["overflow_error"],
        "storage_cut": bool(row["result"]["response_truncated_by_storage"]),
        "answer_chars": len(outcome["text"]),
        "full_answer_if_cut": outcome["text"] if len(outcome["text"]) > STORAGE_CAP else None,
        "tool_results": outcome["tool_results"],
        "turns": turns,
        "written_at_utc": utc_now(),
    }
    if extra:
        meta.update(extra)
    return meta


def outcome_label(meta: dict) -> str:
    return "cut_by_storage" if meta["storage_cut"] else meta["outcome"]


# ------------------------------------------------------------------ folders, manifest, resume
def build_run_manifest(model: str, arm: str, *, pilot: bool, sdk_version: str,
                       gt_cache: Path, ground_truth: dict, marketplace: dict | None,
                       tools_digest: str | None) -> dict:
    with_tools = arm == "tools"
    s = AR.MODEL_SETTINGS[model]
    return RM.build_manifest(
        backend="anthropic-live" if with_tools else "anthropic-batch", model=model,
        with_tools=with_tools, tasks=list(TASKS), corpus="canonical", domains_dir="domains",
        prompt_variants=[PILOT_WORDING] if pilot else list(WORDINGS), num_predict=None,
        snapshot_len=STORAGE_CAP, max_iterations=MAX_TOOL_LOOPS if with_tools else 1,
        stream=False, temperature="not sent (provider default)", think=s["thinking"]["type"],
        ground_truth_source="cached", ground_truth_sha256=RM.ground_truth_sha256(ground_truth),
        gt_cache_sha256=GT_CACHE_SHA256, gt_cache_path=str(gt_cache), sdk_version=sdk_version,
        extra={"run": RUN, "pilot": bool(pilot), "effort": s["effort"],
               "sdk_version_pinned": sdk_version, "output_caps": OUTPUT_CAP,
               "system_sha256": SYSTEM_SHA256[arm],
               "tools_commit": marketplace["commit"] if (marketplace and with_tools) else None,
               "tools_pyvalidator": marketplace["pyvalidator"]
               if (marketplace and with_tools) else None,
               "tools_env": marketplace.get("freeze") if (marketplace and with_tools) else None,
               "tools_sha256": tools_digest})


def done_keys(out_dir: Path) -> set[tuple]:
    rows, torn = read_jsonl(Path(out_dir) / "trials.jsonl")
    if torn:
        print(f"[{RUN}] {out_dir}: skipped {torn} unreadable line(s) of trials.jsonl")
    keys = [tuple(r["key"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ApparatusError(f"{out_dir}/trials.jsonl holds a trial key twice")
    return set(keys)


def write_trial(out_dir: Path, row: dict, meta: dict) -> None:
    """Sidecar line first, then the row: a trial with a row always has its sidecar line."""
    append_jsonl(Path(out_dir) / "trial_meta.jsonl", meta)
    append_jsonl(Path(out_dir) / "trials.jsonl", row)


def log_attempt(out_dir: Path, key: list, what: str, detail: str, **more) -> None:
    append_jsonl(Path(out_dir) / "attempts.jsonl",
                 {"key": key, "custom_id": custom_id(key), "at_utc": utc_now(),
                  "what": what, "detail": detail[:1000], **more})


def write_counts(out_dir: Path, n_grid: int) -> dict:
    metas, _ = read_jsonl(Path(out_dir) / "trial_meta.jsonl")
    done = done_keys(out_dir)
    last = {tuple(m["key"]): m for m in metas if tuple(m["key"]) in done}
    attempts, _ = read_jsonl(Path(out_dir) / "attempts.jsonl")
    counts = {"grid": n_grid, "rows": len(done), "undone": n_grid - len(done),
              "outcomes": dict(Counter(outcome_label(m) for m in last.values())),
              "failed_attempts_logged": len(attempts),
              "model_ids_returned": sorted({i for m in last.values()
                                            for i in m["model_ids_returned"]}),
              "written_at_utc": utc_now()}
    (Path(out_dir) / "run_counts.json").write_text(json.dumps(counts, indent=2) + "\n")
    return counts


def make_client(max_retries: int):
    import anthropic
    return anthropic.AsyncAnthropic(max_retries=max_retries)


def sdk_version() -> str:
    import anthropic
    return anthropic.__version__


# ------------------------------------------------------------------ the tool arm, live
async def run_live_cell(client, mcp, model: str, jobs: list[tuple], out_dir: Path, *,
                        concurrency: int = 4, attempts: int = 3, limit: int | None = None) -> dict:
    """Run the trials of `jobs` that have no row yet. Returns the counts."""
    tools = AR.tool_definitions(mcp.tools)
    done = done_keys(out_dir)
    todo = [j for j in jobs if tuple(trial_key(model, j, True)) not in done]
    if limit:
        todo = todo[:limit]
    print(f"[{RUN}] {model} tools: {len(done)} rows on disk, {len(todo)} to run")
    sem = asyncio.Semaphore(max(1, concurrency))
    state = {"consecutive_undone": 0, "stop": None}
    ver = sdk_version()

    async def one(job):
        key = trial_key(model, job, True)
        async with sem:
            if state["stop"]:
                return
            for attempt in range(1, attempts + 1):
                try:
                    outcome = await run_tools_trial(client, mcp, model, job, tools)
                except InfraError as exc:
                    log_attempt(out_dir, key, "infra", str(exc), attempt=attempt)
                    continue
                except Halt as exc:
                    state["stop"] = state["stop"] or exc
                    return
                try:
                    row = await make_row(model, job, True, outcome, mcp)
                except Halt as exc:
                    state["stop"] = state["stop"] or exc
                    return
                meta = make_meta(model, job, True, outcome, row, transport="live",
                                 sdk_version=ver, extra={"attempt": attempt})
                write_trial(out_dir, row, meta)
                state["consecutive_undone"] = 0
                return
            state["consecutive_undone"] += 1
            if state["consecutive_undone"] >= INFRA_ABORT:
                state["stop"] = state["stop"] or Halt(
                    f"{INFRA_ABORT} trials in a row could not be completed")

    await asyncio.gather(*(one(j) for j in todo))
    counts = write_counts(out_dir, len(jobs))
    if state["stop"]:
        raise state["stop"]
    return counts


# ------------------------------------------------------------------ the no-tools arm, batch
def read_batches(out_dir: Path) -> list[dict]:
    p = Path(out_dir) / "batches.json"
    return json.loads(p.read_text()) if p.exists() else []


def write_batches(out_dir: Path, batches: list[dict]) -> None:
    p = Path(out_dir) / "batches.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(batches, indent=2) + "\n")
    tmp.replace(p)


def batch_requests(model: str, jobs: list[tuple]) -> tuple[list[dict], dict]:
    """({custom_id, params} per trial, {custom_id: trial key})."""
    reqs, id_map = [], {}
    for j in jobs:
        key = trial_key(model, j, False)
        cid = custom_id(key)
        if cid in id_map:
            raise ApparatusError(f"custom_id {cid} is not unique")
        id_map[cid] = key
        reqs.append({"custom_id": cid, "params": first_request(model, j, False, None)})
    return reqs, id_map


async def batch_submit(client, model: str, jobs: list[tuple], out_dir: Path) -> dict:
    """Send one batch holding every trial that has no row yet. Refuses while an earlier
    batch of this folder has not been fetched: that one is polled again, never re-sent."""
    out_dir = Path(out_dir)
    batches = read_batches(out_dir)
    open_ = [b for b in batches if not b.get("fetched")]
    if open_:
        raise Halt(f"{out_dir}: batch {open_[0].get('batch_id') or '(id not recorded)'} is "
                   "not fetched yet; run batch-fetch. Nothing was sent. If no id was "
                   "recorded, the send was interrupted: find the batch in the console "
                   "before sending again.")
    done = done_keys(out_dir)
    todo = [j for j in jobs if tuple(trial_key(model, j, False)) not in done]
    if not todo:
        print(f"[{RUN}] {model} no-tools: every trial has a row; nothing to send")
        return {}
    reqs, id_map = batch_requests(model, todo)
    n = len(batches) + 1
    body = "".join(json.dumps(r) + "\n" for r in reqs)
    if len(reqs) > BATCH_MAX_REQUESTS or len(body.encode("utf-8")) > BATCH_MAX_BYTES:
        raise ApparatusError(f"the batch would hold {len(reqs)} requests and "
                             f"{len(body.encode('utf-8'))} bytes; the limits are "
                             f"{BATCH_MAX_REQUESTS} and {BATCH_MAX_BYTES}")
    (out_dir / f"batch_requests_{n}.jsonl").write_text(body)
    all_map = {}
    map_path = out_dir / "custom_id_map.json"
    if map_path.exists():
        all_map = json.loads(map_path.read_text())
    all_map.update(id_map)
    map_path.write_text(json.dumps(all_map, indent=0) + "\n")
    entry = {"n": n, "batch_id": None, "n_requests": len(reqs), "fetched": False,
             "send_started_at_utc": utc_now()}
    write_batches(out_dir, batches + [entry])           # before the send
    raw = await client.messages.batches.with_raw_response.create(requests=reqs)
    batch = raw.parse()
    entry.update(batch_id=batch.id, submitted_at_utc=utc_now(),
                 request_id=raw.headers.get("request-id"),
                 anthropic_version_sent=raw.http_response.request.headers.get(
                     "anthropic-version"),
                 sdk_version=sdk_version())
    write_batches(out_dir, batches + [entry])
    print(f"[{RUN}] {model} no-tools: batch {batch.id} sent, {len(reqs)} requests")
    return entry


async def batch_poll(client, out_dir: Path, *, wait: bool, interval: float = 120.0) -> dict | None:
    """Fetch the raw results of the open batch once it has ended. Returns the batch entry,
    or None when it has not ended (and `wait` is off)."""
    out_dir = Path(out_dir)
    batches = read_batches(out_dir)
    open_ = [b for b in batches if not b.get("fetched")]
    if not open_:
        return None
    entry = open_[0]
    if not entry.get("batch_id"):
        raise Halt(f"{out_dir}: a send was started at {entry['send_started_at_utc']} and no "
                   "batch id was recorded. Find the batch in the console, write its id into "
                   "batches.json, then fetch.")
    raw_path = out_dir / f"batch_results_{entry['n']}.jsonl"
    if not raw_path.exists():
        while True:
            b = await client.messages.batches.retrieve(entry["batch_id"])
            if b.processing_status == "ended":
                break
            rc = b.request_counts
            print(f"[{RUN}] batch {entry['batch_id']}: {b.processing_status} "
                  f"(processing {rc.processing}, succeeded {rc.succeeded}, "
                  f"errored {rc.errored})")
            if not wait:
                return None
            await asyncio.sleep(interval)
        lines = []
        async for res in await client.messages.batches.results(entry["batch_id"]):
            lines.append(json.dumps(res.model_dump(mode="json", exclude_unset=True,
                                                   by_alias=True)))
        tmp = raw_path.with_suffix(".jsonl.tmp")
        tmp.write_text("".join(ln + "\n" for ln in lines))
        tmp.replace(raw_path)
        entry.update(
            created_at=b.created_at.isoformat() if b.created_at else None,
            ended_at=b.ended_at.isoformat() if b.ended_at else None,
            request_counts=b.request_counts.model_dump(mode="json"),
            results_fetched_at_utc=utc_now())
        write_batches(out_dir, batches)
    return entry


async def batch_grade(model: str, jobs: list[tuple], out_dir: Path, mcp, entry: dict,
                      marketplace: dict | None = None) -> dict:
    """Rows and sidecar lines from the stored raw results of one batch. A result that is
    not `succeeded` leaves its trial undone and is logged; the next batch-submit sends it
    again."""
    out_dir = Path(out_dir)
    by_cid = {custom_id(trial_key(model, j, False)): j for j in jobs}
    done = done_keys(out_dir)
    rejected: list[str] = []
    sent = {q["custom_id"]: q["params"]
            for q in read_jsonl(out_dir / f"batch_requests_{entry['n']}.jsonl")[0]}
    raw, torn = read_jsonl(out_dir / f"batch_results_{entry['n']}.jsonl")
    if torn:
        raise ApparatusError(f"{out_dir}: {torn} unreadable raw result line(s)")
    for res in raw:
        cid = res["custom_id"]
        job = by_cid.get(cid)
        if job is None:
            raise ApparatusError(f"batch result {cid} is not a trial of this grid")
        key = trial_key(model, job, False)
        if tuple(key) in done:
            continue
        result = res["result"]
        if result["type"] != "succeeded":
            log_attempt(out_dir, key, f"batch_{result['type']}",
                        json.dumps(result.get("error"))[:1000], batch_id=entry["batch_id"])
            err = (result.get("error") or {}).get("error") or {}
            if err.get("type") == "invalid_request_error":
                rejected.append(f"{cid}: {err.get('message')}")
            continue
        rec = turn_record(1, result["message"], requested_at=entry.get("submitted_at_utc"),
                          received_at=entry.get("ended_at"), request_id=None,
                          version_sent=entry.get("anthropic_version_sent"),
                          request=AR.request_settings(sent[cid]) if cid in sent else None)
        outcome = outcome_of([rec], [], [])
        row = await make_row(model, job, False, outcome, mcp)
        meta = make_meta(model, job, False, outcome, row, transport="batch",
                         batch_id=entry["batch_id"], sdk_version=entry.get("sdk_version"),
                         extra={"batch_created_at": entry.get("created_at"),
                                "batch_ended_at": entry.get("ended_at")})
        write_trial(out_dir, row, meta)
        done.add(tuple(key))
    batches = read_batches(out_dir)
    for b in batches:
        if b["n"] == entry["n"]:
            b["fetched"] = True
            b["graded_at_utc"] = utc_now()
            if marketplace:
                b["graded_with_tools_commit"] = marketplace["commit"]
                b["graded_with_pyvalidator"] = marketplace["pyvalidator"]
    write_batches(out_dir, batches)
    counts = write_counts(out_dir, len(jobs))
    if rejected:
        # A request the API calls invalid is a fault of this code, not a trial outcome:
        # sending it again would fail again.
        raise ApparatusError(f"{len(rejected)} request(s) of batch {entry['batch_id']} were "
                             f"rejected as invalid; first: {rejected[0]}")
    return counts


# ------------------------------------------------------------------ dry run
def dry_run(models, domains, ground_truth, *, pilot: bool, tools: list[dict] | None) -> dict:
    """Build every first request of the run; no client, no call. Returns the report."""
    placeholder = tools is None
    tool_list = tools if tools is not None else []
    report = {"pilot": pilot, "cells": [], "system_sha256": SYSTEM_SHA256,
              "output_caps": OUTPUT_CAP, "max_tool_loops": MAX_TOOL_LOOPS,
              "gt_cache_sha256": GT_CACHE_SHA256,
              "tools_sha256": None if placeholder else tools_sha256(tool_list),
              "tools": None if placeholder else [t["name"] for t in tool_list]}
    total = 0
    for model in models:
        for arm in ARMS:
            jobs = build_grid(model, arm, domains, ground_truth, pilot)
            h = hashlib.sha256()
            chars = Counter()
            for j in jobs:
                p = first_request(model, j, arm == "tools", tool_list)
                key = trial_key(model, j, arm == "tools")
                user = p["messages"][0]["content"]
                h.update((custom_id(key) + sha256_text(p["system"]) + sha256_text(user)).encode())
                chars[j[J_TASK]] += len(p["system"]) + len(user)
            first = first_request(model, jobs[0], arm == "tools", tool_list)
            report["cells"].append({
                "model": model, "arm": arm, "n": len(jobs),
                "per_task": dict(Counter(j[J_TASK] for j in jobs)),
                "prompt_chars_per_task": dict(chars),
                "prompts_sha256": h.hexdigest(),
                "request_keys": sorted(first),
                "thinking": first["thinking"], "output_config": first["output_config"]})
            total += len(jobs)
    report["total_trials"] = total
    return report


def print_dry_run(rep: dict) -> None:
    print(f"[{RUN}] DRY RUN ({'pilot' if rep['pilot'] else 'full run'}): no API call is made")
    for c in rep["cells"]:
        print(f"  {c['model']:18s} {c['arm']:8s} n={c['n']:5d}  "
              + "  ".join(f"{t}={c['per_task'][t]}" for t in TASKS))
        print(f"    thinking={json.dumps(c['thinking'])} output_config="
              f"{json.dumps(c['output_config'])} keys={c['request_keys']}")
        print(f"    prompts sha256 {c['prompts_sha256']}")
    print(f"  total trials: {rep['total_trials']}")
    print(f"  output caps (max_tokens): {rep['output_caps']}; tool round trips: "
          f"{rep['max_tool_loops']}")
    for arm in ARMS:
        for t in TASKS:
            print(f"  system sha256 {arm:8s} {t:17s} {rep['system_sha256'][arm][t]}")
    print(f"  ground-truth cache sha256 {rep['gt_cache_sha256']}")
    if rep["tools_sha256"]:
        print(f"  tools ({len(rep['tools'])}): {rep['tools']}\n  tools sha256 {rep['tools_sha256']}")
    else:
        print("  tools: not loaded (pass --marketplace-path to load and digest them)")


# ------------------------------------------------------------------ pilot check
def pilot_check_cell(out_dir: Path, model: str, arm: str, n_expected: int) -> dict:
    """The plumbing check of one folder (registration, section 6). It reads no grade, no
    verdict and no answer text: only counts, shapes, settings and ids."""
    out_dir = Path(out_dir)
    with_tools = arm == "tools"
    rows, torn = read_jsonl(out_dir / "trials.jsonl")
    metas, _ = read_jsonl(out_dir / "trial_meta.jsonl")
    meta_by_key = {tuple(m["key"]): m for m in metas}
    attempts, _ = read_jsonl(out_dir / "attempts.jsonl")
    refused_by_loader = cut = 0
    for row in rows:
        try:
            loader_check(row, with_tools)
        except RS.RefusedRow:
            cut += 1
        except RS.SchemaError:
            refused_by_loader += 1
    keys = [tuple(r["key"]) for r in rows]
    mine = [meta_by_key[k] for k in keys if k in meta_by_key]
    countable = [r for r in rows if tuple(r["key"]) in meta_by_key
                 and meta_by_key[tuple(r["key"])]["outcome"] in (ANSWER, LOOP_EXHAUSTED)]
    non_empty = sum(1 for r in countable if r["result"]["response"].strip())
    want = {"thinking": AR.MODEL_SETTINGS[model]["thinking"],
            "effort": AR.MODEL_SETTINGS[model]["effort"]}
    # From the sidecar: the settings of every request that was sent.
    n_requests = bad_requests = sampling = think_back = think_seen = 0
    for m in mine:
        cap = OUTPUT_CAP[m["key"][1]]
        for t in m["turns"]:
            req = t.get("request")
            n_requests += 1
            if req is None or req != AR.registered_request_settings(
                    model, cap, with_tools, req.get("n_messages", -1)):
                bad_requests += 1
            if req and (set(req) | set(req.get("param_keys", []))) & AR.SAMPLING_KEYS:
                sampling += 1
            think_seen += t.get("thinking_blocks_in_previous_response", 0)
            think_back += t.get("thinking_blocks_passed_back", 0)
    ids = sorted({i for m in mine for i in m["model_ids_returned"]})
    ids_ok = all(i.startswith(model) for i in ids)
    settings_ok = all(m["settings"]["thinking"] == want["thinking"]
                      and m["settings"]["effort"] == want["effort"]
                      and m["settings"]["max_tokens"] == OUTPUT_CAP[m["key"][1]]
                      and m["model_requested"] == model for m in mine)
    stored_requests_ok = None
    if not with_tools:
        stored_requests_ok = True
        for f in sorted(out_dir.glob("batch_requests_*.jsonl")):
            for req in read_jsonl(f)[0]:
                try:
                    AR.check_params(req["params"])
                except ValueError:
                    stored_requests_ok = False
    manifest = RM.read_manifest(out_dir) or {}
    rep = {
        "folder": str(out_dir), "model": model, "arm": arm,
        "rows": len(rows), "rows_expected": n_expected,
        "duplicate_keys": len(keys) - len(set(keys)),
        "rows_without_sidecar_line": sum(1 for k in keys if k not in meta_by_key),
        "half_written_lines": torn,
        "rows_the_frozen_loader_refuses": refused_by_loader,
        "rows_cut_by_storage": cut,
        "non_empty_answers": non_empty, "answers_counted": len(countable),
        "settings_as_registered": settings_ok,
        "requests_in_sidecar": n_requests,
        "requests_whose_settings_differ_from_the_registered": bad_requests,
        "requests_with_a_sampling_field": sampling,
        "model_ids_start_with_the_requested_id": ids_ok,
        "thinking_blocks_returned_before_a_next_request": think_seen,
        "thinking_blocks_passed_back_unchanged": think_back,
        "stored_batch_requests_as_registered": stored_requests_ok,
        "api_version_sent": sorted({v for m in mine for v in m["anthropic_version_sent"]}),
        "sdk_versions": sorted({str(m["sdk_version"]) for m in mine}),
        "model_ids_returned": sorted({i for m in mine for i in m["model_ids_returned"]}),
        "endings": dict(Counter(outcome_label(m) for m in mine)),
        "failed_attempts_logged": len(attempts),
        "trials_with_a_note_between_tool_calls": sum(
            1 for m in mine if any(b.get("type") == "thinking"
                                   for t in m["turns"] for b in t["content"])),
        "manifest_tools_commit": manifest.get("tools_commit"),
        "manifest_tools_sha256": manifest.get("tools_sha256"),
    }
    share = non_empty / len(countable) if countable else 0.0
    rep["passes"] = bool(
        len(rows) == n_expected and rep["duplicate_keys"] == 0
        and rep["rows_without_sidecar_line"] == 0 and torn == 0 and refused_by_loader == 0
        and cut == 0 and share >= 0.95 and settings_ok and stored_requests_ok is not False
        and len(rep["api_version_sent"]) == 1 and bad_requests == 0 and sampling == 0
        and ids_ok and think_seen == think_back)
    return rep


def pilot_check(root: Path, models=MODELS, n_expected: int = PILOT_PER_ARM) -> list[dict]:
    return [pilot_check_cell(cell_dir(root, m, arm), m, arm, n_expected)
            for m in models for arm in ARMS]


# ------------------------------------------------------------------ CLI
def _prepare(args, arm: str, need_marketplace: bool):
    check_constants()
    if args.model not in MODELS:
        raise Halt(f"--model must be one of {MODELS}")
    if args.pilot != ("pilot" in Path(args.out).name):
        raise Halt("a pilot writes under a folder named *pilot*, the full run never does "
                   f"(--out {args.out}, pilot={args.pilot})")
    market = check_marketplace(args.marketplace_path) if need_marketplace else None
    gt_path = find_gt_cache(args.gt_cache)
    gt = load_gt_cache(gt_path)
    domains = load_domains(REPO_ROOT / "domains")
    jobs = build_grid(args.model, arm, domains, gt, args.pilot)
    out = cell_dir(Path(args.out), args.model, arm)
    return market, gt_path, gt, jobs, out


async def _cmd_live(args) -> None:
    market, gt_path, gt, jobs, out = _prepare(args, "tools", True)
    mcp = await connect_mcp(args.marketplace_path)
    client = make_client(args.max_retries)
    try:
        tools = AR.tool_definitions(mcp.tools)
        RM.ensure_manifest(out, build_run_manifest(
            args.model, "tools", pilot=args.pilot, sdk_version=sdk_version(), gt_cache=gt_path,
            ground_truth=gt, marketplace=market, tools_digest=tools_sha256(tools)))
        counts = await run_live_cell(client, mcp, args.model, jobs, out,
                                     concurrency=args.concurrency, attempts=args.attempts,
                                     limit=args.limit)
        print(json.dumps(counts, indent=2))
    finally:
        await mcp.close()
        await client.close()


async def _cmd_batch_submit(args) -> None:
    _market, gt_path, gt, jobs, out = _prepare(args, "no-tools", False)
    RM.ensure_manifest(out, build_run_manifest(
        args.model, "no-tools", pilot=args.pilot, sdk_version=sdk_version(), gt_cache=gt_path,
        ground_truth=gt, marketplace=None, tools_digest=None))
    client = make_client(args.max_retries)
    try:
        await batch_submit(client, args.model, jobs, out)
    finally:
        await client.close()


async def _cmd_batch_fetch(args) -> None:
    market, _gt_path, _gt, jobs, out = _prepare(args, "no-tools", True)
    client = make_client(args.max_retries)
    try:
        entry = await batch_poll(client, out, wait=args.wait, interval=args.interval)
    finally:
        await client.close()
    if entry is None:
        print(f"[{RUN}] no batch to grade yet")
        return
    mcp = await connect_mcp(args.marketplace_path)     # solve plans go to the validator
    try:
        print(json.dumps(await batch_grade(args.model, jobs, out, mcp, entry, market),
                         indent=2))
    finally:
        await mcp.close()


async def _cmd_dry_run(args) -> None:
    check_constants()
    gt = load_gt_cache(find_gt_cache(args.gt_cache))
    domains = load_domains(REPO_ROOT / "domains")
    tools = None
    if args.marketplace_path:
        check_marketplace(args.marketplace_path)
        mcp = await connect_mcp(args.marketplace_path)
        try:
            tools = AR.tool_definitions(mcp.tools)
        finally:
            await mcp.close()
    print_dry_run(dry_run(args.models, domains, gt, pilot=args.pilot, tools=tools))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, model=True):
        if model:
            sp.add_argument("--model", required=True, choices=list(MODELS))
            sp.add_argument("--out", required=True,
                            help="root folder, e.g. results/frontier55 or "
                                 "results/frontier55-pilot")
            sp.add_argument("--max-retries", type=int, default=4,
                            help="the SDK's own retries per request")
        sp.add_argument("--pilot", action="store_true",
                        help="the pilot's short list, wording v11 (160 trials per model "
                             "and arm)")
        sp.add_argument("--gt-cache", default=None,
                        help=f"default {GT_CACHE_REL}; must match the pinned sha256")

    d = sub.add_parser("dry-run", help="build every request, print counts and digests")
    common(d, model=False)
    d.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    d.add_argument("--marketplace-path", default=None)

    s = sub.add_parser("batch-submit", help="no-tools arm: send one batch")
    common(s)
    f = sub.add_parser("batch-fetch", help="no-tools arm: fetch an ended batch and write rows")
    common(f)
    f.add_argument("--marketplace-path", required=True)
    f.add_argument("--wait", action="store_true", help="poll until the batch has ended")
    f.add_argument("--interval", type=float, default=120.0)

    lv = sub.add_parser("live", help="tool arm: live calls with a tool loop")
    common(lv)
    lv.add_argument("--marketplace-path", required=True)
    lv.add_argument("--concurrency", type=int, default=4)
    lv.add_argument("--attempts", type=int, default=3,
                    help="tries per trial in one invocation when the failure is outside "
                         "the model")
    lv.add_argument("--limit", type=int, default=None)

    pc = sub.add_parser("pilot-check", help="the plumbing check of the pilot's folders "
                                            "(counts, shapes, settings, ids; no outcome)")
    pc.add_argument("--out", required=True)

    args = p.parse_args(argv)
    if args.cmd == "pilot-check":
        reps = pilot_check(Path(args.out))
        print(json.dumps(reps, indent=2))
        return 0 if all(x["passes"] for x in reps) else 2
    cmd = {"dry-run": _cmd_dry_run, "batch-submit": _cmd_batch_submit,
           "batch-fetch": _cmd_batch_fetch, "live": _cmd_live}[args.cmd]
    try:
        asyncio.run(cmd(args))
    except (Halt, RM.ManifestError) as exc:
        print(f"[{RUN}] HALT: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
