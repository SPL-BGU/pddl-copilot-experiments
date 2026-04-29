"""Table-driven tests for check_success (run_experiment.py).

Run standalone: `python3 tests/test_check_success.py`
Or via the shell wrapper: `bash tests/verify.sh`
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_experiment as rx
from tests._helpers import (
    FakeMCP,
    TestResults,
    build_gt_from_fixture,
    load_fixture,
    plan_sensitive_validator,
    raising_handler,
)


# ---------------------------------------------------------------------------
# Tool-call constructors. Each returns a list[dict] shaped like
# chat_with_tools produces: {name, arguments, result}.
# ---------------------------------------------------------------------------

def tc(name, arguments=None, result=""):
    return {"name": name, "arguments": arguments or {}, "result": result}


async def run_case(label, r, task, response, tool_calls, gt, mcp, dom, prob, with_tools, expected):
    got = await rx.check_success(task, response, tool_calls, gt, mcp, dom, prob, with_tools=with_tools)
    r.check_eq(label, got, expected)


# ---------------------------------------------------------------------------
# Solve
# ---------------------------------------------------------------------------

async def test_solve(r: TestResults):
    bw = load_fixture("blocksworld_p01")
    gt = build_gt_from_fixture(bw)
    dom = bw["domain_pddl"]
    prob = bw["problem_pddl"]
    oracle = bw["oracle_plan"]
    bad = bw["bad_plan"]

    mcp_ok = FakeMCP(plan_sensitive_validator(bw))
    mcp_raise = FakeMCP(raising_handler())

    # with-tools, no tool calls
    await run_case("solve wt no-calls", r, "solve", "", [], gt, mcp_ok, dom, prob, True,
                   (False, False, rx.FR_TOOL_NOT_SELECTED))

    # with-tools, called classic_planner with oracle plan returned
    plan_ok_raw = json.dumps(bw["tool_output_objs"]["classic_planner_ok"])
    await run_case("solve wt oracle plan", r, "solve", "",
                   [tc("classic_planner", {"domain": dom, "problem": prob}, plan_ok_raw)],
                   gt, mcp_ok, dom, prob, True,
                   (True, True, rx.FR_OK))

    # with-tools, called with bad plan returned — validator returns invalid
    plan_bad_raw = json.dumps(bw["tool_output_objs"]["classic_planner_bad"])
    await run_case("solve wt bad plan (FR_PLAN_INVALID)", r, "solve", "",
                   [tc("classic_planner", {"domain": dom, "problem": prob}, plan_bad_raw)],
                   gt, mcp_ok, dom, prob, True,
                   (True, False, rx.FR_PLAN_INVALID))

    # with-tools, tool returns error shape
    err_raw = json.dumps(bw["tool_output_objs"]["classic_planner_error"])
    await run_case("solve wt tool error", r, "solve", "",
                   [tc("classic_planner", {}, err_raw)],
                   gt, mcp_ok, dom, prob, True,
                   (True, False, rx.FR_TOOL_ERROR))

    # with-tools, called save_plan only (wrong tool) → tool_not_selected
    await run_case("solve wt wrong tool only", r, "solve", "",
                   [tc("save_plan", {}, "{}")],
                   gt, mcp_ok, dom, prob, True,
                   (False, False, rx.FR_TOOL_NOT_SELECTED))

    # no-tools, response contains oracle plan as (action args)
    oracle_txt = "\n".join(oracle)
    await run_case("solve nt oracle plan in response", r, "solve", oracle_txt, [],
                   gt, mcp_ok, dom, prob, False,
                   (None, True, rx.FR_OK))

    # no-tools, bulleted plan (B2) — this will fail until B2 regex fix lands
    bullet_txt = "\n".join(f"- {a}" for a in oracle)
    await run_case("solve nt bulleted plan (B2)", r, "solve", bullet_txt, [],
                   gt, mcp_ok, dom, prob, False,
                   (None, True, rx.FR_OK))

    # no-tools, response has no plan and no JSON → both paths produce
    # zero plan lines → FR_FORMAT_PARSE_FAIL (PR-4: distinguishes "the
    # model didn't emit any structured/extractable plan" from "had a plan
    # but it didn't pass pyvalidator", which keeps FR_PLAN_INVALID).
    await run_case("solve nt no plan", r, "solve", "I don't know how to solve this.", [],
                   gt, mcp_ok, dom, prob, False,
                   (None, False, rx.FR_FORMAT_PARSE_FAIL))

    # no-tools, structured SolveResponse JSON → grades via Pydantic path
    # (PR-4). Oracle plan returned in JSON wrapper → FR_OK.
    plan_json = json.dumps({"plan": oracle})
    await run_case("solve nt json plan oracle (PR-4)", r, "solve", plan_json, [],
                   gt, mcp_ok, dom, prob, False,
                   (None, True, rx.FR_OK))

    # no-tools, structured JSON with bad plan → extracts plan, validator
    # rejects it → FR_PLAN_INVALID (not FR_FORMAT_PARSE_FAIL because the
    # plan WAS extracted; only validation failed).
    bad_json = json.dumps({"plan": bad})
    await run_case("solve nt json plan bad (PR-4)", r, "solve", bad_json, [],
                   gt, mcp_ok, dom, prob, False,
                   (None, False, rx.FR_PLAN_INVALID))

    # no-tools, MCP transport fails (B3) — this will fail until B3 fix lands.
    # Under current code: returns (None, False, FR_PLAN_INVALID) because
    # _validate_model_plan swallows exception to False.
    # Post-B3: expects FR_TOOL_ERROR.
    await run_case("solve nt MCP down (B3)", r, "solve", oracle_txt, [],
                   gt, mcp_raise, dom, prob, False,
                   (None, False, rx.FR_TOOL_ERROR))


# ---------------------------------------------------------------------------
# Validate_plan (representative for the three validate_* tasks)
# ---------------------------------------------------------------------------

async def test_validate_plan(r: TestResults):
    bw = load_fixture("blocksworld_p01")
    gt = build_gt_from_fixture(bw)
    dom = bw["domain_pddl"]
    prob = bw["problem_pddl"]
    oracle_plan_str = "\n".join(bw["oracle_plan"])
    bad_plan_str = "\n".join(bw["bad_plan"])

    mcp = FakeMCP(plan_sensitive_validator(bw))

    # with-tools, no tool calls
    await run_case("vp wt no-calls", r, "validate_plan", "", [], gt, mcp, dom, prob, True,
                   (False, False, rx.FR_TOOL_NOT_SELECTED))

    # with-tools, validate called with wrong shape (no plan arg)
    ok_plan_raw = json.dumps(bw["tool_output_objs"]["validate_plan_ok"])
    await run_case("vp wt wrong arg shape", r, "validate_plan", "",
                   [tc("validate_pddl_syntax", {"domain": dom, "problem": prob}, ok_plan_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_VERDICT_MISMATCH))

    # with-tools, correct shape, verdict matches gt (gt.plan_valid = True)
    await run_case("vp wt correct shape match gt", r, "validate_plan", "",
                   [tc("validate_pddl_syntax",
                       {"domain": dom, "problem": prob, "plan": oracle_plan_str},
                       ok_plan_raw)],
                   gt, mcp, dom, prob, True,
                   (True, True, rx.FR_OK))

    # with-tools, correct shape, verdict mismatches gt
    bad_plan_raw = json.dumps(bw["tool_output_objs"]["validate_plan_bad"])
    await run_case("vp wt verdict mismatch", r, "validate_plan", "",
                   [tc("validate_pddl_syntax",
                       {"domain": dom, "problem": prob, "plan": bad_plan_str},
                       bad_plan_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_VERDICT_MISMATCH))

    # with-tools, tool returns {"error": true}
    err_raw = json.dumps({"error": True, "message": "PDDL file not found: 'blocksworld'"})
    await run_case("vp wt tool error", r, "validate_plan", "",
                   [tc("validate_pddl_syntax",
                       {"domain": dom, "problem": prob, "plan": oracle_plan_str},
                       err_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_TOOL_ERROR))

    # no-tools, VERDICT: VALID matching gt=True
    await run_case("vp nt verdict valid match", r, "validate_plan",
                   "The plan looks fine.\nVERDICT: VALID", [],
                   gt, mcp, dom, prob, False,
                   (None, True, rx.FR_OK))

    # no-tools, VERDICT: INVALID mismatching gt=True
    await run_case("vp nt verdict invalid mismatch", r, "validate_plan",
                   "There's an issue.\nVERDICT: INVALID", [],
                   gt, mcp, dom, prob, False,
                   (None, False, rx.FR_VERDICT_MISMATCH))

    # no-tools, no VERDICT: line and no JSON → both paths fail
    # → FR_FORMAT_PARSE_FAIL (PR-4: replaces FR_NO_VERDICT_PARSED for
    # the JSON-first path; the latter is unreachable from check_success
    # but stays as a constant for the truncation-override test).
    await run_case("vp nt no verdict", r, "validate_plan",
                   "I'm not sure if the plan is correct.", [],
                   gt, mcp, dom, prob, False,
                   (None, False, rx.FR_FORMAT_PARSE_FAIL))

    # no-tools, structured ValidateResponse JSON → grades via Pydantic
    # path (PR-4). VALID matches truth=True → FR_OK.
    await run_case("vp nt json verdict valid (PR-4)", r, "validate_plan",
                   '{"verdict": "VALID", "reason": "all preconds met"}', [],
                   gt, mcp, dom, prob, False,
                   (None, True, rx.FR_OK))


# ---------------------------------------------------------------------------
# Validate_domain — shape: no problem, no plan
# ---------------------------------------------------------------------------

async def test_validate_domain(r: TestResults):
    bw = load_fixture("blocksworld_p01")
    gt = build_gt_from_fixture(bw)
    dom = bw["domain_pddl"]
    prob = bw["problem_pddl"]
    mcp = FakeMCP(plan_sensitive_validator(bw))

    dom_raw = json.dumps(bw["gt"]["domain_validation_obj"])

    # Domain-only call, verdict matches gt.domain_valid=True
    await run_case("vd wt domain-only ok", r, "validate_domain", "",
                   [tc("validate_pddl_syntax", {"domain": dom}, dom_raw)],
                   gt, mcp, dom, prob, True,
                   (True, True, rx.FR_OK))

    # Wrong shape — call includes problem, should be skipped by task-shape filter
    prob_raw = json.dumps(bw["gt"]["problem_validation_obj"])
    await run_case("vd wt wrong shape (has problem)", r, "validate_domain", "",
                   [tc("validate_pddl_syntax", {"domain": dom, "problem": prob}, prob_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_VERDICT_MISMATCH))


# ---------------------------------------------------------------------------
# Validate_* with negative ground truth (ISS-001 follow-up).
# Mirrors the truth=True no-tools cases above, with the truth bit flipped:
# the model is now graded against `*_valid=False` ground truth.
# Re-enabled paths in run_experiment.py:878-885 (check_success no-tools
# validate_* branch) are exercised here.
# ---------------------------------------------------------------------------

async def test_validate_negatives_no_tools(r: TestResults):
    bw = load_fixture("blocksworld_p01")
    gt_pos = build_gt_from_fixture(bw)
    dom = bw["domain_pddl"]
    prob = bw["problem_pddl"]
    mcp = FakeMCP(plan_sensitive_validator(bw))

    # Build the three negative gt fragments (one per task) the way the job
    # builder does: copy the positive gt and flip the relevant *_valid bit.
    gt_neg_dom = {**gt_pos, "domain_valid": False}
    gt_neg_prob = {**gt_pos, "problem_valid": False}
    gt_neg_plan = {**gt_pos, "plan_valid": False}

    # validate_domain — INVALID matches truth=False → success
    await run_case("vd nt verdict invalid match (gt=False)", r, "validate_domain",
                   "Saw a missing paren.\nVERDICT: INVALID", [],
                   gt_neg_dom, mcp, dom, prob, False,
                   (None, True, rx.FR_OK))

    # validate_problem — VALID mismatches truth=False
    await run_case("vp(roblem) nt verdict valid mismatch (gt=False)", r, "validate_problem",
                   "Looks fine to me.\nVERDICT: VALID", [],
                   gt_neg_prob, mcp, dom, prob, False,
                   (None, False, rx.FR_VERDICT_MISMATCH))

    # validate_plan — no VERDICT line at all and no JSON → both paths
    # fail → FR_FORMAT_PARSE_FAIL (PR-4).
    await run_case("vp nt no verdict (gt=False)", r, "validate_plan",
                   "I'm undecided about this plan.", [],
                   gt_neg_plan, mcp, dom, prob, False,
                   (None, False, rx.FR_FORMAT_PARSE_FAIL))

    # validate_plan — structured ValidateResponse JSON, INVALID matches
    # truth=False → success (PR-4 JSON-first path).
    await run_case("vp nt json verdict invalid match (PR-4, gt=False)", r, "validate_plan",
                   '{"verdict": "INVALID", "reason": "step 2 broken"}', [],
                   gt_neg_plan, mcp, dom, prob, False,
                   (None, True, rx.FR_OK))

    # validate_plan — INVALID matches truth=False → success (the bread-and-butter
    # case: model correctly identifies a broken plan).
    await run_case("vp nt verdict invalid match (gt=False)", r, "validate_plan",
                   "Step 2 has unmet preconditions.\nVERDICT: INVALID", [],
                   gt_neg_plan, mcp, dom, prob, False,
                   (None, True, rx.FR_OK))


# ---------------------------------------------------------------------------
# Simulate — B1 target
# ---------------------------------------------------------------------------

async def test_simulate(r: TestResults):
    bw = load_fixture("blocksworld_p01")
    gt = build_gt_from_fixture(bw)
    dom = bw["domain_pddl"]
    prob = bw["problem_pddl"]
    oracle_plan_str = "\n".join(bw["oracle_plan"])
    bad_plan_str = "\n".join(bw["bad_plan"])
    mcp = FakeMCP(plan_sensitive_validator(bw))

    # with-tools, no calls
    await run_case("sim wt no-calls", r, "simulate", "", [], gt, mcp, dom, prob, True,
                   (False, False, rx.FR_TOOL_NOT_SELECTED))

    # with-tools, called get_state_transition, trajectory == oracle (B1)
    trace_ok_raw = json.dumps(bw["tool_output_objs"]["get_state_transition_ok"])
    await run_case("sim wt trajectory matches oracle (B1)", r, "simulate", "",
                   [tc("get_state_transition",
                       {"domain": dom, "problem": prob, "plan": oracle_plan_str},
                       trace_ok_raw)],
                   gt, mcp, dom, prob, True,
                   (True, True, rx.FR_OK))

    # with-tools, trajectory differs from oracle → FR_RESULT_MISMATCH (B1 NEW)
    trace_bad_raw = json.dumps(bw["tool_output_objs"]["get_state_transition_bad"])
    await run_case("sim wt trajectory differs (B1 NEW)", r, "simulate", "",
                   [tc("get_state_transition",
                       {"domain": dom, "problem": prob, "plan": bad_plan_str},
                       trace_bad_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_RESULT_MISMATCH))

    # with-tools, valid=false + partial trajectory (was silently OK pre-B1)
    await run_case("sim wt valid=false partial (B1 regression)", r, "simulate", "",
                   [tc("get_state_transition",
                       {"domain": dom, "problem": prob, "plan": bad_plan_str},
                       trace_bad_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_RESULT_MISMATCH))

    # with-tools, tool returns error shape
    err_raw = json.dumps({"error": True, "message": "bad"})
    await run_case("sim wt tool error", r, "simulate", "",
                   [tc("get_state_transition",
                       {"domain": dom, "problem": prob, "plan": oracle_plan_str},
                       err_raw)],
                   gt, mcp, dom, prob, True,
                   (True, False, rx.FR_TOOL_ERROR))

    # PR-4: no-PDDL-tools simulate restored. Grader is JSON-trajectory
    # deep-equality against the oracle (same _normalize_trajectory both
    # sides). Build a model-shaped SimulateResponse from the oracle
    # trajectory so we exercise the round-trip cleanly.
    oracle_traj_obj = bw["gt"]["trace_obj"]["trajectory"]

    def _model_step(entry):
        # Convert oracle step (boolean_fluents = dict[str, bool]) to
        # the model schema (state.boolean = list of TRUE predicates).
        boolean_true = [k for k, v in entry["boolean_fluents"].items() if v]
        return {
            "step": entry["step"],
            "action": entry["action"] or "",
            "state": {
                "boolean": boolean_true,
                "numeric": entry.get("numeric_fluents") or {},
            },
        }

    model_traj_match = json.dumps({"trajectory": [_model_step(e) for e in oracle_traj_obj]})
    await run_case("sim nt json trajectory matches oracle (PR-4)", r, "simulate",
                   model_traj_match, [],
                   gt, mcp, dom, prob, False,
                   (None, True, rx.FR_OK))

    # Mismatch: drop the last step.
    model_traj_short = json.dumps({"trajectory": [_model_step(e) for e in oracle_traj_obj[:-1]]})
    await run_case("sim nt json trajectory mismatch (PR-4)", r, "simulate",
                   model_traj_short, [],
                   gt, mcp, dom, prob, False,
                   (None, False, rx.FR_RESULT_MISMATCH))

    # Malformed JSON → FR_FORMAT_PARSE_FAIL (no free-text fallback for
    # simulate; the keyword grader was the original ISS-002 problem).
    await run_case("sim nt malformed json (PR-4)", r, "simulate",
                   "Here is the state transition trace... step 0 ...", [],
                   gt, mcp, dom, prob, False,
                   (None, False, rx.FR_FORMAT_PARSE_FAIL))


# ---------------------------------------------------------------------------
# Truncation override (evaluate_one uses _apply_truncation_override)
# ---------------------------------------------------------------------------

def test_truncation_override(r: TestResults):
    if not hasattr(rx, "_apply_truncation_override"):
        # Pre-refactor: skip with a recorded failure so it surfaces.
        r.check("_apply_truncation_override exists", False,
                "helper not yet factored out of evaluate_one")
        return

    f = rx._apply_truncation_override

    # Not success + truncated + eligible reason → override to truncated
    r.check_eq("override: truncated + PLAN_INVALID",
               f(False, True, rx.FR_PLAN_INVALID), rx.FR_TRUNCATED_NO_ANSWER)
    r.check_eq("override: truncated + NO_VERDICT_PARSED",
               f(False, True, rx.FR_NO_VERDICT_PARSED), rx.FR_TRUNCATED_NO_ANSWER)
    r.check_eq("override: truncated + SIMULATE_EMPTY",
               f(False, True, rx.FR_SIMULATE_EMPTY), rx.FR_TRUNCATED_NO_ANSWER)
    r.check_eq("override: truncated + UNKNOWN",
               f(False, True, rx.FR_UNKNOWN), rx.FR_TRUNCATED_NO_ANSWER)

    # Not eligible — pins current policy
    r.check_eq("no override: truncated + VERDICT_MISMATCH",
               f(False, True, rx.FR_VERDICT_MISMATCH), rx.FR_VERDICT_MISMATCH)
    r.check_eq("no override: truncated + TOOL_ERROR",
               f(False, True, rx.FR_TOOL_ERROR), rx.FR_TOOL_ERROR)
    r.check_eq("no override: truncated + TOOL_NOT_SELECTED",
               f(False, True, rx.FR_TOOL_NOT_SELECTED), rx.FR_TOOL_NOT_SELECTED)

    # Success → never override
    r.check_eq("no override: success",
               f(True, True, rx.FR_OK), rx.FR_OK)
    # Not truncated → never override
    r.check_eq("no override: not truncated",
               f(False, False, rx.FR_PLAN_INVALID), rx.FR_PLAN_INVALID)


async def _async_main(r: TestResults):
    await test_solve(r)
    await test_validate_plan(r)
    await test_validate_domain(r)
    await test_validate_negatives_no_tools(r)
    await test_simulate(r)


def main():
    r = TestResults("test_check_success")
    asyncio.run(_async_main(r))
    test_truncation_override(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
