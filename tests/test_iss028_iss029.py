"""Tests for the ISS-028 and ISS-029 checks (tools/reanalysis/iss028_029_common.py,
iss028_goal_trailers.py, iss029_simulate_plan.py).

Small synthetic inputs only: no results data, no validator, no ground-truth cache.
The scripts' own self-checks (the frozen readout reproduced exactly) cover the data
path. The committed NUMBERS.md block is checked against the committed JSON output.

Plain-Python test (no pytest dependency), run by tests/verify.sh:
    python3 tests/test_iss028_iss029.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools" / "reanalysis"))
from _helpers import TestResults  # noqa: E402
import iss028_029_common as K  # noqa: E402
import iss028_goal_trailers as T28  # noqa: E402
import iss029_simulate_plan as T29  # noqa: E402

OUT = HERE.parent / "tools" / "reanalysis" / "out"

PROBLEM = """(define (problem p) (:domain d)
  (:objects a b c - block)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  ; (:goal (on c c)) in a comment is not the goal
  (:goal (and (on a b)
              (ON  B   c)
              (not (on c a))
              (>= (fuel) 3)))
)"""
TOOL = ("(pick-up a)", "(stack a b)")


def test_goal_atoms(r):
    g = K.goal_atoms(PROBLEM)
    r.check_eq("positive atoms, lower case, spacing collapsed", g, {"(on a b)", "(on b c)"})
    r.check("negated atom left out", "(on c a)" not in g)
    r.check("fluent under a comparison left out", "(fuel)" not in g)
    r.check_eq("forall: the body, not the variable list",
               K.goal_atoms("(define (problem p) (:goal (forall (?x - block) (and (clear ?x)))))"),
               {"(clear ?x)"})
    r.check("comment ignored", "(on c c)" not in g)
    r.check_eq("no goal section", K.goal_atoms("(define (problem p))"), frozenset())
    r.check_eq("single-atom goal", K.goal_atoms("(define (problem p) (:goal (at t l1)))"),
               {"(at t l1)"})
    r.check_eq("as_atom normalises", K.as_atom("  ( On  A b )"), "(on a b)")


def test_classify(r):
    goals = K.goal_atoms(PROBLEM)
    r.check_eq("(a) tool plan then goal facts",
               K.classify_wrong_facts(TOOL, TOOL + ("(on a b)", "(on b c)"), goals),
               (K.GOAL_TRAILER, "tool plan, then extra lines"))
    r.check_eq("(c) trailer with a non-goal line",
               K.classify_wrong_facts(TOOL, TOOL + ("(on a b)", "(clear a)"), goals),
               (K.OTHER, "tool plan, then extra lines"))
    r.check_eq("(b) same length, one action changed",
               K.classify_wrong_facts(TOOL, ("(pick-up b)", "(stack a b)"), goals),
               (K.COPY_ERROR, "same length, some actions differ"))
    r.check_eq("(c) goal facts before the plan",
               K.classify_wrong_facts(TOOL, ("(on a b)",) + TOOL, goals),
               (K.OTHER, "extra lines, then tool plan"))
    r.check_eq("(c) shorter, not a prefix",
               K.classify_wrong_facts(TOOL, ("(stack a b)",), goals), (K.OTHER, "other"))
    r.check("C4 rule agrees on (a)",
            K.c4_goal_rule(TOOL, TOOL + ("(on a b)",), PROBLEM))
    r.check("C4 rule agrees on (c)",
            not K.c4_goal_rule(TOOL, TOOL + ("(clear a)",), PROBLEM))


def test_strip(r):
    goals = K.goal_atoms(PROBLEM)
    r.check_eq("trailing goal run dropped",
               K.strip_goal_trailer(TOOL + ("(on a b)", "(on b c)"), goals), TOOL)
    r.check_eq("only the trailing run: a goal atom inside the plan stays",
               K.strip_goal_trailer(("(on a b)", "(pick-up a)", "(on b c)"), goals),
               ("(on a b)", "(pick-up a)"))
    r.check_eq("last line not a goal atom: no change", K.strip_goal_trailer(TOOL, goals), None)
    r.check_eq("nothing left: no change",
               K.strip_goal_trailer(("(on a b)", "(on b c)"), goals), None)


def _row(domain, problem, plan, model="m", variant=11):
    calls = (NS(name="get_state_transition", arguments={"plan": plan}, result="{}"),) if plan else ()
    return NS(domain=domain, problem=problem, tool_calls=calls, model_tag=model, variant=variant)


def test_run_plans(r):
    rows = ([_row("d", "p01", "(a x)\n(b y)")] * 9 + [_row("d", "p01", ["(A X)", "(c z)"])]
            + [_row("d", "p02", "(a x)")] * 8 + [_row("d", "p02", "(b y)")] * 2
            + [_row("d", "p03", None)])
    plans = T29.run_plans(rows)
    r.check_eq("90% passed one plan: it is the run plan", plans[("d", "p01")]["plan"], ("a x", "b y"))
    r.check_eq("counts", (plans[("d", "p01")]["modal"], plans[("d", "p01")]["with_plan"]), (9, 10))
    r.check_eq("80%: undetermined", plans[("d", "p02")]["plan"], None)
    r.check_eq("no plan passed: undetermined", (plans[("d", "p03")]["plan"], plans[("d", "p03")]["rows"]),
               (None, 1))
    r.check_eq("first call with a plan argument",
               T29.passed_plan(NS(tool_calls=(NS(name="validate_plan", arguments={"plan": "(q)"}),
                                              NS(name="get_state_transition", arguments={"plan": "(z)"}),
                                              NS(name="get_state_transition", arguments={"plan": "(w)"})))),
               ("z",))


def _res28():
    return {"self_check": {"checks": 15, "equal": 15}, "frozen_wrong_facts": 6,
            "by_class": {K.GOAL_TRAILER: 3, K.COPY_ERROR: 2, K.OTHER: 1},
            "by_class_model": {K.GOAL_TRAILER: {"Qwen3_5_9B": 3}, K.COPY_ERROR: {"qwen3_6_35b": 2},
                               K.OTHER: {"gemma4_26b-a4b": 1}},
            "other_by_shape": {"other": 1},
            "cells": [{"part": "A", "model": "Qwen3_5_9B", "arm": "plain", "n": 10, "k_frozen": 5,
                       "flips": 3, "stripped_still_invalid": 0},
                      {"part": "C", "model": "Qwen3_5_9B", "arm": "unaided", "n": 10, "k_frozen": 1,
                       "flips": 0, "stripped_still_invalid": 1}],
            "derived": [{"figure": "E2", "model": "Qwen3_5_9B", "frozen": 40.0, "post_hoc": 70.0},
                        {"figure": "E3", "model": "Qwen3_5_9B", "frozen": 1.0, "post_hoc": 1.0},
                        {"figure": "R4", "model": "Qwen3_5_9B", "n": 8, "k_frozen": 5,
                         "k_post_hoc": 8, "frozen": 62.5, "post_hoc": 100.0}],
            "haiku": {"overlay": "x", "solve_rows": 100, "plan_invalid": ["a p01", "depot p02"],
                      "depot_p02_is_counted": True, "raw": None}}


def test_render28(r):
    s = T28.render_numbers(_res28(), lambda m: m)
    r.check("frozen -> post hoc for the moved cell", "Qwen3_5_9B solve plain 5/10 (50.0%) → 8/10 (80.0%)" in s)
    r.check("unmoved cell not listed", "unaided (Part C)" not in s)
    r.check("still-invalid rows counted", "(1 more rows lose a goal trailer but stay invalid)." in s)
    r.check("a derived figure that moves", "E2 solve (tools plain − unaided) Qwen3_5_9B +40.0 → +70.0" in s)
    r.check("R4 as a share", "R4 (tool-verified, full answer, delivered) Qwen3_5_9B 62.5% of 8 → 100.0%" in s)
    r.check("a derived figure that does not move is not listed", "E3 solve" not in s)
    r.check("labelled post hoc and do-not-quote", "post hoc" in s and "Do NOT quote" in s)
    r.check("Haiku membership stated", "depot p02 **is one of them**" in s)
    r.check("class counts", "**3** repeat the tool's plan" in s and "**2** are copying errors" in s)


def test_render29(r):
    res = {"readout_checks": 15, "problems_total": 100, "part_c_rows": 900,
           "differ": [{"domain": "gripper", "problem": "p03", "run_len": 11, "cache_len": 11}],
           "part_c_online_ok_delivered_wrong": ["m|simulate|plain|gripper|p03||v11"],
           "part_c_cells": [{"model": "m", "n": 300, "k_frozen": 53, "flips": 1},
                            {"model": "g", "n": 300, "k_frozen": 72, "flips": 0}],
           "tool_rows_ok_with_room_delivered_wrong": []}
    s = T29.render_numbers(res, lambda m: m)
    r.check("problem count", "**1 of 100**" in s)
    r.check("frozen -> post hoc", "m simulate unaided (Part C) 53/300 (17.7%) → 54/300 (18.0%)" in s)
    r.check("unmoved cell not listed", "g simulate" not in s)
    r.check("the row is named", "`m|simulate|plain|gripper|p03||v11`" in s)


def test_committed_outputs(r):
    """The committed NUMBERS.md block equals a render of the committed JSON, and the
    JSON holds the counts it was reviewed at (counts in the record: 38 / 17 / 5)."""
    j = OUT / "iss028_goal_trailers.json"
    if not j.exists():
        r.check("committed iss028 output present", False, str(j))
        return
    res = json.loads(j.read_text())
    import gen_common
    r.check_eq("numbers_iss028.md is the render of the JSON",
               (OUT / "numbers_iss028.md").read_text(), T28.render_numbers(res, gen_common.model_name))
    r.check_eq("classes", (res["frozen_wrong_facts"], res["by_class"]),
               (38, {K.GOAL_TRAILER: 17, K.COPY_ERROR: 5, K.OTHER: 16}))
    r.check_eq("self-check cells", res["self_check"], {"checks": 24, "equal": 24})
    r.check_eq("C4 rule gives the same rows", res["c4_rule_differs"], [])


if __name__ == "__main__":
    r = TestResults("test_iss028_iss029")
    for fn in (test_goal_atoms, test_classify, test_strip, test_run_plans, test_render28,
               test_render29, test_committed_outputs):
        fn(r)
    r.report_and_exit()
