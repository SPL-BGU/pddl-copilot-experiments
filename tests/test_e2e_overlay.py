"""Unit tests for the e2e-overlay regrade + aggregation pass (2026-07-17
PR #91 review fixes).

Run standalone: `python3 tests/test_e2e_overlay.py`
Or via the shell wrapper: `bash tests/verify.sh`

Why this file exists: `tools/e2e_regrade.py` (the offline overlay grader) and
`.claude/skills/analyzer/scripts/e2e_overlay.py` (the aggregator every
table/deck builder reads through) are the single source of truth for
delivered-answer numbers reported in the paper — see
`development/tool_call_vs_final_output_grading.md`. A PR #91 review found
six correctness bugs in that pipeline (trial-key dedup, cap-vs-other
censoring conflation, stale stored-success gating delegation credit, only
the first fenced simulate block considered a candidate, unparseable slurm
stems silently mislabeled as frontier cells, and two crash-on-empty-input
guards in the pooled-table builder). This file pins the fixes so a future
edit can't silently regress any of them.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "analyzer" / "scripts"))

from tests._helpers import TestResults  # noqa: E402

from _constants import parse_dirname_full, _split_cond_and_tag  # noqa: E402
import e2e_overlay  # noqa: E402

import tools.e2e_regrade as e2e_regrade  # noqa: E402
from pddl_eval.scoring import _normalize_trajectory  # noqa: E402


# ---------------------------------------------------------------------------
# 1. _constants._split_cond_and_tag + parse_dirname_full
# ---------------------------------------------------------------------------


def test_parse_dirname_full_bare_cell(r: TestResults) -> None:
    info = parse_dirname_full("slurm_vllm_Qwen3_5_4B_on_no-tools")
    r.check_eq("bare cell model", info["model"], "Qwen3_5_4B")
    r.check_eq("bare cell think", info["think"], "on")
    r.check_eq("bare cell cond", info["cond"], "no-tools")
    r.check_eq("bare cell run_tag", info["run_tag"], "")


def test_parse_dirname_full_run_tagged_cell(r: TestResults) -> None:
    info = parse_dirname_full(
        "slurm_vllm_Qwen3_5_4B_on_tools_all_minimal_iss024d-e2e")
    r.check_eq("run-tagged model", info["model"], "Qwen3_5_4B")
    r.check_eq("run-tagged think", info["think"], "on")
    r.check_eq("run-tagged cond", info["cond"], "tools_all_minimal")
    r.check_eq("run-tagged run_tag", info["run_tag"], "iss024d-e2e")


def test_parse_dirname_full_legacy_no_think_cell(r: TestResults) -> None:
    info = parse_dirname_full("slurm_vllm_Qwen3_5_4B_tools_all_minimal_12345")
    r.check_eq("legacy model", info["model"], "Qwen3_5_4B")
    r.check_eq("legacy think defaults", info["think"], "default")
    r.check_eq("legacy cond", info["cond"], "tools_all_minimal")
    r.check_eq("legacy jobid", info["jobid"], "12345")
    r.check("legacy flagged", info.get("_legacy") is True, str(info))


def test_parse_dirname_full_unparseable(r: TestResults) -> None:
    info = parse_dirname_full("slurm_totally_bogus_name")
    r.check_eq("unparseable cond", info["cond"], "?")
    r.check_eq("unparseable think", info["think"], "?")


def test_split_cond_and_tag_direct(r: TestResults) -> None:
    r.check_eq("split bare", _split_cond_and_tag("Qwen3_5_4B_on_no-tools"),
              ("Qwen3_5_4B_on", "no-tools", ""))
    r.check_eq(
        "split run-tagged",
        _split_cond_and_tag("Qwen3_5_4B_on_tools_all_minimal_iss024d-e2e"),
        ("Qwen3_5_4B_on", "tools_all_minimal", "iss024d-e2e"))
    r.check_eq("split unparseable", _split_cond_and_tag("bogusname"), None)


# ---------------------------------------------------------------------------
# 2. e2e_regrade.detect_cap
# ---------------------------------------------------------------------------


def test_detect_cap_all_below_500(r: TestResults) -> None:
    r.check_eq("all-below-500 -> 500",
              e2e_regrade.detect_cap({100: 5, 200: 3}), 500)


def test_detect_cap_9b_resume_incident_shape(r: TestResults) -> None:
    # 4,496 rows pinned exactly at 500 plus one complete 503-char row from a
    # post-2026-06-25 resume — the mass-pinned rule must still call this 500,
    # not let the single longer row flip the cell to 16384 (D8).
    lengths = {500: 4496, 503: 1}
    r.check_eq("9B resume shape -> 500", e2e_regrade.detect_cap(lengths), 500)


def test_detect_cap_clean_16384(r: TestResults) -> None:
    lengths = {5000: 50, 16384: 20}
    r.check_eq("clean 16384 corpus -> 16384",
              e2e_regrade.detect_cap(lengths), 16384)


def test_detect_cap_above_16384(r: TestResults) -> None:
    r.check_eq("rows above 16384 -> None",
              e2e_regrade.detect_cap({20000: 5}), None)


# ---------------------------------------------------------------------------
# 3. e2e_regrade.extract_plan_lines_tolerant
# ---------------------------------------------------------------------------


def test_extract_plan_lines_strict(r: TestResults) -> None:
    resp = "1. (pick-up a)\n2. (stack a b)"
    lines, mode = e2e_regrade.extract_plan_lines_tolerant(resp)
    r.check_eq("strict lines", lines, ["(pick-up a)", "(stack a b)"])
    r.check_eq("strict mode", mode, "strict_lines")


def test_extract_plan_lines_tolerant_backticked(r: TestResults) -> None:
    resp = ("1. `(pick-up a)` - pick up block a\n"
            "2. `(stack a b)` - stack a on b")
    lines, mode = e2e_regrade.extract_plan_lines_tolerant(resp)
    r.check_eq("tolerant lines", lines, ["(pick-up a)", "(stack a b)"])
    r.check_eq("tolerant mode", mode, "tolerant_lines")


def test_extract_plan_lines_table(r: TestResults) -> None:
    resp = ("| step | action |\n"
            "|---|---|\n"
            "| 1 | `(pick-up a)` |\n"
            "| 2 | `(stack a b)` |\n")
    lines, mode = e2e_regrade.extract_plan_lines_tolerant(resp)
    r.check_eq("table lines", lines, ["(pick-up a)", "(stack a b)"])
    r.check_eq("table mode", mode, "table_lines")


def test_extract_plan_lines_prose(r: TestResults) -> None:
    resp = "I will now describe my plan in words, no action lines here."
    lines, mode = e2e_regrade.extract_plan_lines_tolerant(resp)
    r.check_eq("prose lines empty", lines, [])
    r.check_eq("prose mode None", mode, None)


# ---------------------------------------------------------------------------
# 4. e2e_regrade.simulate_candidates (FIX 4 pin)
# ---------------------------------------------------------------------------


def test_simulate_candidates_second_fenced_block(r: TestResults) -> None:
    # First block is "other" JSON that still coerces (a 1-step trajectory
    # about an irrelevant fluent); the CORRECT 2-step trajectory only shows
    # up in the SECOND fenced block. Before the 2026-07-17 fix,
    # simulate_candidates only ever turned the FIRST coercible block into a
    # candidate, so this trajectory would never have been gradeable True.
    first_block = json.dumps({"trajectory": [
        {"step": 0, "action": "",
         "state": {"boolean": ["(irrelevant)"], "numeric": {}}},
    ]})
    second_steps = [
        {"step": 0, "action": "", "state": {"boolean": ["(ontable a)"], "numeric": {}}},
        {"step": 1, "action": "(pick-up a)",
         "state": {"boolean": ["(holding a)"], "numeric": {}}},
    ]
    second_block = json.dumps({"trajectory": second_steps})
    resp = (f"Here is the initial state:\n```json\n{first_block}\n```\n"
            f"And here is the full trajectory:\n```json\n{second_block}\n```\n")

    cands = e2e_regrade.simulate_candidates(resp)
    fenced = [(steps, mode) for steps, mode in cands if mode == "fenced_block"]
    r.check_eq("both fenced blocks become candidates", len(fenced), 2)

    oracle_canon = _normalize_trajectory(second_steps)
    found = any(_normalize_trajectory(steps) == oracle_canon
               for steps, mode in fenced)
    r.check("second block's trajectory is among the candidates", found,
            f"fenced candidate modes/lens={[len(s) for s, _ in fenced]}")

    # Concatenation candidate (block_steps > 1) stays last and covers both.
    r.check_eq("last candidate is fenced_concat", cands[-1][1], "fenced_concat")
    r.check_eq("fenced_concat length is sum of both blocks",
              len(cands[-1][0]), 1 + 2)


# ---------------------------------------------------------------------------
# 5. Dedup (FIX 1)
# ---------------------------------------------------------------------------


def test_process_corpus_dedups_last_wins(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        corpus_dir = tmp_path / "mycorpus"
        cell_dir = corpus_dir / "mycell"
        cell_dir.mkdir(parents=True)

        key = ["validate_domain", "d1", "p1", "", 11, False]
        old_row = {
            "task": "validate_domain", "model": "testmodel",
            "domain_name": "d1", "problem_name": "p1", "plan_label": "",
            "prompt_variant": 11, "with_tools": False, "success": True,
            "done_reason": "stop", "infra_failure": False,
            "response": "OLD short response",
        }
        new_row = {
            **old_row,
            "success": False,
            "response": "NEW updated response that should win",
        }
        (cell_dir / "trials.jsonl").write_text(
            json.dumps({"key": key, "result": old_row}) + "\n")
        # Alphabetically sorts AFTER trials.jsonl ('.' < '_'), matching the
        # mop-up-file-sorts-later resume semantics the fix relies on.
        (cell_dir / "trials_mopup.jsonl").write_text(
            json.dumps({"key": key, "result": new_row}) + "\n")

        out_root = tmp_path / "out"
        ctx = e2e_regrade.SolveContext(None, None)
        rows = asyncio.run(e2e_regrade.process_corpus(
            corpus_dir, out_root, {}, {}, ctx))

        r.check_eq("one row survives dedup", len(rows), 1)
        r.check_eq("last-wins success_stored", rows[0]["success_stored"], False)
        r.check_eq("last-wins response_len",
                  rows[0]["response_len"], len(new_row["response"]))
        r.check_eq("trial_key carried on the row", rows[0]["trial_key"], key)

        out_file = out_root / "mycorpus" / "mycell.e2e.jsonl"
        written = out_file.read_text().strip().splitlines()
        r.check_eq("overlay file has exactly one deduped line", len(written), 1)


# ---------------------------------------------------------------------------
# 6. Delegation credit uses the recomputed tool-verified (FIX 3)
# ---------------------------------------------------------------------------


def test_delegation_credit_uses_recomputed_tool_verified(r: TestResults) -> None:
    ctx = e2e_regrade.SolveContext(None, None)

    # Stored `success` is (mis-binned) True, but the tool_calls only carry
    # the WRONG validator tool — recompute must flip this to NOT verified,
    # so the empty final turn must fail, not get delegation credit.
    row_wrong_tool = {
        "task": "validate_domain", "model": "testmodel",
        "domain_name": "d1", "problem_name": "p1", "plan_label": "",
        "prompt_variant": 11, "with_tools": True, "success": True,
        "done_reason": "stop", "infra_failure": False, "response": "",
        "tool_calls": [{"name": "validate_problem",
                        "result": json.dumps({"valid": True})}],
    }
    out = asyncio.run(e2e_regrade.regrade_row(row_wrong_tool, 500, {}, ctx))
    r.check_eq("wrong-tool recompute -> tool_verified_fixed False",
              out["tool_verified_fixed"], False)
    r.check_eq("wrong-tool empty-stop -> e2e False", out["e2e"], False)
    r.check_eq("wrong-tool reason", out["e2e_reason"],
              "empty_stop_not_tool_verified")

    # Converse: stored `success` is (mis-binned) False, but the RIGHT
    # validator tool was called with the correct verdict — recompute flips
    # this to verified True, so the empty final turn earns delegation
    # credit off the RECOMPUTED value, not the stale stored grade.
    row_right_tool = {
        **row_wrong_tool,
        "success": False,
        "tool_calls": [{"name": "validate_domain",
                        "result": json.dumps({"valid": True})}],
    }
    out2 = asyncio.run(e2e_regrade.regrade_row(row_right_tool, 500, {}, ctx))
    r.check_eq("right-tool recompute -> tool_verified_fixed True",
              out2["tool_verified_fixed"], True)
    r.check_eq("right-tool empty-stop -> e2e True", out2["e2e"], True)
    r.check_eq("right-tool reason", out2["e2e_reason"],
              "delegation_terminal_credit")


# ---------------------------------------------------------------------------
# 7. Fail-closed slurm-shaped stems (FIX 5)
# ---------------------------------------------------------------------------


def test_load_e2e_cells_unparseable_slurm_stem_raises(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        overlay_root = Path(tmp) / "overlay"
        corpus_dir = overlay_root / "bogus_corpus"
        corpus_dir.mkdir(parents=True)
        (corpus_dir / "slurm_bogusname.e2e.jsonl").write_text("")
        try:
            e2e_overlay.load_e2e_cells("bogus_corpus", overlay_root)
            r.check("unparseable slurm stem raises ValueError", False,
                    "no exception was raised")
        except ValueError as exc:
            r.check("unparseable slurm stem raises ValueError",
                    "slurm_bogusname" in str(exc), str(exc))


def test_load_e2e_cells_frontier_stem_still_aggregates(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        overlay_root = Path(tmp) / "overlay"
        corpus_dir = overlay_root / "frontier_corpus"
        corpus_dir.mkdir(parents=True)
        row = {"task": "solve", "with_tools": True, "prompt_variant": 11,
               "e2e_strict": True, "e2e": True, "tool_verified": True}
        (corpus_dir / "haiku-with-tools.e2e.jsonl").write_text(
            json.dumps(row) + "\n")

        cells = e2e_overlay.load_e2e_cells("frontier_corpus", overlay_root)
        r.check_eq("one frontier cell aggregated", len(cells), 1)
        cell = next(iter(cells.values()))
        r.check_eq("frontier cell n", cell["n"], 1)
        r.check_eq("frontier cell ok", cell["ok"], 1)
        r.check_eq("frontier cell exact (no censoring)", cell["exact"], True)


def main() -> None:
    r = TestResults("test_e2e_overlay")
    test_parse_dirname_full_bare_cell(r)
    test_parse_dirname_full_run_tagged_cell(r)
    test_parse_dirname_full_legacy_no_think_cell(r)
    test_parse_dirname_full_unparseable(r)
    test_split_cond_and_tag_direct(r)
    test_detect_cap_all_below_500(r)
    test_detect_cap_9b_resume_incident_shape(r)
    test_detect_cap_clean_16384(r)
    test_detect_cap_above_16384(r)
    test_extract_plan_lines_strict(r)
    test_extract_plan_lines_tolerant_backticked(r)
    test_extract_plan_lines_table(r)
    test_extract_plan_lines_prose(r)
    test_simulate_candidates_second_fenced_block(r)
    test_process_corpus_dedups_last_wins(r)
    test_delegation_credit_uses_recomputed_tool_verified(r)
    test_load_e2e_cells_unparseable_slurm_stem_raises(r)
    test_load_e2e_cells_frontier_stem_still_aggregates(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
