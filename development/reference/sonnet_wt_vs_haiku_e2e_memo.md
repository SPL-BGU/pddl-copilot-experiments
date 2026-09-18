# Sonnet WT vs Haiku — the with-tools capability ladder at the delivered-answer level

**Date:** 2026-07-13
**Corpora:** `results/sonnet-frontier/sweep5v2-with-tools` (canonical, v11, 1520 trials,
$90.75, 0 infra) vs `results/haiku-frontier/sweep5v2-with-tools` (same design);
no-tools baselines are the existing Sonnet/Haiku NT corpora **sliced to v11**
(D3 decision, zero-cost filter). All numbers are `e2e_strict` from the D7/D7b/D8/**D9**
overlay (`tools/e2e_regrade.py`, re-run repo-wide 2026-07-13), Wilson 95% CIs on
determinate rows, `[low, high]` bounds where snapshot-censored. Sonnet WT-anon was
deliberately not run (decision 2026-07-12); no contamination contrast exists for
Sonnet WT and none is claimed.

**Why a D9 was needed first (grading, not behavior).** The first Sonnet regrade
(2026-07-13 morning, D7/D8 rules) reproduced the exact artifact class retracted for
Haiku on 07-12: solve delivered 55.0 (42/100 `no_plan_extracted`) and simulate
delivered [5.0, 8.0] (71 `trajectory_mismatch`) against tool-verified 100.0/99.0.
Inspection showed both are *format coverage* failures of the D7 tolerance, which was
tuned on Haiku's formats: Sonnet delivers solve plans as a **markdown table** whose
action cell is a backticked s-expression, and simulate trajectories as **one fenced
JSON block per step** (D7 graded block 0 — a single step — against the full oracle
trace). D9 (see `tool_call_vs_final_output_grading.md`) widens extraction to cover
both, keeps the oracle as the false-positive safety net, and adds the solve-style
at-cap pre-censor to simulate. Applied identically to both arms and all corpora;
the repo-wide diff moved only solve/simulate rows, zero validate_* rows.

## Headline table (canonical corpus, variant 11, e2e_strict)

| task | Sonnet NT | Sonnet WT delivered | Sonnet WT tool-ver | gap | Haiku NT | Haiku WT delivered | Haiku WT tool-ver | gap |
|---|---|---|---|---|---|---|---|---|
| validate_domain | 93.3 [87.4, 96.6] | 95.8 [90.6, 98.2] | 95.8 | +0.0 | 87.5 [80.4, 92.3] | 98.3 [94.1, 99.5] | 98.3 | +0.0 |
| validate_problem | 86.5 [81.1, 90.6] | 98.0 [95.0, 99.2] | 98.0 | +0.0 | 73.0 [66.5, 78.7] | 96.5 [93.0, 98.3] | 96.5 | +0.0 |
| validate_plan | 97.1 [95.9, 98.0] | 100.0 [99.6, 100.0] | 99.9 | −0.1 | 91.5 [89.6, 93.1] | 98.8 [97.9, 99.3] | 98.9 | +0.1 |
| solve | 29.0 [21.0, 38.5] | 95.0 [88.8, 97.8] | 100.0 | +5.0 | 22.0 [15.0, 31.1] | 95.0 [88.8, 97.8] | 100.0 | +5.0 |
| simulate | [0, 100] (100% censored) | [49.0, 62.0] (13 censored; det 56.3, n=87) | 99.0 | ≈37–50 | [0, 100] (100% censored) | [52.0, 64.0] (12 censored; det 59.1, n=88) | 97.0 | ≈33–45 |

n per task: validate_domain 120, validate_problem 200, validate_plan 1000, solve 100,
simulate 100. NT simulate is 100% censored on both models (the NT canonical corpora
are 500-char-snapshot runs); the ~$0.3 batch re-run at 16K remains the cheap
de-censoring follow-up.

## Verdicts on the three Track-A questions

**1. Does the tool-verified-vs-delivered gap reproduce at Sonnet tier? Yes, and it is
task-shaped, not model-shaped.** Validation gaps are ~0 on both models (a verdict is a
short string the model always restates). solve delivered is **95.0 on both models with
an identical +5.0pp gap** against a 100.0 tool-verified ceiling. simulate keeps a large
gap on both (Sonnet ≥37pp, Haiku ≥33pp at the band edges). The surviving story is
unchanged and now holds on two tiers: **delivered fidelity degrades with the length of
the answer that must be restated** — verdict (words) < plan (lines) < trajectory
(full state dumps).

**2. Does Sonnet transcribe long outputs better than Haiku? No.** The prediction was
that a stronger model would close the solve/simulate transcription gap. It does not:
solve is exactly tied (95.0 vs 95.0, same 5-failure count), and the simulate bands
overlap almost completely ([49, 62] vs [52, 64]). The gap is a property of the task's
output length interacting with the output budget, not of model strength in this range.

**3. Does the validation tool-lift shrink as the model strengthens? Yes — the ladder
holds.** Delivered-level lift (WT − NT):

| task | Haiku lift | Sonnet lift | Sonnet lift CI-separated? |
|---|---|---|---|
| validate_domain | +10.8 | +2.5 | **no** (CIs overlap: 93.3 [87.4,96.6] vs 95.8 [90.6,98.2]) |
| validate_problem | +23.5 | +11.5 | yes |
| validate_plan | +7.3 | +2.9 | yes (97.1 [95.9,98.0] vs 100.0 [99.6,100.0]) |

All three Haiku lifts are CI-disjoint. At Sonnet tier the lifts shrink by roughly half
to three quarters, and validate_domain loses significance outright. This is the
capability-ladder prediction from the 2026-06-19 probe ("lift grows as the model
weakens") surviving end-to-end grading. solve is the counterpoint: the delivered
solve lift *grows* slightly with tier (Haiku +73.0, Sonnet +66.0 — both enormous and
CI-disjoint) because the NT baseline stays low for both; tools lift solve delivered
~3–4× at either tier.

## Mechanism notes

**solve (Sonnet, 5/100 delivered failures, 0 omissions).** After D9, every Sonnet solve
response contains an extractable plan (extraction: 42 table, 31 tolerant-list,
27 strict) — Sonnet never *drops* the plan the way the retracted reading claimed; all
5 failures are `plan_invalid`, i.e. transcription errors while restating the
tool-validated plan into the final answer (block-grouping p02, counters p01, drone p04,
tpp p05, zenotravel-numeric p01). Haiku's 5 failures: 3 invalid + 2 omitted. The +5.0pp
solve gap on both models is therefore almost entirely *copy fidelity*, not omission.

**simulate (Sonnet, 51/100 not delivered-ok).** Split of the failure mass:
29 output-budget truncations (`done_reason=length`: 13 censored at the 16K snapshot cap
+ 16 determinate fails whose trajectory was cut mid-stream) vs 22 clean-completion
fails (12 `format_parse_fail` — the answer is prose/tables with no coercible JSON
trajectory, e.g. a final-positions table; 10 `trajectory_mismatch` — wrong state
content, e.g. barman p02 delivers 15/15 steps with a state error). The single
`trajectory_ok` with `done_reason=length` delivered the full trace before the cutoff.
So even at Sonnet tier, a model that runs the simulation perfectly through tools
(99.0 tool-verified) fails to hand back the full trace roughly half the time, mostly
because the trace does not fit the output budget it allots itself.

**validate_plan inversion (curiosity, n=1).** Sonnet's one `tool_verified=False`
validate_plan row (block-grouping p03 v5) still delivered the CORRECT verdict —
delivered 100.0 > tool-verified 99.9. The model recovered from a wrong/failed tool
interaction in its final answer.

## Paper implications (rewrites owed, per next_steps item 5 — needs Omer's go)

- The "drives the tool then drops the answer" claim stays retracted; the replacement
  claim is now two-tier: *delivered fidelity is length-dependent* (0pp verdicts, 5pp
  plans, ≥33pp trajectories — same shape on Haiku and Sonnet).
- The with-tools capability ladder can now be stated end-to-end: validation lift
  shrinks with model strength (and loses significance on validate_domain at Sonnet
  tier); generative-task lift survives at both tiers.
- The simulate sole-source-floor rewrite should cite the frontier delivered bands
  ([49,62] / [52,64]) as the with-tools delivered picture alongside the corrected
  open-roster numbers.
- Cost bookkeeping: Sonnet WT $90.75 measured (est. was ~$96); frontier budget spent
  ≈$167.4 of $238.

## Provenance / repro

```bash
python3 tools/e2e_regrade.py results/haiku-frontier results/sonnet-frontier   # (part of the 07-13 repo-wide re-run)
python3 .claude/skills/analyzer/scripts/e2e_pooled.py                          # pooled table
```

Overlay rows carry `extraction` ∈ {strict_lines, tolerant_lines, table_lines, json} /
{whole, fenced_block, fenced_concat} so format drift stays measurable per model.
The pre-D9 overlay snapshot used for the row-level diff lived in the session
scratchpad; the diff summary is recorded in `tool_call_vs_final_output_grading.md` §D9.
