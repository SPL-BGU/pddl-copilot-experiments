"""pddl_eval — Eval harness internals for the PDDL Planning Copilot paper.

Split out of run_experiment.py in PR-1 (2026-04-27); see
development/CHANGELOG.md and development/FRAMEWORK_EXTENSION_PLAN.md.

Module DAG (one-directional, no cycles):
    prompts          — system prompts + per-task templates (no internal deps)
    chat             — Ollama chat loop, MCPPlanner, JSON helpers
    domains      → chat       — fixture loader + ground-truth generator
    scoring      → chat, domains  — verdict/plan extraction + check_success
    runner       → prompts, chat, domains, scoring  — evaluate_one + sweeps
    resume       → runner     — load_progress for trials.jsonl resume
    summary      → runner     — Wilson CIs, tables, save_results

Public API is intentionally lightweight: importers go through the submodules.
`run_experiment.py` re-exports the names that `tests/test_*.py` use.
"""
