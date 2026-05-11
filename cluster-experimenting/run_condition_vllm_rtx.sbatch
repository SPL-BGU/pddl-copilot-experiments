#!/bin/bash
### vLLM analog of run_condition_rtx.sbatch. Runs run_experiment.py for ONE
### (model, think_mode, condition) cell against a SELF-DEPLOYED vLLM
### OpenAI-API server in an Apptainer container on a single GPU node.
###
### Submitted as part of a SLURM array (one task per cell) via
### `submit_with_rtx.sh --backend vllm`. The cell-array picker maps
### $SLURM_ARRAY_TASK_ID to one cell via the ^-separated CELLS_LIST that
### the wrapper exports. Single-cell submissions skip --array; the picker
### still fires with IDX=0.
###
### Verified vLLM serve command (smokes 17461801 / 17468314 / 17468315,
### 2026-05-10, all exit 0:0). The non-prefix-caching flags below match
### exactly the line printed by vllm's "non-default args" startup log on
### the three successful smokes:
###
###   python3 -m vllm.entrypoints.openai.api_server \
###       --host 0.0.0.0 --port <PORT> --model <HF_MODEL> \
###       --max-model-len 16384 --enable-auto-tool-choice \
###       --tool-call-parser qwen3_xml --reasoning-parser qwen3 \
###       --gpu-memory-utilization 0.85
###
### `--enable-prefix-caching` is added explicitly: vLLM V1 (default in
### vllm-openai:latest) already enables APC by default and therefore omits
### it from "non-default args", but stating it pins the behavior against
### a future image refresh and documents that the sweep relies on it for
### the shared {domain} prefix in solve/validate/simulate templates.
###
### Scope (2026-05-11): vLLM in production for qwen3.6:27b + Qwen3.5:0.8B
### only. gemma4:31b + qwen3.6:35b stay on Ollama (resource-contention
### split — see CHANGELOG 2026-05-11). The inline lookup table below has
### two entries; add more when those models move over.
###
### OUT_DIR: results/slurm_vllm_<canonical_tag>_<think>_<cond>/. The
### `slurm_vllm_` prefix isolates vLLM corpora from prior Ollama
### trials.jsonl. The 10-tuple resume key in pddl_eval/runner.py:424
### includes the `model` field as a literal string, so commingling
### Ollama (model="qwen3.6:27b") and vLLM (model="cyankiwi/...") trials
### in one trials.jsonl would silently re-run every cell from zero.
### Separate prefix is the methodology-correct disambiguator.
###
### Resource policy:
###   * GPU: rtx_6000:1 (48 GB, smoke-verified — 27B peaks 83% VRAM,
###     0.8B comfortably below). The wrapper's --gpu-type escape hatch
###     still routes to rtx_pro_6000:1 + --mem=80G if needed.
###   * --mem=48G to match rtx_6000.
###   * --tmp=80G — HF cache for the 27B AWQ snapshot (~17 GB) + vllm.sif
###     (~5 GB) + headroom.
###   * No --cpus-per-task per IT request 2026-04-27.
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_copilot_vllm
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=48G
#SBATCH --tmp=80G
#SBATCH --time=2-00:00:00

set -eo pipefail

# shellcheck source=lib/defaults.sh
source "$HOME/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh"

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Node IP: $(hostname -i)"
echo "Start time: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

### Cell-array picker (mirrors run_condition_rtx.sbatch) ###
if [ -n "${CELLS_LIST:-}" ]; then
    IFS='^' read -ra _CELLS <<< "$CELLS_LIST"
    IDX="${SLURM_ARRAY_TASK_ID:-0}"
    SELECTED="${_CELLS[$IDX]:-}"
    if [ -z "$SELECTED" ]; then
        echo "Error: cell index $IDX out of range (0..$((${#_CELLS[@]}-1)))" >&2
        exit 1
    fi
    IFS='|' read -r CELL_MODEL CELL_THINK CELL_COND <<< "$SELECTED"
    MODELS="$CELL_MODEL"
    THINK_MODES="$CELL_THINK"
    CONDITIONS="$CELL_COND"
    echo "Cell-array task: IDX=$IDX  MODEL=$CELL_MODEL  THINK=$CELL_THINK  COND=$CELL_COND"

    # Rename array task at runtime so squeue / sacct show the actual cell.
    if [ -n "${SLURM_JOB_ID:-}" ] && command -v scontrol >/dev/null 2>&1; then
        _MTAG=$(echo "$CELL_MODEL" | tr '/:.' '___')
        _TTAG="$CELL_THINK"
        case "$CELL_COND" in
            no-tools)               _CTAG="notools" ;;
            tools_per-task_minimal) _CTAG="tools-pt" ;;
            tools_all_minimal)      _CTAG="tools-all" ;;
            *)                      _CTAG="$CELL_COND" ;;
        esac
        scontrol update jobid="$SLURM_JOB_ID" \
            JobName="pddl_vllm_${_MTAG}_${_TTAG}_${_CTAG}" 2>/dev/null || true
        unset _MTAG _TTAG _CTAG
    fi
fi

if [ -z "${MODELS:-}" ]; then
    : "${MODEL:?Error: export MODELS=... Submit via submit_with_rtx.sh --backend vllm}"
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
CONCURRENCY="${CONCURRENCY:-4}"
CONDITIONS="${CONDITIONS:-$PDDL_DEFAULT_SBATCH_CONDITIONS}"
TASKS_ENV_OVERRIDE="${TASKS:-}"

### Workspace on /scratch ###
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE" 2>/dev/null; then
        export SLURM_SCRATCH_DIR="$SCRATCH_BASE"
        WORK="$SCRATCH_BASE/vllm-work"
    else
        echo "Note: $SCRATCH_BASE not writable, falling back to /tmp"
        WORK="/tmp/vllm-${SLURM_JOB_ID}"
    fi
else
    WORK="/tmp/vllm-${SLURM_JOB_ID:-$$}"
fi
mkdir -p "$WORK/hf-cache"
cd "$WORK"

### Preserve vLLM serve logs on EXIT — the trap below would rm -rf the ###
### per-cell vllm-*.log otherwise (lifted from run_smoke_vllm_vs_ollama.sbatch). ###
preserve_serve_logs() {
    local logs_dir="$EXPT_ROOT/cluster-experimenting/logs"
    [ -d "$WORK" ] || return 0
    for f in "$WORK"/vllm-*.log; do
        [ -f "$f" ] || continue
        cp -a "$f" "$logs_dir/${SLURM_JOBID:-local}-$(basename "$f")" 2>/dev/null || true
    done
}

SIF_VLLM="$WORK/vllm.sif"
if [ -f "$HOME/vllm.sif" ]; then
    echo "Using cached vllm.sif from \$HOME/vllm.sif"
    cp "$HOME/vllm.sif" "$SIF_VLLM"
else
    echo "Building vllm.sif from docker://vllm/vllm-openai:latest (first run, ~5 min)"
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

module load anaconda
source activate "$ENV_NAME"

cd "$EXPT_ROOT"
OVERALL_RC=0

for MODEL in $MODELS; do
    MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

    # vllm_lookup is sourced from lib/defaults.sh; exports HF_MODEL +
    # TOOL_CALL_PARSER + REASONING_PARSER. Unverified models bail before
    # the SIF is staged.
    vllm_lookup "$MODEL" || exit 1
    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL  (HF: $HF_MODEL)   started $(date)"
    echo "####################################################################"

    PORT="$(free_port $(( 11500 + (${SLURM_JOBID:-0} % 100) )))"
    SERVE_LOG="$WORK/vllm-${MODEL_TAG}.log"

    echo "Starting vLLM on localhost:$PORT serving $HF_MODEL"
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
            > "$SERVE_LOG" 2>&1 &
    VLLM_PID=$!
    trap 'echo "Shutting down..."; kill $VLLM_PID 2>/dev/null || true; preserve_serve_logs; wait 2>/dev/null || true; cd ~; rm -rf "$WORK"' EXIT

    # vLLM cold-load on 35B took ~9 min (HF download + NFS shards). 27B
    # was ~7 min cold, ~3 min warm. 20-min ceiling matches the smoke.
    ready=0
    for i in $(seq 1 600); do
        if curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
            echo "vllm ready ($((i*2))s)"; ready=1; break
        fi
        if ! kill -0 "$VLLM_PID" 2>/dev/null; then
            echo "vLLM died during startup; tail of $SERVE_LOG:"
            tail -50 "$SERVE_LOG"
            OVERALL_RC=2; break
        fi
        sleep 2
    done
    if [ "$ready" -ne 1 ]; then
        echo "vLLM did not become ready within 20 min; tail of $SERVE_LOG:"
        tail -50 "$SERVE_LOG"
        kill "$VLLM_PID" 2>/dev/null || true
        OVERALL_RC=3
        continue
    fi

    # VRAM 85% guard (matches Ollama path). Smokes peaked at 83-84%; a
    # >85% read means KV cache won't fit and continuous batching will
    # back-pressure to single-stream serving.
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
    VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
    VRAM_PCT=$(( VRAM_USED * 100 / VRAM_TOTAL ))
    echo "VRAM after vLLM load ($MODEL): ${VRAM_USED}/${VRAM_TOTAL} MiB (${VRAM_PCT}%)"
    if [ "$VRAM_PCT" -gt 85 ]; then
        echo "ERROR: VRAM ${VRAM_PCT}% exceeds 85% after loading $MODEL — skipping."
        kill "$VLLM_PID" 2>/dev/null || true
        OVERALL_RC=3
        continue
    fi

    OLLAMA_HOST="http://localhost:$PORT"
    export OLLAMA_HOST

    echo "Backend:     vllm"
    echo "Models:      $MODELS  (HF: $HF_MODEL)"
    echo "Think modes: $THINK_MODES"
    echo "Conditions:  $CONDITIONS"
    echo "Marketplace: $MARKETPLACE_PATH"
    echo "Server:      $OLLAMA_HOST"
    echo "Concurrency: $CONCURRENCY"

    for THINK_MODE in $THINK_MODES; do
        THINK_ARG=()
        if [ "$THINK_MODE" != "default" ]; then
            THINK_ARG=(--think "$THINK_MODE")
        fi

        for COND in $CONDITIONS; do
            if [ "$COND" = "no-tools" ] && [ "$THINK_MODE" != "off" ]; then
                echo "Skipping no-tools/think=$THINK_MODE per matrix gating"
                continue
            fi

            echo
            echo "===================================================================="
            echo "MODEL: $MODEL   THINK: $THINK_MODE   CONDITION: $COND   started $(date)"
            echo "===================================================================="

            if [ -n "$TASKS_ENV_OVERRIDE" ]; then
                TASKS_ARG=(--tasks $TASKS_ENV_OVERRIDE)
            else
                TASKS_ARG=()
            fi

            case "$COND" in
                no-tools)
                    COND_ARGS=(--conditions no-tools) ;;
                tools_per-task_minimal)
                    COND_ARGS=(--conditions tools --tool-filter per-task --prompt-style minimal) ;;
                tools_all_minimal)
                    COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
                *)
                    echo "Error: unknown condition '$COND'"; OVERALL_RC=1; continue ;;
            esac

            # OUT_DIR keyed on (model, think, cond) with `slurm_vllm_` prefix
            # — isolates vLLM corpora from any prior Ollama trials.jsonl in
            # the matching `slurm_<model>_<think>_<cond>/` dir. See header
            # comment for rationale.
            OUT_DIR="${EXPT_ROOT}/results/slurm_vllm_${MODEL_TAG}_${THINK_MODE}_${COND}"

            SHARD_ARGS=()
            if [ -n "${SHARD:-}" ]; then
                SHARD_ARGS=(--shard "$SHARD")
            fi

            CONTINUE_ARG=()
            if [ -n "${CONTINUE_PARTIAL:-}" ] && [ ! -s "$OUT_DIR/trials.jsonl" ]; then
                CONTINUE_ARG=(--continue-partial "$CONTINUE_PARTIAL")
            fi

            PARTIAL_ARG=()
            if [ -n "${PARTIAL_K:-}" ]; then
                PARTIAL_ARG=(--partial "$PARTIAL_K")
            fi

            python3 run_experiment.py \
                --marketplace-path "$MARKETPLACE_PATH" \
                --models "$HF_MODEL" \
                --ollama-host "$OLLAMA_HOST" \
                --concurrency "$CONCURRENCY" \
                --inference-backend vllm \
                "${THINK_ARG[@]}" \
                "${COND_ARGS[@]}" \
                "${TASKS_ARG[@]}" \
                "${SHARD_ARGS[@]}" \
                "${CONTINUE_ARG[@]}" \
                "${PARTIAL_ARG[@]}" \
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

    kill "$VLLM_PID" 2>/dev/null || true
    wait "$VLLM_PID" 2>/dev/null || true

    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL   finished $(date)"
    echo "####################################################################"
done

echo
echo "End time: $(date)   overall rc=$OVERALL_RC"
exit $OVERALL_RC
