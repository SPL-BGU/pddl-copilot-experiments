#!/usr/bin/env python3
"""Frontier contamination: Claude Sonnet 4.6, canonical corpus
(results/sonnet-frontier/sweep5v2) against the anonymized corpus
(results/sonnet-frontier/sweep6), no-tools arm, harness `success` (for no-tools
rows the online grade of the model's own answer, which is the delivered score on
every task except simulate).

(a) The T7 test of 04_equivalence.py, unchanged (its `tost` and `paired_arrays`):
    trials paired on the exact trial key; 90% cluster-robust t interval on the
    paired difference; domain (k=20) and problem clustering both computed, the
    wider governs; criterion met when the governing interval lies inside (-5, +5).
    Delta = anonymized - canonical. simulate is left out: for Sonnet its stored
    `success` is the strict grade that NUMBERS.md retires (the no-tools simulate
    cells are de-censored bounds, "Frontier e2e" block).
(b) How many single answers change, against two baselines on the same model:
    the identical prompt sent again (validate_plan valid plans, grouped by the
    plan file's text, and validate_domain valid domains, whose prompt holds only
    the domain), and a change of wording on the same names (solve, wordings
    v11-v13 within one corpus).
(c) solve per domain: discordant counts, the exact McNemar test (ignores
    clustering; a reference only) and Holm over the 20 domains.

Descriptive and post hoc (written 2026-11-08). Wording rule as in 04: "criterion
met" / "criterion not met (unresolved)", never "equivalent".

Run:  .venv/bin/python tools/reanalysis/05_frontier_contamination.py
"""
from __future__ import annotations

import importlib.util
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from common import OUT, REPO, RESULTS, holm, load_trials, mcnemar_exact

_spec = importlib.util.spec_from_file_location(
    "eq04", Path(__file__).with_name("04_equivalence.py"))
eq04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eq04)

CORPORA = {  # name -> (trials dir, fixture tree)
    "canonical": (RESULTS / "sonnet-frontier" / "sweep5v2", REPO / "domains"),
    "anonymized": (RESULTS / "sonnet-frontier" / "sweep6", REPO / "domains-anon"),
}
EXACT = ["solve", "validate_domain", "validate_problem", "validate_plan"]
WORDINGS = (11, 12, 13)


def trials(d: Path) -> dict[tuple, dict]:
    return {k: v for k, v in load_trials(d).items() if not v.get("infra_failure")}


def plan_text(tree: Path, domain: str, problem: str, label: str) -> str:
    for track in ("classical", "numeric"):
        fp = tree / track / domain / f"{problem}_{label}.plan"
        if fp.exists():
            return fp.read_text()
    raise FileNotFoundError(f"{tree}: {domain}/{problem}_{label}.plan")


def pair_disagreement(groups: dict) -> tuple[int, int]:
    pairs = dis = 0
    for outcomes in groups.values():
        for a, b in combinations(outcomes, 2):
            pairs += 1
            dis += a != b
    return dis, pairs


def pct(x: int, n: int) -> str:
    return f"{x}/{n} = {100 * x / n:.1f}%"


def main() -> None:
    data = {name: trials(d) for name, (d, _) in CORPORA.items()}
    can, anon = data["canonical"], data["anonymized"]
    L = ["# Frontier contamination: Claude Sonnet 4.6, anonymized minus canonical, no-tools",
         "", f"Rows: canonical {len(can)}, anonymized {len(anon)}, shared keys "
         f"{len(set(can) & set(anon))}.", ""]

    # ---------------------------------------------------------------- (a)
    L += ["## (a) Equivalence test, T7 method (simulate left out)", "", eq04.HEAD]
    cells = [(t, lambda k, t=t: k[1] == t) for t in EXACT]
    cells.append(("pooled (4 exact tasks)", lambda k: k[1] in EXACT))
    flips = []
    for name, sel in cells:
        a, b, dom, prob = eq04.paired_arrays(can, anon, sel)
        r = eq04.tost(a, b, dom, prob)
        L.append(eq04.row(f"Sonnet 4.6 {eq04.SHORT.get(name, name)}", r))
        flips.append((name, len(a), int(((a == 1) & (b == 0)).sum()),
                      int(((a == 0) & (b == 1)).sum())))
    L += ["", "Single answers whose outcome differs between the corpora (same trial key):", "",
          "| cell | pairs | right -> wrong | wrong -> right | changed |", "|---|---|---|---|---|"]
    for name, n, lost, won in flips:
        L.append(f"| {name} | {n} | {lost} | {won} | {pct(lost + won, n)} |")
    L.append("")

    # ---------------------------------------------------------------- (b)
    L += ["## (b) How often single answers change, against two baselines", "",
          "| what changes between the two answers | task | corpus | answer pairs that differ |",
          "|---|---|---|---|"]
    for cname, rows in data.items():
        tree = CORPORA[cname][1]
        vp = defaultdict(list)
        vd = defaultdict(list)
        for k, r in rows.items():
            if k[1] == "validate_plan" and k[4].startswith("v"):
                vp[(k[2], k[3], k[5], plan_text(tree, k[2], k[3], k[4]))].append(bool(r["success"]))
            elif k[1] == "validate_domain" and k[3].startswith("p"):
                vd[(k[2], k[5])].append(bool(r["success"]))
        L.append(f"| nothing (identical prompt) | validate_plan, valid plans | {cname} | "
                 f"{pct(*pair_disagreement(vp))} |")
        L.append(f"| nothing (identical prompt) | validate_domain, valid domains | {cname} | "
                 f"{pct(*pair_disagreement(vd))} |")
    solve = {cname: {(k[2], k[3], k[5]): bool(r["success"]) for k, r in rows.items()
                     if k[1] == "solve"} for cname, rows in data.items()}
    problems = sorted({(d, p) for d, p, _ in solve["canonical"]})
    for cname, s in solve.items():
        groups = {pr: [s[pr + (v,)] for v in WORDINGS] for pr in problems}
        L.append(f"| the wording (same names) | solve | {cname} | {pct(*pair_disagreement(groups))} |")
    same = sum(solve["canonical"][pr + (v,)] != solve["anonymized"][pr + (v,)]
               for pr in problems for v in WORDINGS)
    L.append(f"| the names (same wording) | solve | canonical vs anonymized | "
             f"{pct(same, len(problems) * len(WORDINGS))} |")
    k_can = {pr: sum(solve["canonical"][pr + (v,)] for v in WORDINGS) for pr in problems}
    k_anon = {pr: sum(solve["anonymized"][pr + (v,)] for v in WORDINGS) for pr in problems}
    changed = sum(k_can[pr] != k_anon[pr] for pr in problems)
    L += ["", f"solve problems whose number of solved wordings (0 to 3) changes under renaming: "
          f"{changed} of {len(problems)}.", ""]

    # ---------------------------------------------------------------- (c)
    L += ["## (c) solve per domain (15 trials per domain and corpus)", "",
          "| domain | canonical solved | anonymized solved | right -> wrong | wrong -> right | "
          "exact McNemar p | Holm p (m=20) |", "|---|---|---|---|---|---|---|"]
    per = {}
    for d in sorted({d for d, _ in problems}):
        keys = [pr + (v,) for pr in problems if pr[0] == d for v in WORDINGS]
        c = sum(solve["canonical"][k] for k in keys)
        an = sum(solve["anonymized"][k] for k in keys)
        lost = sum(solve["canonical"][k] and not solve["anonymized"][k] for k in keys)
        won = sum(solve["anonymized"][k] and not solve["canonical"][k] for k in keys)
        per[d] = (c, an, lost, won, mcnemar_exact(lost, won))
    adj = holm({d: v[4] for d, v in per.items()})
    for d, (c, an, lost, won, p) in sorted(per.items(), key=lambda kv: kv[1][4]):
        L.append(f"| {d} | {c} | {an} | {lost} | {won} | {p:.4f} | {adj[d]:.3f} |")
    L.append("")

    text = "\n".join(L)
    OUT.mkdir(exist_ok=True)
    (OUT / "05_frontier_contamination.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
