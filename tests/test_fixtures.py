"""Unit tests for tools._taxonomies (PR-3 fixture-mutation primitives).

Run standalone: `python3 tests/test_fixtures.py`
Or via the shell wrapper: `bash tests/verify.sh`

These are pure-text tests — no MCP, no planner. They verify that each
mutator transforms its input in the expected structural way. Whether
the validator agrees the mutation is invalid is checked by the
build_fixtures generator at runtime, not here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from tools import _taxonomies


SAMPLE_PLAN = """(unstack b2 b1)
(put_down b2)
(pick_up b3)
(stack b3 b1)
"""

SAMPLE_PROBLEM = """(define (problem bw_rand_3)
(:domain blocksworld)
(:objects b1 b2 b3 - block)
(:init
(handempty)
(ontable b1)
(on b2 b1)
(ontable b3)
(clear b2)
(clear b3)
)
(:goal
(and
(on b3 b1))
)
)
"""

SAMPLE_DOMAIN = """(define (domain blocksworld)
  (:requirements :strips :typing)
  (:types block)
  (:predicates (on ?x - block ?y - block)
         (ontable ?x - block))
  (:action pick_up
       :parameters (?x - block)
       :precondition (and (clear ?x))
       :effect (and (holding ?x))))
"""


def test_plan_truncate(r: TestResults):
    out = _taxonomies.plan_truncate(SAMPLE_PLAN, n_drop=1)
    r.check_eq(
        "plan_truncate drops last action",
        out.strip().splitlines(),
        ["(unstack b2 b1)", "(put_down b2)", "(pick_up b3)"],
    )
    out2 = _taxonomies.plan_truncate(SAMPLE_PLAN, n_drop=2)
    r.check_eq("plan_truncate n_drop=2", len(out2.strip().splitlines()), 2)
    too_many = _taxonomies.plan_truncate(SAMPLE_PLAN, n_drop=99)
    r.check_eq("plan_truncate n_drop>len returns input unchanged", too_many, SAMPLE_PLAN)


def test_plan_drop_step_k(r: TestResults):
    out = _taxonomies.plan_drop_step_k(SAMPLE_PLAN, k=1)
    r.check("plan_drop_step_k removes step 1",
            "(put_down b2)" not in out, f"got: {out!r}")
    r.check_eq(
        "plan_drop_step_k preserves other steps",
        out.strip().splitlines(),
        ["(unstack b2 b1)", "(pick_up b3)", "(stack b3 b1)"],
    )
    # k = invalid (out of action_idxs) → input unchanged
    out_no = _taxonomies.plan_drop_step_k(SAMPLE_PLAN, k=99)
    r.check_eq("plan_drop_step_k k=99 unchanged", out_no, SAMPLE_PLAN)


def test_plan_swap_args(r: TestResults):
    out = _taxonomies.plan_swap_args(SAMPLE_PLAN, k=0)
    r.check("plan_swap_args swaps b2/b1 in unstack",
            "(unstack b1 b2)" in out, f"got: {out!r}")
    # 1-arg actions should be left alone
    one_arg_plan = "(put_down b2)\n"
    out_one = _taxonomies.plan_swap_args(one_arg_plan, k=0)
    r.check_eq("plan_swap_args 1-arg action unchanged", out_one, one_arg_plan)


def test_plan_duplicate_step(r: TestResults):
    out = _taxonomies.plan_duplicate_step(SAMPLE_PLAN, k=0)
    lines = out.strip().splitlines()
    r.check_eq("plan_duplicate_step adds 1 line", len(lines), 5)
    r.check_eq("plan_duplicate_step duplicates step 0",
               lines[:2], ["(unstack b2 b1)", "(unstack b2 b1)"])


def test_problem_drop_goal(r: TestResults):
    out = _taxonomies.problem_drop_goal(SAMPLE_PROBLEM)
    r.check(":goal block removed", "(:goal" not in out, f"got: {out!r}")
    r.check(":init still present", "(:init" in out, f"got: {out!r}")


def test_problem_inject_undefined_object(r: TestResults):
    out = _taxonomies.problem_inject_undefined_object(SAMPLE_PROBLEM, name="zzz")
    r.check("undefined object inserted", " zzz)" in out, f"got: {out!r}")
    r.check_eq("output longer than input", len(out) > len(SAMPLE_PROBLEM), True)


def test_problem_corrupt_paren(r: TestResults):
    out = _taxonomies.problem_corrupt_paren(SAMPLE_PROBLEM)
    r.check_eq(
        "extra ) appended before trailing newline",
        out.endswith(")\n"),
        True,
    )
    r.check_eq("length increased by 1", len(out), len(SAMPLE_PROBLEM) + 1)


def test_problem_undefined_goal_predicate(r: TestResults):
    out = _taxonomies.problem_undefined_goal_predicate(SAMPLE_PROBLEM, fake="zzz_pred")
    r.check("zzz_pred substituted in goal", "(zzz_pred " in out, f"got: {out!r}")
    r.check(":goal still present", "(:goal" in out, f"got: {out!r}")
    # The original `on` predicate appears inside :init too — that one
    # must remain intact (only the goal-block occurrence is replaced).
    r.check(":init `on` predicate intact", "(on b2 b1)" in out, f"got: {out!r}")


def test_domain_corrupt_paren(r: TestResults):
    out = _taxonomies.domain_corrupt_paren(SAMPLE_DOMAIN)
    r.check_eq("extra ) appended", out.endswith(")\n"), True)
    r.check_eq("length+1", len(out), len(SAMPLE_DOMAIN) + 1)


def test_domain_undefined_predicate_in_effect(r: TestResults):
    out = _taxonomies.domain_undefined_predicate_in_effect(SAMPLE_DOMAIN, fake="zzz_pred")
    r.check(":effect contains injected pred",
            "(zzz_pred ?x)" in out, f"got: {out!r}")


def test_domain_drop_predicates_block(r: TestResults):
    out = _taxonomies.domain_drop_predicates_block(SAMPLE_DOMAIN)
    r.check_eq(":predicates block dropped",
               "(:predicates" in out, False)
    r.check(":action still present",
            "(:action" in out, f"got: {out!r}")


def test_strip_balanced_block_no_match(r: TestResults):
    text = "(define (problem foo))"
    out = _taxonomies._strip_balanced_block(text, ":missing")
    r.check_eq("no match → unchanged", out, text)


# ---------------------------------------------------------------------------
# Loader smoke test — exercises the new flat-layout shape against the
# legacy-fallback path so we catch shape regressions early.
# ---------------------------------------------------------------------------


def test_loader_shape_legacy_layout(r: TestResults):
    # The repo currently has the legacy layout for all 10 domains; the
    # loader must normalize to the new shape (lists of length 1 for
    # negatives.problems and plans_per_problem.<pname>.invalid; v1 single
    # element in plans_per_problem.<pname>.valid).
    from pddl_eval.domains import load_domains  # local import: keep test module light
    domains_dir = Path(__file__).resolve().parent.parent / "domains"
    domains = load_domains(domains_dir)
    r.check("loader returned at least 10 domains", len(domains) >= 10, f"got {len(domains)}")
    bw = domains.get("blocksworld")
    r.check("blocksworld present", bw is not None, "missing blocksworld")
    if not bw:
        return
    r.check_eq("blocksworld.type", bw["type"], "classical")
    r.check("blocksworld.problems contains p01",
            "p01" in bw["problems"], f"got {list(bw['problems'])}")
    negs = bw["negatives"]
    r.check("blocksworld.negatives.domain populated",
            negs["domain"] is not None, "missing")
    r.check("blocksworld.negatives.problems is list",
            isinstance(negs["problems"], list), f"got {type(negs['problems'])}")
    r.check_eq("blocksworld.negatives.problems len ≥ 1",
               len(negs["problems"]) >= 1, True)
    plans = negs["plans_per_problem"]
    r.check("plans_per_problem keyed by pname",
            "p01" in plans, f"got {list(plans)}")
    r.check("p01 has at least 1 valid plan (legacy = 1)",
            len(plans["p01"]["valid"]) >= 1, "got 0")
    r.check("p01 has at least 1 invalid plan (legacy = 1)",
            len(plans["p01"]["invalid"]) >= 1, "got 0")


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def main():
    r = TestResults("test_fixtures")
    test_plan_truncate(r)
    test_plan_drop_step_k(r)
    test_plan_swap_args(r)
    test_plan_duplicate_step(r)
    test_problem_drop_goal(r)
    test_problem_inject_undefined_object(r)
    test_problem_corrupt_paren(r)
    test_problem_undefined_goal_predicate(r)
    test_domain_corrupt_paren(r)
    test_domain_undefined_predicate_in_effect(r)
    test_domain_drop_predicates_block(r)
    test_strip_balanced_block_no_match(r)
    test_loader_shape_legacy_layout(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
