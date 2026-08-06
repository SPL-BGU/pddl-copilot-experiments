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

**Mechanism (prediction ii): RESCUE branch CONFIRMED — all three requirements met**
(third requirement computed 2026-08-05, section below). Delegation = 100.0% of WT
trials in both domains (≥80% required ✓); paired |clean_WT − mystery_WT| = **2.2pp**
(b=119/c=132, exact p=0.449 — within the ±7.5pp margin, let alone the branch's ±10pp
✓); Mystery `formalization_match` = 97.8 [96.3, 98.7] vs clean 96.3 [94.5, 97.6] —
overlapping CIs, Mystery numerically HIGHER, so it is not CI-disjointly below clean ✓.
The joint falsifier (Mystery WT ≈ Mystery NT) is trivially refuted.

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
> **Accept the decomposition reading** (Omer, 2026-08-06). The criterion names the
> model's planning, not the apparatus: 7/443 instrument misses (parser 98.4% on
> plan-bearing blocks) vs 157 model-side non-deliveries. Same reading signed at the
> run-2 gate, extended to the real cell. No apparatus restart; numbers stand as
> reported (treatment policy already counts all 164 as failures).

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
> **Accept the robustness reading** (Omer, 2026-08-06). The collapse is real even if
> the 0.0% cell value is partly instrument-flavored: 0/121 on the uninjected subset,
> bare-NT 4/600 = 0.7% at the completed n=600 denominator (zero injection exposure on
> the `_3` extension), published GPT-4 4.3%; the worst plausible substitution leaves
> the McNemar at p < 1e-100. Report 0/600 with the injection caveat; the stripped-block
> regrade (item 4) stays optional, not required for sign-off.

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

## formalization_match (§4) — computed 2026-08-05, mechanism branch finalized

**Analyzer:** `.local/wt_run/formalization_match.py` (+ per-trial rows in
`formalization_match_rows.jsonl`); instrument = the pddl-parser plugin's own
`inspect_problem`/`inspect_domain`/`get_trajectory` functions imported at analysis time
(kept out of the model's roster, per §4). Inputs = the stamped tool-call side-logs,
deduped LAST record per instance_id (518→500 on blocksworld = the 18 pause/resume
re-attempts; other three cells exact). **Precondition re-verified and extended:** gold
reconstruction from the NL query is 1200/1200 exact across all four WT pools
(`verify_gold_reconstruction.py` — the prereg's 500/500 claims plus both amendment-K
`_3` pools, which the original verification predated), with zero side-log
`query_sha256` mismatches against the response files.

**Operationalization (recorded, not in the prereg text):** a trial's formalization =
the LAST `classic_planner` call's (domain, problem) arguments — the model's final
settled statement; an any-call upper bound is reported as a diagnostic. "solvable" =
the logged Fast Downward result of that same call contains a non-empty plan; note this
conditions on the MODEL's domain, where Planetarium's solvable stage conditions on a
gold domain, so the two solvable rows are not directly comparable. Problem equality =
(objects, init, goal) literal-set equality under the config-declared object bijection
plus an arity-constrained brute-forced predicate bijection (≤6 candidates); domain
equivalence = 24 arity-constrained bijections structurally, behavioral fallback =
gold-plan replay through the model's domain+problem (fallback validated on synthetic
positive and negative controls after an initial parenthesis-stripping bug in the
final-state parse was found and fixed — first pass undercounted clean domain
equivalence 29.3%→69.5%; no other column moved).

| stage (denominator 600) | clean WT | Mystery WT |
|---|---|---|
| delegated (≥1 `classic_planner` call) | 600/600 = 100.0 [99.4, 100.0] | 600/600 = 100.0 [99.4, 100.0] |
| parseable (model problem+domain parse) | 594/600 = **99.0** [97.8, 99.5] | 588/600 = **98.0** [96.5, 98.9] |
| solvable (FD plan on last call) | 418/600 = 69.7 [65.9, 73.2] | 572/600 = 95.3 [93.3, 96.8] |
| **formalization_match (problem ≡ gold)** | 578/600 = **96.3** [94.5, 97.6] | 587/600 = **97.8** [96.3, 98.7] |
| domain equivalent (structural + behavioral) | 417/600 = 69.5 [65.7, 73.1] | 597/600 = **99.5** [98.5, 99.8] |
| any-call match (diagnostic upper bound) | 597/600 = 99.5 | 597/600 = 99.5 |
| P(correct \| match) | 418/578 = 72.3 | 431/587 = 73.4 |
| P(correct \| no match) | **0/22 = 0.0** | **0/13 = 0.0** |

**Verdict on the branch's third requirement: MET** — Mystery formalization_match is
not CI-disjointly below clean (it is numerically above it). Combined with delegation
100% and the 2.2pp paired delta, **the RESCUE branch of prediction (ii) is final: the
NL→PDDL formalization boundary transfers to the obfuscated domain essentially intact,
and the rescue is formalize-then-delegate, not model-side search.** Companion
diagnostics per §4: delegation 100% both cells; accuracy conditional on delegation =
the cell accuracies (69.7 / 71.8).

Three secondary observations, all model-side:

1. **The metric is a perfect gate on delivered correctness:** 0 of the 35 no-match
   trials were graded correct, in both domains. A boundary loss is never recovered
   downstream, which is the funnel-placement claim (§4) observed in data.
2. **The clean ceiling is domain-authoring fidelity, not problem statement and not
   search:** clean P(solvable | domain equivalent) = 415/417 = 99.5% vs
   3/183 = 1.6% without — the FD-failure mass IS the broken-domain mass. Haiku
   transcribes the Mystery domain near-perfectly (99.5% equivalent, all structural)
   because the obfuscated NL is a mechanical 1:1 rendering of the PDDL; the clean NL
   states physics informally (e.g. never says stacking makes the moved block clear),
   and Haiku authors what the text says — 183/600 clean domains cannot even replay
   the gold plan, which is where the honest "unsolvable" empty blocks and part of the
   loop exhaustion come from (audit 1's 94 + deviation 3). The paired WT contrast is
   unaffected: the two arms agree because the problem-side boundary holds in both.
3. **No-match tail decomposition:** clean 22 = 11 init mismatches + 5 goal mismatches
   + 4 unparseable + 2 empty-argument calls; Mystery 13 = 12 unparseable (final
   problem omits the `(:domain ...)` line — the tool rejected the call at run time,
   loop ended before repair) + 1 goal mismatch. Every one graded incorrect, so
   instrument and grader agree on the entire tail.

Planetarium's published GPT-4o decomposition (96.1 / 94.4 / 24.8) is the intended
prose anchor for these rows and remains flagged for `/verify-claims` before any paper
use, as does the different solvable conditioning noted above.

## Bare-NT completion at n=600 (amendment K debt) — run + graded 2026-08-06

Approved by Omer 2026-08-06; ~$1.5 (estimate; single-completion trials). 100 clean +
100 Mystery on the `_3` pools, engine token `anthropic` (the graded 06-22 NT path:
native PlanBench prompt, no scaffold), plain invocation (trap 5 honored — these
configs had no prior bare-NT response files), graded with the same patched
`response_evaluation.py` + Rosetta VAL epoch.

| row (denominator 600) | correct | % | Wilson 95% |
|---|---|---|---|
| Haiku bare-NT clean (205/500 + 58/100) | 263/600 | **43.8** | [39.9, 47.8] |
| Haiku bare-NT Mystery (4/500 + 0/100) | 4/600 | **0.7** | [0.3, 1.7] |
| GPT-4 clean, published grader (157/500 + 49/100) | 206/600 | 34.3 | [30.6, 38.2] |

**The NT-vs-GPT-4 line survives the denominator completion** (amendment L: reported
whichever way it fell): Haiku's clean bare-NT lower bound 39.9 sits above GPT-4's
upper bound 38.2 at the shared n=600 denominator — the extra pool needed ≥~50/100 and
Haiku scored 58 (GPT-4: 49). GPT-4 remains a labelled published reference line per
amendment M — descriptive CI separation, no paired test. Mystery bare-NT at n=600
confirms the collapse on the full published pool (0.7%), and adds a third anchor to
audit 2's robustness case: bare-NT 4/600 with zero injection exposure on the `_3`
extension.

## §9-A directive-only sensitivity arm — run + graded 2026-08-06

Approved by Omer 2026-08-06; measured **$2.61** (side-log token sums at Haiku 4.5
pricing; caching structurally absent as expected — prefix below the cacheable
minimum). Engine `pddl_copilot__anthropic-directive__claude-haiku-4-5`
(planbench/engine.py, commit 36e6292): byte-identical WT scaffold including the
dangling "Your ONLY way … is by calling the provided tools" directive, tools
parameter OMITTED (the pre-registered wire substitution). Mystery t1, full 600 pool —
the §9-A bullet's n=250 predates the whole-pool ANSWER and amendment K, and no draw
file was ever committed (the subsample machinery was struck as dead code), so
whole-pool preserves denominator identity; recorded as the operationalization.
600/600 non-empty deliveries; graded with the same Rosetta VAL epoch.

**Amendment N's four-rung ladder (Mystery t1, n=600, one grader):**

| rung | correct | % | Wilson 95% |
|---|---|---|---|
| native prompt (bare NT) | 4/600 | 0.7 | [0.3, 1.7] |
| scaffold-only (matched NT) | 0/600 | 0.0 | [0.0, 0.6] |
| directive-only (dangling directive, no tools) | 3/600 | **0.5** | [0.2, 1.5] |
| scaffold + tools (WT) | 431/600 | **71.8** | [68.1, 75.3] |

**The pre-registered outcome-neutral prediction holds: the directive alone moves
nothing.** All three tool-less rungs sit in one overlapping 0–1.7% band; the only
rung that moves is actual tool attachment. The +71.8pp contrast is attributable to
tool availability, not to prompt framing, scaffold shape, or the directive text —
closing the pure-availability confound the arm was pre-registered to test.

## Stripped-block regrade of the injected Mystery matched-NT trials — run 2026-08-06

Audit 2 hardening (Owed next item 4), executed after Omer signed the robustness
slot. New side script `.local/wt_run/stripped_block_regrade.py` (graded corpora
untouched, no `response_evaluation.py` re-run): for each of the 600 Mystery
matched-NT trials, re-extract using ONLY the text inside the model's
`[PLAN]..[PLAN END]` block (no block / empty block = failure), convert with the
grader's own `text_to_plan`, validate with the same Rosetta VAL epoch. The script's
injection cross-check reproduces the audit definition exactly: 479/600, tying to
deviation 5. Coverage: 600 delivered, 3 no-block, 36 empty-block, 1 block parsed
to empty plan, 560 VAL invocations.

**The expected ~0 did NOT hold — reported as measured:**

| layer (n=600) | correct | % | Wilson 95% |
|---|---|---|---|
| matched-NT, full-text grading (graded corpus) | 0/600 | 0.0 | [0.0, 0.6] |
| matched-NT, stripped-block regrade | 26/600 | **4.3** | [3.0, 6.3] |

All 26 are 0→1 flips: the narration injection had DEPRESSED the cell — scraped
extra actions invalidated 26 otherwise-valid block plans. So the audit-2 bias
direction stated in deviation 5 ("inflates the WT−NT delta in our favor") is
confirmed and now quantified: the honest matched-NT rate is 4.3%, not 0.0%, and it
lands exactly at the "worst plausible true NT rate (~4%)" the signed slot already
priced in. Re-running the paired PRIMARY contrast against the stripped layer:
WT 431/600 vs stripped-NT 26/600, discordant b=412 / c=7, exact McNemar
**p = 6.4e-112** — under the signed slot's p < 1e-100 threshold; paired Δ = +67.5pp
(vs +71.8pp on the graded layer). The band verdict is a function of WT successes
only, so RESCUE is untouched.

Descriptive notes (amendment M language, no tests): the stripped matched-NT 4.3%
coincides numerically with the published GPT-4 Mystery line (4.3%, published
grader) and is CI-disjoint above bare-NT 0.7 [0.3, 1.7] — the scaffold plus
block-only extraction recovers a small nonzero Mystery rate that bare prompting
does not. For prose: per the signed slot, report the graded 0/600 with the
injection caveat, and cite this measured 4.3% [3.0, 6.3] as the instrument-robust
reading with the contrast surviving at p = 6.4e-112.

## Deviation table

| # | deviation | consequence |
|---|---|---|
| 1 | Run paused by Omer 08-01 (~09:05 UTC) and resumed; 18 loop-exhausted trials re-attempted on resume (temp 0) | ≤$0.60; deterministic re-attempts; final data uses last attempt per instance |
| 2 | One connectivity blip mid-run | absorbed by SDK timeout/retry; no trial lost |
| 3 | loop_exhausted 10.5%/5.2% vs calibration 0/80 | frozen apparatus held (MAX_TOOL_LOOPS=10); counted as delivered failures per treatment-policy |
| 4 | Clean criterion (a) raw fail, decomposed model-side (7/443 instrument) | ANSWER slot above |
| 5 | Mystery NT narration-injection at scale (479/600) | robustness shown (0/121 uninjected); ANSWER slot above; stripped-block regrade DONE 08-06: true rate 4.3%, contrast survives (section above) |
| 6 | Mystery WT dialect losses 125/569 | conservative (against hypothesis); no correction applied |
| 7 | Confirmatory cost $39.87 vs gate projection $34.08 | loop-exhaustion overhead; within revised $40–45 estimate |

## Owed next

1. ~~**`formalization_match` (§4)**~~ DONE 2026-08-05 (section above) — mechanism
   branch final: RESCUE branch confirmed.
2. ~~**Bare-NT 200-trial completion**~~ DONE 2026-08-06 (section above) — published NT
   rows share the n=600 denominator (amendment K).
3. ~~Omer's two ANSWER slots above~~ BOTH FILLED 2026-08-06 (accept + accept) —
   paper-prose planning (Act 4 secondary claim) is now unblocked.
4. ~~Optional robustness: stripped-block regrade~~ DONE 2026-08-06 (section above) —
   NOT ~0: true matched-NT rate 4.3% [3.0, 6.3]; contrast survives at p = 6.4e-112.
