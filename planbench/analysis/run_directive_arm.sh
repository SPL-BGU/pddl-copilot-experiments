#!/bin/bash
# PlanBench §9-A sensitivity arm (amendment A third rung; handoff item 5).
# Approved by Omer 2026-08-06 ("i give you my go on the money decisions").
# Directive-only: verbatim WT scaffold (frozen v2 clause, dangling tool
# directive), NO tools attached (tools param omitted — pre-registered wire
# substitution). Mystery t1 only, FULL 600 pool (the §9-A bullet's n=250
# predates the whole-pool ANSWER and amendment K; whole-pool keeps the
# denominator identical to every other row — recorded in the results memo).
# NO --run_till_completion, NO --ignore_existing. Sequential, halt on failure.
set -u
REPO=/Users/omereliyahu/personal/pddl-copilot-experiments
cd "$REPO/external/LLMs-Planning/plan-bench" || exit 1
export PYTHONPATH="$REPO"
PY="$REPO/.venv-planbench-wt/bin/python"

for cfg in mystery_blocksworld mystery_blocksworld_3; do
  export PDDL_COPILOT_TOOLLOG="$REPO/.local/wt_run/${cfg}__anthropic-directive.jsonl"
  echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  START $cfg / anthropic-directive"
  if ! "$PY" response_generation.py --task t1 --config "$cfg" \
      --engine "pddl_copilot__anthropic-directive__claude-haiku-4-5" \
      > "$REPO/.local/wt_run/${cfg}__anthropic-directive.out" 2>&1; then
    echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  HALT: $cfg FAILED (rc=$?)"
    echo "### see .local/wt_run/${cfg}__anthropic-directive.out"
    exit 1
  fi
  echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  DONE  $cfg"
done
echo "### $(date -u '+%Y-%m-%d %H:%M:%S')  DIRECTIVE ARM DONE (600 trials)"
