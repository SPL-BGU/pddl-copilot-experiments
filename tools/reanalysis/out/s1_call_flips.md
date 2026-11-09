# Call-state flips, main sweep vs delivered rerun (tool cells, think=off)

Calling = `tool_selected` (the task's own tool). Flips are trials whose call state differs between the two runs, paired on the trial key. Prompt check: pairs where both rows are single-turn, share with equal `tokens.prompt`.

| model | task | arm | n paired | calls, main | calls, rerun | called → not | not → called | flips (% of n) | net | any-call flips | prompt equal, single-turn pairs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | plain | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | solve | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_domain | plain | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_domain | steered | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_problem | plain | 600 | 599 (99.8) | 600 (100.0) | 0 | 1 | 1 (0.2) | +1 | 1 | 0 / 0 |
| Gemma-26B | validate_problem | steered | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_plan | plain | 3,000 | 622 (20.7) | 600 (20.0) | 56 | 34 | 90 (3.0) | -22 | 90 | 2,344 / 2,344 |
| Gemma-26B | validate_plan | steered | 3,000 | 2,808 (93.6) | 2,792 (93.1) | 37 | 21 | 58 (1.9) | -16 | 58 | 171 / 171 |
| Gemma-26B | simulate | plain | 300 | 299 (99.7) | 299 (99.7) | 0 | 0 | 0 (0.0) | +0 | 0 | 1 / 1 |
| Gemma-26B | simulate | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | solve | plain | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | solve | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_domain | plain | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_domain | steered | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_problem | plain | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_problem | steered | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_plan | plain | 3,000 | 2,937 (97.9) | 2,935 (97.8) | 13 | 11 | 24 (0.8) | -2 | 22 | 52 / 52 |
| Qwen3.5-9B | validate_plan | steered | 3,000 | 3,000 (100.0) | 3,000 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | simulate | plain | 300 | 240 (80.0) | 242 (80.7) | 4 | 6 | 10 (3.3) | +2 | 9 | 53 / 53 |
| Qwen3.5-9B | simulate | steered | 300 | 299 (99.7) | 300 (100.0) | 0 | 1 | 1 (0.3) | +1 | 1 | 0 / 0 |
| Qwen3.6-35B | solve | plain | 300 | 204 (68.0) | 248 (82.7) | 22 | 66 | 88 (29.3) | +44 | 61 | 20 / 20 |
| Qwen3.6-35B | solve | steered | 300 | 281 (93.7) | 299 (99.7) | 1 | 19 | 20 (6.7) | +18 | 10 | 0 / 0 |
| Qwen3.6-35B | validate_domain | plain | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.6-35B | validate_domain | steered | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.6-35B | validate_problem | plain | 600 | 591 (98.5) | 596 (99.3) | 1 | 6 | 7 (1.2) | +5 | 7 | 3 / 3 |
| Qwen3.6-35B | validate_problem | steered | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.6-35B | validate_plan | plain | 3,000 | 2,487 (82.9) | 2,494 (83.1) | 195 | 202 | 397 (13.2) | +7 | 396 | 311 / 311 |
| Qwen3.6-35B | validate_plan | steered | 3,000 | 2,997 (99.9) | 3,000 (100.0) | 0 | 3 | 3 (0.1) | +3 | 3 | 0 / 0 |
| Qwen3.6-35B | simulate | plain | 300 | 229 (76.3) | 299 (99.7) | 1 | 71 | 72 (24.0) | +70 | 72 | 0 / 0 |
| Qwen3.6-35B | simulate | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |

Unpaired rows: 0. Rows with `tool_selected` null (counted as not called): 0. Prompt tokens equal on 2,955 of 2,955 single-turn pairs.

Largest flip share per model: Gemma-26B 3.0%; Qwen3.5-9B 3.3%; Qwen3.6-35B 29.3%.

