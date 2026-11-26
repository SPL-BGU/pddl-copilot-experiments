# Matched run: readout

**Date:** 2026-11-26. **Registration:** `matched_run_prereg.md` (frozen 2026-11-25,
package hash `1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d`).
**Analysis:** `tools/reanalysis/matched_run.py`, run once the six cells were complete,
with `--i-have-frozen`. It was run a second time to write `NUMBERS.md`; the two outputs
are byte-identical. **Full generated tables:** `development/NUMBERS.md`, section
"Matched run" (the same text as `tools/reanalysis/out/matched_run.md`). This file is the
short reading of those tables. No figure here is in the paper yet; the paper change is a
separate step after Omer has read this.

## 1. What was run

Three models (Qwen3.5-9B, Gemma-26B, Qwen3.6-35B), thinking off, solve and simulate.
Each model answered the same 300 trials per task (100 problems by three wordings) in
three arms, all collected in one job on one day:

- **N**: no tools, with the system message that states the answer format.
- **P**: tools offered, plain wordings.
- **S**: tools offered, with one added sentence that names the tool.

5,400 trials, job 24502726, 2026-11-26 07:09 to 12:34 IST. A new corpus, not pooled
with the rerun, the control, the May sweep or the smoke.

**One grade, fixed before the run.** A trial is right when the final answer the model
wrote is right: on solve the plan in the last code block (or the plan the rerun's grader
reads) passes the validator, in lower case; on simulate the trace equals the answer key,
also when it is written one JSON object per line. The same grade in all three arms.

## 2. Corpus and apparatus checks

- Six cell folders, 600 rows in each no-tools folder and 1,200 in each tools folder, 0
  exception rows, 0 rows cut by storage, 0 half-written lines. The three arms of a model
  hold the same trials, and the trial keys equal the rerun's. Unpaired trials: 0 in
  every contrast.
- The audit checks passed: the registered system text in every request, the same user
  messages in the no-tools and tools cells of a model, tools present in every tools
  request and in no no-tools request, vLLM 0.20.2 in every serve log, the tool suite at
  `5e4f9c0`.
- The frozen grades of the control and of the rerun's tool arms reproduced their filed
  readouts before any contrast was computed. 740 plans were checked against stored
  verdicts before any new plan was validated.
- All six tasks ended COMPLETED with exit code 0, one start each, no preemption.
- **No tripwire fired.** Gemma-26B's no-tools arm on simulate has 43 unread final
  answers of 300 (the single-JSON-object layout the control audited); the registered
  threshold for that cell is 90.
- **One registered deviation** (registration, section 11): Gemma-26B's two cells were
  read on Omer's request while three cells were still running. The figures below are the
  registered analysis on the complete run and replace that early look.

## 3. The result

Percent right, with the 95% interval (bootstrap over the 20 domains), n = 300 per cell.
Differences are paired on the trial, in points.

### Solve

| model | no tools (N) | tools, plain (P) | tools, steered (S) | P minus N (M1) | S minus N (M2) | S minus P (M3) |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | 41.3 [31.0, 51.7] | 91.7 [85.0, 97.3] | 90.3 [83.0, 96.7] | +50.3 [+37.3, +63.3] | +49.0 [+36.0, +61.7] | -1.3 [-3.7, +0.7] |
| Gemma-26B | 58.0 [44.3, 71.3] | 94.0 [90.0, 97.3] | 94.7 [90.7, 98.0] | +36.0 [+23.0, +49.7] | +36.7 [+23.3, +51.0] | +0.7 [-1.3, +3.0] |
| Qwen3.6-35B | 68.3 [55.3, 80.7] | 79.3 [70.7, 87.3] | 90.0 [85.0, 94.7] | +11.0 [+2.3, +19.7] | +21.7 [+11.0, +33.7] | +10.7 [+4.0, +17.7] |

Registered labels: M1 and M2 are "tools ahead" for all three models. For Qwen3.6-35B,
M1 carries "(not after Holm)" (adjusted p = 0.105) and M3 is "naming the tool helps (not
after Holm)" (adjusted p = 0.057). M3 is "no difference shown" for the other two.

### Simulate

| model | no tools (N) | tools, plain (P) | tools, steered (S) | P minus N (M1) | S minus N (M2) | S minus P (M3) |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | 12.7 [5.3, 21.7] | 19.7 [10.3, 30.3] | 16.0 [7.7, 25.7] | +7.0 [-1.3, +15.7] | +3.3 [-4.0, +10.3] | -3.7 [-7.7, -0.7] |
| Gemma-26B | 31.7 [18.3, 45.7] | 17.7 [9.7, 26.3] | 16.0 [8.0, 25.7] | -14.0 [-25.3, -3.7] | -15.7 [-28.0, -4.3] | -1.7 [-4.7, +1.3] |
| Qwen3.6-35B | 35.3 [21.7, 49.7] | 30.3 [18.7, 43.3] | 32.3 [20.0, 45.3] | -5.0 [-13.3, +3.3] | -3.0 [-11.3, +4.7] | +2.0 [-1.0, +5.7] |

Registered labels: "no difference shown" for the two Qwen models on M1 and M2. For
Gemma-26B, M1 and M2 are "no tools ahead (not after Holm)" (adjusted p = 0.105 and
0.063). M3 for Qwen3.5-9B is "naming the tool hurts (not after Holm)" (adjusted p =
0.273); the other two M3 are "no difference shown".

## 4. What this means for RQ1 on these two tasks

- **Solve: the tools help every model, and now the comparison is inside one run.** The
  gain is large for the two models that solve less than 60% unaided (+50 and +36
  points) and small for Qwen3.6-35B (+11 points), which solves 68% unaided. The 35B's
  gap with the plain wording has an interval above zero but does not survive the Holm
  adjustment; with the tool named it is +21.7 and does.
- **Why the 35B gains less with the plain wording.** It does not always call: 36 of 300
  plain trials have no tool call (12 more call only another tool), against 3 with the
  tool named, and its plain arm also stops at the output cap or runs out of window more
  often. The steering sentence adds 10.7 points for this model and nothing for the
  other two. This is RQ2's finding showing up inside RQ1.
- **Simulate: the tools do not help any model.** No model has tools ahead in either
  tool arm. For Gemma-26B the unaided arm is ahead by 14 to 16 points, with intervals
  below zero that do not survive the Holm adjustment. The paper can say: on simulate
  the tools bring no gain, and for one model the estimate favours the unaided arm.
- **Where the simulate answers are lost with tools.** In every tools cell 142 to 168 of
  300 final turns were refused or cut because the prompt and the tool output filled the
  window. Without tools the window never fills; the unaided answers instead stop at the
  output cap (97 to 145 of 300). This is the RQ3 mechanism, visible here in the RQ1
  rates.
- **Headline sentences, if rebuilt on this run:** unaided solve 41 to 68%; with tools
  79 to 94% (plain) and 90 to 95% (steered). The merged draft says 43 to 69% and 78 to
  95%.

**What changes against the merged draft.** One sentence. The draft says the 35B's solve
gap "is not shown" (+9.3 [+0.0, +19.7], across two runs). In this run it is +11.0
[+2.3, +19.7]: shown by the interval, not after the Holm adjustment. Everything else
keeps its direction and its size to within a few points.

## 5. Continuity with the earlier runs (supplement)

Each arm against the same trials in the earlier run, with a margin of 5 points fixed in
advance. Descriptive; no reading depends on it.

- **The tool arms reproduce the October rerun.** Of 12 checks, 9 meet the criterion and
  3 are unresolved (the interval reaches past 5 points). The largest estimate is 2.7
  points. One check meets the criterion and also shows a small difference (Gemma-26B,
  simulate, plain: -2.3 [-4.7, -0.3], not after Holm).
- **The no-tools arm against the control's format-stated cell:** 2 of 6 meet the
  criterion, 3 are unresolved, and one shows a difference (Gemma-26B, simulate: +4.3
  [+1.0, +8.0], not after Holm). The largest estimate is 4.3 points.
- No arm differs from its earlier partner by 20 points (the tripwire). The user
  messages are the same 300 per task in this run and in the control.

So the seven-week gap that the reviewer objected to turns out to have cost little: the
earlier cross-run figures were within about 4 points of the same-run ones. The paper no
longer needs to argue that; it quotes this run.

## 6. Second sample for RQ2 and RQ3 (supplement; the body stays on the rerun)

- **Which tool was called, solve.** The fitting planner is almost always called, but
  only 26.3 to 39.3% of plain trials call it and nothing else (rerun: 22.3 to 39.0%).
  With the tool named: 41.3 to 50.0%.
- **Which tool was called, simulate.** Exactly the right tool in 70.0 to 96.3% of plain
  trials and 86.3 to 96.7% with the tool named. Qwen3.5-9B makes no call in 56 of 300
  plain trials.
- **Tool right, final answer wrong.** Solve: 5.0 to 12.4% of the trials whose tool
  returned a right plan. Simulate: 67.2 to 82.3%. The rerun gave 4.7 to 13.4% and 65.9
  to 80.5% (the latter under the reading that matches this run's grade). Most of the
  simulate loss is a final turn with no room left (107 to 164 trials per cell).

## 7. By size (descriptive)

- **Solve by reference plan length.** Unaided, the share solved falls steadily with
  length: for plans over 40 actions 19.4 / 36.1 / 41.7% (Qwen3.5-9B / Gemma-26B /
  Qwen3.6-35B). With tools (plain) the two smaller models stay at 93% or more up to 40
  actions and fall only in the last bin (44.4 and 61.1%). Qwen3.6-35B falls earlier
  (79.4% at 11 to 20 actions, 70.2% at 21 to 40) and on the longest plans its plain
  tool arm is not ahead of its unaided arm (38.9 against 41.7%; 36 trials per cell,
  wide intervals).
- **Simulate by trace length** (94 problems; the six whose prompt plan can differ from
  the key are left out). Beyond 40 actions no arm of any model delivers one exact
  trace. Up to 5 actions the tools arm is at or above the unaided arm for the two Qwen
  models (54.0 against 14.3%, and 73.0 against 66.7%).
- **The lenient state score** (states right as far as the answer goes). Unaided it is
  far above the strict score for Gemma-26B (56.7 against 40.1%) and Qwen3.6-35B (56.7
  against 43.7%); with tools the two scores are within one point of each other. Unaided answers are often
  right as far as they go and end early; tool answers are complete or absent.

## 8. Record

- Task job ids: Qwen3.5-9B 24502729 (N), 24502730 (tools); Gemma-26B 24502731 (N),
  24502732 (tools); Qwen3.6-35B 24502733 (N), 24502726 (tools). First start 07:09:23,
  last end 12:34:15 IST, 2026-11-26. The 35B tools task started at 08:43, when a slot
  came free; it is a first start.
- GPU `NVIDIA RTX 6000 Ada Generation` (49,140 MiB) in all six tasks, four requests at
  a time, 16,384-token window, vLLM 0.20.2. Cluster checkout at `3044981` with no
  tracked change; tools repo at `5e4f9c0`, clean.
- The cells were copied in two passes (three on the morning of 2026-11-26, the rest
  after the last cell ended). The agent that copied them opened no results file and no
  job log; it reported that no outcome appeared on its screen.
- The registered analysis was run once on the complete run and once more, unchanged, to
  write `NUMBERS.md`.

## 9. Next, after Omer has read this

1. The RQ1 tables and the two by-length figures for solve and simulate are rebuilt on
   this run (tables and figures only; the text is Omer's).
2. The control's and the rerun's figures on these two tasks move to the supplement with
   the continuity table, as the reporting rule says.
3. `paper_outline.md`, section 4.3 and 4.4, gets these numbers in place of the ones
   marked "(matched run)".
