#!/bin/bash
### Runs run_experiment.py for one OR MORE models on a SELF-DEPLOYED Ollama
### server running inside an Apptainer container on a single GPU node.
### For each model, loops over all THINK_MODES × CONDITIONS in the same job
### so weights stay resident — no cross-invocation eviction, no shared-server
### contention. With multiple models, models run sequentially on the same GPU
### (Ollama's MAX_LOADED_MODELS=1 evicts the previous model before loading
### the next), sharing the apptainer/serve startup overhead across models.
###
### Default GPU: rtx_6000:1 (48 GB) — fits all paper models except gpt-oss:120b.
### For gpt-oss:120b, override on the sbatch command line:
###   sbatch --gpus=rtx_pro_6000:1 --mem=80G ... run_condition_rtx.sbatch
### submit_with_rtx.sh handles this routing automatically.
###
### Model VRAM fit (weights + KV cache at NUM_PARALLEL=4, ctx=8192):
###   Qwen3.5:0.8B  ~ 3 GB   → fits rtx_6000 (48 GB) easily
###   gpt-oss:20b   ~18 GB   → fits rtx_6000
###   Qwen3.5:27b   ~23 GB   → fits rtx_6000
###   Qwen3.5:35b   ~30 GB   → fits rtx_6000
###   gemma4:31b    ~26 GB   → fits rtx_6000
###   gpt-oss:120b  ~77 GB   → REQUIRES rtx_pro_6000 (96 GB)
### When packing multiple models in one job, ALL listed models must fit on the
### chosen GPU (loaded one at a time). The submit script auto-routes to
### rtx_pro_6000 if any of the requested models is gpt-oss:120b.
###
### Submit via cluster-experimenting/submit_with_rtx.sh <model> [<model>...],
### or directly:
###   sbatch --export=ALL,MODELS="Qwen3.5:0.8B gpt-oss:20b",THINK_MODES="on off" \
###          cluster-experimenting/run_condition_rtx.sbatch
###
### Required env (one of):
###   MODELS       — space-separated Ollama model names (preferred for packing)
###   MODEL        — single Ollama model name (back-compat fallback)
###   THINK_MODES  — space-separated think modes, e.g. "on off" or "default"
###
### Optional env (defaults shown):
###   CONDITIONS   — default = 4 tools conditions (no-tools omitted; rerun
###                  separately when wanted, matches Qwen3.5:0.8B reference set).
###                  Override: CONDITIONS="no-tools" bash submit_with_rtx.sh ...
###   CONCURRENCY=4              (matches self-deploy OLLAMA_NUM_PARALLEL=4)
###   CHAIN_SAMPLES=100
###
### Resource policy (post 2026-04-27 IT request):
###   * Do NOT set --cpus-per-task here. The cluster default cpus-per-gpu
###     handles CPU sizing. Setting cpus-per-task=12 was flagged as depriving
###     other users.
###   * --mem cap: 48 GB on rtx_6000 jobs, 80 GB on rtx_pro_6000 jobs (per
###     IT email 2026-04-27: "Use no more than 80GB RAM for rtx6000 GPUs").
###     Actual host-RAM usage is dominated by node-local /tmp model cache
###     (~26 GB peak for gemma4:31b weights, ~65 GB for gpt-oss:120b),
###     well within these caps.
###
### KV cache safety: OLLAMA_NUM_PARALLEL=4 + num_ctx=8192 (set per-request by
### run_experiment.py) sizes KV pre-allocation to fit alongside any 20-31B
### model in 48 GB. Do NOT raise NUM_PARALLEL without recomputing VRAM —
### probe 2026-04-23 observed NUM_PARALLEL=8 × ctx=40960 allocating 37.8 GB
### for a 0.6B model (pathological). A runtime VRAM guard aborts if usage
### exceeds 85% after each model's warmup.
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_copilot_rtx
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=48G
#SBATCH --time=2-00:00:00

set -eo pipefail

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Node IP: $(hostname -i)"
echo "Start time: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

### Required inputs ###
# MODELS (space-sep) is preferred. MODEL (single) is accepted for back-compat.
if [ -z "${MODELS:-}" ]; then
    : "${MODEL:?Error: export MODELS=\"m1 m2 ...\" or MODEL=... Submit via submit_with_rtx.sh}"
    MODELS="$MODEL"
fi
: "${THINK_MODES:?Error: export THINK_MODES=... (e.g. \"on off\" or \"default\")}"

# 120b requires rtx_pro_6000 (96 GB). The VRAM guard after warmup will catch
# cases where this sbatch is submitted with the default --gpus=rtx_6000 and
# the 48 GB VRAM can't hold 65 GB weights. submit_with_rtx.sh handles the
# routing automatically.

for tm in $THINK_MODES; do
    case "$tm" in
        on|off|default) ;;
        *) echo "Error: invalid THINK_MODE=$tm (must be on|off|default)"; exit 1 ;;
    esac
done

### Defaults ###
ENV_NAME="${ENV_NAME:-pddl_copilot}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"
CHAIN_SAMPLES="${CHAIN_SAMPLES:-100}"
CONCURRENCY="${CONCURRENCY:-4}"
CONDITIONS="${CONDITIONS:-tools_per-task_minimal tools_per-task_guided tools_all_minimal tools_all_guided}"
TASKS_ENV_OVERRIDE="${TASKS:-}"

### Workspace on compute-node local disk ###
WORK=/tmp/rtx-$SLURM_JOBID
mkdir -p "$WORK/models"
cd "$WORK"

SIF=$WORK/ollama.sif
if [ -f $HOME/ollama.sif ]; then
    echo "Using cached .sif from \$HOME/ollama.sif"
    cp $HOME/ollama.sif $SIF
else
    echo "Building ollama.sif from docker://ollama/ollama (first run, ~3 min)"
    apptainer build --nv --force $SIF docker://ollama/ollama 2>&1 | tail -3
    cp $SIF $HOME/ollama.sif
    echo "Cached to \$HOME/ollama.sif for future jobs"
fi

### Start ollama serve (background) with conservative KV settings ###
# Per-job unique port prevents collision when SLURM co-locates two rtx jobs
# on the same node (apptainer defaults to host network namespace, so binding
# 11434 from a second job silently fails and both jobs end up sharing the
# first job's ollama server → MAX_LOADED=1 thrashing between models).
PORT=$(( 11400 + (SLURM_JOBID % 100) ))
# Fallback if chosen port is already in use (collision on mod-100 wraparound)
while ss -Hltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; do
    PORT=$(( PORT + 1 ))
    [ "$PORT" -ge 11600 ] && { echo "Error: no free port in 11400-11599"; exit 4; }
done
echo "Starting ollama serve on localhost:$PORT (NUM_PARALLEL=4, MAX_LOADED=1, CTX_CAP=8192)"
apptainer exec --nv \
    --bind "$WORK/models:/root/.ollama" \
    --writable-tmpfs \
    "$SIF" bash -c "
        export OLLAMA_HOST=0.0.0.0:$PORT
        export OLLAMA_NUM_PARALLEL=4
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE=1h
        export OLLAMA_CONTEXT_LENGTH=8192
        ollama serve
    " > "$WORK/ollama-serve.log" 2>&1 &
SERVE_PID=$!
trap 'echo "Shutting down..."; kill $SERVE_PID 2>/dev/null || true; wait 2>/dev/null || true; cd ~; rm -rf "$WORK"' EXIT

for i in $(seq 1 90); do
    if curl -sf http://localhost:$PORT/ >/dev/null 2>&1; then
        echo "ollama serve up after ${i}s"
        break
    fi
    sleep 1
done

### Activate conda env for run_experiment.py ###
module load anaconda
source activate "$ENV_NAME"

OLLAMA_HOST="http://localhost:$PORT"
export OLLAMA_HOST
# Explicit empty string so --ollama-insecure is NOT set (no TLS on localhost)
unset OLLAMA_INSECURE

echo
echo "Models:      $MODELS"
echo "Think modes: $THINK_MODES"
echo "Conditions:  $CONDITIONS"
echo "Marketplace: $MARKETPLACE_PATH"
echo "Ollama host: $OLLAMA_HOST (self-deployed, $(hostname):$PORT)"
echo "Concurrency: $CONCURRENCY"
echo

cd "$EXPT_ROOT"
OVERALL_RC=0

### Outer loop: MODELS — sequential, share the apptainer/serve startup ###
for MODEL in $MODELS; do
    MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL   started $(date)"
    echo "####################################################################"

    ### Pull target model ###
    echo "Pulling $MODEL..."
    t0=$EPOCHREALTIME
    apptainer exec --nv --bind "$WORK/models:/root/.ollama" --writable-tmpfs "$SIF" \
        bash -c "OLLAMA_HOST=http://localhost:$PORT ollama pull '$MODEL'" 2>&1 | tail -2
    t1=$EPOCHREALTIME
    awk -v m="$MODEL" "BEGIN{printf \"pull %s: %.1fs\n\", m, $t1-$t0}"

    ### Warmup (load into VRAM at ctx=8192) ###
    echo "Warmup (load $MODEL into VRAM with num_ctx=8192)..."
    curl -s --max-time 300 http://localhost:$PORT/api/chat \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"1h\",\"options\":{\"num_predict\":5,\"num_ctx\":8192}}" \
        >/dev/null
    apptainer exec --bind "$WORK/models:/root/.ollama" "$SIF" \
        bash -c "OLLAMA_HOST=http://localhost:$PORT ollama ps" 2>&1

    ### VRAM sanity check: abort if > 85% used (likely KV-cache blowup) ###
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
    VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
    VRAM_PCT=$(( VRAM_USED * 100 / VRAM_TOTAL ))
    echo "VRAM after warmup ($MODEL): ${VRAM_USED}/${VRAM_TOTAL} MiB (${VRAM_PCT}%)"
    if [ "$VRAM_PCT" -gt 85 ]; then
        echo "ERROR: VRAM usage ${VRAM_PCT}% exceeds 85% safety threshold after loading $MODEL."
        echo "       Likely cause: OLLAMA_NUM_PARALLEL or num_ctx too high for this model,"
        echo "       or this model doesn't fit on the allocated GPU."
        echo "       Skipping $MODEL and continuing with the next model in MODELS."
        OVERALL_RC=3
        continue
    fi

    ### Inner loops: THINK_MODES × CONDITIONS for this model ###
    for THINK_MODE in $THINK_MODES; do
        THINK_ARG=()
        if [ "$THINK_MODE" != "default" ]; then
            THINK_ARG=(--think "$THINK_MODE")
        fi

        for COND in $CONDITIONS; do
            # No-tools is reported only for think=off — its only honest task
            # (`solve`) doesn't depend on the reasoning budget, and
            # think=on/default cells aren't part of any planned comparison.
            # See EXPERIMENTS_FLOW.md §5.
            if [ "$COND" = "no-tools" ] && [ "$THINK_MODE" != "off" ]; then
                echo "Skipping no-tools/think=$THINK_MODE per matrix gating (no-tools reported only for think=off)"
                continue
            fi

            echo
            echo "===================================================================="
            echo "MODEL: $MODEL   THINK: $THINK_MODE   CONDITION: $COND   started $(date)"
            echo "===================================================================="

            CHAINS_ARGS=(--chains --chain-samples "$CHAIN_SAMPLES")
            # Per-condition TASKS: no-tools uses the 4 single-task no-tools matrix
            # (solve + validate_*); tools_* uses run_experiment.py's default (all 5).
            # If TASKS env was set explicitly at submit time, that override wins.
            if [ -n "$TASKS_ENV_OVERRIDE" ]; then
                TASKS_ARG=(--tasks $TASKS_ENV_OVERRIDE)
            else
                TASKS_ARG=()
            fi

            case "$COND" in
                no-tools)
                    COND_ARGS=(--conditions no-tools)
                    CHAINS_ARGS=()
                    if [ -z "$TASKS_ENV_OVERRIDE" ]; then
                        TASKS_ARG=(--tasks solve validate_domain validate_problem validate_plan)
                    fi ;;
                tools_per-task_minimal)
                    COND_ARGS=(--conditions tools --tool-filter per-task --prompt-style minimal) ;;
                tools_per-task_guided)
                    COND_ARGS=(--conditions tools --tool-filter per-task --prompt-style guided) ;;
                tools_all_minimal)
                    COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
                tools_all_guided)
                    COND_ARGS=(--conditions tools --tool-filter all --prompt-style guided) ;;
                *)
                    echo "Error: unknown condition '$COND'"; OVERALL_RC=1; continue ;;
            esac

            # OUT_DIR name matches run_condition.sbatch format so aggregate.py /
            # plot.py parse both cis-ollama and rtx self-deploy runs identically.
            # Distinguish runs via the job name (pddl_rtx_* vs pddl_*) and the
            # ollama-host recorded in summary.json.
            OUT_DIR="${EXPT_ROOT}/results/slurm_${MODEL_TAG}_${THINK_MODE}_${COND}_${SLURM_JOBID}"

            python3 run_experiment.py \
                --marketplace-path "$MARKETPLACE_PATH" \
                --models "$MODEL" \
                --ollama-host "$OLLAMA_HOST" \
                "${CHAINS_ARGS[@]}" \
                --concurrency "$CONCURRENCY" \
                "${THINK_ARG[@]}" \
                "${COND_ARGS[@]}" \
                "${TASKS_ARG[@]}" \
                --output-dir "$OUT_DIR"
            RC=$?

            echo "===================================================================="
            echo "MODEL: $MODEL   THINK: $THINK_MODE   CONDITION: $COND   finished $(date)   rc=$RC"
            echo "===================================================================="

            if [ "$RC" -ne 0 ]; then
                OVERALL_RC=$RC
            fi
        done
    done

    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL   finished $(date)"
    echo "####################################################################"
done

echo
echo "End time: $(date)   overall rc=$OVERALL_RC"
exit $OVERALL_RC
