# `development/` — map

Start here. This dir holds the framework's living logs, stable reference docs, and one folder per **experiment line**. Each line has a single **entry doc**; open that first. Cross-line next steps: **`roadmap_eval_and_paper_completion.md`** (2026-07-15, current; D1–D4 answer slots) supersedes `next_steps_after_inflight_runs.md`.

## Live experiment lines

| Line | Entry doc | Status (2026-07-12; roadmap doc is fresher) |
|---|---|---|
| **Frontier rerun** (Haiku/Sonnet API, e2e) | `frontier_rerun_handoff.md` | Haiku full run DONE + D7-regraded; Sonnet WT canonical DONE 07-13; NT corpora de-censored 07-15; companions: `frontier_rerun_framework_decision.md`, `decision_audit_grading_and_frontier.md` |
| **E2E scoring overlay** | `tool_call_vs_final_output_grading.md` | Phases 1–5 + D7/D7b/D9 done; **ISS-024(d) resolver job 19293221: 0.8B/35b synced, 4B/9B/gemma awaiting sync (VPN)** |
| **Decoupled / iter-2** (Line 1) | `decoupled/decoupled_run_handoff.md` | ✅ LINE COMPLETE (data 2026-06-29, final A/B rollup 2026-07-11); with-tools parity re-run = job 19293221 above |
| **PlanBench** | `planbench/PLANBENCH_HANDOFF_v3.md` | v2 characterized; v3 = scaffold small models next |

A line's entry doc links its companions (plan → staging → handoff → findings). Executed plans move to `archive/`.

## Reference & tooling (root — kept flat because code/skills link these paths)

| Doc | What it is |
|---|---|
| `next_steps_after_inflight_runs.md` | Cross-line roadmap: what happens when the two in-flight runs land (open `> ANSWER:` slots) |
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

## archive/

Executed or superseded plans, kept for provenance — never deleted. (`decoupled_budget_plan.md`, `q1_grader_plan.md` = PRs #88/#87; `simulate_normalizer_fix_plan.md` = historical; `PLANBENCH_HANDOFF_v2.md` = superseded by v3; `frontier_haiku_phase_plan.md` · `frontier_with_tools_ladder.md` · `with_tools_probe_findings.md` = the pre-rerun frontier line, superseded by `frontier_rerun_handoff.md` — each carries an ARCHIVED banner saying what replaced it.)

## House rule

- New work on an **experiment line** → append to that line's entry doc, or add a doc inside its folder. Don't drop a new flat `.md` at the root.
- New **framework / methodology** change → `CHANGELOG.md`; new gap → `OPEN_ISSUES.md` as `ISS-###`. See the `development-log` skill.
- Append-only logs (`CHANGELOG*.md`, `paper_notes_discussions.md`) are not rewritten; they may cite pre-reorg paths as provenance.
