#!/usr/bin/env bash
# Top-level orchestrator (LAPTOP). Launches a Vast.ai instance, bootstraps
# it, runs run_experiment.py --smoke inside tmux, syncs results periodically,
# and tears the instance down. EXIT trap guarantees teardown unless --keep.
#
# Usage:
#   bash run_smoke.sh [--dry-run] [--keep] [--models "m1 m2 ..."]
#
# Cost (default 4-pack on H100 NVL 80GB ~$2.0/h, our highest GPU_PRIORITY
# tier with `dph_total<=2.5`): ~$3 / 90 min smoke. Falls back through
# A100 80GB and Ampere when no H100 offers exist.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────
DEFAULT_MODELS="Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b"

# 48GB+ GPU, single-GPU, reliability ≥0.99, dph_total ceiling, CUDA 12+.
# direct_port_count>=1 enforces direct-SSH availability; without it Vast
# falls back to the sshN.vast.ai proxy which silently wedged 4/4 attempts
# on 2026-04-30 (instance reported `running` but proxy port never opened).
# disk_space>=150 — `--disk N` is silently capped at the host's free disk;
# 4-model smoke needs ~67GB weights + ~10GB image/deps + ~24GB transient
# 'partial' blob during pulls. The 2026-04-30 attempt failed at the third
# model with 'no space left on device' on a 47GB host. Filtering at >=150
# eliminates H100 NVL (small on-host SSDs) and lands on A100 SXM4 ~$0.91/h
# with 1TB disk, or RTX A6000 ~$0.37/h with 500GB.
# dph_total raised to <=2.5 to admit H100-class hosts (~$1.76/h) when their
# disk is sufficient.
# Dropped vs. initial scaffold: datacenter=true (Vast field is null/missing
# on most hosts; filter zeros out), inet_down/up thresholds (excluded too
# many cheap reliable boxes for a 5GB weights pull).
OFFER_FILTER='gpu_ram>=46 num_gpus=1 dph_total<=2.5 reliability>=0.99 cuda_max_good>=12.0 direct_port_count>=1 disk_space>=150'

# GPU PRIORITY (highest tier first). The selection logic walks this list and
# picks the cheapest offer in the highest-available tier — i.e., prefer
# H100 NVL (Hopper, ~3-4× per-call vs Ampere); fall back through A100 80GB
# (HBM2e, ~2×) to A6000 (Ampere GDDR6, baseline) only if no H100/A100
# offers exist. Excluded everywhere: Q RTX 8000 (Turing), RTX 4090
# (consumer 24GB; 48GB listings are non-standard configs).
GPU_PRIORITY="H100 NVL|H100 SXM5|H100 PCIE|A100 SXM4|A100 PCIE|A100X|RTX A6000|A40|RTX 6000Ada|L40|L40S"

# Vast `--ssh` launch mode INJECTS sshd into the container and overrides
# the image's ENTRYPOINT (per docs.vast.ai/instances/launch-modes). The
# image must therefore be sshd-injection-compatible — `ollama/ollama` is
# not (no sshd binary, custom ENTRYPOINT). On 2026-04-30 that mismatch
# wedged 4/4 instances at the SSH-wait step.
#
# `nvidia/cuda:*-runtime-ubuntu22.04` is the lightest standard Ubuntu base
# Vast injects cleanly; Ollama bundles its own CUDA runtime libs so we
# don't need cudnn-devel. Vast's docs example uses pytorch/pytorch but
# torch wheels are 2GB of dead weight here.
#
# Tag pinning is intentionally loose at the patch level; we capture the
# resolved digest indirectly via `nvidia-smi` + `ollama --version` lines
# in host_info.json.
DOCKER_IMAGE="nvidia/cuda:12.4.1-runtime-ubuntu22.04"
# Peak disk during 4-model smoke: ~10GB image+deps + ~67GB model weights +
# ~24GB transient 'partial' blob = ~100GB peak. Allocating 150GB gives
# 50GB headroom; OFFER_FILTER ensures the host actually has it free.
DISK_GB=150
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
# EXIT trap: armed BEFORE `vastai create` so a parse failure between
# instance-creation and the original arm-point can't leave a billable
# orphan. Trap reads $INSTANCE_ID by reference; if the create call fails
# before assignment, cleanup() is a no-op.
# ──────────────────────────────────────────────────────────────────────────
INSTANCE_ID=""

cleanup() {
    local rc=$?
    if [ -z "$INSTANCE_ID" ]; then
        log "EXIT trap (rc=$rc) — no INSTANCE_ID; if create succeeded, check https://cloud.vast.ai/instances/ for orphans"
        return
    fi
    log "EXIT trap (rc=$rc) — final sync ..."
    bash "$SCRIPT_DIR/sync_results.sh" "$INSTANCE_ID" || \
        log "WARN: final sync failed"
    if [ "$KEEP_INSTANCE" = "0" ]; then
        log "Destroying instance $INSTANCE_ID ..."
        vastai destroy instance -y "$INSTANCE_ID" 2>&1 | tee -a "$LOG" || \
            log "WARN: destroy command failed; verify at https://cloud.vast.ai/instances/"
    else
        log "KEEP: instance $INSTANCE_ID left running."
        log "      Tear down later with: bash $SCRIPT_DIR/teardown.sh $INSTANCE_ID"
    fi
}
trap cleanup EXIT

# ──────────────────────────────────────────────────────────────────────────
# Launch instance
# ──────────────────────────────────────────────────────────────────────────
log "Launching instance ..."
LAUNCH_RAW=$(vastai create instance "$OFFER_ID" \
    --image "$DOCKER_IMAGE" \
    --disk "$DISK_GB" \
    --ssh --direct \
    --raw)

INSTANCE_ID=$(echo "$LAUNCH_RAW" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('new_contract') or d.get('id') or '')
")
if [ -z "$INSTANCE_ID" ]; then
    log "ERROR: failed to parse instance id from create response"
    log "  Raw: $LAUNCH_RAW"
    log "  -> trap can't auto-destroy without an ID; check the Vast console manually"
    exit 1
fi
log "Instance ID: $INSTANCE_ID"
echo "INSTANCE_ID=$INSTANCE_ID" > "$LOCAL_LOGS/instance.env"

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
    # Heartbeat every 30s so log readers can distinguish "polling silently"
    # from "process died". Without this, this loop is invisible for up to
    # 10 min — easy to mistake for a hang and easy for an outer task wrapper
    # to kill the process unnoticed.
    if [ $((i % 3)) -eq 0 ]; then
        log "  still waiting (status=${STATUS:-?}, ${i}0s elapsed)"
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

# Wait for SSH to actually accept (separate from Vast's actual_status).
# Vast reports `running` once the container is up, but the in-container SSH
# daemon and the ssh1/2/etc.vast.ai proxy routing can lag by several minutes
# on busy hosts. Wait up to 10 min with progress logging.
log "Waiting for SSH to accept connections (up to 10 min) ..."
SSH_OK=0
SSH_MAX_ITERS=60          # 60 × 10s = 10 min total
for i in $(seq 1 $SSH_MAX_ITERS); do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
            -p "$SSH_PORT" "root@$SSH_HOST" 'echo ok' 2>/dev/null | grep -q ok; then
        SSH_OK=1; break
    fi
    # Log progress every 6 iterations (~60s) so the user knows we're alive
    if [ $((i % 6)) -eq 0 ]; then
        log "  still waiting for SSH ($((i*5))s elapsed; ${SSH_HOST}:${SSH_PORT})"
    fi
    sleep 5
done
if [ "$SSH_OK" != "1" ]; then
    log "ERROR: SSH never accepted in $((SSH_MAX_ITERS*5))s"
    log "Instance state at failure:"
    vastai show instance "$INSTANCE_ID" --raw 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    for k in ('actual_status','intended_status','status_msg','ssh_host','ssh_port','ssh_idx','machine_id','public_ipaddr'):
        print(f'    {k}: {d.get(k, \"?\")}')
except Exception as e:
    print(f'    (failed to parse instance state: {e})')
" | tee -a "$LOG"
    exit 1
fi
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
