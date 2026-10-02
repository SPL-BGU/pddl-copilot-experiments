"""Dry-run tests for cluster-experimenting/submit_with_rtx.sh.

Run standalone: `python3 tests/test_submit_wrapper.py`
Or via the shell wrapper: `bash tests/verify.sh`

Covers the `--prompt-style` / `--tasks` passthrough (2026-10-02). `--dry-run`
only prints the sbatch command line, so nothing here touches SLURM or the
cluster. The property that matters: without the new flags the submission is
unchanged, and with `--prompt-style neutral` the cell is named so that it can
never share a results dir with a `tools_all_minimal` cell.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402

WRAPPER = REPO_ROOT / "cluster-experimenting" / "submit_with_rtx.sh"
SBATCH = REPO_ROOT / "cluster-experimenting" / "run_condition_vllm_rtx.sbatch"


def _dry(*args: str) -> tuple[int, str]:
    """(exit code, stderr) of `submit_with_rtx.sh <args> --dry-run`."""
    p = subprocess.run(["bash", str(WRAPPER), *args, "--dry-run"],
                       capture_output=True, text=True)
    return p.returncode, p.stderr


def _export(stderr: str) -> str:
    m = re.search(r"--export=(\S+)", stderr)
    return m.group(1) if m else ""


def test_defaults_unchanged(r: TestResults) -> None:
    rc, err = _dry("gemma4:26b-a4b", "Qwen3.5:9B", "qwen3.6:35b",
                   "--tools-only", "--think-modes", "off",
                   "--run-tag", "delivered-rerun")
    r.check_eq("default submit exits 0", rc, 0)
    # The whole --export list, pinned: no TASKS, no style token.
    r.check_eq(
        "default --export list",
        _export(err),
        "ALL,CELLS_LIST=gemma4:26b-a4b|off|tools_all_minimal"
        "^Qwen3.5:9B|off|tools_all_minimal"
        "^qwen3.6:35b|off|tools_all_minimal,RUN_TAG=delivered-rerun",
    )
    r.check("default submit prints no style line", "style:" not in err, err)
    r.check("default submit prints no tasks line", "tasks:" not in err, err)

    # An explicit `--prompt-style minimal` is the same submission.
    rc2, err2 = _dry("gemma4:26b-a4b", "Qwen3.5:9B", "qwen3.6:35b",
                     "--tools-only", "--think-modes", "off",
                     "--run-tag", "delivered-rerun",
                     "--prompt-style", "minimal")
    r.check_eq("explicit minimal == default output", (rc2, err2), (rc, err))


def test_neutral_style_and_tasks(r: TestResults) -> None:
    rc, err = _dry("gemma4:26b-a4b", "--tools-only", "--think-modes", "off",
                   "--prompt-style", "neutral", "--tasks", "validate_plan",
                   "--run-tag", "delivered-rerun-neutral")
    r.check_eq("neutral submit exits 0", rc, 0)
    r.check_eq(
        "neutral --export list",
        _export(err),
        "ALL,CELLS_LIST=gemma4:26b-a4b|off|tools_all_neutral,"
        "RUN_TAG=delivered-rerun-neutral,TASKS=validate_plan",
    )
    r.check("neutral cell is not a tools_all_minimal cell",
            "tools_all_minimal" not in _export(err), err)

    # Several tasks: space- or comma-separated, exported `^`-joined so the
    # comma-separated --export list never carries a space or a comma.
    for label, value in (("space-separated", "solve validate_plan"),
                         ("comma-separated", "solve,validate_plan")):
        rc, err = _dry("gemma4:26b-a4b", "--tools-only", "--tasks", value)
        r.check_eq(f"{label} tasks exits 0", rc, 0)
        r.check(f"{label} tasks exported ^-joined",
                _export(err).endswith(",TASKS=solve^validate_plan"),
                _export(err))

    # Repeats are dropped, first-seen order kept.
    rc, err = _dry("gemma4:26b-a4b", "--tools-only", "--tasks",
                   "validate_plan solve,validate_plan solve")
    r.check_eq("duplicate tasks exits 0", rc, 0)
    r.check("duplicate tasks deduped in order",
            _export(err).endswith(",TASKS=validate_plan^solve"), _export(err))

    # A neutral submission never contains a no-tools cell, whatever the
    # model set or think axis.
    rc, err = _dry("--all", "--tools-only", "--prompt-style", "neutral")
    r.check_eq("--all neutral tools-only exits 0", rc, 0)
    r.check("--all neutral: no no-tools cell", "no-tools" not in _export(err),
            _export(err))
    r.check("--all neutral: no minimal cell",
            "tools_all_minimal" not in _export(err), _export(err))
    r.check_eq("--all neutral: 5 models x 2 think modes",
               _export(err).count("tools_all_neutral"), 10)


def test_rejected_combinations(r: TestResults) -> None:
    for label, args, needle in (
        ("unknown style", ("gemma4:26b-a4b", "--prompt-style", "guided"),
         "must be 'minimal' or 'neutral'"),
        ("empty style", ("gemma4:26b-a4b", "--prompt-style", ""),
         "expects a value"),
        # A non-minimal style without --tools-only would also submit the
        # no-tools cells (the whole baseline, under `--all`).
        ("neutral without --tools-only (single model)",
         ("gemma4:26b-a4b", "--prompt-style", "neutral"),
         "requires --tools-only"),
        ("neutral without --tools-only (--all)",
         ("--all", "--prompt-style", "neutral"), "requires --tools-only"),
        ("neutral + --no-tools",
         ("gemma4:26b-a4b", "--no-tools", "--prompt-style", "neutral"),
         "requires --tools-only"),
        ("neutral + --smoke", ("--smoke", "--prompt-style", "neutral"),
         "requires --tools-only"),
        ("unknown task", ("gemma4:26b-a4b", "--tasks", "solve bogus"),
         "unknown task 'bogus'"),
        ("empty task list", ("gemma4:26b-a4b", "--tools-only", "--tasks", ""),
         "at least one task"),
        ("separator-only task list",
         ("gemma4:26b-a4b", "--tools-only", "--tasks", " , "),
         "at least one task"),
        ("tasks + --smoke", ("--smoke", "--tasks", "solve"),
         "cannot be combined with --smoke"),
    ):
        rc, err = _dry(*args)
        r.check(f"{label} rejected", rc != 0 and "Error:" in err
                and needle in err, f"rc={rc} {err!r}")
        r.check(f"{label}: nothing would be submitted", "DRY:" not in err, err)

    # `--tasks` as the very last argument (value missing) must also be a
    # clear error, not a silent exit or an all-tasks run.
    p = subprocess.run(["bash", str(WRAPPER), "gemma4:26b-a4b", "--dry-run",
                        "--tools-only", "--tasks"],
                       capture_output=True, text=True)
    r.check("trailing --tasks with no value rejected",
            p.returncode != 0 and "at least one task" in p.stderr,
            f"rc={p.returncode} {p.stderr!r}")


def test_sbatch_handles_the_new_cond(r: TestResults) -> None:
    """The sbatch must map the cond token the wrapper emits, and turn the
    `^`-joined TASKS back into words."""
    text = SBATCH.read_text()
    r.check("sbatch has a tools_all_neutral branch passing --prompt-style neutral",
            re.search(r"tools_all_neutral\)\s*(?:#[^\n]*\n\s*)*"
                      r"COND_ARGS=\(--conditions tools --tool-filter all "
                      r"--prompt-style neutral\)", text) is not None)
    r.check("sbatch keeps the minimal branch byte-stable",
            "COND_ARGS=(--conditions tools --tool-filter all "
            "--prompt-style minimal) ;;" in text)
    r.check("sbatch maps ^ back to spaces in TASKS",
            'TASKS_ENV_OVERRIDE="${TASKS_ENV_OVERRIDE//^/ }"' in text)
    r.check_eq("sbatch parses (bash -n)",
               subprocess.run(["bash", "-n", str(SBATCH)]).returncode, 0)


def main() -> None:
    r = TestResults("test_submit_wrapper")
    test_defaults_unchanged(r)
    test_neutral_style_and_tasks(r)
    test_rejected_combinations(r)
    test_sbatch_handles_the_new_cond(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
