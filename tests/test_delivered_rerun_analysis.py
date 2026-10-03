"""Freeze gate 4 for the delivered-rerun analysis (tools/delivered_rerun/).

Run standalone: `python3 tests/test_delivered_rerun_analysis.py`
Or via the shell wrapper: `bash tests/verify.sh`

The synthetic fixture (tests/fixtures/delivered_rerun/, built by its
build_fixture.py) plants every trap listed in the freeze protocol and the
prereg. Every expected number below is hand-computed from the plants; the
derivation is in the comment next to it. Domains are dA and dB (k = 2), so a
domain-cluster bootstrap has three outcomes: (A,A), (B,B) with probability
1/4 each and a mixed draw with probability 1/2 whose value (equal cluster
sizes) is the overall mean. With 10,000 draws the 2.5%/5% quantiles fall in
the low atom and the 95%/97.5% quantiles in the high atom, so every interval
equals [min(mean_A, mean_B), max(mean_A, mean_B)] exactly.

No row of the delivered rerun is read anywhere in this file. The canonical
corpus (results/sweep5v2-live) is read only by the parity dry run and the
band-constant check, and both skip cleanly when it is not on disk.
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402

import tools.e2e_regrade as e2e_regrade  # noqa: E402
from tools.delivered_rerun import analysis as A  # noqa: E402
from tools.delivered_rerun import constants as C  # noqa: E402
from tools.delivered_rerun import e4 as E4  # noqa: E402
from tools.delivered_rerun import grade as G  # noqa: E402
from tools.delivered_rerun import run as RUN  # noqa: E402
from tools.delivered_rerun import schema as S  # noqa: E402
from tools.delivered_rerun import stats as ST  # noqa: E402
from tools.delivered_rerun import tripwires as T  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "delivered_rerun"
GM, Q9, Q35 = "gemma4_26b-a4b", "Qwen3_5_9B", "qwen3_6_35b"
PREFIX = "<|channel>thought\n<channel|>"
EPS = 1e-9


def close(a, b):
    return a is not None and b is not None and abs(a - b) < EPS


# ------------------------------------------------------------------ helpers
def run_main(args: list[str]) -> tuple[int, str]:
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = RUN.main(args)
    return code, err.getvalue()


def run_fixture(root: Path, extra: list[str] | None = None) -> tuple[int, str, dict | None]:
    out = Path(tempfile.mkdtemp(prefix="dr_out_"))
    code, err = run_main(["--fixture", str(root), "--out", str(out)] + (extra or []))
    res = None
    if code == 0:
        res = json.loads((out / "delivered_rerun_readout.json").read_text())
    shutil.rmtree(out)
    return code, err, res


def copy_fixture() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="dr_fx_"))
    dst = tmp / "fx"
    shutil.copytree(FIXTURE, dst)
    return dst


def cell_file(root: Path, layer: str, name: str) -> Path:
    return root / layer / name / "trials.jsonl"


def edit_rows(path: Path, fn) -> None:
    """Apply fn(list_of_records) -> list_of_records to a trials.jsonl."""
    recs = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    recs = fn(recs)
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))


def match(rec, task, dom, prob, label, v):
    r = rec["result"]
    return (r["task"], r["domain_name"], r["problem_name"], r["plan_label"],
            r["prompt_variant"]) == (task, dom, prob, label, v)


RA = {m: f"slurm_vllm_{m}_off_tools_all_minimal_delivered-rerun" for m in (GM, Q9, Q35)}
RB = "slurm_vllm_gemma4_26b-a4b_off_tools_all_neutral_delivered-rerun-neutral"
CT = {m: f"slurm_vllm_{m}_off_tools_all_minimal" for m in (GM, Q9, Q35)}


def expect_refusal(r: TestResults, label: str, mutate, needle: str) -> None:
    root = copy_fixture()
    try:
        mutate(root)
        code, err, _ = run_fixture(root)
        r.check(f"{label}: exit non-zero", code == 2, f"code={code} err={err!r}")
        r.check(f"{label}: message", needle in err, f"want {needle!r} in {err!r}")
    finally:
        shutil.rmtree(root.parent)


def by(res, section, **kw):
    hit = [c for c in res[section] if all(c[k] == v for k, v in kw.items())]
    assert len(hit) == 1, (section, kw, len(hit))
    return hit[0]


def pcell(res, model, task, arm):
    hit = [c for c in res["parity"]["cells"]
           if (c["model"], c["task"], c["arm"]) == (model, task, arm)]
    assert len(hit) == 1
    return hit[0]


# ------------------------------------------------------------------ gate 4: fixture
def test_fixture_is_builder_output(r):
    tmp = Path(tempfile.mkdtemp(prefix="dr_build_"))
    try:
        subprocess.run([sys.executable, str(FIXTURE / "build_fixture.py"), str(tmp)],
                       check=True)
        committed = sorted(p.relative_to(FIXTURE) for p in FIXTURE.rglob("*")
                           if p.is_file() and p.name != "build_fixture.py"
                           and "__pycache__" not in p.parts)
        built = sorted(p.relative_to(tmp) for p in tmp.rglob("*") if p.is_file())
        r.check_eq("fixture file list", committed, built)
        for rel in built:
            r.check(f"fixture bytes {rel}", (FIXTURE / rel).read_bytes() == (tmp / rel).read_bytes())
    finally:
        shutil.rmtree(tmp)


def test_base_parity(r, res):
    p = res["parity"]
    # Qwen: 20 cells, 9B validate_domain plain VOID, 35B solve steered not met -> 18.
    r.check_eq("job", p["job"], A.JOB_HOLDS)
    r.check_eq("qwen met", p["qwen_met"], 18)
    r.check_eq("gross", p["gross_cells"], [])
    r.check_eq("gemma first", p["gemma_evaluated_first"], True)
    r.check_eq("gemma failed", p["gemma_failed"], True)
    # F = max |Δ̂| over Gemma cells = Gemma vplan plain 1/12.
    r.check("noise floor F = 100/12", close(p["noise_floor_F"], 100 / 12), p["noise_floor_F"])
    r.check_eq("void cells", p["void_cells"], ["Qwen3_5_9B/validate_domain/plain"])
    r.check_eq("gemma cells listed first", [c["model"] for c in p["cells"][:10]], [GM] * 10)

    # Gemma vplan plain: one row (dA,v1,v11) tool-verified in rerun only.
    c = pcell(res, GM, "validate_plan", "plain")
    r.check("G vplan Δ̂ = 100/12", close(c["delta"], 100 / 12), c["delta"])
    # domain means: dA 1/6, dB 0 -> 90% CI [0, 100/6]
    r.check("G vplan CI90", close(c["ci90"]["lo"], 0) and close(c["ci90"]["hi"], 100 / 6), c["ci90"])
    r.check_eq("G vplan verdict", c["verdict"], A.NOT_MET)
    r.check_eq("G vplan consequence", c["consequence"], A.CONSEQ_CELL_FAIL)
    r.check("G vplan TV", close(c["tv_rerun_pct"], 100 / 12) and close(c["tv_canonical_pct"], 0), c)
    # Newcombe 90%, unpaired 1/12 vs 0/12, Wilson computed independently here.
    z = 1.6448536269514722

    def wil(k, n):
        p_ = k / n
        d = 1 + z * z / n
        cen = (p_ + z * z / (2 * n)) / d
        h = z * math.sqrt(p_ * (1 - p_) / n + z * z / (4 * n * n)) / d
        return max(0.0, cen - h), min(1.0, cen + h)
    l1, u1 = wil(1, 12)
    l2, u2 = wil(0, 12)
    lo = 1 / 12 - math.sqrt((1 / 12 - l1) ** 2 + (u2 - 0) ** 2)
    hi = 1 / 12 + math.sqrt((u1 - 1 / 12) ** 2 + (0 - l2) ** 2)
    nc = c["newcombe90"]
    r.check("G vplan Newcombe", close(nc[0], 100 / 12) and abs(nc[1] - 100 * lo) < 1e-9
            and abs(nc[2] - 100 * hi) < 1e-9, (nc, 100 * lo, 100 * hi))

    # 35B solve steered: +1 at dA, -1 at dB -> Δ̂ 0, CI90 [-100/3, +100/3].
    c = pcell(res, Q35, "solve", "steered")
    r.check("35B solve Δ̂ = 0", close(c["delta"], 0), c["delta"])
    r.check("35B solve CI90", close(c["ci90"]["lo"], -100 / 3) and close(c["ci90"]["hi"], 100 / 3),
            c["ci90"])
    r.check_eq("35B solve verdict", c["verdict"], A.NOT_MET)
    r.check_eq("35B solve gross", c["gross"], False)
    r.check("35B solve TV 5/6 both", close(c["tv_rerun_pct"], 500 / 6)
            and close(c["tv_canonical_pct"], 500 / 6), c)

    # 9B vdom plain: (dA,p01,v11) vs canonical (dA,p02,v11): 1 + 1 unpaired of 7.
    c = pcell(res, Q9, "validate_domain", "plain")
    r.check_eq("9B vdom unpaired", (c["unpaired_rerun"], c["unpaired_canonical"], c["n_paired"]),
               (1, 1, 5))
    r.check("9B vdom unpaired frac 2/7", close(c["unpaired_frac"], 2 / 7), c["unpaired_frac"])
    r.check_eq("9B vdom VOID", (c["verdict"], c["ci90"]), (A.VOID, None))

    # clipped before a tool call: only 35B simulate plain (dA,v11), 2 clipped turns.
    clipped = {(c["model"], c["task"], c["arm"]): c["clipped_before_tool_call"]
               for c in p["cells"] if c["clipped_before_tool_call"]}
    r.check_eq("clipped-before-tool counts", clipped, {(Q35, "simulate", "plain"): 1})

    others = [c for c in p["cells"] if (c["model"], c["task"], c["arm"]) not in {
        (GM, "validate_plan", "plain"), (Q35, "solve", "steered"), (Q9, "validate_domain", "plain")}]
    r.check_eq("27 other cells", len(others), 27)
    r.check("others Δ̂ 0, CI [0,0], met, exact consequence",
            all(close(c["delta"], 0) and close(c["ci90"]["lo"], 0) and close(c["ci90"]["hi"], 0)
                and c["verdict"] == A.MET and c["consequence"] == A.CONSEQ_EXACT for c in others))


# Delivered successes per cell (of n), from the plants:
E1_K = {
    (GM, "solve", "plain"): (5, 6),        # dB v13 clipped final turn
    (GM, "solve", "steered"): (6, 6),      # prefix + backticked list still right
    (GM, "validate_plan", "plain"): (1, 12),
    (GM, "simulate", "plain"): (5, 6),     # dB v12 no-room
    (GM, "simulate", "steered"): (5, 6),   # dA v14 prose
    (Q9, "solve", "plain"): (5, 6),        # dB v13 abridged
    (Q9, "validate_problem", "plain"): (5, 6),   # dA v11 empty
    (Q9, "simulate", "plain"): (5, 6),     # dB v12 numeric omitted
    (Q9, "simulate", "steered"): (5, 6),   # dA v15 step skipped
    (Q35, "solve", "steered"): (3, 6),     # dB v14 wrong, dA v15 prose, dB v15 summary
    (Q35, "validate_domain", "plain"): (5, 6),   # dA v12 no verdict
    (Q35, "validate_problem", "steered"): (0, 6),  # zero-success arm
    (Q35, "validate_plan", "steered"): (11, 12),   # dB b1 v16 wrong verdict
    (Q35, "simulate", "plain"): (5, 6),    # dB v13 tool-input error
    (Q35, "simulate", "steered"): (5, 6),  # dB v16 extra fact
}


def test_base_e1(r, res):
    for m, t, a in A.CELLS:
        n = 12 if t == "validate_plan" else 6
        k, n_ = E1_K.get((m, t, a), (n, n))
        c = by(res, "e1", model=m, task=t, arm=a)
        r.check(f"E1 {m}/{t}/{a} = {k}/{n_}",
                c["n"] == n_ and c["delivered_k"] == k and close(c["delivered_pct"], 100 * k / n_),
                (c["delivered_k"], c["n"]))
    # Intervals: [min, max] of the two domain means.
    for (m, t, a), (lo, hi) in {
        (GM, "validate_plan", "plain"): (0, 100 / 6),        # dA 1/6, dB 0
        (Q35, "solve", "steered"): (100 / 3, 200 / 3),       # dA 2/3, dB 1/3
        (Q35, "validate_plan", "steered"): (500 / 6, 100),   # dA 1, dB 5/6
        (GM, "simulate", "plain"): (200 / 3, 100),           # dA 1, dB 2/3
        (Q35, "validate_problem", "steered"): (0, 0),
        (GM, "validate_domain", "plain"): (100, 100),
    }.items():
        ci = by(res, "e1", model=m, task=t, arm=a)["ci95"]
        r.check(f"E1 CI {m}/{t}/{a}", close(ci["lo"], lo) and close(ci["hi"], hi), ci)
    c = by(res, "e1", model=GM, task="simulate", arm="plain")
    r.check_eq("no-room counted as failure", (c["no_room_n"], c["reasons"]["no_room"]), (1, 1))
    r.check("no-room share 1/6", close(c["no_room_pct"], 100 / 6))
    r.check_eq("no-room only there", sum(c["no_room_n"] for c in res["e1"]), 1)
    r.check_eq("prefix stripped G solve plain",
               by(res, "e1", model=GM, task="solve", arm="plain")["prefix_n"], 1)
    r.check_eq("prefix stripped G solve steered",
               by(res, "e1", model=GM, task="solve", arm="steered")["reasons"],
               {"plan_valid": 6})
    r.check_eq("zero-success arm invocation",
               by(res, "e1", model=Q35, task="validate_problem", arm="steered")["invocation_pct"], 0.0)
    r.check_eq("storage cuts all zero",
               [c["storage_cuts"] for c in res["corpus"] if c["layer"] == "rerun"], [0, 0, 0, 0])


# (Δ̂, CI lo, CI hi, sign-flip p) per model x task. Δ̂ = sum(d) / n.
E2_EXP = {
    (GM, "solve"): (-100 / 6, -100 / 3, 0, 1.0),        # -1 at dB: sums (0,-1)
    (GM, "validate_domain"): (0, 0, 0, 1.0),
    (GM, "validate_problem"): (0, 0, 0, 1.0),
    (GM, "validate_plan"): (-1100 / 12, -100, -500 / 6, 0.5),  # sums (-5,-6): P(|±5±6|>=11)=1/2
    (Q9, "solve"): (-100 / 6, -100 / 3, 0, 1.0),
    (Q9, "validate_domain"): (0, 0, 0, 1.0),
    (Q9, "validate_problem"): (-100 / 6, -100 / 3, 0, 1.0),
    (Q9, "validate_plan"): (0, 0, 0, 1.0),
    (Q35, "solve"): (0, 0, 0, 1.0),
    (Q35, "validate_domain"): (-100 / 6, -100 / 3, 0, 1.0),
    (Q35, "validate_problem"): (0, 0, 0, 1.0),
    (Q35, "validate_plan"): (100 / 3, 100 / 3, 100 / 3, 0.5),  # NT wrong on 4 v11 rows: sums (2,2)
}
E3_EXP = {
    (GM, "solve"): (100 / 6, 0, 100 / 3, 1.0),
    (GM, "validate_domain"): (0, 0, 0, 1.0),
    (GM, "validate_problem"): (0, 0, 0, 1.0),
    (GM, "validate_plan"): (1100 / 12, 500 / 6, 100, 0.5),
    (GM, "simulate"): (0, -100 / 3, 100 / 3, 1.0),        # -1 at dA, +1 at dB
    (Q9, "solve"): (100 / 6, 0, 100 / 3, 1.0),
    (Q9, "validate_domain"): (0, 0, 0, 1.0),
    (Q9, "validate_problem"): (100 / 6, 0, 100 / 3, 1.0),
    (Q9, "validate_plan"): (0, 0, 0, 1.0),
    (Q9, "simulate"): (0, -100 / 3, 100 / 3, 1.0),
    (Q35, "solve"): (-50, -200 / 3, -100 / 3, 0.5),       # sums (-1,-2): P(|±1±2|>=3)=1/2
    (Q35, "validate_domain"): (100 / 6, 0, 100 / 3, 1.0),
    (Q35, "validate_problem"): (-100, -100, -100, 0.5),   # sums (-3,-3)
    (Q35, "validate_plan"): (-100 / 12, -100 / 6, 0, 1.0),
    (Q35, "simulate"): (0, 0, 0, 1.0),                    # plain dB v13 and steered dB v16 both wrong
}


def test_base_e2_e3(r, res):
    for (m, t), (d, lo, hi, p) in E2_EXP.items():
        c = by(res, "e2", model=m, task=t)
        r.check(f"E2 {m}/{t}", c["status"] == "computed" and close(c["delta"], d)
                and close(c["ci95"]["lo"], lo) and close(c["ci95"]["hi"], hi)
                and close(c["p"], p), (c["delta"], c["ci95"], c["p"]))
    for m in (GM, Q9, Q35):
        c = by(res, "e2", model=m, task="simulate")
        r.check(f"E2 {m}/simulate BLOCKED", c["status"] == A.E2_BLOCKED and c["delta"] is None
                and c["p"] == 1.0, c)
    r.check_eq("E2 family size", len(res["e2"]), 15)
    # Holm: smallest p 0.5 x 15 > 1 -> every adjusted p is 1.
    r.check("E2 Holm all 1", all(c["p_holm"] == 1.0 for c in res["e2"]))
    for (m, t), (d, lo, hi, p) in E3_EXP.items():
        c = by(res, "e3", model=m, task=t)
        r.check(f"E3 {m}/{t}", close(c["delta"], d) and close(c["ci95"]["lo"], lo)
                and close(c["ci95"]["hi"], hi) and close(c["p"], p),
                (c["delta"], c["ci95"], c["p"]))
    r.check("E3 Holm all 1", all(c["p_holm"] == 1.0 for c in res["e3"]))
    r.check_eq("E2 caveat present", res["e2_caveat"], A.E2_CAVEAT)


E4_EXP = {
    (GM, "solve", "plain"): (6, {E4.REFUSED_OR_CLIPPED_FINAL: 1}),
    (GM, "validate_plan", "plain"): (1, {}),
    (GM, "simulate", "plain"): (6, {E4.REFUSED_OR_CLIPPED_FINAL: 1}),
    (GM, "simulate", "steered"): (6, {E4.NEEDS_READING: 1}),
    (Q9, "solve", "plain"): (6, {E4.ABRIDGED: 1}),
    (Q9, "validate_problem", "plain"): (6, {E4.NO_FINAL_ANSWER: 1}),
    (Q9, "simulate", "plain"): (6, {E4.NUMERIC_OMITTED: 1}),
    (Q9, "simulate", "steered"): (6, {E4.ABRIDGED: 1}),
    (Q35, "solve", "steered"): (5, {E4.WRONG_WRAPPER: 1, E4.SUMMARY_ONLY: 1}),
    (Q35, "validate_domain", "plain"): (6, {E4.NEEDS_READING: 1}),
    (Q35, "validate_problem", "steered"): (0, {}),
    (Q35, "validate_plan", "steered"): (12, {E4.WRONG_FACTS: 1}),
    (Q35, "simulate", "plain"): (6, {E4.TOOL_INPUT_ERROR: 1}),
    (Q35, "simulate", "steered"): (6, {E4.WRONG_FACTS: 1}),
}


def test_base_e4(r, res):
    for m, t, a in A.CELLS:
        n_default = 12 if t == "validate_plan" else 6
        n_tc, cats = E4_EXP.get((m, t, a), (n_default, {}))
        g = by(res, "e4", model=m, task=t, arm=a)
        got = {k: v for k, v in g["categories"].items() if v}
        gap = sum(cats.values())
        r.check(f"E4 {m}/{t}/{a}", g["n_tool_correct"] == n_tc and g["n_gap"] == gap
                and got == cats, (g["n_tool_correct"], g["n_gap"], got))
        if n_tc:
            r.check(f"E4 share {m}/{t}/{a}", close(g["gap_pct"], 100 * gap / n_tc), g["gap_pct"])
        else:
            r.check_eq(f"E4 share undefined {m}/{t}/{a}", g["gap_pct"], None)
    seen = {c for g in res["e4"] for c, v in g["categories"].items() if v}
    r.check_eq("every E4 category is exercised", seen, set(E4.CATS))


def test_base_readings(r, res):
    R = res["readings"]
    r.check_eq("R1", R["R1"]["label"], A.R1_HARM)                  # CI [-100, -83.3] < -5
    r.check_eq("R2", R["R2"]["label"], A.R2_YES)                   # CI [83.3, 100] > +5
    r.check_eq("R3", R["R3"]["label"], A.R3_STAYS)                 # R1 harm
    r.check_eq("R3 gains", R["R3"]["models_with_e3_gain_above_5"], [GM])
    # R4: Gemma 11/11 (clipped dB v13 excluded as cut), 9B 11/12, 35B 9/11 (dB v14 not tool-verified).
    per = R["R4"]["per_model"]
    r.check_eq("R4 counts", {m: (v["delivered_k"], v["n"]) for m, v in per.items()},
               {GM: (11, 11), Q9: (11, 12), Q35: (9, 11)})
    r.check_eq("R4 label", R["R4"]["label"], A.R4_NOT)
    # R5: minimal-plain invokes only (dA,v1,v11); neutral-plain never -> Δ̂ -1/12,
    # domain means dA -1/6, dB 0 -> 90% CI [-100/6, 0]; est < -5 -> "doing work".
    pl = R["R5"]["neutral_minus_minimal_plain"]
    r.check("R5 plain Δ̂", close(pl["est"], -100 / 12) and close(pl["lo"], -100 / 6)
            and close(pl["hi"], 0), pl)
    r.check_eq("R5 label", R["R5"]["label"], A.R5_WORK)
    st = R["R5"]["neutral_minus_minimal_steered"]
    r.check("R5 steered Δ̂ 0 [0,0]", close(st["est"], 0) and close(st["lo"], 0) and close(st["hi"], 0))
    r.check_eq("R5 steering label", R["R5"]["steering_label"], A.R5_STEER_SUFFICIENT)
    cells = R["R5"]["cells"]
    r.check_eq("R5 2x2", {k: (round(v["invocation_pct"], 6), round(v["delivered_pct"], 6), v["n"])
                          for k, v in cells.items()},
               {"minimal-plain": (round(100 / 12, 6), round(100 / 12, 6), 12),
                "minimal-steered": (100.0, 100.0, 12),
                "neutral-plain": (0.0, 100.0, 12),
                "neutral-steered": (100.0, 100.0, 12)})


# ------------------------------------------------------------------ refusals
def _first(recs, pred):
    for rec in recs:
        if pred(rec):
            return rec
    raise AssertionError("no matching record")


def test_refusals(r):
    def dup(root):
        edit_rows(cell_file(root, "rerun", RA[Q9]), lambda recs: recs + [recs[0]])
    expect_refusal(r, "duplicate key", dup, "duplicate trial key")

    def missing(root):
        def f(recs):
            del recs[3]["result"]["response_truncated_by_storage"]
            return recs
        edit_rows(cell_file(root, "rerun", RA[GM]), f)
    expect_refusal(r, "row missing a new field", missing,
                   "missing key(s) ['response_truncated_by_storage']")

    def cut(root):
        def f(recs):
            recs[5]["result"]["response_truncated_by_storage"] = True
            return recs
        edit_rows(cell_file(root, "rerun", RA[Q35]), f)
    expect_refusal(r, "storage-cut row", cut, "RefusedRow")

    def minimal_in_neutral(root):
        def f(recs):
            recs[0]["result"]["prompt_style"] = "minimal"
            recs[0]["key"][9] = "minimal"
            return recs
        edit_rows(cell_file(root, "rerun", RB), f)
    expect_refusal(r, "minimal row in neutral cell", minimal_in_neutral,
                   "prompt_style 'minimal' in a 'neutral' cell")

    def enum(root):
        def f(recs):
            recs[1]["result"]["failure_reason"] = "mystery"
            recs[1]["result"]["success"] = False
            return recs
        edit_rows(cell_file(root, "rerun", RA[GM]), f)
    expect_refusal(r, "unknown enum", enum, "unknown failure_reason 'mystery'")

    def wrong_layer(root):
        def f(recs):
            recs[2]["result"]["ctx_no_room_turns"] = 1
            return recs
        edit_rows(cell_file(root, "rerun", RA[GM]), f)
    expect_refusal(r, "ctx field at the top level", wrong_layer, "wrong layer")

    def canon_ctx(root):
        def f(recs):
            recs[2]["result"]["tokens"]["ctx_clipped_turns"] = 1
            return recs
        edit_rows(cell_file(root, "canonical", CT[Q9]), f)
    expect_refusal(r, "canonical row with a ctx field", canon_ctx, "wrong corpus layer")

    def canon_new_field(root):
        def f(recs):
            recs[2]["result"]["response_truncated_by_storage"] = False
            return recs
        edit_rows(cell_file(root, "canonical", CT[Q9]), f)
    expect_refusal(r, "canonical row with a rerun-only field", canon_new_field,
                   "unexpected key(s) ['response_truncated_by_storage']")

    def short(root):
        edit_rows(cell_file(root, "rerun", RA[Q35]), lambda recs: recs[:-1])
    expect_refusal(r, "short cell", short, "IncompleteCell")

    def exception_void(root):
        def f(recs):
            res = recs[7]["result"]
            res.update(success=False, failure_reason="exception", error="boom")
            return recs
        edit_rows(cell_file(root, "rerun", RA[Q9]), f)
    expect_refusal(r, "exception rows > 1% -> VOID", exception_void, "VOID (§7)")

    def noroom_text(root):
        def f(recs):
            rec = _first(recs, lambda x: match(x, "simulate", "dB", "p01", "", 12))
            rec["result"]["response"] = "partial"
            return recs
        edit_rows(cell_file(root, "rerun", RA[GM]), f)
    expect_refusal(r, "no-room row with text", noroom_text, "no-room row is not an empty length-stop")

    def clip_over(root):
        def f(recs):
            rec = _first(recs, lambda x: match(x, "solve", "dB", "p01", "", 13))
            rec["result"]["tokens"]["ctx_clip_last_turn_prompt_tokens"] = 15885
            return recs
        edit_rows(cell_file(root, "rerun", RA[GM]), f)
    expect_refusal(r, "clip beyond the window", clip_over, "exceeds 16384")

    def tri_state(root):
        def f(recs):
            recs[4]["result"]["success"] = "indeterminate"
            return recs
        edit_rows(cell_file(root, "rerun", RA[Q35]), f)
    expect_refusal(r, "non-bool grade field", tri_state, "success must be a bool")

    def key_mismatch(root):
        def f(recs):
            recs[4]["key"][7] = "on"
            return recs
        edit_rows(cell_file(root, "rerun", RA[Q35]), f)
    expect_refusal(r, "key disagrees with result", key_mismatch, "disagrees with its result")

    def wrong_model(root):
        def f(recs):
            recs[0]["result"]["model"] = "Qwen/Qwen3.5-9B"
            recs[0]["key"][0] = "Qwen/Qwen3.5-9B"
            return recs
        edit_rows(cell_file(root, "rerun", RA[GM]), f)
    expect_refusal(r, "row of another model", wrong_model, "in cell of gemma4_26b-a4b")

    def no_marker(root):
        (root / "rerun" / RUN.FIXTURE_MARKER).unlink()
    expect_refusal(r, "fixture marker missing", no_marker, "SYNTHETIC_FIXTURE")

    def missing_verdict(root):
        (root / "plan_verdicts.json").write_text("[]\n")
    expect_refusal(r, "no validator verdict", missing_verdict, "no validator verdict")

    # torn line: counted, not fatal; completeness still proves every key.
    root = copy_fixture()
    try:
        with cell_file(root, "rerun", RA[Q9]).open("a") as fh:
            fh.write('{"key": ["Qwen/Qwen3.5-9B", "solve"\n')
        code, err, res = run_fixture(root)
        r.check_eq("torn line exit", code, 0)
        if res:
            r.check_eq("torn line counted",
                       [c["torn_lines"] for c in res["corpus"] if c["cell"] == RA[Q9]], [1])
    finally:
        shutil.rmtree(root.parent)

    # smoke cells are never read
    spec = S.spec_rerun_a(C.REGISTERED, GM)
    smoke = S.CellSpec(**{**spec.__dict__, "name": spec.name + "-smoke"})
    try:
        S.load_cell(FIXTURE / "rerun", smoke)
        r.check("smoke refused", False, "no error")
    except S.SchemaError as e:
        r.check("smoke refused", "smoke" in str(e), str(e))


def test_live_mode_guard(r):
    out = tempfile.mkdtemp(prefix="dr_live_")
    try:
        code, err = run_main(["--rerun-root", "/nonexistent", "--canonical-root", "/nonexistent",
                              "--out", out])
        r.check("live without freeze hash refused", code == 2 and "refusing to run" in err, err)
        code, err = run_main(["--rerun-root", "/nonexistent", "--canonical-root", "/nonexistent",
                              "--out", out, "--i-have-frozen", "0" * 64])
        r.check("live with a wrong hash refused", code == 2 and "refusing to run" in err, err)
        r.check_eq("nothing written", list(Path(out).iterdir()), [])
    finally:
        shutil.rmtree(out)
    h = RUN.package_sha256()
    r.check("package hash is a stable sha256", len(h) == 64 and h == RUN.package_sha256())


# ------------------------------------------------------------------ verdict paths
def test_job_level_failure(r):
    root = copy_fixture()
    try:
        def f(recs):
            rec = _first(recs, lambda x: match(x, "validate_problem", "dA", "p01", "", 12))
            rec["result"].update(success=False, tool_selected=False, tool_calls=[],
                                 failure_reason="tool_not_selected")
            return recs
        edit_rows(cell_file(root, "canonical", CT[Q9]), f)
        code, err, res = run_fixture(root)
        r.check_eq("job-fail run exit", code, 0)
        p = res["parity"]
        # 9B vprob plain: +1 at dA -> Δ̂ 100/6 > 10 -> gross; 17 Qwen cells met.
        r.check_eq("job fails", p["job"], A.JOB_FAILS)
        r.check_eq("qwen met 17", p["qwen_met"], 17)
        r.check_eq("gross cell", p["gross_cells"], ["Qwen3_5_9B/validate_problem/plain"])
        r.check("every consequence is separate-apparatus replication",
                all(c["consequence"] == A.CONSEQ_JOB_FAIL for c in p["cells"]))
    finally:
        shutil.rmtree(root.parent)


def _flip_all(recs):
    for rec in recs:
        res = rec["result"]
        if res["success"]:
            res.update(success=False, tool_selected=False, tool_calls=[],
                       failure_reason="tool_not_selected")
        else:
            res.update(success=True, tool_selected=True, failure_reason="ok",
                       tool_calls=[{"name": "validate_plan", "arguments": {}, "result": "{}"}])
    return recs


def test_tripwires(r):
    # T4: a narrow band for Gemma vplan plain (canonical 12/12 delivered) -> [80, 100].
    root = copy_fixture()
    try:
        d = json.loads((root / "design.json").read_text())
        d["canonical_delivered_counts"][f"{GM}|validate_plan|plain"] = [12, 12, 0]
        (root / "design.json").write_text(json.dumps(d))
        code, err, _ = run_fixture(root)
        r.check("T4 halts", code == 2 and "T4_rate_outside_band" in err
                and "delivered 8.3 outside [80.0, 100.0]" in err, err)
        code, err, res = run_fixture(root, ["--audited-tripwires", "T4_rate_outside_band"])
        r.check("T4 audited run proceeds", code == 0 and "T4_rate_outside_band"
                in res["audited_tripwires"], err)
    finally:
        shutil.rmtree(root.parent)
    # T1: every canonical tool-verified grade flipped -> no cell meets the criterion.
    root = copy_fixture()
    try:
        for m in (GM, Q9, Q35):
            edit_rows(cell_file(root, "canonical", CT[m]), _flip_all)
        code, err, _ = run_fixture(root)
        r.check("T1 halts", code == 2 and "T1_parity_fails_everywhere" in err, err)
    finally:
        shutil.rmtree(root.parent)
    # T3 / T5 on the analysis objects of the base fixture.
    design = RUN.fixture_design(FIXTURE)
    cells = RUN.load_all(design, FIXTURE / "rerun", FIXTURE / "canonical")
    gt = json.loads((FIXTURE / "gt_cache.json").read_text())
    table = RUN.fixture_verdicts(FIXTURE)
    par = A.parity(cells["rerun_a"], cells["canon_tools"], 2)
    rows = [x for lc in cells["rerun_a"].values() for x in lc.rows]
    grades = {(x.cell, x.trial_key): G.grade(x, gt, table) for x in rows}
    e1 = [A.rate_cell(list(cells["rerun_a"][m].rows), grades, m, t, a, "minimal", 2)
          for m, t, a in A.CELLS]
    gaps = [A.e4_cell(list(cells["rerun_a"][m].rows), grades, gt, m, t, a) for m, t, a in A.CELLS]
    r.check_eq("base: no tripwire", T.check(design, par, e1, gaps, cells["rerun_a"],
                                             cells["canon_tools"]), {})
    for c in e1:
        c.invocation_pct = 50.0
    fired = T.check(design, par, e1, gaps, cells["rerun_a"], cells["canon_tools"])
    r.check_eq("T3 constant column", list(fired), ["T3_constant_invocation"])
    for c in e1:
        c.invocation_pct = 100.0 * (c.n % 7)
    for g in gaps:
        if g.n_gap:
            g.categories = {k: 0 for k in E4.CATS}
            g.categories[E4.NEEDS_READING] = g.n_gap
    fired = T.check(design, par, e1, gaps, cells["rerun_a"], cells["canon_tools"])
    r.check("T5 fallback bucket everywhere", "T5_needs_reading_everywhere" in fired, fired)


def _part_b_set(root, invoked_keys):
    """Rewrite Part B plain rows: invoked (tool right, answer right) iff in invoked_keys."""
    def f(recs):
        for rec in recs:
            res = rec["result"]
            if res["prompt_variant"] not in (11, 12, 13):
                continue
            k = (res["domain_name"], res["plan_label"], res["prompt_variant"])
            if k in invoked_keys:
                t = res["plan_label"].startswith("v")
                res.update(success=True, tool_selected=True, failure_reason="ok",
                           tool_calls=[{"name": "validate_plan", "arguments": {},
                                        "result": json.dumps({"valid": t})}])
        return recs
    edit_rows(cell_file(root, "rerun", RB), f)


def test_r5_paths(r):
    cases = [
        # all 12 invoked: Δ̂ = 11/12 > 5 -> suppresses
        ({(d, l, v) for d in ("dA", "dB") for l in ("v1", "b1") for v in (11, 12, 13)},
         A.R5_SUPPRESS),
        # same single row as minimal: Δ̂ 0, CI [0, 0] -> inert
        ({("dA", "v1", 11)}, A.R5_INERT),
        # dB invoked once (+1 at dB) and the minimal dA row not (-1 at dA):
        # Δ̂ 0 but CI [-100/6, +100/6] -> no registered row
        ({("dB", "v1", 11)}, A.R5_NONE),
    ]
    for keys, want in cases:
        root = copy_fixture()
        try:
            _part_b_set(root, keys)
            code, err, res = run_fixture(root)
            r.check_eq(f"R5 path {want}", (code, res and res["readings"]["R5"]["label"]),
                       (0, want))
        finally:
            shutil.rmtree(root.parent)


def test_r4_attributed(r):
    root = copy_fixture()
    try:
        def f(recs):
            for rec in recs:
                if match(rec, "solve", "dA", "p01", "", 15):
                    rec["result"]["response"] = "(a x)\n(b y)"
                if match(rec, "solve", "dB", "p01", "", 15):
                    rec["result"]["response"] = "(c z)\n(d w)\n(e v)"
            return recs
        edit_rows(cell_file(root, "rerun", RA[Q35]), f)
        code, err, res = run_fixture(root)
        R4 = res["readings"]["R4"]
        # 35B now 11/11; 9B 11/12 = 91.7 >= 90; Gemma 11/11.
        r.check_eq("R4 attributed", (code, R4["label"]), (0, A.R4_ATTRIBUTED))
    finally:
        shutil.rmtree(root.parent)


def test_reading_rules(r):
    def con(model, task, lo, hi):
        b = ST.Boot(est=(lo + hi) / 2, lo=lo, hi=hi, level=0.95, k=20, n=100)
        return A.Contrast(model=model, task=task, name="x", n_pairs=100, unpaired_a=0,
                          unpaired_b=0, a_pct=0, b_pct=0, delta=b.est, ci95=b, p=1.0)
    r.check_eq("R1 harm", A.r1([con(GM, "validate_plan", -30, -5.01)])["label"], A.R1_HARM)
    r.check_eq("R1 harm needs < -5", A.r1([con(GM, "validate_plan", -30, -5.0)])["label"],
               A.R1_UNRESOLVED)
    r.check_eq("R1 no harm (inclusive)", A.r1([con(GM, "validate_plan", -5, 5)])["label"],
               A.R1_NO_HARM)
    r.check_eq("R1 unresolved", A.r1([con(GM, "validate_plan", -8, 2)])["label"], A.R1_UNRESOLVED)
    r.check_eq("R2 yes", A.r2([con(GM, "validate_plan", 5.01, 9)])["label"], A.R2_YES)
    r.check_eq("R2 no", A.r2([con(GM, "validate_plan", -4, 4)])["label"], A.R2_NO)
    r.check_eq("R2 unresolved", A.r2([con(GM, "validate_plan", 1, 9)])["label"], A.R2_UNRESOLVED)
    e3s = [con(GM, "validate_plan", 6, 9), con(Q9, "validate_plan", 7, 12),
           con(Q35, "validate_plan", -1, 3)]
    r.check_eq("R3 two models", A.r3(A.R1_NO_HARM, e3s)["label"], A.R3_STAYS)
    r.check_eq("R3 one model", A.r3(A.R1_UNRESOLVED, e3s[:1] + [
        con(Q9, "validate_plan", 4, 12), e3s[2]])["label"], A.R3_CHANGES)
    r.check_eq("R3 via R1", A.r3(A.R1_HARM, [con(m, "validate_plan", 0, 1)
                                             for m in (GM, Q9, Q35)])["label"], A.R3_STAYS)


# ------------------------------------------------------------------ units
def test_grader_prefix(r):
    resp = PREFIX + "1. `(a x)` - pick\n2. `(b y)` - put"
    r.check_eq("e2e_regrade tolerant path loses the first action",
               e2e_regrade.extract_plan_lines_tolerant(resp)[0], ["(b y)"])
    r.check_eq("this grader keeps it", G.solve_plan(resp), (("(a x)", "(b y)"), "tolerant_lines"))
    r.check_eq("strict path", G.solve_plan(PREFIX + "(a x)\n(b y)"),
               (("(a x)", "(b y)"), "strict_lines"))
    doubled = PREFIX + PREFIX + "(a x)"
    r.check_eq("doubled marker stripped once only", G.solve_plan(doubled)[0], ())
    r.check_eq("verdict behind prefix", G.stated_verdict(PREFIX + "VERDICT: INVALID"), False)


def test_stats_units(r):
    r.check_eq("signflip (5,6)", ST.signflip_exact_p([5, 6]), 0.5)
    r.check_eq("signflip (3)", ST.signflip_exact_p([3]), 1.0)
    r.check_eq("signflip (1,1,1)", ST.signflip_exact_p([1, 1, 1]), 0.25)
    r.check_eq("signflip zeros", ST.signflip_exact_p([0, 0]), 1.0)
    # Holm over 15: p_(1)=0.001 -> 0.015; p_(2)=0.004 -> 0.056; p_(3)=0.003? sorted:
    ps = {i: 1.0 for i in range(15)}
    ps.update({0: 0.001, 1: 0.003, 2: 0.004, 3: 0.04})
    h = ST.holm(ps, 15)
    # sorted 0.001, 0.003, 0.004, 0.04: 15*0.001=.015; 14*.003=.042; 13*.004=.052; 12*.04=.48
    r.check("Holm hand values", close(h[0], 0.015) and close(h[1], 0.042)
            and close(h[2], 0.052) and close(h[3], 0.48) and h[4] == 1.0, h)
    try:
        ST.holm({0: 0.1}, 15)
        r.check("Holm refuses a short family", False)
    except AssertionError:
        r.check("Holm refuses a short family", True)
    try:
        ST.cluster_bootstrap([1, 0], ["a", "b"], 0.9, 20)
        r.check("bootstrap asserts k", False)
    except AssertionError:
        r.check("bootstrap asserts k", True)


def test_clipped_logic(r):
    def row(clipped, last, fr="ok"):
        tok = S.Tokens(prompt=1, completion=1, turns=3, ctx_clipped_turns=clipped,
                       ctx_clip_last_turn_max_tokens=last, ctx_clip_last_turn_prompt_tokens=None,
                       ctx_no_room_turns=0)
        return S.Row(layer="rerun", cell="c", model_tag=GM, task="solve", domain="d",
                     problem="p01", plan_label="", variant=11, with_tools=True,
                     prompt_style="minimal", success=fr == "ok", tool_selected=True,
                     response="x", response_truncated_by_storage=False, tool_calls=(),
                     tokens=tok, error="", failure_reason=fr, truncated=False,
                     done_reason="stop", infra_failure=False)
    r.check_eq("no clip", row(0, None).clipped_before_tool_call, False)
    r.check_eq("only the last turn clipped", row(1, 900).clipped_before_tool_call, False)
    r.check_eq("an earlier turn clipped, last not", row(1, None).clipped_before_tool_call, True)
    r.check_eq("two clipped incl. last", row(2, 900).clipped_before_tool_call, True)
    r.check_eq("last clipped, loop exhausted", row(1, 900, "loop_exhausted").clipped_before_tool_call,
               True)


def test_registered_constants(r):
    try:
        C.assert_registered(C.REGISTERED)
        r.check("registered design passes", True)
    except AssertionError as e:
        r.check("registered design passes", False, str(e))
    try:
        C.assert_registered(RUN.fixture_design(FIXTURE))
        r.check("fixture design is not registered", False)
    except AssertionError:
        r.check("fixture design is not registered", True)
    r.check_eq("loader key set = harness TaskResult", len(S.RERUN_RESULT_KEYS), 24)


# ------------------------------------------------------------------ canonical corpus
def canonical_root() -> Path | None:
    cand = [REPO_ROOT / "results" / "sweep5v2-live"]
    try:
        common = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True, check=True).stdout.strip()
        cand.append((REPO_ROOT / common).resolve().parent / "results" / "sweep5v2-live")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    for c in cand:
        if (c / S.canonical_tools_name(GM) / "trials.jsonl").exists():
            return c
    return None


def test_canonical_dry_run(r):
    """Parity code path on sweep5v2-live against itself: Δ = 0 in every cell."""
    root = canonical_root()
    if root is None:
        print("  SKIP canonical dry run: results/sweep5v2-live not on disk")
        return
    ct = {m: S.load_cell(root, S.spec_canonical_tools(C.REGISTERED, m)) for m in C.PART_A_MODELS}
    p = A.parity(ct, ct, C.REGISTERED.k_domains)
    r.check_eq("dry run: 30 cells", len(p.cells), 30)
    r.check("dry run: Δ = 0, CI [0, 0], unpaired 0 everywhere",
            all(c.delta == 0 and c.ci90.lo == 0 and c.ci90.hi == 0 and c.unpaired_frac == 0
                and c.ci90.k == 20 for c in p.cells))
    r.check_eq("dry run: job", (p.job, p.qwen_met, p.gemma_failed), (A.JOB_HOLDS, 20, False))
    nt = {m: S.load_cell(root, S.spec_canonical_no_tools(C.REGISTERED, m)) for m in C.PART_A_MODELS}
    r.check("dry run: no no-tools answer carries the leaked prefix",
            not any(G.has_prefix(x.response) for lc in nt.values() for x in lc.rows))
    # The band constants equal a recount of the canonical overlay.
    ov_dir = root.parent / "derived" / "e2e_overlay" / "sweep5v2-live"
    if not ov_dir.is_dir():
        print("  SKIP band recount: overlay not on disk")
        return
    counts: dict = {}
    for m in C.PART_A_MODELS:
        with (ov_dir / f"{S.canonical_tools_name(m)}.e2e.jsonl").open() as fh:
            for ln in fh:
                o = json.loads(ln)
                arm = "plain" if o["prompt_variant"] in C.PLAIN else "steered"
                n, ok, cen = counts.get((m, o["task"], arm), (0, 0, 0))
                counts[(m, o["task"], arm)] = (n + 1, ok + (o["e2e_strict"] is True),
                                              cen + (o["e2e_strict"] == "indeterminate"))
    r.check_eq("band constants = overlay recount", counts, C.CANONICAL_DELIVERED_COUNTS)


def main():
    r = TestResults("delivered_rerun_analysis")
    test_fixture_is_builder_output(r)
    code, err, res = run_fixture(FIXTURE)
    r.check("base fixture runs", code == 0, err)
    if res is not None:
        r.check_eq("fixture mode recorded", res["mode"], "fixture")
        test_base_parity(r, res)
        test_base_e1(r, res)
        test_base_e2_e3(r, res)
        test_base_e4(r, res)
        test_base_readings(r, res)
    test_refusals(r)
    test_live_mode_guard(r)
    test_job_level_failure(r)
    test_tripwires(r)
    test_r5_paths(r)
    test_r4_attributed(r)
    test_reading_rules(r)
    test_grader_prefix(r)
    test_stats_units(r)
    test_clipped_logic(r)
    test_registered_constants(r)
    test_canonical_dry_run(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
