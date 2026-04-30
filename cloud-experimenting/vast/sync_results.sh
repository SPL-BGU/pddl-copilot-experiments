#!/usr/bin/env bash
# Idempotent rsync of results from a Vast instance to local
# results/vast-<instance-id>/. Safe to run mid-flight; called by run_smoke.sh
# in a polling loop and at teardown. Standalone-safe — pass instance_id.
#
# Usage:
#   bash sync_results.sh <instance-id>
#   bash sync_results.sh                 # uses INSTANCE_ID env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

INSTANCE_ID="${1:-${INSTANCE_ID:-}}"
[ -n "$INSTANCE_ID" ] || { echo "ERROR: instance id required (positional or INSTANCE_ID env)" >&2; exit 2; }

# Look up SSH details from the most recent run state file, or query Vast.
STATE_DIR="$SCRIPT_DIR/logs"
STATE_FILE=$(grep -l "^INSTANCE_ID=$INSTANCE_ID$" "$STATE_DIR"/*/instance.env 2>/dev/null | head -1 || true)

if [ -n "$STATE_FILE" ]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
else
    # Fallback: query Vast for SSH host/port
    JSON=$(vastai show instance "$INSTANCE_ID" --raw 2>/dev/null)
    SSH_HOST=$(echo "$JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh_host',''))")
    SSH_PORT=$(echo "$JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ssh_port',''))")
fi

[ -n "${SSH_HOST:-}" ] && [ -n "${SSH_PORT:-}" ] || {
    echo "WARN: could not resolve SSH host/port for $INSTANCE_ID; skipping sync" >&2
    exit 0
}

DEST="$REPO_ROOT/results/vast-$INSTANCE_ID"
mkdir -p "$DEST"

# --partial keeps half-transferred files; -a preserves; --delete left OFF
# so a transient missing-file on the source doesn't wipe local results.
rsync -az --partial \
    -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p $SSH_PORT" \
    "root@$SSH_HOST:/workspace/pddl-copilot-experiments/results/" \
    "$DEST/" \
    2>&1 | tail -20 || {
        echo "WARN: rsync failed (instance may be terminating)" >&2
        exit 0
    }

# Also pull host_info.json if present
rsync -az \
    -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p $SSH_PORT" \
    "root@$SSH_HOST:/workspace/host_info.json" \
    "$DEST/host_info.json" \
    2>/dev/null || true

echo "Synced -> $DEST"
