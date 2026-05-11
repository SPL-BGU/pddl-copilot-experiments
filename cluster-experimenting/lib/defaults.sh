# shellcheck shell=bash
# Shared cluster-experimenting defaults sourced by submit_with_rtx.sh and
# run_condition_rtx.sbatch. Update here to change the active model roster
# or the default think × cond axes — both wrappers pick up the change.

# Default 4-model roster (post 2026-04-30 trim). See development/CHANGELOG.md
# for roster history. Update here to change the --all default.
PDDL_DEFAULT_MODELS=(Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b)

# Heavy/slow models — kept at Nice=0 by the auto-prioritize logic in
# submit_with_rtx.sh and the cluster-ops `prioritize.sh` skill script.
# Any model in PDDL_DEFAULT_MODELS but NOT in this list is treated as
# fast/cheap and gets Nice=500 so the heavy cells grab the next free GPU
# slot first when there's queue contention. Negative Nice (raise priority
# above default) requires admin on this cluster, so this is the only
# direction we have without a Golden-Ticket QoS.
PDDL_SLOW_MODELS=(gemma4:31b qwen3.6:35b)

# Default think × cond axes. The matrix-gate (no-tools is reported only for
# think=off) is applied where the cells are built, NOT here.
PDDL_DEFAULT_THINK_MODES=(on off)
PDDL_DEFAULT_CONDITIONS=(no-tools tools_per-task_minimal tools_all_minimal)

# Default sbatch CONDITIONS env (space-separated, used when run_condition_rtx.sbatch
# is invoked WITHOUT CELLS_LIST — legacy direct-sbatch path).
PDDL_DEFAULT_SBATCH_CONDITIONS="tools_per-task_minimal tools_all_minimal"

# vLLM production roster. Mirrored by the wrapper's --backend vllm gate
# and by `vllm_lookup` below. Append a model only after its parser has
# been verified via cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch
# (2026-05-10 hermes→qwen3_xml fix landed here as a result of skipping
# verification on the original 27B AWQ probe). The lookup table is the
# single source of truth for OLLAMA_TAG → (HF id, parser flags) used by
# both run_condition_vllm_rtx.sbatch and submit_with_rtx.sh.
PDDL_VLLM_VERIFIED_MODELS=(qwen3.6:27b Qwen3.5:0.8B)

# Resolve canonical Ollama tag → (HF id, parser flags) for vLLM serve.
# Exports HF_MODEL, TOOL_CALL_PARSER, REASONING_PARSER on success;
# returns non-zero with a clear error otherwise so callers can bail.
vllm_lookup() {
    case "$1" in
        qwen3.6:27b)
            HF_MODEL="cyankiwi/Qwen3.6-27B-AWQ-INT4"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        Qwen3.5:0.8B)
            HF_MODEL="Qwen/Qwen3.5-0.8B"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        *)
            echo "Error: model '$1' not in PDDL_VLLM_VERIFIED_MODELS (${PDDL_VLLM_VERIFIED_MODELS[*]})" >&2
            echo "       Verify the parser via run_smoke_vllm_vs_ollama.sbatch before adding it." >&2
            return 1
            ;;
    esac
}
