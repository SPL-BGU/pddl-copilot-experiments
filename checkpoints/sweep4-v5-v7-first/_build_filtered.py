"""One-off: filter sweep-4 qwen0.8B trials.jsonl to prompt_variant ∈ {5,6,7}
and regenerate summary_*.json per cell, into a synthetic results root.

Reads:  results/sweep4-cluster-20260519/slurm_vllm_Qwen3_5_0_8B_*/trials.jsonl
Writes: results/sweep4-v5-v7-first-qwen0_8B/<same dir>/trials.jsonl + summary_*.json
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
                   help="glob matching the cells to filter (default: qwen0.8B vLLM)")
    args = p.parse_args()
    src_root = REPO / "results" / args.src
    dst_root = REPO / "results" / args.dst
    dst_root.mkdir(parents=True, exist_ok=True)

    cells = sorted(d.name for d in src_root.glob(args.model_glob)
                   if d.is_dir() and not _is_retired(d.name))
    if not cells:
        sys.exit(f"no cells matched {args.model_glob!r} under {src_root}")

    print(f"Filtering trials → prompt_variant ∈ {sorted(ACTIVE)}")
    print(f"Source: {src_root.relative_to(REPO)}")
    print(f"Dest:   {dst_root.relative_to(REPO)}")
    print(f"Model glob: {args.model_glob}  (retired-axis cells excluded)")
    print()
    total_in = total_out = 0
    print(f"{'cell':<55} {'n_in':>7} {'n_out':>7}")
    print("-" * 75)
    for c in cells:
        src = src_root / c
        dst = dst_root / c
        n_in, n_out = filter_cell(src, dst)
        total_in += n_in
        total_out += n_out
        print(f"{c:<55} {n_in:>7} {n_out:>7}")
    print("-" * 75)
    print(f"{'TOTAL':<55} {total_in:>7} {total_out:>7}")


if __name__ == "__main__":
    main()
