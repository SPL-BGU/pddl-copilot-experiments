#!/usr/bin/env python3
"""ISS-027 on the open-model solve answers graded from text: unaided solve re-graded
with the plan lower-cased (read-only, post hoc).

    .venv/bin/python tools/reanalysis/iss027_unaided.py --results /abs/results \
        --marketplace-path ../pddl-copilot [--corpora sweep5v2-live sweep6-live delivered-rerun]

What is graded. Every unaided (no-tools cell) solve row, on every problem, the way
`pddl_eval.scoring.check_success` graded it online: the SolveResponse JSON plan,
else the text extractor (`extract_plan_lines`, which lower-cases every line, so only
JSON answers can keep the model's capitals), sent to the plugin's `validate_plan`.
A failed row whose plan holds a capital letter is sent again in lower case; when
that passes, the row flips. For the delivered rerun the same is done with the
delivered grader's extractor (`tools/delivered_rerun/grade.solve_plan`) on the
Part C rows and on the tool-arm solve answers (the rerun's E1/E2 surface).

Answers cut at the snapshot cap. The online grader saw the full answer, the corpus
holds only its first characters (`iss027_common.SNAPSHOT_CAP`, per corpus), so such
a row cannot be re-graded. It can flip only when all of these hold, and it then
counts toward the upper end of a range: the stored grade failed with
`failure_reason == "plan_invalid"` (the grader validated a plan and pyval rejected
it; `format_parse_fail` means there was no plan to validate, and
`truncated_no_answer` means the model ran out of output tokens, so its JSON never
closed and the plan, if any, came from the text extractor, already lower case); the
visible answer starts as JSON; and a plan entry in it writes a declared name with a
capital. The figure is then "low to high": low = the re-graded flips, high = low +
these rows.

Self-checks (exit 2 on failure): pddl-pyvalidator is 0.1.5 and the sibling's
validator server has no local edits; the fixture scan finds the capitals exactly in
the files `iss027_common.expected_upper_files` names, and none in `domains-anon/`;
the re-grade with the as-is plan equals the stored `success` on every row that is
not at the cap. The sibling commit and the package versions are written into the
outputs.

Writes tools/reanalysis/out/iss027_unaided.{json,md}, then the NUMBERS.md block
files (`iss027_common.write_numbers_files`) when out/iss027_replay.json exists.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import iss027_common as C  # noqa: E402

CORPORA = ("sweep5v2-live", "sweep6-live", "delivered-rerun")
ENTRY = re.compile(r'"\(?([A-Za-z][^"]*)\)?"')


class Halt(Exception):
    pass


def at_cap_candidate(row: dict, declared: set[str]) -> bool:
    """A failed row cut at the cap that the case fault could have failed (rule in
    the module docstring)."""
    from pddl_eval.scoring import strip_leaked_channel_prefix
    if row["success"] or row.get("failure_reason") != "plan_invalid":
        return False
    vis = strip_leaked_channel_prefix(row.get("response") or "").lstrip()
    if not (vis.startswith("{") or vis.startswith("```json")):
        return False
    return C.writes_capitals(ENTRY.findall(vis), declared)


async def run(args) -> dict:
    from pddl_eval.schemas import SolveResponse
    from pddl_eval.scoring import _parse_validation_verdict, _safe_pydantic_validate, extract_plan_lines
    from tools.delivered_rerun.grade import solve_plan as delivered_solve_plan

    env = C.environment(args.marketplace_path)
    bad = C.check_environment(env)
    scan = {t: C.upper_case_fixtures(C.REPO / t) for t in ("domains", "domains-anon")}
    if set(scan["domains"]) != C.expected_upper_files():
        bad.append(f"fixtures with capitals: {sorted(scan['domains'])}")
    if scan["domains-anon"]:
        bad.append(f"domains-anon has capitals: {sorted(scan['domains-anon'])}")
    if bad:
        raise Halt("; ".join(bad))
    vs = C.load_validator(args.marketplace_path)
    cache: dict = {}

    async def pyval(dt, pt, lines) -> bool | None:
        """The harness's `_validate_model_plan`: False for no plan, else the verdict."""
        lines = tuple(lines)
        if not lines:
            return False
        if (dt, pt, lines) not in cache:
            raw = await C.call_tool(vs, "validate_plan",
                                    {"domain": dt, "problem": pt, "plan": "\n".join(lines)})
            cache[(dt, pt, lines)] = _parse_validation_verdict(raw)
        return cache[(dt, pt, lines)]

    cells, flips, mismatch = [], [], []
    torn = {}
    for corpus in args.corpora:
        tree = C.REPO / ("domains-anon" if C.is_anon(corpus) else "domains")
        fx = C.fixture_texts(tree)
        for cdir in sorted((args.results / corpus).iterdir()):
            if not (cdir / "trials.jsonl").exists():
                continue
            meta = C.parse_cell(cdir.name)
            if meta["tools"] and corpus != "delivered-rerun":
                continue
            rows, torn[f"{corpus}/{cdir.name}"] = C.load_rows(cdir / "trials.jsonl")
            st = defaultdict(Counter)
            for k, r in rows.items():
                if r.get("infra_failure") or (r["task"] != "solve" and meta["tools"]):
                    continue
                arm = C.arm_of(r)
                s = st[(r["task"], arm)]
                if r["task"] != "solve":  # stored counts only (the T5 contrasts need them)
                    s["n"] += 1
                    s["k_stored"] += bool(r["success"])
                    continue
                d, p = r["domain_name"], r["problem_name"]
                dt, pt = fx(d, p)
                declared = C.declared_lower(dt, pt)
                resp = r.get("response") or ""
                s["n"] += 1
                s["n_affected"] += C.affected(d, p)
                surfaces = []
                if not meta["tools"]:
                    s["k_stored"] += bool(r["success"])
                    if C.at_cap(r, corpus):
                        s["at_cap"] += 1
                        if at_cap_candidate(r, declared):
                            s["at_cap_candidates"] += 1
                            flips.append(dict(corpus=corpus, cell=cdir.name, key=list(k), surface="online",
                                              kind="at-cap candidate", affected=C.affected(d, p)))
                    else:
                        parsed = _safe_pydantic_validate(SolveResponse, resp)
                        lines = parsed.plan if parsed else extract_plan_lines(resp)
                        v = await pyval(dt, pt, lines)
                        s["regraded"] += 1
                        if (v is True) != bool(r["success"]):
                            mismatch.append(f"{corpus}/{cdir.name} {list(k)}: regrade {v}, stored {r['success']}")
                        else:
                            s["regrade_equals_stored"] += 1
                        surfaces.append(("online", lines, bool(r["success"])))
                if corpus == "delivered-rerun":
                    lines, _mode = delivered_solve_plan(resp)
                    v = await pyval(dt, pt, lines)
                    s["delivered_k"] += v is True
                    surfaces.append(("delivered", list(lines), v is True))
                for surface, lines, ok in surfaces:
                    if ok or not any(C.has_upper(x) for x in lines):
                        continue
                    s[f"{surface}_failed_with_capitals"] += 1
                    if await pyval(dt, pt, [x.lower() for x in lines]) is True:
                        s[f"{surface}_flips"] += 1
                        s[f"{surface}_flips_affected"] += C.affected(d, p)
                        flips.append(dict(corpus=corpus, cell=cdir.name, key=list(k), surface=surface,
                                          kind="flip", affected=C.affected(d, p),
                                          failure_reason=r.get("failure_reason")))
            for (task, arm), s in sorted(st.items()):
                cells.append(dict(corpus=corpus, cell=cdir.name, **meta, task=task, arm=arm, **dict(s)))
    if mismatch:
        raise Halt(f"re-grade differs from the stored grade on {len(mismatch)} rows:\n  "
                   + "\n  ".join(mismatch[:20]))
    n_regraded = sum(c.get("regraded", 0) for c in cells)
    return dict(env=env, corpora=list(args.corpora), fixture_scan=scan, torn_lines=torn,
                cells=cells, flips=flips,
                self_check=dict(regraded_rows=n_regraded, regrade_equals_stored=n_regraded,
                                fixture_scan="pass", environment="pass"))


def rate(k, n):
    return f"{100 * k / n:.1f}" if n else "–"


def render_md(js: dict) -> str:
    env = js["env"]
    L = ["# ISS-027: unaided solve re-graded with the plan lower-cased (post hoc)", "",
         f"*Generated by `tools/reanalysis/iss027_unaided.py`; do not edit, rerun the script.* "
         f"pddl-pyvalidator {env['pyval']}, unified-planning {env['unified_planning']}; sibling "
         f"`../pddl-copilot` at `{env['marketplace_head'][:10]}` (validator server last changed in "
         f"`{env['validator_server_last_commit'][:10]}`, no local edits). Self-check: the re-grade with "
         f"the plan as written equals the stored `success` on all {js['self_check']['regraded_rows']:,} "
         "rows not cut at the snapshot cap; the fixture scan finds capitals only in satellite p02-p05 "
         "and pogo_stick, none in `domains-anon/`.", "",
         "Range = low to high: low counts the re-graded rows that pass in lower case; high adds the "
         "failed rows cut at the snapshot cap whose stored reason is `plan_invalid` and whose visible "
         "answer is JSON writing a declared name with a capital (rule in the script).", "",
         "## Unaided solve, harness online grade", "",
         "| corpus | model | think | n | stored | at cap | re-graded | failed with capitals | flips (low) | "
         "at-cap candidates | after, low–high |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in js["cells"]:
        if c["tools"] or c["task"] != "solve":
            continue
        lo, hi = c.get("online_flips", 0), c.get("online_flips", 0) + c.get("at_cap_candidates", 0)
        after = rate(c["k_stored"] + lo, c["n"]) + ("" if lo == hi else "–" + rate(c["k_stored"] + hi, c["n"]))
        L.append(f"| {c['corpus']} | {c['model']} | {c['think']} | {c['n']} | {rate(c['k_stored'], c['n'])} "
                 f"({c['k_stored']}) | {c.get('at_cap', 0)} | {c.get('regraded', 0)} | "
                 f"{c.get('online_failed_with_capitals', 0)} | +{lo} | {hi - lo} | {after} |")
    L += ["", "## Delivered rerun, delivered grade (`tools/delivered_rerun/grade.solve_plan`)", "",
          "| cell | arm | n | of which on affected problems | delivered pass | failed with capitals | flips |",
          "|---|---|---|---|---|---|---|"]
    for c in js["cells"]:
        if c["corpus"] == "delivered-rerun" and c["task"] == "solve":
            L.append(f"| {c['cell']} | {c['arm']} | {c['n']} | {c['n_affected']} | {c.get('delivered_k', 0)} | "
                     f"{c.get('delivered_failed_with_capitals', 0)} | +{c.get('delivered_flips', 0)} |")
    L += ["", "## Every flip and at-cap candidate", ""]
    L += [f"- {f['corpus']} `{f['cell']}` {f['surface']} {f['kind']}: {f['key'][2]} {f['key'][3]} "
          f"v{f['key'][5]}" + (f" (stored `{f['failure_reason']}`)" if f.get("failure_reason") else "")
          + ("" if f["affected"] else " **not an affected fixture**") for f in js["flips"]]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, required=True, help="results root (read-only)")
    ap.add_argument("--marketplace-path", type=Path, required=True, help="the sibling ../pddl-copilot")
    ap.add_argument("--corpora", nargs="+", default=list(CORPORA))
    ap.add_argument("--out-dir", type=Path, default=C.OUT)
    args = ap.parse_args(argv)
    try:
        js = asyncio.run(run(args))
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "iss027_unaided.json").write_text(json.dumps(js, indent=1) + "\n")
    (args.out_dir / "iss027_unaided.md").write_text(render_md(js))
    print(f"self-check: {js['self_check']['regraded_rows']} re-graded rows equal the stored grade; "
          f"wrote {args.out_dir}/iss027_unaided.{{json,md}}", file=sys.stderr)
    if (args.out_dir / "iss027_replay.json").exists():
        for f in C.write_numbers_files(args.out_dir):
            print(f"wrote {f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
