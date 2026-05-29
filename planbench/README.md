# PlanBench arm

Runs the [PlanBench](https://github.com/karthikv792/LLMs-Planning) benchmark
(10 tasks × canonical Blocksworld / Logistics / Depots domains) against our
Ollama + vLLM model fleet, alongside the existing 5-task evaluation in
`run_experiment.py`.

**v1 = vanilla leaderboard only.** No MCP tools used during response
generation. The tool-using arm (LLM-Modulo style, per PlanBench
INTEGRATION.md §3) is tracked as ISS-022 and depends on two MCP plugin
extensions specified in
`../../pddl-copilot/specs-for-plan-bench.md` (sibling repo,
`planbench-integration` branch).

---

## Quick start (laptop)

```bash
# 1. Provision dependencies (clones LLMs-Planning + Fast Downward,
#    builds VAL, sets up a slim PlanBench venv). Idempotent.
bash planbench/setup.sh

# 2. Source the env exports it prints + activate the venv.
source <(bash planbench/setup.sh --print-env-only)
source external/LLMs-Planning/.venv/bin/activate

# 3. Smoke test (assumes a local Ollama with qwen3:0.6b loaded).
cd external/LLMs-Planning/plan-bench
python3 llm_plan_pipeline.py --task t1 --config blocksworld \
    --engine pddl_copilot__ollama__qwen3:0.6b \
    --specific_instances 1 2 3 --verbose True
```

After the smoke run, three JSON stages should exist:
- `external/LLMs-Planning/plan-bench/prompts/blocksworld/task_1_plan_generation.json`
- `external/LLMs-Planning/plan-bench/responses/blocksworld/pddl_copilot__ollama__qwen3:0.6b/task_1_plan_generation.json`
- `external/LLMs-Planning/plan-bench/results/blocksworld/pddl_copilot__ollama__qwen3:0.6b/task_1_plan_generation.json`

The third file contains per-instance `llm_correct` plus an aggregate accuracy.

---

## Engine name format

`pddl_copilot__<backend>__<model>`

- `<backend>` ∈ `{ollama, vllm}`
- `<model>` is the model tag, e.g. `qwen3:0.6b`. The double-underscore separator
  means colons inside model tags survive `.split('__')`.

Examples:
- `pddl_copilot__ollama__qwen3:0.6b`
- `pddl_copilot__ollama__gemma4:31b`
- `pddl_copilot__vllm__cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`

---

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `VAL` | VAL binary directory | `external/LLMs-Planning/planner_tools/VAL` |
| `PR2` | PR2 binary directory | `external/LLMs-Planning/planner_tools/PR2` |
| `FAST_DOWNWARD` | Fast Downward checkout | `external/downward` |
| `PLANBENCH_PATH` | LLMs-Planning checkout | `external/LLMs-Planning` |
| `PDDL_COPILOT_EXPERIMENTS_ROOT` | This repo root | auto-detected by the patch |
| `OPENAI_API_KEY` | PlanBench imports openai at module level; a stub is fine for our engine | `__planbench_stub__` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `VLLM_BASE` | vLLM `/v1` base URL | unset (required when backend=vllm) |
| `VLLM_API_KEY` | optional vLLM bearer token | unset |

`bash planbench/setup.sh --print-env-only` emits the full export block after
a successful setup.

---

## Cluster usage

```bash
ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
    bash planbench/setup.sh && \
    bash cluster-experimenting/submit_planbench.sh --models qwen3:0.6b qwen3:4b"
```

Sweep cells are `(task, config, model)`. Each model gets one sbatch that
loops the `task × config` matrix in-process to keep Ollama warm.

Per-run results land in `results/planbench/slurm_<model>_<jobid>/` (rsynced
from `external/LLMs-Planning/plan-bench/results/` post-run). The cluster-ops
`status.sh --bench planbench` surfaces the progress matrix.

---

## File layout

```
planbench/
├── __init__.py
├── engine.py             — sync Ollama + vLLM adapter exposed to PlanBench
├── setup.sh              — clone + build + patch (idempotent)
├── README.md             — this file
└── patches/
    ├── llm_utils.patch       — adds pddl_copilot__* dispatch in PlanBench
    └── utils_init.patch      — tolerate missing OPENAI_API_KEY at import
```

The cloned PlanBench tree lives at `external/LLMs-Planning/` and is gitignored
— every host runs `setup.sh` independently.

---

## What this does NOT change

- `pddl_eval/` — zero touches. Existing 5-task results in `results/` remain
  byte-comparable.
- `../pddl-copilot/plugins/` — zero touches. MCP plugin extensions needed for
  the v2 tool-using arm are tracked upstream on the `planbench-integration`
  branch of the sibling repo (see `specs-for-plan-bench.md`).
- MCP bridge contract (`MCPPlanner._PINNED_VERBOSE_FALSE` etc.) — unchanged.

See `development/CHANGELOG.md` (entry dated 2026-05-18) and
`EXPERIMENTS_FLOW.md` §13 for the full scope.
