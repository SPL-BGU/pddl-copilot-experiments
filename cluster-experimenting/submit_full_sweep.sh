#!/bin/bash
### Submit the production sweep across the active vLLM model roster:
###
###   rtx_6000:1, 12:00:00 → Qwen3.5:0.8B + 4B + 9B  (small/mid, packed)
###   rtx_6000:1, 48:00:00 → qwen3.6:35b             (heavy MoE)
###   rtx_6000:1, 48:00:00 → gemma4:26b-a4b          (MoE A4B; replaced
###                                                   the dense 31B model
###                                                   2026-05-18)
###
### Three independent sbatch submissions; each model lands on the walltime
### that fits it (see lib/defaults.sh:PDDL_VLLM_VERIFIED_MODELS).
###
### Why this script exists:
###   * The heavy-Qwen 35B MoE needs --time 48:00:00; the wrapper's hardcoded
###     06:00:00 tools ceiling silently TIMEOUTs it (~19h measured on the
###     prior 27B). The `--time` override in submit_with_rtx.sh is the fix.
###   * 4B/9B run far below the heavy walltime but well above 0.8B alone, so
###     the small/mid pack gets --time 12:00:00 as a safe ceiling.
###
### Prereqs:
###   * qwen3.6:35b parser verified via submit_with_rtx.sh --smoke (smoke
###     fastpath landed 2026-05-19, commit 4f50a5b; the 2026-05-12
###     verification ran the predecessor sbatch — check sacct on the smoke
###     job before trusting this script's heavy-pack submission).
###   * Qwen3.5:4B and Qwen3.5:9B parsers verified via the same smoke path
###     (2026-05-17 swap; same qwen3_xml parser as 0.8B but a
###     missing/mismatched parser silently produces 0% tool extraction, so
###     verify before the production sweep).
###
### Usage:
###   bash cluster-experimenting/submit_full_sweep.sh                        # tools matrix
###   bash cluster-experimenting/submit_full_sweep.sh --no-tools             # discriminative
###   bash cluster-experimenting/submit_full_sweep.sh --think-modes "off"    # only think=off
###   bash cluster-experimenting/submit_full_sweep.sh --dry-run              # preview, no submit
###
### Flags forwarded to all three submit_with_rtx.sh calls. `--all` and model
### names are NOT forwarded (this script sets them).

set -e

HERE="$(cd "$(dirname "$0")" && pwd)"

# Filter out flags this orchestrator owns — the user shouldn't be able to
# break the dispatch by passing --all or model names.
FORWARDED=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all|--smoke|--smoke-shuffle)
            echo "Error: $1 is not compatible with the full-sweep orchestrator." >&2
            echo "       Call submit_with_rtx.sh directly for smoke/all modes." >&2
            exit 1 ;;
        --gpu-type)
            echo "Error: --gpu-type is set per-backend by this script." >&2
            exit 1 ;;
        --time)
            echo "Error: --time is set per-cell-class by this script." >&2
            exit 1 ;;
        -h|--help)
            sed -n '1,34p' "$0" | sed 's/^### \{0,1\}//'; exit 0 ;;
        *)
            FORWARDED+=("$1"); shift ;;
    esac
done

echo "==> [1/3] rtx_6000:1, 12:00:00 — Qwen3.5:0.8B + Qwen3.5:4B + Qwen3.5:9B (packed array)"
bash "$HERE/submit_with_rtx.sh" --time 12:00:00 Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B "${FORWARDED[@]}"

echo
echo "==> [2/3] rtx_6000:1, 48:00:00 — qwen3.6:35b"
bash "$HERE/submit_with_rtx.sh" --time 48:00:00 qwen3.6:35b "${FORWARDED[@]}"

echo
echo "==> [3/3] rtx_6000:1, 48:00:00 — gemma4:26b-a4b"
bash "$HERE/submit_with_rtx.sh" --time 48:00:00 gemma4:26b-a4b "${FORWARDED[@]}"

echo
echo "Full sweep submitted. Track via: bash .claude/skills/cluster-ops/scripts/status.sh"
