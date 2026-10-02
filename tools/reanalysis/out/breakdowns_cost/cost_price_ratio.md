# Cost-of-pass under output:input price ratios

## A. Open roster (sweep5v2-live, think off)

### A0. Token mix per trial (pooled over the three models)

| task | arm | n | input tok/trial | output tok/trial | input:output | turns/trial |
|---|---|---|---|---|---|---|
| solve | no-tools | 900 | 1,185 | 3,303 | 0.36:1 | 1.00 |
| solve | tools-plain | 900 | 15,890 | 2,816 | 5.64:1 | 2.69 |
| solve | tools-steered | 900 | 15,651 | 2,457 | 6.37:1 | 2.68 |
| validate_domain | no-tools | 1080 | 803 | 1,176 | 0.68:1 | 1.00 |
| validate_domain | tools-plain | 1080 | 8,980 | 792 | 11.34:1 | 2.02 |
| validate_domain | tools-steered | 1080 | 8,930 | 757 | 11.79:1 | 2.01 |
| validate_problem | no-tools | 1800 | 1,160 | 871 | 1.33:1 | 1.00 |
| validate_problem | tools-plain | 1800 | 10,847 | 1,351 | 8.03:1 | 2.12 |
| validate_problem | tools-steered | 1800 | 10,669 | 1,268 | 8.42:1 | 2.10 |
| validate_plan | no-tools | 9000 | 1,371 | 1,636 | 0.84:1 | 1.00 |
| validate_plan | tools-plain | 9000 | 9,677 | 1,419 | 6.82:1 | 1.74 |
| validate_plan | tools-steered | 9000 | 11,671 | 1,425 | 8.19:1 | 2.04 |
| simulate | no-tools | 900 | 1,454 | 3,035 | 0.48:1 | 1.00 |
| simulate | tools-plain | 900 | 14,495 | 2,017 | 7.18:1 | 2.05 |
| simulate | tools-steered | 900 | 16,093 | 1,819 | 8.85:1 | 2.21 |

### A. tools-steered / no-tools (the paper's pairing): multiplier on the DELIVERED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| pooled 3 models | solve | 2.12x to 5.38x | 0.12x to 0.30x | 0.65x to 1.64x | 0.33x to 0.84x | 0.28x to 0.72x | 0.25x to 0.64x |
| pooled 3 models | validate_domain | 6.39x to 6.61x | 0.37x to 0.38x | 2.81x to 2.91x | 1.48x to 1.54x | 1.25x to 1.29x | 1.09x to 1.13x |
| pooled 3 models | validate_problem | 6.91x to 7.61x | 1.09x to 1.20x | 4.41x to 4.86x | 2.88x to 3.17x | 2.54x to 2.80x | 2.32x to 2.55x |
| pooled 3 models | validate_plan | 8.03x to 10.08x | 0.82x to 1.03x | 4.11x to 5.16x | 2.40x to 3.01x | 2.07x to 2.60x | 1.86x to 2.33x |
| pooled 3 models | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Gemma 26B a4b | solve | 1.42x to 3.56x | 0.10x to 0.24x | 0.51x to 1.29x | 0.27x to 0.68x | 0.23x to 0.59x | 0.21x to 0.52x |
| Gemma 26B a4b | validate_domain | 7.92x to 8.23x | 1.01x to 1.05x | 4.93x to 5.12x | 3.11x to 3.23x | 2.72x to 2.82x | 2.45x to 2.54x |
| Gemma 26B a4b | validate_problem | 6.10x to 6.66x | 1.25x to 1.37x | 4.28x to 4.67x | 2.99x to 3.26x | 2.68x to 2.92x | 2.47x to 2.69x |
| Gemma 26B a4b | validate_plan | 6.72x to 11.52x | 1.15x to 1.98x | 4.23x to 7.25x | 2.78x to 4.76x | 2.47x to 4.23x | 2.26x to 3.87x |
| Gemma 26B a4b | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.5 9B | solve | 2.38x to 5.62x | 0.10x to 0.23x | 0.64x to 1.52x | 0.31x to 0.74x | 0.26x to 0.62x | 0.23x to 0.55x |
| Qwen3.5 9B | validate_domain | 2.98x | 0.12x | 1.08x | 0.53x | 0.44x | 0.38x |
| Qwen3.5 9B | validate_problem | 7.38x to 7.66x | 1.09x to 1.13x | 4.55x to 4.72x | 2.91x to 3.02x | 2.56x to 2.66x | 2.32x to 2.41x |
| Qwen3.5 9B | validate_plan | 8.14x to 8.33x | 0.71x to 0.73x | 3.93x to 4.02x | 2.22x to 2.27x | 1.91x to 1.95x | 1.70x to 1.74x |
| Qwen3.5 9B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.6 35B | solve | 2.77x to 7.93x | 0.17x to 0.50x | 0.82x to 2.35x | 0.43x to 1.24x | 0.37x to 1.07x | 0.34x to 0.96x |
| Qwen3.6 35B | validate_domain | 7.97x to 8.51x | 0.38x to 0.41x | 3.22x to 3.45x | 1.65x to 1.76x | 1.37x to 1.47x | 1.20x to 1.28x |
| Qwen3.6 35B | validate_problem | 7.22x to 8.52x | 0.97x to 1.14x | 4.37x to 5.15x | 2.75x to 3.24x | 2.40x to 2.84x | 2.17x to 2.56x |
| Qwen3.6 35B | validate_plan | 9.32x to 11.06x | 0.73x to 0.86x | 4.20x to 4.98x | 2.31x to 2.74x | 1.97x to 2.34x | 1.75x to 2.08x |
| Qwen3.6 35B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |

### A. tools-steered / no-tools (the paper's pairing): multiplier on the TOOL-VERIFIED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| pooled 3 models | solve | 1.26x | 0.07x | 0.38x | 0.20x | 0.17x | 0.15x |
| pooled 3 models | validate_domain | 6.39x | 0.37x | 2.81x | 1.48x | 1.25x | 1.09x |
| pooled 3 models | validate_problem | 6.92x | 1.09x | 4.42x | 2.88x | 2.55x | 2.32x |
| pooled 3 models | validate_plan | 7.64x | 0.78x | 3.91x | 2.28x | 1.97x | 1.77x |
| pooled 3 models | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Gemma 26B a4b | solve | 0.85x | 0.06x | 0.31x | 0.16x | 0.14x | 0.13x |
| Gemma 26B a4b | validate_domain | 7.92x | 1.01x | 4.93x | 3.11x | 2.72x | 2.45x |
| Gemma 26B a4b | validate_problem | 6.10x | 1.25x | 4.28x | 2.99x | 2.68x | 2.47x |
| Gemma 26B a4b | validate_plan | 6.91x | 1.19x | 4.35x | 2.85x | 2.53x | 2.32x |
| Gemma 26B a4b | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.5 9B | solve | 1.56x | 0.06x | 0.42x | 0.20x | 0.17x | 0.15x |
| Qwen3.5 9B | validate_domain | 2.98x | 0.12x | 1.08x | 0.53x | 0.44x | 0.38x |
| Qwen3.5 9B | validate_problem | 7.45x | 1.10x | 4.59x | 2.94x | 2.58x | 2.35x |
| Qwen3.5 9B | validate_plan | 7.54x | 0.66x | 3.64x | 2.06x | 1.76x | 1.57x |
| Qwen3.5 9B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.6 35B | solve | 1.44x | 0.09x | 0.43x | 0.22x | 0.19x | 0.17x |
| Qwen3.6 35B | validate_domain | 7.97x | 0.38x | 3.22x | 1.65x | 1.37x | 1.20x |
| Qwen3.6 35B | validate_problem | 7.19x | 0.96x | 4.35x | 2.74x | 2.39x | 2.16x |
| Qwen3.6 35B | validate_plan | 8.45x | 0.66x | 3.81x | 2.10x | 1.79x | 1.59x |
| Qwen3.6 35B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |

### A. tools-plain / no-tools: multiplier on the DELIVERED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| pooled 3 models | solve | 2.51x to 7.00x | 0.16x to 0.45x | 0.78x to 2.18x | 0.41x to 1.15x | 0.35x to 0.98x | 0.32x to 0.88x |
| pooled 3 models | validate_domain | 6.44x to 6.72x | 0.39x to 0.40x | 2.84x to 2.96x | 1.51x to 1.57x | 1.27x to 1.32x | 1.11x to 1.16x |
| pooled 3 models | validate_problem | 6.90x to 8.05x | 1.14x to 1.34x | 4.43x to 5.17x | 2.91x to 3.40x | 2.58x to 3.01x | 2.36x to 2.75x |
| pooled 3 models | validate_plan | 6.58x to 12.82x | 0.81x to 1.58x | 3.44x to 6.70x | 2.07x to 4.03x | 1.81x to 3.52x | 1.64x to 3.19x |
| pooled 3 models | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Gemma 26B a4b | solve | 2.78x to 6.85x | 0.19x to 0.47x | 1.01x to 2.48x | 0.54x to 1.32x | 0.46x to 1.13x | 0.41x to 1.01x |
| Gemma 26B a4b | validate_domain | 7.95x to 8.35x | 1.02x to 1.07x | 4.95x to 5.20x | 3.13x to 3.28x | 2.73x to 2.87x | 2.46x to 2.58x |
| Gemma 26B a4b | validate_problem | 6.20x to 7.34x | 1.29x to 1.52x | 4.36x to 5.16x | 3.04x to 3.60x | 2.73x to 3.24x | 2.52x to 2.98x |
| Gemma 26B a4b | validate_plan | 3.33x to 50.48x | 0.95x to 14.37x | 2.26x to 34.31x | 1.64x to 24.89x | 1.51x to 22.88x | 1.42x to 21.52x |
| Gemma 26B a4b | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.5 9B | solve | 2.84x to 6.41x | 0.12x to 0.27x | 0.77x to 1.73x | 0.38x to 0.85x | 0.32x to 0.71x | 0.28x to 0.63x |
| Qwen3.5 9B | validate_domain | 2.97x to 2.98x | 0.12x | 1.07x | 0.53x | 0.44x | 0.38x |
| Qwen3.5 9B | validate_problem | 7.09x to 7.34x | 0.98x to 1.02x | 4.34x to 4.49x | 2.75x to 2.84x | 2.41x to 2.49x | 2.18x to 2.26x |
| Qwen3.5 9B | validate_plan | 8.43x to 9.10x | 0.76x to 0.82x | 4.08x to 4.41x | 2.32x to 2.50x | 1.99x to 2.15x | 1.78x to 1.92x |
| Qwen3.5 9B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.6 35B | solve | 2.06x to 8.72x | 0.18x to 0.77x | 0.65x to 2.75x | 0.37x to 1.56x | 0.32x to 1.38x | 0.30x to 1.26x |
| Qwen3.6 35B | validate_domain | 8.16x to 8.80x | 0.44x to 0.47x | 3.33x to 3.59x | 1.72x to 1.86x | 1.44x to 1.56x | 1.26x to 1.36x |
| Qwen3.6 35B | validate_problem | 7.36x to 9.65x | 1.20x to 1.57x | 4.55x to 5.96x | 2.95x to 3.87x | 2.61x to 3.43x | 2.39x to 3.13x |
| Qwen3.6 35B | validate_plan | 8.37x to 13.73x | 0.79x to 1.29x | 3.85x to 6.31x | 2.18x to 3.58x | 1.88x to 3.09x | 1.69x to 2.77x |
| Qwen3.6 35B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |

### A. tools-plain / no-tools: multiplier on the TOOL-VERIFIED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| pooled 3 models | solve | 1.42x | 0.09x | 0.44x | 0.23x | 0.20x | 0.18x |
| pooled 3 models | validate_domain | 6.46x | 0.39x | 2.85x | 1.51x | 1.27x | 1.12x |
| pooled 3 models | validate_problem | 6.93x | 1.15x | 4.45x | 2.93x | 2.59x | 2.37x |
| pooled 3 models | validate_plan | 9.31x | 1.14x | 4.87x | 2.93x | 2.56x | 2.32x |
| pooled 3 models | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Gemma 26B a4b | solve | 0.99x | 0.07x | 0.36x | 0.19x | 0.16x | 0.15x |
| Gemma 26B a4b | validate_domain | 7.99x | 1.02x | 4.98x | 3.14x | 2.75x | 2.47x |
| Gemma 26B a4b | validate_problem | 6.21x | 1.29x | 4.37x | 3.05x | 2.74x | 2.52x |
| Gemma 26B a4b | validate_plan | 16.12x | 4.59x | 10.96x | 7.95x | 7.31x | 6.87x |
| Gemma 26B a4b | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.5 9B | solve | 1.68x | 0.07x | 0.45x | 0.22x | 0.19x | 0.16x |
| Qwen3.5 9B | validate_domain | 2.97x | 0.12x | 1.07x | 0.53x | 0.44x | 0.38x |
| Qwen3.5 9B | validate_problem | 7.10x | 0.99x | 4.35x | 2.76x | 2.42x | 2.19x |
| Qwen3.5 9B | validate_plan | 7.89x | 0.71x | 3.82x | 2.17x | 1.86x | 1.66x |
| Qwen3.5 9B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.6 35B | solve | 1.75x | 0.15x | 0.55x | 0.31x | 0.28x | 0.25x |
| Qwen3.6 35B | validate_domain | 8.18x | 0.44x | 3.34x | 1.73x | 1.45x | 1.27x |
| Qwen3.6 35B | validate_problem | 7.44x | 1.21x | 4.60x | 2.98x | 2.64x | 2.41x |
| Qwen3.6 35B | validate_plan | 9.19x | 0.86x | 4.23x | 2.40x | 2.07x | 1.86x |
| Qwen3.6 35B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |

### A. Break-even output:input price ratio (the tool is cheaper per success above it)

Delivered, best case = every censored tool-arm row counted as a success; delivered, worst case = none counted (the tool pays for certain only above the worst-case ratio).

| tool arm | cell | task | delivered, best case | delivered, worst case | tool-verified |
|---|---|---|---|---|---|
| tools-steered | pooled 3 models | solve | 0.5:1 | 2.2:1 | 0.1:1 |
| tools-steered | pooled 3 models | validate_domain | 5.8:1 | 6.2:1 | 5.8:1 |
| tools-steered | pooled 3 models | validate_problem | never | never | never |
| tools-steered | pooled 3 models | validate_plan | 33.0:1 | never | 25.5:1 |
| tools-steered | pooled 3 models | simulate | not identified | not identified | not identified |
| tools-steered | Gemma 26B a4b | solve | 0.2:1 | 1.6:1 | any (cheaper on input alone) |
| tools-steered | Gemma 26B a4b | validate_domain | never | never | never |
| tools-steered | Gemma 26B a4b | validate_problem | never | never | never |
| tools-steered | Gemma 26B a4b | validate_plan | never | never | never |
| tools-steered | Gemma 26B a4b | simulate | not identified | not identified | not identified |
| tools-steered | Qwen3.5 9B | solve | 0.5:1 | 1.9:1 | 0.2:1 |
| tools-steered | Qwen3.5 9B | validate_domain | 1.1:1 | 1.1:1 | 1.1:1 |
| tools-steered | Qwen3.5 9B | validate_problem | never | never | never |
| tools-steered | Qwen3.5 9B | validate_plan | 19.0:1 | 20.7:1 | 14.7:1 |
| tools-steered | Qwen3.5 9B | simulate | not identified | not identified | not identified |
| tools-steered | Qwen3.6 35B | solve | 0.7:1 | 4.6:1 | 0.2:1 |
| tools-steered | Qwen3.6 35B | validate_domain | 6.8:1 | 7.6:1 | 6.8:1 |
| tools-steered | Qwen3.6 35B | validate_problem | 226.8:1 | never | 205.1:1 |
| tools-steered | Qwen3.6 35B | validate_plan | 20.8:1 | 50.3:1 | 14.9:1 |
| tools-steered | Qwen3.6 35B | simulate | not identified | not identified | not identified |
| tools-plain | pooled 3 models | solve | 0.6:1 | 3.9:1 | 0.2:1 |
| tools-plain | pooled 3 models | validate_domain | 6.1:1 | 6.5:1 | 6.1:1 |
| tools-plain | pooled 3 models | validate_problem | never | never | never |
| tools-plain | pooled 3 models | validate_plan | 24.5:1 | never | never |
| tools-plain | pooled 3 models | simulate | not identified | not identified | not identified |
| tools-plain | Gemma 26B a4b | solve | 1.0:1 | 5.1:1 | any (cheaper on input alone) |
| tools-plain | Gemma 26B a4b | validate_domain | never | never | never |
| tools-plain | Gemma 26B a4b | validate_problem | never | never | never |
| tools-plain | Gemma 26B a4b | validate_plan | 55.1:1 | never | never |
| tools-plain | Gemma 26B a4b | simulate | not identified | not identified | not identified |
| tools-plain | Qwen3.5 9B | solve | 0.7:1 | 2.3:1 | 0.2:1 |
| tools-plain | Qwen3.5 9B | validate_domain | 1.1:1 | 1.1:1 | 1.1:1 |
| tools-plain | Qwen3.5 9B | validate_problem | 456.2:1 | never | 511.1:1 |
| tools-plain | Qwen3.5 9B | validate_plan | 23.8:1 | 34.9:1 | 18.3:1 |
| tools-plain | Qwen3.5 9B | simulate | not identified | not identified | not identified |
| tools-plain | Qwen3.6 35B | solve | 0.4:1 | 11.0:1 | 0.3:1 |
| tools-plain | Qwen3.6 35B | validate_domain | 7.6:1 | 8.9:1 | 7.7:1 |
| tools-plain | Qwen3.6 35B | validate_problem | never | never | never |
| tools-plain | Qwen3.6 35B | validate_plan | 23.2:1 | never | 40.4:1 |
| tools-plain | Qwen3.6 35B | simulate | not identified | not identified | not identified |

### A. solve by track, pooled 3 models: multiplier on the DELIVERED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| tools-steered, classical | solve | 1.19x to 3.16x | 0.06x to 0.17x | 0.34x to 0.90x | 0.17x to 0.46x | 0.15x to 0.39x | 0.13x to 0.35x |
| tools-steered, numeric | solve | 3.74x to 8.81x | 0.23x to 0.53x | 1.24x to 2.92x | 0.65x to 1.52x | 0.55x to 1.29x | 0.49x to 1.15x |
| tools-plain, classical | solve | 1.35x to 3.88x | 0.09x to 0.25x | 0.39x to 1.13x | 0.21x to 0.60x | 0.18x to 0.52x | 0.16x to 0.47x |
| tools-plain, numeric | solve | 4.70x to 12.49x | 0.31x to 0.82x | 1.58x to 4.19x | 0.83x to 2.21x | 0.71x to 1.90x | 0.64x to 1.70x |

### A. solve by track, pooled 3 models: multiplier on the TOOL-VERIFIED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| tools-steered, classical | solve | 0.86x | 0.05x | 0.24x | 0.13x | 0.11x | 0.10x |
| tools-steered, numeric | solve | 1.71x | 0.10x | 0.57x | 0.30x | 0.25x | 0.22x |
| tools-plain, classical | solve | 0.99x | 0.06x | 0.29x | 0.15x | 0.13x | 0.12x |
| tools-plain, numeric | solve | 1.90x | 0.12x | 0.64x | 0.34x | 0.29x | 0.26x |

## B. Frontier (canonical corpus, wording v11 on both arms)

### B0. Token mix per trial

| tier | task | tools input raw | tools output | tools input:output | tools input cache-billed | no-tools input | no-tools output | no-tools input:output |
|---|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 15,503 | 2,200 | 7.0:1 | 10,187 | 1,457 | 290 | 5.03:1 |
| Sonnet 4.6 | validate_domain | 11,022 | 1,103 | 10.0:1 | 3,478 | 861 | 318 | 2.70:1 |
| Sonnet 4.6 | validate_problem | 12,205 | 1,452 | 8.4:1 | 9,004 | 1,266 | 170 | 7.45:1 |
| Sonnet 4.6 | validate_plan | 14,118 | 1,742 | 8.1:1 | 7,304 | 1,528 | 852 | 1.79:1 |
| Sonnet 4.6 | simulate | 46,439 | 5,355 | 8.7:1 | 51,094 | 1,680 | 3,522 | 0.48:1 |
| Haiku 4.5 | solve | 40,775 | 5,320 | 7.7:1 | 18,973 | 1,456 | 304 | 4.79:1 |
| Haiku 4.5 | validate_domain | 11,133 | 930 | 12.0:1 | 4,367 | 860 | 483 | 1.78:1 |
| Haiku 4.5 | validate_problem | 12,438 | 1,356 | 9.2:1 | 9,104 | 1,265 | 589 | 2.15:1 |
| Haiku 4.5 | validate_plan | 14,616 | 1,766 | 8.3:1 | 7,495 | 1,527 | 1,101 | 1.39:1 |
| Haiku 4.5 | simulate | 42,238 | 4,417 | 9.6:1 | 45,183 | 1,679 | 3,575 | 0.47:1 |

### B. raw: multiplier on the DELIVERED score

raw token count (the paper's accounting); at 5:1 this is list price with caching ignored.

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 3.25x | 2.32x | 3.09x | 2.90x | 2.84x | 2.78x |
| Sonnet 4.6 | validate_domain | 12.47x | 3.37x | 10.01x | 7.69x | 7.04x | 6.57x |
| Sonnet 4.6 | validate_problem | 8.51x | 7.55x | 8.40x | 8.23x | 8.17x | 8.12x |
| Sonnet 4.6 | validate_plan | 8.97x | 1.98x | 6.47x | 4.60x | 4.15x | 3.83x |
| Sonnet 4.6 | simulate | 15.16x to 29.89x | 0.83x to 1.64x | 5.46x to 10.77x | 2.80x to 5.52x | 2.36x to 4.65x | 2.08x to 4.11x |
| Haiku 4.5 | solve | 6.49x | 4.06x | 6.07x | 5.55x | 5.38x | 5.25x |
| Haiku 4.5 | validate_domain | 11.52x | 1.71x | 7.99x | 5.37x | 4.73x | 4.29x |
| Haiku 4.5 | validate_problem | 7.44x | 1.74x | 5.63x | 4.12x | 3.73x | 3.45x |
| Haiku 4.5 | validate_plan | 8.87x | 1.49x | 5.77x | 3.82x | 3.39x | 3.09x |
| Haiku 4.5 | simulate | 14.93x to 32.89x | 0.73x to 1.62x | 5.27x to 11.61x | 2.66x to 5.85x | 2.23x to 4.90x | 1.95x to 4.30x |

### B. raw: multiplier on the TOOL-VERIFIED score

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 3.09x | 2.20x | 2.94x | 2.76x | 2.69x | 2.65x |
| Sonnet 4.6 | validate_domain | 12.47x | 3.37x | 10.01x | 7.69x | 7.04x | 6.57x |
| Sonnet 4.6 | validate_problem | 8.51x | 7.55x | 8.40x | 8.23x | 8.17x | 8.12x |
| Sonnet 4.6 | validate_plan | 8.98x | 1.99x | 6.48x | 4.60x | 4.15x | 3.83x |
| Sonnet 4.6 | simulate | 10.33x | 0.57x | 3.72x | 1.91x | 1.61x | 1.42x |
| Haiku 4.5 | solve | 6.16x | 3.85x | 5.76x | 5.27x | 5.11x | 4.98x |
| Haiku 4.5 | validate_domain | 11.52x | 1.71x | 7.99x | 5.37x | 4.73x | 4.29x |
| Haiku 4.5 | validate_problem | 7.44x | 1.74x | 5.63x | 4.12x | 3.73x | 3.45x |
| Haiku 4.5 | validate_plan | 8.86x | 1.48x | 5.77x | 3.81x | 3.38x | 3.08x |
| Haiku 4.5 | simulate | 10.89x | 0.53x | 3.84x | 1.94x | 1.62x | 1.42x |

### B. cache-billed: multiplier on the DELIVERED score

tools input priced with the cache multipliers; at 5:1 this is the actual list price, both arms at list.

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 2.13x | 2.32x | 2.17x | 2.20x | 2.22x | 2.23x |
| Sonnet 4.6 | validate_domain | 3.93x | 3.37x | 3.78x | 3.64x | 3.60x | 3.57x |
| Sonnet 4.6 | validate_problem | 6.28x | 7.55x | 6.43x | 6.64x | 6.72x | 6.79x |
| Sonnet 4.6 | validate_plan | 4.64x | 1.98x | 3.69x | 2.98x | 2.81x | 2.69x |
| Sonnet 4.6 | simulate | 16.67x to 32.89x | 0.83x to 1.64x | 5.95x to 11.74x | 3.01x to 5.93x | 2.52x to 4.97x | 2.21x to 4.37x |
| Haiku 4.5 | solve | 3.02x | 4.06x | 3.20x | 3.42x | 3.49x | 3.55x |
| Haiku 4.5 | validate_domain | 4.52x | 1.71x | 3.51x | 2.76x | 2.58x | 2.45x |
| Haiku 4.5 | validate_problem | 5.45x | 1.74x | 4.27x | 3.29x | 3.04x | 2.86x |
| Haiku 4.5 | validate_plan | 4.55x | 1.49x | 3.26x | 2.45x | 2.27x | 2.15x |
| Haiku 4.5 | simulate | 15.97x to 35.18x | 0.73x to 1.62x | 5.60x to 12.34x | 2.80x to 6.16x | 2.34x to 5.14x | 2.04x to 4.50x |

### B. cache-billed: multiplier on the TOOL-VERIFIED score

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 2.03x | 2.20x | 2.06x | 2.09x | 2.11x | 2.11x |
| Sonnet 4.6 | validate_domain | 3.93x | 3.37x | 3.78x | 3.64x | 3.60x | 3.57x |
| Sonnet 4.6 | validate_problem | 6.28x | 7.55x | 6.43x | 6.64x | 6.72x | 6.79x |
| Sonnet 4.6 | validate_plan | 4.65x | 1.99x | 3.69x | 2.98x | 2.81x | 2.69x |
| Sonnet 4.6 | simulate | 11.36x | 0.57x | 4.06x | 2.05x | 1.72x | 1.51x |
| Haiku 4.5 | solve | 2.87x | 3.85x | 3.04x | 3.25x | 3.32x | 3.37x |
| Haiku 4.5 | validate_domain | 4.52x | 1.71x | 3.51x | 2.76x | 2.58x | 2.45x |
| Haiku 4.5 | validate_problem | 5.45x | 1.74x | 4.27x | 3.29x | 3.04x | 2.86x |
| Haiku 4.5 | validate_plan | 4.54x | 1.48x | 3.26x | 2.45x | 2.27x | 2.15x |
| Haiku 4.5 | simulate | 11.65x | 0.53x | 4.09x | 2.04x | 1.70x | 1.49x |

### B. as-billed: multiplier on the DELIVERED score

as cache-billed, and the no-tools arm at the Batch API price (half list); at 5:1 this is what the two arms were actually charged.

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 4.27x | 4.64x | 4.33x | 4.41x | 4.43x | 4.45x |
| Sonnet 4.6 | validate_domain | 7.87x | 6.75x | 7.57x | 7.28x | 7.20x | 7.14x |
| Sonnet 4.6 | validate_problem | 12.56x | 15.09x | 12.86x | 13.29x | 13.44x | 13.58x |
| Sonnet 4.6 | validate_plan | 9.28x | 3.97x | 7.38x | 5.96x | 5.61x | 5.37x |
| Sonnet 4.6 | simulate | 33.35x to 65.78x | 1.67x to 3.29x | 11.90x to 23.47x | 6.01x to 11.86x | 5.04x to 9.95x | 4.43x to 8.73x |
| Haiku 4.5 | solve | 6.04x | 8.11x | 6.40x | 6.84x | 6.98x | 7.10x |
| Haiku 4.5 | validate_domain | 9.04x | 3.42x | 7.02x | 5.52x | 5.15x | 4.90x |
| Haiku 4.5 | validate_problem | 10.89x | 3.49x | 8.54x | 6.58x | 6.07x | 5.71x |
| Haiku 4.5 | validate_plan | 9.09x | 2.97x | 6.53x | 4.91x | 4.55x | 4.30x |
| Haiku 4.5 | simulate | 31.95x to 70.37x | 1.47x to 3.23x | 11.21x to 24.69x | 5.59x to 12.32x | 4.67x to 10.29x | 4.08x to 9.00x |

### B. as-billed: multiplier on the TOOL-VERIFIED score

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 4.06x | 4.40x | 4.11x | 4.19x | 4.21x | 4.23x |
| Sonnet 4.6 | validate_domain | 7.87x | 6.75x | 7.57x | 7.28x | 7.20x | 7.14x |
| Sonnet 4.6 | validate_problem | 12.56x | 15.09x | 12.86x | 13.29x | 13.44x | 13.58x |
| Sonnet 4.6 | validate_plan | 9.29x | 3.97x | 7.39x | 5.96x | 5.62x | 5.38x |
| Sonnet 4.6 | simulate | 22.73x | 1.14x | 8.11x | 4.10x | 3.44x | 3.02x |
| Haiku 4.5 | solve | 5.74x | 7.71x | 6.08x | 6.49x | 6.63x | 6.74x |
| Haiku 4.5 | validate_domain | 9.04x | 3.42x | 7.02x | 5.52x | 5.15x | 4.90x |
| Haiku 4.5 | validate_problem | 10.89x | 3.49x | 8.54x | 6.58x | 6.07x | 5.71x |
| Haiku 4.5 | validate_plan | 9.09x | 2.97x | 6.52x | 4.90x | 4.54x | 4.30x |
| Haiku 4.5 | simulate | 23.30x | 1.07x | 8.17x | 4.08x | 3.41x | 2.98x |

### B. Break-even output:input price ratio, delivered score

| tier | task | raw, best case | raw, worst case | cache-billed, worst case |
|---|---|---|---|---|
| Sonnet 4.6 | solve | never | never | never |
| Sonnet 4.6 | validate_domain | never | never | never |
| Sonnet 4.6 | validate_problem | never | never | never |
| Sonnet 4.6 | validate_plan | never | never | never |
| Sonnet 4.6 | simulate | 40.6:1 | never | never |
| Haiku 4.5 | solve | never | never | never |
| Haiku 4.5 | validate_domain | never | never | never |
| Haiku 4.5 | validate_problem | never | never | never |
| Haiku 4.5 | validate_plan | never | never | never |
| Haiku 4.5 | simulate | 24.6:1 | never | never |

### B. Dollars per delivered pass at list prices (tools/frontier_runner.py:71-74)

| tier | task | tools, list, caching ignored | tools, list, cache-billed | no-tools, list | no-tools, Batch (list / 2) |
|---|---|---|---|---|---|
| Sonnet 4.6 | solve | $0.084 | $0.067 | $0.030 | $0.015 |
| Sonnet 4.6 | validate_domain | $0.052 | $0.028 | $0.008 | $0.004 |
| Sonnet 4.6 | validate_problem | $0.060 | $0.050 | $0.007 | $0.004 |
| Sonnet 4.6 | validate_plan | $0.068 | $0.048 | $0.018 | $0.009 |
| Sonnet 4.6 | simulate | $0.354 to $0.448 | $0.377 to $0.477 | $0.109 to $0.170 | $0.055 to $0.085 |
| Haiku 4.5 | solve | $0.071 | $0.048 | $0.014 | $0.007 |
| Haiku 4.5 | validate_domain | $0.016 | $0.009 | $0.004 | $0.002 |
| Haiku 4.5 | validate_problem | $0.020 | $0.016 | $0.006 | $0.003 |
| Haiku 4.5 | validate_plan | $0.024 | $0.017 | $0.008 | $0.004 |
| Haiku 4.5 | simulate | $0.101 to $0.124 | $0.105 to $0.129 | $0.029 to $0.051 | $0.014 to $0.026 |

