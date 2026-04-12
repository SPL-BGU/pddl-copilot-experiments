---
name: debug-and-simplify
description: Diagnose and fix issues with experiment execution, MCP client connections, Ollama models, or result analysis. Use when something is broken or behaving unexpectedly.
disable-model-invocation: true
argument-hint: [description of the issue or error message]
---

## Debugging Workflow with Simplification Review

For the issue described in $ARGUMENTS:

### Phase 1: Diagnose
Systematically check each layer, stopping when the root cause is found:

**Layer 0 — Runtime basics:**
1. Is the virtual environment set up? (`source .venv/bin/activate && pip list`)
2. Are required dependencies installed? (`pip install -r requirements.txt`)
3. Can `run_experiment.py` import its dependencies? `python3 -c "import mcp, ollama, tabulate"`
4. Is Java 17+ available? (`java -version` — required for ENHSP numeric planner)

**Layer 1 — Ollama service:**
1. Is Ollama running? (`curl -s http://localhost:11434/api/tags`)
2. Is the target model pulled? (`ollama list`)
3. Does a simple prompt work? (`ollama run <model> "test" --verbose`)
4. Check `ollama_serve.log` for service errors

**Layer 2 — MCP client connections:**
1. Is `PDDL_MARKETPLACE_PATH` set or does pddl-copilot exist at the expected sibling path?
2. Can the MCP plugin servers start? Run the plugin's `launch-server.sh` directly
3. Do individual MCP tool calls succeed? Test with inline PDDL content
4. Are tool responses in the expected format (dict with error/success fields)?

**Layer 3 — Experiment execution:**
1. Does a single-task dry run work? (`python3 run_experiment.py --tasks solve --dry-run`)
2. Are PDDL domain/problem files found in `domains/`?
3. Is ground-truth generation succeeding before model evaluation?
4. Check timestamped log files (`run_*.log`) for error traces

**Layer 4 — Results and analysis:**
1. Are output JSON files valid? (`python3 -m json.tool results/<dir>/summary_*.json`)
2. Do result schemas match what notebooks expect?
3. Are chain evaluation results consistent with single-task results?

### Phase 2: Fix
Apply the **minimal change** that resolves the root cause:
- Prefer fixing configuration over adding code
- Prefer fixing existing code over adding new files

### Phase 3: Simplify Review
Before committing the fix, review it:
1. Is this the smallest possible change that fixes the issue?
2. Does it introduce any new dependencies or complexity?
3. Could the root cause recur? If so, should we add a pre-flight check?
4. Does the fix maintain compatibility with existing results?

### Phase 4: Verify
1. Run a quick experiment to confirm the fix (smallest model, single task)
2. If the issue was in results/analysis, verify notebooks still load correctly
3. Report: what broke, why, what was fixed, verification result

### Common Issues Reference

| Symptom | Likely cause | Quick check |
|---------|-------------|-------------|
| "ConnectionRefusedError" | Ollama not running | `curl localhost:11434/api/tags` |
| "ModuleNotFoundError" | Missing pip dependency | `pip install -r requirements.txt` |
| MCP tool returns error dict | Plugin server issue or bad PDDL input | Test tool directly with known-good input |
| "model not found" | Model not pulled | `ollama pull <model>` |
| Numeric task fails | Java not installed or wrong version | `java -version` (need 17+) |
| Empty results JSON | Ground-truth generation failed silently | Check log file for upstream errors |
| Background run dies | OOM or Ollama crash | Check `ollama_serve.log` and system memory |
| Stale MCP connection | Plugin venv missing new deps | Delete plugin `.venv` and restart |
