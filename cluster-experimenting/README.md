# Cluster-experimenting (BGU CIS)

SLURM sbatch scripts for running the `pddl-copilot-experiments` sweep on the
BGU CIS cluster (login node: `slurm.bgu.ac.il`). The cluster was rebranded
from "ISE-CS-DT" to "CIS" in the March 2026 user-guide refresh; hardware,
partitions, and GRES names are unchanged.

**Single submit path: `submit_with_rtx.sh` → `run_condition_rtx.sbatch`.**
The wrapper builds a list of `(model, think_mode, condition)` cells with
the matrix-gate filter applied, then submits a SLURM **job array** with
one task per cell. Each task allocates its own dedicated `rtx_pro_6000:1`
GPU (96 GB VRAM, `--mem=80G`, `--tmp=50G`), runs an isolated Apptainer
Ollama server on the compute node, and runs that single cell to
completion. No shared-server contention, no `afterok` chain — every
task is self-contained on its own GPU node and runs concurrently with
the other tasks (subject to pool capacity).

Submission topology history:
- 2026-04-27 — cis-ollama (BGU shared-server) path retired along with
  CPU-only `submit_all.sh` waves and `submit_120b_cis.sh` shortcut.
- 2026-04-29 — `gpt-oss:120b` superseded by `qwen3.6:35b` (A3B MoE) in
  the large-model size band.
- 2026-04-30 — packed-job model retired in favour of per-cell SLURM job
  arrays; each cell is now an independent array task. See
  `development/CHANGELOG.md` for rationale.

## Quickstart

From the login node (`slurm.bgu.ac.il`):

```bash
# 1. Clone both repos under $HOME (siblings — the harness auto-locates the marketplace)
cd ~
git clone https://github.com/SPL-BGU/pddl-copilot-experiments.git
git clone https://github.com/SPL-BGU/pddl-copilot.git

# 2. Build conda env (pddl_copilot: py3.12 + openjdk17 + mcp + ollama)
#    and pre-populate the two plugin .venvs. One-time, ~5 min.
bash ~/pddl-copilot-experiments/cluster-experimenting/setup_env.sh

# 3. Preflight (refreshes repos + venvs, surfaces GPU pool capacity).
bash .claude/skills/cluster-ops/scripts/preflight.sh

# 4. Smoke-test: submit ONE small/cheap no-tools job first to catch env or
#    Ollama-warmup issues before firing the rest. Finishes in ~15 min.
cd ~/pddl-copilot-experiments
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B --no-tools

# 5. If the smoke test finishes OK (exit 0, JSON written under results/),
#    submit the full sweep as a 20-task SLURM array on rtx_pro_6000. Each
#    task is one (model, think, cond) cell on its own GPU; tasks run
#    concurrently as the pool has capacity. Wall ~8h max-of-cell vs prior
#    ~6d packed model.
bash cluster-experimenting/submit_with_rtx.sh --all
```

Rerunning any step is safe: `git clone` can be replaced with `git -C <dir> pull`,
`setup_env.sh` detects an existing conda env and reuses it, and
`submit_with_rtx.sh` is idempotent. Resubmitting the same `(model, think,
cond)` cell — e.g. after a TIMEOUT — lands in the same
`results/slurm_<model>_<think>_<cond>/` dir and resumes from the
previously-completed trials via the `trials.jsonl` mechanism in
`run_experiment.py` (skip with `--no-resume`).

## Why a dedicated cluster setup (vs. just `run_background.sh`)

`run_background.sh` is laptop/macOS oriented: it wraps everything in `nohup` +
`caffeinate` and fires up a local `ollama serve`. On a SLURM compute node
none of that applies — the sbatch process *is* the background job,
`caffeinate` is macOS-only, and compute nodes don't have Ollama installed.
The cluster path stands up an isolated Apptainer Ollama on the compute
node and lets SLURM manage the job lifecycle.

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
- Python 3.12 + `mcp` + `ollama` (from `requirements.txt`)
- OpenJDK 17 (ENHSP needs a JVM — installed via conda-forge, no cluster module needed)
- Pre-populated `.venv`s for `pddl-solver` and `pddl-validator` plugins
  (avoids per-job `pip install` cost and avoids N parallel jobs racing on the same venv)

Override defaults with env vars:
```bash
ENV_NAME=my_env PYTHON_VERSION=3.11 bash cluster-experimenting/setup_env.sh
```

## Submission

```bash
cd ~/pddl-copilot-experiments

# Default: 20-task SLURM array on rtx_pro_6000:1, one task per cell.
# Cells = 5 models × {on, off} × {no-tools, tools_per-task_minimal,
# tools_all_minimal} = 5 × 6 = 30 cells (post 2026-05-12 matrix-gate lift).
# Per-task --time=12h; concurrent fan-out unlimited.
bash cluster-experimenting/submit_with_rtx.sh --all

# Single-model invocation (6-cell array under defaults):
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B

# Multi-model invocation (3 models × 6 = 18-cell array):
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B

# Baseline-only no-tools sweep (5-cell array, one cell per model).
# --time=08:00:00 per task.
bash cluster-experimenting/submit_with_rtx.sh --all --no-tools

# Preview the sbatch command without submitting.
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --dry-run
```

All invocations build a CELLS list and submit as a job array (or a single
sbatch when N=1). Multi-positional args are NOT packed into a single
sequential job — they fan out as independent array tasks, one per cell.

### GPU class

Default: `rtx_pro_6000:1` (96 GB VRAM, `--mem=80G`). Hard-pinned as the
sole self-deploy GPU class so peak VRAM and host RAM are constant across
the sweep. The 4-model pack peaks at `qwen3.6:35b` A3B MoE (~24 GB), well
inside 96 GB, leaving ample headroom for KV cache scaling.

`--gpu-type rtx_6000` is the opt-in escape hatch (48 GB VRAM, `--mem=48G`)
for use only when `rtx_pro_6000` is queue-saturated and the requested
models all fit. Default behaviour locks to `rtx_pro_6000` with no
auto-detection.

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

Each cell writes `results/slurm_<model>_<think>_<cond>/trials.jsonl` as it
goes. Resubmitting `submit_with_rtx.sh <model> ...` for the same cell after
a TIMEOUT or `scancel` lands in the same dir and resumes from
`trials.jsonl` — only the in-flight trial is re-run. To start fresh, pass
`--no-resume` to `run_experiment.py` (the wrapper doesn't currently pipe
this through, so add the flag in the `python3 run_experiment.py …` line of
`run_condition_rtx.sbatch` for that submission). Cell-keyed dir naming
(no `$SLURM_JOBID` suffix) was added 2026-05-01 specifically so
resubmissions land in the same dir; pre-2026-05-01 dirs still aggregate
fine but each carries its own jobid.

### Models in the default sweep

The paper's `qwen3:0.6b` / `qwen3:4b` weren't a fit for the cluster's
historical Ollama-on-cluster inventory, so this cluster run is a
paper-variant, not a 1:1 reproduction. The five active models in the
default `--all` pack — `Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`,
`qwen3.6:35b`, `gemma4:31b` — peak at ~26 GB resident on rtx_pro_6000
under `MAX_LOADED_MODELS=1` and sequence through one packed job.
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
rest of the Qwen3.5/3.6 lineup. The roster no longer carries a
non-Qwen/Gemma slot pending a viable replacement.

The rtx path pulls model weights from the public Ollama registry
(`docker://ollama/ollama` + `ollama pull`), so the model name has to be
valid there. The `.sif` container is cached at `$HOME/ollama.sif` after
the first run (~3 min cold).

## Production vLLM sweep (`--backend vllm`)

The vLLM analog of the Ollama production sbatch, landed 2026-05-11 (see
`development/CHANGELOG.md`). Reuses the per-cell SLURM job array, matrix
gate, Nice auto-prioritization, and cell-keyed OUT_DIR shape from
`submit_with_rtx.sh` — the new flag picks `run_condition_vllm_rtx.sbatch`
in place of the Ollama sbatch.

### Scope (2026-05-17)

Four-model vLLM scope: `Qwen3.5:0.8B` + `Qwen3.5:4B` + `Qwen3.5:9B` +
`qwen3.6:35b` (all share `qwen3_xml`/`qwen3` parsers; 0.8B and 35B
parser-verified on smokes 17468314 / 17494176; 4B/9B added 2026-05-17
and need smoke verification before promotion — see
`run_smoke_vllm_vs_ollama.sbatch`). `gemma4:31b` stays on Ollama — the
gemma4 parser hasn't been verified at the vLLM smoke level. Prior 27B
slot was retired 2026-05-17 (slowest cell at ~19h tools×on).

### Submit recipes

```bash
# Both backends in one go: Ollama array (gemma4:31b + qwen3.6:35b, resume
# existing trials.jsonl) + vLLM array (PDDL_VLLM_VERIFIED_MODELS — currently
# Qwen3.5:0.8B/4B/9B + qwen3.6:35b, fresh slurm_vllm_ corpora).
bash cluster-experimenting/submit_with_resume.sh

# Preview without submitting.
bash cluster-experimenting/submit_with_resume.sh --dry-run

# vLLM-only invocation (e.g. one-cell pilot).
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --backend vllm --think-modes off
```

The vLLM wrapper rejects any model not in `PDDL_VLLM_VERIFIED_MODELS`
before SLURM pulls the slot. To add a model: verify its parser via
`run_smoke_vllm_vs_ollama.sbatch`, then extend both the array constant
in `submit_with_rtx.sh` AND the `vllm_lookup()` case in
`run_condition_vllm_rtx.sbatch`.

### OUT_DIR namespace

vLLM cells write to `results/slurm_vllm_<canonical_tag>_<think>_<cond>/`
(prefix `slurm_vllm_`), not the Ollama `slurm_<canonical_tag>_*/`. The
resume key in `pddl_eval/runner.py:424` includes the `model` field as a
literal string — Ollama emits `Qwen3.5:9B`, vLLM emits the HF id from
`vllm_lookup` (e.g. `Qwen/Qwen3.5-9B`), so commingling both backends'
trials in one trials.jsonl would silently re-run every cell from zero.
`meta.inference_backend` is also recorded (commit 3044258).

### Resource profile

| Field | vLLM (default) | Ollama (default) |
|---|---|---|
| `--gpus` | `rtx_6000:1` (smoke-verified) | `rtx_pro_6000:1` |
| `--mem` | `48G` | `80G` |
| `--time` tools | `06:00:00` | `72:00:00` |
| `--time` no-tools | `05:00:00` | `08:00:00` |
| Concurrency | 4 (smoke-verified) | 4 |
| VRAM peak (27B AWQ, smoke) | 83% (40808/49140 MiB) | — |
| VRAM peak (35B AWQ MoE, smoke) | 84% (41328/49140 MiB) | — |

`--gpu-type rtx_pro_6000` escape hatch routes vLLM to the 96 GB class
+ `--mem=80G` if rtx_6000 is queue-saturated.

## vLLM smoke probes (parser verification)

The Ollama production sweep is the canonical path; vLLM is an opt-in
inference backend exercised through `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`.
A vLLM analog of `run_condition_rtx.sbatch` for the **full sweep** is
**not yet built** — see the 2026-05-09 / 2026-05-10 entries in
`development/CHANGELOG.md` for the open-pending list.

### Per-model parser table (verified 2026-05-10 unless noted)

vLLM's `--tool-call-parser` regex must match the model's emit format. A
mismatch silently drops every tools-trial extraction → 0% tool-selection
with no startup error (we hit this on the original 27B AWQ probe). The
sbatch knob is `TOOL_CALL_PARSER` (env-overridable; default `qwen3_xml`).

| Ollama tag       | HF id                                      | Quant                | TOOL_CALL_PARSER | GPU class               | Status                       |
| ---------------- | ------------------------------------------ | -------------------- | ---------------- | ----------------------- | ---------------------------- |
| `Qwen3.5:0.8B`   | `Qwen/Qwen3.5-0.8B`                        | FP16 (~1.6 GB)       | `qwen3_xml`      | rtx_6000:1              | **Verified** (job 17468314)  |
| `Qwen3.5:4B`     | `Qwen/Qwen3.5-4B`                          | FP16 (~9 GB)         | `qwen3_xml`      | rtx_6000:1              | Pending verify (2026-05-17)  |
| `Qwen3.5:9B`     | `Qwen/Qwen3.5-9B`                          | FP16 (~18 GB)        | `qwen3_xml`      | rtx_6000:1              | Pending verify (2026-05-17)  |
| `qwen3.6:35b`    | `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`        | AWQ-4bit MoE (~17 GB)| `qwen3_xml`      | rtx_6000:1              | **Verified** (job 17494176)  |
| `gemma4:31b`     | `cyankiwi/gemma-4-31B-it-AWQ-4bit`         | AWQ-4bit (~16 GB)    | `gemma4`         | rtx_6000:1              | Pending verify               |

Retired 2026-05-17: `qwen3.6:27b` / `cyankiwi/Qwen3.6-27B-AWQ-INT4` —
slowest cell in the sweep (~19h tools×on on rtx_6000); replaced by
`Qwen3.5:4B` + `Qwen3.5:9B` in the param-ladder mid-band.

For vanilla Qwen3 sizes (e.g. `Qwen/Qwen3-0.6B`), use `TOOL_CALL_PARSER=hermes`
— vanilla Qwen3 emits Hermes JSON inside `<tool_call>`, not Llama-XML.

### Submit recipe

```bash
# Qwen3.5:9B on rtx_6000:1 — verify before promoting to production
sbatch --export=ALL,HF_MODEL="Qwen/Qwen3.5-9B",OLLAMA_TAG="Qwen3.5:9B" \
       --gpus=rtx_6000:1 --mem=48G --time=01:00:00 \
       --job-name=vllm_qwen35_9b_smoke \
       cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch

# Qwen3.5:4B on rtx_6000:1 — verify before promoting to production
sbatch --export=ALL,HF_MODEL="Qwen/Qwen3.5-4B",OLLAMA_TAG="Qwen3.5:4B" \
       --gpus=rtx_6000:1 --mem=48G --time=01:00:00 \
       --job-name=vllm_qwen35_4b_smoke \
       cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch

# Gemma 31B on rtx_6000:1 — note the parser override
sbatch --export=ALL,HF_MODEL="cyankiwi/gemma-4-31B-it-AWQ-4bit",OLLAMA_TAG="gemma4:31b",TOOL_CALL_PARSER="gemma4" \
       --gpus=rtx_6000:1 --mem=48G --time=01:00:00 \
       --job-name=vllm_gemma_smoke \
       cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch

# Tight VRAM (rtx_3090 24 GB serving 27B AWQ) — see CHANGELOG 2026-05-10 caveat
sbatch --export=ALL,HF_MODEL="cyankiwi/Qwen3.6-27B-AWQ-INT4",OLLAMA_TAG="qwen3.6:27b",MAX_MODEL_LEN=7168,GPU_MEM_UTIL=0.85,ENFORCE_EAGER=1,NUM_PREDICT=4096 \
       --gpus=rtx_3090:1 --mem=32G --time=01:00:00 \
       --job-name=vllm_27b_smoke_tight \
       cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch
```

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

### Conditions (3 active) — looped inside every job
- `no-tools`                    — baseline, no MCP tools exposed (matrix gate skips think=on cells)
- `tools_per-task_minimal`      — tools on, filter=per-task allowlist, prompt=minimal
- `tools_all_minimal`           — tools on, filter=all, prompt=minimal

The two `*_guided` variants (`tools_per-task_guided`, `tools_all_guided`)
were retired 2026-04-27 (Newcombe-Δ on the 26042026 sweep showed
minimal-vs-guided shifts results by ≤4pp per model with every CI crossing
zero). The case branches in `run_condition_rtx.sbatch` are commented out;
explicitly listing the old labels in `CONDITIONS=` would now hit the `*)`
error branch. Re-enable by uncommenting the case branches and adding
`"guided"` back to `PROMPT_STYLE_CHOICES` in `run_experiment.py`.

Each condition invokes `run_experiment.py` once, writing to its own output
subdir. Conditions inside a job are independent: a late-stage condition
failure doesn't lose earlier-condition results.

### Think modes
- `on`       — passes `think=True` to Ollama (explicit deliberation).
- `off`      — passes `think=False` (fast path, no reasoning tokens).
- `default`  — omits the `think` kwarg so the model's native setting applies.
   Use this for models without a thinking switch (e.g. `gemma4*` historically;
   the rtx path now passes `on/off` to all models and lets Ollama ignore
   unsupported values).

The paper reports "better of with- and without-thinking"; running both
explicitly lets us reproduce that protocol systematically.

## Resource profile (`run_condition_rtx.sbatch`)

Per-array-task allocation. Each task = one (model, think, cond) cell.

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | rtx_pro_6000 (and the rtx_6000 opt-in) GRES are accessible from `main`. Mar-26 guide §High-Priority: never use a non-`main` partition without QoS rights. |
| `--gpus` | `rtx_pro_6000:1` (default) or `rtx_6000:1` (opt-in) | One dedicated GPU per array task; the cell's single model stays resident throughout |
| `--array` | `0-(N-1)` when N > 1 (no `%N` cap by default) | Fan-out unlimited — SLURM runs as many tasks as the pool has capacity for. Override with `%N` post-submit (`scontrol update JobId=<master> ArrayTaskThrottle=N`) if politeness is desired |
| `--time` | `12:00:00` (tools cells) / `08:00:00` (no-tools cells) / `03:00:00` (smoke) | Per-cell budget. Tools cell wall ~5-9h post 2026-04-29 cap-bump (single-task only after the 2026-05-05 chain archive); no-tools ~6-7h (5-task matrix incl. simulate after PR-4 / no-tools-simulate-task fix) |
| `--mem` | `80G` (rtx_pro_6000 default) / `48G` (rtx_6000 opt-in) | IT cap 2026-04-27. With one model per task, peak host RAM is ~26 GB (gemma4:31b weight cache) — comfortably under either cap |
| `--tmp` | `50G` | Mar-26 guide §"SSD Drive". Reserves space on `/scratch/$USER/$JOBID`; covers ollama.sif (~3 GB) + one model (~26 GB peak). The sbatch falls back to `/tmp/rtx-$JOBID` if `/scratch` isn't writable on the allocated node |
| `--cpus-per-task` | not set (cluster default `cpus-per-gpu`) | IT request 2026-04-27; explicit `12` was depriving other users |
| Concurrency | `4` | Matches OLLAMA_NUM_PARALLEL=4; isolated per-task server so no contention argument applies |

## Monitoring

```bash
squeue --me                                  # all my running/pending jobs
                                             # array tasks appear as <master>_<task>
sstat -j <jobid> --format=JobID,MaxRSS,MaxVMSize   # live memory usage (per task)
scontrol show job <jobid>                    # full job spec
scontrol show job <master>                   # array-master spec (counts queued/running tasks)

# Array task log (each task has its own .out)
tail -f cluster-experimenting/logs/pddl_rtx_<model>-<task_jid>.out

# Per-task ollama serve log on the compute node (now under /scratch)
ssh <node> tail -f /scratch/$USER/<task_jid>/rtx-work/ollama-serve.log
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
gemma4:31b cells).

**Do NOT use `scancel --name=pddl_*`** — verified 2026-04-25 on SLURM 25.11.4:
`--name` is exact-string match (comma-separated literal names), not a glob, so
the cancel is a silent no-op. Filter by name prefix with squeue → awk → xargs:

```bash
squeue --me -h -o '%i %j' | awk '$2 ~ /^pddl_rtx_/ {print $1}' | xargs --no-run-if-empty scancel
```

## Troubleshooting

**VRAM blowup after warmup (`exit 3`).** The runtime guard fired
because VRAM > 85% post-warmup. Likely cause: `OLLAMA_NUM_PARALLEL` × `num_ctx`
too high for the model. Check `run_condition_rtx.sbatch` — `NUM_PARALLEL=4`
and `num_ctx=16384` are sized for the default `--all` pack on
rtx_pro_6000 96 GB. With multi-model packing, the guard skips the
offending model and continues with the next (sets non-zero exit at the end).
Note (2026-04-29): single-task `num_ctx` was raised 8192 → 16384 (with
`num_ctx_thinking` held equal at 16384 for tools/no-tools fairness in
the "tools save tokens" headline). Per-call KV cache approximately
doubles vs the prior 8192 baseline. If a sweep trips the guard,
post-mortem `sacct/MaxRSS` to right-size; lowering `--num-ctx` or
`--concurrency` is the fastest mitigation. The chain-phase ctx knob
(`--num-ctx-chain`) was retired 2026-05-05 with the chain archive.

**`apptainer: command not found`.** Apptainer module not loaded
on the compute node. The sbatch assumes the cluster default has it on the
PATH; if not, add `module load apptainer` to the sbatch.

**Pull fails on first job (no internet).** rtx self-deploy pulls
from `docker://ollama/ollama` and from the public Ollama registry. The
compute node needs outbound internet — confirm with IT if a job hangs at
the `Pulling` step.

**Model name not recognized.** `ollama pull <name>` has to succeed against
the public Ollama registry; check name spelling (`Qwen3.5:0.8B` vs
`qwen3.5:0.8B`) and that the tag exists upstream.

**`java: command not found` or `UnsupportedClassVersionError`.** The conda
env isn't active, or `openjdk=17` wasn't installed. Rerun `setup_env.sh`.

**Plugin `.venv` missing on first job.** `setup_env.sh` didn't run, or ran
from a different `$HOME`. Rerun it on the login node with the same user.

**First run on a given conda env is slow.** First `run_experiment.py`
invocation does MCP handshakes and Ollama cold-starts per model.
Subsequent jobs on the same env reuse the cached plugin `.venv`s and the
cached `$HOME/ollama.sif`.
