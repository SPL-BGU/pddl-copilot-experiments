"""PDDL domain/problem fixture loading + ground-truth oracle generation.

`load_domains` walks `domains/{classical,numeric}/<name>/` to assemble the
positive corpus + negative fixtures. Supports both the PR-3 flat layout
(`domain_neg.pddl`, `n<NN>.pddl`, `p<NN>_v[1-5].plan`, `p<NN>_b[1-5].plan`)
and the legacy `_0`-suffix layout for backward-compat during migration.

`generate_ground_truth` runs the MCP validator + planner over every
fixture to build the per-domain oracle that `runner.evaluate_one`
compares against.
"""

from pathlib import Path

from .chat import MCPPlanner, _parse_validation_verdict, _safe_json_loads


def load_domains(domains_dir: Path) -> dict:
    """
    Load PDDL fixtures from the flat-file layout under
    `domains/{classical,numeric}/<name>/`:

        domain.pddl                  - 1 valid domain
        domain_neg.pddl              - 1 invalid domain (legacy: domain_0.pddl)
        p<NN>.pddl ... × up to 5     - valid problems
        n<NN>.pddl ... × up to 5     - invalid problems (legacy: p<NN>_0.pddl)
        p<NN>_v[1-9].plan × up to 5  - valid plans per problem
                                       (legacy: p<NN>.plan as v1)
        p<NN>_b[1-9].plan × up to 5  - invalid plans per problem
                                       (legacy: p<NN>_0.plan as b1)

    Backward-compat: when the new flat-layout files are absent, fall back
    to the legacy single-fixture-per-slot layout. The compat branch is
    dropped after Commit B of PR-3 (FRAMEWORK_EXTENSION_PLAN.md §3.3).

    Returns:
        {name: {
            "type": str,
            "domain": str,
            "problems": dict[str, str],
            "negatives": {
                "domain": str | None,
                "problems": list[str],
                "plans_per_problem": dict[
                    str,
                    {"valid": list[str], "invalid": list[str]},
                ],
            },
        }}
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

            # Valid problems: prefer p<NN>.pddl glob (excludes n<NN>.pddl
            # and the legacy `p<NN>_0.pddl` negatives). The legacy layout
            # could include `p01_0.pddl` matching `p*.pddl`, so the
            # `_0` filter is load-bearing during migration.
            problems = {
                pf.stem: pf.read_text()
                for pf in sorted(ddir.glob("p[0-9]*.pddl"))
                if not pf.stem.endswith("_0")
            }
            if not problems:
                continue

            # Invalid domain: prefer domain_neg.pddl, fall back to domain_0.pddl
            neg_domain_file = ddir / "domain_neg.pddl"
            if not neg_domain_file.exists():
                neg_domain_file = ddir / "domain_0.pddl"
            neg_domain = neg_domain_file.read_text() if neg_domain_file.exists() else None

            # Invalid problems: prefer n<NN>.pddl glob, fall back to
            # p<NN>_0.pddl (legacy single-fixture form).
            neg_problem_files = sorted(ddir.glob("n[0-9]*.pddl"))
            if not neg_problem_files:
                neg_problem_files = sorted(ddir.glob("p[0-9]*_0.pddl"))
            neg_problems = [f.read_text() for f in neg_problem_files]

            # Plans per problem. Valid: prefer p<NN>_v[1-9].plan, fall
            # back to p<NN>.plan as a single v1. Invalid: prefer
            # p<NN>_b[1-9].plan, fall back to p<NN>_0.plan as a single b1.
            plans_per_problem: dict = {}
            for pname in problems:
                valid_plan_files = sorted(ddir.glob(f"{pname}_v[0-9]*.plan"))
                if not valid_plan_files:
                    legacy_plan = ddir / f"{pname}.plan"
                    valid_plan_files = [legacy_plan] if legacy_plan.exists() else []
                valid_plans = [f.read_text() for f in valid_plan_files]

                invalid_plan_files = sorted(ddir.glob(f"{pname}_b[0-9]*.plan"))
                if not invalid_plan_files:
                    legacy_neg_plan = ddir / f"{pname}_0.plan"
                    invalid_plan_files = (
                        [legacy_neg_plan] if legacy_neg_plan.exists() else []
                    )
                invalid_plans = [f.read_text() for f in invalid_plan_files]

                if valid_plans or invalid_plans:
                    plans_per_problem[pname] = {
                        "valid": valid_plans,
                        "invalid": invalid_plans,
                    }

            domains[ddir.name] = {
                "type": dtype,
                "domain": domain_file.read_text(),
                "problems": problems,
                "negatives": {
                    "domain": neg_domain,
                    "problems": neg_problems,
                    "plans_per_problem": plans_per_problem,
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
    """For each domain/problem, solve and validate via MCP tools as oracle.

    PR-3 ground-truth shape per problem:
        gt[dname][pname] = {
            "domain_valid": bool,
            "problem_valid": bool,
            "plan_valid": bool,        # validation of the planner's plan
            "solvable": bool,
            "plan": list[str] | str,   # canonical plan; used by simulate
            "trace": dict | None,      # state trajectory of the canonical plan
            "valid_plans": list[dict], # [{"plan": str, "plan_valid": bool}, ...]
        }

    Per-domain `_negatives` shape:
        gt[dname]["_negatives"] = {
            "domain":  {"domain_pddl": str, "domain_valid": False},
            "problems": [{"problem_pddl": str, "problem_valid": False}, ...],
            "plans_per_problem": {pname: [{"plan": str, "plan_valid": False}, ...]},
        }

    Aborts startup with SystemExit if any negative validates as True or
    any committed valid_plan validates as False.
    """
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
                "valid_plans": [],
            }

            try:
                raw = await mcp.call_tool("validate_pddl_syntax", {"domain": dinfo["domain"]})
                entry["domain_validation_raw"] = raw
                entry["domain_valid"] = _parse_validation_verdict(raw)
            except Exception as exc:
                entry["domain_validation_raw"] = str(exc)

            try:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax",
                    {"domain": dinfo["domain"], "problem": ppddl},
                )
                entry["problem_validation_raw"] = raw
                entry["problem_valid"] = _parse_validation_verdict(raw)
            except Exception as exc:
                entry["problem_validation_raw"] = str(exc)

            try:
                raw = await mcp.call_tool(planner, {"domain": dinfo["domain"], "problem": ppddl})
                data = _safe_json_loads(raw)
                if isinstance(data, dict) and isinstance(data.get("plan"), list) and data["plan"]:
                    entry["plan"] = data["plan"]
                    entry["solvable"] = True
            except Exception:
                pass

            if entry["plan"]:
                plan_str = _build_plan_str(entry)
                try:
                    entry["trace"] = await mcp.call_tool(
                        "get_state_transition",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str},
                    )
                except Exception:
                    pass
                try:
                    raw = await mcp.call_tool(
                        "validate_pddl_syntax",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str},
                    )
                    entry["plan_validation_raw"] = raw
                    entry["plan_valid"] = _parse_validation_verdict(raw)
                except Exception as exc:
                    entry["plan_validation_raw"] = str(exc)

            # Validate each committed valid plan. The committed `_v[1-9]`
            # plans are independent of the planner's canonical plan above;
            # they are graded separately against `validate_pddl_syntax`.
            committed_valid_plans = (
                dinfo.get("negatives", {})
                .get("plans_per_problem", {})
                .get(pname, {})
                .get("valid", [])
            )
            for i, plan_text in enumerate(committed_valid_plans):
                try:
                    raw = await mcp.call_tool(
                        "validate_pddl_syntax",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_text},
                    )
                    plan_valid = _parse_validation_verdict(raw)
                except Exception:
                    plan_valid = None
                if plan_valid is False:
                    raise SystemExit(
                        f"Valid-plan fixture {dname}/{pname}_v{i+1}.plan validated as "
                        f"valid=False (expected True) — fix the fixture or the validator."
                    )
                entry["valid_plans"].append({"plan": plan_text, "plan_valid": bool(plan_valid)})

            gt[dname][pname] = entry
            tag = "solvable" if entry["solvable"] else "unsolvable"
            print(
                f"    {dname}/{pname}: {tag} "
                f"(domain_valid={entry['domain_valid']} "
                f"problem_valid={entry['problem_valid']} "
                f"plan_valid={entry['plan_valid']} "
                f"valid_plans={len(entry['valid_plans'])})"
            )

        # ---------------- Negative fixtures ----------------
        # The `_negatives` slot is keyed on the negative *kind*. The
        # job builder reads from here and constructs each negative
        # job's gt fragment inline.
        negs = dinfo.get("negatives") or {}
        positive_problems = dinfo["problems"]
        any_neg = (
            negs.get("domain") is not None
            or bool(negs.get("problems"))
            or any(
                bool(v.get("invalid"))
                for v in (negs.get("plans_per_problem") or {}).values()
            )
        )
        if positive_problems and any_neg:
            neg_slot: dict = {}

            if negs.get("domain") is not None:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax", {"domain": negs["domain"]}
                )
                verdict = _parse_validation_verdict(raw)
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/domain_neg.pddl validated as "
                        f"valid={verdict!r} (expected False) — fix the fixture or "
                        f"the validator before running the sweep."
                    )
                neg_slot["domain"] = {
                    "domain_pddl": negs["domain"],
                    "domain_valid": False,
                }
                print(f"    {dname}/domain_neg.pddl: negative ✓ (domain_valid=False)")

            neg_problems_list: list[dict] = []
            for i, prob_text in enumerate(negs.get("problems") or []):
                raw = await mcp.call_tool(
                    "validate_pddl_syntax",
                    {"domain": dinfo["domain"], "problem": prob_text},
                )
                verdict = _parse_validation_verdict(raw)
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/n{i+1:02d}.pddl validated as "
                        f"valid={verdict!r} (expected False)."
                    )
                neg_problems_list.append({
                    "problem_pddl": prob_text,
                    "problem_valid": False,
                })
                print(f"    {dname}/n{i+1:02d}.pddl: negative ✓ (problem_valid=False)")
            if neg_problems_list:
                neg_slot["problems"] = neg_problems_list

            neg_plans_per_problem: dict = {}
            for pname, pp in (negs.get("plans_per_problem") or {}).items():
                invalid_plans = pp.get("invalid") or []
                pname_neg_list: list[dict] = []
                positive_pddl = dinfo["problems"][pname]
                for i, plan_text in enumerate(invalid_plans):
                    raw = await mcp.call_tool(
                        "validate_pddl_syntax",
                        {
                            "domain": dinfo["domain"],
                            "problem": positive_pddl,
                            "plan": plan_text,
                        },
                    )
                    verdict = _parse_validation_verdict(raw)
                    if verdict is not False:
                        raise SystemExit(
                            f"Negative fixture {dname}/{pname}_b{i+1}.plan validated as "
                            f"valid={verdict!r} (expected False)."
                        )
                    pname_neg_list.append({
                        "plan": plan_text,
                        "plan_valid": False,
                    })
                    print(f"    {dname}/{pname}_b{i+1}.plan: negative ✓ (plan_valid=False)")
                if pname_neg_list:
                    neg_plans_per_problem[pname] = pname_neg_list
            if neg_plans_per_problem:
                neg_slot["plans_per_problem"] = neg_plans_per_problem

            if neg_slot:
                gt[dname]["_negatives"] = neg_slot
    return gt
