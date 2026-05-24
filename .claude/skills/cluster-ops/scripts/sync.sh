#!/usr/bin/env bash
# rsync cluster results into a local subdir under results/.
# Never deletes anything remotely. If you want to delete cancelled-job
# .out files, do it in a separate explicit ssh call after confirming IDs
# with the user.
#
# Scope: only `slurm_vllm_*/` cells (active vLLM-era sweep matrix) + any
# `smoke/probe_*/` artefacts. Pre-vLLM legacy `slurm_<model>_<think>_<cond>/`
# dirs on the cluster are intentionally skipped so the local results/ tree
# stays scoped to the in-flight sweep. Each invocation lands in its own
# dated subdir under results/ (default `sweep5-cluster-YYYYMMDD`) so
# checkpoints don't pollute the top level.
#
# Usage:
#   bash sync.sh                          # → results/sweep5-cluster-YYYYMMDD/
#   bash sync.sh results/my-run           # → explicit path
#
# Env overrides:
#   REMOTE_USER (default omereliy), REMOTE_HOST (default slurm.bgu.ac.il)
#   REMOTE_RESULTS (default ~/pddl-copilot-experiments/results)

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

REMOTE_USER="${REMOTE_USER:-omereliy}"
REMOTE_HOST="${REMOTE_HOST:-slurm.bgu.ac.il}"
REMOTE_RESULTS="${REMOTE_RESULTS:-~/pddl-copilot-experiments/results}"

DEST="${1:-$REPO_ROOT/results/sweep5-cluster-$(date +%Y%m%d)}"

# Refuse to dump slurm_* dirs flat into results/ — every sync must land in a
# named subdir so different sweeps stay separable. The default already does
# this; the guard catches an explicit `bash sync.sh results/` or `bash
# sync.sh $REPO_ROOT/results`. Pre-create the parent so `cd` resolves for
# fresh nested DESTs (preserving the original `mkdir -p "$DEST"` semantics).
mkdir -p "$(dirname "$DEST")"
DEST_ABS="$(cd "$(dirname "$DEST")" && pwd)/$(basename "$DEST")"
if [ "$DEST_ABS" = "$REPO_ROOT/results" ]; then
    echo "ERROR: refusing to sync into bare results/ — pass a subdir like results/cluster-DATE" >&2
    exit 2
fi

mkdir -p "$DEST"

echo "Syncing ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_RESULTS}/{slurm_vllm_*, smoke/probe_*} → $DEST"

# Active sweep matrix lives in `slurm_vllm_<model>_<think>_<cond>/` (post
# 2026-05-23 backend unification). Pre-vLLM `slurm_<model>_<think>_<cond>/`
# legacy corpora are explicitly skipped — they're drift-anchors held on the
# cluster for retrospective comparison, not part of the in-flight sweep
# checkpoint. To pull them anyway, pass an explicit DEST and run a separate
# `rsync` outside this script.
before_slurm=$(find "$DEST" -maxdepth 1 -type d -name 'slurm_vllm_*' 2>/dev/null | wc -l | tr -d ' ')
before_probe=$(find "$DEST" -maxdepth 1 -type d -name 'probe_*' 2>/dev/null | wc -l | tr -d ' ')

# --update: only copy when the source is newer; --info=stats2 gives us a compact summary
rsync -av --update "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_RESULTS}/slurm_vllm_*" "$DEST/" 2>&1 \
    | tail -5

# Probe outputs (one-off vLLM/smoke sbatches). Often empty on a fresh cluster
# or between probes — `|| true` so a no-match doesn't fail the whole sync.
# The dir-count diagnostic below reports whatever actually arrived.
echo "---"
rsync -av --update "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_RESULTS}/smoke/probe_*" "$DEST/" 2>&1 \
    | tail -5 || true

after_slurm=$(find "$DEST" -maxdepth 1 -type d -name 'slurm_vllm_*' 2>/dev/null | wc -l | tr -d ' ')
after_probe=$(find "$DEST" -maxdepth 1 -type d -name 'probe_*' 2>/dev/null | wc -l | tr -d ' ')

echo "---"
echo "Sweep cells:   before=${before_slurm} → after=${after_slurm} (+$((after_slurm - before_slurm)) new)"
echo "Probe outputs: before=${before_probe} → after=${after_probe} (+$((after_probe - before_probe)) new)"
echo "Local path: $DEST"
