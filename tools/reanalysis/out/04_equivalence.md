## (a) Contamination: anonymized minus canonical, no-tools

### think=off

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B solve | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B v_dom | 360 | 80.8 | 79.7 | -1.11 | [-4.64, +2.42] | domain (k=20) | [-4.72, +1.94] | 3.53 | 0.036 | criterion met |
| Qwen3.5-0.8B v_prob | 600 | 51.2 | 50.8 | -0.33 | [-3.54, +2.88] | domain (k=20) | [-3.50, +2.33] | 3.21 | 0.011 | criterion met |
| Qwen3.5-0.8B v_plan | 3000 | 49.8 | 49.9 | +0.03 | [-0.60, +0.66] | domain (k=20) | [-0.57, +0.57] | 0.63 | 0.000 | criterion met |
| Qwen3.5-0.8B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B pooled (5 tasks) | 4560 | 45.9 | 45.8 | -0.11 | [-0.55, +0.34] | problem (k=220) | [-0.55, +0.29] | 0.44 | 0.000 | criterion met |
| Qwen3.5-4B solve | 300 | 7.7 | 5.7 | -2.00 | [-4.82, +0.82] | problem (k=100) | [-4.33, +0.00] | 2.82 | 0.040 | criterion met (floor: low information) |
| Qwen3.5-4B v_dom | 360 | 19.2 | 20.3 | +1.11 | [-0.38, +2.61] | domain (k=20) | [+0.00, +2.78] | 1.49 | 0.000 | criterion met |
| Qwen3.5-4B v_prob | 600 | 56.5 | 54.3 | -2.17 | [-6.05, +1.72] | domain (k=20) | [-6.00, +1.33] | 3.88 | 0.111 | criterion not met (unresolved) |
| Qwen3.5-4B v_plan | 3000 | 74.0 | 71.5 | -2.57 | [-5.65, +0.51] | domain (k=20) | [-5.53, +0.23] | 3.08 | 0.094 | criterion not met (unresolved) |
| Qwen3.5-4B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-4B pooled (5 tasks) | 4560 | 58.2 | 56.1 | -2.02 | [-4.33, +0.29] | domain (k=20) | [-4.23, +0.09] | 2.31 | 0.019 | criterion met |
| Qwen3.5-9B solve | 300 | 10.7 | 11.3 | +0.67 | [-2.57, +3.91] | problem (k=100) | [-2.00, +3.67] | 3.24 | 0.014 | criterion met |
| Qwen3.5-9B v_dom | 360 | 25.6 | 26.7 | +1.11 | [-4.66, +6.88] | domain (k=20) | [-4.72, +6.11] | 5.77 | 0.129 | criterion not met (unresolved) |
| Qwen3.5-9B v_prob | 600 | 65.7 | 69.3 | +3.67 | [-1.24, +8.58] | domain (k=20) | [-0.67, +8.50] | 4.91 | 0.322 | criterion not met (unresolved) |
| Qwen3.5-9B v_plan | 3000 | 79.7 | 79.3 | -0.40 | [-2.94, +2.14] | domain (k=20) | [-2.77, +1.97] | 2.54 | 0.003 | criterion met |
| Qwen3.5-9B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-9B pooled (5 tasks) | 4560 | 63.8 | 64.2 | +0.35 | [-1.52, +2.23] | domain (k=20) | [-1.40, +2.06] | 1.88 | 0.000 | criterion met |
| Gemma-26B solve | 300 | 7.7 | 8.0 | +0.33 | [-3.80, +4.47] | domain (k=20) | [-3.33, +4.33] | 4.14 | 0.033 | criterion met (floor: low information) |
| Gemma-26B v_dom | 360 | 77.8 | 80.6 | +2.78 | [-2.03, +7.58] | domain (k=20) | [-1.39, +7.22] | 4.80 | 0.217 | criterion not met (unresolved) |
| Gemma-26B v_prob | 600 | 74.8 | 77.8 | +3.00 | [-1.82, +7.82] | domain (k=20) | [-1.33, +7.50] | 4.82 | 0.241 | criterion not met (unresolved) |
| Gemma-26B v_plan | 3000 | 87.8 | 88.2 | +0.40 | [-2.36, +3.16] | domain (k=20) | [-2.20, +2.90] | 2.76 | 0.005 | criterion met |
| Gemma-26B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Gemma-26B pooled (5 tasks) | 4560 | 74.3 | 75.2 | +0.90 | [-0.71, +2.51] | domain (k=20) | [-0.61, +2.37] | 1.61 | 0.000 | criterion met |
| Qwen3.6-35B solve | 300 | 9.3 | 9.7 | +0.33 | [-3.26, +3.93] | domain (k=20) | [-3.00, +3.67] | 3.59 | 0.018 | criterion met (floor: low information) |
| Qwen3.6-35B v_dom | 360 | 67.8 | 70.3 | +2.50 | [-4.38, +9.38] | domain (k=20) | [-4.17, +8.61] | 6.88 | 0.269 | criterion not met (unresolved) |
| Qwen3.6-35B v_prob | 600 | 75.7 | 76.7 | +1.00 | [-1.99, +3.99] | domain (k=20) | [-1.50, +4.00] | 2.99 | 0.016 | criterion met |
| Qwen3.6-35B v_plan | 3000 | 90.9 | 89.0 | -1.87 | [-3.67, -0.07] | domain (k=20) | [-3.60, -0.27] | 1.80 | 0.004 | criterion met (ceiling: low information) |
| Qwen3.6-35B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.6-35B pooled (5 tasks) | 4560 | 75.7 | 74.8 | -0.88 | [-2.22, +0.47] | domain (k=20) | [-2.15, +0.33] | 1.35 | 0.000 | criterion met |

### think=on

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B solve | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B v_dom | 360 | 0.3 | 1.4 | +1.11 | [-0.38, +2.61] | domain (k=20) | [-0.28, +2.50] | 1.49 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B v_prob | 600 | 0.2 | 0.7 | +0.50 | [-0.46, +1.46] | domain (k=20) | [-0.17, +1.50] | 0.96 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B v_plan | 3000 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-0.8B pooled (5 tasks) | 4560 | 0.0 | 0.2 | +0.15 | [-0.01, +0.32] | domain (k=20) | [+0.00, +0.31] | 0.17 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-4B solve | 300 | 15.7 | 9.3 | -6.33 | [-10.30, -2.37] | domain (k=20) | [-10.33, -3.00] | 3.96 | 0.716 | criterion not met (unresolved) |
| Qwen3.5-4B v_dom | 360 | 0.8 | 0.8 | +0.00 | [-1.21, +1.21] | domain (k=20) | [-1.11, +1.11] | 1.21 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-4B v_prob | 600 | 11.5 | 11.3 | -0.17 | [-3.47, +3.14] | domain (k=20) | [-3.33, +3.00] | 3.31 | 0.010 | criterion met |
| Qwen3.5-4B v_plan | 3000 | 25.0 | 18.7 | -6.27 | [-10.90, -1.63] | domain (k=20) | [-10.83, -2.23] | 4.64 | 0.679 | criterion not met (unresolved) |
| Qwen3.5-4B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-4B pooled (5 tasks) | 4560 | 19.1 | 14.5 | -4.56 | [-7.87, -1.25] | domain (k=20) | [-7.81, -1.64] | 3.31 | 0.411 | criterion not met (unresolved) |
| Qwen3.5-9B solve | 300 | 27.0 | 27.7 | +0.67 | [-6.62, +7.95] | domain (k=20) | [-6.00, +7.67] | 7.29 | 0.158 | criterion not met (unresolved) |
| Qwen3.5-9B v_dom | 360 | 3.3 | 3.1 | -0.28 | [-2.42, +1.87] | domain (k=20) | [-2.22, +1.67] | 2.15 | 0.001 | criterion met (floor: low information) |
| Qwen3.5-9B v_prob | 600 | 17.5 | 17.2 | -0.33 | [-2.66, +1.99] | domain (k=20) | [-2.67, +1.67] | 2.32 | 0.001 | criterion met |
| Qwen3.5-9B v_plan | 3000 | 21.4 | 17.4 | -4.03 | [-8.11, +0.04] | domain (k=20) | [-7.90, -0.43] | 4.08 | 0.343 | criterion not met (unresolved) |
| Qwen3.5-9B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.5-9B pooled (5 tasks) | 4560 | 18.4 | 15.7 | -2.68 | [-5.44, +0.08] | domain (k=20) | [-5.31, -0.24] | 2.76 | 0.081 | criterion not met (unresolved) |
| Gemma-26B solve | 300 | 3.7 | 3.0 | -0.67 | [-2.74, +1.41] | problem (k=100) | [-2.00, +0.67] | 2.08 | 0.000 | criterion met (floor: low information) |
| Gemma-26B v_dom | 360 | 0.0 | 1.1 | +1.11 | [-0.38, +2.61] | domain (k=20) | [+0.00, +2.78] | 1.49 | 0.000 | criterion met (floor: low information) |
| Gemma-26B v_prob | 600 | 4.5 | 5.3 | +0.83 | [-1.21, +2.88] | domain (k=20) | [-1.00, +2.83] | 2.04 | 0.001 | criterion met (floor: low information) |
| Gemma-26B v_plan | 3000 | 10.3 | 10.1 | -0.20 | [-1.80, +1.40] | domain (k=20) | [-1.67, +1.30] | 1.60 | 0.000 | criterion met |
| Gemma-26B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Gemma-26B pooled (5 tasks) | 4560 | 7.6 | 7.6 | +0.02 | [-1.01, +1.05] | domain (k=20) | [-0.92, +0.99] | 1.03 | 0.000 | criterion met (floor: low information) |
| Qwen3.6-35B solve | 300 | 38.3 | 39.0 | +0.67 | [-5.70, +7.03] | domain (k=20) | [-5.00, +6.67] | 6.36 | 0.127 | criterion not met (unresolved) |
| Qwen3.6-35B v_dom | 360 | 73.3 | 72.2 | -1.11 | [-7.21, +4.99] | domain (k=20) | [-6.94, +4.44] | 6.10 | 0.142 | criterion not met (unresolved) |
| Qwen3.6-35B v_prob | 600 | 77.5 | 74.7 | -2.83 | [-4.93, -0.74] | problem (k=200) | [-4.67, -1.00] | 2.09 | 0.044 | criterion met |
| Qwen3.6-35B v_plan | 3000 | 84.8 | 80.5 | -4.33 | [-6.99, -1.67] | domain (k=20) | [-6.83, -1.90] | 2.66 | 0.335 | criterion not met (unresolved) |
| Qwen3.6-35B sim | 300 | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (floor: low information) |
| Qwen3.6-35B pooled (5 tasks) | 4560 | 74.3 | 71.0 | -3.27 | [-5.07, -1.47] | domain (k=20) | [-4.96, -1.60] | 1.80 | 0.056 | criterion not met (unresolved) |

### Count, think=off

| set | cells | criterion met | of which floor/ceiling (low information) | not met (unresolved) |
|---|---|---|---|---|
| headline 3 models x 5 tasks | 15 | 10 | 6 | 5 |
| all 5 models x 5 tasks | 25 | 18 | 10 | 7 |
| headline 3 models, pooled | 3 | 3 | 0 | 0 |
| all 5 models, pooled | 5 | 5 | 0 | 0 |

## (b) Serving version: vLLM 0.20.2 minus 0.22.0, Qwen3.5-0.8B think=off with-tools

Rows: 0.22.0 run 1 = 9120, 0.22.0 run 2 = 9120, 0.20.2 = 9120; shared keys run1/live = 9120.

### 0.20.2 (live) minus 0.22.0 run 1 - the comparison NUMBERS.md quotes

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| solve / plain | 300 | 9.3 | 12.0 | +2.67 | [+0.22, +5.11] | problem (k=100) | [+0.67, +5.00] | 2.45 | 0.058 | criterion not met (unresolved) |
| solve / steered | 300 | 13.3 | 14.0 | +0.67 | [-0.90, +2.24] | problem (k=100) | [-0.33, +1.67] | 1.57 | 0.000 | criterion met |
| v_dom / plain | 360 | 88.6 | 87.5 | -1.11 | [-3.48, +1.26] | domain (k=20) | [-3.33, +1.11] | 2.37 | 0.005 | criterion met |
| v_dom / steered | 360 | 90.6 | 89.2 | -1.39 | [-3.79, +1.01] | domain (k=20) | [-4.17, +0.00] | 2.40 | 0.009 | criterion met (ceiling: low information) |
| v_prob / plain | 600 | 27.5 | 26.2 | -1.33 | [-2.81, +0.14] | domain (k=20) | [-2.67, +0.00] | 1.47 | 0.000 | criterion met |
| v_prob / steered | 600 | 20.7 | 18.5 | -2.17 | [-5.30, +0.97] | domain (k=20) | [-5.17, +0.50] | 3.14 | 0.067 | criterion not met (unresolved) |
| v_plan / plain | 3000 | 22.0 | 23.2 | +1.23 | [-0.16, +2.63] | domain (k=20) | [+0.07, +2.67] | 1.40 | 0.000 | criterion met |
| v_plan / steered | 3000 | 24.1 | 24.8 | +0.73 | [-0.55, +2.02] | domain (k=20) | [-0.43, +1.97] | 1.29 | 0.000 | criterion met |
| sim / plain | 300 | 6.7 | 6.3 | -0.33 | [-2.62, +1.95] | domain (k=20) | [-2.33, +1.67] | 2.29 | 0.001 | criterion met (floor: low information) |
| sim / steered | 300 | 2.3 | 2.7 | +0.33 | [-1.14, +1.80] | problem (k=100) | [+0.00, +1.00] | 1.47 | 0.000 | criterion met (floor: low information) |
| pooled (9,120) | 9120 | 26.4 | 26.9 | +0.43 | [-0.27, +1.13] | domain (k=20) | [-0.19, +1.11] | 0.70 | 0.000 | criterion met |

Task x arm cells meeting the criterion: 8/10; pooled: criterion met.

Individual trials whose outcome differs between the two runs: 395/9120 (4.3%).

### 0.20.2 (live) minus 0.22.0 run 2

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| solve / plain | 300 | 11.0 | 12.0 | +1.00 | [-1.55, +3.55] | domain (k=20) | [-1.35, +3.33] | 2.55 | 0.007 | criterion met |
| solve / steered | 300 | 16.3 | 14.0 | -2.33 | [-4.30, -0.37] | problem (k=100) | [-4.00, -1.00] | 1.97 | 0.013 | criterion met |
| v_dom / plain | 360 | 88.6 | 87.5 | -1.11 | [-3.58, +1.36] | domain (k=20) | [-3.89, +0.56] | 2.47 | 0.007 | criterion met |
| v_dom / steered | 360 | 90.6 | 89.2 | -1.39 | [-3.79, +1.01] | domain (k=20) | [-4.17, +0.00] | 2.40 | 0.009 | criterion met (ceiling: low information) |
| v_prob / plain | 600 | 27.3 | 26.2 | -1.17 | [-2.85, +0.52] | domain (k=20) | [-2.67, +0.33] | 1.69 | 0.000 | criterion met |
| v_prob / steered | 600 | 17.2 | 18.5 | +1.33 | [-1.15, +3.82] | domain (k=20) | [-1.00, +3.67] | 2.49 | 0.010 | criterion met |
| v_plan / plain | 3000 | 23.1 | 23.2 | +0.17 | [-0.99, +1.32] | domain (k=20) | [-0.83, +1.27] | 1.15 | 0.000 | criterion met |
| v_plan / steered | 3000 | 23.7 | 24.8 | +1.10 | [-0.38, +2.58] | domain (k=20) | [-0.20, +2.53] | 1.48 | 0.000 | criterion met |
| sim / plain | 300 | 5.7 | 6.3 | +0.67 | [-1.36, +2.70] | domain (k=20) | [-1.33, +2.67] | 2.03 | 0.001 | criterion met (floor: low information) |
| sim / steered | 300 | 1.7 | 2.7 | +1.00 | [-0.73, +2.73] | domain (k=20) | [+0.00, +3.00] | 1.73 | 0.000 | criterion met (floor: low information) |
| pooled (9,120) | 9120 | 26.5 | 26.9 | +0.34 | [-0.41, +1.09] | domain (k=20) | [-0.30, +1.07] | 0.75 | 0.000 | criterion met |

Task x arm cells meeting the criterion: 10/10; pooled: criterion met.

Individual trials whose outcome differs between the two runs: 381/9120 (4.2%).

### 0.22.0 run 2 minus 0.22.0 run 1 - same version twice (run-to-run noise)

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| solve / plain | 300 | 9.3 | 11.0 | +1.67 | [-2.24, +5.58] | domain (k=20) | [-1.33, +5.67] | 3.91 | 0.078 | criterion not met (unresolved) |
| solve / steered | 300 | 13.3 | 16.3 | +3.00 | [+0.71, +5.29] | domain (k=20) | [+1.00, +5.33] | 2.29 | 0.073 | criterion not met (unresolved) |
| v_dom / plain | 360 | 88.6 | 88.6 | +0.00 | [-2.51, +2.51] | domain (k=20) | [-2.50, +2.22] | 2.51 | 0.001 | criterion met |
| v_dom / steered | 360 | 90.6 | 90.6 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (ceiling: low information) |
| v_prob / plain | 600 | 27.5 | 27.3 | -0.17 | [-1.76, +1.42] | domain (k=20) | [-1.67, +1.33] | 1.59 | 0.000 | criterion met |
| v_prob / steered | 600 | 20.7 | 17.2 | -3.50 | [-5.69, -1.31] | domain (k=20) | [-5.67, -1.67] | 2.19 | 0.126 | criterion not met (unresolved) |
| v_plan / plain | 3000 | 22.0 | 23.1 | +1.07 | [+0.25, +1.88] | problem (k=100) | [+0.40, +1.80] | 0.81 | 0.000 | criterion met |
| v_plan / steered | 3000 | 24.1 | 23.7 | -0.37 | [-1.26, +0.53] | problem (k=100) | [-1.17, +0.43] | 0.90 | 0.000 | criterion met |
| sim / plain | 300 | 6.7 | 5.7 | -1.00 | [-2.92, +0.92] | domain (k=20) | [-2.68, +0.67] | 1.92 | 0.001 | criterion met (floor: low information) |
| sim / steered | 300 | 2.3 | 1.7 | -0.67 | [-1.82, +0.49] | domain (k=20) | [-2.00, +0.00] | 1.15 | 0.000 | criterion met (floor: low information) |
| pooled (9,120) | 9120 | 26.4 | 26.5 | +0.09 | [-0.39, +0.56] | domain (k=20) | [-0.34, +0.54] | 0.48 | 0.000 | criterion met |

Task x arm cells meeting the criterion: 7/10; pooled: criterion met.

Individual trials whose outcome differs between the two runs: 366/9120 (4.0%).

