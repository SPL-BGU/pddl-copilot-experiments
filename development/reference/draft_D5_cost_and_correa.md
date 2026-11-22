# Draft: D5 frontier cost (itemised) and the Corrêa et al. facts

*Agent research, 2026-11-09. Estimate only: nothing spent. Prices from the claude-api skill and the live pricing page; token counts measured on the frontier corpora on disk. For Omer to approve the pilot spend before any API call.*

> ANSWER (approve the 20-key thinking pilot, about $1.50 to $10 with the Batch API, hard cap $38.59 at list price? yes / no / change):

# Corrêa et al. findings and itemised cost for the approved frontier runs (estimate only, nothing spent)

Grand total for all required lines: **about $102 (low), $204 (mid) or $459 (high) with the Batch API**, or $175, $379 and $889 at list price. A 20-key pilot to measure thinking tokens costs **$1.47 to $9.87** with the Batch API, with a hard cap of $38.59. I sent no API calls and did not touch the repo. Scratch files are under `/private/tmp/claude-501/`.

## Part 1. Corrêa, Pereira, Seipp (arXiv:2511.09378)

**The paper.** v1 came out on 2025-11-12 under the title "The 2025 Planning Performance of Frontier Large Language Models". v2 came out on 2026-05-15 as "Frontier Large Language Models Rival State-of-the-Art Planners". Seipp's lab page also lists a 2026 Communications of the ACM version, "Frontier LLMs Are Becoming Competitive with State-of-the-Art Planners", which links to v2.
- Abstract: https://arxiv.org/abs/2511.09378
- HTML: https://arxiv.org/html/2511.09378v2
- Lab page: https://mrlab.ai/jendrik-seipp/

### (a) The exact prompt
It is in the v2 TeX source as `prompt.txt` (saved at `(prompt text: Corrêa et al. v2 TeX source, prompt.txt; to be vendored with a hash when D5e is built)`). There is one user prompt and no system prompt. Its order is:
1. The task description: "You are a highly-skilled professor in AI planning searching a plan for a PDDL task from the domain <domain>X</domain>. ..."
2. The target domain file and instance file.
3. The Gripper example: domain, instance and plan.
4. The Logistics example: domain, instance and plan.
5. "Provide only the plan for the given instance. Here is a checklist to help you with your task:" followed by four items:
   - The plan uses the same format as the examples.
   - The plan goes inside `<plan>...</plan>` tags.
   - Action names and parameter counts must come from the domain.
   - The plan must be valid and end in a goal state.

Only the domain name, the domain file and the instance file change between tasks. Because the target files come before the examples, the shared example text cannot be served from the prompt cache as the prompt stands.

**Which example files they used.** The paper shortens the examples with "[...]", so I identified them by problem name:
- Gripper is `strips-gripper-x-20`, which is IPC 1998 gripper `prob20` (42 balls). The optimal plan is 125 actions.
- Logistics is `strips-log-y-5`, which is IPC 1998 logistics `prob35`. Our planner found a 30-step optimal plan. It starts with the same two actions their prompt shows.
- Both files come from https://github.com/AI-Planning/classical-domains.

**Our gripper clashes with their example.** Our `domains/classical/gripper` is also called `gripper-strips`, but it is a typed multi-robot version (`move ?r ?from ?to`). Their example is the untyped classic. On our 5 gripper problems, the 2-shot prompt would show a different domain under the same name.

### (b) What they have released
- **The 360 tasks, the obfuscated copies and the LLM plans are not released.** v2 says: "will be made publicly available online upon acceptance." I found no GitHub or Zenodo entry, and the lab page lists only the preprint.
- **No code or data licence is given.** The only licence is arXiv's perpetual non-exclusive licence, which covers the paper.
- **How they built the tasks:** 45 new tasks per domain, "using the IPC test set's parameter distributions". No generator command is named.
- **Their 8 domains:** Blocksworld, Childsnack, Floortile, Miconic, Rovers, Sokoban, Spanner, Transport.
- **Obfuscation:** every action, predicate and object name is replaced with a random string.

### (c) The earlier paper the prompt comes from
- Corrêa, Pereira, Seipp, "Classical Planning with LLM-Generated Heuristics: Challenging the State of the Art with Python Code", NeurIPS 2025: https://arxiv.org/abs/2503.18809
- Its code and data are on Zenodo under CC-BY-4.0: https://doi.org/10.5281/zenodo.17400964 (concept DOI 10.5281/zenodo.17400963). It is one 200 MB zip.
- My download stalled at 15 of 200 MB, so I did not inspect it. The same prompt is in that paper's TeX source as `prompts/end-to-end-bw.txt`.

### (d) Their generation settings
- Model IDs: `deepseek-reasoner`, `gpt-3.5-turbo-0125`, `gpt-4.1-2025-04-14`, `gpt-5-2025-08-07`, `gemini-2.5-pro`, `gemini-3-pro-preview`, `gemini-3.1-pro-preview`.
- Temperature 0.1 and top-p 0.5 for all models except GPT-5, which only accepts temperature 1.0.
- No max-token setting (each provider's default). Gemini 3.1 Pro's reasoning limit is 65,536 tokens.
- No reasoning-effort or thinking settings are stated, so they used the defaults.
- One attempt per task, no tools. Plans are checked with VAL.
- The planners got 30 minutes and 8 GiB per task.

### IPC 2023 learning-track benchmarks repo
- https://github.com/ipc2023-learning/benchmarks. Today's HEAD on `main` is `19d6a8ad4b354328154a2cc1f1a95f7c09fa9db6` (2026-09-05).
- No licence file (the GitHub API reports none).
- It has 10 domains: blocksworld, childsnack, ferry, floortile, miconic, rovers, satellite, sokoban, spanner, transport.
- Each domain has `domain.pddl`, a generator (`<domain>.py` plus `generate_all.py`), `base_cases`, `training`, and `testing/{easy,medium,hard}` with 30 tasks each.
- A Floortile fix landed on 2026-09-02, after Corrêa v2 came out.

### How their domains compare with ours (`domains/`)
Our numeric folder shares no domain with them. The plan's "four shared domains" for D5b are shared with the IPC track, but only three of them are in Corrêa's 8.

| domain | in Corrêa's 8? | ours vs IPC 2023 |
|---|---|---|
| blocksworld | yes | Differs. Ours is typed, with `pick_up`, `put_down`, `handempty`, `ontable`. IPC's is untyped, with `pickup`, `putdown`, `arm-empty`, `on-table`. |
| miconic | yes | Matches: same actions and predicates. Ours leaves `:strips` out of the requirements, which does not change anything. |
| rovers | yes | Differs. Ours is the IPC 2002 version with `available` and `channel_free`. IPC 2023 removed both; its file says so in a comment. |
| satellite | no (track only) | Differs. IPC 2023 adds `:negative-preconditions` and a new `turn_to` precondition, `(not (pointing ?s ?d_new))`. |

We do not have childsnack, floortile, sokoban, spanner or transport.

## Part 2. Itemised cost

### Prices used
The `claude-api` skill and the live pricing page (https://platform.claude.com/docs/en/about-claude/pricing), per million tokens:

| model | list (input / output) | Batch API (input / output) |
|---|---|---|
| Sonnet 4.6 | $3 / $15 | $1.50 / $7.50 |
| Haiku 4.5 | $1 / $5 | $0.50 / $2.50 |
| Sonnet 5.5 | $2 / $10 | $1 / $5 |

Thinking tokens are billed as output.

### Measured token counts
From the frontier corpora on disk, mean per trial:

| cell | input | output |
|---|---|---|
| Sonnet 4.6, unaided solve, canonical (v11 to v13) | 1,457 | 261 |
| Sonnet 4.6, unaided solve, renamed corpus (`sonnet-frontier/sweep6`) | 1,513 | 282 |
| Haiku 4.5, unaided solve (v11) | 1,456 | 304 |

For the Sonnet 4.6 tool arm I priced the full usage, including cache writes and cache reads. It comes to $0.0636 per solve trial, $0.2336 per simulate trial at the 6,144 budget, and $0.2621 per simulate trial at 64K.

**Check on the method:** the same arithmetic gives $26.21 (Sonnet tool arm), $6.92 (Haiku tool arm) and $5.55 (Sonnet no-tools, batch) for the budget-probe runs. These equal the measured costs in `frontier_budget_probe_readout.md` §5.

### Cost per line
Thinking adds T tokens per trial: T = 4K (low), 12K (mid) or 32K (high). With thinking on I assumed about 300 visible output tokens. All unaided lines can go through the Batch API. The tool arm cannot, because it runs a multi-turn tool loop.

| line | trials | input / trial | output / trial | list (low / mid / high) | Batch (low / mid / high) |
|---|---|---|---|---|---|
| D5a Sonnet 4.6 thinking on, 300 keys x3 | 900 | 1,457 | 300+T | $62 / $170 / $440 | $31 / $85 / $220 |
| D5a Haiku 4.5 thinking on, 100 keys x3 | 300 | 1,456 | 300+T | $6.89 / $18.89 / $48.89 | $3.44 / $9.44 / $24.44 |
| D5a Sonnet 4.6 thinking off, T=1, x3 | 900 | 1,457 | 261 | $7.46 | $3.73 |
| D5a Haiku 4.5 thinking off, T=1, x3 | 300 | 1,456 | 304 | $0.89 | $0.45 |
| D5a Sonnet 5.5 thinking on (adaptive), 300 x3 | 900 | 1,894 | 390+T | $43 / $115 / $295 | $21 / $57 / $147 |
| D5a Sonnet 5.5 thinking off (`between_tools`), 300 x3 | 900 | 1,894 | 339 | $6.46 | $3.23 |
| D5c Sonnet 4.6 tool arm, renamed corpus, solve, 100 x1 | 100 | measured | measured | $6.36 | not possible |
| D5c Sonnet 4.6 tool arm, renamed corpus, simulate, 100 x1, 6,144 budget | 100 | measured | measured | $23.36 ($26.21 at 64K) | not possible |
| D5d random strings, Sonnet 4.6, 300 x 2 maps, T=0 | 600 | ~1,980 | ~400 | $7.16 | $3.58 |
| D5d random strings, Haiku 4.5, 100 x 2 maps, T=0 | 200 | ~1,980 | ~450 | $0.85 | $0.42 |
| 2-shot cell, Sonnet 4.6, thinking off, 100 x1 | 100 | ~6,500 | 300 | $2.40 | $1.20 |
| 2-shot cell, Sonnet 4.6, thinking on, 100 x1 | 100 | ~6,500 | 300+T | $8.40 / $20.40 / $50.40 | $4.20 / $10.20 / $25.20 |
| **Grand total, required lines** | | | | **$175 / $379 / $889** | **$102 / $204 / $459** |
| Optional: Sonnet 4.6 thinking on, renamed corpus, 300 x3 | 900 | 1,513 | 300+T | $62 / $170 / $440 | $31 / $85 / $220 |
| **Grand total with the optional line** | | | | $237 / $549 / $1,329 | $133 / $289 / $679 |

Running the 2-shot thinking-on line 3 times per problem adds 2 times its cost: +$8 / +$20 / +$50 with the Batch API.

### Pilot to measure thinking tokens
20 keys per arm, 1 run each, Batch API. Arms: Sonnet 4.6 on, Haiku 4.5 on, Sonnet 5.5 on, and Sonnet 5.5 `between_tools` (to confirm it produces no thinking).

| scenario | Batch | list |
|---|---|---|
| low | $1.47 | $2.93 |
| mid | $3.87 | $7.73 |
| high | $9.87 | $19.73 |
| hard cap (every trial hits max_tokens = 64K) | | $38.59 |

Adding a 2-shot thinking-on arm costs $0.84 / $2.04 / $5.04 more with the Batch API.

### Assumptions and API facts that shape the design
1. **The thinking token counts are guesses until the pilot runs.** The pilot replaces the T scenarios. The mid scenario is about 2.5 times the budget probe's aggregate median output of 4,530 tokens.
2. **Sonnet 5.5 counts about 1.3 times as many tokens for the same text** (its newer tokenizer). I scaled its input and visible output by that factor. The T scenarios are in each model's own tokens.
3. **Sonnet 5.5 rejects any non-default temperature.** Both of its arms therefore run at the default T=1, and the 5.5 tier has no T=0 cell. Its "off" setting is `thinking: {type: "between_tools"}`: no extended thinking, accepted only at effort `high` or below. The disabled setting returns a 400 error on 5.5. Both 5.5 arms should send effort `high` explicitly so that only thinking differs between them.
4. **Haiku 4.5 and Sonnet 4.6 turn thinking on in different ways.** Haiku 4.5 needs the manual `budget_tokens` setting. Sonnet 4.6 recommends adaptive thinking, and `budget_tokens` is deprecated there but still works. Using `budget_tokens` on both would keep the two models comparable. This does not affect the on-versus-off comparison within one model.
5. **The T=1 "off" control** means leaving `temperature` out (the default is 1.0).
6. **The T=0 cells need the SDK and API version pinned.** API version 2026-10-21 returns an error for any `temperature` value, even the default, so the SDK has to stay on version 2023-06-01. This covers D5d and keeps it matched to the existing T=0 cells.
7. **D5c is priced at 1 run, T=0, the 6,144 budget, prompt v11,** to pair with the canonical cell and with Haiku's `sweep6-with-tools`. On the renamed corpus the input is about 4% larger, which is not enough to matter.
8. **The random-string input (D5d) is a rough figure.** I assumed random names take about 1.5 times as many tokens as real ones. Even at 1.8 times the line stays under $4 with the Batch API.
9. **The 2-shot input estimate comes from file sizes.**
   - The example files add about 14,900 characters.
   - Our solve prompts measure about 2.95 characters per token on Sonnet 4.6 (a fit over 100 keys).
   - That gives about 5,050 extra tokens, so roughly 6,500 input tokens per trial.
   - Their temperature 0.1 with top-p 0.5 likely cannot be copied: recent Claude models reject a request that sets both temperature and top-p. This is from memory and needs one test call. Thinking on also requires temperature 1.
10. **Prompt caching is not counted.** It could make two of every three repeats cheaper on input, but input is a small part of every thinking-on line.