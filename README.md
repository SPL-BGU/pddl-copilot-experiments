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

## Quick navigation

- First time? Continue reading (Setup, Running (Background)).
- Free-tier GPU (Colab / Kaggle)? See `notebooks/run_single_model.ipynb`.
- Cluster submission? See `cluster-experimenting/README.md`.
- Methodology details? See `EXPERIMENTS_FLOW.md`.
- Analyzing results? See `.claude/skills/analyzer/SKILL.md`.
- Recent changes / open issues? See `development/CHANGELOG.md`, `development/OPEN_ISSUES.md`.

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
runs a different set (post 2026-04-30 roster trim): `Qwen3.5:0.8B`,
`qwen3.6:27b`, `qwen3.6:35b`, `gemma4:31b` — four models spanning the
paper's parameter range across two families (Qwen, Gemma). Since
2026-04-30 each `(model, think, condition)` cell runs as its own SLURM
array task on a dedicated `rtx_pro_6000:1` node (96 GB VRAM, peak
resident ~26 GB on `gemma4:31b`); cells run concurrently subject to
pool capacity, with no shared-server contention. See
`EXPERIMENTS_FLOW.md §11` for the full deviations table and
`development/CHANGELOG.md` for the roster history (including the
2026-04-30 nemotron-3-nano:30b drop after Hermes XML parse failures
proved content-dependent rather than budget-dependent).

## Running (Background)

```bash
cd ~/personal/pddl-copilot-experiments

./run_background.sh small              # quick, low-impact (qwen3:0.6b only)
./run_background.sh large              # heavier (qwen3:4b only) — overnight
./run_background.sh                    # both models (full overnight run, default)
./run_background.sh small-nothink      # qwen3:0.6b with --think off (ablation)
./run_background.sh large-nothink      # qwen3:4b with --think off (ablation)
./run_background.sh partial            # fast feedback slice: --partial 2 across all
                                       # domains, both models, single-task only;
                                       # output → results/partial/
./run_background.sh continue-partial PATH
                                       # full sweep that inherits PATH/trials.jsonl
                                       # from a prior partial run; only un-covered
                                       # cells re-execute. Output → results/full/
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
Running in background, PGID=12345
  Watch progress:  tail -f run_full_20260405_142301.log
  Check status:    ps -p 12345
  Stop:            kill -TERM -- -12345   # negative = whole process group (bash + python + MCP servers)
```

## Running (CLI)

Point `--marketplace-path` at your local pddl-copilot clone:

```bash
# Basic run (all 5 tasks, 2 default models)
python3 run_experiment.py --marketplace-path /path/to/pddl-copilot

# Specific models and tasks
python3 run_experiment.py --marketplace-path /path/to/pddl-copilot \
    --models qwen3:4b --tasks solve validate_plan
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
| `--seed` | 42 | Random seed for `--smoke-shuffle` cell assignment |
| `--tool-filter` | `all` | `all` exposes every MCP tool; `per-task` restricts per TASK_TOOLS allowlist |
| `--prompt-style` | `minimal` | Only active value as of 2026-04-27 — `guided` was retired (the 26042026 sweep showed style shifts results by ≤4pp per model, every CI crossed zero). The `_GUIDED_SUFFIX` constant and `WITH_TOOLS_SYSTEM["guided"]` entry are kept in `run_experiment.py` as documentation; re-enable by adding `"guided"` back to `PROMPT_STYLE_CHOICES`. |
| `--conditions` | `both` | Which conditions to run: `tools`, `no-tools`, or `both`. |
| `--num-predict` | per-task | Override max output tokens (solve=8192, validate_*=6144, simulate=6144). Non-solve caps were raised 1024/1536→4096 on 2026-04-29, then 4096→6144 on 2026-04-30. The 2026-04-30 bump's stated motivation (Hermes XML mid-tag truncation on nemotron-3-nano:30b) was falsified by smoke 17274424 — the 6144 cap is retained as harmless headroom. |
| `--num-ctx` | 16384 | Ollama context window tokens for single-task tools cells (raised from 8192 on 2026-04-29 after qwen3.6:27b smokes showed `think_overflow` at 12288; nemotron-3-nano:30b shared the evidence but was later dropped 2026-04-30). |
| `--num-ctx-thinking` | 16384 | Context tokens for single-task no-tools cells when `think!=off`. **Held equal to `--num-ctx`** so the "tools save tokens" headline isn't confounded by ctx asymmetry across tools/no-tools branches. |
| `--think` | `default` | Override thinking mode: `on`, `off`, or `default` (ablation only) |
| `--concurrency` | 4 | Max concurrent Ollama requests in single-task sweep |
| `--partial` | `0` | If `K>0`, cap each domain to first-K positive + first-K negative fixtures (and first-K valid + first-K invalid plans per kept positive). Fast feedback slice; resume-key shape unchanged so trials transfer to a follow-up full run. |
| `--continue-partial` | unset | Path to a prior run's `trials.jsonl` (or its parent dir). Seeds `--output-dir/trials.jsonl` before resume kicks in, so a follow-up full sweep inherits the partial's progress. Requires identical meta-dimensions (`tool_filter`, `prompt_style`, `think`, `conditions`); mismatched cells silently re-run. |

## Running (Cluster)

Paper-grade sweeps run on the BGU CIS SLURM cluster. See
`cluster-experimenting/README.md` for the full submission flow,
`.claude/skills/cluster-ops/SKILL.md` for monitoring helpers (status /
sync / preflight / postmortem), and `.claude/skills/analyzer/SKILL.md`
for results analysis (aggregate / plot / table / drift detection).

```bash
# Full 4-model sweep — submitted as a 20-task SLURM job array
# (4 models × 5 (think,cond) cells), one rtx_pro_6000:1 GPU per task
bash cluster-experimenting/submit_with_rtx.sh --all

# Or per-model (e.g. when iterating on one model's behaviour)
bash cluster-experimenting/submit_with_rtx.sh qwen3.6:27b

# Baseline-only no-tools sweep (one cell per model, 4-task array)
bash cluster-experimenting/submit_with_rtx.sh --all --no-tools

# Inherit a partial run's trials.jsonl into the full sweep
bash cluster-experimenting/submit_with_rtx.sh --all --continue-partial /path/to/seed_dir
```

## Output

Results are saved as JSON under `results/`, bucketed by run scope (since 2026-05-04):

- `results/full/<run-tag>_<timestamp>_…/` — full sweeps (`run_background.sh` `small`/`large`/`both`/`*-nothink`/`continue-partial`)
- `results/partial/<run-tag>_<timestamp>_…/` — fast feedback slice (`run_background.sh partial`, `--partial K>0`)
- `results/smoke/{fixed,shuffle}_<sha>_<ts>/` — smoke runs (`--smoke`, `--smoke-shuffle`)

Per-run files:

- `single_task_<timestamp>.json` — per-instance results with success, timing, tool calls
- `summary_<timestamp>.json` — aggregated metrics with Wilson 95% confidence intervals; `meta.partial=K` is recorded when `--partial K>0`
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
