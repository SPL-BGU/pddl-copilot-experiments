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
| **Model** | Cluster sweep (default, post 2026-04-30 roster trim): `Qwen3.5:0.8B`, `qwen3.6:27b`, `qwen3.6:35b`, `gemma4:31b` (peak ~26 GB resident, packed in one rtx_pro_6000:1 job under `MAX_LOADED_MODELS=1`). Paper-aligned (laptop): `qwen3:0.6b`, `qwen3:4b`. `gpt-oss:120b` retired 2026-04-27; `gpt-oss:20b` and `Qwen3.5:27b/35b` superseded 2026-04-29; `nemotron-3-nano:30b` (the 2026-04-29 non-Qwen/Gemma slot) dropped 2026-04-30 after Hermes XML parse failures proved content-dependent (CHANGELOG). | Model capacity & family |
| **Condition** | with-tools, without-tools | Whether MCP tools are available |
| **Tool filter** | all, per-task | Which tools the model sees |
| **Prompt style** | minimal (active) — `guided` retired 2026-04-27 | System prompt detail level. Newcombe-Δ analysis on the 26042026 sweep (`checkpoints/cluster-26042026/prompt_variant_stats.md` §5) showed minimal-vs-guided shifts results by ≤4pp per model with every CI crossing zero. The `_GUIDED_SUFFIX` constant is preserved in code as documentation |
| **Think mode** | on, off, default | `on`/`off` toggles the Ollama `think` kwarg for models that support it (Qwen3.x, qwen3.6). `default` omits the kwarg — used for `gemma4:*` historically; the rtx path now passes `on/off` to all models and lets the runtime ignore unsupported values. `--think off` tests whether token starvation from thinking causes solve failures, or raw model incapacity. |

The cluster's model set differs from the paper's `qwen3:0.6b`/`qwen3:4b`
because the BGU Ollama-on-cluster inventory does not host those tags
(verified 2026-04-20). The four-model set above spans the same parameter
range (≤1B → 35B) and covers two families (Qwen, Gemma). The 2026-04-29
roster refresh attempted to keep the family-diversity slot non-Qwen by
swapping `gpt-oss:20b` → NVIDIA `nemotron-3-nano:30b` (hybrid
Mamba+MoE+Attn), but smoke 17274424 (2026-04-30) showed Hermes XML
tool-call parse failures persisting on the same 4 cells across the
4096→6144 num_predict bump — confirming the failure mode as
content-dependent, not budget-dependent — so nemotron was dropped from
the active roster pending an alternate non-Qwen/Gemma replacement.
`qwen3.6:27b` is text-capable on the dense path; the Ollama tag bundles
multimodal weights but text-only inference is unaffected. See §11 for
the full deviations table.

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
| **simulate** | Produce a state-transition trajectory for a plan | `get_state_transition` oracle. With-tools and no-PDDL-tools both grade by canonical-form deep-equality of the produced trajectory against the oracle's (PR-4, 2026-04-29). |

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

### 4.2 No-PDDL-Tools (formerly "without-tools")

PR-4 (2026-04-29) reframes this condition. The model still has Ollama
`format=<json_schema>` constraint enforcement available; what's removed
is the PDDL-specific MCP tooling (planning, validation, simulation).
The user-facing label is **no-PDDL-tools**. The internal field name
(`with_tools: bool`) and JSON `condition: "no-tools"` value are unchanged
for back-compat with the 2026-04 result corpus and downstream notebooks.

The sweep covers all 5 tasks (`simulate` re-enabled in PR-4 alongside
the format-constrained grader). Per-task grading:

- `solve` — Sampler constrained to `SolveResponse = {plan: list[str]}`.
  Extracted plan goes through pyvalidator; `valid == true` → success.
  Free-text plan extractor (`extract_plan_lines`) remains as a fallback
  if JSON parse fails.
- `validate_*` — Sampler constrained to
  `ValidateResponse = {verdict: Literal["VALID", "INVALID"], reason: str}`.
  `verdict` is compared to ground truth; `reason` is recorded but
  ungraded. Free-text `VERDICT: VALID|INVALID` extractor falls back when
  JSON parse fails. With 1:1 balanced positives + negatives (`§6
  Domains`), a constant-VALID prior scores ~50%, so the grader is
  discriminative on both paths.
- `simulate` — Sampler constrained to
  `SimulateResponse = {trajectory: list[StateStep]}` where each step
  carries `{step: int, action: str, state: {boolean: list[str], numeric:
  dict[str, float]}}`. The model's trajectory and the oracle's
  `gt["trace"].trajectory` are both passed through
  `_normalize_trajectory` (see `pddl_eval/scoring.py`) which collapses
  the oracle's `boolean_fluents: dict[str, bool]` shape and the model's
  `state.boolean: list[str]` shape to the same canonical
  `{step, action, boolean, numeric}` form (sorted, lower-cased,
  whitespace-normalised). Equality of the two canonical lists →
  `FR_OK`; non-parseable JSON → `FR_FORMAT_PARSE_FAIL`; parses but
  trajectory differs → `FR_RESULT_MISMATCH`. No free-text fallback for
  simulate — the pre-PR-4 keyword grader was non-discriminative
  (ISS-002).

`FR_FORMAT_PARSE_FAIL` (new PR-4 failure tag) fires only when both the
JSON path and the free-text fallback (where applicable) fail to produce
a usable artefact. It is included in `_TRUNCATION_OVERRIDE_REASONS`, so
a cap-cut mid-JSON is re-tagged as `FR_TRUNCATED_NO_ANSWER` rather than
masquerading as a sampling-degeneracy failure.

**Re-baselining note.** Pre-PR-4 no-tools `validate_*` and `solve`
results were graded via free-text-only paths and are not directly
comparable to post-PR-4 no-PDDL-tools results: the format constraint
both narrows the response space (potentially raising accuracy on
structurally-honest models) and may degrade tiny-model output if the
constraint conflicts with the model's natural shape. Flag any plot that
mixes pre- and post-PR-4 no-tools rows. The with-tools branch is
unchanged structurally; with-tools `simulate` switched to the shared
`_normalize_trajectory` in PR-4 but the equality semantics are
identical (both sides round-trip through the same plugin and produce
byte-equal trajectory dicts on identical inputs).

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
- `--num-ctx` (default 16384, raised from 8192 on 2026-04-29) is the
  single-task context window for tools cells and for `think=off`
  no-tools cells. Bumped after qwen3.6:27b / nemotron-3-nano:30b smokes
  showed `think_overflow` at 12288 on `validate_problem`/`validate_plan`
  (6/12 and 10/20 fail rates in both tools and no-tools cells; every
  miss was `FR_THINK_OVERFLOW`). nemotron was dropped from the active
  roster on 2026-04-30 but the ctx evidence still applies via qwen3.6:27b.
  16384 leaves ~10K of think+output headroom on top of typical PDDL prompts.
- `--num-ctx-thinking` (default 16384, raised from 12288 on 2026-04-29)
  is used ONLY when `think != off` AND `condition=no-tools`. **Held
  equal to `--num-ctx`** by default — the "tools save tokens" headline
  comparison requires identical ctx budgets across the tools and
  no-tools branches; otherwise the no-tools cell could appear better or
  worse simply because it had more (or less) room to think. The
  parameter is kept as a separate constant so future asymmetric
  experiments can override one without touching the other.
  Implementation note: `async_main` splits a `(--conditions=both,
  think!=off)` invocation into two sequential `run_single_task_experiment`
  calls (one per condition), keeping `num_ctx` constant within each call.
  Without the split, mid-call `num_ctx` flips deadlocked Ollama under
  concurrency (smoke job 17244356, 2026-04-28).
- `--num-ctx-chain` (default 16384, added 2026-04-29) replaces `--num-ctx`
  for every step of a multi-task chain run. Chains accumulate the full
  message history across steps (each step re-embeds domain + problem +
  plan in its user prompt, and prior assistant turns + tool-call results
  remain in context), so step-4 prompts on blocksworld-class problems
  can reach ~6–8K tokens before generation. Held equal to `--num-ctx`
  (16384) by the 2026-04-29 follow-up bump: applying the single-task
  `FR_THINK_OVERFLOW` evidence (qwen3.6:27b / nemotron-3-nano:30b at
  ctx=12288 hit overflow on 50% of `validate_problem` / `validate_plan`
  cells; nemotron later dropped 2026-04-30) to a chain step running the
  same task gives **worse** headroom,
  not better — chain step-3 think+output budget at ctx=12288 would be
  ~8K vs ~11K in single-task (the regime that already failed). Raising
  to 16384 brings chain step-3 to ~12K (comparable to the single-task
  16384 envelope) and chain step-4 to ~8–10K (still tighter; raise to
  20480 if a chain sweep surfaces step-4 overflow).
- **Per-task `num_predict` caps** (`pddl_eval/runner.py`
  `DEFAULT_NUM_PREDICT`): `solve=8192`, `validate_*=4096`,
  `simulate=4096`. Non-solve caps were raised from 1024/1536 → 4096 on
  2026-04-29 after the cluster-26042026 sweep showed truncation rates
  (`done_reason == "length"`) of 40.9% on `validate_plan`, 37.1% on
  `simulate`, 32.7% on `validate_problem`, and 17.4% on
  `validate_domain` at the old caps — thinking-mode reasoning and
  tool-call XML/harmony emissions were being cut mid-stream, biasing
  accuracy and producing the bulk of `ollama_parse_error` records (the
  Hermes/harmony XML parser fails on truncated `<function><parameter>`
  tags). Override per-run with `--num-predict N` (applies uniformly to
  all tasks).

The PR-2 abort gate that previously exited early for
`--conditions=no-tools|both` under `--think on/default` was lifted
2026-04-28 — thinking content is now captured separately
(`TaskResult.thinking`) so it does not contaminate the graded
response. See CHANGELOG 2026-04-28 (PR-2).

---

## 6. Domains

20 domains × 5 valid problems × (1 valid + 1 invalid) domain × (5 valid + 5 invalid) plans per problem = **1240 fixture files** (PR-3, 2026-04-29). Per-domain layout:

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

The 10 paper domains came from the paper dataset snapshot at `.local/pddl_mcp_dataset/` (Benyamin et al., 2025, Aug 2025). The 10 PR-3 domains were sourced from public benchmark suites and validated end-to-end by the build pipeline. Substitution rationale and per-domain caveats live in `development/FRAMEWORK_EXTENSION_PLAN.md` § "PR-3 drift from spec".

**Negative fixtures.** Each domain ships:
- `domain_neg.pddl` — joins `validate_domain` (negative arm) only
- `n01..n05.pddl` — join `validate_problem` (negative arm) only
- `p<NN>_b1..b5.plan` — join `validate_plan` (negative arm) for problem `pNN` only

Bug taxonomies (3 domain-mutators, 6 problem-mutators, 4 plan-mutators) are documented in `domains/README.md`. All negatives must validate as `valid=False` against `validate_pddl_syntax` — `generate_ground_truth` aborts startup with `SystemExit` naming any drift.

**Expected validity:** positives are expected to pass `domain_valid == problem_valid == plan_valid == solvable == True`. Each committed `p<NN>_v[1-5].plan` is independently re-validated at startup; any committed valid plan that the validator rejects also aborts startup (symmetric fail-fast on both sides).

**Plan diversity.** Classical domains achieve up to 3 distinct plans via Fast Downward search-strategy variants (`lazy_greedy_cea`, `astar_lmcut`, `lazy_greedy_ff`); numeric domains use ENHSP whose alternative search algorithms are limited, so v2..v5 may be duplicates of v1. The graded count remains 5 per problem; per-call grading robustness is preserved because each prompt variant grades the plan independently.

**Pairing convention (known limitation).** `validate_problem` and `validate_plan` negative jobs always pair the negative file with the *positive* counterparts of the other layers (the `validate_problem` negative uses positive `domain.pddl`; the `validate_plan` negative uses positive `domain.pddl` + the matching positive `pNN.pddl` for that `pNN_bK.plan`). The LLM never sees a filename — prompts interpolate content via `.format(domain=…, problem=…, plan=…)` — so this isn't a leak channel.

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
| failure_reasons | Dict of `FR_*` reason → count (open-ended; new buckets are additive). Notable: `FR_THINK_OVERFLOW` (PR-2, 2026-04-28) — thinking spiral consumed the completion budget leaving empty `content`; more specific than `FR_TRUNCATED_NO_ANSWER`. `FR_FORMAT_PARSE_FAIL` (PR-4, 2026-04-29) — no-PDDL-tools branch: both the `format=<json_schema>` parse and the free-text fallback (where applicable) failed to produce a usable artefact. Treated as a truncation-eligible failure (re-tagged to `FR_TRUNCATED_NO_ANSWER` when `done_reason == "length"`), so a cap-cut mid-JSON does not inflate the parse-fail rate. |

`chains` entries: model, with_tools, chain_length, samples, successes, success_rate, tool_filter, prompt_style, ci_lo, ci_hi, plus `samples_detail` — a per-sample list of `{idx, domain, problem, chain_tasks, step_records, final_success, exception}` (each `step_records[*]` carries `step_index, task, success, failure_reason, tool_calls_count, truncated, loop_exhausted`). Effective chain length per sample = `len(step_records)` (skipped no-plan steps are absent).

`meta` (present when `save_results` is called with metadata; written by `async_main`):
| Field | Description |
|-------|-------------|
| host | Where the run executed (`localhost`, RTX node hostname like `ise-cpu256-09:11434`, etc.). The legacy `is_remote` field was retired 2026-04-27 along with the cis-ollama path. |
| conditions | `tools`, `no-tools`, or `both` |
| models, tasks | CLI inputs that selected which models/tasks ran |
| num_variants, prompt_variants_active, num_ctx, num_ctx_thinking, num_ctx_chain, num_predict, temperature, think | Reproducibility knobs. `prompt_variants_active` records the actual variant indices used (e.g. `[0, 1, 2]` after the 2026-04-27 trim) — `num_variants` alone doesn't disambiguate which paraphrases ran. `num_ctx_thinking` (PR-2, 2026-04-28) is the bigger context budget used for `(think!=off, no-tools)` cells only; `async_main` splits `--conditions=both` into per-condition sub-passes when this applies, so `num_ctx` is constant within each `run_single_task_experiment` call. `num_ctx_chain` (added 2026-04-29, raised 12288 → 16384 same day) is the chain-step budget; held equal to `num_ctx` because chain prompts accumulate full per-step history, making the single-task think_overflow envelope tighter at chain step level rather than looser. `num_predict=null` means per-task defaults (`solve=8192, validate_*=4096, simulate=4096`); a number means a uniform CLI override. |
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

The full 4-model sweep on the BGU rtx GPUs:

```bash
# Full 4-model sweep packed in one rtx_pro_6000 job (Qwen3.5:0.8B,
# qwen3.6:27b, qwen3.6:35b, gemma4:31b — peak ~26 GB resident
# (gemma4:31b) under MAX_LOADED_MODELS=1, so weights swap rather
# than co-reside).
ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
  bash cluster-experimenting/submit_with_rtx.sh --all"

# Single-model run (e.g. iterating on one model)
bash cluster-experimenting/submit_with_rtx.sh qwen3.6:27b

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
| Models | Qwen3, GPT-OSS (various sizes) | Cluster sweep (post 2026-04-30 roster trim): `Qwen3.5:0.8B`, `qwen3.6:27b`, `qwen3.6:35b`, `gemma4:31b` (peak ~26 GB resident; rtx self-deploy on rtx_pro_6000:1 with `MAX_LOADED_MODELS=1`). Laptop default: `qwen3:0.6b`, `qwen3:4b` (paper-aligned). Roster history: `gpt-oss:120b` was substituted by `Qwen3.5:35b` in the large-model size band (2026-04-27); on 2026-04-29 `Qwen3.5:27b/35b` were updated to their `qwen3.6` successors and `gpt-oss:20b` was replaced by NVIDIA `nemotron-3-nano:30b` (hybrid Mamba+MoE+Attn) to preserve non-Qwen/Gemma family diversity and resolve gpt-oss's documented T=0 flakiness; on 2026-04-30 `nemotron-3-nano:30b` was dropped after smoke 17274424 confirmed deterministic Hermes XML parse failures on the same 4 cells across the 4096→6144 num_predict bump (failure is content-dependent, not budget-dependent). The cis-ollama fallback path was retired 2026-04-27 — rtx_pro_6000 self-deploy is the only cluster transport. |
| Domains | 10 IPC benchmarks | Same 10 IPC benchmarks (barman, blocksworld, depots, rovers, satellite, counters, depot, farmland, pogo_stick, sailing) — copied from the paper's published dataset |
| MCP integration | Claude Desktop plugins | Direct MCP stdio connections |
| Validator tool schema | pyvalidator-native shape (`details`, verbose `report` on both tools) | Plugin defaults unchanged (`verbose=True` returns full fidelity). The experiment bridge hides a `verbose` flag and pins it to `False`, projecting the response to `{valid, status, report}` for `validate_pddl_syntax` and `{valid, steps, trajectory}` for `get_state_transition`. |
| Simulate success criterion | Non-error tool result | Canonical-form trajectory deep-equality against oracle `gt["trace"]` on both with-tools and no-PDDL-tools paths via `_normalize_trajectory` (PR-4, 2026-04-29) — bridges oracle (`boolean_fluents: dict[str, bool]`) and model (`state.boolean: list[str]`) shapes to a sorted/lower-cased canonical form. A partial trajectory with `valid=false` is scored `FR_RESULT_MISMATCH`, not silent success. |
| No-tools task set | All 5 tasks scored | All 5 tasks scored under PR-4 (2026-04-29) with format-constrained sampling — `simulate` re-enabled alongside the shared `_normalize_trajectory` grader, replacing the keyword-check that ISS-002 originally dropped. The user-facing label changed to **no-PDDL-tools** to reflect that format constraint is still available; only PDDL-specific MCP tools (planner/validator/simulator) are removed. Internal `with_tools: bool` and JSON `condition: "no-tools"` field unchanged for back-compat. |
| No-tools grader | Free-text regex extractors (`extract_plan_lines`, `extract_verdict`, simulate keyword check) | Per-task Pydantic schema (`pddl_eval/schemas.py`) enforced via Ollama `format=<json_schema>` (PR-4, 2026-04-29). Free-text extractors retained as fallback for `solve` / `validate_*` when JSON parse fails; `simulate` has no fallback (parse failure → `FR_FORMAT_PARSE_FAIL`). Pre-PR-4 no-tools rows are NOT directly comparable to post-PR-4 no-PDDL-tools rows — the constraint narrows the response space and may regress tiny models that conflict with the schema; the new `FR_FORMAT_PARSE_FAIL` tag quantifies that rate per cell. |
| No-tools matrix | Crossed with all think modes + chains | Gated to `--think off` + single-task only. See §5. |

The key methodological addition is the separation of **tool selection** from **end-to-end success**, which reveals cases where models know which tool to use but fail to construct valid arguments.
