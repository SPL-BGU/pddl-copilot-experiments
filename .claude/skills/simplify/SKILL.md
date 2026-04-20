---
name: simplify
description: Review current plan or code changes for unnecessary complexity, methodology drift, and result compatibility issues. Flags over-engineering and changes that could invalidate prior experiments.
context: fork
agent: simplifier
argument-hint: [description of what to review]
---

Review the current work for unnecessary complexity and correctness.

$ARGUMENTS

If no specific target is given, review the most recent changes (check git diff or the current plan).

Key reference files for methodology review:
- run_experiment.py — All experiment logic (MCP, Ollama, evaluation, scoring). Note the `MCPPlanner._PINNED_VERBOSE_FALSE` bridge pattern that strips `verbose` from validator tool schemas and pins it to `False` on call.
- EXPERIMENTS_FLOW.md — Methodology documentation, success criteria, MCP tool API contract (§8), result schemas (§9), paper-diff (§11)
- run_background.sh — CLI wrapper and execution orchestration
- development/CHANGELOG.md — recent framework + sibling-MCP changes; cross-check that the proposed change doesn't duplicate something already landed
- development/OPEN_ISSUES.md — tracked methodology gaps (`ISS-###`); flag if the review's target invalidates an open-issue fix sketch
