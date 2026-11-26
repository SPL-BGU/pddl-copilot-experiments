# Cluster-experimenting (BGU CIS)

SLURM scripts for running `pddl-copilot-experiments` on the BGU CIS cluster
(login node: `slurm.bgu.ac.il`). The cluster was renamed from "ISE-CS-DT" to
"CIS" in March 2026; hardware, partitions and GRES names did not change.

**One submit script: `submit_with_rtx.sh`.** It builds one cell per
(model, think mode, condition) and submits the cells as one SLURM job array of
`run_condition_vllm_rtx.sbatch`. Each array task gets its own GPU, starts its
own vLLM server, and runs `run_experiment.py` for that one cell. No GPU is
shared between cells.

Which run is planned or in flight is in `development/STATUS.md`. Every cluster
action needs Omer's go-ahead first.

## The runs and how each was submitted

| Run | Models | Cells | Run tag | Design of record |
|---|---|---|---|---|
| May sweep | five (`PDDL_DEFAULT_MODELS`) | think on and off, no-tools and tools, all five tasks | `sweep6` for the renamed domains | `submit_full_sweep.sh`; `development/CHANGELOG.md` |
| October rerun | `Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b` | think off; tools and no-tools, all five tasks; plus one Gemma cell with `--prompt-style neutral` on `validate_plan` | `delivered-rerun`, `delivered-rerun-neutral` | `development/reference/delivered_rerun_prereg.md` |
| Corrected-prompt control | same three | think off, no-tools, solve and simulate, three system messages | `control-promptfix` | `development/reference/control_prompt_fix_prereg.md` |
| Matched run | same three | think off, solve and simulate: no-tools with the format-stated message, plus the with-tools cell, in one job | see `development/STATUS.md` | its registration in `development/reference/` |

The exact command of a registered run is in its registration. Do not rebuild
it from this table.

### Flags these runs use

- `--run-tag <tag>`: suffix on every cell's results folder
  (`results/slurm_vllm_<model>_<think>_<cond>_<tag>/`), so a run never writes
  into another run's folder.
- `--think-modes "off"`: without it the default is `on off`, two cells per model.
- `--tools-only` / `--no-tools`: one side of the condition axis.
- `--tasks "<list>"`: run only these tasks.
- `--prompt-style neutral`: with-tools system prompt reduced to the role
  sentence. Requires `--tools-only`. The cell is named `tools_all_neutral`.
- `--no-tools-system "<list>"`: the no-tools system message on solve and
  simulate. Values: `registered`, `no-pointer`, `format-stated`. Each value is
  its own cell (`no-tools`, `no-tools-syspointer-off`, `no-tools-sysformat`).
  Requires `--no-tools`, `--run-tag`, and `--tasks` within `solve simulate`.
- `--with-tools-cell`: only with `--no-tools-system`. Adds the ordinary
  `tools_all_minimal` cell after the no-tools cells of each model.
- `--time HH:MM:SS`: per-cell wall time. It cannot be raised after submission
  on this cluster, so set it at submit time and read it back from the queue.
- `--dry-run`: print the sbatch command and submit nothing.

The control was submitted as:

```bash
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b \
    --no-tools --think-modes off --tasks "solve simulate" \
    --no-tools-system "registered no-pointer format-stated" \
    --run-tag control-promptfix --gpu-type rtx_6000 --time 12:00:00
# 9 cells: three models by three system messages
```

The matched run has this layout:

```bash
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b \
    --no-tools --think-modes off --tasks "solve simulate" \
    --no-tools-system "format-stated" --with-tools-cell \
    --run-tag <tag> --gpu-type rtx_6000 --time HH:MM:SS
# 6 cells: per model, off|no-tools-sysformat and off|tools_all_minimal
```

The with-tools cell runs exactly as a `--tools-only` cell with the same
`--tasks` and `--run-tag` (v11 to v16, minimal style, no
`PDDL_NO_TOOLS_SYSTEM`). Every cell of a `--no-tools-system` job writes
`OUT_DIR/system_prompt_audit.jsonl` (one line per request, so several per trial
in a tool loop) and `OUT_DIR/client_settings.json`, and refuses a folder that
holds trials but no audit log.

### Smoke before a run

A smoke of a registered run is the run's own command with `--partial 1` and a
run tag of its own (for example `control-promptfix-smoke`). It uses the same
GPU class, memory and `--time` as the full run; only the number of trials
differs. Check that the answers are non-empty, not only that the job finished.

`--smoke` is a different thing: a one-cell parser check on blocksworld `p01`
(next section). It cannot be combined with `--tasks` or `--no-tools-system`.

### The May sweep

`submit_full_sweep.sh` is how the May sweep was submitted. It calls
`submit_with_rtx.sh` three times, because the two large models need a longer
wall time:

| Pack | GPU class | Per-cell time |
|---|---|---|
| `Qwen3.5:0.8B` + `Qwen3.5:4B` + `Qwen3.5:9B` | `rtx_6000:1` | 12 h |
| `qwen3.6:35b` | `rtx_6000:1` | 48 h |
| `gemma4:26b-a4b` | `rtx_6000:1` | 48 h |

Each model has one cell per (think mode, condition): 20 cells for five models.
No-tools cells run the plain wordings v11 to v13. With-tools cells run v11 to
v13 and the steered v14 to v16. `--include-no-tools-steered` also runs v14 to
v16 without tools (the steering control); those rows land in the same folder
and differ by `prompt_variant`.

```bash
bash cluster-experimenting/submit_full_sweep.sh --dry-run   # preview, submits nothing
```

## Prereqs

1. **Cluster account**: request access via your SPL-BGU contact / IT.
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
- OpenJDK 17 (ENHSP needs a JVM: installed via conda-forge, no cluster module needed)
- Pre-populated `.venv`s for `pddl-solver` and `pddl-validator` plugins
  (avoids per-job `pip install` cost and avoids N parallel jobs racing on the same venv)

Override defaults with env vars:
```bash
ENV_NAME=my_env PYTHON_VERSION=3.11 bash cluster-experimenting/setup_env.sh
```

## Submission details

Before a submission, run the preflight (it refreshes the repos and plugin
venvs and shows GPU pool capacity):
`bash .claude/skills/cluster-ops/scripts/preflight.sh`.

```bash
cd ~/pddl-copilot-experiments

# One model. Without other flags: 4 cells (think on/off by no-tools/tools).
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B

# Several models fan out as independent array tasks, one GPU each.
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B

# Preview the sbatch command without submitting.
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B --dry-run
```

Run manual submissions from `~/pddl-copilot-experiments`; output paths are
relative to it.

### GPU class

The default is `rtx_6000:1` (48 GB VRAM, `--mem=48G`). The AWQ builds of
`qwen3.6:35b` and `gemma4:26b-a4b` fit under `gpu-memory-utilization=0.85`; the
FP16 Qwen3.5 models sit well below. `--gpu-type rtx_pro_6000` selects the
96 GB class (`--mem=80G`). Any other value is an error.

### `--no-tools`

- `CONDITIONS=no-tools`.
- Think modes default to `on off` (two cells per model). Pass
  `--think-modes "off"` for thinking off only.
- All five tasks, unless `--tasks` is given.
- Wall time: `--time=12:00:00` unless `--time` is given (72 h when
  `--with-tools-cell` is set, since that job also holds a with-tools cell).

The JSON schema that the harness sends with no-tools requests does not take
effect under vLLM 0.20.2 (`EXPERIMENTS_FLOW.md` §4.2).
`--json-constraint structured_outputs` makes it take effect; the cell is then
named `no-tools-jsonbound`. That is a separate condition, used only for the
JSON constraint pilot.

### Resuming a cell

Each cell writes `trials.jsonl` as it goes. Resubmitting the same command after
a TIMEOUT, a preemption or `scancel` lands in the same folder and resumes; only
the trial that was in flight is run again. The resume key (`_trial_key` in
`pddl_eval/runner.py`) holds the `model` field as the HF id from `vllm_lookup`
(for example `Qwen/Qwen3.5-9B`).

## Models

The wrapper rejects any model that is not in `PDDL_VLLM_VERIFIED_MODELS`
(`lib/defaults.sh`). `vllm_lookup()` in the same file maps each tag to its HF
id and parser flags.

| Tag | HF id | Build | `TOOL_CALL_PARSER` | Notes |
|---|---|---|---|---|
| `Qwen3.5:0.8B` | `Qwen/Qwen3.5-0.8B` | FP16 (~1.6 GB) | `qwen3_xml` | May sweep only |
| `Qwen3.5:4B` | `Qwen/Qwen3.5-4B` | FP16 (~9 GB) | `qwen3_xml` | May sweep only |
| `Qwen3.5:9B` | `Qwen/Qwen3.5-9B` | FP16 (~18 GB) | `qwen3_xml` | |
| `qwen3.6:35b` | `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` | AWQ 4-bit MoE (~17 GB) | `qwen3_xml` | |
| `gemma4:26b-a4b` | `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit` | AWQ 4-bit MoE (~16 GB) | `gemma4` | No reasoning parser. Needs `MAX_NUM_BATCHED_TOKENS=4096` (set by `vllm_lookup`) |

Four more tags are in the verified list (`gemma4:26b-a4b-bf16`, `gpt-oss:20b`,
`ministral3:14b`, `llama3.1:8b`). They were smoke-tested only
(`development/reference/d1_smokes_20261027.md`) and are not part of any run.

A wrong `--tool-call-parser` gives no startup error. Every tool call is
silently dropped and tool selection reads 0%. `lib/defaults.sh` is the one
place that sets the parser per model. Roster history is in
`development/CHANGELOG.md`.

### Parser smoke

```bash
bash cluster-experimenting/submit_with_rtx.sh --smoke Qwen3.5:9B
bash cluster-experimenting/submit_with_rtx.sh --smoke --time 24:00:00 qwen3.6:35b
```

`--smoke` submits one cell per model that runs `run_experiment.py --smoke`
(blocksworld `p01`, one wording, all five tasks, both conditions, think on and
off) through the same sbatch. Default wall time 3 h.

### The vLLM image

The sbatch serves from the image `docker://vllm/vllm-openai:v0.20.2`, cached as
`$HOME/vllm.sif`. **Never delete `~/vllm.sif`.** It is shared by every job and
pinned to vLLM 0.20.2, the version every registered run names. A rebuild is
done by a CPU SLURM job, with Omer's go-ahead, and the version line in the
serve log (`Initializing a V1 LLM engine (v0.20.2)`) is checked afterwards.

`bash cluster-experimenting/probe_serving_env.sh` (login node, read-only)
prints the served vLLM version from the serve logs, the GPU models the jobs
saw, the image's vLLM, PyTorch and CUDA versions, and the driver and OS of one
node per GPU class. Its 2026-09-13 output is
`development/reference/serving_env_20260913.md`.

### Operational notes

- **`max_tokens > max_model_len` gives HTTP 400.** The per-task output caps are
  `solve=8192`, `validate_*=6144`, `simulate=6144`, under a 16384-token window.
- **A larger window** (`--max-model-len N`) is a separate condition and needs a
  run tag.

## Conditions and think modes

- `no-tools`: no MCP tools offered.
- `tools_all_minimal`: all tools offered, `minimal` system prompt.
- `tools_all_neutral`: all tools offered, `neutral` system prompt.
- `no-tools-syspointer-off`, `no-tools-sysformat`: no-tools with a corrected
  system message on solve and simulate.
- `no-tools-jsonbound`: no-tools with a JSON constraint that takes effect.

Think modes:

- `on`: `chat_template_kwargs.enable_thinking=True`.
- `off`: `enable_thinking=False`.
- `default`: the setting is omitted and the model's own default applies.

The reasoning trace is not stored by default: vLLM 0.20.2 returns it as
`message.reasoning` and the client reads `reasoning_content`, so `thinking` is
empty in every corpus so far (`pddl_eval/vllm_client.py`; ISS-030).

## Resource profile (`run_condition_vllm_rtx.sbatch`)

Per-array-task allocation. Each task = one (model, think, cond) cell.

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | rtx_6000 (and the rtx_pro_6000 opt-in) GRES are accessible from `main`. Mar-26 guide §High-Priority: never use a non-`main` partition without QoS rights. |
| `--gpus` | `rtx_6000:1` (default) or `rtx_pro_6000:1` (opt-in) | One dedicated GPU per array task; the cell's single model stays resident throughout |
| `--array` | `0-(N-1)` when N > 1 (no `%N` cap by default) | Fan-out unlimited: SLURM runs as many tasks as the pool has capacity for. Override with `%N` post-submit (`scontrol update JobId=<master> ArrayTaskThrottle=N`) if politeness is desired |
| `--time` | `72:00:00` (jobs with a tools cell) / `12:00:00` (`--no-tools`) / `03:00:00` (`--smoke`), unless `--time` is given | Per-cell budget. Cannot be raised after submission |
| `--mem` | `48G` (rtx_6000 default) / `80G` (rtx_pro_6000 opt-in) | IT cap 2026-04-27. With one model per task, peak host RAM is ~24 GB (qwen3.6:35b weight cache): comfortably under either cap |
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
preflight / postmortem) that wrap the SSH calls: see
`.claude/skills/cluster-ops/SKILL.md`. After syncing results, the
`analyzer` skill provides aggregation, plotting, master-table, and
drift-check recipes: see `.claude/skills/analyzer/SKILL.md`.

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
| `results/slurm_vllm_<model>_<think>_<cond>[_<run-tag>]/` | The output of one cell: `trials.jsonl`, `single_task_*.json`, `summary_*.json`. The folder name has no job id, so a resubmitted cell resumes in place. Several submissions leave several timestamped summaries. `results/` is gitignored. |
| `cluster-experimenting/logs/pddl_rtx_<model>-<task_jid>.out` | The job log of one array task. Each (re)submission gets its own file. Gitignored. |
| `cluster-experimenting/logs/<jobid>.cells.tsv` | For an array job: which array index is which cell. |

## Fetching results locally

Use `.claude/skills/cluster-ops/scripts/sync.sh` (see the `cluster-ops` skill).
The schema of the result files is `save_results` in `pddl_eval/summary.py` and
`EXPERIMENTS_FLOW.md` §9. Analyses are in `tools/reanalysis/` and
`tools/delivered_rerun/`; frozen figures in `development/NUMBERS.md`.

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

**Do NOT use `scancel --name=pddl_*`**: verified 2026-04-25 on SLURM 25.11.4:
`--name` is exact-string match (comma-separated literal names), not a glob, so
the cancel is a silent no-op. Filter by name prefix with squeue → awk → xargs:

```bash
squeue --me -h -o '%i %j' | awk '$2 ~ /^pddl_rtx_/ {print $1}' | xargs --no-run-if-empty scancel
```

## Troubleshooting

**VRAM guard after warmup (`exit 3`).** VRAM was above 85% after warmup.
`gpu-memory-utilization=0.85` and the 16384-token window are sized for these
models on a 48 GB `rtx_6000`. Read `sacct` and the job log before changing
anything.

**`apptainer: command not found`.** The sbatch assumes apptainer is on the
PATH of the compute node. If not, add `module load apptainer` to the sbatch.

**`java: command not found` or `UnsupportedClassVersionError`.** The conda env
is not active, or `openjdk=17` was not installed. Rerun `setup_env.sh`.

**Plugin `.venv` missing on the first job.** `setup_env.sh` did not run, or ran
under a different `$HOME`. Rerun it on the login node as the same user.

**Stuck progress or 0% tool selection.** Check the tool-call parser first
(`lib/defaults.sh`).
