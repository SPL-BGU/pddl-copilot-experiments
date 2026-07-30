# PlanBench with-tools arm — handoff (2026-07-28, revised 07-30)

> **ONE GATE IS OPEN AND IT IS NOT YOURS TO CLOSE.** The open item is a **go/no-go
> judgement on whether this arm earns its ≈$46**, not a missing signature. At
> `planbench_wt_prereg.md` §10 Omer wrote: *"lets simplify and dig deeper here i either
> dont realy get the full picture or it just seems insignificant."* The reply — plain
> walkthrough, honest significance verdict, cost-and-off-ramp ladder, answer slots — is
> **`development/planbench/planbench_wt_significance_brief.md`. Read that first.**
>
> **Nothing is built, nothing is spent, no API call has been made.** Do not build, do not
> spend, and do not reopen a slot that §3 below records as decided. On a go, start at §6.
>
> **Git:** prereg work is on `main` (`53553a7`); the brief and the 07-30 stale-content
> cleanup are on branch `planbench-wt-significance-brief` (doc-only, no PR needed by
> project convention). Do not touch `31b84ab` (nt-ster H4 prereg) — parallel session,
> different workstream.
>
> **Suggested entry point:** `/resume-verify development/planbench/PLANBENCH_WT_HANDOFF.md`

## 1. What this arm is and where it sits

Act 4 of the journal paper re-measures PlanBench on a 2026 frontier model. The
**no-tools layer is finished and graded** (`planbench_frontier_haiku_nt.md`, 06-22 run,
07-23 grading) and it carries Act 4's headline: Haiku 4.5 beats GPT-4 on blocksworld
plan generation CI-disjoint (41.0 [36.8,45.4] vs 31.4 [27.5,35.6]), the Mystery collapse
replicates (41.0 → 0.8), the t2 silent-0.0 artifact is fixed, and t7 quantifies a
chat-format grading disease. **This arm cannot strengthen or weaken any of that** — §1 of
the prereg fixes that by design.

The WT arm carries a labelled **secondary** claim: the funnel replicates when the model
operates the prescribed remedy on the field's own instrument. Its real value to the paper
is that it is the only place the tools claim is tested on an instrument we did not build,
which pre-empts the "you designed the benchmark your method wins on" objection for ≈$46.
Be honest about its ceiling: the bare "tools rescue Mystery" result is already published
at least four times, so the novelty is the **matched-scaffold single ablation**, the
formalization-boundary metric, the delegation-rate mediator, and accuracy-vs-dollars —
not the direction of the effect.

**Binding documents, in precedence order:**
1. `development/planbench/planbench_wt_prereg.md` — the protocol. Binding once signed.
2. `development/planbench/planbench_wt_prereg_decisions.md` — reasoning, provenance,
   rejected alternatives, and two findings that live outside the prereg (§7 below).
3. `development/journal_decisions_memo.md` §4 — the accepted D-J3 ruling this implements.
4. `development/planbench/planbench_frontier_haiku_nt.md` — the graded NT layer.
5. `development/planbench/PLANBENCH_HANDOFF_v3.md` — superseded direction (small-model
   scaffolding), kept for its cluster/ops lessons only.

## 2. The design (all slots answered; awaiting signature only)

| | |
|---|---|
| cells | **4** — {blocksworld, mystery_blocksworld} × {with-tools, matched-no-tools}, task t1 only |
| n | **500 per cell**, the whole t1 pool (ids 2..501). No subsampling, no seed, no strata |
| model | `claude-haiku-4-5`, single tier (owned as a limitation) |
| tools | harness roster: pddl-solver + pddl-validator, **7 tools** (`run_experiment.py:122`) |
| backend | adapter over `tools/frontier_runner.py` (SDK Tool Runner), `MAX_TOOL_LOOPS`=10 |
| PDDL | **model-authored** domain + problem + plan; nothing injected |
| cost | ≈$46 central; ≈$52 with the sensitivity arm and calibration (73% of the ~$70.6) |
| confirmatory | 2 paired exact-McNemar tests (clean, Mystery), Holm within family, α=0.05 |
| predictions | (i) Mystery outcome band, (ii) two-branch mechanism test. **(iii) STRUCK** |
| kill date | **2026-08-15** → converts to pre-registered future work inside an NT-only Act 4 |

## 3. Decided — do not reopen

| what | decision | when |
|---|---|---|
| sample | whole pool, 500/cell, no subsampling | Omer, 07-25 |
| scope | **shape B**: t1 2×2 only; t3 pair out; prediction (iii) struck per the linkage rule | Omer, 07-26 |
| t2 | stays excluded, as a **scope** decision — option closed, not deferred | Omer, 07-26 |
| PDDL authorship | model authors domain + problem + plan | Omer, 07-26 |
| spend guard | **no runner-side cap.** The account is prepaid per experiment with no real-time billing, so the loaded balance is the ceiling and `frontier_runner`'s existing "credit balance too low" break is the stop | Omer, 07-26 |
| amendments | §9 A-D and F-I accepted; **E rejected** and rewritten as the prepaid-balance clause | Omer, 07-26 |
| bands | four-outcome partition (NO-RESCUE / PARTIAL / RESCUE / INCONCLUSIVE), cutpoints in counts | prereg §3 |
| clean-t1 check | outcome-neutral, thresholded on the two decomposed quantities (extraction ≥90%, correct-given-extracted ≥90%); raw delivered stays the reported primary | prereg §3 |
| funnel placement | input boundary as a new **leading bar** in the with-tools cascade; CALL-extension rejected on measurement | prereg §4 |

If a fresh reading tempts you to revisit one of these, read the decisions memo section
that argues it before raising it. Each was adjudicated against measured evidence, and two
(t2 rationale, CALL extension) were decided **against** the 07-24 draft's own stated
reasoning because that reasoning was factually wrong.

## 4. Verified facts — do NOT re-derive

A 7-agent read-only evidence workflow (~1.8M tokens) produced these, and the load-bearing
ones were re-verified by hand. Raw per-agent output survives at
`~/.claude/projects/-Users-omereliyahu-personal-pddl-copilot-experiments/37e4225c-19f4-4605-b37d-dfad9c8fd1ec/subagents/workflows/wf_08c98872-d6e/journal.jsonl`
(7 `{"type":"result"}` lines; the decisions memo carries the conclusions with provenance).

**Corpus (measured on disk).** t1 pool ids 2..501, t3 pool ids 1..500, intersection 499 —
this is why the 07-24 "one shared subsample" premise failed, and why the whole pool makes
it moot. Mystery is a **pure symbol rename with an identity object mapping**, verified at
501/501 instance files, 500/500 t1 gold plans (identical lengths), 500/500 t3 candidate
plans, 500/500 t3 verdicts — so clean-vs-Mystery is exactly paired and the §2 pre-lock
check is recorded PASSED. Gold plan lengths take 8 even values {2:30, 4:56, 6:114, 8:139,
10:113, 12:46, 14:1, 16:1}. `instances/blocksworld/mystery/generated_basic` holds a stray
mystery-only `instance-0.pddl` that is **not** a rename of anything: never enumerate the
pool by directory glob. Graded-NT `query` strings are byte-identical to `prompts/*.json`
for 500/500 in all four graded cells.

**NT anchors (recomputed from the on-disk grading fields, all six reproduce exactly).**
bw t1 205/500 = 41.0 [36.8,45.4] · bw t3 391/500 = 78.2 · mystery t1 4/500 = 0.8 [0.3,2.0]
(all four successes have gold plan length 2) · mystery t3 227/500 = 45.4 · GPT-4 bw t1
157/500 = 31.4. Extraction: clean t1 472/500 = **94.4%**, mystery t1 448/500 = 89.6%;
accuracy given extraction 205/472 = 43.4% clean.

**Cost anchors (measured, from our own frontier WT corpora).** Haiku with-tools
$0.02097/trial over 1520 trials ($31.87 total, caching saved 24.8%); the `solve` cell —
the closest analogue — $0.04557/trial at 4.48 turns. loop_exhausted 1/4560 trials.
PlanBench prompts are far smaller than our suite's: bw t1 ≈726 tok, mystery t1 ≈617 tok.
Projected PlanBench WT: bw t1 $0.0348/trial, mystery t1 $0.0412; matched-NT $0.0074 and
$0.0083. Four independent models put the arm between $25 and $60; the gate settles it.

**Statistics (recomputed locally).** Band cutpoints at n=500: NO-RESCUE x ≤ 15, PARTIAL
x ∈ [35,228], RESCUE x ≥ 272, INCONCLUSIVE 16..34 or 229..271 (62/500 outcomes). Surviving
confirmatory power at the whole pool: Mystery ≥0.95 against any WT rate ≥5%, clean ≥0.99
against any WT rate ≥60%. Equivalence margin ±7.5pp is certifiable at n=500 up to total
discordance ψ=0.33; ±5pp is not pre-registrable at any affordable n.

**Code (each verified directly, not inferred).** `REQUIRED_PLUGINS` = solver + validator
only (`run_experiment.py:122`). `_parse_engine_name` allowlist is
`{ollama, vllm, vllm-base, vllm-tools, anthropic}` and raises otherwise
(`planbench/engine.py:~105`). `PDDL_COPILOT_RENDER_FROM_TOOLS` defaults to `"1"`
(`engine.py:393`). `classic_planner(strategy="astar_lmcut")` = `astar(lmcut())`, optimal
(`solver_server.py:247,411`). `WITHOUT_TOOLS_SYSTEM_BY_TASK` exists as a length-matched
mirror (`pddl_eval/prompts.py:110`, test-enforced). `MAX_TOOL_LOOPS` = 10
(`pddl_eval/chat.py:29`). `response_evaluation.py` is **patched in place** by
`planbench/apply_patches.py` (patch 5 A/B/C) — the same build that graded the NT layer.

**External (spot-verified 2026-07-25).** Göbel et al. arXiv:2603.06064 ran **Haiku 4.5**
with PDDL tools over MCP on 102 IPC Blocksworld instances: 63.7% → 66.7% (+3.0pp) at 5.7×
token cost, because the tool exposed a step-wise simulator and the model kept the search.
Huang & Zhang ACL 2025 (arXiv:2412.09879) find formalizers robust to lexical perturbation.
Everything else in the literature block of the decisions memo is **unverified** — run
`/verify-claims` before any of it enters prose.

## 5. Traps that produce wrong numbers silently

1. **`PDDL_COPILOT_RENDER_FROM_TOOLS` defaults to `1`**, which renders the answer from the
   last parseable tool result and never reads the model's final message. Left alone, a
   cell measures tool-verified instead of delivered, contradicting the D-J2 ruling. Pin
   it to `0` for every cell.
2. **`build_table.acc()` divides by `len(instances)`** regardless of what was run. Inert
   at the whole pool, fatal on any subsampled path: a 250-instance replay reports a
   believable 22.2% where the truth is 44.4%. The audit asserts denominator = realized n.
3. **The upstream extractor biases against this arm.** A plan pasted from
   `classic_planner` extracts to nothing (`(unstack a b)` tokenizes as `(unstack`);
   markdown bolding extracts to nothing; shorthand action names extract to nothing; and
   **one narrating sentence before the plan injects a duplicated action** that VAL then
   rejects. The frozen format clause must demand the plan block as the entire answer in
   PlanBench's own NL phrasing. A NO-RESCUE verdict on Mystery may not be called a
   formalization result until the extraction-injection audit has run on that cell.
4. **Never `--run_till_completion`.** A loop-exhausted trial returns an empty answer,
   which PlanBench retries forever at temperature 0 — an unbounded paid loop.
5. **Never `--ignore_existing` against `pddl_copilot__anthropic__claude-haiku-4-5`.** It
   would overwrite the graded 06-22 NT corpus. Use the new engine names in §6.
6. **Do not pass `--specific_instances` to `response_evaluation.py`** — its filter mutates
   a module-level list and silently grades everything after the last matched id.
7. **Prompt caching is on a knife edge** (~5% margin over Haiku's 4096-token minimum) and
   the matched-NT arm cannot cache at all. It is a billing-layer property only, explicitly
   outside the "identical apparatus" clause; the gate records the runner's verdict.

## 6. Owed work, in order — ONLY after RATIFY

1. **Adapter** over `tools/frontier_runner.py` driving PlanBench t1 (~1 agent-day). It
   must stamp the **instance id into every logged tool call** — without that the §4
   formalization metric is unmeasurable and the prereg names a stage it cannot test. The
   existing `PDDL_COPILOT_TOOLLOG` side-log cannot be joined (`query[:200]` has one
   distinct value across all 500 instances).
2. **Engine names + allowlist:** `pddl_copilot__anthropic-tools__claude-haiku-4-5` and
   `pddl_copilot__anthropic-scaffold__claude-haiku-4-5`; add the backend tokens to
   `_parse_engine_name`; no `_chat` substring. Add `build_table` engine entries.
3. **Environment:** no existing venv can run WT generation (the PlanBench venv lacks
   `mcp`; the repo venv lacks `tarski`/`pddl`/`transformers`). Pin the `anthropic` version
   deliberately — 0.109.2 and 0.111.0 are both on this machine.
4. **Scaffold text**, frozen at the gate: NL→PDDL step + task-format clause shared
   byte-identical across arms, tool-use policy sentence mirrored for the no-tools arm, no
   tool name in the shared clause.
5. **Calibration**, ≈$1.50: 20 clean + 20 Mystery instances **disjoint from the graded set
   and discarded**. Headline observable is **p90 output tokens per trial**. Decision
   function reads cost and throughput only — never accuracy, never the contrast.
6. **[OMER, ~10 min]** approve scope and spend; this is also when he decides how much
   balance to load. Scaffold and analysis script freeze here.
7. **Run**, then **grade locally** (Rosetta VAL + plugin FAST_DOWNWARD, cwd
   `external/LLMs-Planning/plan-bench`, `RENDER_FROM_TOOLS=0`).
8. **Results memo** with the pre-registered analysis, the deviation table, and the band
   verdict read off the §3 cutpoints.

## 7. Open items outside this prereg

- **NT t3 GPT-4 comparison is mix-confounded** and is marked `PENDING AUDIT` in
  `planbench_frontier_haiku_nt.md` finding 2. The committed GPT-4 t3 corpus is a different
  corpus (0/500 identical queries; verdict mix 31.0% VALID vs our 64.8%), and the two
  models have opposite verdict biases, so a common-mix reweighting collapses the Mystery
  t3 gap from 28.2pp to 9.5pp. **Do not write paper prose from that finding until it is
  re-reported with per-verdict rates.** t1 is clean and unaffected. Evidence: decisions
  memo §5. Omer has not yet said whether to open this now or after the WT results.
- **Two free strengtheners for the NT layer, pending `/verify-claims`:** an apparent
  independent external replication (LLMFP Direct GPT-4o 41.5 / 0.8 at n=602 vs our 41.0 /
  0.8), and a published GPT-4 Mystery-t1 comparator (26/600 = 4.3% [3.0,6.3], Valmeekam
  arXiv:2305.15771 Table 1) that is CI-disjoint **above** Haiku's 0.8% — the NT doc
  currently records this cell as "not in canonical".
- **The ~$70.6 remainder is bookkeeping** (`frontier_rerun_handoff.md:74`), not a console
  balance. Verify it before any spend.

## 8. Do not

- Build or spend before the RATIFY signature.
- Reopen a §3 decision without reading the argument that settled it.
- Treat the WT numbers as Act 4's headline, or put them in a table or figure with GPT-4
  rows (prereg §7 makes that a protocol rule, not a prose intention).
- Quote the literature block of the decisions memo without `/verify-claims`.
- Touch `31b84ab` / the nt-ster H4 files — parallel session, different workstream.
