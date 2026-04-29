"""PDDL domain/problem fixture loading + ground-truth oracle generation.

`load_domains` walks `domains/{classical,numeric}/<name>/` to assemble the
positive corpus + negative fixtures from the PR-3 flat layout
(`domain_neg.pddl`, `n<NN>.pddl`, `p<NN>_v[1-5].plan`, `p<NN>_b[1-5].plan`).

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
        domain_neg.pddl              - 1 invalid domain
        p<NN>.pddl ... × up to 5     - valid problems
        n<NN>.pddl ... × up to 5     - invalid problems
        p<NN>_v[1-9].plan × up to 5  - valid plans per problem
        p<NN>_b[1-9].plan × up to 5  - invalid plans per problem

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

            problems = {
                pf.stem: pf.read_text()
                for pf in sorted(ddir.glob("p[0-9]*.pddl"))
                if not pf.stem.endswith("_0")
            }
            if not problems:
                continue

            neg_domain_file = ddir / "domain_neg.pddl"
            neg_domain = neg_domain_file.read_text() if neg_domain_file.exists() else None

            neg_problem_files = sorted(ddir.glob("n[0-9]*.pddl"))
            neg_problems = [f.read_text() for f in neg_problem_files]

            plans_per_problem: dict = {}
            for pname in problems:
                valid_plan_files = sorted(ddir.glob(f"{pname}_v[0-9]*.plan"))
                valid_plans = [f.read_text() for f in valid_plan_files]

                invalid_plan_files = sorted(ddir.glob(f"{pname}_b[0-9]*.plan"))
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


async def _validate_capture(
    mcp: MCPPlanner, args: dict,
) -> tuple[str, bool | None]:
    """Call `validate_pddl_syntax(args)` and capture (raw, parsed_verdict).

    On MCP exception, returns `(str(exc), None)` so the caller can stash
    both in a single tuple assignment without an explicit try-block.
    Mirrors the per-layer (domain / problem / plan) ground-truth probes
    in `generate_ground_truth`.
    """
    try:
        raw = await mcp.call_tool("validate_pddl_syntax", args)
    except Exception as exc:
        return str(exc), None
    return raw, _parse_validation_verdict(raw)


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

            entry["domain_validation_raw"], entry["domain_valid"] = await _validate_capture(
                mcp, {"domain": dinfo["domain"]}
            )
            entry["problem_validation_raw"], entry["problem_valid"] = await _validate_capture(
                mcp, {"domain": dinfo["domain"], "problem": ppddl}
            )

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
                entry["plan_validation_raw"], entry["plan_valid"] = await _validate_capture(
                    mcp, {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str}
                )

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
                raw, plan_valid = await _validate_capture(
                    mcp, {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_text}
                )
                if plan_valid is not True:
                    raise SystemExit(
                        f"Valid-plan fixture {dname}/{pname}_v{i+1}.plan validated as "
                        f"valid={plan_valid!r} (expected True) — fix the fixture or the "
                        f"validator. Raw: {raw}"
                    )
                entry["valid_plans"].append({"plan": plan_text, "plan_valid": True})

            gt[dname][pname] = entry
            tag = "solvable" if entry["solvable"] else "unsolvable"
            print(
                f"    {dname}/{pname}: {tag} "
                f"(domain_valid={entry['domain_valid']} "
                f"problem_valid={entry['problem_valid']} "
                f"plan_valid={entry['plan_valid']} "
                f"valid_plans={len(entry['valid_plans'])})"
            )
            # Solvable cell with 0 committed valid plans → the runner's
            # validate_plan positive arm silently emits 0 jobs for this
            # (dname, pname). Surface it at startup so a missing
            # `gen-valid-plans` step on a future domain addition can't
            # slip past unnoticed.
            if entry["solvable"] and not entry["valid_plans"]:
                print(
                    f"    [WARN] {dname}/{pname}: 0 committed valid plans — "
                    "validate_plan positive arm will emit 0 jobs for this cell. "
                    "Run `tools/build_fixtures.py gen-valid-plans` to populate."
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
                raw, verdict = await _validate_capture(
                    mcp, {"domain": negs["domain"]}
                )
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/domain_neg.pddl validated as "
                        f"valid={verdict!r} (expected False) — fix the fixture or "
                        f"the validator before running the sweep. Raw: {raw}"
                    )
                neg_slot["domain"] = {
                    "domain_pddl": negs["domain"],
                    "domain_valid": False,
                }
                print(f"    {dname}/domain_neg.pddl: negative ✓ (domain_valid=False)")

            neg_problems_list: list[dict] = []
            for i, prob_text in enumerate(negs.get("problems") or []):
                raw, verdict = await _validate_capture(
                    mcp,
                    {"domain": dinfo["domain"], "problem": prob_text},
                )
                if verdict is not False:
                    raise SystemExit(
                        f"Negative fixture {dname}/n{i+1:02d}.pddl validated as "
                        f"valid={verdict!r} (expected False). Raw: {raw}"
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
                    raw, verdict = await _validate_capture(
                        mcp,
                        {
                            "domain": dinfo["domain"],
                            "problem": positive_pddl,
                            "plan": plan_text,
                        },
                    )
                    if verdict is not False:
                        raise SystemExit(
                            f"Negative fixture {dname}/{pname}_b{i+1}.plan validated as "
                            f"valid={verdict!r} (expected False). Raw: {raw}"
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
