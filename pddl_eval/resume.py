"""Resume support for `run_single_task_experiment`'s trials.jsonl progress file.

Loads completed-trial records back into memory so an interrupted sweep can
skip already-finished cells. Schema-drift checks (`TRIAL_KEY_LEN`,
`TaskResult` shape) are enforced loudly here — see the comments in
`load_progress` for why silent degradation would burn cluster compute.
"""

import json
from pathlib import Path

from pddl_eval.runner import TRIAL_KEY_LEN, TaskResult


def load_progress(progress_path: Path) -> tuple[set[tuple], list[TaskResult]]:
    """Load completed-trial JSONL written by `run_single_task_experiment`.

    Returns (done_keys, restored_results). Skips silently if the file is
    absent. A trailing partial line (TIMEOUT mid-write) is dropped: the
    in-progress trial will be re-executed on resume, which is the
    intended behaviour. Repeated keys are de-duplicated to first-seen,
    which matches the runner's append-once-per-completion guarantee but
    is defensive against accidental file concatenation.
    """
    if not progress_path.exists():
        return set(), []
    done_keys: set[tuple] = set()
    restored: list[TaskResult] = []
    with progress_path.open("r") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                # Trailing partial line at the tail of an interrupted run;
                # safe to drop — the trial will be re-run.
                continue
            try:
                key = tuple(rec["key"])
                result_dict = rec["result"]
            except (KeyError, TypeError):
                continue
            # Loud failure on key-shape drift: a future refactor that
            # lengthens or reorders the trial key would otherwise leave
            # this loader silently storing wrong-shape tuples that never
            # match newly-built keys, so resume would re-run every trial.
            # Match the TaskResult-drift policy below — force the user to
            # move the file aside rather than silently abandoning data.
            if len(key) != TRIAL_KEY_LEN:
                raise RuntimeError(
                    f"Incompatible trial-key shape in {progress_path} "
                    f"(got len={len(key)}, expected {TRIAL_KEY_LEN}); the "
                    f"key tuple changed since this file was written. "
                    f"Move the file aside and rerun to start fresh."
                )
            if key in done_keys:
                continue
            done_keys.add(key)
            try:
                restored.append(TaskResult(**result_dict))
            except TypeError:
                # Schema drift between dataclass and serialised record.
                # Drop the incompatible JSONL: caller should rm the file
                # and restart fresh. We surface this loudly rather than
                # silently dropping data.
                raise RuntimeError(
                    f"Incompatible TaskResult shape in {progress_path}; "
                    f"the dataclass changed since this file was written. "
                    f"Move the file aside and rerun to start fresh."
                )
    return done_keys, restored
