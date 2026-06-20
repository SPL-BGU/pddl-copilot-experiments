"""Unit tests for tools.sonnet_tools_probe pure helpers + the shared
format-fidelity rule (tools._sonnet_common.format_for).

Pure-Python: no MCP, no Anthropic API, no fixture I/O. Covers the glue the
live with-tools probe owns on top of the reused harness graders:
  * format_for      — per-task format handling MATCHES the vLLM harness
                      (guided_json analog in no-tools; NOTHING in with-tools).
  * _anthropic_tools / _assistant_content — OpenAI->Anthropic shape conversion.
  * _failed_result  — per-trial API-failure record (infra_failure, tool_selected).
  * _grade          — refusal short-circuit, with-tools loop-exhaust routing,
                      and max_tokens->length/truncation, all without spending money.

Run standalone: `python3 tests/test_sonnet_tools_probe.py`
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import FakeMCP, TestResults
import tools.sonnet_tools_probe as sp
from tools._sonnet_common import SIMULATE_JSON_DIRECTIVE, format_for
from pddl_eval.scoring import (
    FR_EXCEPTION,
    FR_LOOP_EXHAUSTED,
    FR_TOOL_NOT_SELECTED,
)


def _job(task, *, pv=11, plan_label="", gt=None, np=6144):
    # (model, task, dname, dpddl, pname, ppddl, pv, with_tools, gt, np, plan_label)
    return (
        sp.MODEL, task, "blocksworld", "(define (domain bw))", "p01",
        "(define (problem p01))", pv, True, gt or {}, np, plan_label,
    )


def _outcome(**over):
    base = {"text": "", "tool_calls": [], "stop_reason": "end_turn",
            "in_tok": 100, "out_tok": 20, "turns": 1, "loop_exhausted": False}
    base.update(over)
    return base


# --- fakes for the Anthropic response-shape helpers ------------------------

class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _ToolUseBlock:
    type = "tool_use"

    def __init__(self, id, name, inp):
        self.id, self.name, self.input = id, name, inp


class _Resp:
    def __init__(self, content):
        self.content = content


# --- format_for: the vLLM-fidelity matrix (the load-bearing fix) -----------

def test_format_for_simulate_with_tools_adds_nothing(r: TestResults) -> None:
    # THE FIX: vLLM's with-tools branch passes no format constraint, and
    # simulate WT is graded from the get_state_transition tool result — so NO
    # JSON directive in the with-tools path.
    user, cfg = format_for("simulate", "BODY", with_tools=True)
    r.check_eq("simulate WT user text unchanged", user, "BODY")
    r.check("simulate WT no output_config", cfg is None)
    r.check("simulate WT carries no JSON directive",
            "return only a single json" not in user.lower())


def test_format_for_simulate_no_tools_adds_directive(r: TestResults) -> None:
    user, cfg = format_for("simulate", "BODY", with_tools=False)
    r.check("simulate NT appends the JSON directive",
            user == "BODY" + SIMULATE_JSON_DIRECTIVE)
    r.check("simulate NT no output_config (directive, not schema)", cfg is None)


def test_format_for_solve(r: TestResults) -> None:
    user_nt, cfg_nt = format_for("solve", "BODY", with_tools=False)
    r.check_eq("solve NT user text unchanged", user_nt, "BODY")
    r.check("solve NT sets output_config", cfg_nt is not None)
    fmt = cfg_nt["format"]
    r.check_eq("solve NT json_schema", fmt["type"], "json_schema")
    r.check_eq("solve NT forbids extra props", fmt["schema"]["additionalProperties"], False)
    r.check("solve NT schema has plan array",
            fmt["schema"]["properties"]["plan"]["type"] == "array")
    # With tools, the planner MCP returns the plan — no structured-output shape.
    user_wt, cfg_wt = format_for("solve", "BODY", with_tools=True)
    r.check("solve WT no output_config", cfg_wt is None and user_wt == "BODY")


def test_format_for_validate_never_constrained(r: TestResults) -> None:
    # validate_* rely on the corpus VERDICT footer + free-text fallback in
    # BOTH conditions — never a directive or schema.
    for task in ("validate_domain", "validate_problem", "validate_plan"):
        for wt in (True, False):
            user, cfg = format_for(task, "BODY", with_tools=wt)
            r.check(f"{task} wt={wt} unchanged + no cfg", user == "BODY" and cfg is None)


# --- response-shape helpers ------------------------------------------------

def test_anthropic_tools_conversion(r: TestResults) -> None:
    mcp = FakeMCP()
    mcp.tools = [{
        "type": "function",
        "function": {"name": "classic_planner", "description": "solve it",
                     "parameters": {"type": "object", "properties": {}}},
    }]
    out = sp._anthropic_tools(mcp)
    r.check_eq("one tool converted", len(out), 1)
    r.check_eq("name copied", out[0]["name"], "classic_planner")
    r.check_eq("description copied", out[0]["description"], "solve it")
    r.check("parameters -> input_schema", out[0]["input_schema"] == {"type": "object", "properties": {}})
    r.check("no leftover OpenAI 'function' key", "function" not in out[0])


def test_assistant_content_reconstruction(r: TestResults) -> None:
    resp = _Resp([_TextBlock("thinking out loud"),
                  _ToolUseBlock("tu_1", "validate_plan", {"plan": "(a)"})])
    blocks = sp._assistant_content(resp)
    r.check_eq("two blocks", len(blocks), 2)
    r.check_eq("text block preserved", blocks[0], {"type": "text", "text": "thinking out loud"})
    r.check_eq("tool_use id", blocks[1]["id"], "tu_1")
    r.check_eq("tool_use name", blocks[1]["name"], "validate_plan")
    r.check_eq("tool_use input", blocks[1]["input"], {"plan": "(a)"})


# --- _failed_result --------------------------------------------------------

def test_failed_result_with_tools(r: TestResults) -> None:
    res = sp._failed_result(_job("simulate"), "400 context overflow", with_tools=True)
    r.check("failure not a success", not res.success)
    r.check("infra_failure keeps it out of capability stats", res.infra_failure)
    r.check_eq("FR_EXCEPTION", res.failure_reason, FR_EXCEPTION)
    r.check("with-tools -> tool_selected False", res.tool_selected is False)
    r.check_eq("error truncated/recorded", res.error, "400 context overflow")
    r.check_eq("done_reason error", res.done_reason, "error")


def test_failed_result_no_tools(r: TestResults) -> None:
    res = sp._failed_result(_job("solve"), "boom", with_tools=False)
    r.check("no-tools -> tool_selected None", res.tool_selected is None)
    r.check("with_tools flag recorded", res.with_tools is False)


# --- _grade: probe glue around the reused grader ---------------------------

def test_grade_refusal(r: TestResults) -> None:
    res = asyncio.run(sp._grade(
        _job("validate_plan", gt={"plan_valid": True}, plan_label="v1"),
        _outcome(stop_reason="refusal", text="", in_tok=5, out_tok=0),
        FakeMCP(), with_tools=True,
    ))
    r.check("refusal -> failure", not res.success)
    r.check_eq("FR_EXCEPTION on refusal", res.failure_reason, FR_EXCEPTION)
    r.check_eq("error names the refusal", res.error, "stop_reason=refusal")
    r.check("refusal not flagged truncated", res.truncated is False)
    r.check_eq("done_reason carries refusal", res.done_reason, "refusal")
    r.check_eq("prompt tokens recorded", res.tokens["prompt"], 5)
    r.check("with_tools tagged", res.with_tools is True)


def test_grade_loop_exhausted(r: TestResults) -> None:
    # with-tools, no tool ever selected, loop ran to the cap -> FR_LOOP_EXHAUSTED
    # (the routing that distinguishes the probe from the no-tools batch path).
    res = asyncio.run(sp._grade(
        _job("validate_plan", gt={"plan_valid": True}, plan_label="v1"),
        _outcome(stop_reason="tool_use", loop_exhausted=True, turns=10),
        FakeMCP(), with_tools=True,
    ))
    r.check("loop-exhaust -> failure", not res.success)
    r.check_eq("FR_LOOP_EXHAUSTED routed", res.failure_reason, FR_LOOP_EXHAUSTED)
    r.check_eq("turns recorded", res.tokens["turns"], 10)


def test_grade_max_tokens_truncation(r: TestResults) -> None:
    res = asyncio.run(sp._grade(
        _job("validate_plan", gt={"plan_valid": True}, plan_label="v1"),
        _outcome(stop_reason="max_tokens", loop_exhausted=False),
        FakeMCP(), with_tools=True,
    ))
    r.check_eq("max_tokens -> done_reason length", res.done_reason, "length")
    r.check("truncated flag set", res.truncated)
    # No tool selected, so the (non-truncation-override) tool-not-selected tag
    # stands even under truncation.
    r.check_eq("tool-not-selected stands", res.failure_reason, FR_TOOL_NOT_SELECTED)


if __name__ == "__main__":
    r = TestResults("test_sonnet_tools_probe")
    test_format_for_simulate_with_tools_adds_nothing(r)
    test_format_for_simulate_no_tools_adds_directive(r)
    test_format_for_solve(r)
    test_format_for_validate_never_constrained(r)
    test_anthropic_tools_conversion(r)
    test_assistant_content_reconstruction(r)
    test_failed_result_with_tools(r)
    test_failed_result_no_tools(r)
    test_grade_refusal(r)
    test_grade_loop_exhausted(r)
    test_grade_max_tokens_truncation(r)
    r.report_and_exit()
