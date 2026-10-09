# Driver flags, sweep6-live, think off (harness score)

| model | task | arm | pooled % | lowest domain | highest domain | domains at 0 / at 100 | leave-one-out range | top domain of the rarer outcome |
|---|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | solve | tools-plain | 97.3 | depot=60 | barman=100 | 0 / 18 | 97.2 (drop barman) .. 99.3 (drop depot) | depot: 75.0% of 8 failures |
| Gemma 26B a4b | solve | tools-steered | 96.0 | depot=40 | barman=100 | 0 / 17 | 95.8 (drop barman) .. 98.9 (drop depot) | depot: 75.0% of 12 failures |
| Gemma 26B a4b | validate_domain | no-tools | 80.6 | block-grouping=17 | barman=100 | 0 / 9 | 79.5 (drop barman) .. 83.9 (drop block-grouping) | block-grouping: 21.4% of 70 failures |
| Gemma 26B a4b | validate_problem | tools-plain | 98.3 | depots=87 | barman=100 | 0 / 17 | 98.2 (drop barman) .. 98.9 (drop depots) | depots: 40.0% of 10 failures |
| Gemma 26B a4b | validate_problem | tools-steered | 98.0 | depots=80 | barman=100 | 0 / 16 | 97.9 (drop barman) .. 98.9 (drop depots) | depots: 50.0% of 12 failures |
| Gemma 26B a4b | validate_plan | tools-steered | 85.8 | barman=12 | blocksworld=100 | 0 / 8 | 85.0 (drop blocksworld) .. 89.6 (drop barman) | barman: 30.9% of 427 failures |
| Gemma 26B a4b | simulate | tools-plain | 85.7 | depots=0 | blocksworld=100 | 1 / 12 | 84.9 (drop blocksworld) .. 90.2 (drop depots) | depots: 34.9% of 43 failures |
| Gemma 26B a4b | simulate | tools-steered | 87.3 | depots=0 | barman=100 | 1 / 15 | 86.7 (drop barman) .. 91.9 (drop depots) | depots: 39.5% of 38 failures |
| Qwen3.5 9B | solve | tools-plain | 97.0 | drone=47 | barman=100 | 0 / 18 | 96.8 (drop barman) .. 99.6 (drop drone) | drone: 88.9% of 9 failures |
| Qwen3.5 9B | solve | tools-steered | 98.0 | drone=60 | barman=100 | 0 / 19 | 97.9 (drop barman) .. 100.0 (drop drone) | drone: 100.0% of 6 failures |
| Qwen3.5 9B | validate_domain | no-tools | 26.7 | tpp=6 | satellite=100 | 0 / 1 | 22.8 (drop satellite) .. 27.8 (drop tpp) | satellite: 18.8% of 96 successes |
| Qwen3.5 9B | validate_problem | tools-steered | 93.7 | gardening=47 | barman=100 | 0 / 11 | 93.3 (drop barman) .. 96.1 (drop gardening) | gardening: 42.1% of 38 failures |
| Qwen3.5 9B | simulate | tools-steered | 83.7 | counters=20 | barman=100 | 0 / 11 | 82.8 (drop barman) .. 87.0 (drop counters) | counters: 24.5% of 49 failures |
| Qwen3.6 35B | validate_domain | no-tools | 70.3 | gardening=11 | barman=100 | 0 / 3 | 68.7 (drop barman) .. 73.4 (drop gardening) | gardening: 15.0% of 107 failures |
| Qwen3.6 35B | validate_domain | tools-plain | 95.6 | rovers=33 | barman=100 | 0 / 17 | 95.3 (drop barman) .. 98.8 (drop rovers) | rovers: 75.0% of 16 failures |
| Qwen3.6 35B | validate_domain | tools-steered | 97.5 | rovers=56 | barman=100 | 0 / 18 | 97.4 (drop barman) .. 99.7 (drop rovers) | rovers: 88.9% of 9 failures |
| Qwen3.6 35B | validate_problem | tools-steered | 95.5 | parking=63 | depots=100 | 0 / 12 | 95.3 (drop depots) .. 97.2 (drop parking) | parking: 40.7% of 27 failures |
| Qwen3.6 35B | validate_plan | tools-steered | 97.1 | parking=68 | barman=100 | 0 / 13 | 96.9 (drop barman) .. 98.6 (drop parking) | parking: 54.5% of 88 failures |
| Qwen3.6 35B | simulate | tools-steered | 96.0 | counters=53 | barman=100 | 0 / 14 | 95.8 (drop barman) .. 98.2 (drop counters) | counters: 58.3% of 12 failures |

