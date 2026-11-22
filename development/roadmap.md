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
  The paper is written as the best full paper it can be. Omer, later the same day: aim
  for the fuller paper; a shorter submission type can be cut from it, unless finishing one
  gets in the way of the other. A separate thesis document is not a concern for now.
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
| M1 | **Literature review** | a full review that leads to the three RQs, every cited paper checked, and from it the paper's related-work section | draft written (`thesis_literature_review.md`, 53 papers); the paper's related-work section is in (the verified draft, with Corrêa et al.). Left: Omer's read, the nine "to verify" papers |
| M2 | **RQ1 analysis** | the four metrics computed by a script, tables and figures, every figure in `NUMBERS.md` | done 2026-11-22 (`tools/reanalysis/rq1_metrics.py`, `rq1_figures.py`) |
| M3 | **RQ1 in the paper** | the experimental setting (how the domains, problems and plans were generated; how the prompts were generated; one test item per task) and the RQ1 results | done and merged 2026-11-22 (PR #139). Left: Omer's read |
| M4 | **RQ2 and RQ3: analysis, then in the paper** | the tool-choice percentages and the "right output, wrong answer" share in `NUMBERS.md`, then written up like M3 | done and merged 2026-11-22 (PR #139). Left: Omer's read |
| M5 | **The whole paper follows the three RQs** | RQ1 to RQ6 and the scorecard gone; introduction, discussion, abstract and title rewritten to the three questions; retired wording removed; Corrêa et al. cited and the unaided-planning claims limited to our models and settings | mostly done and merged 2026-11-22 (PR #139). **Left:** three placeholders for Omer (title, run dates, future-work list); the Supporting Analyses section still carries the older bounds and vocabulary and needs a pass with the search terms of `draft_C5_E1a.md` §1.4; a consistency read of the whole paper |

What the paper stands on: the Study 1 numbers, the VAL cross-check, the delivered rerun
and its frozen readout, the Claude runs, PlanBench and the steering control (data
final), the grader findings ISS-027 to ISS-030 (corrected figures beside the frozen
ones), and the verified drafts now in `reference/` (related work, methods, the Corrêa
facts).

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
> Later the same day (Omer): (a) is excellent, (d) is nice; (b), (e) and (f) needed an
> explanation, given in chat. No definition is changed.

## 7. Answered (2026-11-22, Omer)

- **Track:** none fixed (§1).
- **Thesis doc:** there is none; the paper is the thesis (§1).
- **New runs:** none.
- **Open PRs:** #130, #136, #133, #135 and #138 merged after each reproduced on the
  laptop data; #132 and #137 closed (branches kept); #134 (release files) on hold while a
  submission is under anonymous review.
- **Parked drafts:** deleted (`MOVES.md`), together with every planned experiment and
  feature that does not serve the three questions.

## 8. To discuss with the advisors

Omer raises these; nothing here is planned work until he reports a decision.

1. **Running the models on the larger problems** (the first future-work item of the paper).
   It is the only open item tied to a metric the advisors named: problems solved as a
   function of hardness. On our 100 problems the planner solves everything, so the hard
   end is missing. Ground truth for 120 larger IPC 2023 problems is built
   (`NUMBERS.md`, "D5b ground truth"). It needs new model runs, which the current
   decision rules out. What is known about the planner's failures there (checked
   2026-11-22 on the run records): every unsolved run is a timeout, none is a memory
   limit or an error; 6 problems unsolved at 120 s are solved at 1800 s; 19 problems are
   solved by no strategy so far (10 hard blocksworld, 8 hard rovers, 1 medium
   blocksworld), and the 1800 s pass on the hard tier is not finished. Every plan found
   is VAL-valid. That the 19 are solvable at all is assumed from the IPC generators and
   has not been checked independently. The planner here is Fast Downward with three
   simple search settings on a laptop, far weaker than the competition planners that
   Corrêa et al. ran for 30 minutes each, so "the planner fails" in our data and in
   theirs are not the same statement.
2. **The future-work list of the paper** (the one placeholder left in `paper/main.tex`).
3. **The new direction of §9**, as a possible next project.
4. **Venue matters:** which rule on LLM-written text applies (none is stated on the ICAPS
   2027 call page or in the author kit in the repo); the conference's rule for a program
   chair who is a co-author (the call lists Shahaf Shperberg as a program chair); the
   track; and how the paper is fitted to the venue's submission types.

## 9. Beyond this paper

A direction Omer named on 2026-11-22. It is **not work for the current paper** and nothing
of it is planned or built. The paper's Future Work section names it as a fifth direction
(approved by Omer the same day).

- **Learning domains and action models with an LLM.** Give the model tools or scripts
  for action-model learning, and compare what it learns against an action-model
  learning algorithm on the same data ("simulating the learning against such an
  algorithm"). The design is open: which learning algorithm, which tools the model gets,
  and how a learned model is scored are all still to be decided by Omer and his advisors.
