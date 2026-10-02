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

    # Default two-cond axis: only the with-tools cond is renamed.
    rc, err = _dry("gemma4:26b-a4b", "--think-modes", "off",
                   "--prompt-style", "neutral")
    r.check("no-tools cell kept, tools cell renamed",
            "CELLS_LIST=gemma4:26b-a4b|off|no-tools"
            "^gemma4:26b-a4b|off|tools_all_neutral" in _export(err),
            _export(err))


def test_rejected_combinations(r: TestResults) -> None:
    for label, args in (
        ("unknown style", ("gemma4:26b-a4b", "--prompt-style", "guided")),
        ("neutral + --no-tools",
         ("gemma4:26b-a4b", "--no-tools", "--prompt-style", "neutral")),
        ("neutral + --smoke", ("--smoke", "--prompt-style", "neutral")),
        ("unknown task", ("gemma4:26b-a4b", "--tasks", "solve bogus")),
        ("tasks + --smoke", ("--smoke", "--tasks", "solve")),
    ):
        rc, err = _dry(*args)
        r.check(f"{label} rejected", rc != 0 and "Error:" in err,
                f"rc={rc} {err!r}")


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
