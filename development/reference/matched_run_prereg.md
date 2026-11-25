# Pre-registration: the matched run (tools against no tools on solve and simulate, one job)

**DRAFT, written 2026-11-25, before any trial of this run exists. Not frozen.** Decision
to run: Omer, 2026-11-25 (`development/datasets_breakdown.md`, option 1;
`paper_notes_discussions.md`, 2026-11-25). It reuses the registration of the
corrected-prompt control (`control_prompt_fix_prereg.md`) and its analysis wherever it
can, and says where it differs.

**Choices that are Omer's and still open** are marked **[Omer, A5]** to **[Omer, A10]**
after the questions of `development/unified_run_design.md`, and **[Omer, ISS-029]** (the
simulate answer key, section 3). Each is written here as the
session recommended. They stand unless he changes them before the freeze. Nothing is
frozen and nothing is submitted until he has answered them.

**Disclosure of prior data contact.** No row of this run exists. The author has read
the data of the two runs this one replaces as the source of RQ1 on solve and simulate:
the tool arms of the delivered rerun (Part A, 2026-10-03 to 2026-10-09) and the
corrected-prompt control (2026-11-23 to 2026-11-24), including the rates of the control's
readout. The readings of section 5 were written with those figures known. They were
written before any answer of this run existed. On that old data the registered grade of
section 3 moves the simulate rates of the tool arms a long way from the rerun's frozen
grade: for Gemma-26B with plain wordings, 60 of 300 right under the registered grade
against 25 of 300 under the frozen grade. This was known when the grade was fixed.

**Status of this document.** Sections 1 to 8 are the registration. Section 9 is the
freeze record and section 10 the smoke record, filled in as the steps happen. Section 11
lists deviations.

---

## 1. Purpose

RQ1 asks whether the tools help. On solve and simulate the paper today compares a tool
arm collected in October with a no-tools arm collected seven weeks later. This run
collects the three arms together, so that the comparison is inside one run:

- **N**: no tools, with the system message that states the answer format;
- **P**: tools offered, plain wordings;
- **S**: tools offered, steered wordings (one added sentence that names the tool).

It also fixes the reader of the answers before the run, so that the paper quotes one
grade for these two tasks and no grade is chosen after the data are seen.

**Not covered.** The three validation tasks (their comparison is already inside one run,
the rerun). Thinking on. Any model beyond the three. The Claude models. RQ2 and RQ3,
which the paper answers from the rerun's tool arms on all five tasks (section 6, rule 3).

---

## 2. Design

### 2.1 Arms and cells

| arm | tools | system message | user wordings | cell folder token |
|---|---|---|---|---|
| **N** | none | the format-stated text of the control (its cell B), word for word | v11, v12, v13 | `no-tools-sysformat` |
| **P** | offered | the with-tools text of Part A, unchanged | v11, v12, v13 | `tools_all_minimal` |
| **S** | offered | the same | v14, v15, v16 | `tools_all_minimal` |

P and S share one cell folder, as in Part A: the with-tools cell runs the six wordings.
So each model has two cell folders, and the run has six.

**[Omer, A5]** The no-tools message is the control's cell B. Its sha256 (utf-8) is
`3dbc1baf…` on solve and `7ccf5d9d…` on simulate (the full digests are in section 2.1
of the control's registration). The registered and reference-removed texts are not run
again.

The with-tools system text of arms P and S is fixed by its sha256 (utf-8) as well:

- solve: `9b179ca12c2cd2220b46c5478bc637f6dd47356a2f81a4795d3541ecdf6dbb2c`
- simulate: `ebf8e7fe9d55ab56b9d2d4ba02be4f2b7770fe1b9fdd4d77bba790a68a0d0ac6`

Both are derived from `pddl_eval/prompts.py` (the text Part A sent). They are the same
for plain and steered wordings: the steering sentence is in the user message.

Known in advance from the control: under this message Gemma-26B writes its simulate
answer as one JSON object and breaks the brackets in about one answer in six (52 of 300).
This is behaviour of the model under the stated format and is reported as it comes. No
answer is repaired.

### 2.2 Models, tasks and size

- Models: `Qwen/Qwen3.5-9B`, `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`,
  `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`: the weights and quantisations of the rerun and
  the control. Folder tags `Qwen3_5_9B`, `gemma4_26b-a4b`, `qwen3_6_35b`.
- Thinking off.
- Tasks: solve and simulate.
- Per model, task and arm: the 100 problems of the rerun (20 domains, 5 problems each)
  by three wordings = **300 trials**.
- Per cell folder: N 600 rows (300 per task); tools 1,200 rows (600 per task, 100 per
  wording and task).
- Total: 3 models by 2 tasks by 3 arms by 300 = **5,400 trials**.

### 2.3 Fixed settings **[Omer, A6, A7, A10]**

- **The tools are the suite of Part A, unchanged [A6].** The cluster's `pddl-copilot`
  checkout stays at `5e4f9c0`. In particular the simulate tool keeps its output as it
  is: every predicate, in a notation that differs from the one the answer must use.
  The paper reports what the models do with that tool.
- **Context window 16,384 tokens [A7].** Output cap 8,192 tokens on solve and 6,144 on
  simulate. Temperature 0. Four requests at a time. Answers stored up to 65,536
  characters.
- vLLM 0.20.2 from the shared `~/vllm.sif`. GPU class `rtx_6000`, one model alone on its
  card, `--mem=48G`.
- The with-tools system text, byte for byte as in Part A (section 2.1). The user
  prompts v11 to v16 are assured in four ways. The prompt templates and the code that
  fills them are files of the package hash. The trial keys equal Part A's. The texts of
  v11 to v13 are the same in the N cell and the tools cell of a model (section 7, item
  5). And the user texts of the N cell are compared by sha256 with those of the
  control's cell B, which has an audit log. The count of texts that differ is reported
  beside K1 and does not halt. A difference would mean that a prompt moved between the
  two runs; on simulate that is the plan placed in the prompt (section 3). Part A has
  no audit log, so its user texts cannot be compared directly.
- The no-tools request still carries the `guided_json` field, which the server
  drops, as in the control. No decoder constraint in any arm.
- The harness: `main` at the commit recorded in section 9. The only change since the
  control is in the submit script (the with-tools cell may join the same array job as
  the format-stated no-tools cell). No file under the frozen hashes `822aace9…` or
  `825dab63…` changes.

How each setting is assured follows the control (its section 2.3): the analysis checks
what the synced files hold; what leaves no trace in a cell's files is read from the
submit output and the job logs and recorded in sections 9 and 10.

These settings leave no trace in a cell's files. Each is recorded by hand in sections 9
and 10, from the submit output and the job logs:

- the commit of the cluster's tools repo. It is read on the cluster before the smoke and
  before the full run, and recorded in section 10 and in section 9. The analysis refuses
  to run without a note that says how it was read;
- four requests at a time;
- the GPU class and the memory;
- the `guided_json` field of the no-tools request, and that no arm has a decoder
  constraint;
- the harness commit;
- that the six cells are one array job;
- that every job completed.

### 2.4 One job, one window

All six cells are submitted in **one array job**, so that the three arms of a model run
in the same days, on the same GPU class and the same container image. A cell that is
preempted or reaches its time limit is resumed in place. Job ids and dates are recorded
in section 9.

Run tag `matched-run`; folders `slurm_vllm_<model tag>_off_<cell token>_matched-run`,
synced to `results/matched-run/`. Smoke tag `matched-run-smoke`.

### 2.5 A new corpus

The rows of this run are never pooled with the rerun, the control, the main sweep or
the smoke. No cell of this run stands in for a cell of a filed readout.

---

## 3. The grade, fixed before the run **[Omer, A8, A9]**

**One registered grade: delivered right.** It is applied in the same way to the three
arms. A trial is right when the final answer, as the model wrote it, is right:

- **solve.** The delivered plan is the plan in the last closed code block of the answer
  when that block holds a plan; otherwise the plan the rerun's grader reads. The plan
  must pass the validator. This is the "second reading" of the control
  (`block_plan`, imported unchanged), which was written before any answer under the
  format-stated message existed.
- **simulate.** The trace the rerun's grader reads must equal the answer key; a trace
  written one JSON object per line also counts when it equals the answer key exactly
  (`line_reader_exact`, imported unchanged).
- **The simulate answer key [Omer, ISS-029].** The key is the cached reference trace,
  as in every earlier readout. Known in advance: on 6 of the 100 problems (barman p01
  to p05, gripper p03) the plan placed in the prompt can differ from the plan of the
  cached key. A correct simulation of the prompt's plan is then graded wrong. This
  touches 18 of the 300 simulate trials of an arm, the same trials in all three arms.
  Recommended, and written here: keep the cached key, so that the grade equals
  October's. One descriptive count is registered per model and arm: the simulate trials
  on those six problems, and how many of them are right.
- **Exception rows.** A trial on which the harness raised is wrong under the registered
  grade, whatever answer it stored, as under the rerun's grader.
- **Validator and capitals [A9].** pddl-pyvalidator **0.1.5**, the release of every
  earlier readout, in process, through the route of the control. Release 0.1.5 rejects
  a valid plan that writes a declared name with a capital letter. So the plan is sent
  to the validator in lower case, in every arm. Every plan is lower-cased, not only a
  plan in which a capital is seen. The analysis counts the trials where this differs
  from the control's case-folded column (which lowers a plan only when it holds a
  capital). The analysis halts on any other
  release, on a verdict that is not a plain true or false, and when the route does not
  return the stored verdict for the rerun's plans (the control's check).

**Reported beside it, descriptive, for the supplement only:** the rerun's frozen grade,
and the registered grade without the lower-casing (the control's second reading as
filed, which still reads the stored answer of an exception row). They let a reader connect this run's
table to the earlier ones. No reading of section 5 uses them.

**What the grade does not do.** It does not repair a broken JSON answer, read a plan
from prose outside a code block where the rerun's grader would not, or use the tool's
output in place of the final answer. A tool that returned the right result and a model
that did not deliver it is a wrong trial; that gap is RQ3.

---

## 4. Contrasts and statistics

All contrasts are paired on the trial (task, domain, problem, plan label, wording), per
model and task, in points. A steered wording is paired with its plain wording on the
same problem (v14 with v11, v15 with v12, v16 with v13), as in the rerun.

| name | contrast | role | number |
|---|---|---|---|
| **M1** | P minus N | **primary**: do the tools help when merely offered? | 6 |
| **M2** | S minus N | do the tools help when the prompt names the tool? | 6 |
| **M3** | S minus P | what does naming the tool add? | 6 |

**Continuity checks, across runs, descriptive.** Each crosses two runs, is printed with
the dates of both, and is no gate on anything:

| name | contrast | number |
|---|---|---|
| **K1** | N minus the control's cell B | 6 |
| **K2** | P minus Part A, plain | 6 |
| **K3** | S minus Part A, steered | 6 |

The rows of the control and of Part A are graded again with the registered grade of
section 3. Their frozen grades must reproduce the filed readouts, or the analysis halts.

**Intervals.** 95% percentile intervals from the frozen domain-cluster bootstrap of the
rerun (`tools.delivered_rerun.stats.cluster_bootstrap`): 20 domains, 10,000 resamples,
seed 20261002. Rates carry the same interval.

**Readings of one contrast.**

- M1 and M2: **tools ahead** when the interval is above 0, **no tools ahead** when it is
  below 0, **no difference shown** otherwise.
- M3: **naming the tool helps** / **hurts** / **no difference shown**, by the same rule.
- K1 to K3, with the margin of 5 points of the control: **criterion met** when the whole
  interval lies inside [−5, +5]; **a difference is shown** when it excludes 0;
  **unresolved** when neither. The margin is a threshold chosen in advance. A check can
  be "criterion met" and "a difference is shown" at once (a small difference that is
  inside the margin); both labels are then given.

**Multiplicity.** As in the control: readings use the unadjusted 95% interval; beside
every contrast the analysis reports an exact sign-flip p-value over the 20 domains,
Holm-adjusted across the six contrasts of the same name. A difference whose interval
excludes 0 and whose adjusted p-value is 0.05 or more carries the words "(not after
Holm)". This applies to K1 to K3 as well, with a family of six per name. The number of
contrasts (18, and 18 continuity checks) is stated with every
table.

---

## 5. Registered readings

Per model and task. No reading pools models or tasks.

**Q1. Do the tools help on this task? (M1, and M2 beside it.)** The label of M1 is the
answer the paper gives for "tools offered". The label of M2 is given beside it for
"tools offered and named". Where the two differ, both are stated, and M3 says what
naming the tool added. Two labels differ when they still differ once the words "(not
after Holm)" are removed.

**Q2. Continuity. (K1 to K3.)** Where a check meets the criterion, the supplement says
this run reproduces the earlier one for that model, task and arm within the margin, and
gives the estimate. This holds too when the check also carries "a difference is shown".
Where the criterion is not met, the supplement says so and gives the estimate. Either
way the body quotes this run.

**Readings that would be wrong, named in advance.** "The unaided model is as good as
the tools" from an M1 interval that includes 0: that is "no difference shown". "The
tools hurt" from the same. A pooled figure over the three models. A simulate result
read as a statement about the simulate tool being right or wrong: the tool's own
correctness is not what this grade measures.

**What is expected, stated so that it cannot be claimed as a discovery later.** From the
earlier runs: on solve, tools ahead for Qwen3.5-9B and Gemma-26B by tens of points, and
a small or unshown gap for Qwen3.6-35B; on simulate, no model with tools ahead. The run
may confirm or change each of these.

---

## 6. The reporting rule

Fixed here, before any data:

1. **This run is what the body of the paper reports for RQ1 on solve and simulate**, for
   the three open models: the rate of each arm under the registered grade, and M1, M2
   and M3 with their intervals and labels, whatever they show.
2. **The rerun's and the control's figures on these two tasks move to the supplement**
   with the continuity table, the frozen-grade columns and the record of why the arm
   was run again. One sentence in the body points there.
3. **RQ2 and RQ3 in the body stay on the rerun's tool arms**, on all five tasks. The same
   measures (which tool was called; tool right and final answer wrong) are computed on
   this run's tool rows with the definitions of `tools/reanalysis/rq23_metrics.py` and
   reported in the supplement as a second sample on two tasks. They do not replace the
   rerun's figures. In "final answer wrong", right and wrong mean this run's registered
   grade (section 3). The version under the rerun's frozen grade is printed beside it.
4. **The breakdowns the draft already shows** (solved by reference plan length; simulate
   by trace length; the lenient simulate score) are computed on this run with the bins
   and definitions of `tools/reanalysis/rq1_control_metrics.py`. A trial counts as right
   under this run's registered grade. They are descriptive. Tables only: the figures and
   the LaTeX rows of that script are not part of this registration. The problems left
   out of the by-length simulate tables are chosen by the rule of that script from this
   run's rows (the plan most tool rows passed to the simulate tool is not the reference
   plan), and the list is printed.
5. **No paper text is part of this registration.** The readout goes to Omer.

---

## 7. Execution

- **Order.** Submit-script change merged → this registration answered and the analysis
  frozen (section 9, the five gates of the freeze protocol) → smoke → full run → sync →
  frozen analysis → readout and a `NUMBERS.md` entry. Every SSH or SLURM action needs
  Omer's explicit go-ahead; the smoke and the full run are asked for separately.
- **Smoke.** The full-run SLURM profile, the real configuration with `--partial 1` (the
  first problem of every domain: 120 rows in each N folder, 240 in each tools folder),
  run tag `matched-run-smoke`, all six cells. Never pooled. Checks allowed on smoke
  output, and nothing else:
  1. every job completes and every cell folder holds its rows;
  2. the frozen loader reads every row; no exception or infrastructure-failure row; no
     row cut by storage; no half-written line;
  3. in every N cell at least 95% of the stored answers are non-empty; in every tools
     cell at least 95% of the answers of trials whose final turn was not refused or
     clipped for a full context window are non-empty, and each task has at least one
     such trial. A final turn is refused or clipped
     by the two rules of the rerun's category "refused or clipped final request"
     (`REFUSED_OR_CLIPPED_FINAL` in `tools/delivered_rerun/e4.py`): the row's `no_room`
     is set, or its last turn ran with a clipped allowance
     (`tokens.ctx_clip_last_turn_max_tokens`) and stopped at it (`done_reason`
     "length"). In Part A the smoke subset has 26 to 30% empty answers in a tools cell,
     nearly all of them such rows on simulate, so a plain 95% rule would fail on every
     tools cell;
  4. the system text sent. The audit log has one line per request and no trial key, so
     the check is: every audit line of a cell carries the registered system sha256 of
     its task (N: the format-stated text, marked swapped; tools: the with-tools text of
     section 2.1, marked not swapped); and, per task, the log has at least as many lines
     as the cell has rows and exactly as many different first-user texts as rows (an N
     cell has three wordings per task, a tools cell six);
  5. the N and tools cells of a model hold the same problems; the set of user-text
     sha256 of v11 to v13 is the same in the N cell and in the tools cell (every user
     text of the N cell is also in the tools cell, and the tools cell holds as many
     other texts as the N cell has texts: the steered wordings);
  6. every request of a tools cell is logged with tools present, and no request of an N
     cell is;
  7. the serve log shows vLLM 0.20.2 and no other version; the cluster's tools repo is
     at `5e4f9c0` (read on the cluster and recorded by hand, section 2.3).
  The check prints these items and no success rate, no failure-reason count, no tool-call
  count and no answer text.
- **Items 4 to 7 are preconditions of the analysis** on the full run, together with the
  apparatus checks of the control (window, caps, temperature, thinking, model, storage
  rule). Every summary file must also name the two tasks of this run and no output cap
  of its own, so that the caps are the harness's 8,192 and 6,144. Items 1 and 2 are
  replaced on the full run by the completeness rule, the VOID rule and the storage rule
  below. Item 3 is for the smoke only.
- **During the run.** Monitoring reads row counts and job states only.
- **Stop rules.** A cell folder is VOID if more than 1% of its rows are exception or
  infrastructure-failure rows (the rerun's definition). When a cell is VOID, **both
  cells of that model are run again from scratch, together**, under the run tag
  `matched-run-r2`, so that the three arms still share a window. This is declared here
  and is not a deviation. Any other stop is a deviation.
- **Completeness.** N: 600 rows, 300 per task, 200 per wording. Tools: 1,200 rows, 600
  per task, 200 per wording. A short cell is resumed, not analysed. The trial keys of
  each arm must equal those of the rerun for that model and task; a difference halts
  the analysis. The unpaired count is therefore zero, and it is printed.
- **Exception rows at or under 1%** stay in the denominator and are wrong under every
  grade the readings use (section 3).
  **Rows cut by storage, duplicate keys, half-written lines:** the control's rules.
- **The analysis does not read a row of the full run** unless it is started with the
  package hash of section 9.

---

## 8. Secondary, descriptive (not gates, not readings)

Per model, task and arm, with counts: right answers by wording; the layout of the
answer (the control's categories); answers that stopped at the output cap (the answer
ended at the cap and its final turn was not refused or clipped); trials whose final turn
was refused or clipped because the prompt and the tool output filled the window (the
rule of section 7, item 3), counted on their own; mean output tokens (in
a tools arm, summed over the turns of a trial; the rows hold no per-turn count); the
rerun's failure reason for each trial that is wrong under the registered grade; the
frozen-grade and
not-lower-cased columns of section 3, and beside them the count of trials where the
registered grade differs from the control's case-folded column; the count of section 3
for the six simulate problems; the Holm-adjusted p-values; the measures of section 6,
rules 3 and 4. In the table "tool right and final answer wrong", a trial that the rerun's
rules cannot classify is counted as "not classified" and the count is printed.

**Tripwires that halt the readout until audited**, all on the registered grade: the same
count of right answers in all nine model-by-arm cells of a task; an arm in which no answer at all is read on a task (no
trial of the arm on that task has an answer read by the rerun's grader, a plan block, or
a trace written one object per line); an arm whose rate differs by more than 20 points
from its continuity partner (K1 to K3); a tools arm (model, task, P or S) in which no
trial called a tool; and, **for arm N**, more than
5% unread final answers (the control's definition) for a model and task. One case is
known in advance and has its own threshold: Gemma-26B on simulate, where the control
counted 52 of 300 and audited them; there the tripwire fires above 90 of 300.

---

## 9. Freeze record

*Not frozen. To be filled in: harness commit, tools repo commit, analysis commit,
package hash, the five gates, the dry run on existing data, the submit command, job ids
and dates, GPU class and memory from the job log, sha256 of the frozen files.*

Candidate package hash after the independent review:
`1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d`
(`python -m tools.reanalysis.matched_run --print-package-hash`, 2026-11-25). It is not
a freeze. Any later edit changes it.

Input files outside the package hash. The analysis checks their sha256 and halts on any
other:

| file | sha256 |
|---|---|
| `tools/reanalysis/out/rq1_layout_regrade.json` | `eb56a2e4c1fa38e5a04c3357e9776732871f506906d8d1bb8124a9d4f8164017` |
| `tools/reanalysis/out/control_prompt_fix.json` | `f50452ad5a3d03e8070cd391e8ff1f44c0fcd0aa91176322cedf1335abe4fc3d` |
| `development/reference/delivered_rerun_readout.json` | `81bd59ffd153dafe20e9d9d7422785fff05d8dba894e9f8a331b919a7334c674` |
| `results/delivered-rerun-secondary/plan_verdicts.json` | `3c945faeafbdd36ec921d97bb554ef6ef6e9c53225f61e943056571284c6afb0` |

Recorded, not checked by the analysis: `pddl_eval/vllm_client.py`, sha256
`66a58c6adf2dc52d12936fa0d7a37c9e74907b0a755ea315730b324515caf5e9`. It writes the audit
log; the shape of its lines is what the audit checks of section 7 read. If this file
changes before the run, those checks are read against it again.

Dry run on existing data, 2026-11-25. **Old data. Not results of this run.** The
analysis was run with arm N filled by the rows of the control's cell B and arms P and S
filled by the rows of Part A (`--dry-run-existing`). No row of this run existed.

- K1 to K3 are exactly zero in all 54 entries (18 checks under three grades): estimate
  0, interval [0, 0], 20 domains, 300 pairs, none unpaired.
- M1 without the lower-casing equals the control's filed C4 under the second reading in
  all six cases (estimate, interval and p-values).
- The lower-casing changed no trial in any cell.
- On the six problems of section 3 [Omer, ISS-029] every arm had 18 trials and none was
  right.
- The dry run was repeated after the review edits, with the same three results.

Planned submit command (the flag `--with-tools-cell` is on branch
`harness/matched-run-cells`, commit `2522786`, not merged; a local dry run gives one
array of six tasks, `rtx_6000:1`, `--mem=48G`):

```
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b \
  --no-tools --think-modes off --tasks "solve simulate" \
  --no-tools-system "format-stated" --with-tools-cell \
  --run-tag matched-run --gpu-type rtx_6000 --time 24:00:00
```

`--time` is set at submission and cannot be raised afterwards. A with-tools cell of the
rerun (4,560 rows, five tasks) did not finish in 12 hours; a cell here has 1,200 rows
of the two long tasks, so 24 hours is asked for.

## 10. Smoke record

*Empty.*

## 11. Deviations

*None yet.*
