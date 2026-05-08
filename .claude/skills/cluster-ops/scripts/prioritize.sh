#!/usr/bin/env bash
# Prioritize specific models within a multi-cell array job.
#
# Listed models keep Nice=0; every OTHER pending cell in the manifest
# gets Nice=500 so the listed cells grab the next free GPU slot. This
# is the only direction available without admin (negative Nice is
# admin-only on the BGU CIS cluster).
#
# Use cases:
#   * Mid-sweep, queue is contended, you want a specific high-progress
#     cell to finish next so you can show colleagues partial results
#     while the rest keeps running.
#   * After a `--continue-partial` resubmit when the auto-prioritize
#     gate in submit_with_rtx.sh deliberately did NOT fire.
#
# Usage:
#   bash prioritize.sh <jobid>                       # default slow set
#   bash prioritize.sh <jobid> gemma4:31b            # only gemma stays at Nice=0
#   bash prioritize.sh <jobid> gemma4:31b qwen3.6:35b
#   bash prioritize.sh <jobid> --reset               # reset all cells to Nice=0
#   bash prioritize.sh <jobid> --dry-run [models...] # show what would change
#
# Idempotent — safe to re-run with a different model list. Already-running
# tasks are skipped (Nice has no effect once a task is dispatched).
#
# Reads the manifest written by submit_with_rtx.sh at:
#   <repo>/cluster-experimenting/logs/<jobid>.cells.tsv
#
# Env: REMOTE_USER, REMOTE_HOST, REPO_REMOTE, NICE_VALUE (default 500).

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
REPO_REMOTE="${REPO_REMOTE:-pddl-copilot-experiments}"
NICE_VALUE="${NICE_VALUE:-500}"

# Slow-set defaults — kept in sync with cluster-experimenting/lib/defaults.sh
# PDDL_SLOW_MODELS. Hardcoded here so the skill script can run without
# sourcing the remote defaults file. If you update one, update the other.
DEFAULT_SLOW_MODELS=(gemma4:31b qwen3.6:35b)

if [ "$#" -lt 1 ]; then
    sed -n '1,30p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 1
fi

JOBID="$1"; shift
if ! [[ "$JOBID" =~ ^[0-9]+$ ]]; then
    echo "Error: jobid must be a positive integer (got: $JOBID)" >&2
    exit 1
fi
DRY_RUN=0
RESET=0
KEEP_MODELS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --reset) RESET=1; shift ;;
        -h|--help) sed -n '1,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) KEEP_MODELS+=("$1"); shift ;;
    esac
done

if [ "$RESET" -eq 0 ] && [ "${#KEEP_MODELS[@]}" -eq 0 ]; then
    KEEP_MODELS=("${DEFAULT_SLOW_MODELS[@]}")
fi

echo "--- prioritize ---" >&2
echo "  jobid:        $JOBID" >&2
if [ "$RESET" -eq 1 ]; then
    echo "  mode:         reset (Nice=0 for all cells)" >&2
else
    echo "  keep@Nice=0:  ${KEEP_MODELS[*]}" >&2
    echo "  deprioritize: everything else (Nice=$NICE_VALUE)" >&2
fi
[ "$DRY_RUN" -eq 1 ] && echo "  DRY-RUN" >&2

# Pipe-joined keep-set; pipes can't appear in model names, and the
# wrap-in-pipes match (`*"|${model}|"*`) prevents prefix bleed.
KEEP_LIST=$(IFS='|'; echo "${KEEP_MODELS[*]}")

# One SSH round-trip: read manifest, parse pending tasks, decide Nice for
# each, optionally apply. Output is a TSV report we render locally.
ssh "${REMOTE_USER}@${REMOTE_HOST}" \
    "JOBID=$JOBID NICE_VALUE=$NICE_VALUE KEEP_LIST='$KEEP_LIST' \
     RESET=$RESET DRY_RUN=$DRY_RUN REPO=$REPO_REMOTE bash -s" <<'REMOTE'
set -eo pipefail

manifest="$HOME/$REPO/cluster-experimenting/logs/${JOBID}.cells.tsv"
if [ ! -f "$manifest" ]; then
    echo "Error: manifest not found at $manifest" >&2
    echo "(was the job submitted via submit_with_rtx.sh after the prioritize feature landed?)" >&2
    exit 2
fi

# Pending array tasks for this job. -r expands ranges so each task is its
# own row (otherwise SLURM collapses 17389411_[6-9] into one line).
declare -A PENDING
while IFS='|' read -r tid state; do
    [ -n "$tid" ] || continue
    PENDING["$tid"]="$state"
done < <(squeue -h -j "$JOBID" -r -o '%i|%T' 2>/dev/null || true)

if [ "${#PENDING[@]}" -eq 0 ]; then
    echo "No tasks found for job $JOBID (already completed or cancelled?)" >&2
    exit 0
fi

# Walk the manifest, decide Nice per task, optionally apply.
printf 'idx\tarray_id\tmodel\tthink\tcond\tstate\taction\n'
applied=0
skipped_running=0
not_pending=0
while IFS=$'\t' read -r idx model think cond; do
    [ -n "$idx" ] || continue
    aid="${JOBID}_${idx}"
    state="${PENDING[$aid]:-MISSING}"

    if [ "$RESET" -eq 1 ]; then
        target_nice=0
    else
        # Keep model? → Nice=0; otherwise → NICE_VALUE.
        # KEEP_LIST is `|`-joined; we wrap in pipes for an unambiguous match.
        if [[ "|${KEEP_LIST}|" == *"|${model}|"* ]]; then
            target_nice=0
        else
            target_nice="$NICE_VALUE"
        fi
    fi

    case "$state" in
        PENDING)
            action="set Nice=$target_nice"
            if [ "$DRY_RUN" -eq 0 ]; then
                if scontrol update "JobId=$aid" "Nice=$target_nice" 2>/dev/null; then
                    applied=$((applied + 1))
                else
                    action="${action} (FAILED — likely raced to RUNNING)"
                fi
            fi
            ;;
        RUNNING)
            action="skip (already running)"
            skipped_running=$((skipped_running + 1))
            ;;
        MISSING)
            action="skip (not in queue — completed/cancelled)"
            not_pending=$((not_pending + 1))
            ;;
        *)
            action="skip (state=$state)"
            not_pending=$((not_pending + 1))
            ;;
    esac
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$idx" "$aid" "$model" "$think" "$cond" "$state" "$action"
done < "$manifest"

echo "---" >&2
if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: no scontrol calls executed." >&2
else
    echo "Applied to $applied pending task(s); skipped $skipped_running running, $not_pending not-in-queue." >&2
fi
REMOTE
