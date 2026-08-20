# D-J6 — term collision check + title/abstract candidates (2026-08-16)

Phase-0 items from `journal_decisions_memo.md` §8. **Draft for Omer's review
(~15-30 min).** Nothing here may enter the tex before a `/verify-claims` pass;
§4 flags one number that already failed a check.

## 1. Collision check: is "the delivery gap" available?

**Verdict: available as a coined term, with one near neighbour worth knowing.**
Searched tool-use and agent-eval venues, the ML-evaluation literature, and the
generic-metric space.

**No prior claim on the exact term.** "Delivery gap" is not an established metric
or named phenomenon in tool-use, agent-eval, or ML evaluation. Outside our field
it is a common business and healthcare phrase (service-delivery gap), which costs
it a little distinctiveness but creates no academic ambiguity.

**The one real neighbour.** *Mind the GAP: Text Safety Does Not Transfer to
Tool-Call Safety in LLM Agents* (arXiv:2602.16943, 2026) defines **GAP** as a
named metric for divergence between what an agent says in text and what it does
through tool calls. That is structurally our shape, one layer of the same
question, and its subtitle even shares our "does not transfer" construction. It
measures the opposite direction in a different domain: a model that refuses in
text while executing the harmful action anyway, in a safety setting. Ours is a
correct tool result that fails to reach the user's answer, in a competence
setting. The risk is a reader in agent-eval hearing "gap" plus "text versus tool
call" and filing us under that paper.

**Neighbours that share the suffix but not the meaning**, listed so we do not
trip over them in Related Work: "evaluation gap" (Hutchinson et al., FAccT 2022,
arXiv:2205.05256, an established term); "evaluative gap" (the tau-bench line,
automatic evaluation versus human judgement); "generalization gap"; "Sim2Real
gap" in user simulation for agentic tasks; "tool-use tax" (arXiv:2605.00136) and
"CoT-Tool gap", both adjacent cost-benefit framings.

**Recommendation: keep "the delivery gap".** It is unclaimed, and it is anchored
in our own DELIVER stage rather than floating free, which is the property that
makes a coined term survive. Two cheap safeguards: define it at first use in the
abstract or intro, and if we ever cite Mind the GAP, distinguish the two in the
same sentence. If Omer wants more distance, the strongest alternatives are
**"delivery loss"** (keeps the stage anchor, drops the crowded suffix) and
**"the last-mile gap"** (instantly legible, more journalistic).

> ANSWER (keep "the delivery gap" / switch to "delivery loss" / switch to
> "last-mile gap" / other):
> **ANSWERED 2026-08-20 (Omer): OPTIONAL, and the term choice is deferred.**
> "Let's mark the delivery as optional and later we choose between a version
> where it's included and a version where it's not included. We need to decide
> on a non-confusing narrative. The delivery is not our main point in the paper."
>
> Consequence: the term question is no longer answerable on its own, because it
> only arises in the variant that keeps delivery. The live decision is now the
> narrative in section 2 below; the term follows from it. If delivery stays, the
> collision verdict above stands and "the delivery gap" is the recommendation.

## 2. Narrative decision first, then the title

> **REJECTED 2026-08-20 (Omer), all three earlier candidates.** *"The title is
> misleading. It's over-focused on the recent changes rather than the actual
> field and conclusions we present."* Kept at the bottom of this section for the
> record. The diagnosis is right and it generalises: A ("Need, Call, Deliver")
> and C ("Soundness Does Not Transfer to the Delivered Answer") both make
> DELIVER the thesis, and B ("Dual-Surface Grading") makes our measurement
> instrument the thesis. All three foreground work done in the last two months
> rather than the question the paper answers.

**What the paper actually concludes.** The tex abstract already states it, and it
does not mention delivery at all:

> *"The bottleneck throughout is invocation propensity, an unstable, model- and
> prompt-dependent behavior, separate from the model's capability or the tool's
> accuracy."*

That is the field-level result: sound planning tools are available to LLMs, the
benefit is strongly regime-dependent, and what gates it is whether the model
chooses to call, not whether the tool is correct or the model is capable.

### The two narratives

**N1 — Invocation-propensity spine (delivery out of the thesis).**
The paper asks when tool access helps an LLM planner and answers: it depends on
the regime, and the binding constraint is invocation. Two tasks cannot be done
without the tool; plan checking gets *worse* when the tool is merely available
(-67pp for one model) because the model reasons in prose instead of calling; one
steering sentence moves invocation 21% to 94%. Dual-surface grading appears in
Methods as how we measure honestly, and the delivery gap appears in Limitations
as a second place the guarantee can be lost. Neither is a headline.

**N2 — Two-failure spine (delivery in, subordinate).**
Same spine, plus a second, later failure: even once called, the tool's result may
not reach the answer. Delivery is a supporting act with its own section, not the
climax. Costs an extra concept in the abstract, and risks the reviewer reading
the paper as two loosely joined findings.

**Recommendation: N1.** It matches the tex we already have, it is one idea rather
than two, and it puts the paper in the tool-use literature rather than in the
grading-methodology literature. Delivery is stronger as a limitation that a
careful reader notices than as a co-headline it has to compete with.

> ANSWER (N1 / N2 / other — and if N2, say what delivery is subordinate to):
>

### Title candidates for N1

Each names the field (LLMs calling sound planning tools) and a conclusion, not an
instrument. All are scoped; none makes an unscoped composition-failure claim.

**D. The conclusion, stated.**
> **Invocation Is the Bottleneck: When Sound Planning Tools Help an LLM, and When
> They Do Not**

**E. The question, with the regime answer.**
> **Does Calling a Planner Help? Regime-Dependent Gains and an Availability
> Penalty in LLM PDDL Planning**

**F. The counterintuitive result, scoped.**
> **A Correct Tool the Model Will Not Call: Invocation Propensity as the Limit on
> Tool-Augmented LLM Planning**

**Worth reopening.** "Availability Is Not Enough" was retired because it "anchors
the CALL finding only and predates the DELIVER stage". If delivery leaves the
thesis, that rationale mostly dissolves: anchoring the CALL finding is now
exactly right. It is the most economical statement of the paper's result and it
should be back on the table under N1.

> ANSWER (D / E / F / un-retire "Availability Is Not Enough" / combination /
> other):
>

### Rejected 2026-08-20, kept for the record


Constraints applied: "Availability Is Not Enough" is retired (it anchors the CALL
finding only and predates the DELIVER stage); no unscoped universal
composition-failure declarative; scoped forms are allowed.

**A. Funnel mnemonic (recommended).**
> **Need, Call, Deliver: Where Sound Planning Tools Lose Their Guarantee**

Carries the structural triple into the title, so the paper's organising idea is
legible before the abstract. "Lose their guarantee" is scoped by construction: it
says the guarantee stops somewhere, not that composition fails in general.

**B. Protocol-first (HELM/HAL mold: instrument first, domain second).**
> **Dual-Surface Grading for Tool-Augmented Planning: What Tool-Verified Success
> Hides**

Leads with C1, which is the contribution most likely to outlive the specific
numbers. Weaker as a hook, stronger as a citation magnet for anyone building a
tool-use harness.

**C. Scoped declarative.**
> **Soundness Does Not Transfer to the Delivered Answer: LLMs Using PDDL Planning
> Tools**

The most direct statement of the thesis and the safest form of the
composition-failure claim. Costs us the funnel mnemonic, and it echoes the Mind
the GAP subtitle closely enough that I would only pick it if we are comfortable
being read alongside that paper.

## 3. Abstract candidate

> **PENDING the section-2 narrative answer.** The draft below implements N2 with
> delivery as the *climax* ("this is where the guarantee is lost"), which the
> 2026-08-20 decision demotes. Under N1 it needs rewriting around invocation
> propensity, not renumbering. The scale-figure fix from section 4 is applied
> here already, since it holds under either narrative.

Built on the memo's skeleton: field claim and prescribed remedy, one honest gap
number in gradient form, C1 named, three one-number stage results, constructive
recommendation, scale as protocol validation. Paired with title A.

> Symbolic planners and validators are correct by construction, and the standard
> prescription for unreliable LLM planning is to place one behind a tool
> interface. Whether that guarantee reaches the user is rarely measured, because
> tool-use evaluations typically score the tool's return value rather than the
> answer the model finally gives. We grade both surfaces on the same trials and
> find that they come apart as output grows: on short verdict tasks the two agree,
> on plan generation the delivered answer trails the tool result by about 5
> points, and on long state trajectories it trails by more than 33. We contribute
> a measurement protocol for this: grading both surfaces, an anonymized-domain
> twin as a contamination control, a budget-decoupling control that separates
> reasoning from answer length, denominator discipline that scores an empty answer
> as incorrect, and pre-registered parity tests between apparatus versions.
> Applying it to five PDDL tasks over five open-weight models, with a two-model
> frontier arm as a capability check, the failure localizes to three
> stages. The model needs the tool: unaided plan generation sits at 8 to 11
> percent, and the tool lifts it by 66 to 73 points at both open-weight and
> frontier tiers. The model must choose to call it: mere availability can hurt,
> costing one model 67 points on plan validation because it answers in prose
> instead of calling, and one sentence of steering moves invocation from 21 to 94
> percent. The answer must carry the result: this is where the guarantee is lost,
> and it is lost in proportion to how much there is to say. We recommend reporting
> the delivered answer as the primary number and relaying tool output as
> structured data rather than asking a model to restate it. The protocol is
> exercised over 273,600 open-weight trials across two corpora.

Notes on choices a reviewer might probe. The first number is one-sided by
construction (a gradient, not an interval), per the D-J1 constraint. No sentence
claims a task is impossible without the tool. The simulate floor is not cited as
sole-source anywhere. The delivery gradient is stated in points rather than as a
delivered-simulate figure, which keeps us clear of the bounds-only rule.

> ANSWER (approve / revise — mark the sentences you want changed):
>

## 4. One number in the memo does not reproduce: the "227k trials" scale claim

`journal_decisions_memo.md` uses **227k trials** three times (§5, §8, and the
proposal's limitations paragraph) as the headline scale, with no derivation
recorded anywhere. **It does not reproduce from disk**, so the abstract above
uses a counted figure instead.

Counted 2026-08-16, read-only, over the canonical corpora:

| corpus | analyzable rows | unique trial keys | infra failures |
|---|---|---|---|
| sweep5v2-live | 136,800 | 136,800 | 0 |
| sweep6-live (anonymized twin) | 136,800 | 136,800 | 0 |
| **two-corpus total** | **273,600** | 273,600 | 0 |
| iss024d-e2e-live (separate apparatus) | 45,600 | 45,600 | 0 |
| decoupled-rollup | 36,480 | **18,240** | 0 |

136,800 per corpus is exactly 5 models x 2 reasoning modes x 3 arms x 4,560, which
matches the proposal's own inventory line (4,560 no-tools per cell, 91,200
with-tools). The decoupled tree stores the A/B pair, so its 36,480 rows are 18,240
distinct decoupled trials beside their baseline copies; counting it whole would
double-count.

**273,600 is the defensible two-corpus number** and it is what the draft abstract
uses. Whether the frontier arm (6,080 Haiku plus 10,640 Sonnet) and the two
control corpora are folded into a single headline figure is a presentation
choice, but whichever total we print has to be derivable in one line, because a
reviewer with the released data will check it.

> ANSWER (quote 273,600 two-corpus / quote a larger total that includes the
> control and frontier corpora, specify which / other):
> **ANSWERED 2026-08-20 (Omer): quote 273,600 and say five open-weight models.**
> The abstract names the five open-weight models with the 273,600 two-corpus
> total, so the derivation is one line a reviewer can check:
> 5 models x 2 reasoning modes x 3 arms x 4,560 x 2 corpora. The frontier arm
> (6,080 Haiku + 10,640 Sonnet) is described in its own sentence and is never
> folded into that figure. "227k" does not appear anywhere.
> Applied to the section-3 draft; correction markers added at the head of
> `journal_decisions_memo.md` and `journal_narrative_proposal.md`, which are
> where the "227k-trial / 7-model" pairing entered the drafting chain.

## 5. Before any of this reaches the tex

Every number in §3 traces to a locked deck value or the memo's MAY-USE list, but
none has been through `/verify-claims` in this session. That pass is owed on: the
8-11 percent unaided solve floor, the 66-73 point solve lift at both tiers, the
0 / +5 / >=33 point delivery gradient, the -67 point availability harm, and the
21-to-94 percent steering move. The scale figure in §4 is verified.
