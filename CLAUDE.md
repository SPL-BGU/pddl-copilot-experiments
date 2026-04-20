# pddl-copilot-experiments

Eval harness for the PDDL Planning Copilot paper. `run_experiment.py` orchestrates Ollama models with/without MCP planning tools across 5 PDDL tasks (`solve`, `validate_domain`, `validate_problem`, `validate_plan`, `simulate`).

## Sibling project: pddl-copilot

`../pddl-copilot/` is the Claude Code plugin marketplace this harness exercises. It contains three isolated plugins under `plugins/`: `pddl-solver`, `pddl-validator`, `pddl-parser`. The harness discovers them at runtime via `$PDDL_MARKETPLACE_PATH` (defaults to `../pddl-copilot`).

Agents launched from this repo have read+edit access to `../pddl-copilot/` via `.claude/settings.local.json` → `additionalDirectories`.

### Routing — where does a fix belong?

- MCP tool returns `{"error": ...}` or wrong-shape output → fix in `../pddl-copilot/plugins/<name>/server/` and rerun `bash ../pddl-copilot/plugins/<name>/tests/verify.sh`
- Plugin skill misbehaves, missing a tool, or wrong description → fix in `../pddl-copilot/plugins/<name>/skills/`
- Plugin venv / launch issue → fix in `../pddl-copilot/plugins/<name>/scripts/launch-server.sh` or `requirements.txt`
- Wrong scoring, prompt, ground-truth, or orchestration logic → fix in this repo (`run_experiment.py`, notebooks, `domains/`)

### Commit discipline

Each repo has its own git remote (`SPL-BGU/pddl-copilot-experiments`, `SPL-BGU/pddl-copilot`). Commit in the repo whose tree you edited; never `git add` paths under `../pddl-copilot/` from this repo. When a single change spans both, make two separate commits in the two repos.

### Plugin-isolation rule (inherited from sibling)

When editing across `../pddl-copilot/plugins/`, do NOT cross-import between plugins. Each plugin must remain self-contained and installable standalone. See `../pddl-copilot/.claude/rules/marketplace.md` for the full rule set.
