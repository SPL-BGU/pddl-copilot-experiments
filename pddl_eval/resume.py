"""Resume support for `run_single_task_experiment`'s trials.jsonl progress file.

Loads completed-trial records back into memory so an interrupted sweep can
skip already-finished cells. Schema-drift checks (`TRIAL_KEY_LEN`,
`TaskResult` shape) are enforced loudly here — see the comments in
`load_progress` for why silent degradation would burn cluster compute.
"""

import json
from pathlib import Path

from pddl_eval.runner import TRIAL_KEY_LEN, TaskResult


def load_progress(progress_path: Path) -> dict[tuple, TaskResult]:
    """Load completed-trial JSONL written by `run_single_task_experiment`.

    Returns an ordered dict mapping the 10-tuple resume key to its
    TaskResult, in JSONL append order (which matches first-completion
    order across all prior runs). Callers derive `done_keys = set(d)` and
    `restored_results = list(d.values())`. Returns an empty dict if the
    file is absent.

    The dict is the right shape for two distinct uses: (1) skip-existing
    via `key in restored_by_key`, and (2) the post-`--partial` filter in
    `run_single_task_experiment` that keeps only restored trials whose
    key matches the run's intended scope (meta-dims + post-subset
    fixtures), preventing per-cell summary pollution when a cell's
    `trials.jsonl` was seeded from a multi-cell merged source.

    A trailing partial line (TIMEOUT mid-write) is dropped silently: the
    in-progress trial is re-executed on resume. Repeated keys are
    de-duplicated to first-seen, matching the runner's
    append-once-per-completion guarantee while staying defensive against
    accidental file concatenation.
    """
    out: dict[tuple, TaskResult] = {}
    if not progress_path.exists():
        return out
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
            if key in out:
                continue
            try:
                out[key] = TaskResult(**result_dict)
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
    return out
