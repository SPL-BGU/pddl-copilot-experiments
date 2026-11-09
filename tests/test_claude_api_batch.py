"""Unit tests for tools.claude_api_batch pure helpers.

Pure-Python: no MCP, no Anthropic API, no fixture I/O. Validates the two
load-bearing helpers — request construction (`_build_request`) and response
grading (`_grade_one`) — so the offline Sonnet batch path is covered without
spending money or standing up servers.

Run standalone: `python3 tests/test_claude_api_batch.py`
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
import tools.claude_api_batch as sb
from pddl_eval.runner import TRIAL_KEY_LEN
from pddl_eval.scoring import (
    FR_EXCEPTION,
    FR_OK,
    FR_TRUNCATED_NO_ANSWER,
    FR_VERDICT_MISMATCH,
)


def _job(task, *, pv=11, plan_label="", gt=None, np=6144):
    # (model, task, dname, dpddl, pname, ppddl, pv, with_tools, gt, np, plan_label)
    return (
        sb.MODEL, task, "blocksworld", "(define (domain bw))", "p01",
        "(define (problem p01))", pv, False, gt or {}, np, plan_label,
    )


def _meta(task, *, gt, plan_label=""):
    return {
        "task": task, "gt": gt, "domain_pddl": "(d)", "problem_pddl": "(p)",
        "domain_name": "blocksworld", "problem_name": "p01",
        "prompt_variant": 11, "plan_label": plan_label,
    }


def test_build_request_validate(r: TestResults) -> None:
    gt = {"plan": ["(a)", "(b)"], "plan_valid": True,
          "domain_valid": True, "problem_valid": True}
    req, side = sb._build_request("t000001", _job("validate_plan", plan_label="v1", gt=gt))
    p = req["params"]
    r.check_eq("custom_id", req["custom_id"], "t000001")
    r.check_eq("model", p["model"], sb.MODEL)
    r.check_eq("max_tokens from job num_predict", p["max_tokens"], 6144)
    r.check_eq("temperature 0", p["temperature"], 0)
    r.check("no thinking key (think=off)", "thinking" not in p)
    r.check("no output_config (free-text VERDICT path)", "output_config" not in p)
    r.check("system carries VERDICT footer", "VERDICT" in p["system"])
    r.check("user embeds the plan", "(a)" in p["messages"][0]["content"])
    r.check(
        "no simulate directive on validate",
        "return only a single json" not in p["messages"][0]["content"].lower(),
    )
    r.check_eq("sidecar task", side["task"], "validate_plan")
    r.check_eq("sidecar plan_label", side["plan_label"], "v1")
    r.check_eq("sidecar carries gt", side["gt"]["plan_valid"], True)


def test_build_request_simulate_directive(r: TestResults) -> None:
    req, _ = sb._build_request("t000002", _job("simulate", gt={"plan": ["(a)"], "trace": "{}"}))
    user = req["params"]["messages"][0]["content"]
    r.check("simulate JSON directive appended", "Return ONLY a single JSON object" in user)
    r.check("directive names the trajectory wrapper", '"trajectory"' in user)
    r.check("no output_config on simulate either", "output_config" not in req["params"])


def test_build_request_solve_structured(r: TestResults) -> None:
    req, _ = sb._build_request("t000003", _job("solve", gt={}))
    p = req["params"]
    r.check("solve uses output_config (guided_json analog)", "output_config" in p)
    fmt = p["output_config"]["format"]
    r.check_eq("json_schema format", fmt["type"], "json_schema")
    r.check_eq("schema forbids extra props", fmt["schema"]["additionalProperties"], False)
    r.check("schema has plan array",
            fmt["schema"]["properties"]["plan"]["type"] == "array")
    r.check("no simulate directive on solve",
            "return only a single json" not in p["messages"][0]["content"].lower())


def test_grade_validate_valid(r: TestResults) -> None:
    res = asyncio.run(sb._grade_one(
        _meta("validate_plan", gt={"plan_valid": True}, plan_label="v1"),
        "Reasoning here...\nVERDICT: VALID", "end_turn", 100, 20,
    ))
    r.check("validate VALID -> success", res.success)
    r.check_eq("FR_OK", res.failure_reason, FR_OK)
    r.check_eq("model tagged", res.model, sb.MODEL)
    r.check("no-tools record", res.with_tools is False)
    r.check_eq("prompt tokens recorded", res.tokens["prompt"], 100)
    r.check_eq("completion tokens recorded", res.tokens["completion"], 20)
    r.check_eq("final-turn tokens recorded (single turn == aggregate)",
               res.tokens["completion_final"], 20)


def test_grade_validate_mismatch(r: TestResults) -> None:
    # truth INVALID, model says VALID -> verdict mismatch (not truncation).
    res = asyncio.run(sb._grade_one(
        _meta("validate_plan", gt={"plan_valid": False}, plan_label="b1"),
        "VERDICT: VALID", "end_turn", 50, 10,
    ))
    r.check("mismatch -> failure", not res.success)
    r.check_eq("FR_VERDICT_MISMATCH", res.failure_reason, FR_VERDICT_MISMATCH)


def test_grade_truncation_override(r: TestResults) -> None:
    # No VERDICT line + max_tokens -> FORMAT_PARSE_FAIL reclassified to TRUNCATED.
    res = asyncio.run(sb._grade_one(
        _meta("validate_plan", gt={"plan_valid": True}, plan_label="v1"),
        "Let me think it through... (cut off", "max_tokens", 50, 6144,
    ))
    r.check("truncated flag set", res.truncated)
    r.check_eq("reclassified to TRUNCATED_NO_ANSWER", res.failure_reason, FR_TRUNCATED_NO_ANSWER)
    r.check_eq("done_reason mapped to length", res.done_reason, "length")


def test_grade_error_and_refusal(r: TestResults) -> None:
    err = asyncio.run(sb._grade_one(
        _meta("validate_plan", gt={"plan_valid": True}), None, None, 0, 0, error="boom",
    ))
    r.check("error -> failure", not err.success)
    r.check_eq("FR_EXCEPTION on error", err.failure_reason, FR_EXCEPTION)
    r.check_eq("error recorded", err.error, "boom")

    refusal = asyncio.run(sb._grade_one(
        _meta("validate_plan", gt={"plan_valid": True}), "", "refusal", 5, 0,
    ))
    r.check("refusal -> failure", not refusal.success)
    r.check_eq("FR_EXCEPTION on refusal", refusal.failure_reason, FR_EXCEPTION)


def test_trial_key_for_shape(r: TestResults) -> None:
    key = sb._trial_key_for(_meta("simulate", gt={}))
    r.check_eq("trial key length", len(key), TRIAL_KEY_LEN)
    r.check_eq("model is first field", key[0], sb.MODEL)
    r.check("with_tools is False", key[6] is False)
    r.check_eq("think tag = off", key[7], "off")
    r.check_eq("tool_filter = all", key[8], "all")
    r.check_eq("prompt_style = minimal", key[9], "minimal")


def test_project_cost(r: TestResults) -> None:
    per_task = {"validate_plan": {"n": 50, "success": 40, "in_tok": 100_000, "out_tok": 20_000}}
    counts = {"validate_plan": {"full": 3000, "selected": 50}}
    proj = sb._project_cost(per_task, counts)["validate_plan"]
    # observed = 100k*1.5e-6 + 20k*7.5e-6 = 0.15 + 0.15 = 0.30; projected = *60
    r.check_eq("observed cost", proj["observed_cost_usd"], 0.30)
    r.check_eq("projected full cost", proj["projected_full_cost_usd"], 18.0)
    r.check_eq("full_n surfaced", proj["full_n"], 3000)


# ---------------------------------------------------------------------------
# D5a request-setting options (2026-11-09)
# ---------------------------------------------------------------------------
import json  # noqa: E402
import string  # noqa: E402
import tempfile  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from pddl_eval.runner import build_messages  # noqa: E402
from tools._claude_api_common import format_for  # noqa: E402

CORREA_FILE = Path(__file__).resolve().parent.parent / "tools" / "prompts" / "correa2026_2shot.txt"
CORREA_BODY_SHA256 = "e3ca10c40da0ddc6455120f9d622a3d4a5563998e51ca49101676fed0291fb86"
CORREA_SOURCE_PY_SHA256 = "17bed943c3d577cd33f39a07e5d15a80cadaacb8a5dd64b81a2677ecaa32122d"


def _reference_build_request(custom_id, job, model):
    """Frozen copy of `_build_request` as it was before the D5a options (the
    request the Sonnet 4.6 and Haiku 4.5 frontier cells were sent)."""
    task = job[1]
    dpddl, ppddl = job[3], job[5]
    pv, gt = job[6], job[8]
    messages = build_messages(task, dpddl, ppddl, pv, with_tools=False, gt=gt)
    system_text = messages[0]["content"]
    user_text, output_config = format_for(task, messages[1]["content"], with_tools=False)
    params = {
        "model": model,
        "max_tokens": job[9],
        "temperature": 0,
        "system": system_text,
        "messages": [{"role": "user", "content": user_text}],
    }
    if output_config:
        params["output_config"] = output_config
    return {"custom_id": custom_id, "params": params}


_GT_BY_TASK = {
    "solve": {},
    "simulate": {"plan": ["(a)"], "trace": "{}"},
    "validate_plan": {"plan": ["(a)", "(b)"], "plan_valid": True},
    "validate_problem": {"problem_valid": False},
    "validate_domain": {"domain_valid": True},
}


def test_default_request_byte_identical(r: TestResults) -> None:
    for model in ("claude-sonnet-4-6", "claude-haiku-4-5"):
        old = sb.MODEL
        sb.MODEL = model
        try:
            for task, gt in _GT_BY_TASK.items():
                for pv in (11, 12, 13):
                    pl = "v1" if task == "validate_plan" else ""
                    job = _job(task, pv=pv, plan_label=pl, gt=gt,
                               np=8192 if task == "solve" else 6144)
                    ref = json.dumps(_reference_build_request("t000007", job, model))
                    for settings in (None, dict(sb.DEFAULT_SETTINGS)):
                        new, side = sb._build_request("t000007", job, settings)
                        r.check(f"{model} {task} v{pv} settings={settings is not None}: "
                                "request byte-identical", json.dumps(new) == ref)
                        r.check(f"{model} {task} v{pv}: sidecar has no D5a keys",
                                "request_settings" not in side and "repeat" not in side)
        finally:
            sb.MODEL = old


def _with_model(model, fn):
    old = sb.MODEL
    sb.MODEL = model
    try:
        return fn()
    finally:
        sb.MODEL = old


def test_thinking_on_budget_models(r: TestResults) -> None:
    s = dict(thinking="on", temperature_mode="default", thinking_budget=32000)
    for model in ("claude-sonnet-4-6", "claude-haiku-4-5"):
        sb.validate_settings(model, s, tasks=["solve"])
        req, side = _with_model(model, lambda: sb._build_request(
            "t1", _job("solve", np=64000), s))
        p = req["params"]
        r.check_eq(f"{model}: thinking enabled + budget", p["thinking"],
                   {"type": "enabled", "budget_tokens": 32000})
        r.check(f"{model}: temperature omitted", "temperature" not in p)
        r.check_eq(f"{model}: max_tokens 64000", p["max_tokens"], 64000)
        r.check_eq(f"{model}: model", p["model"], model)
        r.check(f"{model}: solve schema kept", p["output_config"]["format"]["type"] == "json_schema")
        r.check(f"{model}: no effort", "effort" not in p["output_config"])
        r.check(f"{model}: system prompt kept", "system" in p)
        r.check_eq(f"{model}: sidecar records settings", side["request_settings"]["thinking"], "on")
    # budget must stay below max_tokens
    try:
        _with_model("claude-sonnet-4-6", lambda: sb._build_request(
            "t1", _job("solve", np=32000), s))
        r.check("budget >= max_tokens refused", False, "no exception")
    except ValueError:
        r.check("budget >= max_tokens refused", True)


def test_sonnet55_arms(r: TestResults) -> None:
    on = dict(thinking="on", temperature_mode="default", effort="high")
    bt = dict(thinking="between_tools", temperature_mode="default", effort="high")
    for label, s, want in (("on", on, {"type": "adaptive", "display": "summarized"}),
                           ("between_tools", bt, {"type": "between_tools"})):
        sb.validate_settings("claude-sonnet-5-5", s, tasks=["solve"])
        req, _ = _with_model("claude-sonnet-5-5", lambda: sb._build_request(
            "t1", _job("solve", np=64000), s))
        p = req["params"]
        r.check_eq(f"5.5 {label}: thinking param", p["thinking"], want)
        r.check_eq(f"5.5 {label}: effort high sent", p["output_config"]["effort"], "high")
        r.check(f"5.5 {label}: solve schema kept",
                p["output_config"]["format"]["type"] == "json_schema")
        r.check(f"5.5 {label}: temperature omitted", "temperature" not in p)
        r.check_eq(f"5.5 {label}: model id", p["model"], "claude-sonnet-5-5")
    r.check_eq("5.5 list price", sb.LIST_PRICES["claude-sonnet-5-5"],
               (2.0 / 1_000_000, 10.0 / 1_000_000))


def test_validate_settings_refusals(r: TestResults) -> None:
    bad = [
        ("5.5 off", "claude-sonnet-5-5", dict(thinking="off", temperature_mode="default", effort="high")),
        ("5.5 temperature 0", "claude-sonnet-5-5", dict(thinking="on", effort="high")),
        ("5.5 budget", "claude-sonnet-5-5", dict(thinking="on", temperature_mode="default",
                                                 effort="high", thinking_budget=2048)),
        ("5.5 no effort", "claude-sonnet-5-5", dict(thinking="on", temperature_mode="default")),
        ("5.5 between_tools xhigh", "claude-sonnet-5-5",
         dict(thinking="between_tools", temperature_mode="default", effort="xhigh")),
        ("4.6 between_tools", "claude-sonnet-4-6", dict(thinking="between_tools", temperature_mode="default")),
        ("4.6 on at T=0", "claude-sonnet-4-6", dict(thinking="on", thinking_budget=2048)),
        ("4.6 on without budget", "claude-sonnet-4-6", dict(thinking="on", temperature_mode="default")),
        ("4.6 budget below 1024", "claude-sonnet-4-6",
         dict(thinking="on", temperature_mode="default", thinking_budget=512)),
        ("haiku effort", "claude-haiku-4-5", dict(effort="high")),
        ("budget with thinking off", "claude-sonnet-4-6", dict(thinking_budget=2048)),
        ("unknown key", "claude-sonnet-4-6", dict(top_p=0.5)),
    ]
    for label, model, s in bad:
        try:
            sb.validate_settings(model, s, tasks=["solve"])
            r.check(f"refused: {label}", False, "no exception")
        except ValueError:
            r.check(f"refused: {label}", True)
    try:
        sb.validate_settings("claude-sonnet-4-6", dict(prompt_file="x.txt"),
                             tasks=["solve", "simulate"])
        r.check("refused: prompt file on non-solve", False, "no exception")
    except ValueError:
        r.check("refused: prompt file on non-solve", True)
    # T=1 control (thinking off, temperature omitted) is allowed on 4.6/Haiku.
    sb.validate_settings("claude-haiku-4-5", dict(temperature_mode="default"), tasks=["solve"])
    req, _ = sb._build_request("t1", _job("solve", np=8192), dict(temperature_mode="default"))
    r.check("T=1 control: temperature omitted, no thinking",
            "temperature" not in req["params"] and "thinking" not in req["params"])


def test_correa_template(r: TestResults) -> None:
    import hashlib
    t = sb.load_prompt_template(CORREA_FILE)
    r.check_eq("vendored body sha256", t["body_sha256"], CORREA_BODY_SHA256)
    r.check("header records source file sha256", CORREA_SOURCE_PY_SHA256 in CORREA_FILE.read_text())
    r.check("header is not part of the body", "Zenodo" not in t["body"])
    r.check("body starts like the source literal", t["body"].startswith("\n<problem-description>\n"))
    names = {m.group("named") or m.group("braced")
             for m in string.Template.pattern.finditer(t["body"])
             if m.group("named") or m.group("braced")}
    r.check_eq("only three placeholders", names, {"name", "domain", "instance"})
    domain = "; header comment\n(define (domain d)\n  ;; inner comment\n  (:action a))\n"
    problem = ";; keep me\n(define (problem p) (:domain d))\n"
    filled = sb.fill_prompt_template(t["body"], "mydom", domain, problem)
    expected = string.Template(t["body"]).substitute(
        name="mydom", domain="(define (domain d)\n  (:action a))\n", instance=problem)
    r.check("fill = Template.substitute with ';' lines dropped from the domain", filled == expected)
    r.check("instance comment kept", ";; keep me" in filled)
    r.check("domain comment dropped", "inner comment" not in filled)
    r.check("examples present (not elided)", "(pick ball9 rooma right)" in filled
            and "[...]" not in filled)
    # Request shape: one user message, no system prompt, no structured output.
    s = dict(prompt_file=str(CORREA_FILE))
    req, side = sb._build_request("t1", _job("solve", np=8192), s, t)
    p = req["params"]
    r.check("correa: no system prompt", "system" not in p)
    r.check("correa: no output_config", "output_config" not in p)
    r.check_eq("correa: temperature 0", p["temperature"], 0)
    r.check_eq("correa: single user message", [m["role"] for m in p["messages"]], ["user"])
    r.check("correa: domain name filled", "<domain>blocksworld</domain>" in p["messages"][0]["content"])
    r.check_eq("correa: sidecar body sha", side["prompt_file_body_sha256"], CORREA_BODY_SHA256)
    try:
        sb._build_request("t1", _job("simulate"), s, t)
        r.check("correa: non-solve refused", False, "no exception")
    except ValueError:
        r.check("correa: non-solve refused", True)
    # A tampered body is refused.
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.txt"
        bad.write_text(CORREA_FILE.read_text() + "extra\n")
        try:
            sb.load_prompt_template(bad)
            r.check("tampered body refused", False, "no exception")
        except ValueError:
            r.check("tampered body refused", True)
    r.check("file sha recorded", t["file_sha256"] == hashlib.sha256(CORREA_FILE.read_bytes()).hexdigest())


def test_seeded_order(r: TestResults) -> None:
    jobs = [_job("solve", pv=pv) for pv in (11, 12, 13)]
    jobs = [j[:4] + (f"p{i:02d}",) + j[5:] for i in range(10) for j in jobs]
    a = sb.seeded_order(jobs, 7)
    b = sb.seeded_order(list(reversed(jobs)), 7)
    r.check("seeded order independent of input order", a == b)
    r.check("different seed, different order", sb.seeded_order(jobs, 8) != a)
    r.check_eq("same multiset", sorted(a), sorted(jobs))


def _fake_result(content, usage, stop_reason="end_turn", model="claude-sonnet-4-6"):
    msg = SimpleNamespace(model=model, stop_reason=stop_reason, stop_details=None,
                          content=content, usage=usage)
    return SimpleNamespace(custom_id="t000001",
                           result=SimpleNamespace(type="succeeded", message=msg))


class _Usage(SimpleNamespace):
    def model_dump(self, mode="json"):
        d = dict(vars(self))
        if d.get("output_tokens_details") is not None:
            d["output_tokens_details"] = dict(vars(d["output_tokens_details"]))
        return d


def test_result_row(r: TestResults) -> None:
    usage = _Usage(input_tokens=1500, output_tokens=9000,
                   output_tokens_details=SimpleNamespace(thinking_tokens=8600))
    content = [SimpleNamespace(type="thinking", thinking="step one", signature="x"),
               SimpleNamespace(type="text", text='{"plan": ["(a)"]}')]
    params = {"model": "claude-sonnet-4-6", "max_tokens": 64000, "system": "S",
              "messages": [{"role": "user", "content": "U"}],
              "thinking": {"type": "enabled", "budget_tokens": 32000}}
    side = {"task": "solve", "domain_name": "bw", "problem_name": "p01",
            "prompt_variant": 11, "plan_label": ""}
    row = sb._result_row(_fake_result(content, usage), params, side, "0.109.2")
    r.check_eq("answer = text blocks only", row["answer"], '{"plan": ["(a)"]}')
    r.check_eq("thinking text stored", row["thinking_text"], "step one")
    r.check_eq("thinking tokens from usage", row["thinking_tokens"], 8600)
    r.check_eq("visible output tokens = output - thinking (both from usage)",
               row["visible_output_tokens"], 400)
    r.check_eq("model id", row["model_id"], "claude-sonnet-4-6")
    r.check_eq("sdk version", row["sdk_version"], "0.109.2")
    r.check("settings exclude prompt text", "messages" not in row["request_settings"]
            and "system" not in row["request_settings"])
    r.check_eq("settings keep thinking", row["request_settings"]["thinking"]["budget_tokens"], 32000)
    r.check_eq("usage dumped", row["usage"]["output_tokens_details"]["thinking_tokens"], 8600)
    r.check_eq("key fields", (row["task"], row["domain_name"], row["prompt_variant"]),
               ("solve", "bw", 11))
    # No details in usage -> recorded as None, never derived from the text.
    usage2 = _Usage(input_tokens=10, output_tokens=20, output_tokens_details=None)
    row2 = sb._result_row(_fake_result([SimpleNamespace(type="text", text="x")], usage2),
                          None, None, "0.109.2")
    r.check("no usage details -> thinking_tokens None", row2["thinking_tokens"] is None)
    r.check("no usage details -> visible None", row2["visible_output_tokens"] is None)
    err = SimpleNamespace(custom_id="t2", result=SimpleNamespace(type="errored", error="bad"))
    r.check_eq("errored row", sb._result_row(err, None, None, "v")["error"], "bad")


def test_worst_case_cost(r: TestResults) -> None:
    reqs = [{"params": {"max_tokens": 64000, "system": "s" * 200,
                        "messages": [{"role": "user", "content": "u" * 1800}]}}] * 20
    wc = sb.worst_case_list_cost(reqs, "claude-sonnet-4-6")
    # input bound 1001/req, output 64000/req -> 20*(1001*3 + 64000*15)/1e6
    r.check_eq("worst case output bound", wc["output_tokens_bound"], 1_280_000)
    r.check_eq("worst case list usd", wc["list_usd"], round(20 * (1001 * 3 + 64000 * 15) / 1e6, 4))


def test_is_default_settings(r: TestResults) -> None:
    r.check("None is default", sb.is_default_settings(None))
    r.check("explicit defaults are default", sb.is_default_settings(dict(thinking="off")))
    r.check("T=1 is not default", not sb.is_default_settings(dict(temperature_mode="default")))


if __name__ == "__main__":
    r = TestResults("test_claude_api_batch")
    test_default_request_byte_identical(r)
    test_thinking_on_budget_models(r)
    test_sonnet55_arms(r)
    test_validate_settings_refusals(r)
    test_correa_template(r)
    test_seeded_order(r)
    test_result_row(r)
    test_worst_case_cost(r)
    test_is_default_settings(r)
    test_build_request_validate(r)
    test_build_request_simulate_directive(r)
    test_build_request_solve_structured(r)
    test_grade_validate_valid(r)
    test_grade_validate_mismatch(r)
    test_grade_truncation_override(r)
    test_grade_error_and_refusal(r)
    test_trial_key_for_shape(r)
    test_project_cost(r)
    r.report_and_exit()
