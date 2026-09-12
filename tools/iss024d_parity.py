#!/usr/bin/env python3
"""Pre-registered parity check: iss024d-e2e vs sweep5v2-live (tool-verified).

Implements development/iss024d_parity_prereg.md (registered 2026-07-12, before
any iss024d outcome metric was computed) exactly:

  Primary endpoint   per-cell delta = p(iss024d) - p(sweep5v2-live) on
                     TOOL-VERIFIED success (the stored `success` field, graded
                     online on uncapped tool results in both corpora — the
                     snapshot-cap delta cannot touch it), neutral bank
                     (v11-13 pooled), per model x task, think=on x
                     tools_all_minimal.
  Equivalence (TOST) a cell PASSES if the 90% Newcombe (Wilson-score) CI for
                     delta lies entirely within +-5pp (two one-sided tests at
                     alpha = .05).
  Decision rule      gemma (no reasoning parser ever -> zero generative delta)
                     is the negative control, evaluated FIRST; if any gemma
                     cell fails, the empirical noise floor F = max |delta|
                     over gemma cells calibrates Qwen failures. Job-level
                     parity holds iff >=18/20 Qwen cells pass AND no Qwen
                     |delta| > 10pp. The rule is only evaluated on the
                     complete 25-cell table; partial corpora get a DEFERRED
                     banner, never a verdict.
  Secondary          (mechanism, not gates) format_parse_fail rate delta and
                     truncated rate delta per cell (neutral bank), and
                     per-variant success-delta heterogeneity across the full
                     v11-16 bank (descriptive; steered v14-16 are
                     diagnostic-only per paper_notes 2026-07-12).

Corpora are never pooled (corpus-identity rule); trials are deduped by trial
key (last occurrence wins, matching resume semantics) so mop-up re-runs can't
inflate denominators. Interpretation language is bound by paper_notes
2026-07-12: pass or fail, iss024d numbers are "independent rerun estimates
under full-response storage", never "the resolved exact value of" a censored
sweep5v2 cell.

Usage:
  python tools/iss024d_parity.py                    # console table, defaults
  python tools/iss024d_parity.py --md results/derived/iss024d_parity.md
"""

import argparse
import datetime
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "analyzer" / "scripts"))

from _constants import iter_cells  # noqa: E402
from pddl_eval.summary import NEUTRAL_VARIANTS, wilson_ci  # noqa: E402

TASK_ORDER = ("validate_domain", "validate_problem", "validate_plan",
              "solve", "simulate")
THINK = "on"
COND = "tools_all_minimal"
RUN_TAG = "iss024d-e2e"
ALL_VARIANTS = (11, 12, 13, 14, 15, 16)
STEERED = (14, 15, 16)

# TOST at alpha=.05 <=> 90% two-sided CI inside the margin.
Z90 = 1.6448536269514722
MARGIN = 0.05   # +-5pp equivalence margin (prereg)
GROSS = 0.10    # no Qwen cell may exceed 10pp |delta| (decision rule 2)

# Fixed roster = the 25-cell table the decision rule is defined over.
QWEN_MODELS = ("Qwen3_5_0_8B", "Qwen3_5_4B", "Qwen3_5_9B", "qwen3_6_35b")
CONTROL_MODELS = ("gemma4_26b-a4b",)


class Tally:
    """Per model x task accumulator."""

    __slots__ = ("n", "k", "fpf", "trunc", "var")

    def __init__(self):
        self.n = 0        # neutral-bank denominators
        self.k = 0        # tool-verified successes (neutral bank)
        self.fpf = 0      # failure_reason == format_parse_fail (neutral bank)
        self.trunc = 0    # truncated flag set (neutral bank)
        self.var = defaultdict(lambda: [0, 0])  # variant -> [k, n], full bank


def load_corpus(root: Path, run_tag: str) -> tuple[dict, dict]:
    """Return ({(model, task): Tally}, stats). Dedup by trial key, last wins."""
    cells: dict[tuple[str, str], Tally] = {}
    stats = {"dup": 0, "infra": 0, "cells": 0}
    for cell_dir, info in iter_cells(root, run_tag=run_tag):
        if info.get("think") != THINK or info.get("cond") != COND:
            continue
        fp = cell_dir / "trials.jsonl"
        if not fp.exists():
            continue
        stats["cells"] += 1
        model = info["model"]
        seen: dict[tuple, dict] = {}
        with fp.open() as f:
            for line in f:
                try:
                    row = json.loads(line)
                    key, r = tuple(row["key"]), row["result"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                if key in seen:
                    stats["dup"] += 1
                seen[key] = r
        for r in seen.values():
            if r.get("infra_failure"):
                stats["infra"] += 1
                continue
            task = r.get("task")
            v = r.get("prompt_variant")
            if task not in TASK_ORDER or v not in ALL_VARIANTS:
                continue
            t = cells.setdefault((model, task), Tally())
            ok = r.get("success") is True
            kn = t.var[v]
            kn[1] += 1
            kn[0] += int(ok)
            if v in NEUTRAL_VARIANTS:
                t.n += 1
                t.k += int(ok)
                t.fpf += int(r.get("failure_reason") == "format_parse_fail")
                t.trunc += int(bool(r.get("truncated")))
    return cells, stats


def newcombe(k1: int, n1: int, k2: int, n2: int,
             z: float = Z90) -> tuple[float, float, float]:
    """Newcombe hybrid Wilson-score CI for p1 - p2."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_ci(k1, n1, z=z)
    l2, u2 = wilson_ci(k2, n2, z=z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


def build_rows(iss: dict, base: dict, models: tuple[str, ...]) -> list[dict]:
    rows = []
    for m in models:
        for task in TASK_ORDER:
            bi, ii = base.get((m, task)), iss.get((m, task))
            row = {"model": m, "task": task, "base": bi, "iss": ii}
            if bi and ii and bi.n and ii.n:
                d, lo, hi = newcombe(ii.k, ii.n, bi.k, bi.n)
                row.update(d=d, lo=lo, hi=hi,
                           tost=(lo >= -MARGIN and hi <= MARGIN))
            rows.append(row)
    return rows


def pp(x: float) -> str:
    return f"{100 * x:+.1f}"


def render_primary(rows: list[dict], title: str, noise_floor: float | None,
                   md: bool) -> list[str]:
    out = []
    if md:
        out.append(f"### {title}\n")
        out.append("| model | task | n(iss) | p(iss) | n(base) | p(base) | "
                   "Δpp | 90% CI (pp) | TOST |")
        out.append("|---|---|---|---|---|---|---|---|---|")
    else:
        out.append(f"\n{title}")
        out.append(f"{'model':15s} {'task':17s} {'n(iss)':>6s} {'p(iss)':>7s} "
                   f"{'n(base)':>7s} {'p(base)':>7s} {'Δpp':>6s} "
                   f"{'90% CI (pp)':>16s}  TOST")
    for r in rows:
        m, task, bi, ii = r["model"], r["task"], r["base"], r["iss"]
        if "d" not in r:
            missing = "iss024d" if (bi and bi.n) else "baseline"
            cells = (f"| {m} | {task} | — | — | — | — | — | — | "
                     f"not on disk ({missing}) |") if md else (
                     f"{m:15s} {task:17s} {'—':>6s}  … {missing} cell "
                     f"not on disk")
            out.append(cells)
            continue
        verdict = "PASS" if r["tost"] else "FAIL"
        if not r["tost"] and noise_floor is not None \
                and abs(r["d"]) <= noise_floor:
            verdict += " (≤ control noise floor)"
        ci = f"[{pp(r['lo'])}, {pp(r['hi'])}]"
        if md:
            out.append(f"| {m} | {task} | {ii.n} | {100 * ii.k / ii.n:.1f} | "
                       f"{bi.n} | {100 * bi.k / bi.n:.1f} | {pp(r['d'])} | "
                       f"{ci} | {verdict} |")
        else:
            out.append(f"{m:15s} {task:17s} {ii.n:6d} "
                       f"{100 * ii.k / ii.n:7.1f} {bi.n:7d} "
                       f"{100 * bi.k / bi.n:7.1f} {pp(r['d']):>6s} "
                       f"{ci:>16s}  {verdict}")
    return out


def render_secondary(rows: list[dict], md: bool) -> list[str]:
    out = []
    hdr = ("Secondary (neutral bank, descriptive): format_parse_fail and "
           "truncated rate deltas")
    if md:
        out.append(f"### {hdr}\n")
        out.append("| model | task | fpf(iss) | fpf(base) | Δfpf pp | "
                   "trunc(iss) | trunc(base) | Δtrunc pp |")
        out.append("|---|---|---|---|---|---|---|---|")
    else:
        out.append(f"\n{hdr}")
        out.append(f"{'model':15s} {'task':17s} {'fpf(iss)':>8s} "
                   f"{'fpf(base)':>9s} {'Δfpf':>6s} {'trc(iss)':>9s} "
                   f"{'trc(base)':>9s} {'Δtrc':>6s}")
    for r in rows:
        if "d" not in r:
            continue
        bi, ii = r["base"], r["iss"]
        f1, f2 = ii.fpf / ii.n, bi.fpf / bi.n
        t1, t2 = ii.trunc / ii.n, bi.trunc / bi.n
        if md:
            out.append(f"| {r['model']} | {r['task']} | {100 * f1:.1f} | "
                       f"{100 * f2:.1f} | {pp(f1 - f2)} | {100 * t1:.1f} | "
                       f"{100 * t2:.1f} | {pp(t1 - t2)} |")
        else:
            out.append(f"{r['model']:15s} {r['task']:17s} {100 * f1:8.1f} "
                       f"{100 * f2:9.1f} {pp(f1 - f2):>6s} {100 * t1:9.1f} "
                       f"{100 * t2:9.1f} {pp(t1 - t2):>6s}")
    return out


def render_variants(rows: list[dict], md: bool) -> list[str]:
    out = []
    hdr = ("Per-variant success delta (iss − base, pp; full v11-16 bank, "
           "descriptive; * = steered, diagnostic-only)")
    labels = [f"v{v}{'*' if v in STEERED else ''}" for v in ALL_VARIANTS]
    if md:
        out.append(f"### {hdr}\n")
        out.append("| model | task | " + " | ".join(labels) + " |")
        out.append("|---|---|" + "---|" * len(labels))
    else:
        out.append(f"\n{hdr}")
        out.append(f"{'model':15s} {'task':17s} "
                   + " ".join(f"{s:>6s}" for s in labels))
    for r in rows:
        if "d" not in r:
            continue
        bi, ii = r["base"], r["iss"]
        deltas = []
        for v in ALL_VARIANTS:
            (k1, n1), (k2, n2) = ii.var[v], bi.var[v]
            deltas.append(pp(k1 / n1 - k2 / n2) if n1 and n2 else "—")
        if md:
            out.append(f"| {r['model']} | {r['task']} | "
                       + " | ".join(deltas) + " |")
        else:
            out.append(f"{r['model']:15s} {r['task']:17s} "
                       + " ".join(f"{d:>6s}" for d in deltas))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iss-root", type=Path,
                    default=REPO / "results" / "iss024d-e2e-live")
    ap.add_argument("--baseline-root", type=Path,
                    default=REPO / "results" / "sweep5v2-live")
    ap.add_argument("--md", type=Path, default=None,
                    help="also write the report as markdown to this path")
    args = ap.parse_args()

    iss, iss_stats = load_corpus(args.iss_root, run_tag=RUN_TAG)
    base, base_stats = load_corpus(args.baseline_root, run_tag="")

    header = [
        "iss024d-e2e vs sweep5v2-live — tool-verified parity "
        "(pre-registered: development/iss024d_parity_prereg.md)",
        f"filters: think={THINK}, cond={COND}, neutral bank v11-13 pooled; "
        f"TOST margin ±{100 * MARGIN:.0f}pp at α=.05 (90% Newcombe CI, "
        f"z={Z90:.4f})",
        f"iss024d root: {args.iss_root}  "
        f"(cells={iss_stats['cells']}, dup={iss_stats['dup']}, "
        f"infra-excluded={iss_stats['infra']})",
        f"baseline root: {args.baseline_root}  "
        f"(cells={base_stats['cells']}, dup={base_stats['dup']}, "
        f"infra-excluded={base_stats['infra']})",
    ]

    ctrl_rows = build_rows(iss, base, CONTROL_MODELS)
    ctrl_done = [r for r in ctrl_rows if "d" in r]
    noise_floor = None
    if ctrl_done and not all(r["tost"] for r in ctrl_done):
        noise_floor = max(abs(r["d"]) for r in ctrl_done)
    qwen_rows = build_rows(iss, base, QWEN_MODELS)
    qwen_done = [r for r in qwen_rows if "d" in r]

    # Decision rule — only on the complete 25-cell table (prereg).
    decision = []
    n_present = len(ctrl_done) + len(qwen_done)
    if len(ctrl_done) == 5 and len(qwen_done) == 20:
        g_pass = sum(r["tost"] for r in ctrl_done)
        q_pass = sum(r["tost"] for r in qwen_done)
        q_max = max(abs(r["d"]) for r in qwen_done)
        parity = q_pass >= 18 and q_max <= GROSS
        decision.append(f"DECISION RULE (complete 25-cell table): "
                        f"gemma control {g_pass}/5 pass"
                        + (f" (noise floor F = {100 * noise_floor:.1f}pp)"
                           if noise_floor is not None else "")
                        + f"; Qwen {q_pass}/20 pass, "
                          f"max |Δ| = {100 * q_max:.1f}pp")
        decision.append(f"JOB-LEVEL PARITY: "
                        f"{'HOLDS' if parity else 'FAILS'} "
                        f"(rule: ≥18/20 Qwen pass AND no Qwen |Δ| > "
                        f"{100 * GROSS:.0f}pp)")
        if not parity:
            decision.append("Per prereg rule 4: report iss024d as a "
                            "separate-apparatus replication, clearly "
                            "labeled; never as 'the sweep5v2 cells "
                            "resolved'. No margin adjustment.")
        decision.append("Failing cells (if any) need a mechanism "
                        "decomposition (secondary endpoints) before any "
                        "headline use — prereg rule 3.")
    else:
        missing = [f"{r['model']}/{r['task']}"
                   for r in ctrl_rows + qwen_rows if "d" not in r]
        decision.append(f"DECISION RULE DEFERRED — {n_present}/25 cells "
                        f"comparable. Missing: {', '.join(missing)}")
    decision.append("Interpretation language (binding): iss024d numbers are "
                    "'independent rerun estimates under full-response "
                    "storage', never 'the resolved exact value of' a "
                    "censored sweep5v2 cell. Exact e2e is think=on-scoped.")

    def render(md: bool) -> list[str]:
        out = []
        if md:
            out.append("# iss024d-e2e vs sweep5v2-live — tool-verified "
                       "parity\n")
            out.append(f"Generated {datetime.date.today().isoformat()} by "
                       f"`tools/iss024d_parity.py`.\n")
            out.extend(f"- {h}" for h in header[1:])
            out.append("")
        else:
            out.append("=" * 100)
            out.extend(header)
            out.append("=" * 100)
        out.extend(render_primary(
            ctrl_rows, "Gemma negative control (evaluated first — zero "
            "generative delta, calibrates the noise floor)",
            None, md))
        out.append("")
        out.extend(render_primary(
            qwen_rows, "Qwen primary set (parser-off is the one generative "
            "delta)", noise_floor, md))
        out.append("")
        if md:
            out.append("### Decision\n")
        out.extend(decision)
        out.append("")
        out.extend(render_secondary(ctrl_rows + qwen_rows, md))
        out.append("")
        out.extend(render_variants(ctrl_rows + qwen_rows, md))
        return out

    print("\n".join(render(md=False)))
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text("\n".join(render(md=True)) + "\n")
        print(f"\nmarkdown written to {args.md}")


if __name__ == "__main__":
    main()
