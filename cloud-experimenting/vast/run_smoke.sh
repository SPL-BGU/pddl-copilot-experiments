#!/usr/bin/env bash
# Top-level orchestrator (LAPTOP). Launches a Vast.ai instance, bootstraps
# it, runs run_experiment.py --smoke inside tmux, syncs results periodically,
# and tears the instance down. EXIT trap guarantees teardown unless --keep.
#
# Usage:
#   bash run_smoke.sh [--dry-run] [--keep] [--models "m1 m2 ..."]
#
# Cost (default 4-pack on datacenter L40S 48GB ~$0.55/h): ~$0.85 / 90 min.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────
DEFAULT_MODELS="Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b"

# 48GB+ GPU, single-GPU, reliability ≥0.99, dph_total ceiling, CUDA 12+.
# dph_total raised to <=2.5 to admit H100-class hosts (~$1.76/h).
# Dropped vs. initial scaffold: datacenter=true (Vast field is null/missing
# on most hosts; filter zeros out), inet_down/up thresholds (excluded too
# many cheap reliable boxes for a 5GB weights pull).
OFFER_FILTER='gpu_ram>=46 num_gpus=1 dph_total<=2.5 reliability>=0.99 cuda_max_good>=12.0'

# GPU PRIORITY (highest tier first). The selection logic walks this list and
# picks the cheapest offer in the highest-available tier — i.e., prefer
# H100 NVL (Hopper, ~3-4× per-call vs Ampere); fall back through A100 80GB
# (HBM2e, ~2×) to A6000 (Ampere GDDR6, baseline) only if no H100/A100
# offers exist. Excluded everywhere: Q RTX 8000 (Turing), RTX 4090
# (consumer 24GB; 48GB listings are non-standard configs).
GPU_PRIORITY="H100 NVL|H100 SXM5|H100 PCIE|A100 SXM4|A100 PCIE|A100X|RTX A6000|A40|RTX 6000Ada|L40|L40S"

DOCKER_IMAGE="ollama/ollama:latest"   # Vast tag pinning is brittle; we capture
                                      # `ollama --version` into host_info.json.
DISK_GB=100
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-smoke"
LOCAL_LOGS="$SCRIPT_DIR/logs/$RUN_ID"
mkdir -p "$LOCAL_LOGS"
LOG="$LOCAL_LOGS/run.log"

DRY_RUN=0
KEEP_INSTANCE=0
MODELS="$DEFAULT_MODELS"

# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --keep)    KEEP_INSTANCE=1; shift ;;
        --models)  MODELS="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,/^# Cost/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "Unknown arg: $1 (try --help)" >&2; exit 2 ;;
    esac
done

log() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG" >&2 ; }

# ──────────────────────────────────────────────────────────────────────────
# Pre-flight
# ──────────────────────────────────────────────────────────────────────────
command -v vastai >/dev/null \
    || { log "ERROR: vastai CLI not installed. Run: pip install vastai"; exit 1; }
[ -f "$HOME/.config/vastai/vast_api_key" ] || [ -f "$HOME/.vastai/api_key" ] \
    || { log "ERROR: no Vast API key. Run: vastai set api-key <KEY>"; exit 1; }
vastai show user >/dev/null \
    || { log "ERROR: vastai CLI cannot reach API (check key + network)"; exit 1; }
command -v python3 >/dev/null \
    || { log "ERROR: python3 not on PATH"; exit 1; }

BALANCE=$(vastai show user --raw 2>/dev/null | python3 -c \
    'import json,sys; d=json.load(sys.stdin); print(d.get("credit","0"))')
log "Vast balance: \$$BALANCE   Run ID: $RUN_ID"

# ──────────────────────────────────────────────────────────────────────────
# Find offer
# ──────────────────────────────────────────────────────────────────────────
log "Searching offers: $OFFER_FILTER"
OFFER_RAW=$(vastai search offers "$OFFER_FILTER" --raw 2>/dev/null)
[ -n "$OFFER_RAW" ] || { log "ERROR: vastai search offers returned nothing"; exit 1; }

read -r OFFER_ID DPH GPU < <(echo "$OFFER_RAW" | GPU_PRIORITY="$GPU_PRIORITY" python3 -c "
import json, os, sys
offers = json.load(sys.stdin)
if not offers:
    sys.exit('no offers')
priority = os.environ.get('GPU_PRIORITY','').split('|')
chosen = None
for tier in priority:
    in_tier = [o for o in offers if o.get('gpu_name','').strip() == tier]
    if in_tier:
        in_tier.sort(key=lambda x: x.get('dph_total', 1e9))
        chosen = in_tier[0]
        break
if chosen is None:
    sys.exit('no offers matched GPU priority list')
print(chosen['id'], f\"{chosen['dph_total']:.4f}\", chosen.get('gpu_name','?').replace(' ','_'))
")

ESTIMATED_COST=$(python3 -c "print(round($DPH * 1.5, 2))")
log "Selected offer $OFFER_ID — \$$DPH/h on ${GPU//_/ }    estimate \$$ESTIMATED_COST for ~90 min"

if [ "$DRY_RUN" = "1" ]; then
    log "DRY RUN: stopping before instance creation."
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────
# Launch instance
# ──────────────────────────────────────────────────────────────────────────
log "Launching instance ..."
LAUNCH_RAW=$(vastai create instance "$OFFER_ID" \
    --image "$DOCKER_IMAGE" \
    --disk "$DISK_GB" \
    --ssh \
    --raw)

INSTANCE_ID=$(echo "$LAUNCH_RAW" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('new_contract') or d.get('id') or '')
")
[ -n "$INSTANCE_ID" ] || { log "ERROR: failed to parse instance id from create response"; exit 1; }
log "Instance ID: $INSTANCE_ID"
echo "INSTANCE_ID=$INSTANCE_ID" > "$LOCAL_LOGS/instance.env"

# ──────────────────────────────────────────────────────────────────────────
# EXIT trap: always sync + (unless --keep) destroy.
# ──────────────────────────────────────────────────────────────────────────
cleanup() {
    local rc=$?
    log "EXIT trap (rc=$rc) — final sync ..."
    bash "$SCRIPT_DIR/sync_results.sh" "$INSTANCE_ID" || \
        log "WARN: final sync failed"
    if [ "$KEEP_INSTANCE" = "0" ]; then
        log "Destroying instance $INSTANCE_ID ..."
        # `vastai destroy instance` prompts for confirmation; pipe `y` so
        # the trap completes without leaving the box alive.
        echo y | vastai destroy instance "$INSTANCE_ID" 2>&1 | tee -a "$LOG" || \
            log "WARN: destroy command failed; verify at https://cloud.vast.ai/instances/"
    else
        log "KEEP: instance $INSTANCE_ID left running."
        log "      Tear down later with: bash $SCRIPT_DIR/teardown.sh $INSTANCE_ID"
    fi
}
trap cleanup EXIT

# ──────────────────────────────────────────────────────────────────────────
# Wait for instance to come up
# ──────────────────────────────────────────────────────────────────────────
log "Waiting for instance to reach running state (up to 10 min) ..."
SSH_HOST=""; SSH_PORT=""
for i in $(seq 1 60); do
    STATUS_RAW=$(vastai show instance "$INSTANCE_ID" --raw 2>/dev/null || echo '{}')
    read -r SSH_HOST SSH_PORT STATUS < <(echo "$STATUS_RAW" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('ssh_host',''), d.get('ssh_port',''), d.get('actual_status',''))
")
    if [ "$STATUS" = "running" ] && [ -n "$SSH_HOST" ] && [ -n "$SSH_PORT" ]; then
        log "Instance running at $SSH_HOST:$SSH_PORT (status=$STATUS)"
        break
    fi
    sleep 10
done
[ -n "$SSH_HOST" ] && [ -n "$SSH_PORT" ] || { log "ERROR: instance did not come up in 10 min"; exit 1; }

# Persist SSH details for sync_results.sh
cat >> "$LOCAL_LOGS/instance.env" <<EOF
SSH_HOST=$SSH_HOST
SSH_PORT=$SSH_PORT
GPU=$GPU
DPH=$DPH
RUN_ID=$RUN_ID
EOF

# Wait for SSH to actually accept
log "Waiting for SSH to accept connections ..."
SSH_OK=0
for i in $(seq 1 30); do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
            -p "$SSH_PORT" "root@$SSH_HOST" 'echo ok' 2>/dev/null | grep -q ok; then
        SSH_OK=1; break
    fi
    sleep 5
done
[ "$SSH_OK" = "1" ] || { log "ERROR: SSH never accepted in 150s"; exit 1; }
log "SSH OK."

# ──────────────────────────────────────────────────────────────────────────
# Push scripts + bootstrap
# ──────────────────────────────────────────────────────────────────────────
log "Pushing bootstrap.sh + run_on_instance.sh to /workspace/ ..."
ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" "root@$SSH_HOST" 'mkdir -p /workspace'
scp -o StrictHostKeyChecking=no -P "$SSH_PORT" \
    "$SCRIPT_DIR/bootstrap.sh" "$SCRIPT_DIR/run_on_instance.sh" \
    "root@$SSH_HOST:/workspace/"

log "Running bootstrap on instance (~10–15 min: apt + git clone + pip + ollama pull + warmup) ..."
ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" "root@$SSH_HOST" \
    "MODELS='$MODELS' bash /workspace/bootstrap.sh" 2>&1 | tee -a "$LOG"

log "Bootstrap complete. Launching smoke run in tmux ..."
ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" "root@$SSH_HOST" \
    "MODELS='$MODELS' RUN_ID='$RUN_ID' bash /workspace/run_on_instance.sh --smoke"

# ──────────────────────────────────────────────────────────────────────────
# Poll loop: incremental rsync every 5 min until tmux session ends.
# ──────────────────────────────────────────────────────────────────────────
log "Polling tmux for completion (sync every 5 min) ..."
START_TS=$(date -u +%s)
while true; do
    if ssh -o StrictHostKeyChecking=no -p "$SSH_PORT" "root@$SSH_HOST" \
            "tmux has-session -t exp-$RUN_ID 2>/dev/null"; then
        bash "$SCRIPT_DIR/sync_results.sh" "$INSTANCE_ID" >>"$LOG" 2>&1 || true
        ELAPSED=$(( $(date -u +%s) - START_TS ))
        ESTIMATED=$(python3 -c "print(round($DPH * $ELAPSED / 3600, 2))")
        log "Still running. Elapsed ${ELAPSED}s. Estimated cost so far: \$$ESTIMATED"
        sleep 300
    else
        log "tmux session ended."
        break
    fi
done

# ──────────────────────────────────────────────────────────────────────────
# Done — cleanup() trap handles final sync + destroy.
# ──────────────────────────────────────────────────────────────────────────
ELAPSED=$(( $(date -u +%s) - START_TS ))
TOTAL_EST=$(python3 -c "print(round($DPH * $ELAPSED / 3600, 2))")
log "Smoke complete. Total runtime ${ELAPSED}s, estimated cost \$$TOTAL_EST"
log "Results: $REPO_ROOT/results/vast-$INSTANCE_ID/"
