# PlanBench-WT confirmatory results (run 2026-08-01/02, graded 08-02, analyzed 08-03)

**Protocol:** prereg `planbench_wt_prereg.md` as ratified (tag `prereg-planbench-wt-v1`)
+ restart record 1 (frozen v2 clause). Model `claude-haiku-4-5`, sequential, 2400 trials
at the amendment-K 600/cell pool. **Confirmatory spend $39.87**; arm cumulative $42.09
(both calibrations included) of the $170 balance. Grader: patched
`response_evaluation.py` + Rosetta VAL — byte-identical grader epoch to the published NT
layer. Endpoint: **delivered** `llm_correct`, treatment-policy (empty/missing = failure),
denominator = realized 600 per cell (asserted). Analyzer:
`.local/wt_run/analyze_confirmatory.py`.

## Headline: the pre-registered verdict is RESCUE, and both confirmatory tests pass

| cell | correct/600 | % | Wilson 95% |
|---|---|---|---|
| clean matched-NT | 287 | 47.8 | [43.9, 51.8] |
| clean WT | 418 | **69.7** | [65.9, 73.2] |
| Mystery matched-NT | 0 | 0.0 | [0.0, 0.6] |
| Mystery WT | 431 | **71.8** | [68.1, 75.3] |

**PRIMARY family (paired exact McNemar, Holm within family, α=.05):**

- **Mystery:** WT 431/600 vs NT 0/600, paired Δ **+71.8pp** [68.2, 75.4], discordant
  b=431 / c=0, exact p = 3.6e-130 (Holm 7.2e-130) — significant.
- **Clean:** WT 418/600 vs NT 287/600, paired Δ **+21.8pp** [16.6, 27.0], b=206 / c=75,
  exact p = 2.7e-15 (Holm unchanged) — significant.

**Band verdict (amendment K, n=600):** Mystery WT x=431 ≥ 325 → **RESCUE** (Wilson lower
68.1% ≥ 50%). **Conjunctive ruling: significant + band met = SUPPORTED.** Against the two
published bands: lands in the formalize-then-delegate band (~63–100%), far above the
verifier-in-the-loop band (~3.8–14%) [both pending /verify-claims before prose].

**Mechanism (prediction ii): RESCUE branch, provisionally met — one requirement open.**
Delegation = 100.0% of WT trials in both domains (≥80% required ✓); paired
|clean_WT − mystery_WT| = **2.2pp** (b=119/c=132, exact p=0.449 — within the ±7.5pp
margin, let alone the branch's ±10pp ✓); `formalization_match` (§4, the third
requirement) is NOT yet computed — it needs the pddl-parser equivalence pass over the
stamped tool-call logs and is the next analysis step. Branch language stays provisional
until it lands. The joint falsifier (Mystery WT ≈ Mystery NT) is trivially refuted.

## Audits (all pre-registered; two need Omer's sign-off on interpretation)

**1. Clean-t1 apparatus criterion — (b) PASSES, (a) fails RAW but decomposes model-side.**
(b) P(correct | extracted) = 418/436 = **95.9%** ≥90% ✓. (a) raw extraction 436/600 =
72.7% < 90% ✗ — but the 164 non-extractions decompose as: **63 empty deliveries** (loop
exhaustion, model never answered), **94 honest empty plan blocks** (model concluded
"unsolvable" after its own PDDL misled the planner — the calibration's ruled
not-a-defect class, now at scale), and only **7 true instrument misses** (a plan present
in the block that the parser dropped). Parser success on plan-bearing blocks =
436/443 = **98.4%**. The criterion's stated purpose is to "name which stage broke:
the benchmark's text parser or the model's planning" — it names the model's planning.
Same reading Omer signed at the run-2 gate (75% cell), extended to the real cell.
> ANSWER (accept the decomposition reading of criterion (a) / treat as apparatus
> restart):
>

**2. Mystery matched-NT narration-injection recurred at scale — the collapse survives
it.** 479/600 NT trials had extra actions injected from narration (calibration run 2
showed 0/20 on the easier draw; real-pool Mystery prompts elicit long narration again).
Direction of this bias: inflates the WT−NT delta in our favor, so it must be reported.
Robustness: on the 121 uninjected trials the model scores **0/121**; the injected subset
is 0/479; the bare-NT published layer (different pipeline, no scaffold) measured 4/500 =
0.8%, and the published GPT-4 Mystery line is 4.3%. Even substituting the worst
plausible true NT rate (~4%) leaves the McNemar at p < 1e-100. The 0.0% cell value is
partly instrument-flavored; the collapse and the contrast are not.
> ANSWER (accept the robustness reading / require the stripped-block regrade first):
>

**3. Extraction-injection audit on Mystery WT (pre-committed before any NO-RESCUE call;
run although verdict is RESCUE):** injection 11/600 (1.8%); **125/569 delivered Mystery
WT plans were lost to residual PDDL-shorthand dialect** (`feast b c` for the example's
full phrasing — the calibration's 2/20 residual, at scale). Both effects bias AGAINST
the tools arm: with a dialect-tolerant parse the Mystery WT rate would be ~90%+, so
RESCUE is reached despite, not because of, the instrument. Clean WT instrument losses:
7 misses + 8 injections.

**4. Mediators / intercurrent events (treatment-policy, counted as failures):**
loop_exhausted clean WT 63/600 (10.5%), Mystery WT 31/600 (5.2%) — vs 0/80 in
calibration; the real 4/5-block instances are harder. Delegation 100% both WT cells;
caching active; no crash, one connectivity blip absorbed by SDK retry.

## Descriptive context (per amendment M — labelled published reference, no test)

GPT-4 (2023, one-shot NL, published grader epoch, n=600): clean 34.3%. Haiku 4.5
with tools: clean **69.7%**, Mystery **71.8%** — both above the published GPT-4 clean
bar; Haiku matched-NT clean 47.8% is also above it, Mystery matched-NT 0.0% far below.
The controlled contrast remains WT vs matched-NT within Haiku; the bare-NT 200-trial
completion at n=600 (amendment K) is still owed before NT-vs-GPT-4 prose.

Funnel note (exploratory): P(correct | extracted) is 95.9% / 97.3% — once a plan
survives formalization and dialect, delegated search is essentially always right. The
funnel bottleneck on this instrument is the input boundary (formalization) plus the
extractor's dialect intolerance, not search and not tool operation.

## Deviation table

| # | deviation | consequence |
|---|---|---|
| 1 | Run paused by Omer 08-01 (~09:05 UTC) and resumed; 18 loop-exhausted trials re-attempted on resume (temp 0) | ≤$0.60; deterministic re-attempts; final data uses last attempt per instance |
| 2 | One connectivity blip mid-run | absorbed by SDK timeout/retry; no trial lost |
| 3 | loop_exhausted 10.5%/5.2% vs calibration 0/80 | frozen apparatus held (MAX_TOOL_LOOPS=10); counted as delivered failures per treatment-policy |
| 4 | Clean criterion (a) raw fail, decomposed model-side (7/443 instrument) | ANSWER slot above |
| 5 | Mystery NT narration-injection at scale (479/600) | robustness shown (0/121 uninjected); ANSWER slot above; optional stripped-block regrade available |
| 6 | Mystery WT dialect losses 125/569 | conservative (against hypothesis); no correction applied |
| 7 | Confirmatory cost $39.87 vs gate projection $34.08 | loop-exhaustion overhead; within revised $40–45 estimate |

## Owed next

1. **`formalization_match` (§4)** over the stamped tool-call side-logs (pddl-parser
   `inspect_problem`/`inspect_domain`, 24-bijection domain check, gold reconstruction) —
   finalizes the mechanism branch; exploratory family otherwise.
2. **Bare-NT 200-trial completion** (100 clean + 100 Mystery on the _3 pools, ≈$1.5) so
   published NT rows share the n=600 denominator (amendment K).
3. Omer's two ANSWER slots above; then paper-prose planning (Act 4 secondary claim).
4. Optional robustness: stripped-block regrade of the 479 injected Mystery NT trials.
