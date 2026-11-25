# `development/` — map

**Two tiers. The path tells you the status: you never have to open a file to find out
whether it is current.**

| tier | rule |
|---|---|
| **root** | **live**: part of work that is still open |
| **`reference/`** | **stable spec, record or guide**: accurate, but never a status |

There is no archive. A doc that is no longer needed is **deleted**; git keeps it, and
`MOVES.md` records the commit where it last existed and how to get it back. The cut of
2026-10-10 removed 60 files this way (the whole former `archive/` and the finished
handoffs).

Four files answer almost every question:

| start here | for |
|---|---|
| **`STATUS.md`** | what is left to do. Single stable entry point, **edited in place**; never write a dated successor |
| **`roadmap.md`** | the plan the work follows since 2026-11-22: the goal (complete the paper), the three research questions and their metrics, which data answers each, milestones M1 to M5 and their state, and the decisions already answered |
| **`NUMBERS.md`** | the frozen value of every headline figure and the stale readings it replaces. **Check before quoting anything** |
| **`MOVES.md`** | old path to new path (the reorganisations of 2026-08-29 and 2026-09-18) and every file deleted on 2026-10-10. Resolves the old paths cited in the append-only logs and in hash-pinned scripts |

## Root: live

| doc | what it is |
|---|---|
| `STATUS.md` · `roadmap.md` · `NUMBERS.md` · `MOVES.md` | the four above |
| `CHANGELOG.md` · `OPEN_ISSUES.md` · `paper_notes_discussions.md` | append-only logs. `OPEN_ISSUES.md` has a scannable index at its head |
| `paper-git-overleaf-instructions.md` · `sync_overleaf.sh` · `make_overleaf_zip.sh` | the paper ↔ git ↔ Overleaf bridge. **Read the instructions before any sync** |
| `thesis_literature_review.md` | the literature review, first full draft (2026-11-22), with a reading list, a "to verify" list and questions for Omer. Waits for his read |
| `unified_run_design.md` | **open, waiting for Omer's answers** (2026-11-25): the design form of the fresh unified run he approved, 18 questions with recommendations, open models and Claude models |
| `control_prompt_fix_plan.md` | **run complete and analysed 2026-11-24, waiting for Omer's read of `reference/control_prompt_fix_readout.md`** (decided by Omer, 2026-11-23): a control run for the flawed no-tools system prompt on solve and simulate (cells O, A and B, three models, 5,400 trials), the one exception to the no-new-runs line of `roadmap.md`. His answers are in its section 9; the no-run re-grade it asked for first is done (PR #146) |
| `draft_C5_E1a.md` | the hit list of retired wording and figures in the tex, from before the rewrite. **Only its search terms (§1.4) are still used**, for the pass over the paper's Supporting Analyses section (`STATUS.md`, next step 6); its line numbers and its two RQ framings are stale |
| `draft_advisor_correa_comparison.md` (+ two `.docx`) | Omer's outline for the advisor discussion of 2026-11-22; not committed |

## `reference/`: stable, never a status

Files here are not rewritten after they move in. Several were written before 2026-09-18
and say "edit on `paper/aaai27`" or name other old paths. Read that as history: the
paper is edited on a short branch off `main` (`STATUS.md`, "How work is done").

**Drafts whose text is now in the paper** (kept for the checks behind them)

- `draft_B1_B2_related_work.md`: the related-work section and the paragraph on the
  preliminary study, with the check behind every reference (§3). `thesis_literature_review.md`
  cites that table as "B1 §3".
- `draft_B3_B5_methods.md`: the test-data, prompts, tool-suite and answer-key paragraphs and
  the prompts appendix, with their grounding. Its answer list for Omer is overtaken by his
  read of the merged paper.
- `draft_D5_cost_and_correa.md`: the verified facts about Corrêa, Pereira and Seipp (Part 1).
  Its cost notes belong to runs that are no longer planned.
- `draft_release_licence_models.md`: the licence research behind PR #134 (on hold).

**The weakness review and what came out of it**

- `weakness_consolidated.md`: the two reviews merged and verified (C1 to C22,
  disagreements D1 to D8) and the decisions Q1 to Q11 with Omer's answers. The "why"
  behind the action plan.
- `weakness_action_plan.md`: the plan of 2026-10-10 to 2026-11-22 (workstreams A to F,
  the extension, the two-study outline, where each weakness ends). **Replaced by
  `roadmap.md`.** Kept because its step labels (B1, C3, D5b and so on) are cited
  everywhere; never read it as a to-do list.
- `reanalysis_statistics.md` · `reanalysis_planbench.md` · `reanalysis_breakdowns_cost.md`
  · `reanalysis_transcripts.md`: the four re-analyses of 2026-10-02 (scripts in
  `tools/reanalysis/`). The PlanBench figures and the statistics figures (the Study 1
  block, plan step C2) are in `NUMBERS.md`; the breakdowns and cost figures enter it in
  plan step C3a.
- `val_crosscheck.md` (C1, the VAL check of the answer key) · `d1_smokes_20261027.md`
  (the D1 smokes: new families, context room, the JSON constraint).

**Study 2: the delivered rerun (pre-registered)**

- `control_prompt_fix_prereg.md` (the corrected-prompt control: registration and freeze record, 2026-11-23) · `control_prompt_fix_traceability.md` (its clause-to-code map) · `control_prompt_fix_readout.md` (its readout, 2026-11-24) · `control_prompt_fix_t4_audit/` (the audit of the tripwire that fired) ·
- `delivered_rerun_prereg.md` (design of record and freeze record) ·
  `delivered_rerun_traceability.md` (prereg clause to code, freeze gate 3) ·
  `delivered_rerun_readout.md` / `.json` (frozen output; its E2 caveat about a JSON
  constraint is false, see `weakness_consolidated.md` Q3) ·
  `delivered_rerun_secondary/` (descriptive tables and hand reads)

**Closed lines whose numbers `NUMBERS.md` cites or code pins**

- PlanBench: `planbench_wt_prereg.md` · `planbench_wt_prereg_decisions.md` ·
  `planbench_wt_results_20260803.md` (every PlanBench number, the audits, the deviations)
- Steering control: `ntster_h4_prereg.md` · `ntster_h4_prereg_decisions.md` ·
  `ntster_h4_final_readout_20260829.md` (quote the revised readout only)
- Frontier budget probe: `frontier_budget_probe_prereg.md` (holds the freeze record) ·
  `frontier_budget_probe_readout.md`
- Full-storage thinking-on rerun: `iss024d_parity_prereg.md` (executed; parity failed
  07-17, so it is a separate apparatus)
- Grading: `tool_call_vs_final_output_grading.md` (grading decisions D1 to D9) ·
  `job2_delivered_reframe_worknote.md` (§2 the 13/25 verdict table) ·
  `sonnet_wt_vs_haiku_e2e_memo.md` (transcription-gap numbers) ·
  `grading_artifacts_findings.md` (Finding 4 is the `guided_json` audit)

**Design specs, guides and decision records**

- `sweep_prompt_bank_design.md` (the prompt bank; pinned by `run_experiment.py` and
  `pddl_eval/prompts.py`) · `contamination_probe_plan.md` (pinned by `tools/anon_*.py`
  and `submit_with_rtx.sh`)
- `serving_env_20260913.md` (the serving environment) · `cluster_user_guide.md` (BGU CIS
  HPC)
- `title_abstract_candidates.md` (§4 the scale audit, §5 Omer's answers on the abstract)

## House rules

- **Status goes in `STATUS.md`, edited in place.** Never a new dated status file.
- **Numbers go in `NUMBERS.md`** before they go in prose. Verify against
  `results/sweep5v2-live` + `*_sweep6` only (and the rerun's own tree for Study 2);
  any other sweep folder is a sync mirror and gives wrong numbers (the old ones
  were moved out of the repo on 2026-10-10, `MOVES.md`).
- New **framework/methodology** change → `CHANGELOG.md`; new gap → `OPEN_ISSUES.md`
  as `ISS-###`. See the `development-log` skill.
- A doc that stops being needed is **deleted** (`git rm`), and its last commit goes in
  `MOVES.md`. A finished doc that is still a source for numbers, code or decisions moves
  to `reference/`. Nothing stays at the root with a "superseded" banner.
- Append-only logs (`CHANGELOG.md`, `paper_notes_discussions.md`) are never rewritten
  and may cite old or deleted paths; `MOVES.md` resolves them.
