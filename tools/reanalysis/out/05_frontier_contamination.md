# Frontier contamination: Claude Sonnet 4.6, anonymized minus canonical, no-tools

Rows: canonical 4560, anonymized 4560, shared keys 4560.

## (a) Equivalence test, T7 method (simulate left out)

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 4.6 solve | 300 | 28.7 | 28.3 | -0.33 | [-10.59, +9.93] | domain (k=20) | [-9.67, +9.00] | 10.26 | 0.221 | criterion not met (unresolved) |
| Sonnet 4.6 v_dom | 360 | 93.6 | 91.7 | -1.94 | [-4.67, +0.78] | domain (k=20) | [-4.72, +0.28] | 2.72 | 0.034 | criterion met (ceiling: low information) |
| Sonnet 4.6 v_prob | 600 | 89.7 | 90.5 | +0.83 | [-1.33, +3.00] | domain (k=20) | [-1.17, +2.83] | 2.17 | 0.002 | criterion met |
| Sonnet 4.6 v_plan | 3000 | 97.3 | 97.3 | +0.03 | [-1.17, +1.24] | domain (k=20) | [-1.13, +1.13] | 1.20 | 0.000 | criterion met (ceiling: low information) |
| Sonnet 4.6 pooled (4 exact tasks) | 4260 | 91.1 | 91.0 | -0.05 | [-0.99, +0.89] | domain (k=20) | [-0.87, +0.85] | 0.94 | 0.000 | criterion met (ceiling: low information) |

Single answers whose outcome differs between the corpora (same trial key):

| cell | pairs | right -> wrong | wrong -> right | changed |
|---|---|---|---|---|
| solve | 300 | 38 | 37 | 75/300 = 25.0% |
| validate_domain | 360 | 10 | 3 | 13/360 = 3.6% |
| validate_problem | 600 | 14 | 19 | 33/600 = 5.5% |
| validate_plan | 3000 | 57 | 58 | 115/3000 = 3.8% |
| pooled (4 exact tasks) | 4260 | 119 | 117 | 236/4260 = 5.5% |

## (b) How often single answers change, against two baselines

| what changes between the two answers | task | corpus | answer pairs that differ |
|---|---|---|---|
| nothing (identical prompt) | validate_plan, valid plans | canonical | 34/2988 = 1.1% |
| nothing (identical prompt) | validate_domain, valid domains | canonical | 0/600 = 0.0% |
| nothing (identical prompt) | validate_plan, valid plans | anonymized | 86/2988 = 2.9% |
| nothing (identical prompt) | validate_domain, valid domains | anonymized | 16/600 = 2.7% |
| the wording (same names) | solve | canonical | 24/300 = 8.0% |
| the wording (same names) | solve | anonymized | 44/300 = 14.7% |
| the names (same wording) | solve | canonical vs anonymized | 75/300 = 25.0% |

solve problems whose number of solved wordings (0 to 3) changes under renaming: 39 of 100.

## (c) solve per domain (15 trials per domain and corpus)

| domain | canonical solved | anonymized solved | right -> wrong | wrong -> right | exact McNemar p | Holm p (m=20) |
|---|---|---|---|---|---|---|
| blocksworld | 11 | 3 | 8 | 0 | 0.0078 | 0.156 |
| miconic | 15 | 8 | 7 | 0 | 0.0156 | 0.297 |
| sailing | 7 | 0 | 7 | 0 | 0.0156 | 0.297 |
| tpp | 0 | 6 | 0 | 6 | 0.0312 | 0.531 |
| farmland | 3 | 8 | 0 | 5 | 0.0625 | 1.000 |
| gardening | 6 | 11 | 1 | 6 | 0.1250 | 1.000 |
| satellite | 3 | 8 | 1 | 6 | 0.1250 | 1.000 |
| depots | 4 | 2 | 2 | 0 | 0.5000 | 1.000 |
| pogo_stick | 0 | 2 | 0 | 2 | 0.5000 | 1.000 |
| zenotravel-numeric | 9 | 11 | 0 | 2 | 0.5000 | 1.000 |
| counters | 4 | 2 | 3 | 1 | 0.6250 | 1.000 |
| delivery | 4 | 2 | 3 | 1 | 0.6250 | 1.000 |
| zenotravel | 5 | 3 | 5 | 3 | 0.7266 | 1.000 |
| barman | 0 | 0 | 0 | 0 | 1.0000 | 1.000 |
| block-grouping | 0 | 0 | 0 | 0 | 1.0000 | 1.000 |
| depot | 0 | 0 | 0 | 0 | 1.0000 | 1.000 |
| drone | 6 | 7 | 0 | 1 | 1.0000 | 1.000 |
| gripper | 9 | 10 | 1 | 2 | 1.0000 | 1.000 |
| parking | 0 | 1 | 0 | 1 | 1.0000 | 1.000 |
| rovers | 0 | 1 | 0 | 1 | 1.0000 | 1.000 |

