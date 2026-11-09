"""Unit tests for tools._hard_items (mutation primitives for the D1b new item kinds).

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


# ---------------------------------------------------------------------------
# The three trees (tools/build_hard_fixtures.py tree helpers + the committed
# trees). No harness change: everything below goes through main's loader.
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
TREES = ("domains-hard", "domains-hard-vd-a", "domains-hard-vd-b")


def _mini_tree(root: Path, folders: dict) -> None:
    """folders: {name: [file names]}; each file holds a one-line comment."""
    for name, files in folders.items():
        d = root / "classical" / name
        d.mkdir(parents=True)
        for f in files:
            (d / f).write_text(f"; {f}\n")


def test_tree_helpers(r: TestResults):
    import tempfile
    from tools import build_hard_fixtures as B
    out = Path("/x/domains-hard")
    r.check_eq("vd tree names", [p.name for p in B.vd_dirs_for(out, 2)],
               ["domains-hard-vd-a", "domains-hard-vd-b"])
    r.check_eq("vd trees sit next to the main tree",
               {p.parent for p in B.vd_dirs_for(out, 3)}, {Path("/x")})
    with tempfile.TemporaryDirectory() as td:
        a, b, m = Path(td) / "a", Path(td) / "b", Path(td) / "m"
        _mini_tree(a, {"d1": ["domain.pddl", "domain_neg.pddl", "p01.pddl"],
                       "d2": ["domain.pddl", "domain_neg.pddl", "p03.pddl"]})
        _mini_tree(b, {"d1": ["domain.pddl", "domain_neg.pddl", "p02.pddl"]})
        _mini_tree(m, {"d1": ["domain.pddl", "domain_neg.pddl", "domain_neg02.pddl",
                              "p01.pddl", "p02.pddl"]})
        r.check_eq("stray domain_neg02 found", B.stray_negatives(m),
                   ["classical/d1/domain_neg02.pddl"])
        r.check_eq("no stray in a clean tree", B.stray_negatives(a), [])
        r.check_eq("main's loader gives 2:1 on a two-problem folder (why there are two trees)",
                   B.validate_domain_grid(m), {"d1": {"valid": 2, "invalid": 1}})
        ga, gb = B.validate_domain_grid(a), B.validate_domain_grid(b)
        r.check_eq("one-problem folder is 1:1", ga["d1"], {"valid": 1, "invalid": 1})
        r.check_eq("a + b combined", B.combine_grids([ga, gb]),
                   {"d1": {"valid": 2, "invalid": 2}, "d2": {"valid": 1, "invalid": 1}})
        items = [{"path": f"classical/d1/{f}", "task": "t", "label": "valid", "kind": "k"}
                 for f in ("domain.pddl", "domain_neg.pddl")]
        try:
            B.tree_manifest(b, items)
            r.check("manifest missing a file refused", False, "no error")
        except SystemExit:
            r.check("manifest missing a file refused", True)
        items.append({"path": "classical/d1/p02.pddl", "task": "t", "label": "invalid",
                      "kind": "k2"})
        m_ = B.tree_manifest(b, items)
        r.check_eq("manifest counts", m_["counts"], {"t/invalid": 1, "t/valid": 2})
        r.check("manifest has sha256 per item",
                all(len(it["sha256"]) == 64 for it in m_["items"]))


def test_committed_trees(r: TestResults):
    """The committed trees: hashes match their manifests, no file the frozen
    loader would skip, validate_domain balanced over trees a and b together,
    and the other tasks balanced in domains-hard."""
    import hashlib
    import json
    from pddl_eval.domains import load_domains
    from tools import build_hard_fixtures as B
    if not all((REPO / t).is_dir() for t in TREES):
        r.check("committed trees present", False, str(TREES))
        return
    loaded = {}
    for t in TREES:
        root = REPO / t
        man = json.loads((root / "manifest.json").read_text())
        want = (root / "manifest.sha256").read_text().split()[0]
        r.check_eq(f"{t}: manifest.sha256", hashlib.sha256(
            (root / "manifest.json").read_bytes()).hexdigest(), want)
        on_disk = sorted(str(p.relative_to(root)) for p in root.rglob("*")
                         if p.is_file() and p.parent != root)
        r.check_eq(f"{t}: manifest lists every file", sorted(i["path"] for i in man["items"]),
                   on_disk)
        bad = [i["path"] for i in man["items"]
               if hashlib.sha256((root / i["path"]).read_bytes()).hexdigest() != i["sha256"]]
        r.check_eq(f"{t}: every file matches its sha256", bad, [])
        r.check_eq(f"{t}: no domain_neg<digits>.pddl", B.stray_negatives(root), [])
        r.check_eq(f"{t}: VAL re-check agrees on every item",
                   man["val_recheck"].get("disagree", 0), 0)
        r.check(f"{t}: every invalid item rejected by the oracle and VAL",
                all(i["oracle"]["verdict"] is False and i["val"]["verdict"] == "invalid"
                    for i in man["items"] if i["label"] == "invalid"))
        loaded[t] = load_domains(root)
    main_m = json.loads((REPO / TREES[0] / "manifest.json").read_text())
    for t in TREES[1:]:
        r.check_eq(f"main manifest names {t}'s hash",
                   main_m["validate_domain_trees"][t]["manifest_sha256"],
                   (REPO / t / "manifest.sha256").read_text().split()[0])
    hard, va, vb = (loaded[t] for t in TREES)
    combined = B.combine_grids([B.validate_domain_grid(REPO / t) for t in TREES[1:]])
    r.check_eq("validate_domain: a + b covers every domain", sorted(combined), sorted(hard))
    r.check("validate_domain: a + b balanced in every domain",
            all(g["valid"] == g["invalid"] for g in combined.values()), str(combined))
    for name, d in hard.items():
        pa, pb = set(va[name]["problems"]), set(vb[name]["problems"])
        r.check_eq(f"{name}: a and b hold the main tree's problems, one each",
                   (sorted(pa | pb), len(pa), len(pb), pa & pb),
                   (sorted(d["problems"]), 1, 1, set()))
        r.check_eq(f"{name}: tree a's invalid domain is the main tree's",
                   va[name]["negatives"]["domain"], d["negatives"]["domain"])
        r.check(f"{name}: trees a and b have different invalid domains",
                va[name]["negatives"]["domain"] != vb[name]["negatives"]["domain"])
        r.check_eq(f"{name}: same valid domain in all trees",
                   {va[name]["domain"], vb[name]["domain"]}, {d["domain"]})
        negs = d["negatives"]
        r.check_eq(f"{name}: invalid problems == valid problems",
                   len(negs["problems"]), len(d["problems"]))
        for p, pp in negs["plans_per_problem"].items():
            r.check_eq(f"{name}/{p}: invalid plans == valid plans",
                       len(pp["invalid"]), len(pp["valid"]))
            r.check_eq(f"{name}/{p}: valid plans distinct",
                       len(set(pp["valid"])), len(pp["valid"]))


def main():
    r = TestResults("test_hard_items")
    test_reader(r)
    test_parse_errors(r)
    test_names(r)
    test_domain_mutators(r)
    test_problem_mutators(r)
    test_single_type_domain_has_no_type_mismatch(r)
    test_plan_edits(r)
    test_tree_helpers(r)
    test_committed_trees(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
