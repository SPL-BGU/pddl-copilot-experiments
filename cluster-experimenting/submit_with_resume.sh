#!/usr/bin/env bash
# Submit the active 4-model sweep with backend split:
#   - Ollama: gemma4:31b + qwen3.6:35b (resumes from existing trials.jsonl
#     under results/slurm_<model>_<think>_<cond>/).
#   - vLLM:   qwen3.6:27b + Qwen3.5:0.8B (parser-verified on smokes
#     17461801 / 17468314 — see development/CHANGELOG.md 2026-05-10).
#     Fresh corpora under results/slurm_vllm_<model>_<think>_<cond>/.
#
# Backend split rationale (2026-05-11): rtx_pro_6000 pool is queue-saturated,
# so vLLM's 4.6× speedup is most valuable on the heavy Qwen cells that
# already have partial Ollama trials we cannot resume cross-backend (the
# resume key in pddl_eval/runner.py:424 includes the model string).
# gemma4:31b + qwen3.6:35b stay on Ollama because their Ollama corpora are
# 9/10 complete in local sync — moving them now would discard ~36K trials.
#
# Each call to submit_with_rtx.sh is independent: array fan-out, matrix
# gate, Nice auto-prioritization, and per-cell --time budgets are handled
# inside the wrapper. This script just sequences the two calls and surfaces
# both jobids.
#
# Usage:
#   bash cluster-experimenting/submit_with_resume.sh              # submit both
#   bash cluster-experimenting/submit_with_resume.sh --dry-run    # preview
#
# Any additional flags (--dry-run, --exclude, --no-auto-prioritize, ...)
# are passed through to both calls.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/defaults.sh
source "$SCRIPT_DIR/lib/defaults.sh"

# vLLM models come from the parser-verified roster in lib/defaults.sh —
# single source of truth shared with submit_with_rtx.sh and the sbatch
# vllm_lookup table. Ollama models are listed explicitly: they're the
# residual after the vLLM scope split (2026-05-11), driven by the 9/10
# already-complete cells in their slurm_<model>_* corpora.
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
