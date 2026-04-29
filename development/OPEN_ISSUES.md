# Open Issues

Tracker for methodology / framework gaps surfaced by result reviews but not yet resolved. Each entry notes severity, evidence, and the minimal fix. Close an issue by moving its entry (with resolution date and commit) into `CHANGELOG.md`.

Severity legend: **P1** blocks paper-comparable numbers. **P2** distorts interpretation or wastes runtime. **P3** cosmetic / taxonomy.

---

## P1 — Methodology

### ~~ISS-001~~ · `validate_*` ground truth is all-positive
**Closed 2026-04-26** by the task-targeted negative fixtures pass. Each domain now ships three negatives — `domain_0.pddl` / `p01_0.pddl` / `p01_0.plan` — joining exactly its target task, giving 1:1 balanced ground truth (10 positive + 10 negative per `validate_*` task). With-tools `validate_*` now exercises true validation capability (the trivial verdict-match shortcut is gone). No-tools `validate_*` was simultaneously re-enabled (`run_experiment.py:1147` flipped from `task != "solve"` to `task == "simulate"`), so the production matrix again grades it. `generate_ground_truth` aborts startup with `SystemExit` if any negative validates True. See CHANGELOG 2026-04-26.

### ~~ISS-002~~ · `simulate` no-tools scorer is non-discriminative
**Closed 2026-04-25** (path b — drop simulate from no-tools headline). The `run_single_task_experiment` job builder no longer emits `(no-tools, simulate)` jobs; `check_success`'s simulate no-tools branch remains as defensive code but is unreachable from the production matrix. See CHANGELOG 2026-04-25 (no-tools sweep entry).

### ISS-003 · Guided prompt is ineffective at 0.6b
**Source.** Results review, issue 2.
**Evidence.** `per-task_minimal` and `per-task_guided` both hit 6/55 on `validate_domain`. Guided reshuffles failures from `tool_error:3, verdict_mismatch:8` → `tool_error:0, verdict_mismatch:27` — never to success. Sampled tool-call payloads show the 0.6b model passing the literal string `"blocksworld"` (len=11) as domain content; the hint doesn't bite.
**Impact.** Runs half the sweep for no information gain; inflates compute costs without producing a comparable data point.
**Fix.** Drop `guided` from the qwen3:0.6b sweep. Keep guided only for qwen3:4b (and larger) where the prompt may plausibly change behaviour. Consider replacing the one-sentence hint with a one-shot example or a schema-enforced tool-call wrapper before re-enabling for small models.
**Files.** `run_background.sh` or sweep-config call-sites.

### ISS-017 · Grading bias inverts tools-vs-no-tools at small scales
**Source.** Cluster-run1 analysis, 2026-04-22 (SLURM 17123867/8, Qwen3.5:0.8B, 6/10 conditions).
**Status (2026-04-26).** **Largely closed** by the ISS-001 fix landing. With-tools `validate_*` now sees 1:1 balanced ground truth, so the trivial verdict-match shortcut is gone — a constant-VALID strategy scores ~50%, capability shows up above that. No-tools `validate_*` re-enabled in the same PR, also under balanced ground truth. Pre-ISS-001 result rows from cluster-run1 (Qwen3.5:0.8B, 2026-04-22) remain on disk but should not be quoted as headline numbers since the fixtures they were graded against are no longer the production set. Residual concern (P3 only): the simulate keyword-check grader at `run_experiment.py:910-912` is still non-discriminative, but `simulate` no-tools stays excluded from the matrix, so this is dormant. Re-baselining the with-tools `validate_*` cells under balanced ground truth is the remaining follow-up — tracked under the next sweep, not as a new ISS.
**Original evidence (kept for archaeology).** For Qwen3.5:0.8B (think=off, no-tools, n=50/task):
- validate_domain 50/50 (100%), validate_problem 47/50 (94%), validate_plan 44/50 (88%), simulate 48/50 (96%).
- Tools conditions on the same cells drop to 8–78% (`tool_not_selected` dominates failures: 71–150 of 250).
- Direct inspection (`results/cluster-20260422/slurm_Qwen3_5_0_8B_off_no-tools_17123868/single_task_*.json`) shows the model emits `VERDICT: VALID` on 141/150 validate_* instances; all 150 gold verdicts are VALID (benchmark constructed from solvable problems).
- Simulate responses begin with *"Here is the state transition trace..."* — always contains the `state`+`step`/`after` keywords that `check_success` (`run_experiment.py:910-912`) uses as the sole no-tools grader.
**Files.** Tracked upstream. This entry is a cross-reference + scope/severity note.

---

## P2 — Runtime & instrumentation

### ISS-005 · `FR_TOOL_ERROR` is overloaded
**Source.** Results review, issue 6.
**Evidence.** Current `FR_TOOL_ERROR` collapses (a) plugin argument rejections ("PDDL file not found: 'blocksworld'"), (b) PDDL parse errors ("Failed to parse domain: Expected ':parameters', found '.'"), and (c) transport/timeout errors.
**Status (2026-04-21).** Batch-2 portion landed — `FR_LOOP_EXHAUSTED` is now a distinct bucket (CHANGELOG 2026-04-21) and `TaskResult.error` is populated on `FR_TOOL_ERROR`, so the (a)/(b)/(c) split can now be derived by grep on the populated `error` string during analysis without further taxonomy splits. Remaining scope — formal `FR_TOOL_ARG_ERROR` / `FR_TOOL_PARSE_ERROR` / `FR_TOOL_TRANSPORT` constants — is optional polish; downgraded from P2 to P3.
**Impact.** Cannot quantify the "passes names not content" failure mode directly — it's the paper's most interesting diagnostic.
**Fix.** Split into `FR_TOOL_ARG_ERROR` (plugin rejection) / `FR_TOOL_PARSE_ERROR` (content rejection) / `FR_TOOL_TRANSPORT` (MCP failure). ~30 LOC in `_tool_error_seen` + failure-reason vocabulary. Decompose existing runs during follow-up analysis.
**Files.** `run_experiment.py` (failure-reason constants, `_tool_error_seen`, `check_success`).

### ~~ISS-006~~ · Truncation on no-tools `solve` (17/55, 31%) — partially addressed
**Source.** Results review, issue 8.
**Evidence.** `solve no-tools`: 17/55 truncated at the current `num_predict` default.
**Status (2026-04-29).** Audit performed across the cluster-26042026 sweep (CHANGELOG 2026-04-29 cap-bump entry) — confirmed `solve no-tools` truncation at 32.0% across 5 cells with the 8192 cap. The **cap was not raised** because `solve` is already at the `num_ctx=8192` ceiling for tools cells, and raising it would require widening `num_ctx` everywhere with cluster-wide KV-cache cost. The mitigation that landed: non-solve caps were bumped 1024/1536 → 4096 (closing ISS-007 below) so the verdict tasks no longer share the same artefact. Remaining `solve no-tools` truncation at 8192 is a real model-capability signal worth reporting in the paper rather than chasing further; revisit only if a future model lineup pushes it past ~50%.
**Files.** `run_experiment.py` per-task `num_predict` defaults (now in `pddl_eval/runner.py`), sweep scripts.

### ~~ISS-007~~ · `num_predict=1024` caps validate_* LLM reply — closed 2026-04-29
**Source.** Separated concern (C) from the structured-projection plan; earlier analysis of `qwen4b_nothink_20260411_163217_all_guided/summary_20260417_003616.json`.
**Evidence.** 52+/55 validate_* rows end with `done_reason="length"`. Even after the MCP projection fix, the model's reply is capped before it emits a verdict. Cluster-26042026 confirmed: `validate_plan` 40.9%, `validate_problem` 32.7%, `validate_domain` 17.4%, `simulate` 37.1% truncation at the 1024/1536 caps.
**Closed 2026-04-29.** `pddl_eval/runner.py::DEFAULT_NUM_PREDICT` non-solve entries raised 1024/1536 → 4096 (CHANGELOG 2026-04-29). In the same change, `DEFAULT_NUM_CTX` and `DEFAULT_NUM_CTX_THINKING` were raised 8192/12288 → 16384 (held equal for tools/no-tools fairness — the prior asymmetry confounded the "tools save tokens" headline) after qwen3.6/nemotron smokes showed `FR_THINK_OVERFLOW` at 12288 on the same `validate_*` cells. New `DEFAULT_NUM_CTX_CHAIN` and `--num-ctx-chain` CLI flag added (initially 12288, raised same day to 16384 in lockstep with `DEFAULT_NUM_CTX` after re-reading the single-task think_overflow evidence — chain prompts accumulate history, so the same ctx gives chains *less* think+output headroom, not more). Reproduction note: results from sweeps before this date are still valid for trend analysis but truncation rates, `FR_THINK_OVERFLOW` rates, and tools-vs-no-tools accuracy gaps are NOT directly comparable; flag any post-bump sweep as such in plots, and redraw the headline tools-vs-no-tools claim from a fresh equal-ctx run.
**Files.** `pddl_eval/runner.py`, `run_experiment.py`, `EXPERIMENTS_FLOW.md` §5 + summary-meta, `README.md` parameter table.

### ISS-011 · Chain denominator unchanged when steps are skipped
**Source.** Scoring audit, 2026-04-20.
**Evidence.** `run_chain_experiment` now `continue`s past `validate_plan`/`simulate` steps when the oracle didn't produce a plan (`gt["plan"]` missing/empty). The denominator for chain success stays at `samples` regardless of how many skips occurred, and chains drawn against heavily-unsolvable problems look easier than they are.
**Status (2026-04-21).** Data-capture prerequisite resolved — `chain_*.json` now records per-sample `samples_detail` with `step_records` per step (CHANGELOG 2026-04-21). `effective_chain_length = len(step_records)` is directly computable per sample. Remaining work is choosing the aggregation convention (record effective length vs. resample to N executed steps) and surfacing it during analysis; no further harness change required.
**Impact.** Chain success rates across models are not strictly comparable when fixture polarity differs. ISS-001 (all-positive ground truth) masks this currently, but any broken-PDDL fixture work will expose the skew.
**Fix.** Either (a) record `effective_chain_length` per sample and expose it in `chain_*.json` + `summary_*.json`, (b) resample when skipping so every sample executes exactly N steps, or (c) document the semantics and let ISS-001's fix eliminate skips organically. (a)'s data prerequisite is now met.
**Files.** `run_experiment.py::run_chain_experiment`, `save_results`, `EXPERIMENTS_FLOW.md` §4.3.

### ISS-013 · Paper-diff audit vs arXiv:2509.12987
**Source.** Scoring audit, 2026-04-20 (user direction).
**Evidence.** PR #1 introduced several methodology deltas vs. the paper (explicit `VERDICT:` footer on validate_* prompts; two-metric with-tools grading; `FR_*` taxonomy; trajectory-equality simulate gate). `EXPERIMENTS_FLOW.md §11` lists some of these, but the mapping between our scorer paths and the paper's §3/§5 definitions has not been verified end-to-end.
**Status (2026-04-20).** Domain-set prerequisite resolved: `domains/` now matches the paper's 10 (CHANGELOG 2026-04-20). The audit can now compare numbers on like-for-like coverage instead of mapping 3-vs-10.
**Impact.** Unknown whether any of our scoring decisions silently diverge from the paper on a specific task branch.
**Fix.** Read arXiv:2509.12987 §3 (benchmark construction) and §5 (evaluation protocol). Produce a per-task side-by-side diff table as an appendix to `EXPERIMENTS_FLOW.md`. Flag any discrepancy as a new ISS-###.
**Files.** `EXPERIMENTS_FLOW.md`, possibly `run_experiment.py::check_success` if a discrepancy needs a fix.

### ~~ISS-018~~ · `think=off` should be single-task-only (like `no-tools`)
**Closed 2026-04-28** by PR-2 (token + thinking instrumentation). `run_experiment.py::async_main` now skips the chain phase entirely when `args.think == "off"` (mirrors the existing no-tools chain skip). The cluster sbatch templates do not need a parallel guard — they invoke `run_experiment.py`, which now refuses to start chains under `think=off` regardless of the matrix axis values fed in. The PR-2 abort gate that previously refused `(no-tools, think=on/default)` runs was also lifted in the same PR; thinking content is captured into `TaskResult.thinking` separately so it does not contaminate `extract_verdict` / `extract_plan_lines`. See CHANGELOG 2026-04-28 (PR-2).

---

## P3 — Reporting & polish

### ISS-008 · Domain-size cliff in `validate_domain` wins at 0.6b
**Source.** Results review, issue 3.
**Evidence.** All 6 per-task `validate_domain` successes land on `counters` (401 B) only, never `blocksworld` (862 B) or `depots` (1571 B).
**Impact.** `tool_selected_rate=0.45` on `validate_domain` measures verbatim-PDDL-echoing capacity, not planning competence. Scales with model size and co-varies with domain selection.
**Fix.** Add a domain-size-stratified breakdown during analysis. Re-run on qwen3:4b where echoing is less fragile. Report size as a controlled variable.
**Files.** Analysis artefact (TBD), sweep plan for 4b.

### ISS-009 · Chain with-tools = 0% for 0.6b is uninformative
**Source.** Results review, issue 9.
**Evidence.** All chain (length × config) cells with tools score 0 for qwen3:0.6b. No-tools chains run 0.10–0.30.
**Fix.** Skip 4- and 5-length chains for models where the per-step success rate is below ~0.3. Report only chain=2 as a floor estimate for such models.
**Files.** `run_experiment.py` chain-loop gating, `EXPERIMENTS_FLOW.md`.

### ISS-010 · Tool-name contamination under `tool_filter=all`
**Source.** Results review, issue 10.
**Evidence.** `all_minimal` invokes `save_plan` on `validate_plan` (×4), `simulate` (×17-18), `solve` (×19); `all_*` simulate additionally calls `validate_pddl_syntax` (×10-11).
**Impact.** Expected behaviour of the `all` filter and the point of the filter ablation — not a bug, but not currently surfaced in the headline table.
**Fix.** Report `per-task vs all` delta during analysis as "tool-selection noise" and reference it in the paper diff.
**Files.** Analysis artefact (TBD), write-up.

### ISS-019 · Tool-error message extraction is name-unscoped
**Source.** Refactor review, 2026-04-25.
**Evidence.** `evaluate_one`'s `if failure_reason == FR_TOOL_ERROR and not error:` loop walks every entry in `tool_calls` and surfaces the first `{"error": True, ...}` payload it finds, regardless of whether that tool is the one `check_success` flagged. `_tool_error_seen` (the function that decided `FR_TOOL_ERROR` in the first place) was called with a specific tool name (`"validate_pddl_syntax"`, `"classic_planner"`, etc.), so the two sides are scoped differently.
**Impact.** Edge-case only. Triggers when (a) `--tool-filter=all` exposes multiple tools, and (b) the model calls a *different* tool that errors during the same evaluation. With the paper-default `solve` task and `--tool-filter=all`, both `classic_planner` and `numeric_planner` are valid; an error from the unused planner could be reported as the message even though `check_success` accepted the used planner's plan. Has not been observed in 2026-04-20/04-23 sweeps; surfaced as a latent inconsistency during the dedupe refactor.
**Fix.** Either expand `check_success`'s return tuple to include the offending tool name when `FR_TOOL_ERROR` fires, or pass a per-task tool-name filter into the message-extraction loop (already known via `TASK_TOOLS[task]`). Methodology-neutral — the recorded `failure_reason` is already correct; only the `error` snippet is potentially mislabelled.
**Files.** `run_experiment.py::check_success`, `run_experiment.py::evaluate_one` (the `FR_TOOL_ERROR` message-extraction block).

### ISS-012 · Truncation override skips `FR_VERDICT_MISMATCH`
**Source.** Scoring audit, 2026-04-20.
**Evidence.** `_apply_truncation_override` in `run_experiment.py` reclassifies a failure to `FR_TRUNCATED_NO_ANSWER` only when the downstream tag is `FR_PLAN_INVALID` / `FR_NO_VERDICT_PARSED` / `FR_SIMULATE_EMPTY` / `FR_UNKNOWN`. A model that emits `VERDICT: VALID` after a partial chain-of-thought that got cut off, and the verdict happens to be wrong, is tagged `FR_VERDICT_MISMATCH` — truncation-caused or not.
**Impact.** Per-task truncation counts understate the cap's real effect on validate_* success. Minor; the failure is still counted as a failure, just with a different label.
**Fix.** Decide: (a) leave as-is (current policy, pinned by `test_check_success::test_truncation_override`); (b) also override `FR_VERDICT_MISMATCH` when `done_reason=="length"`, treating any truncated+mismatched verdict as cap-driven. (b) would require explicit justification since the model *did* answer.
**Status (2026-04-29).** ISS-007 closed by the cap bump (1024/1536 → 4096); the pressure that motivated this issue is largely relieved. Recommend deferring (b) — at the new caps, `FR_VERDICT_MISMATCH` should overwhelmingly reflect actual model errors rather than truncation artefacts. Re-evaluate post the next sweep on raised caps.
**Files.** `pddl_eval/scoring.py::_apply_truncation_override`, `tests/test_check_success.py::test_truncation_override`.

### ISS-020 · `validate_domain` neg-arm pairs only the first positive (5:1 vs positive 5:5)
**Source.** PR #22 review on `framework-ext-pr3`, 2026-04-29.
**Evidence.** `pddl_eval/runner.py:533-538` (negative `validate_domain` job emission) uses `positive_first = next(iter(dinfo["problems"].values()))` and pairs the single `domain_neg.pddl` only with that first problem. Comment justifies it as "same convention as the generate_ground_truth pass." Post-PR-3 there are 5 positive problems per domain, so the validate_domain arm is now structurally imbalanced: positive arm emits 5 jobs (`p01..p05` × `domain.pddl`) while the negative arm emits 1 (`p01` × `domain_neg.pddl`).
**Impact.** validate_domain n is 6 per domain (5 pos + 1 neg) instead of a balanced 10 (5 pos + 5 neg). At 20 domains × 5 models × 4 conditions ≈ 480 cells, this leaves the negative-arm headline statistic with 1/5 the sample size of the other validate_* tasks (which got balanced 5:5 at PR-3). Wilson CI widths on validate_domain neg are correspondingly ~√5× wider than necessary.
**Fix.** Change the validate_domain negative-job emission loop to iterate over all 5 positives instead of `next(iter(...))`. ~3-line change in `_emit_job` site at `runner.py:533-538`. Ground-truth `_negatives.domain` already validates the standalone negative (independent of paired positive), so the additional jobs reuse the same `domain_neg.pddl` content with each positive's problem PDDL — no fixture change needed.
**Files.** `pddl_eval/runner.py` (validate_domain neg-arm emission).

---

## Planned batches (approved 2026-04-20)

Landing order differs from raw impact ranking — front-load zero-risk wins, then unlock the P1 blocker. Raw impact ranking retained at the bottom.

1. ~~**Batch 1 — ISS-004** + host-label stamp in `summary_*.json`.~~ Landed 2026-04-20 (see CHANGELOG).
2. **Batch 2 — ISS-005** + `FR_TOOL_LOOP_EXCEEDED` fix in `chat_with_tools` exit path (`run_experiment.py:398-401` currently returns raw tool JSON as `content` after `MAX_TOOL_LOOPS`). Refines taxonomy without changing any success/fail verdict.
3. ~~**Batch 3 — ISS-001** + **ISS-011**.~~ ISS-001 portion landed 2026-04-26 (task-targeted negatives, 30 fixtures, 1:1 balanced). ISS-011 (chain denominator) data-capture is already done and only needs an aggregation convention — see its entry above. With-tools `validate_*` cells now need a re-baseline against the balanced ground truth on the next sweep — label result dirs `{tag}_v2fixtures_*` and note in `EXPERIMENTS_FLOW.md §11` when re-running.
4. **Batch 5 — ISS-006** + **ISS-007** num_predict bumps, landed together with the re-run triggered by Batch 3. Reproduction-default stays at paper setting; flag as ablation.
5. ~~**Batch 4 — ISS-002** resolution.~~ De-facto resolved 2026-04-25 (path b — drop simulate from no-tools headline); confirmed dormant 2026-04-26. See updated pending-decisions entry.

Dropped during the review pass:
- `MCPPlanner.call_tool` assert on caller-supplied `verbose` — redundant with the schema stripping done in `connect()`; no path can deliver a `verbose` arg to `call_tool`.
- Live-MCP smoke test in `tests/verify.sh` — duplicates `../pddl-copilot/plugins/*/tests/verify.sh`, which already exercises each tool end-to-end; any contract drift would surface there first.

Deferred (P3, mostly analysis work): **ISS-003, ISS-008, ISS-009, ISS-010, ISS-012, ISS-013**.

---

## Pending decisions

### ISS-002 — simulate no-tools grader design
**Status (2026-04-26).** Batch 3 (ISS-001 invalid fixtures) landed but explicitly kept `simulate` no-tools excluded from the matrix — the keyword-check grader at `run_experiment.py:910-912` is non-discriminative regardless of fixture polarity (a model that says *"Here is the state transition trace…"* always passes). Path (b) (drop simulate from no-tools headline) was already closed on 2026-04-25 and remains the de-facto resolution. Path (a) (structured-trace grader) is dormant: only worth building if a future analysis specifically wants no-tools simulate as a research artifact. No action required for the next sweep.

Original options:
- **(a)** Structured-trace grader: parse a state sequence from the model response and diff against `gt["state_trajectory"]`. ~60 LOC in `check_success` simulate branch + extend ground-truth emission to carry a canonical trajectory.
- **(b)** Drop simulate from the no-tools headline numbers; document as a known limitation in `EXPERIMENTS_FLOW.md`. **Done 2026-04-25.**

---

## Raw impact ranking (reference)

From the results reviewer's suggested-next-steps, ranked by impact regardless of sequencing:

1. **ISS-001** — broken-PDDL fixtures (unlocks meaningful validate_* numbers).
2. **ISS-005** — split `FR_TOOL_ERROR` (directly quantifies the #1 failure mode).
3. **ISS-004** — factor no-tools out of filter × style loop (halves sweep runtime).
4. **ISS-002** — replace or disable simulate no-tools scorer.
5. **ISS-003** — drop `guided` from the 0.6b sweep.

ISS-006 and ISS-007 are useful ablations that should accompany any re-run on the corresponding model size.
