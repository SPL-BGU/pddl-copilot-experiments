# Submission strategy proposal — under the Mar-26 BGU CIS guide

**Author:** fresh agent, 2026-04-30
**Status:** PROPOSAL — awaiting user review before implementation.
**Supersedes once approved:** the packed-job rationale in CHANGELOG 2026-04-27 ("cis-ollama path retired; sole submission is `rtx_pro_6000:1` self-deploy").

---

## 1. Context

The current topology — one packed `rtx_pro_6000:1` job that runs all 4 models × {on, off} × 3 conditions sequentially under `MAX_LOADED_MODELS=1` — was right at the time it was set (CHANGELOG 2026-04-27, when packing replaced 5 separate cis-ollama waves to eliminate shared-server eviction thrashing). With the cis path retired and each job now owning its GPU node end-to-end, the original packing rationale ("share apptainer/serve startup, dodge eviction") is paying ~20 min of saved warmup against a ~140 h serialized wall and a single-point-of-failure across the entire sweep. The Mar-26 guide formalizes the two idioms that fix exactly this: `#SBATCH --array=0-N-1` for trivially-parallel per-model fan-out, and `--tmp=Ng`/`$SLURM_SCRATCH_DIR` for explicit per-job scratch on the compute-node SSD. Neither is novelty — both are guide-documented and our hard constraints (1 GPU/job, IT mem caps, results-schema stability) carry through unchanged. Everything else in the topology (partition pin to `main`, GRES = `rtx_pro_6000:1` default, 80 GB cap, no `--cpus-per-task`, runtime VRAM guard, port-collision fallback) is correct under the new guide and stays.

## 2. Recommendations per lens

### Lens A — Partition routing → KEEP

Stay on `--partition=main` with `--gpus=rtx_pro_6000:1`. The Mar-26 guide is unambiguous: *"When no QoS is needed, do not use partitions other than 'main'. When using QoS, do not use partition 'main'."* (§High-Priority Jobs). Golden Tickets are disabled in `main`, and our group has no documented QoS rights on `rtx_pro_6000` (the QoS partition list is `gtx1080`/`rtx2080`/`rtx3090`/`rtx6000` — `rtx_pro_6000` GRES is reachable from `main` only). Routing smoke runs to `rtx3090` QoS would be cheaper if we had rights there, but using a non-`main` partition without QoS is explicitly disallowed. CPU-only post-processing is N/A — aggregation runs on the laptop or in-job, not as a separate cluster task. The `--qos course --part course` rename and the rtx_6000:2 multi-GPU erratum are noted in `reference_bgu_cluster_guide_mar26.md` for future reference but don't apply to the active sweep.

### Lens B — Runtime efficiency → CHANGE (job array + explicit scratch)

**Adopt SLURM job arrays for `--all`.** Replace the recursive packed-job invocation in `submit_with_rtx.sh:131-143` with a single `sbatch --array=0-N-1` submission. Each array task picks its model by `SLURM_ARRAY_TASK_ID`, runs its own apptainer/serve + warmup + THINK × COND loop, and writes to its own `slurm_<model>_<think>_<cond>_<jobid>/` dir. Wall-clock impact: max-of-tasks ≈ 35 h (single-model post-2026-04-29 cap-bump wall), down from the current 6-day packed estimate — a ~4× speedup when the rtx_pro_6000 pool has ≥2 free slots, with graceful degradation when it doesn't (worst case ≈ current packed time + N apptainer pulls). Crucially this **improves** alignment with `feedback_experiment_pipeline_safety.md`, not violates it: that memory's "strict serialization" rule was about `cis-ollama`'s shared `MAX_LOADED_MODELS=2` eviction thrashing, not throughput per se. With self-deploy GPUs there is no shared resource, so per-model independence is exactly what halt-on-failure semantics want — a node fault or VRAM-guard trip in one task no longer wastes the other models' wall. Per-task `$SLURM_JOBID` continues to disambiguate output dirs; `meta.host` already varies per node in `aggregate.py::host_tag()`, no aggregator change needed.

**Add `#SBATCH --tmp=50G` and switch `WORK` to `$SLURM_SCRATCH_DIR`.** The Mar-26 guide §"Working with the Compute Node's SSD Drive" documents `--tmp=Ng` as the canonical way to request `/scratch/$USER/$JOBID`; we currently use `/tmp/rtx-$SLURM_JOBID`, which is node-local but isn't covered by `--tmp` capacity guarantees and varies per node-type. 50 G covers `ollama.sif` (~3 GB) plus the largest single model (~26 GB for `gemma4:31b` in array mode where each task holds one model) with comfortable headroom. Existing `trap … rm -rf "$WORK"` is preserved; the guide notes scratch is auto-erased on job exit anyway, so this becomes belt-and-suspenders. Fallback path (`${SLURM_SCRATCH_DIR:-/tmp/rtx-$SLURM_JOBID}`) keeps the script working if `--tmp` isn't honored on a given node-type, so no risk of regression.

**Decline: `afterok` chains.** Today there are no inter-job waves to chain. Once `--all` is an array of independent tasks, halt-on-failure is automatic per-task — chaining would only make sense if downstream aggregation depended on all tasks finishing, which it doesn't (each task's results dir is independently analyzable).

**Decline: `scontrol update JobId Nice=N` automation.** Worth documenting in `cluster-experimenting/README.md` as a politeness lever ("if your array is queue-saturating other users' jobs, deprioritize with `scontrol update JobId=<master> Nice=500`"), but auto-applying Nice without queue-state awareness would either be unconditional (penalizing us when the queue is empty) or require a `sres`/`squeue` probe (over-engineered). User-call-it-when-needed beats auto-apply.

**Decline: `/dev/shm` mitigations.** Apptainer ollama caches under `/tmp` (now `$SLURM_SCRATCH_DIR`), not `/dev/shm`. The PyTorch DataLoader hazard is documented for the future Gymnasium/PPO track but is N/A for the current harness.

**Decline: multi-GPU on one node** (`rtx_6000:2 --cpus-per-gpu=8`). The array model already gets per-model parallelism across separate nodes; multi-GPU adds CUDA_VISIBLE_DEVICES routing + per-GPU port management without a wall-clock advantage over the array.

### Lens C — Deployment → KEEP, with one cosmetic nit

The `apptainer build … docker://ollama/ollama` + `apptainer exec --nv --bind` recipe is byte-aligned with the Mar-26 guide §Apptainer. `$HOME/ollama.sif` cache, per-job port (`11400 + JOBID%100`) with `ss -Hltn` collision fallback, and the 85% VRAM runtime guard all remain correct under the new guide. Three sub-decisions:

- **Persistent model cache** (`$HOME/.ollama-cache/` instead of per-job `$WORK/models`). **Defer.** With arrays, each of 4 tasks pays ~2-3 min for `ollama pull` against the public registry — ~12 min total across the sweep, < 1 % of wall. Persistence buys back ~12 min at the cost of $HOME storage churn (≥26 GB) and a stale-tag failure mode if upstream re-tags a model. Revisit only if we scale to many sweeps/day.
- **Port-collision policy.** Current 11400-11599 with `ss -Hltn` fallback handles array tasks landing on the same node (rare under SLURM's default spread placement, but possible). The 200-port range gives ample headroom; no change.
- **Cosmetic: drop `--nv` from `apptainer build`** (line 126). `--nv` is a runtime flag for `exec`; on `build` it's a harmless no-op but isn't in the guide example. Optional one-line cleanup if we're touching the file anyway; not load-bearing.

## 3. Concrete diff sketch

If approved, the implementation is roughly:

**`cluster-experimenting/submit_with_rtx.sh`**
- L131-143 (`if [ "$ALL" -eq 1 ]`): instead of recursing into the multi-positional packing path, set `MODELS=(Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b)` directly and fall through to the (now array-aware) sbatch construction.
- L196-205 (`TIME_ARG` for multi-model): drop the `--time=6-00:00:00` packed-job branch. Use single-model wall (`--time=2-00:00:00`) per array task. Multi-positional invocation (e.g. `submit_with_rtx.sh m1 m2 m3`) becomes the array path too — no separate packed branch.
- L257-263 (sbatch cmd): when `${#MODELS[@]} > 1`, pass `--array=0-$((${#MODELS[@]}-1))`. Pass `MODELS_LIST="${MODELS[*]}"` via `--export` so the sbatch can index by `$SLURM_ARRAY_TASK_ID`. Single-model invocations skip `--array` (no behaviour change for `submit_with_rtx.sh Qwen3.5:0.8B`).
- L226-234 (`JOB_NAME`): for arrays, use `pddl_rtx_array_${ALL_TAG}` so master + tasks share a clean prefix (`%x-%A_%a.out` resolves correctly).
- Update the `--no-tools` time scaling (L188-189) consistently — under arrays, no-tools wall is 6 h per task, not 6 h × N.

**`cluster-experimenting/run_condition_rtx.sbatch`**
- L75-80 (`#SBATCH` block): add `#SBATCH --tmp=50G`. Output stays at `cluster-experimenting/logs/%x-%J.out` (each array task gets its own `$SLURM_JOBID`; that already disambiguates).
- L91-104 (model parsing): if `SLURM_ARRAY_TASK_ID` is set and `MODELS_LIST` is exported, set `MODEL=$(echo "$MODELS_LIST" | awk -v i=$((SLURM_ARRAY_TASK_ID+1)) '{print $i}')` and treat as single-MODEL run (drop the `for MODEL in $MODELS` loop body for this one iteration). When not in array mode, current MODELS-loop behaviour preserved verbatim.
- L115-118 (`WORK` setup): change `WORK=/tmp/rtx-$SLURM_JOBID` → `export SLURM_SCRATCH_DIR="${SLURM_SCRATCH_DIR:-/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}}"; WORK="${SLURM_SCRATCH_DIR}/rtx-work"; mkdir -p "$WORK/models"`. Keep the cleanup `trap` unchanged.
- L126 (cosmetic): `apptainer build --nv --force` → `apptainer build --force` (drop `--nv` from build).

**`cluster-experimenting/README.md`**
- §Quickstart / §Submission: update the "ONE rtx_pro_6000 job" language to "a 4-task array, one model per task. Wall ≈ 35 h max-of-tasks vs ~6 d for the prior packed model." Keep per-model invocation docs unchanged (those were always 1 GPU/job and stay that way).
- §Resource profile table: add row for `--tmp=50G` with rationale.
- §Cancelling jobs: add `scancel <master>` cancels the whole array; `scancel <master>_<task>` cancels one task. Add the `scontrol update JobId=<id> Nice=500` politeness recipe.
- §Where things go: clarify that with arrays, each task's `$SLURM_JOBID` is unique, so `slurm_*_<jobid>/` dirs continue to be one-per-(model,think,cond) without collisions.

**No changes to:** `run_experiment.py`, `pddl_eval/`, `domains/`, `EXPERIMENTS_FLOW.md` §1-9 (methodology and result schema), `../pddl-copilot/`, project memories, MEMORY.md.

## 4. Reproducibility impact

**Pre-existing results: fully comparable.** No changes to scoring (`pddl_eval/scoring.py`), prompts (`PROMPT_TEMPLATES`, `PROMPT_STYLE_CHOICES`), schemas (`pddl_eval/schemas.py`), tool contracts (EXPERIMENTS_FLOW §8), result-file shape (§9), or tasks/conditions matrix. `results/cluster-*` and `results/full-cluster-run*` dirs from prior sweeps remain directly comparable to post-change sweeps cell-for-cell.

**`meta.host` distribution shift (cosmetic).** Today, all 4 models in a packed job record the same `meta.host` (one compute node). Post-change, each array task lands on whichever node SLURM allocates, so `meta.host` will vary across the (model, think, cond) cells of one `--all` sweep. `host_tag()` in `aggregate.py` already accepts arbitrary hostnames — no aggregator code change. This is informational metadata, not a confounder.

**Result dir naming: stable.** `results/slurm_<model>_<think>_<cond>_<jobid>/` continues to hold; `<jobid>` is each array task's `$SLURM_JOBID` (which SLURM guarantees unique per task in array mode). Glob aggregators (`results/slurm_*` in `aggregate.py`, notebooks) work unchanged.

**No new smoke baseline required.** The pure-eval semantics (Ollama params, MCP tools, scoring) are byte-identical to the current setup; only the SLURM scheduling changes. Existing smoke anchors (`smoke_<sha>_<ts>/` from 2026-04-29 / 2026-04-30) remain valid sanity checks. A one-shot `submit_with_rtx.sh Qwen3.5:0.8B` (single-model, no array) verifies the `--tmp=50G` path on rtx_pro_6000 before the first `--all` array submission — that's a smoke-test of the scheduling change, not a methodology re-baseline.

## 5. Open decisions

1. **`--tmp=50G` capacity on rtx_pro_6000 nodes.** The Mar-26 guide §"SSD Drive" documents the flag but doesn't quote per-node `/scratch` capacity. Smoke a single-model run with `--tmp=50G` on rtx_pro_6000 to confirm allocation succeeds before flipping `--all`. If 50 G isn't honored, fall back to keeping `WORK=/tmp/rtx-$SLURM_JOBID` (the existing path) and skip `--tmp`.
2. **Array concurrency cap (`%N`).** `--array=0-3` (default unlimited) lets SLURM run all 4 tasks concurrently if the pool has capacity — best wall-clock outcome. Adding `%2` (max 2 simultaneous) is gentler on other users when the pool is contended. **Recommendation: default unlimited; document the `%N` override.** Add to the politeness section in README.
3. **Drop `--nv` from `apptainer build`?** Pure cosmetic guide-alignment; trivial. Recommend yes when touching the file. No methodology impact.
4. **Single-model recursion-via-positional-args path.** `submit_with_rtx.sh m1 m2 m3` (multi-positional, < 4 models) currently uses the same packing logic as `--all`. Should that also become an array (length-3 array), or keep packing for explicit < 4-model invocations? **Recommendation: array everywhere — uniform code path, no special case.** User can still pack manually by setting `MODELS="m1 m2 m3"` in a single sbatch if there's ever a reason.
5. **`--no-tools` `--time` scaling under arrays.** Current `nt_hours = 6 + 6*(N-1)` was for packed-serial. Under arrays, every task is single-model so `--time=06:00:00` is correct per task regardless of N. Confirm this is the intended scale; the wall-clock budget table in README needs the corresponding update.

---

**Implementation gate:** await user approval. If/when approved, branch first (`git checkout -b cluster/array-submit`), implement, smoke-verify with single-model `--tmp=50G`, then `--all` dry-run + live, then CHANGELOG entry on merge documenting the methodology shift (none) and the operational shift (array fan-out + scratch path + politeness recipe). On merge or rejection, this proposal file moves to `development/archive/` (matches `FRAMEWORK_EXTENSION_PLAN.md` lifecycle convention).
