# The new Claude run: design form (section B of the form of 2026-11-25)

**Status: answered except for the models (2026-11-25).** This file is what is left of
the design form for a "unified run". The open-weight part of that form is closed:

- Omer chose the small matched run on 2026-11-25 (`reference/datasets_breakdown.md`,
  option 1). The full run of the form's sections A1 to A4 and A11 is not run.
- Its questions A5 to A10 (the no-tools system message, the simulate tool's output, the
  context window, the grader fixed before the run, the validator's upper-case fault, the
  fixed settings) were accepted as recommended on 2026-11-25. They live in the matched
  run's registration, `reference/matched_run_prereg.md`.
- The form as first written is in git history (`MOVES.md`, the clean-up of 2026-11-25).

What remains is the frontier run. It is a separate corpus and is never pooled with the
open models. It needs no cluster time.

---

## B. The frontier models

The old Claude runs have four weaknesses: one wording only (v11), answers cut at 16,384
characters, the unaided solve plan requested through structured output, and the two
arms queried 17 days apart. They also used Haiku 4.5 and Sonnet 4.6, which are no
longer the current models.

### B1. Which models

Prices are per million tokens, input / output, from Anthropic's price list (cached
2026-11-03; to be rechecked on the day). The Batch API halves them.

| Model | Price | Thinking can be turned off | Temperature can be set |
|---|---|---|---|
| Haiku 4.5 (old run) | $1.00 / $5.00 | yes | yes, until the API version of 2026-10-21 |
| Sonnet 4.6 (old run) | $3.00 / $15.00 | yes | yes, until the API version of 2026-10-21 |
| Haiku 5.5 | $0.10 / $0.50 | yes, at effort "high" or lower | no |
| Sonnet 5 | $2.00 / $10.00 | yes | no |
| Sonnet 5.5 | $2.00 / $10.00 | no; the closest is "between tools" | no |
| Opus 5 | $5.00 / $25.00 | yes, at effort "high" or lower | no |
| Opus 5.5 | $4.00 / $20.00 | no | no |

Two facts matter for the design:

- **Thinking off is the open models' setting.** Only some of the new models allow it.
  A model that always thinks is a different condition from the open models' and must
  be labelled so.
- **Temperature 0 cannot be set on the new models.** The open models run at
  temperature 0; the new Claude models run at the provider's default. This has to be
  stated; it cannot be removed.

Options:

- **Option 1: rerun the old pair** (Haiku 4.5, Sonnet 4.6). Continuity with the old
  figures; the models are dated and Haiku 4.5 costs ten times Haiku 5.5.
- **Option 2 (recommended): Haiku 5.5 and Sonnet 5**, both with thinking off. They are
  current, cheaper, and the only new pair that matches the open models' thinking
  setting. The old 4.x runs go to the supplement as an earlier record.
- **Option 3: option 2 plus Sonnet 5.5** (thinking "between tools", labelled as a
  different setting), to have the newest Sonnet in the paper.
- **Option 4: add an Opus** (5 or 5.5). The strongest model, at 2 to 2.5 times the
  Sonnet price; Opus 5.5 cannot run with thinking off.

> ANSWER: **Haiku 5.5 and Sonnet 5.5 (Omer, 2026-11-25: "sonet 5.5 and haiku 5.5. no reason for sonnet 5").** Haiku 5.5 runs with thinking off, like the open models. Sonnet 5.5 does not accept the plain "off" setting; its lowest setting (`between_tools`, effort `high` or lower) does no thinking before the answer and only returns the short notes the model writes between tool calls. So in the no-tools arm it does not think, and in the tool arm it writes notes between calls. The paper states this setting. (Corrected the same day against the API reference: the session had first told Omer that Sonnet 5.5 would have to run with thinking on.)

### B2. Design of the frontier run

**Recommendation:** the same design as the open models, as a separate corpus that is
never pooled with them:

- the same five tasks, the same 100 problems, the three plain wordings (v11 to v13);
- two arms, no tools and tools offered (plain). 4,560 trials per arm, 9,120 per model;
- the same system messages as the open models, including the format-stated unaided
  message, and **no structured-output parameter**;
- the same output caps as the open models;
- answers stored in full; both arms of a model queried on the same day;
- the exact model ID, the API version and the query dates recorded per trial.

> ANSWER: **yes, as recommended (Omer, 2026-11-25).**

### B3. A steered tool arm for the frontier models

The old Claude runs have no steered arm.

**Recommendation:** no. RQ2's steering result is about the open models; a steered arm
adds 4,560 trials per model.

> ANSWER: **no steered arm (Omer, 2026-11-25).**

### B4. Cost

**Settled (Omer, 2026-11-25): no cost estimate is needed; the cost is fine.** The Batch
API is still the recommended route (half price; results within a day), unless you want
the results faster.

> ANSWER: **the Batch API (Omer, 2026-11-25).** No cost estimate is needed.

### B5. PlanBench

The PlanBench study used Haiku 4.5. If the main frontier pair changes to newer models,
PlanBench and the main study use different models.

**Recommendation:** leave PlanBench as it is and say so in one sentence. It is a closed,
registered study and redoing it is a separate project.

> ANSWER: **PlanBench is left as it is (Omer, 2026-11-25).**

---

---

## What happens next

Once the models are confirmed: the request design is written down and checked on a
small pilot, both arms of a model are queried on the same day, and the exact model ID,
the API version and the query dates are recorded per trial. Any dollar spend is itemized
for Omer before it is made.
