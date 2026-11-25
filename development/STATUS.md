# STATUS — what is actually left

*Content last refreshed: 2026-11-25 (rewritten short with the repository clean-up).
Earlier refreshes are in git history; the step-by-step record of the control, the
re-grades and the paper merges is in `paper_notes_discussions.md`.*

> **This is the single, stable entry point for project status, and it is edited in
> place.** Do not write a new dated successor doc. Before quoting any figure, check
> `NUMBERS.md`.

## Where we are

**The goal is to complete the paper.** The goals are set by the decisions of Omer and
his advisors. The paper is also Omer's thesis.

- **Venue:** ICAPS 2027, main track. Abstract 2026-12-07, paper 2026-12-14 (UTC-12).
  8 pages of main content, plus references, plus a supplementary PDF. AAAI-27 author
  kit, double-blind.
- **Two texts.** The 8-page submission, and the long text that continues as the thesis.
- **Who writes.** Omer writes the prose himself. The session outlines and analyses
  (`paper_outline.md`), and checks numbers.
- **The paper asks three questions.** RQ1: do the tools help? RQ2: does the model pick
  the right tool? RQ3: does it use what the tool returns?

## Which data answers what

| question | data | state |
|---|---|---|
| RQ2, RQ3 | the October rerun, tool arms (`results/delivered-rerun`) | final |
| RQ1 on validate_domain, validate_problem, validate_plan | the October rerun, tool arms against its own no-tools arm | final |
| RQ1 on solve and simulate | **the matched run** (below) | smoke submitted |
| Frontier rows | a new Claude run (below) | models being confirmed |
| PlanBench | its own registered study | final, left as it is |

Supplement material, in full, with one pointer sentence in the body: the May sweep
(`sweep5v2-live`, `sweep6-live`), the corrected-prompt control, the pilots, the old
Claude runs, the prompt fault and the registered deviations. Four things stay in the
body as constraints and observed behaviour: the problems are small and the planner
always solves them; the simulate tool answers in a different notation and the context
fills up; two of the three models are quantized; the Claude models run under different
conditions.

## The matched run

Three models (Qwen3.5-9B, Gemma-26B, Qwen3.6-35B), thinking off, solve and simulate,
three arms in one job: no tools with the format-stated system message, tools plain,
tools steered. 300 trials per model, task and arm: 5,400 trials. Decided by Omer on
2026-11-25 (`reference/datasets_breakdown.md`, option 1), in place of the full unified
run approved earlier that day.

- **Registered and frozen 2026-11-25:** `reference/matched_run_prereg.md`, package hash
  `1f3d0f84…`, in PR #152 (not merged yet). Harness flag merged: PR #151, `main` at
  `3044981`.
- **Smoke submitted** 2026-11-25 22:17 IST, job 24499771. Result pending.
  `status.sh --matched` lists its folders.
- **The full run needs Omer's separate go-ahead.**

## The frontier models

A new Claude run is decided in outline (`unified_run_design.md`): the same design as the
open models, the plain wordings, two arms, no steered arm, the Batch API. PlanBench is
left as it is. **The exact models are being confirmed with Omer.** The old runs (Haiku
4.5, Sonnet 4.6) go to the supplement.

## The paper file

`paper/main.tex` is the long draft of 2026-11-25 without the parts that will not be in
the body. Those moved, word for word, to `paper/supplement_source.tex` (raw material for
the supplement, not compiled, not on Overleaf): the Supporting Analyses, the Methods and
appendix parts that served them, the repair history of the Results with its appendix
record, and thinking-on in RQ2. Sentences in `main.tex` that still point at moved parts
carry a `% TODO(Omer)` comment. RQ1's solve and simulate tables and figures still show
the control baseline; the matched run replaces them. Generators: `paper/README.md`.

## Next steps

**For Omer**

1. Read the smoke's result when it is in, then give or hold the go-ahead for the full
   matched run.
2. Confirm the Claude models (`unified_run_design.md`, B1).
3. Answer the open choices of `paper_outline.md` (its section 12).
4. Write the text. The `% TODO(Omer)` marks in `main.tex` show where a sentence points
   at moved material.
5. Read `thesis_literature_review.md`: its four questions and its nine "to verify"
   papers.
6. Laptop, when convenient:
   `python3 tools/checkpoints/refresh_frontier_overlays.py --write --force` (until then
   `checkpoints/e2e-overlay/derived_reports.zip` holds the July table, 456 rows).

**For the session**

1. The matched run: smoke readout, then the run and its frozen analysis, each cluster
   step on Omer's word. Then the RQ1 tables and figures for solve and simulate.
2. The Claude run, once the models are confirmed.
3. After the matched run is submitted: remove the four extension models and the gpt-oss
   effort flags from `cluster-experimenting/`, and correct the script header comments.
4. Check whether ICAPS 2027 asks for the Reproducibility Checklist; remove it if not.
5. Backup zips under `checkpoints/` for `results/control-promptfix` and the pilots.

**Before submission:** turn off the comment switch in `main.tex`; check the final PDF's
metadata; anything attached is an anonymous copy (PR #134 is on hold for this).

## Rules that bind every step

- The corpora are never pooled: the May sweep, the October rerun, the control, the
  matched run, the pilots. A figure from one never stands in for a cell of another. Open
  models and Claude are never pooled.
- Any comparison that needs the full final answer uses a run that stored it (the
  rerun, the control, the matched run, the Claude runs), never the May sweep
  (500-character answers).
- Frozen corpora are never re-graded in place. A corrected figure goes beside the frozen
  one, marked post hoc. New analyses of old data are exploratory and are said to be so.
- `NUMBERS.md` before prose; `/verify-claims` on every paper edit with a number. Table
  rows in the tex are pasted from the generators and never edited by hand.
- **The JSON-schema constraint meant for the unaided arm never took effect**, in the May
  sweep or the rerun. Never write that unaided answers were sampled under it (the frozen
  rerun readout's E2 caveat says so and is false). The pilot's constrained cell is a
  separate condition.
- The 35B calling rate differs between the May sweep and the rerun: quote both.
- Paper edits: a short branch off `main`, a PR, Omer merges; `sync_overleaf.sh pull`
  first. A merged PR that touches the synced paper files pushes to Overleaf by itself.
  The sync never deletes a file on Overleaf.
- Ping Omer before any SSH or SLURM action. Itemize any dollar spend before making it.

## Pinned commits and the frozen check

- **Rerun:** harness tag `delivered-rerun-harness` (`4b2fe6e`); analysis tag
  `delivered-rerun-analysis-frozen` (`d558946`).
  `python -m tools.delivered_rerun.run --print-package-hash` must end with
  `822aace9ef8a…`.
- **Control:** `python -m tools.reanalysis.control_prompt_fix --print-package-hash` must
  give `825dab63…` (`reference/control_prompt_fix_prereg.md`, section 9).
- **Matched run:** package hash `1f3d0f84…` (`reference/matched_run_prereg.md`, in
  PR #152).
- **Steering control:** the sha256 of each of `tools/ntster_{h4,factorial,f_gate,common}.py`
  must appear in `reference/ntster_h4_prereg.md`.
- **Budget probe:** the sha256 of `tools/budget_probe_analysis.py` must appear in
  `reference/frontier_budget_probe_prereg.md`.
- Files under these hashes keep old statements and old paths in their comments.
  `MOVES.md` resolves the paths. Never repair them.
- `tests/test_delivered_rerun_analysis.py` fails 1 of 428 inside the main checkout
  because the venv sits inside the repo; not a code fault. In a fresh checkout the
  corpora come from the checkpoint zips (`checkpoints/delivered-rerun/README.md`,
  "Restore"); `results/derived/gt_cache.json` exists only on the laptop.

## Pull requests

Merged: #130, #133, #135, #136, #138 to #143 (2026-11-22), #145 to #148 (2026-11-23),
#149, #150 and #151 (2026-11-25). Closed: #132, #137 (branches kept).

Open:

- **#152** the matched run's registration and frozen analysis.
- **#144** "Future Work adds the restating question". It edits `paper/main.tex`.
- **#134** release files (licences, `CITATION.cff`), on hold while a submission is under
  anonymous review. Release terms are decided: code MIT, data CC BY 4.0, BGN
  Technologies as owner (confirm its exact legal name), Omer as author, lab SPL-BGU.

## Hygiene (Omer's to run)

Agent worktrees and merged branches; `.DS_Store` files; `checkpoints/rq-sweep5v2/`; the
old Overleaf zip; `results/derived/meeting_2026-11-01/`; two old stashes. Figure files
deleted from `paper/figures/` stay on Overleaf until removed there by hand.
