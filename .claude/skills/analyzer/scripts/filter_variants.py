"""Filter trials.jsonl to a chosen prompt-variant set and regenerate
summary_*.json + single_task_*.json per cell, into a synthetic results root.

Promoted from checkpoints/sweep4-v5-v7-first/_build_filtered.py — same semantics,
plus a `--variants` flag so future sweeps can pick their own variant set.

Examples:
  # Sweep-5 main checkpoint (default: --arm both = {11..16} full active set;
  # asymmetric per-cell denominators — with-tools cells gate at 9120 trials,
  # no-tools at 4560 — filter arm-by-arm if uniform --min-out matters):
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep5-cluster-20260601 --dst sweep5-main \\
      --model-glob 'slurm_vllm_*'

  # Sweep-5 neutral arm (H1 isolation: tools-vs-no-tools at byte-identical
  # prompt content). 4560 trials/cell completed.
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep5-cluster-20260601 --dst sweep5-neutral \\
      --model-glob 'slurm_vllm_*' --arm neutral --min-out 4560

  # Sweep-5 steered arm (H2 isolation: steering effect within with-tools,
  # AND the 4th-arm control if its --include-no-tools-steered trials have
  # been merged into the no-tools dirs). 4560 trials/cell completed.
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep5-cluster-20260601 --dst sweep5-steered \\
      --model-glob 'slurm_vllm_*' --arm steered --min-out 4560

  # Sweep-4 replay (historical — explicit --variants since --arm presets
  # only encode sweep-5 indices):
  python3 .claude/skills/analyzer/scripts/filter_variants.py \\
      --src sweep4-cluster-20260519 --dst sweep4-v5-v7-first \\
      --model-glob 'slurm_vllm_*' --variants 5,6,7 --min-out 4560

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


def _think_from_dirname(name: str) -> str:
    """Extract think segment from `slurm_vllm_<model>_<think>_<cond>` cell dirs."""
    for tok in ("_on_", "_off_", "_default_"):
        if tok in name:
            return tok.strip("_")
    return ""


def _trial_to_task_result(t: dict) -> TaskResult:
    r = t["result"]
    allowed = set(TaskResult.__dataclass_fields__.keys())
    kept = {k: v for k, v in r.items() if k in allowed}
    return TaskResult(**kept)


def _scan_trials(src_dir: Path, active: set[int]
                 ) -> tuple[int, int, list[str], list[TaskResult]]:
    """Single-pass read of trials.jsonl. Returns (n_in, n_out, kept_lines, kept_trials).
    No write side effects — caller decides whether to skip or commit to disk.

    Malformed lines (partial flushes leaving null-byte blocks; concurrent-
    write tears) are skipped with a stderr warning rather than aborting the
    filter — corruption sits in <0.5% of trials and the rest of the cell is
    still load-bearing. The skipped lines are tallied so the user sees them.
    """
    import sys
    kept_trials: list[TaskResult] = []
    kept_lines: list[str] = []
    n_in = n_out = n_bad = 0
    with (src_dir / "trials.jsonl").open() as f:
        for line in f:
            n_in += 1
            try:
                t = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            try:
                pv = t["result"].get("prompt_variant")
            except (KeyError, AttributeError, TypeError):
                n_bad += 1
                continue
            if pv not in active:
                continue
            n_out += 1
            kept_trials.append(_trial_to_task_result(t))
            kept_lines.append(line.rstrip("\n"))
    if n_bad:
        print(f"  warn: skipped {n_bad} malformed lines in {src_dir.name}/trials.jsonl",
              file=sys.stderr)
    return n_in, n_out, kept_lines, kept_trials


def write_filtered_cell(src_dir: Path, dst_dir: Path,
                        kept_lines: list[str], kept_trials: list[TaskResult],
                        n_in: int, active: set[int]) -> None:
    """Materialize the kept rows + regenerate summary + single_task on disk."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / "trials.jsonl").write_text(
        "\n".join(kept_lines) + ("\n" if kept_lines else "")
    )

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

    # think_mode threads through the relabel for read-time taxonomy fix
    # (FR_TRUNCATED_NO_ANSWER → FR_THINK_OVERFLOW when response was empty
    # and think=on). Prefer the source meta; fall back to the cell dirname.
    think_mode = src_meta.get("think") or _think_from_dirname(src_dir.name)
    rows = summarize_single_task(kept_trials, think_mode=think_mode)
    summary = {
        "single_task": rows,
        "chains": [],
        "meta": {
            **src_meta,
            "filtered_from": str(src_dir.relative_to(REPO)),
            "filter": f"prompt_variant in {sorted(active)}",
            "source_n_trials": n_in,
            "filtered_n_trials": len(kept_lines),
        },
    }
    (dst_dir / f"summary_{ts}.json").write_text(json.dumps(summary, indent=2))


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


# Sweep-5 arm presets. --arm is the ergonomic front door; --variants stays
# available for sweep-4 replay and ad-hoc combinations. The presets match
# STEERED_VARIANTS in pddl_eval/prompts.py and the design doc §0 matrix.
# Declared as frozenset so a future caller that does
# `args.variants.add(...)` can't silently mutate the module-level preset
# (and break the next call within the same process / test session).
_ARM_VARIANTS: dict[str, frozenset[int]] = {
    "neutral": frozenset({11, 12, 13}),  # sweep-5 v11-13 — neutral prompts (H1 floor / with-tools-neutral arm)
    "steered": frozenset({14, 15, 16}),  # sweep-5 v14-16 — steered prompts (H2 / control arm)
    "both":    frozenset({11, 12, 13, 14, 15, 16}),  # sweep-5 full active set
}


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--src", required=True,
                   help="results subdir name (under results/) of the synced cluster dump")
    p.add_argument("--dst", required=True,
                   help="output results subdir name (under results/) for the filtered corpus")
    p.add_argument("--model-glob", required=True,
                   help="comma-separated globs matching cells to filter, "
                        "e.g. 'slurm_vllm_Qwen3_5_0_8B_*,slurm_vllm_qwen3_6_35b_*'")
    p.add_argument("--arm", choices=("neutral", "steered", "both"), default=None,
                   help="sweep-5 arm preset: 'neutral' = {11,12,13} (H1 floor / "
                        "with-tools-neutral), 'steered' = {14,15,16} (H2 / control), "
                        "'both' = {11..16} (full active set). Mutually exclusive "
                        "with --variants. Default is None → falls through to --variants.")
    p.add_argument("--variants", type=_parse_variants, default=None,
                   help="comma-separated prompt_variant ids to keep. Use this "
                        "for sweep-4 replay (--variants 5,6,7) or ad-hoc subsets. "
                        "Default when neither --arm nor --variants is given: "
                        "the sweep-5 full active set {11,12,13,14,15,16}.")
    p.add_argument("--min-out", type=int, default=0,
                   help="skip cells where n_out (kept-variant trials) is below this "
                        "threshold; useful for restricting to completed cells. "
                        "Sweep-5 per-arm completed-cell count = 4560 (3 variants × "
                        "1520 trials/variant). For --arm both, with-tools cells "
                        "complete at 9120 while no-tools cells complete at 4560 — "
                        "filter arm-by-arm if you want a uniform threshold.")
    args = p.parse_args()
    if args.arm is not None and args.variants is not None:
        # parser.error → argparse's standard usage banner + exit 2 (matches
        # _parse_variants' ArgumentTypeError path). sys.exit would exit 1
        # with no banner — inconsistent with the rest of the flag surface.
        p.error("--arm and --variants are mutually exclusive")
    if args.arm is not None:
        args.variants = _ARM_VARIANTS[args.arm]
    elif args.variants is None:
        args.variants = _ARM_VARIANTS["both"]
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
        n_in, n_out, kept_lines, kept_trials = _scan_trials(src, args.variants)
        if args.min_out and n_out < args.min_out:
            status = f"skip<{args.min_out}"
            n_skipped += 1
            print(f"{c:<55} {n_in:>7} {n_out:>7} {status:<10}")
            continue
        write_filtered_cell(src, dst, kept_lines, kept_trials, n_in, args.variants)
        total_in += n_in
        total_out += n_out
        n_written += 1
        print(f"{c:<55} {n_in:>7} {n_out:>7} {'WRITE':<10}")
    print("-" * 86)
    print(f"{'TOTAL (written):':<55} {total_in:>7} {total_out:>7} "
          f"({n_written} cells, {n_skipped} skipped)")


if __name__ == "__main__":
    main()
