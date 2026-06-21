# API cost summary

One model setup, one corpus, think-off — what each costs to run on each benchmark (Haiku-with-tools is the cheapest path to ~100%; the **hybrid** runs a Sonnet no-tools orchestrator that delegates to a Haiku with-tools subagent).

| Setup | Single-tool | PlanBench | Accuracy |
|---|--:|--:|---|
| Sonnet — no-tools (batchable) | $39 | $66 | low (solve ~29%, simulate 0%) |
| Haiku — with-tools | $146 | $224 | ~100% |
| Sonnet — with-tools | $449 | $673 | ~100% |
| Hybrid — Sonnet orchestrator + Haiku subagent | ~$224 | ~$356 | ~100% |

_Sonnet/Haiku measured on the Anthropic API; PlanBench figures are calibration-transferred (±wide) and also run **free** on local vLLM. Full breakdown + cross-provider prices: `EXPLAINER_eli8.md` / `cheap_model_cost_slides.pptx`._

---

## By model, all providers

Per-model cost, both arms, both benchmarks — ● = measured (own API tokens), the rest projected from the mean measured token profile (June-2026 list prices, re-verify in-console).

| Tier | Model (provider) | Single NT | Single WT | PlanBench NT | PlanBench WT |
|---|---|--:|--:|--:|--:|
| Frontier | ● Sonnet 4.6 (Anthropic) | $39 | $449 | $66 | $673 |
| Frontier | GPT-5.5 (OpenAI) | $86 | $788 | $129 | $1,204 |
| Frontier | Gemini 3.1 Pro (Google) | $34 | $315 | $52 | $481 |
| Frontier | Qwen3.7-Max (Alibaba) | $26 | $321 | $66 | $478 |
| Mid | ● Haiku 4.5 (Anthropic) | $17 | $146 | $22 | $224 |
| Mid | GPT-5.4 Mini (OpenAI) | $13 | $118 | $19 | $181 |
| Mid | Gemini 2.5 Flash (Google) | $7 | $54 | $10 | $84 |
| Mid | Qwen-Plus (Alibaba) | $4 | $51 | $11 | $76 |
| Budget | GPT-5.4 Nano (OpenAI) | $4 | $32 | $5 | $49 |
| Budget | Gemini 2.5 Flash-Lite (Google) | $1 | $14 | $2 | $21 |
| Budget | Qwen-Flash (Alibaba) | $1 | $9 | $3 | $14 |

---

## Single-tool, by task

Where the cost lives — `validate_plan` (10 plan-checks × 100 problems × 3 variants = 3,000 of 4,560 trials) is two-thirds of the no-tools bill.

| Task | trials | Sonnet NT | Sonnet WT | Haiku WT |
|---|--:|--:|--:|--:|
| solve | 300 | $1.24 | $30 | $26 |
| validate_domain | 360 | $1.38 | $19 | $6 |
| validate_problem | 600 | $2.19 | $34 | $11 |
| validate_plan | 3,000 | $25.64 | $212 | $73 |
| simulate | 300 | $8.67 | $154 | $30 |
| **Total** | **4,560** | **$39** | **$449** | **$146** |

---

## Hybrid, by task (Sonnet orchestrator + Haiku subagent)

Sonnet no-tools boss (live → list price) hands each job to a Haiku with-tools helper; the boss is pure overhead on single-task work.

| Task | Sonnet orch | Haiku sub | Together |
|---|--:|--:|--:|
| solve | $2.49 | $26.06 | $28.55 |
| validate_domain | $2.76 | $6.17 | $8.93 |
| validate_problem | $4.38 | $11.17 | $15.56 |
| validate_plan | $51.26 | $73.07 | $124.34 |
| simulate | $17.34 | $29.56 | $46.90 |
| **Total** | **$78** | **$146** | **≈ $224** |
