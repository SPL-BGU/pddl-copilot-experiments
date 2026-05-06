#!/usr/bin/env bash
# Pulls the active model roster on the Vast.ai box and warms each one
# (so first real chat() request from the cluster doesn't pay the model-load
# tax). Runs ON the Vast box as part of the on-start command in
# deploy-ollama.sh — NOT on the cluster.
#
# Reads the roster from MODELS env (space-separated). Defaults to the
# 4-model pack used by --all in submit_with_rtx.sh / submit_with_remote.sh.

set -euo pipefail

MODELS="${MODELS:-Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b}"
OLLAMA_LOCAL="${OLLAMA_LOCAL:-http://127.0.0.1:11434}"

echo "preload: waiting for ollama on $OLLAMA_LOCAL..."
for i in $(seq 1 90); do
	if curl -sf "$OLLAMA_LOCAL/" >/dev/null 2>&1; then
		echo "preload: ollama up after ${i}s"
		break
	fi
	sleep 1
done

for m in $MODELS; do
	echo "preload: pulling $m..."
	t0=$EPOCHREALTIME
	curl -sf "$OLLAMA_LOCAL/api/pull" \
		-H "Content-Type: application/json" \
		-d "{\"name\":\"$m\",\"stream\":false}" \
		>/dev/null
	t1=$EPOCHREALTIME
	awk -v m="$m" "BEGIN{printf \"preload: pulled %s in %.1fs\n\", m, $t1-$t0}"

	echo "preload: warming $m (load weights into VRAM)..."
	curl -sf --max-time 600 "$OLLAMA_LOCAL/api/chat" \
		-H "Content-Type: application/json" \
		-d "{\"model\":\"$m\",\"messages\":[{\"role\":\"user\",\"content\":\"ok\"}],\"stream\":false,\"keep_alive\":\"24h\",\"options\":{\"num_predict\":4,\"num_ctx\":4096}}" \
		>/dev/null
done

echo "preload: done. /api/tags:"
curl -sf "$OLLAMA_LOCAL/api/tags" | head -c 1024
echo
