"""D5b ground truth pipeline: generate, validate, solve (no model runs).

Run with the D5b scratch venv (tools/d5b/requirements.txt), from the repo root:

    PY=external/d5b-venv/bin/python
    $PY -m tools.d5b.pipeline generate            # IPC generators -> external/d5b-work/problems
    $PY -m tools.d5b.manifest --check             # hashes match tools/d5b/manifest.json
    $PY -m tools.d5b.pipeline validate            # pyvalidator + KCL VAL, every domain+problem
    $PY -m tools.d5b.pipeline solve --time-limit 120    # KCL VAL on every plan, inline
    $PY -m tools.d5b.pipeline val --time-limit 120 --checker kcl    # only if a VAL check was cut off
    $PY -m tools.d5b.pipeline solve --time-limit 1800   # only pairs unsolved at 120 s
    $PY -m tools.d5b.pipeline val --time-limit 1800 --checker kcl
    $PY -m tools.d5b.pipeline val --time-limit 120 --checker pyval  # harness grader, slow
    $PY -m tools.d5b.pipeline val --time-limit 1800 --checker pyval
    python -m tools.d5b.shares                    # solved shares (repo venv is fine)

VAL. "Solved" means a plan that KCL VAL accepts (tools/d5b/kval.py: the macOS
build C1 used, sha256 44a07d6d...). The harness grader, pddl-pyvalidator 0.1.6,
is run on the same plans afterwards with `val --checker pyval` and compared
with VAL in tools.d5b.shares; it is far too slow on long plans to run inside
the timed passes (minutes per plan where VAL takes seconds).

All outputs go under --work (default external/d5b-work, gitignored). Nothing
is written under results/.

solve. One job per (problem, strategy) for the three pddl-solver strategies.
Each job is a separate process (tools.d5b.fd_worker), so the parent can watch
its memory. Fast Downward searches are deterministic, so a pair solved within
120 s is also solved within 1800 s with the same plan; the 1800 s pass therefore
runs only the (problem, strategy) pairs that were NOT solved in the 120 s pass,
and tools.d5b.shares counts a pair as solved within 1800 s if it was solved in
either pass. Wall-clock limits on a loaded laptop are not exact: a run near the
limit can land either side of it (shares prints how many solved runs were close).

Memory. The plugin sets no memory limit; on a 24 GiB laptop we need one. Each
run is killed above --mem-cap-gib (default 8, the limit Corrêa et al. used) and
recorded as "memout_cap". New jobs start only while the running jobs' total RSS
is under --mem-budget-gib; if the total passes the budget anyway, the youngest
job is killed and requeued (rerun later from scratch; the search is
deterministic, so only its timing changes). Requeues are logged.

The solve pass is resumable: rerunning the same command skips every job that
already has a final record in the output file.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from tools.d5b import kval, ladder, shares
from tools.d5b.manifest import problem_relpath

REPO = Path(__file__).resolve().parents[2]
STRATEGIES = ("lazy_greedy_cea", "lazy_greedy_ff", "astar_lmcut")
GIB = 1 << 30


def runs_file(work: Path, time_limit: int) -> Path:
    return work / "runs" / f"fd_{time_limit}s.jsonl"


def job_key(rel: str, strategy: str, time_limit: int) -> str:
    return f"{rel}|{strategy}|{time_limit}"


# --------------------------------------------------------------------- generate
def cmd_generate(a) -> int:
    clone, work = a.clone.resolve(), a.work.resolve()
    got = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if got != ladder.IPC_COMMIT:
        print(f"clone is at {got}, expected {ladder.IPC_COMMIT}; stop", file=sys.stderr)
        return 1
    n = 0
    for s in ladder.ladder():
        # Run from <work>/problems/<domain> with the bare tier name as the
        # output folder: the generator writes its output folder into line 1 of
        # the file, so an absolute path would make the hashes depend on where
        # the checkout lives.
        cwd = work / "problems" / s.domain
        (cwd / s.tier).mkdir(parents=True, exist_ok=True)
        argv = [sys.executable, str(clone / s.domain / s.argv[0])] + \
            [s.tier if x == "{OUT}" else x for x in s.argv[1:]]
        env = dict(os.environ, PYTHONPATH=str(clone), **s.env)
        subprocess.run(argv, cwd=cwd, env=env, check=True, stdout=subprocess.DEVNULL)
        n += 1
    print(f"generated {n} problems under {work / 'problems'}")
    return 0


def cmd_repro_ipc(a) -> int:
    """Check our command builder: rebuild IPC 2023's own testing sets (30 per
    tier, seed 1007) and compare them with the files committed in the clone.
    Line 1 of each file records the output folder, so it is compared with
    that folder name swapped back to IPC's "testing/<tier>"."""
    clone, work = a.clone.resolve(), a.work.resolve()
    ok = bad = 0
    for d in ladder.DOMAINS:
        for t in ladder.TIERS:
            out = work / "ipc_repro" / d / t
            out.mkdir(parents=True, exist_ok=True)
            for s in ladder.ipc_testing_commands(d, t):
                argv = [sys.executable] + [str(out) if x == "{OUT}" else x for x in s.argv]
                env = dict(os.environ, PYTHONPATH=str(clone), **s.env)
                subprocess.run(argv, cwd=clone / d, env=env, check=True, stdout=subprocess.DEVNULL)
                mine = (out / s.problem_name).read_text().replace(f"out_folder={out}", f"out_folder=testing/{t}")
                theirs = (clone / d / "testing" / t / s.problem_name).read_text()
                if mine == theirs:
                    ok += 1
                else:
                    bad += 1
                    print(f"differs: {d}/testing/{t}/{s.problem_name}")
    print(f"repro-ipc: {ok} of {ok + bad} IPC 2023 testing problems rebuilt byte for byte")
    return 0 if bad == 0 else 1


# --------------------------------------------------------------------- validate
def cmd_validate(a) -> int:
    """Every domain + problem through pddl-pyvalidator (`valid`) and KCL VAL
    (`kval_valid`; a domain file is checked together with its first problem,
    since VAL needs both)."""
    from pyval import PDDLValidator
    import importlib.metadata as md

    clone, work = a.clone.resolve(), a.work.resolve()
    kbin = _kcl_bin(a)
    out = work / "validate.jsonl"
    bad = 0
    with open(out, "w") as f:
        f.write(json.dumps({"_header": True, "pddl-pyvalidator": md.version("pddl-pyvalidator"),
                            "kcl_val_sha256": kval.binary_sha256(kbin)}) + "\n")
        for d in ladder.DOMAINS:
            r = PDDLValidator().validate_syntax(str(clone / d / "domain.pddl"), None)
            first = work / problem_relpath(d, ladder.TIERS[0], "p01.pddl")
            k = kval.check_files(kbin, str(clone / d / "domain.pddl"), str(first))
            rec = {"file": f"{d}/domain.pddl", "valid": bool(r.is_valid), "status": str(r.status), **k}
            bad += not (rec["valid"] and rec["kval_valid"])
            f.write(json.dumps(rec) + "\n"); f.flush()
        for s in ladder.ladder():
            rel = problem_relpath(s.domain, s.tier, s.problem_name)
            r = PDDLValidator().validate_syntax(str(clone / s.domain / "domain.pddl"), str(work / rel))
            k = kval.check_files(kbin, str(clone / s.domain / "domain.pddl"), str(work / rel))
            rec = {"file": rel, "valid": bool(r.is_valid), "status": str(r.status), **k}
            if not (rec["valid"] and rec["kval_valid"]):
                bad += 1
                rec["report"] = r.report()[-2000:]
            f.write(json.dumps(rec) + "\n"); f.flush()
    print(f"validate: {bad} invalid of {len(ladder.DOMAINS)} domains + {len(ladder.ladder())} problems; wrote {out}")
    return 0 if bad == 0 else 1


# ------------------------------------------------------------------------ solve
def _load_final(path: Path) -> dict:
    """key -> record, for records that are final (not requeue notes)."""
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("_header") or r.get("status") == "requeued":
                continue
            done[r["key"]] = shares.normalize(r)
    return done


def jobs_for(time_limit: int, work: Path, base_limit: int = 120) -> list[tuple[str, str]]:
    pairs = [(problem_relpath(s.domain, s.tier, s.problem_name), st)
             for s in ladder.ladder() for st in STRATEGIES]
    if time_limit == base_limit:
        return pairs
    base = _load_final(runs_file(work, base_limit))
    missing = [p for p in pairs if job_key(p[0], p[1], base_limit) not in base]
    if missing:
        raise SystemExit(f"{len(missing)} pairs have no {base_limit} s record; finish that pass first")
    unval = [k for k, r in base.items() if shares.is_solved(r) is None]
    if unval:
        raise SystemExit(f"{len(unval)} plans of the {base_limit} s pass have no KCL VAL verdict; "
                         f"run `val --checker kcl` first")
    # Deterministic search: only pairs unsolved (or with a VAL-rejected plan) at the base limit.
    return [p for p in pairs if shares.is_solved(base[job_key(p[0], p[1], base_limit)]) is False]


def _tree_rss(proc) -> int:
    import psutil
    try:
        procs = [proc] + proc.children(recursive=True)
    except psutil.NoSuchProcess:
        return 0
    tot = 0
    for p in procs:
        try:
            tot += p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return tot


def _kill_tree(proc) -> None:
    import psutil
    try:
        procs = proc.children(recursive=True) + [proc]
    except psutil.NoSuchProcess:
        return
    for p in procs:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(procs, timeout=10)


def _kcl_bin(a) -> Path:
    b = Path(a.kcl_val)
    if not b.exists():
        raise SystemExit(f"KCL VAL binary not found at {b}; see tools/d5b/kval.py")
    if kval.binary_sha256(b) != kval.EXPECTED_SHA256:
        print(f"warning: {b} is not the C1 VAL build (sha256 differs)", file=sys.stderr)
    return b


def _header(a, n_jobs: int) -> dict:
    import importlib.metadata as md
    import psutil
    return {
        "_header": True, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "time_limit": a.time_limit, "n_jobs": n_jobs, "workers": a.workers,
        "mem_cap_gib": a.mem_cap_gib, "mem_budget_gib": a.mem_budget_gib,
        "host": platform.node(), "machine": platform.machine(), "platform": platform.platform(),
        "cpu_count": os.cpu_count(), "ram_gib": round(psutil.virtual_memory().total / GIB, 1),
        "python": platform.python_version(),
        "versions": {p: md.version(p) for p in
                     ("unified-planning", "up-fast-downward", "pddl-pyvalidator", "psutil")},
        "ipc_commit": ladder.IPC_COMMIT,
        "kcl_val_sha256": kval.binary_sha256(_kcl_bin(a)),
    }


def cmd_solve(a) -> int:
    import psutil

    clone, work = a.clone.resolve(), a.work.resolve()
    kbin = _kcl_bin(a)
    out = runs_file(work, a.time_limit)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = work / "tmp" / str(a.time_limit)
    tmpdir.mkdir(parents=True, exist_ok=True)
    done = _load_final(out)
    pairs = jobs_for(a.time_limit, work)
    queue = [p for p in pairs if job_key(p[0], p[1], a.time_limit) not in done]
    if a.limit_jobs:
        queue = queue[: a.limit_jobs]
    if a.order == "small-first":  # cheapest first, so a cut-short pass covers the small tiers
        tier_rank = {t: i for i, t in enumerate(ladder.TIERS)}
        queue.sort(key=lambda p: (tier_rank[p[0].split("/")[2]], p[0].split("/")[3], p[0], p[1]))
    print(f"solve {a.time_limit}s: {len(pairs)} pairs, {len(done)} already done, {len(queue)} to run, "
          f"{a.workers} workers", flush=True)
    if not queue:
        return 0
    with open(out, "a") as f:
        f.write(json.dumps(_header(a, len(queue))) + "\n")

    deadline = time.time() + a.max_hours * 3600 if a.max_hours else None
    running: dict = {}  # key -> dict(proc, psproc, start, peak, rel, strategy, json)
    cap = a.mem_cap_gib * GIB
    budget = a.mem_budget_gib * GIB
    n_done = 0

    def write(rec):
        with open(out, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def finish(key, extra):
        nonlocal n_done
        r = running.pop(key)
        rec = {"key": key, "problem": r["rel"], "strategy": r["strategy"],
               "time_limit": a.time_limit, "peak_rss_mib": round(r["peak"] / (1 << 20)),
               "wall": round(time.time() - r["start"], 2)}
        rec.update(extra)
        parts = r["rel"].split("/")
        rec["domain"], rec["tier"] = parts[1], parts[2]
        write(rec)
        n_done += 1
        print(f"[{n_done}] {key}: {rec.get('status')} "
              f"{rec.get('solve_time', rec['wall'])}s val={rec.get('kval_valid')}", flush=True)

    def kill(key, reason, requeue=False) -> bool:
        """Kill a running job. If the planner had already finished (the job
        was killed during VAL), keep its result with VAL marked unfinished
        and return True; `pipeline val` completes the check. Otherwise
        record `reason` as the status, or requeue the job, and return False."""
        r = running[key]
        _kill_tree(r["ps"])
        r["log"].close()
        planned = json.loads(r["json"].read_text()) if r["json"].exists() else None
        if planned and planned.get("status") == "solved":
            planned.update(val_killed_by=reason)
            finish(key, planned)
            return True
        if requeue:
            running.pop(key)
            write({"key": key, "status": "requeued", "reason": "total rss over budget"})
            queue.insert(0, (r["rel"], r["strategy"]))
        else:
            finish(key, {"status": reason})
        return False

    while queue or running:
        # launch
        while (queue and len(running) < a.workers
               and (deadline is None or time.time() < deadline)):
            tot = sum(r["peak_now"] for r in running.values())
            if running and (tot > 0.75 * budget or psutil.virtual_memory().available < 3 * GIB):
                break
            rel, st = queue.pop(0)
            key = job_key(rel, st, a.time_limit)
            dom = rel.split("/")[1]
            stem = rel.replace("/", "__")
            jpath = tmpdir / f"{stem}.{st}.json"
            jpath.unlink(missing_ok=True)
            plan = work / "plans" / str(a.time_limit) / rel.replace("problems/", "").replace(".pddl", f".{st}.plan")
            log = open(tmpdir / f"{stem}.{st}.log", "w")
            proc = subprocess.Popen(
                [sys.executable, "-m", "tools.d5b.fd_worker", "--domain", str(clone / dom / "domain.pddl"),
                 "--problem", str(work / rel), "--strategy", st, "--timeout", str(a.time_limit),
                 "--plan-out", str(plan), "--json-out", str(jpath), "--kcl-val", str(kbin)],
                cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            running[key] = {"proc": proc, "ps": psutil.Process(proc.pid), "start": time.time(),
                            "peak": 0, "peak_now": 0, "rel": rel, "strategy": st, "json": jpath, "log": log}
        if not running:
            break
        time.sleep(0.5)
        # monitor
        for key in list(running):
            r = running[key]
            rss = _tree_rss(r["ps"])
            r["peak_now"] = rss
            r["peak"] = max(r["peak"], rss)
            if r["proc"].poll() is not None:
                r["log"].close()
                if r["json"].exists():
                    finish(key, json.loads(r["json"].read_text()))
                else:
                    finish(key, {"status": "worker_crash", "returncode": r["proc"].returncode})
            elif rss > cap:
                kill(key, "memout_cap")
            elif time.time() - r["start"] > a.time_limit + a.grace_s:
                kill(key, "harness_timeout")
        tot = sum(r["peak_now"] for r in running.values())
        if tot > budget and len(running) > 1:
            key = max(running, key=lambda k: running[k]["start"])  # youngest
            if not kill(key, "budget", requeue=True):
                print(f"requeued {key} (total rss {tot / GIB:.1f} GiB)", flush=True)
    left = len(queue)
    print(f"solve {a.time_limit}s: {n_done} jobs finished this session, {left} not started", flush=True)
    return 0


# -------------------------------------------------------------------------- val
def _val_one(args):
    checker, kbin, key, rec, domain, problem = args
    if checker == "kcl":
        return key, rec, kval.check_plan(kbin, domain, problem, rec["plan_file"])
    from tools.d5b.fd_worker import pyval_plan
    return key, rec, pyval_plan(domain, problem, rec["plan_file"])


def cmd_val(a) -> int:
    """Add a VAL verdict to every plan of a pass that lacks one: `--checker kcl`
    (KCL VAL, normally done inline; this finishes checks that were cut off) or
    `--checker pyval` (pddl-pyvalidator 0.1.6, the harness grader; no time
    limit, it is slow on long plans). Appends one updated record per plan; the
    last record of a key wins when the file is read, so this is resumable."""
    from concurrent.futures import ProcessPoolExecutor, as_completed

    clone, work = a.clone.resolve(), a.work.resolve()
    kbin = _kcl_bin(a) if a.checker == "kcl" else None
    field = "kval_valid" if a.checker == "kcl" else "pyval_valid"
    out = runs_file(work, a.time_limit)
    todo = [(a.checker, kbin, k, r, str(clone / r["domain"] / "domain.pddl"), str(work / r["problem"]))
            for k, r in _load_final(out).items()
            if r.get("status") == "solved" and not isinstance(r.get(field), bool)]
    todo.sort(key=lambda t: t[3].get("plan_len") or 0)  # short plans first
    print(f"val {a.time_limit}s --checker {a.checker}: {len(todo)} plans without a verdict", flush=True)
    deadline = time.time() + a.max_hours * 3600 if a.max_hours else None
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(_val_one, t) for t in todo]
        for fut in as_completed(futs):
            key, rec, v = fut.result()
            rec = dict(rec, **v)
            rec[f"{a.checker}_added_later"] = True
            with open(out, "a") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
            print(f"{key}: {field}={rec[field]} ({rec.get(field.replace('_valid', '_time'))}s, "
                  f"{rec.get('plan_len')} steps)", flush=True)
            if deadline and time.time() > deadline:
                print("max hours reached: cancelling the checks not started", flush=True)
                for f_ in futs:
                    f_.cancel()
                break
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5b ground truth pipeline")
    ap.add_argument("--clone", type=Path, default=REPO / "external" / "ipc2023-learning")
    ap.add_argument("--work", type=Path, default=REPO / "external" / "d5b-work")
    ap.add_argument("--kcl-val", type=Path, default=kval.DEFAULT_BIN, help="KCL VAL `validate` binary")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate")
    sub.add_parser("repro-ipc")
    sub.add_parser("validate")
    s = sub.add_parser("solve")
    s.add_argument("--time-limit", type=int, required=True)
    s.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    s.add_argument("--mem-cap-gib", type=float, default=8.0)
    s.add_argument("--mem-budget-gib", type=float, default=14.0)
    s.add_argument("--grace-s", type=int, default=1800,
                   help="extra wall time for parse + VAL before the job is killed (VAL then finishes in `val`)")
    s.add_argument("--max-hours", type=float, default=None,
                   help="stop starting new jobs after this many hours (running jobs finish)")
    s.add_argument("--order", choices=("listed", "small-first"), default="listed")
    s.add_argument("--limit-jobs", type=int, default=0, help="debug: run only the first N jobs")
    v = sub.add_parser("val")
    v.add_argument("--time-limit", type=int, required=True)
    v.add_argument("--checker", choices=("kcl", "pyval"), required=True)
    v.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    v.add_argument("--max-hours", type=float, default=None)
    a = ap.parse_args(argv)
    return {"val": cmd_val, "generate": cmd_generate, "repro-ipc": cmd_repro_ipc, "validate": cmd_validate, "solve": cmd_solve}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
