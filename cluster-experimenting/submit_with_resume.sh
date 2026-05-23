#!/usr/bin/env bash
# Sequence the active sweep across backends. Post 2026-05-18: the entire
# PDDL_DEFAULT_MODELS roster runs on vLLM (gemma4:31b dense → gemma4:26b-a4b
# MoE swap retired the Ollama half), so this orchestrator collapses to a
# single vLLM submission. OLLAMA_MODELS is left empty as the extension
# point: appending a tag here re-enables the Ollama branch without
# touching the vLLM submission below. Pass-through args (e.g. --dry-run)
# go to whichever submission(s) actually fire. Rationale and operator
# docs in README.md.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

# vLLM roster comes from lib/defaults.sh (single source of truth).
# Ollama roster is empty post 2026-05-18 backend unification.
OLLAMA_MODELS=()
VLLM_MODELS=("${PDDL_VLLM_VERIFIED_MODELS[@]}")

ollama_jid=""
if [ "${#OLLAMA_MODELS[@]}" -gt 0 ]; then
    echo "=== Ollama submission: ${OLLAMA_MODELS[*]} (resume existing trials.jsonl) ==="
    ollama_jid=$(bash "$SCRIPT_DIR/submit_with_rtx.sh" "${OLLAMA_MODELS[@]}" "$@") || {
        echo "Error: Ollama submission failed" >&2
        exit 1
    }
    echo
fi

echo "=== vLLM submission: ${VLLM_MODELS[*]} (fresh slurm_vllm_ corpora) ==="
vllm_jid=$(bash "$SCRIPT_DIR/submit_with_rtx.sh" "${VLLM_MODELS[@]}" --backend vllm "$@") || {
    echo "Error: vLLM submission failed" >&2
    exit 1
}

echo
echo "=== submit_with_resume.sh summary ==="
[ -n "$ollama_jid" ] && echo "  Ollama jobid: $ollama_jid"
echo "  vLLM   jobid: $vllm_jid"
echo
echo "Monitor:"
if [ -n "$ollama_jid" ]; then
    echo "  squeue -j ${ollama_jid},${vllm_jid}"
else
    echo "  squeue -j ${vllm_jid}"
fi
echo "  bash .claude/skills/cluster-ops/scripts/status.sh"
