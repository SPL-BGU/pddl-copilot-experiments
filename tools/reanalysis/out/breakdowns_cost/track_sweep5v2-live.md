# Classical vs numeric, sweep5v2-live, think off

## solve

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 150 | 6.7 [3.7, 11.8] | 8.7 [5.1, 14.3] | +2.0 |
| Gemma 26B a4b | tools-plain | tool-verified | 150 | 99.3 [96.3, 99.9] | 99.3 [96.3, 99.9] | +0.0 |
|  |  | delivered | 150 | ⟨14.0, 35.3⟩ (c32) | ⟨14.7, 35.3⟩ (c31) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 150 | 100.0 [97.5, 100.0] | 97.3 [93.3, 99.0] | -2.7 |
|  |  | delivered | 150 | ⟨26.7, 65.3⟩ (c58) | ⟨20.7, 53.3⟩ (c49) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 150 | 9.3 [5.6, 15.1] | 12.0 [7.7, 18.2] | +2.7 |
| Qwen3.5 9B | tools-plain | tool-verified | 150 | 100.0 [97.5, 100.0] | 98.7 [95.3, 99.6] | -1.3 |
|  |  | delivered | 150 | ⟨36.0, 82.7⟩ (c70) | ⟨16.0, 34.7⟩ (c28) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 150 | 100.0 [97.5, 100.0] | 100.0 [97.5, 100.0] | +0.0 |
|  |  | delivered | 150 | ⟨32.0, 88.7⟩ (c85) | ⟨23.3, 42.0⟩ (c28) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 150 | 6.7 [3.7, 11.8] | 12.0 [7.7, 18.2] | +5.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 150 | 56.0 [48.0, 63.7] | 70.0 [62.2, 76.8] | +14.0 |
|  |  | delivered | 150 | ⟨15.3, 69.3⟩ (c81) | ⟨10.0, 38.0⟩ (c42) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 150 | 90.0 [84.2, 93.8] | 94.0 [89.0, 96.8] | +4.0 |
|  |  | delivered | 150 | ⟨20.7, 57.3⟩ (c55) | ⟨12.7, 38.0⟩ (c38) |  |

## validate_domain

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 180 | 90.0 [84.7, 93.6] | 65.6 [58.4, 72.1] | -24.4 |
| Gemma 26B a4b | tools-plain | tool-verified | 180 | 98.3 [95.2, 99.4] | 96.7 [92.9, 98.5] | -1.7 |
|  |  | delivered | 180 | ⟨97.8, 98.3⟩ (c1) | ⟨88.9, 97.8⟩ (c16) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 180 | 98.3 [95.2, 99.4] | 98.3 [95.2, 99.4] | +0.0 |
|  |  | delivered | 180 | 98.3 [95.2, 99.4] | ⟨91.1, 98.3⟩ (c13) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 180 | 35.6 [28.9, 42.8] | 15.6 [11.0, 21.6] | -20.0 |
| Qwen3.5 9B | tools-plain | tool-verified | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] | +0.0 |
|  |  | delivered | 180 | 100.0 [97.9, 100.0] | ⟨99.4, 100.0⟩ (c1) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] | +0.0 |
|  |  | delivered | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] |  |
| Qwen3.6 35B | no-tools | final answer, strict | 180 | 82.2 [76.0, 87.1] | 53.3 [46.1, 60.5] | -28.9 |
| Qwen3.6 35B | tools-plain | tool-verified | 180 | 98.9 [96.0, 99.7] | 98.9 [96.0, 99.7] | +0.0 |
|  |  | delivered | 180 | ⟨91.1, 99.4⟩ (c15) | ⟨92.8, 98.9⟩ (c11) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 180 | 100.0 [97.9, 100.0] | 99.4 [96.9, 99.9] | -0.6 |
|  |  | delivered | 180 | ⟨92.8, 100.0⟩ (c13) | ⟨93.9, 99.4⟩ (c10) |  |

## validate_problem

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 300 | 73.7 [68.4, 78.3] | 76.0 [70.9, 80.5] | +2.3 |
| Gemma 26B a4b | tools-plain | tool-verified | 300 | 99.7 [98.1, 99.9] | 99.7 [98.1, 99.9] | +0.0 |
|  |  | delivered | 300 | ⟨90.3, 100.0⟩ (c29) | ⟨78.3, 99.7⟩ (c64) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 300 | 100.0 [98.7, 100.0] | 100.0 [98.7, 100.0] | +0.0 |
|  |  | delivered | 300 | ⟨91.7, 100.0⟩ (c25) | ⟨91.7, 100.0⟩ (c25) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 300 | 69.3 [63.9, 74.3] | 62.0 [56.4, 67.3] | -7.3 |
| Qwen3.5 9B | tools-plain | tool-verified | 300 | 95.7 [92.7, 97.5] | 94.7 [91.5, 96.7] | -1.0 |
|  |  | delivered | 300 | ⟨91.3, 96.0⟩ (c14) | ⟨93.0, 94.7⟩ (c5) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 300 | 94.3 [91.1, 96.4] | 86.0 [81.6, 89.5] | -8.3 |
|  |  | delivered | 300 | ⟨90.0, 94.3⟩ (c13) | ⟨85.3, 87.7⟩ (c7) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 300 | 74.0 [68.8, 78.6] | 77.3 [72.3, 81.7] | +3.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 300 | 95.7 [92.7, 97.5] | 98.0 [95.7, 99.1] | +2.3 |
|  |  | delivered | 300 | ⟨74.7, 97.7⟩ (c69) | ⟨74.7, 98.0⟩ (c70) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 300 | 96.7 [94.0, 98.2] | 98.0 [95.7, 99.1] | +1.3 |
|  |  | delivered | 300 | ⟨81.7, 96.7⟩ (c45) | ⟨82.7, 97.3⟩ (c44) |  |

## validate_plan

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 1500 | 88.1 [86.4, 89.7] | 87.5 [85.8, 89.1] | -0.6 |
| Gemma 26B a4b | tools-plain | tool-verified | 1500 | 24.3 [22.2, 26.5] | 16.9 [15.1, 18.8] | -7.4 |
|  |  | delivered | 1500 | ⟨9.1, 100.0⟩ (c1364) | ⟨4.1, 99.1⟩ (c1426) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 1500 | 88.4 [86.7, 89.9] | 96.7 [95.7, 97.5] | +8.3 |
|  |  | delivered | 1500 | ⟨58.3, 98.4⟩ (c602) | ⟨52.7, 91.8⟩ (c586) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 1500 | 80.5 [78.4, 82.4] | 79.0 [76.9, 81.0] | -1.5 |
| Qwen3.5 9B | tools-plain | tool-verified | 1500 | 98.3 [97.5, 98.8] | 88.1 [86.3, 89.6] | -10.2 |
|  |  | delivered | 1500 | ⟨85.9, 91.9⟩ (c90) | ⟨75.7, 82.6⟩ (c104) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 1500 | 99.1 [98.5, 99.5] | 92.9 [91.5, 94.1] | -6.2 |
|  |  | delivered | 1500 | ⟨90.4, 93.9⟩ (c53) | ⟨83.5, 83.9⟩ (c6) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 1500 | 92.2 [90.7, 93.5] | 89.6 [88.0, 91.0] | -2.6 |
| Qwen3.6 35B | tools-plain | tool-verified | 1500 | 81.8 [79.8, 83.7] | 82.5 [80.5, 84.4] | +0.7 |
|  |  | delivered | 1500 | ⟨57.3, 93.1⟩ (c537) | ⟨52.7, 87.4⟩ (c521) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 1500 | 99.8 [99.4, 99.9] | 98.7 [98.0, 99.2] | -1.1 |
|  |  | delivered | 1500 | ⟨79.3, 93.7⟩ (c216) | ⟨72.5, 86.3⟩ (c207) |  |

## simulate

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 100.0⟩ (c150) | ⟨0.0, 100.0⟩ (c150) |  |
| Gemma 26B a4b | tools-plain | tool-verified | 150 | 96.0 [91.5, 98.2] | 87.3 [81.1, 91.7] | -8.7 |
|  |  | delivered | 150 | ⟨0.0, 24.0⟩ (c36) | ⟨0.0, 30.7⟩ (c46) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 150 | 96.0 [91.5, 98.2] | 85.3 [78.8, 90.1] | -10.7 |
|  |  | delivered | 150 | ⟨0.0, 24.0⟩ (c36) | ⟨0.0, 30.7⟩ (c46) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 86.0⟩ (c129) | ⟨0.0, 88.7⟩ (c133) |  |
| Qwen3.5 9B | tools-plain | tool-verified | 150 | 64.7 [56.7, 71.9] | 65.3 [57.4, 72.5] | +0.7 |
|  |  | delivered | 150 | ⟨0.0, 36.0⟩ (c54) | ⟨0.0, 42.0⟩ (c63) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 150 | 88.0 [81.8, 92.3] | 78.0 [70.7, 83.9] | -10.0 |
|  |  | delivered | 150 | ⟨0.0, 20.7⟩ (c31) | ⟨0.0, 30.0⟩ (c45) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 92.7⟩ (c139) | ⟨0.0, 88.0⟩ (c132) |  |
| Qwen3.6 35B | tools-plain | tool-verified | 150 | 72.7 [65.0, 79.2] | 76.7 [69.3, 82.7] | +4.0 |
|  |  | delivered | 150 | ⟨0.0, 40.7⟩ (c61) | ⟨0.0, 37.3⟩ (c56) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 150 | 99.3 [96.3, 99.9] | 94.7 [89.8, 97.3] | -4.7 |
|  |  | delivered | 150 | ⟨0.0, 24.0⟩ (c36) | ⟨0.0, 30.0⟩ (c45) |  |

## solve cost-of-pass by track (pooled over the three models)

Tokens = prompt + completion summed over turns (the paper's count). Cost-of-pass = total tokens / successes. Multiplier = tools / no-tools. Delivered is a range because the tool arm's delivered count is a bound.

| track | tool arm | no-tools successes | no-tools tok/trial | no-tools tok/pass | tool-verified ok | delivered ok ⟨low, high⟩ | tools tok/trial | multiplier, tool-verified | multiplier, delivered |
|---|---|---|---|---|---|---|---|---|---|
| all | tools-plain | 83/900 (9.2%) | 4,488 | 48,666 | 785/900 | ⟨159, 443⟩/900 | 18,706 | 0.44x | 0.78x to 2.18x |
| all | tools-steered | 83/900 (9.2%) | 4,488 | 48,666 | 872/900 | ⟨204, 517⟩/900 | 18,108 | 0.38x | 0.65x to 1.64x |
| classical | tools-plain | 34/450 (7.6%) | 4,795 | 63,464 | 383/450 | ⟨98, 281⟩/450 | 15,601 | 0.29x | 0.39x to 1.13x |
| classical | tools-steered | 34/450 (7.6%) | 4,795 | 63,464 | 435/450 | ⟨119, 317⟩/450 | 15,027 | 0.24x | 0.34x to 0.90x |
| numeric | tools-plain | 49/450 (10.9%) | 4,181 | 38,398 | 402/450 | ⟨61, 162⟩/450 | 21,810 | 0.64x | 1.58x to 4.19x |
| numeric | tools-steered | 49/450 (10.9%) | 4,181 | 38,398 | 437/450 | ⟨85, 200⟩/450 | 21,189 | 0.57x | 1.24x to 2.92x |

