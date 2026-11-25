# The unified run: design form

**Status: OPEN, waiting for Omer's answers (written 2026-11-25).** Omer approved a fresh
unified run on 2026-11-25. Nothing here is registered or submitted. Fill in each
`> ANSWER:` line; a bare "ok" accepts the recommendation. Once the answers are in, this
form becomes the registration (`reference/unified_run_prereg.md`), the analysis is
written and frozen, a smoke runs, and then the run. Every cluster step still needs a
separate go-ahead.

**Why the run.** The paper now rests on several corpora that cannot be pooled: the main
sweep (answers cut at 500 characters), the rerun (missed its parity criterion), and the
corrected-prompt control (run seven weeks after the tool arms it is compared with). One
run with full answer storage, the corrected system message, one serving version and all
arms of a model in one window removes the cross-run comparisons.

**What it costs in time.** The rerun had the same size as the recommended design below
(41,040 trials) and took six days of wall time. Preemption is active on the cluster now.
Dates: abstract 2026-12-07, paper 2026-12-14.

---

## A. The open-weight run

### A1. Models

The three models of the rerun: Qwen3.5-9B, Gemma-MoE-26B, Qwen3.6-35B. The two smaller
models (0.8B, 4B) appear only in the main sweep.

**Recommendation:** the three models only. The small ones add about 27,000 trials and
answer no research question.

> ANSWER:

### A2. Tasks

All five: solve, validate_domain, validate_problem, validate_plan, simulate.

**Recommendation:** all five. RQ2 and RQ3 need all of them, and delivered rates for
validate_domain and validate_problem exist today only as tool-verified figures from the
main sweep.

> ANSWER:

### A3. Arms

1. No tools (plain wordings v11 to v13).
2. Tools offered, plain wordings (v11 to v13).
3. Tools offered, steered wordings (v14 to v16).

Not included unless you say so: the neutral tool prompt (Gemma only in the rerun) and
the no-tools steered control.

**Recommendation:** the three arms above. Per model: 4,560 trials per arm, 13,680 in
all; 41,040 for three models.

> ANSWER:

### A4. Thinking

**Recommendation:** thinking off only, as in the rerun and the control. Thinking on
doubles the run and brings back the shared-budget problem. The paper would keep the
main sweep's thinking-on findings as a short pointer to the supplement.

> ANSWER:

### A5. The no-tools system message

**Recommendation:** on solve and simulate, the format-stated messages of the control
(cell B), word for word. On the three validation tasks, the messages as they are (they
never had the schema reference). The registered and reference-removed messages are not
run again; the control already measured them.

Known cost, from the control: with the format-stated message Gemma writes a single JSON
object on simulate and breaks the brackets in about 16% of answers.

> ANSWER:

### A6. The simulate tool's output format

The reviewer's point: the tool returns every predicate, true and false, in a notation
different from the one the answer must use, so the model has to convert a long output.

- **Option 1 (recommended): keep the tool as it is.** The paper then says plainly that
  the simulate loss is a conversion and context-budget bottleneck. No plugin change, and
  the tool suite stays the one the paper describes.
- **Option 2: change the tool** so its output matches the answer format. That is a
  change in the sibling repo, a new tool suite, new verification, and it removes the
  finding the paper currently reports. It also adds days before the run can start.
- **Option 3: both**, as two tool arms on simulate only. Adds 1,800 trials per model
  and the plugin work of option 2.

> ANSWER:

### A7. Context window

**Recommendation:** 16,384 tokens, as everywhere else. The 32K smoke of May raised
unaided parse failures, and a new window size is its own condition. The 64K pilot stays
in the supplement as the evidence on context.

> ANSWER:

### A8. The grader, fixed before the run

Today the paper carries two readings (the registered grader and the "second reading").
A fresh run can register one reader up front.

**Recommendation:** register the second reading as the single grader of the run (the
plan in the last code block on solve; a trace as one object per line also read on
simulate), applied the same way to every arm. The old registered grader is reported
once in the supplement for continuity. One grader means one set of numbers.

> ANSWER:

### A9. The validator's upper-case fault

`pyval` 0.1.5 rejects valid plans that write names in upper case. It lowers a few
unaided solve grades.

- **Option 1 (recommended): keep 0.1.5 and grade the case-folded plan** as the
  registered grade. No validator change, labels stay the ones the fixtures were built
  with, and the fault no longer touches a grade.
- **Option 2:** upgrade the validator. The ground-truth labels would have to be
  rebuilt and rechecked first.

> ANSWER:

### A10. Fixed settings (stated for the record)

Same 20 domains and 100 problems, same fixtures and wordings, same output caps (8,192
tokens on solve, 6,144 on simulate), temperature 0, answers stored up to 65,536
characters, vLLM 0.20.2 from the pinned `~/vllm.sif`, four requests at a time, one
`rtx_6000` per cell, all cells of a model submitted in one array job. The system
message sent is logged per trial, as in the control.

**Recommendation:** accept as listed.

> ANSWER:

### A11. What the old corpora become

**Recommendation:** the unified run is the primary open-weight dataset for RQ1, RQ2 and
RQ3. The main sweep is cited only for what it alone has (thinking on, the renamed
domains, the small models). The rerun and the control move to the supplement as earlier
records and are not quoted in the body. Nothing is pooled across them.

> ANSWER:

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

> ANSWER:

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

> ANSWER:

### B3. A steered tool arm for the frontier models

The old Claude runs have no steered arm.

**Recommendation:** no. RQ2's steering result is about the open models; a steered arm
adds 4,560 trials per model.

> ANSWER:

### B4. Cost ceiling

I have not estimated the cost yet. I will compute it from the token counts of the old
runs and the prices above, per option of B1, before any call is made, and bring it to
you.

**Recommendation:** use the Batch API (half price; results within a day) and set a
ceiling in dollars here.

> ANSWER:

### B5. PlanBench

The PlanBench study used Haiku 4.5. If the main frontier pair changes to newer models,
PlanBench and the main study use different models.

**Recommendation:** leave PlanBench as it is and say so in one sentence. It is a closed,
registered study and redoing it is a separate project.

> ANSWER:

---

## C. Process

### C1. Registration and freeze

**Recommendation:** as for the control. A registration written from this form; the
analysis code written and frozen (typed loader, constants as checks, clause map,
fixture, independent review) before any trial exists; a smoke on the full-run SLURM
profile; then the run. Primary outcome: the delivered final answer. Contrasts per model
and task: tools (plain) minus no tools, and steered minus plain, paired on the trial,
95% domain-cluster bootstrap.

> ANSWER:

### C2. Order and dates

A possible order: answers to this form by 2026-11-26; registration, analysis and smoke
by 2026-11-28; run from 2026-11-28 to about 2026-12-04; analysis and the 8-page text
after that. The abstract of 2026-12-07 would be written when the open-weight numbers
are in or nearly in.

**Recommendation:** start the frontier run in parallel as soon as B1 to B4 are
answered, since it does not use the cluster.

> ANSWER:

### C3. If the run is not finished in time

**Recommendation:** decide now what happens if a model's cells are incomplete on
2026-12-10: submit with the two complete models, or fall back to the merged draft's
corpora. A short cell is never analysed.

> ANSWER:
