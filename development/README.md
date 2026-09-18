# `development/` — map

**Three tiers. The path tells you the status — you never have to open a file to
find out whether it is current.**

| tier | rule |
|---|---|
| **root** | **live** — part of work that is still open |
| **`reference/`** | **stable spec or guide** — accurate, but never a status |
| **`archive/`** | **provenance only** — never a status, never a number, never a next action |

Three files answer almost every question:

| start here | for |
|---|---|
| **`STATUS.md`** | what is actually left to do. Single stable entry point, **edited in place** — never write a dated successor |
| **`NUMBERS.md`** | the frozen value of every headline figure + the stale readings it replaces. **Check before quoting anything** |
| **`MOVES.md`** | old path → new path for the 2026-08-29 and 2026-09-18 reorganisations. Resolves old paths cited in the append-only logs and in hash-pinned scripts |

## Root — live

| doc | what it is |
|---|---|
| `STATUS.md` · `NUMBERS.md` · `MOVES.md` | the three above |
| `review_round_handoff.md` | operational pickup for the review round and pre-submission work (2026-09-18): the single-line branch model, the step sequence, the doc-cleanup brief. Never overrides `STATUS.md` |
| `advisor_brief.md` | one page for the advisors and coauthors: the six `STATUS.md` N2 questions with recommendations and open `> ANSWER:` slots |
| `journal_decisions_memo.md` | the accepted journal-pivot spec; §5 and §10 feed the advisor round. Moves to `reference/` once the venue is ratified. ⚠️ still says "227k trials" in 3 places — the figure is **273,600**, see `NUMBERS.md` |
| `CHANGELOG.md` · `OPEN_ISSUES.md` · `paper_notes_discussions.md` | append-only logs. `OPEN_ISSUES.md` has a scannable index at its head (5 open / 3 no work owed / 13 closed, re-verified 2026-09-18) |
| `paper-git-overleaf-instructions.md` · `sync_overleaf.sh` · `make_overleaf_zip.sh` | the paper ↔ git ↔ Overleaf bridge. **Read the instructions before any sync** |

## `reference/` — stable, code-pinned, never a status

Files here are not rewritten after they move in. Several were written before 2026-09-18
and say "edit on `paper/aaai27`" or name other old paths. Read that as history: the
paper is edited on a short branch off `main` (see `STATUS.md` "How work is done now").

`sweep_prompt_bank_design.md` (sweep-5 prompt bank; pinned by `run_experiment.py`,
`pddl_eval/prompts.py`) · `contamination_probe_plan.md` (pinned by `tools/anon_*.py`,
`submit_with_rtx.sh`) · `planbench_wt_prereg.md` + `planbench_wt_prereg_decisions.md`
(PlanBench design of record) · `ntster_h4_prereg.md` + `ntster_h4_prereg_decisions.md`
(nt-ster H4 design of record; §9.1 holds the two executed deviations) ·
`grading_artifacts_findings.md` ·
`decision_audit_grading_and_frontier.md` · `frontier_rerun_framework_decision.md`
(the D1=B SDK Tool Runner decision) · `baseline_comparison_tool_use_benchmarks.md` ·
`cluster_user_guide.md` (BGU CIS HPC) · `CHANGELOG-archive.md` (pre-2026-05-05)

Added 2026-09-18 (closed lines whose numbers `NUMBERS.md` cites, so they cannot go to
`archive/`): `planbench_wt_results_20260803.md` (every PlanBench number, the audits, the
deviation table) · `frontier_budget_probe_prereg.md` (holds the 09-10 freeze record) +
`frontier_budget_probe_readout.md` (ratified 09-12) · `ntster_h4_final_readout_20260829.md`
(all six units PASS; quote the revised readout only) · `job2_delivered_reframe_worknote.md`
(§2 the 13/25 verdict table, §6 the recompute script) · `sonnet_wt_vs_haiku_e2e_memo.md`
(transcription-gap numbers) · `tool_call_vs_final_output_grading.md` (grading decisions
D1–D9) · `iss024d_parity_prereg.md` (executed; parity failed 07-17) ·
`title_abstract_candidates.md` (N1 closed; §4 scale audit, §5 the abstract) ·
`serving_env_20260913.md` (serving-environment audit)

## `archive/` — closed lines, provenance only

Grouped by line. Nothing here is a status source; several files carry numbers that
`NUMBERS.md` supersedes.

| folder | what closed |
|---|---|
| `planbench/` | `PLANBENCH_WT_FINAL_PHASE_HANDOFF.md` (arm close-out, 09-18) and the signed `planbench_wt_paper_integration_plan.md` (Job 1, executed); the three superseded WT handoffs, `PLANBENCH_HANDOFF_v2/v3`, calibration + verification memos, v1 results, the significance brief |
| `frontier/` | `frontier_budget_probe_handoff.md` (CLOSED 09-12), `frontier_rerun_handoff.md` and the pre-rerun frontier line (phase plan, ladder, probe findings) |
| `decoupled/` | the whole iter-2 line (✅ complete 2026-07-11), incl. its two analysis scripts |
| `status-snapshots/` | the four dated status docs `STATUS.md` replaced (`next_steps` 07-12 → `roadmap` 07-15 → `journal_phase0` 07-24 → this) + `journal_narrative_proposal.md` |
| `plans-executed/` | `doc_cleanup_plan.md` (the 09-18 documentation cleanup, approved "ok all", ran as PRs #103–#105), `dev_docs_refactor_plan.md` (the 08-29 layout rationale, ran as PR #95), `decoupled_budget_plan.md` (#88), `q1_grader_plan.md` (#87), `simulate_normalizer_fix_plan.md`, `FRAMEWORK_EXTENSION_PLAN.md` (restored from git — holds the PR-3 domain-substitution rationale `EXPERIMENTS_FLOW.md` cites) |
| `cost-breakdowns/` | the cost line, parked on the advisor verdict; figures superseded |
| `paper-june/` | `HANDOFF.md`, `GOALS.md`, `REVIEW_AND_REWRITES.md` and the `automated-platforms-review/` folder (iter-1 and iter-2 review triage) that used to sit beside `main.tex`. June-era: dead branches, stale-mirror numbers, a command that would overwrite the manuscript. **Never follow them** |
| `ntster/` | the nt-ster H4 run line — the 08-22 partial readout (superseded by the final readout) and the spent submit-window decisions |

## House rules

- **Status goes in `STATUS.md`, edited in place.** Never a new dated status file.
- **Numbers go in `NUMBERS.md`** before they go in prose. Verify against
  `results/sweep5v2-live` + `*_sweep6` only — `results/sweep5-cluster-20260530` is a
  stale partial mirror.
- New **framework/methodology** change → `CHANGELOG.md`; new gap → `OPEN_ISSUES.md`
  as `ISS-###`. See the `development-log` skill.
- A doc that stops being live **moves to `archive/<line>/`** — it does not get a
  banner and stay at the root.
- Append-only logs (`CHANGELOG*.md`, `paper_notes_discussions.md`) are never
  rewritten and may cite pre-reorg paths; `MOVES.md` resolves them.
