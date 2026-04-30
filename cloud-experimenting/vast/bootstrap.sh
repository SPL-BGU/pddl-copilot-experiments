#!/usr/bin/env bash
# Runs ON the Vast.ai instance. One-time setup:
#   apt deps -> git clone (this repo + pddl-copilot) -> venv + pip install
#   -> warm MCP plugin venvs -> ollama pull -> ollama serve -> arm 10h kill switch
# Re-running is idempotent (skips already-present steps where cheap).
#
# Inputs (env, set by run_smoke.sh):
#   MODELS         space-separated Ollama model names (default: paper 4-pack)
#   EXPT_BRANCH    pddl-copilot-experiments branch to clone (default: feat/vast-ai)
#   PDDL_BRANCH    pddl-copilot branch to clone (default: main)
#
# Outputs: /workspace/host_info.json, /workspace/pddl-copilot-experiments/
#          /workspace/pddl-copilot/, ollama serve on 127.0.0.1:11434.

set -euo pipefail

: "${MODELS:=Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b}"
: "${EXPT_BRANCH:=feat/vast-ai}"
: "${PDDL_BRANCH:=main}"

WORK=/workspace
EXPT_DIR=$WORK/pddl-copilot-experiments
PDDL_DIR=$WORK/pddl-copilot
mkdir -p "$WORK"
cd "$WORK"

log() { echo "[bootstrap $(date -u +%H:%M:%SZ)] $*"; }

# 1. System packages -------------------------------------------------------
if ! command -v python3.11 >/dev/null && ! python3 -c 'import sys; assert sys.version_info>=(3,11)' 2>/dev/null; then
    log "Installing system packages (apt) ..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y -qq
    apt-get install -y -qq --no-install-recommends \
        python3 python3-venv python3-pip \
        git curl rsync tmux ca-certificates zstd \
        openjdk-17-jre-headless build-essential \
        cmake g++ make
fi

# 1b. Ollama -- the new base image (nvidia/cuda runtime) doesn't bundle it.
# The official install script handles binary placement + systemd-style
# launcher; ~30s on cold boot.
if ! command -v ollama >/dev/null; then
    log "Installing ollama (curl https://ollama.com/install.sh | sh) ..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 2. Repos ---------------------------------------------------------------
if [ ! -d "$EXPT_DIR/.git" ]; then
    log "Cloning pddl-copilot-experiments@$EXPT_BRANCH ..."
    git clone --depth 1 --branch "$EXPT_BRANCH" \
        https://github.com/SPL-BGU/pddl-copilot-experiments.git "$EXPT_DIR"
fi
if [ ! -d "$PDDL_DIR/.git" ]; then
    log "Cloning pddl-copilot@$PDDL_BRANCH ..."
    git clone --depth 1 --branch "$PDDL_BRANCH" \
        https://github.com/SPL-BGU/pddl-copilot.git "$PDDL_DIR"
fi

# 3. Python venv + harness deps ------------------------------------------
if [ ! -d "$EXPT_DIR/.venv" ]; then
    log "Creating venv + installing requirements ..."
    python3 -m venv "$EXPT_DIR/.venv"
    "$EXPT_DIR/.venv/bin/pip" install --quiet --upgrade pip wheel
    "$EXPT_DIR/.venv/bin/pip" install --quiet -r "$EXPT_DIR/requirements.txt"
fi

# 4. Warm MCP plugin venvs ------------------------------------------------
# The launch script creates the plugin venv on first run; we just need the
# venv populated so the experiment doesn't pay the cost on the first MCP
# call. Solver-specific Fast Downward build still happens lazily on first
# `solve` (same as cluster cold-start behaviour).
for plugin in pddl-solver pddl-validator pddl-parser; do
    launcher="$PDDL_DIR/plugins/$plugin/scripts/launch-server.sh"
    venv="$PDDL_DIR/plugins/$plugin/.venv"
    [ -x "$launcher" ] || continue
    log "Warming $plugin venv ..."
    "$launcher" </dev/null >/tmp/$plugin.log 2>&1 &
    srv=$!
    # Poll for venv readiness up to 5 min (60 × 5s).
    for i in $(seq 1 60); do
        [ -d "$venv" ] && [ -f "$venv/pyvenv.cfg" ] && break
        sleep 5
    done
    if [ ! -f "$venv/pyvenv.cfg" ]; then
        log "WARN: $plugin venv not ready after 5min; first MCP call will pay setup cost."
    fi
    kill $srv 2>/dev/null || true
    wait $srv 2>/dev/null || true
done

# 5. Ollama pull weights -------------------------------------------------
# The Docker image's entrypoint usually starts `ollama serve` already; check
# and start one if not.
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    log "Starting ollama serve ..."
    OLLAMA_HOST=0.0.0.0:11434 \
    OLLAMA_NUM_PARALLEL=4 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_KEEP_ALIVE=1h \
        nohup ollama serve >/var/log/ollama.log 2>&1 &
    for i in $(seq 1 30); do
        sleep 2
        curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    done
fi
curl -sf http://127.0.0.1:11434/api/tags >/dev/null \
    || { log "ERROR: ollama serve did not come up"; exit 1; }

for model in $MODELS; do
    if ! ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$model"; then
        log "Pulling $model ..."
        ollama pull "$model"
    fi
done

# Warmup at full ctx so first real request doesn't trigger reload
# (matches cluster pattern in run_condition_rtx.sbatch)
for model in $MODELS; do
    log "Warmup $model at num_ctx=16384 ..."
    curl -sf -X POST http://127.0.0.1:11434/api/chat \
        -H 'Content-Type: application/json' \
        -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"1h\",\"options\":{\"num_predict\":5,\"num_ctx\":16384}}" \
        >/dev/null || log "WARN: warmup of $model failed (may need num_ctx tuning)"
done

# 6. Capture host metadata for reproducibility ---------------------------
log "Capturing host_info.json ..."
{
    echo '{'
    echo "  \"captured_at_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"hostname\": \"$(hostname)\","
    echo "  \"ollama_version\": \"$(ollama --version 2>&1 | head -1 | tr -d '\"')\","
    echo "  \"nvidia_smi\": $(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null | head -1 | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))'),"
    echo "  \"cuda\": $(nvcc --version 2>/dev/null | tail -1 | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' || echo '"unknown"'),"
    echo "  \"models\": ["
    first=1
    for model in $MODELS; do
        digest=$(ollama show --modelfile "$model" 2>/dev/null | grep -E '^FROM ' | head -1 | awk '{print $2}')
        [ -z "$digest" ] && digest="unknown"
        [ "$first" -eq 1 ] && first=0 || echo ","
        printf '    {"name": "%s", "from": "%s"}' "$model" "$digest"
    done
    echo
    echo '  ]'
    echo '}'
} > "$WORK/host_info.json"

# 7. 10h hard kill switch ------------------------------------------------
# Belt + suspenders alongside Vast's --auto-destroy and the laptop EXIT trap.
log "Arming shutdown -h +600 (10h kill switch) ..."
shutdown -h +600 "Vast demo 10h ceiling reached" >/dev/null 2>&1 || true

log "Bootstrap complete."
