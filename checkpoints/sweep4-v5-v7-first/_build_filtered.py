"""Filter sweep-4 trials.jsonl to prompt_variant ∈ {5,6,7} and regenerate
summary + single_task per cell, into a synthetic results root.

Examples:
  # Single model (default behavior, qwen0.8B):
  python _build_filtered.py

  # Multiple models into one combined root, skip cells below 4560 v5/v6/v7:
  python _build_filtered.py \
      --dst sweep4-v5-v7-first \
      --model-glob 'slurm_vllm_Qwen3_5_0_8B_*,slurm_vllm_qwen3_6_35b_*' \
      --min-out 4560

Reads:  results/<--src>/<cell>/trials.jsonl
Writes: results/<--dst>/<cell>/{trials.jsonl, summary_*.json, single_task_*.json}
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pddl_eval.summary import summarize_single_task  # noqa: E402
from pddl_eval.runner import TaskResult  # noqa: E402

ACTIVE = {5, 6, 7}


def _trial_to_task_result(t: dict) -> TaskResult:
    r = t["result"]
    # TaskResult expects the exact dataclass fields; drop unknown keys.
    allowed = set(TaskResult.__dataclass_fields__.keys())
    kept = {k: v for k, v in r.items() if k in allowed}
    # Rename legacy keys we know about (none currently — schema is stable).
    return TaskResult(**kept)


def filter_cell(src_dir: Path, dst_dir: Path) -> tuple[int, int]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    kept_trials: list[TaskResult] = []
    n_in = n_out = 0
    out_lines: list[str] = []
    with (src_dir / "trials.jsonl").open() as f:
        for line in f:
            n_in += 1
            t = json.loads(line)
            pv = t["result"].get("prompt_variant")
            if pv not in ACTIVE:
                continue
            n_out += 1
            kept_trials.append(_trial_to_task_result(t))
            out_lines.append(line.rstrip("\n"))
    (dst_dir / "trials.jsonl").write_text("\n".join(out_lines) + ("\n" if out_lines else ""))

    ts = time.strftime("%Y%m%d_%H%M%S")
    # single_task_*.json: per-trial dicts. plot.py reads this for per-domain figs.
    (dst_dir / f"single_task_{ts}.json").write_text(
        json.dumps([asdict(r) for r in kept_trials], indent=2)
    )

    # Carry meta from the latest source summary if any (host, etc).
    src_meta = {}
    for sf in sorted(src_dir.glob("summary_*.json"))[::-1]:
        try:
            src_meta = json.loads(sf.read_text()).get("meta", {})
            break
        except Exception:
            continue

    rows = summarize_single_task(kept_trials)
    summary = {
        "single_task": rows,
        "chains": [],
        "meta": {
            **src_meta,
            "filtered_from": str(src_dir.relative_to(REPO)),
            "filter": "prompt_variant in {5,6,7}",
            "source_n_trials": n_in,
            "filtered_n_trials": n_out,
        },
    }
    (dst_dir / f"summary_{ts}.json").write_text(json.dumps(summary, indent=2))
    return n_in, n_out


# Cells to skip: per-task tools and guided prompt style are retired axes
# (per-task → sweep-5 retirement; guided → already disabled in code). They
# pollute the filtered corpus when present in the source dir.
_RETIRED_COND_SUBSTRINGS = ("per-task", "guided")


def _is_retired(cell_name: str) -> bool:
    return any(s in cell_name for s in _RETIRED_COND_SUBSTRINGS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="sweep4-cluster-20260519",
                   help="results subdir name (under results/)")
    p.add_argument("--dst", default="sweep4-v5-v7-first-qwen0_8B",
                   help="output results subdir name (under results/)")
    p.add_argument("--model-glob", default="slurm_vllm_Qwen3_5_0_8B_*",
                   help="comma-separated globs matching cells to filter")
    p.add_argument("--min-out", type=int, default=0,
                   help="skip cells where n_out (v5+v6+v7 trials) is below this "
                        "threshold; useful for restricting to completed cells "
                        "(typical: 4560 = 3 variants × 1520 trials/variant)")
    args = p.parse_args()
    src_root = REPO / "results" / args.src
    dst_root = REPO / "results" / args.dst
    dst_root.mkdir(parents=True, exist_ok=True)

    globs = [g.strip() for g in args.model_glob.split(",") if g.strip()]
    cell_set: set[str] = set()
    for g in globs:
        for d in src_root.glob(g):
            if d.is_dir() and not _is_retired(d.name):
                cell_set.add(d.name)
    cells = sorted(cell_set)
    if not cells:
        sys.exit(f"no cells matched {args.model_glob!r} under {src_root}")

    print(f"Filtering trials → prompt_variant ∈ {sorted(ACTIVE)}")
    print(f"Source: {src_root.relative_to(REPO)}")
    print(f"Dest:   {dst_root.relative_to(REPO)}")
    print(f"Model globs: {globs}  (retired-axis cells excluded)")
    if args.min_out:
        print(f"Skip threshold: n_out < {args.min_out}")
    print()
    total_in = total_out = 0
    n_written = n_skipped = 0
    print(f"{'cell':<55} {'n_in':>7} {'n_out':>7} {'status':<10}")
    print("-" * 86)
    for c in cells:
        src = src_root / c
        dst = dst_root / c
        # Count first to decide whether to write at all.
        n_in_probe = sum(1 for _ in (src / "trials.jsonl").open())
        n_out_probe = sum(1 for line in (src / "trials.jsonl").open()
                          if json.loads(line)["result"].get("prompt_variant") in ACTIVE)
        status = "WRITE"
        if args.min_out and n_out_probe < args.min_out:
            status = f"skip<{args.min_out}"
            n_skipped += 1
            print(f"{c:<55} {n_in_probe:>7} {n_out_probe:>7} {status:<10}")
            continue
        n_in, n_out = filter_cell(src, dst)
        total_in += n_in
        total_out += n_out
        n_written += 1
        print(f"{c:<55} {n_in:>7} {n_out:>7} {status:<10}")
    print("-" * 86)
    print(f"{'TOTAL (written):':<55} {total_in:>7} {total_out:>7} "
          f"({n_written} cells, {n_skipped} skipped)")


if __name__ == "__main__":
    main()
