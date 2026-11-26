"""Tests of the Claude run's runner (tools/frontier55), with no network.

The real `anthropic` SDK is used on an httpx mock transport, so the tests see the
exact JSON body and headers the SDK would send. No request leaves the process.

Run standalone: `python3 tests/test_frontier55.py`
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import anthropic  # noqa: E402
import httpx  # noqa: E402

from pddl_eval import control_prompts as CP  # noqa: E402
from pddl_eval.prompts import WITH_TOOLS_SYSTEM_BY_TASK  # noqa: E402
from pddl_eval.runner import build_messages  # noqa: E402
from tests._helpers import (FakeMCP, TestResults, build_gt_from_fixture,  # noqa: E402
                            load_fixture, plan_sensitive_validator)
from tools import _run_manifest as RM  # noqa: E402
from tools.delivered_rerun import schema as RS  # noqa: E402
from tools.frontier55 import anthropic_requests as AR  # noqa: E402
from tools.frontier55 import cost as COST  # noqa: E402
from tools.frontier55 import runner as R  # noqa: E402

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
FX = load_fixture("blocksworld_p01")
GT = build_gt_from_fixture(FX)
DOM, PROB = FX["domain_pddl"], FX["problem_pddl"]
PLANNER_OK = json.dumps(FX["tool_output_objs"]["classic_planner_ok"])
TOOLS = [{"name": "classic_planner", "description": "Plan.",
          "input_schema": {"type": "object", "properties": {"domain": {"type": "string"},
                                                            "problem": {"type": "string"}}}}]
FORMAT_STATED_SOLVE = (
    "You are a PDDL planning assistant. PDDL planning tools are not "
    "available in this evaluation. Analyze the domain and problem and "
    "produce a plan using your own reasoning; end your response with "
    "the plan alone in a fenced code block, one parenthesised PDDL "
    "action per line.")
WITH_TOOLS_SOLVE = (
    "You are a PDDL planning assistant. LLMs cannot reliably generate "
    "correct plans from training alone (arXiv:2509.12987). Use the "
    "available planner tool to produce the plan.")


def job(task: str, model: str = SONNET, pv: int = 11, with_tools: bool = True) -> tuple:
    plan_label = "v1" if task == "validate_plan" else ""
    return (model, task, "blocksworld", DOM, "p01", PROB, pv, with_tools, GT,
            R.OUTPUT_CAP[task], plan_label)


def user_text(task: str, with_tools: bool, pv: int = 11) -> str:
    return build_messages(task, DOM, PROB, pv, with_tools, GT)[1]["content"]


def mcp_ok() -> FakeMCP:
    base = plan_sensitive_validator(FX)

    def handler(name, args):
        if name == "classic_planner":
            return PLANNER_OK
        return base(name, args)
    return FakeMCP(handler)


def msg(content: list[dict], stop: str, model: str = SONNET, in_tok: int = 100,
        out_tok: int = 20, think_tok: int | None = None, **more) -> dict:
    usage = {"input_tokens": in_tok, "output_tokens": out_tok}
    if think_tok is not None:
        usage["output_tokens_details"] = {"thinking_tokens": think_tok}
    return {"id": "msg_x", "type": "message", "role": "assistant", "model": model,
            "content": content, "stop_reason": stop, "stop_sequence": None,
            "usage": usage, **more}


THINK = {"type": "thinking", "thinking": "Calling the planner.", "signature": "SIG==",
         "field_this_sdk_does_not_know": 7}


def tool_use(i: int = 1, name: str = "classic_planner") -> dict:
    return {"type": "tool_use", "id": f"tu{i}", "name": name,
            "input": {"domain": DOM, "problem": PROB}}


TEXT_PLAN = {"type": "text", "text": "```\n(pick-up b)\n(stack b c)\n(pick-up a)\n(stack a b)\n```"}


class Wire:
    """A scripted API. `reply(body)` returns a message dict, or (status, json)."""

    def __init__(self, reply):
        self.reply = reply
        self.bodies: list[dict] = []
        self.headers: list[dict] = []
        self.paths: list[str] = []
        self.n = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content) if req.content else None
        self.paths.append(f"{req.method} {req.url.path}")
        self.bodies.append(body)
        self.headers.append(dict(req.headers))
        self.n += 1
        out = self.reply(req, body, self.n)
        if isinstance(out, httpx.Response):
            return out
        status, payload = out if isinstance(out, tuple) else (200, out)
        return httpx.Response(status, headers={"request-id": f"req_{self.n}"}, json=payload)

    def client(self, max_retries: int = 0) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(
            api_key="not-a-key", max_retries=max_retries,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(self)))


def has_tool_result(body: dict) -> bool:
    last = body["messages"][-1]["content"]
    return isinstance(last, list) and any(b.get("type") == "tool_result" for b in last)


def one_tool_then_answer(req, body, n):
    if has_tool_result(body):
        return msg([TEXT_PLAN], "end_turn", in_tok=400, out_tok=30)
    return msg([THINK, tool_use()], "tool_use", think_tok=3)


def loader_row(row: dict, with_tools: bool):
    """The row as the rerun's frozen loader reads it (model name swapped)."""
    import copy
    from tools.delivered_rerun import constants as RC
    obj = copy.deepcopy(row)
    obj["result"]["model"] = obj["key"][0] = RC.MODEL_IDS["Qwen3_5_9B"]
    spec = RS.CellSpec(name="x", layer=RS.RERUN, model_tag="Qwen3_5_9B", with_tools=with_tools,
                       prompt_style="minimal", tasks=R.TASKS, variants=R.WORDINGS, n_rows=0,
                       per_variant=0, per_task_variant={}, k_domains=0)
    return RS.parse_row(obj, spec, "x")


def api_error(status: int, kind: str, message: str):
    return status, {"type": "error", "error": {"type": kind, "message": message}}


async def trial(wire: Wire, task: str = "solve", model: str = SONNET, mcp=None):
    mcp = mcp or mcp_ok()
    c = wire.client()
    try:
        j = job(task, model)
        outcome = await R.run_tools_trial(c, mcp, model, j, TOOLS)
        row = await R.make_row(model, j, True, outcome, mcp)
        meta = R.make_meta(model, j, True, outcome, row, transport="live", sdk_version="t")
        return outcome, row, meta
    finally:
        await c.close()


# ---------------------------------------------------------------------------
def test_request_shapes(r: TestResults) -> None:
    for model, thinking, effort in ((HAIKU, {"type": "disabled"}, "medium"),
                                    (SONNET, {"type": "between_tools"}, "high")):
        got = R.first_request(model, job("solve", model, with_tools=False), False, None)
        r.check_eq(f"{model} no-tools solve request", got, {
            "model": model, "max_tokens": 8192, "system": FORMAT_STATED_SOLVE,
            "messages": [{"role": "user", "content": user_text("solve", False)}],
            "thinking": thinking, "output_config": {"effort": effort}})
        got = R.first_request(model, job("solve", model), True, TOOLS)
        r.check_eq(f"{model} tools solve request", got, {
            "model": model, "max_tokens": 8192, "system": WITH_TOOLS_SOLVE,
            "messages": [{"role": "user", "content": user_text("solve", True)}],
            "thinking": thinking, "output_config": {"effort": effort}, "tools": TOOLS})
    sim = R.first_request(SONNET, job("simulate", with_tools=False), False, None)
    r.check_eq("simulate cap", sim["max_tokens"], 6144)
    r.check_eq("simulate no-tools system is the format-stated text", sim["system"],
               CP.NO_TOOLS_SYSTEM_CONTROL["format-stated"]["simulate"])
    r.check_eq("simulate user text is the harness's, nothing appended",
               sim["messages"][0]["content"], user_text("simulate", False))
    r.check("no JSON directive", "Return ONLY a single JSON object" not in json.dumps(sim))
    for task in ("validate_domain", "validate_problem", "validate_plan"):
        p = R.first_request(HAIKU, job(task, HAIKU, with_tools=False), False, None)
        r.check_eq(f"{task} cap", p["max_tokens"], 6144)
        r.check_eq(f"{task} no-tools system sha", R.sha256_text(p["system"]),
                   R.SYSTEM_SHA256["no-tools"][task])
        p = R.first_request(HAIKU, job(task, HAIKU), True, TOOLS)
        r.check_eq(f"{task} tools system", p["system"], WITH_TOOLS_SYSTEM_BY_TASK[task])
    for bad in ({"temperature": 0}, {"top_p": 0.5}, {"tool_choice": {"type": "any"}},
                {"fallbacks": ["x"]}, {"cache_control": {"type": "ephemeral"}}):
        try:
            AR.check_params({**sim, **bad})
            r.check(f"refuses {list(bad)[0]}", False, "accepted")
        except ValueError:
            r.check(f"refuses {list(bad)[0]}", True)
    for label, bad in (
            ("output_config.format", {**sim, "output_config": {"effort": "high", "format": {}}}),
            ("another effort", {**sim, "output_config": {"effort": "low"}}),
            ("budget in thinking", {**sim, "thinking": {"type": "between_tools",
                                                         "budget_tokens": 1024}}),
            ("assistant prefill", {**sim, "messages": sim["messages"]
                                   + [{"role": "assistant", "content": "{"}]})):
        try:
            AR.check_params(bad)
            r.check(f"refuses {label}", False, "accepted")
        except ValueError:
            r.check(f"refuses {label}", True)
    r.check_eq("tool definition", AR.tool_definitions([{"type": "function", "function": {
        "name": "n", "description": "d", "parameters": {"type": "object"}}}]),
        [{"name": "n", "description": "d", "input_schema": {"type": "object"}}])
    r.check("constants hold", R.check_constants() is None)


async def test_tool_loop(r: TestResults) -> None:
    wire = Wire(one_tool_then_answer)
    outcome, row, meta = await trial(wire)
    res = row["result"]
    r.check_eq("two requests", wire.n, 2)
    r.check_eq("path", wire.paths, ["POST /v1/messages"] * 2)
    first, second = wire.bodies
    r.check_eq("first body", first, {
        "model": SONNET, "max_tokens": 8192, "system": WITH_TOOLS_SOLVE,
        "messages": [{"role": "user", "content": user_text("solve", True)}],
        "thinking": {"type": "between_tools"}, "output_config": {"effort": "high"},
        "tools": TOOLS})
    r.check_eq("second body: assistant blocks passed back unchanged, one result message",
               second["messages"], [
                   {"role": "user", "content": user_text("solve", True)},
                   {"role": "assistant", "content": [THINK, tool_use()]},
                   {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu1",
                                                 "content": PLANNER_OK}]}])
    r.check_eq("second body keeps every other field",
               {k: v for k, v in second.items() if k != "messages"},
               {k: v for k, v in first.items() if k != "messages"})
    r.check("no stream / temperature / tool_choice on the wire",
            not ({"stream", "temperature", "tool_choice", "top_p", "top_k"} & set(first)))
    r.check_eq("outcome", outcome["kind"], R.ANSWER)
    r.check_eq("row keys", set(row), {"key", "result"})
    r.check_eq("key", row["key"], [SONNET, "solve", "blocksworld", "p01", "", 11, True,
                                   "off", "all", "minimal"])
    r.check_eq("tool_calls", res["tool_calls"], [{
        "name": "classic_planner", "arguments": {"domain": DOM, "problem": PROB},
        "result": PLANNER_OK}])
    r.check_eq("response", res["response"], TEXT_PLAN["text"])
    r.check_eq("done_reason", res["done_reason"], "stop")
    r.check_eq("tokens keys", set(res["tokens"]), {"prompt", "completion", "turns",
                                                   "total_duration_ns", "eval_duration_ns"})
    r.check_eq("tokens", (res["tokens"]["prompt"], res["tokens"]["completion"],
                          res["tokens"]["turns"]), (500, 50, 2))
    r.check_eq("stored flags", (res["response_truncated_by_storage"], res["think_truncated"],
                                res["format_compliant"], res["infra_failure"], res["thinking"]),
               (False, None, None, False, ""))
    r.check_eq("harness grade (tool verified)", (res["success"], res["tool_selected"],
                                                 res["failure_reason"]), (True, True, "ok"))
    r.check_eq("24 result keys", set(res), set(RS.RERUN_RESULT_KEYS))
    # sidecar
    r.check_eq("meta key", meta["key"], row["key"])
    r.check_eq("meta model ids", meta["model_ids_returned"], [SONNET])
    r.check_eq("meta version sent", meta["anthropic_version_sent"], ["2023-06-01"])
    r.check_eq("meta request ids", meta["request_ids"], ["req_1", "req_2"])
    r.check_eq("meta settings", meta["settings"], {
        "thinking": {"type": "between_tools"}, "effort": "high", "max_tokens": 8192,
        "system_sha256": R.SYSTEM_SHA256["tools"]["solve"]})
    r.check_eq("meta turns", meta["n_turns"], 2)
    r.check_eq("meta raw blocks of turn 1", meta["turns"][0]["content"], [THINK, tool_use()])
    r.check_eq("meta usage as returned", meta["turns"][0]["usage"],
               {"input_tokens": 100, "output_tokens": 20,
                "output_tokens_details": {"thinking_tokens": 3}})
    r.check_eq("meta stop reasons", [t["stop_reason"] for t in meta["turns"]],
               ["tool_use", "end_turn"])
    r.check_eq("meta: settings of each request sent", [t["request"] for t in meta["turns"]], [
        {"model": SONNET, "max_tokens": 8192, "thinking": {"type": "between_tools"},
         "output_config": {"effort": "high"}, "has_tools": True, "n_messages": n,
         "param_keys": ["max_tokens", "messages", "model", "output_config", "system",
                        "thinking", "tools"]} for n in (1, 3)])
    r.check_eq("meta: the note of turn 1 went back in request 2",
               [(t["thinking_blocks_in_previous_response"], t["thinking_blocks_passed_back"])
                for t in meta["turns"]], [(0, 0), (1, 1)])
    r.check("meta times", all(t["requested_at_utc"] and t["received_at_utc"]
                              for t in meta["turns"]))
    r.check_eq("meta tool results", meta["tool_results"], [
        {"turn": 1, "tool_use_id": "tu1", "name": "classic_planner", "is_error": False}])
    r.check_eq("meta outcome", (meta["outcome"], meta["stop_reason"], meta["transport"],
                                meta["arm"], meta["storage_cut"]),
               ("answer", "end_turn", "live", "tools", False))
    r.check("custom id format", re.fullmatch(r"[A-Za-z0-9_-]{1,64}", meta["custom_id"]) is not None)

    # Haiku: same loop, its own settings on every request
    wire = Wire(lambda q, b, n: msg([TEXT_PLAN], "end_turn", HAIKU) if has_tool_result(b)
                else msg([tool_use()], "tool_use", HAIKU))
    _o, _row, meta = await trial(wire, model=HAIKU)
    r.check_eq("haiku settings on both requests",
               [(b["thinking"], b["output_config"]) for b in wire.bodies],
               [({"type": "disabled"}, {"effort": "medium"})] * 2)

    # two tool calls in one turn -> one user message with both results; a tool that raises
    def two_calls(req, body, n):
        if has_tool_result(body):
            return msg([TEXT_PLAN], "end_turn")
        return msg([tool_use(1), tool_use(2, "validate_plan")], "tool_use")

    def raising(name, args):
        if name == "validate_plan":
            return RuntimeError("boom")
        return PLANNER_OK
    wire = Wire(two_calls)
    _o, row, meta = await trial(wire, mcp=FakeMCP(raising))
    r.check_eq("one result message, error flagged", wire.bodies[1]["messages"][2], {
        "role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu1", "content": PLANNER_OK},
            {"type": "tool_result", "tool_use_id": "tu2", "content": "Tool error: boom",
             "is_error": True}]})
    r.check_eq("tool error string in the row", row["result"]["tool_calls"][1]["result"],
               "Tool error: boom")
    r.check_eq("is_error in sidecar", [t["is_error"] for t in meta["tool_results"]],
               [False, True])


async def test_endings(r: TestResults) -> None:
    # loop exhaustion: ten round trips, then stop
    wire = Wire(lambda q, b, n: msg([tool_use(n, "validate_domain")], "tool_use"))
    outcome, row, meta = await trial(wire)
    res = row["result"]
    r.check_eq("exactly 10 requests", wire.n, 10)
    r.check_eq("loop exhausted", (outcome["kind"], res["response"], res["done_reason"],
                                  res["failure_reason"], res["success"], res["truncated"]),
               (R.LOOP_EXHAUSTED, "", "tool_calls", "loop_exhausted", False, False))
    r.check_eq("ten tool calls kept", len(res["tool_calls"]), 10)
    r.check_eq("turns", res["tokens"]["turns"], 10)

    # refusal on the first turn, and in the middle of the loop
    for label, reply, n_req in (
            ("first turn", lambda q, b, n: msg([{"type": "text", "text": "I can't."}], "refusal",
                                               stop_details={"type": "refusal",
                                                             "category": "x"}), 1),
            ("mid loop", lambda q, b, n: msg([], "refusal") if has_tool_result(b)
             else msg([tool_use()], "tool_use"), 2)):
        wire = Wire(reply)
        outcome, row, meta = await trial(wire)
        res = row["result"]
        r.check_eq(f"refusal {label}: requests", wire.n, n_req)
        r.check_eq(f"refusal {label}: exception shape",
                   (res["success"], res["tool_selected"], res["failure_reason"], res["error"],
                    res["tokens"], res["tool_calls"], res["response"], res["thinking"],
                    res["done_reason"], res["truncated"], res["infra_failure"],
                    res["response_truncated_by_storage"]),
                   (False, None, "exception", "stop_reason=refusal", {}, [], "", "", "",
                    False, False, False))
        r.check_eq(f"refusal {label}: sidecar", (meta["outcome"], meta["stop_reason"],
                                                 meta["n_turns"]), ("refusal", "refusal", n_req))
    r.check_eq("refusal: stop_details kept", meta["stop_details"], None)
    r.check_eq("refusal mid loop: the tool call stays in the sidecar",
               len(meta["tool_results"]), 1)

    # pause_turn cannot occur without server tools: an error row, counted
    wire = Wire(lambda q, b, n: msg([], "pause_turn"))
    outcome, row, meta = await trial(wire)
    r.check_eq("pause_turn", (row["result"]["failure_reason"], row["result"]["error"],
                              R.outcome_label(meta)),
               ("exception", "stop_reason=pause_turn", "pause_turn"))
    wire = Wire(lambda q, b, n: msg([], "some_new_reason"))
    outcome, row, meta = await trial(wire)
    r.check_eq("unknown stop reason", (row["result"]["error"], meta["outcome"]),
               ("stop_reason=some_new_reason", "unknown_stop"))

    # the conversation no longer fits: a recorded outcome
    wire = Wire(lambda q, b, n: api_error(400, "invalid_request_error",
                                          "prompt is too long: 1200000 tokens > 1000000 maximum")
                if has_tool_result(b) else msg([tool_use()], "tool_use"))
    outcome, row, meta = await trial(wire)
    res = row["result"]
    r.check_eq("overflow", (outcome["kind"], res["done_reason"], res["truncated"],
                            res["response"], len(res["tool_calls"]), res["tokens"]["turns"],
                            res["error"]),
               (R.OVERFLOW, "length", True, "", 1, 1, "api: prompt is too long"))
    r.check_eq("overflow row says a turn had no room", res["tokens"].get("ctx_no_room_turns"), 1)
    r.check_eq("overflow token keys", set(res["tokens"]), {
        "prompt", "completion", "turns", "total_duration_ns", "eval_duration_ns",
        "ctx_no_room_turns"})
    r.check("the frozen loader reads it as a no-room row", loader_row(row, True).no_room)
    # the same outcome when the API reports it as a stop reason
    wire = Wire(lambda q, b, n: msg([], "model_context_window_exceeded") if has_tool_result(b)
                else msg([tool_use()], "tool_use"))
    o2, row2, meta2 = await trial(wire)
    res2 = row2["result"]
    r.check_eq("window stop reason", (o2["kind"], res2["done_reason"], res2["response"],
                                      res2["tokens"].get("ctx_no_room_turns"),
                                      res2["tokens"]["turns"], meta2["stop_reason"],
                                      loader_row(row2, True).no_room),
               (R.OVERFLOW, "length", "", 1, 2, "model_context_window_exceeded", True))
    # an ordinary answer carries no such key and is not a no-room row
    wire = Wire(one_tool_then_answer)
    _o, row3, _m = await trial(wire)
    r.check("ordinary row: no ctx key, not no-room",
            "ctx_no_room_turns" not in row3["result"]["tokens"]
            and not loader_row(row3, True).no_room)
    # other wordings of the same rejection are the same outcome
    for text in ("prompt is too long: 1200000 tokens > 1000000 maximum",
                 "input length and `max_tokens` exceed context limit: 990000 + 8192 > 1000000",
                 "This request would exceed the model's context window",
                 "The conversation is too long for the context window.",
                 "Prompt too large: exceeds the maximum context length"):
        wire = Wire(lambda q, b, n, text=text: api_error(400, "invalid_request_error", text)
                    if has_tool_result(b) else msg([tool_use()], "tool_use"))
        o4, _row, _meta = await trial(wire)
        r.check_eq(f"over-length wording: {text[:40]}", o4["kind"], R.OVERFLOW)
    for text, status, want in (("thinking.type: unknown value", 400, False),
                               ("max_tokens: 9000000 is too large", 400, False),
                               ("temperature is not supported", 400, False),
                               ("prompt is too long", 429, False),
                               ("prompt is too long", 400, True)):
        class E(Exception):
            status_code = status
        r.check_eq(f"matcher: {status} {text[:30]}", AR.is_overflow_error(E(text)), want)
    r.check("overflow error kept in sidecar", "prompt is too long" in meta["overflow_error"])
    r.check_eq("overflow keeps the harness grade of the tool call",
               (res["success"], res["tool_selected"]), (True, True))

    # the answer stopped at the output cap
    wire = Wire(lambda q, b, n: msg([{"type": "text", "text": "(pick-up b)"}], "max_tokens"))
    outcome, row, meta = await trial(wire)
    r.check_eq("max_tokens", (row["result"]["done_reason"], row["result"]["truncated"]),
               ("length", True))

    # storage rule: flagged and counted, never cut silently
    long_text = "x" * 70_000
    wire = Wire(lambda q, b, n: msg([{"type": "text", "text": long_text}], "end_turn"))
    outcome, row, meta = await trial(wire)
    res = row["result"]
    r.check_eq("storage cut", (len(res["response"]), res["response_truncated_by_storage"],
                               meta["storage_cut"], meta["answer_chars"],
                               R.outcome_label(meta)), (65_536, True, True, 70_000,
                                                        "cut_by_storage"))
    r.check_eq("full answer kept in the sidecar", meta["full_answer_if_cut"], long_text)
    try:
        R.loader_check(row, True)
        r.check("the frozen loader refuses a cut row", False, "accepted")
    except RS.RefusedRow:
        r.check("the frozen loader refuses a cut row", True)

    # errors of the API
    for label, reply, exc_type in (
            ("another 400", lambda q, b, n: api_error(400, "invalid_request_error",
                                                      "thinking: unknown type"),
             R.ApparatusError),
            ("credit", lambda q, b, n: api_error(400, "invalid_request_error",
                                                 "Your credit balance is too low"), R.Halt),
            ("401", lambda q, b, n: api_error(401, "authentication_error", "no"),
             R.ApparatusError),
            ("529", lambda q, b, n: api_error(529, "overloaded_error", "busy"), R.InfraError),
            ("429", lambda q, b, n: api_error(429, "rate_limit_error", "slow"), R.InfraError)):
        wire = Wire(reply)
        try:
            await trial(wire)
            r.check(f"{label} raises", False, "no error")
        except exc_type as exc:
            r.check(f"{label} raises {exc_type.__name__}", type(exc) is exc_type
                    or exc_type is R.Halt)


async def test_loader_all_tasks(r: TestResults) -> None:
    """Every row shape passes the rerun's frozen loader (model field swapped)."""
    mcp = mcp_ok()
    answers = {"solve": TEXT_PLAN["text"], "validate_domain": "ok\nVERDICT: VALID",
               "validate_problem": "VERDICT: VALID", "validate_plan": "VERDICT: INVALID",
               "simulate": '```json\n{"trajectory": []}\n```'}
    for model in (HAIKU, SONNET):
        for task, text in answers.items():
            for stop in ("end_turn", "max_tokens", "refusal"):
                j = job(task, model, with_tools=False)
                rec = R.turn_record(1, msg([{"type": "text", "text": text}], stop, model),
                                    requested_at="a", received_at="b", request_id=None,
                                    version_sent="2023-06-01")
                row = await R.make_row(model, j, False, R.outcome_of([rec], [], []), mcp)
                res = row["result"]
                try:
                    R.loader_check(row, False)
                    ok = True
                except RS.SchemaError as exc:
                    ok = False
                    print("   ", exc)
                r.check(f"loader accepts no-tools {model} {task} {stop}", ok)
                r.check(f"no-tools fields {task} {stop}", res["tool_selected"] is None
                        and res["tool_calls"] == [] and res["model"] == model)
                if task == "simulate" and stop != "refusal":
                    r.check("simulate format_compliant is a bool",
                            isinstance(res["format_compliant"], bool))
    # the loader really does refuse the model id itself
    row = await R.make_row(SONNET, job("solve", with_tools=False), False, R.outcome_of(
        [R.turn_record(1, msg([TEXT_PLAN], "end_turn"), requested_at=None, received_at=None,
                       request_id=None, version_sent=None)], [], []), mcp)
    spec = RS.CellSpec(name="x", layer=RS.RERUN, model_tag="Qwen3_5_9B", with_tools=False,
                       prompt_style="minimal", tasks=R.TASKS, variants=R.WORDINGS, n_rows=0,
                       per_variant=0, per_task_variant={}, k_domains=0)
    try:
        RS.parse_row(row, spec, "x")
        r.check("unswapped row is refused on the model id only", False, "accepted")
    except RS.SchemaError as exc:
        r.check("unswapped row is refused on the model id only", "in cell of" in str(exc),
                str(exc))
    # a tool_use stop where no tool was offered is an error row
    rec = R.turn_record(1, msg([tool_use()], "tool_use"), requested_at=None, received_at=None,
                        request_id=None, version_sent=None)
    r.check_eq("tool_use in the no-tools arm", R.outcome_of([rec], [], [])["kind"],
               R.UNKNOWN_STOP)


async def test_live_resume(r: TestResults) -> None:
    jobs = [job("solve"), job("validate_domain"), job("validate_problem")]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "claude-sonnet-5-5_tools"
        out.mkdir()
        mcp = mcp_ok()
        mcp.tools = [{"type": "function", "function": {
            "name": "classic_planner", "description": "Plan.",
            "parameters": TOOLS[0]["input_schema"]}}]
        wire = Wire(one_tool_then_answer)
        c = wire.client()
        counts = await R.run_live_cell(c, mcp, SONNET, jobs[:2], out, concurrency=2)
        r.check_eq("first run: rows", (counts["rows"], counts["undone"], wire.n), (2, 0, 4))
        r.check_eq("tools sent are the MCP list converted", wire.bodies[0]["tools"], TOOLS)
        before = wire.n
        counts = await R.run_live_cell(c, mcp, SONNET, jobs, out, concurrency=2)
        r.check_eq("resume: only the new trial is sent", wire.n - before, 2)
        r.check_eq("resume: rows", (counts["rows"], counts["undone"]), (3, 0))
        rows, _ = R.read_jsonl(out / "trials.jsonl")
        metas, _ = R.read_jsonl(out / "trial_meta.jsonl")
        r.check_eq("no key twice", len({tuple(x["key"]) for x in rows}), 3)
        r.check_eq("a sidecar line per row", {tuple(m["key"]) for m in metas},
                   {tuple(x["key"]) for x in rows})
        r.check_eq("counts file", json.loads((out / "run_counts.json").read_text())["outcomes"],
                   {"answer": 3})
        before = wire.n
        await R.run_live_cell(c, mcp, SONNET, jobs, out)
        r.check_eq("third run sends nothing", wire.n, before)
        rep = R.pilot_check_cell(out, SONNET, "tools", 3)
        r.check_eq("plumbing check", {k: rep[k] for k in (
            "rows", "duplicate_keys", "rows_without_sidecar_line", "half_written_lines",
            "rows_the_frozen_loader_refuses", "rows_cut_by_storage", "non_empty_answers",
            "answers_counted", "api_version_sent", "request_hosts",
            "model_ids_returned", "endings",
            "requests_in_sidecar", "requests_whose_settings_differ_from_the_registered",
            "requests_with_a_sampling_field",
            "model_ids_start_with_the_requested_id_and_do_not_change",
            "thinking_blocks_returned_before_a_next_request",
            "thinking_blocks_in_the_next_request_body_byte_equal",
            "thinking_tokens", "thinking_blocks_returned", "thinking_expected_to_be_zero",
            "cache_tokens", "input_tokens", "output_tokens", "implied_usd_of_the_rows",
            "section_9_estimate_usd", "tool_calls_by_tool",
            "limit_numbers_in_over_length_errors", "passes")},
            {"rows": 3, "duplicate_keys": 0, "rows_without_sidecar_line": 0,
             "half_written_lines": 0, "rows_the_frozen_loader_refuses": 0,
             "rows_cut_by_storage": 0, "non_empty_answers": 3, "answers_counted": 3,
             "api_version_sent": ["2023-06-01"], "request_hosts": ["api.anthropic.com"],
             "model_ids_returned": [SONNET], "endings": {"answer": 3},
             "requests_in_sidecar": 6,
             "requests_whose_settings_differ_from_the_registered": 0,
             "requests_with_a_sampling_field": 0,
             "model_ids_start_with_the_requested_id_and_do_not_change": True,
             "thinking_blocks_returned_before_a_next_request": 3,
             "thinking_blocks_in_the_next_request_body_byte_equal": 3,
             "thinking_tokens": 9, "thinking_blocks_returned": 3,
             "thinking_expected_to_be_zero": False, "cache_tokens": 0,
             "input_tokens": 1500, "output_tokens": 150,
             "implied_usd_of_the_rows": round((1500 * 2.0 + 150 * 10.0) / 1e6, 4),
             "section_9_estimate_usd": [11.26, 11.26],
             "tool_calls_by_tool": {"classic_planner": {"calls": 3, "is_error": 0,
                                                        "error_results": 0}},
             "limit_numbers_in_over_length_errors": [], "passes": True})
        # the check fails on a setting that differs, a sampling field, another model's
        # id, or a note that did not go back
        good = (out / "trial_meta.jsonl").read_text()
        for label, edit in (
                ("another effort", lambda m: m["turns"][0]["request"]["output_config"]
                 .update(effort="low")),
                ("a sampling field", lambda m: m["turns"][0]["request"].update(temperature=0)),
                ("another model id", lambda m: m.update(model_ids_returned=["claude-opus-5"])),
                ("a note not passed back", lambda m: m["turns"][1]
                 .update(thinking_blocks_passed_back=0)),
                ("cache tokens", lambda m: m["turns"][0]["usage"]
                 .update(cache_read_input_tokens=5)),
                ("another host", lambda m: m["turns"][0].update(request_host="example.org")),
                ("a second model id", lambda m: m.update(
                    model_ids_returned=[SONNET, SONNET + "-20270101"]))):
            lines = [json.loads(x) for x in good.splitlines()]
            edit(lines[0])
            (out / "trial_meta.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
            r.check_eq(f"plumbing check fails on {label}",
                       R.pilot_check_cell(out, SONNET, "tools", 3)["passes"], False)
        (out / "trial_meta.jsonl").write_text(good)
        r.check("plumbing check: a dated model id passes",
                "claude-sonnet-5-5-20261001".startswith(SONNET))
        r.check("plumbing check prints no outcome field",
                not ({"success", "failure_reason", "tool_selected", "response"} & set(rep)))
        r.check_eq("a short folder fails the check",
                   R.pilot_check_cell(out, SONNET, "tools", 160)["passes"], False)
        await c.close()

        # a failure outside the model on the first turn: logged, the same turn is tried
        # again, the trial completes
        out2 = Path(td) / "second"
        out2.mkdir()
        state = {"failed": False}

        def flaky(req, body, n):
            if not state["failed"]:
                state["failed"] = True
                return api_error(529, "overloaded_error", "busy")
            return one_tool_then_answer(req, body, n)
        wire = Wire(flaky)
        c = wire.client()
        counts = await R.run_live_cell(c, mcp, SONNET, jobs[:1], out2, concurrency=1)
        att, _ = R.read_jsonl(out2 / "attempts.jsonl")
        r.check_eq("failed try logged", [(a["what"], a["turn"], a["attempt"]) for a in att],
                   [("infra", 1, 1)])
        r.check_eq("then completed", (counts["rows"], wire.n), (1, 3))
        await c.close()

        # every try fails: no row, the trial stays undone
        out3 = Path(td) / "third"
        out3.mkdir()
        wire = Wire(lambda q, b, n: api_error(500, "api_error", "down"))
        c = wire.client()
        counts = await R.run_live_cell(c, mcp, SONNET, jobs[:1], out3)
        att, _ = R.read_jsonl(out3 / "attempts.jsonl")
        r.check_eq("undone trial", (counts["rows"], counts["undone"], wire.n,
                                    [a["what"] for a in att]),
                   (0, 1, 2, ["infra", "infra", "trial_abandoned"]))
        r.check("no row file content", not (out3 / "trials.jsonl").exists())
        await c.close()

        # a request the API rejects stops the cell
        out4 = Path(td) / "fourth"
        out4.mkdir()
        wire = Wire(lambda q, b, n: api_error(400, "invalid_request_error", "bad field"))
        c = wire.client()
        try:
            await R.run_live_cell(c, mcp, SONNET, jobs, out4, concurrency=1)
            r.check("rejected request halts the cell", False, "no halt")
        except R.ApparatusError:
            r.check("rejected request halts the cell", wire.n == 1, f"{wire.n} requests")
        await c.close()


BATCH = {"id": "msgbatch_1", "type": "message_batch", "processing_status": "in_progress",
         "request_counts": {"processing": 3, "succeeded": 0, "errored": 0, "canceled": 0,
                            "expired": 0},
         "ended_at": None, "created_at": "2026-12-01T10:00:00Z",
         "expires_at": "2026-12-02T10:00:00Z", "archived_at": None,
         "cancel_initiated_at": None, "results_url": None}


async def test_batch(r: TestResults) -> None:
    jobs = [job(t, HAIKU, with_tools=False) for t in ("solve", "validate_domain", "simulate")]
    cids = [R.custom_id(R.trial_key(HAIKU, j, False)) for j in jobs]
    reqs, id_map = R.batch_requests(HAIKU, jobs)
    r.check_eq("batch request literal", reqs[0], {"custom_id": cids[0], "params": {
        "model": HAIKU, "max_tokens": 8192, "system": FORMAT_STATED_SOLVE,
        "messages": [{"role": "user", "content": user_text("solve", False)}],
        "thinking": {"type": "disabled"}, "output_config": {"effort": "medium"}}})
    r.check_eq("id map", id_map[cids[1]], [HAIKU, "validate_domain", "blocksworld", "p01", "",
                                           11, False, "off", "all", "minimal"])
    r.check("custom ids", all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", c) for c in cids)
            and len(set(cids)) == 3)
    r.check_eq("custom id is stable", R.custom_id(R.trial_key(HAIKU, jobs[0], False)), cids[0])

    state = {"ended": False, "sent": []}
    results = "".join(json.dumps(x) + "\n" for x in (
        {"custom_id": cids[1], "result": {"type": "succeeded", "message": msg(
            [{"type": "text", "text": "fine\nVERDICT: VALID"}], "end_turn", HAIKU + "-20261001",
            in_tok=900, out_tok=40)}},
        {"custom_id": cids[0], "result": {"type": "errored", "error": {
            "type": "error", "error": {"type": "api_error", "message": "internal"}}}},
        {"custom_id": cids[2], "result": {"type": "succeeded", "message": msg(
            [], "refusal", HAIKU + "-20261001")}}))

    def reply(req, body, n):
        path = req.url.path
        if req.method == "POST" and path == "/v1/messages/batches":
            state["sent"].append(body)
            return dict(BATCH, id=f"msgbatch_{len(state['sent'])}")
        if req.method == "GET" and path.endswith("/results"):
            return httpx.Response(200, content=results.encode(),
                                  headers={"content-type": "application/x-jsonl"})
        if req.method == "GET":
            if not state["ended"]:
                return dict(BATCH)
            return dict(BATCH, processing_status="ended", ended_at="2026-12-01T11:00:00Z",
                        request_counts={"processing": 0, "succeeded": 2, "errored": 1,
                                        "canceled": 0, "expired": 0},
                        results_url="https://api.anthropic.com/v1/messages/batches/msgbatch_1/results")
        return 404, {}

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        wire = Wire(reply)
        c = wire.client()
        entry = await R.batch_submit(c, HAIKU, jobs, out)
        r.check_eq("batch body", state["sent"][0], {"requests": reqs})
        r.check_eq("batch id stored", (entry["batch_id"], entry["anthropic_version_sent"],
                                       entry["n_requests"]), ("msgbatch_1", "2023-06-01", 3))
        r.check_eq("batches.json", [(b["batch_id"], b["fetched"])
                                    for b in R.read_batches(out)], [("msgbatch_1", False)])
        r.check_eq("request file", len((out / "batch_requests_1.jsonl").read_text()
                                       .splitlines()), 3)
        r.check_eq("map file", json.loads((out / "custom_id_map.json").read_text()), id_map)
        try:
            await R.batch_submit(c, HAIKU, jobs, out)
            r.check("second submit refuses", False, "sent again")
        except R.Halt:
            r.check("second submit refuses, nothing sent", len(state["sent"]) == 1)
        r.check_eq("not ended: nothing to grade", await R.batch_poll(c, out, wait=False), None)
        state["ended"] = True
        entry = await R.batch_poll(c, out, wait=False)
        r.check_eq("raw results stored", len((out / "batch_results_1.jsonl").read_text()
                                             .splitlines()), 3)
        n_before = wire.n
        entry2 = await R.batch_poll(c, out, wait=False)
        r.check_eq("raw results are not fetched twice", (wire.n, entry2["batch_id"]),
                   (n_before, "msgbatch_1"))
        counts = await R.batch_grade(HAIKU, jobs, out, mcp_ok(), entry)
        rows, _ = R.read_jsonl(out / "trials.jsonl")
        metas, _ = R.read_jsonl(out / "trial_meta.jsonl")
        att, _ = R.read_jsonl(out / "attempts.jsonl")
        r.check_eq("rows: the answered one and the refusal",
                   sorted((x["result"]["task"], x["result"]["failure_reason"]) for x in rows),
                   [("simulate", "exception"), ("validate_domain", "ok")])
        r.check_eq("counts", (counts["rows"], counts["undone"], counts["outcomes"]),
                   (2, 1, {"answer": 1, "refusal": 1}))
        r.check_eq("errored item logged, left undone",
                   [(a["what"], a["key"][1], a["batch_id"]) for a in att],
                   [("batch_errored", "solve", "msgbatch_1")])
        m = next(x for x in metas if x["outcome"] == "answer")
        r.check_eq("batch sidecar", (m["transport"], m["batch_id"], m["model_ids_returned"],
                                     m["anthropic_version_sent"], m["batch_ended_at"],
                                     m["turns"][0]["usage"]["input_tokens"]),
                   ("batch", "msgbatch_1", [HAIKU + "-20261001"], ["2023-06-01"],
                    "2026-12-01T11:00:00+00:00", 900))
        r.check_eq("batch sidecar: settings of the request sent", m["turns"][0]["request"], {
            "model": HAIKU, "max_tokens": 6144, "thinking": {"type": "disabled"},
            "output_config": {"effort": "medium"}, "has_tools": False, "n_messages": 1,
            "param_keys": ["max_tokens", "messages", "model", "output_config", "system",
                           "thinking"]})
        rep = R.pilot_check_cell(out, HAIKU, "no-tools", 2)
        r.check_eq("batch plumbing check", (rep["passes"], rep["requests_in_sidecar"],
                                            rep["model_ids_start_with_the_requested_id_and_do_not_change"],
                                            rep["stored_batch_requests_as_registered"],
                                            rep["endings"]),
                   (True, 2, True, True, {"answer": 1, "refusal": 1}))
        row = next(x for x in rows if x["result"]["task"] == "validate_domain")["result"]
        r.check_eq("batch row", (row["model"], row["tokens"]["prompt"], row["tokens"]["turns"],
                                 row["done_reason"], row["duration_s"]),
                   (HAIKU, 900, 1, "stop", 0.0))
        r.check_eq("batch marked fetched", R.read_batches(out)[0]["fetched"], True)
        # grading again from the stored raw results writes nothing twice
        await R.batch_grade(HAIKU, jobs, out, mcp_ok(), entry)
        r.check_eq("grading again adds no row", len(R.read_jsonl(out / "trials.jsonl")[0]), 2)
        # the next submit sends only the undone trial
        await R.batch_submit(c, HAIKU, jobs, out)
        r.check_eq("second batch holds the errored trial only",
                   [q["custom_id"] for q in state["sent"][1]["requests"]], [cids[0]])
        await c.close()

    # a request the API calls invalid stops the arm (sending it again would fail again)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        (out / "batch_results_1.jsonl").write_text(json.dumps({
            "custom_id": cids[0], "result": {"type": "errored", "error": {
                "type": "error", "error": {"type": "invalid_request_error",
                                           "message": "thinking.type: bad"}}}}) + "\n")
        R.write_batches(out, [{"n": 1, "batch_id": "msgbatch_9", "fetched": False}])
        try:
            await R.batch_grade(HAIKU, jobs, out, mcp_ok(), R.read_batches(out)[0])
            r.check("an invalid batch request halts", False, "no halt")
        except R.ApparatusError as exc:
            r.check("an invalid batch request halts", "thinking.type" in str(exc))


def test_marketplace(r: TestResults) -> None:
    def refused(label, path):
        try:
            R.check_marketplace(path)
            r.check(label, False, "accepted")
        except R.MarketplaceRefused as exc:
            r.check(label, True)
            return str(exc)

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "mk"
        (repo / "plugins" / "pddl-validator").mkdir(parents=True)
        (repo / "plugins" / "pddl-validator" / "server.py").write_text("x = 1\n")
        (repo / ".gitignore").write_text(".venv\n")
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", str(repo), *cmd], check=True, env=env,
                           capture_output=True)
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        msg_ = refused("another commit is refused", repo)
        r.check("the refusal names the registered commit", "5e4f9c0" in (msg_ or ""))
        refused("a folder without plugins/ is refused", td)
        saved = R.MARKETPLACE_COMMIT
        R.MARKETPLACE_COMMIT = head[:7]
        try:
            msg_ = refused("no validator environment is refused", repo)
            py = repo / "plugins" / "pddl-validator" / ".venv" / "bin" / "python3"
            py.parent.mkdir(parents=True)

            def fake(version):
                py.write_text(f"#!/bin/sh\necho {version}\n")
                py.chmod(py.stat().st_mode | stat.S_IEXEC)
            fake("0.1.6")
            msg_ = refused("validator 0.1.6 is refused", repo)
            r.check("the refusal names both releases", "0.1.6" in msg_ and "0.1.5" in msg_)
            fake("0.1.5")
            got = R.check_marketplace(repo)
            r.check_eq("the registered checkout is accepted",
                       (got["commit"], got["pyvalidator"]), (head, "0.1.5"))
            r.check_eq("installed packages listed per plugin environment",
                       got["freeze"], {"pddl-validator": ["0.1.5"]})
            (repo / "plugins" / "pddl-validator" / "server.py").write_text("x = 2\n")
            refused("an edited plugin file is refused", repo)
        finally:
            R.MARKETPLACE_COMMIT = saved


def test_manifest_and_cache(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "cell"
        kw = dict(sdk_version="0.109.2", gt_cache=Path("x"), ground_truth={"a": 1},
                  marketplace={"commit": "5e4f9c0abc", "pyvalidator": "0.1.5",
                               "freeze": {"pddl-validator": ["pddl-pyvalidator==0.1.5"]}},
                  tools_digest="d")
        m = R.build_run_manifest(SONNET, "tools", pilot=False, **kw)
        r.check_eq("manifest lists the tool environments", m["tools_env"],
                   {"pddl-validator": ["pddl-pyvalidator==0.1.5"]})
        r.check_eq("manifest fields", (m["backend"], m["think"], m["effort"], m["temperature"],
                                       m["max_iterations"], m["snapshot_len"],
                                       m["prompt_variants"], m["tools_commit"], m["pilot"]),
                   ("anthropic-live", "between_tools", "high", "not sent (provider default)",
                    10, 65_536, [11, 12, 13], "5e4f9c0abc", False))
        RM.ensure_manifest(out, m)
        RM.ensure_manifest(out, R.build_run_manifest(SONNET, "tools", pilot=False, **kw))
        for label, other in (
                ("pilot", R.build_run_manifest(SONNET, "tools", pilot=True, **kw)),
                ("model", R.build_run_manifest(HAIKU, "tools", pilot=False, **kw)),
                ("tools digest", R.build_run_manifest(SONNET, "tools", pilot=False,
                                                      **{**kw, "tools_digest": "e"})),
                ("package list", R.build_run_manifest(SONNET, "tools", pilot=False, **{
                    **kw, "marketplace": {"commit": "5e4f9c0abc", "pyvalidator": "0.1.5",
                                          "freeze": {"pddl-validator": ["x==2"]}}})),
                ("SDK", R.build_run_manifest(SONNET, "tools", pilot=False,
                                             **{**kw, "sdk_version": "2.0.0"}))):
            try:
                RM.ensure_manifest(out, other)
                r.check(f"resume under another {label} is refused", False, "accepted")
            except RM.ManifestError:
                r.check(f"resume under another {label} is refused", True)
        nt = R.build_run_manifest(HAIKU, "no-tools", pilot=True, **kw)
        r.check_eq("no-tools manifest", (nt["backend"], nt["think"], nt["effort"],
                                         nt["max_iterations"], nt["prompt_variants"],
                                         nt["tools_commit"]),
                   ("anthropic-batch", "disabled", "medium", 1, [11], None))
        bad = Path(td) / "gt.json"
        bad.write_text("{}")
        try:
            R.load_gt_cache(bad)
            r.check("another ground-truth file is refused", False, "accepted")
        except R.Halt:
            r.check("another ground-truth file is refused", True)
    import argparse
    for out_name, pilot in (("frontier55", True), ("frontier55-pilot", False)):
        try:
            R._prepare(argparse.Namespace(model=HAIKU, out=f"/nonexistent/{out_name}",
                                          pilot=pilot, gt_cache="/nonexistent/gt.json",
                                          marketplace_path=None), "no-tools", False)
            r.check(f"folder rule (pilot={pilot}, {out_name})", False, "accepted")
        except R.Halt as exc:
            r.check(f"folder rule (pilot={pilot}, {out_name})", "pilot" in str(exc), str(exc))


def gt_cache_path() -> Path | None:
    """The pinned cache: in this checkout, or in the main checkout of a worktree."""
    cands = [REPO_ROOT / R.GT_CACHE_REL]
    try:
        common = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True).stdout.strip()
        if common:
            cands.append((Path(common) if Path(common).is_absolute()
                          else REPO_ROOT / common).resolve().parent / R.GT_CACHE_REL)
    except OSError:
        pass
    return next((p for p in cands if p.exists()), None)


def test_grid(r: TestResults) -> None:
    path = gt_cache_path()
    if path is None:
        print("  SKIPPED grid counts: results/derived/gt_cache.json is not on this machine")
        return
    from pddl_eval.domains import load_domains
    gt = R.load_gt_cache(path)
    domains = load_domains(REPO_ROOT / "domains")
    rep = R.dry_run(R.MODELS, domains, gt, pilot=False, tools=TOOLS)
    r.check_eq("full run: 4,560 x 2 arms x 2 models", rep["total_trials"], 18_240)
    r.check_eq("four cells", [(c["model"], c["arm"], c["n"]) for c in rep["cells"]],
               [(HAIKU, "no-tools", 4560), (HAIKU, "tools", 4560),
                (SONNET, "no-tools", 4560), (SONNET, "tools", 4560)])
    for c in rep["cells"]:
        r.check_eq(f"per task {c['model']} {c['arm']}", c["per_task"],
                   {"solve": 300, "validate_domain": 360, "validate_problem": 600,
                    "validate_plan": 3000, "simulate": 300})
    r.check_eq("tools digest reported", rep["tools_sha256"], R.tools_sha256(TOOLS))
    pil = R.dry_run(R.MODELS, domains, gt, pilot=True, tools=None)
    r.check_eq("pilot: 160 x 2 arms x 2 models", pil["total_trials"], 640)
    for c in pil["cells"]:
        r.check_eq(f"pilot per task {c['model']} {c['arm']}", c["per_task"],
                   {"solve": 20, "validate_domain": 40, "validate_problem": 40,
                    "validate_plan": 40, "simulate": 20})
    nt = R.build_grid(SONNET, "no-tools", domains, gt)
    wt = R.build_grid(SONNET, "tools", domains, gt)
    r.check_eq("wordings", ({j[R.J_PV] for j in nt}, {j[R.J_PV] for j in wt}),
               ({11, 12, 13}, {11, 12, 13}))
    r.check_eq("20 domains, 100 problems on solve",
               (len({j[R.J_DNAME] for j in nt}),
                len({(j[R.J_DNAME], j[R.J_PNAME]) for j in nt if j[R.J_TASK] == "solve"})),
               (20, 100))
    strip = lambda key: tuple(key[1:6])  # noqa: E731
    r.check_eq("the two arms hold the same trials",
               {strip(R.trial_key(SONNET, j, False)) for j in nt},
               {strip(R.trial_key(SONNET, j, True)) for j in wt})
    ids = [R.custom_id(R.trial_key(m, j, False)) for m in R.MODELS
           for j in R.build_grid(m, "no-tools", domains, gt)]
    r.check_eq("custom ids unique over both batches", len(set(ids)), 9_120)
    pj = R.build_grid(HAIKU, "tools", domains, gt, pilot=True)
    first = R.first_problems(domains)
    r.check_eq("first problems", set(first.values()), {"p01"})
    r.check("pilot: wording v11 only", all(j[R.J_PV] == 11 for j in pj))
    from collections import Counter
    per_domain = Counter((j[R.J_DNAME], j[R.J_TASK], j[R.J_PNAME], j[R.J_PLAN]) for j in pj)
    want_one = {("solve", "p01", ""), ("simulate", "p01", ""), ("validate_problem", "p01", ""),
                ("validate_problem", "n01", ""), ("validate_domain", "p01", ""),
                ("validate_domain", "domain_neg", ""), ("validate_plan", "p01", "v1"),
                ("validate_plan", "p01", "b1")}
    r.check("pilot: the same eight trials in each of the 20 domains",
            all({k[1:] for k in per_domain if k[0] == d} == want_one for d in domains)
            and set(per_domain.values()) == {1} and len(domains) == 20)
    full_keys = {tuple(R.trial_key(HAIKU, j, True)) for j in R.build_grid(HAIKU, "tools",
                                                                         domains, gt)}
    r.check("pilot trials are trials of the full list (the same prompts)",
            {tuple(R.trial_key(HAIKU, j, True)) for j in pj} <= full_keys)
    pn = R.build_grid(HAIKU, "no-tools", domains, gt, pilot=True)
    r.check_eq("pilot: both arms hold the same trials",
               {strip(R.trial_key(HAIKU, j, False)) for j in pn},
               {strip(R.trial_key(HAIKU, j, True)) for j in pj})
    sim = next(j for j in nt if j[R.J_TASK] == "simulate")
    p = R.first_request(SONNET, sim, False, None)
    r.check("the plan in the simulate prompt is the cached plan",
            all(step in p["messages"][0]["content"] for step in sim[R.J_GT]["plan"][:3]))


def test_cost(r: TestResults) -> None:
    row = {"in": 1_000_000, "out": 100_000, "turns": 2}
    s = COST.price_trial(SONNET, "tools", "solve", row, 1.3)
    r.check_eq("sonnet tools: list price, output capped at 2 x 8,192",
               (round(s["usd"], 4), s["out"]), (round(1.3 * 2.0 + 16_384 * 10 / 1e6, 4), 16_384))
    s = COST.price_trial(SONNET, "no-tools", "simulate", {"in": 1000, "out": 1000, "turns": 1}, 1.3)
    r.check_eq("sonnet no-tools: half price", round(s["usd"], 6),
               round((1300 * 2.0 + 1300 * 10.0) / 1e6 / 2, 6))
    h = COST.price_trial(HAIKU, "tools", "simulate", {"in": 50_000, "out": 1000, "turns": 2}, 1.0)
    r.check_eq("haiku base rate", (h["long"], round(h["usd"], 6)),
               (False, round((50_000 * 0.10 + 1000 * 0.50) / 1e6, 6)))
    h = COST.price_trial(HAIKU, "tools", "simulate", {"in": 150_000, "out": 1000, "turns": 2}, 1.0)
    r.check_eq("haiku higher rate above 100,000 prompt tokens", (h["long"], round(h["usd"], 6)),
               (True, round((150_000 * 0.50 + 1000 * 2.50) / 1e6, 6)))
    rows = {"no-tools": [{"task": "solve", "problem": "p01", "in": 1000, "out": 100, "turns": 1},
                         {"task": "solve", "problem": "p02", "in": 1000, "out": 100, "turns": 1}],
            "tools": []}
    pick = lambda t, p, lab="": COST.in_pilot({"task": t, "problem": p, "plan_label": lab})  # noqa: E731
    r.check_eq("pilot list of the estimate",
               [pick("solve", "p01"), pick("solve", "p02"), pick("validate_problem", "n01"),
                pick("validate_problem", "n02"), pick("validate_domain", "domain_neg"),
                pick("validate_domain", "p02"), pick("validate_plan", "p01", "v1"),
                pick("validate_plan", "p01", "b1"), pick("validate_plan", "p01", "v2"),
                pick("validate_plan", "p02", "v1")],
               [True, False, True, False, True, False, True, True, False, False])
    full = COST.estimate(rows, SONNET, pilot=False)
    pil = COST.estimate(rows, SONNET, pilot=True)
    r.check_eq("full run triples the v11 rows; the pilot keeps p01",
               (full[0]["trials"], pil[0]["trials"]), (6, 1))
    r.check("render", "both models" in COST.render({"x": full}))


def live_mcp() -> FakeMCP:
    mcp = mcp_ok()
    mcp.tools = [{"type": "function", "function": {
        "name": "classic_planner", "description": "Plan.",
        "parameters": TOOLS[0]["input_schema"]}}]
    return mcp


async def test_money_paths(r: TestResults) -> None:
    # prices
    r.check_eq("sonnet live price", AR.usage_usd(SONNET, {"input_tokens": 1_000_000,
                                                          "output_tokens": 100_000}, batch=False),
               2.0 + 1.0)
    r.check_eq("sonnet batch price", AR.usage_usd(SONNET, {"input_tokens": 1_000_000,
                                                           "output_tokens": 100_000}, batch=True),
               1.5)
    r.check_eq("haiku base", round(AR.usage_usd(HAIKU, {"input_tokens": 100_000,
                                                        "output_tokens": 1000}, batch=False), 6),
               round((100_000 * 0.10 + 1000 * 0.50) / 1e6, 6))
    r.check_eq("haiku above 100,000 prompt tokens",
               round(AR.usage_usd(HAIKU, {"input_tokens": 100_001, "output_tokens": 1000},
                                  batch=False), 6),
               round((100_001 * 0.50 + 1000 * 2.50) / 1e6, 6))
    r.check_eq("cache tokens are priced",
               round(AR.usage_usd(SONNET, {"input_tokens": 0, "output_tokens": 0,
                                           "cache_creation_input_tokens": 1_000_000,
                                           "cache_read_input_tokens": 1_000_000}, batch=False), 6),
               round(2.0 * 1.25 + 2.0 * 0.10, 6))
    r.check_eq("thinking and cache token scans",
               (AR.thinking_tokens_of({"output_tokens": 9, "output_tokens_details": {
                   "thinking_tokens": 4, "reasoning_tokens": 1}}),
                AR.cache_tokens_of({"cache_read_input_tokens": 2,
                                    "cache_creation_input_tokens": 3, "input_tokens": 7})),
               (5, 5))

    jobs = [job("solve"), job("validate_domain"), job("validate_problem")]
    mcp = live_mcp()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "frontier55-pilot"
        out = R.cell_dir(root, SONNET, "tools")
        out.mkdir(parents=True)
        # the ledger: every response adds its usage; the total is written to the run folder
        wire = Wire(one_tool_then_answer)
        c = wire.client()
        spend = R.Spend(root, SONNET, 1.0)
        await R.run_live_cell(c, mcp, SONNET, jobs[:1], out, spend=spend)
        one_trial = (100 * 2.0 + 20 * 10.0 + 400 * 2.0 + 30 * 10.0) / 1e6
        ledger, _ = R.read_jsonl(out / "spend.jsonl")
        total = json.loads((root / f"spend_{SONNET}.json").read_text())
        r.check_eq("ledger: one line per response", [x["what"] for x in ledger],
                   ["live_turn", "live_turn"])
        r.check_eq("ledger total", (round(spend.total, 8), total["total_usd"], total["max_usd"]),
                   (round(one_trial, 8), round(one_trial, 6), 1.0))
        r.check_eq("a new ledger object reads the total back",
                   round(R.Spend(root, SONNET, 1.0).total, 8), round(one_trial, 8))
        # the stop: the cell halts once the model's total is above --max-usd
        spend = R.Spend(root, SONNET, one_trial * 1.2)
        before = wire.n
        try:
            await R.run_live_cell(c, mcp, SONNET, jobs, out, concurrency=1, spend=spend)
            r.check("spend stop halts the cell", False, "no halt")
        except R.SpendStop:
            r.check("spend stop halts the cell", True)
        r.check_eq("spend stop: one more response was paid for, then nothing",
                   (wire.n - before, len(R.read_jsonl(out / "trials.jsonl")[0])), (1, 1))
        try:
            await R.run_live_cell(c, mcp, SONNET, jobs, out, spend=spend)
            r.check("over the stop: nothing is sent at all", False, "ran")
        except R.SpendStop:
            r.check("over the stop: nothing is sent at all", wire.n - before == 1)
        await c.close()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "frontier55-pilot"
        out = R.cell_dir(root, SONNET, "tools")
        out.mkdir(parents=True)
        # a failure in the middle of a trial: the SAME conversation goes on from the
        # failed turn; turn 1 is not asked again
        state = {"fail": 1}

        def flaky_turn2(req, body, n):
            if has_tool_result(body) and state["fail"] > 0:
                state["fail"] -= 1
                return api_error(529, "overloaded_error", "busy")
            return one_tool_then_answer(req, body, n)
        wire = Wire(flaky_turn2)
        c = wire.client()
        spend = R.Spend(root, SONNET, 5.0)
        counts = await R.run_live_cell(c, mcp, SONNET, jobs[:1], out, spend=spend)
        att, _ = R.read_jsonl(out / "attempts.jsonl")
        r.check_eq("mid-trial failure: three requests, turn 1 asked once", wire.n, 3)
        r.check_eq("the failed turn is sent again unchanged", wire.bodies[1], wire.bodies[2])
        r.check_eq("the try is logged with its turn", [(a["what"], a["turn"], a["attempt"])
                                                       for a in att], [("infra", 2, 1)])
        metas, _ = R.read_jsonl(out / "trial_meta.jsonl")
        r.check_eq("the trial completed with two turns", (counts["rows"], metas[0]["n_turns"]),
                   (1, 2))
        # both tries of turn 2 fail: the trial is abandoned, the paid turn is recorded
        state["fail"] = 2
        before = wire.n
        counts = await R.run_live_cell(c, mcp, SONNET, jobs[:2], out, spend=spend)
        att, _ = R.read_jsonl(out / "attempts.jsonl")
        ab = [a for a in att if a["what"] == "trial_abandoned"]
        r.check_eq("abandoned after two tries of the turn", (wire.n - before, counts["rows"],
                                                             counts["undone"], len(ab)),
                   (3, 1, 1, 1))
        r.check_eq("the discarded turn's usage is written down",
                   (ab[0]["discarded_turns"], ab[0]["discarded_usage"]),
                   (1, [{"input_tokens": 100, "output_tokens": 20,
                         "output_tokens_details": {"thinking_tokens": 3}}]))
        ledger, _ = R.read_jsonl(out / "spend.jsonl")
        r.check_eq("and it is in the spend ledger (3 paid responses so far)", len(ledger), 3)
        # the next run starts that trial again from its first turn
        before = wire.n
        counts = await R.run_live_cell(c, mcp, SONNET, jobs[:2], out, spend=spend)
        r.check_eq("restart from turn 1", (wire.n - before, counts["rows"],
                                           wire.bodies[before]["messages"].__len__()), (2, 2, 1))
        await c.close()

        # seven trials in a row that cannot be completed stop the arm
        out7 = Path(td) / "seven"
        out7.mkdir()
        many = [job("solve", pv=pv) for pv in (11, 12, 13)] + \
               [job("validate_domain", pv=pv) for pv in (11, 12, 13)] + \
               [job("validate_problem", pv=pv) for pv in (11, 12, 13)]
        wire = Wire(lambda q, b, n: api_error(503, "api_error", "down"))
        c = wire.client()
        try:
            await R.run_live_cell(c, mcp, SONNET, many, out7, concurrency=1)
            r.check("seven in a row stop the arm", False, "no halt")
        except R.Halt as exc:
            r.check("seven in a row stop the arm", "7 trials in a row" in str(exc), str(exc))
        r.check_eq("seven trials, two tries each, then nothing", wire.n, 14)
        await c.close()

        # the first request of a trial is rejected as too long: a setup error, the cell halts
        out8 = Path(td) / "first"
        out8.mkdir()
        wire = Wire(lambda q, b, n: api_error(400, "invalid_request_error",
                                              "prompt is too long: 2000000 > 1000000"))
        c = wire.client()
        try:
            await R.run_live_cell(c, mcp, SONNET, jobs, out8, concurrency=1)
            r.check("over-length first request halts the cell", False, "no halt")
        except R.ApparatusError as exc:
            r.check("over-length first request halts the cell",
                    wire.n == 1 and not (out8 / "trials.jsonl").exists(), str(exc))
        await c.close()

        # the model id the provider returns changes within a folder: halt, no row
        out9 = Path(td) / "ids"
        out9.mkdir()

        def two_ids(req, body, n):
            model = SONNET if n <= 2 else SONNET + "-20270101"
            m = one_tool_then_answer(req, body, n)
            return dict(m, model=model)
        wire = Wire(two_ids)
        c = wire.client()
        try:
            await R.run_live_cell(c, mcp, SONNET, jobs, out9, concurrency=1)
            r.check("a changed model id halts the cell", False, "no halt")
        except R.Halt as exc:
            r.check("a changed model id halts the cell", "changed" in str(exc), str(exc))
        att, _ = R.read_jsonl(out9 / "attempts.jsonl")
        r.check_eq("changed id: one row kept, the new one not written, logged",
                   (len(R.read_jsonl(out9 / "trials.jsonl")[0]), [a["what"] for a in att]),
                   (1, ["model_id_changed"]))
        await c.close()

    # the live client
    saved = {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL")}
    try:
        os.environ["ANTHROPIC_API_KEY"] = "not-a-key"
        os.environ.pop("ANTHROPIC_BASE_URL", None)
        c = R.make_client()
        r.check_eq("client: one SDK retry, 600 s, the provider's address",
                   (c.max_retries, float(c.timeout), str(c.base_url).rstrip("/")),
                   (1, 600.0, "https://api.anthropic.com"))
        await c.close()
        os.environ["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com/"
        await R.make_client().close()
        r.check("the provider's own address in the environment is accepted", True)
        os.environ["ANTHROPIC_BASE_URL"] = "http://localhost:8000"
        try:
            R.make_client()
            r.check("another base URL in the environment is refused", False, "accepted")
        except R.Halt:
            r.check("another base URL in the environment is refused", True)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    r.check_eq("turn tries", (R.TURN_ATTEMPTS, R.CLIENT_MAX_RETRIES, R.CLIENT_TIMEOUT_S),
               (2, 1, 600.0))


async def test_batch_send_and_recover(r: TestResults) -> None:
    jobs = [job(t, HAIKU, with_tools=False) for t in ("solve", "validate_domain", "simulate")]
    cids = [R.custom_id(R.trial_key(HAIKU, j, False)) for j in jobs]

    def listing(*batches):
        return {"data": list(batches), "has_more": False,
                "first_id": batches[0]["id"] if batches else None,
                "last_id": batches[-1]["id"] if batches else None}

    for label, reply, exc_type, entry_left, posts in (
            ("connection lost", lambda q, b, n: (_ for _ in ()).throw(
                httpx.ConnectError("reset")), R.Halt, True, 1),
            ("500", lambda q, b, n: api_error(500, "api_error", "boom"), R.Halt, True, 1),
            ("400", lambda q, b, n: api_error(400, "invalid_request_error", "bad"),
             R.ApparatusError, False, 1),
            ("429", lambda q, b, n: api_error(429, "rate_limit_error", "slow"), R.Halt,
             False, 1)):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            wire = Wire(reply)
            c = wire.client(max_retries=3)       # the send itself must not retry
            try:
                await R.batch_submit(c, HAIKU, jobs, out)
                r.check(f"send fails ({label})", False, "no error")
            except exc_type as exc:
                r.check(f"send fails ({label}): {exc_type.__name__}",
                        type(exc) is exc_type, type(exc).__name__)
            left = R.read_batches(out)
            r.check_eq(f"send fails ({label}): tried once, entry kept={entry_left}",
                       (wire.n, len(left), bool(left and left[0].get("send_error")),
                        bool(left and left[0]["batch_id"])), (posts, int(entry_left),
                                                              entry_left, False))
            await c.close()

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        wire = Wire(lambda q, b, n: api_error(500, "api_error", "boom"))
        c = wire.client()
        try:
            await R.batch_submit(c, HAIKU, jobs, out)
        except R.Halt:
            pass
        await c.close()
        started = R.read_batches(out)[0]["send_started_at_utc"]
        try:
            await R.batch_submit(Wire(lambda q, b, n: dict(BATCH)).client(), HAIKU, jobs, out)
            r.check("no second send while the first is unresolved", False, "sent")
        except R.Halt as exc:
            r.check("no second send while the first is unresolved", "batch-recover" in str(exc))
        try:
            await R.batch_poll(Wire(lambda q, b, n: dict(BATCH)).client(), out, wait=False)
            r.check("fetch asks for recover", False, "polled")
        except R.Halt as exc:
            r.check("fetch asks for recover", "batch-recover" in str(exc))
        mine = dict(BATCH, id="msgbatch_mine", created_at=started.replace("Z", "+00:00"))
        other = dict(BATCH, id="msgbatch_other", created_at=started.replace("Z", "+00:00"),
                     request_counts=dict(BATCH["request_counts"], processing=77))
        old = dict(BATCH, id="msgbatch_old", created_at="2026-01-01T00:00:00+00:00")

        # nothing matches: nothing changes, unless --drop
        wire = Wire(lambda q, b, n: listing(other, old))
        c = wire.client()
        rep = await R.batch_recover(c, out)
        r.check_eq("recover: no match, nothing changed",
                   (rep["matches"], len(R.read_batches(out)), wire.paths),
                   ([], 1, ["GET /v1/messages/batches"]))
        # two match: nothing changes
        rep = await R.batch_recover(Wire(lambda q, b, n: listing(
            mine, dict(mine, id="msgbatch_twin"))).client(), out)
        r.check_eq("recover: two matches, nothing changed",
                   (len(rep["matches"]), R.read_batches(out)[0]["batch_id"]), (2, None))
        # one matches by time and request count: its id is written
        rep = await R.batch_recover(Wire(lambda q, b, n: listing(other, mine, old)).client(), out)
        r.check_eq("recover: the id is written",
                   (rep["action"], R.read_batches(out)[0]["batch_id"],
                    [m["batch_id"] for m in rep["matches"]]),
                   ("id written", "msgbatch_mine", ["msgbatch_mine"]))
        try:
            await R.batch_recover(c, out)
            r.check("recover: nothing left to recover", False, "ran")
        except R.Halt:
            r.check("recover: nothing left to recover", True)
        await c.close()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        try:
            await R.batch_submit(Wire(lambda q, b, n: api_error(500, "api_error", "x")).client(),
                                 HAIKU, jobs, out)
        except R.Halt:
            pass
        rep = await R.batch_recover(Wire(lambda q, b, n: listing()).client(), out, drop=True)
        r.check_eq("recover --drop removes the entry when no batch exists",
                   (R.read_batches(out), "removed" in rep["action"]), ([], True))

    # the size limits
    saved = R.BATCH_MAX_REQUESTS
    R.BATCH_MAX_REQUESTS = 2
    try:
        with tempfile.TemporaryDirectory() as td:
            wire = Wire(lambda q, b, n: dict(BATCH))
            try:
                await R.batch_submit(wire.client(), HAIKU, jobs, Path(td))
                r.check("a batch over the limit is not sent", False, "sent")
            except R.ApparatusError:
                r.check("a batch over the limit is not sent",
                        wire.n == 0 and R.read_batches(Path(td)) == [])
    finally:
        R.BATCH_MAX_REQUESTS = saved

    # canceled and expired items, batch spend, a changed model id
    def raw_line(cid, result):
        return json.dumps({"custom_id": cid, "result": result}) + "\n"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "frontier55-pilot"
        out = R.cell_dir(root, HAIKU, "no-tools")
        out.mkdir(parents=True)
        ok = msg([{"type": "text", "text": "VERDICT: VALID"}], "end_turn", HAIKU,
                 in_tok=1_000_000, out_tok=100_000)
        (out / "batch_requests_1.jsonl").write_text("".join(
            json.dumps(q) + "\n" for q in R.batch_requests(HAIKU, jobs)[0]))
        (out / "batch_results_1.jsonl").write_text(
            raw_line(cids[1], {"type": "succeeded", "message": ok})
            + raw_line(cids[0], {"type": "canceled"})
            + raw_line(cids[2], {"type": "expired"}))
        R.write_batches(out, [{"n": 1, "batch_id": "msgbatch_1", "fetched": False,
                               "n_requests": 3}])
        spend = R.Spend(root, HAIKU, 100.0)
        entry = await R.batch_poll(None, out, wait=False, spend=spend)
        r.check_eq("batch spend: half price, the higher Haiku rate above 100,000 tokens",
                   round(spend.total, 6), round((1_000_000 * 0.50 + 100_000 * 2.50) / 1e6 / 2, 6))
        await R.batch_poll(None, out, wait=False, spend=spend)
        r.check_eq("batch spend is recorded once", len(R.read_jsonl(out / "spend.jsonl")[0]), 1)
        counts = await R.batch_grade(HAIKU, jobs, out, mcp_ok(), entry)
        att, _ = R.read_jsonl(out / "attempts.jsonl")
        r.check_eq("canceled and expired items are logged and left undone",
                   (counts["rows"], counts["undone"], sorted(a["what"] for a in att)),
                   (1, 2, ["batch_canceled", "batch_expired"]))
        # a second batch that answers as another model: no row of it is written
        (out / "batch_requests_2.jsonl").write_text((out / "batch_requests_1.jsonl").read_text())
        (out / "batch_results_2.jsonl").write_text(raw_line(cids[0], {
            "type": "succeeded", "message": dict(ok, model=HAIKU + "-20270101")}))
        try:
            await R.batch_grade(HAIKU, jobs, out, mcp_ok(), {"n": 2, "batch_id": "msgbatch_2"})
            r.check("a changed model id halts the batch arm", False, "graded")
        except R.Halt as exc:
            r.check("a changed model id halts the batch arm",
                    "changed" in str(exc) and len(R.read_jsonl(out / "trials.jsonl")[0]) == 1)


async def test_more_checks(r: TestResults) -> None:
    # the note check reads the request body: byte-equal JSON or it does not count
    body = {"messages": [{"role": "user", "content": "u"},
                         {"role": "assistant", "content": [THINK, tool_use()]},
                         {"role": "user", "content": []}]}
    r.check_eq("note passed back", R.passed_back([THINK, tool_use()], body), (1, 1))
    changed = dict(THINK, signature="OTHER")
    r.check_eq("a changed signature does not count",
               R.passed_back([changed, tool_use()], body), (1, 0))
    r.check_eq("a dropped note does not count", R.passed_back(
        [THINK], {"messages": [{"role": "user", "content": "u"},
                               {"role": "assistant", "content": [tool_use()]},
                               {"role": "user", "content": []}]}), (1, 0))
    r.check_eq("first request", R.passed_back(None, {"messages": [
        {"role": "user", "content": "u"}]}), (0, 0))
    r.check_eq("tool results that are errors",
               [R.tool_result_is_error(x) for x in (
                   "Tool error: boom", '{"error": true, "message": "x"}', PLANNER_OK,
                   '{"valid": false}', "plain text")], [True, True, False, False, False])

    # several text blocks in the final turn are one answer; a note between them is not text
    wire = Wire(lambda q, b, n: msg([{"type": "text", "text": "A\n"}, THINK,
                                     {"type": "text", "text": "```\n(pick-up b)\n```"}],
                                    "end_turn") if has_tool_result(b)
                else msg([tool_use()], "tool_use"))
    outcome, row, meta = await trial(wire)
    r.check_eq("multi-block final text", (row["result"]["response"], row["result"]["thinking"]),
               ("A\n```\n(pick-up b)\n```", THINK["thinking"]))

    # the harness grader raises: a scoring-error row, as the harness writes it
    saved = R.check_success

    async def boom(*a, **k):
        raise RuntimeError("grader broke")
    R.check_success = boom
    try:
        wire = Wire(one_tool_then_answer)
        outcome, row, meta = await trial(wire)
    finally:
        R.check_success = saved
    res = row["result"]
    r.check_eq("scoring exception row", (res["success"], res["tool_selected"],
                                         res["failure_reason"], res["error"],
                                         res["response"], res["tokens"]["turns"]),
               (False, None, "exception", "scoring error: grader broke", TEXT_PLAN["text"], 2))
    r.check("the frozen loader reads it as a scoring error", loader_row(row, True).scoring_error)

    # pilot check: thinking where none may be, and limit numbers in over-length errors
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "h"
        out.mkdir()
        wire = Wire(lambda q, b, n: api_error(400, "invalid_request_error",
                                              "prompt is too long: 1,200,000 tokens > 1000000")
                    if has_tool_result(b) else msg([tool_use()], "tool_use", HAIKU, think_tok=2))
        c = wire.client()
        await R.run_live_cell(c, live_mcp(), HAIKU, [job("solve", HAIKU)], out)
        rep = R.pilot_check_cell(out, HAIKU, "tools", 1)
        r.check_eq("pilot check: Haiku must not think; limit numbers are listed",
                   (rep["thinking_tokens"], rep["thinking_expected_to_be_zero"], rep["passes"],
                    rep["limit_numbers_in_over_length_errors"], rep["endings"]),
                   (2, True, False, ["1,200,000", "1000000"], {"overflow": 1}))
        await c.close()

    # lock and repair
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "cell"
        with R.RunLock(out):
            try:
                with R.RunLock(out):
                    r.check("a second run in the same folder is refused", False, "entered")
            except R.Halt:
                r.check("a second run in the same folder is refused", True)
        r.check("the lock is released", not (out / ".lock").exists())
        with R.RunLock(out):
            pass
        good = json.dumps({"key": ["a"], "result": {}}) + "\n"
        (out / "trials.jsonl").write_text(good + '{"key": ["b"], "resu')
        (out / "trial_meta.jsonl").write_text(good)
        r.check_eq("half-written last line is cut and counted", R.repair_cell(out),
                   {"trials.jsonl": 1})
        r.check_eq("the complete lines stay", (out / "trials.jsonl").read_text(), good)
        r.check("the repair is logged", "trials.jsonl" in (out / "repairs.log").read_text())
        r.check_eq("nothing to repair the second time", R.repair_cell(out), {})
        (out / "x.jsonl").write_text("no newline at all")
        R.repair_cell(out)
        r.check_eq("a file that is one half-written line becomes empty",
                   (out / "x.jsonl").read_text(), "")

    # the tools self-check, on a small list
    saved = R.build_grid
    small = [job("solve"), job("validate_domain"), job("validate_problem"),
             job("validate_plan")]
    R.build_grid = lambda *a, **k: small
    try:
        doms = {"blocksworld": {"type": "classical"}}
        rep = await R.tools_selfcheck(mcp_ok(), doms, {})
        r.check_eq("self-check: all agree", (rep["fixtures"], rep["agree"], rep["disagreements"],
                                             rep["solve_plans_equal_to_the_cached_plan"]),
                   (4, 4, [], 1))
        wrong = FakeMCP(lambda name, args: json.dumps({"valid": False, "status": "INVALID"})
                        if name == "validate_domain" else mcp_ok()._handler(name, args))
        rep = await R.tools_selfcheck(wrong, doms, {})
        r.check_eq("self-check: a wrong verdict is listed",
                   (rep["agree"], [(d["task"], d["tool"]) for d in rep["disagreements"]]),
                   (3, [("validate_domain", "validate_domain")]))
    finally:
        R.build_grid = saved
    r.check_eq("right tool per task", [R.right_tool_call(job(t), {"blocksworld": {
        "type": "numeric" if t == "solve" else "classical"}})[0] for t in R.TASKS],
        ["numeric_planner", "validate_domain", "validate_problem", "validate_plan",
         "get_state_transition"])
    r.check_eq("manifest records the address and the runner's files",
               (R.build_run_manifest(SONNET, "no-tools", pilot=True, sdk_version="x",
                                     gt_cache=Path("x"), ground_truth={}, marketplace=None,
                                     tools_digest=None)["base_url"],
                sorted(R.file_hashes())),
               ("https://api.anthropic.com", sorted(R.RUNNER_FILES)))
    with tempfile.TemporaryDirectory() as td:
        rec = R.log_provenance(Path(td))
        r.check("provenance: commit and file digests on every start",
                bool(rec["repo_commit"]) and set(rec["runner_sha256"]) == set(R.RUNNER_FILES)
                and len(R.read_jsonl(Path(td) / "run_provenance.jsonl")[0]) == 1)

    # dry-run builds no client
    path = gt_cache_path()
    if path is None:
        print("  SKIPPED dry-run-without-client: the ground-truth cache is not here")
    else:
        import argparse
        import contextlib
        import io
        saved = R.make_client

        def no_client(*a, **k):
            raise AssertionError("dry-run built a client")
        R.make_client = no_client
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                await R._cmd_dry_run(argparse.Namespace(
                    gt_cache=str(path), marketplace_path=None, models=list(R.MODELS),
                    pilot=True))
            r.check("dry-run builds no client and prints the counts",
                    "total trials: 640" in buf.getvalue())
        finally:
            R.make_client = saved


def test_cli(r: TestResults) -> None:
    def run(*args, env=None):
        e = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
        e.update(env or {})
        p = subprocess.run([sys.executable, "-m", "tools.frontier55.runner", *args],
                           cwd=str(REPO_ROOT), capture_output=True, text=True, env=e)
        return p.returncode, p.stdout + p.stderr
    with tempfile.TemporaryDirectory() as td:
        code, out = run("live", "--model", HAIKU, "--out", td + "/frontier55-pilot",
                        "--marketplace-path", td, "--pilot")
        r.check("a paid command without --max-usd is refused by the parser",
                code == 2 and "--max-usd" in out, out[-200:])
        code, out = run("batch-submit", "--model", HAIKU, "--out", td + "/frontier55",
                        "--pilot", "--max-usd", "1")
        r.check("a pilot outside a pilot folder: exit 2", code == 2 and "HALT" in out, out[-200:])
        code, out = run("live", "--model", HAIKU, "--out", td + "/frontier55-pilot", "--pilot",
                        "--max-usd", "1", "--marketplace-path", td)
        r.check("a folder that is no tools checkout: exit 2",
                code == 2 and "plugins" in out, out[-200:])
        code, out = run("pilot-check", "--out", td + "/frontier55-pilot")
        r.check("pilot-check on empty folders: exit 2", code == 2 and '"passes": false' in out,
                out[-200:])
        code, out = run("batch-recover", "--model", HAIKU, "--out", td + "/frontier55-pilot",
                        env={"ANTHROPIC_BASE_URL": "http://localhost:1"})
        r.check("another base URL: exit 2 before any call",
                code == 2 and "ANTHROPIC_BASE_URL" in out, out[-200:])
        path = gt_cache_path()
        if path is None:
            print("  SKIPPED CLI dry-run: the ground-truth cache is not here")
        else:
            code, out = run("dry-run", "--pilot", "--gt-cache", str(path),
                            env={"ANTHROPIC_BASE_URL": "http://localhost:1"})
            r.check("dry-run: exit 0, with no key and a foreign base URL in the environment",
                    code == 0 and "total trials: 640" in out, out[-200:])
            code, out = run("dry-run", "--gt-cache", td + "/missing.json")
            r.check("dry-run without the cache: exit 2", code == 2, out[-200:])


async def amain() -> TestResults:
    r = TestResults("frontier55 runner")
    test_request_shapes(r)
    await test_tool_loop(r)
    await test_endings(r)
    await test_loader_all_tasks(r)
    await test_live_resume(r)
    await test_batch(r)
    test_marketplace(r)
    test_manifest_and_cache(r)
    test_grid(r)
    test_cost(r)
    await test_money_paths(r)
    await test_batch_send_and_recover(r)
    await test_more_checks(r)
    test_cli(r)
    return r


if __name__ == "__main__":
    asyncio.run(amain()).report_and_exit()
