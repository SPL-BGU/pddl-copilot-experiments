# Pre-registration: corrected-prompt control for the no-tools arm on solve and simulate

**Written 2026-11-23, before any trial of this run exists.** Decision to run: Omer,
2026-11-23, as the one exception to the "No new runs" line of `roadmap.md`. The plan
behind it is `development/control_prompt_fix_plan.md`; his answers are in its section 9.
Where the plan and this document differ, this document holds.

**Disclosure of prior data contact.** No row of this run exists at registration time.
The author of this registration has read, in full or in part, the data the control is
compared with: the unaided answers of the delivered rerun (Part C), the layout-tolerant
re-grade of both arms (`NUMBERS.md`, "RQ1 solve and simulate, layout-tolerant re-grade
of both arms"), and the JSON constraint pilot. The readings of section 5 were written
with those figures known. They were written before any answer under a corrected prompt
existed.

**Status of this document.** Sections 1 to 8 are the registration. Section 9 is the
freeze record and section 10 the smoke record; both are filled in as the steps happen.
Section 11 lists deviations. Two points of sections 4 and 6 are marked **[Omer]**: they
are choices the plan left open, written here as the session recommends, and his to
change before the freeze. After the freeze nothing in sections 1 to 8 changes without an
entry in section 11.

---

## 1. Purpose

On solve and simulate the no-tools system message tells the model to "conform to the
JSON schema provided by the format constraint". The model never received a schema: the
request field that carried it (`guided_json`) is dropped by vLLM 0.20.2. The unaided
baseline of RQ1 on these two tasks was therefore measured under an instruction the
model could not follow.

The control measures two things, for three models and two tasks:

1. how the unaided delivered rate moves when the reference to the schema is removed
   (cell A), and when the answer format is stated in plain words (cell B), with
   everything else held as in Part C;
2. the unaided delivered rate under the corrected instruction (cell B), which the paper
   reports as its no-tools baseline on solve and simulate (section 6).

**Not covered.** The main sweep (Study 1). Thinking on. Any model beyond the three. The
Claude runs, which asked for the format in another way and did not carry this flaw. The
three validation tasks, whose prompts never mentioned a schema. What a decoder
constraint that takes effect would give (the pilot covers that for one model).

---

## 2. Design

### 2.1 Cells

Three cells per model. Only the system message differs between them.

| cell | system message | wrapper value | cell token in the folder name |
|---|---|---|---|
| **O** | the registered text of Part C, unchanged | `registered` | `no-tools` |
| **A** | the reference to the schema removed | `no-pointer` | `no-tools-syspointer-off` |
| **B** | the answer format stated, with the final answer in a fenced code block | `format-stated` | `no-tools-sysformat` |

The six texts are in `pddl_eval/prompts.py` (O, `WITHOUT_TOOLS_SYSTEM_BY_TASK`) and
`pddl_eval/control_prompts.py` (A and B), and are printed in section 2 of the plan. They
are fixed by their sha256 (utf-8).

**Cell B, as run.** The end of its third sentence reads:

- solve: "…; end your response with the plan alone in a fenced code block, one
  parenthesised PDDL action per line."
- simulate: "…; end your response with a fenced code block that holds a single JSON
  object of the form {"trajectory": [ ...steps... ]}, where each step has the keys
  step, action and state (state.boolean and state.numeric)."

The words "in a fenced code block" were added on 2026-11-23 (Omer; PR #148), before
any trial, after the independent review of the analysis showed that an unfenced final
answer after prose is read by neither reader of section 3. A final code block is read:
by the frozen grader on simulate, and by the second reading on solve. The plan's
section 2 has the earlier wording and a note.

| cell | solve | simulate |
|---|---|---|
| O | `dd835ea2f66c73f8f26cb80b11afae9030aac316f102fb54a433498b6e23de83` | `dfd6beadb3e815e769fd31bd88f99ed78c0cfb6c9b74001fe442cc0b2bbc5ccd` |
| A | `1cf4b9b6a7652fa90dc36cd41b98e3a312bebe6be3a427e3f16a62c4a7b2dfa8` | `c99db1124156372ea0e0a88b41779c4b9aa62167821a99272fa886f8b1774553` |
| B | `3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588` | `7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9` |

### 2.2 Models, tasks and size

- Models: `Qwen/Qwen3.5-9B`, `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`,
  `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` (the three headline models, the weights and
  quantisations of Part C). Folder tags `Qwen3_5_9B`, `gemma4_26b-a4b`, `qwen3_6_35b`.
- Thinking off.
- Tasks: solve and simulate.
- Per model, task and cell: the 100 problems of Part C (20 domains, 5 problems each) by
  the three plain wordings (v11, v12, v13) = **300 trials**.
- Per cell folder (one model, one system text, two tasks): 600 rows, 200 per wording.
- Total: 3 models by 3 cells by 600 = **5,400 trials**.

### 2.3 What is identical to Part C

Everything but the system message, and the date.

- The user prompts v11 to v13, byte for byte.
- The request still carries the `guided_json` field in all three cells. The server
  still drops it. Taking it out would be a second change.
- No decoder constraint in any cell.
- The 16,384-token window. Output cap 8,192 tokens on solve and 6,144 on simulate.
  Temperature 0. Four requests at a time. Answers stored up to 65,536 characters.
- vLLM 0.20.2 from the shared `~/vllm.sif`. GPU class `rtx_6000`, one model alone on its
  card, `--mem=48G`.
- The harness: `main` at the merge commit of PR #148 (the control cells of PR #147 with
  the final wording of cell B), recorded in section 9. Both PRs are additive; no file
  of the frozen package hash `822aace9…` differs from the harness of Part C.

**How each of these is assured.** The analysis checks what the synced files hold
(section 7: the system text sent, the window, the caps, temperature, thinking, the
model, the storage rule). Three points leave no trace in a cell's files and are assured
otherwise, each recorded in sections 9 and 10:

- *The user prompts equal Part C's byte for byte.* Part C stored no user text to compare
  with. The prompt templates and the code that fills them are files of the frozen hash
  `822aace9…`, which the harness commit must reproduce (recorded in section 9); the
  analysis checks that the trial keys equal Part C's and that the user texts are the
  same in O, A and B.
- *The request still carries `guided_json`, and no decoder constraint.* Fixed by the
  harness tests of PR #147 (the request of every cell is compared with a literal) and
  by the submit command, which does not pass `--json-constraint`; the command is
  recorded in section 9.
- *Four requests at a time, GPU class `rtx_6000`, one model alone on its card,
  `--mem=48G`.* Read from the submit output and the job's log on the cluster and
  recorded in section 10 (smoke) and section 9 (full run).

### 2.4 One window

All nine cells are submitted in one array job, so that O, A and B of a model run in the
same days, on the same GPU class and the same container image. A cell that stops at its
time limit is resumed in place (same folder). The job id of the submission and of
every resume, and the dates of the run, are recorded in section 9 from the submit
output and the cluster-ops status script, and the readout prints the dates (only the
last job id of a cell is kept in its folder).

Run tag of the full run: `control-promptfix`. Folders:
`slurm_vllm_<model tag>_off_<cell token>_control-promptfix`, synced to
`results/control-promptfix/`.

### 2.5 A new condition

The control's rows are never pooled with Part C, with the main sweep or with the smoke.
No control cell stands in for a Part C cell in a filed readout. Part C stays the
registered unaided input of the rerun's E2 contrast.

---

## 3. Measures

**The registered measure: delivered right, frozen grade.** A trial is right when the
frozen delivered grader says so: `tools.delivered_rerun.grade.grade`, imported
unchanged from the package with hash `822aace9…`. On solve the plan it reads must pass
the validator; on simulate the trace it reads must equal the answer key. Rates are per
model, task and cell, over the three wordings together (n = 300).

**The second reading: layout-tolerant.** Registered beside the frozen grade for every
rate and every contrast. It is the reading of the filed re-grade
(`tools/reanalysis/rq1_layout_regrade.py`). Its two reader functions are imported
unchanged. The rule that combines them with the frozen grade is written again in the
analysis script, and it must reproduce the filed re-grade on the rerun's rows or the
analysis halts:

- **solve.** When the answer has fenced code blocks and the last closed one holds a
  plan, that plan is the delivered plan and replaces the frozen reading, whichever way
  that moves the grade. A block holds a plan when (a) it parses as JSON and is a
  non-empty list of strings, or an object whose `plan` is such a list, every string
  being one parenthesised action, or (b) every non-empty line of it is one action line.
  This is the function `block_plan`. Any other answer keeps its frozen grade.
- **simulate.** A trace written one JSON object per line also counts when it equals the
  answer key exactly (`rq3_context_pilot.line_reader_exact`). An answer the frozen
  grader already counts right stays right.

Both readers are lenient about layout only. The frozen grade answers "did the baseline,
as the paper measures it, move". The second reading answers "did what the models wrote
move". Neither replaces the other.

**Why both.** The frozen solve reader collects every action-shaped line of an answer,
wherever it stands, and reads JSON only when the whole answer is the JSON object. An
answer that reasons first and then gives its plan in a code block is therefore graded
by the frozen grade on the reasoning lines and the plan together, or on no plan at all.
That is the layout of most solve answers under cell O, and it is the layout cell B
asks for. So on solve the frozen grade can stay low in every cell for a reason that is
the grader's, and the second reading, which reads the last code block alone, is the
reading that follows the answer the model gave. On simulate both readers read a final
code block. This is known before the data and is why both readings are registered for
every rate and every contrast.

**Validator.** Every solve plan of the control, under both readings, is validated in
process with pddl-pyvalidator **0.1.5**, the release of the rerun's readout, through
the route of the filed re-grade (the plugin's validator server, loaded in process). The
analysis halts on any other release, on a validator answer whose verdict is not a
plain true or false, and when the validator server file differs from the one the filed
re-grade used (by sha256). Before it validates a new plan it checks that this
route returns the stored verdict for every plan the frozen grade used on the rerun's
solve rows that the analysis reads (Part C, and the plain wording of Part A for C4).

**Case folded (descriptive, not a registered reading).** Release 0.1.5 rejects a plan
that writes a declared name with a capital letter (ISS-027). Beside the second reading
the analysis reports the same reading with every deciding plan sent in lower case. It
is given so the reader can see how much rides on capitals. No reading of section 5 uses
it.

---

## 4. Contrasts and statistics

All contrasts are paired on the trial key (task, domain, problem, plan label, wording),
per model and task, in points, under both readings.

| name | contrast | role | number |
|---|---|---|---|
| **C1** | A minus O | primary: did the wrong reference move the baseline? | 6 |
| **C2** | B minus O | secondary: what does a correct instruction give, against the old one? | 6 |
| **C3** | O minus Part C | drift check: does today's setup reproduce Part C? | 6 |
| **C4** | tools, plain wording (Part A of the rerun) minus B | the RQ1 comparison under the reported baseline (section 6) | 6 |

C3 and C4 use rows of the delivered rerun for the same 300 trial keys. Their frozen
grades are recomputed with the frozen functions and must reproduce the filed readout,
and their second reading must reproduce the filed re-grade, or the analysis halts.

**Intervals.** 95% percentile intervals from the frozen domain-cluster bootstrap of the
rerun (`tools.delivered_rerun.stats.cluster_bootstrap`): the 20 domains are the
clusters, 10,000 resamples, seed 20261002. The analysis asserts 20 domains in every
contrast. Rates carry the same interval.

**Margin.** M = **5 points** (Omer, 2026-11-23; the margin of the rerun's parity check).
It is a threshold chosen in advance, not a claim about what size of shift matters.

**The reading of one contrast (C1, C2, C3).**

- **criterion met**: the whole 95% interval lies inside [−5, +5], endpoints included;
- **a difference is shown**: the 95% interval excludes 0;
- **unresolved**: neither.

A contrast can meet the criterion and show a difference at once (a small shift that is
estimated well). With 20 domains an interval can be wider than the margin allows, and
then the reading is "unresolved", never "unchanged".

**The reading of C4.** "Tools ahead" when the interval is above 0, "no tools ahead"
when it is below 0, "no difference shown" otherwise. The margin is not applied to C4.

**Multiplicity [Omer].** The readings above use the unadjusted 95% interval, as the
registered readings R1 to R3 of the rerun did. Beside every contrast the analysis also
reports an exact sign-flip p-value over the 20 domains, Holm-adjusted across the six
contrasts of the same name and the same reading (the rerun's method for E2 and E3). A
difference whose interval excludes 0 and whose Holm-adjusted p-value is 0.05 or more is
reported as "a difference is shown (not after Holm)", with those words. The same words
are added to a C4 label ("tools ahead (not after Holm)") and are printed as a note
beside any sentence of R1, R2 or R4 that rests on such a contrast. The count of
contrasts (24, each under two readings) is stated with every table.

---

## 5. Registered readings

Written before any data, so that the result cannot choose its own reading. Each is
stated per model and task; no reading pools models or tasks.

**How R1 and R2 are read.** Each contrast has its label under each reading (section
4), and the two labels are always printed. On top of them the readout gives a sentence
for each of the cases below whose condition holds, in the order listed. More than one
can hold (a small rise that is estimated well meets the criterion and shows a rise).
"Unresolved" is given only when no case holds. "A rise" means the 95% interval is above
0, "a fall" that it is below 0. A pattern the cases do not name (for example a rise
under the second reading only) is given as "unresolved", and its two labels say what
each reading shows.

**R1. Did the wrong reference hold the baseline down? (C1.)**

- (a) C1 meets the criterion under both readings: "removing the reference to the
  schema did not move the unaided baseline by more than 5 points".
- (b) C1 shows a rise under the frozen grade and under the second reading: "the wrong
  reference lowered the unaided baseline", with both estimates and intervals.
- (c) C1 shows a rise under the frozen grade and no rise under the second reading: "the
  wrong reference changed how the answers were laid out, and the grader did not read
  that layout; what the models wrote did not change by more than the second reading
  shows" (the layout-only reading).
- (d) C1 shows a fall under the frozen grade: "a fall, reported as it is: the
  reference, wrong as it was, did not cost the model anything on that task".
- (e) none of these: "unresolved", with both intervals.

**R2. What does a correct instruction give? (C2.)** R2 does not decide what the paper
reports as the baseline; section 6 does.

- (a) C2 meets the criterion under both readings: "stating the answer format did not
  move the unaided baseline by more than 5 points".
- (b) C2 shows a rise under both readings: "stating the answer format raises the
  unaided baseline, and not through layout alone", with both estimates and intervals.
- (c) C2 shows a rise under the frozen grade and no rise under the second reading:
  "stating the answer format raises the frozen grade through layout: the answers come
  in a layout the grader reads; what the models wrote did not change by more than the
  second reading shows".
- (d) C2 shows a fall under the frozen grade: "a fall, reported as it is: stating the
  answer format lowered the unaided baseline on that task".
- (e) none of these: "unresolved", with both intervals.

**R3. Drift. (C3, frozen grade.)** If C3 meets the criterion for a model and task, the
setup is taken to reproduce Part C there. If not, the readout says "the setup moved
between Part C and the control for this model and task", gives the estimate, and the
levels of the control are not set beside the levels of Part C for that model and task.
C1 and C2 do not depend on R3: they are within-window contrasts.

**R4. Tools against the reported baseline. (C4.)** Reported per model and task under
both readings, always with the dates of the two runs (Part A: 2026-10-03 to
2026-10-09; the control: the dates of section 9). Where R3 says the setup moved, the C4
entry of that model and task carries the words "across a setup that moved". The rerun's
E2 (tools minus Part C, same run) stays in the appendix as the registered contrast.

**A reading that would be wrong, named in advance.** "The corrected prompt shows the
unaided models are as good as the tool arm" from a C4 interval that includes 0: that is
"no difference shown". "The baseline is unchanged" from an unresolved C1. A pooled
figure over the three models.

---

## 6. The reporting rule (Omer, 2026-11-23)

Fixed here, before any data is read:

1. **Cell B is the no-tools baseline the paper reports on solve and simulate**, for the
   three open models, whatever the contrasts show.
2. **Cell O is the anchor**: for the paired contrasts C1 and C2, and for the drift
   check C3 against Part C. Its level is reported in the appendix table, not as a
   baseline.
3. **Part C stays in the appendix as the registered record**, with a short note on why
   the arm was run again.
4. **Both readings are registered for every rate and every contrast.**
5. **Which figure of cell B the text quotes [Omer].** The frozen grade, since it is the
   paper's measure everywhere else. The second reading stands beside it in the table.
   If the two differ by more than 5 points for a model and task, the text gives both
   figures wherever it gives one for that model and task. This rule is fixed now so
   that the figure is not chosen after the data are seen.
6. **No paper edit is part of this registration.** The readout is reported to Omer; the
   paper change is a separate step after he has read it.

---

## 7. Execution

- **Order.** Harness change merged (PRs #147 and #148) → this registration and the freeze
  (section 9) → smoke → full run → sync → frozen analysis → readout and a `NUMBERS.md`
  entry. Every SSH or SLURM action needs Omer's explicit go-ahead; the smoke and the
  full run are asked for separately.
- **Smoke.** The full-run SLURM profile (same GPU class, memory and `--time`), the real
  configuration with `--partial 1` (the first problem of every domain: 120 rows per
  cell folder), run tag `control-promptfix-smoke`, all nine cells. Never pooled.
  **Checks allowed on smoke output, and nothing else:**
  1. every job completes (job states are read with the cluster-ops status script and
     recorded in section 10; they cannot be seen in the synced files), and every cell
     folder holds its 120 rows;
  2. the frozen loader reads every row; no exception or infrastructure-failure row; no
     row cut by storage; no half-written line;
  3. in every cell, at least 95% of the stored answers are non-empty (the Part C cells
     of these models and tasks hold no empty answer). An answer is empty when nothing
     is left after the leaked thought-channel prefix and white space are removed;
  4. the audit log of each cell (`system_prompt_audit.jsonl`): every line's system text
     has the sha256 this registration gives for that cell and task; the stored text,
     where a line carries it, is that text byte for byte; cell O is marked not swapped
     and cells A and B swapped; no line has tools; the model named is the cell's model;
     and, so that the log covers every trial, each task has at least as many lines as
     the cell has rows of that task and exactly as many different user texts as rows
     (every trial of a task has its own user text);
  5. the user messages are the same in the three cells of a model: the same set of
     user-text sha256. A text that appears more often in one cell than in another is
     allowed (a job that is stopped and resumed sends its unfinished requests again);
     the number of such extra lines is reported per cell;
  6. `client_settings.json` of each cell names that cell's system text;
  7. the serve log of the last job that wrote each cell (the job its
     `client_settings.json` names) shows vLLM 0.20.2 and no other version. Serve logs
     stay on the cluster (`cluster-experimenting/logs/`); they are copied to the laptop
     for this check, or the version line is read on the cluster and the reading is
     recorded as a note that the check prints and section 10 keeps. The serve log of
     any earlier job of a resumed cell is read on the cluster and recorded in section
     9.
  The check is a mode of the analysis script (`--smoke-check`). It prints these items
  and no success rate, no failure-reason count and no answer text.
- **The same audit checks (items 4 to 7) are preconditions of the analysis** on the
  full run. If one fails, the analysis halts before any answer is graded.
- **Apparatus checks, also preconditions of the analysis** (they follow section 2.3):
  `client_settings.json` gives the 16,384-token window and thinking off; the run's
  summary gives the 16,384-token window, temperature 0, thinking off, the no-tools
  condition and the cell's model; no answer is longer than its task's output cap; and
  every answer that stopped at the cap, without a turn whose allowance was lowered to
  fit the window (an answer left empty because the prompt filled the window counts as
  such a turn), used exactly 8,192 tokens on solve or 6,144 on simulate (true of every
  such row of Part C).
- **During the run.** Monitoring reads row counts and job states only. No success rate
  or failure-reason count of any cell is computed before the freeze.
- **Stop rules.** A cell folder is VOID if more than 1% of its rows (more than 6 of
  600) are exception or infrastructure-failure rows. Exception rows are those of the
  rerun's rule: `failure_reason` "exception" or "ollama_parse_error", or the
  empty-message exception shape. When a cell is VOID, by this rule or by the pairing
  rule below, **all three cells of that model are run again from scratch, together**,
  under the run tag `control-promptfix-r2`, so that O, A and B still share a window.
  This is declared here and is not a deviation. The analysis reads the second run of a
  model only after it has found a cell of that model's first run VOID. Any other stop
  is a deviation.
- **Completeness.** 600 rows per cell folder, 200 per wording, 300 per task. A short
  cell is resumed, not analysed. The three cells of a model must hold the same 600
  trial keys. A model whose cells share fewer than 99% of their keys is VOID; this is
  checked first. Then each task's 300 keys must equal the keys of Part C for that model
  and task; a difference halts the analysis. So in an analysed run the unpaired count
  is zero, and it is printed.
- **Exception rows at or under 1%** stay in the denominator and are graded as they are
  (an empty answer is wrong). Their count is reported per cell.
- **Rows cut by storage.** Registered expectation: none (Part C has none). A cut row is
  accepted only if the answer also stopped at the output cap; it is then graded on its
  stored 65,536 characters and counted in the output. Any other cut row halts the
  analysis.
- **Duplicate trial keys** in a cell folder halt the analysis. **Half-written lines**
  (a record cut when a job is stopped) are counted, reported and skipped, as the frozen
  loader of the rerun does; the completeness rule still has to hold without them.
- **The analysis does not read a row of the full run** unless it is started with the
  package hash recorded in section 9 (`--i-have-frozen`).

---

## 8. Secondary, descriptive (not gates, not readings)

Reported per model, task and cell, with counts:

- the count of right answers by wording (v11, v12, v13; 100 trials each), under both
  readings;
- the layout of the answer: on solve, whether the last code block holds a JSON plan,
  action lines, or there is no plan block; on simulate, whether the answer is one JSON
  object (the whole answer, after the leaked prefix and one enclosing code fence are
  removed, parses as an object), one object per line (at least two lines that each
  parse as an object), or neither;
- answers that stopped at the output cap; mean answer tokens;
- the frozen grade's reason for each failure, and how each trial moved from O to A and
  from O to B;
- the case-folded column of section 3;
- the Holm-adjusted p-values of section 4.

**Tripwires that halt the readout until audited** (the audit is recorded in the
readout): a count of right answers that is the same in all nine cells of a task, under
either reading; a cell of O whose frozen rate is more than 20 points from the Part C
rate of the same model and task; a cell in which the frozen grader can read no answer
at all on one of the two tasks; and, **for cell B only**, a model and task in which
more than 5% of the answers (more than 15 of 300) are unread final answers, as defined
next. Cell B is the baseline the paper reports, so it is the cell this tripwire guards.
Under the registered text the count is already known to pass 5% for Qwen3.6-35B (16 of
300 on solve and 22 on simulate in Part C), so for cells O and A it is reported and
does not halt.

**Unread final answers (descriptive, and the fourth tripwire).** An answer that is wrong
under both readings and ends with what looks like its final answer in a place neither
reader reads. The answer did not stop at the output cap (a cut answer has no final
answer). On solve: the answer has no plan block; its last non-empty line, a closing
code fence aside, is one action line; and the plan the frozen reader took is not just
the run of action lines the answer ends with (when it is, the frozen reader did read
the final answer, and the plan was simply wrong). On simulate: the layout is "neither"
and the answer, a closing code fence aside, ends with a closing brace or bracket. Neither reader reads such an answer as the model's final answer. The count is
reported per model, task and cell. It is given so that a baseline held down by layout
is seen and not read as a baseline held down by content.

---

## 9. Freeze record (to be completed before the full run's data is read)

| item | value |
|---|---|
| harness commit on the cluster | *to be filled in: `main` at the merge commit of PR #148* |
| tools repo `pddl-copilot` on the laptop (validator route) | *to be filled in at the freeze* |
| analysis branch and commit | *to be filled in* |
| package hash (`--i-have-frozen`) | *to be filled in* |
| gates | *to be filled in: 1 typed loader, 2 constants as asserts, 3 traceability map, 4 synthetic fixture, 5 independent review* |
| serving version | *to be filled in from the smoke* |
| submit command (smoke and full run) | *to be filled in, verbatim* |
| job ids and dates | *to be filled in* |
| GPU class, memory, requests at a time (from the job log) | *to be filled in* |

**sha256 of the frozen files:** *to be filled in at the freeze.*

---

## 10. Smoke record

*To be filled in.*

---

## 11. Deviations

*None at registration time.*
