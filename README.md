# PDDL Copilot Experiments

Tests vLLM-served LLMs **with** and **without** MCP planning tools on 5 PDDL tasks:

| Task | Description |
|------|-------------|
| `solve` | Find a plan for a domain + problem |
| `validate_domain` | Check domain PDDL syntax |
| `validate_problem` | Check problem PDDL syntax |
| `validate_plan` | Verify a given plan is correct |
| `simulate` | Produce a state-transition trace |

## What the paper asks, and which data answer it

The paper (`paper/`, ICAPS 2027 main track) asks three questions:

1. **RQ1.** Do the PDDL tools help the model on planning tasks?
2. **RQ2.** Does the model pick the right tool?
3. **RQ3.** Does the model use what the tool returns?

| Data | Folder | Used for |
|---|---|---|
| October rerun (three open models, thinking off, full answers stored) | `results/delivered-rerun` | RQ2, RQ3, and RQ1 on the three validation tasks |
| Matched run (same three models, no tools and tools in one job) | its own run tag; see `development/STATUS.md` | RQ1 on solve and simulate |
| May sweep (five models, thinking on and off, answers cut at 500 characters) | `results/sweep5v2-live`, `results/sweep6-live` | supplement |
| Corrected-prompt control, the pilots, the earlier Claude runs, PlanBench | see `development/reference/datasets_breakdown.md` | supplement |

These corpora are never pooled. The JSON-schema constraint that was meant for the
no-tools arm never took effect in any of them (`EXPERIMENTS_FLOW.md` §4.2).

## Quick navigation

- What work is left? See `development/STATUS.md` (the single status file) and `development/paper_outline.md` (the paper's outline). `development/README.md` maps the rest.
- Quoting a result? Check `development/NUMBERS.md` first. It holds the frozen value of every headline figure.
- How the test setup works (tasks, prompts, tool contract, output files)? See `EXPERIMENTS_FLOW.md`.
- Cluster submission? See `cluster-experimenting/README.md`.
- Analyzing results? See `.claude/skills/analyzer/SKILL.md`.
- Recent changes and open issues? See `development/CHANGELOG.md`, `development/OPEN_ISSUES.md`.
- Main-sweep numbers are checked against `results/sweep5v2-live` and `results/sweep6-live` only (`CLAUDE.md` writes the second as `*_sweep6`, after the run tag). Any other sweep folder is a sync mirror and gives wrong numbers; the old mirrors were moved out of the repo on 2026-10-10 (`development/MOVES.md`).
- Two success layers exist: *tool-verified* (scored live by the harness from the tool result) and *delivered* (the final answer the model handed back, graded offline). See "How It Works" below and `EXPERIMENTS_FLOW.md` §14.
- Frontier (Claude API) runs use `tools/frontier_runner.py` and `tools/claude_api_batch.py`, not `run_experiment.py`.
- PlanBench arm? See `planbench/README.md`; its numbers are in `development/reference/planbench_wt_results_20260803.md`.

## Prerequisites

- **Python 3.10+**
- **Java 17+** (OpenJDK): required by the `numeric_planner` tool (ENHSP runs on the JVM)
- **vLLM** OpenAI-compatible server (`/v1/chat/completions`) running locally or on the cluster, serving one of the verified models in `cluster-experimenting/lib/defaults.sh:vllm_lookup`
- **pddl-copilot marketplace** cloned locally:
  ```bash
  git clone https://github.com/SPL-BGU/pddl-copilot.git
  ```

## Setup

```bash
pip3 install -r requirements.txt
```

Runs go through the BGU CIS SLURM cluster
(`cluster-experimenting/submit_with_rtx.sh`). It submits SLURM job arrays,
and each array task starts its own vLLM server on an `rtx_6000:1` (48 GB) or
`rtx_pro_6000:1` (96 GB) node. Laptop runs are not supported: vLLM needs CUDA
and the models do not fit in consumer-GPU memory.

## Running (CLI)

Point `--marketplace-path` at your local pddl-copilot clone and
`--llm-base-url` at the vLLM server:

```bash
# Basic run (all 5 tasks)
python3 run_experiment.py \
    --marketplace-path /path/to/pddl-copilot \
    --llm-base-url http://localhost:8000 \
    --models Qwen3.5:0.8B

# Specific tasks
python3 run_experiment.py \
    --marketplace-path /path/to/pddl-copilot \
    --llm-base-url http://localhost:8000 \
    --models Qwen3.5:0.8B --tasks solve validate_plan
```

Or use the environment variables to avoid repeating flags:

```bash
export PDDL_MARKETPLACE_PATH=/path/to/pddl-copilot
export LLM_BASE_URL=http://localhost:8000
python3 run_experiment.py --models Qwen3.5:0.8B
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--marketplace-path` | `$PDDL_MARKETPLACE_PATH` | Path to pddl-copilot marketplace clone. Required unless the env var is set. |
| `--llm-base-url` | `$LLM_BASE_URL` or `http://localhost:8000` | vLLM `/v1` base URL |
| `--models` | optional; falls back to the original paper's `qwen3:0.6b qwen3:4b` | Model tags from `cluster-experimenting/lib/defaults.sh:vllm_lookup`. Neither fallback tag is in `vllm_lookup` today, so pass the models explicitly. |
| `--tasks` | all 5 | Tasks to evaluate |
| `--domains-dir` | `./domains` | Path to benchmark domains |
| `--domains` | all | Restrict to these domain directory names |
| `--problems` | all | Restrict to these problem stems (e.g. `p01`) within each selected domain |
| `--output-dir` | `./results` | Where to save results. Left at the default, the run is auto-named into a bucket (see Output). |
| `--num-variants` | 6 | First K of `ACTIVE_PROMPT_VARIANTS`, currently `(11, 12, 13, 14, 15, 16)`: v11–v13 neutral, v14–v16 steered. Must be in 1–6. Earlier sweeps used v5–v7 and v0–v2. |
| `--include-no-tools-steered` | off | Also run the steered variants (v14–v16) in no-tools cells. This is the control arm; without the flag those cells are skipped. |
| `--temperature` | 0.0 | LLM sampling temperature |
| `--seed` | 42 | Random seed for `--smoke-shuffle` cell assignment |
| `--tool-filter` | `all` | `all` exposes every MCP tool (only active value). |
| `--prompt-style` | `minimal` | With-tools system prompt. `minimal` is the per-task prompt that tells the model to use the tool. `neutral` keeps only the role sentence (used by the October rerun's Gemma neutral cell). |
| `--conditions` | `both` | Which conditions to run: `tools`, `no-tools`, or `both`. |
| `--num-predict` | per-task | Override max output tokens (solve=8192, validate_*=6144, simulate=6144). |
| `--num-ctx` | 16384 | Context window tokens. |
| `--num-ctx-thinking` | 16384 | Context tokens for no-tools cells when `think!=off`. Held equal to `--num-ctx` so both conditions get the same window. |
| `--think` | `default` | Override thinking mode: `on`, `off`, or `default` (ablation only) |
| `--decoupled-budget` | off | No-tools, `--think on` only. Splits each trial into two calls so reasoning and answer get separate token budgets. Produces a separate corpus; never pool it with a shared-budget run. |
| `--num-predict-think` | 8192 | Reasoning budget under `--decoupled-budget` |
| `--num-predict-answer` | per-task cap | Answer budget under `--decoupled-budget` |
| `--concurrency` | 4 | Max concurrent requests. Pair with vLLM `--max-num-seqs ≥ concurrency`. |
| `--smoke` | off | Smoke slice: blocksworld `p01`, one variant, all 5 tasks, both conditions, think on and off |
| `--smoke-shuffle` | off | Like `--smoke`, but a random (domain, problem) per (model, task) cell, chosen with `--seed` |
| `--shard` | none | `i/N`: run only shard i of N. The hash leaves out the condition, so paired trials stay together. |
| `--no-resume` | off | Delete an existing `trials.jsonl` in the output dir and start fresh. By default completed trials are loaded and skipped. |
| `--partial` | `0` | If `K>0`, cap each domain to first-K positive + first-K negative fixtures. Fast feedback slice; resume-key shape unchanged so trials transfer to a follow-up full run. |
| `--continue-partial` | unset | Path to a prior run's `trials.jsonl` (or its parent dir). Seeds `--output-dir/trials.jsonl` before resume kicks in, so a follow-up full sweep inherits the partial's progress. Requires identical meta-dimensions; mismatched cells silently re-run. |

Two environment variables change what the client sends. They are set by the
cluster wrapper, and only for the runs that register them:

- `$PDDL_NO_TOOLS_SYSTEM` (`no-pointer` or `format-stated`) replaces the no-tools
  system message on solve and simulate with a text from
  `pddl_eval/control_prompts.py`. Unset, the registered message is sent.
- `$PDDL_JSON_CONSTRAINT=structured_outputs` makes the no-tools JSON schema
  take effect (the JSON constraint pilot only). Unset, the schema is sent as
  `guided_json`, which vLLM 0.20.2 ignores.

## Running (Cluster)

All runs for the paper were made on the BGU CIS SLURM cluster. See
`cluster-experimenting/README.md` for the submission flow,
`.claude/skills/cluster-ops/SKILL.md` for monitoring helpers (status, sync,
preflight, postmortem), and `.claude/skills/analyzer/SKILL.md` for the
main-sweep analysis scripts.

`submit_with_rtx.sh` is the one submit script. The October rerun, the control
and the matched run each used it with a run tag of their own:

```bash
# Tools arm of three models, thinking off, under its own run tag
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b \
    --tools-only --think-modes off --run-tag <tag>

# No-tools cells on solve and simulate with a chosen system message, plus the
# with-tools cell in the same job (the matched run's layout)
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b \
    --no-tools --think-modes off --tasks "solve simulate" \
    --no-tools-system "format-stated" --with-tools-cell --run-tag <tag>
```

`--run-tag` gives the cells their own results folders. `--tasks` limits the
tasks. `--no-tools-system` picks the no-tools system message on solve and
simulate. `--with-tools-cell` adds the with-tools cell to such a job. The exact
command of each registered run is in its registration under
`development/reference/`.

`submit_full_sweep.sh` is how the May sweep was submitted: the five models
(`Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`,
set in `cluster-experimenting/lib/defaults.sh`), thinking on and off, both
conditions.

```bash
bash cluster-experimenting/submit_full_sweep.sh --dry-run   # preview the May sweep's layout
```

## Output

Cluster jobs write one directory per (model, think mode, condition) cell:

- `results/slurm_vllm_<model>_<think>_<cond>[_<run-tag>]/`

A bare CLI run (no `--output-dir`) is auto-named into a bucket (since 2026-05-04):

- `results/full/<git-sha>_<timestamp>/`: full runs
- `results/partial/<git-sha>_<timestamp>/`: fast feedback slice (`--partial K>0`)
- `results/smoke/{fixed,shuffle}_<git-sha>_<timestamp>/`: smoke runs (`--smoke`, `--smoke-shuffle`)

Per-run files:

- `single_task_<timestamp>.json`: per-instance results with success, timing, tool calls
- `summary_<timestamp>.json`: aggregated metrics with Wilson 95% confidence intervals
- `trials.jsonl`: append-only progress log used for resume and `--continue-partial`

## Domain Structure

```
domains/{classical,numeric}/<domain-name>/
  domain.pddl                  # valid domain
  domain_neg.pddl              # invalid domain (negative fixture)
  p01.pddl ... p05.pddl        # valid problems
  n01.pddl ... n05.pddl        # invalid problems
  pNN_v1.plan ... pNN_v5.plan  # 5 valid plans per problem
  pNN_b1.plan ... pNN_b5.plan  # 5 invalid plans per problem
```

This repo ships 20 domains: 10 classical and 10 numeric. Ten of them (5 + 5) are the original paper's domains; the other ten were added later. See `EXPERIMENTS_FLOW.md` §6 for the list and `domains/README.md` for provenance and the negative-fixture bug types.

## How It Works

1. **Ground truth**: Solve all problems using MCP planners as oracle
2. **With-tools condition**: Model gets MCP tool descriptions, can call planners/validators
3. **Without-tools condition**: Baseline -- model must answer from its own knowledge
4. **Success criteria**: two metrics, reported separately.
   - With tools: `tool_selected` (did the model call the correct tool?) and `success` (was the tool's result correct against ground truth?).
   - Without tools: `success` (does the model's own answer match ground truth?).

   Both are scored live from the tool result, which the paper calls the *tool-verified* layer. The *delivered* layer grades the final answer the model handed back to the user, offline. For the October rerun this is the frozen package `tools/delivered_rerun/`; for the control it is `tools/reanalysis/control_prompt_fix.py`. `tools/e2e_regrade.py` is the overlay used for the May sweep and the Claude runs. The two layers can differ; see `EXPERIMENTS_FLOW.md` §14.

## Earlier version

This repository is the successor to our earlier, arXiv-only version of this
work. A new paper is in progress (see `paper/`). Until it appears, cite the earlier version:

```bibtex
@misc{benyamin2025pddlcopilot,
  title         = {Toward PDDL Planning Copilot},
  author        = {Benyamin, Yarin and Mordoch, Argaman and Shperberg, Shahaf S. and Stern, Roni},
  year          = {2025},
  eprint        = {2509.12987},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI}
}
```

## Origin
plugins implemented at [SPL-BGU/pddl-copilot](https://github.com/SPL-BGU/pddl-copilot). 
