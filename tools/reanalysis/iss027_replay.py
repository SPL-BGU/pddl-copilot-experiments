#!/usr/bin/env python3
"""ISS-027 on the open-model tool arms: replay the stored simulate and validate_plan
tool calls with the plan lower-cased (read-only, post hoc).

    .venv/bin/python tools/reanalysis/iss027_replay.py --results /abs/results \
        --marketplace-path ../pddl-copilot \
        [--corpora sweep5v2-live delivered-rerun sweep6-live iss024d-e2e-live]
    .venv/bin/python tools/reanalysis/iss027_replay.py --render-only

What is replayed. Models often copy the fixture plan with the fixture's own capitals
into `get_state_transition` (simulate) or `validate_plan` (validate_plan); the tool
answers STRUCTURE_ERROR ("not declared"). For every tool-cell row of those two tasks
in which some call of the task's tool passes a plan with a capital letter (any
problem, any corpus), every call of that tool is sent again to the plugin's FastMCP
server in process, once with the arguments as stored and once with the plan
lower-cased. The harness rule (`pddl_eval.scoring.check_success`: any call whose
verdict equals the answer key, or whose trajectory equals the oracle's) is applied
to both sets of results. A stored failure that passes in lower case is a flip.
Only the tool answer changes in a replay, not the rest of the conversation, so the
tool-verified (mechanism) grade can be corrected this way and the delivered answer
cannot. The other tasks are counted (stored grade only) for the contrasts of the
NUMBERS.md block.

Rows not replayed. A row with no capital letter in any plan argument cannot change
under case folding, so it is not replayed. Among those are 8 calls on the affected
fixtures whose `domain`, `problem` (and sometimes `plan`) are file paths on the
cluster (`/home/omereliy/plans/plan_<id>.solution`, written by the solver's
`save_plan`); replayed here they would fail with "does not look like PDDL content or
a file path", because the file exists only on the cluster. They are outside the
replayed set, so they need no exception.

Self-checks (exit 2 on failure):
- pddl-pyvalidator is 0.1.5 and the sibling's validator server has no local edits
  (the sibling commit and the package versions are written into the outputs);
- every replayed call with the stored arguments returns the stored result (after
  the per-request temporary directory is masked, `iss027_common.norm_result`),
  except the known cases in KNOWN_DIFFERENCES, each matched by its trial key and
  call index, each checked to leave the call's verdict unchanged;
- on every replayed row, the harness rule on the as-is results equals the stored
  `success`.

Writes tools/reanalysis/out/iss027_replay.{json,md} and, when out/iss027_unaided.json
exists, the NUMBERS.md block files. `--render-only` rewrites only the block files from
the two committed JSON outputs (no results data, no validator).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import iss027_common as C  # noqa: E402

CORPORA = ("sweep5v2-live", "delivered-rerun", "sweep6-live", "iss024d-e2e-live")

# Calls whose as-is replay does not return the stored text, found 2026-11-09 and
# read by hand. Key: (corpus, cell, trial key as a tuple, call index among the
# task-tool calls of the row) -> why. Each must still return the stored result in
# every field except the free-text `report` (so the same verdict), and the stored
# result is the one graded.
KNOWN_DIFFERENCES: dict[tuple, str] = {
    ("sweep5v2-live", "slurm_vllm_Qwen3_5_4B_off_tools_all_minimal",
     ("Qwen/Qwen3.5-4B", "validate_plan", "satellite", "p03", "b3", 16, True, "off", "all", "minimal"), 4):
        "the model sent a domain with a malformed precondition; both answers are "
        "`valid: false, status: SYNTAX_ERROR`, but the parser error in `report` is worded "
        "differently (the local unified-planning wraps it as `UPTypeError(...)` and adds the "
        "line and column), so the parser version on the cluster was not the local one",
}


def same_but_report(a, b) -> bool:
    """Both results are JSON objects equal in every field except `report`."""
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return False
    return {k: v for k, v in a.items() if k != "report"} == {k: v for k, v in b.items() if k != "report"}


class Halt(Exception):
    pass


def harness_pass(task: str, results: list[str], truth, oracle) -> bool:
    """The with-tools branch of `check_success` for validate_plan and simulate."""
    from pddl_eval.scoring import _normalize_trajectory, _parse_validation_verdict, _safe_json_loads
    if task == "validate_plan":
        return truth is not None and any(_parse_validation_verdict(x) == truth for x in results)
    if oracle is None:
        return False
    for x in results:
        pj = _safe_json_loads(x)
        if isinstance(pj, dict) and not pj.get("error") and _normalize_trajectory(pj.get("trajectory")) == oracle:
            return True
    return False


async def run(args) -> dict:
    from tools.e2e_regrade import oracle_canon_for, truth_for

    env = C.environment(args.marketplace_path)
    bad = C.check_environment(env)
    if bad:
        raise Halt("; ".join(bad))
    vs = C.load_validator(args.marketplace_path)
    gt = {False: json.loads((args.results / "derived" / "gt_cache.json").read_text()),
          True: json.loads((args.results / "derived" / "gt_cache_anon.json").read_text())}

    cells, flips, diffs, problems = [], [], [], []
    calls = Counter()
    seen_known = set()
    for corpus in args.corpora:
        for cdir in sorted((args.results / corpus).iterdir()):
            meta = C.parse_cell(cdir.name)
            if not meta["tools"] or not (cdir / "trials.jsonl").exists():
                continue
            rows, torn = C.load_rows(cdir / "trials.jsonl")
            st = defaultdict(Counter)
            for k, r in rows.items():
                task = r["task"]
                if r.get("infra_failure"):
                    continue
                arm = C.arm_of(r)
                s = st[(task, arm)]
                s["n"] += 1
                s["k"] += bool(r["success"])
                s["called"] += bool(r.get("tool_selected"))
                if task not in C.TASK_TOOL:  # stored counts only; plans of other tasks are not replayed
                    continue
                tname = C.TASK_TOOL[task]
                tcs = [tc for tc in (r.get("tool_calls") or []) if tc.get("name") == tname]
                if not any(isinstance(tc.get("arguments"), dict) and C.has_upper(tc["arguments"].get("plan", ""))
                           for tc in tcs):
                    continue
                s["replayed_rows"] += 1
                asis, low = [], []
                for i, tc in enumerate(tcs):
                    a = tc.get("arguments") if isinstance(tc.get("arguments"), dict) else {}
                    stored = tc.get("result", "")
                    got = await C.call_tool(vs, tname, a)
                    calls["replayed"] += 1
                    known = (corpus, cdir.name, k, i)
                    if C.norm_result(got) == C.norm_result(stored):
                        calls["equal_to_stored"] += 1
                        asis.append(got)
                    elif known in KNOWN_DIFFERENCES and same_but_report(C.norm_result(got), C.norm_result(stored)):
                        seen_known.add(known)
                        calls["known_difference"] += 1
                        diffs.append(dict(corpus=corpus, cell=cdir.name, key=list(k), call=i,
                                          why=KNOWN_DIFFERENCES[known], stored=C._REQ_DIR.sub("<req>/", stored)[:600],
                                          replay=C._REQ_DIR.sub("<req>/", got)[:600]))
                        asis.append(stored)  # the stored answer is what the grader saw
                    else:
                        problems.append(f"{corpus}/{cdir.name} {list(k)} call {i}: replay differs from "
                                        f"the stored result\n    stored: {stored[:300]!r}\n    replay: {got[:300]!r}")
                        asis.append(got)
                        continue
                    if C.has_upper(a.get("plan", "")) and known not in KNOWN_DIFFERENCES:
                        low.append(await C.call_tool(vs, tname, {**a, "plan": C.lower_plan(a["plan"])}))
                        calls["replayed_lower_case"] += 1
                    else:
                        low.append(asis[-1])
                anon = C.is_anon(corpus)
                truth = truth_for(r) if task == "validate_plan" else None
                oracle = oracle_canon_for(gt[anon], r) if task == "simulate" else None
                pa, pl = harness_pass(task, asis, truth, oracle), harness_pass(task, low, truth, oracle)
                if pa != bool(r["success"]):
                    problems.append(f"{corpus}/{cdir.name} {list(k)}: harness rule on the as-is replay "
                                    f"gives {pa}, stored success {r['success']}")
                if pl != pa:
                    s["flips_up" if pl else "flips_down"] += 1
                    flips.append(dict(corpus=corpus, cell=cdir.name, key=list(k), task=task, arm=arm,
                                      direction="fail -> pass" if pl else "pass -> fail",
                                      affected=C.affected(r["domain_name"], r["problem_name"]),
                                      failure_reason=r.get("failure_reason")))
            for (task, arm), s in sorted(st.items()):
                cells.append(dict(corpus=corpus, cell=cdir.name, **meta, task=task, arm=arm, torn=torn, **dict(s)))
    missing = set(KNOWN_DIFFERENCES) - seen_known
    if missing:
        problems.append(f"known differences not met: {sorted(missing)}")
    if problems:
        raise Halt(f"{len(problems)} problem(s):\n  " + "\n  ".join(problems[:20]))
    return dict(env=env, corpora=list(args.corpora), cells=cells, flips=flips, known_differences=diffs,
                calls=dict(calls),
                self_check=dict(calls_replayed=calls["replayed"], calls_equal=calls["equal_to_stored"],
                                calls_known_difference=calls["known_difference"],
                                rows_replayed=sum(c.get("replayed_rows", 0) for c in cells),
                                environment="pass"))


def render_md(js: dict) -> str:
    env, sc = js["env"], js["self_check"]
    L = ["# ISS-027: tool calls replayed with the plan lower-cased (post hoc)", "",
         f"*Generated by `tools/reanalysis/iss027_replay.py`; do not edit, rerun the script.* "
         f"pddl-pyvalidator {env['pyval']}, unified-planning {env['unified_planning']}, mcp {env['mcp']}; "
         f"sibling `../pddl-copilot` at `{env['marketplace_head'][:10]}` (validator server last changed in "
         f"`{env['validator_server_last_commit'][:10]}`, no local edits). Self-check: {sc['calls_equal']:,} of "
         f"{sc['calls_replayed']:,} calls replayed with the stored arguments return the stored result"
         + (f", {sc['calls_known_difference']} known difference(s) listed below" if sc["calls_known_difference"] else "")
         + f"; on all {sc['rows_replayed']} replayed rows the harness rule on the replay equals the stored "
         "`success`.", "",
         "Rows replayed = rows in which some call of the task's tool passed a plan with a capital letter. "
         "Rates are tool-verified success over all rows of the cell and arm.", "",
         "| corpus | cell | task | arm | n | called | stored | replayed rows | flips | after |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for c in js["cells"]:
        if not c.get("replayed_rows"):
            continue
        up, down = c.get("flips_up", 0), c.get("flips_down", 0)
        L.append(f"| {c['corpus']} | {c['model']} {c['think']} {c['style']} | {c['task']} | {c['arm']} | {c['n']} | "
                 f"{c['called']} | {100 * c['k'] / c['n']:.1f} ({c['k']}) | {c['replayed_rows']} | +{up}"
                 + (f" / −{down}" if down else "") + f" | {100 * (c['k'] + up - down) / c['n']:.1f} |")
    if js["known_differences"]:
        L += ["", "## Known differences between the stored result and the as-is replay", ""]
        L += [f"- {d['corpus']} `{d['cell']}` {d['key'][2]} {d['key'][3]} {d['key'][4]} v{d['key'][5]}, "
              f"call {d['call']}: {d['why']}" for d in js["known_differences"]]
    L += ["", "## Every flip", ""]
    L += [f"- {f['corpus']} `{f['cell']}` {f['task']} {f['arm']}: {f['key'][2]} {f['key'][3]} {f['key'][4]} "
          f"v{f['key'][5]}, {f['direction']} (stored `{f['failure_reason']}`)"
          + ("" if f["affected"] else " **not an affected fixture**") for f in js["flips"]]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, help="results root (read-only)")
    ap.add_argument("--marketplace-path", type=Path, help="the sibling ../pddl-copilot")
    ap.add_argument("--corpora", nargs="+", default=list(CORPORA))
    ap.add_argument("--out-dir", type=Path, default=C.OUT)
    ap.add_argument("--render-only", action="store_true",
                    help="rewrite the NUMBERS.md block files from the committed JSON outputs")
    args = ap.parse_args(argv)
    if not args.render_only:
        if args.results is None or args.marketplace_path is None:
            ap.error("--results and --marketplace-path are required unless --render-only is given")
        try:
            js = asyncio.run(run(args))
        except Halt as e:
            print(f"HALT: {e}", file=sys.stderr)
            return 2
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "iss027_replay.json").write_text(json.dumps(js, indent=1) + "\n")
        (args.out_dir / "iss027_replay.md").write_text(render_md(js))
        sc = js["self_check"]
        print(f"self-check: {sc['calls_equal']} of {sc['calls_replayed']} calls equal the stored result "
              f"({sc['calls_known_difference']} known difference(s)); {sc['rows_replayed']} rows replayed",
              file=sys.stderr)
    if (args.out_dir / "iss027_unaided.json").exists():
        for f in C.write_numbers_files(args.out_dir):
            print(f"wrote {f}", file=sys.stderr)
    elif args.render_only:
        print("out/iss027_unaided.json is missing", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
