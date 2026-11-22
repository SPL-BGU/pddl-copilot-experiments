# Roadmap: complete the paper, around three research questions

*Written 2026-11-22 after Omer's advisor meeting, and revised the same day with Omer's
answers. It replaces the weakness action plan of 2026-10-10 (a record at
`reference/weakness_action_plan.md`; its step labels B1, C3, D5b and so on are still
cited by older docs). `STATUS.md` tracks progress against this file.*

## 1. The goal, and who sets it

**The goal is to complete the paper.** The goals of this project are set by the
decisions of Omer and his advisors (Omer, 2026-11-22). This file follows those
decisions. A recommendation here stays a recommendation until Omer answers it.

What was decided:

- **Venue: ICAPS 2027.** No track is fixed, on purpose: planning around one track
  would pull the work away from the other if the choice changes (Omer, 2026-11-22).
  The paper is written as the best full paper it can be.
- **Paper writing: the venue's format only** (the AAAI-27 author kit, already in use).
  No word cap while writing.
- **The paper is the thesis.** Omer's thesis is composed of his papers, so there is no
  separate thesis document to fill. The advisors' two action items land in the paper:
  1. the literature review (it keeps the key papers from being forgotten);
  2. RQ1, finished and written up: the experimental setting (how the data was
     generated, how the instructions were generated, one or two examples per task) and
     the experimental results.
- **Three research questions** (§2). They replace RQ1 to RQ6 and the scorecard in the
  tex.
- **No new runs.** The questions are answered from data we already own (Omer,
  2026-11-22).

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

Study 1 and Study 2 stay as names for the two data sets, and are still never pooled,
but the paper is organised by RQ, not by study.

## 3. What data answers each metric

Checked against the trial files on 2026-11-22. Two facts drive most of this table:

- **Every tool trial stores each tool call in full** (tool name, arguments, the tool's
  result), in the main sweep, the rerun and the Claude runs. All seven tools were
  visible in every tool trial.
- **The main sweep kept only the first 500 characters of the final answer.** The rerun
  and the Claude runs kept far more (up to 65,536 and 16,384 characters, enough for a
  whole plan or trace). So anything that needs the full final answer comes from the
  rerun and the Claude runs.

| metric | data | state |
|---|---|---|
| RQ1-1 FP/FN, validate_plan | every problem has 5 valid and 5 broken plans, labelled per trial; unaided and tool arms; rerun (3 open models) and Claude Sonnet 4.6 and Haiku 4.5 | tables done (`NUMBERS.md`, "RQ1 metrics") |
| RQ1-2 simulate vs length | stored traces graded state by state against the answer key | tables done |
| RQ1-3 solved vs hardness | success per problem, the reference plan length, the planner's runtime (the solver returns it with every plan, so it is in the tool results) and the object count | tables done |
| RQ1-4 plan length | full delivered plans; the planner's plan inside each tool call | tables done |
| RQ2 tool choice | tool names per trial for every tool trial: main sweep, rerun, Claude; thinking off and on; the plain, steered and neutral prompts | tables done (`NUMBERS.md`, "RQ2 metrics") |
| RQ3 use of the output | tool result and full final answer side by side in the rerun and the Claude runs; the rerun rows are the frozen readout's loss cells restated, with their categories | tables done (`NUMBERS.md`, "RQ3 metrics") |

**Limits to state in the paper:** the delivered comparison covers five models (three
open ones with thinking off, two Claude models); the unaided arm asks for its answer
format in the prompt only, and the JSON-schema constraint meant for it never took effect,
so an unaided failure can be a failure of format as well as of content; the same planner and validator
that the model calls also built the answer key (the VAL cross-check answers most of
this); the planner solves all 100 problems, so the data does not show where the planner
itself gives out.

## 4. Milestones

In this order. M1 and M2 ran in parallel and have first results.

| # | milestone | what "done" means | state |
|---|---|---|---|
| M1 | **Literature review** | a full review that leads to the three RQs, every cited paper checked, and from it the paper's related-work section | first draft written 2026-11-22 (`thesis_literature_review.md`, 53 papers); waits for Omer's read |
| M2 | **RQ1 analysis** | the four metrics computed by a script, tables and figures, every figure in `NUMBERS.md` | done 2026-11-22 (`tools/reanalysis/rq1_metrics.py`, `rq1_figures.py`); waits for Omer's read |
| M3 | **RQ1 in the paper** | the experimental setting (how the domains, problems and plans were generated; how the prompts were generated; one or two examples per task, from `draft_B3_B5_methods.md` and `draft_C4_transcripts.md`) and the RQ1 results | next |
| M4 | **RQ2 and RQ3: analysis, then in the paper** | the tool-choice percentages and the "right output, wrong answer" share in `NUMBERS.md`, then written up like M3 | analysis done 2026-11-22 (`tools/reanalysis/rq23_metrics.py`); the text follows M3 |
| M5 | **The whole paper follows the three RQs** | RQ1 to RQ6 and the scorecard gone; introduction, discussion, abstract and title rewritten to the three questions; retired wording removed (hit list in `draft_C5_E1a.md`); Corrêa et al. cited and the unaided-planning claims limited to our models and settings | after M3 and M4 |

What the new work stands on: the related-work draft (`draft_B1_B2_related_work.md`),
the methods draft and example transcripts, the Study 1 numbers, the VAL cross-check,
the delivered rerun and its frozen readout, the Claude runs, PlanBench and the steering
control (data final), and the grader findings ISS-027 to ISS-030 (corrected figures
beside the frozen ones).

Everything else in the earlier plan is dropped. It is recorded in
`reference/weakness_action_plan.md`, and nothing in it is planned work.

## 5. Rules that still bind

- `NUMBERS.md` before any figure in prose; canonical corpora only; `/verify-claims` on
  every paper edit that carries a number.
- Study 1 and Study 2 are never pooled, and a rerun figure never stands in for a
  main-sweep cell. Frozen corpora are never re-graded in place: a corrected figure goes
  beside the frozen one, marked post hoc.
- Any comparison that needs the full final answer uses the rerun and the Claude runs,
  never the main sweep.
- New analyses of old data are exploratory and are said to be so.
- A short branch and a PR for code and paper edits, unless Omer says otherwise; Omer merges. Ping Omer before any SSH or
  SLURM action.

## 6. The RQ1 metric definitions (kept for now)

These are the choices made while building the RQ1 tables. Omer, 2026-11-22: keep them
for now. They can still change; a change means rerunning `rq1_metrics.py`, not new data.

| | definition | the other option |
|---|---|---|
| a | **Simulate, what is scored.** Three scores against trace length: the whole trace exactly right; the share of single states right; and a lenient version of the second that also reads the complete leading steps of an answer cut off mid-trace. The lenient one is more forgiving than the frozen grader and is shown beside the strict score | exact traces only; or without the lenient score |
| b | **Solve, what "hard" means.** The reference plan length. The planner's runtime is shown beside it, but it barely varies on our problems. Object count as a second view | plan length only |
| c | **Plan length, compared with what.** The answer key's plan and the plan the tool returned. Neither is a shortest plan | add shortest-plan lengths (needs one more local planner pass on the classical domains) |
| d | **RQ2, what "the right tool" is for solve.** The planner that fits the domain (classical or numeric). A plan check called after the planner counts under "other tools called", and is also shown on its own line, since checking a plan is not a mistake | count it as a plain extra call |
| e | **validate_plan, answers with no verdict.** Their own column, counted as neither a false positive nor a false negative | fold them into the errors |
| f | **RQ2 and RQ3, the headline prompt.** The plain prompt (tools offered, no push to use them); the steered and neutral prompts as extra rows | the steered prompt as the headline |

> ANSWER: **ANSWERED 2026-11-22 (Omer): keep for now.**

## 7. Answered (2026-11-22, Omer)

- **Track:** none fixed (§1).
- **Thesis doc:** there is none; the paper is the thesis (§1).
- **New runs:** none.
- **Open PRs:** #130, #136, #133, #135 and #138 merged after each reproduced on the
  laptop data; #132 and #137 closed (branches kept); #134 (release files) on hold while a
  submission is under anonymous review.
- **Parked drafts:** deleted (`MOVES.md`), together with every planned experiment and
  feature that does not serve the three questions.
