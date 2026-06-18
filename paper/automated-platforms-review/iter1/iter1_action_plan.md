# Iter 1 — Action Plan (triage of the two external reviews)

**Input:** `iter1_review_synthesis.md` (ScholarsReview 8.36/10 *accept*; Stanford Agentic
Reviewer *accept*). Both reviews are on the **post-rewrite** PDF, so they already reflect every
`REVIEW_AND_REWRITES.md` fix that landed in `main.tex`. This file dispositions **every** review
item as **CLOSE NOW / DEFER / DROP**, records the reviewer↔reviewer (and reviewer↔paper)
tensions and how they resolve, and lists the open compute/analysis decisions.

**Bar / goal.** AAAI-27 Main Technical, double-blind, abstracts **Jul 21**, full **Jul 28**.
Both reviewers already say accept, so iter-1 is *acceptance-probability maximization*: land every
cheap writing/analysis win, fund the one locked generality experiment (Sonnet no-tools), and keep
anything that would gate the deadline or dilute the single-suite message out of the body.

Status legend: ☐ to do · ◑ partly in paper · ✅ already satisfied (verify only) · ⏸ pending decision.

---

## 0. Disposition summary

| Bucket | Count | What |
|---|---|---|
| **CLOSE NOW** (writing/analysis, no new compute) | ~16 | grammar, definitions, $-estimate, prompt-text appendix, metric unification, narrative sharpening |
| **DEFER** (rebuttal / camera-ready / Future Work) | ~8 | cap-raised rerun, mixed-effects model, BF16 control, structural contamination, multi-tool, temperature, steering ablation, traces |
| **DROP** (no action) | ~5 | PDF-extraction artifact, mis-described "posterior bias", code-at-submission, PlanBench/formalizer-as-main, non-rule grammar nits |
| **DECIDED** (user, 2026-06-18) | 3 | cap rerun → don't (defend via failed pilot) · mixed-effects → delegated to subagent · BF16 control → discarded entirely |

---

## 1. CLOSE NOW — writing & light analysis (no new sweeps, fits the deadline)

### 1a. Grammar / copy-edit batch (ScholarsReview "Language and grammar")
- ☐ Oxford-comma consistency in the model list (§Models).
- ☐ Hyphenation consistency: `accuracy-when-calling` vs `tool-calling` (pick one form, apply paper-wide).
- ☐ Cost-of-pass: use the `÷` symbol *or* the verbal form consistently (currently mixed on p.7).
- ☐ "the 35B" vs "35B": consistent article use in Discussion.
- ☐ MCP double-parenthetical `Model Context Protocol (MCP) (Anthropic 2024)` → reflow.
- ☐ Table 1 caption terminal period — **verify** in compiled PDF (source `tab:tasks` already ends with a period; may be a PDF-extraction artifact).
- ☐ **Fig 3 (`token_quadrant`) log-x tick rendering** — extracted text shows "10 3 104"; regenerate so exponents render as `10^3 / 10^4` superscripts. (analyzer skill; figure-side fix.)
- *Optional polish (low value):* "one steering sentence repairs it" (punchy, venue-appropriate — leave unless the user wants it formalized); preposition-ending nit (non-rule).

### 1b. Definitions & front-loading (ScholarsReview Intro/Background)
- ☐ Define **reasoning mode** operationally at first use (abstract/intro parenthetical), not only in Methodology.
- ☐ Name the **open-weight families** (Qwen, Gemma) immediately when first mentioned in the Intro.
- ☐ **Quantify "limited prompt set"** of the earlier Copilot vs this corpus (need the earlier version's prompt count; we report N=4,560/cell). One concrete comparison sentence.
- ☐ Tie the **classical-vs-numeric** distinction to *why* LLMs struggle (numeric effects / arithmetic state-tracking are harder to hand-simulate). One sentence in Background.
- ☐ Summarize **Tantakoun et al. (2025)** conclusion in one clause rather than a bare cite.
- ☐ Make the **MCP** description one clause more accessible to non-Anthropic-ecosystem readers.

### 1c. Cost section — close the "tokens-only" gap (ScholarsReview "What the Tool Costs")
- ☐ Add a **dollar estimate** (recoverable: tokens × a representative open-weight serving price) and state it as an order-of-magnitude, model-/price-dependent figure.
- ☐ State **explicitly and prominently** that wall-clock latency is *not recoverable* from a batched server (currently only in Limitations), and name a concurrency=1 micro-benchmark as the honest future fix.
- ◑ **Prefix caching**: paper already notes ~90%; add the *cost effect* (re-fed schemas are cheap; tool outputs remain uncached real context) so it doesn't read as worst-case. One clause.

### 1d. Results / mechanism narrative (ScholarsReview Results & Appendix)
- ☐ **`simulate` 0% normalization example** — add a concrete canonical-form before/after snippet (appendix listing) so readers can judge the grading is not whitespace-pedantry.
- ☐ **silence-not-error: deeper hypothesis** — one Discussion sentence on *why* models prose-out (helpful-assistant prior; implicit-need not triggering an explicit call) — flagged as hypothesis, not over-claimed.
- ◑ **Table 4 (`tab:decomp`) guiding narrative** — a `\paragraph{Invocation decomposition.}` already exists; verify it foregrounds the P(call) vs P(correct|call) insight; tighten if buried.
- ◑ **`P(c|¬call)=0` legend clarity** — caption already explains "a missing tool call is ungradeable"; reword the table legend so the zero reads as *by-construction*, not surprising.

### 1e. Metric unification — `validate_domain` pooled vs balanced ([BOTH], theme #6)
- ☐ The paper **headlines balanced accuracy but runs the RQ1 significance test on pooled** (`tab:vdom` caption admits this). Unify: recompute the availability gap's CI-disjointness on **balanced accuracy** (quick recompute from raw trials, no new sweep) and either (i) test on the headline metric, or (ii) report both arms' CIs and state they are disjoint on both. Put the pooled+balanced pair in the main Results text (already partly there). *This is the one item both reviewers convergently flag and it is a real internal inconsistency — treat as near-must-fix.*

### 1f. Scope / claims hygiene (Discussion, Limitations, Future Work, Conclusion)
- ◑ **Over-broad generalization** — already softened ("natural hypotheses … suggest but not establish"); verify no other section over-claims; tighten one verb if needed.
- ☐ **"Delegation" ignores fine-tuning** — one Discussion clause acknowledging that invocation propensity could be internalized via fine-tuning/architecture, not only prompting.
- ☐ **20-domain representativeness** — one Limitations sentence of self-critique on coverage of PDDL complexity.
- ☐ **5:1 imbalance & F1** — one clause noting balanced accuracy (now the headline for `validate_domain`) already neutralizes the imbalance that an F1 concern targets.
- ☐ **Multi-turn / iterative self-correction → P(call)** (Stanford Q8) — add to Future Work alongside the existing multi-tool line.
- ☐ **Future Work sharpening** — make "agentic regimes" concrete (a multi-tool selection setup with ≥2 relevant tools present); add **model-modulo ensembles** (formalizer model ≠ checker model) as one line.
- ☐ **Conclusion** — add a *minimum-effective-steering* heuristic clause (one imperative sentence sufficed 4B→35B; 0.8B mishandles the call) and one clause summarizing the contamination null.
- ✅ **"67 pp drop" model-dependent qualifier** — already "one of three ≥9B models"; verify reads clearly.
- ☐ **(Q1) Cap-raised rerun → defended design choice.** Replace the Limitations line "a cap-raised rerun is untested" with an honest note that a larger-budget configuration was piloted and *degraded format adherence* (the 32K context smoke: +22–36 pp parse failures per model), so a naive budget increase trades the truncation confound for a parsing one — motivating the robust-floor approach as the principled alternative. *Caveat:* phrase cautiously (it was a context-window smoke, not a full think=on decode-cap sweep); rests on internal pilot data, so keep it qualitative ("in pilot runs … degraded format adherence") rather than quoting the smoke deltas as a paper result.

### 1g. Prompt text in appendix ([BOTH], theme #10 — *writing* half only)
- ☐ Add the **thin per-task policy-stub system prompts** (plain vs steered, byte-level) to the Technical Appendix. Central to a prompt-sensitivity paper; this is *showing text*, fully separable from code release, and high value. Closes the writing portion of theme #10 without touching the (deferred) code-release decision.

---

## 1Z. CLOSE NOW — APPLIED to `main.tex` 2026-06-18 (build clean: 13 pp, 0 undefined refs, 0 overfull)

Landed this pass:
- **Intro/Background:** "reasoning mode" glossed at first use (extended-thinking); Qwen/Gemma families
  named immediately; "limited prompt set" anchored to our scale (4,560 trials/cell); classical-vs-numeric
  tied to LLM difficulty (numeric = arithmetic state-tracking); Tantakoun conclusion summarized; MCP
  reflowed (single parenthetical via `\citep[MCP;][]`) + accessibility gloss.
- **Methodology (Q2):** GLMM robustness sentence + cell-by-cell justification (closes Stanford Q5).
- **Cost:** $-estimate + price-invariance of the ratio; explicit latency-unrecoverable statement +
  concurrency-1 future instrument; prefix-caching conservativeness clause.
- **Metric unification (near-must-fix):** `validate_domain` now headlines AND tests balanced accuracy
  (the appendix "tested on pooled" admission removed; +21–47pp balanced gap stated CI-disjoint).
- **Limitations (Q1):** cap-raised rerun reframed as a defended choice (naive budget increase degraded
  format adherence in pilots → trades confounds); 20-domain representativeness self-critique; 5:1 ↔
  balanced-accuracy/F1.
- **Discussion:** deeper silence-not-error hypothesis (instruction-tuning prior); fine-tuning lever.
- **Future Work:** sharpened multi-tool selection (≥2 tools), iterative self-correction, model-modulo
  ensembles; cap-raise replaced by a budget-decoupled design.
- **Conclusion:** minimum-effective-steering-dose heuristic.
- **Appendix:** verbatim per-task policy stubs + all 5 steering directives (Listing 1, from
  `pddl_eval/prompts.py`); concrete `simulate` canonicalization example.
- **Copy-edits:** `accuracy-when-calling`→`accuracy-given-a-call` unified. Verified-and-skipped as
  PDF-artifact / already-consistent: `theverdictpatternreproduces` (spaces present), Table 1 period
  (present), `÷` usage (consistent), "the 35B" article (consistent), preposition nit (non-rule).

Residual CLOSE-NOW (not a `main.tex` text edit):
- ☐ **Fig 3 (`token_quadrant`) log-x tick rendering** — generated asset; regenerate via the analyzer
  skill so exponents render as `10^3/10^4`. Not done this pass.
- ◑ **"limited prompt set" exact earlier count** — used our-side scale anchor; can become a direct ratio
  if the earlier Copilot's prompt count is supplied.
- ⏳ **Camera-ready:** rerun the confirmatory GLMM non-VI (Laplace/MCMC/statsmodels) so the published
  coefficient is from a standard estimator (sign/magnitude already robust).
- **DEFERRED (analysis, not done):** cost-of-pass split by classical-vs-numeric (Scholars) — needs a
  per-domain-class data cut; one honest acknowledgment sentence is the cheap alternative if wanted.

## 2. DEFER — strengthen for rebuttal / camera-ready / route to Future Work

| Item | Theme | Why defer (not now) | Where it goes |
|---|---|---|---|
| **Cap-raised `think=on` rerun** | #1 [BOTH] | **RESOLVED Q1 — DO NOT RERUN.** A budget increase was already piloted (32K context smoke, memory `project_ctx_bump_32k_smoke_failed`) and *raised* format-parse failures +22–36 pp/model. A naive cap-raise trades the truncation confound for a parsing confound, so it is not a clean fix. | reframe Limitations as a *defended design choice* (see 1f-Q1); not a run |
| **Mixed-effects / clustered inference** | #5 [BOTH] | **RESOLVED Q2 — keep post-hoc √2.7 as primary + ONE confirmatory GLMM** on the clean Gemma `validate_plan` plain→steered contrast. GLMM does not move the verdict (log-odds +7.5, z≈78; GEE agrees); CIs disjoint with & without √2.7. Model-fitting rejected as primary due to boundary separation. | **CLOSE NOW** (writing): paste-ready Methods sentences in `.local/...recommendation.md`; rerun the confirmatory fit non-VI before camera-ready |
| **BF16-35B *with-tools* precision control** | #2 [BOTH] | **RESOLVED Q3 — DISCARDED ENTIRELY.** sweep7 (the BF16 run) is dropped in full; no new cluster BF16 run. Confound stays disclosed via the within-model `P(call)×P(correct\|call)` reframe + Limitations sentence already in the paper. | within-model reframe (already in paper); **also drop** the §7D "keep sweep7 no-tools as appendix note" |
| **Structural / deeper contamination** (permute arities, type indirection) | #8 [BOTH] | new fixture build; not cleanly deadline-feasible; symbol-rename control already null | Future Work + one Limitations clause |
| **Multi-tool selection / agentic generalization** | #7 [BOTH] | scope expansion = a different paper's contribution | Future Work (sharpen per 1f) |
| **Temperature sensitivity** | Stanford W-method-1 | compute; temp-0 is a deliberate design choice | Limitations note + Future Work |
| **Steering-sentence phrasing ablation** | #4 [Stanford only] | compute; not convergent; the steering effect is already large and mechanism-backed | Future Work |
| **Trace-providing model on key cells** | Scholars Limitations | new run; think=off gives no CoT anyway; tangential to the propensity claim | Limitations (already notes no traces) |

---

## 3. DROP — no action (out of scope, non-issues, or contradicts a locked decision)

- **`theverdictpatternreproducesunder`** (grammar #1) — PDF-extraction artifact; source (`main.tex` Intro contributions) has correct spaces. Verify-and-ignore.
- **"5:1 ratio biases the posterior toward valid"** (Scholars Methodology) — mis-describes our method: we use frequentist Wilson/MOVER intervals, not a Bayesian posterior, and we now **headline balanced accuracy** for `validate_domain`, which removes the imbalance bias. Address by pointing to balanced accuracy (covered in 1e/1f), **not** by adopting the "posterior" framing.
- **Full source-code release at submission** (theme #10 release half) — locked decision: release at **publication**, not submission; checklist stays honest. Only the prompt *text* is closed now (1g).
- **PlanBench / formalizer baselines as main-paper experiments** (Stanford Background scope) — locked: Future Work. A single sharp suite beats a sprawling one for AAAI Main.
- **Head-to-head with multi-agent/formalizer orchestration frameworks** (Stanford Background) — out of scope; Future Work already names Huang & Zhang.
- **GPT-OSS-120B** — already considered and set aside (`REVIEW_AND_REWRITES.md` §7B); not a capability step-up, flaky with-tools path.

---

## 4. Disagreements & contradictions — and how they resolve

**D1 — Narrow the claims (ScholarsReview) vs broaden the evidence (Stanford).**
Scholars flags the Discussion as over-generalizing to "tool-augmented LLMs more broadly"; Stanford
wants *more* experiments (multi-tool, agentic, frontier, structural contamination) to *earn* that
generality. Opposite directions. **Resolution:** we cannot run Stanford's full battery by Jul 28,
so the dominant lever is Scholars' — keep generality as **explicitly-flagged hypotheses** (already
softened), run the **one** highest-ROI generality experiment that is locked and funded (Sonnet 4.6
no-tools frontier + contamination probe, `REVIEW_AND_REWRITES.md` §7A), and route the rest to a
concrete Future Work. This *fully* satisfies Scholars and *partially* satisfies Stanford (one
frontier datapoint + a concrete plan). The two asks are reconcilable because narrowing the claim
and adding one datapoint both reduce the same gap.

**D2 — Cost beyond tokens (ScholarsReview) vs a hard methodological constraint.**
Scholars wants dollars *and* latency; latency is **not recoverable** from our batched server
(synthetic `_ns`; memory `project_tool_efficiency_metrics`). **Resolution:** add the **$ estimate**
(recoverable from tokens), state the latency limitation **explicitly and up front** in the Cost
section with the reason, and name a concurrency=1 benchmark as the future fix. Partial satisfaction
is the honest ceiling here, and saying so is stronger than a fabricated latency number.

**D3 — Pooled vs balanced metric: reviewer↔paper, not reviewer↔reviewer.**
Both reviewers caught the same real inconsistency — we **headline balanced accuracy but test
significance on pooled**. Not a disagreement between them; a defect they jointly surface.
**Resolution:** unify the metric (1e) — recompute disjointness on balanced accuracy and make the
`tab:vdom` caption consistent. Cheap, and removes a concrete reviewer objection.

**D4 — Cap-raised rerun: the reviews (do it, it's *fixable*) vs our scope decision (defer).**
This is the sharpest review↔plan tension: **both** reviewers rank it #1 and explicitly say deferring
a *fixable* validity issue to Future Work is weak. **RESOLVED (user, Q1): do NOT rerun — and the
reason is stronger than "we didn't get to it."** We already piloted a larger-budget configuration
(the 32K context smoke), and it *raised* format-parse failures +22–36 pp per model. So the rerun the
reviewers want does not cleanly isolate the tool's value: it trades the truncation confound for a
parsing confound. The robust-floor construction is precisely the principled way to read cross-mode
evidence *without* paying that price. **Action:** make this explicit in Limitations (1f-Q1) so the
reviewers' #1 ask is met by a defended design rationale, not an untested gap. This turns the
weakest-looking section into a deliberate methodological choice.

---

## 5. DECISIONS — RESOLVED (user, 2026-06-18)

- **Q1. Cap-raised `think=on` rerun → DO NOT RERUN.** Rationale (user): "if it already failed, why
  try it again?" — a larger-budget configuration was already piloted (32K context smoke,
  `project_ctx_bump_32k_smoke_failed`) and degraded format adherence (+22–36 pp parse failures), so a
  rerun trades the budget confound for a parsing one rather than removing it. **Action:** convert the
  Limitations "a cap-raised rerun is untested" line into a defended design choice (1f-Q1). *Honesty
  caveat in wording:* the smoke was a context-window bump (broader than "decode cap") and a smoke not
  a full sweep — phrase as "in pilot runs, enlarging the budget degraded format adherence," do not
  overstate.
- **Q2. Mixed-effects inference → RESOLVED (subagent, 2026-06-18):** keep the post-hoc √2.7
  inflation as the **primary** defense (uniformly valid across the degenerate matrix) **and add one
  random-intercept GLMM** on the clean Gemma-MoE `validate_plan` plain→steered contrast as a
  belt-and-suspenders robustness check. **A GLMM does NOT move the conclusions** — verified live on
  `sweep5v2-live`: steering log-odds $+7.5$ (posterior SD 0.10, z≈78), a GEE cross-check agrees, and
  both plain Wilson and √2.7-inflated CIs stay disjoint + favorable. Bonus: the subagent's measured
  ICC 0.40–0.73 / deff 1.80–2.46 **bracket and slightly undercut** the paper's ≈0.6 / 2.2–2.7, so the
  √2.7 inflation is *mildly conservative* (referee-friendly). GLMM/GEE/CR2/bootstrap rejected as
  *primary* for a **numerical** reason (boundary separation: `simulate` 0/3,000; tool arms
  P(c|call)≈0.99; 9B `validate_domain` success-separated), not a philosophical one. Paste-ready
  Methods sentences + a one-line citable result in `.local/mixed_effects_inference_recommendation.md`;
  probe at `.local/glmm_feasibility_probe.py`. *Minor refinement before camera-ready:* the
  confirmatory fit used variational inference for speed — rerun as Laplace/MCMC (or statsmodels) so the
  published coefficient is from a standard estimator (sign/magnitude already robust per the subagent).
  **Folds into the combined stats-paragraph pass** (with the Q1 reframe).
- **Q3. BF16-35B with-tools control → DISCARDED ENTIRELY** (user: "sweep 7 is entirely discarded").
  Keep the within-model decomposition reframe + Limitations sentence already in the paper; no new
  run; and **drop** the prior §7D plan to keep sweep7's no-tools as an appendix robustness note.

---

## 6. Already satisfied by the prior rewrite (verify-only, no action)

Title set · RQs enumerated (RQ1–RQ6, "0." prefix dropped) · two regime axes disambiguated ·
`validate_domain` balanced-accuracy reframe + `tab:vdom` · invocation decomposition `tab:decomp` ·
failure-taxonomy figure · Discussion section added · three statistics sentences (ICC≈0.6, design
effect 2.2–2.7 + √2.7 inflation; disjoint-CI conservativeness; no FWER) · per-task contamination
`tab:contam-pertask` · quantization + prompt-clause confounds disclosed in Limitations ·
reproducibility checklist inlined · "67 pp" model-dependent qualifier.
