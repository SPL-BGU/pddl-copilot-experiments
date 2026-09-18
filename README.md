# PDDL Copilot Experiments

Tests vLLM-served LLMs **with** and **without** MCP planning tools on 5 PDDL tasks:

| Task | Description |
|------|-------------|
| `solve` | Find a plan for a domain + problem |
| `validate_domain` | Check domain PDDL syntax |
| `validate_problem` | Check problem PDDL syntax |
| `validate_plan` | Verify a given plan is correct |
| `simulate` | Produce a state-transition trace |

## Quick navigation

- Cluster submission (supported reproduction path)? See `cluster-experimenting/README.md`.
- Methodology details? See `EXPERIMENTS_FLOW.md`.
- Analyzing results? See `.claude/skills/analyzer/SKILL.md`.
- Recent changes / open issues? See `development/CHANGELOG.md`, `development/OPEN_ISSUES.md`.
- What work is left? See `development/STATUS.md` (the single status file; `development/README.md` maps the rest).
- Quoting a result? Check `development/NUMBERS.md` first. It holds the frozen value of every headline figure.
- Which results are canonical? `results/sweep5v2-live` plus the anonymized sweep-6 corpus (`results/sweep6-live`; `CLAUDE.md` writes it as `*_sweep6`, after the run tag). `results/sweep5-cluster-20260530` is a stale partial mirror; do not read numbers from it.
- Two success layers exist: *tool-verified* (scored live by the harness) and *delivered* (the final answer re-graded offline by `tools/e2e_regrade.py`). See "How It Works" below and `EXPERIMENTS_FLOW.md` §14.
- Frontier (Claude API) runs use `tools/frontier_runner.py` and `tools/claude_api_batch.py`, not `run_experiment.py`.
- PlanBench arm? See `planbench/README.md`; its numbers are in `development/reference/planbench_wt_results_20260803.md`.
- The paper (`paper/`) targets JAIR, with TMLR as the fallback.

## Prerequisites

- **Python 3.10+**
- **Java 17+** (OpenJDK) — required by the `numeric_planner` tool (ENHSP runs on the JVM)
- **vLLM** OpenAI-compatible server (`/v1/chat/completions`) running locally or on the cluster, serving one of the verified models in `cluster-experimenting/lib/defaults.sh:vllm_lookup`
- **pddl-copilot marketplace** cloned locally:
  ```bash
  git clone https://github.com/SPL-BGU/pddl-copilot.git
  ```

## Setup

```bash
pip3 install -r requirements.txt
```

The supported reproduction path is the BGU CIS SLURM cluster
(`cluster-experimenting/submit_full_sweep.sh`), which dispatches the full
roster as SLURM job arrays and self-deploys per-job vLLM servers on
`rtx_6000:1` (48 GB) or `rtx_pro_6000:1` (96 GB) nodes. Local laptop runs
are not supported — vLLM requires CUDA and the active roster does not fit
in consumer-GPU VRAM.

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
| `--prompt-style` | `minimal` | Only active value. |
| `--conditions` | `both` | Which conditions to run: `tools`, `no-tools`, or `both`. |
| `--num-predict` | per-task | Override max output tokens (solve=8192, validate_*=6144, simulate=6144). |
| `--num-ctx` | 16384 | Context window tokens for single-task tools cells. |
| `--num-ctx-thinking` | 16384 | Context tokens for single-task no-tools cells when `think!=off`. **Held equal to `--num-ctx`** so the "tools save tokens" headline isn't confounded by ctx asymmetry. |
| `--think` | `default` | Override thinking mode: `on`, `off`, or `default` (ablation only) |
| `--decoupled-budget` | off | No-tools, `--think on` only. Splits each trial into two calls so reasoning and answer get separate token budgets. Produces a separate corpus; never pool it with a shared-budget run. |
| `--num-predict-think` | 8192 | Reasoning budget under `--decoupled-budget` |
| `--num-predict-answer` | per-task cap | Answer budget under `--decoupled-budget` |
| `--concurrency` | 4 | Max concurrent requests in single-task sweep. Pair with vLLM `--max-num-seqs ≥ concurrency`. |
| `--smoke` | off | Smoke slice: blocksworld `p01`, one variant, all 5 tasks, both conditions, think on and off |
| `--smoke-shuffle` | off | Like `--smoke`, but a random (domain, problem) per (model, task) cell, chosen with `--seed` |
| `--shard` | none | `i/N`: run only shard i of N. The hash leaves out the condition, so paired trials stay together. |
| `--no-resume` | off | Delete an existing `trials.jsonl` in the output dir and start fresh. By default completed trials are loaded and skipped. |
| `--partial` | `0` | If `K>0`, cap each domain to first-K positive + first-K negative fixtures. Fast feedback slice; resume-key shape unchanged so trials transfer to a follow-up full run. |
| `--continue-partial` | unset | Path to a prior run's `trials.jsonl` (or its parent dir). Seeds `--output-dir/trials.jsonl` before resume kicks in, so a follow-up full sweep inherits the partial's progress. Requires identical meta-dimensions; mismatched cells silently re-run. |

## Running (Cluster)

Paper-grade sweeps run on the BGU CIS SLURM cluster. See
`cluster-experimenting/README.md` for the full submission flow,
`.claude/skills/cluster-ops/SKILL.md` for monitoring helpers (status /
sync / preflight / postmortem), and `.claude/skills/analyzer/SKILL.md`
for results analysis (aggregate / plot / table / drift detection).

The active 5-model roster (post 2026-05-18 unification on vLLM) is
`Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`
— set in `cluster-experimenting/lib/defaults.sh`.

```bash
# Full roster — primary entrypoint, dispatches the per-cell SLURM array
bash cluster-experimenting/submit_full_sweep.sh

# Baseline-only no-tools sweep
bash cluster-experimenting/submit_full_sweep.sh --no-tools

# Per-cell wrapper (e.g. when iterating on one model's behaviour)
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B
```

## Output

Cluster jobs write one directory per (model, think mode, condition) cell:

- `results/slurm_vllm_<model>_<think>_<cond>[_<run-tag>]/`

A bare CLI run (no `--output-dir`) is auto-named into a bucket (since 2026-05-04):

- `results/full/<git-sha>_<timestamp>/` — full runs
- `results/partial/<git-sha>_<timestamp>/` — fast feedback slice (`--partial K>0`)
- `results/smoke/{fixed,shuffle}_<git-sha>_<timestamp>/` — smoke runs (`--smoke`, `--smoke-shuffle`)

Per-run files:

- `single_task_<timestamp>.json` — per-instance results with success, timing, tool calls
- `summary_<timestamp>.json` — aggregated metrics with Wilson 95% confidence intervals
- `trials.jsonl` — append-only progress log used for resume and `--continue-partial`

Pre-bucket runs (flat `results/<tag>_<ts>_…/` directories) and legacy `chain_<timestamp>.json` files from pre-2026-05-05 sweeps are untouched and ignored by the analyzer.

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

   Both are scored live from the tool result, which the paper calls the *tool-verified* layer. A second, offline pass (`tools/e2e_regrade.py`) grades the final answer the model actually delivered to the user, the *delivered* layer. The two can differ; see `EXPERIMENTS_FLOW.md` §14.

## Earlier version

This repository is the more-robust successor to our earlier, arXiv-only version of this
work; a new paper is in progress (see `paper/`). Until it appears, cite the earlier version:

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
