#!/bin/bash
# Run the PDDL copilot experiment in the background on macOS.
# Detached, low CPU priority, no-sleep — continues while you work.
#
# Usage:
#   ./run_background.sh             # both models (full overnight run)
#   ./run_background.sh small       # just qwen3:0.5b (lightweight daytime run)
#   ./run_background.sh large       # just qwen3:4b (heavier, overnight)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Locate the marketplace (env var wins, then sibling directory)
MARKETPLACE_PATH="${PDDL_MARKETPLACE_PATH:-$SCRIPT_DIR/../pddl-copilot}"
if [ ! -d "$MARKETPLACE_PATH/plugins" ]; then
    echo "Error: pddl-copilot marketplace not found at $MARKETPLACE_PATH"
    echo "Clone it next to this repo or export PDDL_MARKETPLACE_PATH."
    exit 1
fi

case "${1:-both}" in
    small) MODELS=(qwen3:0.5b);            TAG="qwen05b" ;;
    large) MODELS=(qwen3:4b);              TAG="qwen4b" ;;
    both)  MODELS=(qwen3:0.5b qwen3:4b);   TAG="full" ;;
    *)     echo "Usage: $0 [small|large|both]"; exit 1 ;;
esac

STAMP=$(date +%Y%m%d_%H%M%S)
LOG="run_${TAG}_${STAMP}.log"
OUT="results/${TAG}_${STAMP}"

echo "Starting PDDL copilot experiment..."
echo "  Models:      ${MODELS[*]}"
echo "  Marketplace: $MARKETPLACE_PATH"
echo "  Filter:      per-task"
echo "  Chains:      on"
echo "  Output dir:  $OUT"
echo "  Log file:    $LOG"

caffeinate -i nice -n 19 nohup python3 run_experiment.py \
    --marketplace-path "$MARKETPLACE_PATH" \
    --models "${MODELS[@]}" \
    --tool-filter per-task \
    --chains \
    --output-dir "$OUT" \
    > "$LOG" 2>&1 &

PID=$!

echo ""
echo "Running in background, PID=$PID"
echo "  Watch progress:  tail -f $LOG"
echo "  Check status:    ps -p $PID"
echo "  Stop:            kill $PID"
