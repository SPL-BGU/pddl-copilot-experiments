# Identical prompts and run-to-run agreement, sweep5v2-live, think off

Problems whose five valid-plan files are byte-identical: 99 of 100 (101 distinct valid-plan files of 500; 500 distinct invalid-plan files of 500).

Distinct prompts per arm (three wordings): validate_domain 60 valid + 60 invalid = 120 of 360 trials; validate_plan 303 valid + 1500 invalid = 1803 of 3000 trials.

| model | arm | identical-prompt set | groups of 5 | groups not unanimous | share not unanimous | trials disagreeing with their group's majority |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | validate_domain, valid domain x5 | 60 | 13 | 21.7% | 19/300 (6.3%) |
| Gemma 26B a4b | no-tools | validate_plan, valid plan x5 | 297 | 44 | 14.8% | 63/1485 (4.2%) |
| Gemma 26B a4b | tools-plain | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Gemma 26B a4b | tools-plain | validate_plan, valid plan x5 | 297 | 8 | 2.7% | 12/1485 (0.8%) |
| Gemma 26B a4b | tools-steered | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Gemma 26B a4b | tools-steered | validate_plan, valid plan x5 | 297 | 8 | 2.7% | 12/1485 (0.8%) |
| Qwen3.5 9B | no-tools | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.5 9B | no-tools | validate_plan, valid plan x5 | 297 | 46 | 15.5% | 65/1485 (4.4%) |
| Qwen3.5 9B | tools-plain | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.5 9B | tools-plain | validate_plan, valid plan x5 | 297 | 11 | 3.7% | 17/1485 (1.1%) |
| Qwen3.5 9B | tools-steered | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.5 9B | tools-steered | validate_plan, valid plan x5 | 297 | 7 | 2.4% | 10/1485 (0.7%) |
| Qwen3.6 35B | no-tools | validate_domain, valid domain x5 | 60 | 28 | 46.7% | 41/300 (13.7%) |
| Qwen3.6 35B | no-tools | validate_plan, valid plan x5 | 297 | 37 | 12.5% | 50/1485 (3.4%) |
| Qwen3.6 35B | tools-plain | validate_domain, valid domain x5 | 60 | 1 | 1.7% | 2/300 (0.7%) |
| Qwen3.6 35B | tools-plain | validate_plan, valid plan x5 | 297 | 41 | 13.8% | 59/1485 (4.0%) |
| Qwen3.6 35B | tools-steered | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.6 35B | tools-steered | validate_plan, valid plan x5 | 297 | 7 | 2.4% | 8/1485 (0.5%) |

