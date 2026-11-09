"""Build the D1b new item kinds as new fixture trees (no harness change).

Reads the canonical tree (`--src-dir`, normally `domains/`, never written)
and writes three sibling trees in the same flat layout, which the frozen
loader (`pddl_eval.domains.load_domains` on `main`) reads unchanged through
`run_experiment.py --domains-dir`:

  `--out-dir` (normally `domains-hard/`): every task except validate_domain

    <track>/<domain>/domain.pddl            the same valid domain (copied)
    <track>/<domain>/pNN.pddl               a subset of the same valid problems
                                            (copied, original names kept)
    <track>/<domain>/pNN_vK.plan            distinct valid plans (planners)
    <track>/<domain>/pNN_bK.plan            invalid plans: a precondition fails
                                            at or after the halfway step
    <track>/<domain>/domain_neg.pddl        the first invalid domain
    <track>/<domain>/nNN.pddl               invalid problems with one real error
                                            (as many as valid problems)
    manifest.json, manifest.sha256          every item, its sha256, how it was
                                            made, the oracle and VAL verdicts
    planner_outputs.json                    raw planner plans; pass it back as
                                            --cache-json to rebuild the same tree

  `<out-dir>-vd-a/`, `<out-dir>-vd-b/` (one per chosen problem): validate_domain

    <track>/<domain>/domain.pddl            the same valid domain (copied)
    <track>/<domain>/pNN.pddl               ONE valid problem (tree a: the first
                                            chosen problem by name, tree b: the
                                            second)
    <track>/<domain>/domain_neg.pddl        tree a: the first invalid domain,
                                            tree b: the second
    manifest.json, manifest.sha256

Why two small trees. The frozen loader reads one invalid domain per folder,
by the exact name `domain_neg.pddl`, and the runner emits one validate_domain
job per valid problem plus one for `domain_neg`. A folder with two problems
therefore gives a 2:1 valid:invalid grid, and a second file such as
`domain_neg02.pddl` would be ignored without a warning (no glob reads it).
Editing the loader would change frozen files of the delivered-rerun package, so
each validate_domain tree holds one problem and one invalid domain (1:1),
and trees a and b together give the full balanced grid. No file named
`domain_neg<digits>.pddl` is written anywhere; the build stops if it finds
one.

How each kind is made (details in development/reference/d1b_harder_items.md):

* Valid plans. Classical: the domains/ v1 plan plus `classic_planner` with
  each of its three `strategy` values. Numeric: the v1 plan, `numeric_planner`,
  and ENHSP under further search settings (`tools/_enhsp_variants.py`, run in
  the solver plugin's own venv). Plans are normalised (one lowercase action
  per line), deduplicated exactly, and kept only if the oracle and VAL both
  accept them. The distinct count is recorded for every problem.
* Problem choice. Per domain, the problems with a v1 plan of at least 4
  steps are ranked by (distinct valid plans, capped at --max-valid-plans) then
  by v1 length, longest first; the first --problems-per-domain for which the
  invalid plans can be built are kept.
* Invalid plans. Each is one edit of one chosen valid plan: delete a step,
  swap two adjacent steps, or replace a step by a sibling grounding of the
  same action. Kept only if the oracle rejects it with a precondition failure
  whose first failing step i satisfies i >= max(2, ceil(n/2)) (n = length of
  the edited plan; i < n preferred), and VAL fails it at the same step on the
  same action.
* Invalid domains / problems. One local edit inside the define form (see
  `tools/_hard_items.py`): undeclared predicate, wrong arity, type mismatch,
  undeclared type, undeclared function (domains); undefined object, wrong
  arity, type mismatch, undeclared predicate, undeclared type, undeclared
  function (problems). Kinds are spread evenly over the items. Kept only if
  the oracle rejects the file, its report names the edited symbol, and VAL
  rejects it too.

The oracle is the pddl-validator plugin called exactly as the harness calls
it (`pddl_eval.domains._validate_capture` over `MCPPlanner`). After writing,
each new tree is loaded with `pddl_eval.domains.load_domains` and checked by
the harness's own fail-fast pass (`generate_ground_truth`), the
validate_domain grid of trees a and b together is checked to be balanced in
every domain, and every item is re-checked by VAL from disk. Each tree gets
its own manifest; the main one names the hashes of the others.

    .venv/bin/python tools/build_hard_fixtures.py \\
        --src-dir domains --out-dir domains-hard \\
        --marketplace-path ../pddl-copilot \\
        --solver-python ../pddl-copilot/plugins/pddl-solver/.venv/bin/python \\
        --val /path/to/copy/of/VAL/validate --val-prefix "arch -x86_64" \\
        [--problems-per-domain 2] [--max-valid-plans 2] [--seed 0] \\
        [--cache-json /tmp/pool.json] [--force]

  --force deletes and rebuilds all three trees.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from pddl_eval.chat import MCPPlanner, _safe_json_loads  # noqa: E402
from pddl_eval.domains import _validate_capture, generate_ground_truth, load_domains  # noqa: E402
from tools import _hard_items as H  # noqa: E402

FD_STRATEGIES = ("lazy_greedy_cea", "astar_lmcut", "lazy_greedy_ff")
# ENHSP settings tried on top of `numeric_planner` (whose own setting is
# "-h hadd -s gbfs", the up-enhsp default). Each is a heuristic + search pair
# documented in `java -jar enhsp.jar` usage.
ENHSP_CONFIGS = (
    "-h hradd -s gbfs",
    "-h hmrp -s gbfs -ha true",
    "-h hadd -s WAStar",
    "-h aibr -s WAStar",
    "-h hmax -s WAStar",
)
DOMAIN_KINDS = {
    "classical": ("undeclared_predicate", "wrong_arity", "type_mismatch", "undeclared_type"),
    "numeric": ("undeclared_predicate", "wrong_arity", "type_mismatch", "undeclared_type",
                "undeclared_function"),
}
PROBLEM_KINDS = {
    "classical": ("undefined_object", "wrong_arity", "type_mismatch", "undeclared_predicate",
                  "undeclared_type"),
    "numeric": ("undefined_object", "wrong_arity", "type_mismatch", "undeclared_predicate",
                "undeclared_type", "undeclared_function"),
}
PLAN_OPS = ("delete", "swap", "replace")
MIN_PLAN_LEN = 4
CANDIDATE_BUDGET = 120     # oracle calls per invalid plan, at most
FILE_SEEDS = 8             # locations tried per (file, error kind)


def _seed(*parts) -> int:
    """Stable seed (Python's str hash is salted per process)."""
    return int(hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def _sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# VAL
# ---------------------------------------------------------------------------

_VAL_PARSE_MARKERS = (
    "Problem in domain definition!", "Type problem in domain description!",
    "Type problem in problem specification!", "Parser failed to read file!",
    "Error in type-checking!",
)


@dataclass
class Val:
    binary: Path
    prefix: list[str]
    timeout: float = 120.0

    def _run(self, args: list) -> tuple[int, str]:
        cmd = self.prefix + [str(self.binary)] + [str(a) for a in args]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout,
                               errors="replace")
        except subprocess.TimeoutExpired:
            return -999, "TIMEOUT"
        return p.returncode, p.stdout + p.stderr

    def parse(self, domain_text: str, problem_text: str) -> dict:
        """`validate DOMAIN PROBLEM` (no plan): parse + type check. Same rule
        as tools/val_crosscheck.py: any VAL error message -> invalid."""
        with tempfile.TemporaryDirectory() as td:
            dp, pp = Path(td) / "domain.pddl", Path(td) / "problem.pddl"
            dp.write_text(domain_text)
            pp.write_text(problem_text)
            rc, out = self._run([dp, pp])
        msg = next((m for m in _VAL_PARSE_MARKERS if m in out), "")
        err = next((ln.strip() for ln in out.splitlines() if "rror" in ln), "")
        crashed = rc < 0 or rc >= 128
        if msg or err:
            return {"verdict": "invalid", "detail": msg or err,
                    "crashed_after_message": crashed}
        if crashed:
            return {"verdict": "cannot_handle", "detail": f"crash rc={rc}"}
        if rc != 0:
            return {"verdict": "invalid", "detail": f"rc={rc}"}
        return {"verdict": "valid", "detail": ""}

    def plan(self, domain_text: str, problem_text: str, plan: str) -> dict:
        """`validate -v DOMAIN PROBLEM PLAN`: verdict, first failing step and
        the action VAL names there."""
        with tempfile.TemporaryDirectory() as td:
            dp, pp, lp = (Path(td) / n for n in ("domain.pddl", "problem.pddl", "plan.txt"))
            dp.write_text(domain_text)
            pp.write_text(problem_text)
            lp.write_text(plan)
            rc, out = self._run(["-v", dp, pp, lp])
        if "Checking plan:" not in out:
            return {"verdict": "cannot_handle", "detail": f"rc={rc} " + " ".join(out.split())[-160:]}
        after = out.split("Checking plan:", 1)[1]
        if re.search(r"^Plan valid\s*$", after, re.M):
            return {"verdict": "valid", "status": "plan_valid"}
        if "Plan failed to execute" in after:
            m = re.search(r"Checking next happening \(time (\d+)\)\s*\n"
                          r"Plan failed because of unsatisfied precondition in:\s*\n\s*(\([^\n]*\))",
                          after)
            if m:
                return {"verdict": "invalid", "status": "failed_to_execute",
                        "step": int(m.group(1)), "action": " ".join(m.group(2).lower().split())}
            return {"verdict": "invalid", "status": "failed_to_execute", "step": None}
        if "Goal not satisfied" in after:
            return {"verdict": "invalid", "status": "goal_not_satisfied"}
        if "Bad plan description!" in after:
            return {"verdict": "invalid", "status": "bad_plan_description"}
        if re.search(r"^Plan invalid\s*$", after, re.M):
            return {"verdict": "invalid", "status": "plan_invalid_other"}
        return {"verdict": "cannot_handle", "detail": f"rc={rc}"}


# ---------------------------------------------------------------------------
# Oracle (the harness's own call path)
# ---------------------------------------------------------------------------

_STEP_FAIL_RE = re.compile(r"Step (\d+): (\([^\n]*?\))\s*✗ PRECONDITION FAILURE")
_FAILED_AT_RE = re.compile(r"Failed at step (\d+) of (\d+)")


@dataclass
class Oracle:
    mcp: MCPPlanner
    calls: Counter = field(default_factory=Counter)

    async def file(self, domain: str, problem: str | None = None) -> dict:
        args = {"domain": domain} if problem is None else {"domain": domain, "problem": problem}
        self.calls["validate_problem" if problem else "validate_domain"] += 1
        raw, verdict = await _validate_capture(self.mcp, args)
        data = _safe_json_loads(raw)
        data = data if isinstance(data, dict) else {}
        report = data.get("report", "") or ""
        first_err = next((ln.strip() for ln in report.splitlines() if "[ERROR]" in ln), "")
        # Drop the server's random temp folder so the manifest is reproducible.
        first_err = re.sub(r"'?/\S*?/((?:domain|problem)\.pddl)'?", r"\1", first_err)
        return {"verdict": verdict, "status": data.get("status"), "error": first_err[:300]}

    async def plan(self, domain: str, problem: str, plan: str) -> dict:
        self.calls["validate_plan"] += 1
        raw, verdict = await _validate_capture(
            self.mcp, {"domain": domain, "problem": problem, "plan": plan})
        data = _safe_json_loads(raw)
        data = data if isinstance(data, dict) else {}
        report = data.get("report", "") or ""
        out = {"verdict": verdict, "status": data.get("status")}
        m = _FAILED_AT_RE.search(report)
        if m:
            out["failed_step"], out["of"] = int(m.group(1)), int(m.group(2))
        m = _STEP_FAIL_RE.search(report)
        out["precondition_failure"] = bool(m)
        if m:
            out["failed_action"] = " ".join(m.group(2).lower().split())
            out["precondition_step"] = int(m.group(1))
        return out

    async def reason(self, domain: str, problem: str, plan: str) -> list[str]:
        """Unsatisfied preconditions at the failing step (get_state_transition)."""
        self.calls["get_state_transition"] += 1
        raw = await self.mcp.call_tool("get_state_transition",
                                       {"domain": domain, "problem": problem, "plan": plan})
        data = _safe_json_loads(raw)
        steps = data.get("steps") if isinstance(data, dict) else None
        for s in steps or []:
            if s.get("status") == "FAILED":
                return [u.get("expression", "") for u in s.get("unsatisfied_preconditions") or []]
        return []


# ---------------------------------------------------------------------------
# Valid-plan pool
# ---------------------------------------------------------------------------


async def _enhsp_variants(solver_python: Path, domain_file: Path, problem_file: Path,
                          timeout: float, sem: asyncio.Semaphore) -> dict:
    cmd = [str(solver_python), str(REPO / "tools" / "_enhsp_variants.py"),
           "--domain", str(domain_file), "--problem", str(problem_file),
           "--timeout", str(timeout)] + [f"--config={c}" for c in ENHSP_CONFIGS]
    async with sem:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate()
    try:
        return json.loads(out.decode() or "{}")
    except json.JSONDecodeError:
        return {"_error": err.decode()[-400:]}


async def build_pool(mcp: MCPPlanner, oracle: Oracle, val: Val, src: dict, solver_python: Path,
                     enhsp_timeout: float, cache: dict) -> dict:
    """{domain: {pname: {"plans": [{"steps", "sources", ...}], "rejected": [...]}}}"""
    # 1. raw planner outputs (cached)
    raw: dict = cache.setdefault("raw", {})
    sem = asyncio.Semaphore(4)
    enhsp_jobs = {}
    for dname, d in src.items():
        for pname in d["problems"]:
            key = f"{dname}/{pname}"
            if key in raw:
                continue
            entry: dict = {}
            dt, pt = d["domain"], d["problems"][pname]
            if d["type"] == "classical":
                for s in FD_STRATEGIES:
                    r = _safe_json_loads(await mcp.call_tool(
                        "classic_planner", {"domain": dt, "problem": pt, "strategy": s}))
                    entry[f"classic_planner strategy={s}"] = r.get("plan") if isinstance(r, dict) else None
            else:
                r = _safe_json_loads(await mcp.call_tool(
                    "numeric_planner", {"domain": dt, "problem": pt}))
                entry["numeric_planner"] = r.get("plan") if isinstance(r, dict) else None
                enhsp_jobs[key] = asyncio.create_task(_enhsp_variants(
                    solver_python, d["dir"] / "domain.pddl", d["dir"] / f"{pname}.pddl",
                    enhsp_timeout, sem))
            raw[key] = entry
            print(f"  planners: {key}", file=sys.stderr)
    for key, task in enhsp_jobs.items():
        res = await task
        for cfg, r in res.items():
            raw[key][f"enhsp {cfg}"] = r.get("plan") if isinstance(r, dict) else None
        print(f"  enhsp: {key}", file=sys.stderr)

    # 2. normalise, dedupe, check
    pool: dict = {}
    for dname, d in src.items():
        pool[dname] = {}
        for pname, ptext in d["problems"].items():
            cands: list[tuple[str, list[str]]] = [("domains/v1", H.plan_steps(d["v1"][pname]))]
            outputs = raw[f"{dname}/{pname}"]
            for srcname in _source_order(d["type"]):
                plan = outputs.get(srcname)
                if isinstance(plan, list) and plan:
                    cands.append((srcname, H.plan_steps("\n".join(plan))))
            distinct: dict[str, dict] = {}
            for srcname, steps in cands:
                t = H.plan_text(steps)
                distinct.setdefault(t, {"steps": steps, "sources": []})["sources"].append(srcname)
            plans, rejected = [], []
            for t, info in distinct.items():
                o = await oracle.plan(d["domain"], ptext, t)
                v = val.plan(d["domain"], ptext, t)
                info.update(oracle=o["verdict"], val=v["verdict"])
                (plans if o["verdict"] is True and v["verdict"] == "valid" else rejected).append(info)
            pool[dname][pname] = {
                "plans": plans, "rejected": rejected,
                "planner_outputs": {k: (len(v) if isinstance(v, list) else None)
                                    for k, v in outputs.items()}}
    return pool


def _source_order(track: str) -> list[str]:
    """Order in which distinct valid plans are taken (after domains/v1)."""
    if track == "classical":
        return [f"classic_planner strategy={s}" for s in FD_STRATEGIES]
    return ["numeric_planner"] + [f"enhsp {c}" for c in ENHSP_CONFIGS]


# ---------------------------------------------------------------------------
# Invalid plans
# ---------------------------------------------------------------------------


async def find_invalid_plan(oracle: Oracle, val: Val, dtext: str, ptext: str,
                            seed_steps: list[str], forbidden: set[str], op_order: list[str],
                            rng: random.Random, disagreements: list) -> dict | None:
    """First edit of `seed_steps` that meets the mid-plan rule and that VAL
    fails at the same step on the same action. Candidates where the oracle
    meets the rule but VAL says otherwise go to `disagreements` and the
    search goes on."""
    n = len(seed_steps)
    half = math.ceil(n / 2)
    dom = H.read_domain(dtext)
    objtypes = H.read_problem(ptext, dom).object_types(dom)
    per_op: dict[str, list] = {}
    for op in op_order:
        if op == "delete":
            c = [H.plan_delete(seed_steps, k) for k in range(half, n + 1)]
        elif op == "swap":
            c = [H.plan_swap(seed_steps, k) for k in range(max(1, half - 1), n)]
        else:
            c = [r for k in range(half, n + 1)
                 for r in H.plan_replacements(seed_steps, k, dom, objtypes)]
        c = [x for x in c if x is not None]
        rng.shuffle(c)
        per_op[op] = c
    # Round-robin over the edit kinds, starting with op_order[0], so every
    # kind gets tried within the budget.
    cands = [per_op[op][i] for i in range(max(map(len, per_op.values()), default=0))
             for op in op_order if i < len(per_op[op])]
    fallback = None
    tried = 0
    for steps, edit in cands:
        if tried >= CANDIDATE_BUDGET:
            break
        text = H.plan_text(steps)
        if text in forbidden:
            continue
        tried += 1
        o = await oracle.plan(dtext, ptext, text)
        if o["verdict"] is not False or o.get("status") != "INVALID" \
                or not o.get("precondition_failure"):
            continue
        i, m = o["precondition_step"], len(steps)
        if o.get("failed_step") != i or o.get("of") != m:
            continue
        if i < max(2, math.ceil(m / 2)):
            continue
        rec = {"edit": edit, "steps": steps, "text": text, "first_failing_step": i,
               "plan_length": m, "relative_position": round(i / m, 3),
               "failed_action": o["failed_action"], "oracle_status": o["status"]}
        if i == m:                      # failure on the last step: keep looking
            fallback = fallback or rec
            continue
        if await _confirm_plan(oracle, val, dtext, ptext, rec, disagreements):
            return rec
    if fallback and await _confirm_plan(oracle, val, dtext, ptext, fallback, disagreements):
        return fallback
    return None


async def _confirm_plan(oracle: Oracle, val: Val, dtext: str, ptext: str, rec: dict,
                        disagreements: list) -> bool:
    v = val.plan(dtext, ptext, rec["text"])
    rec["val"] = v
    if not (v["verdict"] == "invalid" and v.get("status") == "failed_to_execute"
            and v.get("step") == rec["first_failing_step"]
            and v.get("action") == rec["failed_action"]):
        disagreements.append({"edit": rec["edit"], "oracle_step": rec["first_failing_step"],
                              "oracle_action": rec["failed_action"], "val": v})
        return False
    rec["reason"] = await oracle.reason(dtext, ptext, rec["text"])
    return True


# ---------------------------------------------------------------------------
# Invalid domains and problems
# ---------------------------------------------------------------------------


def _mentions(report: str, mut: H.Mutation) -> bool:
    """The oracle's first error is about the edit we made: it names the new
    (undeclared) name, or, for arity and type errors, the symbol together
    with the kind of complaint."""
    d, low = mut.detail, report.lower()
    if mut.kind in ("undeclared_predicate", "undeclared_function", "undeclared_type",
                    "undefined_object"):
        return d["used"].lower() in low
    if mut.kind == "wrong_arity":
        return d["symbol"].lower() in low and "arity" in low
    if mut.kind == "type_mismatch":
        return d["symbol"].lower() in low and ("well-formed" in low or "type" in low)
    return False


async def make_invalid_file(oracle: Oracle, val: Val, kind: str, mutate, dtext: str,
                            ptext: str | None, val_pair_problem: str, seed_parts: tuple,
                            log: list) -> dict | None:
    """Try FILE_SEEDS locations for one error kind; first one that the oracle
    and VAL both reject wins. `ptext is None` -> a domain mutation."""
    seen: set[str] = set()
    for s in range(FILE_SEEDS):
        rng = random.Random(_seed(*seed_parts, kind, s))
        if ptext is None:
            mut = mutate(H.read_domain(dtext), rng)
        else:
            mut = mutate(H.read_domain(dtext), H.read_problem(ptext, H.read_domain(dtext)), rng)
        if mut is None:
            return None             # kind not possible for this file
        if mut.text in seen:
            continue
        seen.add(mut.text)
        if ptext is None:
            o = await oracle.file(mut.text)
            v = val.parse(mut.text, val_pair_problem)
        else:
            o = await oracle.file(dtext, mut.text)
            v = val.parse(dtext, mut.text)
        ok_oracle = o["verdict"] is False and _mentions(o["error"], mut)
        ok_val = v["verdict"] == "invalid"
        if ok_oracle and ok_val:
            return {"text": mut.text, "kind": kind, "detail": mut.detail, "oracle": o, "val": v}
        log.append({"file": "/".join(map(str, seed_parts[1:])), "kind": kind, "seed": s,
                    "detail": mut.detail, "oracle": o, "val": v,
                    # a disagreement = one says invalid, the other does not
                    "oracle_val_disagree": (o["verdict"] is False) != ok_val,
                    "why": ("oracle accepted the file" if o["verdict"] is not False
                            else "oracle named another error" if not ok_oracle
                            else "VAL accepted the file")})
    return None


def _kind_order(kinds: tuple, counts: Counter, rot: int) -> list[str]:
    """Least-used kind first; ties broken by a rotation that differs per domain."""
    return sorted(kinds, key=lambda k: (counts[k], (kinds.index(k) - rot) % len(kinds)))


# ---------------------------------------------------------------------------
# Source tree
# ---------------------------------------------------------------------------


def load_source(src_dir: Path, only: set[str] | None) -> dict:
    out: dict = {}
    for track in ("classical", "numeric"):
        for ddir in sorted(p for p in (src_dir / track).iterdir() if p.is_dir()):
            if only and ddir.name not in only:
                continue
            probs = {p.stem: p.read_text() for p in sorted(ddir.glob("p[0-9]*.pddl"))}
            out[ddir.name] = {
                "type": track, "dir": ddir, "domain": (ddir / "domain.pddl").read_text(),
                "problems": probs,
                "v1": {p: (ddir / f"{p}_v1.plan").read_text() for p in probs},
            }
    return out


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------


async def build(args: argparse.Namespace) -> None:
    src_dir, out_dir = Path(args.src_dir).resolve(), Path(args.out_dir).resolve()
    vd_dirs = vd_dirs_for(out_dir, args.problems_per_domain)
    for d_ in [out_dir] + vd_dirs:
        if d_ == src_dir or src_dir in d_.parents or d_ in src_dir.parents:
            raise SystemExit(f"{d_} must not be inside --src-dir or contain it")
    # Read the planner cache first: it may live inside --out-dir
    # (domains-hard/planner_outputs.json), which --force deletes.
    cache_path = Path(args.cache_json) if args.cache_json else None
    cache = json.loads(cache_path.read_text()) if cache_path and cache_path.exists() else {}
    for d_ in [out_dir] + vd_dirs:
        if d_.exists():
            if not args.force:
                raise SystemExit(f"{d_} exists; pass --force to rebuild it")
            shutil.rmtree(d_)
    src = load_source(src_dir, set(args.domains) if args.domains else None)
    val = Val(Path(args.val).resolve(), shlex.split(args.val_prefix or ""))
    plugins = Path(args.marketplace_path).resolve() / "plugins"
    mcp = MCPPlanner()
    await mcp.connect([plugins / "pddl-solver", plugins / "pddl-validator"])
    oracle = Oracle(mcp)
    try:
        print("== valid-plan pool", file=sys.stderr)
        pool = await build_pool(mcp, oracle, val, src, Path(args.solver_python), args.enhsp_timeout,
                                cache)
        cache_text = json.dumps(cache, indent=1, sort_keys=True) + "\n"
        if cache_path:
            cache_path.write_text(cache_text)
        # Raw planner outputs ship with the tree: with them as --cache-json a
        # rebuild does not depend on planner timeouts and gives the same files.
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "planner_outputs.json").write_text(cache_text)

        items: list[dict] = []          # one per written file of the main tree
        vd_items: list[list[dict]] = [[] for _ in vd_dirs]   # per validate_domain tree
        exclusions: list[dict] = []     # candidates the oracle and VAL disagreed on
        skipped: list[dict] = []        # what could not be built, and why
        dkind_counts: dict[str, Counter] = {"classical": Counter(), "numeric": Counter()}
        pkind_counts: dict[str, Counter] = {"classical": Counter(), "numeric": Counter()}
        file_logs: list[dict] = []

        for di, (dname, d) in enumerate(src.items()):
            track, dtext = d["type"], d["domain"]
            print(f"== {dname}", file=sys.stderr)
            ddir_out = out_dir / track / dname
            # ---- choose problems and build plans
            ranked = sorted(
                (p for p in d["problems"] if len(H.plan_steps(d["v1"][p])) >= MIN_PLAN_LEN),
                key=lambda p: (-min(len(pool[dname][p]["plans"]), args.max_valid_plans),
                               -len(H.plan_steps(d["v1"][p])), p))
            chosen: list[tuple[str, list[dict], list[dict]]] = []
            for pi, pname in enumerate(ranked):
                if len(chosen) >= args.problems_per_domain:
                    break
                ptext = d["problems"][pname]
                all_plans = pool[dname][pname]["plans"]
                valid = all_plans[:args.max_valid_plans]
                forbidden = {H.plan_text(p["steps"]) for p in all_plans}
                invalid: list[dict] = []
                for slot in range(len(valid)):
                    # b<slot> is an edit of v<slot>; when no edit of that plan
                    # qualifies, the other distinct valid plans are tried.
                    rot = (di + len(chosen) + slot) % len(PLAN_OPS)
                    op_order = list(PLAN_OPS[rot:] + PLAN_OPS[:rot])
                    rec = None
                    for si in [slot] + [j for j in range(len(all_plans)) if j != slot]:
                        rng = random.Random(_seed(args.seed, dname, pname, "plan", slot, si))
                        disagreements: list = []
                        rec = await find_invalid_plan(oracle, val, dtext, ptext,
                                                      all_plans[si]["steps"],
                                                      forbidden | {r["text"] for r in invalid},
                                                      op_order, rng, disagreements)
                        exclusions += [{"domain": dname, "problem": pname,
                                        "item": "invalid plan", "seed_plan_index": si + 1, **x}
                                       for x in disagreements]
                        if rec is not None:
                            rec["seed_index"] = si
                            break
                    if rec is not None:
                        invalid.append(rec)
                if not invalid:
                    skipped.append({"domain": dname, "problem": pname,
                                    "why": "no mid-plan precondition failure found"})
                    continue
                # Balance: as many valid plans as invalid ones for the problem.
                kept_valid = valid[:len(invalid)]
                for r in invalid:
                    si = r["seed_index"]
                    r["seed_plan"] = (f"{pname}_v{si + 1}.plan" if si < len(kept_valid) else
                                      "distinct valid plan not in the set, from "
                                      + ", ".join(all_plans[si]["sources"]))
                chosen.append((pname, kept_valid, invalid))
            if len(chosen) < args.problems_per_domain:
                skipped.append({"domain": dname, "why": f"only {len(chosen)} problems usable"})
            if not chosen:
                continue

            # ---- write valid problems and plans
            ddir_out.mkdir(parents=True, exist_ok=True)
            (ddir_out / "domain.pddl").write_bytes((d["dir"] / "domain.pddl").read_bytes())
            items.append({"path": f"{track}/{dname}/domain.pddl", "task": "validate_domain",
                          "label": "valid", "kind": "valid_domain",
                          "source": f"{src_dir.name}/{track}/{dname}/domain.pddl (copied)"})
            for pname, valid, invalid in chosen:
                (ddir_out / f"{pname}.pddl").write_bytes((d["dir"] / f"{pname}.pddl").read_bytes())
                items.append({"path": f"{track}/{dname}/{pname}.pddl", "task": "validate_problem",
                              "label": "valid", "kind": "valid_problem",
                              "source": f"{src_dir.name}/{track}/{dname}/{pname}.pddl (copied)"})
                for vi, vp in enumerate(valid, 1):
                    t = H.plan_text(vp["steps"])
                    (ddir_out / f"{pname}_v{vi}.plan").write_text(t)
                    items.append({"path": f"{track}/{dname}/{pname}_v{vi}.plan",
                                  "task": "validate_plan", "label": "valid",
                                  "kind": "distinct_valid_plan", "problem": pname,
                                  "plan_length": len(vp["steps"]), "sources": vp["sources"]})
                for bi, rec in enumerate(invalid, 1):
                    (ddir_out / f"{pname}_b{bi}.plan").write_text(rec["text"])
                    items.append({
                        "path": f"{track}/{dname}/{pname}_b{bi}.plan", "task": "validate_plan",
                        "label": "invalid",
                        "kind": "midplan_" + "_".join(
                            x for x in (rec["edit"]["op"], rec["edit"].get("how")) if x),
                        "problem": pname, "seed_plan": rec["seed_plan"],
                        "edit": rec["edit"], "plan_length": rec["plan_length"],
                        "first_failing_step": rec["first_failing_step"],
                        "relative_position": rec["relative_position"],
                        "failed_action": rec["failed_action"], "reason": rec["reason"],
                        "oracle": {"verdict": False, "status": rec["oracle_status"]},
                        "val": rec["val"]})

            # ---- invalid domains: one per chosen problem. Slot k goes to the
            # validate_domain tree k, paired with the k-th chosen problem by
            # name (the only problem in that tree, so the one the harness
            # pairs it with); slot 0 is also the main tree's domain_neg.pddl.
            n_inv = len(chosen)
            by_name = sorted(c[0] for c in chosen)
            used_kinds: list[str] = []
            for slot in range(n_inv):
                pair_name = by_name[slot]
                pair = d["problems"][pair_name]
                done = None
                for kind in _kind_order(DOMAIN_KINDS[track], dkind_counts[track], di + slot):
                    if kind in used_kinds:
                        continue
                    done = await make_invalid_file(oracle, val, kind, H.DOMAIN_MUTATORS[kind],
                                                   dtext, None, pair,
                                                   (args.seed, dname, "domain", slot), file_logs)
                    if done:
                        break
                if not done:
                    skipped.append({"domain": dname, "why": f"invalid domain slot {slot + 1}: no kind worked"})
                    continue
                used_kinds.append(done["kind"])
                dkind_counts[track][done["kind"]] += 1
                rec = {"task": "validate_domain", "label": "invalid", "kind": done["kind"],
                       "source": f"{src_dir.name}/{track}/{dname}/domain.pddl (one edit)",
                       "invalid_domain_slot": slot + 1,
                       "edit": done["detail"], "oracle": done["oracle"], "val": done["val"],
                       "val_pair_problem": f"{pair_name}.pddl"}
                if slot == 0:
                    (ddir_out / "domain_neg.pddl").write_text(done["text"])
                    items.append({"path": f"{track}/{dname}/domain_neg.pddl", **rec})
                vdir = vd_dirs[slot] / track / dname
                vdir.mkdir(parents=True, exist_ok=True)
                (vdir / "domain.pddl").write_bytes((d["dir"] / "domain.pddl").read_bytes())
                (vdir / f"{pair_name}.pddl").write_bytes((d["dir"] / f"{pair_name}.pddl").read_bytes())
                (vdir / "domain_neg.pddl").write_text(done["text"])
                vd_items[slot] += [
                    {"path": f"{track}/{dname}/domain.pddl", "task": "validate_domain",
                     "label": "valid", "kind": "valid_domain",
                     "source": f"{src_dir.name}/{track}/{dname}/domain.pddl (copied)"},
                    {"path": f"{track}/{dname}/{pair_name}.pddl", "task": "paired_problem",
                     "label": "valid", "kind": "valid_problem",
                     "source": f"{src_dir.name}/{track}/{dname}/{pair_name}.pddl (copied)"},
                    {"path": f"{track}/{dname}/domain_neg.pddl", **rec}]

            # ---- invalid problems: one per chosen problem, edited from it
            used_kinds = []
            for slot, (pname, _v, _b) in enumerate(chosen):
                done = None
                for kind in _kind_order(PROBLEM_KINDS[track], pkind_counts[track], di + slot + 1):
                    if kind in used_kinds:
                        continue
                    done = await make_invalid_file(oracle, val, kind, H.PROBLEM_MUTATORS[kind],
                                                   dtext, d["problems"][pname], "",
                                                   (args.seed, dname, pname, "problem"), file_logs)
                    if done:
                        break
                if not done:
                    skipped.append({"domain": dname, "problem": pname,
                                    "why": "invalid problem: no kind worked"})
                    continue
                used_kinds.append(done["kind"])
                pkind_counts[track][done["kind"]] += 1
                fname = f"n{slot + 1:02d}.pddl"
                (ddir_out / fname).write_text(done["text"])
                items.append({"path": f"{track}/{dname}/{fname}", "task": "validate_problem",
                              "label": "invalid", "kind": done["kind"],
                              "source": f"{src_dir.name}/{track}/{dname}/{pname}.pddl (one edit)",
                              "edit": done["detail"], "oracle": done["oracle"], "val": done["val"]})

        trees = [(out_dir, items)] + [(r, its) for r, its in zip(vd_dirs, vd_items) if its]

        # ---- no stray invalid-domain file the frozen loader would ignore
        stray = [f"{r.name}/{p}" for r, _ in trees for p in stray_negatives(r)]
        if stray:
            raise SystemExit(f"files the frozen loader would ignore: {stray}")

        # ---- the harness's own fail-fast pass over every new tree
        harness: dict = {}
        for root, _its in trees:
            print(f"== harness check {root.name} (load_domains + generate_ground_truth)",
                  file=sys.stderr)
            loaded = load_domains(root)
            gt = await generate_ground_truth(mcp, loaded)
            harness[root.name] = {
                "domains": len(loaded), "problems": sum(len(x["problems"]) for x in loaded.values()),
                "solvable": sum(1 for dn in gt for pn, e in gt[dn].items()
                                if pn != "_negatives" and e.get("solvable"))}

        # ---- validate_domain grid as the frozen loader emits it
        grids = {root.name: validate_domain_grid(root) for root, _ in trees}
        combined = combine_grids([grids[r.name] for r, _ in trees[1:]])
        unbalanced = {dn: g for dn, g in combined.items() if g["valid"] != g["invalid"]}
        if unbalanced:
            raise SystemExit(f"validate_domain trees are not balanced: {unbalanced}")

        # ---- VAL from disk, every item of every tree
        print("== VAL re-check from disk", file=sys.stderr)
        rechecks = {root.name: val_recheck(val, root, its) for root, its in trees}

        # ---- manifests: the validate_domain trees first, the main one names their hashes
        build_info = {
            "script": "tools/build_hard_fixtures.py",
            "script_sha256": _sha((REPO / "tools/build_hard_fixtures.py").read_bytes()),
            "helpers_sha256": {f: _sha((REPO / f).read_bytes()) for f in
                               ("tools/_hard_items.py", "tools/_enhsp_variants.py")},
            "seed": args.seed, "problems_per_domain": args.problems_per_domain,
            "max_valid_plans": args.max_valid_plans, "min_plan_len": MIN_PLAN_LEN,
            "enhsp_timeout_s": args.enhsp_timeout, "enhsp_configs": list(ENHSP_CONFIGS),
            "fd_strategies": list(FD_STRATEGIES),
            "marketplace_commit": _git_head(Path(args.marketplace_path)),
            "val_binary_sha256": _sha(Path(args.val).read_bytes()),
            "src_dir": src_dir.name,
            "planner_outputs_sha256": _sha(cache_text),
            "trees": [r.name for r, _ in trees],
        }
        vd_summary: dict = {}
        for k, (root, its) in enumerate(trees[1:]):
            m = tree_manifest(root, its)
            m.update({
                "what": "D1b new item kinds, validate_domain tree "
                        f"{root.name} (development/reference/d1b_harder_items.md)",
                "role": f"validate_domain only: one valid problem and one invalid domain "
                        f"(slot {k + 1}) per folder; run every tree named in "
                        f"validate_domain_trees of {out_dir.name}/manifest.json, each "
                        "to its own --output-dir",
                "build": build_info, "harness_check": harness[root.name],
                "val_recheck": rechecks[root.name],
                "validate_domain_jobs_per_variant": grids[root.name]})
            h = write_manifest(root, m)
            vd_summary[root.name] = {"manifest_sha256": h, "counts": m["counts"],
                                     "kinds": m["kinds"]}
        manifest = tree_manifest(out_dir, items)
        manifest.update({
            "what": "D1b new item kinds (development/reference/d1b_harder_items.md)",
            "role": "every task except validate_domain (here validate_domain is 2 valid : "
                    "1 invalid per folder; use the validate_domain trees instead)",
            "build": build_info,
            "harness_check": harness[out_dir.name],
            "val_recheck": rechecks[out_dir.name],
            "validate_domain_trees": vd_summary,
            "validate_domain_combined": {
                "jobs_per_variant": combined,
                "totals": {lab: sum(g[lab] for g in combined.values()) for lab in ("valid", "invalid")},
                "kinds": dict(sorted(Counter(
                    it["kind"] for _r, its in trees[1:] for it in its
                    if it["task"] == "validate_domain" and it["label"] == "invalid").items()))},
            "oracle_calls": dict(oracle.calls),
            "plan_pool": {dn: {pn: {"distinct_valid": len(v["plans"]),
                                    "sources": [p["sources"] for p in v["plans"]],
                                    "lengths": [len(p["steps"]) for p in v["plans"]],
                                    "rejected": [{"sources": r["sources"], "oracle": r["oracle"],
                                                  "val": r["val"]} for r in v["rejected"]],
                                    "planner_outputs": v["planner_outputs"]}
                               for pn, v in sorted(pp.items())}
                          for dn, pp in sorted(pool.items())},
            "exclusions": exclusions,
            "skipped": skipped,
            "rejected_file_candidates": file_logs,
        })
        h = write_manifest(out_dir, manifest)
        print(json.dumps({"counts": manifest["counts"], "kinds": manifest["kinds"],
                          "validate_domain_combined": manifest["validate_domain_combined"]["totals"],
                          "harness_check": harness, "val_recheck": rechecks,
                          "exclusions": len(exclusions), "skipped": skipped,
                          "manifest_sha256": {out_dir.name: h,
                                              **{n: v["manifest_sha256"]
                                                 for n, v in vd_summary.items()}}}, indent=1))
    finally:
        await mcp.close()


# ---------------------------------------------------------------------------
# Tree helpers (pure apart from reading the tree; unit-tested)
# ---------------------------------------------------------------------------

_STRAY_NEG_RE = re.compile(r"^domain_neg\d+\.pddl$")


def vd_dirs_for(out_dir: Path, n: int) -> list[Path]:
    """`domains-hard` -> [`domains-hard-vd-a`, `domains-hard-vd-b`, ...]."""
    if not 1 <= n <= 26:
        raise ValueError(f"need 1..26 validate_domain trees, got {n}")
    return [out_dir.parent / f"{out_dir.name}-vd-{chr(ord('a') + i)}" for i in range(n)]


def stray_negatives(root: Path) -> list[str]:
    """Files like `domain_neg02.pddl`: the frozen loader reads only
    `domain_neg.pddl`, so these would be skipped without a warning."""
    return sorted(str(p.relative_to(root)) for p in root.rglob("*.pddl")
                  if _STRAY_NEG_RE.match(p.name))


def validate_domain_grid(root: Path) -> dict:
    """validate_domain jobs per prompt variant that the frozen harness emits
    for this tree: one valid job per problem, one invalid job if the folder
    has `domain_neg.pddl` (pddl_eval/runner.py build_jobs)."""
    return {dn: {"valid": len(d["problems"]),
                 "invalid": int(d["negatives"]["domain"] is not None)}
            for dn, d in sorted(load_domains(root).items())}


def combine_grids(grids: list[dict]) -> dict:
    out: dict = {}
    for g in grids:
        for dn, c in g.items():
            acc = out.setdefault(dn, {"valid": 0, "invalid": 0})
            acc["valid"] += c["valid"]
            acc["invalid"] += c["invalid"]
    return dict(sorted(out.items()))


def val_recheck(val: Val, root: Path, items: list[dict]) -> dict:
    """Re-check every item from disk with VAL. A domain file is parsed with
    the folder's first problem by name, the one the harness pairs it with."""
    counts = Counter()
    for it in items:
        p = root / it["path"]
        ddir = p.parent
        dom = (ddir / "domain.pddl").read_text()
        first_p = sorted(ddir.glob("p[0-9]*.pddl"))[0].read_text()
        if it["path"].endswith(".plan"):
            pname = p.name.split("_")[0]
            v = val.plan(dom, (ddir / f"{pname}.pddl").read_text(), p.read_text())
        elif p.name.startswith("domain"):
            v = val.parse(p.read_text(), first_p)
        else:
            v = val.parse(dom, p.read_text())
        agree = (v["verdict"] == "valid") == (it["label"] == "valid") and v["verdict"] != "cannot_handle"
        it["val_recheck"] = v["verdict"]
        counts["agree" if agree else "disagree"] += 1
    return dict(counts)


def tree_manifest(root: Path, items: list[dict]) -> dict:
    """Items sorted by path with their sha256 from disk, plus counts and
    kinds; the file list must equal the fixture files on disk."""
    for it in items:
        it["sha256"] = _sha((root / it["path"]).read_bytes())
    items.sort(key=lambda x: x["path"])
    listed = [it["path"] for it in items]
    if len(set(listed)) != len(listed):
        raise SystemExit(f"{root.name}: a file is listed twice in the manifest")
    on_disk = sorted(str(p.relative_to(root)) for p in root.rglob("*")
                     if p.is_file() and p.parent != root)
    if listed != on_disk:
        raise SystemExit(f"{root.name}: manifest and files on disk differ: "
                         f"{sorted(set(listed) ^ set(on_disk))[:10]}")
    counts = Counter((it["task"], it["label"]) for it in items)
    return {
        "counts": {f"{t}/{lab}": c for (t, lab), c in sorted(counts.items())},
        "kinds": {f"{t}/{kind}": c for (t, kind), c in sorted(
            Counter((it["task"], it["kind"]) for it in items if it["label"] == "invalid").items())},
        "items": items,
    }


def write_manifest(root: Path, manifest: dict) -> str:
    text = json.dumps(manifest, indent=1, sort_keys=True, default=str) + "\n"
    (root / "manifest.json").write_text(text)
    h = _sha(text)
    (root / "manifest.sha256").write_text(f"{h}  manifest.json\n")
    return h


def _git_head(path: Path) -> str:
    p = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src-dir", required=True, help="canonical fixtures tree (read only)")
    ap.add_argument("--out-dir", required=True, help="main tree to write (e.g. domains-hard); the validate_domain trees go next to it as <out-dir>-vd-a, -vd-b, ...")
    ap.add_argument("--marketplace-path", required=True, help="pddl-copilot checkout")
    ap.add_argument("--solver-python", required=True,
                    help="python of the pddl-solver plugin venv (runs _enhsp_variants.py)")
    ap.add_argument("--val", required=True, help="KCL VAL `validate` binary")
    ap.add_argument("--val-prefix", default="", help='e.g. "arch -x86_64" for the macOS build')
    ap.add_argument("--problems-per-domain", type=int, default=2)
    ap.add_argument("--max-valid-plans", type=int, default=2)
    ap.add_argument("--enhsp-timeout", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-json", default=None, help="planner-output cache (speeds up reruns)")
    ap.add_argument("--domains", nargs="+", default=None, help="restrict to these domains")
    ap.add_argument("--force", action="store_true", help="delete and rebuild --out-dir and its validate_domain trees")
    asyncio.run(build(ap.parse_args()))


if __name__ == "__main__":
    main()
