#!/bin/bash
### Prefix-cache observability probe.
###
### Question: does the cached vllm.sif populate
###   usage.prompt_tokens_details.cached_tokens
### in chat completion responses when --enable-prompt-tokens-details +
### --enable-prefix-caching are set together? If yes, the harness can log
### per-trial hit rate by adding a single field extraction in
### pddl_eval/vllm_client.py. If no, fall back to scraping /metrics for
### vllm:gpu_prefix_cache_hit_rate.
###
### Procedure:
###   * Boot vLLM with --enable-prefix-caching --enable-prompt-tokens-details
###     on the smallest verified model (Qwen3.5:0.8B, ~2 GB VRAM, ~2 min load).
###   * Print vLLM version banner from the serve log.
###   * Send 3 chat completion requests:
###       REQ1: ~500-token prompt with a chunky preamble. Cold prefill.
###       REQ2: byte-identical to REQ1. Expect cached_tokens ≈ prompt_tokens.
###       REQ3: same preamble, last sentence swapped. Expect partial hit.
###   * Dump the full `usage` block from each response.
###   * Scrape /metrics for vllm:gpu_prefix_cache_* and any cached_tokens
###     counters as a parallel observability path.
###
### Walltime: ~6-8 min (SIF copy 10 s + HF download ~30 s + serve up ~2 min
###          + 3 fast requests). --time=00:15:00 covers it with margin.
###
#SBATCH --partition=gpu
#SBATCH --job-name=vllm_prefix_cache_probe
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=24G
#SBATCH --tmp=20G
#SBATCH --time=00:15:00

set -eo pipefail

echo "SLURM_JOBID=${SLURM_JOBID:-local}"
echo "Node: $(hostname)"
echo "Start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
HF_MODEL="Qwen/Qwen3.5-0.8B"

if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    WORK="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}/probe-work"
    mkdir -p "$WORK/hf-cache" 2>/dev/null || WORK="/tmp/vllm-pc-${SLURM_JOB_ID}"
else
    WORK="/tmp/vllm-pc-$$"
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

PORT=$(( 11800 + (${SLURM_JOBID:-0} % 100) ))

echo
echo "=== Starting vLLM ($HF_MODEL on :$PORT) ==="
apptainer exec --nv \
    --bind "$WORK/hf-cache:/root/.cache/huggingface" \
    --writable-tmpfs \
    "$SIF_VLLM" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$HF_MODEL" \
        --host 0.0.0.0 \
        --port "$PORT" \
        --max-model-len 4096 \
        --gpu-memory-utilization 0.40 \
        --enable-prefix-caching \
        --enable-prompt-tokens-details \
        > "$SERVE_LOG" 2>&1 &
VLLM_PID=$!

ready=0
for i in $(seq 1 300); do
    if curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
        echo "vllm ready ($((i*2))s)"; ready=1; break
    fi
    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "vLLM died during startup; tail of $SERVE_LOG:"
        tail -80 "$SERVE_LOG"
        exit 2
    fi
    sleep 2
done
if [ "$ready" -ne 1 ]; then
    echo "vLLM did not become ready within 10 min"
    tail -80 "$SERVE_LOG"
    kill "$VLLM_PID" 2>/dev/null || true
    exit 3
fi

echo
echo "=== vLLM version banner ==="
grep -E "^INFO .* (vllm|Initializing|version)" "$SERVE_LOG" | head -10 || true
grep -iE "vllm version|vllm.*[0-9]+\.[0-9]+" "$SERVE_LOG" | head -5 || true

# Long-ish stable preamble. ~150 tokens — comfortably above one cache block
# (16 tokens) so we can see meaningful cached_tokens numbers on a hit.
PREAMBLE='You are an expert in classical planning and PDDL.
Consider the following domain definition with predicates, actions, and
precondition-effect schemas. The domain models a blocksworld-style task
in which a robotic arm stacks and unstacks blocks on a table. Predicates
include on(?x ?y), ontable(?x), clear(?x), holding(?x), and handempty.
Actions are pickup, putdown, stack, and unstack. Each action has
preconditions over these predicates and corresponding add/delete effects.
Consider the problem instance with three blocks A, B, C. Initial state:
ontable A, ontable B, on C A, clear B, clear C, handempty. Goal: on A B
and on B C. Answer the following question:'

PROMPT1="$PREAMBLE Is the goal reachable from the initial state? Reply with YES or NO only."
PROMPT2="$PROMPT1"  # byte-identical → maximum cache hit
PROMPT3="$PREAMBLE How many blocks are mentioned in the problem? Reply with a single digit."

call_chat() {
    local label="$1" prompt="$2"
    echo
    echo "=== $label ==="
    curl -sS "http://localhost:$PORT/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "$(python3 -c "
import json, sys
prompt = sys.argv[1]
print(json.dumps({
    'model': '$HF_MODEL',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 8,
    'temperature': 0.0,
}))" "$prompt")" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('-- response keys:', sorted(d.keys()))
print('-- usage:', json.dumps(d.get('usage'), indent=2, sort_keys=True))
print('-- finish_reason:', d['choices'][0].get('finish_reason'))
print('-- content (truncated):', repr((d['choices'][0]['message'].get('content') or '')[:60]))
"
}

call_chat "REQ1 (cold)" "$PROMPT1"
call_chat "REQ2 (identical → expect high cached_tokens)" "$PROMPT2"
call_chat "REQ3 (shared preamble, different tail)" "$PROMPT3"

echo
echo "=== /metrics prefix-cache lines ==="
curl -sS "http://localhost:$PORT/metrics" | grep -iE "^(# HELP )?vllm.*(prefix|cache)" | head -40 || true

echo
echo "=== Done. ==="
kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true
echo "End: $(date)"
