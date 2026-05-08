#!/bin/bash
### Throughput probe: Ollama vs vLLM on the same node, same prompts, same model.
###
### Single SLURM job that:
###   1. Builds (or reuses cached) ollama.sif and vllm.sif
###   2. Starts Ollama on port 11400, runs bench_throughput.py, stops Ollama
###   3. Starts vLLM on port 11700, runs bench_throughput.py, stops vLLM
###   4. Prints a side-by-side summary
###
### Output: cluster-experimenting/results-bench/bench_<JOBID>.jsonl
### One line per (backend × concurrency) cell. Diff matched cells to compare.
###
### Submit with two model identifiers (Ollama tag + HF id for the same weights):
###   sbatch --export=ALL,OLLAMA_MODEL="Qwen3.5:0.8B",VLLM_MODEL="Qwen/Qwen3.5-0.8B-Instruct" \
###          cluster-experimenting/bench_throughput.sbatch
###
### Required env:
###   OLLAMA_MODEL — Ollama registry tag (e.g. "Qwen3.5:0.8B")
###   VLLM_MODEL   — HuggingFace model id (e.g. "Qwen/Qwen3.5-0.8B-Instruct")
###
### Optional env:
###   N_PROMPTS=30        Number of measurement prompts per concurrency cell
###   CONCURRENCY=1,2,4   Concurrency sweep
###   MAX_TOKENS=512      Cap per request (kept short so prefill matters)
###   ENV_NAME=pddl_copilot
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_bench_throughput
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_pro_6000:1
#SBATCH --mem=80G
#SBATCH --tmp=80G
#SBATCH --time=04:00:00

set -eo pipefail

: "${OLLAMA_MODEL:?Error: export OLLAMA_MODEL=<ollama tag>}"
: "${VLLM_MODEL:?Error: export VLLM_MODEL=<HF id>}"

ENV_NAME="${ENV_NAME:-pddl_copilot}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
N_PROMPTS="${N_PROMPTS:-30}"
CONCURRENCY="${CONCURRENCY:-1,2,4}"
MAX_TOKENS="${MAX_TOKENS:-512}"

echo "SLURM_JOBID=$SLURM_JOBID  Node: $(hostname)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

### Scratch + caches ###
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    mkdir -p "$SCRATCH_BASE" || SCRATCH_BASE="/tmp/bench-${SLURM_JOB_ID}"
else
    SCRATCH_BASE="/tmp/bench-$$"
fi
WORK="$SCRATCH_BASE/work"
mkdir -p "$WORK/ollama" "$WORK/hf"
cd "$WORK"

OUT_DIR="$EXPT_ROOT/cluster-experimenting/results-bench"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/bench_${SLURM_JOB_ID:-$$}.jsonl"
echo "Output: $OUT_FILE"

trap 'echo Cleanup; pkill -P $$ 2>/dev/null || true; wait 2>/dev/null || true; rm -rf "$WORK"' EXIT

### Build / reuse SIFs ###
OLLAMA_SIF="$WORK/ollama.sif"
VLLM_SIF="$WORK/vllm.sif"

if [ -f "$HOME/ollama.sif" ]; then
    cp "$HOME/ollama.sif" "$OLLAMA_SIF"
else
    apptainer build --force "$OLLAMA_SIF" docker://ollama/ollama 2>&1 | tail -3
    cp "$OLLAMA_SIF" "$HOME/ollama.sif"
fi

if [ -f "$HOME/vllm.sif" ]; then
    cp "$HOME/vllm.sif" "$VLLM_SIF"
else
    echo "Building vllm.sif from docker://vllm/vllm-openai:latest (~5-10 min)"
    apptainer build --force "$VLLM_SIF" docker://vllm/vllm-openai:latest 2>&1 | tail -3
    cp "$VLLM_SIF" "$HOME/vllm.sif"
fi

### Activate conda env (provides openai + project deps) ###
module load anaconda
source activate "$ENV_NAME"
cd "$EXPT_ROOT"

### Phase 1: Ollama ###
OLLAMA_PORT=11400
while ss -Hltn "sport = :$OLLAMA_PORT" 2>/dev/null | grep -q LISTEN; do
    OLLAMA_PORT=$(( OLLAMA_PORT + 1 ))
done
echo "=== Phase 1: Ollama on port $OLLAMA_PORT ==="
apptainer exec --nv \
    --bind "$WORK/ollama:/root/.ollama" \
    --writable-tmpfs "$OLLAMA_SIF" bash -c "
        export OLLAMA_HOST=0.0.0.0:$OLLAMA_PORT
        export OLLAMA_NUM_PARALLEL=4
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE=1h
        export OLLAMA_CONTEXT_LENGTH=16384
        ollama serve
    " > "$WORK/ollama.log" 2>&1 &
OLLAMA_PID=$!

for i in $(seq 1 90); do
    curl -sf "http://localhost:$OLLAMA_PORT/" >/dev/null 2>&1 && break
    sleep 1
done

echo "Pulling $OLLAMA_MODEL..."
apptainer exec --nv --bind "$WORK/ollama:/root/.ollama" --writable-tmpfs "$OLLAMA_SIF" \
    bash -c "OLLAMA_HOST=http://localhost:$OLLAMA_PORT ollama pull '$OLLAMA_MODEL'" 2>&1 | tail -2

python3 cluster-experimenting/bench_throughput.py \
    --backend ollama \
    --base-url "http://localhost:$OLLAMA_PORT" \
    --model "$OLLAMA_MODEL" \
    --concurrency "$CONCURRENCY" \
    --n-prompts "$N_PROMPTS" \
    --max-tokens "$MAX_TOKENS" \
    --out "$OUT_FILE"

kill $OLLAMA_PID 2>/dev/null || true
wait $OLLAMA_PID 2>/dev/null || true
sleep 5

### Phase 2: vLLM ###
VLLM_PORT=11700
while ss -Hltn "sport = :$VLLM_PORT" 2>/dev/null | grep -q LISTEN; do
    VLLM_PORT=$(( VLLM_PORT + 1 ))
done
echo "=== Phase 2: vLLM on port $VLLM_PORT ==="
apptainer exec --nv \
    --bind "$WORK/hf:/root/.cache/huggingface" \
    --writable-tmpfs "$VLLM_SIF" bash -c "
        vllm serve '$VLLM_MODEL' \
            --host 0.0.0.0 --port $VLLM_PORT \
            --gpu-memory-utilization 0.90 \
            --max-model-len 16384 \
            --max-num-seqs 8 \
            --disable-log-requests
    " > "$WORK/vllm.log" 2>&1 &
VLLM_PID=$!

# vLLM cold start: weights download + load + CUDA graphs. 30B can hit 10+ min.
for i in $(seq 1 1200); do
    curl -sf "http://localhost:$VLLM_PORT/health" >/dev/null 2>&1 && { echo "vLLM ready after ${i}s"; break; }
    sleep 1
done

python3 cluster-experimenting/bench_throughput.py \
    --backend vllm \
    --base-url "http://localhost:$VLLM_PORT" \
    --model "$VLLM_MODEL" \
    --concurrency "$CONCURRENCY" \
    --n-prompts "$N_PROMPTS" \
    --max-tokens "$MAX_TOKENS" \
    --out "$OUT_FILE"

kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true

### Side-by-side summary ###
echo
echo "================================================================"
echo "Side-by-side summary  (model pair: $OLLAMA_MODEL  /  $VLLM_MODEL)"
echo "================================================================"
python3 - "$OUT_FILE" <<'PY'
import json, sys
from collections import defaultdict
rows = [json.loads(l) for l in open(sys.argv[1])]
by_c = defaultdict(dict)
for r in rows:
    by_c[r["concurrency"]][r["backend"]] = r
print(f"{'conc':>4} {'backend':>7} {'wall_s':>8} {'prom_tps':>9} {'comp_tps':>9} {'ttft_p50':>9} {'ttft_p95':>9}")
for c in sorted(by_c):
    for b in ("ollama", "vllm"):
        r = by_c[c].get(b)
        if not r: continue
        print(f"{c:>4} {b:>7} {r['wall_s']:>8.1f} {r['prompt_tps']:>9.0f} {r['completion_tps']:>9.0f} {r['ttft_p50_ms']:>9.0f} {r['ttft_p95_ms']:>9.0f}")
    o = by_c[c].get("ollama"); v = by_c[c].get("vllm")
    if o and v:
        sp = (o['wall_s'] / v['wall_s']) if v['wall_s'] else 0
        print(f"     speedup (ollama_wall / vllm_wall): {sp:.2f}x")
PY

echo "End time: $(date)"
