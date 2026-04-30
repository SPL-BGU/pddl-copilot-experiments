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
#   default → rtx_pro_6000:1 (96 GB, --mem=80G). Hard-pinned as the sole
#             self-deploy GPU class so peak VRAM and host RAM are constant
#             across the active sweep. The 4-model pack peaks at
#             qwen3.6:35b (~24 GB) under MAX_LOADED_MODELS=1, well inside 96 GB.
#   --gpu-type rtx_6000 → opt-in escape hatch (48 GB VRAM, --mem=48G).
#                         Use only when rtx_pro_6000 is queue-saturated
#                         and the requested models all fit.
#
# Resource policy (post 2026-04-27 IT request):
#   * No --cpus-per-task — uses cluster default cpus-per-gpu.
#   * --mem cap: 80G on rtx_pro_6000 (default), 48G on rtx_6000 (opt-in).
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
#   bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b
#   bash cluster-experimenting/submit_with_rtx.sh --all                  # full sweep, ONE packed job on rtx_pro_6000
#   bash cluster-experimenting/submit_with_rtx.sh --all --no-tools       # full no-tools sweep, ONE packed job
#   bash cluster-experimenting/submit_with_rtx.sh gemma4:31b --no-tools
#
# --all: shorthand for the 4 active models, packed in ONE job:
#   Pack: Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b
# All four fit in ≤26 GB resident (gemma4:31b sets the peak), so
# MAX_LOADED_MODELS=1 sequencing keeps everything well within rtx_pro_6000's
# 96 GB VRAM. Roster history: 2026-04-29 swap (Qwen3.5:27b/35b → qwen3.6
# successors; gpt-oss:20b → nemotron-3-nano:30b for non-Qwen/Gemma diversity).
# 2026-04-30 follow-up dropped nemotron-3-nano:30b after smoke 17274424
# confirmed deterministic Hermes XML parse failures on the same 4 cells
# pre- and post-num_predict bump (4096→6144), establishing the failure as
# content-dependent, not budget-dependent. See development/CHANGELOG.md.
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
SMOKE=0
SMOKE_SHUFFLE=0
SHARD=""
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
        -h|--help)
            sed -n '1,68p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            MODELS+=("$1"); shift ;;
    esac
done

# --smoke / --smoke-shuffle: pin the 4-model pack and full think × cond
# matrix; run_experiment.py auto-overrides --num-variants/--chain-samples
# and skips the inner THINK × CONDITIONS loop in the sbatch (the smoke
# wrapper iterates think internally).
if [ "$SMOKE" -eq 1 ] && [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "Error: --smoke and --smoke-shuffle are mutually exclusive" >&2
    exit 1
fi
if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    if [ "$ALL" -eq 1 ] || [ "$NO_TOOLS" -eq 1 ] || [ -n "$THINK_MODES_OVERRIDE" ]; then
        echo "Error: --smoke[-shuffle] is exclusive with --all/--no-tools/--think-modes" >&2
        exit 1
    fi
    # No explicit models → default to the 4-model paper pack. Explicit
    # models override the pack and smoke just those (used to retest a
    # single model after a fix without re-running the full pack).
    if [ "${#MODELS[@]}" -eq 0 ]; then
        MODELS=(Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b)
    fi
    THINK_MODES_OVERRIDE="default"  # smoke iterates think internally
fi

# --all expands into a single 4-model pack on rtx_pro_6000.
# All five fit in ≤24 GB resident under MAX_LOADED_MODELS=1 sequencing —
# qwen3.6:35b A3B MoE (~24 GB) sets the peak. rtx_pro_6000's 96 GB VRAM has
# ample headroom for KV cache scaling.
if [ "$ALL" -eq 1 ]; then
    if [ "${#MODELS[@]}" -gt 0 ]; then
        echo "Error: --all is exclusive with explicit model args" >&2
        exit 1
    fi
    extra_args=()
    [ "$NO_TOOLS" -eq 1 ] && extra_args+=(--no-tools)
    [ "$DRY_RUN" -eq 1 ] && extra_args+=(--dry-run)
    [ -n "$THINK_MODES_OVERRIDE" ] && extra_args+=(--think-modes "$THINK_MODES_OVERRIDE")
    [ -n "$GPU_TYPE" ] && extra_args+=(--gpu-type "$GPU_TYPE")
    bash "$0" Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b "${extra_args[@]}"
    exit 0
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
        # (peak qwen3.6:35b ~24 GB) but the rtx_6000 pool is the more
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
    # three validate_* tasks scales to ~350 evals/model. Post 2026-04-29
    # num_predict 1024/1536→4096 + num_ctx 8192→16384 bump, per-model wall
    # ~doubles (33–41% of non-solve trials previously truncated mid-emission
    # now run up to 4× longer). Cap = 6h base + 6h per extra model.
    nt_hours=$(( 6 + 6 * (${#MODELS[@]} - 1) ))
    TIME_ARG=(--time=${nt_hours}:00:00)
elif [ -n "$THINK_MODES_OVERRIDE" ]; then
    THINK_MODES="$THINK_MODES_OVERRIDE"
else
    THINK_MODES="on off"
fi

# Multi-model regular sweep needs more wall time than the 2d sbatch default.
# Empirical wall pre 2026-04-29: ~10–17h per model for full {on, off} ×
# 4 tools_conds. Post-bump (num_predict 1024/1536→4096; num_ctx 8192→16384;
# num_ctx_thinking 12288→16384), per-model wall ~doubles to ~20–35h. With
# 4 models packed (--all), 6d (144h) covers the full pack with margin and
# stays under main partition's 7d cap. Single-model regular sweep keeps
# the 2d sbatch default — ~20h post-bump fits in 48h.
if [ "$NO_TOOLS" -eq 0 ] && [ "${#MODELS[@]}" -gt 1 ]; then
    TIME_ARG=(--time=6-00:00:00)
fi

# Smoke wallclock: ~80 evals across 4 models in one packed job. Pre-bump
# (2026-04-29) measured 12–14 min/model on rtx_pro_6000 (ref: job 17263071).
# Post num_predict/num_ctx bump, per-model wall lands ~25–35 min, so 4-model
# pack ~150 min. 3h cap covers Ollama startup + model warmup + slowest cell
# with margin.
if [ "$SMOKE" -eq 1 ] || [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    TIME_ARG=(--time=03:00:00)
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
if [ "$SMOKE" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_smoke"
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    JOB_NAME="${JOB_NAME}_smoke-shuffle"
fi

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

# Compose --export list. ALL inherits caller env; we then layer MODELS,
# THINK_MODES, (when --no-tools) CONDITIONS + TASKS, and the smoke/shard
# env vars consumed by run_condition_rtx.sbatch.
MODELS_STR="${MODELS[*]}"
EXPORT_LIST="ALL,MODELS=${MODELS_STR},THINK_MODES=${THINK_MODES}"
for kv in "${NO_TOOLS_EXPORTS[@]}"; do
    EXPORT_LIST="${EXPORT_LIST},${kv}"
done
if [ "$SMOKE" -eq 1 ]; then
    EXPORT_LIST="${EXPORT_LIST},SMOKE=1"
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    EXPORT_LIST="${EXPORT_LIST},SMOKE_SHUFFLE=1"
fi
if [ -n "$SHARD" ]; then
    EXPORT_LIST="${EXPORT_LIST},SHARD=${SHARD}"
fi

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
if [ "$SMOKE" -eq 1 ]; then
    echo "  mode:        --smoke (1 domain × 1 problem × 1 variant × 5 tasks × 2 conds × 2 think; output → results/smoke_<sha>_<ts>/)" >&2
fi
if [ "$SMOKE_SHUFFLE" -eq 1 ]; then
    echo "  mode:        --smoke-shuffle (per-(model,task) random domain pick; output → results/smoke_shuffle_<sha>_<ts>/)" >&2
fi
if [ -n "$SHARD" ]; then
    echo "  shard:       $SHARD (SHA-256 partitioner; chains run only on shard 0)" >&2
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
