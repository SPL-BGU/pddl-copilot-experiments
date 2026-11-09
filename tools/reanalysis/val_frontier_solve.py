#!/usr/bin/env python3
"""KCL VAL on the Claude (frontier) solve plans: the C1 method
(tools/val_crosscheck.py, development/reference/val_crosscheck.md) applied to
every graded Sonnet 4.6 and Haiku 4.5 solve plan.

Cells (thinking off; the two budget-probe cells hold no solve rows):
  Sonnet 4.6  sonnet-frontier/sweep5v2            unaided, canonical  (v11-13)
              sonnet-frontier/sweep6              unaided, renamed    (v11-13)
              sonnet-frontier/sweep5v2-with-tools tool arm, canonical (v11)
  Haiku 4.5   haiku-frontier/sweep5v2             unaided, canonical  (v11)
              haiku-frontier/sweep6               unaided, renamed    (v11)
              haiku-frontier/sweep5v2-with-tools  tool arm, canonical (v11)
              haiku-frontier/sweep6-with-tools    tool arm, renamed   (v11)
Renamed (sweep6*) rows are checked against domains-anon/, the rest against
domains/ (the overlay's D7b rule, tools/e2e_regrade.is_anon).

"Graded solve plan" = every plan a solve grader validated:
  online     every plan `pddl_eval.scoring.check_success` sends to the
             validator, recorded with a stub (the C1 `regrade_online`): the
             planner tool's plans on the tool arm, the parsed answer unaided.
  delivered  tool arm only: the plan the overlay grader extracts from the
             final answer (`tools/e2e_regrade`: SolveResponse JSON, else
             `extract_plan_lines_tolerant`). Unaided rows are graded once: the
             overlay reuses the stored online grade, so the online plan is
             the delivered plan.
An unaided answer stored at the 16,384-char snapshot cap cannot be rebuilt
(the online grader saw the full text); its row is counted apart.

Harness verdict per plan = live pyval through the harness's own path (C1:
`MCPPlanner` -> pddl-validator plugin). It is checked against what is
stored before it is used: the pyval regrade of every row must reproduce the
stored `success`, and the pyval verdict of every delivered plan must equal the
overlay's `e2e_strict` on the rows it came from. pyval answering with an
error shape (the harness's `tool_error`, graded a failure) is counted apart.

VAL = the C1 binary (PlanBench's macOS x86_64 build, sha256 44a07d6d...) run
under Rosetta (`--val-prefix "arch -x86_64"`), the same `validate -v` call and
the same verdict classes (`val_crosscheck.classify_plan`). Then each row is
regraded with VAL in pyval's place.

Run (from the repo root; needs the VAL binary and ../pddl-copilot):
  .venv/bin/python tools/reanalysis/val_frontier_solve.py \
     --val /path/to/validate --val-prefix "arch -x86_64" \
     --marketplace-path ../pddl-copilot [--results DIR] [--out-dir DIR]
Writes the items and rows CSVs plus a summary JSON to --out-dir (default
results/val-crosscheck-frontier, gitignored), and
tools/reanalysis/out/val_frontier_solve.md + numbers_val_frontier_solve.md.

  .venv/bin/python tools/reanalysis/val_frontier_solve.py --render-only
rewrites only out/numbers_val_frontier_solve.md, from the committed
out/val_frontier_solve.json and the post hoc table of out/val_frontier_solve.md
(no VAL binary, no pyval, no results data).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import importlib.util
import json
import os
import re
import shlex
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools import val_crosscheck as vc  # noqa: E402
from tools.e2e_regrade import (  # noqa: E402
    SolveResponse,
    _safe_pydantic_validate,
    extract_plan_lines_tolerant,
)

OUT = Path(__file__).resolve().parent / "out"
CELLS = [  # (model label, corpus dir, cell, arm, corpus)
    ("Sonnet 4.6", "sonnet-frontier", "sweep5v2", "unaided", "canonical"),
    ("Sonnet 4.6", "sonnet-frontier", "sweep6", "unaided", "renamed"),
    ("Sonnet 4.6", "sonnet-frontier", "sweep5v2-with-tools", "tool arm", "canonical"),
    ("Haiku 4.5", "haiku-frontier", "sweep5v2", "unaided", "canonical"),
    ("Haiku 4.5", "haiku-frontier", "sweep6", "unaided", "renamed"),
    ("Haiku 4.5", "haiku-frontier", "sweep5v2-with-tools", "tool arm", "canonical"),
    ("Haiku 4.5", "haiku-frontier", "sweep6-with-tools", "tool arm", "renamed"),
]
SNAPSHOT_CAP = 16384
V, I, CANNOT = vc.VALID, vc.INVALID, vc.CANNOT
ACTION_LINE = re.compile(r"^\s*[A-Za-z][\w-]*(\s+[\w\-?@.]+)*\s*$")  # "pick_up b1", no brackets


_ACTS: dict[Path, set[str]] = {}


def actions_of(domain_file: Path) -> set[str]:
    """Action names a domain declares, lower case."""
    if domain_file not in _ACTS:
        _ACTS[domain_file] = {m.lower() for m in re.findall(r"\(:action\s+([^\s()]+)",
                                                             domain_file.read_text(), re.I)}
    return _ACTS[domain_file]


def tree_for(corpus: str) -> Path:
    return REPO / ("domains-anon" if corpus == "renamed" else "domains")


def delivered_plan(resp: str) -> tuple[str, ...]:
    """The overlay grader's extraction (tools/e2e_regrade.regrade_row, solve)."""
    if not resp.strip() or len(resp) == SNAPSHOT_CAP:
        return ()
    parsed = _safe_pydantic_validate(SolveResponse, resp)
    lines = parsed.plan if parsed else extract_plan_lines_tolerant(resp)[0]
    return tuple(lines)


def _eq04():
    spec = importlib.util.spec_from_file_location("eq04", Path(__file__).with_name("04_equivalence.py"))
    eq04 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eq04)
    return eq04


CONTAM_ROW = re.compile(
    r"^\| (Sonnet 4\.6|Haiku 4\.5) unaided solve, (stored grade|VAL grade) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| "
    r"([+-][\d.]+) \| \[([+-][\d.]+), ([+-][\d.]+)\] \| (\w+) \(k=\d+\) \|.*\| ([^|]+) \|$")


def render_only() -> list[str]:
    """Rebuild out/numbers_val_frontier_solve.md from the committed outputs
    (out/val_frontier_solve.json for the counts, the post hoc table of
    out/val_frontier_solve.md for the T7 results) without pyval or VAL."""
    js = json.loads((OUT / "val_frontier_solve.json").read_text())
    contam = {}
    for ln in (OUT / "val_frontier_solve.md").read_text().splitlines():
        m = CONTAM_ROW.match(ln)
        if m:
            verdict = m.group(10).strip()
            flag = re.search(r"\((.+): low information\)", verdict)
            contam[(m.group(1), m.group(2))] = dict(
                n=int(m.group(3)), ra=float(m.group(4)), rb=float(m.group(5)), est=float(m.group(6)),
                lo=float(m.group(7)), hi=float(m.group(8)), gov=m.group(9),
                met=verdict.startswith("criterion met"), flag=flag.group(1) if flag else "")
    if len(contam) != 4:
        raise SystemExit(f"post hoc table in out/val_frontier_solve.md: {len(contam)} of 4 rows found")
    return numbers_rows(js["items"], js["classes"], js["rows"], contam)


def numbers_rows(summ: dict, klasses: dict, rc: dict, contam: dict) -> list[str]:
    """The NUMBERS.md rows (out/numbers_val_frontier_solve.md) from the item
    summary, the plan classes, the row counters and the four post hoc T7 results."""
    rc = Counter(rc)
    eq04 = _eq04()

    def g(model, arm, corpus, key):
        return rc[f"{model} | {arm} | {corpus}/{key}"]
    al, tl, un = summ["all plans"], summ["arm: tool arm"], summ["arm: unaided"]
    fs = {m: g(m, "unaided", "canonical", "online_fail_to_success") for m in ("Sonnet 4.6", "Haiku 4.5")}
    sf = sum(rc[k] for k in rc if k.endswith("/online_success_to_fail"))
    fs_ren = sum(g(m, "unaided", "renamed", "online_fail_to_success") for m in ("Sonnet 4.6", "Haiku 4.5"))

    def cr(r):
        return (f"{r['ra']:.1f} → {r['rb']:.1f}, {r['est']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]"
                f"{'' if r['gov'] == 'domain' else ' (problem)'}, {eq04.label(r)}")
    N = ["| figure | value | source | do NOT quote |", "|---|---|---|---|",
         f"| Claude solve plans, VAL vs the harness verdict (pyval) | **{al['agree']:,} / {al['handled']:,} agree "
         f"({100 * al['agree'] / al['handled']:.2f}%, Wilson 95% [{al['lo']:.2f}, {al['hi']:.2f}])** over the "
         f"{al['n']:,} distinct graded plans of Sonnet 4.6 and Haiku 4.5 (unaided and tool arm, canonical and renamed). "
         f"Tool arm **{tl['agree']} / {tl['handled']}**; unaided {un['agree']} / {un['handled']}. "
         f"{klasses.get('agree, with brackets added', 0)} of the agreeing plans ({al['bracketed']} of all plans with "
         f"a verdict from both) were bare `name arg` lines that VAL reads only once brackets are added. "
         f"Not counted: {al['pyval_error']} answers with no plan in them (prose; pyval returns an error shape, graded a "
         f"failure) and {al['val_cannot']} plans that crash VAL (each has a step with the wrong number of arguments, read by hand: gripper `drop` with 3 of 4, barman `empty_shot` with 2 of 3; pyval rejects all of them) "
         f"| `val_frontier_solve.py`; `out/val_frontier_solve.md` | \"100% agreement\"; a figure that pools these with the "
         f"C1 open-model plans |",
         f"| the disagreements | **all {al['case']} are one pyval fault**: the fixture declares upper-case names "
         f"(satellite `Star0`, `GroundStation1`; pogo_stick `CRAFT_PLANK`), the model writes them exactly as declared, "
         f"and pyval rejects the plan as `STRUCTURE_ERROR` (\"not declared\"). The same plan in lower case is VALID "
         f"under pyval, and VAL accepts it as written (PDDL names are case-insensitive). Unaided, canonical corpus only: "
         f"the renamed tree has no upper-case names, and the planner's plans are lower case. Other disagreements: "
         f"{al['other']} | `val_frontier_solve.md` | the C1 hyphen case as the only grader fault (that one was lenient; "
         f"this one is strict) |",
         f"| unaided solve trials whose grade changes under VAL | stored fail → VAL success: **Sonnet 4.6 {fs['Sonnet 4.6']} "
         f"of 300, Haiku 4.5 {fs['Haiku 4.5']} of 100**, canonical; renamed {fs_ren}; success → fail: {sf}. Post hoc, "
         f"Sonnet unaided solve canonical becomes {contam[('Sonnet 4.6', 'VAL grade')]['ra']:.1f}% (stored "
         f"{contam[('Sonnet 4.6', 'stored grade')]['ra']:.1f}%) | `val_rows.csv` | a corrected figure in place of the "
         f"frozen ones |",
         f"| effect on the frontier contamination test, unaided solve (renamed − canonical, T7 method, post hoc) | "
         f"Sonnet 4.6: stored {cr(contam[('Sonnet 4.6', 'stored grade')])}; VAL grade "
         f"{cr(contam[('Sonnet 4.6', 'VAL grade')])}. Haiku 4.5 (v11 only): stored "
         f"{cr(contam[('Haiku 4.5', 'stored grade')])}; VAL grade {cr(contam[('Haiku 4.5', 'VAL grade')])}. The "
         f"case fault lowers only the canonical side, so it biases the contrast toward zero | `val_frontier_solve.md` | "
         f"the VAL-graded Δ as a replacement for the frozen −0.33 row (the grader change is post hoc) |"]
    return N


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--val", type=Path)
    ap.add_argument("--val-prefix", default="")
    ap.add_argument("--marketplace-path", type=Path)
    ap.add_argument("--results", type=Path, default=REPO / "results")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--render-only", action="store_true",
                    help="rewrite out/numbers_val_frontier_solve.md from the committed outputs; no pyval, no VAL")
    args = ap.parse_args(argv)
    if args.render_only:
        N = render_only()
        (OUT / "numbers_val_frontier_solve.md").write_text("\n".join(N) + "\n")
        print("\n".join(N))
        return 0
    if args.val is None or args.marketplace_path is None:
        ap.error("--val and --marketplace-path are required unless --render-only is given")
    out_dir = args.out_dir or (REPO / "results" / "val-crosscheck-frontier")

    runner = vc.ValRunner(args.val, shlex.split(args.val_prefix), 120.0)
    banner = runner.version_banner()
    val_sha = hashlib.sha256(args.val.read_bytes()).hexdigest()

    trees = {}
    for corpus in ("canonical", "renamed"):
        fx = vc.fixture_items(tree_for(corpus))
        trees[corpus] = dict(
            track={it.domain: it.track for it in fx},
            dfile={it.domain: it.domain_file for it in fx if it.name == "domain.pddl"},
            pfile={(it.domain, it.problem): it.problem_file for it in fx
                   if it.kind == "fixture_problem" and it.label == V})

    tmp = tempfile.TemporaryDirectory(prefix="val_frontier_")
    tmpdir = Path(tmp.name)
    items: dict[tuple, vc.Item] = {}
    item_corpus: dict[int, str] = {}
    rows = []  # (cell tuple, key, row, online plans, delivered plan, overlay row)
    stats = Counter()

    def item(corpus, d, p, lines, source):
        text = "\n".join(lines)
        k = (corpus, d, p, text)
        if k not in items:
            h = vc.plan_hash(f"{corpus}/{d}/{p}\n{text}")
            pf = tmpdir / f"{h}.plan"
            pf.write_text(text)
            t = trees[corpus]
            items[k] = vc.Item("solve_plan", t["track"][d], d, p, h, "", "", t["dfile"][d],
                               t["pfile"][(d, p)], plan_text=text, plan_file=pf,
                               n_plan_lines=len(lines))
            item_corpus[id(items[k])] = corpus
        items[k].sources[source] += 1
        return items[k]

    for cell in CELLS:
        model, cdir, cname, arm, corpus = cell
        keyed = {}  # tolerant reader; last row per key wins
        with (args.results / cdir / cname / "trials.jsonl").open(errors="replace") as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                try:
                    o = json.loads(ln)
                except json.JSONDecodeError:
                    stats["torn_lines"] += 1
                    continue
                keyed[tuple(o["key"])] = o["result"]
        ov = {}
        with (args.results / "derived" / "e2e_overlay" / cdir / f"{cname}.e2e.jsonl").open() as fh:
            for ln in fh:
                o = json.loads(ln)
                ov[tuple(o["trial_key"])] = o
        t = trees[corpus]
        for k, r in keyed.items():
            if r.get("task") != "solve" or r.get("infra_failure"):
                continue
            stats[f"rows/{cname}/{model}"] += 1
            d, p = r["domain_name"], r["problem_name"]
            resp = r.get("response") or ""
            at_cap = (not r.get("with_tools")) and len(resp) == SNAPSHOT_CAP
            dtext, ptext = t["dfile"][d].read_text(), t["pfile"][(d, p)].read_text()
            requested = []
            if not at_cap:
                _, requested = vc.regrade_online(r, dtext, ptext, lambda _p: False)
                src = "online_tool" if r.get("with_tools") else "online_notools"
                for ptxt in dict.fromkeys(requested):
                    item(corpus, d, p, tuple(ptxt.split("\n")), src)
            dp = delivered_plan(resp) if r.get("with_tools") else ()
            if dp:
                item(corpus, d, p, dp, "delivered_tools_arm")
            rows.append((cell, k, r, requested, dp, ov.get(k), at_cap))

    all_items = list(items.values())
    print(f"{len(rows)} solve rows, {len(all_items)} distinct plans", file=sys.stderr)

    # pyval live (the harness side), one MCP session per fixture tree is not
    # needed: every call carries the domain and problem text.
    os.environ.setdefault("PDDL_TEMP_DIR", str(tmpdir / "pyval"))
    asyncio.run(vc._pyval_live(all_items, args.marketplace_path))
    for it in all_items:
        it.label = it.pyval_live
        it.label_source = "live pyval"

    def run_val(it):
        rc, out = runner.run(["-v", it.domain_file, it.problem_file, it.plan_file])
        it.val_verdict, it.val_status, it.val_detail, it.val_plan_size = vc.classify_plan(rc, out)
        it.val_raw = (it.val_verdict, it.val_status, it.val_plan_size)
        it.read_as = "as sent"
        # No plan size: VAL rejected the plan description before counting steps
        # ("Bad plan description!", a plan type error): a real invalid verdict.
        if it.val_verdict == CANNOT or it.val_plan_size in (None, it.n_plan_lines):
            return
        # VAL read a different number of steps than were sent, so its verdict is
        # about another plan. Two causes: no plan at all (prose), or plan lines
        # without the brackets VAL's plan reader needs. The second is re-run
        # with each line put in brackets; the first VAL cannot read.
        lines = it.plan_text.split("\n")
        acts = actions_of(it.domain_file)
        if all(ACTION_LINE.match(x) and x.split()[0].lower() in acts for x in lines):
            pf = it.plan_file.with_suffix(".bracketed.plan")
            pf.write_text("\n".join(f"({x.strip()})" for x in lines))
            rc, out = runner.run(["-v", it.domain_file, it.problem_file, pf])
            it.val_verdict, it.val_status, it.val_detail, it.val_plan_size = vc.classify_plan(rc, out)
            it.read_as = "with brackets added"
            if it.val_plan_size in (None, it.n_plan_lines) or it.val_verdict == CANNOT:
                return
        it.val_verdict, it.val_status = CANNOT, "not_read_as_sent"
        it.read_as = "not read"
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        list(ex.map(run_val, all_items))

    # Case check: pyval rejects a name whose case differs from its own
    # (lower-cased) reading of the domain, while PDDL names are case-insensitive.
    # Every plan pyval rejects and VAL accepts is sent to pyval again in lower case.
    lowered = []
    for it in all_items:
        it.pyval_lower = ""
        if it.label == I and it.val_verdict == V:
            low = vc.Item("solve_plan", it.track, it.domain, it.problem, it.name + "-lower", "", "",
                          it.domain_file, it.problem_file, plan_text=it.plan_text.lower(),
                          n_plan_lines=it.n_plan_lines)
            low.parent = it
            lowered.append(low)
    if lowered:
        asyncio.run(vc._pyval_live(lowered, args.marketplace_path))
        for low in lowered:
            low.parent.pyval_lower = low.pyval_live

    def klass(it):
        if it.label not in (V, I):
            return "pyval error shape (" + ("prose, not a plan" if it.read_as == "not read" else "other") + ")"
        if it.val_verdict == CANNOT:
            return "VAL cannot handle (" + it.val_status + ")"
        if it.val_verdict == it.label:
            return "agree" + ("" if it.read_as == "as sent" else ", " + it.read_as)
        if it.label == I and it.pyval_lower == V:
            return "pyval rejects names written in the fixture's own upper case (valid in lower case)"
        return "other disagreement (read by hand)"
    for it in all_items:
        it.klass = klass(it)

    byplan = {k: it for k, it in items.items()}

    def vfn(corpus, d, p, field_):
        def f(text):
            it = byplan.get((corpus, d, p, text))
            if it is None:
                return None
            return {V: True, I: False}.get(getattr(it, field_))
        return f


    # ------------------------------------------------------------ row level
    rc = Counter()
    row_out = []
    regraded: dict[tuple, dict] = defaultdict(dict)
    stored_g: dict[tuple, dict] = defaultdict(dict)
    for cell, k, r, requested, dp, o, at_cap in rows:
        model, cdir, cname, arm, corpus = cell
        g = f"{model} | {arm} | {corpus}"
        t = trees[corpus]
        d, p = r["domain_name"], r["problem_name"]
        rc[f"{g}/rows"] += 1
        if at_cap:
            rc[f"{g}/rows_at_snapshot_cap"] += 1
            row_out.append([cname, model, arm, corpus, d, p, r.get("prompt_variant"), r["success"],
                            r["failure_reason"], "", "", "", "", "at_cap", 0, "", "", "", "", ""])
            regraded[(model, arm, corpus)][k] = {"success": bool(r["success"])}
            stored_g[(model, arm, corpus)][k] = {"success": bool(r["success"])}
            continue
        dtext, ptext = t["dfile"][d].read_text(), t["pfile"][(d, p)].read_text()
        (ok_py, fr_py), _ = vc.regrade_online(r, dtext, ptext, vfn(corpus, d, p, "pyval_live"))
        (ok_val, fr_val), _ = vc.regrade_online(r, dtext, ptext, vfn(corpus, d, p, "val_verdict"))
        online = list(dict.fromkeys(requested))
        oits = [byplan[(corpus, d, p, x)] for x in online]
        cannot = any(it.val_verdict == CANNOT for it in oits)
        rc[f"{g}/pyval_regrade_equals_stored"] += ok_py == r["success"]
        if online:
            rc[f"{g}/online_graded_rows"] += 1
            if cannot:
                rc[f"{g}/online_rows_val_cannot_handle"] += 1
            else:
                rc[f"{g}/online_rows_val_handled"] += 1
                rc[f"{g}/online_val_equals_stored"] += ok_val == r["success"]
                rc[f"{g}/online_fail_to_success"] += (not r["success"]) and bool(ok_val)
                rc[f"{g}/online_success_to_fail"] += bool(r["success"]) and not ok_val
        # the row's online grade with VAL as the validator, where VAL read every
        # plan the grader sent; otherwise the stored grade is kept
        regraded[(model, arm, corpus)][k] = {
            "success": bool(ok_val) if (online and not cannot) else bool(r["success"])}
        stored_g[(model, arm, corpus)][k] = {"success": bool(r["success"])}
        dit = byplan.get((corpus, d, p, "\n".join(dp))) if dp else None
        ov_strict = o.get("e2e_strict") if o else None
        if dit is not None:
            rc[f"{g}/delivered_rows_with_plan"] += 1
            rc[f"{g}/delivered_pyval_equals_overlay"] += (
                {V: True, I: False}.get(dit.pyval_live) == ov_strict)
            if dit.val_verdict in (V, I):
                rc[f"{g}/delivered_rows_val_handled"] += 1
                rc[f"{g}/delivered_val_equals_overlay"] += ({V: True, I: False}[dit.val_verdict] == ov_strict)
        row_out.append([cname, model, arm, corpus, d, p, r.get("prompt_variant"), r["success"],
                        r["failure_reason"], ok_py, fr_py, ok_val, fr_val, int(cannot), len(online),
                        "; ".join(sorted({it.klass for it in oits})),
                        dit.name if dit else "", dit.pyval_live if dit else "",
                        dit.val_verdict if dit else "", ov_strict if o else ""])

    # ------------------------------------------------------------ item level
    groups = defaultdict(list)
    meta_of = {}
    for (corpus, d, p, text), it in items.items():
        cells_of = set()
        for cell, k, r, requested, dp, o, at_cap in rows:
            if cell[4] == corpus and r["domain_name"] == d and r["problem_name"] == p and (
                    text in requested or "\n".join(dp) == text):
                cells_of.add((cell[0], cell[3], corpus))
        meta_of[id(it)] = cells_of
        groups["all plans"].append(it)
        groups[f"track: {it.track}"].append(it)
        for m, a, c in cells_of:
            groups[f"{m} | {a} | {c}"].append(it)
        for a in sorted({a for _, a, _ in cells_of}):
            groups[f"arm: {a}"].append(it)

    def agree(its):
        handled = [it for it in its if it.val_verdict in (V, I) and it.label in (V, I)]
        k = sum(it.val_verdict == it.label for it in handled)
        lo, hi = vc.wilson(k, len(handled))
        return dict(n=len(its), handled=len(handled), agree=k, lo=lo, hi=hi,
                    bracketed=sum(it.read_as == "with brackets added" for it in handled),
                    case=sum(it.klass.startswith("pyval rejects names") for it in its),
                    other=sum(it.klass.startswith("other") for it in its),
                    val_cannot=sum(it.val_verdict == CANNOT and it.label in (V, I) for it in its),
                    pyval_error=sum(it.label not in (V, I) for it in its),
                    valid=sum(it.label == V for it in handled))
    order = ["all plans", "arm: tool arm", "arm: unaided", "track: classical", "track: numeric"] + [
        f"{c[0]} | {c[3]} | {c[4]}" for c in CELLS]
    summ = {g: agree(groups[g]) for g in order if g in groups}
    klasses = Counter(it.klass for it in all_items)

    def desc(it):
        return (f"{item_corpus[id(it)]} {it.domain} {it.problem} `{it.name}` "
                f"({'; '.join(sorted(' | '.join(c) for c in meta_of[id(it)]))}): pyval {it.label} "
                f"`{it.pyval_status}`, VAL {it.val_verdict} `{it.val_status}` ({it.read_as})"
                + (f", pyval in lower case: {it.pyval_lower}" if it.pyval_lower else "")
                + f"; plan: `{' | '.join(it.plan_text.split(chr(10)))[:160]}`")

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "val_items.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["corpus", "track", "domain", "problem", "item", "cells", "class", "pyval_live",
                    "pyval_status", "pyval_lowercase", "val_read_as", "val_verdict", "val_status",
                    "val_detail", "val_as_sent", "n_plan_lines", "val_plan_size", "rows_online_tool",
                    "rows_online_notools", "rows_delivered_tools_arm", "plan"])
        for (corpus, d, p, text), it in items.items():
            w.writerow([corpus, it.track, d, p, it.name,
                        "; ".join(sorted(" | ".join(c) for c in meta_of[id(it)])), it.klass,
                        it.pyval_live, it.pyval_status, it.pyval_lower, it.read_as, it.val_verdict,
                        it.val_status, it.val_detail, "/".join(str(x) for x in it.val_raw),
                        it.n_plan_lines, "" if it.val_plan_size is None else it.val_plan_size,
                        it.sources["online_tool"], it.sources["online_notools"],
                        it.sources["delivered_tools_arm"], " | ".join(text.split("\n"))])
    with (out_dir / "val_rows.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "model", "arm", "corpus", "domain", "problem", "variant", "stored_success",
                    "stored_failure_reason", "pyval_regrade_success", "pyval_regrade_reason",
                    "val_regrade_success", "val_regrade_reason", "val_cannot_handle", "online_plans",
                    "online_plan_classes", "delivered_plan_item", "delivered_pyval", "delivered_val",
                    "overlay_e2e_strict"])
        w.writerows(row_out)
    summary = dict(val_banner=banner, val_sha256=val_sha, stats=dict(stats), rows=dict(rc),
                   items=summ, classes=dict(klasses),
                   not_agree=[desc(it) for it in all_items if not it.klass.startswith("agree")])
    (out_dir / "val_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")

    # ------------------------------------------------------------ markdown
    def fa(a):
        return (f"{a['agree']:,} / {a['handled']:,} ({100 * a['agree'] / a['handled']:.2f}%, "
                f"[{a['lo']:.2f}, {a['hi']:.2f}])" if a["handled"] else "none")
    L = ["# KCL VAL on the Claude solve plans (C1 method)", "",
         f"VAL: {banner}; sha256 `{val_sha}`.", "",
         f"Solve rows read: {len(rows):,}; distinct graded plans: {len(all_items):,}. Harness verdict = "
         "live pyval through the plugin. A plan counts as handled when both gave a verdict and VAL read "
         "as many steps as were sent (after adding brackets to bare `name arg` lines, where needed).", "",
         "## Plans: VAL against pyval (Wilson 95%)", "",
         "| group | distinct plans | agree / handled | of which VAL read with brackets added | "
         "pyval valid (handled) | disagree: pyval rejects the fixture's own upper-case names | "
         "disagree: other | VAL cannot handle | pyval error shape (graded a failure) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for g, a in summ.items():
        L.append(f"| {g} | {a['n']:,} | {fa(a)} | {a['bracketed']} | {a['valid']:,} | {a['case']} | "
                 f"{a['other']} | {a['val_cannot']} | {a['pyval_error']} |")
    L += ["", "Classes over all plans: " + "; ".join(f"{k} {v}" for k, v in sorted(klasses.items())) + ".",
          "", "## Row level", "",
          "| cell | rows | answer at the 16,384-char cap (not rebuilt) | pyval regrade = stored `success` | "
          "online-graded rows VAL handled | VAL regrade = stored | stored fail → VAL success | "
          "stored success → VAL fail | delivered plans (tool arm) | pyval = overlay | VAL = overlay |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for cell in CELLS:
        g = f"{cell[0]} | {cell[3]} | {cell[4]}"
        n = rc[f"{g}/rows"]
        nb = n - rc[f"{g}/rows_at_snapshot_cap"]
        L.append(f"| {g} | {n} | {rc[f'{g}/rows_at_snapshot_cap']} | {rc[f'{g}/pyval_regrade_equals_stored']} / {nb} | "
                 f"{rc[f'{g}/online_rows_val_handled']} / {rc[f'{g}/online_graded_rows']} | "
                 f"{rc[f'{g}/online_val_equals_stored']} / {rc[f'{g}/online_rows_val_handled']} | "
                 f"{rc[f'{g}/online_fail_to_success']} | {rc[f'{g}/online_success_to_fail']} | "
                 f"{rc[f'{g}/delivered_rows_with_plan']} | {rc[f'{g}/delivered_pyval_equals_overlay']} / "
                 f"{rc[f'{g}/delivered_rows_with_plan']} | {rc[f'{g}/delivered_val_equals_overlay']} / "
                 f"{rc[f'{g}/delivered_rows_val_handled']} |")
    L += ["", "## Every plan where VAL and pyval do not agree, or one of them gave no verdict", ""]
    for kl in sorted({it.klass for it in all_items if not it.klass.startswith("agree")}):
        L += [f"### {kl}", ""]
        L += [f"- {desc(it)}" for it in all_items if it.klass == kl]
        L.append("")
    # ------------------------------------------------------------ effect on the contamination test
    eq04 = _eq04()
    L += ["## Post hoc: unaided solve, renamed − canonical, stored grade vs VAL grade (T7 method)", "",
          "VAL grade = the online grade with VAL in pyval's place, on rows where VAL read every plan the "
          "grader sent; other rows keep the stored grade.", "", eq04.HEAD]
    contam = {}
    for model in ("Sonnet 4.6", "Haiku 4.5"):
        for nm, src in (("stored grade", stored_g), ("VAL grade", regraded)):
            a, b = src[(model, "unaided", "canonical")], src[(model, "unaided", "renamed")]
            r = eq04.tost(*eq04.paired_arrays(a, b, lambda k: True))
            contam[(model, nm)] = r
            L.append(eq04.row(f"{model} unaided solve, {nm}", r))
    L.append("")
    OUT.mkdir(exist_ok=True)
    (OUT / "val_frontier_solve.md").write_text("\n".join(L) + "\n")

    N = numbers_rows(summ, klasses, rc, contam)
    (OUT / "numbers_val_frontier_solve.md").write_text("\n".join(N) + "\n")
    print("\n".join(N))
    (OUT / "val_frontier_solve.json").write_text(json.dumps(
        dict(items=summ, classes=dict(klasses), rows=dict(rc), val_sha256=val_sha), indent=1) + "\n")
    print("\n".join(L))
    tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
