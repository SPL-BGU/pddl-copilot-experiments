# Development Changelog

Running log of framework and MCP changes that affect experiment behaviour, methodology, or reproducibility. Dated newest-first. Entries reference the files touched so `git log` can pick up the details.

Scope covers both this repo (`pddl-copilot-experiments`) and the sibling MCP plugins at `../pddl-copilot` when those changes are driven from here.

---

## 2026-04-20 — ISS-014 resolved: `pyval` numeric goal-check fix verified

**Resolution.** Re-ran `mcp__plugin_pddl-validator_pddl-validator__validate_pddl_syntax` against every `domains/**/p01.plan`. All 10 fixtures now report `valid=true`, including `numeric/counters/p01` and `numeric/farmland/p01` which previously failed on numeric `<=` / `>=` goal checks. The arithmetic results match the ones computed by hand in the original ISS-014 evidence block (counters final `c0=12,c1=49,c2=92,c3=93,c4=94`; farmland weighted sum `31.0 ≥ 30.8`).

**Why it fixed itself.** The bug sat in the upstream `pyval.PDDLValidator` goal checker, consumed by `plugins/pddl-validator/server/validator_server.py`. A subsequent `pyval` update (pulled in by a later plugin-venv rebuild) fixed the numeric-comparison path. No experiment-repo change required.

**Implications for scoring**
- Oracle ground truth now returns `gt["plan_valid"]=True` for counters/p01 and farmland/p01, so the asymmetric-scoring failure mode documented in ISS-014 (agents "rewarded for agreeing with the bug") no longer applies.
- `validate_plan`, `solve` (via `_validate_model_plan`), and `simulate` all benefit immediately — no code change needed here.
- Any pre-fix run under `results/` encodes the wrong GT for those two domains; do not compare numeric-domain plan-validity numbers across the fix boundary without the footnote.

**Files.** No edits. Closes ISS-014 (entry removed from `development/OPEN_ISSUES.md`); `domains/README.md` per-domain status table updated to drop the bug notes.

---

## 2026-04-20 — Paper-aligned domain set (10 domains)

**Motivation.** The harness shipped with 3 ad-hoc domains (`blocksworld`, `depots`, `counters`) — 1–5 problems each — while the paper (arXiv:2509.12987) used 10 domains with one problem each. Result tables from this repo therefore could not be aligned to the paper's §5 tables without manual coverage accounting. The paper dataset was present on disk (`.local/pddl_mcp_dataset/`, Aug 2025 snapshot) but detached from the runtime. This change makes `domains/` the paper dataset verbatim so the MCP oracle in `generate_ground_truth()` produces paper-aligned ground truth on every run — no code change needed.

**Data-only change — `domains/`**
- Replaced `classical/{blocksworld,depots}` and `numeric/counters` content with paper versions (one problem each). Deleted leftover `p02.pddl`–`p05.pddl` from those three domains.
- Added seven new domains: `classical/{barman,rovers,satellite}` and `numeric/{depot,farmland,pogo_stick,sailing}`. Each has `domain.pddl`, `p01.pddl` (copied from paper `problem.pddl`), and `p01.plan` (copied from paper `plan.solution` — reference artifact, not read at runtime).
- Skipped paper's `plan.trajectory` (Lisp-text, incompatible with the MCP-JSON shape `get_state_transition` returns for simulate's byte-equal check at `run_experiment.py:856`), `temp_plan.*`, `validation_log.txt`, and `*.txt` domain-description files.
- New `domains/README.md` documents provenance, naming convention, and the expected-validity contract.

**No code changes.** `run_experiment.py`, cluster scripts, and MCP contract are untouched. `load_domains()` already walks `{classical,numeric}/<name>/p*.pddl`, so the new domain set loads automatically.

**Compatibility**
- Existing result JSONs under `results/` encode the old 3-domain coverage and are not directly aggregate-comparable with post-change runs. Each old run remains valid for its 3-domain slice.
- Default invocation patterns for `cluster-experimenting/`, `run_background.sh`, and `remote_background.sh` continue to work unchanged — they just now iterate over 10 domains × 1 problem instead of 3 domains × 1–5 problems.
- Unblocks `ISS-013` (paper-diff audit can now proceed against matching domain coverage). `ISS-001` (no-tools validate_* baseline needs broken fixtures) remains open.

---

## 2026-04-20 — Batch 1: ISS-004 no-tools de-duplication + summary meta

**Motivation.** Per the approved plan in `OPEN_ISSUES.md::Planned batches`, land the zero-risk orchestration win first. The old sweep ran the no-tools condition once per `(tool_filter, prompt_style)` combo — four identical passes per model, since neither knob affects the no-tools branch (`WITHOUT_TOOLS_SYSTEM` is a single string; `TASK_TOOLS` only gates `chat_with_tools`). Closes ISS-004 and the untracked "no host stamp in results" micro-fix.

**Code change — `run_experiment.py`**
- **New `--conditions` flag** (`tools`/`no-tools`/`both`, default `both`). Plumbed into `run_single_task_experiment` (as `conditions: str`) and the chain loop in `async_main`. Expansion helper `_expand_conditions` preserves the legacy `(True, False)` iteration order for `both` so pre-ISS-004 reproductions stay byte-comparable.
- **`save_results` accepts `meta: dict | None`.** `async_main` now passes host, is_remote, conditions, tool_filter/prompt_style (only when with-tools ran), models, tasks, num_variants/ctx/predict, temperature, think. Written under `summary["meta"]`. Rationale: remote-vs-local and split-condition runs were indistinguishable at the summary-JSON level; analysis notebooks had to infer from directory naming.

**Orchestration change — `run_background.sh`**
- One `--conditions no-tools` run up front (output dir `{prefix}_no-tools/`), then the `(FILTER, PSTYLE)` loop runs `--conditions tools` (output dir `{prefix}_tools_{FILTER}_{PSTYLE}/`). Net effect: the full local sweep drops from 4 no-tools passes per model to 1 — ~25% wall-clock savings on the two-model sweep, larger on the BGU four-model sweep.

**Tests — `tests/test_scoring.py`**
- New `test_expand_conditions` (3 assertions) pinning the iteration order for each choice. Full suite now 49 + 35 = 84 green.

**Validation**
- `bash tests/verify.sh` → 84/84 green.
- `python3 run_experiment.py --help` renders `--conditions` in the expected order.
- `save_results` round-trip test confirms `summary["meta"]` present with the expected keys when `meta=` is passed; omitted when `meta=None` (backward-compat).
- Live Ollama smoke test skipped (no local server); MCP handshake and plugin contract already verified in the previous compatibility review.

**Compatibility**
- Default `--conditions=both` preserves paper-reproduction behaviour byte-for-byte — iteration order, prompts, MCP calls unchanged.
- `save_results(meta=None)` matches the pre-batch schema (no `meta` key in summary). Existing `results/*/summary_*.json` files remain valid input to analysis notebooks.
- Result-dir naming under `run_background.sh` changed: `{prefix}_{FILTER}_{PSTYLE}/` → `{prefix}_tools_{FILTER}_{PSTYLE}/` + new `{prefix}_no-tools/`. Gitignored, but any external tooling that globs on the old pattern needs a one-line update.

---

## 2026-04-20 — Scoring audit: tests + B1/B2/B3 fixes

**Motivation.** PR #1 (`adapt-to-mcp`) rewrote the scoring path (`check_success`, two-metric with-tools grading, `FR_*` vocabulary, Wilson CIs) but added zero tests. Review of the branch surfaced three latent bugs that would silently distort metrics. User asked the mechanism to be "verified and tested to behave properly" before trusting new numbers.

**Code change — `run_experiment.py`**
- **B1 (simulate success gate).** `check_success` simulate branch previously scored success on `any(r for r in results) and not _tool_error_seen(...)`. A `{"valid": false, "steps": [...], "trajectory": [partial]}` response satisfied that — but `valid` is a PDDL-syntactic signal, not simulation correctness. New gate: parse each call's `trajectory` and deep-equal against oracle `gt["trace"].trajectory`. Match → `FR_OK`; mismatch → new `FR_RESULT_MISMATCH`; error-shape → `FR_TOOL_ERROR`.
- **B2 (`extract_plan_lines` regex).** `_ACTION_LINE_RE` only matched bare or numbered (`1.` / `1:`) action lines. Extended to accept bulleted lines (`- (action ...)` / `* (action ...)`), since small LLMs often wrap plans in markdown bullets.
- **B3 (`_validate_model_plan` exception path).** Signature is now `bool | None`; MCP transport failure returns `None`, which callers (`check_success` solve branches) map to `FR_TOOL_ERROR` instead of `FR_PLAN_INVALID`. Stops misattributing validator-unreachable runs as invalid-plan runs.
- **New constant.** `FR_RESULT_MISMATCH = "result_mismatch"` added to the `FR_*` block.
- **Truncation override refactor.** Extracted `_apply_truncation_override(success, truncated, failure_reason)` from the inline block in `evaluate_one` so the override logic is testable. No behaviour change.

**Tests — `tests/`** (new directory)
- `tests/verify.sh` — shell entry point matching `../pddl-copilot/plugins/*/tests/verify.sh` pattern. No pytest dependency.
- `tests/_helpers.py` — `FakeMCP` stub, fixture loader, minimal `TestResults` harness.
- `tests/test_scoring.py` — unit tests for `wilson_ci`, `_parse_validation_verdict`, `_tool_error_seen`, `_used_tool`, `_get_tool_results`, `_extract_plan_from_tool_result`, `extract_plan_lines`, `extract_verdict` (46 assertions).
- `tests/test_check_success.py` — table-driven tests for `check_success` across 5 tasks × 2 conditions × tool-call shapes, plus the truncation override helper (35 assertions).
- `tests/fixtures/{blocksworld_p01,counters_p01}.json` — ground-truth + tool outputs generated by real MCP calls through Claude Code's installed plugin; projected to the verbose=False bridge shape.

**Validation**
- `bash tests/verify.sh` → 46/46 + 35/35 green on current code.
- Test cases encode each of B1/B2/B3 as named cases, so any future regression is named in the failure.

**Compatibility**
- `_parse_validation_verdict`, `_tool_error_seen`, and verdict-extraction behaviours all pinned by tests — no change.
- `FR_RESULT_MISMATCH` is additive; existing failure-reasons dicts remain open-ended. `summarize_single_task` and `print_fail_reasons_table` iterate generically, no changes needed.
- Historical `results/*` simulate runs scored as `FR_OK` under the old lenient gate may no longer match when re-scored against post-B1 code. Prior numbers aren't byte-comparable, but the `results/*` directory is gitignored — only future runs see the stricter gate.
- `_validate_model_plan` signature change (`bool` → `bool | None`) has two internal callers (both in `check_success`), both updated in this commit. No external callers.

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
