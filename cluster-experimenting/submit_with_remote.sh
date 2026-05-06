#!/usr/bin/env bash
# Submit a SLURM job array on the BGU CIS cluster covering one or more
# (model, think_mode, condition) cells. Each array task connects to a
# REMOTE Ollama server (e.g. on Vast.ai) instead of self-deploying one
# on a compute-node GPU. Mirrors submit_with_rtx.sh, dropping the GPU
# allocation flags.
#
# Pre-flight: a Vast pool must be live. Run once per sweep:
#   N=4 bash cluster-experimenting/vast/deploy-ollama.sh
#   bash cluster-experimenting/vast/smoke-test.sh
#
# Cell-array semantics, matrix gating, --continue-partial, --partial,
# --shard, --smoke[-shuffle], --exclude, --think-modes, and --no-tools
# are identical to submit_with_rtx.sh. Differences:
#   - No --gpu-type / --mem flags: the cluster job has no GPU.
#   - Cells are routed to vast/pool.txt slots via SLURM_ARRAY_TASK_ID % N.
#   - Per-cell --time defaults are smaller because the bottleneck is the
#     remote box, not local model swap; round-trip-bound cells finish
#     faster than VRAM-bound ones did.
#
# Usage:
#   bash cluster-experimenting/submit_with_remote.sh <model> [<model>...]
#   bash cluster-experimenting/submit_with_remote.sh --all
#   bash cluster-experimenting/submit_with_remote.sh <model> --no-tools
#   bash cluster-experimenting/submit_with_remote.sh <model> --think-modes "on off"
#   bash cluster-experimenting/submit_with_remote.sh <model> --dry-run

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBATCH_FILE="$SCRIPT_DIR/run_condition_remote.sbatch"
POOL_FILE="${POOL_FILE:-$SCRIPT_DIR/vast/pool.txt}"
TOKEN_FILE="${TOKEN_FILE:-$SCRIPT_DIR/vast/.token}"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

if [ ! -f "$SBATCH_FILE" ]; then
    echo "Error: $SBATCH_FILE not found." >&2
    exit 1
fi

# Pool gating: don't queue a job when the remote endpoints aren't ready.
# Defer the actual reachability check to vast/smoke-test.sh — here we just
# ensure pool.txt and .token exist so the per-cell preflight in the sbatch
# can read them.
if [ ! -s "$POOL_FILE" ] || [ ! -s "$TOKEN_FILE" ]; then
    echo "Error: Vast pool not deployed yet." >&2
    echo "       Expected: $POOL_FILE and $TOKEN_FILE" >&2
    echo "       Run:      N=<concurrent_jobs> bash cluster-experimenting/vast/deploy-ollama.sh" >&2
    echo "       Then:     bash cluster-experimenting/vast/smoke-test.sh" >&2
    exit 1
fi

DRY_RUN=0
THINK_MODES_OVERRIDE=""
NO_TOOLS=0
ALL=0
SMOKE=0
SMOKE_SHUFFLE=0
SHARD=""
CONTINUE_PARTIAL=""
PARTIAL_K=""
EXCLUDE_NODES=""
MODELS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --think-modes) shift; THINK_MODES_OVERRIDE="$1"; shift ;;
        --no-tools) NO_TOOLS=1; shift ;;
        --all) ALL=1; shift ;;
        --smoke) SMOKE=1; shift ;;
        --smoke-shuffle) SMOKE_SHUFFLE=1; shift ;;
        --shard) shift; SHARD="$1"; shift ;;
        --continue-partial) shift; CONTINUE_PARTIAL="$1"; shift ;;
        --partial) shift; PARTIAL_K="$1"; shift ;;
        --exclude) shift; EXCLUDE_NODES="$1"; shift ;;
        -h|--help)
            sed -n '1,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

if [ -n "$CONTINUE_PARTIAL" ]; then
    if [ ! -f "${CONTINUE_PARTIAL}/trials.jsonl" ]; then
        echo "Error: --continue-partial: ${CONTINUE_PARTIAL}/trials.jsonl not found" >&2
        exit 1
    fi
fi

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

if [ "$ALL" -eq 1 ]; then
    if [ "${#MODELS[@]}" -gt 0 ]; then
        echo "Error: --all is exclusive with explicit model args" >&2
        exit 1
    fi
    MODELS=("${PDDL_DEFAULT_MODELS[@]}")
fi

if [ "${#MODELS[@]}" -eq 0 ]; then
    echo "Usage: bash $0 <model> [<model>...] [--all] [--no-tools] [--think-modes \"on off\"] [--dry-run]" >&2
    exit 1
fi

if [ "$NO_TOOLS" -eq 1 ]; then
    if [ -n "$THINK_MODES_OVERRIDE" ] \
        && [ "$THINK_MODES_OVERRIDE" != "off" ] \
        && [ "$THINK_MODES_OVERRIDE" != "default" ]; then
        echo "Error: --no-tools forces THINK_MODES to off|default; got --think-modes \"$THINK_MODES_OVERRIDE\"" >&2
        exit 1
    fi
fi

DEFAULT_CONDITIONS=("${PDDL_DEFAULT_CONDITIONS[@]}")
DEFAULT_THINK_MODES=("${PDDL_DEFAULT_THINK_MODES[@]}")

if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
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

# Pool size warning: if more cells than pool URLs, multiple cells share a
# Vast box (Ollama serializes them via NUM_PARALLEL=4). Fine for sequential
# workloads, slower than full fan-out — surface it so the user can resize
# the pool before submitting.
POOL_N=$(awk 'NF && $1 !~ /^#/' "$POOL_FILE" | wc -l)
if [ "$N_CELLS" -gt "$POOL_N" ]; then
    echo "Note: ${N_CELLS} cells will share ${POOL_N} Vast box(es) (slot = task_id % pool)." >&2
    echo "      For full fan-out, redeploy with N=${N_CELLS}." >&2
fi

if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    TIME_ARG=(--time=03:00:00)
elif [ "$NO_TOOLS" -eq 1 ]; then
    TIME_ARG=(--time=08:00:00)
else
    TIME_ARG=(--time=72:00:00)
fi

if [ "${#MODELS[@]}" -eq 1 ]; then
    MODEL_TAG=$(echo "${MODELS[0]}" | tr '/:.' '___')
    JOB_NAME="pddl_remote_${MODEL_TAG}"
else
    FIRST_TAG=$(echo "${MODELS[0]}" | tr '/:.' '___')
    JOB_NAME="pddl_remote_pack${#MODELS[@]}_${FIRST_TAG}"
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

EXPORT_LIST="ALL,CELLS_LIST=${CELLS_LIST},POOL_FILE=${POOL_FILE},TOKEN_FILE=${TOKEN_FILE}"
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

ARRAY_ARG=()
if [ "$N_CELLS" -gt 1 ]; then
    ARRAY_ARG=(--array="0-$((N_CELLS-1))")
fi

EXCLUDE_ARG=()
if [ -n "$EXCLUDE_NODES" ]; then
    EXCLUDE_ARG=(--exclude="$EXCLUDE_NODES")
fi

cmd=(sbatch
    --job-name="$JOB_NAME"
    "${TIME_ARG[@]}"
    "${ARRAY_ARG[@]}"
    "${EXCLUDE_ARG[@]}"
    --export="$EXPORT_LIST"
    "$SBATCH_FILE")

echo "--- remote-Ollama submission ---" >&2
echo "  models:      ${MODELS[*]}" >&2
if [ "$N_CELLS" -gt 1 ]; then
    echo "  cells:       $N_CELLS (array fan-out 0-$((N_CELLS-1)))" >&2
else
    echo "  cells:       1 (single sbatch, no array)" >&2
fi
echo "  pool size:   $POOL_N URL(s) ($POOL_FILE)" >&2
echo "  time/cell:   ${TIME_ARG[*]}" >&2
echo "  job name:    $JOB_NAME" >&2
if [ "$NO_TOOLS" -eq 1 ]; then
    echo "  mode:        --no-tools" >&2
fi
if [ "$SMOKE" -eq 1 ]; then
    echo "  mode:        --smoke" >&2
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "  mode:        --smoke-shuffle" >&2
fi
if [ -n "$SHARD" ]; then
    echo "  shard:       $SHARD" >&2
fi
if [ -n "$CONTINUE_PARTIAL" ]; then
    echo "  cont-from:   $CONTINUE_PARTIAL" >&2
fi
if [ -n "$PARTIAL_K" ]; then
    echo "  partial:     K=$PARTIAL_K" >&2
fi
if [ -n "$EXCLUDE_NODES" ]; then
    echo "  exclude:     $EXCLUDE_NODES" >&2
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
    echo "Results:  $REPO_ROOT/results/slurm_<model>_<think>_<cond>/" >&2
fi
