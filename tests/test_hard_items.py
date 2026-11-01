"""Unit tests for tools._hard_items (D1b harder-item mutation primitives).

Run standalone: `python3 tests/test_hard_items.py`
Or via the shell wrapper: `bash tests/verify.sh`

Pure-text tests: no MCP, no planner, no VAL. They check that the reader
finds signatures and occurrences, that each mutator makes exactly one local
edit of the intended kind, and that the plan edits do what they say.
Whether an edit is really invalid is decided by the oracle and VAL in
tools/build_hard_fixtures.py, not here.
"""

import difflib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from tools import _hard_items as H

DOMAIN = """; a comment (with parens)
(define (domain mini)
  (:requirements :strips :typing :fluents)
  (:types truck crate - object place)
  (:predicates (at ?x - truck ?p - place)
               (loaded ?c - crate ?t - truck)
               (ready))
  (:functions (fuel ?t - truck))
  (:action drive
    :parameters (?t - truck ?from ?to - place ?c - crate)
    :precondition (and (at ?t ?from) (ready) (>= (fuel ?t) 1))
    :effect (and (not (at ?t ?from)) (at ?t ?to) (decrease (fuel ?t) 1)))
  (:action load
    :parameters (?c - crate ?t - truck)
    :precondition (and (ready))
    :effect (and (loaded ?c ?t))))
"""

PROBLEM = """(define (problem mini1) (:domain mini)
  (:objects t1 t2 - truck c1 - crate p1 p2 - place)
  (:init (at t1 p1) (ready) (= (fuel t1) 3) (= (fuel t2) 0))
  (:goal (and (at t1 p2) (loaded c1 t1))))
"""

PLAN = ["(load c1 t1)", "(drive t1 p1 p2 c1)", "(drive t1 p2 p1 c1)", "(drive t1 p1 p2 c1)"]


def _one_edit(a: str, b: str) -> bool:
    """b differs from a in one contiguous region."""
    ops = [op for op in difflib.SequenceMatcher(None, a, b).get_opcodes() if op[0] != "equal"]
    return len(ops) == 1


def test_reader(r: TestResults):
    dom = H.read_domain(DOMAIN)
    r.check_eq("types", dom.types, {"object": None, "truck": "object", "crate": "object",
                                    "place": "object"})
    r.check_eq("predicate signature", dom.predicates["at"], ["truck", "place"])
    r.check_eq("0-ary predicate", dom.predicates["ready"], [])
    r.check_eq("function signature", dom.functions["fuel"], ["truck"])
    r.check_eq("two actions", [a.name for a in dom.actions], ["drive", "load"])
    heads = sorted((o.kind, o.head.low, o.section) for o in dom.occs)
    r.check("finds the function term inside >=",
            ("func", "fuel", "precondition") in heads, str(heads))
    r.check("finds the atom inside not", heads.count(("pred", "at", "effect")) == 2, str(heads))
    r.check("truck and place are incomparable", dom.incomparable("truck", "place"))
    r.check("object is comparable with all", not dom.incomparable("object", "truck"))
    prob = H.read_problem(PROBLEM, dom)
    r.check_eq("object types", prob.object_types(dom),
               {"t1": "truck", "t2": "truck", "c1": "crate", "p1": "place", "p2": "place"})
    r.check_eq("init + goal occurrences", len(prob.occs), 6)


def test_parse_errors(r: TestResults):
    for bad in ("(define (domain x)", "(define (domain x)))"):
        try:
            H.parse_sexp(bad)
            r.check(f"unbalanced {bad!r} raises", False, "no error")
        except ValueError:
            r.check(f"unbalanced {bad!r} raises", True)


def test_names(r: TestResults):
    rng = random.Random(0)
    nm = H.near_miss("holding", {"holding", "clear"}, rng)
    r.check("near_miss is a one-letter typo or plural",
            nm is not None and (len(nm) == 6 or nm == "holdings"), str(nm))
    r.check_eq("short names only get a plural", H.near_miss("at", set(), rng), "ats")
    r.check_eq("case kept", H.near_miss("Depot", set(), random.Random(3))[0], "D")
    r.check("never a declared name", H.near_miss("on", {"ons"}, rng) is None)
    r.check_eq("next object after b6", H.next_object_name("b2", {"b1", "b2", "b6"}), "b7")
    r.check_eq("no digits -> suffix 2", H.next_object_name("rover", {"rover"}), "rover2")


def test_domain_mutators(r: TestResults):
    dom = H.read_domain(DOMAIN)
    for kind, fn in H.DOMAIN_MUTATORS.items():
        m = fn(dom, random.Random(1))
        r.check(f"{kind}: produced", m is not None)
        if m is None:
            continue
        r.check_eq(f"{kind}: kind recorded", m.kind, kind)
        r.check(f"{kind}: one local edit", _one_edit(DOMAIN, m.text), m.detail)
        r.check(f"{kind}: comment kept", m.text.startswith("; a comment (with parens)"))
        H.parse_sexp(m.text)        # still balanced
    m = H.dom_type_mismatch(dom, random.Random(1))
    r.check("type mismatch uses an incomparable type",
            dom.incomparable(m.detail["used_type"], m.detail["declared_type"]), m.detail)
    m = H.dom_wrong_arity(dom, random.Random(1))
    r.check("wrong arity changes the argument count by one",
            abs(m.detail["used_arity"] - m.detail["declared_arity"]) == 1, m.detail)


def test_problem_mutators(r: TestResults):
    dom = H.read_domain(DOMAIN)
    prob = H.read_problem(PROBLEM, dom)
    for kind, fn in H.PROBLEM_MUTATORS.items():
        m = fn(dom, prob, random.Random(2))
        r.check(f"{kind}: produced", m is not None)
        if m is None:
            continue
        r.check(f"{kind}: one local edit", _one_edit(PROBLEM, m.text), m.detail)
        H.parse_sexp(m.text)
    m = H.prob_undefined_object(dom, prob, random.Random(2))
    r.check("undefined object is not declared",
            m.detail["used"] not in prob.object_types(dom), m.detail)
    m = H.prob_type_mismatch(dom, prob, random.Random(2))
    r.check("problem type mismatch uses an incomparable type",
            dom.incomparable(m.detail["used_type"], m.detail["declared_type"]), m.detail)


def test_single_type_domain_has_no_type_mismatch(r: TestResults):
    one = DOMAIN.replace("(:types truck crate - object place)", "(:types thing)")
    one = one.replace(" - truck", " - thing").replace(" - place", " - thing")
    one = one.replace(" - crate", " - thing")
    dom = H.read_domain(one)
    r.check("no incomparable pair -> None", H.dom_type_mismatch(dom, random.Random(0)) is None)


def test_plan_edits(r: TestResults):
    out, e = H.plan_delete(PLAN, 2)
    r.check_eq("delete removes step 2", out, [PLAN[0]] + PLAN[2:])
    r.check_eq("delete records the step", e["removed"], PLAN[1])
    out, e = H.plan_swap(PLAN, 1)
    r.check_eq("swap 1,2", out[:2], [PLAN[1], PLAN[0]])
    r.check("swap of equal neighbours refused", H.plan_swap(["(a)", "(a)"], 1) is None)
    dom = H.read_domain(DOMAIN)
    objtypes = H.read_problem(PROBLEM, dom).object_types(dom)
    reps = H.plan_replacements(PLAN, 2, dom, objtypes)
    hows = {e["how"] for _, e in reps}
    r.check("sibling grounding offered", "sibling_grounding" in hows, str(reps))
    r.check("every replacement changes only step 2",
            all(s[:1] == PLAN[:1] and s[2:] == PLAN[2:] and s[1] != PLAN[1] for s, _ in reps))
    reps_load = H.plan_replacements(PLAN, 1, dom, objtypes)
    r.check("no other action fits (load c1 t1)",
            all(e["how"] == "sibling_grounding" for _, e in reps_load))
    r.check_eq("plan text round trip", H.plan_steps(H.plan_text(PLAN)), PLAN)
    r.check_eq("plan_steps normalises", H.plan_steps("(A  b)\n\n ; c\n(c d)\n"), ["(a b)", "(c d)"])


def main():
    r = TestResults("test_hard_items")
    test_reader(r)
    test_parse_errors(r)
    test_names(r)
    test_domain_mutators(r)
    test_problem_mutators(r)
    test_single_type_domain_has_no_type_mismatch(r)
    test_plan_edits(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
