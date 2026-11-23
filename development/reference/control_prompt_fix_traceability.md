# Traceability map: control-prompt prereg to the analysis code (freeze gate 3)

Spec: `development/reference/control_prompt_fix_prereg.md`, sections 2 to 8, as
revised after the independent review (gate 5).
Code: `tools/reanalysis/control_prompt_fix.py` (written `CPF:<line>` below; a
function is cited by its name and first line).
Fixture checks: `tests/test_control_prompt_fix.py` (written `T:<test function>`),
on the fixture built by `tests/fixtures/control_prompt_fix/build_fixture.py`.
Line numbers are those of the freeze candidate; a re-freeze re-checks them.

Each entry quotes the clause, then names the code or runtime check, then the
fixture check that exercises it. Clauses that are not testable commitments
(purpose, wording of the paper, order of human steps) are marked "not code"
with the reason. Clauses with no implementation are collected at the end under
**NOT IMPLEMENTED**.

Shared mechanics used by many entries:

- every registered constant is a raised check in `check_constants` (CPF:209)
  and `check_design` (CPF:272), called at import (CPF:296) and again in `main`
  (CPF:1656); the checks raise `RegisteredCheckFailed` and are not `assert`
  statements, so `python -O` cannot strip them (the frozen `constants.py` also
  refuses `-O`). T:test_constants flips each constant and each design field and
  sees the check fire; T:test_package_hash checks `-O` is refused.
- every row goes through the frozen `schema.parse_row` in `read_folder`
  (CPF:354) with a `CellSpec` made by `dataclasses.replace` from `spec_rerun_c`
  (`control_spec`, CPF:321), and through the frozen `schema._check_completeness`
  (CPF:403).
- grade fields are read only through `ok_of` (CPF:851, raises unless the frozen
  `ok` is a bool) and `plan_of` (CPF:857); estimator code reads `Graded` records
  (CPF:813) built in `grade_rows` (CPF:999).

---

## Section 2. Design

### 2.1 Cells

> "Three cells per model. Only the system message differs between them."

`CELLS`, `WRAPPER`, `CELL_TOKENS` (CPF:112-114), checked in `check_constants`
(CPF:214-219); folder names `folder_name` (CPF:317). That only the system
message differs is checked through the audit (`check_audit`, CPF:519;
`check_users`, CPF:573) and the trial keys (`check_pairing`, CPF:469).
T:test_refusals, T:test_constants.

> The table of cells O, A, B with wrapper values `registered`, `no-pointer`,
> `format-stated` and folder tokens `no-tools`, `no-tools-syspointer-off`, `no-tools-sysformat`.

CPF:112-114, CPF:214-219 (also against `control_prompts.NO_TOOLS_SYSTEM_MODES`).
T:test_constants.

> "They are fixed by their sha256 (utf-8):" (the six digests)

`SYSTEM_SHA256` (CPF:115-122); `check_constants` recomputes each digest from
`pddl_eval/prompts.py` and `pddl_eval/control_prompts.py` and compares it with
the literal and with `control_prompts.SYSTEM_TEXT_SHA256` (CPF:221-230); every
audit line is compared with them (CPF:538). T:test_constants, T:test_refusals
("audit: wrong system digest"). (Not touched in this pass: the B texts are under
decision.)

### 2.2 Models, tasks and size

> "Models: `Qwen/Qwen3.5-9B`, `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`,
> `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` (...). Folder tags `Qwen3_5_9B`, `gemma4_26b-a4b`, `qwen3_6_35b`."

`MODELS`, `MODEL_ORDER` (CPF:124-129), checked at CPF:231-237 against the frozen
`C.MODEL_IDS`; the frozen loader checks every row's model; the audit (CPF:555)
and `client_settings.json` (CPF:604) too. T:test_constants, T:test_review_refusals
("audit: the wrong model", "client_settings.json hf_model").

> "Thinking off." "Tasks: solve and simulate."

`C.THINK` (CPF:239) and the frozen loader's key check; `TASKS` (CPF:130, checked
CPF:213); the cell spec admits only these tasks. T:test_constants.

> "Per model, task and cell: (...) = **300 trials**." "Per cell folder (...): 600 rows,
> 200 per wording." "Total: 3 models by 3 cells by 600 = **5,400 trials**."

`REGISTERED` (CPF:186) checked in `check_design` (CPF:275-282); `WORDINGS`
(CPF:131, CPF:238); frozen completeness (CPF:403); graded cells and contrasts
hold 300 (in `analyse`, CPF:1271). T:test_refusals ("a short cell"),
T:test_constants.

### 2.3 What is identical to Part C

> "The user prompts v11 to v13, byte for byte."

Within the control: the same set of user texts in O, A and B (`check_users`).
Against Part C: equal trial keys (`check_keys_equal_part_c`, CPF:484). See NOT
IMPLEMENTED 1.

> "The request still carries the `guided_json` field (...)." "No decoder constraint in any cell."

NOT IMPLEMENTED 2.

> "The 16,384-token window. Output cap 8,192 tokens on solve and 6,144 on simulate.
> Temperature 0. Four requests at a time. Answers stored up to 65,536 characters."

The apparatus preconditions of section 7 (`check_apparatus`, CPF:643);
`OUTPUT_CAP` equals the harness's `runner.DEFAULT_NUM_PREDICT` (CPF:242-244);
storage: the frozen loader refuses an answer over 65,536 characters
(`STORAGE_CAP`, CPF:245). "Four requests at a time": NOT IMPLEMENTED 3.

> "vLLM 0.20.2 from the shared `~/vllm.sif`. GPU class `rtx_6000`, one model alone on its card, `--mem=48G`."

vLLM: section 7 item 7. GPU class and memory: NOT IMPLEMENTED 3.

> "The harness: `main` at the merge commit of PR #147, recorded in section 9. (...) no file of
> the frozen package hash `822aace9…` differs from the harness of Part C."

`rq1_metrics.load_rerun_cells` halts unless the frozen package hash is
`822aace9…` (`load_rerun_live`, CPF:1042); the frozen files are hashed with this
script (`DEPENDENCIES`, CPF:85-99). T:test_package_hash. The commit itself is a
section 9 record (not code).

### 2.4 One window

> "(...) The job id of the submission and of every resume, and the dates of the run, are
> recorded in section 9 from the submit output and the cluster-ops status script, and the
> readout prints the dates (only the last job id of a cell is kept in its folder)."

`--control-dates` is required (CPF:1663) and printed in the header and in every R4
sentence (`r4_reading`, CPF:1260); the last job id of each cell is written to
the output (`audit_control`, CPF:682). The job ids are a section 9 record (not
code). T:test_base ("R4 carries both dates").

> "Run tag of the full run: `control-promptfix`. Folders: (...) synced to `results/control-promptfix/`."

`RUN_TAG` (CPF:137, CPF:247), `folder_name`, default `--control-root` in `main`.
T:test_constants.

### 2.5 A new condition

> "The control's rows are never pooled with Part C, with the main sweep or with the smoke.
> No control cell stands in for a Part C cell in a filed readout. (...)"

Control folders carry the control's run tag; Part C and Part A enter only C3, C4
and the reproduction checks, each in its own column (`analyse`); the smoke is
read only by `smoke_check` (CPF:710), which builds smoke names only; fixture
mode reads the fixture's own domains only (`fixture_domains`, CPF:1059; check at
CPF:394). The script writes only its own outputs. T:test_smoke ("the full-run
folders are never read"), T:test_review_refusals ("fixture mode refuses a domain
outside the fixture's own").

---

## Section 3. Measures

> "A trial is right when the frozen delivered grader says so: (...) Rates are per model, task
> and cell, over the three wordings together (n = 300)."

`frozen_grades` (CPF:1015) calls `G.grade`; `rate` (CPF:1138) per (model, task,
cell) in `analyse` (CPF:1297). T:test_base, T:test_planted_answers.

> "**The second reading: layout-tolerant.** Registered beside the frozen grade for every rate and
> every contrast. It is the reading of the filed re-grade (`tools/reanalysis/rq1_layout_regrade.py`).
> Its two reader functions are imported unchanged. The rule that combines them with the frozen
> grade is written again in the analysis script, and it must reproduce the filed re-grade on the
> rerun's rows or the analysis halts:"

The two readers, `rq1_layout_regrade.block_plan` and
`rq3_context_pilot.line_reader_exact`, are imported unchanged. The combining
rule lives inside `rq1_layout_regrade.main()` there and is re-implemented in
`second_reading` (CPF:974): the frozen plan is the default; a block plan
replaces it and decides (CPF:984); the case-folded column re-validates the
deciding plan in lower case only when it has a capital (CPF:989); on simulate
`line_reader_exact` is added only when the frozen grade is wrong (CPF:995).
`check_filed_regrade` (CPF:1106) halts unless this reproduces
`tools/reanalysis/out/rq1_layout_regrade.json` (`frozen_k`, `tolerant_k`,
`folded_k`) on every Part C and Part A (plain) cell. Every rate and contrast
carries both readings (`analyse`, CPF:1297 and CPF:1310). T:test_refusals ("the
second reading does not reproduce the filed re-grade"); the dry run reproduced
all 12 filed cells.

> solve: "When the answer has fenced code blocks and the last closed one holds a plan, that
> plan is the delivered plan (...). This is the function `block_plan`. Any other answer keeps its
> frozen grade." simulate: "A trace written one JSON object per line also counts when it equals
> the answer key exactly (...). An answer the frozen grader already counts right stays right."

CPF:984-995. T:test_planted_answers, T:test_base.

> "**Validator.** Every solve plan of the control, under both readings, is validated in process
> with pddl-pyvalidator **0.1.5**, (...) through the route of the filed re-grade (...). The analysis
> halts on any other release, on a validator answer whose verdict is not a plain true or false,
> and when the validator server file differs from the one the filed re-grade used (by sha256).
> Before it validates a new plan it checks that this route returns the stored verdict for every
> plan the frozen grade used on the rerun's solve rows that the analysis reads (Part C, and the
> plain wording of Part A for C4)."

One `Verdicts` (CPF:879) for both readings; `live_route` (CPF:900) through the
plugin server loaded in process; the verdict by `validator_verdict` (CPF:917),
which halts unless `valid` is a real bool (CPF:924) and on an error answer;
release, an edited server file and the server file's sha256 against the
`environment` block of the filed re-grade (`validator_server_sha256`) in
`check_validator_env` (CPF:929, called at CPF:1705); `check_route` (CPF:954)
before any control row is graded (CPF:1278). T:test_validator_units (well-formed
answers, `valid` 1 or "true", error answer, no field, not JSON; release 0.1.6,
edited file, different sha256, no filed record), T:test_refusals ("the route
disagrees with a stored verdict"). The live route itself is exercised by the dry
run, which reproduced the filed figures.

> "**Case folded (descriptive, not a registered reading).** (...) No reading of section 5 uses it."

CPF:989; no reading function reads it. T:test_planted_answers, T:test_base.

---

## Section 4. Contrasts and statistics

> "All contrasts are paired on the trial key (...), per model and task, in points, under both
> readings." The table of C1 to C4, six each.

`paired` (CPF:1144) on the frozen trial key; the four contrasts and both readings
in `analyse` (CPF:1310); Holm family size 6 (CPF:1331); total 48 checked.
T:test_base.

> "C3 and C4 use rows of the delivered rerun for the same 300 trial keys. Their frozen grades are
> recomputed with the frozen functions and must reproduce the filed readout, and their second
> reading must reproduce the filed re-grade, or the analysis halts."

`load_rerun_live` (CPF:1042, through `rq1_metrics.load_rerun_cells`),
`check_filed_readout` (CPF:1085), `check_filed_regrade` (CPF:1106).
T:test_refusals.

> "**Intervals.** 95% percentile intervals from the frozen domain-cluster bootstrap (...) 20 domains
> (...) 10,000 resamples, seed 20261002. The analysis asserts 20 domains in every contrast. Rates
> carry the same interval."

`boot` (CPF:1127) with `k_expected = 20`, re-checking k and the level; constants
at CPF:251-254. T:test_base, T:test_constants.

> "**Margin.** M = **5 points**" and the reading of C1 to C3: "criterion met (...), endpoints
> included; a difference is shown (...); unresolved: neither." "A contrast can meet the criterion
> and show a difference at once"

`MARGIN` (CPF:143); `contrast_label` (CPF:1156). T:test_base (the endpoint 5.0 is
inside), T:test_labels (met and shown at once, on synthetic values: 3 trials per
domain cannot produce it in the fixture).

> "**The reading of C4.** "Tools ahead" (...) "no tools ahead" (...) "no difference shown" otherwise."

`c4_label` (CPF:1170). Where R3 says the setup moved, the C4 label of both
readings also carries "across a setup that moved" (CPF:1345), so the words are
in the contrast table itself. T:test_base (Qwen3.6-35B solve C4 labels; "C4 label
in the table carries the moved-setup words"), T:test_labels.

> "**Multiplicity [Omer].** (...) an exact sign-flip p-value over the 20 domains, Holm-adjusted
> across the six contrasts of the same name and the same reading (...). A difference whose interval
> excludes 0 and whose Holm-adjusted p-value is 0.05 or more is reported as "a difference is shown
> (not after Holm)" (...). The same words are added to a C4 label (...) and are printed as a note
> beside any sentence of R1, R2 or R4 that rests on such a contrast. The count of contrasts (24,
> each under two readings) is stated with every table."

Frozen `signflip_exact_p` and `holm` (`paired`, CPF:1144; CPF:1331); the words in
`contrast_label` and `c4_label`; the notes from `holm_notes` (CPF:1226) beside
R1, R2 (`r12_reading`, CPF:1232) and R4 (`r4_reading`, CPF:1260), printed by
`render` (`with_notes`, CPF:1517); the count sentence `common` (CPF:1454) under
every table. T:test_base, T:test_labels ("R4 Holm note").

---

## Section 5. Registered readings

> "**How R1 and R2 are read.** Each contrast has its label under each reading (section 4), and the
> two labels are always printed. On top of them the readout gives a sentence for each of the cases
> below whose condition holds, in the order listed. (...) "Unresolved" is given only when no case
> holds. "A rise" means the 95% interval is above 0, "a fall" that it is below 0."

`r12_reading` (CPF:1232): both labels with intervals; a sentence for every case
(a) to (d) that holds, in order; (e) only when none holds; `rise` (CPF:1186)
lo > 0, `fall` (CPF:1190) hi < 0. Printed by `render`. A pattern no case (a) to
(d) names, such as a rise under the second reading only, gets (e) "unresolved"
with its two labels. T:test_base, T:test_labels ("a sentence for a and for b, in
order", "a rise under the second reading only").

> R1 (a) to (e) and R2 (a) to (e), as written out in the prereg.

`R_SENTENCES` (CPF:1198), verbatim; (b) and (e) carry both estimates and
intervals (`WITH_INTERVALS`, CPF:1223). T:test_base (each sentence verbatim),
T:test_labels ("R2 fall sentence").

> "**R3. Drift. (C3, frozen grade.)** (...) the levels of the control are not set beside the levels
> of Part C for that model and task. C1 and C2 do not depend on R3"

`r3_reading` (CPF:1249); `render` leaves Part C out of the rate table there
(CPF:1476, CPF:1493). T:test_base.

> "**R4.** Reported per model and task under both readings, always with the dates of the two runs
> (...). Where R3 says the setup moved, the C4 entry of that model and task carries the words
> "across a setup that moved"."

`r4_reading` (CPF:1260); the C4 labels themselves (CPF:1345). T:test_base.

> "A reading that would be wrong, named in advance." "The rerun's E2 (...) stays in the appendix."

Not code (paper text). No label says "unchanged" or "as good as".

---

## Section 6. The reporting rule

> Rules 1 to 3 and 6.

Paper text; rules 1 and 2 are stated in the rate table's header (CPF:1480).

> "4. **Both readings are registered for every rate and every contrast.**" "5. (...) If the two
> differ by more than 5 points (...) the text gives both figures (...)."

Both readings everywhere (`analyse`); `rule5` (CPF:1359). T:test_base.

---

## Section 7. Execution

> "Order. (...)" "During the run. (...)"

Not code; the script makes no SSH or SLURM call and prints no rate on the smoke.

> "Smoke. (...) 120 rows per cell folder (...), run tag `control-promptfix-smoke`, all nine cells.
> Never pooled. Checks allowed on smoke output, and nothing else:" and "The check is a mode of the
> analysis script (`--smoke-check`). It prints these items and no success rate, no failure-reason
> count and no answer text."

`smoke_check` (CPF:710), `SMOKE` (CPF:188), `SMOKE_TAG` (CPF:138). T:test_smoke.

> "1. every job completes (job states are read with the cluster-ops status script and recorded in
> section 10; they cannot be seen in the synced files), and every cell folder holds its 120 rows;"

Rows: CPF:723; job states: a printed reminder (CPF:805). T:test_smoke.

> "2. the frozen loader reads every row; no exception or infrastructure-failure row; no row cut by
> storage; no half-written line;"

CPF:730-735. T:test_smoke ("a row cut by storage", "an exception row", "a
half-written line fails item 2").

> "3. (...) at least 95% of the stored answers are non-empty (...). An answer is empty when nothing
> is left after the leaked thought-channel prefix and white space are removed;"

CPF:737. T:test_smoke.

> "4. the audit log of each cell (...): every line's system text has the sha256 this registration
> gives for that cell and task; the stored text, where a line carries it, is that text byte for
> byte; cell O is marked not swapped and cells A and B swapped; no line has tools; the model named
> is the cell's model; and, so that the log covers every trial, each task has at least as many
> lines as the cell has rows of that task and exactly as many different user texts as rows (every
> trial of a task has its own user text);"

`check_audit` (CPF:519): digest (CPF:538), stored text (CPF:542), mode
(CPF:547), swapped (CPF:550), tools (CPF:553), model (CPF:555), lines per task
(CPF:564), different user texts per task (CPF:567). The premise (every trial of
a task has its own user text) was checked on the real prompts of all three
models: 300 different texts per task, rendered with `pddl_eval.runner.build_messages`.
T:test_refusals, T:test_review_refusals ("unknown key", "wrong model", "wrong
mode", "empty file", "not JSON", "fewer different user texts than rows").

> "5. the user messages are the same in the three cells of a model: the same set of user-text
> sha256. A text that appears more often in one cell than in another is allowed (...); the number
> of such extra lines is reported per cell;"

`check_users` (CPF:573); reported by `audit_control` and printed by the smoke
check (CPF:801). T:test_base, T:test_refusals, T:test_smoke.

> "6. `client_settings.json` of each cell names that cell's system text;"

`check_settings` (CPF:600). T:test_refusals, T:test_review_refusals ("cond",
"hf_model"), T:test_smoke.

> "7. the serve log of the last job that wrote each cell (the job its `client_settings.json` names)
> shows vLLM 0.20.2 and no other version. Serve logs stay on the cluster (...); they are copied to
> the laptop for this check, or the version line is read on the cluster and the reading is
> recorded as a note that the check prints and section 10 keeps. The serve log of any earlier job
> of a resumed cell is read on the cluster and recorded in section 9."

`check_serve_log` (CPF:621): the log of the job `client_settings.json` names; at
least one banner (CPF:635), all 0.20.2 (CPF:637); the note is printed
(CPF:790); the printed item names the last job and says earlier jobs are read on
the cluster. T:test_refusals, T:test_review_refusals ("a serve log with no
version banner"), T:test_smoke ("item 7 names the last job's serve log").

> "**The same audit checks (items 4 to 7) are preconditions of the analysis** on the full run.
> If one fails, the analysis halts before any answer is graded."

`audit_control` (CPF:682), called in `main` before the rerun is loaded (CPF:1678,
CPF:1698); item 7 with neither logs nor note halts (CPF:688). T:test_refusals.

> "**Apparatus checks, also preconditions of the analysis** (...): `client_settings.json` gives the
> 16,384-token window and thinking off; the run's summary gives the 16,384-token window,
> temperature 0, thinking off, the no-tools condition and the cell's model; no answer is longer
> than its task's output cap; and every answer that stopped at the cap, without a turn whose
> allowance was lowered to fit the window (an answer left empty because the prompt filled the
> window counts as such a turn), used exactly 8,192 tokens on solve or 6,144 on simulate (...)."

`check_apparatus` (CPF:643): settings (CPF:650), summaries (CPF:656), caps
(CPF:673, CPF:675; a no-room row is skipped, as the clause says).
T:test_refusals and T:test_review_refusals (window in settings and summary;
summary temperature, think, conditions, models; an answer over its cap; an
answer stopped at the cap with fewer tokens).

> "**Stop rules.** (...) When a cell is VOID, by this rule or by the pairing rule below, **all three
> cells of that model are run again from scratch, together**, under the run tag
> `control-promptfix-r2` (...). The analysis reads the second run of a model only after it has
> found a cell of that model's first run VOID. Any other stop is a deviation."

`check_void` (CPF:410); `resolve_tags` (CPF:459) and `first_run_void` (CPF:432):
a model named in `--r2-models` has its first-run cells loaded and checked, and
its second run is read only when a first-run cell is VOID by the exception rule
or the pairing rule; a missing, short or otherwise refused first run, or one
that is not VOID, halts (called at CPF:1675 and CPF:1695). T:test_refusals
("exception rows above 1% -> VOID"), T:test_r2 (accepted after a VOID first run
by either rule; refused when the first run is not VOID, when it is missing, and
for an unknown model).

> "**Completeness.** (...) A model whose cells share fewer than 99% of their keys is VOID; this is
> checked first. Then each task's 300 keys must equal the keys of Part C for that model and task;
> a difference halts the analysis. So in an analysed run the unpaired count is zero, and it is printed."

`check_pairing` (CPF:469) right after loading; `check_keys_equal_part_c`
(CPF:484, called at CPF:1276); the unpaired count is a column of the contrast
tables. T:test_refusals, T:test_base.

> "**Exception rows at or under 1%** stay in the denominator and are graded as they are (...).
> Their count is reported per cell." "**Rows cut by storage.** (...)" "**Duplicate trial keys**
> (...) halt the analysis. **Half-written lines** (...) are counted, reported and skipped (...)."

Exception rows: kept by `check_void`, graded by the frozen grader, counted.
Storage cuts: CPF:389. Duplicates: CPF:398. Half-written lines: CPF:382, then
completeness (CPF:403). T:test_base, T:test_refusals, T:test_review_refusals ("a
half-written line is counted and skipped").

> "**The analysis does not read a row of the full run** unless it is started with the package hash
> recorded in section 9 (`--i-have-frozen`)."

`package_sha256` (CPF:308); the gate at CPF:1686, before any read. T:test_live_gate,
T:test_package_hash.

---

## Section 8. Secondary, descriptive

> "the count of right answers by wording (v11, v12, v13; 100 trials each), under both readings;"

`by_wording` (CPF:1427); the table header says "count right". T:test_base
("wording table gives counts").

> "the layout of the answer: (...) on simulate, whether the answer is one JSON object (the whole
> answer, after the leaked prefix and one enclosing code fence are removed, parses as an object),
> one object per line (at least two lines that each parse as an object), or neither;"

`layout` (CPF:1431) from `block_plan` and `simulate_layout` (CPF:861). T:test_base.

> "answers that stopped at the output cap; mean answer tokens;" "the frozen grade's reason for each
> failure, and how each trial moved from O to A and from O to B;" "the case-folded column of section
> 3;" "the Holm-adjusted p-values of section 4."

`secondary_tables` (CPF:1420): CPF:1432, CPF:1436, CPF:1438, CPF:1442; `p_holm`
on every contrast. T:test_base.

> "**Tripwires that halt the readout until audited** (...): a count of right answers that is the same
> in all nine cells of a task, under either reading; a cell of O whose frozen rate is more than 20
> points from the Part C rate of the same model and task; a cell in which the frozen grader can read
> no answer at all on one of the two tasks; and a cell and task in which more than 5% of the answers
> (more than 15 of 300) are unread final answers, as defined next."

In `analyse`: T1 (CPF:1369), T2 (CPF:1376), T3 per cell and task (CPF:1381), T4
per cell and task with `UNREAD_FRAC` (CPF:162, checked CPF:269 and as 15 of 300
at CPF:282) (CPF:1385); a fired tripwire halts unless released with a note
(CPF:1388, the frozen `run.load_audit_notes` at CPF:1659). T:test_tripwires (T1;
T2 with and without a note; T3 on one task; T4 at 4 of 60), T:test_base (3 of 60,
exactly 5%, does not fire).

> "**Unread final answers (descriptive, and the fourth tripwire).** An answer that is wrong under
> both readings and ends with what looks like its final answer outside a code block: on solve, the
> last non-empty line is one action line and the answer has no plan block; on simulate, the layout is
> "neither" and the answer ends with a closing brace or bracket. (...) The count is reported per
> model, task and cell."

`unread_final` (CPF:835): wrong under both readings; solve: the last non-empty
line after the leaked-prefix strip matches the re-grade's tolerant action
pattern (`e2e_regrade._TOLERANT_ACTION_RE`) and `block_plan` is None (CPF:846);
simulate: layout "neither" and the answer, prefix and trailing white space
removed, ends with `}` or `]` (CPF:848). Counted per model, task and cell
(CPF:1439) and, descriptively, for the rerun's rows (CPF:1397).
T:test_unread_units, T:test_base ("unread final answers per cell", "... of the
rerun rows").

---

## NOT IMPLEMENTED

1. **2.3 "The user prompts v11 to v13, byte for byte", against Part C.** Part C
   has no audit log and its rows do not store the user text. What is checked:
   the trial keys equal Part C's, the user texts are the same set in O, A and B,
   and each task has one different user text per row.
2. **2.3 "The request still carries the `guided_json` field" and "No decoder
   constraint in any cell".** No file of a cell records the request body; the
   behaviour is fixed by the harness commit of section 9.
3. **2.3 "Four requests at a time", "GPU class `rtx_6000`, one model alone on its
   card, `--mem=48G`".** Not in the synced files (they are in the job's `.out`
   and in SLURM accounting on the cluster).
