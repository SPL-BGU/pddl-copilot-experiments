---
name: plan-review-simplify
description: Create an execution plan with built-in review for correctness and simplification. Use for multi-file changes, refactoring, or any change spanning multiple files.
disable-model-invocation: true
argument-hint: [task description]
---

## Planning Workflow with Review and Simplification

For the task described in $ARGUMENTS:

### Phase 1: Explore
1. Read all relevant existing code using Grep and Glob
2. Identify existing patterns that can be reused — especially:
   - `run_experiment.py` for experiment evaluation logic and MCP client patterns
   - `run_background.sh` for execution orchestration
   - `EXPERIMENTS_FLOW.md` for methodology and experimental design
3. Check `domains/` for PDDL benchmark structure and `results/` for output format

### Phase 2: Plan
Design the implementation approach covering:
- **Objective**: One sentence describing the goal
- **Analysis**: Current state, what needs to change, existing code to reuse
- **Scope**: Which files are affected? Does this change experiment methodology?
- **Reproducibility**: Will existing results remain valid? Are new baselines needed?
- **Files to modify**: Table of file | action (create/modify/delete) | description
- **Execution steps**: Numbered checklist
- **Validation strategy**: How to verify the change works (test run, result comparison, etc.)

### Phase 3: Review
Before presenting the plan, review it for simplification and correctness:

**Simplification:**
- Can any proposed new file be merged into an existing file?
- Can any proposed new script reuse existing logic from `run_experiment.py` or `run_background.sh`?
- Would a senior engineer say "this is more code than necessary"?
- Does the change avoid adding abstractions with only one consumer?

**Experiment integrity:**
- Does the change preserve compatibility with existing results in `results/`?
- Are evaluation metrics and success criteria unchanged (or intentionally updated)?
- Does the MCP client interface remain consistent with pddl-copilot plugin APIs?
- Is the change documented in `EXPERIMENTS_FLOW.md` if it affects methodology?

**Correctness:**
- Are PDDL domain/problem paths resolved correctly?
- Are Ollama model names and parameters correct?
- Does error handling cover MCP connection failures and tool timeouts?

If concerns found: revise the plan. Note what changed and why.

### Phase 4: Present for Approval
Present plan to user, noting:
- Open decisions requiring user input
- Any impact on existing experiment results or reproducibility

Do NOT proceed until approved.

### Phase 5: Execute
Execute steps in order. After completion:
1. Run a quick smoke test (e.g., single-task evaluation with smallest model)
2. Verify output format matches expected structure in `results/`
3. Summarize changes, key decisions, validation results

## Fast Mode
If user says "fast mode", "just do it", or "skip planning" — execute immediately without the planning workflow.

## Simple Tasks (No Planning Required)
Skip planning for:
- Single-file edits under 50 lines
- Answering questions or explaining code
- Running experiments without modification
- Git operations
- Documentation-only changes
