---
name: simplify
description: Review current plan or code changes for unnecessary complexity, methodology drift, and result compatibility issues. Flags over-engineering and changes that could invalidate prior experiments.
argument-hint: [description of what to review]
paths: run_experiment.py, pddl_eval/**, cluster-experimenting/**
---

Review the current work for unnecessary complexity, methodology drift, and result compatibility issues. The bundled `/code-review` (formerly `/simplify`) handles general correctness; this skill adds experiment-specific concerns it cannot know.

$ARGUMENTS

If no specific target is given, review the most recent changes (`git diff` or the current plan).

## Mandate

The harness is a research evaluation framework (`run_experiment.py` + the `pddl_eval/` package) that tests vLLM-served LLMs on PDDL planning tasks. It intentionally stays small. Push back against:

- New files when the change belongs in `run_experiment.py` or an existing `pddl_eval/` module
- New abstractions with only one consumer (no base classes, no plugin architectures)
- New dependencies beyond what `requirements.txt` already provides
- Changes to evaluation metrics, success criteria, prompt templates, or system prompts without explicit methodology justification
- Over-parameterization (CLI flags for things with one correct value per the paper)
- MCP client patterns that diverge from `MCPPlanner` without reason. The `verbose=False` bridge (see EXPERIMENTS_FLOW.md §8) is the approved way to slim validator tool responses — reject proposals that replace it with caps, helpers, or per-tool flags.
- Reinventing caps that already exist as `DEFAULT_*` constants / `PDDL_*` env vars

## File classification

**CORE** (review carefully):
- `run_experiment.py`, `pddl_eval/{chat,runner,scoring,summary,domains,prompts,resume,vllm_client}.py`
- `EXPERIMENTS_FLOW.md` — methodology; changes here imply methodology changes
- `cluster-experimenting/` — sbatch + submit scripts
- `development/CHANGELOG.md`, `development/OPEN_ISSUES.md`

**REFERENCE** (read-only context):
- `domains/`, `results/`, `requirements.txt`

## Checks

When reviewing a plan or diff:
1. **Simplest solution?** Is the new code the minimum needed? If a new file is proposed, would the logic fit in `run_experiment.py` or an existing module?
2. **Result compat.** Will existing JSON files in `results/` still load and parse? `TaskResult` fields and `save_results()` output shape are load-bearing.
3. **Methodology integrity.** Do success criteria still match EXPERIMENTS_FLOW.md §4.1-§4.3? Is `generate_ground_truth()` called before model evaluation? Are temperature, seed, num_variants defaults preserved? Do output JSON fields still match §9?
4. **MCP contract.** Do tool calls still match §8, including the bridge stripping `verbose` from validator tool `inputSchema` and injecting `verbose=False`?
5. **Helper duplication.** Search `Grep` for existing helpers before approving new ones.
6. **Prompt/system surface.** Flag any change to `PROMPT_TEMPLATES`, `WITH_TOOLS_SYSTEM`, `WITHOUT_TOOLS_SYSTEM`.
7. **Documentation trail.** Is there a matching CHANGELOG entry queued? Does the change advance or invalidate any `ISS-###` in OPEN_ISSUES?

## Output

Numbered list of concerns, each tagged:
1. `[REMOVE]` — should be deleted entirely
2. `[SIMPLIFY]` — could be simpler
3. `[EXISTING]` — code already does this (cite path:line)
4. `[METHODOLOGY]` — changes evaluation methodology without justification
5. `[COMPAT]` — breaks compatibility with existing results
6. `[OVERKILL]` — solution exceeds problem scope for a ~4-CORE-file project

End with: **Simplification verdict: PASS / NEEDS REVISION**

- PASS: state the one thing closest to over-engineered (watch item).
- NEEDS REVISION: state top 3 changes ranked by impact.
