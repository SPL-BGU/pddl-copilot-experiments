# Cluster-experimenting (BGU CIS)

SLURM sbatch scripts for running the `pddl-copilot-experiments` sweep on the
BGU CIS cluster (login node: `slurm.bgu.ac.il`). The cluster was rebranded
from "ISE-CS-DT" to "CIS" in the March 2026 user-guide refresh; hardware,
partitions, and GRES names are unchanged.

**Primary entrypoint: `submit_full_sweep.sh`.** Dispatches the 5-model
roster as three independent sbatch submissions (one SLURM job array each),
splitting by per-cell walltime:

| Pack                                | GPU class         | Per-cell time |
| ----------------------------------- | ----------------- | ------------- |
| `Qwen3.5:0.8B` + `4B` + `9B`        | `rtx_6000:1`      | 12 h          |
| `qwen3.6:35b`                       | `rtx_6000:1`      | 48 h          |
| `gemma4:26b-a4b`                    | `rtx_6000:1`      | 48 h          |

Each model contributes one cell per `(think_mode, condition)` combination
under the 2 × 3 matrix. Every array task allocates its own dedicated GPU
— no GPU sharing across cells; the small-Qwen pack and the 35B pack are
separate sbatch submissions only because they need different walltimes,
not because of GPU contention. Within each pack, cells fan out
concurrently subject to rtx_6000 (or rtx_pro_6000) pool capacity. The
single sbatch is `run_condition_vllm_rtx.sbatch`. `submit_full_sweep.sh`
is a thin orchestrator over `submit_with_rtx.sh`, which is the
lower-level wrapper.

Submission topology history:
- 2026-04-27 — cis-ollama (BGU shared-server) path retired along with
  CPU-only `submit_all.sh` waves and `submit_120b_cis.sh` shortcut.
- 2026-04-29 — `gpt-oss:120b` superseded by `qwen3.6:35b` (A3B MoE) in
  the large-model size band.
- 2026-04-30 — packed-job model retired in favour of per-cell SLURM job
  arrays; each cell is now an independent array task. See
  `development/CHANGELOG.md` for rationale.
- 2026-05-17 — `qwen3.6:27b` retired (slowest cell, ~19h tools×on);
  `Qwen3.5:4B` + `Qwen3.5:9B` added to fill the 0.8B → 35B-A3B param gap.
- 2026-05-18 — backend split LANDED: four Qwens (0.8B / 4B / 9B / 35B)
  on vLLM, `gemma4:31b` on Ollama. `submit_full_sweep.sh` became the
  new primary entrypoint, superseding `submit_with_resume.sh`.
- 2026-05-18 (same day) — backend split RETIRED via the gemma swap:
  `gemma4:31b` dense Ollama replaced with `gemma4:26b-a4b` MoE on vLLM
  (smoke 17638752). Full 5-model roster now single-backend on vLLM
  `rtx_6000:1`. `submit_with_resume.sh`'s Ollama branch is now empty
  (kept as the extension point in case a non-vLLM model rejoins).

## Quickstart

From the login node (`slurm.bgu.ac.il`):

```bash
# 1. Clone both repos under $HOME (siblings — the harness auto-locates the marketplace)
cd ~
git clone https://github.com/SPL-BGU/pddl-copilot-experiments.git
git clone https://github.com/SPL-BGU/pddl-copilot.git

# 2. Build conda env (pddl_copilot: py3.12 + openjdk17 + mcp + openai)
#    and pre-populate the two plugin .venvs. One-time, ~5 min.
bash ~/pddl-copilot-experiments/cluster-experimenting/setup_env.sh

# 3. Preflight (refreshes repos + venvs, surfaces GPU pool capacity).
bash .claude/skills/cluster-ops/scripts/preflight.sh

# 4. Smoke-test: submit ONE small/cheap no-tools cell first to catch env
#    issues before firing the rest. Finishes in ~15 min.
cd ~/pddl-copilot-experiments
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B --no-tools

# 5. If the smoke test finishes OK (exit 0, JSON written under results/),
#    submit the full sweep — three independent SLURM job arrays (small
#    Qwens, qwen3.6:35b, gemma4:26b-a4b) per the topology table above.
#    Each array task is one (model, think, cond) cell on its own dedicated
#    GPU and runs concurrently with siblings as the pool has capacity.
bash cluster-experimenting/submit_full_sweep.sh
```

Rerunning any step is safe: `git clone` can be replaced with `git -C <dir> pull`,
`setup_env.sh` detects an existing conda env and reuses it, and
`submit_with_rtx.sh` is idempotent. Resubmitting the same `(model, think,
cond)` cell — e.g. after a TIMEOUT — lands in the same
`results/slurm_<model>_<think>_<cond>/` dir and resumes from the
previously-completed trials via the `trials.jsonl` mechanism in
`run_experiment.py` (skip with `--no-resume`).

## Prereqs

1. **Cluster account** — request access via your SPL-BGU contact / IT.
2. **Both repos cloned under `$HOME` on the login node:**
   ```bash
   ssh <user>@slurm.bgu.ac.il
   cd ~
   git clone https://github.com/SPL-BGU/pddl-copilot-experiments.git
   git clone https://github.com/SPL-BGU/pddl-copilot.git
   ```

## One-time setup

From the login node:

```bash
bash ~/pddl-copilot-experiments/cluster-experimenting/setup_env.sh
```

This creates a conda env `pddl_copilot` with:
- Python 3.12 + `mcp` + `openai` (from `requirements.txt`)
- OpenJDK 17 (ENHSP needs a JVM — installed via conda-forge, no cluster module needed)
- Pre-populated `.venv`s for `pddl-solver` and `pddl-validator` plugins
  (avoids per-job `pip install` cost and avoids N parallel jobs racing on the same venv)

Override defaults with env vars:
```bash
ENV_NAME=my_env PYTHON_VERSION=3.11 bash cluster-experimenting/setup_env.sh
```

## Submission

The full production sweep is one command — `submit_full_sweep.sh` — which
fires the three backend/walltime-split sbatch submissions from the
topology table above. `submit_with_rtx.sh` is the per-backend lower-level
wrapper; use it directly for single-model pilots or one-off cells.

```bash
cd ~/pddl-copilot-experiments

# Full production sweep: 3 sbatch arrays (small Qwens × 18 cells,
# 35B × 6 cells, gemma4:26b-a4b × 6 cells = 30 cells total). Each
# array task runs on its own dedicated GPU; fan-out concurrent.
bash cluster-experimenting/submit_full_sweep.sh

# Preview the full-sweep dispatch without submitting.
bash cluster-experimenting/submit_full_sweep.sh --dry-run

# Baseline-only no-tools sweep (5 cells total, one per model).
bash cluster-experimenting/submit_full_sweep.sh --no-tools

# Single-model invocation via the lower-level wrapper (default GPU
# class is rtx_6000:1; --gpu-type rtx_pro_6000 is the opt-in escape).
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B

# Multi-model invocation (3 models × 6 = 18-cell array, each cell
# on its own rtx_6000:1 — no GPU packing across cells).
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B

# Preview the sbatch command without submitting.
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --dry-run
```

All invocations build a CELLS list and submit as a job array (or a single
sbatch when N=1). Multi-positional args are NOT packed into a single
sequential job — they fan out as independent array tasks, one per cell,
each with its own dedicated GPU allocation.

### GPU class

`submit_with_rtx.sh` defaults to `rtx_6000:1` (48 GB VRAM, `--mem=48G`)
— used by the full active roster. AWQ quants for `qwen3.6:35b` fit at
~83% VRAM and `gemma4:26b-a4b` at ~85% under
`gpu-memory-utilization=0.85`; the FP16 Qwens (0.8B/4B/9B) sit well
below.

`--gpu-type rtx_pro_6000` is the per-invocation escape hatch (96 GB
VRAM, `--mem=80G`) — use when the rtx_6000 pool is queue-saturated.
Pass either `rtx_pro_6000` or `rtx_6000`; everything else errors.

### `--no-tools` shorthand

`--no-tools` pins the run to the no-tools matrix:
- `CONDITIONS=no-tools` (one tools-off pass)
- `THINK_MODES=off` (no-tools/think=on is skipped by the matrix gate anyway)
- `TASKS=` runner default (all 5: solve, validate_domain, validate_problem,
  validate_plan, simulate). PR-4 re-enabled no-tools `simulate` via JSON-
  trajectory grading against the oracle (`SimulateResponse` schema in
  `pddl_eval/schemas.py`); the prior 4-task gate was retired in this fix.
  Negative fixtures (ISS-001) ride along the matching task automatically.
- Per-task wall: `--time=08:00:00`. Each model is one array task — no
  cross-model serialization, so adding models adds parallelism, not wall.

Conflicts with `--think-modes` (any value other than `off|default`) are
rejected.

### Resuming a TIMEOUT'd cell

Each cell writes `results/slurm_vllm_<model>_<think>_<cond>/trials.jsonl`
as it goes. Resubmitting `submit_with_rtx.sh <model> ...` for the same
cell after a TIMEOUT or `scancel` lands in the same dir and resumes from
`trials.jsonl` — only the in-flight trial is re-run. To start fresh, pass
`--no-resume` to `run_experiment.py` (the wrapper doesn't currently pipe
this through, so add the flag in the `python3 run_experiment.py …` line of
`run_condition_vllm_rtx.sbatch` for that submission). Cell-keyed dir
naming (no `$SLURM_JOBID` suffix) was added 2026-05-01 specifically so
resubmissions land in the same dir; pre-2026-05-01 dirs still aggregate
fine but each carries its own jobid.

### Models in the default sweep

The paper's `qwen3:0.6b` / `qwen3:4b` weren't a fit for the cluster's
original model inventory, so this cluster run is a paper-variant, not a
1:1 reproduction. The five active models, with their GPU class:

| Model            | GPU class         | Notes |
| ---------------- | ----------------- | ----- |
| `Qwen3.5:0.8B`   | `rtx_6000:1`      | FP16, ~1.6 GB weights |
| `Qwen3.5:4B`     | `rtx_6000:1`      | FP16, ~9 GB weights |
| `Qwen3.5:9B`     | `rtx_6000:1`      | FP16, ~18 GB weights |
| `qwen3.6:35b`    | `rtx_6000:1`      | AWQ-4bit MoE (~17 GB), A3B |
| `gemma4:26b-a4b` | `rtx_6000:1`      | AWQ-4bit MoE (~16 GB), A4B. Multimodal-aware; needs `MAX_NUM_BATCHED_TOKENS=4096`. |

Roster history: 2026-04-29 refresh updated `Qwen3.5:27b/35b` to their
`qwen3.6` successors (dense 27B / 35B-A3B MoE, both Apache-2.0, released
2026-04-{16,22}) and replaced `gpt-oss:20b` with NVIDIA
`nemotron-3-nano:30b` (hybrid Mamba+MoE+Attn) for non-Qwen/Gemma
diversity. 2026-04-30 dropped `nemotron-3-nano:30b` after smoke 17274424
confirmed deterministic Hermes XML parse failures on the same 4 cells
pre- and post-num_predict bump (4096→6144), establishing the failure as
content-dependent rather than budget-dependent. `gpt-oss:120b` was
previously substituted out by `Qwen3.5:35b` (2026-04-27) and is now
superseded by `qwen3.6:35b` in the large-model size band. 2026-05-17
dropped `qwen3.6:27b` (slowest cell in the sweep, ~19h tools×on) and
added `Qwen3.5:4B` + `Qwen3.5:9B` to fill the 0.8B → 35B-A3B param gap
with a dense, fast mid-band — same `qwen3_xml` parser family as the
rest of the Qwen3.5/3.6 lineup. 2026-05-18 moved the four Qwens to vLLM
in the production sweep (initially with `gemma4:31b` retained on
Ollama), then same-day retired the backend split by replacing
`gemma4:31b` dense Ollama with `gemma4:26b-a4b` MoE on vLLM (smoke
17638752 verified the gemma4 parser path + the multimodal-tower
`MAX_NUM_BATCHED_TOKENS=4096` requirement). Full roster now
single-backend on vLLM `rtx_6000:1`. The roster no longer carries a
non-Qwen/Gemma slot pending a viable replacement.

The legacy Ollama rtx path (`run_condition_rtx.sbatch`) was deleted
when the Ollama backend was retired (2026-05-23); archived
`slurm_gemma4_31b_*` corpora remain readable on disk for drift
comparison but cannot be re-run from this tree.

## Production vLLM sweep

Reuses the per-cell SLURM job array, matrix gate, Nice
auto-prioritization, and cell-keyed OUT_DIR shape; the single sbatch is
`run_condition_vllm_rtx.sbatch`.

### Scope (2026-05-18, backend unified)

Five-model vLLM scope: `Qwen3.5:0.8B` + `Qwen3.5:4B` + `Qwen3.5:9B` +
`qwen3.6:35b` + `gemma4:26b-a4b`. Qwen lineup shares `qwen3_xml`/`qwen3`
parsers (0.8B and 35B parser-verified on smokes 17468314 / 17494176;
4B/9B parser inherited from the shared family — dedicated smoke still
owed). `gemma4:26b-a4b` uses the `gemma4` tool-call parser with no
reasoning parser (Gemma has no `<think>` tokens) — verified on smoke
17638752 (2026-05-18) with `MAX_NUM_BATCHED_TOKENS=4096` (the model's
multimodal vision tower auto-loads and its per-MM-item budget exceeds
vLLM's default 2048-token batch ceiling). Prior 27B slot was retired
2026-05-17; the gemma4:31b dense Ollama slot was retired 2026-05-18.
The five vLLM cells each run on their own dedicated `rtx_6000:1`
allocation — `submit_full_sweep.sh` packs the three smaller Qwens
(0.8B/4B/9B) into one sbatch job array, 35B into a second sbatch, and
gemma4:26b-a4b into a third (separate walltimes), but within each array
every cell is one SLURM task with its own GPU; vLLM does not
cross-share a GPU between cells.

### Submit recipes

```bash
# Full production sweep — three sbatch arrays per the topology table
# (small/mid Qwens packed, qwen3.6:35b solo, gemma4:26b-a4b solo).
# See submit_full_sweep.sh for the exact per-pack walltime assignment.
bash cluster-experimenting/submit_full_sweep.sh

# Preview without submitting.
bash cluster-experimenting/submit_full_sweep.sh --dry-run

# One-cell pilot.
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --think-modes off
```

The wrapper rejects any model not in `PDDL_VLLM_VERIFIED_MODELS` before
SLURM pulls the slot. To add a model: verify its parser via
`submit_with_rtx.sh --smoke <model>` (one-cell smoke that exercises the
prod sbatch with `run_experiment.py --smoke`), then extend the array
constant in `lib/defaults.sh` AND the `vllm_lookup()` case in the same
file.

`submit_with_resume.sh` was the orchestrator for the historical
backend-split layout; post 2026-05-18 backend unification it functionally
just forwards to the vLLM submission.

### OUT_DIR namespace

Cells write to `results/slurm_vllm_<canonical_tag>_<think>_<cond>/`
(prefix `slurm_vllm_` retained from the era when it disambiguated vLLM
trials from the parallel Ollama corpora). The resume key in
`pddl_eval/runner.py:424` includes the `model` field as the HF id from
`vllm_lookup` (e.g. `Qwen/Qwen3.5-9B`).

### Resource profile

| Field | Default | rtx_pro_6000 (opt-in) |
|---|---|---|
| `--gpus` | `rtx_6000:1` (smoke-verified) | `rtx_pro_6000:1` |
| `--mem` | `48G` | `80G` |
| `--time` tools | `06:00:00` | — |
| `--time` no-tools | `05:00:00` | — |
| Concurrency | 4 (smoke-verified) | 4 |
| VRAM peak (27B AWQ, smoke) | 83% (40808/49140 MiB) | — |
| VRAM peak (35B AWQ MoE, smoke) | 84% (41328/49140 MiB) | — |

`--gpu-type rtx_pro_6000` escape hatch routes to the 96 GB class +
`--mem=80G` if rtx_6000 is queue-saturated.

## vLLM smoke probes (parser verification)

Post 2026-05-18 backend unification, vLLM is the production inference
backend (`run_condition_vllm_rtx.sbatch`). Parser verification is a
one-cell smoke exercised through the prod sbatch via
`submit_with_rtx.sh --smoke <model>` — the smoke fastpath added
2026-05-19 (commit `4f50a5b`) routes the `@smoke@` sentinel into
`run_experiment.py --smoke`. The dedicated
`run_smoke_vllm_vs_ollama.sbatch` was retired in commit `06f2b4b`
(2026-05-19); see `development/CHANGELOG.md` for the parser-verification
history.

### Per-model parser table (verified 2026-05-10 unless noted)

vLLM's `--tool-call-parser` regex must match the model's emit format. A
mismatch silently drops every tools-trial extraction → 0% tool-selection
with no startup error (we hit this on the original 27B AWQ probe). The
sbatch knob is `TOOL_CALL_PARSER` (env-overridable; default `qwen3_xml`).

| Tag              | HF id                                      | Quant                | TOOL_CALL_PARSER | GPU class               | Status                       |
| ---------------- | ------------------------------------------ | -------------------- | ---------------- | ----------------------- | ---------------------------- |
| `Qwen3.5:0.8B`   | `Qwen/Qwen3.5-0.8B`                        | FP16 (~1.6 GB)       | `qwen3_xml`      | rtx_6000:1              | **Verified** (job 17468314)  |
| `Qwen3.5:4B`     | `Qwen/Qwen3.5-4B`                          | FP16 (~9 GB)         | `qwen3_xml`      | rtx_6000:1              | Production-running 2026-05-18 (dedicated smoke still owed) |
| `Qwen3.5:9B`     | `Qwen/Qwen3.5-9B`                          | FP16 (~18 GB)        | `qwen3_xml`      | rtx_6000:1              | Production-running 2026-05-18 (dedicated smoke still owed) |
| `qwen3.6:35b`    | `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`        | AWQ-4bit MoE (~17 GB)| `qwen3_xml`      | rtx_6000:1              | **Verified** (job 17494176)  |
| `gemma4:26b-a4b` | `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`     | AWQ-4bit MoE A4B (~16 GB) | `gemma4`         | rtx_6000:1              | **Verified** (smoke 17638752, 2026-05-18). MM-aware → requires `MAX_NUM_BATCHED_TOKENS=4096` (exported by `vllm_lookup`). Replaced `gemma4:31b` dense Ollama. |

Retired 2026-05-17: `qwen3.6:27b` / `cyankiwi/Qwen3.6-27B-AWQ-INT4` —
slowest cell in the sweep (~19h tools×on on rtx_6000); replaced by
`Qwen3.5:4B` + `Qwen3.5:9B` in the param-ladder mid-band.

For vanilla Qwen3 sizes (e.g. `Qwen/Qwen3-0.6B`), use `TOOL_CALL_PARSER=hermes`
— vanilla Qwen3 emits Hermes JSON inside `<tool_call>`, not Llama-XML.

### Submit recipe

The smoke fastpath in `run_condition_vllm_rtx.sbatch` (2026-05-19,
commit `4f50a5b`) consumes the `@smoke@` sentinel and runs
`run_experiment.py --smoke` with the verified parser flags from
`vllm_lookup`. Use the wrapper rather than calling
`run_condition_vllm_rtx.sbatch` directly — it picks the right GPU,
mem, and time budget per model.

```bash
# One-cell smoke for any verified model.
bash cluster-experimenting/submit_with_rtx.sh --smoke Qwen3.5:9B
bash cluster-experimenting/submit_with_rtx.sh --smoke Qwen3.5:4B
bash cluster-experimenting/submit_with_rtx.sh --smoke gemma4:26b-a4b

# Override walltime if the default smoke window is wrong for a slow model
# (feedback_smoke_full_run_resources: smoke gets full-run resources).
bash cluster-experimenting/submit_with_rtx.sh --smoke --time 24:00:00 qwen3.6:35b
```

To add a NEW vLLM model: extend `PDDL_VLLM_VERIFIED_MODELS` AND the
`vllm_lookup()` case in `lib/defaults.sh`, then run the smoke recipe
above; the wrapper will refuse the tag until both edits are in place.

### Operational caveats

- **Stale `~/vllm.sif`.** The sbatch caches the apptainer SIF in `$HOME/vllm.sif`
  after first build. If `vllm-serve` rejects `--tool-call-parser <name>` at
  startup with "unknown tool-call-parser", the cached SIF predates that
  parser's addition: `rm ~/vllm.sif` and resubmit; the next run rebuilds
  from `docker://vllm/vllm-openai:latest`.
- **`max_tokens > max_model_len` HTTP 400.** vLLM rejects any request where
  `max_tokens > max_model_len` (harness per-task defaults are `solve=8192`,
  `validate_*=6144`, `simulate=6144`). When using `MAX_MODEL_LEN < 8192`,
  set `NUM_PREDICT=4096` (or any value safely below `MAX_MODEL_LEN`).
- **`ENFORCE_EAGER=1` on tight VRAM.** Skips CUDA graph capture+profiling
  (~1.5 GiB headroom) at ~10–15% throughput cost. Recipe: 27B AWQ on
  rtx_3090 24 GB → `MAX_MODEL_LEN=7168 GPU_MEM_UTIL=0.85 ENFORCE_EAGER=1
  NUM_PREDICT=4096`.

## Conditions and think modes

### Conditions (2 active) — looped inside every job
- `no-tools`                    — baseline, no MCP tools exposed
- `tools_all_minimal`           — tools on, filter=all, prompt=minimal

Each condition invokes `run_experiment.py` once, writing to its own output
subdir. Conditions inside a job are independent: a late-stage condition
failure doesn't lose earlier-condition results.

### Think modes
- `on`       — passes `think=True` (forwarded as vLLM `chat_template_kwargs.enable_thinking=True`).
- `off`      — passes `think=False` (fast path, no reasoning tokens).
- `default`  — omits the `think` kwarg so the model's native setting applies.
   Use this for models without a thinking switch (e.g. `gemma4*` historically;
   the rtx path now passes `on/off` to all models and lets the runtime ignore
   unsupported values).

The paper reports "better of with- and without-thinking"; running both
explicitly lets us reproduce that protocol systematically.

## Resource profile (`run_condition_vllm_rtx.sbatch`)

Per-array-task allocation. Each task = one (model, think, cond) cell.

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | rtx_6000 (and the rtx_pro_6000 opt-in) GRES are accessible from `main`. Mar-26 guide §High-Priority: never use a non-`main` partition without QoS rights. |
| `--gpus` | `rtx_6000:1` (default) or `rtx_pro_6000:1` (opt-in) | One dedicated GPU per array task; the cell's single model stays resident throughout |
| `--array` | `0-(N-1)` when N > 1 (no `%N` cap by default) | Fan-out unlimited — SLURM runs as many tasks as the pool has capacity for. Override with `%N` post-submit (`scontrol update JobId=<master> ArrayTaskThrottle=N`) if politeness is desired |
| `--time` | `06:00:00` (tools cells) / `05:00:00` (no-tools cells) / `03:00:00` (smoke); heavy MoE cells override to 48h via `submit_full_sweep.sh` | Per-cell budget; vLLM ~4× faster than the retired Ollama backend (smoke 2026-05-10) |
| `--mem` | `48G` (rtx_6000 default) / `80G` (rtx_pro_6000 opt-in) | IT cap 2026-04-27. With one model per task, peak host RAM is ~24 GB (qwen3.6:35b weight cache) — comfortably under either cap |
| `--tmp` | `50G` | Mar-26 guide §"SSD Drive". Reserves space on `/scratch/$USER/$JOBID`; covers vllm.sif (~5 GB) + one HF snapshot (~24 GB peak). The sbatch falls back to `/tmp/rtx-$JOBID` if `/scratch` isn't writable on the allocated node |
| `--cpus-per-task` | not set (cluster default `cpus-per-gpu`) | IT request 2026-04-27; explicit `12` was depriving other users |
| Concurrency | `4` | Pairs with vLLM `--max-num-seqs ≥ 4`; isolated per-task server so no cross-cell contention |

## Monitoring

```bash
squeue --me                                  # all my running/pending jobs
                                             # array tasks appear as <master>_<task>
sstat -j <jobid> --format=JobID,MaxRSS,MaxVMSize   # live memory usage (per task)
scontrol show job <jobid>                    # full job spec
scontrol show job <master>                   # array-master spec (counts queued/running tasks)

# Array task log (each task has its own .out)
tail -f cluster-experimenting/logs/pddl_rtx_<model>-<task_jid>.out

# Per-task vLLM server log on the compute node (under /scratch)
ssh <node> tail -f /scratch/$USER/<task_jid>/rtx-work/vllm-serve.log
```

After a job finishes:
```bash
sacct -j <jobid> --format=JobName,MaxRSS,AllocTRES,State,Elapsed,Start,ExitCode
sacct -j <master> --format=JobName,MaxRSS,State,Elapsed,Start,ExitCode  # all array tasks
```

The `cluster-ops` skill bundles operations helpers (status / sync /
preflight / postmortem) that wrap the SSH calls — see
`.claude/skills/cluster-ops/SKILL.md`. After syncing results, the
`analyzer` skill provides aggregation, plotting, master-table, and
drift-check recipes — see `.claude/skills/analyzer/SKILL.md`.

### Throttle a running array post-submission

To cap the number of simultaneously-running tasks of an already-submitted
array (e.g. cluster-IT politeness ask, or an array is starving other users):

```bash
scontrol update JobId=<master> ArrayTaskThrottle=2
```

To deprioritize the whole array without cancelling (Mar-26 guide §"Prioritize
Your Own Jobs"):

```bash
scontrol update JobId=<master> Nice=500
```

Higher Nice → lower priority. Default 0. Resets to 0 if you bump it back.

## Where things go

| Path | What |
|---|---|
| `results/slurm_<model>_<think>_<cond>/` | `run_experiment.py` JSON outputs for one cell (per-instance results, `summary_*.json`, `trials.jsonl`). Cell-keyed (no jobid suffix) post 2026-05-01 so resubmissions of the same cell land in the same dir and resume from the prior `trials.jsonl`; aggregators read either shape. Multiple resubmissions accumulate timestamped `single_task_*.json` / `summary_*.json` files; the latest summary wins on aggregation. `meta.host` reflects the latest run's compute node. `results/` is gitignored. |
| `cluster-experimenting/logs/pddl_rtx_<model>-<task_jid>.out` | rtx self-deploy log for one cell. The log filename keeps `<task_jid>` because `%x-%J.out` is resolved by SLURM at job-start, so each (re)submission gets its own log file. Directory is gitignored. |

## Fetching results locally

From your laptop:
```bash
# One cell's output (cell-keyed, no jobid suffix post 2026-05-01)
scp -r <user>@slurm.bgu.ac.il:~/pddl-copilot-experiments/results/slurm_qwen3_6_27b_off_tools_all_minimal \
       ~/personal/pddl-copilot-experiments/results/

# Everything from a run
rsync -av <user>@slurm.bgu.ac.il:~/pddl-copilot-experiments/results/slurm_* \
         ~/personal/pddl-copilot-experiments/results/
```

Analyze synced results ad-hoc against `results/**/{single_task,summary}_*.json` (legacy `chain_*.json` files from pre-2026-05-05 sweeps still parse but the active flow no longer emits them) — the canonical schema for those files is `save_results` in `pddl_eval/summary.py`. Recent analyses live in the contributor's `.local/reports/` (not committed).

## Cancelling jobs

```bash
scancel <task_jid>              # cancel one array task
scancel <master>                # cancel the whole array (master + all tasks)
scancel <master>_<task>         # cancel one task by array index
scancel -u $USER                # nuke all of mine
scancel -t PENDING -u $USER     # only pending
```

**Don't `scancel` a task in CG (completing) state.** It's already past the
workload and SLURM is just unwinding scratch dirs. A `scancel` during CG can
race the natural completion and abort late-cell results that would otherwise
have been written. Wait for it to clear naturally (verified 2026-04-29 on
smoke job 17263071, where a CG-state cancel lost the qwen3.6:35b warmup and
gemma cells).

**Do NOT use `scancel --name=pddl_*`** — verified 2026-04-25 on SLURM 25.11.4:
`--name` is exact-string match (comma-separated literal names), not a glob, so
the cancel is a silent no-op. Filter by name prefix with squeue → awk → xargs:

```bash
squeue --me -h -o '%i %j' | awk '$2 ~ /^pddl_rtx_/ {print $1}' | xargs --no-run-if-empty scancel
```

## Troubleshooting

**VRAM blowup after warmup (`exit 3`).** The runtime guard fired because
VRAM > 85% post-warmup. Check `run_condition_vllm_rtx.sbatch` —
`gpu-memory-utilization=0.85` and `num_ctx=16384` are sized for the
active roster on rtx_6000 48 GB. With one model per cell on its own GPU,
the guard fires per-cell. Note (2026-04-29): single-task `num_ctx` was
raised 8192 → 16384 (with `num_ctx_thinking` held equal at 16384 for
tools/no-tools fairness in the "tools save tokens" headline). If a sweep
trips the guard, post-mortem `sacct/MaxRSS` to right-size; lowering
`--num-ctx` or `--concurrency` is the fastest mitigation. The
chain-phase ctx knob (`--num-ctx-chain`) was retired 2026-05-05 with the
chain archive.

**`apptainer: command not found`.** Apptainer module not loaded on the
compute node. The sbatch assumes the cluster default has it on the PATH;
if not, add `module load apptainer` to the sbatch.

**Stale `~/vllm.sif`.** See the "Operational caveats" subsection above.

**`java: command not found` or `UnsupportedClassVersionError`.** The conda
env isn't active, or `openjdk=17` wasn't installed. Rerun `setup_env.sh`.

**Plugin `.venv` missing on first job.** `setup_env.sh` didn't run, or ran
from a different `$HOME`. Rerun it on the login node with the same user.

**First run on a given conda env is slow.** First `run_experiment.py`
invocation does MCP handshakes and vLLM server cold-starts per model.
Subsequent jobs on the same env reuse the cached plugin `.venv`s and the
cached `$HOME/vllm.sif`.
