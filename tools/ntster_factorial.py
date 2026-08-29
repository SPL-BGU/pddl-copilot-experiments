#!/usr/bin/env python3
"""§4(b) within-July factorial — attribution replication check for nt-ster H4.

THE ESTIMAND IS LOCKED IN `development/ntster_h4_prereg.md` §4(b) AND IS NOT A
CHOICE MADE HERE:

    interaction = Δ_wt(ster − neut) − Δ_nt(ster − neut)

per model, on the **delivered** surface for both legs, with the §3.3 clustered CI.
"Replicated" means the interaction CI excludes 0 and its sign matches May. If the
criterion is not met, §5's PASS sentence **drops the "replicated attribution"
clause** rather than keeping it (§4(b), pre-registered).

WHY THIS FILE IS FROZEN LIKE `ntster_h4.py`. The estimand was locked in the
ratified prereg before any data existed, but this file was written on 2026-08-29,
after the H4 verdict was known. Writing analysis code after seeing a result is
exactly the ordering §8 item 9 exists to prevent. The mitigation, agreed with
Omer (final readout O3): write it, freeze and hash it, record the hash in the
prereg, and only then point it at data — the same protocol items 9 and 10 used.
Its sha256 belongs in `ntster_h4_prereg.md` alongside the other four.

Consequently there is NO `--margin`, `--alpha`, `--surface`, `--sign`, `--models`
or `--shard` flag. Each would turn a design commitment into a run-time choice.
The roster is derived from what legs exist, not passed in.

WHAT THIS NUMBER IS NOT. §2.3(A) declares this comparison **attribution-only**
and structurally budget-unmatchable: `chat_with_tools` re-grants the per-task
decode budget every turn up to `MAX_TOOL_LOOPS = 10` (`chat.py:29`), while a
no-tools trial gets one shared budget. The interaction therefore may never be
read as a capability measurement, an effect size to quote, or a cross-arm
comparison of rates. It answers one question: does the steering effect still
depend on tool access when both legs are measured in the same window?

ROSTER. Models needing BOTH a `think=on` no-tools steered leg (this run) and an
iss024d `think=on` with-tools leg. That is Qwen3.5:9B and qwen3.6:35b. gemma has
no `think=on` nt leg by construction (§2.3(B): the decoupled mechanism stops on
`</think>` and gemma has no think tokens), and 0.8B/4B have no on-mode nt legs.
The exclusions are structural, not chosen after seeing anything.

Usage:
    python3 tools/ntster_factorial.py \
        --nt-overlay-dir results/derived/e2e_overlay/ntster-h4-live \
        --wt-overlay-dir <path>/results/derived/e2e_overlay/iss024d-e2e-live \
        --may-overlay-dir <path>/results/derived/e2e_overlay/sweep5v2-live
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gt_cache_gate import assert_gate                    # noqa: E402
from ntster_common import (                              # noqa: E402
    ALPHA, K_DOMAIN, K_PLAN, K_PROBLEM, K_TASK, K_VARIANT, NEUTRAL_VARIANTS,
    STEERED_VARIANTS, Cell, Interval, completeness_gate, delivered,
    is_indeterminate, load_overlay_cells, paired_cluster_bootstrap,
    paired_cluster_ci, wider,
)

TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")


@dataclass
class Interaction:
    """One fixture's (wt − nt) difference-in-differences.

    Field names match `ntster_common.Pair` so the frozen §3.3 interval machinery
    (`paired_cluster_ci`, `paired_cluster_bootstrap`) applies unchanged — those
    functions read only `.d` and whatever the caller's key function touches.
    """
    task: str
    domain: str
    problem: str
    plan_label: str
    paraphrase: int
    d_wt: float
    d_nt: float

    @property
    def d(self) -> float:
        return self.d_wt - self.d_nt


def _fixture_index(cell: Cell, task: str | None = None) -> dict[tuple, dict]:
    idx: dict[tuple, dict] = {}
    for key, row in cell.rows.items():
        if task is not None and key[K_TASK] != task:
            continue
        idx[(key[K_TASK], key[K_DOMAIN], key[K_PROBLEM], key[K_PLAN],
             key[K_VARIANT])] = row
    return idx


def _arm_deltas(cell: Cell, task: str | None = None) -> dict[tuple, float]:
    """Per-fixture paired difference (steered − anchor) on the delivered surface.

    Keyed by (task, domain, problem, plan_label, paraphrase) so the two legs can
    be joined on identical fixtures. Mirrors `ntster_common.build_pairs`
    (including the §2.3(C) exclusion of indeterminate rows — the wt leg is
    ~14% censored); kept local because the join key must survive out of the
    function. An excluded fixture surfaces in `fixtures_dropped`.
    """
    idx = _fixture_index(cell, task)
    out: dict[tuple, float] = {}
    for j, (vlo, vhi) in enumerate(zip(NEUTRAL_VARIANTS, STEERED_VARIANTS)):
        for (t, dom, prob, plan, v), row in idx.items():
            if v != vlo:
                continue
            other = idx.get((t, dom, prob, plan, vhi))
            if other is None:
                continue
            if is_indeterminate(row) or is_indeterminate(other):
                continue
            out[(t, dom, prob, plan, j)] = float(delivered(other)) - float(delivered(row))
    return out


def build_interactions(wt: Cell, nt: Cell,
                       task: str | None = None) -> tuple[list[Interaction], int]:
    """Join the two legs on the fixture key. Returns (interactions, dropped)."""
    dwt = _arm_deltas(wt, task)
    dnt = _arm_deltas(nt, task)
    shared = dwt.keys() & dnt.keys()
    dropped = len(dwt.keys() | dnt.keys()) - len(shared)
    items = [
        Interaction(task=k[0], domain=k[1], problem=k[2], plan_label=k[3],
                    paraphrase=k[4], d_wt=dwt[k], d_nt=dnt[k])
        for k in sorted(shared)
    ]
    return items, dropped


def _intervals(items: list[Interaction]) -> dict:
    # Problem clustering is size-weighted (§9.2 deviation D5): the realized
    # problem clusters are unbalanced, so the unweighted mean of cluster means
    # would not estimate the locked interaction. Labels carry the realized k.
    ci_domain = paired_cluster_ci(items, lambda p: p.domain, method="domain")
    ci_problem = paired_cluster_ci(items, lambda p: (p.domain, p.problem),
                                   method="problem", weighted=True)
    governing = wider(ci_domain, ci_problem)
    boot = paired_cluster_bootstrap(items, lambda p: p.domain)
    return {"domain": ci_domain, "problem": ci_problem,
            "governing": governing, "bootstrap_domain": boot}


def _as_dict(iv: Interval) -> dict:
    return {"estimate_pp": iv.estimate_pp, "lo_pp": iv.lo_pp, "hi_pp": iv.hi_pp,
            "half_width_pp": iv.half_width_pp, "k": iv.k, "method": iv.method}


def _excludes_zero(iv: Interval) -> bool:
    if math.isnan(iv.lo_pp) or math.isnan(iv.hi_pp):
        return False
    return iv.lo_pp > 0.0 or iv.hi_pp < 0.0


def _leg_delta_pp(cell: Cell, task: str | None = None) -> float:
    """Row-level pooled (steered − anchor) in pp, for reporting the legs."""
    d = _arm_deltas(cell, task)
    return 100.0 * (sum(d.values()) / len(d)) if d else math.nan


def _by_model(cells: list[Cell], leg: str) -> dict[str, Cell]:
    """Model-keyed cells, refusing a silent last-wins on a duplicate.

    A stray overlay beside the clean rerun for the same model (exactly what a
    void cell dir would be) must fail loudly, not shadow the good leg.
    """
    out: dict[str, Cell] = {}
    for c in cells:
        if c.model in out:
            raise SystemExit(
                f"two overlay cells claim model {c.model!r} in the {leg} leg: "
                f"{out[c.model].name!r} and {c.name!r}. Corpus identity is "
                "load-bearing; remove the stray overlay instead of letting "
                "dict order pick one.")
        out[c.model] = c
    return out


def may_reference_sign(may_cells: list[Cell], model: str) -> dict:
    """May's with-tools `think=on` steering effect — the sign to match (§4(b)).

    Computed from the canonical corpus rather than hardcoded, so the reference is
    auditable and cannot drift from a number typed into a docstring. Refuses an
    ambiguous corpus (two matching cells) rather than taking the first by glob
    order.
    """
    matches = [c for c in may_cells
               if c.model == model and c.think == "on" and "no-tools" not in c.name]
    if len(matches) > 1:
        raise SystemExit(
            f"May reference is ambiguous for {model!r}: "
            f"{[c.name for c in matches]!r} all match. Corpus identity is "
            "load-bearing; refusing to pick one silently.")
    if matches:
        c = matches[0]
        delta = _leg_delta_pp(c)
        return {"cell": c.name, "delta_pp": delta,
                "sign": (1 if delta > 0 else -1 if delta < 0 else 0)}
    return {"cell": None, "delta_pp": math.nan, "sign": 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nt-overlay-dir", type=Path, required=True,
                    help="overlay dir holding this run's think=on no-tools cells")
    ap.add_argument("--wt-overlay-dir", type=Path, required=True,
                    help="overlay dir holding the iss024d think=on with-tools cells")
    ap.add_argument("--may-overlay-dir", type=Path, required=True,
                    help="canonical sweep5v2 overlay, for the May reference sign")
    ap.add_argument("--out", type=Path,
                    default=Path("results/derived/ntster_factorial.json"))
    ap.add_argument("--markdown", type=Path,
                    default=Path("results/derived/ntster_factorial.md"))
    args = ap.parse_args()

    gate = assert_gate()
    print(f"gt gate: PASS {gate[:12]}")

    nt_cells = [c for c in load_overlay_cells(args.nt_overlay_dir) if c.think == "on"]
    wt_cells = [c for c in load_overlay_cells(args.wt_overlay_dir) if c.think == "on"]
    may_cells = load_overlay_cells(args.may_overlay_dir)

    nt_by_model = _by_model(nt_cells, "nt")
    wt_by_model = _by_model(wt_cells, "wt")
    roster = sorted(nt_by_model.keys() & wt_by_model.keys())
    if not roster:
        print("ERROR: no model has both a think=on nt leg and a think=on wt leg",
              file=sys.stderr)
        return 2
    print(f"roster ({len(roster)}): {', '.join(roster)}")
    for m in sorted(nt_by_model.keys() - set(roster)):
        print(f"  excluded (no wt leg): {m}")
    for m in sorted(wt_by_model.keys() - set(roster)):
        print(f"  excluded (no nt on-mode leg): {m}")

    results = {
        "produced_by": "tools/ntster_factorial.py",
        "prereg": "development/ntster_h4_prereg.md §4(b)",
        "estimand": "interaction = d_wt(ster-neut) - d_nt(ster-neut), delivered surface",
        "nt_overlay_dir": str(args.nt_overlay_dir),
        "wt_overlay_dir": str(args.wt_overlay_dir),
        "may_overlay_dir": str(args.may_overlay_dir),
        "alpha": ALPHA,
        "gt_gate_hash": gate,
        "scope_note": ("Attribution-only and structurally budget-unmatchable per "
                       "§2.3(A): chat_with_tools re-grants the per-task decode budget "
                       "every turn up to MAX_TOOL_LOOPS=10 while a no-tools trial gets "
                       "one shared budget. Never a capability measurement."),
        "models": [],
    }

    for model in roster:
        nt, wt = nt_by_model[model], wt_by_model[model]
        g_nt = completeness_gate(nt)
        g_wt = completeness_gate(wt)
        if not (g_nt.ok and g_wt.ok):
            # §3.1: an incomplete cell is INCONCLUSIVE and is not analysed on
            # the surviving subset — recording the gate without enforcing it
            # would feed a quiet surviving-subset verdict into §4(b).
            results["models"].append({
                "model": model,
                "nt_cell": nt.name, "wt_cell": wt.name,
                "analysable": False,
                "completeness": {"nt": g_nt.ok, "wt": g_wt.ok,
                                 "nt_lines": g_nt.lines, "wt_lines": g_wt.lines},
                "replicated": False,
                "note": ("leg(s) fail the §3.1 completeness gate — "
                         "INCONCLUSIVE, not analysed; re-run the missing keys "
                         "to completion."),
            })
            continue
        items, dropped = build_interactions(wt, nt)
        ivs = _intervals(items)
        gov = ivs["governing"]
        may = may_reference_sign(may_cells, model)
        est_sign = 1 if gov.estimate_pp > 0 else -1 if gov.estimate_pp < 0 else 0
        excl = _excludes_zero(gov)
        sign_match = bool(may["sign"] != 0 and est_sign == may["sign"])
        replicated = bool(excl and sign_match)

        per_task = {}
        for task in TASKS:
            t_items, _ = build_interactions(wt, nt, task=task)
            if not t_items:
                continue
            t_ivs = _intervals(t_items)
            per_task[task] = {
                "n_fixtures": len(t_items),
                "delta_wt_pp": _leg_delta_pp(wt, task),
                "delta_nt_pp": _leg_delta_pp(nt, task),
                "ci": {k: _as_dict(v) for k, v in t_ivs.items()},
            }

        results["models"].append({
            "model": model,
            "nt_cell": nt.name, "wt_cell": wt.name,
            "analysable": True,
            "completeness": {"nt": g_nt.ok, "wt": g_wt.ok,
                             "nt_lines": g_nt.lines, "wt_lines": g_wt.lines},
            "n_fixtures": len(items), "fixtures_dropped": dropped,
            "delta_wt_pp": _leg_delta_pp(wt),
            "delta_nt_pp": _leg_delta_pp(nt),
            "ci": {k: _as_dict(v) for k, v in ivs.items()},
            "may_reference": may,
            "ci_excludes_zero": excl,
            "sign_matches_may": sign_match,
            "replicated": replicated,
            "per_task": per_task,
        })

    unanalysable = [m["model"] for m in results["models"]
                    if not m.get("analysable", True)]
    all_replicated = (not unanalysable
                      and all(m["replicated"] for m in results["models"]))
    results["clause_verdict"] = {
        "criterion": "§4(b): interaction CI excludes 0 AND sign matches May, every model",
        "include_replicated_attribution_clause": all_replicated,
        "note": ("§5's PASS sentence keeps the '[, with attribution replicated in a "
                 "within-July factorial]' clause" if all_replicated else
                 (("model(s) with an incomplete leg cannot establish the "
                   f"criterion: {', '.join(unanalysable)}. " if unanalysable
                   else "")
                  + "§5's PASS sentence DROPS the 'replicated attribution' "
                    "clause, as pre-registered — it is not rewritten or "
                    "weakened, it is removed.")),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"results written: {args.out}")

    lines = [
        "# nt-ster §4(b) — within-July factorial (attribution replication)",
        "",
        f"Interaction Δ_wt(ster−neut) − Δ_nt(ster−neut) · delivered surface · "
        f"{int((1-ALPHA)*100)}% intervals · GT gate `{gate[:12]}`",
        "",
        "> **Attribution-only.** §2.3(A) declares this comparison structurally "
        "budget-unmatchable (`chat_with_tools` re-grants the per-task decode budget "
        "every turn up to `MAX_TOOL_LOOPS = 10`; a no-tools trial gets one shared "
        "budget). It is not a capability measurement and no rate from it may be quoted "
        "as an effect size.",
        "",
        f"## Clause verdict: **{'KEEP' if all_replicated else 'DROP'}**",
        "",
        results["clause_verdict"]["note"],
        "",
        "| model | Δ_wt | Δ_nt | interaction [90% CI] | excludes 0 | May sign | replicated |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for m in results["models"]:
        if not m.get("analysable", True):
            lines.append(f"| {m['model']} | — | — | INCONCLUSIVE (incomplete leg) "
                         f"| — | — | no |")
            continue
        g = m["ci"]["governing"]
        lines.append(
            f"| {m['model']} | {m['delta_wt_pp']:+.2f} | {m['delta_nt_pp']:+.2f} | "
            f"{g['estimate_pp']:+.2f} [{g['lo_pp']:+.2f}, {g['hi_pp']:+.2f}] | "
            f"{'yes' if m['ci_excludes_zero'] else 'no'} | "
            f"{m['may_reference']['delta_pp']:+.2f} | "
            f"{'**yes**' if m['replicated'] else 'no'} |")

    for m in results["models"]:
        if not m.get("analysable", True):
            lines += ["", f"## {m['model']}", "",
                      f"- nt leg: `{m['nt_cell']}` (complete: {m['completeness']['nt']})",
                      f"- wt leg: `{m['wt_cell']}` (complete: {m['completeness']['wt']})",
                      f"- **{m['note']}**"]
            continue
        lines += ["", f"## {m['model']}", "",
                  f"- nt leg: `{m['nt_cell']}` (complete: {m['completeness']['nt']})",
                  f"- wt leg: `{m['wt_cell']}` (complete: {m['completeness']['wt']})",
                  f"- {m['n_fixtures']:,} matched fixtures, {m['fixtures_dropped']} dropped "
                  "(unmatched or indeterminate on either leg, §2.3(C))",
                  "",
                  "| interval | interaction [90% CI] | half-width |", "|---|---|---:|"]
        for k in ("domain", "problem", "governing", "bootstrap_domain"):
            iv = m["ci"][k]
            lines.append(f"| {k} | {iv['estimate_pp']:+.2f} "
                         f"[{iv['lo_pp']:+.2f}, {iv['hi_pp']:+.2f}] | "
                         f"{iv['half_width_pp']:.2f}pp |")
        lines += ["", "**Per task** (descriptive; §4(b) states the estimand per model, "
                  "so no per-task cell carries clause authority).", "",
                  "| task | Δ_wt | Δ_nt | interaction [90% CI] |", "|---|---:|---:|---|"]
        for task, t in m["per_task"].items():
            g = t["ci"]["governing"]
            lines.append(f"| {task} | {t['delta_wt_pp']:+.2f} | {t['delta_nt_pp']:+.2f} | "
                         f"{g['estimate_pp']:+.2f} "
                         f"[{g['lo_pp']:+.2f}, {g['hi_pp']:+.2f}] |")
        lines.append("")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text("\n".join(lines) + "\n")
    print(f"report written: {args.markdown}")

    print()
    print(f"CLAUSE: {'KEEP' if all_replicated else 'DROP'} the replicated-attribution clause")
    for m in results["models"]:
        if not m.get("analysable", True):
            print(f"  {m['model']}: INCONCLUSIVE — {m['note']}")
            continue
        g = m["ci"]["governing"]
        print(f"  {m['model']}: interaction {g['estimate_pp']:+.2f} "
              f"[{g['lo_pp']:+.2f}, {g['hi_pp']:+.2f}]  replicated={m['replicated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
