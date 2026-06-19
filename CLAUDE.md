# pddl-copilot-experiments

Eval harness for the PDDL Planning Copilot paper. `run_experiment.py` orchestrates vLLM-served models with/without MCP planning tools across 5 PDDL tasks (`solve`, `validate_domain`, `validate_problem`, `validate_plan`, `simulate`). The Ollama backend was retired 2026-05-18; the single supported inference client is `pddl_eval.vllm_client.VLLMClient`.

The active flow is **single-task only** as of 2026-05-05; the multi-task chain phase is archived (function bodies preserved in `pddl_eval/{runner,summary}.py`, no longer wired into `run_experiment.py`). Don't add chain references to active code or docs without first re-wiring the dispatch — see `development/CHANGELOG.md` 2026-05-05 entry.

See `README.md` for the sibling-project (`../pddl-copilot/`) background, marketplace discovery, and additionalDirectories permission. The rules below are agent-routing guidance not duplicated elsewhere.

Paper-related decisions and bottom-line conclusions from our discussions are logged in `development/paper_notes_discussions.md` — append a dated, bulleted entry whenever a paper-related topic is decided.

## Paper writing & Overleaf sync

The AAAI-27 paper lives in `paper/` and syncs to an Overleaf project (owned by co-author Yarin) via a **clone-bridge, NOT git-subtree**. Before any paper-sync work, read `development/paper-git-overleaf-instructions.md`. Key rules: paper edits go on the `paper/aaai27` branch; the bridge (`development/sync_overleaf.sh`) only syncs `paper/`; **always `sync_overleaf.sh pull` (+ commit) before `push`** — a blind push clobbers coauthors' Overleaf web edits (the push guards against it). Never force-push to Overleaf (it's prohibited). `paper/` compiles standalone (`aaai2027.sty`/`.bst` live at `paper/` root; do not hand-edit them).

## Routing — where does a fix belong?

- MCP tool returns `{"error": ...}` or wrong-shape output → fix in `../pddl-copilot/plugins/<name>/server/` and rerun `bash ../pddl-copilot/plugins/<name>/tests/verify.sh`
- Plugin skill misbehaves, missing a tool, or wrong description → fix in `../pddl-copilot/plugins/<name>/skills/`
- Plugin venv / launch issue → fix in `../pddl-copilot/plugins/<name>/scripts/launch-server.sh` or `requirements.txt`
- Wrong scoring, prompt, ground-truth, or orchestration logic → fix in this repo (`run_experiment.py`, `pddl_eval/`, `domains/`)

## Commit discipline

Each repo has its own git remote (`SPL-BGU/pddl-copilot-experiments`, `SPL-BGU/pddl-copilot`). Commit in the repo whose tree you edited; never `git add` paths under `../pddl-copilot/` from this repo. When a single change spans both, make two separate commits in the two repos.

## Plugin-isolation rule (inherited from sibling)

When editing across `../pddl-copilot/plugins/`, do NOT cross-import between plugins. Each plugin must remain self-contained and installable standalone. See `../pddl-copilot/.claude/rules/marketplace.md` for the full rule set.
