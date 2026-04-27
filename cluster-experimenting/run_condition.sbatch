#!/bin/bash
### Runs run_experiment.py for ONE (MODEL, THINK_MODE) pair, looping over
### all 5 conditions sequentially in a single SLURM job so the shared
### cis-ollama server sees the same model's requests back-to-back (avoids
### cross-model weight eviction).
###
### Submit via cluster-experimenting/submit_all.sh (fan-out across models ×
### think modes, staged by wave with --dependency=afterok), or directly:
###   sbatch --export=ALL,MODEL=gpt-oss:20b,THINK_MODE=off \
###          cluster-experimenting/run_condition.sbatch
###
### Required env (set via --export=ALL,MODEL=...,THINK_MODE=...):
###   MODEL       — Ollama model name (e.g. Qwen3.5:0.8B, gpt-oss:20b)
###   THINK_MODE  — one of: on | off | default
###                 'default' omits the think kwarg (model's native setting).
###                 Gemma4 has no thinking concept → use 'default' only.
###
### Optional env (defaults shown):
###   CONDITIONS  — space-separated list of condition labels. Default = 3
###                 active conditions; the two `*_guided` variants were
###                 retired 2026-04-27 (see run_experiment.py
###                 PROMPT_STYLE_CHOICES) but are still recognised by the
###                 case statement below if explicitly listed.
###                   no-tools
###                   tools_per-task_minimal
###                   tools_per-task_guided   # DISABLED — retained for back-compat
###                   tools_all_minimal
###                   tools_all_guided        # DISABLED — retained for back-compat
###   ENV_NAME=pddl_copilot
###   EXPT_ROOT=$HOME/pddl-copilot-experiments
###   PDDL_MARKETPLACE_PATH=$HOME/pddl-copilot
###   OLLAMA_HOST=https://cis-ollama.auth.ad.bgu.ac.il
###   OLLAMA_INSECURE=1                 (empty string disables)
###   CHAIN_SAMPLES=100                 (paper-aligned; paper uses 100/100/100/50
###                                      per chain length, we use 100 flat →
###                                      2× oversample at n=5, harmless)
###   CONCURRENCY=2                     (saturates cis-ollama's measured
###                                      OLLAMA_NUM_PARALLEL=4 exactly when
###                                      paired with 2 parallel jobs per wave;
###                                      raising would queue half the requests
###                                      and starve other users on the shared
###                                      server. Server probe: CHANGELOG
###                                      2026-04-21 entry.)
###
### sbatch config parameters must start with #SBATCH and precede any other command.
#SBATCH --partition main
#SBATCH --time 3-00:00:00
#SBATCH --job-name pddl_copilot
#SBATCH --output cluster-experimenting/logs/%x-%J.out
#SBATCH --gpus=0
#SBATCH --tasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --constraint=cpu

### Job info ###
echo "SLURM_JOBID=$SLURM_JOBID"
echo "SLURM_JOB_NODELIST=$SLURM_JOB_NODELIST"
echo "Start time: $(date)"

### Required inputs ###
: "${MODEL:?Error: export MODEL=... (e.g. Qwen3.5:0.8B). Submit via submit_all.sh or pass --export=ALL,MODEL=...,THINK_MODE=...}"
: "${THINK_MODE:?Error: export THINK_MODE=... (one of: on | off | default)}"

case "$THINK_MODE" in
    on|off|default) ;;
    *) echo "Error: invalid THINK_MODE=$THINK_MODE (must be on|off|default)"; exit 1 ;;
esac

### Defaults ###
ENV_NAME="${ENV_NAME:-pddl_copilot}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"
OLLAMA_HOST="${OLLAMA_HOST:-https://cis-ollama.auth.ad.bgu.ac.il}"
OLLAMA_INSECURE="${OLLAMA_INSECURE:-1}"
CHAIN_SAMPLES="${CHAIN_SAMPLES:-100}"
CONCURRENCY="${CONCURRENCY:-2}"
# `tools_*_guided` retired 2026-04-27 (see run_experiment.py
# PROMPT_STYLE_CHOICES). Case branches kept below as code documentation.
CONDITIONS="${CONDITIONS:-no-tools tools_per-task_minimal tools_all_minimal}"

export OLLAMA_HOST OLLAMA_INSECURE

### Activate conda env (anaconda pre-installed on BGU cluster) ###
module load anaconda
source activate "$ENV_NAME"

### Conditional --ollama-insecure (for BGU's self-signed cert) ###
INSECURE_ARG=()
if [ -n "$OLLAMA_INSECURE" ]; then
    INSECURE_ARG=(--ollama-insecure)
fi

### Conditional --think flag (omit when THINK_MODE=default to preserve model native) ###
THINK_ARG=()
if [ "$THINK_MODE" != "default" ]; then
    THINK_ARG=(--think "$THINK_MODE")
fi

MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

echo "Model:       $MODEL"
echo "Think mode:  $THINK_MODE"
echo "Conditions:  $CONDITIONS"
echo "Marketplace: $MARKETPLACE_PATH"
echo "Ollama host: $OLLAMA_HOST  (insecure=${OLLAMA_INSECURE:-0})"
echo "Chains:      tools-conditions only, --chain-samples $CHAIN_SAMPLES"
echo "Concurrency: $CONCURRENCY"

cd "$EXPT_ROOT"

### Sanity: remote Ollama must be reachable before we burn job time ###
if ! curl ${OLLAMA_INSECURE:+-k} -sf --max-time 10 "${OLLAMA_HOST}/api/tags" > /dev/null; then
    echo "Error: cannot reach ${OLLAMA_HOST}/api/tags from compute node."
    echo "  - Check BGU VPN status from login node."
    echo "  - Set OLLAMA_INSECURE='' if the cert chain is now trusted."
    exit 2
fi

### Loop over conditions sequentially. Each invocation is a fresh Python
### process so MCP subprocesses are torn down between conditions; that's
### cheap (~1-2s) and isolates any per-condition state. Within an
### invocation, run_experiment.py uses its async Semaphore to issue
### --concurrency chat requests in flight, all against the same model →
### server keeps weights resident, no eviction.
OVERALL_RC=0
for COND in $CONDITIONS; do
    # No-tools is reported only for think=off — its only honest task (`solve`)
    # doesn't depend on the reasoning budget, and think=on/default cells
    # aren't part of any planned comparison. See EXPERIMENTS_FLOW.md §5.
    if [ "$COND" = "no-tools" ] && [ "$THINK_MODE" != "off" ]; then
        echo "Skipping no-tools/think=$THINK_MODE per matrix gating (no-tools reported only for think=off)"
        continue
    fi

    echo ""
    echo "===================================================================="
    echo "CONDITION: $COND   (model=$MODEL, think=$THINK_MODE)   started $(date)"
    echo "===================================================================="

    # Chain phase is only meaningful in tools conditions. In no-tools, the
    # LLM has no planner/validator access to propagate intermediate artifacts
    # between chain steps, so chain samples collapse to N independent
    # single-task attempts — signal already captured by the single-task phase.
    CHAINS_ARGS=(--chains --chain-samples "$CHAIN_SAMPLES")
    case "$COND" in
        no-tools)
            COND_ARGS=(--conditions no-tools)
            CHAINS_ARGS=() ;;
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

    OUT_DIR="${EXPT_ROOT}/results/slurm_${MODEL_TAG}_${THINK_MODE}_${COND}_${SLURM_JOBID}"

    python3 run_experiment.py \
        --marketplace-path "$MARKETPLACE_PATH" \
        --models "$MODEL" \
        --ollama-host "$OLLAMA_HOST" \
        "${INSECURE_ARG[@]}" \
        "${CHAINS_ARGS[@]}" \
        --concurrency "$CONCURRENCY" \
        "${THINK_ARG[@]}" \
        "${COND_ARGS[@]}" \
        --output-dir "$OUT_DIR"
    RC=$?

    echo "===================================================================="
    echo "CONDITION: $COND   finished $(date)   rc=$RC"
    echo "===================================================================="

    if [ "$RC" -ne 0 ]; then
        OVERALL_RC=$RC
        # Don't break — we want every condition attempted so a single
        # late-stage hiccup doesn't starve earlier-condition results. But
        # we do surface the non-zero rc at job exit so afterok on the next
        # wave won't fire.
    fi
done

echo ""
echo "End time: $(date)   overall rc=$OVERALL_RC"
exit $OVERALL_RC
