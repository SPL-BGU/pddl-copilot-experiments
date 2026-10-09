# Re-analysis of stored transcripts (2026-10-02)

Local, read-only pass over the stored results. No cluster, no API calls, no spend, no
edits to `paper/` or to any tracked file. It answers three questions raised in
`weakness_consolidated.md` (C3, C5). Scripts are in `tools/reanalysis/`
(`q1_budget_probe_residual.py`, `q2_gemma_nocall.py`, `q3_truncated_tool_arms.py`,
helper `transcripts_common.py`). Commands are at the end.

Intervals in square brackets are Wilson 95%. Angle brackets `<low, high>` are censoring
bounds, as in `NUMBERS.md`.

## What we found

1. **The 64K probe residual is mostly about the answer format, and the two models fail
   differently.** All 65 residual failures were classified (Sonnet 30 of 100, Haiku 35 of
   100; the probe is the simulate task only).
   - Sonnet: 11 answers hold the complete, correct trajectory but in markdown tables or
     plain code blocks instead of JSON. 8 more are correct in every value they give but
     leave out numeric fluents that never change. 10 are deliberately shortened. Only 1
     has a wrong fact.
   - Haiku: 13 answers restate the whole trajectory with wrong facts (it keeps facts the
     tool had marked false, such as `handempty` after a pick-up). 14 are summaries or
     shortened answers. 4 never had a usable result (2 no final answer, 2 where Haiku
     dropped an action when copying the plan into the tool call).
   - In every one of the 61 trials that had a correct tool result and a final answer,
     the tool output was right and the final answer differs from it. So the residual is a
     restating problem, never a tool problem.
2. **Gemma no-call trials: no sign of an unrecognised tool call, as far as the data
   reach.** All 2,378 stored answers are exactly 500 characters, the start of a prose
   walk-through of the plan. None is empty, none shows tool-call syntax, none even names
   the tool: 0 of 2,378 [0.0, 0.2]. The method can see such attempts: the same stack left
   15 raw tool-call fragments in other Gemma answers, all inside the first 500
   characters. What comes after character 500 cannot be seen. Two things narrow it: 36
   to 54% of the answers are too short to contain a full call, and in the full-storage
   rerun (thinking on, outside the canonical corpus) 0 of 1,981 fully stored no-call
   answers contain one.
3. **"Truncated" tool-arm trials are not the model writing until the cap. The final
   turn was never run.** These trials have an empty stored answer. The harness refused
   to send the last request because the conversation plus the full output allowance did
   not fit the 16,384-token window, and its retry could not shrink the allowance enough.
   It then recorded an empty answer marked "length". This is proven exactly for 332 of
   332 trials where it can be checked, and by a token-count argument for 95% of all
   1,987. On validate_plan the model still had about 5,400 tokens of room (estimate) and
   needed about ten. Looping does exist but is small: in 70 of 1,987 trials an earlier
   tool call ran into the output cap, mostly Qwen3.5 9B repeating `increment c2`.
4. **The solve gap does grow with plan length inside the task, but for storage and
   harness reasons.** Longer plans mean more refused final turns and more answers that
   overflow the 500-character snapshot. Among the answers that could be graded at all,
   Qwen3.5 9B is right in 161 of 161 and Qwen3.6 35B in 88 of 90.
5. **New: Gemma's low delivered solve rate is mostly a grading artifact.** 198 of the
   200 Gemma solve answers graded "wrong plan" are the tool's own plan, word for word,
   behind a leaked markup prefix (`<|channel>thought\n<channel|>`) that makes the grader
   drop the first action.

Every frozen number that was checked reproduces (list in the next section). Items 3 and
5 contradict how the paper and the weakness list describe those trials.

## Checks against NUMBERS.md and the paper

| what | frozen value | recomputed | status |
|---|---|---|---|
| probe, delivered at 64K, Sonnet with / without tools | 70 [60.4, 78.1] / 44 [34.7, 53.8] | 70/100, 44/100, same intervals | matches |
| probe, delivered at 64K, Haiku with / without tools | 65 [55.3, 73.6] / 58 [48.2, 67.2] | 65/100, 58/100, same intervals | matches |
| probe, tool-arm final turns at 64,000 | 0 both (no-tools: 1 Sonnet, 2 Haiku) | 0 and 0 (1 and 2) | matches |
| probe failure reasons | Sonnet 17 mismatch + 13 parse fail; Haiku 19 + 14 + 2 empty | same | matches |
| Gemma validate_plan, plain, called the tool | 622/3000 = 20.7% | 622/3000 [19.3, 22.2] | matches |
| same, steered | 2808/3000 = 93.6% | 2808/3000 [92.7, 94.4] | matches |
| correct when it calls; successes without a call | 617/622; 0 | 617/622 [98.1, 99.7]; 0 | matches |
| plain = variants 11-13, steered = 14-16 | as stated in the brief | `pddl_eval/prompts.py`: `ACTIVE_PROMPT_VARIANTS`, `STEERED_VARIANTS = {14, 15, 16}` | confirmed in code |
| "truncated" band of `failure_taxonomy.pdf` (read off the bars in C5 as 37 / 34% and 7 / 8%) | not in NUMBERS.md | solve 336/900 = 37.3%, 302/900 = 33.6%; validate_plan 625/9000 = 6.9%, 724/9000 = 8.0% | matches the bars |
| Gemma solve delivered "at most 35.3"; 9B "26.0 to 58.7" | paper text | Gemma plain `<14.3, 35.3>`; 9B plain `<26.0, 58.7>` | matches |

Points that contradict the current wording:

- **Figure caption for `failure_taxonomy.pdf`: "truncated (the budget ran out with no
  answer)".** For the tool arms the model did not run out while answering. The harness
  never sent the final request (section 3). The same applies to the reading in
  `reference/tool_call_vs_final_output_grading.md` ("tool loops consume the token budget
  and the model never reports the answer") and to C5 in the weakness list ("a model that
  holds the answer and still writes until the cap suggests looping").
- **Gemma delivered solve "at most 35.3".** The number reproduces, but 120 of the 121
  plain-arm answers graded as an invalid plan are the tool's valid plan behind a markup
  prefix (section 3.5). With those counted, the plain-arm bound would be `<54.3, 75.3>`
  and the steered `<49.7, 85.3>`. This is a diagnostic, not a re-grade. It also means
  Gemma's part of the "wrong content" band on the solve tool arms in the same figure is
  this artifact.
- **Reviewer argument R in C5 ("open models lose far more between the two scores").**
  For the open models the loss is made of refused final turns, 500-character storage
  and the Gemma prefix. The stored data do not show open models getting a plan wrong
  when restating it.
- **C3: "In the logs that looks the same as not calling."** Not quite. An unrecognised
  call stays in the answer text, and it was visible in every case found (section 2.4).

## 1. The 64K budget-probe residual

Data: `results/{sonnet,haiku}-frontier/sweep5v2-with-tools-budget64k/trials.jsonl`
(full answers, up to 262,144 characters; tool results stored in full), graded by the
overlay `results/derived/e2e_overlay/{sonnet,haiku}-frontier/sweep5v2-with-tools-budget64k.e2e.jsonl`,
field `e2e_strict`. Oracle: `results/derived/gt_cache.json`. One task (simulate), one
prompt (variant 11), n = 100 per model. No row is censored.

How delivered is graded for simulate (`tools/e2e_regrade.py`): the answer must contain
the trajectory as JSON (the whole answer, one fenced block, or one fenced block per
step), and after normalising notation it must equal the oracle exactly: same steps,
same action, same set of true facts, same numeric fluents with the same values.

### 1.1 Categories

Each residual row gets exactly one category. The order below is the decision order
(first match wins). Categories were defined after reading all 65 answers.

| category | meaning |
|---|---|
| NO_FINAL_ANSWER | the final message is empty |
| TOOL_INPUT_ERROR | the tool's own trajectory is not the oracle's, because the model changed the plan when calling the tool |
| SUMMARY_ONLY | prose or a list of changes; states are written out for fewer than half of the steps |
| ABRIDGED | the trajectory is restated but openly shortened: steps skipped, a state replaced by a placeholder, or each step listing only what changed |
| WRONG_WRAPPER | every step has its full state, but not as JSON (markdown tables, plain code blocks, several JSON objects in one block) |
| NUMERIC_OMITTED | valid JSON, every step, actions and facts all right, every number given is right, but some numeric fluents are missing |
| WRONG_FACTS | valid JSON, every step, full states, but some facts differ from the tool's output |

### 1.2 Counts (task = simulate, n = 100 per model)

| category | Sonnet 4.6 | Haiku 4.5 | both (n = 200) |
|---|---|---|---|
| NO_FINAL_ANSWER | 0 [0.0, 3.7] | 2 [0.6, 7.0] | 2 = 1.0% [0.3, 3.6] |
| TOOL_INPUT_ERROR | 0 [0.0, 3.7] | 2 [0.6, 7.0] | 2 = 1.0% [0.3, 3.6] |
| SUMMARY_ONLY | 0 [0.0, 3.7] | 9 [4.8, 16.2] | 9 = 4.5% [2.4, 8.3] |
| ABRIDGED | 10 [5.5, 17.4] | 5 [2.2, 11.2] | 15 = 7.5% [4.6, 12.0] |
| WRONG_WRAPPER | 11 [6.3, 18.6] | 0 [0.0, 3.7] | 11 = 5.5% [3.1, 9.6] |
| NUMERIC_OMITTED | 8 [4.1, 15.0] | 4 [1.6, 9.8] | 12 = 6.0% [3.5, 10.2] |
| WRONG_FACTS | 1 [0.2, 5.4] | 13 [7.8, 21.0] | 14 = 7.0% [4.2, 11.4] |
| **all residual** | **30 [21.9, 39.6]** | **35 [26.4, 44.7]** | **65 = 32.5% [26.4, 39.3]** |

Counts are also percentages because n = 100.

How the categories line up with the overlay's own labels:

| overlay reason | Sonnet | Haiku |
|---|---|---|
| `trajectory_mismatch` (17 / 19) | 8 ABRIDGED, 8 NUMERIC_OMITTED, 1 WRONG_FACTS | 13 WRONG_FACTS, 4 NUMERIC_OMITTED, 2 ABRIDGED |
| `format_parse_fail` (13 / 14) | 11 WRONG_WRAPPER, 2 ABRIDGED | 9 SUMMARY_ONLY, 3 ABRIDGED, 2 TOOL_INPUT_ERROR |
| `truncated_empty` (0 / 2) | none | 2 NO_FINAL_ANSWER |

Details per category:

- **WRONG_WRAPPER (Sonnet 11).** 8 use one markdown table or code block per step, 2
  use one wide table (step, action, one column per fluent), 1 puts one JSON object per
  line in a single block. A loose reader written for this check (`loose_steps` in the
  script, a diagnostic and not a grader) finds that **all 11 equal the oracle exactly**:
  every step, action, fact and number.
- **NUMERIC_OMITTED (12).** In all 12, every missing fluent but one never changes during
  the plan (grid coordinates and bounds in drone, item weights and load limits in
  delivery, distances and burn rates in zenotravel). Every number that is given is
  right. Domains: drone 7, zenotravel-numeric 3, delivery 2. The prompt says
  "`state.numeric` is the fluents map", which does not say whether constants must be
  repeated.
- **ABRIDGED (15).** Steps skipped: Sonnet 4, Haiku 4 (in 3 of the Haiku rows the `...`
  also makes the JSON invalid). State replaced by a placeholder string: Sonnet 4, Haiku
  1. Each step given only as changes from the previous one: Sonnet 2.
- **SUMMARY_ONLY (Haiku 9).** Answers of 931 to 2,408 characters for oracles of 23 to 60
  steps. This is the "DECLINE" group of the frozen readout; it did not convert at 64K
  there either (0 of 14).
- **WRONG_FACTS (Haiku 13, Sonnet 1).** All steps and actions are right. The states are
  wrong in 1 to 18 steps. Of the 60 extra facts across the Haiku rows, 59 are facts the
  tool reported as false at that step. The model had to turn the tool's true/false map
  into a list of true facts, and kept stale ones.
- **TOOL_INPUT_ERROR (Haiku 2, counters p01 and p05).** Haiku dropped one action when
  it copied a long, repetitive plan into the tool call (72 actions sent for 73; 55 for
  56). The tool then correctly reported the shortened plan as not reaching the goal.
  The final answers are also summaries.
- **NO_FINAL_ANSWER (Haiku 2).** depot/p01: after a second full tool call the
  conversation was 503,067 tokens and the API refused it. satellite/p03: nine calls in
  a row with the `problem` and `plan` arguments missing, then the 10-turn loop limit.

One way to read the residual:

| reading | Sonnet | Haiku |
|---|---|---|
| complete and correct content, only the wrapper is wrong | 11 | 0 |
| correct, but leaves out constant numeric fluents | 8 | 4 |
| the model chose not to restate the whole trajectory (ABRIDGED + SUMMARY_ONLY) | 10 | 14 |
| restated in full, with wrong facts | 1 | 13 |
| no usable tool result, or no answer | 0 | 4 |

So if the grader accepted non-JSON wrappers, Sonnet would read 81 of 100, and 89 if
it also accepted the omission of constants. Haiku would read 65 and 69. These are
what-if readings to size the effect. They are not delivered rates and must not be
quoted as such.

### 1.3 Verbatim examples

WRONG_WRAPPER, Sonnet, parking/p01 (content equals the oracle):

```
### Step 1 — `(move-car-to-car car_1 car_2 car_0)`
car_1 moves from behind car_2 to behind car_0. car_2 becomes clear; car_0 is no longer clear.

| Boolean Predicates |
|---|
| `(at-curb car_0)` |
| `(at-curb car_2)` |
```

WRONG_WRAPPER, Sonnet, counters/p05 (one wide table, content equals the oracle):

```
| Step | Action | `value(c0)` | `value(c1)` | `value(c2)` | `rate_value(c0)` | `rate_value(c1)` | `rate_value(c2)` | `max_int` |
| **0** | *(initial)* | 20 | 88 | 34 | 0 | 0 | 0 | 100 |
| **1** | `(increase_rate c2)` | 20 | 88 | 34 | 0 | 0 | **1** | 100 |
```

WRONG_WRAPPER, Sonnet, gardening/p04 (several JSON objects in one block, so the block is
not one JSON value):

```
{"step": 0, "action": "", "state": {"boolean": [], "numeric": {"max_int": 20, "maxx": 8, ...
{"step": 1, "action": "(move_down_left agent1)", "state": {"boolean": [], "numeric": {"max_int": 20, ...
```

(The two `...` above are mine, to shorten the lines.)

NUMERIC_OMITTED, Sonnet, drone/p02. The oracle also has `min_x`, `max_x`, ..., and
`xl`, `yl`, `zl` for every location (18 fluents that never change):

```
      "boolean": [],
      "numeric": {
        "x": 0, "y": 0, "z": 0,
        "battery-level": 13,
        "battery-level-full": 13
      }
```

ABRIDGED, Sonnet, farmland/p01 (placeholder inside a valid JSON list):

```
    "step": 1,
    "action": "(move-slow farm4 farm0)",
    "state": {
      "boolean": ["... same adj facts as step 0 ..."],
```

ABRIDGED, Haiku, barman/p05 (steps skipped; the line also breaks the JSON):

```
      "numeric": {}
    }
  },
  ... [64 more steps] ...
  {
    "step": 65,
```

ABRIDGED, Sonnet, depots/p05 (each step given only as changes):

```
### Step 1 — `(lift hoist1 crate3 pallet1 depot1)`
**Changes:** `crate3` lifted off `pallet1`; `pallet1` becomes clear; `hoist1` busy.
**State adds:** `(lifting hoist1 crate3)`, `(clear pallet1)`
**State removes:** `(at crate3 depot1)`, `(on crate3 pallet1)`, `(clear crate3)`, `(available hoist1)`
```

SUMMARY_ONLY, Haiku, tpp/p05:

```
The simulation shows that the plan is **VALID** and successfully reaches the goal state. The trajectory contains 37 steps (step 0 through step 36), where:

- **Step 0** is the initial state with all predicates from the problem definition
- **Steps 1-36** show the state after each action is executed
```

and its last line: `The complete trajectory with all boolean and numeric fluents for
each step has been computed and is available in the response above.`

SUMMARY_ONLY, Haiku, barman/p03:

```
**Steps 1-4:** Prepare cocktail2 ingredients
- Grasp shot1, fill with ingredient3, pour into shaker1, clean shot1
```

WRONG_FACTS, Haiku, blocksworld/p02 (`handempty` is false after `pick_up`; the tool said
so):

```
    "step": 1,
    "action": "(pick_up b3)",
    "state": {
      "boolean": [
        "(handempty)",
        "(ontable b1)",
        "(ontable b2)",
        "(clear b1)",
        "(clear b2)",
        "(holding b3)"
```

WRONG_FACTS, Sonnet, depot/p03, step 9 (`on crate1 pallet0` is kept while the hoist is
lifting crate1; the only wrong fact in the whole 16-step answer):

```
  "action": "(lift hoist0 crate1 pallet0 depot0)",
  ...
      "(on crate1 pallet0)",
  ...
      "(lifting hoist0 crate1)",
      "(clear pallet0)"
```

TOOL_INPUT_ERROR, Haiku, counters/p05:

```
The plan executes all 55 actions successfully, but **fails to reach the goal state**.
...
The plan is **one action short** of satisfying the goal.
```

(The fixture plan has 56 actions and does reach the goal.)

NO_FINAL_ANSWER, Haiku, depot/p01, stored error:

```
Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'prompt is too long: 503067 tokens > 200000 maximum'}, ...
```

NO_FINAL_ANSWER, Haiku, satellite/p03, the tool result repeated nine times:

```
{"error": true, "errcode": "missing_required_arg", "tool": "get_state_transition", "missing": ["problem", "plan"], ...
```

## 2. Gemma no-call trials on validate_plan

Cell: `results/sweep5v2-live/slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal/trials.jsonl`
(thinking off). Plain arm, variants 11 to 13, n = 3,000. 622 called the tool, 2,378 made
no structured call at all, 0 called a different tool.

What "called" means here. The harness reads tool calls only from the structured
`tool_calls` field that the server returns (`pddl_eval/vllm_client.py`); the server's
`gemma4` parser fills it. The harness never looks for calls inside the text. A call the
server did not recognise would therefore stay inside the answer text.

### 2.1 What is stored, and how much can be seen

Fields per trial: `model, task, domain_name, problem_name, plan_label, prompt_variant,
with_tools, tool_filter, prompt_style, response, thinking, tool_calls, tokens,
duration_s, done_reason, truncated, failure_reason, success, tool_selected, error,
infra_failure`.

For the 2,378 no-call trials:

| item | value |
|---|---|
| `response` | exactly 500 characters in all 2,378 (the storage limit); the full answer was graded online but not kept |
| `thinking` | empty in all |
| `tool_calls` | empty in all |
| `error`, `infra_failure` | none |
| turns | 1 in all |
| `done_reason` | `stop` 2,357; `length` 21 |
| `failure_reason` | `tool_not_selected` in all |
| output tokens per answer | min 279, median 1,117, 95th percentile 2,364, max 6,144 (the cap) |

At about 2.7 characters per output token on this model (measured on 2,001 trials with a
complete short answer), 500 characters are about **16% of the median answer** (8% to 31%
for the middle 90% of trials). The first sixth is visible, the rest is not.

### 2.2 Counts from the visible 500 characters

One category per trial, first match wins.

| category | plain arm (n = 2,378) |
|---|---|
| empty | 0 [0.0, 0.2] |
| text that looks like a tool-call attempt | 0 [0.0, 0.2] |
| ran into the output cap (`done_reason = length`), visible part is prose | 21 = 0.9% [0.6, 1.3] |
| a verdict is visible in the first 500 characters | 0 [0.0, 0.2] |
| prose reasoning, the model ended the turn itself, verdict not visible | 2,357 = 99.1% [98.7, 99.4] |
| other | 0 [0.0, 0.2] |

The search for tool-call attempts was wide on purpose: Gemma's own call tokens
(`<|tool_call>`), any special-token markup, `call:name{`, the tool name used as a
function, JSON with a `name` / `arguments` key, code fences marked `json` or
`tool_code`, and `print(...)` wrappers. Zero hits on each. In addition, **none of the
2,378 answers contains the string `validate_plan` or the word "tool"**.

The answers all open the same way. 1,364 start "To determine if the plan is"; the rest
start "To validate the plan, we must / need / will ..." or "To check if the plan is".
Typical opening:

```
To determine if the plan is valid, we must trace the state transitions step-by-step based on the provided domain and problem definitions.

**Initial State:**
- `at plane1 city1`, `fuel-level plane1 fl1`
```

Whether these answers end with a verdict, and whether it is right, **cannot be
determined from stored data**: the verdict comes at the end and the end is not stored.
(The harness scores a no-call trial in a tool arm as failed without reading the text,
so the stored `success` says nothing about it either. This is why the cell's delivered
rate is the bound `<6.6, 99.6>` in `NUMBERS.md`.)

The same picture holds elsewhere in the canonical corpora:

| cell | no-call | tool-call-like text visible | ran into output cap | prose, ended itself |
|---|---|---|---|---|
| canonical, steered arm | 192 of 3,000 | 0 | 14 | 178 |
| anonymized twin (`sweep6-live`), plain arm | 2,456 of 3,000 | **4** = 0.2% [0.1, 0.4] | 8 | 2,444 |

### 2.3 Could the unseen part hold a tool call?

A `validate_plan` call has to carry the domain, the problem and the plan as arguments.
For 2,249 of the 2,378 trials the argument size is known, because another trial on the
same fixture did call the tool.

- In **810 of 2,249 = 36.0% [34.1, 38.0]** the whole answer has fewer tokens than the
  arguments alone would need, even at a generous 3.38 characters per token (the 99th
  percentile). At the median rate it is 1,210 of 2,249 = 53.8% [51.7, 55.9]. These
  answers cannot contain a complete call.
- For the other 1,439 (64.0%) a complete call would fit in the unseen text.
  **Cannot be determined from stored data.**
- The answers are about as long as the same model's answers with no tools at all on the
  same task and prompts (output tokens, quartiles: 871 / 1,117 / 1,472 against
  805 / 1,002 / 1,300, n = 3,000). That is what prose validation looks like.

### 2.4 Would we see an unrecognised call if there were one? Yes.

A scan of all 36,480 Gemma tool-arm rows (both canonical corpora, both reasoning modes,
all tasks, both arms) finds 15 answers with raw, unparsed tool-call text. So the stack
does leave such text in the answer, and the search finds it.

| where | n | position of the markup | what happened |
|---|---|---|---|
| `sweep6-live`, thinking off, validate_plan plain | 4 | character 0 | a first-turn call that ran into the 6,144-token output cap before it was closed (`done_reason = length`), so the server could not recognise it |
| `sweep5v2-live`, solve, thinking off (7) and on (1) | 8 | character 28 | after a successful planner call, a second call to `validate_plan` that the server left as text (`done_reason = stop`) |
| `sweep6-live`, validate_plan steered (1), solve thinking on (2) | 3 | characters 19, 248, 461 | same: a later call left as text |

Example (sweep6-live, plain arm, counters/p05):

```
<|tool_call>call:validate_plan{domain:<|"|>(define (domain tankyard)
    (:requirements :strips :typing :equality :adl :fluents)
```

Two things follow. First, the failure mode the reviewer has in mind is real in this
stack: 4 first-turn calls were lost in the anonymized plain arm, and 11 calls on a later
turn were left as text although the turn ended normally (why the server did not
recognise those 11 cannot be determined from stored data). Second, it is rare, and in all 15 cases the markup sits in
the first 500 characters, most often at the very start. In the canonical plain arm
there is none in 2,378.

### 2.5 Side check, outside the canonical corpus

`results/iss024d-e2e-live/slurm_vllm_gemma4_26b-a4b_on_tools_all_minimal_iss024d-e2e`
is the full-storage rerun: same model, same server parser, same prompts, but **thinking
on** and the reasoning parser off, with 16,384 characters stored. It is a different
apparatus (`NUMBERS.md`: "separate apparatus, within-corpus only"). It is used here only
as an illustration and is never pooled with the numbers above.

- Plain arm: 2,973 of 3,000 made no structured call.
- 1,981 of those are stored in full (shorter than 16,384 characters). Tool-call-like
  text anywhere: **0 of 1,981 [0.0, 0.2]**. Mentions of the tool or the word "tool":
  0 of 1,981. A `VERDICT:` line: 883 of 1,981 = 44.6% [42.4, 46.8].
- The other 992 are cut at 16,384 characters; nothing tool-like in the visible part.

### 2.6 Answer to the reviewer question

"Did the model try to call the tool in a format the server did not recognise?"

- In the stored part of the answer: **no**, 0 of 2,378 [0.0, 0.2]. All 2,378 open with
  prose reasoning about the plan and none refers to the tool.
- In at least 36% of the trials, not in the unseen part either (the answer is too short).
- For the remaining 64%, **cannot be determined from stored data**. Supporting, not
  proving: every unrecognised call found anywhere in the Gemma data starts within the
  first 500 characters; the answers have the length of unaided prose answers; the
  full-storage rerun has none in 1,981 complete answers.
- What would settle it: a rerun of this one cell (3,000 trials) with full answers
  stored. That is a new run, so it is outside this re-analysis.

## 3. Truncated tool-arm trials (Gemma 26B, Qwen3.5 9B, Qwen3.6 35B; thinking off)

Cells: `results/sweep5v2-live/slurm_vllm_{gemma4_26b-a4b,Qwen3_5_9B,qwen3_6_35b}_off_tools_all_minimal`,
joined to the overlay on the trial key. solve n = 300 per model and arm, validate_plan
n = 3,000.

Fields used. "Truncated" is the stored `truncated` flag, which is true when the last
chat turn ended with `done_reason = length` (`pddl_eval/runner.py`). The paper figure's
"truncated" band on tool arms is the overlay reason `truncated_empty`: empty final
answer and `done_reason` other than `stop`. Tool-verified is the overlay
`tool_verified` (the harness `success`: the tool's own result was right; the final text
is not read). Delivered is the overlay `e2e_strict`, with full-snapshot rows as
"indeterminate".

### 3.1 Share of trials that end truncated

| model | task | arm | truncated | empty answer after tool call(s) | prose cut at the output cap, no tool call | text cut after tool call(s) |
|---|---|---|---|---|---|---|
| Gemma 26B | solve | plain | 73/300 = 24.3% [19.8, 29.5] | 73 | 0 | 0 |
| Gemma 26B | solve | steered | 43/300 = 14.3% [10.8, 18.8] | 43 | 0 | 0 |
| Gemma 26B | validate_plan | plain | 34/3000 = 1.1% [0.8, 1.6] | 13 | 21 | 0 |
| Gemma 26B | validate_plan | steered | 160/3000 = 5.3% [4.6, 6.2] | 146 | 14 | 0 |
| Qwen3.5 9B | solve | plain | 124/300 = 41.3% [35.9, 47.0] | 124 | 0 | 0 |
| Qwen3.5 9B | solve | steered | 104/300 = 34.7% [29.5, 40.2] | 104 | 0 | 0 |
| Qwen3.5 9B | validate_plan | plain | 330/3000 = 11.0% [9.9, 12.2] | 329 | 0 | 1 |
| Qwen3.5 9B | validate_plan | steered | 290/3000 = 9.7% [8.7, 10.8] | 286 | 0 | 4 |
| Qwen3.6 35B | solve | plain | 160/300 = 53.3% [47.7, 58.9] | 139 | 21 | 0 |
| Qwen3.6 35B | solve | steered | 163/300 = 54.3% [48.7, 59.9] | 155 | 8 | 0 |
| Qwen3.6 35B | validate_plan | plain | 284/3000 = 9.5% [8.5, 10.6] | 283 | 1 | 0 |
| Qwen3.6 35B | validate_plan | steered | 292/3000 = 9.7% [8.7, 10.8] | 292 | 0 | 0 |
| pooled | solve | plain | 357/900 = 39.7% [36.5, 42.9] | 336 | 21 | 0 |
| pooled | solve | steered | 310/900 = 34.4% [31.4, 37.6] | 302 | 8 | 0 |
| pooled | validate_plan | plain | 648/9000 = 7.2% [6.7, 7.8] | 625 | 22 | 1 |
| pooled | validate_plan | steered | 742/9000 = 8.2% [7.7, 8.8] | 724 | 14 | 4 |

The "empty answer after tool call(s)" column is the figure's "truncated" band
(37.3 / 33.6 / 6.9 / 8.0%). In total 2,057 trials are truncated; 1,987 of them have an
empty answer after one or more tool calls.

### 3.2 What the stored snapshots show

| model | task | truncated | stored answer empty | stored answer = 500 chars |
|---|---|---|---|---|
| Gemma 26B | solve | 116 | 116 | 0 |
| Gemma 26B | validate_plan | 194 | 159 | 35 |
| Qwen3.5 9B | solve | 228 | 228 | 0 |
| Qwen3.5 9B | validate_plan | 620 | 615 | 5 |
| Qwen3.6 35B | solve | 323 | 294 | 29 |
| Qwen3.6 35B | validate_plan | 576 | 575 | 1 |

- **1,987 of 2,057: nothing.** The stored answer is empty. There is no text to show
  looping or a long restated plan. The cause has to be read from the token counts and
  the stored tool calls (3.3).
- **65 of 2,057: the model never called a tool and wrote prose until the output cap.**
  The 500 visible characters are the start of a by-hand walk-through. Gemma on
  validate_plan (35): "To validate the plan, we must trace the state transitions ...".
  Qwen3.6 35B on solve (29) and validate_plan (1): "Let me analyze this PDDL problem
  step by step." Whether the later text loops **cannot be determined from stored
  data**; only the first 500 characters of up to 8,192 tokens are kept.
- **5 of 2,057 (Qwen3.5 9B, validate_plan):** after a tool error the model started
  discussing a supposed syntax error in the input and ran out. Example opening: "The
  validation failed due to a syntax error in the PDDL parsing. ..."

### 3.3 Why the answer is empty: the final turn was never run

What the code does (`pddl_eval/vllm_client.py`, `chat()`). Every request asks for the
task's full output allowance (8,192 tokens for solve, 6,144 for validate_plan). The
server rejects a request when prompt plus allowance exceeds the 16,384-token window. Its
error message gives only a lower bound for the prompt size ("at least N input tokens",
with N = window minus allowance plus 1), not the real size. The client lowers the
allowance by N plus a 128-token margin and retries, twice. Because N is only that
bound, each retry lowers the allowance by just 129 tokens. So the retry only helps when
the prompt is within 258 tokens of the limit. Otherwise the client returns a made-up
reply: empty text, `done_reason = "length"`, 0 output tokens, and the last bound as the
prompt size, which is 8,451 for solve and 10,499 for validate_plan
(`_synthesize_overflow_response`).

In a tool arm the last request is large because it holds the original prompt (domain,
problem, plan), the model's tool call (which repeats the same PDDL as arguments) and
the tool's result. Truncated trials sent a median of 5,700 to 10,400 argument
characters, against 2,500 to 3,900 in trials that finished.

Evidence that this is what happened in the 1,987 empty trials:

| check | result |
|---|---|
| Exact. For two-turn trials whose first-turn prompt size is known (from single-turn trials on the same fixture), the recorded final-turn prompt size is exactly the give-up value (10,499 or 8,451) | **332 of 332 = 100% [98.9, 100.0]** (Gemma validate_plan 149/149; 9B validate_plan 101/101, solve 3/3; 35B validate_plan 56/56, solve 23/23) |
| Token count. The whole trial produced fewer output tokens than the smallest allowance a turn could have run out of (cap minus 258), so no turn can have ended by filling its allowance | **1,893 of 1,987 = 95.3% [94.2, 96.1]** |
| The other 94 | 70 have an earlier tool call that itself ran into the output cap (below); for the remaining 24 the sum over several turns is too large for the token argument, and they cannot be checked exactly |

First-turn prompt sizes were taken from the cell's own single-turn trials and, where
needed, from a second cell of the same tokenizer after checking that the difference is
one constant on every common trial (Gemma thinking on: +2 on 626 trials; Qwen3.5 9B
against Qwen3.6 35B: 0 on 102 trials; Qwen3.5 9B thinking on: +2 on 20 trials). For
Gemma solve no single-turn trial exists, so only the token-count check applies there
(116 of 116).

How much room the model really had. The true size of the refused prompt is not stored.
What is certain: it was larger than 10,498 tokens on validate_plan and 8,450 on solve,
so less than 5,886 and 7,934 tokens were free. An estimate from the stored pieces
(first-turn prompt + the call's tokens + the tool result converted at about 0.42 tokens
per character, calibrated on complete two-turn trials) puts the free room on
validate_plan at a **median of about 5,450 tokens (Gemma), 5,730 (9B), 5,450 (35B)**,
and above 1,000 tokens in all 306 trials where it can be estimated. A verdict needs
about ten tokens. For solve the same estimate could not be made (too few calibration
trials).

In 89% of these trials the tool had already returned the right result
(1,772 of 1,987 tool-verified: Gemma 110/116 and 151/159, 9B 226/228 and 481/615, 35B
247/294 and 557/575).

Looping does occur, in a small share. In **70 of 1,987 = 3.5% [2.8, 4.4]** an earlier
tool call was cut at the output cap, so its arguments are stored as unparsed text:
Qwen3.5 9B 65 (57 on validate_plan, 8 on solve; counters p01, p02, p03, p05 and one
gardening/p03), Qwen3.6 35B 5, Gemma 0. In the 9B cases the model repeats one action
inside the `plan` argument until the cap. End of one such call (21,671 characters):

```
c2\", \"increment c2\", \"increment c2\", \"increment c2\", \"increment c2\", \"increment c2\",
```

Typical call sequences in truncated solve trials are planner, then a second planner,
then `validate_plan` (9B: 120 of 228), each repeating the full PDDL. So "restating a long
plan" in the final answer is not what is seen. What is seen is the full PDDL repeated in
the tool-call arguments, which fills the window before the final answer is requested.

### 3.4 solve only: tool-verified against delivered, by plan length

Plan length is the oracle plan's number of actions (100 fixtures; the tool's plan has
the same length as the oracle's in 580 of 605 planner results in the Qwen3.5 9B cell,
correlation 1.00). "Delivered low" counts answers graded correct. "High" adds answers that fill the
500-character snapshot and cannot be graded. The gap is given as a range for the same
reason. The last three columns say where the non-delivered trials went.

Three models pooled, both arms (n = 1,800):

| plan length | n | fixtures | tool-verified | delivered low | delivered high | gap (pp) | final turn refused (empty) | snapshot full | graded wrong |
|---|---|---|---|---|---|---|---|---|---|
| 1-5 | 378 | 21 | 94.4% [91.7, 96.3] | 47.6% [42.6, 52.7] | 73.0% | 21.4 to 46.8 | 11.1% | 25.4% | 15.9% |
| 6-10 | 486 | 27 | 92.8% [90.1, 94.8] | 28.0% [24.2, 32.1] | 61.5% | 31.3 to 64.8 | 18.5% | 33.5% | 20.0% |
| 11-20 | 378 | 21 | 91.0% [87.7, 93.5] | 11.9% [9.0, 15.6] | 52.4% | 38.6 to 79.1 | 37.6% | 40.5% | 10.1% |
| 21-40 | 342 | 19 | 91.5% [88.1, 94.0] | 0.6% [0.2, 2.1] | 38.3% | 53.2 to 90.9 | 59.6% | 37.7% | 2.0% |
| 41+ | 216 | 12 | 88.9% [84.0, 92.4] | 0.0% [0.0, 1.7] | 25.9% | 63.0 to 88.9 | 74.1% | 25.9% | 0.0% |

Per model, both arms (n = 600 each). Cells are: tool-verified / delivered `<low, high>` /
final turn refused / graded wrong.

| plan length | n | Gemma 26B | Qwen3.5 9B | Qwen3.6 35B |
|---|---|---|---|---|
| 1-5 | 126 | 100.0 / `<45.2, 53.2>` / 0.0 / 46.8 | 100.0 / `<61.9, 82.5>` / 17.5 / 0.0 | 83.3 / `<35.7, 83.3>` / 15.9 / 0.8 |
| 6-10 | 162 | 98.8 / `<25.3, 38.9>` / 1.2 / 59.9 | 100.0 / `<37.7, 75.3>` / 24.7 / 0.0 | 79.6 / `<21.0, 70.4>` / 29.6 / 0.0 |
| 11-20 | 126 | 99.2 / `<11.9, 55.6>` / 14.3 / 30.2 | 100.0 / `<17.5, 66.7>` / 33.3 / 0.0 | 73.8 / `<6.3, 34.9>` / 65.1 / 0.0 |
| 21-40 | 114 | 99.1 / `<0.9, 46.5>` / 48.2 / 5.3 | 100.0 / `<0.0, 43.9>` / 56.1 / 0.0 | 75.4 / `<0.9, 24.6>` / 74.6 / 0.9 |
| 41+ | 72 | 97.2 / `<0.0, 43.1>` / 56.9 / 0.0 | 97.2 / `<0.0, 16.7>` / 83.3 / 0.0 | 72.2 / `<0.0, 18.1>` / 81.9 / 0.0 |

The plain and steered arms taken separately show the same shape (script output, part E).

Reading:

- The gap does widen with plan length inside the one task: the lower end of the range
  goes from 21 to 63 points, the refused-final-turn share from 11% to 74%.
- But the two things that grow are the refused final turn (longer problems have longer
  PDDL and longer plans, so the last request does not fit) and the 500-character
  storage limit (a plan of more than about 15 to 20 actions does not fit and cannot be
  graded). Neither is the model restating a plan badly.
- Where an answer could be graded at all (not empty and shorter than the snapshot):
  Qwen3.5 9B 161 of 161 correct [97.7, 100.0]; Qwen3.6 35B 88 of 90 = 97.8% [92.3, 99.4];
  Gemma 114 of 314 = 36.3%, where the 200 "wrong" ones are the artifact in 3.5.
- So for the open models, whether the delivery gap tracks answer length as a property
  of the model **cannot be determined from stored data**. It tracks length as a property
  of the apparatus. Gradeable answers exist almost only for short plans, which is a
  selected set.

### 3.5 Gemma solve: the "graded wrong" answers are the tool's plan behind a markup prefix

With thinking off, Gemma's answer after a tool turn starts with an empty reasoning
block that the server leaves in the text. The delivered grader reads plans line by line
and the first action sits on the same line as the markup, so it is dropped and the rest
is an invalid plan. Example stored answer (blocksworld/p01):

```
<|channel>thought
<channel|>(unstack b2 b1)
(put_down b2)
(pick_up b3)
(stack b3 b1)
```

| arm | n | graded `plan_invalid` | start with the prefix | after removing the prefix, equal line for line to a plan the planner returned in a tool-verified trial | delivered as graded | with those counted (diagnostic) |
|---|---|---|---|---|---|---|
| plain | 300 | 121 | 121 | 120 | `<14.3, 35.3>` | `<54.3, 75.3>` |
| steered | 300 | 79 | 79 | 78 | `<23.7, 59.3>` | `<49.7, 85.3>` |

The prefix is in 5,843 of the cell's 9,120 stored answers. It does not affect the
validation tasks (the verdict is found anywhere in the text). It is absent from the
no-call answers in section 2, which are single-turn. The rows with a full snapshot
would be hit by the same first-line loss if they were graded, so the upper bounds are
optimistic for the current grader too. The "with those counted" column is not a
re-grade: it uses string equality with the tool's plan, not the validator.

## What cannot be determined from stored data

- Whether the 2,378 Gemma no-call answers end with a verdict, and whether it is right
  (only the first 500 characters are stored).
- Whether a tool-call attempt sits after character 500 in the 64% of those answers
  that are long enough to hold one.
- Why the server did not recognise the 11 later-turn Gemma calls.
- The true prompt size of a refused final turn (only the server's lower bound is
  stored), so the free room is an estimate.
- For 24 of the 1,987 empty truncated trials, whether the last turn was refused or ran
  out while writing a call.
- Whether the prose answers that ran to the output cap (65 trials) loop.
- What the open models would have delivered on solve for plans longer than about 20
  actions, and on any trial whose final turn was refused.

## How to reproduce

From the repo root, with the project's Python environment (needs `pydantic`, as the
harness does). All three scripts only read; they print to the terminal and write
nothing.

```
python3 tools/reanalysis/q1_budget_probe_residual.py --rows --examples
python3 tools/reanalysis/q2_gemma_nocall.py --examples
python3 tools/reanalysis/q3_truncated_tool_arms.py --examples
```

- `q1_...` first asserts the frozen probe numbers (70/44 and 65/58) and stops if they
  do not reproduce. `--rows` prints one line per residual trial with its category and
  the measurements behind it; `--examples` prints verbatim excerpts.
- `q2_...` first asserts 622 / 2,808 / 617 / 0. Part E reads
  `results/iss024d-e2e-live` if it is on disk and is labelled as outside the canonical
  corpus.
- `q3_...` part A reproduces the figure's "truncated" band, C holds the checks of
  section 3.3, E the plan-length tables, F the Gemma prefix count.
- Inputs: `results/sweep5v2-live`, `results/sweep6-live`,
  `results/{sonnet,haiku}-frontier/sweep5v2{,-with-tools}-budget64k`,
  `results/derived/e2e_overlay`, `results/derived/gt_cache.json`.
  `results/sweep5-cluster-20260530` is not read anywhere.
- The scripts import the grading helpers from `pddl_eval/scoring.py` and
  `tools/e2e_regrade.py`, and the constants from `pddl_eval/prompts.py`,
  `pddl_eval/runner.py` and `pddl_eval/vllm_client.py`, so they follow the code of
  record. No existing file was edited.
