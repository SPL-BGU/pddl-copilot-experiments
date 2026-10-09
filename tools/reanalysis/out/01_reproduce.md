| check | got | frozen | match |
|---|---|---|---|
| Gemma vplan plain: called / n | (622, 3000) | (622, 3000) | yes |
| Gemma vplan steered: called / n | (2808, 3000) | (2808, 3000) | yes |
| Gemma vplan plain: tool-verified ok | 617 | 617 | yes |
| Gemma vplan plain: successes without a call | 0 | 0 | yes |
| Gemma vplan success plain -> steered (3 dp) | (0.206, 0.926) | (0.206, 0.926) | yes |
| Gemma vplan delivered bound plain <low, high> %, censored | (6.6, 99.6, 2790) | (6.6, 99.6, 2790) | yes |
| unaided simulate strict success / n (10 cells) | (0, 3000) | (0, 3000) | yes |
| unaided simulate failure mix | (1772, 1202, 26) | (1772, 1202, 26) | yes |
| 9B vdomain tl-neut delivered (ok, censored, n) | (359, 1, 360) | (359, 1, 360) | yes |
| pooled_e2e_table.csv agreement, think=off (75 cells): mismatches | 0 | 0 | yes |
| contamination pooled canonical/anonymized Qwen3.5-0.8B | (45.9, 45.8) | (45.9, 45.8) | yes |
| contamination pooled canonical/anonymized Qwen3.5-4B | (58.2, 56.1) | (58.2, 56.1) | yes |
| contamination pooled canonical/anonymized Qwen3.5-9B | (63.8, 64.2) | (63.8, 64.2) | yes |
| contamination pooled canonical/anonymized Gemma-26B | (74.3, 75.2) | (74.3, 75.2) | yes |
| contamination pooled canonical/anonymized Qwen3.6-35B | (75.7, 74.8) | (75.7, 74.8) | yes |
