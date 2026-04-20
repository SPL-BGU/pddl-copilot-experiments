# Development Changelog

Running log of framework and MCP changes that affect experiment behaviour, methodology, or reproducibility. Dated newest-first. Entries reference the files touched so `git log` can pick up the details.

Scope covers both this repo (`pddl-copilot-experiments`) and the sibling MCP plugins at `../pddl-copilot` when those changes are driven from here.

---

## 2026-04-20 — Validator response projection via bridge-pinned `verbose` flag

**Motivation.** Truncation failures on `simulate` and `validate_*` with-tools runs (e.g. 55/55 truncated on qwen3:4b `validate_plan`, qwen0.6b simulate 29/55) were driven in part by the validator plugin returning multi-KB `details` JSON and verbose `report` text that neither the LLM nor the scorer consumed. User direction: resolve by structured projection, not by capping/truncating kept fields.

**Plugin change — `../pddl-copilot/plugins/pddl-validator/server/validator_server.py`**
- `validate_pddl_syntax` gained a `verbose: bool = True` parameter.
  - `verbose=True` (default for standalone MCP callers): `{valid, status, report, details}`.
  - `verbose=False`: `{valid, status, report}`.
- `get_state_transition` gained a `verbose: bool = True` parameter.
  - `verbose=True` (default): `{valid, report, steps, trajectory, details}`.
  - `verbose=False`: `{valid, steps, trajectory}` with full, uncapped `trajectory[*].boolean_fluents` / `numeric_fluents` per step.

**Bridge change — `run_experiment.py::MCPPlanner`**
- New class constant `_PINNED_VERBOSE_FALSE = {"validate_pddl_syntax", "get_state_transition"}`.
- `connect()` strips the `verbose` property from each pinned tool's `inputSchema` before adding it to the tools payload that goes to Ollama.
- `call_tool()` injects `verbose=False` on every pinned-tool invocation.
- Net effect: the experiment agent never sees or controls `verbose`; validator responses arriving at the LLM are always projected.

**Tests — `../pddl-copilot/plugins/pddl-validator/tests/verify.sh`**
- Added four assertions covering both default-verbose and `verbose=False` return shapes for both tools. 15/15 tests pass.

**Docs — `EXPERIMENTS_FLOW.md` §8 and §11**
- §8 now documents the dual-mode validator contract and explicitly notes the bridge's `verbose=False` injection.
- §11 paper-diff table records the methodology delta.

**Compatibility**
- `_parse_validation_verdict` (`run_experiment.py:433-449`) reads only `valid`/`error` — projection is safe.
- `simulate` scorer (`run_experiment.py:769-777`) only checks "non-empty + no error" — projection is safe.
- Prior `results/` `tool_calls[*].result` strings are NOT byte-comparable with post-change runs. Scoring outcomes are.

---

## 2026-04-20 — Cap alignment hygiene (no behavior change)

Existing scattered caps in `../pddl-copilot` normalized to a `DEFAULT_*` module-constant + `PDDL_*` env-override convention. Values unchanged.

| File | Constant | Env var | Default |
|---|---|---|---|
| `plugins/pddl-parser/server/backends.py` | `MAX_GROUNDING_ATTEMPTS` | `PDDL_MAX_GROUNDING_ATTEMPTS` | 10000 |
| `plugins/pddl-parser/server/parser_server.py` | `DEFAULT_MAX_APPLICABLE_ACTIONS` | `PDDL_MAX_APPLICABLE_ACTIONS` | 50 |
| `plugins/pddl-solver/server/solver_server.py` | `MAX_FAILURE_LOG_CHARS` | `PDDL_MAX_LOG_CHARS` | 3000 |
| `plugins/pddl-solver/server/solver_server.py` | `DEFAULT_TIMEOUT` (already aligned) | `PDDL_TIMEOUT` | 120 |

All three plugin `verify.sh` suites still green after extraction (validator 15/15, parser full suite, solver 8/8).

---

## Earlier history

Commits before this log exists are captured in `git log`. Relevant branch: `adapt-to-mcp`. Prior landmark commits:
- `83af87a` skills
- `d378ab5` fix bugs, update docs, and simplify
- `4707a9d` add skills and adapt further
- `59b3c97` / `f25c5b4` adapt to v2.0.0
