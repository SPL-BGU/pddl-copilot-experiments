---
name: analyzer
description: Aggregate, plot, and tabulate PDDL Copilot sweep results; render paper-style figures and the master pivot table; flag drift between an in-flight or follow-up sweep and a baseline. Read-only over results — never mutates experiment state. Pairs with the `cluster-ops` skill: cluster-ops gets results onto disk via `sync.sh` / `status.sh`; this skill turns them into tables, figures, and observations.
argument-hint: [aggregate | plot | table | drift | observations]
---

> User asked for: $ARGUMENTS — pick the matching recipe below.

## Why this skill exists

Triggers (so the skill auto-matches): "aggregate summaries", "plot results", "render figures", "make the paper table", "compare sweeps", "drift check", "is this run consistent with last week", "spot-check ongoing run", "what's the headline number", "summarize results".

**Skill boundary.** This skill is **read-only** over experiment state — it produces Markdown / PNG / CSV / TeX into output dirs under each results root and never edits `run_experiment.py`, sbatch scripts, or result JSONs. For queue queries, rsync, preflight, sacct postmortem, and destructive cleanup, delegate to the sibling `cluster-ops` skill.

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
python3 .claude/skills/analyzer/scripts/plot.py results/sweep5-live --by-arm           # four-arm split → plots/by_arm/
python3 .claude/skills/analyzer/scripts/plot.py results/sweep5-live --by-arm --arms nt-neut,tl-neut  # H1 isolation
python3 .claude/skills/analyzer/scripts/plot.py results/sweep5-live --by-arm --arms tl-neut,tl-ster  # H2 isolation
```

`--figs` accepts `all` (default) or a comma list over `1, 3, 4, 5, 6` (chain figures `2`/`7` archived 2026-05-05; passing them is a hard error). `--no-ci` disables error bars on figs 1, 6. `--merge` pools `tool_filter × prompt_style` into a single `tools_merged` series per `(model, think)` (counts summed, Wilson CIs recomputed on the pooled n); `no-tools` series pass through unchanged.

`--by-arm` (sweep-5 arm-aware mode) re-derives one series per `(cell, arm)` from each summary's `per_variant` dict. Arms come from `pddl_eval.summary.arm_for(with_tools, prompt_variant)`: `nt-neut` / `nt-ster` / `tl-neut` / `tl-ster` for sweep-5 (v11-v16); `nt-legacy` / `tl-legacy` for sweep-3/4 (v0-v10). Wilson CIs are recomputed on the pooled arm n. The `--arms` filter accepts a comma list of arm tags and is the H1/H2 isolation lever (development/sweep_prompt_bank_design.md §0 H1 → `nt-neut,tl-neut`; H2 → `tl-neut,tl-ster`). `fig4` (failure breakdown) auto-skips under `--by-arm` because per-variant cells in `summary_*.json` don't carry arm-tagged FR counts — use `build_deck.py` / `plot_focused.py` (which read trials.jsonl directly) for per-arm FR breakdowns.

### `scripts/plot_focused.py` — supervisor-friendly subset

Companion to `plot.py`: each focused figure answers ONE question with at most two bars per model. Outputs to `<root>/plots/focused/`.

```bash
python3 .claude/skills/analyzer/scripts/plot_focused.py                # auto-pick latest
python3 .claude/skills/analyzer/scripts/plot_focused.py <root> --figs 1,5,7
python3 .claude/skills/analyzer/scripts/plot_focused.py <root> --figs h1   # sweep-5 H1 isolation
```

`--figs h1` renders the sweep-5 H1 isolation per task: two bars per model (nt-neut vs tl-neut on `result_correct`) at byte-identical prompt content. Skipped silently on sweep-3/4 corpora (no v11-v13 records). Use the build_deck path or `plot.py --by-arm --arms tl-neut,tl-ster` for H2 (the H2 panel lives in plot.py because it carries the FR_WRONG_TOOL secondary outcome, not a one-question read).

### `scripts/table.py` — master pivot (md + csv + tex)

One large pivot per run root covering all measured axes. Rows: `(model, think, tool_filter, prompt_style, cond, arm, host, jobid)` — one per `(cell × arm)` so the sweep-5 four-arm matrix reads directly as 3 rows per `(model, think)` for a main-only sweep (nt-neut + tl-neut + tl-ster) or 4 with the control. Wilson 95% CIs are recomputed on the arm-pooled n. Columns: per-task `{succ% [lo–hi], tool_sel%, trunc%, out-med}` × 5 tasks + ST-mean + total n. `out-med` is the output-token median (sweep-5 H3, n-weighted across the arm's variants — see CHANGELOG 2026-05-24). Chain `L=2..5` columns were dropped 2026-05-05 with the chain-phase archive. The `.tex` output uses `booktabs` + `\multicolumn` group headers and is paper-appendix drop-in; the `.csv` flattens CI cells to three columns per task (`_succ`, `_ci_lo`, `_ci_hi`) and adds `_out_med`.

Sweep-3/4 corpora collapse to `*-legacy` arm rows, so the table renders unchanged from pre-arm-axis times (one row per cell, arm=`nt-legacy` or `tl-legacy`).

```bash
python3 .claude/skills/analyzer/scripts/table.py                                    # auto-pick latest
python3 .claude/skills/analyzer/scripts/table.py results/cluster-20260424           # explicit
python3 .claude/skills/analyzer/scripts/table.py results/cluster-20260424 --formats md,csv
python3 .claude/skills/analyzer/scripts/table.py results/cluster-20260424 --out /tmp/tables
```

Reuses `parse_dirname` / `load_summaries` / `host_tag` from `aggregate.py` (same dir).

### `scripts/filter_variants.py` — restrict trials.jsonl to a prompt-variant set

When the on-cluster `trials.jsonl` files mix variants across sweeps (e.g. sweep-5 cells resumed sweep-4 in place; v5/v6/v7 carry-over rows sit alongside v11..v16, and the sweep-5 control `(no-tools × v14-16)` lands in the same no-tools cell dirs as the main sweep), this script projects to one variant set and regenerates `summary_*.json` + `single_task_*.json` per cell into a fresh synthetic results root. Cell dirs whose names contain retired-axis substrings (`per-task`, `guided`) are skipped automatically. `--min-out` gates cells below a kept-trial threshold so partials don't enter a published checkpoint.

**Sweep-5 split is explicit, not implicit.** The `--arm` flag is the ergonomic front door: `--arm neutral` (v11-13) for H1 isolation, `--arm steered` (v14-16) for H2 / control, `--arm both` (default) for the full active set. Per-arm cells complete at 4560 trials; the with-tools full-active cell completes at 9120 (3 variants per arm × 1520 trials/variant × 2 arms = 9120).

```bash
# Sweep-5 full active set (default --arm both); useful for getting all rows
# in one place. Apply --arm-specific filters below for hypothesis-isolating
# checkpoints.
python3 .claude/skills/analyzer/scripts/filter_variants.py \
    --src sweep5-cluster-20260601 --dst sweep5-main \
    --model-glob 'slurm_vllm_*'

# Sweep-5 H1 isolation (neutral arm only — byte-identical prompt across
# no-tools and with-tools, the headline tool-utility comparison):
python3 .claude/skills/analyzer/scripts/filter_variants.py \
    --src sweep5-cluster-20260601 --dst sweep5-neutral \
    --model-glob 'slurm_vllm_*' --arm neutral --min-out 4560

# Sweep-5 H2 isolation (steered arm — measures the steering effect within
# with-tools; also use this filter to extract the 4th-arm control submit
# if its trials were merged into the main no-tools dirs):
python3 .claude/skills/analyzer/scripts/filter_variants.py \
    --src sweep5-cluster-20260601 --dst sweep5-steered \
    --model-glob 'slurm_vllm_*' --arm steered --min-out 4560

# Sweep-4 replay (historical — explicit --variants since --arm presets
# only encode sweep-5 indices):
python3 .claude/skills/analyzer/scripts/filter_variants.py \
    --src sweep4-cluster-20260519 --dst sweep4-v5-v7-first \
    --model-glob 'slurm_vllm_Qwen3_5_0_8B_*,slurm_vllm_qwen3_6_35b_*' \
    --variants 5,6,7 --min-out 4560
```

### `scripts/build_deck.py` — render a paper-talk PPTX from a filtered root

Reads a small `deck_config.py` (model order, captions, results path) and writes a self-contained ~16-slide deck on a sweep-5 corpus (~14 slides on a sweep-3/4 replay — H1/H2 slides are skipped when the relevant arms are absent): success-by-arm (off/on), H1 isolation slide (nt-neut vs tl-neut on result_correct at byte-identical prompts), H2 isolation slide (tl-neut vs tl-ster on tool_selected with FR_WRONG_TOOL share annotation), tool-selection per task, tool-selection vs successful-tool-use, confusion-matrix grids (nt-neut), validation-metric tables, simulate failure-proof slides, output-token note + 7 output-token slides (input tokens dropped 2026-05-24), and 2 latency slides. Chart functions and slide order are baked into the script — per-checkpoint customization is config-only. See `checkpoints/sweep5-live/deck_config.py` for the worked sweep-5 example (or `checkpoints/sweep4-v5-v7-first/deck_config.py` for the sweep-3/4 replay form).

**Arm-axis behavior.** `build_deck.py` re-keys each cell's trials.jsonl into `(model, think, arm)` buckets via `pddl_eval.summary.arm_for()`. A sweep-5 `tools_all_minimal` dir splits into two arm buckets (`tl-neut` from v11-13, `tl-ster` from v14-16); a sweep-3/4 dir collapses into one `tl-legacy` bucket. `ARM_ORDER` is derived from data unless the deck_config sets it explicitly; empty arms are dropped (no reserved slot). Input tokens are no longer plotted — `TOKEN_NOTE_BULLETS` documents the policy and the 2-turn structural multiplier.

```bash
python3 .claude/skills/analyzer/scripts/build_deck.py \
    --config checkpoints/<name>/deck_config.py \
    --out    checkpoints/<name>/pddl_copilot_<name>.pptx     # --out overrides config.OUT_PPTX
```

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

### "Checkpoint a sweep (in-flight or finished)"

End-to-end recipe that turns a cluster sync into a tracked `checkpoints/<name>/` artifact bundle: per-model trial zips, master pivot, plots, deck. Use when a sweep with a new prompt set lands its first complete cells and you want a snapshot to share with collaborators.

Variables: `<sync>` = synced cluster dirname (e.g. `sweep5-cluster-20260601`); `<name>` = checkpoint name (e.g. `sweep5-main`); `<variants>` = active prompt-variant ids (sweep-5 default: `11,12,13,14,15,16`; sweep-4 replay: `5,6,7`).

```bash
# 1. Sync from cluster
bash .claude/skills/cluster-ops/scripts/sync.sh results/<sync>

# 2. Filter to active variants + regen summaries. Sweep-5 has asymmetric
#    completion thresholds within a single dir: a complete with-tools cell
#    holds v11-13 (4560 trials) AND v14-16 (4560), so `--arm both` +
#    `--min-out 4560` would admit half-finished cells (4560-9119 trials).
#    Run the filter TWICE — once per arm with uniform 4560 — and merge
#    the resulting roots, or analyze the two arms independently.
python3 .claude/skills/analyzer/scripts/filter_variants.py \
    --src <sync> --dst <name>-neutral \
    --model-glob 'slurm_vllm_*' --arm neutral --min-out 4560
python3 .claude/skills/analyzer/scripts/filter_variants.py \
    --src <sync> --dst <name>-steered \
    --model-glob 'slurm_vllm_*' --arm steered --min-out 4560
# Sweep-4 replay: --variants 5,6,7 --min-out 4560 (single pass; no arm split).

# 3. Aggregate / plot / table on EACH filtered root. Repeat for <name>-neutral
#    and <name>-steered (steps below shown for one — substitute the other to
#    produce the paired checkpoint). For a sweep-4 replay, drop the suffix.
mkdir -p checkpoints/<name>/{plots,tables}
python3 .claude/skills/analyzer/scripts/aggregate.py     results/<name> > checkpoints/<name>/aggregate.md
python3 .claude/skills/analyzer/scripts/plot.py          results/<name>
python3 .claude/skills/analyzer/scripts/plot_focused.py  results/<name>
python3 .claude/skills/analyzer/scripts/table.py         results/<name>
cp -r results/<name>/plots/* checkpoints/<name>/plots/
cp    results/<name>/tables/* checkpoints/<name>/tables/

# 4. One trials.zip per model (sweep-4+ rule — see sweep4-v5-v7-first FOOTNOTE)
for model in $(ls results/<name> | sed -E 's/^slurm_(vllm_)?(.+)_(on|off)_.*$/\2/' | sort -u); do
    safe=$(echo "$model" | tr ':' '_' | tr '-' '_')
    (cd results/<name> && zip -r ../../checkpoints/<name>/${safe}_trials.zip \
        slurm_*${model}_*/{trials.jsonl,summary_*.json,single_task_*.json})
done

# 5. Deck — first checkpoint needs a deck_config.py; copy from a previous one and edit
#    MODEL_ORDER / MODEL_DISP / COND_ORDER / TITLE / SUBTITLE / SLIDE_CAPTIONS.
python3 .claude/skills/analyzer/scripts/build_deck.py \
    --config checkpoints/<name>/deck_config.py \
    --out    checkpoints/<name>/pddl_copilot_<name>.pptx
(cd checkpoints/<name> && zip pddl_copilot_<name>.pptx.zip pddl_copilot_<name>.pptx \
    && rm pddl_copilot_<name>.pptx)

# 6. Hand-write FOOTNOTE.md — scope, headline findings, caveats.
#    NO template; reference checkpoints/sweep4-v5-v7-first/FOOTNOTE.md for the shape.

# 7. Commit tracked files (zip + csv + tex + deck_config + the .pptx.zip).
#    .png and .md under checkpoints/** are gitignored by design — they rebuild from the zip + scripts.
```

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
