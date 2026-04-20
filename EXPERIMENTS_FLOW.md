# Experiments Flow

Methodology reference for the PDDL Copilot experiment suite.
Reproduces and extends the evaluation from Benyamin et al., 2025 (arXiv:2509.12987).

---

## 1. High-Level Pipeline

```
run_background.sh [small|large|both]
  |
  +-- Activate .venv, start Ollama, pull models if needed
  |
  +-- FOR each tool_filter in {per-task, all}:
        FOR each prompt_style in {minimal, guided}:
          |
          run_experiment.py
            |
            1. Load PDDL domains from domains/{classical,numeric}/
            2. Connect to MCP servers (pddl-solver, pddl-validator)
            3. Generate ground truth (oracle solves every problem)
            4. Single-task evaluation (with-tools & without-tools)
            5. Multi-task chain evaluation
            6. Save results to output directory
```

Each combination of `(tool_filter, prompt_style)` produces its own output directory:
```
results/{tag}_{timestamp}_{filter}_{prompt}/
    single_task_{ts}.json
    chain_{ts}.json
    summary_{ts}.json
```

---

## 2. Experimental Dimensions

The experiment crosses four independent variables:

| Dimension | Values | Controls |
|-----------|--------|----------|
| **Model** | qwen3:0.6b, qwen3:4b | Model capacity |
| **Condition** | with-tools, without-tools | Whether MCP tools are available |
| **Tool filter** | all, per-task | Which tools the model sees |
| **Prompt style** | minimal, guided | System prompt detail level |
| **Think mode** | default, off | Qwen3 thinking-mode ablation (`--think off` tests whether token starvation from thinking causes solve failures, or raw model incapacity) |

### 2.1 Condition: with-tools vs without-tools

- **with-tools**: The model has MCP tool descriptions injected into the Ollama `tools` parameter. It can call tools in a loop (up to 10 iterations). The system prompt instructs it to use tools.
- **without-tools**: No tools available. The model must answer from its parametric knowledge. The system prompt says to work without external tools.

### 2.2 Tool Filter

Controls which MCP tools the model sees during with-tools evaluations.

- **all**: Every tool from all connected MCP servers is exposed every turn. This is the condition closest to the original paper and to real-world copilot usage where the model sees the full tool catalogue.
- **per-task**: Only tools relevant to the current task are exposed, via the `TASK_TOOLS` allowlist:

  | Task | Exposed Tools |
  |------|---------------|
  | solve | `classic_planner`, `numeric_planner` |
  | validate_domain | `validate_pddl_syntax` |
  | validate_problem | `validate_pddl_syntax` |
  | validate_plan | `validate_pddl_syntax` |
  | simulate | `get_state_transition` |

This dimension measures whether tool-selection noise from unrelated tools degrades performance.

### 2.3 Prompt Style

Controls how much guidance the system prompt gives about tool argument formatting.

- **minimal**: Original system prompt from the paper. Tells the model to use tools but says nothing about how to format arguments:
  > *"You are a PDDL planning assistant with access to planning tools. Your ONLY way to get information or solve problems is by calling the provided tools ONE AT A TIME -- never guess or create plan details yourself."*

- **guided**: Appends one sentence instructing the model to pass full PDDL content as tool arguments:
  > *"When calling tools, pass the complete PDDL text from the user message (starting with '(define ...') as the 'domain' and 'problem' arguments -- not file names or domain names."*

**Motivation**: Small models (0.6b) were observed to pass domain names (e.g., `"blocksworld"`) instead of PDDL content strings as tool arguments, causing 100% tool execution failure on the `solve` task despite 74.5% correct tool selection. This dimension isolates whether a minimal prompt nudge recovers tool-use competence.

---

## 3. Tasks

Five tasks, each testing a different stage of the PDDL planning pipeline:

| Task | What the model must do | Ground truth source |
|------|----------------------|---------------------|
| **solve** | Find a valid plan for a domain + problem | `classic_planner` / `numeric_planner` oracle |
| **validate_domain** | Judge whether a domain has valid PDDL syntax | `validate_pddl_syntax` oracle |
| **validate_problem** | Judge whether a problem has valid syntax given its domain | `validate_pddl_syntax` oracle |
| **validate_plan** | Verify a given plan is correct | `validate_pddl_syntax` oracle |
| **simulate** | Produce a state-transition trace for a plan | `get_state_transition` oracle |

Each task uses 5 prompt template variants (different phrasings of the same request) for robustness.

---

## 4. Success Criteria

### 4.1 With-Tools: Two Metrics

The with-tools condition reports two separate metrics:

1. **tool_selected** -- Did the model call the *correct* MCP tool?
   - `solve`: called `classic_planner` or `numeric_planner`
   - `validate_*`: called `validate_pddl_syntax`
   - `simulate`: called `get_state_transition`

2. **success** (end-to-end) -- Was the tool result correct?
   - `solve`: tool returned a plan that passes pyvalidator validation (`valid == true`)
   - `validate_*`: tool result verdict matches ground truth (VALID/INVALID), with the call's argument shape matching the task (e.g., `validate_plan` requires `plan` in args; a domain-only call is rejected)
   - `simulate`: tool's `trajectory` equals the oracle's `gt["trace"].trajectory`. The plugin's `valid` field is a PDDL-syntactic signal, not a simulation-correctness signal — a partial trajectory with `valid=false` would pass a naive non-error check. Oracle and model calls go through the same bridged `get_state_transition(verbose=False)` with identical `(domain, problem, plan)` inputs, so a matching trajectory is deterministic. Mismatch → `FR_RESULT_MISMATCH`.

A model can have high tool_selected but low success (knows *what* to call but can't construct valid arguments). This gap quantifies "tool-use competence" vs "tool awareness."

### 4.2 Without-Tools

- `solve`: Extract plan lines from response, validate via pyvalidator (`valid == true`)
- `validate_*`: Extract `VERDICT: VALID` or `VERDICT: INVALID` from response, compare to ground truth
- `simulate`: Response contains "state" and ("after" or "step") -- loose keyword check

### 4.3 Chains

A chain of length N picks N random tasks and executes them sequentially in a single conversation. The chain succeeds only if **every** task in the sequence succeeds (all-or-nothing).

---

## 5. Evaluation Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Temperature | 0.0 | Deterministic sampling |
| Max tool loops | 10 | Per single evaluation |
| Prompt variants | 5 | Per task, different phrasings |
| Chain samples | 20 | Per chain length |
| Chain lengths | 2, 3, 4, 5 | |
| Random seed | 42 | For chain task sampling |

---

## 6. Domains

```
domains/
  classical/
    blocksworld/   domain.pddl + p01..p05  (5 problems)
    depots/        domain.pddl + p01..p03  (3 problems)
  numeric/
    counters/      domain.pddl + p01..p03  (3 problems)
```

3 domains, 11 problems total. The paper evaluated 10 domains from IPC benchmarks; this subset is used for faster iteration.

---

## 7. Ground Truth Generation

Before any model evaluation, the experiment generates oracle answers by calling the MCP tools directly:

1. **validate_pddl_syntax**(domain) -- domain validity verdict
2. **validate_pddl_syntax**(domain, problem) -- problem validity verdict
3. **classic_planner** or **numeric_planner**(domain, problem) -- oracle plan
4. **validate_pddl_syntax**(domain, problem, plan) -- plan validity verdict
5. **get_state_transition**(domain, problem, plan) -- oracle state trace

These oracle results become the ground truth for scoring model responses.

---

## 8. MCP Tool API Contract

Tools are served by two MCP plugin servers from the [pddl-copilot](https://github.com/SPL-BGU/pddl-copilot) marketplace (v2.0.0+, pure pip — no Docker). The solver uses Fast Downward via `up-fast-downward` and ENHSP via `up-enhsp`; the validator uses `pddl-pyvalidator`. Numeric planning via ENHSP requires Java 17+.

### pddl-solver

| Tool | Parameters | Returns |
|------|-----------|---------|
| `classic_planner` | `domain` (PDDL content or file path), `problem` (same), `strategy` (optional: lazy_greedy_cea, astar_lmcut, lazy_greedy_ff) | `{plan: [...], solve_time: float}` or `{error: true, message: str}` |
| `numeric_planner` | `domain`, `problem` | Same format |

### pddl-validator

| Tool | Parameters | Returns |
|------|-----------|---------|
| `validate_pddl_syntax` | `domain` (required), `problem` (optional), `plan` (optional), `verbose` (optional, default `True`) | `verbose=True`: `{valid, status, report, details}`. `verbose=False`: `{valid, status, report}`. Error: `{error: true, message: str}` |
| `get_state_transition` | `domain`, `problem`, `plan` (all required), `verbose` (optional, default `True`) | `verbose=True`: `{valid, report, steps, trajectory, details}`. `verbose=False`: `{valid, steps, trajectory}`. Error: `{error: true, message: str}` |

**Input detection**: Tools check if an argument starts with `(` or `;` or contains `(define ` to detect inline PDDL content. Otherwise the argument is treated as a file path. This is why passing a domain name like `"blocksworld"` fails -- it's interpreted as a file path that doesn't exist.

**Response-size policy (structured projection, no truncation).** Each validator tool accepts an optional `verbose` parameter that defaults to `True` so standalone MCP callers (Claude Desktop, `ollama_mcp_bridge.py`, future consumers) still receive the full pyvalidator fidelity by default. Setting `verbose=False` drops the redundant fields that re-serialize information already present elsewhere in the response: `details` on `validate_pddl_syntax`; `report` and `details` on `get_state_transition`. Kept fields — `status`, `report` (validate), `steps`, `trajectory` with full `boolean_fluents`/`numeric_fluents` per step — are returned in full; there is no item or character cap.

**Experiment bridge enforces `verbose=False`.** `run_experiment.py::MCPPlanner` strips the `verbose` property from each validator tool's `inputSchema` before passing tools to Ollama, and injects `verbose=False` on every call (see `_PINNED_VERBOSE_FALSE`). The experiment agent cannot see or control the flag. This keeps tool responses compact for the LLM without changing the plugin's default contract for other callers. Prior `tool_calls[*].result` strings recorded in `results/` are not byte-comparable with post-change runs, but scoring (`_parse_validation_verdict`, simulate non-empty check) is unchanged.

**Aligned cap hygiene in the MCP repo.** The existing caps in `../pddl-copilot` now follow a consistent `DEFAULT_*` module-constant + `PDDL_*` env override convention (defaults unchanged):

| Cap | Env var | Default |
|---|---|---|
| Grounding attempts in `get_applicable_actions` | `PDDL_MAX_GROUNDING_ATTEMPTS` | 10000 |
| Applicable-actions return list | `PDDL_MAX_APPLICABLE_ACTIONS` | 50 |
| Planner failure-log tail length | `PDDL_MAX_LOG_CHARS` | 3000 |
| Planner wall-clock timeout (s) | `PDDL_TIMEOUT` | 120 |

---

## 9. Output Files

Each run produces three JSON files:

### summary_{ts}.json

Aggregated statistics. Top-level object with `single_task` and `chains` arrays.

`single_task` entries:
| Field | Description |
|-------|-------------|
| model, condition, task | Grouping key |
| successes, n, success_rate | End-to-end success |
| ci_lo, ci_hi | 95% Wilson score CI |
| tool_selected, tool_selected_rate, tool_selected_ci_lo, tool_selected_ci_hi | Tool selection (with-tools only) |

`chains` entries: model, with_tools, chain_length, samples, successes, success_rate, tool_filter, prompt_style, ci_lo, ci_hi.

### single_task_{ts}.json

Raw per-evaluation results. Each entry is one (model, task, domain, problem, prompt_variant, condition) evaluation.

| Field | Description |
|-------|-------------|
| model, task, domain_name, problem_name, prompt_variant | Evaluation identity |
| with_tools | Condition |
| success | End-to-end correctness |
| tool_selected | Correct tool called (with-tools only, null otherwise) |
| response | Model text response (truncated to 500 chars) |
| tool_calls | List of `{name, arguments, result}` dicts |
| duration_s | Wall-clock time |
| error | Error message if any |
| tool_filter | "all" or "per-task" |
| prompt_style | "minimal" or "guided" |

### chain_{ts}.json

Per-configuration chain results (model, with_tools, chain_length, samples, successes, success_rate, tool_filter, prompt_style).

---

## 10. Running Experiments

### Background (recommended)

```bash
./run_background.sh small    # qwen3:0.6b -- ~4 runs (2 filters x 2 prompts)
./run_background.sh large    # qwen3:4b
./run_background.sh          # both models
```

### Direct CLI

```bash
python3 run_experiment.py \
    --marketplace-path ../pddl-copilot \
    --models qwen3:0.6b \
    --tool-filter all \
    --prompt-style guided \
    --chains \
    --output-dir results/my_run/
```

### Monitoring

```bash
tail -f run_*.log           # Watch progress
ps -p <PID>                 # Check if running
kill <PID>                  # Stop
```

---

## 11. Differences from the Original Paper

| Aspect | Paper (Benyamin et al., 2025) | This Framework |
|--------|-------------------------------|----------------|
| Success metric (with-tools) | Tool selection only | Tool selection AND end-to-end result validation |
| Tool filter | All tools exposed | Configurable: all or per-task |
| Prompt style | Single prompt | Configurable: minimal or guided |
| Models | Qwen3, GPT-OSS (various sizes) | Ollama models (qwen3:0.6b, qwen3:4b) |
| Domains | 10 IPC benchmarks | 3 sample domains (blocksworld, depots, counters) |
| MCP integration | Claude Desktop plugins | Direct MCP stdio connections |
| Validator tool schema | pyvalidator-native shape (`details`, verbose `report` on both tools) | Plugin defaults unchanged (`verbose=True` returns full fidelity). The experiment bridge hides a `verbose` flag and pins it to `False`, projecting the response to `{valid, status, report}` for `validate_pddl_syntax` and `{valid, steps, trajectory}` for `get_state_transition`. |
| Simulate success criterion | Non-error tool result | Trajectory deep-equality against oracle `gt["trace"]`. A partial trajectory with `valid=false` is scored `FR_RESULT_MISMATCH`, not silent success. |

The key methodological addition is the separation of **tool selection** from **end-to-end success**, which reveals cases where models know which tool to use but fail to construct valid arguments.
