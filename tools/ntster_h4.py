#!/usr/bin/env python3
"""nt-ster H4 — frozen entry point 2 of 2: the confirmatory contrast (§3.3-§3.7).

H4 (control / falsification): the steered directive alone does not move the
no-tools floor — (no-tools, v14-16) ≈ (no-tools, v11-13) within ±5pp, tested
inside a single July apparatus. If H4 fails, the H2 attribution of the May +72pp
steering effect to steering-under-tools is compromised.

TWO HARD PRECONDITIONS, both enforced rather than documented:

1. **F before the contrast.** This script refuses to run without the JSON written
   by `ntster_f_gate.py`. The F gate is computed from the anchor arm alone, so
   requiring its output makes the pre-registered order un-skippable.
2. **Ground truth matches its stamp.** `gt_cache_gate.assert_gate()` runs before
   any trial is read. Ground truth is regenerated live per run and never
   persisted, and trial rows store no plan text, so a live-vs-cache divergence
   would otherwise be silent and unauditable.

WHAT IS DELIBERATELY NOT HERE
  * No `--margin`, `--alpha`, or surface flag. Every one of those is a design
    commitment from the prereg; exposing it as a flag is how a pre-registration
    turns into a post-hoc choice.
  * No `--shard`. `prompt_variant` is in the shard key (`runner.py:647-650`), so
    any shard split breaks the +3-offset pairing the primary depends on.

Usage:
    python tools/ntster_h4.py \
        --overlay-dir results/derived/e2e_overlay/ntster-h4-live \
        --f-gate results/derived/ntster_f_gate.json \
        --out results/derived/ntster_h4_results.json \
        --markdown results/derived/ntster_h4_report.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ntster_common import (  # noqa: E402
    ALPHA, ANCHOR_BAND, APPARATUS_REASONS, APPARATUS_VOID_SHARE,
    AT_CAP_RESPONSE_LEN, BOOTSTRAP_B, CEILING_GUARD_TRUNCATION,
    CHANNEL_FORMAT_REASONS, CONTENT_REASONS, HALF_WIDTH_CEILING_PP,
    LEAKAGE_RANK, LOW_BASE_RATE_BELOW, M1_SOLVE_PATTERN, M1_TOOL_NAME_PATTERN,
    MARGIN_PP, MECHANISM_MIN_ABS_DELTA_PP, NEUTRAL_VARIANTS, STEERED_VARIANTS,
    TASKS, TRUNCATED_LOSS_REASONS,
    Cell, Interval, K_TASK, K_VARIANT, arm_rate, build_pairs, completeness_gate,
    delivered, holm, is_censored, legacy, load_overlay_cells,
    newcombe_unpaired, noninferiority_p, paired_cluster_bootstrap,
    paired_cluster_ci, pct, wider,
)
from gt_cache_gate import assert_gate  # noqa: E402

from scipy import stats  # noqa: E402


# ==========================================================================
# §3.3 / §3.4 — the confirmatory contrast
# ==========================================================================

def contrast(cell: Cell, *, task: str | None) -> dict:
    """Paired, domain-clustered contrast at one granularity, with companions."""
    pairs = build_pairs(cell, lo=NEUTRAL_VARIANTS, hi=STEERED_VARIANTS,
                        surface=delivered, task=task)
    ci_domain = paired_cluster_ci(pairs, lambda p: p.domain, method="domain (k=20)")
    ci_problem = paired_cluster_ci(pairs, lambda p: (p.domain, p.problem),
                                   method="problem (k=100)")
    governing = wider(ci_domain, ci_problem)
    boot = paired_cluster_bootstrap(pairs, lambda p: p.domain)

    xa, na = arm_rate(cell, NEUTRAL_VARIANTS, task=task, surface=delivered)
    xb, nb = arm_rate(cell, STEERED_VARIANTS, task=task, surface=delivered)
    newc = newcombe_unpaired(xa, na, xb, nb)

    xal, nal = arm_rate(cell, NEUTRAL_VARIANTS, task=task, surface=legacy)
    xbl, nbl = arm_rate(cell, STEERED_VARIANTS, task=task, surface=legacy)

    # Row-level pooled difference, reported so any cluster imbalance is visible
    # rather than absorbed into the cluster-mean estimator.
    pooled_pp = pct(xb, nb) - pct(xa, na)

    censored_a = sum(1 for k, r in cell.rows.items()
                     if k[K_VARIANT] in NEUTRAL_VARIANTS
                     and (task is None or k[K_TASK] == task) and is_censored(r))
    censored_b = sum(1 for k, r in cell.rows.items()
                     if k[K_VARIANT] in STEERED_VARIANTS
                     and (task is None or k[K_TASK] == task) and is_censored(r))

    return {
        "granularity": task or "pooled",
        "n_pairs": len(pairs),
        "anchor": {"x": xa, "n": na, "rate_pp": pct(xa, na),
                   "legacy_rate_pp": pct(xal, nal), "censored": censored_a},
        "steered": {"x": xb, "n": nb, "rate_pp": pct(xb, nb),
                    "legacy_rate_pp": pct(xbl, nbl), "censored": censored_b},
        "pooled_row_level_delta_pp": pooled_pp,
        "ci": {
            "domain": _ci_dict(ci_domain),
            "problem": _ci_dict(ci_problem),
            "governing": _ci_dict(governing),
            "bootstrap_domain": _ci_dict(boot),
            "newcombe_unpaired": _ci_dict(newc),
        },
        "_governing_obj": governing,
    }


def _ci_dict(ci: Interval) -> dict:
    return {"estimate_pp": ci.estimate_pp, "lo_pp": ci.lo_pp, "hi_pp": ci.hi_pp,
            "half_width_pp": ci.half_width_pp, "k": ci.k, "method": ci.method}


def classify(anchor_rate_pp: float, f_pp: float, half_width_pp: float) -> str:
    """§3.3 point 3, assigned mechanically from the anchor + realized precision.

    Order matters: DEGENERATE is checked before the low-base-rate band, because a
    0%/100% anchor makes an equivalence statement vacuous rather than merely
    imprecise.
    """
    if math.isnan(anchor_rate_pp):
        return "UNINFORMATIVE"
    if anchor_rate_pp in (0.0, 100.0):
        return "DEGENERATE"
    if (not math.isnan(f_pp)) and f_pp >= MARGIN_PP:
        return "UNINFORMATIVE"
    if math.isnan(half_width_pp) or half_width_pp > HALF_WIDTH_CEILING_PP:
        return "UNINFORMATIVE"
    if anchor_rate_pp < LOW_BASE_RATE_BELOW:
        return "LOW-BASE-RATE"
    if not (ANCHOR_BAND[0] <= anchor_rate_pp <= ANCHOR_BAND[1]):
        return "LOW-BASE-RATE" if anchor_rate_pp < ANCHOR_BAND[0] else "UNINFORMATIVE"
    return "ELIGIBLE"


def label(ci: Interval) -> tuple[str, bool]:
    """§3.4 per-task labels — exhaustive and disjoint. Returns (label, underpowered)."""
    underpowered = (not math.isnan(ci.half_width_pp)) and ci.half_width_pp > MARGIN_PP
    if math.isnan(ci.lo_pp) or math.isnan(ci.hi_pp):
        return "INDETERMINATE", underpowered
    if ci.inside_margin():
        return "EQUIVALENT", underpowered
    if ci.outside_margin():
        return "NOT-EQUIVALENT", underpowered
    return "INDETERMINATE", underpowered


def risk_ratio_bound(anchor_x: int, anchor_n: int, steered_x: int,
                     steered_n: int) -> dict:
    """§3.3: a LOW-BASE-RATE cell reports the relative move as well.

    ±5pp absolute at a 7.6% anchor admits a 1.66× relative move, so the absolute
    interval alone would understate what the control permits.
    """
    if anchor_n == 0 or steered_n == 0 or anchor_x == 0:
        return {"rr": math.nan, "note": "anchor has zero successes; RR undefined"}
    pa, pb = anchor_x / anchor_n, steered_x / steered_n
    if pb == 0:
        return {"rr": 0.0, "note": "steered arm has zero successes"}
    log_rr = math.log(pb / pa)
    se = math.sqrt((1 - pa) / anchor_x + (1 - pb) / steered_x)
    z = float(stats.norm.ppf(1 - ALPHA / 2))
    return {"rr": pb / pa, "lo": math.exp(log_rr - z * se),
            "hi": math.exp(log_rr + z * se),
            "margin_equivalent_rr": (pa * 100 + MARGIN_PP) / (pa * 100)}


# ==========================================================================
# §3.7 — mechanism decomposition (secondary; never gates or revises H4)
# ==========================================================================

def _norm_reason(row: dict) -> str:
    r = (row.get("failure_reason") or "").strip()
    if r.upper().startswith("FR_"):
        r = r[3:]
    return r.lower()


def _component(row: dict) -> str | None:
    """Four-way partition of a FAILED row. Returns None for a success."""
    if delivered(row):
        return None
    reason = _norm_reason(row)
    # The overlay can re-grade `simulate` into its own reasons; fold those in.
    e2e_reason = (row.get("e2e_reason") or "").lower()
    if e2e_reason in ("format_parse_fail",) or reason in CHANNEL_FORMAT_REASONS:
        return "CHANNEL_FORMAT"
    if e2e_reason == "trajectory_mismatch" or reason in CONTENT_REASONS:
        return "CONTENT"
    if reason in TRUNCATED_LOSS_REASONS:
        return "TRUNCATED_LOSS"
    if reason in APPARATUS_REASONS or reason == "":
        return "APPARATUS"
    return "APPARATUS"


def mechanism(cell: Cell, *, task: str | None, verdict: str,
              governing: Interval, domain_ci: Interval) -> dict:
    """§3.7. Computed from fields already on each row — no new grader, no new run."""
    arms = {"anchor": NEUTRAL_VARIANTS, "steered": STEERED_VARIANTS}
    out: dict = {"granularity": task or "pooled", "arms": {}, "deltas": {},
                 "label": None, "notes": []}

    tool_re = re.compile(M1_TOOL_NAME_PATTERN, re.I)
    solve_re = re.compile(M1_SOLVE_PATTERN, re.I)

    for arm_name, variants in arms.items():
        rows = [r for k, r in cell.rows.items()
                if k[K_VARIANT] in variants and (task is None or k[K_TASK] == task)]
        n = len(rows)
        comps = defaultdict(int)
        for r in rows:
            c = _component(r)
            if c:
                comps[c] += 1
        m1 = 0
        for r in rows:
            text = r.get("response") or ""
            pat = solve_re if r.get("task") == "solve" else tool_re
            if pat.search(text):
                m1 += 1
        lengths = [r.get("done_reason") == "length" for r in rows]
        completions = [(r.get("tokens") or {}).get("completion")
                       for r in rows]
        completions = [c for c in completions if isinstance(c, (int, float))]
        at_cap = sum(1 for r in rows
                     if len(r.get("response") or "") == AT_CAP_RESPONSE_LEN)
        censored = sum(1 for r in rows if is_censored(r))

        out["arms"][arm_name] = {
            "n": n,
            "success_pp": pct(sum(1 for r in rows if delivered(r)), n),
            "components_pp": {c: pct(comps.get(c, 0), n)
                              for c in ("TRUNCATED_LOSS", "CHANNEL_FORMAT",
                                        "CONTENT", "APPARATUS")},
            "M1_directive_echo_pp": pct(m1, n),
            "M2_done_reason_length_pp": pct(sum(lengths), n),
            "M2_mean_completion_tokens": (statistics.fmean(completions)
                                          if completions else math.nan),
            "M2_median_completion_tokens": (statistics.median(completions)
                                            if completions else math.nan),
            "M2_at_cap_pp": pct(at_cap, n),
            "censored_at_cap_pp": pct(censored, n),
        }

    # Component deltas on the same paired domain-clustered footing as §3.3.
    for comp in ("TRUNCATED_LOSS", "CHANNEL_FORMAT", "CONTENT", "APPARATUS"):
        pairs = build_pairs(cell, lo=NEUTRAL_VARIANTS, hi=STEERED_VARIANTS,
                            surface=lambda r, c=comp: _component(r) == c, task=task)
        ci = paired_cluster_ci(pairs, lambda p: p.domain, method="domain (k=20)")
        out["deltas"][comp] = _ci_dict(ci)

    sum_delta = sum(out["deltas"][c]["estimate_pp"]
                    for c in ("TRUNCATED_LOSS", "CHANNEL_FORMAT", "CONTENT",
                              "APPARATUS")
                    if not math.isnan(out["deltas"][c]["estimate_pp"]))
    out["sum_component_delta_pp"] = sum_delta
    # The identity is checked against the DOMAIN-clustered Δ̂ because that is the
    # clustering the component deltas are computed on. Checking it against the
    # governing interval would show a spurious residual whenever the problem
    # clustering happens to be the wider one.
    out["identity_reference_pp"] = domain_ci.estimate_pp
    out["identity_check_pp"] = sum_delta + domain_ci.estimate_pp
    out["notes"].append(
        "The four components partition Δ̂ exactly (ΣΔ = −Δ̂): this is an accounting "
        "split with CIs, not two independent measurements. Δtruncation must not be "
        "presented as corroborating ΔTRUNCATED-LOSS — they are the same rows.")

    # Guards.
    anchor = out["arms"]["anchor"]
    steered = out["arms"]["steered"]
    for arm_name, a in (("anchor", anchor), ("steered", steered)):
        if a["components_pp"]["APPARATUS"] / 100.0 > APPARATUS_VOID_SHARE:
            out["label"] = "VOID"
            out["notes"].append(
                f"APPARATUS share {a['components_pp']['APPARATUS']:.2f}% in the "
                f"{arm_name} arm exceeds 1% — this cell's mechanism read is VOID.")
    if anchor["M2_done_reason_length_pp"] / 100.0 >= CEILING_GUARD_TRUNCATION:
        out["label"] = "MECHANISM-UNINFORMATIVE"
        out["notes"].append(
            f"Ceiling guard: anchor truncation {anchor['M2_done_reason_length_pp']:.1f}% "
            "≥ 75%, so the cell is mechanism-UNINFORMATIVE.")

    out["notes"].append(
        "M1 is an ARM DIFFERENCE, never an absolute: base rate in the roster neutral "
        "no-tools arms is 0/27,360, but that anchor is measured on 500-char snapshots "
        "and is a specificity floor. M1 is a lower bound on at-cap rows and is "
        "anti-correlated with displacement by construction, so a depressed M1 inside a "
        "displacement-dominated cell may not be read as 'no directive echo'.")
    out["M1_arm_difference_pp"] = (steered["M1_directive_echo_pp"]
                                   - anchor["M1_directive_echo_pp"])

    # A label is assigned only to a FAIL cell, at pooled granularity, |Δ̂| ≥ 9pp,
    # and only when the dominant component's share CI excludes 0.5.
    if out["label"] is None:
        if verdict != "FAIL":
            out["notes"].append("No mechanism label: assigned only to cells whose H4 "
                                "verdict is FAIL.")
        elif task is not None:
            out["notes"].append("No mechanism label: pooled granularity only.")
        elif abs(governing.estimate_pp) < MECHANISM_MIN_ABS_DELTA_PP:
            out["notes"].append(
                f"No mechanism label: |Δ̂| {abs(governing.estimate_pp):.1f}pp < "
                f"{MECHANISM_MIN_ABS_DELTA_PP:g}pp. Component SDs are ~0.7-0.9pp at "
                "n=4,560, so in the 6.5-9pp FAIL band the dominance call is near a "
                "coin flip.")
        else:
            out["label"] = _dominance_label(out, anchor, steered)
    return out


def _dominance_label(out: dict, anchor: dict, steered: dict) -> str | None:
    mags = {c: abs(out["deltas"][c]["estimate_pp"])
            for c in ("TRUNCATED_LOSS", "CHANNEL_FORMAT", "CONTENT")
            if not math.isnan(out["deltas"][c]["estimate_pp"])}
    if not mags:
        return None
    total = sum(mags.values())
    dom = max(mags, key=mags.get)
    if total <= 0 or mags[dom] / total <= 0.5:
        out["notes"].append("No mechanism label: no component's share exceeds 0.5.")
        return None
    if dom == "TRUNCATED_LOSS":
        moved = (steered["M2_mean_completion_tokens"]
                 - anchor["M2_mean_completion_tokens"])
        if math.isnan(moved) or moved == 0:
            out["notes"].append("TRUNCATED-LOSS dominates but mean completion tokens "
                                "did not move with it; no DISPLACEMENT label.")
            return None
        return "DISPLACEMENT"
    if dom == "CONTENT":
        return "REASONING SHIFT"
    return "CHANNEL"


def leakage_spearman(per_task: dict) -> dict:
    """§3.7 help direction: only meaningful when the FAIL is positive."""
    tasks = [t for t in TASKS if t in per_task
             and not math.isnan(per_task[t]["_governing_obj"].estimate_pp)]
    if len(tasks) < 3:
        return {"rho": math.nan, "p": math.nan, "n": len(tasks),
                "note": "too few estimable tasks"}
    deltas = [per_task[t]["_governing_obj"].estimate_pp for t in tasks]
    ranks = [LEAKAGE_RANK[t] for t in tasks]
    rho, p = stats.spearmanr(deltas, ranks)
    return {"rho": float(rho), "p": float(p), "n": len(tasks),
            "tasks": tasks,
            "note": "Per-task half-widths make the middle ranks unresolvable; "
                    "concentration at the bottom of the ranking is reported as "
                    "unexplained."}


# ==========================================================================
# Per-cell driver
# ==========================================================================

def analyse_cell(cell: Cell, f_gate: dict) -> dict:
    gate = completeness_gate(cell)
    fg = next((c for c in f_gate["cells"] if c["cell"] == cell.name), None)
    if fg is None:
        raise SystemExit(
            f"F gate has no entry for cell {cell.name!r}. The F gate must be produced "
            "from the same overlay corpus, before the contrast (§7 step 3).")

    result: dict = {
        "cell": cell.name, "model": cell.model, "think": cell.think,
        "rows": cell.n, "duplicates_dropped": cell.duplicates_dropped,
        "completeness": {"ok": gate.ok, "lines": gate.lines},
        "pooled": None, "per_task": {}, "verdict": None, "mdE": {},
    }
    if not gate.ok:
        result["verdict"] = "INCONCLUSIVE (incomplete cell)"
        result["completeness"]["lines"].append(
            "Incomplete cells are INCONCLUSIVE and are NOT analysed on the surviving "
            "subset (§3.1); the missing keys must be re-run to completion.")
        return result

    pooled = contrast(cell, task=None)
    pooled_f = fg["granularity"]["pooled"]["F_pp"]
    pooled_ci = pooled["_governing_obj"]
    pooled_label, pooled_underpowered = label(pooled_ci)
    pooled["F_pp"] = pooled_f
    pooled["F_ge_margin"] = fg["granularity"]["pooled"]["F_ge_margin"]
    pooled["label"] = pooled_label
    pooled["underpowered"] = pooled_underpowered
    pooled["mde_pp"] = MARGIN_PP + (pooled_ci.half_width_pp
                                    if not math.isnan(pooled_ci.half_width_pp) else 0.0)
    result["pooled"] = pooled

    eligible_names, pvalues = [], {}
    for task in TASKS:
        c = contrast(cell, task=task)
        ci = c["_governing_obj"]
        f_pp = fg["granularity"][task]["F_pp"]
        cls = classify(c["anchor"]["rate_pp"], f_pp, ci.half_width_pp)
        lab, under = label(ci)
        c.update({"F_pp": f_pp, "classification": cls, "label": lab,
                  "underpowered": under,
                  "mde_pp": MARGIN_PP + (ci.half_width_pp
                                         if not math.isnan(ci.half_width_pp) else 0.0)})
        if cls == "LOW-BASE-RATE":
            c["risk_ratio"] = risk_ratio_bound(
                c["anchor"]["x"], c["anchor"]["n"],
                c["steered"]["x"], c["steered"]["n"])
        if cls == "DEGENERATE":
            c["note"] = ("Anchor is exactly 0% or 100%; 0-vs-0 equivalence is vacuous, "
                         "so only a one-sided bound is reported.")
        if cls == "ELIGIBLE":
            eligible_names.append(task)
            pvalues[task] = noninferiority_p(ci)
        result["per_task"][task] = c

    # §3.4 verdict.
    eligible_not_equiv = [t for t in eligible_names
                          if result["per_task"][t]["label"] == "NOT-EQUIVALENT"]
    if pooled_ci.inside_margin() and not eligible_not_equiv:
        verdict = "PASS"
    elif pooled_ci.outside_margin() or eligible_not_equiv:
        verdict = "FAIL"
    else:
        verdict = "INCONCLUSIVE"
    result["verdict"] = verdict
    result["fail_driver"] = ("eligible_task" if eligible_not_equiv
                             else ("pooled" if verdict == "FAIL" else None))
    result["eligible_tasks"] = eligible_names
    result["eligible_not_equivalent"] = eligible_not_equiv

    # Holm across the ELIGIBLE family only, and only for the affirmative claim.
    result["holm_rejected"] = holm(pvalues) if pvalues else {}
    result["holm_pvalues"] = pvalues
    result["multiplicity_note"] = (
        "Intersection-union: the conjunctive equivalence claim needs no α correction "
        "and none is applied. Holm covers the ELIGIBLE family only, for the affirmative "
        "non-equivalence claim. Family membership is frozen by the pre-registered rule "
        "and is never re-picked after seeing Δ̂.")

    if verdict == "PASS" and pooled["anchor"]["rate_pp"] < 15.0 and cell.think == "on":
        result["scope_note"] = ("think=on PASS at an anchor < 15% licenses only the "
                                "absolute ±5pp statement.")

    pooled_domain_ci = Interval(**{k: v for k, v in pooled["ci"]["domain"].items()})
    result["mechanism"] = {
        "pooled": mechanism(cell, task=None, verdict=verdict, governing=pooled_ci,
                            domain_ci=pooled_domain_ci)}
    if verdict == "FAIL" and pooled_ci.estimate_pp > 0:
        result["mechanism"]["help_direction"] = leakage_spearman(result["per_task"])

    # Strip the non-serialisable working objects.
    pooled.pop("_governing_obj", None)
    for t in result["per_task"].values():
        t.pop("_governing_obj", None)
    return result


def paper_branch(cells: list[dict]) -> dict:
    """§3.4 paper-level table over the verdict vector."""
    verdicts = [c.get("verdict") for c in cells]
    fails_eligible = [c["cell"] for c in cells
                      if c.get("verdict") == "FAIL"
                      and c.get("fail_driver") == "eligible_task"]
    fails_other = [c["cell"] for c in cells
                   if c.get("verdict") == "FAIL" and c.get("fail_driver") != "eligible_task"]
    if fails_eligible:
        return {"branch": "FAIL", "cells": fails_eligible,
                "note": "≥1 FAIL in an ELIGIBLE cell — no 'named exception' escape."}
    if fails_other:
        return {"branch": "MIXED", "cells": fails_other,
                "note": "FAILs only outside the ELIGIBLE family; cells named."}
    if verdicts and all(v == "PASS" for v in verdicts):
        return {"branch": "PASS", "cells": [], "note": "All units PASS."}
    return {"branch": "INCONCLUSIVE", "cells": [c["cell"] for c in cells
                                                if c.get("verdict") != "PASS"],
            "note": "Not all units PASS and no ELIGIBLE FAIL."}


# ==========================================================================
# Rendering
# ==========================================================================

def _fmt_ci(d: dict) -> str:
    if math.isnan(d["estimate_pp"]):
        return "—"
    if math.isnan(d["lo_pp"]):
        return f"{d['estimate_pp']:+.2f}"
    return f"{d['estimate_pp']:+.2f} [{d['lo_pp']:+.2f}, {d['hi_pp']:+.2f}]"


def render(results: list[dict], branch: dict, gt_hash: str) -> str:
    L = [f"# nt-ster H4 — confirmatory contrast", "",
         f"Margin ±{MARGIN_PP:g}pp · {int((1-ALPHA)*100)}% intervals · surface = "
         f"delivered · bootstrap B={BOOTSTRAP_B:,} · GT gate `{gt_hash[:12]}`", "",
         "Δ̂ = steered − anchor. The governing interval is the **wider** of the "
         "domain (k=20) and problem-instance (k=100) clusterings.", "",
         f"## Paper-level branch: **{branch['branch']}**", "", branch["note"], ""]
    if branch["cells"]:
        L += ["Cells: " + ", ".join(branch["cells"]), ""]

    L += ["## Verdict vector", "",
          "| cell | anchor | steered | Δ̂ governing | F | verdict |",
          "|---|---:|---:|---|---:|---|"]
    for r in results:
        if r["pooled"] is None:
            L.append(f"| {r['cell']} | — | — | — | — | {r['verdict']} |")
            continue
        p = r["pooled"]
        L.append(f"| {r['cell']} | {p['anchor']['rate_pp']:.1f}% | "
                 f"{p['steered']['rate_pp']:.1f}% | "
                 f"{_fmt_ci(p['ci']['governing'])} | {p['F_pp']:.2f} | "
                 f"**{r['verdict']}** |")
    L.append("")

    for r in results:
        L += [f"## {r['cell']}", ""]
        for ln in r["completeness"]["lines"]:
            L.append(f"- {ln}")
        L.append("")
        if r["pooled"] is None:
            continue
        p = r["pooled"]
        L += ["**Pooled (primary).** "
              f"anchor {p['anchor']['rate_pp']:.2f}% ({p['anchor']['x']}/{p['anchor']['n']}), "
              f"steered {p['steered']['rate_pp']:.2f}% ({p['steered']['x']}/{p['steered']['n']}), "
              f"{p['n_pairs']:,} matched pairs.", "",
              "| interval | Δ̂ [90% CI] | half-width |", "|---|---|---:|"]
        for name in ("domain", "problem", "governing", "bootstrap_domain",
                     "newcombe_unpaired"):
            d = p["ci"][name]
            hw = "—" if math.isnan(d["half_width_pp"]) else f"{d['half_width_pp']:.2f}pp"
            L.append(f"| {name} | {_fmt_ci(d)} | {hw} |")
        L += ["",
              f"- row-level pooled Δ: {p['pooled_row_level_delta_pp']:+.2f}pp "
              "(cluster-mean vs row-level agree when clusters are balanced)",
              f"- label: **{p['label']}**"
              + (" · UNDERPOWERED" if p["underpowered"] else ""),
              f"- MDE (|Δ| needed to FAIL): {p['mde_pp']:.2f}pp", ""]
        if r.get("scope_note"):
            L += [f"- scope: {r['scope_note']}", ""]

        L += ["**Per task.** Classification is assigned mechanically from the anchor "
              "and the realized precision, before the label is read.", "",
              "| task | anchor | Δ̂ governing | half-width | F | class | label | MDE |",
              "|---|---:|---|---:|---:|---|---|---:|"]
        for t in TASKS:
            c = r["per_task"][t]
            g = c["ci"]["governing"]
            hw = "—" if math.isnan(g["half_width_pp"]) else f"{g['half_width_pp']:.2f}"
            lab = c["label"] + (" ⚠" if c["underpowered"] else "")
            L.append(f"| {t} | {c['anchor']['rate_pp']:.1f}% | {_fmt_ci(g)} | {hw} | "
                     f"{c['F_pp']:.2f} | {c['classification']} | {lab} | "
                     f"{c['mde_pp']:.2f} |")
        L.append("")
        for t in TASKS:
            c = r["per_task"][t]
            if "risk_ratio" in c and not math.isnan(c["risk_ratio"].get("rr", math.nan)):
                rr = c["risk_ratio"]
                L.append(f"- `{t}` LOW-BASE-RATE: RR {rr['rr']:.2f} "
                         f"[{rr.get('lo', float('nan')):.2f}, {rr.get('hi', float('nan')):.2f}]; "
                         f"±{MARGIN_PP:g}pp at this anchor admits up to "
                         f"{rr['margin_equivalent_rr']:.2f}× relative.")
            if "note" in c:
                L.append(f"- `{t}`: {c['note']}")
        L.append("")

        if r.get("eligible_tasks"):
            L += [f"- ELIGIBLE family: {', '.join(r['eligible_tasks'])}",
                  f"- {r['multiplicity_note']}", ""]

        m = r["mechanism"]["pooled"]
        L += ["**Mechanism (secondary — never gates or revises the verdict).**", "",
              f"- label: {m['label'] or 'none assigned'}", "",
              "| component | anchor | steered | Δ̂ [90% CI] |", "|---|---:|---:|---|"]
        for comp in ("TRUNCATED_LOSS", "CHANNEL_FORMAT", "CONTENT", "APPARATUS"):
            L.append(f"| {comp} | {m['arms']['anchor']['components_pp'][comp]:.2f}% | "
                     f"{m['arms']['steered']['components_pp'][comp]:.2f}% | "
                     f"{_fmt_ci(m['deltas'][comp])} |")
        L += ["",
              f"- ΣΔ components {m['sum_component_delta_pp']:+.2f}pp vs −Δ̂ "
              f"{-m['identity_reference_pp']:+.2f}pp (domain clustering, the footing "
              f"the components are computed on; residual "
              f"{m['identity_check_pp']:+.3f}pp)",
              f"- M1 directive echo, ARM DIFFERENCE: {m['M1_arm_difference_pp']:+.2f}pp "
              f"(anchor {m['arms']['anchor']['M1_directive_echo_pp']:.2f}% → steered "
              f"{m['arms']['steered']['M1_directive_echo_pp']:.2f}%)",
              f"- M2 budget: done_reason=length "
              f"{m['arms']['anchor']['M2_done_reason_length_pp']:.1f}% → "
              f"{m['arms']['steered']['M2_done_reason_length_pp']:.1f}%; "
              f"mean completion tokens "
              f"{m['arms']['anchor']['M2_mean_completion_tokens']:.0f} → "
              f"{m['arms']['steered']['M2_mean_completion_tokens']:.0f}; at-cap "
              f"{m['arms']['anchor']['M2_at_cap_pp']:.1f}% → "
              f"{m['arms']['steered']['M2_at_cap_pp']:.1f}%",
              f"- censored at snapshot cap (reported separately, folded into neither "
              f"side): anchor {m['arms']['anchor']['censored_at_cap_pp']:.2f}%, "
              f"steered {m['arms']['steered']['censored_at_cap_pp']:.2f}%", ""]
        for note in m["notes"]:
            L.append(f"  > {note}")
        L.append("")
        if "help_direction" in r["mechanism"]:
            h = r["mechanism"]["help_direction"]
            L += [f"- help-direction leakage ranking: Spearman ρ = {h['rho']:.3f} "
                  f"(p = {h['p']:.3f}, n = {h['n']}). {h['note']}", ""]

    L += ["---", "",
          "**Control conservatism (§3.5).** Under `with_tools=False` the system prompt "
          "is always `WITHOUT_TOOLS_SYSTEM_BY_TASK[task]` regardless of variant, which "
          "states that validation tools are not available, while the steered v14-16 "
          "user text tells the model to use a named tool. The control therefore removes "
          "both the tool and its stated availability, which **biases H4 toward PASS** — "
          "a PASS is weaker evidence than an unqualified reading would suggest.", "",
          "**Serving nondeterminism** at T=0 is unbounded by our corpora: decoding is "
          "greedy and unseeded, and no prompt was ever measured twice under one "
          "apparatus. Registered as a stated limitation, not a number.", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--overlay-dir", type=Path, required=True)
    ap.add_argument("--f-gate", type=Path, required=True,
                    help="output of tools/ntster_f_gate.py — REQUIRED, and must "
                         "describe the same overlay corpus")
    ap.add_argument("--out", type=Path,
                    default=Path("results/derived/ntster_h4_results.json"))
    ap.add_argument("--markdown", type=Path,
                    default=Path("results/derived/ntster_h4_report.md"))
    ap.add_argument("--gt-cache", type=Path,
                    default=Path("results/derived/gt_cache.json"))
    ap.add_argument("--gt-stamp", type=Path,
                    default=Path("results/derived/gt_cache_stamp.json"))
    args = ap.parse_args()

    if not args.f_gate.exists():
        raise SystemExit(
            f"F-gate output not found: {args.f_gate}\n"
            "H4 refuses to run without it. Run tools/ntster_f_gate.py first — F is "
            "pre-registered to be computed before the contrast is read (§3.2, §7).")
    f_gate = json.loads(args.f_gate.read_text())
    if f_gate.get("overlay_dir") and Path(f_gate["overlay_dir"]) != args.overlay_dir:
        raise SystemExit(
            f"F gate was produced from {f_gate['overlay_dir']!r} but this run points at "
            f"{str(args.overlay_dir)!r}. Corpus identity is load-bearing; refusing.")

    gt_hash = assert_gate(args.gt_cache, args.gt_stamp)
    print(f"gt gate: PASS {gt_hash[:12]}")

    cells = load_overlay_cells(args.overlay_dir)
    print(f"loaded {len(cells)} cell(s) from {args.overlay_dir}")

    results = [analyse_cell(c, f_gate) for c in cells]
    branch = paper_branch(results)

    payload = {
        "produced_by": "tools/ntster_h4.py",
        "prereg": "development/ntster_h4_prereg.md §3.3-§3.7",
        "overlay_dir": str(args.overlay_dir),
        "f_gate": str(args.f_gate),
        "gt_gate_hash": gt_hash,
        "margin_pp": MARGIN_PP, "alpha": ALPHA, "bootstrap_b": BOOTSTRAP_B,
        "surface": "delivered (overlay e2e)",
        "paper_branch": branch,
        "cells": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"results written: {args.out}")

    md = render(results, branch, gt_hash)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(md + "\n")
    print(f"report written: {args.markdown}")
    print()
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
