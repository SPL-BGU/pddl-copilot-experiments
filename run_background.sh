#!/bin/bash
# Run the PDDL copilot experiment in the background on macOS.
# Detached, low CPU priority, no-sleep — continues while you work.
#
# Usage:
#   ./run_background.sh             # both models (full overnight run)
#   ./run_background.sh small       # just qwen3:0.6b (lightweight daytime run)
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

# v2.0.0 numeric_planner (ENHSP) runs on the JVM — fail fast if Java is missing or too old
if ! command -v java >/dev/null 2>&1; then
    echo "Error: java not found on PATH. Numeric planning via ENHSP requires Java 17+."
    echo "  macOS:  brew install openjdk@17"
    echo "  Linux:  sudo apt install openjdk-17-jre-headless"
    exit 1
fi
JAVA_MAJOR=$(java -version 2>&1 | awk -F'[".]' '/version/ {print $2; exit}')
if ! [[ "$JAVA_MAJOR" =~ ^[0-9]+$ ]] || [ "$JAVA_MAJOR" -lt 17 ]; then
    echo "Error: Java 17+ required for numeric_planner (ENHSP). Found: $(java -version 2>&1 | head -1)"
    exit 1
fi

# Ensure Ollama is running (leave it running on exit — it's persistent laptop infra)
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama not running — starting in background..."
    ollama serve > "$SCRIPT_DIR/ollama_serve.log" 2>&1 &
    for i in {1..15}; do
        if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "Ollama ready."
            break
        fi
        sleep 1
    done
    if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Error: Ollama failed to start after 15s. Is it installed? (see ollama_serve.log)"
        exit 1
    fi
fi

case "${1:-both}" in
    small) MODELS=(qwen3:0.6b);            TAG="qwen06b" ;;
    large) MODELS=(qwen3:4b);              TAG="qwen4b" ;;
    both)  MODELS=(qwen3:0.6b qwen3:4b);   TAG="full" ;;
    *)     echo "Usage: $0 [small|large|both]"; exit 1 ;;
esac

# Ensure requested models are pulled
for m in "${MODELS[@]}"; do
    if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$m"; then
        echo "Pulling $m..."
        ollama pull "$m" || { echo "Error: failed to pull $m"; exit 1; }
    fi
done

STAMP=$(date +%Y%m%d_%H%M%S)
LOG="run_${TAG}_${STAMP}.log"
OUT_PREFIX="results/${TAG}_${STAMP}"
FILTERS="per-task all"
PROMPT_STYLES="minimal guided"

echo "Starting PDDL copilot experiment..."
echo "  Models:      ${MODELS[*]}"
echo "  Marketplace: $MARKETPLACE_PATH"
echo "  Filters:     $FILTERS (run sequentially)"
echo "  Prompts:     $PROMPT_STYLES (run sequentially)"
echo "  Chains:      on"
echo "  Output dirs: ${OUT_PREFIX}_{filter}_{prompt}/"
echo "  Log file:    $LOG"

nohup caffeinate -i bash -c "
cd \"$SCRIPT_DIR\"
for FILTER in $FILTERS; do
  for PSTYLE in $PROMPT_STYLES; do
    echo \"===== filter=\$FILTER prompt=\$PSTYLE started \$(date) =====\"
    nice -n 19 python3 run_experiment.py \
        --marketplace-path \"$MARKETPLACE_PATH\" \
        --models ${MODELS[*]} \
        --tool-filter \"\$FILTER\" \
        --prompt-style \"\$PSTYLE\" \
        --chains \
        --chain-samples 20 \
        --output-dir \"${OUT_PREFIX}_\${FILTER}_\${PSTYLE}\"
    echo \"===== filter=\$FILTER prompt=\$PSTYLE finished \$(date) =====\"
  done
done
" > "$LOG" 2>&1 &

PID=$!

echo ""
echo "Running in background, PID=$PID"
echo "  Watch progress:  tail -f $LOG"
echo "  Check status:    ps -p $PID"
echo "  Stop:            kill $PID"
