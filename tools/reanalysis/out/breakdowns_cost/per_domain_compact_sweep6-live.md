# Per-domain success (compact), sweep6-live, think off

Harness score % (tool-verified on tool arms). nt = no-tools, pl = tools-plain, st = tools-steered.

## solve (n = 15 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 13 | 40 |
| blocksworld | classical | 0 | 100 | 100 | 13 | 100 | 100 | 13 | 27 | 93 |
| depots | classical | 0 | 87 | 87 | 13 | 100 | 100 | 0 | 40 | 80 |
| gripper | classical | 33 | 100 | 100 | 33 | 100 | 100 | 27 | 60 | 100 |
| miconic | classical | 7 | 100 | 100 | 7 | 100 | 100 | 7 | 73 | 100 |
| parking | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 40 | 93 |
| rovers | classical | 0 | 100 | 100 | 0 | 100 | 100 | 7 | 40 | 60 |
| satellite | classical | 0 | 100 | 100 | 0 | 100 | 100 | 7 | 80 | 100 |
| tpp | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 47 | 87 |
| zenotravel | classical | 7 | 100 | 100 | 7 | 100 | 100 | 0 | 40 | 100 |
| block-grouping | numeric | 13 | 100 | 100 | 20 | 100 | 100 | 20 | 100 | 100 |
| counters | numeric | 7 | 100 | 100 | 13 | 100 | 100 | 13 | 93 | 100 |
| delivery | numeric | 7 | 100 | 100 | 20 | 100 | 100 | 0 | 7 | 87 |
| depot | numeric | 7 | 60 | 40 | 0 | 93 | 100 | 0 | 0 | 53 |
| drone | numeric | 0 | 100 | 100 | 13 | 47 | 60 | 20 | 80 | 93 |
| farmland | numeric | 7 | 100 | 100 | 7 | 100 | 100 | 20 | 80 | 100 |
| gardening | numeric | 27 | 100 | 100 | 20 | 100 | 100 | 7 | 87 | 100 |
| pogo_stick | numeric | 7 | 100 | 93 | 13 | 100 | 100 | 13 | 7 | 40 |
| sailing | numeric | 0 | 100 | 100 | 13 | 100 | 100 | 27 | 67 | 100 |
| zenotravel-numeric | numeric | 40 | 100 | 100 | 33 | 100 | 100 | 13 | 67 | 93 |

## validate_domain (n = 18 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 100 | 100 | 100 | 11 | 100 | 100 | 100 | 100 | 100 |
| blocksworld | classical | 100 | 100 | 100 | 17 | 100 | 100 | 83 | 100 | 100 |
| depots | classical | 72 | 100 | 100 | 39 | 100 | 100 | 94 | 100 | 100 |
| gripper | classical | 83 | 100 | 100 | 61 | 100 | 100 | 44 | 100 | 100 |
| miconic | classical | 83 | 100 | 100 | 61 | 100 | 100 | 89 | 100 | 100 |
| parking | classical | 83 | 100 | 100 | 17 | 100 | 100 | 44 | 100 | 100 |
| rovers | classical | 100 | 100 | 100 | 17 | 100 | 100 | 100 | 33 | 56 |
| satellite | classical | 100 | 100 | 94 | 100 | 100 | 100 | 83 | 100 | 100 |
| tpp | classical | 83 | 100 | 100 | 6 | 100 | 100 | 83 | 83 | 94 |
| zenotravel | classical | 83 | 100 | 100 | 17 | 100 | 100 | 83 | 100 | 100 |
| block-grouping | numeric | 17 | 94 | 100 | 17 | 100 | 100 | 33 | 100 | 100 |
| counters | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 89 | 100 | 100 |
| delivery | numeric | 50 | 94 | 89 | 17 | 100 | 100 | 83 | 94 | 100 |
| depot | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 100 | 100 | 100 |
| drone | numeric | 67 | 100 | 100 | 17 | 100 | 100 | 50 | 100 | 100 |
| farmland | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 33 | 100 | 100 |
| gardening | numeric | 28 | 100 | 94 | 17 | 100 | 100 | 11 | 100 | 100 |
| pogo_stick | numeric | 100 | 100 | 100 | 39 | 100 | 100 | 89 | 100 | 100 |
| sailing | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 78 | 100 | 100 |
| zenotravel-numeric | numeric | 61 | 100 | 100 | 17 | 100 | 100 | 33 | 100 | 100 |

## validate_problem (n = 30 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 70 | 100 | 100 | 70 | 100 | 100 | 63 | 93 | 97 |
| blocksworld | classical | 83 | 100 | 100 | 77 | 97 | 100 | 80 | 97 | 97 |
| depots | classical | 90 | 87 | 80 | 80 | 100 | 100 | 70 | 100 | 100 |
| gripper | classical | 70 | 100 | 97 | 77 | 93 | 90 | 77 | 90 | 90 |
| miconic | classical | 87 | 100 | 100 | 83 | 90 | 90 | 77 | 83 | 90 |
| parking | classical | 87 | 100 | 100 | 63 | 100 | 100 | 90 | 67 | 63 |
| rovers | classical | 87 | 100 | 100 | 73 | 93 | 100 | 77 | 87 | 100 |
| satellite | classical | 80 | 100 | 100 | 73 | 90 | 90 | 83 | 83 | 90 |
| tpp | classical | 73 | 100 | 100 | 70 | 93 | 90 | 70 | 93 | 100 |
| zenotravel | classical | 70 | 100 | 100 | 73 | 90 | 90 | 73 | 83 | 93 |
| block-grouping | numeric | 83 | 100 | 100 | 53 | 90 | 90 | 77 | 100 | 100 |
| counters | numeric | 73 | 100 | 100 | 60 | 100 | 100 | 70 | 100 | 100 |
| delivery | numeric | 70 | 100 | 100 | 57 | 90 | 90 | 67 | 97 | 100 |
| depot | numeric | 57 | 100 | 100 | 77 | 100 | 100 | 83 | 77 | 90 |
| drone | numeric | 90 | 100 | 100 | 67 | 97 | 100 | 87 | 100 | 100 |
| farmland | numeric | 87 | 100 | 100 | 87 | 100 | 100 | 80 | 100 | 100 |
| gardening | numeric | 63 | 90 | 93 | 50 | 77 | 47 | 80 | 100 | 100 |
| pogo_stick | numeric | 87 | 90 | 90 | 77 | 100 | 100 | 80 | 100 | 100 |
| sailing | numeric | 83 | 100 | 100 | 60 | 90 | 97 | 73 | 100 | 100 |
| zenotravel-numeric | numeric | 67 | 100 | 100 | 60 | 90 | 100 | 77 | 100 | 100 |

## validate_plan (n = 150 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 63 | 0 | 12 | 53 | 60 | 92 | 68 | 93 | 100 |
| blocksworld | classical | 100 | 46 | 100 | 89 | 100 | 100 | 99 | 88 | 100 |
| depots | classical | 70 | 0 | 50 | 63 | 100 | 100 | 85 | 100 | 100 |
| gripper | classical | 99 | 57 | 100 | 94 | 100 | 100 | 99 | 92 | 99 |
| miconic | classical | 94 | 44 | 100 | 93 | 99 | 100 | 94 | 42 | 100 |
| parking | classical | 97 | 10 | 100 | 80 | 97 | 100 | 87 | 71 | 68 |
| rovers | classical | 87 | 0 | 32 | 77 | 95 | 100 | 96 | 97 | 100 |
| satellite | classical | 97 | 21 | 100 | 83 | 80 | 96 | 98 | 54 | 100 |
| tpp | classical | 79 | 0 | 100 | 71 | 99 | 100 | 75 | 97 | 99 |
| zenotravel | classical | 92 | 20 | 100 | 85 | 100 | 100 | 92 | 79 | 100 |
| block-grouping | numeric | 81 | 0 | 99 | 73 | 80 | 80 | 87 | 64 | 87 |
| counters | numeric | 96 | 65 | 98 | 63 | 73 | 73 | 79 | 71 | 91 |
| delivery | numeric | 90 | 0 | 90 | 86 | 100 | 100 | 95 | 100 | 100 |
| depot | numeric | 77 | 0 | 51 | 61 | 100 | 100 | 78 | 94 | 100 |
| drone | numeric | 91 | 8 | 97 | 79 | 97 | 98 | 93 | 79 | 100 |
| farmland | numeric | 99 | 69 | 100 | 99 | 100 | 100 | 97 | 97 | 100 |
| gardening | numeric | 85 | 4 | 99 | 79 | 82 | 87 | 85 | 90 | 100 |
| pogo_stick | numeric | 94 | 0 | 99 | 97 | 98 | 100 | 93 | 93 | 99 |
| sailing | numeric | 81 | 10 | 89 | 75 | 90 | 90 | 84 | 42 | 99 |
| zenotravel-numeric | numeric | 93 | 1 | 99 | 84 | 100 | 100 | 96 | 93 | 100 |

## simulate (n = 15 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 0 | 93 | 100 | 0 | 100 | 100 | 0 | 100 | 100 |
| blocksworld | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 67 | 100 |
| depots | classical | 0 | 0 | 0 | 0 | 87 | 100 | 0 | 60 | 100 |
| gripper | classical | 0 | 100 | 100 | 0 | 87 | 100 | 0 | 73 | 100 |
| miconic | classical | 0 | 100 | 100 | 0 | 80 | 100 | 0 | 40 | 100 |
| parking | classical | 0 | 100 | 100 | 0 | 67 | 100 | 0 | 73 | 100 |
| rovers | classical | 0 | 87 | 87 | 0 | 73 | 100 | 0 | 93 | 93 |
| satellite | classical | 0 | 100 | 100 | 0 | 67 | 60 | 0 | 60 | 100 |
| tpp | classical | 0 | 100 | 100 | 0 | 47 | 60 | 0 | 67 | 93 |
| zenotravel | classical | 0 | 100 | 100 | 0 | 67 | 100 | 0 | 20 | 100 |
| block-grouping | numeric | 0 | 100 | 100 | 0 | 47 | 47 | 0 | 80 | 93 |
| counters | numeric | 0 | 80 | 67 | 0 | 13 | 20 | 0 | 27 | 53 |
| delivery | numeric | 0 | 93 | 100 | 0 | 73 | 87 | 0 | 100 | 100 |
| depot | numeric | 0 | 7 | 13 | 0 | 80 | 80 | 0 | 73 | 100 |
| drone | numeric | 0 | 100 | 100 | 0 | 60 | 80 | 0 | 73 | 100 |
| farmland | numeric | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 80 | 100 |
| gardening | numeric | 0 | 100 | 100 | 0 | 33 | 60 | 0 | 87 | 100 |
| pogo_stick | numeric | 0 | 100 | 100 | 0 | 67 | 100 | 0 | 80 | 93 |
| sailing | numeric | 0 | 80 | 80 | 0 | 80 | 80 | 0 | 47 | 93 |
| zenotravel-numeric | numeric | 0 | 73 | 100 | 0 | 67 | 100 | 0 | 80 | 100 |

