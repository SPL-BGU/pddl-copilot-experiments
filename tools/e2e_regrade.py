#!/usr/bin/env python3
"""End-to-end (response-graded) overlay regrade — Phases 1+2 (all 5 tasks).

Implements the decisions recorded in
development/tool_call_vs_final_output_grading.md (2026-07-11):
  D1/D2  end-to-end success = grade the MODEL'S final response with the same
         parser the no-tools branch uses, both arms; the stored tool-graded
         success is kept alongside as "tool-verified".
  D2b    BOTH operationalizations are emitted per row so the headline choice
         stays a table-level decision, not a regrade:
           e2e         D2b=B — a bare tool call counts as the model's answer
                       when the model closed the turn on its own
                       (done_reason == "stop", empty response, tool-verified);
                       truncated-empty (done_reason == "length") fails.
           e2e_strict  D2b=i — any empty final turn fails, both arms.
         The two differ exactly on rows with
         e2e_reason == "delegation_terminal_credit".
  D6=A   corpora written under the 500-char response snapshot cap
         (pre-2026-06-25, runner.py RESPONSE_SNAPSHOT_LEN) are censored: a
         non-empty snapshot exactly at the cap with no gradeable answer is
         INDETERMINATE, and rates are reported as [lower, upper] bounds.

Per-task grading of the stored response:
  validate_*  truth from fixture naming (verified against runner.py emission:
              pname "domain_neg"/"n##" = INVALID fixtures, plan_label v*/b* =
              VALID/INVALID); verdict via the no-tools two-stage parse.
  solve       plan extracted via SolveResponse / extract_plan_lines, then
              validated through live MCP (`_validate_model_plan`, same oracle
              as online grading). Needs --marketplace-path plugins.
  simulate    trajectory coerced via `_coerce_simulate_trajectory` and
              compared to the gt-cache oracle trace through the CURRENT
              `_normalize_trajectory` (includes the `_canon_atom` predicate-
              notation fix, so this regrade also repairs the pre-fix simulate
              normalizer artifact). NO-TOOLS simulate rows are REgraded too
              (stored grades on pre-fix corpora used the buggy normalizer);
              all other no-tools rows pass through their stored online grade.

Ground truth for solve/simulate comes from results/derived/gt_cache.json
(build with tools/build_gt_cache.py — one-time local MCP run).

The overlay is DERIVED data: canonical trials.jsonl files are never touched.
Output mirrors <corpus>/<cell>/trials.jsonl as
results/derived/e2e_overlay/<corpus>/<cell>.e2e.jsonl, one row per input
trial, plus a per-corpus summary printed to stdout.
"""

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval.schemas import SolveResponse, ValidateResponse  # noqa: E402
from pddl_eval.scoring import (  # noqa: E402
    _VALIDATE_TOOL_NAMES,
    _coerce_simulate_trajectory,
    _normalize_trajectory,
    _parse_validation_verdict,
    _safe_json_loads,
    _safe_pydantic_validate,
    _tool_error_seen,
    _validate_model_plan,
    extract_plan_lines,
    extract_verdict,
)

VALIDATE_TASKS = ("validate_domain", "validate_problem", "validate_plan")
ALL_TASKS = VALIDATE_TASKS + ("solve", "simulate")
# Snapshot caps the runner has ever used (runner.py RESPONSE_SNAPSHOT_LEN):
# 500 until 2026-06-25, 16384 after. A stored response of exactly cap length
# is (with negligible false-positive mass) a truncated snapshot.
KNOWN_CAPS = (500, 16384)

NEG_PROBLEM_RE = re.compile(r"^n\d\d$")


def truth_for(row: dict) -> bool | None:
    task = row["task"]
    if task == "validate_domain":
        return row["problem_name"] != "domain_neg"
    if task == "validate_problem":
        return not NEG_PROBLEM_RE.match(row["problem_name"] or "")
    if task == "validate_plan":
        label = row.get("plan_label") or ""
        if label.startswith("v"):
            return True
        if label.startswith("b"):
            return False
        return None
    return None


def recompute_tool_verified(row: dict, truth: bool) -> tuple[bool, str]:
    """Mirror of the current check_success validate_* with-tools branch
    (scoring.py:521-539), applied offline to the stored tool calls."""
    task = row["task"]
    tool_calls = row.get("tool_calls") or []
    if not any(tc.get("name") == task for tc in tool_calls):
        if any(tc.get("name") in _VALIDATE_TOOL_NAMES for tc in tool_calls):
            return False, "wrong_tool"
        return False, "tool_not_selected"
    for tc in tool_calls:
        if tc.get("name") != task:
            continue
        if _parse_validation_verdict(tc.get("result", "")) == truth:
            return True, "ok"
    if _tool_error_seen(tool_calls, task):
        return False, "tool_error"
    return False, "verdict_mismatch"


def response_verdict(resp: str) -> bool | None:
    """Same two-stage parse as the no-tools grading branch (scoring.py)."""
    parsed = _safe_pydantic_validate(ValidateResponse, resp or "")
    if parsed is not None:
        return parsed.verdict == "VALID"
    return extract_verdict(resp or "")


def detect_cap(max_len: int) -> int | None:
    """Smallest known snapshot cap the corpus could have been written under."""
    for cap in KNOWN_CAPS:
        if max_len <= cap:
            return cap
    return None


def oracle_canon_for(gt_cache: dict, row: dict):
    trace = (gt_cache.get(row["domain_name"], {})
             .get(row["problem_name"], {}) or {}).get("trace")
    if isinstance(trace, str):
        trace = _safe_json_loads(trace)
    if not isinstance(trace, dict):
        return None
    return _normalize_trajectory(trace.get("trajectory"))


def _base_out(row: dict) -> dict:
    return {
        "task": row["task"],
        "model": row["model"],
        "domain_name": row["domain_name"],
        "problem_name": row["problem_name"],
        "plan_label": row.get("plan_label", ""),
        "prompt_variant": row.get("prompt_variant"),
        "with_tools": row["with_tools"],
        "tool_verified": row["success"] if row["with_tools"] else None,
        "success_stored": row["success"],
        "done_reason": row.get("done_reason"),
        "infra_failure": row.get("infra_failure", False),
        "response_len": len(row.get("response") or ""),
    }


def _grade_empty_or_censored(out: dict, row: dict, resp: str, cap: int | None,
                             parse_fail_reason: str) -> dict:
    """Shared tail rules: D2b=B empty handling, then cap censoring."""
    if not resp.strip():
        if not row["with_tools"]:
            out["e2e"] = False
            out["e2e_reason"] = "empty_response"
        elif row.get("done_reason") == "stop" and row["success"] is True:
            # D2b=B: the model deliberately ended its turn with the tool call
            # as its only substantive output, and that call was correct.
            out["e2e"] = True
            out["e2e_reason"] = "delegation_terminal_credit"
        elif row.get("done_reason") == "stop":
            out["e2e"] = False
            out["e2e_reason"] = "empty_stop_not_tool_verified"
        else:
            out["e2e"] = False
            out["e2e_reason"] = "truncated_empty"
        return out
    if cap is not None and len(resp) == cap:
        out["e2e"] = "indeterminate"
        out["e2e_reason"] = "censored_at_snapshot_cap"
        return out
    out["e2e"] = False
    out["e2e_reason"] = parse_fail_reason
    return out


async def regrade_row(row: dict, cap: int | None, gt_cache: dict,
                      ctx: "SolveContext") -> dict:
    """Return the overlay verdict for one trial row.

    e2e is one of True / False / "indeterminate" (censored).
    """
    out = _base_out(row)
    task = row["task"]
    resp = row.get("response") or ""

    # --- validate_* / solve no-tools: stored grade already ran online on the
    # full response text; it IS the end-to-end verdict. simulate no-tools is
    # the exception (pre-fix normalizer) and falls through to the regrade.
    if not row["with_tools"] and task != "simulate":
        out["e2e"] = row["success"]
        out["e2e_reason"] = "stored_online_grade"
        return out

    if task in VALIDATE_TASKS:
        truth = truth_for(row)
        if truth is None:
            out["e2e"] = "indeterminate"
            out["e2e_reason"] = "no_ground_truth"
            return out
        if row["with_tools"]:
            # Phase 3: recompute tool-verified + failure reason with TODAY'S
            # binning (stored corpora were graded before _tool_error_seen
            # learned the FastMCP "Error executing tool" arg-error shape, so
            # those rows sit mis-binned as verdict_mismatch). Tool results
            # are stored uncapped, so this recompute is exact.
            tv_fixed, tool_fr = recompute_tool_verified(row, truth)
            out["tool_verified_fixed"] = tv_fixed
            out["tool_fr"] = tool_fr
        verdict = response_verdict(resp)
        if verdict is not None:
            out["e2e"] = verdict == truth
            out["e2e_reason"] = ("verdict_stated_ok" if out["e2e"]
                                 else "verdict_stated_wrong")
            return out
        return _grade_empty_or_censored(out, row, resp, cap, "no_verdict_stated")

    if task == "solve":
        # A response at the snapshot cap may hold a cut-off plan; even a
        # prefix that validates is not the model's full answer -> censored.
        if resp.strip() and cap is not None and len(resp) == cap:
            out["e2e"] = "indeterminate"
            out["e2e_reason"] = "censored_at_snapshot_cap"
            return out
        parsed = _safe_pydantic_validate(SolveResponse, resp)
        plan_lines = parsed.plan if parsed else extract_plan_lines(resp)
        if plan_lines:
            verdict = await ctx.validate(row["domain_name"],
                                         row["problem_name"], plan_lines)
            if verdict is None:
                out["e2e"] = "indeterminate"
                out["e2e_reason"] = "plan_validation_transport_error"
            else:
                out["e2e"] = verdict
                out["e2e_reason"] = "plan_valid" if verdict else "plan_invalid"
            return out
        return _grade_empty_or_censored(out, row, resp, cap, "no_plan_extracted")

    if task == "simulate":
        oracle = oracle_canon_for(gt_cache, row)
        if oracle is None:
            out["e2e"] = "indeterminate"
            out["e2e_reason"] = "no_ground_truth"
            return out
        steps, _compliant = _coerce_simulate_trajectory(resp)
        if steps:
            model_canon = _normalize_trajectory(steps)
            if model_canon is None:
                return _grade_empty_or_censored(out, row, resp, cap,
                                                "format_parse_fail")
            out["e2e"] = model_canon == oracle
            out["e2e_reason"] = ("trajectory_ok" if out["e2e"]
                                 else "trajectory_mismatch")
            return out
        if steps is not None:  # coerced cleanly to an empty trajectory
            out["e2e"] = False
            out["e2e_reason"] = "simulate_empty"
            return out
        return _grade_empty_or_censored(out, row, resp, cap, "format_parse_fail")

    out["e2e"] = "indeterminate"
    out["e2e_reason"] = "unknown_task"
    return out


class SolveContext:
    """Live-MCP plan validation with an in-memory dedupe cache."""

    def __init__(self, mcp, domains: dict | None):
        self.mcp = mcp
        self.domains = domains or {}
        self.cache: dict[tuple, bool | None] = {}
        self.calls = 0

    async def validate(self, dname: str, pname: str,
                       plan_lines: list[str]) -> bool | None:
        if self.mcp is None:
            return None
        dinfo = self.domains.get(dname)
        ppddl = (dinfo or {}).get("problems", {}).get(pname)
        if not dinfo or not ppddl:
            return None
        key = (dname, pname, tuple(plan_lines))
        if key not in self.cache:
            self.calls += 1
            self.cache[key] = await _validate_model_plan(
                self.mcp, dinfo["domain"], ppddl, plan_lines)
        return self.cache[key]


async def process_corpus(corpus_dir: Path, out_root: Path, gt_cache: dict,
                         ctx: SolveContext) -> list[dict]:
    rows_out = []
    # trials*.jsonl: the frontier probe corpora use suffixed names
    # (e.g. trials_rest52.jsonl); group per cell dir.
    by_cell: dict[Path, list[Path]] = defaultdict(list)
    for trials in sorted(corpus_dir.glob("*/trials*.jsonl")):
        by_cell[trials.parent].append(trials)
    for cell_dir, files in sorted(by_cell.items()):
        cell = cell_dir.name
        cell_rows = []
        max_len = 0
        for trials in files:
            for ln in trials.open():
                try:
                    row = json.loads(ln).get("result", {})
                except json.JSONDecodeError:
                    continue  # pre-2026-05-28 corpora may carry torn lines
                if row.get("task") not in ALL_TASKS:
                    continue
                max_len = max(max_len, len(row.get("response") or ""))
                cell_rows.append(row)
        if not cell_rows:
            continue
        cap = detect_cap(max_len)
        out_path = out_root / corpus_dir.name / f"{cell}.e2e.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as fh:
            for row in cell_rows:
                graded = await regrade_row(row, cap, gt_cache, ctx)
                graded["e2e_strict"] = (
                    False if graded["e2e_reason"] == "delegation_terminal_credit"
                    else graded["e2e"])
                graded["cell"] = cell
                graded["snapshot_cap"] = cap
                fh.write(json.dumps(graded) + "\n")
                rows_out.append(graded)
    return rows_out


def summarize(rows: list[dict], corpus_name: str) -> None:
    groups = defaultdict(list)
    for r in rows:
        arm = "tools" if r["with_tools"] else "no-tools"
        groups[(r["model"], r["task"], arm)].append(r)

    # Upper bounds are derivable: <rule>-high = <rule>-low + censored.
    print(f"\n{'=' * 108}\n{corpus_name}: end-to-end vs tool-verified\n{'=' * 108}")
    hdr = (f"{'model':34s} {'task':17s} {'arm':9s} {'n':>5s} "
           f"{'tool-ver':>8s} {'strict-lo':>9s} {'B-lo':>7s} {'censored':>8s} "
           f"{'deleg':>6s}")
    print(hdr)
    for (model, task, arm), rs in sorted(groups.items()):
        n = len(rs)
        tv = sum(1 for r in rs if r["tool_verified"]) / n if arm == "tools" else None
        strict = sum(1 for r in rs if r["e2e_strict"] is True) / n
        low = sum(1 for r in rs if r["e2e"] is True) / n
        ind = sum(1 for r in rs if r["e2e"] == "indeterminate") / n
        deleg = sum(1 for r in rs
                    if r["e2e_reason"] == "delegation_terminal_credit") / n
        print(f"{model:34s} {task:17s} {arm:9s} {n:5d} "
              f"{('%8.1f' % (100 * tv)) if tv is not None else '       -'} "
              f"{100 * strict:8.1f} {100 * low:7.1f} {100 * ind:8.1f} "
              f"{100 * deleg:6.1f}")


def phase3_report(rows: list[dict], corpus_name: str) -> None:
    """Stored vs recomputed tool-verified (validate_*), and failure rebinning."""
    print(f"\n{corpus_name}: phase-3 tool-verified recompute (validate_*)")
    for task in VALIDATE_TASKS:
        vs = [r for r in rows
              if r["task"] == task and r["with_tools"] and "tool_fr" in r]
        if not vs:
            continue
        flips = sum(1 for r in vs if bool(r["tool_verified"]) != r["tool_verified_fixed"])
        frc = defaultdict(int)
        for r in vs:
            if not r["tool_verified_fixed"]:
                frc[r["tool_fr"]] += 1
        dist = ", ".join(f"{k}={v}" for k, v in sorted(frc.items(), key=lambda kv: -kv[1]))
        print(f"  {task:17s} n={len(vs):6d} success flips={flips}  "
              f"failure bins: {dist}")


async def amain() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("corpora", nargs="*",
                    default=["results/sweep5v2-live", "results/sweep6-live"],
                    help="corpus directories containing <cell>/trials.jsonl")
    ap.add_argument("--out", default="results/derived/e2e_overlay",
                    help="root for the derived overlay files")
    ap.add_argument("--gt-cache", default="results/derived/gt_cache.json",
                    help="oracle cache from tools/build_gt_cache.py")
    ap.add_argument("--marketplace-path", default="../pddl-copilot",
                    help="plugins root for live solve-plan validation")
    ap.add_argument("--no-mcp", action="store_true",
                    help="skip live MCP; solve plans grade as indeterminate")
    args = ap.parse_args()

    gt_path = Path(args.gt_cache)
    gt_cache = json.loads(gt_path.read_text()) if gt_path.exists() else {}
    if not gt_cache:
        print(f"warning: no gt cache at {gt_path}; simulate rows will be "
              "indeterminate (no_ground_truth)", file=sys.stderr)

    mcp = None
    domains = None
    if not args.no_mcp:
        from run_experiment import resolve_plugin_dirs
        from pddl_eval.chat import MCPPlanner
        from pddl_eval.domains import load_domains
        domains = load_domains(Path("domains"))
        mcp = MCPPlanner()
        await mcp.connect(resolve_plugin_dirs(args.marketplace_path))
    ctx = SolveContext(mcp, domains)

    try:
        out_root = Path(args.out)
        for corpus in args.corpora:
            corpus_dir = Path(corpus)
            if not corpus_dir.is_dir():
                print(f"skip (not a dir): {corpus}", file=sys.stderr)
                continue
            rows = await process_corpus(corpus_dir, out_root, gt_cache, ctx)
            if rows:
                summarize(rows, corpus_dir.name)
                phase3_report(rows, corpus_dir.name)
            else:
                print(f"skip (no gradeable rows): {corpus}", file=sys.stderr)
        if ctx.calls:
            print(f"\n[solve] live plan validations: {ctx.calls} "
                  f"(deduped from cache size {len(ctx.cache)})")
    finally:
        if mcp is not None:
            await mcp.close()


if __name__ == "__main__":
    asyncio.run(amain())
