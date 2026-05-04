#!/usr/bin/env bash
# Submit a SLURM job array on the BGU CIS cluster covering one or more
# (model, think_mode, condition) cells. Each array task self-deploys an
# isolated Apptainer Ollama on a single GPU node, then runs run_experiment.py
# against localhost:<port> for that one cell.
#
# Per-cell array model (replaces the prior packed-job topology, 2026-04-30):
# the wrapper builds CELLS=( "model|think|cond" ... ) with the matrix-gate
# filter (no-tools is reported only for think=off) applied, then submits a
# single sbatch with --array=0-(N-1). Each task picks its cell via
# $SLURM_ARRAY_TASK_ID. Up to N tasks run concurrently if the rtx_pro_6000
# pool has capacity. No %N cap by default — full fan-out for fastest wall.
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
#     guide §"SSD Drive". Covers ollama.sif (~3 GB) + one model (~26 GB
#     peak for gemma4:31b in single-cell mode).
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
#   valid + first-K invalid plans per kept positive — the same fast-feedback
#   slice as the local `run_background.sh partial` mode. Combine with
#   --continue-partial to instantly produce partial-style results from a
#   pre-existing full-sweep cluster directory (resume skips every matching
#   cell, output is the partial-fixture summary).
#
# Examples:
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B           # 5-cell array
#   bash cluster-experimenting/submit_with_rtx.sh --all                  # 20-cell array (4 models × 5 cells)
#   bash cluster-experimenting/submit_with_rtx.sh --all --no-tools       # 4-cell array (4 models × 1 cell)
#   bash cluster-experimenting/submit_with_rtx.sh gemma4:31b --no-tools  # 1-cell job (no array)
#
# --all: shorthand for the 4 active models. Each model contributes 5 cells
#   under the default think={on,off} × cond={no-tools, tools_per-task_minimal,
#   tools_all_minimal} matrix with the no-tools/think=on gate (so 5 not 6).
#   Total array size: 20. Roster history: 2026-04-29 swap, 2026-04-30 nemotron
#   drop. See development/CHANGELOG.md.
#
# --no-tools: pins THINK_MODES=off, CONDITIONS=no-tools. Each (model,) cell
#   becomes one array task. Sbatch's case-branch sets TASKS to the 4-task
#   discriminative matrix (solve + validate_*); simulate stays excluded;
#   chains skipped by matrix gate.
#
# Think modes default to "on off" (both run as separate cells in the array).
# Override with --think-modes "default" for models without a think kwarg
# (e.g. gemma4*) or --think-modes "off" to skip thinking cells.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBATCH_FILE="$SCRIPT_DIR/run_condition_rtx.sbatch"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

if [ ! -f "$SBATCH_FILE" ]; then
    echo "Error: $SBATCH_FILE not found." >&2
    exit 1
fi

DRY_RUN=0
GPU_TYPE=""
THINK_MODES_OVERRIDE=""
NO_TOOLS=0
ALL=0
SMOKE=0
SMOKE_SHUFFLE=0
SHARD=""
CONTINUE_PARTIAL=""
PARTIAL_K=""
MODELS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --gpu-type) shift; GPU_TYPE="$1"; shift ;;
        --think-modes) shift; THINK_MODES_OVERRIDE="$1"; shift ;;
        --no-tools) NO_TOOLS=1; shift ;;
        --all) ALL=1; shift ;;
        --smoke) SMOKE=1; shift ;;
        --smoke-shuffle) SMOKE_SHUFFLE=1; shift ;;
        --shard) shift; SHARD="$1"; shift ;;
        --continue-partial) shift; CONTINUE_PARTIAL="$1"; shift ;;
        --partial) shift; PARTIAL_K="$1"; shift ;;
        -h|--help)
            sed -n '1,80p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

# --smoke / --smoke-shuffle: pin the 4-model pack and full think × cond
# matrix; run_experiment.py auto-overrides --num-variants/--chain-samples
# and skips the inner THINK × CONDITIONS loop in the sbatch (the smoke
# wrapper iterates think internally). One cell per model.
if [ "$SMOKE" -eq 1 ] && [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "Error: --smoke and --smoke-shuffle are mutually exclusive" >&2
    exit 1
fi
if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    if [ "$ALL" -eq 1 ] || [ "$NO_TOOLS" -eq 1 ] || [ -n "$THINK_MODES_OVERRIDE" ]; then
        echo "Error: --smoke[-shuffle] is exclusive with --all/--no-tools/--think-modes" >&2
        exit 1
    fi
    if [ "${#MODELS[@]}" -eq 0 ]; then
        MODELS=("${PDDL_DEFAULT_MODELS[@]}")
    fi
fi

# --all populates the 4-model paper roster. Each (model, think, cond) cell
# becomes one array task on rtx_pro_6000:1.
if [ "$ALL" -eq 1 ]; then
    if [ "${#MODELS[@]}" -gt 0 ]; then
        echo "Error: --all is exclusive with explicit model args" >&2
        exit 1
    fi
    MODELS=("${PDDL_DEFAULT_MODELS[@]}")
fi

if [ "${#MODELS[@]}" -eq 0 ]; then
    echo "Usage: bash $0 <model> [<model>...] [--all] [--no-tools] [--gpu-type rtx_6000|rtx_pro_6000] [--think-modes \"on off\"] [--dry-run]" >&2
    exit 1
fi

# Default GPU is rtx_pro_6000 (single, hard-pinned class). --gpu-type
# rtx_6000 is the opt-in escape hatch. No auto-detection — keeping the
# class fixed is what makes "consistency and known variables" hold across
# the sweep.
GPU_TYPE="${GPU_TYPE:-rtx_pro_6000}"

case "$GPU_TYPE" in
    rtx_6000)
        # Opt-in only. 48 GB VRAM is enough for the active 4-model pack
        # (peak gemma4:31b ~26 GB) but the rtx_6000 pool is the more
        # contended one historically; prefer rtx_pro_6000 unless that's
        # blocked.
        MEM_ARG="--mem=48G" ;;
    rtx_pro_6000)
        # Default. 80G mem cap per IT request 2026-04-27.
        MEM_ARG="--mem=80G" ;;
    *)
        echo "Error: --gpu-type must be rtx_6000 or rtx_pro_6000 (got: $GPU_TYPE)" >&2
        exit 1 ;;
esac

# --no-tools forces think=off (matrix-gate skips think=on/no-tools anyway)
# and the cell-builder below pins CONDITIONS to no-tools alone.
if [ "$NO_TOOLS" -eq 1 ]; then
    if [ -n "$THINK_MODES_OVERRIDE" ] \
        && [ "$THINK_MODES_OVERRIDE" != "off" ] \
        && [ "$THINK_MODES_OVERRIDE" != "default" ]; then
        echo "Error: --no-tools forces THINK_MODES to off|default; got --think-modes \"$THINK_MODES_OVERRIDE\"" >&2
        exit 1
    fi
fi

# Resolve effective think × cond axis values for cell generation.
DEFAULT_CONDITIONS=("${PDDL_DEFAULT_CONDITIONS[@]}")
DEFAULT_THINK_MODES=("${PDDL_DEFAULT_THINK_MODES[@]}")

if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    # Smoke iterates think × conds inside run_experiment.py.
    # One cell per model — sbatch SMOKE-fastpath consumes the cell.
    EFF_THINK=("default")
    EFF_COND=("@smoke@")
elif [ "$NO_TOOLS" -eq 1 ]; then
    EFF_THINK=("${THINK_MODES_OVERRIDE:-off}")
    EFF_COND=("no-tools")
else
    if [ -n "$THINK_MODES_OVERRIDE" ]; then
        read -ra EFF_THINK <<< "$THINK_MODES_OVERRIDE"
    else
        EFF_THINK=("${DEFAULT_THINK_MODES[@]}")
    fi
    EFF_COND=("${DEFAULT_CONDITIONS[@]}")
fi

# Build cells (model × think × cond) with matrix-gate skip:
# no-tools is reported only for think=off — no-tools/think=on cells dropped.
CELLS=()
for m in "${MODELS[@]}"; do
    for t in "${EFF_THINK[@]}"; do
        for c in "${EFF_COND[@]}"; do
            if [ "$c" = "no-tools" ] && [ "$t" != "off" ]; then
                continue
            fi
            CELLS+=("${m}|${t}|${c}")
        done
    done
done
N_CELLS=${#CELLS[@]}
if [ "$N_CELLS" -eq 0 ]; then
    echo "Error: cell list is empty after matrix-gate filter (think_modes=${EFF_THINK[*]} conds=${EFF_COND[*]})" >&2
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
#   no-tools cells: ~6h (4-task discriminative matrix, no chains).
#   smoke cells: ~30-45 min (matrix iteration internal to run_experiment.py).
if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    TIME_ARG=(--time=03:00:00)
elif [ "$NO_TOOLS" -eq 1 ]; then
    TIME_ARG=(--time=08:00:00)
else
    TIME_ARG=(--time=72:00:00)
fi

# Job name: single model uses the model tag; multi-model uses
# pddl_rtx_pack<count>_<first-tag>. With per-cell arrays %x is the same
# across array tasks of one submission and %J disambiguates per task.
# Note: run_condition_rtx.sbatch renames each array task at runtime via
# `scontrol update JobName=...` once it resolves its cell, so live `squeue`
# listings show pddl_<model>_<think>_<cond_tag> per task. Log filenames
# (%x-%J.out) keep the submit-time prefix below — they were resolved at
# job start, before the rename.
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

# Add --array only when N>1; single-cell submissions remain plain sbatch.
ARRAY_ARG=()
if [ "$N_CELLS" -gt 1 ]; then
    ARRAY_ARG=(--array="0-$((N_CELLS-1))")
fi

cmd=(sbatch
    --job-name="$JOB_NAME"
    --gpus="${GPU_TYPE}:1"
    "$MEM_ARG"
    "${TIME_ARG[@]}"
    "${ARRAY_ARG[@]}"
    --export="$EXPORT_LIST"
    "$SBATCH_FILE")

echo "--- rtx self-deploy submission ---" >&2
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
if [ "$NO_TOOLS" -eq 1 ]; then
    echo "  mode:        --no-tools (CONDITIONS=no-tools, TASKS=solve+validate_*)" >&2
fi
if [ "$SMOKE" -eq 1 ]; then
    echo "  mode:        --smoke (1 domain × 1 problem × 1 variant × 5 tasks × 2 conds × 2 think; output → results/smoke/fixed_<sha>_<ts>/)" >&2
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "  mode:        --smoke-shuffle (per-(model,task) random domain pick; output → results/smoke/shuffle_<sha>_<ts>/)" >&2
fi
if [ -n "$SHARD" ]; then
    echo "  shard:       $SHARD (SHA-256 partitioner; chains run only on shard 0)" >&2
fi
if [ -n "$CONTINUE_PARTIAL" ]; then
    echo "  cont-from:   $CONTINUE_PARTIAL (each cell seeds its OUT_DIR/trials.jsonl on first run only)" >&2
fi
if [ -n "$PARTIAL_K" ]; then
    echo "  partial:     K=$PARTIAL_K (per-domain fixture cap; single-task fast feedback slice)" >&2
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
fi
