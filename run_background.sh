#!/bin/bash
# Run the PDDL copilot experiment in the background on macOS.
# Detached, low CPU priority, no-sleep — continues while you work.
#
# Usage:
#   ./run_background.sh                       # both models (full overnight run)
#   ./run_background.sh small                 # just qwen3:0.6b (lightweight daytime run)
#   ./run_background.sh large                 # just qwen3:4b (heavier, overnight)
#   ./run_background.sh small-nothink         # qwen3:0.6b with --think off (ablation)
#   ./run_background.sh large-nothink         # qwen3:4b with --think off (ablation)
#   ./run_background.sh partial               # fast feedback slice (--partial 2,
#                                             # all domains, both models, single-task;
#                                             # output → results/partial/)
#   ./run_background.sh continue-partial PATH # full sweep that inherits PATH/trials.jsonl
#                                             # from a partial run; output → results/full/

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

# Local-only laptop driver. Cluster runs go through
# cluster-experimenting/submit_with_rtx.sh, which uses the self-deployed
# Apptainer Ollama on a single GPU node — no shared server.

# Ensure Ollama serves concurrent chat requests instead of queueing them.
# Must be >= the --concurrency flag passed to run_experiment.py (default 4).
# Exported BEFORE the autostart below so a server we start here inherits it.
# Note: if an ollama serve was already running when this script launched, it
# won't pick up this var — restart it (or set the var in its environment).
export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-4}"

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

THINK_ARGS=()
PARTIAL_ARGS=()
CONTINUE_PARTIAL_ARG=""
BUCKET="full"
case "${1:-both}" in
    small)         MODELS=(qwen3:0.6b);          TAG="qwen06b" ;;
    large)         MODELS=(qwen3:4b);            TAG="qwen4b" ;;
    both)          MODELS=(qwen3:0.6b qwen3:4b); TAG="full" ;;
    small-nothink) MODELS=(qwen3:0.6b);          TAG="qwen06b_nothink"
                   THINK_ARGS=(--think off) ;;
    large-nothink) MODELS=(qwen3:4b);            TAG="qwen4b_nothink"
                   THINK_ARGS=(--think off) ;;
    partial)       MODELS=(qwen3:0.6b qwen3:4b); TAG="partial2"
                   PARTIAL_ARGS=(--partial 2)
                   BUCKET="partial" ;;
    continue-partial)
                   if [ -z "${2:-}" ]; then
                       echo "Usage: $0 continue-partial <path-to-partial-results-dir>" >&2
                       exit 1
                   fi
                   if [ ! -f "${2}/trials.jsonl" ]; then
                       echo "Error: ${2}/trials.jsonl not found" >&2
                       exit 1
                   fi
                   MODELS=(qwen3:0.6b qwen3:4b); TAG="continue"
                   CONTINUE_PARTIAL_ARG="$2" ;;
    *) echo "Usage: $0 [small|large|both|small-nothink|large-nothink|partial|continue-partial PATH]"; exit 1 ;;
esac

# Ensure requested models are available — pull from ollama.com if missing.
for m in "${MODELS[@]}"; do
    if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$m"; then
        echo "Pulling $m..."
        ollama pull "$m" || { echo "Error: failed to pull $m"; exit 1; }
    fi
done

STAMP=$(date +%Y%m%d_%H%M%S)
LOG="run_${TAG}_${STAMP}.log"
OUT_PREFIX="results/${BUCKET}/${TAG}_${STAMP}"
FILTERS="per-task all"
# `guided` retired 2026-04-27 (see run_experiment.py PROMPT_STYLE_CHOICES).
# Re-enable by adding "guided" back here AND in PROMPT_STYLE_CHOICES.
PROMPT_STYLES="minimal"

# `--continue-partial` is only meaningful for full sweeps that inherit a
# partial run's trials.jsonl; tag mode == "continue" passes it once per
# inner invocation so the resume key transfers across all (filter,prompt)
# cells that match the partial run's meta-dimensions.
CONTINUE_ARGS=()
if [ -n "$CONTINUE_PARTIAL_ARG" ]; then
    CONTINUE_ARGS=(--continue-partial "$CONTINUE_PARTIAL_ARG")
fi

echo "Starting PDDL copilot experiment..."
echo "  Models:      ${MODELS[*]}"
echo "  Host:        localhost (default)"
echo "  Marketplace: $MARKETPLACE_PATH"
echo "  Filters:     $FILTERS (run sequentially)"
echo "  Prompts:     $PROMPT_STYLES (run sequentially)"
echo "  Think:       ${THINK_ARGS[*]:-default}"
echo "  Partial:     ${PARTIAL_ARGS[*]:-off}"
echo "  Continue:    ${CONTINUE_PARTIAL_ARG:-(none)}"
echo "  Output dirs: ${OUT_PREFIX}_no-tools/ + ${OUT_PREFIX}_tools_{filter}_{prompt}/"
echo "  Log file:    $LOG"

INNER_SCRIPT=$(cat <<EOF
cd "$SCRIPT_DIR"
# No-tools condition is invariant under tool_filter and prompt_style (filter
# only gates with-tools tool exposure; style only edits WITH_TOOLS_SYSTEM).
# Running it once up front avoids the 4x redundant no-tools pass the old
# (FILTER, PSTYLE) loop produced — ISS-004.
echo "===== conditions=no-tools started \$(date) ====="
nice -n 19 python3 run_experiment.py --marketplace-path "$MARKETPLACE_PATH" --models ${MODELS[*]} --conditions no-tools ${THINK_ARGS[*]} ${PARTIAL_ARGS[*]} ${CONTINUE_ARGS[*]} --output-dir "${OUT_PREFIX}_no-tools"
echo "===== conditions=no-tools finished \$(date) ====="
for FILTER in $FILTERS; do
  for PSTYLE in $PROMPT_STYLES; do
    echo "===== conditions=tools filter=\$FILTER prompt=\$PSTYLE started \$(date) ====="
    nice -n 19 python3 run_experiment.py --marketplace-path "$MARKETPLACE_PATH" --models ${MODELS[*]} --conditions tools --tool-filter "\$FILTER" --prompt-style "\$PSTYLE" ${THINK_ARGS[*]} ${PARTIAL_ARGS[*]} ${CONTINUE_ARGS[*]} --output-dir "${OUT_PREFIX}_tools_\${FILTER}_\${PSTYLE}"
    echo "===== conditions=tools filter=\$FILTER prompt=\$PSTYLE finished \$(date) ====="
  done
done
EOF
)

# Run in a new session so the whole tree shares one PGID (== the leader's PID).
# That lets `kill -TERM -- -$PID` reach bash + run_experiment.py + MCP servers
# in one shot. macOS lacks util-linux `setsid`, so we use Python as a portable
# shim: os.setsid() then execvp hands off to caffeinate with the same PID.
nohup python3 -c '
import os, sys
os.setsid()
os.execvp("caffeinate", ["caffeinate", "-i", "bash", "-c", sys.argv[1]])
' "$INNER_SCRIPT" > "$LOG" 2>&1 &

PID=$!

echo ""
echo "Running in background, PGID=$PID"
echo "  Watch progress:  tail -f $LOG"
echo "  Check status:    ps -p $PID"
echo "  Stop:            kill -TERM -- -$PID   # negative = whole process group"
