# Next steps after the two in-flight runs (written 2026-07-12)

Two runs are in flight, both expected to land within ~20h:

1. **Qwen with-tools re-run** — ISS-024(d), cluster job **19293221** (4 Qwens ×
   think=on × tools_all_minimal, `--reasoning-parser none`, `--run-tag iss024d-e2e`,
   16K snapshot cap, 72h wall from 07-11). Purpose: every trial fully
   e2e-gradeable → resolves the censored with-tools cells exactly, and answers the
   parser-off parity question.
2. **Sonnet WT canonical** — `frontier_runner.py --model claude-sonnet-4-6
   --variant 11` → `results/sonnet-frontier/sweep5v2-with-tools` (122/1520 trials
   at time of writing, est ≈$96, local API run — no cluster involved).

Both feed the same convergence point: one D7 rule set over
`results/derived/e2e_overlay/` → Phase 5 analyzer (e2e_strict headline) →
corrected pooled table → paper prose corrections.

---

## Track A — when Sonnet WT completes (local, no ping needed)

1. **Completion + cost check.** Confirm 1520 trials in `trials.jsonl`, scan for
   context-overflow/truncation rows (Haiku hit one on simulate depot/p01), record
   actual spend vs the ~$66 budget spare in `frontier_rerun_handoff.md`.
2. **Regrade:** `python tools/e2e_regrade.py results/sonnet-frontier` — lands in
   the shared overlay under the D7/D7b rules (16K cap auto-detected → exact e2e,
   `e2e_strict` headline).
3. **Analysis vs Haiku (the with-tools capability ladder):**
   - tool-verified vs delivered gap per task — expect the same solve/simulate
     transcription gap, smaller if Sonnet transcribes long outputs better. This
     directly tests the surviving story ("delivered fidelity degrades with output
     length") on a second model tier.
   - validation tasks: does the tool lift stay ~ceiling at Sonnet tier (ladder
     prediction: lift shrinks as the model strengthens)?
   - NT comparison uses **Sonnet-NT sliced to v11-only** (zero-cost filter, no
     rerun; decided in `archive/frontier_haiku_phase_plan.md`).
4. **Docs:** update `frontier_rerun_handoff.md` + dated entry in
   `paper_notes_discussions.md`. Note: WT-anon deliberately skipped (decision
   recorded 2026-07-12) — don't reopen.

## Track B — when job 19293221 lands (cluster — ping Omer before any SSH)

1. **Ping + sync.** VPN up → cluster-ops sync of
   `results/slurm_vllm_*_iss024d-e2e/` (remember: the run-tag suffix breaks the
   analyzer cell-parser — strip it post-filter). Post-mortem the 4 array tasks
   (sacct, full trial counts, right-size notes).
2. **Regrade** the new corpus with `e2e_regrade.py` → the Phase-1 `[low, high]`
   bounds collapse to exact numbers for the strict-undecided cells:
   - 4B validate_plan (straddled), 35b validate_plan (inverted at lower bound),
     gemma-4-26B (81% censored), 9B solve, all simulate cells.
3. **Parity check:** iss024d-e2e vs sweep5v2-live on tool-verified metrics — the
   parser-off change could shift extraction. Keep it a **separate corpus**, never
   pooled into sweep5v2-live (corpus-identity rule).

## Convergence — after both

4. **Phase 5 analyzer (the one unbuilt piece).** Analyzer/master tables read
   `e2e_strict` as the headline column next to tool-verified, rendering bounds
   where censored. Then regenerate the corrected pooled table from the overlay
   (all corpora, one rule set) — this replaces the retracted 07-12 morning table.
5. **Paper corrections (needs Omer's go — no prose unprompted).** Claims owed a
   rewrite once the corrected table exists:
   - simulate "sole-source 0% floor" → corrected frontier floor ~40–45 canon
     (ISS-024 fix) + WT delivered canon [52,64] under D7;
   - "drives tool then drops answer" → length-dependent delivered fidelity +
     strict-parser format-drift secondary finding;
   - the iter-1 "CLOSE NOW" writing batch (iter1_action_plan.md).
6. **Merge `feat/e2e-scoring-overlay`** (PR to main) once Phase 5 lands and the
   Sonnet/iss024d regrades are in the overlay.

## Not gated on these runs (backlog, unchanged)

- Advisor cost verdict — external gate for the next cost-phase step.
- PlanBench v3 (scaffolded small models; `PLANBENCH_HANDOFF_v3.md`).
- ISS-024(b) `guided_json` enforcement fix (generation apparatus, open-roster).
- Sweep7 open item: resume re-enumerated solve 2400-vs-600 (RunPod pod torn down).

---

## Open decisions (annotate inline)

**D-N1 — Phase 5 shape.** Wire `e2e_strict` into the existing analyzer/master
pivot (flag on the current table builders), or a standalone e2e table generator
that the deck imports? Recommendation: flag on the existing builders, so the
master pivot stays the single source.

> ANSWER: Agree

**D-N2 — Sonnet WT analysis depth.** Quick handoff-style read (gap table + ladder
verdict) vs full research-grade memo with CIs against the Haiku run?
Recommendation: full memo — it's a paper-facing contrast.

> ANSWER: Agree

**D-N3 — Paper prose timing.** Start the claim rewrites (item 5) immediately after
the corrected pooled table, or wait for the advisor cost verdict so the writing
batch happens once? Recommendation: immediately — the retracted claims are
independent of the cost story.

> ANSWER: immediately

**D-N4 — iss024d as headline corpus.** If parity with sweep5v2-live holds, do the
paper's with-tools e2e numbers come from iss024d-e2e (exact) with sweep5v2-live
retained for tool-verified, or do we report sweep5v2-live bounds + iss024d exact
side by side? Recommendation: iss024d for e2e, sweep5v2-live for tool-verified,
stated explicitly in methodology.

> ANSWER: assign corpora per claim, not per column; compute the gap paired within iss024d; pre-specify the parity
> margin; resolve the gemma coverage gap explicitly
