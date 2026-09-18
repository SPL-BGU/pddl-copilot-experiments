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

Quoted verbatim from the current tex. The *finding* is the spine; the *word*
"propensity" is retired (see the terminology note below), so this sentence is one
of the 15 that get rewritten.

That is the field-level result: sound planning tools are available to LLMs, the
benefit is strongly regime-dependent, and what gates it is whether the model
chooses to call, not whether the tool is correct or the model is capable.

### The two narratives

**N1 — Invocation spine (delivery out of the thesis).**
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
> **ANSWERED 2026-08-20 (Omer): N1 — the invocation spine.** The paper asks when
> tool access helps an LLM planner and answers that it depends on the regime, and
> that what gates it is whether the model calls. Delivery moves to Limitations.
> Dual-surface grading stays in Methods as how we measure honestly.
>
> Knock-on: the section-3 abstract is redrafted on this spine below. Dropping the
> delivery gradient from the abstract also drops one of the five numbers owed a
> `/verify-claims` pass (section 5), since the 0 / +5 / >=33 point gradient is no
> longer quoted there.

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
> **A Correct Tool the Model Will Not Call: How Often LLMs Invoke a Sound Planner,
> and What It Costs Them**

### Terminology: retire "propensity" (Omer, 2026-08-20)

*"'Propensity' is a complex word. I don't like it."* It is not a stray word:
`paper/main.tex` uses it **15 times**, so this is a paper-wide rename.

The term has to do two jobs in those slots. It must name a *behavior* (whether
the model calls) as distinct from *capability* (whether it can), and it must
survive in noun positions such as "default propensity", "raise propensity", and
"the propensity result".

**Recommendation: "invocation rate".** It is plain, and it maps exactly onto the
quantity we already measure, the `tool_selected` share, so the simpler word is
also the more concrete one. Where a sentence needs the dispositional sense, spell
it out instead of nominalising: "whether the model chooses to call the tool".

| current | plain replacement |
|---|---|
| "the bottleneck is invocation *propensity*" | "the bottleneck is the invocation rate: whether the model calls the tool at all" |
| "this reflects tool-call *propensity*, not capability" | "this reflects how often the model calls the tool, not whether it can" |
| "the wide cross-model spread in *default propensity*" | "the wide cross-model spread in default invocation rate" |
| "raising invocation *propensity* by fine-tuning" | "raising the invocation rate by fine-tuning" |

Runners-up: **"call rate"** (shorter, slightly informal for a thesis term) and
**"willingness to call"** (most human, mildly anthropomorphic, and awkward in
"the willingness result").

The 15 tex edits are NOT in this branch. Paper edits belong on `paper/aaai27`
(CLAUDE.md), so this is a queued job, not a done one.

> ANSWER ("invocation rate" / "call rate" / "willingness to call" / other — and
> confirm I should make the 15 tex edits on `paper/aaai27`):
> **ANSWERED 2026-08-20 (Omer): "invocation rate".** Applied to the development
> docs and to the section-3 redraft. The 15 `paper/main.tex` edits are still
> QUEUED, not done: the branch confirmation half of this slot was not answered,
> and paper edits belong on `paper/aaai27` behind the Overleaf pull-then-push
> protocol (CLAUDE.md). One word of go-ahead releases them.

**Worth reopening.** "Availability Is Not Enough" was retired because it "anchors
the CALL finding only and predates the DELIVER stage". If delivery leaves the
thesis, that rationale mostly dissolves: anchoring the CALL finding is now
exactly right. It is the most economical statement of the paper's result and it
should be back on the table under N1.

> ANSWER (D / E / F / un-retire "Availability Is Not Enough" / combination /
> other):
> **ANSWERED 2026-08-20 (Omer): D.**
>
> > **Invocation Is the Bottleneck: When Sound Planning Tools Help an LLM, and
> > When They Do Not**
>
> States the conclusion and scopes it in the same breath: the subtitle promises
> both halves of the regime-dependence result, so the title makes no unscoped
> composition-failure claim. Consistent with "invocation rate" as the term, since
> neither uses "propensity".

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

## 3. Abstract candidate (redrafted on the N1 spine, 2026-08-20)

Paired with title D. Built on the memo's skeleton: field claim and prescribed
remedy, the measurement contribution named, the regime result in numbers, the
counterintuitive finding with its mechanism, a constructive recommendation, and
scale as protocol validation. Delivery is absent by design and belongs in
Limitations under N1. Scale figure follows the section-4 decision.

> Sound planners and validators are correct by construction, and the standard
> prescription for unreliable LLM planning is to put one behind a tool interface.
> Whether that access actually helps, and when, is rarely measured directly. Using
> PDDL as a setting where a deterministic oracle grades every answer exactly, we
> evaluate five single-tool-use tasks across five open-weight models, scoring
> against the solver and validator rather than by self-report. A three-arm design
> separates tool availability from a one-sentence steering nudge, every proportion
> carries a confidence interval, and a signed-significance rule distinguishes help
> from harm. We grade the model's delivered answer alongside the tool's return
> value, so a correct tool result that never reaches the answer does not count as
> a success.
>
> The benefit is strongly regime-dependent. Unaided plan generation sits at 8 to
> 11 percent, and the tool lifts it by 66 to 73 points. Plan checking inverts the
> pattern: for one of three models at 9B or larger, merely making the validator
> available lowers success by 67 points, because the model reasons in prose
> instead of calling it. The failure is silence rather than a wrong answer. That
> model is correct on more than 99 percent of the trials where it does call, and
> one steering sentence moves invocation from 21 to 94 percent. The limiting
> factor throughout is the invocation rate, whether the model calls at all. It is
> unstable across models and prompts, and it is separate from the model's
> capability and from the tool's accuracy. We recommend reporting the invocation
> rate beside success, and steering explicitly rather than assuming availability
> is enough. The protocol runs over 273,600 open-weight trials across two corpora,
> including an anonymized-domain twin as a contamination control, with a two-model
> frontier arm as a capability check.

Notes on choices a reviewer might probe. No sentence claims a task is impossible
without the tool; the unaided floor is quoted as a number instead. The simulate
floor is not cited as sole-source anywhere. The delivered-answer sentence names
the dual-surface instrument without spending the abstract on it, which is what N1
asks for. "Propensity" does not appear.

The D-J1 constraint (first number one-sided by construction, a gradient rather
than an interval) governed the delivery figure in the superseded draft. With
delivery out of the abstract, D-J1 no longer binds here; confirm that reading
before the tex pass.

> ANSWER (approve / revise — mark the sentences you want changed):
>

### Superseded draft, kept for the record (delivery-as-climax, N2)


> **SUPERSEDED by the section-2 answer (N1, 2026-08-20).** The draft below
> implements N2 with delivery as the *climax* ("this is where the guarantee is
> lost"), which that decision demotes. Under N1 it needs rewriting around the
> invocation rate, not renumbering. The scale-figure fix from section 4 is applied
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
none has been through `/verify-claims` in this session.

Owed on the **N1 redraft** (four numbers): the 8-11 percent unaided solve floor,
the 66-73 point solve lift, the -67 point availability harm, and the 21-to-94
percent steering move. Also owed: the ">99 percent correct when it does call"
figure, which the redraft promotes from the tex abstract into the mechanism
sentence, and the "one of three models at 9B or larger" roster claim.

The 0 / +5 / >=33 point **delivery gradient is no longer owed here**, since N1
drops it from the abstract. It returns as a debt if it is quoted in Limitations.

The scale figure in §4 is verified. The `guided_json` conformance numbers that
Limitations may cite are verified and reproduce from `tools/guided_json_audit.py`.

## 5. Abstract brainstorm, 2026-09-15 (Omer: "too much methodology; set what we present and the abstraction of the research")

Run under the `brainstorm` skill. Phase 1 context, from the tex on `paper/aaai27`
(`4eb4751`) and the decisions on record:

- **The paper's own question** (Intro, Conclusion): does a sound planner or validator,
  exposed as a callable tool, improve an LLM on individual PDDL tasks, measured at the
  answer the model delivers; when; and at what cost.
- **What the tex claims to contribute** (Intro list): (1) the controlled three-arm,
  five-task, seven-model evaluation graded at two layers; (2) invocation as the limiting
  factor; (3) the delivery gap; (4) token cost-of-pass; (5) robustness (reasoning mode,
  anonymized-domain control). The PlanBench external-validity section (rescue of an
  obfuscated benchmark, 71.8 vs 0) exists since 08-11 but is in neither abstract.
- **Standing decisions that bind the abstract:** N1 spine (invocation is the story,
  delivery lives in Limitations, 08-20); title D; "invocation rate" not "propensity";
  no unscoped "tools do not compose" declaratives; no two-sided interval as the first
  number; quote 273,600 with "five open-weight models" if scale is quoted; no
  retracted numbers (13.5/0, 0% simulate floor); frontier simulate only as bounds.
- **Why both existing abstracts read as methodology:** in each, roughly half the words
  describe the instrument (oracle grading, three arms, CIs, signed significance,
  two-layer grading) before any finding appears, and the findings are listed
  task-by-task instead of as one abstraction.
- **Reader:** JAIR primary, TMLR fallback; the memo's drafting constraint is
  "audience-self-contained", so the abstraction must be stated in tool-use terms with
  PDDL as the instance.

### Clarifying questions (answer inline; suggested answers in parentheses)

**Q1 — What is the one-sentence abstraction of the research?** Pick the sentence the
whole paper is evidence for.
  (i) "A sound tool's guarantee does not transfer to the LLM by availability alone; the
  transfer is gated by whether the model calls the tool." (= the 08-20 N1 decision)
  (ii) "The guarantee passes through two gates, calling the tool and relaying its
  result, and each gate fails for its own reason." (invocation + delivery, matches the
  Conclusion as written)
  (iii) "Whether a sound tool helps an LLM depends on the regime: decisive where the
  model cannot do the task, a cost where it can, and lost where the answer is long."
  (regime-dependence, matches the Results order)
  (Suggested: (i) is on record, but the tex body and Conclusion now argue (ii); choose
  (ii) if you want the abstract to match the paper as it stands, (i) if delivery should
  be pushed back to Limitations in the body as well.)

> ANSWER (i / ii / iii / your own sentence):
> **ANSWERED 2026-09-15 (Omer): (ii)** — two gates, calling the tool and relaying its result.

**Q2 — What do we present: findings, a protocol, or both?** The memo calls the
dual-surface protocol contribution C1; the 08-20 decision says it is not a headline.
  (Suggested: findings first; the protocol gets one clause, "graded at the answer the
  model delivers, not at the tool call", because that clause is what makes the findings
  believable and is the one methodological idea a reader should take away.)

> ANSWER (findings only / findings + one protocol clause / protocol first):
> **ANSWERED 2026-09-15 (Omer): findings + one protocol clause.**

**Q3 — Which results earn a number in the abstract, and how many?** Candidates:
solve lift (+66 to +73 pp, open-weight); availability collapse (−67 pp) and the
steering repair (21% → 94%); delivery gradient (≈0 / 5 / tens of points by answer
length); PlanBench rescue (72 vs 0 on the obfuscated benchmark); scale (273,600 trials).
  (Suggested: three at most: the solve lift, the −67 / 21→94 pair as one sentence, and
  PlanBench 72 vs 0 as the external check; scale in the last sentence if at all.)

> ANSWER (list the ones to keep):
> *(2026-09-15: Omer asked to discuss this one; see §5.1 below.)*

**Q4 — Does PlanBench belong in the abstract?** It is a full section, added after the
08-20 draft, and it is the paper's only result on a public benchmark.
  (Suggested: yes, one sentence, as "the same pattern on PlanBench" external
  validation, since it is the result an outside reader can compare to other papers.)

> ANSWER (yes, one sentence / no):
> **ANSWERED 2026-09-15 (Omer): yes, one sentence.**

**Q5 — Length and shape.** JAIR abstracts run about 150–250 words.
  (Suggested: ≤ 200 words, one paragraph, order = question → abstraction → two or
  three numbered findings → PlanBench check → the practical rule for practitioners.)

> ANSWER (word cap / shape):
> **ANSWERED 2026-09-15 (Omer): as suggested — ≤ 200 words, one paragraph, question → abstraction → findings → PlanBench check → practical rule.**

Approaches are proposed after these are answered (skill Phase 2).

### 5.1 Q3 discussion — which results earn a number (2026-09-15)

Under abstraction (ii), every number in the abstract has to play one of four roles:
show the upside when both gates pass, show gate 1 (calling) failing, show gate 2
(relaying) failing, or check the pattern outside our own benchmark. Anything that does
not play a role is Intro material. Values below are the `NUMBERS.md` frozen readings.

| candidate | role | frozen value / surface | verdict |
|---|---|---|---|
| solve at the frontier: 95% delivered with the tool vs 8–29% unaided | upside, both gates pass | **95.0 [88.8, 97.8]** both tiers, delivered; floors 8–11 open-weight, 22–29 frontier | **keep** — the one exact delivered lift on record |
| open-weight solve lift "+66 to +73 pp" (08-20 draft) | upside | NOT frozen; Job 2 block: open-roster solve *delivered* is exploratory-FAV (9B) / UNDECIDED / UNDECIDED, so the range is a mechanism-layer (tool-verified) figure | **drop** unless `/verify-claims` shows it survives on the delivered surface; the frontier 95% carries the role |
| −67 pp availability collapse on plan checking | gate 1 fails | mechanism layer only (Gemma vplan tool-verified 88 → 21); delivered cell ⟨6.6, 99.6⟩ UNDECIDED; NUMBERS: "do NOT quote −67 pp delivered" | **drop the −67**; say it as an invocation rate instead (next row) |
| invocation 21% → 94% with one steering sentence, 99% correct when it does call | gate 1 fails, and the tool is not the cause | CALL rates are storage-exact in every corpus; 99% is the tex figure (P(correct \| call)) | **keep** — the cleanest gate-1 sentence, needs no surface qualifier |
| delivery gradient: ≈0 pp on verdicts, +5 pp on plans, ≥33 pp on state trajectories, same at both frontier tiers | gate 2 fails, and grows with answer length | frozen: vd/vp/vplan ≈0; solve +5.0; simulate ≈37–50 (Sonnet) / ≈33–45 (Haiku); the tex already says "≥33 pp" | **keep** — it is the gate-2 finding; three small numbers in one clause |
| PlanBench: with tools 72% vs 0% without on the obfuscated (Mystery) benchmark; +20.5 pp on the clean one | external check | Mystery WT **71.8 [68.1, 75.3]** vs NT 0.0; clean first-draw 68.3, Δ **+20.5 pp**, p = 1.4e-13 | **keep the Mystery pair** (72 vs 0); the clean Δ is optional |
| scale: 273,600 trials, five open-weight + two frontier models, two corpora | credibility | frozen 273,600, must say "five open-weight models" | **optional** — one clause at the end or drop; it is in the Intro either way |
| token cost-of-pass ("pays for itself where the model cannot do the task") | practical rule | delivered multipliers are ranges (solve 0.65–1.64×, vd ≈2.9×, …) | **no number** — one clause without a figure, or leave to the body |

Recommended set: four figures, one per role — 95 vs 8–29 · 21 → 94 (+ 99% when called)
· 0 / 5 / ≥33 · 72 vs 0. Scale optional. Nothing else.

Constraints that still apply to the wording: the frontier simulate delivered value is
never a point (only the *gap* is quoted); the availability harm is described as an
invocation drop, not a success drop; the first number in the abstract is not a
two-sided interval (95 vs 8–29 is a rate and a range of floors, fine); "invocation
rate" throughout.

> ANSWER (keep the recommended four / add or remove — name them / scale: keep or drop):
> **ANSWERED 2026-09-18 (Omer): keep all four.** Scale clause: sent to a separate
> advisor agent with the prompt in §5.2; decision pending.

### 5.2 Advisor prompt for the scale clause, and two abstract shapes (2026-09-18)

**What "the scale clause" is.** Not a token count. It is one sentence stating how much
graded evidence the paper rests on: **273,600 trials** (five open-weight models × two
reasoning modes × three arms × 4,560 trials × two corpora), plus the separate frontier
arm (6,080 Haiku + 10,640 Sonnet = 16,720 trials). Candidate wording (22 words):

> The protocol runs over 273,600 graded trials on the five open-weight models across two corpora, one of them an anonymized-domain contamination control.

**Prompt to hand to a separate advisor agent (self-contained):**

```
You are advising on the abstract of a journal paper (target: JAIR, fallback TMLR) about
whether sound symbolic planning tools (PDDL planners and validators, exposed as callable
tools) help large language models. The abstract is capped at 200 words and is built on
one abstraction: the tool's guarantee reaches the model's delivered answer only through
two gates, calling the tool and relaying its result. It already carries four numbers:
frontier plan-generation success 22-29% unaided vs 95% with the tool; invocation 21% vs
94% with one steering sentence (99% correct when called); a delivery gap of 0 / 5 / >33
points by answer length; and PlanBench 0% vs 72% on an obfuscated benchmark.

Question: should the abstract also include a "scale clause" stating the size of the
evidence base, and if so, how? The candidate sentence is:
"The protocol runs over 273,600 graded trials on the five open-weight models across two corpora, one of them an anonymized-domain contamination control."

Facts you may rely on: 273,600 = 5 open-weight models x 2 reasoning modes x 3 arms x
4,560 trials x 2 corpora; a separate frontier arm adds 16,720 trials (two Anthropic
models) and must not be folded into the 273,600 or paired with a phrase like "seven
models"; every proportion in the paper carries a confidence interval. The Introduction
already states the per-cell count (4,560 trials per model-mode-arm cell). The earlier
version of this paper was rejected at a conference; the journal submission argues it is
an extensive revision.

Return: (1) keep / drop / shorten, with a two-sentence reason from the reader's point of
view (a planning-and-LLM-evaluation audience skimming abstracts); (2) if keep or
shorten, the best wording in at most 20 words and where in the abstract it should sit
(after the findings or as the final sentence); (3) any risk you see in quoting a trial
count in an abstract (for example, it reading as a substitute for insight).
```

**Two abstract shapes** (skill Phase 2). Both follow the agreed order: question →
abstraction → findings (upside, gate 1, gate 2) → PlanBench → practical rule. Numbers
are the frozen `NUMBERS.md` values and still owe a `/verify-claims` pass before the tex.
The scale clause, if kept, is appended as the last sentence of either.

**Shape A — guarantee-transfer, abstraction stated as a general tool-use claim** (199 words, trimmed to the 200 cap)

> Planners and validators are correct by construction, and language models can now call them as tools. Does that access improve the answers a model actually delivers, and when? We evaluate five open-weight and two frontier models on five PDDL tasks, where a deterministic oracle grades every answer exactly, scoring the delivered answer rather than the tool call. The tool's guarantee reaches the answer only through two gates. Where both hold the effect is decisive: on plan generation, frontier models rise from 22 to 29 percent unaided to 95 percent. The first gate is invocation: on plan checking, one model calls the validator on 21 percent of trials when it is merely available, on 94 percent after one steering sentence, and is 99 percent correct when it calls. The second gate is delivery: what the tool verifies fails to reach the answer by a gap that grows with answer length, none on verdicts, five points on plans, over thirty on state trajectories, at both frontier tiers. On PlanBench, the same tools lift an obfuscated benchmark from 0 to 72 percent. A sound tool helps when the model is directed to call it and the answer has room for the result.

- Pros: the abstraction is stated in tool-use terms, so it travels beyond planning
  (JAIR and TMLR readers alike); "two gates" gives the reader a handle to retain; the
  protocol appears as one clause ("grading the delivered answer rather than the tool
  call") as decided.
- Cons: "guarantee reaches the answer" is new vocabulary the body does not use yet
  (the body says "delivery gap" and "invocation"); one more sentence than B before the
  first number.
- Effort: low. Fits existing patterns: yes, the Results order is upside → gate 1 →
  gate 2 → PlanBench.

**Shape B — regime framing, uses the body's own wording** (200 words, trimmed to the 200 cap)

> Does a sound planning tool help a language model, and when? The usual fix for unreliable LLM planning is a sound planner or validator behind a tool interface. We test that prescription on five PDDL tasks over five open-weight and two frontier models, grading the delivered answer against a deterministic oracle rather than the tool's return value. The benefit depends on two behaviours separate from the model's capability and the tool's accuracy: whether the model calls the tool, and whether the result survives into the answer. When both hold the tool is decisive: frontier plan generation rises from 22 to 29 percent unaided to 95 percent. Calling is fragile: on plan checking one model invokes the validator on 21 percent of trials when merely available, on 94 percent after one steering sentence, and is 99 percent correct when it calls. Delivery leaks with length: the gap between what the tool verifies and what the answer contains is zero on verdicts, five points on plans, over thirty on state trajectories, at both frontier tiers. On PlanBench the same tools raise an obfuscated benchmark from 0 to 72 percent. Availability alone is not enough: direct the call, and give the answer room.

- Pros: opens with the question in seven words; the abstraction sentence reuses the
  Intro/Conclusion wording ("two behaviours … separate from capability and from tool
  accuracy"), so abstract and body agree word-for-word; the closing rule echoes the
  Conclusion.
- Cons: the abstraction reads as a finding about behaviours rather than as a claim
  about guarantees, which is a weaker hook; "Availability alone is not enough" revives
  the retired title phrase in prose (it is already in the Conclusion, so not new).
- Effort: low. Fits existing patterns: yes.

**Recommendation: Shape A**, because the abstraction is what the reader should carry
away, and A states it as a claim the rest of the paper is evidence for. Take B's opening
question if a seven-word first sentence is preferred.

**One consistency risk to decide with the abstract.** Title D ("Invocation Is the
Bottleneck …") was chosen on 08-20 under abstraction (i), invocation only. Under (ii) it
names the first gate and not the second. Options: keep D (invocation is the larger and
more surprising gate; delivery is the second clause of the subtitle's "when they do
not"), or revisit the title after the abstract settles. Recommendation: keep D for now
and re-read it against the final abstract before the tex pass.

> ANSWER (A / B / A with B's opening / revise — mark sentences; title: keep D / revisit):
> **ANSWERED 2026-09-18 (Omer): A.** APPLIED as `paper/aaai27` `b27ef23` (local, unpushed; 191 words in the tex). Title D kept for now (re-read against the final
> abstract before the tex pass). Scale clause: advisor agent said SHORTEN (18 words, after
> PlanBench, before the takeaway; paper_notes 2026-09-18); Omer accepted; applied as `b045f07`
> (local), abstract held at 200 words. **PUSHED 2026-09-18, Overleaf `a0b8c84`.**
