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
>

## 2. Title candidates

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

> ANSWER (A / B / C / combination):
>

## 3. Abstract candidate

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
> Applying it to five PDDL tasks over seven models, the failure localizes to three
> stages. The model needs the tool: unaided plan generation sits at 8 to 11
> percent, and the tool lifts it by 66 to 73 points at both open-weight and
> frontier tiers. The model must choose to call it: mere availability can hurt,
> costing one model 67 points on plan validation because it answers in prose
> instead of calling, and one sentence of steering moves invocation from 21 to 94
> percent. The answer must carry the result: this is where the guarantee is lost,
> and it is lost in proportion to how much there is to say. We recommend reporting
> the delivered answer as the primary number and relaying tool output as
> structured data rather than asking a model to restate it. The protocol is
> exercised over 273,600 trials across two corpora.

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
>

## 5. Before any of this reaches the tex

Every number in §3 traces to a locked deck value or the memo's MAY-USE list, but
none has been through `/verify-claims` in this session. That pass is owed on: the
8-11 percent unaided solve floor, the 66-73 point solve lift at both tiers, the
0 / +5 / >=33 point delivery gradient, the -67 point availability harm, and the
21-to-94 percent steering move. The scale figure in §4 is verified.
