#!/usr/bin/env bash
# Destroys every Vast.ai instance recorded in pool.txt — single command to
# stop billing at the end of a sweep. Reads instance IDs from the
# "# instance=NN" suffix that deploy-ollama.sh appends to each URL.
#
# Safe to run multiple times: lines with already-destroyed instance IDs are
# ignored by `vastai destroy instance`. After a successful run, the pool.txt
# file is moved to pool.txt.bak so a later deploy-ollama.sh starts fresh
# rather than appending onto a stale list.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POOL_FILE="${POOL_FILE:-$SCRIPT_DIR/pool.txt}"

if [ ! -s "$POOL_FILE" ]; then
	echo "$POOL_FILE empty or missing — nothing to tear down."
	exit 0
fi

if ! command -v vastai >/dev/null 2>&1; then
	echo "Error: vastai CLI not found." >&2
	exit 1
fi

# Same env-pickup as deploy-ollama.sh — lets a fresh Codespace tear down a
# pool deployed from a different machine without manual `vastai set api-key`.
if [ -n "${VASTAI_API_KEY:-}" ] && [ ! -s "$HOME/.vast_api_key" ]; then
	vastai set api-key "$VASTAI_API_KEY" >/dev/null
	echo "vastai: persisted API key from VASTAI_API_KEY env to $HOME/.vast_api_key"
fi

while read -r line; do
	# Lines look like:  https://host:port # instance=12345
	id="$(echo "$line" | sed -n 's/.*instance=\([0-9]\+\).*/\1/p')"
	if [ -z "$id" ]; then
		echo "skip: cannot parse instance id from: $line" >&2
		continue
	fi
	echo "destroying instance $id..."
	vastai destroy instance "$id" || echo "  (already gone or destroy failed for $id)" >&2
done < "$POOL_FILE"

mv "$POOL_FILE" "${POOL_FILE}.bak.$(date +%s)"
echo "done. moved $POOL_FILE aside."
