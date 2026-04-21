#!/usr/bin/env bash
# cis-ollama diagnostic: reachability + hosted models + currently-loaded
# models (with VRAM and expires_at TTLs). Optional: ping a named model
# with a tiny prompt and report elapsed time — useful to distinguish
# "server unreachable" from "model queue saturated".
#
# Usage:
#   bash diag.sh                   # tags + ps
#   bash diag.sh gpt-oss:20b       # tags + ps + 10-token ping to gpt-oss:20b

set -eo pipefail

HOST="${OLLAMA_HOST:-https://cis-ollama.auth.ad.bgu.ac.il}"

echo "== Reachability =="
if curl -k -sf --max-time 10 "${HOST}/api/tags" > /dev/null; then
    echo "  ${HOST}  OK"
else
    echo "  ${HOST}  UNREACHABLE"
    echo "  Check BGU VPN if off-site; login node is always inside."
    exit 2
fi

echo
echo "== Hosted models (${HOST}/api/tags) =="
curl -k -s "${HOST}/api/tags" \
    | python3 -c "
import sys, json
models = json.load(sys.stdin).get('models', [])
for m in sorted(models, key=lambda x: x['name']):
    print(f\"  {m['name']}\")"

echo
echo "== Currently loaded in VRAM (${HOST}/api/ps) =="
curl -k -s "${HOST}/api/ps" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin).get('models', [])
if not data:
    print('  (none loaded)')
else:
    for m in data:
        vram = m.get('size_vram', 0) / 1e9
        print(f\"  {m['name']:28s} {vram:4.1f}GB  ttl={m.get('expires_at','?')}\")"

# Optional model ping
MODEL="${1:-}"
if [ -n "$MODEL" ]; then
    echo
    echo "== Ping ${MODEL} (10-token 'pong' reply, ≤120s) =="
    python3 - "$MODEL" "$HOST" <<'PY'
import json, ssl, sys, time, urllib.request
model, host = sys.argv[1], sys.argv[2]
payload = {"model": model,
           "messages": [{"role": "user", "content": "Reply: pong"}],
           "stream": False, "options": {"num_predict": 10}}
req = urllib.request.Request(
    f"{host}/api/chat",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=120) as r:
        data = json.loads(r.read())
    dt = time.time() - t0
    msg = data.get("message", {}).get("content", "")
    print(f"  {dt:5.1f}s  reply={msg!r}")
except Exception as e:
    print(f"  FAIL {time.time()-t0:.1f}s  {type(e).__name__}: {e}")
    sys.exit(3)
PY
fi
