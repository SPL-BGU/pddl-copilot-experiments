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
(`cluster-experimenting/submit_with_rtx.sh`), which self-deploys a per-job
vLLM server on a `rtx_6000:1` (48 GB) or `rtx_pro_6000:1` (96 GB) node.
Local laptop runs are not supported — vLLM requires CUDA and the active
roster does not fit in consumer-GPU VRAM.

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
| `--marketplace-path` | `$PDDL_MARKETPLACE_PATH` | Path to pddl-copilot marketplace clone |
| `--llm-base-url` | `$LLM_BASE_URL` or `http://localhost:8000` | vLLM `/v1` base URL |
| `--models` | none (required) | Model tags from `cluster-experimenting/lib/defaults.sh:vllm_lookup` |
| `--tasks` | all 5 | Tasks to evaluate |
| `--domains-dir` | `./domains` | Path to benchmark domains |
| `--output-dir` | `./results` | Path to save result JSON files |
| `--num-variants` | 3 | First K of `ACTIVE_PROMPT_VARIANTS` (currently `(0, 1, 2)`). Paper used 5; the 26042026 sensitivity analysis showed v0/v1/v2 are within ~1pp of the 5-variant pooled mean. |
| `--temperature` | 0.0 | LLM sampling temperature |
| `--seed` | 42 | Random seed for `--smoke-shuffle` cell assignment |
| `--tool-filter` | `all` | `all` exposes every MCP tool (only active value). |
| `--prompt-style` | `minimal` | Only active value. |
| `--conditions` | `both` | Which conditions to run: `tools`, `no-tools`, or `both`. |
| `--num-predict` | per-task | Override max output tokens (solve=8192, validate_*=6144, simulate=6144). |
| `--num-ctx` | 16384 | Context window tokens for single-task tools cells. |
| `--num-ctx-thinking` | 16384 | Context tokens for single-task no-tools cells when `think!=off`. **Held equal to `--num-ctx`** so the "tools save tokens" headline isn't confounded by ctx asymmetry. |
| `--think` | `default` | Override thinking mode: `on`, `off`, or `default` (ablation only) |
| `--concurrency` | 4 | Max concurrent requests in single-task sweep. Pair with vLLM `--max-num-seqs ≥ concurrency`. |
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
# Full roster — submitted as a SLURM job array
# (one rtx_6000:1 GPU per (model, think, condition) cell)
bash cluster-experimenting/submit_with_rtx.sh --all

# Or per-model (e.g. when iterating on one model's behaviour)
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B

# Baseline-only no-tools sweep
bash cluster-experimenting/submit_with_rtx.sh --all --no-tools

# Inherit a partial run's trials.jsonl into the full sweep
bash cluster-experimenting/submit_with_rtx.sh --all --continue-partial /path/to/seed_dir
```

## Output

Results are saved as JSON under `results/`, bucketed by run scope (since 2026-05-04):

- `results/full/<run-tag>_<timestamp>_…/` — full sweeps
- `results/partial/<run-tag>_<timestamp>_…/` — fast feedback slice (`--partial K>0`)
- `results/smoke/{fixed,shuffle}_<sha>_<ts>/` — smoke runs (`--smoke`, `--smoke-shuffle`)

Per-run files:

- `single_task_<timestamp>.json` — per-instance results with success, timing, tool calls
- `summary_<timestamp>.json` — aggregated metrics with Wilson 95% confidence intervals
- `trials.jsonl` — append-only progress log used for resume and `--continue-partial`

`chain_<timestamp>.json` was emitted by the pre-2026-05-05 chain phase and is no longer produced by the active flow (see `development/CHANGELOG.md`). Pre-bucket runs (flat `results/<tag>_<ts>_…/` directories) are untouched and still parseable by the analyzer.

## Domain Structure

```
domains/
  classical/<domain-name>/domain.pddl    # Domain definition
                          p01.pddl       # Problem instance(s)
                          p01.plan       # Reference plan (manual cross-check)
  numeric/<domain-name>/domain.pddl
                        p01.pddl
                        p01.plan
```

This repo ships all 10 paper-aligned domains (5 classical: barman, blocksworld, depots, rovers, satellite; 5 numeric: counters, depot, farmland, pogo_stick, sailing). See `domains/README.md` for provenance.

## How It Works

1. **Ground truth**: Solve all problems using MCP planners as oracle
2. **With-tools condition**: Model gets MCP tool descriptions, can call planners/validators
3. **Without-tools condition**: Baseline -- model must answer from its own knowledge
4. **Success criteria**: Did the model call the correct tool (with-tools) or match ground truth (without-tools)?

## Citation

```bibtex
@article{benyamin2025pddlcopilot,
  title={Toward PDDL Planning Copilot},
  author={Benyamin, Omer and others},
  journal={arXiv preprint arXiv:2509.12987},
  year={2025}
}
```

## Origin
plugins implemented at [SPL-BGU/pddl-copilot](https://github.com/SPL-BGU/pddl-copilot). 
