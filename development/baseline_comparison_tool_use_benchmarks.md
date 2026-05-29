# Are our with-tools agents underperforming? — external tool-use / MCP benchmark comparison

_Drafted 2026-05-29. Reference corpus = sweep-5 v1 (`checkpoints/sweep5`), the last fully-sealed
sweep (136,800 trials, 20 cells). sweep5v2 / sweep6 are still in flight, so all of our numbers
below are sweep-5 v1._

**Reference is still representative.** The in-flight sweep5v2-live with-tools cells (gemma4,
qwen3_6_35b — the only with-tools cells synced so far) track sweep-5 v1 within a few points:
gemma off/steered 99/98/100/93/91 vs v1 100/99/100/90/89; qwen3.6 off/steered 92/100/97/99/97 vs
v1 94/100/98/98/98. So conclusions drawn on sweep-5 v1 transfer to what's landing now.

## TL;DR verdict

**Our with-tools agents are not underperforming.** Every qualitative pattern we see is
independently documented in the function-calling / agentic-tool / MCP-native benchmark
literature, and on the *right* analog our absolute numbers sit at or above the external
open-model envelope:

1. **Absolute end-to-end success** — our ≥9B models reach 89–98% agg with tools (steered).
   That is *higher* than open models of the same class score on broad MCP suites (Qwen3-235B
   18–23%, Qwen3-8B ~4% on LiveMCP-101). The reason is task-surface, not harness quality: our
   task is a **short bounded agentic loop — typically one specialized tool-call plus light
   interpretation** (close to the BFCL *single-turn* regime, where strong models score
   0.85–0.94), **not** the 5.4-step multi-server orchestration of the τ-bench / MCP-Universe
   regime, where even GPT-5 tops out at 44–58%. (The loop is not strictly single-shot — the
   `loop_exhausted` / `tool_not_selected` failure buckets show models do iterate — but it is far
   shorter and over a 5-tool surface, not 40–527.) Comparing our 95% to GPT-5's 44% would be
   apples-to-oranges in our favor — don't.
2. **Tool-adherence saturates high for capable models and collapses for weak ones / weak
   prompting** — exactly the external pattern (MCP-Bench tool-name validity 96–100%; BFCL
   relevance 19.6% for Llama-3-8B pre-fix).
3. **Thinking-mode suppresses tool invocation** — documented at our exact model scale
   (Qwen3-4B).
4. **Steering restores tool-calling** — the Databricks eval shows a system-prompt change moving
   relevance/tool-call accuracy by +59 points, mirroring our neutral→steered jump.
5. **Steep size scaling and a "calls-the-tool-but-can't-use-the-output" small-model failure
   mode** — both are the textbook small-model signature.

So: report these as **expected, externally-corroborated results**, not as a defect. The one
thing to *avoid* is the naive cross-benchmark success-rate comparison; frame on structure and
on same-size open models instead.

---

## 1. What we are comparing (sweep-5 v1, steered arm unless noted)

Single-task success% (agg = ST mean across the 5 tasks), with-tools (`tl-ster`) vs no-tools:

| model (size) | think | no-tools agg | **with-tools agg** | solve no-tool→tool | simulate no-tool→tool |
|---|---|---|---|---|---|
| Qwen3.5 0.8B | off | 36* | 29* | 0→16 | 0→1 |
| Qwen3.5 4B  | off | 31 | **78** | 8→78 | 0→54 |
| Qwen3.5 9B  | off | 36 | **93** | 11→95 | 0→84 |
| Gemma3 MoE (~4B act) | off | 50 | **96** | 8→100 | 0→89 |
| Qwen3.6 35B MoE | off | 49 | **98** | 9→94 | 0→98 |

\* The 0.8B no-tools "36" is **degenerate**: its validate_* scores (81/51/50) are near-random
binary guessing on the validate tasks, not capability; solve and simulate are 0%. With tools it
actually *executes* (solve 16%, but simulate still ~1%), so agg looks flat only because the
no-tools number was a coin-flip artifact. Read the per-task solve/simulate deltas, not the 0.8B
agg.

**Tool-selection (`tool_selected_rate`, `tool%` in `tables/master.md`):**
- Capable models, steered: **96–100%** across tasks (they reliably call the tool).
- Thinking-ON + **neutral** prompt collapses it — clean exemplar on **solve** (a task free of the
  scoring artifact below): Gemma3-MoE solve tool% **100** (off) → **23** (on/neut); Qwen3.5-9B
  solve tool% **100** (off) → **55** (on/neut); Qwen3.5-0.8B solve tool% **98** → **48**. The
  model reasons its way to an answer instead of calling the tool.
- **Steering restores it**: Gemma3-MoE solve tool% 23 (on/neut) → **77** (on/steered);
  Qwen3.5-9B 55 → **75**; 0.8B 48 → **78**. Neutral→steered lifts tool% by ~20–55 points in the
  thinking-on cells.

> **⚠ Carve-out — exclude `validate_plan` tool%/success from the tool-adherence story.**
> In `master.md`/`aggregate.md`, gemma4's val-plan column craters at think=**off** too
> (off/neut tool% **18**, success 17% — while solve/val-dom/val-prob/simulate in the *same arm*
> sit ~100%). A think=off collapse cannot be a thinking effect. It is the known
> `validate_plan` FP binning bug (memory `project_validate_plan_fp_scoring_bug`: FastMCP pydantic
> arg-errors mis-binned as val-plan FPs). The relabel fix is applied **only in `build_deck.py`**
> (verified: `relabel_tool_arg_error_taxonomy` appears 5× in build_deck.py, **0×** in
> `aggregate.py`/`table.py`), so the pivot tables we read here carry the *un-relabeled* numbers.
> Confirmed reproducible: sweep5v2-live shows the identical gemma off/neut val-plan = 21% crater.
> Use solve / simulate / val-dom / val-prob for the thinking-collapse and steering evidence; the
> deck-built (relabeled) figures are the ones to trust for val-plan.

These observations (capable-model saturation, thinking collapse, steering recovery — on the
artifact-free tasks) are what we benchmark against the literature below.

---

## 2. The right analog — why a flat success-rate comparison is misleading

| dimension | **our with-tools task** | τ-bench / MCP-Universe / LiveMCP-101 |
|---|---|---|
| tool calls per task | short bounded loop, ~1–few (call solve / validate_X, interpret result) | 5.4 avg (LiveMCP-101); long multi-turn dialogues |
| tool surface | 5 fixed, well-described MCP planning tools | 40–527 tools across 11–70 servers |
| who does the hard work | the **planner/validator** (correct by construction once called with valid args) | the model's planning + state-tracking over many steps |
| answer space | constrained (a plan, or VALID/INVALID + reason) | open-ended DB-state / multi-domain goals |
| closest BFCL category | **single-turn Simple/Multiple** (strong models 0.85–0.94) | **multi-turn / agentic** (best model ~12% on memory) |

Our setup is deliberately the *easy* end of the tool-use spectrum: once the model emits a
valid call, a real Fast-Downward/ENHSP planner or a real validator returns ground truth, and the
model mostly has to relay/interpret it. So 78–98% for 4B–35B models is **in-line with
single-call BFCL**, and the comparison that matters is (a) same-size open models and (b) the
*shape* of the metrics, not the absolute success rate vs a 5.4-step orchestration suite.

---

## 3. External benchmarks — what they measure and the numbers

### 3a. BFCL (Berkeley Function-Calling Leaderboard) — gorilla.cs.berkeley.edu, ICML 2025
The canonical function-calling benchmark; AST + executable scoring; categories Simple / Multiple
/ Parallel / **Multi-turn** / **Relevance & Irrelevance** (the direct analog of our
`tool_selected`). Source: https://openreview.net/pdf?id=2GmDdhBdDk ;
https://gorilla.cs.berkeley.edu/leaderboard.html

- **Single-turn vs multi-turn collapse** (the headline that justifies our agentic difficulty):
  worked Qwen-Plus run single-turn AST **0.87** → **multi-turn 0.38** (≈ −45 to −50 pts); even
  the multi-turn leader (o1) reaches only **12%** on the agentic Memory category.
  (https://evalscope.readthedocs.io/en/latest/third_party/bfcl_v3.html)
- **Relevance / abstention** = our `tool_not_selected` mirror. Databricks reproduction:
  Llama-3-8B relevance **19.6%**, Llama-3-70B **63.8%**, DBRX 84.6% — small open models are far
  worse at *correctly deciding to call*. (https://www.databricks.com/blog/unpacking-function-calling-eval)
- **Size band:** frontier (GPT-4-1106 / Gemini-1.5 / Claude-3.5) ≈ 64–66% overall in the frozen
  paper set; 7–8B open models (Qwen2.5-7B, Llama-3-8B, Mistral-7B, Hermes, xLAM, ToolACE) sit
  well below, gap concentrated in multi-turn + hallucination. Live V4 board (recategorized):
  Qwen3-32B ~75.7%, Qwen3.5-27B 68.5%, Qwen3-VL-4B 63.3%, Phi-4 40.8%.
- **Thinking does not help function-calling on the board:** base==Thinking pairs are identical
  (GLM-4.7-Flash 74.6=74.6; Kimi-K2.5 64.5=64.5).

### 3b. τ-bench / τ²-bench (Sierra) — agentic multi-turn tool use, pass^k
Source: https://arxiv.org/abs/2406.12045 (Table 2), https://arxiv.org/abs/2506.07982

- **Best frontier model is far below 100%:** GPT-4o **retail 61.2% / airline 35.2%**; abstract:
  "even sota function-calling agents (gpt-4o) succeed on **<50%** of tasks … pass^8 < 25% in
  retail." Claude-3.5-Sonnet (later) retail 69.2 / airline 46.0.
- **Open models score poorly:** Llama-3-70B avg **14.6%**, Mixtral-8x22B 24.7%, Mistral-Large
  26.6% — *below* gpt-3.5-turbo. τ-bench has **no model below ~7B and nothing in our 0.8–9B
  band** — the published floor is 70B-class open at 15–27%.
- **τ²-bench** (dual-control telecom): even gpt-4.1 only 34%, near-zero past 7 actions.
- **Steep capability scaling** (gpt-3.5 15.4 → gpt-4o 48.2, >3×) and **policy-following
  fragility** (removing airline policy drops gpt-4o 35→11).

### 3c. MCP-native suites (the closest setting to ours — 2025 wave)

| benchmark | scope | best frontier | open models ≤35B-ish | tool-selection metric |
|---|---|---|---|---|
| **MCP-Universe** (2508.14704) | 11 servers, 133 tools, 231 tasks | GPT-5 **43.7%** | GLM-4.5 24.7%, Qwen3-235B 18.2%, gpt-oss-120B 11.3% | "unknown-tools" misuse flagged, no % |
| **LiveMCP-101** (2508.15760) | 41 servers, 260 tools, 5.4 steps | GPT-5 **58.4%** | Qwen3-235B 22.8%, **Qwen3-32B 18.8%, Qwen3-8B 4.0%, Llama-3.1-8B 1.0%** | "wrong tool selection" 1 of 7 failure types |
| **MCP-Bench** (2508.20453) | 28 servers, 250 tools | GPT-5 0.749 | Qwen3-30B-A3B 0.627, **gemma-3-27B 0.582**, Llama-3.1-8B 0.428 | **Tool-Name Validity 96–100%** across roster |
| **MCPEval** (2507.12806) | 5 servers, 676 tasks (easier) | GPT-4o 90.3 (judge) | Qwen3-32B 78.3 (judge); strict tool-name match GPT-4o 79.3 / Qwen3-32B 59.2 | strict tool-name match 55–79% |
| **MCPToolBench++** (2508.07575) | 67 servers, 3253 tools | Claude-4 (top AST) | per-domain Qwen3-Coder/Qwen2.5-Max | AST (tool-select) 0.6–0.9, **Pass@1 0.2–0.5** |
| **LiveMCPBench** (2508.01780) | 70 servers, 527 tools | Claude-Sonnet-4 **78.95%** | "most models 30–50%" (per-model table not published) | router accuracy not published |

Two robust facts emerge across these: **(a)** absolute success on broad multi-tool MCP tasks is
well below 100% even for frontier models (43–59% on the hard suites), and far lower for open
models in our size band (often <25%, down to ~1–4% at 8B); **(b)** *low-level tool selection is
largely solved / near-saturated* (MCP-Bench tool-name validity 96–100%; MCPToolBench++ AST
0.6–0.9) — the gap lives in **parameter correctness, multi-step planning, and using the tool
output**, exactly mirroring our "high `tool%` but lower success, dominated by `verdict_mismatch`
/ `result_mismatch`" for the 0.8B model.

### 3d. Thinking-mode suppresses tool invocation (our neutral/thinking collapse)
- **ThinkBrake (arXiv 2510.00546)** on **Qwen3-4B-Thinking**: oracle early-termination lifts BFCL
  single-turn 85.8% → **94.2% (+8.4)** while cutting tokens 80–94% — the reasoning trace itself
  overwrites an already-correct call.
- BFCL board base==Thinking identical pairs (above).
- _Additional, more recent, verify-before-citing (post-cutoff arXiv dates):_ "LLM Agents Already
  Know When to Call Tools" (2605.09252) — forcing reasoning before the tool decision drops
  Qwen3-4B per-call utility −42.4 on hard tasks, Llama-3.1-8B 79.5→31.2; "Brief Is Better"
  (2604.02155) — Qwen2.5-1.5B function-calling non-monotonic in CoT budget (44→64% at 32 tok,
  down to 25% at 256 tok). Treat these two as supporting, not load-bearing, until verified.

### 3e. Steering sensitivity (our neutral→steered jump)
- **Databricks function-calling eval:** a system-prompt change raised Llama-3-8B relevance
  **19.6% → 78.3% (+58.7)** and Llama-3-70B 63.8 → 75.4. Prompt wording alone swings whether/
  which tool is called by tens of points — the direct analog of our `tl-neut`→`tl-ster` tool%
  lift. (https://www.databricks.com/blog/unpacking-function-calling-eval)

---

## 4. Point-by-point: our observation vs external evidence

| our sweep-5 v1 observation | external evidence | verdict |
|---|---|---|
| ≥9B steered hit 89–98% agg with tools | single-call BFCL strong models 0.85–0.94; our task is the single-call regime | **expected / strong** — at top of envelope because task is narrow |
| 0.8B calls tools (96–100%) but fails (verdict_mismatch) | MCP-Bench tool-name validity 96–100% with low judged completion; MCPToolBench++ AST high, Pass@1 0.2–0.5; LiveMCP-101 Qwen3-8B 4% | **expected** — canonical "valid call, wrong use of output" small-model mode |
| thinking-ON+neutral collapses solve tool% (gemma 100→23; Qwen3.5-9B 100→55) | ThinkBrake +8.4 recoverable on Qwen3-4B; BFCL base==Thinking; (+ 2026 papers, to verify) | **expected** — documented at our exact scale (val-plan excluded — scoring artifact) |
| steering raises tool% +20–55 pts | Databricks +58.7 pts from prompt steering | **expected** — same direction & magnitude |
| big spread 0.8B(weak) → 35B(98%) | τ-bench gpt-3.5→gpt-4o >3×; LiveMCP-101 8B 4% → 235B 23% | **expected** — steep size scaling is universal |
| no-tools ≪ with-tools on solve/simulate (0→90%+) | tools are the whole point; broad MCP suites assume tools, our no-tools is the ablation | **expected** — clean tool-utility signal |

---

## 5. Caveats / what to verify before putting numbers in the paper

- **Don't compare our 95% to GPT-5's 44%.** Different task difficulty (1 call vs 5.4-step
  orchestration). Frame on (a) same-size open models and (b) metric shape.
- **arXiv dates after the Jan-2026 model cutoff** (2601.x, 2604.x, 2605.x in §3d) were surfaced
  by web agents; spot-check the abstracts before citing. The load-bearing claims (BFCL, τ-bench,
  τ²-bench, the six MCP suites, Databricks, ThinkBrake 2510.00546) are all pre-cutoff and solid.
- **BFCL frozen-set small-model cells** are low-resolution in the paper table; cite the
  category-level pattern, not exact per-cell digits.
- **MCPToolBench++ / LiveMCPBench per-model numbers** are partly chart-only / unpublished — use
  the ranges, flag as such.
- Our `tool_selected_rate` ≈ BFCL *relevance* + tool-name-validity combined; it is **not** the
  same as BFCL *irrelevance* (correct abstention), which we don't test (our tasks always warrant
  a call). Note this if a reviewer asks about over-calling.

## 6. Suggested paper framing

> "On a single-tool-call-per-task setting, tool-augmented open models in the 9–35B range reach
> 89–98% end-to-end success, at the top of the open-model envelope reported by MCP-native
> benchmarks (which target far broader multi-server orchestration). Consistent with BFCL and
> MCP-Bench, low-level tool selection saturates near 100% for capable models, while sub-4B
> models invoke tools correctly yet fail to act on their output. Mirroring ThinkBrake and the
> Databricks function-calling study, enabling reasoning mode suppresses tool invocation and a
> steering system prompt restores it (+20–55 pts tool-selection), confirming that tool adherence
> is prompt- and decoding-sensitive rather than a fixed model property."

## Sources (load-bearing)
- BFCL: https://gorilla.cs.berkeley.edu/leaderboard.html · https://openreview.net/pdf?id=2GmDdhBdDk · https://www.databricks.com/blog/unpacking-function-calling-eval
- τ-bench: https://arxiv.org/abs/2406.12045 · τ²-bench: https://arxiv.org/abs/2506.07982
- MCP-Universe 2508.14704 · LiveMCP-101 2508.15760 · MCP-Bench 2508.20453 · MCPEval 2507.12806 · MCPToolBench++ 2508.07575 · LiveMCPBench 2508.01780
- ThinkBrake: https://arxiv.org/abs/2510.00546
