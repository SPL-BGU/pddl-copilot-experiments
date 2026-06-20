Here's the review formatted as markdown:

---

# Review: *Availability Is Not Enough: When Symbolic Tools Help—and Hurt—LLMs on Planning Tasks*

**Venue:** NeurIPS
**Submitted:** June 20, 2026

---

## Summary

This paper investigates when and how access to sound symbolic planning tools (PDDL planners/validators/simulator) helps or harms LLMs on planning-related tasks. Using a controlled three-arm setup (no-tools, tool-available, tool-steered) across five single-tool-use tasks, five open-weight models, two reasoning modes, and strict end-to-end grading against deterministic oracles, the authors show that tool utility is regime-dependent: tools are indispensable for solving and state-trajectory simulation, improve weak baselines on file-validation tasks, and can paradoxically hurt plan validation unless the model is explicitly steered to call the tool. A central finding is that performance is bottlenecked by invocation propensity, not capability or tool accuracy: once called, tools are >92% accurate, but whether the model calls them varies widely and is highly prompt- and mode-sensitive. The study also presents cost-of-pass token analyses, robustness to reasoning-mode confounds via "robust floors," and a contamination control via symbol anonymization.

---

## Strengths

### Technical Novelty and Innovation
- Separates tool availability from explicit steering in a clean three-arm design, revealing a meaningful and actionable invocation-propensity bottleneck.
- Introduces a signed-significance rule (CI disjointness with direction) to distinguish helpful from harmful effects, preventing misinterpretation of large but adverse changes as "benefits."
- Employs an oracle-based strict end-to-end grading with deterministic planners/validators, allowing exact measurement of success without relying on self-report or partial credit.
- Provides a clear decomposition of success into P(call) × P(correct|call), pinpointing that most variance arises from whether the tool is invoked rather than accuracy given invocation.

### Experimental Rigor and Validation
- Large-scale evaluation (4,560 trials per model-mode-arm cell) over five tasks, five models, and two reasoning modes with temperature-0 decoding for determinism.
- Confidence intervals for all proportions, explicit handling of non-independence (design-effect inflation and a targeted random-effects model), and robust floor statistics for cross-mode claims.
- An anonymized-domain contamination control showing negligible memorization effects on unaided baselines and a probe with a strong proprietary model (unaided) to substantiate capability boundaries.
- Transparent failure-mode breakdowns and token cost-of-pass analysis that clarifies where tools are cost-effective vs. a luxury.

### Clarity of Presentation
- Clear articulation of research questions, setup, and metrics; helpful figures/tables that align with the claims.
- Careful discussion of confounds (reasoning budget, class imbalance for validate_domain) and their mitigation.
- Well-structured limitations and future work that contextualize the scope and constraints.

### Significance of Contributions
- Actionable insight for practitioners: availability alone is not enough—steering (even a single imperative sentence) often determines realized benefit.
- Evidence that certain planning tasks (solve, simulate) exceed current LLM unaided capabilities, reinforcing the LLM-modulo paradigm and emphasizing the importance of orchestration quality.
- A principled evaluation template (strict oracles, signed significance, invocation decomposition) that can be reused for broader tool-use studies.

---

## Weaknesses

### Technical Limitations or Concerns
- The availability contrast includes a slight prompt-policy difference in system prompts beyond tool presence; although acknowledged, this limits causal purity of that contrast.
- Larger models are evaluated in AWQ-INT4 while smaller ones are in 16-bit; cross-model comparisons of invocation propensity could be partially confounded by quantization.
- The domain coverage omits temporal/durative/conditional-effect constructs; conclusions may shift in richer PDDL fragments.

### Experimental Gaps or Methodological Issues
- Tool-use results are limited to open-weight models; only the unaided baseline is reported for a proprietary model, leaving the invocation-propensity phenomenon untested on frontier models with aggressive tool-use post-training.
- Temperature 0 ensures determinism but leaves open questions about robustness to stochastic decoding; some claims might be sensitive to decoding strategies used in practice.
- Strict trajectory equality for simulate is well-justified and canonicalized, but no ablation on alternative output schemas or structured decoding constraints to test whether formatting requirements drive part of the unaided failure.

### Clarity or Presentation Issues
- While generally clear, the paper is dense; some readers may desire a more concise executive summary of the major effect sizes, especially for practitioners.
- The cost-of-pass analysis could benefit from a short explicit note on real-world system optimizations (e.g., tool-output truncation or selective logging) that could reduce input-token overheads in production.

### Missing Related Work or Comparisons
- Could further situate findings relative to agentic prompting frameworks (e.g., ReAct-style deliberate verification/routing) and program-of-thought integrations that may influence invocation propensity.
- No head-to-head with recent planning-agent baselines that incorporate multi-tool orchestration or iterative self-correction, which could partly mitigate under-calling.

---

## Detailed Comments

### Technical Soundness
The experimental design is strong: oracle-grounded grading, deterministic tools, and strict end-to-end metrics eliminate many common ambiguities. The signed-significance rule is a thoughtful safeguard against misinterpreted directionality. The invocation decomposition is convincing: high P(correct|call) across tasks explains the observed regime dependence and the "silent failure" on validate_plan. The treatment of paraphrase clustering and design-effect inflation is careful; the targeted mixed-effects analysis for the largest effect adds credibility. The reasoning-mode budget confound is candidly addressed; using robust floors and avoiding raw cross-mode comparisons is appropriate.

### Experimental Evaluation
Coverage across five tasks provides a rich picture: two sole-source tasks (solve, simulate), two with headroom (validate_domain, validate_problem), and one mixed (validate_plan). The anonymized-domain contamination control is an excellent addition; the near-null drift and the direction of the largest small drifts (favoring anonymized) credibly rule out memorization in unaided baselines. The token cost-of-pass metric appropriately reflects operational tradeoffs: tools are cost-effective when baselines are floored, and a luxury otherwise.

### Comparison with Related Work
- Relative to Valmeekam et al. (PlanBench) and Kambhampati et al., this work quantifies the gains from integrating sound tools, echoing the LLM-modulo vision with direct empirical validation.
- Compared with LLMs-as-formalizers (e.g., LLM+P), the focus is on tool use across multiple PDDL tasks with strict oracle grading, complementing prior literature and filling a gap in end-to-end tool utility measurement.
- In contrast to tool-use competency benchmarks (e.g., BFCL), the paper evaluates real outcome utility with deterministic correctness oracles, connecting tool selection to task end goals.

### Broader Impact
- The key practical lesson—**steering matters**—has immediate implications for agent design: systems must ensure high invocation propensity (via prompting, fine-tuning, routing, or architectural support) to realize the benefit of tooling.
- The evidence that simulate and solve remain out of reach unaided, even for a strong proprietary model, underscores the continued importance of model-based tools in safety- and reliability-critical settings.
- The possibility that naive availability can degrade performance on already-competent tasks is an important caution for practitioners building tool-augmented LLM products.

---

## Questions for Authors

1. Can you provide an ablation where the availability contrast uses exactly matched system prompts (minus tool presence) to isolate the effect of availability without any policy-language differences?
2. Did you experiment with minimal "implicit" steering (e.g., phrasing the user instruction more imperatively without a separate directive sentence) to see if invocation can be nudged without an explicit "Use tool X" line?
3. For simulate, did you try alternative structured outputs (e.g., per-step deltas or compressed state diffs) under schema constraints to assess whether unaided failures are due to cumulative JSON verbosity rather than state-tracking per se?
4. Could you share P(call) under higher sampling temperatures or with nucleus sampling to test whether stochastic decoding increases or decreases invocation propensity?
5. How sensitive are the results to the precise tool descriptions and argument schemas exposed via MCP? For instance, does making the tool name or description more salient raise P(call) without explicit steering?
6. Do you have preliminary results on proprietary models with tool access enabled (not only unaided) to test whether post-training on function-calling diminishes the availability-vs-steering gap?
7. In cost-of-pass calculations, how would typical production-side optimizations (e.g., not re-feeding full tool outputs or summarizing them) change the cost-effectiveness picture on validation tasks?

---

## Overall Assessment

This is a careful, insightful, and practice-relevant measurement study of LLMs augmented with sound symbolic planning tools. Its main contributions—clean separation of availability vs. steering, strict oracle-based end-to-end grading, signed-significance testing, and the identification of invocation propensity as the dominant bottleneck—are both novel and actionable. The experiments are well-designed and thorough, with thoughtful handling of statistical and methodological confounds. Limitations are acknowledged but do not undermine the central empirical findings. Overall, the paper advances the state of knowledge on tool-augmented LLMs in planning contexts and offers a robust evaluation template.

**Recommendation: Accept**