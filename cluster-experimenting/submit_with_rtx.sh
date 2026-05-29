#!/usr/bin/env bash
# Submit a SLURM job array on the BGU CIS cluster covering one or more
# (model, think_mode, condition) cells. Each array task self-deploys an
# isolated vLLM server on a single GPU node, then runs run_experiment.py
# against localhost:<port> for that one cell.
#
# Per-cell array model (replaces the prior packed-job topology, 2026-04-30):
# the wrapper builds CELLS=( "model|think|cond" ... ) over the full
# think × cond product (no-tools/think=on matrix-gate lifted 2026-05-12),
# then submits a single sbatch with --array=0-(N-1). Each task picks its
# cell via $SLURM_ARRAY_TASK_ID. Up to N tasks run concurrently if the
# rtx_pro_6000 pool has capacity. No %N cap by default — full fan-out for
# fastest wall.
#
# GPU routing:
#   default → rtx_pro_6000:1 (96 GB, --mem=80G). Hard-pinned as the sole
#             self-deploy GPU class so peak VRAM and host RAM are constant
#             across the active sweep.
#   --gpu-type rtx_6000 → opt-in escape hatch (48 GB VRAM, --mem=48G).
#                         Use only when rtx_pro_6000 is queue-saturated
#                         and the requested models all fit.
#
# Resource policy (post 2026-04-27 IT request):
#   * No --cpus-per-task — uses cluster default cpus-per-gpu.
#   * --mem cap: 80G on rtx_pro_6000 (default), 48G on rtx_6000 (opt-in).
#   * --tmp=50G on every job — explicit /scratch/$USER/$JOBID per Mar-26
#     guide §"SSD Drive". Covers vLLM image + one HF model snapshot (~24 GB
#     peak for qwen3.6:35b in single-cell mode; gemma4:26b-a4b ~16 GB).
#
# Usage:
#   bash cluster-experimenting/submit_with_rtx.sh <model> [<model>...]
#   bash cluster-experimenting/submit_with_rtx.sh --all
#   bash cluster-experimenting/submit_with_rtx.sh <model> --no-tools
#   bash cluster-experimenting/submit_with_rtx.sh <m1> <m2> --gpu-type rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh <model> --think-modes "on off"
#   bash cluster-experimenting/submit_with_rtx.sh <model> --dry-run
#   bash cluster-experimenting/submit_with_rtx.sh --all --continue-partial /path/to/seed_dir
#   bash cluster-experimenting/submit_with_rtx.sh --all --partial 2 --continue-partial /path/to/seed_dir
#   bash cluster-experimenting/submit_with_rtx.sh --all --exclude ise-6000p-04          # skip a sick node
#   bash cluster-experimenting/submit_with_rtx.sh --all --no-auto-prioritize             # don't deprioritize fast cells
#   bash cluster-experimenting/submit_with_rtx.sh --all --no-tools --include-no-tools-steered  # sweep-5 control arm
#
# --include-no-tools-steered: enables the sweep-5 control arm by emitting
#   v14/v15/v16 in no-tools cells (the harness otherwise skips them — see
#   runner.py:_emit_job emit-skip gate). Pairs with the `nt-ster` column
#   in status.sh; without this flag that column stays empty by design.
#
# --no-auto-prioritize: skips the post-submit `scontrol update Nice=500`
#   that the wrapper otherwise applies to every cell whose model is NOT
#   in PDDL_SLOW_MODELS (gemma4:26b-a4b, qwen3.6:35b). The auto-gate fires
#   only on a fresh `--all` submit (NO --continue-partial / --partial /
#   --smoke / --smoke-shuffle); for resubmits or single-model invocations
#   it doesn't fire to begin with, so this flag is a no-op there. Use the
#   `prioritize.sh` skill script in `.claude/skills/cluster-ops/scripts/`
#   to apply Nice values manually after the fact.
#
# Multi-cell array submissions also write a manifest at
# `cluster-experimenting/logs/<jobid>.cells.tsv` (idx<TAB>model<TAB>think
# <TAB>cond). The cluster-ops `prioritize.sh` skill script reads this to
# map array indices back to cells without re-deriving the cell-product
# logic. Single-cell submissions skip — nothing to reorder.
#
# --exclude NODELIST: passed straight to sbatch's --exclude. Use when a
#   compute node is in a degraded state (e.g. /scratch full, GPU stuck)
#   and the SLURM scheduler would otherwise repeatedly land array tasks
#   on it. Comma-separated list, e.g. `ise-6000p-04,ise-6000p-05`.
#
# --continue-partial PATH: every array cell seeds its OUT_DIR/trials.jsonl
#   from PATH/trials.jsonl on FIRST submission (sbatch-side guard skips the
#   seeding if OUT_DIR/trials.jsonl is already non-empty, so a TIMEOUT'd
#   cell that's resubmitted just resumes from where it left off). PATH must
#   contain a trials.jsonl; merge multiple cells with
#   `cat results/slurm_*/trials.jsonl > /tmp/seed/trials.jsonl` if needed.
#   Array fan-out is unchanged; each cell copies independently from PATH.
#
# --partial K: pass `--partial K` to every cell's run_experiment.py. Caps
#   each domain to first-K positive + first-K negative problems and first-K
#   valid + first-K invalid plans per kept positive — a fast-feedback
#   slice of the full sweep. Combine with
#   --continue-partial to instantly produce partial-style results from a
#   pre-existing full-sweep cluster directory (resume skips every matching
#   cell, output is the partial-fixture summary).
#
# Examples:
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B           # 4-cell array (think × cond)
#   bash cluster-experimenting/submit_with_rtx.sh --all                  # 20-cell array (5 models × 4 cells)
#   bash cluster-experimenting/submit_with_rtx.sh --all --no-tools       # 10-cell array (5 models × 2 cells: think on+off)
#   bash cluster-experimenting/submit_with_rtx.sh gemma4:26b-a4b --no-tools  # 2-cell array (think on+off)
#
# --all: shorthand for the 5 active models in PDDL_DEFAULT_MODELS. Each
#   model contributes 4 cells under the full think={on,off} ×
#   cond={no-tools, tools_all_minimal} matrix. Total array size: 20.
#   Sweep-5 (2026-05-23) keeps the same cell topology but emits 6 prompt
#   variants per with-tools cell (v11-16) vs 3 per no-tools cell (v11-13);
#   the per-cell denominator is asymmetric. Roster history:
#   2026-04-29 swap, 2026-04-30 nemotron drop. The (think=on, no-tools) cell
#   was added 2026-05-12 after ISS-018 (PR-2, 2026-04-28) lifted the runtime
#   abort and routed thinking content into TaskResult.thinking — verdict /
#   plan extraction is no longer contaminated, so the cell is now a valid
#   ablation column. See development/CHANGELOG.md.
#
# --no-tools: pins CONDITIONS=no-tools, defaults THINK_MODES=(on off). Each
#   (model, think) cell becomes one array task. Sbatch's case-branch sets
#   TASKS to the 4-task discriminative matrix (solve + validate_*); simulate
#   stays excluded.
#
# --tools-only: complement of --no-tools — pins CONDITIONS=tools_all_minimal,
#   defaults THINK_MODES=(on off). Used by the sweep5v2 / sweep6 contamination
#   split where the no-tools baseline is reused (sweep5v2) or run separately
#   (sweep6), so only the with-tools arm needs (re-)running against the
#   updated MCP server. Mutually exclusive with --no-tools.
#
# Think modes default to "on off" (both run as separate cells in the array).
# Override with --think-modes "default" for models without a think kwarg
# or --think-modes "off" to skip thinking cells. (Note: gemma4:26b-a4b does
# emit reasoning; the historical "gemma4* no-think" carveout only applied
# to gemma2-era tags and is no longer load-bearing.)

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

DRY_RUN=0
GPU_TYPE=""
THINK_MODES_OVERRIDE=""
NO_TOOLS=0
TOOLS_ONLY=0
ALL=0
SMOKE=0
SMOKE_SHUFFLE=0
SHARD=""
CONTINUE_PARTIAL=""
PARTIAL_K=""
EXCLUDE_NODES=""
NO_AUTO_PRIORITIZE=0
TIME_OVERRIDE=""
TMP_OVERRIDE=""
INCLUDE_NO_TOOLS_STEERED=0
DOMAINS_DIR=""
RUN_TAG=""
MODELS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --gpu-type) shift; GPU_TYPE="$1"; shift ;;
        --think-modes) shift; THINK_MODES_OVERRIDE="$1"; shift ;;
        --no-tools) NO_TOOLS=1; shift ;;
        --tools-only) TOOLS_ONLY=1; shift ;;
        --all) ALL=1; shift ;;
        --smoke) SMOKE=1; shift ;;
        --smoke-shuffle) SMOKE_SHUFFLE=1; shift ;;
        --shard) shift; SHARD="$1"; shift ;;
        --continue-partial) shift; CONTINUE_PARTIAL="$1"; shift ;;
        --partial) shift; PARTIAL_K="$1"; shift ;;
        --exclude) shift; EXCLUDE_NODES="$1"; shift ;;
        --no-auto-prioritize) NO_AUTO_PRIORITIZE=1; shift ;;
        --time) shift; TIME_OVERRIDE="$1"; shift ;;
        --tmp) shift; TMP_OVERRIDE="$1"; shift ;;
        --include-no-tools-steered) INCLUDE_NO_TOOLS_STEERED=1; shift ;;
        --domains-dir) shift; DOMAINS_DIR="$1"; shift ;;
        --run-tag) shift; RUN_TAG="$1"; shift ;;
        -h|--help)
            sed -n '1,100p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            MODELS+=("$1"); shift ;;
    esac
done

if [ -n "$PARTIAL_K" ] && ! [[ "$PARTIAL_K" =~ ^[0-9]+$ ]]; then
    echo "Error: --partial expects a non-negative integer (got: $PARTIAL_K)" >&2
    exit 1
fi

# --no-tools and --tools-only are complementary halves of the cond axis;
# setting both is contradictory. --tools-only pins CONDITIONS=tools_all_minimal
# (the with-tools-only sweep used by the sweep5v2 / sweep6 contamination split,
# where the no-tools baseline is reused rather than re-run).
if [ "$NO_TOOLS" -eq 1 ] && [ "$TOOLS_ONLY" -eq 1 ]; then
    echo "Error: --no-tools and --tools-only are mutually exclusive" >&2
    exit 1
fi

# `--continue-partial PATH` opt-in: per array cell, seed OUT_DIR/trials.jsonl
# from PATH/trials.jsonl IF that cell's OUT_DIR is empty. The sbatch enforces
# the empty-dir guard so a TIMEOUT'd cell that's resubmitted does not re-seed
# (which would clobber trials accumulated since the first seeding). Array
# semantics unchanged — every cell still fans out concurrently, each seeds
# its own OUT_DIR independently from the same source. Validate up front so a
# typo'd path fails before the cluster pulls the slot.
if [ -n "$CONTINUE_PARTIAL" ]; then
    if [ ! -f "${CONTINUE_PARTIAL}/trials.jsonl" ]; then
        echo "Error: --continue-partial: ${CONTINUE_PARTIAL}/trials.jsonl not found" >&2
        exit 1
    fi
fi

# --domains-dir defence-in-depth: per contamination_probe_plan.md §6/§7,
# the canonical fixtures under $REPO_ROOT/domains must never be re-run
# under a contamination-probe banner via a submit-time typo. Resolve the
# supplied path (tolerating not-yet-existing dirs) and refuse if it
# resolves to the canonical domains/ root or anything inside it. Relative
# paths are resolved against $REPO_ROOT (NOT the caller's CWD), matching
# the sbatch which also `cd`s to $EXPT_ROOT before invoking
# run_experiment.py. The resolved absolute path is stored back into
# DOMAINS_DIR so the env-var hop to sbatch is CWD-independent.
#
# Why python3 instead of `realpath -m`: BSD realpath on macOS submission
# hosts lacks `-m` and errors on not-yet-existing paths. python3's
# os.path.realpath is portable across macOS and Linux login nodes and
# tolerates absent leaf dirs (we may submit before the rewriter has
# materialized domains-anon/).
if [ -n "$DOMAINS_DIR" ]; then
    _domains_canonical=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$REPO_ROOT/domains")
    case "$DOMAINS_DIR" in
        /*) _domains_resolved=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$DOMAINS_DIR") ;;
        *)  _domains_resolved=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$REPO_ROOT/$DOMAINS_DIR") ;;
    esac
    # Strip a single trailing slash so `domains/` and `domains` compare
    # identically against the canonical root.
    _domains_resolved="${_domains_resolved%/}"
    _domains_canonical="${_domains_canonical%/}"
    if [ "$_domains_resolved" = "$_domains_canonical" ] || \
       [[ "$_domains_resolved" == "$_domains_canonical"/* ]]; then
        echo "Error: --domains-dir resolves into the canonical fixtures tree." >&2
        echo "  supplied:  $DOMAINS_DIR" >&2
        echo "  resolved:  $_domains_resolved" >&2
        echo "  canonical: $_domains_canonical (forbidden as target)" >&2
        echo "Refusing to re-run canonical fixtures under a non-baseline run." >&2
        echo "Use a sibling directory (e.g. domains-anon/) per development/contamination_probe_plan.md §6." >&2
        exit 1
    fi
    DOMAINS_DIR="$_domains_resolved"
    unset _domains_canonical _domains_resolved
fi

# --run-tag: optional suffix appended to per-cell OUT_DIR in the sbatch so
# a non-canonical corpus run (e.g. --domains-dir domains-anon) doesn't
# clobber the canonical results/slurm_vllm_<model>_<think>_<cond>/ trees.
# Wrapper-only concept; no equivalent existed prior. Constrained to a
# filename-safe alphabet to keep OUT_DIR predictable.
if [ -n "$RUN_TAG" ] && ! [[ "$RUN_TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Error: --run-tag must match [A-Za-z0-9._-]+ (got: $RUN_TAG)" >&2
    exit 1
fi

# --smoke / --smoke-shuffle: pin the default model pack (5 models in
# PDDL_DEFAULT_MODELS) and full think × cond matrix; run_experiment.py
# auto-overrides --num-variants and skips the inner THINK × CONDITIONS
# loop in the sbatch (the smoke wrapper iterates think internally). One
# cell per model.
if [ "$SMOKE" -eq 1 ] && [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "Error: --smoke and --smoke-shuffle are mutually exclusive" >&2
    exit 1
fi
if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    if [ "$ALL" -eq 1 ] || [ "$NO_TOOLS" -eq 1 ] || [ "$TOOLS_ONLY" -eq 1 ] || [ -n "$THINK_MODES_OVERRIDE" ]; then
        echo "Error: --smoke[-shuffle] is exclusive with --all/--no-tools/--tools-only/--think-modes" >&2
        exit 1
    fi
    if [ "${#MODELS[@]}" -eq 0 ]; then
        MODELS=("${PDDL_DEFAULT_MODELS[@]}")
    fi
fi

# --all populates the 5-model paper roster (PDDL_DEFAULT_MODELS). Each
# (model, think, cond) cell becomes one array task; default GPU class is
# rtx_6000:1 (see GPU routing in the header).
if [ "$ALL" -eq 1 ]; then
    if [ "${#MODELS[@]}" -gt 0 ]; then
        echo "Error: --all is exclusive with explicit model args" >&2
        exit 1
    fi
    MODELS=("${PDDL_DEFAULT_MODELS[@]}")
fi

if [ "${#MODELS[@]}" -eq 0 ]; then
    echo "Usage: bash $0 <model> [<model>...] [--all] [--no-tools|--tools-only] [--gpu-type rtx_6000|rtx_pro_6000] [--think-modes \"on off\"] [--dry-run]" >&2
    exit 1
fi

# Model gate. vllm_lookup is the single source of truth for which
# (HF id, parser flags) we'll launch with; fail fast on unverified models.
# The sbatch re-runs the same lookup at runtime for defense-in-depth.
SBATCH_FILE="$SCRIPT_DIR/run_condition_vllm_rtx.sbatch"
for m in "${MODELS[@]}"; do
    vllm_lookup "$m" >/dev/null || exit 1
done

# Default GPU: rtx_6000 (48 GB) — smoke-verified for the full active
# roster (27B AWQ peaks 83% VRAM, 0.8B well below). rtx_pro_6000 (96 GB)
# is the opt-in escape for tools×on cells that need extra headroom.
GPU_TYPE="${GPU_TYPE:-rtx_6000}"

case "$GPU_TYPE" in
    rtx_6000)
        # Default for vLLM after the 2026-05-18 backend unification — the
        # full roster (peak qwen3.6:35b ~24 GB, gemma4:26b-a4b ~16 GB +
        # vision tower) fits comfortably in 48 GB under
        # gpu-memory-utilization=0.85. rtx_pro_6000 remains an opt-in
        # escape for tools×on cells that need extra headroom.
        MEM_ARG="--mem=48G" ;;
    rtx_pro_6000)
        # Default. 80G mem cap per IT request 2026-04-27.
        MEM_ARG="--mem=80G" ;;
    *)
        echo "Error: --gpu-type must be rtx_6000 or rtx_pro_6000 (got: $GPU_TYPE)" >&2
        exit 1 ;;
esac

# Resolve effective think × cond axis values for cell generation.
# --no-tools pins CONDITIONS=no-tools and otherwise lets the default
# (on off) think axis run both cells per model. The legacy think=off-only
# restriction was lifted 2026-05-12 alongside the cell-builder gate (see
# below) — ISS-018 (PR-2, 2026-04-28) had already lifted the runtime abort
# and routed thinking into TaskResult.thinking, so verdict/plan extraction
# is no longer contaminated when think=on/no-tools.
DEFAULT_CONDITIONS=("${PDDL_DEFAULT_CONDITIONS[@]}")
DEFAULT_THINK_MODES=("${PDDL_DEFAULT_THINK_MODES[@]}")

if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    # Smoke iterates think × conds inside run_experiment.py.
    # One cell per model — sbatch SMOKE-fastpath consumes the cell.
    EFF_THINK=("default")
    EFF_COND=("@smoke@")
elif [ "$NO_TOOLS" -eq 1 ]; then
    if [ -n "$THINK_MODES_OVERRIDE" ]; then
        read -ra EFF_THINK <<< "$THINK_MODES_OVERRIDE"
    else
        EFF_THINK=("${DEFAULT_THINK_MODES[@]}")
    fi
    EFF_COND=("no-tools")
elif [ "$TOOLS_ONLY" -eq 1 ]; then
    if [ -n "$THINK_MODES_OVERRIDE" ]; then
        read -ra EFF_THINK <<< "$THINK_MODES_OVERRIDE"
    else
        EFF_THINK=("${DEFAULT_THINK_MODES[@]}")
    fi
    EFF_COND=("tools_all_minimal")
else
    if [ -n "$THINK_MODES_OVERRIDE" ]; then
        read -ra EFF_THINK <<< "$THINK_MODES_OVERRIDE"
    else
        EFF_THINK=("${DEFAULT_THINK_MODES[@]}")
    fi
    EFF_COND=("${DEFAULT_CONDITIONS[@]}")
fi

# Build cells (model × think × cond). The legacy no-tools/think=on gate was
# lifted 2026-05-12 to complete the ablation dimension (4 missing cells per
# `--all` sweep, one per model). Default `--all` now expands to 4×6 = 24
# cells. The runtime-side abort that previously refused this combination was
# already lifted in PR-2 (2026-04-28, ISS-018 closure).
CELLS=()
for m in "${MODELS[@]}"; do
    for t in "${EFF_THINK[@]}"; do
        for c in "${EFF_COND[@]}"; do
            CELLS+=("${m}|${t}|${c}")
        done
    done
done
N_CELLS=${#CELLS[@]}
if [ "$N_CELLS" -eq 0 ]; then
    echo "Error: cell list is empty (think_modes=${EFF_THINK[*]} conds=${EFF_COND[*]})" >&2
    exit 1
fi
CELLS_LIST=$(IFS='^'; echo "${CELLS[*]}")

# Per-task --time. Each array task runs ONE (model, think, cond) cell, so
# the prior packed 6-day budget no longer applies — cells are independent
# and budgets are per-cell.
#   tools cells: 2026-05-01 measured ~40 s/trial × 4560 trials → ~50h wall.
#                Set to 72h to leave headroom and complete in one shot
#                (resume via trials.jsonl still works if a cell does TIMEOUT).
#                Main partition cap is 7 days, so 72h is well within.
#   no-tools cells: ~6-7h (5-task matrix incl. simulate after PR-4).
#   smoke cells: ~30-45 min (matrix iteration internal to run_experiment.py).
if [ -n "$TIME_OVERRIDE" ]; then
    # Explicit --time wins over all auto-computed defaults. Pass HH:MM:SS
    # or D-HH:MM:SS.
    TIME_ARG=(--time="$TIME_OVERRIDE")
elif [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    TIME_ARG=(--time=03:00:00)
else
    # Defaults match the documented per-cell budgets above (tools=72h,
    # no-tools=12h). SLURM bills actual usage, not the wall budget, so
    # generous fallbacks just prevent silent TIMEOUTs on ad-hoc
    # invocations of heavy models without --time. Production sweeps via
    # submit_full_sweep.sh always pass --time explicitly.
    if [ "$NO_TOOLS" -eq 1 ]; then
        TIME_ARG=(--time=12:00:00)
    else
        TIME_ARG=(--time=72:00:00)
    fi
fi

# Job name: single model uses the model tag; multi-model uses
# pddl_rtx_pack<count>_<first-tag>. With per-cell arrays %x is the same
# across array tasks of one submission and %J disambiguates per task.
# Note: run_condition_vllm_rtx.sbatch renames each array task at runtime
# via `scontrol update JobName=...` once it resolves its cell, so live
# `squeue` listings show pddl_<model>_<think>_<cond_tag> per task. Log
# filenames (%x-%J.out) keep the submit-time prefix below — they were
# resolved at job start, before the rename.
if [ "${#MODELS[@]}" -eq 1 ]; then
    MODEL_TAG=$(echo "${MODELS[0]}" | tr '/:.' '___')
    JOB_NAME="pddl_rtx_${MODEL_TAG}"
else
    FIRST_TAG=$(echo "${MODELS[0]}" | tr '/:.' '___')
    JOB_NAME="pddl_rtx_pack${#MODELS[@]}_${FIRST_TAG}"
fi
if [ "$NO_TOOLS" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_notools"
fi
if [ "$TOOLS_ONLY" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_toolsonly"
fi
if [ "$SMOKE" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_smoke"
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_smoke-shuffle"
fi

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

# Compose --export list. ALL inherits caller env; we layer CELLS_LIST
# (^-separated MODEL|THINK|COND triples; sbatch picks one per array task
# via $SLURM_ARRAY_TASK_ID) and the smoke/shard env vars.
EXPORT_LIST="ALL,CELLS_LIST=${CELLS_LIST}"
if [ "$SMOKE" -eq 1 ]; then
    EXPORT_LIST="${EXPORT_LIST},SMOKE=1"
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    EXPORT_LIST="${EXPORT_LIST},SMOKE_SHUFFLE=1"
fi
if [ -n "$SHARD" ]; then
    EXPORT_LIST="${EXPORT_LIST},SHARD=${SHARD}"
fi
if [ -n "$CONTINUE_PARTIAL" ]; then
    EXPORT_LIST="${EXPORT_LIST},CONTINUE_PARTIAL=${CONTINUE_PARTIAL}"
fi
if [ -n "$PARTIAL_K" ]; then
    EXPORT_LIST="${EXPORT_LIST},PARTIAL_K=${PARTIAL_K}"
fi
if [ "$INCLUDE_NO_TOOLS_STEERED" -eq 1 ]; then
    EXPORT_LIST="${EXPORT_LIST},INCLUDE_NO_TOOLS_STEERED=1"
fi
if [ -n "$DOMAINS_DIR" ]; then
    EXPORT_LIST="${EXPORT_LIST},DOMAINS_DIR=${DOMAINS_DIR}"
fi
if [ -n "$RUN_TAG" ]; then
    EXPORT_LIST="${EXPORT_LIST},RUN_TAG=${RUN_TAG}"
fi
# GPU_MEM_UTIL is a correctness param (the VRAM-85%-guard headroom for big
# models like gpt-oss:120b). Thread it explicitly to match the SMOKE/SHARD
# convention rather than relying on --export=ALL inheritance alone.
if [ -n "${GPU_MEM_UTIL:-}" ]; then
    EXPORT_LIST="${EXPORT_LIST},GPU_MEM_UTIL=${GPU_MEM_UTIL}"
fi

# Add --array only when N>1; single-cell submissions remain plain sbatch.
ARRAY_ARG=()
if [ "$N_CELLS" -gt 1 ]; then
    ARRAY_ARG=(--array="0-$((N_CELLS-1))")
fi

EXCLUDE_ARG=()
if [ -n "$EXCLUDE_NODES" ]; then
    EXCLUDE_ARG=(--exclude="$EXCLUDE_NODES")
fi

# --tmp passthrough: overrides the sbatch's `#SBATCH --tmp=80G` directive
# (CLI options win over script directives). The 80G default was sized for
# ~24 GB HF snapshots; a large model (e.g. gpt-oss:120b ~63 GB weights +
# the ~10-15 GB vllm.sif copied to scratch) needs more headroom or the
# /scratch mkdir ENOSPC-bails before the trap fires. Unset → directive stands.
TMP_ARG=()
if [ -n "$TMP_OVERRIDE" ]; then
    TMP_ARG=(--tmp="$TMP_OVERRIDE")
fi

cmd=(sbatch
    --job-name="$JOB_NAME"
    --gpus="${GPU_TYPE}:1"
    "$MEM_ARG"
    "${TIME_ARG[@]}"
    "${TMP_ARG[@]}"
    "${ARRAY_ARG[@]}"
    "${EXCLUDE_ARG[@]}"
    --export="$EXPORT_LIST"
    "$SBATCH_FILE")

echo "--- rtx self-deploy submission (vLLM) ---" >&2
echo "  models:      ${MODELS[*]}" >&2
if [ "$N_CELLS" -gt 1 ]; then
    echo "  cells:       $N_CELLS (array fan-out 0-$((N_CELLS-1)))" >&2
else
    echo "  cells:       1 (single sbatch, no array)" >&2
fi
echo "  GPU:         ${GPU_TYPE}:1" >&2
echo "  mem:         $MEM_ARG" >&2
echo "  time/cell:   ${TIME_ARG[*]}" >&2
echo "  job name:    $JOB_NAME" >&2
echo "  sbatch:      $(basename "$SBATCH_FILE")" >&2
if [ "$NO_TOOLS" -eq 1 ]; then
    echo "  mode:        --no-tools (CONDITIONS=no-tools, TASKS=all 5 incl. simulate)" >&2
fi
if [ "$SMOKE" -eq 1 ]; then
    echo "  mode:        --smoke (1 domain × 1 problem × 1 variant × 5 tasks × 2 conds × 2 think; output → results/smoke/fixed_<sha>_<ts>/)" >&2
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "  mode:        --smoke-shuffle (per-(model,task) random domain pick; output → results/smoke/shuffle_<sha>_<ts>/)" >&2
fi
if [ -n "$SHARD" ]; then
    echo "  shard:       $SHARD (SHA-256 partitioner)" >&2
fi
if [ -n "$CONTINUE_PARTIAL" ]; then
    echo "  cont-from:   $CONTINUE_PARTIAL (each cell seeds its OUT_DIR/trials.jsonl on first run only)" >&2
fi
if [ -n "$PARTIAL_K" ]; then
    echo "  partial:     K=$PARTIAL_K (per-domain fixture cap; single-task fast feedback slice)" >&2
fi
if [ -n "$EXCLUDE_NODES" ]; then
    echo "  exclude:     $EXCLUDE_NODES" >&2
fi
if [ -n "$DOMAINS_DIR" ]; then
    echo "  domains:     $DOMAINS_DIR (non-canonical corpus; per-cell OUT_DIR suffix via --run-tag recommended)" >&2
fi
if [ -n "$RUN_TAG" ]; then
    echo "  run tag:     $RUN_TAG (suffixed onto per-cell OUT_DIR)" >&2
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo "  DRY: ${cmd[*]}" >&2
else
    jid=$("${cmd[@]}" | awk '{print $NF}')
    echo "  submitted as job $jid" >&2
    echo "$jid"
    echo "" >&2
    echo "Monitor:  squeue -j $jid" >&2
    if [ "$N_CELLS" -gt 1 ]; then
        echo "  (array tasks appear as ${jid}_0..${jid}_$((N_CELLS-1)))" >&2
    fi
    echo "Log:      $REPO_ROOT/cluster-experimenting/logs/${JOB_NAME}-<task_jid>.out" >&2
    echo "Results:  $REPO_ROOT/results/slurm_<model>_<think>_<cond>/  (one dir per cell; resubmits resume from trials.jsonl)" >&2

    # Manifest: idx<TAB>model<TAB>think<TAB>cond. Written for every
    # multi-cell array submission so the cluster-ops `prioritize.sh`
    # skill script can map array indices → cells without re-deriving
    # the matrix-gate logic. Single-cell jobs skip — nothing to reorder.
    if [ "$N_CELLS" -gt 1 ]; then
        manifest="cluster-experimenting/logs/${jid}.cells.tsv"
        : > "$manifest"
        for i in "${!CELLS[@]}"; do
            IFS='|' read -r cm ct cc <<< "${CELLS[$i]}"
            printf '%s\t%s\t%s\t%s\n' "$i" "$cm" "$ct" "$cc" >> "$manifest"
        done
        echo "Manifest: $REPO_ROOT/$manifest" >&2

        # Auto-deprioritize fast cells on a fresh `--all` submission so
        # the heavy models (PDDL_SLOW_MODELS) grab the next free GPU
        # slot first. Gate: ALL=1 and not a resume/partial/smoke run.
        # `--no-auto-prioritize` opts out. `|| true` because a task that
        # raced PENDING→RUNNING in the half-second since sbatch returned
        # rejects the Nice update — that's fine, the running cell is
        # already past the scheduling decision.
        if [ "$NO_AUTO_PRIORITIZE" -eq 0 ] \
            && [ "$ALL" -eq 1 ] \
            && [ -z "$CONTINUE_PARTIAL" ] \
            && [ -z "$PARTIAL_K" ] \
            && [ "$SMOKE" -eq 0 ] \
            && [ "$SMOKE_SHUFFLE" -eq 0 ]; then
            slow_re=$(IFS='|'; echo "${PDDL_SLOW_MODELS[*]}")
            deprio=()
            for i in "${!CELLS[@]}"; do
                IFS='|' read -r cm _ _ <<< "${CELLS[$i]}"
                if ! [[ "|${slow_re}|" == *"|${cm}|"* ]]; then
                    deprio+=("${jid}_${i}")
                fi
            done
            if [ "${#deprio[@]}" -gt 0 ]; then
                echo "Auto-prioritize: keeping ${PDDL_SLOW_MODELS[*]} at Nice=0; deprioritizing ${#deprio[@]} fast cells (Nice=500)" >&2
                for j in "${deprio[@]}"; do
                    scontrol update "JobId=${j}" Nice=500 || true
                done
            fi
        fi
    fi
fi
