#!/usr/bin/env bash
# Submit gpt-oss:120b × {on, off} via the shared cis-ollama server.
# Uses the existing CPU-only run_condition.sbatch (no dedicated GPU).
#
# When to use:
#   - rtx_pro_6000 queue is full (submit_with_rtx.sh gpt-oss:120b blocks)
#   - You want to run 120b concurrently with other rtx self-deploy jobs
#
# When NOT to use (prefer submit_with_rtx.sh):
#   - rtx_pro_6000 is available — a dedicated GPU avoids cis eviction
#     (see development/CHANGELOG.md 2026-04-20 where 120b hit 560s/sample
#     under shared-server contention vs 291s for 20b).
#
# Usage:
#   bash cluster-experimenting/submit_120b_cis.sh
#   bash cluster-experimenting/submit_120b_cis.sh --dry-run
#   bash cluster-experimenting/submit_120b_cis.sh --think-modes "on"       # one mode only
#
# Note: this submits TWO jobs (on + off by default), both with no afterok
# dependency. If you're chaining after a submit_all.sh wave, use
# submit_all.sh --from-wave 5 instead (preserves afterok serialization).

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBATCH_FILE="$SCRIPT_DIR/run_condition.sbatch"

if [ ! -f "$SBATCH_FILE" ]; then
    echo "Error: $SBATCH_FILE not found." >&2
    exit 1
fi

DRY_RUN=0
THINK_MODES="on off"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --think-modes) shift; THINK_MODES="$1"; shift ;;
        -h|--help)
            sed -n '1,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)
            echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

MODEL="gpt-oss:120b"
MODEL_TAG=$(echo "$MODEL" | tr '/:.' '___')

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

echo "--- cis-ollama submission: $MODEL × ($THINK_MODES) ---" >&2
for THINK in $THINK_MODES; do
    case "$THINK" in
        on|off|default) ;;
        *) echo "Error: invalid think mode '$THINK' (must be on|off|default)" >&2; exit 1 ;;
    esac

    JOB_NAME="pddl_${MODEL_TAG}_${THINK}"
    cmd=(sbatch
        --job-name="$JOB_NAME"
        --export="ALL,MODEL=${MODEL},THINK_MODE=${THINK}"
        "$SBATCH_FILE")

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  DRY: ${cmd[*]}" >&2
    else
        jid=$("${cmd[@]}" | awk '{print $NF}')
        echo "  submitted $JOB_NAME as $jid" >&2
        echo "$jid"
    fi
done

echo "" >&2
echo "Monitor:   squeue --me | grep pddl_gpt_oss_120b" >&2
echo "Logs:      $REPO_ROOT/cluster-experimenting/logs/pddl_${MODEL_TAG}_*-<jobid>.out" >&2
echo "Results:   $REPO_ROOT/results/slurm_${MODEL_TAG}_*_<jobid>/" >&2
