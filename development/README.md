# `development/` — map

Start here. This dir holds the framework's living logs, stable reference docs, and one folder per **experiment line**. Each line has a single **entry doc**; open that first.

## Live experiment lines

| Line | Folder | Entry doc | Status |
|---|---|---|---|
| **Decoupled / iter-2** (Line 1) | `decoupled/` | `decoupled_run_handoff.md` ¹ | Decoupled think=on no-tools `simulate` re-run; SLURM job `18426027` in-flight |
| **Frontier** (Haiku/Sonnet API) | `frontier/` | `frontier_haiku_phase_plan.md` ¹ | No-tools done; with-tools ladder GATED (`frontier_with_tools_ladder.md`) |
| **PlanBench** | `planbench/` | `PLANBENCH_HANDOFF_v3.md` | v2 characterized; v3 = scaffold small models next |

A line's entry doc links its companions (plan → staging → handoff → findings). Executed plans move to `archive/`.

## Reference & tooling (root — kept flat because code/skills link these paths)

| Doc | What it is |
|---|---|
| `CHANGELOG.md` · `CHANGELOG-archive.md` | Dated framework/MCP changelog (append-only) + pre-2026-05-05 archive |
| `OPEN_ISSUES.md` | `ISS-###` methodology/measurement tracker |
| `paper_notes_discussions.md` | Dated bottom-line log of paper decisions |
| `grading_artifacts_findings.md` | Cross-cutting grading/normalization artifact finding (formerly `frontier_grading_artifacts_findings.md`); drove the `_canon_atom` simulate fix + motivated the decoupled re-run |
| `sweep_prompt_bank_design.md` | Sweep-5 prompt bank + hypotheses (code-pinned: `run_experiment.py`, `pddl_eval/prompts.py`, `summary.py`, analyzer) |
| `contamination_probe_plan.md` | Anonymised-corpus spec (code-pinned: `tools/anon_*.py`, `submit_with_rtx.sh`) |
| `baseline_comparison_tool_use_benchmarks.md` | External tool-use/MCP benchmark comparison |
| `cluster_user_guide.md` | BGU CIS HPC cluster user guide |
| `paper-git-overleaf-instructions.md` · `sync_overleaf.sh` · `make_overleaf_zip.sh` | Paper ↔ Git ↔ Overleaf sync bridge |
| `cost-breakdowns/` | API cost analysis + slides |

## archive/

Executed or superseded plans, kept for provenance — never deleted. (`decoupled_budget_plan.md`, `q1_grader_plan.md` = PRs #88/#87; `simulate_normalizer_fix_plan.md` = historical; `PLANBENCH_HANDOFF_v2.md` = superseded by v3.)

## House rule

- New work on an **experiment line** → append to that line's entry doc, or add a doc inside its folder. Don't drop a new flat `.md` at the root.
- New **framework / methodology** change → `CHANGELOG.md`; new gap → `OPEN_ISSUES.md` as `ISS-###`. See the `development-log` skill.
- Append-only logs (`CHANGELOG*.md`, `paper_notes_discussions.md`) are not rewritten; they may cite pre-reorg paths as provenance.

---
¹ Filed when their feature branch merges to `main` (currently live on `paper/iter2-decoupled-run` / `feat/claude-api-haiku-frontier`). Until then the de-facto decoupled entry is `decoupled/decoupled_run_staging.md`.
