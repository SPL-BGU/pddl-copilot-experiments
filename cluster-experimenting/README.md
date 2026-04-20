# Cluster-experimenting (BGU ISE-CS-DT)

SLURM sbatch scripts for running the `pddl-copilot-experiments` sweep on the
BGU ISE-CS-DT cluster (login node: `slurm.bgu.ac.il`).

**Cluster convention:** each job is one `(model × condition)` pair — mirrors the
fan-out pattern used by `online_model_learning/.local/amlgym/submit_all_comparisons.sh`.
5 conditions × 5 models = 25 independent SLURM jobs, running in parallel up to
cluster capacity.

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

# 3. Preview what the full sweep would submit (25 jobs). No submission yet.
cd ~/pddl-copilot-experiments
bash cluster-experimenting/submit_all.sh --dry-run

# 4. Smoke-test: submit ONE small/cheap job first to catch env or Ollama issues
#    before burning the queue on 25 of them.
sbatch --export=ALL,MODEL=Qwen3.5:0.8B,CONDITION=no-tools \
       cluster-experimenting/run_condition.sbatch
squeue --me
# Watch the log (replace <jobid> with the one sbatch printed):
#   tail -f cluster-experimenting/logs/pddl_Qwen3_5_0_8B_no-tools-<jobid>.out

# 5. If the smoke test finishes OK (exit 0, JSON written under results/),
#    fire the full sweep:
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
bash cluster-experimenting/submit_all.sh              # submit 5 × 5 = 25 jobs
```

**Default models** (all verified present on `cis-ollama/api/tags` on 2026-04-20):

| Model | Slot | Notes |
|---|---|---|
| `Qwen3.5:0.8B` | small | Nearest BGU-hosted analog to the paper's `qwen3:0.6b`. Used as `--small`. |
| `Qwen3.5:27b`  | large Qwen | ~same scale as `gemma4:31b` for clean cross-family comparison at ~30b. |
| `gpt-oss:20b`  | mid gpt-oss | |
| `gpt-oss:120b` | max gpt-oss | Slowest — the 24h sbatch `--time` was sized for this. |
| `gemma4:31b`   | gemma | |

The paper's `qwen3:0.6b` / `qwen3:4b` are **not** hosted on cis-ollama, so this
run is a cluster-variant of the paper, not a 1:1 reproduction.
(See `run_experiment.py:71-75`.) List the currently-hosted models at any time with:
```bash
curl -k -s https://cis-ollama.auth.ad.bgu.ac.il/api/tags \
    | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

**Conditions (5):** matches `run_background.sh`:
- `no-tools`                    — baseline, no MCP tools exposed
- `tools_per-task_minimal`      — tools on, filter=per-task allowlist, prompt=minimal
- `tools_per-task_guided`       — tools on, filter=per-task, prompt=guided
- `tools_all_minimal`           — tools on, filter=all, prompt=minimal
- `tools_all_guided`            — tools on, filter=all, prompt=guided

### Variants

```bash
# Only the small model, all 5 conditions (5 jobs)
bash cluster-experimenting/submit_all.sh --small

# Only the large model
bash cluster-experimenting/submit_all.sh --large

# Custom model list (must match cis-ollama /api/tags names exactly)
bash cluster-experimenting/submit_all.sh --models qwen3:latest gemma4:31b

# A single condition across both models (sanity / debugging)
bash cluster-experimenting/submit_all.sh --conditions no-tools

# Single job, submit directly
sbatch --export=ALL,MODEL=gpt-oss:20b,CONDITION=tools_all_minimal \
       cluster-experimenting/run_condition.sbatch
```

## Resource profile

Per sbatch defaults (`run_condition.sbatch`):

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | CPU partition — no local inference, LLM runs on cis-ollama |
| `--constraint` | `cpu` | Same reason |
| `--time` | `1-00:00:00` | Sized for `gpt-oss:120b`; small models finish much sooner (SLURM charges actual wall time, not the request). |
| `--cpus-per-task` | `8` | MCP server subprocesses + concurrent Ollama requests (default concurrency=4) |
| `--mem` | `16G` | ENHSP heap + Python overhead; well below BGU's 58G ceiling |
| `--gpus` | `0` | Nothing GPU-accelerated runs on the node |

Tighten `--time` / `--mem` for the small model to improve queue priority:
```bash
sbatch --time=0-04:00:00 --mem=8G --export=ALL,MODEL=Qwen3.5:0.8B,CONDITION=no-tools \
       cluster-experimenting/run_condition.sbatch
```

## Monitoring

```bash
squeue --me                                  # all my running/pending jobs
sstat -j <jobid> --format=JobID,MaxRSS,MaxVMSize   # live memory usage
scontrol show job <jobid>                    # full job spec
tail -f cluster-experimenting/logs/pddl_<model>_<cond>-<jobid>.out
```

After a job finishes:
```bash
sacct -j <jobid> --format=JobName,MaxRSS,AllocTRES,State,Elapsed,Start,ExitCode
```

## Where things go

| Path | What |
|---|---|
| `results/slurm_<model>_<cond>_<jobid>/` | `run_experiment.py` JSON outputs (per-instance results, `summary_*.json`). `results/` is gitignored. |
| `cluster-experimenting/logs/<jobname>-<jobid>.out` | SLURM stdout/stderr per job. Directory is gitignored. |

## Fetching results locally

From your laptop:
```bash
# One job
scp -r <user>@slurm.bgu.ac.il:~/pddl-copilot-experiments/results/slurm_gpt_oss_20b_tools_all_minimal_12345 \
       ~/personal/pddl-copilot-experiments/results/

# Everything from a run
rsync -av <user>@slurm.bgu.ac.il:~/pddl-copilot-experiments/results/slurm_* \
         ~/personal/pddl-copilot-experiments/results/
```

Then open `analyze_results.ipynb` — it picks up any `slurm_*` directory under
`results/` transparently.

## Cancelling jobs

```bash
scancel <jobid>                 # by id
scancel --name pddl_gpt-oss_20b_tools_all_minimal   # by name
scancel -u $USER                # nuke all of mine
scancel -t PENDING -u $USER     # only pending
```

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
there and update `--models`:
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
