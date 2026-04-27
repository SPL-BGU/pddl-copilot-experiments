#!/usr/bin/env bash
# Cluster preflight before `bash cluster-experimenting/submit_all.sh` or
# `bash cluster-experimenting/submit_with_rtx.sh <model>`.
#
# Updates that `setup_env.sh` deliberately skips because its `if [ -d .venv ]`
# guard avoids rebuilding existing venvs — great on first install, bad when a
# plugin bumps a pinned dependency (2026-04-21 `pddl-pyvalidator>=0.1.4` was
# silently stale in the plugin venv until we explicitly upgraded).
#
# Pulls both repos, refreshes the two plugin venvs, and surfaces GPU pool
# capacity for the rtx self-deploy partitions (`rtx6000`, `rtx_pro_6000`)
# so the next submit fails fast on stale code or missing capacity.
#
# Usage:
#   bash preflight.sh            # pulls repos, refreshes venvs, reports capacity
#
# Env overrides:
#   REMOTE_USER (default omereliy), REMOTE_HOST (default slurm.bgu.ac.il)

set -eo pipefail

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

ssh "${REMOTE_USER}@${REMOTE_HOST}" "bash -s" <<'REMOTE'
set -eo pipefail

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
for plugin in pddl-solver pddl-validator; do
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
echo "== GPU pool capacity =="
# rtx self-deploy submissions land on a partition matching the GPU type. The
# per-partition free count is what determines whether `submit_with_rtx.sh`
# queues immediately or sits in PENDING(Resources). We don't try to count
# allocatable GPUs per node — just nodes in idle/mix state, which is the
# relevant signal for one-GPU-per-job sbatches.
for part in rtx6000 rtx_pro_6000; do
    free=$(sinfo -h -p "$part" -t idle,mix -o '%n' 2>/dev/null | wc -l | tr -d ' ')
    total=$(sinfo -h -p "$part" -o '%n' 2>/dev/null | wc -l | tr -d ' ')
    printf "    %-14s  %s/%s nodes idle-or-mixed\n" "$part" "$free" "$total"
done

echo
echo "== sres (cluster utilization) =="
# The PDF (p10) recommends sres as the pre-submit decision tool. We grep the
# GPU UTILIZATION block — its 5-column header (6000 4090 3090 2080 1080)
# conflates rtx_6000 with rtx_pro_6000 under "6000", so trust the per-partition
# count above for routing decisions; this is just a one-glance saturation view.
sres_block=$(sres 2>/dev/null | sed -n '/GPU UTILIZATION/,/Available Resources/p' | sed '$d')
if [ -z "$sres_block" ]; then
    echo "    (sres GPU UTILIZATION section not found — output format may have changed)"
else
    printf '%s\n' "$sres_block" | sed 's/^/    /'
fi

echo
echo "Preflight complete. Safe to run: bash cluster-experimenting/submit_with_rtx.sh --all --dry-run"
REMOTE
