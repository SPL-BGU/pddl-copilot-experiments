# Handoff — steady GPU deployment for sweep5v2 + PlanBench

**Status:** GOAL set (Omer leaning toward this). Branch `feat/steady-gpu-deployment` off `main`.
Next agent owns **planning**, then **implementation**. This doc is the goal + constraints only —
no plan yet.

**Created:** 2026-06-16. Cost framing lives in slide 5 of
`development/cost-breakdowns/cheap_model_cost_slides.{py,pptx}` ("Alternative — Rent One Steady
GPU, Self-Host the Open Roster").

---

## Goal

Run **sweep5v2** and **PlanBench** over the OPEN-model roster —
**Qwen3.5-0.8B / 4B / 9B, Qwen3.6-35B**, and (maybe) **gemma4-31B** — on a steady, stronger GPU
than the current 3090/RTX-6000 SLURM cluster, which is queued and **can't seat the 35B in BF16**.

## Decision

Rent **one persistent H200-141GB** from a neocloud (**RunPod Secure Cloud** or **Lambda**).
Run **vanilla vLLM** OpenAI server. **Time-share the single box** across all five models: load one,
run its cells, swap to the next.

**Why H200-141GB:** all five fit in **clean BF16 — no tensor-parallel, no FP8, no multi-GPU** =
fewest moving parts. (H100-80GB only if budget bites → forces FP8 / TP=2 on the 31-35B.)

| Open model    | BF16 weights | H200-141 | H100-80      |
|---------------|--------------|----------|--------------|
| Qwen3.5-0.8B  | ~1.6 GB      | ✓        | ✓            |
| Qwen3.5-4B    | ~8 GB        | ✓        | ✓            |
| Qwen3.5-9B    | ~18 GB       | ✓        | ✓            |
| Qwen3.6-35B   | ~70 GB       | ✓        | FP8 / TP=2   |
| gemma4-31B †  | ~62 GB       | ✓        | FP8 / TP=2   |

† gemma4-31B optional (the "maybe" fifth model).

## Rejected alternatives

- **Free SLURM cluster (3090/RTX-6000):** can't run the 35B steadily; queued, mixed configs.
- **NVIDIA DGX Cloud / Lepton / Brev:** premium pricing or just neocloud wrappers with lock-in.
- **Colab:** no addressable endpoint, disconnects, ToS friction.

## Integration (why this is cheap to wire)

The harness already speaks OpenAI-compatible to vLLM via `pddl_eval.vllm_client.VLLMClient`.
Both benchmark paths construct it with a base URL:

- **sweep5:** `run_experiment.py --llm-base-url <url>` → `VLLMClient(base_url=...)`
  (`run_experiment.py:358`, flag at `:634`). Default `http://localhost:8000`, `/v1` auto-appended.
- **PlanBench:** `planbench/engine.py` reads the **`VLLM_BASE`** env var (`engine.py:142`) →
  `VLLMClient(base=...)` (`engine.py:313`).

So pointing at the rented box is **`--llm-base-url` / `VLLM_BASE` = the rental's `/v1`**.

⚠️ **One real gap for the planner:** `VLLMClient` currently hardcodes `api_key="EMPTY"`
(`vllm_client.py:123`). A self-launched vanilla vLLM needs no key, but if the neocloud proxy
gates the endpoint, the key must become configurable (env var / arg). Confirm the rental's auth
model before assuming "EMPTY" works.

## Cost (estimate)

~**$120-150** for the full sweep5v2 across all five (~40-50 GPU-hrs @ ~$3/hr H200). PlanBench is
**extra** (size TBD). For contrast, the API closed-model baseline (Haiku + Gemini Flash-Lite,
both benchmarks) is ~$1,047 — but that buys *different* models for a *different* purpose; the
rental is the actual open-model experiment roster, not a substitute for the API points.

## Constraints for the planner

- **Corpus isolation (load-bearing):** each model's `trials.jsonl` must come from **ONE**
  backend. Do **not** split a single model's corpus across cluster + rental.
- **Keep sampling params identical** to the existing cluster cells — temp / top_p / max_tokens /
  seed — for comparability.
- **Per-model vLLM launch flags to specify:** `--max-model-len`, `--gpu-memory-utilization`,
  `--served-model-name` (the served name must match what the harness sends per model).

## Open items the planner should resolve

1. **PlanBench trial / problem count** (drives the GPU-hours and cost).
2. **Confirm H200-141 vs H100-80 + FP8** (budget vs simplicity).
3. **Where the small cells run:** do the 0.8-9B cells **stay on the free cluster** (cheaper) or
   **move to the rented box** (simpler — one backend)? Note this interacts with corpus isolation:
   whichever backend a model runs on, it must run *entirely* there.
4. **Auth:** does the chosen neocloud need an API key on the endpoint? If so, plan the
   `VLLMClient` key change (see Integration gap above).
5. **Pilot first:** a short calibration run to confirm real GPU-hours/throughput before
   committing the full sweep.

## Pointers

- Cost slide: `development/cost-breakdowns/cheap_model_cost_slides.py` (slide 5) — edit the
  `GPU` / `GPU_HRS` / `ROSTER` data block + re-run to update the numbers.
- Client: `pddl_eval/vllm_client.py`.
- Entry points: `run_experiment.py`, `planbench/engine.py`.
- Per-model vLLM parser mapping (architecture-specific): see memory `reference_vllm_parser_per_model`.
</content>
