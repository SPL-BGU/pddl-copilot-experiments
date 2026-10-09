"""Readout-time tripwires (freeze protocol, "halt the readout").

Each tripwire returns a message when it fires. The entry point halts with a
non-zero exit on any fired tripwire that the operator has not explicitly
listed as audited (`--audited-tripwires`); audited ones are recorded in the
readout. None of them changes a registered verdict: they decide only whether
a readout may be written before a human has looked.

Bands (T4) and why they are this wide
-------------------------------------
* Tool-verified rate of a rerun cell: within ±30 points of the canonical
  cell. The parity rule already acts at 5 / 10 points with fixed
  consequences; the band sits three times past the gross threshold so it can
  never pre-empt a registered parity consequence, and only catches a column
  that is not what it claims to be (the shipped 4B simulate 41.7 vs 17.1).
* Delivered rate of a rerun cell: inside
  [low − 20, high + 20 + empty-length share + prefix share] of the canonical
  cell, where low/high are the canonical censoring bounds (constants.
  CANONICAL_DELIVERED_COUNTS; the true old-apparatus delivered rate lies
  inside them by construction). Two registered apparatus deltas can only ADD
  delivered successes relative to canonical: the overflow retry (delta 2)
  acts on rows that ended in an empty answer with done_reason "length"
  (failures in canonical), and the prefix normalisation (delta 3) acts on
  answers that start with the leaked prefix. Both shares are counted on the
  canonical rows of the cell. The ±20 slack covers run-to-run noise on
  the delivered layer, which the parity guard does not measure.
* Part B has no canonical counterpart, so it has no band. Part C's delivered
  rate has no registered band (§8b item 15 names only the two above); T3
  still covers it.
"""
from __future__ import annotations

from .analysis import MET, VOID, Contrast, GapCell, Parity, RateCell
from . import constants as C
from . import e4 as E4
from .grade import has_prefix
from .schema import LoadedCell

TV_BAND = 30.0
DLV_SLACK = 20.0
FALLBACK_SHARE = 10.0     # "a fallback bucket absorbing double-digit shares in every arm"


def delivered_band(design: C.Design, canon: LoadedCell, task: str, arm: str) -> tuple[float, float]:
    n, ok, cens = design.canonical_delivered_counts[(canon.spec.model_tag, task, arm)]
    rows = [r for r in canon.rows if r.task == task and r.arm == arm]
    assert len(rows) == n, (canon.spec.name, task, arm, len(rows), n)
    empty_len = sum(1 for r in rows if r.response == "" and r.done_reason == "length")
    prefix = sum(1 for r in rows if has_prefix(r.response))
    low = 100 * ok / n - DLV_SLACK
    high = 100 * (ok + cens + empty_len + prefix) / n + DLV_SLACK
    return max(0.0, low), min(100.0, high)


def _tv(cell: LoadedCell, task: str, arm: str) -> float:
    rows = [r for r in cell.rows if r.task == task and r.arm == arm]
    return 100 * sum(r.success for r in rows) / len(rows)


def check(design: C.Design, par: Parity, e1: list[RateCell], gaps: list[GapCell],
          e2: list[Contrast], rerun_a: dict[str, LoadedCell],
          canon_tools: dict[str, LoadedCell]) -> dict[str, str]:
    fired: dict[str, str] = {}
    # T1/T2: a guard firing everywhere is a bug report, not a result.
    if all(c.verdict != MET for c in par.cells):
        fired["T1_parity_fails_everywhere"] = (
            f"parity criterion not met in all {len(par.cells)} cells")
    if all(c.verdict == VOID for c in par.cells):
        fired["T2_void_everywhere"] = "every parity cell is VOID (unpaired rows)"
    # T3: a constant output column is a schema bug until proven otherwise.
    cols = {
        "tool_verified_rerun": [c.tv_rerun_pct for c in par.cells],
        "parity_delta": [c.delta for c in par.cells],
        "delivered": [c.delivered_pct for c in e1],
        "invocation": [c.invocation_pct for c in e1],
        "no_room_share": [c.no_room_pct for c in e1],
        "e4_gap_share": [g.gap_pct for g in gaps if g.gap_pct is not None],
        "part_c_delivered": [c.a_pct for c in e2],
    }
    for name, vals in cols.items():
        if len(vals) > 1 and len(set(vals)) == 1:
            fired[f"T3_constant_{name}"] = f"{name} is {vals[0]} in all {len(vals)} cells"
    # T4: bands.
    out = []
    for c in par.cells:
        canon_tv = _tv(canon_tools[c.model], c.task, c.arm)
        rerun_tv = _tv(rerun_a[c.model], c.task, c.arm)
        if abs(rerun_tv - canon_tv) > TV_BAND:
            out.append(f"{c.model}/{c.task}/{c.arm} tool-verified {rerun_tv:.1f} vs "
                       f"canonical {canon_tv:.1f}")
    for c in e1:
        lo, hi = delivered_band(design, canon_tools[c.model], c.task, c.arm)
        if not (lo <= c.delivered_pct <= hi):
            out.append(f"{c.model}/{c.task}/{c.arm} delivered {c.delivered_pct:.1f} "
                       f"outside [{lo:.1f}, {hi:.1f}]")
    if out:
        fired["T4_rate_outside_band"] = "; ".join(out)
    # T5: the E4 fallback bucket absorbing double-digit shares in every cell.
    shares = [100 * g.categories[E4.NEEDS_READING] / g.n_gap for g in gaps if g.n_gap]
    if shares and all(s >= FALLBACK_SHARE for s in shares):
        fired["T5_needs_reading_everywhere"] = (
            f"NEEDS_READING is >= {FALLBACK_SHARE:.0f}% of the gap in all "
            f"{len(shares)} cells with a gap")
    return fired
