#!/usr/bin/env bash
# submit_planbench.sh — dispatch the PlanBench arm sbatch one-per-model.
#
# Each model gets its own sbatch on rtx_6000:1 (same GPU class as the
# 5-task arm) that walks (task × config) in-process for cache locality.
# Mirrors the shape of submit_with_rtx.sh but with PlanBench's (task,
# config) axes instead of (think, condition).
#
# Models are canonical tags resolved to HF ids by vllm_lookup
# (lib/defaults.sh) — must be in PDDL_VLLM_VERIFIED_MODELS. The vLLM server
# is self-deployed per-job by run_planbench_rtx.sbatch (Ollama retired
# 2026-05-18; see CHANGELOG 2026-06-02).
#
# Walltime is passed on the CLI (overrides the sbatch's #SBATCH --time),
# mirroring submit_with_rtx.sh. --smoke defaults to a SHORT 03:00:00 so the
# job backfills into idle-GPU gaps instead of pending on (Priority) behind
# higher-priority reservations (a 48h request can't slot into a busy
# rtx_6000 partition). Full runs default to 2-00:00:00; override with --time.
#
# --gpu picks the GPU class (default rtx_6000, same as the 5-task arm). The
# small smoke models (Qwen3.5:0.8B/4B) fit on a 24GB rtx_3090/rtx_4090 — use
# --gpu rtx_3090 --gpu-mem-util 0.80 to run on free 3090/4090 capacity when
# the rtx_6000 pool is saturated. Big AWQ models still need rtx_6000.
#
# --tools selects the v2 MCP-tools-on arm (ISS-022): the model consults the
# pddl-copilot MCP planner/validator before answering. It runs
# run_planbench_tools_rtx.sbatch (engine pddl_copilot__vllm-tools__<tag>,
# .venv-tools, plugin pre-warm) instead of the v1 vanilla sbatch.
#
# Usage:
#   bash submit_planbench.sh --models Qwen3.5:0.8B Qwen3.5:4B
#   bash submit_planbench.sh --models Qwen3.5:0.8B --tasks t1 t3 --configs blocksworld
#   bash submit_planbench.sh --smoke              # 1 model × 1 task × 1 config × 3 instances
#   bash submit_planbench.sh --smoke --gpu rtx_3090 --gpu-mem-util 0.80
#   bash submit_planbench.sh --tools --smoke --gpu rtx_3090 --gpu-mem-util 0.80  # v2 tools smoke
#   bash submit_planbench.sh --time 12:00:00 --models Qwen3.5:0.8B
#   bash submit_planbench.sh --dry-run --models Qwen3.5:0.8B

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

MODELS=()
TASKS=""
CONFIGS=""
INSTANCES=""
THINK="off"
TIME_OVERRIDE=""
GPU_TYPE="rtx_6000"
GPU_MEM_UTIL_OVERRIDE=""
SMOKE=0
DRY_RUN=0
TOOLS=0
BASE=0
NUM_PREDICT_OVERRIDE=""

usage() {
    sed -n '2,37p' "$0" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --models)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MODELS+=("$1"); shift
            done
            ;;
        --tasks)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                TASKS="$TASKS $1"; shift
            done
            TASKS="${TASKS# }"
            ;;
        --configs)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                CONFIGS="$CONFIGS $1"; shift
            done
            CONFIGS="${CONFIGS# }"
            ;;
        --instances)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                INSTANCES="$INSTANCES $1"; shift
            done
            INSTANCES="${INSTANCES# }"
            ;;
        --think) THINK="$2"; shift 2 ;;
        --time) TIME_OVERRIDE="$2"; shift 2 ;;
        --gpu) GPU_TYPE="$2"; shift 2 ;;
        --gpu-mem-util) GPU_MEM_UTIL_OVERRIDE="$2"; shift 2 ;;
        --smoke) SMOKE=1; shift ;;
        --tools) TOOLS=1; shift ;;
        --base) BASE=1; shift ;;
        --num-predict) NUM_PREDICT_OVERRIDE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown arg: $1" >&2; usage ;;
    esac
done

# Defaults
if [[ "$SMOKE" -eq 1 ]]; then
    [[ "${#MODELS[@]}" -eq 0 ]] && MODELS=("${PDDL_DEFAULT_MODELS[0]}")
    TASKS="${TASKS:-t1}"
    CONFIGS="${CONFIGS:-blocksworld}"
    INSTANCES="${INSTANCES:-2 3 4}"
elif [[ "${#MODELS[@]}" -eq 0 ]]; then
    MODELS=("${PDDL_DEFAULT_MODELS[@]}")
fi
TASKS="${TASKS:-$PDDL_PLANBENCH_DEFAULT_TASKS}"
CONFIGS="${CONFIGS:-$PDDL_PLANBENCH_DEFAULT_CONFIGS}"

# Walltime, passed --time on the CLI (overrides the sbatch directive). Short
# for smoke so it backfills; explicit override always wins.
if [[ -n "$TIME_OVERRIDE" ]]; then
    TIME="$TIME_OVERRIDE"
elif [[ "$SMOKE" -eq 1 ]]; then
    TIME="03:00:00"
else
    TIME="2-00:00:00"
fi

echo "PlanBench dispatch:"
echo "  models   = ${MODELS[*]}"
echo "  tasks    = $TASKS"
echo "  configs  = $CONFIGS"
echo "  instances= ${INSTANCES:-<full>}"
echo "  think    = $THINK"
echo "  time     = $TIME"
echo "  gpu      = ${GPU_TYPE}:1${GPU_MEM_UTIL_OVERRIDE:+  (mem-util=$GPU_MEM_UTIL_OVERRIDE)}"
echo "  smoke    = $SMOKE"
echo "  tools    = $TOOLS"
echo "  base     = $BASE"
echo "  num_pred = ${NUM_PREDICT_OVERRIDE:-<engine default 4096>}"
[[ "$DRY_RUN" -eq 1 ]] && echo "  (dry-run — not submitting)"

if [[ "$TOOLS" -eq 1 && "$BASE" -eq 1 ]]; then
    echo "Error: --tools and --base are mutually exclusive" >&2; exit 1
fi
# --tools → v2 MCP-tools-on sbatch (engine vllm-tools). --base → v1 sbatch but
# engine vllm-base (the v2 no-tools baseline, own results dir, v1 vllm__ corpus
# untouched). Neither → the v1 vanilla leaderboard sbatch (engine vllm).
if [[ "$TOOLS" -eq 1 ]]; then
    SBATCH_FILE="$SCRIPT_DIR/run_planbench_tools_rtx.sbatch"
    JOB_KIND="tools_"
elif [[ "$BASE" -eq 1 ]]; then
    SBATCH_FILE="$SCRIPT_DIR/run_planbench_rtx.sbatch"
    JOB_KIND="base_"
else
    SBATCH_FILE="$SCRIPT_DIR/run_planbench_rtx.sbatch"
    JOB_KIND=""
fi

for MODEL in "${MODELS[@]}"; do
    MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
    JOB_NAME="pddl_planbench_${JOB_KIND}${MODEL_TAG}"

    # SLURM `--export` semantics on this cluster:
    #   * Comma-separated KEY=VAL list. Values are NOT quotable; the parser
    #     splits on whitespace, dropping anything after the first space (job
    #     17627831 hit this — PLANBENCH_INSTANCES="2 3 4" became "2" + two
    #     stray sbatch positional args silently dropped).
    #   * `--export=ALL` alone does NOT carry user-defined env vars on this
    #     SLURM (confirmed via `srun --overlap` into a live job: vars set in
    #     the calling shell read back empty inside the allocation). Site
    #     policy presumably strips them. Same finding as why
    #     submit_with_rtx.sh encodes its CELLS_LIST as ^-separated tokens.
    # Workaround: encode multi-value lists with '^' separators so no value
    # contains a space; pass them inline in the comma-separated --export.
    # The sbatch script splits ^ back into spaces before use.
    TASKS_ENC="${TASKS// /^}"
    CONFIGS_ENC="${CONFIGS// /^}"
    INSTANCES_ENC="${INSTANCES// /^}"

    EXPORTS="ALL,MODEL=$MODEL,THINK=$THINK,PLANBENCH_TASKS=$TASKS_ENC,PLANBENCH_CONFIGS=$CONFIGS_ENC"
    if [[ -n "$INSTANCES_ENC" ]]; then
        EXPORTS="$EXPORTS,PLANBENCH_INSTANCES=$INSTANCES_ENC"
    fi
    # GPU_MEM_UTIL override (run_planbench_rtx.sbatch reads it, default 0.85).
    # Lower it for 24GB cards (rtx_3090/4090) so the VRAM-85% guard has
    # headroom on the larger smoke models.
    if [[ -n "$GPU_MEM_UTIL_OVERRIDE" ]]; then
        EXPORTS="$EXPORTS,GPU_MEM_UTIL=$GPU_MEM_UTIL_OVERRIDE"
    fi
    # NUM_PREDICT override — both sbatches export it as PDDL_COPILOT_NUM_PREDICT,
    # which engine.py's _effective_num_predict reads (applies to vllm AND
    # vllm-tools). Set to the single-task sweep's solve cap (8192) for t1 so
    # plan-generation answers don't truncate (the 4096 floor truncated job
    # 18019718). Same value for both arms = clean tools-vs-no-tools baseline.
    if [[ -n "$NUM_PREDICT_OVERRIDE" ]]; then
        EXPORTS="$EXPORTS,NUM_PREDICT=$NUM_PREDICT_OVERRIDE"
    fi
    # --base → vllm-base engine (v2 no-tools baseline, own results dir).
    if [[ "$BASE" -eq 1 ]]; then
        EXPORTS="$EXPORTS,ENGINE_BACKEND=vllm-base"
    fi

    # --gpus + --constraint on the CLI override the sbatch's
    # #SBATCH --gpus=rtx_6000:1 / --constraint=rtx_6000 directives (same idiom
    # as submit_with_rtx.sh's GPU_TYPE). The SLURM feature name equals the
    # GPU-type token, so --constraint=$GPU_TYPE is correct for any class
    # (rtx_6000, rtx_pro_6000, rtx_3090, rtx_4090, ...).
    CMD=(sbatch
        --job-name="$JOB_NAME"
        --time="$TIME"
        --gpus="${GPU_TYPE}:1"
        --constraint="$GPU_TYPE"
        --export="$EXPORTS"
        "$SBATCH_FILE")

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo
        echo "  ${CMD[*]}"
    else
        echo
        echo "Submitting $MODEL..."
        "${CMD[@]}"
    fi
done
