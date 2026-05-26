# Development Changelog

Running log of framework and MCP changes that affect experiment behaviour, methodology, or reproducibility. Dated newest-first. Entries reference the files touched so `git log` can pick up the details.

Scope covers both this repo (`pddl-copilot-experiments`) and the sibling MCP plugins at `../pddl-copilot` when those changes are driven from here.

---

## 2026-05-26 — Analyzer simplification follow-up (ANALYZER-10 + ANALYZER-13)

**Branch:** `analyzer-10-13-17-simplifications`, opened against `sweep5-new-prompts`. Picks up the two tickets PR-69 deferred (loader unification + figure-builder helpers). ANALYZER-17 (build_deck slide-submodule split) was evaluated and dropped — ANALYZER-13's actual LOC reduction was modest enough that the structural split would have been cosmetic.

- **ANALYZER-10 (loader unification)** — added `iter_cells`, `latest_summary`, `latest_single_task`, `iter_trials` to `_constants.py`. The directory walk + file picker + trial streaming patterns now live once. Rewired call sites: `aggregate.load_summaries`, `plot.load_series`, `drift_check._load_cell`, `drift_check._load_root`, `build_deck.load_all`. `drift_check._aggregate_trials_jsonl` deliberately keeps its own inline JSONL loop — it dedups by trial key and validates `TRIAL_KEY_LEN`, neither of which fits `iter_trials`'s simple `result`-stream shape. The two read-time taxonomy fixes (`FR_TRUNCATED_NO_ANSWER → FR_THINK_OVERFLOW`, FastMCP arg-validation → `FR_TOOL_ERROR`) moved from inline code in `build_deck.load_all` into `iter_trials(relabel=True)`. `drift_check` now imports `parse_dirname_full` directly from `_constants` (the sibling-import from `aggregate` is gone).
- **ANALYZER-13 (figure-builder helpers)** — added `_grouped_arm_bars`, `_arm_legend`, `_panel_grid`, `_label_bars`, `_no_data_panel` to `build_deck.py`. The 7 long figures (fig_tool_selection / fig_failure_breakdown / fig_successful_tool_use / fig_tokens / fig_tokens_vs_success / fig_h1_isolation / fig_h2_isolation_for_model) drop from **576 → 525 lines (−9%)**; the helpers themselves add ~110 lines so `build_deck.py` overall is roughly unchanged in size (1822 → 1843). The win is structural deduplication — arm bar grids, arm legends, and 2×3 panel scaffolding are expressed once. The 30% target stated up front was aspirational; bespoke chart-specific text/annotation/layout code resists further extraction without obscuring intent.
- **ANALYZER-17 (build_deck slide-submodule split)** — **not done**. Premise was that build_deck.py is too long; after ANALYZER-13 it's still 1843 lines, but the figure bodies didn't shrink enough to make a 5-file package split materially easier to navigate. The structural separation argument (state vs stats vs figures vs slides) doesn't outweigh the cost of fragmenting cross-figure helper sharing.

**Validation.** Two reference roots (`results/sweep5-live` exercising per-variant arms, `results/sweep4-v5-v7-first` exercising `*-legacy` fallback) captured pre-refactor to `/tmp/analyzer-refactor-baseline/`. Per-commit gate: sweep5 + sweep4 `aggregate` stdout / `master.{md,csv,tex}` / `drift_check` stdout all byte-equal vs baseline; sweep5 deck structural fingerprint (39 slides; slide titles, captions, image filenames, table cell content) byte-equal. 31 sweep5 deck figure PNGs: 22 byte-equal post-refactor, 9 differ at the sub-pixel level (h1 + h2 legend anti-aliasing, success_by_arm tight_layout 1px height shift from `label_arms=True` legend metadata, tokens_task_validate_problem median-label anti-aliasing). Visual inspection confirmed all 9 are sub-pixel rendering noise, not chart-content regressions. Sweep4 deck build was already broken pre-refactor by an unrelated yerr-negative error in matplotlib's errorbar call (filed mentally; out of scope for this PR).

**Reproducibility.** No methodology change. Existing `results/` corpora load and aggregate to byte-identical Markdown / CSV / TeX outputs. The two read-time taxonomy fixes are unchanged; only their call site moved.

---

## 2026-05-25 — PR-69 review follow-up: palette + bash safety + table fallback

Three small fixes surfaced by a high-effort code review of the simplification PR.

- **`.claude/skills/analyzer/scripts/_constants.py`** — restored `ollama_parse_error` to `FAILURE_REASONS` (between `wrong_tool` and `loop_exhausted`) and its historical color `#9467bd` to `FAILURE_COLORS`. The previous claim that the rows were "legacy pre-vLLM corpora only" was wrong: `pddl_eval.runner` still emits the tag for live vLLM hermes/qwen3_xml/gemma4 parser failures (runner.py:74 documents the retention), so fig4 was silently rebucketing a named failure mode into the gray `'other'` slab. Reverses the corresponding fragment of the 2026-05-25 ANALYZER batch.
- **`.claude/skills/analyzer/scripts/_constants.py`** — `decompose_cond` now returns `("-","-")` on both unparseable branches (non-`tools_*`/non-`no-tools` cond, and `tools_<token>` without an inner underscore), matching the sentinel contract of the deleted inline `_cond_parts` in table.py. Dormant on the active corpus but protects the `tool_filter` column meaning when a malformed cond slips through.
- **`.claude/skills/cluster-ops/scripts/sync.sh`** — added `set -eo pipefail` after the `source _lib.sh` line, matching the belt-and-suspenders pattern in the five sibling scripts. `sync.sh` was the lone holdout, leaving its `SCRIPT_DIR` resolution unprotected.

**Dismissed without fix** (CLAUDE.md "no shims, no hypotheticals"): analyzer import-order brittleness (auto-sort would shuffle `_constants` after `pddl_eval`; relies on documented ordering + `# noqa: E402`, never observed in the wild), and `save_results` 4→3-arg signature break for hypothetical out-of-tree callers (chain-archive deletion was intentional; the in-tree caller is updated).

**Reproducibility.** No corpus migration. Plot fidelity on any results dir with `ollama_parse_error` rows improves (gray slab → named purple slice). Master pivot rows for malformed conds now print `-` in `tool_filter`.

---

## 2026-05-25 — Cross-repo simplification pass (PR: `simplifications` → `sweep5-new-prompts`)

**Branch:** `simplifications`, opened against `sweep5-new-prompts` for a lighter diff. Six independently-reviewable commits driven by a fan-out audit that found dead code, duplicated constants, redundant skill/agent definitions, scattered doc references, and a 2093-line CHANGELOG. No methodology change; existing `results/` corpora remain valid.

**Files touched (by batch):**
- **Harness (HARNESS-01)** — deleted `pddl_eval.runner.run_chain_experiment` (~234 LoC), `pddl_eval.summary.{summarize_chains, print_chain_table}`, `DEFAULT_NUM_CTX_CHAIN`, the `chains` parameter of `save_results`, and the analyzer/SKILL chain leftovers (defensive `"chains": []` synthesis, `--figs 2|7` / `--figs 3` guards). `planbench-integration` was verified to not dispatch chain code; the body is dropped entirely rather than moved to an archive module. `OLLAMA_TOOL_PARSE_SIGNATURES` stays (still used at runner.py:394 in active evaluate_one).
- **Documentation (DOCS-01..12)** — flipped README primary entrypoint to `submit_full_sweep.sh` (matches `cluster-experimenting/README.md`); collapsed Ollama-retirement narration to one-liners; trimmed duplicated model-roster history and num_ctx-16K rationale; added Marketplace 1.4.0 header to EXPERIMENTS_FLOW §8; cross-linked OPEN_ISSUES ISS-020 / ISS-005 from §6 / §9; split CHANGELOG at 2026-05-05 (2093 → 961 lines + `development/CHANGELOG-archive.md` for the ~1132 pre-archive entries).
- **`.claude/` meta (META-01..09)** — folded the `simplifier` agent's review rubric into `.claude/skills/simplify/SKILL.md` and deleted the agent (the skill is now self-contained); tightened `.claude/agents/cluster-ops.md` to a thin dispatcher over the skill; added symmetric "Skill boundary" blocks to `analyzer` and `cluster-ops` SKILL.md; replaced ≥5 verbatim `_PINNED_VERBOSE_FALSE` bridge-caveat restatements with one-line links to EXPERIMENTS_FLOW §8; pruned `.claude/skills/cluster-ops/cleanup.md` (delete the Ollama-era Scenario A + 2026-05-18 worked example, keep Scenario B + quarantine convention); routed `experiment-runner` smoke failures to the `debug-and-simplify` skill; replaced its hardcoded CLI invocation with a `--help` pointer; pruned 6 stale entries from `settings.local.json`.
- **Analyzer (ANALYZER-01..09, 11, 12, 14, 15, 16)** — hoist shared constants and helpers into `.claude/skills/analyzer/scripts/_constants.py`: `TASKS`, `TASK_LABELS`, `CONDITIONS`, `RETIRED_CONDS`, `MODEL_COLORS`, `COND_HATCH`, `THINK_LIGHTEN`, `_lighten`, `find_default_root`, `host_tag`, three distinct `parse_dirname_*` variants, `arm_side` / `arm_variant_set`, `decompose_cond`. Unified `FAILURE_REASONS`/`FAILURE_COLORS` on the vLLM-era build_deck ordering (legacy `ollama_parse_error` rows bucket into `other`). build_deck keeps its deck-specific lowercase `TASK_LABEL` (intentionally distinct from plot.py's title-case). Two dead `if len(TASKS) == 1` branches removed. ANALYZER-10 / 13 / 17 (loader unification + build_deck slide-submodule split) deferred to a follow-up PR per user direction.
- **Cluster-ops (CLUSTER-01..04, 08, 10, 12)** — new `_lib.sh` carries the `set -eo pipefail` guard, `:=`-overridable `REMOTE_USER` / `REMOTE_HOST` defaults, and a `_show_help` helper; six callers source it. In status.sh, `jname_to_cell` and `jname_model` unify behind a single `parse_jname` returning `(model, think|None, cond|None)`; the inline `c == "no-tools-steered"` skip is named via a new `is_queue_attributed_cell` helper. postmortem.sh now counts and reports malformed sacct lines instead of dropping them silently. CLUSTER-06/11 (false positive — postmortem has no REASON breakdown), CLUSTER-07 (pace/ETA refactor), CLUSTER-14 (parse_elapsed_h regex) deferred.
- **Tests + tools (TOOLSTEST-01..06, 08, 10)** — extended `tests/_helpers.py` with `make_stub_result`, `make_stub_evaluate_one`, and the `stubbed_evaluate_one` async context manager; migrated four sites in `test_runner.py` and one in `test_prompts.py`. In `tools/build_fixtures.py`, collapsed three near-identical MCP validator wrappers behind one `_validate` helper; promoted retry / plan-truncate padding magic numbers to module constants. Ollama mentions dropped from test docstrings. TOOLSTEST-03 / 07 / 09 deferred (chicken-and-egg with sys.path setup; pytest not in use).

**Audit false positives caught** during the planning phase (not acted on):
- HARNESS-02: `OLLAMA_TOOL_PARSE_SIGNATURES` is still used by active code.
- HARNESS-03: tests do import the `_*` helpers via `import run_experiment as rx`; the re-exports stay.
- HARNESS-05: `relabel_tool_arg_error_taxonomy` IS called from `.claude/skills/analyzer/scripts/build_deck.py` (legacy-corpus recovery, commit a7dc6bf).
- HARNESS-07: `NEUTRAL_VARIANTS` placement in `summary.py` is intentional per CHANGELOG.

**Reproducibility.** Existing `results/` corpora load and parse unchanged. `summary_*.json` no longer carries the `"chains": []` field (analyzer never read it post-archive); legacy corpora still have it and the analyzer ignores it. `tests/verify.sh` passes (8/8 test files green). `aggregate.py` against `results/sweep5-cluster-20260524` produces the expected per-cell rows.

**Net LoC.** ≈+560 / −920 across the six commits (chain delete dominates).

---

## 2026-05-25 — Recover FastMCP arg-validation errors via `_tool_error_seen` extension + read-time relabel

**Branch:** `sweep5-new-prompts`. Surfaced by a fan-out audit of the sweep-5-live with-tools `validate_plan` confusion-matrix FP column. 3,718 with-tools `validate_plan` rows across the 5 model cells were tagged `FR_VERDICT_MISMATCH` for plans labeled `b*` (INVALID truth); the analyzer's `confusion()` treats that as `pred = NOT truth` → counts the row as a confident wrong prediction (FP). Empirical breakdown showed 90.7% (3,373) of those rows had every `validate_plan` tool call return a FastMCP pydantic argument-validation error string of the shape `"Error executing tool validate_plan: N validation errors for validate_planArguments\n  problem\n    Field required ..."` (typical causes: model omits the `problem` field, wraps args as `_raw_arguments`). `pddl_eval.scoring._tool_error_seen` only recognized two error prefixes — `"Tool error"` (transport) and `{"error":true}` (plugin-side JSON) — so this third FastMCP prefix escaped both and the scorer fell through to `FR_VERDICT_MISMATCH` (and analogous `FR_RESULT_MISMATCH` / `FR_PLAN_INVALID` paths for `simulate` / `solve`).

**Two-prong fix mirroring the 2026-05-25 `think_overflow` change.** (i) Forward fix in `_tool_error_seen` so new trials land in `FR_TOOL_ERROR`. (ii) Read-time relabel at analyzer load time so existing sweep-5 corpora recover the bucket without mutating `trials.jsonl`. Sweep-5 is still in flight on some arms; a one-shot in-place re-score would split a single `trials.jsonl` across two classification regimes (corpus-identity hazard per `feedback_pushback_on_methodology_shortcuts`).

**Files touched.**
- `pddl_eval/scoring.py` — extracted `_TOOL_ERROR_PREFIXES = ("Tool error", "Error executing tool")` tuple; `_tool_error_seen` now uses it. Added pure helper `relabel_tool_arg_error_taxonomy(failure_reason, *, task, tool_calls) -> str` co-located with `relabel_truncated_taxonomy`. `check_success` is unchanged.
- `.claude/skills/analyzer/scripts/build_deck.py` — imports and applies the new relabel immediately after `relabel_truncated_taxonomy` in the `load_all` per-trial loop. In-memory mutation only.

**Relabel predicate (read-time).**

```
if  failure_reason ∈ {verdict_mismatch, result_mismatch, plan_invalid}
AND task ∈ {validate_plan, validate_domain, validate_problem, simulate, solve}
AND some tool_call.name matches the task's tool(s) AND its result starts with
    "Tool error" or "Error executing tool"
THEN failure_reason = tool_error
ELSE failure_reason unchanged
```

Task→tool map in `_ARG_ERROR_TOOL_NAMES_BY_TASK`: validate_* → eponymous tool; simulate → `get_state_transition`; solve → `classic_planner` or `numeric_planner`.

**Empirical validation** (on `results/sweep5-live`, with-tools `validate_plan`, FP-as-defined-by-analyzer = `failure_reason==verdict_mismatch AND plan_label.startswith("b")`):

| Cell | FP before | FP relabel→tool_error | residual genuine FP |
|---|---:|---:|---:|
| Qwen3.5-0.8B think=off | 1592 | 1589 (99.8%) | 3 |
| Qwen3.5-0.8B think=on  | 1140 | 1134 (99.5%) | 6 |
| Qwen3.5-4B   think=off |  285 |  285 (100%)  | 0 |
| Qwen3.5-4B   think=on  |  516 |  344 (66.7%) | 172 |
| Qwen3.5-9B   think=off |   72 |   17 (23.6%) | 55 |
| Qwen3.5-9B   think=on  |   41 |    1 (2.4%)  | 40 |
| gemma4-26b   think=off |   17 |    0 (0%)    | 17 |
| gemma4-26b   think=on  |   13 |    0 (0%)    | 13 |
| qwen3.6-35b  think=off |   26 |    0 (0%)    | 26 |
| qwen3.6-35b  think=on  |   16 |    3 (18.8%) | 13 |
| **TOTAL**              | **3718** | **3373 (90.7%)** | **345** |

The 345 residual FPs are the genuine `tool ratified broken plan as VALID` cases. They concentrate in Qwen3.5-4B think=on (172) and Qwen3.5-9B (55 think=off + 40 think=on) — both small-Qwen think-on cells that pre-audit had little think-on data; subsequent appends grew them. The audit reproduced 5 such cases against pyvalidator directly and found 0 cases where pyvalidator and the MCP validate_plan plugin disagreed on the actual `b*` fixture — in every "tool says VALID" case the model had repaired the plan (added a missing action) before passing it to the tool, and the tool legitimately accepted the repaired plan.

**Compatibility note.** `trials.jsonl` files are unchanged. Decks built before this change remain valid as pre-relabel snapshots. Decks built after will show: per-cell with-tools `validate_plan` FP / FN counts drop; `tool_error` (no_ans) counts rise by the same amount; FR_OK counts unchanged; aggregate precision / recall / accuracy values shift accordingly. Same relabel applies to `validate_domain`, `validate_problem`, `simulate`, and `solve` rows that exhibit the same FastMCP arg-validation shape; sweep-5 numerics for those tasks should be re-skimmed.

Partially closes ISS-005 — the `(d) FastMCP arg-validation` sub-pattern (added 2026-05-19 with PR-50 adoption) is now correctly in-bucket as `FR_TOOL_ERROR` rather than absorbed into `FR_VERDICT_MISMATCH` / `FR_RESULT_MISMATCH` / `FR_PLAN_INVALID`. The longer-term `FR_TOOL_ARG_ERROR` / `FR_TOOL_PARSE_ERROR` / `FR_TOOL_TRANSPORT` split remains optional polish (P3) and is not included here.

---

## 2026-05-25 — Recover `think_overflow` via read-time taxonomy relabel

**Branch:** `sweep5-new-prompts`. Surfaced while building the sweep-5-live checkpoint deck: fig4 showed `truncated_no_answer` as the only post-cap failure bar on Qwen3.5 think=on cells, with zero `think_overflow` rows across 106k trials. Empirical probe pinpointed the cause: `pddl_eval.scoring._classify_step_failure` (the FR_THINK_OVERFLOW predicate) requires `thinking_text != ""` AND `response_text == ""` AND `done_reason == "length"`, but vLLM's `--reasoning-parser qwen3` only flushes `reasoning_content` after seeing a complete `<think>…</think>` block — so when the output-token cap fires mid-`<think>`, both the `thinking` and `response` fields come back empty and the predicate's middle conjunct fails. The truncation override at `scoring._apply_truncation_override` then tagged all such rows `FR_TRUNCATED_NO_ANSWER`, conflating "reasoning spiral consumed the budget" with "response was cut off mid-output."

**Scope of this change: ANALYZER ONLY.** Sweep-5 is still in flight (multiple cells partial; control arm not yet submitted). Modifying the runtime classifier now would split a single `trials.jsonl` across two classification regimes — a corpus-identity hazard. Instead, the fix is a *read-time relabel* on values already present in the saved rows; `trials.jsonl` files are unchanged. The runtime predicate fix is deferred until sweep-5 completes and lands as a separate clean change.

**Files touched.**
- `pddl_eval/scoring.py` — added `relabel_truncated_taxonomy(failure_reason, *, truncated, response, think_mode) -> str` pure helper. `_classify_step_failure` and `_apply_truncation_override` are intentionally unchanged.
- `pddl_eval/summary.py` — `summarize_single_task` gains a `think_mode: str | None = None` kwarg, threaded into the aggregation loop so the relabel runs at FR-counting time. `save_results` pulls `think_mode` from `meta["think"]` and passes it through. Print helpers (`print_*_table`) are unchanged — they're console diagnostics, not analysis artifacts, and stay backward-compatible via the default-`None` kwarg.
- `.claude/skills/analyzer/scripts/filter_variants.py` — pulls `think_mode` from source meta first, with a `_think_from_dirname` fallback that parses `slurm_vllm_<model>_<think>_<cond>` cell directories.
- `.claude/skills/analyzer/scripts/build_deck.py` — applies the relabel at `load_all` (in-memory mutation of each loaded trial's `failure_reason` field). All downstream FR consumers (confusion grids, simulate FR slabs, per-cell FR Counters) inherit the corrected tag without further code changes.

**Relabel predicate (read-time).**

```
if   truncated == True
AND  failure_reason ∈ {truncated_no_answer, plan_invalid, no_verdict_parsed,
                       simulate_empty, format_parse_fail, unknown}
AND  response == ""
AND  think_mode == "on"
THEN failure_reason = think_overflow
ELSE failure_reason unchanged
```

The `think_mode == "on"` gate honors honesty: a probe across all 30 sweep-5 cells found 364 think=off Qwen3.5-with-tools rows that would otherwise be mis-labeled as think_overflow (the small Qwen3.5 sizes occasionally emit `<think>` blocks even under think=off; the vLLM parser eats them, leaving empty fields). The gate keeps those as `truncated_no_answer`. gemma4 (no reasoning parser) has zero empty-response truncations across all cells, so it's auto-safe.

**Empirical validation** (on `results/sweep5-live` post-relabel):

| Cell                              | Task           | n   | think_overflow | truncated_no_answer | Notes |
|----------------------------------|----------------|----:|---------------:|--------------------:|-------|
| Qwen3.5-0.8B on/no-tools          | solve          | 300 | 299            | 0                   | reasoning ate budget |
| Qwen3.5-0.8B on/no-tools          | validate_plan  |3000 | 3000           | 0                   |  |
| gemma4-26B on/no-tools            | solve          | 300 | 0              | 266                 | gemma has no think block — stays truncated |
| Qwen3.5-0.8B off/tools_all_minimal| solve          | 600 | 0              | 344                 | honesty gate held |
| Qwen3.5-4B off/no-tools           | validate_plan  |3000 | 0              | 53                  | verdict_mismatch=726 preserved (informative tag wins) |

ST success rates are unchanged across all 30 cells — the relabel only moves counts inside the failure buckets.

**Reproducibility.** Pre-2026-05-25 `summary_*.json` files in checkpoints have the old taxonomy. Re-running `filter_variants.py` (with no other arg changes) regenerates them with the corrected taxonomy. `trials.jsonl` files are the canonical raw record and remain bit-identical. The relabel helper is a pure read-time function — analyses can be re-aggregated to either taxonomy by toggling the call site, although the post-fix taxonomy is the recommended default.

**Risks / follow-ups.**
- The runtime `_classify_step_failure` predicate still ships the (now-known-unsatisfiable) `thinking_text` conjunct. Production runs continue to write `FR_TRUNCATED_NO_ANSWER` to `trials.jsonl` for would-be `FR_THINK_OVERFLOW` rows; analyzers correct this at read time. Once sweep-5 finishes, lift the relabel logic into `_apply_truncation_override` (drop the `thinking_text` conjunct, gate by `response_text == ""` instead). The read-time helper then becomes a no-op on fresh data but stays for historical sweeps.
- Pre-existing `tests/test_summary_arm.py` fixture errors are unrelated to this change (TestResults class with __init__ blocks pytest collection — surfaced before this branch).

---

## 2026-05-24 — Arm-aware analyzer for the sweep-5 four-arm matrix

**Branch:** `sweep5-new-prompts`. Driven by `development/sweep_prompt_bank_design.md` §0 — the analyzer (build_deck / plot / aggregate / table / plot_focused) now renders and tabulates the sweep-5 arms `(nt-neut, nt-ster, tl-neut, tl-ster)` explicitly rather than collapsing them into the pre-sweep-5 `(no-tools, tools_all_minimal)` cond axis.

**TL;DR.** One shared arm classifier (`pddl_eval.summary.arm_for`) is the single source of truth for every analyzer script; all five scripts agree on what an arm is and how legacy (sweep-3/4, v0-v10) corpora map to `*-legacy` arms. `summary._token_row` gains `completion_median` (a sweep-5 H3 primary outcome per the design doc §0). build_deck adds H1 and H2 isolation slides, drops the 5 per-task input-token slides + collapses the input column from `fig_tokens`. plot.py gains `--by-arm` + `--arms <subset>` flags; table.py gains an `arm` column; aggregate.py emits per-arm rows from `per_variant`. plot_focused.py adds `--figs h1` for the supervisor-friendly H1 panel.

**Design-doc anchor (must read before tuning the analyzer further).** The four-arm matrix and H1/H2/H3/H4 hypotheses live in `development/sweep_prompt_bank_design.md` §0. The analyzer surfaces the **primary outcomes** (`result_correct`, `tool_selected`, output-token median/mean, `FR_*` distribution including the new `FR_WRONG_TOOL`); Bonferroni correction is paper-side, not analyzer-side. H3/H4 dedicated plots are deferred — the data is readable off the existing per-arm panels.

**Shared classifier.** `pddl_eval.summary.arm_for(with_tools: bool, prompt_variant: int) -> str` returns one of `{nt-neut, nt-ster, tl-neut, tl-ster, nt-legacy, tl-legacy}`. Imported by `plot.py`, `aggregate.py`, `table.py`, `build_deck.py`, and `plot_focused.py`. Reuses `STEERED_VARIANTS` from `pddl_eval.prompts`; the new `NEUTRAL_VARIANTS = frozenset({11, 12, 13})` lives in `summary.py` (the split is an analysis concept, not a runner emit/dispatch concept).

**Token-median schema bump.** `_new_token_agg` gains an internal `completion_samples: list[int]`; `_add_tokens` appends each trial; `_token_row` emits `completion_median` (stdlib `statistics.median`). The list is never serialized — only the median surfaces in `summary_*.json`. Memory cost ~70KB/cell, negligible. `filter_variants.py` regen surfaces the new field for in-flight sweep-5 cells; consumers default to `0.0` when the field is absent (pre-bump summaries).

**Analyzer changes per script:**
- **`pddl_eval/summary.py`** — adds `arm_for()`, `NEUTRAL_VARIANTS`, `completion_median`. `_token_row` schema is additive (existing consumers unaffected).
- **`.claude/skills/analyzer/scripts/aggregate.py`** — adds an `arm` column to the success-rate matrix; rows synthesized by pooling each `single_task` record's `per_variant` cells. Pre-`per_variant` corpora fall through to a single `*-legacy` row. The failure-reason table keeps its whole-cell prefix (FR isn't arm-tagged in `summary_*.json`); per-arm FR breakdowns live in `build_deck` / `plot_focused`.
- **`.claude/skills/analyzer/scripts/plot.py`** — `--by-arm` adds `split_series_by_arm()` which produces one synthetic series per `(dir, arm)` with Wilson CIs recomputed on the pooled arm n. `--arms <subset>` filters to a chosen pair for H1 (`nt-neut,tl-neut`) or H2 (`tl-neut,tl-ster`). `--merge` and `--by-arm` are mutually exclusive. `fig4` (failure breakdown) auto-skips under `--by-arm` because per-arm FR can't be derived from `summary_*.json` without re-aggregating from trials.jsonl. `fig3` / `fig6` "no-tools exclude" filters generalized to `cond == "no-tools" or cond.startswith("nt-")`.
- **`.claude/skills/analyzer/scripts/table.py`** — adds `arm` to `META_COLS`; one row per `(cell × arm)`; legacy corpora collapse to a single `*-legacy` row. Wilson CIs recomputed on pooled arm n via the shared helpers. Adds a `out-med` column per task (n-weighted mean of per-variant output-token medians — see Risks below for the weighting caveat) so the H3 metric surfaces alongside succ%/tool%/trunc%.
- **`.claude/skills/analyzer/scripts/build_deck.py`** — `CELLS` re-keyed from `(model, think, cond)` to `(model, think, arm)` via row-level `arm_for()`. New `ARM_ORDER` / `ARM_DISP` globals (legacy `COND_ORDER` / `COND_DISP` kept as optional deck_config fields for back-compat). `fig_tokens` is now 1-column (output only, was 2-column input + output); 5 per-task input-token slides removed; per-bar label is `mean (m:median)`. New `fig_h1_isolation` + `fig_h2_isolation` slides (sweep-5 H1 / H2 headline); both return `None` and the slide is skipped when the relevant arms are absent (e.g. sweep-3/4 replay), so legacy decks don't ship empty bar charts. Confusion-grid pinned to `nt-neut` (sweep-5) / `nt-legacy` (sweep-3/4) via `_pick_no_tools_neutral_arm`. `TOKEN_NOTE_BULLETS` rewritten for output-only accounting. `find_malformed_simulate_samples` re-anchored to the H1 baseline arm. Dead `_color_for_cond` alias removed (all callers migrated to `_color_for_arm`).
- **`.claude/skills/analyzer/scripts/plot_focused.py`** — adds `fig_h1` (`--figs h1`): 2-bars-per-model × 5-task panels for the H1 isolation read. Existing fig1/fig2/fig4-8 unchanged.
- **`tests/test_summary_arm.py`** — new file. 45 assertions: `arm_for()` matrix (legacy + neutral + steered boundary), `NEUTRAL_VARIANTS` ∩ `STEERED_VARIANTS` disjoint, `completion_median` round-trip + empty-cell handling + empty-tokens skipping, per_variant arm-pooling invariant (no silent cross-arm aggregation at source). Registered in `tests/verify.sh`.

**Files touched.**
- `pddl_eval/summary.py` (arm_for, NEUTRAL_VARIANTS, completion_median).
- `.claude/skills/analyzer/scripts/{aggregate,plot,table,build_deck,plot_focused}.py`.
- `.claude/skills/analyzer/SKILL.md` (--by-arm / --arms / --figs h1 docs).
- `tests/test_summary_arm.py` (new) + `tests/verify.sh` (registration).

**Compatibility.**
- **Sweep-3/4 corpora** continue to render unchanged via `*-legacy` arms. Smoke-tested against `results/sweep4-v5-v7-first`: aggregate, plot, table, build_deck all produce the same shape as before (one row/series per cell, arm=`nt-legacy`/`tl-legacy`).
- **Sweep-3/4 deck_configs** load unchanged (`COND_ORDER` / `COND_DISP` made optional; `ARM_ORDER` derived from data when absent).
- **`filter_variants.py` is unchanged** — it remains the single-arm-root tool; the arm-aware analyzer is the complementary one-shot view. Existing `sweep5-{neutral,steered,both}` checkpoints continue to work.
- **`summary_*.json` schema** is additive (`completion_median`); consumers default to `0.0` when absent. `_new_token_agg` schema gains an internal `completion_samples` list but never serializes it. No existing consumer breaks.
- **No experiment-result impact.** Trial-key 10-tuple unchanged; no runner / sbatch / scoring change.

**Tests.**
- `bash tests/verify.sh` — green across all 8 test files (test_scoring, test_check_success, test_fixtures, test_runner, test_drift_check, test_partial_subset, test_prompts, test_summary_arm).
- `python3 -m py_compile` on all five analyzer scripts — clean.
- Smoke renders: `results/sweep5-live` deck produces H1 + H2 + by-arm token slides (arms detected: `nt-neut, tl-neut, tl-ster`; nt-ster control not yet submitted, slot dropped per user direction). `results/sweep4-v5-v7-first` legacy deck produces `nt-legacy + tl-legacy` arms — no crashes.
- `plot.py --by-arm --arms nt-neut,tl-neut` (H1) and `--arms tl-neut,tl-ster` (H2) both render to suffixed output dirs (`plots/by_arm_<arms>/`).

**Risks / known limitations.**
- The `out-med` cell in `table.py` is an n-weighted mean of per-variant medians, not a true arm-level median. Medians don't compose by averaging; for sweep-5 each arm has 3 variants with similar n so the approximation is close, but for paper headline numbers, recompute the median from `trials.jsonl` via `build_deck`'s `_completion_median` (which has access to the raw per-trial values). Documented in the `out-med` `_pool_per_variant` docstring.
- H3 / H4 don't have dedicated isolation figures yet. H3 (token efficiency, with-tools < no-tools on per-success output tokens) is readable off the existing per-arm token panel; H4 (control falsification) becomes relevant only when the `(no-tools, steered)` 4th-arm control is submitted — flagged for a future pass when that data lands.

Closes no `ISS-###`. This is the design-doc implementation, not an open-issue triage.

---

## 2026-05-23 — PR-67 follow-up: runner restore-key, ETA denom, sbatch flag plumbing, focused-plots tools

**Branch:** `sweep5-new-prompts`. Closes the four real-risk findings from the PR-67 `code-review` pass; the two low-severity findings (legacy-corpus rescoring and `filter_variants --arm both` asymmetric `--min-out`) are intentionally not addressed — see Triage below.

**Fixes:**
- **runner.py emit-skip ordering** (`pddl_eval/runner.py:_emit_job`). The `(no-tools, v_steered)` skip-gate now sits BELOW `in_scope_keys.add(key)` and the restored-trial early-return, so trials already on disk from a prior `--include-no-tools-steered` submit are surfaced in this run's summary even when the flag is now off. Only new job enqueue is suppressed. Pre-fix, a control submit's on-disk v14-16 no-tools rows silently disappeared from per-cell summaries on any rerun launched without the flag.
- **status.sh dir_totals activity-gate** (`.claude/skills/cluster-ops/scripts/status.sh`). The dir-level denom for `pace_s` / `eta_h` previously summed both arms' denoms unconditionally (4560 + 4560 = 9120), inflating ETA ~2× for any no-tools cell when the steered arm was dormant (i.e. main-only sweep with no `--include-no-tools-steered` control submit). Now `tools_all_minimal` dirs always sum both arms (one sbatch always emits v11..v16 together), while `no-tools` dirs include the steered arm's denom only when that arm has on-disk evidence. Spurious "over 0.9×budget" watch lines disappear.
- **`--include-no-tools-steered` plumbing** (`cluster-experimenting/submit_with_rtx.sh`, `run_condition_vllm_rtx.sbatch`). New wrapper flag exports `INCLUDE_NO_TOOLS_STEERED=1` into the sbatch env, which appends `--include-no-tools-steered` to both the smoke fastpath and the inner-loop `python3 run_experiment.py` invocation. `submit_full_sweep.sh` and `submit_with_resume.sh` already forward arguments verbatim, so the flag reaches the wrapper unchanged. Without this, the sweep-5 control arm could only be launched by manual sbatch surgery — the `nt-ster` column in `status.sh` had no producer.
- **plot_focused.py validator vocabulary** (`.claude/skills/analyzer/scripts/plot_focused.py`). `MCP_TOOLS` and `MCP_TOOL_LABELS` extended with the three marketplace-1.4.0 names (`validate_domain` / `validate_problem` / `validate_plan`). Legacy `validate_pddl_syntax` retained for pre-1.4.0 corpus replay. Sweep-5 focused plots now bucket validator calls correctly instead of dropping them.

**Doc:**
- **EXPERIMENTS_FLOW.md §12.6** gained a paragraph on the `tool_selected` definition shift between sweep-3/4 and sweep-5: pre-1.4.0 `tool_selected=True` whenever the polymorphic validator was called regardless of argument shape; post-1.4.0, `tool_selected=True` requires the task-matching name (wrong-tool call → `FR_WRONG_TOOL`, `tool_selected=False`). Cross-sweep panels should treat the legacy rate as `tool_selected + FR_WRONG_TOOL` (a "validator-family invoked" union) when plotting sweep-3/4 alongside sweep-5.

**Triage (dropped):**
- Legacy `validate_pddl_syntax` calls rescored under new code grade as `FR_TOOL_NOT_SELECTED` (no compat shim). PR is forward-only on scoring per §12.6; pre-1.4.0 corpora stay as pin-locked snapshots, not rescored.
- `filter_variants --arm both --min-out N` cannot gate asymmetric per-cell budgets (9120 with-tools vs 4560 no-tools) with one threshold. The two-pass recipe in `analyzer/SKILL.md` ("Checkpoint a sweep") already mitigates; adding a guard would block a flag invocation that nobody runs against single-arm sweeps in practice.

**Files touched:**
- `pddl_eval/runner.py` (emit-skip ordering)
- `.claude/skills/cluster-ops/scripts/status.sh` (dir_totals activity-gate)
- `cluster-experimenting/submit_with_rtx.sh` (flag parsing + export)
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` (flag forwarding to both invocation paths)
- `.claude/skills/analyzer/scripts/plot_focused.py` (validator vocabulary)
- `EXPERIMENTS_FLOW.md` (§12.6 tool_selected disclosure)
- `development/CHANGELOG.md` (this entry)

**Compatibility.** No experiment-result impact. Trial-key 10-tuple shape unchanged → existing checkpoints from sweep-3/4/4.1/5-smokes remain resume-compatible. Status cache schema unchanged. `filter_variants.py` defaults unchanged. The `--include-no-tools-steered` flag was already harness-side; this only unlocks the wrapper path.

**Verification.**
- `bash -n` on `submit_with_rtx.sh`, `run_condition_vllm_rtx.sbatch`, `status.sh` — all clean.
- `python3 -m py_compile pddl_eval/runner.py .claude/skills/analyzer/scripts/plot_focused.py` — clean.
- `bash tests/verify.sh` — green (covers runner.py emit-skip dispatch + scoring `wrong_tool` paths).

---

## 2026-05-23 — Code-review fixes to the sweep-5 matrix propagation

**Branch:** `sweep5-new-prompts`. Follows the two same-day matrix entries below (`Make sweep-5 neutral/steered split explicit` and `Propagate sweep-5 matrix to ops layers`). Triggered by an extra-high-effort `code-review` pass over the unstaged matrix work; 12 findings landed, all surgical, no methodology impact.

**Status.sh fixes:**
- **#1 Watch-list dedupe** — `watch` loop now tracks a `seen_dirs` set keyed by `dir_cell` so each underlying tools_all sbatch produces at most one watch row. Pre-fix, `tl-neut` and `tl-ster` both mapped to the same dir and each emitted an entry for one physical job. Watch labels now name the dir-level sbatch (e.g. `qwen3.6:35b on/tools_all_minimal`) since the ETA covers both halves of the run.
- **#3 Dir-level pace/eta** — `deltas[cell]["pace_s"]` and `["eta_h"]` were computed from per-logical-column deltas, giving ~2× too-slow pace and ~2× too-pessimistic ETA for any `tools_all` cell. Now aggregated by `LOGICAL_TO_DIR_COND[c]` into a `dir_totals` dict, then written back to each logical child. Siblings show identical pace/eta as a "same sbatch" visual cue. Δ-table rows still split by logical column for visibility.
- **#4 `--help` truncation** — header docstring extended past the prior `sed -n '2,18p'` window after the matrix-doc rewrite; bumped to `2,40p`.
- **#5 `started_now` gate** — the `prev == 0 → started_now` branch now also requires `now < denom`. Without it, cells that arrived already-complete (post-upgrade cache key mismatch → `prev=0`) would mis-render as `▶🆕 started (4560/4560)` instead of silently passing through. The post-upgrade noise floor is otherwise ~30 fake bullets per first run.
- **#6 Sweep-4 replay** — new `steered_enabled` flag (mirrored from `STEERED_VARIANTS_RE`) threaded into the embedded Python via `sys.argv[5]`. When False, the four `*-steered` columns drop from `CELLS` and `COL_HEADERS`, and the steered counts aren't written into `counts`. Replay collapses cleanly to 4 columns × 5 models = 20 cells, no phantom `tl-ster ▶` at 0%.
- **#8 `n_neutral` clamp warning** — `n_steered > n_active` (caused by overlapping/misconfigured regexes) now emits a single stderr `warn:` line summarizing the discrepancy across affected dirs. Run still completes.
- **#9 Dead legacy keys** — `cell_label` shed the legacy `tools_per-task_minimal` / `tools_all_minimal` / `no-tools` entries and the misleading "kept so Δ renders meaningfully" comment. `.get(c, c)` fallback retained for unmapped keys.
- **#10 Malformed-line warning** — counts parser now counts dropped lines (bad shape, non-int) and emits a stderr `warn:` if `count_raw` was non-empty but the matrix was empty. Catches a remote-heredoc wire-format regression instead of silently rendering 0% everywhere.

**filter_variants.py fixes:**
- **#7 `_ARM_VARIANTS` mutation hazard** — presets switched from `set` to `frozenset` so a future `args.variants.add(...)` (latent today, plausible tomorrow) can't silently corrupt the module-level dict.
- **#12 Mutex error consistency** — `--arm` / `--variants` mutex now calls `p.error(...)` (argparse standard exit 2 + usage banner) instead of `sys.exit("error: ...")` (exit 1, no banner). Matches `_parse_variants`'s `ArgumentTypeError` path.

**SKILL.md fix:**
- **#2 Recipe correctness** — the "Checkpoint a sweep" recipe used a single `--arm both` + `--min-out 4560` call that admitted half-finished with-tools cells (4560-9119 of 9120 trials) into the published checkpoint. Rewritten to two passes (`--arm neutral --min-out 4560` + `--arm steered --min-out 4560`), with the result roots named `<name>-neutral` and `<name>-steered`. Sweep-4 replay still uses the single-pass `--variants 5,6,7 --min-out 4560` path.

**CHANGELOG fix:**
- **#11 Compatibility paragraph** — the prior 8-col entry described first-run-after-upgrade as "Δ first-renders every cell as freshly-started" — accurate for the empty-Δ case but understating the wider misclassification. Rewritten to acknowledge fix #5's role in narrowing the impact and to keep the `rm` workaround front-of-mind for unfixed deployments.

**Files touched (this commit):**
- `.claude/skills/cluster-ops/scripts/status.sh` (sys.argv threading, `steered_enabled` filter, malformed warning, oversteered warning, dir_totals pace/eta, watch-list dedup, started_now gate, cell_label cleanup, --help range).
- `.claude/skills/analyzer/scripts/filter_variants.py` (`frozenset` presets, `parser.error` mutex).
- `.claude/skills/analyzer/SKILL.md` (Checkpoint recipe → two-pass arm-aware).
- `development/CHANGELOG.md` (this entry + Compatibility-paragraph rewrite on the entry below).

**Compatibility.** No experiment-result impact. Status cache behaviour: fix #5 narrows the upgrade-cycle mis-classification (no more fake `started_now` for already-complete cells). The `rm ~/.cache/cluster-ops-status.json` workaround is no longer required, but remains the most conservative path. `filter_variants.py` defaults unchanged; the `frozenset` change is API-compatible at every call site (membership + `sorted()` only — verified).

**Verification.**
- `bash -n status.sh` + `ast.parse` on embedded PY — both pass.
- `python3 -m py_compile filter_variants.py` — clean.
- Synthetic-payload smoke covering: (a) sweep-5 main with running with-tools sbatch (verify single watch row, identical sibling pace/eta), (b) sweep-4 replay with `STEERED_VARIANTS_RE=''` (verify 4-column collapse, no phantom rows), (c) pre-split cache (verify completed cells don't mis-render as started_now). All pass.
- `filter_variants.py --arm neutral --variants 14,15,16 ... → argparse banner + exit 2.

---

## 2026-05-23 — Make sweep-5 neutral/steered split explicit in status + analyzer

**Branch:** `sweep5-new-prompts`. Follow-up to the same-day matrix-propagation entry below (user feedback: "isn't there a steered vs neutral? … it should be explicit not implicit").

**TL;DR.** The first cut split only the no-tools arm into a main (neutral) and a control (steered) column; the with-tools column kept a 9120-trial pooled denom that hid the v11-13 vs v14-16 breakdown. This commit splits BOTH arms — every dir's trials are now classified into a neutral or steered logical column, so H1 (tl-neut vs nt-neut) and H2 (tl-ster vs tl-neut) are directly readable from the status board.

**Schema change.**
- `status.sh` matrix: 6 logical columns → **8 logical columns**. CELLS now covers `{no-tools-neutral, no-tools-steered, tools_all-neutral, tools_all-steered} × {on, off}`. All four logical conds have uniform `DENOM=4560`. New `LOGICAL_TO_DIR_COND` map handles queue/running attribution from the dir-level cond back out to its logical children (with-tools sbatch fills both `tl-neut` and `tl-ster` siblings simultaneously). `no-tools-steered` remains the one column without queue inheritance — main and control sbatches share `cond=no-tools` jnames.
- Watch-list iteration now maps logical cells through `LOGICAL_TO_DIR_COND` before looking up `cell_running`; previously the logical-vs-dir mismatch would have silently skipped every cell.
- `total_expected` rolls up to 40 (5 models × 8 columns); coverage caps at 75% on a main-only sweep (control fills the remaining 25%).

**Analyzer ergonomics.**
- `filter_variants.py` gains an `--arm {neutral,steered,both}` flag (mutually exclusive with `--variants`). `--arm neutral` = {11,12,13}, `--arm steered` = {14,15,16}, `--arm both` = full active set (default). `--variants` stays available for sweep-4 replay and ad-hoc subsets.
- `.claude/skills/analyzer/SKILL.md` checkpoint recipe rewritten around `--arm`; sweep-4 replay example kept on `--variants 5,6,7`.

**Doc updates.**
- `.claude/skills/cluster-ops/SKILL.md` — status section now describes the 8-column matrix with an arm-semantics table.
- `.claude/skills/cluster-ops/scripts/status.sh` — header comment block rewritten; `cell_label` short-tag dict adds the four split conds; markdown + terminal renderers use the new 8-col `short_hdrs`.

**Files touched (this commit, on top of the earlier propagation):**
- `.claude/skills/cluster-ops/scripts/status.sh` — CELLS, DENOM, COND_SPLIT, LOGICAL_TO_DIR_COND, cell_status, cell_label, watch list, short_hdrs / CELL_W, header docstring.
- `.claude/skills/cluster-ops/SKILL.md` — 8-column status doc + arm-semantics table.
- `.claude/skills/analyzer/scripts/filter_variants.py` — `--arm` flag + `_ARM_VARIANTS` presets; docstring rewritten around `--arm`.
- `.claude/skills/analyzer/SKILL.md` — `filter_variants` examples switch to `--arm` (explicit-not-implicit framing).
- `development/CHANGELOG.md` — this entry.

**Compatibility.** Status cache from before the 8-col split is read but its keys (`no-tools`, `tools_all_minimal`, `no-tools-steered`) don't match the new logical keys, so `prev_counts.get(cell, 0)` returns 0 for every new logical cell. On the first post-upgrade run, `d["prev"] == 0` for every populated cell — without the follow-up `now < denom` gate (see the same-day "Code-review fixes" entry above), even already-100%-complete cells would mis-render as `▶🆕 started_now`. Recommended workaround: `rm ~/.cache/cluster-ops-status.json` before the first post-upgrade run; the follow-up fix narrows the impact for sessions where the rm is forgotten. No harness change. `filter_variants.py --variants` still accepts arbitrary sets; `--arm` is purely additive.

**Verification.**
- `bash -n` + `ast.parse` on `status.sh` — both pass.
- Smoke-test of `status.sh`'s Python parser against a synthetic 2-dir payload (no-tools 3000/1000 + tools_all 4500/1500) — emits the 8-col table with correct per-column splits (2000/1000/3000/1500 of 4560).
- `python3 -m py_compile` + `--help` on `filter_variants.py` — `--arm` choices render.

---

## 2026-05-23 — Propagate sweep-5 matrix to ops layers (status / submit docs / analyzer defaults)

**Branch:** `sweep5-new-prompts`. Follows commit `ed3a46e` (the prompt-bank + variant-gated dispatch landing) — this entry is the operational propagation of the new matrix into the cluster wrappers and the two `.claude/skills/` skills, so the next status check + submit + analysis don't silently use sweep-4 settings.

**TL;DR.** The harness-side sweep-5 work shipped in `ed3a46e` (v11/v12/v13 neutral + v14/v15/v16 steered; `STEERED_VARIANTS` emit-skip gated by `run_experiment.py --include-no-tools-steered` for the 4th-arm control). This follow-up updates everything *around* the harness:

- **`status.sh`** — `ACTIVE_VARIANTS_RE` default flips from the single-char `[567]` to `1[1-6]` (sweep-5 active set). New `STEERED_VARIANTS_RE` (default `1[4-6]`) splits per-cell no-tools counts into a main column and a synthetic `no-tools-steered` (nt-ctrl) column showing the 4th-arm control fill rate. Per-cell denominators turn asymmetric: `no-tools` and `no-tools-steered` = 4560 each; `tools_all_minimal` = 9120 (sweep-5 with-tools emits 6 variants vs 3 for no-tools; 1520 trials/variant from sweep-3 corpus per `CHANGELOG.md:714`). The remote grep loop now emits `<n_active>\t<n_steered>\t<dirname>` so the local parser can split. Sweep-4 replay is preserved as `ACTIVE_VARIANTS_RE='[567]' STEERED_VARIANTS_RE='' bash status.sh`. The `nt-ctrl` cell never inherits queue/running attribution from its sibling no-tools row (both submits share `cond=no-tools` jnames — status can't distinguish queue state).
- **`sync.sh`** — default DEST renamed `results/sweep3-cluster-…/` → `results/sweep5-cluster-…/`.
- **`.claude/skills/cluster-ops/SKILL.md`** — status doc rewritten to describe the 6-column matrix, asymmetric denominators, and the `--include-no-tools-steered` control workflow. Submit recipe reframed around `submit_full_sweep.sh` with the 20-cell main / control split called out.
- **`.claude/skills/analyzer/scripts/filter_variants.py`** — default `--variants` flips from `{5, 6, 7}` to `{11, 12, 13, 14, 15, 16}`; help text + module docstring rewritten with sweep-5 neutral-only (H1) / steered-only (H2) / sweep-4-replay recipes.
- **`.claude/skills/analyzer/SKILL.md`** — `filter_variants` section + "Checkpoint a sweep" recipe rewritten around sweep-5 defaults and asymmetric `--min-out` (no-tools 4560 vs with-tools 9120); sweep-4-replay example kept alongside as known-good reference per user direction.
- **`cluster-experimenting/README.md`** — `2 × 3 matrix` → `2 × 2 matrix` (sweep-3-era third cond was already gone), cell-count math `30 → 20`, stale `no-tools/think=on gate` sentence corrected, sweep-5 within-cell variant axis + control submit pattern documented in §Conditions.
- **`cluster-experimenting/submit_with_rtx.sh`** — `--all` doc math corrected (`4 models × 6 cells = 24` → `5 models × 4 cells = 20`); smoke-block "4-model pack" → "default model pack (5 models)".
- **`cluster-experimenting/setup_env.sh`** — "submit 4-model pack as ONE rtx_pro_6000 job" → `submit_full_sweep.sh` (20 cells across 3 sbatch arrays).
- **`.claude/skills/analyzer/scripts/plot_focused.py`** — header docstring decouples `DEFAULT_CHECKPOINT` from the (still-valid) historical baseline; explicit comment that current-sweep figures need `<root>` passed.
- **`.claude/skills/analyzer/scripts/build_deck.py`** — docstring reframes `sweep4-v5-v7-first/deck_config.py` as the worked example to copy + edit for a sweep-5 deck.

**Files touched (this commit):**
- `.claude/skills/cluster-ops/scripts/status.sh` (regex defaults, remote heredoc, parsing, render, comments).
- `.claude/skills/cluster-ops/scripts/sync.sh` (default DEST).
- `.claude/skills/cluster-ops/SKILL.md` (matrix doc + submit recipe).
- `.claude/skills/analyzer/scripts/filter_variants.py` (default + docstring).
- `.claude/skills/analyzer/scripts/plot_focused.py` (`DEFAULT_CHECKPOINT` comment + usage doc).
- `.claude/skills/analyzer/scripts/build_deck.py` (docstring).
- `.claude/skills/analyzer/SKILL.md` (`filter_variants` section + Checkpoint recipe).
- `cluster-experimenting/README.md` (matrix shape, cell counts, conditions section).
- `cluster-experimenting/submit_with_rtx.sh` (--all examples + smoke + --all comments).
- `cluster-experimenting/setup_env.sh` (post-install hint).
- `development/CHANGELOG.md` (this entry).

**Compatibility.** No harness behaviour change — only docs, defaults, and a status.sh data-shape extension. Sweep-3/4/4.1 replay paths preserved (override `ACTIVE_VARIANTS_RE` + `STEERED_VARIANTS_RE` on the wrapper side; `filter_variants.py --variants 5,6,7` works as before). Status cache file (`~/.cache/cluster-ops-status.json`) format unchanged at the file level — new sweep-5 cells just add `no-tools-steered` keys; pre-existing keys remain readable. Closes no `ISS-###`.

**Verification.**
- `bash -n .claude/skills/cluster-ops/scripts/status.sh` — bash parses.
- The embedded Python block in `status.sh` parses (ast.parse).
- `python3 -m py_compile` on all touched analyzer scripts.
- `python3 .claude/skills/analyzer/scripts/filter_variants.py --help` — new default + example text renders.
- Live `status.sh` against the cluster — deferred to next user-initiated run; output shape change is purely additive (new columns and labels).

---

## 2026-05-23 — Retire the Ollama inference backend

**Branch:** `sweep5-new-prompts`. Commit `9cdf2da` (the backend cut) plus this entry's follow-up.

**TL;DR.** Removes the entire Ollama path from the harness after the 2026-05-18 cluster backend unification. Single inference client is now `pddl_eval.vllm_client.VLLMClient` (renamed from `VLLMOllamaClient`). No-op for active sweeps — sweep-4/5 have been vLLM-only since the cluster swap.

**Files touched (commit `9cdf2da`):**
- `requirements.txt` — drop `ollama>=0.4.0`. `openai>=1.40.0` is the live runtime dep.
- `pddl_eval/vllm_client.py` — class rename `VLLMOllamaClient → VLLMClient`; ctor kwarg `host=` → `base_url=`; docstring rewritten to describe the OpenAI↔harness-shape adapter without claiming to "mimic Ollama".
- `pddl_eval/chat.py`, `pddl_eval/runner.py` — drop `import ollama` (TYPE_CHECKING), retype `client: "ollama.AsyncClient"` forward-refs to `"VLLMClient"`, reword comments. `FR_OLLAMA_PARSE_ERROR = "ollama_parse_error"` and `is_ollama_parse_error` JSON key retained as stable corpus identifiers (per `scoring.py:30-31` policy). `OLLAMA_TOOL_PARSE_SIGNATURES` variable name kept (internal, unchanged semantics); comment notes the signatures now catch vLLM tool-call parser failures (hermes / qwen3_xml / gemma4) too.
- `run_experiment.py` — drop `import ollama`, `--inference-backend`, `--ollama-host` (replaced by `--llm-base-url`, env `LLM_BASE_URL`), and the `OLLAMA_NUM_PARALLEL` warning print. `meta.inference_backend` no longer written to summary JSON. Help text refreshed.
- `cluster-experimenting/submit_with_rtx.sh` — drop `--backend ollama|vllm` flag; single sbatch path (`run_condition_vllm_rtx.sbatch`). Default GPU now `rtx_6000:1`; `--gpu-type rtx_pro_6000` remains the opt-in escape.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` — exported env var rename `OLLAMA_HOST → LLM_BASE_URL`; drop `--inference-backend vllm` flag from the inner `run_experiment.py` invocations (no longer recognized).
- `cluster-experimenting/submit_full_sweep.sh`, `submit_with_resume.sh` — drop `--backend vllm` forwarding; collapse the Ollama branch in the resume orchestrator.
- `cluster-experimenting/setup_env.sh` — import probe `mcp + ollama` → `mcp + openai`.
- `cluster-experimenting/run_condition_rtx.sbatch` — DELETED (Ollama sbatch).
- `run_background.sh` — DELETED (macOS laptop driver that ran `ollama serve`).
- `notebooks/run_single_model.ipynb`, `notebooks/run_vllm_vs_ollama_smoke.ipynb` — DELETED.
- Docs: `README.md`, `CLAUDE.md`, `EXPERIMENTS_FLOW.md`, `cluster-experimenting/README.md`, `.claude/agents/{experiment-runner,simplifier}.md`, `.claude/skills/{cluster-ops/{SKILL,cleanup},debug-and-simplify/SKILL,simplify/SKILL,plan-review-simplify/SKILL}.md` — sweep misleading present-tense Ollama references; preserve historical context with date stamps where the history is load-bearing.

**Follow-up commit (`<current>`):**
- `development/CHANGELOG.md` — this entry (missing from `9cdf2da`, the simplifier review flagged).
- `.claude/skills/cluster-ops/scripts/status.sh` — drop the per-model `BACKEND = {…}` map, the `dir_backend = "ollama"` branch, and the "skipped N dirs on non-canonical backend" diagnostic. Single-backend now means the BACKEND check is permanently dead-code. Replaced with a one-line informational "archived pre-vLLM dirs ignored" footer.
- `.claude/skills/plan-review-simplify/SKILL.md` — drop `run_background.sh` reference; "Ollama chat loop" → "vLLM chat loop" (the parallel `simplify/SKILL.md` update from `9cdf2da` didn't reach this sibling).
- `run_experiment.py:687-690`, `cluster-experimenting/submit_with_rtx.sh:313-319`, `.claude/skills/cluster-ops/cleanup.md:42` — three stale comments citing the deleted `run_background.sh` / `run_condition_rtx.sbatch`.

**Verification:**
- `python3 -c "from pddl_eval import chat, runner, vllm_client, scoring, summary, prompts, resume, domains"` — all imports clean.
- `python3 run_experiment.py --help` — argparse renders, `--inference-backend` and `--ollama-host` gone, `--llm-base-url` present.
- `python3 -m pytest tests/test_vllm_client.py` — 3/3 pass. Wider `pytest tests/` total identical pre- and post-refactor (pre-existing `TestResults`-as-class collection issue in `tests/_helpers.py:110` unrelated to this change).
- `grep -rn "VLLMOllamaClient\|--inference-backend\|--ollama-host\|import ollama\b" pddl_eval/ run_experiment.py cluster-experimenting/` — empty.

**Compatibility:**
- Active sweeps: no-op. Sweep-4/5 invocations went through `submit_with_rtx.sh` with the vLLM defaults that this commit codifies.
- Archived `slurm_<model>_*` (Ollama-era) corpora in `results/` and `checkpoints/`: read-only. Their `meta.inference_backend = "ollama"` field is still parsed by JSON loaders; nothing in the analyzer pipeline consumes it (verified across `.claude/skills/analyzer/scripts/{aggregate,filter_variants,plot,build_deck,drift_check}.py`).
- Forward-only: new summaries omit `meta.inference_backend`.
- Single inference backend means the `slurm_vllm_<…>` OUT_DIR prefix is now historical (originally introduced to disambiguate vLLM cells from parallel Ollama cells). Renaming would invalidate resume keys mid-sweep, so the prefix stays.

**Memory updates** (off-tree, in the user's auto-memory store): `reference_bgu_ollama.md`, `reference_bgu_self_deploy_ollama.md` marked as retired/historical; `feedback_status_backend_first.md` repositioned around parser-mismatch as the new contamination class; new `project_ollama_retired.md` entry summarising the cut.

---

## 2026-05-23 — Sweep-5 phase A.1: `FR_WRONG_TOOL` + helper inline + cleanup

**Branch:** `sweep5-new-prompts`. Follow-up to the Phase A migration (`beab87a`).

**TL;DR.** Phase A's mechanical migration silently shifted the `FR_TOOL_NOT_SELECTED` bucket: under the polymorphic predecessor it meant "no `validate_pddl_syntax` call at all", but Phase A also routed wrong-validator-tool calls (e.g. `validate_problem` invoked on a `validate_plan` task) into the same bucket. Cross-sweep selection-rate comparisons would have conflated these. Phase A.1 introduces `FR_WRONG_TOOL` so the three failure modes (no validator family / wrong validator / right validator wrong verdict) are reported separately — strictly more informative than the polymorphic predecessor allowed.

**Files touched:**
- `pddl_eval/scoring.py` — new `FR_WRONG_TOOL = "wrong_tool"` constant + `_VALIDATE_TOOL_NAMES` frozenset; three-way split in `check_success` validate branch (right tool → existing verdict-grading path; validator-family but not task-matching → `FR_WRONG_TOOL`; nothing validator-family at all → `FR_TOOL_NOT_SELECTED`); `_call_matches_validate_task` deleted (production-dead after Phase A — `check_success` had collapsed to inline `tc["name"] == task`).
- `run_experiment.py:66-93` — re-export `FR_WRONG_TOOL` from scoring.
- `tests/test_scoring.py::test_call_matches_validate_task` — deleted along with the helper. Behavior coverage moved to `test_check_success.py` (the three FR outcomes are exercised against `validate_plan` and `validate_domain` tasks).
- `tests/test_check_success.py` — two existing "wrong tool" cases now assert `FR_WRONG_TOOL`. New explicit `FR_TOOL_NOT_SELECTED` case where the model called `classic_planner` (non-validator-family) so the three-way split is fully exercised.
- `.claude/skills/analyzer/scripts/plot.py` — `wrong_tool` added to `FAILURE_REASONS` + `FAILURE_COLORS`. Prevents the sweep-4 audit's "anonymous grey 'other' slice" bug from recurring on `validate_*` cells.
- `EXPERIMENTS_FLOW.md` — §4.1 metrics note rewritten to enumerate the three FR outcomes; §9 `failure_reasons` description adds `FR_WRONG_TOOL` to the notable-tags list with its semantics + provenance ("never appears in pre-marketplace-1.4.0 trials").
- `pddl_eval/{scoring,chat,domains}.py` + `tests/_helpers.py` — migration-narrative docstring boilerplate trimmed from five sites. The migration story belongs in this CHANGELOG, not in docstrings that should describe current behavior.
- `development/CHANGELOG.md` — fixed misleading parenthetical in the 2026-05-23 Phase A entry that claimed `_call_matches_validate_task` was called by `check_success` (it wasn't, post-Phase-A).

**Verification:** `bash tests/verify.sh` — 6 test files, all pass.

**Compatibility:**
- Pre-marketplace-1.4.0 trials in `results/` and `checkpoints/` never carry `FR_WRONG_TOOL` (the marketplace surface couldn't produce it). The analyzer whitelist addition is forward-only; historical plots are byte-identical.
- Cross-sweep aggregation: `(FR_TOOL_NOT_SELECTED + FR_WRONG_TOOL)` in sweep-5 is the apples-to-apples counterpart of `(FR_TOOL_NOT_SELECTED + wrong-shape subset of FR_VERDICT_MISMATCH)` in sweep-3/4. The latter is recoverable from stored `tool_calls[*].arguments` if direct comparison is needed in the paper.
- No prompt-bank work yet (still on `sweep5-new-prompts` branch; Phase B is the design-doc rewrite + Phase C the `prompts.py` / `runner.py` implementation).

---

## 2026-05-23 — Marketplace 1.4.0 adoption: validator tool split (sweep-5 foundation)

**Branch:** `sweep5-new-prompts`. **Marketplace pin:** post-PR-52 (pddl-copilot @ `2850bc4`, marketplace `1.4.0`).

**TL;DR.** Sibling-repo PR-#52 split the polymorphic `validate_pddl_syntax` into three task-aligned tools — `validate_domain`, `validate_problem`, `validate_plan` — whose JSON schemas enforce their required arguments. The dominant sweep-3/sweep-4 `validate_plan` failure mode (model calls validator with only `domain`+`problem`, tool returns the consistency verdict instead of the plan verdict, scorer tags `FR_VERDICT_MISMATCH`) is now structurally unreachable — the model can no longer call a polymorphic tool with wrong-shape arguments. Cross-repo migration in this commit; no prompt-bank changes yet (those land in a follow-up commit on the same branch).

**Files touched (this repo):**
- `pddl_eval/chat.py:86` — `_PINNED_VERBOSE_FALSE` updated from `{"validate_pddl_syntax", "get_state_transition"}` to `{"validate_domain", "validate_problem", "validate_plan", "get_state_transition"}`. Docstring at `:58` updated to reference the split.
- `pddl_eval/scoring.py:65-88` — `_call_matches_validate_task` collapses from an argument-shape dispatcher to a name match: `tc["name"] == task` for the three `validate_*` tasks. The old polymorphism gate (rejecting domain-only calls when grading `validate_plan`) is no longer needed.
- `pddl_eval/scoring.py:271-292` — `_validate_model_plan` routes to `validate_plan` directly (was `validate_pddl_syntax`).
- `pddl_eval/scoring.py:408-426` — `check_success` validate branch uses `_used_tool(tool_calls, task)` (task-name == tool-name) instead of looking up the legacy polymorphic tool name.
- `pddl_eval/domains.py:112-130` — `_validate_capture` routes by args to the correct task-aligned tool (presence of `plan` → `validate_plan`; `problem` → `validate_problem`; else → `validate_domain`). Keeps the six call sites in `generate_ground_truth` uniform.
- `tools/build_fixtures.py:105-125` — `_validate_domain` / `_validate_problem` / `_validate_plan` helpers route to their matching tools.
- `tests/_helpers.py:64-99` — `plan_sensitive_validator` handler dispatches by tool name (not arg shape); `validate_plan` still matches plan-text against the fixture's oracle/bad plan.
- `tests/test_check_success.py` — two cases recharacterized: the old "wrong arg shape" failures (which grade as `FR_VERDICT_MISMATCH` under the polymorphic tool) become "wrong tool name" failures (graded as `FR_TOOL_NOT_SELECTED`). The model can no longer call the same tool with wrong-shape args; calling a different validator tool is the residual error.
- `tests/test_scoring.py::test_call_matches_validate_task` — rewritten to assert the simplified name-match semantics. Includes a defensive case for the legacy `validate_pddl_syntax` tool name (always returns False).
- `EXPERIMENTS_FLOW.md` — §3 task table, §4.1 metrics list, §6 ground-truth list, §8 MCP API table, §11 paper-diff row updated to the three-tool surface.

**Verification.** `bash tests/verify.sh` — 6 test files, 401/401 assertions pass.

**Compatibility notes.**
- v0–v10 prompt strings are byte-stable (no edits). Replay-by-rerun of sweep-3 / sweep-4 / sweep-4.1 cells against the new marketplace pin will fail: the model can no longer call `validate_pddl_syntax` (tool removed). This is intentional per user direction (`feedback_pushback_on_methodology_shortcuts`); sweep-3/4/4.1 results in `results/` and `checkpoints/` remain valid as historical snapshots tied to their respective marketplace pins.
- Recorded `tool_calls[*].name` in old `trials.jsonl` continues to read `"validate_pddl_syntax"`. Legacy trials were graded at write-time and stored their `failure_reason` in the record; analysis paths read the stored field rather than re-running `check_success`, so the new tool-name expectations don't disturb historical aggregation.
- Sweep-5 starts fresh on the marketplace 1.4.0 pin. Trial-key shape unchanged (10-tuple); no `runner.py` resume-key edits.

**Sources of the split design (per PR-52 description):** Anthropic "Define tools" docs (3-4 sentence per-tool descriptions, schema-in-`tools=[]` convention), Anthropic engineering "Writing tools for agents" (consolidation, namespacing, "implicit context explicit"), BFCL methodology (relevance / selection / parameter-filling decomposition).

**Next on branch `sweep5-new-prompts`:** rewrite `development/sweep_prompt_bank_design.md` to reflect (a) Option C thin per-task system prompts, (b) post-split simplified one-sentence steered directives, (c) sweep-5 as full (no-tools, steered) backed-up arm — then implement in `pddl_eval/prompts.py` + `pddl_eval/runner.py`.

---

## 2026-05-20 — PR-#66 contamfix: `_CTX_OVERFLOW_RE` regex + analyzer denominator drifts + gemma context limitation

**TL;DR.** Six-agent audit (PR-#66) of the sweep-4 corpus surfaced four root issues. One was the dominant data-quality problem (24 600 corrupted trials across the corpus; 24 in the active checkpoint). Three were latent analyzer denominator bugs that mask themselves on clean data but mis-aggregate on edge-case rows. All four addressed in one commit.

1. **`pddl_eval/vllm_client.py` `_CTX_OVERFLOW_RE` regex didn't match the new vLLM error body** ("upper bound for N input tokens" vs the old "at least N input tokens"). When the parser returned None the BadRequestError re-raised out of `chat()`, the runner's generic `except Exception` caught it, and the trial landed as `FR_EXCEPTION` with `tokens={}` and `tool_selected=None` — exactly the corruption pattern the existing retry-and-synthesize path was designed to prevent. Single-line regex extension `(?:at least|upper bound for) (\d+) input tokens` matches both shapes; verified empirically against contaminated rows. New `tests/test_vllm_client.py` pins both shapes so the next vLLM-message-text change trips a unit-test failure instead of silently corrupting a sweep.

2. **`.claude/skills/analyzer/scripts/build_deck.py:201-209` `tool_selected_rate` denominator** filtered `r.get("tool_selected") is not None`, dropping trials that crashed before tool-selection could be classified. On a cell with 24 such rows (gemma4 simulate, the cleanup target above), the function reported **100% tool-selection vs the canonical 92%** — an 8-point inflation. Canonical denominator in `summary.py:186-188` is every with-tools trial in the cell. Fix mirrors canonical.

3. **`build_deck.py:268-300` `token_stats` denominator** included rows with empty `tokens={}` (numerator contributes 0, denominator inflated by 1). On the same gemma simulate cell every token mean was biased downward by exactly 8% (`prompt_mean` 10979 reported vs 11934 canonical). Canonical `_add_tokens` in `summary.py:49-65` skips empty-tokens trials. Also: `turns` default fixed from `1` to `0` to match canonical; per-turn ratios now skip turns==0 trials to avoid div-by-zero. `base` subset still drives `fail_pct` (all trials), `sub` drives means (token-bearing only).

4. **`.claude/skills/analyzer/scripts/plot.py:94-99` `FAILURE_REASONS` whitelist** was missing `format_parse_fail` and `think_overflow`. Trials with these tags were silently bucketed into the unnamed grey "other" slice on `fig4_failure_breakdown`. On the Qwen3.5-0.8B off/no-tools cell, **85.6% of validate_domain failures and 69.9% of validate_plan failures** rendered as anonymous "other" — the dominant failure mode for no-tools cells with the v5/v6/v7 prompt rewrite was unattributed. Added both to `FAILURE_REASONS` + `FAILURE_COLORS`.

**Contamfix cleanup (separate from this commit, local only).** 24 corrupted rows dropped from both source and filtered gemma `on/tools_all_minimal` cells; summaries regenerated; `checkpoints/sweep4-v5-v7-first/gemma4_26b_a4b_trials.zip` refreshed. `.bak_contamfix` files preserved next to each cleaned `trials.jsonl` for one-cycle reversibility. Source-dir sweep-3 residue (52 rows, `prompt_variant=1`, `APIConnectionError` from pre-`a8c09a4` runs) deliberately not touched per user direction (already excluded by the `{5,6,7}` filter).

**Methodology finding — gemma4:26b-a4b context limitation (ISS-021).** With the regex fix landed, the 24 gemma `simulate` trials that previously corrupted will now land as `FR_TRUNCATED_NO_ANSWER` — caught and accountable, but the model never gets to attempt those tasks (prompt is 6× the 16 384-token cap). Will reoccur identically on every resubmit. **Accepted as a documented limitation; `--max-model-len` is NOT being changed.** Affected (domain, problem) pairs documented in OPEN_ISSUES ISS-021.

**Verification cancelled cluster jobs (separate cluster-ops step).** All 11 running + pending sweep-4 jobs were cancelled prior to this commit landing so the resubmit (gated on a separate explicit go) runs against the fixed runner. Resubmit will refill the gemma cell to 4560 with 24 `FR_TRUNCATED_NO_ANSWER` rows in the previously-corrupted slots.

**Files touched.**
- `pddl_eval/vllm_client.py:60-78` — regex extension + drift-history doc-block.
- `tests/test_vllm_client.py` — new file; 3 regression tests (old body, new body, unrelated-400 negative).
- `.claude/skills/analyzer/scripts/build_deck.py` — `tool_selected_rate` denominator (line 201); `token_stats` denominator + turns default (lines 268-300).
- `.claude/skills/analyzer/scripts/plot.py:94-122` — `FAILURE_REASONS` + `FAILURE_COLORS` add 2 entries.
- `development/OPEN_ISSUES.md` — new ISS-021 entry for the gemma context limitation.
- `development/CHANGELOG.md` — this entry.

**Files NOT touched.**
- `pddl_eval/runner.py` — no need; the regex fix routes context-overflow back through the existing `_synthesize_overflow_response` path. Adding a `BadRequestError` catch in the runner would have masked unrelated 400s.
- `pddl_eval/summary.py` — already canonical; the audit confirmed it as the reference.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch:202` — `--max-model-len 16384` retained per ISS-021 decision; gemma simulate failures on big problems documented, not engineered around.
- Sweep-3 source corpus — out of scope per user direction.

---

## 2026-05-20 — PR-#66 review fixes: infra_failure summary filter, bounded retry abort, status.sh anchoring

**TL;DR.** Four small follow-ups on top of `dce5e29` / `6350c0c` / `b74bdd1` / `fba91e5` / `a8c09a4`, addressing items raised in the second PR-#66 review pass:

1. **`infra_failure` records now filtered from the runner's returned list** (`pddl_eval/runner.py:843`). Previously the JSONL writer correctly skipped these (so `trials.jsonl` stayed canonical and resume was correct), but `run_single_task_experiment` returned the in-memory list unfiltered. Downstream `save_results` → `summarize_single_task` therefore wrote per-cell summary JSONs that counted transport-blip records (e.g. SLURM SIGTERM races) toward `total` / `failure_reasons`. On-disk corpora are unaffected — the analyzer aggregates from `trials.jsonl` — but a truncated run could persist a misleading per-cell summary. Docstring at `runner.py:241–247` corrected (writer lives in `run_one`, not `run_single_task_experiment`).

2. **Bounded consecutive-`infra_failure` abort** (`pddl_eval/runner.py:_INFRA_FAIL_ABORT = 7`). The broad `APIConnectionError` catch added in `a8c09a4` correctly treats SLURM-SIGTERM-near-TIMEOUT races as infra blips, but blindly silently-skipping every connection error could mask a wedged vLLM (wrong port, OOM-loop, crashed at startup). After 7 consecutive infra fails the runner now raises `RuntimeError`, propagating up to `main`'s `KeyboardInterrupt`-style "save partial results" path. SLURM gets a non-zero exit; resume re-attempts the in-flight keys on rerun. Counter resets on any successful trial so transient bursts don't compound across the cell.

3. **`status.sh` regex anchored + grep I/O errors surfaced** (`.claude/skills/cluster-ops/scripts/status.sh:80–94`). The variant filter `"prompt_variant": $VARIANTS_RE` (default `[567]`) would silently match the first digit of a two-digit variant if sweep-5+ ever introduced v10/v15/etc.; now anchored with a trailing `[^0-9]` so the character class binds to the JSON value's terminator (comma). Separately, `2>/dev/null || echo 0` was swallowing real grep errors (rc≥2) as zero counts; now explicit on exit code so rc=1 (no match) → 0 silently but rc≥2 (real I/O error) prints a warn line to stderr.

4. **`development/sweep4_plan_new_prompts.md` stale table marked.** The plan-doc table at lines 17–22 said `tools_per-task_minimal` retirement was "deferred to sweep-5," contradicting `cluster-experimenting/lib/defaults.sh:32` and the 2026-05-19 sweep-4 finalisation entry which pulled the retirement forward. One-line revised stripe added above the table so readers landing on the plan-doc first see the current standing policy.

**Methodology / reproducibility.** No change to trial wire format; `TaskResult.infra_failure` already populated. Sweep-4 data on disk is fine — analyzer reads `trials.jsonl`, never the polluted summary JSONs. The bounded-abort flips an in-progress wedge from "silently produce an empty corpus" to "fail loud with a non-zero SLURM exit," which is the correct posture for an unattended cluster sweep.

**Files touched.**
- `pddl_eval/runner.py` — `_INFRA_FAIL_ABORT` constant; consecutive-fail counter in the `asyncio.as_completed` loop; `new_results` filter; docstring fix.
- `.claude/skills/cluster-ops/scripts/status.sh` — anchored regex; explicit rc=2+ warn path.
- `development/sweep4_plan_new_prompts.md` — revised-stripe note above the deferred-retirement table.
- `development/CHANGELOG.md` — this entry.

**Files NOT touched.** `pddl_eval/summary.py` (defense-in-depth filter intentionally skipped — runner-boundary filter is the actual fix and is sufficient); `pddl_eval/vllm_client.py`; any sbatch.

---

## 2026-05-19 — Adopt pddl-copilot marketplace 1.3.0 (PR-50 merged as `a259a38`)

**TL;DR.** Sibling marketplace bumped to 1.3.0 (solver 2.1.1→2.2.0, validator 2.1.1→2.2.1, parser 1.4.0→1.5.0). Two real bugs fixed upstream: solver crashes (INTERNAL_ERROR / UNSUPPORTED_PROBLEM / INTERMEDIATE / Java-missing) now surface as `{"error": True, ...}` instead of silently masquerading as empty-plan no-finds; validator `report` no longer leaks the misleading `"Plan is VALID"` / `"Plan is INVALID"` line on domain-only / domain+problem calls (fix lives in pyvalidator 0.1.5 upstream). **Zero code change required in this repo** — the framework bridge already (a) reads `valid` not `report` in `_parse_validation_verdict` (chat.py:58-71), (b) detects `{error: True}` in `_tool_error_seen` (scoring.py:295-313), and (c) connects only `pddl-solver` + `pddl-validator`, so every pddl-parser change in PR-50 is out of scope. PR description's sibling-agent validator pass and an independent re-read both returned SAFE.

**Methodology consequence (the headline).** Pre-PR-50, solver crashes were classified as `FR_PLAN_INVALID` on the `solve` task (scoring.py:380): the model was charged with a failure that was actually the planner blowing up. Post-PR-50 the same crashes correctly route to `FR_TOOL_ERROR` via the existing `_tool_error_seen` path (scoring.py:376-379). **`solve` pass% does not move** — both buckets are `result_correct=False` — but the attribution is now honest. Java-missing ENHSP runs especially benefit (was silently invisible).

**Possible second-order effects on sweep-4 (deliberately measured before lock-in).**
- `validate_domain` / `validate_problem` with-tools: clean `report` may marginally shift VERDICT accuracy on small models that were parroting the leaked "Plan is VALID" line. Direction is not predictable a priori — the leak either helped (lucky parroting on actually-valid cases) or hurt (parroting on actually-invalid cases).
- `solve` with-tools FR-histogram: small `FR_PLAN_INVALID` → `FR_TOOL_ERROR` shift on cells where solver crashes occurred.
- All other cells: expected zero drift.

**Reproducibility / byte-equality.**
- Aggregate metrics: stable.
- `tool_calls[*].result` strings recorded in pre-PR-50 `results/` are **not byte-comparable** with post-upgrade trial logs on (i) `validate_pddl_syntax` calls without a plan (report-text change) and (ii) failing `classic_planner` / `numeric_planner` calls (error-shape change). Same accepted-degradation precedent as the original `verbose=False` bridge (EXPERIMENTS_FLOW.md §11).
- Canonical signals (`valid` field, `error` boolean, `trajectory` shape) unchanged.

**Out-of-scope changes documented for completeness.**
- pddl-parser 1.5.0 (Literal `parser` arg, `normalize_pddl` file-path widening + `errors` field, `inspect_domain.types` drops implicit `"object"` root, `:requirements` preserves source order, `get_applicable_actions` cross-backend deterministic lex-sort, `get_trajectory` list[str]): the parser plugin is not in `REQUIRED_PLUGINS`, so none of these reach our LLM or scorer.
- `validate_pddl_syntax` + `get_state_transition` `plan` now accept `list[str]`: additive, we still pass a joined string in `_validate_model_plan` (scoring.py:284).
- `get_state_transition.trajectory` shape (the `simulate` byte-equality oracle, EXPERIMENTS_FLOW.md:145): **explicitly deferred** in PR-50 `docs/breaking-changes.md` to avoid oracle-fixture regeneration. Safe.

**Operational steps taken.**
- Local validator venv at `../pddl-copilot/plugins/pddl-validator/.venv` deleted so pyvalidator>=0.1.5 pin is picked up on next launch.
- Cluster-side validator venv to be wiped during the smoke-submission step (delegated to cluster-ops).
- Smoke submitted across the full vLLM roster (`Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`) on the new marketplace to measure the actual drift magnitude vs the most recent comparable `checkpoints/cluster-20260517/` corpus before locking sweep-4's tool surface.

**ISS-005 status nudge.** PR-50 widens the set of failure modes that route into `FR_TOOL_ERROR` (was: transport / timeout / arg-rejection / parse-error; now: + INTERNAL_ERROR / UNSUPPORTED_PROBLEM / INTERMEDIATE / Java-missing). The (a)/(b)/(c) split that ISS-005 deferred to post-hoc grep on `TaskResult.error` is now modestly more valuable as a diagnostic. See OPEN_ISSUES.md ISS-005 addendum.

**Files touched (this repo).**
- `development/CHANGELOG.md` (this entry)
- `development/OPEN_ISSUES.md` (ISS-005 addendum)

**Files NOT touched.** No source change in `pddl_eval/`, `run_experiment.py`, `tests/`, or any cluster-experimenting sbatch — the upstream fix is consumed by the existing bridge logic without modification.

**Sweep-4 framing.** Adopting PR-50 ahead of sweep-4 (vs pinning to pre-PR-50 marketplace) means sweep-4's prompt v5/v6/v7 ablation is run against a slightly cleaner tool surface than sweep-3. The drift smoke submitted with this change sizes the perturbation; if material, the sweep-4 results will be noted as having a small tool-surface confound on top of the prompt-rewrite effect. Sweep-3 results stay on disk as drift anchors per the `feedback_pushback_on_methodology_shortcuts` corpus-isolation rule.

---

## 2026-05-19 — Sweep-4 finalisation: PR-#66 review fixes + per-task retirement pulled forward

**TL;DR.** Three follow-ups to the prompt-rewrite commit (`dce5e29`) before the cluster sweep launches:

1. **Simulate v5/v6/v7 no-tools** now embed a one-step schema-shaped example (`{"step": ..., "action": ..., "state": {"boolean": [...], "numeric": {}}}`) — closes finding 5's secondary leak that the reviewer flagged ("wire format described but not shown"). The example matches `SimulateResponse → StateStep → StateSnapshot` (nested `state.boolean`/`state.numeric` per `pddl_eval/schemas.py:45-67`); the surrounding text was also updated from bare `boolean`/`numeric` to `state.boolean`/`state.numeric` so the prompt names what the format constraint actually enforces.
2. **`tools_per-task_minimal` retired from sweep-4** (was originally deferred to sweep-5 per `development/sweep4_plan_new_prompts.md`). Sweep-4 cluster matrix is now `{no-tools, tools_all_minimal} × {think on, think off}` = 4 cells/model. Sweep-3 ran 3 conditions × 2 think = 6 cells/model — so sweep-4 vs sweep-3 now differs on TWO axes: (a) v0/v1/v2 → v5/v6/v7 prompts (the headline differential), AND (b) per-task condition retirement. Writeup will need to attribute outcome shifts to both effects, with PR-50's tool-surface delta as a third (empirically silent at smoke scale per `development/sweep4_fr_pivot.md`).
3. **Stale `run_smoke_vllm_vs_ollama.sbatch` references** swept from `cluster-experimenting/README.md`, `lib/defaults.sh` (including the runtime-visible stderr at the `vllm_lookup` refused-model branch), `submit_full_sweep.sh`, and `run_condition_vllm_rtx.sbatch`. Operators following the README or hitting a refused-model error are now pointed at `submit_with_rtx.sh --backend vllm --smoke <model>` (the vLLM smoke fastpath added in `4f50a5b`). The script itself was deleted in `06f2b4b`; CHANGELOG historical entries are deliberately left untouched.

**Why pull the per-task retirement forward.** The plan-doc rationale for keeping it through sweep-4 was "hold the matrix constant so sweep-3 vs sweep-4 cleanly isolates the prompt change." Trading that isolation off against (i) ~33% fewer GPU-hours per sweep, (ii) one fewer condition for the analyzer to plot, (iii) the per-task arm was already slated for retirement anyway in sweep-5, and (iv) the sweep-3 `tools_per-task_minimal` results stay on disk for post-hoc 2-condition-vs-3-condition framing if needed. Net: simpler matrix, faster turnaround, deferred attribution work absorbs the cost.

**Files touched.**
- `pddl_eval/prompts.py` — v5/v6/v7 `simulate` no-tools entries updated (additions only — still no in-place edits to v0–v4).
- `cluster-experimenting/lib/defaults.sh` — `PDDL_DEFAULT_CONDITIONS` drops `tools_per-task_minimal`; `PDDL_DEFAULT_SBATCH_CONDITIONS` follows; 4 stale `run_smoke_vllm_vs_ollama.sbatch` references rewritten.
- `cluster-experimenting/README.md` — vLLM-smoke section rewritten around `submit_with_rtx.sh --backend vllm --smoke`; recipe block uses the wrapper, not raw sbatch.
- `cluster-experimenting/submit_full_sweep.sh` — prereqs comment updated.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` — log-preservation idiom comment updated.
- `development/CHANGELOG.md` — this entry.

**Not touched.** `pddl_eval/runner.py`, `pddl_eval/scoring.py`, `pddl_eval/schemas.py`, the v0–v4 prompt strings (sweep-3 corpus identity preserved), any sbatch resource budget. The cluster matrix change is data-only (defaults.sh constant); the wrapper's cell-builder logic and per-cell `--time` ceilings are unchanged.

---

## 2026-05-19 — Sweep-4 prompt rewrite: append v5/v6/v7, flip ACTIVE_PROMPT_VARIANTS to (5, 6, 7)

**TL;DR.** Phase 1 of sweep-4 lands per `development/sweep4_plan_new_prompts.md`. Three new prompt variants (v5/v6/v7) are appended to each of the 5 task lists in `pddl_eval/prompts.py`; a sparse with-tools override dict `PROMPT_TEMPLATES_TOOLS_OVERRIDE` adds per-condition divergence for v5–v7 only; `ACTIVE_PROMPT_VARIANTS` flips from `(0, 1, 2)` to `(5, 6, 7)`. v0–v4 strings are byte-identical to sweep-3 — corpus identity for variant indices 0–2 is preserved (see `feedback_pushback_on_methodology_shortcuts` and the resume-key reproduction guarantee at `pddl_eval/runner.py:441–451`).

**The six leaks (see `.local/prompts_review.md`) and how v5–v7 address them.**
1. `validate_*` VERDICT trailer fighting the with-tools system prompt → trailer dropped in both branches; with-tools branch tells the model to call the validation tool, no-tools branch relies on `format=ValidateResponse` (`pddl_eval/schemas.py:35–42`) and `_VERDICT_RE` as a fallback.
2. `validate_plan` with-tools dropping the `plan` argument (the dominant FR_VERDICT_MISMATCH leak per `development/sweep4_fr_pivot.md`) → every v5/v6/v7 with-tools template explicitly names `domain`, `problem`, AND `plan` as required arguments.
3. `_GUIDED_SUFFIX` (disabled) being the only place tool-arg shape was taught → arg names now baked into per-task with-tools templates; `_GUIDED_SUFFIX` stays disabled.
4. `solve` / `simulate` user prompts feeling textually satisfiable → with-tools branch names a "planner tool" / "state-transition tool" by category (not by exact tool name — that's deferred to the sweep-5 skill-task arm).
5. `simulate` no-tools not teaching `_normalize_trajectory`'s wire format (`pddl_eval/scoring.py:149–227`) → v5/v6/v7 no-tools encode the three invariants: step 0 = initial state with empty action, EVERY currently-true predicate, parenthesised lowercase form.
6. `solve` no-tools not teaching action wire format → v5/v6/v7 no-tools spell out single parenthesised PDDL actions with concrete examples (`(pick-up a)`, `(unstack a b)`, `(stack a b)`).

**Active call site.** `pddl_eval/runner.py:266` becomes override-aware: when `with_tools=True` and `prompt_variant ∈ override[task]`, the override template wins; otherwise the base `PROMPT_TEMPLATES[task]` lookup is used. For v0–v4 the override dict is empty per task, so the with-tools branch falls through to base — sweep-3 wire-equivalence preserved. Archived chain call site at `runner.py:821` deliberately untouched (CLAUDE.md `single-task only` rule).

**Drift safety.** v5/v6/v7 are disjoint from any sweep-3 resume key (variants 0–4 only). v3/v4 stay disabled (kept in the lists to preserve index reservation, matching the existing comment pattern). No new prompt-style choice introduced — `WITH_TOOLS_SYSTEM`, `PROMPT_STYLE_CHOICES`, and `TOOL_FILTER_CHOICES` are byte-identical to sweep-3; `skill-task` and per-task retirement are deferred to sweep-5.

**Baselines (canonical).**
- **Sweep-3 baseline** (pre-rewrite + pre-PR-50): variants `(0, 1, 2)`, marketplace 1.2.0, e.g. `results/cluster-20260517/`. Reproducible by checking out the sweep-3 sha tag.
- **Sweep-4** (this entry): variants `(5, 6, 7)`, marketplace 1.3.0 (post-PR-50). The prompt rewrite is the headline differential; the marketplace 1.3.0 tool-surface delta is empirically silent at smoke scale per `development/sweep4_fr_pivot.md` (drift verdict 2026-05-19) and folded into a single-line caveat in the eventual writeup.

**Files touched (this repo).**
- `pddl_eval/prompts.py` — docstring rewritten; v5/v6/v7 appended to all 5 task lists; new `PROMPT_TEMPLATES_TOOLS_OVERRIDE` dict; `ACTIVE_PROMPT_VARIANTS = (5, 6, 7)`.
- `pddl_eval/runner.py` — single import addition (`PROMPT_TEMPLATES_TOOLS_OVERRIDE`) and override-aware template lookup at `:266`. Archived chain path at `:821` untouched.
- `run_experiment.py` — argparse help for `--num-variants` mentions the sweep-4 active set; signature and default unchanged (default reads `len(ACTIVE_PROMPT_VARIANTS)`).
- `development/CHANGELOG.md` — this entry.

**Files NOT touched.** `pddl_eval/scoring.py`, `pddl_eval/schemas.py`, `pddl_eval/summary.py`, `pddl_eval/resume.py`, `WITH_TOOLS_SYSTEM`, `PROMPT_STYLE_CHOICES`, `TOOL_FILTER_CHOICES`, any sbatch script, the analyzer skill. The cluster matrix for sweep-4 is held identical to sweep-3 (same condition slugs, models, think modes); only variant indices differ.

**Up next.** Local smoke (`python run_experiment.py --partial 1 --models qwen3:0.6b --conditions both --tool-filter all`) eyeballs one trial per task to confirm the override wiring before the cluster submission. After PR review, push branch `sweep4-new-prompts` to `main` and proceed to Phase 2 (cluster sweep) per the plan.

---

## 2026-05-18 — Roster: gemma4:31b dense Ollama → gemma4:26b-a4b MoE vLLM (backend split retired)

**TL;DR.** Replaces the dense `gemma4:31b` (Ollama-only, parser pending vLLM verification) with `gemma4:26b-a4b` (MoE A4B, ~4B active of 26.5B total, AWQ-INT4) served on vLLM. Same publisher and quant pipeline as the verified `qwen3.6:35b` (`cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`). Full 5-model `PDDL_DEFAULT_MODELS` roster now runs on a single backend (vLLM, `rtx_6000:1`) — retires the 2026-05-12 → 2026-05-18 backend split. Active sweep roster: `Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`.

**Phase A — smoke verification.**
- Phase A.1 (`7106f68`) added `gemma4:26b-a4b` to `vllm_lookup` (HF id, `TOOL_CALL_PARSER=gemma4`, `REASONING_PARSER=none`) and refreshed the Gemma-4 example block in `run_smoke_vllm_vs_ollama.sbatch`. Not yet in `PDDL_VLLM_VERIFIED_MODELS` — `submit_with_rtx.sh --backend vllm` refused the tag until smoke cleared the gate.
- Smoke `17633538` crashed at vLLM startup: `ValueError: Chunked MM input disabled but max_tokens_per_mm_item (2496) is larger than max_num_batched_tokens (2048)`. The HF task tag `image-text-to-text` triggers vLLM's auto-load of Gemma-4's multimodal vision tower; the per-MM-item budget exceeds vLLM's default 2048-token batch ceiling.
- Phase A.2 (`59be812`) added a `MAX_NUM_BATCHED_TOKENS` env-var-conditional flag to the smoke sbatch (mirrors `EAGER_FLAG`/`NUM_PREDICT_FLAG`), threaded `MAX_NUM_BATCHED_TOKENS=4096` into the `gemma4:26b-a4b` `vllm_lookup` case, and updated the `vllm_lookup()` header to document the new export.
- Resubmit smoke `17638752` passed: `vllm ready (344s)`, VRAM 42218/49140 MiB (85%), 80 trials at concurrency=4. Tools cells: solve/validate_domain/validate_problem/simulate ToolSel = 1.00 (N=2/4/12/2); validate_plan 0.95 (N=20, 1 `tool_not_selected`). No-tools think=on shows systemic `truncated_no_answer` failures on validate_plan / validate_problem (CoT eats the 6144-token cap before VERDICT) — expected pre-rewrite behavior and falls into sweep-4's v5/v6/v7 prompt work scope.

**Phase B — roster swap (this commit).**
- `cluster-experimenting/lib/defaults.sh`: `PDDL_DEFAULT_MODELS` and `PDDL_SLOW_MODELS` swap `gemma4:31b` → `gemma4:26b-a4b`; `PDDL_VLLM_VERIFIED_MODELS` appends `gemma4:26b-a4b`. Phase-A candidate marker comment removed (no pending candidates). `gemma4:26b-a4b` `vllm_lookup` case doc-comment updated with smoke-17638752 VRAM peak.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch`: consumer for `MAX_NUM_BATCHED_TOKENS` — `unset` before each `vllm_lookup` call (prevents leftover bleed if a multi-model job ever pairs MM and text-only models), build conditional flag, splice into the apptainer `python3 -m vllm.entrypoints.openai.api_server` invocation after `--enable-prefix-caching`.
- `cluster-experimenting/submit_with_resume.sh`: `OLLAMA_MODELS=()`; both echo lines and the squeue tail gate on a non-empty Ollama job id. Header doc rewritten to record that the script now collapses to a single vLLM submission post-backend-unification; Ollama branch is the extension point.
- `cluster-experimenting/submit_full_sweep.sh`: step `[3/3]` flips from `--backend ollama gemma4:31b` (rtx_pro_6000:1, 72h) to `--backend vllm gemma4:26b-a4b` (rtx_6000:1, 48h). All three steps are now vLLM.
- `cluster-experimenting/submit_with_rtx.sh`: comment refs to `gemma4:31b` and `PDDL_SLOW_MODELS=(gemma4:31b, ...)` swap to `gemma4:26b-a4b`. The `--no-tools` example, the `--no-auto-prioritize` slow-set list, and the `rtx_6000` case comment (peak VRAM 26 GB → 24 GB; reframed as the default for vLLM, not an emergency escape) all updated. The `gemma4*` think-mode carveout comment is reworded (it only applied to gemma2-era tags).
- `cluster-experimenting/run_condition_rtx.sbatch`: legacy Ollama sbatch header rewritten — no active model uses it post 2026-05-18; retained for re-running archived `slurm_gemma4_31b_*` corpora as drift anchors. VRAM-fit table reframed as historical reference; gemma4:31b row tagged retired.
- `.claude/skills/cluster-ops/scripts/status.sh`: `ROSTER`, `DISPLAY`, `BACKEND`, `MODEL_TAG_TO_ROSTER` swap `gemma4_31b` → `gemma4_26b-a4b` (with `BACKEND` flipping to `vllm`). Comments updated. `jname_to_cell` docstring drops the Ollama gemma example (kept as a generic legacy-pattern note).
- `.claude/skills/cluster-ops/scripts/prioritize.sh`: `DEFAULT_SLOW_MODELS` swap; usage example refreshed.
- `.claude/skills/analyzer/scripts/plot.py` + `plot_focused.py`: `gemma4_26b-a4b` added to `MODEL_COLORS` (`#9173b0`, a tint of the gemma4_31b purple), `MODEL_ORDER`, and `MODEL_LABELS`. `gemma4_31b` entries retained as drift-anchor support for re-plotting older corpora. Also added missing `Qwen3_5_4B` / `Qwen3_5_9B` color entries (post 2026-05-17 swap had left them as default-color fallbacks).
- `tests/test_scoring.py:335`: determinism-test fixture key swap `gemma4:31b` → `gemma4:26b-a4b`. The pinned bucket regression check uses `Qwen3.5:0.8B`, unaffected.
- `EXPERIMENTS_FLOW.md:504`: roster description updated to the post-swap five-model vLLM-only roster; roster-history narrative gains the 2026-05-18 unification.
- `cluster-experimenting/README.md`: topology table swap (line 14-16) + roster table swap (line 214-220) + verified-parser table swap (line 336) + production-vLLM scope rewrite (line 253-267) + GPU-class section + mem-cap row + `submit_with_resume.sh` description + legacy CG-cancel example. The 2026-05-18 entry in the submission-topology-history list now reads as two same-day events (backend split landed, then retired by the gemma swap).

**Methodology framing.** Treated as plain operational drift (no paper-baseline comparison). The `gemma4:31b` Ollama corpora at `results/slurm_gemma4_31b_*` stay on disk untouched as drift anchors — never mixed with the new `slurm_vllm_gemma4_26b-a4b_*` corpora per the `feedback_pushback_on_methodology_shortcuts.md` corpus-isolation rule. Resume-key isolation is automatic: the 10-tuple at `pddl_eval/runner.py:441–451` includes the model string and OUT_DIR prefix.

**Compatibility / drift framing.** Five-model roster size unchanged; the gemma slot's identity changes from "dense 31B Ollama Q4_K_M" to "MoE 26.5B A4B vLLM AWQ-INT4." Drift expectation: smoke 17638752 already shows tools-cell ToolSel parity with the verified Qwen3.5/3.6 ladder. No-tools think=on truncation rate is high — explicitly an expected pre-rewrite behavior (sweep-4's v5/v6/v7 prompt work).

**Files touched (Phase B).**
- `cluster-experimenting/lib/defaults.sh`
- `cluster-experimenting/run_condition_vllm_rtx.sbatch`
- `cluster-experimenting/run_condition_rtx.sbatch`
- `cluster-experimenting/submit_with_resume.sh`
- `cluster-experimenting/submit_full_sweep.sh`
- `cluster-experimenting/submit_with_rtx.sh`
- `cluster-experimenting/README.md`
- `.claude/skills/cluster-ops/scripts/status.sh`
- `.claude/skills/cluster-ops/scripts/prioritize.sh`
- `.claude/skills/analyzer/scripts/plot.py`
- `.claude/skills/analyzer/scripts/plot_focused.py`
- `tests/test_scoring.py`
- `EXPERIMENTS_FLOW.md`
- `development/CHANGELOG.md` (this entry)

**Reference logs / commits.**
- Smoke 17633538 (MM-tower startup crash): `cluster-experimenting/logs/vllm_gemma4_26b-a4b_smoke-17633538.out`.
- Smoke 17638752 (passed): `cluster-experimenting/logs/vllm_gemma4_26b-a4b_smoke-17638752.out`, results at `results/smoke/probe_vllm_59be812_20260518_222456/gemma4_26b-a4b/summary_20260518_223823.json`.
- Phase-A commits: `7106f68` (vllm_lookup add), `59be812` (MAX_NUM_BATCHED_TOKENS fix).

---

## 2026-05-17 — Plotting: ablation-friendly bar encoding + roster swap (drop 27B, add 4B/9B, flip 35B to vLLM)

**TL;DR.** Two unrelated changes shipped together:
(1) restyle of the analyzer's grouped-bar plots so the three ablation axes — model, thinking on/off, tool exposure — sit on three independent visual channels;
(2) `status.sh` roster realignment to the 2026-05-17 sweep: drop `qwen3.6:27b` (slowest cell, ~19h tools×on), add `Qwen3.5:4B` and `Qwen3.5:9B` to fill the 0.8B → 35B param gap, and flip `qwen3.6:35b`'s canonical backend Ollama → vLLM.

**Plotting — `plot.py` (style change only; numbers bit-identical to prior checkpoint):**
- `.claude/skills/analyzer/scripts/plot.py` — `COND_HATCH` rewritten: `no-tools` → `////` (striped), `tools_per-task_minimal` → `....` (dotted), `tools_all_minimal` → `None` (solid). The retired `tools_*_guided` keys are kept mapped to `None` so re-plotting pre-2026-05 checkpoints still works (mirrors the comment-don't-delete policy in `run_condition_rtx.sbatch`).
- `style()` simplified to a single per-model base color from `MODEL_COLORS` regardless of cond; the `if cond=="no-tools"` branch is removed, and the now-orphaned `MODEL_COLORS_NO_TOOLS` constant + its `plot_focused._color_for` `with_tools=False` branch are deleted (no live caller).
- `THINK_LIGHTEN` semantics unchanged (off=saturated, on=lightened).

**Plotting — `plot_focused.py` (data change, not just style):**
- `fig1` and `fig4` drop their `tools = [r for r in records if r["with_tools_dir"]]` pre-filter and now include a **no-tools bar series alongside the with-tools bars** — `fig1` becomes 4 bars/model (no-tools × {off,on} + with-tools × {off,on}, hatch separates tool exposure), `fig4` becomes 3 bars/model (no-tools / per-task / all). New bars are new data on the plot, not a re-color of existing bars.
- `fig2` swaps from dual color palettes (per-model dark variant for no-tools) to single per-model color + hatch (`////` for no-tools, solid for with-tools), matching the main-plot encoding.
- Output re-renders visible at `checkpoints/cluster-20260517-ablation/`.

**Operations — `status.sh` roster swap:**
- `.claude/skills/cluster-ops/scripts/status.sh` — `ROSTER`, `DISPLAY`, `BACKEND`, `MODEL_TAG_TO_ROSTER` updated to `[Qwen3_5_0_8B, Qwen3_5_4B, Qwen3_5_9B, gemma4_31b, qwen3_6_35b]`. All four dicts list the same 5 keys.
- `qwen3_6_35b` canonical backend flipped `ollama` → `vllm`; the prior Ollama 35B corpus is checkpointed under `checkpoints/cluster-2026{0514,0517}/`. Dirs from the now-non-canonical backend report under "skipped (wrong backend)" rather than polluting the progress matrix.
- `jname_to_cell` / `jname_model` docstring examples refreshed to the new roster.

---

## 2026-05-12 — vLLM: register `qwen3.6:35b` + per-cell-class `--time` override + full-sweep orchestrator

**TL;DR.** Three operations-side changes consolidate the 4-model production sweep into a single dispatch:
(1) `qwen3.6:35b` joins the verified vLLM roster after a parser smoke;
(2) `submit_with_rtx.sh` gains a `--time` CLI flag so heavy Qwen cells (27B/35B) don't TIMEOUT under the hardcoded 06:00:00 vLLM tools ceiling;
(3) `cluster-experimenting/submit_full_sweep.sh` (new orchestrator) emits three sbatch submissions — the three vLLM Qwens on `rtx_6000:1` and `gemma4:31b` on `rtx_pro_6000:1` via Ollama — each on the GPU class and walltime that fits. No methodology change: identical `CELLS_LIST` builder, identical `OUT_DIR` resolution, identical `vllm_lookup` contract.

**Smoke.** `run_smoke_vllm_vs_ollama.sbatch` job 17494176 (2026-05-12, `rtx_6000:1`, vLLM 0.20.2, `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`, 10:02 wall): zero parser-extraction failures across the full tools × no-tools × 5-task matrix. The 2-3 `verdict_mismatch` records under `validate_problem` are model behaviour, not parser errors. First attempt 17494173 ENOSPC'd at 2s on `ise-cpu256-27` (`/scratch` full); resubmit with `--exclude=ise-cpu256-27` landed on `cs-6000-02`. The smoke sbatch's `/scratch` setup still lacks the ENOSPC-safe fallback that the 2026-05-11 entry added to `run_condition_vllm_rtx.sbatch`; out-of-scope for this commit but worth porting later.

**Why `--time` and not a tighter default.** The wrapper's 06:00:00 vLLM tools ceiling was locked by `vllm-production-plan.md` 2026-05-09 with the 27B AWQ in mind, where it was tight but adequate. Production-scale 27B/35B tools cells extrapolate to ~19h. Encoding model→walltime inside `vllm_lookup` would conflate "verified parser table" with "scheduling policy" — the override flag is the conservative split.

**Why an orchestrator and not just two commands.** `submit_with_rtx.sh` accepts one `--backend` per invocation, so a single command can't mix vLLM + Ollama. The orchestrator wraps three calls, rejects flags it owns (`--backend`, `--gpu-type`, `--time`, `--all`, `--smoke*`) up front so the operator can't accidentally pin all three submissions to one backend, and forwards everything else (`--no-tools`, `--think-modes`, `--dry-run`) to all three. ~30 LOC of real logic; no duplication of cell-builder, sbatch composition, manifest writing, or auto-prioritize.

**Prefix-caching probes (closed as docs-only).** Same-day probes verified that `--enable-prefix-caching` is inert on Qwen3.x cells (Mamba 784-tok block override → cumulative block hash diverges at byte 0 of every distinct prompt) and effective on a non-Mamba Gemma4 variant (93% hit rate on byte-identical replay). vLLM 0.20.2 V1 also doesn't populate `usage.prompt_tokens_details.cached_tokens` (vllm-project/vllm#16162). The flag is left on in `run_condition_vllm_rtx.sbatch` — inert but harmless beyond a cosmetic "Mamba cache 'align' mode is experimental" warning — and PR #61 (per-model conditional) was closed as no-op. Finding preserved in personal memory; revisit when a non-Mamba model joins `vllm_lookup`. Probe sbatches were drafted on the closed branch and are recoverable via `git show 38821bc -- 'cluster-experimenting/run_smoke_prefix_cache_probe*'` if needed.

**What changed.**

- `cluster-experimenting/lib/defaults.sh`: `qwen3.6:35b` added to `PDDL_VLLM_VERIFIED_MODELS` and `vllm_lookup` (HF id `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`, parsers `qwen3_xml` + `qwen3`).
- `cluster-experimenting/submit_with_rtx.sh`: new `--time HH:MM:SS` (or `D-HH:MM:SS`) CLI flag overrides the auto-computed `TIME_ARG`. Auto defaults unchanged for callers that don't pass `--time`.
- `cluster-experimenting/submit_full_sweep.sh`: new orchestrator. Three independent sbatch submissions — vLLM `rtx_6000:1` 06:00:00 for `Qwen3.5:0.8B`, vLLM `rtx_6000:1` 48:00:00 for `qwen3.6:27b` + `qwen3.6:35b` (packed array), Ollama `rtx_pro_6000:1` 72:00:00 for `gemma4:31b`.

---

## 2026-05-11 — vLLM sbatch: `--constraint=rtx_6000` + ENOSPC fallback for `/scratch`

**TL;DR.** Sweep 17480288 broke in two distinct ways. Both were SLURM/node-side conditions that slipped past the existing sbatch gates; fixes are surgical and local to `cluster-experimenting/run_condition_vllm_rtx.sbatch`. No changes to `pddl_eval/`, no response-shape changes, no fresh `slurm_vllm_*` corpus namespace required. Full evidence in `development/INVESTIGATION_vllm_oom_thinkon_20260511.md`.

**Failure mode 1 — qwen3.6:27b OOM on L40S nodes (3 cells: `17480288_{2,3,4}`).** SLURM's `gpu:rtx_6000` GRES label is shared by two physical GPU classes at BGU CIS: real RTX 6000 Ada (48 GiB visible) and L40S (44.39 GiB visible, on `ee-l40s-{01,02}`). The recently pinned `--enable-prefix-caching` + `gpu_memory_utilization=0.85` budget needs the full 48 GiB for 27B; the 3.6 GiB delta on L40S OOMs at `_initialize_kv_caches`. `sinfo -h -N -o '%N %f %G'` confirms real rtx_6000 nodes carry feature `rtx_6000` while both L40S nodes carry feature `l40s`, so `--constraint=rtx_6000` is a clean, future-proof filter.

**Fix 1.** `#SBATCH --constraint=rtx_6000` added to `run_condition_vllm_rtx.sbatch` header. Filters out `ee-l40s-{01,02}` AND any future GPU class that gets a `gpu:rtx_6000:N` GRES mislabel without the matching feature flag.

**Failure mode 2 — `/scratch` exhaustion on `ise-cpu256-27` (2 cells: `17480288_{6,9}`, both Qwen3.5:0.8B `tools_all_minimal`).** Original handoff hypothesised a Qwen3.5 chat-template kwarg rejection (`enable_thinking=true`). **Falsified by primary-source evidence** in the .out files: verbatim error is `mkdir: cannot create directory '/scratch/omereliy/<JOBID>/vllm-work': No space left on device` — bash mkdir failing on ENOSPC, not a Python or vLLM error. The pre-existing scratch-fallback branch never engaged because `mkdir -p "$SCRATCH_BASE"` returned 0 (directory entry fits) even though the deeper `mkdir -p "$WORK/hf-cache"` then failed with ENOSPC; `set -eo pipefail` aborted at 2s before the trap fired. The hypothesis is additionally falsified by IDX=5 (Qwen3.5 on/tools_per-task) running 25:56 fine on `ee-l40s-02` before being operator-cancelled — if `enable_thinking=true` were rejected, IDX=5 would have failed identically.

**Fix 2.** Atomicized the `/scratch` writability test in `run_condition_vllm_rtx.sbatch`: try `mkdir -p "$SCRATCH_BASE/vllm-work/hf-cache"` (full target path) in one shot; fall back to `/tmp` if ANY step fails (including ENOSPC at deeper levels). `pddl_eval/vllm_client.py` is **NOT** touched — the harness was never wrong; the bug was bash short-circuiting before the harness loaded.

**Why no node exclusion.** `ise-cpu256-27`'s `/scratch` exhaustion is a transient operator-side condition (likely a leak from a prior job's epilog). Permanent exclusion is overkill; graceful `/tmp` fallback handles both this incident and any future recurrence on any node.

**Smoke-test posture.** The mode-2 fix's smoke run validates "no regression on a healthy `/scratch`-available node" — it does NOT reproduce the original ENOSPC condition (that requires the node-side state). The mode-1 smoke run requires landing on a real rtx_6000 node, which the new constraint enforces, so its smoke directly verifies the fix path.

**What changed.**

- `cluster-experimenting/run_condition_vllm_rtx.sbatch`: `#SBATCH --constraint=rtx_6000` added (failure mode 1); `/scratch` workspace block atomicized with ENOSPC-safe fallback to `/tmp` (failure mode 2).
- `development/INVESTIGATION_vllm_oom_thinkon_20260511.md`: "Failure mode 2" section rewritten with the verbatim `mkdir` error from the .out files and the falsification of the original chat-template hypothesis; "Failure mode 1" updated with the live `sinfo` evidence and the chosen `--constraint=rtx_6000` fix; open-questions list resolved where applicable.

---

## 2026-05-11 — vLLM context-overflow retry: bump `_CTX_RETRY_SAFETY` 8 → 32

**TL;DR.** The earlier vLLM context-overflow retry patch (CHANGELOG 2026-05-11 entry below) caught the first 400 and retried with a clipped `max_tokens`, but the retry was *also* 400'ing at a non-trivial rate on the 17478753 sweep (qwen3.6:27b 2.8% of trials, Qwen3.5:0.8B `on/tools_*` 7–11%, `off/no-tools` 0%). Forensic count over 374 retry failures showed an exact and consistent **+9-token delta** between the prompt-token count reported in the attempt-1 error body and the prompt-token count reported in the attempt-2 error body, leaving `new_max + new_prompt = max_model_len + 1` every single time. Root cause: vLLM's 400 error message reports `"prompt contains at least N input tokens"` — `N` is a LOWER bound. The pre-flight check fires before final template additions (generation prefix, BOS, prefix-caching block-padding) are appended, and the real served prompt is consistently higher than the reported `N`. The original `_CTX_RETRY_SAFETY = 8` was undersized by exactly 1 token relative to that +9 drift.

**Fix.** `_CTX_RETRY_SAFETY` bumped 8 → 32. Absorbs the observed +9 with ~3× headroom for future vLLM versions / different chat templates. Output-budget cost is < 0.4% of the 8192-token `solve` cap, negligible. Comment in `pddl_eval/vllm_client.py` rewritten with the empirical evidence so the next maintainer doesn't have to re-derive the +9 figure from `trials.jsonl`.

**Methodology stance.** The previous 374 retry-failure trials are now permanently in `slurm_vllm_*/trials.jsonl` as `exception` rows on the 17478753 sweep. With the safety bump applied via a fresh resubmit, ≥99% of future overflow trials will instead land as `done_reason="length"` truncations (Ollama-parity bucket). Whether to cancel + clean + resubmit again, or let 17478753 finish and tolerate the ~7% exception contamination in the affected 0.8B cells, is a sweep-level decision tracked outside this entry.

**Why not a retry loop instead of bumping safety.** A retry loop only converges if the +9 drift dampens after the first retry. Empirically the drift is constant across attempts (vLLM's `"at least N"` is the *same* low-bound formula on every error), so a naive loop would diverge — each retry would 400 by the same +1 margin until max retries was hit, then bubble. Bumping safety to absorb the constant drift in one retry is the closed-form fix.

**What changed.**

- `pddl_eval/vllm_client.py`. `_CTX_RETRY_SAFETY` 8 → 32 and updated docstring comment.

---

## 2026-05-11 — vLLM smoke scripts: parameterize `--reasoning-parser`

**TL;DR.** Both vLLM smoke sbatch scripts (`run_smoke_vllm_vs_ollama.sbatch`, `run_smoke_vllm_concurrency_probe.sbatch`) hardcoded `--reasoning-parser qwen3`, even though `TOOL_CALL_PARSER` was already overridable. The gemma4:31b smoke (job 17468317) inherited that hardcoded flag and vLLM crashed at startup with `Qwen3ReasoningParser reasoning parser could not locate think start/end tokens in the tokenizer!` — Gemma's tokenizer has no `<think>` tokens. Now `REASONING_PARSER` is an env var (default `qwen3` to preserve verified Qwen3.x behaviour); pass `REASONING_PARSER=none` to omit the flag for families without a reasoning trace. No methodology change — verified Qwen3.x probes get the same flags as before. Header comment in `run_smoke_vllm_vs_ollama.sbatch` gains an explicit Gemma-4 submit example.

**Why this slipped past.** The production sbatch (`run_condition_vllm_rtx.sbatch:196`) already takes `$REASONING_PARSER` from `vllm_lookup()` (sourced from `lib/defaults.sh`). The smoke scripts were written before that lookup existed and never got back-fixed when `TOOL_CALL_PARSER` was parameterized in commit f79fa46. Gemma-4 is the first non-Qwen family probed since, which is when the gap surfaced.

**What changed.**

- `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`. New `REASONING_PARSER` env var (default `qwen3`). Builds `REASONING_PARSER_FLAG`, empty when value is `none` or empty. Apptainer command drops the hardcoded literal in favour of the flag var. Header gains a Gemma-4 override example alongside the existing 0.8B one.
- `cluster-experimenting/run_smoke_vllm_concurrency_probe.sbatch`. Same env-var + flag-builder pattern.

**Reference logs.** `cluster-experimenting/logs/427849349/17468317-vllm-gemma4_31b.log` (vLLM startup traceback) and `cluster-experimenting/logs/84560442/vllm_gemma4_31b_smoke-17468317.out` (preserved tail in the sbatch out file).

---

## 2026-05-11 — vLLM client catches context-overflow 400 and retries with clipped max_tokens

**TL;DR.** vLLM's OpenAI server strictly rejects `prompt_tokens + max_tokens > max_model_len` with HTTP 400 BadRequestError before any generation, where Ollama silently truncates from the front (or returns `done_reason="length"`) on the same overflow. The first in-flight vLLM qwen3.6:27b production sweep (array `17478276`) hit this on `tools_all × on × solve` trials at ~55% rate — multi-turn tool replay accumulated past the `16384 − 8192 = 8192` input budget. Those exceptions are NOT comparable to Ollama's silent-truncation behaviour on the same overflow, so they contaminated the failure-mode breakdown. `pddl_eval/vllm_client.py::VLLMOllamaClient.chat()` now catches the specific overflow body, parses `(max_model_len, prompt_tokens)` from it, clips `max_tokens = max_model_len − prompt_tokens − 8` (safety margin), and retries on the same connection. Restores response-shape parity with the Ollama corpus. The degenerate prompt ≥ max_model_len case (no output budget left) returns a synthetic Ollama-shaped response with `done_reason="length"` and empty content, mirroring how Ollama would treat a num_ctx fully consumed by the prompt.

**Sweep impact.** The 5 in-flight qwen3.6:27b vLLM array tasks (`17478276_{0..4}`) were scancelled and their 4 partial result dirs (`results/slurm_vllm_qwen3_6_27b_*`, 266 trials total) removed from the cluster before this patch landed — mid-sweep behaviour shifts violate the corpus-identity rule. Resubmit happens against this branch. The 0.8B vLLM array tasks (`17478276_{5..9}`) were left running; the 0.8B model rarely if ever hits the overflow (no multi-turn accumulation past 8K tokens in the cells observed so far), so cancelling them would have been more wasteful than the marginal corpus-mix risk.

**Why catch+retry rather than pre-flight tokenize.** Reactive is simpler — the BadRequestError body already reports `prompt_tokens`, so no extra tokenize round-trip is needed on the (vast majority) happy path. Cost: overflow trials pay one wasted round-trip + queue delay before the retry. vLLM `total_duration` is already wallclock-synthesised (not server-reported decode-only), so the inflation falls inside an already-lossy field; the per-trial wall comparison vs Ollama remains a fair upper bound.

**Why not raise `--max-model-len`.** Two reasons: (1) 27B AWQ peaked at 83% VRAM on rtx_6000:1 at 16384 ctx; 24576 likely won't fit, forcing rtx_pro_6000:1 + queue pressure. (2) Diverges from the Ollama corpus that ran at `num_ctx=16384`, breaking the like-for-like comparison the `slurm_vllm_` namespace was set up for.

**What changed.**

- `pddl_eval/vllm_client.py`. New `_CTX_OVERFLOW_RE` regex + `_CTX_RETRY_SAFETY` constant. `chat()` wraps `chat.completions.create` in try/except over `openai.BadRequestError`; only matches on the specific overflow body (other 400s — e.g. malformed `tool_choice` — propagate untouched). New helpers `_parse_ctx_overflow` and `_synthesize_overflow_response`. Module docstring updated.

---

## 2026-05-11 — vLLM production sbatch + submit-with-resume wrapper (PR #58)

**TL;DR.** Land a vLLM production sbatch (`run_condition_vllm_rtx.sbatch`) and a `--backend vllm` flag on `submit_with_rtx.sh`. Partial migration: `qwen3.6:27b` + `Qwen3.5:0.8B` move to vLLM; `gemma4:31b` + `qwen3.6:35b` stay on Ollama to preserve ~36K already-complete trials. New `submit_with_resume.sh` sequences both backends. No methodology change. vLLM cells write to `results/slurm_vllm_<canonical>_<think>_<cond>/` — the prefix isolates corpora because the 10-tuple resume key in `pddl_eval/runner.py:424` includes the model string (Ollama `qwen3.6:27b` vs vLLM `cyankiwi/Qwen3.6-27B-AWQ-INT4` would silently mismatch on resume). Operator-facing details + verified serve command + scope-split rationale + parser table live in `cluster-experimenting/README.md` "Production vLLM sweep"; this entry is the diff-of-record.

**Files.**

- `cluster-experimenting/lib/defaults.sh` — `PDDL_VLLM_VERIFIED_MODELS=(qwen3.6:27b Qwen3.5:0.8B)` + `vllm_lookup()` (canonical Ollama tag → HF id + parser flags).
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` (new) — vLLM analog of `run_condition_rtx.sbatch`. Same cell-array picker, scratch, VRAM-85% guard, `preserve_serve_logs` trap. Calls `vllm_lookup`. OUT_DIR prefixed `slurm_vllm_`.
- `cluster-experimenting/submit_with_rtx.sh` — `--backend ollama|vllm` (default ollama). Backend-specific GPU/mem/time defaults; vLLM gate calls `vllm_lookup` to reject unverified models. Job name suffixed `_vllm`.
- `cluster-experimenting/submit_with_resume.sh` (new) — sequences Ollama submission for the residual models and vLLM submission for `PDDL_VLLM_VERIFIED_MODELS`.
- `.claude/skills/analyzer/scripts/{aggregate,plot,drift_check}.py` — `parse_dirname` strips `slurm_vllm_` prefix + adds `backend` field; `drift_check._load_root` keys on `(model, think, cond, backend)`; drift table grows a `backend` column.
- `cluster-experimenting/README.md` — new "Production vLLM sweep" section.

**Open / pending.**

1. Pilot one vLLM cell + verify `meta.inference_backend == "vllm"` before fanning out.
2. `gemma4:31b` parser verification.
3. Analyzer cross-backend pivot (both prefixes).
4. Concurrency saturation probe (c=4/8/16, unrun).

**Reproducibility.** Existing Ollama corpora unchanged. vLLM cells write to a non-overlapping namespace. `meta.inference_backend` disambiguates aggregation.

---

## 2026-05-11 — PR #58 cleanup: shell de-duplication + doc trim

**TL;DR.** Pure-refactor follow-up to the four 2026-05-11 vLLM commits. No behavior change. Three reductions: (1) `submit_with_rtx.sh` drops the inline substring-match verified-models gate and calls `vllm_lookup` directly (single source of truth already in `lib/defaults.sh`); the dual `SBATCH_OLLAMA`/`SBATCH_VLLM` vars collapse into one `case`. (2) Both smoke sbatches stop duplicating the 4-line `REASONING_PARSER_FLAG` builder — new `vllm_reasoning_parser_flag()` helper in `lib/defaults.sh` is the single emitter. (3) Header comments on `run_condition_vllm_rtx.sbatch` and `submit_with_resume.sh` trimmed; the verbatim serve-command copy + scope-split prose live only in the README + the entry above. `pddl_eval/vllm_client.py:_CTX_RETRY_SAFETY` gains a one-line justification.

**Files.** `cluster-experimenting/lib/defaults.sh`, `cluster-experimenting/submit_with_rtx.sh`, `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`, `cluster-experimenting/run_smoke_vllm_concurrency_probe.sbatch`, `cluster-experimenting/run_condition_vllm_rtx.sbatch`, `cluster-experimenting/submit_with_resume.sh`, `pddl_eval/vllm_client.py`, `development/CHANGELOG.md`.

---

## 2026-05-10 — vLLM tool-call parser fix + smoke decision-gate PASS

**TL;DR.** The Qwen3.5/3.6 family emits tool calls in **Llama-3 XML** format
(`<tool_call><function=NAME><parameter=KEY>VAL</parameter></function></tool_call>`),
not Hermes JSON. The 2026-05-09 smoke sbatch picked `--tool-call-parser hermes`,
which silently dropped every tools-trial extraction (`tool_calls=[]` → harness
short-circuits `FR_TOOL_NOT_SELECTED` at `pddl_eval/scoring.py:351`). Original
27B AWQ probe (job 17453988 on rtx_3090) showed 0/40 tools cells extracted;
post-fix 27B AWQ probe (job 17461801 on rtx_6000:1) shows **40/40 tools cells
extracted, 100% tool-selection across all 5 tasks, ~0.22× the matching Ollama
walltime — decision gate clears, migrate-go.**

Also: parameterized `TOOL_CALL_PARSER` as a sbatch env var so per-model
overrides are one flag away.

**Smoke results (apples-to-apples; blocksworld/p01, n=80 trials, c=4).**

| metric                  | vLLM 27B AWQ-INT4 (rtx_6000:1, qwen3_xml) | Ollama qwen3.6:27b (cs-6000-01, Q4_K_M) |
| ----------------------- | ----------------------------------------- | --------------------------------------- |
| tools trials extracted  | 40/40 (100%)                              | 40/40 (100%)                            |
| tools success           | 40/40 (100%)                              | 40/40 (100%)                            |
| no-tools success        | 35/40 (88%)                               | 33/40 (82%)                             |
| sum trial duration      | 3,189 s                                   | 14,604 s                                |
| reported wall (vLLM log)| 888.7 s                                   | n/a                                     |
| effective speedup       | **~4.6×**                                 | —                                       |

**Decision rule (from `run_smoke_vllm_vs_ollama.sbatch` header).** vLLM wall
≤ 0.7× Ollama wall on `qwen3.6:27b tools×off` cell AND per-cell pass rates
within parity. Both bars cleared.

**Per-model parser mapping (canonical reference; mirrored in `cluster-experimenting/README.md`).**

| Ollama tag       | HF id                                      | Quant                | TOOL_CALL_PARSER | GPU class                   | Status         |
| ---------------- | ------------------------------------------ | -------------------- | ---------------- | --------------------------- | -------------- |
| `Qwen3.5:0.8B`   | `Qwen/Qwen3.5-0.8B`                        | BF16                 | `qwen3_xml`      | rtx_3090:1                  | Pending verify |
| `qwen3.6:27b`    | `cyankiwi/Qwen3.6-27B-AWQ-INT4`            | AWQ-4bit             | `qwen3_xml`      | rtx_6000:1 / rtx_pro_6000:1 | **Verified**   |
| `qwen3.6:35b`    | `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`        | AWQ-4bit MoE         | `qwen3_xml`      | rtx_6000:1                  | Pending verify |
| `gemma4:31b`     | `cyankiwi/gemma-4-31B-it-AWQ-4bit`         | AWQ-4bit             | `gemma4`         | rtx_6000:1                  | Pending verify |
| `Qwen/Qwen3-0.6B` (vanilla) | `Qwen/Qwen3-0.6B`              | BF16                 | `hermes`         | any                         | Verified (smoke 17461442 confirmed Hermes JSON-in-XML emit format; parity-anti-example for Qwen3.5/3.6) |

The empirical signal that distinguishes the two Qwen formats: dump
`results/.../trials.jsonl[*].response` for any tools-trial. If the body
is `<tool_call>{"name":..., "arguments":{...}}</tool_call>` → use `hermes`.
If the body is `<tool_call><function=NAME><parameter=KEY>VAL</parameter>
</function></tool_call>` → use `qwen3_xml`. There is no in-band autodetect.

**Operational caveats (cluster).**

- `~/vllm.sif` may predate parser additions. If `vllm-serve` rejects
  `--tool-call-parser <name>` at startup with "unknown tool-call-parser",
  `rm ~/vllm.sif` and resubmit; the next run rebuilds from
  `docker://vllm/vllm-openai:latest`.
- vLLM enforces `max_tokens ≤ max_model_len` (HTTP 400 otherwise). When
  using `MAX_MODEL_LEN < 8192`, set `NUM_PREDICT=4096` via
  `--export=ALL,NUM_PREDICT=4096`. Harness per-task defaults are
  `solve=8192`, `validate_*=6144`, `simulate=6144`.
- Tight-VRAM recipe (rtx_3090 24 GB serving 27B AWQ): `MAX_MODEL_LEN=7168
  GPU_MEM_UTIL=0.85 ENFORCE_EAGER=1 NUM_PREDICT=4096`. The eager flag
  skips CUDA graph profiling (~1.5 GiB headroom) at ~10–15% throughput cost.

**What changed.**

- `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`: `--tool-call-parser
  hermes` → `qwen3_xml` (commit `f563ce3`); then parameterized as
  `TOOL_CALL_PARSER` env var (this commit).
- `notebooks/run_vllm_vs_ollama_smoke.ipynb`: retargeted at parser
  verification — tools-only scope, headline metric is tool-extraction
  rate, sbatch knob parity (commit `ca7a307`).
- `cluster-experimenting/README.md`: new "vLLM smoke probes (parser
  verification)" section with per-model table, submit recipes, and
  operational caveats.

**What did NOT change.**

- `pddl_eval/{vllm_client,scoring,...}.py`, `domains/`, `EXPERIMENTS_FLOW.md`,
  `tests/` — methodology, fixtures, scoring unchanged. The fix is purely
  vLLM-serve flag wiring.
- Production sweep `run_condition_rtx.sbatch` is untouched. Ollama remains
  the sole production backend until the vLLM full-sweep sbatch lands.
- Existing `results/` corpora — no schema change.

**Open / pending (closing the migration).**

1. Parser-verification smokes for `Qwen3.5:0.8B`, `qwen3.6:35b`, `gemma4:31b`
   (queued today on rtx_3090:1 / rtx_6000:1 with 1-hour walltime). Expected
   outcome: `qwen3_xml` clean for the two Qwen entries; `gemma4` clean for
   the Gemma entry. Failure modes are debuggable from
   `trials.jsonl[*].response` per the recipe above.
2. Full-sweep vLLM sbatch — vLLM analog of `run_condition_rtx.sbatch` with
   per-model parser flag + per-model HF-id mapping (probably a new
   `cluster-experimenting/lib/defaults_vllm.sh` table). Blocked on (1).
3. Cross-backend analyzer pivot (per-model walltime + tool-extraction
   parity rollup). Blocked on (2).

**Files.** `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`,
`cluster-experimenting/README.md`, `development/CHANGELOG.md`,
`notebooks/run_vllm_vs_ollama_smoke.ipynb`.

---

## 2026-05-09 — vLLM inference-backend smoke probe

**TL;DR.** Adds an opt-in `--inference-backend vllm` path that points the existing harness at vLLM's OpenAI-compatible `/v1/chat/completions` endpoint via a thin adapter (`pddl_eval/vllm_client.py`). Default is unchanged (`ollama`). New cluster sbatch `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch` runs the existing `--smoke` matrix on both backends sequentially on one `rtx_pro_6000:1` node and writes analyzer-readable summaries under `results/smoke/probe_{ollama,vllm}_<sha>_<ts>/`. **No methodology change** — same prompts, fixtures, tools, scoring, num_ctx, num_predict; production sweep (`run_condition_rtx.sbatch`) untouched. Existing results in `results/` remain valid.

**Motivation.** The 27B Ollama cells in the 2026-04-30 sweep ran 57–107 s/trial × 4560 trials = 72–135 h per cell. vLLM's continuous-batching could compress that, but only if real tool-calling and thinking-mode plumbing survive the wire-format swap. A 2-hour smoke that exercises the full 2 (think) × 2 (cond) × 5 (task) × 2 (model) matrix on both backends gates the migration on both wall-time AND tool-call pass-rate parity — pure tok/s benchmarks would miss a Hermes-parser misfire that silently drops to 0% tool use.

**Decision rule.** Migrate only if vLLM wall ≤ 0.7× Ollama wall on the `qwen3.6:27b tools×off` cell **and** per-cell pass rates are within parity. Below either bar, stay on Ollama.

**What changed (`feat/vllm-smoke-probe` branch).**

- **`pddl_eval/vllm_client.py`** (new). `VLLMOllamaClient` exposes the `chat()` / `aclose()` shape `run_experiment.py` calls on `ollama.AsyncClient`. Returns Ollama-shaped response dicts so `pddl_eval/chat.py` (`chat_with_tools`, `chat_without_tools`) and downstream scoring work without edits. Translations: `tool_calls[].function.arguments` JSON-string ↔ dict; `message.reasoning_content` → `message.thinking` (vLLM `--reasoning-parser qwen3`); `finish_reason` → `done_reason`; `usage.{prompt,completion}_tokens` → `prompt_eval_count`/`eval_count`; `total_duration` synthesised from `time.perf_counter_ns`. Multi-turn tool replay re-attaches synthetic `tool_call_id`s in FIFO order so vLLM's OpenAI server accepts the harness's id-less tool messages. Streaming is forced off (sidesteps vllm-project/vllm#31871 Qwen3-hermes streaming bug).
- **`run_experiment.py`**. Adds `--inference-backend {ollama,vllm}` (default `ollama`); branches the client construction. Banner prints the selected backend. `--ollama-host` help updated to "LLM server base URL".
- **`requirements.txt`**. Adds `openai>=1.40.0` for the OpenAI-compatible client.
- **`cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`** (new). Single sbatch on `rtx_pro_6000:1`, `--mem=80G`, `--time=02:30:00`. Phase A: builds/uses cached `ollama.sif`, runs `--smoke` per model. Phase B: builds/uses cached `vllm.sif` (from `docker://vllm/vllm-openai:latest`), serves each HF model on a fresh port with `--enable-auto-tool-choice --tool-call-parser hermes --reasoning-parser qwen3 --gpu-memory-utilization 0.85`, runs `--smoke --inference-backend vllm`. 27B served from `cyankiwi/Qwen3.6-27B-AWQ-INT4` (`--quantization awq`) — the closest apples-to-apples to Ollama's Q4_K_M (~17 GB on disk for both); 0.8B from `Qwen/Qwen3.5-0.8B` BF16. Both phases write to `results/smoke/probe_{ollama,vllm}_<sha>_<ts>/<model_tag>/`.

**What did NOT change.**

- `pddl_eval/{chat,runner,scoring,domains,prompts,resume,schemas,summary}.py` — adapter returns Ollama-shaped objects so the chat loop and tool-call extraction work unchanged.
- `cluster-experimenting/run_condition_rtx.sbatch`, `submit_with_rtx.sh`, `lib/defaults.sh` — production sweep path is untouched. The smoke sbatch is independent.
- `domains/`, `tests/`, `EXPERIMENTS_FLOW.md` — methodology, fixtures, and the experiment-flow spec are unchanged.
- Existing `results/` corpora — no schema change.

**Compatibility.** `--inference-backend` defaults to `ollama`; existing scripts and analysis pipelines see identical behaviour. The vLLM path requires `openai>=1.40.0` to be installed (`requirements.txt` updated); environments that haven't `pip install -r requirements.txt`-d will only fail when `--inference-backend vllm` is actually requested.

**Open / pending.** No analyzer change yet — the smoke results land in the existing summary shape, comparison is by hand for now. If the smoke clears the 0.7× wall + parity gate, follow-ups would be: full-sweep cluster sbatch fork (vLLM analog of `run_condition_rtx.sbatch`), tool-call parity audit, and analyzer cross-backend pivot.

**Files.** `pddl_eval/vllm_client.py` (new), `run_experiment.py`, `requirements.txt`, `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch` (new), `development/CHANGELOG.md`.

---

## 2026-05-07 — Add Colab/Kaggle single-model notebook driver

**TL;DR.** New `notebooks/run_single_model.ipynb` drives `run_experiment.py` for one model on a free-tier T4 (Colab or Kaggle, auto-detected). Persists results + run log to Google Drive (Colab) or `/kaggle/working/` (Kaggle). Pure driver — **no methodology, scoring, prompt, or schema change**; existing `results/` corpora and the analyzer skill remain valid.

**Motivation.** Lower-friction path for collaborators / readers without laptop GPU access; complements the laptop driver (`run_background.sh`) and cluster driver (`cluster-experimenting/`).

**Files.** `notebooks/run_single_model.ipynb` (new), `README.md` (one-line pointer under quick-nav).

---

## 2026-05-07 — Revert Vast.ai remote-Ollama path

**TL;DR.** Reverts the 2026-05-06 entry below. The Vast.ai pool transport (`cluster-experimenting/vast/`, `run_condition_remote.sbatch`, `submit_with_remote.sh`) and its hooks in `run_experiment.py` (`OLLAMA_AUTH_TOKEN` bearer + `verify=False`) and `pddl_eval/chat.py` (MCP env scrub) are removed. The rtx self-deploy (`run_condition_rtx.sbatch`, `submit_with_rtx.sh`) is again the sole cluster transport. **No methodology or result-schema change** — the reverted hooks were env-gated and inactive on the rtx and laptop paths; no canonical results came from the Vast path.

**Motivation.** The Vast pool didn't perform reliably enough to be worth carrying as a parallel transport.

**Files.** Removed `cluster-experimenting/vast/` (all contents), `cluster-experimenting/{run_condition_remote.sbatch,submit_with_remote.sh}`. Reverted `run_experiment.py`, `pddl_eval/chat.py`, `EXPERIMENTS_FLOW.md` to their pre-2026-05-06 shape.

---

## 2026-05-06 — Vast.ai remote-Ollama path (REVERTED 2026-05-07)

Added a parallel cluster transport that offloaded Ollama serving to a pool of Vast.ai GPU boxes behind Caddy + a bearer token, so cluster jobs scheduled on the `main` partition without competing for `rtx_pro_6000`. New files: `cluster-experimenting/vast/{deploy-ollama.sh,Caddyfile.tmpl,preload-model.sh,smoke-test.sh,teardown-pool.sh,README.md,.gitignore}`, `cluster-experimenting/{run_condition_remote.sbatch,submit_with_remote.sh}`. Hooks added to `run_experiment.py` (`OLLAMA_AUTH_TOKEN` → `Authorization: Bearer …` + `verify=False` for Caddy `tls internal`) and `pddl_eval/chat.py` (strip the bearer from MCP subprocess env). The rtx self-deploy was untouched and remained the default. **No methodology change** at the time. Reverted on 2026-05-07 due to unreliable performance — see entry above. Retained here for traceability.

---

## 2026-05-05 — Archive multi-task chain phase from active flow

**TL;DR.** The chain phase (random-length task sequences, all-or-nothing scoring) is dropped from `run_experiment.py`'s dispatch, the cluster + laptop drivers, the analyzer (aggregate / plot / table / focused), and `cluster-ops/status.sh`. The implementation in `pddl_eval/runner.py::run_chain_experiment` and the helpers in `pddl_eval/summary.py::{summarize_chains, print_chain_table}` are **preserved verbatim** as dead-but-importable code, marked with one-line `# Archived 2026-05-05` headers. `summary_*.json` continues to emit `"chains": []` so downstream notebooks reading both pre- and post-archive corpora don't branch. The CLI flags `--chains`, `--chain-samples`, and `--num-ctx-chain` are removed (no deprecation shim; old shell snippets fail loudly). **No methodology change for single-task** — scoring, prompts, fixtures, num_ctx, num_predict, ground truth all unchanged.

**Motivation.** The paper's first-layer findings (Paper 1 in the two-paper plan, see `project_paper_strategy.md` memory) are tools-vs-no-PDDL-tools comparisons on the 5 single-task evaluations. The chain phase was a multi-task layer on top, useful for second-layer claims about agentic behaviour but adding compute cost (chain cells extend wall by ~30-50% on tools cells) without contributing to the active write-up. Keeping the chain code wired created a pull on every documentation edit and analysis script — every SKILL.md mentioned chains, every plot file had chain branches, every status table had a chain column. Archiving the dispatch removes that maintenance pull while keeping the implementation reachable for any future revival.

**What changed (`feat/archive-chain-experiment` branch).**

- **`run_experiment.py`** — drops `run_chain_experiment` / `DEFAULT_NUM_CTX_CHAIN` / `print_chain_table` / `summarize_chains` from imports; removes `--chains`, `--chain-samples`, `--num-ctx-chain` argparse entries; deletes the chain dispatch block (the gate "skip chain phase when sharding to non-zero shard / when `--chain-samples=0` / when `--think=off`" is moot once the flag is gone); drops `args.chain_samples=0; args.chains=False` from the smoke override; removes `num_ctx_chain` from the run banner and `meta`; passes a literal `[]` as the second arg of `save_results`. `--seed` help text updated to point at `--smoke-shuffle` only. Smoke and shard help text trimmed of chain references. The example in the module docstring drops the `--chains` line.
- **`pddl_eval/runner.py`** — single-line `# Archived 2026-05-05` markers above `DEFAULT_NUM_CTX_CHAIN` and `run_chain_experiment`. Function body unchanged so a future re-wiring needs only to re-add the dispatch in `run_experiment.async_main`.
- **`pddl_eval/summary.py`** — module docstring updated to reflect that the active flow always passes `chains=[]`; archive marker above `summarize_chains` / `print_chain_table`. The chain branch in `save_results` (writes `chain_*.json` when called with a non-empty list) is preserved untouched.
- **`run_background.sh`** — removes `SKIP_CHAINS`, `CHAIN_ARGS`, `CHAIN_ECHO`; drops `${CHAIN_ARGS[*]}` from both `python3 run_experiment.py` invocations; drops the `Chains:` line from the startup echo; drops the `partial`-mode chain-skip branch (now redundant).
- **`cluster-experimenting/run_condition_rtx.sbatch`** — drops `CHAIN_SAMPLES` env default; removes `CHAINS_ARGS=(--chains --chain-samples ...)` line and the no-tools `CHAINS_ARGS=()` override; removes `${CHAINS_ARGS[@]}` from the python invocation. Header comments rewritten to drop the `num_ctx_chain` justification.
- **`cluster-experimenting/submit_with_rtx.sh`** — removes chain references from the help comments (`--all` cell counts, no-tools mode description, per-task wall-time table, `--shard` echo). Cell count math is unchanged — chains never were per-cell.
- **`.claude/skills/analyzer/scripts/aggregate.py`** — drops `CHAIN_LENGTHS`, the `print_chain_table` function, and the chain-related legacy warning. `main()` no longer prints the chain table.
- **`.claude/skills/analyzer/scripts/plot.py`** — drops `fig2_chain` and `fig7_chain_step_survival` (function bodies + dispatch); chain pooling block in `merge_series` deleted (the merged series carries `"chains": []`); `_parse_figs` rejects numeric IDs `2` and `7` with a clear error pointing at this CHANGELOG; `--figs all` resolves to `{1, 3, 4, 5, 6}`. Figs `1, 3, 4, 5, 6` retain their pre-archive numeric IDs so existing shell snippets like `--figs 1,4,5` keep working.
- **`.claude/skills/analyzer/scripts/plot_focused.py`** — drops `fig3` (chain-focused per-model panels). `FIG_KEYS` tuple removes `"3"`; `_parse_figs` rejects `"3"` with an archive-note error. Other focused figures retain their numeric IDs.
- **`.claude/skills/analyzer/scripts/table.py`** — drops `CHAIN_LENGTHS` constant and `_chain_cells` helper; `build_rows`, `write_md`, `write_csv`, `write_tex` no longer emit chain columns. The LaTeX `col_spec` and `\multicolumn` group headers shrink correspondingly.
- **`.claude/skills/cluster-ops/scripts/status.sh`** — drops the `CHAIN` regex, the `chain_done` accumulator across both multi-cond and legacy code paths, and the `chain` column from the running-jobs table. Smoke fast-path no longer emits `"n/a"` placeholder.
- **`.claude/skills/{analyzer,cluster-ops,debug-and-simplify}/SKILL.md`** — chain mentions removed from running-table column lists, figure inventories, master-pivot column descriptions, and Layer-4 debugging questions.
- **`EXPERIMENTS_FLOW.md`** — top-of-file callout pointing at this CHANGELOG; §1 pipeline drops chain step; §4.3 collapsed to a one-paragraph archive notice; §5 evaluation parameters table loses chain rows; §5 gating bullets renamed "Single-task gating" and stripped of chain conditions; §9 output schema notes `chains: []` always emitted, per-task `num_ctx_chain` field annotation marks the date range it was emitted; the `chain_{ts}.json` subsection becomes an archive notice; §10 Direct CLI example drops `--chains \`; §11 paper-diff "no-tools matrix" row gains a chain-archive parenthetical.
- **`README.md`** — removes the chain CLI rows (`--chains`, `--chain-samples`, `--num-ctx-chain`), the "Include multi-task chain evaluation" code example, the "Chain evaluation" bullet from "How It Works", and the `chain_<timestamp>.json` line from the output list (replaced with an archive note pointing here). `--seed` help repurposed to `--smoke-shuffle`.
- **`cluster-experimenting/README.md`** — chain references trimmed from the no-tools quickstart wall, the Conditions list, the resource-profile `--time` table, the "Where things go" / "Fetching results" sections (file glob updated to `{single_task,summary}_*.json` with a back-compat note), and the troubleshooting `--num-ctx-chain` mitigation. The unrelated SLURM `afterok` dependency-chain idiom remains.
- **`CLAUDE.md`** — top-level note: "active flow is single-task only as of 2026-05-05; chain phase archived in `pddl_eval/{runner,summary}.py`."
- **`development/OPEN_ISSUES.md`** — `ISS-009` (chain with-tools=0% for 0.6b is uninformative) and `ISS-011` (chain denominator unchanged when steps are skipped) closed with this date and a pointer here.

**What did NOT change.**

- `pddl_eval/runner.py::run_chain_experiment` body — preserved verbatim.
- `pddl_eval/summary.py::{summarize_chains, print_chain_table, save_results chain branch}` — preserved verbatim.
- `pddl_eval/{chat.py, scoring.py}` — chain-related comments are about shared codepaths and are accurate; left as-is.
- `tests/*` — no chain references existed pre-archive (verified by grep before this PR); test suites unchanged.
- `single_task_*.json` and `summary_*.json` schemas — `summary["chains"]` still present (always `[]` in new outputs); pre-archive rows on disk parse identically.
- Pre-2026-05-05 result corpora (`checkpoints/cluster-26042026/`, `results/cluster-*/`) — files untouched. **Note**: their populated `chains` arrays no longer render in `aggregate.py` / `plot.py` / `table.py` after this change. If you need a chain-rendering aggregator for archaeology, revert this commit on a branch.
- `development/archive/{SUBMISSION_STRATEGY_PROPOSAL,FRAMEWORK_EXTENSION_PLAN}.md` — historical snapshots, untouched.

**Compatibility.**

- Existing `summary_*.json` files load unchanged in the trimmed analyzer (chain rows are ignored, not erroring).
- Old shell scripts that pass `--chains`, `--chain-samples N`, or `--num-ctx-chain N` to `run_experiment.py` will fail loudly with argparse "unrecognized arguments" — this is the intended back-compat boundary.
- The cluster sbatch's `CHAIN_SAMPLES` env var is no longer consumed; setting it has no effect (no warning either — silent ignore).

**Re-wiring the chain phase later.** The minimum patch to revive chains is: re-export the four names in `run_experiment.py`'s import block, re-add the three argparse flags, paste the dispatch block back into `async_main`, restore the smoke override, and pass `chain_results` (not `[]`) to `save_results`. No changes to `pddl_eval/` are needed because the bodies are intact. Analyzer / cluster-ops / docs would re-grow on their own as needed.

**Closes / narrows.** Closes `ISS-009`, `ISS-011` (both chain-specific and now moot under the archive policy). `ISS-013` (paper-diff audit) is left open — its scope spans single-task too.

**Files.** `run_experiment.py`, `pddl_eval/{runner,summary}.py`, `run_background.sh`, `cluster-experimenting/{submit_with_rtx.sh, run_condition_rtx.sbatch, README.md}`, `.claude/skills/analyzer/{SKILL.md, scripts/{aggregate,plot,plot_focused,table}.py}`, `.claude/skills/cluster-ops/{SKILL.md, scripts/status.sh}`, `.claude/skills/debug-and-simplify/SKILL.md`, `EXPERIMENTS_FLOW.md`, `README.md`, `CLAUDE.md`, `development/{CHANGELOG.md, OPEN_ISSUES.md}`.

---

## 2026-05-05 — Record `partial` in summary meta

**TL;DR.** When `--partial K > 0`, `summary_*.json`'s `meta` block now records `"partial": K`. Existing summaries on disk are unaffected; new writes only. Lets a reader of a synced summary tell at a glance whether the cell's `n` reflects partial- or full-scope, without back-deriving from `n` and the domain count.

**Files.** `run_experiment.py`.

---
> Entries before 2026-05-05 are preserved in `development/CHANGELOG-archive.md` (chain-phase history, PR-1/2/3/4, early cluster topology iteration, scoring audit, fixture build).
