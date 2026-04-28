# Experiments Flow

Methodology reference for the PDDL Copilot experiment suite.
Reproduces and extends the evaluation from Benyamin et al., 2025 (arXiv:2509.12987).

---

## 1. High-Level Pipeline

The harness is `run_experiment.py`. It runs one model × one think-mode × one
condition (4 tools-conditions or no-tools) per invocation, optionally
followed by a chain phase. There are two driver paths:

- **Local laptop** — `run_background.sh [small|large|both]` wraps `caffeinate`
  + a local `ollama serve`, then loops `(tool_filter, prompt_style)` itself.
- **BGU cluster** — `cluster-experimenting/submit_with_rtx.sh <model>...`
  (single submit path; default GPU `rtx_pro_6000:1`). See
  `cluster-experimenting/README.md`. The sbatch loops
  `MODELS × THINK_MODES × CONDITIONS` in-process so weights stay resident
  on the allocated GPU.

```
run_experiment.py
  |
  1. Load PDDL domains from domains/{classical,numeric}/
  2. Connect to MCP servers (pddl-solver, pddl-validator, pddl-parser)
  3. Generate ground truth (oracle solves every problem)
  4. Single-task evaluation (with-tools & without-tools)
  5. Multi-task chain evaluation (skipped for no-tools)
  6. Save results to output directory
```

Each `(model, think, condition, tool_filter, prompt_style)` produces its
own output directory:
```
results/slurm_<model>_<think>_<cond>_<jobid>/        # cluster
results/{tag}_{timestamp}_{filter}_{prompt}/         # laptop
    single_task_{ts}.json
    chain_{ts}.json
    summary_{ts}.json
```

---

## 2. Experimental Dimensions

The experiment crosses five independent variables:

| Dimension | Values | Controls |
|-----------|--------|----------|
| **Model** | Cluster sweep (default): `Qwen3.5:0.8B`, `gpt-oss:20b`, `Qwen3.5:27b`, `Qwen3.5:35b`, `gemma4:31b` (peak ~30 GB resident, packed in one rtx_pro_6000:1 job under `MAX_LOADED_MODELS=1`). Paper-aligned (laptop): `qwen3:0.6b`, `qwen3:4b`. `gpt-oss:120b` is no longer in the active sweep — Qwen3.5:35b substitutes for it in the large-model size band | Model capacity & family |
| **Condition** | with-tools, without-tools | Whether MCP tools are available |
| **Tool filter** | all, per-task | Which tools the model sees |
| **Prompt style** | minimal (active) — `guided` retired 2026-04-27 | System prompt detail level. Newcombe-Δ analysis on the 26042026 sweep (`checkpoints/cluster-26042026/prompt_variant_stats.md` §5) showed minimal-vs-guided shifts results by ≤4pp per model with every CI crossing zero. The `_GUIDED_SUFFIX` constant is preserved in code as documentation |
| **Think mode** | on, off, default | `on`/`off` toggles the Ollama `think` kwarg for models that support it (Qwen3.x, gpt-oss). `default` omits the kwarg — used for `gemma4:*` historically; the rtx path now passes `on/off` to all models and lets the runtime ignore unsupported values. `--think off` tests whether token starvation from thinking causes solve failures, or raw model incapacity. |

The cluster's model set differs from the paper's `qwen3:0.6b`/`qwen3:4b`
because the BGU Ollama-on-cluster inventory does not host those tags
(verified 2026-04-20). The five-model set above spans the same parameter
range (≤1B → 35B) and covers three families (Qwen, GPT-OSS, Gemma) —
see §11 for the full deviations table.

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

The without-tools sweep covers `solve` plus the three `validate_*` tasks
(re-enabled 2026-04-26 once balanced negative fixtures landed; ISS-001).
`simulate` remains excluded.

- `solve`: Extract plan lines from response, validate via pyvalidator (`valid == true`)
- `validate_*`: Extract `VERDICT: VALID|INVALID` and compare against ground truth.
  With 1:1 balanced positives + negatives (`§6 Domains`), a constant-VALID prior
  scores ~50% (not 100%), so the grader is now discriminative.
- `simulate`: **Still dropped from no-tools.** Its grader is a literal keyword
  check (`run_experiment.py:910-912`); a structured-trajectory free-text grader
  would itself be a research artifact and a new source of bias (ISS-002 path b).
  With-tools `simulate` is unaffected.

`run_single_task_experiment` enforces the filter: jobs with `with_tools=False`
are emitted for every task **except** `simulate`.

### 4.3 Chains

A chain of length N picks N random tasks and executes them sequentially in a single conversation. The chain succeeds only if **every** task in the sequence succeeds (all-or-nothing).

---

## 5. Evaluation Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Temperature | 0.0 | Deterministic sampling |
| Max tool loops | 10 | Per single evaluation |
| Prompt variants | 5 | Per task, different phrasings |
| Chain samples | 20 (laptop default) / 100 (cluster default) | Per chain length. `run_experiment.py --chain-samples` defaults to 20; `cluster-experimenting/run_condition_rtx.sbatch` overrides to 100 (paper-aligned) via `CHAIN_SAMPLES` env. |
| Chain lengths | 2, 3, 4, 5 | |
| Random seed | 42 | For chain task sampling |

### Single-task vs chain-phase gating

The single-task phase grades every cell of the (`condition` × `think`)
matrix; the chain phase is restricted because chain trajectories carry
constraints that not every cell satisfies:

- `--chains` with `--conditions=no-tools|both` → chain phase skips
  `with_tools=False` (chains require artifact propagation across steps,
  which the model can't do honestly without tools).
- `--chains` with `--think=off` → chain phase is skipped entirely
  (ISS-018, closed 2026-04-28). `think=off` is a single-task ablation
  against `think=on`/`think=default`; chain results under it aren't
  part of any planned comparison.
- `--num-ctx-thinking` (default 12288) replaces `--num-ctx` (default
  8192) for ALL cells where `think != off`, regardless of condition.
  `think=off` keeps the smaller context budget. The condition axis was
  dropped from this rule on 2026-04-28 — flipping `num_ctx` mid-pass
  deadlocked Ollama under concurrency (smoke job 17244356), and a
  constant `num_ctx` per pass costs only a few KB extra KV cache on
  tool-condition runs.

The PR-2 abort gate that previously exited early for
`--conditions=no-tools|both` under `--think on/default` was lifted
2026-04-28 — thinking content is now captured separately
(`TaskResult.thinking`) so it does not contaminate the graded
response. See CHANGELOG 2026-04-28 (PR-2).

---

## 6. Domains

```
domains/
  classical/
    barman/        domain.pddl + p01[.pddl|.plan]   + domain_0.pddl + p01_0[.pddl|.plan]
    blocksworld/   domain.pddl + p01[.pddl|.plan]   + domain_0.pddl + p01_0[.pddl|.plan]
    depots/        ... (same shape)
    rovers/        ...
    satellite/     ...
  numeric/
    counters/      domain.pddl + p01[.pddl|.plan]   + domain_0.pddl + p01_0[.pddl|.plan]
    depot/         ... (singular; paper's numeric split)
    farmland/      ...
    pogo_stick/    ...
    sailing/       ...
```

10 domains × 1 positive problem each — copied verbatim from the paper dataset snapshot at `.local/pddl_mcp_dataset/` (Benyamin et al., 2025, Aug 2025). Each domain also ships `p01.plan` (paper's `plan.solution`) as a reference artifact for manual cross-check; it is **not** read into prompts — the MCP oracle regenerates plan + trace on every run.

**Negative fixtures (added 2026-04-26, ISS-001).** Each domain also ships three task-targeted negatives — `domain_0.pddl` (validate_domain only), `p01_0.pddl` (validate_problem only), `p01_0.plan` (validate_plan only). The `_0` suffix denotes "negative" but is validity-neutral: the LLM never sees a path (prompts pass content, not paths), and `_0` reads as a numeric variant index even if a path were ever leaked. Each negative joins exactly its target task, so per-task ground truth is now 1:1 balanced (10 positive + 10 negative). See `domains/README.md` for the bug taxonomy.

**Expected validity:** positives are expected to pass `domain_valid == problem_valid == plan_valid == solvable == True`. The startup ground-truth summary prints these flags per positive problem for manual review; drift is not auto-enforced. Negatives, by contrast, are **strictly enforced** — `generate_ground_truth` aborts startup with `SystemExit` if any negative validates as anything other than False.

**Pairing convention (known limitation).** `validate_problem` and `validate_plan` negative jobs always pair their negative file with the *positive* counterparts of the other layers (the `validate_problem` negative uses positive `domain.pddl`; the `validate_plan` negative uses positive `domain.pddl` + positive `p01.pddl`). The paper dataset ships one positive problem per domain, so the negative plan is always paired with `p01.pddl`. The LLM never sees a filename — prompts interpolate content via `.format(domain=…, problem=…, plan=…)` (`run_experiment.py:989`) — so this isn't a leak channel. Multi-problem datasets would need a designated-primary lookup at the two `next(iter(dinfo["problems"].values()))` sites in `generate_ground_truth` and the job builder.

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

Aggregated statistics. Top-level object with `single_task` and `chains` arrays, plus an optional `meta` dict.

`single_task` entries:
| Field | Description |
|-------|-------------|
| model, condition, task | Grouping key |
| successes, n, success_rate | End-to-end success |
| ci_lo, ci_hi | 95% Wilson score CI |
| tool_selected, tool_selected_rate, tool_selected_ci_lo, tool_selected_ci_hi | Tool selection (with-tools only) |
| truncated | Count of evaluations where `done_reason == "length"` (token-cap hit) |
| failure_reasons | Dict of `FR_*` reason → count (open-ended; new buckets are additive). Notable: `FR_THINK_OVERFLOW` (PR-2, 2026-04-28) — thinking spiral consumed the completion budget leaving empty `content`; more specific than `FR_TRUNCATED_NO_ANSWER`. |

`chains` entries: model, with_tools, chain_length, samples, successes, success_rate, tool_filter, prompt_style, ci_lo, ci_hi, plus `samples_detail` — a per-sample list of `{idx, domain, problem, chain_tasks, step_records, final_success, exception}` (each `step_records[*]` carries `step_index, task, success, failure_reason, tool_calls_count, truncated, loop_exhausted`). Effective chain length per sample = `len(step_records)` (skipped no-plan steps are absent).

`meta` (present when `save_results` is called with metadata; written by `async_main`):
| Field | Description |
|-------|-------------|
| host | Where the run executed (`localhost`, RTX node hostname like `ise-cpu256-09:11434`, etc.). The legacy `is_remote` field was retired 2026-04-27 along with the cis-ollama path. |
| conditions | `tools`, `no-tools`, or `both` |
| models, tasks | CLI inputs that selected which models/tasks ran |
| num_variants, prompt_variants_active, num_ctx, num_ctx_thinking, num_predict, temperature, think | Reproducibility knobs. `prompt_variants_active` records the actual variant indices used (e.g. `[0, 1, 2]` after the 2026-04-27 trim) — `num_variants` alone doesn't disambiguate which paraphrases ran. `num_ctx_thinking` (PR-2, 2026-04-28) is the bigger context budget used for ALL cells where `think != off` (the condition axis was dropped after the cluster smoke deadlocked on the mid-pass num_ctx flip). |
| tool_filter, prompt_style | Recorded only when `conditions ∈ {tools, both}` (with-tools knobs) |

### single_task_{ts}.json

Raw per-evaluation results. Each entry is one (model, task, domain, problem, prompt_variant, condition) evaluation.

| Field | Description |
|-------|-------------|
| model, task, domain_name, problem_name, prompt_variant | Evaluation identity |
| with_tools | Condition |
| success | End-to-end correctness |
| tool_selected | Correct tool called (with-tools only, null otherwise) |
| response | Model text response (truncated to `RESPONSE_SNAPSHOT_LEN=500` chars) |
| thinking | Last-turn structured `message.thinking` content (PR-2, truncated to `THINKING_SNAPSHOT_LEN=4096` chars). Empty string when the model didn't emit thinking. For multi-turn `with_tools` runs, only the last turn's thinking is recorded — earlier-turn reasoning is observable via `tool_calls[]`. |
| tool_calls | List of `{name, arguments, result}` dicts |
| tokens | Dict `{prompt, completion, turns, total_duration_ns, eval_duration_ns}` (PR-2). Counts are summed across `client.chat()` turns; `turns=1` for `with_tools=False`, up to `MAX_TOOL_LOOPS=10` otherwise. Durations are Ollama's server-side aggregates; `eval_duration_ns ≤ total_duration_ns`. Used for tokens-per-second and prompt-shrinkage analysis. |
| duration_s | Wall-clock time around the chat helper (Python + MCP latency included; not the same as `tokens.total_duration_ns`) |
| error | Error message if any |
| failure_reason | `FR_*` constant from `pddl_eval/scoring.py` ("ok" iff `success=True`); see `failure_reasons` description above for the open-ended vocabulary |
| truncated | `done_reason == "length"` on any turn (output-token cap hit) |
| done_reason | Raw `done_reason` from the last chat turn (`"stop"`, `"length"`, etc.) |
| tool_filter | "all" or "per-task" |
| prompt_style | "minimal" (the `"guided"` retirement is recorded in `PROMPT_STYLE_CHOICES` in `run_experiment.py`) |

### chain_{ts}.json

Per-configuration chain results (model, with_tools, chain_length, samples, successes, success_rate, tool_filter, prompt_style).

---

## 10. Running Experiments

### Cluster (default for paper sweeps)

The full 5-model sweep on the BGU rtx GPUs:

```bash
# Full 5-model sweep packed in one rtx_pro_6000 job (Qwen3.5:0.8B, gpt-oss:20b,
# Qwen3.5:27b, Qwen3.5:35b, gemma4:31b — peak ~30 GB resident under
# MAX_LOADED_MODELS=1, so weights swap rather than co-reside).
ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
  bash cluster-experimenting/submit_with_rtx.sh --all"

# Single-model run (e.g. iterating on one model)
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b

# Baseline-only no-tools sweep (4-task discriminative matrix, packed)
bash cluster-experimenting/submit_with_rtx.sh --all --no-tools
```

See `cluster-experimenting/README.md` for full submission flow,
`.claude/skills/cluster-ops/SKILL.md` for status/preflight/postmortem
helpers.

### Laptop background

```bash
./run_background.sh small    # qwen3:0.6b -- ~4 runs (2 filters x 2 prompts)
./run_background.sh large    # qwen3:4b
./run_background.sh          # both models
```

`run_background.sh` is macOS-oriented (uses `caffeinate`, expects local
`ollama serve`). On Linux laptops, run `run_experiment.py` directly.

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
tail -f run_*.log           # Laptop: watch progress
ps -p <PID>                 # Laptop: check if running
kill <PID>                  # Laptop: stop

# Cluster: see cluster-experimenting/README.md "Monitoring" section
squeue --me                 # All my running/pending jobs
```

---

## 11. Differences from the Original Paper

| Aspect | Paper (Benyamin et al., 2025) | This Framework |
|--------|-------------------------------|----------------|
| Success metric (with-tools) | Tool selection only | Tool selection AND end-to-end result validation |
| Tool filter | All tools exposed | Configurable: all or per-task |
| Prompt style | Single prompt | `minimal` only (paper-aligned) as of 2026-04-27. `guided` was active during the 26042026 sweep but retired after the Newcombe-Δ analysis showed it didn't move outcomes outside CIs; `_GUIDED_SUFFIX` is preserved in `run_experiment.py` as documentation |
| Models | Qwen3, GPT-OSS (various sizes) | Cluster sweep: `Qwen3.5:0.8B`, `gpt-oss:20b`, `Qwen3.5:27b`, `Qwen3.5:35b`, `gemma4:31b` (peak ~30 GB resident; rtx self-deploy on rtx_pro_6000:1 with `MAX_LOADED_MODELS=1`). Laptop default: `qwen3:0.6b`, `qwen3:4b` (paper-aligned). `gpt-oss:120b` was substituted by `Qwen3.5:35b` in the large-model size band (2026-04-27); it is no longer in the active sweep. The cis-ollama fallback path was retired the same day — rtx_pro_6000 self-deploy is the only cluster transport. |
| Domains | 10 IPC benchmarks | Same 10 IPC benchmarks (barman, blocksworld, depots, rovers, satellite, counters, depot, farmland, pogo_stick, sailing) — copied from the paper's published dataset |
| MCP integration | Claude Desktop plugins | Direct MCP stdio connections |
| Validator tool schema | pyvalidator-native shape (`details`, verbose `report` on both tools) | Plugin defaults unchanged (`verbose=True` returns full fidelity). The experiment bridge hides a `verbose` flag and pins it to `False`, projecting the response to `{valid, status, report}` for `validate_pddl_syntax` and `{valid, steps, trajectory}` for `get_state_transition`. |
| Simulate success criterion | Non-error tool result | Trajectory deep-equality against oracle `gt["trace"]`. A partial trajectory with `valid=false` is scored `FR_RESULT_MISMATCH`, not silent success. |
| No-tools task set | All 5 tasks scored | `solve` + three `validate_*` (the latter restored 2026-04-26 alongside balanced 1:1 ground truth; ISS-001 closed). `simulate` remains excluded — its keyword-check grader is non-discriminative regardless of negatives, and a structured-trajectory free-text grader would itself be a research artifact (ISS-002 path b). With-tools task set unchanged. |
| No-tools matrix | Crossed with all think modes + chains | Gated to `--think off` + single-task only. See §5. |

The key methodological addition is the separation of **tool selection** from **end-to-end success**, which reveals cases where models know which tool to use but fail to construct valid arguments.
