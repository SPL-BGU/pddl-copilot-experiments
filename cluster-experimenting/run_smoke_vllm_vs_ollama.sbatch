#!/bin/bash
### vLLM smoke probe — qwen3.6:27b only.
###
### Runs `run_experiment.py --smoke --inference-backend vllm` on
### `cyankiwi/Qwen3.6-27B-AWQ-INT4` at c=4. The Ollama baseline for the
### comparison comes from the EXISTING 27B production sweep
### (results/slurm_qwen3_6_27b_*); we don't re-run Ollama in this job.
###
### Decision rule: vLLM smoke wall ≤ 0.7× the matching Ollama production
### cell (qwen3.6:27b tools×off) AND per-cell pass rates within parity
### → migrate. Below either bar, stay on Ollama.
###
### Output:
###   results/smoke/probe_vllm_<sha>_<ts>/qwen3_6_27b/
### Analyzer-readable summary_*.json.
###
### Submit:
###   sbatch cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch
###
### Notes:
###   * The cyankiwi 27B quant declares quant_method="compressed-tensors"
###     in config.json (NOT pure "awq"). We let vLLM auto-detect from
###     config.json — passing --quantization awq would have been wrong.
###   * 0.8B was dropped from the probe: it's fast enough on Ollama that
###     vLLM's continuous batching wins are negligible, and the 27B cell
###     is the load-bearing decision point per the migration ROI.
###
#SBATCH --partition=main
#SBATCH --job-name=vllm_27b_smoke
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_pro_6000:1
#SBATCH --mem=80G
#SBATCH --tmp=80G
#SBATCH --time=01:00:00

set -eo pipefail

source "$HOME/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh" 2>/dev/null || true

echo "SLURM_JOBID=${SLURM_JOBID:-local}"
echo "Node: $(hostname)"
echo "Start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

ENV_NAME="${ENV_NAME:-pddl_copilot}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"
CONCURRENCY="${CONCURRENCY:-4}"
# Surface concurrency to run_experiment.py — the harness logs a misleading
# "OLLAMA_NUM_PARALLEL is not set" warning otherwise. vLLM doesn't read it.
export OLLAMA_NUM_PARALLEL="$CONCURRENCY"

# Default: 27B AWQ-INT4 (closest apples-to-apples to Ollama's Q4_K_M,
# ~17 GB on disk for both). BF16 (54 GB) won't fit, FP8 (28 GB) is a
# different precision class than Q4_K_M.
#
# Override at submit time via env-var to probe a different model on the
# same script — e.g. for a 0.8B sanity run on rtx_6000:
#   sbatch --export=ALL,HF_MODEL="Qwen/Qwen3.5-0.8B",OLLAMA_TAG="Qwen3.5:0.8B" \
#          --gpus=rtx_6000:1 --mem=48G --job-name=vllm_0_8b_smoke \
#          cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch
OLLAMA_TAG="${OLLAMA_TAG:-qwen3.6:27b}"
HF_LARGE="${HF_MODEL:-cyankiwi/Qwen3.6-27B-AWQ-INT4}"
# vLLM serve sizing — overridable for tighter VRAM (e.g. running 27B AWQ on a
# 24 GB rtx_3090 instead of the 96 GB rtx_pro_6000 default). The defaults
# below preserve the rtx_pro_6000 tuning so existing submissions don't shift.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-16384}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.85}"
# Skip CUDA graph capture+profiling on memory-tight hosts. Profiling itself
# needs ~1.5 GiB headroom which 27B AWQ on a 24 GB rtx_3090 can't spare.
# Cost: slower per-token inference (no cudagraph reuse). Toggle with
# ENFORCE_EAGER=1 in the submit's --export list.
ENFORCE_EAGER="${ENFORCE_EAGER:-0}"
EAGER_FLAG=""
[ "$ENFORCE_EAGER" = "1" ] && EAGER_FLAG="--enforce-eager"
# Override harness per-task num_predict caps (solve=8192, validate_*=6144) to
# fit under a tight MAX_MODEL_LEN. vLLM rejects max_tokens > max_model_len with
# HTTP 400, so without this override every tools-cell trial 400-errors before
# the model generates a token. Empty (default) keeps the harness defaults.
NUM_PREDICT="${NUM_PREDICT:-}"
NUM_PREDICT_FLAG=""
[ -n "$NUM_PREDICT" ] && NUM_PREDICT_FLAG="--num-predict $NUM_PREDICT"
# vLLM tool-call parser must match the model's emit format (verified empirically
# in 2026-05-10 smokes; see development/CHANGELOG.md). Defaults to qwen3_xml
# (Qwen3.5/3.6 family Llama-XML <function=NAME><parameter=KEY>VAL</parameter>
# </function>); override to `gemma4` for Gemma-4, `hermes` for vanilla Qwen3
# (Hermes JSON-in-XML), or any other registered parser.
TOOL_CALL_PARSER="${TOOL_CALL_PARSER:-qwen3_xml}"

GIT_SHA="$(git -C "$EXPT_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_VLLM="$EXPT_ROOT/results/smoke/probe_vllm_${GIT_SHA}_${TS}"
mkdir -p "$OUT_VLLM"

# Compute-node scratch (cluster guide §"SSD Drive"). HF cache lives here so
# the 27B AWQ snapshot (~17 GB) stays node-local instead of hitting NFS.
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE" 2>/dev/null; then
        WORK="$SCRATCH_BASE/probe-work"
    else
        WORK="/tmp/vllm-probe-${SLURM_JOB_ID:-$$}"
    fi
else
    WORK="/tmp/vllm-probe-${SLURM_JOB_ID:-$$}"
fi
mkdir -p "$WORK/hf-cache"

# Preserve vLLM serve logs to the persistent log dir on EXIT — the actual
# root cause of an EngineCore failure lives in the per-cell vllm-*.log
# inside $WORK, and the trap below would otherwise rm -rf it before we
# could read it. Filename prefixed with $SLURM_JOBID so concurrent or
# resubmitted runs don't collide.
preserve_serve_logs() {
    local logs_dir="$EXPT_ROOT/cluster-experimenting/logs"
    [ -d "$WORK" ] || return 0
    for f in "$WORK"/vllm-*.log; do
        [ -f "$f" ] || continue
        cp -a "$f" "$logs_dir/${SLURM_JOBID:-local}-$(basename "$f")" 2>/dev/null || true
    done
}
trap 'echo "Cleanup..."; jobs -p | xargs -r kill 2>/dev/null || true; preserve_serve_logs; cd ~; rm -rf "$WORK"' EXIT

module load anaconda
source activate "$ENV_NAME"

cd "$EXPT_ROOT"

free_port() {
    local p="$1"
    while ss -Hltn "sport = :$p" 2>/dev/null | grep -q LISTEN; do
        p=$(( p + 1 ))
        [ "$p" -ge 11999 ] && { echo "no free port"; exit 4; }
    done
    echo "$p"
}

############################################
# vLLM 27B smoke
############################################
SIF_VLLM="$WORK/vllm.sif"
if [ -f "$HOME/vllm.sif" ]; then
    cp "$HOME/vllm.sif" "$SIF_VLLM"
else
    echo "Building vllm.sif from docker://vllm/vllm-openai:latest (first run, ~5 min)"
    apptainer build --force "$SIF_VLLM" docker://vllm/vllm-openai:latest 2>&1 | tail -3
    cp "$SIF_VLLM" "$HOME/vllm.sif"
fi

M_TAG="$(echo "$OLLAMA_TAG" | tr '/:.' '___')"
PORT="$(free_port $(( 11500 + (${SLURM_JOBID:-0} % 100) )))"
SERVE_LOG="$WORK/vllm-${M_TAG}.log"

echo
echo "=== vLLM serve: $HF_LARGE on :$PORT (alias of $OLLAMA_TAG) ==="
apptainer exec --nv \
    --bind "$WORK/hf-cache:/root/.cache/huggingface" \
    --writable-tmpfs \
    "$SIF_VLLM" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$HF_LARGE" \
        --host 0.0.0.0 \
        --port "$PORT" \
        --max-model-len "$MAX_MODEL_LEN" \
        --enable-auto-tool-choice \
        --tool-call-parser "$TOOL_CALL_PARSER" \
        --reasoning-parser qwen3 \
        --gpu-memory-utilization "$GPU_MEM_UTIL" \
        $EAGER_FLAG \
        > "$SERVE_LOG" 2>&1 &
VLLM_PID=$!

# vLLM model load can take several minutes for the 27B AWQ on first run
# (HF download). Wait up to 20 min before giving up.
ready=0
for i in $(seq 1 600); do
    if curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
        echo "vllm ready ($((i*2))s)"; ready=1; break
    fi
    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "vLLM died during startup; tail of $SERVE_LOG:"
        tail -50 "$SERVE_LOG"
        exit 2
    fi
    sleep 2
done
if [ "$ready" -ne 1 ]; then
    echo "vLLM did not become ready within 20 min; tail of $SERVE_LOG:"
    tail -50 "$SERVE_LOG"
    kill "$VLLM_PID" 2>/dev/null || true
    exit 3
fi

# GPU sanity: same 85% guard the production sbatch uses.
VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
VRAM_PCT=$(( VRAM_USED * 100 / VRAM_TOTAL ))
echo "VRAM after vLLM load ($HF_LARGE): ${VRAM_USED}/${VRAM_TOTAL} MiB (${VRAM_PCT}%)"

echo "--- vLLM smoke: $HF_LARGE ---"
t0=$EPOCHREALTIME
python3 run_experiment.py \
    --marketplace-path "$MARKETPLACE_PATH" \
    --models "$HF_LARGE" \
    --ollama-host "http://localhost:$PORT" \
    --concurrency "$CONCURRENCY" \
    --inference-backend vllm \
    --smoke \
    $NUM_PREDICT_FLAG \
    --output-dir "$OUT_VLLM/$M_TAG"
t1=$EPOCHREALTIME
awk -v m="$HF_LARGE" "BEGIN{printf \"VLLM SMOKE WALL %s: %.1fs\n\", m, $t1-$t0}"

kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true

echo
echo "End: $(date)"
echo "Results:"
echo "  vLLM 27B: $OUT_VLLM"
echo
echo "Compare against the existing Ollama 27B production cell:"
echo "  results/slurm_qwen3_6_27b_off_tools_all_minimal/summary_*.json"
echo "  results/slurm_qwen3_6_27b_off_tools_per-task_minimal/summary_*.json"
echo "Decision gate: vLLM wall ≤ 0.7× Ollama on qwen3.6:27b tools×off cell + parity on pass rates."
