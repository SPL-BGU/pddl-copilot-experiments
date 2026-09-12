# PlanBench-WT analysis layer

Scripts that computed the PlanBench-WT numbers in
`development/planbench/planbench_wt_results_20260803.md`. Promoted from
machine-local `.local/wt_run/` on 2026-08-07 (ISS-026). Data lives in
`results/planbench/wt-anthropic-20260801/` (see its README for provenance);
side-log location is overridable via `WT_SIDELOG_DIR` (defaults to the
committed archive's `sidelogs/`).

Byte-faithful to the scripts that ran, with exactly two deliberate deltas:
the cosmetic ×100 per-cell-percent printf bug in `analyze_confirmatory.py`
is fixed (Wilson columns were always correct), and hardcoded/`__file__`-
relative side-log paths were replaced by the `WT_SIDELOG_DIR` default so the
scripts run from a clone.

## Quick check (no VAL needed)

    python3 planbench/analysis/verify_promotion.py

Data-only: re-derives every published count / CI / McNemar (incl. the
first-draw 410/600 = 68.3 that Act 4 quotes) from the committed archive and
verifies its MANIFEST. Run it after any touch of the archive.

## The scripts as they ran

Full re-runs need the patched upstream tree (`planbench/setup.sh` +
`planbench/apply_patches.py`) because they import `utils.text_to_pddl` /
tarski and call VAL. Invocation for the analysis trio (cwd =
`external/LLMs-Planning/plan-bench`, venv `.venv-planbench-wt`):

- `analyze_confirmatory.py` — prereg §3/§6 confirmatory analysis: per-cell
  counts, McNemar+Holm, band verdict, apparatus criterion, mediators.
- `stripped_block_regrade.py` — deviation-5 follow-up: re-grades matched-NT
  Mystery from the `[PLAN]` block only (26/600 = 4.3; provenance audited +
  8/8 flips VAL-confirmed 2026-08-06, see archive `verification/`).
- `formalization_match.py` — §4 mechanism layer; writes/reads
  `formalization_match_rows.jsonl` (578/587 match, 0/35 no-match correct).
- `verify_gold_reconstruction.py` — gold-plan reconstruction audit
  (1200/1200) + side-log sha256 join check.

Run scripts (`run_confirmatory.sh`, `run_bare_nt_completion.sh`,
`run_directive_arm.sh`) are the as-run records of the API runs — arm
identity, env, sequencing. Do not re-run without a fresh prereg decision;
`run_confirmatory.sh` spends real API money.

Verification artifacts (as-run evidence for the 2026-08-06 checks; paths
inside are as they executed, not portable): `firstdraw_analysis.py`
(first-draw reconstruction + stats), `val_spotcheck.py` (independent
re-extraction + direct VAL validation of stripped-regrade flips).
