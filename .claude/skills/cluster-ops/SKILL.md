---
name: cluster-ops
description: Operate the BGU ISE-CS-DT SLURM cluster for the PDDL copilot sweep — query queue + progress, submit/cancel jobs, sync results locally, aggregate summary JSONs, render paper-style plots, and diagnose cis-ollama reachability. Trigger on "cluster status", "what's running", "submit sweep", "cancel jobs", "sync results", "plot results", "aggregate summaries", "check ollama". Read this skill before running SSH/rsync/plot commands ad-hoc; it avoids re-deriving the grep patterns and result-dir conventions every session.
disable-model-invocation: true
argument-hint: [status | submit | cancel | sync | aggregate | plot | diag]
---

## Why this skill exists

Every session we re-derive the same SSH queue queries, `.out`-file grep patterns, rsync invocations, summary-JSON aggregations, and plot scripts. The cluster state is persistent but Claude's working set isn't. This skill pins the conventions in one place and exposes 5 short helper scripts.

Cluster & repo conventions that matter here:

- **Login node**: `omereliy@slurm.bgu.ac.il` — SSH is pre-authed for the user.
- **Remote repo root**: `~/pddl-copilot-experiments` on the login node.
- **Job submission**: `cluster-experimenting/submit_all.sh` submits 9 jobs in 5 dependency-chained waves per `(model, think_mode)` (`run_condition.sbatch:2–5`). Each SLURM job loops all 5 conditions sequentially, so one job = 5×(single-task+chain) phases.
- **Log file**: `cluster-experimenting/logs/pddl_<model>_<think>-<jobid>.out` (current) or `pddl_<model>_<cond>-<jobid>.out` (legacy, pre-2026-04-21).
- **Results dir**: `results/slurm_<model>_<think>_<cond>_<jobid>/` (current) or `results/slurm_<model>_<cond>_<jobid>/` (legacy).
- **Ollama server**: `https://cis-ollama.auth.ad.bgu.ac.il` — self-signed cert, always pass `-k` / `verify=False`.
- **Routing rules** (from `CLAUDE.md`): MCP-tool bugs → `../pddl-copilot/plugins/<name>/server/`. Scoring/prompt/GT → here. This skill is read-only over experiment state.

## Safety

- **Destructive ops require explicit user consent**: `scancel -u omereliy` (kills all jobs), `rm` on logs or results. Confirm with the user before each.
- **Never mutate** `run_experiment.py`, `run_condition.sbatch`, or `submit_all.sh` from this skill.
- **Preflight before submit**: run `scripts/diag.sh` first to confirm cis-ollama is reachable; submitting against an unreachable server wastes the wave.

## Helper scripts (all live under `scripts/`)

All paths below are relative to the repo root `/Users/omereliyahu/personal/pddl-copilot-experiments`.

### `scripts/status.sh` — cluster status snapshot

Prints a Markdown table of every running job with: condition index (which of 5), single-task progress `N/250`, chain progress `k/400`, and gateway-timeout percentage. Handles both legacy (one condition per job) and current (5 conditions per job) `.out` layouts.

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

Generalization of `results/full-cluster-run1/make_plots.py`. Auto-discovers series from dir names + summary meta; dynamically builds the SERIES list. Three figures (fig1 single-task, fig2 chain, fig3 planner-selection).

```bash
python3 .claude/skills/cluster-ops/scripts/plot.py                                  # auto-pick latest, plots → <root>/plots/
python3 .claude/skills/cluster-ops/scripts/plot.py results/full-cluster-run1        # explicit root
python3 .claude/skills/cluster-ops/scripts/plot.py results/cluster-20260501 --group-by think
```

### `scripts/diag.sh` — cis-ollama diagnostic

Reachability + loaded-models + TTLs. Optional cold-start ping to a named model.

```bash
bash .claude/skills/cluster-ops/scripts/diag.sh                # tags + ps
bash .claude/skills/cluster-ops/scripts/diag.sh gpt-oss:20b    # + small chat ping for latency
```

## Recipes

### "What's the cluster status?"

1. `bash .claude/skills/cluster-ops/scripts/status.sh` — table of all running jobs.
2. If any job shows `>20%` gateway-timeout rate → queue is saturated (`ISS-015`), suggest narrowing the submit or waiting for the current wave to finish.
3. If any job has been stuck at the same progress for >30 min → tail the `.out` file to see the last line and surface to the user.

### "Sync and plot the results"

1. `bash .claude/skills/cluster-ops/scripts/sync.sh` — rsync into `results/cluster-<today>/`.
2. `python3 .claude/skills/cluster-ops/scripts/aggregate.py <that-dir>` — print success-rate tables.
3. `python3 .claude/skills/cluster-ops/scripts/plot.py <that-dir>` — write PNGs.
4. Report to user with the plot paths and 3-5 key numbers.

### "Submit the sweep"

1. **Always** run `scripts/diag.sh` first. Halt if unreachable.
2. Preflight on the cluster: `ssh omereliy@slurm.bgu.ac.il 'cd ~/pddl-copilot-experiments && git pull && cd ~/pddl-copilot && git pull'`. Mention venv refresh only if `pddl-validator/requirements.txt` has changed.
3. `ssh omereliy@slurm.bgu.ac.il 'cd ~/pddl-copilot-experiments && bash cluster-experimenting/submit_all.sh --dry-run'` — user reviews.
4. If approved, same command without `--dry-run`.

### "Cancel jobs"

Specific IDs only unless the user explicitly says "kill everything":

```bash
ssh omereliy@slurm.bgu.ac.il 'scancel <id> <id> …'
```

`scancel -u omereliy` (nuke all) needs an explicit user request — it will terminate jobs that have been running for hours. Confirm first.

### "Debug a FAIL (exception) cluster"

The tag is overloaded (see `development/OPEN_ISSUES.md:ISS-015`, `ISS-016`). Classify by elapsed time in the `.out`:

- `1200.0s ± 0.5`: BGU reverse-proxy 504 (queue saturation / model eviction). `ISS-015`. Not a code bug.
- Any other elapsed: real MCP/chat failure, often FD-stdout pollution on tool use (`ISS-016`, fixed 2026-04-21 in `pddl-copilot` as `bb23ad0`).

The stderr lines added in commit `cea5ae0` (`run_experiment.py:951–971`) print the exception type + message live in the `.out`. For older jobs, the message only exists in `single_task_*.json`.

## Things this skill does NOT do

- Edit experiment code, plugin code, or sbatch scripts (those have their own routing rules).
- Launch an agent; everything here is direct tool calls.
- Resolve an `ISS-###`; it just references them in diagnostics.
