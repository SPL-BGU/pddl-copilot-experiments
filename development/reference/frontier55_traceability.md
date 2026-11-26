# Traceability map: the Claude-run registration to the analysis code (freeze gate 3)

**Frozen 2026-11-26** at package hash `0cbb69b7f810d039734b0aba15096bda91a6f97c6c334dfd2a0ec8ed59cbb497`
(registration, section 10). The independent review (gate 5) ran on commit `6f30ffe`, was
verified on `6fe8442` and checked again on `2905790`; every item it raised is applied
here. The owner's open choices are listed at the end under **Open points**: Omer accepted
points 1 to 7 as implemented on 2026-11-26; point 8 is kept as implemented (registration,
section 10).

Spec: `development/reference/frontier55_prereg.md`, sections 2.1 to 2.3 (constants), 2.5,
2.6, 3, 4, 5, 6, 7 and 8.
Code: `tools/reanalysis/frontier55.py`. A function or constant is cited by its name and
first line, written `` `name` (F:<line>) ``; a statement inside a function is cited as
`F:<line>`. `tests/test_frontier55_analysis.py` checks that every `` `name` (F:<line>) ``
below points at the line that defines that name. Functions of the frozen analyses are
written `CPF:<name>` (`tools/reanalysis/control_prompt_fix.py`), `MR:<name>`
(`tools/reanalysis/matched_run.py`), `S:<name>`, `G:<name>`, `ST:<name>`
(`tools/delivered_rerun/schema.py`, `grade.py`, `stats.py`) and `R23:<name>`
(`tools/reanalysis/rq23_metrics.py`). They are imported and not edited.
Fixture checks: `tests/test_frontier55_analysis.py` (written `T:<test function>`), on the
fixture built by `tests/fixtures/frontier55/build_fixture.py`.

Each entry quotes the clause, then names the code or runtime check, then the fixture check
that exercises it. Clauses that are not testable commitments of the analysis (what the
runner does at run time, what the paper says, what is recorded by hand) are marked "not
analysis code" with the reason. What has no implementation is under **Not implemented**.

Shared mechanics used by many entries:

- every registered constant is a raised check in `check_constants` (F:272) and
  `check_design` (F:396), called at import (F:416) and again in `main` (F:2146). The
  checks call the control's `_check`, which raises `RegisteredCheckFailed` and is not an
  `assert`, so `python -O` cannot strip it; the frozen `constants.py` also refuses `-O`.
  `check_constants` first calls the matched run's own `check_constants`.
  T:test_constants flips every constant and every design field and sees the check fire;
  T:test_package_hash checks `-O` is refused.
- every row is read by `load_row` (F:979), called from `read_cell` (F:1006). It calls the
  frozen `S:parse_row` (F:999) with a `CellSpec` made by `cell_spec` (F:445) from the
  rerun's `spec_rerun_c`, and `read_cell` calls the frozen `S:_check_completeness` (F:1060).
- every sidecar line is read by `parse_meta` (F:630) and `parse_turn` (F:571): exact key
  sets, typed values, registered settings, and the shape of the conversation
  (`check_conversation` (F:707)). A missing key, an extra key or an unknown value raises
  `SidecarError` (F:102). The runner is not imported; T:test_runner_shapes sends rows and
  sidecar lines built by the runner's own functions (the SDK on a mock transport, no
  network) through these readers and compares the constants the two files state.
- each row is checked against its sidecar line by `check_row_meta` (F:928): the error
  text against the outcome, turns and token sums, the no-room and loop-exhausted endings,
  the stored tool calls, the stored answer against the text of the sidecar's last turn.
- grades are read only through `CPF:ok_of` and the `Trial` record (`Trial` (F:1429)) built
  in `grade_cell` (F:1468). No stored grade field is read as the grade.
- the package hash covers this script and every repo file it imports (`DEPENDENCIES`
  (F:96), `package_sha256` (F:429)): the matched run's 37 files and this script. The
  runner's files (`tools/frontier55/`) are not in it. The three frozen hashes are
  untouched: `matched_run --print-package-hash` still ends `1f3d0f84…`,
  `control_prompt_fix` `825dab63…`, `tools.delivered_rerun.run` `822aace9…`
  (T:test_package_hash checks all three).
- a registered rule that sends both arms of one model back to be run again (VOID, failed
  batch items, the later-date share, a tool request dated before the batch) does not stop
  the readout: `screen` (F:1155) leaves
  that model out, `NotAnalysed` (F:106) carries the rule, and the model is printed as "not
  analysed: <rule>" and is in no table (`render`, F:1970). When no model is left the
  analysis halts (F:1172). A fault (a row the loader refuses, a short folder, arms with
  different trials) still halts everything. T:test_refusals (`blocks` cases).
- a model whose two arms were run again in new folders is read from them:
  `--rerun-root MODEL=PATH` and `--rerun-suffix MODEL=SUFFIX` (`parse_reruns` (F:1192),
  `load_run` (F:1178)). The folders read are printed; the first attempt's folders are
  counted and nothing in them is graded (`first_attempt` (F:1274)). A rerun must be a
  new collection: `check_rerun` (F:1251) reads the batch ids, the request ids and the
  request times of the first attempt's sidecar (`first_attempt_requests` (F:1218)) and
  halts, naming the overlap, when the rerun's folders hold a batch id (F:1258) or a
  request id (F:1263) of the first attempt, or a request that is not later than the first
  attempt's last one (F:1268). T:test_reruns (a rerun three days later is read; a copy of
  the first attempt, the first attempt's request ids, and a collection on the first
  attempt's days are each refused).
- live mode reads nothing unless `--i-have-frozen` equals the package hash (F:2209), and
  refuses a folder whose name holds "pilot" (F:2212). T:test_live_gate.

---

## Section 2. Design (constants, gate 2)

### 2.1 Models, tasks and size

> Models `claude-haiku-5-5` and `claude-sonnet-5-5`; five tasks; wordings v11, v12, v13;
> arms no tools and tools; per model and arm 4,560 trials (solve 300, validate_domain 360,
> validate_problem 600, validate_plan 3,000, simulate 300); 18,240 trials; 20 domains.

`MODELS` (F:118), `ARMS` (F:119), `TASKS` (F:120), `WORDINGS` (F:122), `PER_TASK` (F:123),
`N_FOLDER` (F:125), `TOTAL_TRIALS` (F:126), `K_DOMAINS` (F:127), `REGISTERED` (F:252);
checked in `check_constants` and `check_design`. T:test_constants.

> "The two arms of a model hold the same trials. The trial list comes from the harness's
> own enumerator (`pddl_eval.runner.build_jobs`)."

`check_same_trials` (F:1304) halts when the two folders of a model differ in a trial key.
Live mode also builds the registered list with `build_jobs`, as the runner calls it
(`registered_grid` (F:1314): 4,560 trials, the per-task counts, 20 domains, the same list
for both arms) and requires every folder to hold exactly that list (`check_grid`
(F:1334)). T:test_refusals (arms with different trial keys); T:test_units (the list, when
the pinned ground truth is on the machine; a folder that does not hold it is refused).

> "The pilot is its own short list … never pooled with the full run."

Live mode refuses a folder named `*pilot*` (F:2212), and `check_manifest` (F:839) refuses
a folder whose run manifest says `pilot: true` (F:853). T:test_live_gate; T:test_refusals
(manifest: a pilot folder under a full-run name).

### 2.2 Messages

> The table of ten sha256 digests of the system texts.

`SYSTEM_SHA256` (F:129). `check_constants` rebuilds each text from the harness
(`system_text` (F:260): `build_messages`, and `control_prompts.swap_system` on no-tools
solve and simulate) for the three wordings and compares the digest; it also ties the four
solve and simulate digests to the matched run's and the control's constants. Per trial,
`parse_meta` requires the sidecar's `settings.system_sha256` to be the registered one
(F:630), and `check_manifest` the manifest's `system_sha256` table. T:test_constants;
T:test_units; T:test_refusals (sidecar: another system text).

> "Plans in the prompts come from the pinned ground-truth cache … sha256 `77d4184e…c7e`.
> The runner halts on any other file."

`GT_CACHE_SHA256` (F:145). `load_gt_cache` (F:1551) halts on any other file and also
requires the rerun's pinned canonical hash. Every folder's manifest must name the same
file (`read_cell`, the check after `check_manifest`) and the same content
(`ground_truth_sha256`, in `check_manifest`). T:test_units; T:test_refusals (manifest:
another ground truth, another ground-truth file).

### 2.3 Request settings

> The table: thinking `disabled` / `between_tools`; effort `medium` / `high`; output cap
> 8,192 on solve and 6,144 on the other four tasks; at most 10 tool round trips. No
> temperature, top-p or top-k. No other field in a request. `api.anthropic.com`.

`SETTINGS` (F:147), `OUTPUT_CAP` (F:152), `MAX_ROUND_TRIPS` (F:154), `API_HOST` (F:158),
`TRANSPORT` (F:160). Per request: `parse_turn` requires the sidecar's record of the
request to equal `registered_request` (F:559), which fixes the model, the cap, the
thinking setting, the effort, the list of field names (so a sampling field or any other
field halts) and the number of messages (F:579); a live request must have gone to the
registered host (F:613). Per trial: `settings` in `parse_meta`. Per folder:
`check_manifest`. The round-trip limit: `check_conversation`. T:test_refusals (sidecar:
another effort, another output cap, a sampling field, another thinking setting, a request
without its settings, another host, eleven round trips; manifest: another effort, another
output cap, another address).

> "`pddl-copilot` at commit `5e4f9c0`, with pddl-pyvalidator 0.1.5 … The sha256 of the
> tool list built there is `dd145078…`. The run records this digest in its manifest."

`TOOLS_COMMIT` (F:155), `TOOLS_SHA256` (F:156), `PYVALIDATOR` (F:157). `check_manifest`
requires the tool arm's manifest to record that commit, that validator release and that
tool-list digest (F:862), and a no-tools folder to record none. The validator the
analysis itself grades with: `validator_env` (F:1563). T:test_refusals (manifest: another
tool list, another tools commit, another validator release, tools recorded in a no-tools
folder); T:test_runner_shapes (the runner's own manifest is accepted, its pilot manifest
refused).

> "The tool code is the open models' commit. Its dependencies were resolved on another
> machine … This is a record, not a gate."

Not analysis code: a record in the manifest (`tools_env`), read by hand for section 10.

### 2.4 Two routes

> No tools through the Batch API; tools through live calls.

`TRANSPORT` (F:160); `parse_meta` requires `transport` "batch" with a batch id in the
no-tools folders and "live" with none in the tool folders. T:test_refusals (sidecar: the
batch route in the tool arm, a batch id on a live trial).

### 2.5 The tool conversation

> "After a response that asks for a tool, the model's content goes back exactly as it
> came … For Sonnet 5.5 this includes its notes between tool calls."

`apparatus` (F:1401) halts unless the number of notes returned before a next request
equals the number found byte-equal in that request (F:1406); both numbers are in the
apparatus table. T:test_refusals (a note that did not go back unchanged); T:test_base
(40 returned, 40 passed back).

> "All tool results of a turn go back in one user message."

`registered_request`: request n of a trial holds 2n − 1 messages (F:579). T:test_refusals
(turns that are not numbered in order).

> "A tool that raises gives the harness's text `Tool error: …`, marked as an error."

Counted, not gated: per model, arm and task, the tool calls the sidecar flags as errors
and the stored results that start with `Tool error:` (`descriptive` (F:1742)).
T:test_base (Haiku tools validate_problem: one call raised).

> "The conversation ends at the first response that does not ask for a tool."

`check_conversation`: every turn before the last stopped with `tool_use`, and the last
turn of an answer did not. T:test_refusals (sidecar: an answer that stopped for a tool).

> "After 10 round trips still asking for a tool: loop exhausted, the answer is empty."

`check_conversation` (ten turns that all asked for a tool, tool arm only);
`check_row_meta` (`done_reason` "tool_calls" exactly on that outcome, and an empty stored
answer); the ending "loop exhausted" in `ending_of` (F:1449). T:test_traps (loop
exhausted); T:test_runner_shapes.

> "The provider refuses the request because the conversation no longer fits its window …
> recorded as an outcome … `ctx_no_room_turns: 1` … The rerun's loader then reads it as a
> 'no room' row, as for the open models."

`check_conversation` accepts an over-length outcome only in the tool arm and only after a
tool result, in its two forms (a rejected request: the last turn asked for a tool and an
error text is kept; a stop reason `model_context_window_exceeded` on a later turn)
(F:736). `check_row_meta` requires the row's `no_room` exactly on that outcome. The row is
graded by the frozen graders as any no-room row (reason `no_room`, wrong), counted under
"refused for length", kept out of "stopped at the output cap", and stays in RQ2 and RQ3
(tool right, answer wrong) as for the open models. T:test_traps (both forms);
T:test_refusals (an over-length outcome in the no-tools arm); T:test_base.

> The four listed differences from an open model's over-length row (turn count, error
> text, clipping, where it can happen).

Turn count: `check_row_meta` requires `tokens.turns` to equal the number of responses in
the sidecar, which holds in both forms. Error text: not read. Clipping: `check_row_meta`
halts on any clipped-turn field. Where: `check_conversation`, above. T:test_refusals (a
clipped turn does not exist in this run).

> "A refusal by the model (section 3.6)." "A 'pause' stop … the trial is an error row and
> is counted."

`error_kind` (F:900); see section 3 item 6 and section 7 below.

> "If the first request of a trial is rejected as too long, the run of that folder stops."

Runner behaviour. The analysis side: an over-length outcome with no tool result behind it
is refused by `check_conversation`.

### 2.6 What is stored

> "`trials.jsonl`: one row per trial in the harness's row shape, so that the rerun's
> loader and graders read it … The loader knows only the three open models' names, so the
> check swaps the model name for one of them and applies every other rule unchanged."

`load_row`: the row's model and key must name the folder's Claude model; then the name is
swapped for `LOADER_TAG` (F:163) and the row goes through `S:parse_row` unchanged (F:999).
A row that already names an open model is refused. The row's `cell` is its own folder
name; the open model's name reaches no output. T:test_refusals (a row of the other model,
a row that already names an open model, an unknown failure reason, a missing key);
T:test_traps (rows are named by their own folder); T:test_base (the output never names an
open model).

> "An answer longer than 65,536 characters is flagged (`response_truncated_by_storage`
> true, the first 65,536 characters in the row), counted as 'cut by storage', and its full
> text is kept in the sidecar. It is graded from that full text."

`STORAGE_CAP` (F:162). `check_row_meta` requires the row's flag, the sidecar's flag and
the length of the answer in the sidecar's last turn to agree, the sidecar's
`full_answer_if_cut` to be that answer, and the stored characters to be its first 65,536
(F:970). `load_row` reads such a row through the frozen loader with its stored characters
and the flag off (the frozen loader refuses a flagged row) and then gives the typed row
the full answer (F:1002), so every grader reads the full text. Counted per folder and per
cell and listed row by row (`storage_table` (F:1800)). T:test_traps (the cut row is right
only in its full answer); T:test_refusals (four malformed cut rows); T:test_base.

> "`trial_meta.jsonl`: one line per trial …"

`parse_meta`, `parse_turn`, `read_sidecar` (F:754). A row without its line halts (F:992);
a line of a trial that has no row halts (F:1065); a half-written line is counted and
skipped; a second line for the same trial is counted and the last is used (F:774, open
point 3). T:test_refusals; T:test_base (corpus table).

> `attempts.jsonl`, `spend.jsonl`, `spend_<model>.json`, `run_provenance.jsonl`, the lock
> file, `repairs.log`.

Not analysis code: no registered measure reads them. `run_manifest.json` is read
(`check_manifest`).

> "Stop reasons are written in the harness's words … The provider's own word is in the
> sidecar." "Token counts in a row …"

`check_row_meta`: `done_reason` against the sidecar's stop reason (`DONE_OF_STOP` (F:196));
`tokens.prompt`, `tokens.completion` and `tokens.turns` against the sums over the
sidecar's turns (input tokens include cache-written and cache-read). T:test_refusals
(token counts that are not the sidecar's).

### 2.7 A new corpus

> "The rows of this run are never pooled with the open models' runs, with the old Claude
> runs, or with the pilot."

The analysis reads the four folders of this run and nothing else of any model. The two
files of the rerun it reads are the stored validator verdicts (plans and true or false,
for the route check) and the filed re-grade's environment record. No rate, count or row of
another run enters the output. T:test_base (no open model named; every measured row names
one model and one task).

---

## Section 3. What differs from the open models

Items 1, 3, 7 and 8 are statements for the paper: not analysis code. The pointer to them
is in the header of the markdown output (`render` (F:1948)).

> Item 2. "Sonnet's no-tools arm does not think, and its tool arm carries those notes. The
> notes are stored, and their token count is reported."

`MAY_THINK` (F:151). Per model, arm and task: thinking tokens (every integer of a usage
block whose field name holds "thinking" or "reasoning", the runner's rule, `_sum_keys`
(F:543)), thinking blocks, trials with a note (`descriptive`). Tripwire T6 fires on any
note or thinking token in the three folders that may have none; T8 when notes exist and no
token count does (`tripwires` (F:1817)). T:test_base; T:test_tripwires.

> Item 4. "The output cap is in the provider's tokens …" "If Sonnet's final turn reaches
> the cap holding a note and no answer text, the harness's rule labels the row
> `think_overflow` … The analysis maps it to 'stopped at the cap with no answer', the
> label the same event gets for the open models."

`ending_of`: a row that stopped for length with an empty answer is "stopped at the cap
with no answer" whatever its stored label. `grade_cell` raises unless every row labelled
`think_overflow` has that ending, the frozen reason `truncated_empty` and a wrong grade
(F:1507). The count of such rows is printed beside the ending; no ending or reason in the
output is called `think_overflow`. T:test_traps; T:test_base; T:test_runner_shapes (a row
the runner itself labels `think_overflow`).

> Item 5. "Each trial records the model ID the provider returned and its time. Both arms
> of a model are queried on the same UTC day (section 6)."

`apparatus`: the model ids returned and the request dates, per folder (F:1413).
`parse_turn`: a returned id must start with the id asked for. See section 6.

> Item 6. "A refusal is wrong under the grade, stays in the denominator, is kept out of
> the VOID rule of section 7, and is counted and reported per model, arm and task."

`error_kind`: a refusal is the row whose error text is `stop_reason=refusal`. Wrong:
in `grade_cell`, F:1505. In the denominator: every row of a folder is graded, and
`analyse` (F:1883) requires each cell to hold the registered number of trials. Out of
VOID:
`VOID_KINDS` (F:221), `void_rows` (F:1085). Counted: `refusal_table` (F:1794).
T:test_traps; T:test_base; T:test_refusals (eleven refusals of 300 are analysed).

> "An error row (a refusal, a pause, an unknown stop) holds no tool calls and no tokens;
> those are in the sidecar. Such a trial is left out of the four tool-choice classes of
> RQ2 and out of RQ3's 'tool right' set, and is counted beside them, per model and task.
> 'No room' rows are treated as for the open models."

`NAMED_ERROR_KINDS` (F:218). `rq2` (F:1666) skips a row of one of the three named kinds
and counts it by kind (F:1683); `Trial.tool_right` is false for it (F:1518) and `rq3`
(F:1712) counts it beside. Turns and tokens of error rows are taken from the sidecar in
`descriptive`. A trial on which the harness's grader raised is not one of the three: it
is classed by its stored tool calls, and the `tool_selected` self-check is skipped where
the row stores none (F:1691) (open point 1). T:test_base (Sonnet validate_domain: two left
out; simulate and validate_problem: the two scoring-error rows are classed); T:test_traps.

---

## Section 4. The grade

> "A trial is right when the final answer, as the model wrote it, is right. The tool's
> output is never used in place of the final answer."

`grade_cell` reads `row.response` only, which `check_row_meta` ties to the text of the
sidecar's last turn. No tool result enters a grade.

> "Solve and simulate: the matched run's registered grade (its section 3), word for word."

`grade_cell` calls `CPF:frozen_grades` (F:1476) and `MR:grade_trials` (F:1477) unchanged
and takes `Trial.registered`. That function reads the plan in the last closed code block
when it holds a plan (`block_plan`), otherwise the rerun's reading; sends it to the
validator in lower case; and on simulate also counts a trace written one JSON object per
line that equals the key. The validator: release 0.1.5, in process, through the control's
route (`validator_env`, `CPF:live_route`, `CPF:Verdicts`: a verdict that is not a plain
true or false halts). The route is checked against the stored verdicts of the rerun's
plans before any new plan (`check_route_table` (F:1526), open point 5). T:test_traps (the
plan only in the last code block; capitals; one object per line); T:test_planted_answers;
T:test_units.

> "Validate_domain, validate_problem, validate_plan: the rerun's frozen grade. The stated
> verdict must equal the truth."

`grade_cell` takes `G:grade` (through `CPF:frozen_grades`) and raises unless the grade is
right exactly when the stated verdict equals the truth (F:1500). T:test_base;
T:test_traps.

> "Error rows (a refusal, an unknown stop) are wrong under the grade, whatever they
> stored."

F:1505. T:test_traps (the scoring-error row stores a right trace and is wrong).

> "Rows cut by storage: the registered expectation is zero. Any such row is graded from
> the full answer in the sidecar and reported."

Section 2.6 above.

> "RQ2 and RQ3 use the definitions of the open models (`rq23_metrics.py`)."

`rq2` calls `R23:row2` (which calls `R23:classify` and `R23:right_tool`) (F:1686), with
the self-check of `R23:rq2_rows` (the harness rule on the stored calls equals the stored
`tool_selected`). `rq3` takes "tool right" as `R23:rq3_rerun` does: the stored harness
grade of a with-tools row (F:1518, open point 6). The readout says under the RQ3 table
what that check credits: a trial where any call returned the right result, including a
call to a tool other than the task's own (F:2029). T:test_base.

> "Intervals" of the RQ2 and RQ3 shares.

`share` (F:1594): the open models' practice, since section 4 binds RQ2 and RQ3 to their
definitions and the rows stand beside theirs. The interval is `rq1_metrics.boot`, as
`rq23_metrics` and the matched run's `rq3_cells` call it: the frozen domain-cluster
bootstrap over the domains the subset holds. The number of domains k is printed beside
the cell whenever it is under 20 (`share_cell` (F:1603)); an empty subset has no share and
no interval, as the frozen helper returns. The 20 domains stay asserted on the RQ1 rates
and contrasts, where the registration states them (`CPF:rate`, `CPF:paired`).
T:test_base (every share of the base fixture reaches 20 domains and no k is printed);
T:test_tripwires (a tool-right set of 57 trials in 19 domains with one wrong: 1.8 [0.0,
5.3], k = 19, by hand; the helper on 20 and on 2 domains).

> "No row of the full run is read before the analysis is frozen."

The `--i-have-frozen` gate (F:2209). Not code: nobody opened a row while this was
written; the fixture is synthetic.

> "The runner also stores the harness's own online grade in each row … No reading uses
> it."

RQ1, the verdict errors and every descriptive count use `Trial.registered`. The one use of
the stored grade is RQ3's "tool right" set (open point 6). T:test_traps (a no-tools row
the harness stored as wrong is right under the grade).

---

## Section 5. Measures and contrasts

> "Per model and task. Nothing is pooled over models or tasks."

Every table of `analyse` is keyed by model and task (and arm). The per-folder corpus table
holds counts of rows and of error rows only, which the VOID rule needs. T:test_base.

> "RQ1. The rate right in each arm, and tools minus no tools, paired on the trial (task,
> domain, problem, plan label, wording), in points. 10 contrasts."

`rq1` (F:1610): `CPF:rate` per arm (F:1623); `CPF:paired` with the no-tools arm first, so
the difference is tools minus no tools (F:1624), on the loader's `trial_key` (task,
domain, problem, plan label, wording); every contrast must pair all its trials with none
left over. `N_CONTRASTS` (F:168). T:test_base (20 rates, 10 contrasts, hand values).

> "Verdict errors, on the three validation tasks, in each arm: valid inputs called
> invalid, and invalid inputs called valid, with counts."

`verdict_errors` (F:1643), with `rq1_metrics.confusion`, F:1651; the truth is
`e2e_regrade.truth_for`, the function the frozen grader uses. T:test_base.

> "RQ2. Tool choice in the tool arm: the four classes, with counts." "RQ3. Tool right and
> answer wrong."

`rq2`, `rq3`. T:test_base (hand counts; share intervals from hand-built inputs).

> "Intervals. 95% percentile intervals from the rerun's domain-cluster bootstrap: 20
> domains, 10,000 resamples, seed 20261002."

`LEVEL` (F:169), `B_BOOT` (F:170), `SEED` (F:171), tied in `check_constants` to the frozen
constants the bootstrap reads. `CPF:rate` and `CPF:paired` call `ST:cluster_bootstrap`
with k = 20 asserted. T:test_base (hand intervals); T:test_constants (k = 20 is asserted).

> "'Tools ahead' when the interval is above 0, 'no tools ahead' when it is below 0, 'no
> difference shown' otherwise. Beside each contrast, an exact sign-flip p-value over the
> 20 domains, Holm-adjusted across the five tasks of a model. A difference whose interval
> excludes 0 and whose adjusted p-value is 0.05 or more carries the words '(not after
> Holm)'."

`CPF:paired` (sign-flip p on the domain sums); `ST:holm` over the five tasks of a model
(F:1629), `HOLM_FAMILY` (F:172), `HOLM_ALPHA` (F:173); the label by `CPF:c4_label`
(F:1632), whose six cases `check_constants` checks word for word; `LABELS` (F:174),
`NOT_AFTER_HOLM` (F:175). T:test_base (all three labels and both "(not after Holm)"
forms); T:test_constants.

> "Readings that would be wrong, named in advance."

`WRONG_READINGS` (F:234), printed in the output (F:1985). The output holds no pooled
figure and no number of another run.

> "Descriptive, with counts: right answers by wording; answers that stopped at the output
> cap; loop-exhausted trials; trials the provider refused for length; refusals; other
> error rows; turns per trial; input and output tokens per trial; for Sonnet, the thinking
> tokens between tool calls; the model IDs returned and the dates."

`descriptive`: F:1762 (by wording), F:1766 (cap), F:1769 (loop), F:1770 (refused for
length), F:1771 (refusals), F:1772 (other error rows), F:1775 (turns), F:1777 (tokens),
F:1779 (thinking tokens). `apparatus`: F:1413 (model ids), F:1414 (dates). T:test_base.

---

## Section 6. Execution

Order of steps, the dry run, the tools self-check, the pilot and its twelve checks, resume
and batch handling: runner and human steps, not analysis code.

> "The same-day rule. Both arms of a model count as 'the same day' when the batch was
> sent and every tool trial was requested on one UTC date. The sidecar holds the times."

`same_day` (F:1348), from the request times of the sidecar (`parse_time` (F:525), read in
UTC). T:test_base (Haiku same day; Sonnet not).

> "If the batch does not end that day … the date sent and the date ended are both
> reported."

`same_day`: the dates sent and ended, per batch id. T:test_base (Sonnet's batch ended the
next day).

> "If the tool arm does not finish that day … The trials requested on a later date are
> counted and reported. If more than 5% of a model's tool trials fall on a later date,
> both arms of that model are run again together."

`same_day` counts the tool trials with a request on a later UTC date than the batch's
send date; above `LATER_FRAC` (F:178) the model is not analysed (F:1393). How a trial is
dated is open point 4. A tool request dated before the batch was sent is another fault
than a late trial: that model is not analysed, under its own rule, and the other model's
readout goes on (F:1362). T:test_base (3 of 300); T:test_refusals (16 of 300: that model
is not analysed, the other is; 15 of 300 is analysed; a request dated before the batch:
that model is not analysed, the other is).

> "A model ID that changes within a folder stops that folder."

`read_cell` halts when a folder holds more than one returned id (F:1069). T:test_refusals.

> "Completeness. 4,560 rows per folder, with the per-task counts of section 2.1, and the
> same trials in both arms of a model. A short folder is resumed, not analysed."

`read_cell`: the frozen `S:_check_completeness` (rows, rows per wording, rows per task and
wording, 20 domains) (F:1060) and the per-task totals (F:1062); duplicate keys halt;
`check_same_trials`; live: `check_grid`. T:test_refusals (a short folder, a missing
folder, per-task counts, different trial keys, a duplicate key).

> "Failed batch items, in this order. (1) Items that come back failed, canceled or
> expired are sent again once, in a second batch, the same day. (2) If after that more
> than 1% of the arm's trials are still without a row, or if the first batch expired as a
> whole, both arms of that model are run again together in new folders, and the first
> attempt is kept and reported."

`read_batches` (F:804) reads the `batches.json` the runner keeps in a no-tools folder:
one entry per batch in the order sent, with its number of requests and the provider's
request counts (`Batch` (F:797)); a missing key, a batch that was not fetched, counts
that do not add up or entries out of order halt. `failed_batch_rule` (F:1105): a folder
is complete when it is read, so the trials that had no row after the retry batch are the
rows whose sidecar line names a third or later batch. More than `BATCH_RETRY_FRAC`
(F:179) of the folder's rows (F:1138), or a first batch whose requests all expired
(F:1133): the model is not analysed. Rows of a batch the record does not list, or more
rows than a batch's succeeded requests, halt. The batches and their rows are printed. A
folder with any trial still missing is refused by completeness. The rerun "in new
folders" and the first attempt "kept and reported": `parse_reruns` and `first_attempt`,
above. T:test_base (three rows of 300 from a third batch: exactly 1%, analysed);
T:test_refusals (a fourth row: not analysed; the first batch expired as a whole: not
analysed; seven malformed batch records); T:test_runner_shapes (the batch record the
runner's own functions write); T:test_reruns.

---

## Section 7. Stop rules

The invalid-request stop, the seven-trials stop, spend and `--max-usd`: runner behaviour.

> "A folder is VOID when more than 1% of its rows are error rows that are not refusals
> (unknown stop, pause). Both arms of that model are then run again together … Refusals
> are outcomes and do not count toward this rule … the analysis of this run must separate
> the two by the row's error text (`stop_reason=refusal`)."

`VOID_FRAC` (F:181), `error_kind`, `counts_toward_void` (F:1078), `void_rows`, `is_void`
(F:1090), `void_rule` (F:1094): the model with a VOID folder is not analysed, the other
model's readout goes on. A trial on which the harness's grader raised counts only where
the rerun's `is_exception` holds (open point 1). When all four folders are VOID the
analysis halts and says that a guard firing everywhere is a fault to trace (F:1160).
T:test_traps (3 of 300 is not VOID; five refusals do not count; a scoring error labelled
`loop_exhausted` does not count); T:test_refusals (4 of 300 in a tool folder; 4 of 300 in
a no-tools folder; all four folders; no model left); T:test_units (45 and 46 of 4,560).

> "The storage rule: any row cut by storage is reported and graded from the sidecar."

Section 2.6 above.

---

## Section 8. The reporting rule

> "1. This run is what the paper reports for the frontier models, for the three questions:
> the rate of each arm, the contrast of section 5 with its interval and label, the verdict
> errors, the tool choice and the tool-right-answer-wrong share, whatever they show."

`render`: one table for each, with nothing left out by a result.

> "2. The Claude rows stand beside the open models' rows and are not ranked against them."

No open-model number is in the output. Items 3, 4 and 5: not analysis code.

---

## Readout-time tripwires (freeze protocol, not registration clauses)

`tripwires` (F:1817). A fired tripwire halts and prints; it is released only by
`--audited-tripwires` with a written note per id, and the note is printed in the readout
(F:1905). T1 the same count of right answers on a task in all four folders (not
evaluated when one model is not analysed); T2 a cell
where the grader reads no answer at all; T3 a tool-arm cell where no trial called a tool;
T4 more than 5% of a cell's final answers that no reader read (`UNREAD_FRAC` (F:183));
T5 more than 10% refusals in a cell (`REFUSAL_TRIPWIRE_FRAC` (F:184)); T6 thinking where
the registration has none; T7 a response over its output cap; T8 notes without a
thinking-token count (if the provider does not report thinking tokens apart, T8 fires for
Sonnet's tool arm by design, and its message says what the audit must establish: the
notes are present, no usage field counts them apart, so their tokens are inside the
output tokens and are reported as "not separable", F:1860); T9 the two arms of a model
each returned one model id and the two differ (F:1871). All four folders VOID halts in
`screen`. T:test_tripwires.

The per-folder counts of refusals and of error rows in the corpus table are labelled as
bookkeeping for the VOID rule; the reported counts are per model, arm and task (F:2106).

---

## Not implemented

Nothing in sections 2.5, 2.6, 3, 4, 5, 6 (completeness, same-day, later-date share, failed
batch items), 7 (VOID, storage) and 8 is left without code or a named reason. The first
candidate (commit `6f30ffe`) had no code for section 6, "Failed batch items" (2); the
independent review found it, and `failed_batch_rule` now implements it.

## Open points for the owner (marked `# OPEN:` in the code)

1. **A trial on which the harness's own grader raised** (`error_kind`, F:900). The
   registration lists a refusal, a pause and an unknown stop as error rows and is silent
   on this one. Implemented, the reading that follows the open models' rules: wrong under
   the grade; counted toward VOID only where the rerun's `is_exception` holds (so not a
   row the harness labelled `loop_exhausted`); classed in RQ2 by its stored tool calls;
   never in RQ3's "tool right" set, because its stored grade is wrong. Other reading: an
   error row like the three named ones (counts toward VOID whatever its label; left out of
   RQ2 and counted beside).
2. **How a row cut by storage is told** (`check_row_meta`, F:928). Implemented: the row's
   flag, the sidecar's flag and the length of the answer in the sidecar must agree, or the
   analysis halts. Other option: go by the row's flag alone.
3. **A trial with more than one sidecar line** (`read_sidecar`, F:754). Implemented: the
   last line is used, the earlier ones are counted, and the line used must agree with the
   row. Other option: halt on any repeated key.
4. **How a tool trial is dated for the later-date rule** (`same_day`, F:1348).
   Implemented: the reference date is the earliest date a batch of the model was sent; a
   tool trial counts when any of its requests has a later UTC date. Other option: date a
   trial by its first request.
5. **The validator route check** (`check_route_table`, F:1526, and `validator_env`,
   F:1563). The matched run's grade halts when the route does not return the stored
   verdicts of the rerun's plans, and requires the validator server file of the filed
   re-grade. Implemented: both, the first on all 740 plans of the stored table. Other
   option: drop them, since this registration does not repeat those sentences.
6. **"Tool right" in RQ3** (`rq3`, F:1712). Section 4 says no reading uses the harness's
   online grade; it also gives RQ3 the definitions of `rq23_metrics.py`, where "tool
   right" is that stored grade on a with-tools row. Implemented: the stored grade, for
   RQ3's denominator only. Other option: work out "tool right" again from the stored tool
   results.
7. **The tripwires** (`tripwires`, F:1817). The registration names none; the nine above
   are this analysis's own. Other options: other thresholds, or fewer wires.
8. **"The first batch expired as a whole"** (`failed_batch_rule`, F:1105). Implemented:
   every request of the first batch expired; item (1) of the same rule sends single
   expired items again once, so they are the ordinary retry case. Other reading: any
   expired item means the batch ran into its 24-hour limit, and that already sends the
   model back.
