# PlanBench arm

Runs the [PlanBench](https://github.com/karthikv792/LLMs-Planning) benchmark
(10 tasks × canonical Blocksworld / Logistics / Depots domains) against our
vLLM model fleet — the **same models, served the same way** as the existing
5-task evaluation in `run_experiment.py`, for corpus identity between the two
arms. The cluster sbatch self-deploys vLLM per job (Ollama backend retired
2026-05-18; the arm was migrated off it 2026-06-02 — see CHANGELOG).

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

# 3. Smoke test. Needs a vLLM server reachable at $VLLM_BASE. The laptop is
#    engine-smoke-only (no VAL/PR2/FD binaries on macOS); point VLLM_BASE at
#    any running OpenAI-compatible vLLM serving the model under its tag.
cd external/LLMs-Planning/plan-bench
export VLLM_BASE="http://localhost:8000/v1"
python3 llm_plan_pipeline.py --task t1 --config blocksworld \
    --engine pddl_copilot__vllm__Qwen3.5:0.8B \
    --specific_instances 2 3 4 --verbose True
```

The real validation surface is the cluster (`submit_planbench.sh --smoke`),
which self-deploys vLLM and runs the VAL evaluation stage. After a run, three
JSON stages should exist (engine name = `pddl_copilot__vllm__Qwen3.5:0.8B`):
- `external/LLMs-Planning/plan-bench/prompts/blocksworld/task_1_plan_generation.json`
- `external/LLMs-Planning/plan-bench/responses/blocksworld/pddl_copilot__vllm__Qwen3.5:0.8B/task_1_plan_generation.json`
- `external/LLMs-Planning/plan-bench/results/blocksworld/pddl_copilot__vllm__Qwen3.5:0.8B/task_1_plan_generation.json`

The third file contains per-instance `llm_correct` plus an aggregate accuracy.

---

## Engine name format

`pddl_copilot__<backend>__<model>`

- `<backend>` ∈ `{vllm, ollama}`. **vllm** is the active path; `ollama` is
  retained in `engine.py` for archaeology only (backend retired 2026-05-18).
- `<model>` is the canonical model tag, e.g. `Qwen3.5:0.8B`. The
  double-underscore separator means colons inside model tags survive
  `.split('__')`. For vLLM the tag must match the server's
  `--served-model-name`; `run_planbench_rtx.sbatch` sets that to the canonical
  tag (not the HF id) so the engine name — and PlanBench's results dir — stays
  slash-free.

Examples (active vLLM roster):
- `pddl_copilot__vllm__Qwen3.5:0.8B`
- `pddl_copilot__vllm__qwen3.6:35b`
- `pddl_copilot__vllm__gemma4:26b-a4b`

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
| `VLLM_BASE` | vLLM `/v1` base URL (active backend) | unset (required when backend=vllm) |
| `VLLM_API_KEY` | optional vLLM bearer token | unset |
| `PDDL_COPILOT_THINK` | `on`/`off`/`default` — toggles qwen3 thinking via `chat_template_kwargs.enable_thinking` | `off` (baselines are non-thinking) |
| `OLLAMA_HOST` | Ollama server URL (retired backend; archaeology only) | `http://localhost:11434` |

`bash planbench/setup.sh --print-env-only` emits the full export block after
a successful setup.

---

## Cluster usage

```bash
ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
    bash planbench/setup.sh && \
    bash cluster-experimenting/submit_planbench.sh --models Qwen3.5:0.8B Qwen3.5:4B"
```

Sweep cells are `(task, config, model)`. Each model gets one sbatch that
self-deploys vLLM and loops the `task × config` matrix in-process to keep the
server warm. Models must be in `PDDL_VLLM_VERIFIED_MODELS` (lib/defaults.sh).

Per-run results land in `results/planbench/slurm_<model>_<jobid>/` (rsynced
from `external/LLMs-Planning/plan-bench/results/` post-run). The cluster-ops
`status.sh --bench planbench` surfaces the progress matrix.

---

## File layout

```
planbench/
├── __init__.py
├── engine.py             — sync vLLM adapter exposed to PlanBench (active);
│                           retired Ollama branch kept for archaeology
├── setup.sh              — clone + build + patch + venv (idempotent)
├── apply_patches.py      — idempotent in-place edits to the LLMs-Planning
│                           tree: tolerate missing OPENAI_API_KEY, add the
│                           pddl_copilot__* dispatch, fix the upstream
│                           --specific_instances self-destructing filter
└── README.md             — this file
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

See `development/CHANGELOG.md` (entries dated 2026-05-18 and 2026-06-02) and
`EXPERIMENTS_FLOW.md` §13 for the full scope.
