# MOVES.md — old path → new path (reorg of 2026-08-29)

The `development/` tree was reorganised into three tiers on 2026-08-29 (rationale:
`dev_docs_refactor_plan.md`). Live docs and code were repointed at the same time.

**The append-only logs were deliberately NOT rewritten** — `CHANGELOG.md`,
`reference/CHANGELOG-archive.md`, and `paper_notes_discussions.md` are append-only by
house rule and may cite pre-reorg paths as historical provenance. **This table is how
you resolve those.** If a path in a dated log entry does not exist, look it up here.

Every move below was made with `git mv`, so `git log --follow <new-path>` gives the
full history.

## Tier meaning

| tier | rule |
|---|---|
| `development/` root | **live** — part of work that is still open |
| `development/reference/` | **stable spec or guide** — accurate, but never a status |
| `development/archive/` | **provenance only** — never a status, never a number, never a next action |

## Renames

Rows marked *(08-29 second wave)* were moved after the nt-ster H4 run closed on the same
day, in the same tier scheme — see the note at the foot of this file.


| old path | new path |
|---|---|
| `development/CHANGELOG-archive.md` | `development/reference/CHANGELOG-archive.md` |
| `development/archive/PLANBENCH_HANDOFF_v2.md` | `development/archive/planbench/PLANBENCH_HANDOFF_v2.md` |
| `development/archive/decoupled_budget_plan.md` | `development/archive/plans-executed/decoupled_budget_plan.md` |
| `development/archive/frontier_haiku_phase_plan.md` | `development/archive/frontier/frontier_haiku_phase_plan.md` |
| `development/archive/frontier_with_tools_ladder.md` | `development/archive/frontier/frontier_with_tools_ladder.md` |
| `development/archive/q1_grader_plan.md` | `development/archive/plans-executed/q1_grader_plan.md` |
| `development/archive/simulate_normalizer_fix_plan.md` | `development/archive/plans-executed/simulate_normalizer_fix_plan.md` |
| `development/archive/with_tools_probe_findings.md` | `development/archive/frontier/with_tools_probe_findings.md` |
| `development/baseline_comparison_tool_use_benchmarks.md` | `development/reference/baseline_comparison_tool_use_benchmarks.md` |
| `development/cluster_user_guide.md` | `development/reference/cluster_user_guide.md` |
| `development/contamination_probe_plan.md` | `development/reference/contamination_probe_plan.md` |
| `development/cost-breakdowns/EXPLAINER_eli8.md` | `development/archive/cost-breakdowns/EXPLAINER_eli8.md` |
| `development/cost-breakdowns/SAMPLE_REDUCTION.md` | `development/archive/cost-breakdowns/SAMPLE_REDUCTION.md` |
| `development/cost-breakdowns/SUMMARY.md` | `development/archive/cost-breakdowns/SUMMARY.md` |
| `development/cost-breakdowns/cheap_model_cost_slides.pptx` | `development/archive/cost-breakdowns/cheap_model_cost_slides.pptx` |
| `development/cost-breakdowns/cheap_model_cost_slides.py` | `development/archive/cost-breakdowns/cheap_model_cost_slides.py` |
| `development/decision_audit_grading_and_frontier.md` | `development/reference/decision_audit_grading_and_frontier.md` |
| `development/decoupled/decoupled_rollup.py` | `development/archive/decoupled/decoupled_rollup.py` |
| `development/decoupled/decoupled_run_handoff.md` | `development/archive/decoupled/decoupled_run_handoff.md` |
| `development/decoupled/decoupled_run_staging.md` | `development/archive/decoupled/decoupled_run_staging.md` |
| `development/decoupled/iter2_execution_plan.md` | `development/archive/decoupled/iter2_execution_plan.md` |
| `development/decoupled/simulate_decisions_and_next_steps.md` | `development/archive/decoupled/simulate_decisions_and_next_steps.md` |
| `development/decoupled/with_tools_grading_surface_probe.py` | `development/archive/decoupled/with_tools_grading_surface_probe.py` |
| `development/frontier_rerun_framework_decision.md` | `development/reference/frontier_rerun_framework_decision.md` |
| `development/frontier_rerun_handoff.md` | `development/archive/frontier/frontier_rerun_handoff.md` |
| `development/grading_artifacts_findings.md` | `development/reference/grading_artifacts_findings.md` |
| `development/journal_narrative_proposal.md` | `development/archive/status-snapshots/journal_narrative_proposal.md` |
| `development/journal_phase0_handoff.md` | `development/archive/status-snapshots/journal_phase0_handoff.md` |
| `development/next_steps_after_inflight_runs.md` | `development/archive/status-snapshots/next_steps_after_inflight_runs.md` |
| `development/ntster_h4_partial_readout_20260822.md` | `development/archive/ntster/ntster_h4_partial_readout_20260822.md` |
| `development/ntster_h4_prereg.md` | `development/reference/ntster_h4_prereg.md` |
| `development/ntster_h4_prereg_decisions.md` | `development/reference/ntster_h4_prereg_decisions.md` |
| `development/ntster_submit_window_decisions.md` | `development/archive/ntster/ntster_submit_window_decisions.md` |
| `development/planbench/PLANBENCH_HANDOFF_v3.md` | `development/archive/planbench/PLANBENCH_HANDOFF_v3.md` |
| `development/planbench/PLANBENCH_WT_HANDOFF.md` | `development/archive/planbench/PLANBENCH_WT_HANDOFF.md` |
| `development/planbench/PLANBENCH_WT_NEXT_STEPS_HANDOFF.md` | `development/archive/planbench/PLANBENCH_WT_NEXT_STEPS_HANDOFF.md` |
| `development/planbench/planbench_frontier_haiku_nt.md` | `development/archive/planbench/planbench_frontier_haiku_nt.md` |
| `development/planbench/planbench_v1_results.md` | `development/archive/planbench/planbench_v1_results.md` |
| `development/planbench/planbench_verification_20260730.md` | `development/archive/planbench/planbench_verification_20260730.md` |
| `development/planbench/planbench_wt_calibration_20260730.md` | `development/archive/planbench/planbench_wt_calibration_20260730.md` |
| `development/planbench/planbench_wt_calibration_run2_20260801.md` | `development/archive/planbench/planbench_wt_calibration_run2_20260801.md` |
| `development/planbench/planbench_wt_prereg.md` | `development/reference/planbench_wt_prereg.md` |
| `development/planbench/planbench_wt_prereg_decisions.md` | `development/reference/planbench_wt_prereg_decisions.md` |
| `development/planbench/planbench_wt_significance_brief.md` | `development/archive/planbench/planbench_wt_significance_brief.md` |
| `development/remaining_work_20260811.md` | `development/STATUS.md` |
| `development/roadmap_eval_and_paper_completion.md` | `development/archive/status-snapshots/roadmap_eval_and_paper_completion.md` |
| `development/sweep_prompt_bank_design.md` | `development/reference/sweep_prompt_bank_design.md` |

## Pre-existing dangling paths, also resolved

These were already broken before the reorg (cited but not present) and now point at
real files:

| cited as | actually at |
|---|---|
| `development/FRAMEWORK_EXTENSION_PLAN.md` | `development/archive/plans-executed/FRAMEWORK_EXTENSION_PLAN.md` — deleted in `ec22cbe` (2026-04-30), **restored from git 2026-08-29** because `EXPERIMENTS_FLOW.md` cites it for the "PR-3 drift from spec" rationale, the only record of the PR-3 domain-substitution reasoning |
| `development/frontier/with_tools_probe_findings.md`, `development/with_tools_probe_findings.md` | `development/archive/frontier/with_tools_probe_findings.md` |
| `development/frontier/frontier_haiku_phase_plan.md` | `development/archive/frontier/frontier_haiku_phase_plan.md` |
| `development/PLANBENCH_HANDOFF_v2.md` / `_v3.md` | `development/archive/planbench/` |
| `development/planbench_v1_results.md` | `development/archive/planbench/planbench_v1_results.md` |
| `development/decoupled_budget_plan.md` | `development/archive/plans-executed/decoupled_budget_plan.md` |
| `development/decoupled_run_staging.md` | `development/archive/decoupled/decoupled_run_staging.md` |
| `development/sweep_prompt_redesign_handoff.md` | **no successor file** — folded into `development/reference/sweep_prompt_bank_design.md` in `b82f590`; `pddl_eval/prompts.py` was repointed there |

## Never committed — do not go looking

| cited as | status |
|---|---|
| `development/ntster_h4_slot_recommendations.md` | user-local scratch (the 34-agent evidence workflow behind the nt-ster prereg). Never entered the repo; not recoverable from git. The citation in `ntster_h4_prereg.md` is annotated to say so |
| `development/INVESTIGATION_vllm_oom_thinkon_20260511.md`, `SUBMISSION_STRATEGY_PROPOSAL.md`, `qwen3_6_35b_validate_plan_tool_inversion.md`, `sweep4_plan_new_prompts.md`, `sweep4_fr_pivot.md` | cited only from append-only log entries; not present and not restored. Treat the log entry itself as the record |

## The frozen analysis scripts deliberately keep pre-reorg paths

`tools/ntster_common.py`, `ntster_f_gate.py`, `ntster_h4.py` and `ntster_factorial.py`
each cite `development/ntster_h4_prereg.md` in a docstring or in the `prereg` field of
their JSON output. That path now resolves to `development/reference/ntster_h4_prereg.md`.

**Do not repair them.** All four are frozen and pinned by sha256 in the prereg (§8 item 9
and its 08-29 addendum); their bytes are the audit trail that the analysis which produced
the H4 verdict is the analysis that was registered. Editing a docstring changes the hash
and silently voids that guarantee, which is a far worse outcome than a stale path in a
comment. This table is how you resolve them.

The same applies to any archived doc under `archive/` — #95's rule was to repair live
docs and code, not to rewrite archived bodies.

## nt-ster H4 line — second wave, 2026-08-29

The four rows above moved after the run closed (all six units PASS, paper-level branch
PASS). The prereg pair went to `reference/` as the design of record, matching the
PlanBench prereg pair; the superseded partial readout and the spent submit-window
decisions went to `archive/ntster/`. The live doc for the line is
`ntster_h4_final_readout_20260829.md`, which stays at the root because the paper
integration it specifies is still open.
