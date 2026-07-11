#!/usr/bin/env python3
"""End-to-end (response-graded) overlay regrade — Phase 1: validate_*.

Implements the decisions recorded in
development/tool_call_vs_final_output_grading.md (2026-07-11):
  D1/D2  end-to-end success = grade the MODEL'S final response with the same
         parser the no-tools branch uses, both arms; the stored tool-graded
         success is kept alongside as "tool-verified".
  D2b=B  a bare tool call counts as the model's answer only when the model
         closed the turn on its own (done_reason == "stop", empty response,
         tool-verified). Truncated-empty (done_reason == "length") fails,
         symmetric with no-tools truncation.
  D6=A   corpora written under the 500-char response snapshot cap
         (pre-2026-06-25, runner.py RESPONSE_SNAPSHOT_LEN) are censored: a
         non-empty snapshot exactly at the cap with no parseable verdict is
         INDETERMINATE, and rates are reported as [lower, upper] bounds.

Phase-1 scope is validate_{domain,problem,plan}: ground truth is encoded in
the fixture naming (verified against runner.py job emission):
  validate_domain   problem_name == "domain_neg"      -> INVALID else VALID
  validate_problem  problem_name matches n\\d\\d       -> INVALID else VALID
  validate_plan     plan_label b* -> INVALID, v* -> VALID
solve/simulate need the MCP-generated oracle (plan validity / trace) and land
in Phase 2 via a materialized gt cache.

The overlay is DERIVED data: canonical trials.jsonl files are never touched.
Output mirrors <corpus>/<cell>/trials.jsonl as
results/derived/e2e_overlay/<corpus>/<cell>.e2e.jsonl, one row per input
trial, plus a per-corpus summary printed to stdout.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval.schemas import ValidateResponse  # noqa: E402
from pddl_eval.scoring import _safe_pydantic_validate, extract_verdict  # noqa: E402

VALIDATE_TASKS = ("validate_domain", "validate_problem", "validate_plan")
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


def regrade_row(row: dict, cap: int | None) -> dict:
    """Return the overlay verdict for one trial row.

    e2e is one of True / False / "indeterminate" (censored).
    """
    out = {
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

    if not row["with_tools"]:
        # No-tools grading already ran online on the full response text; the
        # stored success IS the end-to-end verdict. (Offline re-parse would
        # only re-introduce the snapshot censoring.)
        out["e2e"] = row["success"]
        out["e2e_reason"] = "stored_online_grade"
        return out

    truth = truth_for(row)
    if truth is None:
        out["e2e"] = "indeterminate"
        out["e2e_reason"] = "no_ground_truth"
        return out

    resp = row.get("response") or ""
    verdict = response_verdict(resp)
    if verdict is not None:
        out["e2e"] = verdict == truth
        out["e2e_reason"] = "verdict_stated_ok" if out["e2e"] else "verdict_stated_wrong"
        return out

    if not resp.strip():
        if row.get("done_reason") == "stop" and row["success"] is True:
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
    out["e2e_reason"] = "no_verdict_stated"
    return out


def process_corpus(corpus_dir: Path, out_root: Path) -> list[dict]:
    rows_out = []
    for trials in sorted(corpus_dir.glob("*/trials.jsonl")):
        cell = trials.parent.name
        cell_rows = []
        max_len = 0
        for ln in trials.open():
            try:
                row = json.loads(ln).get("result", {})
            except json.JSONDecodeError:
                continue  # pre-2026-05-28 corpora may carry torn lines
            if row.get("task") not in VALIDATE_TASKS:
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
                graded = regrade_row(row, cap)
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

    print(f"\n{'=' * 100}\n{corpus_name}: end-to-end vs tool-verified (validate_*)\n{'=' * 100}")
    hdr = (f"{'model':34s} {'task':17s} {'arm':9s} {'n':>5s} "
           f"{'tool-ver':>8s} {'e2e-low':>8s} {'e2e-high':>8s} {'censored':>8s}")
    print(hdr)
    for (model, task, arm), rs in sorted(groups.items()):
        n = len(rs)
        tv = sum(1 for r in rs if r["tool_verified"]) / n if arm == "tools" else None
        low = sum(1 for r in rs if r["e2e"] is True) / n
        ind = sum(1 for r in rs if r["e2e"] == "indeterminate") / n
        print(f"{model:34s} {task:17s} {arm:9s} {n:5d} "
              f"{('%8.1f' % (100 * tv)) if tv is not None else '       -'} "
              f"{100 * low:7.1f} {100 * (low + ind):8.1f} {100 * ind:8.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("corpora", nargs="*",
                    default=["results/sweep5v2-live", "results/sweep6-live"],
                    help="corpus directories containing <cell>/trials.jsonl")
    ap.add_argument("--out", default="results/derived/e2e_overlay",
                    help="root for the derived overlay files")
    args = ap.parse_args()

    out_root = Path(args.out)
    for corpus in args.corpora:
        corpus_dir = Path(corpus)
        if not corpus_dir.is_dir():
            print(f"skip (not a dir): {corpus}", file=sys.stderr)
            continue
        rows = process_corpus(corpus_dir, out_root)
        if rows:
            summarize(rows, corpus_dir.name)
        else:
            print(f"skip (no validate_* rows): {corpus}", file=sys.stderr)


if __name__ == "__main__":
    main()
