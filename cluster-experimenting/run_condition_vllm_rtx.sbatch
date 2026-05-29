#!/bin/bash
### Runs one (model, think, cond) cell against a self-deployed vLLM
### OpenAI server. Submitted via `submit_with_rtx.sh`; CELLS_LIST is the
### cell-array picker. OUT_DIR is `slurm_vllm_<…>` (prefix retained for
### corpus comparability with prior sweeps). Operator docs + verified
### serve-flag rationale live in cluster-experimenting/README.md
### "Production vLLM sweep".
###
#SBATCH --partition=main
#SBATCH --job-name=pddl_copilot_vllm
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --constraint=rtx_6000
#SBATCH --mem=48G
#SBATCH --tmp=80G
#SBATCH --time=2-00:00:00

# --constraint=rtx_6000 filters out ee-l40s-{01,02}, which carry the
# `l40s` feature but are mislabelled as `gpu:rtx_6000:8` in SLURM's GRES
# table. Their visible VRAM (44.39 GiB vs the real 48 GiB) is 3.6 GiB
# short of what `--enable-prefix-caching` + `gpu_memory_utilization=0.85`
# needs for qwen3.6:27b's KV cache. Sweep 17480288 OOM-failed three 27B
# cells on ee-l40s-02 for exactly this reason. See
# development/INVESTIGATION_vllm_oom_thinkon_20260511.md "Failure mode 1".

set -eo pipefail

# shellcheck source=lib/defaults.sh
source "$HOME/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh"

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Node IP: $(hostname -i)"
echo "Start time: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

### Cell-array picker ###
if [ -n "${CELLS_LIST:-}" ]; then
    IFS='^' read -ra _CELLS <<< "$CELLS_LIST"
    IDX="${SLURM_ARRAY_TASK_ID:-0}"
    SELECTED="${_CELLS[$IDX]:-}"
    if [ -z "$SELECTED" ]; then
        echo "Error: cell index $IDX out of range (0..$((${#_CELLS[@]}-1)))" >&2
        exit 1
    fi
    IFS='|' read -r CELL_MODEL CELL_THINK CELL_COND <<< "$SELECTED"
    # Smoke sentinel: submit_with_rtx.sh sends `@smoke@` as the COND token
    # when invoked with --smoke. Intercept it here so the inner think/cond
    # loop is bypassed in favor of the smoke fastpath below, which
    # delegates think×cond iteration to run_experiment.py --smoke. Without
    # this branch, `@smoke@` propagates to `--conditions @smoke@` and
    # argparse rejects it before any work runs (job 17653267 all 5 cells,
    # 2026-05-19).
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

    # Rename array task at runtime so squeue / sacct show the actual cell.
    if [ -n "${SLURM_JOB_ID:-}" ] && command -v scontrol >/dev/null 2>&1; then
        _MTAG=$(echo "$CELL_MODEL" | tr '/:.' '___')
        _TTAG="$CELL_THINK"
        case "$CELL_COND" in
            no-tools)               _CTAG="notools" ;;
            tools_all_minimal)      _CTAG="tools-all" ;;
            @smoke@)                _CTAG="smoke"; _TTAG="default" ;;
            *)                      _CTAG="$CELL_COND" ;;
        esac
        scontrol update jobid="$SLURM_JOB_ID" \
            JobName="pddl_vllm_${_MTAG}_${_TTAG}_${_CTAG}" 2>/dev/null || true
        unset _MTAG _TTAG _CTAG
    fi
fi

if [ -z "${MODELS:-}" ]; then
    : "${MODEL:?Error: export MODELS=... Submit via submit_with_rtx.sh}"
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

### Workspace on /scratch — with ENOSPC fallback to /tmp ###
# Test the FULL target path (vllm-work/hf-cache) in one mkdir -p so an
# ENOSPC on a deeper level triggers the /tmp fallback. The prior
# `mkdir -p "$SCRATCH_BASE"` then `mkdir -p "$WORK/hf-cache"` split
# returned 0 on a creatable-but-full /scratch (the base dir entry fits;
# the subdirs don't), causing `set -eo pipefail` to bail with exit 1 on
# the second mkdir before the trap could fire. Sweep 17480288 cells
# {6,9} hit this on ise-cpu256-27 at 2 s wall — see
# development/INVESTIGATION_vllm_oom_thinkon_20260511.md "Failure mode 2".
WORK=""
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE/vllm-work/hf-cache" 2>/dev/null; then
        export SLURM_SCRATCH_DIR="$SCRATCH_BASE"
        WORK="$SCRATCH_BASE/vllm-work"
    else
        echo "Note: $SCRATCH_BASE unwritable or out of space, falling back to /tmp"
    fi
fi
if [ -z "$WORK" ]; then
    WORK="/tmp/vllm-${SLURM_JOB_ID:-$$}"
    mkdir -p "$WORK/hf-cache" || { echo "ERROR: cannot create $WORK/hf-cache on /tmp either"; exit 1; }
fi
cd "$WORK"

### Preserve vLLM serve logs on EXIT — the trap below would rm -rf the ###
### per-cell vllm-*.log otherwise (idiom inherited from the retired vLLM smoke sbatch, see CHANGELOG 06f2b4b). ###
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
    # TOOL_CALL_PARSER + REASONING_PARSER + (optionally)
    # MAX_NUM_BATCHED_TOKENS. Unset between iterations so a leftover
    # MM-aware value from a previous model doesn't bleed into a
    # text-only model's serve command.
    unset MAX_NUM_BATCHED_TOKENS
    vllm_lookup "$MODEL" || exit 1
    MAX_NUM_BATCHED_TOKENS_FLAG=""
    [ -n "${MAX_NUM_BATCHED_TOKENS:-}" ] && \
        MAX_NUM_BATCHED_TOKENS_FLAG="--max-num-batched-tokens $MAX_NUM_BATCHED_TOKENS"
    # Build --reasoning-parser flag via the shared helper. Families with
    # no reasoning trace (gemma4, REASONING_PARSER=none) get an empty
    # string so the flag is omitted — passing `--reasoning-parser none`
    # crashes vLLM with `KeyError: Reasoning parser 'none' not found`
    # (verified on array job 17638961 task 17638977, 2026-05-18).
    REASONING_PARSER_FLAG="$(vllm_reasoning_parser_flag)"
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
            $REASONING_PARSER_FLAG \
            --gpu-memory-utilization 0.85 \
            --enable-prefix-caching \
            $MAX_NUM_BATCHED_TOKENS_FLAG \
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

    # VRAM 85% guard. Smokes peaked at 83-84%; a >85% read means KV
    # cache won't fit and continuous batching will back-pressure to
    # single-stream serving.
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

    LLM_BASE_URL="http://localhost:$PORT"
    export LLM_BASE_URL

    echo "Models:      $MODELS  (HF: $HF_MODEL)"
    echo "Think modes: $THINK_MODES"
    echo "Conditions:  $CONDITIONS"
    echo "Marketplace: $MARKETPLACE_PATH"
    echo "Server:      $LLM_BASE_URL"
    echo "Concurrency: $CONCURRENCY"

    ### Smoke fast-path — skip the inner THINK × CONDITIONS loop. The
    ### --smoke flag tells run_experiment.py to iterate think×cond
    ### internally and write to results/smoke/fixed_<sha>_<ts>/<model>/.
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
        STEERED_ARG=()
        if [ "${INCLUDE_NO_TOOLS_STEERED:-0}" = "1" ]; then
            STEERED_ARG=(--include-no-tools-steered)
        fi
        DOMAINS_DIR_ARG=()
        if [ -n "${DOMAINS_DIR:-}" ]; then
            DOMAINS_DIR_ARG=(--domains-dir "$DOMAINS_DIR")
        fi
        echo
        echo "===================================================================="
        echo "MODEL: $MODEL   smoke ($SMOKE_FLAG)   started $(date)"
        echo "===================================================================="
        python3 run_experiment.py \
            --marketplace-path "$MARKETPLACE_PATH" \
            --models "$HF_MODEL" \
            --llm-base-url "$LLM_BASE_URL" \
            --concurrency "$CONCURRENCY" \
            "$SMOKE_FLAG" \
            "${SHARD_ARGS[@]}" \
            "${STEERED_ARG[@]}" \
            "${DOMAINS_DIR_ARG[@]}"
        RC=$?
        echo "===================================================================="
        echo "MODEL: $MODEL   smoke   finished $(date)   rc=$RC"
        echo "===================================================================="
        if [ "$RC" -ne 0 ]; then
            OVERALL_RC=$RC
        fi
        kill "$VLLM_PID" 2>/dev/null || true
        wait "$VLLM_PID" 2>/dev/null || true
        continue
    fi

    for THINK_MODE in $THINK_MODES; do
        THINK_ARG=()
        if [ "$THINK_MODE" != "default" ]; then
            THINK_ARG=(--think "$THINK_MODE")
        fi

        for COND in $CONDITIONS; do
            # The legacy no-tools/think=on gate was lifted 2026-05-12 — see
            # submit_with_rtx.sh + cluster-ops/scripts/status.sh. ISS-018 had
            # already lifted the in-Python abort (PR-2, 2026-04-28) and
            # routed thinking into TaskResult.thinking, so this combination
            # is a valid ablation column.
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
                tools_all_minimal)
                    COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
                *)
                    echo "Error: unknown condition '$COND'"; OVERALL_RC=1; continue ;;
            esac

            # OUT_DIR keyed on (model, think, cond). The `slurm_vllm_`
            # prefix is historical (originally to isolate vLLM corpora from
            # retired Ollama-backend trials.jsonl in the matching
            # `slurm_<model>_<think>_<cond>/` dir); retained for corpus
            # comparability across sweeps.
            # ${RUN_TAG:+_$RUN_TAG} appends `_<tag>` only when RUN_TAG is
            # exported by the wrapper (--run-tag); unset → byte-equivalent
            # to the pre-change OUT_DIR. Used to isolate non-canonical
            # corpus runs (e.g. --domains-dir domains-anon) from canonical
            # results/slurm_vllm_*/ trees.
            OUT_DIR="${EXPT_ROOT}/results/slurm_vllm_${MODEL_TAG}_${THINK_MODE}_${COND}${RUN_TAG:+_$RUN_TAG}"

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

            STEERED_ARG=()
            if [ "${INCLUDE_NO_TOOLS_STEERED:-0}" = "1" ]; then
                STEERED_ARG=(--include-no-tools-steered)
            fi

            DOMAINS_DIR_ARG=()
            if [ -n "${DOMAINS_DIR:-}" ]; then
                DOMAINS_DIR_ARG=(--domains-dir "$DOMAINS_DIR")
            fi

            python3 run_experiment.py \
                --marketplace-path "$MARKETPLACE_PATH" \
                --models "$HF_MODEL" \
                --llm-base-url "$LLM_BASE_URL" \
                --concurrency "$CONCURRENCY" \
                "${THINK_ARG[@]}" \
                "${COND_ARGS[@]}" \
                "${TASKS_ARG[@]}" \
                "${SHARD_ARGS[@]}" \
                "${CONTINUE_ARG[@]}" \
                "${PARTIAL_ARG[@]}" \
                "${STEERED_ARG[@]}" \
                "${DOMAINS_DIR_ARG[@]}" \
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
