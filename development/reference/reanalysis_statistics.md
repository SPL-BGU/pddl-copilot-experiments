# Statistics re-analysis (weakness C9)

*Written 2026-10-02. Local, read-only over results, no spend. Nothing in `paper/` was
edited and no existing tracked file was changed. Scripts: `tools/reanalysis/`. Full
machine-readable output: `tools/reanalysis/out/`.*

Scope: the three headline open models (Qwen3.5-9B, Gemma-26B, Qwen3.6-35B), thinking
off, canonical corpus `results/sweep5v2-live` (plus `results/sweep6-live` for the
contamination check). Two contrasts per task: **availability** (no tools vs tools with
the plain wording) and **steering** (tools plain vs tools steered). That is 3 models x
5 tasks x 2 contrasts = 30 comparisons.

Every number is given on **two surfaces**, because the paper uses both:

- **Mechanism layer**: the harness `success` field. In the tool arms this is
  tool-verified success (the tool was called and its result was right). Exact on every
  row.
- **Delivered**: the final answer the user gets (`e2e_strict` in the overlay). In the
  tool arms of this corpus most answers were stored cut at 500 characters, so a cell is
  a bound `<low, high>`, not a point. Censored rows are never counted as successes or
  as failures. A claim on a bounded cell is tested at its worst-case end.

---

## What we found, and what it changes in the paper

**0. The starting figures reproduce.** 15 of 15 checks match `NUMBERS.md` and the tex
tables: 622/3000 and 2808/3000 invocation, 617 tool-verified, 0.206 -> 0.926, the
unaided simulate 0/3,000 with its failure mix, all 75 thinking-off cells of
`pooled_e2e_table.csv`, and the five pooled contamination rows. No mismatch to explain.

**1. Domain clustering is much larger than the sqrt(2.7) widening allows for, on single
rates.** The sqrt(2.7) factor matches the three-wordings clustering well (median
variance inflation 2.0, max 2.7). It does not cover the fact that instances come from
20 domains. For clustering by domain the median inflation is 2.8 and the maximum is 78.
The domain bootstrap interval is wider than the paper's widened Wilson interval in 18
of 45 headline cells on the mechanism layer and 29 of 45 on the delivered surface. The
gap is worst on validate_plan (150 trials per domain per arm): for example Gemma
tools-plain is 20.6%, paper interval [18.3, 23.0], domain bootstrap [8.9, 33.9]. The
domain interval is at least as wide as the problem-instance interval in 40 of 45 cells,
so **domain governs**, as it does in the steering control.
*Change:* the sentence that the Wilson intervals are made safe by the sqrt(2.7) factor
is not true for single-arm rates on validate_plan; those intervals are two to five
times too narrow.

**2. Pairing rescues almost every arm contrast, and two headline verdicts change.**
The arms share instances, so most of the domain-to-domain variation cancels in the
difference. With paired differences and a domain-clustered 95% interval (mechanism
layer, 30 headline contrasts):

- 18 favorable verdicts hold, all with intervals far from zero for the large effects
  (+50 to +92 points).
- The Gemma validate_plan harm from mere availability holds: -67.3 [-79.7, -54.8].
- The Gemma validate_plan steering gain holds: +72.0 [+57.5, +86.5].
- **Changes to not significant:** Qwen3.5-9B validate_plan steering, +2.9 points, paper
  says favorable even after sqrt(2.7); clustered interval [-0.6, +6.3].
- **Changes to not significant:** Qwen3.6-35B validate_plan availability, -8.7 points,
  paper's rule says significant-against even after sqrt(2.7); clustered interval
  [-19.0, +1.5].
- The -5 point validate_problem steering dip (Qwen3.5-9B) stays not significant
  ([-10.9, +0.9]), which agrees with the paper's own flag.

On the delivered surface the six favorable availability cells all keep intervals that
exclude zero at the worst-case end, including Gemma validate_problem, which the paper
marks as failing the sqrt(2.7) check (paired interval [+0.9, +31.6]). The other 24
delivered cells stay UNDECIDED, as in the paper. No delivered verdict flips direction.

**3. The mixed model: the direction holds, the quoted uncertainty does not.** The
original fit is `.local/glmm_feasibility_probe.py` (untracked), a mean-field
variational fit in statsmodels. Rerunning it gives 7.53 with SD 0.096, so the paper's
"+7.5, SD 0.10" is that output. A standard maximum-likelihood fit of the same model
gives **log-odds +7.80, SE 0.29, 95% interval [7.23, 8.37]** (profile interval
[7.25, 8.40]). So the point estimate is about right and the SD of 0.10 was about three
times too small, as suspected. The paper's sentence "strongly favorable and
significant" still holds under every estimator tried. Two further points: the GEE the
sentence says "agrees" estimates a different quantity (population-averaged log-odds
+3.87, not +7.5), so it agrees on sign and significance only; and when the clustering
is on domain rather than on instance the evidence is z of about 6, not 78 or 27.

**4. Multiplicity: the "stricter than Bonferroni" argument does not hold, but most
verdicts survive a real correction.** The family really is 30 contrasts per surface for
the headline set (60 if both surfaces count, 100 for the full five-model roster with
thinking off, 200 with both reasoning modes). Two verdicts that pass the paper's
"z of about 3.2" rule fail an ordinary uncorrected clustered test (item 2), so that
rule is not stricter than Bonferroni in practice. Applying Holm at 0.05 on top of the
clustered paired tests:

- Mechanism layer, family of 30: all 19 clustered verdicts survive. Two survive only
  just (Qwen3.5-9B validate_plan availability +13.4, adjusted p = 0.046; Gemma
  validate_domain availability +19.7, adjusted p = 0.050).
- If the family is the 60 contrasts on both surfaces, those two and Qwen3.6-35B
  validate_plan steering (+17.1, adjusted p = 0.063) no longer survive. The other 16,
  including every +50 to +92 point effect and both Gemma validate_plan results, survive
  any family size up to 200.
- Delivered surface, family of 30: 3 of the 6 favorable cells survive (Qwen3.5-9B
  validate_domain, Qwen3.5-9B validate_problem, Qwen3.6-35B validate_domain). Three do
  not: Gemma validate_domain (p = 0.031), Gemma validate_problem (p = 0.032),
  Qwen3.5-9B solve (p = 0.036). So the delivered validate_domain row reads favorable
  for two of three models after correction, not three of three.

**5. Equivalence tests, margin +/-5 points, 90% clustered interval.**

- *Contamination, pooled over the five tasks, thinking off:* **criterion met for all
  five models** (widest interval: Qwen3.5-4B, [-4.33, +0.29]).
- *Contamination, per task, headline models (15 cells):* criterion met in 10, but 6 of
  those 10 sit on a floor or ceiling where the test carries almost no information (all
  three simulate cells are 0% vs 0%). **Criterion met with real information in 4 cells;
  criterion not met (unresolved) in 5 cells**: validate_domain for all three models and
  validate_problem for Qwen3.5-9B and Gemma. In those five the interval reaches +6.9 to
  +9.4 points. "Zero CI-disjoint cells" is therefore not a per-task null. One cell has
  a 90% interval that excludes zero while staying inside the margin: Qwen3.6-35B
  validate_plan, anonymized minus canonical = -1.87 [-3.67, -0.07].
- *Contamination, thinking on:* pooled criterion not met (unresolved) for Qwen3.5-4B,
  Qwen3.5-9B and Qwen3.6-35B.
- *vLLM 0.20.2 vs 0.22.0:* the data are on disk. Pooled **criterion met**: +0.43
  [-0.27, +1.13]. By task and arm, 8 of 10 cells meet it against the first 0.22.0 run
  and 10 of 10 against the second. Two runs of the *same* version meet it in only 7 of
  10 cells, and 4% of individual trials change outcome between any two runs, so the
  per-cell resolution is limited by run-to-run noise, not by the version.

**What does not change:** every large headline effect, the Gemma validate_plan harm and
its steering rescue, the direction of every delivered verdict, and the pooled
contamination and serving-version results.

---

## Table 0. Reproduction of the frozen figures

| check | got | frozen | match |
|---|---|---|---|
| Gemma validate_plan plain: called / n | 622 / 3000 | 622 / 3000 | yes |
| Gemma validate_plan steered: called / n | 2808 / 3000 | 2808 / 3000 | yes |
| Gemma validate_plan plain: tool-verified ok | 617 | 617 | yes |
| Gemma validate_plan plain: successes without a call | 0 | 0 | yes |
| Gemma validate_plan success plain -> steered | 0.206 -> 0.926 | 0.206 -> 0.926 | yes |
| Gemma validate_plan delivered bound, plain | <6.6, 99.6>, 2790 censored | <6.6, 99.6>, c2790 | yes |
| unaided simulate strict success (10 no-tools cells) | 0 / 3000 | 0 / 3000 | yes |
| unaided simulate failure mix | 1772 / 1202 / 26 | 1772 / 1202 / 26 | yes |
| Qwen3.5-9B validate_domain tools-plain delivered | 359/360, 1 censored | 359/360, c1 | yes |
| `pooled_e2e_table.csv`, 75 thinking-off cells (n, ok, censored, tool-verified) | 0 mismatches | 0 | yes |
| contamination pooled, canonical / anonymized, 5 models | 45.9/45.8, 58.2/56.1, 63.8/64.2, 74.3/75.2, 75.7/74.8 | same | yes |

Fields used. No-tools arm: `success` in `trials.jsonl` (online grade of the model's own
full answer). Tool arms, mechanism layer: `success` (tool-verified; identical to the
overlay's `tool_verified`). Tool arms, delivered: overlay `e2e_strict`, three-valued.
Summary files were not used (they carry n=0 stub rows). The stale mirror
`results/sweep5-cluster-20260530` was not read.

## Table 1. Single-arm rates: paper interval vs cluster bootstrap

Mechanism layer, thinking off, percent. Shown: the cells where the domain bootstrap is
clearly wider than the paper's widened Wilson interval (about 1.4 times or more). All 90 headline rows
(both surfaces) are in `tools/reanalysis/out/02_tables.md`, Table A, and
`02_rates.csv`.

| model | task | arm | rate | Wilson | Wilson x sqrt(2.7) (paper) | bootstrap: problem | bootstrap: domain (k=20) | variance inflation, domain |
|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | v_plan | no tools | 79.7 | [78.3, 81.1] | [77.3, 82.0] | [75.9, 83.5] | [73.7, 85.5] | 17.6 |
| Qwen3.5-9B | v_plan | tools plain | 93.2 | [92.2, 94.0] | [91.5, 94.5] | [89.7, 96.2] | [88.2, 97.4] | 28.1 |
| Qwen3.5-9B | v_plan | tools steered | 96.0 | [95.3, 96.7] | [94.7, 97.0] | [93.2, 98.4] | [91.9, 99.1] | 28.7 |
| Qwen3.5-9B | v_prob | tools steered | 90.2 | [87.5, 92.3] | [85.5, 93.4] | [86.2, 93.8] | [83.3, 95.5] | 7.1 |
| Gemma-26B | v_dom | no tools | 77.8 | [73.2, 81.8] | [70.0, 84.0] | [71.1, 84.2] | [65.6, 88.6] | 7.6 |
| Gemma-26B | v_plan | no tools | 87.8 | [86.6, 89.0] | [85.8, 89.6] | [84.7, 90.8] | [83.7, 91.4] | 11.8 |
| Gemma-26B | v_plan | tools plain | 20.6 | [19.2, 22.1] | [18.3, 23.0] | [14.8, 26.5] | [8.9, 33.9] | 78.4 |
| Gemma-26B | v_plan | tools steered | 92.6 | [91.6, 93.5] | [90.9, 94.0] | [88.0, 96.3] | [83.2, 98.7] | 77.9 |
| Qwen3.6-35B | v_dom | no tools | 67.8 | [62.8, 72.4] | [59.4, 75.1] | [61.1, 74.2] | [56.4, 78.3] | 5.6 |
| Qwen3.6-35B | v_plan | no tools | 90.9 | [89.8, 91.9] | [89.1, 92.5] | [87.9, 93.6] | [87.7, 93.9] | 9.3 |
| Qwen3.6-35B | v_plan | tools plain | 82.2 | [80.8, 83.5] | [79.8, 84.3] | [77.3, 86.7] | [72.6, 90.6] | 45.9 |

Which is wider, over the 45 headline arm cells per surface:

| surface | domain bootstrap wider than paper interval | problem bootstrap wider than paper interval | domain at least as wide as problem |
|---|---|---|---|
| mechanism | 18 / 45 | 9 / 45 | 40 / 45 |
| delivered | 29 / 45 | 10 / 45 | 38 / 45 |

Variance inflation relative to independent trials (38 non-degenerate mechanism cells):

| clustering | median | max | cells above 2.7 |
|---|---|---|---|
| instance (the three wordings) | 2.04 | 2.7 | 1 |
| domain (k=20) | 2.79 | 78.4 | 20 |

For solve, simulate and the smaller validate tasks the paper's widened interval is
usually the wider one, because those cells have only 15 to 30 trials per domain. Cells
at exactly 0% or 100% have a zero-width bootstrap interval; Wilson is the sensible
interval there.

## Table 2. Paired contrasts, mechanism layer

Delta = second arm minus first arm, points, over fixture-matched pairs (same instance,
same wording). "Clustered 95% CI" is the wider of the domain (k=20) and problem
cluster-robust t intervals; domain governs in 28 of 30 rows. p = cluster-t p-value of
the governing clustering. "Sign-flip" = exact randomisation test on the 20 domain
totals (smallest possible value 1.9e-06). "Paper rule" = disjoint Wilson intervals, then
the same after widening by sqrt(2.7).

| model | task | contrast | first arm | second arm | Delta | clustered 95% CI | domain bootstrap | problem bootstrap | p | sign-flip p | paper rule | paper rule x sqrt(2.7) | clustered paired | after Holm, m=30 | after Holm, m=60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | avail | 10.7 | 99.3 | +88.7 | [83.4, 93.9] | [83.7, 93.3] | [85.0, 92.0] | 9.1e-19 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | solve | steer | 99.3 | 100.0 | +0.7 | [-0.7, 2.1] | [0.0, 2.0] | [0.0, 2.0] | 0.330 | 1.000 | NS | NS | NS | NS | NS |
| Qwen3.5-9B | v_dom | avail | 25.6 | 100.0 | +74.4 | [64.0, 84.9] | [63.6, 82.5] | [67.2, 81.4] | 6.1e-12 | 3.8e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_dom | steer | 100.0 | 100.0 | +0.0 | [0.0, 0.0] | [0.0, 0.0] | [0.0, 0.0] | 1.000 | 1.000 | NS | NS | NS | NS | NS |
| Qwen3.5-9B | v_prob | avail | 65.7 | 95.2 | +29.5 | [22.2, 36.8] | [23.2, 36.5] | [24.0, 35.3] | 6.8e-08 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_prob | steer | 95.2 | 90.2 | -5.0 | [-10.9, 0.9] | [-11.2, -0.5] | [-8.2, -2.2] | 0.093 | 0.086 | AGAINST | NS | NS | NS | NS |
| Qwen3.5-9B | v_plan | avail | 79.7 | 93.2 | +13.4 | [5.0, 21.9] | [5.6, 21.2] | [9.0, 17.9] | 0.004 | 0.004 | FAV | FAV | FAV | FAV (adj. p 0.046) | **not significant** |
| **Qwen3.5-9B** | **v_plan** | **steer** | 93.2 | 96.0 | +2.9 | [-0.6, 6.3] | [0.5, 6.6] | [1.0, 5.1] | 0.097 | 0.020 | FAV | FAV | **NS** | NS | NS |
| Qwen3.5-9B | sim | avail | 0.0 | 65.0 | +65.0 | [55.9, 74.1] | [56.3, 72.7] | [59.0, 70.7] | 5.9e-12 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | sim | steer | 65.0 | 83.0 | +18.0 | [13.4, 22.6] | [13.7, 22.0] | [13.7, 22.0] | 1.4e-07 | 7.6e-06 | FAV | FAV | FAV | FAV | FAV |
| Gemma-26B | solve | avail | 7.7 | 99.3 | +91.7 | [87.3, 96.1] | [87.3, 95.3] | [88.3, 94.7] | 1.6e-20 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Gemma-26B | solve | steer | 99.3 | 98.7 | -0.7 | [-2.9, 1.6] | [-3.0, 1.0] | [-2.0, 0.7] | 0.541 | 1.000 | NS | NS | NS | NS | NS |
| Gemma-26B | v_dom | avail | 77.8 | 97.5 | +19.7 | [7.1, 32.4] | [8.9, 31.9] | [13.1, 26.7] | 0.004 | 0.001 | FAV | FAV | FAV | FAV (adj. p 0.050) | **not significant** |
| Gemma-26B | v_dom | steer | 97.5 | 98.3 | +0.8 | [-0.1, 1.8] | [0.0, 1.7] | [0.0, 1.9] | 0.083 | 0.250 | NS | NS | NS | NS | NS |
| Gemma-26B | v_prob | avail | 74.8 | 99.7 | +24.8 | [18.3, 31.3] | [19.0, 30.8] | [19.8, 30.2] | 1.7e-07 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Gemma-26B | v_prob | steer | 99.7 | 100.0 | +0.3 | [-0.1, 0.8] | [0.0, 0.8] | [0.0, 0.8] | 0.163 | 0.500 | NS | NS | NS | NS | NS |
| Gemma-26B | v_plan | avail | 87.8 | 20.6 | -67.3 | [-79.7, -54.8] | [-78.0, -55.3] | [-73.2, -61.2] | 6.7e-10 | 1.9e-06 | AGAINST | AGAINST | AGAINST | AGAINST | AGAINST |
| Gemma-26B | v_plan | steer | 20.6 | 92.6 | +72.0 | [57.5, 86.5] | [58.2, 84.5] | [65.5, 78.4] | 2.8e-09 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Gemma-26B | sim | avail | 0.0 | 91.7 | +91.7 | [85.9, 97.5] | [86.0, 96.7] | [87.0, 95.7] | 3.0e-18 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Gemma-26B | sim | steer | 91.7 | 90.7 | -1.0 | [-4.7, 2.7] | [-4.7, 2.0] | [-4.0, 1.7] | 0.577 | 0.719 | NS | NS | NS | NS | NS |
| Qwen3.6-35B | solve | avail | 9.3 | 63.0 | +53.7 | [45.7, 61.7] | [46.3, 61.0] | [47.7, 59.7] | 1.8e-11 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | solve | steer | 63.0 | 92.0 | +29.0 | [21.6, 36.4] | [22.3, 35.7] | [23.0, 35.0] | 1.1e-07 | 7.6e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_dom | avail | 67.8 | 98.9 | +31.1 | [18.4, 43.8] | [20.0, 43.1] | [24.7, 37.8] | 6.0e-05 | 1.9e-05 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_dom | steer | 98.9 | 99.7 | +0.8 | [-0.4, 2.1] | [0.0, 2.2] | [0.0, 1.9] | 0.186 | 0.500 | NS | NS | NS | NS | NS |
| Qwen3.6-35B | v_prob | avail | 75.7 | 96.8 | +21.2 | [15.5, 26.8] | [16.5, 26.2] | [15.7, 26.8] | 7.9e-08 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_prob | steer | 96.8 | 97.3 | +0.5 | [-1.1, 2.1] | [-0.5, 1.3] | [-1.2, 2.0] | 0.550 | 0.531 | NS | NS | NS | NS | NS |
| **Qwen3.6-35B** | **v_plan** | **avail** | 90.9 | 82.2 | -8.7 | [-19.0, 1.5] | [-18.5, 0.0] | [-14.2, -3.2] | 0.090 | 0.097 | AGAINST | AGAINST | **NS** | NS | NS |
| Qwen3.6-35B | v_plan | steer | 82.2 | 99.3 | +17.1 | [7.4, 26.8] | [8.9, 26.5] | [12.7, 21.9] | 0.002 | 3.8e-06 | FAV | FAV | FAV | FAV | **not significant** (adj. p 0.063) |
| Qwen3.6-35B | sim | avail | 0.0 | 74.7 | +74.7 | [65.1, 84.2] | [65.3, 83.0] | [68.7, 80.3] | 1.1e-12 | 1.9e-06 | FAV | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | sim | steer | 74.7 | 97.0 | +22.3 | [12.8, 31.9] | [14.3, 31.7] | [16.3, 28.3] | 1.0e-04 | 3.8e-05 | FAV | FAV | FAV | FAV | FAV |

Notes on the two changed rows. Both are on validate_plan, where domain clustering is
strongest. If one clusters only on problem instance, both would still read significant
(problem bootstrap [1.0, 5.1] and [-14.2, -3.2]); it is the 20-domain clustering that
removes them. Qwen3.5-9B validate_plan steering is borderline: the t interval includes
zero (p = 0.097) while the sign-flip test gives p = 0.020. Neither survives Holm.

## Table 3. Paired contrasts, delivered surface

Same layout. A bounded cell is `<low, high>`. The Delta bound takes censored rows at
their worst and best case. The interval is an envelope: its lower limit is the clustered
lower limit of the worst-case Delta, its upper limit the clustered upper limit of the
best-case Delta. A favorable verdict needs the worst case to stay above zero. p-values
are for the worst-case end, so they are conservative. Rows whose bounds straddle zero
cannot be tested and stay UNDECIDED (24 of 30; all in `02_tables.md`, Table B (dlv)).
Only the six decided rows are shown.

| model | task | contrast | no tools | tools plain | Delta bound | clustered 95% envelope | p (worst case) | paper rule | paper rule x sqrt(2.7) | clustered paired | after Holm, m=30 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | v_dom | avail | 25.6 | <99.7, 100.0> | <+74.2, +74.4> | [63.8, 84.9] | 6.1e-12 | FAV | FAV | FAV | FAV |
| Qwen3.5-9B | v_prob | avail | 65.7 | <92.2, 95.3> | <+26.5, +29.7> | [19.0, 36.9] | 5.8e-07 | FAV | FAV | FAV | FAV |
| Qwen3.6-35B | v_dom | avail | 67.8 | <91.9, 99.2> | <+24.2, +31.4> | [11.8, 43.7] | 6.2e-04 | FAV | FAV | FAV | FAV |
| Gemma-26B | v_dom | avail | 77.8 | <93.3, 98.1> | <+15.6, +20.3> | [1.6, 32.9] | 0.031 | FAV | FAV | FAV | **not significant** |
| Gemma-26B | v_prob | avail | 74.8 | <84.3, 99.8> | <+9.5, +25.0> | [0.9, 31.6] | 0.032 | FAV | UNDECIDED | FAV | **not significant** |
| Qwen3.5-9B | solve | avail | 10.7 | <26.0, 58.7> | <+15.3, +48.0> | [1.1, 65.6] | 0.036 | FAV | FAV | FAV | **not significant** |

The paper's delivered verdict table (`reference/job2_delivered_reframe_worknote.md`,
section 2) is reproduced exactly by the "paper rule" columns, including the Gemma
validate_problem knife-edge and the Qwen3.5-9B solve margin.

## Table 4. The mixed model on Gemma validate_plan, plain vs steered

6,000 trials, 1,000 instances, 20 domains. Success 0.206 -> 0.926. The 1,000 instances
split as: 571 fail all three plain and pass all three steered; 285 pass one or two
plain and all three steered; 45 fail everything; 41 pass everything; 58 other.

| fit | log-odds, steered vs plain | SE (or posterior SD) | 95% interval | z | what it estimates |
|---|---|---|---|---|---|
| Variational Bayes, random intercept per instance (the paper's fit, rerun) | +7.53 | 0.10 | [7.34, 7.72] | 78 | effect within an instance |
| **Maximum likelihood, same model, Gauss-Hermite quadrature (200 nodes)** | **+7.80** | **0.29** | **[7.23, 8.37]**; profile [7.25, 8.40] | 27 | effect within an instance |
| Conditional logistic, stratified on instance | +6.15 | 0.29 | [5.59, 6.72] | 21 | effect within an instance, no assumption on the instance effect |
| GEE, exchangeable, clustered on instance (k=1000) | +3.87 | 0.12 | [3.65, 4.10] | 34 | population-averaged |
| GEE, exchangeable, clustered on domain (k=20) | +3.87 | 0.64 | [2.63, 5.12] | 6.1 | population-averaged |
| Logistic regression, domain-cluster-robust SE, t(19) interval | +3.87 | 0.65 | [2.51, 5.24] | 5.9 | population-averaged |

Maximum-likelihood details: random-intercept SD 2.86; likelihood-ratio chi-square 4,410
on 1 df; the fitted model implies marginal rates 0.204 -> 0.931 (observed 0.206 ->
0.926); the estimate is the same to three decimals at 50, 200 and 400 quadrature nodes.
The quadrature code recovers known parameters on simulated data of the same shape
(truth 4.00, estimate 3.89, SE 0.11).

Same contrast as a plain paired difference in success rate: +72.0 points, 95% interval
[57.5, 86.5] clustered on domain, [65.4, 78.6] on problem, [69.8, 74.2] on instance.

Reading:

- The SD of 0.10 is an artifact of the variational method (mean-field approximations
  are known to understate posterior spread). The standard fit gives 0.29.
- The effect is strongly positive under every estimator, so the paper's qualitative
  sentence holds.
- +7.5 or +7.8 and +3.87 are not two estimates of one number. The first is the effect
  inside an instance, the second is the effect on the average rate. With a large
  instance-to-instance spread they differ by design.
- The conditional fit is lower (+6.15) than the random-intercept fit (+7.80). That is a
  sign the normal assumption for the instance effect fits poorly here (most instances
  are all-or-nothing). The exact size of the log-odds is therefore model-dependent; the
  sign and the significance are not.
- Honest uncertainty on this contrast is set by the 20 domains: z of about 6.

## Table 5. Multiplicity

Family sizes actually present:

| family | m | Bonferroni per-test level | matching two-sided z | clustered verdicts before correction | survive Holm | survive Bonferroni |
|---|---|---|---|---|---|---|
| headline, delivered surface | 30 | 1.7e-03 | 3.14 | 6 | 3 | 3 |
| headline, mechanism layer | 30 | 1.7e-03 | 3.14 | 19 | 19 | 17 |
| headline, both surfaces | 60 | 8.3e-04 | 3.34 | 25 | 19 | 19 |
| all five models, thinking off, both surfaces | 100 | 5.0e-04 | 3.48 | 40 | 28 | 27 |
| all five models, both modes, both surfaces | 200 | 2.5e-04 | 3.66 | 89 | 60 | 59 |

The paper's count of "about 30" is right for one surface of the headline set. It
leaves out the second surface, the two small models, the thinking-on robustness cells,
and the 25 contamination cells.

Why the paper's argument does not work, in numbers:

- The sqrt(2.7) factor is sized for the three-wordings clustering (Table 1: median
  2.0, max 2.7). It is fully used up there. Nothing of it is left over to pay for 30
  comparisons.
- It is too small for domain clustering in half the cells (Table 1).
- Two contrasts that pass "disjoint after sqrt(2.7)" fail a plain uncorrected clustered
  test (Table 2). A rule that were really stricter than Bonferroni could not do that.

Verdicts lost to Holm, headline set: on the mechanism layer none at m=30 and three at
m=60 (Table 2, last column). On the delivered surface three at m=30 (Table 3). Full
list including the two small models and thinking on: `02_tables.md`, Table C.

## Table 6. Equivalence: contamination (anonymized minus canonical, no tools, thinking off)

Trials paired on the exact trial key (the anonymized corpus keeps the same domain and
problem keys). 90% cluster-robust t interval, the wider of domain and problem
clustering. Criterion met when the whole interval lies inside (-5, +5). "Low
information" marks a cell whose canonical rate is below 10% or above 90%.

| model | cell | canonical % | anonymized % | Delta | governing 90% CI | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | 10.7 | 11.3 | +0.67 | [-2.57, +3.91] | 3.24 | 0.014 | criterion met |
| Qwen3.5-9B | v_dom | 25.6 | 26.7 | +1.11 | [-4.66, +6.88] | 5.77 | 0.129 | criterion not met (unresolved) |
| Qwen3.5-9B | v_prob | 65.7 | 69.3 | +3.67 | [-1.24, +8.58] | 4.91 | 0.322 | criterion not met (unresolved) |
| Qwen3.5-9B | v_plan | 79.7 | 79.3 | -0.40 | [-2.94, +2.14] | 2.54 | 0.003 | criterion met |
| Qwen3.5-9B | sim | 0.0 | 0.0 | +0.00 | [0.00, 0.00] | 0.00 | n/a | criterion met (floor: low information) |
| Qwen3.5-9B | **pooled** | 63.8 | 64.2 | +0.35 | [-1.52, +2.23] | 1.88 | <0.001 | **criterion met** |
| Gemma-26B | solve | 7.7 | 8.0 | +0.33 | [-3.80, +4.47] | 4.14 | 0.033 | criterion met (floor: low information) |
| Gemma-26B | v_dom | 77.8 | 80.6 | +2.78 | [-2.03, +7.58] | 4.80 | 0.217 | criterion not met (unresolved) |
| Gemma-26B | v_prob | 74.8 | 77.8 | +3.00 | [-1.82, +7.82] | 4.82 | 0.241 | criterion not met (unresolved) |
| Gemma-26B | v_plan | 87.8 | 88.2 | +0.40 | [-2.36, +3.16] | 2.76 | 0.005 | criterion met |
| Gemma-26B | sim | 0.0 | 0.0 | +0.00 | [0.00, 0.00] | 0.00 | n/a | criterion met (floor: low information) |
| Gemma-26B | **pooled** | 74.3 | 75.2 | +0.90 | [-0.71, +2.51] | 1.61 | <0.001 | **criterion met** |
| Qwen3.6-35B | solve | 9.3 | 9.7 | +0.33 | [-3.26, +3.93] | 3.59 | 0.018 | criterion met (floor: low information) |
| Qwen3.6-35B | v_dom | 67.8 | 70.3 | +2.50 | [-4.38, +9.38] | 6.88 | 0.269 | criterion not met (unresolved) |
| Qwen3.6-35B | v_prob | 75.7 | 76.7 | +1.00 | [-1.99, +3.99] | 2.99 | 0.016 | criterion met |
| Qwen3.6-35B | v_plan | 90.9 | 89.0 | -1.87 | [-3.67, -0.07] | 1.80 | 0.004 | criterion met (ceiling: low information) |
| Qwen3.6-35B | sim | 0.0 | 0.0 | +0.00 | [0.00, 0.00] | 0.00 | n/a | criterion met (floor: low information) |
| Qwen3.6-35B | **pooled** | 75.7 | 74.8 | -0.88 | [-2.22, +0.47] | 1.35 | <0.001 | **criterion met** |
| Qwen3.5-0.8B | **pooled** | 45.9 | 45.8 | -0.11 | [-0.55, +0.34] | 0.44 | <0.001 | **criterion met** |
| Qwen3.5-4B | **pooled** | 58.2 | 56.1 | -2.02 | [-4.33, +0.29] | 2.31 | 0.019 | **criterion met** |

Counts, thinking off:

| set | cells | criterion met | of which low information | not met (unresolved) |
|---|---|---|---|---|
| headline 3 models x 5 tasks | 15 | 10 | 6 | 5 |
| all 5 models x 5 tasks | 25 | 18 | 10 | 7 |
| headline, pooled | 3 | 3 | 0 | 0 |
| all 5 models, pooled | 5 | 5 | 0 | 0 |

Points to carry:

- The pooled result is real and tight, but 3,000 of 4,560 pooled trials are
  validate_plan, so "pooled" mostly means validate_plan.
- validate_domain is unresolved for all three headline models. It has 18 trials per
  domain, so the interval half-width is 4.8 to 6.9 points and a +/-5 criterion cannot
  be met there with this design, whatever the truth.
- The simulate cells are 0 against 0 on the strict grade (the shared-budget artifact in
  `NUMBERS.md`). They say nothing about contamination. Solve sits near 8 to 11%, where
  a drop of 5 points is barely possible.
- No correction is needed across cells for an equivalence claim of the form "all cells
  meet the criterion" (each cell must pass on its own). The claim that can be made is
  the pooled one.
- Thinking on (same table, `04_equivalence.md`): pooled criterion met for Qwen3.5-0.8B
  and Gemma (both on a floor), **not met (unresolved)** for Qwen3.5-4B (-4.56
  [-7.87, -1.25]), Qwen3.5-9B (-2.68 [-5.44, +0.08]) and Qwen3.6-35B (-3.27
  [-5.07, -1.47]). The paper already treats thinking on as budget-confounded.
- The frontier contamination rows (Sonnet, Haiku) were not re-tested here; the request
  was scoped to the open models.

## Table 7. Equivalence: vLLM 0.20.2 vs 0.22.0

Qwen3.5-0.8B, thinking off, with tools, canonical, 9,120 trials per run, harness
`success`. The two 0.22.0 runs exist only as backups in
`results/sweep5-cluster-20260601/` (`..._sweep5v2.v0220-bak` and `.v0220-2nd-bak`);
this is the provenance `NUMBERS.md` cites and is not the stale 20260530 mirror. The
0.20.2 run is the live canonical cell. The script reproduces the `NUMBERS.md` rates
(26.44 / 26.86, pooled +0.43).

| comparison | pooled Delta | governing 90% CI | pooled verdict | task x arm cells meeting criterion | trials whose outcome differs |
|---|---|---|---|---|---|
| 0.20.2 minus 0.22.0 run 1 (the one `NUMBERS.md` quotes) | +0.43 | [-0.27, +1.13] | **criterion met** | 8 / 10 | 395 / 9,120 (4.3%) |
| 0.20.2 minus 0.22.0 run 2 | +0.34 | [-0.41, +1.09] | **criterion met** | 10 / 10 | 381 / 9,120 (4.2%) |
| 0.22.0 run 2 minus 0.22.0 run 1 (same version twice) | +0.09 | [-0.39, +0.56] | criterion met | 7 / 10 | 366 / 9,120 (4.0%) |

Cells not meeting the criterion against run 1: solve plain (+2.67 [+0.22, +5.11]) and
validate_problem steered (-2.17 [-5.30, +0.97]). Against run 2 both meet it. The same
version run twice fails it in three cells (solve plain, solve steered, validate_problem
steered).

Reading: pooled, the criterion is met with a tight interval. The paired interval
([-0.27, +1.13]) is narrower than the unpaired one in `NUMBERS.md` ([-0.86, +1.71])
because the same trials are compared. Per cell, the check cannot separate a version
effect from run-to-run noise, since identical runs disagree by as much. As `NUMBERS.md`
already says, this cell is a 0.8B model and is not direct evidence for the 4B and 9B
cells that were actually served at 0.22.0.

---

## Method notes and limits

- **Clusters.** Domain = the 20 domain names. Problem = domain + problem (100 for
  solve, simulate and validate_plan; 120 for validate_domain; 200 for
  validate_problem). Instance = problem + plan label (1,000 for validate_plan, same as
  problem elsewhere). The paper's sqrt(2.7) addresses the instance level only.
- **Intervals.** Cluster-robust (cluster-sum) standard error with a t interval on k-1
  degrees of freedom; and a percentile cluster bootstrap, 10,000 resamples, fixed seed.
  With k=20 the percentile bootstrap runs slightly narrow, so the t interval is the one
  used for verdicts. The wider of domain and problem governs, as in the steering
  control.
- **Tests.** Cluster-t p-value of the governing clustering feeds Holm. The exact
  sign-flip test on the 20 domain totals is a distribution-free cross-check. Plain
  McNemar counts are in `02_contrasts.csv` for reference only; McNemar ignores
  clustering.
- **Twenty domains is few.** All domain-level intervals rest on k=20. They are honest
  about that, but they are not precise.
- **Delivered surface.** Tests are run at the worst-case end of the censoring bound,
  so delivered p-values are upper bounds and "not significant after Holm" there is a
  conservative reading.
- **Not done.** Thinking-on results and the two small models are in the CSVs and in
  `02_tables.md` Table C but are not discussed here. Frontier corpora were not
  re-analysed. The vote-counting rule (YES / MIXED / NO) and the +30 point "robust
  floor" in C9 were not part of this request.

## Reproduce

```bash
cd /Users/omereliyahu/personal/pddl-copilot-experiments/tools/reanalysis
../../.venv/bin/python 01_reproduce_frozen.py            # Table 0            -> out/01_reproduce.md
../../.venv/bin/python 02_cluster_paired_multiplicity.py # Tables 1, 2, 3, 5  -> out/02_tables.md, 02_rates.csv, 02_contrasts.csv
../../.venv/bin/python 03_glmm_refit.py                  # Table 4            -> out/03_glmm.md
../../.venv/bin/python 04_equivalence.py                 # Tables 6, 7        -> out/04_equivalence.md
# the original variational fit the paper quotes (untracked, user-private):
cd ../.. && .venv/bin/python .local/glmm_feasibility_probe.py
```

Run time is under a minute in total. All random draws use seed 20261002.

Inputs read: `results/sweep5v2-live/*/trials.jsonl`, `results/sweep6-live/*/trials.jsonl`,
`results/derived/e2e_overlay/{sweep5v2-live,sweep6-live}/*.e2e.jsonl`,
`results/derived/e2e_overlay/pooled_e2e_table.csv`, and for Table 7 only the two
`.v0220` backup cells under `results/sweep5-cluster-20260601/`.

Versions: Python 3.14.3, numpy 2.4.3, scipy 1.17.1, pandas 3.0.1, statsmodels 0.14.6.
R and lme4 are not installed on this machine, so the maximum-likelihood mixed model was
fitted by direct Gauss-Hermite quadrature of the same likelihood `lme4::glmer` uses
with `nAGQ > 1` (code in `03_glmm_refit.py`, with a simulated-data self-check).

No hash-pinned script was modified or imported. `tools/reanalysis/common.py` re-implements
the same pairing and cluster-interval conventions as `tools/ntster_common.py`.
