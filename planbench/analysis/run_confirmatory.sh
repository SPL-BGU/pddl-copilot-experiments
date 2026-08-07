#!/bin/bash
# PlanBench-WT CONFIRMATORY run (prereg v2, tag prereg-planbench-wt-v1 + restart record 1).
# Approved by Omer 2026-08-01 ("launch") at the measured $34.08 projection.
# 4 cells x 600 instances = 2400 trials, SEQUENTIAL (decided), frozen v2 clause.
# Halt-on-failure between invocations (pipeline-safety rule). Crash-resume is safe:
# response trees were verified CLEAN at launch, so skip-existing only ever skips
# this run's own completed instances.
set -u
REPO=/Users/omereliyahu/personal/pddl-copilot-experiments
cd "$REPO/external/LLMs-Planning/plan-bench" || exit 1

export PDDL_MARKETPLACE_PATH=/Users/omereliyahu/personal/pddl-copilot
export PDDL_PLANBENCH_PLUGINS="pddl-solver pddl-validator"
export PDDL_COPILOT_TASK=t1
export FAST_DOWNWARD=/Users/omereliyahu/personal/pddl-copilot/plugins/pddl-solver/.venv/lib/python3.14/site-packages/up_fast_downward/downward
export PYTHONPATH="$REPO"
PY="$REPO/.venv-planbench-wt/bin/python"

# NO --run_till_completion (unbounded paid retry on an empty answer, trap 4).
# NO --ignore_existing (trap 5; also gives cheap crash-resume).
for cfg in blocksworld blocksworld_3 mystery_blocksworld mystery_blocksworld_3; do
  for backend in anthropic-tools anthropic-scaffold; do
    export PDDL_COPILOT_TOOLLOG="$REPO/.local/wt_run/${cfg}__${backend}.jsonl"
    echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  START $cfg / $backend"
    if ! "$PY" response_generation.py --task t1 --config "$cfg" \
        --engine "pddl_copilot__${backend}__claude-haiku-4-5" \
        > "$REPO/.local/wt_run/${cfg}__${backend}.out" 2>&1; then
      echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  HALT: $cfg / $backend FAILED (rc=$?)"
      echo "### see .local/wt_run/${cfg}__${backend}.out"
      exit 1
    fi
    echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  DONE  $cfg / $backend"
  done
done
echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  ALL 8 INVOCATIONS COMPLETE"
