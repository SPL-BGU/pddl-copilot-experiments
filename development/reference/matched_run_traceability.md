# Traceability map: matched-run prereg to the analysis code (freeze gate 3)

**Freeze candidate. Not frozen.** No hash of this code is recorded as frozen; the
independent review (gate 5) and the owner's answers to the open choices come first.

Spec: `development/reference/matched_run_prereg.md`, sections 2 to 8 (the draft of
2026-11-25, branch tip `7d33589`).
Code: `tools/reanalysis/matched_run.py` (written `MR:<line>` below; a function is cited by
its name and first line). Functions of the control's frozen analysis are written
`CPF:<name>` (`tools/reanalysis/control_prompt_fix.py`, imported, not edited).
Fixture checks: `tests/test_matched_run.py` (written `T:<test function>`), on the fixture
built by `tests/fixtures/matched_run/build_fixture.py`.
Line numbers are those of the freeze candidate; a re-freeze re-checks them.

Each entry quotes the clause, then names the code or runtime check, then the fixture
check that exercises it. Clauses that are not testable commitments (purpose, order of
human steps, what the paper says) are marked "not code" with the reason. Clauses with no
implementation, or only part of one, are collected at the end under **NOT IMPLEMENTED**.
Choices the code had to make where the spec leaves room are listed under **Choices made**.

Shared mechanics used by many entries:

- every registered constant is a raised check in `check_constants` (MR:207) and
  `check_design` (MR:303), called at import (MR:344) and again in `main` (MR:1551). The
  checks call the control's `_check`, which raises `RegisteredCheckFailed` and is not an
  `assert`, so `python -O` cannot strip it; the frozen `constants.py` also refuses `-O`.
  `check_constants` first calls the control's own `check_constants`. T:test_constants
  flips every constant and every design field and sees the check fire;
  T:test_package_hash checks `-O` is refused.
- every row is read by `CPF:read_folder`, which calls the frozen `schema.parse_row` and
  the frozen `schema._check_completeness`, with a `CellSpec` made by
  `dataclasses.replace` from the rerun's `spec_rerun_c` (N) or `spec_rerun_a` (tools):
  `matched_spec` (MR:370).
- grade fields are read only through `CPF:ok_of` and `CPF:plan_of`; estimator code reads
  `Trial` records (MR:957) built in `grade_trials` (MR:976).
- the package hash covers this script, the control's script and every repo file either
  imports (`DEPENDENCIES`, MR:93; `package_sha256`, MR:358). The control's hash machinery
  is not touched: `control_prompt_fix --print-package-hash` still ends `825dab63…` and
  `tools.delivered_rerun.run --print-package-hash` still ends `822aace9…`
  (T:test_package_hash checks both).

---

## Section 2. Design

### 2.1 Arms and cells

> The table: N (no tools, the format-stated text of the control's cell B, v11 to v13,
> `no-tools-sysformat`), P (tools, the with-tools text of Part A, v11 to v13,
> `tools_all_minimal`), S (the same, v14 to v16, `tools_all_minimal`).

`ARMS`, `ARM_WORDINGS`, `CELL_TOKENS`, `FOLDER_WORDINGS` (MR:106-111), checked in
`check_constants` (MR:207) against the rerun's `C.PLAIN`, `C.STEERED`, `C.VARIANTS` and
the control's cell B token. Rows are split into arms by wording in `arm_rows` (MR:459).
T:test_constants; T:test_base (the steered arm lists v14 to v16).

> "P and S share one cell folder, as in Part A: the with-tools cell runs the six
> wordings. So each model has two cell folders, and the run has six."

`FOLDERS`, `ARM_FOLDER` (MR:108-109); `matched_spec` (MR:370) gives the tools folder
the six wordings; `load_matched` (MR:413) reads two folders per model.
T:test_constants (the two specs), T:test_base (corpus: 120 and 240 rows).

> "**[Omer, A5]** The no-tools message is the control's cell B. Its sha256 (utf-8) is
> `3dbc1baf…` on solve and `7ccf5d9d…` on simulate"

`N_SYSTEM_SHA256` (MR:113), checked equal to the control's `SYSTEM_SHA256["B"]` and to
the sha256 of the text in `pddl_eval/control_prompts.py` (MR:207). Every audit line of
an N cell is checked by `CPF:check_audit` with cell "B" (called at MR:660).
T:test_refusals ("audit N: wrong system digest", "audit N: not swapped").

> "The registered and reference-removed texts are not run again."

Not code (design). The spec of an N folder names the one token `no-tools-sysformat`.

> "Known in advance from the control: under this message Gemma-26B writes its simulate
> answer as one JSON object and breaks the brackets in about one answer in six (52 of
> 300). ... No answer is repaired."

No repair: `grade_trials` (MR:976) calls only the frozen grader and the two imported
readers. T:test_planted_answers ("an unread final answer is wrong"). The 52 is the
constant `UNREAD_KNOWN_CONTROL` (MR:168); its tripwire is in section 8.

> The with-tools system text ("the with-tools text of Part A, unchanged").

`TOOLS_SYSTEM_SHA256` (MR:119): `9b179ca1…` on solve, `ebf8e7fe…` on simulate. These
two digests are not in the prereg; they are derived from `pddl_eval/prompts.py`
(`WITH_TOOLS_SYSTEM_BY_TASK`) and asserted here. `check_constants` recomputes each from
the harness text and from what `build_messages(..., with_tools=True,
prompt_style="minimal")` sends for every wording v11 to v16 (MR:207), so the same text
for plain and steered is a checked fact. Every audit line of a tools cell is compared
with them in `check_audit_tools` (MR:508). T:test_constants, T:test_refusals ("audit
tools: wrong system digest", "the N text in a tools cell", "byte for byte").

### 2.2 Models, tasks and size

> "Models: `Qwen/Qwen3.5-9B`, `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`,
> `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` ... Folder tags `Qwen3_5_9B`, `gemma4_26b-a4b`,
> `qwen3_6_35b`."

`MODELS`, `MODEL_ORDER` (MR:126-127), checked against the rerun's `C.MODEL_IDS`
(MR:207). The frozen `parse_row` refuses a row whose model id is not the cell's.
Audit lines: `check_audit_tools` (MR:508), `CPF:check_audit`. T:test_constants,
T:test_refusals ("audit tools: another model").

> "Thinking off."

`C.THINK == "off"` (MR:207); the frozen `parse_row` requires `"off"` in every resume
key; `client_settings.json` and every summary: `CPF:check_apparatus` (N),
`check_apparatus_tools` (MR:619).

> "Tasks: solve and simulate."

`TASKS` (MR:128, MR:207); the cell specs register only these two tasks, so the frozen
loader refuses any other. T:test_constants.

> "Per model, task and arm: the 100 problems of the rerun (20 domains, 5 problems each)
> by three wordings = **300 trials**." / "Per cell folder: N 600 rows (300 per task);
> tools 1,200 rows (600 per task, 100 per wording and task)." / "Total: ... **5,400
> trials**."

`REGISTERED` (MR:196) and `check_design` (MR:303): 300, 600, 1,200, 200 per wording, 100
per task and wording, k = 20, 5,400. Enforced on the rows by the frozen
`_check_completeness` through the spec, and again per arm in `analyse` (MR:1180, "300
trials" check on every arm and every earlier cell). "The 100 problems of the rerun":
`check_keys_equal_rerun` (MR:490). T:test_constants (each field), T:test_refusals
("a short tools cell", "a short N cell", "trial keys that differ from the rerun's").

### 2.3 Fixed settings

> "The cluster's `pddl-copilot` checkout stays at `5e4f9c0`."

`TOOLS_REPO_COMMIT` (MR:131). It leaves no trace in a cell's files: see NOT IMPLEMENTED
1. The analysis refuses to run without a note saying how it was checked (`need_notes`,
MR:650). T:test_refusals ("item 7: no note on the tools repo").

> "Context window 16,384 tokens. Output cap 8,192 tokens on solve and 6,144 on simulate.
> Temperature 0. Four requests at a time. Answers stored up to 65,536 characters."

Window, temperature: `client_settings.json` and every summary, N by `CPF:check_apparatus`,
tools by `check_apparatus_tools` (MR:619). The frozen loader refuses a row whose clipped
allowance breaks the window and a stored answer longer than 65,536 characters. Output
cap, N rows: `CPF:check_apparatus`. Output cap, tools rows: `check_tool_row_caps`
(MR:597); the cap applies to each turn of the tool loop and `tokens.completion` is the
sum over turns, so the control's rule cannot be used (see Choices made 4). "Four
requests at a time": NOT IMPLEMENTED 1. T:test_refusals (the "apparatus:" cases),
T:test_cap_units.

> "vLLM 0.20.2 from the shared `~/vllm.sif`. GPU class `rtx_6000`, one model alone on
> its card, `--mem=48G`."

Version: `CPF:check_serve_log` on the serve log of the job each cell's
`client_settings.json` names (called at MR:660), or a hand note. GPU class and memory:
NOT IMPLEMENTED 1. T:test_refusals ("serve log shows another vLLM", "a missing serve
log", "item 7 by hand").

> "The user prompts v11 to v16 and the with-tools system text, byte for byte as in
> Part A."

System text: section 2.1 above. User prompts: only through the audit relation of
section 7 item 5 (`check_users`, MR:564); see NOT IMPLEMENTED 4.

> "The no-tools request still carries the `guided_json` field, which the server drops,
> as in the control. No decoder constraint in any arm."

NOT IMPLEMENTED 1 (no trace in a cell's files).

> "The harness: `main` at the commit recorded in section 9. ... No file under the frozen
> hashes `822aace9…` or `825dab63…` changes."

`RERUN_PACKAGE`, `CONTROL_PACKAGE` (MR:139-140); live mode halts when either package
hash differs (`load_earlier_live`, MR:834, and `rq1_metrics.load_rerun_cells`).
T:test_package_hash (both hashes unchanged).

> "How each setting is assured follows the control ... what leaves no trace in a cell's
> files is read from the submit output and the job logs and recorded in sections 9 and
> 10."

Not code: this is the rule NOT IMPLEMENTED 1 rests on.

### 2.4 One job, one window

> "All six cells are submitted in **one array job** ... Job ids and dates are recorded in
> section 9."

Not checked by the analysis: NOT IMPLEMENTED 2. The job id each cell's
`client_settings.json` names is written to the output (`audit.settings`, MR:660).

> "Run tag `matched-run`; folders `slurm_vllm_<model tag>_off_<cell token>_matched-run`,
> synced to `results/matched-run/`. Smoke tag `matched-run-smoke`."

`RUN_TAG`, `SMOKE_TAG` (MR:136-137); `folder_name` (MR:366); live root
`args.results / RUN_TAG` (MR:1551). T:test_constants (folder names).

### 2.5 A new corpus

> "The rows of this run are never pooled with the rerun, the control, the main sweep or
> the smoke. No cell of this run stands in for a cell of a filed readout."

The matched run is read only from folders named with the run tag (or the r2 tag); a
smoke folder carries another name and is not found. The earlier runs are read into
`Earlier` (MR:814) and meet this run only in K1 to K3. T:test_smoke ("the analysis does
not read smoke folders"). The dry run goes the other way (old rows fill the arms) and
says so in its mode, file name and first line (MR:1551, MR:1358).

---

## Section 3. The grade

> "**One registered grade: delivered right.** It is applied in the same way to the three
> arms."

`grade_trials` (MR:976), one function for every row of every arm and of the earlier
runs. `REGISTERED_GRADE` (MR:144). T:test_planted_answers ("caps_block in a tools row:
the same rule in every arm").

> "**solve.** The delivered plan is the plan in the last closed code block of the answer
> when that block holds a plan; otherwise the plan the rerun's grader reads. The plan
> must pass the validator. ... (`block_plan`, imported unchanged)"

MR:976: `RG.block_plan(r.response)`, else `CPF:plan_of` of the frozen `grade.grade`
result; the verdict comes from the one injected route. T:test_planted_answers
(json_block, right_to_wrong, wrong_lines, prose).

> "**simulate.** The trace the rerun's grader reads must equal the answer key; a trace
> written one JSON object per line also counts when it equals the answer key exactly
> (`line_reader_exact`, imported unchanged)."

MR:976 takes the `second` value of `CPF:second_reading`, which is the frozen grade or
`PILOT.line_reader_exact`. T:test_planted_answers (trace, per_line, per_line_wrong).

> "pddl-pyvalidator **0.1.5** ... in process, through the route of the control."

`CPF:live_route`; `validator_env` (MR:1706) calls `CPF:check_validator_env` (release
0.1.5, server file unedited and equal by sha256 to the filed re-grade's). `PYVALIDATOR`
(MR:142). Run in the dry run on this machine; not reachable from the fixture (the
control's T:test_validator_units covers `check_validator_env`).

> "So the plan is sent to the validator in lower case, in every arm."

MR:976: `verdict(r.domain, r.problem, RG.lower(plan))`, always, not only when a capital
is seen (see Choices made 1). T:test_planted_answers ("caps_block: right only in lower
case"; the route records that it was sent the lower-case plan).

> "The analysis halts on any other release, on a verdict that is not a plain true or
> false, and when the route does not return the stored verdict for the rerun's plans (the
> control's check)."

Release: `validator_env` (MR:1706). Verdict: `CPF:validator_verdict` and `CPF:Verdicts`.
Stored verdicts: `CPF:check_route` on the solve plans of Part C, Part A plain and Part A
steered, before any new plan is validated (MR:1180). T:test_refusals ("the route
disagrees with a stored verdict").

> "**Reported beside it, descriptive, for the supplement only:** the rerun's frozen
> grade, and the registered grade without the lower-casing. ... No reading of section 5
> uses them."

`DESCRIPTIVE_GRADES` (MR:145); `Trial.frozen`, `Trial.second` (MR:957) from
`CPF:grade_rows`; rates and contrasts under them are computed but carry no label
(`family`, MR:1243). T:test_base (RATES, DESCRIPTIVE, "a descriptive grade carries no
label").

> "**What the grade does not do.** It does not repair a broken JSON answer, read a plan
> from prose outside a code block where the rerun's grader would not, or use the tool's
> output in place of the final answer."

By construction of MR:976 (no other reader is called; tool calls are not read).
T:test_planted_answers (unread_sim, prose), T:test_base (Gemma simulate S: tool right,
answer wrong, graded wrong).

---

## Section 4. Contrasts and statistics

> "All contrasts are paired on the trial (task, domain, problem, plan label, wording),
> per model and task, in points. A steered wording is paired with its plain wording on
> the same problem (v14 with v11, v15 with v12, v16 with v13), as in the rerun."

`canon` (MR:468), `STEER_OFFSET` (MR:151, checked against `C.STEER_OFFSET`);
`CPF:paired` over the canonical keys in `family` (MR:1243), which raises unless there
are 300 pairs and none unpaired. T:test_planted_answers (canon), T:test_base (M2 of
Qwen3.5-9B simulate: 0 gained, 0 lost; the pairing trap).

> M1 = P minus N (primary), M2 = S minus N, M3 = S minus P, six each.

`CONTRASTS` (MR:147), `N_CONTRASTS` (MR:149); MR:1180. T:test_base (REGISTERED, 18
contrasts under three grades), T:test_constants.

> K1 = N minus the control's cell B, K2 = P minus Part A plain, K3 = S minus Part A
> steered; "Each crosses two runs, is printed with the dates of both, and is no gate on
> anything".

`CONTINUITY` (MR:148), `N_CONTINUITY` (MR:150); `q2_reading` (MR:1048) and the K table
of `render` (MR:1358) print `EARLIER_DATES` and `--run-dates`. No check halts on a K
label. T:test_base (K rows, "carries both dates").

> "The rows of the control and of Part A are graded again with the registered grade of
> section 3. Their frozen grades must reproduce the filed readouts, or the analysis
> halts."

Graded again: MR:1180 (`earlier`). Filed readouts: `check_filed_readout` (MR:896, the
rerun's E1 counts, plain and steered), `check_filed_regrade` (MR:914, the filed layout
re-grade: frozen, second reading, case folded), `check_filed_control` (MR:935, the
control's filed cell B counts). In live mode `rq1_metrics.load_rerun_cells` also halts
unless the rerun's package, ground truth and E1/E2 reproduce. T:test_refusals (the three
"does not reproduce" cases and "the steered arm is missing").

> "**Intervals.** 95% percentile intervals from the frozen domain-cluster bootstrap of
> the rerun (`tools.delivered_rerun.stats.cluster_bootstrap`): 20 domains, 10,000
> resamples, seed 20261002. Rates carry the same interval."

`CPF:boot` (k and level asserted) through `CPF:paired` and `CPF:rate`; `LEVEL`,
`B_BOOT`, `SEED` (MR:153-155) checked equal to the rerun's constants. T:test_base (k =
20 on every contrast and rate; the hand-computed intervals).

> "M1 and M2: **tools ahead** when the interval is above 0, **no tools ahead** when it is
> below 0, **no difference shown** otherwise."

`label_of` (MR:1024) calls `CPF:c4_label`. T:test_labels, T:test_base.

> "M3: **naming the tool helps** / **hurts** / **no difference shown**, by the same rule."

`m3_label` (MR:1012). T:test_labels, T:test_base.

> "K1 to K3, with the margin of 5 points of the control: **criterion met** when the whole
> interval lies inside [−5, +5]; **a difference is shown** when it excludes 0;
> **unresolved** when neither."

`label_of` (MR:1024) calls `CPF:contrast_label` (endpoints included; both labels can
hold at once). `MARGIN` (MR:152). T:test_labels, T:test_base ("endpoint exactly 5.0").

> "**Multiplicity.** ... an exact sign-flip p-value over the 20 domains, Holm-adjusted
> across the six contrasts of the same name. A difference whose interval excludes 0 and
> whose adjusted p-value is 0.05 or more carries the words "(not after Holm)"."

`ST.signflip_exact_p` in `CPF:paired`; `ST.holm(..., HOLM_FAMILY)` per name in `family`
(MR:1243). T:test_base (p and Holm values of all 36 registered rows), T:test_labels.

> "The number of contrasts (18, and 18 continuity checks) is stated with every table."

The `common` sentence of `render` (MR:1358). T:test_base ("states the number of
contrasts with the tables").

---

## Section 5. Registered readings

> "Per model and task. No reading pools models or tasks."

MR:1180 builds one reading per model and task; nothing pools. T:test_base.

> "**Q1.** ... The label of M1 is the answer the paper gives for "tools offered". The
> label of M2 is given beside it for "tools offered and named". Where the two differ,
> both are stated, and M3 says what naming the tool added."

`q1_reading` (MR:1035). T:test_base (Q1 labels, differ, sentence), T:test_labels.

> "**Q2.** ... Where a check meets the criterion, the supplement says this run reproduces
> the earlier one for that model, task and arm. Where it does not, the supplement says
> so and gives the estimate."

`q2_reading` (MR:1048). T:test_base, T:test_labels.

> "Either way the body quotes this run." / "Readings that would be wrong, named in
> advance" / "What is expected, stated so that it cannot be claimed as a discovery
> later."

Not code (what the paper may say). The labels above are the only readings the code
prints; it prints no pooled figure.

---

## Section 6. The reporting rule

> Rule 1: "the rate of each arm under the registered grade, and M1, M2 and M3 with their
> intervals and labels, whatever they show."

`rates` and `contrasts` of `analyse` (MR:1180); first two tables of `render` (MR:1358).

> Rule 2 (the earlier figures move to the supplement with the continuity table and the
> frozen-grade columns).

The K table, the descriptive-grade tables and "the earlier runs, graded again" table of
`render` (MR:1358). Where the paper puts them: not code.

> Rule 3: "The same measures (which tool was called; tool right and final answer wrong)
> are computed on this run's tool rows with the definitions of
> `tools/reanalysis/rq23_metrics.py` and reported in the supplement".

Which tool: `rq2_cells` (MR:1080) calls `rq23_metrics.row2` and `rq23_metrics.rq2`
unchanged and repeats the self-check of `rq2_rows`. Tool right, answer wrong:
`rq3_cells` (MR:1106) uses the frozen `analysis.e4_cell` and the formula of
`rq23_metrics.rq3_rerun` (see Choices made 5). T:test_base (tool choice classes; Gemma
solve P 20 of 60; Gemma simulate S 4 of 60). The dry run reproduces the rerun readout's
E4 counts and categories on all 12 cells.

> Rule 4: "The breakdowns the draft already shows (solved by reference plan length;
> simulate by trace length; the lenient simulate score) are computed on this run with
> the bins and definitions of `tools/reanalysis/rq1_control_metrics.py`, unchanged".

`breakdowns` (MR:1136): `rq1_metrics.problem_facts`, `metric3`, and `metric2` with
`rq1_control_metrics.best_state_score_second` put in place for that call (as that
script does). See Choices made 6 and NOT IMPLEMENTED 6. T:test_base (by reference
length; exact, strict and lenient state scores; a per-line trace scores all its
states). The dry run equals the filed `rq1_control_metrics.json` on all 45 by-length
cells of each table.

> Rule 5: "No paper text is part of this registration."

Not code.

---

## Section 7. Execution

> "Order." / "Every SSH or SLURM action needs Omer's explicit go-ahead".

Not code.

> "**Smoke.** ... `--partial 1` (the first problem of every domain: 120 rows in each N
> folder, 240 in each tools folder), run tag `matched-run-smoke`, all six cells. Never
> pooled."

`SMOKE` (MR:198), `check_smoke_design` (MR:328), `smoke_check` (MR:689). T:test_smoke,
T:test_constants.

> Item 1: "every job completes and every cell folder holds its rows"

Rows: MR:689 (`IncompleteCell`). Job states: NOT IMPLEMENTED 3. T:test_smoke ("a short
tools folder", "a missing folder").

> Item 2: "the frozen loader reads every row; no exception or infrastructure-failure
> row; no row cut by storage; no half-written line"

MR:689. T:test_smoke ("an exception row", "a half-written line").

> Item 3: "in every cell, at least 95% of the stored answers are non-empty"

MR:689, `SMOKE_NONEMPTY` (MR:161), every cell, as written. T:test_smoke (114 of 120
passes, 113 fails; 227 of 240 fails). **This item is expected to fail on the tools
cells**: see Spec question 1 in the hand-off report.

> Item 4: "in the N cells the audit log gives the registered sha256 for every trial; in
> the tools cells the same audit log (one line per request, so several per trial) gives
> one system text per task, the with-tools text of Part A, marked not swapped and with
> tools, for every trial"

N: `CPF:check_audit` with cell "B". Tools: `check_audit_tools` (MR:508). "For every
trial" is checked by count (each task has at least as many lines as rows and exactly as
many different user texts as rows): NOT IMPLEMENTED 4. T:test_base (476, 480 and 460
lines for 240 trials), T:test_refusals (the "audit" cases), T:test_smoke.

> Item 5: "the N and tools cells of a model hold the same problems; the user messages of
> v11 to v13 are the same in N and in the tools cell"

`check_same_problems` (MR:479); `check_users` (MR:564). T:test_refusals ("N and tools
cells do not hold the same problems", "steered wordings not on the plain wordings'
problems", "a user message of N is not sent in the tools cell"), T:test_smoke.

> Item 6: "every tools cell offered the tools (the tool list is recorded and non-empty),
> and no N cell did"

`has_tools` true on every audit line of a tools cell (MR:508) and false on every line
of an N cell (`CPF:check_audit`); the rows' `with_tools` by the frozen loader;
`client_settings.json` by `check_settings_tools` (MR:580) and `CPF:check_settings`. The
tool list itself is not in the files: NOT IMPLEMENTED 5. T:test_refusals, T:test_smoke.

> Item 7: "the serve log shows vLLM 0.20.2 and no other version; the cluster's tools
> repo is at `5e4f9c0`."

Serve log: `CPF:check_serve_log`, or a hand note. Tools repo: a hand note is required
(`need_notes`, MR:650); NOT IMPLEMENTED 1. T:test_smoke, T:test_refusals.

> "The check prints these items and no success rate, no failure-reason count, no
> tool-call count and no answer text."

MR:689 prints item lines, failure messages of the checks, row counts and re-sent
request counts only. T:test_smoke ("prints no rate, reason, tool-call count or answer
text").

> "**The same checks are preconditions of the analysis** on the full run, together with
> the apparatus checks of the control (window, caps, temperature, thinking, model,
> storage rule)."

`audit_matched` (MR:660), before any answer is graded; item 3 is a smoke-only check, as
in the control. T:test_refusals.

> "During the run. Monitoring reads row counts and job states only."

Not code.

> "**Stop rules.** A cell folder is VOID if more than 1% of its rows are exception or
> infrastructure-failure rows (the rerun's definition). When a cell is VOID, **both cells
> of that model are run again from scratch, together**, under the run tag
> `matched-run-r2`".

`check_void` (MR:402), `VOID_FRAC` (MR:162); `first_run_void` (MR:426) and
`resolve_tags` (MR:449): the r2 folders of a model are read only after the analysis has
itself found a first-run cell of that model VOID. T:test_refusals (2 of 120 and 3 of 240
are VOID), T:test_r2.

> "**Completeness.** N: 600 rows, 300 per task, 200 per wording. Tools: 1,200 rows, 600
> per task, 200 per wording. A short cell is resumed, not analysed."

`matched_spec` (MR:370) with the frozen `_check_completeness` (rows, rows per wording,
rows per task and wording, 20 domains; 300 and 600 per task follow). T:test_refusals,
T:test_constants.

> "The trial keys of each arm must equal those of the rerun for that model and task; a
> difference halts the analysis. The unpaired count is therefore zero, and it is
> printed."

`check_keys_equal_rerun` (MR:490); `family` (MR:1243) raises unless unpaired is 0; the
M table prints the column. T:test_refusals, T:test_base.

> "**Exception rows at or under 1%** stay in the denominator and are graded as they are."

The frozen grader gives them the reason "exception" (wrong). T:test_base (1 of 120),
T:test_refusals (2 of 240 kept).

> "**Rows cut by storage, duplicate keys, half-written lines:** the control's rules."

`CPF:read_folder`. T:test_refusals ("duplicate trial key", "a storage-cut row that did
not stop at the output cap").

> "**The analysis does not read a row of the full run** unless it is started with the
> package hash of section 9."

MR:1664 (`main`): the first statement of live mode. T:test_live_gate (no hash, a wrong
hash, the control's hash).

---

## Section 8. Secondary and tripwires

> "Per model, task and arm, with counts: right answers by wording; the layout of the
> answer (the control's categories); answers that stopped at the output cap and answers
> left empty because the prompt and tool output filled the window; mean answer tokens;
> the rerun's failure reason for each wrong trial; the frozen-grade and not-lower-cased
> columns of section 3; the Holm-adjusted p-values; the measures of section 6, rules 3
> and 4."

`secondary_tables` (MR:1333); the layout is `CPF:second_reading`'s; "window filled" is
the row's `no_room`; the two columns are in `rates`; the Holm p in `contrasts`.
T:test_base.

> "a count of right answers that is the same in all cells of a task"

T1 (MR:1279), over the nine cells of this run, registered grade. T:test_tripwires.

> "an arm in which the grader reads no answer at all on a task"

T2 (MR:1279), `Trial.read` (see Choices made 2). T:test_tripwires.

> "an arm whose rate differs by more than 20 points from its continuity partner (K1 to
> K3)"

T3 (MR:1279), `TRIPWIRE_POINTS` (MR:164). T:test_tripwires (fires at +33.3; released
with a written note).

> "a tools cell in which no trial called a tool"

T4 (MR:1279), per tools cell folder (see Spec question 4). T:test_tripwires.

> "and, **for arm N**, more than 5% unread final answers (the control's definition) for a
> model and task. One case is known in advance and has its own threshold: Gemma-26B on
> simulate, where the control counted 52 of 300 and audited them; there the tripwire
> fires above 90 of 300."

T5 (MR:1279), `CPF:unread_final` through `CPF:grade_rows`; `unread_limit` (MR:336),
`UNREAD_FRAC`, `UNREAD_KNOWN*` (MR:165-168). T:test_tripwires (3 of 60 stays, 4 fires;
arm P is not guarded; Gemma simulate 18 of 60 stays, 19 fires; 90 and 15 on the
registered design).

> "**Tripwires that halt the readout until audited**"

MR:1307: a fired tripwire halts unless `--audited-tripwires` and `--audit-notes` release
it with a written note, which is printed. T:test_tripwires.

---

## Choices made (where the spec leaves room)

1. **Lower case always.** The control's case-folded column lowers a plan only when it
   holds an ASCII capital. The registered grade here lowers every plan, as section 3
   says. The two agree unless a plan holds a non-ASCII capital letter; the output counts
   the trials where they differ (`registered_differs_from_case_folded`; 0 in the dry run
   and in the fixture).
2. **"The grader reads no answer" (T2).** An answer counts as read when the frozen
   grader reads one, or `block_plan` finds a plan block (solve), or the line reader
   finds a trace (simulate). The control's tripwire looked at the frozen grader alone.
3. **Failure reasons.** "The rerun's failure reason for each wrong trial" is counted
   over the trials that are wrong under the registered grade.
4. **Output cap in a tools row.** Three checks replace the control's rule: the sum of
   answer tokens is at most the cap times the number of turns; a one-turn trial follows
   the control's rule; a trial that stopped at the cap with no clipped and no refused
   turn used at least the cap in all. All 3,600 solve and simulate rows of Part A pass
   (run in the dry run). The check cannot see the tokens of one turn.
5. **Tool right, answer wrong.** "Answer wrong" is the rerun's frozen delivered grade,
   as `rq23_metrics.py` defines it; the count under the registered grade is printed
   beside it. `rq23_metrics.rq3_rerun` cannot be called (it loops over the rerun's five
   tasks and checks the rerun's readout), so the same lines are written out with the
   frozen `e4_cell`.
6. **By-length breakdowns.** A trial counts as right under this run's registered grade.
   `rq1_control_metrics.py` uses the second reading without the lower-casing.
7. **Q1, "where the two differ".** Two labels differ when they differ after the words
   "(not after Holm)" are taken away.
8. **Holm on K1 to K3.** Applied, six per name, as for M1 to M3.
9. **Item 7 needs two notes.** The vLLM version (serve logs or a note) and the tools
   repo commit (a note) are separate; the analysis refuses without either.
10. **Dates.** `--run-dates` is required; the dates of Part A and of the control are
    the constants the prereg's disclosure paragraph gives.

---

## NOT IMPLEMENTED

1. **Settings that leave no trace in a cell's files** (section 2.3; section 7 item 7,
   second half): the tools repo commit `5e4f9c0` on the cluster, four requests at a
   time, GPU class and memory, one model alone on its card, the `guided_json` field of
   the no-tools request, "no decoder constraint in any arm", the harness commit. The
   prereg says these are read from the submit output and the job logs and recorded in
   sections 9 and 10. The code only refuses to run without a note for the tools repo.
   Needed to close it: the sbatch would have to write these into `client_settings.json`.
2. **One array job, one window** (section 2.4). The job id of each cell is printed, not
   compared. Needed: the array job id in `client_settings.json` (today it holds one job
   id per cell, and its form for an array task was not checked).
3. **"Every job completes"** (section 7 item 1). Job states are not in the synced files;
   the smoke check says so and asks for the cluster-ops status record.
4. **The audit "for every trial", and the user prompts byte for byte** (section 2.3;
   section 7 items 4 and 5). An audit line carries no trial key and no wording. The
   checks are by count and by set: each task has at least as many lines as rows and
   exactly as many different user texts as rows; every user text of N is also in the
   tools cell; the tools cell holds as many other texts as N has. Not checked: which
   line belongs to which trial, that a trial of k turns has k lines, that the texts N
   and the tools cell share are those of v11 to v13 of the same problem, and that the
   texts equal Part A's (Part A has no audit log). A rebuild of the user texts offline
   with `build_messages` and the ground-truth cache was tried on the control's cell B
   and reproduced 582 of its 600 user-text sha256 per model, so it cannot be a
   registered check as it stands (the 18 misses are probably the simulate prompts of
   the six problems whose run-time plan differs from the cached one; not verified).
   Needed: the trial key in each audit line.
5. **"The tool list is recorded and non-empty"** (section 7 item 6). The files record
   one boolean per request (`has_tools`), which is true exactly when the list sent was
   non-empty. The names of the tools offered are in no file of a cell.
6. **Figures and LaTeX rows of the by-length breakdowns** (section 6 rule 4). The tables
   are in the JSON and markdown output; the figure and `.tex` writers of
   `rq1_control_metrics.py` are not called.
7. **Mean tokens of the final answer in a tools arm** (section 8). The rows hold the sum
   over the turns of the tool loop only; the column reports that sum and says so.
