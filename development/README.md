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
| **`weakness_action_plan.md`** | the plan the work follows: workstreams A to F, the experiment extension, the rewrite outline, and where every weakness ends |
| **`NUMBERS.md`** | the frozen value of every headline figure and the stale readings it replaces. **Check before quoting anything** |
| **`MOVES.md`** | old path to new path (the reorganisations of 2026-08-29 and 2026-09-18) and every file deleted on 2026-10-10. Resolves the old paths cited in the append-only logs and in hash-pinned scripts |

## Root: live

| doc | what it is |
|---|---|
| `STATUS.md` · `weakness_action_plan.md` · `NUMBERS.md` · `MOVES.md` | the four above |
| `advisor_brief.md` | one page for the advisors and coauthors, with open `> ANSWER:` slots. Sending is on hold (R7); its top note says which questions still stand |
| `CHANGELOG.md` · `OPEN_ISSUES.md` · `paper_notes_discussions.md` | append-only logs. `OPEN_ISSUES.md` has a scannable index at its head |
| `paper-git-overleaf-instructions.md` · `sync_overleaf.sh` · `make_overleaf_zip.sh` | the paper ↔ git ↔ Overleaf bridge. **Read the instructions before any sync** |
| `draft_B1_B2_related_work.md` · `draft_B3_B5_methods.md` | plan §4 B drafts, for Omer's read before the B paper PR |
| `handoff_20261109.md` | the 2026-11-09 decisions in final form and the ordered work list; delete when its items move into `items.yaml` |
| `draft_E1_research_questions.md` · `draft_tracking_proposal.md` · `draft_D5_cost_and_correa.md` · `draft_release_licence_models.md` | live drafts: the open RQ question; the tracking design (A chosen); D5 cost and the Corrêa facts; licence and model research. (`draft_C4_transcripts.md` arrives with PR #128) |

## `reference/`: stable, never a status

Files here are not rewritten after they move in. Several were written before 2026-09-18
and say "edit on `paper/aaai27`" or name other old paths. Read that as history: the
paper is edited on a short branch off `main` (`STATUS.md`, "How work is done").

**The weakness review and what came out of it**

- `weakness_consolidated.md`: the two reviews merged and verified (C1 to C22,
  disagreements D1 to D8) and the decisions Q1 to Q11 with Omer's answers. The "why"
  behind the action plan.
- `reanalysis_statistics.md` · `reanalysis_planbench.md` · `reanalysis_breakdowns_cost.md`
  · `reanalysis_transcripts.md`: the four re-analyses of 2026-10-02 (scripts in
  `tools/reanalysis/`). The PlanBench figures and the statistics figures (the Study 1
  block, plan step C2) are in `NUMBERS.md`; the breakdowns and cost figures enter it in
  plan step C3a.
- `val_crosscheck.md` (C1, the VAL check of the answer key) · `d1_smokes_20261027.md`
  (the D1 smokes: new families, context room, the JSON constraint).

**Study 2: the delivered rerun (pre-registered)**

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
- `journal_decisions_memo.md` (the journal pivot: venue §5, advisor questions §10; ⚠️ it
  says "227k trials" in three places, the figure is **273,600**, see `NUMBERS.md`) ·
  `title_abstract_candidates.md` (§4 the scale audit, §5 Omer's answers on the abstract)

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
