"""PDDL domain/problem fixture loading + ground-truth oracle generation.

`load_domains` walks `domains/{classical,numeric}/<name>/` to assemble the
positive corpus + task-targeted negative fixtures (ISS-001).

`generate_ground_truth` runs the MCP validator + planner over every fixture
to build the per-domain oracle that `runner.evaluate_one` compares against.
"""

from pathlib import Path

from .chat import MCPPlanner, _parse_validation_verdict, _safe_json_loads


def load_domains(domains_dir: Path) -> dict:
    """
    Load PDDL domains from:
        domains/{classical,numeric}/<name>/domain.pddl
        domains/{classical,numeric}/<name>/p*.pddl

    Optionally also picks up task-targeted negative fixtures with the `_0`
    suffix (validity-neutral filenames; see `domains/README.md` and ISS-001):
        domain_0.pddl  → validate_domain only
        p01_0.pddl     → validate_problem only
        p01_0.plan     → validate_plan only

    Returns {name: {"type": str, "domain": str, "problems": {pname: str},
                    "negatives": {"domain": str|None, "problem": str|None,
                                  "plan": str|None}}}.
    """
    domains: dict = {}
    for dtype in ("classical", "numeric"):
        type_dir = domains_dir / dtype
        if not type_dir.is_dir():
            continue
        for ddir in sorted(type_dir.iterdir()):
            if not ddir.is_dir():
                continue
            domain_file = ddir / "domain.pddl"
            if not domain_file.exists():
                continue
            # Exclude `_0`-suffixed problem files: they are negative fixtures
            # consumed via `negatives["problem"]`, not real positive problems.
            problems = {
                pf.stem: pf.read_text()
                for pf in sorted(ddir.glob("p*.pddl"))
                if not pf.stem.endswith("_0")
            }
            if problems:
                neg_domain = ddir / "domain_0.pddl"
                neg_problem = ddir / "p01_0.pddl"
                neg_plan = ddir / "p01_0.plan"
                domains[ddir.name] = {
                    "type": dtype,
                    "domain": domain_file.read_text(),
                    "problems": problems,
                    "negatives": {
                        "domain": neg_domain.read_text() if neg_domain.exists() else None,
                        "problem": neg_problem.read_text() if neg_problem.exists() else None,
                        "plan": neg_plan.read_text() if neg_plan.exists() else None,
                    },
                }
    return domains


def _build_plan_str(gt: dict) -> str:
    """Stringify a ground-truth plan for prompt/tool inputs.

    Returns "" when no plan is recorded; otherwise newline-joins list plans
    or passes through pre-stringified plans. Keeps the validate_plan and
    simulate prompt-builders consistent with the oracle's format.
    """
    plan = gt.get("plan")
    if not plan:
        return ""
    if isinstance(plan, list):
        return "\n".join(plan)
    return plan


async def generate_ground_truth(mcp: MCPPlanner, domains: dict) -> dict:
    """For each domain/problem, solve and validate using the MCP tools as oracle."""
    gt: dict = {}
    for dname, dinfo in domains.items():
        gt[dname] = {}
        planner = "classic_planner" if dinfo["type"] == "classical" else "numeric_planner"
        for pname, ppddl in dinfo["problems"].items():
            entry: dict = {
                "domain_valid": None,
                "problem_valid": None,
                "plan_valid": None,
                "solvable": False,
                "plan": None,
                "trace": None,
            }

            # Validate domain via pyvalidator
            try:
                raw = await mcp.call_tool("validate_pddl_syntax", {"domain": dinfo["domain"]})
                entry["domain_validation_raw"] = raw
                entry["domain_valid"] = _parse_validation_verdict(raw)
            except Exception as exc:
                entry["domain_validation_raw"] = str(exc)

            # Validate problem via pyvalidator
            try:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax",
                    {"domain": dinfo["domain"], "problem": ppddl},
                )
                entry["problem_validation_raw"] = raw
                entry["problem_valid"] = _parse_validation_verdict(raw)
            except Exception as exc:
                entry["problem_validation_raw"] = str(exc)

            # Solve — distinguish solvable (non-empty plan) from unsolvable (empty plan)
            try:
                raw = await mcp.call_tool(planner, {"domain": dinfo["domain"], "problem": ppddl})
                data = _safe_json_loads(raw)
                if isinstance(data, dict) and isinstance(data.get("plan"), list) and data["plan"]:
                    entry["plan"] = data["plan"]
                    entry["solvable"] = True
            except Exception:
                pass

            # State trace + plan-validity verdict (only if we have a plan)
            if entry["plan"]:
                plan_str = _build_plan_str(entry)
                try:
                    entry["trace"] = await mcp.call_tool(
                        "get_state_transition",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str},
                    )
                except Exception:
                    pass
                # Validate the oracle plan so validate_plan has a verdict
                try:
                    raw = await mcp.call_tool(
                        "validate_pddl_syntax",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str},
                    )
                    entry["plan_validation_raw"] = raw
                    entry["plan_valid"] = _parse_validation_verdict(raw)
                except Exception as exc:
                    entry["plan_validation_raw"] = str(exc)

            gt[dname][pname] = entry
            tag = "solvable" if entry["solvable"] else "unsolvable"
            print(
                f"    {dname}/{pname}: {tag} "
                f"(domain_valid={entry['domain_valid']} "
                f"problem_valid={entry['problem_valid']} "
                f"plan_valid={entry['plan_valid']})"
            )

        # Task-targeted negative fixtures (ISS-001). The `_negatives` slot is
        # keyed on the negative *kind*, not a `pname`, to avoid colliding
        # with the per-problem map above. The job builder reads from here
        # and constructs each negative job's `gt` fragment inline.
        negs = dinfo.get("negatives") or {}
        positive_problems = dinfo["problems"]
        if positive_problems and any(v is not None for v in negs.values()):
            # Pairing: validate_problem and validate_plan negatives need a
            # *positive* domain/problem to attach to. The paper dataset
            # ships a single positive per domain, so we just take the first
            # one. Generalise to multi-problem datasets by carrying a
            # designated "primary" problem in `dinfo`.
            positive_p01 = next(iter(positive_problems.values()))
            neg_slot: dict = {}

            if negs.get("domain") is not None:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax", {"domain": negs["domain"]}
                )
                verdict = _parse_validation_verdict(raw)
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/domain_0.pddl validated as "
                        f"{verdict!r} (expected False) — fix the fixture or "
                        f"the validator before running the sweep."
                    )
                neg_slot["domain"] = {
                    "domain_pddl": negs["domain"],
                    "domain_valid": False,
                }
                print(f"    {dname}/domain_0.pddl: negative ✓ (domain_valid=False)")

            if negs.get("problem") is not None:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax",
                    {"domain": dinfo["domain"], "problem": negs["problem"]},
                )
                verdict = _parse_validation_verdict(raw)
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/p01_0.pddl validated as "
                        f"{verdict!r} (expected False)."
                    )
                neg_slot["problem"] = {
                    "problem_pddl": negs["problem"],
                    "problem_valid": False,
                }
                print(f"    {dname}/p01_0.pddl: negative ✓ (problem_valid=False)")

            if negs.get("plan") is not None:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax",
                    {
                        "domain": dinfo["domain"],
                        "problem": positive_p01,
                        "plan": negs["plan"],
                    },
                )
                verdict = _parse_validation_verdict(raw)
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/p01_0.plan validated as "
                        f"{verdict!r} (expected False)."
                    )
                neg_slot["plan"] = {
                    "plan": negs["plan"],   # picked up by _build_plan_str
                    "plan_valid": False,
                }
                print(f"    {dname}/p01_0.plan: negative ✓ (plan_valid=False)")

            if neg_slot:
                gt[dname]["_negatives"] = neg_slot
    return gt
