#!/usr/bin/env bash
# Fan-out submission for pddl-copilot-experiments on BGU SLURM.
# Submits one sbatch per (model × condition) pair — 5 conditions per model.
#
# Mirrors run_background.sh's sweep (1 no-tools run + tools × {per-task,all} × {minimal,guided})
# but parallelizes across conditions as independent SLURM jobs.
#
# Usage:
#   bash cluster-experimenting/submit_all.sh                 # default: both models, all 5 conditions (10 jobs)
#   bash cluster-experimenting/submit_all.sh --small         # Qwen3.5:0.8B only       (5 jobs)
#   bash cluster-experimenting/submit_all.sh --large         # gpt-oss:20b only        (5 jobs)
#   bash cluster-experimenting/submit_all.sh --models a b c  # custom list
#   bash cluster-experimenting/submit_all.sh --conditions no-tools tools_all_minimal
#   bash cluster-experimenting/submit_all.sh --dry-run       # print sbatch commands, do not submit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBATCH_FILE="$SCRIPT_DIR/run_condition.sbatch"

# Defaults — all 5 confirmed present on cis-ollama/api/tags (checked 2026-04-20).
# Qwen3.5:0.8B is the closest analog to the paper's qwen3:0.6b.
# Qwen3.5:27b picks a large-qwen point that doesn't duplicate gpt-oss:120b's
# scale or overlap gpt-oss:20b; it sits at ~same scale as gemma4:31b for a
# clean cross-family comparison at ~30b.
# The paper's qwen3:0.6b / qwen3:4b are NOT hosted on cis-ollama, so this is
# a cluster-variant of the sweep, not a 1:1 paper reproduction.
DEFAULT_MODELS=(Qwen3.5:0.8B Qwen3.5:27b gpt-oss:20b gpt-oss:120b gemma4:31b)

DEFAULT_CONDITIONS=(
    no-tools
    tools_per-task_minimal
    tools_per-task_guided
    tools_all_minimal
    tools_all_guided
)

MODELS=()
CONDITIONS=()
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --small)
            MODELS=(Qwen3.5:0.8B); shift ;;
        --large)
            MODELS=(gpt-oss:20b); shift ;;
        --both)
            MODELS=("${DEFAULT_MODELS[@]}"); shift ;;
        --models)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do MODELS+=("$1"); shift; done ;;
        --conditions)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do CONDITIONS+=("$1"); shift; done ;;
        --dry-run)
            DRY_RUN=1; shift ;;
        -h|--help)
            sed -n '1,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)
            echo "Unknown option: $1"; exit 1 ;;
    esac
done

[ ${#MODELS[@]}     -eq 0 ] && MODELS=("${DEFAULT_MODELS[@]}")
[ ${#CONDITIONS[@]} -eq 0 ] && CONDITIONS=("${DEFAULT_CONDITIONS[@]}")

# sbatch --output uses 'cluster-experimenting/logs/' relative to the submit dir.
# cd into the repo root so that path resolves regardless of where the user invoked us.
cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

TOTAL=$(( ${#MODELS[@]} * ${#CONDITIONS[@]} ))
echo "Submitting $TOTAL jobs: ${#MODELS[@]} model(s) × ${#CONDITIONS[@]} condition(s)"
echo "  Models:     ${MODELS[*]}"
echo "  Conditions: ${CONDITIONS[*]}"
echo "  Submit CWD: $PWD"
echo "  sbatch:     $SBATCH_FILE"
echo "---"

for model in "${MODELS[@]}"; do
    for cond in "${CONDITIONS[@]}"; do
        model_tag=$(echo "$model" | tr '/:.' '___')
        job_name="pddl_${model_tag}_${cond}"
        cmd=(sbatch
            --job-name="$job_name"
            --export="ALL,MODEL=${model},CONDITION=${cond}"
            "$SBATCH_FILE")
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '  DRY  %s\n' "${cmd[*]}"
        else
            printf '  %s\n' "$job_name"
            "${cmd[@]}"
        fi
    done
done

echo "---"
echo "Monitor:   squeue --me"
echo "Logs:      $REPO_ROOT/cluster-experimenting/logs/  (pddl_<model>_<cond>-<jobid>.out)"
echo "Results:   $REPO_ROOT/results/  (slurm_<model>_<cond>_<jobid>/)"
echo "Cancel:    scancel --name <job_name>   |  scancel -u \$USER"
