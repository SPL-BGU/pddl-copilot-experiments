#!/usr/bin/env bash
# Cluster preflight before `bash cluster-experimenting/submit_all.sh`.
#
# Updates that `setup_env.sh` deliberately skips because its `if [ -d .venv ]`
# guard avoids rebuilding existing venvs — great on first install, bad when a
# plugin bumps a pinned dependency (2026-04-21 `pddl-pyvalidator>=0.1.4` was
# silently stale in the plugin venv until we explicitly upgraded).
#
# Pulls both repos and refreshes the two plugin venvs. Confirms cis-ollama
# reachability at the end so a stale-network state fails fast instead of
# burning a wave.
#
# Usage:
#   bash preflight.sh            # interactive: show what would change, then apply
#   bash preflight.sh --yes      # non-interactive: apply without prompting
#
# Env overrides:
#   REMOTE_USER (default omereliy), REMOTE_HOST (default slurm.bgu.ac.il)

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
YES=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes|-y) YES=1; shift ;;
        -h|--help)
            sed -n '1,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" "$YES" <<'REMOTE'
set -eo pipefail
YES="$1"

EXPT="$HOME/pddl-copilot-experiments"
PLUG="$HOME/pddl-copilot"

echo "== git pull =="
for repo in "$EXPT" "$PLUG"; do
    echo "--- $repo"
    git -C "$repo" fetch --quiet origin
    before=$(git -C "$repo" rev-parse HEAD)
    git -C "$repo" pull --ff-only --quiet
    after=$(git -C "$repo" rev-parse HEAD)
    if [ "$before" = "$after" ]; then
        echo "    already up to date ($after)"
    else
        echo "    $before → $after"
        git -C "$repo" log --oneline "$before..$after"
    fi
done

echo
echo "== plugin venvs (pip install --upgrade -r requirements.txt) =="
for plugin in pddl-solver pddl-validator pddl-parser; do
    plug_dir="$PLUG/plugins/$plugin"
    venv="$plug_dir/.venv"
    if [ ! -d "$venv" ]; then
        echo "--- $plugin: .venv missing; run setup_env.sh first" >&2
        continue
    fi
    echo "--- $plugin"
    out=$("$venv/bin/pip" install --upgrade --quiet -r "$plug_dir/requirements.txt" 2>&1)
    if [ -n "$out" ]; then
        # pip is --quiet so output appears only if something actually changed
        echo "$out" | sed 's/^/    /'
    else
        echo "    already up to date"
    fi
done

echo
echo "== cis-ollama reachability =="
if curl -k -sf --max-time 10 https://cis-ollama.auth.ad.bgu.ac.il/api/tags > /dev/null; then
    echo "    OK"
else
    echo "    UNREACHABLE — abort before submitting a wave" >&2
    exit 2
fi

echo
echo "Preflight complete. Safe to run: bash cluster-experimenting/submit_all.sh --dry-run"
REMOTE
