
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
