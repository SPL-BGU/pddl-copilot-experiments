# PlanBench-WT archive (anthropic arms, runs 2026-08-01..06)

Committed record of the PlanBench with-tools (WT) arm: the graded corpora,
raw side-logs, and verification evidence behind every number in
`development/planbench/planbench_wt_results_20260803.md` and the Act-4
integration plan. Promoted from the machine-local `.local/wt_run/` +
gitignored `external/` trees on 2026-08-07 (ISS-026) so the results are
reproducible from a clone.

**Verify:** `python3 planbench/analysis/verify_promotion.py` (repo root)
re-derives every published count, Wilson CI, and McNemar test — including
the first-draw reading (410/600 = 68.3) that Act 4 quotes — from these files
alone, and checks `MANIFEST.sha256` over all 71 data files.

## Layout

- `graded/<config>/<engine>/task_1_plan_generation.json` — graded corpora
  (verbatim copies from `external/LLMs-Planning/plan-bench/results/`).
  Engines: `pddl_copilot__anthropic__…` (bare NT), `…anthropic-scaffold__…`
  (matched-NT), `…anthropic-tools__…` (WT), `…anthropic-directive__…`
  (ladder rung 3). The three `task_2_plan_optimality.json` files
  (blocksworld / logistics / mystery_blocksworld bare) are prereg-STRUCK t2
  probes kept for the record — never quote them as t1 results.
- `configs/*.yaml` — the four pool configs (declare start/end; denominators
  derive from these, ids are 2..end+1).
- `sidelogs/*.jsonl` — per-trial side-logs written by `planbench/engine.py`
  (append-mode; in `blocksworld__anthropic-tools.jsonl` the 18 duplicate ids
  ARE the 08-01 resume re-draws, file order = draw order — the basis of the
  first-draw reading, results-doc deviation 1). Plus
  `formalization_match_rows.jsonl`, the per-trial mechanism rows behind the
  §4 formalization_match numbers (578/587 match, 0/35 no-match correct).
- `verification/` — evidence from the three 2026-08-06 $0 checks:
  `val-spotcheck/` (8/8 stripped-regrade flip IDs re-validated by direct VAL
  calls; settles the GPT-4 26/600 coincidence as genuine),
  `firstdraw-stats/` (independent first-draw recompute), `oldstack-regrade/`
  (completion half re-graded under py3.12 + tarski 0.7.0 — 200/200 verdicts
  identical).
- `MANIFEST.sha256` — sha256 over every file above.

## What is NOT here

- The 500-pool bare-NT t1 corpora (clean 205/500 etc.) — already tracked at
  `results/planbench/../../haiku-frontier/planbench/`. The 600-pool bare
  union = that tree + the `*_3` bare cells here.
- The upstream harness (`external/LLMs-Planning`): clone + patch via
  `planbench/setup.sh` + `planbench/apply_patches.py`. Provenance of the
  epoch that graded these corpora:
  - fork commit `0378bfeb554e73d08c7e2435c79bb22caea93112`, patched via
    `apply_patches.py` (response_generation.py) only;
  - grader files (byte-identity of the grading epoch):
    - `plan-bench/response_evaluation.py`
      `12f14c4b4f3feb2e5e6296c5ce978526b48226e1556d02970dfe523846990712`
    - `plan-bench/utils/__init__.py`
      `5fd5910780e014fc2f74e9ebfc01ade9f059870ebbe56b3b024fc8adbd64e39b`
    - `plan-bench/utils/text_to_pddl.py`
      `9589950148c6893884d00beeea3790731e2dc43413c76ea6a808797b6b10eb20`
  - Rosetta-VAL binary (`planner_tools/VAL/bin/MacOSExecutables/validate`,
    Mach-O x86_64)
    `44a07d6d3b2917c7c3df8e3932a3b895a8062b4e0f5fa0343f9f1ad409c4a9fe`
  - domain files: clean
    `7bc3adedadbc3165c0c4372633305dcfb3238c205a5af0c18b8bc0ec2399a468`,
    mystery
    `ed9a88b4206197d12e825342fe646057d31eaed9b5927a245be7f31b46f3fcf9`
  - Interpreter stacks: run/grade epoch py3.14 + tarski 0.9.1
    (`planbench/requirements-wt.txt`); the 06-22 bare-NT 500-half used
    py3.12 + tarski 0.7.0 — demonstrated verdict-invariant
    (`verification/oldstack-regrade/`, 200/200).

## Reading rules

Endpoint is delivered `llm_correct`, treatment policy (missing/empty =
failure), denominator = declared pool (600 per union cell). Act 4 quotes
clean WT FIRST-DRAW: 410/600 = 68.3 [64.5, 71.9], paired Δ +20.5pp,
b=202/c=79, p=1.38e-13 (decision 2026-08-06); the last-attempt 418/600 =
69.7 stays in deviation row 1. WT cells never share a table with GPT-4 rows
(prereg rule 5). Analysis scripts live in `planbench/analysis/`.
