# Iter 1 — External Review Synthesis

Consolidated, navigable view of the **two external reviews** of the AAAI-27 submission
*Availability Is Not Enough: When Symbolic Tools Help—and Hurt—LLMs on Planning Tasks*.
Both reviews are on the **current (post-rewrite) draft** — `paper_submitted.pdf` already
contains the rewrite fixes (corrected decomp row, AWQ/precision Limitations sentence,
volatility reframe, `14–92%` truncation range, corrected Huang citation).

**Both platforms recommend ACCEPT.** ScholarsReview overall **8.36/10**; Stanford Agentic
Reviewer: *"a valuable contribution suitable for AAAI."*

Use this file to fix iter-1 weaknesses one area at a time: jump via the [Contents](#contents),
read only the section you are addressing, and open the source PDFs only when you need the
verbatim wording. Each item is tagged **[Scholars]**, **[Stanford]**, or **[BOTH]** (highest
priority = convergent), plus an effort label *(writing / analysis / compute / release)*.

## Source artifacts

- [`paper_submitted.pdf`](paper_submitted.pdf) — the reviewed paper (12 pp, post-rewrite)
- [`scholarsreview_res.pdf`](scholarsreview_res.pdf) — ScholarsReview: per-section scores, weaknesses, strengths, grammar (8.36/10, *accept*)
- [`stanfordreview_res.pdf`](stanfordreview_res.pdf) — Stanford Agentic Reviewer: summary, strengths, weaknesses, 10 author questions (*accept*)

## Contents

- [Top recurring themes](#top-recurring-themes) — the priority cross-cutting asks
- [Introduction](#introduction)
- [Background and Related Work](#background-and-related-work)
- [Methodology](#methodology)
- [Results](#results)
- [What the Tool Costs](#what-the-tool-costs)
- [Robustness (reasoning mode and contamination)](#robustness-reasoning-mode-and-contamination)
- [Discussion](#discussion)
- [Limitations](#limitations)
- [Future Work](#future-work)
- [Conclusion](#conclusion)
- [Technical Appendix](#technical-appendix)
- [Stanford questions for authors](#stanford-questions-for-authors)
- [Language and grammar (ScholarsReview)](#language-and-grammar-scholarsreview)
- [Scores, strengths, and recommendations](#scores-strengths-and-recommendations)

---

## Top recurring themes

The high-leverage asks, ranked by how central + how convergent across the two reviews.
*(Note: each links to the per-section detail below.)*

1. **Cap-raised `think=on` rerun** — **[BOTH]** *(compute)*. Rerun reasoning-mode with a larger
   decode cap on a subset of tasks to remove the shared-budget confound, rather than only
   defending it with the robust floor. → [Robustness](#robustness-reasoning-mode-and-contamination), [Future Work](#future-work), Stanford Q3.
2. **BF16 precision control on the 35B** — **[BOTH]** *(compute)*. The size-inversion claim is
   confounded (35B is AWQ-INT4, 9B is 16-bit). A 16-bit run of the 35B on key cells would
   decouple size from quantization. Currently disclosed in Limitations but not controlled. → [Methodology](#methodology), [Limitations](#limitations), Stanford Q9.
3. **Hold the policy/format clause constant** — **[BOTH]** *(compute)*. The availability gap's
   no-tools vs plain prompts differ by a one-line policy/format clause beyond tool presence;
   an ablation that differs *only* in tool presence would fully isolate availability. → [Methodology](#methodology), Stanford Q2.
4. **Steering-sentence ablation** — **[Stanford]** *(compute)*. Vary the single steering
   sentence (semantically similar / dissimilar wordings, distractor instructions) to show how
   robust the propensity effect is to phrasing. → [Methodology](#methodology), [Results](#results), Stanford Q1.
5. **Clustered / mixed-effects inference** — **[BOTH]** *(analysis)*. Fit instance+paraphrase
   random-effects logistic models and report whether significance conclusions move vs
   Wilson/MOVER intervals (the paper currently uses a post-hoc design-effect inflation check). → [Methodology](#methodology), Stanford Q5.
6. **Unify pooled vs balanced accuracy for `validate_domain`** — **[BOTH]** *(writing/analysis)*.
   Put balanced and pooled side by side in the main Results text, and use one metric for the
   significance test (the paper headlines balanced but tests on pooled). → [Results](#results), [Technical Appendix](#technical-appendix).
7. **Multi-tool selection / agentic generalization** — **[BOTH]** *(scope/future)*. Test
   selection among several relevant tools (e.g. validator + simulator both present) and
   multi-call/iterative settings. → [Discussion](#discussion), [Future Work](#future-work), Stanford Q6, Q8.
8. **Deeper / structural contamination** — **[BOTH]** *(compute)*. Beyond symbol renaming,
   perturb structure (permute action arities, type indirection) to probe structural
   memorization of common domains (e.g. Blocksworld logic). → [Robustness](#robustness-reasoning-mode-and-contamination), Stanford Q7.
9. **Frontier / closed-weight models** — **[Stanford]** *(compute/future)*. Whether propensity
   dynamics persist at the frontier (the planned no-tools Sonnet probe partially answers this). → [Future Work](#future-work).
10. **Release harness, fixtures, prompts, MCP schemas** — **[BOTH]** *(release)*. In particular
    the exact "thin per-task policy stub" prompt text, which is central to the paper's theme
    but not shown in the main text. → [Methodology](#methodology), [Technical Appendix](#technical-appendix), Stanford Q10.
11. **Cost beyond tokens ($ and latency)** — **[Scholars]** *(writing)*. Token-only cost feels
    incomplete to practitioners. (Draft already states latency is unrecoverable from a batched
    server; consider noting a dollar estimate.) → [What the Tool Costs](#what-the-tool-costs).

---

## Introduction

- **[Scholars]** *(writing)* The critique of the Planning Copilot as having a "limited prompt
  set" is not quantified relative to this study's corpus — give concrete numbers so the reader
  can gauge the scale improvement. *(Para 2, line 15.)*
- **[Scholars]** *(writing)* "Open-weight models" is mentioned without naming the specific
  families immediately, delaying architectural context. *(Para 3, line 5.)*
- **[Scholars]** *(writing)* "Reasoning-mode" is used before any operational definition,
  assuming familiarity with internal model states not clarified until Methodology. *(Para 4, line 12.)*

## Background and Related Work

- **[Scholars]** *(writing)* The classical-vs-numeric planning distinction is stated but not
  tied to *why* LLMs might struggle more with one than the other. *(Sec 2, para 1, line 8.)*
- **[Scholars]** *(writing)* Tantakoun et al. (2025) is cited without summarizing its
  conclusions or how they differ here — treated as a placeholder rather than integrated. *(Sec 3, para 1, line 12.)*
- **[Scholars]** *(writing)* The MCP description assumes prior knowledge of the Anthropic
  ecosystem; make it more accessible to non-specialists. *(Sec 4, para 1, line 5.)*
- **[Stanford]** *(scope)* No direct head-to-head with recent formalizer pipelines / multi-agent
  orchestration frameworks that also integrate symbolic tools, limiting external comparability.

## Methodology

- **[BOTH]** *(compute)* **Quantization confound.** AWQ-INT4 (large models) vs 16-bit (small
  models) is a confound for cross-model / tool-calling comparisons; not fully decoupled. Run a
  16-bit 35B on key cells. *(Scholars: Models and Serving, para 1, line 4 · Stanford: W-tech-2, Q9.)*
  → see theme [#2](#top-recurring-themes).
- **[BOTH]** *(compute)* **Prompt-clause confound.** The "thin per-task policy stubs" differ by
  more than tool presence (policy + output-format clause). Provide an ablation holding the clause
  constant, or estimate its contribution. *(Scholars: Three-Arm Design, para 4, line 2 · Stanford: W-tech-3, Q2.)*
  → theme [#3](#top-recurring-themes).
- **[BOTH]** *(release/writing)* **Exact prompts not in the paper.** The system-prompt text is
  central to a prompt-sensitivity paper but not shown — include it (appendix) for scrutiny /
  replication. *(Scholars: Three-Arm Design, para 4, line 2 · Stanford: Q10.)*
- **[Stanford]** *(compute)* **Steering-sentence not ablated.** Test multiple phrasings +
  distractors to show how sensitive propensity is to wording. *(W-clarity-2, Q1.)* → theme [#4](#top-recurring-themes).
- **[Stanford]** *(analysis)* **Clustered/mixed-effects inference.** Prefer instance+paraphrase
  random-effects logistic models over Wilson + post-hoc inflation. *(W-method-2, Q5.)* → theme [#5](#top-recurring-themes).
- **[Stanford]** *(compute)* **Temperature-0 only.** No sensitivity to sampling variance or to
  minor prompt variants beyond the single steering sentence. *(W-method-1.)*
- **[Scholars]** *(writing)* The 5:1 positive:negative ratio for domain validation is
  acknowledged to widen intervals but not statistically justified; note it can bias the
  posterior toward "valid". *(Tasks/Oracle/Fixtures, para 2, line 10.)*

## Results

- **[BOTH]** *(writing/analysis)* **Pooled vs balanced accuracy feels uneven** on
  `validate_domain` — show them side by side in the Results text, not only the appendix, and
  use one metric for significance. *(Scholars: Two Validation Tasks, para 1, line 6 · Stanford: W-clarity-1.)*
  → theme [#6](#top-recurring-themes).
- **[Scholars]** *(writing)* The 0% `simulate` rate is asserted "not a grading artifact" without
  detailing the canonical normal form, so readers can't judge whether grading was overly pedantic
  about whitespace/formatting. Add a concrete normalization example. *(Para 4, line 4.)*
- **[Scholars]** *(writing/analysis)* The "silence-not-error" mechanism is identified but *why*
  models favor prose over tools is left as speculation — offer a deeper hypothesis. *(When Availability Backfires, para 2, line 3.)*
- **[Stanford]** *(analysis)* How stable is P(correct|call) across domains and longer/rarer
  cases (e.g. complex numeric effects)? Any domain classes that erode accuracy-when-called?
  *(Q4.)* (Note: the rewrite already flags 9B `simulate` P(c|call) ≈ 81% as an exception.)

## What the Tool Costs

- **[Scholars]** *(writing)* Token-only cost ignores **dollars and latency**, feeling incomplete
  for practitioners. *(Para 1, line 6.)* (Draft already states wall-clock latency is unrecoverable
  from a batched server; consider adding a $-estimate and saying so explicitly.)
- **[Scholars]** *(analysis)* Cost-of-pass is global, not broken down by **classical vs numeric**
  domain complexity (numeric tool outputs may be far larger). *(Para 2, line 8.)*
- **[Scholars]** *(writing)* Doesn't account for **server-side prompt caching** reducing re-fed
  schema cost — reads as worst-case. *(Para 2, line 15.)* (Draft *does* mention ~90% prefix
  caching; make that more prominent / quantify its cost effect.)

## Robustness (reasoning mode and contamination)

- **[BOTH]** *(compute)* **Cap-raised `think=on` rerun** not attempted — the true reasoning-mode
  capability stays partly masked by the shared budget. *(Scholars: Robustness, para 1, line 10 · Stanford: W-tech-1, Q3.)*
  → theme [#1](#top-recurring-themes).
- **[BOTH]** *(compute)* **Structural memorization** not tested — symbol renaming may miss a model
  recognizing Blocksworld *logic*. Probe by permuting action arities / type indirection. *(Scholars: Robustness, para 2, line 5 · Stanford: Q7.)*
  → theme [#8](#top-recurring-themes).
- **[Scholars]** *(analysis)* The "renamed prompts ran ~5% longer → more truncation" note means
  the anonymized arm is slightly under-powered (a length-based systematic bias, not knowledge).
  *(Para 2, line 12.)* (Draft already explains this as the budget confound; consider making the
  length-matched control explicit.)

## Discussion

- **[BOTH]** *(scope/writing)* **Over-broad generalization.** Findings extended to "tool-augmented
  LLMs more broadly" despite testing only deterministic PDDL tools; probabilistic tools (web
  search, calculators) have different error profiles and "delegation" logic may not transfer.
  *(Scholars: Discussion, para 1, line 12 · cf. Stanford W-related-2.)* (The rewrite already
  softened the verb to "natural hypotheses … can suggest but not establish" — verify the framing
  satisfies this and don't over-claim elsewhere.)
- **[Scholars]** *(writing)* "Delegation" is framed as a prompting issue, ignoring fine-tuning /
  architectural routes to internalize invocation propensity. *(Para 2, line 6.)*
- **[BOTH]** *(scope)* No discussion of how **multi-turn / iterative self-correction** would alter
  P(call). *(Scholars: Discussion, para 2, line 15 · Stanford Q8.)* → theme [#7](#top-recurring-themes).

## Limitations

- **[Scholars]** *(writing)* Section is brief; lacks self-critique of whether the **20 domains**
  are representative of PDDL complexity. *(Para 1, line 4.)*
- **[Scholars]** *(compute/writing)* The lack of reasoning traces is noted but not mitigated by
  using a trace-providing model on key cells — tool-calling failures stay a black box. *(Para 1, line 15.)*
- **[Scholars]** *(analysis)* The 5:1 imbalance is mentioned but its effect on imbalance-robust
  metrics (F1) is not addressed. *(Para 1, line 22.)*
- **[Stanford]** *(writing)* Quantization + prompt-difference confounds are acknowledged here —
  reviewers credit this, but still want the actual controls (themes [#2](#top-recurring-themes), [#3](#top-recurring-themes)).

## Future Work

- **[Scholars]** *(writing)* "Agentic regimes" suggestion is vague — give a concrete multi-tool
  selection framework / actionable hypotheses. *(Para 1, line 5.)*
- **[BOTH]** *(compute)* The **cap-raised rerun** is deferred to future work rather than done —
  reviewers note it is a *fixable* validity issue. *(Scholars: Future Work, para 1, line 8 · Stanford Q3.)*
  → theme [#1](#top-recurring-themes).
- **[Scholars]** *(scope)* No mention of "model-modulo" ensembles (different models for
  formalization vs checking). *(Para 1, line 12.)*
- **[Stanford]** *(compute)* **Frontier/closed models** out of scope — does propensity persist at
  the frontier? *(W-related-2.)* (Planned no-tools Sonnet probe partially addresses; a small
  with-tools frontier cell would address it directly.) → theme [#9](#top-recurring-themes).

## Conclusion

- **[Scholars]** *(writing)* Repeats the "67 pp drop" without clarifying it is **model-dependent**,
  risking over-sensationalizing the harm for scanners. *(Para 1, line 8.)* (The rewrite added a
  "for one of three models" qualifier in the abstract/conclusion — verify it reads clearly here.)
- **[Scholars]** *(writing)* The practical rule lacks a concrete heuristic for **minimum effective
  steering** across model sizes. *(Para 1, line 12.)*
- **[Scholars]** *(writing)* Omits a summary of the **contamination-control** finding, a missed
  chance to reinforce robustness against the memorization critique. *(Para 1, line 14.)*

## Technical Appendix

- **[Scholars]** *(writing)* The invocation decomposition table (Table 4) is dense; add a guiding
  narrative so the key P(call) vs P(correct) insight isn't buried in the grid. *(Table 4, para 1, line 2.)*
- **[Scholars]** *(writing)* "P(c|call)=0 where no-call classes exist" is counter-intuitive —
  clarify in the table legend. *(Para 2, line 5.)*
- **[BOTH]** *(release)* Reproducibility-checklist items marked "no/partial" (esp. source code)
  signal the work isn't yet fully replicable. *(Scholars: Repro Checklist, sec 4.3 · Stanford Q10.)*
  → theme [#10](#top-recurring-themes). (Decision on record: release at publication, not submission.)

---

## Stanford questions for authors

Verbatim from `stanfordreview_res.pdf` (mapped to themes above):

1. Sensitivity of propensity to the **exact steering wording** (similar/dissimilar phrasings, distractors)? → [#4](#top-recurring-themes)
2. Ablation **holding the policy/format clause constant** to isolate tool presence? → [#3](#top-recurring-themes)
3. Targeted **higher-cap `think=on`** experiment on a subset to confirm the robust floor? → [#1](#top-recurring-themes)
4. Stability of **P(correct|call)** across domains and longer/rarer failure cases? → [Results](#results)
5. Would **clustered/mixed-effects** models change significance vs Wilson/MOVER? → [#5](#top-recurring-themes)
6. A **"multiple relevant tools present"** setup to measure tool selection under ambiguity? → [#7](#top-recurring-themes)
7. **Structural obfuscation** (permute arities, type indirection) for deeper contamination probing? → [#8](#top-recurring-themes)
8. Portability to **agentic multi-call** settings (iterative refinement, re-planning)? → [#7](#top-recurring-themes)
9. Did **quantization** influence tool-calling (logit-lens, or a 16-bit 35B on key cells)? → [#2](#top-recurring-themes)
10. Will you **release** the harness, fixtures, anonymization scripts, prompts, and MCP schemas? → [#10](#top-recurring-themes)

## Language and grammar (ScholarsReview)

Quick copy-edits (verbatim):

1. Intro bullet 4: `theverdictpatternreproducesunder` (missing spaces). *(Likely a PDF-extraction artifact; check the source.)*
2. Models and Serving: inconsistent Oxford-comma usage in the model list.
3. Table 1 caption: missing period at end.
4. Page 3, col 2: `accuracy-when-calling` vs `tool-calling` — inconsistent compound-adjective hyphenation.
5. Page 7: mixed use of `÷` symbol and verbal descriptions for cost-of-pass.
6. Discussion: inconsistent "the" before model numbers ("the 35B").
7. Results, para 4: "one steering sentence repairs it." — flagged as overly conversational.
8. Page 2, col 2: `Model Context Protocol (MCP) (Anthropic 2024)` — awkward double parentheticals.
9. Intro para 2: "which is what this paper sets out to do." — ends with a preposition.
10. Figure 4: caption says "log x" but axis scaling looks inconsistent — verify the tick rendering.

## Scores, strengths, and recommendations

**ScholarsReview section scores** (overall **8.36/10**): Introduction 9 · Background 8 ·
Methodology **10** · Results 9 · What the Tool Costs 8 · Robustness 9 · Discussion 8 ·
Limitations 7 · Future Work 7 · Conclusion 9 · Technical Appendix 8.

**Both reviews — recurring praise** (do not regress these when revising):

- Three-arm design cleanly disentangles availability from steering.
- The `P(call) × P(correct|call)` decomposition / invocation-propensity finding is the
  standout, actionable contribution.
- Signed-significance rule correctly separates *help* from *harm*.
- Strict end-to-end oracle grading + failure-type decomposition.
- Anonymized-domain contamination control, convincingly null under `think=off`.
- Cost-of-pass framing ("tools pay where the baseline is floored").
- Honest, transparent Limitations (decode budget, quantization, prompt differences).

**Recommendations:** ScholarsReview — *accept* ("a much-needed empirical foundation for the
LLM-Modulo framework"). Stanford Agentic Reviewer — *accept* ("a valuable contribution suitable
for AAAI").
