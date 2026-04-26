# Cluster-experimenting (BGU ISE-CS-DT)

SLURM sbatch scripts for running the `pddl-copilot-experiments` sweep on the
BGU ISE-CS-DT cluster (login node: `slurm.bgu.ac.il`).

**Default path: rtx self-deploy (`submit_with_rtx.sh`).** One job per model,
allocated its own GPU (rtx_6000 48 GB or rtx_pro_6000 96 GB), runs an
isolated Apptainer Ollama server on the compute node, and loops
`THINK_MODES × CONDITIONS` in-process so weights stay resident. No
shared-server contention, no `afterok` chain — all model jobs queue in
parallel and start as soon as a GPU node frees up. The 2026-04-25 sweep
(14 jobs) submitted at 17:31 had bulk jobs starting in 8 seconds.

**Fallback path: cis-ollama waves (`submit_all.sh`).** Use only when:
- the rtx_pro_6000 pool is saturated and `gpt-oss:120b` needs a GPU
  alternative — see `submit_120b_cis.sh`, or
- you want to compare cis vs. rtx-dedicated throughput for the same model.

The cis path needs strict `afterok` serialization across 5 waves
(9 jobs total) because cis-ollama runs `MAX_LOADED=1`: parallel jobs
across model families would thrash on weight eviction. See
`development/CHANGELOG.md` 2026-04-21 entry for the original analysis.

## Quickstart — rtx self-deploy (default)

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
#    submit the rest. Each model is one independent job; they queue in
#    parallel with no cross-job dependency.
for m in Qwen3.5:0.8B gpt-oss:20b Qwen3.5:27b gemma4:31b gpt-oss:120b; do
    bash cluster-experimenting/submit_with_rtx.sh "$m"
done
```

Rerunning any step is safe: `git clone` can be replaced with `git -C <dir> pull`,
`setup_env.sh` detects an existing conda env and reuses it, and
`submit_with_rtx.sh` is idempotent (each submission gets a fresh
`$SLURM_JOBID` in the output path).

## Why a dedicated cluster setup (vs. just `run_background.sh`)

`run_background.sh` is laptop/macOS oriented: it wraps everything in `nohup` +
`caffeinate` and can fire up a local `ollama serve`. On a SLURM compute node
none of that applies — the sbatch process *is* the background job, `caffeinate`
is macOS-only, and compute nodes don't have Ollama installed. The files here
reuse the remote-Ollama logic from `run_background.sh` but strip the
backgrounding wrapper so SLURM can manage the job lifecycle.

## Prereqs

1. **Cluster account** — request access via your SPL-BGU contact / IT.
2. **BGU VPN** — needed only if you use the cis-ollama fallback path (the
   compute node has to reach `cis-ollama.auth.ad.bgu.ac.il`). The default
   rtx self-deploy path runs Ollama on the compute node itself and pulls
   weights from the public Ollama registry. Login node is inside the BGU
   network either way, so VPN is only relevant if you test from outside.
3. **Both repos cloned under `$HOME` on the login node:**
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

## rtx self-deploy submission (default path)

```bash
cd ~/pddl-copilot-experiments

# Per-model job: full think × condition matrix (4 tools-conditions × 2 think
# modes = 8 condition-runs in one job).
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:27b
bash cluster-experimenting/submit_with_rtx.sh gemma4:31b
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:120b   # → rtx_pro_6000

# Baseline-only run: no-tools/think=off/solve, ~15 min, --time=1:00:00.
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B --no-tools

# Preview command without submitting.
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b --dry-run
```

Each invocation submits one independent SLURM job. There's no `afterok`
chain — SLURM queues them in parallel and they start as soon as a GPU
node frees up. The 2026-04-25 sweep had bulk jobs starting in 8 seconds.

### GPU routing

| Model | Default pool | Why |
|---|---|---|
| `gpt-oss:120b` | `rtx_pro_6000` (96 GB) | 65 GB weights don't fit on rtx_6000 (48 GB) |
| everything else | opportunistic | Queries `sinfo` at submit time and picks whichever pool has more idle nodes; tiebreak prefers rtx_pro_6000 |

Force a specific pool with `--gpu-type rtx_6000` or `--gpu-type rtx_pro_6000`.

If `rtx_pro_6000` is saturated when you submit `gpt-oss:120b`, fall back
to the cis path: `bash cluster-experimenting/submit_120b_cis.sh`.

### `--no-tools` shorthand

`--no-tools` pins the run to the baseline-only cell:
- `CONDITIONS=no-tools` (one tools-off pass)
- `THINK_MODES=off` (no-tools/think=on is skipped by the matrix gate anyway)
- `TASKS=solve` (no-tools is only meaningful for solve; the other 4 tasks
  require tool calls to be honestly evaluated — see EXPERIMENTS_FLOW.md §5)
- `--time=1:00:00` (3× headroom on the slowest no-tools run observed
  2026-04-25; tighter wall time helps SLURM fairshare priority)

Conflicts with `--think-modes` (any value other than `off`) are rejected.

### Models verified on cis-ollama (2026-04-20)

The paper's `qwen3:0.6b` / `qwen3:4b` are **not** hosted on cis-ollama, so
this cluster run is a paper-variant, not a 1:1 reproduction (see
`run_experiment.py:71-75`). The five models in this sweep —
`Qwen3.5:0.8B`, `gpt-oss:20b`, `Qwen3.5:27b`, `gemma4:31b`, `gpt-oss:120b`
— have all been verified hosted. List currently-hosted models with:

```bash
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/tags \
    | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

The rtx path doesn't depend on cis-ollama for inference, but it does pull
model weights from the public Ollama registry (`docker://ollama/ollama` +
`ollama pull`), so the model name has to be valid there. The `.sif`
container is cached at `$HOME/ollama.sif` after the first run (~3 min cold).

## Cis-ollama wave submission (fallback path)

Use this only when:
- the rtx_pro_6000 pool is saturated and you need `gpt-oss:120b` to
  proceed → `bash cluster-experimenting/submit_120b_cis.sh`, or
- you want to compare cis-shared vs. rtx-dedicated throughput head-to-head.

```bash
cd ~/pddl-copilot-experiments
bash cluster-experimenting/submit_all.sh --dry-run    # preview commands
bash cluster-experimenting/submit_all.sh              # submit 9 jobs in 5 waves
```

### Wave structure (9 jobs total)

| Wave | Model | Think variants | Jobs | Depends on |
|---|---|---|---|---|
| 1 | `Qwen3.5:0.8B` | `on`, `off` | 2 | — (runs immediately) |
| 2 | `gpt-oss:20b` | `on`, `off` | 2 | `afterok:<wave1>` |
| 3 | `Qwen3.5:27b` | `on`, `off` | 2 | `afterok:<wave2>` |
| 4 | `gemma4:31b` | `default` | 1 | `afterok:<wave3>` |
| 5 | `gpt-oss:120b` | `on`, `off` | 2 | `afterok:<wave4>` |

Within each wave the think-on / think-off jobs run **in parallel** — they
share the same loaded model weights on the server, so there's no eviction.
Across waves, `afterok` serialises everything: if any job in a wave fails
(non-zero exit), the subsequent waves will never run — SLURM marks them
`PENDING (DependencyNeverSatisfied)` and they sit there until you
`scancel` them. You diagnose the failure, then resubmit. See the
Cancelling section below for cleanup.

### Cis variants

```bash
# Resume from a specific wave (skips earlier waves — no afterok dep on them)
bash cluster-experimenting/submit_all.sh --from-wave 3

# Single job, submit directly (e.g. smoke-test, rerun one model)
sbatch --job-name=pddl_gpt-oss_20b_off \
       --export=ALL,MODEL=gpt-oss:20b,THINK_MODE=off \
       cluster-experimenting/run_condition.sbatch

# Single job, only one condition
sbatch --job-name=pddl_Qwen3_5_0_8B_off \
       --export=ALL,MODEL=Qwen3.5:0.8B,THINK_MODE=off,CONDITIONS=no-tools \
       cluster-experimenting/run_condition.sbatch
```

Custom model lists and custom wave compositions aren't exposed as flags —
if the default matrix needs to change, edit the `WAVE1`–`WAVE5` arrays at
the top of `submit_all.sh`.

## Conditions and think modes (shared)

### Conditions (5) — looped inside every job
- `no-tools`                    — baseline, no MCP tools exposed (rtx path: only honest for `solve`/think=off; matrix gate skips other cells)
- `tools_per-task_minimal`      — tools on, filter=per-task allowlist, prompt=minimal
- `tools_per-task_guided`       — tools on, filter=per-task, prompt=guided
- `tools_all_minimal`           — tools on, filter=all, prompt=minimal
- `tools_all_guided`            — tools on, filter=all, prompt=guided

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

## Resource profiles

### rtx self-deploy (`run_condition_rtx.sbatch`) — default

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | rtx_6000 / rtx_pro_6000 GRES are accessible from `main` |
| `--gpus` | `rtx_6000:1` or `rtx_pro_6000:1` | One dedicated GPU per job; weights stay resident across the inner think × condition loop |
| `--time` | `2-00:00:00` (full sweep) / `1:00:00` (--no-tools) | Slowest tools job observed at ~10 h on 2026-04-25. No-tools runs at 10–22 min wall |
| `--mem` | `48G` (rtx_6000) / `96G` (rtx_pro_6000) | Sized to GPU pool's host RAM expectation |
| `--cpus-per-task` | `12` | MCP subprocesses + Ollama serve + concurrency=4 |
| Concurrency | `4` | Matches OLLAMA_NUM_PARALLEL=4; no shared-server contention so no need to under-provision |

### cis-ollama waves (`run_condition.sbatch`) — fallback

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | CPU partition — no local inference, LLM runs on cis-ollama |
| `--constraint` | `cpu` | Same reason |
| `--time` | `3-00:00:00` | Sized for `gpt-oss:120b` × 5 conditions × paper-aligned chain-samples=100. Partition `main` allows up to 7 days. Small models finish much sooner; SLURM charges actual wall time. |
| `--cpus-per-task` | `8` | MCP server subprocesses + concurrent Ollama requests. In-job `concurrency=2` × 2 parallel jobs per wave = 4 concurrent requests, exactly saturating the measured server `OLLAMA_NUM_PARALLEL=4` without queueing (probe 2026-04-21; see CHANGELOG). |
| `--mem` | `16G` | ENHSP heap + Python overhead; well below BGU's 58G ceiling |
| `--gpus` | `0` | Nothing GPU-accelerated runs on the node |

## Monitoring

```bash
squeue --me                                  # all my running/pending jobs
sstat -j <jobid> --format=JobID,MaxRSS,MaxVMSize   # live memory usage
scontrol show job <jobid>                    # full job spec

# rtx self-deploy log (default path)
tail -f cluster-experimenting/logs/pddl_rtx_<model>-<jobid>.out
# cis-ollama wave log (fallback path)
tail -f cluster-experimenting/logs/pddl_<model>_<think>-<jobid>.out

# rtx path: inspect the per-job ollama.log for VRAM/load events
ssh <node> tail -f /tmp/rtx-<jobid>/ollama-serve.log

# cis path: check what model is currently loaded on the shared server
# (diagnose eviction). During a wave, expect exactly ONE model loaded —
# the wave's target model. Other models showing up mid-wave means another
# user is also hitting cis-ollama.
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/ps \
    | python3 -m json.tool
```

After a job finishes:
```bash
sacct -j <jobid> --format=JobName,MaxRSS,AllocTRES,State,Elapsed,Start,ExitCode
```

The cluster-ops skill bundles status/preflight/postmortem helpers that wrap
the SSH calls — see `.claude/skills/cluster-ops/SKILL.md`.

## Where things go

| Path | What |
|---|---|
| `results/slurm_<model>_<think>_<cond>_<jobid>/` | `run_experiment.py` JSON outputs (per-instance results, `summary_*.json`). Same format for both backends — distinguish runs via `ollama_host` recorded in `summary.json`. `results/` is gitignored. |
| `cluster-experimenting/logs/pddl_rtx_<model>-<jobid>.out` | rtx self-deploy log (default). Covers the full think × condition matrix in one file. Directory is gitignored. |
| `cluster-experimenting/logs/pddl_<model>_<think>-<jobid>.out` | cis-ollama wave log (fallback). One job = one think mode × all conditions. |

## Fetching results locally

From your laptop:
```bash
# One condition's output
scp -r <user>@slurm.bgu.ac.il:~/pddl-copilot-experiments/results/slurm_gpt-oss_20b_off_tools_all_minimal_12345 \
       ~/personal/pddl-copilot-experiments/results/

# Everything from a run
rsync -av <user>@slurm.bgu.ac.il:~/pddl-copilot-experiments/results/slurm_* \
         ~/personal/pddl-copilot-experiments/results/
```

Analyze synced results ad-hoc against `results/**/{single_task,chain,summary}_*.json` — the canonical schema for those files is `save_results` in `run_experiment.py`. Recent analyses live in the contributor's `.local/reports/` (not committed).

## Cancelling jobs

```bash
scancel <jobid>                 # by id
scancel -u $USER                # nuke all of mine
scancel -t PENDING -u $USER     # only pending
```

**Do NOT use `scancel --name=pddl_*`** — verified 2026-04-25 on SLURM 25.11.4:
`--name` is exact-string match (comma-separated literal names), not a glob, so
the cancel is a silent no-op. Filter by name prefix with squeue → awk → xargs:

```bash
squeue --me -h -o '%i %j' | awk '$2 ~ /^pddl_/ {print $1}' | xargs --no-run-if-empty scancel
```

**About afterok cascades (cis path only):** cancelling an earlier-wave job
does **not** automatically cancel its dependents — SLURM leaves them
`PENDING` with reason `DependencyNeverSatisfied` and they never run. Clean
them up with `scancel -u $USER` or `scancel -t PENDING -u $USER`. The rtx
path doesn't have this problem because there's no afterok chain.

## Troubleshooting

**rtx path: VRAM blowup after warmup (`exit 3`).** The runtime guard fired
because VRAM > 85% post-warmup. Likely cause: `OLLAMA_NUM_PARALLEL` × `num_ctx`
too high for the model. Check `run_condition_rtx.sbatch` — `NUM_PARALLEL=4`
and `num_ctx=8192` are sized for ≤31B models on rtx_6000 (48 GB). For 120b,
ensure you're on rtx_pro_6000.

**rtx path: `apptainer: command not found`.** Apptainer module not loaded
on the compute node. The sbatch assumes the cluster default has it on the
PATH; if not, add `module load apptainer` to the sbatch.

**rtx path: pull fails on first job (no internet).** rtx self-deploy pulls
from `docker://ollama/ollama` and from the public Ollama registry. The
compute node needs outbound internet — confirm with IT if a job hangs at
the `Pulling` step.

**cis path: job dies at startup with `cannot reach …/api/tags`.** Compute
node can't reach cis-ollama. Usually a BGU-VPN / DNS / cert issue.
Sanity-check from the login node:
```bash
curl -k -sf --max-time 10 https://cis-ollama.auth.ad.bgu.ac.il/api/tags | head
```
If that works but the compute node fails, IT can route-whitelist the compute
subnet. If it's a cert chain issue, `OLLAMA_INSECURE=1` (already default) handles it.

**Model name not recognized.** Both paths require the model name be
recognized by Ollama. For the rtx path, `ollama pull <name>` has to
succeed (public registry); for the cis path, the name has to appear in
cis-ollama's `/api/tags`. List cis-hosted models:
```bash
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/tags \
    | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

**`java: command not found` or `UnsupportedClassVersionError`.** The conda
env isn't active, or `openjdk=17` wasn't installed. Rerun `setup_env.sh`.

**Plugin `.venv` missing on first job.** `setup_env.sh` didn't run, or ran
from a different `$HOME`. Rerun it on the login node with the same user.

**First run on a given conda env is slow.** First `run_experiment.py`
invocation does MCP handshakes and (rtx path) Ollama cold-starts per
model. Subsequent jobs on the same env reuse the cached plugin `.venv`s
and (rtx path) the cached `$HOME/ollama.sif`.
