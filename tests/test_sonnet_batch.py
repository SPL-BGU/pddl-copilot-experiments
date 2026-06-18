"""Unit tests for tools.sonnet_batch pure helpers.

Pure-Python: no MCP, no Anthropic API, no fixture I/O. Validates the two
load-bearing helpers — request construction (`_build_request`) and response
grading (`_grade_one`) — so the offline Sonnet batch path is covered without
spending money or standing up servers.

Run standalone: `python3 tests/test_sonnet_batch.py`
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
import tools.sonnet_batch as sb
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


if __name__ == "__main__":
    r = TestResults("test_sonnet_batch")
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
