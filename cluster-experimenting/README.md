# Cluster-experimenting (BGU ISE-CS-DT)

SLURM sbatch scripts for running the `pddl-copilot-experiments` sweep on the
BGU ISE-CS-DT cluster (login node: `slurm.bgu.ac.il`).

**Single submit path: `submit_with_rtx.sh` → `run_condition_rtx.sbatch`.**
Each job allocates one dedicated `rtx_pro_6000:1` GPU (96 GB VRAM,
`--mem=80G`), runs an isolated Apptainer Ollama server on the compute
node, and loops `MODELS × THINK_MODES × CONDITIONS` in-process so weights
stay resident. No shared-server contention, no `afterok` chain — every
submission is self-contained on its own GPU node.

The cis-ollama (BGU shared-server) path was retired 2026-04-27 along with
its CPU-only `submit_all.sh` waves and `submit_120b_cis.sh` shortcut.
`gpt-oss:120b` is no longer in the active sweep — `Qwen3.5:35b` substitutes
for it in the large-model size band.

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
#    submit the full sweep packed into ONE rtx_pro_6000 job. The five models
#    (Qwen3.5:0.8B, gpt-oss:20b, Qwen3.5:27b, Qwen3.5:35b, gemma4:31b) peak
#    at ~30 GB resident, so MAX_LOADED_MODELS=1 sequencing keeps each
#    weight set on the GPU one at a time without VRAM blowup.
bash cluster-experimenting/submit_with_rtx.sh --all
```

Rerunning any step is safe: `git clone` can be replaced with `git -C <dir> pull`,
`setup_env.sh` detects an existing conda env and reuses it, and
`submit_with_rtx.sh` is idempotent (each submission gets a fresh
`$SLURM_JOBID` in the output path).

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

# Default: pack all 5 paper models in ONE rtx_pro_6000 job. Each model gets
# the full think × condition matrix (4 tools-conditions × 2 think modes = 8
# condition-runs); models run sequentially with MAX_LOADED_MODELS=1 evicting
# the previous weights. Wall: 4d allocation (well under main's 7d cap).
bash cluster-experimenting/submit_with_rtx.sh --all

# Per-model jobs (multiple positional args also pack into one job):
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B gpt-oss:20b Qwen3.5:27b

# Baseline-only no-tools sweep: 4-task discriminative matrix
# (solve + validate_*), packed in one job. --time scales with model count.
bash cluster-experimenting/submit_with_rtx.sh --all --no-tools

# Preview command without submitting.
bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b --dry-run
```

`--all` issues one packed job; per-model invocations submit independent
jobs that SLURM queues in parallel.

### GPU class

Default: `rtx_pro_6000:1` (96 GB VRAM, `--mem=80G`). Hard-pinned as the
sole self-deploy GPU class so peak VRAM and host RAM are constant across
the sweep. The 5-model pack peaks at `Qwen3.5:35b` (~30 GB), well inside
96 GB, leaving ample headroom for KV cache scaling.

`--gpu-type rtx_6000` is the opt-in escape hatch (48 GB VRAM, `--mem=48G`)
for use only when `rtx_pro_6000` is queue-saturated and the requested
models all fit. Default behaviour locks to `rtx_pro_6000` with no
auto-detection.

### `--no-tools` shorthand

`--no-tools` pins the run to the discriminative no-tools matrix:
- `CONDITIONS=no-tools` (one tools-off pass)
- `THINK_MODES=off` (no-tools/think=on is skipped by the matrix gate anyway)
- `TASKS="solve validate_domain validate_problem validate_plan"` —
  the four discriminative no-tools tasks. Negative fixtures (ISS-001) ride
  along the matching task automatically. `simulate` stays excluded — its
  keyword grader is non-discriminative regardless of negatives. Chains are
  skipped by the matrix gate.
- `--time` scales linearly with model count: 4h base + 4h per extra model
  (`--all --no-tools` → 20h for 5 models).

Conflicts with `--think-modes` (any value other than `off|default`) are
rejected.

### Models in the default sweep

The paper's `qwen3:0.6b` / `qwen3:4b` weren't a fit for the cluster's
historical Ollama-on-cluster inventory, so this cluster run is a
paper-variant, not a 1:1 reproduction. The five models in the default
`--all` pack — `Qwen3.5:0.8B`, `gpt-oss:20b`, `Qwen3.5:27b`,
`Qwen3.5:35b`, `gemma4:31b` — peak at ~30 GB resident on rtx_pro_6000
under `MAX_LOADED_MODELS=1` and sequence through one packed job.
`gpt-oss:120b` was substituted by `Qwen3.5:35b` in the large-model size
band (2026-04-27); it is no longer in the active sweep.

The rtx path pulls model weights from the public Ollama registry
(`docker://ollama/ollama` + `ollama pull`), so the model name has to be
valid there. The `.sif` container is cached at `$HOME/ollama.sif` after
the first run (~3 min cold).

## Conditions and think modes

### Conditions (3 active) — looped inside every job
- `no-tools`                    — baseline, no MCP tools exposed (matrix gate skips think=on cells; chain phase skipped)
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

| Field | Value | Rationale |
|---|---|---|
| `--partition` | `main` | rtx_pro_6000 (and the rtx_6000 opt-in) GRES are accessible from `main` |
| `--gpus` | `rtx_pro_6000:1` (default) or `rtx_6000:1` (opt-in) | One dedicated GPU per job; weights stay resident across the inner think × condition loop |
| `--time` | `2-00:00:00` (single-model) / `4-00:00:00` (multi-model `--all` pack) / `4h × N` (`--no-tools`, N = model count) | Single-model tools job ~10 h observed 2026-04-25. Multi-model pack scales linearly with model count, capped well below `main`'s 7d limit. No-tools 4-task matrix: ~4 h per model |
| `--mem` | `80G` (rtx_pro_6000 default) / `48G` (rtx_6000 opt-in) | Sized to GPU pool's host RAM expectation. `80G` cap on rtx_pro_6000 added 2026-04-27 per IT request (was 96G); host-RAM peak for the 5-model pack is well under both caps |
| `--cpus-per-task` | not set (cluster default `cpus-per-gpu`) | Removed 2026-04-27 per IT request; explicit `12` was depriving other users |
| Concurrency | `4` | Matches OLLAMA_NUM_PARALLEL=4; isolated per-job server so no contention argument applies |

## Monitoring

```bash
squeue --me                                  # all my running/pending jobs
sstat -j <jobid> --format=JobID,MaxRSS,MaxVMSize   # live memory usage
scontrol show job <jobid>                    # full job spec

# rtx self-deploy log
tail -f cluster-experimenting/logs/pddl_rtx_<model>-<jobid>.out

# Per-job ollama serve log on the compute node
ssh <node> tail -f /tmp/rtx-<jobid>/ollama-serve.log
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
| `results/slurm_<model>_<think>_<cond>_<jobid>/` | `run_experiment.py` JSON outputs (per-instance results, `summary_*.json`). Distinguish runs via `meta.host` recorded in `summary.json`. `results/` is gitignored. |
| `cluster-experimenting/logs/pddl_rtx_<model>-<jobid>.out` | rtx self-deploy log. Covers the full think × condition matrix in one file. Directory is gitignored. |

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
squeue --me -h -o '%i %j' | awk '$2 ~ /^pddl_rtx_/ {print $1}' | xargs --no-run-if-empty scancel
```

## Troubleshooting

**VRAM blowup after warmup (`exit 3`).** The runtime guard fired
because VRAM > 85% post-warmup. Likely cause: `OLLAMA_NUM_PARALLEL` × `num_ctx`
too high for the model. Check `run_condition_rtx.sbatch` — `NUM_PARALLEL=4`
and `num_ctx=8192` are sized for the default `--all` pack (peak ~30 GB on
rtx_pro_6000 96 GB). With multi-model packing, the guard skips the
offending model and continues with the next (sets non-zero exit at the end).

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
