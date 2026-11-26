# Pre-registration: the Claude run (Haiku 5.5 and Sonnet 5.5, tools against no tools, five tasks)

**Written 2026-11-26, before any request was sent to the provider. Sections 1 to 9 are
fixed as of the pilot's pass (section 11), before the first request of the full run.
The analysis is not written yet; it is written and frozen before any row of the full
run is read (sections 4 and 6).** Decision to run, and the outline of the design: Omer,
2026-11-25 (`development/unified_run_design.md`, section B). The runner is written and
tested without any network call (`tools/frontier55/`, `tests/test_frontier55.py`). The
analysis is not written yet (section 4).

**Choices that were Omer's** are marked **[Omer, 1]** to **[Omer, 3]**. Each was put to
him as the session's recommendation. **Accepted on 2026-11-26:** with the three choices
in front of him he answered "launch the claude run". This is recorded here from the
session's log; Omer confirms it when he reads this draft.

- **[Omer, 1]** The no-tools arm goes through the Batch API. The tool arm goes through
  live calls, started the same day (section 2.4).
- **[Omer, 2]** Effort: each model's own default, sent explicitly. Haiku 5.5 "medium",
  Sonnet 5.5 "high" (section 2.3).
- **[Omer, 3]** A pilot first (section 6).

**Cost.** Omer said on 2026-11-25 that no cost estimate is needed
(`unified_run_design.md`, B4). The session still posts the itemized estimate of section
9 before the first paid request, and **stops and asks if the estimate for the whole run
is above 500 dollars**. The estimate today is 351 to 358 dollars. The stop that the code
enforces is `--max-usd`, a spend limit per model that every paid command must be given
(section 7).

**The grade** (section 4) follows from the decision of 2026-11-25 that this run has the
same design as the open models. It is written here for Omer to read before the freeze.

**Disclosure of prior data contact.** No row of this run exists. The author has read the
old Claude runs (Haiku 4.5 and Sonnet 4.6, June to September 2026): their rows, their
rates, the lengths of their tool outputs and their token counts. Section 3 and the cost
table use those lengths and counts. The author has also read the open models' rerun and
control. No answer of Haiku 5.5 on these tasks has been read. For Sonnet 5.5, the pilot
of 2026-11-09 (`results/frontier-d5a-pilot`, 40 unaided solve answers under other
settings) exists; its answers were not graded.

**Status of this document.** Sections 1 to 8 are the registration once Omer has answered
and the analysis is frozen. Section 9 is the cost table. Section 10 is the freeze record,
section 11 the pilot record, section 12 the deviations. The last three are empty.

---

## 1. Purpose

The paper asks three questions about the open models:

- **RQ1.** Do PDDL tools help a model do planning tasks?
- **RQ2.** Does the model choose the right tool?
- **RQ3.** Does the model use the tool's output properly?

This run asks the same three questions of two hosted frontier models, Claude Haiku 5.5
and Claude Sonnet 5.5, on the same tasks and problems.

**It is a separate corpus.** Its rows are never pooled with the open models' rows. The
two Claude models are not ranked against the open models, and no difference between a
Claude model and an open model is tested. Section 3 lists the conditions that differ
and cannot be removed. The paper shows the Claude rows beside the open models' rows and
states those conditions.

**Not covered.** A steered tool arm (Omer, 2026-11-25: none). Thinking on. Any other
model. PlanBench (left as it is). A rerun of the old Claude models.

---

## 2. Design

### 2.1 Models, tasks and size

- Models: `claude-haiku-5-5` and `claude-sonnet-5-5`.
- Tasks: solve, validate_domain, validate_problem, validate_plan, simulate.
- Problems: the 100 problems of the open models' runs (20 domains, 5 problems each),
  with their fixtures: the broken domains and problems, and five valid and five broken
  plans per problem.
- Wordings: the three plain wordings, v11, v12 and v13.
- Arms: **no tools**, and **tools offered** (plain wordings; all seven tools visible).
- Per model and arm: **4,560 trials**. Solve 300, validate_domain 360, validate_problem
  600, validate_plan 3,000, simulate 300.
- Total: 2 models by 2 arms by 4,560 = **18,240 trials**.

The two arms of a model hold the same trials. The trial list comes from the harness's own
enumerator (`pddl_eval.runner.build_jobs`), and the runner halts if the counts differ
from the ones above.

**The pilot is its own short list** (section 6). It is not a share of the full run
drawn by a rule, it is never pooled with the full run, and the full run asks every one
of its trials again.

### 2.2 Messages

The system and user messages are built by the harness (`build_messages`), word for word
as for the open models.

- **No tools, solve and simulate:** the format-stated system text of the control (its
  cell B), the text the matched run's no-tools arm uses. sha256 (utf-8) `3dbc1baf…` on
  solve and `7ccf5d9d…` on simulate.
- **No tools, the three validation tasks:** the registered no-tools text, which asks for
  one final line `VERDICT: VALID` or `VERDICT: INVALID`.
- **Tools:** the with-tools text of the rerun's Part A.

The runner checks the sha256 of every system text before a request is built:

| arm | task | sha256 of the system text |
|---|---|---|
| no tools | solve | `3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588` |
| no tools | simulate | `7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9` |
| no tools | validate_domain | `ab1ffd2abc5e6deab5f37668366b09be3e78d9060646e1aac8ec944fd64d0c36` |
| no tools | validate_problem | `f8bea04b4d9e1aac588db14775254f8ef1f77465d1b1f7ec3705441488b9f201` |
| no tools | validate_plan | `dcbd1189e28a7f5ace9bcdba92236e6945bd71c9b8b9feed349ceeec09c5c538` |
| tools | solve | `9b179ca12c2cd2220b46c5478bc637f6dd47356a2f81a4795d3541ecdf6dbb2c` |
| tools | simulate | `ebf8e7fe9d55ab56b9d2d4ba02be4f2b7770fe1b9fdd4d77bba790a68a0d0ac6` |
| tools | validate_domain | `2351f7b2257621ca0155af5206a4304ba7bef79caf974712ac2563101dda839d` |
| tools | validate_problem | `fa18dc28613de2ae12a75efca36bd2aaeb3950fd6f6b6cf7d176295a6a88c54e` |
| tools | validate_plan | `dae2e397c4fc933163608debcab8a6004c170db9f1242ea53b1953909a616f0f` |

The first two and the two with-tools digests of solve and simulate are the ones the
control's and the matched run's registrations give.

**Plans in the prompts** (validate_plan and simulate) come from the pinned ground-truth
cache, `results/derived/gt_cache.json`, sha256 `77d4184e…c7e`. The runner halts on any
other file. Ground truth is never computed at run time. So the plan a simulate prompt
shows is the plan the answer key belongs to, on all 100 problems. **This differs from
the matched run and the rerun**, where on six problems (barman p01 to p05, gripper p03)
the plan in the prompt could differ from the plan of the key (ISS-029).

### 2.3 Request settings

A request holds the model, the output cap, the system text, the messages, the thinking
setting, the effort level and, in the tool arm, the tool list. Nothing else.

| setting | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| thinking | `{"type": "disabled"}` | `{"type": "between_tools"}` |
| effort **[Omer, 2]** | `medium` (its default) | `high` (its default) |
| output cap per request | 8,192 tokens on solve, 6,144 on the other four tasks | the same |
| tool round trips per trial | at most 10 | at most 10 |

- **No temperature, top-p or top-k is sent.** These models reject any value other than
  their default.
- **No structured output, and no added sentence that asks for JSON.** The old Claude
  runs used both in the no-tools arm.
- No prompt caching, no prefilled answer, no forced tool choice (the default lets the
  model decide), no fallback model. **A fallback would have another model answer the
  trial, so it is never set.**
- The runner refuses to send a request that holds any other field.
- The client talks to `https://api.anthropic.com`, given explicitly and recorded in the
  manifest. The runner refuses to start when the environment sets another address
  (`ANTHROPIC_BASE_URL`). A live request has a 600-second limit and one retry by the SDK.

**The tools** are the open models' suite, run on the laptop as local servers:
`pddl-copilot` at commit `5e4f9c0`, with pddl-pyvalidator **0.1.5**. The tool names,
descriptions and schemas go to the model unchanged. The runner **refuses to start**
unless the checkout it is given is at `5e4f9c0`, has no change under `plugins/`, and its
validator environment reports 0.1.5.

The laptop's working checkout of `pddl-copilot` is at a later commit with validator
0.1.6, and is not touched. The run uses a second checkout, made once:

1. `git -C ../pddl-copilot worktree add --detach ../pddl-copilot-5e4f9c0 5e4f9c0`
   (or a local clone checked out at that commit);
2. in `plugins/pddl-solver` and `plugins/pddl-validator` of that checkout:
   `uv venv --python 3.14 .venv` and
   `uv pip install --python .venv/bin/python3 -r requirements.txt`;
3. `uv pip install --python plugins/pddl-validator/.venv/bin/python3 "pddl-pyvalidator==0.1.5"`.
   The requirements file of `5e4f9c0` says "0.1.5 or later", so without this step the
   environment gets 0.1.6 and the runner refuses it.

This was tried on 2026-11-26 on a local clone in a scratch folder. The runner accepted
it, listed the seven tools, and a planner call and a plan check returned results. The
sha256 of the tool list built there is
`dd14507890d38a8a3c581971a699037b39a3a0bd9374d5801072fb58b9b14400`. The run records this
digest in its manifest and refuses to resume under another.

**The tool code is the open models' commit. Its dependencies were resolved on another
machine.** The planners and libraries are installed from the requirement ranges of that
commit, on the laptop, on the day the checkout is made. The manifest of the tool arm
records the installed packages of every plugin environment of the checkout
(`name==version`, the same content as `pip freeze`) and the tool-list digest. When the
cluster is reachable, its installed versions are read and set beside these. This is a
record, not a gate.

### 2.4 Two routes to the provider **[Omer, 1]**

- **No tools:** one request per trial, all 4,560 of a model in one batch (Message
  Batches API, half price). From the API reference: a batch holds up to 100,000
  requests or 256 MB; most batches complete within an hour, and a batch has at most 24
  hours; results are kept for 29 days. The runner checks the two size limits before it
  sends, and stores the raw results on disk as soon as the batch ends.
- **Tools:** live calls. The runner sends a request, runs the tools the model asks for,
  sends the results back, and repeats, at most 10 times. Four trials run at a time.

Why the tool arm is not batched: a tool conversation has several turns, and under the
Batch API every turn of every trial would wait for a whole batch to finish. A batch can
take up to a day. The old Claude tool rows needed up to 10 turns. The two arms of a model
could then not be kept in the same day. The price of this choice is in section 9: the
tool arm is paid at the list price.

### 2.5 The tool conversation

- After a response that asks for a tool, the model's content goes back **exactly as it
  came**, every block in order. For Sonnet 5.5 this includes its notes between tool
  calls (`thinking` blocks) with their signatures.
- All tool results of a turn go back in one user message.
- A tool that raises gives the harness's text `Tool error: …`, marked as an error.
- The conversation ends at the first response that does not ask for a tool.
- After 10 round trips still asking for a tool: **loop exhausted**, the answer is empty.
- The provider refuses the request because the conversation no longer fits its window
  (an error that says the prompt or the context is too long, or the stop reason
  `model_context_window_exceeded`): recorded as an outcome of the trial, with the tool
  calls made so far. Not a crash. The row is written as the harness writes it for an
  open model whose window is full: empty answer, stopped for length, and
  `ctx_no_room_turns: 1` in its token record. The rerun's loader then reads it as a
  "no room" row, as for the open models.
- A refusal by the model (section 3.6).
- **If the first request of a trial is rejected as too long, the run of that folder
  stops.** The first request holds only the task's own prompt, so this is a setup
  error and not an outcome.
- A "pause" stop cannot happen without the provider's own server tools. If it does, the
  trial is an error row and is counted.

**How an over-length row here differs from one of the open models**, written down so
that the analysis treats them alike on purpose. Both have an empty answer, a stop for
length, `ctx_no_room_turns: 1`, and the tool calls made so far. The differences:

- *Turn count.* For an open model the turn that had no room is counted in
  `tokens.turns` (the harness records an empty turn). Here a request that the provider
  rejects produced no response, so it is not counted; when the provider instead answers
  with the stop reason `model_context_window_exceeded`, that response is counted.
- *Error text.* The open rows carry no error text. These rows carry
  `api: prompt is too long` in `error`, and the provider's full message in the sidecar.
- *Clipping.* An open model's request can also be clipped (answered with a smaller
  output allowance). That does not exist here: a request either fits or is rejected.
- *Where it can happen.* Here only after a tool result, never on the first request.

### 2.6 What is stored

Per model and arm, one folder: `<model>_no-tools` and `<model>_tools`, under
`results/frontier55/` (the pilot: `results/frontier55-pilot/`).

- **`trials.jsonl`:** one row per trial in the harness's row shape, so that the rerun's
  loader and graders read it. The answer is stored in full. An answer longer than 65,536
  characters is flagged (`response_truncated_by_storage` true, the first 65,536
  characters in the row), counted as "cut by storage", and its full text is kept in the
  sidecar. It is graded from that full text. At 8,192 output tokens this is not
  expected: it would need 8 characters per token.
  Every row is passed through the rerun's frozen loader before it is written. The
  loader knows only the three open models' names, so the check swaps the model name for
  one of them and applies every other rule unchanged.
- **`trial_meta.jsonl`:** one line per trial. The model ID the provider returned; the API
  version header that was sent; the SDK version; the UTC time of every request and
  response; the request IDs or the batch ID; the raw stop reason and its details; the
  full usage block of every turn; the effort and thinking settings; the number of turns;
  and the raw content of every turn, so that the notes and the full answers can be read
  again at no cost.
- **`attempts.jsonl`:** every try that failed for a reason outside the model, with its
  turn, and every trial that was abandoned, with the usage of its discarded turns.
- **`spend.jsonl`** and, in the run's root folder, **`spend_<model>.json`:** the usage and
  the price of every response, and the model's running total (section 7).
- **`run_manifest.json`:** the settings, the provider's address, and the sha256 of the
  runner's three files. A resume under other settings, or with a changed runner, is
  refused.
- **`run_provenance.jsonl`:** one line per start: this repo's commit, whether the
  runner's files or this registration had uncommitted changes, and the sha256 of the
  runner's files and of this registration. The commit and the registration's digest are
  kept here and not in the manifest, because the manifest refuses a resume on any
  difference and this document gains its records (sections 10 and 11) during the run.
- A lock file per folder lets one paid command run in a folder at a time. On start, a
  half-written last line of any of these files is cut back to the last complete line;
  the cut is counted and logged (`repairs.log`).

Stop reasons are written in the harness's words: an ordinary end is `stop`, the output
cap is `length`, an exhausted loop is `tool_calls`. The provider's own word is in the
sidecar.

**Token counts in a row.** `tokens.prompt` is every input token of the trial, summed
over its turns (uncached, cache-written and cache-read; no caching is asked for, so the
last two are expected to be zero). `tokens.completion` is every output token, summed
over the turns, the notes between tool calls included. `tokens.turns` is the number of
requests. The two duration fields hold the trial's wall time in the tool arm and 0 in
the batched arm. The per-turn usage as the provider returned it is in the sidecar.

### 2.7 A new corpus

The rows of this run are never pooled with the open models' runs, with the old Claude
runs, or with the pilot. No cell of this run stands in for a cell of a filed readout.

---

## 3. What differs from the open models and cannot be removed

The paper states each of these beside the Claude rows.

1. **Temperature.** The open models run at temperature 0. These models accept only
   their default. Each trial is one draw at that default.
2. **Thinking.** The open models and Haiku 5.5 run with thinking off. Sonnet 5.5 has no
   "off". Its lowest setting does no thinking before the answer, and in the tool arm it
   writes short notes between tool calls. So Sonnet's no-tools arm does not think, and
   its tool arm carries those notes. The notes are stored, and their token count is
   reported.
3. **The window.** The open models have a 16,384-token window, and on simulate the
   tool's output often fills it. These models have a window of about one million tokens,
   so that does not happen here. Measured on the old Sonnet 4.6 tool rows (102 calls of
   the simulate tool): the output has a median of 27,664 characters, a 90th percentile
   of 188,202, and a largest value of 1,191,002 (depot p01), about 496,000 of that
   model's tokens. In 64 of 99 two-turn simulate trials the second request held more
   than 16,384 tokens. The largest output fits the new window once; a second call of the
   tool on that problem may not. Such a trial is recorded as section 2.5 says.
4. **The output cap is in the provider's tokens.** The numbers are the open models'
   (8,192 and 6,144), but a token is not the same unit. Sonnet 5.5 counts about 1.3
   times as many tokens for the same text as Sonnet 4.6, so the cap is tighter for it.
   For Haiku 5.5 the ratio is not known. On simulate the cap is expected to cut many
   traces in both arms: with the same cap, 89 of 300 unaided and 30 of 100 tool answers
   of Sonnet 4.6 stopped at it. **Sonnet's notes between tool calls count against the
   cap of the request they are written in.** A long note leaves less room for the tool
   call or the answer in that request.
   **A label the open rows never carry.** If Sonnet's final turn reaches the cap holding
   a note and no answer text, the harness's rule labels the row `think_overflow`
   (stopped for length, thinking present, answer empty). No row of the open models
   carries that label, because their stored thinking is always empty. The analysis maps
   it to "stopped at the cap with no answer", the label the same event gets for the
   open models.
5. **Hosted models.** The weights behind a model name can change without notice. Each
   trial records the model ID the provider returned and its time. Both arms of a model
   are queried on the same UTC day (section 6).
6. **Refusals.** The provider can end a response with a refusal. Such a trial is a wrong
   trial, stored as an error row with `stop_reason=refusal`, its details in the sidecar.
   A refusal in the middle of a tool conversation ends the trial the same way. A refused
   trial is never run again and never sent to another model. **Rule for the analysis:**
   a refusal is wrong under the grade, stays in the denominator, is kept out of the VOID
   rule of section 7, and is counted and reported per model, arm and task.
   **Error rows and RQ2, RQ3.** An error row (a refusal, a pause, an unknown stop) holds
   no tool calls and no tokens; those are in the sidecar. Such a trial is left out of
   the four tool-choice classes of RQ2 and out of RQ3's "tool right" set, and is counted
   beside them, per model and task. "No room" rows are treated as for the open models.
7. **The tools run on another machine.** The same tool commit and validator release as
   the open models, but on the laptop, with the planners and libraries installed from
   the same requirement ranges on another day. The installed versions and the tool
   list's digest are recorded (section 2.3).
8. **Route.** The no-tools arm is batched and the tool arm is live (section 2.4).

---

## 4. The grade

A trial is right when the final answer, as the model wrote it, is right. The tool's
output is never used in place of the final answer.

- **Solve and simulate: the matched run's registered grade** (its section 3), word for
  word. Solve: the plan in the last closed code block when that block holds a plan,
  otherwise the plan the rerun's grader reads; sent to the validator (release 0.1.5) in
  lower case; it must pass. Simulate: the trace the rerun's grader reads must equal the
  answer key; a trace written one JSON object per line also counts when it equals the
  key.
- **Validate_domain, validate_problem, validate_plan: the rerun's frozen grade.** The
  stated verdict must equal the truth.
- **Error rows** (a refusal, an unknown stop) are wrong under the grade, whatever they
  stored.
- **Rows cut by storage:** the registered expectation is zero. Any such row is graded
  from the full answer in the sidecar and reported.

**RQ2 and RQ3** use the definitions of the open models
(`tools/reanalysis/rq23_metrics.py`): which tools a trial called, in four classes (no
call, the right tool only, the right tool and another, other tools only); and, among
trials where the right tool returned the right result, the share whose final answer is
wrong under the grade above.

**The analysis is not written.** It will be a new script that reads these rows through
the rerun's loader (with the model-name swap of section 2.6) and applies the graders
above unchanged. It is written and frozen, with the five gates of the freeze protocol,
after the pilot's plumbing check. The pilot's check reads no outcome (section 6).

**No row of the full run is read before the analysis is frozen. The run may be collected
before that.** Until the freeze, only the row counts and the counts of endings of the
full run are looked at (section 6, "During the run"). The runner also stores the
harness's own online grade in each row, as the open models' rows do. No reading uses it.

---

## 5. Measures and contrasts

Per model and task. Nothing is pooled over models or tasks.

- **RQ1.** The rate right in each arm, and **tools minus no tools**, paired on the trial
  (task, domain, problem, plan label, wording), in points. 10 contrasts (2 models by 5
  tasks).
- **Verdict errors**, on the three validation tasks, in each arm: valid inputs called
  invalid, and invalid inputs called valid, with counts.
- **RQ2.** Tool choice in the tool arm: the four classes, with counts.
- **RQ3.** Tool right and answer wrong: of the trials where the right tool returned the
  right result, the share whose final answer is wrong.

**Intervals.** 95% percentile intervals from the rerun's domain-cluster bootstrap
(`tools.delivered_rerun.stats.cluster_bootstrap`): 20 domains, 10,000 resamples, seed
20261002, as in the matched run.

**Readings of the RQ1 contrast.** "Tools ahead" when the interval is above 0, "no tools
ahead" when it is below 0, "no difference shown" otherwise. Beside each contrast, an
exact sign-flip p-value over the 20 domains, Holm-adjusted across the five tasks of a
model. A difference whose interval excludes 0 and whose adjusted p-value is 0.05 or more
carries the words "(not after Holm)".

**Readings that would be wrong, named in advance.** "The unaided model is as good as the
tools" from an interval that includes 0. Any ranking of a Claude model against an open
model. A pooled figure over the two models. A comparison of this run's rates with the
old Claude runs as if they were the same experiment.

**Descriptive, with counts:** right answers by wording; answers that stopped at the
output cap; loop-exhausted trials; trials the provider refused for length; refusals;
other error rows; turns per trial; input and output tokens per trial (per turn in the
sidecar); for Sonnet, the thinking tokens between tool calls; the model IDs returned and
the dates.

---

## 6. Execution

Every spend needs Omer's go-ahead, with the cost table of section 9 in front of him. The
pilot and the full run are asked for separately.

**Order.** The checkout of section 2.3 is made → dry run (no call) → **tools self-check**
(no call) → the itemized estimate is posted → pilot **[Omer, 3]** → plumbing check →
full run. The analysis is
written and frozen (section 10) after the plumbing check; the full run may be collected
meanwhile, and none of its rows is read before the freeze → frozen analysis → readout
and a `NUMBERS.md` entry.

**Dry run.** `python -m tools.frontier55.runner dry-run --marketplace-path <checkout>`
builds every request and prints the counts and digests. It builds no client and makes no
call.

**Tools self-check, before the pilot, local and free.**
`python -m tools.frontier55.runner tools-selfcheck --marketplace-path <checkout>` calls,
through the checkout, the right tool of every task on every fixture of the full run: the
planner on the 100 problems, the simulate tool on the 100 cached plans, and the three
validators on every valid and broken domain, problem and plan (1,520 fixtures). Each
result is graded by the harness's own with-tools rule against the ground-truth cache and
the fixture labels. No model is involved. **Any disagreement is resolved before the
pilot.** Result of 2026-11-26 on the scratch checkout of section 2.3: 1,520 of 1,520
agree (solve 100, validate_domain 120, validate_problem 200, validate_plan 1,000,
simulate 100), and the planner returned the cached plan on all 100 problems.

**Pilot.** Wording v11, both arms, both models. Per domain, on its first problem:

| task | trials per domain | which |
|---|---|---|
| solve | 1 | the first problem |
| simulate | 1 | the first problem |
| validate_problem | 2 | the first (valid) problem, and the first broken problem of the domain |
| validate_domain | 2 | the valid domain, and the broken domain (every domain has one) |
| validate_plan | 2 | the first valid plan and the first broken plan of the first problem |

**160 trials per model and arm** (solve 20, simulate 20, validate_problem 40,
validate_domain 40, validate_plan 40), **640 trials** in all. Never pooled, and not a
share of the full run drawn by a rule. The checks allowed on the pilot's output, and
nothing else:

1. every folder holds its 160 rows, and each row has its sidecar line;
2. the rerun's frozen loader reads every row (with the model-name swap); no row cut by
   storage; no half-written line;
3. at least 95% of the stored answers are non-empty in each folder, counted without the
   error rows and the trials the provider refused for length;
4. the settings, read from the sidecar, which keeps every field of every request that
   was sent except the texts and the tool list: per model, the thinking setting, the
   effort and the output cap equal section 2.3 on every request; no request holds a
   sampling field or any field outside section 2.3; one API version header was sent;
5. the model IDs the provider returned, listed per folder; each must start with the ID
   that was asked for;
6. the counts of each kind of ending (answer, loop exhausted, refused for length,
   refusal, pause, unknown, cut by storage) and of failed attempts;
7. notes between tool calls. For every request after the first of a trial, the runner
   reads back the bytes it sent and counts the `thinking` blocks of the previous
   response that are in the request body, byte-equal as JSON. The check prints the
   number of such blocks returned and the number found in the next request body. The
   two must be equal. Numbers only; no note is printed;
8. thinking where none may be: the thinking token counts of the usage blocks and the
   number of `thinking` blocks must be zero in both arms of Haiku 5.5 and in the
   no-tools arm of Sonnet 5.5; for the tool arm of Sonnet 5.5 they are reported;
9. cache token counts are zero in every folder; every request went to
   `api.anthropic.com`; the model ID returned does not change within a folder;
10. total input and output tokens and the dollars they imply at the registered prices,
    per model and arm, beside the estimate of section 9 and the spend ledger;
11. per tool name: the number of calls, the number flagged as errors, and the number of
    results that are an error object or start with `Tool error:`;
12. any limit number found in the text of an over-length error.

`python -m tools.frontier55.runner pilot-check --out results/frontier55-pilot` prints
these items. It prints no rate of right answers, no verdict, no tool-call count per task
and no answer text.

**Full run, per model.** On one UTC day: the no-tools batch is sent, then the tool arm
is started. The two models may run on different days.

- **The same-day rule.** Both arms of a model count as "the same day" when the batch was
  sent and every tool trial was requested on one UTC date. The sidecar holds the times.
- **If the batch does not end that day:** its results are still used. A batch is
  processed by the provider at a time of its choosing after it is sent; the date sent
  and the date ended are both reported, and the paper states the span. Failed items and
  an expired batch follow the order given under "Failed batch items" below. A rerun of
  both arms is declared here and is not a deviation.
- **If the tool arm does not finish that day** (a rate limit, an outage): it is resumed
  as soon as possible. The trials requested on a later date are counted and reported.
  If more than 5% of a model's tool trials fall on a later date, both arms of that
  model are run again together, as above.

**Resume.** A tool trial with a row is never run again. When a request fails for a
reason outside the model (rate limit, server error, connection), the same turn is tried
once more with the conversation as it stands; the earlier turns are not asked again. If
that fails too, the trial is abandoned without a row and starts again from its first
turn on the next start. The usage of its discarded turns is written to `attempts.jsonl`
and is counted in the spend. Every failed try is logged.

**The batch is sent once.** The send is not retried. If it fails so that it is not known
whether the batch exists, the folder keeps a "send started" entry without an ID and
nothing more is sent from it; `batch-recover` lists the account's batches and finds the
ID by creation time and request count. If the provider plainly refuses the send, no
batch exists and the entry is removed. A batch that was sent is polled again, never
sent twice.

**Failed batch items, in this order.** (1) Items that come back failed, canceled or
expired are sent again once, in a second batch, the same day. (2) If after that more
than 1% of the arm's trials are still without a row, or if the first batch expired as a
whole, both arms of that model are run again together in new folders, and the first
attempt is kept and reported.

**A model ID that changes within a folder** stops that folder. No row is written for
the trial that showed the new ID, and the change is reported.

**During the run.** Monitoring reads row counts and the counts of endings only.

**Completeness.** 4,560 rows per folder, with the per-task counts of section 2.1, and
the same trials in both arms of a model. A short folder is resumed, not analysed.

---

## 7. Stop rules

- **A request the provider calls invalid** stops the run at once. It is a fault of the
  runner, not an outcome. Nothing is written for that trial.
- **Seven tool trials in a row that cannot be completed** stop the tool arm. It is
  resumed later.
- **A folder is VOID** when more than 1% of its rows are error rows that are not
  refusals (unknown stop, pause). Both arms of that model are then run again together,
  in new folders. Refusals are outcomes and do not count toward this rule; they are
  reported per model, arm and task. The rerun's own rule would count a refusal row as
  an exception; the analysis of this run must separate the two by the row's error text
  (`stop_reason=refusal`).
- **The storage rule:** any row cut by storage is reported and graded from the sidecar.
- **Spend:** the itemized estimate is posted before the first paid request. If the
  estimate for the whole run is above 500 dollars, nothing is sent and Omer is asked.
  **The enforced stop is `--max-usd`.** Every paid command must be given it; there is
  no default. The runner adds up the usage of every response at the registered prices
  (section 9; cache tokens are priced too if they ever appear), the responses of
  abandoned tries and the batch results included, over both arms of the model, and
  writes the running total to the run folder. When the model's total passes `--max-usd`
  the folder stops and Omer is asked. The value per model is set by the session at each
  start and recorded in section 10. The "bound" column of section 9 is a ceiling of the
  estimate, not a stop.
- **The first request of a trial rejected as too long**, or **a model ID that changes
  within a folder**, stops that folder (sections 2.5 and 6).
- Any other stop is a deviation (section 12).

---

## 8. The reporting rule

Fixed here, before any data:

1. **This run is what the paper reports for the frontier models**, for the three
   questions: the rate of each arm, the contrast of section 5 with its interval and
   label, the verdict errors, the tool choice and the tool-right-answer-wrong share,
   whatever they show.
2. **The Claude rows stand beside the open models' rows and are not ranked against
   them.** The conditions of section 3 are stated with them.
3. **The old runs** (Haiku 4.5 and Sonnet 4.6) go to the supplement as an earlier
   record, with their own conditions: one wording in the tool arm, answers cut at 16,384
   characters, structured output on unaided solve, arms 17 days apart.
4. **The pilot** is reported as a plumbing check only.
5. **No paper text is part of this registration.** The readout goes to Omer.

---

## 9. Cost, itemized (an estimate; nothing has been spent)

Made by `python -m tools.frontier55.cost` from the old Claude rows of wording v11. No
call was made to produce it.

How to read it:

- Tokens are the old rows' counts, scaled to the new model. **Sonnet: times 1.3** (the
  repo's note on its tokenizer). **Haiku: the factor is not known**; the range is from
  1.0 to 1.3.
- Prices per million tokens, input / output, to be checked on the day: Haiku 5.5
  $0.10 / $0.50 for prompts up to 100,000 tokens and $0.50 / $2.50 above; Sonnet 5.5
  $2.00 / $10.00. The no-tools arm is at half price (Batch API). The tool arm is at the
  list price, with no caching.
- **"Estimate"** assumes answers as long as the old models'. That is not known for the
  new models, and the old unaided solve answers were short because of structured
  output. **"Bound"** has every request write its full output cap.
- A Haiku trial whose summed input passes 100,000 tokens is priced at the higher rate as
  a whole, which overstates it.

**Pilot (160 trials per model and arm, wording v11)**

| model | arm | task | trials | requests | input, MTok | output, MTok | trials at Haiku's higher rate | estimate, $ | bound, $ |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | no tools | solve | 20 | 20 | 0.03 to 0.04 | 0.01 | 0 | 0.00 to 0.01 | 0.04 |
| Haiku 5.5 | no tools | validate_domain | 40 | 40 | 0.03 to 0.04 | 0.02 | 0 | 0.01 | 0.06 |
| Haiku 5.5 | no tools | validate_problem | 40 | 40 | 0.05 to 0.06 | 0.02 to 0.03 | 0 | 0.01 | 0.06 |
| Haiku 5.5 | no tools | validate_plan | 40 | 40 | 0.06 to 0.07 | 0.04 to 0.05 | 0 | 0.01 to 0.02 | 0.07 |
| Haiku 5.5 | no tools | simulate | 20 | 20 | 0.03 to 0.04 | 0.07 to 0.08 | 0 | 0.02 | 0.03 |
| Haiku 5.5 | tools | solve | 20 | 93 | 0.81 to 1.06 | 0.10 to 0.13 | 1 | 0.13 to 0.24 | 0.61 |
| Haiku 5.5 | tools | validate_domain | 40 | 80 | 0.45 to 0.58 | 0.04 to 0.05 | 0 | 0.06 to 0.08 | 0.30 |
| Haiku 5.5 | tools | validate_problem | 40 | 80 | 0.49 to 0.63 | 0.05 to 0.07 | 0 | 0.07 to 0.10 | 0.31 |
| Haiku 5.5 | tools | validate_plan | 40 | 80 | 0.54 to 0.71 | 0.06 to 0.08 | 0 | 0.09 to 0.11 | 0.32 |
| Haiku 5.5 | tools | simulate | 20 | 41 | 0.55 to 0.71 | 0.09 to 0.12 | 0 | 0.10 to 0.13 | 0.20 |
| Sonnet 5.5 | no tools | solve | 20 | 20 | 0.04 | 0.01 | 0 | 0.10 | 0.86 |
| Sonnet 5.5 | no tools | validate_domain | 40 | 40 | 0.04 | 0.02 | 0 | 0.13 | 1.27 |
| Sonnet 5.5 | no tools | validate_problem | 40 | 40 | 0.06 | 0.01 | 0 | 0.10 | 1.29 |
| Sonnet 5.5 | no tools | validate_plan | 40 | 40 | 0.07 | 0.04 | 0 | 0.27 | 1.30 |
| Sonnet 5.5 | no tools | simulate | 20 | 20 | 0.04 | 0.08 | 0 | 0.44 | 0.66 |
| Sonnet 5.5 | tools | solve | 20 | 46 | 0.39 | 0.05 | 0 | 1.28 | 4.54 |
| Sonnet 5.5 | tools | validate_domain | 40 | 80 | 0.57 | 0.06 | 0 | 1.72 | 6.06 |
| Sonnet 5.5 | tools | validate_problem | 40 | 80 | 0.63 | 0.07 | 0 | 1.98 | 6.17 |
| Sonnet 5.5 | tools | validate_plan | 40 | 80 | 0.70 | 0.08 | 0 | 2.24 | 6.32 |
| Sonnet 5.5 | tools | simulate | 20 | 40 | 1.33 | 0.14 | 0 | 4.03 | 5.11 |
| **Haiku 5.5, total** | | | **320** | **534** | | | | **0.51 to 0.73** | **2.01** |
| **Sonnet 5.5, total** | | | **320** | **486** | | | | **12.30** | **33.58** |
| **both models** | | | **640** | **1,020** | | | | **12.80 to 13.02** | **35.59** |

Every pilot trial has an old row of wording v11 behind it, for both old models: the
trial counts above are the pilot's own (320 per model).

**Full run (three wordings)**

| model | arm | task | trials | requests | input, MTok | output, MTok | trials at Haiku's higher rate | estimate, $ | bound, $ |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | no tools | solve | 300 | 300 | 0.44 to 0.57 | 0.09 to 0.11 | 0 | 0.04 to 0.06 | 0.64 |
| Haiku 5.5 | no tools | validate_domain | 360 | 360 | 0.31 to 0.40 | 0.17 to 0.23 | 0 | 0.06 to 0.08 | 0.57 |
| Haiku 5.5 | no tools | validate_problem | 600 | 600 | 0.76 to 0.99 | 0.35 to 0.46 | 0 | 0.13 to 0.16 | 0.97 |
| Haiku 5.5 | no tools | validate_plan | 3,000 | 3,000 | 4.58 to 5.95 | 3.30 to 4.29 | 0 | 1.05 to 1.37 | 4.91 |
| Haiku 5.5 | no tools | simulate | 300 | 300 | 0.50 to 0.65 | 1.07 to 1.19 | 0 | 0.29 to 0.33 | 0.49 |
| Haiku 5.5 | tools | solve | 300 | 1,344 | 12.23 to 15.90 | 1.60 to 2.07 | 18 | 2.38 to 4.16 | 9.74 |
| Haiku 5.5 | tools | validate_domain | 360 | 720 | 4.01 to 5.21 | 0.33 to 0.44 | 0 | 0.57 to 0.74 | 2.73 |
| Haiku 5.5 | tools | validate_problem | 600 | 1,209 | 7.46 to 9.70 | 0.81 to 1.06 | 0 | 1.15 to 1.50 | 4.68 |
| Haiku 5.5 | tools | validate_plan | 3,000 | 6,126 | 43.85 to 57.00 | 5.30 to 6.89 | 3 | 7.03 to 9.34 | 24.85 |
| Haiku 5.5 | tools | simulate | 300 | 627 | 12.67 to 16.47 | 1.33 to 1.72 | 45 | 3.85 to 5.97 | 7.94 |
| Sonnet 5.5 | no tools | solve | 300 | 300 | 0.57 | 0.11 | 0 | 1.10 | 12.86 |
| Sonnet 5.5 | no tools | validate_domain | 360 | 360 | 0.40 | 0.15 | 0 | 1.15 | 11.46 |
| Sonnet 5.5 | no tools | validate_problem | 600 | 600 | 0.99 | 0.13 | 0 | 1.65 | 19.42 |
| Sonnet 5.5 | no tools | validate_plan | 3,000 | 3,000 | 5.96 | 3.32 | 0 | 22.57 | 98.12 |
| Sonnet 5.5 | no tools | simulate | 300 | 300 | 0.66 | 1.19 | 0 | 6.62 | 9.87 |
| Sonnet 5.5 | tools | solve | 300 | 699 | 6.05 | 0.86 | 0 | 20.67 | 69.35 |
| Sonnet 5.5 | tools | validate_domain | 360 | 720 | 5.16 | 0.52 | 0 | 15.48 | 54.55 |
| Sonnet 5.5 | tools | validate_problem | 600 | 1,200 | 9.52 | 1.13 | 0 | 30.36 | 92.77 |
| Sonnet 5.5 | tools | validate_plan | 3,000 | 6,039 | 55.06 | 6.79 | 0 | 178.05 | 481.16 |
| Sonnet 5.5 | tools | simulate | 300 | 609 | 18.11 | 2.09 | 0 | 57.10 | 73.64 |
| **Haiku 5.5, total** | | | **9,120** | **14,586** | | | | **16.56 to 23.70** | **57.53** |
| **Sonnet 5.5, total** | | | **9,120** | **13,827** | | | | **334.75** | **923.20** |
| **both models** | | | **18,240** | **28,413** | | | | **351.31 to 358.45** | **980.72** |

What stands out: Sonnet's tool arm is about $302 of the estimate, and $178 of that is
validate_plan (3,000 trials, each sending the domain, the problem and the plan twice).
Batching the tool arm would halve that part and give up the same-day rule ([Omer, 1]).
The whole-run estimate, 351 to 358 dollars, is under the 500-dollar line of section 7.
The bound is above it; the bound is what the run would cost if every request wrote its
full output cap, and it is the per-model stop of section 7.

---

## 10. Freeze record

**FROZEN 2026-11-26, about 11:35 UTC.** At that moment Haiku 5.5 was complete in both
arms (4,560 rows each) and Sonnet 5.5's tool arm held 3,924 of 4,560 rows; its batch had
not been fetched. **No row, sidecar answer or outcome of the full run had been read** by
the session or by any agent. What was read before the freeze, as section 6 allows: row
counts; the counts of endings of Haiku's batch (one batch, 4,560 succeeded, none
expired, errored or canceled); the run manifests and the start records (settings,
commits, digests). The analysis refuses to read a row unless it is started with the
package hash below.

| item | value |
|---|---|
| analysis | `tools/reanalysis/frontier55.py`, branch `analysis/frontier55` (the run's branch with `main` merged in), freeze commit: the commit that adds this record |
| package hash (`--i-have-frozen`) | **`0cbb69b7f810d039734b0aba15096bda91a6f97c6c334dfd2a0ec8ed59cbb497`** (38 files: the analysis script and the 37 files of the matched run's package, whose own hash is still `1f3d0f84…`; the rerun's `822aace9…` and the control's `825dab63…` are unchanged). The runner's files are not in it |
| gate 1, typed load | rows through the rerun's frozen loader with the model-name swap of section 2.6; sidecar, manifest and batch records through typed readers that halt on a missing key or an unknown value |
| gate 2, constants as checks | models, arms, 4,560 rows per folder and the per-task counts, the same trials in both arms, 20 domains for RQ1, 10,000 resamples, seed 20261002, the ground-truth sha256, validator 0.1.5, the ten system-text digests, the output caps, the storage cap |
| gate 3, clause map | `frontier55_traceability.md`; nothing of sections 2.5 to 8 is left without code or a named reason |
| gate 4, fixture | `tests/fixtures/frontier55/` (four folders of 300 rows with planted traps and hand-computed values); `tests/test_frontier55_analysis.py`, 1,007 checks in 13 tests, all pass |
| gate 5, independent review | an agent that did not write the code, 2026-11-26, in three passes. First pass on `6f30ffe`: no wrong number in the grade, the denominators or the statistics (three contrasts recomputed independently from the fixture rows matched exactly); one blocker (section 6, "Failed batch items" (2), had no code) and two should-fix items (halt per model; scoring-error rows), six notes. Verification pass on `6fe8442`: no blocker; two should-fix items (a rerun guard; per-model blocking for a request dated before the batch send) and one reading for the owner (point 8 below). Last check on `2905790`: no blocker; the hand case of the share interval recomputed independently. Every item was applied |
| the owner's open points | eight readings the registration leaves open, listed in the clause map. Omer accepted points 1 to 7 as implemented on 2026-11-26 ("Ok, all seven"). Point 8 ("the first batch expired as a whole" read as every item expired) was shown to him the same day and is kept as implemented; it cannot change Haiku's readout (no item of its batch expired), and Sonnet's batch counts are read before the analysis is run: if any item expired, Omer is asked before the run |
| runner | commit `65083c559e0cb69ca678e45fa069fcfd77332ee1` (branch `frontier/claude-55-run`), not edited since. sha256: `runner.py` `9b3e4cec…1f652`, `anthropic_requests.py` `5c4b7665…190dd`, `cost.py` `5118ea98…02b97`, as in every folder's manifest |
| starts | one per folder, all from that commit with no uncommitted change, 2026-11-26 07:16:02 to 07:16:15 UTC; registration sha256 at the start `1a724398…5fc54` (this document before this record) |
| settings, from the manifests | `api.anthropic.com`; SDK 0.109.2 (pinned); Haiku 5.5 effort medium, thinking disabled; Sonnet 5.5 effort high, thinking between tools; temperature not sent; output caps 8,192 (solve) and 6,144 (the other four tasks); up to 10 tool turns; answers stored up to 65,536 characters; ground-truth cache `77d4184e…04c7e` |
| tool checkout | `external/pddl-copilot-5e4f9c0` (a clone of `pddl-copilot` at `5e4f9c0`, pddl-pyvalidator 0.1.5); tool-list sha256 `dd145078…14400` |
| API version header | `2023-06-01` on every request of all four folders (read from the sidecars by the analysis, 2026-11-26) |
| the run, as it ended | all four folders complete at 4,560 rows on 2026-11-26 (Haiku 5.5 about 11:00 UTC, Sonnet 5.5 12:14 UTC); one start per folder; one batch per model, 4,560 of 4,560 items succeeded and none expired, so point 8 did not arise; every request on 2026-11-26 UTC; no refusal, no error row, no abandoned try; spend 20.25 dollars (Haiku 5.5) and 294.49 (Sonnet 5.5), under the limits |
| analysis run | 2026-11-26, after the freeze commit `621f07c`, with the package hash above. The first start halted on tripwire T8 (six notes between tool calls in Sonnet's tool arm with a thinking-token count of zero); the audit is filed in `frontier55_t8_audit/` and embedded in the output. The analysis then ran, and once more unchanged to write `NUMBERS.md` (byte-identical output). No cell VOID, no model left out. Readout: `frontier55_readout.md` |
| the console download | on 2026-11-26 Omer sent the batch results of Sonnet's no-tools arm as downloaded from the provider's console. The file was not opened or used; the runner fetched the same batch (`msgbatch_01VKEaEPUmdUHb5swNcH2Cx5`) itself |
| still to add | the cluster's tool library versions beside the laptop's (section 3, item 7) |
| `--max-usd` | 60 (Haiku 5.5) and 430 (Sonnet 5.5) at the one start of each model |

## 11. Pilot record

**2026-11-26, 07:00 to 07:15 UTC: the pilot passes.** Runner at commit `3dafccc` (branch
`frontier/claude-55-run`), reviewed by a second agent in two passes before any paid
request. Tool checkout: a clone of `pddl-copilot` at `5e4f9c0` with pddl-pyvalidator
0.1.5 (`external/pddl-copilot-5e4f9c0`), tool-list sha256 `dd145078…`. Folder:
`results/frontier55-pilot/`. Never pooled.

- **Before any paid request:** 346 of 346 runner tests; the local tool check agreed with
  the stored reference on 1,520 of 1,520 items.
- **Rows:** 160 in each of the four folders (two models by two arms), 640 in all; every
  answer non-empty; no failed attempt; no refusal, pause or unknown stop.
- **Settings:** no request differed from the registered settings; the returned model
  ids were `claude-haiku-5-5` and `claude-sonnet-5-5` throughout; live requests went to
  `api.anthropic.com` only.
- **Thinking:** zero thinking tokens and zero thinking blocks in all four folders. In
  particular Sonnet 5.5 returned no note between tool calls in any of its 160 tool
  trials, so the pass-back of such notes was not exercised on a real response. The
  runner still checks it on every trial of the full run.
- **Cache tokens:** zero. **Over-length errors:** none.
- **Tool errors:** none flagged by the tool layer; a tool returned an error object in 3
  of 178 Haiku calls and 0 of 164 Sonnet calls.
- **Spend:** Haiku 5.5 0.79 dollars (estimate 0.51 to 0.73); Sonnet 5.5 10.64 dollars
  (estimate 12.30). Batches: `msgbatch_01SUrbfj1mPAXFo5emZpgzx6`,
  `msgbatch_014ArGjkxfnx6HynxfnauFoi`.
- **First contact confirmed:** Haiku 5.5 accepts thinking off at effort medium, with and
  without tools; Sonnet 5.5 accepts its lowest thinking setting with and without tools.
- No success rate, grade or answer text of the pilot was read. The check prints counts
  of how answers ended and nothing else about outcomes.

**Limits given for the full run:** `--max-usd 60` for Haiku 5.5 and `--max-usd 430` for
Sonnet 5.5 (pilot-scaled estimates: about 25 to 35 and about 290 dollars).

## 12. Deviations

None.
