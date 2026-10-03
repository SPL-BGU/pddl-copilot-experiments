"""Parity guard (§3), endpoints E1–E4 (§4) and readings R1–R5 (§5).

Inputs are typed `Row`s from schema.load_cell and `Delivered` grades from
grade.grade; nothing here reads a file or a dict-shaped row. Every reading is
emitted as one of the label strings below, verbatim from the prereg tables,
never as free text.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

from . import constants as C
from . import e4 as E4
from .grade import Delivered
from .schema import LoadedCell, Row, SchemaError
from .stats import (Boot, cluster_bootstrap, domain_sums, holm, newcombe,
                    signflip_exact_p, tost_met)

# ------------------------------------------------------------------ labels
MET = "criterion met"
NOT_MET = "criterion not met (unresolved)"
VOID = "VOID"
JOB_HOLDS = "Parity holds"
JOB_FAILS = "Parity fails at job level"
CONSEQ_EXACT = ("reported as the exact delivered rate of the headline cell, "
                "with the apparatus deltas of §2 stated")
CONSEQ_CELL_FAIL = "separate-apparatus measurement, labelled; criterion not met (unresolved)"
CONSEQ_JOB_FAIL = "separate-apparatus replication (whole rerun)"

R1_HARM = "Harm confirmed on the primary outcome."
R1_NO_HARM = "No delivered harm."
R1_UNRESOLVED = "Unresolved."
R2_YES = "Yes: interval entirely above +5."
R2_NO = "No: interval entirely inside [−5, +5]."
R2_UNRESOLVED = "Unresolved."
R3_STAYS = "Title stays: invocation is the bottleneck."
R3_CHANGES = "Title changes to the two-gate reading (invocation and delivery)."
R4_ATTRIBUTED = ("The canonical open-weight delivery gap on solve is attributed to "
                 "storage and the refused final request.")
R4_NOT = "R4 condition not met"                                   # §8b item 8
R5_WORK = "The system-prompt sentence was doing work."
R5_INERT = "The system-prompt sentence is inert for this model."
R5_SUPPRESS = "The directive suppresses calling."
R5_NONE = "No registered row applies"                              # §8b item 9
R5_STEER_SUFFICIENT = "Steering in the user turn is sufficient by itself."
# Not registered (neither §5 nor §8b names the complement of the steering sentence).
R5_STEER_NOT = "Not shown (neutral-steered not within ±5 of minimal-steered)."
E2_CAVEAT = ("No-tools side: Part C of this run (same harness commit, vLLM 0.20.2, full "
             "storage, the same delivered grader as the tool side). The no-tools arm is "
             "sampled under the per-task JSON constraint; the tool arm has none (§4 E2).")

# §3 "with the apparatus deltas of §2 stated": the four deltas, verbatim in substance.
APPARATUS_DELTAS = (
    "1. Storage: final answers stored up to 65,536 characters (canonical: 500); "
    "rows cut by storage: 0 (asserted).",
    "2. Final-request overflow retry: a request refused for exceeding the 16,384-token "
    "window is resent with the allowance that fits; the first request of every turn is "
    "unchanged.",
    "3. A leading empty thought-channel marker is removed from the text the grader reads.",
    "4. Serving version: vLLM 0.20.2; Qwen3.5-9B canonical tool cells ran on 0.22.0.",
)

CELLS = [(m, t, a) for m in C.PART_A_MODELS for t in C.TASKS for a in C.ARMS]


def _bd(b: Boot | None) -> dict | None:
    return None if b is None else asdict(b)


# ------------------------------------------------------------------ parity (§3)
@dataclass
class ParityCell:
    model: str
    task: str
    arm: str
    n_rerun: int
    n_canonical: int
    n_paired: int
    unpaired_rerun: int
    unpaired_canonical: int
    unpaired_frac: float
    tv_rerun_pct: float          # on paired rows
    tv_canonical_pct: float      # on paired rows
    delta: float                 # paired Δ̂, points
    ci90: Boot | None            # None when VOID (cluster set incomplete)
    verdict: str
    newcombe90: tuple[float, float, float]   # secondary, unpaired, all rows
    gross: bool                  # |Δ̂| > 10
    clipped_before_tool_call: int  # rerun rows (§3 "known reason a cell may move")
    consequence: str = ""


def _by_key(rows: list[Row]) -> dict[tuple, Row]:
    out: dict[tuple, Row] = {}
    for r in rows:
        if r.trial_key in out:
            raise SchemaError(f"duplicate trial key {r.trial_key}")
        out[r.trial_key] = r
    return out


def parity_cell(rerun: list[Row], canon: list[Row], model: str, task: str,
                arm: str, k: int) -> ParityCell:
    rr = _by_key([r for r in rerun if r.task == task and r.arm == arm])
    cc = _by_key([r for r in canon if r.task == task and r.arm == arm])
    both = sorted(set(rr) & set(cc))
    if not both:
        raise SchemaError(f"parity {model}/{task}/{arm}: no paired rows")
    ur, uc = len(set(rr) - set(cc)), len(set(cc) - set(rr))
    frac = (ur + uc) / len(set(rr) | set(cc))
    d = [int(rr[x].success) - int(cc[x].success) for x in both]
    delta = 100 * sum(d) / len(d)
    void = frac > C.UNPAIRED_VOID_FRAC
    ci = None if void else cluster_bootstrap(d, [x[1] for x in both], C.CI_PARITY, k)
    verdict = VOID if void else (MET if tost_met(ci) else NOT_MET)
    k1 = sum(r.success for r in rr.values())
    k2 = sum(r.success for r in cc.values())
    return ParityCell(
        model=model, task=task, arm=arm, n_rerun=len(rr), n_canonical=len(cc),
        n_paired=len(both), unpaired_rerun=ur, unpaired_canonical=uc,
        unpaired_frac=frac,
        tv_rerun_pct=100 * sum(rr[x].success for x in both) / len(both),
        tv_canonical_pct=100 * sum(cc[x].success for x in both) / len(both),
        delta=delta, ci90=ci, verdict=verdict,
        newcombe90=newcombe(k1, len(rr), k2, len(cc)),
        gross=abs(delta) > C.GROSS,
        clipped_before_tool_call=sum(r.clipped_before_tool_call for r in rr.values()))


@dataclass
class Parity:
    cells: list[ParityCell]
    gemma_evaluated_first: bool
    gemma_failed: bool
    noise_floor_F: float | None
    qwen_met: int
    gross_cells: list[str]
    job: str
    void_cells: list[str] = field(default_factory=list)


def parity(rerun_a: dict[str, LoadedCell], canon_tools: dict[str, LoadedCell],
           k: int) -> Parity:
    order = [C.CONTROL_MODEL] + [m for m in C.PART_A_MODELS if m != C.CONTROL_MODEL]
    assert order[0] == C.CONTROL_MODEL and set(order) == set(C.PART_A_MODELS)
    cells: list[ParityCell] = []
    gemma_failed = None
    floor = None
    for m in order:
        for t in C.TASKS:
            for a in C.ARMS:
                cells.append(parity_cell(list(rerun_a[m].rows), list(canon_tools[m].rows),
                                         m, t, a, k))
        if m == C.CONTROL_MODEL:
            # §3: Gemma's 10 cells are evaluated before any Qwen cell.
            g = [c for c in cells if c.model == C.CONTROL_MODEL]
            assert len(g) == 10
            gemma_failed = any(c.verdict != MET for c in g)
            floor = max(abs(c.delta) for c in g) if gemma_failed else None
    assert len(cells) == C.PARITY_CELLS
    q = [c for c in cells if c.model in C.QWEN_MODELS]
    assert len(q) == C.QWEN_CELLS_TOTAL
    qwen_met = sum(c.verdict == MET for c in q)
    gross = [f"{c.model}/{c.task}/{c.arm}" for c in cells if c.gross]
    holds = qwen_met >= C.QWEN_CELLS_REQUIRED and not gross
    for c in cells:
        if not holds:
            c.consequence = CONSEQ_JOB_FAIL
        elif c.verdict == MET:
            c.consequence = CONSEQ_EXACT
        else:
            c.consequence = CONSEQ_CELL_FAIL
    return Parity(cells=cells, gemma_evaluated_first=True, gemma_failed=bool(gemma_failed),
                  noise_floor_F=floor, qwen_met=qwen_met, gross_cells=gross,
                  job=JOB_HOLDS if holds else JOB_FAILS,
                  void_cells=[f"{c.model}/{c.task}/{c.arm}" for c in cells
                              if c.verdict == VOID])


# ------------------------------------------------------------------ E1 (§4)
Grades = dict[tuple[str, tuple], Delivered]     # (cell name, trial_key) -> grade


def dlv(grades: Grades, r: Row) -> bool:
    g = grades[(r.cell, r.trial_key)]
    return g.ok


@dataclass
class RateCell:
    model: str
    task: str
    arm: str
    style: str
    n: int
    delivered_k: int
    delivered_pct: float
    ci95: Boot
    tool_verified_pct: float
    invocation_pct: float
    no_room_n: int
    no_room_pct: float
    prefix_n: int
    reasons: dict


def rate_cell(rows: list[Row], grades: Grades, model: str, task: str, arm: str,
              style: str, k: int) -> RateCell:
    rs = [r for r in rows if r.task == task and r.arm == arm]
    if not rs:
        raise SchemaError(f"E1 {model}/{task}/{arm}: no rows")
    ok = [int(dlv(grades, r)) for r in rs]
    n = len(rs)
    return RateCell(
        model=model, task=task, arm=arm, style=style, n=n, delivered_k=sum(ok),
        delivered_pct=100 * sum(ok) / n,
        ci95=cluster_bootstrap(ok, [r.domain for r in rs], C.CI_ENDPOINT, k),
        tool_verified_pct=100 * sum(r.success for r in rs) / n,
        invocation_pct=100 * sum(r.invoked for r in rs) / n,
        no_room_n=sum(r.no_room for r in rs),
        no_room_pct=100 * sum(r.no_room for r in rs) / n,
        prefix_n=sum(grades[(r.cell, r.trial_key)].prefix_stripped for r in rs),
        reasons=dict(sorted(Counter(grades[(r.cell, r.trial_key)].reason
                                    for r in rs).items())))


# ------------------------------------------------------------------ E2 / E3 (§4)
@dataclass
class Contrast:
    model: str
    task: str
    name: str
    n_pairs: int
    unpaired_a: int
    unpaired_b: int
    a_pct: float | None
    b_pct: float | None
    delta: float | None
    ci95: Boot | None
    p: float
    p_holm: float = 1.0


def _contrast(name: str, model: str, task: str, pairs: list[tuple[int, int, str]],
              ua: int, ub: int, k: int) -> Contrast:
    if not pairs:
        raise SchemaError(f"{name} {model}/{task}: no pairs")
    d = [b - a for a, b, _ in pairs]
    doms = [dom for _, _, dom in pairs]
    ci = cluster_bootstrap(d, doms, C.CI_ENDPOINT, k)
    n = len(pairs)
    return Contrast(model=model, task=task, name=name, n_pairs=n, unpaired_a=ua,
                    unpaired_b=ub, a_pct=100 * sum(a for a, _, _ in pairs) / n,
                    b_pct=100 * sum(b for _, b, _ in pairs) / n,
                    delta=100 * sum(d) / n, ci95=ci,
                    p=signflip_exact_p(domain_sums(d, doms)))


def e2(rerun_a: dict[str, LoadedCell], rerun_c: dict[str, LoadedCell],
       grades: Grades, k: int) -> list[Contrast]:
    """Tools-plain (Part A) − no-tools (Part C), both this run, per model × task,
    paired on (domain, problem, variant, plan label); both sides graded by the
    same delivered grader (§2 Part C, §8b item 12)."""
    out: list[Contrast] = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            tl = _by_key([r for r in rerun_a[m].rows if r.task == t and r.arm == "plain"])
            nt = _by_key([r for r in rerun_c[m].rows if r.task == t])
            assert all(r.variant in C.PLAIN and not r.with_tools and r.layer == "rerun"
                       for r in nt.values())
            both = sorted(set(tl) & set(nt))
            ua, ub = len(set(nt) - set(tl)), len(set(tl) - set(nt))
            pairs = [(int(dlv(grades, nt[x])), int(dlv(grades, tl[x])), x[1]) for x in both]
            out.append(_contrast("E2", m, t, pairs, ua, ub, k))
    _apply_holm(out)
    return out


def part_c_parity(rerun_c: dict[str, LoadedCell], canon_nt: dict[str, LoadedCell],
                  k: int) -> list[ParityCell]:
    """§2 Part C parity (reported, not a gate on E2): Part C − canonical on the
    stored online `success`, paired, the §3 code path (TOST ±5 on the 90%
    domain-cluster interval, unpaired/VOID rule). Simulate excluded."""
    cells = [parity_cell(list(rerun_c[m].rows), list(canon_nt[m].rows), m, t, "plain", k)
             for m in C.PART_A_MODELS for t in C.PART_C_PARITY_TASKS]
    assert len(cells) == 12
    return cells


def e3(rerun_a: dict[str, LoadedCell], grades: Grades, k: int) -> list[Contrast]:
    """Tools-steered − tools-plain (both this run): v ↔ v+3 on the same fixture."""
    out: list[Contrast] = []
    for m in C.PART_A_MODELS:
        rows = rerun_a[m].rows
        for t in C.TASKS:
            plain = _by_key([r for r in rows if r.task == t and r.arm == "plain"])
            steer = _by_key([r for r in rows if r.task == t and r.arm == "steered"])
            pairs, ua = [], 0
            matched = set()
            for x, rp in plain.items():
                y = (x[0], x[1], x[2], x[3], x[4] + C.STEER_OFFSET)
                if y in steer:
                    pairs.append((int(dlv(grades, rp)), int(dlv(grades, steer[y])), x[1]))
                    matched.add(y)
                else:
                    ua += 1
            out.append(_contrast("E3", m, t, pairs, ua, len(set(steer) - matched), k))
    _apply_holm(out)
    return out


def _apply_holm(cs: list[Contrast]) -> None:
    """Holm over the registered family of 15 (§4; p from §8b item 1)."""
    adj = holm({(c.model, c.task): c.p for c in cs}, C.HOLM_FAMILY)
    for c in cs:
        c.p_holm = adj[(c.model, c.task)]


# ------------------------------------------------------------------ E4 (§4)
@dataclass
class GapCell:
    model: str
    task: str
    arm: str
    n_tool_correct: int
    n_gap: int
    gap_pct: float | None
    categories: dict
    subs: dict


def e4_cell(rows: list[Row], grades: Grades, gt_cache: dict, model: str, task: str,
            arm: str) -> GapCell:
    rs = [r for r in rows if r.task == task and r.arm == arm and r.success is True]
    gap = [r for r in rs if grades[(r.cell, r.trial_key)].ok is False]
    cats: Counter = Counter()
    subs: Counter = Counter()
    for r in gap:
        cat, sub = E4.classify(r, grades[(r.cell, r.trial_key)], gt_cache)
        assert cat in E4.CATS
        cats[cat] += 1
        subs[f"{cat}: {sub}"] += 1
    return GapCell(model=model, task=task, arm=arm, n_tool_correct=len(rs),
                   n_gap=len(gap), gap_pct=(100 * len(gap) / len(rs)) if rs else None,
                   categories={c: cats[c] for c in E4.CATS},
                   subs=dict(sorted(subs.items())))


# ------------------------------------------------------------------ readings (§5)
def _find(cs: list[Contrast], model: str, task: str) -> Contrast:
    hit = [c for c in cs if c.model == model and c.task == task]
    assert len(hit) == 1
    return hit[0]


def r1(e2s: list[Contrast]) -> dict:
    c = _find(e2s, C.CONTROL_MODEL, "validate_plan")
    lo, hi = c.ci95.lo, c.ci95.hi
    if hi < -C.MARGIN:
        label = R1_HARM
    elif lo >= -C.MARGIN and hi <= C.MARGIN:
        label = R1_NO_HARM
    else:
        label = R1_UNRESOLVED
    return {"label": label, "delta": c.delta, "ci95": [lo, hi]}


def r2(e3s: list[Contrast]) -> dict:
    c = _find(e3s, C.CONTROL_MODEL, "validate_plan")
    lo, hi = c.ci95.lo, c.ci95.hi
    if lo > C.MARGIN:
        label = R2_YES
    elif lo >= -C.MARGIN and hi <= C.MARGIN:
        label = R2_NO
    else:
        label = R2_UNRESOLVED
    return {"label": label, "delta": c.delta, "ci95": [lo, hi]}


def r3(r1_label: str, e3s: list[Contrast]) -> dict:
    gains = [m for m in C.PART_A_MODELS
             if _find(e3s, m, "validate_plan").ci95.lo > C.MARGIN]
    stays = r1_label == R1_HARM or len(gains) >= C.R3_MODELS_REQUIRED
    return {"label": R3_STAYS if stays else R3_CHANGES,
            "r1_harm": r1_label == R1_HARM, "models_with_e3_gain_above_5": gains}


def r4(rerun_a: dict[str, LoadedCell], grades: Grades) -> dict:
    """Solve, per model (both arms pooled): among tool-verified trials whose
    final answer is full and uncut, the share delivered correctly."""
    per = {}
    for m in C.PART_A_MODELS:
        rs = [r for r in rerun_a[m].rows if r.task == "solve" and r.success is True
              and r.done_reason != "length" and not r.no_room
              and r.response_truncated_by_storage is False]
        k = sum(dlv(grades, r) for r in rs)
        per[m] = {"n": len(rs), "delivered_k": k,
                  "delivered_pct": (100 * k / len(rs)) if rs else None}
    ok = all(v["delivered_pct"] is not None and v["delivered_pct"] >= C.R4_THRESHOLD
             for v in per.values())
    return {"label": R4_ATTRIBUTED if ok else R4_NOT, "per_model": per}


def r5(minimal: list[Row], neutral: list[Row], grades: Grades, k: int) -> dict:
    """§5 R5 on Gemma validate_plan: the 2 × 2 and the two invocation contrasts."""
    mini = [r for r in minimal if r.task == C.PART_B_TASK]
    cells = {}
    for style, rows in (("minimal", mini), ("neutral", neutral)):
        for arm in C.ARMS:
            rs = [r for r in rows if r.arm == arm]
            inv = [int(r.invoked) for r in rs]
            ok = [int(dlv(grades, r)) for r in rs]
            dom = [r.domain for r in rs]
            cells[f"{style}-{arm}"] = {
                "n": len(rs),
                "invocation_pct": 100 * sum(inv) / len(rs),
                "invocation_ci95": _bd(cluster_bootstrap(inv, dom, C.CI_ENDPOINT, k)),
                "delivered_pct": 100 * sum(ok) / len(rs),
                "delivered_ci95": _bd(cluster_bootstrap(ok, dom, C.CI_ENDPOINT, k)),
            }

    def contrast(arm: str) -> Boot:
        a = _by_key([r for r in mini if r.arm == arm])
        b = _by_key([r for r in neutral if r.arm == arm])
        both = sorted(set(a) & set(b))
        if len(both) != len(a) or len(both) != len(b):
            raise SchemaError(f"R5 {arm}: Part A and Part B keys differ")
        d = [int(b[x].invoked) - int(a[x].invoked) for x in both]
        return cluster_bootstrap(d, [x[1] for x in both], C.CI_PARITY, k)

    plain = contrast("plain")
    if plain.est < -C.MARGIN:
        label = R5_WORK
    elif tost_met(plain):
        label = R5_INERT
    elif plain.est > C.MARGIN:
        label = R5_SUPPRESS
    else:
        label = R5_NONE
    steer = contrast("steered")
    return {"label": label, "neutral_minus_minimal_plain": _bd(plain),
            "steering_label": R5_STEER_SUFFICIENT if tost_met(steer) else R5_STEER_NOT,
            "neutral_minus_minimal_steered": _bd(steer), "cells": cells}
