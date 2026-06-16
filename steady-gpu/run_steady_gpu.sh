#!/usr/bin/env bash
### run_steady_gpu.sh — single-tool sweep on a rented, non-SLURM GPU box.
###
### Mirrors the cluster's 5-task arm (cluster-experimenting/
### run_condition_vllm_rtx.sbatch) for a steady neocloud GPU (RunPod H200-141GB),
### serving the model in CLEAN BF16 instead of the cluster's AWQ-INT4 quant.
### The experiment design is byte-identical to the cluster sweep: same matrix
### (5 tasks x {no-tools, tools_all_minimal} x {think on, off} x prompt
### variants x domains), same sampling (temp 0 greedy), same max-model-len,
### same parsers. The ONLY deltas are (1) the model WEIGHT id (BF16 upstream of
### the cluster's AWQ quant) and (2) the host/launcher (pip `vllm serve` on a
### bare box vs apptainer under SLURM). Neither changes token-level outputs.
###
### Corpus isolation: results land under RESULTS_ROOT with RUN_TAG=sweep7 so
### the BF16 corpus never collides with the cluster's AWQ sweep5v2 tree. The
### analyzer strips the run-tag suffix and reads the cells as the same model
### (e.g. qwen3_6_35b) — the BF16-vs-AWQ delta is a *finding*, not a bug.
###
### Resumable: run_experiment.py skips trials already in each cell's
### trials.jsonl, so a crash/teardown only loses the trial in flight.
###
### Usage (run from the box, harness venv active, vLLM pip-installed):
###   bash steady-gpu/run_steady_gpu.sh            # full sweep7 (default 35B)
###   SMOKE=1   bash steady-gpu/run_steady_gpu.sh  # 1 domain x 1 problem sanity
###   PARTIAL_K=2 bash steady-gpu/run_steady_gpu.sh  # pilot: first-2 fixtures/domain
###
### Key env (defaults mirror the cluster unless noted):
###   MODELS         canonical tags, space-separated. Default "qwen3.6:35b".
###   THINK_MODES    default "on off"
###   CONDITIONS     default "no-tools tools_all_minimal"
###   RUN_TAG        default "sweep7"  (OUT_DIR suffix → corpus isolation)
###   CONCURRENCY    default 4
###   GPU_MEM_UTIL   default 0.90  (box deviation: H200 headroom; KV-cache only,
###                  generation-neutral at temp 0. Cluster used 0.85 on a 48GB
###                  knife-edge. The cluster's >85% VRAM abort is NOT ported —
###                  it was an rtx_6000-specific OOM guard.)
###   MAX_MODEL_LEN  default 16384  (mirror cluster; the 32K bump was rejected)
###   VLLM_PORT      default 8000
###   SMOKE=1        run `run_experiment.py --smoke` instead of the full matrix
###   PARTIAL_K=N    cap each domain to first-K fixtures (pilot/probe)
###   EXPT_ROOT      default $HOME/pddl-copilot-experiments
###   MARKETPLACE_PATH  default $HOME/pddl-copilot  (MCP plugins for the tools arm)

set -eo pipefail

EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-${MARKETPLACE_PATH:-$HOME/pddl-copilot}}"

# shellcheck source=../cluster-experimenting/lib/defaults.sh
source "$EXPT_ROOT/cluster-experimenting/lib/defaults.sh"

MODELS="${MODELS:-qwen3.6:35b}"
THINK_MODES="${THINK_MODES:-on off}"
CONDITIONS="${CONDITIONS:-no-tools tools_all_minimal}"
RUN_TAG="${RUN_TAG:-sweep7}"
CONCURRENCY="${CONCURRENCY:-4}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-16384}"
VLLM_PORT="${VLLM_PORT:-8000}"
RESULTS_ROOT="${RESULTS_ROOT:-$EXPT_ROOT/results/$RUN_TAG}"

# BF16 weight override — the ONLY experiment-affecting delta from the cluster.
# Parser/reasoning flags are resolved by vllm_lookup (single source of truth in
# lib/defaults.sh), so they stay identical to the AWQ cluster cells; here we
# swap ONLY HF_MODEL to the un-quantized upstream weights.
#   qwen3.6:35b → BF16 upstream of cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit (~70GB).
#   Qwen3.5:9B  → already BF16 on the cluster (identity unchanged; co-located).
# Confirm the exact 35B id with a --smoke before the full run: a wrong served
# name silently yields 0% tool extraction in the tools arm.
bf16_weight_override() {
    case "$1" in
        qwen3.6:35b) HF_MODEL="Qwen/Qwen3.6-35B-A3B" ;;
        Qwen3.5:9B)  HF_MODEL="Qwen/Qwen3.5-9B" ;;
        *) echo "Error: no BF16 weight mapping for '$1' — add it to bf16_weight_override()" >&2
           return 1 ;;
    esac
}

cd "$EXPT_ROOT"
OVERALL_RC=0

for MODEL in $MODELS; do
    MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

    unset MAX_NUM_BATCHED_TOKENS
    vllm_lookup "$MODEL" || exit 1          # AWQ HF_MODEL + parsers
    bf16_weight_override "$MODEL" || exit 1  # override HF_MODEL → BF16 weights
    REASONING_PARSER_FLAG="$(vllm_reasoning_parser_flag)"
    MAX_NUM_BATCHED_TOKENS_FLAG=""
    [ -n "${MAX_NUM_BATCHED_TOKENS:-}" ] && \
        MAX_NUM_BATCHED_TOKENS_FLAG="--max-num-batched-tokens $MAX_NUM_BATCHED_TOKENS"

    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL  (BF16 HF: $HF_MODEL)  RUN_TAG=$RUN_TAG  started $(date)"
    echo "# parsers: --tool-call-parser $TOOL_CALL_PARSER ${REASONING_PARSER_FLAG:-(none)}"
    echo "####################################################################"

    SERVE_LOG="$EXPT_ROOT/steady-gpu/vllm-${MODEL_TAG}-${RUN_TAG}.log"
    echo "Starting vLLM on localhost:$VLLM_PORT serving $HF_MODEL → $SERVE_LOG"
    vllm serve "$HF_MODEL" \
        --host 0.0.0.0 \
        --port "$VLLM_PORT" \
        --max-model-len "$MAX_MODEL_LEN" \
        --enable-auto-tool-choice \
        --tool-call-parser "$TOOL_CALL_PARSER" \
        $REASONING_PARSER_FLAG \
        --gpu-memory-utilization "$GPU_MEM_UTIL" \
        --enable-prefix-caching \
        $MAX_NUM_BATCHED_TOKENS_FLAG \
        > "$SERVE_LOG" 2>&1 &
    VLLM_PID=$!
    # shellcheck disable=SC2064
    trap "echo 'Shutting down vLLM...'; kill $VLLM_PID 2>/dev/null || true; wait 2>/dev/null || true" EXIT

    # Readiness probe. Generous 60-min ceiling: a cold BF16 35B pulls ~70GB
    # from HF on first run. Pre-download via huggingface-cli (see runbook) to
    # make this near-instant on a warm persistent volume.
    ready=0
    for _ in $(seq 1 1800); do
        if curl -sf "http://localhost:$VLLM_PORT/v1/models" >/dev/null 2>&1; then
            ready=1; break
        fi
        if ! kill -0 "$VLLM_PID" 2>/dev/null; then
            echo "vLLM died during startup; tail of $SERVE_LOG:"; tail -50 "$SERVE_LOG"
            OVERALL_RC=2; break
        fi
        sleep 2
    done
    if [ "$ready" -ne 1 ]; then
        echo "vLLM not ready within 60 min; tail of $SERVE_LOG:"; tail -50 "$SERVE_LOG"
        kill "$VLLM_PID" 2>/dev/null || true; OVERALL_RC=3; continue
    fi
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | head -1
    echo "vLLM ready. base_url=http://localhost:$VLLM_PORT"

    LLM_BASE_URL="http://localhost:$VLLM_PORT"

    ### Probe fast-path: --smoke (1 domain x 1 problem, think×cond internal). ###
    if [ "${SMOKE:-0}" = "1" ]; then
        echo "=== SMOKE: $MODEL ($HF_MODEL) ==="
        python3 run_experiment.py \
            --marketplace-path "$MARKETPLACE_PATH" \
            --models "$HF_MODEL" \
            --llm-base-url "$LLM_BASE_URL" \
            --concurrency "$CONCURRENCY" \
            --smoke || OVERALL_RC=$?
        kill "$VLLM_PID" 2>/dev/null || true; wait "$VLLM_PID" 2>/dev/null || true
        continue
    fi

    ### Full sweep7 matrix — mirrors the cluster sbatch's think × cond loop. ###
    PARTIAL_ARG=()
    [ -n "${PARTIAL_K:-}" ] && PARTIAL_ARG=(--partial "$PARTIAL_K")

    for THINK_MODE in $THINK_MODES; do
        THINK_ARG=()
        [ "$THINK_MODE" != "default" ] && THINK_ARG=(--think "$THINK_MODE")

        for COND in $CONDITIONS; do
            case "$COND" in
                no-tools)          COND_ARGS=(--conditions no-tools) ;;
                tools_all_minimal) COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
                *) echo "Error: unknown condition '$COND'"; OVERALL_RC=1; continue ;;
            esac

            OUT_DIR="$RESULTS_ROOT/slurm_vllm_${MODEL_TAG}_${THINK_MODE}_${COND}_${RUN_TAG}"
            echo
            echo "=== $MODEL  THINK=$THINK_MODE  COND=$COND → $OUT_DIR  $(date) ==="
            python3 run_experiment.py \
                --marketplace-path "$MARKETPLACE_PATH" \
                --models "$HF_MODEL" \
                --llm-base-url "$LLM_BASE_URL" \
                --concurrency "$CONCURRENCY" \
                "${THINK_ARG[@]}" \
                "${COND_ARGS[@]}" \
                "${PARTIAL_ARG[@]}" \
                --output-dir "$OUT_DIR"
            RC=$?
            echo "=== $MODEL  THINK=$THINK_MODE  COND=$COND  rc=$RC  $(date) ==="
            [ "$RC" -ne 0 ] && OVERALL_RC=$RC
        done
    done

    kill "$VLLM_PID" 2>/dev/null || true; wait "$VLLM_PID" 2>/dev/null || true
    trap - EXIT
    echo "# MODEL: $MODEL finished $(date)"
done

echo
echo "End time: $(date)   overall rc=$OVERALL_RC"
echo "Results under: $RESULTS_ROOT"
exit $OVERALL_RC
