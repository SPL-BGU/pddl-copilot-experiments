# Advisor brief: six decisions before the journal submission (2026-09-18)

Goes with the manuscript (`paper/main.pdf`, 25 pages): *Invocation Is the Bottleneck:
When Sound Planning Tools Help an LLM, and When They Do Not*. **Write under each
`> ANSWER:` line**; one conversation can close all six. No new numbers here: every
figure is the frozen value in `NUMBERS.md`.

**Where the paper stands.** No experiment is owed and no `\todo` is left. All three
writing jobs are in Overleaf. The main suite grades 273,600 trials (five open-weight
models, two corpora, anonymized domains as the contamination control), plus two frontier
tiers and the PlanBench arm. After this round only the venue reformat and the cover
letter remain.

## 1. Venue: JAIR first, TMLR as the fallback?

JAIR has planning-literate readers, recent LLM-evaluation papers, no page cap and no
fee. It asks for "originality and significance", so the cover letter argues that each
control we added flipped a headline of our own earlier version (arXiv:2509.12987). That
also answers JAIR's summary-reject rule for rejected work "not undergone extensive
revisions". Fallbacks are fixed in advance: summary reject → same manuscript to TMLR;
"resubmission encouraged" → back to JAIR; full-review reject → TMLR with the reviews
addressed. AIJ only on your override (about 20 weeks to a first decision). Base rates
over all 2025 JAIR submissions, not adjusted for quality: about 77% summary reject, 13%
accept (around spring 2027), 10% late reject. This reverses the May ranking (AIJ first).

**Recommendation:** ratify JAIR primary, TMLR fallback. *Source:* memo §5, §10.1;
working target since 2026-08-30.

> ANSWER (ratify / AIJ instead / other):
>

## 2. Thesis requirement: is *submitted* enough?

The venue choice assumes the September 2026 MSc requirement is a **submitted**
manuscript, not an acceptance. No shortlisted venue can return an acceptance in that
time. If acceptance is required, question 1 reopens.

**Recommendation:** confirm that submitted is enough. *Source:* memo §5, §10.2.

> ANSWER (submitted is enough / acceptance needed):
>

## 3. Put the journal pivot on record

AAAI-27 is off: the deadline passed (recorded 2026-08-30) and the paper is journal-only.
It is still typeset in the AAAI style; the reformat is done once, after question 1.

**Recommendation:** acknowledge. *Source:* memo §10.3; `paper_notes_discussions.md` 08-30.

> ANSWER (acknowledged / comment):
>

## 4. Cost: does anything from the dollar-cost deck belong in the paper?

The paper reports **tokens per delivered success**, measured on our runs (on plan
generation, 3.1× the tokens with the tool for Sonnet, 6.1× for Haiku). The separate deck
(`archive/cost-breakdowns/`) prices whole setups in dollars across four providers. Only
its Anthropic rows are measured; the rest are projected at June-2026 list prices, and
two of its figures were superseded on 07-12. It was built to size API spend, which is
done, so this is now a content question only.

**Recommendation:** keep the measured token cost-of-pass; the deck stays internal.
*Source:* `STATUS.md` "External gates"; memo §10.4; `archive/cost-breakdowns/SUMMARY.md`.

> ANSWER (keep as is / add dollar figures, say which / other):
>

## 5. Storage-fixed rerun of about five headline cells: contingency, or run first?

The open-weight tool-arm runs stored a 500-character snapshot of each final answer, so
delivered success there is a range, and 13 of 25 availability cells stay undecided at
`think=off`. The paper says so and pre-registers a full-storage rerun as its answer to a
reviewer request (Limitations). Running it now costs cluster GPU-hours and VPN time, no
dollars. Known risk: the earlier independent full-storage rerun failed job-level parity,
so a new one counts only if it passes the Gemma control and the ±5 pp equivalence test.

**Recommendation:** contingency only (the recorded default). *Source:* memo §3, §9, §10.5.

> ANSWER (contingency only / run before submission):
>

## 6. Sonnet-tier PlanBench extension: run, or leave excluded?

The PlanBench arm uses one model, Claude Haiku 4.5: 68.3% with tools on the clean set
(first draw, +20.5 pp against the matched no-tools arm) and 71.8% against 0% on the
obfuscated Mystery set. A Sonnet arm was registered and not run, for budget reasons
only; the grant removed that reason on 08-30. The paper owns it as a limitation. It is
not priced yet: it needs a calibration of about 20 instances and a preregistration
before any spend. For scale, the whole Haiku arm cost about $46 and Sonnet's list price
per token is three times Haiku's. API only, no cluster.

**Recommendation:** leave it excluded for the first submission and price it now, so it
is a costed, preregistered answer if a reviewer asks. Run it first only if you judge the
one-model limitation a likely reason for rejection. *Source:* `paper_notes_discussions.md`
08-30 (expense ledger, item 2); tex "Scope and Cost".

> ANSWER (leave excluded / price it, then decide / run before submission):
>
