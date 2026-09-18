---
name: cluster-ops
description: Operate the BGU CIS (formerly ISE-CS-DT) SLURM cluster for the PDDL copilot sweep — queue + pending-reason, submit/cancel, sync results, post-mortem completed jobs (right-size --mem from sacct/MaxRSS), prioritize pending cells via per-task Nice. Operations only; aggregation, plotting, tables, and drift detection live in the sibling `analyzer` skill.
argument-hint: [status | job | preflight | sync | postmortem | prioritize]
---

> User asked for: $ARGUMENTS — pick the matching recipe below.

## Why this skill exists

Triggers (so the skill auto-matches): "cluster status", "what's running", "why is it pending", "when will it run", "queue position", "queue rank", "ETA for job", "submit sweep", "cancel jobs", "sync results", "check vllm", "postmortem", "memory headroom", "prioritize", "deprioritize", "nice value", "let cell X finish first".

Every session we re-derive the same SSH queue queries, `.out`-file grep patterns, rsync invocations, and sacct memory-headroom recipes. The cluster state is persistent but Claude's working set isn't. This skill pins the conventions in one place and exposes six short helper scripts. Read it before running SSH/rsync commands ad-hoc.

**Skill boundary.** This skill owns cluster operations: queue inspection, submit/cancel, sync, preflight, postmortem, prioritization, and the destructive scenarios in `cleanup.md`. For result analysis (Markdown tables, paper plots, the master pivot, drift detection), delegate to the sibling `analyzer` skill. The two compose via the recipes below.

Cluster & repo conventions that matter here:

- **Login node**: `omereliy@slurm.bgu.ac.il` — SSH is pre-authed for the user.
- **Remote repo root**: `~/pddl-copilot-experiments` on the login node.
- **Job submission**:
  - `cluster-experimenting/submit_with_rtx.sh <model> [<model>...]` is the only submit path. GPU sbatch self-deploys a vLLM OpenAI server via Apptainer on a single dedicated GPU (default `rtx_6000:1` 48 GB; `--gpu-type rtx_pro_6000` is the opt-in 96 GB escape hatch). Each array task is one (model, think, cond) cell with weights resident throughout. `--all` expands to the 5 active models (`Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`) × think × cond. The `--no-tools` flag pins the run to the discriminative no-tools matrix (`CONDITIONS=no-tools`, `THINK_MODES={on,off}`, `--time=12:00:00`). A with-tools cell defaults to `--time=72:00:00`; an explicit `--time` always wins. Note: the header comment of `submit_with_rtx.sh` still calls `rtx_pro_6000` the default. The code (`GPU_TYPE="${GPU_TYPE:-rtx_6000}"`) is what runs, and it is what this skill documents.
  - Historical: the cis-ollama path was retired 2026-04-27. The Ollama backend was retired 2026-05-18, code removed 2026-05-23 (including `run_condition_rtx.sbatch`). The `cis-ollama.*` hostname still exists and now serves vLLM. `gpt-oss:120b` is no longer in the active sweep; the large-model band is held by `qwen3.6:35b` (A3B MoE).
- **Log file**: `cluster-experimenting/logs/pddl_rtx_<model>-<jobid>.out`. Legacy formats from earlier sweeps: `pddl_<model>_<think>-<jobid>.out` (cis path, retired) and `pddl_<model>_<cond>-<jobid>.out` (pre-2026-04-21).
- **Results dir**: `results/slurm_vllm_<model>_<think>_<cond>_<RUN_TAG>/` when the submit passes `--run-tag` (every run since 2026-05-26: `sweep5v2`, `sweep6`, `decoupled-thinkon`, `iss024d-e2e`, `ntster-h4`); bare `results/slurm_vllm_<model>_<think>_<cond>/` for older corpora. Cell-keyed, no jobid suffix. The `slurm_vllm_` prefix is kept from the era when it told vLLM cells apart from Ollama cells.
- **vLLM server**: per-job unique port on the allocated compute node (Apptainer-served, no TLS), exported as `LLM_BASE_URL` by `run_condition_vllm_rtx.sbatch`.
- **Routing rules** (from `CLAUDE.md`): MCP-tool bugs → `../pddl-copilot/plugins/<name>/server/`. Scoring/prompt/GT → here. This skill is read-only over experiment state.

## Safety

- **Destructive ops require explicit user consent**: `scancel -u omereliy` (kills all jobs), `rm` on logs or results. Confirm with the user before each.
- **Never mutate** `run_experiment.py`, `run_condition_vllm_rtx.sbatch`, or `submit_with_rtx.sh` from this skill.
- **Ask first**: get Omer's explicit go-ahead before any SSH / SLURM action (his connection is not always up). Local work needs no ping.
- **Preflight before submit**: run `scripts/preflight.sh` first — it pulls both repos, refreshes the plugin venvs, and surfaces GPU pool capacity in one shot. Submitting with a stale venv or against a saturated pool wastes time.

## Operations scripts (under `scripts/`)

All paths are relative to the repo root `/Users/omereliyahu/personal/pddl-copilot-experiments`. This skill retains six operations scripts: `status.sh`, `job.sh`, `sync.sh`, `preflight.sh`, `postmortem.sh`, `prioritize.sh`. The five analysis scripts (`aggregate.py`, `plot.py`, `plot_focused.py`, `table.py`, `drift_check.py`) moved to `.claude/skills/analyzer/scripts/` on 2026-05-01 — see the `analyzer` skill for those.

### `scripts/status.sh` — cluster status snapshot

**Tracks runs by run tag.** Since 2026-05-27 the script only builds its matrix from result dirs whose name ends in `_<RUN_TAG>`. The default tag is `sweep6` (the anonymized contamination corpus). To look at the canonical corpus, run `RUN_TAG=sweep5v2 bash status.sh`. Dirs without the suffix are listed in an "archived" footer and never enter the matrix.

One SSH call gathers `squeue` plus per-cell trial counts (computed cluster-side, returned as a small text blob; no result files are transferred, that is `sync.sh`). Local Python diffs against `~/.cache/cluster-ops-status-<RUN_TAG>.json` (one cache per run tag; override with the `STATE_FILE` env) and renders six sections, in this order:

1. **Header** — `## Status — ~Xh since last check` (or `first run` when the cache file is absent).
2. **What changed** — cells that flipped to ✓ this window and cells that newly started accumulating trials. Omitted if nothing changed.
3. **Per-cell progress matrix** — 5 active models × **6 logical columns**: `on/nt-neut`, `on/tl-neut`, `on/tl-ster`, then the same three for `off/`. `nt` = no-tools, `tl` = `tools_all_minimal`, `neut` = variants v11-13, `ster` = v14-16. Every column has the same **4560-trial denominator** (3 variants × 1520 trials). There is **no `nt-ster` column** in the default matrix: the sweep-6 plan does not run the no-tools steered arm. Each cell shows `N/D (P%)` plus an icon: ✓ done · ▶ growing · ⏸ has trials but no growth · `PD↻` pending rerun (count > 0) · `PD` pending fresh · `_-_` empty/no match · `n/a` absent by design.
4. **Δ since last status** — only cells whose count grew this window. Columns: `Cell | Prev → Now | Δ | pace (s/trial) | ETA`. Pace is window-averaged, so a cell that started mid-window looks slower than it is.
5. **Roll-up** — Done X/30 (5 models × 6 columns) · trial coverage % · running cells (job IDs) · watch list (cells where `elapsed + ETA > 0.9 × --time` budget).
6. **Queue** (compact) — running job IDs, pending grouped by REASON. See the REASON cheat-sheet below.

**Which sbatch cell fills which column:**

| Column    | Variants | Filled by |
|-----------|----------|-----------|
| `nt-neut` | v11-13   | the no-tools cell |
| `tl-neut` | v11-13   | the with-tools cell (same run as below) |
| `tl-ster` | v14-16   | the with-tools cell (it emits both arms into one `trials.jsonl`; the split is a row-level filter on `prompt_variant`) |

**Profiles** (each sets its own default run tag; an explicit `RUN_TAG=` env still wins):

| Flag | Default run tag | Board |
|------|-----------------|-------|
| (none) | `sweep6` | 5 models × 6 columns, Done X/30 |
| `--decoupled` | `decoupled-thinkon` | split-budget no-tools think=on sweep: 4 Qwens (gemma excluded, it has no `<think>`) × one column (`on/nt-neut`). 48 h wall for every cell. Record: `development/archive/decoupled/decoupled_run_handoff.md` |
| `--iss024d` | `iss024d-e2e` | ISS-024(d) with-tools resolver: 5 models × one column (`on/tl-neut`). The run wrote the full v11-16 bank; the board tracks the neutral half only. 72 h wall. Record: `development/reference/tool_call_vs_final_output_grading.md` |
| `--ntster` | `ntster-h4` | nt-ster H4 control: 3 models (`Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b`) × `off/nt-neut`, `off/nt-ster`, `on/nt-neut`, `on/nt-ster`. **The only profile with an `nt-ster` column**, because it is the only run that passed `--include-no-tools-steered`. gemma has no think=on leg by design, so that slot shows `n/a` and is left out of the roll-up. Walls: off 5 days, on 7 days. Record: `development/reference/ntster_h4_prereg.md` |

All four of those runs are finished; the profiles stay so a closed run can still be inspected.

The variant filters can be overridden with the `ACTIVE_VARIANTS_RE` (default `1[1-6]`) and `STEERED_VARIANTS_RE` (default `1[4-6]`) env vars.

The cache file is local-only scratch. `rm ~/.cache/cluster-ops-status-<RUN_TAG>.json` resets it (the next run is a "first run" with no Δ table).

Pending array tasks whose per-cell name hasn't materialised yet (still showing the parent template like `pddl_rtx_qwen3_6_35b`) are matched to that model's cells via the submit manifest, so `PD` icons appear before the array fans out.

**Output mode** auto-selects from stdout TTY-detect: ANSI-coloured aligned text in a real terminal, GitHub-flavoured markdown when piped or run via the Bash tool. Override with flags:

```bash
bash .claude/skills/cluster-ops/scripts/status.sh                 # auto (terminal in zsh, md in pipes)
bash .claude/skills/cluster-ops/scripts/status.sh --md            # force markdown (paste into chat)
bash .claude/skills/cluster-ops/scripts/status.sh --terminal      # force pretty (e.g. `… | less -R`)
bash .claude/skills/cluster-ops/scripts/status.sh --no-color      # strip ANSI from terminal mode
RUN_TAG=sweep5v2 bash .claude/skills/cluster-ops/scripts/status.sh   # canonical corpus instead of sweep6
bash .claude/skills/cluster-ops/scripts/status.sh --ntster           # one of the profiles above
bash .claude/skills/cluster-ops/scripts/status.sh --bench planbench  # PlanBench arm (model × task × config)
```

The two modes share data computation; they differ only in rendering, so the metrics, Δ window, and watch-list logic are identical.

**`--bench planbench`** delegates to `scripts/status_planbench.sh`, which renders a model × config matrix counting completed `task_*.json` files per cell (10 tasks expected per cell). Minimal v1: no Δ-table, no pace/ETA. Reads `results/planbench/slurm_<model>_<jobid>/` on the cluster. The native 5-task renderer is unchanged when `--bench 5task` (default) is used or no flag is passed.

If percentages look stuck, check for a tool-call parser mismatch in `vllm_lookup()` (`cluster-experimenting/lib/defaults.sh`) before suspecting a dead job.

### `scripts/job.sh` — single-job inspection

Use when `status.sh`'s sweep-matrix rendering doesn't fit — one-off probes / smoke sbatches with non-`pddl_*` names, or drilling into one specific cell of a sweep. One SSH call: `squeue -j <id>` + `sacct -j <id>` + (when STATE=PENDING) queue assessment + log tail (`cluster-experimenting/logs/*-<jobid>.out`, glob covers all naming patterns including probes). Markdown output, pastes cleanly into chat.

```bash
bash .claude/skills/cluster-ops/scripts/job.sh <jobid>                # squeue + sacct + queue assessment + last 25 log lines
bash .claude/skills/cluster-ops/scripts/job.sh <jobid> --lines 100    # custom tail size
bash .claude/skills/cluster-ops/scripts/job.sh <jobid> --no-log       # squeue/sacct + queue assessment only (skip log)
```

Handles three states gracefully: pending (squeue table + queue assessment, see below), running (live tail), completed/cancelled (squeue empty + helpful message, sacct shows terminal state with `.batch`/`.extern` step rows). Numeric-jobid guard catches the easy mistake of typing a script name instead.

**Queue assessment** (auto-renders when STATE=PENDING) answers "when does this move from PD to RUNNING?":

- **Priority** — `sprio` total priority value. Compare with peers to see whether you're scheduled to win contention.
- **Same-class queue rank** — `#N of M` pending jobs requesting the same GPU class as yours (derived from your job's `tres-per-job`). Filter is anchored on the colon (`gpu:rtx_6000:` ≠ `gpu:rtx_pro_6000:`) so the two classes don't cross-contaminate.
- **REASON breakdown for jobs ahead** — `JobArrayTaskLimit=6 Priority=2 …`. Crucial for interpreting rank: a high #N can still translate to a quick start if most ahead are blocked on `MaxGRESPerAccount`, `JobArrayTaskLimit`, or `Dependency` rather than competing for free GPUs.
- **SLURM earliest-slot estimate** — `<ISO> → best-case ~Xm` or `next backfill window (best-case lower bound, not a guarantee)`. Computed from SLURM's `StartTime` via `date -d`. The estimate is the earliest slot the backfill scheduler can verify *assuming our job is next in line*; higher-priority arrivals can leapfrog it, so it's a lower bound that frequently slips. When SLURM returns `Unknown`/`N/A`, prints "not yet computed — re-check in 1-2 min".

Caveats: neither rank nor SLURM's earliest-slot estimate is a real ETA. Rank counts jobs ahead by priority; many of them are blocked on QoS / array-throttle / dependencies and won't compete. The estimate is a backfill window, not a commitment. The honest signal is the *combination*: rank tells you who's ahead and why (REASON breakdown), and the estimate tells you when SLURM next plans to even look at your job. Non-GPU jobs skip the same-class filter and just get priority + estimate.

### `scripts/sync.sh` — pull results locally

`rsync -av --update` from the cluster's `results/slurm_*` AND `results/smoke/probe_*` into a local subdir under `results/`. Two rsync calls — sweep cells (must succeed) and probe outputs (`|| true` since they're often empty on a fresh cluster).

```bash
bash .claude/skills/cluster-ops/scripts/sync.sh                          # → results/sweep5-cluster-YYYYMMDD/ (the script's default name; a fresh dated mirror)
bash .claude/skills/cluster-ops/scripts/sync.sh results/my-custom-run    # → explicit dir
```

**A dated sync dir is a working mirror, never the corpus paper numbers are checked against.** Paper numbers are verified only against `results/sweep5v2-live` plus the `*_sweep6` cells; `results/sweep5-cluster-20260530` in particular is a stale partial mirror.

Reports per-class dir-count delta (sweep cells / probe outputs) so you can tell whether the probe added anything. Never deletes anything. To clear cancelled-job `.out` files on the remote side, tell the user explicitly what IDs you intend to delete and wait for confirmation before `ssh … rm`.

### `scripts/preflight.sh` — pre-submit cluster refresh + capacity

Run this before every `submit_with_rtx.sh`. Does, in one SSH call:

1. `git pull` both repos (this one + `../pddl-copilot`).
2. `pip install --upgrade -r requirements.txt` in each plugin's `.venv` — `setup_env.sh` deliberately skips existing venvs, so a pinned dependency bump in `../pddl-copilot/plugins/<plugin>/requirements.txt` is silently stale until something explicitly upgrades.
3. **GPU pool capacity** — `sinfo -p rtx6000 -t idle,mix` and same for `rtx_pro_6000`. The free-node count tells you whether `submit_with_rtx.sh` will queue immediately or sit in `PENDING(Resources)`. The default class is `rtx_6000`; if that pool is full and you can't wait, `--gpu-type rtx_pro_6000` is the opt-in escape hatch.
4. **`sres` snapshot** (Mar-26 guide §"Resources Usage") — one-glance cluster utilization view. `sres`'s "6000" column conflates `rtx_6000` and `rtx_pro_6000`, so trust step 3 for routing decisions.

```bash
bash .claude/skills/cluster-ops/scripts/preflight.sh
```

### `scripts/prioritize.sh` — bias which pending cells run next

Per-array-task `scontrol update Nice=N` driven by the manifest written at submit time (`cluster-experimenting/logs/<jobid>.cells.tsv`, idx<TAB>model<TAB>think<TAB>cond). Listed models keep `Nice=0`; every other pending cell gets `Nice=500` so the listed cells grab the next free GPU slot. Already-running tasks are skipped (Nice has no effect once dispatched).

Direction is one-way: negative Nice (raise priority above default) is admin-only on this cluster — verified by probe 2026-05-08 (`nice=100` accepted, `nice=-1000` denied). The only lever is *deprioritizing the rest*.

`submit_with_rtx.sh` already auto-applies this on a fresh `--all` submission (deprioritizes everything outside `PDDL_SLOW_MODELS`={gemma4:26b-a4b, qwen3.6:35b}, defined in `cluster-experimenting/lib/defaults.sh`). The skill script is the manual lever for: (a) `--continue-partial` / single-model resubmits where the auto-gate intentionally doesn't fire, and (b) mid-sweep when you want one specific high-progress cell to finish next so partial results are ready for analyst handoff.

```bash
bash .claude/skills/cluster-ops/scripts/prioritize.sh <jobid>                       # default slow set
bash .claude/skills/cluster-ops/scripts/prioritize.sh <jobid> gemma4:26b-a4b        # only gemma at Nice=0
bash .claude/skills/cluster-ops/scripts/prioritize.sh <jobid> --reset               # all cells back to Nice=0
bash .claude/skills/cluster-ops/scripts/prioritize.sh <jobid> --dry-run gemma4:26b-a4b  # show plan without applying
```

Idempotent — safe to re-run with a different keep-list. If the manifest is missing (job submitted before the prioritize feature landed), the script exits 2 and tells you so; in that case fall back to manual `scontrol update JobId=<master>_<idx> Nice=500` per `cluster-experimenting/README.md`, section "Throttle a running array post-submission".

If you want progress-aware ordering (rank pending cells by current `trials.jsonl` count and apply a Nice ladder so the closest-to-done cell wins ties), do it manually for now: pull progress with `status.sh`, then `scontrol update JobId=<master>_<idx> Nice=N` per task with N rising as progress falls (e.g. 0 / 100 / 200 / … / 700 — Nice values up to 700 are accepted unprivileged). Codifying it into the script is on the table when there's a second concrete need.

### `scripts/postmortem.sh` — completed-job introspection (`sacct`)

Closes the loop on the Mar-26 guide's "use minimum possible RAM" rule (§Allocating Resources). Pulls `sacct` for completed `pddl_*` jobs, merges parent + `.batch` step rows so MaxRSS lands in the same row as State/Elapsed/ExitCode, then computes a memory-headroom recommendation across the window.

Use it after a sweep finishes to: spot OOMs (`Comment` = `OOM-Kill`), find jobs that approached their `--time` budget, and right-size `--mem` for the next sweep without manual `sacct` per job.

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

This recipe spans both skills — sync + sacct here, aggregate + plot + table in `analyzer`.

1. `bash .claude/skills/cluster-ops/scripts/sync.sh` — rsync into `results/sweep5-cluster-<today>/` (or pass an explicit subdir).
2. Hand off to the `analyzer` skill's "Sync, aggregate, plot, table" recipe for steps 3–5 (`aggregate.py`, `plot.py`, `table.py` against the synced dir).
3. `bash .claude/skills/cluster-ops/scripts/postmortem.sh` — sacct table + memory-headroom recommendation. Surface any OOM rows or jobs that approached `--time` to the user.
4. Report to user with the plot paths (from analyzer) and 3–5 key numbers.

### "Is the in-flight sweep drifting?"

After a sweep is submitted, periodically verify it's not regressing vs a baseline before letting it eat more GPU-hours. The drift logic lives in `analyzer/scripts/drift_check.py`; the status + sync glue is here.

1. `bash .claude/skills/cluster-ops/scripts/status.sh` — confirm jobs are running (not stuck, not OOM-killed).
2. `bash .claude/skills/cluster-ops/scripts/sync.sh results/cluster-<today>` — pull whatever cells have started writing. Cells without a `summary_*.json` yet still ship `trials.jsonl`, which `drift_check.py` aggregates as a fallback.
3. Hand off to the `analyzer` skill's "Is the in-flight sweep consistent with the last one?" recipe — it picks a baseline and runs `drift_check.py`.

### "Submit the sweep"

No sweep is in flight or owed as of 2026-09-18 (`development/STATUS.md`). When one is needed, the production submit is `submit_full_sweep.sh`: three `submit_with_rtx.sh` calls (small Qwens at `--time 12:00:00`, `qwen3.6:35b` and `gemma4:26b-a4b` at `48:00:00`), 20 cells in total (5 models × 4 think×cond cells). Per-cell trial count is asymmetric: no-tools = 4560 (v11-13), `tools_all_minimal` = 9120 (v11-16, the with-tools cell emits both the neutral and the steered variants in one run). Pass `--run-tag <tag>` so the dirs get a suffix `status.sh` can track.

0. Get Omer's go-ahead (see Safety), and check for existing runs before recommending a rerun.
1. `bash .claude/skills/cluster-ops/scripts/preflight.sh` — pulls both repos, refreshes plugin venvs, surfaces GPU pool capacity for `rtx6000` and `rtx_pro_6000`. Halts on any failure.
2. Dry-run, then submit. `submit_full_sweep.sh` dispatches the production pack:
   ```bash
   ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
     bash cluster-experimenting/submit_full_sweep.sh --dry-run"
   ```
   For single-model pilots, fall back to `submit_with_rtx.sh <model>`.
3. If approved, same command without `--dry-run`.
4. **No-tools steered control arm** `(no-tools × v14-16)`: only a submit that passes `--include-no-tools-steered` writes it. The one run that did is the nt-ster H4 control (run tag `ntster-h4`, finished 2026-08-29); both arms land in one 9,120-row cell file and are split by `prompt_variant`. `status.sh --ntster` is the only board with an `nt-ster` column.

**`--no-tools` shorthand**: for the baseline-only run, `bash submit_with_rtx.sh --all --no-tools` pins `CONDITIONS=no-tools` and `THINK_MODES={on,off}`, with `--time=12:00:00` per cell.

**GPU class**: default `rtx_6000:1` (48 GB, `--mem=48G`). `--gpu-type rtx_pro_6000` is the opt-in 96 GB escape hatch (use only if `rtx_6000` is saturated). Think modes auto-select to `on off` (both run sequentially in one cell so weights stay resident); override with `--think-modes "default"` for a model that lacks the think kwarg.

**VRAM safety**: the sbatch serves with `--gpu-memory-utilization 0.85` (env `GPU_MEM_UTIL`), `--max-model-len 16384` and `--enable-prefix-caching`. It does **not** pass `--max-num-seqs`, so vLLM's own default applies. After the model loads, a guard aborts the cell if VRAM usage is above 85%. Hold the context at 16K: the 32K smoke fit in VRAM but raised format-parse failures.

### "Submit a one-off probe / smoke sbatch"

For sbatches that aren't sweep cells — vLLM probes, concurrency-saturation tests, smoke runs of an unrelated experiment, anything submitted as plain `sbatch <file>` rather than via `submit_with_rtx.sh`. The pattern:

1. Edit the sbatch locally on a feature branch. Commit + push (the cluster reads from `origin`, never your laptop).
2. SSH to the cluster, fast-forward the matching branch, submit:
   ```bash
   ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && \
     git fetch --quiet && git checkout <branch> && git pull --ff-only --quiet && \
     sbatch <path/to/your.sbatch>"
   ```
   Capture the printed `Submitted batch job <jobid>`. The `GPU Parameter Set ! Using GPU Partition` line under it is informational, not an error.
3. Inspect with `bash .claude/skills/cluster-ops/scripts/job.sh <jobid>` — pending state shows queue position + estimated start; running state shows live log tail.
4. When the probe completes, `bash .claude/skills/cluster-ops/scripts/sync.sh` already pulls `results/smoke/probe_*` alongside sweep cells, so the data lands under `results/sweep5-cluster-<today>/probe_*/` (the script's default dir name).

This path explicitly bypasses `submit_with_rtx.sh` (no CELLS_LIST manifest, no auto-prioritize, no `pddl_*` job-name) — fine because the recipe is for one-off experiments, not sweep cells. Don't use it for sweep work.

### "Prioritize a cell during a contended sweep"

The auto-prioritize logic in `submit_with_rtx.sh` covers the common case (fresh `--all` → heavy models grab slots first). For everything else:

1. `bash .claude/skills/cluster-ops/scripts/status.sh` — identify which pending cell you want to win the next free slot. Note its model.
2. Decide the keep-list. Examples:
   - "let qwen3.6:35b finish for the Friday meeting" → `prioritize.sh <jid> qwen3.6:35b`
   - "this resubmit, just keep the slow set up front" → `prioritize.sh <jid>` (default = `PDDL_SLOW_MODELS`)
   - "I want everything back to default after the contention clears" → `prioritize.sh <jid> --reset`
3. Run `--dry-run` first if you want to inspect the plan; then re-run without `--dry-run` to apply.

Caveats:
- Nice ordering only matters while tasks are PENDING. RUNNING tasks are past the scheduling decision; the script skips them and reports the count.
- If pending tasks are stuck on a node-specific reservation (REASON=`ReqNodeNotAvail`/`Reservation`), Nice ordering changes who-goes-first but doesn't dislodge the reservation. Check `status.sh`'s queue table and the Pending REASON cheat-sheet below.

### "Cancel jobs"

Specific IDs first; pipe `squeue → awk → scancel` is the safer middle ground when the user wants the whole sweep gone:

```bash
ssh omereliy@slurm.bgu.ac.il 'scancel <id> <id> …'                                                # specific jobs
ssh omereliy@slurm.bgu.ac.il "squeue --me -h -o '%i %j' | awk '\$2 ~ /^pddl_/ {print \$1}' \
                              | xargs --no-run-if-empty scancel"                                  # only the pddl sweep
```

**Do NOT use `scancel --name=pddl_*`** — verified 2026-04-25 on SLURM 25.11.4: `--name` is exact-string match (comma-separated list of literal names), not a glob/regex, so `pddl_*` silently matches zero jobs and the cancel is a no-op with no error. Use the squeue→awk→xargs pipe above to filter by name prefix.

`scancel -u omereliy` (nuke all, no name filter) needs an explicit user request — it will terminate jobs that have been running for hours and may not be sweep-related. Confirm first.

### "Clean up after a wrong submission / cancel"

Two distinct flavours — see **[`cleanup.md`](cleanup.md)** in this skill dir for full recipes, predicates, and the worked 2026-05-18 Qwen3.5:4B/9B Ollama-contamination example.

- **Misconfigured deployment** (wrong sbatch wrote rows to non-canonical paths). Historical; post 2026-05-23 there is only one sbatch (`run_condition_vllm_rtx.sbatch`), so backend-routing contamination is no longer possible. Parser-mismatch contamination (wrong `TOOL_CALL_PARSER` for a model) is still possible — detect via 0% tool-selection in `summary.json`, quarantine the affected `slurm_vllm_*` dirs to `checkpoints/cluster-<UTC-date>-<reason>/`, fix `vllm_lookup()` in `cluster-experimenting/lib/defaults.sh`, resubmit.
- **Cancel-induced error rows** (a `scancel`'d cell left `FR_*` rows in `trials.jsonl` that aren't real model errors). Back up to `trials.jsonl.bak-precleanup<N>-<UTC-timestamp>`, prune by **jid + failure_reason**, never by `failure_reason` alone.

### Pending REASON cheat sheet (Mar-26 guide §FAQ)

When `status.sh`'s Pending table shows a non-trivial REASON, here's what to do:

| REASON | What it means | Action |
|---|---|---|
| `Resources` | The requested partition pool is full. | Wait. If the default `rtx_6000` pool is saturated, `--gpu-type rtx_pro_6000` is the opt-in alternative. |
| `Priority` | Preempted by a Golden-Ticket QoS job (Mar-26 guide §"High Priority Jobs"). | Wait — usually clears in minutes. |
| `QOSMaxJobsPerUserLimit` | Per-user concurrent-job cap reached. | Wait for one of your other jobs to finish, or scancel a low-priority one. |
| `MaxGRESPerAccount` | Per-account GPU cap (relevant for high-priority QoS). | Wait. Not applicable on plain `--partition main`. |
| `PartitionTimeLimit` | `--time` exceeds partition's max (`main` ≤ 7 days). | Resubmit with a smaller `--time` passed to `submit_with_rtx.sh`. A running job's limit cannot be raised by a normal user. |

### "Debug a FAIL (exception) cluster"

Real MCP/chat failure, often FD-stdout pollution on tool use (`ISS-016`, fixed 2026-04-21 in `pddl-copilot` as `bb23ad0`).

The harness prints `[exception] <Type>: <message>` (and `[infra-skip] …`, `[scoring exception] …`) to stderr live, so they show up in the `.out` (`pddl_eval/runner.py`, the trial-error handler). The same text is stored per trial in `trials.jsonl`.

## Things this skill does NOT do

- Edit experiment code, plugin code, or sbatch scripts (those have their own routing rules).
- Launch an agent; everything here is direct tool calls.
- Resolve an `ISS-###`; it just references them in diagnostics.
