---
name: experiment-runner
description: Run a quick smoke-test experiment to verify the pipeline works (Ollama, MCP connections, evaluation, result saving). Use after code changes.
tools: Bash, Read, Grep
model: haiku
maxTurns: 6
---

Run a minimal smoke-test experiment to verify the pipeline works end to end.

1. Check prerequisites:
   - Ollama is running: `curl -sf http://localhost:11434/api/tags`
   - Model is available: `ollama list | grep qwen3:0.6b`
   - pddl-copilot marketplace exists at `../pddl-copilot` (or `$PDDL_MARKETPLACE_PATH`)

2. Run the canonical smoke slice (auto-pins domain/problem/variants/tasks/conditions/think modes; writes to `results/smoke/fixed_<git-sha>_<ts>/`):
   ```
   source .venv/bin/activate 2>/dev/null
   python3 run_experiment.py \
       --marketplace-path "${PDDL_MARKETPLACE_PATH:-../pddl-copilot}" \
       --models qwen3:0.6b \
       --smoke
   ```
   If `results/smoke/fixed_<git-sha>_<ts>/` already exists from a prior run on this commit, the harness resumes from `trials.jsonl` by default; pass `--no-resume` to start fresh.

3. Report results as:
   - Pipeline status: PASS (results saved) or FAIL (with error)
   - MCP connections: which plugin servers connected successfully
   - Ground truth: generated or failed
   - Model evaluation: success/failure counts from the summary output
   - Output files: list files created in `results/smoke/fixed_<git-sha>_<ts>/`
   - **Bridge projection check**: `tool_calls[*]` entries that hit `validate_pddl_syntax` or `get_state_transition` should NOT contain `"details"` in the result JSON (bridge pins `verbose=False`). Parse one result string and report `keys present`. See EXPERIMENTS_FLOW.md §8.
   - If FAIL: include the relevant error trace
   - For deeper aggregation/plotting beyond this smoke check, hand off to the `analyzer` skill (`.claude/skills/analyzer/SKILL.md`).
