# Iter 2 — External Review Synthesis (unified, action-plan-ready)

Consolidated view of the **two iter-2 external reviews** of *Availability Is Not Enough:
When Symbolic Tools Help—and Hurt—LLMs on Planning Tasks*. Both are from the **Stanford
Agentic Reviewer** platform, run twice under two venue rubrics. **Both recommend ACCEPT.**

This file is organized **by ask, not by paper section** (iter1 was section-by-section), so it
feeds straight into an action plan: every distinct weakness/question from both reviews is
collapsed into one numbered ask, tagged by convergence, effort, and its relationship to iter1.

Source files (names now match their content venue):
- [`stanfordAAAI.md`](stanfordAAAI.md) → **Venue: AAAI** (tagged `[AAAI]` below)
- [`stanfordneuroIPS.md`](stanfordneuroIPS.md) → **Venue: NeurIPS** (tagged `[NeurIPS]` below)

---

## How to read this

- **Convergence tag** — `[BOTH]` (raised in both reviews; highest priority), `[AAAI]`, `[NeurIPS]`.
- **Effort** — *writing / analysis / compute / release*, same vocabulary as iter1.
- **iter1 link** — `RECURS #n` (same ask as iter1 theme *n*; may already have a disposition)
  or `NEW` (first surfaced in iter2).
- **Existing evidence** column is a cross-reference to settle/short-circuit the ask when we
  derive the action plan — it is *not* part of the review and is **to be confirmed**, not assumed.

This round had **no ScholarsReview** (iter1 had Scholars + Stanford); both iter2 reviews are the
Stanford agentic reviewer, so there is no per-section numeric scorecard this time. There are also
**no copy-edit / grammar findings** this round.

---

## Bottom line

- **Both platforms: ACCEPT.** NeurIPS rubric → "Recommendation: Accept." AAAI rubric →
  "well-suited for publication at AAAI."
- The two reviews are **strongly convergent** — most asks are `[BOTH]`. Both independently
  re-derive the same praise: three-arm design, `P(call) × P(correct|call)` decomposition,
  signed-significance rule, strict oracle grading, contamination control, cost-of-pass framing.
- **Mostly a re-run of iter1's open asks**, not new objections: quantization confound,
  prompt-clause confound, steering-sentence ablation, think=on budget, frontier tool-use, and
  multi-tool generalization all recur. Several already have dispositions on record from iter1.
- **Genuinely new in iter2** (worth deciding on): (a) **multiple-testing / FWER correction**
  `[AAAI]`; (b) **partial-credit / alternative-schema grading for `simulate`** `[BOTH]`;
  (c) **tool-schema salience & verbosity → P(call)** `[BOTH]`; (d) **light fine-tuning / constrained
  decoding to raise P(call)** `[AAAI]`; (e) **stochastic-decoding (temperature) sensitivity** `[NeurIPS]`;
  (f) a **practitioner executive summary** of effect sizes `[NeurIPS]`.

---

## Consolidated asks — master table (the action-plan seed)

Ranked by convergence first, then leverage. `A#` = AAAI question number, `N#` = NeurIPS question number.

| #  | Ask | Tag | Effort | iter1 | Maps to Qs |
|----|-----|-----|--------|-------|-----------|
| 1  | **Frontier / closed models in the *with-tools* arms** — does the availability/steering gap persist under aggressive tool-use post-training, or vanish? | `[BOTH]` | compute | RECURS #9 | A6, N6 |
| 2  | **Quantization control** — re-run one large model at higher precision (BF16) to separate *size* from *AWQ-INT4* in spontaneous tool-adoption / size-inversion. | `[BOTH]` | compute | RECURS #2 | A7, N(W-tech) |
| 3  | **Matched-prompt availability ablation** — hold the policy/format clause constant so the no-tools vs tool-available contrast differs *only* in tool presence. | `[BOTH]` | compute | RECURS #3 | A(W-tech), N1 |
| 4  | **Steering-sentence ablation** — vary phrasing (imperative vs suggestive), placement, and "implicit" steering; how robust is the propensity effect to wording? | `[BOTH]` | compute | RECURS #4 | A3, N2 |
| 5  | **`simulate` grading beyond exact-match** — (a) partial-credit / per-step metric; (b) alternative output schemas / structured decoding — is the 0% unaided rate state-tracking failure or JSON-verbosity / formatting? | `[BOTH]` | analysis + compute | NEW | A5, N3 |
| 6  | **Tool-schema salience & verbosity → P(call)** — does a more salient tool name/description, or a shorter schema, raise invocation without explicit steering (and at what token cost)? | `[BOTH]` | compute | NEW | A4, N5 |
| 7  | **Multi-tool / multi-call / agentic generalization** — report multi-call statistics; test selection among several relevant tools and iterative self-correction; head-to-head with orchestration baselines. | `[BOTH]` | compute + scope | RECURS #7 | A1, N(related) |
| 8  | **think=on budget decoupling** — separate decode caps for reasoning vs final answer to remove the shared-budget confound. | `[AAAI]` | compute | RECURS #1 | A2 |
| 9  | **Multiple-testing / FWER correction** — breadth of comparisons invites family-wise error concerns; add a correction or justify the conservative signed-CI rule as sufficient. | `[AAAI]` | analysis | NEW | — |
| 10 | **Light fine-tuning / constrained decoding to raise P(call)** without harming P(correct\|call) — beyond prompting. | `[AAAI]` | compute + future | NEW | A8 |
| 11 | **Stochastic-decoding sensitivity** — report P(call) under temperature / nucleus sampling, not only temperature 0. | `[NeurIPS]` | compute | RECURS (W-method-1) | N4 |
| 12 | **Cost realism — production optimizations, latency, $** — note that not re-feeding/summarizing tool outputs cuts input-token overhead; add a latency complement and/or $ estimate. | `[BOTH]` | writing + analysis | RECURS #11 | A(W-clarity), N7 |
| 13 | **Reproducibility / deployment detail** — hardware-software stack, tool-call iteration stats, tool latency. | `[AAAI]` | writing + release | RECURS #10 | — |
| 14 | **Related-work head-to-heads** — ReAct-style / program-of-thought routing `[NeurIPS]`; PlanBench-style evals, alternative PDDL toolchains, LLM-as-formalizer pipelines `[AAAI]`; RLAIF/RLHF influence on invocation propensity `[AAAI]`. | `[BOTH]` | writing | RECURS (related) + NEW angles | — |
| 15 | **Richer PDDL fragments** — temporal / durative / conditional-effect constructs are out of scope; conclusions may shift. | `[BOTH]` | scope / future | RECURS (limits) | — |
| 16 | **Practitioner executive summary** — the paper is dense; add a concise summary of the major effect sizes for practitioners. | `[NeurIPS]` | writing | NEW | — |

---

## Asks in detail

Grouped by kind. Each item notes the source review(s) and the verbatim substance.

### A. Controls & confounds (compute-heavy; mostly iter1 carryover)

- **[1] Frontier with-tools `[BOTH]` · RECURS #9.** Tool-use is open-weight only; just the
  *unaided* baseline is reported for a proprietary model, so the invocation-propensity phenomenon
  is "untested on frontier models with aggressive tool-use post-training" (NeurIPS W-gap). AAAI Q6 /
  NeurIPS Q6 both ask directly for *with-tools* proprietary results.
  *Existing evidence (confirm):* this is the **live phase** — the Sonnet/Haiku with-tools probe.
  The no-tools frontier result (Sonnet 4.6) is already in the paper; the open question is the
  with-tools cell cost-gate, not whether to do it.

- **[2] Quantization control `[BOTH]` · RECURS #2.** Largest models are AWQ-INT4 while smaller
  ones are 16-bit, so "cross-model differences in spontaneous tool adoption may partially reflect
  quantization." AAAI Q7 asks to "re-run one large model in higher precision … to separate size vs
  quantization."
  *Existing evidence (confirm):* iter1 disposition recorded BF16 control as *discarded*, **but** a
  35B BF16 run on RunPod (sweep7) found **AWQ-INT4 ≈ BF16** (quant does not degrade 35B think=on) —
  i.e. the experiment that answers this reviewer was effectively run. The action item may be to
  *fold the existing BF16 evidence into the paper* rather than run anything new.

- **[3] Matched-prompt availability ablation `[BOTH]` · RECURS #3.** The no-tools vs tool-available
  contrast also differs by "a short system prompt clause," confounding availability with a subtle
  instruction difference (acknowledged in Limitations). NeurIPS Q1 asks for "exactly matched system
  prompts (minus tool presence)."

- **[4] Steering-sentence ablation `[BOTH]` · RECURS #4.** Both ask how sensitive the
  availability/steering gaps are to the exact steering sentence — imperative vs suggestive phrasing,
  placement (AAAI Q3), and whether a more imperative *user* instruction nudges invocation without a
  separate directive line ("implicit" steering, NeurIPS Q2).

- **[8] think=on budget decoupling `[AAAI]` · RECURS #1.** `think=on` is confounded by a shared
  decode budget; the robust-floor approach helps but "a fully decoupled budget design would be
  stronger." AAAI Q2 asks for separate caps for reasoning vs final answer and the effect on
  truncation / format adherence.
  *Existing evidence (confirm):* iter1 disposition was **do not rerun** — defend via the failed
  32K-cap pilot (raising the cap reintroduced format-parse failures). Same defense applies here.

### B. Grading & metrics (the sharpest *new* asks)

- **[5] `simulate` grading beyond exact-match `[BOTH]` · NEW.** Exact-match trajectory grading gives
  no partial credit and may "understate near-correct unassisted reasoning" (AAAI W-gap, Q5 asks
  whether a per-step / partial-credit metric would change the unaided-vs-tool conclusion). NeurIPS
  Q3 attacks the same 0% from the other side: try per-step deltas / compressed state diffs under
  schema constraints to test whether the unaided failure is **JSON verbosity / formatting**, not
  state-tracking. Together: *is the headline 0% a capability result or a formatting artifact?*
  *Note:* iter1 only asked us to show the canonical normal form; iter2 escalates to an actual
  alternative-metric / alternative-schema probe.

- **[9] Multiple-testing / FWER `[AAAI]` · NEW.** "No multiple testing correction is applied;
  although effect sizes are large and the authors use a conservative signed-CI rule, the breadth of
  comparisons invites FWER concerns." Lowest-effort new ask — likely answerable in analysis/writing
  by either adding a correction on the headline contrasts or arguing the signed-CI rule + effect
  sizes make it moot.

### C. Mechanism of invocation propensity (new levers)

- **[6] Tool-schema salience & verbosity `[BOTH]` · NEW.** NeurIPS Q5: does making the tool
  name/description more salient raise P(call) without explicit steering? AAAI Q4: ablate schema
  verbosity (shorter function descriptions) and measure the effect on invocation propensity *and*
  token cost. A direct probe of *why* models under-call.

- **[10] Fine-tuning / constrained decoding for P(call) `[AAAI]` · NEW.** AAAI Q8: beyond prompting,
  have you explored light fine-tuning or constrained decoding to raise P(call) without harming
  P(correct|call)? (iter1 only *noted* in Discussion that delegation was framed as a prompting issue
  ignoring fine-tuning; iter2 turns that into a direct ask.) Naturally future-work.

- **[11] Stochastic-decoding sensitivity `[NeurIPS]` · RECURS (W-method-1).** Temperature 0 ensures
  determinism but leaves robustness to sampling open; NeurIPS Q4 asks for P(call) under higher
  temperature / nucleus sampling.

### D. Scope & generalization

- **[7] Multi-tool / multi-call / agentic `[BOTH]` · RECURS #7.** AAAI Q1 asks how often multiple
  tool calls (beyond the first) occurred and whether single-call limiting changes outcomes/cost
  (note: the active harness is single-task / effectively single-tool — this is partly a
  *reporting* ask, partly a scope ask). NeurIPS wants head-to-heads with multi-tool orchestration /
  iterative self-correction baselines that could mitigate under-calling.

- **[15] Richer PDDL fragments `[BOTH]` · RECURS (limits).** Temporal / durative / conditional-effect
  constructs and multi-tool orchestration are excluded; "conclusions may shift in richer PDDL
  fragments." Future-work framing already partly present.

### E. Cost, reproducibility, related work, presentation (writing-led)

- **[12] Cost realism `[BOTH]` · RECURS #11.** NeurIPS Q7 / W-clarity: production-side optimizations
  (not re-feeding full tool outputs, summarizing them) would lower input-token overhead on
  validation tasks — note this so cost-of-pass doesn't read as worst-case. AAAI: add a **latency**
  complement; empirical timing would be informative.
  *Existing evidence (confirm):* draft already states latency is unrecoverable from a batched server
  and mentions ~90% prefix caching — make the caching effect and a $-estimate more prominent rather
  than run new timing.

- **[13] Reproducibility / deployment detail `[AAAI]` · RECURS #10.** Expand hardware/software stack,
  tool-call iteration statistics, and tool latency to "aid reproducibility and deployment realism."

- **[14] Related-work head-to-heads `[BOTH]`.** NeurIPS: situate vs ReAct-style deliberate
  verification/routing and program-of-thought integrations that may influence invocation propensity;
  no head-to-head with multi-tool planning-agent baselines. AAAI: PlanBench-style evals, alternative
  PDDL toolchains, LLM-as-formalizer pipelines deferred; and limited discussion of
  RLAIF/RLHF/policy-tuning influence on propensity "despite being central to the observed variance."
  Mostly writing; the RLHF-propensity discussion is a `NEW` angle.

- **[16] Practitioner executive summary `[NeurIPS]` · NEW.** "The paper is dense; some readers may
  desire a more concise executive summary of the major effect sizes, especially for practitioners."

---

## Strengths to preserve (do not regress)

Both reviews independently re-praise the same load-bearing elements — keep them intact through any revision:

- **Three-arm design** cleanly decouples availability from a one-sentence steering nudge.
- **`P(call) × P(correct|call)` invocation-propensity decomposition** — both call this the standout,
  mechanistic, actionable contribution (variance lives in *whether* the tool is called, not accuracy).
- **Signed-significance rule** (CI disjointness + direction) correctly separates *help* from *harm*.
- **Strict end-to-end oracle grading** against deterministic planners/validators; per-trial failure-type breakdowns.
- **Statistical care** — Wilson / MOVER intervals, design-effect inflation, and a GLMM/GEE check on a key contrast under paraphrase clustering.
- **Contamination control** via symbol anonymization, with a frontier no-tools probe corroborating the sole-source floors and the null.
- **Cost-of-pass framing** — "tools pay where the baseline is floored, a luxury otherwise"; the
  plan-length scaling (benefit rises with harder instances) and object-count null are singled out as compelling.
- **Honest, transparent Limitations** — decode-budget confound, quantization caveat, prompt differences.

---

## Author questions — verbatim, mapped to asks

**NeurIPS review** ([`stanfordneuroIPS.md`](stanfordneuroIPS.md)):

1. Matched system prompts (minus tool presence) to isolate availability. → **[3]**
2. Minimal "implicit" steering (imperative user instruction, no separate directive). → **[4]**
3. `simulate` with alternative structured outputs (per-step deltas / compressed diffs) under schema constraints — verbosity vs state-tracking. → **[5]**
4. P(call) under higher temperature / nucleus sampling. → **[11]**
5. Sensitivity to tool descriptions / MCP argument schemas — does a more salient name/description raise P(call) without steering? → **[6]**
6. Proprietary models with tool access enabled (not only unaided). → **[1]**
7. Cost-of-pass under production optimizations (not re-feeding / summarizing tool outputs). → **[12]**

**AAAI review** ([`stanfordAAAI.md`](stanfordAAAI.md)):

1. How often multiple tool calls were used; does single-call limiting change outcomes/cost? → **[7]**
2. Budget-decoupled think mode (separate caps reasoning vs answer) — effect on truncation / format adherence? → **[8]**
3. Sensitivity of availability/steering gaps to small steering-sentence variations (imperative vs suggestive, placement). → **[4]**
4. Schema-verbosity ablation (shorter function descriptions) → invocation propensity and token cost. → **[6]**
5. Partial-credit / per-step metric for `simulate` — would it change the unaided-vs-tool conclusion? → **[5]**
6. With-tools arms on proprietary models with strong tool-use post-training. → **[1]**
7. Quantify AWQ-INT4 effect (re-run one large model higher-precision) to separate size vs quantization. → **[2]**
8. Light fine-tuning / constrained decoding to raise P(call) without harming P(correct|call). → **[10]**

---

## Recommendations

| Platform (rubric) | File (content venue) | Verdict |
|---|---|---|
| Stanford Agentic Reviewer — NeurIPS | `stanfordneuroIPS.md` (NeurIPS) | **Accept** |
| Stanford Agentic Reviewer — AAAI | `stanfordAAAI.md` (AAAI) | **Accept** ("well-suited for publication at AAAI") |

---

## Suggested triage for the action-plan step (preview, not decided)

- **Already answered / fold-in only:** [1] frontier with-tools (live phase), [2] quantization
  (RunPod BF16 ≈ AWQ evidence exists), [8] think=on budget (failed 32K pilot defense), [12] cost
  (caching/$ already in draft). → mostly *writing* to surface existing evidence.
- **Lowest-effort new wins:** [9] FWER (analysis/writing), [16] exec summary (writing),
  [14] RLHF-propensity + ReAct/PlanBench framing (writing).
- **Decide whether to run:** [5] `simulate` partial-credit/schema probe, [6] schema-salience/verbosity
  probe — both *new*, both `[BOTH]`, both directly attack the headline mechanism, so highest
  scientific leverage if we have compute.
- **Defer to future work:** [7] multi-tool/agentic, [10] fine-tuning for P(call), [11] stochastic
  decoding, [15] richer PDDL fragments.
