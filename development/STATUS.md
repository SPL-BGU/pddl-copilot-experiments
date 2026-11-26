# STATUS — what is actually left

*Content last refreshed: 2026-11-26, afternoon (the matched run is complete, analysed and
read out; the Claude run is being collected and its analysis is under review before the
freeze). The step-by-step record of earlier work is in
`paper_notes_discussions.md`.*

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
| RQ1 on solve and simulate | **the matched run** (below) | complete and analysed 2026-11-26; readout with Omer |
| Frontier rows | a new Claude run (below) | Haiku 5.5 and Sonnet 5.5; being collected, analysis not frozen |
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
  `1f3d0f84…`, on `main` (PR #152). Harness flag merged: PR #151, `main` at
  `3044981`.
- **Smoke passed** 2026-11-25 (job 24499771), all seven registered checks.
- **Full run:** job **24502726**, 2026-11-26 07:09 to 12:34 IST, on Omer's word. Six
  cells, 5,400 rows, every task COMPLETED on its first start, no preemption. Copied to
  `results/matched-run/` on his go-ahead, with no results file or log opened.
- **Deviation 1 (registration, section 11):** on Omer's request Gemma-26B's two cells
  were read on 2026-11-26 while three cells were still running. The registered analysis
  on the complete run is the record.
- **Frozen analysis: run 2026-11-26**, once, with the registered hash (and once more,
  byte-identical, to write `NUMBERS.md`). No tripwire fired, no cell VOID.
  **Readout: `reference/matched_run_readout.md`**; tables in `NUMBERS.md`, section
  "Matched run"; run record in section 9 of the registration.
- **Bottom line, registered grade, tools (plain) minus no tools, same run.** Solve: tools
  ahead for all three models, +50.3 [+37.3, +63.3] (Qwen3.5-9B), +36.0 [+23.0, +49.7]
  (Gemma-26B), +11.0 [+2.3, +19.7] (Qwen3.6-35B, not after the Holm adjustment; +21.7
  with the tool named). Simulate: no model has tools ahead; for Gemma-26B the unaided
  arm is ahead, -14.0 [-25.3, -3.7], not after Holm. Unaided solve 41.3 to 68.3%; with
  tools 79.3 to 94.0% (plain), 90.0 to 94.7% (steered).
- **Waiting for Omer's read of the readout.** Nothing goes near the paper before it.
  Then: the RQ1 tables and the two by-length figures for solve and simulate rebuilt on
  this run, and the numbers of `paper_outline.md` 4.3 and 4.4 replaced.

## The frontier models

Separate corpora, never pooled with or ranked against the open models. The old runs
(Haiku 4.5, Sonnet 4.6) go to the supplement. PlanBench is left as it is.

- **Claude Haiku 5.5 and Sonnet 5.5 (Omer, 2026-11-25 and 2026-11-26).** Five tasks,
  wordings v11 to v13, two arms (no tools by Batch, tools by live calls the same day),
  18,240 trials. Haiku runs with thinking off; Sonnet at its lowest setting, which
  returned no thinking in the pilot. Registration:
  `reference/frontier55_prereg.md` on branch `frontier/claude-55-run` (not on `main`
  yet); runner `tools/frontier55/`. Pilot passed 2026-11-26 (640 trials, 11.43
  dollars). **Full run started 2026-11-26 about 07:20 UTC** from the worktree
  `.claude/worktrees/frontier55`, into `results/frontier55/`, with enforced limits of
  60 and 430 dollars. At 10:02 UTC both runners were alive and the tool arms held
  3,099 (Haiku) and 2,108 (Sonnet) of 4,560 rows; the no-tools batches are fetched
  after the tool arms end. If a process dies: start the same three commands again for
  that model (`batch-submit`, `live`, `batch-fetch --wait`, same `--out`, `--gt-cache`,
  `--marketplace-path external/pddl-copilot-5e4f9c0` and `--max-usd`); they resume and
  never resend a batch; a leftover `.lock` is removed by hand. Both arms of a model are
  meant to fall on one UTC day (registration, section 6).
  **Its answers are not read until the Claude analysis is frozen.** That analysis is
  written as a freeze candidate (2026-11-26): `tools/reanalysis/frontier55.py` in the
  worktree `.claude/worktrees/frontier55-analysis`, branch `analysis/frontier55` (the
  run's branch with `main` merged in), commit `6f30ffe`, not pushed. Built from a
  synthetic fixture only (846 checks pass); no row of the run was read. **Not frozen.**
  An independent review (gate 5) is running. Seven points the registration leaves open
  are marked `# OPEN:` in the script and go to Omer before the freeze. Then: fixes,
  the freeze record (registration, section 10), the reading, and one PR for the branch.
  Do not edit `tools/frontier55/*.py` or touch the worktree `frontier55` while the run
  is unfinished: the run's manifest pins the runner's hashes. Still to add to the
  registration: the cluster's tool library versions beside the laptop's.
- **`gpt-6.2-sol` and hosted `Qwen/Qwen3.6-35B-A3B` (Omer, 2026-11-26).** The Qwen run
  is the same weights as the local 35B at full precision (host: Novita), as an anchor
  that measures the cost of the local 4-bit quantization. Runners, their tests (366
  checks) and a registration draft (`reference/hosted_gpt_qwen_prereg.md`) are
  committed on branch `frontier/gpt-qwen-run` (worktree
  `.claude/worktrees/hosted-models`, commits `102458f` and `33cc879`); no request was
  ever sent to either provider. Estimated cost: GPT 261 to 453 dollars (ceiling 927),
  Qwen about 56 (ceiling 158). Still to do: an independent review of the runners,
  Omer's answers (below), the itemized cost in chat, a pilot, the full run.

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

1. Read the matched run's readout (`reference/matched_run_readout.md`); say whether
   the RQ1 tables and figures are rebuilt on it.
2. Answer the open points of the Claude analysis before its freeze (listed in chat on
   2026-11-26 and marked `# OPEN:` in `tools/reanalysis/frontier55.py`).
3. For the GPT and hosted Qwen runs: set `OPENAI_API_KEY` and `NOVITA_API_KEY` in the
   shell (not set on 2026-11-26); say yes or no to GPT at reasoning "low" (it cannot be
   turned off); answer the draft's open questions (GPT's output cap counts its hidden
   reasoning: keep 8,192 and 6,144 or raise them; prompt caching off for GPT; which
   OpenAI tier, since the lowest paid tier has a 500-dollar monthly cap; what to do if
   the Qwen host refuses temperature 0).
4. Write the text. Decided 2026-11-26: the Claude results stay in a small section of
   their own for now; RQ3 quotes the registered trace-loss range with the other
   reading in one clause; PlanBench stays in the body. The `% TODO(Omer)` marks in `main.tex` show where a sentence points
   at moved material.
5. Read `thesis_literature_review.md`: its four questions and its nine "to verify"
   papers.
6. Laptop, when convenient:
   `python3 tools/checkpoints/refresh_frontier_overlays.py --write --force` (until then
   `checkpoints/e2e-overlay/derived_reports.zip` holds the July table, 456 rows).

**For the session**

1. The matched run: after Omer's read, the RQ1 tables and figures for solve and
   simulate.
2. The Claude run: let it finish; review, fix and freeze its analysis; then read it.
3. The GPT and hosted Qwen runs: review the runners, itemize the cost, pilot, run,
   once the keys exist. Before any paid request the itemized cost goes to Omer; stop
   and ask if an estimate passes 500 dollars.
4. Now that the matched run is complete: remove the four extension models
   and the gpt-oss effort flags from `cluster-experimenting/`, and correct the script
   header comments.
5. Remove the Reproducibility Checklist from `paper/main.tex`, in the next paper PR.
   The ICAPS 2027 call (read 2026-11-26) says the AAAI checklist is not required. The
   same call has a Reproducibility section that asks for hardware, benchmarks and
   software versions in the main paper (`paper_outline.md`, 3.3).
6. Backup zips under `checkpoints/` for `results/control-promptfix`, the pilots,
   `results/matched-run*` and `results/frontier55*`.

**Before submission:** turn off the comment switch in `main.tex`; check the final PDF's
metadata; anything attached is an anonymous copy (PR #134, closed, holds the release files).

## Rules that bind every step

- The corpora are never pooled (the May sweep, the October rerun, the control, the
  matched run, the pilots), and a figure from one never stands in for a cell of another.
  Open models and Claude are never pooled.
- A comparison that needs the full final answer uses a run that stored it, never the May
  sweep (500-character answers).
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
  first. A merged PR that touches the synced files pushes to Overleaf by itself.
- Ping Omer before any SSH or SLURM action. Itemize any dollar spend before making it.

## Pinned commits and the frozen check

- **Rerun:** harness tag `delivered-rerun-harness` (`4b2fe6e`), analysis tag
  `delivered-rerun-analysis-frozen` (`d558946`).
  `python -m tools.delivered_rerun.run --print-package-hash` must end `822aace9ef8a…`.
- **Control:** `python -m tools.reanalysis.control_prompt_fix --print-package-hash` must
  give `825dab63…` (`reference/control_prompt_fix_prereg.md`, section 9).
- **Matched run:** package hash `1f3d0f84…` (`reference/matched_run_prereg.md`, PR #152).
- **Steering control and budget probe:** the sha256 of each of
  `tools/ntster_{h4,factorial,f_gate,common}.py` must appear in
  `reference/ntster_h4_prereg.md`, and that of `tools/budget_probe_analysis.py` in
  `reference/frontier_budget_probe_prereg.md`.
- Files under these hashes keep old statements and old paths in their comments.
  `MOVES.md` resolves the paths. Never repair them.
- `tests/test_delivered_rerun_analysis.py` fails 1 of 428 inside the main checkout
  because the venv sits inside the repo; not a code fault. In a fresh checkout the
  corpora come from the checkpoint zips (`checkpoints/delivered-rerun/README.md`);
  `results/derived/gt_cache.json` exists only on the laptop.

## Pull requests

Merged: #130, #133, #135, #136, #138 to #143 (2026-11-22), #145 to #148 (2026-11-23),
#149, #150 and #151 (2026-11-25), #152 (the matched run's registration and frozen
analysis) and #153 (the repository clean-up) on 2026-11-26. Closed: #132, #137
(branches kept).

Closed without merging (state checked 2026-11-26):

- **#144** "Future Work adds the restating question". Its one idea is kept as a
  future-work item in `paper_outline.md`.
- **#134** release files (licences, `CITATION.cff`), set aside while a submission is
  under anonymous review. Release terms are decided: code MIT, data CC BY 4.0, BGN
  Technologies as owner (confirm its exact legal name), Omer as author, lab SPL-BGU.

No pull request is open.

## Hygiene (Omer's to run)

Agent worktrees and merged branches; `.DS_Store` files; `checkpoints/rq-sweep5v2/`; the
old Overleaf zip; `results/derived/meeting_2026-11-01/`; two old stashes. Figure files
deleted from `paper/figures/` stay on Overleaf until removed there by hand.
