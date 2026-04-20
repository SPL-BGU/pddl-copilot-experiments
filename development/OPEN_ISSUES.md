# Open Issues

Tracker for methodology / framework gaps surfaced by result reviews but not yet resolved. Each entry notes severity, evidence, and the minimal fix. Close an issue by moving its entry (with resolution date and commit) into `CHANGELOG.md`.

Severity legend: **P1** blocks paper-comparable numbers. **P2** distorts interpretation or wastes runtime. **P3** cosmetic / taxonomy.

---

## P1 — Methodology

### ISS-001 · `validate_*` ground truth is all-positive
**Source.** Results review of `qwen06b_20260419_210436_*`, issue 4.
**Evidence.** `gt["domain_valid"]=True` for every bundled problem (no-tools `validate_domain` = 55/55 across all configs). `gt["problem_valid"]=True` for all 55 (3 misses are model false-negatives). Oracle-generated plans are always valid.
**Status (2026-04-20).** Partially addressed. The paper-aligned 10-domain dataset (CHANGELOG 2026-04-20) ships 10 fixtures that are expected to be all-valid; the startup ground-truth summary surfaces per-problem `{domain,problem,plan}_valid` flags for manual review. The core issue — no *invalid* fixtures for the no-tools verdict baseline — is unchanged.
**Impact.** The `validate_*` benchmark has zero invalid examples, so a `VERDICT: VALID` prior trivially wins the no-tools condition. Absolute verdict-accuracy numbers cannot be compared to the paper.
**Fix (remaining).** Inject broken fixtures into `domains/` — corrupted parens, missing `:parameters`, invalid goals — so `gt["{domain,problem}_valid"]` has a non-trivial False fraction. Balance polarity per task.
**Files.** `domains/**/*.pddl`, ground-truth generation in `run_experiment.py`.

### ISS-002 · `simulate` no-tools scorer is non-discriminative
**Source.** Results review, issue 7.
**Evidence.** `check_success` in `run_experiment.py` passes a simulate response whenever `"state"` + (`"after"` or `"step"`) appear in lowercase. 29/55 `truncated_no_answer` still scored `ok:40`.
**Impact.** Measures vocabulary, not simulation correctness.
**Fix.** Replace with structured-trace grader: parse a state sequence from the response and diff against `gt["state_trajectory"]`. Alternatively, flag this as a known limitation in the write-up and drop simulate from the no-tools headline numbers.
**Files.** `run_experiment.py` (simulate branch of `check_success`), ground-truth trajectory emission.

### ISS-003 · Guided prompt is ineffective at 0.6b
**Source.** Results review, issue 2.
**Evidence.** `per-task_minimal` and `per-task_guided` both hit 6/55 on `validate_domain`. Guided reshuffles failures from `tool_error:3, verdict_mismatch:8` → `tool_error:0, verdict_mismatch:27` — never to success. Sampled tool-call payloads show the 0.6b model passing the literal string `"blocksworld"` (len=11) as domain content; the hint doesn't bite.
**Impact.** Runs half the sweep for no information gain; inflates compute costs without producing a comparable data point.
**Fix.** Drop `guided` from the qwen3:0.6b sweep. Keep guided only for qwen3:4b (and larger) where the prompt may plausibly change behaviour. Consider replacing the one-sentence hint with a one-shot example or a schema-enforced tool-call wrapper before re-enabling for small models.
**Files.** `run_background.sh` or sweep-config call-sites.

---

## P2 — Runtime & instrumentation

### ISS-005 · `FR_TOOL_ERROR` is overloaded
**Source.** Results review, issue 6.
**Evidence.** Current `FR_TOOL_ERROR` collapses (a) plugin argument rejections ("PDDL file not found: 'blocksworld'"), (b) PDDL parse errors ("Failed to parse domain: Expected ':parameters', found '.'"), and (c) transport/timeout errors.
**Impact.** Cannot quantify the "passes names not content" failure mode directly — it's the paper's most interesting diagnostic.
**Fix.** Split into `FR_TOOL_ARG_ERROR` (plugin rejection) / `FR_TOOL_PARSE_ERROR` (content rejection) / `FR_TOOL_TRANSPORT` (MCP failure). ~30 LOC in `_tool_error_seen` + failure-reason vocabulary. Backfill analysis notebook to decompose existing runs.
**Files.** `run_experiment.py` (failure-reason constants, `_tool_error_seen`, `check_success`), `analyze_results.ipynb`.

### ISS-006 · Truncation on no-tools `solve` (17/55, 31%)
**Source.** Results review, issue 8.
**Evidence.** `solve no-tools`: 17/55 truncated at the current `num_predict` default.
**Impact.** 0/55 success rate may be a token-budget artefact, not a capability signal.
**Fix.** Re-run `solve no-tools` at `--num-predict 16384` for qwen3:0.6b. Audit per-task median completion lengths against their caps (`DEFAULT_NUM_PREDICT` at `run_experiment.py:77-83`) and raise where medians approach the cap.
**Files.** `run_experiment.py` per-task `num_predict` defaults, sweep scripts.

### ISS-007 · `num_predict=1024` caps validate_* LLM reply
**Source.** Separated concern (C) from the structured-projection plan; earlier analysis of `qwen4b_nothink_20260411_163217_all_guided/summary_20260417_003616.json`.
**Evidence.** 52+/55 validate_* rows end with `done_reason="length"`. Even after the MCP projection fix, the model's reply is capped before it emits a verdict.
**Fix.** Raise `num_predict` for validate_* to 2048–3072. Requires a reproduction-impact note since defaults reproduce the paper setting.
**Files.** `run_experiment.py:77-83`, `EXPERIMENTS_FLOW.md` §5 + §11.

### ISS-011 · Chain denominator unchanged when steps are skipped
**Source.** Scoring audit, 2026-04-20.
**Evidence.** `run_chain_experiment` now `continue`s past `validate_plan`/`simulate` steps when the oracle didn't produce a plan (`gt["plan"]` missing/empty). The denominator for chain success stays at `samples` regardless of how many skips occurred, and chains drawn against heavily-unsolvable problems look easier than they are. The `chain_*.json` output does not record per-sample effective length.
**Impact.** Chain success rates across models are not strictly comparable when fixture polarity differs. ISS-001 (all-positive ground truth) masks this currently, but any broken-PDDL fixture work will expose the skew.
**Fix.** Either (a) record `effective_chain_length` per sample and expose it in `chain_*.json` + `summary_*.json`, (b) resample when skipping so every sample executes exactly N steps, or (c) document the semantics and let ISS-001's fix eliminate skips organically.
**Files.** `run_experiment.py::run_chain_experiment`, `save_results`, `EXPERIMENTS_FLOW.md` §4.3.

### ISS-013 · Paper-diff audit vs arXiv:2509.12987
**Source.** Scoring audit, 2026-04-20 (user direction).
**Evidence.** PR #1 introduced several methodology deltas vs. the paper (explicit `VERDICT:` footer on validate_* prompts; two-metric with-tools grading; `FR_*` taxonomy; trajectory-equality simulate gate). `EXPERIMENTS_FLOW.md §11` lists some of these, but the mapping between our scorer paths and the paper's §3/§5 definitions has not been verified end-to-end.
**Status (2026-04-20).** Domain-set prerequisite resolved: `domains/` now matches the paper's 10 (CHANGELOG 2026-04-20). The audit can now compare numbers on like-for-like coverage instead of mapping 3-vs-10.
**Impact.** Unknown whether any of our scoring decisions silently diverge from the paper on a specific task branch.
**Fix.** Read arXiv:2509.12987 §3 (benchmark construction) and §5 (evaluation protocol). Produce a per-task side-by-side diff table as an appendix to `EXPERIMENTS_FLOW.md`. Flag any discrepancy as a new ISS-###.
**Files.** `EXPERIMENTS_FLOW.md`, possibly `run_experiment.py::check_success` if a discrepancy needs a fix.

### ISS-014 · `pddl-validator` plugin miscomputes numeric `<=` / `>=` goal checks
**Source.** Manual per-domain GT validation via user-scoped pddl-copilot plugin, 2026-04-20. Initial finding (wrongly) attributed the failure to paper-dataset defects; subsequent arithmetic check traced the root cause to the validator itself.
**Evidence.** After copying the paper dataset into `domains/`, calling `mcp__plugin_pddl-validator_pddl-validator__validate_pddl_syntax(domain, problem, plan)` on each fixture:
- `numeric/counters/p01.plan` (paper's `plan.solution`): validator reports `valid=false` with 4 unmet goals (`(<= (+ (value cN) 1) (value cN+1))`). **However** the reported final state is `c0=12, c1=49, c2=92, c3=93, c4=94` — arithmetic verification: `13<=49 ✓`, `50<=92 ✓`, `93<=93 ✓`, `94<=94 ✓`. All four goals are arithmetically satisfied. The fresh `numeric_planner` plan ends at `c0=12, c1=49, c2=50, c3=51, c4=79` — also satisfies all four goals (50<=50, 51<=51, 52<=79). Both are wrongly flagged invalid.
- `numeric/farmland/p01.plan` (paper's `plan.solution`): validator reports 16 unmet goals. Final state shows x=[1,1,1,1,9,1,1,1,1,1,1,1,1,1,2]. The 15 `(>= (x farmN) 1)` goals are all satisfied (every value ≥ 1). Weighted-sum goal `>= 30.8`: hand-computed sum with weights `[1.3,1.4,1.4,1.1,1.0,1.3,1.1,1.3,1.0,1.8,1.9,1.1,1.9,1.6,1.9]` = **31.0** ≥ 30.8 ✓. All 16 satisfied; validator flags all 16 unmet.
- By contrast, `pogo_stick` (boolean goal `have_pogo_stick=true`), `sailing` (booleans `saved(p0)`, `saved(p1)`), `depot` (boolean stacking), and all 5 classical domains validate as `valid=true`. Bug is **specific to numeric `<=` / `>=` comparison goals**.
**Impact.** Oracle ground truth is wrong on counters/p01 and farmland/p01 (both get `gt["plan_valid"]=False` when the true value is `True`). Scoring is symmetric against GT, so:
- For `validate_plan`: an agent that correctly reasons "plan IS valid" gets `FR_VERDICT_MISMATCH` against the (wrong) GT. An agent that calls the buggy validator tool and parrots "INVALID" matches GT and passes — the two wrong answers cancel.
- For `solve`: `_validate_model_plan` uses the same buggy validator on the agent's plan, so any agent plan for counters or farmland will be marked `FR_PLAN_INVALID` regardless of quality.
- For `simulate`: byte-equal trajectory comparison is symmetric across the same buggy validator, so this task is unaffected in principle (both sides wrong in sync).
Net effect: scoring for counters/farmland rewards agreeing-with-the-bug over being-correct on any task that consults plan validity.
**Root cause.** `plugins/pddl-validator/server/validator_server.py` imports `pyval.PDDLValidator` (line 16). Bug is upstream in `pyval`, not in the plugin wrapper.
**Fix.** (a) File an issue / patch upstream in `pyval`; (b) bound the impact by documenting that numeric goal-check results are not trustworthy until fixed; (c) temporarily exclude counters + farmland from aggregate numeric-domain stats in `analyze_results.ipynb` with a footnote.
**Files.** `../pddl-copilot/plugins/pddl-validator/` (wrapper), `pyval` upstream, `analyze_results.ipynb` (reporting workaround), `domains/README.md` (note).

---

## P3 — Reporting & polish

### ISS-008 · Domain-size cliff in `validate_domain` wins at 0.6b
**Source.** Results review, issue 3.
**Evidence.** All 6 per-task `validate_domain` successes land on `counters` (401 B) only, never `blocksworld` (862 B) or `depots` (1571 B).
**Impact.** `tool_selected_rate=0.45` on `validate_domain` measures verbatim-PDDL-echoing capacity, not planning competence. Scales with model size and co-varies with domain selection.
**Fix.** Add a domain-size-stratified breakdown to the analysis notebook. Re-run on qwen3:4b where echoing is less fragile. Report size as a controlled variable.
**Files.** `analyze_results.ipynb`, sweep plan for 4b.

### ISS-009 · Chain with-tools = 0% for 0.6b is uninformative
**Source.** Results review, issue 9.
**Evidence.** All chain (length × config) cells with tools score 0 for qwen3:0.6b. No-tools chains run 0.10–0.30.
**Fix.** Skip 4- and 5-length chains for models where the per-step success rate is below ~0.3. Report only chain=2 as a floor estimate for such models.
**Files.** `run_experiment.py` chain-loop gating, `EXPERIMENTS_FLOW.md`.

### ISS-010 · Tool-name contamination under `tool_filter=all`
**Source.** Results review, issue 10.
**Evidence.** `all_minimal` invokes `save_plan` on `validate_plan` (×4), `simulate` (×17-18), `solve` (×19); `all_*` simulate additionally calls `validate_pddl_syntax` (×10-11).
**Impact.** Expected behaviour of the `all` filter and the point of the filter ablation — not a bug, but not currently surfaced in the headline table.
**Fix.** Report `per-task vs all` delta in the analysis notebook as "tool-selection noise" and reference it in the paper diff.
**Files.** `analyze_results.ipynb`, write-up.

### ISS-012 · Truncation override skips `FR_VERDICT_MISMATCH`
**Source.** Scoring audit, 2026-04-20.
**Evidence.** `_apply_truncation_override` in `run_experiment.py` reclassifies a failure to `FR_TRUNCATED_NO_ANSWER` only when the downstream tag is `FR_PLAN_INVALID` / `FR_NO_VERDICT_PARSED` / `FR_SIMULATE_EMPTY` / `FR_UNKNOWN`. A model that emits `VERDICT: VALID` after a partial chain-of-thought that got cut off, and the verdict happens to be wrong, is tagged `FR_VERDICT_MISMATCH` — truncation-caused or not.
**Impact.** Per-task truncation counts understate the cap's real effect on validate_* success. Minor; the failure is still counted as a failure, just with a different label.
**Fix.** Decide: (a) leave as-is (current policy, pinned by `test_check_success::test_truncation_override`); (b) also override `FR_VERDICT_MISMATCH` when `done_reason=="length"`, treating any truncated+mismatched verdict as cap-driven. (b) would require explicit justification since the model *did* answer. Low priority until ISS-007 is addressed (the cap itself is the proximate problem).
**Files.** `run_experiment.py::_apply_truncation_override`, `tests/test_check_success.py::test_truncation_override`.

---

## Planned batches (approved 2026-04-20)

Landing order differs from raw impact ranking — front-load zero-risk wins, then unlock the P1 blocker. Raw impact ranking retained at the bottom.

1. ~~**Batch 1 — ISS-004** + host-label stamp in `summary_*.json`.~~ Landed 2026-04-20 (see CHANGELOG).
2. **Batch 2 — ISS-005** + `FR_TOOL_LOOP_EXCEEDED` fix in `chat_with_tools` exit path (`run_experiment.py:398-401` currently returns raw tool JSON as `content` after `MAX_TOOL_LOOPS`). Refines taxonomy without changing any success/fail verdict.
3. **Batch 3 — ISS-001** + **ISS-011**. 2 invalid fixtures per domain (6 total): one syntax-level (e.g. corrupted parens), one semantic-level (e.g. missing `:parameters`, type mismatch). Invalidates prior `validate_*` numbers → new baseline required; label result dirs `{tag}_v2fixtures_*` and note in `EXPERIMENTS_FLOW.md §11`.
4. **Batch 5 — ISS-006** + **ISS-007** num_predict bumps, landed together with the re-run triggered by Batch 3. Reproduction-default stays at paper setting; flag as ablation.
5. **Batch 4 — ISS-002** resolution (see pending decision below).

Dropped during the review pass:
- `MCPPlanner.call_tool` assert on caller-supplied `verbose` — redundant with the schema stripping done in `connect()`; no path can deliver a `verbose` arg to `call_tool`.
- Live-MCP smoke test in `tests/verify.sh` — duplicates `../pddl-copilot/plugins/*/tests/verify.sh`, which already exercises each tool end-to-end; any contract drift would surface there first.

Deferred (P3, mostly `analyze_results.ipynb` work): **ISS-003, ISS-008, ISS-009, ISS-010, ISS-012, ISS-013**.

---

## Pending decisions

### ISS-002 — simulate no-tools grader design
Two resolution paths proposed in ISS-002, deferred until Batch 3 lands:
- **(a)** Structured-trace grader: parse a state sequence from the model response and diff against `gt["state_trajectory"]`. ~60 LOC in `check_success` simulate branch + extend ground-truth emission to carry a canonical trajectory.
- **(b)** Drop simulate from the no-tools headline numbers; document as a known limitation in `EXPERIMENTS_FLOW.md`.

**Decision rule.** Run Batch 3 first. If the no-tools simulate row under the mixed-polarity fixture set still looks artifactual (e.g. success driven by vocabulary alone), land (b). If the mix makes simulate no-tools a plausibly informative row, build (a).

---

## Raw impact ranking (reference)

From the results reviewer's suggested-next-steps, ranked by impact regardless of sequencing:

1. **ISS-001** — broken-PDDL fixtures (unlocks meaningful validate_* numbers).
2. **ISS-005** — split `FR_TOOL_ERROR` (directly quantifies the #1 failure mode).
3. **ISS-004** — factor no-tools out of filter × style loop (halves sweep runtime).
4. **ISS-002** — replace or disable simulate no-tools scorer.
5. **ISS-003** — drop `guided` from the 0.6b sweep.

ISS-006 and ISS-007 are useful ablations that should accompany any re-run on the corresponding model size.
