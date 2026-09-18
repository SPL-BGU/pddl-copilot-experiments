# PlanBench-WT — arm close-out (final state; last updated 2026-08-11)

> **THE ONE ENTRY POINT for this arm.** The other three handoffs
> (`PLANBENCH_WT_NEXT_STEPS_HANDOFF.md`, `PLANBENCH_WT_HANDOFF.md`,
> `PLANBENCH_HANDOFF_v3.md`) are superseded snapshots kept for background and
> traps only — each carries a banner saying so. Do not take a state claim or a
> headline number from any of them.
>
> **The arm is CLOSED.** All experiments done, verdict **RESCUE, SUPPORTED**,
> mechanism branch final, four-rung ladder complete, bare-NT at n=600. No
> further paid runs are planned or needed. Arm cumulative ≈ $46.2 of $170.
>
> **Authoritative sources, in order:**
> 1. `planbench_wt_results_20260803.md` — every internal number, the audits, the
>    deviation table. Self-contained; read the deviation-1 row before quoting
>    any clean-WT figure.
> 2. `planbench_wt_paper_integration_plan.md` — what goes in Act 4 and how. All
>    four ANSWER slots signed by Omer (2026-08-06/07). **Authoritative over
>    every handoff on which numbers Act 4 quotes.**
> 3. `planbench_wt_prereg.md` — the binding design (tag `prereg-planbench-wt-v1`
>    + restart record 1).
> 4. `results/planbench/wt-anthropic-20260801/` — the committed data archive;
>    `python3 planbench/analysis/verify_promotion.py` re-derives every published
>    number from it and checks the 71-file MANIFEST.

## Headline numbers a fresh session may cite (all verified against graded corpora)

| cell (n=600 each, one Rosetta-VAL grader epoch) | result |
|---|---|
| Mystery WT / matched-NT | **71.8** [68.1, 75.3] / 0.0 [0.0, 0.6] — McNemar p=3.6e-130 |
| clean WT / matched-NT | **68.3** [64.5, 71.9] / 47.8 [43.9, 51.8] — Δ+20.5pp, b=202/c=79, p=1.38e-13 |
| formalization_match clean / Mystery | 96.3 [94.5, 97.6] / **97.8** [96.3, 98.7] (branch req. MET) |
| bare-NT clean / Mystery | **43.8** [39.9, 47.8] (CI-disjoint above GPT-4 34.3 [30.6, 38.2]) / 0.7 [0.3, 1.7] |
| §9-A ladder (Mystery) | native 0.7 / scaffold-only 0.0 / directive-only **0.5** / +tools **71.8** |
| clean domain-equivalence mechanism | P(solvable \| domain-equiv) 99.5% vs 1.6%; 0/35 no-match trials correct |

The clean-WT row is the **first-draw** reading — Omer's ratified 2026-08-06
decision ("the 1 pt does not worth the ambiguity"). The last-attempt reading
(69.7 / +21.8pp / p=2.7e-15) survives only in results-doc deviation row 1 and
must never be quoted as the headline. Earlier handoff snapshots still show it;
they are wrong on this point.

## Status of the three tasks this doc was written to hand off — ALL DONE

| task | outcome |
|---|---|
| 1 — stripped-block regrade | DONE 08-06/07. Mystery-NT true 4.3; the 26/600-vs-GPT-4 coincidence audited and settled **GENUINE** (8/8 flip IDs VAL-confirmed). Evidence: `results/planbench/wt-anthropic-20260801/verification/`. |
| 2 — open the PR | DONE. **PR #93**, open against main, plus two review passes applied (see CHANGELOG 08-06/07 and the 08-11 second pass). |
| 3 — paper integration | Plan DONE and signed (`planbench_wt_paper_integration_plan.md`, 4/4 slots). Prose starts only after PR #93 merges. |

The per-task instructions those rows replaced are in git history. Exactly one
open item remains for this arm — the Act 4 prose below — and it is gated on
PR #93 merging. Everything after that section is reference (traps), not action.

## The only open work: Act 4 prose (gated on PR #93 merging)

The integration plan is written and all four slots are signed — read
`planbench_wt_paper_integration_plan.md` for what goes where and which numbers.
It is authoritative; the rules below are the ones that bind while writing and
are NOT restated there.

1. **Branch/workflow:** paper edits go on `paper/aaai27` ONLY, after this arm's
   branch is merged to main. Read `development/paper-git-overleaf-instructions.md`
   BEFORE any paper work; always `sync_overleaf.sh pull` (+ commit) before `push`;
   never force-push to Overleaf.
2. **Claim shape (prereg §1 + amendment I):** WT is the labelled SECONDARY claim,
   never Act 4's headline. The bare claim "tools rescue Mystery" is already
   published (Huang & Zhang ACL 2025); ours is a **replication with an ablation the
   field has not run** — matched-scaffold control + directive-only rung, VAL
   grading on canonical instances, Wilson CIs + paired tests, the
   formalization-boundary metric, delegation mediator, measured $/trial.
3. **Amendment M:** GPT-4 is a labelled published reference line at stated
   epoch/denominator — never a comparator, no test against it (descriptive CI
   separation language only). Every external number prints pool size + grader on
   the same line ("Mystery Blocksworld" = ≥5 different pools).
4. **`/verify-claims` before ANY literature number enters prose.** The Act-4
   literature pass ran 2026-08-06 (commit e108bc2): 4 claims confirmed, 2
   corrected (La Malfa pool = 3×50/task and cite the retitled v2; Göbel's
   +3.0pp is a no-planner-roster design, not a choice). Anything outside that
   pass is still unverified. Also grep `development/` for PENDING specs before
   editing any existing claim — tex is not ground truth.
5. **Funnel placement (prereg §4 ANSWER):** FORMALIZE is a new leading bar at the
   head of the with-tools cascade, an instrument property absent where prompts
   embed PDDL (our own suite). Four bars for PlanBench, three for ours.
6. Style: `feedback_avoid_ai_writing_tells` binds (no em-dash habit, no "X, not Y"
   reversals, no triads); never mention page limits or recommend cuts.

## Traps that still bind (full lists in PLANBENCH_WT_HANDOFF.md §3/§5)

- Never `--ignore_existing` against any `pddl_copilot__anthropic*` engine dir;
  never `--specific_instances` to `response_evaluation.py`; never
  `--run_till_completion`.
- Aggregation: `build_table.acc()` divides by len(instances) regardless of what ran.
- Pairing key = `(config, instance_id)`; band cutpoints = amendment K n=600 row.
- The 06-22 bare-NT 500-pool graded t1 lives at
  `results/haiku-frontier/planbench/<cfg>/pddl_copilot__anthropic__claude-haiku-4-5/`
  (repo root), NOT under the plan-bench results tree (only t2 is there).
- Side-logs dedupe by LAST record per instance_id.
