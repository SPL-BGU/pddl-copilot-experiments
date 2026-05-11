#!/usr/bin/env bash
# Sequence the active backend-split sweep: Ollama for gemma4:31b + qwen3.6:35b,
# vLLM for the parser-verified roster. Pass-through args (e.g. --dry-run) go
# to both submissions. Rationale and operator docs in README.md.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

# vLLM roster comes from lib/defaults.sh (single source of truth).
# Ollama roster is the residual after the vLLM scope split.
OLLAMA_MODELS=(gemma4:31b qwen3.6:35b)
VLLM_MODELS=("${PDDL_VLLM_VERIFIED_MODELS[@]}")

echo "=== Ollama submission: ${OLLAMA_MODELS[*]} (resume existing trials.jsonl) ==="
ollama_jid=$(bash "$SCRIPT_DIR/submit_with_rtx.sh" "${OLLAMA_MODELS[@]}" "$@") || {
    echo "Error: Ollama submission failed" >&2
    exit 1
}

echo
echo "=== vLLM submission: ${VLLM_MODELS[*]} (fresh slurm_vllm_ corpora) ==="
vllm_jid=$(bash "$SCRIPT_DIR/submit_with_rtx.sh" "${VLLM_MODELS[@]}" --backend vllm "$@") || {
    echo "Error: vLLM submission failed" >&2
    exit 1
}

echo
echo "=== submit_with_resume.sh summary ==="
echo "  Ollama jobid: $ollama_jid"
echo "  vLLM   jobid: $vllm_jid"
echo
echo "Monitor:"
echo "  squeue -j ${ollama_jid},${vllm_jid}"
echo "  bash .claude/skills/cluster-ops/scripts/status.sh"
