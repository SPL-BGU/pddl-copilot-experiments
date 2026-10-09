"""Entry point: the preregistered analysis of the delivered rerun.

    python -m tools.delivered_rerun.run --print-package-hash
    python -m tools.delivered_rerun.run --fixture tests/fixtures/delivered_rerun --out OUT
    python -m tools.delivered_rerun.run --rerun-root results --canonical-root \\
        results/sweep5v2-live --gt-cache results/derived/gt_cache.json \\
        --out OUT --i-have-frozen <sha256 printed by --print-package-hash>

Live mode refuses to start unless `--i-have-frozen` equals the sha256 of this
package's files, so the code cannot be run on the rerun's rows before it is
frozen (prereg §8). Fixture mode runs only on a directory that carries the
`SYNTHETIC_FIXTURE` marker and a non-registered (small) design.

Order of operations follows the prereg: completeness and VOID rules (§7)
for Parts A, B and C -> parity on tool-verified success (§3, before any
delivered number) and the Part C parity check on the stored online grade (§2)
-> delivered grading of every rerun row, tool and no-tools alike (§8b item 12)
-> E1–E4 (§4) -> readings (§5) -> readout tripwires -> JSON + markdown (both
rendered in memory before either is written). Any failure exits non-zero
without writing a readout.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from . import analysis as A          # noqa: E402
from . import constants as C         # noqa: E402
from . import grade as G             # noqa: E402
from . import schema as S            # noqa: E402
from . import tripwires as T         # noqa: E402
from .readout import render          # noqa: E402

PACKAGE_DIR = Path(__file__).resolve().parent
FIXTURE_MARKER = "SYNTHETIC_FIXTURE"


class Halt(Exception):
    """A registered stop: exits non-zero with the message, no readout."""


# Files outside the package whose behaviour the analysis imports. They are
# part of the freeze: a later edit to any of them changes the package hash,
# so `--i-have-frozen` refuses to run until the change is declared.
# Every repo module imported by the package, by `run_experiment` (for
# resolve_plugin_dirs) and by the live-mode gates; a test checks this list
# covers sys.modules after those imports (review F2).
DEPENDENCIES = (
    "pddl_eval/__init__.py", "pddl_eval/scoring.py", "pddl_eval/chat.py",
    "pddl_eval/schemas.py", "pddl_eval/runner.py", "pddl_eval/summary.py",
    "pddl_eval/prompts.py", "pddl_eval/domains.py", "pddl_eval/resume.py",
    "run_experiment.py", "tools/__init__.py", "tools/e2e_regrade.py",
    "tools/_run_manifest.py", "tools/gt_cache_gate.py",
)


def frozen_files() -> list[tuple[str, Path]]:
    own = [(f"tools/delivered_rerun/{p.name}", p) for p in sorted(PACKAGE_DIR.glob("*.py"))]
    return own + [(d, REPO / d) for d in DEPENDENCIES]


def file_hashes() -> list[tuple[str, str]]:
    return [(rel, hashlib.sha256(p.read_bytes()).hexdigest()) for rel, p in frozen_files()]


def package_sha256() -> str:
    """sha256 over (path, sha256(bytes)) of the package and its imported deps."""
    h = hashlib.sha256()
    for rel, digest in file_hashes():
        h.update(rel.encode() + b"\0" + digest.encode() + b"\n")
    return h.hexdigest()


def domains_manifest(domains_dir: Path) -> tuple[int, str]:
    """(file count, sha256 over (relative path, sha256(bytes))) of every .pddl
    and .plan file that pddl_eval.domains.load_domains can read."""
    files = sorted(f for d in ("classical", "numeric") for f in (domains_dir / d).rglob("*")
                   if f.is_file() and f.suffix in (".pddl", ".plan"))
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(domains_dir).as_posix().encode() + b"\0"
                 + hashlib.sha256(f.read_bytes()).hexdigest().encode() + b"\n")
    return len(files), h.hexdigest()


def check_domains(domains_dir: Path) -> None:
    n, digest = domains_manifest(domains_dir)
    if (n, digest) != (C.DOMAINS_FILES, C.DOMAINS_MANIFEST_SHA256):
        raise Halt(f"{domains_dir}: {n} fixture files, manifest {digest}; registered "
                   f"{C.DOMAINS_FILES}, {C.DOMAINS_MANIFEST_SHA256}")


def check_marketplace(head: str, plugin_changes: list[str]) -> None:
    """prereg §8: tools repo `pddl-copilot` at 5e4f9c0, and no uncommitted
    change under plugins/ (the validator code the solve plans are checked
    with): no edited tracked file and no untracked file git does not ignore."""
    if not head.startswith(C.MARKETPLACE_PIN):
        raise Halt(f"marketplace HEAD {head[:12]} is not the pinned {C.MARKETPLACE_PIN} "
                   "(prereg §8); check it out before validating solve plans")
    if plugin_changes:
        raise Halt(f"marketplace has uncommitted changes under plugins/: {plugin_changes[:5]}")


def marketplace_state(path: Path) -> tuple[str, list[str]]:
    """(HEAD sha, `git status --porcelain` lines under plugins/): edited
    tracked files and untracked files, ignored files left out (git status
    lists ignored files only with --ignored)."""
    head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True,
                          text=True)
    if head.returncode != 0:
        raise Halt(f"--marketplace-path {path}: not a git checkout ({head.stderr.strip()})")
    st = subprocess.run(["git", "-C", str(path), "status", "--porcelain",
                         "--untracked-files=all", "--", "plugins"],
                        capture_output=True, text=True)
    if st.returncode != 0:
        raise Halt(f"--marketplace-path {path}: git status failed ({st.stderr.strip()})")
    return head.stdout.strip(), [ln for ln in st.stdout.splitlines() if ln.strip()]


def load_audit_notes(path: Path | None, audited: set[str]) -> dict[str, str]:
    """§8b item 15: 'the audit is recorded in the readout'. Every released
    tripwire needs a written note; the notes are embedded verbatim."""
    if not audited:
        if path is not None:
            raise Halt("--audit-notes given without --audited-tripwires")
        return {}
    if path is None:
        raise Halt("--audited-tripwires needs --audit-notes FILE (a JSON object with "
                   "one note per released tripwire id)")
    try:
        notes = json.loads(path.read_text())
    except (OSError, ValueError) as e:      # missing/unreadable file, bad JSON
        raise Halt(f"--audit-notes {path}: cannot be read as JSON "
                   f"({type(e).__name__}: {e})") from e
    if not isinstance(notes, dict) or set(notes) != audited:
        raise Halt(f"--audit-notes must have exactly one entry per released tripwire "
                   f"{sorted(audited)}")
    for k, v in notes.items():
        if not isinstance(v, str) or not v.strip():
            raise Halt(f"--audit-notes: the note for {k} is empty")
    return notes


# ------------------------------------------------------------------ inputs
def fixture_design(root: Path) -> C.Design:
    d = json.loads((root / "design.json").read_text())
    counts = {tuple(k.split("|")): tuple(v) for k, v in d["canonical_delivered_counts"].items()}
    design = C.Design(name="fixture", n_part_a_cell=d["n_part_a_cell"], n_part_b=d["n_part_b"],
                      per_variant_a=d["per_variant_a"], per_variant_b=d["per_variant_b"],
                      per_task_variant=d["per_task_variant"], k_domains=d["k_domains"],
                      n_no_tools_cell=d["n_no_tools_cell"],
                      canonical_delivered_counts=counts)
    if design.n_part_a_cell == C.REGISTERED.n_part_a_cell or design.n_part_b == C.REGISTERED.n_part_b:
        raise Halt("fixture mode refuses a registered-size design")
    return design


def load_all(design: C.Design, rerun_root: Path, canonical_root: Path) -> dict:
    cells = {
        "rerun_a": {m: S.load_cell(rerun_root, S.spec_rerun_a(design, m)) for m in C.PART_A_MODELS},
        "rerun_b": S.load_cell(rerun_root, S.spec_rerun_b(design)),
        "rerun_c": {m: S.load_cell(rerun_root, S.spec_rerun_c(design, m)) for m in C.PART_A_MODELS},
        "canon_tools": {m: S.load_cell(canonical_root, S.spec_canonical_tools(design, m))
                        for m in C.PART_A_MODELS},
        "canon_nt": {m: S.load_cell(canonical_root, S.spec_canonical_no_tools(design, m))
                     for m in C.PART_A_MODELS},
    }
    # §7 stop rule: > 1% exception / infrastructure rows -> VOID, rerun from scratch.
    for lc in (list(cells["rerun_a"].values()) + [cells["rerun_b"]]
               + list(cells["rerun_c"].values())):
        bad = lc.void_rule_rows
        if bad > C.EXCEPTION_VOID_FRAC * len(lc.rows):
            raise Halt(f"VOID (§7): {lc.spec.name} has {bad} exception/infrastructure rows "
                       f"of {len(lc.rows)} (> {100 * C.EXCEPTION_VOID_FRAC:.0f}%); the cell "
                       "is rerun from scratch, not analysed")
    return cells


def corpus_table(cells: dict) -> list[dict]:
    out = []
    every = (list(cells["rerun_a"].values()) + [cells["rerun_b"]]
             + list(cells["rerun_c"].values()) + list(cells["canon_tools"].values())
             + list(cells["canon_nt"].values()))
    for lc in every:
        rerun = lc.spec.layer == S.RERUN
        out.append({"cell": lc.spec.name, "layer": lc.spec.layer, "rows": len(lc.rows),
                    "torn_lines": lc.torn_lines, "exception_rows": lc.exception_rows,
                    "infra_rows": lc.infra_rows, "scoring_error_rows": lc.scoring_error_rows,
                    "storage_cuts": (sum(r.response_truncated_by_storage is True for r in lc.rows)
                                     if rerun else None),
                    # Review N3, descriptive only (the strip is never widened):
                    # answers starting with the exact registered prefix, with
                    # it twice, and with a channel marker left after the strip.
                    "prefix_rows": (sum(G.has_prefix(r.response) for r in lc.rows)
                                    if rerun else None),
                    "doubled_prefix_rows": (sum(G.doubled_prefix(r.response) for r in lc.rows)
                                            if rerun else None),
                    "residual_marker_rows": (sum(G.residual_marker(r.response) for r in lc.rows)
                                             if rerun else None)})
    return out


def fixture_verdicts(root: Path) -> dict:
    table = json.loads((root / "plan_verdicts.json").read_text())
    out = {}
    for e in table:
        out[(e["domain"], e["problem"], tuple(e["plan"]))] = e["valid"]
    return out


async def live_verdicts(need: set, domains_dir: Path, marketplace: Path) -> dict:
    """Validate every delivered solve plan with the same live MCP oracle the
    harness and tools/e2e_regrade.py use (`_validate_model_plan`)."""
    from pddl_eval.chat import MCPPlanner
    from pddl_eval.domains import load_domains
    from pddl_eval.scoring import _validate_model_plan
    from run_experiment import resolve_plugin_dirs
    domains = load_domains(domains_dir)
    # Checked before connecting, so a missing fixture is a named HALT, not a
    # KeyError traceback.
    absent = sorted({(d, p) for d, p, _ in need
                     if d not in domains or p not in domains[d]["problems"]})
    if absent:
        raise Halt(f"plan validation: {len(absent)} domain/problem pair(s) not in "
                   f"{domains_dir}: {absent[:5]}")
    mcp = MCPPlanner()
    await mcp.connect(resolve_plugin_dirs(marketplace))
    out = {}
    try:
        for dname, pname, plan in sorted(need):
            dinfo = domains[dname]
            v = await _validate_model_plan(mcp, dinfo["domain"], dinfo["problems"][pname],
                                           list(plan))
            if v is None:
                raise Halt(f"plan validation transport error for {dname}/{pname}")
            out[(dname, pname, plan)] = v
    finally:
        await mcp.close()
    return out


# ------------------------------------------------------------------ analysis
def analyse(design: C.Design, cells: dict, gt_cache: dict, verdict_fn, mode: str,
            audit_notes: dict[str, str]) -> dict:
    audited = set(audit_notes)
    k = design.k_domains
    rerun_a, rerun_b, rerun_c = cells["rerun_a"], cells["rerun_b"], cells["rerun_c"]

    # §3 first: tool-verified only, before any delivered grade exists. The
    # Part C parity check reads only the stored online grade as well.
    par = A.parity(rerun_a, cells["canon_tools"], k)
    par_c = A.part_c_parity(rerun_c, cells["canon_nt"], k)
    book = A.StatusBook(par, par_c)

    rerun_rows = ([r for lc in rerun_a.values() for r in lc.rows] + list(rerun_b.rows)
                  + [r for lc in rerun_c.values() for r in lc.rows])
    need = G.solve_plans_to_validate(rerun_rows)
    verdicts = verdict_fn(need)
    grades: A.Grades = {}
    for r in rerun_rows:
        grades[(r.cell, r.trial_key)] = G.grade(r, gt_cache, verdicts)

    e1 = [A.rate_cell(list(rerun_a[m].rows), grades, m, t, a, C.STYLE_A, k, book.a(m, t, a))
          for m, t, a in A.CELLS]
    e2 = A.e2(rerun_a, rerun_c, grades, k, book)
    e3 = A.e3(rerun_a, grades, k, book)
    gaps = [A.e4_cell(list(rerun_a[m].rows), grades, gt_cache, m, t, a) for m, t, a in A.CELLS]
    r1 = A.r1(e2)
    readings = {"R1": r1, "R2": A.r2(e3), "R3": A.r3(r1["label"], e3),
                "R4": A.r4(rerun_a, grades, book),
                "R5": A.r5(list(rerun_a[C.PART_B_MODEL].rows), list(rerun_b.rows), grades, k)}

    fired = T.check(design, par, e1, gaps, e2, rerun_a, cells["canon_tools"])
    unaudited = {k_: v for k_, v in fired.items() if k_ not in audited}
    if unaudited:
        raise Halt("readout tripwire(s) fired; audit before any readout sentence:\n  "
                   + "\n  ".join(f"{k_}: {v}" for k_, v in unaudited.items()))

    return {
        "mode": mode,
        "package_sha256": package_sha256(),
        "design": design.name,
        "audited_tripwires": {k_: v for k_, v in fired.items() if k_ in audited},
        "audit_notes": audit_notes,
        "corpus": corpus_table(cells),
        "parity": asdict(par),
        "apparatus_deltas": list(A.APPARATUS_DELTAS),
        "part_c_parity": [asdict(c) for c in par_c],
        "e1": [asdict(c) for c in e1],
        "e2": [asdict(c) for c in e2],
        "e2_caveat": A.E2_CAVEAT,
        "e3": [asdict(c) for c in e3],
        "e4": [asdict(g) for g in gaps],
        "readings": readings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--print-package-hash", action="store_true")
    ap.add_argument("--fixture", type=Path, help="synthetic fixture root (tests only)")
    ap.add_argument("--rerun-root", type=Path)
    ap.add_argument("--canonical-root", type=Path)
    # Live mode requires these explicitly: from a git worktree, REPO-relative
    # defaults point at the wrong checkout (review F2).
    ap.add_argument("--gt-cache", type=Path)
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--marketplace-path", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--i-have-frozen", metavar="SHA256")
    ap.add_argument("--audited-tripwires", default="",
                    help="comma-separated tripwire ids a human has audited")
    ap.add_argument("--audit-notes", type=Path,
                    help="JSON object {tripwire id: audit note}, one per released id")
    args = ap.parse_args(argv)

    if args.print_package_hash:
        for rel, digest in file_hashes():
            print(f"{digest}  {rel}")
        print(f"{package_sha256()}  (package hash for --i-have-frozen)")
        return 0
    audited = {x for x in args.audited_tripwires.split(",") if x}
    try:
        audit_notes = load_audit_notes(args.audit_notes, audited)
        if args.out is None:
            raise Halt("--out is required")
        if args.fixture is not None:
            root = args.fixture
            if not (root / "rerun" / FIXTURE_MARKER).exists():
                raise Halt(f"fixture mode: {root}/rerun has no {FIXTURE_MARKER} marker")
            design = fixture_design(root)
            cells = load_all(design, root / "rerun", root / "canonical")
            gt_cache = json.loads((root / "gt_cache.json").read_text())
            table = fixture_verdicts(root)

            def verdict_fn(need):
                missing = [n for n in need if n not in table]
                if missing:
                    raise Halt(f"fixture has no validator verdict for {missing[:3]}")
                return {n: table[n] for n in need}
            mode = "fixture"
        else:
            if args.i_have_frozen != package_sha256():
                raise Halt("refusing to run on live data: --i-have-frozen does not match the "
                           "package sha256 (freeze the package first, prereg §8)")
            missing = [f for f, v in (("--rerun-root", args.rerun_root),
                                      ("--canonical-root", args.canonical_root),
                                      ("--gt-cache", args.gt_cache),
                                      ("--marketplace-path", args.marketplace_path)) if v is None]
            if missing:
                raise Halt(f"live mode requires {', '.join(missing)}")
            check_marketplace(*marketplace_state(args.marketplace_path))
            check_domains(args.domains_dir)
            design = C.REGISTERED
            C.assert_registered(design)
            from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash
            gt_cache = json.loads(args.gt_cache.read_text())
            if canonical_hash(gt_cache) != PREREG_PINNED_HASH:
                raise Halt("ground-truth cache does not match the pinned canonical hash")
            cells = load_all(design, args.rerun_root, args.canonical_root)

            def verdict_fn(need):
                return asyncio.run(live_verdicts(need, args.domains_dir, args.marketplace_path))
            mode = "live"
        res = analyse(design, cells, gt_cache, verdict_fn, mode, audit_notes)
        # Both outputs are produced in memory first, so a render error leaves
        # neither file on disk (never a JSON readout without its markdown).
        try:
            md = render(res)
            js = json.dumps(res, indent=1, sort_keys=True, default=list) + "\n"
        except Exception as e:  # noqa: BLE001 -- any render failure is a named HALT
            raise Halt(f"readout render failed ({type(e).__name__}: {e}); "
                       "nothing written") from e
        write_readout(args.out, js, md)
    except (Halt, S.SchemaError, C.RegisteredCheckFailed, AssertionError) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}/delivered_rerun_readout.{{json,md}}")
    return 0


def write_readout(out: Path, js: str, md: str) -> None:
    """Write the JSON and markdown readouts as a pair: both go to temporary
    names first and are renamed only when both writes succeeded; on an
    error the temporary files, and any file this call already renamed into
    place, are removed and the run halts."""
    final = [out / "delivered_rerun_readout.json", out / "delivered_rerun_readout.md"]
    tmp = [f.with_name(f.name + ".tmp") for f in final]
    placed: list[Path] = []
    try:
        out.mkdir(parents=True, exist_ok=True)
        for t, text in zip(tmp, (js, md)):
            t.write_text(text)
        for t, f in zip(tmp, final):
            t.replace(f)
            placed.append(f)
    except OSError as e:
        for f in tmp + placed:
            with contextlib.suppress(OSError):    # best effort; the halt is what counts
                f.unlink(missing_ok=True)
        raise Halt(f"could not write the readout to {out} ({e}); nothing kept") from e


if __name__ == "__main__":
    raise SystemExit(main())
