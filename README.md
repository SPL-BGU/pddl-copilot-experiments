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

- **Docker** running (MCP planning servers run in Docker)
- **Ollama** installed and running with desired models pulled
- **Python 3.10+**
- **pddl-copilot marketplace** cloned locally:
  ```bash
  git clone https://github.com/SPL-BGU/pddl-copilot.git
  ```

## Setup

```bash
# Pull models used in the paper
ollama pull qwen3:0.6b
ollama pull qwen3:4b

# Install dependencies
pip3 install -r requirements.txt
```

## Running (CLI)

```bash
cd ~/personal/pddl-copilot-experiments

./run_background.sh small   # quick, low-impact (qwen3:0.6b only)
./run_background.sh large   # heavier (qwen3:4b only) — overnight
./run_background.sh         # both models (full overnight run, default)
```

## What it does

- Activates `.venv` if present
- Auto-locates `pddl-copilot` as a sibling dir (or reads `$PDDL_MARKETPLACE_PATH`)
- Wraps with `caffeinate -i nice -n 19 nohup` so it survives terminal close, no sleep, low CPU priority
- Timestamps log + results directories so runs don't collide
- Prints PID + monitor commands

## Quick monitoring

After launch, the script prints exactly what you need:
```
Running in background, PID=12345
  Watch progress:  tail -f run_full_20260405_142301.log
  Check status:    ps -p 12345
  Stop:            kill 12345
```


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
| `--num-variants` | 5 | Prompt variants per task (paper uses 5) |
| `--temperature` | 0.0 | LLM sampling temperature |
| `--chains` | off | Also run multi-task chain evaluation |
| `--chain-samples` | 20 | Samples per chain length |
| `--seed` | 42 | Random seed for chain sampling |

## Running (Jupyter)

For interactive exploration:

```bash
pip3 install -r requirements.txt  # includes jupyter, matplotlib, pandas
jupyter notebook
```

- **`experiment_notebook.ipynb`** -- Run experiments interactively, modify parameters per cell
- **`analyze_results.ipynb`** -- Visualize results from `results/` (tables, bar charts, chain plots)

## Output

Results are saved as JSON in `results/`:

- `single_task_<timestamp>.json` -- Per-instance results with success, timing, tool calls
- `chain_<timestamp>.json` -- Chain evaluation success rates

## Domain Structure

```
domains/
  classical/<domain-name>/domain.pddl    # Domain definition
                          p01.pddl       # Problem instances
                          p02.pddl
  numeric/<domain-name>/domain.pddl
                        p01.pddl
```

This repo includes 3 sample domains (blocksworld, depots, counters). The paper evaluated 10 domains total -- full IPC benchmarks available from [downward-benchmarks](https://github.com/aibasel/downward-benchmarks).

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
