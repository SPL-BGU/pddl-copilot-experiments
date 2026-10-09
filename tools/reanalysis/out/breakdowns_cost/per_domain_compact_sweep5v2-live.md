# Per-domain success (compact), sweep5v2-live, think off

Harness score % (tool-verified on tool arms). nt = no-tools, pl = tools-plain, st = tools-steered.

## solve (n = 15 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 33 | 67 |
| blocksworld | classical | 7 | 100 | 100 | 13 | 100 | 100 | 13 | 53 | 100 |
| depots | classical | 7 | 100 | 100 | 7 | 100 | 100 | 7 | 60 | 93 |
| gripper | classical | 33 | 100 | 100 | 33 | 100 | 100 | 7 | 53 | 100 |
| miconic | classical | 13 | 100 | 100 | 20 | 100 | 100 | 13 | 67 | 100 |
| parking | classical | 0 | 100 | 100 | 7 | 100 | 100 | 7 | 53 | 80 |
| rovers | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 47 | 73 |
| satellite | classical | 0 | 100 | 100 | 7 | 100 | 100 | 13 | 67 | 100 |
| tpp | classical | 7 | 93 | 100 | 0 | 100 | 100 | 0 | 47 | 87 |
| zenotravel | classical | 0 | 100 | 100 | 7 | 100 | 100 | 7 | 80 | 100 |
| block-grouping | numeric | 27 | 100 | 100 | 27 | 100 | 100 | 20 | 93 | 100 |
| counters | numeric | 20 | 100 | 100 | 0 | 100 | 100 | 13 | 100 | 100 |
| delivery | numeric | 7 | 93 | 93 | 13 | 100 | 100 | 7 | 73 | 100 |
| depot | numeric | 7 | 100 | 100 | 0 | 100 | 100 | 0 | 27 | 73 |
| drone | numeric | 7 | 100 | 100 | 20 | 87 | 100 | 7 | 80 | 80 |
| farmland | numeric | 7 | 100 | 100 | 0 | 100 | 100 | 7 | 87 | 100 |
| gardening | numeric | 7 | 100 | 100 | 27 | 100 | 100 | 27 | 80 | 100 |
| pogo_stick | numeric | 0 | 100 | 80 | 13 | 100 | 100 | 13 | 53 | 87 |
| sailing | numeric | 0 | 100 | 100 | 7 | 100 | 100 | 13 | 67 | 100 |
| zenotravel-numeric | numeric | 7 | 100 | 100 | 13 | 100 | 100 | 13 | 40 | 100 |

## validate_domain (n = 18 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 94 | 100 | 100 | 17 | 100 | 100 | 83 | 100 | 100 |
| blocksworld | classical | 100 | 100 | 100 | 17 | 100 | 100 | 56 | 100 | 100 |
| depots | classical | 89 | 100 | 100 | 17 | 100 | 100 | 89 | 100 | 100 |
| gripper | classical | 83 | 100 | 100 | 44 | 100 | 100 | 72 | 100 | 100 |
| miconic | classical | 83 | 100 | 100 | 44 | 100 | 100 | 83 | 100 | 100 |
| parking | classical | 83 | 100 | 100 | 67 | 100 | 100 | 78 | 100 | 100 |
| rovers | classical | 100 | 100 | 100 | 17 | 100 | 100 | 100 | 89 | 100 |
| satellite | classical | 100 | 83 | 83 | 100 | 100 | 100 | 83 | 100 | 100 |
| tpp | classical | 83 | 100 | 100 | 17 | 100 | 100 | 94 | 100 | 100 |
| zenotravel | classical | 83 | 100 | 100 | 17 | 100 | 100 | 83 | 100 | 100 |
| block-grouping | numeric | 17 | 100 | 100 | 17 | 100 | 100 | 17 | 100 | 100 |
| counters | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 72 | 100 | 100 |
| delivery | numeric | 61 | 83 | 89 | 11 | 100 | 100 | 78 | 89 | 94 |
| depot | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 100 | 100 | 100 |
| drone | numeric | 33 | 100 | 100 | 17 | 100 | 100 | 28 | 100 | 100 |
| farmland | numeric | 100 | 100 | 100 | 11 | 100 | 100 | 17 | 100 | 100 |
| gardening | numeric | 39 | 89 | 94 | 17 | 100 | 100 | 44 | 100 | 100 |
| pogo_stick | numeric | 83 | 100 | 100 | 17 | 100 | 100 | 67 | 100 | 100 |
| sailing | numeric | 94 | 94 | 100 | 17 | 100 | 100 | 72 | 100 | 100 |
| zenotravel-numeric | numeric | 28 | 100 | 100 | 17 | 100 | 100 | 39 | 100 | 100 |

## validate_problem (n = 30 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 50 | 100 | 100 | 67 | 93 | 97 | 67 | 97 | 97 |
| blocksworld | classical | 83 | 100 | 100 | 77 | 100 | 100 | 80 | 97 | 100 |
| depots | classical | 60 | 100 | 100 | 73 | 100 | 100 | 60 | 100 | 100 |
| gripper | classical | 87 | 100 | 100 | 83 | 97 | 93 | 83 | 90 | 90 |
| miconic | classical | 80 | 100 | 100 | 87 | 90 | 90 | 73 | 90 | 90 |
| parking | classical | 97 | 100 | 100 | 73 | 100 | 100 | 90 | 100 | 100 |
| rovers | classical | 60 | 97 | 100 | 30 | 100 | 100 | 50 | 97 | 97 |
| satellite | classical | 80 | 100 | 100 | 73 | 90 | 80 | 83 | 93 | 97 |
| tpp | classical | 70 | 100 | 100 | 67 | 97 | 93 | 70 | 97 | 100 |
| zenotravel | classical | 70 | 100 | 100 | 63 | 90 | 90 | 83 | 97 | 97 |
| block-grouping | numeric | 70 | 100 | 100 | 43 | 90 | 90 | 70 | 100 | 100 |
| counters | numeric | 83 | 100 | 100 | 37 | 100 | 100 | 70 | 100 | 100 |
| delivery | numeric | 73 | 100 | 100 | 60 | 90 | 90 | 70 | 97 | 90 |
| depot | numeric | 47 | 100 | 100 | 67 | 100 | 100 | 80 | 90 | 90 |
| drone | numeric | 83 | 100 | 100 | 67 | 100 | 100 | 93 | 97 | 100 |
| farmland | numeric | 90 | 100 | 100 | 77 | 100 | 100 | 87 | 100 | 100 |
| gardening | numeric | 77 | 100 | 100 | 57 | 90 | 43 | 77 | 100 | 100 |
| pogo_stick | numeric | 90 | 97 | 100 | 73 | 97 | 63 | 80 | 100 | 100 |
| sailing | numeric | 87 | 100 | 100 | 67 | 90 | 80 | 73 | 100 | 100 |
| zenotravel-numeric | numeric | 60 | 100 | 100 | 73 | 90 | 93 | 73 | 97 | 100 |

## validate_plan (n = 150 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 59 | 0 | 18 | 57 | 97 | 99 | 82 | 95 | 100 |
| blocksworld | classical | 100 | 80 | 100 | 97 | 100 | 100 | 100 | 88 | 100 |
| depots | classical | 91 | 0 | 100 | 65 | 100 | 100 | 97 | 99 | 99 |
| gripper | classical | 95 | 67 | 98 | 83 | 100 | 100 | 99 | 95 | 99 |
| miconic | classical | 93 | 66 | 99 | 93 | 100 | 100 | 94 | 31 | 100 |
| parking | classical | 89 | 3 | 100 | 81 | 99 | 100 | 87 | 93 | 100 |
| rovers | classical | 91 | 0 | 72 | 78 | 99 | 100 | 94 | 82 | 100 |
| satellite | classical | 93 | 4 | 99 | 96 | 87 | 93 | 97 | 46 | 100 |
| tpp | classical | 77 | 9 | 100 | 67 | 100 | 100 | 78 | 99 | 100 |
| zenotravel | classical | 92 | 14 | 98 | 87 | 100 | 100 | 94 | 91 | 100 |
| block-grouping | numeric | 85 | 0 | 100 | 81 | 81 | 87 | 87 | 66 | 97 |
| counters | numeric | 80 | 63 | 95 | 65 | 63 | 65 | 76 | 61 | 96 |
| delivery | numeric | 85 | 0 | 99 | 92 | 100 | 100 | 95 | 100 | 100 |
| depot | numeric | 79 | 0 | 82 | 53 | 97 | 100 | 83 | 93 | 100 |
| drone | numeric | 95 | 11 | 98 | 73 | 90 | 89 | 93 | 99 | 100 |
| farmland | numeric | 99 | 70 | 100 | 95 | 91 | 100 | 99 | 98 | 100 |
| gardening | numeric | 86 | 4 | 100 | 67 | 100 | 99 | 88 | 89 | 100 |
| pogo_stick | numeric | 86 | 0 | 100 | 95 | 68 | 100 | 98 | 86 | 98 |
| sailing | numeric | 86 | 9 | 97 | 81 | 90 | 90 | 87 | 41 | 97 |
| zenotravel-numeric | numeric | 94 | 13 | 96 | 88 | 100 | 100 | 90 | 93 | 99 |

## simulate (n = 15 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 0 | 100 | 100 | 0 | 47 | 67 | 0 | 100 | 100 |
| blocksworld | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 93 | 100 |
| depots | classical | 0 | 100 | 100 | 0 | 80 | 100 | 0 | 87 | 100 |
| gripper | classical | 0 | 100 | 100 | 0 | 87 | 100 | 0 | 80 | 100 |
| miconic | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 40 | 100 |
| parking | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 67 | 100 |
| rovers | classical | 0 | 93 | 100 | 0 | 67 | 93 | 0 | 100 | 93 |
| satellite | classical | 0 | 73 | 73 | 0 | 47 | 73 | 0 | 67 | 100 |
| tpp | classical | 0 | 93 | 100 | 0 | 27 | 47 | 0 | 73 | 100 |
| zenotravel | classical | 0 | 100 | 87 | 0 | 73 | 100 | 0 | 20 | 100 |
| block-grouping | numeric | 0 | 100 | 100 | 0 | 67 | 67 | 0 | 73 | 100 |
| counters | numeric | 0 | 73 | 53 | 0 | 13 | 20 | 0 | 53 | 73 |
| delivery | numeric | 0 | 100 | 100 | 0 | 80 | 100 | 0 | 100 | 100 |
| depot | numeric | 0 | 100 | 100 | 0 | 67 | 93 | 0 | 80 | 100 |
| drone | numeric | 0 | 73 | 53 | 0 | 53 | 60 | 0 | 93 | 100 |
| farmland | numeric | 0 | 100 | 100 | 0 | 93 | 100 | 0 | 73 | 100 |
| gardening | numeric | 0 | 80 | 87 | 0 | 67 | 80 | 0 | 67 | 93 |
| pogo_stick | numeric | 0 | 60 | 60 | 0 | 67 | 80 | 0 | 73 | 80 |
| sailing | numeric | 0 | 93 | 100 | 0 | 80 | 80 | 0 | 67 | 100 |
| zenotravel-numeric | numeric | 0 | 93 | 100 | 0 | 67 | 100 | 0 | 87 | 100 |

