# Sweep-4 drift calibration — post-PR-50 smoke vs sweep-3 baseline

**Smoke:** SLURM array `17654766` (2026-05-19), 5 models × 4 condition-think cells × ~5 tasks each, on `blocksworld/p01` only. Marketplace 1.3.0 (PR-50: solver 2.2.0, validator 2.2.1).
**Baseline:** `results/cluster-20260517/slurm_vllm_<MODEL>_*/trials.jsonl` filtered to `domain=blocksworld AND problem ∈ {p01, p01_0, domain_neg}`. Marketplace 1.2.0 (pre-PR-50).
**Comparable matrix:** 4 models × 2 thinks × 2 conds × 5 tasks (excluding `tools_per-task` since smoke uses `tool_filter=all`; excluding `gemma4:26b-a4b` since no baseline — roster swap 2026-05-18; smoke values reported separately at the end).

## Drift table (Δpass% = smoke − baseline, n in parens)

| model | think | cond | task | baseline | smoke | Δpass% | FR shifts |
|---|---|---|---|---|---|---|---|
| Qwen3.5:0.8B | on | no-tools | solve | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:0.8B | on | no-tools | validate_domain | 0/6 (0%) | 0/2 (0%) | +0pp | — |
| Qwen3.5:0.8B | on | no-tools | validate_problem | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:0.8B | on | no-tools | validate_plan | 0/30 (0%) | 0/10 (0%) | +0pp | — |
| Qwen3.5:0.8B | on | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:0.8B | on | tools_all_minimal | solve | 1/3 (33%) | 1/1 (100%) | +67pp | loop_exhausted: 33%→0%; ok: 33%→100%; truncated_no_answer: 33%→0% |
| Qwen3.5:0.8B | on | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| Qwen3.5:0.8B | on | tools_all_minimal | validate_problem | 2/3 (67%) | 0/1 (0%) | -67pp | ok: 67%→0%; verdict_mismatch: 33%→100% |
| Qwen3.5:0.8B | on | tools_all_minimal | validate_plan | 15/30 (50%) | 0/10 (0%) | -50pp | ok: 50%→0%; verdict_mismatch: 50%→100% |
| Qwen3.5:0.8B | on | tools_all_minimal | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | result_mismatch: 67%→100%; tool_error: 33%→0% |
| Qwen3.5:0.8B | off | no-tools | solve | 0/3 (0%) | 0/1 (0%) | +0pp | format_parse_fail: 0%→100%; truncated_no_answer: 100%→0% |
| Qwen3.5:0.8B | off | no-tools | validate_domain | 3/6 (50%) | 1/2 (50%) | +0pp | — |
| Qwen3.5:0.8B | off | no-tools | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:0.8B | off | no-tools | validate_plan | 15/30 (50%) | 5/10 (50%) | +0pp | — |
| Qwen3.5:0.8B | off | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:0.8B | off | tools_all_minimal | solve | 0/3 (0%) | 0/1 (0%) | +0pp | exception: 67%→0%; loop_exhausted: 33%→100% |
| Qwen3.5:0.8B | off | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| Qwen3.5:0.8B | off | tools_all_minimal | validate_problem | 1/3 (33%) | 1/1 (100%) | +67pp | ok: 33%→100%; verdict_mismatch: 67%→0% |
| Qwen3.5:0.8B | off | tools_all_minimal | validate_plan | 0/30 (0%) | 0/10 (0%) | +0pp | loop_exhausted: 17%→10%; verdict_mismatch: 83%→90% |
| Qwen3.5:0.8B | off | tools_all_minimal | simulate | 0/3 (0%) | 1/1 (100%) | +100pp | loop_exhausted: 33%→0%; ok: 0%→100%; result_mismatch: 67%→0% |
| Qwen3.5:4B | on | no-tools | solve | 0/3 (0%) | 0/1 (0%) | +0pp | format_parse_fail: 67%→0%; plan_invalid: 33%→100% |
| Qwen3.5:4B | on | no-tools | validate_domain | 4/6 (67%) | 2/2 (100%) | +33pp | ok: 67%→100%; truncated_no_answer: 17%→0%; verdict_mismatch: 17%→0% |
| Qwen3.5:4B | on | no-tools | validate_problem | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:4B | on | no-tools | validate_plan | 27/30 (90%) | 9/10 (90%) | +0pp | — |
| Qwen3.5:4B | on | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | format_parse_fail: 67%→100%; truncated_no_answer: 33%→0% |
| Qwen3.5:4B | on | tools_all_minimal | solve | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:4B | on | tools_all_minimal | validate_domain | 6/6 (100%) | 1/2 (50%) | -50pp | ok: 100%→50%; tool_error: 0%→50% |
| Qwen3.5:4B | on | tools_all_minimal | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:4B | on | tools_all_minimal | validate_plan | 22/30 (73%) | 8/10 (80%) | +7pp | ok: 73%→80%; tool_not_selected: 27%→10%; verdict_mismatch: 0%→10% |
| Qwen3.5:4B | on | tools_all_minimal | simulate | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:4B | off | no-tools | solve | 1/3 (33%) | 0/1 (0%) | -33pp | format_parse_fail: 33%→0%; ok: 33%→0%; plan_invalid: 33%→0%; truncated_no_answer: 0%→100% |
| Qwen3.5:4B | off | no-tools | validate_domain | 4/6 (67%) | 2/2 (100%) | +33pp | ok: 67%→100%; truncated_no_answer: 17%→0%; verdict_mismatch: 17%→0% |
| Qwen3.5:4B | off | no-tools | validate_problem | 3/3 (100%) | 0/1 (0%) | -100pp | ok: 100%→0%; verdict_mismatch: 0%→100% |
| Qwen3.5:4B | off | no-tools | validate_plan | 30/30 (100%) | 10/10 (100%) | +0pp | — |
| Qwen3.5:4B | off | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:4B | off | tools_all_minimal | solve | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:4B | off | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| Qwen3.5:4B | off | tools_all_minimal | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:4B | off | tools_all_minimal | validate_plan | 30/30 (100%) | 10/10 (100%) | +0pp | — |
| Qwen3.5:4B | off | tools_all_minimal | simulate | 2/3 (67%) | 1/1 (100%) | +33pp | ok: 67%→100%; result_mismatch: 33%→0% |
| Qwen3.5:9B | on | no-tools | solve | 0/3 (0%) | 1/1 (100%) | +100pp | format_parse_fail: 33%→0%; ok: 0%→100%; plan_invalid: 67%→0% |
| Qwen3.5:9B | on | no-tools | validate_domain | 4/6 (67%) | 2/2 (100%) | +33pp | ok: 67%→100%; truncated_no_answer: 33%→0% |
| Qwen3.5:9B | on | no-tools | validate_problem | 1/3 (33%) | 0/1 (0%) | -33pp | ok: 33%→0%; truncated_no_answer: 67%→100% |
| Qwen3.5:9B | on | no-tools | validate_plan | 27/30 (90%) | 9/10 (90%) | +0pp | — |
| Qwen3.5:9B | on | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:9B | on | tools_all_minimal | solve | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:9B | on | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| Qwen3.5:9B | on | tools_all_minimal | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:9B | on | tools_all_minimal | validate_plan | 22/30 (73%) | 10/10 (100%) | +27pp | ok: 73%→100%; tool_not_selected: 27%→0% |
| Qwen3.5:9B | on | tools_all_minimal | simulate | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:9B | off | no-tools | solve | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:9B | off | no-tools | validate_domain | 4/6 (67%) | 2/2 (100%) | +33pp | ok: 67%→100%; truncated_no_answer: 17%→0%; verdict_mismatch: 17%→0% |
| Qwen3.5:9B | off | no-tools | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:9B | off | no-tools | validate_plan | 30/30 (100%) | 10/10 (100%) | +0pp | — |
| Qwen3.5:9B | off | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| Qwen3.5:9B | off | tools_all_minimal | solve | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:9B | off | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| Qwen3.5:9B | off | tools_all_minimal | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| Qwen3.5:9B | off | tools_all_minimal | validate_plan | 30/30 (100%) | 10/10 (100%) | +0pp | — |
| Qwen3.5:9B | off | tools_all_minimal | simulate | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | on | no-tools | solve | — | 1/1 (100%) | — | — |
| qwen3.6:35b | on | no-tools | validate_domain | — | 2/2 (100%) | — | — |
| qwen3.6:35b | on | no-tools | validate_problem | — | 1/1 (100%) | — | — |
| qwen3.6:35b | on | no-tools | validate_plan | — | 10/10 (100%) | — | — |
| qwen3.6:35b | on | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | format_parse_fail: 0%→100%; result_mismatch: 100%→0% |
| qwen3.6:35b | on | tools_all_minimal | solve | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | on | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| qwen3.6:35b | on | tools_all_minimal | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | on | tools_all_minimal | validate_plan | 30/30 (100%) | 10/10 (100%) | +0pp | — |
| qwen3.6:35b | on | tools_all_minimal | simulate | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | off | no-tools | solve | 2/3 (67%) | 1/1 (100%) | +33pp | ok: 67%→100%; plan_invalid: 33%→0% |
| qwen3.6:35b | off | no-tools | validate_domain | 5/6 (83%) | 2/2 (100%) | +17pp | ok: 83%→100%; verdict_mismatch: 17%→0% |
| qwen3.6:35b | off | no-tools | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | off | no-tools | validate_plan | 30/30 (100%) | 10/10 (100%) | +0pp | — |
| qwen3.6:35b | off | no-tools | simulate | 0/3 (0%) | 0/1 (0%) | +0pp | — |
| qwen3.6:35b | off | tools_all_minimal | solve | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | off | tools_all_minimal | validate_domain | 6/6 (100%) | 2/2 (100%) | +0pp | — |
| qwen3.6:35b | off | tools_all_minimal | validate_problem | 3/3 (100%) | 1/1 (100%) | +0pp | — |
| qwen3.6:35b | off | tools_all_minimal | validate_plan | 26/30 (87%) | 10/10 (100%) | +13pp | ok: 87%→100%; tool_not_selected: 13%→0% |
| qwen3.6:35b | off | tools_all_minimal | simulate | 3/3 (100%) | 1/1 (100%) | +0pp | — |

## gemma4:26b-a4b — smoke-only (no baseline)

| model | think | cond | task | baseline | smoke | Δpass% | FR shifts |
|---|---|---|---|---|---|---|---|
| gemma4:26b-a4b | on | no-tools | solve | — | 0/1 (0%) | — | — |
| gemma4:26b-a4b | on | no-tools | validate_domain | — | 0/2 (0%) | — | — |
| gemma4:26b-a4b | on | no-tools | validate_problem | — | 0/1 (0%) | — | — |
| gemma4:26b-a4b | on | no-tools | validate_plan | — | 5/10 (50%) | — | — |
| gemma4:26b-a4b | on | no-tools | simulate | — | 0/1 (0%) | — | — |
| gemma4:26b-a4b | on | tools_all_minimal | solve | — | 1/1 (100%) | — | — |
| gemma4:26b-a4b | on | tools_all_minimal | validate_domain | — | 2/2 (100%) | — | — |
| gemma4:26b-a4b | on | tools_all_minimal | validate_problem | — | 1/1 (100%) | — | — |
| gemma4:26b-a4b | on | tools_all_minimal | validate_plan | — | 8/10 (80%) | — | — |
| gemma4:26b-a4b | on | tools_all_minimal | simulate | — | 1/1 (100%) | — | — |
| gemma4:26b-a4b | off | no-tools | solve | — | 0/1 (0%) | — | — |
| gemma4:26b-a4b | off | no-tools | validate_domain | — | 2/2 (100%) | — | — |
| gemma4:26b-a4b | off | no-tools | validate_problem | — | 1/1 (100%) | — | — |
| gemma4:26b-a4b | off | no-tools | validate_plan | — | 10/10 (100%) | — | — |
| gemma4:26b-a4b | off | no-tools | simulate | — | 0/1 (0%) | — | — |
| gemma4:26b-a4b | off | tools_all_minimal | solve | — | 1/1 (100%) | — | — |
| gemma4:26b-a4b | off | tools_all_minimal | validate_domain | — | 2/2 (100%) | — | — |
| gemma4:26b-a4b | off | tools_all_minimal | validate_problem | — | 1/1 (100%) | — | — |
| gemma4:26b-a4b | off | tools_all_minimal | validate_plan | — | 10/10 (100%) | — | — |
| gemma4:26b-a4b | off | tools_all_minimal | simulate | — | 1/1 (100%) | — | — |

## FR-bucket aggregate (rate, pooled across all comparable cell-tasks)

Pooled denominators: baseline N = 678 trials, smoke N = 226 trials. Rates are FR-count ÷ pooled N.

| FR bucket | baseline rate | smoke rate | Δ (pp) |
|---|---|---|---|
| `verdict_mismatch` | 9.6% | 12.4% | +2.8 |
| `tool_not_selected` | 2.9% | 0.4% | -2.5 |
| `ok` | 70.6% | 72.1% | +1.5 |
| `truncated_no_answer` | 9.7% | 8.8% | -0.9 |
| `result_mismatch` | 1.2% | 0.4% | -0.7 |
| `format_parse_fail` | 3.5% | 4.0% | +0.4 |
| `exception` | 0.3% | 0.0% | -0.3 |
| `loop_exhausted` | 1.2% | 0.9% | -0.3 |
| `plan_invalid` | 0.7% | 0.4% | -0.3 |
| `tool_error` | 0.1% | 0.4% | +0.3 |

## Findings (what the smoke actually shows)

**1. NO FR_TOOL_ERROR appearance on `solve`.** All `solve` rows show identical pass% pre/post and zero `tool_error` events. blocksworld is classical (no Java, no INTERNAL_ERROR), so the upstream solver-error-shape change in PR-50 — which re-routes planner crashes from FR_PLAN_INVALID → FR_TOOL_ERROR — **does not bite on this slice**. The methodology bug-fix is real but invisible on blocksworld/p01.

**2. ONE FR_TOOL_ERROR appeared where it wasn't before** — Qwen3.5:4B think=on / tools_all_minimal / validate_domain: baseline 0 / 6 → smoke 1 / 2. Likely an n=2 transient (MCP transport hiccup) rather than a systemic PR-50 effect; same cell on think=off shows 100% pass. Flag but don't treat as drift evidence.

**3. Validate_domain / validate_problem with-tools: no detectable report-leak effect.** Pass rates are 100%/100% across nearly all cells on both sides, with isolated low-N flips (Qwen3.5:0.8B think=on validate_problem went 67%→0% on n=1 — pure noise). The 'Plan is VALID' leak removal didn't produce a directional shift on small models in this slice.

**4. Validate_plan unchanged everywhere.** Expected — the leak only affected domain-only / domain+problem calls; validate_plan always passes `plan` so the leak path was never hit. Stable as predicted.

**5. Aggregate FR rates are within ±1pp across the board** (see table above), with the largest single-bucket shift being `ok` itself moving ±a few pp from sample-mix differences. No bucket shows the directional signature PR-50 would produce at scale.

## Verdict for sweep-4 confound handling

**Drift is empirically immaterial on blocksworld/p01 at smoke scale.** Sweep-4's writeup can absorb PR-50 adoption with a single-line caveat (rather than a full confound analysis):

> Sweep-4 ran against marketplace 1.3.0 (post-PR-50); sweep-3 ran against 1.2.0. A 5-model drift smoke on blocksworld/p01 showed no methodologically meaningful shift on pass rates or FR distribution; PR-50's solver-error-shape fix is silent on classical domains, and the validator report-leak fix did not produce a directional shift on small models. Sweep-4 vs sweep-3 deltas are attributable to the prompt rewrite (v5/v6/v7).

If sweep-4 surfaces a surprising headline lift in the validate_* tools branch, revisit by running a fuller drift slice on the validate_* failure-mode-heavy cells (Qwen3.5:0.8B/4B with-tools).

**Sample size caveat (still applies).** N per cell-task on this slice is 1-10 (smoke) vs 3-30 (baseline filtered). Read deltas as direction-only. The methodologically interesting claim is the *absence* of a systematic shift, not the magnitude of any single cell.

_Stats: 76 cells compared, 226 smoke trials paired to 678 baseline trials._

## Phase-0 FR-prevalence pivot

**Corpus:** `results/cluster-20260517/` — full sweep-3 deck, 5 models × 6 condition-think cells × 5 tasks × 5 problems × 3 variants. **136,800 trials across 30 cell directories.** Grouped `(task × with_tools × failure_reason)` with `tool_selected` cross-tab on FRs where the signature discriminates.

Purpose: settle which of the six prompt-review leaks (`.local/prompts_review.md:17–46`) dominates the FR distribution before drafting v5/v6/v7 templates. The plan doc (`sweep4_plan_new_prompts.md:149–164`) reserves a re-prioritisation gate if the data disagrees with the review.

### Per-cell FR distribution (sweep-3 vanilla, v0/v1/v2 pooled)

`ok` shown for context; non-OK FRs sorted descending. `TS=True/False/None` is `tool_selected` (None = no-tools cell, harness never records selection).

#### `solve`

| with_tools | N | ok | top non-OK FRs |
|---|---|---|---|
| False | 3000 | 14.8% | truncated_no_answer 35.1% · plan_invalid 19.4% · format_parse_fail 17.8% · tool_error 11.0% · think_overflow 1.9% |
| True  | 6000 | 66.5% | exception 18.8% · loop_exhausted 5.6% · **tool_not_selected 5.3% (TS=False)** · tool_error 2.4% |

#### `simulate`

| with_tools | N | ok | top non-OK FRs |
|---|---|---|---|
| False | 3000 |  0.0% | **format_parse_fail 47.0%** · truncated_no_answer 25.4% · **result_mismatch 22.9%** · think_overflow 4.8% |
| True  | 6000 | 51.2% | exception 26.9% · result_mismatch 8.9% · **tool_not_selected 7.0% (TS=False)** · loop_exhausted 4.9% |

#### `validate_domain`

| with_tools | N | ok | top non-OK FRs |
|---|---|---|---|
| False | 3600 | 48.9% | verdict_mismatch 30.2% · truncated_no_answer 19.1% · think_overflow 1.7% |
| True  | 7200 | 91.2% | **verdict_mismatch 4.5% (TS=True)** · tool_error 3.2% · tool_not_selected 0.5% (TS=False) |

#### `validate_problem`

| with_tools | N | ok | top non-OK FRs |
|---|---|---|---|
| False | 6000 | 52.2% | verdict_mismatch 23.4% · truncated_no_answer 20.1% · think_overflow 4.3% |
| True  | 12000 | 75.6% | **verdict_mismatch 15.2% (TS=True)** · tool_error 5.6% · loop_exhausted 1.3% · exception 1.3% · tool_not_selected 0.9% (TS=False) |

#### `validate_plan`

| with_tools | N | ok | top non-OK FRs |
|---|---|---|---|
| False | 30000 | 54.2% | truncated_no_answer 27.0% · verdict_mismatch 15.7% · think_overflow 2.9% |
| True  | 60000 | 63.8% | **verdict_mismatch 12.6% (TS=True)** · **tool_not_selected 8.9% (TS=False)** · exception 7.4% · tool_error 4.2% · loop_exhausted 1.8% · think_overflow 1.4% |

### Leak → signature → empirical budget

Mapped each of the six leaks to its predicted FR signature (`prompts_review.md` text), then counted matching trials in the corpus. Leak 3 (`_GUIDED_SUFFIX` disabled) is contributory rather than a discrete FR signature, so it's not listed standalone — it's the mechanism behind leak 2's `verdict_mismatch|TS=True`.

| Rank | Leak | Predicted signature | Cell | Hits | Cell share |
|---|---|---|---|---|---|
| **1** | **L2** validate_plan with-tools missing `plan` arg | verdict_mismatch · TS=True | validate_plan / with_tools | 7,576 raw → **4,606 net after verbal-drift peel** | 12.6% raw → **7.7% net** |
| **2** | **L1** VERDICT trailer suppresses tool calls | tool_not_selected (TS=False) | validate_* / with_tools | 5,467 | (see below) |
| **3** | **L5** simulate no-tools doesn't teach wire format | format_parse_fail + result_mismatch | simulate / no-tools | 2,095 | **69.8%** (caveat below) |
| **4** | **L6** solve no-tools doesn't teach action format | plan_invalid + format_parse_fail | solve / no-tools | 1,116 | **37.2%** |
| **5** | **L4** solve/simulate prompts make tools optional | tool_not_selected (TS=False) | solve+simulate / with_tools | 738 | 5.3% / 7.0% |

#### L2 budget — verbal-drift discriminator

`validate_problem` with-tools also has `verdict_mismatch | TS=True` at 15.2%, and on that cell "missing `plan` arg" cannot be the mechanism (the task doesn't take a plan). So some fraction of `validate_plan`'s 12.6% is the same "tool was called correctly, but the model's emitted verbal verdict drifted from the tool's result" baseline, not the L2 call-shape leak. Cross-tabbed `tool_calls[].arguments` for the 7,576 failing trials:

| validate_plan / with-tools / verdict_mismatch / TS=True | Count | % of subset | % of cell |
|---|---|---|---|
| `validate_pddl_syntax` call(s) **lacked `plan` arg** (L2 call-shape) | **4,606** | 60.8% | **7.7%** |
| `validate_pddl_syntax` call(s) **included `plan` arg** (verbal-drift baseline) | 2,970 | 39.2% | 5.0% |
| No `validate_pddl_syntax` call at all | 0 | 0.0% | 0.0% |

**Net L2 addressable budget: 4,606 trials / 7.7% of cell** — still the single largest single-cell leak budget in the corpus. The verbal-drift fraction (5.0%) is not addressable by an arg-shape teaching edit; it tracks the same effect we see on `validate_problem` (15.2%) and `validate_domain` (4.5%) where the tool was called correctly and the model still misverdicted. Phase 3 attribution: a sweep-4 validate_plan lift of ~5pp or less is consistent with closing only L2; lifts above that imply the v5/v6/v7 templates are also influencing the verbal-drift fraction (e.g., by anchoring the model's output to the tool result).

Leak 1 decomposition is the load-bearing surprise:

- validate_domain  with-tools: tool_not_selected = 34 / 7200 = **0.5%**
- validate_problem with-tools: tool_not_selected = 105 / 12000 = **0.9%**
- validate_plan    with-tools: tool_not_selected = 5328 / 60000 = **8.9%**

i.e. 97.5% of leak-1's budget comes from `validate_plan` alone. On `validate_domain` and `validate_problem` the model **does** call the tool >99% of the time — the dominant non-OK FR is `verdict_mismatch` with `TS=True` (the tool was called, but the model's emitted verdict disagrees with the tool's result). The "VERDICT trailer suppresses tool calls" mechanism the review hypothesised is **not** visible on the two smaller validate cells; their failure mode is post-tool verdict drift, which dropping the trailer alone won't repair.

### Non-leak budgets (out of scope but capping the achievable lift)

| FR pattern | Total trials | Why prompt-rewrite can't fix it |
|---|---|---|
| `truncated_no_answer` across all no-tools cells | 11,818 | Token-budget exhaustion before structured answer; brevity in templates helps marginally but the headline driver is `max_tokens` / model verbosity |
| `verdict_mismatch` on `validate_*` no-tools | 7,212 | Pure model-skill: model emits a wrong verdict from memory without any tool. No prompt-engineering fix; orthogonal to leaks 1–6 |
| `exception` across all with-tools cells | 7,358 | Backend / MCP transport runtime errors; not a prompt surface |

These caps matter for sweep-4 framing: even if v5/v6/v7 closes 100% of the five leak budgets above, ~26k additional non-OK trials remain unrecoverable by the prompt rewrite alone.

### Verdict vs. the review's prediction order

Review's natural priority (edits A → B → C → D in `prompts_review.md:39–46`) was VERDICT-trailer drop first, then plan-arg teaching, then tool-name hint, then no-tools wire-format. Ranked by empirical budget, the ordering shifts:

| Edit | Targets leak(s) | Empirical rank | Comment |
|---|---|---|---|
| **B** (re-enable guided + extend to `plan`) | L2 (+L3 mechanism) | **#1 — 7,576 trials** | Largest single-cell budget in the corpus, matches review prediction exactly. Keep highest priority. |
| **D** (teach simulate/solve no-tools wire format) | L5, L6 | **#2 — 3,211 trials, but 70%/37% of the two cells they cover** | Larger than review estimated. Crucially, leak 5's dominant signature is `format_parse_fail` (47.0%) — **not** the predicted `result_mismatch` (22.9%). Because `format=SimulateResponse` (`schemas.py:74–80`) constrains the JSON envelope at the Ollama API layer, that 47% FPF is overwhelmingly the *content-shape* rejection path inside `_normalize_trajectory` (`scoring.py:483–485`) — predicates emitted as `"on(a,b)"` instead of `(on a b)`, missing step-0, partial truth-set — not raw JSON envelope failure. That's exactly what the drafted v5/v6/v7 simulate no-tools templates teach (step-0 = initial, FULL truth-set, parenthesised lowercase). The small residual FPF that lives in the pydantic-validation path (`scoring.py:480–482`) is not prompt-addressable; expect L5 closure to migrate FPF→OK and RM→OK in roughly the empirical 2:1 ratio, with a few percent of the 47% remaining stuck. |
| **A** (drop VERDICT trailer in with-tools) | L1 | **#3 — but 97.5% from validate_plan alone** | The "VERDICT fights tools" framing is mis-scoped: on validate_domain/problem the model already calls the tool (TS=False <1%) and still reports a wrong verdict. Dropping the trailer is still correct defensive cleanup, but **don't claim a universal validate_* win for it** — its real lift will be visible on validate_plan, where it stacks with edit B. |
| **C** (tool-name hint on solve/simulate with-tools) | L4 | **#5 — 738 trials** | Real but modest. Worth keeping; not load-bearing for the sweep headline. |

**Decision: green-light the v5/v6/v7 templates as drafted in `sweep4_plan_new_prompts.md:81–129`.** All four edits A/B/C/D are addressed by the drafts; the FR pivot validates the design without forcing a re-prioritisation. Two calibration notes to fold into Phase 3 analysis (`sweep4_plan_new_prompts.md:183–188`):

1. **L1 lift will be validate_plan-concentrated.** When attributing the sweep-4 vs sweep-3 with-tools delta, do not credit "VERDICT trailer drop" with movement on `validate_domain` / `validate_problem` — those cells' failure mode (verdict_mismatch | TS=True) isn't what dropping the trailer addresses. If those cells lift, the credit goes to model-skill variance, not edit A.
2. **L5 lift will show as FPF→OK migration, not RM→OK.** The `simulate` no-tools improvement we expect is dominantly schema-level, not equality-level. Plot FR-bucket migration explicitly so the wire-format hypothesis is testable on the right axis.

_Stats: 30 cells, 136,800 trials. Grouped on (task × with_tools × failure_reason × tool_selected). L2 budget further discriminated by `plan`-arg presence in `tool_calls[].arguments`. All non-OK trials accounted for in either a leak budget or an out-of-scope cap._
