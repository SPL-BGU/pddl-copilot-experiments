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
- run_experiment.py — All experiment logic (MCP, Ollama, evaluation, scoring)
- EXPERIMENTS_FLOW.md — Methodology documentation and success criteria
- run_background.sh — CLI wrapper and execution orchestration
