#!/usr/bin/env bash
# Verifies a remote Ollama URL is reachable, the bearer token is accepted,
# and the configured roster is loaded. Run from the cluster login node BEFORE
# submitting any sbatch — this is the gate that catches the classic Vast
# failure mode (port not exposed externally, auth token mismatch, model not
# pulled). Cheap (one tiny chat() request per model).
#
# Usage:
#   bash cluster-experimenting/vast/smoke-test.sh <url>
#   bash cluster-experimenting/vast/smoke-test.sh https://1.2.3.4:54321
#   # No arg: checks every URL in pool.txt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POOL_FILE="${POOL_FILE:-$SCRIPT_DIR/pool.txt}"
TOKEN_FILE="${TOKEN_FILE:-$SCRIPT_DIR/.token}"

if [ ! -s "$TOKEN_FILE" ]; then
	echo "Error: $TOKEN_FILE missing. Run vast/deploy-ollama.sh first." >&2
	exit 1
fi
TOKEN="$(cat "$TOKEN_FILE")"

URLS=()
if [ "$#" -gt 0 ]; then
	URLS=("$@")
elif [ -s "$POOL_FILE" ]; then
	while read -r line; do
		# pool.txt entries look like "https://host:port # instance=NN".
		# `read` with a discard rest-arg trims whitespace and drops the
		# instance suffix in one shot.
		read -r url _ <<< "${line%%#*}"
		[ -n "$url" ] && URLS+=("$url")
	done < "$POOL_FILE"
else
	echo "Error: no URL arg and $POOL_FILE empty." >&2
	exit 1
fi

# Caddy uses self-signed TLS (Caddyfile.tmpl: 'tls internal'). Skip cert
# verification — the bearer token is what gates access, not the cert. If you
# want a public-CA cert, swap 'tls internal' for an automatic-HTTPS line in
# Caddyfile.tmpl with a domain you control.
CURL=(curl -sSk --max-time 30 -H "Authorization: Bearer $TOKEN")

OVERALL=0
for URL in "${URLS[@]}"; do
	echo "=== $URL ==="

	# 1. /api/tags — basic reachability + auth check.
	if ! TAGS="$("${CURL[@]}" "$URL/api/tags")"; then
		echo "  FAIL: /api/tags unreachable" >&2
		OVERALL=1
		continue
	fi
	if ! echo "$TAGS" | python3 -c "import sys, json; json.loads(sys.stdin.read())" >/dev/null 2>&1; then
		echo "  FAIL: /api/tags returned non-JSON (auth probably rejected). Got:" >&2
		echo "$TAGS" | head -c 200 >&2; echo >&2
		OVERALL=1
		continue
	fi

	MODELS_JSON="$(echo "$TAGS" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
for m in d.get('models', []):
    print(m['name'])")"
	if [ -z "$MODELS_JSON" ]; then
		echo "  WARN: no models loaded yet — preload may still be running. Tail /var/log/preload.log on the box." >&2
	else
		echo "  models present:"
		echo "$MODELS_JSON" | sed 's/^/    /'
	fi

	# 2. tiny chat() against the smallest expected model — confirms the
	#    request path actually works, not just /api/tags.
	PROBE_MODEL="${PROBE_MODEL:-Qwen3.5:0.8B}"
	if echo "$MODELS_JSON" | grep -qx "$PROBE_MODEL"; then
		REPLY="$("${CURL[@]}" --max-time 60 "$URL/api/chat" \
			-H "Content-Type: application/json" \
			-d "{\"model\":\"$PROBE_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply ok\"}],\"stream\":false,\"options\":{\"num_predict\":4}}" \
			|| echo '{"error":"curl-failed"}')"
		if echo "$REPLY" | python3 -c "import sys, json; d=json.loads(sys.stdin.read()); assert 'message' in d, d" >/dev/null 2>&1; then
			echo "  OK: chat() returned a message"
		else
			echo "  FAIL: chat() did not return a message. Got:" >&2
			echo "$REPLY" | head -c 400 >&2; echo >&2
			OVERALL=1
		fi
	else
		echo "  SKIP: probe model $PROBE_MODEL not in roster, can't run chat() test"
	fi
done

if [ "$OVERALL" -ne 0 ]; then
	echo
	echo "smoke-test FAILED on at least one URL — DO NOT submit sbatch jobs yet." >&2
	exit "$OVERALL"
fi
echo
echo "smoke-test passed for all ${#URLS[@]} URL(s)."
