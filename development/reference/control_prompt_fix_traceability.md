# Traceability map: control-prompt prereg to the analysis code (freeze gate 3)

Spec: `development/reference/control_prompt_fix_prereg.md`, sections 2 to 8 (the
revision of 2026-11-23 that registers the points of the first gate pass).
Code: `tools/reanalysis/control_prompt_fix.py` (written `CPF:<line>` below).
Fixture checks: `tests/test_control_prompt_fix.py` (written `T:<test function>`),
on the fixture built by `tests/fixtures/control_prompt_fix/build_fixture.py`.
Line numbers are those of the freeze candidate; a re-freeze re-checks them.

Each entry quotes the clause, then names the code or runtime check, then the
fixture check that exercises it. Clauses that are not testable commitments
(purpose, wording of the paper, order of human steps) are marked "not code"
with the reason. Clauses with no implementation are collected at the end under
**NOT IMPLEMENTED**.

Shared mechanics used by many entries:

- every registered constant is a raised check in `check_constants` (CPF:208-265)
  and `check_design` (CPF:268-281), called at import (CPF:291) and again in
  `main` (CPF:1527); the checks raise `RegisteredCheckFailed` and are not
  `assert` statements, so `python -O` cannot strip them (the frozen
  `constants.py` also refuses `-O`). T:test_constants flips each constant and
  each design field and sees the check fire; T:test_package_hash checks `-O`
  is refused.
- every row goes through the frozen `schema.parse_row` (CPF:387) with a
  `CellSpec` made by `dataclasses.replace` from `spec_rerun_c` (CPF:316-322),
  and through the frozen `schema._check_completeness` (CPF:394).
- grade fields are read only through `ok_of` (CPF:779, raises unless the frozen
  `ok` is a bool) and `plan_of` (CPF:785); estimator code reads `Graded` records
  (CPF:758) built in `grade_rows` (CPF:902).

---

## Section 2. Design

### 2.1 Cells

> "Three cells per model. Only the system message differs between them."

Cell names, wrapper values and folder tokens: `CELLS`, `WRAPPER`, `CELL_TOKENS`
(CPF:112-114), checked at CPF:213-217; folder names `folder_name` (CPF:312).
That only the system message differs is checked through the audit (the same set
of user texts in O, A and B, `check_users`, CPF:521) and the trial keys of the
three cells (CPF:422-434). T:test_refusals ("user-text digests differ", "cells
share fewer than 99%"), T:test_constants.

> "| **O** | the registered text of Part C, unchanged | `registered` | `no-tools` |"
> "| **A** | the reference to the schema removed | `no-pointer` | `no-tools-syspointer-off` |"
> "| **B** | the answer format stated | `format-stated` | `no-tools-sysformat` |"

CPF:112-114, CPF:213-218 (also against `control_prompts.NO_TOOLS_SYSTEM_MODES`).
T:test_constants (flips WRAPPER, CELL_TOKENS, CELLS).

> "They are fixed by their sha256 (utf-8):" (the six digests of the table)

`SYSTEM_SHA256` literals (CPF:115-122); `check_constants` recomputes the sha256
of each text from `pddl_eval/prompts.py` and `pddl_eval/control_prompts.py`
and compares it with the literal and with `control_prompts.SYSTEM_TEXT_SHA256`
(CPF:219-229). The audit compares every line against these digests (CPF:489-493).
T:test_constants (flips one digest), T:test_refusals ("audit: wrong system digest").

### 2.2 Models, tasks and size

> "Models: `Qwen/Qwen3.5-9B`, `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`,
> `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` (...). Folder tags `Qwen3_5_9B`, `gemma4_26b-a4b`, `qwen3_6_35b`."

`MODELS`, `MODEL_ORDER` (CPF:124-129), checked at CPF:230-236 against the
frozen `C.MODEL_IDS` and `C.PART_A_MODELS`; every row's model id is checked by
the frozen `parse_row` against the cell's tag; audit lines (CPF:507) and
`client_settings.json` `hf_model` (CPF:552-556) too. T:test_constants.

> "Thinking off."

`C.THINK == "off"` (CPF:238); the frozen `parse_row` refuses a resume key whose
think is not "off"; `client_settings.json` `think_mode_token` and every
summary's `think` (CPF:597-618). T:test_constants.

> "Tasks: solve and simulate."

`TASKS` (CPF:130, checked CPF:212); the cell spec registers only these two
tasks, so the frozen loader refuses any other (CPF:316-322). T:test_constants.

> "Per model, task and cell: the 100 problems of Part C (20 domains, 5 problems each)
> by the three plain wordings (v11, v12, v13) = **300 trials**."

`REGISTERED.per_task_cell = 300`, `per_task_wording = 100`, `k_domains = 20`
(CPF:185-186, checked CPF:272-276); `WORDINGS` (CPF:131, checked CPF:237);
completeness per task and wording by the frozen `_check_completeness`
(CPF:394); every graded cell holds that many trials (CPF:1188) and every
contrast that many pairs (CPF:1221). T:test_refusals ("a short cell"),
T:test_base (n = 60 in the fixture design), T:test_constants.

> "Per cell folder (one model, one system text, two tasks): 600 rows, 200 per wording."

`per_folder = 600`, `per_wording = 200` (CPF:185-186, CPF:273-274); frozen
completeness (CPF:394). T:test_refusals ("a short cell").

> "Total: 3 models by 3 cells by 600 = **5,400 trials**."

CPF:277. T:test_constants.

### 2.3 What is identical to Part C

> "Everything but the system message, and the date."

Not one check; the items below.

> "The user prompts v11 to v13, byte for byte."

Within the control: the same set of user-text sha256 in O, A and B
(`check_users`, CPF:521). Against Part C: the trial keys equal Part C's
(CPF:437-447). The user text itself is not compared with Part C's: see NOT
IMPLEMENTED 1.

> "The request still carries the `guided_json` field in all three cells. The server
> still drops it. Taking it out would be a second change." "No decoder constraint in any cell."

NOT IMPLEMENTED 2.

> "The 16,384-token window. Output cap 8,192 tokens on solve and 6,144 on simulate.
> Temperature 0. Four requests at a time. Answers stored up to 65,536 characters."

The apparatus preconditions of section 7 (below, `check_apparatus`,
CPF:590-626); storage: the frozen loader refuses an answer longer than 65,536
characters and `STORAGE_CAP` is checked against the frozen constant (CPF:242);
the frozen loader also refuses a row whose prompt plus clipped allowance exceeds
the 16,384 window. "Four requests at a time": NOT IMPLEMENTED 3.

> "vLLM 0.20.2 from the shared `~/vllm.sif`. GPU class `rtx_6000`, one model alone on its
> card, `--mem=48G`."

vLLM version: section 7 item 7. GPU class and memory: NOT IMPLEMENTED 3.

> "The harness: `main` at the merge commit of PR #147, recorded in section 9. That PR is
> additive; no file of the frozen package hash `822aace9…` differs from the harness of Part C."

The analysis side: `rq1_metrics.load_rerun_cells` halts unless the frozen
package hash is `822aace9…` (live mode, CPF:944-958); the frozen files are part
of this script's package hash (`DEPENDENCIES`, CPF:85-99). T:test_package_hash
("the frozen rerun package hash is unchanged"). The harness commit on the
cluster is a section 9 record (not code: no row or summary carries a commit).

### 2.4 One window

> "All nine cells are submitted in one array job (...). A cell that stops at its time limit
> is resumed in place (same folder). The job id of the submission and of every resume, and
> the dates of the run, are recorded in section 9 from the submit output and the cluster-ops
> status script, and the readout prints the dates (only the last job id of a cell is kept in its folder)."

The dates are given by `--control-dates` (required, CPF:1533-1534) and printed in
the header and in every R4 sentence (CPF:1153-1160); the last job id of each
cell, from its `client_settings.json`, is written to the output
(`audit.settings`, CPF:645). The job ids of every submission and resume are a
section 9 record (not code). T:test_base ("R4 carries both dates").

> "Run tag of the full run: `control-promptfix`. Folders:
> `slurm_vllm_<model tag>_off_<cell token>_control-promptfix`, synced to `results/control-promptfix/`."

`RUN_TAG` (CPF:137, checked CPF:244), `folder_name` (CPF:312), default
`--control-root` `<results>/control-promptfix` (CPF:1568). T:test_constants.

### 2.5 A new condition

> "The control's rows are never pooled with Part C, with the main sweep or with the smoke."

The control folders carry the control's run tag (CPF:312) and are read only by
`load_control` (CPF:410); Part C and Part A rows enter only C3, C4 and the
reproduction checks, each in its own column (CPF:1174-1229). The smoke is read
only by `--smoke-check`, which builds smoke folder names only (CPF:665-667); the
frozen `load_cell` refuses any folder named "smoke". T:test_smoke ("the
full-run folders are never read").

> "No control cell stands in for a Part C cell in a filed readout. Part C stays the
> registered unaided input of the rerun's E2 contrast."

Not code: the script writes only its own outputs
(`tools/reanalysis/out/control_prompt_fix.*`, NUMBERS tag CONTROL-PROMPT-FIX).

---

## Section 3. Measures

> "A trial is right when the frozen delivered grader says so:
> `tools.delivered_rerun.grade.grade`, imported unchanged from the package with hash `822aace9…`.
> On solve the plan it reads must pass the validator; on simulate the trace it reads must
> equal the answer key. Rates are per model, task and cell, over the three wordings together (n = 300)."

`frozen_grades` (CPF:917-921) calls `G.grade` on every control row, its solve
verdicts from the injected route; `rate` over the 300 graded trials of each
(model, task, cell) (CPF:1190-1201, size checked CPF:1188). T:test_base,
T:test_planted_answers.

> "**The second reading: layout-tolerant.** Registered beside the frozen grade for every
> rate and every contrast. It is the reading of the filed re-grade
> (`tools/reanalysis/rq1_layout_regrade.py`), imported unchanged:"

Every rate carries `frozen` and `second` (CPF:1198); every contrast is computed
under both readings (CPF:1203-1229, count checked CPF:1229). `second_reading`
(CPF:877-899) calls `rq1_layout_regrade.block_plan`, `rq1_layout_regrade.lower`,
`iss027_common.has_upper` and `rq3_context_pilot.line_reader_exact`, all
imported unchanged. The composition of those functions lives inside
`rq1_layout_regrade.main()` (lines 196-217 of that file) and is not a function
there, so it is re-implemented in `second_reading` line for line. That it
equals the filed re-grade is checked on every run by `check_filed_regrade`
(CPF:999-1017) on the Part C and Part A (plain) cells; the dry run on the
existing data reproduced all 12 filed cells. T:test_refusals ("the second
reading does not reproduce the filed re-grade").

> "solve. When the answer has fenced code blocks and the last closed one holds a plan,
> that plan is the delivered plan and replaces the frozen reading, whichever way that moves
> the grade. (...) This is the function `block_plan`. Any other answer keeps its frozen grade."

CPF:887-891. T:test_planted_answers ("JSON plan in the last block", "right to
wrong", "block of action lines", "unclosed fence"), T:test_base.

> "simulate. A trace written one JSON object per line also counts when it equals the answer
> key exactly (`rq3_context_pilot.line_reader_exact`). An answer the frozen grader already
> counts right stays right."

CPF:897-899. T:test_planted_answers ("one object per line equal to the key",
"... not equal to the key"), T:test_base.

> "**Validator.** Every solve plan of the control, under both readings, is validated in
> process with pddl-pyvalidator **0.1.5**, (...) through the route of the filed re-grade
> (the plugin's validator server, loaded in process). The analysis halts on any other release."

One `Verdicts` object (CPF:807-825) for both readings: live `live_route`
(CPF:828-845; `iss027_common.load_validator` and `call_tool`, verdict by
`scoring._parse_validation_verdict`), fixture `table_route` (CPF:848-854).
Release: CPF:1573-1580 (`iss027_common.environment`, `check_environment`,
`env["pyval"] == PYVALIDATOR`), `PYVALIDATOR` checked CPF:247. Live only; the
fixture has no validator, the dry run exercises it. T:test_constants.

> "Before it validates a new plan it checks that this route returns the stored verdict for
> every plan the frozen grade used on the rerun's solve rows that the analysis reads (Part C,
> and the plain wording of Part A for C4)."

`check_route` (CPF:857-874) on the Part C and Part A plain solve rows, called
in `analyse` (CPF:1171) before any control row is graded. T:test_refusals ("the
route disagrees with a stored verdict"), T:test_base (40 plans checked).

> "**Case folded (descriptive, not a registered reading).** (...) the same reading with every
> deciding plan sent in lower case. (...) No reading of section 5 uses it."

`folded` in `second_reading` (CPF:892-895); no reading function reads it
(CPF:1091-1160). T:test_planted_answers ("caps_block"), T:test_base.

---

## Section 4. Contrasts and statistics

> "All contrasts are paired on the trial key (task, domain, problem, plan label, wording),
> per model and task, in points, under both readings."

`paired` (CPF:1037-1046) on the frozen `Row.trial_key`, per model, task and
reading (CPF:1203-1229). T:test_base.

> The table of C1 (A minus O), C2 (B minus O), C3 (O minus Part C), C4 (tools, plain wording
> (Part A of the rerun) minus B), six each.

`sides` (CPF:1204); six per name, checked by the Holm family size (CPF:1224)
and the total (CPF:1229). T:test_base (all 48 values).

> "C3 and C4 use rows of the delivered rerun for the same 300 trial keys. Their frozen grades
> are recomputed with the frozen functions and must reproduce the filed readout, and their
> second reading must reproduce the filed re-grade, or the analysis halts."

Rows: `load_rerun_live` (CPF:944-958). Frozen: `rq1_metrics.load_rerun_cells`
(live) and `check_filed_readout` (CPF:978-996, both modes: E1 counts of the
plain tool arm, E2 unaided rate). Second reading: `check_filed_regrade`
(CPF:999-1017). 300 pairs per contrast (CPF:1221). T:test_refusals ("the rerun
does not reproduce the filed readout", "... filed re-grade").

> "**Intervals.** 95% percentile intervals from the frozen domain-cluster bootstrap of the rerun
> (`tools.delivered_rerun.stats.cluster_bootstrap`): the 20 domains are the clusters, 10,000
> resamples, seed 20261002. The analysis asserts 20 domains in every contrast. Rates carry the same interval."

`boot` (CPF:1020-1024) calls the frozen bootstrap with `k_expected =
design.k_domains` (20 live, CPF:276) and re-checks `k` and the level; `LEVEL`,
`B_BOOT`, `SEED` checked against the frozen constants (CPF:249-251); rates use
the same `boot` (CPF:1031). T:test_base, T:test_constants.

> "**Margin.** M = **5 points**"

`MARGIN` (CPF:143, checked CPF:248). T:test_constants.

> "criterion met: the whole 95% interval lies inside [−5, +5], endpoints included; a
> difference is shown: the 95% interval excludes 0; unresolved: neither." "A contrast can
> meet the criterion and show a difference at once"

`contrast_label` (CPF:1049-1060). T:test_base (the endpoint exactly 5.0 is
inside; unresolved cases), T:test_labels ("met and shown at once", "inclusive
endpoints", "lo exactly 0 does not exclude 0"). The fixture cannot hold a
contrast that is met and shown at once (3 trials per domain); T:test_labels
covers it on synthetic values.

> "**The reading of C4.** "Tools ahead" when the interval is above 0, "no tools ahead" when
> it is below 0, "no difference shown" otherwise. The margin is not applied to C4."

`c4_label` (CPF:1063-1072). T:test_base, T:test_labels.

> "Beside every contrast the analysis also reports an exact sign-flip p-value over the 20
> domains, Holm-adjusted across the six contrasts of the same name and the same reading (...).
> A difference whose interval excludes 0 and whose Holm-adjusted p-value is 0.05 or more is
> reported as "a difference is shown (not after Holm)", with those words. The same words are
> added to a C4 label ("tools ahead (not after Holm)") and are printed as a note beside any
> sentence of R1, R2 or R4 that rests on such a contrast."

Frozen `stats.signflip_exact_p` on `stats.domain_sums` (CPF:1044); frozen
`stats.holm` per name and reading, family of 6 checked (CPF:1224-1227);
`HOLM_FAMILY`, `HOLM_ALPHA` checked (CPF:252-253). The words: C1 to C3
CPF:1057-1059, C4 CPF:1072; the notes beside R1, R2 (CPF:1139) and R4
(CPF:1160) from `holm_notes` (CPF:1119-1122), printed by `render`
(CPF:1394-1407). T:test_base (Qwen3.6-35B simulate C1 and C2; "R1 carries the
Holm note", "R2 Holm note", "R4 carries no Holm note where none applies"),
T:test_labels ("C4 no tools ahead, not after Holm", "R4 Holm note").

> "The count of contrasts (24, each under two readings) is stated with every table."

`common` sentence (CPF:1331), written under every table heading. T:test_base
("markdown states the count of contrasts with every table").

---

## Section 5. Registered readings

> "Each is stated per model and task; no reading pools models or tasks."

`readings` per (model, task) (CPF:1232-1249). T:test_base.

> "**How R1 and R2 are read.** Each contrast has its label under each reading (section 4),
> and the two labels are always printed. On top of them the readout gives a sentence for each
> of the cases below whose condition holds, in the order listed. More than one can hold (...).
> "Unresolved" is given only when no case holds. "A rise" means the 95% interval is above 0,
> "a fall" that it is below 0. A pattern the cases do not name (for example a rise under the
> second reading only) gets no sentence beyond its two labels."

`r12_reading` (CPF:1125-1139): both labels with their intervals (`labels`);
`holds` evaluates (a) to (d) (CPF:1131-1132); a sentence for every case that
holds, in the order a, b, c, d; (e) only when none holds (CPF:1133); `rise` is
lo > 0, `fall` is hi < 0 (CPF:1079-1084). The labels and sentences are printed
together (CPF:1399-1404). T:test_base (each reading's labels printed; the five
cases), T:test_labels ("a sentence for a and for b, in order", "met and a fall
-> a, d", "a rise under the second reading only"). See the last section for the
one point where this paragraph and case (e) disagree.

> R1: "(a) C1 meets the criterion under both readings: "removing the reference to the schema
> did not move the unaided baseline by more than 5 points"." "(b) C1 shows a rise under the
> frozen grade and under the second reading: "the wrong reference lowered the unaided
> baseline", with both estimates and intervals." "(c) C1 shows a rise under the frozen grade
> and no rise under the second reading: "the wrong reference changed how the answers were
> laid out, and the grader did not read that layout; what the models wrote did not change by
> more than the second reading shows" (the layout-only reading)." "(d) C1 shows a fall under
> the frozen grade: "a fall, reported as it is: the reference, wrong as it was, did not cost
> the model anything on that task"." "(e) none of these: "unresolved", with both intervals."

`R_SENTENCES["C1"]` (CPF:1091-1103), verbatim; (b) and (e) carry both estimates
and intervals (`WITH_INTERVALS`, CPF:1116). T:test_base ("R1 (a) sentence" to
"R1 (e) sentence", each checked verbatim).

> R2: "(a) (...) "stating the answer format did not move the unaided baseline by more than 5
> points"." "(b) C2 shows a rise under both readings: "stating the answer format raises the
> unaided baseline, and not through layout alone", with both estimates and intervals." "(c) C2
> shows a rise under the frozen grade and no rise under the second reading: "stating the answer
> format raises the frozen grade through layout: the answers come in a layout the grader reads;
> what the models wrote did not change by more than the second reading shows"." "(d) C2 shows a
> fall under the frozen grade: "a fall, reported as it is: stating the answer format lowered the
> unaided baseline on that task"." "(e) none of these: "unresolved", with both intervals."
> "R2 does not decide what the paper reports as the baseline; section 6 does."

`R_SENTENCES["C2"]` (CPF:1104-1115), verbatim. T:test_base ("R2 (a)", "R2 (b)",
"R2 (c) sentence"), T:test_labels ("R2 fall sentence"). The last sentence is not
code (section 6 is applied in the rate table, CPF:1356-1362).

> "**R3. Drift. (C3, frozen grade.)** If C3 meets the criterion (...) the setup is taken to
> reproduce Part C there. If not, the readout says "the setup moved between Part C and the
> control for this model and task", gives the estimate, and the levels of the control are not
> set beside the levels of Part C for that model and task. C1 and C2 do not depend on R3"

`r3_reading` (CPF:1142-1150) on the frozen C3; `render` leaves Part C out of
the rate table for that model and task and says so (CPF:1353-1370); no reading
of C1 or C2 reads R3 (CPF:1241-1242). T:test_base ("R3 moved sentence", "R3:
Part C's level not set beside the control where the setup moved"), T:test_labels.

> "**R4.** Reported per model and task under both readings, always with the dates of the two
> runs (Part A: 2026-10-03 to 2026-10-09; the control: the dates of section 9). Where R3 says the
> setup moved, the C4 entry of that model and task carries the words "across a setup that moved"."

`r4_reading` (CPF:1153-1160); `PART_A_DATES` checked (CPF:258);
`--control-dates` required (CPF:1533-1534). T:test_base ("R4 carries both
dates", "across a setup that moved"), T:test_labels.

> "The rerun's E2 (...) stays in the appendix as the registered contrast." "A reading that
> would be wrong, named in advance."

Not code (paper text). No label says "unchanged" or "as good as".

---

## Section 6. The reporting rule

> Rules 1 to 3 (cell B the reported baseline; cell O the anchor; Part C in the appendix) and
> 6 (no paper edit)

Paper text; rules 1 and 2 are stated in the header of the rate table
(CPF:1356-1362). The script never writes under `paper/`.

> "4. **Both readings are registered for every rate and every contrast.**"

CPF:1198, CPF:1203-1229. T:test_base.

> "5. (...) If the two differ by more than 5 points for a model and task, the text gives both
> figures wherever it gives one for that model and task."

`rule5` (CPF:1246-1247), written in the readings table (CPF:1408-1412);
`QUOTE_BOTH_POINTS` checked (CPF:259). T:test_base (Gemma solve flagged;
Qwen3.5-9B solve, a 1.7-point gap, not).

---

## Section 7. Execution

> "Order. (...) Every SSH or SLURM action needs Omer's explicit go-ahead"

Not code; the script makes no SSH or SLURM call.

> "Smoke. (...) `--partial 1` (the first problem of every domain: 120 rows per cell folder),
> run tag `control-promptfix-smoke`, all nine cells. Never pooled. Checks allowed on smoke
> output, and nothing else:"

`SMOKE` (CPF:187-188, checked CPF:284-289), `SMOKE_TAG` (CPF:138, checked
CPF:245); `smoke_check` (CPF:657-753) builds the nine smoke folder names only and
runs items 1 to 7. T:test_smoke.

> "1. every job completes (job states are read with the cluster-ops status script and recorded
> in section 10; they cannot be seen in the synced files), and every cell folder holds its 120 rows;"

Rows: `read_folder` raising `IncompleteCell` (CPF:669-671). Job states: printed
reminder (CPF:750-751); the states themselves are a section 10 record.
T:test_smoke ("a short cell fails").

> "2. the frozen loader reads every row; no exception or infrastructure-failure row; no row cut
> by storage; no half-written line;"

CPF:673-682. T:test_smoke ("a row cut by storage", "an exception row").

> "3. in every cell, at least 95% of the stored answers are non-empty (...). An answer is empty
> when nothing is left after the leaked thought-channel prefix and white space are removed;"

CPF:683-686 (`strip_leaked_channel_prefix(...).strip()`; `SMOKE_NONEMPTY`
checked CPF:260). T:test_smoke (7 of 120 empty fails; 6 of 120 passes).

> "4. the audit log of each cell (`system_prompt_audit.jsonl`): every line's system text has the
> sha256 this registration gives for that cell and task; the stored text, where a line carries
> it, is that text byte for byte; cell O is marked not swapped and cells A and B swapped; no line
> has tools; the model named is the cell's model; and each task has at least as many lines as the
> cell has rows of that task, so that the log covers every trial;"

`check_audit` (CPF:472-518), line shape of `vllm_client._write_audit`: digest
(CPF:489-493), stored text (CPF:494-498), mode (CPF:499-501), swapped
(CPF:502-504), no tools (CPF:505-506), model (CPF:507-508), lines per task
(CPF:513-517). T:test_refusals ("wrong system digest", "the stored text is not
the registered text", "cell O marked swapped", "cell A marked not swapped", "a
line with tools", "a missing audit file", "fewer lines than rows").

> "5. the user messages are the same in the three cells of a model: the same set of user-text
> sha256. A text that appears more often in one cell than in another is allowed (a job that is
> stopped and resumed sends its unfinished requests again); the number of such extra lines is
> reported per cell;"

`check_users` (CPF:521-532): the three sets must be equal; the extra lines of a
cell are its lines above the smallest count of the three, per text. Reported
per cell in the live output (`audit.extra_user_lines`, CPF:650-652) and printed
by the smoke check (CPF:744-746). T:test_base ("extra user-message lines
reported per cell": the fixture's re-sent line in Qwen3.6-35B A counts 1),
T:test_refusals ("user-text digests differ": a text in one cell and missing in
another halts), T:test_smoke ("a re-sent request passes item 5 and is
counted", "differing user messages fail item 5").

> "6. `client_settings.json` of each cell names that cell's system text;"

`check_settings` (CPF:548-562): `no_tools_system`, also `cond`, `hf_model` and
the audit log path. T:test_refusals, T:test_smoke ("wrong client settings fails
item 6").

> "7. the serve log of the job that wrote each cell shows vLLM 0.20.2 and no other version.
> Serve logs stay on the cluster (`cluster-experimenting/logs/`); they are copied to the laptop
> for this check, or the version line is read on the cluster and the reading is recorded as a
> note that the check prints and section 10 keeps."

`check_serve_log` (CPF:569-587): `<job id>-vllm-<model tag>.log` of the job
named in `client_settings.json`, in the folder `--serve-logs` names; at least
one banner and every banner 0.20.2 (CPF:582-586). Without the logs, the note of
`--version-checked-by-hand` is printed (CPF:733-740) or the item is NOT CHECKED
and the check fails. T:test_refusals ("serve log shows another vLLM", "a
missing serve log"), T:test_smoke ("item 7 NOT CHECKED", "checked by hand with a
note").

> "The check is a mode of the analysis script (`--smoke-check`). It prints these items and no
> success rate, no failure-reason count and no answer text."

CPF:1524-1525, CPF:657-753. T:test_smoke ("no answer text printed", "no rate or
count printed for item 3", "no percentage anywhere but the threshold").

> "**The same audit checks (items 4 to 7) are preconditions of the analysis** on the full run.
> If one fails, the analysis halts before any answer is graded."

`audit_control` (CPF:629-654) runs in `main` before the rerun is loaded and
before any control row is graded (CPF:1571-1572; fixture CPF:1548-1550). Item
7: `--serve-logs`, or the note, recorded in the output; with neither, a halt
(CPF:635-637). T:test_refusals (every audit refusal halts with nothing written;
"item 7 by hand"; "item 7 neither checked nor noted").

> "**Apparatus checks, also preconditions of the analysis** (they follow section 2.3):
> `client_settings.json` gives the 16,384-token window and thinking off; the run's summary gives
> the 16,384-token window, temperature 0, thinking off, the no-tools condition and the cell's
> model; no answer is longer than its task's output cap; and every answer that stopped at the cap,
> without a turn whose allowance was lowered to fit the window, used exactly 8,192 tokens on solve
> or 6,144 on simulate (true of every such row of Part C)."

`check_apparatus` (CPF:590-626): settings (CPF:597-602), summaries
(CPF:603-618), caps (CPF:619-625); called from `audit_control` (CPF:648-649).
T:test_refusals ("apparatus: context window in client_settings.json", "... in a
summary").

> "**During the run.** Monitoring reads row counts and job states only. No success rate or
> failure-reason count of any cell is computed before the freeze."

Not code for the run; the live mode refuses to read a row before the freeze
(below) and the smoke check prints no rate.

> "**Stop rules.** A cell folder is VOID if more than 1% of its rows (more than 6 of 600) are
> exception or infrastructure-failure rows. Exception rows are those of the rerun's rule:
> `failure_reason` "exception" or "ollama_parse_error", or the empty-message exception shape.
> When a cell is VOID, all three cells of that model are run again from scratch, together, under
> the run tag `control-promptfix-r2` (...)."

`check_void` (CPF:401-407) on the frozen `Row.is_exception` or `infra_failure`;
`VOID_FRAC` and `C.EXCEPTION_REASONS` checked (CPF:261-263); the halt names the
rerun; `--r2-models` reads that model's cells under `R2_TAG` (CPF:1564-1567).
T:test_refusals ("exception rows above 1% -> VOID").

> "**Completeness.** 600 rows per cell folder, 200 per wording, 300 per task. A short cell is
> resumed, not analysed. The three cells of a model must hold the same 600 trial keys. A model
> whose cells share fewer than 99% of their keys is VOID; this is checked first. Then each
> task's 300 keys must equal the keys of Part C for that model and task; a difference halts the
> analysis. So in an analysed run the unpaired count is zero, and it is printed."

Frozen completeness (CPF:394); `check_pairing` first (CPF:422-434, in `main`
right after loading, CPF:1570); `check_keys_equal_part_c` then (CPF:437-447,
CPF:1169); the unpaired count of every contrast (CPF:1040) is a column of the
contrast tables. T:test_refusals ("a short cell", "cells share fewer than 99%",
"keys that differ from Part C's"), T:test_base (unpaired 0).

> "**Exception rows at or under 1%** stay in the denominator and are graded as they are (an
> empty answer is wrong). Their count is reported per cell."

Kept by `check_void`; graded by the frozen grader (reason "exception"); counted
per folder (`corpus`, CPF:1279) and per cell and task (`secondary`).
T:test_base ("exception rows kept and counted", "exception row graded as it is").

> "**Rows cut by storage.** (...) A cut row is accepted only if the answer also stopped at the
> output cap; it is then graded on its stored 65,536 characters and counted in the output. Any
> other cut row halts the analysis."

`read_folder` (CPF:378-393). T:test_refusals ("a storage-cut row that did not
stop at the output cap"), T:test_base ("storage-cut rows accepted and counted").

> "**Duplicate trial keys** in a cell folder halt the analysis. **Half-written lines** (a record
> cut when a job is stopped) are counted, reported and skipped, as the frozen loader of the rerun
> does; the completeness rule still has to hold without them."

Duplicates CPF:388-389; half-written lines CPF:375-377 (counted in `Folder`,
reported in `corpus`), completeness after them (CPF:394). T:test_refusals
("duplicate trial key"). Half-written lines in live mode are not planted in the
fixture (the smoke check fails them, item 2).

> "**The analysis does not read a row of the full run** unless it is started with the package
> hash recorded in section 9 (`--i-have-frozen`)."

`package_sha256` (CPF:303-308) over this script and `DEPENDENCIES` (CPF:85-99);
live mode compares it before any read (CPF:1556-1558). T:test_live_gate,
T:test_package_hash.

---

## Section 8. Secondary, descriptive

> "the rate by wording (v11, v12, v13), under both readings;"

`by_wording` (CPF:1305). T:test_base.

> "the layout of the answer: on solve, whether the last code block holds a JSON plan, action
> lines, or there is no plan block; on simulate, whether the answer is one JSON object (the whole
> answer, after the leaked prefix and one enclosing code fence are removed, parses as an object),
> one object per line (at least two lines that each parse as an object), or neither;"

`layout` (CPF:1309): solve from `block_plan` (CPF:887-891), simulate from
`simulate_layout` (CPF:789-804: `_strip_md_fence` after the prefix strip, then
at least two object lines). T:test_base (layout checks).

> "answers that stopped at the output cap; mean answer tokens;"

CPF:1310-1311. T:test_base.

> "the frozen grade's reason for each failure, and how each trial moved from O to A and from O to B;"

`failure_reasons` (CPF:1314), `moves_from_O` (CPF:1319). T:test_base.

> "the case-folded column of section 3;" "the Holm-adjusted p-values of section 4."

`folded_k` (CPF:1316), the rate table, `p_holm` on every contrast. T:test_base.

> "**Tripwires that halt the readout until audited** (the audit is recorded in the readout): a
> count of right answers that is the same in all nine cells of a task, under either reading; a
> cell of O whose frozen rate is more than 20 points from the Part C rate of the same model and
> task; a cell in which the frozen grader can read no answer at all on one of the two tasks."

`fired` (CPF:1251-1269): T1 per task and reading (CPF:1252-1258); T2
(CPF:1259-1264, `TRIPWIRE_POINTS` checked CPF:265); T3 per cell and task
(CPF:1265-1269, "readable" = a frozen reason outside `UNREADABLE`, CPF:773). A
fired tripwire halts unless released with `--audited-tripwires` and
`--audit-notes` (the frozen `run.load_audit_notes`, CPF:1530); notes for
tripwires that did not fire halt; the notes are written to the output
(CPF:1270-1276). T:test_tripwires (T1; T2 with and without a note; T3 on one
task only).

---

## NOT IMPLEMENTED

1. **2.3 "The user prompts v11 to v13, byte for byte", against Part C.** Part C
   has no audit log and its rows do not store the user text, so the bytes cannot
   be compared. What is checked: the trial keys equal Part C's, and the user
   texts are the same set in O, A and B.
2. **2.3 "The request still carries the `guided_json` field" and "No decoder
   constraint in any cell".** No file of a cell records the request body; the
   behaviour is fixed by the harness commit of section 9.
3. **2.3 "Four requests at a time", "GPU class `rtx_6000`, one model alone on its
   card, `--mem=48G`".** Not in the synced files (they are in the job's `.out`
   and in SLURM accounting on the cluster).

Removed from the list by the revision: the harness commit, the job ids of every
resume and the job states of smoke item 1 are now registered as section 9 and
section 10 records, and the readout prints the dates and the last job id, which
is what the code does.

## Where the revised prereg and the code may still disagree

- **Section 5, "How R1 and R2 are read" against case (e).** The paragraph says a
  pattern the cases do not name, "for example a rise under the second reading
  only", gets "no sentence beyond its two labels". Case (e) says "none of these:
  "unresolved"", and the paragraph says "Unresolved is given only when no case
  holds". A rise under the second reading only (with the frozen interval
  including 0) holds none of (a) to (d), so (e) gives it "unresolved". The code
  follows (e) as written: "unresolved" with both intervals, the two labels beside
  it (T:test_labels, "a rise under the second reading only"). If the paragraph
  is meant, (e) should read: "(e) none of (a) to (d), and neither reading shows a
  difference: "unresolved", with both intervals; any other pattern gets its two
  labels only."
