#!/usr/bin/env bash
# Submit ONE rtx self-deploy job covering one OR MORE models on the BGU
# cluster. Runs an isolated Apptainer Ollama server on a single GPU node,
# then runs run_experiment.py against localhost:<port> (no cis-ollama
# dependency).
#
# Multi-model packing: list multiple models as positional args and they will
# be processed sequentially in the SAME job, sharing the apptainer/serve
# startup overhead. Ollama's MAX_LOADED_MODELS=1 evicts the previous model
# before loading the next, so peak VRAM is bounded by the largest model in
# the set, not the sum.
#
# GPU routing:
#   any of MODELS == gpt-oss:120b → rtx_pro_6000:1 (96 GB, required for 65 GB weights)
#   everything else               → opportunistic: at submit time, queries `sinfo`
#                                   for idle counts in `rtx6000` and `rtx_pro_6000`
#                                   partitions and picks whichever has more idle-or-mixed
#                                   nodes. Tiebreak prefers rtx_pro_6000.
#                                   Fallback when sinfo is unavailable: rtx_6000.
# Override with --gpu-type to force one pool.
#
# Resource policy (post 2026-04-27 IT request):
#   * No --cpus-per-task — uses cluster default cpus-per-gpu.
#   * --mem cap: 48G on rtx_6000, 80G on rtx_pro_6000 (was 96G; lowered
#     per IT email "no more than 80GB RAM for rtx6000 GPUs").
#
# Usage:
#   bash cluster-experimenting/submit_with_rtx.sh <model> [<model>...]
#   bash cluster-experimenting/submit_with_rtx.sh --all
#   bash cluster-experimenting/submit_with_rtx.sh <model> --no-tools
#   bash cluster-experimenting/submit_with_rtx.sh <m1> <m2> --gpu-type rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh <model> --think-modes "on off"
#   bash cluster-experimenting/submit_with_rtx.sh <model> --dry-run
#
# Examples:
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B gpt-oss:20b Qwen3.5:27b gemma4:31b
#   bash cluster-experimenting/submit_with_rtx.sh --all                  # full sweep, 2 jobs
#   bash cluster-experimenting/submit_with_rtx.sh --all --no-tools       # full no-tools sweep, 2 jobs
#   bash cluster-experimenting/submit_with_rtx.sh gpt-oss:20b --no-tools
#   bash cluster-experimenting/submit_with_rtx.sh gpt-oss:120b           # auto → rtx_pro_6000
#
# --all: shorthand for the 5 paper models, submitted as TWO jobs:
#   Job A: Qwen3.5:0.8B gpt-oss:20b Qwen3.5:27b gemma4:31b on rtx_6000
#   Job B: gpt-oss:120b on rtx_pro_6000
# This packs the 4 small/mid models in one job (sharing serve startup) while
# isolating 120b on the only pool that fits its 65 GB weights. Splits the
# matrix into 2 jobs total instead of 5, while staying inside fairshare-
# friendly time limits.
#
# --no-tools: shorthand for the single-task no-tools matrix. Pins
#   THINK_MODES=off, CONDITIONS=no-tools, and TASKS to the four discriminative
#   single-task evals: solve + validate_domain + validate_problem +
#   validate_plan. Negative fixtures (ISS-001, 2026-04-26) ride along the
#   matching task automatically. `simulate` stays excluded (non-discriminative
#   keyword grader). Chains are skipped by the matrix gate in
#   run_condition_rtx.sbatch. --time scales linearly with model count
#   (4h base + 4h per extra model).
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
ALL=0
MODELS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --gpu-type) shift; GPU_TYPE="$1"; shift ;;
        --think-modes) shift; THINK_MODES_OVERRIDE="$1"; shift ;;
        --no-tools) NO_TOOLS=1; shift ;;
        --all) ALL=1; shift ;;
        -h|--help)
            sed -n '1,68p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            MODELS+=("$1"); shift ;;
    esac
done

# --all expands into two recursive submits: small/mid pack + 120b alone.
# This keeps the 5-model sweep at 2 jobs while isolating 120b on rtx_pro_6000.
if [ "$ALL" -eq 1 ]; then
    if [ "${#MODELS[@]}" -gt 0 ]; then
        echo "Error: --all is exclusive with explicit model args" >&2
        exit 1
    fi
    extra_args=()
    [ "$NO_TOOLS" -eq 1 ] && extra_args+=(--no-tools)
    [ "$DRY_RUN" -eq 1 ] && extra_args+=(--dry-run)
    [ -n "$THINK_MODES_OVERRIDE" ] && extra_args+=(--think-modes "$THINK_MODES_OVERRIDE")
    bash "$0" Qwen3.5:0.8B gpt-oss:20b Qwen3.5:27b gemma4:31b "${extra_args[@]}"
    bash "$0" gpt-oss:120b "${extra_args[@]}"
    exit 0
fi

if [ "${#MODELS[@]}" -eq 0 ]; then
    echo "Usage: bash $0 <model> [<model>...] [--all] [--no-tools] [--gpu-type rtx_6000|rtx_pro_6000] [--think-modes \"on off\"] [--dry-run]" >&2
    exit 1
fi

# Detect whether 120b is in the model set.
HAS_120B=0
for m in "${MODELS[@]}"; do
    case "$m" in
        gpt-oss:120b|gpt-oss:120B) HAS_120B=1 ;;
    esac
done

# Auto-select GPU type when not overridden.
#
# 120b in the set is hard-pinned to rtx_pro_6000 (only pool with 96 GB).
# Everything else: query sinfo for idle nodes in each pool and pick the more
# available one. Observed 2026-04-25: rtx_pro_6000 frequently has idle nodes
# while rtx6000 queues — opportunistic routing trims queue wait without
# capacity loss (per-job throughput is identical on both).
if [ -z "$GPU_TYPE" ]; then
    if [ "$HAS_120B" -eq 1 ]; then
        GPU_TYPE="rtx_pro_6000"
        echo "[auto] gpt-oss:120b in MODELS → using rtx_pro_6000 (96 GB)" >&2
    elif ! command -v sinfo >/dev/null 2>&1; then
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
    fi
fi

case "$GPU_TYPE" in
    rtx_6000)
        MEM_ARG="--mem=48G"
        # Defensive gate: 120b (~65 GB weights) does not fit on rtx_6000 (48 GB).
        if [ "$HAS_120B" -eq 1 ]; then
            echo "Error: gpt-oss:120b does NOT fit on rtx_6000 (48 GB)." >&2
            echo "       Options:" >&2
            echo "         1. Use rtx_pro_6000 (96 GB):" >&2
            echo "              bash $0 ${MODELS[*]} --gpu-type rtx_pro_6000" >&2
            echo "         2. Drop 120b from the model list and submit it separately." >&2
            exit 2
        fi
        ;;
    rtx_pro_6000)
        # 80G cap per IT request 2026-04-27 (was 96G); host-RAM usage is
        # dominated by node-local /tmp model cache (~65 GB peak for 120b)
        # which fits inside 80G.
        MEM_ARG="--mem=80G" ;;
    *)
        echo "Error: --gpu-type must be rtx_6000 or rtx_pro_6000 (got: $GPU_TYPE)" >&2
        exit 1 ;;
esac

# --no-tools shorthand: pins the single-task no-tools baseline matrix.
NO_TOOLS_EXPORTS=()
TIME_ARG=()
if [ "$NO_TOOLS" -eq 1 ]; then
    if [ -n "$THINK_MODES_OVERRIDE" ] \
        && [ "$THINK_MODES_OVERRIDE" != "off" ] \
        && [ "$THINK_MODES_OVERRIDE" != "default" ]; then
        echo "Error: --no-tools forces THINK_MODES to off|default; got --think-modes \"$THINK_MODES_OVERRIDE\"" >&2
        exit 1
    fi
    THINK_MODES="${THINK_MODES_OVERRIDE:-off}"
    NO_TOOLS_EXPORTS=(CONDITIONS=no-tools "TASKS=solve validate_domain validate_problem validate_plan")
    # Solve-only no-tools measured 10–22 min wall (2026-04-25). Adding the
    # three validate_* tasks scales to ~350 evals/model. With multi-model
    # packing, scale time linearly: 4h base + 4h per extra model.
    nt_hours=$(( 4 + 4 * (${#MODELS[@]} - 1) ))
    TIME_ARG=(--time=${nt_hours}:00:00)
elif [ -n "$THINK_MODES_OVERRIDE" ]; then
    THINK_MODES="$THINK_MODES_OVERRIDE"
else
    THINK_MODES="on off"
fi

# Multi-model regular sweep needs more wall time than the 2d sbatch default.
# Empirical wall: ~10–17h per model for full {on, off} × 4 tools_conds. With
# 4 models packed, set 4d (still well under main partition's 7d cap).
# Single-model regular sweep keeps the 2d default.
if [ "$NO_TOOLS" -eq 0 ] && [ "${#MODELS[@]}" -gt 1 ]; then
    TIME_ARG=(--time=4-00:00:00)
fi

# Job name: single model uses the model tag; multi-model uses
# pddl_rtx_pack<count>_<first-tag> so the .out file is searchable but
# distinct from the prior single-model layout.
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

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

# Compose --export list. ALL inherits caller env; we then layer MODELS,
# THINK_MODES, and (when --no-tools) CONDITIONS + TASKS.
MODELS_STR="${MODELS[*]}"
EXPORT_LIST="ALL,MODELS=${MODELS_STR},THINK_MODES=${THINK_MODES}"
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
echo "  models:      ${MODELS[*]}" >&2
echo "  think modes: $THINK_MODES" >&2
echo "  GPU:         ${GPU_TYPE}:1" >&2
echo "  mem:         $MEM_ARG" >&2
if [ "${#TIME_ARG[@]}" -gt 0 ]; then
    echo "  time:        ${TIME_ARG[*]}" >&2
fi
echo "  job name:    $JOB_NAME" >&2
if [ "$NO_TOOLS" -eq 1 ]; then
    echo "  mode:        --no-tools (CONDITIONS=no-tools, TASKS=\"solve validate_domain validate_problem validate_plan\")" >&2
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
    echo "Results:  $REPO_ROOT/results/slurm_<model>_<think>_<cond>_${jid}/  (one dir per (model,think,cond))" >&2
fi
