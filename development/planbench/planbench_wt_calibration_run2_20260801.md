# PlanBench-WT calibration gate — run 2 (2026-08-01, v2 clause)

**Spent: $1.13 across 80 trials** (run 1 $1.09 → cumulative $2.22 of the $170 balance).
Run under the FROZEN v2 format clause (prereg §10-R restart record 1), sequential, same
discarded 20+20 draw as run 1. Run 1's responses/results/side-logs were archived to
`.local/calib/archive-20260801-103650/` before launch, so no run-1 response could be
silently reused (the no-`--ignore_existing` skip trap).

**GATE READING: both restart defects are FIXED and confirmed; cost and throughput pass;
the instrument extracts every plan the model delivered on three cells and 90% on the
fourth. One cell reads below the headline 90% line for a reason prereg run 1 already
classified as NOT an instrument defect (details below). Recommendation: proceed to
Omer's scope-and-spend slot with this reading disclosed — that slot was the next gate
regardless.**

## The two restart defects — both fixed

| defect | run 1 | run 2 | mechanism check |
|---|---|---|---|
| 1. Mystery tools shorthand (`attack g` for `attack object g`) | extraction **15.0%** | **90.0%** | residual: 2/20 trials still shorthand (was 17/20). Meets the ≥90% bar exactly. |
| 2. Mystery matched-NT narration → extractor injection | preamble 80%, injection **65%** | preamble **0%**, injection **0%** | fully dead — the `[PLAN]`-first-characters clause eliminated it. |

## Full table (run 2, all measured; analyzer `.local/calib/analyze_calib.py`)

| cell | n | extraction | preamble | injection | $/trial | out p50 | out p90 | turns | cache hit | loop_exh | delegation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ordinary / tools | 20 | **75.0%** | 100% | 5% | $0.0280 | 2917 | 5115 | 4.70 | 100% | 0 | 100% |
| ordinary / matched-NT | 20 | 100% | 0% | 0% | $0.0011 | 64 | 82 | 1.00 | 0% | 0 | — |
| Mystery / tools | 20 | **90.0%** | 25% | 0% | $0.0267 | 2339 | 4192 | 5.60 | 100% | 0 | 100% |
| Mystery / matched-NT | 20 | 100% | 0% | 0% | $0.0010 | 46 | 57 | 1.00 | 0% | 0 | — |

Analyzer validation: run against run 1's archived data it reproduces the run-1 memo's
extraction/preamble/injection **exactly** on all four cells and the $/trial figures to
the fourth decimal on the three fully-archived side-logs ($0.0011 / $0.0248 / $0.0034;
bw-tools $0.0256 vs $0.0254 on a 19-of-20-line archived log). Pricing: Haiku 4.5
$1.00/$5.00 per MTok, cache write $1.25 (5-min), cache read $0.10.

## The ordinary/tools 75% — model behavior, not instrument (same ruling as run 1)

All 5 empty extractions are the model **honestly delivering an empty
`[PLAN][PLAN END]` block after concluding the problem is unsolvable** — because its
self-authored PDDL made `classic_planner` say so. All 5 instances have gold plans
(6–8 actions), so every "unsolvable" conclusion is a formalization failure. The
extractor behaved correctly: an empty block extracts to an empty plan.

- **Instrument view: extraction of delivered plans is 15/15 = 100%** on this cell
  (Mystery tools: 18/20 = 90% — its 2 failures ARE delivered plans lost to residual
  shorthand). Run 1's memo classified this exact mechanism as "NOT a defect … the §4
  formalization-boundary mechanism appearing on its own" and restarted only on the two
  instrument defects. The same classification applies verbatim.
- **No apparatus fix exists that would not bias the design.** The only wording that
  prevents "no plan exists" answers is telling the model every problem is solvable —
  injecting ground truth into the scaffold. Not permissible.
- **Signal, not result:** rate rose 50%→75% under v2, but n=20, discarded draw,
  ungraded. It must not enter prose or influence the design. Recorded because it again
  says the real ordinary/tools cell will be informative, and the §4 boundary metric has
  something to measure.

## Residual apparatus observations (on the record for the results phase)

1. **Tools-arm final messages ignore the [PLAN]-first rule** (preamble 100% ordinary /
   25% Mystery): after a tool loop, Haiku's final message leads with a wrap-up sentence.
   The single-turn matched-NT cells obey perfectly (0% both), so the clause works; the
   multi-turn context weakens it. Verified against `planbench/engine.py:799-803` — the
   stored response IS the final message only, not loop concatenation.
2. **Measured consequence: injection 1/40 tools trials** (bw instance 7: model listed 4
   actions, extractor emitted 8 by also parsing the narration). Bias direction is
   AGAINST the tools arm (a correct plan gains spurious actions VAL will reject), i.e.
   conservative for our hypothesis. The trap-3 injection audit the prereg requires
   before any NO-RESCUE call is now automated per-cell in the analyzer; Mystery tools
   injection = 0% this run.
3. Mystery shorthand residual 2/20 — at the bar, not under it. Expect a ~10% extraction
   haircut on the Mystery tools cell at n=600; it biases against the tools arm
   (rescued plans lost to dialect), so it cannot manufacture a RESCUE verdict.

## Cost, throughput, projection (600/cell)

- Projection from measured per-trial: bw tools $16.80 + Mystery tools $16.02 + two
  matched-NT cells $1.26 ≈ **$34.08** (run 1 projected $32.78; bw tools output tokens
  rose ~10% under v2). Against $170: not budget-binding.
- **Wall-clock, sequential: ≈7.3 h** — tools trials ~22s/~19s, matched-NT ~1.5s. This
  supersedes the run-1 memo's ~12 h figure, which priced all 2400 trials at the tools
  rate.
- Caching ACTIVE (100% cache-read hit on tools trials; matched-NT 0% as predicted),
  loop_exhausted 0/80, delegation 100% both tools cells.

## Owed before the confirmatory run

1. **[OMER] scope-and-spend approval** on the measured $34.08 — including sign-off on
   the gate reading above (three cells ≥90%; ordinary/tools 75% carried as the
   not-a-defect class per run 1's ruling).
2. VAL: already resolved (Rosetta build, same grader epoch as NT — restart record 1).
3. Nothing else. Concurrency decided sequential; clause frozen; adapter unchanged.
