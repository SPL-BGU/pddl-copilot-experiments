# Traceability map: matched-run prereg to the analysis code (freeze gate 3)

**Freeze candidate. Not frozen.** No hash of this code is recorded as frozen. The
independent review (gate 5) has been run once and its points are applied here; the
owner's open choices come next.

Spec: `development/reference/matched_run_prereg.md`, sections 2 to 8 (the draft of
2026-11-25, with the wording decided the same day on the candidate's spec questions and
on the independent review's seven points).
Code: `tools/reanalysis/matched_run.py` (written `MR:<line>` below; a function is cited by
its name and first line). Functions of the control's frozen analysis are written
`CPF:<name>` (`tools/reanalysis/control_prompt_fix.py`, imported, not edited).
Fixture checks: `tests/test_matched_run.py` (written `T:<test function>`), on the fixture
built by `tests/fixtures/matched_run/build_fixture.py`.
Line numbers are those of the freeze candidate; a re-freeze re-checks them.

Each entry quotes the clause, then names the code or runtime check, then the fixture
check that exercises it. Clauses that are not testable commitments (purpose, order of
human steps, what the paper says, what is recorded by hand) are marked "not code" with
the reason. What has no implementation is collected at the end under **NOT
IMPLEMENTED**. Details the code had to settle are under **Choices made**. **Known
issues** lists what a reviewer will meet outside this code.

Shared mechanics used by many entries:

- every registered constant is a raised check in `check_constants` (MR:222) and
  `check_design` (MR:329), called at import (MR:370) and again in `main` (MR:1731). The
  checks call the control's `_check`, which raises `RegisteredCheckFailed` and is not an
  `assert`, so `python -O` cannot strip it; the frozen `constants.py` also refuses `-O`.
  `check_constants` first calls the control's own `check_constants`. T:test_constants
  flips every constant and every design field and sees the check fire;
  T:test_package_hash checks `-O` is refused.
- every row is read by `CPF:read_folder`, which calls the frozen `schema.parse_row` and
  the frozen `schema._check_completeness`, with a `CellSpec` made by
  `dataclasses.replace` from the rerun's `spec_rerun_c` (N) or `spec_rerun_a` (tools):
  `matched_spec` (MR:396).
- grade fields are read only through `CPF:ok_of` and `CPF:plan_of`; estimator code reads
  `Trial` records (MR:1068) built in `grade_trials` (MR:1087).
- the package hash covers this script, the control's script and every repo file either
  imports (`DEPENDENCIES`, MR:93; `package_sha256`, MR:384). The control's hash machinery
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
`check_constants` (MR:222) against the rerun's `C.PLAIN`, `C.STEERED`, `C.VARIANTS` and
the control's cell B token. Rows are split into arms by wording in `arm_rows` (MR:485).
T:test_constants; T:test_base (the steered arm lists v14 to v16).

> "P and S share one cell folder, as in Part A: the with-tools cell runs the six
> wordings. So each model has two cell folders, and the run has six."

`FOLDERS`, `ARM_FOLDER` (MR:108-109); `matched_spec` (MR:396) gives the tools folder
the six wordings; `load_matched` (MR:439) reads two folders per model.
T:test_constants (the two specs), T:test_base (corpus: 120 and 240 rows).

> "**[Omer, A5]** The no-tools message is the control's cell B. Its sha256 (utf-8) is
> `3dbc1baf…` on solve and `7ccf5d9d…` on simulate"

`N_SYSTEM_SHA256` (MR:113), checked equal to the control's `SYSTEM_SHA256["B"]` and to
the sha256 of the text in `pddl_eval/control_prompts.py` (MR:222). Every audit line of
an N cell is checked by `CPF:check_audit` with cell "B" (called at MR:728).
T:test_refusals ("audit N: wrong system digest", "audit N: not swapped").

> "The registered and reference-removed texts are not run again."

Not code (design). The spec of an N folder names the one token `no-tools-sysformat`.

> "The with-tools system text of arms P and S is fixed by its sha256 (utf-8) as well"
> (the two digests) "Both are derived from `pddl_eval/prompts.py` (the text Part A
> sent). They are the same for plain and steered wordings: the steering sentence is in
> the user message."

`TOOLS_SYSTEM_SHA256` (MR:119), the two literals of the prereg. `check_constants`
(MR:222) recomputes each from `WITH_TOOLS_SYSTEM_BY_TASK` and from what
`build_messages(..., with_tools=True, prompt_style="minimal")` sends for every wording
v11 to v16, so "the same for plain and steered" is a checked fact. Every audit line of
a tools cell is compared with them in `check_audit_tools` (MR:534). T:test_constants,
T:test_refusals ("audit tools: wrong system digest", "the N text in a tools cell",
"byte for byte").

> "Known in advance from the control: under this message Gemma-26B writes its simulate
> answer as one JSON object and breaks the brackets in about one answer in six (52 of
> 300). ... No answer is repaired."

No repair: `grade_trials` (MR:1087) calls only the frozen grader and the two imported
readers. T:test_planted_answers ("an unread final answer is wrong"). The 52 is the
constant `UNREAD_KNOWN_CONTROL` (MR:183); its tripwire is in section 8.

### 2.2 Models, tasks and size

> "Models: `Qwen/Qwen3.5-9B`, `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`,
> `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` ... Folder tags `Qwen3_5_9B`, `gemma4_26b-a4b`,
> `qwen3_6_35b`."

`MODELS`, `MODEL_ORDER` (MR:126-127), checked against the rerun's `C.MODEL_IDS`
(MR:222). The frozen `parse_row` refuses a row whose model id is not the cell's.
Audit lines: `check_audit_tools` (MR:534), `CPF:check_audit`. T:test_constants,
T:test_refusals ("audit tools: another model").

> "Thinking off."

`C.THINK == "off"` (MR:222); the frozen `parse_row` requires `"off"` in every resume
key; `client_settings.json` and every summary: `CPF:check_apparatus` (N),
`check_apparatus_tools` (MR:645).

> "Tasks: solve and simulate."

`TASKS` (MR:128, MR:222); the cell specs register only these two tasks, so the frozen
loader refuses any other. T:test_constants.

> "Per model, task and arm: the 100 problems of the rerun (20 domains, 5 problems each)
> by three wordings = **300 trials**." / "Per cell folder: N 600 rows (300 per task);
> tools 1,200 rows (600 per task, 100 per wording and task)." / "Total: ... **5,400
> trials**."

`REGISTERED` (MR:211) and `check_design` (MR:329): 300, 600, 1,200, 200 per wording, 100
per task and wording, k = 20, 5,400. Enforced on the rows by the frozen
`_check_completeness` through the spec, and again per arm in `analyse` (MR:1314, "300
trials" check on every arm and every earlier cell). "The 100 problems of the rerun":
`check_keys_equal_rerun` (MR:516). T:test_constants (each field), T:test_refusals
("a short tools cell", "a short N cell", "trial keys that differ from the rerun's").

### 2.3 Fixed settings

> "The cluster's `pddl-copilot` checkout stays at `5e4f9c0`." / "the commit of the
> cluster's tools repo. It is read on the cluster before the smoke and before the full
> run, and recorded in section 10 and in section 9. The analysis refuses to run without
> a note that says how it was read"

`TOOLS_REPO_COMMIT` (MR:131). `need_notes` (MR:718) halts the analysis without
`--tools-repo-checked-by-hand NOTE`; the note is written to the output. The smoke check
(MR:781) reports the item as NOT CHECKED and fails without it. T:test_refusals ("item
7: no note on the tools repo"), T:test_smoke ("item 7: the tools repo needs a note"),
T:test_base (the note is recorded).

> "Context window 16,384 tokens. Output cap 8,192 tokens on solve and 6,144 on simulate.
> Temperature 0. ... Answers stored up to 65,536 characters."

Window, temperature: `client_settings.json` and every summary, N by `CPF:check_apparatus`,
tools by `check_apparatus_tools` (MR:645). The frozen loader refuses a row whose clipped
allowance breaks the window and a stored answer longer than 65,536 characters. Output
cap, N rows: `CPF:check_apparatus`. Output cap, tools rows: `check_tool_row_caps`
(MR:623); the cap applies to each turn of the tool loop and `tokens.completion` is the
sum over turns, so the control's rule cannot be used (Choices made 2). That the caps are
the harness's own: `check_summary_run` (MR:676) requires `num_predict`
null and the two tasks of this run in every summary file of an N and of a tools cell
(section 7), and `check_constants` ties the harness's defaults to 8,192 and 6,144.
T:test_refusals (the "apparatus:" cases, with "its own output cap" and the two "summary
of ... task" cases), T:test_cap_units. Run on the real summaries of the control's cell B
in the dry run.

> "vLLM 0.20.2 from the shared `~/vllm.sif`."

`CPF:check_serve_log` on the serve log of the job each cell's `client_settings.json`
names (called at MR:728), or a hand note. T:test_refusals ("serve log shows another
vLLM", "a missing serve log", "item 7 by hand").

> "The with-tools system text, byte for byte as in Part A (section 2.1). The user
> prompts v11 to v16 are assured in four ways. The prompt templates and the code that
> fills them are files of the package hash. The trial keys equal Part A's. The texts of
> v11 to v13 are the same in the N cell and the tools cell of a model (section 7, item
> 5). And the user texts of the N cell are compared by sha256 with those of the
> control's cell B ... The count of texts that differ is reported beside K1 and does not
> halt."

System text: section 2.1 above. Package hash: `pddl_eval/prompts.py`,
`pddl_eval/runner.py` and `pddl_eval/domains.py` are in `DEPENDENCIES` (MR:93;
T:test_package_hash). Trial keys: `check_keys_equal_rerun` (MR:516). N against tools:
`check_users` (MR:590). N against the control's cell B: `compare_user_texts`
(MR:696), called in `main` in fixture and live mode, written to
`audit.user_texts_vs_control` and printed under the K table; a difference is counted and
never halts, a missing audit log of the control halts. T:test_base (one differing text
in Qwen3.6-35B simulate: 59 shared, 1 and 1; 60, 0, 0 elsewhere), T:test_refusals ("the
control's cell B has no audit log").

> "These settings leave no trace in a cell's files. Each is recorded by hand in sections
> 9 and 10, from the submit output and the job logs" (four requests at a time; the GPU
> class and the memory; the `guided_json` field of the no-tools request and no decoder
> constraint; the harness commit; one array job; every job completed).

Not code, by this clause. The job id each cell's `client_settings.json` names is
written to the output (`audit.settings`, MR:728) and is not compared.

> "The harness: `main` at the commit recorded in section 9. ... No file under the frozen
> hashes `822aace9…` or `825dab63…` changes."

`RERUN_PACKAGE`, `CONTROL_PACKAGE` (MR:139-148); live mode halts when either package
hash differs (`load_earlier_live`, MR:944, and `rq1_metrics.load_rerun_cells`).
T:test_package_hash (both hashes unchanged).

### 2.4 One job, one window

> "All six cells are submitted in **one array job** ... Job ids and dates are recorded in
> section 9."

Not code (recorded by hand, section 2.3).

> "Run tag `matched-run`; folders `slurm_vllm_<model tag>_off_<cell token>_matched-run`,
> synced to `results/matched-run/`. Smoke tag `matched-run-smoke`."

`RUN_TAG`, `SMOKE_TAG` (MR:136-137); `folder_name` (MR:392); live root
`args.results / RUN_TAG` (MR:1731). T:test_constants (folder names).

### 2.5 A new corpus

> "The rows of this run are never pooled with the rerun, the control, the main sweep or
> the smoke. No cell of this run stands in for a cell of a filed readout."

The matched run is read only from folders named with the run tag (or the r2 tag); a
smoke folder carries another name and is not found. The earlier runs are read into
`Earlier` (MR:910) and meet this run only in K1 to K3. T:test_smoke ("the analysis does
not read smoke folders"). The dry run goes the other way (old rows fill the arms) and
says so in its mode, file name and first line (MR:1731, MR:1508).

---

## Section 3. The grade

> "**One registered grade: delivered right.** It is applied in the same way to the three
> arms."

`grade_trials` (MR:1087), one function for every row of every arm and of the earlier
runs. `REGISTERED_GRADE` (MR:159). T:test_planted_answers ("caps_block in a tools row:
the same rule in every arm").

> "**solve.** The delivered plan is the plan in the last closed code block of the answer
> when that block holds a plan; otherwise the plan the rerun's grader reads. The plan
> must pass the validator. ... (`block_plan`, imported unchanged)"

MR:1087: `RG.block_plan(r.response)`, else `CPF:plan_of` of the frozen `grade.grade`
result; the verdict comes from the one injected route. T:test_planted_answers
(json_block, right_to_wrong, wrong_lines, prose).

> "**simulate.** The trace the rerun's grader reads must equal the answer key; a trace
> written one JSON object per line also counts when it equals the answer key exactly
> (`line_reader_exact`, imported unchanged)."

MR:1087 takes the `second` value of `CPF:second_reading`, which is the frozen grade or
`PILOT.line_reader_exact`. T:test_planted_answers (trace, per_line, per_line_wrong).

> "**The simulate answer key [Omer, ISS-029].** The key is the cached reference trace
> ... on 6 of the 100 problems (barman p01 to p05, gripper p03) the plan placed in the
> prompt can differ from the plan of the cached key. ... 18 of the 300 simulate trials
> of an arm ... One descriptive count is registered per model and arm: the simulate
> trials on those six problems, and how many of them are right."

The key: the frozen grader and `line_reader_exact` both compare with
`oracle_canon_for(gt_cache, ...)`; the cache must have the pinned canonical hash
(`rq1_metrics.load_rerun_cells`). The six problems: `KEY_PLAN_DIFFERS` (MR:154),
`KEY_PLAN_DIFFERS_TRIALS` (MR:157), both in `check_constants`. The
count: `key_plan_differs` in `analyse` (MR:1314), which on the registered design raises
unless every arm has 18 such trials; printed as its own table. The fixture names its
own two problems in `design.json`. T:test_base (5 trials per arm; 4 right where a
planted wrong trace falls on them; d20/p01 is not counted), T:test_constants. Dry run:
18 trials per arm, the list equal to the problems the by-length rule leaves out.

> "**Exception rows.** A trial on which the harness raised is wrong under the registered
> grade, whatever answer it stored, as under the rerun's grader."

`grade_trials` (MR:1087): `if r.is_exception: registered = False`. T:test_planted_answers
(a scoring-exception row with a right plan in a block, and one with a right per-line
trace: registered wrong; a client exception: wrong under every grade), T:test_base
(Qwen3.5-9B solve N: 40 registered, 40 frozen, 41 not lower-cased).

> "pddl-pyvalidator **0.1.5** ... in process, through the route of the control."

`CPF:live_route`; `validator_env` (MR:1900) calls `CPF:check_validator_env` (release
0.1.5, server file unedited and equal by sha256 to the filed re-grade's). `PYVALIDATOR`
(MR:150). Run in the dry run on this machine; not reachable from the fixture (the
control's T:test_validator_units covers `check_validator_env`).

> "So the plan is sent to the validator in lower case, in every arm. Every plan is
> lower-cased, not only a plan in which a capital is seen. The analysis counts the
> trials where this differs from the control's case-folded column".

MR:1087: `verdict(r.domain, r.problem, RG.lower(plan))`, always. The counter is
`registered_differs_from_case_folded` in every rate row (MR:1314), printed as a column
of both rate tables. T:test_planted_answers ("caps_block: right only in lower case",
where the route records that it was sent the lower-case plan; "caps_json": a plan the
frozen reader took, with no code block, is lower-cased too), T:test_base (Qwen3.6-35B
solve S: 60 registered, 40 under both descriptive grades; the counter is 1 for the one
scoring-exception row and 0 elsewhere).

> "The analysis halts on any other release, on a verdict that is not a plain true or
> false, and when the route does not return the stored verdict for the rerun's plans (the
> control's check)."

Release: `validator_env` (MR:1900). Verdict: `CPF:validator_verdict` and `CPF:Verdicts`.
Stored verdicts: `CPF:check_route` on the solve plans of Part C, Part A plain and Part A
steered, before any new plan is validated (MR:1314). T:test_refusals ("the route
disagrees with a stored verdict").

> "**Reported beside it, descriptive, for the supplement only:** the rerun's frozen
> grade, and the registered grade without the lower-casing (the control's second reading
> as filed, which still reads the stored answer of an exception row). ... No reading of
> section 5 uses them."

`DESCRIPTIVE_GRADES` (MR:160); `Trial.frozen`, `Trial.second` (MR:1068) from
`CPF:grade_rows`; rates and contrasts under them are computed but carry no label
(`family`, MR:1377). T:test_base (RATES, DESCRIPTIVE, "a descriptive grade carries no
label").

> "**What the grade does not do.** It does not repair a broken JSON answer, read a plan
> from prose outside a code block where the rerun's grader would not, or use the tool's
> output in place of the final answer."

By construction of MR:1087 (no other reader is called; tool calls are not read).
T:test_planted_answers (unread_sim, prose), T:test_base (Gemma simulate S: tool right,
answer wrong, graded wrong).

---

## Section 4. Contrasts and statistics

> "All contrasts are paired on the trial (task, domain, problem, plan label, wording),
> per model and task, in points. A steered wording is paired with its plain wording on
> the same problem (v14 with v11, v15 with v12, v16 with v13), as in the rerun."

`canon` (MR:494), `STEER_OFFSET` (MR:166, checked against `C.STEER_OFFSET`);
`CPF:paired` over the canonical keys in `family` (MR:1377), which raises unless there
are 300 pairs and none unpaired. T:test_planted_answers (canon), T:test_base (M2 of
Qwen3.5-9B simulate: 0 gained, 0 lost; the pairing trap).

> M1 = P minus N (primary), M2 = S minus N, M3 = S minus P, six each.

`CONTRASTS` (MR:162), `N_CONTRASTS` (MR:164); MR:1314. T:test_base (REGISTERED, 18
contrasts under three grades), T:test_constants.

> K1 = N minus the control's cell B, K2 = P minus Part A plain, K3 = S minus Part A
> steered; "Each crosses two runs, is printed with the dates of both, and is no gate on
> anything".

`CONTINUITY` (MR:163), `N_CONTINUITY` (MR:165); `q2_reading` (MR:1166) and the K table
of `render` (MR:1508) print `EARLIER_DATES` and `--run-dates` (required). No check halts
on a K label. T:test_base (K rows, "carries both dates"), T:test_refusals ("no dates
for the run").

> "The rows of the control and of Part A are graded again with the registered grade of
> section 3. Their frozen grades must reproduce the filed readouts, or the analysis
> halts."

Graded again: MR:1314 (`earlier`). Filed readouts: `check_filed_readout` (MR:1007, the
rerun's E1 counts, plain and steered), `check_filed_regrade` (MR:1025, the filed layout
re-grade: frozen, second reading, case folded), `check_filed_control` (MR:1046, the
control's filed cell B counts). In live mode `rq1_metrics.load_rerun_cells` also halts
unless the rerun's package, ground truth and E1/E2 reproduce. T:test_refusals (the three
"does not reproduce" cases and "the steered arm is missing").

> "**Intervals.** 95% percentile intervals from the frozen domain-cluster bootstrap of
> the rerun (`tools.delivered_rerun.stats.cluster_bootstrap`): 20 domains, 10,000
> resamples, seed 20261002. Rates carry the same interval."

`CPF:boot` (k and level asserted) through `CPF:paired` and `CPF:rate`; `LEVEL`,
`B_BOOT`, `SEED` (MR:168-170) checked equal to the rerun's constants. T:test_base (k =
20 on every contrast and rate; the hand-computed intervals).

> "M1 and M2: **tools ahead** when the interval is above 0, **no tools ahead** when it is
> below 0, **no difference shown** otherwise."

`label_of` (MR:1142) calls `CPF:c4_label`. T:test_labels, T:test_base.

> "M3: **naming the tool helps** / **hurts** / **no difference shown**, by the same rule."

`m3_label` (MR:1130). T:test_labels, T:test_base.

> "K1 to K3, with the margin of 5 points of the control: **criterion met** when the whole
> interval lies inside [−5, +5]; **a difference is shown** when it excludes 0;
> **unresolved** when neither. ... A check can be "criterion met" and "a difference is
> shown" at once ...; both labels are then given."

`label_of` (MR:1142) calls `CPF:contrast_label` (endpoints included; both labels joined
when both hold). `MARGIN` (MR:167). T:test_labels ("K excludes 0 and inside the margin:
both labels"), T:test_base ("endpoint exactly 5.0").

> "**Multiplicity.** ... an exact sign-flip p-value over the 20 domains, Holm-adjusted
> across the six contrasts of the same name. A difference whose interval excludes 0 and
> whose adjusted p-value is 0.05 or more carries the words "(not after Holm)". This
> applies to K1 to K3 as well, with a family of six per name."

`ST.signflip_exact_p` in `CPF:paired`; `ST.holm(..., HOLM_FAMILY)` per name in `family`
(MR:1377), called for M1 to M3 and for K1 to K3 alike. T:test_base (p and Holm values of
all 36 registered rows; K1 and K3 of Qwen3.5-9B simulate carry "(not after Holm)"),
T:test_labels.

> "The number of contrasts (18, and 18 continuity checks) is stated with every table."

The `common` sentence of `render` (MR:1508). T:test_base ("states the number of
contrasts with the tables").

---

## Section 5. Registered readings

> "Per model and task. No reading pools models or tasks."

MR:1314 builds one reading per model and task; nothing pools. T:test_base.

> "**Q1.** ... The label of M1 is the answer the paper gives for "tools offered". The
> label of M2 is given beside it for "tools offered and named". Where the two differ,
> both are stated, and M3 says what naming the tool added. Two labels differ when they
> still differ once the words "(not after Holm)" are removed."

`q1_reading` (MR:1153), `base_label` (MR:1126). T:test_base (Q1 labels, differ,
sentence), T:test_labels ("same answer with and without the Holm words").

> "**Q2.** ... Where a check meets the criterion, the supplement says this run reproduces
> the earlier one for that model, task and arm within the margin, and gives the
> estimate. This holds too when the check also carries "a difference is shown". Where
> the criterion is not met, the supplement says so and gives the estimate."

`q2_reading` (MR:1166): decided by `CPF:met` alone; the sentence carries the full label
and the estimate with its interval. T:test_base ("within the margin (criterion met,
+1.7 [+0.0, +5.0])"; the not-met sentence), T:test_labels.

> "Either way the body quotes this run." / "Readings that would be wrong, named in
> advance" / "What is expected, stated so that it cannot be claimed as a discovery
> later."

Not code (what the paper may say). The labels above are the only readings the code
prints; it prints no pooled figure.

---

## Section 6. The reporting rule

> Rule 1: "the rate of each arm under the registered grade, and M1, M2 and M3 with their
> intervals and labels, whatever they show."

`rates` and `contrasts` of `analyse` (MR:1314); first two tables of `render` (MR:1508).

> Rule 2 (the earlier figures move to the supplement with the continuity table and the
> frozen-grade columns).

The K table, the descriptive-grade tables and "the earlier runs, graded again" table of
`render` (MR:1508). Where the paper puts them: not code.

> Rule 3: "The same measures (which tool was called; tool right and final answer wrong)
> are computed on this run's tool rows with the definitions of
> `tools/reanalysis/rq23_metrics.py` ... In "final answer wrong", right and wrong mean
> this run's registered grade (section 3). The version under the rerun's frozen grade is
> printed beside it."

Which tool: `rq2_cells` (MR:1199) calls `rq23_metrics.row2` and `rq23_metrics.rq2`
unchanged and repeats the self-check of `rq2_rows`. Tool right, answer wrong:
`rq3_cells` (MR:1225): `n_lost` and `lost` under the registered grade; `n_lost_frozen`,
`lost_frozen` and `why_frozen` with the categories of the frozen `e4.classify`
(Choices made 3); a trial that function refuses is counted in `not_classified`, printed,
and does not halt (section 8). T:test_base (tool choice classes; Gemma solve P: 0 of 60
registered, 20 of 60 frozen; Gemma simulate S: 4 of 60 under both, 3 refused or clipped
and 1 wrong facts; Qwen3.6-35B solve S: 0 and 20), T:test_units ("a refused
classification is counted"). The dry run reproduces the rerun readout's E4 counts and
categories on all 12 cells (frozen-grade version), with none unclassified.

> Rule 4: "computed on this run with the bins and definitions of
> `tools/reanalysis/rq1_control_metrics.py`. A trial counts as right under this run's
> registered grade. They are descriptive. Tables only: the figures and the LaTeX rows of
> that script are not part of this registration. The problems left out of the by-length
> simulate tables are chosen by the rule of that script from this run's rows ..., and
> the list is printed."

`breakdowns` (MR:1270): `rq1_metrics.problem_facts`, `metric3`, and `metric2` with
`rq1_control_metrics.best_state_score_second` put in place for that call (as that
script does); each record's `ok` is `Trial.registered`. No figure or `.tex` writer is
called. The problems left out are `rq1_metrics.problem_facts`'s `sim_plan_differs`,
computed from this run's own records; the list is `simulate_left_out` and is printed
above the table. T:test_base (none left out; by reference length, with Gemma P at 100
under the registered grade; exact, strict and lenient state scores; a per-line trace scores all its states).
On the dry run the tables equal the filed `rq1_control_metrics.json` on all 45 cells of
each (lower-casing changed no trial there).

> Rule 5: "No paper text is part of this registration."

Not code.

---

## Section 7. Execution

> "Order." / "Every SSH or SLURM action needs Omer's explicit go-ahead".

Not code.

> "**Smoke.** ... `--partial 1` (the first problem of every domain: 120 rows in each N
> folder, 240 in each tools folder), run tag `matched-run-smoke`, all six cells. Never
> pooled."

`SMOKE` (MR:213), `check_smoke_design` (MR:354), `smoke_check` (MR:781). T:test_smoke,
T:test_constants.

> Item 1: "every job completes and every cell folder holds its rows"

Rows: MR:781 (`IncompleteCell`). "Every job completes" is recorded by hand (section
2.3); the smoke check prints that it cannot see job states. T:test_smoke ("a short tools
folder", "a missing folder").

> Item 2: "the frozen loader reads every row; no exception or infrastructure-failure
> row; no row cut by storage; no half-written line"

MR:781. T:test_smoke ("an exception row", "a half-written line").

> Item 3: "in every N cell at least 95% of the stored answers are non-empty; in every
> tools cell at least 95% of the answers of trials whose final turn was not refused or
> clipped for a full context window are non-empty. A final turn is refused or clipped by
> the two rules of the rerun's category ... (`REFUSED_OR_CLIPPED_FINAL` in
> `tools/delivered_rerun/e4.py`): the row's `no_room` is set, or its last turn ran with a
> clipped allowance (`tokens.ctx_clip_last_turn_max_tokens`) and stopped at it
> (`done_reason` "length")."

`window_full` (MR:758): the two conditions of `e4.classify`, written out on the typed
row because `classify` itself accepts only tool-verified rows that are graded wrong.
`nonempty_enough` (MR:770), `SMOKE_NONEMPTY` (MR:176), called in `smoke_check`
(MR:781). So that the item cannot pass on nothing, a tools cell also needs at least one
trial per task whose final turn was not refused or clipped (Choices made 6). T:test_smoke
(N: 114 of 120 passes, 113 fails; tools: 227 of 240 fails; 73 empty answers of refused,
then of clipped, final turns pass; a tools cell with no simulate trial left fails;
`window_full` and the per-folder rule on single rows). Checked outside the fixture on Part A: the rule passes
on the smoke subset of all three models (156 to 166 trials left, all non-empty).

> Item 4: "every audit line of a cell carries the registered system sha256 of its task
> (N: the format-stated text, marked swapped; tools: the with-tools text of section 2.1,
> marked not swapped); and, per task, the log has at least as many lines as the cell has
> rows and exactly as many different first-user texts as rows (an N cell has three
> wordings per task, a tools cell six)"

N: `CPF:check_audit` with cell "B". Tools: `check_audit_tools` (MR:534). Both also
compare the stored text byte for byte where a line carries it, and the model id.
T:test_base (476, 480 and 460 lines for 240 trials), T:test_refusals ("audit N: wrong
system digest", "audit N: not swapped", "audit tools: wrong system digest", "the N text
in a tools cell", "byte for byte", "marked swapped", "wrong mode", "a trial with no line
of its own", "fewer lines than rows", "a missing audit file"), T:test_smoke.

> Item 5: "the N and tools cells of a model hold the same problems; the set of user-text
> sha256 of v11 to v13 is the same in the N cell and in the tools cell (every user text
> of the N cell is also in the tools cell, and the tools cell holds as many other texts
> as the N cell has texts: the steered wordings)"

`check_same_problems` (MR:505); `check_users` (MR:590). T:test_refusals ("N and tools
cells do not hold the same problems", "steered wordings not on the plain wordings'
problems", "a user message of N is not sent in the tools cell"), T:test_base (120 shared
and 120 tools-only texts per model), T:test_smoke.

> Item 6: "every request of a tools cell is logged with tools present, and no request of
> an N cell is"

`has_tools` true on every audit line of a tools cell (MR:534) and false on every line
of an N cell (`CPF:check_audit`). Beside it: the rows' `with_tools` by the frozen
loader, and `client_settings.json` by `check_settings_tools` (MR:606) and
`CPF:check_settings`. T:test_refusals ("audit tools: a request without tools", "audit
N: a line with tools", the settings cases), T:test_smoke.

> Item 7: "the serve log shows vLLM 0.20.2 and no other version; the cluster's tools
> repo is at `5e4f9c0` (read on the cluster and recorded by hand, section 2.3)."

Serve log: `CPF:check_serve_log`, or a hand note. Tools repo: the note `need_notes`
(MR:718) requires. T:test_smoke, T:test_refusals.

> "The check prints these items and no success rate, no failure-reason count, no
> tool-call count and no answer text."

MR:781 prints item lines, failure messages of the checks, row counts and re-sent
request counts only. T:test_smoke ("prints no rate, reason, tool-call count or answer
text").

> "**Items 4 to 7 are preconditions of the analysis** on the full run, together with the
> apparatus checks of the control (window, caps, temperature, thinking, model, storage
> rule). Every summary file must also name the two tasks of this run and no output cap
> of its own ... Items 1 and 2 are replaced on the full run by the completeness rule,
> the VOID rule and the storage rule below. Item 3 is for the smoke only."

`audit_matched` (MR:728), before any answer is graded: items 4 to 7, `CPF:check_apparatus`
(N), `check_apparatus_tools` (MR:645), and `check_summary_run`
(MR:676) for both folders. Items 1 and 2: `matched_spec` with the
frozen completeness check, `check_void`, and the storage rule of `CPF:read_folder`
(entries below). Item 3: only in `smoke_check`. T:test_refusals; T:test_base (the base
fixture is analysed with an exception row, a storage-cut row at the cap and a torn
line, which the smoke's item 2 would fail).

> "During the run. Monitoring reads row counts and job states only."

Not code.

> "**Stop rules.** A cell folder is VOID if more than 1% of its rows are exception or
> infrastructure-failure rows (the rerun's definition). When a cell is VOID, **both cells
> of that model are run again from scratch, together**, under the run tag
> `matched-run-r2`".

`check_void` (MR:428), `VOID_FRAC` (MR:177); `first_run_void` (MR:452) and
`resolve_tags` (MR:475): the r2 folders of a model are read only after the analysis has
itself found a first-run cell of that model VOID. T:test_refusals (2 of 120 and 3 of 240
are VOID), T:test_r2.

> "**Completeness.** N: 600 rows, 300 per task, 200 per wording. Tools: 1,200 rows, 600
> per task, 200 per wording. A short cell is resumed, not analysed."

`matched_spec` (MR:396) with the frozen `_check_completeness` (rows, rows per wording,
rows per task and wording, 20 domains; 300 and 600 per task follow). T:test_refusals,
T:test_constants.

> "The trial keys of each arm must equal those of the rerun for that model and task; a
> difference halts the analysis. The unpaired count is therefore zero, and it is
> printed."

`check_keys_equal_rerun` (MR:516); `family` (MR:1377) raises unless unpaired is 0; the
M table prints the column. T:test_refusals, T:test_base.

> "**Exception rows at or under 1%** stay in the denominator and are wrong under every
> grade the readings use (section 3)."

The frozen grader gives them the reason "exception" (wrong); `grade_trials` (MR:1087)
sets the registered grade to wrong. T:test_base (1 of 120, a scoring-exception row with
a readable right answer), T:test_refusals (2 of 240 kept, both wrong).

> "**Rows cut by storage, duplicate keys, half-written lines:** the control's rules."

`CPF:read_folder`. T:test_refusals ("duplicate trial key", "a storage-cut row that did
not stop at the output cap"), T:test_base (in a tools cell, in analysis mode: one answer
cut by storage at the output cap accepted and counted; one half-written line counted
and skipped).

> "**The analysis does not read a row of the full run** unless it is started with the
> package hash of section 9."

MR:1852 (`main`): the first statement of live mode. T:test_live_gate (no hash, a wrong
hash, the control's hash).

---

## Section 8. Secondary and tripwires

> "Per model, task and arm, with counts: right answers by wording; the layout of the
> answer (the control's categories); answers that stopped at the output cap (the answer
> ended at the cap and its final turn was not refused or clipped); trials whose final
> turn was refused or clipped because the prompt and the tool output filled the window
> (the rule of section 7, item 3), counted on their own; mean output tokens (in a tools
> arm, summed over the turns of a trial; the rows hold no per-turn count); the rerun's
> failure reason for each trial that is wrong under the registered grade; the
> frozen-grade and not-lower-cased columns of section 3, and beside them the count of
> trials where the registered grade differs from the control's case-folded column; the
> count of section 3 for the six simulate problems; the Holm-adjusted p-values; the
> measures of section 6, rules 3 and 4. In the table "tool right and final answer
> wrong", a trial that the rerun's rules cannot classify is counted as "not classified"
> and the count is printed."

`secondary_tables` (MR:1483): `by_wording`, `layout` (`CPF:second_reading`'s),
`at_output_cap` (`Trial.at_cap`: `done_reason` "length" and not `window_full`),
`window_full` (`Trial.window_full`, the function at MR:758), `mean_output_tokens`
(`tokens.completion`), `failure_reasons` (over `registered is False`). The grade columns
and the case-fold counter are in `rates`; the six-problem count in `key_plan_differs`;
the Holm p in `contrasts`; "not classified" in `rq3_cells` (MR:1225). T:test_base
(layout; failure reasons; right by wording 19, 2, 19; Gemma simulate S: 1 at the cap
and 3 window-full; Qwen3.5-9B simulate S: 1 and 0; 5 in all; the markdown columns),
T:test_units.

> "all on the registered grade: the same count of right answers in all nine model-by-arm
> cells of a task"

T1 (MR:1413), over the nine cells of this run; every tripwire reads `Trial.registered`
or a K estimate under the registered grade. T:test_tripwires.

> "an arm in which no answer at all is read on a task (no trial of the arm on that task
> has an answer read by the rerun's grader, a plan block, or a trace written one object
> per line)"

T2 (MR:1413), `Trial.read` set in `grade_trials` (MR:1087): the frozen reason is not one
of the control's unreadable reasons, or `block_plan` finds a plan block (solve), or
`line_reader_steps` finds a trace (simulate). T:test_tripwires (solve all prose in one
arm fires for that arm and task only).

> "an arm whose rate differs by more than 20 points from its continuity partner (K1 to
> K3)"

T3 (MR:1413), `TRIPWIRE_POINTS` (MR:179). T:test_tripwires (fires at +33.3; released
with a written note).

> "a tools arm (model, task, P or S) in which no trial called a tool"

T4 (MR:1413), id `T4:<model>:<arm>:<task>`, `Trial.invoked`. T:test_tripwires (fires
for Qwen3.6-35B solve P alone; an arm with one wording of three without a call does
not fire).

> "and, **for arm N**, more than 5% unread final answers (the control's definition) for a
> model and task. One case is known in advance and has its own threshold: Gemma-26B on
> simulate, where the control counted 52 of 300 and audited them; there the tripwire
> fires above 90 of 300."

T5 (MR:1413), `CPF:unread_final` through `CPF:grade_rows`; `unread_limit` (MR:362),
`UNREAD_FRAC`, `UNREAD_KNOWN*` (MR:180-183). T:test_tripwires (3 of 60 stays, 4 fires;
arm P is not guarded; Gemma simulate 18 of 60 stays, 19 fires; 90 and 15 on the
registered design).

> "**Tripwires that halt the readout until audited**"

MR:1443: a fired tripwire halts unless `--audited-tripwires` and `--audit-notes` release
it with a written note, which is printed. T:test_tripwires.

---

## Choices made (details the spec does not fix)

1. **Item 7 needs two pieces of evidence.** The vLLM version (serve logs or a note) and
   the tools repo commit (a note) are asked for separately.
2. **Output cap in a tools row.** Three checks replace the control's rule: the sum of
   output tokens is at most the cap times the number of turns; a one-turn trial follows
   the control's rule; a trial that stopped at the cap with no clipped and no refused
   turn used at least the cap in all. All 3,600 solve and simulate rows of Part A pass
   (run in the dry run). The check cannot see the tokens of one turn.
3. **`rq3_rerun` and `e4_cell` are not called.** `rq3_rerun` loops over the rerun's five
   tasks and checks the rerun's readout. `e4_cell` stops at the first trial the
   classifier refuses. Their lines are written out in `rq3_cells` around the frozen
   `e4.classify`. The categories (`why_frozen`) describe the trials that are wrong under
   the frozen grade; the registered-grade count has no categories.
4. **Dates.** The dates of Part A and of the control are the constants the prereg's
   disclosure paragraph gives; the dates of this run come from `--run-dates`.
5. **The dry run does not halt on a tripwire** and takes no audit notes; it lists what
   fired. It does not compare user texts with the control (its arm N is the control).
6. **Smoke item 3 cannot pass on nothing.** A tools cell with no trial left on a task
   after the window-full trials are set aside fails the item.
7. **The fixture names its own "six problems".** The registered list holds real domain
   names; fixture mode reads two fixture problems from `design.json` instead.
8. **A missing audit log of the control's cell B halts.** Only a difference in the user
   texts is "reported, not halting".

---

## NOT IMPLEMENTED

Nothing. Every testable clause of sections 2 to 8 has a code line above.

What the earlier versions of this map listed here is now either reworded in the prereg
to what the files allow (section 2.3 user prompts; section 7 items 3 to 6; section 8
tokens; section 6 rule 4 tables only) or named there as recorded by hand (section 2.3
list). One limit stays and is stated in the prereg: Part A has no audit log, so its user
texts are not compared directly. An offline rebuild of the user texts with
`build_messages` and the ground-truth cache reproduced 582 of the 600 user-text sha256
of the control's cell B per model; the 18 misses fit the 18 simulate prompts of the six
problems of section 3 (not verified text by text).

---

## Known issues (outside this code)

- **The control's fixture has no serve logs in git.** `.gitignore` holds `*.log`, so
  `tests/fixtures/control_prompt_fix/serve_logs/*.log` were never committed. On a clean
  checkout `tests/test_control_prompt_fix.py` fails until that fixture is rebuilt
  (`python tests/fixtures/control_prompt_fix/build_fixture.py`, which rewrites the
  tracked files byte for byte and adds the ignored logs). The control's tests and
  fixture are not touched here. This fixture's serve logs were added with `git add -f`.
- **`test_base` of the control under pytest.** It takes a `res` argument that is no
  pytest fixture, so `pytest tests/test_control_prompt_fix.py` reports one error; the
  standalone runner (`python tests/test_control_prompt_fix.py`) passes 441 of 441.
- **`pddl_eval/vllm_client.py` is outside the package hash.** Its sha256 is recorded in
  section 9 of the prereg; the audit checks encode the shape of the lines it writes.
- **Not run against a real tools-cell audit log.** None exists. The shape checked
  (one line per request; mode "registered"; not swapped; tools present) is read from
  `pddl_eval/vllm_client.py` and from the submit-script commit `2522786`. The smoke is
  its first contact with real files.
