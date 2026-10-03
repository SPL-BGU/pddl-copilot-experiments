## Table A. Headline arm rates: paper intervals vs cluster bootstrap (think=off)

Percent. `<a, b>` is a censoring bound. For a bounded cell every interval is the outer envelope (lower limit on the low end, upper limit on the high end). `deff` = variance inflation relative to independent trials, on the determinate series.

### mechanism layer (harness success; tool-verified in the tool arms)

| model | task | arm | rate | Wilson | Wilson x sqrt(2.7) | boot: instance | boot: problem | boot: domain (k=20) | widest | deff inst | deff domain |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | nt-neut | 10.7 | [7.7, 14.7] | [6.2, 17.8] | [7.3, 14.0] | [7.3, 14.0] | [6.3, 15.0] | Wilson x sqrt(2.7) | 0.9 | 1.6 |
| Qwen3.5-9B | solve | tl-neut | 99.3 | [97.6, 99.8] | [95.5, 99.9] | [98.0, 100.0] | [98.0, 100.0] | [98.0, 100.0] | Wilson x sqrt(2.7) | 2.0 | 2.0 |
| Qwen3.5-9B | solve | tl-ster | 100.0 | [98.7, 100.0] | [96.7, 100.0] | [100.0, 100.0] | [100.0, 100.0] | [100.0, 100.0] | Wilson x sqrt(2.7) | nan | nan |
| Qwen3.5-9B | v_dom | nt-neut | 25.6 | [21.3, 30.3] | [18.9, 33.6] | [18.6, 32.8] | [18.6, 32.8] | [17.5, 36.4] | domain | 2.5 | 4.7 |
| Qwen3.5-9B | v_dom | tl-neut | 100.0 | [98.9, 100.0] | [97.2, 100.0] | [100.0, 100.0] | [100.0, 100.0] | [100.0, 100.0] | Wilson x sqrt(2.7) | nan | nan |
| Qwen3.5-9B | v_dom | tl-ster | 100.0 | [98.9, 100.0] | [97.2, 100.0] | [100.0, 100.0] | [100.0, 100.0] | [100.0, 100.0] | Wilson x sqrt(2.7) | nan | nan |
| Qwen3.5-9B | v_prob | nt-neut | 65.7 | [61.8, 69.4] | [59.2, 71.6] | [60.2, 71.2] | [60.2, 71.2] | [59.2, 71.5] | Wilson x sqrt(2.7) | 2.2 | 2.8 |
| Qwen3.5-9B | v_prob | tl-neut | 95.2 | [93.1, 96.6] | [91.5, 97.3] | [92.2, 97.8] | [92.2, 97.8] | [93.2, 97.2] | Wilson x sqrt(2.7) | 2.7 | 1.4 |
| Qwen3.5-9B | v_prob | tl-ster | 90.2 | [87.5, 92.3] | [85.5, 93.4] | [86.2, 93.8] | [86.2, 93.8] | [83.3, 95.5] | domain | 2.6 | 7.1 |
| Qwen3.5-9B | v_plan | nt-neut | 79.7 | [78.3, 81.1] | [77.3, 82.0] | [77.6, 81.8] | [75.9, 83.5] | [73.7, 85.5] | domain | 2.2 | 17.6 |
| Qwen3.5-9B | v_plan | tl-neut | 93.2 | [92.2, 94.0] | [91.5, 94.5] | [91.8, 94.5] | [89.7, 96.2] | [88.2, 97.4] | domain | 2.2 | 28.1 |
| Qwen3.5-9B | v_plan | tl-ster | 96.0 | [95.3, 96.7] | [94.7, 97.0] | [94.9, 97.1] | [93.2, 98.4] | [91.9, 99.1] | domain | 2.6 | 28.7 |
| Qwen3.5-9B | sim | nt-neut | 0.0 | [0.0, 1.3] | [0.0, 3.3] | [0.0, 0.0] | [0.0, 0.0] | [0.0, 0.0] | Wilson x sqrt(2.7) | nan | nan |
| Qwen3.5-9B | sim | tl-neut | 65.0 | [59.4, 70.2] | [55.8, 73.2] | [59.0, 70.7] | [59.0, 70.7] | [56.3, 72.7] | Wilson x sqrt(2.7) | 1.2 | 2.5 |
| Qwen3.5-9B | sim | tl-ster | 83.0 | [78.3, 86.8] | [74.9, 88.9] | [76.3, 89.3] | [76.3, 89.3] | [73.0, 91.7] | domain | 2.4 | 5.2 |
| Gemma-26B | solve | nt-neut | 7.7 | [5.2, 11.2] | [4.0, 14.1] | [4.7, 10.7] | [4.7, 10.7] | [4.0, 12.0] | Wilson x sqrt(2.7) | 1.0 | 1.8 |
| Gemma-26B | solve | tl-neut | 99.3 | [97.6, 99.8] | [95.5, 99.9] | [98.3, 100.0] | [98.3, 100.0] | [98.3, 100.0] | Wilson x sqrt(2.7) | 1.0 | 1.0 |
| Gemma-26B | solve | tl-ster | 98.7 | [96.6, 99.5] | [94.4, 99.7] | [97.3, 99.7] | [97.3, 99.7] | [96.3, 100.0] | Wilson x sqrt(2.7) | 1.0 | 2.5 |
| Gemma-26B | v_dom | nt-neut | 77.8 | [73.2, 81.8] | [70.0, 84.0] | [71.1, 84.2] | [71.1, 84.2] | [65.6, 88.6] | domain | 2.3 | 7.6 |
| Gemma-26B | v_dom | tl-neut | 97.5 | [95.3, 98.7] | [93.2, 99.1] | [94.4, 99.7] | [94.4, 99.7] | [95.0, 99.4] | Wilson x sqrt(2.7) | 2.6 | 2.3 |
| Gemma-26B | v_dom | tl-ster | 98.3 | [96.4, 99.2] | [94.4, 99.5] | [96.1, 100.0] | [96.1, 100.0] | [96.1, 100.0] | Wilson x sqrt(2.7) | 2.3 | 2.2 |
| Gemma-26B | v_prob | nt-neut | 74.8 | [71.2, 78.1] | [68.7, 80.1] | [69.3, 79.8] | [69.3, 79.8] | [68.8, 80.7] | domain | 2.3 | 3.0 |
| Gemma-26B | v_prob | tl-neut | 99.7 | [98.8, 99.9] | [97.7, 100.0] | [99.2, 100.0] | [99.2, 100.0] | [99.2, 100.0] | Wilson x sqrt(2.7) | 1.0 | 1.0 |
| Gemma-26B | v_prob | tl-ster | 100.0 | [99.4, 100.0] | [98.3, 100.0] | [100.0, 100.0] | [100.0, 100.0] | [100.0, 100.0] | Wilson x sqrt(2.7) | nan | nan |
| Gemma-26B | v_plan | nt-neut | 87.8 | [86.6, 89.0] | [85.8, 89.6] | [86.1, 89.6] | [84.7, 90.8] | [83.7, 91.4] | domain | 2.3 | 11.8 |
| Gemma-26B | v_plan | tl-neut | 20.6 | [19.2, 22.1] | [18.3, 23.0] | [18.7, 22.6] | [14.8, 26.5] | [8.9, 33.9] | domain | 1.8 | 78.4 |
| Gemma-26B | v_plan | tl-ster | 92.6 | [91.6, 93.5] | [90.9, 94.0] | [91.1, 94.0] | [88.0, 96.3] | [83.2, 98.7] | domain | 2.5 | 77.9 |
| Gemma-26B | sim | nt-neut | 0.0 | [0.0, 1.3] | [0.0, 3.3] | [0.0, 0.0] | [0.0, 0.0] | [0.0, 0.0] | Wilson x sqrt(2.7) | nan | nan |
| Gemma-26B | sim | tl-neut | 91.7 | [88.0, 94.3] | [85.0, 95.5] | [87.0, 95.7] | [87.0, 95.7] | [86.0, 96.7] | domain | 2.1 | 3.0 |
| Gemma-26B | sim | tl-ster | 90.7 | [86.8, 93.5] | [83.8, 94.8] | [85.3, 95.3] | [85.3, 95.3] | [83.0, 97.3] | domain | 2.5 | 4.9 |
| Qwen3.6-35B | solve | nt-neut | 9.3 | [6.5, 13.2] | [5.2, 16.2] | [6.3, 12.3] | [6.3, 12.3] | [6.3, 12.3] | Wilson x sqrt(2.7) | 0.8 | 0.9 |
| Qwen3.6-35B | solve | tl-neut | 63.0 | [57.4, 68.3] | [53.7, 71.4] | [57.0, 69.0] | [57.0, 69.0] | [54.3, 71.7] | Wilson x sqrt(2.7) | 1.2 | 2.5 |
| Qwen3.6-35B | solve | tl-ster | 92.0 | [88.4, 94.6] | [85.4, 95.8] | [88.0, 95.3] | [88.0, 95.3] | [87.0, 96.7] | Wilson x sqrt(2.7) | 1.5 | 2.6 |
| Qwen3.6-35B | v_dom | nt-neut | 67.8 | [62.8, 72.4] | [59.4, 75.1] | [61.1, 74.2] | [61.1, 74.2] | [56.4, 78.3] | domain | 1.8 | 5.6 |
| Qwen3.6-35B | v_dom | tl-neut | 98.9 | [97.2, 99.6] | [95.3, 99.7] | [97.5, 100.0] | [97.5, 100.0] | [97.2, 100.0] | Wilson x sqrt(2.7) | 1.5 | 1.9 |
| Qwen3.6-35B | v_dom | tl-ster | 99.7 | [98.4, 100.0] | [96.7, 100.0] | [99.2, 100.0] | [99.2, 100.0] | [99.2, 100.0] | Wilson x sqrt(2.7) | 1.0 | 1.0 |
| Qwen3.6-35B | v_prob | nt-neut | 75.7 | [72.1, 78.9] | [69.6, 80.8] | [70.3, 81.0] | [70.3, 81.0] | [71.2, 79.8] | Wilson x sqrt(2.7) | 2.4 | 1.7 |
| Qwen3.6-35B | v_prob | tl-neut | 96.8 | [95.1, 98.0] | [93.6, 98.5] | [95.0, 98.5] | [95.0, 98.5] | [95.2, 98.2] | Wilson x sqrt(2.7) | 1.6 | 1.2 |
| Qwen3.6-35B | v_prob | tl-ster | 97.3 | [95.7, 98.4] | [94.3, 98.8] | [95.2, 99.2] | [95.2, 99.2] | [95.5, 99.0] | Wilson x sqrt(2.7) | 2.5 | 1.8 |
| Qwen3.6-35B | v_plan | nt-neut | 90.9 | [89.8, 91.9] | [89.1, 92.5] | [89.3, 92.4] | [87.9, 93.6] | [87.7, 93.9] | domain | 2.2 | 9.3 |
| Qwen3.6-35B | v_plan | tl-neut | 82.2 | [80.8, 83.5] | [79.8, 84.3] | [80.3, 83.9] | [77.3, 86.7] | [72.6, 90.6] | domain | 1.8 | 45.9 |
| Qwen3.6-35B | v_plan | tl-ster | 99.3 | [98.9, 99.5] | [98.6, 99.6] | [98.8, 99.6] | [98.7, 99.7] | [98.7, 99.8] | domain | 1.6 | 3.3 |
| Qwen3.6-35B | sim | nt-neut | 0.0 | [0.0, 1.3] | [0.0, 3.3] | [0.0, 0.0] | [0.0, 0.0] | [0.0, 0.0] | Wilson x sqrt(2.7) | nan | nan |
| Qwen3.6-35B | sim | tl-neut | 74.7 | [69.5, 79.3] | [65.8, 81.8] | [68.7, 80.3] | [68.7, 80.3] | [65.3, 83.0] | domain | 1.5 | 3.3 |
| Qwen3.6-35B | sim | tl-ster | 97.0 | [94.4, 98.4] | [91.9, 98.9] | [94.0, 99.3] | [94.0, 99.3] | [93.3, 99.7] | Wilson x sqrt(2.7) | 1.9 | 2.8 |

### delivered surface

| model | task | arm | rate | Wilson | Wilson x sqrt(2.7) | boot: instance | boot: problem | boot: domain (k=20) | widest | deff inst | deff domain |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | nt-neut | 10.7 | [7.7, 14.7] | [6.2, 17.8] | [7.3, 14.0] | [7.3, 14.0] | [6.3, 15.0] | Wilson x sqrt(2.7) | 0.9 | 1.6 |
| Qwen3.5-9B | solve | tl-neut | <26.0, 58.7> | [21.4, 64.1] | [18.7, 67.4] | [19.3, 67.0] | [19.3, 67.0] | [13.3, 74.0] | domain | 1.8 | 7.1 |
| Qwen3.5-9B | solve | tl-ster | <27.7, 65.3> | [22.9, 70.5] | [20.2, 73.5] | [21.3, 73.7] | [21.3, 73.7] | [16.0, 79.3] | domain | 1.7 | 6.0 |
| Qwen3.5-9B | v_dom | nt-neut | 25.6 | [21.3, 30.3] | [18.9, 33.6] | [18.6, 32.8] | [18.6, 32.8] | [17.5, 36.4] | domain | 2.5 | 4.7 |
| Qwen3.5-9B | v_dom | tl-neut | <99.7, 100.0> | [98.4, 100.0] | [96.7, 100.0] | [99.2, 100.0] | [99.2, 100.0] | [99.2, 100.0] | Wilson x sqrt(2.7) | 1.0 | 1.0 |
| Qwen3.5-9B | v_dom | tl-ster | 100.0 | [98.9, 100.0] | [97.2, 100.0] | [100.0, 100.0] | [100.0, 100.0] | [100.0, 100.0] | Wilson x sqrt(2.7) | nan | nan |
| Qwen3.5-9B | v_prob | nt-neut | 65.7 | [61.8, 69.4] | [59.2, 71.6] | [60.2, 71.2] | [60.2, 71.2] | [59.2, 71.5] | Wilson x sqrt(2.7) | 2.2 | 2.8 |
| Qwen3.5-9B | v_prob | tl-neut | <92.2, 95.3> | [89.7, 96.8] | [87.9, 97.4] | [88.7, 97.8] | [88.7, 97.8] | [89.0, 97.3] | Wilson x sqrt(2.7) | 2.6 | 2.2 |
| Qwen3.5-9B | v_prob | tl-ster | <87.7, 91.0> | [84.8, 93.0] | [82.7, 94.1] | [83.3, 94.3] | [83.3, 94.3] | [80.2, 95.7] | domain | 2.5 | 7.2 |
| Qwen3.5-9B | v_plan | nt-neut | 79.7 | [78.3, 81.1] | [77.3, 82.0] | [77.6, 81.8] | [75.9, 83.5] | [73.7, 85.5] | domain | 2.2 | 17.6 |
| Qwen3.5-9B | v_plan | tl-neut | <80.8, 87.2> | [79.3, 88.4] | [78.3, 89.1] | [78.5, 89.1] | [74.7, 92.2] | [73.0, 92.9] | domain | 2.5 | 29.2 |
| Qwen3.5-9B | v_plan | tl-ster | <86.9, 88.9> | [85.7, 90.0] | [84.8, 90.6] | [84.9, 90.8] | [81.4, 93.8] | [80.7, 94.4] | domain | 2.7 | 25.8 |
| Qwen3.5-9B | sim | nt-neut | <0.0, 87.3> | [0.0, 90.6] | [0.0, 92.3] | [0.0, 90.3] | [0.0, 90.3] | [0.0, 93.0] | domain | nan | nan |
| Qwen3.5-9B | sim | tl-neut | <0.0, 39.0> | [0.0, 44.6] | [0.0, 48.3] | [0.0, 46.3] | [0.0, 46.3] | [0.0, 49.0] | domain | nan | nan |
| Qwen3.5-9B | sim | tl-ster | <0.0, 25.3> | [0.0, 30.5] | [0.0, 34.2] | [0.0, 34.0] | [0.0, 34.0] | [0.0, 37.0] | domain | nan | nan |
| Gemma-26B | solve | nt-neut | 7.7 | [5.2, 11.2] | [4.0, 14.1] | [4.7, 10.7] | [4.7, 10.7] | [4.0, 12.0] | Wilson x sqrt(2.7) | 1.0 | 1.8 |
| Gemma-26B | solve | tl-neut | <14.3, 35.3> | [10.8, 40.9] | [9.0, 44.6] | [9.3, 42.3] | [9.3, 42.3] | [6.7, 42.3] | domain | 1.8 | 4.2 |
| Gemma-26B | solve | tl-ster | <23.7, 59.3> | [19.2, 64.7] | [16.7, 68.0] | [18.0, 65.0] | [18.0, 65.0] | [14.3, 65.3] | Wilson x sqrt(2.7) | 1.4 | 4.1 |
| Gemma-26B | v_dom | nt-neut | 77.8 | [73.2, 81.8] | [70.0, 84.0] | [71.1, 84.2] | [71.1, 84.2] | [65.6, 88.6] | domain | 2.3 | 7.6 |
| Gemma-26B | v_dom | tl-neut | <93.3, 98.1> | [90.3, 99.1] | [87.8, 99.4] | [89.7, 100.0] | [89.7, 100.0] | [87.2, 100.0] | domain | 1.8 | 4.8 |
| Gemma-26B | v_dom | tl-ster | <94.7, 98.3> | [91.9, 99.2] | [89.5, 99.5] | [90.8, 100.0] | [90.8, 100.0] | [88.1, 100.0] | domain | 2.1 | 7.0 |
| Gemma-26B | v_prob | nt-neut | 74.8 | [71.2, 78.1] | [68.7, 80.1] | [69.3, 79.8] | [69.3, 79.8] | [68.8, 80.7] | domain | 2.3 | 3.0 |
| Gemma-26B | v_prob | tl-neut | <84.3, 99.8> | [81.2, 100.0] | [79.0, 100.0] | [80.7, 100.0] | [80.7, 100.0] | [79.5, 100.0] | Wilson x sqrt(2.7) | 1.7 | 2.8 |
| Gemma-26B | v_prob | tl-ster | <91.7, 100.0> | [89.2, 100.0] | [87.3, 100.0] | [88.5, 100.0] | [88.5, 100.0] | [89.5, 100.0] | Wilson x sqrt(2.7) | 1.8 | 1.0 |
| Gemma-26B | v_plan | nt-neut | 87.8 | [86.6, 89.0] | [85.8, 89.6] | [86.1, 89.6] | [84.7, 90.8] | [83.7, 91.4] | domain | 2.3 | 11.8 |
| Gemma-26B | v_plan | tl-neut | <6.6, 99.6> | [5.7, 99.7] | [5.3, 99.8] | [5.4, 99.8] | [4.0, 100.0] | [2.5, 100.0] | domain | 1.7 | 26.9 |
| Gemma-26B | v_plan | tl-ster | <55.5, 95.1> | [53.7, 95.8] | [52.6, 96.2] | [52.7, 96.4] | [49.4, 98.3] | [45.9, 98.6] | domain | 2.5 | 30.0 |
| Gemma-26B | sim | nt-neut | <0.0, 100.0> | [0.0, 100.0] | [0.0, 100.0] | [0.0, 100.0] | [0.0, 100.0] | [0.0, 100.0] | problem | nan | nan |
| Gemma-26B | sim | tl-neut | <0.0, 27.3> | [0.0, 32.6] | [0.0, 36.3] | [0.0, 35.7] | [0.0, 35.7] | [0.0, 38.3] | domain | nan | nan |
| Gemma-26B | sim | tl-ster | <0.0, 27.3> | [0.0, 32.6] | [0.0, 36.3] | [0.0, 35.7] | [0.0, 35.7] | [0.0, 38.3] | domain | nan | nan |
| Qwen3.6-35B | solve | nt-neut | 9.3 | [6.5, 13.2] | [5.2, 16.2] | [6.3, 12.3] | [6.3, 12.3] | [6.3, 12.3] | Wilson x sqrt(2.7) | 0.8 | 0.9 |
| Qwen3.6-35B | solve | tl-neut | <12.7, 53.7> | [9.4, 59.2] | [7.7, 62.7] | [8.0, 61.3] | [8.0, 61.3] | [5.7, 65.7] | domain | 1.7 | 4.3 |
| Qwen3.6-35B | solve | tl-ster | <16.7, 47.7> | [12.9, 53.3] | [10.9, 56.9] | [11.3, 56.0] | [11.3, 56.0] | [8.3, 63.0] | domain | 1.7 | 5.0 |
| Qwen3.6-35B | v_dom | nt-neut | 67.8 | [62.8, 72.4] | [59.4, 75.1] | [61.1, 74.2] | [61.1, 74.2] | [56.4, 78.3] | domain | 1.8 | 5.6 |
| Qwen3.6-35B | v_dom | tl-neut | <91.9, 99.2> | [88.7, 99.7] | [86.1, 99.8] | [87.2, 100.0] | [87.2, 100.0] | [88.9, 100.0] | Wilson x sqrt(2.7) | 2.3 | 1.3 |
| Qwen3.6-35B | v_dom | tl-ster | <93.3, 99.7> | [90.3, 100.0] | [87.8, 100.0] | [90.0, 100.0] | [90.0, 100.0] | [90.8, 100.0] | Wilson x sqrt(2.7) | 1.5 | 1.0 |
| Qwen3.6-35B | v_prob | nt-neut | 75.7 | [72.1, 78.9] | [69.6, 80.8] | [70.3, 81.0] | [70.3, 81.0] | [71.2, 79.8] | Wilson x sqrt(2.7) | 2.4 | 1.7 |
| Qwen3.6-35B | v_prob | tl-neut | <74.7, 97.8> | [71.0, 98.7] | [68.6, 99.1] | [69.7, 99.2] | [69.7, 99.2] | [71.7, 99.2] | Wilson x sqrt(2.7) | 2.1 | 0.7 |
| Qwen3.6-35B | v_prob | tl-ster | <82.2, 97.0> | [78.9, 98.1] | [76.6, 98.6] | [77.5, 98.8] | [77.5, 98.8] | [79.5, 98.7] | Wilson x sqrt(2.7) | 2.3 | 0.8 |
| Qwen3.6-35B | v_plan | nt-neut | 90.9 | [89.8, 91.9] | [89.1, 92.5] | [89.3, 92.4] | [87.9, 93.6] | [87.7, 93.9] | domain | 2.2 | 9.3 |
| Qwen3.6-35B | v_plan | tl-neut | <55.0, 90.3> | [53.2, 91.3] | [52.1, 91.9] | [52.6, 91.9] | [49.7, 94.6] | [47.2, 95.3] | domain | 2.0 | 19.3 |
| Qwen3.6-35B | v_plan | tl-ster | <75.9, 90.0> | [74.3, 91.0] | [73.3, 91.6] | [73.5, 91.7] | [70.9, 94.6] | [71.0, 95.0] | domain | 2.3 | 10.3 |
| Qwen3.6-35B | sim | nt-neut | <0.0, 90.3> | [0.0, 93.2] | [0.0, 94.6] | [0.0, 93.3] | [0.0, 93.3] | [0.0, 95.0] | domain | nan | nan |
| Qwen3.6-35B | sim | tl-neut | <0.0, 39.0> | [0.0, 44.6] | [0.0, 48.3] | [0.0, 47.7] | [0.0, 47.7] | [0.0, 51.0] | domain | nan | nan |
| Qwen3.6-35B | sim | tl-ster | <0.0, 27.0> | [0.0, 32.3] | [0.0, 35.9] | [0.0, 36.0] | [0.0, 36.0] | [0.0, 39.0] | domain | nan | nan |

## Table B (mech). Paired arm contrasts, mechanism layer, think=off, headline models

Delta = second arm minus first arm, in points, over fixture-matched pairs. `governing CI` = the wider of the domain-clustered (k=20) and problem-clustered 95% t intervals. p = cluster-t p of the governing clustering; `flip` = exact sign-flip test on the 20 domain sums. Holm column = verdict after Holm at 0.05 over the 30 headline contrasts on this surface.

| model | task | contrast | arm A | arm B | Delta | governing CI | by | boot domain | boot problem | p | flip p | paper (Wilson) | paper (x sqrt 2.7) | clustered paired | after Holm (30) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | avail | 10.7 | 99.3 | +88.7 | [83.4, 93.9] | doma | [83.7, 93.3] | [85.0, 92.0] | 9.1e-19 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | solve | steer | 99.3 | 100.0 | +0.7 | [-0.7, 2.1] | doma | [0.0, 2.0] | [0.0, 2.0] | 0.330 | 1.000 | NS | NS | NS | NS |
| Qwen3.5-9B | v_dom | avail | 25.6 | 100.0 | +74.4 | [64.0, 84.9] | doma | [63.6, 82.5] | [67.2, 81.4] | 6.1e-12 | 3.8e-06 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_dom | steer | 100.0 | 100.0 | +0.0 | [0.0, 0.0] | doma | [0.0, 0.0] | [0.0, 0.0] | 1.000 | 1.000 | NS | NS | NS | NS |
| Qwen3.5-9B | v_prob | avail | 65.7 | 95.2 | +29.5 | [22.2, 36.8] | doma | [23.2, 36.5] | [24.0, 35.3] | 6.8e-08 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_prob | steer | 95.2 | 90.2 | -5.0 | [-10.9, 0.9] | doma | [-11.2, -0.5] | [-8.2, -2.2] | 0.093 | 0.086 | AGAINST | NS | NS | NS |
| Qwen3.5-9B | v_plan | avail | 79.7 | 93.2 | +13.4 | [5.0, 21.9] | doma | [5.6, 21.2] | [9.0, 17.9] | 0.004 | 0.004 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_plan | steer | 93.2 | 96.0 | +2.9 | [-0.6, 6.3] | doma | [0.5, 6.6] | [1.0, 5.1] | 0.097 | 0.020 | FAV | FAV | NS | NS |
| Qwen3.5-9B | sim | avail | 0.0 | 65.0 | +65.0 | [55.9, 74.1] | doma | [56.3, 72.7] | [59.0, 70.7] | 5.9e-12 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | sim | steer | 65.0 | 83.0 | +18.0 | [13.4, 22.6] | doma | [13.7, 22.0] | [13.7, 22.0] | 1.4e-07 | 7.6e-06 | FAV | FAV | FAV | FAV |
| Gemma-26B | solve | avail | 7.7 | 99.3 | +91.7 | [87.3, 96.1] | doma | [87.3, 95.3] | [88.3, 94.7] | 1.6e-20 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Gemma-26B | solve | steer | 99.3 | 98.7 | -0.7 | [-2.9, 1.6] | doma | [-3.0, 1.0] | [-2.0, 0.7] | 0.541 | 1.000 | NS | NS | NS | NS |
| Gemma-26B | v_dom | avail | 77.8 | 97.5 | +19.7 | [7.1, 32.4] | doma | [8.9, 31.9] | [13.1, 26.7] | 0.004 | 0.001 | FAV | FAV | FAV | FAV |
| Gemma-26B | v_dom | steer | 97.5 | 98.3 | +0.8 | [-0.1, 1.8] | doma | [0.0, 1.7] | [0.0, 1.9] | 0.083 | 0.250 | NS | NS | NS | NS |
| Gemma-26B | v_prob | avail | 74.8 | 99.7 | +24.8 | [18.3, 31.3] | doma | [19.0, 30.8] | [19.8, 30.2] | 1.7e-07 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Gemma-26B | v_prob | steer | 99.7 | 100.0 | +0.3 | [-0.1, 0.8] | doma | [0.0, 0.8] | [0.0, 0.8] | 0.163 | 0.500 | NS | NS | NS | NS |
| Gemma-26B | v_plan | avail | 87.8 | 20.6 | -67.3 | [-79.7, -54.8] | doma | [-78.0, -55.3] | [-73.2, -61.2] | 6.7e-10 | 1.9e-06 | AGAINST | AGAINST | AGAINST | AGAINST |
| Gemma-26B | v_plan | steer | 20.6 | 92.6 | +72.0 | [57.5, 86.5] | doma | [58.2, 84.5] | [65.5, 78.4] | 2.8e-09 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Gemma-26B | sim | avail | 0.0 | 91.7 | +91.7 | [85.9, 97.5] | doma | [86.0, 96.7] | [87.0, 95.7] | 3.0e-18 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Gemma-26B | sim | steer | 91.7 | 90.7 | -1.0 | [-4.7, 2.7] | doma | [-4.7, 2.0] | [-4.0, 1.7] | 0.577 | 0.719 | NS | NS | NS | NS |
| Qwen3.6-35B | solve | avail | 9.3 | 63.0 | +53.7 | [45.7, 61.7] | doma | [46.3, 61.0] | [47.7, 59.7] | 1.8e-11 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | solve | steer | 63.0 | 92.0 | +29.0 | [21.6, 36.4] | doma | [22.3, 35.7] | [23.0, 35.0] | 1.1e-07 | 7.6e-06 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_dom | avail | 67.8 | 98.9 | +31.1 | [18.4, 43.8] | doma | [20.0, 43.1] | [24.7, 37.8] | 6.0e-05 | 1.9e-05 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_dom | steer | 98.9 | 99.7 | +0.8 | [-0.4, 2.1] | doma | [0.0, 2.2] | [0.0, 1.9] | 0.186 | 0.500 | NS | NS | NS | NS |
| Qwen3.6-35B | v_prob | avail | 75.7 | 96.8 | +21.2 | [15.5, 26.8] | prob | [16.5, 26.2] | [15.7, 26.8] | 7.9e-08 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_prob | steer | 96.8 | 97.3 | +0.5 | [-1.1, 2.1] | prob | [-0.5, 1.3] | [-1.2, 2.0] | 0.550 | 0.531 | NS | NS | NS | NS |
| Qwen3.6-35B | v_plan | avail | 90.9 | 82.2 | -8.7 | [-19.0, 1.5] | doma | [-18.5, 0.0] | [-14.2, -3.2] | 0.090 | 0.097 | AGAINST | AGAINST | NS | NS |
| Qwen3.6-35B | v_plan | steer | 82.2 | 99.3 | +17.1 | [7.4, 26.8] | doma | [8.9, 26.5] | [12.7, 21.9] | 0.002 | 3.8e-06 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | sim | avail | 0.0 | 74.7 | +74.7 | [65.1, 84.2] | doma | [65.3, 83.0] | [68.7, 80.3] | 1.1e-12 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | sim | steer | 74.7 | 97.0 | +22.3 | [12.8, 31.9] | doma | [14.3, 31.7] | [16.3, 28.3] | 1.0e-04 | 3.8e-05 | FAV | FAV | FAV | FAV |

## Table B (dlv). Paired arm contrasts, delivered surface, think=off, headline models

Delta = second arm minus first arm, in points, over fixture-matched pairs. `governing CI` = the wider of the domain-clustered (k=20) and problem-clustered 95% t intervals. p = cluster-t p of the governing clustering; `flip` = exact sign-flip test on the 20 domain sums. Holm column = verdict after Holm at 0.05 over the 30 headline contrasts on this surface.

| model | task | contrast | arm A | arm B | Delta | governing CI | by | boot domain | boot problem | p | flip p | paper (Wilson) | paper (x sqrt 2.7) | clustered paired | after Holm (30) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | avail | 10.7 | <26.0, 58.7> | <+15.3, +48.0> | [1.1, 65.6] | doma | [3.0, 63.7] | [8.7, 57.0] | 0.036 | 0.040 | FAV | FAV | FAV | ns-after-Holm |
| Qwen3.5-9B | solve | steer | <26.0, 58.7> | <27.7, 65.3> | <-31.0, +39.3> | [-43.4, 51.9] | doma | [-42.7, 51.0] | [-38.3, 46.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.5-9B | v_dom | avail | 25.6 | <99.7, 100.0> | <+74.2, +74.4> | [63.8, 84.9] | doma | [63.3, 82.5] | [66.9, 81.4] | 6.1e-12 | 3.8e-06 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_dom | steer | <99.7, 100.0> | 100.0 | <+0.0, +0.3> | [0.0, 0.9] | doma | [0.0, 0.8] | [0.0, 0.8] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.5-9B | v_prob | avail | 65.7 | <92.2, 95.3> | <+26.5, +29.7> | [19.0, 36.9] | doma | [19.8, 36.7] | [21.0, 35.3] | 5.8e-07 | 1.9e-06 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_prob | steer | <92.2, 95.3> | <87.7, 91.0> | <-7.7, -1.2> | [-14.4, 3.5] | doma | [-14.5, 2.5] | [-11.2, 2.0] | 0.605 | 0.742 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.5-9B | v_plan | avail | 79.7 | <80.8, 87.2> | <+1.0, +7.5> | [-8.3, 13.5] | doma | [-8.2, 13.1] | [-4.4, 11.6] | 0.819 | 0.827 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.5-9B | v_plan | steer | <80.8, 87.2> | <86.9, 88.9> | <-0.3, +8.1> | [-2.0, 15.1] | doma | [-1.8, 15.3] | [-2.2, 11.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.5-9B | sim | avail | <0.0, 87.3> | <0.0, 39.0> | <-87.3, +39.0> | [-93.6, 49.4] | doma | [-93.0, 49.0] | [-90.3, 46.3] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.5-9B | sim | steer | <0.0, 39.0> | <0.0, 25.3> | <-39.0, +25.3> | [-49.4, 37.7] | doma | [-49.0, 37.0] | [-46.3, 34.0] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | solve | avail | 7.7 | <14.3, 35.3> | <+6.7, +27.7> | [-2.5, 36.1] | doma | [-1.3, 35.3] | [1.3, 35.3] | 0.144 | 0.168 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | solve | steer | <14.3, 35.3> | <23.7, 59.3> | <-11.7, +45.0> | [-21.2, 56.1] | doma | [-20.3, 55.3] | [-20.0, 52.0] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | v_dom | avail | 77.8 | <93.3, 98.1> | <+15.6, +20.3> | [1.6, 32.9] | doma | [3.3, 32.5] | [8.3, 26.9] | 0.031 | 0.034 | FAV | FAV | FAV | ns-after-Holm |
| Gemma-26B | v_dom | steer | <93.3, 98.1> | <94.7, 98.3> | <-3.3, +5.0> | [-9.8, 10.3] | doma | [-9.7, 10.6] | [-6.4, 7.8] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | v_prob | avail | 74.8 | <84.3, 99.8> | <+9.5, +25.0> | [0.9, 31.6] | doma | [1.7, 31.0] | [3.7, 30.3] | 0.032 | 0.034 | FAV | UNDECIDED | FAV | ns-after-Holm |
| Gemma-26B | v_prob | steer | <84.3, 99.8> | <91.7, 100.0> | <-8.2, +15.7> | [-11.2, 20.9] | doma | [-10.3, 20.5] | [-11.3, 19.3] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | v_plan | avail | 87.8 | <6.6, 99.6> | <-81.3, +11.7> | [-85.9, 16.1] | doma | [-85.3, 15.9] | [-84.7, 14.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | v_plan | steer | <6.6, 99.6> | <55.5, 95.1> | <-44.1, +88.5> | [-54.4, 94.5] | doma | [-53.6, 93.7] | [-50.1, 92.5] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | sim | avail | <0.0, 100.0> | <0.0, 27.3> | <-100.0, +27.3> | [-100.0, 39.2] | doma | [-100.0, 38.3] | [-100.0, 35.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Gemma-26B | sim | steer | <0.0, 27.3> | <0.0, 27.3> | <-27.3, +27.3> | [-39.2, 39.2] | doma | [-38.3, 38.3] | [-35.7, 35.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | solve | avail | 9.3 | <12.7, 53.7> | <+3.3, +44.3> | [-5.2, 58.0] | doma | [-4.3, 56.7] | [-2.0, 52.3] | 0.425 | 0.477 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | solve | steer | <12.7, 53.7> | <16.7, 47.7> | <-37.0, +35.0> | [-46.8, 45.8] | doma | [-46.0, 45.3] | [-44.0, 41.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | v_dom | avail | 67.8 | <91.9, 99.2> | <+24.2, +31.4> | [11.8, 43.7] | doma | [13.1, 43.1] | [16.4, 37.8] | 6.2e-04 | 2.9e-04 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_dom | steer | <91.9, 99.2> | <93.3, 99.7> | <-5.8, +7.8> | [-8.9, 12.0] | prob | [-8.6, 10.8] | [-8.9, 12.2] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | v_prob | avail | 75.7 | <74.7, 97.8> | <-1.0, +22.2> | [-6.1, 27.6] | doma | [-5.3, 27.3] | [-6.2, 27.5] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | v_prob | steer | <74.7, 97.8> | <82.2, 97.0> | <-15.7, +22.3> | [-20.0, 26.9] | prob | [-18.7, 26.0] | [-20.2, 26.8] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | v_plan | avail | 90.9 | <55.0, 90.3> | <-35.9, -0.6> | [-44.1, 5.4] | doma | [-43.7, 4.6] | [-40.9, 3.5] | 0.829 | 0.843 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | v_plan | steer | <55.0, 90.3> | <75.9, 90.0> | <-14.4, +35.0> | [-18.9, 44.3] | doma | [-18.6, 44.0] | [-17.4, 39.8] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | sim | avail | <0.0, 90.3> | <0.0, 39.0> | <-90.3, +39.0> | [-95.7, 52.1] | doma | [-95.0, 51.0] | [-93.3, 47.7] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |
| Qwen3.6-35B | sim | steer | <0.0, 39.0> | <0.0, 27.0> | <-39.0, +27.0> | [-52.1, 40.0] | doma | [-51.0, 39.0] | [-47.7, 36.0] | 1.000 | 1.000 | UNDECIDED | UNDECIDED | UNDECIDED | UNDECIDED |

## Table C. Verdict changes

Rows where the paper's rule (Wilson disjointness, widened by sqrt(2.7)) and the clustered paired test disagree, or where Holm removes a clustered verdict. All models, both modes.

| model | think | task | contrast | surface | Delta | governing CI | paper (x sqrt 2.7) | clustered paired | Holm 30 | Holm 60 | Holm 100 | Holm 200 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | off | solve | avail | mech | +12.0 | [1.5, 22.5] | FAV | FAV | - | - | ns-after-Holm | ns-after-Holm |
| Qwen3.5-0.8B | off | v_prob | avail | mech | -25.0 | [-40.1, -9.9] | AGAINST | AGAINST | - | - | ns-after-Holm | ns-after-Holm |
| Qwen3.5-0.8B | off | v_prob | steer | mech | -7.7 | [-14.3, -1.0] | NS | AGAINST | - | - | ns-after-Holm | ns-after-Holm |
| Qwen3.5-0.8B | off | sim | avail | mech | +6.3 | [0.1, 12.5] | NS | FAV | - | - | ns-after-Holm | ns-after-Holm |
| Qwen3.5-0.8B | on | solve | avail | mech | +11.7 | [5.5, 17.8] | FAV | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-0.8B | on | solve | steer | mech | +11.3 | [3.1, 19.6] | NS | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-0.8B | on | v_plan | avail | dlv | <+5.8, +6.2> | [2.1, 10.0] | FAV | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-0.8B | on | sim | avail | mech | +5.0 | [1.4, 8.6] | NS | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-4B | off | v_plan | avail | dlv | <-41.5, -22.8> | [-55.0, -9.0] | AGAINST | AGAINST | - | - | ns-after-Holm | ns-after-Holm |
| Qwen3.5-4B | off | v_plan | steer | mech | +9.6 | [0.7, 18.5] | FAV | FAV | - | - | ns-after-Holm | ns-after-Holm |
| Qwen3.5-4B | on | solve | steer | mech | +8.3 | [1.3, 15.3] | NS | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-4B | on | v_plan | avail | dlv | <+17.1, +20.4> | [4.1, 33.4] | FAV | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-4B | on | sim | steer | mech | +11.0 | [1.7, 20.3] | NS | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-9B | off | solve | avail | dlv | <+15.3, +48.0> | [1.1, 65.6] | FAV | FAV | ns-after-Holm | ns-after-Holm | ns-after-Holm | ns-after-Holm |
| Qwen3.5-9B | off | v_plan | avail | mech | +13.4 | [5.0, 21.9] | FAV | FAV | FAV | ns-after-Holm | ns-after-Holm | ns-after-Holm |
| Qwen3.5-9B | off | v_plan | steer | mech | +2.9 | [-0.6, 6.3] | FAV | NS | NS | NS | NS | NS |
| Qwen3.5-9B | on | solve | avail | dlv | <-19.7, -13.3> | [-31.7, -1.3] | UNDECIDED | AGAINST | - | - | - | ns-after-Holm |
| Qwen3.5-9B | on | solve | steer | mech | +15.3 | [6.0, 24.6] | NS | FAV | - | - | - | ns-after-Holm |
| Qwen3.5-9B | on | v_dom | steer | dlv | <-10.3, -9.4> | [-17.6, -2.2] | UNDECIDED | AGAINST | - | - | - | ns-after-Holm |
| Qwen3.5-9B | on | sim | steer | mech | +5.7 | [0.9, 10.4] | NS | FAV | - | - | - | ns-after-Holm |
| Gemma-26B | off | v_dom | avail | mech | +19.7 | [7.1, 32.4] | FAV | FAV | FAV | ns-after-Holm | ns-after-Holm | ns-after-Holm |
| Gemma-26B | off | v_dom | avail | dlv | <+15.6, +20.3> | [1.6, 32.9] | FAV | FAV | ns-after-Holm | ns-after-Holm | ns-after-Holm | ns-after-Holm |
| Gemma-26B | off | v_prob | avail | dlv | <+9.5, +25.0> | [0.9, 31.6] | UNDECIDED | FAV | ns-after-Holm | ns-after-Holm | ns-after-Holm | ns-after-Holm |
| Gemma-26B | on | v_dom | avail | dlv | <+17.2, +97.2> | [8.9, 100.2] | FAV | FAV | - | - | - | ns-after-Holm |
| Gemma-26B | on | v_plan | avail | mech | -9.7 | [-14.6, -4.7] | AGAINST | AGAINST | - | - | - | ns-after-Holm |
| Qwen3.6-35B | off | v_dom | avail | dlv | <+24.2, +31.4> | [11.8, 43.7] | FAV | FAV | FAV | FAV | FAV | ns-after-Holm |
| Qwen3.6-35B | off | v_plan | avail | mech | -8.7 | [-19.0, 1.5] | AGAINST | NS | NS | NS | NS | NS |
| Qwen3.6-35B | off | v_plan | steer | mech | +17.1 | [7.4, 26.8] | FAV | FAV | FAV | ns-after-Holm | ns-after-Holm | ns-after-Holm |
| Qwen3.6-35B | on | solve | steer | mech | +13.3 | [6.9, 19.8] | FAV | FAV | - | - | - | ns-after-Holm |
| Qwen3.6-35B | on | v_dom | avail | dlv | <+12.5, +25.8> | [3.8, 32.6] | UNDECIDED | FAV | - | - | - | ns-after-Holm |
| Qwen3.6-35B | on | v_plan | avail | mech | +13.8 | [6.1, 21.5] | FAV | FAV | - | - | - | ns-after-Holm |

## Table D. Family sizes and survival counts

| family | m | Bonferroni per-test alpha | two-sided z | clustered verdicts before | survive Holm | survive Bonferroni |
|---|---|---|---|---|---|---|
| H30_dlv | 30 | 1.67e-03 | 3.14 | 6 | 3 | 3 |
| H30_mech | 30 | 1.67e-03 | 3.14 | 19 | 19 | 17 |
| H60_both | 60 | 8.33e-04 | 3.34 | 25 | 19 | 19 |
| R100_off_both | 100 | 5.00e-04 | 3.48 | 40 | 28 | 27 |
| R200_all | 200 | 2.50e-04 | 3.66 | 89 | 60 | 59 |

## Table E. How large is the clustering really? (think=off, headline, mechanism layer)

Median and max design effect per clustering level over the 45 headline arm cells with a non-degenerate rate.

| clustering | cells | median deff | max deff | cells with deff > 2.7 |
|---|---|---|---|---|
| instance (3 wordings) | 38 | 2.04 | 2.7 | 1 |
| domain (k=20) | 38 | 2.79 | 78.4 | 20 |

