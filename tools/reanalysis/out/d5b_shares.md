# D5b ground truth: Fast Downward solved shares

Source: `<work>/runs/fd_120s.jsonl` and `fd_1800s.jsonl` (default work folder `external/d5b-work`, gitignored), printed by `python -m tools.d5b.shares`.

## Solved within 120 s (plan found and VAL-valid)

| domain | tier | lazy_greedy_cea | lazy_greedy_ff | astar_lmcut | any strategy |
|---|---|---|---|---|---|
| blocksworld | easy | 10/10 (100%) | 10/10 (100%) | 4/10 (40%) | 10/10 (100%) |
| blocksworld | medium | 6/10 (60%) | 6/10 (60%) | 0/10 (0%) | 6/10 (60%) |
| blocksworld | hard | 0/10 (0%) | 0/10 (0%) | 0/10 (0%) | 0/10 (0%) |
| miconic | easy | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) |
| miconic | medium | 10/10 (100%) | 10/10 (100%) | 3/10 (30%) | 10/10 (100%) |
| miconic | hard | 4/10 (40%) | 10/10 (100%) | 1/10 (10%) | 10/10 (100%) |
| rovers | easy | 10/10 (100%) | 10/10 (100%) | 5/10 (50%) | 10/10 (100%) |
| rovers | medium | 5/10 (50%) | 8/10 (80%) | 0/10 (0%) | 8/10 (80%) |
| rovers | hard | 1/10 (10%) | 1/10 (10%) | 0/10 (0%) | 1/10 (10%) |
| satellite | easy | 10/10 (100%) | 10/10 (100%) | 8/10 (80%) | 10/10 (100%) |
| satellite | medium | 10/10 (100%) | 10/10 (100%) | 1/10 (10%) | 10/10 (100%) |
| satellite | hard | 10/10 (100%) | 9/10 (90%) | 0/10 (0%) | 10/10 (100%) |
| all four | easy | 40/40 (100%) | 40/40 (100%) | 27/40 (68%) | 40/40 (100%) |
| all four | medium | 31/40 (78%) | 34/40 (85%) | 4/40 (10%) | 34/40 (85%) |
| all four | hard | 15/40 (38%) | 20/40 (50%) | 1/40 (2%) | 21/40 (52%) |

## Solved within 1800 s (plan found and VAL-valid)

| domain | tier | lazy_greedy_cea | lazy_greedy_ff | astar_lmcut | any strategy |
|---|---|---|---|---|---|
| blocksworld | easy | 10/10 (100%) | 10/10 (100%) | 5/10 (50%) | 10/10 (100%) |
| blocksworld | medium | 9/10 (90%) | 6/10 (60%) | 0/10 (0%) | 9/10 (90%) |
| blocksworld | hard | 0-5/10 (0-50%, 5 pending) | 0-5/10 (0-50%, 5 pending) | 0-5/10 (0-50%, 5 pending) | 0-5/10 (0-50%, 5 pending) |
| miconic | easy | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) |
| miconic | medium | 10/10 (100%) | 10/10 (100%) | 3/10 (30%) | 10/10 (100%) |
| miconic | hard | 4-10/10 (40-100%, 6 pending) | 10/10 (100%) | 2-8/10 (20-80%, 6 pending) | 10/10 (100%) |
| rovers | easy | 10/10 (100%) | 10/10 (100%) | 5/10 (50%) | 10/10 (100%) |
| rovers | medium | 9/10 (90%) | 10/10 (100%) | 0/10 (0%) | 10/10 (100%) |
| rovers | hard | 2-8/10 (20-80%, 6 pending) | 2-8/10 (20-80%, 6 pending) | 0-6/10 (0-60%, 6 pending) | 2-8/10 (20-80%, 6 pending) |
| satellite | easy | 10/10 (100%) | 10/10 (100%) | 8/10 (80%) | 10/10 (100%) |
| satellite | medium | 10/10 (100%) | 10/10 (100%) | 1/10 (10%) | 10/10 (100%) |
| satellite | hard | 10/10 (100%) | 9-10/10 (90-100%, 1 pending) | 0-6/10 (0-60%, 6 pending) | 10/10 (100%) |
| all four | easy | 40/40 (100%) | 40/40 (100%) | 28/40 (70%) | 40/40 (100%) |
| all four | medium | 38/40 (95%) | 36/40 (90%) | 4/40 (10%) | 39/40 (98%) |
| all four | hard | 16-33/40 (40-82%, 17 pending) | 21-33/40 (52-82%, 12 pending) | 2-25/40 (5-62%, 23 pending) | 22-33/40 (55-82%, 11 pending) |

## Checks

- 120 s pass: 360 runs; statuses {'solved': 212, 'timeout': 148}; plans rejected by KCL VAL: 0; plans with no KCL VAL verdict yet: 0; VAL plan size differs from the plan length: 0; solved runs that took over half the limit: 5
- 120 s pass, pddl-pyvalidator 0.1.6 (the harness grader): run on 208 of 212 plans; agrees with KCL VAL on 208 of 208 checked by both; slowest pyval check 1286 s for a 537-step plan (rovers/hard/p01.pddl, lazy_greedy_cea)
- 1800 s pass: 96 runs; statuses {'solved': 13, 'timeout': 83}; plans rejected by KCL VAL: 0; plans with no KCL VAL verdict yet: 0; VAL plan size differs from the plan length: 0; solved runs that took over half the limit: 1
- 1800 s pass, pddl-pyvalidator 0.1.6 (the harness grader): run on 0 of 13 plans; agrees with KCL VAL on 0 of 0 checked by both
- pairs pending within 1800 s (unsolved at 120 s and not yet run at 1800 s, or no VAL verdict yet): 52
