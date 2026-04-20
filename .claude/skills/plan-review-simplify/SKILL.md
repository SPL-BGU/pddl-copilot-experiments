---
name: plan-review-simplify
description: Create an execution plan with built-in review for correctness and simplification. Use for multi-file changes, refactoring, MCP/plugin edits, or any change spanning multiple files in this experiment harness. Trigger whenever the user asks to plan, design, or think through an implementation before coding — especially if the change could alter experiment methodology, tool-call output shape, or result schemas.
disable-model-invocation: true
argument-hint: [task description]
---

## Planning Workflow with Review and Simplification

For the task described in $ARGUMENTS:

### Phase 1: Explore
Read all relevant existing code using Grep and Glob. Identify reusable patterns and existing state so the plan doesn't reinvent them.

Reference surface, in the order you typically need them:
- `run_experiment.py` — experiment logic, `MCPPlanner` (MCP stdio client + `verbose` bridge stripping/injection), Ollama chat loop, scoring
- `run_background.sh` — execution orchestration
- `EXPERIMENTS_FLOW.md` — methodology, success criteria, MCP tool contract (§8), result schema (§9), paper-diff (§11)
- `development/CHANGELOG.md` — dated record of framework + sibling-MCP changes; check here first to avoid re-solving something that's already landed
- `development/OPEN_ISSUES.md` — known methodology gaps (`ISS-###`) with severity and fix sketches; many "should we fix X?" questions already have a written answer here
- `domains/` — PDDL benchmark structure; `results/` — output format

Why these matter: the harness is intentionally small (~4 CORE files). Most changes either land in `run_experiment.py` or cross into `../pddl-copilot` plugin servers. Checking CHANGELOG + OPEN_ISSUES up front prevents duplicate work and surfaces whether the ask is already tracked.

### Phase 2: Plan
Design the implementation approach covering:
- **Objective**: One sentence describing the goal
- **Analysis**: Current state, what needs to change, existing code to reuse
- **Scope**: Which files are affected? Does this change experiment methodology?
- **Reproducibility**: Will existing results remain valid? Are new baselines needed?
- **Files to modify**: Table of file | action (create/modify/delete) | description
- **Execution steps**: Numbered checklist
- **Validation strategy**: How to verify the change works (test run, result comparison, etc.)
- **Documentation**: Which entry belongs in `development/CHANGELOG.md`; does it resolve any `ISS-###` in `OPEN_ISSUES.md`?

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
- Does the MCP client interface remain consistent with the pddl-copilot plugin contract in EXPERIMENTS_FLOW.md §8 (including the bridge-pinned `verbose=False` convention for validator tools)?
- Is the change documented in `EXPERIMENTS_FLOW.md` if it affects methodology, and queued for `development/CHANGELOG.md`?
- Does it close or partially address any open `ISS-###`?

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
3. Append an entry to `development/CHANGELOG.md` (date, motivation, files touched, compatibility notes). If the change closes or narrows an `ISS-###`, move or update the matching entry in `development/OPEN_ISSUES.md`.
4. Summarize changes, key decisions, validation results

## Fast Mode
If user says "fast mode", "just do it", or "skip planning" — execute immediately without the planning workflow.

## Simple Tasks (No Planning Required)
Skip planning for:
- Single-file edits under 50 lines
- Answering questions or explaining code
- Running experiments without modification
- Git operations
- Documentation-only changes
