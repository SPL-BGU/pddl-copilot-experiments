#!/usr/bin/env python3
"""Frontier contamination, tool arm: Claude Haiku 4.5 with tools, canonical
corpus (results/haiku-frontier/sweep5v2-with-tools) against the renamed corpus
(results/haiku-frontier/sweep6-with-tools; run 2026-07-12, 1,520 trials, not
reported before 2026-11-09). Variant 11 only, both cells.

Two surfaces, per task and pooled:
  tool-verified  the harness `success` (the tool was called and its result
                 matched the answer key). Exact on every row.
  delivered      the overlay `e2e_strict` (results/derived/e2e_overlay/
                 haiku-frontier/<cell>.e2e.jsonl, the grader of the Frontier
                 e2e block). Tri-state: rows censored at the response snapshot
                 cap ("indeterminate") are bounds; the paired test uses only
                 pairs determinate on both sides (the nt-ster H4 convention) and
                 the count left out is shown.

Method = T7 / 05_frontier_contamination.py, unchanged (`04_equivalence.tost`
and the same pairing): paired on the exact trial key; 90% cluster-robust t
interval on the paired difference; domain (k=20) and problem clustering both
computed, the wider governs; criterion met when the governing interval lies
inside (-5, +5). Delta = renamed - canonical. Wording: "criterion met" /
"criterion not met (unresolved)", never "equivalent".

Also checks that the two cells match on everything but the corpus: the run
meta of every summary file, the model on every row, the key set, variant,
tool filter, prompt style, and the truncation pattern (the meta records no
max-tokens value).

Descriptive and post hoc (written 2026-11-09).

Run:  .venv/bin/python tools/reanalysis/06_frontier_tools_contamination.py [--results DIR]
Writes tools/reanalysis/out/06_frontier_tools_contamination.md and
       tools/reanalysis/out/numbers_06_frontier_tools_contamination.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np

from common import OUT, REPO, TASKS, read_jsonl

_spec = importlib.util.spec_from_file_location(
    "eq04", Path(__file__).with_name("04_equivalence.py"))
eq04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eq04)

CELLS = {"canonical": "sweep5v2-with-tools", "renamed": "sweep6-with-tools"}


def load(results: Path, cell: str):
    d = results / "haiku-frontier" / cell
    rows = {}
    for rec in read_jsonl(d / "trials.jsonl"):
        rows[tuple(rec["key"])] = rec["result"]
    ov = {tuple(r["trial_key"]): r for r in
          read_jsonl(results / "derived" / "e2e_overlay" / "haiku-frontier" / f"{cell}.e2e.jsonl")}
    metas = {}
    for fp in sorted(d.glob("summary_*.json")):
        metas[fp.name] = json.loads(fp.read_text()).get("meta", {})
    return rows, ov, metas


def arrays(ca, ra, keys, f):
    a = np.array([float(f(ca, k)) for k in keys])
    b = np.array([float(f(ra, k)) for k in keys])
    dom = np.array([k[2] for k in keys])
    prob = np.array([f"{k[2]}|{k[3]}" for k in keys])
    return a, b, dom, prob


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=REPO / "results")
    args = ap.parse_args(argv)
    (can, can_ov, can_meta), (ren, ren_ov, ren_meta) = (load(args.results, c) for c in CELLS.values())

    # ------------------------------------------------------------ settings check
    L = ["# Frontier contamination, tool arm: Claude Haiku 4.5, renamed minus canonical", ""]
    issues = []
    shared = sorted(set(can) & set(ren))
    if set(can) != set(ren):
        issues.append(f"key sets differ: {len(set(can) ^ set(ren))} keys in one cell only")
    strip = lambda m: {k: v for k, v in m.items() if k != "corpus"}  # noqa: E731
    metas = [strip(m) for m in list(can_meta.values()) + list(ren_meta.values())]
    if any(m != metas[0] for m in metas):
        issues.append("run meta differs between summary files: " + json.dumps(metas))
    corp = {n: m.get("corpus") for n, m in {**can_meta, **ren_meta}.items()}
    for nm, rows in (("canonical", can), ("renamed", ren)):
        for fld in ("model", "tool_filter", "prompt_style", "prompt_variant", "with_tools"):
            vals = Counter(r[fld] for r in rows.values())
            if len(vals) != 1:
                issues.append(f"{nm}: {fld} not constant {dict(vals)}")
    m0 = metas[0]
    redone = []  # rows of trials.jsonl that differ from a cell's first full snapshot
    for nm, cell, rows in (("canonical", CELLS["canonical"], can), ("renamed", CELLS["renamed"], ren)):
        snaps = sorted((args.results / "haiku-frontier" / cell).glob("single_task_*.json"))
        first = {(r["task"], r["domain_name"], r["problem_name"], r.get("plan_label", "")): r
                 for r in json.loads(snaps[0].read_text())}
        for k, r in rows.items():
            f = first.get(k[1:5])
            if f is None or f["response"] != r["response"] or f["success"] != r["success"]:
                redone.append(f"{nm} {k[1]} {k[2]} {k[3]} (first run: {f and f.get('failure_reason')}, "
                              f"stored: {r['failure_reason']}; {len(snaps)} snapshots)")
    trunc = {nm: sorted(r["tokens"]["completion"] for k, r in rows.items() if r["done_reason"] == "length")
             for nm, rows in (("canonical", can), ("renamed", ren))}
    trunc_tasks = {nm: Counter(k[1] for k, r in rows.items() if r["done_reason"] == "length")
                   for nm, rows in (("canonical", can), ("renamed", ren))}
    infra = {nm: sum(bool(r.get("infra_failure")) for r in rows.values())
             for nm, rows in (("canonical", can), ("renamed", ren))}
    L += ["## Settings check", "",
          f"- rows: canonical {len(can)}, renamed {len(ren)}, shared keys {len(shared)}; "
          f"infrastructure-failure rows {infra['canonical']} / {infra['renamed']}",
          f"- run meta (every summary file, corpus field aside): model `{m0.get('model')}`, "
          f"sdk `{m0.get('sdk_version')}`, temperature {m0.get('temperature')}, think {m0.get('think')}, "
          f"max_iterations {m0.get('max_iterations')}, backend `{m0.get('backend')}`; corpus field "
          + ", ".join(f"{n}: {v}" for n, v in corp.items()),
          "- max tokens: not recorded in the run meta. Both cells ran with the runner's per-task "
          "default (no `--num-predict` override; `pddl_eval.runner.DEFAULT_NUM_PREDICT`). Rows stopped "
          f"by the budget: canonical {sum(trunc_tasks['canonical'].values())} "
          f"({dict(trunc_tasks['canonical'])}), renamed {sum(trunc_tasks['renamed'].values())} "
          f"({dict(trunc_tasks['renamed'])}); completion tokens of those rows "
          f"{trunc['canonical'][0]}–{trunc['canonical'][-1]} vs {trunc['renamed'][0]}–{trunc['renamed'][-1]}",
          "- rows that differ from the cell's first full run (re-run on resume): "
          + ("; ".join(redone) if redone else "none"),
          "- mismatches found: " + ("; ".join(issues) if issues else "none"), ""]

    # ------------------------------------------------------------ tests
    def tv(rows, k):
        return bool(rows[k]["success"])
    dl_rows = {"c": can_ov, "r": ren_ov}

    def det(k):
        return can_ov[k]["e2e_strict"] in (True, False) and ren_ov[k]["e2e_strict"] in (True, False)

    def dl(ov, k):
        return ov[k]["e2e_strict"] is True

    res = {}
    L += ["## Paired test, T7 method", "", "Tool-verified (`success`):", "", eq04.HEAD]
    for t in TASKS + ["pooled"]:
        keys = [k for k in shared if t == "pooled" or k[1] == t]
        r = eq04.tost(*arrays(can, ren, keys, tv))
        r["flips"] = (int(sum(tv(can, k) and not tv(ren, k) for k in keys)),
                      int(sum(tv(ren, k) and not tv(can, k) for k in keys)))
        res[("tv", t)] = r
        L.append(eq04.row(f"Haiku 4.5 tools {eq04.SHORT[t]}", r))
    L += ["", "Delivered (`e2e_strict`, pairs determinate on both sides):", "", eq04.HEAD]
    for t in TASKS + ["pooled"]:
        keys_all = [k for k in shared if t == "pooled" or k[1] == t]
        keys = [k for k in keys_all if det(k)]
        r = eq04.tost(*arrays(can_ov, ren_ov, keys, dl))
        r["left_out"] = len(keys_all) - len(keys)
        r["flips"] = (int(sum(dl(can_ov, k) and not dl(ren_ov, k) for k in keys)),
                      int(sum(dl(ren_ov, k) and not dl(can_ov, k) for k in keys)))
        res[("dl", t)] = r
        L.append(eq04.row(f"Haiku 4.5 tools {eq04.SHORT[t]}", r))
    L.append("")
    L += ["Outcome flips between the corpora (same key) and censored pairs left out of the delivered test:", "",
          "| task | tool-verified right→wrong / wrong→right | delivered right→wrong / wrong→right | delivered pairs left out (censored on either side) | delivered bounds, canonical / renamed |",
          "|---|---|---|---|---|"]
    for t in TASKS:
        keys = [k for k in shared if k[1] == t]
        b = {}
        for nm, ov in (("c", can_ov), ("r", ren_ov)):
            lo = sum(ov[k]["e2e_strict"] is True for k in keys)
            hi = lo + sum(ov[k]["e2e_strict"] not in (True, False) for k in keys)
            b[nm] = f"[{100 * lo / len(keys):.1f}, {100 * hi / len(keys):.1f}]" if hi > lo else f"{100 * lo / len(keys):.1f}"
        a, d = res[("tv", t)], res[("dl", t)]
        L.append(f"| {t} | {a['flips'][0]} / {a['flips'][1]} | {d['flips'][0]} / {d['flips'][1]} | "
                 f"{d['left_out']} | {b['c']} / {b['r']} |")
    L.append("")
    calls = {nm: sum(bool(r["tool_selected"]) for r in rows.values()) for nm, rows in (("c", can), ("r", ren))}
    L.append(f"Calling (`tool_selected`): canonical {calls['c']}/{len(can)}, renamed {calls['r']}/{len(ren)}.")
    L.append("")

    # self-check against the frozen Frontier e2e block (Haiku with tools, canonical)
    sv = [k for k in shared if k[1] == "solve"]
    assert sum(can_ov[k]["e2e_strict"] is True for k in sv) == 95, "canonical solve delivered is not 95/100"

    text = "\n".join(L) + "\n"
    OUT.mkdir(exist_ok=True)
    (OUT / "06_frontier_tools_contamination.md").write_text(text)

    def lab(r):
        s = eq04.label(r)
        return s.replace("criterion not met (unresolved)", "**criterion not met (unresolved)**")

    def cell(r):
        return f"{r['est']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]{'' if r['gov'] == 'domain' else ' (problem)'}"
    per_tv = "; ".join(f"{t} {res[('tv', t)]['ra']:.1f} → {res[('tv', t)]['rb']:.1f}, {cell(res[('tv', t)])} {lab(res[('tv', t)])}"
                       for t in TASKS)
    per_dl = "; ".join(f"{t} {res[('dl', t)]['ra']:.1f} → {res[('dl', t)]['rb']:.1f}, {cell(res[('dl', t)])} {lab(res[('dl', t)])}"
                       for t in TASKS)
    pt, pd = res[("tv", "pooled")], res[("dl", "pooled")]
    N = ["| figure | **quote this** | do NOT quote |", "|---|---|---|",
         f"| Haiku 4.5 with tools, renamed − canonical, tool-verified, per task (n = 100 / 120 / 200 / 1,000 / 100) "
         f"| {per_tv} | \"equivalent\"; any of these as a memorization test: the tool arm sits at a ceiling, so a met "
         f"criterion carries little information |",
         f"| same, delivered (`e2e_strict`, pairs determinate on both sides) | {per_dl}. Censored pairs left out: "
         f"simulate {res[('dl', 'simulate')]['left_out']}, every other task {sum(res[('dl', t)]['left_out'] for t in TASKS if t != 'simulate')} "
         f"| simulate delivered as a point rate (it is bounded: see the table in `06_frontier_tools_contamination.md`) |",
         f"| pooled, 5 tasks | tool-verified {pt['ra']:.1f} → {pt['rb']:.1f}, {cell(pt)}, {lab(pt)}; delivered "
         f"{pd['ra']:.1f} → {pd['rb']:.1f}, {cell(pd)}, {lab(pd)} (1,000 of the 1,520 trials are validate_plan) | none |",
         f"| settings, canonical vs renamed cell | same model, sdk {m0.get('sdk_version')}, temperature, max_iterations, "
         f"tool filter, prompt style, variant and key set; max tokens not in the meta, same default per task and "
         f"the same truncation pattern ({sum(trunc_tasks['canonical'].values())} vs {sum(trunc_tasks['renamed'].values())} rows, all simulate). "
         f"Mismatches: {'; '.join(issues) if issues else 'none'}. Rows re-run on resume: "
         f"{'; '.join(redone) if redone else 'none'} | none |"]
    (OUT / "numbers_06_frontier_tools_contamination.md").write_text("\n".join(N) + "\n")
    print(text)
    print("\n".join(N))


if __name__ == "__main__":
    main()
