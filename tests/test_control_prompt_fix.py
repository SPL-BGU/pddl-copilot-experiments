"""Freeze gate 4 for the control-prompt analysis (tools/reanalysis/control_prompt_fix.py).

Run standalone: `python3 tests/test_control_prompt_fix.py`
Or via the shell wrapper: `bash tests/verify.sh`

The synthetic fixture (tests/fixtures/control_prompt_fix/, built by its
build_fixture.py) has the smoke layout: 20 domains d01..d20, one problem, three
wordings, so 60 trials per model, task and cell, 3 per domain. Every expected
number below is hand-computed from the plants of build_fixture.py; the
derivation is in the comment next to it.

Bootstrap arithmetic used below (frozen `cluster_bootstrap`: 20 domains drawn
with replacement, ratio estimator; every domain holds 3 trials, so a draw's
value is (sum of the drawn domains' paired differences) / 60):
  * every domain has the same difference d: every draw gives d, so the interval
    is [d, d] and equals the estimate;
  * one domain with sum s, the rest 0: a draw gives s*X/60 with X ~ Bin(20, 1/20)
    the number of times that domain is drawn. P(X = 0) = 0.358, so the 2.5%
    quantile is 0; P(X >= 3) = 0.0755 and P(X >= 4) = 0.0159, so the 97.5%
    quantile is X = 3: the interval is [0, 3s/60] (s = 1: [0, 5.0]; s = 3:
    [0, 15.0]; s = -3: [-15.0, 0]);
  * four domains with sum +1: X ~ Bin(20, 4/20). P(X = 0) = 0.0115 and
    P(X <= 1) = 0.0692, so the 2.5% quantile is X = 1; P(X >= 8) = 0.0321 and
    P(X >= 9) = 0.0100, so the 97.5% quantile is X = 8: [1/60, 8/60] in points
    [1.667, 13.333].
Sign-flip p (exact, over the 20 domain sums): 20 equal non-zero sums give
2/2^20 = 1.9073e-06; m equal non-zero sums and the rest 0 give 2/2^m (m = 1:
1.0; m = 4: 0.125); all zero gives 1.0.

No row of any real corpus is read here.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests" / "fixtures" / "control_prompt_fix"))

from tests._helpers import TestResults  # noqa: E402

import build_fixture as BF  # noqa: E402
from tools.delivered_rerun import constants as C  # noqa: E402
from tools.delivered_rerun import grade as G  # noqa: E402
from tools.delivered_rerun import run as RUN  # noqa: E402
from tools.reanalysis import control_prompt_fix as M  # noqa: E402
from tools.reanalysis import rq1_layout_regrade as RG  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "control_prompt_fix"
Q9, GM, Q35 = "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"
EPS = 1e-9
P20 = 2 / 2 ** 20                 # 20 equal non-zero domain sums
HOLM6 = 6 * P20                   # Holm, the smallest of six: 6 * p
DATES = "2026-11-27 to 2026-11-29 (fixture)"
FROZEN_RERUN_SHA = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"


def close(a, b):
    return a is not None and b is not None and abs(a - b) < EPS


# ------------------------------------------------------------------ helpers
def run_main(args: list[str]) -> tuple[int, str, str]:
    err, out = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        code = M.main(args)
    return code, err.getvalue(), out.getvalue()


def run_fixture(root: Path, extra: list[str] | None = None):
    out = Path(tempfile.mkdtemp(prefix="cpf_out_"))
    code, err, _ = run_main(["--fixture", str(root), "--out", str(out),
                             "--control-dates", DATES] + (extra or []))
    res = None
    if code == 0:
        res = json.loads((out / "control_prompt_fix.json").read_text())
        res["_md"] = (out / "control_prompt_fix.md").read_text()
    written = sorted(p.name for p in out.iterdir())
    shutil.rmtree(out)
    return code, err, res, written


def copy_fixture() -> Path:
    dst = Path(tempfile.mkdtemp(prefix="cpf_fx_")) / "fx"
    shutil.copytree(FIXTURE, dst)
    return dst


def cdir(root: Path, model: str, cell: str) -> Path:
    return root / "control" / BF.folder(model, cell, BF.RUN_TAG)


def edit_jsonl(path: Path, fn) -> None:
    recs = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fn(recs)))


def edit_json(path: Path, fn) -> None:
    obj = json.loads(path.read_text())
    fn(obj)
    path.write_text(json.dumps(obj, indent=1) + "\n")


def find(recs, task, dom, v):
    for i, o in enumerate(recs):
        r = o["result"]
        if (r["task"], r["domain_name"], r["prompt_variant"]) == (task, dom, v):
            return i
    raise KeyError((task, dom, v))


def set_answer(root: Path, model: str, cell: str, task: str, dom: str, v: int, kind: str):
    """Replace one control row with a builder row of another answer kind."""
    def fn(recs):
        i = find(recs, task, dom, v)
        row = BF.make_row(model, task, dom, v, kind)
        recs[i] = {"key": BF.key_of(row), "result": row}
        return recs
    edit_jsonl(cdir(root, model, cell) / "trials.jsonl", fn)


def expect_halt(r: TestResults, label: str, mutate, needle: str, extra=None) -> None:
    root = copy_fixture()
    try:
        mutate(root)
        code, err, _res, written = run_fixture(root, extra)
        r.check(f"refused: {label}", code == 2 and needle in err and written == [],
                f"code={code} written={written} err={err[-400:]}")
    finally:
        shutil.rmtree(root.parent)


def by(res, section, **kw):
    out = [e for e in res[section] if all(e.get(k) == v for k, v in kw.items())]
    assert len(out) == 1, (section, kw, len(out))
    return out[0]


# ------------------------------------------------------------------ the fixture is the builder's output
def test_fixture_is_builder_output(r):
    tmp = Path(tempfile.mkdtemp(prefix="cpf_build_"))
    try:
        BF.build(tmp)
        got = {p.relative_to(tmp).as_posix(): p.read_bytes() for p in tmp.rglob("*") if p.is_file()}
        want = {p.relative_to(FIXTURE).as_posix(): p.read_bytes() for p in FIXTURE.rglob("*")
                if p.is_file() and p.name != "build_fixture.py" and "__pycache__" not in p.parts}
        r.check_eq("fixture files = builder output (names)", sorted(got), sorted(want))
        r.check("fixture files = builder output (bytes)",
                all(got[k] == want.get(k) for k in got), [k for k in got if got[k] != want.get(k)][:5])
    finally:
        shutil.rmtree(tmp)


# ------------------------------------------------------------------ readers on the planted answers
def test_planted_answers(r):
    """Each planted answer kind, read by the frozen reader and the second reading."""
    plan, wrong, caps = tuple(BF.PLAN), tuple(BF.WRONG), tuple(BF.CAPS)
    A = BF.ANSWERS
    r.check_eq("right: frozen reads action lines", G.solve_plan(A["right"]), (plan, "strict_lines"))
    r.check_eq("right: no block", RG.block_plan(A["right"]), None)
    r.check_eq("JSON plan in the last block: the frozen reader misses it",
               G.solve_plan(A["json_block"]), ((), None))
    r.check_eq("JSON plan in the last block: block_plan reads it",
               RG.block_plan(A["json_block"]), (plan, RG.JSON_BLOCK))
    r.check_eq("right to wrong: frozen reads the right lines",
               G.solve_plan(A["right_to_wrong"]), (plan, "strict_lines"))
    r.check_eq("right to wrong: the block holds the wrong plan",
               RG.block_plan(A["right_to_wrong"]), (wrong, RG.JSON_BLOCK))
    r.check_eq("block of action lines: same plan both ways",
               (G.solve_plan(A["lines_block"])[0], RG.block_plan(A["lines_block"])),
               (plan, (plan, RG.LINES_BLOCK)))
    r.check_eq("unclosed fence: no block, no frozen plan",
               (G.solve_plan(A["unclosed"]), RG.block_plan(A["unclosed"])), (((), None), None))
    r.check_eq("capitals in a JSON block kept", RG.block_plan(A["caps_block"]),
               (caps, RG.JSON_BLOCK))
    table = {(d, "p01", p): v for d in BF.DOMAINS for p, v in
             ((plan, True), (wrong, False), (caps, False))}
    verdict = M.Verdicts(M.table_route(table))
    gt = json.loads((FIXTURE / "gt_cache.json").read_text())

    def two(kind, task="solve"):
        row = BF.make_row(Q9, task, "d01", 11, kind)
        from tools.delivered_rerun import schema as S
        spec = M.control_spec(M.SMOKE, Q9, "O", BF.RUN_TAG)
        if kind == "storage_cut":
            row = {**row, "response_truncated_by_storage": False}
        parsed = S.parse_row({"key": BF.key_of(row), "result": row}, spec, "t")
        need = G.solve_plans_to_validate([parsed])
        g = G.grade(parsed, gt, {k: verdict(*k) for k in need})
        s, f, lay = M.second_reading(parsed, g, verdict, gt)
        return g.ok, s, f, lay

    r.check_eq("json_block: frozen wrong, second right", two("json_block")[:3], (False, True, True))
    r.check_eq("right_to_wrong: frozen right, second wrong", two("right_to_wrong")[:3],
               (True, False, False))
    r.check_eq("caps_block: second wrong, case folded right", two("caps_block")[:3],
               (False, False, True))
    r.check_eq("lines_block: right both ways", two("lines_block"), (True, True, True, RG.LINES_BLOCK))
    r.check_eq("unclosed: wrong both ways, no plan block", two("unclosed"),
               (False, False, False, M.NO_PLAN_BLOCK))
    r.check_eq("simulate, one object per line equal to the key: frozen wrong, second right",
               two("per_line", "simulate"), (False, True, True, M.PER_LINE))
    r.check_eq("simulate, one object per line not equal to the key: wrong both",
               two("per_line_wrong", "simulate"), (False, False, False, M.PER_LINE))
    r.check_eq("simulate, one JSON object: right both", two("trace", "simulate"),
               (True, True, True, M.ONE_OBJECT))


# ------------------------------------------------------------------ the base fixture
# (n, frozen, second, case folded) per (model, task, cell), 60 trials each.
RATES = {
    # Gemma solve: O, B, Part C end v11 with a JSON plan in a block in all 20
    # domains: frozen 60 - 20 = 40, second and folded 60. A, Part A: 60.
    (GM, "solve", "O"): (40, 60, 60), (GM, "solve", "A"): (60, 60, 60),
    (GM, "solve", "B"): (40, 60, 60), (GM, "solve", "Part C"): (40, 60, 60),
    (GM, "solve", "Part A"): (60, 60, 60),
    # Gemma simulate: O and Part C wrong on v11 everywhere (in O, d05 v11 is the
    # exception row): 40 both readings. A, B, Part A: 60.
    (GM, "simulate", "O"): (40, 40, 40), (GM, "simulate", "A"): (60, 60, 60),
    (GM, "simulate", "B"): (60, 60, 60), (GM, "simulate", "Part C"): (40, 40, 40),
    (GM, "simulate", "Part A"): (60, 60, 60),
    # Qwen3.5-9B solve, v13 plants in every cell: d10 capitals (frozen wrong,
    # second wrong, folded right), d11 right to wrong (frozen right, second and
    # folded wrong), d12 action-line block (right), d13 unclosed fence (wrong).
    # Frozen 60-2 = 58, second 60-3 = 57, folded 60-2 = 58. A also wrong on v12
    # in all 20 domains: 38, 37, 38.
    (Q9, "solve", "O"): (58, 57, 58), (Q9, "solve", "A"): (38, 37, 38),
    (Q9, "solve", "B"): (58, 57, 58), (Q9, "solve", "Part C"): (58, 57, 58),
    (Q9, "solve", "Part A"): (58, 57, 58),
    # Qwen3.5-9B simulate: d20 v13 a wrong trace one object per line everywhere;
    # O and Part C also wrong on d01 v11: 58; the rest 59.
    (Q9, "simulate", "O"): (58, 58, 58), (Q9, "simulate", "A"): (59, 59, 59),
    (Q9, "simulate", "B"): (59, 59, 59), (Q9, "simulate", "Part C"): (58, 58, 58),
    (Q9, "simulate", "Part A"): (59, 59, 59),
    # Qwen3.6-35B solve: O has no plan on d01 (three wordings): 57. Part A wrong
    # on v13 in all domains: 40.
    (Q35, "solve", "O"): (57, 57, 57), (Q35, "solve", "A"): (60, 60, 60),
    (Q35, "solve", "B"): (60, 60, 60), (Q35, "solve", "Part C"): (60, 60, 60),
    (Q35, "solve", "Part A"): (40, 40, 40),
    # Qwen3.6-35B simulate: O and Part C write the right trace one object per
    # line on d01..d04 v11: frozen 56, second 60.
    (Q35, "simulate", "O"): (56, 60, 60), (Q35, "simulate", "A"): (60, 60, 60),
    (Q35, "simulate", "B"): (60, 60, 60), (Q35, "simulate", "Part C"): (56, 60, 60),
    (Q35, "simulate", "Part A"): (60, 60, 60),
}

# (est, lo, hi, p, p_holm, label) per (contrast, reading, model, task).
S1 = (100 / 3, 100 / 3, 100 / 3, P20)       # +1 on one wording in every domain
F1 = (-100 / 3, -100 / 3, -100 / 3, P20)    # -1 on one wording in every domain
Z = (0.0, 0.0, 0.0, 1.0, 1.0, "criterion met")
CONTRASTS = {
    # C1 = A minus O.
    # Gemma solve frozen: +1 at v11 in every domain -> [33.3, 33.3]; Holm: three
    # p of 2^-19 in the family, the smallest gets 6p, the next two 5p and 4p,
    # running max 6p.
    ("C1", "frozen", GM, "solve"): S1 + (HOLM6, "a difference is shown"),
    ("C1", "second", GM, "solve"): Z,                   # the block plan is right in O
    ("C1", "frozen", GM, "simulate"): S1 + (HOLM6, "a difference is shown"),
    ("C1", "second", GM, "simulate"): S1 + (HOLM6, "a difference is shown"),
    ("C1", "frozen", Q9, "solve"): F1 + (HOLM6, "a difference is shown"),
    ("C1", "second", Q9, "solve"): F1 + (HOLM6, "a difference is shown"),
    # Q9 simulate: d01 sum +1 -> [0, 5.0], est 1/60; 5.0 is inside (inclusive).
    ("C1", "frozen", Q9, "simulate"): (100 / 60, 0.0, 5.0, 1.0, 1.0, "criterion met"),
    ("C1", "second", Q9, "simulate"): (100 / 60, 0.0, 5.0, 1.0, 1.0, "criterion met"),
    # Q35 solve: d01 sum +3 -> est 3/60 = 5.0, [0, 15.0]: unresolved.
    ("C1", "frozen", Q35, "solve"): (5.0, 0.0, 15.0, 1.0, 1.0, "unresolved"),
    ("C1", "second", Q35, "solve"): (5.0, 0.0, 15.0, 1.0, 1.0, "unresolved"),
    # Q35 simulate frozen: d01..d04 sum +1 -> est 4/60, [1/60, 8/60]; p = 2/2^4 =
    # 0.125, Holm rank 4 of 6: 3 * 0.125 = 0.375 -> shown, not after Holm.
    ("C1", "frozen", Q35, "simulate"): (400 / 60, 100 / 60, 800 / 60, 0.125, 0.375,
                                        "a difference is shown (not after Holm)"),
    ("C1", "second", Q35, "simulate"): Z,
    # C2 = B minus O.
    ("C2", "frozen", GM, "solve"): Z, ("C2", "second", GM, "solve"): Z,   # B = O
    ("C2", "frozen", GM, "simulate"): S1 + (HOLM6, "a difference is shown"),
    ("C2", "second", GM, "simulate"): S1 + (HOLM6, "a difference is shown"),
    ("C2", "frozen", Q9, "solve"): Z, ("C2", "second", Q9, "solve"): Z,
    ("C2", "frozen", Q9, "simulate"): (100 / 60, 0.0, 5.0, 1.0, 1.0, "criterion met"),
    ("C2", "second", Q9, "simulate"): (100 / 60, 0.0, 5.0, 1.0, 1.0, "criterion met"),
    ("C2", "frozen", Q35, "solve"): (5.0, 0.0, 15.0, 1.0, 1.0, "unresolved"),
    ("C2", "second", Q35, "solve"): (5.0, 0.0, 15.0, 1.0, 1.0, "unresolved"),
    # Holm rank 2 of 6 (one p of 2^-19 below it): 5 * 0.125 = 0.625.
    ("C2", "frozen", Q35, "simulate"): (400 / 60, 100 / 60, 800 / 60, 0.125, 0.625,
                                        "a difference is shown (not after Holm)"),
    ("C2", "second", Q35, "simulate"): Z,
    # C3 = O minus Part C: Part C equals O everywhere but Q35 solve, where O lost
    # d01 (sum -3): est -5.0, [-15.0, 0]: unresolved.
    **{("C3", rd, m, t): Z for rd in ("frozen", "second") for m in (GM, Q9, Q35)
       for t in ("solve", "simulate") if (m, t) != (Q35, "solve")},
    ("C3", "frozen", Q35, "solve"): (-5.0, -15.0, 0.0, 1.0, 1.0, "unresolved"),
    ("C3", "second", Q35, "solve"): (-5.0, -15.0, 0.0, 1.0, 1.0, "unresolved"),
    # C4 = Part A minus B. Gemma solve frozen: B misses the v11 block plans.
    ("C4", "frozen", GM, "solve"): S1 + (HOLM6, "tools ahead"),
    ("C4", "second", GM, "solve"): (0.0, 0.0, 0.0, 1.0, 1.0, "no difference shown"),
    # Q35 solve: Part A wrong on v13 in every domain.
    ("C4", "frozen", Q35, "solve"): F1 + (HOLM6, "no tools ahead"),
    ("C4", "second", Q35, "solve"): F1 + (HOLM6, "no tools ahead"),
    **{("C4", rd, m, t): (0.0, 0.0, 0.0, 1.0, 1.0, "no difference shown")
       for rd in ("frozen", "second") for m, t in ((GM, "simulate"), (Q9, "solve"),
                                                    (Q9, "simulate"), (Q35, "simulate"))},
}
# Registered reading case per (model, task): R1 (C1), R2 (C2), R3 moved, rule 5.
READINGS = {
    (GM, "solve"): ("c", "a", False, True),      # layout only; B frozen 66.7, second 100
    (GM, "simulate"): ("b", "b", False, False),  # rise under both readings
    (Q9, "solve"): ("d", "a", False, False),     # a fall; B gap 96.7 - 95.0 = 1.7
    (Q9, "simulate"): ("a", "a", False, False),  # criterion met under both
    (Q35, "solve"): ("e", "e", True, False),     # unresolved; C3 unresolved -> moved
    (Q35, "simulate"): ("c", "c", False, False),  # layout only, frozen not after Holm
}


def test_base(r, res):
    r.check_eq("mode", res["mode"], "fixture")
    r.check_eq("design k", res["design"]["k_domains"], 20)
    for (m, t, cell), want in RATES.items():
        e = by(res, "rates", model=m, task=t, cell=cell)
        got = (e["frozen"]["right"], e["second"]["right"], e["folded"]["right"])
        r.check_eq(f"rate {m}/{t}/{cell}", (e["n"],) + got, (60,) + want)
    # Rate intervals where every domain is the same: Gemma solve O frozen (2 of 3
    # right in every domain) and Qwen3.6-35B simulate O second (all right).
    e = by(res, "rates", model=GM, task="solve", cell="O")["frozen"]
    r.check("rate interval equals the estimate (every domain 2/3)",
            close(e["est"], 200 / 3) and close(e["lo"], 200 / 3) and close(e["hi"], 200 / 3)
            and e["k"] == 20, e)
    r.check_eq("24 contrasts under two readings", len(res["contrasts"]), 48)
    for (name, rd, m, t), (est, lo, hi, p, ph, label) in CONTRASTS.items():
        c = by(res, "contrasts", name=name, reading=rd, model=m, task=t)
        r.check(f"{name} {rd} {m}/{t}: {est:.3f} [{lo:.3f}, {hi:.3f}] p {p:.3g} holm {ph:.3g}",
                close(c["est"], est) and close(c["lo"], lo) and close(c["hi"], hi)
                and close(c["p"], p) and close(c["p_holm"], ph) and c["k"] == 20
                and c["n_pairs"] == 60 and c["unpaired"] == 0,
                {k: c[k] for k in ("est", "lo", "hi", "p", "p_holm", "k", "n_pairs")})
        r.check_eq(f"{name} {rd} {m}/{t} label", c["label"], label)
    # The inclusive endpoint: exactly 5.0, met.
    c = by(res, "contrasts", name="C1", reading="frozen", model=Q9, task="simulate")
    r.check("endpoint exactly 5.0 counts as inside the margin",
            c["hi"] == 5.0 and c["label"] == "criterion met", c["hi"])
    for (m, t), (r1, r2, moved, both) in READINGS.items():
        e = by(res, "readings", model=m, task=t)
        r.check_eq(f"R1 {m}/{t}", e["R1"]["cases"], [r1])
        r.check_eq(f"R2 {m}/{t}", e["R2"]["cases"], [r2])
        for rr, name in (("R1", "C1"), ("R2", "C2")):
            for rd in ("frozen", "second"):
                c = by(res, "contrasts", name=name, reading=rd, model=m, task=t)
                r.check(f"{rr} {m}/{t} prints the {rd} label",
                        e[rr]["labels"][rd].startswith(c["label"] + " ("), e[rr]["labels"])
        r.check_eq(f"R3 {m}/{t} moved", e["R3"]["moved"], moved)
        r.check_eq(f"R4 {m}/{t} across a setup that moved",
                   e["R4"]["across_a_setup_that_moved"], moved)
        r.check(f"R4 {m}/{t} carries both dates",
                M.PART_A_DATES in e["R4"]["sentence"] and DATES in e["R4"]["sentence"])
        r.check_eq(f"rule 5 {m}/{t}", e["rule5"]["quote_both"], both)
    e = by(res, "readings", model=GM, task="solve")
    r.check_eq("rule 5 gap, Gemma solve B: 66.7 - 100", round(e["rule5"]["gap"], 6),
               round(200 / 3 - 100, 6))
    e = by(res, "readings", model=Q35, task="simulate")
    r.check("R1 carries the Holm note", e["R1"]["holm_notes"] ==
            ["frozen reading: a difference is shown (not after Holm)"], e["R1"])
    # The sentences of section 5, verbatim; (b) and (e) carry both estimates and intervals.
    r.check_eq("R1 (a) sentence", by(res, "readings", model=Q9, task="simulate")["R1"]["sentences"],
               ["removing the reference to the schema did not move the unaided baseline by more "
                "than 5 points"])
    r.check_eq("R2 (a) sentence", by(res, "readings", model=Q9, task="simulate")["R2"]["sentences"],
               ["stating the answer format did not move the unaided baseline by more than 5 points"])
    r.check_eq("R1 (b) sentence", by(res, "readings", model=GM, task="simulate")["R1"]["sentences"],
               ["the wrong reference lowered the unaided baseline (frozen +33.3 [+33.3, +33.3], "
                "second reading +33.3 [+33.3, +33.3])"])
    r.check_eq("R2 (b) sentence", by(res, "readings", model=GM, task="simulate")["R2"]["sentences"],
               ["stating the answer format raises the unaided baseline, and not through layout "
                "alone (frozen +33.3 [+33.3, +33.3], second reading +33.3 [+33.3, +33.3])"])
    r.check_eq("R1 (c) sentence", by(res, "readings", model=GM, task="solve")["R1"]["sentences"],
               ["the wrong reference changed how the answers were laid out, and the grader did "
                "not read that layout; what the models wrote did not change by more than the "
                "second reading shows"])
    r.check_eq("R2 (c) sentence", by(res, "readings", model=Q35, task="simulate")["R2"]["sentences"],
               ["stating the answer format raises the frozen grade through layout: the answers "
                "come in a layout the grader reads; what the models wrote did not change by more "
                "than the second reading shows"])
    r.check_eq("R1 (d) sentence", by(res, "readings", model=Q9, task="solve")["R1"]["sentences"],
               ["a fall, reported as it is: the reference, wrong as it was, did not cost the "
                "model anything on that task"])
    r.check_eq("R1 (e) sentence", by(res, "readings", model=Q35, task="solve")["R1"]["sentences"],
               ["unresolved (frozen +5.0 [+0.0, +15.0], second reading +5.0 [+0.0, +15.0])"])
    r.check_eq("R2 Holm note", by(res, "readings", model=Q35, task="simulate")["R2"]["holm_notes"],
               ["frozen reading: a difference is shown (not after Holm)"])
    r.check("R4 carries no Holm note where none applies",
            all(e["R4"]["holm_notes"] == [] for e in res["readings"]))
    # Item 5: one request re-sent in Qwen3.6-35B A (its audit holds one line twice).
    extra = res["audit"]["extra_user_lines"]
    r.check_eq("extra user-message lines reported per cell",
               {k: v for k, v in extra.items() if v}, {BF.folder(Q35, "A", BF.RUN_TAG): 1})
    r.check_eq("extra user-message lines: every cell listed", len(extra), 9)
    r.check("R3 moved sentence", by(res, "readings", model=Q35, task="solve")["R3"]["sentence"]
            .startswith("the setup moved between Part C and the control for this model and task"))
    # Corpus: one exception row kept (Gemma O, 1 of 120 <= 1%); one storage-cut
    # row accepted (Qwen3.6-35B O, stopped at the output cap).
    ex = {c["cell"]: c["exception_rows"] for c in res["corpus"]}
    cut = {c["cell"]: c["storage_cut_accepted"] for c in res["corpus"]}
    r.check_eq("exception rows kept and counted",
               {k: v for k, v in ex.items() if v}, {BF.folder(GM, "O", BF.RUN_TAG): 1})
    r.check_eq("storage-cut rows accepted and counted",
               {k: v for k, v in cut.items() if v}, {BF.folder(Q35, "O", BF.RUN_TAG): 1})
    # Secondary tables.
    s = by(res, "secondary", model=GM, task="solve", cell="O")
    r.check_eq("layout Gemma solve O", s["layout"],
               {RG.JSON_BLOCK: 20, M.NO_PLAN_BLOCK: 40})
    r.check_eq("failure reasons Gemma solve O", s["failure_reasons"], {"no_plan_extracted": 20})
    r.check_eq("by wording Gemma solve O", s["by_wording"],
               {"11": {"frozen": 0, "second": 20}, "12": {"frozen": 20, "second": 20},
                "13": {"frozen": 20, "second": 20}})
    s = by(res, "secondary", model=Q9, task="solve", cell="O")
    r.check_eq("layout Qwen3.5-9B solve O (capitals, right to wrong, lines block)", s["layout"],
               {RG.JSON_BLOCK: 2, RG.LINES_BLOCK: 1, M.NO_PLAN_BLOCK: 57})
    r.check_eq("at the output cap: the unclosed fence", s["at_output_cap"], 1)
    r.check_eq("case folded > second reading", (s["folded_k"], s["by_wording"]["13"]["second"]),
               (58, 17))
    s = by(res, "secondary", model=Q35, task="simulate", cell="O")
    r.check_eq("simulate layout one object per line", s["layout"],
               {M.ONE_OBJECT: 56, M.PER_LINE: 4})
    s = by(res, "secondary", model=GM, task="simulate", cell="O")
    r.check_eq("exception row graded as it is", (s["exception_rows"], s["failure_reasons"]),
               (1, {"exception": 1, "trajectory_mismatch": 19}))
    s = by(res, "secondary", model=GM, task="solve", cell="A")
    r.check_eq("moves O -> A Gemma solve", s["moves_from_O"],
               {"no_plan_extracted -> plan_valid": 20, "plan_valid -> plan_valid": 40})
    s = by(res, "secondary", model=Q35, task="solve", cell="O")
    r.check_eq("Q35 solve O at cap (the storage-cut row)", s["at_output_cap"], 1)
    # Route: R and W stored for every domain (40 plans) checked first; CAPS of d10
    # validated new (41 in all).
    r.check_eq("route checked / validated", (res["route_checked_plans"], res["validated_plans"]),
               (40, 41))
    md = res["_md"]
    r.check("markdown states the count of contrasts with every table",
            md.count("24 contrasts, each under two readings") >= 8)
    r.check("R3: Part C's level not set beside the control where the setup moved",
            "| Qwen3.6-35B | solve | Part C |" not in md
            and "| Qwen3.6-35B | simulate | Part C |" in md
            and "Part C is left out of this table for Qwen3.6-35B solve" in md)
    r.check("markdown names the reading of each contrast table",
            "contrasts C1 to C4, frozen grade" in md and "contrasts C1 to C4, second reading" in md)
    r.check("no em-dash in the markdown", "\u2014" not in md)


# ------------------------------------------------------------------ refusals
def _dup(root):
    def fn(recs):
        return recs + [copy.deepcopy(recs[0])]
    edit_jsonl(cdir(root, Q9, "A") / "trials.jsonl", fn)


def _cut_not_at_cap(root):
    def fn(recs):
        i = find(recs, "solve", "d02", 11)
        recs[i]["result"]["response_truncated_by_storage"] = True
        return recs
    edit_jsonl(cdir(root, Q9, "O") / "trials.jsonl", fn)


def _two_exceptions(root):
    set_answer(root, Q9, "B", "solve", "d03", 11, "exception")
    set_answer(root, Q9, "B", "solve", "d04", 11, "exception")


def _short(root):
    edit_jsonl(cdir(root, Q9, "A") / "trials.jsonl", lambda recs: recs[:-1])


def _rename_problem(cells, n=1):
    def mut(root):
        for cell in cells:
            def fn(recs):
                for i in range(n):
                    j = find(recs, "simulate", f"d{i + 1:02d}", 12)
                    recs[j]["result"]["problem_name"] = "p02"
                    recs[j]["key"][3] = "p02"
                return recs
            edit_jsonl(cdir(root, Q9, cell) / "trials.jsonl", fn)
    return mut


def _unknown_reason(root):
    def fn(recs):
        recs[5]["result"]["failure_reason"] = "plan_almost_valid"
        return recs
    edit_jsonl(cdir(root, GM, "B") / "trials.jsonl", fn)


def _audit(model, cell, fn):
    def mut(root):
        edit_jsonl(cdir(root, model, cell) / "system_prompt_audit.jsonl", fn)
    return mut


def _set_line(i, **kw):
    def fn(recs):
        recs[i].update(kw)
        return recs
    return fn


def _settings(model, cell, **kw):
    def mut(root):
        edit_json(cdir(root, model, cell) / "client_settings.json", lambda s: s.update(kw))
    return mut


def _serve_version(root):
    p = root / "serve_logs" / f"24000004-vllm-{GM}.log"
    p.write_text(p.read_text().replace("v0.20.2", "v0.22.0"))


def _route_disagrees(root):
    def fn(obj):
        for e in obj:
            if e["domain"] == "d07" and e["plan"] == BF.PLAN:
                e["valid"] = False
    edit_json(root / "route" / "plan_verdicts.json", fn)


def _filed_readout(root):
    def fn(obj):
        obj["e2"][0]["a_pct"] += 1.0
    edit_json(root / "filed_readout.json", fn)


def _filed_regrade(root):
    def fn(obj):
        for c in obj["cells"]:
            if (c["tag"], c["task"], c["arm"]) == (Q35, "simulate", "unaided"):
                c["tolerant_k"] = 56
    edit_json(root / "filed_regrade.json", fn)


def _summary_ctx(root):
    p = next(cdir(root, Q35, "B").glob("summary_*.json"))
    edit_json(p, lambda s: s["meta"].update(num_ctx=32768))


def _rm(rel):
    def mut(root):
        for p in root.glob(rel):
            p.unlink()
    return mut


def test_refusals(r):
    expect_halt(r, "duplicate trial key", _dup, "duplicate trial key")
    expect_halt(r, "a storage-cut row that did not stop at the output cap", _cut_not_at_cap,
                "did not stop at the output cap")
    # 2 exception rows of 120 = 1.7% > 1%.
    expect_halt(r, "exception rows above 1% -> VOID", _two_exceptions, "VOID (section 7)")
    expect_halt(r, "a short cell (a missing trial key)", _short, "119 rows, registered 120")
    # 2 renamed keys in one cell: the three cells share 118 of 120 = 98.3% < 99%.
    expect_halt(r, "cells share fewer than 99% of their keys -> model VOID",
                _rename_problem(("A",), n=2), "share 118 of 120 trial keys")
    # The same renamed key in all three cells: pairing holds, Part C's keys differ.
    expect_halt(r, "keys that differ from Part C's", _rename_problem(("O", "A", "B")),
                "keys differ from Part C's")
    expect_halt(r, "an unknown failure_reason (loader)", _unknown_reason,
                "unknown failure_reason 'plan_almost_valid'")
    expect_halt(r, "audit: wrong system digest",
                _audit(Q9, "A", _set_line(3, system_sha256="0" * 64)),
                "is not the registered text of cell A")
    expect_halt(r, "audit: the stored text is not the registered text",
                _audit(Q9, "B", _set_line(0, system_text="You are a helpful assistant.")),
                "byte for byte")
    expect_halt(r, "audit: cell O marked swapped", _audit(GM, "O", _set_line(7, swapped=True)),
                "swapped=True")
    expect_halt(r, "audit: cell A marked not swapped",
                _audit(GM, "A", _set_line(7, swapped=False)), "swapped=False")
    expect_halt(r, "audit: a line with tools", _audit(Q35, "B", _set_line(9, has_tools=True)),
                "has tools")
    expect_halt(r, "audit: a missing audit file",
                _rm(f"control/{BF.folder(Q35, 'A', BF.RUN_TAG)}/system_prompt_audit.jsonl"),
                "no system_prompt_audit.jsonl")
    expect_halt(r, "audit: fewer lines than rows", _audit(Q9, "O", lambda recs: recs[:-1]),
                "fewer than its 60 rows")
    expect_halt(r, "user-text digests differ between the cells of a model",
                _audit(Q9, "B", _set_line(11, user_sha256="a" * 64)),
                "the user messages differ between the cells")
    expect_halt(r, "client_settings.json names the wrong cell",
                _settings(GM, "B", no_tools_system="no-pointer"),
                "client_settings.json no_tools_system='no-pointer'")
    expect_halt(r, "client_settings.json names another cell's audit log",
                _settings(GM, "B", system_audit_log="/x/slurm_vllm_other/system_prompt_audit.jsonl"),
                "is not this cell's audit log")
    expect_halt(r, "serve log shows another vLLM", _serve_version, "shows vLLM ['0.22.0']")
    expect_halt(r, "a missing serve log", _rm(f"serve_logs/24000001-vllm-{Q9}.log"),
                "not in")
    expect_halt(r, "apparatus: context window in client_settings.json",
                _settings(Q9, "O", max_model_len=32768), "max_model_len 32768")
    expect_halt(r, "apparatus: context window in a summary", _summary_ctx, "num_ctx=32768")
    expect_halt(r, "the route disagrees with a stored verdict", _route_disagrees,
                "route disagrees with the stored verdict")
    expect_halt(r, "the rerun does not reproduce the filed readout", _filed_readout,
                "do not reproduce the filed readout")
    expect_halt(r, "the second reading does not reproduce the filed re-grade", _filed_regrade,
                "does not reproduce the filed re-grade")
    expect_halt(r, "fixture without its marker", _rm("SYNTHETIC_FIXTURE"),
                "has no SYNTHETIC_FIXTURE marker")
    expect_halt(r, "fixture mode refuses --numbers", lambda root: None,
                "--numbers is for live mode only", extra=["--numbers"])
    expect_halt(r, "a registered-size design in fixture mode",
                lambda root: edit_json(root / "design.json", lambda d: d.update(
                    per_task_cell=300, per_folder=600, per_wording=200, per_task_wording=100)),
                "refuses a registered-size design")
    # Item 7 by hand: with a note the run passes without serve logs and records it.
    root = copy_fixture()
    try:
        _rm("serve_logs/*")(root)
        code, err, res, _ = run_fixture(root, ["--version-checked-by-hand",
                                               "banners read with probe_serving_env.sh"])
        r.check("item 7 by hand: passes and is recorded",
                code == 0 and res["audit"]["version_note"] == "banners read with "
                "probe_serving_env.sh" and res["audit"]["serve_logs"] == {}, err[-300:])
        code, err, _, _ = run_fixture(root)
        r.check("item 7: no serve log and no note halts", code == 2 and "not in" in err, err)
    finally:
        shutil.rmtree(root.parent)
    try:
        M.audit_control(FIXTURE / "control", {}, None, None)
        r.check("item 7 neither checked nor noted", False)
    except M.AuditFailed as e:
        r.check("item 7 neither checked nor noted", "item 7" in str(e) and "NOTE" in str(e), str(e))


# ------------------------------------------------------------------ tripwires
def test_tripwires(r):
    # T2: Part C of Gemma simulate made all right (60) while O stays 40: 33.3 > 20.
    # The filed records are moved with it, so the reproduction checks still hold.
    root = copy_fixture()
    try:
        def fn(recs):
            out = []
            for o in recs:
                if o["result"]["task"] == "simulate":
                    row = BF.make_row(GM, "simulate", o["result"]["domain_name"],
                                      o["result"]["prompt_variant"], "trace")
                    o = {"key": BF.key_of(row), "result": row}
                out.append(o)
            return out
        edit_jsonl(root / "rerun" / f"slurm_vllm_{GM}_off_no-tools_delivered-rerun" /
                   "trials.jsonl", fn)
        edit_json(root / "filed_readout.json", lambda d: [
            e.update(a_pct=100.0) for e in d["e2"] if (e["model"], e["task"]) == (GM, "simulate")])
        edit_json(root / "filed_regrade.json", lambda d: [
            c.update(frozen_k=60, tolerant_k=60, folded_k=60) for c in d["cells"]
            if (c["tag"], c["task"], c["arm"]) == (GM, "simulate", "unaided")])
        code, err, _, written = run_fixture(root)
        r.check("T2 fires and halts", code == 2 and "T2:gemma4_26b-a4b:simulate" in err
                and "-33.3 points from Part C" in err and written == [], err[-500:])
        notes = root / "notes.json"
        notes.write_text(json.dumps({"T2:gemma4_26b-a4b:simulate": "audited: planted"}))
        code, err, res, _ = run_fixture(root, ["--audited-tripwires", "T2:gemma4_26b-a4b:simulate",
                                               "--audit-notes", str(notes)])
        r.check("T2 released with an audit note, note recorded",
                code == 0 and res["tripwires_audited"]["T2:gemma4_26b-a4b:simulate"]["note"]
                == "audited: planted" and "audited: planted" in res["_md"], err[-300:])
        code, err, _, _ = run_fixture(root, ["--audited-tripwires", "T2:gemma4_26b-a4b:simulate"])
        r.check("a released tripwire needs a note", code == 2 and "--audit-notes" in err, err)
    finally:
        shutil.rmtree(root.parent)
    # T1: every control simulate answer right -> 60 of 60 in all nine cells. (T2
    # also fires: Gemma O 60 against Part C 40.)
    root = copy_fixture()
    try:
        for m in BF.MODELS:
            for cell in BF.CELLS:
                def fn(recs, m=m):
                    out = []
                    for o in recs:
                        if o["result"]["task"] == "simulate":
                            row = BF.make_row(m, "simulate", o["result"]["domain_name"],
                                              o["result"]["prompt_variant"], "trace")
                            o = {"key": BF.key_of(row), "result": row}
                        out.append(o)
                    return out
                edit_jsonl(cdir(root, m, cell) / "trials.jsonl", fn)
        code, err, _, _ = run_fixture(root)
        r.check("T1 fires (a rate the same in all nine cells)",
                code == 2 and "T1:simulate:frozen" in err and "T1:simulate:second" in err, err[-600:])
    finally:
        shutil.rmtree(root.parent)
    # T3: a cell in which the frozen grader reads no answer on ONE task (solve made
    # all prose in Qwen3.5-9B B; its simulate answers stay readable).
    root = copy_fixture()
    try:
        def fn(recs):
            out = []
            for o in recs:
                r_ = o["result"]
                if r_["task"] == "solve":
                    row = BF.make_row(Q9, "solve", r_["domain_name"], r_["prompt_variant"],
                                      "prose")
                    o = {"key": BF.key_of(row), "result": row}
                out.append(o)
            return out
        edit_jsonl(cdir(root, Q9, "B") / "trials.jsonl", fn)
        code, err, _, _ = run_fixture(root)
        r.check("T3 fires for the one task with no readable answer",
                code == 2 and "T3:Qwen3_5_9B:B:solve" in err
                and "T3:Qwen3_5_9B:B:simulate" not in err, err[-600:])
    finally:
        shutil.rmtree(root.parent)


# ------------------------------------------------------------------ the freeze gate
def test_live_gate(r):
    out = Path(tempfile.mkdtemp(prefix="cpf_live_"))
    try:
        base = ["--control-root", "/nonexistent/control", "--results", "/nonexistent",
                "--marketplace", "/nonexistent", "--out", str(out), "--control-dates", "x"]
        code, err, _ = run_main(base)
        r.check("live without --i-have-frozen reads nothing",
                code == 2 and "refusing to read the control" in err, err)
        code, err, _ = run_main(base + ["--i-have-frozen", "0" * 64])
        r.check("live with a wrong hash reads nothing",
                code == 2 and "refusing to read the control" in err, err)
        r.check_eq("nothing written", list(out.iterdir()), [])
        code, err, _ = run_main(base + ["--i-have-frozen", M.package_sha256()])
        r.check("with the right hash it goes on to read the control (and finds none)",
                code == 2 and "refusing" not in err and "/nonexistent/control" in err, err)
    finally:
        shutil.rmtree(out)


def test_package_hash(r):
    r.check_eq("DEPENDENCIES sorted, no duplicates", list(M.DEPENDENCIES),
               sorted(set(M.DEPENDENCIES)))
    frozen_pkg = {rel for rel, _ in RUN.frozen_files()}
    listed = {rel for rel, _ in M.frozen_files()}
    r.check("the frozen rerun package and its dependencies are listed", frozen_pkg <= listed,
            sorted(frozen_pkg - listed))
    r.check("the script itself is hashed", M.SCRIPT in listed)
    for d in ("pddl_eval/control_prompts.py", "tools/reanalysis/rq1_layout_regrade.py",
              "tools/reanalysis/rq1_metrics.py", "tools/reanalysis/rq3_context_pilot.py",
              "tools/reanalysis/iss027_common.py", "tools/reanalysis/gen_common.py"):
        r.check(f"listed: {d}", d in listed)
    # Every repo module the script imports, in a fresh interpreter.
    code = ("import os, sys; import tools.reanalysis.control_prompt_fix as M; "
            "R = os.getcwd(); print('\\n'.join(sorted(os.path.relpath(m.__file__, R) for m in "
            "list(sys.modules.values()) if getattr(m, '__file__', None) and "
            "os.path.abspath(m.__file__).startswith(R + os.sep))))")
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True,
                          text=True)
    imported = set(proc.stdout.split())
    r.check("import ran", proc.returncode == 0 and imported, proc.stderr[-300:])
    r.check("DEPENDENCIES cover every imported repo module", imported <= listed,
            sorted(imported - listed))
    h = M.package_sha256()
    r.check("package hash is a stable sha256", len(h) == 64 and h == M.package_sha256())
    r.check_eq("the frozen rerun package hash is unchanged", RUN.package_sha256(), FROZEN_RERUN_SHA)
    proc = subprocess.run([sys.executable, "-O", "-m", "tools.reanalysis.control_prompt_fix",
                           "--print-package-hash"], cwd=REPO_ROOT, capture_output=True, text=True)
    r.check("python -O refused", proc.returncode != 0 and "python -O" in proc.stderr,
            proc.stderr[-300:])


# ------------------------------------------------------------------ registered constants
def test_constants(r):
    try:
        M.check_constants()
        M.check_design(M.REGISTERED, registered=True)
        M.check_smoke_design()
        r.check("registered constants and design pass", True)
    except C.RegisteredCheckFailed as e:
        r.check("registered constants and design pass", False, str(e))
    flips = {
        "CELLS": ("O", "B", "A"), "WRAPPER": {"O": "registered", "A": "format-stated",
                                              "B": "no-pointer"},
        "CELL_TOKENS": {"O": "no-tools", "A": "no-tools-sysformat", "B": "no-tools-syspointer-off"},
        "SYSTEM_SHA256": {**M.SYSTEM_SHA256, "B": {**M.SYSTEM_SHA256["B"], "solve": "0" * 64}},
        "MODELS": {**M.MODELS, "Qwen3_5_9B": "Qwen/Qwen3.5-4B"},
        "MODEL_ORDER": ("Qwen3_5_9B", "gemma4_26b-a4b"),
        "TASKS": ("solve", "validate_plan"), "WORDINGS": (11, 12, 14),
        "CONTEXT_WINDOW": 32_768, "OUTPUT_CAP": {"solve": 8_192, "simulate": 8_192},
        "STORAGE_CAP": 500, "VLLM_VERSION": "0.22.0", "RUN_TAG": "control",
        "SMOKE_TAG": "control-smoke", "R2_TAG": "control-r3", "PYVALIDATOR": "0.1.6",
        "MARGIN": 4.0, "LEVEL": 0.90, "B_BOOT": 1_000, "SEED": 1, "HOLM_FAMILY": 12,
        "HOLM_ALPHA": 0.10, "CONTRASTS": ("C1", "C2", "C3"), "N_CONTRASTS": 12,
        "READINGS": ("frozen",), "PART_A_DATES": "2026-10-03", "QUOTE_BOTH_POINTS": 10.0,
        "SMOKE_NONEMPTY": 0.90, "VOID_FRAC": 0.05, "PAIRING_MIN": 0.95,
        "TRIPWIRE_POINTS": 10.0,
    }
    for name, value in flips.items():
        old = getattr(M, name)
        setattr(M, name, value)
        try:
            M.check_constants()
            r.check(f"flipped {name} is caught", False)
        except C.RegisteredCheckFailed:
            r.check(f"flipped {name} is caught", True)
        except Exception as e:  # noqa: BLE001 - any other failure is a test failure
            r.check(f"flipped {name} is caught", False, repr(e))
        finally:
            setattr(M, name, old)
    import dataclasses
    for field, value in (("per_task_cell", 299), ("per_folder", 599), ("per_wording", 199),
                         ("per_task_wording", 99), ("k_domains", 19)):
        d = dataclasses.replace(M.REGISTERED, **{field: value})
        for registered in (True,):
            try:
                M.check_design(d, registered=registered)
                r.check(f"design {field}={value} is caught", False)
            except C.RegisteredCheckFailed:
                r.check(f"design {field}={value} is caught", True)
    try:
        M.check_design(dataclasses.replace(M.REGISTERED), registered=True)
        r.check("a copy of REGISTERED is not REGISTERED", False)
    except C.RegisteredCheckFailed:
        r.check("a copy of REGISTERED is not REGISTERED", True)


# ------------------------------------------------------------------ labels and readings
def test_labels(r):
    def c(est, lo, hi, ph=0.001):
        return {"est": est, "lo": lo, "hi": hi, "p_holm": ph}
    r.check_eq("met and shown at once (a small, well-estimated shift)",
               M.contrast_label(c(2.0, 1.0, 3.0)), "criterion met; a difference is shown")
    r.check_eq("met and shown, not after Holm", M.contrast_label(c(2.0, 1.0, 3.0, 0.05)),
               "criterion met; a difference is shown (not after Holm)")
    r.check_eq("inclusive endpoints [-5, 5]", M.contrast_label(c(0.0, -5.0, 5.0, 1.0)),
               "criterion met")
    r.check_eq("just outside the margin", M.contrast_label(c(0.0, -5.000001, 5.0, 1.0)),
               "unresolved")
    r.check_eq("lo exactly 0 does not exclude 0", M.contrast_label(c(3.0, 0.0, 6.0, 0.001)),
               "unresolved")
    r.check_eq("C4 tools ahead", M.c4_label(c(10.0, 2.0, 20.0)), "tools ahead")
    r.check_eq("C4 no tools ahead, not after Holm", M.c4_label(c(-10.0, -20.0, -2.0, 0.2)),
               "no tools ahead (not after Holm)")
    r.check_eq("C4 no difference shown (margin not applied)", M.c4_label(c(1.0, -0.5, 2.0)),
               "no difference shown")
    fz, sc = c(2.0, 1.0, 3.0), c(2.0, 1.0, 3.0)
    fz["label"] = sc["label"] = M.contrast_label(fz)
    e = M.r12_reading("C1", fz, sc)
    r.check_eq("R1: met under both and a rise under both -> a sentence for a and for b, in order",
               (e["cases"], len(e["sentences"])), (["a", "b"], 2))
    r.check("R1: the (a) sentence comes first", e["sentences"][0].startswith("removing the"))
    fz, sc = c(-2.0, -4.0, -1.0), c(-2.0, -4.0, -1.0)
    fz["label"] = sc["label"] = M.contrast_label(fz)
    r.check_eq("R1: met and a fall -> a, d", M.r12_reading("C1", fz, sc)["cases"], ["a", "d"])
    # A rise under the second reading only (frozen unresolved): no case (a) to (d)
    # holds, so (e) "unresolved"; the labels still say what each reading shows.
    fz, sc = c(4.0, -1.0, 9.0, 1.0), c(10.0, 2.0, 18.0)
    fz["label"], sc["label"] = M.contrast_label(fz), M.contrast_label(sc)
    e = M.r12_reading("C1", fz, sc)
    r.check("R1: a rise under the second reading only -> (e), labels printed",
            e["cases"] == ["e"] and e["labels"]["second"].startswith("a difference is shown"), e)
    fz, sc = c(-10.0, -20.0, -2.0), c(-10.0, -20.0, -2.0)
    fz["label"] = sc["label"] = M.contrast_label(fz)
    e = M.r12_reading("C2", fz, sc)
    r.check_eq("R2 fall sentence", (e["cases"], e["sentences"]),
               (["d"], ["a fall, reported as it is: stating the answer format lowered the unaided "
                        "baseline on that task"]))
    r.check("R3 met", M.r3_reading(c(1.0, -4.0, 5.0))["moved"] is False)
    r.check("R3 not met", M.r3_reading(c(1.0, -6.0, 5.0))["moved"] is True)
    s = M.r4_reading({**c(1, 2, 3), "label": "tools ahead"}, {**c(1, 2, 3), "label": "tools ahead"},
                     True, "D")["sentence"]
    r.check("R4 with a moved setup", s.endswith("; across a setup that moved") and "D" in s, s)
    e = M.r4_reading({**c(10, 2, 20, 0.2), "label": "tools ahead (not after Holm)"},
                     {**c(1, 2, 3), "label": "tools ahead"}, False, "D")
    r.check_eq("R4 Holm note", e["holm_notes"], ["frozen reading: tools ahead (not after Holm)"])


# ------------------------------------------------------------------ smoke check
def smoke_run(root: Path, extra: list[str] | None = None) -> tuple[int, str]:
    out = io.StringIO()
    lines: list[str] = []
    code = M.smoke_check(root, (root / "serve_logs") if extra is None else None,
                         (extra or [None])[0], out=lines.append)
    out.write("\n".join(lines))
    return code, out.getvalue()


def smoke_dir(root: Path, model: str, cell: str) -> Path:
    return root / BF.folder(model, cell, BF.SMOKE_TAG)


def test_smoke(r):
    tmp = Path(tempfile.mkdtemp(prefix="cpf_smoke_"))
    try:
        root = tmp / "clean"
        BF.build_smoke(root)
        code, text = smoke_run(root)
        r.check("smoke: a clean mini smoke passes",
                code == 0 and "RESULT: PASS" in text and text.count(": PASS:") == 7, text)
        code, text = smoke_run(root, extra=[None])
        r.check("smoke: item 7 NOT CHECKED without serve logs or a note",
                code == 1 and "item 7: NOT CHECKED" in text, text)
        code, text = smoke_run(root, extra=["read the banners by hand"])
        r.check("smoke: item 7 checked by hand with a note",
                code == 0 and "checked by hand, not by this script: read the banners" in text, text)
        # More than 5% empty answers: 7 of 120 (5.8%); a marked answer elsewhere
        # must never be printed.
        bad = tmp / "bad"
        shutil.copytree(root, bad)

        def fn(recs):
            for i in range(7):
                recs[i]["result"]["response"] = ""
            recs[50]["result"]["response"] = "ZEBRA-ANSWER-TEXT (go l1 l2)"
            return recs
        edit_jsonl(smoke_dir(bad, GM, "A") / "trials.jsonl", fn)
        code, text = smoke_run(bad)
        r.check("smoke: more than 5% empty answers fails item 3",
                code == 1 and "item 3: FAIL" in text and "RESULT: FAIL" in text, text)
        r.check("smoke: no answer text printed", "ZEBRA" not in text)
        item3 = [ln for ln in text.splitlines() if "fewer than" in ln]
        r.check("smoke: no rate or count printed for item 3",
                len(item3) == 1 and re.sub(r"slurm_vllm_\S+", "", item3[0]).count("95") == 1
                and not re.search(r"\d+\.\d|\b(7|113|5\.8)\b", re.sub(r"slurm_vllm_\S+", "",
                                                                    item3[0])), item3)
        r.check("smoke: no percentage anywhere but the threshold",
                set(re.findall(r"\d+(?:\.\d+)?%", text)) == {"95%"}, re.findall(r"\d+%", text))
        # 6 of 120 empty (5.0%): passes (at least 95% non-empty).
        ok6 = tmp / "ok6"
        shutil.copytree(root, ok6)

        def fn6(recs):
            for i in range(6):
                recs[i]["result"]["response"] = ""
            return recs
        edit_jsonl(smoke_dir(ok6, GM, "A") / "trials.jsonl", fn6)
        code, text = smoke_run(ok6)
        r.check("smoke: exactly 95% non-empty passes", code == 0, text)
        # A storage-cut row (even at the cap), an exception row, a short cell.
        for label, mutate, needle in (
                ("a row cut by storage", lambda recs: [recs[0]["result"].update(
                    response_truncated_by_storage=True, done_reason="length", truncated=True),
                    recs][1], "item 2: FAIL"),
                ("an exception row", lambda recs: [recs.__setitem__(0, {
                    "key": recs[0]["key"], "result": BF.make_row(
                        Q35, "solve", "d01", 11, "exception")}), recs][1], "item 2: FAIL"),
                ("a short cell", lambda recs: recs[:-1], "item 1: FAIL")):
            d = tmp / "m"
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(root, d)
            edit_jsonl(smoke_dir(d, Q35, "O") / "trials.jsonl", mutate)
            code, text = smoke_run(d)
            r.check(f"smoke: {label} fails", code == 1 and needle in text, text)
        # A re-sent request: one audit line twice in one cell. Passes, and is counted.
        d = tmp / "m"
        shutil.rmtree(d)
        shutil.copytree(root, d)
        edit_jsonl(smoke_dir(d, GM, "B") / "system_prompt_audit.jsonl",
                   lambda recs: recs + [{k: v for k, v in recs[3].items() if k != "system_text"}])
        code, text = smoke_run(d)
        r.check("smoke: a re-sent request passes item 5 and is counted",
                code == 0 and "item 5: PASS" in text
                and f"(re-sent requests): {BF.folder(GM, 'B', BF.SMOKE_TAG)}: 1" in text
                and f"(re-sent requests): {BF.folder(GM, 'O', BF.SMOKE_TAG)}: 0" in text, text)
        shutil.rmtree(d)
        shutil.copytree(root, d)
        edit_json(smoke_dir(d, Q9, "B") / "client_settings.json",
                  lambda s: s.update(no_tools_system="registered"))
        code, text = smoke_run(d)
        r.check("smoke: wrong client settings fails item 6", code == 1 and "item 6: FAIL" in text,
                text)
        edit_jsonl(smoke_dir(d, Q9, "A") / "system_prompt_audit.jsonl",
                   _set_line(2, user_sha256="b" * 64))
        code, text = smoke_run(d)
        r.check("smoke: differing user messages fail item 5", code == 1 and "item 5: FAIL" in text,
                text)
        r.check("smoke: the full-run folders are never read",
                all(BF.SMOKE_TAG in ln for ln in text.splitlines() if "slurm_vllm_" in ln))
    finally:
        shutil.rmtree(tmp)


def main():
    r = TestResults("control_prompt_fix")
    test_fixture_is_builder_output(r)
    test_planted_answers(r)
    code, err, res, _ = run_fixture(FIXTURE)
    r.check("base fixture runs", code == 0, err)
    if res is not None:
        test_base(r, res)
    test_refusals(r)
    test_tripwires(r)
    test_live_gate(r)
    test_package_hash(r)
    test_constants(r)
    test_labels(r)
    test_smoke(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
