# PlanBench WT prereg — decisions memo for the open slots (2026-07-25)

**Status:** RECOMMENDATIONS for Omer. Each §N below ends in a paste-ready block; the
blocks are already pasted into `development/planbench/planbench_wt_prereg.md` marked
`RECOMMENDED … pending RATIFY`, so the prereg reads as a complete document and the
single gate is still the §9 RATIFY slot. **No build or spend before ratification.**

**Method.** A 7-agent evidence workflow ran read-only over the repo, the on-disk
PlanBench corpora, the graded NT layer, our frontier cost corpora, and the external
literature (1.8M tokens; investigators: instance-pool audit, cost model, funnel/scoring
audit, statistics, runner/adapter audit, literature, preregistration standards). The
workflow's decision-and-red-team phases died on a session limit, so the adjudication
below is mine, with the load-bearing repo facts re-verified directly
(`REQUIRED_PLUGINS`, the engine-name allowlist, `PDDL_COPILOT_RENDER_FROM_TOOLS`,
`astar_lmcut`, `WITHOUT_TOOLS_SYSTEM_BY_TASK`, `MAX_TOOL_LOOPS`) and the band cutpoints
recomputed from scratch. Two external citations were spot-fetched (Göbel et al.
arXiv:2603.06064 and Huang & Zhang ACL 2025); the rest of the literature block is
flagged for `/verify-claims` before anything from it enters prose.

**Headline of this memo.** The design survives, but **five of the prereg's stated
premises are measurably false**, and two of them would have silently produced wrong
numbers rather than an error:

| # | premise as written | measured reality |
|---|---|---|
| 1 | "S … reused verbatim in all four t1 cells and the t3 pair", drawn from "the 500-instance pool" | t1 ids are 2..501, t3 ids are 1..500; intersection 499. A draw including id 501 silently makes t3 n=249 |
| 2 | "stratified by gold-plan-length quartile" | 8 distinct even lengths; quartile cuts land on the three modal values → strata 200/139/113/48, not 125 each |
| 3 | "full marketplace roster (pddl-parser, pddl-solver, pddl-validator)" | `run_experiment.py:122` exposes solver+validator only, 7 tools |
| 4 | "upstream `response_evaluation.py` unmodified" | three robustness patches are applied in place (`planbench/apply_patches.py` patch 5 A/B/C) — the same build that graded the NT layer |
| 5 | "t2 excluded — optimal_plan tool unbuilt" | `classic_planner(strategy="astar_lmcut")` = `astar(lmcut())`, optimal (`solver_server.py:247,411`) |

Plus two **silent-wrong-number** hazards that no existing audit catches:
`build_table.acc()` divides by 500 regardless of the subsample (measured: reports
22.2% where the truth is 44.4%), and `PDDL_COPILOT_RENDER_FROM_TOOLS` defaults to `1`,
which renders the t3 verdict from the last tool result and never reads the model's
final message — i.e. the cell would measure tool-verified, contradicting the
delivered-primary ruling.

---

## 1. §2 — subsample size, seed, and how S is actually fixed

**DECIDED 2026-07-25 (Omer): run the WHOLE POOL, 500 per cell**, to match the
leaderboard corpus. This supersedes the n=250 recommendation below, and it is the
stronger design on four counts beyond comparability: it deletes the entire subsample
apparatus (no seed, no strata, no id list, and no t1-vs-t3 intersection problem, since
each task runs its own full pool), it raises the sample-size justification class from
resource-constrained to whole-population, it makes both silent subsampling hazards inert
(the `build_table` denominator and the evaluator's `--specific_instances` filter), and it
fixes the one under-powered prediction — exact McNemar 80%-power MDE on t3 falls from
+9.0pp to +6.0pp, and power at a WT t3 of 85% rises from 0.58 to 0.88. Cost is the one
real constraint: the t1 2x2 at the whole pool is ~$46 central (65% of the remainder) and
six cells ~$59 (84%), so §8 fixes a spend priority (t1 2x2 first, t3 pair second) and the
t3 pair is the cell that drops to 250 if the gate says six cells do not fit — t3's
external comparability is already broken by the corpus mismatch (§5), so subsampling it
forfeits nothing.

**Original bottom line (retained as the costed fallback spec).** n=250 is affordable with
2-4x headroom, so money is not the binding constraint and the prereg should stop
presenting it as one. But "seed 20260724 + quartile stratification" does not pin S, so as
written this is not a pre-registration. Fix the pool (499-id intersection), fix the strata
(discrete length value x t3 verdict), **materialize the realized id list before the
gate**, run the cheap no-tools cells at the full pool.

**Cost.** Four independent estimates of Haiku WT $/trial on PlanBench: $0.0348
(parametric model fitted to our five measured frontier WT cells, ±0.2% on three of
them), $0.014-0.024 (prompt-size scaling), $0.0328 (frontier stage-1 probe), and
$0.0447 (assumption-free "behaves exactly like our measured `solve` cell"). Recommended
shape at central: WT 750 trials ≈ $23.4, matched-NT 1497 trials ≈ $11.2, third control
arm ≈ $2.1, calibration ≈ $1.5 → **≈ $38 of the ~$70.6 remainder (54%)**. The
pessimistic band breaches (≈$90), which is what the gate and the shrink order exist
for. Worst legal trial (10 loops) is ≈$0.135, and the measured loop_exhausted rate on
our own apparatus is 1/4560.

**Power.** n=250→200 costs almost nothing except on t3: exact McNemar for a paired
78.2→90.0 shift with 5% leakage gives p=2.4e-05 at n=250 and 1.8e-04 at n=200, and the
paired-delta half-width moves 5.5pp → 6.2pp. Clean t1 has power 1.0000 to spare at
every WT value considered. **So the prereg's valve is pointed at the wrong cell:** it
trims n uniformly and names t3 as the only cuttable pair, when t3 is the one cell
where power is scarce and clean t1 is where it is free.

**Why the no-tools cells go to the full pool.** They are single-turn and 4.7-5.0x
cheaper per trial ($0.0069-0.0083). Running all three at 499 instead of 250 costs
≈$5.6 central and buys: the NT side leaves the subsampling story entirely, the
matched-NT point estimates get ~2x the precision of the WT cells they anchor, and the
bare-NT→matched-NT scaffold delta becomes fully paired against the published n=500
rows. The one thing it must not do is create analysis latitude, hence the explicit
sentence that the confirmatory paired tests run on S only.

**Why the seed alone is not enough.** A reference implementation of "seed 20260724,
length-quartile, n=250, proportional + largest-remainder" produced an S that excludes
id 501, induces a t3 VALID share of 61.2% against the pool's 64.8%, and shifts
NT-recomputed-on-S by up to 5pp (mystery t3 50.4 vs 45.4 on the full pool). Two agents
implementing the same sentence get different S values.

> ANSWER (paste into §2, n + seed slot):
>
> **n and pool.** S is drawn from the **499-id t1∩t3 intersection (instance_ids
> 2..500)**, not the 500-instance t1 pool: t1/t2 ids are 2..501 and t3 ids are 1..500
> (measured), so a draw containing id 501 would silently reduce the t3 cells to n=249.
> **|S| = 250** for the with-tools cells. The three matched-no-tools cells run the
> **full 499-id pool**; the confirmatory paired tests are computed on S only, and the
> extra 249 no-tools rows are a labelled secondary precision estimate for the NT cell
> and for the bare-NT scaffold delta, never entering a paired test.
>
> **Stratification.** Proportional allocation with largest-remainder over the crossed
> strata **(gold-plan-length value, collapsed: {2,4} / {6} / {8} / {10} / {12,14,16})
> x (t3 gold verdict: VALID / INVALID)**. "Quartile" is struck as not implementable:
> gold plan lengths take 8 even values {2:30, 4:56, 6:114, 8:139, 10:113, 12:46, 14:1,
> 16:1} and the quartile cuts 6/8/10 coincide with the three modal values, giving
> strata of 200/139/113/48. Verdict enters because t3 accuracy is strongly
> verdict-conditional in the graded NT layer (blocksworld VALID 73.1 [68.1,77.7] vs
> INVALID 87.5 [81.8,91.6]; mystery 25.9 vs 81.2), so the t3 marginal is a mixture
> whose value tracks the VALID share; the joint scheme ties or dominates every
> alternative in Monte Carlo at both n (bw t3 sampling SD 1.83 SRS → 1.76).
>
> **Seed and materialization.** Seed **20260724**, `random.Random(20260724)`, strata
> iterated in sorted (length-bin, verdict) order, proportional + largest-remainder
> allocation. The seed alone does not pin S (a reference draw shifted NT-on-S by up to
> 5pp), so the drawing script `planbench/draw_wt_subsample.py` **and the realized id
> list** `planbench/wt_subsample_S.json` (250 ids + stratum labels + sha256) are
> committed **before the calibration gate**; the prereg's S is that file, not the
> procedure.
>
> **Pre-committed escalation (cost-only, increase-only).** If the calibration gate's
> projection at **p90** measured $/WT-trial for the full-pool design is **≤ $50**
> (≈71% of the remainder, holding a ~20% reserve), the with-tools cells run the full
> 499-id pool instead of S. This decision is made before any confirmatory trial and
> reads **only** $/trial, turns/trial, cache-read fraction and wall-clock — never
> graded accuracy and never the WT-vs-NT contrast. Escalation raises the sample-size
> justification from resource-constrained to whole-population, lets every WT row share
> a denominator with the published n=500 bare-NT layer, and cuts the pre-registered
> INCONCLUSIVE band mass from 45/251 outcomes to 63/500 (§3).
>
> **Shrink order if the gate's projection misses $50** (cost-only, in this order, never
> whole-cell deletion inside the t1 2x2): (1) drop the pure-availability sensitivity
> arm; (2) matched-NT from 499 back to |S|; (3) clean-t1 WT n 250→150 (power 1.0000 to
> spare at every pre-registered WT value); (4) **t3 last**, 250→200 — t3 is the only
> power-scarce cell (exact McNemar MDE at 80% power = +9.0pp at n=250 vs +10.4pp at
> n=200 under 10% leakage), so the previous wording, which trimmed uniformly and named
> t3 as the only cuttable pair, is inverted here. If even step (4) misses, kill
> criterion (a) fires for the whole arm.
>
> **Correspondence check: PASSED, recorded now** (not contingent). Mystery is not
> merely a deterministic obfuscation but a pure symbol rename with an identity object
> mapping, verified at four levels: 501/501 instance files isomorphic (identical
> `:objects`, predicate-mapped `:init`/`:goal` literal sets), 500/500 t1 gold plans
> action-for-action isomorphic with identical lengths, 500/500 t3 candidate plans
> isomorphic, 500/500 t3 gold verdicts identical. The "if it fails, mystery gets an
> independent draw and contrasts become unpaired" fallback is struck as dead code, and
> clean-vs-mystery is committed as paired. Note the stray
> `instances/blocksworld/mystery/generated_basic/instance-0.pddl` (mystery-only, not a
> rename of any clean instance, unused at `start=1`): never enumerate the pool by
> directory glob.
>
> **Denominator (blocking).** TOTAL = |S| (or 499 if escalated). `build_table.acc()`
> divides by `len(instances)` = 500 regardless of the subsample: replaying the real
> graded bw-t1 file with 250 instances stripped returns 22.2% where the truth is 44.4%.
> Filter the response JSON to S before grading, or pass S to the table builder. Do
> **not** pass `--specific_instances` to `response_evaluation.py` — its filter mutates
> a module-level list and silently grades everything after the last matched id
> (unpatched at :92-96, :155-159, :254-258); the evaluator already skips
> empty-response instances, so a subsampled run yields denominator = |S| naturally.

---

## 2. §3 — outcome bands, attainability, and making prediction (ii) a real test

**Bottom line.** Three defects, all fatal to the prereg's purpose if left: the band
rule cannot classify some of its own possible data, the ">= 90" bands are unattainable
for instrument rather than capability reasons, and prediction (ii) as written cannot
fail. All three are fixable with wording plus one cheap measurement.

**(a) The partition has a hole.** "NO-RESCUE = CI upper < 5; PARTIAL = CI midpoint in
[5,50); RESCUE = CI midpoint >= 50" leaves exactly 5 integer outcomes unclassifiable
at each n (x=6..10 of 250; x=4..8 of 200). The Wilson midpoint is also not the point
estimate: mid − p̂ = [z²/(n+z²)](0.5 − p̂), so "midpoint < 5%" really means p̂ < 4.31%
at n=250. The RESCUE boundary is unaffected (the bias vanishes at 0.5).

**(b) ">= 90" is not reachable as a CI-backed claim.** Wilson lower ≥ 90 needs
p̂ ≥ 94.0% at n=250 (235/250). The measured clean-t1 extraction ceiling is **94.4%**
(472/500 non-empty extractions on the graded NT rows), so the band would require the
WT arm to hit the instrument ceiling with essentially zero plan errors among extracted
plans (P(correct | extracted) ≥ 0.953). Note the prereg's own premise was *pessimistic
in the wrong place*: the ~10-12% loss it cites is a **t2** number conditioned on the
`[PLAN]` marker; the extractor does not require that marker, and measured t1 extraction
is 94.4% clean / 89.6% mystery.

**(c) The extractor actively penalizes the arm most likely to trip it.** Measured
against the real extractor: a plan pasted verbatim from `classic_planner` extracts to
nothing (0 of 4 lines — `(unstack a b)` tokenizes as `(unstack`); markdown-bolded
actions extract to nothing; shorthand names extract to nothing; and **one narrating
sentence before the plan injects a duplicated action** that VAL then rejects. On t3 the
grader is first-mention-wins and case-sensitive: "The plan is VALID." grades as
ungraded-hence-incorrect, and the preamble "Let me check whether the plan is valid…"
flips a correct INVALID verdict to VALID. Every one of these biases *against* the
with-tools arm, which is the arm holding a solver whose output is canonical PDDL. This
is a plausible route to a spurious 0.0% mystery cell.

**(d) Prediction (ii) is the Nosek et al. failure mode** ("a prediction so vague that
many outcomes can be rationalized as supporting it"). The accepted fix in the
Registered Reports literature is not to pick a direction: it is per-branch
mechanistic signatures plus a stated joint falsifier plus outcome-neutral quality
tests. We can do better than wording here, because the mechanism is measurable —
see §3 of this memo (the formalization-boundary metric) and the delegation-rate
telemetry.

**(e) The literature says the outcome distribution is bimodal, and that architecture
decides, not tier.** Verified directly: Göbel et al. (arXiv:2603.06064) ran **Claude
Haiku 4.5** with PDDL operations exposed over MCP on 102 IPC Blocksworld instances and
got **63.7% → 66.7% (+3.0pp)** at 5.7x token cost, because the tools exposed a
step-wise simulator and the model kept the search. Huang & Zhang (ACL 2025) report the
opposite regime — models that formalize and delegate are "robust to lexical
perturbation". So the single most informative thing to log is **whether the trial
delegated search to `classic_planner` at all**. Without it, a persistence result is
indistinguishable from Göbel's published +3pp and a rescue result is
indistinguishable from Huang & Zhang's published formalizer numbers.

> ANSWER (paste into §3, band-threshold slot):
>
> **Estimand first (ICH E9(R1) attributes).** Treatment = tool availability (the
> 7-tool harness roster plus the tool-use directive) vs its no-tools mirror;
> population = S; endpoint = the **delivered** final message graded by the patched
> upstream evaluator, t1 `llm_correct` and t3 **`llm_correct_binary`** (named
> explicitly: the three t3 fields differ by up to 19.4pp on identical responses —
> binary 78.2 / w_type 68.2 / w_expl 58.8 — and the published NT layer and the GPT-4
> 94.6 comparator are both on binary; w_type and w_expl are secondary); summary =
> per-cell proportion with Wilson 95% CI plus the paired Δ on S; intercurrent events
> per the §10-F exclusion table (treatment-policy: counted as failures, denominator
> = |S|).
>
> **(i) Mystery t1 WT — four-outcome evidential partition** (exhaustive and disjoint
> by construction; verified by enumerating every integer outcome, and mirroring the
> PASS/FAIL/UNDERPOWERED shape already ratified in `ntster_h4_prereg.md`):
>
> | verdict | rule | counts at n=250 | counts at n=499 |
> |---|---|---|---|
> | NO-RESCUE | Wilson upper < 5% | x ≤ 5 (≤2.00%) | x ≤ 15 (≤3.01%) |
> | PARTIAL | CI entirely within [5,50) | x ∈ [20,109] | x ∈ [35,227] |
> | RESCUE | Wilson lower ≥ 50% | x ≥ 141 (≥56.40%) | x ≥ 272 (≥54.51%) |
> | INCONCLUSIVE | CI spans 5% or 50% | x ∈ 6..19 or 110..140 | x ∈ 16..34 or 228..271 |
>
> "CI midpoint" is struck: the Wilson midpoint is not the point estimate
> (mid − p̂ = [z²/(n+z²)](0.5 − p̂), so "midpoint < 5%" means p̂ < 4.31% at n=250), and
> the literal rule left 5 integer outcomes unclassifiable at each n. **Anchors:** 5% =
> ~2.5x the measured bare-NT mystery Wilson upper bound (2.0% at n=500) and just above
> the smallest value distinguishable from it at n=250 (Wilson half-width 2.8pp at
> p=0.05); 50% = solved more often than not, which in evidential form demands
> p̂ ≥ 56.4% (n=250) / 54.5% (n=499). A declared INCONCLUSIVE region is the
> falsifiability feature, not an escape hatch: 45/251 outcomes at n=250 and 63/500 at
> n=499 fall in it, which is a second reason to prefer the §2 escalation. Every verdict
> is additionally reported against the two published bands — verifier-in-the-loop
> ~3.8-14% and formalize-then-delegate ~63-100% (pending `/verify-claims`) — with pool
> size and grader on the same line, since "Mystery Blocksworld" denotes at least five
> different pools in the literature (ours 500; Valmeekam 600; LLMFP 602; H&Z/CoPE 100;
> La Malfa 93).
>
> **Clean t1 WT is demoted from a prediction to an OUTCOME-NEUTRAL apparatus
> criterion** (Registered Reports device), thresholded on the two DECOMPOSED quantities
> rather than on the combined number [updated 07-25]: (a) **extraction rate ≥ 90%**
> (measured NT clean t1 = 94.4%, 472/500) and (b) **P(correct | extracted) ≥ 90%**
> (measured NT = 43.4%, 205/472). A failure then names which stage broke — the
> benchmark's text parser or the model's planning — while raw delivered accuracy stays
> the reported primary for comparability with the NT layer and the GPT-4 rows. The old
> raw ">= 90" band is struck as unattainable-by-instrument at any n: Wilson lower ≥ 90
> needs p̂ ≥ 92.8% at n=500 / 94.0% at n=250 against a 94.4% extraction ceiling, i.e.
> P(correct | extracted) ≥ 0.95. Failing (a) is an apparatus-fix-and-restart event, never a scope
> decision; failing (b) with (a) passing is recorded as a scaffold/capability ceiling
> that bounds the mystery cell's interpretation.
>
> **(ii) Two-branch mechanism test with a joint falsifier** (replaces "both directions
> publishable"). Stated directional prior: we expect RESCUE, p≈0.6, because mystery is
> a verified pure symbol rename with identity object mapping (501/501) and Fast
> Downward is name-blind, and Huang & Zhang (ACL 2025) find formalizers robust to
> lexical perturbation; the counterweight is Göbel et al. (arXiv:2603.06064), who got
> only +3.0pp with **this same model** (Haiku 4.5) and PDDL tools over MCP on clean
> Blocksworld because the tools exposed a step-wise simulator and the model kept the
> search.
> - **RESCUE branch** additionally requires: mystery `formalization_match` (§4) not
>   CI-disjointly below clean; delegation rate (share of trials calling
>   `classic_planner`) ≥ 80%; and paired |clean_WT − mystery_WT| within **±10pp**.
> - **PERSISTENCE branch** additionally requires the loss to be charged at the named
>   formalization boundary: mystery `formalization_match` CI-disjointly below clean,
>   while the clean cell formalizes successfully.
> - **JOINT FALSIFIER:** mystery WT statistically indistinguishable from mystery
>   matched-NT with the same per-stage failure profile as clean WT (tools changed
>   nothing anywhere in the cascade) → the arm's mechanism claim is reported as
>   **unsupported**, not narrated either way.
> - The ±10pp equivalence margin is what n supports and is stated as such: paired TOST
>   at n=250 has power 0.96 at the plausible discordance ψ=0.18 and certifies ±10pp up
>   to ψ=0.29; **±5pp is not pre-registrable** (power 0.18 at n=250; it would need
>   ~617 pairs). The 5.26pp post-hoc CI half-width must not be quoted as licence for a
>   ±5pp margin.
>
> **(iii) t3, with its power stated instead of assumed.** Confirmatory: exact McNemar
> paired WT vs matched-NT on S. Band: WT t3 p̂ ≥ 90 with Wilson lower ≥ 85, anchored on
> our own measured Haiku frontier with-tools validation delivered rates (96-99) minus
> headroom for the added NL→PDDL step, against the NT anchor 78.2 [74.4,81.6] and
> GPT-4's 94.6. **Pre-registered MDE:** at n=250 power is 0.94 if WT t3 reaches 90% and
> the tool breaks ≤10% of NT successes, but only 0.58 if WT t3 lands at 85%; the
> 80%-power MDE is +9.0pp (n=250) / +10.4pp (n=200) under 10% leakage. A true +7pp
> improvement will therefore likely be missed, and that is pre-declared rather than
> reinterpreted afterwards. **Conjunctive ruling table, fixed now:** McNemar
> significant + band met = prediction supported; significant + band missed = "gap
> narrowed, not closed" (reported as such, no rescue language); not significant + band
> met = level reached without a demonstrable paired lift, reported descriptively;
> neither = not supported. **Mandatory alongside:** the VALID/INVALID confusion matrix,
> FPR/FNR, and the constant-VALID degenerate baseline (324/499 = 64.9% [60.5,68.9];
> 64.8% [58.7,70.5] at n=250) — Haiku NT 78.2 is only +13.4pp above always-answering
> VALID, and published Mystery-BW verification "accuracy" of 79.6% has been shown to be
> an always-invalid artifact (FNR 97.1%), so a marginal lift must be shown not to be a
> response-bias shift.
>
> **Multiplicity: declared hierarchy, no blanket correction.** PRIMARY confirmatory
> family = the two paired WT-vs-matched-NT t1 contrasts (clean, mystery), **Holm within
> family** at α=0.05 (cost measured: mystery-t1 power 0.953→0.903 at n=250; clean t1
> unaffected at 1.0000). Prediction (iii) is a **serially gated secondary**:
> interpreted inferentially only if the primary family is significant, else reported
> descriptively. Funnel decomposition, clean-vs-mystery within arm, the bare-NT
> scaffold delta, per-verdict rates and delegation-conditional accuracy are
> **exploratory/diagnostic**, unadjusted, explicitly non-confirmatory. Exhaustive test
> count is stated in the results memo. One sentence carries the rest: band verdicts are
> pre-registered interpretation rules on interval estimates, not significance tests,
> and carry no multiplicity adjustment.
>
> **Format-clause requirements are part of the band spec**, because the extractor
> biases against this arm (all measured on the real extractor): a plan pasted from
> `classic_planner` extracts to nothing; markdown bolding extracts to nothing;
> shorthand action names extract to nothing; one narrating sentence before the plan
> injects a duplicated action that VAL rejects; t3 is first-mention-wins and
> case-sensitive, so "The plan is VALID." scores incorrect and a hedging preamble flips
> a correct INVALID to VALID. The frozen task-format clause therefore requires the plan
> block (t1) or the exact verdict sentence (t3) as the **entire** answer, in PlanBench's
> own NL action phrasing, with no preamble, no markdown emphasis and no PDDL. It is
> identical in both arms, so the contrast stays unbiased. **Pre-committed:** a NO-RESCUE
> verdict on mystery t1 may not be called a formalization result until the
> extraction-injection audit has run on that cell.

---

## 3. §4 — where the NL→PDDL formalization interface sits in the funnel

**Bottom line.** Take (A), the input-boundary stage, but fix its geometry, reject (B)
on measured grounds rather than taste, and name the *metric* — otherwise §4 commits the
paper to a stage it cannot measure, which is the one failure a protocol paper cannot
afford.

**(B)'s stated rationale is false in our own code.** The argument for folding
formalization into CALL is that argument errors already live there. They do not. CALL
is `TaskResult.tool_selected`, and exactly three codes clear it to False
(`FR_TOOL_NOT_SELECTED`, `FR_WRONG_TOOL`, infra). Measured over 45,600 with-tools
think=off trials: 10,419 trials contain a `missing_required_arg` error, **98.4% of them
pass the CALL bar**, and 31.5% recover to `FR_OK` and vanish from the taxonomy
entirely. Invalid-PDDL-as-argument behaves the same (90.3% pass CALL, 32.0% recover).
Adopting (B) would move the published CALL bar by up to **−53.2pp** (0.8B: 95.4 → 42.2)
and flip the minimum-CALL model from gemma4-26b to Qwen3.5-0.8B, contradicting
`main.tex:685` with its own figure. Inside the ≥9B headline scope the swing is ≤1.3pp,
so the flagship −67pp Gemma claim survives either way.

**And (B) would not even capture the phenomenon.** The observed PlanBench formalization
failure is malformed PDDL → tool error → retry loop → truncate to empty, which lands as
`FR_LOOP_EXHAUSTED`/`FR_TRUNCATED_NO_ANSWER` with `tool_selected=True` (547/584
loop_exhausted rows). Extending CALL leaves the dominant failure outside CALL anyway.

**The decisive case is the third one.** A tool call carrying *valid PDDL that means the
wrong problem* lands at DELIVER under **both** placements, because the upstream grader
VAL-checks the delivered plan against the **gold** domain and instance: a plan that is
optimal for the model's own mis-formalized problem simply fails as a wrong answer. Only
a boundary-stage metric separates that from a genuine delivery failure.

**(A) is exactly measurable, and the enabling checks already pass.** A gold reference
formalization is reconstructible from the NL query alone using only on-disk config maps
— measured 500/500 exact for blocksworld and 500/500 for mystery, zero unparsed
clauses. The comparator is (objects, init, goal) literal-set equality, and the
instrument is `inspect_problem` from the pddl-parser plugin, which returns sorted
canonical literals. Mystery makes the comparison *easier*, not harder (its NL names
objects "object a"…"object l" with an identity map and states the obfuscated predicates
verbatim), which is what turns it into a direct discriminator for prediction (ii).

**One blocking build precondition.** The existing PlanBench tool-call side-log cannot
be joined to instances: `query[:200]` has exactly **1 distinct value across the 500 t1
instances**, results are truncated to 500 chars, and there is no instance id. The
`frontier_runner` path is fine (arguments are unbounded and land in `trials.jsonl`) *if*
the adapter stamps the instance id into the record.

> ANSWER (paste into §4, funnel-placement slot):
>
> **(A), corrected: a new LEADING BAR at the head of the with-tools cascade**, not "a
> stage upstream of NEED". In the ratified Figure-1 spec (`journal_decisions_memo.md`
> §2) NEED is a reference line drawn from the no-tools arm, not a bar, so "upstream of
> NEED" is geometrically undefined. The PlanBench cascade reads: trials →
> **FORMALIZE** → CALL → tool result correct → delivered correct. The three downstream
> stage definitions are untouched, which is the sense in which the funnel is stable
> across instruments; the honest cost is that Figure 1 has four bars for PlanBench and
> three for our own suite, so the boundary bar carries its own one-line question in the
> organizing device: *can the model state the problem in the tool's language?* The
> stage is declared an **instrument property** — absent by construction wherever the
> prompt already contains the PDDL, as in every template of our own suite
> (`pddl_eval/prompts.py`, which embeds `{domain}`/`{problem}`/`{plan}` verbatim and
> makes argument construction an explicit copy task).
>
> **(B) (CALL extension) is rejected on measurement, not preference**, and the reasons
> are recorded so the choice is not relitigated: (1) its premise is false — CALL is
> `tool_selected`, and 98.4% of `missing_required_arg` trials and 90.3% of
> invalid-PDDL-argument trials **pass** the CALL bar today (31.5%/32.0% recover to
> `FR_OK`); (2) adopting it would move the published CALL bar by up to −53.2pp (0.8B
> 95.4→42.2) and flip the minimum-CALL model, contradicting `main.tex:685`; (3) it
> would still not capture the dominant formalization failure, which is
> retry-to-truncation (`loop_exhausted` with `tool_selected=True`, 547/584); (4) it
> does not fix the misattribution it is offered to fix, since valid-but-wrong PDDL
> surfaces at DELIVER under both placements (the grader VAL-checks the delivered plan
> against gold).
>
> **The metric, pre-registered with the stage.** `formalization_match` = the
> model-authored problem's (object set, init literal set, goal literal set) equals
> gold's, up to the config-declared object bijection; computed post hoc from the logged
> tool-call arguments with `inspect_problem` (pddl-parser plugin, used by us at
> analysis time — it stays **out** of the model's roster, so §10-B's 7-tool roster is
> unaffected), against a gold reference reconstructed from the NL query (verified
> 500/500 blocksworld and 500/500 mystery, 0 unparsed clauses). Reported per cell with
> a Wilson 95% CI on the same denominator as accuracy, decomposed as **parseable →
> solvable → equivalent-to-gold** so the numbers sit against Planetarium's published
> base rates (GPT-4o 96.1 / 94.4 / 24.8) rather than a decomposition of our own
> invention. For the model-authored **domain**, equivalence is decided by brute-forcing
> the 24 arity-constrained candidate bijections (6 predicate x 4 action) against
> `inspect_domain`, with a behavioural fallback (replay the gold plan through the
> model's domain+problem). Two companion diagnostics are pre-registered with it: the
> **delegation rate** (share of trials calling `classic_planner`, i.e. search delegated
> to Fast Downward rather than retained by the model) and accuracy **conditional on
> delegation** — without which a persistence result is indistinguishable from Göbel et
> al.'s published +3.0pp Haiku-4.5-plus-MCP-simulator result and a rescue result is
> indistinguishable from Huang & Zhang's published formalizer numbers.
>
> **Build precondition (blocking, promoted into §2).** Every logged tool call must
> carry its instance id. The existing PlanBench side-log cannot be joined post hoc
> (`query[:200]` has 1 distinct value across all 500 t1 instances, tool results are
> truncated to 500 chars, no instance id), so the adapter must stamp the instance id
> into the per-call record on the `frontier_runner` path, where arguments are already
> unbounded and land in `trials.jsonl`. Shipping without this makes §4 unfalsifiable.
>
> **Open sub-decision recorded here:** the on-disk v2 scaffold has the model author
> domain **and** problem **and** plan, and no ruling exists. Recommended: keep
> model-authored (the arm's claim is that the model operates the prescribed remedy
> end-to-end), which makes the domain check the 24-bijection test above. Injecting the
> gold domain would reduce the boundary metric to problem-only set equality but changes
> the condition into a labelled "given PDDL" variant. See §10-O.

---

## 4. Cross-cutting items that must be settled before ratification

These are not in any existing slot, and several would void the prereg after the fact.
Full wording is in the prereg's new §10; the summary and reasoning:

- **A. Matched-NT scaffold parity (the objection most likely to sink the arm).** §2
  lists tool-use guidance as a scaffold component and then calls the control "identical
  scaffold, empty tool list as the ONLY ablation". Keeping that clause is
  self-contradictory, not merely redundant: `WITH_TOOLS_SYSTEM` asserts "Your ONLY way
  to get information or solve problems is by calling the provided tools", and the t1
  format clause names `classic_planner`. With an empty tool list the control asserts a
  false premise and forbids the only action available, so it would measure
  instruction-conflict compliance, and any depression it causes inflates the WT−NT
  delta in the hypothesis's favour. The accepted ruling names only the NL→PDDL step and
  the task-format clause as shared, which licenses the coherent control; the repo
  precedent is stronger still (`WITHOUT_TOOLS_SYSTEM_BY_TASK` is a length-matched
  mirror, test-enforced). **Recommendation:** coherent control (mirror the policy
  sentence, strike the tool name from the shared format clause), name the contrast a
  package contrast, and add a **third arm on mystery t1 only** (pure availability:
  dangling directive, empty tools) at ≈$2 as an outcome-neutral control that the
  directive alone moves nothing — the same logic already ratified in the H4 prereg.
- **B. Roster.** 7 tools (pddl-solver + pddl-validator). Strike pddl-parser from the
  model's roster; it is only an analysis-time instrument (§3 above).
- **C. Caching leaves the "identical in every respect" clause.** The WT cacheable
  prefix is ~4.1-4.4K tokens against Haiku 4.5's 4,096 minimum (a ~5% margin), the
  matched-NT prefix is ~150 tokens and cannot cache at all, and `frontier_runner`
  passes a top-level `cache_control`, which places the breakpoint after the per-instance
  user turn so cross-trial reuse of the tools+system prefix is structurally absent.
  Caching is a billing-layer property that cannot affect sampled outputs; log per-trial
  cache tokens and record the runner's ACTIVE / NET-LOSS / INACTIVE verdict per cell.
- **D. Calibration gate: disjoint and discarded.** Reusing the calibration instances is
  defensible only under blinded internal-pilot conditions, and two of the gate's own
  observables (extraction rate, loop_exhausted) are outcome-adjacent, while the
  5-instance mystery spot-check is a direct peek at prediction (i). Making the whole
  gate disjoint from S and discarding it costs ≈$1.5 and removes the argument. Widen it
  to 20 clean + 20 mystery (5 points cannot bound a heavy-tailed cost distribution),
  and make the **headline gate number p90 output tokens per trial**: output is 50-60% of
  WT per-trial cost and a 3.3x lever across its plausible range, while turns are only a
  2.4x lever across their entire legal range.
- **E. Spend guard.** `frontier_runner` has no dollar cap; its only stop is an
  Anthropic "credit balance too low" exception, i.e. it halts when the money is already
  gone. Add `--max-spend` with a running accumulator that saves and exits (the resume
  path makes a mid-run stop safe), global cap $50, per-cell cap 2x the calibrated
  central projection. Also: **the ~$70.6 is a bookkeeping figure**
  (`frontier_rerun_handoff.md:74`), not a console balance — verify it before spending.
- **F. Exclusion / intercurrent-event table**, identical in both arms, with a censoring
  cap that converts an over-censored cell into reported bounds rather than a point
  estimate. Load-bearing because this runner has a measured intermittent failure that
  disappeared on re-run at temperature 0, i.e. "run it again and keep the better
  number" is physically possible here; hence also a single-run/no-cherry-pick rule.
- **G. Operational aborts:** never `--run_till_completion` (an empty answer from a
  loop-exhausted trial is retried forever at temp 0 — an unbounded paid loop); never
  `--ignore_existing` against the 06-22 engine name (it would overwrite the graded NT
  corpus); fresh engine names plus an allowlist entry (verified: the allowlist is
  `{ollama, vllm, vllm-base, vllm-tools, anthropic}` and rejects anything else);
  `PDDL_COPILOT_RENDER_FROM_TOOLS=0` for WT t3; `build_table` engine entries; a venv
  that can actually run WT generation (none can today) with the `anthropic` version
  pinned deliberately; `MAX_TOOL_LOOPS=10` recorded in run meta; and no latency claims
  (the duration fields are hard-coded 0).
- **H. §5 wording:** "unmodified" → "the same patched evaluator build that graded the NT
  layer".
- **I. Freeze mechanics:** commit SHA + UTC timestamp + git tag `prereg-planbench-wt-v1`
  on ratification; analysis script frozen and SHA-pinned, exercised against the
  published bare-NT rows before the WT run; deviations reported in a table.
- **J. §1/§7 claim wording:** the bare claim is already published (Huang & Zhang ACL
  2025 verified; La Malfa arXiv:2512.09629, LLMFP, CoPE pending `/verify-claims`). The
  surviving novelty is the matched-scaffold single ablation with VAL grading, Wilson
  CIs, paired tests, the formalization-boundary metric, the delegation mediator, and
  measured dollars — so §1 should say "replication with an ablation the field has not
  run" rather than implying a new phenomenon.

---

## 5. Two things this memo found that are outside the prereg

**(1) A red flag on the NT layer's t3 row, which is Act 4 headline material.** The
committed GPT-4 t3 corpus is **not the corpus we ran**: 0/500 identical queries,
identical gold verdict text on only 119/500, and the verdict mix is inverted (GPT-4
155 VALID / 345 INVALID = 31.0% VALID, ours 324/176 = 64.8% VALID; t3's generator draws
its examples and mutation type with unseeded `random`). Because the two models have
opposite verdict biases, post-stratifying to a common mix moves Haiku bw t3 78.2 → 83.1
and mystery 45.4 → 64.1, and GPT-4 the other way (94.6 → 90.3, 73.6 → 83.7): **the
mystery t3 gap collapses from 28.2pp to 9.5pp.** Finding 2 of
`planbench_frontier_haiku_nt.md` ("verification does not follow; Haiku sits clearly
below GPT-4") is therefore mix-confounded as stated and needs re-reporting with
per-verdict rates and a stated mix. The t1 headline is unaffected and clean (same 500
ids, same one-shot example 500/500, 499/500 byte-identical queries after removing our
one extra domain-rule sentence). I have not edited the NT doc — flagging for a separate
work item.

**(2) Two free strengtheners for the same layer, pending citation verification.**
LLMFP's Direct GPT-4o rows are 41.5% blocksworld / 0.8% mystery at n=602, within 0.5pp
of our Haiku 41.0 / 0.8 at n=500 — an independent external replication of the NT layer
on a different model. And a published GPT-4 mystery-t1 comparator does exist (26/600 =
4.3% [3.0,6.3], Valmeekam et al. arXiv:2305.15771 Table 1) where the NT doc records
"not in canonical"; it is CI-disjoint **above** Haiku's 0.8%, so Act 4 can state that
Haiku is significantly *worse* than GPT-4 under obfuscation. That sharpens the collapse
story, and it is also a caution for this arm: the model we are about to hand tools to
is, unaided, below GPT-4 on the exact target cell.

---

## 6. Open decisions that are genuinely Omer's

> ANSWER — **t2**: the stated exclusion rationale is false (`classic_planner(strategy=
> "astar_lmcut")` = `astar(lmcut())`, optimal — `solver_server.py:247,411`), and t2 is
> where the field's strongest published mystery numbers live (LLMFP optimal rate 77.7
> GPT-4o / 98.0 Claude 3.5 Sonnet, n=602). Recommendation: **keep t2 out** of this arm
> (protect the 2026-08-15 date and the arm's simplicity), correct the rationale to a
> scope decision, and record a mystery-t2 WT+matched-NT pair (≈$12 at n=250) as a
> gate-contingent option. Accept / add t2 / defer:

> ANSWER — **third control arm** (pure-availability NT on mystery t1, ≈$2): recommended
> as the cheapest answer to the strongest methodological objection, and first item in
> the shrink order. Accept / drop:

> ANSWER — **domain authorship** (§10-O): model authors the domain (recommended) vs
> gold domain injected as a labelled "given PDDL" variant:

> ANSWER — **the NT t3 mix confound** (§5 item 1): open as a separate work item now, or
> defer until the WT results memo:
