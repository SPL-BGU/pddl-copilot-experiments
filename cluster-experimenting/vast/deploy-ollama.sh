#!/usr/bin/env bash
# Provisions ONE Vast.ai instance running Ollama + a Caddy reverse-proxy
# that gates the API behind a bearer token. Appends the resulting public URL
# to vast/pool.txt and writes the shared bearer token to vast/.token (both
# gitignored). Run from the cluster login node or your laptop — anywhere with
# the `vastai` CLI installed and `vastai login` already done.
#
# Usage:
#   bash cluster-experimenting/vast/deploy-ollama.sh           # 1 box, default GPU filter
#   N=3 bash cluster-experimenting/vast/deploy-ollama.sh        # spin up 3 boxes
#   GPU_QUERY="gpu_name=H100 gpu_total_ram>=80" bash ...        # custom filter
#
# Before first run: `pip install vastai && vastai set api-key <YOUR_KEY>`
# (the user said they had a previous Vast deployment, so the CLI is presumed
# already configured).
#
# Why a pool: cluster jobs hit one URL each (slot = SLURM_ARRAY_TASK_ID % N),
# so the pool size should match the planned concurrent SLURM job count. See
# cluster-experimenting/run_condition_remote.sbatch for the slot-picker.
#
# Why pre-provision (vs. on-demand from the sbatch prologue): Vast scheduling
# can take 30-120s, and a SLURM job that's killed mid-run would orphan the
# rented box — i.e. you'd keep paying. Provisioning once per sweep and tearing
# down at the end with teardown-pool.sh is simpler to reason about.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POOL_FILE="${POOL_FILE:-$SCRIPT_DIR/pool.txt}"
TOKEN_FILE="${TOKEN_FILE:-$SCRIPT_DIR/.token}"

# Single source of truth for the active model roster lives in lib/defaults.sh
# (PDDL_DEFAULT_MODELS). Sourcing it here keeps the on-start preload list in
# lockstep with the rtx variant without manual triple-bookkeeping.
# shellcheck source=../lib/defaults.sh
source "$SCRIPT_DIR/../lib/defaults.sh"

N="${N:-1}"

# A100 80GB / H100 80GB co-resides 35B + 0.8b + one mid-class model without
# Ollama having to swap. The reliability+disk filters skip cheap boxes that
# cause "Ollama starts but model download stalls" failure modes.
# `direct_port_count>=1` is critical: Vast hosts without direct port mapping
# silently drop the `-p 8443:8443` request, so the on-start succeeds but the
# public endpoint is unreachable. Skipping those hosts up front prevents the
# 5-min poll-then-WARN failure mode in the create loop.
GPU_QUERY="${GPU_QUERY:-gpu_total_ram>=80 reliability>=0.95 disk_space>=100 inet_down>=200 direct_port_count>=1}"

# Image: official Ollama. The on-start script below installs Caddy on top.
IMAGE="${IMAGE:-ollama/ollama:latest}"

# Models the box should preload at boot. Default reuses the cluster-side
# 4-model roster (PDDL_DEFAULT_MODELS from lib/defaults.sh). Override via env.
MODELS="${MODELS:-${PDDL_DEFAULT_MODELS[*]}}"

if ! command -v vastai >/dev/null 2>&1; then
	echo "Error: vastai CLI not found. Install with 'pip install vastai' and 'vastai set api-key <KEY>'." >&2
	exit 1
fi

# Auto-pickup of VASTAI_API_KEY from env (e.g. GitHub Codespaces secret) into
# the CLI's persisted-key file. Only runs when the file isn't already populated
# so existing laptop setups (where `vastai set api-key` has been done by hand)
# are untouched. The CLI reads ~/.vast_api_key on every call; without this
# bridge a fresh Codespace would 401 on the first `vastai search offers`.
if [ -n "${VASTAI_API_KEY:-}" ] && [ ! -s "$HOME/.vast_api_key" ]; then
	vastai set api-key "$VASTAI_API_KEY" >/dev/null
	echo "vastai: persisted API key from VASTAI_API_KEY env to $HOME/.vast_api_key"
fi

# Generate a single shared bearer token for the whole pool (so cluster jobs
# only need one secret). Reused across re-runs of this script — first run
# creates it, later runs reuse it.
if [ ! -s "$TOKEN_FILE" ]; then
	umask 077
	openssl rand -hex 32 > "$TOKEN_FILE"
	echo "wrote new bearer token to $TOKEN_FILE"
fi
TOKEN="$(cat "$TOKEN_FILE")"

CADDYFILE_CONTENT="$(cat "$SCRIPT_DIR/Caddyfile.tmpl")"
PRELOAD_CONTENT="$(cat "$SCRIPT_DIR/preload-model.sh")"

# On-start script run inside the Vast container after Ollama is launched.
# Order matters:
#   1. Install Caddy (apt) and write Caddyfile + auth env.
#   2. Start Caddy (binds :8443, reverse-proxies 127.0.0.1:11434).
#   3. Pull and warm each model. Done last so the URL is reachable for
#      smoke-testing as soon as Caddy is up, even before all models are
#      loaded.
ONSTART="$(cat <<EOF
#!/usr/bin/env bash
set -euo pipefail

export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=3
export OLLAMA_KEEP_ALIVE=24h
export OLLAMA_CONTEXT_LENGTH=16384
export OLLAMA_AUTH_TOKEN='$TOKEN'

# Ollama is the container's default entrypoint; start it in the background.
nohup ollama serve > /var/log/ollama.log 2>&1 &

# Caddy install (Debian-based ollama/ollama image).
apt-get update -qq
apt-get install -y -qq curl gnupg
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
	| gpg --dearmor -o /usr/share/keyrings/caddy.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" \
	> /etc/apt/sources.list.d/caddy.list
apt-get update -qq
apt-get install -y -qq caddy

mkdir -p /etc/caddy
cat > /etc/caddy/Caddyfile <<'CADDYFILE_EOF'
$CADDYFILE_CONTENT
CADDYFILE_EOF

# Run Caddy in the background; bearer token comes from the env.
nohup caddy run --config /etc/caddy/Caddyfile --adapter caddyfile \
	> /var/log/caddy.log 2>&1 &

# Preload + warm models (does NOT block the proxy; runs after both servers
# are up, so /api/tags responds during the pull).
mkdir -p /opt/preload
cat > /opt/preload/preload.sh <<'PRELOAD_EOF'
$PRELOAD_CONTENT
PRELOAD_EOF
chmod +x /opt/preload/preload.sh
MODELS='$MODELS' /opt/preload/preload.sh > /var/log/preload.log 2>&1 &
EOF
)"

echo "Provisioning $N Vast box(es) with filter: $GPU_QUERY"

for i in $(seq 1 "$N"); do
	echo "[$i/$N] searching offers..."
	OFFER_ID="$(vastai search offers "$GPU_QUERY" -o 'dph+' --raw \
		| python3 -c "import sys, json; offers=json.load(sys.stdin); print(offers[0]['id']) if offers else sys.exit('no offers')")"
	echo "[$i/$N] cheapest offer: $OFFER_ID"

	# Expose port 8443 (Caddy public listener). Ollama on 11434 stays internal.
	CREATE_JSON="$(vastai create instance "$OFFER_ID" \
		--image "$IMAGE" \
		--disk 100 \
		--env "-p 8443:8443" \
		--onstart-cmd "$ONSTART" \
		--raw)"
	INSTANCE_ID="$(echo "$CREATE_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['new_contract'])")"
	echo "[$i/$N] created instance $INSTANCE_ID — waiting for it to come up..."

	# Poll until Vast reports the public IP+port mapping for 8443.
	URL=""
	for s in $(seq 1 60); do
		INFO="$(vastai show instance "$INSTANCE_ID" --raw)"
		HOST="$(echo "$INFO" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('public_ipaddr') or '')")"
		PORT="$(echo "$INFO" | python3 -c "import sys, json; d=json.load(sys.stdin); ports=d.get('ports') or {}; m=ports.get('8443/tcp') or []; print(m[0]['HostPort'] if m else '')")"
		if [ -n "$HOST" ] && [ -n "$PORT" ]; then
			URL="https://$HOST:$PORT"
			break
		fi
		sleep 5
	done
	if [ -z "$URL" ]; then
		echo "[$i/$N] WARN: instance $INSTANCE_ID did not surface a public 8443 mapping in 5min." >&2
		# Tear the orphan down so it doesn't keep billing. The instance was
		# created (line ~123) but never made it into pool.txt, so a later
		# teardown-pool.sh would not see it. Best-effort destroy + a clear
		# log line so the user can confirm in the Vast dashboard.
		echo "[$i/$N] destroying orphan instance $INSTANCE_ID to stop billing..." >&2
		vastai destroy instance "$INSTANCE_ID" >&2 || \
			echo "[$i/$N] WARN: vastai destroy failed for $INSTANCE_ID — verify manually with: vastai show instance $INSTANCE_ID" >&2
		continue
	fi

	# Record both the instance id (for teardown) and the URL (for the pool).
	echo "$URL # instance=$INSTANCE_ID" >> "$POOL_FILE"
	echo "[$i/$N] pool entry: $URL  (instance $INSTANCE_ID)"
done

echo
echo "Pool file: $POOL_FILE"
echo "Token file: $TOKEN_FILE"
echo
echo "Next: smoke-test before submitting any sbatch jobs."
echo "  bash cluster-experimenting/vast/smoke-test.sh \"\$(head -1 $POOL_FILE | awk '{print \$1}')\""
