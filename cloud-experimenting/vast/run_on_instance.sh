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

# Build the run command. Quote $@ properly so arg flags survive.
EXTRA_ARGS=("$@")

CMD=$(cat <<INNER
set -o pipefail   # tmux's default shell doesn't inherit pipefail; we
                  # need it so PIPESTATUS captures python's exit, not tee's
source $EXPT_DIR/.venv/bin/activate
export PDDL_MARKETPLACE_PATH=$PDDL_DIR
export OLLAMA_NUM_PARALLEL=4
cd $EXPT_DIR
python3 run_experiment.py \\
    --ollama-host http://127.0.0.1:11434 \\
    --concurrency 4 \\
    --models $MODELS \\
    ${EXTRA_ARGS[@]} \\
    --output-dir $LOG_DIR \\
    2>&1 | tee $LOG_DIR/run.log
echo "EXIT=\${PIPESTATUS[0]}" >> $LOG_DIR/run.log
INNER
)

tmux new-session -d -s "exp-$RUN_ID" "$CMD"
echo "Started tmux session 'exp-$RUN_ID'. Tail logs at $LOG_DIR/run.log"
echo "Attach manually with:  tmux attach -t exp-$RUN_ID"
