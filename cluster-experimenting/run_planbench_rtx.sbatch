#!/bin/bash
### Runs the PlanBench arm for ONE model on a self-deployed vLLM OpenAI
### server. Loops PlanBench (task × config) in-process to keep the vLLM
### server warm across cells (10 tasks × 3 configs = 30 cells per model).
###
### Migrated from the retired Ollama self-deploy 2026-06-02 (CHANGELOG):
### the Ollama backend was retired harness-wide 2026-05-18, the
### run_condition_rtx.sbatch this file used to mirror was DELETED in that
### retirement, and the current roster's gemma4:26b-a4b is a vLLM-only AWQ
### quant that `ollama pull` cannot serve at all. This file now mirrors
### run_condition_vllm_rtx.sbatch's bootstrap (same GPU class + serve
### config) so the PlanBench arm serves the 5-task arm's exact models —
### corpus identity between the two arms.
###
### v1 = vanilla leaderboard (no MCP tools). MCP-tool-using arm is tracked
### as ISS-022 — depends on sibling-repo MCP work documented in
### ../pddl-copilot/specs-for-plan-bench.md (branch: planbench-integration).
###
### Required env (set by cluster-experimenting/submit_planbench.sh):
###   MODEL    — canonical model tag (e.g. Qwen3.5:0.8B), resolved to an HF
###              id + parser flags by vllm_lookup in lib/defaults.sh. One
###              model per sbatch job.
###
### Optional env (defaults shown):
###   PLANBENCH_TASKS    — space-separated, default = all 10
###   PLANBENCH_CONFIGS  — space-separated, default = blocksworld logistics depots
###   PLANBENCH_INSTANCES— space-separated instance ids, default = "" (full set)
###   THINK              — on|off|default, default = off (PlanBench published
###                        baselines are non-thinking; this matches). Plumbed
###                        to engine.py via PDDL_COPILOT_THINK →
###                        chat_template_kwargs.enable_thinking.
###   GPU_MEM_UTIL       — vLLM KV-cache VRAM fraction, default 0.85.
###
### Resource policy (mirrors run_condition_vllm_rtx.sbatch):
###   * rtx_6000:1 + --constraint=rtx_6000 (same GPU as the 5-task arm).
###   * --mem=48G, --tmp=80G (vLLM SIF + HF cache live on scratch).
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_planbench_rtx
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --constraint=rtx_6000
#SBATCH --mem=48G
#SBATCH --tmp=80G
#SBATCH --time=2-00:00:00

# --constraint=rtx_6000 filters out the mislabelled ee-l40s-{01,02} nodes
# (same rationale as run_condition_vllm_rtx.sbatch — their visible 44.39 GiB
# is 3.6 GiB short of what --enable-prefix-caching + gpu_mem_util=0.85 needs).

set -eo pipefail

# shellcheck source=lib/defaults.sh
source "$HOME/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh"

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Start time: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

### Required + defaults ###
: "${MODEL:?Error: export MODEL=... (submit via submit_planbench.sh)}"
echo "[env-debug] raw PLANBENCH_TASKS=\"${PLANBENCH_TASKS:-<unset>}\""
echo "[env-debug] raw PLANBENCH_CONFIGS=\"${PLANBENCH_CONFIGS:-<unset>}\""
echo "[env-debug] raw PLANBENCH_INSTANCES=\"${PLANBENCH_INSTANCES:-<unset>}\""
# submit_planbench.sh encodes space-separated multi-values as ^-joined to
# survive SLURM's comma-parsing --export. Decode here. The default values
# are already space-separated (literal), so the tr is a no-op for them.
PLANBENCH_TASKS="$(echo "${PLANBENCH_TASKS:-$PDDL_PLANBENCH_DEFAULT_TASKS}" | tr '^' ' ')"
PLANBENCH_CONFIGS="$(echo "${PLANBENCH_CONFIGS:-$PDDL_PLANBENCH_DEFAULT_CONFIGS}" | tr '^' ' ')"
PLANBENCH_INSTANCES="$(echo "${PLANBENCH_INSTANCES:-}" | tr '^' ' ')"
echo "[env-debug] decoded PLANBENCH_TASKS=\"$PLANBENCH_TASKS\""
echo "[env-debug] decoded PLANBENCH_CONFIGS=\"$PLANBENCH_CONFIGS\""
echo "[env-debug] decoded PLANBENCH_INSTANCES=\"$PLANBENCH_INSTANCES\""
THINK="${THINK:-off}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.85}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
PLANBENCH_ROOT="$EXPT_ROOT/external/LLMs-Planning"

### Resolve model → HF id + serve flags (shared with the 5-task arm) ###
# vllm_lookup (lib/defaults.sh) exports HF_MODEL + TOOL_CALL_PARSER +
# REASONING_PARSER + (optionally) MAX_NUM_BATCHED_TOKENS, or fails with a
# clear error if MODEL isn't in PDDL_VLLM_VERIFIED_MODELS.
unset MAX_NUM_BATCHED_TOKENS
vllm_lookup "$MODEL" || exit 1
MAX_NUM_BATCHED_TOKENS_FLAG=""
[ -n "${MAX_NUM_BATCHED_TOKENS:-}" ] && \
    MAX_NUM_BATCHED_TOKENS_FLAG="--max-num-batched-tokens $MAX_NUM_BATCHED_TOKENS"
REASONING_PARSER_FLAG="$(vllm_reasoning_parser_flag)"
MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

### Workspace on /scratch — ENOSPC fallback to /tmp (mirrors vLLM sbatch) ###
WORK=""
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE/vllm-work/hf-cache" 2>/dev/null; then
        WORK="$SCRATCH_BASE/vllm-work"
    else
        echo "Note: $SCRATCH_BASE unwritable or out of space, falling back to /tmp"
    fi
fi
if [ -z "$WORK" ]; then
    WORK="/tmp/planbench-${SLURM_JOB_ID:-$$}"
    mkdir -p "$WORK/hf-cache" || { echo "ERROR: cannot create $WORK/hf-cache on /tmp"; exit 1; }
fi
cd "$WORK"

### vLLM container image — PINNED to the production fleet's tag ###
VLLM_IMAGE="${VLLM_IMAGE:-docker://vllm/vllm-openai:v0.20.2}"
SIF_VLLM="$WORK/vllm.sif"
if [ -f "$HOME/vllm.sif" ]; then
    echo "Using cached vllm.sif from \$HOME/vllm.sif"
    cp "$HOME/vllm.sif" "$SIF_VLLM"
else
    echo "Building vllm.sif from $VLLM_IMAGE (first run, ~5 min)"
    apptainer build --force "$SIF_VLLM" "$VLLM_IMAGE" 2>&1 | tail -3
    cp "$SIF_VLLM" "$HOME/vllm.sif"
fi

### Pick a free port ###
PORT=$(( 11500 + (SLURM_JOBID % 100) ))
while ss -Hltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; do
    PORT=$(( PORT + 1 ))
    [ "$PORT" -ge 11999 ] && { echo "Error: no free port in 11500-11998"; exit 4; }
done

### Start vLLM serving $HF_MODEL, registered under the canonical tag $MODEL ###
# --served-model-name "$MODEL" makes the OpenAI `model` field equal the
# canonical tag (e.g. Qwen3.5:0.8B) so the PlanBench engine name stays
# pddl_copilot__vllm__<tag> — a filesystem-clean results dir, instead of
# carrying the HF id's slash (Qwen/Qwen3.5-0.8B → nested subdir). engine.py
# sends `model=<tag>` in the request body, which must match this name.
# Serve flags mirror run_condition_vllm_rtx.sbatch for an identical
# VRAM/serving profile; the tool-call + reasoning parsers are inert in v1
# (the engine sends no `tools`) but kept so the two arms share a server.
# SERVE_LOG goes straight to the persistent logs dir so it survives the
# EXIT trap's rm -rf "$WORK" (and a SIGKILL OOM the trap can't catch).
SERVE_LOG="$EXPT_ROOT/cluster-experimenting/logs/${SLURM_JOBID:-local}-vllm-${MODEL_TAG}.log"
echo "Starting vLLM on localhost:$PORT serving $HF_MODEL (served as $MODEL)"
echo "  serve flags: --tool-call-parser $TOOL_CALL_PARSER ${REASONING_PARSER_FLAG:-(no reasoning-parser)} --gpu-memory-utilization $GPU_MEM_UTIL ${MAX_NUM_BATCHED_TOKENS_FLAG:-}"
apptainer exec --nv \
    --bind "$WORK/hf-cache:/root/.cache/huggingface" \
    --writable-tmpfs \
    "$SIF_VLLM" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "$HF_MODEL" \
        --served-model-name "$MODEL" \
        --host 0.0.0.0 \
        --port "$PORT" \
        --max-model-len 16384 \
        --enable-auto-tool-choice \
        --tool-call-parser "$TOOL_CALL_PARSER" \
        $REASONING_PARSER_FLAG \
        --gpu-memory-utilization "$GPU_MEM_UTIL" \
        --enable-prefix-caching \
        $MAX_NUM_BATCHED_TOKENS_FLAG \
        > "$SERVE_LOG" 2>&1 &
VLLM_PID=$!
trap 'echo "Shutting down..."; kill $VLLM_PID 2>/dev/null || true; wait 2>/dev/null || true; cd ~; rm -rf "$WORK"' EXIT

### Readiness probe (20-min ceiling; mirrors vLLM sbatch) ###
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
    exit 3
fi

### VRAM 85% guard ###
VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
VRAM_PCT=$(( VRAM_USED * 100 / VRAM_TOTAL ))
echo "VRAM after vLLM load ($MODEL): ${VRAM_USED}/${VRAM_TOTAL} MiB (${VRAM_PCT}%)"
if [ "$VRAM_PCT" -gt 85 ]; then
    echo "ERROR: VRAM usage ${VRAM_PCT}% exceeds 85%; aborting." >&2
    exit 3
fi

### Provision PlanBench (idempotent: skips if external/LLMs-Planning is built) ###
if [ ! -d "$PLANBENCH_ROOT/.venv" ]; then
    echo "Running planbench/setup.sh (first run on this host)..."
    bash "$EXPT_ROOT/planbench/setup.sh"
fi

### Env exports for PlanBench's pipeline ###
# shellcheck disable=SC1090
source <(bash "$EXPT_ROOT/planbench/setup.sh" --print-env-only)
# shellcheck disable=SC1091
source "$PLANBENCH_ROOT/.venv/bin/activate"
# engine.py's _vllm_chat reads these two: VLLM_BASE must include the /v1
# suffix (the adapter appends /chat/completions); PDDL_COPILOT_THINK toggles
# qwen3 thinking via chat_template_kwargs.enable_thinking.
export VLLM_BASE="http://localhost:$PORT/v1"
export PDDL_COPILOT_THINK="$THINK"
# Optional output-cap override (engine.py floors num_predict at 4096). Set
# NUM_PREDICT via submit_planbench.sh --num-predict to match the tools arm for
# a clean tools-vs-no-tools baseline (e.g. 8192 = single-task sweep solve cap).
[ -n "${NUM_PREDICT:-}" ] && export PDDL_COPILOT_NUM_PREDICT="$NUM_PREDICT"

ENGINE="pddl_copilot__vllm__${MODEL}"
echo "Engine:    $ENGINE"
echo "VLLM_BASE: $VLLM_BASE"
echo "Tasks:     $PLANBENCH_TASKS"
echo "Configs:   $PLANBENCH_CONFIGS"
echo "Think:     $THINK"

### Inner loop: task × config -----------------------------------------------
cd "$PLANBENCH_ROOT/plan-bench"
OVERALL_RC=0
for TASK in $PLANBENCH_TASKS; do
    for CONFIG in $PLANBENCH_CONFIGS; do
        echo
        echo "===================================================================="
        echo "TASK=$TASK CONFIG=$CONFIG ENGINE=$ENGINE   started $(date)"
        echo "===================================================================="

        INSTANCE_ARGS=()
        if [ -n "$PLANBENCH_INSTANCES" ]; then
            # shellcheck disable=SC2086  # we want word-splitting here
            INSTANCE_ARGS=(--specific_instances $PLANBENCH_INSTANCES)
        fi
        echo "[env-debug] INSTANCE_ARGS=(${INSTANCE_ARGS[*]})"
        echo "[env-debug] python invocation: response_generation.py --task $TASK --config $CONFIG --engine $ENGINE --verbose False ${INSTANCE_ARGS[*]}"

        # Stage 2 — response generation against our engine. We call this
        # directly (rather than llm_plan_pipeline.py) because that pipeline
        # script doesn't forward --specific_instances to response_generation,
        # so the filter we pass here would be silently dropped. Stage 1
        # (prompt_generation) is skipped because PlanBench ships pre-built
        # prompts/<config>/*.json files for the canonical configs.
        python3 response_generation.py \
            --task "$TASK" \
            --config "$CONFIG" \
            --engine "$ENGINE" \
            --verbose False \
            "${INSTANCE_ARGS[@]}" \
            || { echo "response_generation rc=$? for $TASK/$CONFIG"; OVERALL_RC=1; continue; }

        # Stage 3 — evaluation. Uses VAL (and PR2 for t4-t8) which were built
        # by planbench/setup.sh. The evaluator is task-specific; the dispatch
        # mirrors llm_plan_pipeline.py.
        case "$TASK" in
            t7)    EVAL_KIND="evaluate_state" ;;
            t3)    EVAL_KIND="evaluate_verification" ;;
            *)     EVAL_KIND="evaluate_plan" ;;
        esac
        python3 response_evaluation.py \
            --task "$TASK" \
            --config "$CONFIG" \
            --engine "$ENGINE" \
            --verbose False \
            "${INSTANCE_ARGS[@]}" \
            || { echo "response_evaluation rc=$? for $TASK/$CONFIG"; OVERALL_RC=1; continue; }

        echo "TASK=$TASK CONFIG=$CONFIG   finished $(date)"
    done
done

### Rsync results into our results/planbench/<tag>/ namespace --------------
OUT_DIR="$EXPT_ROOT/results/planbench/slurm_${MODEL_TAG}_${SLURM_JOB_ID}"
mkdir -p "$OUT_DIR"
echo
echo "Rsyncing PlanBench results → $OUT_DIR"
rsync -a "$PLANBENCH_ROOT/plan-bench/results/" "$OUT_DIR/results/"
rsync -a "$PLANBENCH_ROOT/plan-bench/responses/" "$OUT_DIR/responses/"

# Manifest: which model/engine/tasks/configs produced this corpus.
cat > "$OUT_DIR/manifest.json" <<EOF
{
  "model": "$MODEL",
  "hf_model": "$HF_MODEL",
  "backend": "vllm",
  "engine": "$ENGINE",
  "think": "$THINK",
  "tasks": "$PLANBENCH_TASKS",
  "configs": "$PLANBENCH_CONFIGS",
  "instances": "$PLANBENCH_INSTANCES",
  "slurm_job_id": "$SLURM_JOB_ID",
  "node": "$SLURM_JOB_NODELIST",
  "vllm_base": "localhost:$PORT/v1",
  "start_time_iso": "$(date -Iseconds)"
}
EOF

echo "End time: $(date)"
echo "Overall rc: $OVERALL_RC"
exit "$OVERALL_RC"
