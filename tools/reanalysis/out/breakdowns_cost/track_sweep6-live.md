# Classical vs numeric, sweep6-live, think off

## solve

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 150 | 4.7 [2.3, 9.3] | 11.3 [7.2, 17.4] | +6.7 |
| Gemma 26B a4b | tools-plain | tool-verified | 150 | 98.7 [95.3, 99.6] | 96.0 [91.5, 98.2] | -2.7 |
|  |  | delivered | 150 | ⟨13.3, 34.0⟩ (c31) | ⟨16.0, 36.0⟩ (c30) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 150 | 98.7 [95.3, 99.6] | 93.3 [88.2, 96.3] | -5.3 |
|  |  | delivered | 150 | ⟨24.7, 53.3⟩ (c43) | ⟨20.7, 49.3⟩ (c43) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 150 | 7.3 [4.1, 12.7] | 15.3 [10.4, 22.0] | +8.0 |
| Qwen3.5 9B | tools-plain | tool-verified | 150 | 100.0 [97.5, 100.0] | 94.0 [89.0, 96.8] | -6.0 |
|  |  | delivered | 150 | ⟨30.7, 83.3⟩ (c79) | ⟨9.3, 28.7⟩ (c29) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 150 | 100.0 [97.5, 100.0] | 96.0 [91.5, 98.2] | -4.0 |
|  |  | delivered | 150 | ⟨30.0, 90.0⟩ (c90) | ⟨13.3, 42.7⟩ (c44) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 150 | 6.0 [3.2, 11.0] | 13.3 [8.8, 19.7] | +7.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 150 | 46.0 [38.2, 54.0] | 58.7 [50.7, 66.2] | +12.7 |
|  |  | delivered | 150 | ⟨11.3, 64.0⟩ (c79) | ⟨6.7, 42.0⟩ (c53) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 150 | 85.3 [78.8, 90.1] | 86.7 [80.3, 91.2] | +1.3 |
|  |  | delivered | 150 | ⟨12.0, 48.7⟩ (c55) | ⟨8.0, 34.0⟩ (c39) |  |

## validate_domain

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 180 | 88.9 [83.5, 92.7] | 72.2 [65.3, 78.2] | -16.7 |
| Gemma 26B a4b | tools-plain | tool-verified | 180 | 100.0 [97.9, 100.0] | 98.9 [96.0, 99.7] | -1.1 |
|  |  | delivered | 180 | ⟨99.4, 100.0⟩ (c1) | ⟨91.1, 98.9⟩ (c14) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 180 | 99.4 [96.9, 99.9] | 98.3 [95.2, 99.4] | -1.1 |
|  |  | delivered | 180 | 99.4 [96.9, 99.9] | ⟨94.4, 98.3⟩ (c7) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 180 | 34.4 [27.9, 41.6] | 18.9 [13.8, 25.2] | -15.6 |
| Qwen3.5 9B | tools-plain | tool-verified | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] | +0.0 |
|  |  | delivered | 180 | ⟨99.4, 100.0⟩ (c1) | ⟨99.4, 100.0⟩ (c1) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] | +0.0 |
|  |  | delivered | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] |  |
| Qwen3.6 35B | no-tools | final answer, strict | 180 | 80.6 [74.2, 85.7] | 60.0 [52.7, 66.9] | -20.6 |
| Qwen3.6 35B | tools-plain | tool-verified | 180 | 91.7 [86.7, 94.9] | 99.4 [96.9, 99.9] | +7.8 |
|  |  | delivered | 180 | ⟨83.3, 100.0⟩ (c30) | ⟨91.7, 99.4⟩ (c14) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 180 | 95.0 [90.8, 97.3] | 100.0 [97.9, 100.0] | +5.0 |
|  |  | delivered | 180 | ⟨91.7, 97.8⟩ (c11) | ⟨94.4, 100.0⟩ (c10) |  |

## validate_problem

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 300 | 79.7 [74.8, 83.8] | 76.0 [70.9, 80.5] | -3.7 |
| Gemma 26B a4b | tools-plain | tool-verified | 300 | 98.7 [96.6, 99.5] | 98.0 [95.7, 99.1] | -0.7 |
|  |  | delivered | 300 | ⟨88.7, 98.7⟩ (c30) | ⟨73.3, 98.0⟩ (c74) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 300 | 97.7 [95.3, 98.9] | 98.3 [96.2, 99.3] | +0.7 |
|  |  | delivered | 300 | ⟨86.3, 98.7⟩ (c37) | ⟨89.0, 98.0⟩ (c27) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 300 | 74.0 [68.8, 78.6] | 64.7 [59.1, 69.9] | -9.3 |
| Qwen3.5 9B | tools-plain | tool-verified | 300 | 94.7 [91.5, 96.7] | 93.3 [89.9, 95.6] | -1.3 |
|  |  | delivered | 300 | ⟨89.7, 94.0⟩ (c13) | ⟨92.0, 93.3⟩ (c4) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 300 | 95.0 [91.9, 96.9] | 92.3 [88.8, 94.8] | -2.7 |
|  |  | delivered | 300 | ⟨91.3, 94.0⟩ (c8) | ⟨89.0, 92.3⟩ (c10) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 300 | 76.0 [70.9, 80.5] | 77.3 [72.3, 81.7] | +1.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 300 | 87.7 [83.5, 90.9] | 97.3 [94.8, 98.6] | +9.7 |
|  |  | delivered | 300 | ⟨66.3, 93.7⟩ (c82) | ⟨69.0, 97.0⟩ (c84) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 300 | 92.0 [88.4, 94.6] | 99.0 [97.1, 99.7] | +7.0 |
|  |  | delivered | 300 | ⟨74.7, 94.7⟩ (c60) | ⟨83.0, 99.0⟩ (c48) |  |

## validate_plan

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 1500 | 87.8 [86.0, 89.4] | 88.7 [87.0, 90.2] | +0.9 |
| Gemma 26B a4b | tools-plain | tool-verified | 1500 | 19.8 [17.9, 21.9] | 15.6 [13.9, 17.5] | -4.2 |
|  |  | delivered | 1500 | ⟨6.4, 100.0⟩ (c1404) | ⟨3.1, 98.9⟩ (c1437) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 1500 | 79.4 [77.3, 81.4] | 92.1 [90.7, 93.4] | +12.7 |
|  |  | delivered | 1500 | ⟨44.6, 98.5⟩ (c808) | ⟨47.4, 87.1⟩ (c595) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 1500 | 78.9 [76.7, 80.9] | 79.8 [77.7, 81.8] | +0.9 |
| Qwen3.5 9B | tools-plain | tool-verified | 1500 | 93.1 [91.7, 94.2] | 92.1 [90.6, 93.3] | -1.0 |
|  |  | delivered | 1500 | ⟨79.8, 89.7⟩ (c148) | ⟨77.5, 81.8⟩ (c65) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 1500 | 98.8 [98.1, 99.2] | 92.8 [91.4, 94.0] | -6.0 |
|  |  | delivered | 1500 | ⟨88.8, 91.0⟩ (c33) | ⟨81.5, 81.7⟩ (c3) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 1500 | 89.3 [87.7, 90.8] | 88.7 [87.0, 90.2] | -0.6 |
| Qwen3.6 35B | tools-plain | tool-verified | 1500 | 81.3 [79.2, 83.2] | 82.4 [80.4, 84.2] | +1.1 |
|  |  | delivered | 1500 | ⟨52.0, 91.5⟩ (c592) | ⟨51.6, 86.0⟩ (c516) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 1500 | 96.6 [95.6, 97.4] | 97.5 [96.6, 98.2] | +0.9 |
|  |  | delivered | 1500 | ⟨69.6, 90.3⟩ (c310) | ⟨68.5, 84.7⟩ (c244) |  |

## simulate

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 100.0⟩ (c150) | ⟨0.0, 100.0⟩ (c150) |  |
| Gemma 26B a4b | tools-plain | tool-verified | 150 | 88.0 [81.8, 92.3] | 83.3 [76.6, 88.4] | -4.7 |
|  |  | delivered | 150 | ⟨0.0, 26.7⟩ (c40) | ⟨0.0, 29.3⟩ (c44) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 150 | 88.7 [82.6, 92.8] | 86.0 [79.5, 90.7] | -2.7 |
|  |  | delivered | 150 | ⟨0.0, 26.0⟩ (c39) | ⟨0.0, 31.3⟩ (c47) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 89.3⟩ (c134) | ⟨0.0, 93.3⟩ (c140) |  |
| Qwen3.5 9B | tools-plain | tool-verified | 150 | 74.7 [67.2, 81.0] | 62.0 [54.0, 69.4] | -12.7 |
|  |  | delivered | 150 | ⟨0.0, 30.0⟩ (c45) | ⟨0.0, 38.0⟩ (c57) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 150 | 92.0 [86.5, 95.4] | 75.3 [67.9, 81.5] | -16.7 |
|  |  | delivered | 150 | ⟨0.0, 20.0⟩ (c30) | ⟨0.0, 30.0⟩ (c45) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 94.7⟩ (c142) | ⟨0.0, 88.0⟩ (c132) |  |
| Qwen3.6 35B | tools-plain | tool-verified | 150 | 65.3 [57.4, 72.5] | 72.7 [65.0, 79.2] | +7.3 |
|  |  | delivered | 150 | ⟨0.0, 45.3⟩ (c68) | ⟨0.0, 39.3⟩ (c59) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 150 | 98.7 [95.3, 99.6] | 93.3 [88.2, 96.3] | -5.3 |
|  |  | delivered | 150 | ⟨0.0, 22.0⟩ (c33) | ⟨0.0, 30.0⟩ (c45) |  |

## solve cost-of-pass by track (pooled over the three models)

Tokens = prompt + completion summed over turns (the paper's count). Cost-of-pass = total tokens / successes. Multiplier = tools / no-tools. Delivered is a range because the tool arm's delivered count is a bound.

| track | tool arm | no-tools successes | no-tools tok/trial | no-tools tok/pass | tool-verified ok | delivered ok ⟨low, high⟩ | tools tok/trial | multiplier, tool-verified | multiplier, delivered |
|---|---|---|---|---|---|---|---|---|---|
| all | tools-plain | 87/900 (9.7%) | 5,051 | 52,248 | 740/900 | ⟨131, 432⟩/900 | 19,031 | 0.44x | 0.76x to 2.50x |
| all | tools-steered | 87/900 (9.7%) | 5,051 | 52,248 | 840/900 | ⟨163, 477⟩/900 | 18,648 | 0.38x | 0.67x to 1.97x |
| classical | tools-plain | 27/450 (6.0%) | 5,502 | 91,706 | 367/450 | ⟨83, 272⟩/450 | 16,044 | 0.21x | 0.29x to 0.95x |
| classical | tools-steered | 27/450 (6.0%) | 5,502 | 91,706 | 426/450 | ⟨100, 288⟩/450 | 16,085 | 0.19x | 0.27x to 0.79x |
| numeric | tools-plain | 60/450 (13.3%) | 4,599 | 34,492 | 373/450 | ⟨48, 160⟩/450 | 22,018 | 0.77x | 1.80x to 5.98x |
| numeric | tools-steered | 60/450 (13.3%) | 4,599 | 34,492 | 414/450 | ⟨63, 189⟩/450 | 21,211 | 0.67x | 1.46x to 4.39x |

