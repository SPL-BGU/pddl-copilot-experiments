"""Validation-gate runner for the contamination-probe renamed corpus.

Implements §4 (gates 1–10) and the round-trip determinism check (gate 11)
of `development/contamination_probe_plan.md`. Read that doc first — the
gates are the contract; this script is the executor.

Reuses `pddl_eval.chat.MCPPlanner` (stdio transport, same client the
harness uses in `generate_ground_truth`) so the oracle on disk matches
the oracle a sweep run would see byte-for-byte. Plugin discovery mirrors
`tools/build_fixtures.py` — `PDDL_MARKETPLACE_PATH` or the sibling
`../pddl-copilot` checkout.

Run order is gate-by-gate, per-domain. Per the plan: failures don't abort
the run; we record them and exit non-zero at the end so an operator gets
a complete picture in one pass.

CLI: `python3 tools/anon_validate.py --corpus-dir domains-anon
                                     [--domain depots] [--gates 1,2,...]
                                     [--canonical-dir domains/]
                                     [--maps-dir domains-anon/_maps]
                                     [--json-report report.json]
                                     [--verbose]`
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Import the lowest leaf only — keeps us out of vllm/runner pulls. Same
# contract as `tools/build_fixtures.py`.
from pddl_eval.chat import (  # noqa: E402
    MCPPlanner,
    _parse_validation_verdict,
    _safe_json_loads,
)


# Truncation cap for raw MCP payloads in the JSON report. Big enough to
# eyeball the pyvalidator `report` field, small enough that 30 domains ×
# 80+ gate-calls don't make the report unreadable.
RAW_TRUNCATE = 2000

# Plans-per-problem ceiling per `domains/README.md` taxonomy (`_v[1-5]`,
# `_b[1-5]`). Some domains commit fewer; gates 8/9 are tolerant of that.
PLANS_PER_PROBLEM_CEIL = 5

ALL_GATES = list(range(1, 12))


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    gate: int
    domain: str
    name: str
    passed: bool | None  # True/False; None = N/A (skipped, prerequisite missing)
    detail: str = ""
    # `payloads` is gate-specific structured evidence (per-fixture verdicts,
    # raw MCP responses truncated to RAW_TRUNCATE chars, replacement events).
    payloads: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Path / safety helpers
# ---------------------------------------------------------------------------


def _truncate(s: Any) -> str:
    if not isinstance(s, str):
        s = repr(s)
    return s if len(s) <= RAW_TRUNCATE else s[:RAW_TRUNCATE] + f"...<+{len(s)-RAW_TRUNCATE}>"


def _refuse_canonical(corpus_dir: Path) -> None:
    """Defence-in-depth (plan §6) — never let this script touch `domains/`.

    Even though it's read-mostly, gate 6 writes `*_solver.plan` side-files
    and gate 8 may overwrite `*_vK.plan`. A typo here = silent canonical
    mutation, which is exactly what the plan's hard-invariant forbids.
    """
    canonical = (REPO_ROOT / "domains").resolve()
    target = corpus_dir.resolve()
    if target == canonical:
        sys.exit(
            f"REFUSED: --corpus-dir resolves to the canonical {canonical} — "
            "this script writes solver-plan side-files and may rewrite vK plans. "
            "Point it at domains-anon/ instead."
        )
    try:
        if target.is_relative_to(canonical):
            sys.exit(
                f"REFUSED: --corpus-dir {target} is inside the canonical "
                f"{canonical}."
            )
    except AttributeError:
        # Py <3.9 fallback (we're on 3.11+ in the harness, but defensive).
        if str(target).startswith(str(canonical) + os.sep):
            sys.exit(f"REFUSED: --corpus-dir {target} is inside {canonical}.")


def _resolve_plugin_dirs() -> list[Path]:
    """Mirror `tools/build_fixtures.py:_resolve_plugin_dirs` — discover all
    plugins under the marketplace. We need parser + validator + solver
    (run_experiment.py's `REQUIRED_PLUGINS` only lists two; this validator
    additionally needs the parser for `inspect_domain` / `get_trajectory`).
    """
    marketplace = Path(
        os.environ.get(
            "PDDL_MARKETPLACE_PATH",
            str(REPO_ROOT.parent / "pddl-copilot"),
        )
    ).resolve()
    plugins_root = marketplace / "plugins"
    if not plugins_root.is_dir():
        raise SystemExit(
            f"pddl-copilot marketplace not found at {plugins_root!s}. "
            "Set $PDDL_MARKETPLACE_PATH to the marketplace root."
        )
    needed = ("pddl-parser", "pddl-validator", "pddl-solver")
    dirs = []
    for name in needed:
        d = plugins_root / name
        if not d.is_dir():
            raise SystemExit(f"plugin {name!r} missing under {plugins_root}")
        dirs.append(d)
    return dirs


def _discover_domains(corpus_dir: Path) -> list[tuple[str, str, Path]]:
    """Yield (dtype, dname, ddir) for every domain dir under
    `<corpus>/{classical,numeric}/`. Layout mirrors `domains/` per plan §6.
    """
    out: list[tuple[str, str, Path]] = []
    for dtype in ("classical", "numeric"):
        type_dir = corpus_dir / dtype
        if not type_dir.is_dir():
            continue
        for ddir in sorted(type_dir.iterdir()):
            if ddir.is_dir() and (ddir / "domain.pddl").exists():
                out.append((dtype, ddir.name, ddir))
    return out


def _problem_files(ddir: Path, kind: str) -> list[Path]:
    """`kind` in {'p', 'n'} — positive or negative problems. Sorted by name."""
    return sorted(ddir.glob(f"{kind}[0-9]*.pddl"))


def _plan_files(ddir: Path, pname: str, kind: str) -> list[Path]:
    """`kind` in {'v', 'b'}. Returns `p0N_<kind><K>.plan` sorted by K."""
    return sorted(ddir.glob(f"{pname}_{kind}[0-9]*.plan"))


# ---------------------------------------------------------------------------
# Per-gate logic
# ---------------------------------------------------------------------------


def _load_map(maps_dir: Path, dname: str) -> dict | None:
    """Per-domain YAML at `<maps>/<domain>.yaml` (plan §3.1)."""
    fp = maps_dir / f"{dname}.yaml"
    if not fp.exists():
        return None
    with fp.open() as fh:
        return yaml.safe_load(fh) or {}


def _rename_sides(anon_map: dict) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (sources, targets): lhs vs rhs symbols of the YAML's
    `rename.{types|predicates|actions}` block. PDDL is case-insensitive; the
    parser canonicalises casing, so both sides are lowercased.

    Object_prefixes are excluded — `inspect_domain` reports types/predicates/
    actions, not grounded object names; those are checked at problem level.
    """
    rename = (anon_map or {}).get("rename") or {}
    sources: dict[str, set[str]] = {}
    targets: dict[str, set[str]] = {}
    for kind in ("types", "predicates", "actions"):
        sub = rename.get(kind) or {}
        sources[kind] = {str(k).lower() for k in sub.keys()}
        targets[kind] = {str(v).lower() for v in sub.values()}
    return sources, targets


def _inspect_domain_symbols(data: dict) -> dict[str, set[str]]:
    """Coerce `inspect_domain` response into {kind: set(name)}.

    Defensive on shape: `predicates` and `actions` are `list[dict]` with
    `name` keys per `backends.py:DomainInfo`; tolerate list[str] as a
    fallback if a backend returns the bare-name form.
    """
    out: dict[str, set[str]] = {"types": set(), "predicates": set(), "actions": set()}
    types = data.get("types") or {}
    if isinstance(types, dict):
        out["types"] = {str(k).lower() for k in types.keys()}
    elif isinstance(types, list):
        out["types"] = {str(t).lower() for t in types}

    for kind in ("predicates", "actions"):
        items = data.get(kind) or []
        names: set[str] = set()
        for it in items:
            if isinstance(it, dict) and "name" in it:
                names.add(str(it["name"]).lower())
            elif isinstance(it, str):
                names.add(it.lower())
        out[kind] = names
    return out


async def _validate_call(
    mcp: MCPPlanner, tool: str, args: dict
) -> tuple[bool | None, str, dict | None, bool]:
    """Run a validator-shaped MCP tool. Returns (verdict, raw, parsed, mcp_error).

    `mcp_error=True` means the plugin returned `{"error": True, ...}` (or the
    transport raised). Per the plan + project routing rule (CLAUDE.md), we
    do NOT patch the tool — we record `mcp_error` and let the gate fail.
    """
    try:
        raw = await mcp.call_tool(tool, args)
    except Exception as exc:
        return None, f"<transport-exception> {exc!r}", None, True
    parsed = _safe_json_loads(raw)
    if isinstance(parsed, dict) and parsed.get("error") is True:
        return None, raw, parsed, True
    return _parse_validation_verdict(raw), raw, parsed, False


async def _solve_call(
    mcp: MCPPlanner, planner: str, domain_pddl: str, problem_pddl: str
) -> tuple[list[str] | None, str, bool]:
    """Returns (plan_lines_or_None, raw, mcp_error)."""
    try:
        raw = await mcp.call_tool(planner, {"domain": domain_pddl, "problem": problem_pddl})
    except Exception as exc:
        return None, f"<transport-exception> {exc!r}", True
    data = _safe_json_loads(raw)
    if isinstance(data, dict) and data.get("error") is True:
        return None, raw, True
    if isinstance(data, dict) and isinstance(data.get("plan"), list) and data["plan"]:
        return list(data["plan"]), raw, False
    # Empty plan or `{"plan": [], "note": "unsolvable"}` — gate 6 fails.
    return None, raw, False


# Each gate runner takes (mcp, ctx) and returns a GateResult. `ctx` carries
# per-domain inputs + the cross-gate cache (solver_plans, replacements).
@dataclass
class DomainCtx:
    dtype: str
    dname: str
    ddir: Path
    domain_pddl: str
    domain_neg_pddl: str | None
    anon_map: dict | None
    # Cross-gate cache.
    solver_plans: dict[str, list[str]] = field(default_factory=dict)  # pname -> plan
    replacements: list[dict] = field(default_factory=list)  # gate-8 events


async def gate_1(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    """`inspect_domain` parses the renamed domain and exposes the renamed
    symbols. Cross-check the renamed targets from `<maps>/<dname>.yaml`
    against the names the parser reports (set-inclusion, order-free).
    """
    try:
        raw = await mcp.call_tool("inspect_domain", {"domain": ctx.domain_pddl})
    except Exception as exc:
        return GateResult(1, ctx.dname, "domain_syntax", False,
                          detail=f"transport exception: {exc!r}",
                          payloads=[{"raw": _truncate(str(exc))}])
    parsed = _safe_json_loads(raw)
    if not isinstance(parsed, dict) or parsed.get("error") is True:
        return GateResult(1, ctx.dname, "domain_syntax", False,
                          detail="inspect_domain returned error/unparseable",
                          payloads=[{"raw": _truncate(raw)}])
    parser_syms = _inspect_domain_symbols(parsed)
    payloads: list[dict] = [{
        "tool": "inspect_domain",
        "parser_types": sorted(parser_syms["types"]),
        "parser_predicates": sorted(parser_syms["predicates"]),
        "parser_actions": sorted(parser_syms["actions"]),
    }]
    if ctx.anon_map is None:
        # Yaml missing — we can still confirm the domain parses, but we
        # cannot cross-check renames. Pass with a noted caveat.
        return GateResult(1, ctx.dname, "domain_syntax", True,
                          detail="parsed; no map YAML present for cross-check",
                          payloads=payloads)
    sources, targets = _rename_sides(ctx.anon_map)
    payloads[0]["expected_targets"] = {k: sorted(v) for k, v in targets.items()}
    payloads[0]["expected_sources_absent"] = {k: sorted(v) for k, v in sources.items()}

    # Two checks (both required):
    #   (a) every renamed *target* is present in the parser response
    #       — otherwise the rename was incomplete and a target leaked nothing
    #   (b) NO canonical *source* symbol remains in the parser response
    #       — otherwise the rewriter missed a site, which is the exact
    #         lexical-contamination leak this whole probe is built to detect
    # (b) is the load-bearing one; (a) is defensive — a target listed in the
    # map but absent from the domain means the map is stale.
    missing: dict[str, list[str]] = {}
    leaked: dict[str, list[str]] = {}
    for kind in ("types", "predicates", "actions"):
        miss = sorted(s for s in targets[kind] if s not in parser_syms[kind])
        leak = sorted(s for s in sources[kind] if s in parser_syms[kind])
        if miss:
            missing[kind] = miss
        if leak:
            leaked[kind] = leak
    if missing or leaked:
        bits = []
        if leaked:
            bits.append(f"canonical source symbols still present: {leaked}")
        if missing:
            bits.append(f"renamed targets missing from parser response: {missing}")
        return GateResult(1, ctx.dname, "domain_syntax", False,
                          detail="; ".join(bits),
                          payloads=payloads)
    return GateResult(1, ctx.dname, "domain_syntax", True,
                      detail="parsed; all renamed targets present, no source leaks",
                      payloads=payloads)


async def gate_2(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    verdict, raw, _, mcp_error = await _validate_call(
        mcp, "validate_domain", {"domain": ctx.domain_pddl}
    )
    passed = (verdict is True) and not mcp_error
    return GateResult(2, ctx.dname, "domain_validity", passed,
                      detail=("expected valid=true; "
                              f"got verdict={verdict!r} mcp_error={mcp_error}"),
                      payloads=[{"raw": _truncate(raw)}])


async def gate_3(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    if ctx.domain_neg_pddl is None:
        return GateResult(3, ctx.dname, "neg_domain_validity", None,
                          detail="domain_neg.pddl not present — skipped")
    verdict, raw, _, mcp_error = await _validate_call(
        mcp, "validate_domain", {"domain": ctx.domain_neg_pddl}
    )
    # `valid=false` is the goal; `mcp_error` (e.g. parser threw on the
    # broken domain) is NOT a pass — we need a reasoned `valid=false`
    # verdict so we know the rewriter preserved the bug class.
    passed = (verdict is False) and not mcp_error
    return GateResult(3, ctx.dname, "neg_domain_validity", passed,
                      detail=("expected valid=false; "
                              f"got verdict={verdict!r} mcp_error={mcp_error}"),
                      payloads=[{"raw": _truncate(raw)}])


async def _validate_problems(
    mcp: MCPPlanner, ctx: DomainCtx, expect_valid: bool, kind: str, gate_num: int, gate_name: str,
) -> GateResult:
    files = _problem_files(ctx.ddir, kind)
    if not files:
        return GateResult(gate_num, ctx.dname, gate_name, None,
                          detail=f"no {kind}NN.pddl fixtures present — skipped")
    payloads = []
    all_pass = True
    for pf in files:
        ppddl = pf.read_text()
        verdict, raw, _, mcp_error = await _validate_call(
            mcp, "validate_problem",
            {"domain": ctx.domain_pddl, "problem": ppddl},
        )
        ok = (verdict is expect_valid) and not mcp_error
        payloads.append({
            "fixture": pf.name,
            "expected_valid": expect_valid,
            "verdict": verdict,
            "mcp_error": mcp_error,
            "passed": ok,
            "raw": _truncate(raw),
        })
        all_pass = all_pass and ok
    return GateResult(gate_num, ctx.dname, gate_name, all_pass,
                      detail=f"checked {len(files)} fixtures, all_pass={all_pass}",
                      payloads=payloads)


async def gate_4(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    return await _validate_problems(mcp, ctx, True, "p", 4, "pos_problem_validity")


async def gate_5(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    return await _validate_problems(mcp, ctx, False, "n", 5, "neg_problem_validity")


async def gate_6(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    """Re-solve each p0N.pddl with the matching planner. Persist freshly-
    solved plan to `<ddir>/<pname>_solver.plan` (DO NOT overwrite vK plans).
    Cache plans in `ctx.solver_plans[pname]` for gates 7/8.
    """
    planner = "classic_planner" if ctx.dtype == "classical" else "numeric_planner"
    files = _problem_files(ctx.ddir, "p")
    if not files:
        return GateResult(6, ctx.dname, "resolve_positives", None,
                          detail="no positive problems present — skipped")
    payloads = []
    all_pass = True
    for pf in files:
        pname = pf.stem
        ppddl = pf.read_text()
        plan_lines, raw, mcp_error = await _solve_call(mcp, planner, ctx.domain_pddl, ppddl)
        ok = plan_lines is not None and not mcp_error
        side_file = ctx.ddir / f"{pname}_solver.plan"
        if ok:
            # Re-confirm side-file is inside the corpus dir before writing.
            # Defence-in-depth: `_refuse_canonical` already cleared the corpus
            # root, but pname comes from a glob so this is belt-and-braces.
            side_file.write_text("\n".join(plan_lines) + "\n")
            ctx.solver_plans[pname] = plan_lines
        payloads.append({
            "fixture": pf.name,
            "planner": planner,
            "plan_returned": ok,
            "plan_len": len(plan_lines) if plan_lines else 0,
            "solver_plan_path": str(side_file) if ok else None,
            "mcp_error": mcp_error,
            "raw": _truncate(raw),
        })
        all_pass = all_pass and ok
    return GateResult(6, ctx.dname, "resolve_positives", all_pass,
                      detail=f"solved {len(ctx.solver_plans)}/{len(files)} problems",
                      payloads=payloads)


async def gate_7(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    """Plan equivalence: BOTH the committed `p0N_v1.plan` AND the gate-6
    solver plan must reach the goal against the renamed domain/problem.

    SPEC AMBIGUITY: plan §4 row 7 invokes `get_trajectory` and demands
    `valid=true`, but `get_trajectory` returns `{"trajectory", "final_state",
    "num_steps"}` — no `valid` field. The verdict-bearing tool is
    `validate_plan`. We use `validate_plan` as the verdict (pass = both
    reach goal) AND call `get_trajectory` for the structural trace (pass
    = non-empty `trajectory` + no `error`). Both must pass. Flagged in the
    final-report ambiguities list.
    """
    if not ctx.solver_plans:
        return GateResult(7, ctx.dname, "plan_equivalence", None,
                          detail="gate 6 did not produce solver plans — skipped")
    files = _problem_files(ctx.ddir, "p")
    payloads = []
    all_pass = True
    for pf in files:
        pname = pf.stem
        ppddl = pf.read_text()
        v1_path = ctx.ddir / f"{pname}_v1.plan"
        solver_plan = ctx.solver_plans.get(pname)
        if not v1_path.exists() or solver_plan is None:
            payloads.append({
                "fixture": pname,
                "skipped": True,
                "reason": ("missing v1.plan" if not v1_path.exists()
                           else "no solver plan from gate 6"),
            })
            all_pass = False
            continue
        v1_text = v1_path.read_text()
        # validate_plan on committed v1
        v1_verdict, v1_raw, _, v1_err = await _validate_call(
            mcp, "validate_plan",
            {"domain": ctx.domain_pddl, "problem": ppddl, "plan": v1_text},
        )
        # validate_plan on solver plan
        sv_verdict, sv_raw, _, sv_err = await _validate_call(
            mcp, "validate_plan",
            {"domain": ctx.domain_pddl, "problem": ppddl, "plan": solver_plan},
        )
        # get_trajectory on both (structural — non-empty trajectory + no error)
        try:
            traj_v1_raw = await mcp.call_tool(
                "get_trajectory",
                {"domain": ctx.domain_pddl, "problem": ppddl, "plan": v1_text},
            )
        except Exception as exc:
            traj_v1_raw = f"<transport-exception> {exc!r}"
        try:
            traj_sv_raw = await mcp.call_tool(
                "get_trajectory",
                {"domain": ctx.domain_pddl, "problem": ppddl, "plan": solver_plan},
            )
        except Exception as exc:
            traj_sv_raw = f"<transport-exception> {exc!r}"
        traj_v1 = _safe_json_loads(traj_v1_raw)
        traj_sv = _safe_json_loads(traj_sv_raw)
        traj_v1_ok = (
            isinstance(traj_v1, dict)
            and not traj_v1.get("error")
            and bool(traj_v1.get("trajectory"))
        )
        traj_sv_ok = (
            isinstance(traj_sv, dict)
            and not traj_sv.get("error")
            and bool(traj_sv.get("trajectory"))
        )
        ok = (
            v1_verdict is True and not v1_err
            and sv_verdict is True and not sv_err
            and traj_v1_ok and traj_sv_ok
        )
        payloads.append({
            "fixture": pname,
            "v1_validate_plan": {"verdict": v1_verdict, "mcp_error": v1_err,
                                 "raw": _truncate(v1_raw)},
            "solver_validate_plan": {"verdict": sv_verdict, "mcp_error": sv_err,
                                     "raw": _truncate(sv_raw)},
            "v1_get_trajectory_ok": traj_v1_ok,
            "solver_get_trajectory_ok": traj_sv_ok,
            "v1_trajectory_raw": _truncate(traj_v1_raw),
            "solver_trajectory_raw": _truncate(traj_sv_raw),
            "passed": ok,
        })
        all_pass = all_pass and ok
    return GateResult(7, ctx.dname, "plan_equivalence", all_pass,
                      detail=f"checked {len(payloads)} pairs, all_pass={all_pass}",
                      payloads=payloads)


async def gate_8(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    """`validate_plan` on every `p0N_vK.plan`. If a vK fails, REPLACE it with
    the gate-6 solver output and re-validate. Record the replacement.

    Per the plan, gate-8 is the only step that may overwrite a committed
    valid plan; we require ctx.solver_plans[pname] to do the replacement.
    """
    pos_files = _problem_files(ctx.ddir, "p")
    if not pos_files:
        return GateResult(8, ctx.dname, "valid_plan_validity", None,
                          detail="no positive problems present — skipped")
    payloads = []
    all_pass = True
    for pf in pos_files:
        pname = pf.stem
        ppddl = pf.read_text()
        v_files = _plan_files(ctx.ddir, pname, "v")
        if not v_files:
            payloads.append({"fixture": pname, "skipped": True,
                             "reason": "no vK plans present"})
            continue
        for vf in v_files:
            plan_text = vf.read_text()
            verdict, raw, _, mcp_err = await _validate_call(
                mcp, "validate_plan",
                {"domain": ctx.domain_pddl, "problem": ppddl, "plan": plan_text},
            )
            replaced = False
            replacement_payload: dict | None = None
            if verdict is True and not mcp_err:
                payloads.append({
                    "fixture": vf.name, "verdict": verdict, "mcp_error": mcp_err,
                    "passed": True, "raw": _truncate(raw),
                })
                continue
            # Fall back to solver plan from gate 6.
            solver_plan = ctx.solver_plans.get(pname)
            if solver_plan is None:
                payloads.append({
                    "fixture": vf.name, "verdict": verdict, "mcp_error": mcp_err,
                    "passed": False, "raw": _truncate(raw),
                    "replacement_attempted": False,
                    "reason": "no gate-6 solver plan available",
                })
                all_pass = False
                continue
            new_text = "\n".join(solver_plan) + "\n"
            old_sha = hashlib.sha256(plan_text.encode("utf-8")).hexdigest()
            new_sha = hashlib.sha256(new_text.encode("utf-8")).hexdigest()
            vf.write_text(new_text)
            ctx.replacements.append({
                "fixture": str(vf),
                "old_text_sha256": old_sha,
                "new_text_sha256": new_sha,
                "new_plan_lines": len(solver_plan),
            })
            replaced = True
            re_verdict, re_raw, _, re_err = await _validate_call(
                mcp, "validate_plan",
                {"domain": ctx.domain_pddl, "problem": ppddl, "plan": new_text},
            )
            ok = (re_verdict is True) and not re_err
            replacement_payload = {
                "replaced": True,
                "new_verdict": re_verdict,
                "new_mcp_error": re_err,
                "new_raw": _truncate(re_raw),
            }
            payloads.append({
                "fixture": vf.name,
                "orig_verdict": verdict, "orig_mcp_error": mcp_err,
                "orig_raw": _truncate(raw),
                "passed": ok,
                "replacement": replacement_payload,
            })
            all_pass = all_pass and ok
    return GateResult(8, ctx.dname, "valid_plan_validity", all_pass,
                      detail=(f"checked {len(payloads)} plan-fixtures, "
                              f"replacements={len(ctx.replacements)}, "
                              f"all_pass={all_pass}"),
                      payloads=payloads)


async def gate_9(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    """`validate_plan` on every `p0N_bK.plan` → `valid=false`. NO replacement
    on failure — the bug-structure invariance is itself under test.
    """
    pos_files = _problem_files(ctx.ddir, "p")
    if not pos_files:
        return GateResult(9, ctx.dname, "invalid_plan_validity", None,
                          detail="no positive problems present — skipped")
    payloads = []
    all_pass = True
    any_checked = False
    for pf in pos_files:
        pname = pf.stem
        ppddl = pf.read_text()
        b_files = _plan_files(ctx.ddir, pname, "b")
        for bf in b_files:
            any_checked = True
            plan_text = bf.read_text()
            verdict, raw, _, mcp_err = await _validate_call(
                mcp, "validate_plan",
                {"domain": ctx.domain_pddl, "problem": ppddl, "plan": plan_text},
            )
            ok = (verdict is False) and not mcp_err
            payloads.append({
                "fixture": bf.name, "expected_valid": False,
                "verdict": verdict, "mcp_error": mcp_err,
                "passed": ok, "raw": _truncate(raw),
            })
            all_pass = all_pass and ok
    if not any_checked:
        return GateResult(9, ctx.dname, "invalid_plan_validity", None,
                          detail="no bK plans present — skipped")
    return GateResult(9, ctx.dname, "invalid_plan_validity", all_pass,
                      detail=f"checked {len(payloads)} bK plans, all_pass={all_pass}",
                      payloads=payloads)


async def gate_10(mcp: MCPPlanner, ctx: DomainCtx) -> GateResult:
    """`get_state_transition` on each (`p0N.pddl`, `p0N_v1.plan`).
    Pass = non-empty `trajectory` and `valid=true`.
    """
    pos_files = _problem_files(ctx.ddir, "p")
    if not pos_files:
        return GateResult(10, ctx.dname, "trajectory_smoke", None,
                          detail="no positive problems present — skipped")
    payloads = []
    all_pass = True
    any_checked = False
    for pf in pos_files:
        pname = pf.stem
        ppddl = pf.read_text()
        v1 = ctx.ddir / f"{pname}_v1.plan"
        if not v1.exists():
            payloads.append({"fixture": pname, "skipped": True,
                             "reason": "no v1 plan"})
            continue
        any_checked = True
        try:
            raw = await mcp.call_tool(
                "get_state_transition",
                {"domain": ctx.domain_pddl, "problem": ppddl, "plan": v1.read_text()},
            )
        except Exception as exc:
            raw = f"<transport-exception> {exc!r}"
        parsed = _safe_json_loads(raw)
        mcp_err = isinstance(parsed, dict) and parsed.get("error") is True
        traj = parsed.get("trajectory") if isinstance(parsed, dict) else None
        valid = parsed.get("valid") if isinstance(parsed, dict) else None
        ok = (
            isinstance(parsed, dict) and not mcp_err
            and valid is True and bool(traj)
        )
        payloads.append({
            "fixture": f"{pname} + {pname}_v1.plan",
            "valid": valid, "trajectory_nonempty": bool(traj),
            "mcp_error": mcp_err, "passed": ok, "raw": _truncate(raw),
        })
        all_pass = all_pass and ok
    if not any_checked:
        return GateResult(10, ctx.dname, "trajectory_smoke", None,
                          detail="no v1 plans present — skipped")
    return GateResult(10, ctx.dname, "trajectory_smoke", all_pass,
                      detail=f"checked {len(payloads)} (problem, v1) pairs, all_pass={all_pass}",
                      payloads=payloads)


def gate_11_roundtrip(
    corpus_dir: Path, canonical_dir: Path, maps_dir: Path,
) -> GateResult:
    """Round-trip determinism: invoke the sibling rewriter's
    `--round-trip-check` and surface its exit code. Run once for the whole
    corpus (not per-domain), so we record it under domain="<all>" — the
    summary table renders it as a single row.

    If `tools/anon_rename.py` doesn't exist yet (sibling agent in flight),
    mark N/A — not FAIL — so the operator can re-run after the rewriter
    lands without a confusing diff.
    """
    rewriter = REPO_ROOT / "tools" / "anon_rename.py"
    if not rewriter.exists():
        return GateResult(11, "<all>", "roundtrip_determinism", None,
                          detail=f"{rewriter} not present yet — gate skipped",
                          payloads=[])
    cmd = [
        sys.executable, str(rewriter), "--round-trip-check",
        "--output-dir", str(corpus_dir),
        "--source-dir", str(canonical_dir),
        "--maps-dir", str(maps_dir),
    ]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return GateResult(11, "<all>", "roundtrip_determinism", False,
                          detail="anon_rename.py --round-trip-check timed out",
                          payloads=[{"cmd": cmd}])
    except Exception as exc:
        return GateResult(11, "<all>", "roundtrip_determinism", False,
                          detail=f"failed to invoke rewriter: {exc!r}",
                          payloads=[{"cmd": cmd}])
    ok = cp.returncode == 0
    return GateResult(11, "<all>", "roundtrip_determinism", ok,
                      detail=f"exit={cp.returncode}",
                      payloads=[{
                          "cmd": cmd,
                          "stdout": _truncate(cp.stdout),
                          "stderr": _truncate(cp.stderr),
                      }])


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


# Per-domain gates run in (mcp, ctx) signature; gate 11 is corpus-level
# and synchronous. Keep them separate so the dispatch reads as the spec
# does.
PER_DOMAIN_GATES = OrderedDict([
    (1, gate_1), (2, gate_2), (3, gate_3),
    (4, gate_4), (5, gate_5), (6, gate_6),
    (7, gate_7), (8, gate_8), (9, gate_9), (10, gate_10),
])


def _parse_gates_arg(s: str | None) -> list[int]:
    if not s:
        return list(ALL_GATES)
    out: list[int] = []
    for piece in s.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            n = int(piece)
        except ValueError:
            sys.exit(f"--gates: not an int: {piece!r}")
        if n not in ALL_GATES:
            sys.exit(f"--gates: {n} not in {ALL_GATES}")
        out.append(n)
    return sorted(set(out))


def _prereq_warn(selected: list[int]) -> None:
    """Gates 7 + 8 (fallback) need gate 6 to seed solver_plans. We don't
    auto-pull — explicit selection is what the user asked for — but we
    warn loud so a partial-rerun doesn't silently false-pass a gate that
    skipped its inputs.
    """
    if 6 not in selected and any(g in selected for g in (7, 8)):
        logging.warning(
            "Gates 7 and 8 depend on gate 6 (solver plans). Without 6, "
            "gate 7 will skip (N/A) and gate 8 cannot perform replacements. "
            "Add 6 to --gates to get full coverage."
        )


async def _run_async(args: argparse.Namespace) -> int:
    corpus_dir = Path(args.corpus_dir).resolve()
    _refuse_canonical(corpus_dir)
    if not corpus_dir.is_dir():
        sys.exit(f"--corpus-dir does not exist or is not a directory: {corpus_dir}")

    maps_dir = Path(args.maps_dir).resolve() if args.maps_dir \
        else (corpus_dir / "_maps").resolve()
    canonical_dir = Path(args.canonical_dir).resolve()

    selected_gates = _parse_gates_arg(args.gates)
    _prereq_warn(selected_gates)

    domains = _discover_domains(corpus_dir)
    if args.domain:
        wanted = set(args.domain)
        domains = [d for d in domains if d[1] in wanted]
        missing = wanted - {d[1] for d in domains}
        if missing:
            sys.exit(f"--domain not found under {corpus_dir}: {sorted(missing)}")
    if not domains:
        sys.exit(f"No domains found under {corpus_dir}/{{classical,numeric}}/")

    logging.info("Corpus:    %s", corpus_dir)
    logging.info("Maps:      %s", maps_dir)
    logging.info("Canonical: %s", canonical_dir)
    logging.info("Gates:     %s", selected_gates)
    logging.info("Domains:   %s", [d[1] for d in domains])

    # Connect MCP servers once for all domains/gates.
    mcp = MCPPlanner()
    plugin_dirs = _resolve_plugin_dirs()
    await mcp.connect(plugin_dirs)

    results: list[GateResult] = []
    try:
        for dtype, dname, ddir in domains:
            logging.info("=== %s/%s ===", dtype, dname)
            domain_pddl = (ddir / "domain.pddl").read_text()
            neg_path = ddir / "domain_neg.pddl"
            domain_neg_pddl = neg_path.read_text() if neg_path.exists() else None
            anon_map = _load_map(maps_dir, dname)
            ctx = DomainCtx(
                dtype=dtype, dname=dname, ddir=ddir,
                domain_pddl=domain_pddl, domain_neg_pddl=domain_neg_pddl,
                anon_map=anon_map,
            )
            for gnum in selected_gates:
                if gnum == 11:
                    continue  # handled corpus-wide after the loop
                gate_fn = PER_DOMAIN_GATES[gnum]
                try:
                    res = await gate_fn(mcp, ctx)
                except Exception as exc:
                    res = GateResult(gnum, dname, gate_fn.__name__, False,
                                     detail=f"gate raised: {exc!r}")
                results.append(res)
                logging.info(
                    "  gate %2d %-22s %s %s",
                    res.gate, res.name,
                    {True: "PASS", False: "FAIL", None: "N/A"}[res.passed],
                    res.detail,
                )
    finally:
        await mcp.close()

    if 11 in selected_gates:
        r11 = gate_11_roundtrip(corpus_dir, canonical_dir, maps_dir)
        results.append(r11)
        logging.info(
            "  gate 11 %-22s %s %s",
            r11.name, {True: "PASS", False: "FAIL", None: "N/A"}[r11.passed], r11.detail,
        )

    _print_summary(results, selected_gates, [d[1] for d in domains])
    if args.json_report:
        _write_json_report(Path(args.json_report), results, args)

    any_fail = any(r.passed is False for r in results)
    return 1 if any_fail else 0


def _print_summary(
    results: list[GateResult], gates: list[int], domains: list[str],
) -> None:
    print()
    print("=" * 78)
    print("Per-gate × per-domain summary  (PASS / FAIL / N/A)")
    print("=" * 78)
    # index by (gate, domain) -> verdict char
    idx: dict[tuple[int, str], str] = {}
    for r in results:
        idx[(r.gate, r.domain)] = {True: "PASS", False: "FAIL", None: "N/A "}[r.passed]
    domain_w = max(8, max((len(d) for d in domains), default=8))
    header = "gate  " + "  ".join(d.ljust(domain_w) for d in domains)
    if 11 in gates:
        header += "  " + "<all>".ljust(domain_w)
    print(header)
    for gnum in gates:
        if gnum == 11:
            row = f"  {gnum:>2}  " + "  ".join("-".ljust(domain_w) for _ in domains)
            row += "  " + idx.get((11, "<all>"), "N/A ").ljust(domain_w)
        else:
            row = f"  {gnum:>2}  " + "  ".join(
                idx.get((gnum, d), "N/A ").ljust(domain_w) for d in domains
            )
        print(row)
    print()
    fails = [r for r in results if r.passed is False]
    skips = [r for r in results if r.passed is None]
    passes = [r for r in results if r.passed is True]
    print(f"Total: {len(passes)} PASS, {len(fails)} FAIL, {len(skips)} N/A")
    if fails:
        print("Failures:")
        for r in fails:
            print(f"  gate {r.gate:>2} {r.domain}: {r.detail}")


def _write_json_report(
    out_path: Path, results: list[GateResult], args: argparse.Namespace,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "corpus_dir": str(Path(args.corpus_dir).resolve()),
        "canonical_dir": str(Path(args.canonical_dir).resolve()),
        "maps_dir": str(
            (Path(args.maps_dir).resolve() if args.maps_dir
             else (Path(args.corpus_dir).resolve() / "_maps"))
        ),
        "gates": _parse_gates_arg(args.gates),
        "raw_truncate": RAW_TRUNCATE,
        "results": [
            {
                "gate": r.gate,
                "domain": r.domain,
                "name": r.name,
                "passed": r.passed,  # True / False / None
                "detail": r.detail,
                "payloads": r.payloads,
            }
            for r in results
        ],
    }
    with out_path.open("w") as fh:
        json.dump(report, fh, indent=2, default=str)
    logging.info("Wrote JSON report: %s", out_path)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Run §4 validation gates over the renamed corpus.",
    )
    p.add_argument("--corpus-dir", required=True,
                   help="Root of the renamed corpus (e.g. domains-anon/). "
                        "REFUSED if this resolves to domains/ or inside it.")
    p.add_argument("--domain", action="append", default=None,
                   help="Domain name to validate; repeatable. Default: all.")
    p.add_argument("--gates", default=None,
                   help=f"Comma-separated gate numbers from {ALL_GATES}. "
                        "Default: all.")
    p.add_argument("--canonical-dir", default=str(REPO_ROOT / "domains"),
                   help="Canonical corpus root (gate 11 only). "
                        "Default: <repo>/domains.")
    p.add_argument("--maps-dir", default=None,
                   help="Per-domain YAML map directory. "
                        "Default: <corpus-dir>/_maps.")
    p.add_argument("--json-report", default=None,
                   help="Write a structured JSON report to this path.")
    p.add_argument("--verbose", action="store_true",
                   help="Raise log level from WARNING to INFO.")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s  %(levelname)s  %(message)s",
    )
    rc = asyncio.run(_run_async(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
