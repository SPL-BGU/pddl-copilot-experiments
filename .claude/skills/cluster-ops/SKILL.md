---
name: cluster-ops
description: Operate the BGU ISE-CS-DT SLURM cluster for the PDDL copilot sweep — queue + pending-reason, submit/cancel, sync results, aggregate summaries, render paper plots, post-mortem completed jobs (right-size --mem from sacct/MaxRSS).
argument-hint: [status | preflight | sync | aggregate | plot | table | postmortem]
---

> User asked for: $ARGUMENTS — pick the matching recipe below.

## Why this skill exists

Triggers (so the skill auto-matches): "cluster status", "what's running", "why is it pending", "submit sweep", "cancel jobs", "sync results", "plot results", "aggregate summaries", "check ollama", "postmortem", "memory headroom".

Every session we re-derive the same SSH queue queries, `.out`-file grep patterns, rsync invocations, summary-JSON aggregations, and plot scripts. The cluster state is persistent but Claude's working set isn't. This skill pins the conventions in one place and exposes 6 short helper scripts. Read it before running SSH/rsync/plot commands ad-hoc.

Cluster & repo conventions that matter here:

- **Login node**: `omereliy@slurm.bgu.ac.il` — SSH is pre-authed for the user.
- **Remote repo root**: `~/pddl-copilot-experiments` on the login node.
- **Job submission — single backend**:
  - `cluster-experimenting/submit_with_rtx.sh <model> [<model>...]` is the only submit path. GPU sbatch, self-deploys Ollama via Apptainer on a single dedicated GPU (default `rtx_pro_6000:1` 96 GB; `--gpu-type rtx_6000` is the opt-in 48 GB escape hatch). Loops `MODELS × THINK_MODES × CONDITIONS` in-process so weights stay resident. `--all` packs the 5 active models (Qwen3.5:0.8B, nemotron-3-nano:30b, qwen3.6:27b, qwen3.6:35b, gemma4:31b — post 2026-04-29 roster refresh) into one job under `MAX_LOADED_MODELS=1`. The `--no-tools` flag pins the run to the discriminative no-tools matrix (`CONDITIONS=no-tools`, `THINK_MODES=off`, `TASKS=solve+validate_*`, `--time=4h × N`).
  - The cis-ollama path (`submit_all.sh` waves, `submit_120b_cis.sh`, `run_condition.sbatch`) was retired 2026-04-27. `gpt-oss:120b` is no longer in the active sweep; the large-model band is held by `qwen3.6:35b` (A3B MoE) as of the 2026-04-29 refresh (previously `Qwen3.5:35b` since 2026-04-27).
- **Log file**: `cluster-experimenting/logs/pddl_rtx_<model>-<jobid>.out`. Legacy formats from earlier sweeps: `pddl_<model>_<think>-<jobid>.out` (cis path, retired) and `pddl_<model>_<cond>-<jobid>.out` (pre-2026-04-21).
- **Results dir**: `results/slurm_<model>_<think>_<cond>_<jobid>/` (schema unchanged — distinguish runs by the job's `meta.host` in `summary.json`).
- **Ollama server**: `http://localhost:11434` inside the allocated compute node (Apptainer-served, no TLS, unique port per job set by the sbatch).
- **Routing rules** (from `CLAUDE.md`): MCP-tool bugs → `../pddl-copilot/plugins/<name>/server/`. Scoring/prompt/GT → here. This skill is read-only over experiment state.

## Safety

- **Destructive ops require explicit user consent**: `scancel -u omereliy` (kills all jobs), `rm` on logs or results. Confirm with the user before each.
- **Never mutate** `run_experiment.py`, `run_condition_rtx.sbatch`, or `submit_with_rtx.sh` from this skill.
- **Preflight before submit**: run `scripts/preflight.sh` first — it pulls both repos, refreshes the plugin venvs, and surfaces GPU pool capacity in one shot. Submitting with a stale venv or against a saturated pool wastes time.

## Helper scripts (all live under `scripts/`)

All paths below are relative to the repo root `/Users/omereliyahu/personal/pddl-copilot-experiments`.

### `scripts/status.sh` — cluster status snapshot

Prints two Markdown tables:
- **Pending** — `job | name | reason | elapsed`. The `reason` column is `squeue %R` (e.g. `Resources`, `Priority`, `DependencyNeverSatisfied`). See the REASON cheat-sheet below for what each value means.
- **Running** — `job | phase | ST | chain | elapsed`. Phase shows condition index (which of 5), single-task progress `N/250`, and chain progress `k/400`. Handles both legacy (one condition per job) and current (5 conditions per job) `.out` layouts.

```bash
bash .claude/skills/cluster-ops/scripts/status.sh
```

### `scripts/sync.sh` — pull results locally

`rsync -av --update` from the cluster `results/slurm_*` into a local subdir under `results/`.

```bash
bash .claude/skills/cluster-ops/scripts/sync.sh                          # → results/cluster-YYYYMMDD/
bash .claude/skills/cluster-ops/scripts/sync.sh results/my-custom-run    # → explicit dir
```

Never deletes anything. To clear cancelled-job `.out` files on the remote side, tell the user explicitly what IDs you intend to delete and wait for confirmation before `ssh … rm`.

### `scripts/aggregate.py` — summary.json → Markdown

Walks a results root (default: the most recent `results/cluster-*` or `results/full-cluster-run*`), loads every `summary_*.json`, emits Markdown tables: single-task success-rate matrix, chain success-rate matrix, failure-reason totals.

```bash
python3 .claude/skills/cluster-ops/scripts/aggregate.py                            # auto-pick latest
python3 .claude/skills/cluster-ops/scripts/aggregate.py results/full-cluster-run1  # explicit
```

Legacy dirs (no `<think>` segment) are treated as `think=default` with a header warning.

### `scripts/plot.py` — paper-style plots

Auto-discovers series from dir names + summary meta; dynamically builds the SERIES list. Seven figures in `<root>/plots/`:

- `fig1_single_task.png` — task × series success-rate bars with Wilson 95% CI whiskers
- `fig2_chain.png` — chain length × series bars (chain=1 is ST mean), CI whiskers on L=2..5
- `fig3_tool_selection.png` — classical vs numeric planner-selection rate on `solve`
- `fig4_failure_breakdown.png` — 1×5 grid of 100%-stacked failure-reason bars per task
- `fig5_domain_heatmap.png` — 1×5 heatmap grid, rows=series × cols=10 domains, cell=`k/n`
- `fig6_tool_adherence.png` — per-task `tool_selected_rate` with CI whiskers (with-tools only)
- `fig7_chain_step_survival.png` — P(reach step k) per chain length L=2..5

```bash
python3 .claude/skills/cluster-ops/scripts/plot.py                                     # auto-pick latest, plots → <root>/plots/
python3 .claude/skills/cluster-ops/scripts/plot.py results/full-cluster-run1           # explicit root
python3 .claude/skills/cluster-ops/scripts/plot.py results/cluster-20260501 --group-by think
python3 .claude/skills/cluster-ops/scripts/plot.py results/cluster-20260501 --figs 1,4,5  # subset
python3 .claude/skills/cluster-ops/scripts/plot.py results/cluster-20260501 --no-ci       # drop CI whiskers
python3 .claude/skills/cluster-ops/scripts/plot.py results/cluster-20260501 --merge       # pooled (model, think) → plots/merged/
```

`--figs` accepts `all` (default) or a comma list over `1..7`. `--no-ci` disables error bars on figs 1, 2, 6. `--merge` pools `tool_filter × prompt_style` into a single `tools_merged` series per `(model, think)` (counts summed, Wilson CIs recomputed on the pooled n); `no-tools` series pass through unchanged so they remain as the baseline next to each merged tools row. Output → `<root>/plots/merged/` — run it alongside the default invocation to get both views.

### `scripts/table.py` — master pivot (md + csv + tex)

Emits one large pivot per run root covering all measured axes. Rows: `(model, think, tool_filter, prompt_style, cond, host, jobid)`. Columns: per-task `{succ% [lo–hi], tool_sel%, trunc%}` × 5 tasks + chain `succ% [lo–hi]` × `L=2..5` + ST-mean + total n. The `.tex` output uses `booktabs` + `\multicolumn` group headers and is paper-appendix drop-in; the `.csv` flattens CI cells to three columns per task (`_succ`, `_ci_lo`, `_ci_hi`) for downstream analysis.

```bash
python3 .claude/skills/cluster-ops/scripts/table.py                                    # auto-pick latest, writes <root>/tables/master.{md,csv,tex}
python3 .claude/skills/cluster-ops/scripts/table.py results/cluster-20260424           # explicit root
python3 .claude/skills/cluster-ops/scripts/table.py results/cluster-20260424 --formats md,csv
python3 .claude/skills/cluster-ops/scripts/table.py results/cluster-20260424 --out /tmp/tables
```

Reuses `parse_dirname`/`load_summaries`/`host_tag` from `aggregate.py` (same dir) — no duplicated logic.

### `scripts/preflight.sh` — pre-submit cluster refresh + capacity

Run this before every `submit_with_rtx.sh`. Does, in one SSH call:

1. `git pull` both repos (this one + `../pddl-copilot`).
2. `pip install --upgrade -r requirements.txt` in each plugin's `.venv` — `setup_env.sh` deliberately skips existing venvs, so a pinned dependency bump in `../pddl-copilot/plugins/<plugin>/requirements.txt` is silently stale until something explicitly upgrades.
3. **GPU pool capacity** — `sinfo -p rtx6000 -t idle,mix` and same for `rtx_pro_6000`. The free-node count tells you whether `submit_with_rtx.sh` will queue immediately or sit in `PENDING(Resources)`. If `rtx_pro_6000` is 0/6 and you can't wait, `--gpu-type rtx_6000` is the opt-in escape hatch.
4. **`sres` snapshot** (PDF p10) — one-glance cluster utilization view. `sres`'s "6000" column conflates `rtx_6000` and `rtx_pro_6000`, so trust step 3 for routing decisions.

```bash
bash .claude/skills/cluster-ops/scripts/preflight.sh
```

### `scripts/postmortem.sh` — completed-job introspection (`sacct`)

Closes the loop on PDF p9's "use minimum possible RAM" rule. Pulls `sacct` for completed `pddl_*` jobs, merges parent + `.batch` step rows so MaxRSS lands in the same row as State/Elapsed/ExitCode, then computes a memory-headroom recommendation across the window.

Use it after a sweep finishes to: spot OOMs (`Comment` = `OOM-Kill`), find jobs that approached `--time` (Elapsed close to 3-00:00:00), and right-size `--mem` for the next sweep without manual `sacct` per job.

```bash
bash .claude/skills/cluster-ops/scripts/postmortem.sh                          # last 7 days, all pddl_* jobs
bash .claude/skills/cluster-ops/scripts/postmortem.sh --since 2026-04-22       # specific window
bash .claude/skills/cluster-ops/scripts/postmortem.sh --jobs 17130166,17130167 # specific job ids
```

## Recipes

### "What's the cluster status?"

1. `bash .claude/skills/cluster-ops/scripts/status.sh` — table of all running jobs.
2. If any job has been stuck at the same progress for >30 min → tail the `.out` file to see the last line and surface to the user:
   ```bash
   ssh omereliy@slurm.bgu.ac.il 'tail -50 pddl-copilot-experiments/cluster-experimenting/logs/*-<jobid>.out'
   ```

### "Sync and plot the results"

1. `bash .claude/skills/cluster-ops/scripts/sync.sh` — rsync into `results/cluster-<today>/`.
2. `python3 .claude/skills/cluster-ops/scripts/aggregate.py <that-dir>` — print success-rate tables.
3. `python3 .claude/skills/cluster-ops/scripts/plot.py <that-dir>` — write the 7 PNG figures.
4. `python3 .claude/skills/cluster-ops/scripts/table.py <that-dir>` — write `tables/master.{md,csv,tex}` for the paper.
5. `bash .claude/skills/cluster-ops/scripts/postmortem.sh` — sacct table + memory-headroom recommendation. Surface any OOM rows or jobs that approached `--time` to the user.
6. Report to user with the plot paths and 3-5 key numbers.

### "Submit the sweep"

The path validated 2026-04-25: bulk jobs queued in 8 seconds, full 5-model sweep packed in ONE rtx_pro_6000 job under `MAX_LOADED_MODELS=1`.

1. `bash .claude/skills/cluster-ops/scripts/preflight.sh` — pulls both repos, refreshes plugin venvs, surfaces GPU pool capacity for `rtx6000` and `rtx_pro_6000`. Halts on any failure.
2. Dry-run, then submit. `--all` packs the 5 active models into one job; per-model invocations submit independent jobs that queue in parallel:
   ```bash
   ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
     bash cluster-experimenting/submit_with_rtx.sh --all --dry-run"
   ```
3. If approved, same command without `--dry-run`.

**`--no-tools` shorthand**: for the baseline-only run, `bash submit_with_rtx.sh --all --no-tools` pins `CONDITIONS=no-tools`, `THINK_MODES=off`, `TASKS="solve validate_domain validate_problem validate_plan"`, and scales `--time` linearly with model count (4h base + 4h per extra model).

**GPU class**: default `rtx_pro_6000:1` (96 GB, `--mem=80G`). The sweep is hard-pinned to this class for consistency; `--gpu-type rtx_6000` is the opt-in 48 GB escape hatch (use only if `rtx_pro_6000` is saturated). Think modes auto-select to `on off` (both run sequentially in one job so weights stay resident); override with `--think-modes "default"` for a model that lacks the think kwarg.

**VRAM safety**: the sbatch pins `OLLAMA_NUM_PARALLEL=4`, `MAX_LOADED_MODELS=1`, `CONTEXT_LENGTH=8192`. After warmup, a runtime guard aborts the offending model if VRAM usage > 85% (loop continues with the next model). Never raise NUM_PARALLEL without re-measuring KV-cache allocation.

### "Cancel jobs"

Specific IDs first; pipe `squeue → awk → scancel` is the safer middle ground when the user wants the whole sweep gone:

```bash
ssh omereliy@slurm.bgu.ac.il 'scancel <id> <id> …'                                                # specific jobs
ssh omereliy@slurm.bgu.ac.il "squeue --me -h -o '%i %j' | awk '\$2 ~ /^pddl_/ {print \$1}' \
                              | xargs --no-run-if-empty scancel"                                  # only the pddl sweep
```

**Do NOT use `scancel --name=pddl_*`** — verified 2026-04-25 on SLURM 25.11.4: `--name` is exact-string match (comma-separated list of literal names), not a glob/regex, so `pddl_*` silently matches zero jobs and the cancel is a no-op with no error. Use the squeue→awk→xargs pipe above to filter by name prefix.

`scancel -u omereliy` (nuke all, no name filter) needs an explicit user request — it will terminate jobs that have been running for hours and may not be sweep-related. Confirm first.

### Pending REASON cheat sheet (PDF p43–44)

When `status.sh`'s Pending table shows a non-trivial REASON, here's what to do:

| REASON | What it means | Action |
|---|---|---|
| `Resources` | The requested partition pool is full. | Wait, or fall back to `--gpu-type rtx_6000` if `rtx_pro_6000` is saturated and the model set fits 48 GB. |
| `Priority` | Preempted by a Golden-Ticket QoS job (PDF p14). | Wait — usually clears in minutes. |
| `QOSMaxJobsPerUserLimit` | Per-user concurrent-job cap reached. | Wait for one of your other jobs to finish, or scancel a low-priority one. |
| `MaxGRESPerAccount` | Per-account GPU cap (relevant for high-priority QoS). | Wait. Not applicable on plain `--partition main`. |
| `PartitionTimeLimit` | `--time` exceeds partition's max (`main` ≤ 7 days). | Edit the `#SBATCH --time` line in the sbatch and resubmit. |

### "Debug a FAIL (exception) cluster"

Real MCP/chat failure, often FD-stdout pollution on tool use (`ISS-016`, fixed 2026-04-21 in `pddl-copilot` as `bb23ad0`).

The stderr lines added in commit `cea5ae0` (`run_experiment.py:951–971`) print the exception type + message live in the `.out`. For older jobs, the message only exists in `single_task_*.json`.

## Things this skill does NOT do

- Edit experiment code, plugin code, or sbatch scripts (those have their own routing rules).
- Launch an agent; everything here is direct tool calls.
- Resolve an `ISS-###`; it just references them in diagnostics.
