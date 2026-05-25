---
name: experiment-runner
description: Run a quick smoke-test experiment to verify the pipeline works (vLLM server, MCP connections, evaluation, result saving). Use after code changes.
tools: Bash, Read, Grep
model: haiku
maxTurns: 6
---

Run a minimal smoke-test experiment to verify the pipeline works end to end.

1. Check prerequisites:
   - vLLM server reachable: `curl -sf "${LLM_BASE_URL:-http://localhost:8000}/v1/models"`
   - pddl-copilot marketplace exists at `../pddl-copilot` (or `$PDDL_MARKETPLACE_PATH`)

2. Run the canonical smoke slice (auto-pins domain/problem/variants/tasks/conditions/think modes; writes to `results/smoke/fixed_<git-sha>_<ts>/`). See `python3 run_experiment.py --help` for the full flag list; typical invocation:
   ```
   source .venv/bin/activate 2>/dev/null
   python3 run_experiment.py --smoke --models Qwen3.5:0.8B
   ```
   `--marketplace-path` defaults to `$PDDL_MARKETPLACE_PATH` (required when the env var is unset — pass `--marketplace-path ../pddl-copilot` explicitly in that case); `--llm-base-url` defaults to `$LLM_BASE_URL`. If the smoke output dir for this commit exists, the harness resumes from `trials.jsonl`; pass `--no-resume` to start fresh.

3. Report results as:
   - Pipeline status: PASS (results saved) or FAIL (with error)
   - MCP connections: which plugin servers connected successfully
   - Ground truth: generated or failed
   - Model evaluation: success/failure counts from the summary output
   - Output files: list files created under the smoke dir
   - **Bridge projection check**: validator + `get_state_transition` tool results should NOT contain `"details"` (see EXPERIMENTS_FLOW.md §8). Report `keys present` from one parsed result.
   - If FAIL: include the relevant error trace, then hand off to the `debug-and-simplify` skill (`.claude/skills/debug-and-simplify/SKILL.md`).
   - For deeper aggregation/plotting beyond this smoke, hand off to the `analyzer` skill (`.claude/skills/analyzer/SKILL.md`).
