#!/bin/bash
### Runs the PlanBench arm for ONE model on the rtx_pro_6000:1 self-deploy
### path. Loops PlanBench (task × config) in-process to keep the Ollama
### model warm across cells (10 tasks × 3 configs = 30 cells per model).
###
### v1 = vanilla leaderboard (no MCP tools). MCP-tool-using arm is tracked
### as ISS-021 — depends on sibling-repo MCP work documented in
### ../pddl-copilot/specs-for-plan-bench.md (branch: planbench-integration).
###
### Required env (set by cluster-experimenting/submit_planbench.sh):
###   MODEL    — Ollama tag (e.g. Qwen3.5:0.8B). One model per sbatch job.
###
### Optional env (defaults shown):
###   PLANBENCH_TASKS    — space-separated, default = all 10
###   PLANBENCH_CONFIGS  — space-separated, default = blocksworld logistics depots
###   PLANBENCH_INSTANCES— space-separated instance ids, default = "" (full set)
###   THINK              — on|off|default, default = off (PlanBench published
###                        baselines are non-thinking; this matches.)
###
### Resource policy (mirrors run_condition_rtx.sbatch):
###   * No --cpus-per-task (cluster default cpus-per-gpu handles it).
###   * --mem=80G on rtx_pro_6000.
###   * --tmp=50G for the SIF + model cache.
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_planbench_rtx
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_pro_6000:1
#SBATCH --mem=80G
#SBATCH --tmp=50G
#SBATCH --time=2-00:00:00

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
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
PLANBENCH_ROOT="$EXPT_ROOT/external/LLMs-Planning"

### Workspace ###
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE" 2>/dev/null; then
        WORK="$SCRATCH_BASE/planbench-work"
    else
        WORK="/tmp/planbench-${SLURM_JOB_ID}"
    fi
else
    WORK="/tmp/planbench-${SLURM_JOB_ID:-$$}"
fi
mkdir -p "$WORK/models"
cd "$WORK"

### Apptainer SIF for Ollama (cached at $HOME/ollama.sif by run_condition_rtx) ###
SIF="$WORK/ollama.sif"
if [ -f "$HOME/ollama.sif" ]; then
    echo "Using cached .sif from \$HOME/ollama.sif"
    cp "$HOME/ollama.sif" "$SIF"
else
    echo "Building ollama.sif from docker://ollama/ollama (first run, ~3 min)"
    apptainer build --force "$SIF" docker://ollama/ollama 2>&1 | tail -3
    cp "$SIF" "$HOME/ollama.sif"
fi

### Start ollama serve ###
PORT=$(( 11400 + (SLURM_JOBID % 100) ))
while ss -Hltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; do
    PORT=$(( PORT + 1 ))
    [ "$PORT" -ge 11600 ] && { echo "Error: no free port in 11400-11599"; exit 4; }
done
echo "Starting ollama serve on localhost:$PORT (NUM_PARALLEL=1, MAX_LOADED=1, CTX=16384)"
apptainer exec --nv \
    --bind "$WORK/models:/root/.ollama" \
    --writable-tmpfs \
    "$SIF" bash -c "
        export OLLAMA_HOST=0.0.0.0:$PORT
        export OLLAMA_NUM_PARALLEL=1
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE=1h
        export OLLAMA_CONTEXT_LENGTH=16384
        ollama serve
    " > "$WORK/ollama-serve.log" 2>&1 &
SERVE_PID=$!
trap 'echo "Shutting down..."; kill $SERVE_PID 2>/dev/null || true; wait 2>/dev/null || true; cd ~; rm -rf "$WORK"' EXIT

for i in $(seq 1 90); do
    if curl -sf "http://localhost:$PORT/" >/dev/null 2>&1; then
        echo "ollama serve up after ${i}s"
        break
    fi
    sleep 1
done

### Pull + warmup ###
echo "Pulling $MODEL..."
apptainer exec --nv --bind "$WORK/models:/root/.ollama" --writable-tmpfs "$SIF" \
    bash -c "OLLAMA_HOST=http://localhost:$PORT ollama pull '$MODEL'" 2>&1 | tail -2

echo "Warmup (load $MODEL into VRAM with num_ctx=16384)..."
curl -s --max-time 300 "http://localhost:$PORT/api/chat" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"1h\",\"options\":{\"num_predict\":5,\"num_ctx\":16384}}" \
    >/dev/null

VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
VRAM_PCT=$(( VRAM_USED * 100 / VRAM_TOTAL ))
echo "VRAM after warmup ($MODEL): ${VRAM_USED}/${VRAM_TOTAL} MiB (${VRAM_PCT}%)"
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
export OLLAMA_HOST="http://localhost:$PORT"

ENGINE="pddl_copilot__ollama__${MODEL}"
echo "Engine: $ENGINE"
echo "Tasks:   $PLANBENCH_TASKS"
echo "Configs: $PLANBENCH_CONFIGS"
echo "Think:   $THINK"

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
MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
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
  "engine": "$ENGINE",
  "think": "$THINK",
  "tasks": "$PLANBENCH_TASKS",
  "configs": "$PLANBENCH_CONFIGS",
  "instances": "$PLANBENCH_INSTANCES",
  "slurm_job_id": "$SLURM_JOB_ID",
  "node": "$SLURM_JOB_NODELIST",
  "host_port": "localhost:$PORT",
  "start_time_iso": "$(date -Iseconds)"
}
EOF

echo "End time: $(date)"
echo "Overall rc: $OVERALL_RC"
exit "$OVERALL_RC"
