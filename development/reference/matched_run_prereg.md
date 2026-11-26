# Pre-registration: the matched run (tools against no tools on solve and simulate, one job)

**Written 2026-11-25, before any trial of this run exists. The analysis was frozen the
same day (section 9).** Decision
to run: Omer, 2026-11-25 (`development/datasets_breakdown.md`, option 1;
`paper_notes_discussions.md`, 2026-11-25). It reuses the registration of the
corrected-prompt control (`control_prompt_fix_prereg.md`) and its analysis wherever it
can, and says where it differs.

**Choices that were Omer's** are marked **[Omer, A5]** to **[Omer, A10]** after the
questions of `development/unified_run_design.md`, and **[Omer, ISS-029]** (the simulate
answer key, section 3). Each was written here as the session recommended. **Omer
accepted all of them on 2026-11-25 ("Yes, accept all"), before the freeze and before
any trial.** Nothing in sections 1 to 8 changes from here on without an entry in
section 11.

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

**FROZEN 2026-11-25.** No row of this run existed at freeze time, and nothing had been
submitted to the cluster. The analysis does not read a row of the full run unless it is
started with the package hash below.

| item | value |
|---|---|
| analysis branch and commit | `analysis/matched-run-prereg`; the code is unchanged since commit `41f9059` (PR #152) |
| package hash (`--i-have-frozen`) | **`1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d`** (37 files: the analysis script and the repo files it imports, among them the frozen packages of the rerun and the control, whose own hashes are still `822aace9…` and `825dab63…`) |
| gate 1, typed loader | every row through the rerun's frozen `schema.parse_row` |
| gate 2, constants as raised checks | yes; the package refuses `python -O` |
| gate 3, traceability map | `development/reference/matched_run_traceability.md`; nothing left unimplemented |
| gate 4, synthetic fixture | `tests/test_matched_run.py`, 586 checks with literal expected values |
| gate 5, independent review | a second agent that did not write the code, 2026-11-25, two passes: no code path giving a wrong number; 7 should-fix items and the notes of the first pass fixed and verified in the second; one wording point of the second pass fixed in this document (smoke item 3). Five planted cases recomputed by hand by the reviewer |
| tools repo `pddl-copilot` on the laptop (validator route) | `e428f17fd0b211f502955b11177687d544b68277`; pddl-pyvalidator 0.1.5; validator server file equal to the filed re-grade's |
| harness commit | `main` at `3044981bf5bfb1d624a55533e4e4765bac493dbf` (merge of PR #151, the flag `--with-tools-cell`; Omer merged it on 2026-11-25). The cluster checkout must be at this commit for the smoke and the full run |
| cluster tools repo | to be read on the cluster before the smoke and before the full run (must be `5e4f9c0`) |
| submit command (full run) | from `~/pddl-copilot-experiments` on the login node, after a dry run of the same command: `bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b --no-tools --think-modes off --tasks "solve simulate" --no-tools-system "format-stated" --with-tools-cell --run-tag matched-run --gpu-type rtx_6000 --time 24:00:00` (the smoke's command without `--partial 1`, with the run tag `matched-run`) |
| job ids and dates (full run) | Job **24502726**, submitted 2026-11-26 07:09 IST on Omer's go-ahead ("Yes, run it"), one array of six tasks (0 to 5: Qwen3.5-9B N, tools; Gemma-26B N, tools; Qwen3.6-35B N, tools). `TimeLimit=1-00:00:00` read back. Read on the cluster before submitting: experiments checkout at `3044981`, no tracked change; tools repo at `5e4f9c0`, clean, pddl-pyvalidator 0.1.5; no folder of this run tag existed; no other job of his in the queue. Task job ids, end times, restarts, GPU class and memory from the job logs: to be filled in when the run ends |

sha256 of the frozen files. Any later edit to one of them is a declared deviation in
section 11, followed by a new freeze.

| file | sha256 |
|---|---|
| `pddl_eval/__init__.py` | `0164c8d1cca872a3be65dd2461d627b95cdae8dc4b23ef4a6c6871b632c1e3db` |
| `pddl_eval/chat.py` | `f195e0889bc0003c6faf2050bbdec28d525ace5cc9ecacf7c1be3a2b28426907` |
| `pddl_eval/control_prompts.py` | `9e6380e08fb9704db5edac82efe216ff4ec518abcaf1d94874e266c0e06adff4` |
| `pddl_eval/domains.py` | `6f2a7f98c7327b535fa3d489f31555969b94fc03b735fb2735f2c96527aa7a94` |
| `pddl_eval/prompts.py` | `f12c19e9026bea463cdb5cf0b1e9ece96104e419a1bf51f9f1b0bf5dddd32e92` |
| `pddl_eval/resume.py` | `f4abc5d4843204f42e7099f7eedfcc4ff3e3763d7b2848db4dfae0a154ba72c9` |
| `pddl_eval/runner.py` | `95213c61e343447d76f16be7bb1dcb0cfa3798d0febf14a440a352a11bd6f1cb` |
| `pddl_eval/schemas.py` | `335b62a6d2907eace6694f899e1d54f87764e85e8deb6c65aaba7c20b45528ef` |
| `pddl_eval/scoring.py` | `13444404ed07f5fe06216248b742d8d286da7caad631ccab6b374837ed237299` |
| `pddl_eval/summary.py` | `6b3475163cee2b35f7ce816d00b1886b6c788b1d2caa6c083ff0b518e4eebb36` |
| `run_experiment.py` | `38f0b5d4fb1dba014efbfadaa101444f8a1b183d12fd92ed6a45d92e4addad29` |
| `tools/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tools/_run_manifest.py` | `08db2b20be699c818e47e15e589639d4294a40be1a6707b5a1e8c5acf2152c45` |
| `tools/delivered_rerun/__init__.py` | `1450beb6fe7ba5d573676ca1825a4cba39b4d73cb82159d903e436e6e8675917` |
| `tools/delivered_rerun/analysis.py` | `ec915da3da9eda78870e7cc26cb5bcf0d145cfb21dd7d7f846c2ec00a530de8b` |
| `tools/delivered_rerun/constants.py` | `879daf12ce176a71f7d7c2137b73c21a7844ff562dde9b07da4d67b60bc9a1b9` |
| `tools/delivered_rerun/e4.py` | `2ad776ee4b648971d0459c613db85d34326d8c3c6ec330ee75f5c71893a2c25b` |
| `tools/delivered_rerun/grade.py` | `1588646c021ce23126d11b716bad9c24f794e72894b0e73f261dc206b32b617e` |
| `tools/delivered_rerun/readout.py` | `ffddae5576d396d1bd69e2baee8958892a91f96856f9fae035c0be3bc5c78590` |
| `tools/delivered_rerun/run.py` | `8410090db908cfb01622cbfd4d7f97204b82139c434d03e92da03fbd5e68f940` |
| `tools/delivered_rerun/schema.py` | `5e33d6bd16ebcdf6b7298002d5929d07b7601f32b586c93933a176688e9aa66e` |
| `tools/delivered_rerun/stats.py` | `f37950779694741c106b0a8d20e6d4afe9d10573a658edd7e3efdd8c726d87a0` |
| `tools/delivered_rerun/tripwires.py` | `f53193a5f2b40ec9bae3cbe64df4b44691f2dca54cb494eb60fb79d640145ae4` |
| `tools/e2e_regrade.py` | `45dcf74a23b5d2b1d79028fd1733a9ba7884ba7f62f84c7ffa4febd100c4b11a` |
| `tools/gt_cache_gate.py` | `1181781e674f212c7d62c4fcdb6d50eb7ee9e650887d8e2bd95937609d8f3897` |
| `tools/reanalysis/bc_common.py` | `f9c2c8032dc5df8a6deda3ac1e8193b4d343c2cdde6f2e213c6e2c22440dcb67` |
| `tools/reanalysis/control_prompt_fix.py` | `ce2369c83d0c0d3b46aaf46fa28b8fc05430a40585a44da79281326af101bc53` |
| `tools/reanalysis/gen_common.py` | `97a28322bfcc2990b5564c59a968d28af874142a50536ec53995a3c21458bcd4` |
| `tools/reanalysis/iss027_common.py` | `33e0b4a34c11fb71456efb05228e4b86b15b691353e538910725f2199d4af4b5` |
| `tools/reanalysis/matched_run.py` | `e493caa4f6dfc02431082ebeedb752452bfdebfb84737fe7ee0371430d076054` |
| `tools/reanalysis/rq1_control_metrics.py` | `21a946331ff0a76ecbd85e253b0083e5d428e5214c89ad4e40276e2cdb3440f7` |
| `tools/reanalysis/rq1_figures.py` | `a4a51eaf3695b0f0ef4e5717efee5e59155d61f3ddb6c5373dc672f6df125817` |
| `tools/reanalysis/rq1_layout_regrade.py` | `557c603618017946d0109cb01b9de6868f4db5a5fcf4c04a50c68fb6ebf3cd79` |
| `tools/reanalysis/rq1_metrics.py` | `b2fc5edcbed5095dba4865e7deaacc81a946626f661b668b895bfd0e98e175fe` |
| `tools/reanalysis/rq1_tex.py` | `85ecd0b9e51468f27ecf12594eda9b110015569966ac90982cae7385c3c52264` |
| `tools/reanalysis/rq23_metrics.py` | `b9b2d6c9773c12bf7d8fde02e264c7027df14339e528873e5a75649a125f4123` |
| `tools/reanalysis/rq3_context_pilot.py` | `af92e8dc190c1c92ac6023fa1e3a31024b28ad1ddc917d74ab66ca54fef2b549` |
| `development/reference/matched_run_traceability.md` (outside the package hash) | `0b17cfe1eb6361a049a6bb731b929df231182940094fd99325d2790437818ce4` |
| `tests/test_matched_run.py` (outside the package hash) | `ffddfac7ddb5d0a1cf8cb250d9889167a3e568d186af99c433b15d3af67b69e6` |
| `tests/fixtures/matched_run/build_fixture.py` (outside the package hash) | `43dea783e57b3546ddf2a992de5e332d3807b258186493643e234b5a5edb41cd` |

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
`harness/matched-run-cells`, commit `2522786`, merged as `3044981`; a local dry run gives one
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

**Submitted 2026-11-25 22:17 IST** (Omer's go-ahead for the smoke, the same day), from
`~/pddl-copilot-experiments` on the login node, after a dry run of the same command:

```
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b \
  --no-tools --think-modes off --tasks "solve simulate" \
  --no-tools-system "format-stated" --with-tools-cell \
  --run-tag matched-run-smoke --partial 1 --gpu-type rtx_6000 --time 24:00:00
```

Job **24499771**, array tasks 0 to 5, one `rtx_6000` per task, `--mem=48G`,
`TimeLimit=1-00:00:00` read back from the queue (the full-run profile; only `--partial 1`
and the run tag differ from the full run's command). Array index to cell: 0 Qwen3.5-9B
N, 1 Qwen3.5-9B tools, 2 Gemma-26B N, 3 Gemma-26B tools, 4 Qwen3.6-35B N, 5 Qwen3.6-35B
tools.

Read on the cluster before submitting: experiments checkout on `main` at
`3044981bf5bfb1d624a55533e4e4765bac493dbf` (fast-forwarded from `9109179`); tools repo
`pddl-copilot` at `5e4f9c0bfbea0fdfe802edb08eaa2aa9d2095d38`, clean, with
pddl-pyvalidator 0.1.5, left as it was (the preflight script was not run, because it
pulls that repo and upgrades its packages); no folder of this run tag existed.

**Result, 2026-11-25: the smoke passes.** All six array tasks ended COMPLETED with exit
code 0 (`sacct -j 24499771`), between 22:17 and 23:34 IST, with no restart and no
preemption. The registered check (`--smoke-check`, code at package hash `1f3d0f84…`, on
the folders synced to `results/matched-run-smoke/`) printed PASS for all seven items:

| item | result |
|---|---|
| 1 | every job COMPLETED; 120 rows in each N folder, 240 in each tools folder |
| 2 | the frozen loader reads every row; no exception row, no infrastructure-failure row, no row cut by storage, no half-written line |
| 3 | at least 95% non-empty answers in every N cell; in every tools cell the same among the trials with room, with at least one such trial per task |
| 4 | N cells: the registered system text in every audit line, marked swapped. Tools cells: one system text per task, the with-tools text of Part A, not swapped. This is the first real audit log of a tools cell; it has one line per request (582 to 691 lines for 240 trials), as read from the code before the run |
| 5 | the N and tools cells of a model hold the same problems; every user message of the N cell is also sent in the tools cell; no re-sent request |
| 6 | every request of a tools cell is logged with tools present, and no request of an N cell is |
| 7 | every serve log shows vLLM 0.20.2 and no other version; tools repo at `5e4f9c0`, read by hand before submission |

**Apparatus, read from the job logs:** GPU `NVIDIA RTX 6000 Ada Generation` (49,140 MiB)
in all six tasks; 49,152 MB memory; `Concurrency: 4`; context 16,384; tasks solve and
simulate only; one model per task and card. Task job ids: Qwen3.5-9B 24499774 (N),
24499775 (tools); Gemma-26B 24499776 (N), 24499777 (tools); Qwen3.6-35B 24499778 (N),
24499771 (tools). Run time of a cell: 23 to 77 minutes. The N cells also start the tool
servers, as every cell of the harness does; no N request carried a tool (item 6).

**What was seen of the smoke's outcomes.** No success rate, failure-reason count or
tool-call count of the smoke was computed or read by the session. While copying the job
logs, the agent that did the sync saw a few per-trial result lines on its screen (two or
three per cell). It did not count or report them, and the session has not seen them.
This is recorded here because the rule of section 7 is that nothing but the seven items
is read.


## 11. Deviations

**1. One model's results were read while the run was unfinished (2026-11-26, about 10:25
cluster time).** Section 7 says that during the run only row counts and job states are
read. Omer asked to see the results of the cells that had finished, to check that the
run behaves as expected. The session said twice what that costs and recommended
waiting; he first chose to wait and then asked for Gemma-26B's results. At that moment
the two Gemma-26B cells and the Qwen3.6-35B no-tools cell were complete, and the three
other cells were running (Qwen3.5-9B both, Qwen3.6-35B tools).

- **What was read:** for Gemma-26B only, the rate of each arm on solve and simulate
  under the registered grade, and M1, M2 and M3 with their intervals. Computed by a
  separate script that calls the frozen functions without changing them, because the
  frozen analysis refuses an unfinished run. Holm-adjusted values were not computed
  (they need all six contrasts of a name).
- **What was not read:** any row of Qwen3.5-9B or Qwen3.6-35B.
- **What it could have changed, and did not:** the analysis was frozen before the run
  and its package hash is unchanged; the three running cells were left alone, with no
  cancellation, resubmission or change of any setting after the look.
- **The record is the registered analysis,** run once on the complete corpus with the
  package hash. The early figures are not filed in `NUMBERS.md` and are not quoted.
