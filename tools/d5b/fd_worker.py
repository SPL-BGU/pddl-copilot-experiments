"""One D5b planner run: Fast Downward through unified-planning, then VAL.

Runs in its own process (started by tools.d5b.pipeline), so the parent can
watch its memory and kill it. Needs the D5b scratch venv
(tools/d5b/requirements.txt), not the repo venv.

The planner call copies the pddl-solver plugin's `_solve` and
`classic_planner` (../pddl-copilot/plugins/pddl-solver/server/solver_server.py,
read only, never imported): PDDLReader().parse_problem on the two files, then
OneshotPlanner(name="fast-downward",
params={"fast_downward_search_config": FD_STRATEGIES[strategy]}) and
planner.solve(problem, timeout=T) with the working directory pinned to a fresh
temp folder. The timeout covers the Fast Downward subprocess (translate plus
search), as in the plugin; parsing is outside it. The plan is extracted the way
the plugin does it (lowercase "(name arg ...)"), written one action per line,
and checked with pddl-pyvalidator (PDDLValidator().validate, as the
pddl-validator plugin does) against the original IPC domain and problem files.
VAL time is not part of the planner time.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import time

# Same dict as the pddl-solver plugin (tests/test_d5b.py checks it against the
# sibling file when that file is present).
FD_STRATEGIES = {
    "lazy_greedy_cea": "let(hcea,cea(),lazy_greedy([hcea],preferred=[hcea]))",
    "astar_lmcut": "astar(lmcut())",
    "lazy_greedy_ff": "let(hff,ff(),lazy_greedy([hff],preferred=[hff]))",
}


def _extract_plan(result) -> list[str]:
    if result.plan is None:
        return []
    actions = []
    for ai in result.plan.actions:
        name = ai.action.name
        params = " ".join(str(p) for p in ai.actual_parameters)
        actions.append((f"({name} {params})" if params else f"({name})").lower())
    return actions


def validate_plan(domain: str, problem: str, plan_file: str) -> dict:
    """pddl-pyvalidator verdict on one plan file (no time limit)."""
    from pyval import PDDLValidator
    t = time.time()
    try:
        v = PDDLValidator().validate(domain, problem, plan_file)
        out = {"val_valid": bool(v.is_valid), "val_status": str(v.status)}
    except Exception as e:  # noqa: BLE001
        out = {"val_valid": False, "val_status": "VAL_ERROR", "val_message": str(e)[-2000:]}
    out["val_time"] = round(time.time() - t, 3)
    return out


def write_json(path: str, rec: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f)
    os.replace(tmp, path)


def run(domain: str, problem: str, strategy: str, timeout: int, plan_out: str,
        checkpoint=lambda rec: None) -> dict:
    from unified_planning.io import PDDLReader
    from unified_planning.shortcuts import OneshotPlanner, get_environment
    import unified_planning.engines.results as up_results

    get_environment().credits_stream = None
    rec: dict = {"strategy": strategy, "time_limit": timeout}
    rd = tempfile.mkdtemp(prefix="d5b_")
    prev = os.getcwd()
    try:
        t0 = time.time()
        try:
            up_problem = PDDLReader().parse_problem(domain, problem)
        except Exception as e:  # noqa: BLE001
            rec.update(status="parse_error", message=str(e)[-2000:])
            return rec
        rec["parse_time"] = round(time.time() - t0, 3)
        t1 = time.time()
        try:
            os.chdir(rd)
            with OneshotPlanner(name="fast-downward",
                                params={"fast_downward_search_config": FD_STRATEGIES[strategy]}) as planner:
                result = planner.solve(up_problem, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            rec.update(status="planner_error", message=str(e)[-2000:])
            return rec
        finally:
            os.chdir(prev)
        rec["solve_time"] = round(time.time() - t1, 3)
        try:
            rec["engine_internal_time"] = float(result.metrics.get("engine_internal_time"))
        except (TypeError, ValueError, AttributeError):
            pass
        st = result.status
        rec["up_status"] = st.name
        # Fast Downward's own search statistics, from the captured stdout.
        info = result.log_messages[0].message if result.log_messages else ""
        for pat, name, conv in ((r"Expanded (\d+) state", "fd_expanded", int),
                                (r"Search time: ([0-9.]+)s", "fd_search_time", float)):
            m = re.findall(pat, info)
            if m:
                rec[name] = conv(m[-1])
        if st in up_results.POSITIVE_OUTCOMES:
            plan = _extract_plan(result)
            os.makedirs(os.path.dirname(plan_out), exist_ok=True)
            with open(plan_out, "w") as f:
                f.write("".join(a + "\n" for a in plan))
            rec.update(status="solved", plan_len=len(plan), plan_file=plan_out,
                       val_valid=None, val_status="PENDING")
            # Planner result first: if VAL is then killed (memory or wall
            # guard), the parent still records the plan, and
            # `pipeline val` finishes the check later.
            checkpoint(rec)
            rec.update(validate_plan(domain, problem, plan_out))
        elif st in (up_results.PlanGenerationResultStatus.UNSOLVABLE_PROVEN,
                    up_results.PlanGenerationResultStatus.UNSOLVABLE_INCOMPLETELY):
            rec["status"] = "unsolvable"
        elif st == up_results.PlanGenerationResultStatus.TIMEOUT:
            rec["status"] = "timeout"
        elif st == up_results.PlanGenerationResultStatus.MEMOUT:
            rec["status"] = "memout"
        else:
            log = str(result.log_messages) if result.log_messages else ""
            rec.update(status="planner_failed", message=log[-2000:])
        return rec
    finally:
        shutil.rmtree(rd, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--strategy", required=True, choices=sorted(FD_STRATEGIES))
    ap.add_argument("--timeout", type=int, required=True)
    ap.add_argument("--plan-out", required=True)
    ap.add_argument("--json-out", required=True)
    a = ap.parse_args(argv)
    rec = run(a.domain, a.problem, a.strategy, a.timeout, a.plan_out,
              checkpoint=lambda r: write_json(a.json_out, r))
    write_json(a.json_out, rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
