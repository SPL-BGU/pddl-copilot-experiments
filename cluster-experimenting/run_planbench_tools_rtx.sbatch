#!/bin/bash
### PlanBench v2 (MCP tools-on, ISS-022) arm for ONE model on a self-deployed
### vLLM OpenAI server PLUS the pddl-copilot MCP plugins. Same self-deploy +
### task×config loop as run_planbench_rtx.sbatch (v1), but the engine routes
### each instance through pddl_eval.chat.chat_with_tools so the model can
### consult the MCP planner / validator before answering. PlanBench stays
### single-turn (one send_query per instance); the tool-loop is internal.
###
### v1 vs v2 deltas (everything else mirrors run_planbench_rtx.sbatch):
###   * engine name  pddl_copilot__vllm__<tag>  ->  pddl_copilot__vllm-tools__<tag>
###     (the `vllm-tools` backend token keeps the `pddl_copilot__` prefix so
###     PlanBench's already-patched dispatch branch catches it — no re-clone).
###   * venv  .venv (openai<1.0)  ->  .venv-tools (openai>=1.0 + mcp), built by
###     planbench/setup.sh --tools; the v1 venv is left frozen.
###   * MCP plugins (pddl-solver + pddl-validator) from $PDDL_MARKETPLACE_PATH
###     are pre-warmed (venv provisioned) so MCPPlanner's initialize handshake
###     doesn't race a cold pip install. The plugin servers launch on demand.
###
### A t1-only smoke needs NO new MCP tools — existing classic_planner +
### validators suffice; the sibling repo stays on whatever branch is checked
### out ($HOME/pddl-copilot, typically main). The FULL 10-task v2 additionally
### needs validate_plan_structured + optimal_plan (specs-for-plan-bench.md).
###
### Required env (set by cluster-experimenting/submit_planbench.sh --tools):
###   MODEL    — canonical model tag (e.g. Qwen3.5:0.8B), resolved by
###              vllm_lookup. One model per sbatch job.
###
### Optional env (defaults shown):
###   PLANBENCH_TASKS    — space-separated, default = all 10
###   PLANBENCH_CONFIGS  — space-separated, default = blocksworld logistics depots
###   PLANBENCH_INSTANCES— space-separated instance ids, default = "" (full set)
###   THINK              — on|off|default|effort-<low|medium|high>, default = off
###                        (baselines non-thinking). effort-* is for models whose
###                        lookup sets SUPPORTS_REASONING_EFFORT=1 (gpt-oss:20b):
###                        it runs like `default` and sends reasoning_effort, as
###                        run_condition_vllm_rtx.sbatch does. ministral3:14b
###                        needs THINK=default (its tokenizer rejects
###                        chat_template_kwargs).
###   PROMPT_ARM         — legacy|plain|steered, default = legacy. legacy is the
###                        pre-D1e engine pddl_copilot__vllm-tools__<tag> (its
###                        prompt unchanged). plain / steered are the D1e arms,
###                        engines pddl_copilot__vllm-tools-<arm>__<tag>, t1 only,
###                        both on the frozen WT format clause
###                        (planbench/engine.py _VLLM_TOOLS_ARMS).
###   GPU_MEM_UTIL       — vLLM KV-cache VRAM fraction, default 0.85.
###   PDDL_MARKETPLACE_PATH — pddl-copilot clone with plugins/, default
###                        $HOME/pddl-copilot.
###   PDDL_PLANBENCH_PLUGINS — space-separated plugin names exposed to the
###                        model, default "pddl-solver pddl-validator".
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_planbench_tools_rtx
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --constraint=rtx_6000
#SBATCH --mem=48G
#SBATCH --tmp=80G
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
: "${MODEL:?Error: export MODEL=... (submit via submit_planbench.sh --tools)}"
echo "[env-debug] raw PLANBENCH_TASKS=\"${PLANBENCH_TASKS:-<unset>}\""
echo "[env-debug] raw PLANBENCH_CONFIGS=\"${PLANBENCH_CONFIGS:-<unset>}\""
echo "[env-debug] raw PLANBENCH_INSTANCES=\"${PLANBENCH_INSTANCES:-<unset>}\""
# submit_planbench.sh encodes space-separated multi-values as ^-joined to
# survive SLURM's comma-parsing --export. Decode here.
PLANBENCH_TASKS="$(echo "${PLANBENCH_TASKS:-$PDDL_PLANBENCH_DEFAULT_TASKS}" | tr '^' ' ')"
PLANBENCH_CONFIGS="$(echo "${PLANBENCH_CONFIGS:-$PDDL_PLANBENCH_DEFAULT_CONFIGS}" | tr '^' ' ')"
PLANBENCH_INSTANCES="$(echo "${PLANBENCH_INSTANCES:-}" | tr '^' ' ')"
echo "[env-debug] decoded PLANBENCH_TASKS=\"$PLANBENCH_TASKS\""
echo "[env-debug] decoded PLANBENCH_CONFIGS=\"$PLANBENCH_CONFIGS\""
echo "[env-debug] decoded PLANBENCH_INSTANCES=\"$PLANBENCH_INSTANCES\""
THINK="${THINK:-off}"
PROMPT_ARM="${PROMPT_ARM:-legacy}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.85}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
PLANBENCH_ROOT="$EXPT_ROOT/external/LLMs-Planning"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"
PLANBENCH_PLUGINS="${PDDL_PLANBENCH_PLUGINS:-pddl-solver pddl-validator}"

### Prompt arm → engine backend token (D1e) ###
case "$PROMPT_ARM" in
    legacy)  ENGINE_BACKEND="vllm-tools" ;;
    plain)   ENGINE_BACKEND="vllm-tools-plain" ;;
    steered) ENGINE_BACKEND="vllm-tools-steered" ;;
    *) echo "Error: PROMPT_ARM=$PROMPT_ARM (must be legacy|plain|steered)" >&2; exit 1 ;;
esac
if [ "$PROMPT_ARM" != "legacy" ] && [ "$PLANBENCH_TASKS" != "t1" ]; then
    # The arms' format clause is t1-only; the engine would SystemExit on every
    # other task. Refuse here, before the GPU job loads a model.
    echo "Error: PROMPT_ARM=$PROMPT_ARM is t1-only; got PLANBENCH_TASKS=\"$PLANBENCH_TASKS\"" >&2
    exit 1
fi
case "$THINK" in
    on|off|default|effort-low|effort-medium|effort-high) ;;
    *) echo "Error: THINK=$THINK (must be on|off|default|effort-low|effort-medium|effort-high)" >&2; exit 1 ;;
esac

### Resolve model → HF id + serve flags (shared with the 5-task arm) ###
# Same per-model handling as run_condition_vllm_rtx.sbatch (PR #122, #126):
# every optional extra is unset first so nothing leaks in through the
# environment, then lib/defaults.sh sets the ones this model needs. All of
# them stay empty for the models verified before 2026-10-27 (Qwen3.5,
# Qwen3.6-35B, the AWQ Gemma), so their serve command is unchanged.
unset MAX_NUM_BATCHED_TOKENS CHAT_TEMPLATE EXTRA_SERVE_ARGS HF_REVISION HF_CACHE_IN_JOB TOOL_CALL_ID_STYLE \
    SUPPORTS_REASONING_EFFORT
unset PDDL_TOOL_CALL_ID_STYLE PDDL_REASONING_EFFORT PDDL_STORE_REASONING
vllm_lookup "$MODEL" || exit 1
MAX_NUM_BATCHED_TOKENS_FLAG=""
[ -n "${MAX_NUM_BATCHED_TOKENS:-}" ] && \
    MAX_NUM_BATCHED_TOKENS_FLAG="--max-num-batched-tokens $MAX_NUM_BATCHED_TOKENS"
REASONING_PARSER_FLAG="$(vllm_reasoning_parser_flag)"
MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
# The template path is under $EXPT_ROOT, inside $HOME, which apptainer binds.
CHAT_TEMPLATE_FLAG=""
if [ -n "${CHAT_TEMPLATE:-}" ]; then
    if [ ! -f "$EXPT_ROOT/$CHAT_TEMPLATE" ]; then
        echo "Error: chat template $EXPT_ROOT/$CHAT_TEMPLATE not found"; exit 1
    fi
    CHAT_TEMPLATE_FLAG="--chat-template $EXPT_ROOT/$CHAT_TEMPLATE"
fi
EXTRA_SERVE_FLAGS="${EXTRA_SERVE_ARGS:-}"
if [ -n "${HF_REVISION:-}" ]; then
    EXTRA_SERVE_FLAGS="$EXTRA_SERVE_FLAGS --revision $HF_REVISION --tokenizer-revision $HF_REVISION"
fi
# HF_CACHE_IN_JOB=1: weights download to the job's scratch hf-cache, not $HOME.
APPTAINER_ENV=()
if [ "${HF_CACHE_IN_JOB:-0}" = "1" ]; then
    APPTAINER_ENV=(APPTAINERENV_HF_HOME=/root/.cache/huggingface)
fi
# Client-side per-model setting, read by pddl_eval.vllm_client.VLLMClient
# (the engine's tool loop uses it); exported below with the other env.
# effort-<level>: run as `default` (no chat_template_kwargs) and send
# reasoning_effort=<level>. A model that ignores the field would run a default
# cell under an effort label, so refuse it, as the main sbatch does.
EFFORT=""
ENGINE_THINK="$THINK"
if [[ "$THINK" == effort-* ]]; then
    if [ "${SUPPORTS_REASONING_EFFORT:-0}" != "1" ]; then
        echo "Error: THINK=$THINK needs a model that reads reasoning_effort (gpt-oss); $MODEL does not" >&2
        exit 1
    fi
    EFFORT="${THINK#effort-}"
    ENGINE_THINK="default"
fi
if [ "${TOOL_CALL_ID_STYLE:-}" = "mistral9" ] && [ "$THINK" != "default" ]; then
    # lib/defaults.sh: Mistral's tokenizer rejects any request carrying
    # chat_template_kwargs, which THINK=on/off sends. Every request would fail
    # and PlanBench would grade a run of empty answers.
    echo "Error: $MODEL must run with THINK=default (got THINK=$THINK)" >&2
    exit 1
fi

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
# The tool-call + reasoning parsers are LIVE here (unlike v1) — the engine
# sends `tools`, so vLLM must extract the model's tool calls.
SERVE_LOG="$EXPT_ROOT/cluster-experimenting/logs/${SLURM_JOBID:-local}-vllm-tools-${MODEL_TAG}.log"
echo "Starting vLLM on localhost:$PORT serving $HF_MODEL (served as $MODEL)"
echo "  serve flags: --tool-call-parser $TOOL_CALL_PARSER ${REASONING_PARSER_FLAG:-(no reasoning-parser)} --gpu-memory-utilization $GPU_MEM_UTIL ${MAX_NUM_BATCHED_TOKENS_FLAG:-} ${CHAT_TEMPLATE_FLAG:-} ${EXTRA_SERVE_FLAGS:-}"
[ "${HF_CACHE_IN_JOB:-0}" = "1" ] && echo "  hf cache: job scratch ($WORK/hf-cache)"
env "${APPTAINER_ENV[@]}" apptainer exec --nv \
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
        $CHAT_TEMPLATE_FLAG \
        $EXTRA_SERVE_FLAGS \
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

### Conda env (python3.12 + Java) — mirrors run_condition_vllm_rtx.sbatch ----
# The cluster has no system python>=3.10 (/usr/bin/python3 is 3.9, no uv on
# PATH); `mcp` needs >=3.10. The 5-task arm's conda env `pddl_copilot`
# (python=3.12, openjdk=17) is the python>=3.10 source — and what built the
# plugin venvs. Activating it makes `python3` 3.12 so setup.sh --tools builds
# .venv-tools on a 3.12 base (mcp installs); Java stays on PATH after the venv
# layers on top. WITHOUT this the tools venv silently falls back to 3.9 and
# `pip install mcp` fails with "No matching distribution".
ENV_NAME="${ENV_NAME:-pddl_copilot}"
module load anaconda
source activate "$ENV_NAME"

### gpt-oss: check the effort the served model really gets (main sbatch idiom) ###
# Render-only request (no generation); the job log shows the Harmony system
# line. An effort cell whose line does not show its level is refused. Runs
# after the conda env is active: reasoning_settings.py needs python>=3.10.
HARMONY_LINE=""
if [ "${SUPPORTS_REASONING_EFFORT:-0}" = "1" ]; then
    HARMONY_RC=0
    HARMONY_LINE="$(python3 "$EXPT_ROOT/cluster-experimenting/reasoning_settings.py" system-line \
        --base-url "http://localhost:$PORT/v1" --model "$MODEL" ${EFFORT:+--effort "$EFFORT"})" \
        || HARMONY_RC=$?
    echo "  $HARMONY_LINE"
    if [ -n "$EFFORT" ] && [ "$HARMONY_RC" -ne 0 ]; then
        echo "Error: reasoning_effort=$EFFORT is not on the served system line; aborting" >&2
        exit 3
    fi
fi

### Provision PlanBench + the TOOLS venv (idempotent) -----------------------
# setup.sh --tools clones/patches the checkout, builds VAL/PR2/FD, and creates
# BOTH .venv (v1, frozen) and .venv-tools (v2: openai>=1.0 + mcp). Guarded on
# .venv-tools so a host that only ran v1 still gets the tools venv built.
if [ ! -d "$PLANBENCH_ROOT/.venv-tools" ]; then
    echo "Provisioning PlanBench tools venv (planbench/setup.sh --tools)..."
    bash "$EXPT_ROOT/planbench/setup.sh" --tools
fi

### Marketplace + plugin pre-warm ------------------------------------------
# Pre-create the plugin venvs so MCPPlanner.connect's stdio initialize
# handshake doesn't race a multi-minute first-launch pip install. Mirrors
# plugins/<name>/scripts/launch-server.sh's provisioning (venv + requirements)
# without starting the server.
if [ ! -d "$MARKETPLACE_PATH/plugins" ]; then
    echo "ERROR: PDDL_MARKETPLACE_PATH has no plugins/ at $MARKETPLACE_PATH" >&2
    echo "  Clone the marketplace: git clone <SPL-BGU/pddl-copilot> $MARKETPLACE_PATH" >&2
    exit 5
fi
for P in $PLANBENCH_PLUGINS; do
    PDIR="$MARKETPLACE_PATH/plugins/$P"
    if [ ! -d "$PDIR" ]; then
        echo "ERROR: required plugin '$P' missing under $MARKETPLACE_PATH/plugins" >&2
        exit 5
    fi
    if [ ! -d "$PDIR/.venv" ]; then
        echo "Pre-warming $P plugin venv (first launch on this host)..."
        python3 -m venv "$PDIR/.venv"
        "$PDIR/.venv/bin/pip" install --quiet --upgrade pip
        "$PDIR/.venv/bin/pip" install --quiet -r "$PDIR/requirements.txt"
    fi
    echo "Plugin ready: $P"
done

### Env exports for PlanBench's pipeline ###
# shellcheck disable=SC1090
source <(bash "$EXPT_ROOT/planbench/setup.sh" --print-env-only)
# Activate the TOOLS venv (NOT the v1 .venv): openai>=1.0 + mcp.
# shellcheck disable=SC1091
source "$PLANBENCH_TOOLS_VENV/bin/activate"
# engine.py's vllm-tools path reads these: VLLM_BASE must include /v1
# (VLLMClient normalises it); PDDL_MARKETPLACE_PATH + PDDL_PLANBENCH_PLUGINS
# locate the MCP plugins; PDDL_COPILOT_TOOLLOG captures the per-instance
# tool-call transcript for content-validation; PDDL_COPILOT_THINK toggles
# qwen3 thinking.
export VLLM_BASE="http://localhost:$PORT/v1"
export PDDL_COPILOT_THINK="$ENGINE_THINK"
[ -n "${TOOL_CALL_ID_STYLE:-}" ] && export PDDL_TOOL_CALL_ID_STYLE="$TOOL_CALL_ID_STYLE"
[ -n "$EFFORT" ] && export PDDL_REASONING_EFFORT="$EFFORT"
export PDDL_MARKETPLACE_PATH="$MARKETPLACE_PATH"
export PDDL_PLANBENCH_PLUGINS="$PLANBENCH_PLUGINS"
export PDDL_COPILOT_TOOLLOG="$EXPT_ROOT/cluster-experimenting/logs/${SLURM_JOBID:-local}-toolcalls-${ENGINE_BACKEND}-${MODEL_TAG}.jsonl"
# Raise the per-instance output cap (engine.py floors at 4096). Set NUM_PREDICT
# to the single-task sweep's solve cap (8192) so plan-generation answers don't
# truncate; same value as the no-tools arm for a clean baseline.
[ -n "${NUM_PREDICT:-}" ] && export PDDL_COPILOT_NUM_PREDICT="$NUM_PREDICT"

ENGINE="pddl_copilot__${ENGINE_BACKEND}__${MODEL}"
echo "Engine:      $ENGINE"
echo "Prompt arm:  $PROMPT_ARM"
echo "VLLM_BASE:   $VLLM_BASE"
echo "Marketplace: $MARKETPLACE_PATH (plugins: $PLANBENCH_PLUGINS)"
echo "Tool log:    $PDDL_COPILOT_TOOLLOG"
echo "Tasks:       $PLANBENCH_TASKS"
echo "Configs:     $PLANBENCH_CONFIGS"
echo "Think:       $THINK${EFFORT:+ (engine think=default, reasoning_effort=$EFFORT)}"

### Inner loop: task × config -----------------------------------------------
cd "$PLANBENCH_ROOT/plan-bench"
OVERALL_RC=0
for TASK in $PLANBENCH_TASKS; do
    for CONFIG in $PLANBENCH_CONFIGS; do
        echo
        echo "===================================================================="
        echo "TASK=$TASK CONFIG=$CONFIG ENGINE=$ENGINE   started $(date)"
        echo "===================================================================="

        # engine.py's _tools_system_prompt() reads this to pick the task's
        # forcing tool prompt + output format (t3 verdict / t7 state / else plan).
        export PDDL_COPILOT_TASK="$TASK"

        INSTANCE_ARGS=()
        if [ -n "$PLANBENCH_INSTANCES" ]; then
            # shellcheck disable=SC2086  # we want word-splitting here
            INSTANCE_ARGS=(--specific_instances $PLANBENCH_INSTANCES)
        fi
        echo "[env-debug] INSTANCE_ARGS=(${INSTANCE_ARGS[*]})"
        echo "[env-debug] python invocation: response_generation.py --task $TASK --config $CONFIG --engine $ENGINE --verbose False ${INSTANCE_ARGS[*]}"

        # Stage 2 — response generation through the MCP tool-loop engine.
        python3 response_generation.py \
            --task "$TASK" \
            --config "$CONFIG" \
            --engine "$ENGINE" \
            --verbose False \
            "${INSTANCE_ARGS[@]}" \
            || { echo "response_generation rc=$? for $TASK/$CONFIG"; OVERALL_RC=1; continue; }

        # Stage 3 — evaluation (engine-agnostic; VAL/PR2 parse the response).
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
if [ "$PROMPT_ARM" = "legacy" ]; then
    OUT_DIR="$EXPT_ROOT/results/planbench/slurm_tools_${MODEL_TAG}_${SLURM_JOB_ID}"
else
    OUT_DIR="$EXPT_ROOT/results/planbench/slurm_tools-${PROMPT_ARM}_${MODEL_TAG}_${SLURM_JOB_ID}"
fi
mkdir -p "$OUT_DIR"
echo
echo "Rsyncing PlanBench results → $OUT_DIR"
rsync -a "$PLANBENCH_ROOT/plan-bench/results/" "$OUT_DIR/results/"
rsync -a "$PLANBENCH_ROOT/plan-bench/responses/" "$OUT_DIR/responses/"
# Carry the tool-call transcript next to the results for content-validation.
[ -f "$PDDL_COPILOT_TOOLLOG" ] && cp "$PDDL_COPILOT_TOOLLOG" "$OUT_DIR/toolcalls.jsonl"

# Manifest: which model/engine/tasks/configs produced this corpus.
cat > "$OUT_DIR/manifest.json" <<EOF
{
  "model": "$MODEL",
  "hf_model": "$HF_MODEL",
  "backend": "$ENGINE_BACKEND",
  "engine": "$ENGINE",
  "prompt_arm": "$PROMPT_ARM",
  "think": "$THINK",
  "reasoning_effort": "$EFFORT",
  "tool_call_parser": "$TOOL_CALL_PARSER",
  "reasoning_parser": "${REASONING_PARSER:-}",
  "hf_revision": "${HF_REVISION:-}",
  "chat_template": "${CHAT_TEMPLATE:-}",
  "tool_call_id_style": "${TOOL_CALL_ID_STYLE:-}",
  "tasks": "$PLANBENCH_TASKS",
  "configs": "$PLANBENCH_CONFIGS",
  "instances": "$PLANBENCH_INSTANCES",
  "marketplace_path": "$MARKETPLACE_PATH",
  "plugins": "$PLANBENCH_PLUGINS",
  "slurm_job_id": "$SLURM_JOB_ID",
  "node": "$SLURM_JOB_NODELIST",
  "vllm_base": "localhost:$PORT/v1",
  "start_time_iso": "$(date -Iseconds)"
}
EOF

echo "End time: $(date)"
echo "Overall rc: $OVERALL_RC"
exit "$OVERALL_RC"
