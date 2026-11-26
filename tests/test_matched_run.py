"""Freeze gate 4 for the matched-run analysis (tools/reanalysis/matched_run.py).

Run standalone: `python3 tests/test_matched_run.py`
Or: `python3 -m pytest tests/test_matched_run.py`

The synthetic fixture (tests/fixtures/matched_run/, built by its build_fixture.py) has
60 trials per model, task and arm, 3 per domain, over 20 domains d01..d20. d01 to d18 have
one problem on three wordings; d19 and d20 have two problems (d19: p01 v11, p02 v11, p01
v12; d20: p02 v12, p01 v13, p02 v13), so every wording still has 20 rows per task and a
pairing key without the problem would collide. A plant "on v12 everywhere" means the
second of the three trials of every domain. Every expected number below is hand-computed from the plants of
build_fixture.py; the derivation is in the comment next to it.

Bootstrap arithmetic used below (frozen `cluster_bootstrap`: 20 domains drawn with
replacement, ratio estimator; every domain holds 3 trials of an arm, so a draw's value
is (sum of the drawn domains' paired differences) / 60). The draws depend only on the
seed and on k = 20, so these three patterns are the ones the control's tests use:
  * every domain has the same difference d: every draw gives d, so the interval is
    [d, d] and equals the estimate;
  * one domain with sum s, the rest 0: a draw gives s*X/60 with X ~ Bin(20, 1/20).
    P(X = 0) = 0.358, so the 2.5% quantile is 0; P(X >= 3) = 0.0755 and
    P(X >= 4) = 0.0159, so the 97.5% quantile is X = 3: the interval is [0, 3s/60]
    (s = 1: [0, 5.0]; s = 3: [0, 15.0]; s = -3: [-15.0, 0]);
  * four domains with sum +1: X ~ Bin(20, 4/20). P(X = 0) = 0.0115 and
    P(X <= 1) = 0.0692, so the 2.5% quantile is X = 1; P(X >= 8) = 0.0321 and
    P(X >= 9) = 0.0100, so the 97.5% quantile is X = 8: [1/60, 8/60], in points
    [1.667, 13.333]; with sum -1 the interval is mirrored, [-13.333, -1.667].
Sign-flip p (exact, over the 20 domain sums): 20 equal non-zero sums give
2/2^20 = 1.9073e-06; m equal non-zero sums and the rest 0 give 2/2^m (m = 1: 1.0;
m = 4: 0.125); all zero gives 1.0.

No row of any real corpus is read here.
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402

from tools.delivered_rerun import constants as C  # noqa: E402
from tools.delivered_rerun import grade as G  # noqa: E402
from tools.delivered_rerun import run as RUN  # noqa: E402
from tools.delivered_rerun import schema as S  # noqa: E402
from tools.reanalysis import control_prompt_fix as CPF  # noqa: E402
from tools.reanalysis import matched_run as M  # noqa: E402
from tools.reanalysis import rq1_layout_regrade as RG  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "matched_run"


def _load_builder():
    """Both fixture builders are called build_fixture.py; load this one by path."""
    name = "matched_run_build_fixture"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, FIXTURE / "build_fixture.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


BF = _load_builder()
Q9, GM, Q35 = "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"
EPS = 1e-9
P20 = 2 / 2 ** 20                 # 20 equal non-zero domain sums
HOLM6 = 6 * P20                   # Holm, the smallest of six: 6 * p
DATES = "2026-12-01 to 2026-12-02 (fixture)"
REPO_NOTE = "git rev-parse read on the cluster (fixture)"
FROZEN_RERUN_SHA = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"
FROZEN_CONTROL_SHA = "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79"
NDS = "no difference shown"
MET = "criterion met"


def close(a, b):
    return a is not None and b is not None and abs(a - b) < EPS


# ------------------------------------------------------------------ helpers
def run_main(args: list[str]) -> tuple[int, str, str]:
    err, out = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        code = M.main(args)
    return code, err.getvalue(), out.getvalue()


def run_fixture(root: Path, extra: list[str] | None = None, repo_note: bool = True,
                dates: bool = True):
    out = Path(tempfile.mkdtemp(prefix="mr_out_"))
    args = ["--fixture", str(root), "--out", str(out)]
    if dates:
        args += ["--run-dates", DATES]
    if repo_note:
        args += ["--tools-repo-checked-by-hand", REPO_NOTE]
    code, err, _ = run_main(args + (extra or []))
    res = None
    if code == 0:
        res = json.loads((out / "matched_run.json").read_text())
        res["_md"] = (out / "matched_run.md").read_text()
    written = sorted(p.name for p in out.iterdir())
    shutil.rmtree(out)
    return code, err, res, written


def copy_fixture() -> Path:
    dst = Path(tempfile.mkdtemp(prefix="mr_fx_")) / "fx"
    shutil.copytree(FIXTURE, dst)
    return dst


def mdir(root: Path, model: str, fo: str, tag: str | None = None) -> Path:
    return root / "matched" / BF.folder(model, fo, tag or BF.RUN_TAG)


def bdir(root: Path, model: str) -> Path:
    return root / "control" / f"slurm_vllm_{model}_off_no-tools-sysformat_control-promptfix"


def edit_jsonl(path: Path, fn) -> None:
    """Rewrite a JSON-lines file. A half-written line (the fixture plants one) is dropped."""
    recs = []
    for ln in path.read_text().splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            recs.append(json.loads(ln))
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


def set_answer(path: Path, model: str, task: str, dom: str, v: int, kind: str,
               with_tools: bool = False, tool: str = "right"):
    """Replace one row of a trials file with a builder row of another answer kind."""
    def fn(recs):
        i = find(recs, task, dom, v)
        row = BF.make_row(model, task, dom, v, kind, with_tools, tool,
                          recs[i]["result"]["problem_name"])
        recs[i] = {"key": BF.key_of(row), "result": row}
        return recs
    edit_jsonl(path / "trials.jsonl", fn)


def expect_halt(r: TestResults, label: str, mutate, needle: str, extra=None, **kw) -> None:
    root = copy_fixture()
    try:
        mutate(root)
        code, err, _res, written = run_fixture(root, extra, **kw)
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
    tmp = Path(tempfile.mkdtemp(prefix="mr_build_"))
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


# ------------------------------------------------------------------ the grade on the planted answers
def test_planted_answers(r):
    """Each planted answer kind under the three grades: (registered, frozen, second)."""
    plan, wrong, caps, tried = (tuple(BF.PLAN), tuple(BF.WRONG), tuple(BF.CAPS), tuple(BF.TRIED))
    table = {(d, "p01", p): v for d in BF.DOMAINS for p, v in
             ((plan, True), (wrong, False), (caps, False), (tried, False))}
    gt = json.loads((FIXTURE / "gt_cache.json").read_text())
    calls = []
    r.check_eq("caps_json: the frozen reader takes the capitals, there is no block",
               (G.solve_plan(BF.ANSWERS["caps_json"]), RG.block_plan(BF.ANSWERS["caps_json"])),
               ((caps, "json"), None))

    def route(d, p, pl):
        calls.append(pl)
        return table[(d, p, pl)]

    def three(kind, task="solve", with_tools=False, tool="right"):
        verdict = CPF.Verdicts(route)
        row = BF.make_row(Q9, task, "d01", 11, kind, with_tools, tool)
        spec = M.matched_spec(M.SMOKE, Q9, "T" if with_tools else "N", BF.RUN_TAG)
        parsed = S.parse_row({"key": BF.key_of(row), "result": row}, spec, "t")
        pairs = CPF.frozen_grades([parsed], verdict, gt)
        x = M.grade_trials(pairs, verdict, gt)[parsed.trial_key]
        return x.registered, x.frozen, x.second

    r.check_eq("right: every grade", three("right"), (True, True, True))
    # A JSON plan in the last code block: the frozen reader misses it, the block plan is read.
    r.check_eq("json_block: registered right, frozen wrong", three("json_block"),
               (True, False, True))
    # Capitals in a JSON plan in the last block: release 0.1.5 rejects it as written
    # (the route table says False for the capitals); in lower case it is the valid plan.
    calls.clear()
    r.check_eq("caps_block: right only in lower case", three("caps_block"), (True, False, False))
    r.check("caps_block: the validator was sent the lower-case plan", plan in calls, calls)
    r.check_eq("caps_block in a tools row: the same rule in every arm",
               three("caps_block", with_tools=True), (True, False, False))
    # The same with no code block: the plan the frozen reader took, in capitals.
    r.check_eq("caps_json: a frozen-reader plan is lower-cased too", three("caps_json"),
               (True, False, False))
    # Exception rows are wrong under the registered grade whatever their stored answer.
    # A scoring-exception row keeps its answer; the descriptive second reading (the
    # control's frozen behaviour) still reads it.
    r.check_eq("scoring exception with a right plan in a block: registered wrong",
               three("json_block", tool="scoring"), (False, False, True))
    r.check_eq("scoring exception with a right per-line trace: registered wrong",
               three("per_line", "simulate", tool="scoring"), (False, False, True))
    r.check_eq("client exception: wrong under every grade", three("exception"),
               (False, False, False))
    # Right action lines, then a wrong JSON plan in the last block: the block decides.
    r.check_eq("right_to_wrong: the last block decides", three("right_to_wrong"),
               (False, True, False))
    r.check_eq("wrong_lines", three("wrong_lines"), (False, False, False))
    r.check_eq("prose: no plan, no verdict asked", three("prose"), (False, False, False))
    r.check_eq("simulate, one JSON object", three("trace", "simulate"), (True, True, True))
    r.check_eq("simulate, one object per line equal to the key",
               three("per_line", "simulate"), (True, False, True))
    r.check_eq("simulate, one object per line not equal to the key",
               three("per_line_wrong", "simulate"), (False, False, False))
    r.check_eq("simulate, wrong trace", three("trace_wrong", "simulate"), (False, False, False))
    # The registered grade does not repair: prose, then the right trace on one line.
    r.check_eq("simulate, an unread final answer is wrong", three("unread_sim", "simulate"),
               (False, False, False))
    # Pairing key: a steered wording maps to its plain wording.
    r.check_eq("canon v14 -> v11", M.canon(("solve", "d01", "p01", "", 14)),
               ("solve", "d01", "p01", "", 11))
    r.check_eq("canon v16 -> v13", M.canon(("solve", "d01", "p01", "", 16))[4], 13)
    r.check_eq("canon v12 stays", M.canon(("solve", "d01", "p01", "", 12))[4], 12)
    try:
        M.canon(("solve", "d01", "p01", "", 17))
        r.check("canon refuses a wording of no arm", False)
    except M.Halt:
        r.check("canon refuses a wording of no arm", True)


# ------------------------------------------------------------------ the base fixture
# (registered, frozen, second) right of 60, per (model, task, cell).
ALL = (60, 60, 60)
RATES = {
    # A. Qwen3.5-9B solve: N wrong on the second trial of all 20 domains: 40. d05 v12 is
    # a scoring-exception row whose stored answer is a right plan in a block: wrong under
    # the registered and the frozen grade; the descriptive second reading reads it (41).
    # Cell B of the control: 40 under all three.
    (Q9, "solve", "N"): (40, 40, 41), (Q9, "solve", "P"): ALL, (Q9, "solve", "S"): ALL,
    (Q9, "solve", "cell B of the control"): (40, 40, 40),
    (Q9, "solve", "Part A, plain"): ALL, (Q9, "solve", "Part A, steered"): ALL,
    # B. Qwen3.5-9B simulate: N wrong on v11 in d01..d04, S wrong on v14 in d01..d04: 56.
    (Q9, "simulate", "N"): (56, 56, 56), (Q9, "simulate", "P"): ALL,
    (Q9, "simulate", "S"): (56, 56, 56), (Q9, "simulate", "cell B of the control"): ALL,
    (Q9, "simulate", "Part A, plain"): ALL, (Q9, "simulate", "Part A, steered"): ALL,
    # C. Gemma solve: N a JSON plan in a block on v11 (frozen 40, both others 60); P a
    # JSON plan in capitals on v11 (registered 60; frozen and not-lower-cased 40).
    (GM, "solve", "N"): (60, 40, 60), (GM, "solve", "P"): (60, 40, 40), (GM, "solve", "S"): ALL,
    (GM, "solve", "cell B of the control"): (60, 40, 60),
    (GM, "solve", "Part A, plain"): (60, 40, 40), (GM, "solve", "Part A, steered"): ALL,
    # D. Gemma simulate: S wrong on v16 in d01..d04.
    (GM, "simulate", "N"): ALL, (GM, "simulate", "P"): ALL, (GM, "simulate", "S"): (56, 56, 56),
    (GM, "simulate", "cell B of the control"): ALL, (GM, "simulate", "Part A, plain"): ALL,
    (GM, "simulate", "Part A, steered"): (56, 56, 56),
    # E. Qwen3.6-35B solve: N wrong on d01, three wordings: 57. S and Part A steered
    # answer the third trial of every domain with a bare JSON plan in capitals: right
    # only in lower case (registered 60; frozen and not-lower-cased 40).
    (Q35, "solve", "N"): (57, 57, 57), (Q35, "solve", "P"): ALL,
    (Q35, "solve", "S"): (60, 40, 40),
    (Q35, "solve", "cell B of the control"): ALL, (Q35, "solve", "Part A, plain"): ALL,
    (Q35, "solve", "Part A, steered"): (60, 40, 40),
    # F. Qwen3.6-35B simulate: N right one object per line on v11 in d01..d04 (frozen 56);
    # Part A plain wrong on d07 v12: 59.
    (Q35, "simulate", "N"): (60, 56, 60), (Q35, "simulate", "P"): ALL,
    (Q35, "simulate", "S"): ALL, (Q35, "simulate", "cell B of the control"): (60, 56, 60),
    (Q35, "simulate", "Part A, plain"): (59, 59, 59), (Q35, "simulate", "Part A, steered"): ALL,
}
S20 = (100 / 3, 100 / 3, 100 / 3, P20)                 # +1 on one wording in every domain
F20 = (-100 / 3, -100 / 3, -100 / 3, P20)
UP4 = (400 / 60, 100 / 60, 800 / 60, 0.125)            # +1 in four domains
DOWN4 = (-400 / 60, -800 / 60, -100 / 60, 0.125)
ZERO = (0.0, 0.0, 0.0, 1.0)
# (est, lo, hi, p, p_holm, label, gained, lost) per (name, model, task), registered grade.
REGISTERED = {
    # M1 = P minus N. Holm over the six: p = 2^-19 first (6p), then 0.125 (5 * 0.125),
    # then four of 1.0.
    ("M1", Q9, "solve"): S20 + (HOLM6, "tools ahead", 20, 0),
    ("M1", Q9, "simulate"): UP4 + (0.625, "tools ahead (not after Holm)", 4, 0),
    ("M1", GM, "solve"): ZERO + (1.0, NDS, 0, 0),      # both right in lower case
    ("M1", GM, "simulate"): ZERO + (1.0, NDS, 0, 0),
    # one domain with sum +3: est 5.0, [0, 15.0]; the interval touches 0: no difference.
    ("M1", Q35, "solve"): (5.0, 0.0, 15.0, 1.0, 1.0, NDS, 3, 0),
    ("M1", Q35, "simulate"): ZERO + (1.0, NDS, 0, 0),
    # M2 = S minus N. Qwen3.5-9B simulate is the pairing trap: S is wrong on v14 where N
    # is wrong on v11, so every paired difference is 0 (gained 0, lost 0). A pairing by
    # the raw wording would find no pair; one that crossed wordings would gain 4, lose 4.
    ("M2", Q9, "solve"): S20 + (HOLM6, "tools ahead", 20, 0),
    ("M2", Q9, "simulate"): ZERO + (1.0, NDS, 0, 0),
    ("M2", GM, "solve"): ZERO + (1.0, NDS, 0, 0),
    ("M2", GM, "simulate"): DOWN4 + (0.625, "no tools ahead (not after Holm)", 0, 4),
    ("M2", Q35, "solve"): (5.0, 0.0, 15.0, 1.0, 1.0, NDS, 3, 0),
    ("M2", Q35, "simulate"): ZERO + (1.0, NDS, 0, 0),
    # M3 = S minus P. Two p of 0.125: Holm gives 6 * 0.125 = 0.75 to the first and
    # max(0.75, 5 * 0.125) = 0.75 to the second.
    ("M3", Q9, "solve"): ZERO + (1.0, NDS, 0, 0),
    ("M3", Q9, "simulate"): DOWN4 + (0.75, "naming the tool hurts (not after Holm)", 0, 4),
    ("M3", GM, "solve"): ZERO + (1.0, NDS, 0, 0),
    ("M3", GM, "simulate"): DOWN4 + (0.75, "naming the tool hurts (not after Holm)", 0, 4),
    ("M3", Q35, "solve"): ZERO + (1.0, NDS, 0, 0),
    ("M3", Q35, "simulate"): ZERO + (1.0, NDS, 0, 0),
    # K1 = N minus cell B of the control. Cell B is all right on Qwen3.5-9B simulate
    # (N lost d01..d04) and on Qwen3.6-35B solve (N lost d01 three times).
    ("K1", Q9, "solve"): ZERO + (1.0, MET, 0, 0),
    ("K1", Q9, "simulate"): DOWN4 + (0.75, "a difference is shown (not after Holm)", 0, 4),
    ("K1", GM, "solve"): ZERO + (1.0, MET, 0, 0),
    ("K1", GM, "simulate"): ZERO + (1.0, MET, 0, 0),
    ("K1", Q35, "solve"): (-5.0, -15.0, 0.0, 1.0, 1.0, "unresolved", 0, 3),
    ("K1", Q35, "simulate"): ZERO + (1.0, MET, 0, 0),
    # K2 = P minus Part A plain. One domain with sum +1: [0, 5.0], inside the margin with
    # the endpoint included.
    **{("K2", m, t): ZERO + (1.0, MET, 0, 0) for m in (Q9, GM, Q35) for t in ("solve", "simulate")
       if (m, t) != (Q35, "simulate")},
    ("K2", Q35, "simulate"): (100 / 60, 0.0, 5.0, 1.0, 1.0, MET, 1, 0),
    # K3 = S minus Part A steered. Part A steered is all right on Qwen3.5-9B simulate.
    **{("K3", m, t): ZERO + (1.0, MET, 0, 0) for m in (Q9, GM, Q35) for t in ("solve", "simulate")
       if (m, t) != (Q9, "simulate")},
    ("K3", Q9, "simulate"): DOWN4 + (0.75, "a difference is shown (not after Holm)", 0, 4),
}
# The descriptive grades where they differ from the registered grade: (est, lo, hi, p).
DESCRIPTIVE = {
    # Not lower-cased: Gemma solve P loses the capital-letter plans (40 against N's 60).
    ("M1", "second", GM, "solve"): F20, ("M3", "second", GM, "solve"): S20,
    ("M2", "second", GM, "solve"): ZERO,
    # Frozen: Gemma solve N and P both miss v11 (40 and 40, the same trials); S is 60.
    ("M1", "frozen", GM, "solve"): ZERO, ("M2", "frozen", GM, "solve"): S20,
    ("M3", "frozen", GM, "solve"): S20,
    # Frozen: Qwen3.6-35B simulate N misses the four per-line traces.
    ("M1", "frozen", Q35, "simulate"): UP4, ("M2", "frozen", Q35, "simulate"): UP4,
    ("M3", "frozen", Q35, "simulate"): ZERO,
    ("M1", "frozen", Q9, "solve"): S20,
    # Qwen3.6-35B solve: S loses the bare capital-letter plans under both descriptive
    # grades (one trial in every domain); P is all right.
    ("M3", "second", Q35, "solve"): F20, ("M3", "frozen", Q35, "solve"): F20,
}


def test_base(r):
    code, err, res, _ = run_fixture(FIXTURE)
    r.check("base fixture runs", code == 0, err)
    if res is None:
        return
    r.check_eq("mode", res["mode"], "fixture")
    r.check_eq("design k", res["design"]["k_domains"], 20)
    r.check_eq("package hash recorded", res["package_sha256"], M.package_sha256())
    for (m, t, cell), want in RATES.items():
        e = by(res, "rates", model=m, task=t, cell=cell)
        got = (e["registered"]["right"], e["frozen"]["right"], e["second"]["right"])
        r.check_eq(f"rate {m}/{t}/{cell}", (e["n"],) + got, (60,) + want)
        r.check_eq(f"rate {m}/{t}/{cell} k", e["registered"]["k"], 20)
    r.check_eq("36 rate rows (18 of this run, 18 earlier)", len(res["rates"]), 36)
    # The counter: the registered grade against the control's case-folded column. They
    # differ on the one scoring-exception row (case folded reads its answer).
    r.check_eq("trials where the registered grade differs from the case-folded column",
               {(e["model"], e["task"], e["cell"]): e["registered_differs_from_case_folded"]
                for e in res["rates"] if e["registered_differs_from_case_folded"]},
               {(Q9, "solve", "N"): 1})
    # Rate interval where every domain is the same: Qwen3.5-9B solve N (2 of 3 everywhere).
    e = by(res, "rates", model=Q9, task="solve", cell="N")["registered"]
    r.check("rate interval equals the estimate (every domain 2/3)",
            close(e["est"], 200 / 3) and close(e["lo"], 200 / 3) and close(e["hi"], 200 / 3), e)
    r.check_eq("18 contrasts under three grades", len(res["contrasts"]), 54)
    r.check_eq("18 continuity checks under three grades", len(res["continuity"]), 54)
    r.check_eq("the counts stated with every table", (res["n_contrasts"], res["n_continuity"]),
               (18, 18))
    for (name, m, t), (est, lo, hi, p, ph, label, gained, lost) in REGISTERED.items():
        sec = "contrasts" if name.startswith("M") else "continuity"
        c = by(res, sec, name=name, grade="registered", model=m, task=t)
        r.check(f"{name} {m}/{t}: {est:.3f} [{lo:.3f}, {hi:.3f}] p {p:.3g} holm {ph:.3g}",
                close(c["est"], est) and close(c["lo"], lo) and close(c["hi"], hi)
                and close(c["p"], p) and close(c["p_holm"], ph) and c["k"] == 20
                and c["n_pairs"] == 60 and c["unpaired"] == 0,
                {k: c[k] for k in ("est", "lo", "hi", "p", "p_holm", "k", "n_pairs", "unpaired")})
        r.check_eq(f"{name} {m}/{t} label", c["label"], label)
        r.check_eq(f"{name} {m}/{t} gained, lost", (c["gained"], c["lost"]), (gained, lost))
    r.check_eq("every registered contrast is in the expected table", len(REGISTERED), 36)
    for (name, gr, m, t), (est, lo, hi, p) in DESCRIPTIVE.items():
        c = by(res, "contrasts", name=name, grade=gr, model=m, task=t)
        r.check(f"descriptive {name} {gr} {m}/{t}",
                close(c["est"], est) and close(c["lo"], lo) and close(c["hi"], hi)
                and close(c["p"], p) and c["n_pairs"] == 60, c)
    r.check("a descriptive grade carries no label (no reading uses it)",
            all(c["label"] is None for c in res["contrasts"] + res["continuity"]
                if c["grade"] != "registered"))
    # The inclusive endpoint: exactly 5.0, met.
    c = by(res, "continuity", name="K2", grade="registered", model=Q35, task="simulate")
    r.check("endpoint exactly 5.0 counts as inside the margin",
            c["hi"] == 5.0 and c["label"] == MET, c["hi"])
    # Q1: where M1 and M2 differ, both are stated and M3 says what naming the tool added.
    differ = {(Q9, "simulate"), (GM, "simulate")}
    for e in res["readings"]:
        key = (e["model"], e["task"])
        q1 = e["Q1"]
        r.check_eq(f"Q1 {key} labels", (q1["tools_offered"], q1["tools_offered_and_named"]),
                   (REGISTERED[("M1",) + key][5], REGISTERED[("M2",) + key][5]))
        r.check_eq(f"Q1 {key} differ", q1["differ"], key in differ)
        r.check_eq(f"Q1 {key} naming the tool", q1["naming_the_tool"],
                   REGISTERED[("M3",) + key][5] if key in differ else None)
        for name in ("K1", "K2", "K3"):
            q2 = e["Q2"][name]
            r.check_eq(f"Q2 {name} {key} met", q2["criterion_met"],
                       REGISTERED[(name,) + key][5] == MET)
            r.check(f"Q2 {name} {key} carries both dates",
                    DATES in q2["sentence"] and M.EARLIER_DATES[name] in q2["sentence"],
                    q2["sentence"])
    q = by(res, "readings", model=Q9, task="simulate")
    r.check_eq("Q1 sentence where the two differ", q["Q1"]["sentence"],
               "tools offered: tools ahead (not after Holm) (+6.7 [+1.7, +13.3]); tools offered "
               "and named: no difference shown (+0.0 [+0.0, +0.0]); the two differ; naming the "
               "tool: naming the tool hurts (not after Holm) (-6.7 [-13.3, -1.7])")
    r.check("Q2 not met gives the estimate", q["Q2"]["K1"]["sentence"].startswith(
        "this run does not meet the criterion against cell B of the control for arm N (a "
        "difference is shown (not after Holm), -6.7 [-13.3, -1.7])"), q["Q2"]["K1"]["sentence"])
    r.check("Q2 met says the run reproduces the earlier one within the margin, with the "
            "estimate",
            by(res, "readings", model=Q35, task="simulate")["Q2"]["K2"]["sentence"].startswith(
                "this run reproduces Part A, plain for arm P within the margin (criterion met, "
                "+1.7 [+0.0, +5.0])"))
    # Corpus: one exception row kept (Qwen3.5-9B N, 1 of 120 <= 1%); one answer cut by
    # storage at the output cap accepted (Qwen3.5-9B tools); one half-written line
    # counted and skipped (Gemma tools).
    def corpus(field):
        return {c["cell"]: c[field] for c in res["corpus"] if c[field]}
    r.check_eq("exception rows kept and counted", corpus("exception_rows"),
               {BF.folder(Q9, "N", BF.RUN_TAG): 1})
    r.check_eq("storage-cut rows accepted and counted (a tools cell)",
               corpus("storage_cut_accepted"), {BF.folder(Q9, "T", BF.RUN_TAG): 1})
    r.check_eq("torn lines counted (a tools cell)", corpus("torn_lines"),
               {BF.folder(GM, "T", BF.RUN_TAG): 1})
    # Section 2.3: the user texts of N against the control's cell B. One text of the
    # control differs (Qwen3.6-35B simulate d07 v12): reported, not a halt.
    r.check_eq("user texts of N against the control's cell B",
               {(u["model"], u["task"]): (u["shared"], u["only_this_run"], u["only_control"])
                for u in res["audit"]["user_texts_vs_control"]},
               {**{(m, t): (60, 0, 0) for m in (Q9, GM, Q35) for t in ("solve", "simulate")},
                (Q35, "simulate"): (59, 1, 1)})
    # Section 3: the simulate trials on the problems whose prompt plan can differ from
    # the cached key (design.json: d02/p01, three trials; d20/p02, two; d20/p01 is not
    # listed). Wrong among them: Qwen3.5-9B N (d02 v11) and S (d02 v14), Gemma S (d02 v16).
    kp = res["key_plan_differs"]
    r.check_eq("key-plan problems listed", kp["problems"], ["d02/p01", "d20/p02"])
    r.check_eq("key-plan trials and right, per model and arm",
               {(c["model"], c["arm"]): (c["trials"], c["right"]) for c in kp["cells"]},
               {**{(m, a): (5, 5) for m in (Q9, GM, Q35) for a in ("N", "P", "S")},
                (Q9, "N"): (5, 4), (Q9, "S"): (5, 4), (GM, "S"): (5, 4)})
    r.check_eq("corpus rows", sorted({c["rows"] for c in res["corpus"]}), [120, 240])
    # Audit: several lines per trial in a tools cell; one re-sent request in an N cell.
    users = res["audit"]["users"]
    r.check_eq("N and tools share the 120 plain user texts; 120 steered ones are tools only",
               {m: (u["shared_user_texts"], u["tools_only_user_texts"]) for m, u in users.items()},
               {m: (120, 120) for m in (Q9, GM, Q35)})
    # Tools lines: 2 per trial with a tool call, 1 without. Q9: 240 trials, 4 without
    # (simulate v14 d01..d04): 476. Gemma: 480. Q35: 20 without (solve v13): 460.
    r.check_eq("tools-cell audit lines (several per trial)",
               {m: u["tools_lines"] for m, u in users.items()}, {Q9: 476, GM: 480, Q35: 460})
    r.check_eq("re-sent request lines in the N cell",
               {m: u["n_resent_lines"] for m, u in users.items()}, {Q9: 0, GM: 0, Q35: 1})
    r.check_eq("the tools-repo note is recorded", res["audit"]["tools_repo_note"], REPO_NOTE)
    # Secondary tables.
    s = by(res, "secondary", model=GM, task="solve", arm="N")
    r.check_eq("layout Gemma solve N", s["layout"], {RG.JSON_BLOCK: 20, CPF.NO_PLAN_BLOCK: 40})
    r.check_eq("no wrong trial there under the registered grade", s["failure_reasons"], {})
    s = by(res, "secondary", model=Q9, task="solve", arm="N")
    r.check_eq("failure reasons of the wrong trials (19 wrong plans and the exception row)",
               s["failure_reasons"], {"exception": 1, "plan_invalid": 19})
    # The wrong trial of a domain is its second one: (p01, v12) in d01..d18, (p02, v11)
    # in d19, (p01, v13) in d20. So v11 has 19 right of 20, v12 2 of 20, v13 19 of 20.
    r.check_eq("right by wording, Qwen3.5-9B solve N",
               {v: d["registered"] for v, d in s["by_wording"].items()},
               {"11": 19, "12": 2, "13": 19})
    r.check_eq("20 trials per wording", s["per_wording_n"], {"11": 20, "12": 20, "13": 20})
    r.check_eq("exception row counted in its arm", s["exception_rows"], 1)
    s = by(res, "secondary", model=Q9, task="simulate", arm="S")
    r.check_eq("steered arm lists the steered wordings", sorted(s["by_wording"]),
               ["14", "15", "16"])
    r.check_eq("trials with a tool call, Qwen3.5-9B simulate S", s["called_a_tool"], 56)
    # Stopped at the output cap = the answer ended at the cap and the final turn was not
    # refused or clipped. Qwen3.5-9B simulate S: the storage-cut answer (1), no window-full
    # trial. Gemma simulate S: d04 ended at the cap with room (1); d01 and d02 were
    # refused and d03 clipped (3 window-full, not counted as stopped at the cap).
    r.check_eq("Qwen3.5-9B simulate S: at the cap, window full",
               (s["at_output_cap"], s["window_full"]), (1, 0))
    s = by(res, "secondary", model=GM, task="simulate", arm="S")
    r.check_eq("Gemma simulate S: at the cap, window full",
               (s["at_output_cap"], s["window_full"]), (1, 3))
    r.check_eq("Gemma simulate S: frozen reasons of the four wrong trials",
               s["failure_reasons"], {"no_room": 2, "trajectory_mismatch": 2})
    r.check_eq("no other arm has a trial at the cap or with a full window",
               sum(x["at_output_cap"] + x["window_full"] for x in res["secondary"]), 5)
    r.check_eq("trials with a tool call, Qwen3.6-35B solve P",
               by(res, "secondary", model=Q35, task="solve", arm="P")["called_a_tool"], 40)
    r.check_eq("no tool call in any N arm",
               {s["called_a_tool"] for s in res["secondary"] if s["arm"] == "N"}, {0})
    # Three unread final answers in Qwen3.6-35B solve N: exactly 5%, the tripwire stays.
    r.check_eq("unread final answers, Qwen3.6-35B solve N",
               by(res, "secondary", model=Q35, task="solve", arm="N")["unread_final_answers"], 3)
    r.check_eq("no tripwire fired", (res["tripwires_audited"], res["tripwires_fired_not_halting"]),
               ({}, {}))
    # Section 6 rule 3, which tool was called. Qwen3.5-9B solve S calls the classic
    # planner on v15 in every domain: right in d01..d10, the other planner in d11..d20.
    t = by(res, "tool_choice", model=Q9, task="solve", arm="steered")
    r.check_eq("tool choice: the wrong planner is 'other only'", t["counts"],
               {"none": 0, "right_only": 50, "right_plus": 0, "other_only": 10})
    r.check_eq("tool choice: the other planner counted", t["other_planner"], 10)
    r.check_eq("tool choice: no call", by(res, "tool_choice", model=Q35, task="solve",
                                          arm="plain")["counts"],
               {"none": 20, "right_only": 40, "right_plus": 0, "other_only": 0})
    r.check_eq("tool choice: no call on simulate", by(res, "tool_choice", model=Q9,
                                                      task="simulate", arm="steered")["counts"],
               {"none": 4, "right_only": 56, "right_plus": 0, "other_only": 0})
    r.check_eq("tool choice: 12 cells", len(res["tool_choice"]), 12)
    # Section 6 rule 3, tool right and final answer wrong. "Wrong" is the registered
    # grade; the frozen-grade version is beside it. Gemma solve P: the tool was right in
    # all 60; the registered grade reads the 20 capital-letter block plans (0 wrong), the
    # frozen grader misses them (20 wrong, 33.3%, the same in every domain). Gemma
    # simulate S: 4 wrong traces after a right tool under both.
    g = by(res, "tool_right_answer_wrong", model=GM, task="solve", arm="P")
    r.check_eq("tool right, answer wrong: Gemma solve P",
               (g["n_trials"], g["n_tool_right"], g["n_lost"], g["n_lost_frozen"],
                g["why_frozen"]), (60, 60, 0, 20, {"WRONG_WRAPPER": 20}))
    r.check("registered share 0, frozen share 33.3 with a point interval",
            close(g["lost"]["est"], 0.0) and close(g["lost_frozen"]["est"], 100 / 3)
            and close(g["lost_frozen"]["lo"], 100 / 3), (g["lost"], g["lost_frozen"]))
    g = by(res, "tool_right_answer_wrong", model=GM, task="simulate", arm="S")
    r.check_eq("tool right, answer wrong: Gemma simulate S (3 refused or clipped, 1 wrong)",
               (g["n_tool_right"], g["n_lost"], g["n_lost_frozen"], g["why_frozen"]),
               (60, 4, 4, {"REFUSED_OR_CLIPPED_FINAL": 3, "WRONG_FACTS": 1}))
    # Qwen3.6-35B solve S: the bare capital-letter plan repeats the tool's plan; the
    # frozen grade calls it invalid (20), the registered grade reads it (0).
    g = by(res, "tool_right_answer_wrong", model=Q35, task="solve", arm="S")
    r.check_eq("tool right, answer wrong: Qwen3.6-35B solve S",
               (g["n_tool_right"], g["n_lost"], g["n_lost_frozen"], g["why_frozen"]),
               (60, 0, 20, {"TOOL_INPUT_ERROR": 20}))
    r.check_eq("every frozen-wrong trial was classified",
               sum(c["not_classified"] for c in res["tool_right_answer_wrong"]), 0)
    g = by(res, "tool_right_answer_wrong", model=GM, task="simulate", arm="S")
    r.check("its registered share is 4 of 60", close(g["lost"]["est"], 400 / 60), g["lost"])
    g = by(res, "tool_right_answer_wrong", model=Q9, task="simulate", arm="S")
    r.check_eq("no tool call is not 'tool right'", (g["n_tool_right"], g["n_lost"]), (56, 0))
    # Section 6 rule 4. Reference plans: 2 actions in d01..d10 (bin 1-5), 7 in d11..d20
    # (bin 6-10); 30 trials of an arm in each bin.
    bl = {(c["model"], c["arm"], c["bin"]): c for c in res["breakdowns"]["solve_by_reference_length"]}
    q9n = [bl[("Qwen3.5-9B", "none", b)] for b in ("1–5", "6–10")]
    r.check("solve by reference length: Qwen3.5-9B N is 20 of 30 in both bins",
            all(c["n"] == 30 and close(c["solved"]["est"], 200 / 3) for c in q9n), q9n)
    q35 = [bl[("Qwen3.6-35B", "none", b)] for b in ("1–5", "6–10")]
    r.check("solve by reference length: Qwen3.6-35B N lost d01 (27 of 30, then 30 of 30)",
            close(q35[0]["solved"]["est"], 90.0) and close(q35[1]["solved"]["est"], 100.0), q35)
    r.check("solve by reference length uses the registered grade (Gemma P is 100)",
            close(bl[("Gemma-26B", "plain", "1–5")]["solved"]["est"], 100.0))
    so = {(c["model"], c["arm"]): c for c in res["breakdowns"]["simulate_overall"]}
    # Qwen3.5-9B simulate N: 56 exact; a wrong trace has 1 of its 2 states right:
    # (56 + 4 * 0.5) / 60 = 96.67 strict, the same lenient.
    c = so[("Qwen3.5-9B", "none")]
    r.check("simulate: exact, strict and lenient state scores",
            c["n"] == 60 and close(c["exact"]["est"], 5600 / 60)
            and close(c["states"]["est"], 5800 / 60)
            and close(c["states_salvaged"]["est"], 5800 / 60), c)
    # Qwen3.6-35B simulate N: the four per-line traces score all their states (the line
    # trace is a candidate, as in rq1_control_metrics).
    c = so[("Qwen3.6-35B", "none")]
    r.check("simulate: a per-line trace scores all its states",
            close(c["exact"]["est"], 100.0) and close(c["states"]["est"], 100.0), c)
    r.check_eq("simulate by trace length: one bin (one action)",
               {c["bin"] for c in res["breakdowns"]["simulate_by_trace_length"]}, {"1–5"})
    r.check_eq("no simulate problem left out", res["breakdowns"]["simulate_left_out"], [])
    md = res["_md"]
    for title in ("delivered right per arm", "contrasts M1 to M3, registered grade",
                  "registered readings (section 5, Q1)", "continuity checks K1 to K3",
                  "which tool was called", "tool right and final answer wrong",
                  "solved by reference plan length", "simulate by trace length", "corpus",
                  "mean output tokens", "answer wrong (registered grade)",
                  "Holm-adjusted p | unpaired | earlier run",
                  "final turn refused or clipped (window full)",
                  "problems whose prompt plan can differ from the cached key",
                  "not classified by the rerun's rules", "only in the control",
                  "differs from the control's case-folded column"):
        r.check(f"markdown has: {title}", title in md)
    r.check("markdown states the number of contrasts with the tables",
            md.count("18 contrasts and 18 continuity checks") >= 8)
    r.check("markdown carries the dates of the three runs",
            DATES in md and M.PART_A_DATES in md and M.CONTROL_DATES in md)
    r.check("no em-dash in the markdown", "—" not in md)


# ------------------------------------------------------------------ refusals
def _edit_rows(sub, fn):
    def mut(root):
        edit_jsonl(sub(root) / "trials.jsonl", fn)
    return mut


def _dup(recs):
    return recs + [copy.deepcopy(recs[0])]


def _cut_not_at_cap(recs):
    recs[find(recs, "solve", "d02", 11)]["result"]["response_truncated_by_storage"] = True
    return recs


def _rename(fos, wordings, model=Q9):
    def mut(root):
        for fo in fos:
            def fn(recs):
                for o in recs:
                    res = o["result"]
                    if (res["task"], res["domain_name"]) == ("simulate", "d01") \
                            and res["prompt_variant"] in wordings:
                        res["problem_name"] = "p02"
                        o["key"][3] = "p02"
                return recs
            edit_jsonl(mdir(root, model, fo) / "trials.jsonl", fn)
    return mut


def _audit(model, fo, fn):
    def mut(root):
        edit_jsonl(mdir(root, model, fo) / "system_prompt_audit.jsonl", fn)
    return mut


def _set_line(i, **kw):
    def fn(recs):
        recs[i].update(kw)
        return recs
    return fn


def _same_user_twice(recs):
    """A tools trial has two lines; give both lines of the second trial the user text of
    the first, so one trial has no line of its own."""
    recs[2]["user_sha256"] = recs[3]["user_sha256"] = recs[0]["user_sha256"]
    return recs


def _settings(model, fo, **kw):
    def mut(root):
        edit_json(mdir(root, model, fo) / "client_settings.json", lambda s: s.update(kw))
    return mut


def _meta(model, fo, **kw):
    def mut(root):
        p = next(mdir(root, model, fo).glob("summary_*.json"))
        edit_json(p, lambda s: s["meta"].update(kw))
    return mut


def _tokens(model, fo, task, dom, v, done=None, **kw):
    def fn(recs):
        res = recs[find(recs, task, dom, v)]["result"]
        res["tokens"].update(kw)
        if done is not None:
            res["done_reason"], res["truncated"] = done, done == "length"
        return recs
    return _edit_rows(lambda root: mdir(root, model, fo), fn)


def _serve_version(root):
    p = root / "serve_logs" / f"26000004-vllm-{GM}.log"
    p.write_text(p.read_text().replace("v0.20.2", "v0.22.0"))


def _route_disagrees(root):
    def fn(obj):
        for e in obj:
            if e["domain"] == "d07" and e["plan"] == BF.PLAN:
                e["valid"] = False
    edit_json(root / "route" / "plan_verdicts.json", fn)


def _rm(rel):
    def mut(root):
        for p in root.glob(rel):
            p.unlink()
    return mut


def _exceptions(model, fo, n, with_tools):
    def mut(root):
        for i in range(n):
            set_answer(mdir(root, model, fo), model, "solve", f"d{i + 6:02d}", 13, "exception",
                       with_tools)
    return mut


def test_refusals(r):
    tools = lambda m: (lambda root: mdir(root, m, "T"))      # noqa: E731
    nf = lambda m: (lambda root: mdir(root, m, "N"))         # noqa: E731
    expect_halt(r, "duplicate trial key", _edit_rows(tools(Q9), _dup), "duplicate trial key")
    expect_halt(r, "a storage-cut row that did not stop at the output cap",
                _edit_rows(nf(GM), _cut_not_at_cap), "did not stop at the output cap")
    # N folder: the base holds 1 exception row of 120 in Qwen3.5-9B; a second makes
    # 2 of 120 = 1.7% > 1%.
    expect_halt(r, "N cell: exception rows above 1% -> VOID", _exceptions(Q9, "N", 1, False),
                "both cells of Qwen3_5_9B are run again from scratch")
    # Tools folder: 3 of 240 = 1.25% > 1%.
    expect_halt(r, "tools cell: exception rows above 1% -> VOID", _exceptions(GM, "T", 3, True),
                "VOID (section 7)")
    expect_halt(r, "a short tools cell", _edit_rows(tools(Q9), lambda recs: recs[:-1]),
                "239 rows, registered 240")
    expect_halt(r, "a short N cell", _edit_rows(nf(Q35), lambda recs: recs[:-1]),
                "119 rows, registered 120")
    # The same problem renamed in N, P and S: the arms agree, the rerun's keys differ.
    expect_halt(r, "trial keys that differ from the rerun's",
                _rename(("N", "T"), (11, 12, 13, 14, 15, 16)), "keys differ from the rerun's")
    # Renamed in N only: the N and tools cells no longer hold the same problems.
    expect_halt(r, "N and tools cells do not hold the same problems",
                _rename(("N",), (11, 12, 13)), "do not hold the same simulate problems")
    # Renamed in the steered wordings only: S is not paired with P and N.
    expect_halt(r, "steered wordings not on the plain wordings' problems",
                _rename(("T",), (14, 15, 16)), "do not hold the same simulate problems")

    def unknown_reason(recs):
        recs[5]["result"]["failure_reason"] = "plan_almost_valid"
        return recs
    expect_halt(r, "an unknown failure_reason (loader)", _edit_rows(tools(GM), unknown_reason),
                "unknown failure_reason 'plan_almost_valid'")

    def foreign_domain(recs):
        recs[0]["result"]["domain_name"] = "blocksworld"
        recs[0]["key"][2] = "blocksworld"
        return recs
    expect_halt(r, "a row of a real domain in fixture mode",
                _edit_rows(nf(GM), foreign_domain), "is not one of the fixture's own")
    # Audit, N cell (the control's check with cell B).
    expect_halt(r, "audit N: wrong system digest",
                _audit(Q9, "N", _set_line(3, system_sha256="0" * 64)),
                "is not the registered text of cell B")
    expect_halt(r, "audit N: a line with tools", _audit(Q35, "N", _set_line(9, has_tools=True)),
                "has tools")
    expect_halt(r, "audit N: not swapped", _audit(GM, "N", _set_line(7, swapped=False)),
                "swapped=False")
    # Audit, tools cell.
    expect_halt(r, "audit tools: wrong system digest",
                _audit(Q9, "T", _set_line(3, system_sha256="0" * 64)),
                "is not the with-tools text of Part A")
    expect_halt(r, "audit tools: the N text in a tools cell",
                _audit(Q9, "T", _set_line(3, system_sha256=M.N_SYSTEM_SHA256["solve"])),
                "is not the with-tools text of Part A")
    expect_halt(r, "audit tools: the stored text is not the registered text",
                _audit(Q9, "T", _set_line(0, system_text="You are a helpful assistant.")),
                "byte for byte")
    expect_halt(r, "audit tools: a request without tools",
                _audit(GM, "T", _set_line(8, has_tools=False)), "without tools")
    expect_halt(r, "audit tools: marked swapped", _audit(GM, "T", _set_line(7, swapped=True)),
                "swapped=True")
    expect_halt(r, "audit tools: wrong mode",
                _audit(GM, "T", _set_line(7, mode="format-stated")), "mode 'format-stated'")
    expect_halt(r, "audit tools: another model",
                _audit(GM, "T", _set_line(7, model="Qwen/Qwen3.5-9B")), "model 'Qwen/Qwen3.5-9B'")
    expect_halt(r, "audit tools: a missing audit file",
                _rm(f"matched/{BF.folder(Q35, 'T', BF.RUN_TAG)}/system_prompt_audit.jsonl"),
                "no system_prompt_audit.jsonl")
    expect_halt(r, "audit N: a missing audit file",
                _rm(f"matched/{BF.folder(Q35, 'N', BF.RUN_TAG)}/system_prompt_audit.jsonl"),
                "no system_prompt_audit.jsonl")
    expect_halt(r, "audit tools: a trial with no line of its own",
                _audit(Q9, "T", _same_user_twice), "19 different user texts for solve")
    expect_halt(r, "audit tools: fewer lines than rows",
                _audit(GM, "T", lambda recs: [o for o in recs if o["system_sha256"]
                                              != M.TOOLS_SYSTEM_SHA256["simulate"]][:1]
                       + [o for o in recs if o["system_sha256"]
                          == M.TOOLS_SYSTEM_SHA256["simulate"]]),
                "1 audit lines for solve, fewer than its 120 rows")
    # Item 5: a user message of N that the tools cell never sent.
    expect_halt(r, "a user message of N is not sent in the tools cell",
                _audit(Q9, "N", _set_line(11, user_sha256="a" * 64)),
                "user messages of the N cell are not sent in the tools cell")
    # Settings.
    expect_halt(r, "tools client_settings.json names a no-tools system text",
                _settings(GM, "T", no_tools_system="format-stated"),
                "client_settings.json no_tools_system='format-stated'")
    expect_halt(r, "tools client_settings.json names another condition",
                _settings(GM, "T", cond="tools_all_neutral"), "cond='tools_all_neutral'")
    expect_halt(r, "N client_settings.json names another text",
                _settings(GM, "N", no_tools_system="no-pointer"),
                "client_settings.json no_tools_system='no-pointer'")
    expect_halt(r, "client_settings.json names another cell's audit log",
                _settings(GM, "T", system_audit_log="/x/slurm_vllm_other/system_prompt_audit.jsonl"),
                "is not this cell's audit log")
    expect_halt(r, "serve log shows another vLLM", _serve_version, "shows vLLM ['0.22.0']")
    expect_halt(r, "a missing serve log", _rm(f"serve_logs/26000002-vllm-{Q9}.log"), "not in")
    # Apparatus.
    expect_halt(r, "apparatus: context window, tools client_settings.json",
                _settings(Q9, "T", max_model_len=32768), "max_model_len 32768")
    expect_halt(r, "apparatus: context window, N client_settings.json",
                _settings(Q9, "N", max_model_len=32768), "max_model_len 32768")
    expect_halt(r, "apparatus: context window in a tools summary", _meta(Q35, "T", num_ctx=32768),
                "num_ctx=32768")
    expect_halt(r, "apparatus: temperature in a tools summary", _meta(Q35, "T", temperature=0.7),
                "temperature=0.7")
    expect_halt(r, "apparatus: a tools summary with a tool filter",
                _meta(Q35, "T", tool_filter="planners"), "tool_filter='planners'")
    expect_halt(r, "apparatus: a tools summary of a no-tools run",
                _meta(Q35, "T", conditions="no-tools"), "conditions='no-tools'")
    expect_halt(r, "apparatus: an N summary of a tools run", _meta(Q35, "N", conditions="tools"),
                "conditions='tools'")
    expect_halt(r, "apparatus: an N answer longer than the cap",
                _tokens(GM, "N", "solve", "d03", 12, completion=8193), "cap 8192")
    # Tools rows: 8192 per turn on solve; two turns may sum to 16,384, not more.
    expect_halt(r, "apparatus: a tools answer above the cap times its turns",
                _tokens(GM, "T", "solve", "d03", 12, completion=16385), "cap 8192 per turn")
    expect_halt(r, "apparatus: a one-turn tools answer stopped at the cap short of it",
                _tokens(GM, "T", "simulate", "d03", 12, done="length", turns=1, completion=6000),
                "one-turn answer stopped at the cap after 6000 tokens")
    expect_halt(r, "apparatus: a tools answer stopped at the cap with fewer tokens in all",
                _tokens(GM, "T", "simulate", "d03", 12, done="length", completion=6000),
                "stopped at the cap after 6000 tokens in all")
    # The summary names this run's two tasks and no output cap of its own (N and tools).
    expect_halt(r, "apparatus: a tools summary with its own output cap",
                _meta(Q35, "T", num_predict=4096), "num_predict=4096")
    expect_halt(r, "apparatus: an N summary with its own output cap",
                _meta(Q35, "N", num_predict=4096), "num_predict=4096")
    expect_halt(r, "apparatus: a tools summary of five tasks",
                _meta(GM, "T", tasks=["solve", "validate_domain", "validate_problem",
                                      "validate_plan", "simulate"]), "meta tasks=")
    expect_halt(r, "apparatus: an N summary of one task", _meta(GM, "N", tasks=["solve"]),
                "meta tasks=['solve']")
    expect_halt(r, "the control's cell B has no audit log to compare the user texts with",
                _rm("control/*/system_prompt_audit.jsonl"), "no system_prompt_audit.jsonl")
    # Earlier runs.
    expect_halt(r, "the route disagrees with a stored verdict", _route_disagrees,
                "route disagrees with the stored verdict")
    expect_halt(r, "Part A does not reproduce the filed readout",
                lambda root: edit_json(root / "filed_readout.json",
                                       lambda d: d["e1"][0].update(delivered_k=1)),
                "do not reproduce the filed readout")
    expect_halt(r, "the steered arm is missing from the filed readout",
                lambda root: edit_json(root / "filed_readout.json", lambda d: d.update(
                    e1=[e for e in d["e1"] if e["arm"] == "plain"])),
                "do not reproduce the filed readout")
    expect_halt(r, "Part A does not reproduce the filed re-grade",
                lambda root: edit_json(root / "filed_regrade.json", lambda d: [
                    c.update(folded_k=40) for c in d["cells"]
                    if (c["tag"], c["task"], c["arm"]) == (GM, "solve", "plain")]),
                "do not reproduce the filed re-grade")
    expect_halt(r, "cell B does not reproduce the control's filed readout",
                lambda root: edit_json(root / "filed_control.json", lambda d: [
                    c["second"].update(right=40) for c in d["rates"]
                    if (c["model"], c["task"]) == (GM, "solve")]),
                "does not reproduce the control's filed readout")
    # Mode guards.
    expect_halt(r, "fixture without its marker", _rm("SYNTHETIC_FIXTURE"),
                "has no SYNTHETIC_FIXTURE marker")
    expect_halt(r, "fixture mode refuses --numbers", lambda root: None,
                "--numbers is for live mode only", extra=["--numbers"])
    expect_halt(r, "a registered-size design in fixture mode",
                lambda root: edit_json(root / "design.json", lambda d: d.update(
                    per_task_arm=300, n_folder=600, tools_folder=1200, per_wording=200,
                    per_task_wording=100)),
                "refuses a registered-size design")
    expect_halt(r, "fixture and dry run together", lambda root: None,
                "different modes", extra=["--dry-run-existing"])
    expect_halt(r, "no dates for the run", lambda root: None, "--run-dates is required",
                dates=False)
    expect_halt(r, "item 7: no note on the tools repo", lambda root: None,
                "pass --tools-repo-checked-by-hand NOTE", repo_note=False)
    # Item 7 by hand: with a note the run passes without serve logs and records it.
    root = copy_fixture()
    try:
        _rm("serve_logs/*")(root)
        code, err, res, _ = run_fixture(root, ["--version-checked-by-hand", "banners read"])
        r.check("item 7 by hand: passes and is recorded",
                code == 0 and res["audit"]["version_note"] == "banners read"
                and res["audit"]["serve_logs"] == {}, err[-300:])
        code, err, _, _ = run_fixture(root)
        r.check("item 7: no serve log and no note halts", code == 2 and "not in" in err, err)
    finally:
        shutil.rmtree(root.parent)
    # Exception rows at or under 1% stay in: 2 of 240 in a tools cell.
    root = copy_fixture()
    try:
        _exceptions(GM, "T", 2, True)(root)
        code, err, res, _ = run_fixture(root)
        ex = {c["cell"]: c["exception_rows"] for c in (res or {"corpus": []})["corpus"]}
        r.check("2 exception rows of 240 (0.8%) are kept and graded as they are",
                code == 0 and ex.get(BF.folder(GM, "T", BF.RUN_TAG)) == 2
                and by(res, "rates", model=GM, task="solve", cell="P")["registered"]["right"]
                == 58, err[-300:])
    finally:
        shutil.rmtree(root.parent)


def test_units(r):
    """Small rules on their own: the pairing key, the input files, the classifier."""
    # A pairing key without the problem: d19 holds p01 and p02 on v11, so the keys of an
    # arm collide and the analysis halts.
    real = M.canon
    M.canon = lambda key: (key[0], key[1], "", key[3], real(key)[4])
    try:
        code, err, _, written = run_fixture(FIXTURE)
        r.check("a pairing key without the problem is caught",
                code == 2 and "pairing keys are unique within an arm" in err and written == [],
                err[-300:])
    finally:
        M.canon = real
    # The four input files outside the package hash.
    tmp = Path(tempfile.mkdtemp(prefix="mr_in_"))
    try:
        import argparse
        files = {k: tmp / f"{k}.json" for k in M.INPUT_SHA256}
        for f in files.values():
            f.write_text("{}\n")
        try:
            M.check_inputs(argparse.Namespace(**files))
            r.check("an input file with another sha256 is refused", False)
        except M.Halt as e:
            r.check("an input file with another sha256 is refused",
                    "is not the recorded" in str(e) and "section 9" in str(e), str(e))
        files["regrade_json"] = tmp / "absent.json"
        try:
            M.check_inputs(argparse.Namespace(**files))
            r.check("a missing input file is refused", False)
        except M.Halt as e:
            r.check("a missing input file is refused", "cannot be read" in str(e), str(e))
    finally:
        shutil.rmtree(tmp)
    import hashlib
    for name, rel in (("regrade_json", "tools/reanalysis/out/rq1_layout_regrade.json"),
                      ("control_json", "tools/reanalysis/out/control_prompt_fix.json"),
                      ("readout_json", "development/reference/delivered_rerun_readout.json")):
        r.check_eq(f"recorded sha256 of {rel}", M.INPUT_SHA256[name],
                   hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest())
    # A row the rerun's classifier refuses is counted, and the tables still come out.
    real_classify = M.E4.classify
    seen = []

    def refuse_one(row, dlv, gt):
        if row.task == "simulate" and row.domain == "d04" and not seen:
            seen.append(row.trial_key)
            raise S.SchemaError("planted: not classifiable")
        return real_classify(row, dlv, gt)
    M.E4.classify = refuse_one
    try:
        code, err, res, _ = run_fixture(FIXTURE)
        g = by(res, "tool_right_answer_wrong", model=GM, task="simulate", arm="S") if res else {}
        r.check("a refused classification is counted as not classified and does not halt",
                code == 0 and (g["n_lost"], g["n_lost_frozen"], g["not_classified"],
                               g["why_frozen"]) == (4, 4, 1, {"REFUSED_OR_CLIPPED_FINAL": 3}),
                (err[-300:], g))
    finally:
        M.E4.classify = real_classify


def test_cap_units(r):
    """`check_tool_row_caps` on single rows (solve cap 8192, simulate 6144)."""
    spec = M.matched_spec(M.SMOKE, Q9, "T", BF.RUN_TAG)

    def row(task, done="stop", **tok):
        d = BF.make_row(Q9, task, "d01", 11, "right" if task == "solve" else "trace", True)
        d["tokens"].update(tok)
        d["done_reason"], d["truncated"] = done, done == "length"
        return S.parse_row({"key": BF.key_of(d), "result": d}, spec, "t")

    def ok(rw):
        try:
            M.check_tool_row_caps([rw], "t")
            return True
        except M.Halt:
            return False
    r.check("two turns may sum above one cap", ok(row("solve", turns=2, completion=12_000)))
    r.check("two turns at exactly twice the cap", ok(row("solve", turns=2, completion=16_384)))
    r.check("two turns above twice the cap is refused",
            not ok(row("solve", turns=2, completion=16_385)))
    r.check("one turn above the cap is refused", not ok(row("solve", turns=1, completion=8_193)))
    r.check("one turn stopped at the cap used exactly the cap",
            ok(row("simulate", "length", turns=1, completion=6_144))
            and not ok(row("simulate", "length", turns=1, completion=6_143)))
    r.check("several turns, the last stopped at the cap: at least the cap in all",
            ok(row("simulate", "length", turns=3, completion=6_500))
            and not ok(row("simulate", "length", turns=3, completion=6_000)))
    r.check("a clipped turn may stop short of the cap",
            ok(row("simulate", "length", turns=2, completion=3_000, ctx_clipped_turns=1,
                   ctx_clip_last_turn_max_tokens=2_000, ctx_clip_last_turn_prompt_tokens=14_000)))
    d = BF.make_row(Q9, "simulate", "d01", 11, "trace", True)
    d.update(response="", done_reason="length", truncated=True)
    d["tokens"].update(turns=2, completion=300, ctx_no_room_turns=1)
    r.check("a refused turn (window full) may stop short of the cap",
            ok(S.parse_row({"key": BF.key_of(d), "result": d}, spec, "t")))


# ------------------------------------------------------------------ tripwires
def _all_rows(path: Path, fn) -> None:
    edit_jsonl(path / "trials.jsonl", lambda recs: [fn(o) for o in recs])


def _rebuild(model, with_tools, pick):
    """Row editor: replace the rows `pick` selects with a builder row of the kind it names."""
    def fn(o):
        res = o["result"]
        kind = pick(res)
        if kind is None:
            return o
        row = BF.make_row(model, res["task"], res["domain_name"], res["prompt_variant"], kind,
                          with_tools, "right", res["problem_name"])
        return {"key": BF.key_of(row), "result": row}
    return fn


def test_tripwires(r):
    # T3: Qwen3.5-9B solve N made all right (60) while cell B of the control stays 40:
    # K1 = +33.3 > 20.
    root = copy_fixture()
    try:
        _all_rows(mdir(root, Q9, "N"),
                  _rebuild(Q9, False, lambda res: "right" if res["task"] == "solve" else None))
        code, err, _, written = run_fixture(root)
        tid = "T3:K1:Qwen3_5_9B:solve"
        r.check("T3 fires and halts", code == 2 and tid in err
                and "+33.3 points from cell B of the control" in err and written == [], err[-500:])
        notes = root / "notes.json"
        notes.write_text(json.dumps({tid: "audited: planted"}))
        code, err, res, _ = run_fixture(root, ["--audited-tripwires", tid,
                                               "--audit-notes", str(notes)])
        r.check("T3 released with an audit note, note recorded",
                code == 0 and res["tripwires_audited"][tid]["note"] == "audited: planted"
                and "audited: planted" in res["_md"], err[-300:])
        code, err, _, _ = run_fixture(root, ["--audited-tripwires", tid])
        r.check("a released tripwire needs a note", code == 2 and "--audit-notes" in err, err)
    finally:
        shutil.rmtree(root.parent)
    # An audit note for a tripwire that did not fire is refused.
    root = copy_fixture()
    try:
        notes = root / "notes.json"
        notes.write_text(json.dumps({"T4:qwen3_6_35b": "x"}))
        code, err, _, _ = run_fixture(root, ["--audited-tripwires", "T4:qwen3_6_35b",
                                             "--audit-notes", str(notes)])
        r.check("a note for a tripwire that did not fire is refused",
                code == 2 and "did not fire" in err, err[-300:])
    finally:
        shutil.rmtree(root.parent)
    # T1: every simulate answer of this run right -> 60 of 60 in all nine cells.
    root = copy_fixture()
    try:
        for m in BF.MODELS:
            for fo in ("N", "T"):
                _all_rows(mdir(root, m, fo), _rebuild(
                    m, fo == "T", lambda res: "trace" if res["task"] == "simulate" else None))
        code, err, _, _ = run_fixture(root)
        r.check("T1 fires (a count the same in all nine cells of a task)",
                code == 2 and "T1:simulate" in err and "T1:solve" not in err
                and "60 of 60" in err, err[-600:])
    finally:
        shutil.rmtree(root.parent)
    # T2: an arm in which no answer is read on ONE task (solve all prose in Qwen3.5-9B N).
    root = copy_fixture()
    try:
        _all_rows(mdir(root, Q9, "N"),
                  _rebuild(Q9, False, lambda res: "prose" if res["task"] == "solve" else None))
        code, err, _, _ = run_fixture(root)
        r.check("T2 fires for the one arm and task with no answer read",
                code == 2 and "T2:Qwen3_5_9B:N:solve" in err
                and "T2:Qwen3_5_9B:N:simulate" not in err and "T2:Qwen3_5_9B:P" not in err,
                err[-600:])
    finally:
        shutil.rmtree(root.parent)
    # T4: a tools arm (model, task, P or S) in which no trial called a tool. The base
    # fixture has an arm with no call on one wording of three (Qwen3.6-35B solve P, v13),
    # which does not fire. Here the other two wordings lose their calls too. The answers
    # stay, so no grade and no other tripwire moves; arm S and simulate keep their calls.
    root = copy_fixture()
    try:
        def no_call(o):
            res = o["result"]
            if res["task"] == "solve" and res["prompt_variant"] in (11, 12, 13):
                res.update(tool_calls=[], success=False, tool_selected=False,
                           failure_reason="tool_not_selected")
            return o
        _all_rows(mdir(root, Q35, "T"), no_call)
        code, err, _, _ = run_fixture(root)
        r.check("T4 fires for the one tools arm and task with no tool call",
                code == 2 and "T4:qwen3_6_35b:P:solve: tools arm P of qwen3_6_35b, solve: no "
                "trial called a tool" in err and err.count("T4:") == 1 and "T3" not in err,
                err[-500:])
    finally:
        shutil.rmtree(root.parent)
    # T5: a fourth unread final answer in Qwen3.6-35B solve N (4 of 60 > 5%).
    root = copy_fixture()
    try:
        set_answer(mdir(root, Q35, "N"), Q35, "solve", "d02", 11, "unread_solve")
        code, err, _, _ = run_fixture(root)
        r.check("T5 fires in arm N above 5% unread final answers",
                code == 2 and "T5:qwen3_6_35b:solve" in err
                and "4 unread final answers of 60 (more than 3)" in err, err[-500:])
    finally:
        shutil.rmtree(root.parent)
    # T5 guards arm N only: the same four unread answers in a tools arm do not fire it.
    root = copy_fixture()
    try:
        for d in ("d01", "d02", "d03", "d04"):
            set_answer(mdir(root, Q35, "T"), Q35, "solve", d, 12, "unread_solve", True)
        code, err, res, _ = run_fixture(root)
        r.check("T5 does not guard a tools arm",
                code == 0 and by(res, "secondary", model=Q35, task="solve",
                                 arm="P")["unread_final_answers"] == 4, err[-400:])
    finally:
        shutil.rmtree(root.parent)
    # T5, the case known in advance: Gemma-26B simulate fires above 90 of 300, here above
    # 18 of 60. 18 unread answers (v12, d01..d18) in N and, so that K1 stays at 0, in cell
    # B of the control with its filed counts: no tripwire. A 19th fires it.
    for n_unread, fires in ((18, False), (19, True)):
        root = copy_fixture()
        try:
            doms = BF.DOMAINS[:18]
            for path in (mdir(root, GM, "N"), bdir(root, GM)):
                for d in doms:
                    set_answer(path, GM, "simulate", d, 12, "unread_sim")
            if n_unread == 19:
                set_answer(mdir(root, GM, "N"), GM, "simulate", "d19", 12, "unread_sim")
            edit_json(root / "filed_control.json", lambda d: [
                (c["frozen"].update(right=42), c["second"].update(right=42),
                 c["folded"].update(right=42)) for c in d["rates"]
                if (c["model"], c["task"]) == (GM, "simulate")])
            code, err, res, _ = run_fixture(root)
            if fires:
                r.check("T5, Gemma simulate: 19 of 60 fires (above 18)",
                        code == 2 and "T5:gemma4_26b-a4b:simulate" in err
                        and "19 unread final answers of 60 (more than 18)" in err, err[-500:])
            else:
                r.check("T5, Gemma simulate: 18 of 60 does not fire (the known case)",
                        code == 0 and by(res, "secondary", model=GM, task="simulate",
                                         arm="N")["unread_final_answers"] == 18, err[-500:])
        finally:
            shutil.rmtree(root.parent)
    r.check_eq("the known case scales to 90 of 300 on the registered design",
               (M.unread_limit(M.REGISTERED, GM, "simulate"),
                M.unread_limit(M.REGISTERED, GM, "solve"),
                M.unread_limit(M.REGISTERED, Q9, "simulate")), (90.0, 15.0, 15.0))


# ------------------------------------------------------------------ the VOID rerun tag
def test_r2(r):
    """Section 7: a VOID cell sends both cells of the model to the run tag matched-run-r2."""
    def make_r2(root, model):
        BF.write_cell(root / "matched", root / "serve_logs", model, "N", BF.R2_TAG, "26000091",
                      BF.n_rows(model))
        BF.write_cell(root / "matched", root / "serve_logs", model, "T", BF.R2_TAG, "26000092",
                      BF.tools_rows(model))
    root = copy_fixture()
    try:
        make_r2(root, Q9)
        code, err, _, _ = run_fixture(root, ["--r2-models", Q9])
        r.check("the second run is not read when the first run is not VOID",
                code == 2 and "no cell of the first run is VOID" in err, err[-300:])
        _exceptions(Q9, "N", 1, False)(root)              # first run: 2 of 120 -> VOID
        code, err, _, _ = run_fixture(root)
        r.check("a VOID first run halts without --r2-models", code == 2 and "VOID" in err, err)
        code, err, res, _ = run_fixture(root, ["--r2-models", Q9])
        r.check("with a VOID first run the model's two cells are read under the r2 tag",
                code == 0 and res["run_tags"] == {Q9: BF.R2_TAG, GM: BF.RUN_TAG, Q35: BF.RUN_TAG}
                and "VOID (section 7)" in res["first_run_void"][Q9]
                and {c["cell"] for c in res["corpus"]} >= {BF.folder(Q9, "N", BF.R2_TAG),
                                                            BF.folder(Q9, "T", BF.R2_TAG)},
                err[-300:])
        code, err, _, _ = run_fixture(root, ["--r2-models", "Qwen3_5_4B"])
        r.check("an unknown model tag is refused", code == 2 and "unknown model tags" in err, err)
        shutil.rmtree(mdir(root, Q9, "T"))
        code, err, _, _ = run_fixture(root, ["--r2-models", Q9])
        r.check("a first run that cannot be read is not taken as VOID",
                code == 2 and "the first run cannot be read" in err, err[-300:])
    finally:
        shutil.rmtree(root.parent)


# ------------------------------------------------------------------ live and dry-run gates
def test_live_gate(r):
    out = Path(tempfile.mkdtemp(prefix="mr_live_"))
    try:
        base = ["--matched-root", "/nonexistent/matched", "--results", "/nonexistent",
                "--marketplace", "/nonexistent", "--out", str(out), "--run-dates", "x",
                "--tools-repo-checked-by-hand", "x", "--version-checked-by-hand", "x"]
        code, err, _ = run_main(base)
        r.check("live without --i-have-frozen reads nothing",
                code == 2 and "refusing to read the matched run" in err, err)
        code, err, _ = run_main(base + ["--i-have-frozen", "0" * 64])
        r.check("live with a wrong hash reads nothing",
                code == 2 and "refusing to read the matched run" in err, err)
        code, err, _ = run_main(base + ["--i-have-frozen", CPF.package_sha256()])
        r.check("the control's hash does not open the matched run",
                code == 2 and "refusing to read the matched run" in err, err)
        r.check_eq("nothing written", list(out.iterdir()), [])
        code, err, _ = run_main(base + ["--i-have-frozen", M.package_sha256()])
        r.check("with the right hash it goes on to read the matched run (and finds none)",
                code == 2 and "refusing" not in err and "/nonexistent/matched" in err, err)
        # The dry run reads existing data only and never writes beside the real output.
        code, err, _ = run_main(["--dry-run-existing", "--marketplace", "/nonexistent"])
        r.check("the dry run refuses the real output folder",
                code == 2 and "needs its own --out" in err, err)
        code, err, _ = run_main(["--dry-run-existing", "--out", str(out)])
        r.check("the dry run needs the validator checkout",
                code == 2 and "requires --marketplace" in err, err)
        code, err, _ = run_main(["--dry-run-existing", "--out", str(out), "--numbers",
                                 "--marketplace", "/nonexistent"])
        r.check("the dry run never writes NUMBERS.md",
                code == 2 and "--numbers is for live mode only" in err, err)
        r.check_eq("still nothing written", list(out.iterdir()), [])
    finally:
        shutil.rmtree(out)


def test_package_hash(r):
    r.check_eq("DEPENDENCIES sorted, no duplicates", list(M.DEPENDENCIES),
               sorted(set(M.DEPENDENCIES)))
    listed = {rel for rel, _ in M.frozen_files()}
    r.check("the frozen rerun package and its dependencies are listed",
            {rel for rel, _ in RUN.frozen_files()} <= listed)
    r.check("the control's script and every file it hashes are listed",
            {rel for rel, _ in CPF.frozen_files()} <= listed)
    r.check("the script itself is hashed", M.SCRIPT in listed)
    for d in ("tools/reanalysis/control_prompt_fix.py", "tools/reanalysis/rq23_metrics.py",
              "tools/reanalysis/rq1_control_metrics.py", "tools/reanalysis/bc_common.py",
              "tools/reanalysis/rq1_layout_regrade.py", "tools/reanalysis/rq3_context_pilot.py",
              "tools/delivered_rerun/schema.py", "tools/delivered_rerun/stats.py"):
        r.check(f"listed: {d}", d in listed)
    r.check("every listed file exists", all(p.is_file() for _, p in M.frozen_files()))
    # Every repo module the script imports, in a fresh interpreter.
    code = ("import os, sys; import tools.reanalysis.matched_run as M; "
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
    r.check("the matched run's hash is not the control's", h != CPF.package_sha256())
    r.check_eq("the frozen rerun package hash is unchanged", RUN.package_sha256(), FROZEN_RERUN_SHA)
    r.check_eq("the control's package hash is unchanged", CPF.package_sha256(), FROZEN_CONTROL_SHA)
    proc = subprocess.run([sys.executable, "-m", "tools.reanalysis.matched_run",
                           "--print-package-hash"], cwd=REPO_ROOT, capture_output=True, text=True)
    r.check("--print-package-hash prints the hash last",
            proc.returncode == 0 and proc.stdout.strip().splitlines()[-1].startswith(h), proc.stderr)
    proc = subprocess.run([sys.executable, "-O", "-m", "tools.reanalysis.matched_run",
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
        "ARMS": ("N", "S", "P"),
        "ARM_WORDINGS": {"N": (11, 12, 13), "P": (11, 12, 13), "S": (11, 12, 13)},
        "FOLDERS": ("N", "P", "S"), "ARM_FOLDER": {"N": "N", "P": "N", "S": "T"},
        "CELL_TOKENS": {"N": "no-tools", "T": "tools_all_minimal"},
        "FOLDER_WORDINGS": {"N": (11, 12, 13), "T": (11, 12, 13)},
        "CONTROL_CELL": "A",
        "N_SYSTEM_SHA256": {**M.N_SYSTEM_SHA256, "solve": CPF.SYSTEM_SHA256["O"]["solve"]},
        "TOOLS_SYSTEM_SHA256": {**M.TOOLS_SYSTEM_SHA256, "simulate": "0" * 64},
        "TOOLS_AUDIT_MODE": "format-stated", "TOOLS_SETTINGS_SYSTEM": "registered",
        "MODELS": {**M.MODELS, "Qwen3_5_9B": "Qwen/Qwen3.5-4B"},
        "MODEL_ORDER": ("Qwen3_5_9B", "gemma4_26b-a4b"),
        "TASKS": ("solve", "validate_plan"), "TOTAL_TRIALS": 5_000,
        "TOOLS_REPO_COMMIT": "e428f17", "CONTEXT_WINDOW": 32_768,
        "OUTPUT_CAP": {"solve": 8_192, "simulate": 8_192}, "STORAGE_CAP": 500,
        "VLLM_VERSION": "0.22.0", "RUN_TAG": "matched", "SMOKE_TAG": "matched-smoke",
        "R2_TAG": "matched-run-r3", "RERUN_PACKAGE": "0" * 64, "CONTROL_PACKAGE": "0" * 64,
        "PYVALIDATOR": "0.1.6", "GRADES": ("registered", "frozen"),
        "REGISTERED_GRADE": "frozen", "DESCRIPTIVE_GRADES": ("frozen",),
        "CONTRASTS": {"M1": ("P", "N"), "M2": ("N", "S"), "M3": ("P", "S")},
        "CONTINUITY": {"K1": ("B", "N"), "K2": ("steered", "P"), "K3": ("plain", "S")},
        "N_CONTRASTS": 24, "N_CONTINUITY": 6, "STEER_OFFSET": 0,
        "MARGIN": 4.0, "LEVEL": 0.90, "B_BOOT": 1_000, "SEED": 1, "HOLM_FAMILY": 18,
        "HOLM_ALPHA": 0.10, "PART_A_DATES": "2026-10-03", "CONTROL_DATES": "2026-11-23",
        "SMOKE_NONEMPTY": 0.90, "VOID_FRAC": 0.05, "TRIPWIRE_POINTS": 10.0, "UNREAD_FRAC": 0.10,
        "UNREAD_KNOWN": ("gemma4_26b-a4b", "solve"), "UNREAD_KNOWN_COUNT": 52,
        "UNREAD_KNOWN_OF": 600, "UNREAD_KNOWN_CONTROL": 90,
        "KEY_PLAN_DIFFERS": M.KEY_PLAN_DIFFERS[:5], "KEY_PLAN_DIFFERS_TRIALS": 6,
        "INPUT_SHA256": {**M.INPUT_SHA256, "control_json": "0" * 64},
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
    for field, value in (("per_task_arm", 299), ("n_folder", 599), ("tools_folder", 1_199),
                         ("per_wording", 199), ("per_task_wording", 99), ("k_domains", 19)):
        d = dataclasses.replace(M.REGISTERED, **{field: value})
        try:
            M.check_design(d, registered=True)
            r.check(f"design {field}={value} is caught", False)
        except C.RegisteredCheckFailed:
            r.check(f"design {field}={value} is caught", True)
    try:
        M.check_design(dataclasses.replace(M.REGISTERED), registered=True)
        r.check("a copy of REGISTERED is not REGISTERED", False)
    except C.RegisteredCheckFailed:
        r.check("a copy of REGISTERED is not REGISTERED", True)
    r.check_eq("smoke: 120 and 240 rows", (M.SMOKE.n_folder, M.SMOKE.tools_folder), (120, 240))
    r.check_eq("folder names",
               (M.folder_name(Q9, "N", M.RUN_TAG), M.folder_name(GM, "T", M.RUN_TAG)),
               ("slurm_vllm_Qwen3_5_9B_off_no-tools-sysformat_matched-run",
                "slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_matched-run"))
    n, t = M.matched_spec(M.REGISTERED, Q9, "N", M.RUN_TAG), M.matched_spec(M.REGISTERED, Q9, "T",
                                                                             M.RUN_TAG)
    r.check_eq("N spec: 600 rows, 200 per wording, 100 per task and wording, no tools",
               (n.n_rows, n.per_variant, n.per_task_variant, n.variants, n.with_tools, n.tasks),
               (600, 200, {"solve": 100, "simulate": 100}, (11, 12, 13), False,
                ("solve", "simulate")))
    r.check_eq("tools spec: 1,200 rows, 200 per wording, six wordings, tools",
               (t.n_rows, t.per_variant, t.per_task_variant, t.variants, t.with_tools,
                t.prompt_style),
               (1200, 200, {"solve": 100, "simulate": 100}, (11, 12, 13, 14, 15, 16), True,
                "minimal"))


# ------------------------------------------------------------------ labels and readings
def test_labels(r):
    def c(lo, hi, ph=0.001, est=0.0):
        return {"est": est, "lo": lo, "hi": hi, "p_holm": ph}
    r.check_eq("M1 above 0", M.label_of("M1", c(0.1, 9)), "tools ahead")
    r.check_eq("M2 below 0", M.label_of("M2", c(-9, -0.1)), "no tools ahead")
    r.check_eq("M1 touching 0", M.label_of("M1", c(0.0, 9)), NDS)
    r.check_eq("M1 not after Holm", M.label_of("M1", c(0.1, 9, 0.05)),
               "tools ahead (not after Holm)")
    r.check_eq("M3 above 0", M.label_of("M3", c(0.1, 9)), "naming the tool helps")
    r.check_eq("M3 below 0", M.label_of("M3", c(-9, -0.1)), "naming the tool hurts")
    r.check_eq("M3 includes 0", M.label_of("M3", c(-1, 1)), NDS)
    r.check_eq("M3 not after Holm", M.label_of("M3", c(0.1, 9, 0.2)),
               "naming the tool helps (not after Holm)")
    r.check_eq("K inside the margin, endpoints included", M.label_of("K1", c(-5.0, 5.0)), MET)
    r.check_eq("K just outside the margin", M.label_of("K2", c(-5.01, 5.0)), "unresolved")
    r.check_eq("K excludes 0 and inside the margin: both labels",
               M.label_of("K3", c(1.0, 4.0)), "criterion met; a difference is shown")
    r.check_eq("K excludes 0, outside the margin", M.label_of("K1", c(6.0, 30.0)),
               "a difference is shown")
    r.check_eq("K excludes 0, not after Holm", M.label_of("K1", c(6.0, 30.0, 0.5)),
               "a difference is shown (not after Holm)")
    # Q1: labels that differ only by the Holm words do not differ.
    a = {**c(1, 9), "label": "tools ahead"}
    b = {**c(1, 9), "label": "tools ahead (not after Holm)"}
    z = {**c(-1, 1), "label": NDS}
    r.check_eq("Q1: same answer with and without the Holm words",
               M.q1_reading(a, b, z)["differ"], False)
    q = M.q1_reading(a, z, {**c(-9, -1), "label": "naming the tool hurts"})
    r.check_eq("Q1: different answers bring M3 in", (q["differ"], q["naming_the_tool"]),
               (True, "naming the tool hurts"))
    r.check_eq("Q2 met", M.q2_reading("K1", {**c(-2, 2), "label": MET}, "d")["criterion_met"], True)
    r.check_eq("Q2 not met",
               M.q2_reading("K3", {**c(-2, 7), "label": "unresolved"}, "d")["criterion_met"], False)


# ------------------------------------------------------------------ smoke check
def smoke_run(root: Path, extra: list[str] | None = None, repo_note: bool = True):
    args = ["--smoke-check", str(root)]
    if repo_note:
        args += ["--tools-repo-checked-by-hand", REPO_NOTE]
    code, err, out = run_main(args + (extra or []))
    return code, out + err


def sdir(root: Path, model: str, fo: str) -> Path:
    return root / BF.folder(model, fo, BF.SMOKE_TAG)


def test_smoke(r):
    base = Path(tempfile.mkdtemp(prefix="mr_smoke_"))
    try:
        BF.build_smoke(base / "clean")
        logs = ["--serve-logs", str(base / "clean" / "serve_logs")]
        code, out = smoke_run(base / "clean", logs)
        r.check("a clean smoke passes", code == 0 and "RESULT: PASS" in out, out[-600:])
        r.check("all seven items print PASS",
                all(f"item {i}: PASS" in out for i in range(1, 8)), out)
        r.check("six cell folders, 120 and 240 rows",
                out.count(": 120\n") == 3 and out.count(": 240\n") == 3
                and "6 cell folders" in out, out)
        # Section 7: no success rate, no failure-reason count, no tool-call count, no answer.
        low = out.lower()
        r.check("the smoke check prints no rate, reason, tool-call count or answer text",
                not any(w in low for w in ("right", "success", "failure_reason", "plan_valid",
                                           "tool_not_selected", "tool call", "(go l1 l2)",
                                           "trajectory", "called"))
                and out.count("%") == 1, out)
        code, out = smoke_run(base / "clean", logs, repo_note=False)
        r.check("item 7: the tools repo needs a note",
                code == 1 and "tools repo at 5e4f9c0: NOT CHECKED" in out, out[-400:])
        code, out = smoke_run(base / "clean")
        r.check("item 7: the vLLM version needs logs or a note",
                code == 1 and "item 7: NOT CHECKED" in out, out[-400:])
        code, out = smoke_run(base / "clean", ["--version-checked-by-hand", "banners read"])
        r.check("item 7 by hand passes", code == 0 and "checked by hand" in out, out[-400:])

        def case(label, mutate, item, needle):
            root = base / label.replace(" ", "_")
            shutil.copytree(base / "clean", root)
            mutate(root)
            code, out = smoke_run(root, ["--serve-logs", str(root / "serve_logs")])
            r.check(f"smoke: {label}", code == 1 and f"item {item}: FAIL" in out
                    and needle in out and "RESULT: FAIL" in out, out[-700:])

        case("a short tools folder",
             lambda root: edit_jsonl(sdir(root, Q9, "T") / "trials.jsonl", lambda x: x[:-1]),
             1, "239 rows, registered 240")
        case("a missing folder", lambda root: shutil.rmtree(sdir(root, GM, "N")), 1,
             "cell folder not found")
        case("an exception row",
             lambda root: set_answer(sdir(root, Q9, "N"), Q9, "solve", "d01", 11, "exception"),
             2, "exception or infrastructure-failure rows")

        def torn(root):
            with (sdir(root, Q9, "T") / "trials.jsonl").open("a") as fh:
                fh.write('{"key": ["half')
        case("a half-written line", torn, 2, "a torn line")

        def empty(fo, n):
            def mut(root):
                def fn(recs):
                    for o in recs[:n]:
                        o["result"]["response"] = ""
                    return recs
                edit_jsonl(sdir(root, GM, fo) / "trials.jsonl", fn)
            return mut
        # 120 rows: 114 non-empty is exactly 95% (passes), 113 is below.
        case("N cell: fewer than 95% non-empty answers", empty("N", 7), 3,
             "fewer than 95% of the stored answers are non-empty")
        root = base / "six_empty"
        shutil.copytree(base / "clean", root)
        empty("N", 6)(root)
        code, out = smoke_run(root, ["--serve-logs", str(root / "serve_logs")])
        r.check("smoke: exactly 95% non-empty passes", code == 0, out[-400:])
        # 240 rows, none with a full window: 228 is 95%; 13 empty answers leave 227.
        case("tools cell: fewer than 95% non-empty answers", empty("T", 13), 3,
             "fewer than 95% of the stored answers are non-empty among the trials whose "
             "final turn was not refused or clipped for a full window")

        # The same 13 empty answers, and 60 more, as trials whose final turn was refused
        # because the prompt and the tool output filled the window: they leave the base
        # (240 - 73 = 167 trials, all non-empty), so the item passes. A plain 95% rule
        # would fail here (167 of 240 = 70%).
        def window_full(n, clipped=False):
            def mut(root):
                def fn(recs):
                    for o in recs[:n]:
                        res = o["result"]
                        res.update(response="", done_reason="length", truncated=True)
                        if clipped:
                            res["tokens"].update(ctx_clipped_turns=1,
                                                 ctx_clip_last_turn_max_tokens=100,
                                                 ctx_clip_last_turn_prompt_tokens=16_000)
                        else:
                            res["tokens"].update(ctx_no_room_turns=1)
                    return recs
                edit_jsonl(sdir(root, GM, "T") / "trials.jsonl", fn)
            return mut
        for label, mut in (("refused", window_full(73)), ("clipped", window_full(73, True))):
            root = base / f"full_{label}"
            shutil.copytree(base / "clean", root)
            mut(root)
            code, out = smoke_run(root, ["--serve-logs", str(root / "serve_logs")])
            r.check(f"smoke: empty answers of {label} final turns do not count in a tools cell",
                    code == 0 and "item 3: PASS" in out, out[-500:])
        # The item cannot pass on nothing: every simulate trial of a tools cell refused
        # for a full window leaves no simulate trial to look at.
        def all_simulate_full(root):
            def fn(recs):
                for o in recs:
                    res = o["result"]
                    if res["task"] == "simulate":
                        res.update(response="", done_reason="length", truncated=True)
                        res["tokens"].update(ctx_no_room_turns=1)
                return recs
            edit_jsonl(sdir(root, GM, "T") / "trials.jsonl", fn)
        case("tools cell: no simulate trial with room", all_simulate_full, 3,
             "or a task has no such trial")
        # An N cell has no such exemption: the same rows in an N cell are plain empty answers.
        spec = M.matched_spec(M.SMOKE, GM, "T", BF.SMOKE_TAG)
        d = BF.make_row(GM, "simulate", "d01", 11, "trace", True)
        d.update(response="", done_reason="length", truncated=True)
        d["tokens"].update(ctx_no_room_turns=1)
        row = S.parse_row({"key": BF.key_of(d), "result": d}, spec, "t")
        ok_rows = [S.parse_row({"key": BF.key_of(x), "result": x}, spec, "t") for x in (
            BF.make_row(GM, "solve", "d01", 11, "right", True),
            BF.make_row(GM, "simulate", "d02", 11, "trace", True))]
        r.check_eq("window_full: a refused turn; the rule per folder",
                   (M.window_full(row), M.nonempty_enough("T", [row] + ok_rows),
                    M.nonempty_enough("T", [row]), M.nonempty_enough("N", [row])),
                   (True, True, False, False))
        d2 = BF.make_row(GM, "simulate", "d01", 11, "trace", True)
        d2.update(response="", done_reason="stop")
        r.check_eq("window_full: an empty answer that stopped by itself is not window-full",
                   M.window_full(S.parse_row({"key": BF.key_of(d2), "result": d2}, spec, "t")),
                   False)
        case("audit: another system text in a tools cell",
             lambda root: edit_jsonl(sdir(root, Q9, "T") / "system_prompt_audit.jsonl",
                                     _set_line(4, system_sha256="0" * 64)),
             4, "is not the with-tools text of Part A")
        case("audit: a tools cell marked swapped",
             lambda root: edit_jsonl(sdir(root, Q9, "T") / "system_prompt_audit.jsonl",
                                     _set_line(4, swapped=True)), 4, "swapped=True")
        case("a user message of N not sent in the tools cell",
             lambda root: edit_jsonl(sdir(root, Q9, "N") / "system_prompt_audit.jsonl",
                                     _set_line(4, user_sha256="b" * 64)),
             5, "are not sent in the tools cell")

        def other_problem(root):
            def fn(recs):
                for o in recs:
                    if (o["result"]["task"], o["result"]["domain_name"]) == ("solve", "d09"):
                        o["result"]["problem_name"] = "p02"
                        o["key"][3] = "p02"
                return recs
            edit_jsonl(sdir(root, Q9, "N") / "trials.jsonl", fn)
        case("N and tools cells hold different problems", other_problem, 5,
             "do not hold the same solve problems")
        case("a request of a tools cell without tools",
             lambda root: edit_jsonl(sdir(root, GM, "T") / "system_prompt_audit.jsonl",
                                     _set_line(4, has_tools=False)), 6, "without tools")
        case("a request of an N cell with tools",
             lambda root: edit_jsonl(sdir(root, GM, "N") / "system_prompt_audit.jsonl",
                                     _set_line(4, has_tools=True)), 6, "has tools")
        case("client_settings.json of a tools cell names a no-tools text",
             lambda root: edit_json(sdir(root, GM, "T") / "client_settings.json",
                                    lambda s: s.update(no_tools_system="format-stated")),
             6, "no_tools_system='format-stated'")

        def version(root):
            p = root / "serve_logs" / f"27000003-vllm-{GM}.log"
            p.write_text(p.read_text().replace("v0.20.2", "v0.22.0"))
        case("another vLLM version", version, 7, "shows vLLM ['0.22.0']")
        # The smoke is never analysed: its folders carry the smoke tag, which the
        # analysis does not read.
        out_dir = Path(tempfile.mkdtemp(prefix="mr_smoke_out_"))
        code, err, _ = run_main(["--matched-root", str(base / "clean"), "--results", "/nonexistent",
                                 "--marketplace", "/nonexistent", "--out", str(out_dir),
                                 "--run-dates", "x", "--tools-repo-checked-by-hand", "x",
                                 "--version-checked-by-hand", "x",
                                 "--i-have-frozen", M.package_sha256()])
        r.check("the analysis does not read smoke folders",
                code == 2 and "cell folder not found" in err and list(out_dir.iterdir()) == [],
                err[-300:])
        shutil.rmtree(out_dir)
    finally:
        shutil.rmtree(base)


def main():
    r = TestResults("matched_run")
    test_fixture_is_builder_output(r)
    test_planted_answers(r)
    test_base(r)
    test_refusals(r)
    test_units(r)
    test_cap_units(r)
    test_tripwires(r)
    test_r2(r)
    test_live_gate(r)
    test_package_hash(r)
    test_constants(r)
    test_labels(r)
    test_smoke(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
