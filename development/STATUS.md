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
| Frontier rows | a new Claude run (below) | Haiku 5.5 and Sonnet 5.5; complete and analysed 2026-11-26; readout with Omer (PR #155) |
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
- **Tables and figures rebuilt (Omer, 2026-11-26: "Yes, rebuild"), PR #154, open.**
  Tables rq1-simulate, rq1-solve and rq1-planlen and the two by-length figures now take
  their open-model rows from this run (`tools/reanalysis/rq1_matched_metrics.py`, which
  halts unless its counts equal the frozen analysis output; `NUMBERS.md`, block
  "RQ1-MATCHED-METRICS"). New Table rq1-matched: the three arms with their paired
  differences. Claude rows unchanged. No paragraph was edited: the sentences whose
  numbers no longer match the tables carry `% TODO(Omer)` and are listed, old and new,
  in the PR's body. `paper_outline.md` 4.3 and 4.4 carry this run's numbers.

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
  **Complete and analysed (2026-11-26), PR #155, open.** All four folders hold 4,560
  rows; every request on 2026-11-26 UTC; no refusal, no error row; spend 20.25 dollars
  (Haiku) and 294.49 (Sonnet). The analysis (`tools/reanalysis/frontier55.py`) was
  frozen at package hash `0cbb69b7…` before any row was read (freeze commit `621f07c`;
  five gates, an independent review in three passes; Omer accepted the open points).
  One tripwire fired and was audited (six notes between tool calls in Sonnet's tool
  arm; the provider counts zero thinking tokens for them). **Readout:**
  `reference/frontier55_readout.md` on that branch; tables in `NUMBERS.md`, "Claude
  run".
  **Bottom line, tools minus no tools.** Haiku 5.5: tools ahead on solve (+21.3 [+7.7,
  +36.3]; 73.7 to 95.0%), validate_domain (+17.5) and validate_problem (+8.8); no
  difference shown on validate_plan; on simulate the unaided arm is ahead (-20.3
  [-30.7, -11.0]). Sonnet 5.5: unaided 94 to 99.7% on four tasks; tools ahead only on
  validate_problem (+3.8 [+2.2, +5.7]); simulate -8.7 [-17.0, +0.0], no difference
  shown. Tool right and answer wrong: nothing on verdicts, 3.0 to 5.1% on plans, 53.0
  to 78.0% on traces. With tools, 204 of Haiku's 300 simulate answers are the trace in
  prose, which the grade does not accept (a post hoc description).
  **These are not the old runs' models:** the merged draft's "22 to 29% unaided solve"
  is Haiku 4.5 and Sonnet 4.6 and does not describe this run.
  **In the paper (Omer, 2026-11-26: "Yes, build it"), PR #156, open:** a subsection
  "Frontier Models" at the end of the Results holding Table claude (ten rows, read
  from the frozen output by `tools/reanalysis/frontier55_tex.py`) and no text yet. The
  rows of the earlier Claude runs left the six body tables that carried them and the
  three figures with Claude panels; they are in `paper/supplement_source.tex` word for
  word. Open-model rows are byte-identical. 27 paragraphs that quote the earlier Claude
  runs carry a `% TODO(Omer)` comment (listed in the PR). PlanBench and its funnel
  figure are unchanged (Haiku 4.5). `paper_outline.md` section 7 carries the new
  numbers. Still to add to the registration: the cluster's tool library versions.
- **Where the Claude rows go (Omer, 2026-11-26): their own section only.** Done in
  PR #156.
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
carry a `% TODO(Omer)` comment. RQ1's solve and simulate tables and figures are rebuilt
on the matched run in PR #154 (open); the paragraphs around them still quote the control
baseline's numbers until Omer rewrites them. Generators: `paper/README.md`.

## Next steps

**For Omer**

1. Merge PR #154 (the RQ1 tables and figures on the matched run), or say what to
   change. Its body lists the sentences that quote superseded numbers.
2. Merge PR #156 (it sits on top of #154 and holds #155, so merging it alone brings
   all three in), or merge #154, #155 and #156 in that order. Say whether a second,
   descriptive reading of Haiku's prose traces on simulate is wanted
   (`reference/frontier55_readout.md`, section 5).
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

1. The matched run: done; PR #154 carries the tables and figures.
2. The Claude run: done; PR #155, and its table in the paper in PR #156.
   The token-consumption analysis Omer asked for on 2026-11-26 is done: PR #157
   (branch `analysis/token-consumption`; report in `development/token_consumption/README.md`;
   descriptive and post hoc). **Not in the outline (Omer, 2026-11-26).** It sits in
   `paper/main.tex` as an optional, temporary section "Token Consumption" just before
   the Technical Appendix (after the references): Table tokens and three figures, no
   text, marked `% TODO(Omer)` to write or remove. Nothing else in the paper refers to
   it. Still open: dated marks on the two older cost claims it contradicts (the
   supplement source's "What the Tool Costs"; `NUMBERS.md` S2-C solve and simulate
   rows), and its three sources verified before any citation.
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

Open: **#154**, the RQ1 solve and simulate tables and figures rebuilt on the matched
run (2026-11-26); **#155**, the Claude run (runner, registration, frozen analysis,
readout; no paper file); **#156**, the Claude table in a subsection of its own and the
earlier Claude rows out of the body (on top of #154, holds #155). **#157**, the token-consumption
analysis and its optional paper section (on top of #156, so it holds #154 to #156;
merging it alone brings all four in).

## Hygiene (Omer's to run)

Agent worktrees and merged branches; `.DS_Store` files; `checkpoints/rq-sweep5v2/`; the
old Overleaf zip; `results/derived/meeting_2026-11-01/`; two old stashes. Figure files
deleted from `paper/figures/` stay on Overleaf until removed there by hand.
