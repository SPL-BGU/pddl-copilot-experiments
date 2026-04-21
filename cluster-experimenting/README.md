# Cluster-experimenting (BGU ISE-CS-DT)

SLURM sbatch scripts for running the `pddl-copilot-experiments` sweep on the
BGU ISE-CS-DT cluster (login node: `slurm.bgu.ac.il`).

**Cluster convention:** each job is one `(model, think_mode)` pair and loops
all 5 conditions sequentially in-process. The full sweep is 9 jobs organised
into 5 waves, each wave chained to the previous with `--dependency=afterok`
so only one model family is live on the shared `cis-ollama` server at any
time. This keeps the server from evicting and reloading weights between
jobs (the pathology that made the 2026-04-20 sweep take >10h/job; see
`development/CHANGELOG.md` 2026-04-21 entry for the full analysis).

## Quickstart (from the login node, `slurm-login-01` / `slurm.bgu.ac.il`)

Copy-paste this whole block the first time:

```bash
# 1. Clone both repos under $HOME (siblings — the harness auto-locates the marketplace)
cd ~
git clone https://github.com/SPL-BGU/pddl-copilot-experiments.git
git clone https://github.com/SPL-BGU/pddl-copilot.git

# 2. Build conda env (pddl_copilot: py3.12 + openjdk17 + mcp + ollama)
#    and pre-populate the two plugin .venvs. One-time, ~5 min.
bash ~/pddl-copilot-experiments/cluster-experimenting/setup_env.sh

# 3. Preview what the full sweep would submit (9 jobs across 5 waves). No submission yet.
cd ~/pddl-copilot-experiments
bash cluster-experimenting/submit_all.sh --dry-run

# 4. Smoke-test: submit ONE small/cheap job first to catch env or Ollama issues
#    before firing the dependency chain. Restrict CONDITIONS to a single
#    condition (no-tools) so it finishes in minutes. Setting --job-name keeps
#    the log path aligned with the tail command below; the submit_all.sh path
#    sets it automatically, but direct sbatch invocations have to.
sbatch --job-name=pddl_Qwen3_5_0_8B_off \
       --export=ALL,MODEL=Qwen3.5:0.8B,THINK_MODE=off,CONDITIONS=no-tools \
       cluster-experimenting/run_condition.sbatch
squeue --me
# Watch the log (replace <jobid> with the one sbatch printed):
#   tail -f cluster-experimenting/logs/pddl_Qwen3_5_0_8B_off-<jobid>.out

# 5. If the smoke test finishes OK (exit 0, JSON written under results/),
#    fire the full sweep. Wave 1 runs immediately; waves 2-5 queue with
#    afterok dependencies and only start once the previous wave succeeds.
bash cluster-experimenting/submit_all.sh
```

Rerunning any step is safe: `git clone` can be replaced with `git -C <dir> pull`,
`setup_env.sh` detects an existing conda env and reuses it, and `submit_all.sh`
is idempotent (each submission gets a fresh `$SLURM_JOBID` in the output path).

## Why a dedicated cluster setup (vs. just `run_background.sh`)

`run_background.sh` is laptop/macOS oriented: it wraps everything in `nohup` +
`caffeinate` and can fire up a local `ollama serve`. On a SLURM compute node
none of that applies — the sbatch process *is* the background job, `caffeinate`
is macOS-only, and compute nodes don't have Ollama installed. The files here
reuse the remote-Ollama logic from `run_background.sh` but strip the
backgrounding wrapper so SLURM can manage the job lifecycle.

## Prereqs

1. **Cluster account** — request access via your SPL-BGU contact / IT.
2. **BGU VPN** — needed for the compute node to reach `cis-ollama.auth.ad.bgu.ac.il`.
   (Login node is inside the BGU network, so VPN is only relevant if you test
   from outside.)
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

## Submitting the full sweep

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

Models are all verified present on `cis-ollama/api/tags` (2026-04-20). The
paper's `qwen3:0.6b` / `qwen3:4b` are **not** hosted on cis-ollama, so this
run is a cluster-variant of the paper, not a 1:1 reproduction
(see `run_experiment.py:71-75`). List currently-hosted models with:
```bash
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/tags \
    | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

### Conditions (5) — looped inside every job
- `no-tools`                    — baseline, no MCP tools exposed
- `tools_per-task_minimal`      — tools on, filter=per-task allowlist, prompt=minimal
- `tools_per-task_guided`       — tools on, filter=per-task, prompt=guided
- `tools_all_minimal`           — tools on, filter=all, prompt=minimal
- `tools_all_guided`            — tools on, filter=all, prompt=guided

Each condition invokes `run_experiment.py` once, writing to its own output
subdir. Conditions inside a job are independent: a late-stage condition
failure doesn't lose earlier-condition results, but a non-zero overall rc
still halts the afterok chain.

### Think modes
- `on`       — passes `think=True` to Ollama (explicit deliberation).
- `off`      — passes `think=False` (fast path, no reasoning tokens).
- `default`  — omits the `think` kwarg so the model's native setting applies.
   Used for `gemma4:31b`, which has no thinking mode.

The paper reports "better of with- and without-thinking"; running both
explicitly lets us reproduce that protocol systematically. Before this
change the default was `--think default` for every model, which meant
thinking ON for Qwen but OFF for gpt-oss/gemma — silent mixed methodology.

### Variants

```bash
# Resume from a specific wave (skips earlier waves — no afterok dep on them)
bash cluster-experimenting/submit_all.sh --from-wave 3

# Preview without submitting
bash cluster-experimenting/submit_all.sh --dry-run

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

## Resource profile

Per sbatch defaults (`run_condition.sbatch`):

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | CPU partition — no local inference, LLM runs on cis-ollama |
| `--constraint` | `cpu` | Same reason |
| `--time` | `3-00:00:00` | Sized for `gpt-oss:120b` × 5 conditions × paper-aligned chain-samples=100. Partition `main` allows up to 7 days. Small models finish much sooner; SLURM charges actual wall time. |
| `--cpus-per-task` | `8` | MCP server subprocesses + concurrent Ollama requests. In-job `concurrency=2` × 2 parallel jobs per wave = 4 concurrent requests, exactly saturating the measured server `OLLAMA_NUM_PARALLEL=4` without queueing (probe 2026-04-21; see CHANGELOG). |
| `--mem` | `16G` | ENHSP heap + Python overhead; well below BGU's 58G ceiling |
| `--gpus` | `0` | Nothing GPU-accelerated runs on the node |

Tighten `--time` / `--mem` for the small model to improve queue priority:
```bash
sbatch --job-name=pddl_Qwen3_5_0_8B_off \
       --time=0-04:00:00 --mem=8G \
       --export=ALL,MODEL=Qwen3.5:0.8B,THINK_MODE=off,CONDITIONS=no-tools \
       cluster-experimenting/run_condition.sbatch
```

## Monitoring

```bash
squeue --me                                  # all my running/pending jobs
sstat -j <jobid> --format=JobID,MaxRSS,MaxVMSize   # live memory usage
scontrol show job <jobid>                    # full job spec
tail -f cluster-experimenting/logs/pddl_<model>_<think>-<jobid>.out

# Check what model is currently loaded on the shared server (diagnose eviction):
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/ps \
    | python3 -m json.tool
# During a wave, expect exactly ONE model loaded — the wave's target model.
# Other models showing up mid-wave means another user is also hitting cis-ollama.
```

After a job finishes:
```bash
sacct -j <jobid> --format=JobName,MaxRSS,AllocTRES,State,Elapsed,Start,ExitCode
```

## Where things go

| Path | What |
|---|---|
| `results/slurm_<model>_<think>_<cond>_<jobid>/` | `run_experiment.py` JSON outputs (per-instance results, `summary_*.json`). One subdir per condition inside a single job; `<jobid>` is the same across the 5 subdirs a job produces. `results/` is gitignored. |
| `cluster-experimenting/logs/<jobname>-<jobid>.out` | SLURM stdout/stderr per job — covers all 5 conditions run sequentially. Directory is gitignored. |

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

Then open `analyze_results.ipynb`. Note: the notebook's top cell currently
globs `results/single_task_*.json` at depth 1, which doesn't descend into
`slurm_*/` subdirs — you'll need to either flatten the JSONs up one level
or change the glob to `results/**/single_task_*.json` with
`recursive=True`. This is a pre-existing notebook limitation, not new
here.

## Cancelling jobs

```bash
scancel <jobid>                 # by id
scancel --name pddl_gpt-oss_20b_off   # by name (new pattern: <model>_<think>)
scancel -u $USER                # nuke all of mine
scancel -t PENDING -u $USER     # only pending
```

**About afterok cascades:** cancelling an earlier-wave job does **not**
automatically cancel its dependents — SLURM leaves them `PENDING` with
reason `DependencyNeverSatisfied` and they never run. Clean them up with
`scancel -u $USER` or `scancel -t PENDING -u $USER`.

Conversely, if an earlier-wave job **fails** (non-zero exit), its
dependents stay `PENDING (DependencyNeverSatisfied)` until you cancel
them. No wasted compute, but the queue entries linger until cleanup.

## Troubleshooting

**Job dies at startup with `cannot reach …/api/tags`:** compute node can't reach
cis-ollama. Usually a BGU-VPN / DNS / cert issue. Sanity-check from the login
node:
```bash
curl -k -sf --max-time 10 https://cis-ollama.auth.ad.bgu.ac.il/api/tags | head
```
If that works but the compute node fails, IT can route-whitelist the compute
subnet. If it's a cert chain issue, `OLLAMA_INSECURE=1` (already default) handles it.

**Model name not recognized:** cis-ollama's available models drift. List what's
there, then edit the `WAVE1`–`WAVE5` arrays at the top of `submit_all.sh`
to use the current names:
```bash
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/tags \
    | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

**`java: command not found` or `UnsupportedClassVersionError`:** the conda env
isn't active, or `openjdk=17` wasn't installed. Rerun `setup_env.sh`.

**Plugin `.venv` missing on first job:** `setup_env.sh` didn't run, or ran from
a different `$HOME`. Rerun it on the login node with the same user.

**First run on a given conda env is slow:** first `run_experiment.py` invocation
does MCP handshakes and Ollama cold-starts per model. Subsequent jobs on the
same env reuse the cached plugin `.venv`s.
