# Fixture facts (measured from domains/)

## 1. Inventory

| item | count |
|---|---|
| domains | 20 |
| valid domain files | 20 |
| invalid domain files | 20 |
| valid problems | 100 |
| invalid problems | 100 |
| valid plan files | 500 |
| invalid plan files | 500 |

## 2. What the invalid fixtures contain (structural classification against the source file)

Invalid domains (1 per domain, 20 total):

| error type | files |
|---|---|
| one extra closing paren | 9 |
| undeclared predicate used in a precondition or effect (inherited) | 5 |
| missing closing paren(s) | 3 |
| '-' dropped from a typed parameter list (inherited) | 2 |
| :predicates block removed (generator) | 1 |

Invalid problems (5 per domain, 100 total; every one is a mutation of that domain's p01.pddl):

| error type | files | classical | numeric |
|---|---|---|---|
| undeclared object in :init | 20 | 10 | 10 |
| undefined predicate in :goal | 20 | 10 | 10 |
| one extra closing paren | 18 | 9 | 9 |
| missing :goal | 13 | 6 | 7 |
| missing :goal + one extra closing paren | 13 | 8 | 5 |
| inherited hand-made n01 (see list) | 7 | 4 | 3 |
| :objects block removed | 7 | 2 | 5 |
| :init block removed | 2 | 1 | 1 |

Invalid plans (5 per problem, 500 total; every one is a mutation of that problem's v1 plan):

| error type | files |
|---|---|
| one mid-plan step dropped | 290 |
| tail truncated (-1) | 90 |
| first two arguments swapped in one step | 74 |
| one step duplicated | 17 |
| inherited hand-made b1 plan (shortened and/or altered) | 9 |
| tail truncated (-2) | 8 |
| tail truncated (-3) | 4 |
| tail truncated (-4) | 4 |
| tail truncated (-5) | 3 |
| tail truncated (-10) | 1 |

Same, tail truncations merged, by track:

| error type | classical | numeric |
|---|---|---|
| first two arguments swapped in one step | 41 | 33 |
| inherited hand-made b1 plan (shortened and/or altered) | 5 | 4 |
| one mid-plan step dropped | 156 | 134 |
| one step duplicated | 3 | 14 |
| tail truncated | 45 | 65 |

## 3. Sizes

| quantity | classical (10 domains, 50 problems) | numeric (10 domains, 50 problems) | all |
|---|---|---|---|
| declared objects per valid problem | min 3 / q1 7.25 / median 11.5 / q3 16.75 / max 24 (mean 11.9, n=50) | min 2 / q1 3 / median 5 / q3 15 / max 35 (mean 10.4, n=50) | min 2 / q1 5 / median 9 / q3 16 / max 35 (mean 11.2, n=100) |
| reference plan length, steps (v1 plan) | min 2 / q1 6 / median 10 / q3 15.75 / max 65 (mean 14.5, n=50) | min 3 / q1 7 / median 14.5 / q3 32.5 / max 110 (mean 24.3, n=50) | min 2 / q1 6 / median 11.5 / q3 25.5 / max 110 (mean 19.4, n=100) |
| domain file size, characters | min 984 / q1 1253.25 / median 1648 / q3 2172.25 / max 5542 (mean 2160.8, n=10) | min 686 / q1 1618.25 / median 2002 / q3 2579.5 / max 3779 (mean 2130.4, n=10) | min 686 / q1 1447.75 / median 1812 / q3 2384.5 / max 5542 (mean 2145.6, n=20) |
| actions per domain | min 3 / q1 4 / median 4.5 / q3 5 / max 12 (mean 5.5, n=10) | min 2 / q1 4.25 / median 5 / q3 7.75 / max 10 (mean 5.8, n=10) | min 2 / q1 4 / median 5 / q3 7.25 / max 12 (mean 5.7, n=20) |
| distinct files among the 5 valid plans of a problem | {1: 49, 2: 1} | {1: 50} |  |

Invalid plan length minus its v1 plan length (steps): -99: 1, -61: 1, -28: 1, -25: 1, -18: 1, -10: 2, -5: 3, -4: 4, -3: 6, -2: 8, -1: 380, +0: 75, +1: 17

| domain | track | domain chars | actions | objects (min-max over p01..p05) | plan length (min-max) |
|---|---|---|---|---|---|
| barman | classical | 5542 | 12 | 13-20 | 14-65 |
| blocksworld | classical | 1164 | 4 | 3-6 | 2-16 |
| depots | classical | 1521 | 5 | 9-24 | 5-22 |
| gripper | classical | 984 | 3 | 7-19 | 3-14 |
| miconic | classical | 1003 | 4 | 3-7 | 3-10 |
| parking | classical | 1852 | 4 | 6-10 | 3-7 |
| rovers | classical | 3967 | 9 | 11-19 | 12-34 |
| satellite | classical | 1717 | 5 | 9-21 | 6-15 |
| tpp | classical | 2279 | 4 | 8-18 | 13-36 |
| zenotravel | classical | 1579 | 5 | 12-18 | 4-10 |
| block-grouping | numeric | 1556 | 4 | 5-5 | 10-36 |
| counters | numeric | 1228 | 4 | 3-5 | 8-56 |
| delivery | numeric | 2185 | 5 | 13-22 | 14-46 |
| depot | numeric | 1819 | 5 | 9-21 | 5-62 |
| drone | numeric | 2701 | 8 | 2-18 | 5-110 |
| farmland | numeric | 686 | 2 | 4-15 | 3-19 |
| gardening | numeric | 3779 | 10 | 3-3 | 5-86 |
| pogo_stick | numeric | 3330 | 7 | 35-35 | 10-23 |
| sailing | numeric | 1805 | 8 | 3-3 | 4-100 |
| zenotravel-numeric | numeric | 2215 | 5 | 4-7 | 3-14 |

Prompt size in characters (system + user, wording v11, valid fixtures, built with `pddl_eval.runner.build_messages`):

| task | characters |
|---|---|
| solve | min 1510 / q1 2472.75 / median 3065 / q3 4418 / max 8052 (mean 3451.2, n=100) |
| validate_domain | min 1044 / q1 1805.75 / median 2170 / q3 2742.5 / max 5900 (mean 2503.6, n=100) |
| validate_problem | min 1531 / q1 2493.75 / median 3086 / q3 4439 / max 8073 (mean 3472.2, n=100) |
| validate_plan | min 1678 / q1 2651.25 / median 3454.5 / q3 5158.25 / max 9810 (mean 4031.9, n=100) |
| simulate | min 1977 / q1 2950.25 / median 3753.5 / q3 5457.25 / max 10109 (mean 4330.9, n=100) |

## 4. Difficulty-bin cut points (recomputed as rq_deck.py:493-512)

Rows = the three headline models, think off, arms no-tools and tools-steered (equal weight per instance x wording). Bins: low = value <= c1, mid = c1 < value <= c2, high = value > c2.

| bin variable | task | low bin | mid bin | high bin | rows per bin (both arms, 3 models) | value range |
|---|---|---|---|---|---|---|
| plan length | solve | <= 8 | 9 to 19 | > 19 | 648 / 558 / 594 | 2 to 110 |
| plan length | validate_plan | <= 8 | 9 to 19 | > 19 | 3240 / 2790 / 2970 | 2 to 110 |
| plan length | simulate | <= 8 | 9 to 19 | > 19 | 648 / 558 / 594 | 2 to 110 |
| object count | solve | <= 6 | 7 to 14 | > 14 | 702 / 522 / 576 | 2 to 35 |
| object count | validate_plan | <= 6 | 7 to 14 | > 14 | 3510 / 2610 / 2880 | 2 to 35 |
| object count | validate_problem | <= 5 | 6 to 13 | > 13 | 1152 / 1206 / 1080 | 2 to 35 |
| object count | simulate | <= 6 | 7 to 14 | > 14 | 702 / 522 / 576 | 2 to 35 |

