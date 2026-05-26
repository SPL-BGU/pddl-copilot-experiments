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

source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

LINES=25
NO_LOG=0
JOBID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lines) shift; LINES="$1"; shift ;;
        --no-log) NO_LOG=1; shift ;;
        -h|--help) _show_help 2 15; exit 0 ;;
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

# --- Queue assessment (PENDING only) ---
# Answers "when does this move from PD to R?" via priority value, same-GPU-class
# rank, REASON breakdown for jobs ahead, and SLURM's StartTime translated into
# a humanised ETA. Skipped for non-pending jobs.
STATE=$(squeue -j "$JOBID" -h -o '%T' 2>/dev/null | head -1)
if [ "$STATE" = "PENDING" ]; then
    echo "### Queue assessment"

    # Priority value (sprio column 3 = PRIORITY; -h drops the header).
    PRIO=$(sprio -j "$JOBID" -h 2>/dev/null | awk '{print $3}' | head -1)
    echo "- Priority: ${PRIO:-?}"

    # GPU class from the job's tres-per-job (e.g. "gres/gpu:rtx_6000:1" → rtx_6000).
    GPU_CLASS=$(squeue -j "$JOBID" -h -O 'tres-per-job:64' 2>/dev/null \
        | grep -oE 'gres/gpu:[^:[:space:]]+:' | head -1 | cut -d: -f2)

    if [ -n "$GPU_CLASS" ]; then
        # Same-class pending list, sorted by priority desc. Anchored colon in the
        # awk regex avoids matching the rtx_6000 substring of rtx_pro_6000.
        SAMECLASS=$(squeue -t PD -h --sort=-p -O 'JobID:14,tres-per-job:36,Reason:24' 2>/dev/null \
            | awk -v cls="$GPU_CLASS" '$2 ~ ("gpu:"cls":")')
        if [ -n "$SAMECLASS" ]; then
            TOTAL=$(echo "$SAMECLASS" | wc -l | tr -d ' ')
            RANK=$(echo "$SAMECLASS" | nl -ba | awk -v jid="$JOBID" '$2 == jid {print $1; exit}')
            echo "- Same-class queue: #${RANK:-?} of $TOTAL pending requesting $GPU_CLASS"

            # REASON breakdown for jobs ahead. Many "ahead" jobs are blocked on
            # MaxGRESPerAccount, Dependency, etc. and won't all clear before us
            # — this explains why rank doesn't predict timing linearly.
            if [ -n "$RANK" ] && [ "$RANK" -gt 1 ]; then
                AHEAD=$(( RANK - 1 ))
                BR=$(echo "$SAMECLASS" | head -n "$AHEAD" | awk '{print $3}' \
                     | sort | uniq -c | sort -rn \
                     | awk '{printf "%s=%d ", $2, $1}')
                [ -n "$BR" ] && echo "- $AHEAD ahead by REASON: $BR"
            fi
        fi
    fi

    # SLURM "StartTime" is the earliest backfill-window slot the scheduler
    # can verify assuming our job is next in line. Higher-priority jobs can
    # leapfrog it, so the value is a best-case lower bound, not a
    # commitment — re-computed each scheduler cycle and frequently slips.
    # In practice it's almost always "now-ish" for any pending job, which
    # is why we frame it as a window-marker rather than an ETA.
    ST=$(squeue -j "$JOBID" -h -O 'StartTime:24' 2>/dev/null | tr -d ' ')
    if [ -n "$ST" ] && [ "$ST" != "Unknown" ] && [ "$ST" != "N/A" ]; then
        NOW=$(date +%s)
        SE=$(date -d "$ST" +%s 2>/dev/null || echo 0)
        D=$(( SE - NOW ))
        if [ "$D" -le 60 ]; then
            ETA="next backfill window (best-case lower bound, not a guarantee)"
        elif [ "$D" -lt 300 ]; then
            ETA="best-case ~$((D/60))m $((D%60))s"
        elif [ "$D" -lt 3600 ]; then
            ETA="best-case ~$((D/60))m"
        elif [ "$D" -lt 86400 ]; then
            ETA="best-case ~$((D/3600))h $(((D%3600)/60))m"
        else
            ETA="best-case ~$((D/86400))d $(((D%86400)/3600))h"
        fi
        echo "- SLURM earliest-slot estimate: $ST → $ETA"
    else
        echo "- SLURM earliest-slot estimate: not yet computed — re-check in 1-2 min"
    fi
    echo
fi

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
