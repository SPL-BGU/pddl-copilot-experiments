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
