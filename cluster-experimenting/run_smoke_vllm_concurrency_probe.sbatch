#!/bin/bash
### Concurrency-saturation probe: vLLM 27B AWQ at c ∈ {4, 8, 16}.
###
### Follow-up to `run_smoke_vllm_vs_ollama.sbatch`. Same vLLM server stays
### up across all three concurrency levels — model load + CUDA graph
### compile is paid once, not three times.
###
### Walltime projection (rtx_pro_6000:1, vllm.sif cached, HF re-download):
###   vllm.sif copy        ~10 s
###   HF download (17 GB)  ~3 min
###   vLLM serve up        ~2 min (AWQ-INT4 weights load)
###   smoke c=4            ~25 min
###   smoke c=8            ~20 min  (continuous batching helps as c grows)
###   smoke c=16           ~15 min
### Total ~ 65–80 min. `--time=02:00:00` covers it with margin.
###
### Submit with afterok dependency on the parent smoke:
###   sbatch --dependency=afterok:<PARENT_JOBID> \
###          cluster-experimenting/run_smoke_vllm_concurrency_probe.sbatch
###
### Decision use: maps the throughput-vs-concurrency curve so we know
### where vLLM saturates. The migration ROI is "vLLM at c=N vs Ollama at
### c=4" — N comes from this probe.
###
#SBATCH --partition=main
#SBATCH --job-name=vllm_concurrency_probe
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_pro_6000:1
#SBATCH --mem=80G
#SBATCH --tmp=80G
#SBATCH --time=02:00:00

set -eo pipefail

source "$HOME/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh" 2>/dev/null || true

echo "SLURM_JOBID=${SLURM_JOBID:-local}"
echo "Node: $(hostname)"
echo "Start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

ENV_NAME="${ENV_NAME:-pddl_copilot}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"

# 27B only — the 0.8B is fast enough that concurrency improvements on it
# wouldn't change the production-sweep migration calculus.
# Quantization is auto-detected from config.json (cyankiwi declares
# quant_method="compressed-tensors", NOT pure "awq"). Passing
# --quantization awq would have been wrong; let vLLM auto-detect.
HF_LARGE="cyankiwi/Qwen3.6-27B-AWQ-INT4"
OLLAMA_LARGE_TAG="qwen3.6_27b"

# Override the c-grid via env if you want a finer/coarser sweep.
CONCURRENCIES="${CONCURRENCIES:-4 8 16}"

GIT_SHA="$(git -C "$EXPT_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
TS="$(date +%Y%m%d_%H%M%S)"

# Compute-node scratch — same SSD-Drive pattern as the parent smoke.
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE" 2>/dev/null; then
        WORK="$SCRATCH_BASE/probe-work"
    else
        WORK="/tmp/vllm-conc-${SLURM_JOB_ID:-$$}"
    fi
else
    WORK="/tmp/vllm-conc-${SLURM_JOB_ID:-$$}"
fi
mkdir -p "$WORK/hf-cache"

# Preserve vLLM serve logs to the persistent log dir on EXIT — the actual
# root cause of an EngineCore failure lives in $WORK/vllm-*.log, and the
# trap below would otherwise rm -rf it before we could read it.
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

# Reuse the cached vllm.sif from the parent smoke. If absent (rare —
# parent should have populated it), fall back to a fresh build.
SIF_VLLM="$WORK/vllm.sif"
if [ -f "$HOME/vllm.sif" ]; then
    cp "$HOME/vllm.sif" "$SIF_VLLM"
else
    echo "WARN: \$HOME/vllm.sif not cached (parent smoke didn't run successfully?), building from scratch"
    apptainer build --force "$SIF_VLLM" docker://vllm/vllm-openai:latest 2>&1 | tail -3
    cp "$SIF_VLLM" "$HOME/vllm.sif"
fi

free_port() {
    local p="$1"
    while ss -Hltn "sport = :$p" 2>/dev/null | grep -q LISTEN; do
        p=$(( p + 1 ))
        [ "$p" -ge 11999 ] && { echo "no free port"; exit 4; }
    done
    echo "$p"
}

VLLM_PORT="$(free_port $(( 11700 + (${SLURM_JOBID:-0} % 100) )))"

echo
echo "=== vLLM serve: $HF_LARGE on :$VLLM_PORT ==="
SERVE_LOG="$WORK/vllm-serve.log"
apptainer exec --nv \
    --bind "$WORK/hf-cache:/root/.cache/huggingface" \
    --writable-tmpfs \
    "$SIF_VLLM" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$HF_LARGE" \
        --host 0.0.0.0 \
        --port "$VLLM_PORT" \
        --max-model-len 16384 \
        --enable-auto-tool-choice \
        --tool-call-parser hermes \
        --reasoning-parser qwen3 \
        --gpu-memory-utilization 0.85 \
        > "$SERVE_LOG" 2>&1 &
VLLM_PID=$!

ready=0
for i in $(seq 1 600); do
    if curl -sf "http://localhost:$VLLM_PORT/v1/models" >/dev/null 2>&1; then
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

# Post-load VRAM snapshot — should be under 85% pre-allocated.
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

# Sweep concurrencies on the SAME running vLLM server. The harness fires
# `--concurrency C` async tasks; vLLM's continuous-batching scheduler
# (default --max-num-seqs=256) accommodates all three levels without a
# server restart, so we pay model-load + CUDA-graph compile exactly once.
for C in $CONCURRENCIES; do
    OUT="$EXPT_ROOT/results/smoke/probe_vllm_c${C}_${GIT_SHA}_${TS}/${OLLAMA_LARGE_TAG}"
    mkdir -p "$OUT"
    # Surface concurrency to run_experiment.py — vLLM doesn't read this, but
    # the harness logs a misleading "OLLAMA_NUM_PARALLEL is not set" banner
    # otherwise. Set per-cell so the printout matches the active C.
    export OLLAMA_NUM_PARALLEL="$C"
    echo
    echo "=== smoke c=${C} → $OUT ==="
    t0=$EPOCHREALTIME
    python3 run_experiment.py \
        --marketplace-path "$MARKETPLACE_PATH" \
        --models "$HF_LARGE" \
        --ollama-host "http://localhost:$VLLM_PORT" \
        --concurrency "$C" \
        --inference-backend vllm \
        --smoke \
        --output-dir "$OUT" \
        || echo "WARN: smoke c=$C exited non-zero (rc=$?)"
    t1=$EPOCHREALTIME
    awk -v c="$C" "BEGIN{printf \"VLLM CONC PROBE c=%s WALL: %.1fs\n\", c, $t1-$t0}"
done

echo
echo "--- Stopping vLLM ---"
kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true

echo
echo "End: $(date)"
echo "Results:"
for C in $CONCURRENCIES; do
    echo "  c=$C: $EXPT_ROOT/results/smoke/probe_vllm_c${C}_${GIT_SHA}_${TS}/${OLLAMA_LARGE_TAG}"
done
echo
echo "Next: compare per-(task,cond) median trial wall across c-levels;"
echo "      saturation = where the c→c+1 wall ratio falls below ~0.85x."
