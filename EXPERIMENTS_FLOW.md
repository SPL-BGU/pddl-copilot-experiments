# Experiments Flow

Reference for the test setup of the PDDL Copilot evaluation: the tasks, the
conditions, the prompts, the tool contract, how a trial is graded and what a
run writes to disk. It extends the evaluation of Benyamin et al., 2025
(arXiv:2509.12987).

**Which data the paper uses, and what is left to do:** `development/STATUS.md`.
This file does not restate it. Frozen figures: `development/NUMBERS.md`.
Registered designs and their analyses: `development/reference/`.

> **Single-task only.** The multi-task chain phase was archived 2026-05-05 and
> its code deleted 2026-05-25. See `development/CHANGELOG.md`.

---

## 1. High-Level Pipeline

The harness is `run_experiment.py`. One invocation runs one model, one think
mode and one condition (with-tools or no-tools). Runs are made on the BGU
cluster through `cluster-experimenting/submit_with_rtx.sh`
(`cluster-experimenting/README.md`). Each SLURM array task starts its own vLLM
server and runs one cell against it. The single inference client is
`pddl_eval.vllm_client.VLLMClient` (the Ollama backend was retired 2026-05-18
and its code removed 2026-05-23).

```
run_experiment.py
  |
  1. Load PDDL domains from domains/{classical,numeric}/
  2. Connect to MCP servers (pddl-solver, pddl-validator: the two required plugins)
  3. Generate ground truth (oracle solves every problem)
  4. Single-task evaluation (with-tools or without-tools)
  5. Save results to output directory
```

Each `(model, think, condition, tool_filter, prompt_style)` has its own output
directory:
```
results/slurm_vllm_<model>_<think>_<cond>[_<run-tag>]/           # cluster
results/{full,partial}/<git-sha>_<timestamp>/                    # bare CLI (--output-dir auto)
results/smoke/{fixed,shuffle}_<git-sha>_<timestamp>/             # --smoke
    trials.jsonl
    single_task_{ts}.json
    summary_{ts}.json
```

---

## 2. Experimental Dimensions

| Dimension | Values | Notes |
|-----------|--------|-------|
| **Model** | Any tag in `vllm_lookup` (`cluster-experimenting/lib/defaults.sh`). The May sweep ran `Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`. The October rerun, the control and the matched run use the last three of these. | Served by vLLM on one `rtx_6000` GPU per cell |
| **Condition** | with-tools, without-tools | Whether MCP tools are offered |
| **Tool filter** | all | Every tool is offered every turn (single value) |
| **Prompt style** | `minimal`, `neutral` | With-tools system prompt (§2.3) |
| **Prompt variant** | v11 to v13 (plain), v14 to v16 (steered) | User-prompt wording (§3) |
| **Think mode** | on, off, default | `on`/`off` set vLLM `chat_template_kwargs.enable_thinking`. `default` omits the setting. The May sweep ran on and off; every later open-model run is thinking off |

### 2.1 Condition: with-tools vs without-tools

- **with-tools**: the MCP tool descriptions are passed in the OpenAI `tools` parameter of the chat-completions request. The model can call tools in a loop (up to 10 iterations). The per-task system prompt tells it to use the available tool (§2.3).
- **without-tools**: no tools are offered. The model answers from its own knowledge. The per-task system prompt says PDDL tools are not available and asks for an answer format (§4.2).

### 2.2 Tool Filter

`all` is the only value: every tool of both MCP servers is offered on every turn.

### 2.3 Prompts and where they live

All prompt text is in `pddl_eval/prompts.py`; the design is in
`development/reference/sweep_prompt_bank_design.md`.

- **User prompts.** Three plain wordings per task (v11, v12, v13) and three steered ones (v14, v15, v16). A steered wording is the plain text with one sentence added that tells the model to use the tool. No-tools cells run v11 to v13 only, unless `--include-no-tools-steered` is given.
- **With-tools system prompt, `minimal` style.** A three-sentence per-task text from `WITH_TOOLS_SYSTEM_BY_TASK`. For `solve`:
  > *"You are a PDDL planning assistant. LLMs cannot reliably generate correct plans from training alone (arXiv:2509.12987). Use the available planner tool to produce the plan."*

  Tool signatures and argument descriptions are not in the system prompt. They travel in the `tools` parameter.
- **With-tools system prompt, `neutral` style** (`--prompt-style neutral`). Only the role sentence, with no instruction to use the tool. The cell is then named `tools_all_neutral`.
- **No-tools system prompt.** A three-sentence per-task text from `WITHOUT_TOOLS_SYSTEM_BY_TASK`. On the three validation tasks it asks for a last line `VERDICT: VALID` or `VERDICT: INVALID`. **On solve and simulate it tells the model to "conform to the JSON schema provided by the format constraint", and no schema ever reaches the model** (§4.2). This is the registered message of the May sweep and of the October rerun.
- **Corrected no-tools system prompts** (`pddl_eval/control_prompts.py`), for solve and simulate only. `no-pointer` removes the schema sentence. `format-stated` states the answer format in plain words and asks for the final answer in a fenced code block. The client swaps the message when `$PDDL_NO_TOOLS_SYSTEM` names one of the two (`submit_with_rtx.sh --no-tools-system`). Every cell of such a job logs the system text it sent to `system_prompt_audit.jsonl`.
- **Legacy variants (v0 to v10).** The flat `WITH_TOOLS_SYSTEM` / `WITHOUT_TOOLS_SYSTEM` constants and the old user prompts are kept unchanged in `prompts.py` so an old run can be replayed. `runner.py:evaluate_one` routes `prompt_variant < 11` to them.

---

## 3. Tasks

Five tasks, each testing a different stage of the PDDL planning pipeline:

| Task | What the model must do | Ground truth source |
|------|----------------------|---------------------|
| **solve** | Find a valid plan for a domain + problem | `classic_planner` / `numeric_planner` oracle |
| **validate_domain** | Judge whether a domain has valid PDDL syntax | `validate_domain` oracle (since marketplace 1.4.0; previously the polymorphic `validate_pddl_syntax`) |
| **validate_problem** | Judge whether a problem has valid syntax given its domain | `validate_problem` oracle |
| **validate_plan** | Verify a given plan is correct | `validate_plan` oracle |
| **simulate** | Produce a state-transition trajectory for a plan | `get_state_transition` oracle. Both conditions are graded by comparing the produced trajectory, in a canonical form, with the oracle's. |

Each task has three plain wordings (`v11/v12/v13`: imperative, declarative, interrogative) and three steered ones (`v14/v15/v16`: the plain text plus one sentence that tells the model to use the tool). The full prompt bank is in `development/reference/sweep_prompt_bank_design.md`.

---

## 4. Success Criteria

### 4.1 With-Tools: Two Metrics

The with-tools condition reports two separate metrics:

1. **tool_selected** -- Did the model call the *correct* MCP tool?
   - `solve`: called `classic_planner` or `numeric_planner`
   - `validate_domain` / `validate_problem` / `validate_plan`: called the matching task-aligned tool of the same name (marketplace 1.4.0 split the legacy polymorphic `validate_pddl_syntax` into three; task name == tool name)
   - `simulate`: called `get_state_transition`

2. **success** (end-to-end) -- Was the tool result correct?
   - `solve`: tool returned a plan that passes `validate_plan` (`valid == true`)
   - `validate_*`: tool result verdict matches ground truth (VALID/INVALID). The "wrong argument-shape" failure mode that existed under the polymorphic predecessor is now structurally unreachable — each tool's JSON schema enforces its required arguments. The residual error modes are three-way split: `FR_TOOL_NOT_SELECTED` (no validator-family call at all), `FR_WRONG_TOOL` (model called a validator-family tool but not the task-matching one — e.g. `validate_problem` on a `validate_plan` task), and `FR_VERDICT_MISMATCH` (right tool, wrong verdict). This decomposition is sharper than the pre-1.4.0 grader could achieve, which collapsed wrong-shape calls into `FR_VERDICT_MISMATCH`.
   - `simulate`: tool's `trajectory` equals the oracle's `gt["trace"].trajectory`. The plugin's `valid` field is a PDDL-syntactic signal, not a simulation-correctness signal — a partial trajectory with `valid=false` would pass a naive non-error check. Oracle and model calls go through the same bridged `get_state_transition(verbose=False)` with identical `(domain, problem, plan)` inputs, so a matching trajectory is deterministic. Mismatch → `FR_RESULT_MISMATCH`.

A model can call the right tool and still fail, for example with arguments the tool rejects. The two metrics keep these cases apart.

Both metrics are scored live from the tool result (the *tool-verified* layer). Whether the final answer the model hands back is correct is a separate, offline grade (the *delivered* layer, §14).

### 4.2 Without tools

The JSON value of this condition is `condition: "no-tools"` and the internal
field is `with_tools: false`. All five tasks are run.

**The JSON-schema constraint never took effect.** The harness sends a per-task
JSON schema (`pddl_eval/schemas.py`) with every no-tools request, in the
request field `guided_json`. vLLM 0.20.2 ignores that field, and the constraint
took effect in no corpus (`development/STATUS.md`, "Rules that bind every
step"). So no unaided answer was sampled under a schema: the model saw only
the prompt. A constraint that does take effect
exists as a separate condition (`submit_with_rtx.sh --json-constraint
structured_outputs`, cell name `no-tools-jsonbound`). It was used only for the
JSON constraint pilot and is never pooled with, or set in place of, a no-tools
cell.

Per-task grading at run time (`pddl_eval/scoring.py`):

- `solve`: the answer is first read as JSON `{"plan": [...]}`. If that fails,
  the free-text plan extractor (`extract_plan_lines`) is used. The plan goes
  through the validator; `valid == true` is success.
- `validate_*`: the answer is first read as JSON
  `{"verdict": "VALID" | "INVALID", "reason": ...}`. If that fails, the last
  `VERDICT: VALID|INVALID` line is used. The verdict is compared with ground
  truth. Positives and negatives are balanced 1:1 on `validate_problem` and
  `validate_plan` (§6), so always answering VALID scores about 50%.
- `simulate`: the whole answer must parse as JSON: the wrapper
  `{"trajectory": [...]}`, a bare list of steps, or a single step object
  (`_coerce_simulate_trajectory`), each step with
  `{step, action, state: {boolean: [...], numeric: {...}}}`. Whether the answer
  used the exact wrapper is recorded separately as `format_compliant`. The model's
  trajectory and the oracle's are both passed through `_normalize_trajectory`,
  which brings the two shapes to one canonical form (sorted, lower-cased,
  whitespace-normalised). Equal lists give `FR_OK`; JSON that does not parse
  gives `FR_FORMAT_PARSE_FAIL`; a different trajectory gives
  `FR_RESULT_MISMATCH`. There is no free-text fallback for simulate.

`FR_FORMAT_PARSE_FAIL` fires only when neither the JSON path nor the fallback
(where there is one) yields an answer. An answer cut off by the output cap is
tagged `FR_TRUNCATED_NO_ANSWER` instead.

The run-time grade is what `summary_*.json` holds. The paper's unaided figures
for the October rerun, the control and the matched run come from the offline
graders named in their registrations (§14), which read the stored full answer.

---

## 5. Evaluation Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Temperature | 0.0 | |
| Max tool loops | 10 | Per trial |
| Prompt variants | 6 | Per task: v11 to v13 plain, v14 to v16 steered (§3). `--num-variants` default 6 |
| Random seed | 42 | For `--smoke-shuffle` cell assignment |
| Context window | 16384 tokens | `--num-ctx`; `--num-ctx-thinking` (no-tools cells with thinking on) is held equal to it |
| Output cap | solve 8192, validate_* 6144, simulate 6144 tokens | `DEFAULT_NUM_PREDICT` in `pddl_eval/runner.py`; `--num-predict N` overrides all tasks |
| Concurrency | 4 requests | `--concurrency` |

The context window was 8192 until 2026-04-29 and the non-solve output caps were
lower before that date; `development/CHANGELOG.md` has the history. A larger
window (`submit_with_rtx.sh --max-model-len`) is a separate condition with its
own run tag.

`--decoupled-budget` (no-tools, `--think on` only) splits a trial into a
reasoning call and an answer call with separate token budgets. It writes a
separate corpus; never pool it with a shared-budget run.

---

## 6. Domains

20 domains × 5 valid problems × (1 valid + 1 invalid) domain × (5 valid + 5 invalid) plans per problem = **1240 fixture files** . Per-domain layout:

```
domains/<type>/<domain>/
  domain.pddl                       (1 valid)
  domain_neg.pddl                   (1 invalid)
  p01.pddl ... p05.pddl             (5 valid)
  n01.pddl ... n05.pddl             (5 invalid)
  p01_v1.plan ... p05_v5.plan       (25 valid plans = 5 per problem)
  p01_b1.plan ... p05_b5.plan       (25 invalid plans = 5 per problem)
```

Domain set:

| Type | Domain | Provenance | Goal kind |
|---|---|---|---|
| classical | barman | paper | boolean |
| classical | blocksworld | paper | boolean |
| classical | depots | paper | boolean |
| classical | gripper | PR-3 (olam-compatible) | boolean |
| classical | miconic | PR-3 (olam-compatible) | boolean |
| classical | parking | PR-3 (olam-compatible) | boolean |
| classical | rovers | paper | boolean |
| classical | satellite | paper | boolean |
| classical | tpp | PR-3 (olam-compatible) | boolean |
| classical | zenotravel | PR-3 (olam-compatible; substitute for spec's "logistics") | boolean |
| numeric | block-grouping | PR-3 (matteocarde/patty `files/`; substitute for spec's "settlers") | numeric |
| numeric | counters | paper | numeric `<=` |
| numeric | delivery | PR-3 (matteocarde/patty IPC-2023; substitute for spec's "transport-numeric") | numeric |
| numeric | depot | paper (singular — distinct from classical `depots`) | boolean |
| numeric | drone | PR-3 (matteocarde/patty IPC-2023) | numeric |
| numeric | farmland | paper | numeric `>=` + weighted sum |
| numeric | gardening | PR-3 (matteocarde/patty `files/`; substitute for spec's "plant-watering") | numeric |
| numeric | pogo_stick | paper | boolean |
| numeric | sailing | paper | boolean |
| numeric | zenotravel-numeric | PR-3 (matteocarde/patty IPC-2023; p02-p05 hand-authored) | numeric |

The 10 "paper" domains come from the dataset of the earlier version (Benyamin et al., 2025). The 10 "PR-3" domains were taken from public benchmark suites and checked end to end by the build pipeline. Provenance per domain is in `domains/README.md`.

**Negative fixtures.** Each domain ships:
- `domain_neg.pddl` — joins `validate_domain` (negative arm) only
- `n01..n05.pddl` — join `validate_problem` (negative arm) only
- `p<NN>_b1..b5.plan` — join `validate_plan` (negative arm) for problem `pNN` only

Bug taxonomies (3 domain-mutators, 6 problem-mutators, 4 plan-mutators) are documented in `domains/README.md`. All negatives must validate as `valid=False` against the matching validator tool (`validate_domain` / `validate_problem` / `validate_plan`, per marketplace 1.4.0) — `generate_ground_truth` aborts startup with `SystemExit` naming any drift.

**Expected validity:** positives are expected to pass `domain_valid == problem_valid == plan_valid == solvable == True`. Each committed `p<NN>_v[1-5].plan` is independently re-validated at startup; any committed valid plan that the validator rejects also aborts startup (symmetric fail-fast on both sides).

**Plan diversity.** Classical domains achieve up to 3 distinct plans via Fast Downward search-strategy variants (`lazy_greedy_cea`, `astar_lmcut`, `lazy_greedy_ff`); numeric domains use ENHSP whose alternative search algorithms are limited, so v2..v5 may be duplicates of v1. The graded count remains 5 per problem; per-call grading robustness is preserved because each prompt variant grades the plan independently.

**Pairing convention (known limitation).** `validate_problem` and `validate_plan` negative jobs always pair the negative file with the *positive* counterparts of the other layers (the `validate_problem` negative uses positive `domain.pddl`; the `validate_plan` negative uses positive `domain.pddl` + the matching positive `pNN.pddl` for that `pNN_bK.plan`). The LLM never sees a filename — prompts interpolate content via `.format(domain=…, problem=…, plan=…)` — so this isn't a leak channel. See `development/OPEN_ISSUES.md` ISS-020 for the related 5:1 negative-vs-positive sample-size imbalance on `validate_domain`.

---

## 7. Ground Truth Generation

Before any model evaluation, the experiment generates oracle answers by calling the MCP tools directly:

1. **validate_domain**(domain) -- domain validity verdict
2. **validate_problem**(domain, problem) -- problem validity verdict
3. **classic_planner** or **numeric_planner**(domain, problem) -- oracle plan
4. **validate_plan**(domain, problem, plan) -- plan validity verdict
5. **get_state_transition**(domain, problem, plan) -- oracle state trace

These oracle results become the ground truth for scoring model responses.

---

## 8. MCP Tool API Contract

**Marketplace compatibility:** the harness requires marketplace 1.4.0+ (per-task
`validate_domain` / `validate_problem` / `validate_plan` tools). Runs before
2026-05-23 used the single predecessor tool `validate_pddl_syntax`; see CHANGELOG
2026-05-23.

Two version schemes appear in this repo's docs. "Marketplace 1.4.0" is the `metadata.version` field of `.claude-plugin/marketplace.json` in pddl-copilot (1.4.0 = commit `2850bc4`, 2026-05-23, the validator split). "v2.0.0" is a git tag of the same repo (2026-04-10, the move from Docker to pure pip); at that tag the marketplace field read 1.2.0. Each plugin also carries its own version. When a doc says "marketplace X", it means the first scheme.

Tools are served by two MCP plugin servers from the [pddl-copilot](https://github.com/SPL-BGU/pddl-copilot) marketplace (pure pip since git tag `v2.0.0` — no Docker). The solver uses Fast Downward via `up-fast-downward` and ENHSP via `up-enhsp`; the validator uses `pddl-pyvalidator`. Numeric planning via ENHSP requires Java 17+.

### pddl-solver

| Tool | Parameters | Returns |
|------|-----------|---------|
| `classic_planner` | `domain` (PDDL content or file path), `problem` (same), `strategy` (optional: lazy_greedy_cea, astar_lmcut, lazy_greedy_ff) | `{plan: [...], solve_time: float}` or `{error: true, message: str}` |
| `numeric_planner` | `domain`, `problem` | Same format |

### pddl-validator

| Tool | Parameters | Returns |
|------|-----------|---------|
| `validate_domain` | `domain` (required), `verbose` (optional, default `True`) | `verbose=True`: `{valid, status, report, details}`. `verbose=False`: `{valid, status, report}` (drops `details` only). Error: `{error: true, message: str}` |
| `validate_problem` | `domain`, `problem` (both required), `verbose` (optional, default `True`) | Same response shape as `validate_domain`. |
| `validate_plan` | `domain`, `problem`, `plan` (all required), `verbose` (optional, default `True`) | Same response shape — `valid` reflects PLAN CORRECTNESS (preconditions hold + goal satisfied), not just syntax. |
| `get_state_transition` | `domain`, `problem`, `plan` (all required), `verbose` (optional, default `True`) | `verbose=True`: `{valid, report, steps, trajectory, details}`. `verbose=False`: `{valid, steps, trajectory}` (drops BOTH `report` and `details` — asymmetric with `validate_*`). Error: `{error: true, message: str}` |

**Input detection**: Tools check if an argument starts with `(` or `;` or contains `(define ` to detect inline PDDL content. Otherwise the argument is treated as a file path. This is why passing a domain name like `"blocksworld"` fails -- it's interpreted as a file path that doesn't exist.

**Response-size policy (structured projection, no truncation).** Each validator tool accepts an optional `verbose` parameter that defaults to `True` so standalone MCP callers (Claude Desktop, future consumers) still receive the full pyvalidator fidelity by default. Setting `verbose=False` drops the redundant fields that re-serialize information already present elsewhere in the response: `details` on the three `validate_*` tools; `report` and `details` on `get_state_transition`. Kept fields — `status`, `report` (validate), `steps`, `trajectory` with full `boolean_fluents`/`numeric_fluents` per step — are returned in full; there is no item or character cap.

**Experiment bridge enforces `verbose=False`.** `MCPPlanner` (`pddl_eval/chat.py`) strips the `verbose` property from each validator tool's `inputSchema` before passing tools to the LLM, and injects `verbose=False` on every call (see `_PINNED_VERBOSE_FALSE = {"validate_domain", "validate_problem", "validate_plan", "get_state_transition"}` in `pddl_eval/chat.py:86`). The experiment agent cannot see or control the flag. This keeps tool responses compact for the LLM without changing the plugin's default contract for other callers. Prior `tool_calls[*].result` strings recorded in `results/` are not byte-comparable with post-change runs, but scoring (`_parse_validation_verdict`, simulate non-empty check) is unchanged.

**Aligned cap hygiene in the MCP repo.** The existing caps in `../pddl-copilot` now follow a consistent `DEFAULT_*` module-constant + `PDDL_*` env override convention (defaults unchanged):

| Cap | Env var | Default |
|---|---|---|
| Grounding attempts in `get_applicable_actions` | `PDDL_MAX_GROUNDING_ATTEMPTS` | 10000 |
| Applicable-actions return list | `PDDL_MAX_APPLICABLE_ACTIONS` | 50 |
| Planner failure-log tail length | `PDDL_MAX_LOG_CHARS` | 3000 |
| Planner wall-clock timeout (s) | `PDDL_TIMEOUT` | 120 |

---

## 9. Output Files

Each run writes three files into its output directory: `trials.jsonl` while it runs,
then `single_task_*.json` and `summary_*.json` at the end.

### trials.jsonl

The append-only progress log, and the file the analysis layer reads. One line per
completed trial, written as soon as the trial finishes, so a timeout or cancel loses
nothing:

```
{"key": [model, task, domain, problem, plan_label, prompt_variant, with_tools, think, tool_filter, prompt_style], "result": {...}}
```

- `key` is the 10-field resume key (`runner.py:_trial_key`). On restart, trials whose key
  is already present are skipped. `--no-resume` deletes the file first.
- `result` has the same fields as a `single_task_*.json` entry (table below).
- Trials that failed for infrastructure reasons (e.g. the vLLM server died) are not
  written, so the next run retries them.
- A half-written last line is dropped on load. Duplicate keys keep the first record.
- Keep one corpus per file. Rows from different backends or configs in one `trials.jsonl`
  break corpus identity.

### summary_{ts}.json

Aggregated statistics. Top-level object with a `single_task` array plus an
optional `meta` dict.

`single_task` entries:
| Field | Description |
|-------|-------------|
| model, condition, task | Grouping key |
| successes, n, success_rate | End-to-end success as scored live (the tool-verified layer, §14) |
| ci_lo, ci_hi | 95% Wilson score CI |
| tool_selected, tool_selected_rate, tool_selected_ci_lo, tool_selected_ci_hi | Tool selection (with-tools only) |
| truncated | Count of evaluations where `done_reason == "length"` (token-cap hit) |
| failure_reasons | Dict of `FR_*` reason → count (open-ended; new buckets are additive). Paper-cited tags: `FR_OK`, `FR_THINK_OVERFLOW`, `FR_FORMAT_PARSE_FAIL`, `FR_WRONG_TOOL`. See `development/OPEN_ISSUES.md` ISS-005 for the full vocabulary and sub-pattern audit. |
| simulate_q1 | No-tools `simulate` rows only. The two-metric grader: `state_tracking_rate` (same as `success_rate`), `format_compliant` / `_rate` / CIs (did the model emit the exact `{"trajectory": [...]}` wrapper), and `strict` / `_rate` / CIs (both at once), all over the same `n`. |
| tokens | Token aggregates for the group: prompt / completion / total sums and means, completion median, mean and max turns, eval duration, completion tokens per second |
| per_variant | The same success, CI, `tool_selected` and `tokens` numbers broken down by prompt variant (keys are variant indices as strings) |

Known defect: some no-tools summaries carry extra `condition: "tools"` rows with `n = 0`.
Filter `single_task` rows on `condition` before using them.

`meta` (present when `save_results` is called with metadata; written by `async_main`):
| Field | Description |
|-------|-------------|
| host | The `--llm-base-url` the run used (`localhost` when unset). The legacy `is_remote` field was retired 2026-04-27. |
| conditions | `tools`, `no-tools`, or `both` |
| models, tasks | CLI inputs that selected which models/tasks ran |
| num_variants, prompt_variants_active, num_ctx, num_ctx_thinking, num_predict, temperature, think | Reproducibility knobs. `prompt_variants_active` records the actual variant indices used (e.g. `[11, 12, 13, 14, 15, 16]`) — `num_variants` alone doesn't say which paraphrases ran. `num_ctx_thinking` (PR-2, 2026-04-28) is the context budget used for `(think!=off, no-tools)` cells only; `async_main` splits `--conditions=both` into per-condition sub-passes when this applies, so `num_ctx` is constant within each `run_single_task_experiment` call. `num_predict=null` means per-task defaults (`solve=8192, validate_*=6144, simulate=6144`); a number means a uniform CLI override. |
| include_no_tools_steered | Whether the no-tools steered control arm (v14–v16) was emitted |
| decoupled_budget, num_predict_think, num_predict_answer | Present only on `--decoupled-budget` runs. `num_predict_answer` is a number, or `{"per_task": ...}` when it fell back to the per-task caps |
| tool_filter, prompt_style | Recorded only when `conditions ∈ {tools, both}` (with-tools knobs) |
| partial | Present only when `--partial K > 0` |
| resumed_count | Present only when the run restored trials from `trials.jsonl`: how many in-scope restored trials were folded into this output |

### single_task_{ts}.json

Raw per-evaluation results. Each entry is one (model, task, domain, problem, plan_label, prompt_variant, condition) evaluation.

| Field | Description |
|-------|-------------|
| model, task, domain_name, problem_name, prompt_variant | Evaluation identity |
| plan_label | `validate_plan` only: `v1`..`v5` for the valid plans, `b1`..`b5` for the invalid ones. Empty string for every other task |
| with_tools | Condition |
| success | End-to-end correctness as scored live. For no-tools `simulate` this is state-tracking |
| tool_selected | Correct tool called (with-tools only, null otherwise) |
| format_compliant | No-tools `simulate` only: the model emitted the schema-exact `{"trajectory": [...]}` wrapper. Null elsewhere |
| response | Model text response, truncated to `RESPONSE_SNAPSHOT_LEN = 65536` chars (the head is kept). **Corpora written before 2026-06-25 stored only 500 chars, and corpora from 2026-06-25 to 2026-10-02 stored 16384.** Those older caps cut long answers before their end (the verdict or final plan), which is what makes some delivered-answer cells censored (§14) |
| response_truncated_by_storage | `true` when the answer was longer than the cap and `response` holds only its head, `false` when `response` is the complete answer. Null on rows written before 2026-10-02 |
| thinking | Last-turn structured `message.thinking` content (PR-2, truncated to `THINKING_SNAPSHOT_LEN=4096` chars). Empty string when the model didn't emit thinking. For multi-turn `with_tools` runs, only the last turn's thinking is recorded — earlier-turn reasoning is observable via `tool_calls[]`. |
| tool_calls | List of `{name, arguments, result}` dicts |
| tokens | Dict `{prompt, completion, turns, total_duration_ns, eval_duration_ns}` (PR-2). Counts are summed across `client.chat()` turns; `turns=1` for `with_tools=False`, up to `MAX_TOOL_LOOPS=10` otherwise. Durations are measured client-side with `perf_counter_ns` around the vLLM call; `eval_duration_ns ≤ total_duration_ns`. Used for tokens-per-second and prompt-shrinkage analysis. Since 2026-10-02 four more keys appear **only** when a turn overflowed the context window: `ctx_clipped_turns` (turns that ran with a reduced output allowance), `ctx_clip_last_turn_max_tokens` (the allowance the final turn actually got, present only if that turn was clipped), `ctx_clip_last_turn_prompt_tokens` (that turn's measured prompt size; prompt plus allowance never exceeds the context window) and `ctx_no_room_turns` (turns never generated because the prompt alone filled the window; the row then has an empty answer with `done_reason = "length"`). |
| duration_s | Wall-clock time around the chat helper (Python + MCP latency included; not the same as `tokens.total_duration_ns`) |
| error | Error message if any |
| failure_reason | `FR_*` constant from `pddl_eval/scoring.py` ("ok" iff `success=True`); see `failure_reasons` description above for the open-ended vocabulary |
| truncated | `done_reason == "length"` on any turn (output-token cap hit). On a decoupled-budget trial this is the answer phase |
| think_truncated | Decoupled-budget trials only: the reasoning phase hit its own budget. Null on every other trial, so "not null" marks a decoupled row |
| done_reason | Raw `done_reason` from the last chat turn (`"stop"`, `"length"`, etc.) |
| infra_failure | True when the trial never got a real model attempt (transport or server failure). Such records are dropped from `trials.jsonl` and from the saved list, so this is `false` on disk |
| tool_filter | "all" |
| prompt_style | "minimal" (every corpus before 2026-10-02), or "neutral" for a `--prompt-style neutral` run: the with-tools system prompt is only the role-framing sentence, with no "use the tool" instruction. This is the system-prompt style and is separate from the neutral (v11–13) versus steered (v14–16) prompt variants |

---

## 10. Running Experiments

Run from `~/pddl-copilot-experiments` on the cluster login node.

```bash
# One model, or a preview without submitting
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --think-modes off
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --think-modes off --dry-run
```

`submit_with_rtx.sh` builds one cell per (model, think mode, condition) and
submits them as one SLURM job array of
`cluster-experimenting/run_condition_vllm_rtx.sbatch`. Each array task starts
its own vLLM server on one GPU, runs `run_experiment.py` for that cell, and
writes to `results/slurm_vllm_<model>_<think>_<cond>[_<run-tag>]/`. A
resubmitted cell resumes from its `trials.jsonl`. Only tags listed in
`vllm_lookup` (`cluster-experimenting/lib/defaults.sh`) are accepted.

How each run of the paper was submitted (run tags, tasks, system messages) is
in `cluster-experimenting/README.md` and in the run's registration.
`submit_full_sweep.sh` is how the May sweep was submitted. Status, sync and
postmortem helpers: `.claude/skills/cluster-ops/SKILL.md`.

### Direct CLI

Needs a reachable vLLM server (CUDA). Laptop runs are not supported.

```bash
python3 run_experiment.py \
    --marketplace-path ../pddl-copilot \
    --llm-base-url http://localhost:8000 \
    --models Qwen3.5:0.8B \
    --output-dir results/my_run/
```

---

## 11. Differences from the 2025 version (mechanics)

| Aspect | Benyamin et al., 2025 | This harness |
|--------|-----------------------|--------------|
| Success with tools | Tool selection only | Tool selection, and whether the tool result is correct (§4.1); the delivered answer is graded offline (§14) |
| Tool filter | All tools offered | All tools offered |
| Models | Qwen3, GPT-OSS (various sizes) | Qwen3.5, Qwen3.6 and Gemma 4 models served by vLLM (§2) |
| Domains | 10 IPC benchmarks | 20 domains: those 10 plus 10 added later (§6) |
| MCP integration | Claude Desktop plugins | Direct MCP stdio connections |
| Validator tool output | Full pyvalidator shape | The plugin default is unchanged. The experiment bridge pins `verbose=False`, so the model sees `{valid, status, report}` from the three `validate_*` tools and `{valid, steps, trajectory}` from `get_state_transition` (§8) |
| Simulate success | Non-error tool result | The trajectory must equal the oracle's after normalization, in both conditions |
| No-tools grading | Free-text extractors | JSON read first, free-text fallback for `solve` and `validate_*`, JSON only for `simulate` (§4.2). The JSON-schema constraint never took effect |
| Scope | Single tasks and chains | Single tasks only |

---

## 12. Notes on the prompt and tool design

- **Verdict line.** The no-tools `validate_*` prompts ask for a last line `VERDICT: VALID|INVALID`. The grader falls back to it when the answer is not JSON.
- **Paraphrases.** The three wordings of a task differ only in the task sentence. The steering sentence is the same in v14, v15 and v16 of a task.
- **Per-task validator tools.** Marketplace 1.4.0 (pddl-copilot `2850bc4`) split the old `validate_pddl_syntax` into `validate_domain`, `validate_problem` and `validate_plan`, each with required arguments in its schema. `tool_selected` therefore needs the tool whose name matches the task; a call to another validator tool is `FR_WRONG_TOOL`. Runs made before that split used the old tool and cannot be rerun against the current plugins.
- **No-tools steered cells.** `--include-no-tools-steered` also runs v14 to v16 without tools. This is the steering control (`development/reference/ntster_h4_prereg.md`).

---

## 13. PlanBench Arm (added 2026-05-18)

A second, parallel evaluation arm that runs the PlanBench benchmark, alongside (not replacing) the 5-task `run_experiment.py` matrix above. It has two parts:

- **Vanilla arm (v1).** No MCP tools during response generation. §13.1–13.7 below are its methodology reference; `planbench/README.md` has operator-level usage.
- **With-tools arm.** It ran and is **closed** (ISS-022, PR #93, 2026-08). It is not future work. Design of record: `development/reference/planbench_wt_prereg.md`. Every number, audit and deviation: `development/reference/planbench_wt_results_20260803.md`; quote them through `development/NUMBERS.md`. Analysis scripts: `planbench/analysis/`. Committed data: `results/planbench/wt-anthropic-20260801/`. It includes the Mystery (obfuscated) Blocksworld configuration.

> **Backend note (2026-06-02).** The arm originally self-deployed Ollama (it landed the same day Ollama was retired harness-wide). The run-path was migrated to self-deployed vLLM — the same GPU class + serve config as the 5-task arm, for corpus identity. See CHANGELOG 2026-06-02. The `engine.py` Ollama branch is retained for archaeology only.

### 13.1 What it measures

The 5-task matrix grades our own domain corpus against ground truth from the
MCP tools. PlanBench grades plan generation from natural-language prompts on
its own domains, with its own VAL-based scorer. Its published baseline results
are read from the files it ships.

PlanBench's `INTEGRATION.md` treats `send_query` as a single turn. An agent
that calls MCP tools inside that call is a distinct method and is not the
vanilla leaderboard setting. The vanilla arm does the single-turn path only.

### 13.2 Scope

- **Tasks**: all 10 — t1 (plan generation), t2 (cost-optimal planning), t3 (plan verification), t4 (plan reuse), t5 (plan generalization), t6 (replanning), t7 (reasoning about plan execution), t8_1 / t8_2 / t8_3 (goal-reformulation variants).
- **Configs (vanilla arm)**: canonical Blocksworld + Logistics + Depots. Mystery Blocksworld was covered by the with-tools arm and its matched no-tools cells (see the results doc above).
- **Models (vanilla arm)**: per-sweep choice. Canonical tags from `PDDL_VLLM_VERIFIED_MODELS` (resolved to HF ids by `vllm_lookup`); cluster runs use the same `PDDL_DEFAULT_MODELS` roster as the 5-task sweep by default. Run history: CHANGELOG 2026-05-18 and 2026-06-02.

### 13.3 Integration architecture

LLMs-Planning is cloned per-host into `external/LLMs-Planning/` and patched idempotently:

1. **`utils/__init__.py`**: tolerate missing `OPENAI_API_KEY` at import (PlanBench's `utils/__init__.py:9` hard-codes `os.environ["OPENAI_API_KEY"]` at module load).
2. **`utils/llm_utils.py`**: tolerate missing transformers/openai imports + add a dispatch branch
   ```python
   elif engine.startswith('pddl_copilot__'):
       from planbench.engine import pddl_copilot_send_query
       return pddl_copilot_send_query(query, engine, max_tokens, model=model, stop=stop)
   ```
3. **`plan-bench/response_generation.py`**: fix the upstream self-destructing `--specific_instances` filter (it `.remove()`s each matched id, so after the last match the guard `len(specified_instances) > 0` flips False and every remaining instance falls through). Replaced with a once-snapshotted set membership test. Backend-independent.

Patches live in `planbench/apply_patches.py` (anchored on stable strings, not line numbers — survives most upstream churn).

The cluster sbatch (`run_planbench_rtx.sbatch`) self-deploys vLLM (mirroring `run_condition_vllm_rtx.sbatch`: pinned `vllm/vllm-openai:v0.20.2` SIF, `vllm_lookup`-resolved serve flags, readiness probe + VRAM guard) and exports `VLLM_BASE` + `PDDL_COPILOT_THINK` for `engine.py`. It serves with `--served-model-name <canonical-tag>` so the OpenAI `model` field, the engine name, and PlanBench's `results/<engine>/` dir all stay the slash-free canonical tag (not the HF id). It skips PlanBench's prompt-generation stage (uses the pre-shipped `prompts/<config>/*.json`) and calls `response_generation.py` + `response_evaluation.py` directly — `llm_plan_pipeline.py` doesn't forward `--specific_instances`.

### 13.4 Engine name format

`pddl_copilot__<backend>__<model>`

- `<backend>` ∈ `{vllm, ollama}` — **vllm** is the active path; `ollama` is archaeology only (Ollama backend retired 2026-05-18, code removed 2026-05-23 from the 5-task harness; a dead branch remains in `planbench/engine.py`).
- `<model>` is the canonical model tag, colons preserved by the double-underscore separator (`Qwen3.5:0.8B`, `qwen3.6:35b`, `gemma4:26b-a4b`). For vLLM it must equal the server's `--served-model-name` (the sbatch sets that to the canonical tag, not the HF id, so the engine name stays slash-free).

### 13.5 Non-obvious adapter behaviour

Corrections that deviate from the naive port of PlanBench's openai-style `send_query`:

- **`num_predict` floor.** PlanBench passes `self.max_gpt_response_length = 500` (a legacy OpenAI-completion cap). On thinking-capable models (qwen3.x, qwen3.6) the reasoning trace eats the entire 500-token budget and content emits empty. The adapter floors at 4096 (matches `pddl_eval/runner.py::DEFAULT_NUM_PREDICT` non-solve defaults).
- **No `[PLAN END]` in the stop list.** Stop strings match against the model's full output, including the thinking trace. PlanBench's prompts include `[PLAN END]` as instruction text; thinking-capable models echo it while reasoning about the prompt, so generation could halt before any content emits. The adapter passes only the caller-supplied `stop` (PlanBench passes `"[STATEMENT]"`, the few-shot delimiter). PlanBench's parser extracts the `[PLAN]…[PLAN END]` block from full output anyway.
- **Thinking control (vLLM).** `PDDL_COPILOT_THINK` (set by the sbatch from `THINK`, default `off`) maps to `chat_template_kwargs.enable_thinking`, mirroring `pddl_eval.vllm_client`. PlanBench's published baselines are non-thinking, so the default suppresses the qwen3 reasoning trace; `default` omits the kwarg (model default); gemma4 has no `<think>` tokens and ignores it.

### 13.6 Scoring + reproducibility

PlanBench writes per-instance JSON to `external/LLMs-Planning/plan-bench/results/<config>/<engine>/task_*.json` — fields include `instance_id`, `llm_raw_response`, `extracted_llm_plan`, `llm_correct`, and per-task extras (`llm_correct_binary` / `_w_type` / `_w_expl` for t3; `actual_cost_of_llm_plan` / `cost_by_llm` for t2). The cluster sbatch rsyncs these into `results/planbench/slurm_<model_tag>_<jobid>/` so our existing `sync.sh` carries them down, and `status.sh --bench planbench` renders a model × config completion matrix.

PlanBench's pre-shipped `prompts/<config>/task_*.json` files are deterministic (seeded random.seed(10) in `utils/__init__.py`), so our adapter's only contribution to non-determinism is the underlying vLLM call. We use `temperature=0.0` matching the 5-task matrix.

### 13.7 What this arm does NOT change

- `pddl_eval/` — zero touches. Existing 5-task `results/<run-dir>/single_task_*.json` schemas, scoring, and Wilson CIs are byte-comparable across the 2026-05-18 commit.
- MCP plugin contract (`MCPPlanner._PINNED_VERBOSE_FALSE`, schema-strip behaviour) — unchanged. PlanBench engine doesn't talk to MCP in v1.

### 13.8 With-tools arm — closed

The tool-using arm that earlier versions of this section described as planned ("v2",
ISS-022) ran in August 2026 and closed with PR #93. The plan sketched here at the time
(two new MCP tools, an engine-name scheme) is not a description of what ran. Read the
prereg and the results doc named at the top of §13 instead.

---

## 14. The delivered layer and the other runners

None of this changes how `run_experiment.py` scores a trial.

**Two success layers.** The harness scores a with-tools trial from the tool
result (§4.1): the *tool-verified* layer. The *delivered* layer asks whether
the final answer the model handed back to the user is correct. It is always
computed offline from the stored `response`; `trials.jsonl` is never rewritten.

| Corpus | Delivered grader |
|---|---|
| October rerun (`results/delivered-rerun`) | the frozen package `tools/delivered_rerun/` (registration `development/reference/delivered_rerun_prereg.md`) |
| Corrected-prompt control (`results/control-promptfix`) | `tools/reanalysis/control_prompt_fix.py` (registration `development/reference/control_prompt_fix_prereg.md`) |
| May sweep and the Claude runs | the overlay `tools/e2e_regrade.py`, aggregated by `.claude/skills/analyzer/scripts/e2e_overlay.py`; decisions in `development/reference/tool_call_vs_final_output_grading.md` |

Ground truth for the offline graders is the cache `results/derived/gt_cache.json`.

**Storage cap and censoring.** A corpus written before 2026-06-25 stored only
the first 500 characters of an answer; from 2026-06-25 to 2026-10-02 the cap was
16384; since then it is 65536 (§9). A stored answer that sits at the cap with no
gradable answer in the visible part is *censored*: it may have been cut by
storage, so it is neither a success nor a failure. A cell with censored trials
is reported as bounds, never as a point. This is why the May sweep has no
delivered rate for its tool arms.

**Frontier runner.** Claude API models do not go through `run_experiment.py`.
With-tools runs use `tools/frontier_runner.py`; no-tools runs use the batch
builder `tools/claude_api_batch.py`. Both build prompts through
`pddl_eval.runner.build_messages`, so a frontier trial gets the same prompt
text as an open-model trial. Several of these files are frozen by hash
(`development/MOVES.md`).

**Renamed domains.** `domains-anon/` holds the 20 domains with names and
symbols renamed (`tools/anon_*.py`), used for the contamination check under
run tag `sweep6`. Design: `development/reference/contamination_probe_plan.md`.

**Corpora are never pooled.** Each run has its own folder and run tag. Check
`development/NUMBERS.md` before quoting any figure, and
`development/STATUS.md` for which corpus the paper uses for what.
