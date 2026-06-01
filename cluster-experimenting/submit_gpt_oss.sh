#!/usr/bin/env bash
# Dedicated submission wrapper for the STANDALONE gpt-oss:120b cell(s).
#
# Why a separate script (and not just `submit_with_rtx.sh gpt-oss:120b`):
# gpt-oss-120b has hard constraints the generic wrapper would let an
# operator violate by omission —
#
#   1. Thinking has NO on/off toggle. gpt-oss reasons at a reasoning_effort
#      level (low|medium|high, default medium) carried in its harmony system
#      message. The harness only injects the Qwen-style enable_thinking when
#      `think is not None` (pddl_eval/vllm_client.py:154), so we MUST run
#      --think-modes default (→ think=None → native medium effort untouched).
#      Running --think on/off would splice chat_template_kwargs.enable_thinking
#      that gpt-oss's template does not honor — a meaningless / mismatched cell.
#   2. GPU class is fixed to rtx_pro_6000. The native MXFP4 weights are ~63 GB
#      and do NOT fit the 48 GB rtx_6000 escape hatch.
#   3. It is NOT part of PDDL_DEFAULT_MODELS / `--all`. This is a standalone
#      reference model (its own comparison; the model used for the PlanBench
#      track) and must never be pooled into the canonical 5-model sweep corpus.
#
# This wrapper pins (1)-(3), lowers the vLLM VRAM fraction to keep the
# sbatch's 85%-VRAM guard off the knife-edge on the 96 GB card, enlarges
# /scratch for the 63 GB pull, and forwards every other flag to
# submit_with_rtx.sh unchanged. The model registry entry (HF id + the
# verified --tool-call-parser openai / --reasoning-parser openai_gptoss
# flags) lives in lib/defaults.sh:vllm_lookup — single source of truth.
#
# Usage:
#   bash cluster-experimenting/submit_gpt_oss.sh --smoke                 # validate deploy + parser first
#   bash cluster-experimenting/submit_gpt_oss.sh                         # full standalone: think=default × {no-tools, tools}
#   bash cluster-experimenting/submit_gpt_oss.sh --tools-only            # with-tools cell only
#   bash cluster-experimenting/submit_gpt_oss.sh --no-tools              # no-tools baseline only
#   bash cluster-experimenting/submit_gpt_oss.sh --dry-run               # print the sbatch line, submit nothing
#
# Forwarded flags (handed straight to submit_with_rtx.sh): --smoke,
# --smoke-shuffle, --tools-only, --no-tools, --dry-run, --time, --tmp,
# --continue-partial, --partial, --exclude, --domains-dir, --run-tag,
# --shard, --include-no-tools-steered, --no-auto-prioritize.
#
# Rejected (this wrapper owns them): --gpu-type, --think-modes, and any
# positional model argument.
#
# PRE-FLIGHT (clear before the first smoke — see advisor notes / CHANGELOG):
#   * Rebuild a stale $HOME/vllm.sif on the cluster — a cached image from
#     before gpt-oss support (vLLM <0.10.1) will fail to load the arch:
#       rm -f $HOME/vllm.sif   # forces rebuild from docker://vllm/vllm-openai:latest
#   * Confirm `openai/gpt-oss-120b` pulls (Apache-2.0, ungated; HF_TOKEN not
#     required, but verify the cluster can reach HF / has cache space).
#   * Smoke verdict = ToolSel rate on the tools cell + non-empty
#     reasoning_content (thinking) — NOT first-pass success%, which medium
#     reasoning can depress via num_predict truncation. The smoke's think
#     on/off passes render identically here (enable_thinking is ignored by
#     gpt-oss's template); that is expected, not a bug.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODEL="gpt-oss:120b"
# Lower than the sbatch's 0.85 default: on a 96 GB rtx_pro_6000, 0.82 →
# ~78.7 GB used → ~82% read, leaving the `VRAM_PCT > 85` guard ~3 pts of
# slack (gpt-oss is MXFP4 on a card the guard was never tuned for).
# Propagated to the job via submit_with_rtx.sh's `sbatch --export=ALL`.
export GPU_MEM_UTIL="0.82"
# Write the vLLM serve log directly to the persistent logs dir. gpt-oss:120b
# is large enough to risk a host-RAM cgroup OOM during cold-load (smoke
# 17951156 died at ~95% of the 80G cap); that's a SIGKILL the sbatch's EXIT
# trap can't catch, so the scratch-then-copy path loses the log. Persisting
# it inline is what makes a failure diagnosable (host-OOM vs vLLM crash).
export PERSIST_SERVE_LOG="1"

FORWARD=()
HAS_TMP=0
HAS_TIME=0
IS_SMOKE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gpu-type)
            echo "Error: --gpu-type is fixed to rtx_pro_6000 for gpt-oss:120b (63 GB weights do not fit rtx_6000)." >&2
            exit 1 ;;
        --think-modes)
            echo "Error: --think-modes is fixed to 'default' for gpt-oss:120b (no on/off toggle; see header)." >&2
            exit 1 ;;
        --tmp) HAS_TMP=1; FORWARD+=("$1" "$2"); shift 2 ;;
        --time) HAS_TIME=1; FORWARD+=("$1" "$2"); shift 2 ;;
        --dependency) FORWARD+=("$1" "$2"); shift 2 ;;
        --smoke|--smoke-shuffle) IS_SMOKE=1; FORWARD+=("$1"); shift ;;
        -*) FORWARD+=("$1"); shift ;;
        *)
            echo "Error: positional model arg '$1' not allowed — this wrapper is hard-pinned to $MODEL." >&2
            exit 1 ;;
    esac
done

# Default /scratch bump for the 63 GB pull + ~10-15 GB vllm.sif copy (the
# sbatch's 80G directive is marginal). Overridable via an explicit --tmp.
if [ "$HAS_TMP" -eq 0 ]; then
    FORWARD+=(--tmp 100G)
fi

# Smoke gets full-run wall time, not submit_with_rtx.sh's 3h smoke default —
# gpt-oss reasons (medium effort) so trials are slow; a 3h cap risks a
# silent TIMEOUT mid-smoke. (Matches the project's smoke-resourcing rule.)
if [ "$IS_SMOKE" -eq 1 ] && [ "$HAS_TIME" -eq 0 ]; then
    FORWARD+=(--time 24:00:00)
fi

# --think-modes default is the pin for the production path. The smoke path
# (run_experiment.py --smoke) already iterates think internally and
# submit_with_rtx.sh forbids --smoke + --think-modes together, so we omit
# the flag there — the sbatch smoke fastpath sets THINK_MODES=default for us.
if [ "$IS_SMOKE" -eq 1 ]; then
    set -- "$MODEL" --gpu-type rtx_pro_6000 "${FORWARD[@]}"
else
    set -- "$MODEL" --gpu-type rtx_pro_6000 --think-modes default "${FORWARD[@]}"
fi

echo "--- gpt-oss:120b standalone submit (pinned: rtx_pro_6000, think=default, GPU_MEM_UTIL=$GPU_MEM_UTIL) ---" >&2
echo "  delegating to: submit_with_rtx.sh $*" >&2

exec bash "$SCRIPT_DIR/submit_with_rtx.sh" "$@"
