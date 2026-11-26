"""Freeze gate 4 for the Claude-run analysis (tools/reanalysis/frontier55.py).

Run standalone: `python3 tests/test_frontier55_analysis.py`
Or: `python3 -m pytest tests/test_frontier55_analysis.py`

The synthetic fixture (tests/fixtures/frontier55/, built by its build_fixture.py) has 60
trials per model, arm and task, 3 per domain, over 20 domains d01..d20, and a sidecar line
per trial. Every expected number below is hand-computed from the plants of
build_fixture.py; the derivation is in the comment next to it.

Bootstrap arithmetic used below (frozen `cluster_bootstrap`: 20 domains drawn with
replacement, ratio estimator; every domain holds 3 trials of a task in an arm, so a draw's
value is (sum over the drawn domains) / 60). The draws depend only on the seed and on
k = 20, so these patterns are the ones the control's and the matched run's tests use:
  * every domain has the same value d: every draw gives d, the interval is [d, d];
  * one domain with sum s, the rest 0: a draw gives s*X/60 with X ~ Bin(20, 1/20).
    P(X = 0) = 0.358, so the 2.5% quantile is 0; P(X >= 3) = 0.0755 and
    P(X >= 4) = 0.0159, so the 97.5% quantile is X = 3: the interval is [0, 3s/60]
    (s = 3: [0, 15.0]; s = -3: [-15.0, 0]);
  * four domains with sum +1: X ~ Bin(20, 4/20). P(X <= 1) = 0.0692 and P(X = 0) =
    0.0115, so the 2.5% quantile is X = 1; P(X >= 8) = 0.0321 and P(X >= 9) = 0.0100, so
    the 97.5% quantile is X = 8: [1/60, 8/60], in points [1.667, 13.333]; with sum -1 the
    interval is mirrored.
  A rate is the same arithmetic on the wrong answers: one domain with 0 of 3 right gives
  [100 - 15, 100] = [85.0, 100.0]; four domains with 2 of 3 right give [86.667, 98.333].
Sign-flip p (exact, over the 20 domain sums): 20 equal non-zero sums give 2/2^20 =
1.9073e-06; m equal non-zero sums and the rest 0 give 2/2^m (m = 1: 1.0; m = 4: 0.125);
all zero gives 1.0.

No row of any real corpus is read here. Nothing under results/frontier55 or
results/frontier55-pilot is opened; the one real file a test may read is the pinned
ground-truth cache (results/derived/gt_cache.json), to check the registered trial list.
"""
from __future__ import annotations

import asyncio
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
from tools.delivered_rerun import stats as ST  # noqa: E402
from tools.reanalysis import control_prompt_fix as CPF  # noqa: E402
from tools.reanalysis import frontier55 as F  # noqa: E402
from tools.reanalysis import matched_run as MR  # noqa: E402
from tools.reanalysis import rq1_layout_regrade as RG  # noqa: E402
from tools.reanalysis import rq3_context_pilot as PILOT  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "frontier55"


def _load_builder():
    """The fixture builders are all called build_fixture.py; load this one by path."""
    name = "frontier55_build_fixture"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, FIXTURE / "build_fixture.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


BF = _load_builder()
HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
N, T = "no-tools", "tools"
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
EPS = 1e-9
P20 = 2 / 2 ** 20                 # 20 equal non-zero domain sums
FROZEN_RERUN_SHA = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"
FROZEN_CONTROL_SHA = "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79"
FROZEN_MATCHED_SHA = "1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d"
NDS, AHEAD, BEHIND = "no difference shown", "tools ahead", "no tools ahead"
NAH = " (not after Holm)"


def close(a, b):
    return a is not None and b is not None and abs(a - b) < EPS


# ------------------------------------------------------------------ helpers
def run_main(args: list[str]) -> tuple[int, str, str]:
    err, out = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        code = F.main(args)
    return code, err.getvalue(), out.getvalue()


def run_fixture(root: Path, extra: list[str] | None = None):
    out = Path(tempfile.mkdtemp(prefix="f55_out_"))
    code, err, _ = run_main(["--fixture", str(root), "--out", str(out)] + (extra or []))
    res = None
    if code == 0:
        res = json.loads((out / "frontier55.json").read_text())
        res["_md"] = (out / "frontier55.md").read_text()
    written = sorted(p.name for p in out.iterdir())
    shutil.rmtree(out)
    return code, err, res, written


def copy_fixture() -> Path:
    dst = Path(tempfile.mkdtemp(prefix="f55_fx_")) / "fx"
    shutil.copytree(FIXTURE, dst)
    return dst


def cdir(root: Path, model: str, arm: str) -> Path:
    return root / "frontier55" / f"{model}_{arm}"


def read_lines(path: Path) -> list[dict]:
    """A JSON-lines file; a half-written line (the fixture plants two) is dropped."""
    out = []
    for ln in path.read_text().splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            out.append(json.loads(ln))
    return out


def write_lines(path: Path, recs: list[dict]) -> None:
    path.write_text("".join(json.dumps(x) + "\n" for x in recs))


def edit(root: Path, model: str, arm: str, rows=None, metas=None) -> None:
    """Rewrite a folder's rows and sidecar lines through the two functions."""
    d = cdir(root, model, arm)
    if rows is not None:
        write_lines(d / "trials.jsonl", rows(read_lines(d / "trials.jsonl")))
    if metas is not None:
        write_lines(d / "trial_meta.jsonl", metas(read_lines(d / "trial_meta.jsonl")))


def key_of(model, arm, task, dom, slot) -> list:
    prob, label, v = BF.slots(task, dom)[slot]
    return [model, task, dom, prob, label, v, arm == T, "off", "all", "minimal"]


def replant(root: Path, model: str, arm: str, task: str, dom: str, slot: int, spec) -> None:
    """Replace one trial (its row and its sidecar line) by the builder's trial for `spec`."""
    row, meta = BF.make_trial(model, arm, task, dom, slot, BF.Clock(model), spec)
    k = row["key"]
    edit(root, model, arm,
         rows=lambda rs: [row if x["key"] == k else x for x in rs],
         metas=lambda ms: [meta if x["key"] == k else x for x in ms])


def on_meta(root: Path, model: str, arm: str, task: str, dom: str, slot: int, fn) -> None:
    k = key_of(model, arm, task, dom, slot)

    def go(ms):
        for x in ms:
            if x["key"] == k:
                fn(x)
        return ms
    edit(root, model, arm, metas=go)


def on_row(root: Path, model: str, arm: str, task: str, dom: str, slot: int, fn) -> None:
    k = key_of(model, arm, task, dom, slot)

    def go(rs):
        for x in rs:
            if x["key"] == k:
                fn(x)
        return rs
    edit(root, model, arm, rows=go)


def by(res: dict, table: str, **kw) -> dict:
    hits = [e for e in res[table] if all(e[k] == v for k, v in kw.items())]
    assert len(hits) == 1, (table, kw, len(hits))
    return hits[0]


def halts(r, label: str, mutate, needle: str, extra: list[str] | None = None) -> None:
    """A mutated copy of the fixture is refused: exit 2, the message, nothing written."""
    root = copy_fixture()
    try:
        mutate(root)
        code, err, _res, written = run_fixture(root, extra)
        r.check(label, code == 2 and needle in err and written == [],
                f"code={code} written={written} err={err[-400:]}")
    finally:
        shutil.rmtree(root.parent)


def load_fixture_cells(root: Path = FIXTURE) -> dict:
    gt = json.loads((root / "gt_cache.json").read_text())
    return F.load_run(root / "frontier55", F.fixture_design(root), gt,
                      F.file_sha256(root / "gt_cache.json", "gt"), CPF.fixture_domains(root))


def on_manifest(root: Path, model: str, arm: str, fn) -> None:
    path = cdir(root, model, arm) / "run_manifest.json"
    m = json.loads(path.read_text())
    fn(m)
    path.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def fixture_verdict(root: Path = FIXTURE) -> CPF.Verdicts:
    return CPF.Verdicts(CPF.table_route(RUN.fixture_verdicts(root / "route")))


# ------------------------------------------------------------------ the fixture is the builder's output
def test_fixture_is_builder_output(r):
    tmp = Path(tempfile.mkdtemp(prefix="f55_build_"))
    try:
        BF.build(tmp)
        got = {p.relative_to(tmp).as_posix(): p.read_bytes() for p in tmp.rglob("*") if p.is_file()}
        want = {p.relative_to(FIXTURE).as_posix(): p.read_bytes() for p in FIXTURE.rglob("*")
                if p.is_file() and p.name != "build_fixture.py" and "__pycache__" not in p.parts}
        r.check_eq("fixture files = builder output (names)", sorted(got), sorted(want))
        r.check("fixture files = builder output (bytes)",
                all(got[k] == want.get(k) for k in got),
                [k for k in got if got[k] != want.get(k)][:5])
    finally:
        shutil.rmtree(tmp)
    # The layout the hand arithmetic relies on.
    for task in TASKS:
        per_wording = {v: 0 for v in BF.WORDINGS}
        for d in BF.DOMAINS:
            trio = BF.slots(task, d)
            r.check(f"{task} {d}: three different trials", len(set(trio)) == 3)
            for _p, _l, v in trio:
                per_wording[v] += 1
        r.check_eq(f"{task}: 20 rows per wording", per_wording, {11: 20, 12: 20, 13: 20})
    # d19 and d20: a key without the problem (or without the plan label) would collide.
    r.check("solve d19: two problems on one wording",
            {(p, v) for p, _l, v in BF.slots("solve", "d19")} >= {("p01", 11), ("p02", 11)})
    r.check("validate_plan d19: two plan labels on one problem and wording",
            {(p, lab, v) for p, lab, v in BF.slots("validate_plan", "d19")}
            >= {("p01", "v1", 11), ("p01", "b1", 11)})
    # Valid and invalid inputs per arm (the denominators of the verdict errors):
    # validate_domain: d01..d18 two valid, one broken (36, 18); d19 two valid, one broken;
    # d20 one valid, two broken: 39 valid, 21 broken. validate_problem: d01..d18 one valid,
    # two broken (18, 36); d19 two valid, one broken; d20 one valid, two broken: 21, 39.
    # validate_plan: as validate_domain (v1 and v2 valid, b1 broken): 39, 21.
    for task, want in (("validate_domain", (39, 21)), ("validate_problem", (21, 39)),
                       ("validate_plan", (39, 21))):
        ts = [BF.truth(task, p, lab) for d in BF.DOMAINS for p, lab, _v in BF.slots(task, d)]
        r.check_eq(f"{task}: valid and broken inputs", (sum(ts), len(ts) - sum(ts)), want)


# ------------------------------------------------------------------ the grade on the planted answers
def test_planted_answers(r):
    """What each planted answer is under the frozen readers, so that the traps are real:
    a pipeline that took another reader would give other numbers."""
    A = BF.ANSWERS
    plan, mode = G.solve_plan(A["json_block"])
    r.check_eq("json_block: the rerun's reader finds no plan", (plan, mode), ((), None))
    r.check_eq("json_block: the last code block holds the plan",
               RG.block_plan(A["json_block"])[0], tuple(BF.PLAN))
    plan, _ = G.solve_plan(A["tried_then_block"])
    r.check_eq("tried_then_block: the rerun's reader takes the tried step too", plan,
               tuple(BF.TRIED))
    r.check_eq("tried_then_block: the last code block is the plan alone",
               RG.block_plan(A["tried_then_block"])[0], tuple(BF.PLAN))
    r.check_eq("caps_block: the block holds the plan in capitals",
               RG.block_plan(A["caps_block"])[0], tuple(BF.CAPS))
    r.check_eq("caps_block and caps_json: lower case is the valid plan",
               (RG.lower(BF.CAPS), G.solve_plan(A["caps_json"])[0]),
               (tuple(BF.PLAN), tuple(BF.CAPS)))
    table = RUN.fixture_verdicts(FIXTURE / "route")
    r.check_eq("route: the plan valid, capitals invalid, the tried plan invalid",
               (table[("d01", "p01", tuple(BF.PLAN))], table[("d01", "p01", tuple(BF.CAPS))],
                table[("d01", "p01", tuple(BF.TRIED))]), (True, False, False))
    full = A["cut_plan"]
    r.check("cut_plan: longer than the storage cap", len(full) > 65_536)
    r.check_eq("cut_plan: its first 65,536 characters hold no plan",
               (G.solve_plan(full[:65_536]), RG.block_plan(full[:65_536])), (((), None), None))
    r.check_eq("cut_plan: the full answer ends with the plan in a code block",
               RG.block_plan(full)[0], tuple(BF.PLAN))
    oracle = [{"step": 1}]
    gt = json.loads((FIXTURE / "gt_cache.json").read_text())
    from tools.e2e_regrade import oracle_canon_for
    oracle = oracle_canon_for(gt, {"domain_name": "d01", "problem_name": "p01"})
    r.check("per_line: the line reader reads the key", PILOT.line_reader_exact(A["per_line"], oracle))
    r.check("per_line_wrong: the line reader reads another trace",
            PILOT.line_reader_steps(A["per_line_wrong"]) is not None
            and not PILOT.line_reader_exact(A["per_line_wrong"], oracle))
    r.check_eq("verdict answers", (G.stated_verdict(BF.answer("ok", "validate_domain", "p01", "")),
                                   G.stated_verdict(BF.answer("wrong", "validate_domain", "p01", "")),
                                   G.stated_verdict(A["no_verdict"])), (True, False, None))


# ------------------------------------------------------------------ the base run
# Right answers of 60, by (model, task): (no tools, tools). Derived from PLANTS:
#   Haiku solve: no tools wrong on the second slot of every domain (20): 40; tools 60 (the
#     storage-cut row is right in its full answer). validate_domain: no tools wrong on the
#     three trials of d01: 57. validate_problem: no tools refused on d01..d04: 56.
#     validate_plan: tools wrong on d01..d04: 56. simulate: no tools 0.
#   Sonnet solve: 60 and 60 (right only under the registered grade on the first slot).
#     validate_domain: tools wrong on the three trials of d02: 57. validate_plan: no tools
#     wrong on the third slot of every domain: 40. simulate: tools wrong on d05..d08: 56.
RIGHT = {
    (HAIKU, "solve"): (40, 60), (HAIKU, "validate_domain"): (57, 60),
    (HAIKU, "validate_problem"): (56, 60), (HAIKU, "validate_plan"): (60, 56),
    (HAIKU, "simulate"): (0, 60),
    (SONNET, "solve"): (60, 60), (SONNET, "validate_domain"): (60, 57),
    (SONNET, "validate_problem"): (60, 60), (SONNET, "validate_plan"): (40, 60),
    (SONNET, "simulate"): (60, 56),
}
# Rate intervals by the number right (see the docstring): 60 -> [100, 100]; 0 -> [0, 0];
# 40 (2 of 3 in every domain) -> [66.667, 66.667]; 57 (one domain 0 of 3) -> [85, 100];
# 56 (four domains 2 of 3) -> [86.667, 98.333].
RATE_CI = {60: (100.0, 100.0), 0: (0.0, 0.0), 40: (200 / 3, 200 / 3), 57: (85.0, 100.0),
           56: (100 - 800 / 60, 100 - 100 / 60)}
# Contrasts, tools minus no tools: (estimate, lo, hi, p, Holm-adjusted p, label, no tools
# wrong and tools right, no tools right and tools wrong).
#   Holm, Haiku (five tasks): p sorted = simulate P20, solve P20, validate_plan 0.125,
#   validate_problem 0.125, validate_domain 1.0 -> 5*P20, max(5*P20, 4*P20), 3*0.125,
#   max(0.375, 2*0.125), max(0.375, 1.0).
#   Holm, Sonnet: validate_plan P20, simulate 0.125, then three of 1.0 -> 5*P20,
#   4*0.125 = 0.5, 1.0, 1.0, 1.0.
CONTRASTS = {
    (HAIKU, "solve"): (100 / 3, 100 / 3, 100 / 3, P20, 5 * P20, AHEAD, 20, 0),
    (HAIKU, "validate_domain"): (5.0, 0.0, 15.0, 1.0, 1.0, NDS, 3, 0),
    (HAIKU, "validate_problem"): (400 / 60, 100 / 60, 800 / 60, 0.125, 0.375, AHEAD + NAH, 4, 0),
    (HAIKU, "validate_plan"): (-400 / 60, -800 / 60, -100 / 60, 0.125, 0.375, BEHIND + NAH, 0, 4),
    (HAIKU, "simulate"): (100.0, 100.0, 100.0, P20, 5 * P20, AHEAD, 60, 0),
    (SONNET, "solve"): (0.0, 0.0, 0.0, 1.0, 1.0, NDS, 0, 0),
    (SONNET, "validate_domain"): (-5.0, -15.0, 0.0, 1.0, 1.0, NDS, 0, 3),
    (SONNET, "validate_problem"): (0.0, 0.0, 0.0, 1.0, 1.0, NDS, 0, 0),
    (SONNET, "validate_plan"): (100 / 3, 100 / 3, 100 / 3, P20, 5 * P20, AHEAD, 20, 0),
    (SONNET, "simulate"): (-400 / 60, -800 / 60, -100 / 60, 0.125, 0.5, BEHIND + NAH, 0, 4),
}
# Verdict errors: (valid inputs, called invalid, no verdict, of which error rows, invalid
# inputs, called valid, no verdict, of which error rows). Cells not listed are all zero.
#   Haiku no tools validate_domain, d01: p01@11 (valid) refused; domain_neg@12 (broken)
#     called valid; p01@13 (valid) called invalid.
#   Haiku no tools validate_problem: p01@11 (valid) refused on d01..d04.
#   Haiku tools validate_plan, v1@11 (valid) on d01..d04: loop exhausted (no verdict), no
#     tool call and called invalid, tool right and called invalid, tool right and no verdict.
#   Sonnet tools validate_domain, d02: p01@11 (valid) a pause; domain_neg@12 (broken) an
#     unknown stop; p01@13 (valid) called invalid.
#   Sonnet no tools validate_plan, wrong on the third slot: d01..d18 v2@13 (valid) and d19
#     v1@12 (valid) called invalid: 19; d20 b1@13 (broken) called valid: 1.
VERDICT_ERRORS = {
    (HAIKU, "validate_domain", N): (39, 1, 1, 1, 21, 1, 0, 0),
    (HAIKU, "validate_problem", N): (21, 0, 4, 4, 39, 0, 0, 0),
    (HAIKU, "validate_plan", T): (39, 2, 2, 0, 21, 0, 0, 0),
    (SONNET, "validate_domain", T): (39, 1, 1, 1, 21, 0, 1, 1),
    (SONNET, "validate_plan", N): (39, 19, 0, 0, 21, 1, 0, 0),
}
VALID_INVALID = {"validate_domain": (39, 21), "validate_problem": (21, 39),
                 "validate_plan": (39, 21)}
# RQ2, the tool arm: (classed, no call, right only, right + other, other only, error rows
# left out, the other planner).
#   Haiku solve: the classic planner on the third slot whatever the domain: right on
#     d01..d10, the other planner on d11..d20 (10 other only). validate_plan: d01 other
#     only (ten calls of another tool), d02 no call, d03 right + other.
#   Sonnet solve: no call on the third slot (20). validate_domain: two error rows left
#     out. simulate: one error row left out (the scoring error), d06 other only.
TOOL_CHOICE = {
    (HAIKU, "solve"): (60, 0, 50, 0, 10, 0, 10), (HAIKU, "validate_domain"): (60, 0, 60, 0, 0, 0, 0),
    (HAIKU, "validate_problem"): (60, 0, 60, 0, 0, 0, 0),
    (HAIKU, "validate_plan"): (60, 1, 57, 1, 1, 0, 0), (HAIKU, "simulate"): (60, 0, 60, 0, 0, 0, 0),
    (SONNET, "solve"): (60, 20, 40, 0, 0, 0, 0), (SONNET, "validate_domain"): (58, 0, 58, 0, 0, 2, 0),
    (SONNET, "validate_problem"): (60, 0, 60, 0, 0, 0, 0),
    (SONNET, "validate_plan"): (60, 0, 60, 0, 0, 0, 0), (SONNET, "simulate"): (59, 0, 58, 0, 1, 1, 0),
}
# RQ3, the tool arm: (tool right, answer wrong, error rows left out).
#   Haiku validate_plan: tool right on all but d01 (another tool) and d02 (no call): 58;
#     answer wrong on d03 and d04: 2. Sonnet solve: 40 trials called the planner.
#     validate_domain: 58 (two error rows left out), d02's third trial wrong: 1.
#     simulate: 59 rows that are not error rows, less d06 (another tool): 58; the two
#     no-room trials d07 and d08 are wrong: 2.
TOOL_RIGHT = {
    (HAIKU, "solve"): (60, 0, 0), (HAIKU, "validate_domain"): (60, 0, 0),
    (HAIKU, "validate_problem"): (60, 0, 0), (HAIKU, "validate_plan"): (58, 2, 0),
    (HAIKU, "simulate"): (60, 0, 0),
    (SONNET, "solve"): (40, 0, 0), (SONNET, "validate_domain"): (58, 1, 2),
    (SONNET, "validate_problem"): (60, 0, 0), (SONNET, "validate_plan"): (60, 0, 0),
    (SONNET, "simulate"): (58, 2, 1),
}


def test_base(r):
    code, err, res, written = run_fixture(FIXTURE)
    r.check("base fixture runs", code == 0, err)
    if res is None:
        return
    r.check_eq("both files written", written, ["frontier55.json", "frontier55.md"])
    r.check_eq("mode, models, arms, tasks", (res["mode"], res["models"], res["arms"], res["tasks"]),
               ("fixture", [HAIKU, SONNET], [N, T], list(TASKS)))
    r.check_eq("package hash recorded", res["package_sha256"], F.package_sha256())
    # RQ1 rates.
    r.check_eq("20 rate rows", len(res["rates"]), 20)
    for (m, t), want in RIGHT.items():
        for arm, k in zip((N, T), want):
            e = by(res, "rates", model=m, task=t, arm=arm)
            lo, hi = RATE_CI[k]
            r.check_eq(f"rate {m}/{t}/{arm}: right of 60, 20 domains",
                       (e["right"], e["n"], e["k"], e["level"]), (k, 60, 20, 0.95))
            r.check(f"rate {m}/{t}/{arm}: estimate and interval",
                    close(e["est"], 100 * k / 60) and close(e["lo"], lo) and close(e["hi"], hi),
                    (e["est"], e["lo"], e["hi"]))
    # RQ1 contrasts.
    r.check_eq("10 contrasts", (len(res["contrasts"]), res["n_contrasts"]), (10, 10))
    for (m, t), (est, lo, hi, p, ph, label, gained, lost) in CONTRASTS.items():
        c = by(res, "contrasts", model=m, task=t)
        r.check(f"contrast {m}/{t}: estimate and interval",
                close(c["est"], est) and close(c["lo"], lo) and close(c["hi"], hi),
                (c["est"], c["lo"], c["hi"]))
        r.check(f"contrast {m}/{t}: sign-flip p and Holm", close(c["p"], p) and close(c["p_holm"], ph),
                (c["p"], c["p_holm"]))
        r.check_eq(f"contrast {m}/{t}: label, pairs, moves",
                   (c["label"], c["n_pairs"], c["unpaired"], c["gained"], c["lost"], c["k"]),
                   (label, 60, 0, gained, lost, 20))
        n_right, t_right = RIGHT[(m, t)]
        r.check(f"contrast {m}/{t}: the difference of the two rates",
                close(c["est"], 100 * (t_right - n_right) / 60))
    # Verdict errors.
    r.check_eq("12 verdict-error rows", len(res["verdict_errors"]), 12)
    for m in (HAIKU, SONNET):
        for t, (nv, nb) in VALID_INVALID.items():
            for arm in (N, T):
                v = by(res, "verdict_errors", model=m, task=t, arm=arm)
                got = (v["valid_inputs"], v["valid_called_invalid"], v["valid_no_verdict"],
                       v["valid_error_rows"], v["invalid_inputs"], v["invalid_called_valid"],
                       v["invalid_no_verdict"], v["invalid_error_rows"])
                r.check_eq(f"verdict errors {m}/{t}/{arm}", got,
                           VERDICT_ERRORS.get((m, t, arm), (nv, 0, 0, 0, nb, 0, 0, 0)))
    # RQ2.
    r.check_eq("10 tool-choice rows", len(res["tool_choice"]), 10)
    for (m, t), (classed, none, only, plus, other, left, planner) in TOOL_CHOICE.items():
        c = by(res, "tool_choice", model=m, task=t)
        got = (c["n_classed"], c["counts"]["none"], c["counts"]["right_only"],
               c["counts"]["right_plus"], c["counts"]["other_only"], c["error_rows_left_out"],
               c["other_planner"])
        r.check_eq(f"tool choice {m}/{t}", got, (classed, none, only, plus, other, left, planner))
        r.check_eq(f"tool choice {m}/{t}: every trial", (c["n_trials"], classed + left), (60, 60))
        r.check(f"tool choice {m}/{t}: share of exactly the right tool",
                close(c["exactly_right"]["est"], 100 * only / classed))
    r.check_eq("error rows left out, by kind",
               (by(res, "tool_choice", model=SONNET, task="validate_domain")["error_rows_by_kind"],
                by(res, "tool_choice", model=SONNET, task="simulate")["error_rows_by_kind"]),
               ({"pause": 1, "unknown stop": 1}, {"scoring error": 1}))
    # RQ3.
    r.check_eq("10 tool-right rows", len(res["tool_right_answer_wrong"]), 10)
    for (m, t), (right, wrong, left) in TOOL_RIGHT.items():
        c = by(res, "tool_right_answer_wrong", model=m, task=t)
        r.check_eq(f"tool right, answer wrong {m}/{t}",
                   (c["n_trials"], c["n_tool_right"], c["n_answer_wrong"], c["error_rows_left_out"]),
                   (60, right, wrong, left))
        r.check(f"tool right, answer wrong {m}/{t}: share",
                close(c["answer_wrong"]["est"], 100 * wrong / right))
    # The interval of a share, from hand-built inputs: Haiku validate_plan. Tool right: two
    # trials in d01 and in d02, three in every other domain; answer wrong: one in d03, one
    # in d04.
    vals, doms = [], []
    for d in BF.DOMAINS:
        for i in range(2 if d in ("d01", "d02") else 3):
            vals.append(float(d in ("d03", "d04") and i == 0))
            doms.append(d)
    b = ST.cluster_bootstrap(vals, doms, 0.95, 20)
    c = by(res, "tool_right_answer_wrong", model=HAIKU, task="validate_plan")["answer_wrong"]
    r.check("share interval, Haiku validate_plan, from hand-built inputs",
            close(c["est"], 100 * 2 / 58) and close(c["lo"], b.lo) and close(c["hi"], b.hi)
            and (c["k"], c["n"]) == (20, 58), c)
    # Sonnet simulate: 58 tool-right trials (d05 and d06 hold two), wrong in d07 and d08.
    vals, doms = [], []
    for d in BF.DOMAINS:
        for i in range(2 if d in ("d05", "d06") else 3):
            vals.append(float(d in ("d07", "d08") and i == 0))
            doms.append(d)
    b = ST.cluster_bootstrap(vals, doms, 0.95, 20)
    c = by(res, "tool_right_answer_wrong", model=SONNET, task="simulate")
    r.check("share interval, Sonnet simulate, from hand-built inputs",
            close(c["answer_wrong"]["lo"], b.lo) and close(c["answer_wrong"]["hi"], b.hi), c)
    r.check_eq("how the wrong answers ended",
               (c["why"], by(res, "tool_right_answer_wrong", model=HAIKU,
                             task="validate_plan")["why"]),
               ({"refused for length (no room)": 2},
                {"no_verdict_stated": 1, "verdict_stated_wrong": 1}))
    _descriptive_checks(r, res)
    _corpus_checks(r, res)


def _descriptive_checks(r, res):
    r.check_eq("20 descriptive rows", len(res["descriptive"]), 20)

    def d(m, arm, t):
        return by(res, "descriptive", model=m, arm=arm, task=t)
    # Right by wording. Haiku no tools solve: wrong on the second slot: v12 in d01..d18,
    # (p02, v11) in d19, (p01, v13) in d20.
    r.check_eq("right by wording, Haiku no tools solve", d(HAIKU, N, "solve")["right_by_wording"],
               {"11": {"right": 19, "n": 20}, "12": {"right": 2, "n": 20},
                "13": {"right": 19, "n": 20}})
    # Sonnet no tools validate_plan: wrong on the third slot: v13 in d01..d18 and d20, v12
    # in d19.
    r.check_eq("right by wording, Sonnet no tools validate_plan",
               d(SONNET, N, "validate_plan")["right_by_wording"],
               {"11": {"right": 20, "n": 20}, "12": {"right": 19, "n": 20},
                "13": {"right": 1, "n": 20}})
    for m in (HAIKU, SONNET):
        for arm in (N, T):
            for t in TASKS:
                e = d(m, arm, t)
                r.check_eq(f"{m}/{arm}/{t}: the endings cover every trial",
                           sum(e["endings"].values()), 60)
                r.check_eq(f"{m}/{arm}/{t}: right by wording sums to the rate",
                           sum(x["right"] for x in e["right_by_wording"].values()),
                           RIGHT[(m, t)][arm == T])
    # Endings.
    e = d(HAIKU, N, "solve")
    r.check_eq("Haiku no tools solve: one answer stopped at the cap, with an answer",
               (e["stopped_at_the_output_cap"], e["stopped_at_the_cap_with_no_answer"],
                e["endings"]["stopped at the cap with an answer"]), (1, 0, 1))
    r.check_eq("Haiku no tools solve: output tokens (59 answers of 10, one of 8,192)",
               (e["output_tokens_total"], e["input_tokens_total"], e["turns_max"]),
               (59 * 10 + 8192, 60_000, 1))
    e = d(SONNET, T, "simulate")
    r.check_eq("Sonnet tools simulate: the think_overflow row is \"stopped at the cap with no "
               "answer\"; two no-room trials; one scoring error",
               (e["stopped_at_the_output_cap"], e["stopped_at_the_cap_with_no_answer"],
                e["labelled_think_overflow_by_the_harness"], e["refused_for_length"],
                e["loop_exhausted"], e["refusals"], e["other_error_rows"]),
               (1, 1, 1, 2, 0, 0, {"pause": 0, "unknown stop": 0, "scoring error": 1}))
    r.check_eq("Sonnet tools simulate: endings", e["endings"], {
        "answer": 56, "empty answer": 0, "stopped at the cap with an answer": 0,
        "stopped at the cap with no answer": 1, "loop exhausted": 0,
        "refused for length (no room)": 2, "refusal": 0, "other error row": 1})
    # 57 trials of two requests (10 output tokens each), the note row 10 + 6,144, the
    # rejected request 10 (one turn), the window stop 20 (two turns).
    r.check_eq("Sonnet tools simulate: turns and tokens",
               (sum(int(k) * v for k, v in e["turns_histogram"].items()), e["output_tokens_total"],
                e["thinking_tokens_total"], e["thinking_blocks"], e["trials_with_a_note"]),
               (57 * 2 + 2 + 1 + 2, 57 * 20 + 6154 + 10 + 20, 7, 1, 1))
    r.check("no ending is called think_overflow", "think_overflow" not in json.dumps(
        [x["endings"] for x in res["descriptive"]]) and "think_overflow" not in json.dumps(
        [x["wrong_by_reason"] for x in res["descriptive"]]))
    r.check_eq("Sonnet tools simulate: reasons of the wrong trials",
               e["wrong_by_reason"], {"exception": 1, "no_room": 2, "truncated_empty": 1})
    e = d(HAIKU, T, "validate_plan")
    # 56 default trials and d03, d04 of two requests; d01 of ten; d02 of one.
    r.check_eq("Haiku tools validate_plan: loop exhausted, turns, tool calls",
               (e["loop_exhausted"], e["turns_max"], e["turns_histogram"], e["input_tokens_total"],
                e["tool_calls"], e["trials_with_a_tool_call"], e["unread_final_answers"]),
               (1, 10, {"1": 1, "2": 58, "10": 1}, 127_000, 57 + 10 + 2, 59, 1))
    r.check("Haiku tools validate_plan: mean turns", close(e["turns_mean"], 127 / 60))
    e = d(HAIKU, T, "validate_problem")
    r.check_eq("Haiku tools validate_problem: one tool call raised",
               (e["tool_calls"], e["tool_calls_flagged_as_errors"],
                e["tool_results_that_are_the_error_text"], e["turns_max"]), (61, 1, 1, 3))
    e = d(SONNET, T, "solve")
    # A note of 3 thinking tokens on each of the 40 trials that called the planner.
    r.check_eq("Sonnet tools solve: notes between tool calls",
               (e["thinking_tokens_total"], e["thinking_blocks"], e["trials_with_a_note"],
                e["trials_with_a_tool_call"]), (120, 40, 40, 40))
    e = d(SONNET, T, "validate_domain")
    r.check_eq("Sonnet tools validate_domain: a pause and an unknown stop",
               (e["refusals"], e["other_error_rows"], e["endings"]["other error row"],
                e["tool_calls"], e["rows_with_a_stored_tool_call"]),
               (0, {"pause": 1, "unknown stop": 1, "scoring error": 0}, 2, 59, 58))
    for m, arm in ((HAIKU, N), (HAIKU, T), (SONNET, N)):
        r.check_eq(f"{m} {arm}: no note and no thinking token",
                   sum(d(m, arm, t)["thinking_blocks"] + d(m, arm, t)["thinking_tokens_total"]
                       for t in TASKS), 0)
    # Refusals per model, arm and task.
    r.check_eq("20 refusal rows", len(res["refusals"]), 20)
    want = {(HAIKU, N, "validate_domain"): 1, (HAIKU, N, "validate_problem"): 4}
    for e in res["refusals"]:
        r.check_eq(f"refusals {e['model']}/{e['arm']}/{e['task']}", (e["refusals"], e["n"]),
                   (want.get((e["model"], e["arm"], e["task"]), 0), 60))
    # The storage rule.
    r.check_eq("one row cut by storage, graded from the sidecar, right", res["storage_cut_rows"], [{
        "model": HAIKU, "arm": T, "task": "solve", "domain": "d03", "problem": "p01",
        "plan_label": "", "wording": 12, "answer_chars": len(BF.ANSWERS["cut_plan"]),
        "graded_from": "the full answer in the sidecar", "right": True}])
    r.check_eq("cut by storage in the descriptive table",
               sum(x["cut_by_storage"] for x in res["descriptive"]), 1)


def _corpus_checks(r, res):
    corpus = {c["folder"]: c for c in res["corpus"]}
    r.check_eq("four folders of 300 rows", {k: v["rows"] for k, v in corpus.items()},
               {f"{m}_{a}": 300 for m in (HAIKU, SONNET) for a in (N, T)})
    hn, ht = corpus[f"{HAIKU}_{N}"], corpus[f"{HAIKU}_{T}"]
    sn, st = corpus[f"{SONNET}_{N}"], corpus[f"{SONNET}_{T}"]
    r.check_eq("Haiku no tools: five refusals (more than 1%) and not VOID",
               (hn["refusals"], hn["error_rows_not_refusals"], hn["void"], hn["void_above"]),
               (5, 0, False, 3.0))
    r.check_eq("Sonnet tools: three error rows that are not refusals (exactly 1%), not VOID",
               (st["refusals"], st["error_rows_not_refusals"], st["void"], st["error_rows_by_kind"]),
               (0, 3, False, {"refusal": 0, "pause": 1, "unknown stop": 1, "scoring error": 1}))
    r.check_eq("half-written lines counted and skipped",
               (ht["torn_lines"], sn["sidecar_torn_lines"], hn["torn_lines"], st["sidecar_torn_lines"]),
               (1, 1, 0, 0))
    r.check_eq("a sidecar line of an abandoned try is counted, the last line is used",
               (ht["sidecar_lines_of_abandoned_tries"], ht["sidecar_lines"], hn["sidecar_lines"]),
               (1, 301, 300))
    r.check_eq("cut by storage per folder", [c["cut_by_storage"] for c in res["corpus"]], [0, 1, 0, 0])
    # The same-day rule.
    h, s = (by(res, "same_day", model=m) for m in (HAIKU, SONNET))
    r.check_eq("Haiku: one UTC date", (h["same_day"], h["tool_trials_on_another_date"],
                                       h["batch_sent_dates"], h["batch_ended_dates"]),
               (True, 0, {"2026-11-26": 300}, {"2026-11-26": 300}))
    # Sonnet: d01 and d02 of validate_problem requested the next day; d03's second request
    # the next day (its first is on the batch's date). The batch ended the next day.
    r.check_eq("Sonnet: three tool trials on another date, the batch ended the next day",
               (s["same_day"], s["tool_trials_on_another_date"], s["tool_trials"],
                s["tool_trial_first_request_dates"], s["batch_sent_dates"], s["batch_ended_dates"],
                s["reference_date"], s["no_tools_trials_sent_on_another_date"]),
               (False, 3, 300, {"2026-11-27": 298, "2026-11-28": 2}, {"2026-11-27": 300},
                {"2026-11-28": 300}, "2026-11-27", 0))
    r.check("Sonnet: share on another date", close(s["share_on_another_date"], 0.01))
    r.check_eq("batches", s["batches"], [{"batch_id": "msgbatch_fixture_sonnet", "trials": 300,
                                          "sent": ["2026-11-27"], "ended": ["2026-11-28"]}])
    # Apparatus.
    app = {a["folder"]: a for a in res["apparatus"]}
    r.check_eq("model ids returned", {k: v["model_ids_returned"] for k, v in app.items()},
               {f"{HAIKU}_{N}": [HAIKU], f"{HAIKU}_{T}": [HAIKU],
                f"{SONNET}_{N}": ["claude-sonnet-5-5-20261120"],
                f"{SONNET}_{T}": ["claude-sonnet-5-5-20261120"]})
    a = app[f"{SONNET}_{T}"]
    # Requests of Sonnet's tool arm: solve 100, validate_domain 119, validate_problem 120,
    # validate_plan 120, simulate 119. On the next day: two trials of two requests and one
    # second request.
    r.check_eq("Sonnet tools: requests and their dates",
               (a["requests"], a["request_dates_utc"]),
               (578, {"2026-11-27": 573, "2026-11-28": 5}))
    r.check_eq("Sonnet tools: notes passed back, host, version, cache tokens",
               (a["notes_returned_before_a_next_request"], a["notes_passed_back_unchanged"],
                a["hosts"], a["api_versions_sent"], a["sdk_versions"], a["cache_tokens"],
                a["responses_over_the_output_cap"], a["other_content_blocks"]),
               (40, 40, ["api.anthropic.com"], ["2023-06-01"], ["0.109.2"], 0, 0, {}))
    r.check_eq("Sonnet tools: the tools of the run, from its manifest",
               (a["manifest"]["tools_commit"][:7], a["manifest"]["tools_pyvalidator"],
                a["manifest"]["tools_sha256"], a["manifest"]["sdk_version"],
                sorted(a["manifest"]["runner_sha256"])),
               ("5e4f9c0", "0.1.5", F.TOOLS_SHA256, "0.109.2",
                ["tools/frontier55/anthropic_requests.py", "tools/frontier55/cost.py",
                 "tools/frontier55/runner.py"]))
    r.check_eq("no-tools folders record no tools",
               [(app[f"{m}_{N}"]["manifest"]["tools_commit"],
                 app[f"{m}_{N}"]["manifest"]["tools_sha256"]) for m in (HAIKU, SONNET)],
               [(None, None), (None, None)])
    r.check_eq("no-tools folders: one request per trial, no host",
               [(app[f"{m}_{N}"]["requests"], app[f"{m}_{N}"]["hosts"]) for m in (HAIKU, SONNET)],
               [(300, []), (300, [])])
    # 22 problems, three stored plans each; the tried plan of d01/p01 is validated on top.
    r.check_eq("validator route", (res["route_checked_plans"], res["validated_plans"]), (66, 67))
    r.check_eq("no tripwire fired", res["tripwires_audited"], {})
    # Nothing pooled, no open model.
    text = json.dumps({k: v for k, v in res.items() if k != "_md"}) + res["_md"]
    for word in ("Qwen", "qwen", "gemma", "Gemma", "pooled over the", "all models", "all tasks"):
        r.check(f"the output never says {word!r}", word not in text)
    r.check("every measured row names one model and one task",
            all(e["model"] in (HAIKU, SONNET) and e["task"] in TASKS
                for tab in ("rates", "contrasts", "verdict_errors", "tool_choice",
                            "tool_right_answer_wrong", "descriptive", "refusals")
                for e in res[tab]))
    r.check_eq("the wrong readings named in advance", len(res["wrong_readings_named_in_advance"]), 4)
    md = res["_md"]
    for title in ("RQ1, right answers per arm", "RQ1, tools minus no tools", "verdict errors",
                  "RQ2, which tool was called", "RQ3, tool right and final answer wrong",
                  "how the trials ended", "turns and tokens per trial", "rows cut by storage",
                  "the same-day rule", "corpus and apparatus"):
        r.check(f"markdown section: {title}", f"#### Claude run: {title}" in md)
    r.check("markdown: the Holm words appear", "tools ahead (not after Holm)" in md
            and "no tools ahead (not after Holm)" in md and "no difference shown" in md)


# ------------------------------------------------------------------ the planted rows, one by one
def test_traps(r):
    cells = load_fixture_cells()
    gt = json.loads((FIXTURE / "gt_cache.json").read_text())
    verdict = fixture_verdict()
    graded = {(m, arm): F.grade_cell(cells[m][arm], verdict, gt)
              for m in (HAIKU, SONNET) for arm in (N, T)}

    def trial(m, arm, task, dom, slot):
        return graded[(m, arm)][tuple(key_of(m, arm, task, dom, slot)[1:6])]

    def row(m, arm, task, dom, slot):
        k = tuple(key_of(m, arm, task, dom, slot)[1:6])
        return next(x for x in cells[m][arm].rows if x.trial_key == k)

    # A refusal: wrong, in the denominator, not counted toward VOID.
    t = trial(HAIKU, N, "validate_domain", "d01", 0)
    r.check_eq("refusal row", (t.registered, t.error_kind, t.ending, t.reason, t.tool_right),
               (False, "refusal", "refusal", "exception", False))
    r.check_eq("refusals do not count toward VOID",
               (F.void_rows(cells[HAIKU][N]), F.is_void(cells[HAIKU][N])), (0, False))
    # Error rows that are not refusals: wrong, counted toward VOID.
    for dom_slot, kind in ((("d02", 0), "pause"), (("d02", 1), "unknown stop")):
        t = trial(SONNET, T, "validate_domain", *dom_slot)
        r.check_eq(f"{kind} row", (t.registered, t.error_kind, t.ending),
                   (False, kind, "other error row"))
    t = trial(SONNET, T, "simulate", "d05", 0)
    rw = row(SONNET, T, "simulate", "d05", 0)
    g = G.grade(dataclasses.replace(rw, failure_reason="result_mismatch", error=""), gt, {})
    r.check_eq("scoring-error row: its stored answer is the right trace, and it is wrong",
               (g.ok, t.registered, t.error_kind, t.ending, t.scoring_error),
               (True, False, "scoring error", "other error row", True))
    r.check_eq("three error rows that are not refusals of 300: exactly 1%, not VOID",
               (F.void_rows(cells[SONNET][T]), F.is_void(cells[SONNET][T])), (3, False))
    # think_overflow maps to "stopped at the cap with no answer".
    t = trial(SONNET, T, "simulate", "d06", 0)
    rw = row(SONNET, T, "simulate", "d06", 0)
    r.check_eq("think_overflow row", (rw.failure_reason, t.think_overflow, t.ending, t.reason,
                                      t.registered, t.tool_right),
               ("think_overflow", True, "stopped at the cap with no answer", "truncated_empty",
                False, False))
    # No room: an empty length stop with ctx_no_room_turns, tool right, answer wrong.
    for dom in ("d07", "d08"):
        t = trial(SONNET, T, "simulate", dom, 0)
        rw = row(SONNET, T, "simulate", dom, 0)
        r.check_eq(f"no-room row {dom}", (rw.no_room, rw.response, rw.done_reason, t.ending,
                                          t.reason, t.registered, t.tool_right),
                   (True, "", "length", "refused for length (no room)", "no_room", False, True))
    r.check_eq("the two no-room rows: one rejected request, one stop reason",
               (cells[SONNET][T].meta[tuple(key_of(SONNET, T, "simulate", "d07", 0)[1:6])].overflow_error[:18],
                cells[SONNET][T].meta[tuple(key_of(SONNET, T, "simulate", "d08", 0)[1:6])].stop_reason),
               ("prompt is too long", "model_context_window_exceeded"))
    # Cut by storage: graded from the sidecar's full answer.
    t = trial(HAIKU, T, "solve", "d03", 1)
    rw = row(HAIKU, T, "solve", "d03", 1)
    stored = next(x for x in read_lines(cdir(FIXTURE, HAIKU, T) / "trials.jsonl")
                  if x["key"] == key_of(HAIKU, T, "solve", "d03", 1))["result"]
    r.check_eq("cut row: 65,536 stored characters, flagged",
               (len(stored["response"]), stored["response_truncated_by_storage"]), (65_536, True))
    r.check_eq("cut row: the typed row carries the full answer and is right",
               (rw.response == BF.ANSWERS["cut_plan"], t.storage_cut, t.registered, t.ending),
               (True, True, True, "answer"))
    cut_wrong = CPF.Verdicts(CPF.table_route({}))("d03", "p01", G.solve_plan(stored["response"])[0])
    r.check_eq("cut row: graded on its stored characters it would be wrong", cut_wrong, False)
    # Solve: the plan only in the last code block; capitals.
    for dom, kind in (("d02", "json_block"), ("d01", "tried_then_block")):
        t = trial(SONNET, N, "solve", dom, 0)
        g = G.grade(row(SONNET, N, "solve", dom, 0), gt, RUN.fixture_verdicts(FIXTURE / "route"))
        r.check_eq(f"{kind}: wrong under the rerun's grade, right under the registered grade",
                   (g.ok, t.registered), (False, True))
    t = trial(SONNET, T, "solve", "d02", 0)
    rw = row(SONNET, T, "solve", "d02", 0)
    plan = RG.block_plan(rw.response)[0]
    r.check_eq("capitals: invalid as written, valid in lower case, right",
               (verdict("d02", "p01", plan), verdict("d02", "p01", RG.lower(plan)), t.registered),
               (False, True, True))
    t = trial(SONNET, T, "solve", "d01", 1)
    r.check_eq("capitals in a bare JSON plan: right", t.registered, True)
    # Simulate: one JSON object per line.
    t = trial(SONNET, N, "simulate", "d01", 0)
    g = G.grade(row(SONNET, N, "simulate", "d01", 0), gt, {})
    r.check_eq("trace one object per line: the rerun's grade wrong, the registered grade right",
               (g.ok, g.reason, t.registered), (False, "format_parse_fail", True))
    t = trial(HAIKU, N, "simulate", "d01", 0)
    r.check_eq("a wrong trace one object per line stays wrong", t.registered, False)
    # Loop exhausted; the four classes; tool right and answer wrong.
    t = trial(HAIKU, T, "validate_plan", "d01", 0)
    r.check_eq("loop exhausted", (t.ending, t.registered, t.tool_right, t.reason),
               ("loop exhausted", False, False, "empty_stop"))
    t = trial(HAIKU, T, "validate_plan", "d03", 0)
    r.check_eq("tool right, answer wrong", (t.tool_right, t.registered, t.stated, t.truth),
               (True, False, False, True))
    t = trial(HAIKU, T, "validate_plan", "d04", 0)
    r.check_eq("tool right, no verdict stated", (t.tool_right, t.registered, t.stated, t.unread),
               (True, False, None, True))
    # The stored online grade is not the grade: a no-tools row the harness counted wrong.
    rw = row(SONNET, N, "solve", "d02", 0)
    r.check_eq("the stored online grade is not read", (rw.success, trial(SONNET, N, "solve", "d02", 0).registered),
               (False, True))
    # A zero-success cell, and the pairing key.
    r.check_eq("zero-success cell", sum(x.registered for x in graded[(HAIKU, N)].values()
                                        if x.task == "simulate"), 0)
    keys = [x.key for x in graded[(HAIKU, N)].values() if x.task == "validate_plan"]
    r.check("validate_plan keys collide without the plan label",
            len({k[:3] + k[4:] for k in keys}) < len(keys) == len(set(keys)) == 60)
    # The loader's model name never reaches a row's cell name.
    r.check("rows are named by their own folder",
            {x.cell for m in (HAIKU, SONNET) for a in (N, T) for x in cells[m][a].rows}
            == {f"{m}_{a}" for m in (HAIKU, SONNET) for a in (N, T)})


# ------------------------------------------------------------------ refusals of malformed input
def test_refusals(r):
    # Completeness: a short folder is resumed, not analysed.
    def short(root):
        k = key_of(SONNET, N, "solve", "d09", 2)
        edit(root, SONNET, N, rows=lambda rs: [x for x in rs if x["key"] != k],
             metas=lambda ms: [x for x in ms if x["key"] != k])
    halts(r, "a short folder is refused", short, "299 rows, registered 300")

    def missing_folder(root):
        shutil.rmtree(cdir(root, HAIKU, T))
    halts(r, "a missing folder is refused", missing_folder, "folder not found")

    # 300 rows, but one task a row short and another a row long.
    def wrong_per_task(root):
        k = key_of(SONNET, N, "solve", "d09", 2)
        row, meta = BF.make_trial(SONNET, N, "simulate", "d09", 2, BF.Clock(SONNET))
        row["key"][3] = row["result"]["problem_name"] = meta["key"][3] = "p03"
        edit(root, SONNET, N, rows=lambda rs: [x for x in rs if x["key"] != k] + [row],
             metas=lambda ms: [x for x in ms if x["key"] != k] + [meta])
    halts(r, "per-task counts are checked", wrong_per_task, "IncompleteCell")

    # The two arms of a model must hold the same trials.
    def other_keys(root):
        def rename(x):
            x["key"][3] = "p03"
            if "result" in x:
                x["result"]["problem_name"] = "p03"
        on_row(root, HAIKU, T, "solve", "d09", 2, rename)
        on_meta(root, HAIKU, T, "solve", "d09", 2, rename)
    halts(r, "arms with different trial keys are refused", other_keys,
          "the two arms do not hold the same trials (1 only in the no-tools folder, 1 only in "
          "the tools folder)")

    # VOID: a fourth error row that is not a refusal in Sonnet's tool arm (4 of 300).
    halts(r, "VOID above 1% error rows that are not refusals",
          lambda root: replant(root, SONNET, T, "validate_plan", "d09", 0, ("", "pause")),
          "VOID (section 7): claude-sonnet-5-5_tools has 4 error rows that are not refusals of "
          "300 (more than 1%). Both arms of claude-sonnet-5-5 are run again together")

    def unknown_stop(root, m, dom):
        """A no-tools trial that ended with a stop reason the runner does not know."""
        def meta(x):
            x["outcome"], x["stop_reason"] = "unknown_stop", "some_new_reason"
            x["turns"][0]["stop_reason"] = "some_new_reason"
            x["answer_chars"] = 0

        def row(x):
            x["result"].update(success=False, response="", tokens={}, done_reason="",
                               truncated=False, failure_reason="exception",
                               error="stop_reason=some_new_reason")
        on_meta(root, m, N, "validate_plan", dom, 0, meta)
        on_row(root, m, N, "validate_plan", dom, 0, row)

    def all_void(root):
        for m in (HAIKU, SONNET):
            for dom in ("d09", "d10", "d11", "d12"):
                replant(root, m, T, "validate_plan", dom, 0, ("", "pause"))
                unknown_stop(root, m, dom)
    halts(r, "all four folders VOID is a fault to trace", all_void, "every folder is VOID")
    halts(r, "VOID in the no-tools arm (4 unknown stops of 300)",
          lambda root: [unknown_stop(root, HAIKU, d) for d in ("d09", "d10", "d11", "d12")],
          "claude-haiku-5-5_no-tools has 4 error rows that are not refusals of 300 (more than "
          "1%). Both arms of claude-haiku-5-5 are run again together")

    # The run manifest: the settings the folder was collected under.
    def manifest_case(label, fn, needle, where=(SONNET, T)):
        halts(r, f"manifest: {label}", lambda root: on_manifest(root, *where, fn), needle)

    manifest_case("a pilot folder under a full-run name", lambda m: m.update(pilot=True),
                  "pilot=True, registered False")
    manifest_case("another tool list", lambda m: m.update(tools_sha256="0" * 64), "tools_sha256=")
    manifest_case("another tools commit", lambda m: m.update(tools_commit="e428f17" + "0" * 33),
                  "tools_commit='e428f17")
    manifest_case("another validator release", lambda m: m.update(tools_pyvalidator="0.1.6"),
                  "tools_pyvalidator='0.1.6', registered '0.1.5'")
    manifest_case("another output cap", lambda m: m["output_caps"].update(simulate=8192),
                  "output_caps=")
    manifest_case("another effort", lambda m: m.update(effort="low"), "effort='low'")
    manifest_case("another storage cap", lambda m: m.update(snapshot_len=16_384),
                  "snapshot_len=16384, registered 65536")
    manifest_case("a fourth wording", lambda m: m.update(prompt_variants=[11, 12, 13, 14]),
                  "prompt_variants=")
    manifest_case("another address", lambda m: m.update(base_url="https://proxy.example.com"),
                  "base_url=")
    manifest_case("another ground truth", lambda m: m.update(ground_truth_sha256="0" * 64),
                  "ground_truth_sha256=")
    manifest_case("another ground-truth file", lambda m: m.update(gt_cache_sha256="0" * 64),
                  "the run used the ground-truth cache 000000000000")
    manifest_case("a missing field", lambda m: m.pop("tools_sha256"), "has no 'tools_sha256'")
    manifest_case("tools recorded in a no-tools folder",
                  lambda m: m.update(tools_commit="5e4f9c0" + "0" * 33),
                  "a no-tools folder records a tools commit", where=(SONNET, N))
    manifest_case("the other model", lambda m: m.update(model=HAIKU), "model='claude-haiku-5-5'")
    halts(r, "manifest: a folder without one is refused",
          lambda root: (cdir(root, HAIKU, N) / "run_manifest.json").unlink(),
          "no readable run manifest")

    # The storage rule: a cut row is graded from the sidecar, so the sidecar must hold it.
    def no_full(x):
        x["full_answer_if_cut"] = None
    halts(r, "a cut row without its full answer is refused",
          lambda root: on_meta(root, HAIKU, T, "solve", "d03", 1, no_full),
          "storage_cut, answer_chars and full_answer_if_cut disagree")

    def flag_only(x):
        x["result"]["response_truncated_by_storage"] = True
    halts(r, "a row flagged as cut whose sidecar says it is not is refused",
          lambda root: on_row(root, SONNET, N, "solve", "d09", 0, flag_only),
          "whether the answer was cut by storage")

    def other_full(x):
        x["full_answer_if_cut"] = x["full_answer_if_cut"][:-1] + "x"
    halts(r, "a full answer that is not the last turn's text is refused",
          lambda root: on_meta(root, HAIKU, T, "solve", "d03", 1, other_full),
          "full_answer_if_cut is not the answer text of the last turn")

    def unflag(x):
        x["result"]["response_truncated_by_storage"] = False
    halts(r, "a cut answer whose row is not flagged is refused",
          lambda root: on_row(root, HAIKU, T, "solve", "d03", 1, unflag),
          "whether the answer was cut by storage")

    # Row against sidecar.
    def drop_meta(root):
        k = key_of(SONNET, N, "solve", "d09", 0)
        edit(root, SONNET, N, metas=lambda ms: [x for x in ms if x["key"] != k])
    halts(r, "a row without its sidecar line is refused", drop_meta, "has no sidecar line")

    def extra_meta(root):
        _row, meta = BF.make_trial(SONNET, N, "solve", "d09", 0, BF.Clock(SONNET))
        meta["key"][3] = "p04"
        edit(root, SONNET, N, metas=lambda ms: ms + [meta])
    halts(r, "a sidecar line of a trial without a row is refused", extra_meta,
          "sidecar line(s) of trials that have no row")

    def dup_row(root):
        edit(root, SONNET, N, rows=lambda rs: rs + [rs[0]])
    halts(r, "a duplicate trial key is refused", dup_row, "duplicate trial key")

    def answer_differs(x):
        x["result"]["response"] += " "
    halts(r, "a stored answer that is not the sidecar's is refused",
          lambda root: on_row(root, SONNET, N, "solve", "d09", 0, answer_differs),
          "the stored answer is not the answer text of the sidecar's last turn")

    def tokens_differ(x):
        x["result"]["tokens"]["completion"] += 1
    halts(r, "token counts that are not the sidecar's are refused",
          lambda root: on_row(root, SONNET, T, "solve", "d09", 0, tokens_differ),
          "turns and tokens")

    def calls_differ(x):
        x["result"]["tool_calls"][0]["name"] = "validate_plan"
    halts(r, "stored tool calls that are not the sidecar's are refused",
          lambda root: on_row(root, SONNET, T, "solve", "d09", 0, calls_differ),
          "the stored tool calls and the sidecar's tool results")

    def refusal_text(x):
        x["result"]["error"] = "stop_reason=refusal"
    halts(r, "an error text that is not the sidecar's outcome is refused",
          lambda root: on_row(root, SONNET, T, "validate_domain", "d02", 0, refusal_text),
          "error text 'stop_reason=refusal' with sidecar outcome 'pause_turn'")

    def other_error(x):
        x["result"]["error"] = "boom: the server raised"
    halts(r, "an exception row that is neither a stop reason nor a scoring error is refused",
          lambda root: on_row(root, SONNET, T, "validate_domain", "d02", 0, other_error),
          "neither a stop reason nor a scoring error")

    def wrong_model(x):
        x["result"]["model"] = x["key"][0] = SONNET
    halts(r, "a row of the other model is refused",
          lambda root: on_row(root, HAIKU, N, "solve", "d09", 0, wrong_model),
          "in the folder of claude-haiku-5-5")

    def open_model(x):
        x["result"]["model"] = x["key"][0] = C.MODEL_IDS[F.LOADER_TAG]
    halts(r, "a row that already names an open model is refused",
          lambda root: on_row(root, HAIKU, N, "solve", "d09", 0, open_model),
          "in the folder of claude-haiku-5-5")

    def clipped(root):
        def row(x):
            x["result"]["tokens"].update(ctx_clipped_turns=1, ctx_clip_last_turn_max_tokens=100,
                                         ctx_clip_last_turn_prompt_tokens=16_000)
        on_row(root, SONNET, T, "solve", "d09", 0, row)
    halts(r, "a clipped turn does not exist in this run", clipped, "a clipped turn")

    def infra(x):
        x["result"]["infra_failure"] = True
    halts(r, "an infrastructure-failure row is refused",
          lambda root: on_row(root, SONNET, N, "solve", "d09", 0, infra),
          "a row shape the runner of this run never writes")

    def bad_enum(x):
        x["result"]["failure_reason"] = "made_up"
    halts(r, "the frozen loader refuses an unknown failure reason",
          lambda root: on_row(root, SONNET, N, "solve", "d09", 0, bad_enum),
          "unknown failure_reason")

    def missing_field(x):
        del x["result"]["done_reason"]
    halts(r, "the frozen loader refuses a missing key",
          lambda root: on_row(root, SONNET, N, "solve", "d09", 0, missing_field), "missing key")

    def foreign_domain(root):
        def rename(x):
            x["key"][2] = "blocksworld"
            if "result" in x:
                x["result"]["domain_name"] = "blocksworld"
        on_row(root, SONNET, N, "solve", "d09", 0, rename)
        on_meta(root, SONNET, N, "solve", "d09", 0, rename)
    halts(r, "fixture mode reads the fixture's own domains only", foreign_domain,
          "is not one of the fixture's own")

    # The sidecar's typed reader.
    S_ = (SONNET, T, "solve", "d09", 0)

    def meta_case(label, fn, needle, where=S_):
        halts(r, f"sidecar: {label}", lambda root: on_meta(root, *where, fn), needle)

    meta_case("a missing key", lambda x: x.pop("outcome"), "missing key(s) ['outcome']")
    meta_case("an extra key", lambda x: x.update(grade="right"), "unexpected key(s) ['grade']")
    meta_case("an unknown outcome", lambda x: x.update(outcome="fine"), "unknown outcome 'fine'")
    meta_case("another effort", lambda x: x["settings"].update(effort="low"),
              "are not the registered")
    meta_case("another system text", lambda x: x["settings"].update(system_sha256="0" * 64),
              "are not the registered")
    meta_case("another output cap", lambda x: x["turns"][0]["request"].update(max_tokens=16_384),
              "the request's settings are not the registered ones")
    meta_case("a sampling field in a request",
              lambda x: x["turns"][0]["request"]["param_keys"].append("temperature"),
              "the request's settings are not the registered ones")
    meta_case("another thinking setting",
              lambda x: x["turns"][1]["request"].update(thinking={"type": "enabled"}),
              "the request's settings are not the registered ones")
    meta_case("a request without its settings", lambda x: x["turns"][0].update(request=None),
              "the request's settings are not the registered ones")
    meta_case("a request to another host",
              lambda x: x["turns"][0].update(request_host="proxy.example.com"),
              "the request went to 'proxy.example.com'")
    meta_case("another model id", lambda x: (x["turns"][0].update(model="claude-opus-5"),),
              "the provider returned model id 'claude-opus-5'")
    meta_case("a turn missing its usage", lambda x: x["turns"][0].pop("usage"), "missing key(s) ['usage']")
    meta_case("token counts that are not integers",
              lambda x: x["turns"][0]["usage"].update(output_tokens="10"), "output_tokens must be int")
    meta_case("an unreadable time", lambda x: x["turns"][0].update(requested_at_utc="yesterday"),
              "unreadable time")
    meta_case("a missing time", lambda x: x["turns"][0].update(requested_at_utc=None),
              "a time must be a string")
    meta_case("an answer that stopped for a tool",
              lambda x: (x["turns"][1].update(stop_reason="tool_use"), x.update(stop_reason="tool_use")),
              "the last turn stopped with 'tool_use'")
    meta_case("turns that are not numbered in order",
              lambda x: (x["turns"].append(copy.deepcopy(x["turns"][-1])),), "numbered 2")

    def eleventh(x):
        t = copy.deepcopy(x["turns"][-1])
        t["turn"], t["request"]["n_messages"] = 11, 21
        x["turns"].append(t)
        x["n_turns"] = 11
        x["request_ids"].append("req_x")
    meta_case("eleven round trips", eleventh, "11 round trips, at most 10",
              where=(HAIKU, T, "validate_plan", "d01", 0))
    meta_case("tool results that are not the tools asked for",
              lambda x: x["tool_results"][0].update(name="validate_plan"),
              "the tool results are not those of the tools the model asked for")
    meta_case("a batch id on a live trial", lambda x: x.update(batch_id="msgbatch_x"),
              "a live trial with a batch id")
    meta_case("another run", lambda x: x.update(run="frontier55-pilot"), "run='frontier55-pilot'")
    meta_case("the batch route in the tool arm", lambda x: x.update(transport="batch"),
              "transport='batch'")
    def second_request(x):
        x["turns"][0]["stop_reason"] = "tool_use"
        t = copy.deepcopy(x["turns"][0])
        t["turn"], t["request"]["n_messages"], t["stop_reason"] = 2, 3, "end_turn"
        x["turns"].append(t)
        x["n_turns"] = 2
        x["request_ids"].append(None)
    meta_case("two requests in the no-tools arm", second_request,
              "2 requests in the no-tools arm", where=(SONNET, N, "solve", "d09", 0))

    # Section 2.5: an over-length outcome only after a tool result, in the tool arm.
    def no_room_no_tools(root):
        def meta(x):
            x["outcome"] = "overflow"
            x["stop_reason"] = x["turns"][0]["stop_reason"] = "model_context_window_exceeded"
        on_meta(root, SONNET, N, "solve", "d09", 0, meta)
    halts(r, "an over-length outcome in the no-tools arm is refused", no_room_no_tools,
          "not a tool conversation that ran out of the window after a tool result")

    # Section 2.5: the model's notes go back as they came.
    def note_lost(x):
        x["turns"][1]["thinking_blocks_passed_back"] = 0
    halts(r, "a note that did not go back unchanged is refused",
          lambda root: on_meta(root, *S_, note_lost), "were found unchanged in the next request")

    # Section 6: the model id changes within a folder.
    def other_id(x):
        x["turns"][0]["model"] = x["turns"][1]["model"] = "claude-sonnet-5-5-20261201"
        x["model_ids_returned"] = ["claude-sonnet-5-5-20261201"]
    halts(r, "a model id that changes within a folder is refused",
          lambda root: on_meta(root, *S_, other_id), "changes within the folder")

    # Section 6: more than 5% of the tool trials on another date (16 of 300; 3 are planted).
    def late(root):
        ks = [key_of(SONNET, T, "validate_plan", d, 0) for d in BF.DOMAINS[:13]]

        def go(ms):
            for x in ms:
                if x["key"] in ks:
                    for t in x["turns"]:
                        t["requested_at_utc"] = t["requested_at_utc"].replace("2026-11-27", "2026-11-28")
            return ms
        edit(root, SONNET, T, metas=go)
    halts(r, "more than 5% of the tool trials on another date is refused", late,
          "16 of 300 tool trials were requested on a date other than 2026-11-27")

    def late_15(root):
        ks = [key_of(SONNET, T, "validate_plan", d, 0) for d in BF.DOMAINS[:12]]

        def go(ms):
            for x in ms:
                if x["key"] in ks:
                    for t in x["turns"]:
                        t["requested_at_utc"] = t["requested_at_utc"].replace("2026-11-27", "2026-11-28")
            return ms
        edit(root, SONNET, T, metas=go)
    root = copy_fixture()
    try:
        late_15(root)
        code, err, res, _ = run_fixture(root)
        r.check("exactly 5% of the tool trials on another date is analysed and reported",
                code == 0 and by(res, "same_day", model=SONNET)["tool_trials_on_another_date"] == 15,
                err)
    finally:
        shutil.rmtree(root.parent)

    # Refusals stay in the denominator and never make a folder VOID: six more of them.
    root = copy_fixture()
    try:
        for dom in BF.DOMAINS[4:10]:
            replant(root, HAIKU, N, "validate_plan", dom, 0, ("", "refusal"))
        code, err, res, _ = run_fixture(root)
        ok = code == 0
        if ok:
            c = next(x for x in res["corpus"] if x["folder"] == f"{HAIKU}_{N}")
            e = by(res, "rates", model=HAIKU, task="validate_plan", arm=N)
            ok = (c["refusals"], c["void"], e["right"], e["n"]) == (11, False, 54, 60) and by(
                res, "refusals", model=HAIKU, arm=N, task="validate_plan")["refusals"] == 6
        r.check("eleven refusals of 300: analysed, wrong, in the denominator", ok, err)
    finally:
        shutil.rmtree(root.parent)

    # Fixture mode guards.
    def no_marker(root):
        (root / "SYNTHETIC_FIXTURE").unlink()
    halts(r, "fixture mode needs the marker", no_marker, "has no SYNTHETIC_FIXTURE marker")

    def registered_size(root):
        d = json.loads((root / "design.json").read_text())
        d.update(n_folder=4560, per_wording=1520, per_task=dict(F.PER_TASK))
        (root / "design.json").write_text(json.dumps(d))
    halts(r, "fixture mode refuses a registered-size design", registered_size,
          "refuses a registered-size design")
    code, err, _ = run_main(["--fixture", str(FIXTURE)])
    r.check("fixture mode needs its own --out", code == 2 and "needs its own --out" in err, err)
    code, err, _ = run_main(["--fixture", str(FIXTURE), "--out", "/nonexistent/x", "--numbers"])
    r.check("fixture mode never writes NUMBERS.md", code == 2 and "live mode only" in err, err)

    # The validator route: a stored verdict the route does not return.
    def route_flip(root):
        p = root / "route" / "plan_verdicts.json"
        table = json.loads(p.read_text())
        table[0]["valid"] = not table[0]["valid"]
        p.write_text(json.dumps(table))
    halts(r, "a route that disagrees with a stored verdict is refused", route_flip,
          "the validator route disagrees with the stored verdict")


# ------------------------------------------------------------------ tripwires
def test_tripwires(r):
    # T1, a constant column: with Haiku's refusals on validate_problem answered right, the
    # four folders all have 60 of 60 on that task.
    root = copy_fixture()
    try:
        for dom in BF.DOMAINS[:4]:
            replant(root, HAIKU, N, "validate_problem", dom, 0, ("ok", "plain"))
        code, err, _res, written = run_fixture(root)
        r.check("T1 halts and writes nothing",
                code == 2 and "T1:validate_problem" in err and "the same in all four folders "
                "(60 of 60)" in err and written == [], err[-300:])
        notes = root / "notes.json"
        notes.write_text(json.dumps({"T1:validate_problem": "read 20 answers by hand (fixture)"}))
        code, err, res, _ = run_fixture(root, ["--audited-tripwires", "T1:validate_problem",
                                               "--audit-notes", str(notes)])
        r.check("an audited tripwire is released and recorded",
                code == 0 and res["tripwires_audited"]["T1:validate_problem"]["note"]
                == "read 20 answers by hand (fixture)" and "Tripwires that fired and were "
                "audited" in res["_md"], err)
        code, err, _res, _ = run_fixture(root, ["--audited-tripwires", "T1:validate_problem"])
        r.check("an audited tripwire needs a written note", code == 2 and "--audit-notes" in err, err)
        notes.write_text(json.dumps({"T1:validate_problem": "x", "T1:solve": "y"}))
        code, err, _res, _ = run_fixture(root, ["--audited-tripwires", "T1:validate_problem,T1:solve",
                                                "--audit-notes", str(notes)])
        r.check("a note for a tripwire that did not fire is refused",
                code == 2 and "did not fire" in err, err)
    finally:
        shutil.rmtree(root.parent)

    # T6, thinking where the registration has none: a note in Haiku's tool arm.
    def haiku_note(x):
        x["turns"][0]["content"].insert(0, {"type": "thinking", "thinking": "hm", "signature": "S"})
        x["turns"][1]["thinking_blocks_in_previous_response"] = 1
        x["turns"][1]["thinking_blocks_passed_back"] = 1
    halts(r, "T6: a note where the registration has none halts",
          lambda root: on_meta(root, HAIKU, T, "solve", "d09", 0, haiku_note), "T6:claude-haiku-5-5:tools")

    # T4, more than 5% of the final answers unread: four of 60 no-tools answers of Sonnet
    # on validate_domain state no verdict.
    def four_unread(root):
        for dom in BF.DOMAINS[8:12]:
            replant(root, SONNET, N, "validate_domain", dom, 0, ("no_verdict", "plain"))
    halts(r, "T4: more than 5% unread final answers halts", four_unread,
          "T4:claude-sonnet-5-5:no-tools:validate_domain")

    # T7, a response over its output cap.
    def over_cap(root):
        def meta(x):
            x["turns"][0]["usage"]["output_tokens"] = 9000

        def row(x):
            x["result"]["tokens"]["completion"] = 9000
        on_meta(root, SONNET, N, "solve", "d09", 0, meta)
        on_row(root, SONNET, N, "solve", "d09", 0, row)
    halts(r, "T7: a response over its output cap halts", over_cap, "T7:claude-sonnet-5-5:no-tools")

    # The rule itself, on hand-built tables.
    design = F.Design("unit", {t: 60 for t in TASKS}, 300, 100, 20)

    def desc(**kw):
        base = {"model": SONNET, "arm": T, "task": "solve", "n": 60, "read": 60,
                "trials_with_a_tool_call": 40, "unread_final_answers": 0, "refusals": 0,
                "thinking_tokens_total": 5, "thinking_blocks": 2}
        return {**base, **kw}
    rates = [{"model": m, "task": t, "arm": a, "right": 30 + i} for i, (m, a) in enumerate(
        (m, a) for m in (HAIKU, SONNET) for a in (N, T)) for t in TASKS]
    app = [{"model": SONNET, "arm": T, "folder": "f", "responses_over_the_output_cap": 0}]

    def fired(d=None, ra=None, ap=None):
        return set(F.tripwires(design, ra or rates, [d or desc()], ap or app))
    r.check_eq("nothing fires on an ordinary cell", fired(), set())
    r.check_eq("T2: the grader reads no answer", fired(desc(read=0)), {f"T2:{SONNET}:{T}:solve"})
    r.check_eq("T3: no trial called a tool", fired(desc(trials_with_a_tool_call=0)),
               {f"T3:{SONNET}:solve"})
    r.check_eq("T3 is for the tool arm only", fired(desc(arm=N, trials_with_a_tool_call=0,
                                                         thinking_tokens_total=0, thinking_blocks=0)),
               set())
    r.check_eq("T4: 3 of 60 unread is the limit, 4 fires",
               (fired(desc(unread_final_answers=3)), fired(desc(unread_final_answers=4))),
               (set(), {f"T4:{SONNET}:{T}:solve"}))
    r.check_eq("T5: 6 of 60 refusals is the limit, 7 fires",
               (fired(desc(refusals=6)), fired(desc(refusals=7))),
               (set(), {f"T5:{SONNET}:{T}:solve"}))
    r.check_eq("T6: thinking tokens in Sonnet's no-tools arm", fired(desc(arm=N)), {f"T6:{SONNET}:{N}"})
    r.check_eq("T8: notes without a thinking token count", fired(desc(thinking_tokens_total=0)),
               {f"T8:{SONNET}:{T}"})
    r.check_eq("T7: a response over the cap",
               fired(ap=[{**app[0], "responses_over_the_output_cap": 2}]), {f"T7:{SONNET}:{T}"})
    same = [{**e, "right": 60} for e in rates]
    r.check_eq("T1: the same count in all four folders, on every task", fired(ra=same),
               {f"T1:{t}" for t in TASKS})


# ------------------------------------------------------------------ the runner's own shapes
def test_runner_shapes(r):
    """Rows and sidecar lines built by the runner's own functions (no network: the SDK on
    a mock transport, as tests/test_frontier55.py does) go through this file's readers.
    The fixture is hand-written in the same shape; this is the check that it is."""
    try:
        from tests import test_frontier55 as TR
    except ImportError as e:   # the SDK is not installed
        print(f"  SKIPPED runner shapes: {e}")
        return
    R, AR = TR.R, TR.AR
    # Constants the two files state separately.
    r.check_eq("models", F.MODELS, tuple(R.MODELS))
    r.check_eq("tasks, wordings, arms", (F.TASKS, F.WORDINGS, F.ARMS), (R.TASKS, R.WORDINGS, R.ARMS))
    r.check_eq("trials per task and folder", (F.PER_TASK, F.N_FOLDER), (R.PER_TASK_PER_ARM, R.N_PER_ARM))
    r.check_eq("system sha256", F.SYSTEM_SHA256, R.SYSTEM_SHA256)
    r.check_eq("output caps, storage cap, round trips",
               (F.OUTPUT_CAP, F.STORAGE_CAP, F.MAX_ROUND_TRIPS),
               (R.OUTPUT_CAP, R.STORAGE_CAP, R.MAX_TOOL_LOOPS))
    r.check_eq("ground-truth cache, tools commit, validator",
               (F.GT_CACHE_SHA256, F.TOOLS_COMMIT, F.PYVALIDATOR),
               (R.GT_CACHE_SHA256, R.MARKETPLACE_COMMIT, R.PYVALIDATOR))
    r.check_eq("settings per model", F.SETTINGS, AR.MODEL_SETTINGS)
    r.check_eq("run name, host", (F.RUN_NAME, "https://" + F.API_HOST), (R.RUN, R.API_BASE_URL))
    r.check_eq("outcomes", set(F.OUTCOMES), {R.ANSWER, R.LOOP_EXHAUSTED, R.OVERFLOW, R.REFUSAL,
                                             R.PAUSE_TURN, R.UNKNOWN_STOP})
    r.check_eq("error outcomes", F.ERROR_OUTCOMES, R.ERROR_ROW_OUTCOMES)
    r.check_eq("stop reasons", (F.STOP_END, F.STOP_MAX, F.STOP_TOOL, F.STOP_REFUSAL, F.STOP_PAUSE,
                                F.STOP_SEQ, F.STOP_WINDOW),
               (AR.STOP_END, AR.STOP_MAX_TOKENS, AR.STOP_TOOL_USE, AR.STOP_REFUSAL, AR.STOP_PAUSE,
                AR.STOP_SEQUENCE, AR.STOP_WINDOW))
    r.check("done reasons of an answer",
            all(AR.DONE_REASON_OF_STOP[k] == v for k, v in F.DONE_OF_STOP.items()))
    for model in F.MODELS:
        for arm in F.ARMS:
            for task in TASKS:
                for n in (1, 3):
                    r.check_eq(f"registered request {model} {arm} {task} {n}",
                               F.registered_request(model, task, arm, n),
                               AR.registered_request_settings(model, F.OUTPUT_CAP[task],
                                                              arm == T, n))
    usage = {"input_tokens": 5, "output_tokens": 9, "cache_read_input_tokens": 2,
             "cache_creation": {"ephemeral_5m_input_tokens": 1},
             "output_tokens_details": {"thinking_tokens": 4, "reasoning_tokens": 1}}
    r.check_eq("thinking and cache token rules",
               (F._sum_keys(usage, ("thinking", "reasoning")), F._sum_keys(usage, ("cache",))),
               (AR.thinking_tokens_of(usage), AR.cache_tokens_of(usage)))
    r.check_eq("the loader's model name is the runner's", C.MODEL_IDS[F.LOADER_TAG],
               C.MODEL_IDS[C.PART_A_MODELS[0]])

    # The run manifest the runner writes is the one `check_manifest` reads.
    tmp = Path(tempfile.mkdtemp(prefix="f55_manifest_"))
    try:
        gt = {"d": {"p": {"plan": ["(a)"]}}}
        market = {"commit": "5e4f9c0" + "a" * 33, "pyvalidator": "0.1.5",
                  "freeze": {"pddl-validator": ["pddl-pyvalidator==0.1.5"]}}
        for model in F.MODELS:
            for arm in F.ARMS:
                for pilot in (False, True):
                    d = tmp / f"{model}_{arm}_{pilot}"
                    TR.RM.write_manifest(d, R.build_run_manifest(
                        model, arm, pilot=pilot, sdk_version="0.109.2", gt_cache=Path("gt.json"),
                        ground_truth=gt, marketplace=market if arm == T else None,
                        tools_digest=F.TOOLS_SHA256 if arm == T else None))
                    try:
                        got = F.check_manifest(d, model, arm, gt)
                        ok = (not pilot and got["gt_cache_sha256"] == F.GT_CACHE_SHA256
                              and sorted(got["runner_sha256"]) == sorted(R.RUNNER_FILES))
                    except CPF.Halt as e:
                        ok = pilot and "pilot=True" in str(e)
                    r.check(f"runner's manifest {model} {arm} pilot={pilot}", ok)
    finally:
        shutil.rmtree(tmp)

    design = F.Design("unit", {t: 3 for t in TASKS}, 15, 5, 1)
    seen_meta, seen_turn, seen_live = set(), set(), set()

    def through(label, model, arm, row, meta, want_kind, want_ending, cut=False):
        row, meta = json.loads(json.dumps(row)), json.loads(json.dumps(meta))
        (seen_meta.update(meta) if arm == T else None)
        for t in meta["turns"]:
            (seen_live if arm == T else seen_turn).update(t)
        try:
            m = F.parse_meta(meta, model, arm, label)
            typed, m2, kind, was_cut = F.load_row(row, {m.key: m}, F.cell_spec(design, model, arm),
                                                  model, label)
        except (S.SchemaError, CPF.Halt) as e:
            r.check(f"runner shape accepted: {label}", False, f"{type(e).__name__}: {e}")
            return None, None
        r.check_eq(f"runner shape: {label}", (kind, F.ending_of(typed, kind), was_cut, m2 is m),
                   (want_kind, want_ending, cut, True))
        return typed, m

    async def tools_cases():
        W, msg, tool_use, has = TR.Wire, TR.msg, TR.tool_use, TR.has_tool_result
        out = []
        for model in (HAIKU, SONNET):
            def tr(reply, task="solve", model=model):
                return TR.trial(W(reply), task, model)
            _o, row, meta = await tr(lambda q, b, n: msg([TR.TEXT_PLAN], "end_turn", model, in_tok=400)
                                     if has(b) else msg([tool_use()], "tool_use", model))
            out.append((f"{model} tool then answer", model, row, meta, None, "answer", False))
            _o, row, meta = await tr(lambda q, b, n: msg([tool_use(n, "validate_domain")], "tool_use", model))
            out.append((f"{model} loop exhausted", model, row, meta, None, "loop exhausted", False))
            _o, row, meta = await tr(lambda q, b, n: msg([{"type": "text", "text": "I can't."}],
                                                         "refusal", model))
            out.append((f"{model} refusal", model, row, meta, "refusal", "refusal", False))
            _o, row, meta = await tr(lambda q, b, n: msg([], "refusal", model) if has(b)
                                     else msg([tool_use()], "tool_use", model))
            out.append((f"{model} refusal after a tool", model, row, meta, "refusal", "refusal", False))
            _o, row, meta = await tr(lambda q, b, n: msg([], "pause_turn", model))
            out.append((f"{model} pause", model, row, meta, "pause", "other error row", False))
            _o, row, meta = await tr(lambda q, b, n: msg([], "some_new_reason", model))
            out.append((f"{model} unknown stop", model, row, meta, "unknown stop", "other error row", False))
            _o, row, meta = await tr(lambda q, b, n: TR.api_error(
                400, "invalid_request_error", "prompt is too long: 1200000 tokens > 1000000 maximum")
                if has(b) else msg([tool_use()], "tool_use", model))
            out.append((f"{model} no room (rejected)", model, row, meta, None,
                        "refused for length (no room)", False))
            _o, row, meta = await tr(lambda q, b, n: msg([], "model_context_window_exceeded", model)
                                     if has(b) else msg([tool_use()], "tool_use", model))
            out.append((f"{model} no room (stop reason)", model, row, meta, None,
                        "refused for length (no room)", False))
            _o, row, meta = await tr(lambda q, b, n: msg([{"type": "text", "text": "(pick-up b)"}],
                                                         "max_tokens", model))
            out.append((f"{model} stopped at the cap", model, row, meta, None,
                        "stopped at the cap with an answer", False))
            _o, row, meta = await tr(lambda q, b, n: msg([{"type": "text", "text": "x" * 70_000}],
                                                         "end_turn", model))
            out.append((f"{model} cut by storage", model, row, meta, None, "answer", True))
        # Sonnet: a note, a tool, then a final turn at the cap holding a note and no text.
        _o, row, meta = await TR.trial(W(lambda q, b, n: msg([TR.THINK], "max_tokens", think_tok=9)
                                         if has(b) else msg([TR.THINK, tool_use(1, "validate_domain")],
                                                            "tool_use", think_tok=3)), "solve", SONNET)
        out.append(("Sonnet think_overflow", SONNET, row, meta, None,
                    "stopped at the cap with no answer", False))
        return out

    async def batch_cases():
        out = []
        entry = {"submitted_at_utc": "2026-11-26T07:00:01.000000Z",
                 "ended_at": "2026-11-26T07:40:00+00:00", "anthropic_version_sent": "2023-06-01",
                 "created_at": "2026-11-26T07:00:00+00:00", "batch_id": "msgbatch_x",
                 "sdk_version": "0.109.2"}
        mcp = TR.mcp_ok()
        answers = {"solve": TR.TEXT_PLAN["text"], "validate_domain": "ok\nVERDICT: VALID",
                   "validate_problem": "VERDICT: VALID", "validate_plan": "VERDICT: INVALID",
                   "simulate": '```json\n{"trajectory": []}\n```'}
        for model in (HAIKU, SONNET):
            for task, text in answers.items():
                for stop, kind, ending in (("end_turn", None, "answer"),
                                           ("max_tokens", None, "stopped at the cap with an answer"),
                                           ("refusal", "refusal", "refusal"),
                                           ("tool_use", "unknown stop", "other error row")):
                    j = TR.job(task, model, with_tools=False)
                    params = R.first_request(model, j, False, None)
                    rec = R.turn_record(1, TR.msg([{"type": "text", "text": text}], stop, model),
                                        requested_at=entry["submitted_at_utc"],
                                        received_at=entry["ended_at"], request_id=None,
                                        version_sent=entry["anthropic_version_sent"],
                                        request=AR.request_settings(params))
                    outcome = R.outcome_of([rec], [], [])
                    row = await R.make_row(model, j, False, outcome, mcp)
                    meta = R.make_meta(model, j, False, outcome, row, transport="batch",
                                       batch_id=entry["batch_id"], sdk_version=entry["sdk_version"],
                                       extra={"batch_created_at": entry["created_at"],
                                              "batch_ended_at": entry["ended_at"]})
                    out.append((f"{model} batch {task} {stop}", model, row, meta, kind, ending))
        return out

    for label, model, row, meta, kind, ending, cut in asyncio.run(tools_cases()):
        typed, m = through(label, model, T, row, meta, kind, ending, cut)
        if typed is not None and cut:
            r.check_eq(f"{label}: the typed row carries the sidecar's full answer",
                       (len(typed.response), typed.response == m.full_answer), (70_000, True))
        if typed is not None and "think_overflow" in label:
            r.check_eq(f"{label}: the harness's label, the notes and their tokens",
                       (typed.failure_reason, sum(t.thinking_blocks for t in m.turns),
                        sum(t.thinking_tokens for t in m.turns), m.turns[1].think_seen,
                        m.turns[1].think_back), ("think_overflow", 2, 12, 1, 1))
    seen_batch = set()
    for label, model, row, meta, kind, ending in asyncio.run(batch_cases()):
        seen_batch.update(meta)
        through(label, model, N, row, meta, kind, ending)
    r.check_eq("sidecar keys of a live trial", seen_meta, set(F.META_KEYS))
    r.check_eq("sidecar keys of a batch trial", seen_batch, set(F.META_BATCH_KEYS))
    r.check_eq("turn keys of a live trial", seen_live, set(F.TURN_LIVE_KEYS))
    r.check_eq("turn keys of a batch trial", seen_turn, set(F.TURN_KEYS))
    # The fixture's hand-written lines have the same keys.
    for arm, mk, tk in ((N, F.META_BATCH_KEYS, F.TURN_KEYS), (T, F.META_KEYS, F.TURN_LIVE_KEYS)):
        metas = read_lines(cdir(FIXTURE, SONNET, arm) / "trial_meta.jsonl")
        r.check(f"fixture sidecar lines have the runner's keys ({arm})",
                all(set(x) == set(mk) and all(set(t) == set(tk) for t in x["turns"]) for x in metas))


# ------------------------------------------------------------------ units
def test_units(r):
    # Times.
    a = F.parse_time("2026-11-26T23:59:59.500000Z", "t")
    b = F.parse_time("2026-11-27T01:59:59+02:00", "t")
    r.check_eq("times are read in UTC", (a.date().isoformat(), b.date().isoformat(), b.hour),
               ("2026-11-26", "2026-11-26", 23))
    for bad in ("2026-11-26T10:00:00", None, 5, "soon"):
        try:
            F.parse_time(bad, "t")
            r.check(f"time {bad!r} refused", False)
        except F.SidecarError:
            r.check(f"time {bad!r} refused", True)
    # The system texts, from the harness.
    r.check_eq("ten system texts with the registered sha256",
               {arm: {t: F._text_sha(F.system_text(arm, t)) for t in TASKS} for arm in F.ARMS},
               F.SYSTEM_SHA256)
    # The cell spec: the rerun's loader, five tasks, three wordings.
    n, t = F.cell_spec(F.REGISTERED, HAIKU, N), F.cell_spec(F.REGISTERED, SONNET, T)
    r.check_eq("no-tools spec", (n.name, n.n_rows, n.per_variant, n.per_task_variant, n.variants,
                                 n.with_tools, n.tasks, n.k_domains, n.layer, n.prompt_style),
               ("claude-haiku-5-5_no-tools", 4560, 1520,
                {"solve": 100, "validate_domain": 120, "validate_problem": 200,
                 "validate_plan": 1000, "simulate": 100}, (11, 12, 13), False, TASKS, 20,
                S.RERUN, "minimal"))
    r.check_eq("tools spec", (t.name, t.with_tools, t.n_rows), ("claude-sonnet-5-5_tools", True, 4560))
    # VOID arithmetic on the registered size: 45 of 4,560 is under 1%, 46 is over.
    r.check_eq("VOID line on 4,560 rows", (45 > F.VOID_FRAC * 4560, 46 > F.VOID_FRAC * 4560),
               (False, True))
    # The registered trial list, when the pinned ground truth is on this machine.
    path = gt_cache_path()
    if path is None:
        print("  SKIPPED registered trial list: results/derived/gt_cache.json is not on this machine")
    else:
        gt = F.load_gt_cache(path)
        grid = F.registered_grid(REPO_ROOT / "domains", gt)
        from collections import Counter
        r.check_eq("registered trial list: 4,560 trials, the per-task counts, 20 domains",
                   (len(grid), dict(Counter(k[0] for k in grid)), len({k[1] for k in grid})),
                   (4560, F.PER_TASK, 20))
        cells = load_fixture_cells()
        try:
            F.check_grid(cells, grid)
            r.check("a folder that does not hold the registered list is refused", False)
        except CPF.Halt as e:
            r.check("a folder that does not hold the registered list is refused",
                    "not the registered list" in str(e), str(e))
        bad = path.parent / "does_not_exist.json"
        try:
            F.load_gt_cache(bad)
            r.check("a missing ground-truth cache halts", False)
        except CPF.Halt:
            r.check("a missing ground-truth cache halts", True)
    tmp = Path(tempfile.mkdtemp(prefix="f55_gt_"))
    try:
        (tmp / "gt.json").write_text("{}")
        try:
            F.load_gt_cache(tmp / "gt.json")
            r.check("another ground-truth cache halts", False)
        except CPF.Halt as e:
            r.check("another ground-truth cache halts", "is not the pinned" in str(e), str(e))
        (tmp / "pv.json").write_text("[]")
        try:
            F.stored_verdicts(tmp / "pv.json")
            r.check("another stored-verdict table halts", False)
        except CPF.Halt as e:
            r.check("another stored-verdict table halts", "is not the recorded" in str(e), str(e))
    finally:
        shutil.rmtree(tmp)
    # The stored-verdict check itself.
    v = CPF.Verdicts(CPF.table_route({("d", "p", ("(a)",)): True}))
    r.check_eq("route check counts the plans", F.check_route_table(v, {("d", "p", ("(a)",)): True}), 1)
    for stored in ({("d", "p", ("(a)",)): False}, {("d", "p", ("(a)",)): "yes"}):
        try:
            F.check_route_table(v, stored)
            r.check("route check halts on a disagreement or a non-bool", False)
        except CPF.Halt:
            r.check("route check halts on a disagreement or a non-bool", True)


def gt_cache_path() -> Path | None:
    """The pinned cache: in this checkout, or in the main checkout of a worktree."""
    rel = "results/derived/gt_cache.json"
    cands = [REPO_ROOT / rel]
    try:
        common = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True).stdout.strip()
        if common:
            cands.append((Path(common) if Path(common).is_absolute()
                          else REPO_ROOT / common).resolve().parent / rel)
    except OSError:
        pass
    return next((p for p in cands if p.exists()), None)


# ------------------------------------------------------------------ the live gate
def test_live_gate(r):
    out = Path(tempfile.mkdtemp(prefix="f55_live_"))
    try:
        base = ["--root", "/nonexistent/frontier55", "--gt-cache", "/nonexistent/gt.json",
                "--plan-verdicts", "/nonexistent/pv.json", "--marketplace", "/nonexistent",
                "--out", str(out)]
        code, err, _ = run_main(base)
        r.check("live without --i-have-frozen reads nothing",
                code == 2 and "refusing to read the Claude run" in err, err)
        for label, h in (("a wrong hash", "0" * 64), ("the matched run's hash", MR.package_sha256()),
                         ("the control's hash", CPF.package_sha256()),
                         ("the rerun's hash", RUN.package_sha256())):
            code, err, _ = run_main(base + ["--i-have-frozen", h])
            r.check(f"live with {label} reads nothing",
                    code == 2 and "refusing to read the Claude run" in err, err)
        code, err, _ = run_main(base + ["--i-have-frozen", F.package_sha256()])
        r.check("with the right hash it goes on to the pinned inputs (and finds none)",
                code == 2 and "refusing" not in err and "/nonexistent/gt.json" in err, err)
        pilot = ["--root", "/nonexistent/frontier55-pilot"] + base[2:]
        code, err, _ = run_main(pilot + ["--i-have-frozen", F.package_sha256()])
        r.check("a pilot folder is never analysed", code == 2 and "is a pilot folder" in err, err)
        code, err, _ = run_main(base[:-4] + ["--out", str(out), "--i-have-frozen", F.package_sha256()])
        r.check("live mode needs the validator checkout",
                code == 2 and "requires --marketplace" in err, err)
        code, err, _ = run_main(base + ["--i-have-frozen", F.package_sha256(), "--numbers"])
        r.check("--numbers is checked before anything is read",
                code == 2 and ("markers" in err or "/nonexistent/gt.json" in err), err)
        r.check_eq("nothing written", list(out.iterdir()), [])
    finally:
        shutil.rmtree(out)


def test_package_hash(r):
    r.check_eq("DEPENDENCIES sorted, no duplicates", list(F.DEPENDENCIES),
               sorted(set(F.DEPENDENCIES)))
    listed = {rel for rel, _ in F.frozen_files()}
    r.check("the matched run's script and every file it hashes are listed",
            {rel for rel, _ in MR.frozen_files()} <= listed)
    r.check("the frozen rerun package and the control are listed",
            {rel for rel, _ in RUN.frozen_files()} <= listed
            and {rel for rel, _ in CPF.frozen_files()} <= listed)
    r.check("the script itself is hashed", F.SCRIPT in listed)
    for d in ("tools/reanalysis/matched_run.py", "tools/reanalysis/control_prompt_fix.py",
              "tools/reanalysis/rq23_metrics.py", "tools/reanalysis/rq1_metrics.py",
              "tools/delivered_rerun/schema.py", "tools/delivered_rerun/grade.py",
              "tools/delivered_rerun/stats.py", "tools/e2e_regrade.py", "pddl_eval/runner.py"):
        r.check(f"listed: {d}", d in listed)
    r.check("the runner's files are not part of the package (they are not imported)",
            not any(rel.startswith("tools/frontier55/") for rel in listed))
    r.check("every listed file exists", all(p.is_file() for _, p in F.frozen_files()))
    r.check_eq("the package is the matched run's files and this script",
               listed, {rel for rel, _ in MR.frozen_files()} | {F.SCRIPT})
    # Every repo module the script imports, in a fresh interpreter.
    code = ("import os, sys; import tools.reanalysis.frontier55 as M; "
            "R = os.getcwd(); print('\\n'.join(sorted(os.path.relpath(m.__file__, R) for m in "
            "list(sys.modules.values()) if getattr(m, '__file__', None) and "
            "os.path.abspath(m.__file__).startswith(R + os.sep))))")
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True,
                          text=True)
    imported = set(proc.stdout.split())
    r.check("import ran", proc.returncode == 0 and imported, proc.stderr[-300:])
    r.check("DEPENDENCIES cover every imported repo module", imported <= listed,
            sorted(imported - listed))
    r.check("the runner is not imported", not any("frontier55/" in m for m in imported))
    h = F.package_sha256()
    r.check("package hash is a stable sha256", len(h) == 64 and h == F.package_sha256())
    r.check("this run's hash is no other package's",
            h not in (MR.package_sha256(), CPF.package_sha256(), RUN.package_sha256()))
    r.check_eq("the frozen rerun package hash is unchanged", RUN.package_sha256(), FROZEN_RERUN_SHA)
    r.check_eq("the control's package hash is unchanged", CPF.package_sha256(), FROZEN_CONTROL_SHA)
    r.check_eq("the matched run's package hash is unchanged", MR.package_sha256(), FROZEN_MATCHED_SHA)
    proc = subprocess.run([sys.executable, "-m", "tools.reanalysis.frontier55",
                           "--print-package-hash"], cwd=REPO_ROOT, capture_output=True, text=True)
    r.check("--print-package-hash prints the hash last",
            proc.returncode == 0 and proc.stdout.strip().splitlines()[-1].startswith(h), proc.stderr)
    proc = subprocess.run([sys.executable, "-O", "-m", "tools.reanalysis.frontier55",
                           "--print-package-hash"], cwd=REPO_ROOT, capture_output=True, text=True)
    r.check("python -O refused", proc.returncode != 0 and "python -O" in proc.stderr,
            proc.stderr[-300:])


# ------------------------------------------------------------------ the clause map (gate 3)
def test_traceability(r):
    """Every `name` (F:<line>) of the clause map points at the line that defines the name,
    every bare F:<line> at a line of code, and every T:<test> at a test of this file."""
    import re
    doc = (REPO_ROOT / "development" / "reference" / "frontier55_traceability.md").read_text()
    doc = " ".join(doc.split())
    src = (REPO_ROOT / F.SCRIPT).read_text().splitlines()
    named = re.findall(r"`([A-Za-z_][A-Za-z_0-9.]*)` \(F:(\d+)\)", doc)
    r.check("the map cites definitions by name and line", len(named) >= 60, len(named))
    for name, line in named:
        name = name.split(".")[0]
        text = src[int(line) - 1] if int(line) <= len(src) else ""
        ok = re.match(rf"(def {name}\(|class {name}\b|{name}\b[^=]*= )", text) is not None
        r.check(f"`{name}` (F:{line}) is defined on that line", ok, text[:80])
    bare = {int(n) for n in re.findall(r"F:(\d+)", doc)}
    r.check("every cited line is a line of code",
            all(n <= len(src) and src[n - 1].strip() and not src[n - 1].strip().startswith("#")
                for n in bare), sorted(n for n in bare if n > len(src) or not src[n - 1].strip()))
    tests = set(re.findall(r"T:(test_[a-z_]+)", doc))
    here = {k for k in globals() if k.startswith("test_")}
    r.check("every cited test exists", tests <= here, sorted(tests - here))
    r.check("every test of this file is cited",
            here - {"test_traceability"} <= tests | {"test_fixture_is_builder_output"},
            sorted(here - tests))
    for words in ("Freeze candidate. Not frozen.", "Open points for the owner", "Not implemented"):
        r.check(f"the map says: {words}", words in doc)
    r.check_eq("the map lists every open point of the code",
               len(re.findall(r"^\d+\. \*\*", (REPO_ROOT / "development" / "reference"
                                                 / "frontier55_traceability.md").read_text(),
                              flags=re.M)),
               sum("# OPEN:" in ln for ln in src))


# ------------------------------------------------------------------ registered constants
def test_constants(r):
    try:
        F.check_constants()
        F.check_design(F.REGISTERED, registered=True)
        r.check("registered constants and design pass", True)
    except C.RegisteredCheckFailed as e:
        r.check("registered constants and design pass", False, str(e))
    sha = F.SYSTEM_SHA256
    flips = {
        "RUN_NAME": "frontier55-pilot", "MODELS": ("claude-haiku-5-5",),
        "ARMS": ("tools", "no-tools"), "TASKS": ("solve", "simulate"), "WORDINGS": (11, 12, 13, 14),
        "PER_TASK": {**F.PER_TASK, "validate_plan": 300}, "N_FOLDER": 4_561, "TOTAL_TRIALS": 9_120,
        "K_DOMAINS": 19,
        "SYSTEM_SHA256": {**sha, "no-tools": {**sha["no-tools"], "validate_plan": sha["tools"]["validate_plan"]}},
        "GT_CACHE_SHA256": "0" * 64,
        "SETTINGS": {**F.SETTINGS, "claude-haiku-5-5": {"thinking": {"type": "disabled"}, "effort": "high"}},
        "MAY_THINK": (), "OUTPUT_CAP": {**F.OUTPUT_CAP, "solve": 6_144}, "MAX_ROUND_TRIPS": 20,
        "TOOLS_COMMIT": "e428f17", "TOOLS_SHA256": "0" * 64, "PYVALIDATOR": "0.1.6",
        "API_HOST": "example.com",
        "TRANSPORT": {"no-tools": "live", "tools": "live"}, "STORAGE_CAP": 16_384,
        "LOADER_TAG": "claude-haiku-5-5", "MATCHED_GRADE_TASKS": ("solve",),
        "RERUN_GRADE_TASKS": ("validate_domain", "validate_problem"), "N_CONTRASTS": 5,
        "LEVEL": 0.90, "B_BOOT": 1_000, "SEED": 1, "HOLM_FAMILY": 10, "HOLM_ALPHA": 0.10,
        "LABELS": ("tools ahead", "no tools ahead"), "NOT_AFTER_HOLM": " (not significant)",
        "RQ2_CLASSES": ("none", "right_only", "other_only"), "LATER_FRAC": 0.10, "VOID_FRAC": 0.05,
        "UNREAD_FRAC": 0.10, "REFUSAL_TRIPWIRE_FRAC": 0.5,
        "OUTCOMES": ("answer",), "ERROR_OUTCOMES": ("refusal",),
        "VOID_KINDS": ("refusal", "pause", "unknown stop", "scoring error"),
        "ERROR_KINDS": ("refusal",), "THINK_OVERFLOW": "truncated_no_answer",
        "E_CAP_EMPTY": "think_overflow",
    }
    for name, value in flips.items():
        old = getattr(F, name)
        setattr(F, name, value)
        try:
            F.check_constants()
            r.check(f"flipped {name} is caught", False)
        except C.RegisteredCheckFailed:
            r.check(f"flipped {name} is caught", True)
        except Exception as e:  # noqa: BLE001 - any other failure is a test failure
            r.check(f"flipped {name} is caught", False, repr(e))
        finally:
            setattr(F, name, old)
    for field, value in (("per_task", {**F.PER_TASK, "solve": 297}), ("n_folder", 4_557),
                         ("per_wording", 1_519), ("k_domains", 19)):
        d = dataclasses.replace(F.REGISTERED, **{field: value})
        try:
            F.check_design(d, registered=True)
            r.check(f"design {field} is caught", False)
        except C.RegisteredCheckFailed:
            r.check(f"design {field} is caught", True)
    try:
        F.check_design(dataclasses.replace(F.REGISTERED), registered=True)
        r.check("a copy of REGISTERED is not REGISTERED", False)
    except C.RegisteredCheckFailed:
        r.check("a copy of REGISTERED is not REGISTERED", True)
    for bad in ({**{t: 60 for t in TASKS}, "solve": 61}, {t: 60 for t in TASKS[:4]}):
        try:
            F.check_design(F.Design("x", bad, 300, 100, 20), registered=False)
            r.check("a fixture design that does not add up is caught", False)
        except C.RegisteredCheckFailed:
            r.check("a fixture design that does not add up is caught", True)
    # The frozen bootstrap refuses a contrast that does not hold the 20 domains.
    try:
        CPF.boot([1.0, 0.0], ["d01", "d02"], 20, "unit")
        r.check("k = 20 is asserted", False)
    except C.RegisteredCheckFailed:
        r.check("k = 20 is asserted", True)
    try:
        ST.holm({"a": 0.1, "b": 0.2}, F.HOLM_FAMILY)
        r.check("the Holm family of five is asserted", False)
    except C.RegisteredCheckFailed:
        r.check("the Holm family of five is asserted", True)


def main():
    r = TestResults("frontier55_analysis")
    test_fixture_is_builder_output(r)
    test_planted_answers(r)
    test_base(r)
    test_traps(r)
    test_refusals(r)
    test_tripwires(r)
    test_runner_shapes(r)
    test_units(r)
    test_live_gate(r)
    test_package_hash(r)
    test_traceability(r)
    test_constants(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
