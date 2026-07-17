"""Shared e2e-overlay aggregation — Phase 5 of the end-to-end grading work.

Single source for delivered-answer (end-to-end) columns: every table/deck
builder that shows e2e numbers must read them through `load_e2e_cells` so
that `results/derived/e2e_overlay/` (one rule set: D7/D7b tolerant
extraction, `e2e_strict` headline per the D2b revision of 2026-07-11 —
see development/tool_call_vs_final_output_grading.md) stays the only
place e2e verdicts are computed. This module aggregates; it never grades.

Censoring: rows whose stored response snapshot sits exactly at the cell's
snapshot cap are indeterminate (`e2e_strict == "indeterminate"`); a smaller
share of indeterminate rows come from other causes entirely (missing ground
truth, plan-validation transport errors) — the `cens_cap` / `cens_other`
split below separates the two for presentation only (2026-07-17). A cell
aggregate therefore carries a bounds pair:

    low  = ok / n            (every censored row counted as a failure)
    high = (ok + cens) / n   (every censored row counted as a success)

The two collapse to the same point when `cens == 0`; presentation layers
render a point (with Wilson CI) in that case and the `[low, high]` bounds
otherwise. Keep the values structured until render time — never sort or
diff on the formatted strings.

Cells are keyed by (model, think, cond, run_tag, arm, task). `run_tag` is
part of the identity on purpose: differently-tagged corpora (sweep5v2 vs
iss024d-e2e vs decoupled-thinkon) must never pool (corpus-identity rule).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from _constants import (  # noqa: E402
    arm_for,
    parse_dirname_full,
    wilson_ci,
)

# results/derived/e2e_overlay relative to a results root's parent
# (results/<corpus> → results/derived/e2e_overlay/<corpus>).
def default_overlay_root(results_root: Path) -> Path:
    return results_root.parent / "derived" / "e2e_overlay"


def load_e2e_cells(corpus: str | Path,
                   overlay_root: Path) -> dict[tuple, dict]:
    """Aggregate one overlay corpus into per-cell e2e numbers.

    `corpus` may be a results root (results/sweep5v2-live) or a bare corpus
    name; only its basename is used. Returns
        {(model, think, cond, run_tag, arm, task): cell}
    with cell = {n, ok, ok_b, cens, cens_cap, cens_other, low, high, low_b,
                 high_b, exact}:
        ok / ok_b   e2e_strict / e2e(D2b=B) == True counts
        cens        indeterminate (censored) rows, TOTAL — bounds math and
                    low/high/exact are computed from this total and are
                    UNCHANGED by the cens_cap/cens_other split below
        cens_cap    of `cens`, rows censored at the response-snapshot cap
                    (e2e_reason == "censored_at_snapshot_cap")
        cens_other  of `cens`, indeterminate for a different reason
                    (no_ground_truth / plan_validation_transport_error /
                    unknown_task) — NOT snapshot-cap censoring; split out
                    for presentation only (fmt_e2e), 2026-07-17
        low, high   e2e_strict bounds as fractions (== point when exact)
        exact       True when cens == 0
    Raises FileNotFoundError when the corpus has no overlay directory —
    callers should tell the user to run tools/e2e_regrade.py first.
    """
    corpus_dir = overlay_root / Path(corpus).name
    if not corpus_dir.is_dir():
        raise FileNotFoundError(
            f"no overlay for corpus {Path(corpus).name!r} under "
            f"{overlay_root} — run tools/e2e_regrade.py on it first")
    counts: dict[tuple, dict] = defaultdict(
        lambda: {"n": 0, "ok": 0, "ok_b": 0, "cens": 0, "cens_cap": 0,
                 "cens_other": 0, "tv_ok": 0, "tv_n": 0})
    for f in sorted(corpus_dir.glob("*.e2e.jsonl")):
        stem = f.name.removesuffix(".e2e.jsonl")
        info = parse_dirname_full(stem)
        if info["cond"] == "?":
            if stem.startswith("slurm"):
                # A slurm_*-shaped cell name the dirname parser could not
                # parse is a real bug (typo'd model/think/cond segment, a
                # condition the parser doesn't know about, ...) — the
                # frontier-inference fallback below is only for non-slurm
                # (prompt-corpus-named) stems. Silently mislabeling it as a
                # frontier cell would corrupt the aggregate under a wrong
                # key instead of surfacing the parse failure (2026-07-17
                # review fix).
                raise ValueError(
                    f"{stem!r}: unparseable slurm-shaped overlay stem — fix "
                    "the cell dirname or the parser")
            # Frontier corpora name their cells by prompt corpus rather
            # than the slurm_ shape (e.g. `sweep5v2-with-tools`,
            # `sweep6`). Model = the corpus itself (haiku-frontier,
            # sonnet-frontier, ...); the prompt-corpus prefix rides in
            # run_tag so canonical and anon cells can never pool.
            cond = ("tools_all_minimal" if "with-tools" in stem
                    else "no-tools")
            base = (Path(corpus).name, "default", cond,
                    stem.removesuffix("-with-tools"))
        else:
            base = (info["model"], info["think"], info["cond"],
                    info.get("run_tag", ""))
        for ln in f.open():
            r = json.loads(ln)
            arm = arm_for(bool(r.get("with_tools")),
                          r.get("prompt_variant"))
            c = counts[base + (arm, r["task"])]
            c["n"] += 1
            if r["e2e_strict"] is True:
                c["ok"] += 1
            elif r["e2e_strict"] == "indeterminate":
                c["cens"] += 1
                if r.get("e2e_reason") == "censored_at_snapshot_cap":
                    c["cens_cap"] += 1
                else:
                    c["cens_other"] += 1
            if r["e2e"] is True:
                c["ok_b"] += 1
            # stored tool-verified success rides along for gap columns
            # (None on no-tools rows)
            if r.get("tool_verified") is not None:
                c["tv_n"] += 1
                if r["tool_verified"]:
                    c["tv_ok"] += 1
    cells: dict[tuple, dict] = {}
    for key, c in counts.items():
        n = c["n"]
        cells[key] = {
            **c,
            "low": c["ok"] / n,
            "high": (c["ok"] + c["cens"]) / n,
            "low_b": c["ok_b"] / n,
            "high_b": (c["ok_b"] + c["cens"]) / n,
            "exact": c["cens"] == 0,
        }
    return cells


def fmt_e2e(cell: dict | None) -> str:
    """Render one e2e_strict aggregate for tables.

    exact cell           → `62 [58.1–64.3]` (point + Wilson 95% CI, matching
                           the tool-verified column format)
    censored, all cens
    are snapshot-cap      → `48.2–71.5 (c692/3000)` (bounds + censored row
                           count) — unchanged from the pre-split rendering.
    censored, some cens
    are non-cap           → `48.2–71.5 (c692+u17/3000)` (2026-07-17): `c` is
                           rows censored at the response-snapshot cap, `u` is
                           the remaining indeterminate rows for a non-cap
                           reason (missing ground truth or a plan-validation
                           transport error) — see load_e2e_cells' docstring.
    missing               → `—`
    """
    if cell is None or cell["n"] == 0:
        return "—"
    if cell["exact"]:
        lo, hi = wilson_ci(cell["ok"], cell["n"])
        return f"{int(round(cell['low'] * 100))} [{lo * 100:.1f}–{hi * 100:.1f}]"
    if cell["cens_other"] == 0:
        return (f"{cell['low'] * 100:.1f}–{cell['high'] * 100:.1f} "
                f"(c{cell['cens']}/{cell['n']})")
    return (f"{cell['low'] * 100:.1f}–{cell['high'] * 100:.1f} "
            f"(c{cell['cens_cap']}+u{cell['cens_other']}/{cell['n']})")
