Here's the review formatted as markdown:

---

# Review: *Availability Is Not Enough: When Symbolic Tools Help—and Hurt—LLMs on Planning Tasks*

**Venue:** AAAI
**Submitted:** June 20, 2026

---

## Summary

This paper studies when and how access to sound symbolic planning tools helps, or hurts, language models on planning tasks. Using five single-tool PDDL tasks and five open-weight models, the authors implement a three-arm design that separates mere tool availability from a one-sentence steering directive, and grade all answers strictly against deterministic solver/validator oracles with confidence intervals and signed significance. The key findings are regime-dependent utility, an "invocation propensity" bottleneck (P(call) × P(correct|call)), and a striking case where tool availability alone sharply degrades performance due to models reasoning in prose rather than calling the validator—an effect reversed by one steering sentence; a token cost-of-pass analysis and contamination controls round out the evaluation.

---

## Strengths

### Technical Novelty and Innovation
- A clean, tool-oracle setting for end-to-end grading across five PDDL tasks, avoiding self-reported correctness and yielding unambiguous success/failure.
- A three-arm design that explicitly decouples tool availability from a minimal steering nudge, with a signed-significance rule that distinguishes help from harm.
- The invocation propensity decomposition (P(call) × P(correct|call)) provides a clear, mechanistic account of where variance lies and why availability alone can regress performance.
- Rigorous contamination control via symbol anonymization and a budget-insensitive cross-mode analysis (robust floors) to address reasoning-mode confounds.

### Experimental Rigor and Validation
- Large-scale evaluation (4,560 graded trials per model–mode–arm cell) across classical and numeric domains with per-trial outcome typing and Wilson/MOVER intervals.
- Strict end-to-end grading against deterministic oracles, with a GLMM/GEE check validating one key result under paraphrase clustering.
- Thoughtful treatment of class imbalance (balanced accuracy for `validate_domain`), and thorough failure-mode breakdowns.
- Inclusion of a frontier proprietary model (no-tools arm) to corroborate sole-source floors and contamination null beyond the open models.

### Clarity of Presentation
- Clear articulation of research questions (RQ1–RQ6), verdict criteria, and interpretation, including signed significance and conservative inference choices.
- Transparent limitations (decode budget confound under `think=on`; prompt differences between arms; quantization caveat for largest models) and rationale for design choices.
- Informative figures/tables that trace success, failure types, and tool-use rates; explicit prompts and steering directive are provided.

### Significance of Contributions
- Establishes that symbolic tools are not uniformly beneficial; their value is strongly regime-dependent and gated by invocation propensity—a key insight for agent/tool pipeline design.
- Demonstrates indispensable tool utility for tasks beyond LLM unaided reach (`solve`, `simulate`), while revealing risks of naïve availability on tasks LLMs can already do.
- Offers practical guidance (explicitly nudge tool use; expect higher token cost; benefits rise with plan length), with broader implications for LLM-modulo frameworks.

---

## Weaknesses

### Technical Limitations or Concerns
- The availability-vs-no-tools arm comparison also differs in a short system prompt clause, potentially confounding availability with subtle instruction differences (acknowledged but still a limitation).
- Largest models are AWQ-INT4 while smaller ones are 16-bit; cross-model differences in spontaneous tool adoption may partially reflect quantization effects.
- Reasoning mode (`think=on`) remains confounded by a shared decode budget; while the robust-floor approach helps, a fully decoupled budget design would be stronger.

### Experimental Gaps or Methodological Issues
- Closed-source models are not evaluated in the tool-using arms; thus, the central availability/steering findings may not transfer to models with aggressive tool-use post-training.
- The study excludes temporal/durative/conditional-effect PDDL features and multi-tool orchestration, potentially limiting generality.
- Exact-match trajectory grading for `simulate`, while principled, provides no partial credit, which may understate near-correct unassisted reasoning or intermediate utility.
- No multiple testing correction is applied; although effect sizes are large and the authors use a conservative signed-CI rule, the breadth of comparisons invites FWER concerns.

### Clarity or Presentation Issues
- Some methodological details (hardware/software stack, tool-call iteration statistics, and tool latency) could be expanded to aid reproducibility and deployment realism.
- The token cost analysis is sound but would benefit from a latency complement; token-level caching caveats are discussed but empirical timing would be informative.

### Missing Related Work or Comparisons
- Head-to-heads with PlanBench-style evaluations, alternative PDDL toolchains, or LLM-as-formalizer pipelines are deferred; some readers may expect direct comparisons.
- Limited discussion of policy-tuning/RLAIF/RLHF influences on invocation propensity, despite being central to the observed behavioral variance.

---

## Detailed Comments

**Technical Soundness**
The oracle-based, strict grading removes subjective scoring and self-report biases. The decomposition of success into P(call) × P(correct|call) is well justified by the determinism and correctness of the tools, and it localizes the main driver of variance to invocation propensity. Statistical treatment is careful: Wilson intervals for proportions, MOVER intervals for gap differences, and explicit recognition of paraphrase clustering with either design-effect inflation or GLMM/GEE modeling for key contrasts. The signed-significance rule appropriately guards against misinterpreting harmful effects as mere "effects."

**Experimental Evaluation**
The five-task coverage across classical and numeric domains provides a well-rounded picture of single-tool utility: two sole-source (`solve`, `simulate`), two headroom tasks (`validate_domain`, `validate_problem`), and one mixed case (`validate_plan`). The plan-length analysis showing increasing benefit for harder instances is particularly compelling; the object-count null is also informative. The token cost-of-pass analysis is a practical contribution: the tool is cost-effective when the unaided baseline is floored and a luxury when the baseline is strong.

**Comparison with Related Work**
- Relative to PlanBench (Valmeekam et al.), this paper focuses on end-to-end utility of calling sound tools rather than raw LLM planning ability, deepening the LLM-modulo perspective advocated by Kambhampati et al.
- Compared to LLM-as-formalizer lines (e.g., LLM+P; Tantakoun et al.; Huang and Zhang), this study evaluates multi-faceted PDDL tool use rather than only translation quality, offering a complementary lens.
- Relative to tool-use benchmarks (BFCL), the work highlights invocation propensity as the key real-world bottleneck.

**Broader Impact**
The central lesson—that availability is not enough and explicit steering is often necessary—has immediate implications for agent system design, prompt engineering, and tool-use post-training. The identified volatility of invocation propensity suggests research opportunities in routing, fine-tuning for tool seeking, and protocol design that prevents "prose fallback."

---

## Questions for Authors

1. Can you report how often multiple tool calls (beyond the first) were used and whether limiting to a single call changes outcomes or costs?
2. Did you attempt a budget-decoupled think mode (separate caps for reasoning vs. final answer)? If so, how did it affect truncation and format adherence?
3. How sensitive are the availability and steering gaps to small variations in the steering sentence (imperative vs. suggestive phrasing, different placement)?
4. Do you have ablations on schema verbosity (e.g., shorter function descriptions) and their effect on invocation propensity and token cost?
5. For `simulate`, would a graded or partial-credit metric (e.g., per-step accuracy) materially change the conclusions about unaided capability vs. tool utility?
6. Have you tested the with-tools arms on any proprietary models with strong tool-use post-training to see if the availability gap persists or vanishes?
7. Can you quantify the effect of AWQ-INT4 quantization on invocation propensity (e.g., by re-running one large model in higher precision) to separate size vs. quantization?
8. Beyond prompting, have you explored light fine-tuning or constrained decoding strategies to increase P(call) without harming P(correct|call)?

---

## Overall Assessment

This is a careful, insightful empirical study that advances our understanding of when symbolic tools help LLMs in planning contexts. The methodology is strong—strict oracle-based grading, a three-arm design that disentangles availability from steering, robust statistics, contamination controls, and practical token-cost analysis. The main results are both novel and practically meaningful: two tasks are tool-sole-source; two see clear gains over weak baselines; and one reveals a counterintuitive harm from mere tool availability that disappears with a minimal nudge. The invocation propensity framing is an especially valuable contribution, clarifying that the dominant variance lies in whether models call the tool, not in tool accuracy. While the scope is limited to single-tool, single-call PDDL tasks and some confounds remain, the authors acknowledge these clearly and propose sensible future directions. Overall, this work offers both rigorous evidence and actionable guidance for building reliable LLM+tool systems and is **well-suited for publication at AAAI**.