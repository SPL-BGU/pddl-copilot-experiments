#!/usr/bin/env bash
# Fan-out submission for pddl-copilot-experiments on BGU SLURM.
# Submits 9 jobs across 5 waves keyed on (model, think_mode).
# Each wave waits for the previous to succeed (--dependency=afterok) so
# only one model family is live on the shared cis-ollama server at a time,
# eliminating weight-eviction thrashing (see plan: ~/iridescent-meandering-nest.md).
#
# Within each wave, the think-on / think-off jobs for the same model run in
# parallel — they share loaded weights, so OLLAMA_NUM_PARALLEL handles
# both client sessions without eviction.
#
# Each SLURM job (run_condition.sbatch) loops over all 5 conditions
# sequentially in a single process.
#
# Waves:
#   1. Qwen3.5:0.8B   × {on, off}       (2 jobs)
#   2. gpt-oss:20b    × {on, off}       (2 jobs, afterok wave 1)
#   3. Qwen3.5:27b    × {on, off}       (2 jobs, afterok wave 2)
#   4. gemma4:31b     × {default}       (1 job,  afterok wave 3; gemma has no thinking)
#   5. gpt-oss:120b   × {on, off}       (2 jobs, afterok wave 4)
#
# Usage:
#   bash cluster-experimenting/submit_all.sh                       # submit all 5 waves (9 jobs), all 5 conditions
#   bash cluster-experimenting/submit_all.sh --dry-run             # print sbatch commands, do not submit
#   bash cluster-experimenting/submit_all.sh --from-wave 3         # skip waves 1-2 (no dependency on them)
#   bash cluster-experimenting/submit_all.sh --from-wave 3 --force # bypass preflight (use with care)
#
# Optional env override:
#   CONDITIONS="tools_per-task_minimal tools_per-task_guided tools_all_minimal tools_all_guided" \
#     bash cluster-experimenting/submit_all.sh
#   Forwarded to each sbatch via --export so run_condition.sbatch uses the restricted list.
#   Unset → run_condition.sbatch's own default (all 5 conditions) applies.
#
# Safety: --from-wave N>1 refuses to submit if any pddl_* jobs are already
# RUNNING or PENDING on the queue, because resumed waves have no afterok
# dependency on the live ones and would re-trigger the eviction thrashing
# this wave design exists to prevent. Override with --force only after
# inspecting `squeue --me` and deciding the concurrency is acceptable.

set -eo pipefail
# Note: deliberately NOT using `-u` (nounset). The wave submission logic
# expands potentially-empty arrays (`dep_arg`, `IDS`) inside function calls,
# which trips nounset under bash 3.2 on macOS. The script's own variables
# are all set with defaults above, so nounset buys us nothing useful here.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBATCH_FILE="$SCRIPT_DIR/run_condition.sbatch"

DRY_RUN=0
FROM_WAVE=1
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1; shift ;;
        --from-wave)
            shift; FROM_WAVE="$1"; shift ;;
        --force)
            FORCE=1; shift ;;
        -h|--help)
            sed -n '1,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)
            echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$REPO_ROOT"
mkdir -p cluster-experimenting/logs

# Preflight: refuse --from-wave N>1 while earlier-wave pddl_* jobs are still
# live on the queue. The resumed waves are submitted with no afterok dep on
# the live ones, so they would race and re-trigger cis-ollama weight eviction.
if [ "$FROM_WAVE" -gt 1 ] && [ "$DRY_RUN" -eq 0 ] && [ "$FORCE" -eq 0 ]; then
    live=$(squeue --me --states=R,PD --noheader --format=%j 2>/dev/null | grep -c '^pddl_' || true)
    if [ "$live" -gt 0 ]; then
        echo "ERROR: --from-wave $FROM_WAVE but $live pddl_* job(s) are still RUNNING or PENDING." >&2
        echo "       Resuming now bypasses afterok serialization and re-triggers" >&2
        echo "       weight-eviction thrashing on cis-ollama." >&2
        echo "       Inspect:   squeue --me --noheader --format='%j %T' | grep '^pddl_'" >&2
        echo "       Override:  bash $0 --from-wave $FROM_WAVE --force" >&2
        exit 2
    fi
fi

# Wave definitions: each wave is a list of (model, think_mode) pairs encoded
# as "MODEL|THINK_MODE" strings (|-separated so model names with ':' are safe).
WAVE1=(
    "Qwen3.5:0.8B|on"
    "Qwen3.5:0.8B|off"
)
WAVE2=(
    "gpt-oss:20b|on"
    "gpt-oss:20b|off"
)
WAVE3=(
    "Qwen3.5:27b|on"
    "Qwen3.5:27b|off"
)
WAVE4=(
    "gemma4:31b|default"
)
WAVE5=(
    "gpt-oss:120b|on"
    "gpt-oss:120b|off"
)

# Submit one wave, optionally with an afterok dependency on previous wave's
# job IDs. Prints the newly-created job IDs (one per line) to stdout so the
# caller can capture them. Progress chatter goes to stderr.
submit_wave() {
    local wave_num="$1"; shift
    local dep_ids="$1"; shift
    local jobs=("$@")

    local dep_arg=()
    if [ -n "$dep_ids" ]; then
        dep_arg=(--dependency="afterok:${dep_ids}")
    fi

    echo "--- Wave $wave_num (${#jobs[@]} job(s))${dep_ids:+  depends on afterok:$dep_ids}" >&2

    for entry in "${jobs[@]}"; do
        local model="${entry%%|*}"
        local think="${entry##*|}"
        local model_tag
        model_tag=$(echo "$model" | tr '/:.' '___')
        local job_name="pddl_${model_tag}_${think}"

        # Forward the caller-set CONDITIONS env var when present, so the
        # caller can restrict which conditions each job runs without touching
        # run_condition.sbatch. When unset, sbatch's --export=ALL would still
        # propagate CONDITIONS implicitly, but being explicit documents the
        # contract and survives accidental removal of ALL.
        local export_spec="ALL,MODEL=${model},THINK_MODE=${think}"
        if [ -n "${CONDITIONS:-}" ]; then
            export_spec="${export_spec},CONDITIONS=${CONDITIONS}"
        fi

        local cmd=(sbatch
            --parsable
            "${dep_arg[@]}"
            --job-name="$job_name"
            --export="$export_spec"
            "$SBATCH_FILE")

        if [ "$DRY_RUN" -eq 1 ]; then
            echo "  DRY: ${cmd[*]}" >&2
            # Emit a placeholder job id so downstream dep string construction
            # still looks realistic in dry-run output.
            echo "DRYRUN_w${wave_num}_${model_tag}_${think}"
        else
            echo "  submitting $job_name" >&2
            local jid
            jid=$("${cmd[@]}")
            echo "  -> $jid" >&2
            echo "$jid"
        fi
    done
}

# Run the waves. Each wave captures its job ids into a colon-joined string
# that becomes the next wave's afterok dependency list.
join_colons() {
    local IFS=:
    echo "$*"
}

# read_wave_ids: portable substitute for `mapfile -t` (not available in
# macOS bash 3.2). Populates the global IDS array with one entry per stdout
# line from the given command.
read_wave_ids() {
    IDS=()
    local line
    while IFS= read -r line; do
        IDS+=("$line")
    done < <("$@")
}

DEP=""

if [ "$FROM_WAVE" -le 1 ]; then
    read_wave_ids submit_wave 1 "$DEP" "${WAVE1[@]}"
    DEP=$(join_colons "${IDS[@]}")
fi

if [ "$FROM_WAVE" -le 2 ]; then
    read_wave_ids submit_wave 2 "$DEP" "${WAVE2[@]}"
    DEP=$(join_colons "${IDS[@]}")
fi

if [ "$FROM_WAVE" -le 3 ]; then
    read_wave_ids submit_wave 3 "$DEP" "${WAVE3[@]}"
    DEP=$(join_colons "${IDS[@]}")
fi

if [ "$FROM_WAVE" -le 4 ]; then
    read_wave_ids submit_wave 4 "$DEP" "${WAVE4[@]}"
    DEP=$(join_colons "${IDS[@]}")
fi

if [ "$FROM_WAVE" -le 5 ]; then
    read_wave_ids submit_wave 5 "$DEP" "${WAVE5[@]}"
fi

echo "---" >&2
echo "Monitor:   squeue --me" >&2
echo "Logs:      $REPO_ROOT/cluster-experimenting/logs/  (pddl_<model>_<think>-<jobid>.out)" >&2
echo "Results:   $REPO_ROOT/results/  (slurm_<model>_<think>_<cond>_<jobid>/)" >&2
echo "Cancel:    scancel -u \$USER" >&2
