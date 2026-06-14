"""Regenerate the per-instance difficulty metadata (`meta_sweep5v2.json`) that
the RQ deck (`rq_deck.py`) consumes for phase-2 (RQ0.5 / RQ0.6) difficulty binning.

Source of truth = the `domains/` tree (read-only). For every instance
`<domain>/<problem>` (problems `p01..p05` solvable + `n01..n05` unsolvable):

    track     : "classical" | "numeric"  — which top-level domains/ subtree
    obj_count : number of objects declared in the problem `(:objects ...)` block
    plan_len  : {variant: non-empty-line-count} over `<problem>_<variant>.plan`
                fixtures (v1..v5 valid, b1..b5 buggy). Empty for n0* (no fixtures).
    ref_len   : min plan length over the valid variants v1..v5; None when absent.

Top-level `domain_track` maps each domain name → its track.

Derivation verified to reproduce the committed oracle exactly (200 instances,
1000 plan_len cells, all ref_len): run with `--check <oracle.json>` to re-assert.
This is the tracked, reproducible path for a file that otherwise has no generator.

Usage:
    # regenerate to the tracked deck-data location
    python3 .claude/skills/analyzer/scripts/gen_meta.py \
        --out .claude/skills/analyzer/data/meta_sweep5v2.json

    # regenerate and HARD-ASSERT equality against an existing copy (diff-gate)
    python3 .claude/skills/analyzer/scripts/gen_meta.py --check \
        .claude/skills/analyzer/data/meta_sweep5v2.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DOMAINS = REPO / "domains"

PROBLEMS = [f"p{i:02d}" for i in range(1, 6)] + [f"n{i:02d}" for i in range(1, 6)]
VALID_VARIANTS = ["v1", "v2", "v3", "v4", "v5"]
BUGGY_VARIANTS = ["b1", "b2", "b3", "b4", "b5"]
ALL_VARIANTS = VALID_VARIANTS + BUGGY_VARIANTS


def _objects_block(pddl_text: str) -> str:
    """Return the token span between `(:objects` and its matching close paren."""
    m = re.search(r"\(:objects\b", pddl_text, re.IGNORECASE)
    if not m:
        return ""
    i = m.end()
    depth = 1  # we are inside the `(:objects` paren
    out = []
    while i < len(pddl_text) and depth > 0:
        c = pddl_text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        else:
            out.append(c)
        i += 1
    return "".join(out)


def obj_count(problem_path: Path) -> int | None:
    """Count declared objects in a problem file's `(:objects ...)` block.

    PDDL object syntax: `o1 o2 - type1 o3 - type2`. Names before each `-` are
    objects; the single token after `-` is the type (not counted). Untyped
    trailing names (no `-`) are also objects.

    Returns None for malformed problems — those missing a `(:objects)` or
    `(:init)` section. The intentionally-broken n0* negatives (no init / no
    objects) are unparseable as instances; the difficulty oracle records them
    as None and the deck excludes them from arity binning. (Verified: this
    `objects AND init` predicate reproduces the oracle's None set exactly.)
    """
    text = problem_path.read_text()
    has_objects = re.search(r"\(:objects\b", text, re.IGNORECASE) is not None
    has_init = re.search(r"\(:init\b", text, re.IGNORECASE) is not None
    if not (has_objects and has_init):
        return None
    block = _objects_block(text)
    tokens = block.replace("\n", " ").split()
    count = 0
    expect_type = False
    for tok in tokens:
        if tok == "-":
            expect_type = True
            continue
        if expect_type:
            expect_type = False  # this token is a type name, skip
            continue
        count += 1
    return count


def _nonempty_lines(path: Path) -> int:
    return sum(1 for ln in path.read_text().splitlines() if ln.strip())


def build_instances() -> dict:
    instances: dict[str, dict] = {}
    domain_track: dict[str, str] = {}
    for track in ("classical", "numeric"):
        track_dir = DOMAINS / track
        if not track_dir.is_dir():
            continue
        for dom_dir in sorted(p for p in track_dir.iterdir() if p.is_dir()):
            dom = dom_dir.name
            domain_track[dom] = track
            for prob in PROBLEMS:
                pf = dom_dir / f"{prob}.pddl"
                if not pf.exists():
                    continue
                plan_len: dict[str, int] = {}
                for var in ALL_VARIANTS:
                    pl = dom_dir / f"{prob}_{var}.plan"
                    if pl.exists():
                        plan_len[var] = _nonempty_lines(pl)
                valid_lens = [plan_len[v] for v in VALID_VARIANTS if v in plan_len]
                ref_len = min(valid_lens) if valid_lens else None
                instances[f"{dom}/{prob}"] = {
                    "track": track,
                    "obj_count": obj_count(pf),
                    "plan_len": plan_len,
                    "ref_len": ref_len,
                }
    return {"instances": instances, "domain_track": domain_track}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None,
                    help="write regenerated meta JSON here")
    ap.add_argument("--check", type=Path, default=None,
                    help="hard-assert the regenerated meta equals this existing file")
    args = ap.parse_args()

    meta = build_instances()
    n_inst = len(meta["instances"])
    n_cells = sum(len(v["plan_len"]) for v in meta["instances"].values())
    print(f"built {n_inst} instances, {n_cells} plan_len cells, "
          f"{len(meta['domain_track'])} domains", file=sys.stderr)

    if args.check is not None:
        oracle = json.loads(args.check.read_text())
        if meta == oracle:
            print(f"OK: regenerated meta matches {args.check} exactly", file=sys.stderr)
        else:
            # surface the first few diffs to make a mismatch actionable
            diffs = []
            oi = oracle.get("instances", {})
            mi = meta["instances"]
            for k in sorted(set(oi) | set(mi)):
                if oi.get(k) != mi.get(k):
                    diffs.append((k, oi.get(k), mi.get(k)))
            print(f"MISMATCH: {len(diffs)} instance(s) differ", file=sys.stderr)
            for k, o, m in diffs[:8]:
                print(f"  {k}: oracle={o} regen={m}", file=sys.stderr)
            return 1

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(meta, indent=1) + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
