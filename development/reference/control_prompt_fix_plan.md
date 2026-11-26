# Control run: does the flawed no-tools system prompt hold the unaided baseline down?

*Written 2026-11-23 as a proposal. **Status: decided the same day (Omer): run it, as an
exception to the "No new runs" line of `roadmap.md`.** His answers are in section 9. The
re-grade of stored answers (step 0) is done and filed. The run has not started; every
cluster action still needs its own go-ahead. Sections 0 to 8 are kept as written, with
dated notes where a decision or a finished step changed them.*

**In short.** Checking the facts for this plan turned up something that needs no run:
the frozen grader does not read an unaided solve plan when the model writes it as a
JSON list inside a code block, and that is the layout the flawed system prompt asks
for. A first count says the unaided solve baseline about doubles when that block is
read (section 0). So the recommendation has two parts, in this order:

1. **A re-grade of the answers we already have** (no run, allowed under the current
   decision, about one day). It measures the layout part of the problem. **Done
   2026-11-23, PR #146** (note at the end of section 0).
2. **The control run** (3 models, solve and simulate, 3 prompt cells, 5,400 trials,
   about 19 GPU-hours). It measures what a re-grade cannot: whether the wrong
   description changed what the models wrote, and not only how it was laid out.

---

## 0. Found while checking the facts

The facts in the brief were checked against the repository and the stored trials. The
figures in the brief all hold. Four points differ from it or add to it. The last two
change the plan.

**a. The opt-in JSON constraint is already on `main`.** `harness/d1a-new-families` is
merged. `--json-constraint`, `$PDDL_JSON_CONSTRAINT` and the cell `no-tools-jsonbound`
are in `pddl_eval/vllm_client.py` (lines 182 to 214 and 296 to 299),
`cluster-experimenting/submit_with_rtx.sh` and `run_condition_vllm_rtx.sbatch`.

**b. The frozen hash covers the prompt files.** `tools/delivered_rerun/run.py`
(`DEPENDENCIES`) hashes `pddl_eval/prompts.py`, `runner.py`, `schemas.py`,
`scoring.py`, `chat.py` and `run_experiment.py` into the package hash `822aace9…`. So
a corrected prompt cannot be added by editing `prompts.py`. It has to live in a file
outside that list (section 6). The hash was confirmed on this worktree.

**c. The pointer changed the layout of the solve answers.** The user prompts ask for
parenthesised PDDL actions. Most stored unaided solve answers still end with a JSON
plan in a code block, either `{"plan": [...]}` or a bare list of quoted actions:
260 of 300 for Gemma-26B, 198 for Qwen3.5-9B, 204 for Qwen3.6-35B (Part C of the
rerun). A few answers name "the schema" in their text. The only place a JSON answer is
asked for on solve is the system prompt.

**d. The frozen delivered grader does not read that layout.** The brief says it reads
plans in any layout. It does not. `tools/delivered_rerun/grade.py` (`solve_plan`) reads
a JSON plan only when the whole answer is the JSON object. For an answer that reasons
first and then gives the plan as a JSON list in a code block, it either finds no plan,
or it grades action-shaped lines picked up from the reasoning text. Counts from a
read-only pass over Part C with the frozen functions:

| model | unaided solve, frozen grade (the record) | right when the plan in the last code block is read | frozen wrong, block right | frozen right, block wrong |
|---|---|---|---|---|
| Gemma-26B | 64 of 300 (21.3%) | 146 of 300 (48.7%) | 83 | 1 |
| Qwen3.5-9B | 73 of 300 (24.3%) | 120 of 300 (40.0%) | 50 | 3 |
| Qwen3.6-35B | 76 of 300 (25.3%) | 155 of 300 (51.7%) | 80 | 1 |

On simulate the same pass, with the line reader already used for RQ3
(`rq3_context_pilot.line_reader_exact`), adds 37 right traces for Gemma-26B (72 to 109
of 300), 11 for Qwen3.6-35B (53 to 64) and none for Qwen3.5-9B (28). All 100 of Gemma's
answers to wording v12 fail the frozen grader on layout: they are one JSON object per
line with no outer wrapper.

**How far to trust these counts.** They are scoping counts from one pass by one
session. They are not reviewed, carry no intervals, and are not in `NUMBERS.md`. The
first column reproduces the frozen readout exactly (21.3, 24.3, 25.3 on solve; 24.0,
9.3, 17.7 on simulate), which checks the loader and the grader. The 302 plans that had
no stored verdict were validated on the laptop with pddl-pyvalidator 0.1.6; the frozen
readout used 0.1.5, which is stricter about capital letters (ISS-027). Appendix A gives
the rule and the files. **Do not quote these figures.** They say a proper re-grade is
worth doing, and that it should come before the run.

**Update, 2026-11-23: these scoping counts are replaced by a filed re-grade.**
`tools/reanalysis/rq1_layout_regrade.py` (PR #146, merged) keeps every frozen grade and
adds the layout-tolerant reading beside it, with the same reader on the unaided arm and
on both tool arms. It is filed in `NUMBERS.md`, "RQ1 solve and simulate, layout-tolerant
re-grade of both arms": unaided solve 21.3 / 24.3 / 25.3% frozen against 48.0 / 38.3 /
48.0% layout-tolerant (Gemma-26B / Qwen3.5-9B / Qwen3.6-35B). The counts in the table
above (48.7 / 40.0 / 51.7%) are that script's "case folded" column, because the scoping
pass validated with pyvalidator 0.1.6. Quote the filed figures, and only beside the
frozen ones. Two parts of that script carry over to the control (section 6): its
`block_plan` reader, and its in-process validator route on pddl-pyvalidator 0.1.5, the
readout's release.

**What this means for the question.** The abstract and RQ1 quote unaided solve at
21 to 29%. For the open models that figure is the frozen grade. Part of the distance
between it and the tool arms is the grader not reading the layout the prompt asked for.
This is the main session's to handle in the paper; this document only plans around it.

---

## 1. The question

On solve and simulate, the no-tools system prompt tells the model to "conform to the
JSON schema provided by the format constraint". The model never received a schema,
because the server dropped the field that carried it. Omer's question: did that wrong
description hold the unaided baseline of RQ1 down?

There are two ways it could have done so.

- **Layout.** The model writes its answer in a shape the grader does not read. Section
  0 shows this happened on solve and, for Gemma and the 35B, on simulate. A re-grade of
  the stored answers measures it. No run is needed.
- **Content.** The pointer changes what the model writes: how it reasons, how long the
  answer is, whether it runs into the output cap. No re-grade can show this, because
  the stored answers were all written under the flawed prompt. Only new answers under a
  corrected prompt can.

**What the control can show.** For three models and two tasks: how the delivered
baseline moves when the pointer is removed, and when the format is spelled out, with
everything else held as in Part C.

**What it cannot show.** It says nothing about the main sweep (Study 1), about
thinking on, about other models, or about the Claude runs. It does not tell us what a
working decoder constraint would give (the pilot of PR #145 covers that for one model).
It does not replace Part C: it is a new condition, reported beside Part C.

---

## 2. The design

### Cells

**Recommendation: option (b), two corrected cells, plus the old prompt run again in the
same window.** Three cells per model:

| cell | system prompt | what it answers |
|---|---|---|
| **O** (old) | today's text, unchanged | the anchor for pairing, and the drift check against Part C |
| **A** (pointer removed) | the reference to the schema deleted, nothing added | Omer's question as asked: did the wrong description misguide the models? |
| **B** (format stated) | the pointer replaced by a plain statement of the answer format, with the outer `{"trajectory": [...]}` wrapper on simulate | what a correct description would have given |

Why two cells and not one. A single cell that both removes the pointer and states the
format cannot say which change moved the score. Cell A is the smallest possible edit, a
deletion, so any effect is the pointer's. Cell B answers a different question (what the
baseline would be with a correct instruction). Each extra cell costs about 6 GPU-hours
(section 4), so cost does not argue for one cell. If Omer wants the smallest run, the
one cell to keep is B, with A dropped; the price is that "pointer removed" and "format
stated" can no longer be told apart.

### Exact wording

Current text, from `pddl_eval/prompts.py` (`WITHOUT_TOOLS_SYSTEM_BY_TASK`). The part
that changes is the end of the third sentence. The first two sentences stay byte for
byte, and each prompt stays three sentences long, as the mirror rule of the tool-arm
prompts requires.

**solve**

- O: `You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; conform to the JSON schema provided by the format constraint.`
- A: `You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning.`
- B: `You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; end your response with the plan alone, one parenthesised PDDL action per line.`

**simulate**

- O: `You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; conform to the JSON schema provided by the format constraint (per-step state with boolean predicates and numeric fluents).`
- A: `You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; give the per-step state with boolean predicates and numeric fluents.`
- B: `You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; end your response with a single JSON object of the form {"trajectory": [ ...steps... ]}, where each step has the keys step, action and state (state.boolean and state.numeric).`

**Changed 2026-11-23, before any trial (Omer): cell B asks for a fenced code block.**
The independent review of the analysis showed that neither registered reader reads a
final answer given without a code block after prose (on solve the frozen grader mixes
it with action-shaped lines of the reasoning; on simulate it reads only a whole-answer
object or a fenced one). Cell B as run:

- solve B: `You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; end your response with the plan alone in a fenced code block, one parenthesised PDDL action per line.`
- simulate B: `You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; end your response with a fenced code block that holds a single JSON object of the form {"trajectory": [ ...steps... ]}, where each step has the keys step, action and state (state.boolean and state.numeric).`

The B lines above are the first wording and were never run. The registration
(`reference/control_prompt_fix_prereg.md`) holds the sha256 of the texts as run.

Notes on the choices, each open to Omer's edit before the prereg is frozen:

- **B on solve asks for lines, not JSON.** The three user wordings ask for parenthesised
  actions, and v12 asks for "each action on its own line". A JSON instruction in the
  system prompt would contradict the user prompt, which is the conflict the original
  design had. Lines agree with all three wordings.
- **B on simulate follows the sentence the Claude runs used** (`SIMULATE_JSON_DIRECTIVE`
  in `tools/_claude_api_common.py`, printed in the paper's appendix), without its "ONLY
  ... no prose" part. That part would take away the room to reason before answering,
  which is the effect the constraint pilot measured and which would make B a different
  condition again.
- **B mirrors the validation prompts**, which say "end your response with exactly one
  line: VERDICT: ...". Those are the tasks where the prompt-level format worked.
- **A on simulate keeps the hint about the state** ("boolean predicates and numeric
  fluents"), because that hint describes the task and is not part of the pointer.

### What stays identical to Part C

Everything except the system text. Sources in brackets.

- User prompts v11, v12, v13, byte for byte (`pddl_eval/prompts.py`).
- The three models, same weights and quantisations: `Qwen/Qwen3.5-9B`,
  `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`, `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`
  (`tools/delivered_rerun/constants.py`, `MODEL_IDS`).
- Thinking off. The 16,384-token window. Output cap 8,192 tokens on solve and 6,144 on
  simulate (`pddl_eval/runner.py`, `DEFAULT_NUM_PREDICT`). Temperature 0
  (`pddl_eval/chat.py`). Four requests at a time (the sbatch default).
- vLLM 0.20.2 from the shared `~/vllm.sif`. Answers stored up to 65,536 characters.
- The same 100 problems per task (20 domains, 5 problems each).
- The request still carries the `guided_json` field that the server drops, in all three
  cells. Taking it out would be a second change.
- No decoder constraint in any cell.
- The harness at tag `delivered-rerun-harness` plus additive changes only.
- The grader: the frozen delivered grader, imported unchanged.

---

## 3. The comparison

**The old prompt is run again, in the same window, and the comparison is paired.** Cell
O is submitted together with A and B, on the same GPU class and the same container. A
and B are each compared with O on the trial key (task, domain, problem, wording), the
same key the rerun used.

Why not compare A and B with the stored Part C cell directly. The rerun ran from
2026-10-03 to 2026-10-09 (`NUMBERS.md`, "Run and query dates"). A cell run about eight
weeks later differs from it in ways no one controls (queue, node,
batching at temperature 0). The constraint pilot saw 25.0% against 31.7% on the same
60 solve trials between two jobs, an interval-sized gap at that sample. With a fresh O
cell the prompt is the only thing that differs between the cells compared.

**What Part C is then used for: a drift check.** O is compared with Part C on the same
300 trial keys per model and task, by the frozen grade. The precedent for the size of
such a gap: the same unaided solve trials in the main sweep and in Part C, months
apart, differed by 0.0 to +2.0 points with 90% intervals about 2 to 3 points wide on
each side (`delivered_rerun_readout.md`, "Part C parity"). If O sits within the chosen
margin of Part C, the setup is taken to match Part C's. If it does not, the control's
within-window contrasts still stand, and the readout says plainly that the setup moved
and that the control's levels should not be set beside Part C's levels.

**Never pooled.** O, A and B are not pooled with Part C or with the main sweep, and no
control figure stands in for a Part C cell. Part C stays the registered unaided input
of the rerun's E2 contrast.

---

## 4. Size and cost

**Trials.** The full Part C size on the two tasks: 100 problems by 3 wordings, so 300
trials per model, task and cell.

| | per model | all three models |
|---|---|---|
| one cell (solve + simulate) | 600 | 1,800 |
| recommended: O + A + B | 1,800 | **5,400** |
| smaller option: O + B | 1,200 | 3,600 |

A smaller slice (the first problem of each domain, 60 trials per cell) is what the
pilot used, and its paired intervals were 8 to 12 points wide on each side. That is too
wide to say "unchanged", so the full size is recommended.

**GPU time**, from the stored `duration_s` of the Part C unaided trials
(`results/delivered-rerun/slurm_vllm_*_off_no-tools_delivered-rerun/trials.jsonl`).
The stored value is the time of one request while four run at once, so wall time is
the sum divided by four.

| model | solve, 300 trials (sum of trial time) | simulate, 300 trials | wall time for one cell | wall time for O + A + B |
|---|---|---|---|---|
| Qwen3.5-9B | 6.79 h | 5.73 h | 3.1 h | 9.4 h |
| Gemma-26B | 2.17 h | 2.72 h | 1.2 h | 3.7 h |
| Qwen3.6-35B | 2.84 h | 2.34 h | 1.3 h | 3.9 h |
| total | | | 5.7 h | **17.0 h** |

With model loading at the start of each job, call it **about 19 GPU-hours** for the
recommended design and about 13 for O + B. This assumes the same load as Part C. Queue
waiting is on top and is not predictable. For scale, the whole rerun was 47,040 trials
in about a week (`reference/weakness_action_plan.md`); this is 5,400.

**GPU class.** Each of the three models fits one `rtx_6000` (48 GB), the submit
wrapper's default class (`cluster-experimenting/lib/defaults.sh`: the 9B about 18 GB of
weights, Gemma peaking at about 85% of the card, the 35B about 17 GB on disk). Each
model runs alone on its card. The class's limits apply: `--mem=48G` and no
`--cpus-per-task` (`.claude/skills/cluster-ops/SKILL.md`, "GPU class";
`submit_with_rtx.sh`, "Resource policy"). `--time` is set at submit and cannot be
raised later.

---

## 5. Endpoints and readings, written before any data

**The measure.** Delivered right by the frozen delivered grader
(`tools/delivered_rerun/grade.py`, unchanged), per model and task, over the three
wordings together (n = 300). Intervals are 95% domain-cluster bootstrap intervals over
the 20 domains, with the resample count and seed fixed in the prereg.

**The contrasts.** Paired on the trial key, in points:

- primary: **A minus O**, per model and task (6 contrasts);
- secondary: **B minus O**, per model and task (6 contrasts);
- drift check: **O minus Part C**, per model and task.

**A second reading, registered beside the first.** Section 0 shows that the frozen
grader misses the commonest layout under the old prompt. A prompt that changes the
layout therefore changes the frozen grade even if the content is the same. So each
contrast is also reported under a layout-tolerant reader, fixed in the prereg before
any data: on solve the plan in the last code block when that block holds a plan
(`block_plan` of `tools/reanalysis/rq1_layout_regrade.py`, the reader of the filed
re-grade, with new plans validated in process on pddl-pyvalidator 0.1.5), on simulate
the RQ3 line reader. The frozen grade answers
"did the baseline, as the paper measures it, move". The tolerant reading answers "did
the content move". Both are reported; neither replaces the other.

**The readings.** M is a margin in points, **a threshold to be chosen by Omer**
(section 9). The rerun used 5 points for its own parity check (`constants.py`,
`MARGIN`). For each contrast:

- **criterion met**: the whole 95% interval lies inside [-M, +M];
- **a difference is shown**: the interval excludes 0;
- **unresolved**: neither of the above.

A contrast can meet the criterion and show a difference at once (a small, real shift).
With 20 domains the interval for A minus O may be wider than a 5-point margin allows,
and then the honest reading is "unresolved", not "unchanged".

**The reporting rule (Omer, 2026-11-23; it replaces the sentence struck below and goes
into the registration before any data is read).** Cell B is the no-tools baseline the
paper reports on solve and simulate. Cell O is the anchor for the paired contrasts and
for the drift check against Part C. Part C stays in the appendix as the registered
record, with a short note on why it was run again. Both the frozen grade and the
layout-tolerant reading are registered for every contrast. The control is still a new
condition: its rows are never pooled with Part C or with the main sweep. The five
readings below say what the contrasts mean; where they speak of quoting the control
"beside Part C", read them with this rule.

**What each outcome would mean for the paper.** Written now, so the result cannot
choose its own reading. ~~In every case Part C stays in the paper as the registered
baseline, and the control is one short paragraph and one appendix table beside it.~~

1. **Baseline unchanged (criterion met on both tasks, A and B, by the frozen grade).**
   The Limitations sentence "what a corrected prompt would have produced is unmeasured"
   is replaced by the measured statement and its margin. RQ1 keeps its figures.
2. **Baseline rises on simulate only.** RQ1's simulate comparison quotes the control
   baseline beside Part C's. This matters most where the unaided arm is already close
   to or above the tool arm: Gemma's unaided simulate (24.0%) is above its tool arm
   (8.3%), and for the two Qwen models the tool arm's lead is 8.0 and 10.7 points
   (`delivered_rerun_readout.md`, E2). Solve is reported as unchanged or unresolved.
3. **Baseline rises on both tasks.** Every RQ1 sentence that sets a tool-arm rate
   against an unaided solve or simulate rate quotes both baselines, including the
   abstract's "21 to 29% without". The direction of the solve result is not at risk in
   any plausible case: the tool arms deliver 77.0 to 92.3% on solve (same E2 table),
   and the scoping count of section 0 puts the best reading of today's unaided answers
   at 40 to 52%.
4. **Baseline falls.** Reported as it is. It would mean the pointer, wrong as it was,
   did not cost the models anything on that task.
5. **The frozen grade moves and the tolerant reading does not.** The effect is layout
   only: the wrong description changed how answers were written, and the grader's
   reading did the rest. The paper says so, and the re-grade of step 0 is the figure
   that carries the point.

If the drift check fails (O is outside the margin of Part C), readings 1 to 5 still
apply to the contrasts, and the paper adds one sentence that the control's levels are
not comparable with Part C's.

---

## 6. What has to be built

**Step 0 is done (2026-11-23, PR #146, merged).** The script is
`tools/reanalysis/rq1_layout_regrade.py`; its figures are in `NUMBERS.md`, "RQ1 solve
and simulate, layout-tolerant re-grade of both arms"; a second agent reviewed the code
and read answers in full. The control's second reading reuses its `block_plan` reader
and its in-process validator route (pddl-pyvalidator 0.1.5, the readout's release; the
script halts on another release and first checks that the route returns the stored
verdict of every plan the frozen grade used). The step as it was proposed:

**Step 0. The re-grade of stored answers (no run).** A script in `tools/reanalysis/`
that keeps every frozen grade and adds the layout-tolerant reading beside it, for the
unaided arm and, with the same reader, for the tool arms, so the RQ1 contrast is read
the same way on both sides. It follows `rq3_simulate_regrade.py`: the frozen column
must reproduce the filed cells or the script halts; plans are validated with the same
validator version the frozen readout used; the output is marked post hoc and goes into
`NUMBERS.md` beside the frozen figures. This is a new analysis of old data, which the
current rules allow. It is worth doing whether or not the run happens.

**Step 1. The harness change.** Additive and opt-in. `run_experiment.py`, `prompts.py`,
`runner.py` and every other file in the frozen hash stay byte-identical (section 0, b).

- A new module, for example `pddl_eval/control_prompts.py`, holds the A and B texts.
- `pddl_eval/vllm_client.py` reads a new variable, `$PDDL_NO_TOOLS_SYSTEM`, the same
  way it reads `$PDDL_JSON_CONSTRAINT` today. Unset, the request is today's request.
  Set to `no-pointer` or `format-stated`, the client swaps the system message for the
  matching text, and only when the message it was given is exactly today's solve or
  simulate text. Anything else is an error, so the swap cannot touch a tool arm, a
  validation task or a prompt it does not know.
- `submit_with_rtx.sh` and the sbatch get two new cell names, for example
  `no-tools-syspointer-off` and `no-tools-sysformat`, each with its own output folder,
  as `no-tools-jsonbound` has. The sbatch sets the variable only for those cells.
- Tests: the default request is unchanged byte for byte; the package hash still ends in
  `822aace9…`; the user message is identical in all three cells; the swap fails closed.
- One branch, one PR, Omer merges.

An alternative that also leaves the hashed files alone is a small wrapper entry point
that swaps the dictionary entry in memory and then calls `run_experiment.main()`. The
client route is recommended because it reuses a pattern that is already reviewed and
already wired into the sbatch.

**Order changed (Omer, 2026-11-23): the registration and the freeze come before the
smoke.** The work order is: 1 the harness change; 2 the registration and the
`/freeze-protocol` gate, with the hash recorded before the full run's data is read; 3
the smoke; 4 the full run, only after the smoke passes and the freeze is recorded; 5
sync, the frozen analysis, a readout and a `NUMBERS.md` entry. The two paragraphs below
keep their old numbers.

**Step 2. The smoke.** The full-run SLURM profile (same GPU, memory and `--time`), a
few trials per cell and model. It must check: answers are non-empty in every cell; the
system text sent in each cell is the registered one; the O cell's request is today's;
the serve log shows vLLM 0.20.2; the frozen loader reads the rows; no exception rows.
Needs Omer's cluster go-ahead.

**Step 3. A short prereg and the freeze.** `development/reference/control_prompt_fix_prereg.md`:
the cells and the sha256 of each prompt text, the sizes, the measure, the pairing key,
the bootstrap settings, the margin M, the tolerant reader's exact rule, the readings of
section 5, the drift check, the void rules of the rerun (more than 1% unpaired rows or
exception rows), and what is not claimed. Then `/freeze-protocol`: the typed loader
(the rerun's `schema.parse_row`, reused as the pilot script does), the constants as
asserts, the clause-by-clause map, a synthetic fixture with hand-computed answers, and
an independent review. The hash is taken before the full run's data is read.

**Step 4. The analysis script.** `tools/reanalysis/control_prompt_fix.py`, built from
the pilot script on branch `analysis/json-constraint-pilot`
(`tools/reanalysis/json_constraint_pilot.py`): it already pairs two cells on the trial
key, grades with the frozen grader, validates new plans live and prints the rerun's
grade on the same keys. It needs a third cell, the tolerant reader and the readings.

---

## 7. Timeline

Today is Monday 2026-11-23. Abstract: Monday 2026-12-07. Paper: Monday 2026-12-14.
The dates below assume nothing fails and the queue is kind.

| dates | step | Omer's part |
|---|---|---|
| Mon 11-23 to Tue 11-24 | decision on this plan; step 0 starts on a yes to item 1 of section 9 | answer section 9 |
| Tue 11-24 to Thu 11-26 | step 0 done and read; harness change with tests; prereg draft; analysis script on the fixture | merge one PR |
| Thu 11-26 to Fri 11-27 | smoke, three models, three cells | cluster go-ahead |
| Fri 11-27 to Sun 11-29 | freeze gates, independent review, hash recorded | read the prereg |
| Sun 11-29 to Tue 12-01 | the full run, about 19 GPU-hours plus queue | cluster go-ahead |
| Wed 12-02 | sync, frozen analysis, readout, `NUMBERS.md` entry | read the readout |
| Thu 12-03 to Fri 12-04 | paper edit on a short branch, PR | read and merge |
| Mon 12-07 | abstract | |
| Mon 12-14 | paper | |

**The latest go-ahead that still fits.** From a yes to a readout is about nine days
when nothing fails. Add two days for one cluster failure and two for the paper edit and
Omer's read.

- For the control to be in the paper on 12-14: a go-ahead by **Monday 2026-11-30**.
- For it to inform the abstract on 12-07: a go-ahead by **Wednesday 2026-11-25**, with
  no slack. The abstract quotes the unaided solve figure, so this date matters.
- After 11-30 the control can still run, as an addition after submission.

Step 0 does not depend on any of this. It can be finished this week.

---

## 8. Risks and limits

- **A new condition.** The control never replaces Part C and is never pooled with it.
  It has its own prereg and its own cell names, and the paper reports it beside Part C.
- **It runs against a standing decision.** "No new runs" was decided on 2026-11-22.
  This plan asks for an exception of 5,400 trials. That is Omer's and his advisors' call.
- **The grader's blind spot cuts both ways.** Cell B asks for a layout the frozen
  grader reads. So B minus O by the frozen grade is partly a statement about the grader,
  by construction. This is why the tolerant reading is registered beside it.
- **The frozen readers take action-shaped lines from anywhere in an answer.** A model
  that lists steps while reasoning and then gives its plan can be graded on both
  together. The tolerant reader has to be defined with this in mind, in the prereg.
- **Validator version.** The frozen readout graded plans with pddl-pyvalidator 0.1.5;
  the laptop's plugin now has 0.1.6. The prereg must name one version for all three
  cells and for the drift check. *(2026-11-23: it is 0.1.5, through the in-process
  route of the filed re-grade.)*
- **The Claude runs are not covered.** They asked for the format differently: on solve
  through the provider's structured-output setting with a schema, and on simulate
  through one added sentence that states the outer wrapper
  (`tools/_claude_api_common.py`, `format_for`). So the Claude unaided arm did not
  carry this flaw, and the open and Claude unaided baselines were not obtained under
  the same instruction. The paper's appendix already states the difference.
- **Thinking off only, three models, two tasks.** The validation tasks are left out
  because their prompts never held the pointer.
- **An "unresolved" result is likely for some contrasts**, with 20 domains.
- **Time.** The run sits inside the three weeks before the deadline, with Omer's read of
  the whole paper still open.

**If the control is not run.** The paper keeps its present disclosure (Methods and
Limitations): the constraint never took effect, the solve and simulate prompts pointed
to a schema the model never received, and what a corrected prompt would give is
unmeasured. With step 0 done it can add, beside the frozen figures, how much of the
unaided failure on solve and simulate is an answer the grader did not read. The content
question then stays open and is named as a limit.

---

## 9. Decisions for Omer

1. **The re-grade of stored answers (step 0, no run).** Do it now? Recommended: yes. It
   is allowed under the current decision and section 0 says it will move the unaided
   solve baseline a great deal.

> ANSWER: yes (2026-11-23). Done the same day: PR #146, `tools/reanalysis/rq1_layout_regrade.py`.

2. **The control run.** Run it, as an exception to "No new runs"? Recommended: yes, if
   the go-ahead comes by 2026-11-30; otherwise leave it for after submission.

> ANSWER: yes, run it (2026-11-23), as an exception to "No new runs". Go-ahead dates stand: 2026-11-30 for the paper, 2026-11-25 if the abstract is to quote the new baseline.

3. **One corrected cell or two.** O + A + B (recommended, 5,400 trials, about 19
   GPU-hours), or O + B only (3,600 trials, about 13 GPU-hours)?

> ANSWER: O + A + B. 5,400 trials.

4. **The prompt wording** of cells A and B in section 2. Accept, or edit? In particular:
   B on solve asks for lines and not for JSON.

> ANSWER: as written in section 2.

5. **The margin M** for "criterion met" (the rerun used 5 points).

> ANSWER: 5 points.

6. **Models.** All three headline models (recommended), or fewer?

> ANSWER: all three: Qwen3.5-9B, Gemma-26B, Qwen3.6-35B. Thinking off.

7. **Validation tasks.** Left out (recommended; their prompts never held the pointer),
   or add validate_plan as a check that a cell with no prompt change does not move?

> ANSWER: left out. Solve and simulate only.

8. **Cluster go-ahead.** One for the smoke and one for the full run, each asked for
   when its turn comes. Nothing touches the cluster before that.

> ANSWER: one explicit go-ahead before every SSH or SLURM action, the smoke and the full run separately.

9. **How the paper reports the control** (added 2026-11-23, after the plan was written).

> ANSWER: cell B is the no-tools baseline the paper reports on solve and simulate. Cell
> O is the anchor for the paired contrasts and for the drift check against Part C. Part
> C stays in the appendix as the registered record, with a short note on why it was run
> again. Both the frozen grade and the layout-tolerant reading are registered for every
> contrast. This rule is written into the registration before any data is read. No
> paper edit before Omer has read the readout.

---

## Appendix A. Where each number comes from

| number | source |
|---|---|
| Current system and user prompt texts | `pddl_eval/prompts.py` (`WITHOUT_TOOLS_SYSTEM_BY_TASK`; solve and simulate v11 to v13 at the end of the file) |
| The schema and the outer `trajectory` wrapper | `pddl_eval/schemas.py` (`SolveResponse`, `SimulateResponse`) |
| How the schema is sent, and that 0.20.2 drops it | `pddl_eval/runner.py` (`format=TASK_SCHEMAS.get(task)`), `pddl_eval/vllm_client.py` lines 197 to 214 and 296 to 299, `reference/d1_smokes_20261027.md` section D1d |
| Part C design: 300 solve and 300 simulate trials per model, wordings 11 to 13, the three model ids, 16,384 window, 65,536 storage, margin 5.0 | `tools/delivered_rerun/constants.py` |
| Unaided delivered, frozen: solve 21.3 / 24.3 / 25.3; simulate 24.0 / 9.3 / 17.7 (Gemma / 9B / 35B); tool arm solve 77.0 to 92.3; simulate tool arm 8.3 / 17.3 / 28.3 | `reference/delivered_rerun_readout.md`, table E2 |
| Same-trial gap between the main sweep and Part C on unaided solve: 0.0 to +2.0 | same file, "Part C parity" |
| Unaided delivered by wording (solve v12 32 to 42% against 16 to 22% for v11 and v13) | `NUMBERS.md`, table S2-W |
| Pilot: 25.0 against 31.7 on the same 60 solve trials; paired intervals at n = 60 | `git show analysis/json-constraint-pilot:tools/reanalysis/out/json_constraint_pilot.md` |
| Run-time failure reasons (checked, equal to the brief): solve `format_parse_fail` 173 / 192 / 217 of 300 (9B / Gemma / 35B); simulate `format_parse_fail` 37 / 88 / 84; simulate `truncated_no_answer` 108 / 82 / 67 | `results/delivered-rerun/slurm_vllm_*_off_no-tools_delivered-rerun/trials.jsonl`, field `failure_reason` (main checkout; `results/` is not in git) |
| Trial durations and GPU hours | same files, field `duration_s`, summed per model and task and divided by 4 |
| Output caps, temperature, concurrency | `pddl_eval/runner.py` (`DEFAULT_NUM_PREDICT`), `pddl_eval/chat.py` (`TEMPERATURE`), `run_condition_vllm_rtx.sbatch` (`CONCURRENCY`) |
| GPU class per model | `cluster-experimenting/lib/defaults.sh` (`vllm_lookup`) |
| Files in the frozen hash; the hash value | `tools/delivered_rerun/run.py` (`DEPENDENCIES`); `python -m tools.delivered_rerun.run --print-package-hash` |
| The Claude format mechanism | `tools/_claude_api_common.py` (`SIMULATE_JSON_DIRECTIVE`, `format_for`) |

**The scoping counts of section 0** are not filed figures. The rule:

- Rows: Part C solve and simulate rows of the three models, read through
  `tools.delivered_rerun.schema.parse_row` with `spec_rerun_c`.
- Frozen column: `tools.delivered_rerun.grade.grade`, with the answer key
  `results/derived/gt_cache.json` and the stored verdicts
  `results/delivered-rerun-secondary/plan_verdicts.json`.
- Solve, last code block: the last fenced block of the answer
  (`tools.e2e_regrade._FENCED_BLOCK_RE`); if it parses as JSON and is a non-empty list
  of strings, or an object whose `plan` is one, that list is the plan (whitespace
  collapsed, nothing else changed) and it replaces the frozen reading; otherwise the
  frozen grade stands. Plans with no stored verdict (302) were validated with
  `tools.delivered_rerun.run.live_verdicts` against the sibling repo at `e428f17`
  (pddl-pyvalidator 0.1.6).
- Simulate, line reader: `tools.reanalysis.rq3_context_pilot.line_reader_exact`.
- The scratch scripts and their output are in the shared notes folder of the sessions
  that produced this plan (`control-prompt-fix-scoping/`), outside the repository. Step
  0 replaces them with a reviewed script.
