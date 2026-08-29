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
| **`MOVES.md`** | old path → new path, for resolving pre-2026-08-29 paths cited in the append-only logs |

## Root — live (13 docs)

| doc | what it is |
|---|---|
| `STATUS.md` · `NUMBERS.md` · `MOVES.md` | the three above |
| `journal_decisions_memo.md` | the accepted journal-pivot spec; §3 is the Job 2 e2e-reframe brief. ⚠️ still says "227k trials" in 3 places — the figure is **273,600**, see `NUMBERS.md` |
| `tool_call_vs_final_output_grading.md` | e2e-vs-tool-verified grading decisions D1–D9 + phase results |
| `sonnet_wt_vs_haiku_e2e_memo.md` | Sonnet-WT vs Haiku delivered/tool-verified comparison; the transcription-gap numbers |
| `iss024d_parity_prereg.md` | pre-registered parity test gating headline use of the e2e overlay |
| `ntster_h4_prereg.md` · `ntster_h4_prereg_decisions.md` | no-tools-steered H4 preregistration + answered slots |
| `title_abstract_candidates.md` | term-collision check, title/abstract candidates, scale-claim audit (open `> ANSWER:` slots) |
| `planbench/` (3 docs) | `PLANBENCH_WT_FINAL_PHASE_HANDOFF.md` (the one entry point + binding constraints), `planbench_wt_paper_integration_plan.md` (Job 1 spec, 4/4 signed), `planbench_wt_results_20260803.md` (frozen numbers) |
| `CHANGELOG.md` · `OPEN_ISSUES.md` · `paper_notes_discussions.md` | append-only logs. `OPEN_ISSUES.md` has a scannable index at its head (13 open / 8 closed) |
| `paper-git-overleaf-instructions.md` · `sync_overleaf.sh` · `make_overleaf_zip.sh` | the paper ↔ git ↔ Overleaf bridge. **Read the instructions before any sync** |
| `dev_docs_refactor_plan.md` | rationale for this layout (2026-08-29) |

## `reference/` — stable, code-pinned, never a status

`sweep_prompt_bank_design.md` (sweep-5 prompt bank; pinned by `run_experiment.py`,
`pddl_eval/prompts.py`) · `contamination_probe_plan.md` (pinned by `tools/anon_*.py`,
`submit_with_rtx.sh`) · `planbench_wt_prereg.md` + `planbench_wt_prereg_decisions.md`
(PlanBench design of record) · `grading_artifacts_findings.md` ·
`decision_audit_grading_and_frontier.md` · `frontier_rerun_framework_decision.md`
(the D1=B SDK Tool Runner decision) · `baseline_comparison_tool_use_benchmarks.md` ·
`cluster_user_guide.md` (BGU CIS HPC) · `CHANGELOG-archive.md` (pre-2026-05-05)

## `archive/` — closed lines, provenance only

Grouped by line. Nothing here is a status source; several files carry numbers that
`NUMBERS.md` supersedes.

| folder | what closed |
|---|---|
| `planbench/` | the three superseded WT handoffs, `PLANBENCH_HANDOFF_v2/v3`, calibration + verification memos, v1 results, the significance brief |
| `frontier/` | `frontier_rerun_handoff.md` and the pre-rerun frontier line (phase plan, ladder, probe findings) |
| `decoupled/` | the whole iter-2 line (✅ complete 2026-07-11), incl. its two analysis scripts |
| `status-snapshots/` | the four dated status docs `STATUS.md` replaced (`next_steps` 07-12 → `roadmap` 07-15 → `journal_phase0` 07-24 → this) + `journal_narrative_proposal.md` |
| `plans-executed/` | `decoupled_budget_plan.md` (#88), `q1_grader_plan.md` (#87), `simulate_normalizer_fix_plan.md`, `FRAMEWORK_EXTENSION_PLAN.md` (restored from git — holds the PR-3 domain-substitution rationale `EXPERIMENTS_FLOW.md` cites) |
| `cost-breakdowns/` | the cost line, parked on the advisor verdict; figures superseded |

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
