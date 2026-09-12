#!/bin/bash
# PlanBench bare-NT 200-trial completion (amendment K debt; handoff item 3).
# Approved by Omer 2026-08-06 ("i give you my go on the money decisions").
# 100 clean + 100 Mystery on the _3 pools, engine token `anthropic` (the graded
# 06-22 NT path: native PlanBench prompt, no scaffold, no tools).
# Trap 5: plain invocation only — these configs have NO existing anthropic
# response files, so nothing can be overwritten; NO --ignore_existing,
# NO --run_till_completion (traps 4/5). Sequential, halt on failure.
set -u
REPO=/Users/omereliyahu/personal/pddl-copilot-experiments
cd "$REPO/external/LLMs-Planning/plan-bench" || exit 1
export PYTHONPATH="$REPO"
PY="$REPO/.venv-planbench-wt/bin/python"

for cfg in blocksworld_3 mystery_blocksworld_3; do
  echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  START $cfg / anthropic (bare NT)"
  if ! "$PY" response_generation.py --task t1 --config "$cfg" \
      --engine "pddl_copilot__anthropic__claude-haiku-4-5" \
      > "$REPO/.local/wt_run/${cfg}__anthropic-bare.out" 2>&1; then
    echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  HALT: $cfg FAILED (rc=$?)"
    echo "### see .local/wt_run/${cfg}__anthropic-bare.out"
    exit 1
  fi
  echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  DONE  $cfg"
done
echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  BARE-NT COMPLETION DONE (200 trials)"
