"""Unit tests for pddl_eval.runner internals.

Run standalone: `python3 tests/test_runner.py`
Or via the shell wrapper: `bash tests/verify.sh`

Pure-Python tests: no MCP, no Ollama, no fixture I/O.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from pddl_eval.runner import (
    TRIAL_KEY_LEN,
    TaskResult,
    _shard_filter,
    _think_str,
    _trial_key,
    run_single_task_experiment,
)


def test_plan_label_in_shard_key_spreads_across_shards(r: TestResults) -> None:
    """v1..v5/b1..b5 must not all cluster in shard 0.

    Regression guard for the PR-3 shard-key change that added `plan_label`
    to the key so v1..v5 / b1..b5 spread across shards instead of all
    landing in shard 0 alongside the underlying (model, task, dname, pname)
    cell.
    """
    base = ("llama3.2:3b", "validate_plan", "blocksworld", "p01")
    plan_labels = ["v1", "v2", "v3", "v4", "v5", "b1", "b2", "b3", "b4", "b5"]
    shard_n = 4
    selected: set[int] = set()
    for label in plan_labels:
        key = (*base, label, "False")
        for shard_i in range(shard_n):
            if _shard_filter(shard_i, shard_n, key):
                selected.add(shard_i)
                break
    r.check(
        "plan_label disperses keys across >1 shard",
        len(selected) > 1,
        f"all {len(plan_labels)} labels landed in shards={sorted(selected)} (expected >1)",
    )


def test_shard_filter_partitions_keys(r: TestResults) -> None:
    """Each key lands in exactly one shard (well-defined partition)."""
    key = ("m", "validate_plan", "d", "p01", "v1", "False")
    for shard_n in (2, 4, 8):
        hits = [
            shard_i
            for shard_i in range(shard_n)
            if _shard_filter(shard_i, shard_n, key)
        ]
        r.check_eq(f"shard_n={shard_n} key lands in 1 shard", len(hits), 1)


def test_shard_filter_single_shard_passes_all(r: TestResults) -> None:
    """`shard_n <= 1` is a no-op: every key passes."""
    for key in [("a",), ("b", "c"), ("x", "y", "z")]:
        r.check(
            f"shard_n=1 passes key={key}",
            _shard_filter(0, 1, key),
        )


def test_think_str_serialisation(r: TestResults) -> None:
    """`_think_str` maps the 3-valued think flag for trial keys.

    Resume keys discriminate think={on, off, default}; getting the
    serialisation wrong would silently drop or duplicate trials when
    smoke mode iterates think values into the same `trials.jsonl`.
    """
    r.check_eq("think=True -> 'on'", _think_str(True), "on")
    r.check_eq("think=False -> 'off'", _think_str(False), "off")
    r.check_eq("think=None -> 'default'", _think_str(None), "default")


def test_load_progress_roundtrip(r: TestResults) -> None:
    """`_load_progress` reads back what `run_single_task_experiment` wrote.

    Validates the JSONL line shape against the loader so a key tuple
    written by the runner is recognised on resume.
    """
    from run_experiment import _load_progress

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trials.jsonl"
        rec = {
            "key": ["qwen3:0.6b", "solve", "blocks", "p01", "", 0, True,
                    "on", "all", "minimal"],
            "result": {
                "model": "qwen3:0.6b", "task": "solve",
                "domain_name": "blocks", "problem_name": "p01",
                "prompt_variant": 0, "with_tools": True, "success": True,
            },
        }
        p.write_text(json.dumps(rec) + "\n")
        keys, results = _load_progress(p)
        r.check_eq("loads 1 key", len(keys), 1)
        r.check_eq("loads 1 result", len(results), 1)
        r.check_eq("result.success preserved", results[0].success, True)
        r.check(
            "key tuple roundtrips",
            tuple(rec["key"]) in keys,
            f"expected {tuple(rec['key'])} in {keys}",
        )


def test_load_progress_tolerates_partial_line(r: TestResults) -> None:
    """A TIMEOUT mid-write leaves a partial JSONL tail; loader drops it.

    Without this tolerance, a run that crashed during a flush would
    refuse to resume — which would force the user to manually trim the
    file every TIMEOUT, defeating the purpose of resume.
    """
    from run_experiment import _load_progress

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trials.jsonl"
        good = {
            "key": ["m", "t", "d", "p", "", 0, True, "on", "all", "minimal"],
            "result": {"model": "m", "task": "t", "domain_name": "d",
                       "problem_name": "p", "prompt_variant": 0,
                       "with_tools": True, "success": True},
        }
        p.write_text(json.dumps(good) + "\n" + '{"partial": ')
        keys, results = _load_progress(p)
        r.check_eq("partial line dropped, good kept", len(keys), 1)


def test_partial_tail_does_not_corrupt_next_append(r: TestResults) -> None:
    """A partial trailing line must not concatenate onto the next append.

    Regression: if `trials.jsonl` ends mid-write (no trailing "\\n"), the
    runner's append-mode write would otherwise glue onto the partial,
    corrupting BOTH that line and the new one. The heal step inside
    `run_single_task_experiment` pads a trailing newline before opening
    in append mode, isolating the partial so only it gets dropped.
    """
    # Direct unit check: simulate the heal logic on a partial-tail file.
    # We don't invoke the async runner here (pure-Python guarantee) — we
    # mirror the heal block from runner.py and verify behaviour. Failures
    # here indicate the heal block in runner.py needs a matching update.
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trials.jsonl"
        p.write_text('{"key":["a","b","c","d","",0,true,"on","all","minimal"],'
                     '"result":{"model":"a","task":"b","domain_name":"c",'
                     '"problem_name":"d","prompt_variant":0,"with_tools":true,'
                     '"success":true}}\n'
                     '{"partial": ')
        # Apply heal.
        if p.exists() and p.stat().st_size > 0:
            with p.open("rb") as f:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    with p.open("a") as f2:
                        f2.write("\n")
        # Append a new complete line.
        with p.open("a") as f:
            f.write('{"key":["x","y","z","w","",0,true,"on","all","minimal"],'
                    '"result":{"model":"x","task":"y","domain_name":"z",'
                    '"problem_name":"w","prompt_variant":0,"with_tools":true,'
                    '"success":false}}\n')
        # Loader should see 2 valid records, partial dropped.
        from run_experiment import _load_progress
        keys, results = _load_progress(p)
        r.check_eq("heal preserves 2 valid records", len(keys), 2)
        r.check_eq("heal preserves both results", len(results), 2)


def test_trial_key_shape_matches_loader_constant(r: TestResults) -> None:
    """`_trial_key` must produce a tuple of length `TRIAL_KEY_LEN`.

    `_load_progress` raises on length mismatch — if a future refactor
    extends `_trial_key` without bumping `TRIAL_KEY_LEN`, every existing
    `trials.jsonl` becomes a hard error at startup. This test catches
    the desync at edit time instead of at the next cluster TIMEOUT.
    """
    key = _trial_key(
        "qwen3:0.6b", "solve", "blocks", "p01", "", 0, True,
        "on", "all", "minimal",
    )
    r.check_eq("key length matches TRIAL_KEY_LEN", len(key), TRIAL_KEY_LEN)


def test_load_progress_rejects_wrong_key_length(r: TestResults) -> None:
    """Wrong-length key tuples must raise loudly, not silently filter.

    Regression: a partial silent-drop policy here would let an old
    `trials.jsonl` (written before a key-shape change) load with stale
    tuples that never match newly-built keys, causing every trial to
    be re-run instead of skipped — wasting hours of compute without a
    visible error.
    """
    from run_experiment import _load_progress

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trials.jsonl"
        bad = {
            "key": ["m", "t", "d", "p"],  # short of TRIAL_KEY_LEN
            "result": {"model": "m", "task": "t", "domain_name": "d",
                       "problem_name": "p", "prompt_variant": 0,
                       "with_tools": True, "success": True},
        }
        p.write_text(json.dumps(bad) + "\n")
        try:
            _load_progress(p)
        except RuntimeError as exc:
            r.check(
                "raised on wrong-length key",
                "trial-key shape" in str(exc),
                f"unexpected error message: {exc}",
            )
        else:
            r.check(
                "raised on wrong-length key",
                False,
                "expected RuntimeError, none raised",
            )


def test_writer_emits_loadable_jsonl(r: TestResults) -> None:
    """End-to-end: run_single_task_experiment writes JSONL the loader reads back.

    Stubs `evaluate_one` with a canned `TaskResult` so this test stays
    pure-Python (no MCP, no Ollama). Verifies (a) the writer emits one
    JSONL line per completed trial, (b) the line shape is what
    `_load_progress` expects, (c) the key in the line matches what
    `_trial_key` would produce for the same trial — closing the gap
    where a writer-only refactor (e.g. swapping field order in the
    appended JSON) would silently break resume without any test
    catching it.
    """
    from pddl_eval import runner as runner_mod
    from run_experiment import _load_progress

    async def stub_evaluate_one(
        client, model, task, domain_name, domain_pddl,
        problem_name, problem_pddl, prompt_variant, with_tools,
        mcp, gt, **kwargs,
    ):
        return TaskResult(
            model=model, task=task, domain_name=domain_name,
            problem_name=problem_name, prompt_variant=prompt_variant,
            with_tools=with_tools, success=True,
            tool_filter=kwargs.get("tool_filter", "all"),
            prompt_style=kwargs.get("prompt_style", "minimal"),
            plan_label=kwargs.get("plan_label", ""),
        )

    original = runner_mod.evaluate_one
    runner_mod.evaluate_one = stub_evaluate_one
    try:
        with tempfile.TemporaryDirectory() as d:
            progress_path = Path(d) / "trials.jsonl"
            domains = {
                "d1": {"domain": "(d)", "problems": {"p1": "(p)"}, "type": "test"},
            }
            ground_truth = {"d1": {"p1": {}}}
            results = asyncio.run(run_single_task_experiment(
                client=None, models=["m"], tasks=["solve"],
                domains=domains, ground_truth=ground_truth, mcp=None,
                num_variants=1, conditions="tools",
                progress_path=progress_path,
            ))
            r.check_eq("writer ran 1 trial", len(results), 1)
            r.check(
                "trials.jsonl exists",
                progress_path.exists(),
                f"{progress_path} not written",
            )

            keys, restored = _load_progress(progress_path)
            r.check_eq("loader sees 1 key", len(keys), 1)
            r.check_eq("loader sees 1 result", len(restored), 1)
            r.check_eq(
                "round-trip success preserved",
                restored[0].success, True,
            )

            expected_key = _trial_key(
                "m", "solve", "d1", "p1", "", 0, True,
                "default", "all", "minimal",
            )
            r.check(
                "writer key matches _trial_key",
                expected_key in keys,
                f"expected {expected_key} in {keys}",
            )
    finally:
        runner_mod.evaluate_one = original


def test_load_progress_dedups_repeated_keys(r: TestResults) -> None:
    """Defensive: two records for the same key keep the first only.

    The runner appends once per completion so this shouldn't happen, but
    if a JSONL gets concatenated (cluster sync race, manual cat, etc.)
    we want a deterministic resolution rather than crashing or silently
    double-counting in `summary_*.json`.
    """
    from run_experiment import _load_progress

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trials.jsonl"
        same_key = ["m", "t", "d", "p", "", 0, True, "on", "all", "minimal"]
        rec1 = {"key": same_key, "result": {"model": "m", "task": "t",
                "domain_name": "d", "problem_name": "p", "prompt_variant": 0,
                "with_tools": True, "success": True}}
        rec2 = {"key": same_key, "result": {"model": "m", "task": "t",
                "domain_name": "d", "problem_name": "p", "prompt_variant": 0,
                "with_tools": True, "success": False}}  # different result
        p.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n")
        keys, results = _load_progress(p)
        r.check_eq("dedups to 1 key", len(keys), 1)
        r.check_eq("dedups to 1 result", len(results), 1)
        r.check_eq("first-seen wins", results[0].success, True)


if __name__ == "__main__":
    r = TestResults("test_runner")
    test_plan_label_in_shard_key_spreads_across_shards(r)
    test_shard_filter_partitions_keys(r)
    test_shard_filter_single_shard_passes_all(r)
    test_think_str_serialisation(r)
    test_load_progress_roundtrip(r)
    test_load_progress_tolerates_partial_line(r)
    test_partial_tail_does_not_corrupt_next_append(r)
    test_trial_key_shape_matches_loader_constant(r)
    test_load_progress_rejects_wrong_key_length(r)
    test_writer_emits_loadable_jsonl(r)
    test_load_progress_dedups_repeated_keys(r)
    r.report_and_exit()
