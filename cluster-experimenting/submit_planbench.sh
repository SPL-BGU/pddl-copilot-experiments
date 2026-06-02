#!/usr/bin/env bash
# submit_planbench.sh — dispatch the PlanBench arm sbatch one-per-model.
#
# Each model gets its own sbatch on rtx_pro_6000:1 that walks
# (task × config) in-process for cache locality. Mirrors the shape of
# submit_with_rtx.sh but with PlanBench's (task, config) axes instead of
# (think, condition).
#
# Models are canonical tags resolved to HF ids by vllm_lookup
# (lib/defaults.sh) — must be in PDDL_VLLM_VERIFIED_MODELS. The vLLM server
# is self-deployed per-job by run_planbench_rtx.sbatch (Ollama retired
# 2026-05-18; see CHANGELOG 2026-06-02).
#
# Usage:
#   bash submit_planbench.sh --models Qwen3.5:0.8B Qwen3.5:4B
#   bash submit_planbench.sh --models Qwen3.5:0.8B --tasks t1 t3 --configs blocksworld
#   bash submit_planbench.sh --smoke              # 1 model × 1 task × 1 config × 3 instances
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
SMOKE=0
DRY_RUN=0

usage() {
    sed -n '2,12p' "$0" >&2
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
        --smoke) SMOKE=1; shift ;;
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

echo "PlanBench dispatch:"
echo "  models   = ${MODELS[*]}"
echo "  tasks    = $TASKS"
echo "  configs  = $CONFIGS"
echo "  instances= ${INSTANCES:-<full>}"
echo "  think    = $THINK"
echo "  smoke    = $SMOKE"
[[ "$DRY_RUN" -eq 1 ]] && echo "  (dry-run — not submitting)"

for MODEL in "${MODELS[@]}"; do
    MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
    JOB_NAME="pddl_planbench_${MODEL_TAG}"

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

    CMD=(sbatch
        --job-name="$JOB_NAME"
        --export="$EXPORTS"
        "$SCRIPT_DIR/run_planbench_rtx.sbatch")

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo
        echo "  ${CMD[*]}"
    else
        echo
        echo "Submitting $MODEL..."
        "${CMD[@]}"
    fi
done
