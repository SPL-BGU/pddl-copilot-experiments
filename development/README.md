# `development/` — map

Start here. This dir holds the framework's living logs, stable reference docs, and one folder per **experiment line**. Each line has a single **entry doc**; open that first.

**What is actually left to do → `remaining_work_20260811.md`.** That is the current cross-line entry point (written after PR #93 merged). It supersedes the status rows in `roadmap_eval_and_paper_completion.md` (07-15) and `journal_phase0_handoff.md` (07-24), which supersede `next_steps_after_inflight_runs.md` (07-12) in turn. The older three are kept for their decision records; do not take a status or a deadline from them.

## Live experiment lines

| Line | Entry doc | Status (refreshed 2026-08-20) |
|---|---|---|
| **Frontier rerun** (Haiku/Sonnet API, e2e) | `frontier_rerun_handoff.md` | Haiku full run DONE + D7-regraded; Sonnet WT canonical DONE 07-13; NT corpora de-censored 07-15; companions: `frontier_rerun_framework_decision.md`, `decision_audit_grading_and_frontier.md` |
| **E2E scoring overlay** | `tool_call_vs_final_output_grading.md` | Phases 1–5 + D7/D7b/D9 done; **ISS-024(d) resolver job 19293221 COMPLETE** — all 5 cells of `results/iss024d-e2e-live/` on disk at full N (9,120 rows each, 45,600 total), parity report at `results/derived/iss024d_parity_report.md` (2026-07-17); prereg gating its headline use: `iss024d_parity_prereg.md` |
| **Decoupled / iter-2** (Line 1) | `decoupled/decoupled_run_handoff.md` | ✅ LINE COMPLETE (data 2026-06-29, final A/B rollup 2026-07-11); with-tools parity re-run = job 19293221 above |
| **PlanBench (with-tools arm)** | `planbench/PLANBENCH_WT_FINAL_PHASE_HANDOFF.md` | ✅ ARM CLOSED OUT 2026-08-06/11 (RESCUE verdict; Act-4 quotes clean WT first-draw 68.3). **THE one entry point** — the other three WT handoffs and `planbench/PLANBENCH_HANDOFF_v3.md` are banner-marked SUPERSEDED; v3 is retained for cluster/ops lessons only |

A line's entry doc links its companions (plan → staging → handoff → findings). Executed plans move to `archive/`.

## Reference & tooling (root — kept flat because code/skills link these paths)

| Doc | What it is |
|---|---|
| `next_steps_after_inflight_runs.md` | ⚠️ SUPERSEDED (07-12). Both "in-flight" runs landed in July; its open slots are moot. Decision record only |
| `CHANGELOG.md` · `CHANGELOG-archive.md` | Dated framework/MCP changelog (append-only) + pre-2026-05-05 archive |
| `OPEN_ISSUES.md` | `ISS-###` methodology/measurement tracker |
| `paper_notes_discussions.md` | Dated bottom-line log of paper decisions |
| `tool_call_vs_final_output_grading.md` | E2E-vs-tool-verified grading decisions (D1–D7b) + phase results |
| `decision_audit_grading_and_frontier.md` | Methodology audit of the grading + frontier-harness decisions |
| `frontier_rerun_handoff.md` · `frontier_rerun_framework_decision.md` | Frontier rerun living state + the D1=B (SDK Tool Runner) decision record |
| `grading_artifacts_findings.md` | Cross-cutting grading/normalization artifact finding; drove the `_canon_atom` simulate fix + motivated the decoupled re-run (status updated 2026-07-12) |
| `sweep_prompt_bank_design.md` | Sweep-5 prompt bank + hypotheses (code-pinned: `run_experiment.py`, `pddl_eval/prompts.py`, `summary.py`, analyzer) |
| `contamination_probe_plan.md` | Anonymised-corpus spec (code-pinned: `tools/anon_*.py`, `submit_with_rtx.sh`) |
| `baseline_comparison_tool_use_benchmarks.md` | External tool-use/MCP benchmark comparison |
| `cluster_user_guide.md` | BGU CIS HPC cluster user guide |
| `paper-git-overleaf-instructions.md` · `sync_overleaf.sh` · `make_overleaf_zip.sh` | Paper ↔ Git ↔ Overleaf sync bridge |
| `cost-breakdowns/` | API cost analysis + slides (SUMMARY carries a 2026-07-12 superseded-figures note) |

## Paper lines — journal pivot, prereg, drafting (added to the map 2026-08-20)

These were live but absent from this map, so a fresh session never found them.

| Doc | What it is |
|---|---|
| `remaining_work_20260811.md` | **Cross-line entry point: what is actually left.** Post-PR-#93 work map (R1–R6) |
| `journal_decisions_memo.md` | The accepted journal-pivot spec — all 8 slots ACCEPTED 2026-07-24; everything downstream derives from it. ⚠️ its "227k trials" scale figure does not reproduce from disk (counted two-corpus total is 273,600) |
| `journal_narrative_proposal.md` | Narrative/positioning proposal companion to the memo (same 227k caveat) |
| `journal_phase0_handoff.md` | ⚠️ SUPERSEDED (07-24) by `remaining_work_20260811.md`. Decision record only — do NOT use its "run /resume-verify against this doc" pickup protocol |
| `ntster_h4_prereg.md` · `ntster_h4_prereg_decisions.md` | no-tools-steered H4 preregistration + its answered decision slots (RATIFIED 2026-08-11; submit still gated on a ping + VPN) |
| `title_abstract_candidates.md` | D-J6 term-collision check on "the delivery gap", title/abstract candidates, and the "227k" scale-claim audit (open `> ANSWER:` slots) |
| `iss024d_parity_prereg.md` | Pre-registered iss024d-vs-sweep5v2 parity test; gates headline use of the e2e overlay |
| `sonnet_wt_vs_haiku_e2e_memo.md` | Sonnet-WT vs Haiku e2e comparison memo (capability ladder holds across tiers) |

## archive/

Executed or superseded plans, kept for provenance — never deleted. (`decoupled_budget_plan.md`, `q1_grader_plan.md` = PRs #88/#87; `simulate_normalizer_fix_plan.md` = historical; `PLANBENCH_HANDOFF_v2.md` = superseded by v3; `frontier_haiku_phase_plan.md` · `frontier_with_tools_ladder.md` · `with_tools_probe_findings.md` = the pre-rerun frontier line, superseded by `frontier_rerun_handoff.md` — each carries an ARCHIVED banner saying what replaced it.)

## House rule

- New work on an **experiment line** → append to that line's entry doc, or add a doc inside its folder. Don't drop a new flat `.md` at the root.
- New **framework / methodology** change → `CHANGELOG.md`; new gap → `OPEN_ISSUES.md` as `ISS-###`. See the `development-log` skill.
- Append-only logs (`CHANGELOG*.md`, `paper_notes_discussions.md`) are not rewritten; they may cite pre-reorg paths as provenance.
