#!/usr/bin/env python3
"""KCL VAL cross-check of the answer key (action plan C1).

The harness grades every PDDL artefact with pyval (`pddl-pyvalidator` on
`unified-planning`), reached through the pddl-validator MCP plugin, which is
the same validator the model is given as a tool. This script runs an outside
checker, KCL VAL, on the same inputs and writes one CSV row per item:

  fixture_domain   every domain.pddl / domain_neg.pddl     VAL parse + type check
  fixture_problem  every pNN.pddl / nNN.pddl               VAL parse + type check
  fixture_plan     every pNN_vK.plan / pNN_bK.plan         VAL plan validation
  solve_plan       every distinct (domain, problem, plan) a solve grader of the
                   rerun validated: the plan the delivered grader extracted from
                   a final answer (tools/delivered_rerun/grade.solve_plan), and
                   every plan the online grader validated (pddl_eval.scoring.
                   check_success: a planner tool's plan on the with-tools arm,
                   the parsed answer on the no-tools arm)

Plans are written to VAL exactly as the harness hands them to pyval
(`"\\n".join(plan_lines)`; fixture plan files as stored). Domain and problem
files are the fixture files the harness reads.

VAL verdicts
  plan   "Plan valid" -> valid; "Plan invalid" / "Plan failed to execute" /
         "Goal not satisfied" / "Bad plan description!" / a plan type-check
         error -> invalid; VAL rejecting the domain or problem, or dying
         without a verdict -> cannot_handle (reported apart, never counted as
         agreement or disagreement).
  parse  `validate DOMAIN PROBLEM` with no plan file. A domain is checked with
         the domain's first valid problem (pNN.pddl), a problem with
         domain.pddl. Any VAL error message -> invalid; no message and exit 0
         -> valid; a crash with no message -> cannot_handle.

Harness verdicts
  fixtures      the slot label (domain / pNN / _vK valid; domain_neg / nNN /
                _bK invalid), which `generate_ground_truth` asserts equal to
                pyval at every sweep start.
  solve_plan    the stored delivered verdict (--plan-verdicts, the live-oracle
                cache the delivered secondary analysis wrote) when the plan is
                in it; otherwise the live pyval verdict (--marketplace-path).
  With --marketplace-path the script also re-runs pyval on every item through
  the harness's own call path (MCPPlanner -> validator plugin), so the CSV
  carries label, stored and live pyval side by side.

Row level (with --rows-csv): every solve trial row is regraded by the
harness's own `check_success` (plus the runner's truncation relabel) twice,
once with live pyval and once with VAL as the validator (a stub MCP that
answers `validate_plan` from the verdict tables); the pyval regrade must
reproduce the stored online `success` exactly. The delivered grade of each
row is recomputed with VAL in place of pyval.

    python tools/val_crosscheck.py --val /path/to/validate \\
        [--val-prefix "arch -x86_64"] --domains-dir domains \\
        [--rerun-root results/delivered-rerun] \\
        [--plan-verdicts results/delivered-rerun-secondary/plan_verdicts.json] \\
        [--marketplace-path ../pddl-copilot] \\
        --out-csv OUT/val_items.csv [--rows-csv OUT/val_rows.csv] [--jobs 8]

Read-only over results and fixtures.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from pddl_eval.chat import _parse_validation_verdict, _safe_json_loads  # noqa: E402
from pddl_eval.scoring import (  # noqa: E402
    _apply_truncation_override,
    check_success,
    strip_leaked_channel_prefix,
)
from tools.delivered_rerun.grade import solve_plan  # noqa: E402

VALID, INVALID, CANNOT = "valid", "invalid", "cannot_handle"

# ----------------------------------------------------------------- VAL output
_DP_MARKERS = (
    ("Problem in domain definition!", "domain_syntax_error"),
    ("Type problem in domain description!", "domain_type_error"),
    ("Type problem in problem specification!", "problem_type_error"),
    ("Parser failed to read file!", "parser_failed"),
    ("Error in type-checking!", "type_check_error"),
)


def _crashed(rc: int) -> bool:
    return rc < 0 or rc >= 128


def classify_parse(rc: int, out: str) -> tuple[str, str, str]:
    """(verdict, status, detail) of `validate DOMAIN PROBLEM` without a plan."""
    for marker, status in _DP_MARKERS:
        if marker in out:
            return INVALID, status, _first_error_line(out) or marker
    err = _first_error_line(out)
    if err:
        return INVALID, "error", err
    if _crashed(rc):
        return CANNOT, f"crash_rc{rc}", "VAL crashed with no message"
    if rc != 0:
        return INVALID, f"rc{rc}", _tail(out)
    return VALID, "accepted", ""


def classify_plan(rc: int, out: str) -> tuple[str, str, str, int | None]:
    """(verdict, status, detail, VAL's plan size) of `validate -v D P PLAN`."""
    lines = [ln.rstrip() for ln in out.splitlines()]
    size = None
    m = re.search(r"^Plan size:\s*(\d+)", out, re.M)
    if m:
        size = int(m.group(1))
    if "Checking plan:" not in out:
        # No plan verdict: VAL rejected the domain or problem, or died. A crash
        # loses VAL's buffered stdout, so "Checking plan:" may be missing even
        # when VAL got as far as the plan.
        for marker, status in _DP_MARKERS:
            if marker in out:
                return CANNOT, "rejected_" + status, _first_error_line(out) or marker, size
        if _crashed(rc):
            return CANNOT, f"crash_rc{rc}", "VAL crashed with no verdict", size
        return CANNOT, f"no_plan_check_rc{rc}", _tail(out), size
    after = out.split("Checking plan:", 1)[1]
    if re.search(r"^Plan valid\s*$", after, re.M):
        return VALID, "plan_valid", "", size
    if "Bad plan description!" in after:
        return INVALID, "bad_plan_description", "", size
    if "Plan failed to execute" in after:
        detail = ""
        for i, ln in enumerate(lines):
            if ln.startswith("Plan failed because of unsatisfied precondition in:"):
                detail = "unsatisfied precondition in " + (lines[i + 1].strip() if i + 1 < len(lines) else "")
                break
        if not detail:
            detail = next((ln.strip() for ln in lines if "fail" in ln.lower()
                           and "Plan failed to execute" not in ln), "")
        return INVALID, "failed_to_execute", detail, size
    if "Goal not satisfied" in after:
        return INVALID, "goal_not_satisfied", "", size
    if re.search(r"^Plan invalid\s*$", after, re.M):
        return INVALID, "plan_invalid_other", _tail(out), size
    if "Error in type-checking!" in after:
        obj = re.search(r"Object with unknown type:\s*(\S+)", after)
        return (INVALID, "plan_type_error",
                f"unknown object {obj.group(1)}" if obj else "type-check error in a plan step", size)
    if _crashed(rc):
        return CANNOT, f"crash_rc{rc}", "VAL crashed with no verdict", size
    return CANNOT, f"no_verdict_rc{rc}", _tail(out), size


def _first_error_line(out: str) -> str:
    for ln in out.splitlines():
        if "Error" in ln or "error" in ln:
            return re.sub(r"^\S*/", "", ln.strip())[:200]
    return ""


def _tail(out: str, n: int = 160) -> str:
    return " ".join(out.split())[-n:]


@dataclass
class ValRunner:
    val: Path
    prefix: list[str]
    timeout: float

    def run(self, args: list[Path | str]) -> tuple[int, str]:
        cmd = self.prefix + [str(self.val)] + [str(a) for a in args]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout,
                               errors="replace")
        except subprocess.TimeoutExpired:
            return -999, "TIMEOUT"
        return p.returncode, p.stdout + p.stderr

    def version_banner(self) -> str:
        rc, out = self.run(["-h"])
        return " ".join(out.split("Usage:")[0].split())


# ----------------------------------------------------------------- items
@dataclass
class Item:
    kind: str
    track: str
    domain: str
    problem: str
    name: str                   # file name, or plan hash for solve plans
    label: str                  # harness verdict: valid / invalid
    label_source: str
    domain_file: Path
    problem_file: Path | None
    plan_text: str | None = None
    plan_file: Path | None = None
    n_plan_lines: int | None = None
    sources: Counter = field(default_factory=Counter)
    pyval_live: str = ""
    pyval_status: str = ""
    val_verdict: str = ""
    val_status: str = ""
    val_detail: str = ""
    val_plan_size: int | None = None
    shape: str = ""


def plan_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def file_shape(path: Path, kind: str) -> str:
    """Objective notes for the hand read of a parse-check item: parenthesis
    balance (comments removed) and, for a problem, any missing section."""
    text = re.sub(r";[^\n]*", "", path.read_text())
    notes = []
    bal = text.count("(") - text.count(")")
    if bal < 0:
        notes.append(f"{-bal} extra ')'")
    elif bal > 0:
        notes.append(f"{bal} unclosed '('")
    if kind == "fixture_problem":
        for sec in (":objects", ":init", ":goal"):
            if not re.search(r"\(\s*" + re.escape(sec) + r"\b", text, re.I):
                notes.append(f"no ({sec} section")
    return "; ".join(notes)


def fixture_items(domains_dir: Path) -> list[Item]:
    items: list[Item] = []
    for track in ("classical", "numeric"):
        tdir = domains_dir / track
        if not tdir.is_dir():
            continue
        for ddir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            dom = ddir / "domain.pddl"
            if not dom.exists():
                continue
            probs = sorted(ddir.glob("p[0-9]*.pddl"))
            if not probs:
                continue
            first_problem = probs[0]
            items.append(Item("fixture_domain", track, ddir.name, "", "domain.pddl", VALID,
                              "slot label", dom, first_problem))
            neg = ddir / "domain_neg.pddl"
            if neg.exists():
                items.append(Item("fixture_domain", track, ddir.name, "", "domain_neg.pddl",
                                  INVALID, "slot label", neg, first_problem))
            for pf in probs:
                items.append(Item("fixture_problem", track, ddir.name, pf.stem, pf.name, VALID,
                                  "slot label", dom, pf))
            for nf in sorted(ddir.glob("n[0-9]*.pddl")):
                items.append(Item("fixture_problem", track, ddir.name, nf.stem, nf.name,
                                  INVALID, "slot label", dom, nf))
            for pf in probs:
                for lab, pat in ((VALID, "_v[0-9]*.plan"), (INVALID, "_b[0-9]*.plan")):
                    for plf in sorted(ddir.glob(pf.stem + pat)):
                        text = plf.read_text()
                        n = sum(1 for ln in text.splitlines() if ln.strip().startswith("("))
                        items.append(Item("fixture_plan", track, ddir.name, pf.stem, plf.name,
                                          lab, "slot label", dom, pf, plan_text=text,
                                          plan_file=plf, n_plan_lines=n))
    return items


# ----------------------------------------------------------------- rerun rows
def load_rows(rerun_root: Path) -> tuple[list[dict], Counter]:
    """Every solve row of every cell under rerun_root (tolerant JSONL reader)."""
    rows: list[dict] = []
    stats: Counter = Counter()
    for cell in sorted(p for p in rerun_root.iterdir() if p.is_dir()):
        tj = cell / "trials.jsonl"
        if not tj.exists():
            continue
        with tj.open(errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    stats["torn_lines"] += 1
                    continue
                r = obj.get("result", obj)
                stats["rows"] += 1
                if r.get("task") != "solve":
                    continue
                r = dict(r)
                r["_cell"] = cell.name
                rows.append(r)
                stats["solve_rows"] += 1
    return rows, stats


class _RecordingMCP:
    """Stub MCP for `check_success`: records every validate_plan request and
    answers from a verdict function. Returning a non-valid verdict while
    recording makes the with-tools loop visit every planner plan."""

    def __init__(self, verdict_fn):
        self.verdict_fn = verdict_fn
        self.requests: list[str] = []

    async def call_tool(self, name: str, arguments: dict) -> str:
        if name != "validate_plan":
            raise ValueError(f"unexpected tool {name}")
        plan = arguments["plan"]
        self.requests.append(plan)
        v = self.verdict_fn(plan)
        if v is None:
            return json.dumps({"error": True, "message": "no verdict"})
        return json.dumps({"valid": bool(v), "status": "VALID" if v else "INVALID"})


def regrade_online(row: dict, domain_text: str, problem_text: str, verdict_fn):
    """Run the harness's check_success on one stored solve row with a stub
    validator, then the runner's truncation relabel (a failed row cut by the
    token cap is stored as truncated_no_answer). Returns
    ((ok, failure_reason), plans requested)."""
    stub = _RecordingMCP(verdict_fn)
    _sel, ok, fr = asyncio.run(check_success(
        "solve", row.get("response") or "", row.get("tool_calls") or [], {}, stub,
        domain_text, problem_text, bool(row.get("with_tools"))))
    fr = _apply_truncation_override(ok, bool(row.get("truncated")), fr)
    return (ok, fr), stub.requests


def delivered_plan(row: dict) -> tuple[str, ...]:
    """The plan the delivered grader reads (tools/delivered_rerun/grade.py):
    nothing for an exception row or an empty final answer."""
    if row.get("failure_reason") == "exception":
        return ()
    resp = row.get("response") or ""
    if not strip_leaked_channel_prefix(resp).strip():
        return ()
    plan, _mode = solve_plan(resp)
    return tuple(plan)


# ----------------------------------------------------------------- pyval live
async def _pyval_live(items: list[Item], marketplace: Path) -> None:
    from pddl_eval.chat import MCPPlanner
    from pddl_eval.domains import _validate_capture
    plugin = marketplace / "plugins" / "pddl-validator"
    if not plugin.is_dir():
        raise SystemExit(f"--marketplace-path: {plugin} not found")
    mcp = MCPPlanner()
    await mcp.connect([plugin])
    texts: dict[Path, str] = {}

    def text(p: Path) -> str:
        if p not in texts:
            texts[p] = p.read_text()
        return texts[p]
    try:
        for i, it in enumerate(items, 1):
            if it.kind == "fixture_domain":
                raw, v = await _validate_capture(mcp, {"domain": text(it.domain_file)})
            elif it.kind == "fixture_problem":
                raw, v = await _validate_capture(mcp, {"domain": text(it.domain_file),
                                                       "problem": text(it.problem_file)})
            elif it.kind == "fixture_plan":
                raw, v = await _validate_capture(mcp, {"domain": text(it.domain_file),
                                                       "problem": text(it.problem_file),
                                                       "plan": it.plan_text})
            else:
                # solve_plan: the call `scoring._validate_model_plan` makes for a
                # non-empty plan (same arguments, same verdict parser), done
                # inline so the raw status is kept as well.
                raw = await mcp.call_tool("validate_plan", {
                    "domain": text(it.domain_file), "problem": text(it.problem_file),
                    "plan": it.plan_text})
                v = _parse_validation_verdict(raw)
            data = _safe_json_loads(raw)
            it.pyval_live = {True: VALID, False: INVALID, None: "error"}[v]
            it.pyval_status = data.get("status", "") if isinstance(data, dict) else ""
            if i % 250 == 0:
                print(f"  pyval live: {i}/{len(items)}", file=sys.stderr)
    finally:
        await mcp.close()


# ----------------------------------------------------------------- stats
def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (100 * (centre - half), 100 * (centre + half))


def agreement(items: list[Item]) -> dict:
    handled = [it for it in items if it.val_verdict in (VALID, INVALID)]
    k = sum(it.val_verdict == it.label for it in handled)
    lo, hi = wilson(k, len(handled))
    return {"n_items": len(items), "n_handled": len(handled), "agree": k,
            "pct": (100 * k / len(handled)) if handled else float("nan"),
            "wilson95": [lo, hi],
            "cannot_handle": len(items) - len(handled)}


# ----------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--val", type=Path, required=True, help="VAL `validate` binary")
    ap.add_argument("--val-prefix", default="", help='runner prefix, e.g. "arch -x86_64"')
    ap.add_argument("--domains-dir", type=Path, required=True)
    ap.add_argument("--rerun-root", type=Path, help="cells with trials.jsonl (solve plans)")
    ap.add_argument("--plan-verdicts", type=Path,
                    help="stored delivered verdicts [{domain, problem, plan, valid}]")
    ap.add_argument("--marketplace-path", type=Path,
                    help="pddl-copilot checkout: re-run pyval live through the plugin")
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--rows-csv", type=Path, help="row-level regrade CSV (needs --rerun-root)")
    ap.add_argument("--summary-json", type=Path)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args(argv)

    runner = ValRunner(args.val, shlex.split(args.val_prefix), args.timeout)
    banner = runner.version_banner()
    print(f"VAL: {banner}", file=sys.stderr)
    val_sha = hashlib.sha256(args.val.read_bytes()).hexdigest()

    items = fixture_items(args.domains_dir)
    track_of = {it.domain: it.track for it in items}
    dfile = {it.domain: it.domain_file for it in items if it.name == "domain.pddl"}
    pfile = {(it.domain, it.problem): it.problem_file for it in items
             if it.kind == "fixture_problem" and it.label == VALID}

    rows: list[dict] = []
    load_stats: Counter = Counter()
    stored: dict[tuple, bool] = {}
    if args.plan_verdicts:
        for e in json.loads(args.plan_verdicts.read_text()):
            stored[(e["domain"], e["problem"], tuple(e["plan"]))] = e["valid"]

    tmp = tempfile.TemporaryDirectory(prefix="val_crosscheck_")
    tmpdir = Path(tmp.name)
    solve: dict[tuple, Item] = {}
    row_plans: list[tuple[dict, tuple, list[str]]] = []

    def solve_item(dname: str, pname: str, plan_lines: tuple, source: str) -> Item:
        text = "\n".join(plan_lines)
        key = (dname, pname, text)
        if key not in solve:
            h = plan_hash(f"{dname}/{pname}\n{text}")
            pf = tmpdir / f"{h}.plan"
            pf.write_text(text)
            solve[key] = Item("solve_plan", track_of[dname], dname, pname, h, "", "",
                              dfile[dname], pfile[(dname, pname)], plan_text=text,
                              plan_file=pf, n_plan_lines=len(plan_lines))
        solve[key].sources[source] += 1
        return solve[key]

    if args.rerun_root:
        rows, load_stats = load_rows(args.rerun_root)
        for r in rows:
            dname, pname = r["domain_name"], r["problem_name"]
            dtext, ptext = dfile[dname].read_text(), pfile[(dname, pname)].read_text()
            # every plan the online grader validates (recording pass)
            _, requested = regrade_online(r, dtext, ptext, lambda _p: False)
            src = "online_tool" if r.get("with_tools") else "online_notools"
            for ptxt in dict.fromkeys(requested):
                solve_item(dname, pname, tuple(ptxt.split("\n")), src)
            dp = delivered_plan(r)
            if dp:
                solve_item(dname, pname, dp,
                           "delivered_tools_arm" if r.get("with_tools") else "delivered_notools_arm")
            row_plans.append((r, dp, requested))
        print(f"rerun: {load_stats['solve_rows']} solve rows, {len(solve)} distinct plans, "
              f"torn lines {load_stats['torn_lines']}", file=sys.stderr)
        for (dname, pname, text), it in solve.items():
            key = (dname, pname, tuple(text.split("\n")))
            if key in stored:
                it.label = VALID if stored[key] else INVALID
                it.label_source = "stored delivered verdict (plan_verdicts.json)"
        if stored:
            delivered_keys = {(d, p, tuple(t.split("\n"))) for (d, p, t), it in solve.items()
                              if it.sources["delivered_tools_arm"] or it.sources["delivered_notools_arm"]}
            load_stats["delivered_plans"] = len(delivered_keys)
            load_stats["delivered_plans_in_store"] = len(delivered_keys & set(stored))
            load_stats["store_entries"] = len(stored)

    all_items = items + list(solve.values())

    if args.marketplace_path:
        os.environ.setdefault("PDDL_TEMP_DIR", str(tmpdir / "pyval"))
        print(f"pyval live on {len(all_items)} items ...", file=sys.stderr)
        asyncio.run(_pyval_live(all_items, args.marketplace_path))
    for it in all_items:
        if not it.label:
            if it.pyval_live in (VALID, INVALID):
                it.label, it.label_source = it.pyval_live, "live pyval"
            else:
                it.label, it.label_source = "unknown", "none"

    def run_val(it: Item) -> None:
        if it.kind in ("fixture_domain", "fixture_problem"):
            rc, out = runner.run([it.domain_file, it.problem_file])
            it.shape = file_shape(it.domain_file if it.kind == "fixture_domain"
                                  else it.problem_file, it.kind)
            it.val_verdict, it.val_status, it.val_detail = classify_parse(rc, out)
        else:
            rc, out = runner.run(["-v", it.domain_file, it.problem_file, it.plan_file])
            it.val_verdict, it.val_status, it.val_detail, it.val_plan_size = classify_plan(rc, out)

    print(f"VAL on {len(all_items)} items ...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        list(ex.map(run_val, all_items))

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = ["kind", "track", "domain", "problem", "item", "harness_verdict", "harness_source",
            "pyval_live", "pyval_status", "val_verdict", "val_status", "val_detail",
            "agree", "file_shape", "n_plan_lines", "val_plan_size", "rows_online_tool",
            "rows_online_notools", "rows_delivered_tools_arm", "rows_delivered_notools_arm",
            "plan"]
    with args.out_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for it in all_items:
            agree = ("" if it.val_verdict == CANNOT or it.label not in (VALID, INVALID)
                     else int(it.val_verdict == it.label))
            w.writerow([it.kind, it.track, it.domain, it.problem, it.name, it.label,
                        it.label_source, it.pyval_live, it.pyval_status, it.val_verdict,
                        it.val_status, it.val_detail, agree, it.shape, it.n_plan_lines,
                        "" if it.val_plan_size is None else it.val_plan_size,
                        it.sources["online_tool"], it.sources["online_notools"],
                        it.sources["delivered_tools_arm"], it.sources["delivered_notools_arm"],
                        " | ".join(it.plan_text.split("\n")) if it.kind == "solve_plan" else ""])

    summary: dict = {"val_banner": banner, "val_sha256": val_sha, "load": dict(load_stats),
                     "agreement": {}, "rows": {}}
    groups: dict[str, list[Item]] = defaultdict(list)
    for it in all_items:
        groups[it.kind].append(it)
        groups[f"{it.kind}/{it.track}"].append(it)
        groups[f"{it.kind}/{it.track}/label_{it.label}"].append(it)
        groups[f"all/{it.track}"].append(it)
        groups["all"].append(it)
        family = "plans" if it.kind in ("fixture_plan", "solve_plan") else "parse"
        groups[family].append(it)
        groups[f"{family}/{it.track}"].append(it)
        if it.kind == "solve_plan":
            for s in it.sources:
                groups[f"solve_plan/source_{s}"].append(it)
    for g, its in sorted(groups.items()):
        summary["agreement"][g] = agreement(its)
    pv = [it for it in all_items if it.pyval_live and it.label_source != "live pyval"]
    summary["pyval_live_vs_harness"] = {
        "n": len(pv), "agree": sum(it.pyval_live == it.label for it in pv),
        "mismatch": [f"{it.kind}:{it.domain}/{it.problem}/{it.name}" for it in pv
                     if it.pyval_live != it.label]}
    summary["plan_size_mismatch"] = [
        f"{it.kind}:{it.domain}/{it.problem}/{it.name} lines={it.n_plan_lines} val={it.val_plan_size}"
        for it in all_items if it.val_plan_size is not None and it.n_plan_lines is not None
        and it.val_plan_size != it.n_plan_lines]

    if args.rows_csv and rows:
        byplan = {(d, p, t): it for (d, p, t), it in solve.items()}

        def vfn(dname, pname, field_):
            def f(text):
                it = byplan.get((dname, pname, text))
                if it is None:
                    return None
                v = getattr(it, field_)
                return {VALID: True, INVALID: False}.get(v)
            return f
        rc: Counter = Counter()
        with args.rows_csv.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["cell", "model", "with_tools", "domain", "problem", "variant",
                        "stored_success", "stored_failure_reason", "pyval_regrade_success",
                        "pyval_regrade_reason", "val_regrade_success", "val_regrade_reason",
                        "val_cannot_handle", "online_plans", "delivered_plan_item",
                        "delivered_harness", "delivered_val"])
            for r, dp, requested in row_plans:
                dname, pname = r["domain_name"], r["problem_name"]
                dtext, ptext = dfile[dname].read_text(), pfile[(dname, pname)].read_text()
                ok_py, fr_py = "", ""
                if args.marketplace_path:
                    (ok_py, fr_py), _ = regrade_online(r, dtext, ptext,
                                                       vfn(dname, pname, "pyval_live"))
                (ok_val, fr_val), _ = regrade_online(r, dtext, ptext,
                                                     vfn(dname, pname, "val_verdict"))
                online = list(dict.fromkeys(requested))
                cannot = any(byplan[(dname, pname, t)].val_verdict == CANNOT for t in online)
                dit = byplan.get((dname, pname, "\n".join(dp))) if dp else None
                w.writerow([r["_cell"], r.get("model"), r.get("with_tools"), dname, pname,
                            r.get("prompt_variant"), r.get("success"), r.get("failure_reason"),
                            ok_py, fr_py, ok_val, fr_val, int(cannot), len(online),
                            dit.name if dit else "", dit.label if dit else "",
                            dit.val_verdict if dit else ""])
                arm = "tools" if r.get("with_tools") else "notools"
                rc[f"{arm}/rows"] += 1
                if online:
                    rc[f"{arm}/online_graded_rows"] += 1
                    if args.marketplace_path:
                        rc[f"{arm}/pyval_regrade_success_equals_stored"] += ok_py == r.get("success")
                        rc[f"{arm}/pyval_regrade_reason_equals_stored"] += fr_py == r.get("failure_reason")
                    if cannot:
                        rc[f"{arm}/online_rows_val_cannot_handle"] += 1
                    else:
                        rc[f"{arm}/online_rows_val_handled"] += 1
                        rc[f"{arm}/val_regrade_success_equals_stored"] += ok_val == r.get("success")
                if dit is not None:
                    rc[f"{arm}/delivered_rows_with_plan"] += 1
                    if dit.val_verdict in (VALID, INVALID):
                        rc[f"{arm}/delivered_rows_val_handled"] += 1
                        rc[f"{arm}/delivered_rows_agree"] += dit.val_verdict == dit.label
        summary["rows"] = dict(rc)

    if args.summary_json:
        args.summary_json.write_text(json.dumps(summary, indent=1, default=str) + "\n")
    for g in ("plans", "fixture_plan", "solve_plan", "parse", "fixture_domain",
              "fixture_problem"):
        a = summary["agreement"].get(g)
        if a:
            print(f"{g:16s} agree {a['agree']}/{a['n_handled']} ({a['pct']:.1f}%, "
                  f"Wilson95 {a['wilson95'][0]:.1f}-{a['wilson95'][1]:.1f}); "
                  f"VAL cannot handle {a['cannot_handle']}", file=sys.stderr)
    tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
