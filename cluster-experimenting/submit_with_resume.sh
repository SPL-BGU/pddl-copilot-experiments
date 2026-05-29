#!/usr/bin/env bash
# Submit the active vLLM sweep across the verified model roster. Pass-through
# args (e.g. --dry-run) go straight to submit_with_rtx.sh. Rationale and
# operator docs in README.md.
#
# History: pre-2026-05-18 this orchestrator sequenced an Ollama + vLLM
# submission pair; the Ollama backend was retired and the script collapsed
# to a single vLLM submission.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

# vLLM roster comes from lib/defaults.sh (single source of truth).
VLLM_MODELS=("${PDDL_VLLM_VERIFIED_MODELS[@]}")

echo "=== vLLM submission: ${VLLM_MODELS[*]} ==="
vllm_jid=$(bash "$SCRIPT_DIR/submit_with_rtx.sh" "${VLLM_MODELS[@]}" "$@") || {
    echo "Error: vLLM submission failed" >&2
    exit 1
}

echo
echo "=== submit_with_resume.sh summary ==="
echo "  vLLM jobid: $vllm_jid"
echo
echo "Monitor:"
echo "  squeue -j ${vllm_jid}"
echo "  bash .claude/skills/cluster-ops/scripts/status.sh"
