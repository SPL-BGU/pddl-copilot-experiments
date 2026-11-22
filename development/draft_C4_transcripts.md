# C4: example transcripts from the delivered rerun, drawn by a stated rule

Written by `tools/reanalysis/c4_select_transcripts.py` (do not edit by hand; change the script and rerun it). Plan step C4 (`development/weakness_action_plan.md`). Descriptive: not a gate and not part of the frozen analysis. Ready for E3 to lift into an appendix.

## How the examples were chosen

The rule was fixed before any row was drawn. Two parts of it were set after looking at the pools as a whole, never at a drawn row: the length caps (after the spread of answer lengths in each pool) and example 4's same-length filter (after the shape table below showed that 17 of the 38 solve WRONG_FACTS rows are goal facts read as plan steps and that only 5 keep the tool plan's length with some actions changed). Example 1's list of doubt words (given below the numbered rules) was also chosen after looking: it was written with the readers' notes on the 60 no-call answers in view, and those notes include the notes on the row later drawn. The git history cannot show that the list was fixed before the draw, because the list, the draws and the readings first appear in the same commit. Rule 4b was added after a draw; it says so.

1. Each example has an **eligible set**, defined by the filters in the tables below. Rows come from the three Part A tool cells of the delivered rerun (Gemma 4 26B-A4B, Qwen3.5-9B, Qwen3.6-35B-A3B; minimal system prompt; plain and steered wordings), loaded by the frozen loader and graded by the frozen delivered grader. The script first checks that its grades reproduce the E1 and E4 counts of the frozen readout.
2. The eligible ids are sorted, then shuffled once with Python's `random.Random(20261109 + k)` for example k (seed **20261109**). The first id in that order is drawn.
3. **Length caps** keep an excerpt to about a page: the final answer is at most 3,000 characters (example 1), 1,500 (example 2) and 3,000 (example 4). Example 3 has no answer to cap; its tool result is the point, so it is shown abridged.
4. **Reading and redraw.** Each drawn transcript is read in full. The readings recorded below were drafted by an AI session, Claude Code, on 2026-11-09 and pending Omer's confirmation. If a reading finds the row does not show what the example is meant to show (for example the verdict is right but the reasoning is wrong), the row is recorded below as rejected with the reason, and the next id in the same shuffled order is taken.
4b. **Prompt-rebuild check** (automatic, run before the reading). For simulate and validate_plan rows that called a tool with a `plan` argument, the plan the model passed must be the plan in the rebuilt prompt (actions compared with parentheses, case and spacing ignored). A row that fails is skipped the same way, because its prompt cannot be shown as the model saw it. *This check was added after the first draw for example 3 failed it* (see side finding 2); it changes no eligible set, only which drawn rows can be shown, and the skipped row is listed with the reason.
5. **Abridging.** Long PDDL, plans and tool output are cut to their first and last lines (domain 14+2, problem 8+10, plan 20+5, tool result 30+8 lines). In example 4 the answer and the planner result keep instead the lines around the steps that differ. Every cut is marked in the text as `[... N lines of X elided ...]`. A tool argument that equals the prompt's domain or problem text (byte for byte, once whitespace is collapsed, or once `;` comment lines are also dropped) is not repeated; the line says which. A single line longer than 300 characters is cut in the middle, also marked.
6. **The prompt is not stored** in the rows. It is rebuilt with the harness's own `build_jobs` and `build_messages` from `domains/` and the pinned ground-truth cache. The tool schemas the model saw (all tools of `pddl-copilot` at `5e4f9c0`) are not reproduced.

Example 1 draws from the 60 no-call answers that two readers already read in full (`results/delivered-rerun-secondary/nocall_sample/`, readings in `development/reference/delivered_rerun_secondary/hand_reads/nocall_readings.json`). A row is dropped when either reader's note contains one of these words (case-insensitive): 'wrong', 'doubtful', 'dubious', 'muddled', 'retract', 'flip', 'contradict', 'sloppy', 'garbled', 'hedg', 'conditional', 'worry', 'elide', 'skip', 'not a full', 'no full', 'not a step trace', 'no real check', 'without confirming', 'misread', 'loose'.

## Eligible sets

**Example 1: Gemma skips the tool and judges the plan correctly in prose**

| filter | rows |
|---|---|
| packets in the hand-read sample | 60 |
| both readers: verdict right | 54 |
| ... and no reader note flags the reasoning | 39 |
| ... and final answer <= 3,000 characters | 24 |

Dropped by a reader note: `gemma4_26b-a4b|validate_plan|plain|depots|p05|b2|v12` ('wrong'); `gemma4_26b-a4b|validate_plan|plain|counters|p01|b5|v13` ('loose'); `gemma4_26b-a4b|validate_plan|plain|barman|p05|v1|v12` ('no full'); `gemma4_26b-a4b|validate_plan|plain|zenotravel|p02|b4|v13` ('muddled'); `gemma4_26b-a4b|validate_plan|plain|rovers|p03|v5|v12` ('loose'); `gemma4_26b-a4b|validate_plan|plain|depots|p05|b4|v13` ('muddled'); `gemma4_26b-a4b|validate_plan|plain|depots|p03|v5|v11` ('wrong'); `gemma4_26b-a4b|validate_plan|plain|satellite|p02|v3|v13` ('hedg'); `gemma4_26b-a4b|validate_plan|plain|depots|p03|v3|v11` ('worry'); `gemma4_26b-a4b|validate_plan|plain|rovers|p05|b1|v11` ('sloppy'); `gemma4_26b-a4b|validate_plan|plain|rovers|p05|v1|v12` ('without confirming'); `gemma4_26b-a4b|validate_plan|plain|rovers|p02|b1|v13` ('garbled'); `gemma4_26b-a4b|validate_plan|plain|tpp|p03|b4|v11` ('elide'); `gemma4_26b-a4b|validate_plan|plain|depots|p05|b1|v13` ('wrong'); `gemma4_26b-a4b|validate_plan|plain|barman|p05|b1|v12` ('retract').

**Example 2: A correct relay: the tool result is right and the delivered answer is right**

| filter | rows |
|---|---|
| solve rows (3 models x 2 arms) | 1,800 |
| tool-verified right and delivered right | 1,572 |
| ... and exactly one tool call, to a planner | 628 |
| ... and final answer <= 1,500 characters | 576 |

**Example 3: Simulate: the tool result fills the context window**

| filter | rows |
|---|---|
| simulate rows (3 models x 2 arms) | 1,800 |
| tool-verified right, delivered wrong (E4 rows) | 1,266 |
| ... and E4 label 'final turn refused: prompt filled the window' | 752 |
| ... and exactly one tool call, to get_state_transition | 686 |

**Example 4: Solve: a transcription error (the answer restates the tool's plan with a change)**

| filter | rows |
|---|---|
| solve E4 rows labelled WRONG_FACTS | 38 |
| ... and the answer has as many actions as the tool plan, some different | 5 |
| ... and final answer <= 3,000 characters | 5 |

How the delivered plan differs from the tool's plan, over all solve WRONG_FACTS rows (descriptive):

| shape | rows |
|---|---|
| tool plan, then extra lines | 18 |
| other | 10 |
| extra lines, then tool plan | 5 |
| same length, some actions differ | 5 |

**Side finding 1: goal facts read as plan steps (not a transcription error).** In 17 of the 18 "tool plan, then extra lines" rows, every extra line is an atom of the problem's goal. The answer repeats the tool's plan action for action and then lists the goal's facts, each in parentheses on its own line. The delivered grader's line extractor reads those goal facts as more plan steps, and the longer plan fails validation. So these rows count as delivery failures although the tool's (valid) plan is in the answer intact. By model: Qwen3_5_9B 15, qwen3_6_35b 2. The frozen grade is not changed here. The rows: `Qwen3_5_9B|solve|plain|barman|p05||v11`, `Qwen3_5_9B|solve|steered|blocksworld|p04||v16`, `Qwen3_5_9B|solve|plain|depots|p04||v13`, `Qwen3_5_9B|solve|plain|depots|p04||v11`, `Qwen3_5_9B|solve|steered|depots|p04||v16`, `Qwen3_5_9B|solve|plain|depots|p05||v11`, `Qwen3_5_9B|solve|steered|depots|p05||v14`, `Qwen3_5_9B|solve|steered|rovers|p01||v16`, `Qwen3_5_9B|solve|plain|satellite|p05||v13`, `Qwen3_5_9B|solve|steered|satellite|p05||v16`, `Qwen3_5_9B|solve|plain|tpp|p03||v11`, `Qwen3_5_9B|solve|plain|tpp|p03||v13`, `Qwen3_5_9B|solve|plain|tpp|p05||v13`, `Qwen3_5_9B|solve|steered|tpp|p05||v16`, `Qwen3_5_9B|solve|plain|depot|p04||v13`, `qwen3_6_35b|solve|steered|blocksworld|p04||v16`, `qwen3_6_35b|solve|steered|satellite|p01||v16`.

## Side finding 2: the simulate plan in the run is not always the cached plan

The harness builds each simulate prompt from the planner's plan, computed live when the run starts; the delivered grader's oracle is the pinned ground-truth cache. For each simulate problem, the script compares the plan every with-tools row passed to `get_state_transition` with the cache's plan (actions compared with parentheses, case and spacing ignored). It lists the problems where no row passed the cache's plan and at least 90% of the rows passed one same other plan, so the run's prompt must have held that other plan. 6 of 100 problems:

| problem | rows | rows passing a plan | rows passing the modal plan | modal plan actions | cache plan actions | rows whose final turn had no room |
|---|---|---|---|---|---|---|
| barman p01 | 18 | 18 | 17 | 30 | 28 | 18 |
| barman p02 | 18 | 17 | 17 | 14 | 14 | 17 |
| barman p03 | 18 | 18 | 18 | 30 | 34 | 18 |
| barman p04 | 18 | 18 | 18 | 61 | 59 | 18 |
| barman p05 | 18 | 18 | 18 | 61 | 65 | 18 |
| gripper p03 | 18 | 18 | 18 | 11 | 11 | 18 |

On these problems nearly every with-tools row ended with no room for the final turn. For those rows the delivered grade fails before any trajectory is compared, so the cache's plan is not used. With-tools rows on these problems that the online grade passed, that had room, and that the delivered grade fails: 0. Part C (no tools) rows on these problems that the online grade (live ground truth) passed and the delivered grade (cache oracle) fails: 1 (`qwen3_6_35b|simulate|plain|gripper|p03||v11`, whose answer's actions are exactly the plan the with-tools rows passed). A row like that simulated the run's plan correctly and is graded against a different plan. Over all 900 Part C simulate rows (any problem), the rows the online grade passes and the delivered grade fails are: `qwen3_6_35b|simulate|plain|gripper|p03||v11`. The frozen readout is not changed here; this is reported for the main session to decide on.

---

## Example 1. Gemma skips the tool and judges the plan correctly in prose

| field | value |
|---|---|
| served model | `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`: community AWQ 4-bit quantisation (Hugging Face uploader `cyankiwi`) of Google's Gemma 4 26B-A4B instruct model; not the official Google weights |
| serving | vLLM 0.20.2, temperature 0.0, context window 16,384 tokens, thinking off, all tools visible, system prompt style `minimal` |
| cell file | `results/delivered-rerun/slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_delivered-rerun/trials.jsonl`, line 7265 |
| trial key (as stored) | `["cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit", "validate_plan", "counters", "p04", "b2", 11, true, "off", "all", "minimal"]` |
| task / domain / problem / plan / wording | validate_plan / counters / p04 / b2 / v11 (plain arm) |
| stored grade (tool-verified) | success=False, failure_reason=`tool_not_selected` |
| delivered grade (frozen grader) | ok=True, reason=`verdict_stated_ok` |
| tokens | prompt 3,580 (summed over turns), completion 588, turns 1, clipped turns 0, no-room turns 0, done_reason `stop` |

Drawn: position 1 of 24 in the shuffled order (seed 20261109 + 1). Trial id `gemma4_26b-a4b|validate_plan|plain|counters|p04|b2|v11`.

Reader A, method: "tracks counter values, finds goal not met". Reader B, method: "notes rate is zero so value never changes, goal fails". Both: verdict INVALID, right.

**System prompt** (rebuilt with `pddl_eval.runner.build_messages`):

```text
You are a PDDL validation assistant. LLMs cannot reliably check plan correctness from training alone. Use the available validation tool to check whether the plan solves the problem.
```

**User prompt** (rebuilt the same way; long PDDL abridged, elisions marked):

```text
Validate whether this plan is correct for the given domain and problem.

Domain:
(define (domain fo-counters-rnd)
    (:requirements :strips :typing :equality :adl :fluents)
    (:types counter)
  (:predicates
    (nop ?x - counter)
  )

    (:functions
        (value ?c - counter);; - int  ;; The value shown in counter ?c
        (rate_value ?c - counter);;
        (max_int);; -  int ;; The maximum integer we consider - a static value
    )

    ;; Increment the value in the given counter by one
[... 22 lines of the domain elided ...]
    )
)

Problem:
;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_3_100)
	(:domain fo-counters-rnd)
	(:objects
		c0 c1 c2 - counter
	)
  (:init
		(= (value c0) 14)
[... 7 lines of the problem elided ...]
		(= (max_int) 100)
	)
	(:goal
		(and
			(<= (+ (value c0) 1) (value c1))
	(<= (+ (value c1) 1) (value c2))
		)
	)
)


Plan:
(increment c1)
(increment c1)
(increment c1)
(increment c1)
(increment c1)
(increment c1)
(increment c1)


End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID
```

**Final answer** (verbatim, 1,510 characters):

```text
To validate the plan, we need to check if the actions are executable and if the final state satisfies the goal.

**Initial State:**
- `(value c0) = 14`, `(rate_value c0) = 0`
- `(value c1) = 8`, `(rate_value c1) = 0`
- `(value c2) = 82`, `(rate_value c2) = 0`
- `(max_int) = 100`

**Goal:**
1. `(value c0) + 1 <= (value c1)` $\Rightarrow$ `14 + 1 <= (value c1)` $\Rightarrow$ `15 <= (value c1)`
2. `(value c1) + 1 <= (value c2)` $\Rightarrow$ `(value c1) + 1 <= 82`

**Plan Execution:**
The plan consists of 7 `(increment c1)` actions.
However, let's look at the precondition for the `increment` action:
`(:action increment :parameters (?c - counter) :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int))) :effect (and (increase (value ?c) (rate_value ?c))))`

In the initial state, `(rate_value c1) = 0`.
1. **Action 1: `(increment c1)`**
   - Precondition: `(value c1) + (rate_value c1) <= 100` $\Rightarrow$ `8 + 0 <= 100` (True)
   - Effect: `(increase (value c1) 0)`
   - New `(value c1)`: `8 + 0 = 8`

Since `(rate_value c1)` is 0, the `increment` action adds 0 to the `value`. No matter how many times `(increment c1)` is called, the `value` of `c1` will remain 8 because the rate is 0 and there are no `increase_rate` actions in the plan to change it.

**Final State Check:**
- `(value c0) = 14`
- `(value c1) = 8`
- `(value c2) = 82`

**Goal Check:**
1. `(value c0) + 1 <= (value c1)` $\Rightarrow$ `14 + 1 <= 8` $\Rightarrow$ `15 <= 8` (False)

The goal is not satisfied.

VERDICT: INVALID
```

**Reading** (drafted by an AI session, Claude Code, on 2026-11-09 and pending Omer's confirmation). Confirmed (read in full on 2026-11-09, against `domains/numeric/counters/p04.pddl` and `p04_b2.plan`). Every rate starts at 0, so each `(increment c1)` adds 0 and `c1` stays at 8. The goal needs value(c0) + 1 <= value(c1), that is 15 <= 8, which fails. The answer reasons exactly this way and ends in `VERDICT: INVALID`: the right verdict for the right reason. It makes no tool call and does not mention a tool.

---

## Example 2. A correct relay: the tool result is right and the delivered answer is right

| field | value |
|---|---|
| served model | `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`: community AWQ 4-bit quantisation (Hugging Face uploader `cyankiwi`) of Google's Gemma 4 26B-A4B instruct model; not the official Google weights |
| serving | vLLM 0.20.2, temperature 0.0, context window 16,384 tokens, thinking off, all tools visible, system prompt style `minimal` |
| cell file | `results/delivered-rerun/slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_delivered-rerun/trials.jsonl`, line 139 |
| trial key (as stored) | `["cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit", "solve", "miconic", "p04", "", 12, true, "off", "all", "minimal"]` |
| task / domain / problem / plan / wording | solve / miconic / p04 / - / v12 (plain arm) |
| stored grade (tool-verified) | success=True, failure_reason=`ok` |
| delivered grade (frozen grader) | ok=True, reason=`plan_valid`, plan extracted by `strict_lines` |
| tokens | prompt 7,671 (summed over turns), completion 640, turns 2, clipped turns 0, no-room turns 0, done_reason `stop` |

Drawn: position 1 of 576 in the shuffled order (seed 20261109 + 2). Trial id `gemma4_26b-a4b|solve|plain|miconic|p04||v12`.

**System prompt** (rebuilt with `pddl_eval.runner.build_messages`):

```text
You are a PDDL planning assistant. LLMs cannot reliably generate correct plans from training alone (arXiv:2509.12987). Use the available planner tool to produce the plan.
```

**User prompt** (rebuilt the same way; long PDDL abridged, elisions marked):

```text
Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`.

Domain definition:
(define (domain miconic)
(:requirements :typing)
(:types floor passenger)

(:predicates
    (origin ?person - passenger ?floor - floor)
    (destin ?person - passenger ?floor - floor)
    (above ?floor1 - floor ?floor2 - floor)
    (boarded ?person - passenger)
    (served ?person - passenger)
    (lift-at ?floor - floor))

(:action board
    :parameters (?f - floor ?p - passenger)
[... 17 lines of the domain elided ...]

)

Problem definition:



(define (problem mixed-f3-p3-u0-v0-d0-a0-n0-A0-B0-N0-F0)
   (:domain miconic)
   (:objects p0 p1 p2 - passenger
             f0 f1 f2 - floor)

[... 23 lines of the problem elided ...]
(lift-at f0)
)


(:goal (and
(served p0)
(served p1)
(served p2)
))
)
```

The model's intermediate assistant text is not stored; the rows keep each tool call's name, arguments and result, and the final answer.

**Tool call 1: `classic_planner`**, arguments:

- `domain`: the domain text of the prompt, the same once whitespace is collapsed (1,002 characters)
- `problem`: the problem text of the prompt, the same once whitespace is collapsed (365 characters)

**Tool result 1** (246 characters, 15 lines):

```json
{
  "plan": [
    "(up f0 f1)",
    "(board f1 p0)",
    "(board f1 p1)",
    "(board f1 p2)",
    "(down f1 f0)",
    "(up f0 f2)",
    "(depart f2 p2)",
    "(depart f2 p0)",
    "(down f2 f0)",
    "(depart f0 p1)"
  ],
  "solve_time": 0.234
}
```

**Final answer** (verbatim, 162 characters; it starts with the leaked channel marker `<|channel>thought` / `<channel|>` that the grader strips once):

```text
<|channel>thought
<channel|>(up f0 f1)
(board f1 p0)
(board f1 p1)
(board f1 p2)
(down f1 f0)
(up f0 f2)
(depart f2 p2)
(depart f2 p0)
(down f2 f0)
(depart f0 p1)
```

**Reading** (drafted by an AI session, Claude Code, on 2026-11-09 and pending Omer's confirmation). Confirmed (read in full on 2026-11-09). One planner call. After the leaked channel marker, the answer is the tool's 10 actions in the same order, nothing added and nothing dropped. The grader strips the marker once, extracts the 10 lines, and the validator accepts the plan.

---

## Example 3. Simulate: the tool result fills the context window

| field | value |
|---|---|
| served model | `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`: community AWQ 4-bit quantisation (Hugging Face uploader `cyankiwi`) of Qwen3.6-35B-A3B; not the official Qwen weights |
| serving | vLLM 0.20.2, temperature 0.0, context window 16,384 tokens, thinking off, all tools visible, system prompt style `minimal` |
| cell file | `results/delivered-rerun/slurm_vllm_qwen3_6_35b_off_tools_all_minimal_delivered-rerun/trials.jsonl`, line 8598 |
| trial key (as stored) | `["cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit", "simulate", "depots", "p03", "", 16, true, "off", "all", "minimal"]` |
| task / domain / problem / plan / wording | simulate / depots / p03 / - / v16 (steered arm) |
| stored grade (tool-verified) | success=True, failure_reason=`ok` |
| delivered grade (frozen grader) | ok=False, reason=`no_room` |
| E4 label (frozen e4.classify) | REFUSED_OR_CLIPPED_FINAL (final turn refused: prompt filled the window) |
| tokens | prompt 20,987 (summed over turns), completion 1,042, turns 2, clipped turns 0, no-room turns 1, done_reason `length` |

Drawn: position 2 of 686 in the shuffled order (seed 20261109 + 3). Trial id `qwen3_6_35b|simulate|steered|depots|p03||v16`.

Skipped before this draw (redraw rule):

- position 1, `gemma4_26b-a4b|simulate|steered|barman|p01||v16`: rejected by the prompt-rebuild check: the plan the model passed to `get_state_transition` (30 actions) is not the plan in the rebuilt prompt (28 actions, from the ground-truth cache), so the run's prompt held a different plan (see side finding 2)

**System prompt** (rebuilt with `pddl_eval.runner.build_messages`):

```text
You are a PDDL simulation assistant. LLMs cannot reliably trace state transitions through a plan from training alone. Use the available simulation tool to compute the trajectory.
```

**User prompt** (rebuilt the same way; long PDDL abridged, elisions marked):

```text
Show the state at each step of this plan. Step 0 = initial state with empty `action`. Each `state.boolean` entry lists every predicate that holds in that state, parenthesised and lowercase; `state.numeric` is the fluents map (empty for purely-symbolic domains).
Example step: {"step": 0, "action": "", "state": {"boolean": ["(ontable a)", "(clear a)"], "numeric": {}}}
Use the get_state_transition tool with the domain, problem, and plan as arguments.

Domain:
(define (domain depots)
(:requirements :strips :typing)
(:types place locatable - object
  depot distributor - place
        truck hoist surface - locatable
        pallet crate - surface)

(:predicates (at ?x - locatable ?y - place)
             (on ?x - crate ?y - surface)
             (in ?x - crate ?y - truck)
             (lifting ?x - hoist ?y - crate)
             (available ?x - hoist)
             (clear ?x - surface))

[... 24 lines of the domain elided ...]

)

Problem:
(define (problem depotprob134536825) (:domain depots)
(:objects
	depot0 depot1 - Depot
	distributor0 distributor1 - Distributor
	truck0 - Truck
	pallet0 pallet1 pallet2 pallet3 - Pallet
	crate0 crate1 crate2 - Crate
	hoist0 hoist1 hoist2 hoist3 - Hoist)
[... 21 lines of the problem elided ...]
	(on crate1 pallet3)
	(at crate2 depot0)
	(on crate2 crate0)
)

(:goal (and
		(on crate1 pallet1)
		(on crate2 crate1)
	)
))

Plan:
(drive truck0 distributor0 depot0)
(lift hoist0 crate2 crate0 depot0)
(load hoist0 crate2 truck0 depot0)
(drive truck0 depot0 distributor1)
(lift hoist3 crate1 pallet3 distributor1)
(load hoist3 crate1 truck0 distributor1)
(drive truck0 distributor1 depot1)
(unload hoist1 crate1 truck0 depot1)
(drop hoist1 crate1 pallet1 depot1)
(unload hoist1 crate2 truck0 depot1)
(drop hoist1 crate2 crate1 depot1)
```

The model's intermediate assistant text is not stored; the rows keep each tool call's name, arguments and result, and the final answer.

**Tool call 1: `get_state_transition`**, arguments:

- `domain`: the domain text of the prompt, the same once whitespace is collapsed (1,520 characters)
- `problem`: the problem text of the prompt, the same once whitespace is collapsed (812 characters)
- `plan` (a string, 11 actions):

```text
["drive truck0 distributor0 depot0", "lift hoist0 crate2 crate0 depot0", "load hoist0 crate2 truck0 depot0", "drive truck0 depot0 distributor1", "lift hoist3 crate1 pallet3 distributor1", "load hoist3 crate1 truck0 distributor1", "drive tru[... 134 characters of this line elided ...]t1", "drop hoist1 crate2 crate1 depot1"]
```

**Tool result 1** (49,830 characters, 1,384 lines; abridged):

```json
{
  "valid": true,
  "status": "VALID",
  "steps": [
    {
      "index": 1,
      "action": "(drive truck0 distributor0 depot0)",
      "status": "OK",
      "changes": {
        "boolean": {
          "at(truck0, distributor0)": false,
          "at(truck0, depot0)": true
        },
        "numeric": {}
      }
    },
    {
      "index": 2,
      "action": "(lift hoist0 crate2 crate0 depot0)",
      "status": "OK",
      "changes": {
        "boolean": {
          "clear(crate2)": false,
          "available(hoist0)": false,
          "at(crate2, depot0)": false,
          "on(crate2, crate0)": false,
          "lifting(hoist0, crate2)": true,
          "clear(crate0)": true
        },
        "numeric": {}
[... 1346 lines of the tool result elided ...]
        "clear(pallet0)": false,
        "clear(pallet3)": true,
        "clear(crate0)": true
      },
      "numeric_fluents": {}
    }
  ]
}
```

**Final answer:** empty. The last turn was never generated: the server refused it because the prompt (system, user, the tool call and its result) did not fit the 16,384-token window (`ctx_no_room_turns` = 1).

**Reading** (drafted by an AI session, Claude Code, on 2026-11-09 and pending Omer's confirmation). Confirmed (read in full on 2026-11-09). The model passed the prompt's domain, problem and 11-action plan to `get_state_transition`. The tool's trajectory is right (stored success true). The result is 49,830 characters: a list of the changes at each step, then all 12 states (the initial one and one after each action), each listing every ground fact of the problem as true or false. The next turn would have had to hold the prompt and this result, which does not fit in 16,384 tokens, so the server refused it and the final answer is empty. The model never got a turn in which to relay the result.

---

## Example 4. Solve: a transcription error (the answer restates the tool's plan with a change)

| field | value |
|---|---|
| served model | `Qwen/Qwen3.5-9B`: official release from the Qwen organisation's repository, no third-party quantisation; the serving dtype is not recorded in the cell metadata |
| serving | vLLM 0.20.2, temperature 0.0, context window 16,384 tokens, thinking off, all tools visible, system prompt style `minimal` |
| cell file | `results/delivered-rerun/slurm_vllm_Qwen3_5_9B_off_tools_all_minimal_delivered-rerun/trials.jsonl`, line 448 |
| trial key (as stored) | `["Qwen/Qwen3.5-9B", "solve", "drone", "p05", "", 15, true, "off", "all", "minimal"]` |
| task / domain / problem / plan / wording | solve / drone / p05 / - / v15 (steered arm) |
| stored grade (tool-verified) | success=True, failure_reason=`ok` |
| delivered grade (frozen grader) | ok=False, reason=`plan_invalid`, plan extracted by `strict_lines` |
| E4 label (frozen e4.classify) | WRONG_FACTS (plan differs from the tool's plan) |
| tokens | prompt 25,517 (summed over turns), completion 5,140, turns 3, clipped turns 2 (last turn clipped to max_tokens 4,910, its prompt 11,474 tokens), no-room turns 0, done_reason `stop` |

Context clipping: 2 turn(s) of this row ran with the output allowance (max_tokens) cut down so the turn fits the 16,384-token window. The last turn was one of them, with 4,910 tokens allowed, and it ended with done_reason `stop`, so the final answer was not cut short by the clip.

Drawn: position 1 of 5 in the shuffled order (seed 20261109 + 4). Trial id `Qwen3_5_9B|solve|steered|drone|p05||v15`.

The tool's plan and the delivered plan both have 110 actions; they differ at 7 position(s):

| step | tool's plan | delivered answer |
|---|---|---|
| 71 | `(decrease_y)` | `(recharge)` |
| 72 | `(recharge)` | `(visit x0y0z0)` |
| 89 | `(visit x0y0z0)` | `(increase_x)` |
| 90 | `(increase_x)` | `(visit x1y0z0)` |
| 91 | `(visit x1y0z0)` | `(decrease_x)` |
| 92 | `(decrease_x)` | `(recharge)` |
| 93 | `(recharge)` | `(increase_y)` |

Read as runs of one repeated action, the two plans differ only here:

| action | tool's plan: run length (from step) | delivered answer: run length (from step) |
|---|---|---|
| `(decrease_y)` | 8 (step 64) | 7 (step 64) |
| `(increase_y)` | 8 (step 94) | 9 (step 93) |

**System prompt** (rebuilt with `pddl_eval.runner.build_messages`):

```text
You are a PDDL planning assistant. LLMs cannot reliably generate correct plans from training alone (arXiv:2509.12987). Use the available planner tool to produce the plan.
```

**User prompt** (rebuilt the same way; long PDDL abridged, elisions marked):

```text
Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`. Use the planner tool with the domain and problem as arguments.

Domain definition:
(define (domain drone)

    ;remove requirements that are not needed
    ;(:requirements :strips)

    (:types ;todo: enumerate types and their hierarchy here, e.g. car truck bus - vehicle
        location - object
    )

    ; un-comment following line if constants are needed
    ;(:constants )

    (:predicates ;todo: define predicates here
        (visited ?x - location)
[... 104 lines of the domain elided ...]

)

Problem definition:
;;Instance with 2x9x1 points
(define (problem name) (:domain drone)
(:objects
x0y0z0 - location
x0y1z0 - location
x0y2z0 - location
x0y3z0 - location
x0y4z0 - location
[... 86 lines of the problem elided ...]
(visited x1y1z0)
(visited x1y2z0)
(visited x1y3z0)
(visited x1y4z0)
(visited x1y5z0)
(visited x1y6z0)
(visited x1y7z0)
(visited x1y8z0)
(= (x) 0) (= (y) 0) (= (z) 0) ))
);; end of the problem instance
```

The model's intermediate assistant text is not stored; the rows keep each tool call's name, arguments and result, and the final answer.

**Tool call 1: `classic_planner`**, arguments:

- `domain`: the domain text of the prompt, the same once whitespace is collapsed (2,700 characters)
- `problem`: the problem text of the prompt, the same once `;` comment lines are dropped and whitespace is collapsed (1,909 characters)

**Tool result 1** (1,636 characters, 7 lines; abridged):

```json
{
  "error": true,
  "message": "Planner failed with status PlanGenerationResultStatus.INTERNAL_ERROR. log_tail: \"luents\\\\nExpected: :strips, :adl, :typing, :negation, :equality, :negative-preconditions, :disjunctive-preconditions, :existential-preconditio[... 238 characters of this line elided ...]el=<LogLevel.ERROR: 4>, message='')]\"",
  "status": "PlanGenerationResultStatus.INTERNAL_ERROR",
  "solve_time": 0.141,
  "log": "[LogMessage(level=<LogLevel.INFO: 2>, message='INFO     planner time limit: None\\nINFO     planner memory limit: None\\n\\nINFO     Running translator.\\nINFO     translator stdin: None\\nINFO     translator time limit: None\\nIN[... 736 characters of this line elided ...]level=<LogLevel.ERROR: 4>, message='')]"
}
```

**Tool call 2: `numeric_planner`**, arguments:

- `domain`: the domain text of the prompt, the same once whitespace is collapsed (2,700 characters)
- `problem`: the problem text of the prompt, the same once `;` comment lines are dropped and whitespace is collapsed (1,909 characters)

**Tool result 2** (2,305 characters, 115 lines; abridged):

```json
{
  "plan": [
    "(increase_y)",
    "(increase_y)",
[... 59 lines of the tool result elided ...]
    "(visit x1y8z0)",
    "(decrease_x)",
    "(decrease_y)",
    "(decrease_y)",
    "(decrease_y)",
    "(decrease_y)",
    "(decrease_y)",
    "(decrease_y)",
    "(decrease_y)",
    "(decrease_y)",
    "(recharge)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(visit x0y0z0)",
    "(increase_x)",
    "(visit x1y0z0)",
    "(decrease_x)",
    "(recharge)",
    "(increase_y)",
    "(increase_y)",
    "(increase_y)",
    "(increase_y)",
    "(increase_y)",
    "(increase_y)",
    "(increase_y)",
    "(increase_y)",
    "(visit x0y8z0)",
    "(decrease_y)",
[... 6 lines of the tool result elided ...]
    "(decrease_y)"
  ],
  "solve_time": 0.434
}
```

**Final answer** (verbatim, 1,601 characters, abridged):

````text
The planner found a valid plan. Let me output each action on its own line in the requested format:

```
(increase_y)
[... 60 lines of the answer elided ...]
(visit x1y8z0)
(decrease_x)
(decrease_y)
(decrease_y)
(decrease_y)
(decrease_y)
(decrease_y)
(decrease_y)
(decrease_y)
(recharge)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(visit x0y0z0)
(increase_x)
(visit x1y0z0)
(decrease_x)
(recharge)
(increase_y)
(increase_y)
(increase_y)
(increase_y)
(increase_y)
(increase_y)
(increase_y)
(increase_y)
(increase_y)
(visit x0y8z0)
(decrease_y)
[... 5 lines of the answer elided ...]
(decrease_y)
(decrease_y)
```
````

**Reading** (drafted by an AI session, Claude Code, on 2026-11-09 and pending Omer's confirmation). Confirmed (read in full on 2026-11-09). The classic planner failed on this numeric domain and the model then called the numeric planner, which returned a 110-action plan (stored grade: valid). The answer restates it as 110 lines but miscounts two runs of a repeated action: 7 `(decrease_y)` where the tool has 8, and 9 `(increase_y)` where the tool has 8. The length is unchanged and every other action matches; the validator rejects the restated plan. A transcription error in the plain sense: the model had the right plan and copied it wrong.

---

## Notes for E3

- **Captions must name the served build.** Gemma and Qwen3.6 were served as community AWQ 4-bit quantisations (`cyankiwi/...`), not the official weights; Qwen3.5-9B is the official release. Each excerpt's table says which.
- **Example 4 pairs with the frontier passage** on transcription errors (`paper/main.tex`, subsection "The Delivery Gap"). Side finding 1 matters there: in this rerun, 17 of the 38 solve rows the frozen E4 labels WRONG_FACTS are goal facts read as plan steps. Of the other 21, 5 keep the tool plan's length with some actions changed (example 4's pool); 5 have extra lines before the tool plan; 1 has the tool plan followed by extra lines that are not all goal facts; 10 have some other shape, not classified further. Only the same-length shape (example 4's pool) is a transcription error by construction. Before the paper counts frontier failures as transcription errors, check that none of them is this extractor case: a quick look outside this script found one Haiku with-tools solve answer (depot p02) that repeats the tool's plan and then lists two goal facts. Whether the frontier grading counted that row among Haiku's "three transcription errors" was not checked.
- **Example 3's first draw was skipped** because its prompt cannot be rebuilt from the cache (side finding 2). The shown row's plan passed the check.
- The intermediate assistant turns (the text that carried each tool call) are not stored, so an excerpt shows the tool calls by name and arguments only.
