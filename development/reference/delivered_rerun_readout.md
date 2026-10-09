# Delivered rerun readout (live)

Package sha256: `822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9`. Prereg: `development/reference/delivered_rerun_prereg.md`.

## Corpus checks (§2, §7, §8a)

The last three columns are descriptive (rerun cells only): answers starting with the registered leaked prefix, answers starting with it twice (only the first is stripped), and answers that still contain a channel marker after the strip.

| cell | rows | torn lines | exception rows | infra rows | scoring-error rows | storage cuts | leaked prefix | doubled prefix | marker left after strip |
|---|---|---|---|---|---|---|---|---|---|
| slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_delivered-rerun | 9120 | 0 | 0 | 0 | 0 | 0 | 6180 | 0 | 31 |
| slurm_vllm_Qwen3_5_9B_off_tools_all_minimal_delivered-rerun | 9120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| slurm_vllm_qwen3_6_35b_off_tools_all_minimal_delivered-rerun | 9120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| slurm_vllm_gemma4_26b-a4b_off_tools_all_neutral_delivered-rerun-neutral | 6000 | 0 | 0 | 0 | 0 | 0 | 3724 | 0 | 25 |
| slurm_vllm_gemma4_26b-a4b_off_no-tools_delivered-rerun | 4560 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| slurm_vllm_Qwen3_5_9B_off_no-tools_delivered-rerun | 4560 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| slurm_vllm_qwen3_6_35b_off_no-tools_delivered-rerun | 4560 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal | 9120 | 0 | 0 | 0 | 0 | – | – | – | – |
| slurm_vllm_Qwen3_5_9B_off_tools_all_minimal | 9120 | 0 | 0 | 0 | 0 | – | – | – | – |
| slurm_vllm_qwen3_6_35b_off_tools_all_minimal | 9120 | 0 | 0 | 0 | 0 | – | – | – | – |
| slurm_vllm_gemma4_26b-a4b_off_no-tools | 4560 | 0 | 0 | 0 | 0 | – | – | – | – |
| slurm_vllm_Qwen3_5_9B_off_no-tools | 4560 | 0 | 0 | 0 | 0 | – | – | – | – |
| slurm_vllm_qwen3_6_35b_off_no-tools | 4560 | 0 | 0 | 0 | 0 | – | – | – | – |

## Parity guard (§3), evaluated before any delivered number

Job level: **Parity fails at job level**. Qwen cells meeting the criterion: 15 / 20. Cells with |Δ̂| > 10: qwen3_6_35b/solve/plain, qwen3_6_35b/simulate/plain. Gemma evaluated first: True; any Gemma cell failed: False; noise floor F = –.

Apparatus deltas against the canonical corpus (§2):

- 1. Storage: final answers stored up to 65,536 characters (canonical: 500); rows cut by storage: 0 (asserted).
- 2. Final-request overflow retry: a request refused for exceeding the 16,384-token window is resent with the allowance that fits; the first request of every turn is unchanged.
- 3. A leading empty thought-channel marker is removed from the text the grader reads.
- 4. Serving version: vLLM 0.20.2; Qwen3.5-9B canonical tool cells ran on 0.22.0.

| model | task | arm | paired | unpaired (rerun/canon) | TV rerun | TV canon | Δ̂ | 90% CI (domain boot) | verdict | Newcombe 90% (secondary) | clipped before a tool call | consequence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma4_26b-a4b | solve | plain | 300 | 0/0 | 98.7 | 99.3 | -0.7 | [-1.3, 0.0] | criterion met | [-2.3, +0.9] | 20 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | solve | steered | 300 | 0/0 | 100.0 | 98.7 | +1.3 | [0.0, 3.3] | criterion met | [+0.2, +2.9] | 17 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_domain | plain | 360 | 0/0 | 97.8 | 97.5 | +0.3 | [0.0, 0.8] | criterion met | [-1.7, +2.3] | 0 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_domain | steered | 360 | 0/0 | 98.9 | 98.3 | +0.6 | [0.0, 1.7] | criterion met | [-1.0, +2.2] | 0 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_problem | plain | 600 | 0/0 | 99.5 | 99.7 | -0.2 | [-0.7, 0.3] | criterion met | [-0.9, +0.6] | 0 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_problem | steered | 600 | 0/0 | 100.0 | 100.0 | +0.0 | [0.0, 0.0] | criterion met | [-0.4, +0.4] | 0 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_plan | plain | 3000 | 0/0 | 19.9 | 20.6 | -0.7 | [-1.4, 0.0] | criterion met | [-2.4, +1.0] | 0 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_plan | steered | 3000 | 0/0 | 92.1 | 92.6 | -0.4 | [-1.1, 0.1] | criterion met | [-1.6, +0.7] | 5 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | simulate | plain | 300 | 0/0 | 90.7 | 91.7 | -1.0 | [-3.3, 1.3] | criterion met | [-4.9, +2.9] | 9 | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | simulate | steered | 300 | 0/0 | 90.7 | 90.7 | +0.0 | [-1.3, 1.7] | criterion met | [-4.0, +4.0] | 10 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | solve | plain | 300 | 0/0 | 100.0 | 99.3 | +0.7 | [0.0, 2.0] | criterion met | [-0.3, +2.0] | 66 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | solve | steered | 300 | 0/0 | 100.0 | 100.0 | +0.0 | [0.0, 0.0] | criterion met | [-0.9, +0.9] | 47 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_domain | plain | 360 | 0/0 | 100.0 | 100.0 | +0.0 | [0.0, 0.0] | criterion met | [-0.7, +0.7] | 0 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_domain | steered | 360 | 0/0 | 100.0 | 100.0 | +0.0 | [0.0, 0.0] | criterion met | [-0.7, +0.7] | 0 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_problem | plain | 600 | 0/0 | 94.8 | 95.2 | -0.3 | [-0.7, 0.0] | criterion met | [-2.4, +1.8] | 2 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_problem | steered | 600 | 0/0 | 91.0 | 90.2 | +0.8 | [0.0, 1.7] | criterion met | [-2.0, +3.6] | 0 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_plan | plain | 3000 | 0/0 | 92.5 | 93.2 | -0.6 | [-1.2, 0.0] | criterion met | [-1.7, +0.5] | 59 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_plan | steered | 3000 | 0/0 | 96.1 | 96.0 | +0.1 | [-0.2, 0.4] | criterion met | [-0.7, +0.9] | 25 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | simulate | plain | 300 | 0/0 | 68.0 | 65.0 | +3.0 | [-0.3, 6.7] | criterion not met (unresolved) | [-3.3, +9.3] | 33 | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | simulate | steered | 300 | 0/0 | 87.0 | 83.0 | +4.0 | [1.7, 6.7] | criterion not met (unresolved) | [-0.8, +8.8] | 34 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | solve | plain | 300 | 0/0 | 82.3 | 63.0 | +19.3 | [14.3, 24.7] | criterion not met (unresolved) | [+13.4, +25.1] | 97 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | solve | steered | 300 | 0/0 | 99.3 | 92.0 | +7.3 | [3.7, 11.3] | criterion not met (unresolved) | [+4.7, +10.3] | 85 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_domain | plain | 360 | 0/0 | 98.6 | 98.9 | -0.3 | [-1.7, 1.1] | criterion met | [-1.8, +1.2] | 0 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_domain | steered | 360 | 0/0 | 99.4 | 99.7 | -0.3 | [-1.4, 0.6] | criterion met | [-1.4, +0.7] | 0 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_problem | plain | 600 | 0/0 | 97.2 | 96.8 | +0.3 | [-0.8, 1.5] | criterion met | [-1.3, +2.0] | 1 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_problem | steered | 600 | 0/0 | 97.3 | 97.3 | +0.0 | [-1.0, 1.2] | criterion met | [-1.6, +1.6] | 0 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_plan | plain | 3000 | 0/0 | 82.4 | 82.2 | +0.2 | [-3.9, 4.3] | criterion met | [-1.4, +1.9] | 8 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_plan | steered | 3000 | 0/0 | 99.1 | 99.3 | -0.1 | [-0.5, 0.2] | criterion met | [-0.5, +0.3] | 4 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | simulate | plain | 300 | 0/0 | 94.0 | 74.7 | +19.3 | [11.7, 27.7] | criterion not met (unresolved) | [+14.6, +24.1] | 8 | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | simulate | steered | 300 | 0/0 | 95.7 | 97.0 | -1.3 | [-2.3, -0.3] | criterion met | [-4.0, +1.3] | 8 | separate-apparatus replication (whole rerun) |

## Part C parity (§2; reported, not a gate on E2)

Part C − canonical no-tools on the stored online grade, paired; simulate excluded.

| model | task | paired | unpaired (rerun/canon) | Part C | canonical | Δ̂ | 90% CI (domain boot) | verdict |
|---|---|---|---|---|---|---|---|---|
| gemma4_26b-a4b | solve | 300 | 0/0 | 9.7 | 7.7 | +2.0 | [0.0, 4.3] | criterion met |
| gemma4_26b-a4b | validate_domain | 360 | 0/0 | 79.4 | 77.8 | +1.7 | [0.0, 3.6] | criterion met |
| gemma4_26b-a4b | validate_problem | 600 | 0/0 | 76.2 | 74.8 | +1.3 | [-0.5, 3.2] | criterion met |
| gemma4_26b-a4b | validate_plan | 3000 | 0/0 | 88.3 | 87.8 | +0.5 | [-0.6, 1.5] | criterion met |
| Qwen3_5_9B | solve | 300 | 0/0 | 10.7 | 10.7 | +0.0 | [-2.7, 2.7] | criterion met |
| Qwen3_5_9B | validate_domain | 360 | 0/0 | 26.1 | 25.6 | +0.6 | [-0.3, 1.4] | criterion met |
| Qwen3_5_9B | validate_problem | 600 | 0/0 | 65.8 | 65.7 | +0.2 | [-1.5, 1.8] | criterion met |
| Qwen3_5_9B | validate_plan | 3000 | 0/0 | 79.8 | 79.7 | +0.1 | [-0.8, 0.9] | criterion met |
| qwen3_6_35b | solve | 300 | 0/0 | 10.0 | 9.3 | +0.7 | [-1.7, 3.0] | criterion met |
| qwen3_6_35b | validate_domain | 360 | 0/0 | 76.4 | 67.8 | +8.6 | [2.8, 14.7] | criterion not met (unresolved) |
| qwen3_6_35b | validate_problem | 600 | 0/0 | 74.7 | 75.7 | -1.0 | [-2.5, 0.5] | criterion met |
| qwen3_6_35b | validate_plan | 3000 | 0/0 | 90.4 | 90.9 | -0.5 | [-1.8, 0.9] | criterion met |

## E1. Delivered rate per cell (§4), exact

No-room rows (§8a) and harness exception rows (§7) are counted as delivered failures; their counts are shown. Each rate carries its cell's §3 parity verdict and consequence. The last two count columns are descriptive: answers starting with the leaked prefix twice (only the first is stripped) and answers that still contain a channel marker after the strip.

| model | task | arm | n | delivered | 95% CI | tool-verified | invocation | no-room n (%) | exception rows | leaked prefix stripped | doubled prefix | marker left after strip | parity verdict | consequence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma4_26b-a4b | solve | plain | 300 | 92.3 | [87.3, 97.0] | 98.7 | 100.0 | 8 (2.7) | 0 | 291 | 0 | 1 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | solve | steered | 300 | 95.3 | [91.3, 98.7] | 100.0 | 100.0 | 8 (2.7) | 0 | 290 | 0 | 2 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_domain | plain | 360 | 98.3 | [96.1, 100.0] | 97.8 | 100.0 | 0 (0.0) | 0 | 360 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_domain | steered | 360 | 98.9 | [97.5, 100.0] | 98.9 | 100.0 | 0 (0.0) | 0 | 359 | 0 | 1 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_problem | plain | 600 | 99.5 | [99.0, 100.0] | 99.5 | 100.0 | 0 (0.0) | 0 | 598 | 0 | 2 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_problem | steered | 600 | 99.7 | [99.2, 100.0] | 100.0 | 100.0 | 0 (0.0) | 0 | 600 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_plan | plain | 3000 | 89.2 | [84.6, 93.1] | 19.9 | 20.0 | 0 (0.0) | 0 | 595 | 0 | 5 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | validate_plan | steered | 3000 | 96.6 | [93.1, 98.9] | 92.1 | 93.1 | 0 (0.0) | 0 | 2776 | 0 | 16 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | simulate | plain | 300 | 8.3 | [4.0, 13.3] | 90.7 | 99.7 | 138 (46.0) | 0 | 156 | 0 | 3 | criterion met | separate-apparatus replication (whole rerun) |
| gemma4_26b-a4b | simulate | steered | 300 | 8.3 | [4.3, 13.0] | 90.7 | 100.0 | 141 (47.0) | 0 | 155 | 0 | 1 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | solve | plain | 300 | 88.7 | [82.0, 94.7] | 100.0 | 100.0 | 16 (5.3) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | solve | steered | 300 | 89.0 | [82.7, 94.3] | 100.0 | 100.0 | 17 (5.7) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_domain | plain | 360 | 100.0 | [100.0, 100.0] | 100.0 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_domain | steered | 360 | 100.0 | [100.0, 100.0] | 100.0 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_problem | plain | 600 | 94.8 | [92.8, 96.8] | 94.8 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_problem | steered | 600 | 90.7 | [84.5, 95.8] | 91.0 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_plan | plain | 3000 | 94.0 | [89.4, 97.6] | 92.5 | 97.9 | 58 (1.9) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | validate_plan | steered | 3000 | 95.9 | [92.1, 98.8] | 96.1 | 100.0 | 24 (0.8) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | simulate | plain | 300 | 17.3 | [8.0, 27.7] | 68.0 | 81.3 | 128 (42.7) | 0 | 0 | 0 | 0 | criterion not met (unresolved) | separate-apparatus replication (whole rerun) |
| Qwen3_5_9B | simulate | steered | 300 | 16.3 | [8.0, 26.0] | 87.0 | 100.0 | 159 (53.0) | 0 | 0 | 0 | 0 | criterion not met (unresolved) | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | solve | plain | 300 | 77.0 | [69.7, 83.7] | 82.3 | 87.7 | 25 (8.3) | 0 | 0 | 0 | 0 | criterion not met (unresolved) | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | solve | steered | 300 | 87.3 | [81.7, 92.3] | 99.3 | 99.7 | 21 (7.0) | 0 | 0 | 0 | 0 | criterion not met (unresolved) | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_domain | plain | 360 | 98.6 | [96.1, 100.0] | 98.6 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_domain | steered | 360 | 99.4 | [98.3, 100.0] | 99.4 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_problem | plain | 600 | 96.2 | [94.2, 98.0] | 97.2 | 99.3 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_problem | steered | 600 | 97.3 | [95.5, 99.0] | 97.3 | 100.0 | 0 (0.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_plan | plain | 3000 | 97.8 | [96.7, 98.9] | 82.4 | 83.1 | 3 (0.1) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | validate_plan | steered | 3000 | 98.6 | [97.8, 99.4] | 99.1 | 100.0 | 2 (0.1) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | simulate | plain | 300 | 28.3 | [16.3, 41.3] | 94.0 | 99.7 | 150 (50.0) | 0 | 0 | 0 | 0 | criterion not met (unresolved) | separate-apparatus replication (whole rerun) |
| qwen3_6_35b | simulate | steered | 300 | 25.7 | [15.0, 37.0] | 95.7 | 100.0 | 150 (50.0) | 0 | 0 | 0 | 0 | criterion met | separate-apparatus replication (whole rerun) |

## E2. Availability contrast, tools-plain (Part A) − no-tools (Part C) (§4)

No-tools side: Part C of this run (prereg §2 "Part C" and §4 E2: same harness commit, full storage, graded with the same delivered grader as the tool side; the canonical no-tools cells are not an E2 input). The no-tools arm is sampled under the per-task JSON constraint; the tool arm has none.

Δ̂ = tools-plain (A) − no-tools (C), paired.

| model | task | pairs | unpaired (no-tools (C) / tools-plain (A)) | no-tools (C) | tools-plain (A) | Δ̂ | 95% CI | p (domain sign-flip) | p (Holm, 15) | input cells: parity verdict [consequence] |
|---|---|---|---|---|---|---|---|---|---|---|
| gemma4_26b-a4b | solve | 300 | 0 / 0 | 21.3 | 92.3 | 71.0 | [62.0, 79.7] | 1.907e-06 | 2.861e-05 | C/gemma4_26b-a4b/solve/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/gemma4_26b-a4b/solve/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | validate_domain | 360 | 0 / 0 | 79.4 | 98.3 | 18.9 | [7.5, 31.7] | 0.001465 | 0.007324 | C/gemma4_26b-a4b/validate_domain/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/gemma4_26b-a4b/validate_domain/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | validate_problem | 600 | 0 / 0 | 76.2 | 99.5 | 23.3 | [17.5, 29.0] | 3.815e-06 | 3.815e-05 | C/gemma4_26b-a4b/validate_problem/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/gemma4_26b-a4b/validate_problem/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | validate_plan | 3000 | 0 / 0 | 88.3 | 89.2 | 0.9 | [-1.2, 2.9] | 0.4566 | 0.4566 | C/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | simulate | 300 | 0 / 0 | 24.0 | 8.3 | -15.7 | [-24.7, -6.7] | 0.004395 | 0.01758 | C/gemma4_26b-a4b/simulate/plain: not checked (simulate is excluded from the Part C parity check, §2) [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/gemma4_26b-a4b/simulate/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | solve | 300 | 0 / 0 | 24.3 | 88.7 | 64.3 | [54.0, 74.7] | 1.907e-06 | 2.861e-05 | C/Qwen3_5_9B/solve/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/Qwen3_5_9B/solve/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | validate_domain | 360 | 0 / 0 | 26.1 | 100.0 | 73.9 | [63.3, 81.7] | 3.815e-06 | 3.815e-05 | C/Qwen3_5_9B/validate_domain/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/Qwen3_5_9B/validate_domain/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | validate_problem | 600 | 0 / 0 | 65.8 | 94.8 | 29.0 | [22.8, 35.8] | 1.907e-06 | 2.861e-05 | C/Qwen3_5_9B/validate_problem/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/Qwen3_5_9B/validate_problem/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | validate_plan | 3000 | 0 / 0 | 79.8 | 94.0 | 14.2 | [8.7, 20.2] | 0.0001202 | 0.0008411 | C/Qwen3_5_9B/validate_plan/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/Qwen3_5_9B/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | simulate | 300 | 0 / 0 | 9.3 | 17.3 | 8.0 | [-0.3, 17.0] | 0.1123 | 0.2246 | C/Qwen3_5_9B/simulate/plain: not checked (simulate is excluded from the Part C parity check, §2) [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/Qwen3_5_9B/simulate/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | solve | 300 | 0 / 0 | 25.3 | 77.0 | 51.7 | [42.3, 60.0] | 1.907e-06 | 2.861e-05 | C/qwen3_6_35b/solve/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/qwen3_6_35b/solve/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | validate_domain | 360 | 0 / 0 | 76.4 | 98.6 | 22.2 | [12.8, 32.2] | 0.0002747 | 0.001648 | C/qwen3_6_35b/validate_domain/plain: criterion not met (unresolved) [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/qwen3_6_35b/validate_domain/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | validate_problem | 600 | 0 / 0 | 74.7 | 96.2 | 21.5 | [17.2, 26.0] | 1.907e-06 | 2.861e-05 | C/qwen3_6_35b/validate_problem/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/qwen3_6_35b/validate_problem/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | validate_plan | 3000 | 0 / 0 | 90.4 | 97.8 | 7.4 | [4.4, 10.6] | 6.866e-05 | 0.0005493 | C/qwen3_6_35b/validate_plan/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/qwen3_6_35b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | simulate | 300 | 0 / 0 | 17.7 | 28.3 | 10.7 | [2.0, 19.0] | 0.02994 | 0.08981 | C/qwen3_6_35b/simulate/plain: not checked (simulate is excluded from the Part C parity check, §2) [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/qwen3_6_35b/simulate/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)] |

## E3. Steering contrast, steered − plain (§4)

Δ̂ = steered − plain, paired.

| model | task | pairs | unpaired (plain / steered) | plain | steered | Δ̂ | 95% CI | p (domain sign-flip) | p (Holm, 15) | input cells: parity verdict [consequence] |
|---|---|---|---|---|---|---|---|---|---|---|
| gemma4_26b-a4b | solve | 300 | 0 / 0 | 92.3 | 95.3 | 3.0 | [-0.3, 7.0] | 0.2031 | 1 | A/gemma4_26b-a4b/solve/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/solve/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | validate_domain | 360 | 0 / 0 | 98.3 | 98.9 | 0.6 | [0.0, 1.4] | 0.5 | 1 | A/gemma4_26b-a4b/validate_domain/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/validate_domain/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | validate_problem | 600 | 0 / 0 | 99.5 | 99.7 | 0.2 | [-0.5, 0.8] | 1 | 1 | A/gemma4_26b-a4b/validate_problem/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/validate_problem/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | validate_plan | 3000 | 0 / 0 | 89.2 | 96.6 | 7.5 | [4.9, 10.2] | 3.815e-05 | 0.0005722 | A/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| gemma4_26b-a4b | simulate | 300 | 0 / 0 | 8.3 | 8.3 | 0.0 | [-2.3, 2.7] | 1 | 1 | A/gemma4_26b-a4b/simulate/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/simulate/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | solve | 300 | 0 / 0 | 88.7 | 89.0 | 0.3 | [-1.0, 1.7] | 1 | 1 | A/Qwen3_5_9B/solve/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/solve/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | validate_domain | 360 | 0 / 0 | 100.0 | 100.0 | 0.0 | [0.0, 0.0] | 1 | 1 | A/Qwen3_5_9B/validate_domain/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/validate_domain/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | validate_problem | 600 | 0 / 0 | 94.8 | 90.7 | -4.2 | [-9.7, 0.0] | 0.1719 | 1 | A/Qwen3_5_9B/validate_problem/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/validate_problem/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | validate_plan | 3000 | 0 / 0 | 94.0 | 95.9 | 1.9 | [0.5, 3.6] | 0.01953 | 0.2539 | A/Qwen3_5_9B/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| Qwen3_5_9B | simulate | 300 | 0 / 0 | 17.3 | 16.3 | -1.0 | [-6.0, 2.7] | 0.875 | 1 | A/Qwen3_5_9B/simulate/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/simulate/steered: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | solve | 300 | 0 / 0 | 77.0 | 87.3 | 10.3 | [3.7, 18.0] | 0.01085 | 0.1519 | A/qwen3_6_35b/solve/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/solve/steered: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | validate_domain | 360 | 0 / 0 | 98.6 | 99.4 | 0.8 | [0.0, 2.2] | 0.5 | 1 | A/qwen3_6_35b/validate_domain/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/validate_domain/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | validate_problem | 600 | 0 / 0 | 96.2 | 97.3 | 1.2 | [0.0, 2.5] | 0.1484 | 1 | A/qwen3_6_35b/validate_problem/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/validate_problem/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | validate_plan | 3000 | 0 / 0 | 97.8 | 98.6 | 0.8 | [0.1, 1.5] | 0.0459 | 0.5508 | A/qwen3_6_35b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |
| qwen3_6_35b | simulate | 300 | 0 / 0 | 28.3 | 25.7 | -2.7 | [-6.3, 1.3] | 0.2637 | 1 | A/qwen3_6_35b/simulate/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/simulate/steered: criterion met [consequence: separate-apparatus replication (whole rerun)] |

## E4. Delivery gap among trials with a correct tool result (§4)

| model | task | arm | tool-correct | gap | gap % | REFUSED_OR_CLIPPED_FINAL | NO_FINAL_ANSWER | TOOL_INPUT_ERROR | SUMMARY_ONLY | ABRIDGED | WRONG_WRAPPER | NUMERIC_OMITTED | WRONG_FACTS | NEEDS_READING |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma4_26b-a4b | solve | plain | 296 | 19 | 6.4 | 10 | 0 | 0 | 0 | 0 | 3 | 0 | 6 | 0 |
| gemma4_26b-a4b | solve | steered | 300 | 14 | 4.7 | 10 | 0 | 0 | 0 | 0 | 1 | 0 | 3 | 0 |
| gemma4_26b-a4b | validate_domain | plain | 352 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemma4_26b-a4b | validate_domain | steered | 356 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemma4_26b-a4b | validate_problem | plain | 597 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemma4_26b-a4b | validate_problem | steered | 600 | 2 | 0.3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| gemma4_26b-a4b | validate_plan | plain | 596 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gemma4_26b-a4b | validate_plan | steered | 2764 | 3 | 0.1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| gemma4_26b-a4b | simulate | plain | 272 | 247 | 90.8 | 148 | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 81 |
| gemma4_26b-a4b | simulate | steered | 272 | 248 | 91.2 | 151 | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 79 |
| Qwen3_5_9B | solve | plain | 300 | 34 | 11.3 | 20 | 0 | 0 | 0 | 1 | 0 | 0 | 13 | 0 |
| Qwen3_5_9B | solve | steered | 300 | 33 | 11.0 | 19 | 0 | 0 | 2 | 2 | 0 | 0 | 10 | 0 |
| Qwen3_5_9B | validate_domain | plain | 360 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3_5_9B | validate_domain | steered | 360 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3_5_9B | validate_problem | plain | 569 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3_5_9B | validate_problem | steered | 546 | 2 | 0.4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| Qwen3_5_9B | validate_plan | plain | 2776 | 20 | 0.7 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 4 |
| Qwen3_5_9B | validate_plan | steered | 2884 | 7 | 0.2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 4 |
| Qwen3_5_9B | simulate | plain | 204 | 152 | 74.5 | 106 | 0 | 0 | 0 | 1 | 0 | 0 | 35 | 10 |
| Qwen3_5_9B | simulate | steered | 261 | 212 | 81.2 | 132 | 0 | 0 | 0 | 1 | 0 | 1 | 40 | 38 |
| qwen3_6_35b | solve | plain | 247 | 33 | 13.4 | 22 | 0 | 0 | 1 | 4 | 3 | 0 | 3 | 0 |
| qwen3_6_35b | solve | steered | 298 | 36 | 12.1 | 23 | 0 | 0 | 3 | 3 | 2 | 0 | 3 | 2 |
| qwen3_6_35b | validate_domain | plain | 355 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qwen3_6_35b | validate_domain | steered | 358 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qwen3_6_35b | validate_problem | plain | 583 | 10 | 1.7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 9 |
| qwen3_6_35b | validate_problem | steered | 584 | 0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| qwen3_6_35b | validate_plan | plain | 2472 | 17 | 0.7 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 12 |
| qwen3_6_35b | validate_plan | steered | 2974 | 15 | 0.5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| qwen3_6_35b | simulate | plain | 282 | 197 | 69.9 | 151 | 0 | 0 | 0 | 0 | 0 | 9 | 26 | 11 |
| qwen3_6_35b | simulate | steered | 287 | 210 | 73.2 | 155 | 0 | 0 | 0 | 0 | 0 | 7 | 23 | 25 |

## Registered readings (§5)

- **R1** (E2, Gemma validate_plan; Δ̂ +0.9, 95% CI [-1.2, 2.9]): No delivered harm.
  - input cells: C/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: Part C parity is reported, not a gate on E2 (§2 Part C)]; A/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]
- **R2** (E3, Gemma validate_plan; Δ̂ +7.5, 95% CI [4.9, 10.2]): Unresolved.
  - input cells: A/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)]
- **R3**: Title changes to the two-gate reading (invocation and delivery). (models with an E3 validate_plan gain above +5: none)
  - input cells: A/gemma4_26b-a4b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/validate_plan/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/validate_plan/steered: criterion met [consequence: separate-apparatus replication (whole rerun)]
- **R4** (solve, tool-verified, full uncut answer: gemma4_26b-a4b 97.7% of 576; Qwen3_5_9B 95.0% of 561; qwen3_6_35b 95.2% of 498): The canonical open-weight delivery gap on solve is attributed to storage and the refused final request.
  - input cells: A/gemma4_26b-a4b/solve/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/gemma4_26b-a4b/solve/steered: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/solve/plain: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/Qwen3_5_9B/solve/steered: criterion met [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/solve/plain: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)]; A/qwen3_6_35b/solve/steered: criterion not met (unresolved) [consequence: separate-apparatus replication (whole rerun)]
- **R5** (neutral-plain − minimal-plain invocation +6.9, 90% CI [3.6, 10.7]): The directive suppresses calling.
- **R5, steering** (neutral-steered − minimal-steered invocation +5.0, 90% CI [0.5, 11.5]): Not shown (neutral-steered not within ±5 of minimal-steered)

| 2 × 2 cell | n | invocation | 95% CI | delivered | 95% CI |
|---|---|---|---|---|---|
| minimal-plain | 3000 | 20.0 | [8.5, 33.1] | 89.2 | [84.6, 93.1] |
| minimal-steered | 3000 | 93.1 | [82.9, 99.9] | 96.6 | [93.1, 98.9] |
| neutral-plain | 3000 | 26.9 | [14.5, 40.0] | 89.5 | [85.5, 93.0] |
| neutral-steered | 3000 | 98.1 | [95.8, 100.0] | 98.6 | [97.7, 99.4] |

