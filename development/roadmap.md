# Roadmap: three research questions, the thesis, ICAPS 2027

*Written 2026-11-22, after Omer's advisor meeting. It replaces the weakness action plan
of 2026-10-10 (now a record at `reference/weakness_action_plan.md`; its step labels B1,
C3, D5b and so on are still cited by older docs). `STATUS.md` tracks progress against
this file. Decisions that are Omer's to make are in §7, each with an `> ANSWER:` slot.*

## 1. What was decided (advisors, reported by Omer 2026-11-22)

- **Venue: ICAPS 2027**, perhaps the demo track. JAIR and TMLR are no longer the target.
- **Paper writing: use the venue's format only.** No word cap while writing.
- **Two action items, both for the thesis:**
  1. Start the literature review. It becomes part of the thesis, and it keeps the key
     papers from being forgotten.
  2. Finish RQ1 and write it in the thesis doc: the experimental setting (how the data
     was generated, how the instructions were generated, one or two examples per task)
     and the experimental results.
- **Three research questions** (§2). They replace RQ1 to RQ6 and the scorecard in the
  tex, and they close the question that was open as E1.
- **We already own most of the data, perhaps all of it.** So the work is analysis and
  writing. The planned extension (about 190K new trials) is no longer on the path (§5).

## 2. The research questions and their metrics

**RQ1. Do PDDL tools help an LLM do planning-related tasks?**
Compare the same model with and without the tools, task by task:

| # | metric | task |
|---|---|---|
| 1 | false positives and false negatives of the plan verdicts | validate_plan |
| 2 | share of simulated states that are correct, as a function of the simulation length | simulate |
| 3 | how many problems are solved, as a function of how hard the problem is (hardness is roughly the solution length, or the planner's runtime without an LLM) | solve |
| 4 | plan quality: the length of the plan | solve |

**RQ2. Does the LLM know to choose the right PDDL tool?**
The model is given all the tools, and we check which ones it called:

- share of trials where exactly the right tool was called and no other (higher is better);
- share of trials where the right tool was called (higher is better);
- share of trials where other tools were called as well (lower is better).

**RQ3. Does the LLM know how to use the tool's output properly?**

- share of trials where the tool produced the right output but the model's final answer
  was wrong (this is the delivered metric).

How this maps to what we had: RQ2 is the old "gate 1" (calling) and RQ3 is the old
"gate 2" (delivery). RQ1 is the plain question the advisors approved from the start,
"do tools help?". Study 1 and Study 2 stay as names for the two data sets, and are still
never pooled, but the paper and the thesis are organised by RQ, not by study.

## 3. What data we own for each metric

Checked against the trial files on 2026-11-22. Two facts drive most of this table:

- **Every tool trial stores each tool call in full** (tool name, arguments, the tool's
  result), in the main sweep, the rerun and the Claude runs. All seven tools were
  visible in every tool trial.
- **The main sweep kept only the first 500 characters of the final answer.** The rerun
  and the Claude runs kept far more (up to 65,536 and 16,384 characters, enough for a
  whole plan or trace). So anything that needs the full final answer
  (a long plan, a state trace) comes from the rerun and the Claude runs, as the delivered
  figures already do.

| metric | data we own | what is missing | new model runs? |
|---|---|---|---|
| RQ1-1 FP/FN, validate_plan | every problem has 5 valid and 5 broken plans, labelled per trial; unaided and tool arms; main sweep (5 open models, thinking off and on), rerun (3 models), Claude Sonnet 4.6 and Haiku 4.5 | a table script: FP, FN and "no verdict" counts per model and arm | no |
| RQ1-2 simulate vs length | each trial is graded as "whole trace exactly right", and the trace length is in the answer key | a per-state scorer (which states are right, where the first wrong one is). It can run after the fact on the stored answers, but only where the full answer was stored: the rerun and Claude. Today's grader is all-or-nothing | no |
| RQ1-3 solved vs hardness | success per problem, the reference plan length and the object count for all 100 problems (the tex already has plan-length and object-count analyses) | (a) nothing: the planner's runtime turned out to be stored too (the solver returns `solve_time` with every plan, so each planner call in a tool trial carries it). (b) the planner solves all 100, so on our corpus the tool arm cannot show where the planner gives out, and its runtime barely varies (two thirds of the problems take under a third of a second). The 120 larger IPC 2023 problems of PR #138 would show it, but no model has run on them (§7, decision 3) | no for (a); yes for (b), optional |
| RQ1-4 plan length | full delivered plans in the rerun and the Claude runs; the planner's plan inside each tool call | a script comparing, per problem, the length of the valid unaided plan, the valid plan delivered with tools, and the planner's plan. The main sweep's unaided plans are cut at 500 characters, so it is left out. Our planner settings look for any plan, not the shortest; shortest-plan lengths would need one more local planner pass (§7, decision 5c) | no |
| RQ2 tool choice | tool names per trial for every tool trial: main sweep, rerun, Claude; thinking off and on; the plain, steered and neutral prompts | a script for the three percentages per task, model and arm, and a fixed table of "the right tool" per task. Today's figures count only "the right tool was called" | no |
| RQ3 use of the output | tool result and full final answer side by side in the rerun (3 open models) and the Claude runs; the frozen rerun readout already has the loss tables, and PR #136 splits the solve losses into real copying errors and correct plans with extra text | restate the readout as the advisors' metric; merge #136 and #130 so the corrected figures sit beside the frozen ones | no |

So no metric needs a new run. *(Corrected 2026-11-22, later: the first version of this
table asked for a planner timing pass; the runtime is already in the tool results.)* The
only thing a new run would add is the hard end of RQ1 metric 3, on the larger problems.

**Limits that stay, to be stated in the text:** the delivered comparison covers five
models (three open ones with thinking off, two Claude models); in the rerun the unaided
answers had a JSON format constraint and the tool answers did not; the same planner and
validator that the model calls also built the answer key (the VAL cross-check answers
most of this).

## 4. Milestones

Dates are targets. M1 and M2 are independent and run in parallel.

| # | milestone | what "done" means | target |
|---|---|---|---|
| M1 | **Literature review, first full draft** (draft written 2026-11-22: `thesis_literature_review.md`, 53 papers, waits for Omer's read) | a thesis-style review built from `draft_B1_B2_related_work.md` (every reference already looked up and verified), the Corrêa et al. facts in `draft_D5_cost_and_correa.md`, and the arXiv-version delta. A reading list with one line per paper on why it matters to us. Omer reads it | 2026-11-29 |
| M2 | **RQ1 analysis** (first tables done 2026-11-22: `tools/reanalysis/rq1_metrics.py`, `NUMBERS.md` "RQ1 metrics"; left: Omer's read of the tables, the figures, the object-count view, and the shortest-plan pass if decision 5c asks for it) | the metric definitions of §7 decision 5 fixed first; the analysis script in `tools/reanalysis/`; tables and figures; every figure in `NUMBERS.md`, checked against the canonical corpora | 2026-12-01 |
| M3 | **RQ1 in the thesis doc** | experimental setting (how the domains, problems and plans were generated; how the prompts were generated; one or two examples per task, from `draft_B3_B5_methods.md` and `draft_C4_transcripts.md`) and the results of M2 | 2026-12-06 |
| M4 | **RQ2 and RQ3 analysis and text** | the tool-choice percentages and the "right output, wrong answer" share, in `NUMBERS.md`, then written up in the same form as M3 | 2026-12-13 |
| M5 | **The paper follows the three RQs** | RQ1 to RQ6 and the scorecard replaced by the three questions; results sections reordered by RQ; retired wording removed (hit list in `draft_C5_E1a.md`); Corrêa et al. cited and the unaided-planning claims limited to our models and settings. The paper already uses the AAAI-27 author kit, which is the format ICAPS 2027 asks for | depends on §7 decision 1 |
| M6 | **Demo material** (only if the demo track is chosen) | a short system description and a video of the copilot at work (the plugins in `../pddl-copilot`) | when the 2027 demo call is published |

Order of work for Omer: answer §7; read the literature review (M1); read the RQ1 tables
(M2) before any results prose is written; read the thesis sections (M3, M4).

## 5. What happens to the earlier plan

Kept, because the new work stands on it:

| earlier item | role now |
|---|---|
| The related-work draft (B1, B2) | the base of M1 |
| The methods draft (B3 to B5) and the example transcripts (C4) | the base of M3's experimental setting |
| Study 1 numbers, VAL cross-check, breakdown tables (C1 to C3), all in `NUMBERS.md` | RQ1 and RQ2 results |
| The delivered rerun and its frozen readout | RQ1 and RQ3 results |
| Claude runs, PlanBench, the steering control | supporting results; data final |
| The grader findings ISS-027 to ISS-030 (PRs #130, #136) | corrected figures beside the frozen ones, for RQ1 and RQ3 |
| The retired-wording hit list (`draft_C5_E1a.md`) | the checklist for M5 |

Off the path. Nothing here runs or is written without a new go-ahead from Omer:

| earlier item | why it is off |
|---|---|
| The extension, waves 1 and 2 (new model families, the small models, thinking-on rerun, context room, the JSON control, harder test items; about 190K trials) and its prereg draft | new data; the three RQs are answered from data we own |
| Open-model PlanBench with tools (PR #137) | not asked by any of the three RQs |
| The Corrêa follow-up runs (D5a thinking on, D5c, D5d, D5e) | new data. See §7 decision 3 for the two that bear on RQ1 |
| The two-study restructure of the paper (workstream E) | replaced by M5 |
| The JAIR reformat and the journal cover letter | the venue changed; the format is already right |
| The tracking file `items.yaml` (PR #132) | it was seeded with the earlier plan's 55 items; this plan is small enough for `STATUS.md` |

Still standing regardless of the plan: the public release (code MIT, data CC BY 4.0;
PR #134 stays on hold while a submission is under anonymous review) and the checkpoint
housekeeping (PR #133).

## 6. Rules that still bind

- `NUMBERS.md` before any figure in prose; canonical corpora only; `/verify-claims` on
  every paper edit that carries a number.
- Study 1 and Study 2 are never pooled, and a rerun figure never stands in for a
  main-sweep cell. Frozen corpora are never re-graded in place: a corrected figure goes
  beside the frozen one, marked post hoc.
- Any comparison that needs the full final answer uses the rerun and the Claude runs,
  never the main sweep.
- New analyses of old data are exploratory and are said to be so.
- A short branch and a PR for code and paper; Omer merges. Ping Omer before any SSH or
  SLURM action.

## 7. Decisions for Omer

**1. Which ICAPS track, and so which date.**
The main track's dates are published: abstract **2026-12-07**, paper **2026-12-14**
(UTC-12), in the AAAI-27 author kit. The 2027 demo call is not published yet; in 2026
the demo track asked for a short abstract in the AAAI template plus a video of at most
10 minutes, due in early April. The two are different things: a main-track paper would
carry the RQ1 to RQ3 results, a demo shows the system working.
*(rec)* Keep the demo track as the plan of record, since it matches the advisors'
wording and puts the thesis first. Treat 2026-12-01 as a checkpoint: if the RQ1 tables
(M2) are in by then, ask the advisors whether to register a main-track abstract.

> ANSWER:

**2. Where the thesis doc lives.**
*(rec)* I draft M1 and M3 as markdown in `development/` (`thesis_literature_review.md`,
`thesis_rq1.md`) and you paste or I export to the format you need. If the thesis is a
Google Doc, a Word file or an Overleaf project, say which and I write to match it.

> ANSWER:

**3. New runs: none, or the two small ones that bear on RQ1.**
- *Larger problems (PR #138).* RQ1 metric 3 asks for "solved as a function of hardness".
  On our 100 problems the planner solves everything, so the hard end of the curve is
  missing. Running the models on the 120 larger problems would add it.
- *Claude with thinking on (D5a, about $66, already approved before the replan).* It
  answers the Corrêa et al. challenge to our unaided baseline. That paper comes from the
  ICAPS community, so a reviewer there is likely to raise it.

*(rec)* No new runs now. Look at the RQ1-3 curve on the data we own first (M2), then
decide on the larger problems. Keep D5a parked unless the main track is chosen.

> ANSWER:

**4. The open PRs.**
**Done 2026-11-22:** #130, #136 (grader corrections, used by RQ1 and RQ3), #133
(checkpoints), #135 (a tex comment) and #138 (the larger problems' ground truth, data
only) are merged, each after its scripts reproduced on the laptop data. *(rec)* for the
rest: close #132
(tracking) and #137 (PlanBench tools). Keep #134 (release files) on hold.

> ANSWER:

**5. Metric definitions I filled in.** They stand unless you change them.

| | definition | the other option |
|---|---|---|
| a | RQ1-2: report both the share of traces that are exactly right and the share of single states that are right, each against the trace length. Added while building it: many answers are cut off mid-trace and are not readable at all, so a third score also reads the complete leading steps of a cut-off trace. It is more lenient than the frozen grader and is shown beside the strict score, never instead of it | exact traces only (today's grader); or drop the lenient third score |
| b | RQ1-3: hardness is the reference plan length, with the planner's runtime beside it (already in the data, but it barely varies on this corpus, so plan length carries the result); object count as a second view, still to add | plan length only |
| c | RQ1-4: compare with the plan the tool returned; add shortest-plan lengths for the classical domains if the local planner pass is cheap | the tool's plan only |
| d | RQ2: for solve, the right tool is the planner that fits the domain (classical or numeric). A plan check called after the planner counts under "other tools called", and is also shown on its own line, since checking the plan is not a mistake | count it as a plain extra call |
| e | RQ1-1: a trial with no readable verdict is its own column, not an FP or an FN | fold it into the errors |
| f | RQ2 and RQ3 headline arm: the plain prompt (tools offered, no push to use them); the steered and neutral prompts as extra rows | steered as the headline |

> ANSWER (keep / change: ...):

**6. Parked drafts at the root of `development/`.**
`draft_D1f_extension_prereg.md` and `draft_tracking_proposal.md` belong to work that is
now off the path. *(rec)* Delete both once decision 3 is answered (git keeps them, and
`MOVES.md` records the commit). `advisor_brief.md` is overtaken by the meeting; delete
it too if you agree.

> ANSWER:
