#!/usr/bin/env bash
# Final results sync + Vast instance destroy. Used by run_smoke.sh's EXIT
# trap; standalone-safe if a previous run was killed and the instance is
# still alive.
#
# Usage:
#   bash teardown.sh <instance-id>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE_ID="${1:-${INSTANCE_ID:-}}"
[ -n "$INSTANCE_ID" ] || { echo "ERROR: instance id required" >&2; exit 2; }

echo "[teardown] Final result sync ..."
bash "$SCRIPT_DIR/sync_results.sh" "$INSTANCE_ID" || \
    echo "[teardown] WARN: final sync failed; check $SCRIPT_DIR/logs/" >&2

echo "[teardown] Destroying instance $INSTANCE_ID ..."
vastai destroy instance -y "$INSTANCE_ID" || {
    echo "[teardown] WARN: destroy command failed; check https://cloud.vast.ai/instances/" >&2
    exit 1
}

# Brief verify loop — Vast is async; show should report destroyed within ~30s.
for i in $(seq 1 6); do
    STATUS=$(vastai show instance "$INSTANCE_ID" --raw 2>/dev/null \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('actual_status','unknown'))" 2>/dev/null \
        || echo "gone")
    if [ "$STATUS" = "gone" ] || [ "$STATUS" = "exited" ] || [ "$STATUS" = "destroyed" ]; then
        echo "[teardown] Instance $INSTANCE_ID destroyed."
        exit 0
    fi
    sleep 5
done

echo "[teardown] WARN: instance $INSTANCE_ID still showing as alive after 30s."
echo "          Verify in console: https://cloud.vast.ai/instances/"
exit 1
