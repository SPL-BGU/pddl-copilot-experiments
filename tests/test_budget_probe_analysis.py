"""Synthetic-fixture test for tools/budget_probe_analysis.py — freeze-protocol
v2 gate 4 for development/frontier_budget_probe_prereg.md.

Run standalone: `python3 tests/test_budget_probe_analysis.py`
Or via the shell wrapper: `bash tests/verify.sh`

The fixture is a 30-row mini-corpus (reference + probe) with planted traps
and hand-computed answers. Every expected number below was computed by hand
from the prereg's rules (§3.1 classes, §3.2 one-sided Fisher exact, §3.6
tripwires) BEFORE the pipeline ran on it; the pipeline must reproduce them
exactly and must refuse the malformed variants.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "analyzer" / "scripts"))

from tests._helpers import TestResults  # noqa: E402
import tools.budget_probe_analysis as bpa  # noqa: E402

MODEL = "claude-sonnet-4-6"
KEY_TAIL = ["", 11, True, "off", "all", "minimal"]


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------
def _trace(n_preds: int, n_steps: int = 3) -> str:
    """Oracle trace whose canonical JSON size scales with n_preds."""
    steps = []
    for i in range(n_steps):
        steps.append({"step": i, "action": None if i == 0 else f"(move x{i})",
                      "boolean_fluents": {f"(p{j:04d} a b)": True for j in range(n_preds)},
                      "numeric_fluents": {}})
    return json.dumps(steps)


# (cls, domain, problem, n_preds, ref(e2e, done, resp_len, err), probe(e2e, done, out_tok))
# canon sizes sit around the fit boundary: fits(64000) <=> canon <= 70,243 chars.
SMALL, BIG = 20, 5000          # canon ≈ 1.4K chars  vs  ≈ 330K chars (no fit)
SPEC = [
    ("OK",       "d", "p01", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p02", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p03", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p04", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p05", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p06", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p07", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p08", SMALL, (True, "end_turn", 2000, ""),       (True, "end_turn", 3000)),
    ("OK",       "d", "p09", SMALL, (True, "end_turn", 2000, ""),       (False, "end_turn", 3000)),
    ("OK",       "d", "p10", SMALL, (True, "length", 16384, ""),        (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p01", SMALL, (False, "length", 12000, ""),       (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p02", SMALL, (False, "length", 12000, ""),       (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p03", SMALL, ("indeterminate", "length", 16384, ""), (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p04", SMALL, ("indeterminate", "length", 16384, ""), (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p05", SMALL, (False, "length", 12000, ""),       (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p06", SMALL, (False, "length", 12000, ""),       (True, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p07", SMALL, (False, "length", 12000, ""),       (False, "end_turn", 9000)),
    ("LEN-FIT",  "e", "p08", SMALL, (False, "length", 12000, ""),       (False, "end_turn", 9000)),
    ("LEN-NOFIT", "f", "p01", BIG,  (False, "length", 12000, ""),       (False, "length", 64000)),
    ("LEN-NOFIT", "f", "p02", BIG,  ("indeterminate", "length", 16384, ""), (False, "length", 64000)),
    ("OVERFLOW", "g", "p01", BIG,   (False, "length", 0, "prompt is too long: 498K"), (False, "length", 0)),
    ("SNAP",     "h", "p01", SMALL, ("indeterminate", "end_turn", 16384, ""), (True, "end_turn", 7000)),
    ("DECLINE",  "i", "p01", 900,   (False, "end_turn", 1500, ""),      (True, "end_turn", 30000)),
    ("DECLINE",  "i", "p02", 900,   (False, "end_turn", 1500, ""),      (True, "end_turn", 30000)),
    ("DECLINE",  "i", "p03", 900,   (False, "end_turn", 1500, ""),      (True, "end_turn", 30000)),
    ("DECLINE",  "i", "p04", 900,   (False, "end_turn", 1500, ""),      (False, "end_turn", 1500)),
    ("ET-FAIL",  "j", "p01", SMALL, (False, "end_turn", 5000, ""),      (True, "end_turn", 5000)),
    ("ET-FAIL",  "j", "p02", SMALL, (False, "end_turn", 5000, ""),      (False, "end_turn", 5000)),
    ("ET-FAIL",  "j", "p03", SMALL, (False, "end_turn", 5000, ""),      (False, "end_turn", 5000)),
    ("ET-FAIL",  "j", "p04", SMALL, (False, "end_turn", 5000, ""),      (False, "end_turn", 5000)),
]
EXPECTED_CLASSES = {"OK": 10, "LEN-FIT": 8, "LEN-NOFIT": 2, "OVERFLOW": 1, "SNAP": 1,
                    "DECLINE": 4, "ET-FAIL": 4, "OTHER": 0}
# Hand-computed §3.2: LEN-FIT converted 6/8, ET-FAIL converted 1/4.
#   one-sided Fisher on [[6,2],[1,3]]: n1=8, n2=4, k=7
#   P(X>=6) = [C(8,6)C(4,1) + C(8,7)C(4,0)] / C(12,7) = (28*4 + 8*1)/792 = 120/792
EXPECTED_FISHER_P = 120 / 792
# 0.75 > 0.30 and p = 0.1515 >= 0.05  ->  PARTIAL
EXPECTED_VERDICT = "PARTIAL"
# OK re-run 9/10 (p09 flipped). DECLINE conversion 3/4 = 0.75 > 0.5 -> tripwire (c).
# Probe has no censored rows and no LEN-FIT length rows -> no (a); control 0.25 -> no (b).


def _gt(spec) -> dict:
    gt: dict = {}
    for _, dom, prob, preds, _, _ in spec:
        gt.setdefault(dom, {})[prob] = {"trace": _trace(preds)}
    return gt


def _write_corpus(root: Path, name: str, spec, *, probe: bool, cap: int,
                  meta: dict | None = None, manifest: dict | None = None,
                  mutate=None) -> tuple[Path, Path]:
    cell_dir = root / "results" / "sonnet-frontier" / name
    ov_dir = root / "results" / "derived" / "e2e_overlay" / "sonnet-frontier"
    cell_dir.mkdir(parents=True, exist_ok=True)
    ov_dir.mkdir(parents=True, exist_ok=True)
    raw_lines, ov_lines = [], []
    for cls, dom, prob, preds, ref, prb in spec:
        e2e, done, resp_len, err = ref
        out_tok = 6000
        tokens = {"prompt": 10, "completion": out_tok, "turns": 2}
        if probe:
            e2e, done, out_tok = prb
            resp_len = min(out_tok * 2, cap) if e2e is not False else 1500
            err = ""
            # Probe rows carry the final-turn count (the runner writes it);
            # by default the final turn is the whole output.
            tokens = {"prompt": 10, "completion": out_tok, "completion_final": out_tok,
                      "turns": 2}
        key = [MODEL, "simulate", dom, prob] + KEY_TAIL
        raw = {"key": key, "result": {"task": "simulate", "domain_name": dom,
                                       "problem_name": prob, "model": MODEL,
                                       "prompt_variant": 11, "with_tools": True,
                                       "done_reason": done, "error": err,
                                       "tokens": tokens}}
        ov = {"task": "simulate", "model": MODEL, "domain_name": dom, "problem_name": prob,
              "plan_label": "", "prompt_variant": 11, "with_tools": True,
              "tool_verified": True, "done_reason": done, "response_len": resp_len,
              "e2e_strict": e2e, "e2e": e2e,
              "e2e_reason": ("trajectory_ok" if e2e is True else
                             "censored_at_snapshot_cap" if e2e == "indeterminate"
                             else "format_parse_fail"),
              "snapshot_cap": cap, "trial_key": key}
        if mutate:
            raw, ov = mutate(cls, dom, prob, raw, ov)
            if raw is None:
                continue
        raw_lines.append(json.dumps(raw))
        ov_lines.append(json.dumps(ov))
    (cell_dir / "trials.jsonl").write_text("\n".join(raw_lines) + "\n")
    (ov_dir / f"{name}.e2e.jsonl").write_text("\n".join(ov_lines) + "\n")
    if meta is not None:
        (cell_dir / "summary_20260101_000000.json").write_text(json.dumps({"meta": meta}))
    if manifest is not None:
        (cell_dir / "run_manifest.json").write_text(json.dumps(manifest))
    return cell_dir, ov_dir / f"{name}.e2e.jsonl"


GOOD_META = {"num_predict": 64000, "snapshot_len": 262144}
# The run manifest the runner writes before its first API call; every field
# below is one the prereg registers (§2.4) and the readout asserts.
GOOD_MANIFEST = {
    "manifest_version": 1, "created_at": "2026-01-01T00:00:00+0000",
    "backend": "anthropic-tool-runner", "sdk_version": "0.109.2",
    "model": MODEL, "with_tools": True, "conditions": "tools", "tasks": ["simulate"],
    "corpus": "canonical", "domains_dir": "domains", "prompt_variants": [11],
    "num_predict": 64000, "snapshot_len": 262144, "max_iterations": 10, "stream": True,
    "temperature": 0, "think": "off", "ground_truth": "cached",
    "ground_truth_sha256": "0" * 64, "gt_cache_sha256": bpa.GT_CACHE_SHA256,
    "gt_cache_path": "results/derived/gt_cache.json", "keys_files": None, "limit": None,
}


def _run(spec, *, probe_meta=GOOD_META, probe_manifest=GOOD_MANIFEST, ref_mutate=None,
         probe_mutate=None, pinned=EXPECTED_CLASSES):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ref_dir, ref_ov = _write_corpus(root, "sweep5v2-with-tools", spec, probe=False,
                                        cap=16384, mutate=ref_mutate)
        pr_dir, pr_ov = _write_corpus(root, "sweep5v2-with-tools-budget64k", spec,
                                      probe=True, cap=262144, meta=probe_meta,
                                      manifest=probe_manifest, mutate=probe_mutate)
        return bpa.run_readout(tier="sonnet", ref_dir=ref_dir, ref_overlay=ref_ov,
                               probe_dir=pr_dir, probe_overlay=pr_ov, gt=_gt(spec),
                               pinned=pinned, ok_rerun_trip=8, n_per_leg=len(spec))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_fisher_known_values(r: TestResults) -> None:
    # Fisher's tea tasting [[3,1],[1,3]]: one-sided P(X>=3) = 17/70
    r.check("tea tasting 17/70", abs(bpa.fisher_one_sided(3, 1, 1, 3) - 17 / 70) < 1e-12,
            str(bpa.fisher_one_sided(3, 1, 1, 3)))
    r.check_eq("zero converted -> p = 1", bpa.fisher_one_sided(0, 5, 0, 5), 1.0)
    r.check("fixture 2x2 = 120/792", abs(bpa.fisher_one_sided(6, 2, 1, 3) - 120 / 792) < 1e-12,
            str(bpa.fisher_one_sided(6, 2, 1, 3)))


def test_fit_rule_boundary(r: TestResults) -> None:
    # 0.82 * canon <= 0.9 * 64000 = 57600  <=>  canon <= 70243.9
    r.check("70243 fits", bpa.fits(70243), "fit boundary low side")
    r.check("70244 does not fit", not bpa.fits(70244), "fit boundary high side")
    # The old 65,536 budget put the boundary at 71,929; no reference oracle
    # lies in (70243, 71929], which is why the pinned counts survived the
    # 2026-09-10 amendment — pin the boundary so a future budget edit reruns
    # `classify` instead of assuming the same.
    r.check("budget is 64,000", bpa.BUDGET_TOKENS == 64000, str(bpa.BUDGET_TOKENS))
    r.check("budget fits Haiku's ceiling", bpa.BUDGET_TOKENS <= bpa.HAIKU_MAX_OUTPUT_TOKENS, "")
    # 16384 budget: 0.82 * canon <= 14745.6 <=> canon <= 17,982 chars
    r.check("16384 budget: 17,982-char oracle fits", bpa.fits(17982, 16384), "")
    r.check("16384 budget: 17,983-char oracle does not fit", not bpa.fits(17983, 16384), "")


def test_fixture_classes_and_primary(r: TestResults) -> None:
    out = _run(SPEC)
    r.check_eq("class table", out["classes"], EXPECTED_CLASSES)
    pr = out["primary"]
    r.check_eq("LEN-FIT conversion", pr["len_fit"], (6, 8))
    r.check_eq("ET-FAIL conversion", pr["et_fail"], (1, 4))
    r.check("fisher p", abs(pr["fisher_p"] - EXPECTED_FISHER_P) < 1e-12, str(pr["fisher_p"]))
    r.check_eq("verdict", pr["verdict"], EXPECTED_VERDICT)
    sec = out["secondary"]
    r.check_eq("OK re-run 9/10", sec["ok_rerun"], (9, 10))
    r.check_eq("DECLINE 3/4", sec["decline"], (3, 4))
    r.check_eq("LEN-NOFIT 0/2", sec["len_nofit"], (0, 2))
    r.check_eq("OVERFLOW 0/1", sec["overflow"], (0, 1))
    r.check_eq("SNAP 1/1", sec["snap"], (1, 1))
    # OK 9 (p09 flipped; p10 stays ok) + LEN-FIT 6 + SNAP 1 + DECLINE 3 + ET-FAIL 1 = 20
    r.check_eq("cell delivered", sec["cell_delivered"], (20, 30))
    r.check_eq("one tripwire (c) only", [tw[:3] for tw in out["tripwires"]], ["(c)"])


def test_h1_and_kill_verdicts(r: TestResults) -> None:
    # H1: LEN-FIT 8/8, ET-FAIL 0/4 -> p = 1/C(12,8) = 1/495 < 0.05, rate 1.0
    spec = [(c, d, p, n, ref, ((True, "end_turn", 9000) if c == "LEN-FIT" else
                               (False, "end_turn", 5000) if c == "ET-FAIL" else prb))
            for c, d, p, n, ref, prb in SPEC]
    out = _run(spec)
    r.check_eq("H1 verdict", out["primary"]["verdict"], "H1")
    r.check("H1 p = 1/495", abs(out["primary"]["fisher_p"] - 1 / 495) < 1e-12,
            str(out["primary"]["fisher_p"]))
    # KILL: LEN-FIT 2/8 (0.25 <= 0.30)
    spec = [(c, d, p, n, ref, ((True if p in ("p01", "p02") else False, "end_turn", 9000)
                               if c == "LEN-FIT" else prb))
            for c, d, p, n, ref, prb in SPEC]
    out = _run(spec)
    r.check_eq("KILL verdict", out["primary"]["verdict"], "KILL")


def test_tripwire_a_censored_probe_row(r: TestResults) -> None:
    def mut(cls, dom, prob, raw, ov):
        if (dom, prob) == ("e", "p01"):
            ov = dict(ov, e2e_strict="indeterminate", e2e="indeterminate",
                      e2e_reason="censored_at_snapshot_cap", response_len=262144)
        return raw, ov
    out = _run(SPEC, probe_mutate=mut)
    r.check("tripwire (a) fires", any(tw.startswith("(a) 1 probe rows censored")
                                     for tw in out["tripwires"]), str(out["tripwires"]))


def test_refuses_duplicate_key(r: TestResults) -> None:
    def mut(cls, dom, prob, raw, ov):
        if (dom, prob) == ("j", "p04"):
            raw = dict(raw, key=[MODEL, "simulate", "j", "p03"] + KEY_TAIL)
        return raw, ov
    try:
        _run(SPEC, probe_mutate=mut)
        r.check("duplicate raw key refused", False, "no exception")
    except ValueError as exc:
        r.check("duplicate raw key refused", "duplicate raw key" in str(exc), str(exc))


def test_refuses_missing_snapshot_cap_and_unknown_grade(r: TestResults) -> None:
    def mut_cap(cls, dom, prob, raw, ov):
        if (dom, prob) == ("d", "p01"):
            ov = {k: v for k, v in ov.items() if k != "snapshot_cap"}
        return raw, ov
    try:
        _run(SPEC, ref_mutate=mut_cap)
        r.check("missing snapshot_cap refused", False, "no exception")
    except KeyError:
        r.check("missing snapshot_cap refused", True, "")

    def mut_grade(cls, dom, prob, raw, ov):
        if (dom, prob) == ("d", "p02"):
            ov = dict(ov, e2e_strict="maybe")
        return raw, ov
    try:
        _run(SPEC, ref_mutate=mut_grade)
        r.check("unknown e2e_strict refused", False, "no exception")
    except ValueError as exc:
        r.check("unknown e2e_strict refused", "unknown e2e_strict" in str(exc), str(exc))


def test_refuses_wrong_meta_and_drifted_counts(r: TestResults) -> None:
    try:
        _run(SPEC, probe_meta={"num_predict": 16384, "snapshot_len": 262144})
        r.check("wrong num_predict refused", False, "no exception")
    except AssertionError:
        r.check("wrong num_predict refused", True, "")
    try:
        _run(SPEC, pinned=dict(EXPECTED_CLASSES, **{"LEN-FIT": 7, "ET-FAIL": 5}))
        r.check("drifted pinned counts refused", False, "no exception")
    except AssertionError as exc:
        r.check("drifted pinned counts refused", "drifted" in str(exc), str(exc))


def test_refuses_key_mismatch(r: TestResults) -> None:
    def mut(cls, dom, prob, raw, ov):
        if (dom, prob) == ("j", "p04"):
            return None, None       # drop one probe row -> 29 vs 30
        return raw, ov
    try:
        _run(SPEC, probe_mutate=mut)
        r.check("29/30 join refused", False, "no exception")
    except AssertionError:
        r.check("29/30 join refused", True, "")


def test_refuses_manifest_violations(r: TestResults) -> None:
    """§2.4: every registered setting is asserted against run_manifest.json."""
    cases = {
        "missing manifest": None,
        "wrong corpus (anon)": dict(GOOD_MANIFEST, corpus="anon", domains_dir="domains-anon"),
        "wrong loop limit": dict(GOOD_MANIFEST, max_iterations=5),
        "wrong gt_cache hash": dict(GOOD_MANIFEST, gt_cache_sha256="f" * 64),
        "generated (not cached) ground truth": dict(GOOD_MANIFEST, ground_truth="generated",
                                                    gt_cache_sha256=None),
        "not streaming": dict(GOOD_MANIFEST, stream=False),
        "wrong budget": dict(GOOD_MANIFEST, num_predict=65536),
        "wrong snapshot": dict(GOOD_MANIFEST, snapshot_len=16384),
        "wrong variant set": dict(GOOD_MANIFEST, prompt_variants=[11, 12]),
        "wrong model": dict(GOOD_MANIFEST, model="claude-haiku-4-5"),
        "keys-file subset": dict(GOOD_MANIFEST, keys_files=["k.jsonl"]),
        "limit set": dict(GOOD_MANIFEST, limit=20),
    }
    for label, manifest in cases.items():
        try:
            _run(SPEC, probe_manifest=manifest)
            r.check(f"refused: {label}", False, "no exception")
        except ValueError as exc:
            r.check(f"refused: {label}", "manifest" in str(exc), str(exc))
    # And the good manifest passes, surfacing the checked fields in the readout.
    out = _run(SPEC)
    r.check_eq("manifest echoed in readout", out["manifest"]["num_predict"], 64000)


def test_refuses_probe_row_without_final_tokens(r: TestResults) -> None:
    def mut(cls, dom, prob, raw, ov):
        if (dom, prob) == ("e", "p01"):
            toks = {k: v for k, v in raw["result"]["tokens"].items() if k != "completion_final"}
            raw = dict(raw, result=dict(raw["result"], tokens=toks))
        return raw, ov
    try:
        _run(SPEC, probe_mutate=mut)
        r.check("missing completion_final refused", False, "no exception")
    except ValueError as exc:
        r.check("missing completion_final refused", "completion_final" in str(exc), str(exc))


def _len_fit_length_row(final: int, aggregate: int, resp_len: int = 20000):
    """Mutator: e/p01 (LEN-FIT) re-truncates in the probe with the given
    final-turn / aggregate output tokens and response length."""
    def mut(cls, dom, prob, raw, ov):
        if (dom, prob) == ("e", "p01"):
            raw = dict(raw, result=dict(raw["result"], done_reason="length",
                                        tokens={"prompt": 10, "completion": aggregate,
                                                "completion_final": final, "turns": 3}))
            ov = dict(ov, done_reason="length", e2e_strict=False, e2e=False,
                      e2e_reason="format_parse_fail", response_len=resp_len)
        return raw, ov
    return mut


def test_tripwire_a_uses_final_turn_tokens(r: TestResults) -> None:
    """§3.6(a) second clause, literally: done_reason == length ∧ response_len <
    0.9 × 262,144 ∧ FINAL-turn output ≠ 64,000. The aggregate is not consulted."""
    def tw_a(out):
        return [tw for tw in out["tripwires"] if "final-turn" in tw]
    # Aggregate ABOVE the budget, final turn below it: the old aggregate rule
    # (completion < budget) would stay silent; the final-turn rule must fire.
    out = _run(SPEC, probe_mutate=_len_fit_length_row(final=30000, aggregate=70000))
    r.check_eq("aggregate 70000 / final 30000 -> tripwire", tw_a(out),
               ["(a) 1 LEN-FIT rows truncated with final-turn output != 64000"])
    # Final turn truncated EXACTLY at the budget: the budget bound, no tripwire,
    # whatever the aggregate says.
    out = _run(SPEC, probe_mutate=_len_fit_length_row(final=64000, aggregate=70000))
    r.check_eq("final 64000 exactly -> no tripwire", tw_a(out), [])
    # Final turn one token short of the budget: the budget did not bind.
    out = _run(SPEC, probe_mutate=_len_fit_length_row(final=63999, aggregate=63999))
    r.check_eq("final 63999 -> tripwire", len(tw_a(out)), 1)
    # Response at/above 0.9 × snapshot (= 235,929.6 chars): the response-length
    # clause excludes it (that row is the censoring clause's business, not
    # this one). 235,930 is the first integer length at or above the bound.
    out = _run(SPEC, probe_mutate=_len_fit_length_row(final=30000, aggregate=30000,
                                                      resp_len=235930))
    r.check_eq("response_len >= 0.9 cap -> excluded", tw_a(out), [])
    out = _run(SPEC, probe_mutate=_len_fit_length_row(final=30000, aggregate=30000,
                                                      resp_len=235929))
    r.check_eq("response_len just under 0.9 cap -> included", len(tw_a(out)), 1)
    # The same shape on a LEN-NOFIT reference row is out of scope for (a).
    def nofit(cls, dom, prob, raw, ov):
        if (dom, prob) == ("f", "p01"):
            raw = dict(raw, result=dict(raw["result"],
                                        tokens={"prompt": 10, "completion": 30000,
                                                "completion_final": 30000, "turns": 2}))
        return raw, ov
    out = _run(SPEC, probe_mutate=nofit)
    r.check_eq("LEN-NOFIT row not covered by (a)", tw_a(out), [])
    # Secondary token columns: aggregate and final reported separately.
    out = _run(SPEC, probe_mutate=_len_fit_length_row(final=30000, aggregate=70000))
    sec = out["secondary"]
    r.check_eq("aggregate max = 70000", sec["completion_tokens_max"], 70000)
    r.check_eq("final max = 64000 (the two LEN-NOFIT rows)", sec["completion_final_max"], 64000)
    r.check_eq("rows with final == budget", sec["completion_final_at_budget"], 2)


def main() -> None:
    r = TestResults("test_budget_probe_analysis")
    test_fisher_known_values(r)
    test_fit_rule_boundary(r)
    test_fixture_classes_and_primary(r)
    test_h1_and_kill_verdicts(r)
    test_tripwire_a_censored_probe_row(r)
    test_refuses_duplicate_key(r)
    test_refuses_missing_snapshot_cap_and_unknown_grade(r)
    test_refuses_wrong_meta_and_drifted_counts(r)
    test_refuses_key_mismatch(r)
    test_refuses_manifest_violations(r)
    test_refuses_probe_row_without_final_tokens(r)
    test_tripwire_a_uses_final_turn_tokens(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
