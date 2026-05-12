#!/bin/bash
### Prefix-cache observability probe — Gemma4 architecture check.
###
### Follow-up to probe_v2: that one showed zero prefix-cache hits on
### cyankiwi/Qwen3.6-27B-AWQ-INT4 because vLLM logs
###   "Setting attention block size to 784 tokens to ensure that
###    attention page size is >= mamba page size"
### Qwen3.5/3.6 are Mamba-attention hybrids, so the 784-token block
### threshold makes hits impossible for prompts < 784 tokens.
###
### This probe answers: does Gemma4 (non-Mamba) avoid that override and
### actually register hits on identical sequential requests? If yes,
### keep --enable-prefix-caching for Gemma4 cells; if no, drop it
### universally and document.
###
### Uses google/gemma-4-E2B-it (~3-4 GB) — same gemma4 architecture
### family as production's gemma4:31b but small enough to load in ~1 min.
### The block-size override (or its absence) is architecture-dependent,
### not size-dependent, so this matches the production-relevant signal.
###
###
#SBATCH --partition=gpu
#SBATCH --job-name=vllm_prefix_cache_probe_gemma4
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=24G
#SBATCH --tmp=20G
#SBATCH --time=00:20:00

set -eo pipefail

echo "SLURM_JOBID=${SLURM_JOBID:-local}"
echo "Node: $(hostname)"
echo "Start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
HF_MODEL="google/gemma-4-E2B-it"

if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    WORK="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}/probe-work"
    mkdir -p "$WORK/hf-cache" 2>/dev/null || WORK="/tmp/vllm-pcg-${SLURM_JOB_ID}"
else
    WORK="/tmp/vllm-pcg-$$"
fi
mkdir -p "$WORK/hf-cache"

SERVE_LOG="$WORK/vllm-serve.log"
preserve() {
    [ -f "$SERVE_LOG" ] && cp -a "$SERVE_LOG" "$EXPT_ROOT/cluster-experimenting/logs/${SLURM_JOBID:-local}-vllm-serve.log" 2>/dev/null || true
}
trap 'echo "Cleanup..."; jobs -p | xargs -r kill 2>/dev/null || true; preserve; rm -rf "$WORK"' EXIT

SIF_VLLM="$WORK/vllm.sif"
if [ -f "$HOME/vllm.sif" ]; then
    cp "$HOME/vllm.sif" "$SIF_VLLM"
    echo "Reusing cached \$HOME/vllm.sif"
else
    echo "WARN: no cached SIF; building fresh from docker://vllm/vllm-openai:latest"
    apptainer build --force "$SIF_VLLM" docker://vllm/vllm-openai:latest 2>&1 | tail -3
    cp "$SIF_VLLM" "$HOME/vllm.sif"
fi

PORT=$(( 11950 + (${SLURM_JOBID:-0} % 50) ))

echo
echo "=== Starting vLLM ($HF_MODEL on :$PORT) ==="
# No tool-call/reasoning parsers — probing pure prefix-cache, not
# tool-emission semantics. Gemma's chat template handles user/assistant
# turns directly.
apptainer exec --nv \
    --bind "$WORK/hf-cache:/root/.cache/huggingface" \
    --writable-tmpfs \
    "$SIF_VLLM" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$HF_MODEL" \
        --host 0.0.0.0 \
        --port "$PORT" \
        --max-model-len 8192 \
        --gpu-memory-utilization 0.60 \
        --enable-prefix-caching \
        > "$SERVE_LOG" 2>&1 &
VLLM_PID=$!

ready=0
for i in $(seq 1 600); do
    if curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
        echo "vllm ready ($((i*2))s)"; ready=1; break
    fi
    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "vLLM died during startup; tail of $SERVE_LOG:"
        tail -120 "$SERVE_LOG"
        exit 2
    fi
    sleep 2
done
if [ "$ready" -ne 1 ]; then
    echo "vLLM did not become ready within 20 min"
    tail -120 "$SERVE_LOG"
    kill "$VLLM_PID" 2>/dev/null || true
    exit 3
fi

echo
echo "=== KEY LOG LINES — architecture + block-size config ==="
grep -E "attention block size|Mamba|prefix caching|block_size|page size|version 0\." "$SERVE_LOG" | head -20 || true

echo
echo "=== Cache config from /metrics ==="
curl -sS "http://localhost:$PORT/metrics" | grep -E "^vllm:cache_config_info" | tr ',' '\n' | grep -E "block_size|enable_prefix|num_gpu_blocks|mamba" | head -10 || true

snap_metrics() {
    local label="$1"
    echo
    echo "--- /metrics snapshot: $label ---"
    curl -sS "http://localhost:$PORT/metrics" | grep -E "^vllm:(prefix_cache_(queries|hits)_total|prompt_tokens_by_source_total|kv_cache_usage_perc)\b" || true
}

post_chat() {
    local label="$1" prompt="$2"
    echo
    echo "############ $label ############"
    curl -sS "http://localhost:$PORT/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "$(python3 -c "
import json, sys
print(json.dumps({
    'model': '$HF_MODEL',
    'messages': [{'role': 'user', 'content': sys.argv[1]}],
    'max_tokens': 4,
    'temperature': 0.0,
}))" "$prompt")" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
usage = d.get('usage') or {}
print('-- usage:', json.dumps(usage, sort_keys=True))
print('-- finish_reason:', d['choices'][0].get('finish_reason'))
"
}

# Long preamble — same shape as v2 probe (~330-350 tokens). If Gemma4 uses
# the default 16-token block size, this is plenty to populate ~20 cached
# blocks. If Gemma4 also overrides to a huge block size, hits will stay 0.
PREAMBLE='You are an expert in classical planning with PDDL. The following is a
blocksworld-style domain. Predicates: on(?x ?y), ontable(?x), clear(?x),
holding(?x), and handempty. Actions are pickup, putdown, stack, and unstack.
The pickup action requires the block to be clear, on the table, and the
hand to be empty; its effect is to put the block in the hand and clear
the table position. Putdown places a held block back on the table and
makes the hand empty. Stack(?x ?y) requires holding(?x) and clear(?y);
its effect is to place x on y, mark y as not clear, and free the hand.
Unstack(?x ?y) requires on(?x ?y), clear(?x), and handempty; its effect
is the inverse. Consider the problem instance with five blocks A, B, C,
D, and E. Initial state: ontable A, ontable B, ontable C, on D A, on E
B, clear C, clear D, clear E, handempty. The goal is to construct two
stacks: on A B and on B C and on D E and ontable A and ontable D. Each
question below pertains to this domain-and-problem pair. Now answer:'

PROMPT1="$PREAMBLE Does initial state satisfy handempty? Answer YES or NO."
PROMPT2="$PROMPT1"  # byte-identical
PROMPT3="$PREAMBLE How many blocks are mentioned? Answer with a digit."

snap_metrics "baseline"
post_chat "REQ1 (cold)" "$PROMPT1"
snap_metrics "after REQ1"
post_chat "REQ2 (byte-identical to REQ1) — expect hits jump" "$PROMPT2"
snap_metrics "after REQ2"
post_chat "REQ3 (shared preamble, swapped tail)" "$PROMPT3"
snap_metrics "after REQ3"

echo
echo "=== Done. ==="
kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true
echo "End: $(date)"
