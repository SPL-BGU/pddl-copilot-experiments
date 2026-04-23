#!/usr/bin/env bash
# Submit ONE rtx self-deploy job for a given model on the BGU cluster.
# Runs an isolated Apptainer Ollama server on a single GPU node, then runs
# run_experiment.py against localhost:11434 (no cis-ollama dependency).
#
# GPU routing by model:
#   gpt-oss:120b → rtx_pro_6000:1 (96 GB, required for 65 GB weights)
#   everything else → rtx_6000:1 (48 GB, larger pool, faster queue)
# Override with --gpu-type to force one or the other.
#
# Usage:
#   bash cluster-experimenting/submit_with_rtx.sh <model>
#   bash cluster-experimenting/submit_with_rtx.sh <model> --gpu-type rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh <model> --think-modes "on off"
#   bash cluster-experimenting/submit_with_rtx.sh <model> --dry-run
#
# Examples:
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B
#   bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b
#   bash cluster-experimenting/submit_with_rtx.sh gpt-oss:120b          # auto → rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh gemma4:31b --gpu-type rtx_pro_6000
#
# Think modes default to the same protocol as submit_all.sh:
#   gemma4:*  → "default" (no thinking mode in gemma)
#   all other → "on off"  (both modes run sequentially in one job)

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
MODEL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --gpu-type) shift; GPU_TYPE="$1"; shift ;;
        --think-modes) shift; THINK_MODES_OVERRIDE="$1"; shift ;;
        -h|--help)
            sed -n '1,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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
    echo "Usage: bash $0 <model> [--gpu-type rtx_6000|rtx_pro_6000] [--think-modes \"on off\"] [--dry-run]" >&2
    exit 1
fi

# Auto-select GPU type when not overridden.
if [ -z "$GPU_TYPE" ]; then
    case "$MODEL" in
        gpt-oss:120b|gpt-oss:120B)
            GPU_TYPE="rtx_pro_6000"
            echo "[auto] $MODEL needs ~77 GB VRAM → using rtx_pro_6000 (96 GB)" >&2 ;;
        *)
            GPU_TYPE="rtx_6000" ;;
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

# Auto-select think modes when not overridden.
if [ -n "$THINK_MODES_OVERRIDE" ]; then
    THINK_MODES="$THINK_MODES_OVERRIDE"
else
    case "$MODEL" in
        gemma4:*|gemma3:*|gemma2:*)
            THINK_MODES="default" ;;
        *)
            THINK_MODES="on off" ;;
    esac
fi

MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
JOB_NAME="pddl_rtx_${MODEL_TAG}"

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

cmd=(sbatch
    --job-name="$JOB_NAME"
    --gpus="${GPU_TYPE}:1"
    "$MEM_ARG"
    --export="ALL,MODEL=${MODEL},THINK_MODES=${THINK_MODES}"
    "$SBATCH_FILE")

echo "--- rtx self-deploy submission ---" >&2
echo "  model:       $MODEL" >&2
echo "  think modes: $THINK_MODES" >&2
echo "  GPU:         ${GPU_TYPE}:1" >&2
echo "  job name:    $JOB_NAME" >&2

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
