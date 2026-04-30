#!/usr/bin/env bash
# Runs ON the Vast.ai instance. Launches run_experiment.py inside `tmux`
# so the laptop's SSH session can disconnect without killing the run.
# Returns immediately; orchestrator polls for completion via tmux.
#
# Inputs (env, set by run_smoke.sh):
#   MODELS    space-separated Ollama model names
#   RUN_ID    short identifier embedded in result paths + tmux session name
# Inputs (positional):
#   any extra args are forwarded to run_experiment.py (typically --smoke).

set -euo pipefail

: "${MODELS:?MODELS env required}"
: "${RUN_ID:?RUN_ID env required}"

WORK=/workspace
EXPT_DIR=$WORK/pddl-copilot-experiments
PDDL_DIR=$WORK/pddl-copilot

cd "$EXPT_DIR"

# Verify ollama serve is up before we bother launching tmux
curl -sf http://127.0.0.1:11434/api/tags >/dev/null \
    || { echo "ERROR: ollama serve not reachable on 127.0.0.1:11434" >&2; exit 1; }

LOG_DIR="$EXPT_DIR/results/vast-$RUN_ID"
mkdir -p "$LOG_DIR"

# Kill any prior tmux session under the same name (re-runs)
tmux kill-session -t "exp-$RUN_ID" 2>/dev/null || true

# Build the run command. We bake `--smoke` literally rather than splatting
# `${EXTRA_ARGS[@]}` from the heredoc — array expansion inside an unquoted
# heredoc was a fragile dance and the 2026-04-30 attempt died at argparse
# with `unrecognized arguments: <whitespace>`, exit 2. Smoke is the only
# thing this script gets invoked for today; if a non-smoke variant ever
# needs it, parameterize via a SMOKE_FLAG env var instead of $@.
#
# Pin LANG/LC_ALL because the apt step on the nvidia/cuda base image emits
# `Setting locale failed` (no locales pkg). A broken locale on Python 3.11+
# can mis-decode argv to control chars, which is one hypothesis for the
# 'whitespace argv' failure mode.
CMD=$(cat <<INNER
set -o pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
source $EXPT_DIR/.venv/bin/activate
export PDDL_MARKETPLACE_PATH=$PDDL_DIR
export OLLAMA_NUM_PARALLEL=4
cd $EXPT_DIR
python3 run_experiment.py \\
    --ollama-host http://127.0.0.1:11434 \\
    --concurrency 4 \\
    --models $MODELS \\
    --smoke \\
    --output-dir $LOG_DIR \\
    2>&1 | tee $LOG_DIR/run.log
echo "EXIT=\${PIPESTATUS[0]}" >> $LOG_DIR/run.log
INNER
)

# Diagnostic capture so post-mortem doesn't depend on the instance still
# being alive — these files are inside $LOG_DIR which the orchestrator
# rsyncs locally on EXIT. Triggered by the 2026-04-30 'unrecognized argv'
# failure where we couldn't see the actual CMD that ran.
{
    echo "===== CMD passed to tmux ====="
    printf '%s\n' "$CMD"
    echo
    echo "===== argv to run_on_instance.sh ====="
    printf 'argv[0]=%q\n' "$0"
    i=0
    for a in "$@"; do
        i=$((i+1))
        printf 'argv[%d]=%q\n' "$i" "$a"
    done
    echo
    echo "===== env (LANG/LC_*/MODELS/RUN_ID) ====="
    env | grep -E '^(LANG|LC_|MODELS|RUN_ID|PDDL_)' | sort
    echo
    echo "===== bash version ====="
    bash --version | head -1
    echo "===== /bin/sh -> ====="
    readlink -f /bin/sh 2>/dev/null || echo "/bin/sh (not a symlink)"
} > "$LOG_DIR/instance-diag.txt"

tmux new-session -d -s "exp-$RUN_ID" "$CMD"
echo "Started tmux session 'exp-$RUN_ID'. Tail logs at $LOG_DIR/run.log"
echo "Attach manually with:  tmux attach -t exp-$RUN_ID"
echo "Pre-launch diagnostic captured at $LOG_DIR/instance-diag.txt"
