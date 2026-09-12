#!/usr/bin/env python3
"""Frontier output-budget probe — frozen analysis entry point.

Prereg: development/frontier_budget_probe_prereg.md (§3 analysis plan; §8 gates).
This file is the ONLY place the probe's verdict is computed. It reads

  * the reference with-tools simulate cell (overlay + raw trials) and classifies
    every reference row into one of the §3.1 classes from the reference corpus
    alone (never from probe data);
  * the probe corpus (overlay + raw trials + run_manifest.json), joined on the
    trial key;

and prints the §3.2 primary contrast (one-sided Fisher exact, LEN-FIT vs
ET-FAIL conversion), the §3.3 secondaries, and the §3.6 tripwires. It refuses
to run when a §2.4 constant does not hold: every registered apparatus setting
is asserted against the probe directory's run_manifest.json (written by
tools/frontier_runner.py before its first API call) and the typed loader
crashes on an unknown enum or a missing field (freeze gates 1 and 2). Nothing
here grades a response — grading is tools/e2e_regrade.py.

Usage
  python3 tools/budget_probe_analysis.py classify --tier sonnet
      # reference-only: prints the §3.1 class table (used to pin the counts)
  python3 tools/budget_probe_analysis.py readout --tier sonnet \
      --probe results/sonnet-frontier/sweep5v2-with-tools-budget64k \
      --out results/derived/budget_probe
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / ".claude/skills/analyzer/scripts"))

from pddl_eval.scoring import _normalize_trajectory  # noqa: E402
from tools._run_manifest import MANIFEST_NAME, read_manifest  # noqa: E402
from _constants import wilson_ci  # noqa: E402

# ---------------------------------------------------------------------------
# Registered constants (prereg §2.2 / §2.4 / §3.1). Freeze gate 2: asserts.
# ---------------------------------------------------------------------------
BUDGET_TOKENS = 64_000                # §2.2 (amended 2026-09-10 from 65,536)
HAIKU_MAX_OUTPUT_TOKENS = 64_000      # claude-haiku-4-5 output ceiling; the
                                      # budget must fit BOTH tiers (§2.2)
assert BUDGET_TOKENS <= HAIKU_MAX_OUTPUT_TOKENS
SNAPSHOT_CAP = 262_144
REFERENCE_BUDGET = 6_144
REFERENCE_CAP = 16_384
N_PER_LEG = 100
PROMPT_VARIANT = 11
TASK = "simulate"
CORPUS = "canonical"                  # §2.4: domains/ (never domains-anon/)
LOOP_LIMIT = 10                       # §2.4: MAX_TOOL_LOOPS, held at the reference value
STREAM_REQUIRED = True                # §2.3: streaming is the registered apparatus
FIT_TOKENS_PER_CANON_CHAR = 0.82      # 1.8 chars-per-canon-char / 2.2 chars-per-token
FIT_HEADROOM = 0.9
DECLINE_RATIO = 0.25
DECLINE_MIN_CANON = 8_000
ALPHA = 0.05
H1_MIN_CONVERSION = 0.60
KILL_MAX_CONVERSION = 0.30
CONTROL_TRIP = 0.50
NONBINDING_LEN_FRACTION = 0.9         # §3.6(a): response_len < 0.9 × snapshot

TIERS = {
    "sonnet": dict(corpus="sonnet-frontier", model="claude-sonnet-4-6",
                   ref_cell="sweep5v2-with-tools"),
    "haiku": dict(corpus="haiku-frontier", model="claude-haiku-4-5",
                  ref_cell="sweep5v2-with-tools"),
}
# §3.1 reference class counts, pinned 2026-09-08 by `classify` and RE-DERIVED
# 2026-09-10 under the 64,000 budget (fits ⇔ canon ≤ 70,243 chars; no oracle
# lies between that and the old 71,929 cutoff, so the counts are unchanged —
# checked, not assumed). A re-derivation that disagrees must fail loudly
# (freeze gate 2), never silently re-bin.
PINNED_CLASS_COUNTS = {
    "sonnet": {"OK": 49, "LEN-FIT": 25, "LEN-NOFIT": 4, "OVERFLOW": 0, "SNAP": 0,
               "DECLINE": 3, "ET-FAIL": 19, "OTHER": 0},
    "haiku": {"OK": 52, "LEN-FIT": 17, "LEN-NOFIT": 1, "OVERFLOW": 1, "SNAP": 2,
              "DECLINE": 14, "ET-FAIL": 12, "OTHER": 1},
}
GT_CACHE_SHA256 = "77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e"
OK_RERUN_TRIPS = {"sonnet": 40, "haiku": 42}

CLASSES = ("OK", "LEN-FIT", "LEN-NOFIT", "OVERFLOW", "SNAP", "DECLINE",
           "ET-FAIL", "OTHER")
E2E_VALUES = (True, False, "indeterminate")
DONE_REASONS = ("end_turn", "length", "tool_use", "stop", "error", "refusal",
                "max_tokens", "stop_sequence", "pause_turn")


@dataclass(frozen=True)
class Row:
    """Typed join of one overlay row with its raw trial (freeze gate 1)."""
    key: tuple
    domain: str
    problem: str
    e2e_strict: object          # True / False / "indeterminate"
    e2e_reason: str
    done_reason: str
    response_len: int
    snapshot_cap: int
    tool_verified: object
    completion_tokens: int      # aggregate over every turn (cost)
    completion_final_tokens: int | None   # the last turn alone (truncation);
                                          # None only on legacy reference rows
    turns: int
    error: str
    canon_chars: int


def _load_overlay(path: Path) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for ln in path.read_text().splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r["task"] != TASK:
            continue
        key = tuple(r["trial_key"])
        if key in out:
            raise ValueError(f"duplicate overlay key {key} in {path}")
        out[key] = r
    return out


def _load_raw(path: Path) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for ln in path.read_text().splitlines():
        if not ln.strip():
            continue
        obj = json.loads(ln)          # a torn line is a crash here, on purpose
        r = obj["result"]
        if r["task"] != TASK:
            continue
        key = tuple(obj["key"])
        if key in out:
            raise ValueError(f"duplicate raw key {key} in {path}")
        out[key] = r
    return out


def canon_size(gt: dict, domain: str, problem: str) -> int:
    trace = gt[domain][problem]["trace"]
    steps = json.loads(trace)
    if isinstance(steps, dict):
        steps = steps.get("trajectory")
    canon = _normalize_trajectory(steps)
    if canon is None:
        raise ValueError(f"oracle trajectory for {domain}/{problem} does not normalize")
    return len(json.dumps(canon))


def load_cell(corpus_dir: Path, overlay_path: Path, gt: dict, *, model: str,
              expect_cap: int, final_tokens_required: bool) -> dict[tuple, Row]:
    """Typed load of one cell. `final_tokens_required=True` (the probe) makes a
    raw row without `tokens.completion_final` a crash; the reference corpora
    predate the field (2026-07-12) and load it as None, never read."""
    ov = _load_overlay(overlay_path)
    raw = _load_raw(corpus_dir / "trials.jsonl")
    if set(ov) != set(raw):
        raise ValueError(f"overlay/raw key mismatch: {len(ov)} vs {len(raw)} "
                         f"({len(set(ov) ^ set(raw))} differ)")
    rows: dict[tuple, Row] = {}
    for key, o in ov.items():
        r = raw[key]
        e2e = o["e2e_strict"]
        if e2e not in E2E_VALUES:
            raise ValueError(f"unknown e2e_strict {e2e!r} at {key}")
        dr = o["done_reason"]
        if dr not in DONE_REASONS:
            raise ValueError(f"unknown done_reason {dr!r} at {key}")
        if o["snapshot_cap"] != expect_cap:
            raise ValueError(f"snapshot_cap {o['snapshot_cap']} != {expect_cap} at {key}")
        if o["model"] != model or o["prompt_variant"] != PROMPT_VARIANT:
            raise ValueError(f"wrong model/variant at {key}")
        toks = r["tokens"]
        if final_tokens_required:
            if "completion_final" not in toks:
                raise ValueError(f"raw row lacks tokens.completion_final at {key} "
                                 "(written by a pre-2026-09-10 runner?)")
            final = int(toks["completion_final"])
        else:
            final = int(toks["completion_final"]) if "completion_final" in toks else None
        rows[key] = Row(
            key=key, domain=o["domain_name"], problem=o["problem_name"],
            e2e_strict=e2e, e2e_reason=o["e2e_reason"], done_reason=dr,
            response_len=int(o["response_len"]), snapshot_cap=int(o["snapshot_cap"]),
            tool_verified=o["tool_verified"],
            completion_tokens=int(toks["completion"]),
            completion_final_tokens=final,
            turns=int(toks["turns"]), error=str(r.get("error") or ""),
            canon_chars=canon_size(gt, o["domain_name"], o["problem_name"]),
        )
    return rows


# ---------------------------------------------------------------------------
# §2.4 apparatus validation — every registered setting against the manifest.
# ---------------------------------------------------------------------------
def expected_probe_manifest(tier: str) -> dict:
    """The manifest fields the prereg registers for a with-tools probe leg.
    Every key here is compared for exact equality with the probe directory's
    run_manifest.json; anything else in the manifest is provenance only."""
    return {
        "backend": "anthropic-tool-runner",
        "model": TIERS[tier]["model"],
        "with_tools": True,
        "conditions": "tools",
        "tasks": [TASK],
        "corpus": CORPUS,
        "domains_dir": "domains",
        "prompt_variants": [PROMPT_VARIANT],
        "num_predict": BUDGET_TOKENS,
        "snapshot_len": SNAPSHOT_CAP,
        "max_iterations": LOOP_LIMIT,
        "stream": STREAM_REQUIRED,
        "temperature": 0,
        "think": "off",
        "ground_truth": "cached",
        "gt_cache_sha256": GT_CACHE_SHA256,
        "keys_files": None,
        "limit": None,
    }


def validate_probe_manifest(probe_dir: Path, tier: str,
                            expected: dict | None = None) -> dict:
    """Raise ValueError naming every registered setting the probe directory's
    manifest violates; return the manifest when all hold."""
    manifest = read_manifest(probe_dir)
    if manifest is None:
        raise ValueError(f"probe corpus {probe_dir} has no {MANIFEST_NAME}: its "
                         "settings are not verifiable (prereg §2.4)")
    expected = expected_probe_manifest(tier) if expected is None else expected
    bad = [f"{k}: manifest={manifest.get(k, '<absent>')!r} registered={v!r}"
           for k, v in expected.items() if manifest.get(k, "<absent>") != v]
    if bad:
        raise ValueError("probe manifest violates registered settings:\n  "
                         + "\n  ".join(bad))
    return manifest


# ---------------------------------------------------------------------------
# §3.1 classification — from the reference row ONLY.
# ---------------------------------------------------------------------------
def fits(canon_chars: int, budget: int = BUDGET_TOKENS) -> bool:
    return FIT_TOKENS_PER_CANON_CHAR * canon_chars <= FIT_HEADROOM * budget


def classify(row: Row) -> str:
    if row.e2e_strict is True:
        return "OK"
    if "prompt is too long" in row.error:
        return "OVERFLOW"
    if row.done_reason == "length":
        return "LEN-FIT" if fits(row.canon_chars) else "LEN-NOFIT"
    if row.done_reason == "end_turn":
        if row.e2e_strict == "indeterminate":
            return "SNAP"            # finished on its own; storage censored it
        if (row.canon_chars > DECLINE_MIN_CANON
                and row.response_len < DECLINE_RATIO * row.canon_chars):
            return "DECLINE"
        return "ET-FAIL"
    return "OTHER"


def class_table(rows: dict[tuple, Row]) -> dict[str, int]:
    t = {c: 0 for c in CLASSES}
    for r in rows.values():
        t[classify(r)] += 1
    assert sum(t.values()) == len(rows)
    return t


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """P(X >= a) for the 2x2 [[a, b], [c, d]] under the hypergeometric null
    (row 1 = LEN-FIT converted/not, row 2 = ET-FAIL converted/not)."""
    n1, n2, k = a + b, c + d, a + c
    lo, hi = max(0, k - n2), min(k, n1)
    def pmf(x: int) -> float:
        return (math.comb(n1, x) * math.comb(n2, k - x)) / math.comb(n1 + n2, k)
    return sum(pmf(x) for x in range(a, hi + 1))


def conversion(ref: dict[tuple, Row], probe: dict[tuple, Row], cls: str) -> tuple[int, int]:
    keys = [k for k, r in ref.items() if classify(r) == cls]
    conv = sum(1 for k in keys if probe[k].e2e_strict is True)
    return conv, len(keys)


def nonbinding_truncations(ref: dict[tuple, Row], probe: dict[tuple, Row]) -> list[tuple]:
    """§3.6(a), second clause, implemented literally: a LEN-FIT reference row
    whose probe row has done_reason == "length", a response shorter than
    0.9 × the snapshot cap, and a FINAL-TURN output-token count ≠ the budget.
    The budget did not bind on the turn that stopped, yet the row truncated:
    apparatus bug. The aggregate `completion_tokens` is NOT consulted — a
    multi-turn trial can exceed the budget in total without any single turn
    having been cut."""
    out = []
    for k, r in probe.items():
        if classify(ref[k]) != "LEN-FIT" or r.done_reason != "length":
            continue
        if r.response_len < NONBINDING_LEN_FRACTION * SNAPSHOT_CAP \
                and r.completion_final_tokens != BUDGET_TOKENS:
            out.append(k)
    return out


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def _paths(tier: str, probe_dir: Path | None):
    cfg = TIERS[tier]
    ref_dir = REPO / "results" / cfg["corpus"] / cfg["ref_cell"]
    ref_ov = REPO / "results/derived/e2e_overlay" / cfg["corpus"] / f"{cfg['ref_cell']}.e2e.jsonl"
    probe_ov = None
    if probe_dir is not None:
        probe_ov = REPO / "results/derived/e2e_overlay" / probe_dir.parent.name / f"{probe_dir.name}.e2e.jsonl"
    return cfg, ref_dir, ref_ov, probe_ov


def cmd_classify(args) -> int:
    cfg, ref_dir, ref_ov, _ = _paths(args.tier, None)
    gt = json.loads((REPO / args.gt_cache).read_text())
    ref = load_cell(ref_dir, ref_ov, gt, model=cfg["model"], expect_cap=REFERENCE_CAP,
                    final_tokens_required=False)
    assert len(ref) == N_PER_LEG, len(ref)
    t = class_table(ref)
    print(f"[{args.tier}] reference cell {ref_dir.relative_to(REPO)} n={len(ref)} "
          f"budget={BUDGET_TOKENS} (fits <=> canon <= "
          f"{int(FIT_HEADROOM * BUDGET_TOKENS / FIT_TOKENS_PER_CANON_CHAR)} chars)")
    for c in CLASSES:
        print(f"  {c:10s} {t[c]:3d}")
    if args.verbose:
        for k, r in sorted(ref.items(), key=lambda kv: kv[1].canon_chars):
            print(f"    {classify(r):10s} {r.domain:20s} {r.problem} canon={r.canon_chars:7d} "
                  f"{r.done_reason:9s} {str(r.e2e_strict):14s} {r.e2e_reason} resp={r.response_len}")
    print("gt_cache sha256:", hashlib.sha256((REPO / args.gt_cache).read_bytes()).hexdigest())
    return 0


def run_readout(*, tier: str, ref_dir: Path, ref_overlay: Path, probe_dir: Path,
                probe_overlay: Path, gt: dict, pinned: dict[str, int] | None = None,
                ok_rerun_trip: int | None = None, n_per_leg: int = N_PER_LEG,
                expected_manifest: dict | None = None) -> dict:
    """The whole §3 readout as a pure function (freeze gate 4 drives it with a
    synthetic fixture). Every prereg §2.4 setting is asserted — against the
    probe directory's run_manifest.json and its summary meta — before any
    statistic is computed."""
    cfg = TIERS[tier]
    pinned = PINNED_CLASS_COUNTS[tier] if pinned is None else pinned
    ok_rerun_trip = OK_RERUN_TRIPS[tier] if ok_rerun_trip is None else ok_rerun_trip
    # §2.4 apparatus: manifest first (nothing else is read if it fails).
    manifest = validate_probe_manifest(probe_dir, tier, expected_manifest)
    meta_files = sorted(probe_dir.glob("summary_*.json"))
    assert meta_files, "probe corpus has no summary_*.json (run meta missing)"
    meta = json.loads(meta_files[-1].read_text()).get("meta", {})
    assert meta.get("num_predict") == BUDGET_TOKENS, meta
    assert meta.get("snapshot_len") == SNAPSHOT_CAP, meta
    assert meta.get("num_predict") == manifest["num_predict"], (meta, manifest)
    assert meta.get("snapshot_len") == manifest["snapshot_len"], (meta, manifest)

    ref = load_cell(ref_dir, ref_overlay, gt, model=cfg["model"], expect_cap=REFERENCE_CAP,
                    final_tokens_required=False)
    probe = load_cell(probe_dir, probe_overlay, gt, model=cfg["model"], expect_cap=SNAPSHOT_CAP,
                      final_tokens_required=True)
    # §2.4 asserts
    assert len(ref) == n_per_leg and len(probe) == n_per_leg, (len(ref), len(probe))
    assert set(ref) == set(probe), "probe keys != reference keys (join must be 100/100)"
    t = class_table(ref)
    assert t == pinned, f"class counts drifted: {t} != {pinned}"

    out: dict = {"tier": tier, "classes": t, "tripwires": [],
                 "manifest": {k: manifest.get(k) for k in expected_probe_manifest(tier)}}
    # §3.6(a) censoring / non-binding truncation
    cens = [k for k, r in probe.items() if r.e2e_strict == "indeterminate"]
    if cens:
        out["tripwires"].append(f"(a) {len(cens)} probe rows censored at {SNAPSHOT_CAP}")
    odd = nonbinding_truncations(ref, probe)
    if odd:
        out["tripwires"].append(
            f"(a) {len(odd)} LEN-FIT rows truncated with final-turn output != {BUDGET_TOKENS}")
    # §3.2 primary
    a, n1 = conversion(ref, probe, "LEN-FIT")
    c, n2 = conversion(ref, probe, "ET-FAIL")
    p = fisher_one_sided(a, n1 - a, c, n2 - c)
    r1, r2 = a / n1 if n1 else float("nan"), c / n2 if n2 else float("nan")
    verdict = ("H1" if (p < ALPHA and r1 >= H1_MIN_CONVERSION)
               else "KILL" if r1 <= KILL_MAX_CONVERSION else "PARTIAL")
    out["primary"] = dict(len_fit=(a, n1), et_fail=(c, n2), fisher_p=p,
                          rate_len_fit=r1, rate_et_fail=r2,
                          ci_len_fit=wilson_ci(a, n1), ci_et_fail=wilson_ci(c, n2),
                          verdict=verdict)
    # §3.6(b)/(c)
    ok_keys = [k for k, r in ref.items() if classify(r) == "OK"]
    ok_rerun = sum(1 for k in ok_keys if probe[k].e2e_strict is True)
    if r2 > CONTROL_TRIP:
        out["tripwires"].append(f"(b) control conversion {r2:.2f} > {CONTROL_TRIP}")
    if ok_rerun < ok_rerun_trip:
        out["tripwires"].append(f"(b) OK re-run {ok_rerun}/{len(ok_keys)} < {ok_rerun_trip}")
    d, nd = conversion(ref, probe, "DECLINE")
    if nd and d / nd > CONTROL_TRIP:
        out["tripwires"].append(f"(c) DECLINE conversion {d}/{nd} > {CONTROL_TRIP}")
    # §3.3 secondaries
    ok = sum(1 for r in probe.values() if r.e2e_strict is True)
    out["secondary"] = dict(
        cell_delivered=(ok, len(probe)), cell_ci=wilson_ci(ok, len(probe)),
        ok_rerun=(ok_rerun, len(ok_keys)), decline=(d, nd),
        len_nofit=conversion(ref, probe, "LEN-NOFIT"),
        overflow=conversion(ref, probe, "OVERFLOW"), snap=conversion(ref, probe, "SNAP"),
        probe_reasons=_count(r.e2e_reason for r in probe.values()),
        ref_reasons=_count(r.e2e_reason for r in ref.values()),
        # aggregate output tokens = the cost figure (§3.3 item 6 / ledger)
        completion_tokens_median=_median([r.completion_tokens for r in probe.values()]),
        completion_tokens_max=max(r.completion_tokens for r in probe.values()),
        # final-turn output tokens = the budget-binding figure (§3.6(a))
        completion_final_median=_median([r.completion_final_tokens for r in probe.values()]),
        completion_final_max=max(r.completion_final_tokens for r in probe.values()),
        completion_final_at_budget=sum(
            1 for r in probe.values() if r.completion_final_tokens == BUDGET_TOKENS),
    )
    return out


def cmd_readout(args) -> int:
    cfg, ref_dir, ref_ov, probe_ov = _paths(args.tier, Path(args.probe))
    gt_path = REPO / args.gt_cache
    sha = hashlib.sha256(gt_path.read_bytes()).hexdigest()
    assert sha == GT_CACHE_SHA256, f"gt_cache sha256 drifted: {sha}"
    gt = json.loads(gt_path.read_text())
    out = run_readout(tier=args.tier, ref_dir=ref_dir, ref_overlay=ref_ov,
                      probe_dir=Path(args.probe), probe_overlay=probe_ov, gt=gt)
    out_dir = REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"readout_{args.tier}.json").write_text(json.dumps(out, indent=1, default=str))
    if out["tripwires"]:
        print("TRIPWIRE(S) — halt and trace before writing any sentence:")
        for tw in out["tripwires"]:
            print("  ", tw)
    print(json.dumps(out["primary"], indent=1, default=str))
    print(json.dumps(out["secondary"], indent=1, default=str))
    return 0


def _count(it):
    d: dict[str, int] = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


def _median(xs: list[int]) -> float:
    s = sorted(xs)
    n = len(s)
    return (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2) if n else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gt-cache", default="results/derived/gt_cache.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify"); c.add_argument("--tier", choices=TIERS, required=True)
    c.add_argument("--verbose", action="store_true"); c.set_defaults(fn=cmd_classify)
    r = sub.add_parser("readout"); r.add_argument("--tier", choices=TIERS, required=True)
    r.add_argument("--probe", required=True); r.add_argument("--out", default="results/derived/budget_probe")
    r.set_defaults(fn=cmd_readout)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
