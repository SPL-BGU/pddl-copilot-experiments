# API cost summary

One model setup, one corpus, think-off — what each costs to run on each benchmark (Haiku-with-tools is the cheapest path to ~100%; the **hybrid** runs a Sonnet no-tools orchestrator that delegates to a Haiku with-tools subagent).

| Setup | Single-tool | PlanBench | Accuracy |
|---|--:|--:|---|
| Sonnet — no-tools (batchable) | $39 | $66 | low (solve ~29%, simulate 0%) |
| Haiku — with-tools | $146 | $224 | ~100% |
| Sonnet — with-tools | $449 | $673 | ~100% |
| Hybrid — Sonnet orchestrator + Haiku subagent | ~$224 | ~$356 | ~100% |

_Sonnet/Haiku measured on the Anthropic API; PlanBench figures are calibration-transferred (±wide) and also run **free** on local vLLM. Full breakdown + cross-provider prices: `EXPLAINER_eli8.md` / `cheap_model_cost_slides.pptx`._
