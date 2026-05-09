#!/bin/bash
### Smoke probe: vLLM vs Ollama on Qwen3.5:0.8B + qwen3.6:27b.
###
### Runs the existing `run_experiment.py --smoke` flow twice on the same
### rtx_pro_6000:1 GPU (Phase A: ollama, Phase B: vllm) so wall-time + tool
### pass-rate are comparable across the 2 (think) × 2 (cond) × 5 (task) ×
### 2 (model) = 80-cell smoke matrix. Decision rule: vLLM wall-time
### ≤ 0.7× Ollama on the 27B tools×off cell (full-sweep projection)
### → migrate. Below that, stay on Ollama.
###
### Outputs:
###   results/smoke/probe_ollama_<sha>_<ts>/<model_tag>/
###   results/smoke/probe_vllm_<sha>_<ts>/<model_tag>/
### Both directories are analyzer-readable summary_*.json.
###
### Submit:
###   sbatch cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch
###
#SBATCH --partition=main
#SBATCH --job-name=vllm_vs_ollama_smoke
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_pro_6000:1
#SBATCH --mem=80G
#SBATCH --tmp=80G
#SBATCH --time=02:30:00

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

# Models: Ollama tag (Phase A) + matching HuggingFace repo (Phase B).
# qwen3.6:27b on Ollama is Q4_K_M; the closest apples-to-apples on vLLM is
# AWQ-INT4 from the most-downloaded community quant. BF16 (54 GB) won't
# fit, FP8 (28 GB) is a different precision class than Q4_K_M.
OLLAMA_SMALL="Qwen3.5:0.8B"
OLLAMA_LARGE="qwen3.6:27b"
HF_SMALL="Qwen/Qwen3.5-0.8B"
HF_LARGE="cyankiwi/Qwen3.6-27B-AWQ-INT4"
HF_LARGE_QUANT="awq"

GIT_SHA="$(git -C "$EXPT_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_OLLAMA="$EXPT_ROOT/results/smoke/probe_ollama_${GIT_SHA}_${TS}"
OUT_VLLM="$EXPT_ROOT/results/smoke/probe_vllm_${GIT_SHA}_${TS}"
mkdir -p "$OUT_OLLAMA" "$OUT_VLLM"

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
mkdir -p "$WORK/ollama-models" "$WORK/hf-cache"
trap 'echo "Cleanup..."; jobs -p | xargs -r kill 2>/dev/null || true; cd ~; rm -rf "$WORK"' EXIT

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
# Phase A: Ollama smoke
############################################
SIF_OLLAMA="$WORK/ollama.sif"
if [ -f "$HOME/ollama.sif" ]; then
    cp "$HOME/ollama.sif" "$SIF_OLLAMA"
else
    apptainer build --force "$SIF_OLLAMA" docker://ollama/ollama 2>&1 | tail -3
    cp "$SIF_OLLAMA" "$HOME/ollama.sif"
fi

OLLAMA_PORT="$(free_port $(( 11400 + (${SLURM_JOBID:-0} % 100) )))"
echo
echo "=== Phase A: Ollama on :$OLLAMA_PORT ==="
apptainer exec --nv \
    --bind "$WORK/ollama-models:/root/.ollama" \
    --writable-tmpfs \
    "$SIF_OLLAMA" bash -c "
        export OLLAMA_HOST=0.0.0.0:$OLLAMA_PORT
        export OLLAMA_NUM_PARALLEL=$CONCURRENCY
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE=1h
        export OLLAMA_CONTEXT_LENGTH=16384
        ollama serve
    " > "$WORK/ollama-serve.log" 2>&1 &
OLLAMA_PID=$!

for i in $(seq 1 90); do
    curl -sf "http://localhost:$OLLAMA_PORT/" >/dev/null 2>&1 && { echo "ollama up (${i}s)"; break; }
    sleep 1
done

for M in "$OLLAMA_SMALL" "$OLLAMA_LARGE"; do
    M_TAG="$(echo "$M" | tr '/:.' '___')"
    echo
    echo "--- Ollama: pull + warmup $M ---"
    apptainer exec --nv --bind "$WORK/ollama-models:/root/.ollama" --writable-tmpfs "$SIF_OLLAMA" \
        bash -c "OLLAMA_HOST=http://localhost:$OLLAMA_PORT ollama pull '$M'" 2>&1 | tail -2
    curl -s --max-time 300 "http://localhost:$OLLAMA_PORT/api/chat" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"1h\",\"options\":{\"num_predict\":5,\"num_ctx\":16384}}" \
        >/dev/null

    echo "--- Ollama smoke: $M ---"
    t0=$EPOCHREALTIME
    python3 run_experiment.py \
        --marketplace-path "$MARKETPLACE_PATH" \
        --models "$M" \
        --ollama-host "http://localhost:$OLLAMA_PORT" \
        --concurrency "$CONCURRENCY" \
        --inference-backend ollama \
        --smoke \
        --output-dir "$OUT_OLLAMA/$M_TAG"
    t1=$EPOCHREALTIME
    awk -v m="$M" "BEGIN{printf \"OLLAMA SMOKE WALL %s: %.1fs\n\", m, $t1-$t0}"
done

echo "--- Stopping Ollama ---"
kill "$OLLAMA_PID" 2>/dev/null || true
wait "$OLLAMA_PID" 2>/dev/null || true
sleep 5

############################################
# Phase B: vLLM smoke
############################################
SIF_VLLM="$WORK/vllm.sif"
if [ -f "$HOME/vllm.sif" ]; then
    cp "$HOME/vllm.sif" "$SIF_VLLM"
else
    echo "Building vllm.sif from docker://vllm/vllm-openai:latest (first run, ~5 min)"
    apptainer build --force "$SIF_VLLM" docker://vllm/vllm-openai:latest 2>&1 | tail -3
    cp "$SIF_VLLM" "$HOME/vllm.sif"
fi

run_vllm_cell() {
    local hf_id="$1"
    local ollama_tag="$2"
    local quant_arg="$3"
    local m_tag
    m_tag="$(echo "$ollama_tag" | tr '/:.' '___')"
    local port
    port="$(free_port $(( 11500 + (${SLURM_JOBID:-0} % 100) )))"

    local serve_log="$WORK/vllm-${m_tag}.log"
    echo
    echo "=== vLLM serve: $hf_id on :$port (alias of $ollama_tag) ==="
    # shellcheck disable=SC2086 — quant_arg is a single token or empty
    apptainer exec --nv \
        --bind "$WORK/hf-cache:/root/.cache/huggingface" \
        --writable-tmpfs \
        "$SIF_VLLM" \
        python3 -m vllm.entrypoints.openai.api_server \
            --model "$hf_id" \
            --host 0.0.0.0 \
            --port "$port" \
            --max-model-len 16384 \
            --enable-auto-tool-choice \
            --tool-call-parser hermes \
            --reasoning-parser qwen3 \
            --gpu-memory-utilization 0.85 \
            $quant_arg \
            > "$serve_log" 2>&1 &
    local pid=$!

    # vLLM model load can take several minutes for the 27B AWQ on first run
    # (HF download). Wait up to 20 min before giving up.
    local ready=0
    for i in $(seq 1 600); do
        if curl -sf "http://localhost:$port/v1/models" >/dev/null 2>&1; then
            echo "vllm ready ($((i*2))s)"; ready=1; break
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "vLLM died during startup; tail of $serve_log:"
            tail -50 "$serve_log"
            return 2
        fi
        sleep 2
    done
    if [ "$ready" -ne 1 ]; then
        echo "vLLM did not become ready within 20 min; tail of $serve_log:"
        tail -50 "$serve_log"
        kill "$pid" 2>/dev/null || true
        return 3
    fi

    # GPU sanity: same 85% guard the production sbatch uses.
    local vu vt vp
    vu=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
    vt=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
    vp=$(( vu * 100 / vt ))
    echo "VRAM after vLLM load ($hf_id): ${vu}/${vt} MiB (${vp}%)"

    echo "--- vLLM smoke: $hf_id ---"
    local t0=$EPOCHREALTIME
    python3 run_experiment.py \
        --marketplace-path "$MARKETPLACE_PATH" \
        --models "$hf_id" \
        --ollama-host "http://localhost:$port" \
        --concurrency "$CONCURRENCY" \
        --inference-backend vllm \
        --smoke \
        --output-dir "$OUT_VLLM/$m_tag"
    local t1=$EPOCHREALTIME
    awk -v m="$hf_id" "BEGIN{printf \"VLLM SMOKE WALL %s: %.1fs\n\", m, $t1-$t0}"

    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    sleep 5
    return 0
}

run_vllm_cell "$HF_SMALL" "$OLLAMA_SMALL" "" || echo "WARN: vLLM small failed (rc=$?)"
run_vllm_cell "$HF_LARGE" "$OLLAMA_LARGE" "--quantization $HF_LARGE_QUANT" || echo "WARN: vLLM large failed (rc=$?)"

echo
echo "End: $(date)"
echo "Results:"
echo "  Ollama: $OUT_OLLAMA"
echo "  vLLM:   $OUT_VLLM"
echo
echo "Next: compare wall-time + per-cell pass rate via the analyzer skill."
echo "Decision gate: vLLM wall ≤ 0.7× Ollama on qwen3.6:27b tools×off cell."
