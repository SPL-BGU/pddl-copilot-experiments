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

2. Run a single-task smoke test:
   ```
   source .venv/bin/activate 2>/dev/null
   python3 run_experiment.py \
       --marketplace-path "${PDDL_MARKETPLACE_PATH:-../pddl-copilot}" \
       --models qwen3:0.6b \
       --tasks validate_domain \
       --num-variants 1 \
       --tool-filter per-task \
       --prompt-style minimal \
       --think off \
       --output-dir results/smoke_test/
   ```

3. Report results as:
   - Pipeline status: PASS (results saved) or FAIL (with error)
   - MCP connections: which plugin servers connected successfully
   - Ground truth: generated or failed
   - Model evaluation: success/failure counts from the summary output
   - Output files: list files created in `results/smoke_test/`
   - If FAIL: include the relevant error trace
