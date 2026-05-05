---
name: analyzer
description: Aggregate, plot, and tabulate PDDL Copilot sweep results; render paper-style figures and the master pivot table; flag drift between an in-flight or follow-up sweep and a baseline. Read-only over results — never mutates experiment state. Pairs with the `cluster-ops` skill: cluster-ops gets results onto disk via `sync.sh` / `status.sh`; this skill turns them into tables, figures, and observations.
argument-hint: [aggregate | plot | table | drift | observations]
---

> User asked for: $ARGUMENTS — pick the matching recipe below.

## Why this skill exists

Triggers (so the skill auto-matches): "aggregate summaries", "plot results", "render figures", "make the paper table", "compare sweeps", "drift check", "is this run consistent with last week", "spot-check ongoing run", "what's the headline number", "summarize results".

Operations (queue queries, rsync, preflight, sacct postmortem) live in the `cluster-ops` skill. Analysis (Markdown tables, figures, drift detection) lives here. The split exists because the two have different consumers: cluster-ops is invoked while a sweep is queued/running and the user wants knobs to turn; analyzer is invoked after results land and the user wants numbers and pictures. Mixing the two surfaces in one skill made each unfocused.

This skill is **read-only** over experiment state — it never edits `run_experiment.py`, sbatch scripts, or result JSONs. It only emits Markdown / PNG / CSV / TeX into output dirs under each results root.

## Conventions

All paths below are relative to the repo root `/Users/omereliyahu/personal/pddl-copilot-experiments`.

- **Results root**: directories under `results/`, typically `results/cluster-YYYYMMDD/` (synced) or `results/full-cluster-run*/` (older). Each contains one `slurm_<model>_<think>_<cond>[_<jobid>]/` subdir per cell.
- **Per-cell layout**: `summary_*.json` (aggregated single_task; the legacy `chains` array is empty under the active flow as of 2026-05-05) is the canonical analysis input. `trials.jsonl` (per-trial JSONL, post 2026-05-01) is read by `drift_check.py` as a mid-sweep fallback when no `summary_*.json` exists yet.
- **Cell dirname shapes** (handled transparently by `parse_dirname`):
  - Cell-keyed (current, post 2026-05-01): `slurm_<model>_<think>_<cond>` — one dir per cell, resubmits accumulate timestamped summaries inside.
  - With-jobid (pre 2026-05-01): `slurm_<model>_<think>_<cond>_<jobid>` — one dir per submission.
  - Pre-think-axis legacy: `slurm_<model>_<cond>_<jobid>` — treated as `think=default` with a header warning.
- **Wilson 95% CIs** are the standard interval everywhere — never raw stderrs. Canonical impl: `pddl_eval.summary.wilson_ci`. `plot.py` and `drift_check.py` import it directly (each adds the repo root to `sys.path` once at import time so they remain runnable as standalone scripts from the repo root).

## Helper scripts (all live under `scripts/`)

### `scripts/aggregate.py` — summary.json → Markdown

Walks a results root (default: most recent `results/cluster-*` or `results/full-cluster-run*`), loads every `summary_*.json`, emits Markdown tables: single-task success-rate matrix and failure-reason totals.

```bash
python3 .claude/skills/analyzer/scripts/aggregate.py                            # auto-pick latest
python3 .claude/skills/analyzer/scripts/aggregate.py results/full-cluster-run1  # explicit
```

Legacy dirs (no `<think>` segment) are treated as `think=default` with a header warning.

### `scripts/plot.py` — paper-style plots

Auto-discovers series from dir names + summary meta; dynamically builds the SERIES list. Five figures in `<root>/plots/` (chain-phase fig2 + fig7 archived 2026-05-05; numeric IDs preserved):

- `fig1_single_task.png` — task × series success-rate bars with Wilson 95% CI whiskers
- `fig3_tool_selection.png` — classical vs numeric planner-selection rate on `solve`
- `fig4_failure_breakdown.png` — 1×5 grid of 100%-stacked failure-reason bars per task
- `fig5_domain_heatmap.png` — 1×5 heatmap grid, rows=series × cols=10 domains, cell=`k/n`
- `fig6_tool_adherence.png` — per-task `tool_selected_rate` with CI whiskers (with-tools only)

```bash
python3 .claude/skills/analyzer/scripts/plot.py                                     # auto-pick latest, plots → <root>/plots/
python3 .claude/skills/analyzer/scripts/plot.py results/full-cluster-run1           # explicit root
python3 .claude/skills/analyzer/scripts/plot.py results/cluster-20260501 --group-by think
python3 .claude/skills/analyzer/scripts/plot.py results/cluster-20260501 --figs 1,4,5  # subset
python3 .claude/skills/analyzer/scripts/plot.py results/cluster-20260501 --no-ci       # drop CI whiskers
python3 .claude/skills/analyzer/scripts/plot.py results/cluster-20260501 --merge       # pooled (model, think) → plots/merged/
```

`--figs` accepts `all` (default) or a comma list over `1, 3, 4, 5, 6` (chain figures `2`/`7` archived 2026-05-05; passing them is a hard error). `--no-ci` disables error bars on figs 1, 6. `--merge` pools `tool_filter × prompt_style` into a single `tools_merged` series per `(model, think)` (counts summed, Wilson CIs recomputed on the pooled n); `no-tools` series pass through unchanged.

### `scripts/plot_focused.py` — supervisor-friendly subset

Companion to `plot.py`: each focused figure answers ONE question with at most two bars per model. Outputs to `<root>/plots/focused/`.

```bash
python3 .claude/skills/analyzer/scripts/plot_focused.py                # auto-pick latest
python3 .claude/skills/analyzer/scripts/plot_focused.py <root> --figs 1,5,7
```

### `scripts/table.py` — master pivot (md + csv + tex)

One large pivot per run root covering all measured axes. Rows: `(model, think, tool_filter, prompt_style, cond, host, jobid)`. Columns: per-task `{succ% [lo–hi], tool_sel%, trunc%}` × 5 tasks + ST-mean + total n. Chain `L=2..5` columns were dropped 2026-05-05 with the chain-phase archive. The `.tex` output uses `booktabs` + `\multicolumn` group headers and is paper-appendix drop-in; the `.csv` flattens CI cells to three columns per task (`_succ`, `_ci_lo`, `_ci_hi`).

```bash
python3 .claude/skills/analyzer/scripts/table.py                                    # auto-pick latest
python3 .claude/skills/analyzer/scripts/table.py results/cluster-20260424           # explicit
python3 .claude/skills/analyzer/scripts/table.py results/cluster-20260424 --formats md,csv
python3 .claude/skills/analyzer/scripts/table.py results/cluster-20260424 --out /tmp/tables
```

Reuses `parse_dirname` / `load_summaries` / `host_tag` from `aggregate.py` (same dir).

### `scripts/drift_check.py` — flag cells diverging from a baseline

Compares a `--current` results root (in-flight or finished) against a `--baseline` root, aligns per-cell rows by `(model, think, cond, task)`, and flags any cell where the current point estimate falls outside the baseline's Wilson 95% CI. For each current cell, prefers the latest `summary_*.json`; falls back to aggregating `trials.jsonl` so mid-sweep cells (no `save_results` yet) still surface a current estimate.

```bash
python3 .claude/skills/analyzer/scripts/drift_check.py \
    --baseline results/cluster-20260427 \
    --current  results/cluster-20260501

# Bound to specific tasks:
python3 .claude/skills/analyzer/scripts/drift_check.py --baseline ... --current ... \
    --tasks solve validate_plan

# Suppress the "no drift detected" note (only print drifted rows):
python3 .claude/skills/analyzer/scripts/drift_check.py --baseline ... --current ... --quiet
```

Exit code is `1` if any `direction=below` rows surface (current notably worse than baseline), `0` otherwise. Use this in scripted gating.

## Recipes

### "Sync, aggregate, plot, table"

The standard end-of-sweep flow. Step 1 lives in `cluster-ops`; the rest in this skill.

1. `bash .claude/skills/cluster-ops/scripts/sync.sh` — rsync into `results/cluster-<today>/`.
2. `python3 .claude/skills/analyzer/scripts/aggregate.py <that-dir>` — print success-rate tables.
3. `python3 .claude/skills/analyzer/scripts/plot.py <that-dir>` — write the 7 PNG figures.
4. `python3 .claude/skills/analyzer/scripts/table.py <that-dir>` — write `tables/master.{md,csv,tex}` for the paper.
5. (Optional) `bash .claude/skills/cluster-ops/scripts/postmortem.sh` — sacct memory headroom; surface OOMs / near-`--time` jobs.
6. Report to user with the plot paths and 3–5 key numbers from the aggregate table. Frame against the paper headline (arXiv:2509.12987) when possible.

### "Is the in-flight sweep consistent with the last one?"

Drift gate before letting a long sweep continue chewing GPU-hours. Combines `cluster-ops` (status + sync) with this skill's `drift_check.py`.

1. `bash .claude/skills/cluster-ops/scripts/status.sh` — confirm jobs are actually running (not stuck, not OOM-killed).
2. `bash .claude/skills/cluster-ops/scripts/sync.sh results/cluster-<today>` — pull whatever cells have started writing. Cells without a `summary_*.json` yet still ship `trials.jsonl` (PR-30) so partial progress is captured.
3. Pick a baseline. The most reliable choice is the most recent prior **finished** sweep (e.g. `results/cluster-20260427/`). For paper-target gating, point at a curated reference dir.
4. `python3 .claude/skills/analyzer/scripts/drift_check.py --baseline <baseline> --current results/cluster-<today>`.
5. **Interpret the output:**
   - "No drift detected" → green light, sweep is on the same surface as baseline.
   - Rows with `direction=below` and `src=trials` → mid-sweep cells trending worse than baseline. Often the early samples just haven't covered the easier domains yet (sweep order is stable but per-trial rate varies). Re-run the drift check after another `sync.sh` pass; if `below` persists across two pulls separated by ≥30 min of further progress, surface to the user with the affected cells and the candidate causes (recent code change, model swap, num_ctx bump).
   - Rows with `direction=below` and `src=summary` → finished cells drifting from baseline. This is real divergence; report to the user with the cell list and offer hypotheses (compare `meta.host`, `meta.num_ctx`, model versions across baseline vs current).
   - Rows with `direction=above` → uniformly good news, surface as a positive headline.
6. If any `below` rows surface and aren't explained by sweep-order coverage, **stop** before the sweep finishes — every additional GPU-hour is potentially burning compute on a regression. The user can then `scancel` the affected cells or let them finish for diagnostics.

### "Pull observations and conclusions out of a sweep"

For a finished sweep, after step 1–4 of the standard flow:

1. Read `<root>/aggregate.md` (printed by `aggregate.py`) for the success-rate matrix and failure-reason totals.
2. Cross-reference against the paper headline (`reference_paper_and_repos.md` memory) — flag any cell ≥10pp off the paper's reported number. Always express deltas with Wilson CIs.
3. Look at `fig4_failure_breakdown.png` for failure-mode distribution; comment on shifts since the prior sweep (e.g. truncation rates falling after a num_predict bump).
4. Look at `fig5_domain_heatmap.png` for domain-stratified breakdowns; note any cliff (e.g. `validate_domain` succeeds on `counters` but fails on `blocksworld` / `depots` — the size-cliff in `ISS-008`).
5. When reporting, use the analysis-style memory's structure: paper-comparison framing, CIs on every percentage, implications. Avoid bare percentages without n.

## Things this skill does NOT do

- SSH to the cluster, submit/cancel jobs, refresh venvs — that's `cluster-ops`. Compose the two skills via the recipes above.
- Edit `run_experiment.py`, plugin code, sbatch scripts, or domain PDDLs — see CLAUDE.md routing rules.
- Open issues / PRs (model tool-use failures are findings to report in analysis, not ISS-### to file — see `tool-adherence = data` memory).
- Compute new metrics (e.g. cost-per-correct, latency percentiles) from scratch — extend `summary.summarize_single_task` in the runner if a new metric is needed across all sweeps; this skill consumes whatever the runner emits.
