# shellcheck shell=bash
# Shared cluster-experimenting defaults sourced by submit_with_rtx.sh and
# run_condition_rtx.sbatch. Update here to change the active model roster
# or the default think × cond axes — both wrappers pick up the change.

# Default 5-model roster (post 2026-05-17 swap: dropped qwen3.6:27b, added
# Qwen3.5:4B + Qwen3.5:9B to fill the 0.8B → 35B-A3B param gap with a
# faster, dense mid-band). See development/CHANGELOG.md for roster history.
# Update here to change the --all default.
PDDL_DEFAULT_MODELS=(Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B qwen3.6:35b gemma4:31b)

# Heavy/slow models — kept at Nice=0 by the auto-prioritize logic in
# submit_with_rtx.sh and the cluster-ops `prioritize.sh` skill script.
# Any model in PDDL_DEFAULT_MODELS but NOT in this list is treated as
# fast/cheap and gets Nice=500 so the heavy cells grab the next free GPU
# slot first when there's queue contention. Negative Nice (raise priority
# above default) requires admin on this cluster, so this is the only
# direction we have without a Golden-Ticket QoS.
PDDL_SLOW_MODELS=(gemma4:31b qwen3.6:35b)

# Default think × cond axes. The full Cartesian product is built; the legacy
# no-tools/think=on matrix-gate was lifted 2026-05-12 in submit_with_rtx.sh.
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
PDDL_VLLM_VERIFIED_MODELS=(qwen3.6:35b Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B)

# Resolve canonical Ollama tag → (HF id, parser flags) for vLLM serve.
# Exports HF_MODEL, TOOL_CALL_PARSER, REASONING_PARSER on success;
# returns non-zero with a clear error otherwise so callers can bail.
vllm_lookup() {
    case "$1" in
        qwen3.6:35b)
            # qwen3_5_moe arch, compressed-tensors AWQ-INT4. 35B A3B MoE:
            # ~17 GB on disk, fits rtx_6000:1 with ~30 GB KV-cache headroom
            # under gpu-memory-utilization=0.85. Parser verified via
            # run_smoke_vllm_vs_ollama.sbatch job 17494176, 2026-05-12.
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
            # (same as 0.8B/9B). Smoke-verify via run_smoke_vllm_vs_ollama
            # before flipping the production sweep.
            HF_MODEL="Qwen/Qwen3.5-4B"
            TOOL_CALL_PARSER="qwen3_xml"
            REASONING_PARSER="qwen3"
            ;;
        Qwen3.5:9B)
            # qwen3_5 dense arch, FP16. ~18 GB weights on rtx_6000:1.
            # Note: Qwen3.5 ladder skips 8B; 9B is the next dense size
            # above 4B (HF id Qwen/Qwen3.5-9B, NOT Qwen3.5-8B which
            # does not exist). Smoke-verify before production.
            HF_MODEL="Qwen/Qwen3.5-9B"
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

# --- PlanBench arm defaults (added 2026-05-18, planbench-integration branch) ---
# Sourced by run_planbench_rtx.sbatch + submit_planbench.sh. v1 = vanilla
# leaderboard (no MCP tools). Default tasks/configs match the user's chosen
# scope (all 10 tasks × canonical 3 domains). Mystery/obfuscated configs
# deferred; see planbench/README.md.
PDDL_PLANBENCH_DEFAULT_TASKS="t1 t2 t3 t4 t5 t6 t7 t8_1 t8_2 t8_3"
PDDL_PLANBENCH_DEFAULT_CONFIGS="blocksworld logistics depots"

# Local PlanBench checkout (cloned + patched + venv'd by planbench/setup.sh).
# `external/` is gitignored — each host runs setup.sh once.
PDDL_PLANBENCH_PATH="${PDDL_PLANBENCH_PATH:-$HOME/pddl-copilot-experiments/external/LLMs-Planning}"
