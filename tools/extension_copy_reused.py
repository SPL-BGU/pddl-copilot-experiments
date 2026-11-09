#!/usr/bin/env python3
"""Copy reused rerun rows into the extension's own results folder, with provenance.

Decided 2026-11-09 (Omer, D1b storage): the extension gets a NEW sweep folder.
Rerun rows it reuses are copied in, and every copied row keeps fields naming
where it came from. `results/delivered-rerun/` and `results/sweep5v2-live/`
stay the frozen sources and are never written. A rerun is not identical to the
original run (the 35B finding), so reused rows must stay identifiable.

What it does

* Reads one source `trials.jsonl` (opened read-only, never written).
* Keeps the rows whose resume key matches the cell filter: model, task(s),
  arm (`tools` / `no-tools`), and prompt variant(s).
* Writes `<dest>/trials.jsonl`: each kept row is the source line byte for
  byte, with four top-level fields added before its closing brace:

      reused_from_folder   the source cell folder (repo-relative when inside the repo)
      reused_from_job      the SLURM job id(s) of the source cell, as given
      reused_from_sha256   sha256 of the source trials.jsonl as read
      copied_at            the timestamp passed with --copied-at

  The fields sit next to `key` and `result`, not inside `result`: the harness
  resume loader (`pddl_eval/resume.py`) rebuilds `TaskResult(**result)` and
  would refuse unknown fields there, while it ignores extra top-level ones.
  So `run_experiment.py --output-dir <dest>` treats the copied rows as done
  trials and appends only the new ones. A row with no `reused_from_*` field
  is a new trial of the extension.
* Writes `<dest>/reuse_provenance.json`: source, hashes, filter, counts, and
  the sha256 of the written trials.jsonl, for the prereg's reuse declaration.

Where the job id comes from. The run's summary and single-task JSON (`meta`)
do not store the SLURM job id, and neither does `trials.jsonl`. The ids of the
delivered rerun are in `development/reference/delivered_rerun_prereg.md` §8
(job IDs row; the 9B no-tools cell was resumed once, §8c). So the job id is a
required argument. If the source cell's `summary_*.json` meta ever carries a
job id (`slurm_job_id` or `job_id`), it must equal the one given.

Refusals: the destination is inside a frozen corpus (`delivered-rerun`,
`sweep5v2-live`, `sweep6-live`, `*_sweep6`), or is the source folder;
`<dest>/trials.jsonl` or `<dest>/reuse_provenance.json` already exists (never
overwrite); the source has an unreadable line or a key of the wrong length;
the filter keeps no row.

Proposed destination: `results/extension-live/<cell>/`, one folder per cell,
named like the source cell. Do not run this on real data before the
extension's prereg declares the reuse.

    .venv/bin/python tools/extension_copy_reused.py \\
        --source results/delivered-rerun/<cell>/trials.jsonl \\
        --source-job 21982370 \\
        --model cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit --task solve --arm tools \\
        --variant 11 12 13 14 15 16 \\
        --dest results/extension-live/<cell> \\
        --copied-at 2026-11-09T12:00:00Z
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Resume-key positions (pddl_eval/runner.py `_trial_key`, 10-tuple).
KEY_LEN = 10
K_MODEL, K_TASK, K_PV, K_WITH_TOOLS = 0, 1, 5, 6

PROTECTED_NAMES = ("delivered-rerun", "sweep5v2-live", "sweep6-live")
PROTECTED_SUFFIXES = ("_sweep6",)
PROVENANCE_FIELDS = ("reused_from_folder", "reused_from_job", "reused_from_sha256",
                     "copied_at")
SIDECAR = "reuse_provenance.json"


class Refuse(SystemExit):
    """Raised for every refusal; the message says why."""


def _is_protected(path: Path) -> str | None:
    for part in (path, *path.parents):
        name = part.name
        if name in PROTECTED_NAMES or any(name.endswith(s) for s in PROTECTED_SUFFIXES):
            return str(part)
    return None


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _check_timestamp(s: str) -> str:
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise Refuse(f"--copied-at {s!r} is not an ISO 8601 timestamp")
    return s


def _summary_job_ids(cell_dir: Path) -> set[str]:
    """Job ids recorded in the source cell's summary meta, if any (none today)."""
    out: set[str] = set()
    for f in sorted(cell_dir.glob("summary_*.json")):
        try:
            meta = json.loads(f.read_text()).get("meta") or {}
        except (json.JSONDecodeError, AttributeError):
            continue
        for k in ("slurm_job_id", "job_id"):
            if meta.get(k) not in (None, ""):
                out.add(str(meta[k]))
    return out


def with_provenance(line: str, fields: dict) -> str:
    """The source line byte for byte, with `fields` added before its closing
    brace, so the copied row is the original record plus the new fields."""
    body = line.rstrip()
    if not body.endswith("}"):
        raise Refuse("a trial record does not end with '}'")
    extra = json.dumps(fields)
    return body[:-1] + ", " + extra[1:]


def row_matches(key: list, *, model: str, tasks: set[str], arm: str,
                variants: set[int]) -> bool:
    with_tools = arm == "tools"
    return (key[K_MODEL] == model and key[K_TASK] in tasks
            and bool(key[K_WITH_TOOLS]) is with_tools and int(key[K_PV]) in variants)


def copy_reused(*, source: Path, source_job: str, model: str, tasks: list[str], arm: str,
                variants: list[int], dest: Path, copied_at: str) -> dict:
    source, dest = source.resolve(), dest.resolve()
    if source.name != "trials.jsonl" or not source.is_file():
        raise Refuse(f"--source must be an existing trials.jsonl, got {source}")
    if arm not in ("tools", "no-tools"):
        raise Refuse(f"--arm must be tools or no-tools, got {arm!r}")
    if not source_job.strip():
        raise Refuse("--source-job is empty")
    copied_at = _check_timestamp(copied_at)
    hit = _is_protected(dest)
    if hit:
        raise Refuse(f"destination {dest} is inside the frozen corpus {hit}")
    if dest == source.parent or dest in source.parents or source.parent in dest.parents:
        raise Refuse(f"destination {dest} is the source folder, contains it, or is inside it")
    out_path, side_path = dest / "trials.jsonl", dest / SIDECAR
    for p in (out_path, side_path):
        if p.exists():
            raise Refuse(f"{p} exists; this tool never overwrites")

    recorded = _summary_job_ids(source.parent)
    if recorded and recorded != {source_job}:
        raise Refuse(f"--source-job {source_job} differs from the job id(s) {sorted(recorded)} "
                     f"in the source summary meta")

    raw = source.read_bytes()             # one read: the hash is of exactly what is copied
    src_sha = hashlib.sha256(raw).hexdigest()
    folder = _display(source.parent)
    tasks_set, variants_set = set(tasks), {int(v) for v in variants}
    kept: list[str] = []
    seen: set[tuple] = set()
    n_rows = n_dup = 0
    for i, line in enumerate(raw.decode("utf-8").split("\n"), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            key = rec["key"]
            rec["result"]
        except (json.JSONDecodeError, KeyError, TypeError):
            raise Refuse(f"{source}:{i} is not a complete trial record; refusing to copy")
        if not isinstance(key, list) or len(key) != KEY_LEN:
            raise Refuse(f"{source}:{i} key has the wrong shape (expected {KEY_LEN} fields)")
        clash = [f for f in PROVENANCE_FIELDS if f in rec]
        if clash:
            raise Refuse(f"{source}:{i} already carries {clash}; copy from the original source")
        n_rows += 1
        if not row_matches(key, model=model, tasks=tasks_set, arm=arm, variants=variants_set):
            continue
        if tuple(key) in seen:            # the resume loader keeps the first one too
            n_dup += 1
            continue
        seen.add(tuple(key))
        kept.append(with_provenance(line, {
            "reused_from_folder": folder, "reused_from_job": source_job,
            "reused_from_sha256": src_sha, "copied_at": copied_at}))
    if not kept:
        raise Refuse("the filter keeps no row of the source")

    text = "\n".join(kept) + "\n"
    dest.mkdir(parents=True, exist_ok=True)
    with out_path.open("x") as f:         # "x": fail rather than overwrite
        f.write(text)
    record = {
        "what": "rows reused from an earlier run, copied by tools/extension_copy_reused.py",
        "source_trials": _display(source), "source_folder": folder,
        "source_sha256": src_sha, "source_job": source_job,
        "source_rows": n_rows, "copied_rows": len(kept), "duplicate_keys_skipped": n_dup,
        "filter": {"model": model, "tasks": sorted(tasks_set), "arm": arm,
                   "variants": sorted(variants_set)},
        "copied_at": copied_at,
        "dest_trials_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with side_path.open("x") as f:
        f.write(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return record


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", type=Path, required=True, help="source trials.jsonl (read only)")
    ap.add_argument("--source-job", required=True,
                    help="SLURM job id(s) of the source cell (prereg §8), e.g. 21982370")
    ap.add_argument("--model", required=True, help="model tag as in the resume key")
    ap.add_argument("--task", nargs="+", required=True, help="task(s) to copy")
    ap.add_argument("--arm", required=True, choices=("tools", "no-tools"))
    ap.add_argument("--variant", nargs="+", type=int, required=True, help="prompt variant(s)")
    ap.add_argument("--dest", type=Path, required=True,
                    help="new cell folder, e.g. results/extension-live/<cell>")
    ap.add_argument("--copied-at", required=True, help="ISO 8601 timestamp, recorded as given")
    a = ap.parse_args(argv)
    rec = copy_reused(source=a.source, source_job=a.source_job, model=a.model, tasks=a.task,
                      arm=a.arm, variants=a.variant, dest=a.dest, copied_at=a.copied_at)
    print(json.dumps(rec, indent=1, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
