#!/usr/bin/env python3
"""Shared core for the two frozen nt-ster H4 analysis entry points.

`ntster_f_gate.py` and `ntster_h4.py` are the pre-registered entry points
(`development/ntster_h4_prereg.md` §7 step 3). This module holds what they both
need — loading, dedup, the completeness gate, the paired estimator, and the
interval machinery — so the two scripts cannot drift apart in how they read a
cell or compute a CI.

FREEZING. All three files are hashed together and the hashes are recorded in the
prereg before the sync ping. Deliberately **self-contained**: nothing here
imports from `.claude/skills/analyzer/`, because a frozen analysis that imports a
live module is not frozen — an edit there would silently change a pre-registered
result. Standard library plus numpy/scipy only.

Surfaces (§3.1). Primary is **delivered** = the overlay's `e2e` field. For
no-tools rows outside `simulate` the overlay passes the stored online grade
through unchanged, so delivered and legacy coincide on ~93.4% of rows and the
legacy column is a real second measurement only on `simulate`.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from scipy import stats

# --------------------------------------------------------------------------
# Pre-registered constants. None of these are CLI-tunable on purpose: every one
# of them is a design commitment, and a flag would let a later run quietly pick
# a different one.
# --------------------------------------------------------------------------

TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]

NEUTRAL_VARIANTS = (11, 12, 13)     # anchor arm  (nt-neut)
STEERED_VARIANTS = (14, 15, 16)     # control arm (nt-ster)
PAIR_OFFSET = 3                     # v11↔v14, v12↔v15, v13↔v16

MARGIN_PP = 5.0                     # §1 equivalence margin, ±5pp
ALPHA = 0.10                        # 90% intervals throughout
BOOTSTRAP_B = 10_000                # §3.3 domain-clustered bootstrap

EXPECTED_CELL_ROWS = 9_120          # §2.1 both arms in one cell file
EXPECTED_PER_VARIANT = 1_520
EXPECTED_PER_TASK_VARIANT = {
    "solve": 100,
    "validate_domain": 120,
    "validate_problem": 200,
    "validate_plan": 1_000,
    "simulate": 100,
}
EXPECTED_SNAPSHOT_CAP = 16_384      # §2.3(C); a cell reporting 500 is not analysable

# Eligibility thresholds (§3.3 point 3).
ANCHOR_BAND = (10.0, 90.0)          # ELIGIBLE requires the anchor rate inside this
LOW_BASE_RATE_BELOW = 10.0
HALF_WIDTH_CEILING_PP = 5.0

# Mechanism guards (§3.7).
APPARATUS_VOID_SHARE = 0.01         # >1% APPARATUS in either arm voids the read
CEILING_GUARD_TRUNCATION = 0.75     # anchor truncation ≥75% ⇒ mechanism-UNINFORMATIVE
MECHANISM_MIN_ABS_DELTA_PP = 9.0    # a label needs |Δ̂| ≥ 9pp
AT_CAP_RESPONSE_LEN = 16_384

# Trial-key layout, as written by `pddl_eval.runner._trial_key`:
#   [model, task, domain, problem, plan_label, variant, with_tools,
#    think, tool_filter, prompt_style]
K_MODEL, K_TASK, K_DOMAIN, K_PROBLEM, K_PLAN, K_VARIANT = 0, 1, 2, 3, 4, 5
K_WITH_TOOLS, K_THINK, K_TOOL_FILTER, K_STYLE = 6, 7, 8, 9

# §3.7 partition of `failure_reason`. Names are normalised (lowercase, `FR_`
# stripped) before lookup.
TRUNCATED_LOSS_REASONS = {"truncated_no_answer", "think_overflow"}
CHANNEL_FORMAT_REASONS = {"format_parse_fail"}
CONTENT_REASONS = {"verdict_mismatch", "plan_invalid", "result_mismatch",
                   "simulate_empty", "trajectory_mismatch"}
APPARATUS_REASONS = {"exception", "tool_error", "unknown"}

# §3.7 M1 directive echo. validate_*/simulate directives name a tool; `solve`'s
# names none, so it gets its own pattern.
M1_TOOL_NAME_PATTERN = (r"(classic_planner|numeric_planner|validate_domain|"
                        r"validate_problem|validate_plan|get_state_transition)")
M1_SOLVE_PATTERN = r"(planner tool|the planner\b)"

# §3.7 help-direction leakage ranking, pre-registered so the contrast is not
# chosen after the fact. Higher rank = more expected leakage.
LEAKAGE_RANK = {"validate_plan": 5, "simulate": 4, "validate_problem": 3,
                "validate_domain": 2, "solve": 1}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

@dataclass
class Cell:
    """One (model, think) overlay corpus, deduped and arm-split."""
    name: str
    model: str
    think: str
    rows: dict[tuple, dict]                 # trial key -> graded row
    duplicates_dropped: int = 0
    snapshot_caps: set[int] = field(default_factory=set)

    @property
    def n(self) -> int:
        return len(self.rows)


def _row_key(row: dict) -> tuple | None:
    tk = row.get("trial_key")
    if tk is not None:
        return tuple(tk)
    # Overlay files written before `trial_key` landed. The prereg forbids
    # requiring the field, so fall back to the identifying tuple.
    needed = ("model", "task", "domain_name", "problem_name", "plan_label",
              "prompt_variant", "with_tools")
    if any(k not in row for k in needed):
        return None
    return (row["model"], row["task"], row["domain_name"], row["problem_name"],
            row["plan_label"], row["prompt_variant"], row["with_tools"])


def load_overlay_cells(overlay_dir: Path) -> list[Cell]:
    """Load every `*.e2e.jsonl` under `overlay_dir`, deduped by trial key.

    Dedup policy is **last wins**, matching `e2e_regrade.py:530-536` and
    `pddl_eval.resume`. A resumed cell legitimately re-emits keys; the later row
    is the one the run finished with.
    """
    if not overlay_dir.is_dir():
        raise SystemExit(f"overlay dir not found: {overlay_dir}\n"
                         "Run tools/e2e_regrade.py first (§7 step 4).")
    files = sorted(overlay_dir.glob("*.e2e.jsonl"))
    if not files:
        raise SystemExit(f"no *.e2e.jsonl under {overlay_dir}")

    cells: list[Cell] = []
    for fp in files:
        rows: dict[tuple, dict] = {}
        dups = 0
        caps: set[int] = set()
        model, think = "", ""
        with fp.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = _row_key(row)
                if key is None:
                    continue
                if key in rows:
                    dups += 1
                rows[key] = row
                if row.get("snapshot_cap") is not None:
                    caps.add(int(row["snapshot_cap"]))
                model = model or row.get("model", "")
                think = think or str(row.get("think", "") or "")
        if not rows:
            continue
        if not think:
            think = _think_from_name(fp.name)
        cells.append(Cell(name=fp.name.replace(".e2e.jsonl", ""), model=model,
                          think=think, rows=rows, duplicates_dropped=dups,
                          snapshot_caps=caps))
    return cells


def _think_from_name(name: str) -> str:
    for tag in ("_on_", "_off_"):
        if tag in name:
            return tag.strip("_")
    return ""


def delivered(row: dict) -> bool:
    """§3.1 primary surface. `e2e` is the overlay's delivered grade."""
    return bool(row.get("e2e"))


def legacy(row: dict) -> bool:
    """Stored online grade — the consistency column, a real second measurement
    only on `simulate` (§3.1)."""
    return bool(row.get("success"))


def is_censored(row: dict) -> bool:
    return row.get("e2e_reason") == "censored_at_snapshot_cap"


# --------------------------------------------------------------------------
# Completeness gate (§3.1)
# --------------------------------------------------------------------------

@dataclass
class GateReport:
    ok: bool
    lines: list[str]
    per_variant: dict[int, int]
    per_task_variant: dict[tuple[str, int], int]
    reweighting_needed: bool


def completeness_gate(cell: Cell, *, arms: Sequence[int] | None = None) -> GateReport:
    """Enforce the enumerated grid before any contrast is read.

    `infra_failure` rows are never written to `trials.jsonl` by design, so an
    on-disk shortfall means keys that must be re-run, NOT failures. An incomplete
    cell is INCONCLUSIVE and is explicitly **not** analysed on the surviving
    subset. `runner.py:708-709` silently drops a validate_plan/simulate fixture
    whose planner ground truth is missing, so the harness does not enforce this
    shape — hence the explicit gate.
    """
    arms = tuple(arms) if arms is not None else tuple(NEUTRAL_VARIANTS + STEERED_VARIANTS)
    lines: list[str] = []
    ok = True

    per_variant: dict[int, int] = defaultdict(int)
    per_task_variant: dict[tuple[str, int], int] = defaultdict(int)
    for key, row in cell.rows.items():
        v = key[K_VARIANT]
        if v not in arms:
            continue
        per_variant[v] += 1
        per_task_variant[(key[K_TASK], v)] += 1

    expected_rows = EXPECTED_PER_VARIANT * len(arms)
    total = sum(per_variant.values())
    if total != expected_rows:
        ok = False
        lines.append(f"row count {total:,} != expected {expected_rows:,} "
                     f"over variants {list(arms)}")

    imbalance = False
    for v in arms:
        got = per_variant.get(v, 0)
        if got != EXPECTED_PER_VARIANT:
            ok = False
            imbalance = True
            lines.append(f"variant v{v}: {got:,} rows != {EXPECTED_PER_VARIANT:,}")

    for task, expect in EXPECTED_PER_TASK_VARIANT.items():
        for v in arms:
            got = per_task_variant.get((task, v), 0)
            if got != expect:
                ok = False
                imbalance = True
                lines.append(f"({task}, v{v}): {got:,} rows != {expect:,}")

    if cell.snapshot_caps and cell.snapshot_caps != {EXPECTED_SNAPSHOT_CAP}:
        ok = False
        lines.append(
            f"snapshot_cap {sorted(cell.snapshot_caps)} != [{EXPECTED_SNAPSHOT_CAP}] — "
            "detect_cap returns 500 for any cell whose max response length is ≤500, "
            "so this cell's censor branches are not trustworthy (§3.1)")

    if cell.duplicates_dropped:
        lines.append(f"note: {cell.duplicates_dropped:,} duplicate trial key(s) "
                     "deduped (last wins) — expected on a resumed cell")

    if ok:
        lines.append(f"complete: {total:,} rows, {EXPECTED_PER_VARIANT:,}/variant, "
                     "per-(task, variant) shape exact")
    return GateReport(ok=ok, lines=lines, per_variant=dict(per_variant),
                      per_task_variant=dict(per_task_variant),
                      reweighting_needed=imbalance)


# --------------------------------------------------------------------------
# Pairing (§3.3 point 1)
# --------------------------------------------------------------------------

@dataclass
class Pair:
    task: str
    domain: str
    problem: str
    plan_label: str
    paraphrase: int          # 0,1,2 → (v11,v14), (v12,v15), (v13,v16)
    a: bool                  # arm A outcome (anchor / lower variant)
    b: bool                  # arm B outcome (steered / upper variant)

    @property
    def d(self) -> float:
        return float(self.b) - float(self.a)


def build_pairs(cell: Cell, *, lo: Sequence[int], hi: Sequence[int],
                surface: Callable[[dict], bool] = delivered,
                task: str | None = None) -> list[Pair]:
    """Fixture-matched join: the trial key with the variant slot stripped.

    v11/v12/v13 cover byte-identical `(task, domain, problem, plan_label)` sets
    and v14-16 are those same prompts plus one appended sentence, so the join is
    exact rather than approximate. Unmatched fixtures are dropped and counted by
    the caller via the length difference — with a passing completeness gate there
    are none.
    """
    if len(lo) != len(hi):
        raise ValueError("lo and hi must be the same length")
    index: dict[tuple, dict] = {}
    for key, row in cell.rows.items():
        if task is not None and key[K_TASK] != task:
            continue
        index[(key[K_TASK], key[K_DOMAIN], key[K_PROBLEM], key[K_PLAN],
               key[K_VARIANT])] = row

    pairs: list[Pair] = []
    for j, (vlo, vhi) in enumerate(zip(lo, hi)):
        for (t, dom, prob, plan, v), row in index.items():
            if v != vlo:
                continue
            other = index.get((t, dom, prob, plan, vhi))
            if other is None:
                continue
            pairs.append(Pair(task=t, domain=dom, problem=prob, plan_label=plan,
                              paraphrase=j, a=surface(row), b=surface(other)))
    return pairs


# --------------------------------------------------------------------------
# Interval machinery (§3.3)
# --------------------------------------------------------------------------

@dataclass
class Interval:
    estimate_pp: float
    lo_pp: float
    hi_pp: float
    half_width_pp: float
    k: int
    method: str

    def inside_margin(self, margin: float = MARGIN_PP) -> bool:
        return self.lo_pp > -margin and self.hi_pp < margin

    def outside_margin(self, margin: float = MARGIN_PP) -> bool:
        return self.lo_pp > margin or self.hi_pp < -margin


def _cluster_means(pairs: Sequence[Pair],
                   key: Callable[[Pair], object]) -> tuple[np.ndarray, list]:
    buckets: dict[object, list[float]] = defaultdict(list)
    for p in pairs:
        buckets[key(p)].append(p.d)
    labels = sorted(buckets, key=repr)
    return np.array([float(np.mean(buckets[c])) for c in labels]), labels


def paired_cluster_ci(pairs: Sequence[Pair], key: Callable[[Pair], object],
                      *, method: str, alpha: float = ALPHA) -> Interval:
    """90% t interval on the per-cluster mean of the per-fixture paired difference.

    The estimate is the unweighted mean of cluster means. Under this design the
    clusters are balanced, so it coincides with the row-level pooled difference;
    `pooled_rate_pp` is reported alongside so any imbalance is visible rather
    than absorbed.
    """
    if not pairs:
        return Interval(math.nan, math.nan, math.nan, math.nan, 0, method)
    means, labels = _cluster_means(pairs, key)
    k = len(means)
    est = float(means.mean()) * 100.0
    if k < 2:
        return Interval(est, math.nan, math.nan, math.nan, k, method)
    se = float(means.std(ddof=1)) / math.sqrt(k) * 100.0
    tcrit = float(stats.t.ppf(1.0 - alpha / 2.0, k - 1))
    hw = tcrit * se
    return Interval(est, est - hw, est + hw, hw, k, method)


def paired_cluster_bootstrap(pairs: Sequence[Pair], key: Callable[[Pair], object],
                             *, b: int = BOOTSTRAP_B, alpha: float = ALPHA,
                             seed: int = 20260817) -> Interval:
    """Cluster bootstrap: resample whole clusters with replacement.

    Seeded so the frozen script is reproducible; the seed is part of the frozen
    artifact, not a tuning knob.
    """
    if not pairs:
        return Interval(math.nan, math.nan, math.nan, math.nan, 0, "bootstrap")
    means, _ = _cluster_means(pairs, key)
    k = len(means)
    if k < 2:
        return Interval(float(means.mean()) * 100.0, math.nan, math.nan, math.nan,
                        k, "bootstrap")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, k, size=(b, k))
    boot = means[draws].mean(axis=1) * 100.0
    lo, hi = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
    est = float(means.mean()) * 100.0
    return Interval(est, float(lo), float(hi), float(hi - lo) / 2.0, k, "bootstrap")


def _wilson(x: int, n: int, alpha: float) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    z = float(stats.norm.ppf(1.0 - alpha / 2.0))
    p = x / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def newcombe_unpaired(x1: int, n1: int, x2: int, n2: int,
                      alpha: float = ALPHA) -> Interval:
    """Newcombe hybrid-score interval for p2 − p1 (the conservative companion).

    Deliberately ignores the pairing, which is why it is wider and why the
    prereg keeps it as a companion rather than the primary.
    """
    if n1 == 0 or n2 == 0:
        return Interval(math.nan, math.nan, math.nan, math.nan, 0, "newcombe")
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = _wilson(x1, n1, alpha)
    l2, u2 = _wilson(x2, n2, alpha)
    est = (p2 - p1) * 100.0
    lo = (p2 - p1 - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)) * 100.0
    hi = (p2 - p1 + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)) * 100.0
    return Interval(est, lo, hi, (hi - lo) / 2.0, n1 + n2, "newcombe")


def wider(a: Interval, b: Interval) -> Interval:
    """§3.3: the script reports both clusterings and **the wider one governs**."""
    if math.isnan(a.half_width_pp):
        return b
    if math.isnan(b.half_width_pp):
        return a
    return a if a.half_width_pp >= b.half_width_pp else b


def noninferiority_p(interval: Interval, margin: float = MARGIN_PP) -> float:
    """One-sided p for the affirmative claim |Δ| > margin, for Holm (§3.4).

    Only ever applied to the ELIGIBLE family, and only to the affirmative
    non-equivalence direction — the conjunctive equivalence claim is
    intersection-union and takes no correction.
    """
    if math.isnan(interval.half_width_pp) or interval.k < 2:
        return math.nan
    tcrit = float(stats.t.ppf(1.0 - ALPHA / 2.0, interval.k - 1))
    if tcrit == 0:
        return math.nan
    se = interval.half_width_pp / tcrit
    if se <= 0:
        return 0.0 if abs(interval.estimate_pp) > margin else 1.0
    t = (abs(interval.estimate_pp) - margin) / se
    return float(stats.t.sf(t, interval.k - 1))


def holm(pvalues: dict[str, float], alpha: float = ALPHA) -> dict[str, bool]:
    """Holm step-down over the ELIGIBLE family. Returns name -> rejected."""
    live = {k: v for k, v in pvalues.items() if not math.isnan(v)}
    out = {k: False for k in pvalues}
    m = len(live)
    for i, (name, p) in enumerate(sorted(live.items(), key=lambda kv: kv[1])):
        if p <= alpha / (m - i):
            out[name] = True
        else:
            break
    return out


# --------------------------------------------------------------------------
# Rates
# --------------------------------------------------------------------------

def arm_rate(cell: Cell, variants: Sequence[int], *, task: str | None = None,
             surface: Callable[[dict], bool] = delivered) -> tuple[int, int]:
    """(successes, n) for one arm at pooled or per-task granularity."""
    x = n = 0
    for key, row in cell.rows.items():
        if key[K_VARIANT] not in variants:
            continue
        if task is not None and key[K_TASK] != task:
            continue
        n += 1
        x += int(surface(row))
    return x, n


def pct(x: int, n: int) -> float:
    return 100.0 * x / n if n else math.nan


# --------------------------------------------------------------------------
# Freeze support
# --------------------------------------------------------------------------

def frozen_hashes() -> dict[str, str]:
    """sha256 of the three frozen files, for the prereg record."""
    import hashlib
    here = Path(__file__).resolve().parent
    out = {}
    for name in ("ntster_common.py", "ntster_f_gate.py", "ntster_h4.py"):
        fp = here / name
        if fp.exists():
            out[name] = hashlib.sha256(fp.read_bytes()).hexdigest()
    return out
