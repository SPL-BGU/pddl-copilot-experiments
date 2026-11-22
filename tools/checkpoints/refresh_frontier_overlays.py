#!/usr/bin/env python3
"""Refresh the frontier overlay zips and build the checkpoints/frontier/ backup.

Run this on the laptop, from the main checkout, where the 2026-09-12 frontier
files live. It only READS results/. It writes zips under checkpoints/ (or under
--out), and only when you pass --write.

What it builds (decision 16 of development/handoff_20261109.md):

  checkpoints/e2e-overlay/haiku-frontier_overlay.zip    the Haiku overlay, 09-12 files
  checkpoints/e2e-overlay/sonnet-frontier_overlay.zip   the Sonnet overlay, 09-12 files
  checkpoints/e2e-overlay/derived_reports.zip           pooled table (09-12), the
                                                        iss024d parity report, the two
                                                        budget-probe readouts
  checkpoints/frontier/<tier>-frontier_<cell>.zip       one zip per raw frontier cell
                                                        that git does not track

Safety rules:
  * Without --write it only checks the inputs and prints the plan.
  * If any input is missing it builds nothing (no partial set).
  * It refuses to replace an existing zip unless you pass --force.
  * It refuses an --out folder inside results/.
  * All zips are built in a temp folder first and moved into place only when
    every zip built and passed the size check.

The zips are deterministic: entries are sorted, each entry has fixed
permissions, and its time is the file's modification time in UTC (or
1980-01-01 with --fixed-time). The same files give the same sha256 on the same
Python/zlib build.

Usage (from the repo root):
  python3 tools/checkpoints/refresh_frontier_overlays.py            # check only
  python3 tools/checkpoints/refresh_frontier_overlays.py --write --out /tmp/ck
  python3 tools/checkpoints/refresh_frontier_overlays.py --write --force
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys
import tempfile
import time
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

TIERS = ("haiku", "sonnet")

# Overlay files each refreshed zip must hold. The first group is what the
# 2026-07-17 zips already hold; the *-budget64k files come from the 09-12
# budget probe. Any other *.e2e.jsonl in the folder is added too.
OVERLAY_REQUIRED = {
    "haiku": ["sweep5v2", "sweep6", "sweep5v2-with-tools", "sweep6-with-tools",
              "sweep5v2-budget64k", "sweep5v2-with-tools-budget64k"],
    "sonnet": ["sweep5v2", "sweep6", "sweep5v2-with-tools",
               "sweep5v2-budget64k", "sweep5v2-with-tools-budget64k"],
}

# Raw frontier cells that git does not track (results/ is gitignored; only
# haiku sweep5v2, sonnet sweep5v2/sweep6 and the planbench folders are
# force-added). These go into checkpoints/frontier/.
RAW_CELLS = {
    "haiku": ["sweep6", "sweep5v2-with-tools", "sweep6-with-tools",
              "sweep5v2-budget64k", "sweep5v2-with-tools-budget64k"],
    "sonnet": ["sweep5v2-with-tools",
               "sweep5v2-budget64k", "sweep5v2-with-tools-budget64k"],
}
# Folders under results/<tier>-frontier/ that are already in git.
TRACKED_CELLS = {"haiku": {"sweep5v2", "planbench"},
                 "sonnet": {"sweep5v2", "sweep6"}}

# derived_reports.zip members, as paths relative to results/derived/ (so the
# restore is a single `unzip -d results/derived/`).
DERIVED_MEMBERS = [
    "e2e_overlay/pooled_e2e_table.md",
    "e2e_overlay/pooled_e2e_table.csv",
    "iss024d_parity_report.md",
    "budget_probe/readout_sonnet.json",
    "budget_probe/readout_haiku.json",
]

# The pooled table only has its 460 rows when these overlay corpora are in
# the overlay root (handoff decision 16). Their absence is reported.
KEEP_CORPORA = ("sweep7", "frontier-with-tools-probe")

SKIP_NAMES = {".DS_Store", "__pycache__"}
GITHUB_HARD_LIMIT = 100 * 1024 * 1024
GITHUB_WARN_LIMIT = 50 * 1024 * 1024
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _zip_time(path: Path, fixed: bool) -> tuple:
    if fixed:
        return FIXED_TIME
    t = time.gmtime(int(path.stat().st_mtime) // 2 * 2)
    stamp = (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    return max(stamp, FIXED_TIME)


def _walk(folder: Path) -> list[Path]:
    """Every file under folder, sorted, skipping OS junk."""
    out = []
    for p in sorted(folder.rglob("*")):
        if any(part in SKIP_NAMES for part in p.relative_to(folder).parts):
            continue
        if p.is_file():
            out.append(p)
    return out


def plan(repo: Path) -> tuple[list[dict], list[str], list[str]]:
    """Return (zip specs, missing inputs, notes). Reads only."""
    res = repo / "results"
    ovl = res / "derived" / "e2e_overlay"
    specs, missing, notes = [], [], []

    for tier in TIERS:
        src = ovl / f"{tier}-frontier"
        if not src.is_dir():
            missing.append(f"{src.relative_to(repo)}/ (overlay folder)")
            continue
        for stem in OVERLAY_REQUIRED[tier]:
            f = src / f"{stem}.e2e.jsonl"
            if not f.is_file():
                missing.append(str(f.relative_to(repo)))
        files = sorted(src.glob("*.e2e.jsonl"))
        extra = [p.name for p in files
                 if p.name[: -len(".e2e.jsonl")] not in OVERLAY_REQUIRED[tier]]
        if extra:
            notes.append(f"{tier} overlay: also adding {', '.join(extra)}")
        other = [p.name for p in sorted(src.iterdir())
                 if p.is_file() and not p.name.endswith(".e2e.jsonl")
                 and p.name not in SKIP_NAMES]
        if other:
            notes.append(f"{tier} overlay: NOT adding non-overlay files "
                         f"{', '.join(other)}")
        specs.append({
            "target": Path("e2e-overlay") / f"{tier}-frontier_overlay.zip",
            "dir_entry": f"{tier}-frontier/",
            "members": [(f"{tier}-frontier/{p.name}", p) for p in files],
        })

    derived = res / "derived"
    members = []
    for rel in DERIVED_MEMBERS:
        p = derived / rel
        if not p.is_file():
            missing.append(str(p.relative_to(repo)))
        members.append((rel, p))
    specs.append({"target": Path("e2e-overlay") / "derived_reports.zip",
                  "dir_entry": None, "members": members})

    for tier in TIERS:
        base = res / f"{tier}-frontier"
        for cell in RAW_CELLS[tier]:
            src = base / cell
            if not src.is_dir():
                missing.append(f"{src.relative_to(repo)}/ (raw cell)")
                continue
            files = _walk(src)
            if not any(p.name == "trials.jsonl" for p in files):
                missing.append(f"{src.relative_to(repo)}/**/trials.jsonl")
            specs.append({
                "target": Path("frontier") / f"{tier}-frontier_{cell}.zip",
                "dir_entry": None,
                "members": [(f"{tier}-frontier/{cell}/"
                             f"{p.relative_to(src).as_posix()}", p)
                            for p in files],
            })
        if base.is_dir():
            known = set(RAW_CELLS[tier]) | TRACKED_CELLS[tier]
            unknown = [p.name for p in sorted(base.iterdir())
                       if p.is_dir() and p.name not in known]
            if unknown:
                notes.append(f"results/{tier}-frontier/ has folders this script "
                             f"does not back up: {', '.join(unknown)}")

    for corpus in KEEP_CORPORA:
        if not (ovl / corpus).is_dir():
            notes.append(f"overlay root has no {corpus}/ — the pooled table "
                         "will not have its 460 rows if rebuilt from it")
    return specs, missing, notes


def pooled_summary(repo: Path) -> str | None:
    csv_path = repo / "results/derived/e2e_overlay/pooled_e2e_table.csv"
    if not csv_path.is_file():
        return None
    with csv_path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    per = Counter(r["corpus"] for r in rows)
    lines = [f"pooled_e2e_table.csv: {len(rows)} data rows"]
    lines += [f"  {c}: {n}" for c, n in sorted(per.items())]
    return "\n".join(lines)


def build_zip(spec: dict, dest: Path, fixed_time: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        if spec["dir_entry"]:
            src_dir = spec["members"][0][1].parent if spec["members"] else None
            zi = zipfile.ZipInfo(
                spec["dir_entry"],
                _zip_time(src_dir, fixed_time) if src_dir else FIXED_TIME)
            zi.create_system = 3
            zi.external_attr = (0o40755 << 16) | 0x10
            zf.writestr(zi, b"")
        for arcname, path in sorted(spec["members"]):
            zi = zipfile.ZipInfo(arcname, _zip_time(path, fixed_time))
            zi.create_system = 3
            zi.external_attr = 0o100644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, path.read_bytes(), compresslevel=9)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=REPO,
                    help="repo root holding results/ (default: this checkout)")
    ap.add_argument("--out", type=Path, default=None,
                    help="where the zips go (default: <repo>/checkpoints)")
    ap.add_argument("--write", action="store_true",
                    help="build the zips (default: check inputs only)")
    ap.add_argument("--force", action="store_true",
                    help="replace zips that already exist")
    ap.add_argument("--fixed-time", action="store_true",
                    help="stamp every entry 1980-01-01 instead of its mtime")
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    out = (args.out or repo / "checkpoints").resolve()
    results = (repo / "results").resolve()
    if out == results or results in out.parents:
        print(f"refusing: --out {out} is inside results/", file=sys.stderr)
        return 2

    specs, missing, notes = plan(repo)
    for n in notes:
        print(f"note: {n}")
    summary = pooled_summary(repo)
    if summary:
        print(summary)
    if missing:
        print("\nmissing inputs (nothing built):", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1

    print("\nplan:")
    for s in specs:
        size = sum(p.stat().st_size for _, p in s["members"])
        print(f"  {s['target']}  {len(s['members'])} files, "
              f"{size / 1e6:.1f} MB raw")
    existing = [s["target"] for s in specs if (out / s["target"]).exists()]
    if not args.write:
        if existing:
            print(f"\n{len(existing)} target(s) already exist; "
                  "--write needs --force to replace them")
        print("\ncheck only; pass --write to build")
        return 0
    if existing and not args.force:
        print("\nrefusing to replace existing zips without --force:",
              file=sys.stderr)
        for t in existing:
            print(f"  {out / t}", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".refresh-", dir=out))
    try:
        for s in specs:
            build_zip(s, stage / s["target"], args.fixed_time)
        too_big = [s["target"] for s in specs
                   if (stage / s["target"]).stat().st_size > GITHUB_HARD_LIMIT]
        if too_big:
            print("\nrefusing: over GitHub's 100 MB file limit (nothing "
                  "moved into place):", file=sys.stderr)
            for t in too_big:
                print(f"  {t}", file=sys.stderr)
            return 1
        for s in specs:
            dest = out / s["target"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / s["target"], dest)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    print("\nbuilt:")
    total = 0
    sums = []
    for s in specs:
        dest = out / s["target"]
        size = dest.stat().st_size
        total += size
        flag = "  (over 50 MB: GitHub warns)" if size > GITHUB_WARN_LIMIT else ""
        print(f"  {s['target']}  {size / 1e6:.1f} MB{flag}")
        sums.append(f"{sha256(dest)}  {s['target'].as_posix()}")
    print(f"  total {total / 1e6:.1f} MB")
    print("\nsha256 (paths relative to the --out folder):")
    print("\n".join(sums))
    return 0


if __name__ == "__main__":
    sys.exit(main())
