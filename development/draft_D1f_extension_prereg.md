# DRAFT: Pre-registration of the extension (Study 2 part 2), plan step D1f

> **Status: DRAFT for Omer's read, 2026-11-09. Nothing here is frozen.** No trial of
> the extension exists. When Omer has answered the `> ANSWER:` slots, the document
> moves to `development/reference/extension_prereg.md` and is frozen **in three stages**
> (wave 1, wave 2, frontier), each stage after `/freeze-protocol` (gates 1 to 5, §11) and
> before that stage's first trial. A later stage may be edited until its own freeze; a
> frozen stage is changed only by a declared deviation (§12).
>
> **E1 is OPEN.** This prereg names endpoints and readings. It does not decide the
> paper's research questions, and nothing in it removes RQ1 to RQ6 or the scorecard.
> Each reading says which RQ framing it serves under both options of
> `draft_E1_research_questions.md` only where that is unambiguous.
>
> Slots marked **[FROM ITEM 9]** are filled from the PR of handoff item 9 (D5b ground
> truth), running when this draft was written. The ISS-028 and ISS-029 rules follow PR
> #136's recommendations and are checked against it once it merges.

Sources: `weakness_action_plan.md` §4 D (D1 to D5), `handoff_20261109.md` §2 decisions 1
to 13 and §4 item 10, `STATUS.md` "Decided 2026-11-09", `reference/d1_smokes_20261027.md`,
`reference/d1b_harder_items.md`, `reference/delivered_rerun_prereg.md` (the model for this
document), `NUMBERS.md` T8c (35B call flips), `OPEN_ISSUES.md` ISS-027 to ISS-030. Every
figure quoted below is copied from `NUMBERS.md` or from the record it names; none is new.

---

## 0. Disclosure of prior data contact

No extension row exists. What we already know and cannot un-know, and which shaped the
readings below:

- **Study 2 part 1 (the delivered rerun, frozen readout 2026-10-09)** in full: delivered,
  tool-verified and calling rates for the three headline models, thinking off; the Gemma
  neutral 2 x 2 on validate_plan; Part C unaided.
- **The 35B call flips (T8c):** between the main sweep and the rerun, the 35B plain arm
  changed call state on 29.3% of solve trials, 24.0% of simulate and 13.2% of
  validate_plan; the 9B and Gemma stayed at or below 3.3% in every cell. Prompt tokens
  were equal on all 2,955 single-turn pairs. The 35B calling rate is quoted as both runs
  (solve plain 68.0 and 82.7).
- **D1 smokes (smoke scale, not results):** the four new families extract tool calls;
  gpt-oss-20b skips the tool often on validate_plan (0.10 in a 20-trial smoke); 32K and
  64K windows cut empty final answers steeply with tool-verified flat; the
  `structured_outputs` JSON constraint binds and moves the score in both directions.
- **ISS-027 to ISS-030** (grading and storage faults found 2026-11-09) and their post hoc
  counts.
- **The D5a pilot** (PR #131, $1.69): thinking-token counts and the answer-parse rate on
  20 keys per arm. Plan success was not computed (§9.4).
- **D5b ground truth** (item 9): the share of the new IPC 2023 problems the planner
  solves at 120 s and 1800 s. **[FROM ITEM 9]**
- Frontier Study 1 cells (thinking off), the contamination probe, the budget probe.

---

## 1. Purpose

Study 2 part 1 measured the delivered answer exactly for three models, thinking off, on
one item set. The extension asks whether its findings hold:

1. **in other model families** (the calling finding was one family-pair, C3 and C14);
2. **on items the models cannot judge at a glance** (new item kinds, C11; whether they are
   harder is itself measured, §6 R6);
3. **with more context room** (the delivery gate, C5);
4. **under a format constraint** on the unaided side (C6);
5. **with reasoning on** (C18; Gemma's calling 21% → 0.6% with thinking on);
6. **on PlanBench with open models** (C15);
7. **for frontier models with thinking on, on larger problems, and under Corrêa et al.'s
   own prompt** (D5a to D5e, the answer to arXiv:2511.09378).

It is one Study 2: the rerun's setup plus additive changes only (§2.3).

---

## 2. Setup common to every cell

### 2.1 Harness and serving

- Harness: tag `delivered-rerun-harness` plus additive changes only (new model entries,
  new item trees, new prompt styles, opt-in flags). The exact commit of each stage is
  recorded in its freeze record (§11). `run_experiment.py` keeps its frozen hash.
- vLLM 0.20.2 (`~/vllm.sif`); serving version read from each serve log's banner and
  recorded per job (`probe_serving_env.sh`).
- Temperature, seed, budgets, prompt variants (v11 to v13 plain, v14 to v16 steered),
  full storage (65,536 characters): as the rerun. Context 16K unless the cell says
  otherwise.
- Per-model tool and reasoning parsers from `lib/defaults.sh` (the one source).
  **Gemma in wave 2 runs with `REASONING_PARSER=none`**, as in Study 1 (decision 6); its
  reasoning stays inside `response`.

### 2.2 Grading

- The rerun's delivered grader and oracle, **with `pddl-pyvalidator` 0.1.6** (the ISS-027
  case fix, decision 13). The installed version is read from the plugin venv on the
  cluster before the first trial and recorded (handoff item 11; B3 Q6).
- **Anchor slice graded twice** (§4): with 0.1.6 and with the rerun's validator version,
  so drift is never confounded with the grader change.
- **ISS-028 extractor rule (solve)** (PR #136's recommendation, handoff §6 decision 10): a
  goal list after a correct plan does not fail the answer. The extractor **reads up to the
  last action** and ignores trailing goal facts. Real copying errors (record: 5 of the
  rerun's 38 wrong-facts solve rows) stay wrong. The rule is applied to extension rows
  and, post hoc and labelled, to the rerun rows they are compared with, so both sides of
  a contrast use one rule. The exact rule text is copied from `iss028_goal_trailers.py`
  at the freeze. **[CHECK against #136 once merged]**
- **ISS-029 plan source (simulate)** (PR #136's recommendation, handoff §6 decision 12):
  the simulate prompt is **built from the same cached plan the grader uses**
  (`results/derived/gt_cache.json`, hash recorded at the freeze), so prompt and grader
  cannot disagree (in the rerun they disagreed on 6 of 100 problems). The freeze gate
  (§11, gate 4) checks on a fixture that the plan in a built prompt equals the cached
  plan for every simulate item.
- Frozen corpora (`sweep5v2-live`, `sweep6-live`, `delivered-rerun`) are only read. Any
  rerun figure regraded under 0.1.6 or the ISS-028 rule is reported beside the frozen
  figure, labelled post hoc.

### 2.3 Apparatus deltas against the rerun (declared because they change what is
generated or graded)

| # | delta | where | effect |
|---|---|---|---|
| 1 | validator 0.1.6 (case fold) | every graded cell | grading only; measured on the anchor slice (§4) |
| 2 | ISS-028 extractor rule | solve | grading only; rerun side re-graded post hoc for contrasts |
| 3 | ISS-029 prompt-plan source | simulate | grading only, 6 of 100 problems |
| 4 | PR #122 serve flags (`HF_CACHE_IN_JOB`, `HF_REVISION`, per-model flags) | new families | serving setup; no effect on the headline models' requests (to be checked on the anchor slice) |
| 5 | gpt-oss `reasoning_effort` sent explicitly (PR #126) | gpt-oss cells only | generation |
| 6 | reasoning trace stored (`PDDL_STORE_REASONING=1`, PR #126) | wave 2 if Q4 says yes | changes failure labels through the frozen scoring code (ISS-030); success unaffected (to be proven, §11 gate 4) |
| 7 | context 32K and 64K | context-room cells | generation, by design |
| 8 | `structured_outputs` JSON constraint | JSON-control cells | generation, by design; 2-in-480 escape in the smoke is a known leak |
| 9 | rtx_pro_6000 for the official Gemma BF16 | that tier | GPU class differs from the AWQ build (one sentence in Methods) |

Nothing else differs.

### 2.4 Where results go

- New sweep folder `results/extension-live/<cell>/`. `delivered-rerun/`, `sweep5v2-live`,
  `sweep6-live` are never written.
- **Reused rows** (rerun rows the extension reuses instead of rerunning) are copied with
  `tools/extension_copy_reused.py`, which adds `reused_from_folder`, `reused_from_job`,
  `reused_from_sha256`, `copied_at` to every copied row and writes
  `reuse_provenance.json`. The SLURM job id is passed by the operator (ids in
  `reference/delivered_rerun_prereg.md` §8). Which cells are reused: §3.4.
- **New-item trees** run into their own folders, never shared with reused rows: suffix
  `-hard` (`domains-hard/`), `-hard-vd-a`, `-hard-vd-b`. **Trees a and b never share a
  folder** (both name the invalid job `domain_neg`). Validate_domain never runs on
  `domains-hard/` (2 : 1 there). Rows are labelled by output folder in the analysis
  (rows do not record `--domains-dir`).
- Effort and stored-reasoning cells carry `OUT_DIR/client_settings.json` (effort, served
  system line, revision, job id).

---

## 3. The cells

### 3.1 Family tiers (decision 5)

Every family is registered now as a numbered tier with **the same cells and the same
analysis**, so adding a tier later needs only Omer's go-ahead, not a new prereg. A tier
runs only after it passes the parser smoke (tool calls clearly extracted; a wrong parser
gives a silent 0%).

| tier | model | weights (pinned) | parsers | thinking | GPU | smoke | wave |
|---|---|---|---|---|---|---|---|
| T0 | Qwen3.5-9B, Gemma-26B (AWQ), Qwen3.6-35B | as the rerun | as the rerun | off (w1), on (w2) | rtx_6000 | rerun | 1, 2 |
| T1 | gpt-oss-20b | `openai/gpt-oss-20b` @ `6cee5e8` | `openai`, `openai_gptoss` | effort **low** (w1), **medium** (w2), sent explicitly; labelled "low effort", never "thinking off" | rtx_6000 | passed (D1a) | 1, 2 |
| T2 | Llama 3.1 8B | `unsloth/Llama-3.1-8B-Instruct` @ `4699cc7` (weights byte-identical to Meta's) | `llama3_json` + vLLM's 3.1 JSON template | none (`--think-modes default`) | rtx_6000 | passed | 1 |
| T3 | Gemma 4 26B official BF16 | `google/gemma-4-26B-A4B-it` @ `4d7ae49` | `gemma4` | off (w1); on (w2, parser `none`) | rtx_pro_6000 | passed | 1, 2 |
| T4 | Ministral 3 14B | `mistralai/Ministral-3-14B-Instruct-2512` @ `29439f8` | `mistral`, `TOOL_CALL_ID_STYLE=mistral9` | none (`--think-modes default`) | rtx_6000 | passed | 2 |
| T5 | GLM-4.7-Flash | to pin at smoke | to choose at smoke | off and on | to choose | **not yet** | later |
| T6 | gpt-oss-120b | to pin at smoke | as T1 | effort as T1 | a GPU to itself | **not yet** | later |

Size ladder (same family as T0): Qwen3.5-0.8B and 4B, unaided, plain and steered, thinking
off (wave 1).

**gpt-oss date pin.** Harmony writes the current date into the system message
(`VLLM_SYSTEM_START_DATE` unset = today), so a gpt-oss prompt changes by day.
> ANSWER (Q1: pin `VLLM_SYSTEM_START_DATE` to one date, recommended 2026-11-09, for every
> gpt-oss cell? yes / no / other date):

### 3.2 Wave 1, thinking off (D2)

| cell | models | tasks | items | trials (rough) | settles |
|---|---|---|---|---|---|
| W1-a family cells: unaided, plain, steered | T1, T2, T3 | all five | `domains/` | ~80K | C3, C14 |
| W1-b neutral 2 x 2 (directive x steering) | T1, T2, T3, 9B, 35B | validate_plan | `domains/` | 12,000 for 9B and 35B; per new tier as Gemma's Part B | C4 |
| W1-c size ladder | 0.8B, 4B | all five | `domains/` | 27,360 | the ladder |
| W1-d new item kinds: unaided, plain, steered | every wave-1 model | validate_problem, validate_plan (`domains-hard/`); validate_domain (trees a and b) | D1b trees | ~20K | C11, how general R1 is |
| W1-e context room: plain and steered tool arms at 32K and 64K (16K = the rerun) | T0 | solve, simulate | `domains/` | ~4K | C5 |
| W1-f JSON control (`structured_outputs`) | T0 | unaided solve, simulate | `domains/` | 1,800 | C6 |
| W1-g open-model PlanBench, plain and steered (D1e) | 2 or 3 models incl. the 4B | PlanBench WT | PlanBench | ~7K | C15 |
| W1-h anchor slice (§4) | T0 | §4 | `domains/` | §4 | drift |

The exact trial count of each cell is computed by a script from the item manifests and
asserted in the analysis code (§11 gate 2); the "rough" column is the plan's.

### 3.3 Wave 2, thinking on (D3)

| cell | models | tasks | trials | settles |
|---|---|---|---|---|
| W2-a thinking on: unaided, plain, steered, the main sweep's budgets | T0 headline models; T1 at medium effort; T3 | all five | 41,040 for T0 | C18; the 0.6% calling finding |
| W2-b Ministral tier | T4 | as W1-a | as one W1-a tier | C14 |

**Reasoning trace (ISS-030).** Storing it (`PDDL_STORE_REASONING=1`) is the only way to
read what thinking did before a call. It changes failure labels through the frozen
scoring code (the think-overflow label becomes reachable), so wave-2 failure-label
tables would not compare with Study 1's thinking-on tables.
> ANSWER (Q4: store the trace in wave 2? Recommended **yes**, with failure-label
> comparisons to Study 1 thinking-on cells declared not comparable and success endpoints
> proven unaffected by a fixture test before the freeze):

### 3.4 Reused rows

Cells that equal a rerun cell (same model, weights, task, arm, items, context, grader
inputs) are **not rerun**; their rows are copied with provenance (§2.4). Proposed: the T0
thinking-off cells of the rerun (Part A plain and steered, Part B neutral for Gemma, Part
C unaided) are reused as the T0 side of W1-a, W1-b (Gemma) and W1-e (16K). The anchor
slice (§4) is a fresh run, so the reuse can be checked.

### 3.5 Frontier stage (D5; never pooled with Study 1 or Study 2)

Runner: `tools/claude_api_batch.py` (SDK `anthropic==0.109.2`), Batch API for every
unaided cell. Cost approved: about $66 in all with D5e (decision 8).

| cell | what | models | n | notes |
|---|---|---|---|---|
| D5a-1 | unaided solve, thinking on | Sonnet 4.6, Haiku 4.5 | 3 repeats per problem | within-model contrast with the existing thinking-off cells |
| D5a-2 | unaided solve, thinking on and `between_tools` | Sonnet 5.5 | 3 repeats | 5.5 rejects non-default temperature: both arms at T=1, effort `high` sent explicitly so only thinking differs |
| D5a-3 | thinking off at temperature 1, same problems | Sonnet 4.6, Haiku 4.5 | 3 repeats | separates sampling from thinking |
| D5b | size ladder: unaided and tool arm, calling rate, against size | to decide (Q6) | **[FROM ITEM 9]** | no model run until the ground truth is in (item 9); the tool arm cannot exceed the planner's 120 s share |
| D5c | tool arm on `domains-anon` | Sonnet 4.6 | 100 x1 solve; simulate as the budget probe | Haiku 4.5's already ran (2026-07-12, 1,520 trials, #125) |
| D5d | two random-string maps per domain, unaided solve | Sonnet 4.6, Haiku 4.5 | about 800 | memorization against "this renaming is harder" |
| D5e | Corrêa et al.'s 2-shot prompt word for word, our Gripper problems left out | Sonnet 4.6 | 95 x1 thinking off T=0; 95 x3 thinking on | one descriptive row, outside the confirmatory set, never pooled with v11 to v13 |

**GPT and Gemini** (in the 2026-11-08 approval, not in the 2026-11-09 decision):
> ANSWER (Q5: recommended **defer**, and keep them out of this stage; a later stage would
> need its own runner, keys and freeze):

> ANSWER (Q6: D5b models. Recommended: Sonnet 4.6 and Haiku 4.5, unaided and tool arm,
> thinking off; thinking on only if D5a shows a large thinking effect):

---

## 4. Anchor slice: has the setup drifted? (decision 4)

A fresh repeat of part of the rerun under the extension's apparatus.

**Cells (proposed).**

| model | task | arms | n per arm | why |
|---|---|---|---|---|
| Qwen3.6-35B | solve, simulate, validate_plan | plain, steered | 300, 300, 3,000 | the 35B cells flipped between the main sweep and the rerun (T8c) |
| Gemma-26B | validate_plan | plain | 3,000 | the R1 cell |
| Qwen3.5-9B | solve, simulate | plain | 300, 300 | a stable model, as a negative control |

About 10,800 trials.
> ANSWER (Q2: this slice, or a smaller one, e.g. the 35B solve and simulate cells plus
> Gemma validate_plan plain, about 4,200 trials?):

**Endpoints.**

- **A1, trial-level flip rate** (the endpoint decision 4 asks for): the share of paired
  trials (key: domain, problem, variant, plan label) whose call state differs between the
  rerun and the anchor repeat, per cell, with a domain-cluster bootstrap 95% interval
  (10,000 resamples, seed fixed at freeze). Also the share whose tool-verified success
  differs. Computed by the same method as `tools/reanalysis/s1_call_flips.py`.
- **A2, parity on tool-verified success**, as the rerun's §3: Δ = anchor − rerun, paired,
  TOST at ±5 points, 90% domain-cluster interval. Graded twice (validator 0.1.6 and the
  rerun's version); the verdict uses the rerun's version, the 0.1.6 figure is reported
  beside it.
- **A3, calling rate per cell**, anchor against rerun, same test.

**Readings (fixed now).**

| result | reading |
|---|---|
| 9B and Gemma: every cell's flip rate ≤ 5% and A2 within ±5 | no drift; extension cells compare with the rerun |
| 9B or Gemma: a cell's flip rate > 5% or A2 fails | the setup drifted; every extension contrast against a reused rerun row is reported as a separate-run comparison, and the reused rows are replaced by fresh runs for the contrasts that need them (cost to Omer first) |
| 35B: A3 within ±5 of the rerun (82.7 solve plain) | the rerun's 35B calling reproduces; "both runs" stays the quoted form for Study 1, and the extension may quote the rerun and anchor values together |
| 35B: A3 not within ±5, but the flip rate is like T8c's | 35B calling is unstable run to run on this setup; every 35B calling figure is quoted with its run-to-run spread, and "bigger calls less" stays a direction only |
| anything else | unresolved, reported with intervals |

---

## 5. Primary endpoints (every wave, every tier)

All on **delivered success**, exact, graded as §2.2, with the rerun's E1 to E4 definitions
(`reference/delivered_rerun_prereg.md` §4), applied per tier:

- **E1** delivered rate per cell, domain-cluster bootstrap 95% interval.
- **E2** availability contrast: tools-plain against unaided, same run, same grader, paired.
- **E3** steering contrast: tools-steered against tools-plain.
- **E4** delivery gap among calling trials, by the fixed failure categories (plus
  "refused or clipped final request").
- **E5 (new) calling rate** per cell (share of trials with at least one tool call).

Holm within each tier across that tier's E2 comparisons, and separately across its E3
comparisons. TOST margin ±5 points throughout. Wording: "criterion met" or "unresolved".

New items: validate_domain intervals cluster on the item (20 distinct valid items against
40 distinct invalid ones, `d1b_harder_items.md` §2), other tasks on the domain.

---

## 6. Registered readings

No reading is added, dropped or re-thresholded after the data are seen.

**R1. Does the directive lower calling in other families? (C3, C4; W1-b)** Per tier, the
neutral-minus-minimal calling difference on validate_plan, as the rerun's R5:

| result | reading |
|---|---|
| neutral calling lower by more than 5 points | the system-prompt sentence does work in that family |
| within ±5 (TOST) | inert in that family |
| higher by more than 5 | the directive suppresses calling there, reported as found |

"The calling finding generalises" is said only if at least two non-Qwen tiers give the
same reading as Gemma did.

**R2. Does not calling cost delivered answers in other families? (W1-a)** Per tier and
task, E2 for the lowest-calling cell: interval entirely below −5 = harm confirmed;
entirely inside [−5, +5] = no delivered harm; else unresolved.

**R3. Does "not calling costs nothing" hold on the new items? (W1-d)** The same E2 reading
on the new-item cells. A different reading from `domains/` for the same model and task is
reported as a dependence on the item kind.

**R4. Does delivery fall as context room shrinks? (C5, W1-e)** Per model and task, the
delivered rate at 16K, 32K and 64K, and the share of empty final answers. Reading: a
monotone rise in delivered success from 16K to 64K whose 16K-to-64K difference has a
95% interval above 0 = the delivery gate moves with context room; tool-verified flat
(TOST ±5 at each step) = the tool layer does not. Anything else unresolved.

**R5. The JSON control measures a different condition (C6, W1-f).** Reported as its own
condition, never as a "fixed" unaided baseline. Reading: the share of answers that parse
under the constraint and the delivered rate, beside Part C. The 2-in-480 escape rate of
the smoke is reported as a known leak.

**R6. Are the new item kinds harder? (C11; `d1b_harder_items.md` §7)** Per model, task and
kind: unaided and tool-verified accuracy on the new items minus on `domains/` (same
models, prompts and tasks), with intervals. The items are called **harder** in the paper
only if the difference is below −5 with its whole interval, for unaided accuracy, in at
least two of the three validate tasks. Otherwise they are "new item kinds".

**R7. Does the calling finding survive reasoning? (C18, W2-a)** Per model, calling rate
thinking on against thinking off. For Gemma: whether the drop from 21% to 0.6% (Study 1)
reproduces in the official BF16 weights (T3) and its effect on E2.

**R8. PlanBench with open models (C15, W1-g).** Calling rate and success, plain and
steered, per model; the frozen WT format clause reused byte for byte. Descriptive per
model; "tools help on PlanBench" only if E2 is above +5 with its interval for at least
two models.

**R9 to R11, frontier (D5).**

- **R9 (D5a).** Thinking on against thinking off on unaided solve, per model, paired on
  the problem, using the mean of the 3 repeats per problem; problem-cluster bootstrap.
  Reading: interval entirely above +5 = thinking raises solve for that model; inside ±5 =
  no effect; else unresolved. D5a-3 (T=1 thinking off) separates sampling: the thinking
  effect is quoted against D5a-3, not against the T=0 cells, if the two differ by more
  than 5.
- **R10 (D5b).** Unaided and tool-arm solve rates and the calling rate against the size
  tier; the tool arm's ceiling is the planner's 120 s share from item 9, reported beside
  it. **[FROM ITEM 9: the tiers and the planner shares]**
- **R11 (D5d).** Random-string solve against the themed renaming and the original; the
  reading of `NUMBERS.md`'s contamination block is "memorization" only if random strings
  recover the original's rate and the themed renaming does not.
- **D5e** is one descriptive row (no reading).

---

## 7. Secondary (descriptive, not gates)

Per-wording and per-domain calling and delivered tables; classical against numeric;
clipped-allowance counts; tokens and cost-of-pass on the delivered score (total tokens
and cost-of-pass, `project_tool_efficiency_metrics`); gpt-oss served system lines;
reasoning-trace lengths (wave 2, if stored); the D5a thinking tokens.

---

## 8. Execution order

1. Code PRs merged: item 5 (ISS-028/029 scripts), item 8 (D1e), the extension analysis
   code (§11). Item 11 on the cluster with Omer's go-ahead: the gpt-oss effort smoke,
   the validator venv upgrade to 0.1.6, the installed versions read, the checkout commit
   checked.
2. Wave-1 freeze (§11), then wave 1: anchor slice first; the anchor readings (§4) are
   computed before any other wave-1 cell is read.
3. Frontier freeze, then D5a, D5c, D5d, D5e (Batch API); D5b after item 9's ground truth.
4. Wave-2 freeze, then wave 2.
5. Readout (D4): the frozen code on live data, figures into `NUMBERS.md` by script,
   `paper_notes` entry, Omer reads it before any prose.

---

## 9. Declared pilots and smokes (none reads an outcome)

1. D1 smokes (2026-10-27 to 11-01), `reference/d1_smokes_20261027.md`.
2. The gpt-oss effort and trace smoke (PR #126 body), pass criteria in
   `tools/effort_smoke_check.py`.
3. The D1e PlanBench smoke (D1j), one model.
4. **The D5a thinking pilot** (2026-11-09, PR #131, $1.69): 20 keys per arm (Sonnet 4.6
   on, Haiku 4.5 on, Sonnet 5.5 on, Sonnet 5.5 `between_tools`, plus arm e, the 2-shot
   prompt). It measured thinking tokens and the answer-parse rate only; plan success was
   not computed. Its keys (`results/frontier-d5a-pilot/keys`) **are / are not** part of the
   D5a cells:
   > ANSWER (Q7: recommended **not**: the pilot keys are excluded from no cell, but the
   > pilot rows are not pooled into D5a; D5a reruns those keys):

---

## 10. Analysis code (to be written; nothing exists yet)

`tools/extension/` (proposed), one entry point per stage, each:

- reads rows through one typed loader that crashes on an unknown enum, a missing key or a
  wrong layer (gate 1); labels rows by output folder (tree a / b, `-hard`);
- asserts every registered constant: tier roster, N per cell (from the manifests), item
  hashes (`d1b_harder_items.md` §5), cluster counts (20 domains; items for
  validate_domain), seeds, validator version, the reuse provenance fields (gate 2);
- applies the ISS-028 rule and the ISS-029 plan source (§2.2);
- prints every figure the readout quotes in a form `NUMBERS.md` takes verbatim.

The frozen delivered-rerun analysis refuses these trees (it checks the `domains/`
manifest); the extension reuses its estimators by import, read-only, where they fit.

---

## 11. Freeze record (one per stage; to be completed before that stage's first trial)

Blocking prerequisites (`/freeze-protocol` v2), each recorded here with evidence:

1. **Typed load boundary** over every row the stage reads.
2. **Registered constants are asserts** (list them with `file:line`).
3. **Traceability map**: every clause of §4 to §6 for the stage → `file:line` or a runtime
   assert. A clause without code blocks the freeze.
4. **Synthetic fixture run** (~30 rows, committed under `tests/`): censored and
   indeterminate rows, a zero-success arm, a duplicate overlay cell, a missing
   `snapshot_cap`, a known Δ per contrast, a tree-a/tree-b `domain_neg` collision, a
   reused row, an ISS-028 trailer, an ISS-029 prompt built from the cached plan, and (wave 2) a
   stored-trace row whose success must equal the same row graded without the trace.
5. **Adversarial review** of the freeze candidate (a different session, `/code-review`
   high or stronger), findings fixed before hashing.

Then: harness commit, sha256 of every analysis file, `run_experiment.py` hash unchanged,
delivered-rerun package hash `822aace9ef8a…` unchanged, the 5 other prereg-pinned files
unchanged, validator version on the cluster, item manifests' hashes.

Readout-time tripwires (halt, do not narrate): a guard firing in every cell; a constant
output column; a rate outside the known band for that model and task.

---

## 12. Deviations

None yet. After a stage's freeze, any change to its cells, endpoints, readings or frozen
files is a numbered deviation here, with a re-freeze.

---

## Questions for Omer (the `> ANSWER:` slots above, in one list)

1. **Q1** gpt-oss date pin: recommended yes, 2026-11-09.
2. **Q2** anchor slice size: recommended the full ~10,800-trial slice (the 35B flips make
   the 35B cells the ones most worth repeating; the 9B is the negative control).
3. **Q3** the anchor thresholds in §4 (5% flip rate for the stable models; ±5 TOST): accept,
   or change before the freeze.
   > ANSWER:
4. **Q4** store the reasoning trace in wave 2: recommended yes.
5. **Q5** GPT and Gemini in D5a: recommended defer.
6. **Q6** D5b models: recommended Sonnet 4.6 and Haiku 4.5, thinking off, unaided and tool arm.
7. **Q7** D5a pilot keys: recommended rerun them inside D5a, pilot rows not pooled.
8. **Q8** reuse of the rerun's T0 thinking-off cells (§3.4) instead of rerunning them:
   recommended yes, conditional on the anchor reading "no drift".
   > ANSWER:
9. **Q9** R6's bar for calling the items "harder" (below −5 for unaided accuracy in at
   least two of three validate tasks): accept or change.
   > ANSWER:
