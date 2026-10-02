# Consistency read, group E — reworded sentences for approval (2026-10-02)

*Companion to `consistency_read_findings.md`. Groups A–D are applied (uncommitted) on
branch `paper/consistency-read`, stacked on PR #110. Nothing in this file is in the tex
yet. Mark each row yes / no / reword in the ANSWER slot at the end, or write "all".
One E3 site (the old "budget, not the grader" closer) is gone already: PR #110 rewrote
that sentence.*

| # | Original | Proposed |
|---|---|---|
| E1 | (Delivery Gap) "…without the tool. Not calling is not the same as not answering, a point the availability analysis below has to respect." | "…without the tool, a case the availability analysis below has to respect." (the sentence stays once, in the availability subsection) |
| E2a | (Discussion, end) "The practical rule that follows is simple: a planner or validator behind a tool interface helps most when…" | "In practice, a planner or validator behind a tool interface helps most when…" |
| E2b | (Conclusion) "The rule for practitioners follows: a planner or validator behind a tool interface helps an LLM most when…" | "For practitioners, a planner or validator behind a tool interface helps an LLM most when…" (the executive summary's "Two rules follow:" stays as the single statement) |
| E3a | "The unaided zero, meanwhile, is a property of the deployed budget and format requirements, not an absent capability." | "The unaided zero, meanwhile, reflects the deployed budget and format requirements, and the control below shows that the capability is present." |
| E3b | "On this evidence the gap is a property of answer length interacting with the output budget, not of model strength." | "On this evidence the gap depends on answer length interacting with the output budget and is the same at both capability tiers." |
| E3c | "the open-weight roster's apparent zero reflects those pressures (68% unparseable, 29% truncated; Figure…), not a model-general incapacity." | "the open-weight roster's apparent zero reflects those pressures (68% unparseable, 29% truncated; Figure…) and does not carry over to the stronger model." |
| E3d | "This is a property of the stored corpus, not of the generation apparatus: point identification is feasible by re-running…" | "This limitation comes from the stored corpus alone: point identification is feasible by re-running…" |
| E4a | "The tool does not *refine* a competent baseline here; it *rescues* a task the models cannot do reliably." | "Here the tool *rescues* a task the models cannot do reliably." |
| E4b | "what limits tool-augmented performance here is not whether the model *can* use the tool but whether it *does*, and the less obvious point is that whether it does is a large, unstable…" | "what limits tool-augmented performance here is whether the model actually calls the tool, and the less obvious point is that this is a large, unstable…" |
| E4c | "so what the simulator lacks is not accuracy but a delivery path." | "so the simulator is accurate and what it lacks is a delivery path." |
| E5 | "The mechanism layer says why the open-roster bounds sit so far under their tool-verified rates of 63–99%: invocation." | "The mechanism layer points to invocation as the reason the open-roster bounds sit so far under their tool-verified rates of 63–99%." |
| E6 | "A correct-by-construction tool turns ``can the model plan?'' into ``will the model delegate?'', and the second question is the one that varies widely." | "With a correct-by-construction tool, the open question shifts from whether the model can plan to whether it delegates, and delegation is what varies widely." |
| E7a | "The honest comparison in the matching mode is therefore…" | "The comparison in the matching mode is therefore…" |
| E7b | "what shrinks is the unaided floor, to its honest size." | "what shrinks is the unaided floor." |
| E8a | "At the mechanism layer the picture is dramatic and exact." | "At the mechanism layer the picture is exact." |
| E8b | "The pattern is sharp and identical at both capability tiers." | "The pattern is identical at both capability tiers." |
| E8c | "This sign-awareness carries real weight:" | "This sign-awareness matters:" |
| E8d | "which is a real caution for any system" | "which is a caution for any system" |
| E8e | "by huge, model-specific amounts" | "by large, model-specific amounts" |
| E8f | "the delivered lift is enormous at both tiers" | "the delivered lift is large at both tiers" |
| E9 | "and dies in delivery" | "and is lost in delivery" |
| E10a | "The question is less settled than it may appear. One line of work…" | "The question is not settled. One line of work…" |
| E10b | "This paper sets out to do exactly that, grading…" | "This paper does so, grading…" |
| E10c | "That is the gap we close. This paper contributes…" | delete the first sentence |
| E10d | "The two grading layers let us measure something the tool-use literature usually cannot see: how much of what the tool computes actually reaches the model's answer." | "The two grading layers measure how much of what the tool computes reaches the model's answer, a quantity the tool-use literature usually cannot observe." |
| E10e | "Two things stand out. A small current model scores…" | delete the first sentence |
| E11a | "the reported value shape follows the storage, not the estimand." | "the reported value shape is set by the storage, while the estimand is the same throughout." |
| E11b | "(it is a replication under a different apparatus, not a repair)" | "(it replicates under a different apparatus and does not repair the canonical cells)" |
| E11c | "Plan length is a difficulty axis the tool's advantage tracks; object count is not." | "The tool's advantage tracks plan length and is flat in object count." |
| E11d | "Availability alone is not enough. The prompting fix is small:" | "Availability alone does not secure this, and the prompting fix is small:" |

**Caution on three rows.** E3b ("the same at both capability tiers") and E8b
("identical at both capability tiers") restate the delivery-gap claim that the weakness
list (C5) says is over-stated, and E3a ("the capability is present") leans on a control
that covers Qwen only, thinking on. Suggested: hold E3a, E3b and E8b for the C5 / C6
rewrite and apply the rest.

> ANSWER (all / all except … / per-row notes):
>
