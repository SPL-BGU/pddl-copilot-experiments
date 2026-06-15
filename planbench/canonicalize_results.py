#!/usr/bin/env python3
"""Canonicalize / de-duplicate the PlanBench per-job results store.

Why this exists
---------------
Every PlanBench sbatch (``run_planbench{,_tools}_rtx.sbatch``) finishes by
rsyncing the *entire shared* ``plan-bench/results/`` (and ``responses/``)
accumulator into its own per-job output dir::

    rsync -a "$PLANBENCH_ROOT/plan-bench/results/" "$OUT_DIR/results/"

That accumulator is one directory reused by every job on the cluster checkout,
so each job's snapshot contains EVERY engine ever run there — even though the
job itself only generated ONE engine (its ``manifest.engine``). Net effect:

  * the SAME (config, engine, task) corpus is copied into up to 50 job dirs
    (old engines like ``vllm__Qwen3.5:0.8B`` and the shipped ``gpt-4_chat`` /
    ``text-davinci-002`` baselines sit in all 50);
  * ``results/planbench`` balloons to ~5.9 GB of mostly-identical copies;
  * a naive ``slurm_*/results/**/task_*.json`` glob double-counts each model.

It is NOT duplicated compute — ``manifest.json`` proves one engine per job and
the staggered, rsync-preserved mtimes prove the foreign subdirs are copies, not
re-runs. This tool fixes the *storage / analysis* fallout, not a compute bug.

Canonical-copy rule
-------------------
Group every file by ``(namespace, config, engine, relpath)`` where namespace is
``results`` or ``responses``. Within a group the canonical copy is the one with
the newest mtime; ``rsync -a`` preserves the source generation time, so the
newest copy is the freshest content (this is also what resolves the two-epoch
case — a corpus that was regenerated once across the sweep). All other copies
in the group are byte-identical-or-older duplicates.

  * ``--materialize OUT``  builds a clean ``OUT/<config>/<engine>/task_*.json``
    tree (symlinks by default, ``--copy`` for real files) from the canonical
    copies — feed it straight to ``build_table.py``.
  * ``--prune``            reports the redundant (non-canonical) copies and the
    space they hold; ``--apply`` deletes them. A copy is deleted ONLY when a
    strictly-newer-or-equal-mtime sibling survives, so the freshest generation
    of every distinct file is always kept. ``manifest.json`` and
    ``toolcalls.jsonl`` (unique per job, never duplicated) are never touched.

Usage
-----
    python3 planbench/canonicalize_results.py RESULTS_PLANBENCH_DIR            # report only
    python3 planbench/canonicalize_results.py RESULTS_PLANBENCH_DIR --materialize /tmp/pb_canon
    python3 planbench/canonicalize_results.py RESULTS_PLANBENCH_DIR --materialize /tmp/pb_canon --copy
    python3 planbench/canonicalize_results.py RESULTS_PLANBENCH_DIR --prune            # dry-run
    python3 planbench/canonicalize_results.py RESULTS_PLANBENCH_DIR --prune --apply     # delete

``RESULTS_PLANBENCH_DIR`` is the dir holding ``slurm_*/`` job dirs (e.g.
``results/planbench`` in the experiments repo, on the cluster).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

NAMESPACES = ("results", "responses")


def _human(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            return f"{f:.1f}{unit}" if unit != "B" else f"{int(f)}B"
        f /= 1024
    return f"{f:.1f}TB"


def _job_dirs(root: str) -> list[str]:
    return sorted(
        os.path.join(root, d)
        for d in os.listdir(root)
        if d.startswith("slurm_") and os.path.isdir(os.path.join(root, d))
    )


def _read_manifest(job_dir: str) -> dict:
    p = os.path.join(job_dir, "manifest.json")
    try:
        with open(p) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def scan(root: str):
    """Return (groups, jobs).

    groups maps (namespace, config, engine, relpath) -> list of copy records
        (mtime, is_owner, job_name, size, abspath), one per copy across jobs.
        ``is_owner`` is True when the holding job's manifest.engine == engine
        (i.e. that job actually generated this corpus, vs froze an rsync copy).
    jobs   maps job_dir -> manifest dict (for the provenance report).
    """
    groups: dict[tuple, list] = defaultdict(list)
    jobs: dict[str, dict] = {}
    for job_dir in _job_dirs(root):
        man = _read_manifest(job_dir)
        jobs[job_dir] = man
        man_engine = man.get("engine")
        job_name = os.path.basename(job_dir)
        for ns in NAMESPACES:
            ns_root = os.path.join(job_dir, ns)
            if not os.path.isdir(ns_root):
                continue
            # Layout: <ns>/<config>/<engine>/<relpath...>
            for config in os.listdir(ns_root):
                cfg_dir = os.path.join(ns_root, config)
                if not os.path.isdir(cfg_dir):
                    continue
                for engine in os.listdir(cfg_dir):
                    eng_dir = os.path.join(cfg_dir, engine)
                    if not os.path.isdir(eng_dir):
                        continue
                    for dirpath, _dirs, files in os.walk(eng_dir):
                        for fn in files:
                            ap = os.path.join(dirpath, fn)
                            try:
                                st = os.lstat(ap)
                            except OSError:
                                continue
                            if not os.path.isfile(ap):
                                continue
                            rel = os.path.relpath(ap, eng_dir)
                            groups[(ns, config, engine, rel)].append(
                                (st.st_mtime, man_engine == engine, job_name,
                                 st.st_size, ap)
                            )
    return groups, jobs


# copy record indices
_MTIME, _IS_OWNER, _JOB, _SIZE, _PATH = range(5)


def _canonical(copies: list) -> tuple:
    """Pick the canonical copy.

    Newest mtime wins (rsync -a preserves the generation time, so newest =
    freshest content; this drops stale epochs). Among same-mtime copies of one
    generation prefer an OWNER copy (manifest.engine == engine) so each engine's
    survivor stays in a job that actually ran it, then the lexicographically
    largest job name (== latest job id) for stability.
    """
    return max(copies, key=lambda c: (c[_MTIME], c[_IS_OWNER], c[_JOB]))


def report(root: str, groups: dict, jobs: dict) -> None:
    owned = defaultdict(list)  # engine -> [job_dir...]
    for job_dir, man in jobs.items():
        eng = man.get("engine")
        if eng:
            owned[eng].append(os.path.basename(job_dir))

    total_files = total_bytes = 0
    canon_files = canon_bytes = 0
    dup_per_engine = defaultdict(lambda: [0, 0])  # engine -> [redundant_files, redundant_bytes]
    for (ns, config, engine, rel), copies in groups.items():
        canon = _canonical(copies)
        for c in copies:
            total_files += 1
            total_bytes += c[_SIZE]
        canon_files += 1
        canon_bytes += canon[_SIZE]
        for c in copies:
            if c[_PATH] != canon[_PATH]:
                dup_per_engine[engine][0] += 1
                dup_per_engine[engine][1] += c[_SIZE]

    print(f"job dirs           : {len(jobs)}")
    print(f"distinct files     : {canon_files}  ({_human(canon_bytes)} canonical)")
    print(f"total copies on disk: {total_files}  ({_human(total_bytes)})")
    print(f"reclaimable (dups) : {_human(total_bytes - canon_bytes)}")
    print()
    print("engine                                   owned-by-jobs   redundant-copies")
    print("-" * 78)
    all_engines = sorted(set(list(owned) + list(dup_per_engine)))
    for eng in all_engines:
        n_owners = len(owned.get(eng, []))
        rf, rb = dup_per_engine.get(eng, [0, 0])
        tag = "" if n_owners else "  (UNOWNED/baseline)"
        print(f"{eng:40s} {n_owners:>11d}   {rf:>6d} files {_human(rb):>9s}{tag}")


def materialize(root: str, groups: dict, out: str, copy: bool) -> None:
    import shutil

    made = 0
    for (ns, config, engine, rel), copies in groups.items():
        if ns != "results":
            continue  # build_table.py reads results/ only
        canon = _canonical(copies)
        dst = os.path.join(out, config, engine, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst):
            os.remove(dst)
        if copy:
            shutil.copy2(canon[_PATH], dst)
        else:
            os.symlink(os.path.abspath(canon[_PATH]), dst)
        made += 1
    kind = "copies" if copy else "symlinks"
    print(f"materialized {made} canonical results files as {kind} under {out}")
    print(f"  -> python3 planbench/build_table.py {out}")


def prune(root: str, groups: dict, apply: bool) -> None:
    to_delete: list[tuple[int, str]] = []  # (size, abspath)
    skipped = 0
    for (ns, config, engine, rel), copies in groups.items():
        if len(copies) == 1:
            continue
        canon = _canonical(copies)
        for c in copies:
            if c[_PATH] == canon[_PATH]:
                continue
            # Safety: only delete a copy that is older-or-equal to the survivor.
            # By construction canon has the max mtime, so this always holds; the
            # guard is belt-and-braces against a future selection-rule change.
            if c[_MTIME] <= canon[_MTIME]:
                to_delete.append((c[_SIZE], c[_PATH]))
            else:
                skipped += 1

    total = sum(s for s, _ in to_delete)
    print(f"redundant copies   : {len(to_delete)} files, {_human(total)} reclaimable")
    if skipped:
        print(f"  !! {skipped} copies newer than their group's canonical — SKIPPED (investigate)")
    for size, ap in to_delete[:8]:
        print(f"  would delete  {_human(size):>9s}  {os.path.relpath(ap, root)}")
    if len(to_delete) > 8:
        print(f"  ... and {len(to_delete) - 8} more")

    if not apply:
        print("\n(dry-run; pass --apply to delete)")
        return

    deleted_bytes = deleted_files = 0
    for size, ap in to_delete:
        try:
            os.remove(ap)
            deleted_files += 1
            deleted_bytes += size
        except OSError as exc:
            print(f"  ERROR deleting {ap}: {exc}", file=sys.stderr)
    # Remove dirs left empty by the deletions (deepest-first).
    removed_dirs = 0
    for job_dir in _job_dirs(root):
        for ns in NAMESPACES:
            ns_root = os.path.join(job_dir, ns)
            if not os.path.isdir(ns_root):
                continue
            for dirpath, _dirs, _files in os.walk(ns_root, topdown=False):
                if dirpath == ns_root:
                    continue
                try:
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                        removed_dirs += 1
                except OSError:
                    pass
    print(f"\nDELETED {deleted_files} files, reclaimed {_human(deleted_bytes)}; "
          f"removed {removed_dirs} empty dirs")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="results/planbench dir holding slurm_*/ job dirs")
    ap.add_argument("--materialize", metavar="OUT",
                    help="assemble a clean <config>/<engine>/task_*.json tree for build_table.py")
    ap.add_argument("--copy", action="store_true",
                    help="with --materialize: real copies instead of symlinks")
    ap.add_argument("--prune", action="store_true",
                    help="report redundant copies (dry-run unless --apply)")
    ap.add_argument("--apply", action="store_true",
                    help="with --prune: actually delete the redundant copies")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        sys.exit(f"not a directory: {args.root}")

    groups, jobs = scan(args.root)
    if not groups:
        sys.exit(f"no slurm_*/{{results,responses}}/ files found under {args.root}")

    if args.materialize:
        materialize(args.root, groups, args.materialize, args.copy)
    elif args.prune:
        prune(args.root, groups, args.apply)
    else:
        report(args.root, groups, jobs)


if __name__ == "__main__":
    main()
