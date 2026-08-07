# PlanBench-WT — final-phase handoff (state as of 2026-08-06)

> **Entry point for a fresh session: `/resume-verify` this file.**
> The WT arm's EXPERIMENTS ARE ALL DONE. Confirmatory verdict **RESCUE, SUPPORTED**;
> mechanism branch FINAL via formalization_match; amendment N's four-rung ladder
> complete; bare-NT rows completed to n=600; **both ANSWER slots signed by Omer
> (accept + accept) → paper prose UNBLOCKED**. Everything is committed on
> `planbench-wt-significance-brief` (24 commits ahead of main, unmerged).
> Read `planbench_wt_results_20260803.md` for the full record — it is
> self-contained. Deep background/traps: `PLANBENCH_WT_HANDOFF.md`;
> superseded ordered list: `PLANBENCH_WT_NEXT_STEPS_HANDOFF.md` (close-out header).
> Spend: arm cumulative ≈ $46.2 of $170. No further paid runs are planned or needed.

**Omer's directive for this session (2026-08-06): run the regrade, open the PR,
integrate the paper.** Recommended order below — regrade first (free, hardens a
number the paper will cite), PR second (paper work should reference merged state),
paper last (it has its own branch + sync workflow).

## Headline numbers a fresh session may cite (all verified against graded corpora)

| cell (n=600 each, one Rosetta-VAL grader epoch) | result |
|---|---|
| Mystery WT / matched-NT | **71.8** [68.1, 75.3] / 0.0 [0.0, 0.6] — McNemar p=3.6e-130 |
| clean WT / matched-NT | **69.7** [65.9, 73.2] / 47.8 [43.9, 51.8] — p=2.7e-15 |
| formalization_match clean / Mystery | 96.3 [94.5, 97.6] / **97.8** [96.3, 98.7] (branch req. MET) |
| bare-NT clean / Mystery | **43.8** [39.9, 47.8] (CI-disjoint above GPT-4 34.3 [30.6, 38.2]) / 0.7 [0.3, 1.7] |
| §9-A ladder (Mystery) | native 0.7 / scaffold-only 0.0 / directive-only **0.5** / +tools **71.8** |
| clean domain-equivalence mechanism | P(solvable \| domain-equiv) 99.5% vs 1.6%; 0/35 no-match trials correct |

## Task 1 — [FREE, LOCAL] Stripped-block regrade of the injected Mystery-NT trials

Hardens the signed ANSWER slot (b) (audit 2). The Mystery **matched-NT** cells
(engine `pddl_copilot__anthropic-scaffold__claude-haiku-4-5`, configs
`mystery_blocksworld` + `mystery_blocksworld_3`) had 479/600 trials where the
benchmark extractor scraped extra actions out of narration ("injection" = extracted
action count > actions inside the model's own `[PLAN]..[PLAN END]` block — wrinkle 2
definitions in the NEXT_STEPS handoff; the counting logic lives in
`.local/wt_run/analyze_confirmatory.py`, which also carries a COSMETIC ×100 printf
bug in per-cell percents — fix before reuse, Wilson columns are correct).

**Spec:** for each of the 600 trials, re-extract using ONLY the text inside the
model's `[PLAN]..[PLAN END]` block (empty/no block → failure), run the same
`text_to_plan` conversion the grader uses, then VAL — same env as
`.local/wt_run/grade_all.sh`: `VAL=<repo>/external/LLMs-Planning/planner_tools/VAL/
bin/MacOSExecutables`, cwd `external/LLMs-Planning/plan-bench`, `PYTHONPATH=<repo>`,
`.venv-planbench-wt` python. **Write a NEW side script** (e.g.
`.local/wt_run/stripped_block_regrade.py`); do NOT overwrite the graded corpora and
do NOT re-run `response_evaluation.py` with modified inputs in place. Expected:
stays ~0 correct. Deliverable: a short dated subsection appended to
`planbench_wt_results_20260803.md` (audit 2 hardening) + commit. If it does NOT
stay ~0, that is a finding — report it, do not massage it; slot (b) is signed on
robustness grounds that do not depend on the exact 0, but the memo must say what
was measured.

## Task 2 — Open the PR for `planbench-wt-significance-brief`

- 24 commits ahead of main; carries CODE (`planbench/engine.py` +369 lines: WT/
  scaffold/directive backends; `apply_patches.py` patch 6; `build_table.py` engine
  entries) plus all prereg/results docs — the doc-only no-PR exception does NOT
  apply. Commit discipline: open a PR, never merge to main without one; Omer
  merges after review.
- `gh pr create` against main with a summary of: prereg + ratification trail,
  confirmatory RESCUE result, formalization_match, ladder, bare-NT completion,
  measured costs. No Claude/co-author credits anywhere.
- Do NOT touch `31b84ab` / nt-ster H4 files — parallel workstream, not this branch's
  business. If rebase conflicts appear against main, stop and ask Omer rather than
  resolving experiment-adjacent files silently.
- Machine-local caveat for the PR text: graded corpora under
  `external/LLMs-Planning/plan-bench/{responses,results}/` and everything in
  `.local/wt_run/` are gitignored and exist ONLY on Omer's laptop — irreplaceable
  without re-spend; the PR ships code + docs, not data.

## Task 3 — Paper integration (Act 4 secondary claim)

Prose is UNBLOCKED (both slots signed 2026-08-06) and Omer has now PROMPTED the
integration — but plan-first still applies: draft an integration plan (what goes
where, which numbers, which tables), get Omer's sign-off on the plan, then write.
Binding rules, none waivable:

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
4. **`/verify-claims` before ANY literature number enters prose.** Currently
   flagged unverified-for-prose: Göbel +3.0pp, published Mystery bands, Valmeekam
   4.3%, LLMFP replication numbers, Planetarium 96.1/94.4/24.8, La Malfa
   arXiv:2512.09629. Also grep `development/` for PENDING specs before editing any
   existing claim (tex is not ground truth).
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
