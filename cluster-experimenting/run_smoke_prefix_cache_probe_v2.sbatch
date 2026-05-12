#!/bin/bash
### Prefix-cache observability probe — follow-up (production model + per-step metrics).
###
### Disambiguates three explanations for the v1 probe's zero-hit result:
###   (A) vLLM V1 metric mis-wiring   — measure delta across every step.
###   (B) Chat-template entropy        — compare prompt_token_ids across
###                                       identical chat-completions calls,
###                                       and run a /v1/completions twin so
###                                       the chat template is bypassed.
###   (C) Production silently broken   — run on the production model
###                                       (cyankiwi/Qwen3.6-27B-AWQ-INT4) with
###                                       production flags so the result
###                                       directly reflects the live sweep.
###
### Walltime: ~12-15 min (SIF copy 10 s + HF download ~3 min + serve up
### ~3 min + 6 short requests). --time=00:30:00 covers cold downloads.
###
#SBATCH --partition=gpu
#SBATCH --job-name=vllm_prefix_cache_probe_v2
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=48G
#SBATCH --tmp=40G
#SBATCH --time=00:30:00

set -eo pipefail

echo "SLURM_JOBID=${SLURM_JOBID:-local}"
echo "Node: $(hostname)"
echo "Start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"

# Match production exactly — same HF id, same parsers.
HF_MODEL="cyankiwi/Qwen3.6-27B-AWQ-INT4"
TOOL_CALL_PARSER="qwen3_xml"
REASONING_PARSER="qwen3"

if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    WORK="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}/probe-work"
    mkdir -p "$WORK/hf-cache" 2>/dev/null || WORK="/tmp/vllm-pc2-${SLURM_JOB_ID}"
else
    WORK="/tmp/vllm-pc2-$$"
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

PORT=$(( 11900 + (${SLURM_JOBID:-0} % 50) ))

echo
echo "=== Starting vLLM ($HF_MODEL on :$PORT) — production flags + prompt-tokens-details ==="
apptainer exec --nv \
    --bind "$WORK/hf-cache:/root/.cache/huggingface" \
    --writable-tmpfs \
    "$SIF_VLLM" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$HF_MODEL" \
        --host 0.0.0.0 \
        --port "$PORT" \
        --max-model-len 16384 \
        --enable-auto-tool-choice \
        --tool-call-parser "$TOOL_CALL_PARSER" \
        --reasoning-parser "$REASONING_PARSER" \
        --gpu-memory-utilization 0.85 \
        --enable-prefix-caching \
        --enable-prompt-tokens-details \
        > "$SERVE_LOG" 2>&1 &
VLLM_PID=$!

ready=0
for i in $(seq 1 600); do
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
    echo "vLLM did not become ready within 20 min"
    tail -120 "$SERVE_LOG"
    kill "$VLLM_PID" 2>/dev/null || true
    exit 3
fi

echo
echo "=== Cache config from /metrics ==="
curl -sS "http://localhost:$PORT/metrics" | grep -E "^vllm:cache_config_info" | tr ',' '\n' | head -30 || true

snap_metrics() {
    local label="$1"
    echo
    echo "--- /metrics snapshot: $label ---"
    curl -sS "http://localhost:$PORT/metrics" | grep -E "^vllm:(prefix_cache_(queries|hits)_total|prompt_tokens_(cached_total|by_source_total)|kv_cache_usage_perc)\b" || true
}

post_chat() {
    local label="$1" prompt="$2"
    echo
    echo "############ $label (chat) ############"
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
tids  = d.get('prompt_token_ids') or []
print('-- usage:', json.dumps(usage, sort_keys=True))
print('-- prompt_token_ids len:', len(tids))
print('-- prompt_token_ids head[:20]:', tids[:20])
print('-- prompt_token_ids tail[-10:]:', tids[-10:])
print('-- finish_reason:', d['choices'][0].get('finish_reason'))
print('-- content head:', repr((d['choices'][0]['message'].get('content') or '')[:60]))
"
}

post_completions() {
    local label="$1" prompt="$2"
    echo
    echo "############ $label (completions, no chat template) ############"
    curl -sS "http://localhost:$PORT/v1/completions" \
        -H "Content-Type: application/json" \
        -d "$(python3 -c "
import json, sys
print(json.dumps({
    'model': '$HF_MODEL',
    'prompt': sys.argv[1],
    'max_tokens': 4,
    'temperature': 0.0,
}))" "$prompt")" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
usage = d.get('usage') or {}
tids  = d.get('prompt_token_ids') or []
print('-- usage:', json.dumps(usage, sort_keys=True))
print('-- prompt_token_ids len:', len(tids))
print('-- prompt_token_ids head[:20]:', tids[:20])
print('-- prompt_token_ids tail[-10:]:', tids[-10:])
print('-- finish_reason:', d['choices'][0].get('finish_reason'))
print('-- text head:', repr((d['choices'][0].get('text') or '')[:60]))
"
}

# Longer, more realistic preamble — ~600-800 tokens after tokenization, well above
# any plausible per-request threshold and well above 16-token block alignment.
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
question below pertains to this domain-and-problem pair. Reasoning
about reachability, optimal plan length, and individual action
applicability requires inspecting both initial state and goal carefully.
Now please answer the following question concisely:'

Q1=" Does the initial state satisfy handempty? Answer YES or NO."
Q2=" How many blocks are in the problem? Answer with a single digit."

PROMPT1="$PREAMBLE$Q1"
PROMPT2="$PREAMBLE$Q1"  # byte-identical to PROMPT1
PROMPT3="$PREAMBLE$Q2"  # shared preamble, different tail

snap_metrics "baseline (no requests yet)"

post_chat "REQ1 chat (cold)" "$PROMPT1"
snap_metrics "after REQ1 chat"

post_chat "REQ2 chat (byte-identical to REQ1)" "$PROMPT2"
snap_metrics "after REQ2 chat — expect hits jump"

post_chat "REQ3 chat (shared preamble, swapped tail)" "$PROMPT3"
snap_metrics "after REQ3 chat — expect partial hits"

# /v1/completions twin: bypasses chat template entirely. If chat-completion
# hits stayed at 0 but raw completions DO register hits, the suspect is the
# chat template. If raw completions ALSO show zero hits, suspect (A): the
# metric is mis-wired in this V1 build.
post_completions "REQ4 raw (cold)" "$PROMPT1"
snap_metrics "after REQ4 raw"

post_completions "REQ5 raw (identical to REQ4)" "$PROMPT1"
snap_metrics "after REQ5 raw — expect hits jump"

echo
echo "=== Done. ==="
kill "$VLLM_PID" 2>/dev/null || true
wait "$VLLM_PID" 2>/dev/null || true
echo "End: $(date)"
