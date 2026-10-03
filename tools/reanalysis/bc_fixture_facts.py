"""C11 — measured facts about the test data (domains/), for the data-description
gap. Read-only; no MCP, no model calls.

What it measures
  1. file inventory per domain and the trial grid it implies per task;
  2. which mutation produced each invalid fixture, recovered by re-applying the
     generator's own pure-text mutators (tools/_taxonomies.py) to the source
     file and by structural comparison where the mutator is randomised;
  3. size distributions: declared objects per problem, plan length, prompt
     characters per task;
  4. the difficulty-bin cut points, recomputed exactly as
     .claude/skills/analyzer/scripts/rq_deck.py:508-512 does (row-weighted
     tertiles, floor of the 1/3 and 2/3 quantiles, bins <=c1 / (c1, c2] / >c2);
  5. how many of the committed "valid plan" files are distinct.

    python3 tools/reanalysis/bc_fixture_facts.py

Writes out/breakdowns_cost/fixture_facts.md (+ fixture_invalid_types.csv).
"""
from __future__ import annotations

import csv
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bc_common as C  # noqa: E402
from tools import _taxonomies as T  # noqa: E402
from pddl_eval.domains import load_domains  # noqa: E402
from pddl_eval.runner import build_messages  # noqa: E402


def lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def obj_count(text: str) -> int | None:
    """Same rule as analyzer gen_meta.py:66-96 (names before each '-' are
    objects, the token after '-' is a type; None when :objects or :init is
    missing)."""
    if not (re.search(r"\(:objects\b", text, re.I) and re.search(r"\(:init\b", text, re.I)):
        return None
    m = re.search(r"\(:objects\b", text, re.I)
    i, depth, out = m.end(), 1, []
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        else:
            out.append(ch)
        i += 1
    count, expect_type = 0, False
    for tok in "".join(out).split():
        if tok == "-":
            expect_type = True
        elif expect_type:
            expect_type = False
        else:
            count += 1
    return count


def _paren_delta(text: str) -> int:
    """closing minus opening parentheses (comments stripped)."""
    body = re.sub(r";[^\n]*", "", text)
    return body.count(")") - body.count("(")


def _symbols(text: str) -> set[str]:
    return set(re.findall(r"\(\s*([A-Za-z][\w-]*)", re.sub(r";[^\n]*", "", text)))


def classify_domain_neg(pos: str, neg: str) -> str:
    """Structural: the generator's three mutators (build_fixtures.py:582-586)
    plus the shapes found in the ten domains inherited from the 2025 dataset,
    whose domain_neg.pddl was migrated (build_fixtures.py:203), not generated."""
    if "undef_pred_xyz" in neg:
        return "undeclared predicate in an effect (generator)"
    if not re.search(r"\(:predicates\b", neg):
        return ":predicates block removed (generator)"
    d = _paren_delta(neg) - _paren_delta(pos)
    if d == 1:
        return "one extra closing paren"
    if d < 0:
        return "missing closing paren(s)"
    extra = _symbols(neg) - _symbols(pos)
    if extra:
        return "undeclared predicate used in a precondition or effect (inherited)"
    if neg.count(" - ") < pos.count(" - "):
        return "'-' dropped from a typed parameter list (inherited)"
    return "other"


def classify_problem_neg(p01: str, neg: str) -> str:
    """Structural version of build_fixtures.py:505-512 (PROBLEM_MUTATORS) and
    the compound pad at :553; the residue is the inherited n01.pddl of the ten
    2025-dataset domains (migrated from p01_0.pddl, build_fixtures.py:205-208)."""
    d = _paren_delta(neg) - _paren_delta(p01)
    if "undef_obj_xyz" in neg:
        return "undeclared object in :init"
    if "undef_pred_xyz" in neg:
        return "undefined predicate in :goal"
    if not re.search(r"\(:goal\b", neg):
        return "missing :goal + one extra closing paren" if d == 1 else "missing :goal"
    if not re.search(r"\(:objects\b", neg):
        return ":objects block removed"
    if not re.search(r"\(:init\b", neg):
        return ":init block removed"
    if d == 1 and neg.replace(" ", "").replace("\n", "") == (
            p01.replace(" ", "").replace("\n", "") + ")"):
        return "one extra closing paren"
    return "inherited hand-made n01 (see list)"


def classify_plan_neg(v1: str, bad: str) -> str:
    a, b = lines(v1), lines(bad)
    if len(b) < len(a) and b == a[:len(b)]:
        return f"tail truncated (-{len(a) - len(b)})"
    if len(b) == len(a) - 1:
        for k in range(len(a)):
            if a[:k] + a[k + 1:] == b:
                return "one mid-plan step dropped"
    if len(b) == len(a) + 1:
        for k in range(len(a)):
            if a[:k + 1] + [a[k]] + a[k + 1:] == b:
                return "one step duplicated"
    if len(b) == len(a):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            ta, tb = a[diff[0]].strip("()").split(), b[diff[0]].strip("()").split()
            if (len(ta) == len(tb) and len(ta) >= 3 and ta[0] == tb[0]
                    and ta[1] == tb[2] and ta[2] == tb[1] and ta[3:] == tb[3:]):
                return "first two arguments swapped in one step"
    return "inherited hand-made b1 plan (shortened and/or altered)"


def dist(vals: list[float]) -> str:
    vals = sorted(vals)
    q = np.quantile(vals, [0.25, 0.5, 0.75])
    return (f"min {vals[0]:g} / q1 {q[0]:g} / median {q[1]:g} / q3 {q[2]:g} / "
            f"max {vals[-1]:g} (mean {st.mean(vals):.1f}, n={len(vals)})")


def main() -> int:
    track = C.domain_track()
    domains = sorted(track, key=lambda d: (track[d], d))
    md: list[str] = ["# Fixture facts (measured from domains/)", ""]

    # ---------------------------------------------------------------- 1 inventory
    inv = Counter()
    for d in domains:
        ddir = C.DOMAINS_DIR / track[d] / d
        inv["domains"] += 1
        inv["valid domain files"] += (ddir / "domain.pddl").exists()
        inv["invalid domain files"] += (ddir / "domain_neg.pddl").exists()
        inv["valid problems"] += len(list(ddir.glob("p[0-9][0-9].pddl")))
        inv["invalid problems"] += len(list(ddir.glob("n[0-9][0-9].pddl")))
        inv["valid plan files"] += len(list(ddir.glob("p*_v[0-9].plan")))
        inv["invalid plan files"] += len(list(ddir.glob("p*_b[0-9].plan")))
    md += ["## 1. Inventory", "", C.md_table(["item", "count"], [[k, v] for k, v in inv.items()]), ""]

    # ---------------------------------------------------------------- 2 invalid types
    type_rows = []
    dom_types, prob_types, plan_types = Counter(), Counter(), Counter()
    prob_by_track, plan_by_track = defaultdict(Counter), defaultdict(Counter)
    for d in domains:
        ddir = C.DOMAINS_DIR / track[d] / d
        k = classify_domain_neg((ddir / "domain.pddl").read_text(),
                                (ddir / "domain_neg.pddl").read_text())
        dom_types[k] += 1
        type_rows.append({"domain": d, "track": track[d], "fixture": "domain_neg.pddl",
                          "kind": "domain", "type": k})
        p01 = (ddir / "p01.pddl").read_text()
        for f in sorted(ddir.glob("n[0-9][0-9].pddl")):
            k = classify_problem_neg(p01, f.read_text())
            prob_types[k] += 1
            prob_by_track[track[d]][k] += 1
            type_rows.append({"domain": d, "track": track[d], "fixture": f.name,
                              "kind": "problem", "type": k})
        for f in sorted(ddir.glob("p*_b[0-9].plan")):
            pname = f.name.split("_")[0]
            k = classify_plan_neg((ddir / f"{pname}_v1.plan").read_text(), f.read_text())
            kk = re.sub(r" \(-\d+\)", "", k)
            plan_types[k] += 1
            plan_by_track[track[d]][kk] += 1
            type_rows.append({"domain": d, "track": track[d], "fixture": f.name,
                              "kind": "plan", "type": k})
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (C.OUT_DIR / "fixture_invalid_types.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(type_rows[0].keys()))
        w.writeheader()
        w.writerows(type_rows)
    md += ["## 2. What the invalid fixtures contain (structural classification against the source file)", "",
           "Invalid domains (1 per domain, 20 total):", "",
           C.md_table(["error type", "files"], sorted(dom_types.items(), key=lambda x: -x[1])), "",
           "Invalid problems (5 per domain, 100 total; every one is a mutation of that "
           "domain's p01.pddl):", "",
           C.md_table(["error type", "files", "classical", "numeric"],
                      [[k, v, prob_by_track["classical"][k], prob_by_track["numeric"][k]]
                       for k, v in sorted(prob_types.items(), key=lambda x: -x[1])]), "",
           "Invalid plans (5 per problem, 500 total; every one is a mutation of that "
           "problem's v1 plan):", "",
           C.md_table(["error type", "files"], sorted(plan_types.items(), key=lambda x: -x[1])), "",
           "Same, tail truncations merged, by track:", "",
           C.md_table(["error type", "classical", "numeric"],
                      [[k, plan_by_track["classical"][k], plan_by_track["numeric"][k]]
                       for k in sorted(set(plan_by_track["classical"]) | set(plan_by_track["numeric"]))]),
           ""]

    # ---------------------------------------------------------------- 3 sizes
    objs, plen, dchars, nact = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    distinct_valid = defaultdict(list)
    bad_len_delta = Counter()
    per_dom_rows = []
    for d in domains:
        ddir = C.DOMAINS_DIR / track[d] / d
        dtext = (ddir / "domain.pddl").read_text()
        dchars[track[d]].append(len(dtext))
        nact[track[d]].append(len(re.findall(r"\(:action\b", dtext, re.I)))
        o_d, l_d = [], []
        for pf in sorted(ddir.glob("p[0-9][0-9].pddl")):
            oc = obj_count(pf.read_text())
            objs[track[d]].append(oc)
            o_d.append(oc)
            v = [(ddir / f"{pf.stem}_v{i}.plan").read_text() for i in range(1, 6)]
            L = len(lines(v[0]))
            plen[track[d]].append(L)
            l_d.append(L)
            distinct_valid[track[d]].append(len(set(v)))
            for i in range(1, 6):
                b = len(lines((ddir / f"{pf.stem}_b{i}.plan").read_text()))
                bad_len_delta[b - L] += 1
        per_dom_rows.append([d, track[d], len(dtext), nact[track[d]][-1],
                             f"{min(o_d)}-{max(o_d)}", f"{min(l_d)}-{max(l_d)}"])
    md += ["## 3. Sizes", "",
           C.md_table(["quantity", "classical (10 domains, 50 problems)",
                       "numeric (10 domains, 50 problems)", "all"],
                      [["declared objects per valid problem", dist(objs["classical"]),
                        dist(objs["numeric"]), dist(objs["classical"] + objs["numeric"])],
                       ["reference plan length, steps (v1 plan)", dist(plen["classical"]),
                        dist(plen["numeric"]), dist(plen["classical"] + plen["numeric"])],
                       ["domain file size, characters", dist(dchars["classical"]),
                        dist(dchars["numeric"]), dist(dchars["classical"] + dchars["numeric"])],
                       ["actions per domain", dist(nact["classical"]), dist(nact["numeric"]),
                        dist(nact["classical"] + nact["numeric"])],
                       ["distinct files among the 5 valid plans of a problem",
                        str(dict(sorted(Counter(distinct_valid["classical"]).items()))),
                        str(dict(sorted(Counter(distinct_valid["numeric"]).items()))), ""]]), "",
           "Invalid plan length minus its v1 plan length (steps): "
           + ", ".join(f"{k:+d}: {v}" for k, v in sorted(bad_len_delta.items())), "",
           C.md_table(["domain", "track", "domain chars", "actions", "objects (min-max over p01..p05)",
                       "plan length (min-max)"], per_dom_rows), ""]

    # prompt sizes (characters of system + user text), v11, from the harness builder
    doms = load_domains(C.DOMAINS_DIR)
    psize = defaultdict(list)
    for d, info in doms.items():
        ddir = C.DOMAINS_DIR / info["type"] / d
        for pname, ppddl in info["problems"].items():
            plan = (ddir / f"{pname}_v1.plan").read_text()
            for task in C.TASKS:
                msgs = build_messages(task, info["domain"], ppddl, 11, False, {"plan": plan})
                psize[task].append(len(msgs[0]["content"]) + len(msgs[1]["content"]))
    md += ["Prompt size in characters (system + user, wording v11, valid fixtures, "
           "built with `pddl_eval.runner.build_messages`):", "",
           C.md_table(["task", "characters"], [[t, dist(psize[t])] for t in C.TASKS]), ""]

    # ---------------------------------------------------------------- 4 bins
    md += ["## 4. Difficulty-bin cut points (recomputed as rq_deck.py:493-512)", "",
           "Rows = the three headline models, think off, arms no-tools and tools-steered "
           "(equal weight per instance x wording). Bins: low = value <= c1, "
           "mid = c1 < value <= c2, high = value > c2.", ""]
    meta = {}
    for d in domains:
        ddir = C.DOMAINS_DIR / track[d] / d
        for pf in sorted(list(ddir.glob("p[0-9][0-9].pddl")) + list(ddir.glob("n[0-9][0-9].pddl"))):
            pl = {}
            for var in [f"v{i}" for i in range(1, 6)] + [f"b{i}" for i in range(1, 6)]:
                f = ddir / f"{pf.stem}_{var}.plan"
                if f.exists():
                    pl[var] = len(lines(f.read_text()))
            valid = [pl[v] for v in pl if v.startswith("v")]
            meta[f"{d}/{pf.stem}"] = {"obj": obj_count(pf.read_text()), "plan_len": pl,
                                      "ref_len": min(valid) if valid else None}
    cells = C.open_cells()
    rows_all = [r for rows in cells.values() for r in rows if r["arm"] in ("nt-neut", "tl-ster")]
    brow = []
    for rq, tasks in (("plan length", ["solve", "validate_plan", "simulate"]),
                      ("object count", ["solve", "validate_plan", "validate_problem", "simulate"])):
        for task in tasks:
            vals = []
            for r in rows_all:
                if r["task"] != task:
                    continue
                if task == "validate_plan" and not r["plan_label"].startswith("v"):
                    continue
                m = meta.get(f"{r['domain']}/{r['problem']}")
                if not m:
                    continue
                if rq == "object count":
                    v = m["obj"]
                elif task in ("solve", "simulate"):
                    v = m["ref_len"]
                else:
                    v = m["plan_len"].get(r["plan_label"])
                if v is not None:
                    vals.append(v)
            arr = np.array(vals)
            c1, c2 = (float(x) for x in np.floor(np.quantile(arr, [1 / 3, 2 / 3])))
            n = [int((arr <= c1).sum()), int(((arr > c1) & (arr <= c2)).sum()), int((arr > c2).sum())]
            brow.append([rq, task, f"<= {int(c1)}", f"{int(c1) + 1} to {int(c2)}", f"> {int(c2)}",
                         f"{n[0]} / {n[1]} / {n[2]}", f"{int(arr.min())} to {int(arr.max())}"])
    md += [C.md_table(["bin variable", "task", "low bin", "mid bin", "high bin",
                       "rows per bin (both arms, 3 models)", "value range"], brow), ""]

    out = C.OUT_DIR / "fixture_facts.md"
    out.write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
