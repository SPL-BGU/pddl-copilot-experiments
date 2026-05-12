#!/bin/bash
### Submit the 4-model production sweep with per-model backend + GPU dispatch:
###
###   vLLM,   rtx_6000:1, 06:00:00 → Qwen3.5:0.8B               (small, fast cells)
###   vLLM,   rtx_6000:1, 48:00:00 → qwen3.6:27b + qwen3.6:35b  (heavy, packed array)
###   Ollama, rtx_pro_6000:1, 72h  → gemma4:31b                 (paper default)
###
### Three independent sbatch submissions. Each model lands on the GPU class
### and walltime that fits it, and the backend per model matches what's
### actually been verified (see lib/defaults.sh:PDDL_VLLM_VERIFIED_MODELS).
###
### Why this script exists:
###   * submit_with_rtx.sh accepts ONE backend per invocation, so a single
###     command can't mix vLLM + Ollama. This wrapper is the simplest
###     orchestration that gets the right tool to each model.
###   * The heavy-Qwen pack needs --time 48:00:00; the wrapper's hardcoded
###     06:00:00 vLLM tools ceiling silently TIMEOUTs 27B/35B (~19h
###     measured). The `--time` override in submit_with_rtx.sh is the fix.
###
### Prereqs:
###   * qwen3.6:35b parser verified via run_smoke_vllm_vs_ollama.sbatch
###     (post-edit on 2026-05-12; check sacct on the smoke job before
###     trusting this script's heavy-pack submission).
###   * Both backends are non-overlapping GPU classes (rtx_6000 vs
###     rtx_pro_6000), so the four sbatch jobs don't contend.
###
### Usage:
###   bash cluster-experimenting/submit_full_sweep.sh                        # tools matrix
###   bash cluster-experimenting/submit_full_sweep.sh --no-tools             # discriminative
###   bash cluster-experimenting/submit_full_sweep.sh --think-modes "off"    # only think=off
###   bash cluster-experimenting/submit_full_sweep.sh --dry-run              # preview, no submit
###
### Flags forwarded to all three submit_with_rtx.sh calls. `--all`, model
### names, and `--backend` are NOT forwarded (this script sets them).

set -e

HERE="$(cd "$(dirname "$0")" && pwd)"

# Filter out flags this orchestrator owns — the user shouldn't be able to
# break the dispatch by passing --all, model names, or --backend.
FORWARDED=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all|--smoke|--smoke-shuffle)
            echo "Error: $1 is not compatible with the full-sweep orchestrator." >&2
            echo "       Call submit_with_rtx.sh directly for smoke/all modes." >&2
            exit 1 ;;
        --backend)
            echo "Error: --backend is set per-model by this script." >&2
            exit 1 ;;
        --gpu-type)
            echo "Error: --gpu-type is set per-backend by this script." >&2
            exit 1 ;;
        --time)
            echo "Error: --time is set per-cell-class by this script." >&2
            exit 1 ;;
        -h|--help)
            sed -n '1,40p' "$0" | sed 's/^### \{0,1\}//'; exit 0 ;;
        *)
            FORWARDED+=("$1"); shift ;;
    esac
done

echo "==> [1/3] vLLM, rtx_6000:1, 06:00:00 — Qwen3.5:0.8B"
bash "$HERE/submit_with_rtx.sh" --backend vllm Qwen3.5:0.8B "${FORWARDED[@]}"

echo
echo "==> [2/3] vLLM, rtx_6000:1, 48:00:00 — qwen3.6:27b + qwen3.6:35b (packed array)"
bash "$HERE/submit_with_rtx.sh" --backend vllm --time 48:00:00 qwen3.6:27b qwen3.6:35b "${FORWARDED[@]}"

echo
echo "==> [3/3] Ollama, rtx_pro_6000:1, 72:00:00 — gemma4:31b"
bash "$HERE/submit_with_rtx.sh" --backend ollama gemma4:31b "${FORWARDED[@]}"

echo
echo "Full sweep submitted. Track via: bash .claude/skills/cluster-ops/scripts/status.sh"
