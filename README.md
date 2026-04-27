# PDDL Copilot Experiments

Reproduction suite for the evaluation in [Benyamin et al., 2025 (arXiv:2509.12987)](https://arxiv.org/abs/2509.12987).

Tests Ollama LLMs **with** and **without** MCP planning tools on 5 PDDL tasks:

| Task | Description |
|------|-------------|
| `solve` | Find a plan for a domain + problem |
| `validate_domain` | Check domain PDDL syntax |
| `validate_problem` | Check problem PDDL syntax |
| `validate_plan` | Verify a given plan is correct |
| `simulate` | Produce a state-transition trace |

## Prerequisites

- **Python 3.10+**
- **Java 17+** (OpenJDK) — required by the `numeric_planner` tool (ENHSP runs on the JVM)
- **Ollama** installed and running with desired models pulled
- **pddl-copilot marketplace** cloned locally (v2.0.0 or later — pure pip, no Docker):
  ```bash
  git clone https://github.com/SPL-BGU/pddl-copilot.git
  ```

## Setup

```bash
# Pull models used in the paper (small enough to fit on a laptop GPU)
ollama pull qwen3:0.6b
ollama pull qwen3:4b

# Install dependencies
pip3 install -r requirements.txt
```

The paper-aligned `qwen3:0.6b` / `qwen3:4b` are the **laptop default**. The
**cluster sweep** (BGU rtx GPUs, see `cluster-experimenting/README.md`)
runs a different set: `Qwen3.5:0.8B`, `gpt-oss:20b`, `Qwen3.5:27b`,
`Qwen3.5:35b`, `gemma4:31b` — chosen because the paper tags aren't all
hosted on cis-ollama and the 5-model set spans the same parameter range
across three families while fitting on a single rtx_6000 (48 GB) GPU
under `MAX_LOADED_MODELS=1` sequencing. `gpt-oss:120b` can still be run
individually via `submit_with_rtx.sh gpt-oss:120b` (auto-routes to
rtx_pro_6000), but is no longer in the default `--all` sweep. See
`EXPERIMENTS_FLOW.md §11` for the full deviations table.

## Running (Background)

```bash
cd ~/personal/pddl-copilot-experiments

./run_background.sh small   # quick, low-impact (qwen3:0.6b only)
./run_background.sh large   # heavier (qwen3:4b only) — overnight
./run_background.sh         # both models (full overnight run, default)
```

What it does:
- Activates `.venv` if present
- Auto-locates `pddl-copilot` as a sibling dir (or reads `$PDDL_MARKETPLACE_PATH`)
- Wraps with `caffeinate -i nice -n 19 nohup` so it survives terminal close, no sleep, low CPU priority
- Loops over `tool_filter × prompt_style` combinations, each getting its own output directory
- Timestamps log + results directories so runs don't collide
- Prints PID + monitor commands

After launch, the script prints exactly what you need:
```
Running in background, PID=12345
  Watch progress:  tail -f run_full_20260405_142301.log
  Check status:    ps -p 12345
  Stop:            kill 12345
```

## Running (CLI)

Point `--marketplace-path` at your local pddl-copilot clone:

```bash
# Basic run (all 5 tasks, 2 default models)
python3 run_experiment.py --marketplace-path /path/to/pddl-copilot

# Specific models and tasks
python3 run_experiment.py --marketplace-path /path/to/pddl-copilot \
    --models qwen3:4b --tasks solve validate_plan

# Include multi-task chain evaluation
python3 run_experiment.py --marketplace-path /path/to/pddl-copilot \
    --models qwen3:4b --chains --chain-samples 20
```

Or set the environment variable to avoid repeating the path:

```bash
export PDDL_MARKETPLACE_PATH=/path/to/pddl-copilot
python3 run_experiment.py --models qwen3:0.6b qwen3:4b
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--marketplace-path` | `$PDDL_MARKETPLACE_PATH` | Path to pddl-copilot marketplace clone |
| `--models` | `qwen3:0.6b qwen3:4b` | Ollama model names to evaluate |
| `--tasks` | all 5 | Tasks to evaluate |
| `--domains-dir` | `./domains` | Path to benchmark domains |
| `--output-dir` | `./results` | Path to save result JSON files |
| `--num-variants` | 3 | First K of `ACTIVE_PROMPT_VARIANTS` (currently `(0, 1, 2)`). Capped at the tuple length; widen by editing `run_experiment.py`. Paper used 5; the 26042026 sensitivity analysis (`checkpoints/cluster-26042026/prompt_variant_stats.md`) showed v0/v1/v2 are within ~1pp of the 5-variant pooled mean. |
| `--temperature` | 0.0 | LLM sampling temperature |
| `--chains` | off | Also run multi-task chain evaluation |
| `--chain-samples` | 20 | Samples per chain length. The cluster sbatch (`cluster-experimenting/run_condition_rtx.sbatch`) overrides this to 100 for paper alignment. |
| `--seed` | 42 | Random seed for chain sampling |
| `--tool-filter` | `all` | `all` exposes every MCP tool; `per-task` restricts per TASK_TOOLS allowlist |
| `--prompt-style` | `minimal` | Only active value as of 2026-04-27 — `guided` was retired (the 26042026 sweep showed style shifts results by ≤4pp per model, every CI crossed zero). The `_GUIDED_SUFFIX` constant and `WITH_TOOLS_SYSTEM["guided"]` entry are kept in `run_experiment.py` as documentation; re-enable by adding `"guided"` back to `PROMPT_STYLE_CHOICES`. |
| `--num-predict` | per-task | Override max output tokens (solve=8192, simulate=1536, validate=1024) |
| `--num-ctx` | 8192 | Ollama context window tokens |
| `--think` | `default` | Override thinking mode: `on`, `off`, or `default` (ablation only) |
| `--concurrency` | 4 | Max concurrent Ollama requests in single-task sweep |

## Running (Cluster)

Paper-grade sweeps run on the BGU ISE-CS-DT SLURM cluster, not on a laptop.
Default path is `cluster-experimenting/submit_with_rtx.sh <model>` (one
job per model on a dedicated rtx_6000 / rtx_pro_6000 GPU; jobs queue in
parallel). See `cluster-experimenting/README.md` for the full submission
flow and `.claude/skills/cluster-ops/SKILL.md` for monitoring helpers.

```bash
# Full 5-model sweep packed in ONE job on rtx_6000
bash cluster-experimenting/submit_with_rtx.sh --all

# Or per-model (e.g. when iterating on one model's behaviour)
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b

# Baseline-only no-tools sweep (4-task discriminative matrix, packed in one job)
bash cluster-experimenting/submit_with_rtx.sh --all --no-tools
```

## Running (Jupyter)

For interactive exploration:

```bash
pip3 install -r requirements.txt  # includes jupyter, matplotlib, pandas
jupyter notebook
```

- **`experiment_notebook.ipynb`** -- Run experiments interactively, modify parameters per cell

## Output

Results are saved as JSON in `results/`:

- `single_task_<timestamp>.json` -- Per-instance results with success, timing, tool calls
- `chain_<timestamp>.json` -- Chain evaluation success rates
- `summary_<timestamp>.json` -- Aggregated metrics with Wilson 95% confidence intervals

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
5. **Chain evaluation**: Random sequences of n tasks; all must succeed for the chain to count

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
