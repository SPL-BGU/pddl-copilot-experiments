"""Unit tests for tools/d5b/ (D5b ground truth, handoff 2026-11-09 item 9).

Pure Python, standard library only: no planner, no validator. Covers the size
ladder and its generator commands (against IPC 2023's own recorded testing
parameters), the sha256 manifest build and diff, the 1800 s job selection
(only pairs unsolved at 120 s), and the solved-share computation. Two checks
read sibling or clone files when present and are skipped otherwise.

Run standalone: `python3 tests/test_d5b.py`
"""
from __future__ import annotations

import ast
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402
from tools.d5b import ladder, manifest, shares  # noqa: E402
from tools.d5b import fd_worker, pipeline  # noqa: E402  (both import only stdlib at top)

_SOLVER_REL = Path("pddl-copilot/plugins/pddl-solver/server/solver_server.py")
# The sibling repo sits next to the main checkout; a worktree lives deeper
# (.claude/worktrees/<name>), so look up every parent.
SIBLING_SOLVER = next((p / _SOLVER_REL for p in REPO_ROOT.parents if (p / _SOLVER_REL).exists()),
                      REPO_ROOT.parent / _SOLVER_REL)
CLONE = REPO_ROOT / "external" / "ipc2023-learning"


def test_ladder(r: TestResults) -> None:
    specs = ladder.ladder()
    r.check_eq("120 problems", len(specs), 120)
    r.check_eq("10 per domain and tier",
               set(Counter((s.domain, s.tier) for s in specs).values()), {10})
    seeds = {s.seed for s in specs}
    r.check_eq("30 distinct seeds (shared across domains)", len(seeds), 30)
    r.check("no IPC testing or training seed",
            not seeds & set(range(1007, 1037)) and not seeds & set(range(42, 142)))
    for d in ladder.DOMAINS:
        for t in ladder.TIERS:
            tier = [s for s in specs if s.domain == d and s.tier == t]
            rng = ladder.IPC_TEST_RANGES[d][t]
            r.check_eq(f"{d}/{t} first = range start", tier[0].params, {k: v[0] for k, v in rng.items()})
            for k, (lo, hi) in rng.items():
                vals = [s.params[k] for s in tier]
                r.check(f"{d}/{t}/{k} non-decreasing", vals == sorted(vals), str(vals))
                if not (d == "rovers" and k == "objectives"):  # IPC's rovers quirk overshoots
                    r.check(f"{d}/{t}/{k} within range", lo <= min(vals) and max(vals) <= hi, str(vals))
    s = specs[0]
    r.check_eq("blocksworld command", s.shell_command("easy"),
               "python blocksworld.py -b 5 -out easy -id 1 --seed 5001")
    m = [x for x in specs if x.domain == "miconic"][0]
    r.check_eq("miconic command keeps PYTHONHASHSEED=0", m.shell_command("easy"),
               "PYTHONHASHSEED=0 python miconic.py -p 1 -f 4 -o easy -i 1 --seed 5001")


def test_ipc_testing_params(r: TestResults) -> None:
    # Values from the ";;" header lines of IPC 2023's committed testing files.
    def p(d, t, i):
        return ladder.ipc_testing_commands(d, t)[i - 1]
    r.check_eq("bw easy p01", (p("blocksworld", "easy", 1).params, p("blocksworld", "easy", 1).seed),
               ({"blocks": 5}, 1007))
    r.check_eq("bw hard p30", (p("blocksworld", "hard", 30).params, p("blocksworld", "hard", 30).seed),
               ({"blocks": 488}, 1036))
    r.check_eq("miconic hard p30", p("miconic", "hard", 30).params, {"passengers": 485, "floors": 196})
    r.check_eq("rovers medium p01", p("rovers", "medium", 1).params,
               {"rovers": 5, "waypoints": 15, "cameras": 5, "objectives": 15})
    r.check_eq("satellite hard p01", p("satellite", "hard", 1).params,
               {"satellites": 50, "instruments": 50, "modes": 5, "directions": 40})
    if not CLONE.exists():
        print("  (skip: no clone at external/ipc2023-learning for the full header check)")
        return
    bad = 0
    for d in ladder.DOMAINS:
        for t in ladder.TIERS:
            for s in ladder.ipc_testing_commands(d, t):
                head = (CLONE / d / "testing" / t / s.problem_name).read_text().splitlines()[0]
                got = dict(re.findall(r"(\w+)=([^,\s]+)", head))
                want = {k: str(v) for k, v in s.params.items()}
                want.update(instance_id=str(s.instance_id), seed=str(s.seed))
                bad += any(got.get(k) != v for k, v in want.items())
    r.check_eq("all 360 IPC testing headers match our parameters", bad, 0)


def test_strategies_match_plugin(r: TestResults) -> None:
    r.check_eq("three strategies", set(fd_worker.FD_STRATEGIES), set(pipeline.STRATEGIES))
    if not SIBLING_SOLVER.exists():
        print("  (skip: sibling pddl-solver not found)")
        return
    tree = ast.parse(SIBLING_SOLVER.read_text())
    found = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FD_STRATEGIES" for t in node.targets):
            found = ast.literal_eval(node.value)
    r.check_eq("FD_STRATEGIES identical to the pddl-solver plugin", fd_worker.FD_STRATEGIES, found)
    src = SIBLING_SOLVER.read_text()
    r.check("plugin default timeout is 120", 'os.environ.get("PDDL_TIMEOUT", "120")' in src)


def _fake_tree(root: Path, specs) -> None:
    for d in {s.domain for s in specs}:
        (root / "clone" / d).mkdir(parents=True, exist_ok=True)
        (root / "clone" / d / "domain.pddl").write_text(f"(define (domain {d}))\n")
    for s in specs:
        f = root / "work" / manifest.problem_relpath(s.domain, s.tier, s.problem_name)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"; {s.domain} {s.tier} {s.instance_id}\n")


def test_manifest(r: TestResults) -> None:
    specs = [s for s in ladder.ladder() if s.domain == "blocksworld" and s.tier == "easy"][:3]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fake_tree(root, specs)
        m = manifest.build(root / "clone", root / "work", specs)
        r.check_eq("3 problems", len(m["problems"]), 3)
        r.check_eq("domain hash", m["domain_files"]["blocksworld"],
                   manifest.sha256_file(root / "clone" / "blocksworld" / "domain.pddl"))
        e = m["problems"]["problems/blocksworld/easy/p01.pddl"]
        r.check_eq("record carries seed and params", (e["seed"], e["params"]), (5001, {"blocks": 5}))
        r.check_eq("identical tree, no diff", manifest.diff(m, manifest.build(root / "clone", root / "work", specs)), [])
        (root / "work" / "problems/blocksworld/easy/p02.pddl").write_text("changed\n")
        d = manifest.diff(m, manifest.build(root / "clone", root / "work", specs))
        r.check("changed problem is reported", len(d) == 1 and "p02" in d[0], str(d))
        (root / "work" / "problems/blocksworld/easy/p03.pddl").unlink()
        try:
            manifest.build(root / "clone", root / "work", specs)
            r.check("missing problem refused", False, "no exception")
        except FileNotFoundError:
            r.check("missing problem refused", True)
    committed = json.loads(manifest.MANIFEST_PATH.read_text())
    r.check_eq("committed manifest: 120 problems", len(committed["problems"]), 120)
    r.check_eq("committed manifest pins the commit", committed["spec"]["source_commit"], ladder.IPC_COMMIT)
    r.check_eq("committed manifest spec = current ladder spec", committed["spec"], ladder.spec_record())
    r.check("no absolute paths in committed manifest", "/Users/" not in manifest.MANIFEST_PATH.read_text())


def _rec(problem, strategy, lim, status, valid=None, t=1.0):
    d = {"key": f"{problem}|{strategy}|{lim}", "problem": problem, "strategy": strategy,
         "time_limit": lim, "status": status, "solve_time": t}
    if valid is not None:
        d["val_valid"] = valid
    return d


def test_jobs_for_1800(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "runs").mkdir()
        recs = [{"_header": True}]
        for s in ladder.ladder():
            rel = manifest.problem_relpath(s.domain, s.tier, s.problem_name)
            for st in pipeline.STRATEGIES:
                ok = s.tier == "easy"
                recs.append(_rec(rel, st, 120, "solved" if ok else "timeout", True if ok else None))
        # one easy pair whose plan VAL rejected: must be rerun at 1800 s
        bad_rel = "problems/rovers/easy/p03.pddl"
        recs.append({"key": f"{bad_rel}|astar_lmcut|120", "status": "requeued"})
        recs.append(_rec(bad_rel, "astar_lmcut", 120, "solved", False))
        pipeline.runs_file(work, 120).write_text("".join(json.dumps(x) + "\n" for x in recs))
        jobs = pipeline.jobs_for(1800, work)
        r.check_eq("1800 s jobs = unsolved pairs (medium + hard) + 1 VAL-rejected", len(jobs), 4 * 20 * 3 + 1)
        r.check("no solved easy pair rerun", all("/easy/" not in p for p, _ in jobs if p != bad_rel))
        r.check_eq("120 s jobs = all pairs", len(pipeline.jobs_for(120, work)), 360)
        # a plan without a VAL verdict blocks the 1800 s selection
        unv = _rec("problems/rovers/easy/p04.pddl", "astar_lmcut", 120, "solved", None)
        pipeline.runs_file(work, 120).write_text("".join(json.dumps(x) + "\n" for x in recs + [unv]))
        try:
            pipeline.jobs_for(1800, work)
            r.check("unfinished VAL refused", False, "no exception")
        except SystemExit:
            r.check("unfinished VAL refused", True)
        # an incomplete 120 s pass refuses the 1800 s selection
        pipeline.runs_file(work, 120).write_text("".join(json.dumps(x) + "\n" for x in recs[:10]))
        try:
            pipeline.jobs_for(1800, work)
            r.check("incomplete 120 s pass refused", False, "no exception")
        except SystemExit:
            r.check("incomplete 120 s pass refused", True)


def test_shares(r: TestResults) -> None:
    A, B = "problems/blocksworld/easy/p01.pddl", "problems/blocksworld/easy/p02.pddl"
    C = "problems/miconic/hard/p01.pddl"
    with tempfile.TemporaryDirectory() as tmp:
        p120, p1800 = Path(tmp) / "a.jsonl", Path(tmp) / "b.jsonl"
        lines120 = [
            {"_header": True},
            _rec(A, "lazy_greedy_cea", 120, "solved", True),
            _rec(A, "lazy_greedy_ff", 120, "solved", False),       # VAL rejected -> not solved
            _rec(A, "astar_lmcut", 120, "timeout"),
            {"key": "x", "problem": B, "strategy": "lazy_greedy_cea", "status": "requeued"},
            _rec(B, "lazy_greedy_cea", 120, "timeout"),
            _rec(B, "lazy_greedy_ff", 120, "memout_cap"),
            _rec(B, "astar_lmcut", 120, "timeout"),
            _rec(C, "lazy_greedy_cea", 120, "timeout"),
            _rec(C, "lazy_greedy_ff", 120, "timeout"),
            _rec(C, "astar_lmcut", 120, "timeout"),
        ]
        lines1800 = [
            _rec(A, "astar_lmcut", 1800, "solved", True, t=1000.0),
            _rec(A, "lazy_greedy_ff", 1800, "solved", True),
            _rec(B, "lazy_greedy_cea", 1800, "timeout"),
            _rec(B, "lazy_greedy_ff", 1800, "timeout"),
            _rec(B, "astar_lmcut", 1800, "timeout"),
            _rec(C, "lazy_greedy_cea", 1800, "timeout"),
            # C ff and astar not run yet -> pending
        ]
        p120.write_text("".join(json.dumps(x) + "\n" for x in lines120))
        p1800.write_text("".join(json.dumps(x) + "\n" for x in lines1800))
        r120, r1800 = shares.load(p120), shares.load(p1800)
        r.check_eq("requeue notes and headers skipped", len(r120), 9)
        o = shares.pair_outcomes(r120, r1800)
        r.check_eq("A cea", o[(A, "lazy_greedy_cea")], {120: True, 1800: True})
        r.check_eq("A ff: VAL-rejected at 120, solved at 1800", o[(A, "lazy_greedy_ff")], {120: False, 1800: True})
        r.check_eq("A astar solved only at 1800", o[(A, "astar_lmcut")], {120: False, 1800: True})
        r.check_eq("C ff pending", o[(C, "lazy_greedy_ff")], {120: False, 1800: None})
        c = shares.cells(o)
        r.check_eq("bw easy cea 120", dict(c[("blocksworld", "easy", "lazy_greedy_cea", 120)]),
                   {"solved": 1, "unsolved": 1})
        r.check_eq("bw easy any 120", dict(c[("blocksworld", "easy", "any", 120)]), {"solved": 1, "unsolved": 1})
        r.check_eq("bw easy astar 1800", dict(c[("blocksworld", "easy", "astar_lmcut", 1800)]),
                   {"solved": 1, "unsolved": 1})
        r.check_eq("miconic hard any 1800 pending", dict(c[("miconic", "hard", "any", 1800)]), {"pending": 1})
        r.check_eq("miconic hard cea 1800", dict(c[("miconic", "hard", "lazy_greedy_cea", 1800)]), {"unsolved": 1})
        unv = dict(r120[(A, "lazy_greedy_cea")], val_valid=None, val_status="VAL_NOT_FINISHED")
        o2 = shares.pair_outcomes({(A, "lazy_greedy_cea"): unv}, {})
        r.check_eq("VAL unfinished = pending at both limits", o2[(A, "lazy_greedy_cea")], {120: None, 1800: None})
        r.check_eq("not solved status", shares.is_solved(_rec(A, "x", 120, "memout_cap")), False)
        r.check_eq("fmt plain", shares.fmt(Counter(solved=1, unsolved=1)), "1/2 (50%)")
        r.check_eq("fmt pending", shares.fmt(Counter(solved=1, unsolved=1, pending=2)),
                   "1-3/4 (25-75%, 2 pending)")
        rep = shares.report(r120, r1800)
        r.check("report counts VAL rejection", "plans rejected by VAL: 1" in rep, rep)
        r.check("report counts pending", "or VAL unfinished): 2" in rep, rep)
        r.check("report flags near-limit solve", "took over half the limit: 1" in rep, rep)
        rows = shares.numbers_rows(r120, r1800, [{"valid": True}] * 5)
        r.check_eq("numbers rows: header + 2 + syntax + 4 share rows + VAL row", rows.count("\n"), 8)
        r.check("numbers rows: syntax row", "5 / 5 files valid" in rows, rows)
        r.check("numbers rows: VAL row", "| 1 of 4 |" in rows, rows)
        r.check("numbers rows: default strategy at 120 s",
                "plugin default `lazy_greedy_cea` (3 problems, plan VAL-valid) | **easy 1/2 (50%), "
                "medium -, hard 0/1 (0%)" in rows, rows)


def main() -> None:
    r = TestResults("test_d5b")
    test_ladder(r)
    test_ipc_testing_params(r)
    test_strategies_match_plugin(r)
    test_manifest(r)
    test_jobs_for_1800(r)
    test_shares(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
