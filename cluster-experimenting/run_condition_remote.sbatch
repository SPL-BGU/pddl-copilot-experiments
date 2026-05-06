#!/bin/bash
### Runs run_experiment.py for ONE (model, think_mode, condition) cell against
### a REMOTE Ollama server (e.g. on Vast.ai), instead of self-deploying an
### Apptainer Ollama on the compute node like run_condition_rtx.sbatch does.
###
### Why a separate sbatch: leaves the local-Apptainer path (rtx variant)
### untouched as the legacy fallback, while making the remote path obviously
### "different shape" — no GPU directive, no Apptainer/.sif, no VRAM check,
### much smaller --mem. Cells / arrays / cell-array picker / matrix-gate /
### resume / continue-partial / partial / shard semantics are identical.
###
### Pool model: cluster-experimenting/vast/pool.txt holds one
###   "https://host:port # instance=<id>"
### per pre-provisioned Vast box. Each array task picks a slot via
### SLURM_ARRAY_TASK_ID % N. The bearer token (vast/.token) is shared across
### the whole pool. See cluster-experimenting/vast/README.md.
###
### Submit via cluster-experimenting/submit_with_remote.sh — the wrapper
### builds CELLS_LIST, validates pool.txt + .token exist, and submits this
### sbatch with --array=0-(N_CELLS-1).
###
### Required env (set by submit_with_remote.sh):
###   CELLS_LIST   — ^-separated MODEL|THINK|COND triples
###   POOL_FILE    — abs path to pool.txt (defaults to vast/pool.txt)
###   TOKEN_FILE   — abs path to .token (defaults to vast/.token)
###
### Optional env (defaults shown):
###   CONCURRENCY=4              (matches Vast-side OLLAMA_NUM_PARALLEL=4)
###   CHAIN_SAMPLES=100
###
### Resource policy: no --gpus directive (the Vast box does the GPU work).
### --mem=16G is generous for the cluster-side Python + MCP plugin processes.
### --tmp=8G — only a small workdir is needed (no .sif, no model cache).
#SBATCH --partition=main
#SBATCH --job-name=pddl_copilot_remote
#SBATCH --output=cluster-experimenting/logs/%x-%J.out
#SBATCH --mem=16G
#SBATCH --tmp=8G
#SBATCH --time=2-00:00:00

set -eo pipefail

# shellcheck source=lib/defaults.sh
source "$HOME/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh"

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Node IP: $(hostname -i)"
echo "Start time: $(date)"

### Cell-array picker (identical to run_condition_rtx.sbatch) ###
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
if [ -z "${MODELS:-}" ]; then
    : "${MODEL:?Error: export MODELS=\"m1 m2 ...\" or MODEL=... Submit via submit_with_remote.sh}"
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
CONDITIONS="${CONDITIONS:-$PDDL_DEFAULT_SBATCH_CONDITIONS}"
TASKS_ENV_OVERRIDE="${TASKS:-}"

POOL_FILE="${POOL_FILE:-$EXPT_ROOT/cluster-experimenting/vast/pool.txt}"
TOKEN_FILE="${TOKEN_FILE:-$EXPT_ROOT/cluster-experimenting/vast/.token}"

### Pool slot selection ###
# Each entry of pool.txt:  "https://host:port # instance=<id>".
# Empty/comment-only lines are tolerated (mostly to make the file editable
# by hand without breaking parsing).
if [ ! -s "$POOL_FILE" ]; then
    echo "Error: $POOL_FILE empty/missing. Run cluster-experimenting/vast/deploy-ollama.sh first." >&2
    exit 2
fi
mapfile -t _POOL_RAW < "$POOL_FILE"
POOL=()
for line in "${_POOL_RAW[@]}"; do
    # Strip "# instance=..." suffix and surrounding whitespace. `read` with a
    # discard rest-arg cleanly drops both leading whitespace and any trailing
    # tokens, leaving just the URL token.
    read -r url _ <<< "${line%%#*}"
    [ -n "$url" ] && POOL+=("$url")
done
if [ "${#POOL[@]}" -eq 0 ]; then
    echo "Error: no usable URLs parsed from $POOL_FILE" >&2
    exit 2
fi

SLOT_KEY="${SLURM_ARRAY_TASK_ID:-${SLURM_JOBID:-$$}}"
SLOT=$(( SLOT_KEY % ${#POOL[@]} ))
OLLAMA_HOST="${POOL[$SLOT]}"
export OLLAMA_HOST

if [ ! -s "$TOKEN_FILE" ]; then
    echo "Error: $TOKEN_FILE missing. deploy-ollama.sh writes it on first run." >&2
    exit 2
fi
OLLAMA_AUTH_TOKEN="$(cat "$TOKEN_FILE")"
export OLLAMA_AUTH_TOKEN

echo "Pool size: ${#POOL[@]}  slot $SLOT/${#POOL[@]}  host=$OLLAMA_HOST"

### Preflight: don't burn the SLURM job if the box is unreachable ###
# -k tolerates Caddy's self-signed cert (Caddyfile.tmpl uses 'tls internal').
# Token gates real access; the cert just provides transport TLS.
if ! curl -fsSk --max-time 30 \
        -H "Authorization: Bearer $OLLAMA_AUTH_TOKEN" \
        "$OLLAMA_HOST/api/tags" >/dev/null; then
    echo "Error: preflight failed — $OLLAMA_HOST/api/tags unreachable or auth rejected." >&2
    echo "       Run: bash cluster-experimenting/vast/smoke-test.sh \"$OLLAMA_HOST\"" >&2
    exit 3
fi
echo "Preflight OK."

### Activate conda env for run_experiment.py ###
module load anaconda
source activate "$ENV_NAME"

### Workspace on compute-node SSD scratch — only used by run_experiment.py ###
### for tmpfiles, not for model storage (which lives on the Vast box). ###
if [ -n "${SLURM_JOB_USER:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
    SCRATCH_BASE="/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}"
    if mkdir -p "$SCRATCH_BASE" 2>/dev/null; then
        export SLURM_SCRATCH_DIR="$SCRATCH_BASE"
    fi
fi

echo
echo "Models:      $MODELS"
echo "Think modes: $THINK_MODES"
echo "Conditions:  $CONDITIONS"
echo "Marketplace: $MARKETPLACE_PATH"
echo "Ollama host: $OLLAMA_HOST (remote, pool slot $SLOT/${#POOL[@]})"
echo "Concurrency: $CONCURRENCY"
echo

cd "$EXPT_ROOT"
OVERALL_RC=0

### Outer loop: MODELS — single iteration when invoked as a cell-array task.
for MODEL in $MODELS; do
    MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL   started $(date)"
    echo "####################################################################"

    ### Warmup: ensure the model is hot in remote VRAM before timed trials. ###
    ### The Vast deploy script preloads at boot; this is a defensive nudge  ###
    ### in case the box has been idle long enough to evict (won't happen at ###
    ### keep_alive=24h, but cheap and idempotent).                          ###
    echo "Warmup (load $MODEL into remote VRAM with num_ctx=16384)..."
    curl -sSk --max-time 600 "$OLLAMA_HOST/api/chat" \
        -H "Authorization: Bearer $OLLAMA_AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"24h\",\"options\":{\"num_predict\":5,\"num_ctx\":16384}}" \
        >/dev/null

    ### Smoke fast-path — see run_condition_rtx.sbatch for rationale. ###
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
            if [ "$COND" = "no-tools" ] && [ "$THINK_MODE" != "off" ]; then
                echo "Skipping no-tools/think=$THINK_MODE per matrix gating (no-tools reported only for think=off)"
                continue
            fi

            echo
            echo "===================================================================="
            echo "MODEL: $MODEL   THINK: $THINK_MODE   CONDITION: $COND   started $(date)"
            echo "===================================================================="

            CHAINS_ARGS=(--chains --chain-samples "$CHAIN_SAMPLES")
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
                tools_all_minimal)
                    COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
                *)
                    echo "Error: unknown condition '$COND'"; OVERALL_RC=1; continue ;;
            esac

            # Output dir keyed on (model, think, cond) — same shape as the rtx
            # path so aggregate.py / plot.py treat results uniformly. The
            # remote variant writes to the SAME results/slurm_* layout; the
            # only difference vs rtx is which Ollama served the trial. If you
            # want to keep remote results separate for the methodology
            # comparison, set OUT_DIR_PREFIX env.
            OUT_DIR_PREFIX="${OUT_DIR_PREFIX:-slurm}"
            OUT_DIR="${EXPT_ROOT}/results/${OUT_DIR_PREFIX}_${MODEL_TAG}_${THINK_MODE}_${COND}"

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
                --models "$MODEL" \
                --ollama-host "$OLLAMA_HOST" \
                "${CHAINS_ARGS[@]}" \
                --concurrency "$CONCURRENCY" \
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

    echo
    echo "####################################################################"
    echo "# MODEL: $MODEL   finished $(date)"
    echo "####################################################################"
done

echo
echo "End time: $(date)   overall rc=$OVERALL_RC"
exit $OVERALL_RC
