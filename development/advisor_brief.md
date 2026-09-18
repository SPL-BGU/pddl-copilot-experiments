# Advisor brief: six decisions before the journal submission (2026-09-18)

**Goes with** the manuscript (`paper/main.pdf`, 25 pages, title *Invocation Is the
Bottleneck: When Sound Planning Tools Help an LLM, and When They Do Not*).
**How to answer:** write under each `> ANSWER:` line. One conversation can close all six.
This page adds no new numbers; every figure is the frozen value in `NUMBERS.md`.

**Where the paper stands.** No experiment is owed and no `\todo` is left. The three
writing jobs (PlanBench section, the delivered-answer reframe, the steering control) are
in Overleaf. The main suite grades 273,600 trials across five open-weight models and two
corpora, with anonymized domains as the contamination control, plus two frontier tiers
(Claude Haiku 4.5, Sonnet 4.6) and the PlanBench arm. What is left after this round is
mechanical: the venue reformat and the cover letter.

## 1. Venue: JAIR first, TMLR as the fallback?

JAIR fits on verified grounds: planning-literate readers, recent LLM-evaluation papers in
the venue, no page cap, no publication fee. Its policy asks for "originality and
significance", so the cover letter argues that directly: each control we added flipped a
headline of our own earlier version (arXiv:2509.12987), which also answers JAIR's
summary-reject trigger for previously rejected work that has "not undergone extensive
revisions". Fallback rules are fixed in advance: summary reject → the same manuscript to
TMLR, reformat only; "reject, resubmission encouraged" → resubmit to JAIR; full-review
reject → TMLR with the reviews addressed. AIJ only if you override (first decision
about 20 weeks, few LLM-evaluation papers there in 2024–2026). The honest odds, as base
rates over all 2025 JAIR submissions and not adjusted for quality: about 77% summary
reject, 13% accept (around spring 2027), 10% late reject. This reverses the May ranking
that had AIJ first.

**Recommendation:** ratify JAIR primary, TMLR fallback.
*Source:* `journal_decisions_memo.md` §5 and §10.1; Omer confirmed it as the working
target on 2026-08-30 (`paper_notes_discussions.md`).

> ANSWER (ratify / AIJ instead / other):
>

## 2. Thesis requirement: is *submitted* enough?

The venue choice assumes the September 2026 MSc requirement is a **submitted**
manuscript, not an acceptance. No venue on the shortlist can return an acceptance in
that time. If acceptance is required, question 1 reopens.

**Recommendation:** confirm that submitted is enough.
*Source:* memo §5 (stated assumption) and §10.2.

> ANSWER (submitted is enough / acceptance needed):
>

## 3. Put the journal pivot on record

AAAI-27 is off: its deadline passed (recorded 2026-08-30) and the paper is journal-only.
The manuscript is still typeset with the AAAI style file; the reformat touches every
float, so it is done once, after question 1 is answered.

**Recommendation:** acknowledge, so the pivot is on record with everyone.
*Source:* memo §10.3; `paper_notes_discussions.md` 2026-08-30.

> ANSWER (acknowledged / comment):
>

## 4. Cost: does anything from the dollar-cost deck belong in the paper?

The paper's cost section ("What the Tool Costs") reports **tokens per delivered
success**, measured on our own runs. Example: on plan generation a delivered success
costs 3.1× the tokens with the tool for Sonnet and 6.1× for Haiku. The recompute on the
delivered surface that the memo asked for is done and in the tex. The separate deck
(`archive/cost-breakdowns/`) prices whole setups in dollars across four providers, a
hybrid orchestrator-plus-subagent setup and a sample-reduction ladder. Only its
Anthropic rows are measured; the other providers are projected from the mean of two
token profiles at June-2026 list prices, and two of its figures were superseded on
2026-07-12. It was built to size API spend. That spend is done and the budget question
closed on 2026-08-30, so what remains is a content question only.

**Recommendation:** keep the paper on the measured token cost-of-pass it has; the deck
stays an internal planning document.
*Source:* `STATUS.md` "External gates"; memo §10.4; `archive/cost-breakdowns/SUMMARY.md`;
`NUMBERS.md` cost-of-pass rows.

> ANSWER (keep as is / add dollar figures, say which / other):
>

## 5. Storage-fixed rerun of about five headline cells: contingency, or run before submitting?

The open-weight tool-arm runs stored a 500-character snapshot of each final answer, so
delivered success in those cells is a range, and 13 of 25 availability cells stay
undecided at `think=off`. The paper says so and pre-registers a full-storage rerun of
the headline cells as its declared answer to a reviewer request (Limitations). Running
it now costs cluster GPU-hours and Omer's VPN time, no dollars. It carries a known risk:
the earlier independent full-storage rerun failed job-level parity with the main sweep,
so a new rerun counts only if it passes a Gemma negative control and the ±5 pp
equivalence test.

**Recommendation:** contingency only (the recorded default).
*Source:* memo §3 amendment, §9 "Optional, default = not run", §10.5; `NUMBERS.md`
open-roster availability row.

> ANSWER (contingency only / run before submission):
>

## 6. Sonnet-tier PlanBench extension: run, or leave excluded?

The PlanBench arm uses one model, Claude Haiku 4.5: 68.3% with tools on the clean set
(first draw, +20.5 pp against the matched no-tools arm) and 71.8% against 0% on the
obfuscated Mystery set. A Sonnet arm was registered as an extension and not run. The
only reason was budget, and the grant removed that reason on 2026-08-30. The paper owns
it as a limitation ("This arm covers one model"). It is not priced yet: it needs a
calibration of about 20 instances and a preregistration under the freeze protocol
before any spend. For scale, the whole Haiku arm cost about $46 (about $0.017 per
trial), and Sonnet's list price per token is three times Haiku's. API only, no cluster.

**Recommendation:** leave it excluded for the first submission and price it now, so it
is a costed, preregistered answer if a reviewer asks. Run it before submission only if
you judge the one-model limitation a likely reason for rejection.
*Source:* `paper_notes_discussions.md` 2026-08-30 (expense ledger, item 2); memo §4
"Cost to Omer"; tex "Scope and Cost"; `NUMBERS.md` PlanBench rows.

> ANSWER (leave excluded / price it, then decide / run before submission):
>
