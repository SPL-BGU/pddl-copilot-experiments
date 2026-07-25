# Pre-registration — PlanBench frontier with-tools arm (Haiku 4.5)

**Status:** DRAFT awaiting Omer's ratification. The three original ANSWER slots now carry
**recommendations** (2026-07-25, from a 7-agent evidence workflow; reasoning, provenance
and rejected alternatives in `development/planbench/planbench_wt_prereg_decisions.md`),
plus a new §9 of ratification-blocking amendments and three narrower ANSWER slots.
Review the recommendations, annotate any rejections, then sign §10 RATIFY.
**No build or spend before ratification.** Corrections applied inline are marked
`[corrected 07-25: …]`; five premises in the 07-24 draft were measurably false and two
of them would have produced wrong numbers silently (denominator, t3 grading surface).
**Date:** 2026-07-24, amended 2026-07-25. **Binding source:**
`development/journal_decisions_memo.md` §4
(accepted D-J3, 2026-07-24); scoped to UNRUN cells only — the 06-22 bare-NT rows
(graded, `development/planbench/planbench_frontier_haiku_nt.md`) are untouched and
become the published-apparatus replication layer.

## 1. Claims and headline assignment (fixed)

- **Act 4 headline = the already-graded NT layer** (honest-denominator regrade, t2
  silent-0.0 artifact fix, t7 chat-format grading critique, Haiku t1 41.0 beats
  GPT-4 31.4 CI-disjoint, Mystery collapse replication). The WT arm can neither
  strengthen nor weaken this claim.
- **WT carries the explicitly-labeled SECONDARY claim:** "the funnel replicates when
  the model operates the prescribed remedy on the field's instrument" — external
  validity for C2, within-apparatus only. Single-tier (Haiku) is owned as a
  limitation; Sonnet extension is out of budget.
- WT-vs-GPT-4 comparison is structurally excluded (presentation rules, §7).

## 2. Design

**Backend.** Adapter over `tools/frontier_runner.py` (SDK Tool Runner, D1=B; its
docstring pre-plans this reuse). Model pinned `claude-haiku-4-5`; tool execution on
the harness `MCPPlanner` with **the harness roster `resolve_plugin_dirs` exposes:
pddl-solver + pddl-validator, 7 tools** (`run_experiment.py:122`
`REQUIRED_PLUGINS`); `max_iterations=MAX_TOOL_LOOPS` (=10, recorded in run meta);
per-trial token/turn/tool-call logging **including full tool-call arguments stamped
with the instance id** (§4 build precondition); `anthropic` package version pinned
and recorded in run meta. Live API (multi-turn loop cannot batch).
[corrected 07-25: the earlier text said "full marketplace roster (pddl-parser,
pddl-solver, pddl-validator)"; pddl-parser is NOT in the harness roster and is used
only as an analysis-time instrument (§4). Prompt caching moved to §9-C: it cannot be
part of an "identical in every respect" clause, because the WT prefix is on a ~5%
margin over Haiku's 4096-token minimum and the matched-NT prefix cannot cache at all.]

**Scaffold.** System scaffold containing (a) an NL→PDDL formalization step
instruction, (b) a task-format clause (answer in the upstream extractor's expected
format, per the measured extractor requirements in §3), (c) a tool-use policy
sentence. User message = the upstream PlanBench prompt, unchanged (same prompts the
06-22 NT rows answered; verified byte-identical to `prompts/*.json` for 500/500
instances in all four graded cells). **Scaffold text is frozen at the calibration
sign-off gate (§8); any post-freeze change voids the prereg for affected cells and
restarts them.**

**Matched-scaffold no-tools control (the primary comparator).** Same SDK loop, same
instance set, same grading, with components (a) and (b) **byte-identical** and the
tool-use policy sentence (c) replaced by its no-tools mirror; tool availability
(the tool list together with the directive) is the only ablation. See §9-A for why
the verbatim-with-dangling-directive variant is not the primary comparator and is
instead run as a labelled sensitivity arm on mystery t1. The 06-22 bare-NT rows (no
system prompt) are NOT the control; they are a replication layer, and the
matched-NT-vs-bare-NT delta is reported once as a scaffold effect in the validity
thread, never as a treatment contrast (paired on S — the bare-NT rows cover the same
instances).

**Cells, in priority order** (t2 excluded **as a scope decision**, not a capability
one — [corrected 07-25: `classic_planner(strategy="astar_lmcut")` = `astar(lmcut())`
is optimal search and ships today (`solver_server.py:247,411`), so the earlier
"optimal_plan tool unbuilt" rationale is false; a gate-contingent mystery-t2 option is
recorded in the decisions memo §6]; t7 excluded from WT — grading critique only,
Act 5; logistics out of scope):

| pri | cell pair (WT + matched-NT) | role |
|---|---|---|
| 1 | blocksworld t1 | near-ceiling confirmation |
| 2 | mystery_blocksworld t1 | the failure→success cell (NT 0.8%) |
| — | **target = {clean, mystery} × {matched-NT, WT} 2×2 on t1** | primary contrasts |
| 3 | blocksworld t3 | verification-gap probe (prediction iii) |

**Budget valve = subsampling, never whole-cell deletion within the t1 2×2.**
[corrected 07-25: the earlier valve trimmed n uniformly and named the t3 pair as the
only cuttable one, which is inverted — t3 is the ONLY power-scarce cell (80%-power
McNemar MDE +9.0pp at n=250 vs +10.4pp at n=200 under 10% leakage) and clean t1 has
power 1.0000 to spare at every pre-registered WT value. The cost-only shrink order is
now: (1) drop the §9-A sensitivity arm; (2) matched-NT from the full pool back to |S|;
(3) clean-t1 WT n 250→150; (4) **t3 last**, 250→200. If step (4) still misses budget,
kill criterion (a) fires for the whole arm (§8).]

**Instance subsample.** See the ANSWER block below, which supersedes the earlier
"seed 20260724 + gold-plan-length quartile over the 500-instance pool" wording:
measured on disk, the t1 pool is ids 2..501 and the t3 pool is ids 1..500
(intersection 499), gold plan lengths take only 8 even values so quartile cuts land on
the modal values (strata 200/139/113/48), and a seed alone does not pin S.

> ANSWER (RECOMMENDED 2026-07-25, decisions memo §1 — pending RATIFY):
>
> **n and pool.** S is drawn from the **499-id t1∩t3 intersection (instance_ids
> 2..500)**, not the 500-instance t1 pool: t1/t2 ids are 2..501 and t3 ids are 1..500
> (measured), so a draw containing id 501 would silently reduce the t3 cells to n=249.
> **|S| = 250** for the with-tools cells. The three matched-no-tools cells run the
> **full 499-id pool** (+≈$5.6 central): the confirmatory paired tests are computed on
> S only, and the extra 249 no-tools rows are a labelled secondary precision estimate
> for the NT cell and for the bare-NT scaffold delta, never entering a paired test.
>
> **Stratification.** Proportional allocation with largest-remainder over the crossed
> strata **(gold-plan-length value, collapsed: {2,4} / {6} / {8} / {10} / {12,14,16})
> × (t3 gold verdict: VALID / INVALID)**. "Quartile" is struck as not implementable:
> lengths are {2:30, 4:56, 6:114, 8:139, 10:113, 12:46, 14:1, 16:1} and the quartile
> cuts 6/8/10 coincide with the three modal values. Verdict enters because t3 accuracy
> is strongly verdict-conditional in the graded NT layer (blocksworld VALID 73.1
> [68.1,77.7] vs INVALID 87.5 [81.8,91.6]; mystery 25.9 vs 81.2), so the t3 marginal is
> a mixture whose value tracks the VALID share; the joint scheme ties or dominates every
> alternative in Monte Carlo at both n (bw t3 sampling SD 1.83 SRS → 1.76).
>
> **Seed and materialization.** Seed **20260724**, `random.Random(20260724)`, strata
> iterated in sorted (length-bin, verdict) order, proportional + largest-remainder.
> The seed alone does not pin S (a reference draw shifted NT-recomputed-on-S by up to
> 5pp: mystery t3 50.4 vs 45.4), so the drawing script
> `planbench/draw_wt_subsample.py` **and the realized id list**
> `planbench/wt_subsample_S.json` (250 ids + stratum labels + sha256) are committed
> **before the calibration gate**; the pre-registered S is that file, not the procedure.
>
> **Pre-committed escalation (cost-only, increase-only).** If the calibration gate's
> projection at **p90** measured $/WT-trial for the full-pool design is **≤ $50**
> (≈71% of the remainder, holding a ~20% reserve), the with-tools cells run the full
> 499-id pool instead of S. Decided before any confirmatory trial, reading **only**
> $/trial, turns/trial, cache-read fraction and wall-clock — never graded accuracy and
> never the WT-vs-NT contrast. Escalation raises the sample-size justification from
> resource-constrained to whole-population, lets every WT row share a denominator with
> the published n=500 bare-NT layer, and cuts the §3 INCONCLUSIVE band mass from 45/251
> outcomes to 63/500.
>
> **Correspondence check: PASSED, recorded now** (the contingent fallback is struck as
> dead code, and clean-vs-mystery is committed as paired). Mystery is a pure symbol
> rename with an identity object mapping, verified at four levels: 501/501 instance
> files isomorphic (identical `:objects`, predicate-mapped `:init`/`:goal` literal
> sets), 500/500 t1 gold plans action-for-action isomorphic with identical lengths,
> 500/500 t3 candidate plans isomorphic, 500/500 t3 gold verdicts identical. Never
> enumerate the pool by directory glob: `instances/blocksworld/mystery/generated_basic`
> holds a stray mystery-only `instance-0.pddl` that is not a rename of any clean
> instance (unused at `start=1`).
>
> **Denominator (blocking).** TOTAL = |S| (or 499 if escalated). `build_table.acc()`
> divides by `len(instances)` = 500 regardless of the subsample: replaying the real
> graded bw-t1 file with 250 instances stripped returns 22.2% where the truth is 44.4%.
> Filter the response JSON to S before grading, or pass S to the table builder. Do
> **not** pass `--specific_instances` to `response_evaluation.py` — its filter mutates a
> module-level list and silently grades everything after the last matched id (unpatched
> at :92-96, :155-159, :254-258); the evaluator already skips empty-response instances,
> so a subsampled run yields denominator = |S| naturally.

## 3. Predictions (pre-registered, with outcome bands)

Linkage rule: **any prediction whose test cell is trimmed is struck** from the
prereg — reported as struck, not as unsupported.

- **(i) Tools convert failure to success on mystery t1.** Four-outcome evidential
  partition in the ANSWER below. [corrected 07-25: "CI midpoint" is struck — the Wilson
  midpoint is not the point estimate, and the literal rule left 5 integer outcomes
  unclassifiable at each n. The clean-t1 "≥ 90%" band is struck as
  unattainable-by-instrument and demoted to an outcome-neutral apparatus criterion.]
- **(ii) Mystery mechanism, two branches with per-branch signatures and a joint
  falsifier.** Both directions remain publishable, but the branches are now
  distinguished by a measured discriminator (the §4 formalization-boundary metric plus
  the delegation rate), and a pattern is named that refutes both. [corrected 07-25:
  "both directions publishable, neither is a failed experiment" is unfalsifiable as a
  stand-alone prediction.]
- **(iii) Tool-available t3 closes Haiku's verification gap vs its own matched-NT:**
  paired improvement (McNemar exact) with the band, MDE and conjunctive-outcome ruling
  in the ANSWER below. **Struck if t3 is trimmed.**

> ANSWER (RECOMMENDED 2026-07-25, decisions memo §2 — pending RATIFY):
>
> **Estimand first (ICH E9(R1) attributes).** Treatment = tool availability (the 7-tool
> harness roster together with the tool-use directive) vs its no-tools mirror;
> population = S; endpoint = the **delivered** final message graded by the patched
> upstream evaluator, t1 `llm_correct` and t3 **`llm_correct_binary`** (named
> explicitly: the three t3 fields differ by up to 19.4pp on identical responses — binary
> 78.2 / w_type 68.2 / w_expl 58.8 — and both the published NT layer and the GPT-4 94.6
> comparator are on binary; w_type and w_expl are secondary); summary = per-cell
> proportion with Wilson 95% CI plus the paired Δ on S; intercurrent events per the §9-F
> exclusion table (treatment-policy: counted as failures, denominator = |S|).
>
> **(i) Mystery t1 WT bands** (exhaustive and disjoint by construction, verified by
> enumerating every integer outcome; mirrors the PASS/FAIL/UNDERPOWERED shape already
> ratified in `ntster_h4_prereg.md`):
>
> | verdict | rule | counts at n=250 | counts at n=499 |
> |---|---|---|---|
> | NO-RESCUE | Wilson upper < 5% | x ≤ 5 (≤ 2.00%) | x ≤ 15 (≤ 3.01%) |
> | PARTIAL | CI entirely within [5,50) | x ∈ [20,109] | x ∈ [35,227] |
> | RESCUE | Wilson lower ≥ 50% | x ≥ 141 (≥ 56.40%) | x ≥ 272 (≥ 54.51%) |
> | INCONCLUSIVE | CI spans 5% or 50% | x ∈ 6..19 or 110..140 | x ∈ 16..34 or 228..271 |
>
> **Anchors:** 5% = ~2.5× the measured bare-NT mystery Wilson upper bound (2.0% at
> n=500) and just above the smallest value distinguishable from it at n=250 (Wilson
> half-width 2.8pp at p=0.05); 50% = solved more often than not, which in evidential
> form demands p̂ ≥ 56.4% (n=250) / 54.5% (n=499). The declared INCONCLUSIVE region is
> the falsifiability feature: 45/251 outcomes at n=250 and 63/500 at n=499 land in it.
> Every verdict is additionally reported against the two published bands
> (verifier-in-the-loop ~3.8-14%, formalize-then-delegate ~63-100%; pending
> `/verify-claims`) with pool size and grader on the same line, since "Mystery
> Blocksworld" denotes at least five different pools in the literature.
>
> **Clean t1 WT = OUTCOME-NEUTRAL apparatus criterion, not a prediction:**
> (a) extraction rate ≥ 90% (measured NT clean t1 = 94.4%, 472/500) and (b) delivered
> p̂ ≥ 85% with Wilson lower ≥ 80. The old "≥ 90%" is struck: Wilson lower ≥ 90 needs
> p̂ ≥ 94.0% at n=250 against a 94.4% extraction ceiling, i.e. P(correct | extracted)
> ≥ 0.953. Report P(correct | extracted) alongside the raw rate in every t1 cell.
> Failing (a) is an apparatus-fix-and-restart event, never a scope decision; failing (b)
> with (a) passing is recorded as a scaffold/capability ceiling that bounds the mystery
> cell's interpretation.
>
> **(ii) Two-branch mechanism test.** Stated directional prior: RESCUE, p≈0.6, because
> mystery is a verified pure symbol rename with identity object mapping (501/501) and
> Fast Downward is name-blind, and Huang & Zhang (ACL 2025) find formalizers robust to
> lexical perturbation. Counterweight, pre-registered: Göbel et al. (arXiv:2603.06064)
> obtained only +3.0pp (63.7 → 66.7) with **this same model** and PDDL tools over MCP on
> clean Blocksworld, because the tools exposed a step-wise simulator and the model kept
> the search — architecture, not tier, decides.
> - **RESCUE branch** additionally requires: mystery `formalization_match` (§4) not
>   CI-disjointly below clean; delegation rate (share of trials calling
>   `classic_planner`) ≥ 80%; and paired |clean_WT − mystery_WT| within **±10pp**.
> - **PERSISTENCE branch** additionally requires the loss charged at the named
>   formalization boundary: mystery `formalization_match` CI-disjointly below clean,
>   while the clean cell formalizes successfully.
> - **JOINT FALSIFIER:** mystery WT statistically indistinguishable from mystery
>   matched-NT with the same per-stage failure profile as clean WT → the arm's mechanism
>   claim is reported **unsupported**, not narrated either way.
> - **±10pp is the margin n supports** (paired TOST power 0.96 at n=250 for the
>   plausible discordance ψ=0.18, certifying ±10pp up to ψ=0.29). **±5pp is not
>   pre-registrable** (power 0.18 at n=250; ~617 pairs needed), and the 5.26pp post-hoc
>   CI half-width must not be quoted as licence for it.
>
> **(iii) t3, with its power stated instead of assumed.** Confirmatory: exact McNemar,
> paired WT vs matched-NT on S. Band: WT t3 p̂ ≥ 90 with Wilson lower ≥ 85, anchored on
> our own measured Haiku frontier with-tools validation delivered rates (96-99) minus
> headroom for the added NL→PDDL step, against the NT anchor 78.2 [74.4,81.6] and
> GPT-4's 94.6. **Pre-registered MDE:** power is 0.94 at n=250 if WT t3 reaches 90% and
> the tool breaks ≤10% of NT successes, but only 0.58 if WT t3 lands at 85%; the
> 80%-power MDE is +9.0pp (n=250) / +10.4pp (n=200) under 10% leakage, so a true +7pp
> improvement will likely be missed — pre-declared, not reinterpreted afterwards.
> **Conjunctive ruling, fixed now:** significant + band met = supported; significant +
> band missed = "gap narrowed, not closed" (no rescue language); not significant + band
> met = level reached without a demonstrable paired lift, reported descriptively;
> neither = not supported. **Mandatory alongside:** the VALID/INVALID confusion matrix,
> FPR/FNR, and the constant-VALID degenerate baseline (324/499 = 64.9% [60.5,68.9]; 64.8%
> [58.7,70.5] at n=250) — Haiku NT 78.2 is only +13.4pp above always answering VALID, and
> a published Mystery-BW verification "accuracy" of 79.6% has been shown to be an
> always-invalid artifact (FNR 97.1%).
>
> **Multiplicity: declared hierarchy, no blanket correction.** PRIMARY confirmatory
> family = the two paired WT-vs-matched-NT t1 contrasts (clean, mystery), **Holm within
> family** at α=0.05 (measured cost: mystery-t1 power 0.953 → 0.903 at n=250; clean t1
> unaffected at 1.0000). Prediction (iii) is a **serially gated secondary**, interpreted
> inferentially only if the primary family is significant, else descriptively. Funnel
> decomposition, clean-vs-mystery within arm, the bare-NT scaffold delta, per-verdict
> rates and delegation-conditional accuracy are exploratory/diagnostic, unadjusted and
> explicitly non-confirmatory; the exhaustive test count is stated in the results memo.
> Band verdicts are pre-registered interpretation rules on interval estimates, not
> significance tests, and carry no multiplicity adjustment.
>
> **Extractor requirements are part of this spec, because the instrument biases against
> the WT arm** (all measured against the real extractor): a plan pasted from
> `classic_planner` extracts to nothing (`(unstack a b)` tokenizes as `(unstack`);
> markdown-bolded actions extract to nothing; shorthand action names extract to nothing;
> **one narrating sentence before the plan injects a duplicated action** that VAL then
> rejects; and t3 is first-mention-wins and case-sensitive, so "The plan is VALID."
> grades incorrect and the preamble "Let me check whether the plan is valid…" flips a
> correct INVALID verdict to VALID. The frozen task-format clause therefore requires the
> plan block (t1) or the exact verdict sentence (t3) as the **entire** answer, in
> PlanBench's own NL action phrasing, with no preamble, no markdown emphasis and no
> PDDL — identical in both arms, so the contrast stays unbiased. **Pre-committed:** a
> NO-RESCUE verdict on mystery t1 may not be called a formalization result until the
> extraction-injection audit has run on that cell.

## 4. Funnel-placement statement (named BEFORE data)

The NL→PDDL formalization interface must have a fixed home in the funnel taxonomy
before any WT data is graded. **Proposal: an input-boundary stage upstream of
NEED** — NL-specified problems enter through a formalization boundary before
tool-need recognition; formalization losses are charged to that boundary stage, not
to CALL. Alternative (memo-sanctioned): an explicit CALL extension
(formalization-as-argument-construction).

> ANSWER (RECOMMENDED 2026-07-25, decisions memo §3 — pending RATIFY):
>
> **(A), corrected: a new LEADING BAR at the head of the with-tools cascade**, not "a
> stage upstream of NEED". In the ratified Figure-1 spec (`journal_decisions_memo.md`
> §2) NEED is a reference line drawn from the no-tools arm, not a bar, so "upstream of
> NEED" is geometrically undefined. The PlanBench cascade reads: trials → **FORMALIZE**
> → CALL → tool result correct → delivered correct. The three downstream stage
> definitions are untouched, which is the sense in which the funnel is stable across
> instruments; the honest cost is that Figure 1 has four bars for PlanBench and three
> for our own suite, so the boundary bar carries its own one-line question in the
> organizing device: *can the model state the problem in the tool's language?* The stage
> is declared an **instrument property**, absent by construction wherever the prompt
> already contains the PDDL — as in every template of our own suite
> (`pddl_eval/prompts.py` embeds `{domain}`/`{problem}`/`{plan}` verbatim and the
> with-tools overrides make argument construction an explicit copy task; measured
> frontier WT domain arguments are verbatim retransmissions, median 1,804 chars).
>
> **(B) (CALL extension) is rejected on measurement, not preference**, recorded so the
> choice is not relitigated: (1) its premise is false — CALL is `tool_selected`, and
> 98.4% of `missing_required_arg` trials and 90.3% of invalid-PDDL-argument trials
> **pass** the CALL bar today, with 31.5%/32.0% recovering to `FR_OK`; (2) adopting it
> would move the published CALL bar by up to −53.2pp (0.8B 95.4 → 42.2) and flip the
> minimum-CALL model from gemma4-26b to Qwen3.5-0.8B, contradicting `main.tex:685` with
> its own figure (the ≥9B headline swing is ≤1.3pp, so the −67pp Gemma claim survives
> either way); (3) it would still not capture the dominant formalization failure, which
> is retry-to-truncation (`loop_exhausted` with `tool_selected=True`, 547/584); (4) it
> does not fix the misattribution it is offered to fix, since valid-but-wrong PDDL
> surfaces at DELIVER under both placements (the grader VAL-checks the delivered plan
> against gold).
>
> **The metric is pre-registered with the stage.** `formalization_match` = the
> model-authored problem's (object set, init literal set, goal literal set) equals
> gold's, up to the config-declared object bijection; computed post hoc from the logged
> tool-call arguments with `inspect_problem` (pddl-parser plugin, used by us at analysis
> time and deliberately kept OUT of the model's roster), against a gold reference
> reconstructed from the NL query alone (verified 500/500 blocksworld and 500/500
> mystery, 0 unparsed clauses). Reported per cell with a Wilson 95% CI on the same
> denominator as accuracy, decomposed as **parseable → solvable → equivalent-to-gold**
> so the numbers sit against published base rates (Planetarium GPT-4o 96.1 / 94.4 /
> 24.8) rather than a decomposition of our own invention. For the model-authored
> **domain**, equivalence is decided by brute-forcing the 24 arity-constrained candidate
> bijections (6 predicate × 4 action) against `inspect_domain`, with a behavioural
> fallback (replay the gold plan through the model's domain+problem). Two companion
> diagnostics ship with it: the **delegation rate** (share of trials calling
> `classic_planner`, i.e. search delegated to Fast Downward rather than retained) and
> accuracy **conditional on delegation** — without which a persistence result is
> indistinguishable from Göbel et al.'s published +3.0pp and a rescue result is
> indistinguishable from Huang & Zhang's published formalizer numbers.
>
> **Build precondition (blocking).** Every logged tool call must carry its instance id.
> The existing PlanBench side-log cannot be joined post hoc (`query[:200]` has exactly 1
> distinct value across all 500 t1 instances, tool results truncated to 500 chars, no
> instance id), so the adapter stamps the instance id into the per-call record on the
> `frontier_runner` path, where arguments are unbounded and already land in
> `trials.jsonl`. Shipping without this makes this section unfalsifiable.
>
> **Open sub-decision** (§9-O): the on-disk v2 scaffold has the model author domain
> **and** problem **and** plan, and no ruling exists. Recommended: keep model-authored,
> which makes the domain check the 24-bijection test above; injecting the gold domain
> would reduce the boundary metric to problem-only set equality but turns the cell into
> a labelled "given PDDL" variant.

## 5. Grading

Local, zero cluster: **the same patched upstream evaluator build that graded the NT
layer** (`planbench/apply_patches.py` patch 5 A/B/C, commit-pinned) — [corrected 07-25:
"unmodified" is checkable and false; three robustness patches are applied in place, and
naming the shared build is what preserves comparability]; VAL = the Rosetta x86_64 Mac
build; FAST_DOWNWARD pinned to the pddl-solver plugin venv even where unused (no
silent-missing-dependency path — the t2 silent-0.0 artifact is the cautionary
precedent); grading runs with cwd = `external/LLMs-Planning/plan-bench` and
`PDDL_COPILOT_RENDER_FROM_TOOLS=0` (its default is `1`, which renders the t3 verdict
from the last tool result and never reads the model's final message — i.e. the cell
would silently measure tool-verified, contradicting the delivered-primary ruling).
Per newly graded cell: (a) ≥ 4 hand-verified instances, 2 expected-correct + 2
expected-incorrect; (b) extraction-rate distribution check against the measured NT
baselines (clean t1 94.4%, mystery t1 89.6%); (c) **any cell grading exactly 0.0% or
100.0% triggers a mandatory artifact audit before the number is used anywhere**;
(d) **denominator assertion**: the graded denominator equals |S| (or 499 if escalated) —
`build_table.acc()` divides by 500 regardless of the subsample and this audit is the
only thing that catches it, since a halved-denominator cell does not land on 0.0/100.0;
(e) a **gold-PDDL positive control**: the hand-verified instances' gold domain+problem
are run through the same `MCPPlanner`/runner and must return a valid plan, so a
persistence result cannot be a broken-solver artifact.

## 6. Analysis

Per-cell accuracy with Wilson 95% CI, correct/TOTAL denominator where TOTAL = |S| (no
dropped instances). **Primary confirmatory family** (§3): the two paired
WT-vs-matched-NT t1 contrasts, McNemar exact + paired Δ with CI, Holm within family;
prediction (iii) t3 serially gated behind it. Clean vs mystery within arm is **paired**
(the correspondence check is recorded PASSED in §2, not contingent) and is
exploratory/diagnostic, with the ±10pp equivalence test as pre-specified in §3(ii).
Funnel decomposition per the §4 placement, including `formalization_match` (parseable →
solvable → equivalent-to-gold) and the delegation rate with delegation-conditional
accuracy. t3 tables always carry per-verdict rates, the confusion matrix and the
constant-VALID baseline. Bare-NT replication delta reported in the validity thread only,
paired on S. Reported alongside every cell: turns/trial, output tokens/trial and $/cell
(latency is not measurable on this path — the duration fields are hard-coded 0 — so any
efficiency claim uses turns and output tokens only).

## 7. Presentation rules (prereg rules, not prose intentions)

- WT cells never share a table or figure with GPT-4 rows. **Table A** = NT vs
  committed GPT-4 (existing caveats). **Figure B** = within-Haiku paired
  matched-NT→WT deltas, no GPT-4 column.
- t7 appears only in Act 5's grading critique.
- Headline assignment of §1 is a presentation rule: WT numbers are introduced as
  secondary, within-apparatus.

## 8. Budget, calibration gate, kill criteria

**Ceiling:** the ~$70.6 API remainder (D4 parks the steering reframe and the
contamination probe precisely to fund this). **The figure is bookkeeping**
(`frontier_rerun_handoff.md:74`), not a console balance — verify it in the Anthropic
console before authorizing spend. Projected cost of the recommended shape at central
estimates: **≈$38 (54% of the ceiling)** — WT 750 trials ≈$23.4, matched-NT 1497
trials ≈$11.2, sensitivity arm ≈$2.1, calibration ≈$1.5; the pessimistic band breaches
(≈$90), which is what the gate, the spend guard (§9-E) and the §2 shrink order are for.

**Calibration gate:** **20 clean + 20 mystery instances drawn DISJOINT from S and
discarded** — [corrected 07-25: the earlier "~20 instances from S + a 5-instance mystery
spot-check" both reused S (an internal-pilot reuse argument) and peeked at prediction
(i); 5 points also cannot bound a heavy-tailed cost distribution. Disjoint-and-discard
costs ≈$1.5 and removes the argument entirely.] Measure and record: **p90 output tokens
per trial (the headline number — output is 50-60% of WT per-trial cost and a 3.3× lever,
while turns are only a 2.4× lever across their whole legal range)**, $/trial, turn
distribution, loop_exhausted rate, the runner's ACTIVE / NET-LOSS / INACTIVE caching
verdict with `cache_read > 0` on ≥90% of trials, extraction rate, delegation rate, and
wall-clock. The gate's decision function reads **cost and throughput only** — never
graded accuracy, never the WT-vs-NT contrast; sample-size changes are increase-only;
extraction rate and loop_exhausted are outcome-neutral quality checks whose only
permitted consequence is fix-apparatus-and-restart. **[OMER ~10 min]** approves
calibrated scope + spend before the full run; the scaffold and the analysis script
freeze here.

**Kill criteria** (either fires → convert to Future Work): (a) calibration projects
the t1 2×2 above the remainder even at n=200/cell; (b) no graded WT table by
**2026-08-15**. **Fallback shape = SHRINK, NOT SCATTER:** Act 4 survives as the
NT-only re-measurement act with this WT design published inside it as
pre-registered Future Work; the NT beats are not dispersed across other acts.

## 9. Ratification-blocking amendments (added 2026-07-25; decisions memo §4)

Each item is measured, cheap, and would void the prereg after the fact if left. Accept
in bulk at the RATIFY slot, or annotate individual rejections.

- **A. Matched-NT scaffold parity.** `WITH_TOOLS_SYSTEM` asserts "Your ONLY way to get
  information or solve problems is by calling the provided tools", and the t1 format
  clause names `classic_planner`; with an empty tool list that control asserts a false
  premise and forbids the only available action, so it would measure instruction-conflict
  compliance and any depression it causes inflates the WT−NT delta in the hypothesis's
  favour. The accepted D-J3 ruling names only the NL→PDDL step and the task-format clause
  as shared, and the repo precedent is a length-matched mirror
  (`WITHOUT_TOOLS_SYSTEM_BY_TASK`, test-enforced). **Adopted:** coherent control — mirror
  the policy sentence, strike the tool name from the shared format clause, and name the
  contrast a package contrast (tool list + directive). **Plus a third arm on mystery t1
  only** (pure availability: dangling directive, empty tool list, n=250, ≈$2) as an
  outcome-neutral control that the directive alone moves nothing — the logic already
  ratified in `ntster_h4_prereg.md`. First item in the §2 shrink order. Both scaffold
  texts ship verbatim in an appendix. Wire-level note: if the API rejects `tools: []`,
  the tools parameter is omitted instead (the SDK loop degenerates to one `create()` call
  either way) — pre-registered as a wire substitution, not a scaffold change.
- **B. Roster:** 7 tools (pddl-solver + pddl-validator), ~4.1-4.4K token prefix.
  pddl-parser stays out of the model's roster and is used only at analysis time (§4).
- **C. Caching is a billing-layer property, not part of "identical in every respect".**
  The WT cacheable prefix sits ~5% above Haiku 4.5's 4,096-token minimum; the matched-NT
  prefix (~150 tokens, empty tool list) cannot cache at all; and `frontier_runner` passes
  a top-level `cache_control`, so the breakpoint falls after the per-instance user turn
  and cross-trial reuse of the tools+system prefix is structurally absent. Log per-trial
  cache tokens; record the runner's verdict per cell; re-project at the gate if caching
  reads INACTIVE.
- **D. Calibration gate** — see §8 (disjoint from S, discarded, 20+20, cost-only decision
  function, p90 output tokens as the headline).
- **E. Spend guard.** `frontier_runner` has no dollar cap; its only stop is an Anthropic
  "credit balance too low" exception, i.e. it halts when the money is already gone. Add
  `--max-spend` with a running accumulator that saves and exits (the resume path makes a
  mid-run stop safe): global cap **$50**, per-cell cap 2× the calibrated central
  projection. Worst legal trial (10 loops) ≈$0.135, and the measured loop_exhausted rate
  on our own apparatus is 1/4560, so the cap is a backstop rather than a throttle.
- **F. Exclusion / intercurrent-event table**, identical in both arms, denominator = |S|
  throughout: API error → one logged deterministic retry, then counted as failure;
  `loop_exhausted` → counted as failure, never retried (it is an outcome);
  `truncated_no_answer` → counted as failure; prompt-too-long 400 → counted as failure,
  logged; MCP/infra failure → retried once, logged; extraction failure → counted as
  failure (delivered surface). If excluded or censored rows exceed 10% of a cell, the
  cell is reported as **bounds, not a point estimate** (the project's existing censoring
  convention). **Single-run rule:** each cell runs once to completion; resume and mop-up
  only for infra failures, logged — load-bearing because this runner has a measured
  intermittent failure that vanished on re-run at temperature 0, so "run it again and
  keep the better number" is physically possible here.
- **G. Operational aborts, pre-registered.** Never `--run_till_completion` (an empty
  answer from a loop-exhausted trial is retried forever at temp 0 — an unbounded paid
  loop). Never `--ignore_existing` against `pddl_copilot__anthropic__claude-haiku-4-5`
  (it would overwrite the graded 06-22 NT corpus). Engine names
  `pddl_copilot__anthropic-tools__claude-haiku-4-5` (WT) and
  `pddl_copilot__anthropic-scaffold__claude-haiku-4-5` (matched-NT), with the new backend
  tokens added to `planbench/engine.py::_parse_engine_name` (whose allowlist is
  `{ollama, vllm, vllm-base, vllm-tools, anthropic}` and raises otherwise) and no `_chat`
  substring. Add `build_table` engine entries (its `OURS` list is hard-coded to four vllm
  Qwen engines) or an `--engines` flag. Provision a venv that can actually run WT
  generation before any spend (none can today: the PlanBench venv lacks `mcp`, the repo
  venv lacks `tarski`/`pddl`/`transformers`) and pin the `anthropic` version deliberately
  (0.109.2 and 0.111.0 are both present on this machine).
- **H. Freeze mechanics.** On ratification, stamp this document with its commit SHA and
  UTC timestamp and git-tag it `prereg-planbench-wt-v1`. Freeze the analysis script
  (per-cell Wilson + exact McNemar + Holm + the §3 band decision table + funnel
  decomposition), exercise it against the published bare-NT rows first, and pin its SHA
  here; only bug fixes may change it, each logged. Deviations are reported in a table
  (what changed / when / why / which clause / which claim is affected / whether that
  claim is downgraded to exploratory).
- **I. Claim wording (§1/§7).** The bare claim "tools convert PlanBench mystery failure
  to success" is already published (Huang & Zhang ACL 2025 verified 2026-07-25; La Malfa
  arXiv:2512.09629, LLMFP arXiv:2410.12112 and CoPE pending `/verify-claims`), so §1's
  secondary claim is a **replication with an ablation the field has not run**, and must
  say so. The surviving novelty: matched-scaffold single ablation, VAL grading on
  canonical instances, Wilson CIs and paired tests, the formalization-boundary metric,
  the delegation mediator, and measured $/trial. Presentation rule extended: every
  external comparator prints its pool size and its grader on the same line ("Mystery
  Blocksworld" denotes at least five different pools: ours 500; Valmeekam 600; LLMFP 602;
  H&Z/CoPE 100; La Malfa 93).

**N. t2 scope** (the exclusion rationale in §2 was false; the capability ships). Keeping
t2 out protects the 2026-08-15 date and the arm's simplicity; adding a mystery-t2 pair
buys the only like-for-like comparison to the strongest published rescue numbers
(optimal-plan rate 77.7 GPT-4o / 98.0 Claude 3.5 Sonnet at n=602, pending
`/verify-claims`).

**O. Domain authorship** (§4): model-authored keeps the arm's end-to-end claim and makes
the boundary metric use the 24-bijection domain check; injecting the gold domain reduces
the metric to problem-only set equality and turns the cells into a labelled "given PDDL"
variant.

> ANSWER (accept A-I in bulk, or list rejections):

> ANSWER (N — t2: keep excluded [recommended] / add a mystery-t2 WT+matched-NT pair
> (≈$12 at n=250) / defer to gate headroom):

> ANSWER (O — domain authorship: model authors domain+problem+plan [recommended] / gold
> domain injected):

## 10. Ratification

> RATIFY (design + predictions + rules above are binding as annotated):
