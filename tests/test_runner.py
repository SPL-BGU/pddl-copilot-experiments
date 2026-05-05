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
    from pddl_eval.resume import load_progress

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
        loaded = load_progress(p)
        keys = set(loaded.keys())
        results = list(loaded.values())
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
    from pddl_eval.resume import load_progress

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trials.jsonl"
        good = {
            "key": ["m", "t", "d", "p", "", 0, True, "on", "all", "minimal"],
            "result": {"model": "m", "task": "t", "domain_name": "d",
                       "problem_name": "p", "prompt_variant": 0,
                       "with_tools": True, "success": True},
        }
        p.write_text(json.dumps(good) + "\n" + '{"partial": ')
        loaded = load_progress(p)
        keys = set(loaded.keys())
        results = list(loaded.values())
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
        from pddl_eval.resume import load_progress
        loaded = load_progress(p)
        keys = set(loaded.keys())
        results = list(loaded.values())
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
    from pddl_eval.resume import load_progress

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
            load_progress(p)
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
    from pddl_eval.resume import load_progress

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

            loaded = load_progress(progress_path)
            keys = set(loaded.keys())
            restored = list(loaded.values())
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


def test_runner_filters_out_of_scope_restored(r: TestResults) -> None:
    """Restored trials outside this run's scope (different model, different
    think mode, dropped fixture) must NOT appear in the returned results.

    Regression guard for the merged-seed pollution case: when a cell's
    `trials.jsonl` was seeded from a multi-cell merged source, the cell's
    final summary was including trials from OTHER cells, polluting per-
    cell aggregates. Fix lives in `run_single_task_experiment`, which
    builds an `in_scope_keys` set during job emission and filters the
    `restored_by_key` dict by membership before merging.
    """
    from pddl_eval import runner as runner_mod
    from pddl_eval.resume import load_progress

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
            # Pre-seed with two records: one in-scope (model="m1"), one
            # out-of-scope (model="other-model" — not in the run's models
            # list). The out-of-scope record simulates a multi-cell merged
            # seed where another cell's trials snuck in.
            in_scope_rec = {
                "key": ["m1", "solve", "d1", "p1", "", 0, True,
                        "default", "all", "minimal"],
                "result": {"model": "m1", "task": "solve", "domain_name": "d1",
                           "problem_name": "p1", "prompt_variant": 0,
                           "with_tools": True, "success": True,
                           "tool_filter": "all", "prompt_style": "minimal"},
            }
            out_of_scope_rec = {
                "key": ["other-model", "solve", "d1", "p1", "", 0, True,
                        "default", "all", "minimal"],
                "result": {"model": "other-model", "task": "solve",
                           "domain_name": "d1", "problem_name": "p1",
                           "prompt_variant": 0, "with_tools": True,
                           "success": False, "tool_filter": "all",
                           "prompt_style": "minimal"},
            }
            progress_path.write_text(
                json.dumps(in_scope_rec) + "\n"
                + json.dumps(out_of_scope_rec) + "\n"
            )
            restored_by_key = load_progress(progress_path)
            r.check_eq("loader saw both records", len(restored_by_key), 2)

            domains = {
                "d1": {"domain": "(d)", "problems": {"p1": "(p)"}, "type": "test"},
            }
            ground_truth = {"d1": {"p1": {}}}
            results = asyncio.run(run_single_task_experiment(
                client=None, models=["m1"], tasks=["solve"],
                domains=domains, ground_truth=ground_truth, mcp=None,
                num_variants=1, conditions="tools",
                progress_path=progress_path,
                restored_by_key=restored_by_key,
            ))
            r.check_eq("returned exactly 1 result (in-scope only)", len(results), 1)
            r.check_eq("kept the in-scope model", results[0].model, "m1")
            r.check(
                "out-of-scope model did NOT leak through",
                all(rr.model != "other-model" for rr in results),
                f"found other-model in results: {[rr.model for rr in results]}",
            )
    finally:
        runner_mod.evaluate_one = original


def test_runner_filters_out_partial_dropped_fixtures(r: TestResults) -> None:
    """Restored trials for fixtures dropped by `--partial K` (e.g. p03 when
    K=2) must NOT appear in the returned results.

    This is the second leg of the scope-filter contract: even when the
    meta-dims (model/think/cond/filter/prompt) match, a restored trial
    targeting a fixture that's no longer in `domains` after the partial
    subset is out-of-scope and must be dropped.
    """
    from pddl_eval import runner as runner_mod
    from pddl_eval.resume import load_progress

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
            # Two records: p1 (kept) and p3 (dropped — caller passes only
            # {p1: ...} in `domains`, simulating --partial 2 having
            # dropped p3 upstream).
            kept_rec = {
                "key": ["m1", "solve", "d1", "p1", "", 0, True,
                        "default", "all", "minimal"],
                "result": {"model": "m1", "task": "solve", "domain_name": "d1",
                           "problem_name": "p1", "prompt_variant": 0,
                           "with_tools": True, "success": True,
                           "tool_filter": "all", "prompt_style": "minimal"},
            }
            dropped_rec = {
                "key": ["m1", "solve", "d1", "p3", "", 0, True,
                        "default", "all", "minimal"],
                "result": {"model": "m1", "task": "solve", "domain_name": "d1",
                           "problem_name": "p3", "prompt_variant": 0,
                           "with_tools": True, "success": False,
                           "tool_filter": "all", "prompt_style": "minimal"},
            }
            progress_path.write_text(
                json.dumps(kept_rec) + "\n"
                + json.dumps(dropped_rec) + "\n"
            )
            restored_by_key = load_progress(progress_path)
            domains = {
                "d1": {"domain": "(d)", "problems": {"p1": "(p)"}, "type": "test"},
            }
            ground_truth = {"d1": {"p1": {}}}
            results = asyncio.run(run_single_task_experiment(
                client=None, models=["m1"], tasks=["solve"],
                domains=domains, ground_truth=ground_truth, mcp=None,
                num_variants=1, conditions="tools",
                progress_path=progress_path,
                restored_by_key=restored_by_key,
            ))
            r.check_eq("returned exactly 1 result (kept fixture only)", len(results), 1)
            r.check_eq("problem name kept", results[0].problem_name, "p1")
            r.check(
                "dropped fixture p3 did NOT leak through",
                all(rr.problem_name != "p3" for rr in results),
                f"found p3 in results: {[rr.problem_name for rr in results]}",
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
    from pddl_eval.resume import load_progress

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
        loaded = load_progress(p)
        keys = set(loaded.keys())
        results = list(loaded.values())
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
    test_runner_filters_out_of_scope_restored(r)
    test_runner_filters_out_partial_dropped_fixtures(r)
    test_load_progress_dedups_repeated_keys(r)
    r.report_and_exit()
