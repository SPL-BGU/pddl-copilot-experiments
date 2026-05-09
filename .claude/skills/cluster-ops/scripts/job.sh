#!/usr/bin/env bash
# Single-job inspection: squeue + sacct + log tail in one SSH call.
#
# Use for one-off probe/smoke sbatches where status.sh's sweep-matrix
# rendering doesn't fit, or to drill into one specific cell of a sweep.
# Works for any jobid — sweep cells, probes, post-mortems of failed jobs.
#
# Usage:
#   bash job.sh <jobid>                 # squeue + sacct + last 25 log lines
#   bash job.sh <jobid> --lines 100     # custom log tail size
#   bash job.sh <jobid> --no-log        # skip log tail (squeue/sacct only)
#
# Env overrides:
#   REMOTE_USER (default omereliy), REMOTE_HOST (default slurm.bgu.ac.il)

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
LINES=25
NO_LOG=0
JOBID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lines) shift; LINES="$1"; shift ;;
        --no-log) NO_LOG=1; shift ;;
        -h|--help)
            sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)
            if [ -z "$JOBID" ]; then
                JOBID="$1"; shift
            else
                echo "Unknown extra arg: $1" >&2; exit 1
            fi
            ;;
    esac
done

if [ -z "$JOBID" ]; then
    echo "Usage: bash job.sh <jobid> [--lines N] [--no-log]" >&2
    exit 1
fi

# Numeric guard — catches accidental `bash job.sh status` (status.sh confusion).
case "$JOBID" in
    ''|*[!0-9_]*) echo "ERROR: jobid must be numeric (got: $JOBID)" >&2; exit 2 ;;
esac

# Pass JOBID/LINES/NO_LOG positionally so the remote can `set -- "$1" "$2" "$3"`.
# `bash -s --` ends bash option parsing so values starting with `-` would still
# land in $1+ (defensive — current values are numeric, but cheap insurance).
ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s --" "$JOBID" "$LINES" "$NO_LOG" <<'REMOTE'
set -eo pipefail
JOBID="$1"; LINES="$2"; NO_LOG="$3"
LOGS_DIR="$HOME/pddl-copilot-experiments/cluster-experimenting/logs"

echo "## Job $JOBID"
echo

echo "### squeue"
sq=$(squeue -j "$JOBID" -o '%.10i %.20j %.8T %.10M %.10L %.16R %.20S' 2>/dev/null || true)
if [ -n "$sq" ] && [ "$(echo "$sq" | wc -l)" -gt 1 ]; then
    echo '```'
    echo "$sq"
    echo '```'
else
    echo "_(not in queue — completed, cancelled, or unknown jobid)_"
fi
echo

echo "### sacct"
echo '```'
# JobName%24 is wide enough for vllm_27b_smoke and the per-cell pddl_<model>_<think>_<cond>
# names. State%12 covers PENDING/RUNNING/COMPLETED/CANCELLED+. Reason%20 covers all
# Mar-26 guide REASON values.
sacct -j "$JOBID" \
    --format=JobID,JobName%24,State%12,Elapsed,Start,End,ExitCode,Reason%20 \
    2>/dev/null | head -10
echo '```'
echo

if [ "$NO_LOG" = "0" ]; then
    # Glob covers all log naming patterns: pddl_rtx_<model>-<jid>.out (current),
    # pddl_<model>_<think>-<jid>.out (cis-retired), <jobname>-<jid>.out (probes).
    LOGF=$(ls -t "$LOGS_DIR"/*-"$JOBID".out 2>/dev/null | head -1)
    if [ -n "$LOGF" ]; then
        echo "### Log tail (last $LINES lines)"
        echo "path: \`$LOGF\`"
        echo '```'
        tail -n "$LINES" "$LOGF"
        echo '```'
    else
        echo "### Log tail"
        echo "_(no log file matching $LOGS_DIR/*-$JOBID.out — job hasn't started, or log was cleaned)_"
    fi
fi
REMOTE
