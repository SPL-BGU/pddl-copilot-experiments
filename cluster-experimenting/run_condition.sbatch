#!/bin/bash
### Runs run_experiment.py for ONE (MODEL, CONDITION) pair.
### Submit via cluster-experimenting/submit_all.sh (fan-out across models × conditions),
### or directly:
###   sbatch --export=ALL,MODEL=gpt-oss:20b,CONDITION=tools_all_minimal \
###          cluster-experimenting/run_condition.sbatch
###
### Required env (set via --export=ALL,MODEL=...,CONDITION=...):
###   MODEL       — Ollama model name (e.g. Qwen3.5:0.8B, gpt-oss:20b)
###   CONDITION   — one of:
###                   no-tools
###                   tools_per-task_minimal
###                   tools_per-task_guided
###                   tools_all_minimal
###                   tools_all_guided
###
### Optional env (defaults shown):
###   ENV_NAME=pddl_copilot
###   EXPT_ROOT=$HOME/pddl-copilot-experiments
###   PDDL_MARKETPLACE_PATH=$HOME/pddl-copilot
###   OLLAMA_HOST=https://cis-ollama.auth.ad.bgu.ac.il
###   OLLAMA_INSECURE=1                 (empty string disables)
###   CHAIN_SAMPLES=20
###
### sbatch config parameters must start with #SBATCH and precede any other command.
#SBATCH --partition main
#SBATCH --time 1-00:00:00
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
: "${MODEL:?Error: export MODEL=... (e.g. Qwen3.5:0.8B). Submit via submit_all.sh or pass --export=ALL,MODEL=...,CONDITION=...}"
: "${CONDITION:?Error: export CONDITION=... (one of: no-tools | tools_per-task_minimal | tools_per-task_guided | tools_all_minimal | tools_all_guided)}"

### Defaults ###
ENV_NAME="${ENV_NAME:-pddl_copilot}"
EXPT_ROOT="${EXPT_ROOT:-$HOME/pddl-copilot-experiments}"
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$HOME/pddl-copilot}"
OLLAMA_HOST="${OLLAMA_HOST:-https://cis-ollama.auth.ad.bgu.ac.il}"
OLLAMA_INSECURE="${OLLAMA_INSECURE:-1}"
CHAIN_SAMPLES="${CHAIN_SAMPLES:-20}"

export OLLAMA_HOST OLLAMA_INSECURE

### Activate conda env (anaconda pre-installed on BGU cluster) ###
module load anaconda
source activate "$ENV_NAME"

### Parse CONDITION into run_experiment.py flags ###
### Labels match run_background.sh output-dir naming so downstream analysis
### notebooks (analyze_results.ipynb) pick them up uniformly.
case "$CONDITION" in
    no-tools)
        COND_ARGS=(--conditions no-tools) ;;
    tools_per-task_minimal)
        COND_ARGS=(--conditions tools --tool-filter per-task --prompt-style minimal) ;;
    tools_per-task_guided)
        COND_ARGS=(--conditions tools --tool-filter per-task --prompt-style guided) ;;
    tools_all_minimal)
        COND_ARGS=(--conditions tools --tool-filter all --prompt-style minimal) ;;
    tools_all_guided)
        COND_ARGS=(--conditions tools --tool-filter all --prompt-style guided) ;;
    *)
        echo "Error: unknown CONDITION=$CONDITION"; exit 1 ;;
esac

### Conditional --ollama-insecure (for BGU's self-signed cert) ###
INSECURE_ARG=()
if [ -n "$OLLAMA_INSECURE" ]; then
    INSECURE_ARG=(--ollama-insecure)
fi

### Output dir (matches run_background.sh convention: slurm_<tag>_<cond>_<jobid>) ###
MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')
OUT_DIR="${EXPT_ROOT}/results/slurm_${MODEL_TAG}_${CONDITION}_${SLURM_JOBID}"

echo "Model:       $MODEL"
echo "Condition:   $CONDITION  (args: ${COND_ARGS[*]})"
echo "Output:      $OUT_DIR"
echo "Marketplace: $MARKETPLACE_PATH"
echo "Ollama host: $OLLAMA_HOST  (insecure=${OLLAMA_INSECURE:-0})"
echo "Chains:      on, --chain-samples $CHAIN_SAMPLES"

cd "$EXPT_ROOT"

### Sanity: remote Ollama must be reachable before we burn job time ###
if ! curl ${OLLAMA_INSECURE:+-k} -sf --max-time 10 "${OLLAMA_HOST}/api/tags" > /dev/null; then
    echo "Error: cannot reach ${OLLAMA_HOST}/api/tags from compute node."
    echo "  - Check BGU VPN status from login node."
    echo "  - Set OLLAMA_INSECURE='' if the cert chain is now trusted."
    exit 2
fi

### Run ###
python3 run_experiment.py \
    --marketplace-path "$MARKETPLACE_PATH" \
    --models "$MODEL" \
    --ollama-host "$OLLAMA_HOST" \
    "${INSECURE_ARG[@]}" \
    --chains --chain-samples "$CHAIN_SAMPLES" \
    "${COND_ARGS[@]}" \
    --output-dir "$OUT_DIR"

echo "End time: $(date)"
