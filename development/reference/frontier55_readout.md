# The Claude run (Haiku 5.5, Sonnet 5.5): readout

**Date:** 2026-11-26. **Registration:** `frontier55_prereg.md` (analysis frozen
2026-11-26 at package hash
`0cbb69b7f810d039734b0aba15096bda91a6f97c6c334dfd2a0ec8ed59cbb497`, before any row was
read). **Analysis:** `tools/reanalysis/frontier55.py`, run once the four folders were
complete, with `--i-have-frozen`. The first start halted on one tripwire; after its audit
(section 2) the analysis ran, and ran once more unchanged to write `NUMBERS.md`
(byte-identical output). **Full generated tables:** `development/NUMBERS.md`, section
"Claude run" (the same text as `tools/reanalysis/out/frontier55.md`). This file is the
short reading of those tables. No figure here is in the paper yet; the paper change is a
separate step after Omer has read this.

## 1. What was run

Two hosted models, Claude Haiku 5.5 and Claude Sonnet 5.5, on the open models' five
tasks, 100 problems and three plain wordings. Two arms, the same 4,560 trials in each:
**no tools** (sent as one batch per model) and **tools offered** (live calls, all seven
tools visible). 18,240 trials, every request on 2026-11-26 UTC. Spend: 20.25 dollars
(Haiku) and 294.49 (Sonnet), plus 11.43 for the pilot.

**A separate corpus.** These rows are not pooled with, ranked against or tested against
the open models, the old Claude runs (Haiku 4.5, Sonnet 4.6) or the pilot.

**The grade** is the final answer as the model wrote it: on solve and simulate the
matched run's registered grade, on the three validation tasks the October rerun's grade.

**Conditions that differ from the open models and are stated with every row:**
temperature at the provider's default (the open models run at 0); a window of about one
million tokens (theirs is 16,384); the output cap of 8,192 and 6,144 counted in the
provider's tokens; hosted weights; the no-tools arm batched and the tool arm live; the
tools run on the laptop. Haiku ran with thinking off. Sonnet ran at its lowest setting.

## 2. Corpus and apparatus checks

- Four folders, 4,560 rows each, the same trials in both arms of a model. No refusal, no
  error row, no row cut by storage, no half-written line, no abandoned try.
- One batch per model, 4,560 of 4,560 items succeeded, none expired, errored or
  canceled. Both arms of each model fall on one UTC day.
- One start per folder, from the runner commit the registration names. The model id
  returned was the one asked for throughout. API version header `2023-06-01`, SDK
  0.109.2, no cache tokens.
- The validator route returned the stored verdict for 740 plans before any new plan was
  validated.
- **One tripwire fired and was audited** (`frontier55_t8_audit/`). Sonnet's tool arm
  returned six notes between tool calls (in 6 of 4,560 trials, 122 to 212 characters
  each), and the provider's own count of thinking tokens is zero on every one of its
  9,167 turns, those six included. So the notes' tokens are inside the output tokens and
  are reported as not separable. All six were passed back unchanged. No grade depends on
  them. Haiku and Sonnet's no-tools arm returned no note.
- **The eighth open point** ("the first batch expired as a whole") did not arise: no
  item of either batch expired.
- Omer sent the console download of Sonnet's batch results on 2026-11-26. It was not
  opened or used; the runner fetched the same batch itself.

## 3. RQ1: do the tools help?

Percent right with the 95% interval (bootstrap over the 20 domains). The difference is
paired on the trial, in points.

| model | task | no tools | tools | tools minus no tools | reading |
|---|---|---|---|---|---|
| Haiku 5.5 | solve | 73.7 [60.0, 85.7] | 95.0 [89.0, 99.3] | +21.3 [+7.7, +36.3] | tools ahead |
| Haiku 5.5 | validate_domain | 82.5 [70.6, 92.2] | 100.0 | +17.5 [+7.8, +29.4] | tools ahead |
| Haiku 5.5 | validate_problem | 88.3 [83.5, 92.7] | 97.2 [95.5, 98.7] | +8.8 [+4.2, +14.0] | tools ahead |
| Haiku 5.5 | validate_plan | 94.3 [91.3, 96.9] | 95.1 [91.8, 98.0] | +0.8 [-1.6, +3.0] | no difference shown |
| Haiku 5.5 | simulate | 41.3 [26.0, 57.3] | 21.0 [11.7, 32.0] | -20.3 [-30.7, -11.0] | no tools ahead |
| Sonnet 5.5 | solve | 94.0 [87.3, 99.3] | 97.0 [94.7, 99.0] | +3.0 [-3.0, +10.7] | no difference shown |
| Sonnet 5.5 | validate_domain | 99.7 [99.2, 100.0] | 100.0 | +0.3 [+0.0, +0.8] | no difference shown |
| Sonnet 5.5 | validate_problem | 95.7 [94.0, 97.3] | 99.5 [98.5, 100.0] | +3.8 [+2.2, +5.7] | tools ahead |
| Sonnet 5.5 | validate_plan | 99.0 [97.9, 99.8] | 99.4 [98.5, 100.0] | +0.4 [-0.5, +1.6] | no difference shown |
| Sonnet 5.5 | simulate | 55.0 [41.7, 68.3] | 46.3 [33.0, 60.0] | -8.7 [-17.0, +0.0] | no difference shown |

Every "tools ahead" and Haiku's "no tools ahead" survive the Holm adjustment across the
five tasks of the model (adjusted p from 0.0015 to 0.022).

**What this means.**

- **Haiku 5.5: the tools help where the unaided model still errs.** Solve, domain
  validation and problem validation gain 9 to 21 points and reach 95 to 100%.
- **Sonnet 5.5: little room is left.** Unaided it is right in 94 to 99.7% of trials on
  four tasks, so the tools can add at most a few points. The one gain shown is on problem
  validation (+3.8). On solve the registered reading is "no difference shown"; it is not
  "the unaided model is as good as the tools".
- **Simulate: the tools help neither model, and for Haiku the unaided arm is clearly
  ahead** (-20.3 points, the interval far from zero). This is the same direction as the
  open models, and here the window cannot be the cause: it holds about a million tokens.
  Section 5 looks at why.

**Verdict errors on validate_plan** (1,500 valid and 1,500 broken plans per arm).
Unaided, Haiku calls 105 valid plans invalid (7.0%) and 67 broken plans valid (4.5%);
Sonnet 19 (1.3%) and 10 (0.7%). With tools, Haiku 56 and 11, Sonnet 12 and 0. Haiku's
tool arm also leaves 80 trials with no verdict: 79 of its validate_plan tool trials
stopped at the output cap. That is why its plan-validation rate does not rise with tools
although its wrong verdicts fall.

## 4. RQ2 and RQ3

**RQ2: the right tool is called.** Sonnet calls exactly the task's tool in 91.3 to 100%
of trials on every task. Haiku does so in 100% on domain validation and simulate, 86.3%
on solve and 86.1% on validate_plan (116 of 3,000 trials make no call), and 64.2% on
problem validation, where 215 of 600 trials call the right tool and another one beside
it. Calling only a wrong tool is rare (at most 5 trials in a cell).

**RQ3: verdicts and plans reach the answer; traces mostly do not.** Of the trials whose
tool returned the right result, the final answer is wrong in:

| task | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| validate_domain, validate_plan | 0 of 3,175 | 0 of 3,343 |
| validate_problem | 5 of 588 (0.9%) | 0 of 597 |
| solve | 15 of 294 (5.1% [0.7, 11.4]) | 9 of 299 (3.0% [1.0, 5.3]) |
| simulate | 223 of 286 (78.0% [66.0, 88.0]) | 157 of 296 (53.0% [39.0, 66.7]) |

The order is the open models' order: almost nothing lost on verdicts, a few percent on
plans, most of the traces. The trace loss is as large here as for the open models, with
no window limit.

## 5. How the simulate answers look (a post hoc description, not registered)

Counted on the stored final answers after the registered analysis, by layout only. The
user message shows the step format in both arms; the no-tools system message also asks
for one fenced JSON object, and the with-tools system message does not state a format.

- **Unaided, both models write the JSON trace.** 213 (Haiku) and 214 (Sonnet) of 300
  answers are a JSON object with the trace; 86 (Haiku) and 85 (Sonnet) stop at the
  output cap before the trace ends.
- **With tools, Haiku mostly writes the trace as prose.** 204 of 300 final answers hold
  no JSON at all: a step-by-step listing in sentences or a table, often with the static
  facts set aside or with phrases that abridge it. The registered grade reads these as
  wrong. Whether their content is right is not measured.
- **With tools, Sonnet mostly writes JSON** (219 of 300 as a list of steps), and its
  wrong answers are more often a trace that differs from the key (84) than an unread
  layout (52).

So for Haiku the simulate gap is mainly about the form of the answer: after the tool
has returned the trace, the model reports on it instead of handing it over in the format
asked for. That is what RQ3 asks about. It is also a caveat on the size of the gap: a
grade that read prose would give a different number, and none is registered.

## 6. Against the old Claude runs: what must not be said

The merged draft quotes the old runs (Haiku 4.5, Sonnet 4.6): unaided solve 22 to 29%,
with tools 95%. The new models solve 73.7 and 94.0% unaided. The two are different
models under different conditions (the old unaided solve answers were requested through
structured output; one wording in the tool arm; answers cut at 16,384 characters), so the
change is not a measured effect of anything. For the paper it means the sentence
"frontier models solve 22 to 29% unaided" does not describe these models, and "the tools
lift the frontier models to 95%" becomes "Haiku 5.5 gains 21 points; for Sonnet 5.5 no
gain is shown".

## 7. Next, after Omer has read this

1. The Claude section's table is built from this run, and the Claude rows leave the RQ1
   tables and the by-length figures (Omer, 2026-11-26: "Own section only"). The old
   Claude rows go to the supplement.
2. `paper_outline.md`, section 7, gets these numbers.
3. Open for Omer: whether to compute a second, descriptive reading of Haiku's prose
   traces (section 5). It would be post hoc and could not replace the registered figure.
