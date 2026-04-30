#!/bin/bash
### Runs run_experiment.py for ONE (model, think_mode, condition) cell on a
### SELF-DEPLOYED Ollama server running inside an Apptainer container on a
### single GPU node. Submitted as part of a SLURM array (one task per cell)
### via cluster-experimenting/submit_with_rtx.sh; the wrapper builds the
### CELLS_LIST and the cell-array picker block below maps SLURM_ARRAY_TASK_ID
### to one cell. Single-cell submissions skip --array; the picker still fires
### with IDX=0.
###
### Default GPU: rtx_pro_6000:1 (96 GB) — single, hard-pinned class so peak
### VRAM and host RAM are constant across the active sweep. Each cell holds
### exactly one model under MAX_LOADED_MODELS=1; the largest active model
### (gemma4:31b ~26 GB) fits in 96 GB with ample KV cache headroom. Override
### with --gpu-type rtx_6000 (and --mem=48G) only as an emergency escape.
###
### Model VRAM fit (weights + KV cache at NUM_PARALLEL=4, ctx=16384):
###   Qwen3.5:0.8B        ~ 3 GB   → fits rtx_pro_6000 (96 GB)
###   qwen3.6:27b         ~17 GB   → fits rtx_pro_6000 (dense 27.8B Q4_K_M)
###   qwen3.6:35b         ~24 GB   → fits rtx_pro_6000 (35B-A3B MoE)
###   gemma4:31b          ~26 GB   → fits rtx_pro_6000 (peak)
### Roster history (CHANGELOG): 2026-04-29 Qwen3.5:27b/35b → qwen3.6
### successors, gpt-oss:20b → nemotron-3-nano:30b. 2026-04-30 dropped
### nemotron after smoke 17274424 confirmed Hermes XML parse failures
### independent of num_predict.
###
### Submit via cluster-experimenting/submit_with_rtx.sh <model> [<model>...],
### or directly (legacy non-array path with old-style MODELS env):
###   sbatch --export=ALL,MODELS="Qwen3.5:0.8B",THINK_MODES="on off" \
###          cluster-experimenting/run_condition_rtx.sbatch
###
### Required env (one of):
###   CELLS_LIST   — ^-separated MODEL|THINK|COND triples (set by submit_with_rtx.sh)
###   MODELS       — space-separated Ollama model names (legacy direct-sbatch)
###   MODEL        — single Ollama model name (back-compat fallback)
###   THINK_MODES  — space-separated think modes, e.g. "on off" or "default"
###
### Optional env (defaults shown):
###   CONDITIONS   — default = 2 active tools conditions (tools_per-task_minimal
###                  + tools_all_minimal). When CELLS_LIST is set this is
###                  overridden by the cell-array picker. The retired
###                  *_guided variants are no longer in the default.
###   CONCURRENCY=4              (matches self-deploy OLLAMA_NUM_PARALLEL=4)
###   CHAIN_SAMPLES=100
###
### Resource policy (post 2026-04-27 IT request):
###   * Do NOT set --cpus-per-task here. The cluster default cpus-per-gpu
###     handles CPU sizing. Setting cpus-per-task=12 was flagged as depriving
###     other users.
###   * --mem=80G on rtx_pro_6000 (the default). Override to --mem=48G when
###     submit_with_rtx.sh is invoked with `--gpu-type rtx_6000`.
###     Actual host-RAM usage is dominated by node-local /tmp model cache
###     (~24 GB peak for qwen3.6:35b A3B weights), well within either cap.
###
### KV cache safety: OLLAMA_NUM_PARALLEL=4 + num_ctx=16384 (single-task tools
### + think=off no-tools cells), num_ctx_thinking=16384 (no-tools+think_on
### cells, held equal to num_ctx for tools/no-tools fairness in the "tools
### save tokens" headline), num_ctx_chain=16384 (chain runs, tools-only per
### ISS-018; held equal to num_ctx because chain prompts accumulate history
### -- the single-task think_overflow envelope tightens at chain step level
### rather than loosens) — all set per-request by run_experiment.py. The
### single-task ctx values were raised from 8192/12288 to 16384 on
### 2026-04-29 after qwen3.6:27b / nemotron-3-nano:30b smokes showed
### think_overflow at 12288 on validate_problem/validate_plan (nemotron
### was later dropped 2026-04-30; the ctx evidence still applies to the
### remaining roster via qwen3.6:27b); chain ctx
### was raised 12288 → 16384 in the same-day follow-up. Do NOT raise NUM_PARALLEL
### without recomputing VRAM — probe 2026-04-23 observed NUM_PARALLEL=8 ×
### ctx=40960 allocating 37.8 GB for a 0.6B model (pathological). The
### 16384-ctx single-task budget approximately doubles per-call KV vs the
### prior 8192 baseline; the 80 GB rtx_pro_6000 cap should still hold for
### the active pack but post-mortem MaxRSS / nvidia-smi peak after the
### first sweep on raised ctx and right-size --mem if needed.
### A runtime VRAM guard aborts if usage exceeds 85% after each model's warmup.
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_copilot_rtx
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_pro_6000:1
#SBATCH --mem=80G
#SBATCH --tmp=50G
#SBATCH --time=2-00:00:00

set -eo pipefail

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Node IP: $(hostname -i)"
echo "Start time: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

### Cell-array picker ###
# When invoked via submit_with_rtx.sh (the default path post-2026-04-30),
# CELLS_LIST is exported as a ^-separated list of "MODEL|THINK|COND" triples.
# Each array task picks its cell by $SLURM_ARRAY_TASK_ID (defaults to 0 for
# single-cell submissions where --array isn't set).
#
# Legacy direct-sbatch invocations (with old-style MODELS/THINK_MODES env)
# still work — the picker only fires when CELLS_LIST is set.
if [ -n "${CELLS_LIST:-}" ]; then
    IFS='^' read -ra _CELLS <<< "$CELLS_LIST"
    IDX="${SLURM_ARRAY_TASK_ID:-0}"
    SELECTED="${_CELLS[$IDX]:-}"
    if [ -z "$SELECTED" ]; then
        echo "Error: cell index $IDX out of range (0..$((${#_CELLS[@]}-1)))" >&2
        exit 1
    fi
    IFS='|' read -r CELL_MODEL CELL_THINK CELL_COND <<< "$SELECTED"
    if [ "$CELL_COND" = "@smoke@" ]; then
        SMOKE="${SMOKE:-1}"
        MODELS="$CELL_MODEL"
        THINK_MODES="default"
    else
        MODELS="$CELL_MODEL"
        THINK_MODES="$CELL_THINK"
        CONDITIONS="$CELL_COND"
    fi
    echo "Cell-array task: IDX=$IDX  MODEL=$CELL_MODEL  THINK=$CELL_THINK  COND=$CELL_COND"

    # Rename this array task at runtime so `squeue` / `sacct` show the actual
    # (model, think, cond) cell instead of the static submit-time pack name
    # (e.g. `pddl_rtx_pack4_Qwen3_5_0_8B`). Output filename %x-%J.out was
    # already resolved at job-start using the submit-time name, so logs keep
    # the original prefix — only live listings change.
    if [ -n "${SLURM_JOB_ID:-}" ] && command -v scontrol >/dev/null 2>&1; then
        _MTAG=$(echo "$CELL_MODEL" | tr '/:.' '___')
        _TTAG="$CELL_THINK"
        case "$CELL_COND" in
            no-tools)               _CTAG="notools" ;;
            tools_per-task_minimal) _CTAG="tools-pt" ;;
            tools_all_minimal)      _CTAG="tools-all" ;;
            @smoke@)                _CTAG="smoke"; _TTAG="default" ;;
            *)                      _CTAG="$CELL_COND" ;;
        esac
        scontrol update jobid="$SLURM_JOB_ID" \
            JobName="pddl_${_MTAG}_${_TTAG}_${_CTAG}" 2>/dev/null || true
        unset _MTAG _TTAG _CTAG
    fi
fi

### Required inputs ###
# MODELS (space-sep) is preferred. MODEL (single) is accepted for back-compat.
if [ -z "${MODELS:-}" ]; then
    : "${MODEL:?Error: export MODELS=\"m1 m2 ...\" or MODEL=... Submit via submit_with_rtx.sh}"
    MODELS="$MODEL"
fi
: "${THINK_MODES:?Error: export THINK_MODES=... (e.g. \"on off\" or \"default\")}"

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
CONDITIONS="${CONDITIONS:-tools_per-task_minimal tools_all_minimal}"
TASKS_ENV_OVERRIDE="${TASKS:-}"

### Workspace on compute-node SSD scratch (Mar-26 guide §"SSD Drive") ###
# --tmp=50G reserves space on /scratch/$USER/$JOBID. We construct and export
# SLURM_SCRATCH_DIR per the guide. Falls back to /tmp/rtx-$JOBID if /scratch
# isn't writable on this node-type (functionally similar — node-local OS disk).
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE" 2>/dev/null; then
        export SLURM_SCRATCH_DIR="$SCRATCH_BASE"
        WORK="$SCRATCH_BASE/rtx-work"
    else
        echo "Note: $SCRATCH_BASE not writable, falling back to /tmp"
        WORK="/tmp/rtx-${SLURM_JOB_ID}"
    fi
else
    WORK="/tmp/rtx-${SLURM_JOB_ID:-$$}"
fi
mkdir -p "$WORK/models"
cd "$WORK"

SIF=$WORK/ollama.sif
if [ -f $HOME/ollama.sif ]; then
    echo "Using cached .sif from \$HOME/ollama.sif"
    cp $HOME/ollama.sif $SIF
else
    echo "Building ollama.sif from docker://ollama/ollama (first run, ~3 min)"
    apptainer build --force $SIF docker://ollama/ollama 2>&1 | tail -3
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
echo "Starting ollama serve on localhost:$PORT (NUM_PARALLEL=4, MAX_LOADED=1, CTX_DEFAULT=16384)"
apptainer exec --nv \
    --bind "$WORK/models:/root/.ollama" \
    --writable-tmpfs \
    "$SIF" bash -c "
        export OLLAMA_HOST=0.0.0.0:$PORT
        export OLLAMA_NUM_PARALLEL=4
        export OLLAMA_MAX_LOADED_MODELS=1
        export OLLAMA_KEEP_ALIVE=1h
        export OLLAMA_CONTEXT_LENGTH=16384
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

### Outer loop: MODELS — single iteration when invoked as a cell-array task
### (CELLS_LIST sets MODELS to one model). Multi-iteration only on legacy
### direct-sbatch invocations with old-style MODELS env.
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

    ### Warmup (load into VRAM at ctx=16384 — matches the per-request num_ctx ###
    ### that single-task cells use post 2026-04-29 cap bump, so the model is  ###
    ### resident at the run's ctx and the first real request doesn't reload). ###
    echo "Warmup (load $MODEL into VRAM with num_ctx=16384)..."
    curl -s --max-time 300 http://localhost:$PORT/api/chat \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"1h\",\"options\":{\"num_predict\":5,\"num_ctx\":16384}}" \
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

    ### Smoke fast-path — skip the THINK × CONDITIONS loop. The smoke
    ### wrapper inside run_experiment.py iterates both think modes
    ### internally and writes to results/smoke[_shuffle]_<sha>_<ts>/.
    if [ "${SMOKE:-0}" = "1" ] || [ "${SMOKE_SHUFFLE:-0}" = "1" ]; then
        if [ "${SMOKE_SHUFFLE:-0}" = "1" ]; then
            SMOKE_FLAG="--smoke-shuffle"
        else
            SMOKE_FLAG="--smoke"
        fi
        SHARD_ARGS=()
        if [ -n "${SHARD:-}" ]; then
            SHARD_ARGS=(--shard "$SHARD")
        fi
        echo
        echo "===================================================================="
        echo "MODEL: $MODEL   smoke ($SMOKE_FLAG)   started $(date)"
        echo "===================================================================="
        python3 run_experiment.py \
            --marketplace-path "$MARKETPLACE_PATH" \
            --models "$MODEL" \
            --ollama-host "$OLLAMA_HOST" \
            --concurrency "$CONCURRENCY" \
            "$SMOKE_FLAG" \
            "${SHARD_ARGS[@]}"
        RC=$?
        echo "===================================================================="
        echo "MODEL: $MODEL   smoke   finished $(date)   rc=$RC"
        echo "===================================================================="
        if [ "$RC" -ne 0 ]; then
            OVERALL_RC=$RC
        fi
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
                # tools_per-task_guided)  # DISABLED 2026-04-27 — see run_experiment.py PROMPT_STYLE_CHOICES
                #     COND_ARGS=(--conditions tools --tool-filter per-task --prompt-style guided) ;;
                tools_all_minimal)
                    COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
                # tools_all_guided)  # DISABLED 2026-04-27 — see run_experiment.py PROMPT_STYLE_CHOICES
                #     COND_ARGS=(--conditions tools --tool-filter all --prompt-style guided) ;;
                *)
                    echo "Error: unknown condition '$COND'"; OVERALL_RC=1; continue ;;
            esac

            # OUT_DIR name kept stable so aggregate.py / plot.py can read both
            # historical cis-ollama runs and current rtx self-deploy runs
            # identically. The cis path was retired 2026-04-27.
            OUT_DIR="${EXPT_ROOT}/results/slurm_${MODEL_TAG}_${THINK_MODE}_${COND}_${SLURM_JOBID}"

            SHARD_ARGS=()
            if [ -n "${SHARD:-}" ]; then
                SHARD_ARGS=(--shard "$SHARD")
            fi

            python3 run_experiment.py \
                --marketplace-path "$MARKETPLACE_PATH" \
                --models "$MODEL" \
                --ollama-host "$OLLAMA_HOST" \
                "${CHAINS_ARGS[@]}" \
                --concurrency "$CONCURRENCY" \
                "${THINK_ARG[@]}" \
                "${COND_ARGS[@]}" \
                "${TASKS_ARG[@]}" \
                "${SHARD_ARGS[@]}" \
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
