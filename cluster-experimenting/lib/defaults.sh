# shellcheck shell=bash
# Shared cluster-experimenting defaults sourced by submit_with_rtx.sh and
# run_condition_vllm_rtx.sbatch. Update here to change the active model
# roster or the default think × cond axes — both wrappers pick up the change.

# Default 5-model roster (post 2026-05-18: backend unified on vLLM —
# gemma4:31b dense was swapped for gemma4:26b-a4b MoE, completing the
# Ollama retirement). See development/CHANGELOG.md for full roster history.
# Update here to change the --all default.
PDDL_DEFAULT_MODELS=(Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B qwen3.6:35b gemma4:26b-a4b)

# Heavy/slow models — kept at Nice=0 by the auto-prioritize logic in
# submit_with_rtx.sh and the cluster-ops `prioritize.sh` skill script.
# Any model in PDDL_DEFAULT_MODELS but NOT in this list is treated as
# fast/cheap and gets Nice=500 so the heavy cells grab the next free GPU
# slot first when there's queue contention. Negative Nice (raise priority
# above default) requires admin on this cluster, so this is the only
# direction we have without a Golden-Ticket QoS.
PDDL_SLOW_MODELS=(gemma4:26b-a4b qwen3.6:35b)

# Default think × cond axes. The full Cartesian product is built; the legacy
# no-tools/think=on matrix-gate was lifted 2026-05-12 in submit_with_rtx.sh.
PDDL_DEFAULT_THINK_MODES=(on off)
PDDL_DEFAULT_CONDITIONS=(no-tools tools_all_minimal)

# Default sbatch CONDITIONS env (space-separated, used when
# run_condition_vllm_rtx.sbatch is invoked WITHOUT CELLS_LIST — legacy
# direct-sbatch path).
PDDL_DEFAULT_SBATCH_CONDITIONS="tools_all_minimal"

# vLLM production roster. Mirrored by `vllm_lookup` below. Append a model
# only after its parser has been verified via
# `submit_with_rtx.sh --smoke <model>` (one-cell smoke that exercises
# the prod sbatch's smoke fastpath; the 2026-05-10 hermes→qwen3_xml fix
# landed because the original 27B AWQ probe skipped this step). The
# lookup table is the single source of truth for canonical-tag →
# (HF id, parser flags) used by both run_condition_vllm_rtx.sbatch and
# submit_with_rtx.sh.
PDDL_VLLM_VERIFIED_MODELS=(qwen3.6:35b Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B gemma4:26b-a4b)

# Resolve canonical model tag → (HF id, parser flags) for vLLM serve.
# Exports HF_MODEL, TOOL_CALL_PARSER, REASONING_PARSER on success, plus
# MAX_NUM_BATCHED_TOKENS for multimodal-aware cases where vLLM's default
# 2048-token batch budget is too small for the model's per-MM-item
# (left unset for text-only models → callers fall through to vLLM default);
# returns non-zero with a clear error otherwise so callers can bail.
vllm_lookup() {
    case "$1" in
        qwen3.6:35b)
            # qwen3_5_moe arch, compressed-tensors AWQ-INT4. 35B A3B MoE:
            # ~17 GB on disk, fits rtx_6000:1 with ~30 GB KV-cache headroom
            # under gpu-memory-utilization=0.85. Parser verified via
            # the vLLM smoke path in job 17494176, 2026-05-12.
            HF_MODEL="cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        Qwen3.5:0.8B)
            HF_MODEL="Qwen/Qwen3.5-0.8B"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        Qwen3.5:4B)
            # qwen3_5 dense arch, FP16. ~9 GB weights on rtx_6000:1 leaves
            # ample KV headroom. Parsers inherited from the Qwen3.5 family
            # (same as 0.8B/9B). Smoke-verify via
            # `submit_with_rtx.sh --smoke <model>` before
            # flipping the production sweep.
            HF_MODEL="Qwen/Qwen3.5-4B"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        Qwen3.5:9B)
            # qwen3_5 dense arch, FP16. ~18 GB weights on rtx_6000:1.
            # Note: Qwen3.5 ladder skips 8B; 9B is the next dense size
            # above 4B (HF id Qwen/Qwen3.5-9B, NOT Qwen3.5-8B which
            # does not exist). Smoke-verify via
            # `submit_with_rtx.sh --smoke <model>` before
            # production.
            HF_MODEL="Qwen/Qwen3.5-9B"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        gemma4:26b-a4b)
            # gemma4 arch, MoE A4B (~4B active of 26.5B total),
            # compressed-tensors AWQ-INT4 from the same publisher as
            # qwen3.6:35b's verified vLLM quant. ~16 GB weights on disk,
            # peaks ~85% on rtx_6000:1 (42218/49140 MiB) under
            # gpu-memory-utilization=0.85. Gemma's tokenizer has no
            # <think> tokens → REASONING_PARSER=none (omits the flag);
            # tool-call format is the gemma4 family parser (verified
            # registered in vLLM 0.20.x via the 2026-05-12 smoke fix;
            # tools-cell ToolSel ≥0.95 in smoke 17638752).
            # HF tag is image-text-to-text — vLLM auto-loads the vision
            # tower whose per-MM-item budget (2496 tok) exceeds the
            # default --max-num-batched-tokens=2048 and crashes startup
            # without MAX_NUM_BATCHED_TOKENS≥2496 (smoke 17633538 →
            # 17638752 confirmed 4096 is sufficient).
            HF_MODEL="cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
            TOOL_CALL_PARSER="gemma4"
            REASONING_PARSER="none"
            MAX_NUM_BATCHED_TOKENS="4096"
            ;;
        gpt-oss:120b)
            # OpenAI gpt-oss-120b. MoE, 117B total / 5.1B active, native
            # MXFP4 (~63 GB weights) — loads out of the box, no quant flag.
            # STANDALONE model: NOT in PDDL_DEFAULT_MODELS / --all. Submit
            # only via the dedicated `submit_gpt_oss.sh` wrapper, which pins
            # rtx_pro_6000 (the 63 GB weights do NOT fit the 48 GB rtx_6000)
            # and --think-modes default.
            #
            # Thinking: gpt-oss has NO on/off toggle — only a reasoning_effort
            # level (low|medium|high, default medium) carried in the harmony
            # system message. The harness only injects enable_thinking when
            # `think is not None` (vllm_client.py:154), so think=default
            # (→ think=None) is correct and leaves the native medium effort
            # untouched. Never run this model with --think on/off: it would
            # splice a Qwen-style chat_template_kwargs.enable_thinking that
            # gpt-oss's harmony template does not honor.
            #
            # Parsers (verified from vLLM source, stable 0.10.x→0.13.x; a
            # wrong name silently yields 0% extraction):
            #   --tool-call-parser openai     (OpenAIToolParser; NOT
            #                                  openai_gptoss/harmony) + the
            #                                  sbatch's --enable-auto-tool-choice
            #   --reasoning-parser openai_gptoss  (GptOssReasoningParser; the
            #                                  registered name is openai_gptoss
            #                                  even though the file is gptoss_*)
            # Needs vLLM >=0.10.1 (mainlined); the prod sbatch's
            # docker://vllm/vllm-openai:latest is well past that — but a STALE
            # cached $HOME/vllm.sif on the cluster may predate gpt-oss support,
            # so rebuild it (rm $HOME/vllm.sif) before the first smoke.
            # PENDING vLLM smoke verification before promotion to
            # PDDL_VLLM_VERIFIED_MODELS.
            HF_MODEL="openai/gpt-oss-120b"
            TOOL_CALL_PARSER="openai"
            REASONING_PARSER="openai_gptoss"
            ;;
        *)
            echo "Error: model '$1' not in PDDL_VLLM_VERIFIED_MODELS (${PDDL_VLLM_VERIFIED_MODELS[*]})" >&2
            echo "       Verify the parser via 'submit_with_rtx.sh --smoke <model>' before adding it." >&2
            return 1
            ;;
    esac
}

# Build the `--reasoning-parser X` flag from $REASONING_PARSER. Unset or
# empty defaults to `qwen3`; pass `none` to omit the flag (required for
# families with no <think> tokens, e.g. Gemma-4 — qwen3 crashes against
# their tokenizer at vLLM startup). Echoes the flag; callers splice with
# `$(...)`. No quoting on splice site so the empty case expands to nothing.
vllm_reasoning_parser_flag() {
    local p="${REASONING_PARSER:-qwen3}"
    if [ -n "$p" ] && [ "$p" != "none" ]; then
        echo "--reasoning-parser $p"
    fi
}
