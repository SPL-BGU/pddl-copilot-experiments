# Driver flags, sweep5v2-live, think off (harness score)

| model | task | arm | pooled % | lowest domain | highest domain | domains at 0 / at 100 | leave-one-out range | top domain of the rarer outcome |
|---|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | validate_domain | no-tools | 77.8 | block-grouping=17 | blocksworld=100 | 0 / 6 | 76.6 (drop blocksworld) .. 81.0 (drop block-grouping) | block-grouping: 18.8% of 80 failures |
| Gemma 26B a4b | validate_domain | tools-steered | 98.3 | satellite=83 | barman=100 | 0 / 17 | 98.2 (drop barman) .. 99.1 (drop satellite) | satellite: 50.0% of 6 failures |
| Gemma 26B a4b | validate_plan | tools-plain | 20.6 | barman=0 | blocksworld=80 | 7 / 0 | 17.4 (drop blocksworld) .. 21.6 (drop barman) | blocksworld: 19.4% of 617 successes |
| Gemma 26B a4b | validate_plan | tools-steered | 92.6 | barman=18 | blocksworld=100 | 0 / 8 | 92.2 (drop blocksworld) .. 96.5 (drop barman) | barman: 55.2% of 223 failures |
| Qwen3.5 9B | validate_domain | no-tools | 25.6 | delivery=11 | satellite=100 | 0 / 1 | 21.6 (drop satellite) .. 26.3 (drop delivery) | satellite: 19.6% of 92 successes |
| Qwen3.5 9B | validate_plan | tools-steered | 96.0 | counters=65 | blocksworld=100 | 0 / 13 | 95.8 (drop blocksworld) .. 97.7 (drop counters) | counters: 44.5% of 119 failures |
| Qwen3.5 9B | simulate | tools-steered | 83.0 | counters=20 | blocksworld=100 | 0 / 9 | 82.1 (drop blocksworld) .. 86.3 (drop counters) | counters: 23.5% of 51 failures |
| Qwen3.6 35B | simulate | tools-steered | 97.0 | counters=73 | barman=100 | 0 / 16 | 96.8 (drop barman) .. 98.2 (drop counters) | counters: 44.4% of 9 failures |

