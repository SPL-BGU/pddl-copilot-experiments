"""Filter trials.jsonl to a chosen prompt-variant set and regenerate
summary_*.json + single_task_*.json per cell, into a synthetic results root.

Promoted from checkpoints/sweep4-v5-v7-first/_build_filtered.py — same semantics,
plus a `--variants` flag so future sweeps can pick their own variant set.

Examples:
  # Sweep-4 single model (default variants 5,6,7):
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep4-cluster-20260519 --dst sweep4-v5-v7-first-qwen0_8B \\
      --model-glob 'slurm_vllm_Qwen3_5_0_8B_*'

  # Sweep-4 multi-model into one root, gate on completed cells (4560 trials):
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep4-cluster-20260519 --dst sweep4-v5-v7-first \\
      --model-glob 'slurm_vllm_Qwen3_5_0_8B_*,slurm_vllm_qwen3_6_35b_*' \\
      --min-out 4560

  # Future sweep with a different variant set:
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep5-cluster-20260601 --dst sweep5-v8-v10 \\
      --model-glob 'slurm_vllm_*' --variants 8,9,10 --min-out 4560

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

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from pddl_eval.summary import summarize_single_task  # noqa: E402
from pddl_eval.runner import TaskResult  # noqa: E402


def _trial_to_task_result(t: dict) -> TaskResult:
    r = t["result"]
    allowed = set(TaskResult.__dataclass_fields__.keys())
    kept = {k: v for k, v in r.items() if k in allowed}
    return TaskResult(**kept)


def filter_cell(src_dir: Path, dst_dir: Path, active: set[int]) -> tuple[int, int]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    kept_trials: list[TaskResult] = []
    n_in = n_out = 0
    out_lines: list[str] = []
    with (src_dir / "trials.jsonl").open() as f:
        for line in f:
            n_in += 1
            t = json.loads(line)
            pv = t["result"].get("prompt_variant")
            if pv not in active:
                continue
            n_out += 1
            kept_trials.append(_trial_to_task_result(t))
            out_lines.append(line.rstrip("\n"))
    (dst_dir / "trials.jsonl").write_text("\n".join(out_lines) + ("\n" if out_lines else ""))

    ts = time.strftime("%Y%m%d_%H%M%S")
    (dst_dir / f"single_task_{ts}.json").write_text(
        json.dumps([asdict(r) for r in kept_trials], indent=2)
    )

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
            "filter": f"prompt_variant in {sorted(active)}",
            "source_n_trials": n_in,
            "filtered_n_trials": n_out,
        },
    }
    (dst_dir / f"summary_{ts}.json").write_text(json.dumps(summary, indent=2))
    return n_in, n_out


# Cells to skip: per-task tools and guided prompt style are retired axes
# (per-task → sweep-5 retirement; guided → already disabled in code).
_RETIRED_COND_SUBSTRINGS = ("per-task", "guided")


def _is_retired(cell_name: str) -> bool:
    return any(s in cell_name for s in _RETIRED_COND_SUBSTRINGS)


def _parse_variants(s: str) -> set[int]:
    try:
        return {int(x.strip()) for x in s.split(",") if x.strip()}
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"--variants must be comma-separated ints, got {s!r}") from e


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--src", required=True,
                   help="results subdir name (under results/) of the synced cluster dump")
    p.add_argument("--dst", required=True,
                   help="output results subdir name (under results/) for the filtered corpus")
    p.add_argument("--model-glob", required=True,
                   help="comma-separated globs matching cells to filter, "
                        "e.g. 'slurm_vllm_Qwen3_5_0_8B_*,slurm_vllm_qwen3_6_35b_*'")
    p.add_argument("--variants", type=_parse_variants, default={5, 6, 7},
                   help="comma-separated prompt_variant ids to keep (default: 5,6,7 = sweep-4)")
    p.add_argument("--min-out", type=int, default=0,
                   help="skip cells where n_out (kept-variant trials) is below this "
                        "threshold; useful for restricting to completed cells "
                        "(typical: 4560 = 3 variants × 1520 trials/variant for sweep-4)")
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

    print(f"Filtering trials → prompt_variant ∈ {sorted(args.variants)}")
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
        n_in_probe = sum(1 for _ in (src / "trials.jsonl").open())
        n_out_probe = sum(1 for line in (src / "trials.jsonl").open()
                          if json.loads(line)["result"].get("prompt_variant") in args.variants)
        status = "WRITE"
        if args.min_out and n_out_probe < args.min_out:
            status = f"skip<{args.min_out}"
            n_skipped += 1
            print(f"{c:<55} {n_in_probe:>7} {n_out_probe:>7} {status:<10}")
            continue
        n_in, n_out = filter_cell(src, dst, args.variants)
        total_in += n_in
        total_out += n_out
        n_written += 1
        print(f"{c:<55} {n_in:>7} {n_out:>7} {status:<10}")
    print("-" * 86)
    print(f"{'TOTAL (written):':<55} {total_in:>7} {total_out:>7} "
          f"({n_written} cells, {n_skipped} skipped)")


if __name__ == "__main__":
    main()
