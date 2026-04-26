#!/usr/bin/env bash
# Submit ONE rtx self-deploy job for a given model on the BGU cluster.
# Runs an isolated Apptainer Ollama server on a single GPU node, then runs
# run_experiment.py against localhost:11434 (no cis-ollama dependency).
#
# GPU routing by model:
#   gpt-oss:120b    → rtx_pro_6000:1 (96 GB, required for 65 GB weights)
#   everything else → opportunistic: at submit time, queries `sinfo` for idle
#                     counts in `rtx6000` and `rtx_pro_6000` partitions and
#                     picks whichever has more idle-or-mixed nodes.
#                     Tiebreak prefers rtx_pro_6000 (typically less contended).
#                     Fallback when sinfo is unavailable: rtx_6000.
# Override with --gpu-type to force one pool.
#
# Usage:
#   bash cluster-experimenting/submit_with_rtx.sh <model>
#   bash cluster-experimenting/submit_with_rtx.sh <model> --no-tools
#   bash cluster-experimenting/submit_with_rtx.sh <model> --gpu-type rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh <model> --think-modes "on off"
#   bash cluster-experimenting/submit_with_rtx.sh <model> --dry-run
#
# Examples:
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B
#   bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b --no-tools
#   bash cluster-experimenting/submit_with_rtx.sh gpt-oss:120b          # auto → rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh gemma4:31b --gpu-type rtx_pro_6000
#
# --no-tools: shorthand for the baseline-only run. Pins THINK_MODES=off,
#   CONDITIONS=no-tools, TASKS=solve (no-tools is only meaningful for solve
#   with thinking off — chains and other tasks are skipped per the matrix
#   gate in run_condition_rtx.sbatch). Also passes --time=1:00:00 because
#   no-tools jobs measured 10–22 min wall on 2026-04-25 (default 2 days
#   wastes fairshare priority).
#
# Think modes default to "on off" (both run sequentially in one job so
# weights stay resident). Override with --think-modes "default" for models
# without a think kwarg (e.g. gemma4*).

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBATCH_FILE="$SCRIPT_DIR/run_condition_rtx.sbatch"

if [ ! -f "$SBATCH_FILE" ]; then
    echo "Error: $SBATCH_FILE not found." >&2
    exit 1
fi

DRY_RUN=0
GPU_TYPE=""
THINK_MODES_OVERRIDE=""
NO_TOOLS=0
MODEL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --gpu-type) shift; GPU_TYPE="$1"; shift ;;
        --think-modes) shift; THINK_MODES_OVERRIDE="$1"; shift ;;
        --no-tools) NO_TOOLS=1; shift ;;
        -h|--help)
            sed -n '1,38p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            if [ -z "$MODEL" ]; then MODEL="$1"
            else echo "Error: extra positional arg '$1' (model already set to '$MODEL')" >&2; exit 1
            fi
            shift ;;
    esac
done

if [ -z "$MODEL" ]; then
    echo "Usage: bash $0 <model> [--no-tools] [--gpu-type rtx_6000|rtx_pro_6000] [--think-modes \"on off\"] [--dry-run]" >&2
    exit 1
fi

# Auto-select GPU type when not overridden.
#
# 120b is hard-pinned to rtx_pro_6000 (only pool with 96 GB).
# Everything else: query sinfo for idle nodes in each pool and pick the more
# available one. Observed 2026-04-25: rtx_pro_6000 frequently has idle nodes
# while rtx6000 queues — opportunistic routing trims queue wait without
# capacity loss (per-job throughput is identical on both).
if [ -z "$GPU_TYPE" ]; then
    case "$MODEL" in
        gpt-oss:120b|gpt-oss:120B)
            GPU_TYPE="rtx_pro_6000"
            echo "[auto] $MODEL needs ~77 GB VRAM → using rtx_pro_6000 (96 GB)" >&2 ;;
        *)
            if ! command -v sinfo >/dev/null 2>&1; then
                # sinfo unavailable (e.g. --dry-run from laptop). Routing only
                # matters at actual submit time on the login node, so fall
                # back to historical default.
                GPU_TYPE="rtx_6000"
                echo "[auto] sinfo unavailable → falling back to rtx_6000 (routing decision deferred to submit)" >&2
            else
                # `set -e` + pipefail would abort on sinfo failure mid-pipe.
                # Wrap each call so a missing/empty partition just yields 0.
                free_6000=$( { sinfo -h -p rtx6000 -t idle,mix -o '%n' 2>/dev/null || true; } | wc -l | tr -d ' ')
                free_pro=$( { sinfo -h -p rtx_pro_6000 -t idle,mix -o '%n' 2>/dev/null || true; } | wc -l | tr -d ' ')
                if [ "${free_pro:-0}" -gt "${free_6000:-0}" ]; then
                    GPU_TYPE="rtx_pro_6000"
                    echo "[auto] rtx_pro_6000 (${free_pro} idle) > rtx6000 (${free_6000} idle) → routing to rtx_pro_6000" >&2
                elif [ "${free_6000:-0}" -gt "${free_pro:-0}" ]; then
                    GPU_TYPE="rtx_6000"
                    echo "[auto] rtx6000 (${free_6000} idle) > rtx_pro_6000 (${free_pro} idle) → routing to rtx_6000" >&2
                else
                    # Tiebreak: pro is typically less contended on this cluster.
                    GPU_TYPE="rtx_pro_6000"
                    echo "[auto] tie (${free_6000}=${free_pro}) → preferring rtx_pro_6000" >&2
                fi
            fi ;;
    esac
fi

case "$GPU_TYPE" in
    rtx_6000)
        MEM_ARG="--mem=48G"
        # Defensive gate per user spec: accidental 120b submission on rtx_6000
        # (48 GB) would fail VRAM sanity check at runtime, wasting queue wait.
        # Fail fast at submit time.
        case "$MODEL" in
            gpt-oss:120b|gpt-oss:120B)
                echo "Error: $MODEL (~65 GB weights) does NOT fit on rtx_6000 (48 GB)." >&2
                echo "       Options:" >&2
                echo "         1. Use rtx_pro_6000 (96 GB):" >&2
                echo "              bash $0 $MODEL --gpu-type rtx_pro_6000" >&2
                echo "         2. Route via cis-ollama (shared, no dedicated GPU):" >&2
                echo "              bash cluster-experimenting/submit_120b_cis.sh" >&2
                exit 2 ;;
        esac
        ;;
    rtx_pro_6000)
        MEM_ARG="--mem=96G" ;;
    *)
        echo "Error: --gpu-type must be rtx_6000 or rtx_pro_6000 (got: $GPU_TYPE)" >&2
        exit 1 ;;
esac

# --no-tools shorthand: pins single-task baseline-only run.
#   * THINK_MODES=off — no-tools/think=on is skipped by the matrix gate
#     anyway; making it explicit avoids wasted scheduling of a no-op cell.
#   * CONDITIONS=no-tools — single tools-off pass.
#   * TASKS=solve — no-tools is only meaningful for solve. The other 4
#     tasks (validate_*, simulate) require tool calls to be honest.
# Conflicts with --think-modes are flagged.
NO_TOOLS_EXPORTS=()
TIME_ARG=()
if [ "$NO_TOOLS" -eq 1 ]; then
    if [ -n "$THINK_MODES_OVERRIDE" ] && [ "$THINK_MODES_OVERRIDE" != "off" ]; then
        echo "Error: --no-tools forces THINK_MODES=off; got --think-modes \"$THINK_MODES_OVERRIDE\"" >&2
        exit 1
    fi
    THINK_MODES="off"
    NO_TOOLS_EXPORTS=(CONDITIONS=no-tools TASKS=solve)
    # No-tools observed at 10–22 min wall (2026-04-25). 1 hour gives ≥3×
    # headroom on the slowest run; tighter --time helps SLURM fairshare.
    TIME_ARG=(--time=1:00:00)
elif [ -n "$THINK_MODES_OVERRIDE" ]; then
    THINK_MODES="$THINK_MODES_OVERRIDE"
else
    THINK_MODES="on off"
fi

MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
JOB_NAME="pddl_rtx_${MODEL_TAG}"
if [ "$NO_TOOLS" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_notools"
fi

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

# Compose --export list. ALL inherits caller env; we then layer MODEL,
# THINK_MODES, and (when --no-tools) CONDITIONS + TASKS.
EXPORT_LIST="ALL,MODEL=${MODEL},THINK_MODES=${THINK_MODES}"
for kv in "${NO_TOOLS_EXPORTS[@]}"; do
    EXPORT_LIST="${EXPORT_LIST},${kv}"
done

cmd=(sbatch
    --job-name="$JOB_NAME"
    --gpus="${GPU_TYPE}:1"
    "$MEM_ARG"
    "${TIME_ARG[@]}"
    --export="$EXPORT_LIST"
    "$SBATCH_FILE")

echo "--- rtx self-deploy submission ---" >&2
echo "  model:       $MODEL" >&2
echo "  think modes: $THINK_MODES" >&2
echo "  GPU:         ${GPU_TYPE}:1" >&2
echo "  job name:    $JOB_NAME" >&2
if [ "$NO_TOOLS" -eq 1 ]; then
    echo "  mode:        --no-tools (CONDITIONS=no-tools, TASKS=solve, --time=1:00:00)" >&2
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo "  DRY: ${cmd[*]}" >&2
else
    jid=$("${cmd[@]}" | awk '{print $NF}')
    echo "  submitted as job $jid" >&2
    echo "$jid"
    echo "" >&2
    echo "Monitor:  squeue -j $jid" >&2
    echo "Log:      $REPO_ROOT/cluster-experimenting/logs/${JOB_NAME}-${jid}.out" >&2
    echo "Results:  $REPO_ROOT/results/slurm_rtx_${MODEL_TAG}_<think>_<cond>_${jid}/" >&2
fi
