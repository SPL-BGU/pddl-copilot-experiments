# Corrected-prompt control: readout

**Date:** 2026-11-24. **Registration:** `control_prompt_fix_prereg.md` (frozen
2026-11-23, package hash `825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79`).
**Analysis:** `tools/reanalysis/control_prompt_fix.py`, run once the nine cells were
complete, with `--i-have-frozen`. **Full generated tables:** `development/NUMBERS.md`,
section "Corrected-prompt control" (the same text as
`tools/reanalysis/out/control_prompt_fix.md`). This file is the short reading of those
tables. No figure here is in the paper yet; the paper change is a separate step after
Omer has read this.

## 1. What was run

Three models (Qwen3.5-9B, Gemma-26B, Qwen3.6-35B), no tools, thinking off, solve and
simulate. Each model answered the same 300 trials per task (100 problems by the three
plain wordings) under three system texts:

- **O**: the registered text of Part C, which points at a schema that is not there.
- **A**: the same text with that reference removed.
- **B**: the text that states the answer format (final answer in a fenced code block).

5,400 trials, job 24445482, 2026-11-23 19:40 to 2026-11-24 06:12. The control is a new
condition and is not pooled with Part C, the main sweep or the smoke.

**Two readings of every answer.** The *frozen grade* is the registered grader of the
rerun. The *second reading* also accepts a plan in the last code block (solve) and a
trace written one JSON object per line (simulate). Omer decided on 2026-11-23, before
any trial, that the paper quotes the second reading for cell B and for the tool arm
beside it.

## 2. Corpus and apparatus checks

- Nine cell folders, 600 rows each, 0 exception rows, 0 rows cut by storage, 0
  half-written lines. The three cells of each model hold the same 600 trial keys, and
  each task's keys equal Part C's. Unpaired trials: 0 in every contrast.
- The audit checks passed (registered system text in every cell, same user messages
  across a model's three cells, client settings, vLLM 0.20.2 in every serve log).
- The frozen grades of Part C and Part A reproduced the filed readout, and the validator
  route returned the stored verdict for 712 plans before any new plan was validated.
- Six starts were stopped by preemption and resumed in place (section 5).

## 3. The baseline the paper would quote: cell B beside the tool arm

Percent right, with the 95% interval (bootstrap over the 20 domains), n = 300 each. The
tool arm is Part A of the rerun (plain wording, 2026-10-03 to 2026-10-09), so this
comparison crosses two runs.

| model | task | no tools, cell B, second reading | tools (Part A), second reading | tools minus cell B (C4) | reading |
|---|---|---|---|---|---|
| Qwen3.5-9B | solve | 42.7 [31.7, 53.7] | 92.0 [85.3, 97.7] | +49.3 [+36.0, +63.0] | tools ahead |
| Qwen3.5-9B | simulate | 12.7 [6.0, 20.7] | 20.3 [10.3, 31.3] | +7.7 [-0.7, +17.0] | no difference shown |
| Gemma-26B | solve | 54.0 [38.3, 69.7] | 92.3 [87.3, 97.0] | +38.3 [+23.7, +53.7] | tools ahead (setup marked as moved) |
| Gemma-26B | simulate | 27.3 [15.3, 40.0] | 20.0 [11.3, 29.7] | -7.3 [-17.0, +2.7] | no difference shown |
| Qwen3.6-35B | solve | 69.0 [55.0, 81.3] | 78.3 [71.3, 84.7] | +9.3 [+0.0, +19.7] | no difference shown (setup marked as moved) |
| Qwen3.6-35B | simulate | 33.3 [20.0, 47.7] | 29.3 [17.3, 42.3] | -4.0 [-11.7, +4.3] | no difference shown (setup marked as moved) |

Under the frozen grade the same contrast reads: tools ahead on solve for all three
models (+55.7, +54.7, and +10.7 [+1.7, +20.7] for Qwen3.6-35B, which does not survive
the Holm adjustment); on simulate no difference shown for the two Qwens and **no tools
ahead for Gemma-26B** (-19.0 [-29.7, -9.0]).

**What this means for RQ1 on these two tasks.**

- **Solve.** Tools are clearly ahead for Qwen3.5-9B and Gemma-26B, by 38 to 49 points
  under the second reading. For Qwen3.6-35B the gap is +9.3 points with an interval
  that reaches zero, so with the corrected baseline the paper can no longer say tools
  are shown ahead on solve for that model.
- **Simulate.** No model shows tools ahead. For Gemma-26B the point estimate favours the
  unaided arm.
- The unaided baseline is much higher than the figures from the registered text. On
  solve, cell B under the second reading is 42.7 / 54.0 / 69.0, against 24.3 / 22.7 /
  29.3 for cell O under the frozen grade.

## 4. What changing the system text did (within this run)

Points, paired on the trial, n = 300, margin 5 points.

| contrast | model | task | frozen grade | second reading |
|---|---|---|---|---|
| A minus O (reference removed) | Qwen3.5-9B | solve | +14.7 [+10.3, +19.3] difference shown | +7.0 [+0.7, +14.7] difference shown (not after Holm) |
| | Qwen3.5-9B | simulate | +12.7 [+7.0, +18.7] difference shown | +12.7 [+7.0, +18.7] difference shown |
| | Gemma-26B | solve | +23.3 [+12.7, +34.3] difference shown | -6.0 [-12.0, +0.3] unresolved |
| | Gemma-26B | simulate | -6.3 [-11.7, -1.7] difference shown (not after Holm) | -0.7 [-3.7, +2.7] criterion met |
| | Qwen3.6-35B | solve | +28.3 [+20.0, +37.0] difference shown | +7.7 [+0.0, +16.0] unresolved |
| | Qwen3.6-35B | simulate | +4.3 [-2.0, +10.7] unresolved | +4.0 [-3.0, +11.3] unresolved |
| B minus O (format stated) | Qwen3.5-9B | solve | +8.7 [+3.7, +13.3] difference shown | +3.3 [-4.0, +11.3] unresolved |
| | Qwen3.5-9B | simulate | +5.0 [+1.0, +9.0] difference shown (not after Holm) | same |
| | Gemma-26B | solve | +15.0 [+6.7, +23.7] difference shown | +2.0 [-3.3, +7.3] unresolved |
| | Gemma-26B | simulate | +3.0 [-4.7, +11.3] unresolved | -9.0 [-19.0, +1.3] unresolved |
| | Qwen3.6-35B | solve | +37.0 [+26.7, +48.0] difference shown | +17.7 [+7.0, +30.3] difference shown |
| | Qwen3.6-35B | simulate | +14.0 [+6.0, +22.3] difference shown | +10.7 [+3.7, +18.0] difference shown (not after Holm) |

The registered readings (R1, R2), in plain words:

- **The wrong reference did lower the frozen grade on solve**, by 15 to 28 points in all
  three models. For Gemma-26B and Qwen3.6-35B most of that is layout: with the
  reference, the models wrote the plan as JSON, which the frozen grader did not read;
  under the second reading the effect is small or unresolved. For Qwen3.5-9B part of it
  remains under the second reading (+7.0), and on simulate the reference cost that
  model 12.7 points under both readings.
- **Stating the format raises the frozen grade on solve in all three models.** Only for
  Qwen3.6-35B does it also raise what the model wrote (+17.7 on solve and +10.7 on
  simulate under the second reading). For the other two the gain is layout.
- **Gemma-26B on simulate is the exception.** Neither change helps; under the second
  reading the format-stated text is 9 points lower, unresolved (section 6).

**Does cell O reproduce Part C (C3)?** The differences are small everywhere (-1.7 to
+4.0 points). The 5-point criterion is met for Qwen3.5-9B on both tasks and for
Gemma-26B on simulate. It is unresolved for Gemma-26B solve and for Qwen3.6-35B on both
tasks, because the interval reaches past 5 points; by the registered rule those three
are marked "the setup moved" and the control's levels are not set beside Part C's
there. This is a label from interval width, not a sign of a large shift.

## 5. Run record

- Preemption: six starts were stopped and requeued (Qwen3.5-9B cell A twice,
  Qwen3.6-35B cells O and A twice each). Each resumed in its own folder. No stopped
  request left a row.
- vLLM 0.20.2 in the final serve log of all nine cells. The logs of five of the six
  stopped starts were seen before they were overwritten and show 0.20.2 as well; the
  sixth (Qwen3.5-9B cell A, a start of four minutes on 2026-11-24 01:50) left a log
  with no version line, since its server did not finish starting. Every start used the
  same `~/vllm.sif`.
- GPU `NVIDIA RTX 6000 Ada Generation`, `--mem=48G`, four requests at a time, in all
  nine tasks.

## 6. The tripwire that fired, and its audit

The analysis halted on one registered tripwire: **Gemma-26B, cell B, simulate, 52
"unread final answers" of 300** (the limit is 15). The audit read the shape of all 52
(scripts and note in `control_prompt_fix_t4_audit/`):

- All 52 follow the layout cell B asks for: reasoning, then one fenced JSON block at the
  end. No answer is left in a place the readers do not look.
- 47 blocks are not valid JSON as written. The brackets do not balance: 36 lack one
  closing brace, 11 have a closing brace too many.
- 5 blocks are valid JSON, all in the sailing domain, and write each numeric value as a
  nested object, a form the grader's trace reader does not accept.
- Audit only, not a registered reading and not to be quoted as a rate: with the bracket
  slip mended where the parser stops, 25 of the 47 traces equal the answer key.

So the count is a model that writes the one JSON object it was asked for with a syntax
slip. Both readings count those answers as wrong, and the tool arm is graded by the same
parser. It does mean Gemma-26B's cell B figure on simulate (27.3) is up to about 8
points lower for syntax and not for the content of the trace. Under the registered text
Gemma wrote one object per line instead, which the second reading accepts (36.3 in cell
O). For this one model and task, the format-stated text is therefore not clearly the
fairer baseline. The tripwire was released with this note, which is printed at the top
of the generated tables.

The same count for the other cells is descriptive and did not halt: it is 0 for
Qwen3.6-35B and 10 or fewer for Qwen3.5-9B in cell B.

## 7. Open, for Omer

1. **Gemma-26B on simulate. DECIDED (Omer, 2026-11-24): keep cell B (27.3)**, as the
   registered rule says, with the JSON slip stated in one sentence. The rest of this
   item is the background. The registered rule quotes cell B (27.3). Cell O under the
   second reading is 36.3. The rule stands unless Omer changes it; changing it now
   would be a choice made after the data were seen and would have to be said so.
2. **Qwen3.6-35B on solve. DECIDED (Omer, 2026-11-25): RQ1 gives all three figures**
   (+49.3, +38.3 and +9.3 with their intervals) and says the third is not shown. The
   rest of this item is the background. With the corrected baseline the tool advantage is +9.3
   [+0.0, +19.7], not shown. RQ1's solve claim would need to say two of three models,
   or give the three figures.
3. **How the paper states the reading**: one sentence that the second reading was added
   after the rerun's data were seen and before the control's (already noted on
   2026-11-23).

## 8. Deviations

None from the registered analysis. One record that could not be kept as written: the
serve log of an earlier start of a resumed cell is overwritten by the next start (same
job id, same file name). The version lines of five of six such starts were captured by
the watcher; see section 5.
