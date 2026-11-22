
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
