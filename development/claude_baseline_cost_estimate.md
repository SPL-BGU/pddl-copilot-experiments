# Adding Claude as a frontier baseline — design + cost breakdown

**Date:** 2026-06-01 · **Status:** planning note (no code written yet)

Goal: run Claude (Anthropic API) as an additional model-under-test in the existing
harness, **reusing the pydantic schemas and ground-truth scoring unchanged**, to get a
frontier-model point with/without the PDDL MCP tools — apples-to-apples with the
vLLM Qwen/gemma cells.

## What reuses as-is vs. what needs adaptation

**Reuses unchanged (model-agnostic):**
- `pddl_eval/scoring.py` — `check_success`, ground-truth grading, `model_validate`,
  the `_tool_error_seen` / failure taxonomy.
- `pddl_eval/schemas.py` — `TASK_SCHEMAS` (the pydantic models) drive both the
  no-tools structured constraint and the scoring deserialisation.
- Tasks (5), domains/problems, prompt variants, the 3 MCP servers.

**Needs a thin adapter (a new `AnthropicClient` mirroring `VLLMClient`):**
1. **Inference call** — swap `openai`-style `chat.completions` for
   `anthropic.messages.create`. This is the only "model" seam.
2. **no-tools enforcement** — Claude has **no `guided_json`**. Honour the *same*
   pydantic schema via Claude **structured output / forced-tool** (`tool_choice` on a
   single tool whose `input_schema = TASK_SCHEMAS[task]`). Scoring reuse is unchanged —
   we still `model_validate` the JSON.
3. **with-tools loop** — the Messages API **MCP connector is remote-only + beta**, so it
   can't reach our **local stdio** servers. Bridge one of two ways:
   - reuse the existing `chat.py` MCP client for *tool execution* and only swap the
     inference call (lowest lift, keeps our tool-call logging shape), **or**
   - run via the Claude Agent SDK with the stdio servers in `.mcp.json`.
4. **think on/off** → Claude `thinking` parameter (off = no extended thinking,
   on = extended thinking). ⚠ extended-thinking output can be **much larger** than the
   Qwen think-on output measured below — the biggest cost uncertainty.
5. **Corpus identity** — each (model, condition, think) gets its own `trials.jsonl`
   (methodology rule: never mix backends/configs in one corpus).

## Empirical per-trial token usage (measured from real corpora)

Source: `results/sweep5-cluster-*` and `results/sweep6-live` (Qwen3.5-9B). Token counts
are **cumulative across the agent loop** (`chat.py:295`) → they map directly to
Anthropic per-call billing (each loop call bills full history as input).

| Cell | trials/model | input tok/trial | output tok/trial | turns |
|---|---|---|---|---|
| no-tools, think-off | 4,560 | 1,353 | 2,056 | 1 |
| no-tools, think-on | 4,560 | 1,274 | 5,746 | 1 |
| with-tools, think-off | 9,120 | 12,681 | 1,482 | 2 (max 10) |
| with-tools, think-on | 9,120 | 11,540 | 3,206 | 2 (max 10) |

**Matrix basis = canonical sweep5v2** (verified complete for Qwen3.5-9B in
`results/sweep5-cluster-20260601`): 5 tasks × 20 domains × 220 problems. The
with-tools 2× (9,120 vs 4,560) is **not** an artifact — with-tools runs **6 prompt
variants (11–16)**, no-tools runs **3 (11–13)**. Both think settings → per model:
4,560 + 4,560 + 9,120 + 9,120.

**Full replication = 27,360 trials/model → 232.9M input + 78.3M output tokens.**
**The with-tools input is 95% of all input** (220.9M) because each loop turn re-sends
domain + problem + tool schemas + growing history. → **prompt caching that prefix is
the single biggest cost lever.**
(no-tools-off per-trial tokens were sampled from sweep6-live, same 3-variant matrix;
it's 2.6% of total input so any anon-prompt length skew is negligible.)

## Cost per model (current list prices, verified 2026-06-01)

Prices/MTok: Opus 4.8 $5/$25 · Sonnet 4.6 $3/$15 · Haiku 4.5 $1/$5.
Batch API = −50% both. Prompt-cache read = 0.1× base (stacks with batch).

### Full 4-cell replication (27,360 trials/model)
| Tier | List | Batch −50% | Batch + caching* |
|---|---|---|---|
| **Opus 4.8** | $3,123 | $1,561 | ~$1,288 |
| **Sonnet 4.6** | $1,874 | $937 | ~$773 |
| **Haiku 4.5** | $625 | $312 | ~$258 |

### With-tools-only (drop the 2 no-tools cells; 18,240 trials/model)
| Tier | List | Batch −50% |
|---|---|---|
| Opus 4.8 | $2,173 | $1,087 |
| Sonnet 4.6 | $1,304 | $652 |
| Haiku 4.5 | $435 | $217 |

\* caching estimate assumes ~55% of with-tools input becomes cache reads — rough;
validate in the pilot.

### Headline scenarios — budget on the **Batch-only floor** (full replication)
Batch-only is the firm number: it doesn't depend on cache hit-rate. Caching is upside.
- **Sonnet 4.6 only** (frontier representative): **~$0.9k**
- **Sonnet 4.6 + Haiku 4.5** (frontier + cheap floor): **~$1.25k**
- **Opus 4.8 + Sonnet 4.6 + Haiku 4.5** (full curve): **~$2.8k**

Caching upside (if hit-rate lands): could trim toward $0.8k / $1.0k / $2.3k respectively
— but **don't budget on it**. The Batch API doesn't guarantee request ordering/timing,
so the 5-min cache TTL is unreliable across thousands of batched requests; the constant
system+tools prefix may need **1-hour cache writes (2× write)** to hold, which changes
the math. Measure realized hit-rate in the pilot before claiming the upside.

## Cross-vendor comparison (full 27,360-trial eval, prices verified 2026-06-01)

All prompts are <200K tokens, so Gemini Pro bills at its ≤200K tier. Batch = −50%.
**Output is 63–68% of every bill** (output priced ~5× input; it's ~⅓ the volume but
costs more) — so the think-on cells and any extended-thinking blow-up dominate, and
**prompt caching, which only touches input, is a secondary lever.**

| Model | List | **Batch (budget)** |
|---|---|---|
| OpenAI GPT-5.5 | $3,514 | $1,757 |
| Anthropic Opus 4.8 | $3,122 | $1,561 |
| OpenAI GPT-5.4 | $1,757 | $878 |
| Anthropic Sonnet 4.6 | $1,873 | $937 |
| Google Gemini 3.1 Pro | $1,405 | **$703** |
| Google Gemini 3.5 Flash | $1,054 | $527 |
| OpenAI GPT-5.4-Mini | $527 | $264 |
| Anthropic Haiku 4.5 | $624 | $312 |
| Google Gemini 3.1 Flash-Lite | $176 | $88 |
| OpenAI GPT-5.4-Nano | $144 | $72 |

Note: **Gemini 3.1 Pro ($2/$12) is the cheapest *Pro-tier* frontier model** here —
below Sonnet and Opus. GPT-5.5 and Opus are the priciest flagships.

## Why it's expensive & how to cut it

It's expensive because it's a **full per-model eval — the identical 27,360 trials a
Qwen3.6-35B run does** (verified: same 4,560/9,120 cell counts, token means within 3%).
The only difference: Qwen runs on your SLURM GPUs (sunk cost), so a frontier API model
is the price of doing that *same* eval on metered compute you can't self-host.

Levers, in order of impact:
1. **Batch API (−50% on input AND output).** Biggest single lever; offline eval has no
   reason to pay realtime. Already baked into the "Batch" column.
2. **Trim the output-heavy axes.** 6 with-tools variants + 3 no-tools variants exist for
   statistical power across *weak* models; a frontier *baseline point* doesn't need all 6.
   **Lean scope** (with-tools 2 variants, no-tools 1, all else equal) = 9,120 trials/model
   (⅓): Gemini 3.1 Pro **~$234**, Sonnet **~$312**, Opus **~$520**, Gemini Flash-Lite **~$29**.
3. **Cheaper tiers for a frontier-ish point:** Gemini Flash-Lite ($88), GPT-5.4-Nano ($72),
   Haiku ($312) — full scope, Batch.
4. **Prompt caching (input only → caps at ~⅓ of the bill).** Secondary, but real on the
   with-tools prefix (95% of *input*). See Bedrock note below.

### Bedrock prompt-caching note
Yes — on Bedrock (or first-party) you can cache the **constant system prompt + 15 tool
schemas** (identical across all 27,360 trials) and the **domain+problem prefix** (shared
across the 6 variants per problem), read at ~0.1× base. Because with-tools input is 95%
of all *input*, this meaningfully dents the input third of the bill. Two realities:
(a) it does **not** touch output (the 63% majority), and (b) **Batch halves everything
including output**, so Batch is the stronger lever — use caching *on top of* Batch, not
instead. Cache TTL (5-min default) is the constraint; order requests by (domain, problem)
or use 1-hour cache writes (2× write) to hold the constant prefix. Bedrock regional
endpoints add a ~10% premium for Claude 4.5+.

## Caveats (read before budgeting)
- **Tokenizer:** counts are Qwen's. Opus 4.7+ uses a new tokenizer that can use **~+35%
  tokens** on the same text → scale **Opus input ~×1.35**. Sonnet 4.6 / Haiku 4.5 are
  closer to the measured numbers (±~15%).
- **Extended thinking:** Claude think-on output may be 2–5× the Qwen think-on output →
  the think-on cells are the largest single uncertainty. Cap with a `thinking.budget_tokens`.
- **Turn count:** Claude may take fewer/more tool turns than Qwen (mean 2 here) → shifts
  with-tools input proportionally.
- **No server-side tool fees:** the MCP servers are local/client-side; tool results are
  already counted as input tokens. No per-search charges.
- **Harness/MCP compute** runs on our own hardware → negligible vs API cost.

## Recommendation
1. **Pilot first (~$20–35):** 1 task × ~10 problems × both conditions × both think
   (~600 trials) on Sonnet 4.6 via Batch. Purpose: validate the adapter end-to-end AND
   replace the Qwen-tokenizer proxy with **real Claude token counts** before committing.
2. Use **Batch API** (this is offline eval — no reason to pay realtime) + **prompt
   caching** on the system+tools+domain+problem prefix.
3. Suggested first real run: **Sonnet 4.6 + Haiku 4.5, full replication, Batch
   ≈ ~$1.25k** (firm); add **Opus 4.8 (~+$1.56k Batch)** once the pilot confirms real
   token counts and an extended-thinking output budget. Treat caching savings as a
   bonus measured in the pilot, not a planned line item.
