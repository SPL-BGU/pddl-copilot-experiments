# shellcheck shell=bash
# Shared cluster-experimenting defaults sourced by submit_with_rtx.sh and
# run_condition_rtx.sbatch. Update here to change the active model roster
# or the default think × cond axes — both wrappers pick up the change.

# Default 4-model roster (post 2026-04-30 trim). See development/CHANGELOG.md
# for roster history. Update here to change the --all default.
PDDL_DEFAULT_MODELS=(Qwen3.5:0.8B qwen3.6:27b qwen3.6:35b gemma4:31b)

# Default think × cond axes. The matrix-gate (no-tools is reported only for
# think=off) is applied where the cells are built, NOT here.
PDDL_DEFAULT_THINK_MODES=(on off)
PDDL_DEFAULT_CONDITIONS=(no-tools tools_per-task_minimal tools_all_minimal)

# Default sbatch CONDITIONS env (space-separated, used when run_condition_rtx.sbatch
# is invoked WITHOUT CELLS_LIST — legacy direct-sbatch path).
PDDL_DEFAULT_SBATCH_CONDITIONS="tools_per-task_minimal tools_all_minimal"
