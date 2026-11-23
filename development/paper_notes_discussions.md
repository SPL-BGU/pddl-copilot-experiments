
- **Decided (Omer, 2026-11-22):** the material that none of the three questions asks for
  (cost, the contamination control, PlanBench, the steering control, the output-budget
  probe) stays, as supporting sections after the three questions.
- **Second commit on PR #139:** RQ2 and RQ3 sections from generated tables
  (`tools/reanalysis/rq23_tex.py`); the older task-by-task results moved under a new
  "Supporting Analyses" section with their reading rules and vocabulary; Methods takes
  the drafted test-data and prompts paragraphs (B3.2), a table with one test item per
  task, and the appendix with every prompt verbatim (B3.4). Front and back matter are
  not touched yet, and the title is still the retired one.

## 2026-11-22 (end of day) — The paper rewrite is merged; development/ cut to what is left

- **Instruction (Omer):** complete the open items of the paper branch where the facts are
  on hand, leave placeholders otherwise, commit everything to main, and clean
  `development/` of anything we no longer act on.
- **Merged, PR #139 (now on Overleaf):** the three research questions with their Results
  subsections; a Supporting Analyses section for the older results; the rewritten
  abstract, introduction, discussion, limitations opening, future work and conclusion; the
  verified related-work draft with 19 new bibliography entries, Corrêa et al. among them;
  the test-data, prompts, tool-suite and answer-key paragraphs; one test item per task;
  every prompt verbatim in the appendix. The two claims marked for removal on 2026-10-10
  ("direct empirical support for the LLM-Modulo thesis", "capability boundary") are gone.
- **Placeholders left for Omer in the tex:** the title (a working title is in place), the
  run and query dates, the list of future-work directions.
- **Known and not done:** the Supporting Analyses text still reports main-sweep delivered
  bounds that the rerun retired, in the older vocabulary; it needs a pass. None of the
  new prose has had Omer's read.
- **The track question (Omer asked):** the main track fits the paper. The decision not to
  fix a track stands.
- **Cleanup:** four drafts whose text is in the paper moved to `reference/`; the C4
  transcripts draft and the journal memo deleted (`MOVES.md`). `STATUS.md` is rewritten as
  a short list of next steps.

## 2026-11-22 (night) — Second agent's paper pass: PR #140, checked, waiting for Omer

- **Instruction (Omer):** send another agent to do the Supporting Analyses pass and the
  consistency read, and have it remove the usual machine-writing habits so the text is
  easier for him to refine.
- **Done on PR #140** (three commits by the agent, one by the main session): the retired
  open-weight delivered bounds and their verdicts are out of the Supporting Analyses,
  Methods, Limitations and the appendix; retired vocabulary removed (robust floor,
  realizable benefit, sole-source, mechanism layer, claim-adverse, invocation rate);
  section references that printed empty are replaced by section names; prose pass over
  the whole paper (no em-dashes, colon reveals, rhetorical questions, emphasis words).
- **Checked by the main session:** clean compile; generated table rows identical to the
  generators; the only numbers new to the file trace to `NUMBERS.md`; placeholders intact.
  One sentence of the main session's own was corrected: the prompt-only answer format
  holds for the open-weight runs, while the Claude solve runs used the provider's
  structured output.
- **Not checked:** the 21 dropped or altered claims as content (listed in the PR body with
  old and new text); figures that still draw retired bounds; float order.
- **Outside facts found the same evening:** no rule on LLM-written text on the ICAPS 2027
  call page or in the AAAI-27 kit in the repo (AAAI has one for its own conferences);
  the call lists Shahaf Shperberg (BGU) as a program chair.
- **Decided (Omer, 2026-11-22): merge PR #140; his edits come after.** Merged as `5f1feae`.

## 2026-11-22 (late night) — Two placeholders filled: run dates, and the 0.8B on the validation tasks

- **Run and query dates** are in the paper (Models and Serving) and in `NUMBERS.md` ("Run
  and query dates") with their sources: main sweep jobs 2026-05-24 to 06-02; rerun
  2026-10-03 to 10-09; Claude queried 06-25 and 07-12 (the 07-15 stamp is a re-grade, not a
  query), 08-01 to 08-06 for PlanBench, 09-12 for the output-budget probe.
- **Qwen3.5-0.8B, main sweep, think=off** (`tools/reanalysis/s1_small_model_validation.py`,
  `NUMBERS.md` T1b): validate_domain 80.8% unaided, 87.5% tool-verified plain;
  validate_problem 51.2% unaided, 26.2% tool-verified plain, with a missing required
  argument in 375 of 600 plain trials (470 of 600 steered). **The earlier sentence said the
  model omits arguments on both tasks; that holds for validate_problem only**, and the
  paper now says so.
- Two placeholders remain, both Omer's choices: the title and the future-work list.

## 2026-11-22 (late night) — The context-window pilot, graded for RQ3: room removes empty answers, not most of the loss

- **Omer's position:** the October smoke is enough to establish the context-window point
  if compared on the same trials; no further compute is needed. He invited argument.
- **What the same data show once graded for RQ3** (`tools/reanalysis/rq3_context_pilot.py`,
  `NUMBERS.md` "RQ3 pilot"; 16K rerun against the 32K and 64K smoke runs, matched trials,
  frozen delivered grader): on simulate, empty final answers fall from 42 to 43% at 16K to
  6 to 11% at 64K, but the share of correct tool results that are lost falls only from
  92.5 to 83.8% (Gemma), 72.9 to 69.0% (9B) and 64.5 to 49.1% (35B). At 64K the lost
  answers are mostly unreadable or mismatched traces.
- **Bottom line:** agreed that no further compute is needed for this point. The point
  itself is different from what the smoke table suggested and from what the session told
  Omer earlier the same day: room in the window explains the empty answers and a part of
  the loss, and most lost traces stay lost with room.
- **Paper (PR #141):** a pilot paragraph and table in RQ3; the abstract, introduction,
  discussion, future work and conclusion no longer say the window is the main cause of
  the loss. The frontier APIs were not used: a window of 16K is a property of the
  open-weight serving setup, and the Claude runs have the output-budget probe.
- **Title (Omer):** keep the working title for now.

## 2026-11-22 (late night) — Planner failures checked; a new future direction; the advisor list

- **Omer's question:** in Corrêa et al. the model succeeds where the planner fails, which
  looks odd; did we validate the planner failures?
- **Ours, checked on the run records of the 120 larger problems:** all 231 unsolved runs
  ended in a timeout (no memory limit hit, peak 6.0 GiB under an 8 GiB cap; no error).
  Six problems unsolved at 120 s are solved at 1800 s. Nineteen are solved by no strategy
  so far, and the 1800 s pass on the hard tier is unfinished. Plans found: all VAL-valid.
  Not checked: that the nineteen are solvable. **Theirs:** we never ran their benchmark
  (it is not released), so we validated nothing about their planners' failures.
- **New direction (Omer), not for the current paper:** learning domains and action models
  with an LLM, by giving it action-model learning tools or scripts and comparing against
  such an algorithm. Recorded in `roadmap.md` §9; nothing planned or built.
- **To discuss with the advisors (Omer):** the larger-problems experiment, with the other
  items of `roadmap.md` §8.

## 2026-11-22 (late night) — Omer's challenge to the pilot: is a technical fault hiding the recovery?

- **Omer's point:** a larger window should also raise success; perhaps the pilot's setup
  was faulty or outdated, and its metrics should be discarded.
- **Checked:** no fault in the pilot's setup (same harness line, matched trials, frozen
  grader, the 2026-10-27 runs). Delivered success does rise with the window (Gemma 7.0 to
  14.9%, 35B 33.3 to 50.0%, 9B 20.2 to 22.8%). His suspicion is right about the measure:
  on simulate the "lost" share mixes three things.
  1. *No room* in the window: what the larger window removes.
  2. *Layout:* the grader reads a single JSON value; a trace written one object per line
     fails whatever its content. Reading those too lowers Gemma's loss at 64K from 83.8 to
     72.4% and the 35B's from 49.1 to 46.4%. The rerun's hand read judged 154 of 244
     undecided simulate answers right.
  3. *Conversion:* the state tool returns each state as a map of every predicate to true
     or false in functional notation, and the answer must list the true predicates only.
     Delivering a trace is a conversion, not a copy; a model got a five-state trace wrong.
- **Kept:** the pilot's figures (they are right for the frozen grader). **Changed:** the
  paper's explanation of them (RQ3 pilot paragraph, Discussion) and `NUMBERS.md` "RQ3
  pilot". **Consequence for RQ3 in general:** the simulate loss should not be described as
  the model failing to copy the tool's output.

## 2026-11-22 (late night) — PR #141 merged

- **Decided (Omer):** merge PR #141. Merged as `05ab4e5`; the paper on `main` and on
  Overleaf now has the run dates, the corrected 0.8B sentence and the context-window pilot
  of RQ3 with its explanation.
- **Still open, for discussion:** whether the abstract, introduction and conclusion qualify
  the "70 to 91% lost" figure (`STATUS.md`, item 0).

## 2026-11-22 (late night) — Figures redrawn, future-work list written and reviewed

- **Decided (Omer):** the future-work list is the four extensions plus learning action
  models with a language model (he may trim later); the smaller items PR #140 left open
  are approved as written; the five older figures are to be redrawn by a subagent and the
  Future Work section reviewed by another.
- **Figures (subagent, checked by the main session by eye and by compile):** funnel bottom
  row, solve, simulate, failure taxonomy and the token figure no longer draw the retired
  open-weight delivered bounds. Open-weight tool bars are now tool-verified rates; the
  failure figure shows the no-tools arm only, with simulate from the run-time grade; the
  token figure shows tokens only.
- **Future Work (review subagent, fixes applied):** each item now says what would be
  learned; the fifth direction names the comparison (the learning algorithm with and
  without a language model) and cites four references checked on Crossref.
- **Also corrected:** the Methods sentence that said the schema enforces required
  arguments; a Methods sentence now gives the planner's 120-second limit.
- **Not decided:** the layout-tolerant re-grade of RQ3 simulate on the full rerun.

## 2026-11-22 (late night) — PR #142 merged; Omer's read of the roadmap

- **Decided (Omer):** merge PR #142 (merged as `c4ab052`).
- **Aim (Omer):** do the best research we can for ICAPS. The track is not a concern: a
  paper written for the fuller track has what a shorter submission needs, unless
  finishing one gets in the way of the other. A thesis document is not a concern for now.
- **RQ1 metric definitions (roadmap §6):** (a) "excellent", (d) "nice"; (b), (e) and (f)
  explained to him in chat. Nothing changed.

## 2026-11-22 (late night) — RQ3 simulate graded a second time on the full rerun (Omer: yes)

- **Decided (Omer):** run the layout-tolerant re-grade; metric definitions (b), (e), (f)
  are fine after the explanation.
- **Result** (`tools/reanalysis/rq3_simulate_regrade.py`, `NUMBERS.md` "RQ3 simulate —
  layout-tolerant re-grade (post hoc)"; frozen figures stay the record): reading a trace
  written one JSON object per line lowers the lost share from 69.9-91.2% to 65.9-80.5%.
  The change is large for Gemma (about 12 points), 7 points for the 35B under the steered
  prompt, and at most 1 point in the other three cells.
- **What is still lost (1,174 answers):** 843 have no room or are empty; 219 give a
  full-length trace with a wrong step, 145 of them with only the true/false conversion
  wrong; 112 have another length or no readable trace.
- **Bottom line:** layout does not explain the finding (at most 13 points in one model).
  At 16K most lost traces have no room, and the pilot shows that room alone does not
  recover most of them. Conversion errors are real but cannot be given as a share of all
  losses.
- **Two corrections that came out of it:** the October "hand read" was made by two
  language-model readers with a third reading, not by people (paper and `NUMBERS.md` note
  corrected); 99 of the lost answers sit on the six problems whose prompt plan differs
  from the answer key's (now said in the paper).

## 2026-11-22 (late night) — The six mismatched problems stay out of the RQ3 text

- **Checked:** the six problems whose prompt plan differs from the answer key's hold 99 of
  the lost simulate answers. All 99 are empty answers, so the mismatch changed no grade;
  without them the lost share moves by at most 2 points (`NUMBERS.md`, re-grade block,
  "Sensitivity").
- **Decided (Omer):** do not mention this in the RQ3 results. It is not relevant enough to
  the result and would confuse; simplicity comes first. The one Methods sentence that says
  RQ1 leaves the six problems out stays.

## 2026-11-22 (late night) — PR #143 merged

- **Decided (Omer):** shorten the mentions of the six left-out simulate problems, push and
  merge. Methods and RQ1 now each say it in one short clause; RQ3 does not discuss it.
- PR #143 (the RQ3 simulate re-grade) is merged and on Overleaf.

## 2026-11-22 (late night) — Track view; the program-chair item dropped

- **Session's recommendation (not a decision):** the main track, as an empirical and
  evaluation paper; a demo of the tool stays possible later. The decision not to fix a
  track stands.
- **Decided (Omer):** the program-chair conflict is not an item for us. The co-author who
  chairs the program handles the conference's rule himself, as for any paper by his
  students. Removed from `roadmap.md` §8.
- **Decided (Omer):** keep the harness attachment and the anonymity sweep open until the
  submission is near; the comment switch in the tex stays on; the arXiv number in the
  appendix prompt stays as it is.

## 2026-11-23 — The JSON constraint: what the synced data holds; pilot built

- **Omer's question:** the cluster trials are all on the laptop now; is there anything in
  them to replace the JSON mistake (the format constraint on the unaided arm that never
  took effect), and should the arm be rerun?
- **What the data holds.** One run has a constraint that takes effect: the D1d probe of
  2026-10-27 (Qwen3.5-9B, 480 unaided trials, run with and without it). Nothing else.
- **Session's recommendation (not a decision): no rerun.** The unaided data is a valid
  measurement of "format asked in the prompt"; the error was in how it was described,
  and the paper already says so. A constrained arm is a new condition that cannot replace
  or be pooled with Part C, and in the probe it lowers the baseline on two tasks. In the rerun's
  unaided answers the validation tasks have no format failures at all, and solve is
  already reported under the delivered grader, which reads a plan in any layout.
- **Decided (Omer):** build the pilot. Done in PR #145: the probe graded with the frozen
  delivered grader (`tools/reanalysis/json_constraint_pilot.py`), `NUMBERS.md` ("JSON
  constraint pilot"), a table and a paragraph in the Technical Appendix, and the
  Limitations sentence.
- **Bottom line of the pilot.** Solve 25.0% to 5.0% (-20.0 points [-31.7, -10.0]);
  validate_plan 83.3% to 57.5% (-25.8 [-39.2, -13.3]), all on valid plans; the other three
  tasks within their intervals. The first tally given in chat used the strict run-time
  grade (solve 10.0% to 5.0%, simulate +6.7); the frozen delivered grade replaces it.
- **Left open:** unaided simulate in the rerun has 12 to 29% format failures by the run-time grade and no
  layout-tolerant reading yet (the RQ3 line reader covers the tool arms only).
- **Corrected the same day, on Omer's challenge** (is a wrong description not misleading,
  and how did it not misguide the models?). "The error was only in how it was described"
  is too strong. There are two wrong descriptions. The one to the reader is fixed by the
  paper's text. The one to the model is inside the data: on solve and simulate the
  no-tools system prompt says "conform to the JSON schema provided by the format
  constraint", a schema the model never received, and the simulate user prompt shows one
  example step without the outer `{"trajectory": [...]}` wrapper
  (`pddl_eval/prompts.py`, `WITHOUT_TOOLS_SYSTEM_BY_TASK`). The three validation tasks are
  untouched: their prompts ask for a `VERDICT:` line and never mention a schema.
- **What is and is not shown.** It cannot be shown that the pointer did not hold the
  unaided solve and simulate scores down. The pilot bounds it for one model on simulate
  only (shape forced: +3.3 points [-5.0, +11.7]); the constraint itself is a different
  condition, so the pilot does not test the prompt. Gemma and the 35B are unmeasured.
- **Session's recommendation (not a decision):** the run that would answer it is a small
  control, not the constrained rerun: unaided solve and simulate with a corrected system
  prompt and no constraint, three headline models, beside Part C and never in its place.
  It goes against the no-new-runs line of `roadmap.md` (2026-11-22). Omer asked for the
  plan to be drafted in a separate worktree (`development/control_prompt_fix_plan.md`,
  branch of that worktree; a proposal until he rules).

- **Decided (Omer), same day:** Limitations points to the pilot's table and quotes none
  of its figures (one model; the figures stay in the Technical Appendix). The appendix
  paragraph also says that the pilot cannot separate the prompt's reference to a schema
  from the constraint.
