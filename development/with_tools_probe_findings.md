# With-tools frontier probe — findings, cost, and decision (2026-06-19)

Investigation of the **with-tools** condition for proprietary frontier models
(Sonnet 4.6, Haiku 4.5), to (a) extend the paper's tool-use propensity result
beyond the open roster and (b) put a number on the **token-efficiency / cost-of-pass**
claim. Companion to the no-tools work in `tools/claude_api_batch.py` + `results/sonnet-frontier/`.

## The load-bearing constraint: with-tools cannot be batched

With-tools is a multi-turn **agentic loop** (`chat.MAX_TOOL_LOOPS = 10`): the model
calls an MCP tool, *we* execute it locally (pddl-solver / pddl-validator), feed the
result back, and loop until it answers. The Anthropic **Batches API is single-pass**
and cannot run our local MCP tools mid-conversation, so with-tools **must run live, at
list price — no −50% batch discount.** This is the single biggest cost driver and it
is structural, not an implementation choice.

## Method

Tool: `tools/claude_api_tools_probe.py` (live agentic loop; `--model`, `--no-tools`,
per-trial error handling, cost report + projection). Reuses the harness builders for
corpus identity: `build_jobs` / `build_messages` / `check_success` / `save_results` —
same fixtures, prompts, and graders as the live vLLM harness and the no-tools batch.

Sample: the **same stratified 75-trial set** used for the no-tools cost probing —
49 validate_plan + 8 simulate + 6 each of solve / validate_problem / validate_domain,
canonical (sweep5v2), prompt variant 11 (plain), mid-difficulty domains, both
polarities, short→long. validate_plan (n=49) is the statistically solid cell; the
n=6–8 cells are directional (wide CIs).

Four conditions, all on identical canonical fixtures:
- Sonnet no-tools — from the full run (`results/sonnet-frontier/sweep5v2`, full N).
- Sonnet with-tools — 75-trial probe (first 23 + remaining 52; the first batch
  crashed on a depleted credit balance mid-run and was salvaged from the log).
- Haiku with-tools — 75-trial probe.
- Haiku no-tools — 75-trial probe.

## The capability ladder (success rate)

| Task | Sonnet NT | Sonnet WT | Haiku NT | Haiku WT | Haiku lift | Sonnet lift |
|---|--:|--:|--:|--:|--:|--:|
| simulate | 0.0% | 100% | 0.0% | 87.5% | +87.5 | +100 |
| solve | 28.7% | 100% | 33.3% | 100% | +66.7 | +71.3 |
| validate_plan | 97.3% | 100% | 83.7% | 100% | +16.3 | +2.7 |
| validate_problem | 89.7% | 100% | 50.0% | 100% | **+50.0** | +10.3 |
| validate_domain | 93.6% | 100% | 83.3% | 100% | +16.7 | +6.4 |

NT = no-tools, WT = with-tools. Probe n: validate_plan 49, others 6–8.

## Findings

1. **Tools take every task to ~100%** for both models. Big accuracy jumps are simulate
   (0→~100) and solve (~30→100); validation gains are marginal for Sonnet (already
   high) but large for Haiku.

2. **Cost-of-pass — at the frontier, tools win only on simulate.** Because Sonnet's
   *no-tools* baseline is already good *and* cheap (28.7% solve, 90–97% validate), the
   agentic-loop overhead (the ~3,611-token tool schema re-sent every turn, at 2× list
   price) makes tools **7–14× more expensive per correct answer** on solve/validate.
   simulate is the sole unambiguous win — no-tools cost-of-pass is infinite (0
   successes), so tools are the only way to a correct trajectory.

3. **Capability gradient (the key result).** The tools *lift* is **2–5× larger for the
   weaker model** on the validation tasks (validate_problem +50.0 Haiku vs +10.3
   Sonnet; validate_plan +16.3 vs +2.7). Sonnet's no-tools validation holds high
   (90–97%); Haiku's collapses (validate_problem to a coin-flip 50%). **Validation
   competence is capability-gated, and tools erase that gap.** Claim: *tools close the
   gap, and the gap they close grows as the model weakens.*

4. **Floors are model-agnostic.** simulate is 0% for *both* models unaided (sole-source
   confirmed across the capability range); solve is ~29–33% for both. Generative /
   state-tracking failure is universal; only validation separates strong from weak.

5. **Haiku's 200K context overflows on giant-trajectory simulate.** The lone Haiku WT
   failure is `simulate depot/p01` — a 400 invalid_request: the trajectory tool dumps
   ~500k tokens (it fit Sonnet's 1M window but not Haiku's 200K). The per-trial error
   handling records it as a failure and the probe continues. Net: Haiku's cap makes
   simulate 5× cheaper but costs that trial (87.5% vs 100%).

## Cost (probe-projected)

With-tools at LIST price (no batch). Full arm = all 6 variants (9,120); plain-only =
variants 11–13 (4,560), the direct tools-vs-no-tools contrast.

| | Sonnet WT | Haiku WT |
|---|--:|--:|
| simulate | $308 | $59 |
| solve | $60 | $52 |
| validate_plan | $423 | $146 |
| validate_problem | $69 | $22 |
| validate_domain | $38 | $12 |
| **Full arm (9,120)** | **~$897** | **~$292** |
| **Plain-only (4,560)** | ~$449 | **~$146** |

Plain-only $146 breakdown (Haiku): validate_plan ~$73, simulate ~$30, solve ~$26,
validate_problem ~$11, validate_domain ~$6. (For reference: Haiku no-tools full is
~$17, batchable.)

## DECISION (2026-06-19)

**Run Haiku 4.5 with-tools over the 4,560 (plain-only, variants 11–13) corpus of
sweep5v2** — the direct tools-vs-no-tools contrast, matched N to the no-tools plain
arm.

**Cost constraint: the ~$146 list-price cost is NOT accepted. A cheaper solution is
required before this runs.** This is an open blocker, not a green light.

### Cheaper-solution candidates (to resolve before running)

1. **Prompt caching (recommended first — methodologically free).** The system prompt +
   the ~3,611-token tool schema are byte-identical across all 4,560 trials and re-sent
   every turn. `cache_control` on that stable prefix (and on prior turns within a
   trial) charges cached reads at 0.1×. Input dominates the bill (~85% of token cost),
   and a large share of input is this repeated prefix → potentially a large cut with
   **no change to prompts or grading**. Needs a small re-probe to measure the realised
   saving (caching helps live/sequential runs; it did not help the parallel batch).
2. **simulate trajectory compaction.** simulate is the worst per-token offender and the
   source of the Haiku overflow. A compact trajectory-tool result (truncate/summarise
   the state dump) would cut simulate cost *and* fix the overflow — but it changes the
   tool output, so it must be applied identically to any comparison arm or documented
   as a backend adaptation.
3. **Lower the agentic turn cap.** Haiku used up to 6 turns on solve; capping loops
   trims worst-case token growth (small saving, low risk).
4. **Subsample validate_plan** (the $73 bulk). Cheapest lever but **breaks N-matching**
   with the no-tools corpus — only acceptable with reported CIs and an explicit note.

Recommended path: prototype #1 (prompt caching) with a short re-probe to quantify the
saving, then decide if #2 is also needed to clear the budget.

## Caveats

- Probe-based projections from small per-task n (validate_plan n=49 solid; the rest
  n=6–8 with wide CIs). Treat the n=6 cells as directional.
- simulate WT cost is the least reliable projection: at full N more giant-trajectory
  fixtures will overflow Haiku's 200K and fail cheaply, so real simulate cost may come
  in under the projection but with success below the probe's 87.5%.
- Paper scope (per advisor decision): the Sonnet no-tools result is in the submission;
  the with-tools / Haiku ladder is **Future Work** — this probe gives the feasibility +
  cost evidence for that future run.

Data: `results/frontier-with-tools-probe/` (keys + graded probe trials). Tool:
`tools/claude_api_tools_probe.py`.
