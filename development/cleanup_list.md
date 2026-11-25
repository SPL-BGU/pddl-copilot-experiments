# Repository clean-up: the list, for approval before anything is removed

**Written 2026-11-25. Nothing has been deleted or edited.** An inventory agent read the
repository (what it did not read line by line is in section 8). Every item has the
session's recommendation; write `ok` or a change on each `> ANSWER:` line. A bare `ok`
on section 0 accepts every recommendation. After your answers, all of it goes into one
PR, with a `MOVES.md` row for each deleted or moved file.

Never touched, whatever is listed here: registrations, readouts, traceability maps, the
frozen analysis packages and every file under a pinned hash (both hashes were re-run
and match), the append-only logs, `results/`, `checkpoints/` data. Some of those files
still carry old statements (for example code comments that say the JSON constraint
works). They stay as they are; the documents around them are corrected.

## 0. Accept all recommendations below?

> ANSWER:

---

## 1. Delete

| # | path | why |
|---|---|---|
| D1 | `development/draft_C5_E1a.md` | its only remaining use was a pass over the Supporting Analyses, which is being removed |
| D2 | `development/next_session_prompt.md` | the handoff this session is carrying out; its tasks are tracked in `STATUS.md` |
| D3 | `tools/extension_copy_reused.py` and its test | built for the dropped extension, never run |
| D4 | `tools/make_stage1_keys.py` | key generator for the June probe; points at a deleted handoff |
| D5 | `tools/backfill_token_stats.py` | one-time May migration that edits summaries in place, which the rules now forbid |
| D6 | `tools/frontier_ab_compare.py`, `tools/e2e_d2b_compare.py` | decision support for choices settled in the summer |
| D7 | `cluster-experimenting/submit_with_resume.sh` | only forwards to the main submit script, and submits the dropped extension models too |
| D8 | five June PNGs in `paper/figures/` (`mechanism_validate_plan`, `solve`, `simulate`, `token_quadrant`, `visible_mode_succ`) | the paper uses the PDFs; nothing refers to the PNGs |
| D9 | `.claude/agents/experiment-runner.md` | a local smoke agent; laptop runs are not supported |
| D10 | `tools/effort_smoke_check.py` and `tests/test_reasoning_settings.py` | checker for the gpt-oss effort path, which was dropped |

> ANSWER:

## 2. Move to `development/reference/` (finished, still a source)

| # | path | why |
|---|---|---|
| M1 | `development/control_prompt_fix_plan.md` | the control is run, analysed and in the paper; section 9 holds your answers. Pinned files keep citing the old path; `MOVES.md` resolves it |
| M2 | `development/datasets_breakdown.md` | decided (option 1); it is the record of why the matched run exists |
| M3 | `development/roadmap.md` | it is the plan of 2026-11-22 ("no track fixed", "no new runs", the main sweep as the base). `STATUS.md` and `paper_outline.md` carry the plan now. Pinned scripts cite it by path, so it moves and is not deleted |

> ANSWER:

## 3. Rewrite or cut (the file stays)

| # | file | what changes |
|---|---|---|
| E1 | `development/STATUS.md` | rewritten short around where we are now: main track, 8 pages plus supplement, the matched run, who writes what. It contradicts itself today on the track and on runs. The control's step-by-step history comes out (it is in the log). PRs #144 to #150 added to the list |
| E2 | `CLAUDE.md` | venue line (main track, dates, 8 pages plus supplement; long thesis text continues; you write the prose); the data rule now names the October run and the matched run as the lead data and the May sweep as supplement material |
| E3 | `development/README.md` | index brought up to date (new files, moved files, wrong "not committed" note) |
| E4 | `development/unified_run_design.md` | cut to what is still open: A5 to A10 until the matched run is frozen, and section B (Claude models). The 41,040-trial run comes out |
| E5 | `README.md` (top level) | says what the paper asks and which data answer it; the May sweep's submit path is labelled as that; chain and old-default leftovers removed |
| E6 | `EXPERIMENTS_FLOW.md` | cut to a reference of the test setup (tasks, tool contract, output format). It describes the JSON constraint as working in six places, and frames the paper with the old hypotheses |
| E7 | `cluster-experimenting/README.md` | adds how the October run, the control and the matched run are submitted; removes the wrong advice to delete the shared container image, the 27B model, the gpt-oss cells, the "better of thinking on and off" line from the 2025 paper |
| E8 | script headers in `cluster-experimenting/` | header says one default GPU class, the code another; old plan-step labels. Comments only |
| E9 | `.claude/skills/` (`analyzer`, `cluster-ops`, `verify-claims`, `experiment-drift-review`, `development-log`) | lead data updated; `sync.sh` default folder name no longer looks like a mirror; `verify-claims` no longer assumes the session edits prose |
| E10 | `development/OPEN_ISSUES.md` | index lines that wait for steps that no longer exist (ISS-013, ISS-028, ISS-029) |
| E11 | `paper/README.md`, `paper/figures/make_paper_figures.py` docstring, `development/paper-git-overleaf-instructions.md` ("journal paper") | brought up to date |
| E12 | `tests/verify.sh` and dead pointers in non-pinned code comments (`tools/d5b/README.md`, two checkpoint READMEs, five script docstrings) | tests of deleted scripts removed from the list; pointers corrected |
| E13 | `development/NUMBERS.md` | **marks only, no rewriting**: a "replaced" note on the September abstract block and on six section headers that say "in no tex yet" for figures the paper has carried since November |

> ANSWER:

## 4. The paper (`paper/main.tex`)

Proposal: the removed text is **moved into a new file `paper/supplement_source.tex`**
that is not compiled into the paper, so nothing is lost and the supplement can be built
from it later. Generators, figures' sources and data stay.

| # | what leaves `main.tex` | lines today |
|---|---|---|
| P1 | The Supporting Analyses section, whole (seven subsections, five figures, four tables) | 1628 to 2248 |
| P2 | The parts of Methods that exist only for that section: difficulty bins, the fourth (control) arm, the run-time grader and its bounds, the Wilson and model-based interval checks, signed significance, comparing reasoning modes, contamination control | parts of 556 to 900 |
| P3 | The appendix blocks that serve it: calling decomposition, per-class accuracy, per-task contamination, the probe protocol, the steering control | 2726 to 3105 |
| P4 | Repair history in the Results: the parity sentence, the paragraph on the faulty baseline and the second reading, Table rq1-control and its paragraph, the Gemma JSON passage, the second grading of simulate (Table rq3-regrade and its paragraph), the post hoc sentences | listed in the inventory, 935 to 1626 |
| P5 | The appendix record of that history: the JSON pilot, the October run's unaided tables, the re-grade table, the control's two tables | 3107 to 3419 |
| P6 | Thinking-on in RQ2 (Table rq2-thinking and its paragraph), the one RQ2 item from the May sweep | 1406 to 1442 |

What this leaves that you should know before saying yes:

- **Dangling pointers.** About twenty sentences in the abstract, Introduction,
  Discussion, Limitations and Conclusion point at the removed parts or quote their
  numbers. I would not rewrite your prose: each such sentence is marked with a
  `% TODO(Omer)` comment and its `\ref` is replaced by plain words so the file compiles.
- **RQ1 on solve and simulate** keeps its two tables and two figures as they are
  (control baseline) until the matched run replaces them. Their captions lose the
  repair wording.
- **PlanBench** cites the funnel figure, which sits in the removed section. The figure
  stays with PlanBench.
- **Overleaf keeps deleted files.** The sync copies and never deletes, so a figure
  removed here stays there until removed by hand.
- **PR #144 is open** (Future Work adds the restating question) and edits the same
  file. It should be merged or closed before this PR.

> ANSWER (P1 to P6, the supplement file, the TODO marks, PR #144):

## 5. Questions

| # | item | question | lean |
|---|---|---|---|
| Q1 | `domains-hard*` (403 files) with their three build scripts, test and reference doc | harder test items: built, never run on a model, in none of the three questions. Keep for the thesis or future work? | delete as a set, recorded in `MOVES.md`, unless Future Work will cite them as existing |
| Q2 | the four extension models in `cluster-experimenting/lib/defaults.sh`, the Llama chat template, the gpt-oss effort flags | new model families: smoke only, dropped | remove after the matched run is submitted (the files are in use until then) |
| Q3 | `development/draft_advisor_correa_comparison.md` and two `.docx` | your files; they carry the false JSON statement, and the meeting is over | delete all three |
| Q4 | `tools/d5a_pilot.py` and its test (Claude with thinking on) | wanted for the new Claude decision? | keep until section B is answered |
| Q5 | `development/thesis_literature_review.md` | still a live file? | keep |
| Q6 | `paper/figures/rq1_solve_by_length.pdf`, `rq1_simulate_by_length.pdf` (October run's unaided arm by length) | will the supplement show them? | keep |
| Q7 | Reproducibility Checklist at the end of `main.tex` | an AAAI requirement; does ICAPS 2027 ask for it? | I check the call and remove it if not asked for |
| Q8 | PlanBench section | stays in the body? | yes, shortened by you (also 12.4 of the outline) |
| Q9 | `status.sh` | add a view for the matched run's folders (today the no-tools folders show as "unmatched" and the tool folders against the wrong total)? | yes, small, in the submit-script PR |
| Q10 | backup zips for `results/control-promptfix`, `d1-smokes`, `frontier-d5a-pilot`, `val-crosscheck` | these exist only on the laptop and the cluster | yes for the control and the pilots; separate from this PR |

> ANSWER:

## 6. Yours to remove (listed only)

- 16 agent worktrees under `.claude/worktrees/` (about 6.7 GB), all clean, and about 40
  local branches already merged. Three branches hold unmerged work and are kept:
  `fixtures/d1b-harder-items` (depends on Q1), `planbench/d1e-engineering`,
  `claude/plan-prompt-fix-control-186fe9` (its content came in with PR #147).
- Two stashes from the removed `paper/aaai27` branch.
- Untracked clutter: `.DS_Store` files, `checkpoints/rq-sweep5v2/`, the old Overleaf zip,
  `results/derived/meeting_2026-11-01/`.

Say the word and I remove the clean worktrees and merged branches for you.

> ANSWER:

## 7. Kept, though you might expect them gone

`reference/weakness_action_plan.md` and `weakness_consolidated.md` (their step labels
are cited across `NUMBERS.md` and the registrations); `domains-anon/` and its tools
(read by pinned files); `planbench/` whole; `tools/d5b/` (the larger-problems ground
truth, the first future-work item); every generator of a paper table or figure; the
analyzer's deck scripts that paper figures import; `submit_full_sweep.sh` (relabelled as
how the May sweep was submitted).

## 8. Not read line by line by the inventory

The append-only logs before their last entries; the bodies of the registrations and
readouts (protected); `main.tex` lines 1769 to 2498 and most of the appendix (searched,
not read); the bodies of most scripts under `tools/reanalysis/`, `planbench/` and
`tests/`; the PDDL files. Deletions in section 1 were each checked by search for
importers; the test suite was not run and will be before the PR.
