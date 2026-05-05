# pddl-copilot-experiments

Eval harness for the PDDL Planning Copilot paper. `run_experiment.py` orchestrates Ollama models with/without MCP planning tools across 5 PDDL tasks (`solve`, `validate_domain`, `validate_problem`, `validate_plan`, `simulate`).

The active flow is **single-task only** as of 2026-05-05; the multi-task chain phase is archived (function bodies preserved in `pddl_eval/{runner,summary}.py`, no longer wired into `run_experiment.py`). Don't add chain references to active code or docs without first re-wiring the dispatch — see `development/CHANGELOG.md` 2026-05-05 entry.

See `README.md` for the sibling-project (`../pddl-copilot/`) background, marketplace discovery, and additionalDirectories permission. The rules below are agent-routing guidance not duplicated elsewhere.

## Routing — where does a fix belong?

- MCP tool returns `{"error": ...}` or wrong-shape output → fix in `../pddl-copilot/plugins/<name>/server/` and rerun `bash ../pddl-copilot/plugins/<name>/tests/verify.sh`
- Plugin skill misbehaves, missing a tool, or wrong description → fix in `../pddl-copilot/plugins/<name>/skills/`
- Plugin venv / launch issue → fix in `../pddl-copilot/plugins/<name>/scripts/launch-server.sh` or `requirements.txt`
- Wrong scoring, prompt, ground-truth, or orchestration logic → fix in this repo (`run_experiment.py`, notebooks, `domains/`)

## Commit discipline

Each repo has its own git remote (`SPL-BGU/pddl-copilot-experiments`, `SPL-BGU/pddl-copilot`). Commit in the repo whose tree you edited; never `git add` paths under `../pddl-copilot/` from this repo. When a single change spans both, make two separate commits in the two repos.

## Plugin-isolation rule (inherited from sibling)

When editing across `../pddl-copilot/plugins/`, do NOT cross-import between plugins. Each plugin must remain self-contained and installable standalone. See `../pddl-copilot/.claude/rules/marketplace.md` for the full rule set.
