"""Fixture generator for PR-3.

Produces the flat-layout per-domain fixture set described in
FRAMEWORK_EXTENSION_PLAN.md §3.3:

    domain.pddl                  - 1 valid domain
    domain_neg.pddl              - 1 invalid domain
    p<NN>.pddl × up to 5         - valid problems
    n<NN>.pddl × up to 5         - invalid problems (5-bug taxonomy)
    p<NN>_v[1-9].plan × up to 5  - valid plans per problem
    p<NN>_b[1-9].plan × up to 5  - invalid plans per problem (5-bug taxonomy)

Subcommands:

    migrate <domain>          rename legacy `_0`-suffix files in-place
                              (domain_0→domain_neg, p01_0.pddl→n01.pddl,
                              p01_0.plan→p01_b1.plan, p01.plan→p01_v1.plan).
                              Idempotent — runs `git mv` only if source exists
                              and destination is absent.

    gen-valid-plans <domain> [--target 5] [--problem PNAME] [--planner-args]
                              Run the planner to produce up to <target>
                              distinct valid plan files per problem. Falls
                              back to v1-duplicates for numeric domains
                              when ENHSP can't produce diversity (per spec
                              §3.3.3 / Decisions log).

    gen-invalid-plans <domain> [--target 5] [--problem PNAME]
                              Mutate an existing valid plan via the 5-bug
                              taxonomy in `tools/_taxonomies.py`. Each
                              candidate is MCP-validated; mutations the
                              validator accepts as valid are discarded
                              and the next mutation seed tried.

    gen-invalid-problems <domain> [--target 5]
                              Mutate p01.pddl via the 5-bug problem
                              taxonomy. Same MCP-rejection retry loop.

    all <domain>              Convenience: migrate + gen-valid-plans +
                              gen-invalid-plans + gen-invalid-problems.

The script is idempotent: existing files are not overwritten unless
`--force` is passed. Always validates output via MCP before writing.

This generator is a one-off for PR-3 and may be regenerated if a domain
is later substituted; that's why it lives in `tools/` (committed) rather
than `.local/` (gitignored).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pddl_eval.chat import (  # noqa: E402
    MCPPlanner,
    _parse_validation_verdict,
    _safe_json_loads,
)
from tools import _taxonomies  # noqa: E402


# ---------------------------------------------------------------------------
# MCP plumbing
# ---------------------------------------------------------------------------


def _resolve_plugin_dirs() -> list[Path]:
    """Mirror run_experiment.resolve_plugin_dirs without importing CLI shim."""
    marketplace = Path(
        os.environ.get(
            "PDDL_MARKETPLACE_PATH",
            str(REPO_ROOT.parent / "pddl-copilot"),
        )
    ).resolve()
    plugins_root = marketplace / "plugins"
    if not plugins_root.is_dir():
        raise SystemExit(
            f"pddl-copilot marketplace not found at {plugins_root!s}. Set "
            "$PDDL_MARKETPLACE_PATH to the marketplace root."
        )
    return [d for d in sorted(plugins_root.iterdir()) if d.is_dir()]


async def _connect_mcp() -> MCPPlanner:
    mcp = MCPPlanner()
    await mcp.connect(_resolve_plugin_dirs())
    return mcp


# ---------------------------------------------------------------------------
# Validation helpers (use MCP as the oracle, never trust mutators directly)
# ---------------------------------------------------------------------------


async def _validate_domain(mcp: MCPPlanner, domain_pddl: str) -> bool | None:
    raw = await mcp.call_tool("validate_pddl_syntax", {"domain": domain_pddl})
    return _parse_validation_verdict(raw)


async def _validate_problem(mcp: MCPPlanner, domain_pddl: str, problem_pddl: str) -> bool | None:
    raw = await mcp.call_tool(
        "validate_pddl_syntax",
        {"domain": domain_pddl, "problem": problem_pddl},
    )
    return _parse_validation_verdict(raw)


async def _validate_plan(
    mcp: MCPPlanner, domain_pddl: str, problem_pddl: str, plan: str,
) -> bool | None:
    raw = await mcp.call_tool(
        "validate_pddl_syntax",
        {"domain": domain_pddl, "problem": problem_pddl, "plan": plan},
    )
    return _parse_validation_verdict(raw)


async def _solve(
    mcp: MCPPlanner, domain_pddl: str, problem_pddl: str, planner: str,
) -> list[str] | None:
    raw = await mcp.call_tool(planner, {"domain": domain_pddl, "problem": problem_pddl})
    data = _safe_json_loads(raw)
    if isinstance(data, dict) and isinstance(data.get("plan"), list) and data["plan"]:
        return data["plan"]
    return None


# ---------------------------------------------------------------------------
# Disk helpers
# ---------------------------------------------------------------------------


def _domain_dir(domain: str) -> Path:
    for dtype in ("classical", "numeric"):
        d = REPO_ROOT / "domains" / dtype / domain
        if d.is_dir():
            return d
    raise SystemExit(f"domain {domain!r} not found under domains/{{classical,numeric}}/")


def _domain_type(domain: str) -> str:
    return "classical" if (REPO_ROOT / "domains" / "classical" / domain).is_dir() else "numeric"


def _git_mv(src: Path, dst: Path, dry_run: bool = False) -> None:
    """`git mv` if src exists and dst is absent. Idempotent."""
    if not src.exists():
        return
    if dst.exists():
        return
    if dry_run:
        print(f"  [dry-run] git mv {src.name} -> {dst.name}")
        return
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "mv", str(src.relative_to(REPO_ROOT)),
         str(dst.relative_to(REPO_ROOT))],
        check=True,
    )
    print(f"  git mv {src.name} -> {dst.name}")


def _write_atomic(path: Path, content: str, force: bool = False, dry_run: bool = False) -> bool:
    """Write `content` to `path`. Skip if file exists and force=False."""
    if path.exists() and not force:
        print(f"  skip (exists): {path.name}")
        return False
    if dry_run:
        print(f"  [dry-run] write {path.name} ({len(content)} bytes)")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)
    print(f"  write {path.name}")
    return True


# ---------------------------------------------------------------------------
# Migrate (legacy `_0` → flat-file naming)
# ---------------------------------------------------------------------------


def cmd_migrate(domain: str, dry_run: bool = False) -> None:
    """Rename legacy `_0`-suffix files to PR-3 flat-file names."""
    ddir = _domain_dir(domain)
    print(f"migrate: {ddir.relative_to(REPO_ROOT)}")
    _git_mv(ddir / "domain_0.pddl", ddir / "domain_neg.pddl", dry_run)
    # `pNN_0.pddl` → `nNN.pddl` for each existing problem.
    for legacy in sorted(ddir.glob("p[0-9]*_0.pddl")):
        n_index = legacy.stem.split("_")[0][1:]  # "p01" → "01"
        new = ddir / f"n{n_index}.pddl"
        _git_mv(legacy, new, dry_run)
    # `pNN.plan` → `pNN_v1.plan` (do NOT rename if `pNN_v*.plan` already exists).
    for legacy in sorted(ddir.glob("p[0-9]*.plan")):
        if "_" in legacy.stem:
            continue
        new = ddir / f"{legacy.stem}_v1.plan"
        if any(ddir.glob(f"{legacy.stem}_v[0-9]*.plan")):
            continue
        _git_mv(legacy, new, dry_run)
    # `pNN_0.plan` → `pNN_b1.plan`.
    for legacy in sorted(ddir.glob("p[0-9]*_0.plan")):
        pname = legacy.stem.split("_")[0]
        new = ddir / f"{pname}_b1.plan"
        _git_mv(legacy, new, dry_run)


# ---------------------------------------------------------------------------
# Generate valid plans (planner with strategy variants)
# ---------------------------------------------------------------------------


# Fast Downward / classic_planner search-strategy hints. The plugin's
# `classic_planner` accepts an optional `search` argument (verified
# against the plugin's MCP tool schema in CHANGELOG 2026-04-20). When the
# argument is unsupported, we fall back to the default invocation.
CLASSICAL_STRATEGIES: tuple[str, ...] = (
    "lazy_greedy_cea",
    "astar_lmcut",
    "lazy_greedy_ff",
)


async def cmd_gen_valid_plans(
    mcp: MCPPlanner,
    domain: str,
    target: int = 5,
    problem: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    ddir = _domain_dir(domain)
    dtype = _domain_type(domain)
    domain_pddl = (ddir / "domain.pddl").read_text()
    planner = "classic_planner" if dtype == "classical" else "numeric_planner"
    problems = sorted(ddir.glob("p[0-9]*.pddl"))
    problems = [p for p in problems if not p.stem.endswith("_0")]
    if problem:
        problems = [p for p in problems if p.stem == problem]
    print(f"gen-valid-plans: {ddir.relative_to(REPO_ROOT)} ({len(problems)} problems)")
    for pfile in problems:
        pname = pfile.stem
        problem_pddl = pfile.read_text()
        existing = sorted(ddir.glob(f"{pname}_v[0-9]*.plan"))
        existing_count = len(existing)
        if existing_count >= target and not force:
            print(f"  {pname}: already {existing_count}/{target} valid plans, skipping")
            continue
        # Strategy 1: default invocation. Always tried — gives the
        # canonical plan that simulate's trace will be built from.
        plans: list[str] = []
        plan = await _solve(mcp, domain_pddl, problem_pddl, planner)
        if plan:
            plans.append("\n".join(plan) + "\n")
        # Strategy 2..N: try classical strategy variants. Numeric
        # planners (ENHSP) have fewer variants — duplicates are
        # accepted per spec §3.3.3.
        if dtype == "classical":
            for strat in CLASSICAL_STRATEGIES:
                if len(plans) >= target:
                    break
                try:
                    raw = await mcp.call_tool(
                        planner,
                        {
                            "domain": domain_pddl,
                            "problem": problem_pddl,
                            "search": strat,
                        },
                    )
                    data = _safe_json_loads(raw)
                    if isinstance(data, dict) and isinstance(data.get("plan"), list):
                        text = "\n".join(data["plan"]) + "\n"
                        if text and text not in plans:
                            plans.append(text)
                except Exception as exc:
                    print(f"    strategy {strat}: error {exc}")
        # Pad to target with duplicates of the canonical plan when the
        # planner can't supply diversity (numeric domains, search-
        # strategy collisions).
        while len(plans) < target and plans:
            plans.append(plans[0])
        # Validate each candidate via MCP before writing. A domain
        # that produces a plan the validator rejects is a fixture
        # bug, not a model bug — abort.
        for i, plan_text in enumerate(plans[:target], start=1):
            if not plan_text:
                continue
            verdict = await _validate_plan(mcp, domain_pddl, problem_pddl, plan_text)
            if verdict is False:
                raise SystemExit(
                    f"  {pname}: planner output (v{i}) failed validation — "
                    "fixture must be reviewed manually."
                )
            out_path = ddir / f"{pname}_v{i}.plan"
            _write_atomic(out_path, plan_text, force=force, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Generate invalid plans (5-bug taxonomy + MCP-rejection retry)
# ---------------------------------------------------------------------------


# Ordered candidate-mutation list per spec §3.3.4. The build script tries
# each in order with multiple seeds; the first 5 distinct mutations the
# validator rejects become b1..b5. Per spec, action names + arity always
# remain valid PDDL syntax; that constraint is honored by all mutators
# in `tools/_taxonomies.py` (no syntactic edits, only semantic edits).
PLAN_MUTATORS = (
    ("truncate-tail",  _taxonomies.plan_truncate),
    ("drop-step-k",    _taxonomies.plan_drop_step_k),
    ("swap-args",      _taxonomies.plan_swap_args),
    ("duplicate-step", _taxonomies.plan_duplicate_step),
)


async def cmd_gen_invalid_plans(
    mcp: MCPPlanner,
    domain: str,
    target: int = 5,
    problem: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    seed: int = 0,
) -> None:
    ddir = _domain_dir(domain)
    domain_pddl = (ddir / "domain.pddl").read_text()
    problems = sorted(ddir.glob("p[0-9]*.pddl"))
    problems = [p for p in problems if not p.stem.endswith("_0")]
    if problem:
        problems = [p for p in problems if p.stem == problem]
    print(f"gen-invalid-plans: {ddir.relative_to(REPO_ROOT)} ({len(problems)} problems)")
    for pfile in problems:
        pname = pfile.stem
        problem_pddl = pfile.read_text()
        # Source plan: prefer p<NN>_v1.plan, fall back to p<NN>.plan
        # (legacy migration pre-step), else solve via planner.
        src_plan = ddir / f"{pname}_v1.plan"
        if not src_plan.exists():
            src_plan = ddir / f"{pname}.plan"
        if src_plan.exists():
            v1_text = src_plan.read_text()
        else:
            print(f"  {pname}: no source plan; run gen-valid-plans first")
            continue
        rng = random.Random(seed + abs(hash(pname)) % 10_000)
        mutated: list[str] = []
        # Try each mutator with up to 4 retries (different seeds) per
        # mutator before falling through. Total candidate budget per
        # problem: ~16 attempts before raising.
        for mut_name, mut_fn in PLAN_MUTATORS:
            for _ in range(4):
                if len(mutated) >= target:
                    break
                candidate = mut_fn(v1_text, rng=rng)
                if not candidate or candidate == v1_text or candidate in mutated:
                    continue
                verdict = await _validate_plan(mcp, domain_pddl, problem_pddl, candidate)
                if verdict is False:
                    mutated.append(candidate)
            if len(mutated) >= target:
                break
        # Pad with extra truncations of varying length when the
        # mutator pool exhausts itself before reaching `target`.
        n_drop = 1
        while len(mutated) < target and n_drop < 10:
            candidate = _taxonomies.plan_truncate(v1_text, n_drop=n_drop)
            n_drop += 1
            if not candidate or candidate == v1_text or candidate in mutated:
                continue
            verdict = await _validate_plan(mcp, domain_pddl, problem_pddl, candidate)
            if verdict is False:
                mutated.append(candidate)
        if len(mutated) < target:
            raise SystemExit(
                f"  {pname}: only generated {len(mutated)}/{target} invalid plans — "
                "domain may need a hand-authored entry. Review fixture taxonomy."
            )
        for i, candidate in enumerate(mutated[:target], start=1):
            out_path = ddir / f"{pname}_b{i}.plan"
            _write_atomic(out_path, candidate, force=force, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Generate invalid problems (5-bug taxonomy + MCP-rejection retry)
# ---------------------------------------------------------------------------


PROBLEM_MUTATORS = (
    ("missing-goal",         _taxonomies.problem_drop_goal),
    ("undefined-init-obj",   _taxonomies.problem_inject_undefined_object),
    ("undef-goal-pred",      _taxonomies.problem_undefined_goal_predicate),
    ("malformed-paren",      _taxonomies.problem_corrupt_paren),
)


async def cmd_gen_invalid_problems(
    mcp: MCPPlanner,
    domain: str,
    target: int = 5,
    force: bool = False,
    dry_run: bool = False,
    seed: int = 0,
) -> None:
    ddir = _domain_dir(domain)
    domain_pddl = (ddir / "domain.pddl").read_text()
    src = ddir / "p01.pddl"
    if not src.exists():
        raise SystemExit(f"  {domain}: p01.pddl missing — required as mutation seed")
    p01_text = src.read_text()
    rng = random.Random(seed + abs(hash(domain)) % 10_000)
    mutated: list[str] = []
    for mut_name, mut_fn in PROBLEM_MUTATORS:
        for _ in range(4):
            if len(mutated) >= target:
                break
            candidate = mut_fn(p01_text, rng=rng)
            if not candidate or candidate == p01_text or candidate in mutated:
                continue
            verdict = await _validate_problem(mcp, domain_pddl, candidate)
            if verdict is False:
                mutated.append(candidate)
        if len(mutated) >= target:
            break
    # Pad: stack two mutations (e.g. drop-goal + corrupt-paren) for
    # the 5th slot when the pool is exhausted at 4 distinct categories.
    if len(mutated) < target:
        compound = _taxonomies.problem_corrupt_paren(_taxonomies.problem_drop_goal(p01_text))
        if compound and compound not in mutated:
            verdict = await _validate_problem(mcp, domain_pddl, compound)
            if verdict is False:
                mutated.append(compound)
    if len(mutated) < target:
        raise SystemExit(
            f"  {domain}: only generated {len(mutated)}/{target} invalid problems"
        )
    print(f"gen-invalid-problems: {ddir.relative_to(REPO_ROOT)} (target={target})")
    for i, candidate in enumerate(mutated[:target], start=1):
        out_path = ddir / f"n{i:02d}.pddl"
        _write_atomic(out_path, candidate, force=force, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Generate invalid domain (single fixture per domain per spec §1)
# ---------------------------------------------------------------------------


async def cmd_gen_invalid_domain(
    mcp: MCPPlanner,
    domain: str,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    ddir = _domain_dir(domain)
    out = ddir / "domain_neg.pddl"
    if out.exists() and not force:
        print(f"gen-invalid-domain: {out.name} exists, skipping")
        return
    src = ddir / "domain.pddl"
    if not src.exists():
        raise SystemExit(f"  {domain}: domain.pddl missing")
    domain_pddl = src.read_text()
    candidates = (
        _taxonomies.domain_corrupt_paren(domain_pddl),
        _taxonomies.domain_undefined_predicate_in_effect(domain_pddl),
        _taxonomies.domain_drop_predicates_block(domain_pddl),
    )
    chosen: str | None = None
    for c in candidates:
        if c == domain_pddl:
            continue
        verdict = await _validate_domain(mcp, c)
        if verdict is False:
            chosen = c
            break
    if chosen is None:
        raise SystemExit(f"  {domain}: no domain mutation produced an invalid file")
    _write_atomic(out, chosen, force=force, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Convenience: do all of the above in order
# ---------------------------------------------------------------------------


async def cmd_all(
    mcp: MCPPlanner, domain: str, target: int = 5, force: bool = False, dry_run: bool = False,
) -> None:
    cmd_migrate(domain, dry_run=dry_run)
    await cmd_gen_invalid_domain(mcp, domain, force=force, dry_run=dry_run)
    await cmd_gen_valid_plans(mcp, domain, target=target, force=force, dry_run=dry_run)
    await cmd_gen_invalid_plans(mcp, domain, target=target, force=force, dry_run=dry_run)
    await cmd_gen_invalid_problems(mcp, domain, target=target, force=force, dry_run=dry_run)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="tools.build_fixtures")
    p.add_argument("--dry-run", action="store_true", help="report intended actions without writing files")
    p.add_argument("--force", action="store_true", help="overwrite existing fixture files")
    p.add_argument("--target", type=int, default=5, help="target count per slot (default 5)")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for mutator picks")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, helptext in (
        ("migrate", "rename legacy `_0` files in-place"),
        ("gen-valid-plans", "produce up to --target valid plans per problem"),
        ("gen-invalid-plans", "mutate v1 plan into --target invalid plans per problem"),
        ("gen-invalid-problems", "mutate p01.pddl into --target invalid problems"),
        ("gen-invalid-domain", "produce 1 invalid domain"),
        ("all", "migrate + gen-* in order"),
    ):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("domain", help="domain name (e.g. blocksworld)")
        if name in ("gen-valid-plans", "gen-invalid-plans"):
            sp.add_argument("--problem", help="restrict to a single problem name")
    return p.parse_args()


async def _async_main(args: argparse.Namespace) -> None:
    needs_mcp = args.cmd != "migrate"
    mcp: MCPPlanner | None = None
    if needs_mcp:
        mcp = await _connect_mcp()
    try:
        if args.cmd == "migrate":
            cmd_migrate(args.domain, dry_run=args.dry_run)
        elif args.cmd == "gen-valid-plans":
            await cmd_gen_valid_plans(
                mcp, args.domain, target=args.target,
                problem=args.problem, force=args.force, dry_run=args.dry_run,
            )
        elif args.cmd == "gen-invalid-plans":
            await cmd_gen_invalid_plans(
                mcp, args.domain, target=args.target,
                problem=args.problem, force=args.force, dry_run=args.dry_run,
                seed=args.seed,
            )
        elif args.cmd == "gen-invalid-problems":
            await cmd_gen_invalid_problems(
                mcp, args.domain, target=args.target,
                force=args.force, dry_run=args.dry_run, seed=args.seed,
            )
        elif args.cmd == "gen-invalid-domain":
            await cmd_gen_invalid_domain(
                mcp, args.domain, force=args.force, dry_run=args.dry_run,
            )
        elif args.cmd == "all":
            await cmd_all(
                mcp, args.domain, target=args.target,
                force=args.force, dry_run=args.dry_run,
            )
        else:  # pragma: no cover - argparse rejects unknowns
            raise SystemExit(f"unknown command {args.cmd!r}")
    finally:
        if mcp is not None:
            await mcp.close()


def main() -> None:
    args = _parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
