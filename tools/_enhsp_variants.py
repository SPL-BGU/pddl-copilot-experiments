#!/usr/bin/env python3
"""Run ENHSP under several search settings on one (domain, problem) pair.

Helper for `tools/build_hard_fixtures.py` (action plan D1b). The MCP tool
`numeric_planner` exposes no search option, so to look for genuinely
different numeric plans this script calls ENHSP the same way the
pddl-solver plugin does (unified-planning `PDDLReader` -> `OneshotPlanner(
name="enhsp")`), only with a different ENHSP parameter string each time.
Plans are formatted exactly as the plugin's `_extract_plan` formats them
(lowercase, one `(name args)` per action).

It must run under the pddl-solver plugin's own Python (the one with
`unified-planning` and `up-enhsp` installed), for example:

    ../pddl-copilot/plugins/pddl-solver/.venv/bin/python \\
        tools/_enhsp_variants.py --domain D.pddl --problem P.pddl \\
        --config "-h hadd -s gbfs" --config "-h hradd -s gbfs" --timeout 60

Output: one JSON object on stdout, {config: {"plan": [...]} |
{"error": str} | {"unsolvable": true}}. Read-only; writes only temp files
(unified-planning's own).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import warnings


def _java_ok(java: str) -> bool:
    try:
        p = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=30)
    except Exception:
        return False
    return p.returncode == 0 and "Unable to locate a Java Runtime" not in (p.stdout + p.stderr)


def _ensure_java(java_home: str | None) -> str:
    """Put a working `java` first on PATH; mirrors the plugin's discovery
    order (an explicit JAVA_HOME, `java_home -v 17+`, Homebrew keg-only
    openjdk, /usr/lib/jvm). Returns the java binary used."""
    cands: list[str] = []
    if java_home:
        cands.append(os.path.join(java_home, "bin"))
    if shutil.which("java") and _java_ok(shutil.which("java")):
        return shutil.which("java")
    if os.path.exists("/usr/libexec/java_home"):
        p = subprocess.run(["/usr/libexec/java_home", "-v", "17+"], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            cands.append(os.path.join(p.stdout.strip(), "bin"))
    cands += sorted(glob.glob("/opt/homebrew/opt/openjdk*/bin"))
    cands += sorted(glob.glob("/usr/local/opt/openjdk*/bin"))
    cands += sorted(glob.glob("/usr/lib/jvm/*/bin"))
    for c in cands:
        j = os.path.join(c, "java")
        if os.path.exists(j) and _java_ok(j):
            os.environ["PATH"] = c + os.pathsep + os.environ.get("PATH", "")
            os.environ["JAVA_HOME"] = os.path.dirname(c)
            return j
    raise SystemExit("no working Java runtime found (ENHSP needs OpenJDK 17+)")


def _extract_plan(result) -> list[str]:
    # Same formatting as pddl-solver/server/solver_server.py `_extract_plan`.
    if result.plan is None:
        return []
    actions = []
    for ai in result.plan.actions:
        name = ai.action.name
        params = " ".join(str(p) for p in ai.actual_parameters)
        action_str = f"({name} {params})" if params else f"({name})"
        actions.append(action_str.lower())
    return actions


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--config", action="append", required=True,
                    help="ENHSP parameter string, e.g. '-h hadd -s gbfs' (repeatable)")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--java-home", default=None)
    args = ap.parse_args()

    warnings.filterwarnings("ignore")
    _ensure_java(args.java_home)
    from unified_planning.io import PDDLReader
    from unified_planning.shortcuts import OneshotPlanner, get_environment
    import unified_planning.engines.results as up_results

    get_environment().credits_stream = None
    out: dict[str, dict] = {}
    for cfg in args.config:
        try:
            problem = PDDLReader().parse_problem(args.domain, args.problem)
            with OneshotPlanner(name="enhsp", params={"params": cfg}) as planner:
                res = planner.solve(problem, timeout=args.timeout)
            if res.status in up_results.POSITIVE_OUTCOMES:
                out[cfg] = {"plan": _extract_plan(res)}
            elif res.status in (up_results.PlanGenerationResultStatus.UNSOLVABLE_PROVEN,
                                up_results.PlanGenerationResultStatus.UNSOLVABLE_INCOMPLETELY):
                out[cfg] = {"unsolvable": True}
            else:
                out[cfg] = {"error": str(res.status)}
        except Exception as exc:  # one bad setting must not lose the others
            out[cfg] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
