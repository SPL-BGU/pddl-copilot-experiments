# Paper outline, ICAPS 2027 version

**Written 2026-11-25 for Omer. Outline only: no prose is drafted here and nothing is
fitted to a page count.** For each section: what it has to establish, which numbers
carry it, and which figures and tables sit there. Numbers are the ones in the merged
draft and `NUMBERS.md`. Those marked **(matched run)** are from the matched run of
2026-11-26 (`reference/matched_run_readout.md`; `NUMBERS.md`, "Matched run"), filled in
on 2026-11-26. Open choices are collected in
section 12 with `> ANSWER:` lines.

The line the paper follows: clean results first; the earlier runs, the prompt fault and
the registered deviations in the supplement in full, with one sentence in the body that
points there.

---

## 1. Introduction

**Has to establish**
- The setting: a language model is given PDDL tools (planners, validators, a state
  simulator) and asked to do planning-related tasks. Having a correct tool does not
  settle whether the answer the user receives is correct.
- The three questions: do the tools help (RQ1), does the model pick the right tool
  (RQ2), does it use what the tool returns (RQ3).
- What is measured: the final answer the model delivers, on five tasks, with and without
  tools, for three open-weight models, with frontier models beside them.
- One finding per question, as the contribution list.

**Numbers that carry it** (one per question)
- RQ1: with tools the models deliver a valid plan in 79 to 95% of trials, against 41 to
  68% unaided **(matched run)**; on plan verdicts both error rates fall for the two Qwen
  models (for Qwen3.5-9B, wrongly rejected valid plans −20.1 points, wrongly accepted
  broken plans −9.3).
- RQ2: when a model calls, it calls the right tool; whether it calls is the variable.
  Gemma-26B calls the plan validator in 20.0% of trials under the plain wording and
  93.1% with one added sentence.
- RQ3: verdicts reach the answer (at most 1.7% lost), plans mostly do (4.7 to 13.4%
  lost), state traces mostly do not (66 to 91% lost, depending on the reading; see
  12.3).

**Figures and tables:** none. (Optional: one small schematic of the three questions
along the path question → tool call → tool result → final answer. It would also serve
as the map of the Results.)

---

## 2. Background and related work

**Has to establish**
- Language models as planners and plan checkers: unaided plan generation is unreliable
  (Valmeekam et al.; PlanBench).
- Language models as formalizers that hand the problem to a planner (Huang and Zhang,
  ACL 2025; LLMFP; Corrêa et al.).
- Tool use and the decision to call: prior work mostly assumes the call happens.
- Positioning: this paper measures the three steps separately, on the delivered answer.
- Relation to the group's earlier study, in the third person (anonymity).

**Numbers:** none of ours.

**Figures and tables:** none.

---

## 3. Experimental setup

One section, five short parts. The four constraints you want in the body are stated
here, as facts about the setup, each once.

### 3.1 The tools
- Seven tools offered together in every with-tools trial: two planners (classical,
  numeric), three validators (domain, problem, plan), the state-transition tool, and
  plan saving.
- **Constraint (simulate tool):** the state-transition tool returns every predicate with
  a true or false value in its own notation, while the answer must list the true
  predicates. Delivering a trace is a conversion, not a copy. Stated here, used in RQ3.

### 3.2 Tasks and test items
- Five tasks: solve, validate_domain, validate_problem, validate_plan, simulate.
- 20 domains, 5 problems each; valid and broken plans per problem for validate_plan.
- **Constraint (small problems):** the planner solves every problem when called (run
  time 0.15 s to 22.3 s, two thirds under 0.32 s). So the paper says nothing about
  problems a planner cannot solve; what it measures on solve is everything around the
  planner.
- **Table (tasks):** the current Table `tab:tasks`. **Table (one example per task):**
  `tab:task-examples`, here if room in your long draft, otherwise supplement.

### 3.3 Models
- Qwen3.5-9B, Gemma-26B, Qwen3.6-35B, served locally, thinking off, 16,384-token
  window. **Constraint (quantization):** Gemma-26B and Qwen3.6-35B are 4-bit quantized.
- Frontier models (decision 12.1). **Constraint (different conditions):** one
  sentence listing what differs (provider-side sampling, no fixed temperature on the
  new models, thinking setting), and that their rows are never pooled with or ranked
  against the open models.
- **Asked for by the call** (ICAPS 2027, Reproducibility section, read 2026-11-26):
  hardware, benchmarks and software versions stated in the main paper. One or two
  sentences here: the GPU class, the serving software and its version, the tool suite's
  commit and the validator release, the model identifiers. The AAAI Reproducibility
  Checklist is not required and leaves `main.tex`.

### 3.4 The three arms
- No tools; tools offered with the plain wordings; tools offered with one added sentence
  that names the tool (steered). Three paraphrased wordings per arm.
- The no-tools system message states the answer format in plain words.

### 3.5 Grading and statistics
- What counts: the final answer as delivered, graded the same way in every arm. On solve
  the plan must pass the validator; on simulate the trace must equal the reference;
  on the validation tasks the verdict must be right.
- Paired differences on the same trial; 95% intervals from a bootstrap over the 20
  domains; no pooling across models.
- **Table (data):** a small table that says where each result comes from: the matched
  run (RQ1 on solve and simulate), the October run (RQ1 on the validation tasks, RQ2,
  RQ3), the frontier run. With trial counts and dates.
- **The one pointer sentence:** earlier runs, a fault in an earlier no-tools prompt and
  all registered deviations are reported in the supplement.

---

## 4. RQ1: do the tools help?

### 4.1 Plan verdicts (validate_plan)
**Has to establish:** with the tool, both kinds of verdict error fall, when the model
calls it.
**Numbers:** unaided, the open models reject 8.5 to 25.7% of valid plans and accept 7.8
to 11.1% of broken ones. With tools (plain): Qwen3.5-9B −20.1 [−31.6, −9.3] and −9.3
[−14.6, −3.5]; Qwen3.6-35B −7.5 [−12.4, −3.3] and −5.6 [−8.2, −3.1]; Gemma-26B no change
(−3.3 [−7.2, 0.3], +0.8 [−1.6, 3.3]) because it rarely calls (forward pointer to RQ2);
with the steering sentence Gemma's rates are 2.8% and 2.9%.
**Table:** `tab:rq1-verdicts`. **Figure:** `fig:rq1-verdicts`.
Source: October run, both arms in one run.

### 4.2 Domain and problem validation
**Has to establish:** the same question on the other two validation tasks.
**Numbers:** not yet computed as delivered rates (analysis to do, section 13). The
data are clean (October run, both arms).
**Table:** one row block added to the verdict table, or one small table.

### 4.3 Solve
**Has to establish:** how much the tools add to the share of problems solved, per model,
and how that depends on problem size.
**Numbers (matched run):** unaided 41.3 / 58.0 / 68.3% (Qwen3.5-9B / Gemma-26B /
Qwen3.6-35B); tools with the plain wording 91.7 / 94.0 / 79.3%; with the tool named
90.3 / 94.7 / 90.0%. Tools (plain) minus no tools: +50.3 [+37.3, +63.3], +36.0 [+23.0,
+49.7], +11.0 [+2.3, +19.7]. The last has an interval above zero and does not survive
the Holm adjustment (adjusted p = 0.105); with the tool named it is +21.7 [+11.0,
+33.7] and does. Naming the tool adds +10.7 [+4.0, +17.7] for Qwen3.6-35B (not after
Holm) and nothing for the other two: its plain arm makes no call in 36 of 300 trials
(forward pointer to RQ2). By size: on reference plans over 40 actions, unaided 19.4 /
36.1 / 41.7%, with tools (plain) 44.4 / 61.1 / 38.9%; the two smaller models stay at
93% or more with tools up to 40 actions.
**Table:** solve, three arms by three models, with the paired differences (replaces
`tab:rq1-solve` and `tab:rq1-control`). **Figure:** solved against reference plan
length (`fig:rq1-solve`, redrawn on the matched run).
**Plan length of valid plans** (`tab:rq1-planlen`): one sentence in the body (a plan
delivered with tools is the planner's plan; median ratio 1.00 unaided); table to the
supplement.

### 4.4 Simulate
**Has to establish:** on the task whose tool output is long, the tools do not raise the
share of correct answers, and both arms degrade with trace length.
**Numbers (matched run):** exact traces unaided 12.7 / 31.7 / 35.3%; tools with the
plain wording 19.7 / 17.7 / 30.3%; with the tool named 16.0 / 16.0 / 32.3%. Tools
(plain) minus no tools: +7.0 [-1.3, +15.7], -14.0 [-25.3, -3.7], -5.0 [-13.3, +3.3]. No
model has tools ahead. For Gemma-26B the unaided arm is ahead, with an interval below
zero that does not survive the Holm adjustment (adjusted p = 0.105). Beyond 40 actions
no arm of any model delivers one exact trace. With tools, 142 to 168 of 300 final turns
per cell had no room left in the window (forward pointer to RQ3); unaided, 97 to 145 of
300 answers stop at the output cap.
**Table:** simulate, three arms by three models (replaces `tab:rq1-simulate`).
**Figure:** share of states right against trace length (`fig:rq1-simulate`, redrawn).
The state-by-state and lenient scores: keep the strict score in the body, the lenient
one as a sentence (many unaided answers are right as far as they go and end early:
unaided lenient 56.7% against strict 40.1% for Gemma-26B and 56.7% against 43.7% for
Qwen3.6-35B, on 94 problems; with tools the two scores are within one point).

---

## 5. RQ2: does the model choose the right tool?

**Has to establish**
- On four of the five tasks a model that calls, calls the right tool and nothing else.
- What varies is whether it calls, and one sentence in the prompt moves that.
- On solve the models call more than they need.

**Numbers**
- Other tools called in at most 13.0% of trials in any open-model cell.
- Calling under the plain wording: Gemma-26B plan validator 20.0%; Qwen3.6-35B 83.1%;
  Qwen3.5-9B state-transition tool 80.7%. With the steering sentence: 93.1, 100.0,
  100.0%.
- Solve: the fitting planner is called in 82.7 to 100% of trials, but only 22.3 to 39.0%
  call it and nothing else; Gemma mostly adds a plan check (175 of 214), Qwen3.5-9B
  mostly the other planner (138 of 183).

**Table:** `tab:rq2-choice`. **Figure:** none needed; optional bar chart of calling,
plain against steered, per task and model.
Source: October run, tool arms.
To the supplement: thinking on (`tab:rq2-thinking`); the registered system-prompt
sentence result for Gemma (20.0 to 26.9%).

---

## 6. RQ3: does the model use the tool's output?

**Has to establish**
- The loss between a correct tool result and the final answer grows with the size of
  what has to be carried: a verdict, a plan, a state trace.
- For traces, two observed causes: the context window fills, and the answer needs a
  conversion of the tool's notation.

**Numbers**
- Verdicts: 76 of 20,086 correct results lost, at most 1.7% in a cell.
- Plans: 4.7 to 13.4% lost.
- Traces: 69.9 to 91.2% lost (registered); 65.9 to 80.5% when a one-object-per-line
  trace is also read (decision 12.3 on which is quoted).
- Causes, plain wording: 405 of 596 lost traces and 52 of 86 lost plans are final turns
  with no room left in the window. Of the traces with the right number of steps and a
  wrong step, 145 of 219 differ only in the converted predicates.
- Larger window (pilot, 114 to 120 trials per cell): empty answers fall from 42 to 43%
  at 16K to 6 to 11% at 64K, while the loss falls much less (for example 72.9 to 69.0%
  for Qwen3.5-9B).

**Table:** `tab:rq3-lost` (with the cause columns folded in if they fit).
**Figure:** optional, one stacked bar per task: delivered / lost to the window / lost in
conversion / other.
Source: October run, tool arms.
To the supplement: the pilot table (`tab:rq3-pilot`), the second grading
(`tab:rq3-regrade`), the reading by language-model readers.

---

## 7. Frontier models

**Has to establish:** whether the three answers hold for much stronger models, under
conditions that are stated as different.
**Numbers** (the registered Claude run, Haiku 5.5 and Sonnet 5.5; readout
`reference/frontier55_readout.md`; frozen values in `NUMBERS.md`, block "Claude run")
- Size: 4,560 trials per arm and model, three plain wordings, all on 2026-11-26.
- Solve, right per arm (no tools, tools): Haiku 73.7%, 95.0%; Sonnet 94.0%, 97.0%.
- Simulate, right per arm (no tools, tools): Haiku 41.3%, 21.0%; Sonnet 55.0%, 46.3%.
- Tools minus no tools, Haiku (points, 95% interval): solve +21.3 [+7.7, +36.3];
  validate_domain +17.5 [+7.8, +29.4]; validate_problem +8.8 [+4.2, +14.0];
  validate_plan +0.8 [-1.6, +3.0]; simulate -20.3 [-30.7, -11.0].
- Tools minus no tools, Sonnet: solve +3.0 [-3.0, +10.7]; validate_domain +0.3
  [+0.0, +0.8]; validate_problem +3.8 [+2.2, +5.7]; validate_plan +0.4 [-0.5, +1.6];
  simulate -8.7 [-17.0, +0.0].
- Registered readings: tools ahead on Haiku solve, validate_domain, validate_problem
  and on Sonnet validate_problem; no tools ahead on Haiku simulate; no difference shown
  on the other five. The five differences shown all hold after Holm.
- Exactly the right tool: Haiku 64.2 to 100% (lowest on validate_problem); Sonnet 91.3
  to 100%.
- Tool right and answer wrong, traces: Haiku 78.0% [66.0, 88.0] (223 of 286); Sonnet
  53.0% [39.0, 66.7] (157 of 296).
- Tool right and answer wrong, plans: Haiku 5.1% (15 of 294); Sonnet 3.0% (9 of 299).
  Verdicts: Haiku 5 of 3,763; Sonnet 0 of 3,940.
- Caveat (post hoc): with tools, 204 of Haiku's 300 simulate answers are prose the
  grade does not accept.
- The old runs (Haiku 4.5, Sonnet 4.6) are an earlier record in the supplement source;
  their figures are not compared with these.

**Table:** `tab:claude` (two models by five tasks: right per arm, the paired
difference, exactly the right tool, tool right and answer wrong).
**Placement (decided, 12.2):** one short section with one table after RQ3. No Claude
row in the RQ1 tables or the by-length figures.

---

## 8. External check on PlanBench

**Has to establish:** the direction of RQ1 holds on a public benchmark that was not
built by us, and the gain comes from the tools and not from the added instructions.
**Numbers:** the registered PlanBench study as filed (Haiku 4.5; 600 instances per
domain).
**Table:** one, the with-tools result (`tab:pb-wt`) with the no-tools column beside it.
To the supplement: the instruction ladder (`tab:pb-ladder`), the distortion analysis,
scope and cost.

---

## 9. Discussion

**Has to establish**
- The three answers as one picture: the planner is not the bottleneck on these
  problems; the model's decision to call and its ability to carry the result are.
- Where tools help most (short outputs: verdicts, plans) and where they do not (long
  outputs: traces).
- What a tool designer can take from it: the form and size of a tool's output decide
  whether its correctness reaches the user; a single sentence decides whether it is
  called.

**Numbers:** none new; at most three recalled.

---

## 10. Scope of the claims

Short. The four constraints, each in one sentence with what it limits: small solvable
problems; the simulate tool's notation and the 16K window; two quantized models; the
frontier models' conditions. Then: three open models from two families; thinking off;
one tool suite.

---

## 11. Conclusion, with future work folded in

**Has to establish:** the three answers in three sentences; two directions (larger
problems where the planner can fail; tools whose output is shaped for the model).
A third direction worth a sentence (from the closed PR #144): whether the model should
restate the tool's output at all, or the tool's result should go straight into the
answer while the model only chooses the tool and checks the result.

---

## Supplement (in full, pointed to once from 3.5)

1. The earlier runs: the May sweep (five models, thinking on and off, renamed domains,
   500-character storage), the October run's parity record, the corrected-prompt
   control, the continuity table of the matched run.
2. The prompt fault on solve and simulate: what it was, the control that measured it,
   both gradings.
3. All registrations, deviations and tripwire audits.
4. Every prompt verbatim; one example per task; domain sizes.
5. Thinking on; the two small models; contamination (renamed domains); cost in tokens.
6. The context-window pilot; the JSON constraint pilot; the second gradings.
7. PlanBench in full. The old Claude runs if a new frontier run replaces them.
8. Plan-length table; per-wording and per-domain tables.

---

## 12. Open choices

### 12.1 Which frontier models (section B of `unified_run_design.md`)
Lean: Haiku 5.5 and Sonnet 5, both with thinking off, same tasks and wordings as the
open models, no structured-output parameter, both arms on the same day.
> ANSWER: **Haiku 5.5 and Sonnet 5.5 (Omer, 2026-11-25).** Haiku with thinking off; Sonnet at its lowest setting (no thinking before the answer, short notes between tool calls).

### 12.2 Where the frontier results sit
Lean: their own short section (7) with one table. Inside the RQ tables they invite a
ranking against the open models that the conditions do not support.
> ANSWER: **Own section only (Omer, 2026-11-26).** The Claude rows leave the RQ1 tables
> and the by-length figures and appear only in the table of section 7, built on the
> Haiku 5.5 and Sonnet 5.5 run. Done together with that section's table, once the
> run's readout is in. The old rows (Haiku 4.5, Sonnet 4.6) go to the supplement.

### 12.3 Which trace-loss figure RQ3 quotes
The October run registered one grader (69.9 to 91.2% lost). The matched run registers a
reader that also accepts one object per line; under that reader the October figure is
65.9 to 80.5%, computed after the fact. Lean: quote the registered range in the table
and give the other in one clause, so RQ1 and RQ3 are not read with two rulers without
saying so.
> ANSWER: **ok (Omer, 2026-11-26):** the registered range in the table, the other in one clause.

### 12.4 PlanBench in the body or the supplement
Lean: body, one paragraph and one table. It is the only evidence outside our own test
items.
> ANSWER: **yes, in the body (Omer, 2026-11-26).**

---

## 13. Analysis still to do for this outline

1. The matched run: done 2026-11-26 (`reference/matched_run_readout.md`).
2. (Not now: Omer, 2026-11-26.) Delivered rates on validate_domain and validate_problem, tools against no tools,
   from the October run (4.2).
3. The frontier run, once 12.1 is answered.
4. Tables and figures rebuilt on the matched run (solve by plan length, simulate by
   trace length, plan length, and a table of the three arms with their paired
   differences): in work on branch `paper/rq1-matched-run`, 2026-11-26.
