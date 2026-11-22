# NUMBERS.md — the one lookup before you quote a figure

**Purpose.** Several headline figures exist at more than one value across the docs,
because a reading was revised after the first write-up. Every stale value is
banner-marked where it lives, but that means trusting a banner in each of six files.
This table replaces that: **one row per figure, the frozen value, where it is
provenanced, and the readings it replaces.**

**Rule.** Before any figure enters paper prose, check it here. If it is not in this
table, run `/verify-claims` against the canonical corpora
(`results/sweep5v2-live` + `*_sweep6`; **never** a sync mirror such as the old
`results/sweep5-cluster-20260530`, moved out of the repo on 2026-10-10, `MOVES.md`). Every value below was re-verified against its provenance
file on 2026-08-29.

**Branch names in this file are provenance.** A hash written as "`paper/aaai27` `<hash>`"
was made on the old paper branch. That branch was merged into `main` by PR #101
(2026-09-18, merge commit, not squashed) and deleted, so every such hash is reachable on
`main`. Docs cited by bare name moved on 2026-09-18; `MOVES.md` "Third wave" resolves them.

*Last refreshed: 2026-11-09 (three generated additions, in no tex yet: call-state flips between the main sweep and the rerun, T8c; Haiku 4.5 tool arm on the renamed corpus, frontier contamination block; KCL VAL on the Claude solve plans, next to the C1 VAL block, which finds a case fault in the answer key; then plan step C3: two generated sub-blocks, the Study 1 breakdowns by `tools/reanalysis/s1_breakdowns_md.py` and the Study 2 part 1 tables by `tools/reanalysis/s2_gen_md.py`; no existing row changed; later the same day, generated post hoc ISS-028 and ISS-029 lines beside the delivered-rerun readout, both run on the laptop with the pinned ground-truth cache and the raw Haiku trials). Before that: 2026-11-08 (frontier contamination block, Sonnet 4.6 by the T7 method; T7 marked as in the tex). Before that: 2026-10-27 (VAL cross-check block, plan step C1; Study 1 block: main-sweep calling, tool-verified, unaided and contamination figures, the clustered tests and the mixed-model refit, and the replication table; plan step C2). Before that: 2026-10-09 (delivered-rerun readout block). Before that: 2026-10-03 (PlanBench equivalence + post hoc regrade rows; consistency-read figures; Gemma-prefix warning). Before that: 2026-09-18 (doc cleanup: provenance paths repointed after the moves, the note above added, the budget-probe row now names its readout; no figure changed). Earlier the same day (abstract cross-check block added: the four abstract figures + the Gemma invocation counts, verified for `paper/aaai27` `b27ef23`). 2026-09-14 (serving-environment block: tex pushed + Overleaf-synced, disclosure kept per Omer). 2026-09-13 (housekeeping: the "Single-tool suite — per-cell figures" block replaces the "to be pinned as Job 2 writes" placeholder; Job 2 tex note updated to pushed. Earlier the same day — nt-ster block: tex cross-check rows + factorial row extended as Job 3 landed and was pushed; frontier budget probe row frozen).*

## PlanBench — with-tools arm (CLOSED 2026-08-06/11; Act 4)

Provenance for all rows: `reference/planbench_wt_results_20260803.md`.
Binding constraints on use: the first-draw rule (deviation row 1 of the results doc
above) and Amendment M in `reference/planbench_wt_prereg.md` (GPT-4 is a published
reference line, not a comparator arm).

| figure | **quote this** | line | do NOT quote |
|---|---|---|---|
| clean WT accuracy | **68.3** [64.5, 71.9], 410/600 — *first-draw* | L23, L103 | **69.7** (last-attempt reading, L17) |
| clean WT paired Δ vs matched-NT | **+20.5pp**, b=202/c=79, McNemar **p=1.38e-13** | L23 | **+21.8pp**, p=2.7e-15 (last-attempt, L32) |
| Mystery WT | **71.8** [68.1, 75.3] vs NT **0.0** — paired Δ +71.8pp | L19, L30 | — |
| bare-NT clean | **43.8** [39.9, 47.8], 263/600 — CI-disjoint above GPT-4 | L108, L196 | — |
| GPT-4 reference line (2023, published grader) | clean **34.3** [30.6, 38.2]; Mystery **4.3** | L102, L198 | — *(reference line, never a comparator)* |
| matched-NT stripped-block regrade | **4.3** [3.0, 6.3], 26/600 | L254 | graded **0.0** — carries the injection caveat |
| formalization_match | clean **96.3** [94.5, 97.6] · Mystery **97.8** [96.3, 98.7] | L147 | — |

The first-draw-vs-last-attempt split is Omer's 2026-08-06 call ("the 1 pt is not
worth the ambiguity"). Cause: 18 instances were re-attempted on a resume and are
effectively best-of-2 while every other instance is single-shot; first-draw counts
the re-draws as failures. Full derivation: results doc deviation row 1 (L293).

### Added 2026-10-03 — PlanBench equivalence test and post hoc regrade (tex PR #114)

Provenance: `reference/reanalysis_planbench.md`; scripts `tools/reanalysis/planbench_equivalence_tost.py`, `planbench_corrected_extractor.py` (re-run 2026-10-02).

| figure | **quote this** | do NOT quote |
|---|---|---|
| clean-vs-Mystery WT paired gap (primary, first-draw) | **3.5 pp Mystery-above**, b = 119 / c = 140, McNemar **p = 0.214**; 90% CI **[−7.9, +0.9]**; discordance 43.2% | 2.2 pp, b = 119 / c = 132, p = 0.449 (last-attempt) |
| paired equivalence test on that gap (prereg-named, exploratory comparison; computed 2026-10-02, declared deviation) | ±7.5: **criterion not met (unresolved)**, TOST **p = 0.068**; ±10: **criterion met**, **p = 0.008** | "within / well inside the ±7.5 margin"; last-attempt p = 0.022; the word "equivalent" |
| corrected-extractor cells (**POST HOC**, always beside the primary) | BW NT **47.8** [43.9, 51.8] 287/600; BW WT **70.2** [66.4, 73.7] 421/600 first-draw; Mystery NT **4.3** [3.0, 6.3] 26/600; Mystery WT **94.3** [92.2, 95.9] 566/600 | BW WT 71.5 (last-attempt); Mystery WT 94.0 (first-block rule); "above 90%" as an estimate; any corrected figure as a headline |
| corrected-extractor paired contrasts (**POST HOC**) | BW WT vs NT **+22.3 pp**, 207/73, p = 5.1e−16; Mystery WT vs NT **+90.0 pp**, 541/1, p = 7.5e−161; BW WT vs Mystery WT **24.2 pp Mystery-above**, 28/173, p = 1.0e−26, criterion not met at ±7.5 or ±10 | last-attempt variants; block-only rows |
| instance files | **602 files** (501 + 101), **600 asked** (file 1 of each directory is the worked example); rename check 602/602 | "501 instance files" as the whole set |

## Frontier e2e — delivered vs tool-verified

Provenance: `reference/sonnet_wt_vs_haiku_e2e_memo.md` (canonical corpus, variant 11,
`e2e_strict`). **Delivered is the primary surface**; tool-verified is the mechanism
layer (journal memo §3 / D-J2).

| figure | **quote this** | do NOT quote |
|---|---|---|
| solve delivered, with tools | **95.0** [88.8, 97.8] — *both* Sonnet and Haiku; tool-verified 100.0, gap **+5.0pp** | **13.5% — RETRACTED**, an overlay grading artifact |
| simulate delivered, with tools | **bounds, not points**: Sonnet **[49.0, 62.0]**, Haiku **[52.0, 64.0]** | **0% — RETRACTED**, same artifact |
| simulate delivered↔tool-verified gap | ≈37–50pp Sonnet · ≈33–45pp Haiku (length-driven) | a single pooled "≈35–45" figure |
| simulate, no-tools | **bounds after 07-15 de-censoring** (pooled table 07-17): Sonnet canonical ⟨41.7, 61.3⟩ (c59/300), anon ⟨36.3, 57.7⟩ (c64/300); Haiku canonical ⟨38, 68⟩ (c30/100) | **[0, 100]** (pre-de-censoring memo row) and **45.0 / 38.3 exact points** (in the pre-reframe tex; reproduce from no sanctioned artifact — see `reference/job2_delivered_reframe_worknote.md` §3(e)) |
| validation tasks (vd/vp/vplan) | gap ≈0.0pp; delivered ≈ tool-verified | — |

The retracted 13.5 / 0.0 pair is the single most dangerous stale number in the tree:
it was published in earlier drafts before the overlay bug was found. Anything quoting
a frontier solve or simulate figure below ~90 / outside those bands is pre-retraction.

## Frontier contamination — Claude Sonnet 4.6, unaided (added 2026-11-08; in tex via PR #123)

Provenance: `tools/reanalysis/05_frontier_contamination.py`, output
`tools/reanalysis/out/05_frontier_contamination.md`, over `results/sonnet-frontier/sweep5v2`
(canonical) and `results/sonnet-frontier/sweep6` (anonymized): no-tools `success`, which is
the delivered score on every task except simulate; 4,560 trials each side, every key shared.
Method = T7 in the Study 1 block (`04_equivalence.py` `tost`, unchanged): paired on the exact
trial key, a 90% cluster-robust interval with the wider of domain (k=20) and problem
clustering governing, criterion met when the interval lies inside ±5. Post hoc: the tex's
earlier test was whether two separate Wilson intervals overlap. simulate is left out because
its stored `success` is the retired strict grade (the 45.0 / 38.3 row above).

| figure | **quote this** | do NOT quote |
|---|---|---|
| solve, Δ anonymized − canonical | **−0.33 pp, 90% [−10.59, +9.93]** (domain-governed), 28.7 vs 28.3 → **criterion not met (unresolved)** | **[−6.0, +5.3]** (an unclustered paired 95% interval from the 2026-11-08 discussion; it ignores the domain clustering); "equivalent"; "no memorization on solve" |
| validate_domain · validate_problem · validate_plan | **−1.94 [−4.67, +0.78]** met (ceiling, 93.6%) · **+0.83 [−1.33, +3.00]** met · **+0.03 [−1.17, +1.24]** met (ceiling, 97.3%) | validate_plan at 97.3% as "high-headroom" (it is a ceiling under the T7 rule) |
| pooled | four exact tasks **−0.05 [−0.99, +0.89]**, met (ceiling: 91.1%, and 3,000 of the 4,260 trials are validate_plan) | the tex's former "pooled \|Δ\| = 0.5" (it pooled the retired simulate grade: −0.48 over five tasks) |
| single solve answers that change under renaming | **75 of 300 (25.0%)**: 38 right→wrong, 37 wrong→right; **39 of 100** problems change their number of solved wordings | "39% of answers flip" (39 counts problems, not answers) |
| baselines for that 25% (in no tex yet) | identical prompt sent again: **1.1%** of answer pairs differ (validate_plan valid plans, 34/2,988; validate_domain 0/600), canonical; 2.9% and 2.7% anonymized. Wording changed, same names (solve): **8.0%** canonical (24/300), 14.7% anonymized | the validation-task rate as the solve noise floor (an easier task; no exact solve repeats exist) |
| solve per domain (15 trials a side) | down: blocksworld **11→3**, miconic 15→8, sailing 7→0; up: tpp **0→6**, farmland 3→8, satellite 3→8, gardening 6→11. **No domain survives Holm over the 20** (smallest adjusted p 0.156; exact McNemar, which ignores clustering) | any single domain as a memorization finding: with one renaming per domain, memorization cannot be told apart from a harder renaming |

**Warning (2026-11-09):** the solve rows above use the stored grade, which rejects some correct canonical answers (a case fault in pyval; counts in "VAL on the Claude solve plans" below). The renamed side is not affected, so the stored Δ is biased toward zero.

### Added 2026-11-09: Claude Haiku 4.5 with tools, renamed − canonical (in no tex yet)

Provenance: `tools/reanalysis/06_frontier_tools_contamination.py`, output
`tools/reanalysis/out/06_frontier_tools_contamination.md`, over
`results/haiku-frontier/sweep5v2-with-tools` (canonical) and `results/haiku-frontier/sweep6-with-tools`
(renamed; run 2026-07-12, never reported before). Variant 11, 1,520 trials a side, every key shared.
Method = T7, unchanged (`04_equivalence.tost`), on both surfaces: tool-verified (`success`) and
delivered (overlay `e2e_strict`, pairs determinate on both sides). Post hoc and descriptive.

<!-- gen:06_frontier_tools_contamination -->
| figure | **quote this** | do NOT quote |
|---|---|---|
| Haiku 4.5 with tools, renamed − canonical, tool-verified, per task (n = 100 / 120 / 200 / 1,000 / 100) | solve 100.0 → 100.0, +0.00 [+0.00, +0.00] criterion met (ceiling: low information); validate_domain 98.3 → 99.2, +0.83 [-1.71, +3.37] criterion met (ceiling: low information); validate_problem 96.5 → 97.0, +0.50 [-1.35, +2.35] (problem) criterion met (ceiling: low information); validate_plan 98.9 → 98.4, -0.50 [-1.05, +0.05] criterion met (ceiling: low information); simulate 97.0 → 98.0, +1.00 [-0.73, +2.73] criterion met (ceiling: low information) | "equivalent"; any of these as a memorization test: the tool arm sits at a ceiling, so a met criterion carries little information |
| same, delivered (`e2e_strict`, pairs determinate on both sides) | solve 95.0 → 97.0, +2.00 [-2.95, +6.95] **criterion not met (unresolved)**; validate_domain 98.3 → 99.2, +0.83 [-1.71, +3.37] criterion met (ceiling: low information); validate_problem 96.5 → 96.5, +0.00 [-2.03, +2.03] (problem) criterion met (ceiling: low information); validate_plan 98.8 → 98.4, -0.40 [-0.94, +0.14] criterion met (ceiling: low information); simulate 59.0 → 55.4, -3.61 [-12.77, +5.54] **criterion not met (unresolved)**. Censored pairs left out: simulate 17, every other task 0 | simulate delivered as a point rate (it is bounded: see the table in `06_frontier_tools_contamination.md`) |
| pooled, 5 tasks | tool-verified 98.5 → 98.4, -0.13 [-0.62, +0.36], criterion met (ceiling: low information); delivered 96.0 → 95.7, -0.27 [-1.11, +0.58], criterion met (ceiling: low information) (1,000 of the 1,520 trials are validate_plan) | none |
| settings, canonical vs renamed cell | same model, sdk 0.109.2, temperature, max_iterations, tool filter, prompt style, variant and key set; max tokens not in the meta, same default per task and the same truncation pattern (19 vs 19 rows, all simulate). Mismatches: none. Rows re-run on resume: canonical simulate depot p01 (first run: exception, stored: ok; 2 snapshots) | none |
<!-- /gen:06_frontier_tools_contamination -->

## Job 2 — the delivered surface (batches 1+2, 2026-09-07/08)

Provenance: `reference/job2_delivered_reframe_worknote.md` §2 (verdict table, derived from
`results/derived/e2e_overlay/pooled_e2e_table.csv`, 2026-07-17) and §8 (batch-2
tables). Tex: `paper/aaai27` `125cc7a` + `dbea3d7` (pushed 2026-09-08, Overleaf `cbc45b7`). Notation: Wilson `[a, b]`; censoring bounds `⟨a, b⟩`, never resolved.

| figure | **quote this** | do NOT quote |
|---|---|---|
| open-roster availability verdicts, think=off, delivered (sweep5v2-live, v11–13) | **13/25 cells UNDECIDED**; headline ≥9B: vd FAV/FAV/FAV (9B/Gemma/35B); vp FAV / knife-edge (fails √2.7) / UNDECIDED; vplan UNDECIDED ×3; solve exploratory-FAV (9B, +0.9pp margin) / UNDECIDED / UNDECIDED; simulate UNDECIDED ×3 | the memo's "exactly 2/25 UNDECIDED" (mode-pooled computation) |
| 9B validate_domain delivered | **⟨99.7, 100.0⟩** (359/360, c1) vs unaided 25.6 | — |
| gemma validate_plan, canonical delivered | **⟨6.6, 99.6⟩** (c2790/3000), UNDECIDED; the −67pp harm is a **mechanism-layer** claim | "−67pp delivered" |
| gemma validate_plan, full-storage rerun (iss024d, think=on) | delivered **⟨30.0, 63.1⟩** vs tool-verified 0.9 — separate apparatus, within-corpus only | as a resolution of the canonical cell |
| frontier NT simulate, v11 slice (funnel NEED line) | Sonnet **⟨34, 53⟩** (c19/100); Haiku **⟨38, 68⟩** (c30/100) | 45.0 / 38.3 exact points (retired) |
| frontier CALL rate, with-tools plain, every task | **100.0%** both tiers | — |
| delivered cost-of-pass multiplier, pooled ≥9B, tl-ster ÷ nt-neut (canonical) | solve **0.65–1.64×**; vd 2.81–2.91×; vp 4.41–4.86×; vplan 4.11–5.16×; simulate not identified | the mechanism-layer 0.3–0.4× as a delivered figure |
| frontier delivered cost-of-pass, solve | Sonnet **3.1×** (18.6K vs 6.0K tokens/pass); Haiku **6.1×** (48.5K vs 8.0K). Caveat (2026-11-09): the unaided side counts passes by the stored grade, which the pyval case fault (ISS-027) lowers; under VAL more unaided answers pass (Sonnet 28.7 → 32.7%, Haiku 22.0 → 25.0%), so the unaided tokens per pass would fall and both multipliers would rise. Not recomputed; counts in "VAL on the Claude solve plans" below | — |
| frontier delivered cost-of-pass, simulate | Sonnet ⟨83.5K, 105.7K⟩ vs NT ⟨9.8K, 15.3K⟩ (**5.5–10.8×**); Haiku ⟨72.9K, 89.7K⟩ vs ⟨7.7K, 13.8K⟩ (5.3–11.6×) | — |
| validate_domain balanced accuracy, delivered, steered arm | 9B **⟨100, 100⟩**; Gemma **⟨92.2, 95.0⟩**; 35B **⟨82.7, 99.2⟩** vs unaided 53.3 / 74.0 / 64.7 (plain: ⟨99.2,100⟩ / ⟨87.3,94.2⟩ / ⟨77.2,97.5⟩) | mechanism-layer 95–100 as delivered |
| PlanBench funnel stages (Haiku WT, n=600) | clean FORMALIZE 96.3 → CALL 100 → plan found 69.7 → delivered **68.3** (first-draw); Mystery 97.8 → 100 → 95.3 → **71.8** | last-attempt 69.7 delivered |
| frontier budget probe (RATIFIED 2026-09-12; in tex 5466cb6, Overleaf d922237; readout: `reference/frontier_budget_probe_readout.md`) | Sonnet: LEN-FIT **16/25** (64.0% [44.5, 79.8]) vs ET-FAIL **7/19** (36.8% [19.1, 59.0]), one-sided Fisher **p = 0.069** → PARTIAL (criterion not met); Haiku: **12/17** (70.6% [46.9, 86.7]) vs **1/12** (8.3% [1.5, 35.4]), **p = 0.0011** → H1; Haiku DECLINE **0/14**; delivered at 64K WT/NT: Sonnet **70 [60.4, 78.1] / 44 [34.7, 53.8]** (Δ +26 pp), Haiku **65 [55.3, 73.6] / 58 [48.2, 67.2]** (Δ +7 pp); tool-arm final turns at 64,000: **0** both tiers (NT: 1 Sonnet, 2 Haiku); censored at 262,144 chars: 0; cost **$40.68**; reference anatomy Sonnet 49/25/4/0/0/3/19/0, Haiku 52/17/1/1/2/14/12/1; canonical cells ⟨49, 62⟩ / ⟨52, 64⟩ UNCHANGED | the pre-retry readout (identical counts, superseded); the 65,536 budget and $217 cap; any pooling of probe rows with canonical cells |
| open-roster unaided simulate, canonical corpus, both reasoning modes (verified 2026-09-19) | **0/3,000 format-exact on the shared-budget corpus** (10 no-tools cells × 300, strict `success`, `results/sweep5v2-live/slurm_vllm_*_no-tools/trials.jsonl`; failure mix 1,772 `truncated_no_answer` · 1,202 `format_parse_fail` · 26 `result_mismatch`). Always carry the qualifier; the capability figure is the decoupled control, 22–40% content-correct at ≥4B | a bare "0/3,000" or "0%" read as a capability floor |

### Added 2026-10-03 — figures changed by the consistency read (tex PR #111)

Provenance: `results/derived/e2e_overlay/pooled_e2e_table.csv` (corpus `iss024d-e2e-live`, simulate, plain arm) and the frontier rows above.

| figure | **quote this** | do NOT quote |
|---|---|---|
| open-weight delivered simulate, rerun apparatus, upper end | **at most 21%** (Gemma ⟨6.0, 20.7⟩; 4B ⟨8.3, 10.7⟩, 9B ⟨12.0, 16.7⟩, 35B ⟨12.7, 13.7⟩ from 25+7, 36+14, 18+44, 38+3 of 300) | "at most 17%" (ignored Gemma) |
| frontier delivered vs verified | delivered at **two thirds** of the verified rate or less (64/97 = 0.66 Haiku high end; 62/99 = 0.63 Sonnet) | "half that or less" |
| rerun simulate mechanism layer, plain arm | **63.0 / 82.7 / 44.0 / 92.3%** (4B / 9B / Gemma / 35B; 189, 248, 132, 277 of 300) | the 3-model list "63, 83, 92%" |

<!-- gen:iss027_mech -->
**ISS-027, post hoc (grader case fault; the frozen values above stay).** Gemma plain 44.0% (132 of 300) reads 45.3% (136 of 300, +4 trials) with plan names case-folded. On the same corpus Qwen3.5-4B simulate steered 73.3 → 73.7 (+1); Gemma-26B simulate steered 92.0 → 93.0 (+3) move as well. The plain-arm values of Qwen3.5-4B, Qwen3.5-9B, Qwen3.6-35B in this row do not move.
<!-- /gen:iss027_mech -->

**Warning (2026-10-02).** `pddl_eval/scoring.py` on `harness/delivered-rerun` (PR #113) strips a leaked Gemma channel prefix before extraction. The pinned `tools/e2e_regrade.py` imports those functions, so re-running it on the canonical Gemma tool cells now gives different delivered solve numbers from the frozen rows in this file. The frozen rows stay; any regenerated Gemma figure is a new reading and needs its own row.

## Study 1 — main sweep figures (added 2026-10-27; T7 in tex via PR #123 (2026-11-08), the rest in no tex yet)

Plan step C2 (`weakness_action_plan.md` §4 C; settles C9 and C13). Study 1 is the main
sweep: canonical corpus `results/sweep5v2-live`, with the anonymized twin
`results/sweep6-live` for the contamination rows only. Headline models Qwen3.5-9B,
Gemma-26B (`gemma4_26b-a4b`) and Qwen3.6-35B, thinking off unless a row says otherwise.
Arms: **unaided** = the no-tools cell, wordings v11–13; **plain** = the tools cell, v11–13;
**steered** = the tools cell, v14–16. Trials per arm: solve 300, validate_domain 360 (300
valid + 60 invalid), validate_problem 600, validate_plan 3,000, simulate 300, over 20
domains. The six headline cells have 0 torn lines and 0 infrastructure-failure rows. The
canonical Qwen3.5-9B tool cells were served by vLLM 0.22.0 ("Serving environment" below).

**Provenance (all re-run 2026-10-27).**

- `tools/reanalysis/01`–`04` (the Reproduce section of `reference/reanalysis_statistics.md`):
  15/15 reproduction checks match, and every output is identical to the committed
  `tools/reanalysis/out/` (the two CSVs differ only in line endings). T1, T5, T6 and T7
  below come from these scripts.
- Calling, correct given a call (T2, T3) and validate_domain balanced accuracy (T4):
  `tools/reanalysis/s1_calling.py` (writes `out/s1_calling_sweep5v2-live.csv`) and
  `s1_extra.py`; the tables are rendered by `s1_gen_md.py`. What they compute: rows =
  `common.load_cell("sweep5v2-live", model, think, True)` filtered on the task and on
  `variant in NEUT` (plain) or `in STER` (steered). Calling = mean of `called`, which is
  the harness `tool_selected` (the task's own tool was called: a planner for solve, the
  validator of the same name for validate_*, `get_state_transition` for simulate).
  Interval = `common.cluster_boot(values, domains)`. Correct given a call = the same over
  the called rows, on `mech`. Balanced accuracy = mean of the two class accuracies (valid =
  problems `p01`–`p05`, invalid = `domain_neg`), interval from resampling the 20 domains
  with `numpy.random.default_rng(20261002)`, 10,000 draws. These calling rates reproduce
  all 7 rows of the tex `tab:decomp` and the counts of the Abstract block.
- Replication (T8) through the frozen rerun package itself, read-only:
  `tools.delivered_rerun.run.load_all(constants.REGISTERED, results/delivered-rerun,
  results/sweep5v2-live)`, then `analysis.parity` and `analysis.part_c_parity` (package
  hash `822aace…` as frozen; the grading step was not run). All 30 + 12 rows equal the
  readout (`tools/reanalysis/s1_parity_rederive.py <out.json>`). The calling column of
  T8a (`s1_calling_rerun_vs_main.py <out.json>`) is descriptive, not a registered test: same loader,
  paired `tool_selected` differences, `stats.cluster_bootstrap(..., 0.90, 20)`.

**Rules for this block.**

- **Surface = mechanism layer only.** Tool arms: `success` = tool-verified (the tool was
  called and its result matched the oracle). Unaided arm: `success` = the harness's
  online grade of the model's own full answer. Both are exact on every row. Study 1's
  delivered surface (the overlay's `e2e_strict` bounds, `reanalysis_statistics.md`
  Table 3) is retired for the open models and is not carried here.
- **Never pooled with Study 2**, and no rerun figure stands in for a cell of this block.
  T8 only sets the two side by side.
- **At-cap and grading.** An unaided answer cut by the output budget counts as a failure
  (`truncated_no_answer`), so the unaided simulate 0.0 cells always carry the qualifier of
  the Job 2 row ("0/3,000 format-exact on the shared-budget corpus"). The unaided grade
  here is the harness online grade, not the Study 2 delivered grader: on the same rerun
  rows, unaided solve is 9.7–10.7% online (T8b) and 21.3–25.3% delivered (readout E2).
  Never set a T1 unaided figure against a Study 2 delivered figure.
- **Intervals.** Single rates: domain-cluster percentile bootstrap, 95% (k = 20, 10,000
  resamples, seed 20261002; `02_rates.csv` `boot_domain_*`). Where a rate is exactly 0 or
  100% the bootstrap has zero width and the Wilson 95% interval is shown instead, marked
  †. Paired contrasts: the wider of the domain (k = 20) and problem cluster-robust t 95%
  intervals; domain governs unless marked "(problem)". The paper's Wilson × √2.7
  intervals ignore the domain clustering and are two to five times too narrow on
  validate_plan single rates (reanalysis item 1).
- Never take a figure from `summary_*.json` (n = 0 stub rows for the condition that did
  not run).

| figure | **quote this** | source | do NOT quote |
|---|---|---|---|
| Gemma validate_plan calling, plain → steered | **20.7% (622/3,000) → 93.6% (2,808/3,000)**, 95% [9.0, 34.1] → [84.0, 100.0]; correct given a call 99.2% / 98.9%; 0 successes without a call | T2; same counts as the Abstract block row 2 | the Wilson interval [19.3, 22.2] as its uncertainty (ignores the domains) |
| Gemma validate_plan availability, tool-verified | **−67.3 pp** [−79.7, −54.8] (87.8 unaided → 20.6 tool-verified), Holm p 1.5e−08 at m = 30. **Tool-verified only** | T5; reanalysis Table 2 | "−67 pp" as a delivered harm or a headline (Study 2 R1: delivered +0.9 [−1.2, 2.9]) |
| Gemma validate_plan steering, tool-verified | **+72.0 pp** [57.5, 86.5] | T5; equals the nt-ster block's "+72.0pp with tools" | — |
| paired verdicts, headline, think=off | **19 of 30** contrasts significant (18 favorable, plus the Gemma validate_plan harm); **all 19 survive Holm at m = 30**, two only just (9B validate_plan availability p_adj 0.046; Gemma validate_domain availability 0.050). At m = 60 those two and 35B validate_plan steering (0.063) drop; the other 16 survive every family up to m = 200. The m = 60 family counted the delivered surface, now retired, so the family size the paper uses is still to be decided | T5; reanalysis items 2 and 4, Table 5 | the "stricter than Bonferroni" argument for the √2.7 rule; 9B validate_plan steering (+2.9 [−0.6, +6.3]) as favorable; 35B validate_plan availability (−8.7 [−19.0, +1.5]) as significant |
| mixed model, Gemma validate_plan steered vs plain | **log-odds +7.80, SE 0.29, 95% [7.23, 8.37]** (maximum likelihood, random intercept per instance; profile [7.25, 8.40]); with domain clustering the evidence is z ≈ 6 (GEE +3.87 [2.63, 5.12], population-averaged) | T6; reanalysis Table 4 | "+7.5, SD 0.10" (variational fit; the SD is about 3× too small); "the GEE agrees" as one quantity; z = 78 |
| correct given a call, headline, think=off | 95.2% or higher in every cell except 9B simulate **81.2 / 83.3**, 9B validate_problem steered **90.2**, Gemma simulate **92.0 / 90.7** and 35B solve plain **92.6** | T2 | the tex appendix "≥92% throughout, except on 9B simulate" (misses 9B validate_problem steered and Gemma simulate steered); the tex "≥93% for both" on solve and validate_plan (35B solve plain is 92.6) |
| calling under thinking on | validate_plan plain: Gemma **20.7% → 0.6%** (19/3,000), 9B 97.9 → **69.2%** (2,075/3,000), 35B 82.9 → **99.9%** (2,998/3,000) | T3 | — (Study 2 D3 measures this again on the fixed setup) |
| validate_domain balanced accuracy | unaided **53.3 / 74.0 / 64.7** (9B / Gemma / 35B; frozen in the Job 2 block) → tool-verified steered **100.0 / 95.0 / 99.2** (plain 100.0 / 92.5 / 98.0) | T4 | these tool-verified values as delivered |
| contamination, pooled, think=off | **criterion met at ±5 for all five models**; widest Qwen3.5-4B −2.02 [−4.33, +0.29] (90%) | T7 | "equivalent"; the tex `tab:contam` 4B "−2.1" (difference of the rounded rates; the paired Δ is −2.02) |
| contamination, per task, headline | criterion met in 10 of 15 cells, 6 of them on a floor or ceiling (little information); **not met (unresolved) in 5**: validate_domain for all three, validate_problem for 9B and Gemma. Mean \|Δ\| 1.2 (max 3.7) over these 15; 1.1 over all 25 | T7 | "zero CI-disjoint cells" as a per-task null |
| contamination, thinking on, pooled | **not met (unresolved)** for Qwen3.5-4B, 9B, 35B; met on a floor for 0.8B and Gemma | T7 | — |
| replication, tool cells | **25 of 30 met the ±5 criterion** (Gemma 10/10, Qwen 15/20); not met: 9B simulate ×2, 35B solve ×2, 35B simulate plain. By point estimate, 27 of 30 are within ±5 | T8a; frozen in the "Delivered rerun — readout" parity row | "25 of 30 within 5 points" (25 is the equivalence criterion, the point-estimate count is 27); "the rerun reproduces the canonical cells" |
| replication, unaided cells | **11 of 12 met**; 35B validate_domain +8.6 [2.8, 14.7] unresolved | T8b; frozen Part C row | — |
| calling, rerun vs main sweep (descriptive) | within 1 point in 27 of 30 cells; **moved only in the three cells that failed the tool-verified criterion**: 35B solve plain 68.0 → 82.7 (+14.7 [10.7, 19.3]), steered 93.7 → 99.7 (+6.0), 35B simulate plain 76.3 → 99.7 (+23.3 [16.7, 30.7]). Cause not established in this pass (in the main sweep the 35B traced 66 simulate plans by hand without a call; in the rerun the same trials called the tool) | T8a | the 35B "calls the planner on only 68%", or the 9B-vs-35B "size inversion" on solve, without this caveat |
| serving version, paired (reanalysis Table 7) | 0.20.2 − 0.22.0, Qwen3.5-0.8B with tools: **+0.43 [−0.27, +1.13]** (paired, 90%), criterion met; 8 of 10 task × arm cells meet it (10 of 10 against the second 0.22.0 run; the same version run twice: 7 of 10) | `tools/reanalysis/out/04_equivalence.md` (b) | as a replacement for the frozen unpaired row in "Serving environment" (that row stays) |

<!-- gen:iss027_summary -->
**ISS-027, post hoc (grader case fault; the frozen values above stay).** Gemma simulate correct given a call reads 95.3 / 94.0 with plan names case-folded (frozen 92.0 / 90.7); see T2.
<!-- /gen:iss027_summary -->

### Study 1 per-cell tables (generated by the scripts above, not transcribed)

Rates in percent; counts in parentheses. † = Wilson 95% (rate exactly 0 or 100%). Every
other single-rate interval is the domain bootstrap 95%.

#### T1. Unaided and tool-verified success (think=off)

`success` per arm; the same rates as `02_rates.csv` (mechanism surface).

| model | task | n per arm | unaided | tool-verified, plain | tool-verified, steered |
|---|---|---|---|---|---|
| Qwen3.5-9B | solve | 300 | 10.7 [6.3, 15.0] (32) | 99.3 [98.0, 100.0] (298) | 100.0 [98.7, 100.0]† (300) |
| Qwen3.5-9B | validate_domain | 360 | 25.6 [17.5, 36.4] (92) | 100.0 [98.9, 100.0]† (360) | 100.0 [98.9, 100.0]† (360) |
| Qwen3.5-9B | validate_problem | 600 | 65.7 [59.2, 71.5] (394) | 95.2 [93.2, 97.2] (571) | 90.2 [83.3, 95.5] (541) |
| Qwen3.5-9B | validate_plan | 3,000 | 79.7 [73.7, 85.5] (2392) | 93.2 [88.2, 97.4] (2795) | 96.0 [91.9, 99.1] (2881) |
| Qwen3.5-9B | simulate | 300 | 0.0 [0.0, 1.3]† (0) | 65.0 [56.3, 72.7] (195) | 83.0 [73.0, 91.7] (249) |
| Gemma-26B | solve | 300 | 7.7 [4.0, 12.0] (23) | 99.3 [98.3, 100.0] (298) | 98.7 [96.3, 100.0] (296) |
| Gemma-26B | validate_domain | 360 | 77.8 [65.6, 88.6] (280) | 97.5 [95.0, 99.4] (351) | 98.3 [96.1, 100.0] (354) |
| Gemma-26B | validate_problem | 600 | 74.8 [68.8, 80.7] (449) | 99.7 [99.2, 100.0] (598) | 100.0 [99.4, 100.0]† (600) |
| Gemma-26B | validate_plan | 3,000 | 87.8 [83.7, 91.4] (2635) | 20.6 [8.9, 33.9] (617) | 92.6 [83.2, 98.7] (2777) |
| Gemma-26B | simulate | 300 | 0.0 [0.0, 1.3]† (0) | 91.7 [86.0, 96.7] (275) | 90.7 [83.0, 97.3] (272) |
| Qwen3.6-35B | solve | 300 | 9.3 [6.3, 12.3] (28) | 63.0 [54.3, 71.7] (189) | 92.0 [87.0, 96.7] (276) |
| Qwen3.6-35B | validate_domain | 360 | 67.8 [56.4, 78.3] (244) | 98.9 [97.2, 100.0] (356) | 99.7 [99.2, 100.0] (359) |
| Qwen3.6-35B | validate_problem | 600 | 75.7 [71.2, 79.8] (454) | 96.8 [95.2, 98.2] (581) | 97.3 [95.5, 99.0] (584) |
| Qwen3.6-35B | validate_plan | 3,000 | 90.9 [87.7, 93.9] (2727) | 82.2 [72.6, 90.6] (2465) | 99.3 [98.7, 99.8] (2978) |
| Qwen3.6-35B | simulate | 300 | 0.0 [0.0, 1.3]† (0) | 74.7 [65.3, 83.0] (224) | 97.0 [93.3, 99.7] (291) |

<!-- gen:iss027_t1 -->
**ISS-027, post hoc (grader case fault; the frozen values above stay).** With plan names case-folded, these cells move: Qwen3.5-9B simulate tool-verified plain 65.0 → 65.3 (+1 trial); Qwen3.5-9B solve unaided 10.7 → 11.3 (+2 trials); Gemma-26B simulate tool-verified plain 91.7 → 95.0 (+10 trials); Gemma-26B simulate tool-verified steered 90.7 → 94.0 (+10 trials); Gemma-26B validate_plan tool-verified steered 92.6 → 92.6 (+1 trial). No other cell of this table moves. Counts and method: "ISS-027 post hoc corrections" below.
<!-- /gen:iss027_t1 -->

#### T1b. Qwen3.5-0.8B on validate_domain and validate_problem (think=off; added 2026-11-22; in tex since the placeholders PR)

T1 holds the three ≥9B models. The paper's Supporting Analyses also describe the 0.8B model on these two tasks; the delivered
bounds that used to carry that sentence are retired, so these are the figures to quote. **Do NOT quote** "the 0.8B omits required
arguments on both tasks": it does so on validate_problem only.

<!-- gen:s1_small_model_validation -->
*Generated by `tools/reanalysis/s1_small_model_validation.py`; do not edit between the markers, rerun the script. Qwen3.5-0.8B, main sweep, think=off. Rates as T1 (stored harness grade; 95% domain-cluster bootstrap, counts in brackets). validate_domain pools 5 valid trials for each invalid one, so its pooled rate is not a balanced accuracy.*

| task | unaided | tool-verified, plain | tool-verified, steered | called the validator, plain / steered | trials with a missing-argument error, plain / steered |
|---|---|---|---|---|---|
| validate_domain | 80.8 [75.6, 83.9] (291/360) | 87.5 [76.1, 96.9] (315/360) | 89.2 [76.9, 98.6] (321/360) | 355/360 (98.6%) / 360/360 (100.0%) | 0/360 / 0/360 |
| validate_problem | 51.2 [49.3, 53.3] (307/600) | 26.2 [14.2, 40.0] (157/600) | 18.5 [9.0, 29.3] (111/600) | 572/600 (95.3%) / 600/600 (100.0%) | 375/600 / 470/600 |
<!-- /gen:s1_small_model_validation -->

#### T2. Calling, and correct given a call (think=off)

Calling = `tool_selected`. Correct given a call = tool-verified success among the trials that called. On this layer a trial without a call fails by construction: 0 successes without a call in all 30 cells.

| model | task | calling, plain | calling, steered | correct given a call, plain | correct given a call, steered |
|---|---|---|---|---|---|
| Qwen3.5-9B | solve | 100.0 [98.7, 100.0]† (300/300) | 100.0 [98.7, 100.0]† (300/300) | 99.3 [98.0, 100.0] (298/300) | 100.0 [98.7, 100.0]† (300/300) |
| Qwen3.5-9B | validate_domain | 100.0 [98.9, 100.0]† (360/360) | 100.0 [98.9, 100.0]† (360/360) | 100.0 [98.9, 100.0]† (360/360) | 100.0 [98.9, 100.0]† (360/360) |
| Qwen3.5-9B | validate_problem | 100.0 [99.4, 100.0]† (600/600) | 100.0 [99.4, 100.0]† (600/600) | 95.2 [93.2, 97.2] (571/600) | 90.2 [83.3, 95.5] (541/600) |
| Qwen3.5-9B | validate_plan | 97.9 [94.2, 100.0] (2937/3000) | 100.0 [99.9, 100.0]† (3000/3000) | 95.2 [90.7, 98.6] (2795/2937) | 96.0 [91.9, 99.1] (2881/3000) |
| Qwen3.5-9B | simulate | 80.0 [76.0, 84.0] (240/300) | 99.7 [99.0, 100.0] (299/300) | 81.2 [69.6, 91.5] (195/240) | 83.3 [73.0, 92.3] (249/299) |
| Gemma-26B | solve | 100.0 [98.7, 100.0]† (300/300) | 100.0 [98.7, 100.0]† (300/300) | 99.3 [98.3, 100.0] (298/300) | 98.7 [96.3, 100.0] (296/300) |
| Gemma-26B | validate_domain | 100.0 [98.9, 100.0]† (360/360) | 100.0 [98.9, 100.0]† (360/360) | 97.5 [95.0, 99.4] (351/360) | 98.3 [96.1, 100.0] (354/360) |
| Gemma-26B | validate_problem | 99.8 [99.5, 100.0] (599/600) | 100.0 [99.4, 100.0]† (600/600) | 99.8 [99.5, 100.0] (598/599) | 100.0 [99.4, 100.0]† (600/600) |
| Gemma-26B | validate_plan | 20.7 [9.0, 34.1] (622/3000) | 93.6 [84.0, 100.0] (2808/3000) | 99.2 [97.8, 99.9]‡ (617/622) | 98.9 [98.2, 99.5] (2777/2808) |
| Gemma-26B | simulate | 99.7 [99.0, 100.0] (299/300) | 100.0 [98.7, 100.0]† (300/300) | 92.0 [86.3, 97.0] (275/299) | 90.7 [83.0, 97.3] (272/300) |
| Qwen3.6-35B | solve | 68.0 [60.0, 76.0] (204/300) | 93.7 [89.3, 97.3] (281/300) | 92.6 [86.9, 97.5] (189/204) | 98.2 [96.3, 99.7] (276/281) |
| Qwen3.6-35B | validate_domain | 100.0 [98.9, 100.0]† (360/360) | 100.0 [98.9, 100.0]† (360/360) | 98.9 [97.2, 100.0] (356/360) | 99.7 [99.2, 100.0] (359/360) |
| Qwen3.6-35B | validate_problem | 98.5 [97.8, 99.2] (591/600) | 100.0 [99.4, 100.0]† (600/600) | 98.3 [96.8, 99.5] (581/591) | 97.3 [95.5, 99.0] (584/600) |
| Qwen3.6-35B | validate_plan | 82.9 [73.5, 91.1] (2487/3000) | 99.9 [99.7, 100.0] (2997/3000) | 99.1 [98.4, 99.7] (2465/2487) | 99.4 [98.8, 99.8] (2978/2997) |
| Qwen3.6-35B | simulate | 76.3 [67.0, 84.3] (229/300) | 100.0 [98.7, 100.0]† (300/300) | 97.8 [94.5, 100.0] (224/229) | 97.0 [93.3, 99.7] (291/300) |

‡ Only 13 of the 20 domains have a call in this cell, so the bootstrap runs over 13 clusters.

<!-- gen:iss027_t2 -->
**ISS-027, post hoc (grader case fault; the frozen values above stay).** Correct given a call, names case-folded: Qwen3.5-9B simulate plain 81.2 → 81.7 (196/240); Gemma-26B simulate plain 92.0 → 95.3 (285/299); Gemma-26B simulate steered 90.7 → 94.0 (282/300); Gemma-26B validate_plan steered 98.9 → 98.9 (2778/2808). Calling does not change.
<!-- /gen:iss027_t2 -->

#### T3. Calling with thinking on (think=on; plain / steered)

| model | arm | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | plain | 59.0 [47.7, 69.7] | 99.4 [98.6, 100.0] | 98.7 [97.3, 99.7] | 69.2 [61.7, 76.0] | 94.0 [90.0, 97.3] |
| Qwen3.5-9B | steered | 74.0 [65.3, 82.0] | 98.9 [97.8, 99.7] | 99.0 [98.2, 99.7] | 97.1 [95.9, 98.3] | 99.7 [99.0, 100.0] |
| Gemma-26B | plain | 23.3 [15.7, 31.7] | 52.5 [36.7, 68.1] | 56.0 [43.7, 68.0] | 0.6 [0.0, 1.5] | 53.3 [45.0, 61.7] |
| Gemma-26B | steered | 75.0 [60.3, 88.3] | 90.6 [82.8, 96.7] | 85.0 [74.2, 93.7] | 44.2 [29.6, 59.6] | 98.7 [97.3, 99.7] |
| Qwen3.6-35B | plain | 78.3 [68.3, 87.7] | 100.0 [98.9, 100.0]† | 100.0 [99.4, 100.0]† | 99.9 [99.8, 100.0] | 99.3 [98.3, 100.0] |
| Qwen3.6-35B | steered | 92.0 [86.0, 97.0] | 100.0 [98.9, 100.0]† | 100.0 [99.4, 100.0]† | 99.9 [99.7, 100.0] | 100.0 [98.7, 100.0]† |

Counts behind the quoted cells (validate_plan plain): 9B 2,075/3,000, Gemma 19/3,000, 35B 2,998/3,000. For comparison, think=off: 97.9, 20.7, 82.9 (T2).

#### T4. validate_domain balanced accuracy (think=off)

Mean of the accuracy on the 300 valid and the 60 invalid trials (the fixtures run 5:1, so a constant VALID scores 83.3% pooled and 50% balanced). The 9B tool arms make no error in either class, so their bootstrap has zero width.

| model | unaided | tool-verified, plain | tool-verified, steered |
|---|---|---|---|
| Qwen3.5-9B | 53.3 [48.3, 60.0] (valid 11.7 / invalid 95.0) | 100.0 [100.0, 100.0] (valid 100.0 / invalid 100.0) | 100.0 [100.0, 100.0] (valid 100.0 / invalid 100.0) |
| Gemma-26B | 74.0 [63.3, 84.7] (valid 79.7 / invalid 68.3) | 92.5 [85.0, 98.3] (valid 100.0 / invalid 85.0) | 95.0 [88.3, 100.0] (valid 100.0 / invalid 90.0) |
| Qwen3.6-35B | 64.7 [54.3, 74.8] (valid 69.3 / invalid 60.0) | 98.0 [94.3, 100.0] (valid 99.3 / invalid 96.7) | 99.2 [97.5, 100.0] (valid 100.0 / invalid 98.3) |

#### T5. Paired, domain-clustered, Holm-corrected tests (think=off, mechanism layer)

| model | task | contrast | first → second arm | Δ | clustered 95% CI | p | Holm p, m=30 | after Holm, m=30 | after Holm, m=60 | paper rule × √2.7 |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | avail. | 10.7 → 99.3 | +88.7 | [+83.4, +93.9] | 9.1e-19 | 2.6e-17 | FAV | FAV | FAV |
| Qwen3.5-9B | solve | steer. | 99.3 → 100.0 | +0.7 | [-0.7, +2.1] | 0.330 | 1.000 | NS | NS | NS |
| Qwen3.5-9B | validate_domain | avail. | 25.6 → 100.0 | +74.4 | [+64.0, +84.9] | 6.1e-12 | 1.5e-10 | FAV | FAV | FAV |
| Qwen3.5-9B | validate_domain | steer. | 100.0 → 100.0 | +0.0 | [+0.0, +0.0] | 1.000 | 1.000 | NS | NS | NS |
| Qwen3.5-9B | validate_problem | avail. | 65.7 → 95.2 | +29.5 | [+22.2, +36.8] | 6.8e-08 | 1.4e-06 | FAV | FAV | FAV |
| Qwen3.5-9B | validate_problem | steer. | 95.2 → 90.2 | -5.0 | [-10.9, +0.9] | 0.093 | 0.916 | NS | NS | NS |
| Qwen3.5-9B | validate_plan | avail. | 79.7 → 93.2 | +13.4 | [+5.0, +21.9] | 0.004 | 0.046 | FAV | **not significant** | FAV |
| Qwen3.5-9B | validate_plan | steer. | 93.2 → 96.0 | +2.9 | [-0.6, +6.3] | 0.097 | 0.916 | **NS** | NS | FAV |
| Qwen3.5-9B | simulate | avail. | 0.0 → 65.0 | +65.0 § | [+55.9, +74.1] | 5.9e-12 | 1.5e-10 | FAV | FAV | FAV |
| Qwen3.5-9B | simulate | steer. | 65.0 → 83.0 | +18.0 § | [+13.4, +22.6] | 1.4e-07 | 2.5e-06 | FAV | FAV | FAV |
| Gemma-26B | solve | avail. | 7.7 → 99.3 | +91.7 | [+87.3, +96.1] | 1.6e-20 | 4.9e-19 | FAV | FAV | FAV |
| Gemma-26B | solve | steer. | 99.3 → 98.7 | -0.7 | [-2.9, +1.6] | 0.541 | 1.000 | NS | NS | NS |
| Gemma-26B | validate_domain | avail. | 77.8 → 97.5 | +19.7 | [+7.1, +32.4] | 0.004 | 0.050 | FAV | **not significant** | FAV |
| Gemma-26B | validate_domain | steer. | 97.5 → 98.3 | +0.8 | [-0.1, +1.8] | 0.083 | 0.916 | NS | NS | NS |
| Gemma-26B | validate_problem | avail. | 74.8 → 99.7 | +24.8 | [+18.3, +31.3] | 1.7e-07 | 2.8e-06 | FAV | FAV | FAV |
| Gemma-26B | validate_problem | steer. | 99.7 → 100.0 | +0.3 | [-0.1, +0.8] | 0.163 | 1.000 | NS | NS | NS |
| Gemma-26B | validate_plan | avail. | 87.8 → 20.6 | -67.3 | [-79.7, -54.8] | 6.7e-10 | 1.5e-08 | AGAINST | AGAINST | AGAINST |
| Gemma-26B | validate_plan | steer. | 20.6 → 92.6 | +72.0 | [+57.5, +86.5] | 2.8e-09 | 6.1e-08 | FAV | FAV | FAV |
| Gemma-26B | simulate | avail. | 0.0 → 91.7 | +91.7 | [+85.9, +97.5] | 3.0e-18 | 8.3e-17 | FAV | FAV | FAV |
| Gemma-26B | simulate | steer. | 91.7 → 90.7 | -1.0 | [-4.7, +2.7] | 0.577 | 1.000 | NS | NS | NS |
| Qwen3.6-35B | solve | avail. | 9.3 → 63.0 | +53.7 § | [+45.7, +61.7] | 1.8e-11 | 4.2e-10 | FAV | FAV | FAV |
| Qwen3.6-35B | solve | steer. | 63.0 → 92.0 | +29.0 § | [+21.6, +36.4] | 1.1e-07 | 2.1e-06 | FAV | FAV | FAV |
| Qwen3.6-35B | validate_domain | avail. | 67.8 → 98.9 | +31.1 | [+18.4, +43.8] | 6.0e-05 | 9.5e-04 | FAV | FAV | FAV |
| Qwen3.6-35B | validate_domain | steer. | 98.9 → 99.7 | +0.8 | [-0.4, +2.1] | 0.186 | 1.000 | NS | NS | NS |
| Qwen3.6-35B | validate_problem | avail. | 75.7 → 96.8 | +21.2 | [+15.5, +26.8] (problem) | 7.9e-08 | 1.6e-06 | FAV | FAV | FAV |
| Qwen3.6-35B | validate_problem | steer. | 96.8 → 97.3 | +0.5 | [-1.1, +2.1] (problem) | 0.550 | 1.000 | NS | NS | NS |
| Qwen3.6-35B | validate_plan | avail. | 90.9 → 82.2 | -8.7 | [-19.0, +1.5] | 0.090 | 0.916 | **NS** | NS | AGAINST |
| Qwen3.6-35B | validate_plan | steer. | 82.2 → 99.3 | +17.1 | [+7.4, +26.8] | 0.002 | 0.022 | FAV | **not significant** | FAV |
| Qwen3.6-35B | simulate | avail. | 0.0 → 74.7 | +74.7 § | [+65.1, +84.2] | 1.1e-12 | 3.1e-11 | FAV | FAV | FAV |
| Qwen3.6-35B | simulate | steer. | 74.7 → 97.0 | +22.3 § | [+12.8, +31.9] | 1.0e-04 | 0.002 | FAV | FAV | FAV |

**Bold** verdict = differs from the paper rule (Wilson disjointness × √2.7), or lost to Holm. Holm m = 30 = the 30 rows of this table; m = 60 adds the 30 delivered-surface contrasts (`02_contrasts.csv` `holm_p_H60_both`). Exact sign-flip p-values on the 20 domain sums are in `02_contrasts.csv` (`p_signflip_domain`).

§ An input cell did not meet the replication criterion (T8a). Tool-verified, main sweep vs rerun: 9B simulate plain 65.0 vs 68.0, steered 83.0 vs 87.0; 35B solve plain 63.0 vs 82.3, steered 92.0 vs 99.3; 35B simulate plain 74.7 vs 94.0 (steered met: 97.0 vs 95.7). Each § contrast is still a main-sweep measurement; the mark says its size is not reproduced on the fixed setup.

<!-- gen:iss027_t5 -->
**ISS-027, post hoc (grader case fault; the frozen values above stay).** Δ with plan names case-folded, point estimates (the clustered intervals and Holm p-values are not recomputed): Qwen3.5-9B solve availability +88.7 → +88.0; Qwen3.5-9B simulate availability +65.0 → +65.3; Qwen3.5-9B simulate steering +18.0 → +17.7; Gemma-26B validate_plan steering +72.0 → +72.0; Gemma-26B simulate availability +91.7 → +95.0; Gemma-26B simulate steering -1.0 → -1.0. No other row of T5 moves.
<!-- /gen:iss027_t5 -->

#### T6. Mixed model: Gemma validate_plan, steered vs plain (think=off, tool-verified)

6,000 trials, 1,000 instances (plan files), 20 domains; success 0.206 → 0.926. Of the 1,000 instances, 571 fail all three plain trials and pass all three steered ones.

| fit | log-odds, steered vs plain | SE | 95% interval | z | what it estimates |
|---|---|---|---|---|---|
| **maximum likelihood, random intercept per instance** (Gauss-Hermite, 200 nodes; the likelihood `lme4::glmer` maximises) | **+7.80** | **0.29** | **[7.23, 8.37]**; profile [7.25, 8.40] | 26.8 | the effect within an instance |
| conditional logistic, stratified on instance | +6.15 | 0.29 | [5.59, 6.72] | 21.2 | within an instance, no distribution assumed for the instance effect |
| GEE, exchangeable, clustered on instance (k = 1,000) | +3.87 | 0.12 | [3.65, 4.10] | 33.5 | population-averaged |
| GEE, exchangeable, clustered on domain (k = 20) | +3.87 | 0.64 | [2.63, 5.12] | 6.1 | population-averaged |
| logistic, domain-cluster-robust SE, t(19) interval | +3.87 | 0.65 | [2.51, 5.24] | 5.9 | population-averaged |
| variational Bayes (the fit the tex quotes, `.local/glmm_feasibility_probe.py`, rerun) | +7.53 | 0.10 (posterior SD) | [7.34, 7.72] | 78.1 | within an instance; **do not quote the SD** |

Maximum-likelihood details: random-intercept SD 2.86; likelihood-ratio χ² 4,410 on 1 df; implied marginal rates 0.204 → 0.931 (observed 0.206 → 0.926); the same estimate to three decimals at 50 and 400 nodes. The same contrast as a paired difference in rate: +72.0 pp, 95% [57.5, 86.5] clustered on domain. The sign and the significance hold under every fit; the size of the log-odds depends on the model (the conditional fit is lower, a sign that a normal instance effect fits all-or-nothing instances poorly).

#### T7. Contamination: anonymized − canonical, unaided (no-tools `success`)

Δ in points, paired on the exact trial key; 90% interval, the wider of domain and problem clustering; criterion met = the whole interval inside ±5 (TOST at α = 0.05). Floor or ceiling = a canonical rate below 10% or above 90%. Per-task rows for the two small models are in `04_equivalence.md`.

| model | cell | think | canonical | anonymized | Δ | governing 90% CI | verdict at ±5 |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | pooled, 5 tasks | off | 45.9 | 45.8 | -0.11 | [-0.55, +0.34] (problem) | **criterion met** |
| Qwen3.5-4B | pooled, 5 tasks | off | 58.2 | 56.1 | -2.02 | [-4.33, +0.29] | **criterion met** |
| Qwen3.5-9B | solve | off | 10.7 | 11.3 | +0.67 | [-2.57, +3.91] (problem) | criterion met |
| Qwen3.5-9B | validate_domain | off | 25.6 | 26.7 | +1.11 | [-4.66, +6.88] | criterion not met (unresolved) |
| Qwen3.5-9B | validate_problem | off | 65.7 | 69.3 | +3.67 | [-1.24, +8.58] | criterion not met (unresolved) |
| Qwen3.5-9B | validate_plan | off | 79.7 | 79.3 | -0.40 | [-2.94, +2.14] | criterion met |
| Qwen3.5-9B | simulate | off | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | criterion met (floor: low information) |
| Qwen3.5-9B | pooled, 5 tasks | off | 63.8 | 64.2 | +0.35 | [-1.52, +2.23] | **criterion met** |
| Gemma-26B | solve | off | 7.7 | 8.0 | +0.33 | [-3.80, +4.47] | criterion met (floor: low information) |
| Gemma-26B | validate_domain | off | 77.8 | 80.6 | +2.78 | [-2.03, +7.58] | criterion not met (unresolved) |
| Gemma-26B | validate_problem | off | 74.8 | 77.8 | +3.00 | [-1.82, +7.82] | criterion not met (unresolved) |
| Gemma-26B | validate_plan | off | 87.8 | 88.2 | +0.40 | [-2.36, +3.16] | criterion met |
| Gemma-26B | simulate | off | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | criterion met (floor: low information) |
| Gemma-26B | pooled, 5 tasks | off | 74.3 | 75.2 | +0.90 | [-0.71, +2.51] | **criterion met** |
| Qwen3.6-35B | solve | off | 9.3 | 9.7 | +0.33 | [-3.26, +3.93] | criterion met (floor: low information) |
| Qwen3.6-35B | validate_domain | off | 67.8 | 70.3 | +2.50 | [-4.38, +9.38] | criterion not met (unresolved) |
| Qwen3.6-35B | validate_problem | off | 75.7 | 76.7 | +1.00 | [-1.99, +3.99] | criterion met |
| Qwen3.6-35B | validate_plan | off | 90.9 | 89.0 | -1.87 | [-3.67, -0.07] | criterion met (ceiling: low information) |
| Qwen3.6-35B | simulate | off | 0.0 | 0.0 | +0.00 | [+0.00, +0.00] | criterion met (floor: low information) |
| Qwen3.6-35B | pooled, 5 tasks | off | 75.7 | 74.8 | -0.88 | [-2.22, +0.47] | **criterion met** |
| Qwen3.5-0.8B | pooled, 5 tasks | on | 0.0 | 0.2 | +0.15 | [-0.01, +0.32] | **criterion met (floor: low information)** |
| Qwen3.5-4B | pooled, 5 tasks | on | 19.1 | 14.5 | -4.56 | [-7.87, -1.25] | **criterion not met (unresolved)** |
| Qwen3.5-9B | pooled, 5 tasks | on | 18.4 | 15.7 | -2.68 | [-5.44, +0.08] | **criterion not met (unresolved)** |
| Gemma-26B | pooled, 5 tasks | on | 7.6 | 7.6 | +0.02 | [-1.01, +1.05] | **criterion met (floor: low information)** |
| Qwen3.6-35B | pooled, 5 tasks | on | 74.3 | 71.0 | -3.27 | [-5.07, -1.47] | **criterion not met (unresolved)** |

#### T8a. Replication, tool cells: tool-verified success, delivered rerun vs main sweep

Δ = rerun − main, paired on the trial key (0 unpaired rows); 90% domain-cluster bootstrap; criterion met = interval inside [−5, +5] (prereg §3). The rerun differs from the main sweep in four ways (readout §2: full answer storage, the final-request retry, the leaked-prefix strip, and vLLM 0.20.2 for the 9B), so it is a separate-apparatus replication. The last column is descriptive: calling (`tool_selected`) on both sides, paired Δ with the same bootstrap. The readout's own "invocation" column counts any tool call, not the task's tool, so its rerun values differ from this column in three cells (readout vs here: 35B solve plain 87.7 vs 82.7, 9B simulate plain 81.3 vs 80.7, 9B validate_plan plain 97.9 vs 97.8); counted as any tool call, this run matches the readout in all 30.

| model | task | arm | main sweep | rerun | Δ (rerun − main) | 90% CI | ±5 criterion | calling, main → rerun (Δ) |
|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | plain | 99.3 | 98.7 | -0.7 | [-1.3, +0.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Gemma-26B | solve | steered | 98.7 | 100.0 | +1.3 | [+0.0, +3.3] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Gemma-26B | validate_domain | plain | 97.5 | 97.8 | +0.3 | [+0.0, +0.8] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Gemma-26B | validate_domain | steered | 98.3 | 98.9 | +0.6 | [+0.0, +1.7] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Gemma-26B | validate_problem | plain | 99.7 | 99.5 | -0.2 | [-0.7, +0.3] | met | 99.8 → 100.0 (+0.2 [+0.0, +0.5]) |
| Gemma-26B | validate_problem | steered | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Gemma-26B | validate_plan | plain | 20.6 | 19.9 | -0.7 | [-1.4, +0.0] | met | 20.7 → 20.0 (-0.7 [-1.5, +0.0]) |
| Gemma-26B | validate_plan | steered | 92.6 | 92.1 | -0.4 | [-1.1, +0.1] | met | 93.6 → 93.1 (-0.5 [-1.1, -0.1]) |
| Gemma-26B | simulate | plain | 91.7 | 90.7 | -1.0 | [-3.3, +1.3] | met | 99.7 → 99.7 (+0.0 [+0.0, +0.0]) |
| Gemma-26B | simulate | steered | 90.7 | 90.7 | +0.0 | [-1.3, +1.7] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | solve | plain | 99.3 | 100.0 | +0.7 | [+0.0, +2.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | solve | steered | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | validate_domain | plain | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | validate_domain | steered | 100.0 | 100.0 | +0.0 | [+0.0, +0.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | validate_problem | plain | 95.2 | 94.8 | -0.3 | [-0.7, +0.0] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | validate_problem | steered | 90.2 | 91.0 | +0.8 | [+0.0, +1.7] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | validate_plan | plain | 93.2 | 92.5 | -0.6 | [-1.2, +0.0] | met | 97.9 → 97.8 (-0.1 [-0.6, +0.5]) |
| Qwen3.5-9B | validate_plan | steered | 96.0 | 96.1 | +0.1 | [-0.2, +0.4] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.5-9B | simulate | plain | 65.0 | 68.0 | +3.0 | [-0.3, +6.7] | **not met (unresolved)** | 80.0 → 80.7 (+0.7 [-1.3, +2.7]) |
| Qwen3.5-9B | simulate | steered | 83.0 | 87.0 | +4.0 | [+1.7, +6.7] | **not met (unresolved)** | 99.7 → 100.0 (+0.3 [+0.0, +1.0]) |
| Qwen3.6-35B | solve | plain | 63.0 | 82.3 | +19.3 | [+14.3, +24.7] | **not met (unresolved)** | 68.0 → 82.7 (+14.7 [+10.7, +19.3]) |
| Qwen3.6-35B | solve | steered | 92.0 | 99.3 | +7.3 | [+3.7, +11.3] | **not met (unresolved)** | 93.7 → 99.7 (+6.0 [+2.7, +9.7]) |
| Qwen3.6-35B | validate_domain | plain | 98.9 | 98.6 | -0.3 | [-1.7, +1.1] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.6-35B | validate_domain | steered | 99.7 | 99.4 | -0.3 | [-1.4, +0.6] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.6-35B | validate_problem | plain | 96.8 | 97.2 | +0.3 | [-0.8, +1.5] | met | 98.5 → 99.3 (+0.8 [+0.2, +1.5]) |
| Qwen3.6-35B | validate_problem | steered | 97.3 | 97.3 | +0.0 | [-1.0, +1.2] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |
| Qwen3.6-35B | validate_plan | plain | 82.2 | 82.4 | +0.2 | [-3.9, +4.3] | met | 82.9 → 83.1 (+0.2 [-3.9, +4.3]) |
| Qwen3.6-35B | validate_plan | steered | 99.3 | 99.1 | -0.1 | [-0.5, +0.2] | met | 99.9 → 100.0 (+0.1 [+0.0, +0.2]) |
| Qwen3.6-35B | simulate | plain | 74.7 | 94.0 | +19.3 | [+11.7, +27.7] | **not met (unresolved)** | 76.3 → 99.7 (+23.3 [+16.7, +30.7]) |
| Qwen3.6-35B | simulate | steered | 97.0 | 95.7 | -1.3 | [-2.3, -0.3] | met | 100.0 → 100.0 (+0.0 [+0.0, +0.0]) |

<!-- gen:iss027_t8a -->
**ISS-027, post hoc (grader case fault; the frozen values above stay).** Tool-verified cells that move with plan names case-folded (point estimates; the paired intervals and the ±5 verdicts are not recomputed): Qwen3.5-9B simulate plain: main 65.0 → 65.3, rerun 68.0 → 68.0, Δ +3.0 → +2.7; Gemma-26B validate_plan steered: main 92.6 → 92.6, rerun 92.1 → 92.1, Δ -0.4 → -0.5; Gemma-26B simulate plain: main 91.7 → 95.0, rerun 90.7 → 93.7, Δ -1.0 → -1.3; Gemma-26B simulate steered: main 90.7 → 94.0, rerun 90.7 → 93.7, Δ +0.0 → -0.3; Qwen3.6-35B simulate plain: main 74.7 → 74.7, rerun 94.0 → 94.7, Δ +19.3 → +20.0; Qwen3.6-35B simulate steered: main 97.0 → 97.0, rerun 95.7 → 96.3, Δ -1.3 → -0.7. Calling does not change.
<!-- /gen:iss027_t8a -->

#### T8b. Replication, unaided cells: harness online grade, rerun Part C vs main sweep (simulate excluded, prereg §2)

| model | task | main sweep | rerun | Δ (rerun − main) | 90% CI | ±5 criterion |
|---|---|---|---|---|---|---|
| Gemma-26B | solve | 7.7 | 9.7 | +2.0 | [+0.0, +4.3] | met |
| Gemma-26B | validate_domain | 77.8 | 79.4 | +1.7 | [+0.0, +3.6] | met |
| Gemma-26B | validate_problem | 74.8 | 76.2 | +1.3 | [-0.5, +3.2] | met |
| Gemma-26B | validate_plan | 87.8 | 88.3 | +0.5 | [-0.6, +1.5] | met |
| Qwen3.5-9B | solve | 10.7 | 10.7 | +0.0 | [-2.7, +2.7] | met |
| Qwen3.5-9B | validate_domain | 25.6 | 26.1 | +0.6 | [-0.3, +1.4] | met |
| Qwen3.5-9B | validate_problem | 65.7 | 65.8 | +0.2 | [-1.5, +1.8] | met |
| Qwen3.5-9B | validate_plan | 79.7 | 79.8 | +0.1 | [-0.8, +0.9] | met |
| Qwen3.6-35B | solve | 9.3 | 10.0 | +0.7 | [-1.7, +3.0] | met |
| Qwen3.6-35B | validate_domain | 67.8 | 76.4 | +8.6 | [+2.8, +14.7] | **not met (unresolved)** |
| Qwen3.6-35B | validate_problem | 75.7 | 74.7 | -1.0 | [-2.5, +0.5] | met |
| Qwen3.6-35B | validate_plan | 90.9 | 90.4 | -0.5 | [-1.8, +0.9] | met |

Counts: tool cells 25 of 30 met (Gemma 10/10, Qwen 15/20), 27 of 30 within ±5 by point estimate; unaided cells 11 of 12 met, 11 of 12 within ±5 by point estimate. No row was unpaired on either side.

#### T8c. Call-state flips, main sweep vs delivered rerun (added 2026-11-09; in no tex yet)

Provenance: `tools/reanalysis/s1_call_flips.py` (rows through the frozen rerun package's loader, read-only).
Per tool cell, the trials whose call state (`tool_selected`) differs between the two runs, paired on the
trial key. Descriptive, post hoc; the calling column of T8a carries the paired interval.
Decision (Omer, 2026-11-09): quote both runs for the 35B plain calling rate (68.0 and 82.7) and keep
"bigger calls less" as a direction only.

<!-- gen:s1_call_flips -->
| figure | **quote this** | source | do NOT quote |
|---|---|---|---|
| call-state flips, 35B, plain arm (descriptive) | solve **88/300 (29.3%; 22 called → not, 66 not → called; calls 68.0 → 82.7)**; simulate **72/300 (24.0%; 1 called → not, 71 not → called; calls 76.3 → 99.7)**; validate_plan **397/3,000 (13.2%; 195 called → not, 202 not → called; calls 82.9 → 83.1)**. Every other 35B cell ≤ 6.7%; 9B and Gemma ≤ 3.3% in every cell | `s1_call_flips.py`; table below | **a single-run 35B plain calling rate alone** (Omer 2026-11-09: quote both runs, 68.0 and 82.7, and keep "bigger calls less" as a direction only) |
| prompt check on the paired rows | prompt tokens equal on **2,955 of 2,955** single-turn pairs (rows that called a tool sum the prompt over turns and are not compared) | `s1_call_flips.py` | none |

| model | task | arm | n paired | calls, main | calls, rerun | called → not | not → called | flips (% of n) | net | any-call flips | prompt equal, single-turn pairs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | plain | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | solve | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_domain | plain | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_domain | steered | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_problem | plain | 600 | 599 (99.8) | 600 (100.0) | 0 | 1 | 1 (0.2) | +1 | 1 | 0 / 0 |
| Gemma-26B | validate_problem | steered | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Gemma-26B | validate_plan | plain | 3,000 | 622 (20.7) | 600 (20.0) | 56 | 34 | 90 (3.0) | -22 | 90 | 2,344 / 2,344 |
| Gemma-26B | validate_plan | steered | 3,000 | 2,808 (93.6) | 2,792 (93.1) | 37 | 21 | 58 (1.9) | -16 | 58 | 171 / 171 |
| Gemma-26B | simulate | plain | 300 | 299 (99.7) | 299 (99.7) | 0 | 0 | 0 (0.0) | +0 | 0 | 1 / 1 |
| Gemma-26B | simulate | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | solve | plain | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | solve | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_domain | plain | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_domain | steered | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_problem | plain | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_problem | steered | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | validate_plan | plain | 3,000 | 2,937 (97.9) | 2,935 (97.8) | 13 | 11 | 24 (0.8) | -2 | 22 | 52 / 52 |
| Qwen3.5-9B | validate_plan | steered | 3,000 | 3,000 (100.0) | 3,000 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.5-9B | simulate | plain | 300 | 240 (80.0) | 242 (80.7) | 4 | 6 | 10 (3.3) | +2 | 9 | 53 / 53 |
| Qwen3.5-9B | simulate | steered | 300 | 299 (99.7) | 300 (100.0) | 0 | 1 | 1 (0.3) | +1 | 1 | 0 / 0 |
| Qwen3.6-35B | solve | plain | 300 | 204 (68.0) | 248 (82.7) | 22 | 66 | 88 (29.3) | +44 | 61 | 20 / 20 |
| Qwen3.6-35B | solve | steered | 300 | 281 (93.7) | 299 (99.7) | 1 | 19 | 20 (6.7) | +18 | 10 | 0 / 0 |
| Qwen3.6-35B | validate_domain | plain | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.6-35B | validate_domain | steered | 360 | 360 (100.0) | 360 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.6-35B | validate_problem | plain | 600 | 591 (98.5) | 596 (99.3) | 1 | 6 | 7 (1.2) | +5 | 7 | 3 / 3 |
| Qwen3.6-35B | validate_problem | steered | 600 | 600 (100.0) | 600 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |
| Qwen3.6-35B | validate_plan | plain | 3,000 | 2,487 (82.9) | 2,494 (83.1) | 195 | 202 | 397 (13.2) | +7 | 396 | 311 / 311 |
| Qwen3.6-35B | validate_plan | steered | 3,000 | 2,997 (99.9) | 3,000 (100.0) | 0 | 3 | 3 (0.1) | +3 | 3 | 0 / 0 |
| Qwen3.6-35B | simulate | plain | 300 | 229 (76.3) | 299 (99.7) | 1 | 71 | 72 (24.0) | +70 | 72 | 0 / 0 |
| Qwen3.6-35B | simulate | steered | 300 | 300 (100.0) | 300 (100.0) | 0 | 0 | 0 (0.0) | +0 | 0 | 0 / 0 |

Unpaired rows: 0. Rows with `tool_selected` null (counted as not called): 0. Prompt tokens equal on 2,955 of 2,955 single-turn pairs.

Largest flip share per model: Gemma-26B 3.0%; Qwen3.5-9B 3.3%; Qwen3.6-35B 29.3%.
<!-- /gen:s1_call_flips -->

### Study 1 breakdowns: per wording, per track, per domain (plan step C3a; added 2026-11-09; in no tex yet)

Generated by `tools/reanalysis/s1_breakdowns_md.py` (rerun: `python3 tools/reanalysis/s1_breakdowns_md.py --results <abs path to results>`); `.tex` fragments in `tools/reanalysis/out/tex/s1_*.tex`. Descriptive breakdowns of the T1 and T2 cells: no test, no verdict.

<!-- BEGIN GENERATED: s1_breakdowns_md.py (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/s1_breakdowns_md.py`; do not edit between the markers, rerun the script. Self-check: 1305 of 1305 pass (75 pooled counts equal T1 and T2 above; every per-wording, per-track and per-domain count equals the committed `tools/reanalysis/out/breakdowns_cost/*_sweep5v2-live.csv` of `bc_per_wording.py` and `bc_per_domain.py`; 10 35B main-sweep calling rates equal the T8a calling column; 5 ISS-027 before/after rates follow from the pooled counts).*

**Apparatus: Study 1 only** (main sweep, `results/sweep5v2-live`, think=off, the headline models; never pooled with a Study 2 table). **Mechanism layer only**: *unaided* = the no-tools cell's online grade (wordings v11–13); *calling* = `tool_selected` (the task's own tool was called); *tool-verified* = `success` on the tools cell. **Why no delivered tool-arm column**: the breakdowns of 2026-10-02 (`reference/reanalysis_breakdowns_cost.md`) also showed the overlay's delivered bounds for the tool arms; that surface is retired for the open models in Study 1 (Rules above), and on the main sweep many of those cells are wide censoring bounds set by the 500-character answer storage. The delivered surface on the fixed setup is in the Study 2 tables below. Intervals as in the Rules above (domain bootstrap 95%; † = Wilson at 0 or 100%); a track subset resamples only its own domains.

**Unaided simulate.** ¶ = unaided simulate, format-exact on the shared-budget corpus (the qualifier of the Job 2 row: "0/3,000 format-exact on the shared-budget corpus"). An answer cut by the output budget counts as a failure, so never read this 0 as a capability floor; the capability figure is the decoupled control, 22–40% content-correct at ≥4B.

**Grader caveat.** ISS-027 (open, `OPEN_ISSUES.md`): the plan grader (pyval 0.1.5) is case-sensitive on object and action names, and PDDL is case-insensitive, so a plan that copies the capitals of the satellite p02–p05 or pogo_stick fixtures is graded wrong. This hits unaided solve and the simulate and validate_plan tool arms. The success cells are the frozen grades; a corrected figure goes beside them post hoc. Pooled cells that would move (think=off): Qwen3.5-9B simulate tool-verified plain 65.0 → 65.3 (+1 trial); Gemma-26B simulate tool-verified plain 91.7 → 95.0 (+10 trials); Gemma-26B simulate tool-verified steered 90.7 → 94.0 (+10 trials); Gemma-26B validate_plan tool-verified steered 92.6 → 92.6 (+1 trial); Qwen3.5-9B solve unaided 10.7 → 11.3 (+2 trials). No other pooled cell moves, but a single wording or domain cell can move more than its pooled cell. Calling is not affected.

**35B calling.** Qwen3.6-35B calling cells: main sweep alone. The 35B calling rate is quoted as both runs, main sweep and delivered rerun (decided 2026-11-09, `STATUS.md`), and "bigger calls less" stays a direction only; see S1-Q, T8a and T8c (call-state flips).

#### S1-Q. What to quote from these tables

| figure | **quote this** | do NOT quote |
|---|---|---|
| Gemma validate_plan calling, plain, by wording (descriptive) | w1 **31.2** (312/1000) · w2 **26.8** (268/1000) · w3 **4.2** (42/1000); pooled (T2) 20.7%, their mean (equal n) | "21%" without its wording range; a single wording's rate as a test |
| unaided solve, by wording (descriptive) | Qwen3.5-9B w1 **2.0** (2/100) · w2 **29.0** (29/100) · w3 **1.0** (1/100); Gemma-26B w1 **1.0** (1/100) · w2 **16.0** (16/100) · w3 **6.0** (6/100); Qwen3.6-35B w1 **0.0** (0/100) · w2 **28.0** (28/100) · w3 **0.0** (0/100) (frozen grades; ISS-027 would add 2 Qwen3.5-9B trials over the three wordings) | the pooled unaided solve rate (T1) as if it did not depend on the wording |
| Qwen3.6-35B calling, any cell of S1-W, S1-T or S1-D | no single-run figure. Quote both runs: solve plain **68.0** (main sweep) and **82.7** (delivered rerun), Δ +14.7 [+10.7, +19.3]; solve steered **93.7** (main sweep) and **99.7** (delivered rerun), Δ +6.0 [+2.7, +9.7]; simulate plain **76.3** (main sweep) and **99.7** (delivered rerun), Δ +23.3 [+16.7, +30.7] (T8a; the trials that flip are in T8c). "Bigger calls less" is a direction only (decided 2026-11-09, `STATUS.md`) | a 35B per-wording, per-track or per-domain calling rate from the main sweep alone; the 9B-vs-35B size inversion as a measured effect |
| success cells hit by ISS-027 (grader case fault) | the frozen value, with the ISS-027 caveat; corrected value beside it, post hoc: Qwen3.5-9B simulate tool-verified plain 65.0 → 65.3 (+1 trial); Gemma-26B simulate tool-verified plain 91.7 → 95.0 (+10 trials); Gemma-26B simulate tool-verified steered 90.7 → 94.0 (+10 trials); Gemma-26B validate_plan tool-verified steered 92.6 → 92.6 (+1 trial); Qwen3.5-9B solve unaided 10.7 → 11.3 (+2 trials) | a re-graded value in place of the frozen one; the frozen value without the caveat |
| unaided simulate cells (¶) | 0.0 **format-exact on the shared-budget corpus**, always with that qualifier (Job 2 row) | a bare 0.0 or 0% read as a capability floor |
| tool-arm figures in these tables | tool-verified and calling only | any Study 1 delivered tool-arm figure from `bc_per_wording.py` or `bc_per_domain.py` (retired surface) |

#### S1-W. Per wording: calling beside success (think=off)

Wording w1 = plain v11 / steered v14 (v14 is v11 plus one sentence naming the tool), w2 = v12 / v15, w3 = v13 / v16; unaided uses the plain wording. ¶, ISS-027 and the 35B calling cells: see the caveats above.

| model | task | wording | n | unaided | calling, plain | tool-verified, plain | calling, steered | tool-verified, steered |
|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | w1 | 100 | 2.0 [0.0, 5.0] | 100.0 [96.3, 100.0]† | 99.0 [97.0, 100.0] | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† |
| Qwen3.5-9B | solve | w2 | 100 | 29.0 [16.0, 43.0] | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† |
| Qwen3.5-9B | solve | w3 | 100 | 1.0 [0.0, 3.0] | 100.0 [96.3, 100.0]† | 99.0 [97.0, 100.0] | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† |
| Qwen3.5-9B | validate_domain | w1 | 120 | 32.5 [20.0, 48.3] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† |
| Qwen3.5-9B | validate_domain | w2 | 120 | 24.2 [15.0, 37.5] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† |
| Qwen3.5-9B | validate_domain | w3 | 120 | 20.0 [14.2, 29.2] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† |
| Qwen3.5-9B | validate_problem | w1 | 200 | 67.0 [60.0, 73.0] | 100.0 [98.1, 100.0]† | 96.0 [94.0, 98.0] | 100.0 [98.1, 100.0]† | 91.0 [85.5, 95.0] |
| Qwen3.5-9B | validate_problem | w2 | 200 | 61.5 [53.5, 69.0] | 100.0 [98.1, 100.0]† | 95.0 [93.0, 97.0] | 100.0 [98.1, 100.0]† | 90.0 [82.0, 96.0] |
| Qwen3.5-9B | validate_problem | w3 | 200 | 68.5 [60.5, 76.0] | 100.0 [98.1, 100.0]† | 94.5 [92.5, 96.5] | 100.0 [98.1, 100.0]† | 89.5 [81.5, 96.0] |
| Qwen3.5-9B | validate_plan | w1 | 1000 | 80.5 [74.0, 86.6] | 98.8 [96.9, 100.0] | 93.7 [88.5, 97.6] | 100.0 [99.6, 100.0]† | 95.8 [90.7, 99.1] |
| Qwen3.5-9B | validate_plan | w2 | 1000 | 77.7 [71.3, 83.8] | 100.0 [99.6, 100.0]† | 95.5 [91.5, 98.6] | 100.0 [99.6, 100.0]† | 95.8 [91.6, 99.0] |
| Qwen3.5-9B | validate_plan | w3 | 1000 | 81.0 [75.1, 86.9] | 94.9 [85.8, 100.0] | 90.3 [80.7, 97.0] | 100.0 [99.6, 100.0]† | 96.5 [93.3, 99.0] |
| Qwen3.5-9B | simulate | w1 | 100 | 0.0 [0.0, 3.7]†¶ | 100.0 [96.3, 100.0]† | 83.0 [72.0, 93.0] | 100.0 [96.3, 100.0]† | 81.0 [69.0, 91.0] |
| Qwen3.5-9B | simulate | w2 | 100 | 0.0 [0.0, 3.7]†¶ | 40.0 [28.0, 52.0] | 30.0 [19.0, 41.0] | 99.0 [97.0, 100.0] | 84.0 [74.0, 92.0] |
| Qwen3.5-9B | simulate | w3 | 100 | 0.0 [0.0, 3.7]†¶ | 100.0 [96.3, 100.0]† | 82.0 [70.0, 93.0] | 100.0 [96.3, 100.0]† | 84.0 [73.0, 94.0] |
| Gemma-26B | solve | w1 | 100 | 1.0 [0.0, 3.0] | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† | 97.0 [91.0, 100.0] |
| Gemma-26B | solve | w2 | 100 | 16.0 [8.0, 26.0] | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† | 100.0 [96.3, 100.0]† |
| Gemma-26B | solve | w3 | 100 | 6.0 [2.0, 10.0] | 100.0 [96.3, 100.0]† | 98.0 [95.0, 100.0] | 100.0 [96.3, 100.0]† | 99.0 [97.0, 100.0] |
| Gemma-26B | validate_domain | w1 | 120 | 75.0 [60.0, 88.3] | 100.0 [96.9, 100.0]† | 98.3 [95.8, 100.0] | 100.0 [96.9, 100.0]† | 98.3 [95.8, 100.0] |
| Gemma-26B | validate_domain | w2 | 120 | 80.8 [69.2, 90.8] | 100.0 [96.9, 100.0]† | 97.5 [95.0, 100.0] | 100.0 [96.9, 100.0]† | 98.3 [95.8, 100.0] |
| Gemma-26B | validate_domain | w3 | 120 | 77.5 [65.8, 88.3] | 100.0 [96.9, 100.0]† | 96.7 [93.3, 99.2] | 100.0 [96.9, 100.0]† | 98.3 [95.8, 100.0] |
| Gemma-26B | validate_problem | w1 | 200 | 73.5 [66.0, 80.5] | 100.0 [98.1, 100.0]† | 99.5 [98.5, 100.0] | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† |
| Gemma-26B | validate_problem | w2 | 200 | 76.0 [71.0, 81.5] | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† |
| Gemma-26B | validate_problem | w3 | 200 | 75.0 [67.5, 82.0] | 99.5 [98.5, 100.0] | 99.5 [98.5, 100.0] | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† |
| Gemma-26B | validate_plan | w1 | 1000 | 88.0 [83.9, 91.7] | 31.2 [14.8, 49.5] | 30.9 [14.6, 49.2] | 94.2 [85.5, 100.0] | 93.4 [84.8, 98.9] |
| Gemma-26B | validate_plan | w2 | 1000 | 88.6 [84.9, 91.8] | 26.8 [10.5, 45.0] | 26.6 [10.4, 44.9] | 93.0 [83.1, 100.0] | 92.3 [82.4, 99.0] |
| Gemma-26B | validate_plan | w3 | 1000 | 86.9 [82.0, 91.0] | 4.2 [0.0, 10.4] | 4.2 [0.0, 10.4] | 93.6 [83.8, 100.0] | 92.0 [82.4, 98.2] |
| Gemma-26B | simulate | w1 | 100 | 0.0 [0.0, 3.7]†¶ | 100.0 [96.3, 100.0]† | 90.0 [83.0, 96.0] | 100.0 [96.3, 100.0]† | 90.0 [81.0, 97.0] |
| Gemma-26B | simulate | w2 | 100 | 0.0 [0.0, 3.7]†¶ | 99.0 [97.0, 100.0] | 90.0 [82.0, 97.0] | 100.0 [96.3, 100.0]† | 92.0 [84.0, 98.0] |
| Gemma-26B | simulate | w3 | 100 | 0.0 [0.0, 3.7]†¶ | 100.0 [96.3, 100.0]† | 95.0 [90.0, 99.0] | 100.0 [96.3, 100.0]† | 90.0 [82.0, 97.0] |
| Qwen3.6-35B | solve | w1 | 100 | 0.0 [0.0, 3.7]† | 80.0 [73.0, 87.0] | 73.0 [64.0, 82.0] | 96.0 [92.0, 99.0] | 95.0 [91.0, 98.0] |
| Qwen3.6-35B | solve | w2 | 100 | 28.0 [19.0, 37.0] | 63.0 [50.0, 76.0] | 59.0 [46.0, 72.0] | 94.0 [89.0, 98.0] | 91.0 [85.0, 96.0] |
| Qwen3.6-35B | solve | w3 | 100 | 0.0 [0.0, 3.7]† | 61.0 [47.0, 74.0] | 57.0 [44.0, 69.0] | 91.0 [83.0, 98.0] | 90.0 [81.0, 97.0] |
| Qwen3.6-35B | validate_domain | w1 | 120 | 66.7 [55.8, 77.5] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† |
| Qwen3.6-35B | validate_domain | w2 | 120 | 64.2 [50.0, 77.5] | 100.0 [96.9, 100.0]† | 99.2 [97.5, 100.0] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† |
| Qwen3.6-35B | validate_domain | w3 | 120 | 72.5 [60.0, 84.2] | 100.0 [96.9, 100.0]† | 97.5 [93.3, 100.0] | 100.0 [96.9, 100.0]† | 99.2 [97.5, 100.0] |
| Qwen3.6-35B | validate_problem | w1 | 200 | 73.5 [69.5, 77.5] | 98.5 [97.0, 100.0] | 96.5 [94.0, 99.0] | 100.0 [98.1, 100.0]† | 97.5 [95.5, 99.5] |
| Qwen3.6-35B | validate_problem | w2 | 200 | 76.0 [71.5, 80.0] | 100.0 [98.1, 100.0]† | 98.0 [96.0, 99.5] | 100.0 [98.1, 100.0]† | 97.0 [95.0, 99.0] |
| Qwen3.6-35B | validate_problem | w3 | 200 | 77.5 [70.5, 84.0] | 97.0 [95.0, 99.0] | 96.0 [93.5, 98.5] | 100.0 [98.1, 100.0]† | 97.5 [95.5, 99.0] |
| Qwen3.6-35B | validate_plan | w1 | 1000 | 91.0 [87.3, 94.4] | 87.8 [78.9, 94.8] | 87.6 [78.7, 94.6] | 99.8 [99.4, 100.0] | 99.3 [98.5, 100.0] |
| Qwen3.6-35B | validate_plan | w2 | 1000 | 90.5 [87.4, 93.4] | 86.3 [76.2, 94.6] | 85.6 [75.5, 94.0] | 100.0 [99.6, 100.0]† | 99.2 [98.4, 99.8] |
| Qwen3.6-35B | validate_plan | w3 | 1000 | 91.2 [88.1, 94.1] | 74.6 [61.5, 86.2] | 73.3 [60.0, 85.1] | 99.9 [99.7, 100.0] | 99.3 [98.7, 99.8] |
| Qwen3.6-35B | simulate | w1 | 100 | 0.0 [0.0, 3.7]†¶ | 96.0 [91.0, 100.0] | 93.0 [87.0, 98.0] | 100.0 [96.3, 100.0]† | 96.0 [92.0, 99.0] |
| Qwen3.6-35B | simulate | w2 | 100 | 0.0 [0.0, 3.7]†¶ | 59.0 [45.0, 72.0] | 59.0 [45.0, 72.0] | 100.0 [96.3, 100.0]† | 97.0 [92.0, 100.0] |
| Qwen3.6-35B | simulate | w3 | 100 | 0.0 [0.0, 3.7]†¶ | 74.0 [60.0, 86.0] | 72.0 [59.0, 84.0] | 100.0 [96.3, 100.0]† | 98.0 [95.0, 100.0] |

Range over the three wordings, low–high (max − min, points):

| model | task | unaided | calling, plain | tool-verified, plain | calling, steered | tool-verified, steered |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | 1.0–29.0 (28.0) | 100.0–100.0 (0.0) | 99.0–100.0 (1.0) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) |
| Qwen3.5-9B | validate_domain | 20.0–32.5 (12.5) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) |
| Qwen3.5-9B | validate_problem | 61.5–68.5 (7.0) | 100.0–100.0 (0.0) | 94.5–96.0 (1.5) | 100.0–100.0 (0.0) | 89.5–91.0 (1.5) |
| Qwen3.5-9B | validate_plan | 77.7–81.0 (3.3) | 94.9–100.0 (5.1) | 90.3–95.5 (5.2) | 100.0–100.0 (0.0) | 95.8–96.5 (0.7) |
| Qwen3.5-9B | simulate | 0.0–0.0 (0.0)¶ | 40.0–100.0 (60.0) | 30.0–83.0 (53.0) | 99.0–100.0 (1.0) | 81.0–84.0 (3.0) |
| Gemma-26B | solve | 1.0–16.0 (15.0) | 100.0–100.0 (0.0) | 98.0–100.0 (2.0) | 100.0–100.0 (0.0) | 97.0–100.0 (3.0) |
| Gemma-26B | validate_domain | 75.0–80.8 (5.8) | 100.0–100.0 (0.0) | 96.7–98.3 (1.7) | 100.0–100.0 (0.0) | 98.3–98.3 (0.0) |
| Gemma-26B | validate_problem | 73.5–76.0 (2.5) | 99.5–100.0 (0.5) | 99.5–100.0 (0.5) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) |
| Gemma-26B | validate_plan | 86.9–88.6 (1.7) | 4.2–31.2 (27.0) | 4.2–30.9 (26.7) | 93.0–94.2 (1.2) | 92.0–93.4 (1.4) |
| Gemma-26B | simulate | 0.0–0.0 (0.0)¶ | 99.0–100.0 (1.0) | 90.0–95.0 (5.0) | 100.0–100.0 (0.0) | 90.0–92.0 (2.0) |
| Qwen3.6-35B | solve | 0.0–28.0 (28.0) | 61.0–80.0 (19.0) | 57.0–73.0 (16.0) | 91.0–96.0 (5.0) | 90.0–95.0 (5.0) |
| Qwen3.6-35B | validate_domain | 64.2–72.5 (8.3) | 100.0–100.0 (0.0) | 97.5–100.0 (2.5) | 100.0–100.0 (0.0) | 99.2–100.0 (0.8) |
| Qwen3.6-35B | validate_problem | 73.5–77.5 (4.0) | 97.0–100.0 (3.0) | 96.0–98.0 (2.0) | 100.0–100.0 (0.0) | 97.0–97.5 (0.5) |
| Qwen3.6-35B | validate_plan | 90.5–91.2 (0.7) | 74.6–87.8 (13.2) | 73.3–87.6 (14.3) | 99.8–100.0 (0.2) | 99.2–99.3 (0.1) |
| Qwen3.6-35B | simulate | 0.0–0.0 (0.0)¶ | 59.0–96.0 (37.0) | 59.0–93.0 (34.0) | 100.0–100.0 (0.0) | 96.0–98.0 (2.0) |

#### S1-T. Classical against numeric (think=off, pooled over wordings)

Track = the top-level folder under `domains/` (the harness's own label; it picks the oracle planner). classical: 10 domains, numeric: 10 domains. ¶, ISS-027 and the 35B calling cells: see the caveats above.

| model | task | track | n per arm | unaided | calling, plain | tool-verified, plain | calling, steered | tool-verified, steered |
|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | solve | classical | 150 | 9.3 [4.0, 16.0] | 100.0 [97.5, 100.0]† | 100.0 [97.5, 100.0]† | 100.0 [97.5, 100.0]† | 100.0 [97.5, 100.0]† |
| Qwen3.5-9B | solve | numeric | 150 | 12.0 [6.0, 18.0] | 100.0 [97.5, 100.0]† | 98.7 [96.0, 100.0] | 100.0 [97.5, 100.0]† | 100.0 [97.5, 100.0]† |
| Qwen3.5-9B | validate_domain | classical | 180 | 35.6 [19.4, 54.4] | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† |
| Qwen3.5-9B | validate_domain | numeric | 180 | 15.6 [13.9, 16.7] | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† |
| Qwen3.5-9B | validate_problem | classical | 300 | 69.3 [59.0, 77.0] | 100.0 [98.7, 100.0]† | 95.7 [93.0, 98.3] | 100.0 [98.7, 100.0]† | 94.3 [90.3, 97.7] |
| Qwen3.5-9B | validate_problem | numeric | 300 | 62.0 [53.7, 69.3] | 100.0 [98.7, 100.0]† | 94.7 [91.7, 97.7] | 100.0 [98.7, 100.0]† | 86.0 [74.0, 96.0] |
| Qwen3.5-9B | validate_plan | classical | 1500 | 80.5 [72.0, 88.3] | 99.9 [99.8, 100.0] | 98.3 [95.5, 99.9] | 100.0 [99.7, 100.0]† | 99.1 [97.7, 100.0] |
| Qwen3.5-9B | validate_plan | numeric | 1500 | 79.0 [70.5, 86.9] | 95.9 [88.5, 100.0] | 88.1 [79.7, 95.3] | 100.0 [99.7, 100.0]† | 92.9 [85.7, 98.7] |
| Qwen3.5-9B | simulate | classical | 150 | 0.0 [0.0, 2.5]†¶ | 77.3 [72.7, 82.0] | 64.7 [52.7, 74.7] | 99.3 [98.0, 100.0] | 88.0 [75.3, 98.0] |
| Qwen3.5-9B | simulate | numeric | 150 | 0.0 [0.0, 2.5]†¶ | 82.7 [76.7, 88.7] | 65.3 [52.0, 76.0] | 100.0 [97.5, 100.0]† | 78.0 [62.0, 90.7] |
| Gemma-26B | solve | classical | 150 | 6.7 [1.3, 13.3] | 100.0 [97.5, 100.0]† | 99.3 [98.0, 100.0] | 100.0 [97.5, 100.0]† | 100.0 [97.5, 100.0]† |
| Gemma-26B | solve | numeric | 150 | 8.7 [4.0, 14.0] | 100.0 [97.5, 100.0]† | 99.3 [98.0, 100.0] | 100.0 [97.5, 100.0]† | 97.3 [93.3, 100.0] |
| Gemma-26B | validate_domain | classical | 180 | 90.0 [85.6, 94.4] | 100.0 [97.9, 100.0]† | 98.3 [95.0, 100.0] | 100.0 [97.9, 100.0]† | 98.3 [95.0, 100.0] |
| Gemma-26B | validate_domain | numeric | 180 | 65.6 [46.1, 85.0] | 100.0 [97.9, 100.0]† | 96.7 [92.8, 100.0] | 100.0 [97.9, 100.0]† | 98.3 [95.6, 100.0] |
| Gemma-26B | validate_problem | classical | 300 | 73.7 [65.3, 82.0] | 99.7 [99.0, 100.0] | 99.7 [99.0, 100.0] | 100.0 [98.7, 100.0]† | 100.0 [98.7, 100.0]† |
| Gemma-26B | validate_problem | numeric | 300 | 76.0 [67.3, 83.7] | 100.0 [98.7, 100.0]† | 99.7 [99.0, 100.0] | 100.0 [98.7, 100.0]† | 100.0 [98.7, 100.0]† |
| Gemma-26B | validate_plan | classical | 1500 | 88.1 [80.5, 93.8] | 24.4 [6.6, 44.7] | 24.3 [6.3, 44.6] | 89.0 [72.6, 100.0] | 88.4 [71.9, 99.5] |
| Gemma-26B | validate_plan | numeric | 1500 | 87.5 [83.9, 91.5] | 17.1 [3.5, 35.1] | 16.9 [3.4, 34.8] | 98.2 [94.6, 100.0] | 96.7 [93.1, 99.2] |
| Gemma-26B | simulate | classical | 150 | 0.0 [0.0, 2.5]†¶ | 99.3 [98.0, 100.0] | 96.0 [90.0, 100.0] | 100.0 [97.5, 100.0]† | 96.0 [90.7, 100.0] |
| Gemma-26B | simulate | numeric | 150 | 0.0 [0.0, 2.5]†¶ | 100.0 [97.5, 100.0]† | 87.3 [78.0, 95.3] | 100.0 [97.5, 100.0]† | 85.3 [72.0, 96.0] |
| Qwen3.6-35B | solve | classical | 150 | 6.7 [3.3, 10.0] | 57.3 [50.7, 64.0] | 56.0 [48.7, 64.0] | 91.3 [84.0, 97.3] | 90.0 [82.0, 96.7] |
| Qwen3.6-35B | solve | numeric | 150 | 12.0 [8.0, 16.7] | 78.7 [66.0, 88.7] | 70.0 [56.0, 83.3] | 96.0 [91.3, 100.0] | 94.0 [88.0, 100.0] |
| Qwen3.6-35B | validate_domain | classical | 180 | 82.2 [75.0, 88.9] | 100.0 [97.9, 100.0]† | 98.9 [96.7, 100.0] | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† |
| Qwen3.6-35B | validate_domain | numeric | 180 | 53.3 [36.7, 70.0] | 100.0 [97.9, 100.0]† | 98.9 [96.7, 100.0] | 100.0 [97.9, 100.0]† | 99.4 [98.3, 100.0] |
| Qwen3.6-35B | validate_problem | classical | 300 | 74.0 [66.3, 81.0] | 98.3 [97.3, 99.3] | 95.7 [93.7, 97.7] | 100.0 [98.7, 100.0]† | 96.7 [94.3, 98.7] |
| Qwen3.6-35B | validate_problem | numeric | 300 | 77.3 [73.0, 82.3] | 98.7 [97.7, 99.7] | 98.0 [96.0, 99.7] | 100.0 [98.7, 100.0]† | 98.0 [95.0, 100.0] |
| Qwen3.6-35B | validate_plan | classical | 1500 | 92.2 [87.5, 96.2] | 82.2 [67.0, 94.5] | 81.8 [66.7, 93.9] | 100.0 [99.7, 100.0]† | 99.8 [99.5, 100.0] |
| Qwen3.6-35B | validate_plan | numeric | 1500 | 89.6 [85.4, 93.5] | 83.6 [71.6, 93.5] | 82.5 [69.9, 93.1] | 99.8 [99.5, 100.0] | 98.7 [97.8, 99.6] |
| Qwen3.6-35B | simulate | classical | 150 | 0.0 [0.0, 2.5]†¶ | 72.7 [56.7, 86.7] | 72.7 [56.7, 86.7] | 100.0 [97.5, 100.0]† | 99.3 [98.0, 100.0] |
| Qwen3.6-35B | simulate | numeric | 150 | 0.0 [0.0, 2.5]†¶ | 80.0 [74.0, 86.7] | 76.7 [68.7, 84.7] | 100.0 [97.5, 100.0]† | 94.7 [88.0, 100.0] |

#### S1-D. Per domain (think=off, pooled over wordings)

Rows per domain and arm: solve 15, validate_domain 18, validate_problem 30, validate_plan 150, simulate 15. Too few for single-domain claims; read for pattern. Counts and Wilson intervals: `tools/reanalysis/out/breakdowns_cost/per_domain_sweep5v2-live.csv` (its delivered columns are the retired surface).

**Success %, unaided / tool-verified plain / tool-verified steered** (¶ and ISS-027: see the caveats above; the ISS-027 moves sit in the satellite and pogo_stick rows):

| domain | track | model | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| barman | cla | Qwen3.5-9B | 0 / 100 / 100 | 17 / 100 / 100 | 67 / 93 / 97 | 57 / 97 / 99 | 0¶ / 47 / 67 |
| barman | cla | Gemma-26B | 0 / 100 / 100 | 94 / 100 / 100 | 50 / 100 / 100 | 59 / 0 / 18 | 0¶ / 100 / 100 |
| barman | cla | Qwen3.6-35B | 0 / 33 / 67 | 83 / 100 / 100 | 67 / 97 / 97 | 82 / 95 / 100 | 0¶ / 100 / 100 |
| blocksworld | cla | Qwen3.5-9B | 13 / 100 / 100 | 17 / 100 / 100 | 77 / 100 / 100 | 97 / 100 / 100 | 0¶ / 73 / 100 |
| blocksworld | cla | Gemma-26B | 7 / 100 / 100 | 100 / 100 / 100 | 83 / 100 / 100 | 100 / 80 / 100 | 0¶ / 100 / 100 |
| blocksworld | cla | Qwen3.6-35B | 13 / 53 / 100 | 56 / 100 / 100 | 80 / 97 / 100 | 100 / 88 / 100 | 0¶ / 93 / 100 |
| depots | cla | Qwen3.5-9B | 7 / 100 / 100 | 17 / 100 / 100 | 73 / 100 / 100 | 65 / 100 / 100 | 0¶ / 80 / 100 |
| depots | cla | Gemma-26B | 7 / 100 / 100 | 89 / 100 / 100 | 60 / 100 / 100 | 91 / 0 / 100 | 0¶ / 100 / 100 |
| depots | cla | Qwen3.6-35B | 7 / 60 / 93 | 89 / 100 / 100 | 60 / 100 / 100 | 97 / 99 / 99 | 0¶ / 87 / 100 |
| gripper | cla | Qwen3.5-9B | 33 / 100 / 100 | 44 / 100 / 100 | 83 / 97 / 93 | 83 / 100 / 100 | 0¶ / 87 / 100 |
| gripper | cla | Gemma-26B | 33 / 100 / 100 | 83 / 100 / 100 | 87 / 100 / 100 | 95 / 67 / 98 | 0¶ / 100 / 100 |
| gripper | cla | Qwen3.6-35B | 7 / 53 / 100 | 72 / 100 / 100 | 83 / 90 / 90 | 99 / 95 / 99 | 0¶ / 80 / 100 |
| miconic | cla | Qwen3.5-9B | 20 / 100 / 100 | 44 / 100 / 100 | 87 / 90 / 90 | 93 / 100 / 100 | 0¶ / 73 / 100 |
| miconic | cla | Gemma-26B | 13 / 100 / 100 | 83 / 100 / 100 | 80 / 100 / 100 | 93 / 66 / 99 | 0¶ / 100 / 100 |
| miconic | cla | Qwen3.6-35B | 13 / 67 / 100 | 83 / 100 / 100 | 73 / 90 / 90 | 94 / 31 / 100 | 0¶ / 40 / 100 |
| parking | cla | Qwen3.5-9B | 7 / 100 / 100 | 67 / 100 / 100 | 73 / 100 / 100 | 81 / 99 / 100 | 0¶ / 73 / 100 |
| parking | cla | Gemma-26B | 0 / 100 / 100 | 83 / 100 / 100 | 97 / 100 / 100 | 89 / 3 / 100 | 0¶ / 100 / 100 |
| parking | cla | Qwen3.6-35B | 7 / 53 / 80 | 78 / 100 / 100 | 90 / 100 / 100 | 87 / 93 / 100 | 0¶ / 67 / 100 |
| rovers | cla | Qwen3.5-9B | 0 / 100 / 100 | 17 / 100 / 100 | 30 / 100 / 100 | 78 / 99 / 100 | 0¶ / 67 / 93 |
| rovers | cla | Gemma-26B | 0 / 100 / 100 | 100 / 100 / 100 | 60 / 97 / 100 | 91 / 0 / 72 | 0¶ / 93 / 100 |
| rovers | cla | Qwen3.6-35B | 0 / 47 / 73 | 100 / 89 / 100 | 50 / 97 / 97 | 94 / 82 / 100 | 0¶ / 100 / 93 |
| satellite | cla | Qwen3.5-9B | 7 / 100 / 100 | 100 / 100 / 100 | 73 / 90 / 80 | 96 / 87 / 93 | 0¶ / 47 / 73 |
| satellite | cla | Gemma-26B | 0 / 100 / 100 | 100 / 83 / 83 | 80 / 100 / 100 | 93 / 4 / 99 | 0¶ / 73 / 73 |
| satellite | cla | Qwen3.6-35B | 13 / 67 / 100 | 83 / 100 / 100 | 83 / 93 / 97 | 97 / 46 / 100 | 0¶ / 67 / 100 |
| tpp | cla | Qwen3.5-9B | 0 / 100 / 100 | 17 / 100 / 100 | 67 / 97 / 93 | 67 / 100 / 100 | 0¶ / 27 / 47 |
| tpp | cla | Gemma-26B | 7 / 93 / 100 | 83 / 100 / 100 | 70 / 100 / 100 | 77 / 9 / 100 | 0¶ / 93 / 100 |
| tpp | cla | Qwen3.6-35B | 0 / 47 / 87 | 94 / 100 / 100 | 70 / 97 / 100 | 78 / 99 / 100 | 0¶ / 73 / 100 |
| zenotravel | cla | Qwen3.5-9B | 7 / 100 / 100 | 17 / 100 / 100 | 63 / 90 / 90 | 87 / 100 / 100 | 0¶ / 73 / 100 |
| zenotravel | cla | Gemma-26B | 0 / 100 / 100 | 83 / 100 / 100 | 70 / 100 / 100 | 92 / 14 / 98 | 0¶ / 100 / 87 |
| zenotravel | cla | Qwen3.6-35B | 7 / 80 / 100 | 83 / 100 / 100 | 83 / 97 / 97 | 94 / 91 / 100 | 0¶ / 20 / 100 |
| block-grouping | num | Qwen3.5-9B | 27 / 100 / 100 | 17 / 100 / 100 | 43 / 90 / 90 | 81 / 81 / 87 | 0¶ / 67 / 67 |
| block-grouping | num | Gemma-26B | 27 / 100 / 100 | 17 / 100 / 100 | 70 / 100 / 100 | 85 / 0 / 100 | 0¶ / 100 / 100 |
| block-grouping | num | Qwen3.6-35B | 20 / 93 / 100 | 17 / 100 / 100 | 70 / 100 / 100 | 87 / 66 / 97 | 0¶ / 73 / 100 |
| counters | num | Qwen3.5-9B | 0 / 100 / 100 | 17 / 100 / 100 | 37 / 100 / 100 | 65 / 63 / 65 | 0¶ / 13 / 20 |
| counters | num | Gemma-26B | 20 / 100 / 100 | 100 / 100 / 100 | 83 / 100 / 100 | 80 / 63 / 95 | 0¶ / 73 / 53 |
| counters | num | Qwen3.6-35B | 13 / 100 / 100 | 72 / 100 / 100 | 70 / 100 / 100 | 76 / 61 / 96 | 0¶ / 53 / 73 |
| delivery | num | Qwen3.5-9B | 13 / 100 / 100 | 11 / 100 / 100 | 60 / 90 / 90 | 92 / 100 / 100 | 0¶ / 80 / 100 |
| delivery | num | Gemma-26B | 7 / 93 / 93 | 61 / 83 / 89 | 73 / 100 / 100 | 85 / 0 / 99 | 0¶ / 100 / 100 |
| delivery | num | Qwen3.6-35B | 7 / 73 / 100 | 78 / 89 / 94 | 70 / 97 / 90 | 95 / 100 / 100 | 0¶ / 100 / 100 |
| depot | num | Qwen3.5-9B | 0 / 100 / 100 | 17 / 100 / 100 | 67 / 100 / 100 | 53 / 97 / 100 | 0¶ / 67 / 93 |
| depot | num | Gemma-26B | 7 / 100 / 100 | 100 / 100 / 100 | 47 / 100 / 100 | 79 / 0 / 82 | 0¶ / 100 / 100 |
| depot | num | Qwen3.6-35B | 0 / 27 / 73 | 100 / 100 / 100 | 80 / 90 / 90 | 83 / 93 / 100 | 0¶ / 80 / 100 |
| drone | num | Qwen3.5-9B | 20 / 87 / 100 | 17 / 100 / 100 | 67 / 100 / 100 | 73 / 90 / 89 | 0¶ / 53 / 60 |
| drone | num | Gemma-26B | 7 / 100 / 100 | 33 / 100 / 100 | 83 / 100 / 100 | 95 / 11 / 98 | 0¶ / 73 / 53 |
| drone | num | Qwen3.6-35B | 7 / 80 / 80 | 28 / 100 / 100 | 93 / 97 / 100 | 93 / 99 / 100 | 0¶ / 93 / 100 |
| farmland | num | Qwen3.5-9B | 0 / 100 / 100 | 11 / 100 / 100 | 77 / 100 / 100 | 95 / 91 / 100 | 0¶ / 93 / 100 |
| farmland | num | Gemma-26B | 7 / 100 / 100 | 100 / 100 / 100 | 90 / 100 / 100 | 99 / 70 / 100 | 0¶ / 100 / 100 |
| farmland | num | Qwen3.6-35B | 7 / 87 / 100 | 17 / 100 / 100 | 87 / 100 / 100 | 99 / 98 / 100 | 0¶ / 73 / 100 |
| gardening | num | Qwen3.5-9B | 27 / 100 / 100 | 17 / 100 / 100 | 57 / 90 / 43 | 67 / 100 / 99 | 0¶ / 67 / 80 |
| gardening | num | Gemma-26B | 7 / 100 / 100 | 39 / 89 / 94 | 77 / 100 / 100 | 86 / 4 / 100 | 0¶ / 80 / 87 |
| gardening | num | Qwen3.6-35B | 27 / 80 / 100 | 44 / 100 / 100 | 77 / 100 / 100 | 88 / 89 / 100 | 0¶ / 67 / 93 |
| pogo_stick | num | Qwen3.5-9B | 13 / 100 / 100 | 17 / 100 / 100 | 73 / 97 / 63 | 95 / 68 / 100 | 0¶ / 67 / 80 |
| pogo_stick | num | Gemma-26B | 0 / 100 / 80 | 83 / 100 / 100 | 90 / 97 / 100 | 86 / 0 / 100 | 0¶ / 60 / 60 |
| pogo_stick | num | Qwen3.6-35B | 13 / 53 / 87 | 67 / 100 / 100 | 80 / 100 / 100 | 98 / 86 / 98 | 0¶ / 73 / 80 |
| sailing | num | Qwen3.5-9B | 7 / 100 / 100 | 17 / 100 / 100 | 67 / 90 / 80 | 81 / 90 / 90 | 0¶ / 80 / 80 |
| sailing | num | Gemma-26B | 0 / 100 / 100 | 94 / 94 / 100 | 87 / 100 / 100 | 86 / 9 / 97 | 0¶ / 93 / 100 |
| sailing | num | Qwen3.6-35B | 13 / 67 / 100 | 72 / 100 / 100 | 73 / 100 / 100 | 87 / 41 / 97 | 0¶ / 67 / 100 |
| zenotravel-numeric | num | Qwen3.5-9B | 13 / 100 / 100 | 17 / 100 / 100 | 73 / 90 / 93 | 88 / 100 / 100 | 0¶ / 67 / 100 |
| zenotravel-numeric | num | Gemma-26B | 7 / 100 / 100 | 28 / 100 / 100 | 60 / 100 / 100 | 94 / 13 / 96 | 0¶ / 93 / 100 |
| zenotravel-numeric | num | Qwen3.6-35B | 13 / 40 / 100 | 39 / 100 / 100 | 73 / 97 / 100 | 90 / 93 / 99 | 0¶ / 87 / 100 |

**Calling %, plain / steered** (35B cells: see the caveats above):

| domain | track | model | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| barman | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 87 / 100 |
| barman | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 0 / 18 | 100 / 100 |
| barman | cla | Qwen3.6-35B | 40 / 67 | 100 / 100 | 100 / 100 | 95 / 100 | 100 / 100 |
| blocksworld | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 73 / 100 |
| blocksworld | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 80 / 100 | 100 / 100 |
| blocksworld | cla | Qwen3.6-35B | 53 / 100 | 100 / 100 | 97 / 100 | 88 / 100 | 93 / 100 |
| depots | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 80 / 100 |
| depots | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 0 / 100 | 100 / 100 |
| depots | cla | Qwen3.6-35B | 60 / 93 | 100 / 100 | 100 / 100 | 100 / 100 | 87 / 100 |
| gripper | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 87 / 100 |
| gripper | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 67 / 100 | 100 / 100 |
| gripper | cla | Qwen3.6-35B | 53 / 100 | 100 / 100 | 100 / 100 | 97 / 100 | 80 / 100 |
| miconic | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 73 / 100 |
| miconic | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 66 / 100 | 100 / 100 |
| miconic | cla | Qwen3.6-35B | 67 / 100 | 100 / 100 | 97 / 100 | 31 / 100 | 40 / 100 |
| parking | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 87 / 100 |
| parking | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 3 / 100 | 100 / 100 |
| parking | cla | Qwen3.6-35B | 53 / 80 | 100 / 100 | 100 / 100 | 93 / 100 | 67 / 100 |
| rovers | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 99 / 100 | 67 / 93 |
| rovers | cla | Gemma-26B | 100 / 100 | 100 / 100 | 97 / 100 | 0 / 72 | 93 / 100 |
| rovers | cla | Qwen3.6-35B | 53 / 80 | 100 / 100 | 97 / 100 | 82 / 100 | 100 / 100 |
| satellite | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 67 / 100 |
| satellite | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 4 / 100 | 100 / 100 |
| satellite | cla | Qwen3.6-35B | 67 / 100 | 100 / 100 | 100 / 100 | 46 / 100 | 67 / 100 |
| tpp | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 80 / 100 |
| tpp | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 9 / 100 | 100 / 100 |
| tpp | cla | Qwen3.6-35B | 47 / 93 | 100 / 100 | 97 / 100 | 99 / 100 | 73 / 100 |
| zenotravel | cla | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 73 / 100 |
| zenotravel | cla | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 15 / 100 | 100 / 100 |
| zenotravel | cla | Qwen3.6-35B | 80 / 100 | 100 / 100 | 97 / 100 | 91 / 100 | 20 / 100 |
| block-grouping | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 87 / 100 |
| block-grouping | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 0 / 100 | 100 / 100 |
| block-grouping | num | Qwen3.6-35B | 93 / 100 | 100 / 100 | 100 / 100 | 71 / 100 | 73 / 100 |
| counters | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 87 / 100 |
| counters | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 63 / 100 | 100 / 100 |
| counters | num | Qwen3.6-35B | 100 / 100 | 100 / 100 | 100 / 100 | 63 / 100 | 73 / 100 |
| delivery | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 80 / 100 |
| delivery | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 0 / 100 | 100 / 100 |
| delivery | num | Qwen3.6-35B | 87 / 100 | 100 / 100 | 97 / 100 | 100 / 100 | 100 / 100 |
| depot | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 73 / 100 |
| depot | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 0 / 82 | 100 / 100 |
| depot | num | Qwen3.6-35B | 33 / 87 | 100 / 100 | 97 / 100 | 93 / 100 | 80 / 100 |
| drone | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 93 / 100 |
| drone | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 11 / 100 | 100 / 100 |
| drone | num | Qwen3.6-35B | 93 / 80 | 100 / 100 | 97 / 100 | 99 / 100 | 93 / 100 |
| farmland | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 91 / 100 | 93 / 100 |
| farmland | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 70 / 100 | 100 / 100 |
| farmland | num | Qwen3.6-35B | 87 / 100 | 100 / 100 | 100 / 100 | 98 / 100 | 73 / 100 |
| gardening | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 67 / 100 |
| gardening | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 4 / 100 | 100 / 100 |
| gardening | num | Qwen3.6-35B | 80 / 100 | 100 / 100 | 100 / 100 | 90 / 100 | 67 / 100 |
| pogo_stick | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 68 / 100 | 87 / 100 |
| pogo_stick | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 0 / 100 | 100 / 100 |
| pogo_stick | num | Qwen3.6-35B | 80 / 93 | 100 / 100 | 100 / 100 | 87 / 100 | 87 / 100 |
| sailing | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 93 / 100 |
| sailing | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 9 / 100 | 100 / 100 |
| sailing | num | Qwen3.6-35B | 67 / 100 | 100 / 100 | 100 / 100 | 43 / 99 | 67 / 100 |
| zenotravel-numeric | num | Qwen3.5-9B | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 67 / 100 |
| zenotravel-numeric | num | Gemma-26B | 100 / 100 | 100 / 100 | 100 / 100 | 13 / 100 | 100 / 100 |
| zenotravel-numeric | num | Qwen3.6-35B | 67 / 100 | 100 / 100 | 97 / 100 | 93 / 99 | 87 / 100 |
<!-- END GENERATED: s1_breakdowns_md.py -->

## VAL cross-check of the answer key (C1; added 2026-10-27; in no tex yet)

Plan step C1 (settles C8, D1). Method, every disagreement and the items VAL cannot read:
`reference/val_crosscheck.md`; script `tools/val_crosscheck.py`; outputs in the gitignored
`results/val-crosscheck/`. KCL VAL "Version 4" (the LLMs-Planning macOS build, sha256
`44a07d6d…`, the binary of the PlanBench spot checks). pyval re-run locally reproduced every
stored verdict first, so VAL is compared with the answer key as stored.

| figure | value | source | do NOT quote |
|---|---|---|---|
| plans, VAL vs the answer key | **1,731 / 1,732 agree (99.94%, Wilson 95% [99.67, 99.99])**: all 1,000 validate_plan fixture plans; 731 / 732 distinct solve plans graded in the delivered rerun (classical 877/878, numeric 854/854). 10 more plans crash VAL (wrong argument count; pyval rejects all 10) and are not counted | `val_crosscheck.md` | "100% agreement"; any figure pooling plans with files |
| the one disagreement | pyval accepts `pick-up` for the action `pick_up` (it retries `-` as `_`); one Part C no-tools trial (Qwen3.5-9B, blocksworld p02, wording 11). Post hoc, outside the frozen readout: Part C Qwen3.5-9B unaided solve would be 72 / 300 delivered, not 73 / 300 | `val_crosscheck.md` | a corrected figure in place of the frozen readout's |
| domain and problem files, parse check | 184 / 238 (77.3% [71.6, 82.2]). Every miss is VAL being more lenient than PDDL: it accepts a stray `)` after the define, and treats a missing `:goal` as empty. VAL accepts all 120 valid files and rejects all 64 invalid files whose error is inside the define | `val_crosscheck.md` | "validate_domain / validate_problem labels checked by VAL" |

### Added 2026-11-09: VAL on the Claude solve plans (in no tex yet)

Provenance: `tools/reanalysis/val_frontier_solve.py` (imports the C1 functions of `tools/val_crosscheck.py`),
output `tools/reanalysis/out/val_frontier_solve.md` (every disagreement listed), item and row CSVs in the
gitignored `results/val-crosscheck-frontier/`. Same VAL binary (sha256 `44a07d6d…`, under Rosetta) and the
same `validate -v` call as C1. Plans: every plan a solve grader validated in the seven Claude cells with
solve rows (Sonnet 4.6 unaided canonical and renamed, tool arm canonical; Haiku 4.5 unaided and tool arm,
canonical and renamed), checked against `domains/` or `domains-anon/` as the overlay does. Harness verdict
= live pyval through the plugin; it reproduced the stored `success` of every row it could rebuild and the
overlay verdict of every delivered tool-arm plan. Unaided answers stored at the 16,384-character cap
(all graded failures, counted in the output's row table) cannot be rebuilt and are left out.

<!-- gen:val_frontier_solve -->
| figure | value | source | do NOT quote |
|---|---|---|---|
| Claude solve plans, VAL vs the harness verdict (pyval) | **734 / 745 agree (98.52%, Wilson 95% [97.38, 99.17])** over the 771 distinct graded plans of Sonnet 4.6 and Haiku 4.5 (unaided and tool arm, canonical and renamed). Tool arm **219 / 219**; unaided 541 / 552. 16 of the agreeing plans (18 of all plans with a verdict from both) were bare `name arg` lines that VAL reads only once brackets are added. Not counted: 21 answers with no plan in them (prose; pyval returns an error shape, graded a failure) and 5 plans that crash VAL (each has a step with the wrong number of arguments, read by hand: gripper `drop` with 3 of 4, barman `empty_shot` with 2 of 3; pyval rejects all of them) | `val_frontier_solve.py`; `out/val_frontier_solve.md` | "100% agreement"; a figure that pools these with the C1 open-model plans |
| the disagreements | **all 11 are one pyval fault**: the fixture declares upper-case names (satellite `Star0`, `GroundStation1`; pogo_stick `CRAFT_PLANK`), the model writes them exactly as declared, and pyval rejects the plan as `STRUCTURE_ERROR` ("not declared"). The same plan in lower case is VALID under pyval, and VAL accepts it as written (PDDL names are case-insensitive). Unaided, canonical corpus only: the renamed tree has no upper-case names, and the planner's plans are lower case. Other disagreements: 0 | `val_frontier_solve.md` | the C1 hyphen case as the only grader fault (that one was lenient; this one is strict) |
| unaided solve trials whose grade changes under VAL | stored fail → VAL success: **Sonnet 4.6 12 of 300, Haiku 4.5 3 of 100**, canonical; renamed 0; success → fail: 0. Post hoc, Sonnet unaided solve canonical becomes 32.7% (stored 28.7%) | `val_rows.csv` | a corrected figure in place of the frozen ones |
| effect on the frontier contamination test, unaided solve (renamed − canonical, T7 method, post hoc) | Sonnet 4.6: stored 28.7 → 28.3, -0.33 [-10.59, +9.93], criterion not met (unresolved); VAL grade 32.7 → 28.3, -4.33 [-14.38, +5.71], criterion not met (unresolved). Haiku 4.5 (v11 only): stored 22.0 → 19.0, -3.00 [-12.14, +6.14], criterion not met (unresolved); VAL grade 25.0 → 19.0, -6.00 [-17.25, +5.25], criterion not met (unresolved). The case fault lowers only the canonical side, so it biases the contrast toward zero | `val_frontier_solve.md` | the VAL-graded Δ as a replacement for the frozen −0.33 row (the grader change is post hoc) |
<!-- /gen:val_frontier_solve -->

### Added 2026-11-09: ISS-027 post hoc corrections, open models (in no tex yet)

Provenance: `tools/reanalysis/iss027_replay.py` (the stored simulate and validate_plan tool calls replayed with the plan lower-cased) and `tools/reanalysis/iss027_unaided.py` (unaided solve re-graded with the plan lower-cased), both read-only over the canonical corpora (`sweep5v2-live`, `sweep6-live`, `delivered-rerun`, and `iss024d-e2e-live` for the mechanism row of the 2026-10-03 block). The fault is ISS-027 (`OPEN_ISSUES.md`): pyval 0.1.5 rejects a plan that writes a fixture name with the fixture's own capitals. The frozen figures stay where they are; the post hoc values below sit beside them, and a short generated caveat follows each table that holds a moved figure (T1, T2, T5, T8a, the Study 1 summary and the 2026-10-03 block).

<!-- gen:iss027 -->
*Generated by `tools/reanalysis/iss027_replay.py` and `iss027_unaided.py` (outputs `tools/reanalysis/out/iss027_*.{json,md}`); do not edit between the markers, rerun the scripts. pddl-pyvalidator 0.1.5 (the frozen grader; 0.1.6 folds case), sibling `../pddl-copilot` at `e428f17fd0`. Self-check: 665 of 666 replayed tool calls return the stored result (1 known wording difference in the free-text report, same verdict, listed in `iss027_replay.md`); the harness rule on the as-is replay equals the stored `success` on all 179 replayed rows; the unaided re-grade equals the stored `success` on all 3,236 rows not cut at the snapshot cap.*

| figure | frozen → post hoc (names case-folded) | source | do NOT quote |
|---|---|---|---|
| Study 1, think=off, headline (T1, T2, T5) | Qwen3.5-9B simulate tool-verified plain 65.0 → 65.3 (+1); Qwen3.5-9B solve unaided 10.7 → 11.3 (+2); Gemma-26B simulate tool-verified plain 91.7 → 95.0 (+10); Gemma-26B simulate tool-verified steered 90.7 → 94.0 (+10); Gemma-26B validate_plan tool-verified steered 92.6 → 92.6 (+1) | `iss027_replay.md`, `iss027_unaided.md` | a post hoc value in place of the frozen one; the frozen value without this caveat |
| Study 1, think=on (main sweep) | Qwen3.5-4B simulate tool-verified plain 63.7 → 64.3 (+2); Qwen3.5-4B simulate tool-verified steered 74.7 → 75.0 (+1); Qwen3.5-4B validate_plan tool-verified steered 73.1 → 73.1 (+1); Qwen3.5-9B solve unaided 27.0 → 27.3–28.7 (+1 to +5); Gemma-26B simulate tool-verified plain 44.0 → 46.0 (+6); Gemma-26B simulate tool-verified steered 91.0 → 91.7 (+2); Qwen3.6-35B solve unaided 38.3 → 40.3–40.7 (+6 to +7) | same | same |
| Study 1, think=off, Qwen3.5-0.8B and 4B | Qwen3.5-4B validate_plan tool-verified steered 79.5 → 79.6 (+2) | same | same |
| contamination twin (`sweep6-live`, renamed tree, no capitals declared) | off: none; on: none | same | — |
| delivered rerun, tool-verified (T8a inputs) | Gemma-26B simulate tool-verified plain 90.7 → 93.7 (+9); Gemma-26B simulate tool-verified steered 90.7 → 93.7 (+9); Qwen3.6-35B simulate tool-verified plain 94.0 → 94.7 (+2); Qwen3.6-35B simulate tool-verified steered 95.7 → 96.3 (+2) | `iss027_replay.md` | same |
| delivered rerun, solve graded from the answer (Part C online and delivered, tool-arm delivered E1/E2) | **0 flips**; Part C has 81 rows on the affected fixtures and none of their plans keeps a capital | `iss027_unaided.md` | — |
| rerun simulate mechanism layer (`iss024d-e2e-live`, think on) | Qwen3.5-4B simulate tool-verified steered 73.3 → 73.7 (+1); Gemma-26B simulate tool-verified plain 44.0 → 45.3 (+4); Gemma-26B simulate tool-verified steered 92.0 → 93.0 (+3) | `iss027_replay.md` | same |

Ranges ("+a to +b") come from unaided answers stored cut at the 500-character snapshot: the low end re-grades what is stored; the high end adds the cut answers whose stored reason is `plan_invalid` and whose visible JSON writes a capitalised fixture name. A replay changes only the tool's answer, so it corrects the tool-verified grade only; the delivered grade of the tool arms stays as stored. Every flip is on satellite p02–p05 or pogo_stick. Not recomputed here: intervals, p-values and equivalence verdicts (point estimates only).
<!-- /gen:iss027 -->

## D5b ground truth: Fast Downward on the IPC 2023 size ladder (added 2026-11-09; in no tex yet; no model runs)

Plan row D5b, handoff 2026-11-09 item 9. Planner figures only: no model has seen these
problems. Source `github.com/ipc2023-learning/benchmarks` at `19d6a8ad4b35…` (no licence
file, so only the commit, the generator spec, the seeds and a sha256 manifest are committed:
`tools/d5b/manifest.json`). 120 fresh problems: blocksworld, miconic, rovers, satellite (IPC's
own domain files), three tiers that copy IPC's testing tiers easy, medium and hard, 10 per
tier, seeds 5001-5010 / 5101-5110 / 5201-5210. Fast Downward through unified-planning 1.3.0
and up-fast-downward 0.5.2 with the pddl-solver plugin's three strategies; wall-clock limits
120 s and 1800 s, 8 GiB per run, up to 12 runs at once on the laptop (14 cores, 24 GiB). The
1800 s pass runs only the pairs unsolved at 120 s (deterministic search). Solved = a plan KCL
VAL accepts (the C1 build, sha256 `44a07d6d…`). Method and regeneration: `tools/d5b/README.md`;
runs in the gitignored `external/d5b-work/runs/`; rows printed by `python -m tools.d5b.shares
--write` (full tables in `tools/reanalysis/out/d5b_shares.md`).

<!-- gen:d5b_shares -->
| figure | value | source | do NOT quote |
|---|---|---|---|
| D5b corpus, syntax check | 124 / 124 files valid (4 IPC 2023 domain files + 120 generated problems; pddl-pyvalidator 0.1.6 and KCL VAL both) | `validate.jsonl` | - |
| Fast Downward solved within 120 s, plugin default `lazy_greedy_cea` (120 problems, plan VAL-valid) | **easy 40/40 (100%), medium 31/40 (78%), hard 15/40 (38%). Per domain: blocksworld: easy 10/10, medium 6/10, hard 0/10; miconic: easy 10/10, medium 10/10, hard 4/10; rovers: easy 10/10, medium 5/10, hard 1/10; satellite: easy 10/10, medium 10/10, hard 10/10** | `tools/d5b/shares.py` | a share with a pending range as one number; these shares as a model result (no model has run on these problems); the cut-off as exact (wall clock, 12 runs at once on a laptop, so a run near the limit can fall either side) |
| Fast Downward solved within 120 s, any of the three strategies (120 problems, plan VAL-valid) | **easy 40/40 (100%), medium 34/40 (85%), hard 21/40 (52%). Per domain: blocksworld: easy 10/10, medium 6/10, hard 0/10; miconic: easy 10/10, medium 10/10, hard 10/10; rovers: easy 10/10, medium 8/10, hard 1/10; satellite: easy 10/10, medium 10/10, hard 10/10** | `tools/d5b/shares.py` | a share with a pending range as one number; these shares as a model result (no model has run on these problems); the cut-off as exact (wall clock, 12 runs at once on a laptop, so a run near the limit can fall either side) |
| Fast Downward solved within 1800 s, plugin default `lazy_greedy_cea` (120 problems, plan VAL-valid) | **easy 40/40 (100%), medium 38/40 (95%), hard 16-33/40 (40-82%, 17 pending). Per domain: blocksworld: easy 10/10, medium 9/10, hard 0-5/10; miconic: easy 10/10, medium 10/10, hard 4-10/10; rovers: easy 10/10, medium 9/10, hard 2-8/10; satellite: easy 10/10, medium 10/10, hard 10/10** | `tools/d5b/shares.py` | a share with a pending range as one number; these shares as a model result (no model has run on these problems); the cut-off as exact (wall clock, 12 runs at once on a laptop, so a run near the limit can fall either side) |
| Fast Downward solved within 1800 s, any of the three strategies (120 problems, plan VAL-valid) | **easy 40/40 (100%), medium 39/40 (98%), hard 22-33/40 (55-82%, 11 pending). Per domain: blocksworld: easy 10/10, medium 9/10, hard 0-5/10; miconic: easy 10/10, medium 10/10, hard 10/10; rovers: easy 10/10, medium 10/10, hard 2-8/10; satellite: easy 10/10, medium 10/10, hard 10/10** | `tools/d5b/shares.py` | a share with a pending range as one number; these shares as a model result (no model has run on these problems); the cut-off as exact (wall clock, 12 runs at once on a laptop, so a run near the limit can fall either side) |
| plans found, rejected by KCL VAL | 0 of 225 | `tools/d5b/shares.py` | - |
| pddl-pyvalidator 0.1.6 (the harness grader) vs KCL VAL on the planner's plans | agrees on 208 of 208 plans checked by both (17 not checked by pyval yet); slowest pyval check 1286 s for a 537-step plan | `tools/d5b/shares.py` | - |
<!-- /gen:d5b_shares -->

## Delivered rerun — readout (FROZEN 2026-10-09; in no tex yet)

Provenance: `reference/delivered_rerun_readout.md` / `.json` (frozen code `d558946`, package `822aace…`; summary and sha256s in `reference/delivered_rerun_prereg.md` §8c). Data: `results/delivered-rerun/` (seven cells, cluster run tag `delivered-rerun` / `delivered-rerun-neutral`). **Parity failed at job level, so every figure below is a separate-apparatus replication**: it never replaces a canonical-cell figure and is never pooled with one.

| figure | **quote this** | do NOT quote |
|---|---|---|
| parity guard (§3) | Gemma **10/10** met; Qwen **15/20** met (needs 18); \|Δ̂\| > 10 in 35B solve-plain **+19.3** and 35B simulate-plain **+19.3** → **parity fails at job level** | "the rerun reproduces the canonical cells"; any rerun rate as the exact delivered rate of a canonical cell |
| Part C parity | **11/12** met; 35B validate_domain **+8.6** [2.8, 14.7] unresolved | — |
| R1, Gemma validate_plan delivered, tools-plain − unaided (E2) | **+0.9** [−1.2, 2.9] (89.2 vs 88.3) → **No delivered harm** | "−67 pp" as a delivered effect (it is tool-verified only) |
| R2, Gemma validate_plan steered − plain (E3) | **+7.5** [4.9, 10.2], Holm p 0.00057 → **Unresolved** (lower bound not above +5) | "steering raises delivered answers" as a registered finding |
| R3, title rule | **Title changes to the two-gate reading (invocation and delivery)** | "invocation is the bottleneck" as the title |
| R4, solve, full uncut answers delivered correctly | Gemma **97.7%** of 576 · 9B **95.0%** of 561 · 35B **95.2%** of 498 → gap attributed to storage and the refused final request | — |
| R5, neutral system prompt, invocation | neutral-plain **26.9** vs minimal-plain **20.0** (+6.9, 90% CI [3.6, 10.7]) → **The directive suppresses calling**; steered 98.1 vs 93.1 → steering sentence "Not shown" | — |
| E2 solve delivered, tools-plain − unaided | **+71.0 / +64.3 / +51.7** (Gemma / 9B / 35B) | the canonical tool-verified "+66 to +73" as delivered |
| E2 simulate, Gemma | **−15.7** [−24.7, −6.7], Holm p 0.018 (tools worse; 8.3 vs 24.0) | — |
| E1 simulate delivered, tool arms | Gemma **8.3** both arms · 9B **17.3 / 16.3** · 35B **28.3 / 25.7** (plain / steered); no-room share **42.7–53.0%** | the 2026-10-03 "at most 21%" row above (`iss024d` apparatus), as a figure of this run |

### Added 2026-11-09: post hoc splits beside the frozen readout (ISS-028, ISS-029; in no tex yet)

The frozen rows above stay the record. These lines are post hoc and descriptive; never quote one in place of a frozen figure.

<!-- gen:iss028 -->
*Generated by `tools/reanalysis/iss028_goal_trailers.py` (output `tools/reanalysis/out/iss028_goal_trailers.{json,md}`); do not edit between the markers, rerun the script. Self-check: the frozen grader reproduces the readout's solve figures (E1, Part C, E2, E3, E4, R4: 24 of 24 equal), and the three classes sum to the frozen total.*

**ISS-028, post hoc (goal facts after a correct plan; the frozen values above stay).** Of the **38** solve rows the frozen E4 labels WRONG_FACTS: **17** repeat the tool's plan exactly and then list goal facts (Qwen3.5-9B 15, Qwen3.6-35B 2); **5** are copying errors (the tool plan's length, some actions changed; Qwen3.5-9B 3, Gemma-26B 1, Qwen3.6-35B 1); **16** are other shapes (extra lines, then tool plan 5; other 10; tool plan, then extra lines 1). With the trailing goal facts dropped and the plan validated again (post hoc extractor rule, every solve row graded `plan_invalid`), delivered solve moves in these cells: Qwen3.5-9B solve plain 266/300 (88.7%) → 275/300 (91.7%); Qwen3.5-9B solve steered 267/300 (89.0%) → 273/300 (91.0%); Qwen3.6-35B solve steered 262/300 (87.3%) → 264/300 (88.0%); Qwen3.6-35B solve unaided (Part C) 76/300 (25.3%) → 78/300 (26.0%). No other rerun solve cell moves (14 more rows lose a goal trailer but stay invalid). Figures built on these cells, point estimates only (intervals, p-values and readings not recomputed): E2 solve (tools plain − unaided) Qwen3.5-9B +64.3 → +67.3; E2 solve (tools plain − unaided) Qwen3.6-35B +51.7 → +51.0; E3 solve (steered − plain) Qwen3.5-9B +0.3 → -0.7; E3 solve (steered − plain) Qwen3.6-35B +10.3 → +11.0; R4 (tool-verified, full answer, delivered) Qwen3.5-9B 95.0% of 561 → 97.7%; R4 (tool-verified, full answer, delivered) Qwen3.6-35B 95.2% of 498 → 96.0%. Do NOT quote a post hoc value in place of the frozen E1 / E2 / E3 / E4 / R4 figure, or "transcription errors" for all 38 rows. Frontier Haiku 4.5 with tools: the overlay grades 3 of 100 solve rows `plan_invalid` (counters p05, depot p02, parking p05); these are the "three transcription errors" of the paper's delivery-gap paragraph, so depot p02 **is one of them**. By the rule above (raw trials read): counters p05 other (1 plan lines extracted, tool plan 56 actions); depot p02 goal_trailer (7 plan lines extracted, tool plan 5 actions, trailing goal facts dropped: valid); parking p05 other (11 plan lines extracted, tool plan 121 actions); 0 of 3 are copying errors by this rule, 2 write fewer lines than the tool plan has actions.
<!-- /gen:iss028 -->

<!-- gen:iss029 -->
*Generated by `tools/reanalysis/iss029_simulate_plan.py` (output `tools/reanalysis/out/iss029_simulate_plan.{json,md}`); do not edit between the markers, rerun the script. Self-check: the ground-truth cache matches the pinned hash; the frozen grader reproduces the readout's simulate E1, Part C and E4 rows (15 cells); every Part C row the online grade passes and the delivered grade fails is on a listed problem and simulates the run's plan.*

**ISS-029, post hoc (simulate prompt plan vs cached plan; the frozen values above stay).** For **6 of 100** simulate problems the plan the run's with-tools rows passed to the tool (so the plan in the prompt) is not the cached plan the delivered grader uses: barman p01 (30 vs 28 actions), barman p02 (14 vs 14 actions), barman p03 (30 vs 34 actions), barman p04 (61 vs 59 actions), barman p05 (61 vs 65 actions), gripper p03 (11 vs 11 actions). Of the 900 Part C simulate rows, **1** pass the online grade and fail the delivered grade: `qwen3_6_35b|simulate|plain|gripper|p03||v11`. Graded against the run plan's trajectory: Qwen3.6-35B simulate unaided (Part C) 53/300 (17.7%) → 54/300 (18.0%). With-tools rows on these problems that pass online, had room and fail delivered: 0. Do NOT quote the post hoc count in place of the frozen E2 simulate figure.
<!-- /gen:iss029 -->

## Delivered rerun — descriptive secondary analyses (prereg §6, §8b 13; 2026-10-09; in no tex yet)

Provenance: `reference/delivered_rerun_secondary/secondary.md` / `.json`, from `tools/delivered_rerun_secondary.py` on the frozen package (`822aace…`; its grades reproduce the readout's E1 and E4 counts exactly). Hand reads and rules: `reference/delivered_rerun_secondary/hand_reads/`. **Descriptive, not registered readings**; same separate-apparatus caveat as the block above.

| figure | **quote this** | do NOT quote |
|---|---|---|
| Gemma validate_plan, no-call answers (minimal-plain) | **2,400** no-call; **2,377** end in a parsed verdict (the other 23 hit the output cap); delivered right **2,078 = 86.6%** [85.2, 87.9]; unaided (Part C) on the same 2,400 fixtures **2,098**; tool-call-like text **0**, names the tool **0** | "not calling loses the answer"; the canonical "cannot be determined" (now determined) |
| same, hand read (60, seeded) | **59/60** end in a verdict, **54/60** right; both readers agree on every field; reader = grader's parsed verdict **60/60** | — |
| Gemma validate_plan invocation by wording, plain arm | v11 **31.0** · v12 **25.1** · v13 **3.9**; Part B neutral **44.2 / 29.7 / 6.7** | one invocation rate as if wording did not matter |
| E4 hand read | **290** rows, two independent readers + third reading; category agreement **259/290 (89.3%)**, "right" agreement **282/290 (97.2%)**; **218** WRONG_WRAPPER, **180** right to a human reader | the readout's NEEDS_READING counts as unexplained |
| simulate gap that is form only | **154 of 1,266** simulate gap rows (12%) are right to a human reader (**148** full trajectories in a form the grader does not read, 6 change lists or answers missing constants); the largest share stays REFUSED_OR_CLIPPED_FINAL (**843**) | "the simulate gap is a formatting artefact" |
| 35B validate_plan gap | **25 of 32** gap rows are a bare "VALID" (right; the grader needs `VERDICT:`) | — |
| cost-of-pass multiplier, tools ÷ unaided, delivered, pooled solve | plain **1.48** [0.89, 2.27] at 1:1, **0.58** [0.35, 0.90] at 5:1; steered **1.32** [0.80, 2.06] / **0.51** [0.31, 0.80] | "tools are cheaper" without the price ratio. Validation tasks and simulate: interval above 1 at 1:1 everywhere except 9B validate_domain (1.08 [0.71, 1.68]); at 5:1 only 9B validate_domain is below 1 (0.38 [0.25, 0.62]), and 9B simulate, 35B simulate and pooled validate_domain include 1 |

### Study 2 part 1 tables (plan step C3b; added 2026-11-09; in no tex yet)

Generated by `tools/reanalysis/s2_gen_md.py` (rerun: `python3 tools/reanalysis/s2_gen_md.py --results <abs path to results>`; plan step D4 reruns it unchanged, every cell list is read from the data); `.tex` fragments in `tools/reanalysis/out/tex/s2_*.tex`. Same caveats as the two blocks above: descriptive, separate apparatus. The rows above stay the quoted values; the tables below give their full breakdown.

<!-- BEGIN GENERATED: s2_gen_md.py (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/s2_gen_md.py`; do not edit between the markers, rerun the script. Inputs: `reference/delivered_rerun_secondary/secondary.json` (per wording, per track, per domain, hand reads), `reference/delivered_rerun_readout.json` (E1, E4), and the trial rows of `results/delivered-rerun/` through the frozen loader (package `822aace…`, tokens only). Self-check: 325 of 325 checks pass (counts sum to the readout's E1 in all cells; the all-domain cost rows equal `secondary.json` to 1e-9; 15 figures already in this file are reproduced).*

**Apparatus: Study 2 part 1 only** (the delivered rerun: full answer storage, the final-request retry, the leaked-prefix strip, vLLM 0.20.2, the delivered grader of the frozen package). Separate-apparatus replication: never pooled with a Study 1 table, and no figure here is the exact delivered rate of a canonical cell. *Delivered* = the frozen grader's verdict on the final answer. *Invocation* = any tool call (the readout's measure; Study 1 *calling* counts only the task's own tool, and the two differ in three cells, T8a note). Intervals: domain-cluster percentile bootstrap 95% from the frozen `stats.cluster_bootstrap` (k = the domains in the subset); † = Wilson 95% where the rate is exactly 0 or 100%.

#### S2-Q. What to quote from these tables

| figure | **quote this** | do NOT quote |
|---|---|---|
| Gemma validate_plan invocation by wording, plain (descriptive) | v11 **31.0** · v12 **25.1** · v13 **3.9**; Part B neutral 44.2 / 29.7 / 6.7 | one pooled invocation rate as if wording did not matter |
| pooled solve cost-of-pass multiplier, tools-plain ÷ unaided, by track (descriptive) | classical **0.67 [0.31, 1.16]** at 1:1, 0.27 [0.13, 0.46] at 5:1; numeric **2.70 [1.66, 4.01]** at 1:1, 1.07 [0.65, 1.62] at 5:1 | a track figure without the price ratio; a track figure as a test (k = 10 domains a track) |
| delivery gap, E4 folded with the hand reads | the S2-E table, with the frozen E4 column beside it | a folded count as the readout's E4 (the frozen E4 is the record) |

#### S2-W. Per wording: delivered beside invocation (Part A tools, Part C unaided)

Wording i pairs plain v1i with steered v1(i+3) (the steered prompt is the plain one plus one sentence naming the tool) and with unaided Part C on the plain wording.

| model | task | wording | n | delivered, plain | invocation, plain | delivered, steered | invocation, steered | delivered, unaided |
|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | v11 / v14 | 100 | 92.0 [86.0, 97.0] | 100.0 [96.3, 100.0]† | 95.0 [91.0, 99.0] | 100.0 [96.3, 100.0]† | 16.0 [7.0, 26.0] |
| Gemma-26B | solve | v12 / v15 | 100 | 93.0 [88.0, 98.0] | 100.0 [96.3, 100.0]† | 96.0 [92.0, 99.0] | 100.0 [96.3, 100.0]† | 32.0 [19.0, 46.0] |
| Gemma-26B | solve | v13 / v16 | 100 | 92.0 [86.0, 97.0] | 100.0 [96.3, 100.0]† | 95.0 [89.0, 100.0] | 100.0 [96.3, 100.0]† | 16.0 [9.0, 23.0] |
| Gemma-26B | validate_domain | v11 / v14 | 120 | 99.2 [97.5, 100.0] | 100.0 [96.9, 100.0]† | 98.3 [95.8, 100.0] | 100.0 [96.9, 100.0]† | 77.5 [63.3, 90.0] |
| Gemma-26B | validate_domain | v12 / v15 | 120 | 97.5 [95.0, 100.0] | 100.0 [96.9, 100.0]† | 98.3 [95.8, 100.0] | 100.0 [96.9, 100.0]† | 80.0 [66.7, 91.7] |
| Gemma-26B | validate_domain | v13 / v16 | 120 | 98.3 [95.8, 100.0] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 80.8 [68.3, 90.8] |
| Gemma-26B | validate_problem | v11 / v14 | 200 | 98.5 [97.0, 100.0] | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 76.0 [69.0, 82.5] |
| Gemma-26B | validate_problem | v12 / v15 | 200 | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 76.5 [71.0, 82.0] |
| Gemma-26B | validate_problem | v13 / v16 | 200 | 100.0 [98.1, 100.0]† | 100.0 [98.1, 100.0]† | 99.0 [97.5, 100.0] | 100.0 [98.1, 100.0]† | 76.0 [69.5, 82.5] |
| Gemma-26B | validate_plan | v11 / v14 | 1000 | 89.9 [84.8, 94.3] | 31.0 [15.2, 48.7] | 96.8 [93.0, 99.2] | 93.9 [84.4, 99.6] | 88.3 [83.6, 92.4] |
| Gemma-26B | validate_plan | v12 / v15 | 1000 | 90.4 [85.5, 94.5] | 25.1 [8.4, 43.7] | 96.5 [92.8, 99.1] | 92.5 [82.3, 100.0] | 88.2 [84.2, 91.9] |
| Gemma-26B | validate_plan | v13 / v16 | 1000 | 87.2 [82.5, 91.4] | 3.9 [0.1, 9.3] | 96.6 [93.2, 98.9] | 92.8 [82.5, 100.0] | 88.4 [84.1, 92.0] |
| Gemma-26B | simulate | v11 / v14 | 100 | 24.0 [12.0, 38.0] | 100.0 [96.3, 100.0]† | 23.0 [11.0, 37.0] | 100.0 [96.3, 100.0]† | 36.0 [20.0, 52.0] |
| Gemma-26B | simulate | v12 / v15 | 100 | 0.0 [0.0, 3.7]† | 99.0 [97.0, 100.0] | 0.0 [0.0, 3.7]† | 100.0 [96.3, 100.0]† | 0.0 [0.0, 3.7]† |
| Gemma-26B | simulate | v13 / v16 | 100 | 1.0 [0.0, 3.0] | 100.0 [96.3, 100.0]† | 2.0 [0.0, 5.0] | 100.0 [96.3, 100.0]† | 36.0 [20.0, 52.0] |
| Qwen3.5-9B | solve | v11 / v14 | 100 | 86.0 [78.0, 93.0] | 100.0 [96.3, 100.0]† | 92.0 [86.0, 97.0] | 100.0 [96.3, 100.0]† | 22.0 [13.0, 32.0] |
| Qwen3.5-9B | solve | v12 / v15 | 100 | 93.0 [87.0, 98.0] | 100.0 [96.3, 100.0]† | 93.0 [86.0, 99.0] | 100.0 [96.3, 100.0]† | 33.0 [20.0, 47.0] |
| Qwen3.5-9B | solve | v13 / v16 | 100 | 87.0 [80.0, 94.0] | 100.0 [96.3, 100.0]† | 82.0 [73.0, 90.0] | 100.0 [96.3, 100.0]† | 18.0 [10.0, 28.0] |
| Qwen3.5-9B | validate_domain | v11 / v14 | 120 | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 32.5 [20.0, 48.3] |
| Qwen3.5-9B | validate_domain | v12 / v15 | 120 | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 25.8 [16.7, 38.3] |
| Qwen3.5-9B | validate_domain | v13 / v16 | 120 | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 20.0 [13.3, 30.0] |
| Qwen3.5-9B | validate_problem | v11 / v14 | 200 | 95.5 [93.5, 97.5] | 100.0 [98.1, 100.0]† | 91.0 [85.0, 96.0] | 100.0 [98.1, 100.0]† | 67.5 [60.5, 73.5] |
| Qwen3.5-9B | validate_problem | v12 / v15 | 200 | 94.5 [92.0, 97.0] | 100.0 [98.1, 100.0]† | 90.5 [84.0, 95.5] | 100.0 [98.1, 100.0]† | 63.0 [56.0, 70.0] |
| Qwen3.5-9B | validate_problem | v13 / v16 | 200 | 94.5 [92.5, 96.5] | 100.0 [98.1, 100.0]† | 90.5 [83.5, 96.5] | 100.0 [98.1, 100.0]† | 67.0 [59.0, 74.5] |
| Qwen3.5-9B | validate_plan | v11 / v14 | 1000 | 93.4 [87.4, 98.0] | 99.0 [97.5, 100.0] | 95.7 [91.1, 99.0] | 100.0 [99.6, 100.0]† | 80.9 [75.1, 86.5] |
| Qwen3.5-9B | validate_plan | v12 / v15 | 1000 | 94.8 [90.7, 98.1] | 100.0 [99.6, 100.0]† | 95.7 [91.8, 98.8] | 100.0 [99.6, 100.0]† | 77.1 [70.3, 83.8] |
| Qwen3.5-9B | validate_plan | v13 / v16 | 1000 | 93.9 [89.9, 97.3] | 94.7 [86.0, 100.0] | 96.4 [93.1, 99.0] | 100.0 [99.6, 100.0]† | 81.4 [75.5, 87.0] |
| Qwen3.5-9B | simulate | v11 / v14 | 100 | 23.0 [11.0, 37.0] | 100.0 [96.3, 100.0]† | 24.0 [12.0, 37.0] | 100.0 [96.3, 100.0]† | 13.0 [4.0, 22.0] |
| Qwen3.5-9B | simulate | v12 / v15 | 100 | 6.0 [1.0, 12.0] | 44.0 [30.0, 58.0] | 2.0 [0.0, 6.0] | 100.0 [96.3, 100.0]† | 5.0 [0.0, 12.0] |
| Qwen3.5-9B | simulate | v13 / v16 | 100 | 23.0 [11.0, 37.0] | 100.0 [96.3, 100.0]† | 23.0 [12.0, 36.0] | 100.0 [96.3, 100.0]† | 10.0 [1.0, 22.0] |
| Qwen3.6-35B | solve | v11 / v14 | 100 | 78.0 [71.0, 85.0] | 95.0 [91.0, 98.0] | 87.0 [81.0, 93.0] | 100.0 [96.3, 100.0]† | 17.0 [7.0, 29.0] |
| Qwen3.6-35B | solve | v12 / v15 | 100 | 78.0 [68.0, 87.0] | 83.0 [73.0, 92.0] | 94.0 [89.0, 98.0] | 100.0 [96.3, 100.0]† | 42.0 [32.0, 52.0] |
| Qwen3.6-35B | solve | v13 / v16 | 100 | 75.0 [66.0, 83.0] | 85.0 [76.0, 93.0] | 81.0 [71.0, 90.0] | 99.0 [97.0, 100.0] | 17.0 [7.0, 29.0] |
| Qwen3.6-35B | validate_domain | v11 / v14 | 120 | 97.5 [92.5, 100.0] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 74.2 [63.3, 84.2] |
| Qwen3.6-35B | validate_domain | v12 / v15 | 120 | 99.2 [97.5, 100.0] | 100.0 [96.9, 100.0]† | 98.3 [95.0, 100.0] | 100.0 [96.9, 100.0]† | 81.7 [72.5, 90.0] |
| Qwen3.6-35B | validate_domain | v13 / v16 | 120 | 99.2 [97.5, 100.0] | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 100.0 [96.9, 100.0]† | 73.3 [60.8, 85.0] |
| Qwen3.6-35B | validate_problem | v11 / v14 | 200 | 95.0 [91.5, 98.0] | 100.0 [98.1, 100.0]† | 98.0 [96.0, 99.5] | 100.0 [98.1, 100.0]† | 76.5 [72.0, 81.0] |
| Qwen3.6-35B | validate_problem | v12 / v15 | 200 | 97.5 [95.5, 99.0] | 100.0 [98.1, 100.0]† | 98.0 [96.0, 99.5] | 100.0 [98.1, 100.0]† | 74.0 [69.5, 78.0] |
| Qwen3.6-35B | validate_problem | v13 / v16 | 200 | 96.0 [94.0, 98.0] | 98.0 [96.0, 99.5] | 96.0 [93.0, 98.5] | 100.0 [98.1, 100.0]† | 73.5 [67.5, 79.5] |
| Qwen3.6-35B | validate_plan | v11 / v14 | 1000 | 98.7 [97.9, 99.4] | 90.8 [80.8, 97.4] | 97.9 [96.4, 99.2] | 100.0 [99.6, 100.0]† | 90.6 [86.9, 93.9] |
| Qwen3.6-35B | validate_plan | v12 / v15 | 1000 | 97.0 [94.8, 98.8] | 84.3 [71.8, 94.6] | 98.8 [97.8, 99.6] | 100.0 [99.6, 100.0]† | 90.7 [87.8, 93.4] |
| Qwen3.6-35B | validate_plan | v13 / v16 | 1000 | 97.8 [96.4, 99.0] | 74.3 [59.8, 86.6] | 99.2 [98.6, 99.7] | 100.0 [99.6, 100.0]† | 90.0 [86.6, 93.2] |
| Qwen3.6-35B | simulate | v11 / v14 | 100 | 33.0 [20.0, 47.0] | 100.0 [96.3, 100.0]† | 35.0 [22.0, 49.0] | 100.0 [96.3, 100.0]† | 28.0 [14.0, 43.0] |
| Qwen3.6-35B | simulate | v12 / v15 | 100 | 23.0 [11.0, 36.0] | 99.0 [97.0, 100.0] | 24.0 [12.0, 37.0] | 100.0 [96.3, 100.0]† | 7.0 [1.0, 15.0] |
| Qwen3.6-35B | simulate | v13 / v16 | 100 | 29.0 [16.0, 43.0] | 100.0 [96.3, 100.0]† | 18.0 [9.0, 28.0] | 100.0 [96.3, 100.0]† | 18.0 [9.0, 28.0] |
| Gemma-26B, Part B (neutral prompt) | validate_plan | v11 / v14 | 1000 | 90.4 [86.6, 93.8] | 44.2 [27.3, 61.3] | 98.4 [96.8, 99.6] | 98.2 [95.5, 100.0] | – |
| Gemma-26B, Part B (neutral prompt) | validate_plan | v12 / v15 | 1000 | 90.3 [85.8, 94.4] | 29.7 [13.0, 47.5] | 98.9 [97.7, 99.7] | 97.2 [93.5, 100.0] | – |
| Gemma-26B, Part B (neutral prompt) | validate_plan | v13 / v16 | 1000 | 87.7 [83.3, 91.8] | 6.7 [0.7, 15.1] | 98.5 [97.0, 99.6] | 98.9 [97.2, 100.0] | – |

Spread over the three wordings (max − min, points):

| model | task | invocation, plain | delivered, plain | invocation, steered | delivered, steered | delivered, unaided |
|---|---|---|---|---|---|---|
| Gemma-26B | solve | 100.0–100.0 (0.0) | 92.0–93.0 (1.0) | 100.0–100.0 (0.0) | 95.0–96.0 (1.0) | 16.0–32.0 (16.0) |
| Gemma-26B | validate_domain | 100.0–100.0 (0.0) | 97.5–99.2 (1.7) | 100.0–100.0 (0.0) | 98.3–100.0 (1.7) | 77.5–80.8 (3.3) |
| Gemma-26B | validate_problem | 100.0–100.0 (0.0) | 98.5–100.0 (1.5) | 100.0–100.0 (0.0) | 99.0–100.0 (1.0) | 76.0–76.5 (0.5) |
| Gemma-26B | validate_plan | 3.9–31.0 (27.1) | 87.2–90.4 (3.2) | 92.5–93.9 (1.4) | 96.5–96.8 (0.3) | 88.2–88.4 (0.2) |
| Gemma-26B | simulate | 99.0–100.0 (1.0) | 0.0–24.0 (24.0) | 100.0–100.0 (0.0) | 0.0–23.0 (23.0) | 0.0–36.0 (36.0) |
| Qwen3.5-9B | solve | 100.0–100.0 (0.0) | 86.0–93.0 (7.0) | 100.0–100.0 (0.0) | 82.0–93.0 (11.0) | 18.0–33.0 (15.0) |
| Qwen3.5-9B | validate_domain | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) | 100.0–100.0 (0.0) | 20.0–32.5 (12.5) |
| Qwen3.5-9B | validate_problem | 100.0–100.0 (0.0) | 94.5–95.5 (1.0) | 100.0–100.0 (0.0) | 90.5–91.0 (0.5) | 63.0–67.5 (4.5) |
| Qwen3.5-9B | validate_plan | 94.7–100.0 (5.3) | 93.4–94.8 (1.4) | 100.0–100.0 (0.0) | 95.7–96.4 (0.7) | 77.1–81.4 (4.3) |
| Qwen3.5-9B | simulate | 44.0–100.0 (56.0) | 6.0–23.0 (17.0) | 100.0–100.0 (0.0) | 2.0–24.0 (22.0) | 5.0–13.0 (8.0) |
| Qwen3.6-35B | solve | 83.0–95.0 (12.0) | 75.0–78.0 (3.0) | 99.0–100.0 (1.0) | 81.0–94.0 (13.0) | 17.0–42.0 (25.0) |
| Qwen3.6-35B | validate_domain | 100.0–100.0 (0.0) | 97.5–99.2 (1.7) | 100.0–100.0 (0.0) | 98.3–100.0 (1.7) | 73.3–81.7 (8.3) |
| Qwen3.6-35B | validate_problem | 98.0–100.0 (2.0) | 95.0–97.5 (2.5) | 100.0–100.0 (0.0) | 96.0–98.0 (2.0) | 73.5–76.5 (3.0) |
| Qwen3.6-35B | validate_plan | 74.3–90.8 (16.5) | 97.0–98.7 (1.7) | 100.0–100.0 (0.0) | 97.9–99.2 (1.3) | 90.0–90.7 (0.7) |
| Qwen3.6-35B | simulate | 99.0–100.0 (1.0) | 23.0–33.0 (10.0) | 100.0–100.0 (0.0) | 18.0–35.0 (17.0) | 7.0–28.0 (21.0) |

#### S2-T. Classical against numeric (pooled over wordings)

Domains per track: classical 10, numeric 10. The bootstrap resamples the domains of one track only.

| model | task | track | n per arm | delivered, plain | invocation, plain | delivered, steered | invocation, steered | delivered, unaided |
|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | classical | 150 | 96.7 [92.0, 100.0] | 100.0 [97.5, 100.0]† | 98.7 [96.0, 100.0] | 100.0 [97.5, 100.0]† | 15.3 [5.3, 27.3] |
| Gemma-26B | solve | numeric | 150 | 88.0 [80.0, 95.3] | 100.0 [97.5, 100.0]† | 92.0 [85.3, 98.7] | 100.0 [97.5, 100.0]† | 27.3 [15.3, 40.7] |
| Gemma-26B | validate_domain | classical | 180 | 98.9 [96.7, 100.0] | 100.0 [97.9, 100.0]† | 99.4 [98.3, 100.0] | 100.0 [97.9, 100.0]† | 91.1 [86.1, 96.1] |
| Gemma-26B | validate_domain | numeric | 180 | 97.8 [94.4, 100.0] | 100.0 [97.9, 100.0]† | 98.3 [95.6, 100.0] | 100.0 [97.9, 100.0]† | 67.8 [46.7, 89.4] |
| Gemma-26B | validate_problem | classical | 300 | 99.7 [99.0, 100.0] | 100.0 [98.7, 100.0]† | 99.7 [99.0, 100.0] | 100.0 [98.7, 100.0]† | 75.0 [67.3, 83.3] |
| Gemma-26B | validate_problem | numeric | 300 | 99.3 [98.3, 100.0] | 100.0 [98.7, 100.0]† | 99.7 [99.0, 100.0] | 100.0 [98.7, 100.0]† | 77.3 [69.0, 85.0] |
| Gemma-26B | validate_plan | classical | 1500 | 88.0 [79.7, 94.7] | 22.8 [4.7, 42.9] | 96.0 [89.6, 99.6] | 88.1 [71.0, 100.0] | 88.3 [81.1, 94.0] |
| Gemma-26B | validate_plan | numeric | 1500 | 90.3 [86.1, 94.1] | 17.2 [3.9, 34.5] | 97.3 [95.3, 98.8] | 98.1 [94.5, 100.0] | 88.3 [83.7, 92.3] |
| Gemma-26B | simulate | classical | 150 | 7.3 [2.0, 15.3] | 99.3 [98.0, 100.0] | 8.7 [2.7, 16.0] | 100.0 [97.5, 100.0]† | 16.0 [4.0, 31.3] |
| Gemma-26B | simulate | numeric | 150 | 9.3 [4.0, 15.3] | 100.0 [97.5, 100.0]† | 8.0 [2.7, 14.7] | 100.0 [97.5, 100.0]† | 32.0 [17.3, 46.0] |
| Qwen3.5-9B | solve | classical | 150 | 94.0 [88.7, 98.7] | 100.0 [97.5, 100.0]† | 93.3 [89.3, 97.3] | 100.0 [97.5, 100.0]† | 16.0 [6.0, 26.7] |
| Qwen3.5-9B | solve | numeric | 150 | 83.3 [72.7, 93.3] | 100.0 [97.5, 100.0]† | 84.7 [74.0, 94.0] | 100.0 [97.5, 100.0]† | 32.7 [22.7, 42.7] |
| Qwen3.5-9B | validate_domain | classical | 180 | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 35.6 [21.1, 54.4] |
| Qwen3.5-9B | validate_domain | numeric | 180 | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 16.7 [15.0, 18.3] |
| Qwen3.5-9B | validate_problem | classical | 300 | 95.0 [92.3, 97.7] | 100.0 [98.7, 100.0]† | 94.0 [89.3, 97.7] | 100.0 [98.7, 100.0]† | 67.7 [57.7, 75.3] |
| Qwen3.5-9B | validate_problem | numeric | 300 | 94.7 [91.7, 97.7] | 100.0 [98.7, 100.0]† | 87.3 [76.7, 96.7] | 100.0 [98.7, 100.0]† | 64.0 [56.3, 70.3] |
| Qwen3.5-9B | validate_plan | classical | 1500 | 97.7 [95.3, 99.5] | 99.6 [98.8, 100.0] | 98.7 [96.7, 100.0] | 100.0 [99.7, 100.0]† | 80.5 [72.3, 88.2] |
| Qwen3.5-9B | validate_plan | numeric | 1500 | 90.4 [82.4, 96.7] | 96.2 [89.7, 100.0] | 93.1 [86.4, 98.3] | 100.0 [99.7, 100.0]† | 79.1 [70.7, 87.3] |
| Qwen3.5-9B | simulate | classical | 150 | 13.3 [2.0, 28.7] | 78.7 [73.3, 84.0] | 15.3 [4.0, 31.3] | 100.0 [97.5, 100.0]† | 12.7 [4.0, 22.7] |
| Qwen3.5-9B | simulate | numeric | 150 | 21.3 [8.0, 35.3] | 84.0 [76.7, 91.3] | 17.3 [7.3, 28.0] | 100.0 [97.5, 100.0]† | 6.0 [0.0, 13.3] |
| Qwen3.6-35B | solve | classical | 150 | 74.7 [63.3, 83.3] | 82.0 [73.3, 90.7] | 91.3 [84.0, 96.0] | 99.3 [98.0, 100.0] | 14.0 [7.3, 21.3] |
| Qwen3.6-35B | solve | numeric | 150 | 79.3 [69.3, 88.7] | 93.3 [85.3, 99.3] | 83.3 [76.0, 90.7] | 100.0 [97.5, 100.0]† | 36.7 [22.7, 52.0] |
| Qwen3.6-35B | validate_domain | classical | 180 | 97.8 [93.3, 100.0] | 100.0 [97.9, 100.0]† | 98.9 [96.7, 100.0] | 100.0 [97.9, 100.0]† | 87.8 [81.1, 93.9] |
| Qwen3.6-35B | validate_domain | numeric | 180 | 99.4 [98.3, 100.0] | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 100.0 [97.9, 100.0]† | 65.0 [51.1, 78.9] |
| Qwen3.6-35B | validate_problem | classical | 300 | 96.3 [93.3, 99.0] | 99.7 [99.0, 100.0] | 96.3 [93.7, 98.7] | 100.0 [98.7, 100.0]† | 72.7 [65.0, 80.0] |
| Qwen3.6-35B | validate_problem | numeric | 300 | 96.0 [93.7, 98.3] | 99.0 [98.0, 100.0] | 98.3 [96.0, 100.0] | 100.0 [98.7, 100.0]† | 76.7 [72.7, 80.7] |
| Qwen3.6-35B | validate_plan | classical | 1500 | 97.8 [96.7, 98.8] | 76.9 [57.5, 92.9] | 98.6 [97.4, 99.6] | 100.0 [99.7, 100.0]† | 92.1 [86.8, 96.5] |
| Qwen3.6-35B | validate_plan | numeric | 1500 | 97.9 [95.7, 99.6] | 89.4 [78.9, 95.9] | 98.7 [97.3, 99.7] | 100.0 [99.7, 100.0]† | 88.7 [85.6, 91.9] |
| Qwen3.6-35B | simulate | classical | 150 | 32.0 [14.0, 52.7] | 100.0 [97.5, 100.0]† | 25.3 [10.0, 43.3] | 100.0 [97.5, 100.0]† | 17.3 [6.0, 30.7] |
| Qwen3.6-35B | simulate | numeric | 150 | 24.7 [10.7, 40.0] | 99.3 [98.0, 100.0] | 26.0 [12.7, 40.7] | 100.0 [97.5, 100.0]† | 18.0 [8.0, 28.0] |

#### S2-D. Per domain, delivered % (plain / steered / unaided), pooled over wordings

Rows per domain and arm: solve 15, validate_domain 18, validate_problem 30, validate_plan 150, simulate 15. Too few for single-domain claims; read for pattern. Counts, Wilson intervals and invocation: `reference/delivered_rerun_secondary/per_domain.csv`.

| domain | track | model | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| barman | cla | Gemma-26B | 80 / 87 / 0 | 100 / 100 / 94 | 100 / 100 / 57 | 58 / 68 / 63 | 0 / 0 / 0 |
| barman | cla | Qwen3.5-9B | 87 / 87 / 0 | 100 / 100 / 17 | 90 / 93 / 63 | 96 / 97 / 57 | 0 / 0 / 0 |
| barman | cla | Qwen3.6-35B | 73 / 60 / 0 | 100 / 100 / 100 | 93 / 93 / 63 | 97 / 98 / 76 | 0 / 0 / 0 |
| blocksworld | cla | Gemma-26B | 100 / 100 / 27 | 100 / 100 / 100 | 100 / 97 / 87 | 100 / 100 / 100 | 7 / 7 / 20 |
| blocksworld | cla | Qwen3.5-9B | 100 / 93 / 27 | 100 / 100 / 17 | 100 / 100 / 73 | 100 / 100 / 95 | 20 / 20 / 0 |
| blocksworld | cla | Qwen3.6-35B | 87 / 93 / 27 | 100 / 100 / 94 | 100 / 100 / 80 | 95 / 95 / 100 | 20 / 13 / 13 |
| depots | cla | Gemma-26B | 100 / 100 / 20 | 100 / 100 / 100 | 97 / 100 / 67 | 89 / 100 / 87 | 0 / 0 / 0 |
| depots | cla | Qwen3.5-9B | 80 / 87 / 20 | 100 / 100 / 17 | 100 / 100 / 63 | 100 / 100 / 63 | 0 / 0 / 0 |
| depots | cla | Qwen3.6-35B | 73 / 93 / 13 | 100 / 100 / 89 | 100 / 100 / 57 | 100 / 100 / 97 | 7 / 0 / 0 |
| gripper | cla | Gemma-26B | 100 / 100 / 60 | 100 / 100 / 83 | 100 / 100 / 83 | 99 / 99 / 96 | 7 / 7 / 0 |
| gripper | cla | Qwen3.5-9B | 100 / 100 / 53 | 100 / 100 / 44 | 93 / 93 / 80 | 100 / 100 / 81 | 13 / 13 / 20 |
| gripper | cla | Qwen3.6-35B | 87 / 100 / 13 | 100 / 100 / 67 | 90 / 90 / 80 | 99 / 98 / 99 | 40 / 40 / 27 |
| miconic | cla | Gemma-26B | 100 / 100 / 20 | 100 / 100 / 83 | 100 / 100 / 77 | 98 / 99 / 94 | 40 / 33 / 67 |
| miconic | cla | Qwen3.5-9B | 100 / 100 / 33 | 100 / 100 / 39 | 90 / 90 / 87 | 100 / 100 / 94 | 73 / 80 / 27 |
| miconic | cla | Qwen3.6-35B | 93 / 93 / 13 | 100 / 100 / 83 | 100 / 100 / 73 | 95 / 100 / 93 | 100 / 87 / 60 |
| parking | cla | Gemma-26B | 100 / 100 / 0 | 100 / 100 / 83 | 100 / 100 / 100 | 85 / 100 / 89 | 0 / 20 / 0 |
| parking | cla | Qwen3.5-9B | 100 / 100 / 0 | 100 / 100 / 67 | 100 / 100 / 70 | 99 / 100 / 82 | 0 / 0 / 0 |
| parking | cla | Qwen3.6-35B | 67 / 93 / 7 | 100 / 100 / 72 | 100 / 100 / 90 | 99 / 99 / 93 | 53 / 40 / 0 |
| rovers | cla | Gemma-26B | 100 / 100 / 0 | 100 / 100 / 100 | 100 / 100 / 57 | 85 / 97 / 91 | 0 / 0 / 0 |
| rovers | cla | Qwen3.5-9B | 100 / 93 / 7 | 100 / 100 / 17 | 100 / 100 / 30 | 97 / 100 / 79 | 0 / 0 / 0 |
| rovers | cla | Qwen3.6-35B | 33 / 93 / 7 | 78 / 89 / 100 | 87 / 93 / 50 | 99 / 100 / 95 | 0 / 0 / 7 |
| satellite | cla | Gemma-26B | 100 / 100 / 7 | 89 / 94 / 100 | 100 / 100 / 83 | 94 / 100 / 95 | 7 / 7 / 47 |
| satellite | cla | Qwen3.5-9B | 93 / 93 / 20 | 100 / 100 / 100 | 90 / 77 / 77 | 89 / 90 / 95 | 0 / 13 / 20 |
| satellite | cla | Qwen3.6-35B | 80 / 93 / 33 | 100 / 100 / 94 | 93 / 90 / 87 | 97 / 100 / 97 | 60 / 47 / 47 |
| tpp | cla | Gemma-26B | 87 / 100 / 0 | 100 / 100 / 83 | 100 / 100 / 70 | 77 / 99 / 76 | 0 / 0 / 0 |
| tpp | cla | Qwen3.5-9B | 80 / 80 / 0 | 100 / 100 / 22 | 97 / 97 / 70 | 96 / 100 / 70 | 0 / 0 / 13 |
| tpp | cla | Qwen3.6-35B | 67 / 93 / 0 | 100 / 100 / 89 | 100 / 100 / 70 | 100 / 100 / 78 | 0 / 0 / 7 |
| zenotravel | cla | Gemma-26B | 100 / 100 / 20 | 100 / 100 / 83 | 100 / 100 / 70 | 95 / 98 / 93 | 13 / 13 / 27 |
| zenotravel | cla | Qwen3.5-9B | 100 / 100 / 0 | 100 / 100 / 17 | 90 / 90 / 63 | 100 / 100 / 88 | 27 / 27 / 47 |
| zenotravel | cla | Qwen3.6-35B | 87 / 100 / 27 | 100 / 100 / 89 | 100 / 97 / 77 | 96 / 95 / 93 | 40 / 27 / 13 |
| block-grouping | num | Gemma-26B | 100 / 100 / 47 | 100 / 100 / 17 | 100 / 100 / 77 | 87 / 99 / 85 | 7 / 7 / 60 |
| block-grouping | num | Qwen3.5-9B | 73 / 73 / 33 | 100 / 100 / 17 | 90 / 87 / 47 | 81 / 89 / 75 | 13 / 13 / 0 |
| block-grouping | num | Qwen3.6-35B | 87 / 80 / 80 | 100 / 100 / 61 | 100 / 100 / 77 | 98 / 100 / 85 | 7 / 13 / 40 |
| counters | num | Gemma-26B | 80 / 73 / 47 | 100 / 100 / 100 | 100 / 100 / 73 | 93 / 97 / 81 | 7 / 7 / 33 |
| counters | num | Qwen3.5-9B | 53 / 53 / 33 | 100 / 100 / 17 | 100 / 100 / 40 | 61 / 67 / 66 | 0 / 0 / 0 |
| counters | num | Qwen3.6-35B | 53 / 60 / 20 | 100 / 100 / 83 | 97 / 100 / 63 | 91 / 95 / 85 | 20 / 7 / 7 |
| delivery | num | Gemma-26B | 73 / 87 / 33 | 83 / 89 / 67 | 100 / 97 / 73 | 90 / 98 / 90 | 0 / 0 / 0 |
| delivery | num | Qwen3.5-9B | 100 / 100 / 27 | 100 / 100 / 17 | 90 / 90 / 60 | 100 / 100 / 88 | 0 / 0 / 0 |
| delivery | num | Qwen3.6-35B | 60 / 80 / 13 | 100 / 100 / 89 | 90 / 93 / 77 | 100 / 100 / 93 | 0 / 0 / 0 |
| depot | num | Gemma-26B | 80 / 87 / 0 | 100 / 100 / 100 | 100 / 100 / 50 | 75 / 90 / 73 | 0 / 0 / 0 |
| depot | num | Qwen3.5-9B | 80 / 87 / 0 | 100 / 100 / 22 | 100 / 100 / 70 | 87 / 100 / 53 | 0 / 0 / 0 |
| depot | num | Qwen3.6-35B | 60 / 73 / 13 | 100 / 100 / 100 | 90 / 90 / 80 | 100 / 100 / 84 | 0 / 20 / 0 |
| drone | num | Gemma-26B | 80 / 73 / 7 | 100 / 100 / 28 | 100 / 100 / 93 | 90 / 97 / 94 | 0 / 0 / 27 |
| drone | num | Qwen3.5-9B | 60 / 60 / 27 | 100 / 100 / 17 | 100 / 100 / 67 | 90 / 89 / 75 | 20 / 20 / 0 |
| drone | num | Qwen3.6-35B | 80 / 73 / 27 | 100 / 100 / 61 | 100 / 100 / 90 | 99 / 99 / 95 | 20 / 20 / 7 |
| farmland | num | Gemma-26B | 100 / 100 / 13 | 100 / 100 / 100 | 100 / 100 / 90 | 100 / 100 / 97 | 20 / 20 / 53 |
| farmland | num | Qwen3.5-9B | 100 / 100 / 47 | 100 / 100 / 11 | 100 / 100 / 73 | 98 / 100 / 100 | 53 / 40 / 0 |
| farmland | num | Qwen3.6-35B | 100 / 100 / 27 | 100 / 100 / 33 | 100 / 100 / 77 | 100 / 100 / 93 | 53 / 40 / 33 |
| gardening | num | Gemma-26B | 100 / 100 / 33 | 94 / 94 / 33 | 97 / 100 / 70 | 95 / 100 / 87 | 20 / 20 / 53 |
| gardening | num | Qwen3.5-9B | 87 / 93 / 47 | 100 / 100 / 17 | 90 / 50 / 70 | 100 / 97 / 69 | 27 / 33 / 7 |
| gardening | num | Qwen3.6-35B | 100 / 87 / 53 | 94 / 100 / 56 | 97 / 100 / 80 | 100 / 100 / 81 | 27 / 33 / 33 |
| pogo_stick | num | Gemma-26B | 67 / 100 / 7 | 100 / 100 / 100 | 97 / 100 / 90 | 91 / 100 / 87 | 0 / 0 / 40 |
| pogo_stick | num | Qwen3.5-9B | 100 / 100 / 13 | 100 / 100 / 17 | 97 / 67 / 70 | 98 / 100 / 96 | 0 / 0 / 0 |
| pogo_stick | num | Qwen3.6-35B | 80 / 100 / 13 | 100 / 100 / 83 | 93 / 100 / 77 | 100 / 98 / 97 | 0 / 0 / 0 |
| sailing | num | Gemma-26B | 100 / 100 / 67 | 100 / 100 / 100 | 100 / 100 / 90 | 85 / 96 / 95 | 13 / 0 / 53 |
| sailing | num | Qwen3.5-9B | 80 / 80 / 40 | 100 / 100 / 17 | 90 / 80 / 70 | 90 / 90 / 81 | 60 / 20 / 20 |
| sailing | num | Qwen3.6-35B | 80 / 87 / 73 | 100 / 100 / 56 | 100 / 100 / 70 | 92 / 95 / 86 | 67 / 67 / 27 |
| zenotravel-numeric | num | Gemma-26B | 100 / 100 / 20 | 100 / 100 / 33 | 100 / 100 / 67 | 97 / 96 / 94 | 27 / 27 / 0 |
| zenotravel-numeric | num | Qwen3.5-9B | 100 / 100 / 60 | 100 / 100 / 17 | 90 / 100 / 73 | 100 / 100 / 87 | 40 / 47 / 33 |
| zenotravel-numeric | num | Qwen3.6-35B | 93 / 93 / 47 | 100 / 100 / 28 | 93 / 100 / 77 | 99 / 99 / 89 | 53 / 60 / 33 |

#### S2-C. Cost-of-pass multiplier by price ratio, split by track (delivered score)

Cost-of-pass = (input + r × output tokens, summed over all turns) / delivered successes; multiplier = tool arm ÷ unaided Part C (same run, same grader, same fixtures); below 1 the tool arm is cheaper per delivered success. r = output:input price ratio. Domain-cluster bootstrap 95%, the same domain draw for both arms (seed 20261002, 10,000 draws); draws where an arm has no success are dropped and counted. Track *all* reproduces `secondary.json` at 1, 3, 4 and 5:1; 2:1 and the track split are new here. Tokens per trial in the last columns.

**tools, plain ÷ unaided**

| model | task | track | domains | × at 1:1 | × at 2:1 | × at 3:1 | × at 4:1 | × at 5:1 | tokens/trial, tools | tokens/trial, unaided |
|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | classical | 10 | 0.68 [0.23, 1.37] (1 draw dropped) | 0.45 [0.15, 0.91] (1 draw dropped) | 0.35 [0.12, 0.71] (1 draw dropped) | 0.30 [0.10, 0.60] (1 draw dropped) | 0.27 [0.09, 0.54] (1 draw dropped) | 18,241 | 4,264 |
| Gemma-26B | solve | numeric | 10 | 2.07 [1.07, 3.30] | 1.42 [0.72, 2.31] | 1.14 [0.57, 1.86] | 0.97 [0.49, 1.61] | 0.87 [0.44, 1.45] | 22,540 | 3,385 |
| Gemma-26B | solve | all | 20 | 1.23 [0.68, 1.98] | 0.82 [0.46, 1.35] | 0.65 [0.36, 1.07] | 0.56 [0.31, 0.91] | 0.50 [0.28, 0.82] | 20,391 | 3,825 |
| Gemma-26B | validate_domain | classical | 10 | 5.78 [5.05, 6.82] | 4.43 [3.87, 5.21] | 3.70 [3.20, 4.37] | 3.24 [2.79, 3.87] | 2.93 [2.50, 3.51] | 9,017 | 1,436 |
| Gemma-26B | validate_domain | numeric | 10 | 4.48 [3.02, 6.14] | 3.43 [2.33, 4.62] | 2.86 [1.95, 3.82] | 2.50 [1.71, 3.33] | 2.26 [1.55, 3.00] | 9,031 | 1,397 |
| Gemma-26B | validate_domain | all | 20 | 5.15 [4.22, 6.10] | 3.94 [3.25, 4.63] | 3.29 [2.71, 3.87] | 2.88 [2.38, 3.39] | 2.60 [2.14, 3.07] | 9,024 | 1,417 |
| Gemma-26B | validate_problem | classical | 10 | 4.42 [3.53, 5.53] | 3.54 [2.82, 4.39] | 3.05 [2.41, 3.75] | 2.73 [2.16, 3.36] | 2.51 [1.98, 3.08] | 10,823 | 1,843 |
| Gemma-26B | validate_problem | numeric | 10 | 4.60 [3.83, 5.42] | 3.80 [3.10, 4.52] | 3.33 [2.67, 3.99] | 3.02 [2.39, 3.65] | 2.80 [2.20, 3.41] | 11,149 | 1,885 |
| Gemma-26B | validate_problem | all | 20 | 4.51 [3.90, 5.17] | 3.67 [3.14, 4.23] | 3.19 [2.71, 3.69] | 2.87 [2.43, 3.34] | 2.65 [2.23, 3.09] | 10,986 | 1,864 |
| Gemma-26B | validate_plan | classical | 10 | 2.54 [2.07, 3.26] | 2.06 [1.75, 2.50] | 1.81 [1.58, 2.12] | 1.66 [1.47, 1.90] | 1.55 [1.40, 1.75] | 6,513 | 2,577 |
| Gemma-26B | validate_plan | numeric | 10 | 2.55 [2.14, 3.14] | 2.13 [1.84, 2.53] | 1.90 [1.68, 2.21] | 1.76 [1.57, 2.01] | 1.66 [1.50, 1.87] | 6,523 | 2,503 |
| Gemma-26B | validate_plan | all | 20 | 2.54 [2.21, 2.98] | 2.09 [1.87, 2.38] | 1.85 [1.68, 2.06] | 1.70 [1.57, 1.87] | 1.60 [1.49, 1.74] | 6,518 | 2,540 |
| Gemma-26B | simulate | classical | 10 | 10.52 [5.88, 23.38] (62 draws dropped) | 6.87 [3.84, 15.18] (62 draws dropped) | 5.32 [2.97, 11.73] (62 draws dropped) | 4.46 [2.48, 9.83] (62 draws dropped) | 3.91 [2.18, 8.63] (62 draws dropped) | 21,453 | 4,448 |
| Gemma-26B | simulate | numeric | 10 | 14.50 [7.36, 32.32] (1 draw dropped) | 9.54 [4.85, 21.18] (1 draw dropped) | 7.48 [3.81, 16.66] (1 draw dropped) | 6.36 [3.24, 14.16] (1 draw dropped) | 5.65 [2.86, 12.57] (1 draw dropped) | 22,189 | 5,245 |
| Gemma-26B | simulate | all | 20 | 12.97 [8.16, 22.26] | 8.49 [5.36, 14.55] | 6.62 [4.16, 11.36] | 5.59 [3.51, 9.60] | 4.93 [3.09, 8.50] | 21,821 | 4,847 |
| Qwen3.5-9B | solve | classical | 10 | 0.49 [0.17, 0.97] (3 draws dropped) | 0.31 [0.11, 0.61] (3 draws dropped) | 0.24 [0.08, 0.46] (3 draws dropped) | 0.20 [0.07, 0.39] (3 draws dropped) | 0.17 [0.06, 0.34] (3 draws dropped) | 15,580 | 5,408 |
| Qwen3.5-9B | solve | numeric | 10 | 2.94 [1.71, 4.47] | 1.90 [1.07, 2.97] | 1.47 [0.83, 2.33] | 1.25 [0.70, 1.99] | 1.10 [0.62, 1.76] | 33,943 | 4,529 |
| Qwen3.5-9B | solve | all | 20 | 1.37 [0.73, 2.28] | 0.87 [0.46, 1.47] | 0.67 [0.36, 1.14] | 0.57 [0.30, 0.96] | 0.50 [0.26, 0.85] | 24,761 | 4,969 |
| Qwen3.5-9B | validate_domain | classical | 10 | 1.44 [0.76, 2.70] | 0.92 [0.48, 1.79] | 0.70 [0.36, 1.39] | 0.58 [0.30, 1.16] | 0.51 [0.26, 1.02] | 9,992 | 2,475 |
| Qwen3.5-9B | validate_domain | numeric | 10 | 0.71 [0.57, 0.93] | 0.46 [0.35, 0.64] | 0.35 [0.26, 0.50] | 0.29 [0.22, 0.42] | 0.25 [0.19, 0.37] | 9,959 | 2,335 |
| Qwen3.5-9B | validate_domain | all | 20 | 1.08 [0.71, 1.68] | 0.70 [0.45, 1.10] | 0.53 [0.34, 0.85] | 0.44 [0.28, 0.71] | 0.38 [0.25, 0.62] | 9,976 | 2,405 |
| Qwen3.5-9B | validate_problem | classical | 10 | 5.18 [4.05, 6.44] | 4.04 [3.12, 5.11] | 3.42 [2.57, 4.42] | 3.03 [2.22, 4.00] | 2.76 [1.98, 3.69] | 13,703 | 1,886 |
| Qwen3.5-9B | validate_problem | numeric | 10 | 3.75 [2.80, 4.73] | 2.79 [1.96, 3.70] | 2.30 [1.56, 3.14] | 2.00 [1.33, 2.79] | 1.80 [1.18, 2.54] | 12,708 | 2,292 |
| Qwen3.5-9B | validate_problem | all | 20 | 4.39 [3.58, 5.27] | 3.33 [2.63, 4.12] | 2.78 [2.14, 3.51] | 2.44 [1.85, 3.12] | 2.21 [1.65, 2.86] | 13,205 | 2,089 |
| Qwen3.5-9B | validate_plan | classical | 10 | 3.79 [2.82, 5.70] | 2.63 [1.97, 3.95] | 2.10 [1.57, 3.16] | 1.80 [1.34, 2.71] | 1.60 [1.19, 2.41] | 14,900 | 3,238 |
| Qwen3.5-9B | validate_plan | numeric | 10 | 4.16 [3.52, 5.26] | 3.00 [2.50, 3.86] | 2.45 [2.01, 3.19] | 2.12 [1.73, 2.80] | 1.91 [1.54, 2.54] | 14,487 | 3,044 |
| Qwen3.5-9B | validate_plan | all | 20 | 3.97 [3.29, 4.99] | 2.81 [2.31, 3.56] | 2.26 [1.85, 2.88] | 1.95 [1.59, 2.49] | 1.74 [1.41, 2.24] | 14,694 | 3,141 |
| Qwen3.5-9B | simulate | classical | 10 | 6.00 [2.24, 23.67] (68 draws dropped) | 3.98 [1.50, 15.69] (68 draws dropped) | 3.12 [1.18, 12.33] (68 draws dropped) | 2.65 [1.00, 10.42] (68 draws dropped) | 2.34 [0.89, 9.22] (68 draws dropped) | 26,732 | 4,234 |
| Qwen3.5-9B | simulate | numeric | 10 | 1.13 [0.21, 2.32] (278 draws dropped) | 0.75 [0.14, 1.57] (278 draws dropped) | 0.59 [0.11, 1.26] (278 draws dropped) | 0.51 [0.09, 1.09] (278 draws dropped) | 0.46 [0.08, 0.97] (278 draws dropped) | 20,104 | 5,024 |
| Qwen3.5-9B | simulate | all | 20 | 2.72 [1.22, 5.76] | 1.81 [0.80, 3.80] | 1.42 [0.63, 2.98] | 1.21 [0.54, 2.52] | 1.08 [0.48, 2.24] | 23,418 | 4,629 |
| Qwen3.6-35B | solve | classical | 10 | 0.92 [0.46, 1.56] | 0.63 [0.31, 1.08] | 0.51 [0.26, 0.88] | 0.45 [0.22, 0.77] | 0.41 [0.21, 0.70] | 22,198 | 4,546 |
| Qwen3.6-35B | solve | numeric | 10 | 3.13 [1.86, 4.88] | 2.06 [1.22, 3.23] | 1.63 [0.97, 2.55] | 1.40 [0.83, 2.17] | 1.25 [0.75, 1.94] | 30,150 | 4,454 |
| Qwen3.6-35B | solve | all | 20 | 1.91 [1.16, 2.94] | 1.28 [0.78, 1.97] | 1.02 [0.63, 1.57] | 0.89 [0.55, 1.35] | 0.80 [0.50, 1.22] | 26,174 | 4,500 |
| Qwen3.6-35B | validate_domain | classical | 10 | 4.52 [4.12, 5.03] | 3.05 [2.76, 3.38] | 2.38 [2.13, 2.66] | 1.99 [1.77, 2.24] | 1.75 [1.53, 1.98] | 9,999 | 1,987 |
| Qwen3.6-35B | validate_domain | numeric | 10 | 2.99 [2.23, 3.83] | 1.95 [1.42, 2.54] | 1.49 [1.07, 1.97] | 1.24 [0.88, 1.65] | 1.08 [0.76, 1.44] | 9,941 | 2,172 |
| Qwen3.6-35B | validate_domain | all | 20 | 3.71 [3.12, 4.30] | 2.46 [2.04, 2.89] | 1.90 [1.56, 2.25] | 1.59 [1.29, 1.89] | 1.38 [1.12, 1.65] | 9,970 | 2,080 |
| Qwen3.6-35B | validate_problem | classical | 10 | 4.12 [3.41, 4.94] | 3.06 [2.53, 3.64] | 2.53 [2.08, 3.01] | 2.20 [1.80, 2.64] | 1.99 [1.62, 2.40] | 11,688 | 2,142 |
| Qwen3.6-35B | validate_problem | numeric | 10 | 4.66 [4.30, 4.98] | 3.63 [3.25, 3.99] | 3.09 [2.71, 3.46] | 2.75 [2.38, 3.13] | 2.52 [2.16, 2.89] | 12,462 | 2,136 |
| Qwen3.6-35B | validate_problem | all | 20 | 4.38 [3.93, 4.83] | 3.34 [2.97, 3.71] | 2.80 [2.47, 3.14] | 2.47 [2.16, 2.78] | 2.24 [1.96, 2.55] | 12,075 | 2,139 |
| Qwen3.6-35B | validate_plan | classical | 10 | 3.26 [2.82, 3.80] | 2.26 [1.93, 2.63] | 1.81 [1.54, 2.11] | 1.56 [1.32, 1.83] | 1.40 [1.18, 1.64] | 12,174 | 3,517 |
| Qwen3.6-35B | validate_plan | numeric | 10 | 3.95 [3.50, 4.52] | 2.81 [2.45, 3.26] | 2.28 [1.96, 2.67] | 1.97 [1.69, 2.32] | 1.77 [1.51, 2.09] | 14,064 | 3,229 |
| Qwen3.6-35B | validate_plan | all | 20 | 3.60 [3.22, 4.02] | 2.52 [2.24, 2.85] | 2.03 [1.79, 2.31] | 1.75 [1.54, 1.99] | 1.57 [1.38, 1.79] | 13,119 | 3,373 |
| Qwen3.6-35B | simulate | classical | 10 | 3.01 [1.57, 4.39] | 2.00 [1.05, 2.93] | 1.56 [0.83, 2.28] | 1.31 [0.70, 1.91] | 1.15 [0.61, 1.68] | 21,422 | 3,854 |
| Qwen3.6-35B | simulate | numeric | 10 | 3.82 [2.26, 7.51] | 2.53 [1.50, 4.94] | 1.98 [1.17, 3.86] | 1.67 [0.98, 3.27] | 1.48 [0.87, 2.90] | 23,448 | 4,483 |
| Qwen3.6-35B | simulate | all | 20 | 3.36 [2.33, 4.85] | 2.23 [1.55, 3.20] | 1.74 [1.21, 2.50] | 1.46 [1.02, 2.11] | 1.29 [0.90, 1.86] | 22,435 | 4,169 |
| pooled (3 models) | solve | classical | 10 | 0.67 [0.31, 1.16] | 0.44 [0.21, 0.76] | 0.35 [0.17, 0.60] | 0.30 [0.14, 0.51] | 0.27 [0.13, 0.46] | 18,673 | 4,740 |
| pooled (3 models) | solve | numeric | 10 | 2.70 [1.66, 4.01] | 1.79 [1.08, 2.68] | 1.41 [0.85, 2.12] | 1.20 [0.73, 1.81] | 1.07 [0.65, 1.62] | 28,878 | 4,123 |
| pooled (3 models) | solve | all | 20 | 1.48 [0.89, 2.27] | 0.97 [0.59, 1.50] | 0.76 [0.46, 1.18] | 0.65 [0.40, 1.01] | 0.58 [0.35, 0.90] | 23,775 | 4,431 |
| pooled (3 models) | validate_domain | classical | 10 | 3.56 [3.05, 4.39] | 2.42 [2.05, 3.01] | 1.90 [1.59, 2.38] | 1.60 [1.32, 2.02] | 1.40 [1.15, 1.78] | 9,669 | 1,966 |
| pooled (3 models) | validate_domain | numeric | 10 | 2.46 [1.97, 2.97] | 1.66 [1.32, 2.01] | 1.29 [1.02, 1.56] | 1.08 [0.85, 1.31] | 0.95 [0.74, 1.15] | 9,644 | 1,968 |
| pooled (3 models) | validate_domain | all | 20 | 3.01 [2.58, 3.52] | 2.04 [1.74, 2.40] | 1.59 [1.35, 1.88] | 1.34 [1.13, 1.59] | 1.17 [0.99, 1.39] | 9,657 | 1,967 |
| pooled (3 models) | validate_problem | classical | 10 | 4.57 [3.87, 5.29] | 3.53 [3.06, 3.96] | 2.97 [2.60, 3.31] | 2.62 [2.29, 2.92] | 2.39 [2.08, 2.66] | 12,072 | 1,957 |
| pooled (3 models) | validate_problem | numeric | 10 | 4.32 [3.82, 4.82] | 3.37 [2.86, 3.88] | 2.85 [2.37, 3.36] | 2.53 [2.07, 3.02] | 2.31 [1.87, 2.78] | 12,106 | 2,104 |
| pooled (3 models) | validate_problem | all | 20 | 4.44 [4.01, 4.88] | 3.45 [3.10, 3.79] | 2.91 [2.60, 3.21] | 2.58 [2.29, 2.86] | 2.35 [2.07, 2.62] | 12,089 | 2,031 |
| pooled (3 models) | validate_plan | classical | 10 | 3.31 [2.76, 4.18] | 2.38 [1.99, 2.99] | 1.95 [1.63, 2.43] | 1.69 [1.42, 2.11] | 1.53 [1.28, 1.91] | 11,196 | 3,110 |
| pooled (3 models) | validate_plan | numeric | 10 | 3.67 [3.26, 4.29] | 2.73 [2.41, 3.20] | 2.27 [1.98, 2.67] | 1.99 [1.74, 2.36] | 1.81 [1.57, 2.14] | 11,691 | 2,925 |
| pooled (3 models) | validate_plan | all | 20 | 3.49 [3.09, 3.99] | 2.55 [2.25, 2.92] | 2.10 [1.85, 2.40] | 1.83 [1.62, 2.11] | 1.66 [1.46, 1.91] | 11,444 | 3,018 |
| pooled (3 models) | simulate | classical | 10 | 4.85 [2.97, 7.89] | 3.21 [1.98, 5.18] | 2.50 [1.55, 4.03] | 2.10 [1.31, 3.38] | 1.85 [1.16, 2.97] | 23,202 | 4,179 |
| pooled (3 models) | simulate | numeric | 10 | 4.51 [3.17, 8.03] | 2.98 [2.09, 5.28] | 2.34 [1.63, 4.15] | 1.99 [1.38, 3.53] | 1.77 [1.22, 3.14] | 21,914 | 4,917 |
| pooled (3 models) | simulate | all | 20 | 4.68 [3.55, 6.63] | 3.09 [2.35, 4.36] | 2.42 [1.84, 3.40] | 2.05 [1.56, 2.88] | 1.81 [1.38, 2.54] | 22,558 | 4,548 |

**tools, steered ÷ unaided**

| model | task | track | domains | × at 1:1 | × at 2:1 | × at 3:1 | × at 4:1 | × at 5:1 | tokens/trial, tools | tokens/trial, unaided |
|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | classical | 10 | 0.56 [0.18, 1.18] (1 draw dropped) | 0.37 [0.12, 0.78] (1 draw dropped) | 0.29 [0.09, 0.61] (1 draw dropped) | 0.24 [0.08, 0.52] (1 draw dropped) | 0.22 [0.07, 0.46] (1 draw dropped) | 15,299 | 4,264 |
| Gemma-26B | solve | numeric | 10 | 1.76 [0.89, 2.81] | 1.21 [0.61, 1.95] | 0.97 [0.48, 1.57] | 0.83 [0.41, 1.35] | 0.74 [0.37, 1.22] | 20,010 | 3,385 |
| Gemma-26B | solve | all | 20 | 1.03 [0.56, 1.69] | 0.69 [0.37, 1.15] | 0.55 [0.30, 0.91] | 0.47 [0.25, 0.78] | 0.42 [0.23, 0.70] | 17,655 | 3,825 |
| Gemma-26B | validate_domain | classical | 10 | 5.75 [5.04, 6.72] | 4.40 [3.87, 5.14] | 3.67 [3.19, 4.31] | 3.22 [2.78, 3.81] | 2.90 [2.48, 3.47] | 9,014 | 1,436 |
| Gemma-26B | validate_domain | numeric | 10 | 4.46 [3.00, 6.11] | 3.41 [2.31, 4.60] | 2.84 [1.93, 3.81] | 2.49 [1.70, 3.31] | 2.24 [1.53, 2.98] | 9,033 | 1,397 |
| Gemma-26B | validate_domain | all | 20 | 5.12 [4.19, 6.06] | 3.92 [3.23, 4.59] | 3.27 [2.70, 3.83] | 2.86 [2.36, 3.36] | 2.58 [2.13, 3.04] | 9,023 | 1,417 |
| Gemma-26B | validate_problem | classical | 10 | 4.28 [3.33, 5.51] | 3.43 [2.65, 4.35] | 2.94 [2.27, 3.71] | 2.63 [2.03, 3.31] | 2.42 [1.86, 3.04] | 10,492 | 1,843 |
| Gemma-26B | validate_problem | numeric | 10 | 4.56 [3.81, 5.34] | 3.77 [3.08, 4.45] | 3.30 [2.66, 3.93] | 2.99 [2.39, 3.59] | 2.77 [2.20, 3.34] | 11,090 | 1,885 |
| Gemma-26B | validate_problem | all | 20 | 4.42 [3.78, 5.12] | 3.60 [3.05, 4.17] | 3.12 [2.63, 3.64] | 2.81 [2.36, 3.29] | 2.59 [2.17, 3.04] | 10,791 | 1,864 |
| Gemma-26B | validate_plan | classical | 10 | 3.84 [3.18, 4.67] | 2.94 [2.54, 3.42] | 2.47 [2.19, 2.81] | 2.19 [1.97, 2.45] | 2.00 [1.81, 2.22] | 10,757 | 2,577 |
| Gemma-26B | validate_plan | numeric | 10 | 4.60 [4.13, 5.10] | 3.62 [3.23, 4.02] | 3.09 [2.74, 3.44] | 2.76 [2.43, 3.08] | 2.53 [2.23, 2.83] | 12,686 | 2,503 |
| Gemma-26B | validate_plan | all | 20 | 4.22 [3.73, 4.72] | 3.27 [2.93, 3.63] | 2.77 [2.50, 3.07] | 2.46 [2.23, 2.72] | 2.25 [2.05, 2.49] | 11,722 | 2,540 |
| Gemma-26B | simulate | classical | 10 | 9.09 [2.92, 20.65] (62 draws dropped) | 5.93 [1.91, 13.36] (62 draws dropped) | 4.59 [1.48, 10.29] (62 draws dropped) | 3.84 [1.24, 8.59] (62 draws dropped) | 3.37 [1.09, 7.52] (62 draws dropped) | 21,891 | 4,448 |
| Gemma-26B | simulate | numeric | 10 | 17.25 [7.61, 53.81] (10 draws dropped) | 11.32 [4.99, 35.23] (10 draws dropped) | 8.86 [3.91, 27.65] (10 draws dropped) | 7.52 [3.31, 23.46] (10 draws dropped) | 6.67 [2.94, 20.77] (10 draws dropped) | 22,616 | 5,245 |
| Gemma-26B | simulate | all | 20 | 13.22 [7.33, 24.72] | 8.65 [4.79, 16.07] | 6.73 [3.72, 12.52] | 5.68 [3.14, 10.56] | 5.01 [2.77, 9.33] | 22,253 | 4,847 |
| Qwen3.5-9B | solve | classical | 10 | 0.45 [0.16, 0.91] (3 draws dropped) | 0.28 [0.10, 0.56] (3 draws dropped) | 0.22 [0.08, 0.43] (3 draws dropped) | 0.18 [0.07, 0.36] (3 draws dropped) | 0.16 [0.06, 0.31] (3 draws dropped) | 14,297 | 5,408 |
| Qwen3.5-9B | solve | numeric | 10 | 2.69 [1.55, 4.13] | 1.74 [0.98, 2.72] | 1.35 [0.75, 2.12] | 1.14 [0.63, 1.80] | 1.01 [0.56, 1.59] | 31,625 | 4,529 |
| Qwen3.5-9B | solve | all | 20 | 1.26 [0.67, 2.11] | 0.80 [0.42, 1.35] | 0.62 [0.33, 1.05] | 0.52 [0.28, 0.89] | 0.46 [0.24, 0.78] | 22,961 | 4,969 |
| Qwen3.5-9B | validate_domain | classical | 10 | 1.44 [0.76, 2.71] | 0.92 [0.48, 1.80] | 0.71 [0.36, 1.39] | 0.58 [0.30, 1.17] | 0.51 [0.26, 1.02] | 10,017 | 2,475 |
| Qwen3.5-9B | validate_domain | numeric | 10 | 0.71 [0.57, 0.93] | 0.46 [0.35, 0.64] | 0.35 [0.26, 0.51] | 0.29 [0.22, 0.43] | 0.25 [0.19, 0.37] | 9,990 | 2,335 |
| Qwen3.5-9B | validate_domain | all | 20 | 1.09 [0.71, 1.68] | 0.70 [0.45, 1.11] | 0.53 [0.34, 0.85] | 0.44 [0.28, 0.71] | 0.38 [0.25, 0.62] | 10,003 | 2,405 |
| Qwen3.5-9B | validate_problem | classical | 10 | 5.15 [4.06, 6.43] | 4.02 [3.13, 5.05] | 3.40 [2.58, 4.36] | 3.01 [2.24, 3.93] | 2.74 [2.00, 3.64] | 13,499 | 1,886 |
| Qwen3.5-9B | validate_problem | numeric | 10 | 4.17 [3.14, 5.36] | 3.13 [2.23, 4.20] | 2.59 [1.80, 3.59] | 2.27 [1.55, 3.20] | 2.06 [1.38, 2.94] | 13,037 | 2,292 |
| Qwen3.5-9B | validate_problem | all | 20 | 4.61 [3.81, 5.51] | 3.52 [2.81, 4.30] | 2.94 [2.30, 3.66] | 2.59 [1.99, 3.26] | 2.35 [1.79, 2.99] | 13,268 | 2,089 |
| Qwen3.5-9B | validate_plan | classical | 10 | 3.57 [2.70, 5.13] | 2.48 [1.87, 3.57] | 1.98 [1.49, 2.85] | 1.69 [1.26, 2.45] | 1.50 [1.12, 2.19] | 14,190 | 3,238 |
| Qwen3.5-9B | validate_plan | numeric | 10 | 3.92 [3.22, 4.88] | 2.80 [2.25, 3.55] | 2.27 [1.80, 2.90] | 1.96 [1.54, 2.53] | 1.75 [1.37, 2.27] | 14,066 | 3,044 |
| Qwen3.5-9B | validate_plan | all | 20 | 3.74 [3.12, 4.59] | 2.63 [2.18, 3.26] | 2.11 [1.74, 2.64] | 1.81 [1.49, 2.28] | 1.62 [1.33, 2.04] | 14,128 | 3,141 |
| Qwen3.5-9B | simulate | classical | 10 | 5.66 [2.25, 15.26] (18 draws dropped) | 3.71 [1.48, 9.99] (18 draws dropped) | 2.88 [1.15, 7.75] (18 draws dropped) | 2.41 [0.97, 6.51] (18 draws dropped) | 2.12 [0.85, 5.72] (18 draws dropped) | 29,033 | 4,234 |
| Qwen3.5-9B | simulate | numeric | 10 | 1.49 [0.23, 3.04] (278 draws dropped) | 0.97 [0.15, 1.99] (278 draws dropped) | 0.75 [0.12, 1.57] (278 draws dropped) | 0.64 [0.10, 1.33] (278 draws dropped) | 0.56 [0.09, 1.18] (278 draws dropped) | 21,575 | 5,024 |
| Qwen3.5-9B | simulate | all | 20 | 3.12 [1.44, 6.06] | 2.04 [0.94, 3.95] | 1.58 [0.73, 3.06] | 1.33 [0.61, 2.57] | 1.17 [0.54, 2.27] | 25,304 | 4,629 |
| Qwen3.6-35B | solve | classical | 10 | 0.82 [0.44, 1.25] | 0.54 [0.29, 0.83] | 0.43 [0.23, 0.66] | 0.37 [0.19, 0.56] | 0.33 [0.17, 0.51] | 24,354 | 4,546 |
| Qwen3.6-35B | solve | numeric | 10 | 2.83 [1.54, 4.87] | 1.84 [1.00, 3.20] | 1.44 [0.78, 2.50] | 1.22 [0.66, 2.12] | 1.09 [0.59, 1.88] | 28,657 | 4,454 |
| Qwen3.6-35B | solve | all | 20 | 1.71 [1.02, 2.71] | 1.12 [0.67, 1.78] | 0.88 [0.52, 1.40] | 0.75 [0.45, 1.19] | 0.67 [0.40, 1.06] | 26,505 | 4,500 |
| Qwen3.6-35B | validate_domain | classical | 10 | 4.48 [4.10, 4.99] | 3.02 [2.75, 3.33] | 2.36 [2.12, 2.61] | 1.98 [1.76, 2.20] | 1.73 [1.53, 1.94] | 10,023 | 1,987 |
| Qwen3.6-35B | validate_domain | numeric | 10 | 2.99 [2.23, 3.84] | 1.95 [1.42, 2.55] | 1.49 [1.07, 1.97] | 1.24 [0.88, 1.65] | 1.08 [0.76, 1.44] | 9,986 | 2,172 |
| Qwen3.6-35B | validate_domain | all | 20 | 3.70 [3.11, 4.27] | 2.45 [2.03, 2.86] | 1.89 [1.56, 2.23] | 1.58 [1.29, 1.87] | 1.38 [1.12, 1.64] | 10,004 | 2,080 |
| Qwen3.6-35B | validate_problem | classical | 10 | 3.98 [3.23, 4.88] | 2.93 [2.39, 3.53] | 2.40 [1.95, 2.88] | 2.08 [1.69, 2.50] | 1.86 [1.51, 2.24] | 11,310 | 2,142 |
| Qwen3.6-35B | validate_problem | numeric | 10 | 4.22 [3.99, 4.48] | 3.22 [2.94, 3.51] | 2.68 [2.41, 2.98] | 2.35 [2.08, 2.65] | 2.13 [1.87, 2.42] | 11,576 | 2,136 |
| Qwen3.6-35B | validate_problem | all | 20 | 4.10 [3.67, 4.55] | 3.07 [2.73, 3.41] | 2.54 [2.25, 2.83] | 2.21 [1.96, 2.48] | 1.99 [1.76, 2.24] | 11,443 | 2,139 |
| Qwen3.6-35B | validate_plan | classical | 10 | 3.53 [2.94, 4.32] | 2.40 [1.98, 2.92] | 1.89 [1.56, 2.30] | 1.61 [1.33, 1.95] | 1.43 [1.17, 1.73] | 13,298 | 3,517 |
| Qwen3.6-35B | validate_plan | numeric | 10 | 3.91 [3.50, 4.42] | 2.74 [2.42, 3.13] | 2.19 [1.92, 2.52] | 1.88 [1.64, 2.16] | 1.67 [1.45, 1.93] | 14,043 | 3,229 |
| Qwen3.6-35B | validate_plan | all | 20 | 3.72 [3.31, 4.18] | 2.56 [2.26, 2.90] | 2.04 [1.79, 2.31] | 1.73 [1.53, 1.97] | 1.54 [1.35, 1.75] | 13,670 | 3,373 |
| Qwen3.6-35B | simulate | classical | 10 | 3.83 [2.10, 5.66] | 2.54 [1.41, 3.75] | 1.98 [1.10, 2.91] | 1.66 [0.93, 2.44] | 1.45 [0.82, 2.14] | 21,576 | 3,854 |
| Qwen3.6-35B | simulate | numeric | 10 | 3.40 [2.02, 5.84] | 2.24 [1.33, 3.83] | 1.75 [1.04, 2.99] | 1.48 [0.87, 2.52] | 1.30 [0.76, 2.23] | 22,006 | 4,483 |
| Qwen3.6-35B | simulate | all | 20 | 3.60 [2.53, 4.96] | 2.38 [1.68, 3.27] | 1.85 [1.31, 2.55] | 1.56 [1.10, 2.14] | 1.37 [0.97, 1.89] | 21,791 | 4,169 |
| pooled (3 models) | solve | classical | 10 | 0.61 [0.28, 1.04] | 0.39 [0.18, 0.67] | 0.31 [0.14, 0.52] | 0.26 [0.12, 0.44] | 0.23 [0.11, 0.39] | 17,983 | 4,740 |
| pooled (3 models) | solve | numeric | 10 | 2.41 [1.44, 3.75] | 1.59 [0.94, 2.51] | 1.25 [0.73, 1.98] | 1.06 [0.62, 1.68] | 0.94 [0.55, 1.49] | 26,764 | 4,123 |
| pooled (3 models) | solve | all | 20 | 1.32 [0.80, 2.06] | 0.86 [0.51, 1.35] | 0.67 [0.40, 1.06] | 0.57 [0.34, 0.90] | 0.51 [0.31, 0.80] | 22,374 | 4,431 |
| pooled (3 models) | validate_domain | classical | 10 | 3.54 [3.04, 4.37] | 2.41 [2.04, 3.00] | 1.89 [1.58, 2.37] | 1.59 [1.31, 2.01] | 1.40 [1.14, 1.77] | 9,684 | 1,966 |
| pooled (3 models) | validate_domain | numeric | 10 | 2.46 [1.97, 2.96] | 1.66 [1.32, 2.00] | 1.29 [1.02, 1.56] | 1.08 [0.85, 1.31] | 0.95 [0.74, 1.15] | 9,669 | 1,968 |
| pooled (3 models) | validate_domain | all | 20 | 3.00 [2.57, 3.51] | 2.03 [1.74, 2.39] | 1.59 [1.35, 1.88] | 1.33 [1.13, 1.58] | 1.17 [0.99, 1.39] | 9,677 | 1,967 |
| pooled (3 models) | validate_problem | classical | 10 | 4.47 [3.74, 5.28] | 3.44 [2.95, 3.93] | 2.89 [2.51, 3.25] | 2.54 [2.22, 2.85] | 2.31 [2.02, 2.58] | 11,767 | 1,957 |
| pooled (3 models) | validate_problem | numeric | 10 | 4.32 [3.83, 4.85] | 3.35 [2.86, 3.87] | 2.83 [2.36, 3.33] | 2.50 [2.05, 2.99] | 2.28 [1.85, 2.75] | 11,901 | 2,104 |
| pooled (3 models) | validate_problem | all | 20 | 4.39 [3.96, 4.85] | 3.39 [3.05, 3.75] | 2.86 [2.55, 3.17] | 2.52 [2.23, 2.81] | 2.29 [2.02, 2.56] | 11,834 | 2,031 |
| pooled (3 models) | validate_plan | classical | 10 | 3.65 [2.99, 4.63] | 2.58 [2.13, 3.24] | 2.08 [1.72, 2.60] | 1.79 [1.48, 2.23] | 1.60 [1.33, 1.99] | 12,749 | 3,110 |
| pooled (3 models) | validate_plan | numeric | 10 | 4.12 [3.61, 4.73] | 3.00 [2.59, 3.49] | 2.46 [2.10, 2.88] | 2.13 [1.81, 2.51] | 1.92 [1.62, 2.26] | 13,598 | 2,925 |
| pooled (3 models) | validate_plan | all | 20 | 3.88 [3.41, 4.44] | 2.78 [2.44, 3.18] | 2.26 [1.98, 2.59] | 1.95 [1.71, 2.24] | 1.75 [1.53, 2.01] | 13,173 | 3,018 |
| pooled (3 models) | simulate | classical | 10 | 5.39 [3.02, 9.27] | 3.54 [2.00, 6.04] | 2.75 [1.57, 4.66] | 2.30 [1.32, 3.91] | 2.02 [1.16, 3.42] | 24,167 | 4,179 |
| pooled (3 models) | simulate | numeric | 10 | 4.90 [3.33, 8.05] | 3.21 [2.19, 5.23] | 2.50 [1.71, 4.05] | 2.12 [1.44, 3.42] | 1.87 [1.27, 3.02] | 22,065 | 4,917 |
| pooled (3 models) | simulate | all | 20 | 5.15 [3.77, 7.29] | 3.38 [2.48, 4.75] | 2.62 [1.93, 3.69] | 2.21 [1.63, 3.09] | 1.95 [1.43, 2.72] | 23,116 | 4,548 |

#### S2-E. Delivery gap: frozen E4 categories beside the hand reads

Gap rows = the tool returned the right result but the delivered answer is graded wrong (readout E4). *E4 frozen* = the readout's mechanical category (the record). *Hand read* = the category two independent readers and a third reading gave the NEEDS_READING rows (`reference/delivered_rerun_secondary/hand_reads/`). *Folded* = E4 with each NEEDS_READING row moved to its hand-read category: **descriptive, not a registered reading**. *Right to a reader* = hand-read rows a human reader judges right.

| task | gap rows | category | E4 frozen (record) | hand read | folded (descriptive) | right to a reader |
|---|---|---|---|---|---|---|
| solve | 169 | ABRIDGED | 10 |  | 10 |  |
| solve | 169 | NEEDS_READING | 2 |  | 0 |  |
| solve | 169 | REFUSED_OR_CLIPPED_FINAL | 104 |  | 104 |  |
| solve | 169 | SUMMARY_ONLY | 6 | 1 | 7 |  |
| solve | 169 | WRONG_FACTS | 38 |  | 38 |  |
| solve | 169 | WRONG_WRAPPER | 9 | 1 | 10 | 1 |
| validate_problem | 14 | NEEDS_READING | 10 |  | 0 |  |
| validate_problem | 14 | SUMMARY_ONLY | 0 | 10 | 10 |  |
| validate_problem | 14 | WRONG_FACTS | 4 |  | 4 |  |
| validate_plan | 62 | NEEDS_READING | 34 |  | 0 |  |
| validate_plan | 62 | NO_FINAL_ANSWER | 1 | 1 | 2 |  |
| validate_plan | 62 | REFUSED_OR_CLIPPED_FINAL | 22 |  | 22 |  |
| validate_plan | 62 | SUMMARY_ONLY | 0 | 8 | 8 |  |
| validate_plan | 62 | WRONG_FACTS | 5 |  | 5 |  |
| validate_plan | 62 | WRONG_WRAPPER | 0 | 25 | 25 | 25 |
| simulate | 1266 | ABRIDGED | 2 | 7 | 9 | 4 |
| simulate | 1266 | NEEDS_READING | 244 |  | 0 |  |
| simulate | 1266 | NUMERIC_OMITTED | 17 | 40 | 57 | 2 |
| simulate | 1266 | REFUSED_OR_CLIPPED_FINAL | 843 |  | 843 |  |
| simulate | 1266 | WRONG_FACTS | 160 | 5 | 165 |  |
| simulate | 1266 | WRONG_WRAPPER | 0 | 192 | 192 | 148 |
| all | 1511 | ABRIDGED | 12 | 7 | 19 | 4 |
| all | 1511 | NEEDS_READING | 290 |  | 0 |  |
| all | 1511 | NO_FINAL_ANSWER | 1 | 1 | 2 |  |
| all | 1511 | NUMERIC_OMITTED | 17 | 40 | 57 | 2 |
| all | 1511 | REFUSED_OR_CLIPPED_FINAL | 969 |  | 969 |  |
| all | 1511 | SUMMARY_ONLY | 6 | 19 | 25 |  |
| all | 1511 | WRONG_FACTS | 207 | 5 | 212 |  |
| all | 1511 | WRONG_WRAPPER | 9 | 218 | 227 | 174 |
<!-- END GENERATED: s2_gen_md.py -->

Solve WRONG_FACTS in S2-E: most of these rows are a correct plan followed by the goal facts, not copying errors. The split is the post hoc ISS-028 line under "Delivered rerun — readout" above; the frozen E4 column stays the record.

## RQ1 metrics — the advisors' four metrics (added 2026-11-22; post hoc, exploratory; in no tex yet)

The metrics set at the advisor meeting of 2026-11-22 (`roadmap.md` §2), computed on data
already on disk by `tools/reanalysis/rq1_metrics.py` (rerun: `python -m tools.reanalysis.rq1_metrics --numbers`;
tests in `tests/test_rq1_metrics.py`). How to read the block:

- **Not a registered endpoint.** The frozen readout of the delivered rerun stays the record.
  These are new views of the same graded answers. The script halts unless the frozen
  package hash, the pinned ground-truth cache and the readout's E1 and E2 delivered counts
  all reproduce, so every table sits on the readout's exact grades.
- **Delivered answers only**, from the two sources that stored them in full: the delivered
  rerun (three open models, thinking off) and the Claude runs (wording v11 in both arms).
  The main sweep is not used (500-character answers). Open models and Claude are never pooled.
- **Frozen grades.** The corrections of ISS-027 (plan-name case) and ISS-028 (a correct plan
  followed by the goal facts) are not applied here; they lower some solve cells slightly
  (the corrected figures are the ISS-027 and ISS-028 post hoc lines elsewhere in this file,
  from PRs #130 and #136, merged 2026-11-22).
- **The unaided arm asks for its answer format in the prompt only** (JSON on solve and
  simulate, a verdict line on the validation tasks). The JSON-schema constraint meant for
  that arm never took effect, in the main sweep or in the rerun (13,446 of the rerun's
  13,680 unaided answers do not begin with `{`; `reference/weakness_consolidated.md`, the
  Q3 note). So an unaided failure can be a failure of format as well as of content, and
  what a working constraint would have produced is unmeasured. *Corrected 2026-11-22: this
  bullet first said the unaided answers were sampled under the constraint, which is the
  frozen readout's false sentence.*
- **Simulate:** six problems are left out because the run's plan was not the cached plan
  (ISS-029; the script finds the same six as the record). "States, salvaged" is more
  lenient than the frozen grader. Claude answers were stored up to 16,384 characters, so
  a Claude trace cut by storage scores lower than what the model wrote.
- **Planner runtime** is the `solve_time` the solver plugin returns with each plan, as
  measured during the runs on the cluster. It spans 0.15 s to 22.3 s with two thirds of
  the problems under 0.32 s, so on this corpus it separates problems far less than plan
  length does.

<!-- BEGIN GENERATED: RQ1-METRICS (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/rq1_metrics.py`. Post hoc and descriptive; delivered final answers only. Open models: the delivered rerun (thinking off; no tools = Part C, tools = Part A), graded by the frozen package. Claude: the frontier runs, wording v11, never pooled with the open models. Intervals are 95% domain-cluster bootstrap percentile intervals, in percent (or points for differences). The no-tools arm asks for its answer format in the prompt only (JSON on solve and simulate, a verdict line on the validation tasks); the JSON-schema constraint meant for that arm never took effect, so an unaided failure can be a failure of format as well as of content.*

#### RQ1-1. validate_plan: false positives and false negatives

FN = a valid plan rejected (share of valid plans). FP = a broken plan accepted (share of broken plans). "No verdict" = the final answer states no readable verdict; it is counted in neither rate.

| model | arm | valid plans | FN | FN rate | no verdict | broken plans | FP | FP rate | no verdict | verdict right |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 500 | 31 | 6.2 [2.6, 10.2] | 0 | 500 | 54 | 10.8 [6.0, 16.4] | 0 | 91.5 [87.9, 94.7] |
| Claude Haiku 4.5 | tools | 500 | 10 | 2.0 [0.0, 5.0] | 0 | 500 | 2 | 0.4 [0.0, 1.0] | 0 | 98.8 [97.3, 99.9] |
| Claude Sonnet 4.6 | no tools | 500 | 8 | 1.6 [0.0, 4.0] | 0 | 500 | 21 | 4.2 [1.6, 7.2] | 0 | 97.1 [95.5, 98.5] |
| Claude Sonnet 4.6 | tools | 500 | 0 | 0.0 [0.0, 0.0] | 0 | 500 | 0 | 0.0 [0.0, 0.0] | 0 | 100.0 [100.0, 100.0] |
| Gemma-26B | no tools | 1500 | 205 | 13.7 [8.1, 19.9] | 6 | 1500 | 135 | 9.0 [6.1, 12.2] | 5 | 88.3 [84.1, 92.0] |
| Gemma-26B | tools, plain | 1500 | 155 | 10.3 [6.1, 14.9] | 9 | 1500 | 147 | 9.8 [5.6, 14.7] | 14 | 89.2 [84.6, 93.1] |
| Gemma-26B | tools, steered | 1500 | 42 | 2.8 [0.4, 6.2] | 9 | 1500 | 43 | 2.9 [0.9, 5.7] | 7 | 96.6 [93.1, 98.9] |
| Qwen3.5-9B | no tools | 1500 | 386 | 25.7 [15.4, 36.6] | 26 | 1500 | 166 | 11.1 [7.3, 15.1] | 28 | 79.8 [74.0, 85.5] |
| Qwen3.5-9B | tools, plain | 1500 | 85 | 5.7 [1.9, 10.5] | 42 | 1500 | 26 | 1.7 [0.0, 5.1] | 26 | 94.0 [89.4, 97.6] |
| Qwen3.5-9B | tools, steered | 1500 | 61 | 4.1 [1.1, 7.6] | 19 | 1500 | 28 | 1.9 [0.0, 5.5] | 14 | 95.9 [92.1, 98.8] |
| Qwen3.6-35B | no tools | 1500 | 127 | 8.5 [3.8, 13.6] | 27 | 1500 | 117 | 7.8 [5.3, 10.3] | 16 | 90.4 [87.3, 93.3] |
| Qwen3.6-35B | tools, plain | 1500 | 14 | 0.9 [0.1, 2.1] | 16 | 1500 | 33 | 2.2 [1.0, 3.5] | 2 | 97.8 [96.7, 98.9] |
| Qwen3.6-35B | tools, steered | 1500 | 11 | 0.7 [0.0, 1.7] | 14 | 1500 | 13 | 0.9 [0.2, 1.9] | 3 | 98.6 [97.8, 99.4] |

Paired change, tools minus no tools, on the same plan and wording (points; negative = fewer errors with tools):

| model | tool arm | error | pairs | change |
|---|---|---|---|---|
| Claude Haiku 4.5 | tools | FN | 500 | -4.2 [-8.2, -0.2] |
| Claude Haiku 4.5 | tools | FP | 500 | -10.4 [-16.2, -5.6] |
| Claude Sonnet 4.6 | tools | FN | 500 | -1.6 [-4.0, +0.0] |
| Claude Sonnet 4.6 | tools | FP | 500 | -4.2 [-7.2, -1.6] |
| Gemma-26B | tools, plain | FN | 1500 | -3.3 [-7.2, +0.3] |
| Gemma-26B | tools, plain | FP | 1500 | +0.8 [-1.6, +3.3] |
| Qwen3.5-9B | tools, plain | FN | 1500 | -20.1 [-31.6, -9.3] |
| Qwen3.5-9B | tools, plain | FP | 1500 | -9.3 [-14.6, -3.5] |
| Qwen3.6-35B | tools, plain | FN | 1500 | -7.5 [-12.4, -3.3] |
| Qwen3.6-35B | tools, plain | FP | 1500 | -5.6 [-8.2, -3.1] |

False positives by broken-plan label (accepted / shown):

| model | arm | b1 | b2 | b3 | b4 | b5 |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 8/100 | 4/100 | 7/100 | 15/100 | 20/100 |
| Claude Haiku 4.5 | tools | 0/100 | 0/100 | 0/100 | 0/100 | 2/100 |
| Claude Sonnet 4.6 | no tools | 0/100 | 2/100 | 3/100 | 3/100 | 13/100 |
| Claude Sonnet 4.6 | tools | 0/100 | 0/100 | 0/100 | 0/100 | 0/100 |
| Gemma-26B | no tools | 8/300 | 17/300 | 14/300 | 33/300 | 63/300 |
| Gemma-26B | tools, plain | 10/300 | 21/300 | 22/300 | 37/300 | 57/300 |
| Gemma-26B | tools, steered | 7/300 | 6/300 | 3/300 | 15/300 | 12/300 |
| Qwen3.5-9B | no tools | 28/300 | 26/300 | 19/300 | 34/300 | 59/300 |
| Qwen3.5-9B | tools, plain | 6/300 | 8/300 | 5/300 | 4/300 | 3/300 |
| Qwen3.5-9B | tools, steered | 6/300 | 9/300 | 3/300 | 6/300 | 4/300 |
| Qwen3.6-35B | no tools | 7/300 | 14/300 | 10/300 | 34/300 | 52/300 |
| Qwen3.6-35B | tools, plain | 5/300 | 1/300 | 1/300 | 5/300 | 21/300 |
| Qwen3.6-35B | tools, steered | 5/300 | 1/300 | 0/300 | 1/300 | 6/300 |

#### RQ1-2. simulate: share of states right, against trace length

"Exact" = the whole trace equals the oracle (the frozen grade). "States" = mean share of the oracle's states that the answer has right at the same position. "Prefix" = mean share of the trace that is right before the first wrong state. "No trace" = answers with no readable trace (they score 0 on all three). "States, salvaged" = the same as "states", but for an answer cut off mid-trace the complete leading steps are read too ("salvaged" counts those answers); it is more lenient than the frozen grader. Trace length = number of actions. Left out (ISS-029, the run's plan is not the cached plan): barman/p01, barman/p02, barman/p03, barman/p04, barman/p05, gripper/p03. Run plan undetermined (kept): block-grouping/p01, block-grouping/p02, counters/p01, counters/p02, counters/p03, counters/p05, drone/p04, drone/p05, gardening/p03, pogo_stick/p02, sailing/p01.

| model | arm | trials | exact | states | prefix | no trace | states, salvaged | salvaged | Spearman, states vs length |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 94 | 40.4 [24.2, 57.8] ‡26 | 46.9 [29.5, 63.8] | 44.2 [27.1, 61.2] | 34 | 62.2 [46.4, 77.4] | 34 | -0.48 (p=0.000) |
| Claude Haiku 4.5 | tools | 94 | 54.3 [41.1, 67.7] ‡10 | 60.9 [47.8, 73.5] | 56.8 [43.4, 69.9] | 31 | 72.4 [60.9, 83.3] | 21 | -0.65 (p=0.000) |
| Claude Sonnet 4.6 | no tools | 94 | 35.1 [20.2, 51.1] ‡15 | 36.7 [22.0, 52.9] | 36.0 [21.3, 52.1] | 57 | 77.7 [64.9, 88.6] | 57 | -0.58 (p=0.000) |
| Claude Sonnet 4.6 | tools | 94 | 51.1 [37.9, 64.5] ‡9 | 58.5 [48.3, 69.6] | 58.5 [48.3, 69.6] | 23 | 59.8 [49.3, 71.1] | 5 | -0.52 (p=0.000) |
| Gemma-26B | no tools | 282 | 25.5 [14.9, 36.5] | 32.5 [22.0, 42.9] | 30.0 [19.8, 40.4] | 143 | 36.9 [25.7, 48.0] | 41 | -0.26 (p=0.000) |
| Gemma-26B | tools, plain | 282 | 8.9 [4.6, 14.2] | 11.0 [6.6, 16.1] | 10.1 [5.7, 15.3] | 238 | 12.2 [7.6, 17.2] | 10 | -0.34 (p=0.000) |
| Gemma-26B | tools, steered | 282 | 8.9 [4.6, 13.7] | 11.4 [6.6, 16.7] | 10.2 [5.6, 15.2] | 238 | 12.6 [7.9, 17.8] | 11 | -0.38 (p=0.000) |
| Qwen3.5-9B | no tools | 282 | 9.9 [4.2, 16.7] | 18.5 [10.9, 27.1] | 17.2 [10.2, 25.3] | 94 | 21.7 [14.1, 30.0] | 58 | -0.52 (p=0.000) |
| Qwen3.5-9B | tools, plain | 282 | 18.4 [8.9, 29.1] | 24.3 [14.6, 34.9] | 22.4 [13.2, 32.6] | 166 | 24.7 [14.9, 35.3] | 4 | -0.55 (p=0.000) |
| Qwen3.5-9B | tools, steered | 282 | 17.4 [8.9, 27.4] | 22.1 [13.4, 32.4] | 20.3 [11.7, 30.6] | 188 | 22.4 [13.5, 32.8] | 2 | -0.58 (p=0.000) |
| Qwen3.6-35B | no tools | 282 | 18.8 [11.2, 27.3] | 24.9 [17.3, 33.2] | 24.2 [16.5, 32.4] | 102 | 29.5 [21.7, 37.8] | 31 | -0.23 (p=0.000) |
| Qwen3.6-35B | tools, plain | 282 | 30.1 [18.1, 43.7] | 36.7 [24.5, 50.0] | 35.7 [23.5, 48.8] | 152 | 38.5 [26.3, 51.4] | 8 | -0.73 (p=0.000) |
| Qwen3.6-35B | tools, steered | 282 | 27.3 [16.5, 39.4] | 33.0 [21.4, 45.4] | 32.2 [20.5, 44.6] | 168 | 34.1 [22.8, 46.3] | 6 | -0.70 (p=0.000) |

States are compared position by position. Moving the answer by one position would match more states in 7 of the 641 readable answers that are not exact, so an off-by-one trace is not what drives these scores.

‡ n = Claude answers cut at the storage cap, exact grade unknown (counted as not exact here; their states are scored on what was stored).

Mean share by trace length, "states" (trials in the bin):

| model | arm | 1–5 actions | 6–10 actions | 11–20 actions | 21–40 actions | 41+ actions |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 59.9 [29.3, 90.7] (21) | 75.2 [51.8, 91.1] (27) | 37.8 [17.4, 63.2] (19) | 17.6 [0.0, 41.2] (17) | 10.0 [0.0, 23.1] (10) |
| Claude Haiku 4.5 | tools | 94.9 [87.1, 100.0] (21) | 90.4 [79.3, 98.6] (27) | 46.7 [22.2, 77.1] (19) | 17.9 [0.0, 41.2] (17) | 10.0 [0.0, 23.1] (10) |
| Claude Sonnet 4.6 | no tools | 60.3 [30.8, 96.1] (21) | 73.6 [49.5, 92.4] (27) | 10.5 [0.0, 29.4] (19) | 0.0 [0.0, 0.0] (17) | 0.0 [0.0, 0.0] (10) |
| Claude Sonnet 4.6 | tools | 76.2 [52.6, 100.0] (21) | 81.9 [64.7, 96.3] (27) | 65.8 [49.6, 82.9] (19) | 22.8 [5.8, 41.6] (17) | 4.9 [0.0, 12.2] (10) |
| Gemma-26B | no tools | 41.6 [21.6, 59.4] (63) | 44.7 [28.5, 57.9] (81) | 29.2 [18.6, 40.7] (57) | 20.5 [1.9, 42.0] (51) | 6.7 [0.0, 15.4] (30) |
| Gemma-26B | tools, plain | 24.5 [14.1, 36.4] (63) | 18.1 [8.5, 27.5] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Gemma-26B | tools, steered | 28.3 [17.3, 36.9] (63) | 16.5 [8.3, 24.1] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.5-9B | no tools | 29.1 [18.7, 43.2] (63) | 34.4 [20.0, 44.2] (81) | 6.6 [2.2, 13.9] (57) | 2.6 [0.4, 7.7] (51) | 3.0 [0.0, 6.9] (30) |
| Qwen3.5-9B | tools, plain | 56.7 [41.0, 72.5] (63) | 37.2 [19.5, 54.6] (81) | 3.9 [0.9, 8.2] (57) | 1.1 [0.4, 2.0] (51) | 0.1 [0.0, 0.3] (30) |
| Qwen3.5-9B | tools, steered | 47.8 [36.6, 60.5] (63) | 38.2 [19.5, 56.8] (81) | 2.2 [0.0, 6.7] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | no tools | 31.2 [15.6, 47.6] (63) | 41.2 [27.3, 53.0] (81) | 20.2 [11.2, 32.5] (57) | 11.0 [1.5, 21.3] (51) | 0.5 [0.1, 0.8] (30) |
| Qwen3.6-35B | tools, plain | 82.9 [72.1, 91.2] (63) | 58.9 [36.9, 77.9] (81) | 2.5 [0.0, 7.1] (57) | 4.3 [0.0, 12.2] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | tools, steered | 78.1 [67.4, 88.4] (63) | 50.8 [33.2, 65.5] (81) | 4.6 [0.5, 10.5] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |

Mean share by trace length, "states, salvaged" (trials in the bin):

| model | arm | 1–5 actions | 6–10 actions | 11–20 actions | 21–40 actions | 41+ actions |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 59.9 [29.3, 90.7] (21) | 82.0 [63.8, 93.9] (27) | 67.5 [55.4, 78.8] (19) | 43.8 [22.7, 66.6] (17) | 34.4 [3.7, 62.3] (10) |
| Claude Haiku 4.5 | tools | 94.9 [87.1, 100.0] (21) | 90.4 [79.3, 98.6] (27) | 75.9 [61.4, 89.7] (19) | 40.5 [14.5, 68.7] (17) | 24.2 [4.4, 47.7] (10) |
| Claude Sonnet 4.6 | no tools | 79.4 [48.6, 100.0] (21) | 95.2 [85.1, 100.0] (27) | 85.9 [76.7, 96.0] (19) | 56.3 [36.4, 77.8] (17) | 47.5 [15.4, 77.0] (10) |
| Claude Sonnet 4.6 | tools | 76.2 [52.6, 100.0] (21) | 81.9 [64.7, 96.3] (27) | 65.8 [49.6, 82.9] (19) | 27.9 [7.7, 47.6] (17) | 8.7 [1.5, 20.7] (10) |
| Gemma-26B | no tools | 41.9 [21.9, 59.5] (63) | 44.7 [28.5, 57.9] (81) | 37.1 [24.5, 49.3] (57) | 25.8 [9.0, 45.9] (51) | 23.8 [4.4, 44.3] (30) |
| Gemma-26B | tools, plain | 25.1 [14.7, 36.5] (63) | 18.5 [8.9, 27.8] (81) | 3.6 [0.0, 9.3] (57) | 3.1 [0.0, 8.8] (51) | 0.0 [0.0, 0.0] (30) |
| Gemma-26B | tools, steered | 29.2 [19.9, 36.9] (63) | 17.6 [9.4, 24.8] (81) | 3.6 [0.0, 9.3] (57) | 1.9 [0.0, 5.4] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.5-9B | no tools | 29.1 [18.7, 43.2] (63) | 35.2 [21.1, 44.7] (81) | 14.6 [7.4, 21.2] (57) | 6.6 [3.0, 12.3] (51) | 8.9 [0.2, 19.1] (30) |
| Qwen3.5-9B | tools, plain | 56.7 [41.0, 72.5] (63) | 38.1 [21.0, 54.9] (81) | 4.3 [1.0, 9.0] (57) | 1.1 [0.4, 2.0] (51) | 0.1 [0.0, 0.3] (30) |
| Qwen3.5-9B | tools, steered | 47.8 [36.6, 60.5] (63) | 38.9 [20.6, 57.1] (81) | 2.7 [0.0, 7.5] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | no tools | 31.2 [15.6, 47.6] (63) | 41.2 [27.3, 53.0] (81) | 27.9 [19.7, 37.3] (57) | 21.5 [8.9, 37.2] (51) | 11.1 [0.9, 20.8] (30) |
| Qwen3.6-35B | tools, plain | 82.9 [72.1, 91.2] (63) | 60.4 [40.1, 78.2] (81) | 4.7 [0.7, 10.4] (57) | 9.0 [0.0, 21.8] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | tools, steered | 78.1 [67.4, 88.4] (63) | 51.5 [34.1, 65.7] (81) | 5.3 [0.9, 11.5] (57) | 4.5 [0.0, 10.1] (51) | 0.0 [0.0, 0.0] (30) |

Mean share by trace length, "exact" (trials in the bin):

| model | arm | 1–5 actions | 6–10 actions | 11–20 actions | 21–40 actions | 41+ actions |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 52.4 [20.8, 84.2] (21) | 66.7 [39.1, 87.0] (27) | 26.3 [9.1, 47.4] (19) | 17.6 [0.0, 41.2] (17) | 10.0 [0.0, 23.1] (10) |
| Claude Haiku 4.5 | tools | 81.0 [58.3, 100.0] (21) | 81.5 [63.2, 94.1] (27) | 42.1 [17.6, 70.6] (19) | 17.6 [0.0, 41.2] (17) | 10.0 [0.0, 23.1] (10) |
| Claude Sonnet 4.6 | no tools | 57.1 [29.2, 93.8] (21) | 70.4 [45.0, 90.0] (27) | 10.5 [0.0, 29.4] (19) | 0.0 [0.0, 0.0] (17) | 0.0 [0.0, 0.0] (10) |
| Claude Sonnet 4.6 | tools | 76.2 [52.6, 100.0] (21) | 81.5 [63.6, 96.3] (27) | 42.1 [17.6, 72.2] (19) | 11.8 [0.0, 27.8] (17) | 0.0 [0.0, 0.0] (10) |
| Gemma-26B | no tools | 36.5 [16.7, 55.1] (63) | 34.6 [17.9, 50.7] (81) | 17.5 [5.6, 30.3] (57) | 19.6 [0.0, 41.7] (51) | 3.3 [0.0, 7.7] (30) |
| Gemma-26B | tools, plain | 17.5 [8.7, 27.5] (63) | 16.0 [5.8, 26.2] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Gemma-26B | tools, steered | 20.6 [11.8, 28.4] (63) | 13.6 [4.3, 22.2] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.5-9B | no tools | 15.9 [4.8, 30.0] (63) | 19.8 [7.9, 28.1] (81) | 3.5 [0.0, 11.1] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.5-9B | tools, plain | 47.6 [24.6, 69.8] (63) | 25.9 [8.0, 45.2] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.5-9B | tools, steered | 38.1 [20.5, 57.4] (63) | 29.6 [10.1, 49.4] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | no tools | 25.4 [12.1, 39.4] (63) | 33.3 [16.7, 47.5] (81) | 12.3 [3.7, 24.1] (57) | 5.9 [0.0, 16.7] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | tools, plain | 71.4 [56.1, 85.2] (63) | 48.1 [21.8, 71.3] (81) | 1.8 [0.0, 6.2] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |
| Qwen3.6-35B | tools, steered | 68.3 [52.4, 85.2] (63) | 39.5 [17.3, 58.6] (81) | 3.5 [0.0, 9.5] (57) | 0.0 [0.0, 0.0] (51) | 0.0 [0.0, 0.0] (30) |

#### RQ1-3. solve: delivered success against problem hardness

Hardness 1: reference plan length (actions). Hardness 2: the planner's own runtime, the median `solve_time` over the planner calls the rerun models made on the problem (100 problems timed, 0.15 s to 22.30 s; thirds cut at 0.20 s and 0.32 s). Plan length and planner runtime: Spearman +0.52 (p=0.000). Second view: the number of objects in the problem (2 to 35; thirds cut at 6 and 14); plan length and object count: Spearman +0.38 (p=0.000). The planner solves every problem in this corpus, so the hard end, where the planner itself fails, is not covered.

| model | arm | solved | Spearman, solved vs plan length | Spearman, solved vs planner runtime | Spearman, solved vs object count |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 22.0 [9.0, 37.0] | -0.33 (p=0.001) | -0.32 (p=0.001) | -0.24 (p=0.015) |
| Claude Haiku 4.5 | tools | 95.0 [90.0, 99.0] | +0.03 (p=0.765) | -0.12 (p=0.241) | -0.02 (p=0.844) |
| Claude Sonnet 4.6 | no tools | 29.0 [17.0, 42.0] | -0.54 (p=0.000) | -0.32 (p=0.001) | -0.42 (p=0.000) |
| Claude Sonnet 4.6 | tools | 95.0 [91.0, 98.0] | -0.25 (p=0.012) | -0.17 (p=0.099) | -0.01 (p=0.937) |
| Gemma-26B | no tools | 21.3 [13.0, 30.3] | -0.32 (p=0.001) | -0.11 (p=0.288) | -0.39 (p=0.000) |
| Gemma-26B | tools, plain | 92.3 [87.3, 97.0] | -0.44 (p=0.000) | -0.46 (p=0.000) | -0.40 (p=0.000) |
| Gemma-26B | tools, steered | 95.3 [91.3, 98.7] | -0.40 (p=0.000) | -0.33 (p=0.001) | -0.13 (p=0.189) |
| Qwen3.5-9B | no tools | 24.3 [16.3, 32.3] | -0.29 (p=0.003) | -0.02 (p=0.832) | -0.47 (p=0.000) |
| Qwen3.5-9B | tools, plain | 88.7 [82.0, 94.7] | -0.56 (p=0.000) | -0.29 (p=0.003) | -0.08 (p=0.449) |
| Qwen3.5-9B | tools, steered | 89.0 [82.7, 94.3] | -0.53 (p=0.000) | -0.21 (p=0.034) | -0.07 (p=0.484) |
| Qwen3.6-35B | no tools | 25.3 [16.3, 35.7] | -0.34 (p=0.000) | +0.03 (p=0.738) | -0.42 (p=0.000) |
| Qwen3.6-35B | tools, plain | 77.0 [69.7, 83.7] | -0.34 (p=0.001) | -0.09 (p=0.390) | -0.30 (p=0.003) |
| Qwen3.6-35B | tools, steered | 87.3 [81.7, 92.3] | -0.51 (p=0.000) | -0.30 (p=0.003) | -0.07 (p=0.494) |

Solved, by reference plan length (trials in the bin):

| model | arm | 1–5 | 6–10 | 11–20 | 21–40 | 41+ |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 28.6 [11.1, 56.2] (21) | 40.7 [15.0, 64.0] (27) | 19.0 [0.0, 42.9] (21) | 5.3 [0.0, 16.7] (19) | 0.0 [0.0, 0.0] (12) |
| Claude Haiku 4.5 | tools | 85.7 [68.4, 100.0] (21) | 100.0 [100.0, 100.0] (27) | 100.0 [100.0, 100.0] (21) | 100.0 [100.0, 100.0] (19) | 83.3 [68.8, 100.0] (12) |
| Claude Sonnet 4.6 | no tools | 61.9 [36.7, 88.2] (21) | 48.1 [27.3, 67.7] (27) | 9.5 [0.0, 26.3] (21) | 5.3 [0.0, 16.7] (19) | 0.0 [0.0, 0.0] (12) |
| Claude Sonnet 4.6 | tools | 100.0 [100.0, 100.0] (21) | 100.0 [100.0, 100.0] (27) | 95.2 [83.3, 100.0] (21) | 89.5 [79.2, 100.0] (19) | 83.3 [68.8, 100.0] (12) |
| Gemma-26B | no tools | 38.1 [18.5, 59.3] (63) | 22.2 [9.9, 38.7] (81) | 15.9 [4.9, 31.5] (63) | 14.0 [3.3, 26.3] (57) | 11.1 [0.0, 22.2] (36) |
| Gemma-26B | tools, plain | 100.0 [100.0, 100.0] (63) | 97.5 [91.7, 100.0] (81) | 98.4 [95.0, 100.0] (63) | 91.2 [81.2, 100.0] (57) | 58.3 [41.7, 75.0] (36) |
| Gemma-26B | tools, steered | 100.0 [100.0, 100.0] (63) | 100.0 [100.0, 100.0] (81) | 100.0 [100.0, 100.0] (63) | 96.5 [88.9, 100.0] (57) | 66.7 [48.7, 87.9] (36) |
| Qwen3.5-9B | no tools | 39.7 [19.8, 61.4] (63) | 27.2 [16.7, 37.7] (81) | 19.0 [8.0, 33.3] (63) | 15.8 [4.2, 28.8] (57) | 13.9 [2.6, 25.6] (36) |
| Qwen3.5-9B | tools, plain | 100.0 [100.0, 100.0] (63) | 100.0 [100.0, 100.0] (81) | 98.4 [95.0, 100.0] (63) | 80.7 [68.3, 95.2] (57) | 38.9 [12.8, 66.7] (36) |
| Qwen3.5-9B | tools, steered | 100.0 [100.0, 100.0] (63) | 98.8 [95.8, 100.0] (81) | 95.2 [91.3, 100.0] (63) | 84.2 [73.0, 96.3] (57) | 44.4 [18.2, 71.8] (36) |
| Qwen3.6-35B | no tools | 38.1 [18.8, 60.3] (63) | 32.1 [22.9, 44.4] (81) | 23.8 [12.5, 37.0] (63) | 19.3 [2.0, 41.7] (57) | 0.0 [0.0, 0.0] (36) |
| Qwen3.6-35B | tools, plain | 85.7 [76.2, 95.0] (63) | 88.9 [81.3, 95.1] (81) | 82.5 [63.8, 96.7] (63) | 70.2 [56.1, 85.2] (57) | 36.1 [19.4, 54.5] (36) |
| Qwen3.6-35B | tools, steered | 98.4 [95.8, 100.0] (63) | 93.8 [90.0, 97.5] (81) | 98.4 [95.7, 100.0] (63) | 86.0 [78.3, 93.8] (57) | 36.1 [20.8, 48.9] (36) |

Solved, by planner runtime (trials in the bin):

| model | arm | fast third | middle third | slow third |
|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 38.2 [6.9, 67.4] (34) | 15.2 [3.0, 32.1] (33) | 12.1 [0.0, 23.7] (33) |
| Claude Haiku 4.5 | tools | 100.0 [100.0, 100.0] (34) | 90.9 [77.8, 100.0] (33) | 93.9 [84.4, 100.0] (33) |
| Claude Sonnet 4.6 | no tools | 41.2 [15.4, 64.9] (34) | 33.3 [15.6, 51.7] (33) | 12.1 [0.0, 23.7] (33) |
| Claude Sonnet 4.6 | tools | 100.0 [100.0, 100.0] (34) | 97.0 [89.7, 100.0] (33) | 87.9 [76.7, 97.0] (33) |
| Gemma-26B | no tools | 22.5 [9.2, 37.5] (102) | 26.3 [6.9, 45.4] (99) | 15.2 [3.2, 27.0] (99) |
| Gemma-26B | tools, plain | 99.0 [96.7, 100.0] (102) | 98.0 [95.1, 100.0] (99) | 79.8 [69.9, 90.1] (99) |
| Gemma-26B | tools, steered | 100.0 [100.0, 100.0] (102) | 99.0 [97.0, 100.0] (99) | 86.9 [75.0, 95.5] (99) |
| Qwen3.5-9B | no tools | 23.5 [11.1, 34.4] (102) | 28.3 [11.8, 42.9] (99) | 21.2 [11.7, 29.7] (99) |
| Qwen3.5-9B | tools, plain | 97.1 [92.2, 100.0] (102) | 91.9 [81.8, 100.0] (99) | 76.8 [60.0, 89.5] (99) |
| Qwen3.5-9B | tools, steered | 95.1 [90.5, 98.9] (102) | 92.9 [84.0, 100.0] (99) | 78.8 [62.2, 91.0] (99) |
| Qwen3.6-35B | no tools | 17.6 [10.1, 25.0] (102) | 34.3 [17.2, 54.2] (99) | 24.2 [8.3, 44.8] (99) |
| Qwen3.6-35B | tools, plain | 78.4 [63.2, 88.6] (102) | 80.8 [67.9, 90.6] (99) | 71.7 [58.3, 82.8] (99) |
| Qwen3.6-35B | tools, steered | 95.1 [92.9, 97.8] (102) | 90.9 [82.8, 97.2] (99) | 75.8 [61.5, 86.5] (99) |

Solved, by number of objects (trials in the bin):

| model | arm | fewest objects | middle third | most objects |
|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 33.3 [13.2, 58.1] (39) | 20.7 [3.3, 44.4] (29) | 9.4 [0.0, 25.0] (32) |
| Claude Haiku 4.5 | tools | 97.4 [92.1, 100.0] (39) | 89.7 [76.7, 100.0] (29) | 96.9 [90.3, 100.0] (32) |
| Claude Sonnet 4.6 | no tools | 51.3 [30.4, 71.9] (39) | 20.7 [6.2, 39.1] (29) | 9.4 [0.0, 17.6] (32) |
| Claude Sonnet 4.6 | tools | 94.9 [88.6, 100.0] (39) | 96.6 [87.5, 100.0] (29) | 93.8 [82.1, 100.0] (32) |
| Gemma-26B | no tools | 35.0 [24.3, 45.7] (117) | 14.9 [3.2, 30.8] (87) | 10.4 [2.4, 19.2] (96) |
| Gemma-26B | tools, plain | 97.4 [92.1, 100.0] (117) | 98.9 [96.7, 100.0] (87) | 80.2 [70.0, 91.4] (96) |
| Gemma-26B | tools, steered | 96.6 [89.5, 100.0] (117) | 100.0 [100.0, 100.0] (87) | 89.6 [78.6, 97.8] (96) |
| Qwen3.5-9B | no tools | 40.2 [33.3, 48.4] (117) | 17.2 [6.7, 30.8] (87) | 11.5 [3.8, 19.4] (96) |
| Qwen3.5-9B | tools, plain | 86.3 [75.2, 96.6] (117) | 97.7 [93.3, 100.0] (87) | 83.3 [66.7, 94.7] (96) |
| Qwen3.5-9B | tools, steered | 86.3 [75.2, 96.3] (117) | 96.6 [92.2, 100.0] (87) | 85.4 [69.3, 95.5] (96) |
| Qwen3.6-35B | no tools | 43.6 [26.7, 59.7] (117) | 16.1 [10.0, 23.3] (87) | 11.5 [5.4, 19.2] (96) |
| Qwen3.6-35B | tools, plain | 84.6 [73.5, 93.3] (117) | 77.0 [64.3, 88.9] (87) | 67.7 [57.8, 77.0] (96) |
| Qwen3.6-35B | tools, steered | 87.2 [78.7, 94.6] (117) | 93.1 [90.0, 96.5] (87) | 82.3 [67.7, 95.1] (96) |

#### RQ1-4. solve: length of the valid delivered plans

Only trials whose delivered plan is valid. Reference = the answer key's plan for the same problem (the planners' default any-plan search, not a shortest plan). Ratio of sums = total delivered actions / total reference actions over those trials.

| model | arm | valid plans / trials | mean length | mean reference length | ratio of sums | median ratio | shorter | equal | longer | largest ratio | same length as the tool's plan |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | no tools | 22/100 | 8.55 | 8.41 | 1.02 | 1.00 | 6 | 10 | 6 | 2.00 | – |
| Claude Haiku 4.5 | tools | 95/100 | 19.66 | 19.73 | 1.00 | 1.00 | 1 | 91 | 3 | 8.67 | 93/95 |
| Claude Sonnet 4.6 | no tools | 29/100 | 6.59 | 7.03 | 0.94 | 1.00 | 7 | 21 | 1 | 1.50 | – |
| Claude Sonnet 4.6 | tools | 95/100 | 23.56 | 18.92 | 1.25 | 1.00 | 4 | 85 | 6 | 61.40 | 94/95 |
| Gemma-26B | no tools | 64/300 | 9.67 | 12.97 | 0.75 | 1.00 | 15 | 45 | 4 | 1.67 | – |
| Gemma-26B | tools, plain | 277/300 | 16.89 | 16.81 | 1.00 | 1.00 | 5 | 259 | 13 | 1.21 | 269/277 |
| Gemma-26B | tools, steered | 286/300 | 17.38 | 17.35 | 1.00 | 1.00 | 4 | 270 | 12 | 1.07 | 280/286 |
| Qwen3.5-9B | no tools | 73/300 | 11.33 | 13.67 | 0.83 | 1.00 | 20 | 40 | 13 | 2.00 | – |
| Qwen3.5-9B | tools, plain | 266/300 | 14.91 | 14.92 | 1.00 | 1.00 | 6 | 252 | 8 | 1.07 | 262/266 |
| Qwen3.5-9B | tools, steered | 267/300 | 15.44 | 15.44 | 1.00 | 1.00 | 6 | 253 | 8 | 1.11 | 263/267 |
| Qwen3.6-35B | no tools | 76/300 | 11.79 | 11.14 | 1.06 | 1.00 | 15 | 44 | 17 | 3.18 | – |
| Qwen3.6-35B | tools, plain | 231/300 | 15.33 | 15.42 | 0.99 | 1.00 | 10 | 214 | 7 | 1.29 | 213/214 |
| Qwen3.6-35B | tools, steered | 262/300 | 15.34 | 15.23 | 1.01 | 1.00 | 4 | 248 | 10 | 8.67 | 257/262 |

"Same length as the tool's plan" = of the valid delivered plans in a trial where a planner call returned a plan, how many have that plan's length. The planner's plan can be much longer than the reference when the model picks another search strategy or the search takes another path; planner calls behind the valid plans, by strategy (all / those longer than the reference):

| model | arm | planner calls by strategy | of which longer than reference |
|---|---|---|---|
| Claude Haiku 4.5 | tools | classic_planner:default 42, classic_planner:lazy_greedy_cea 2, numeric_planner:default 51 | numeric_planner:default 3 |
| Claude Sonnet 4.6 | tools | classic_planner:default 38, classic_planner:lazy_greedy_ff 6, numeric_planner:default 51 | classic_planner:lazy_greedy_ff 2, numeric_planner:default 4 |
| Gemma-26B | tools, plain | classic_planner:default 140, classic_planner:lazy_greedy_cea 3, classic_planner:lazy_greedy_ff 2, numeric_planner:default 132 | classic_planner:default 5, numeric_planner:default 8 |
| Gemma-26B | tools, steered | classic_planner:default 144, classic_planner:lazy_greedy_cea 4, numeric_planner:default 138 | classic_planner:default 6, numeric_planner:default 6 |
| Qwen3.5-9B | tools, plain | classic_planner:default 141, numeric_planner:default 125 | classic_planner:default 6, numeric_planner:default 2 |
| Qwen3.5-9B | tools, steered | classic_planner:default 140, numeric_planner:astar_lmcut 1, numeric_planner:default 126 | classic_planner:default 5, numeric_planner:default 3 |
| Qwen3.6-35B | tools, plain | classic_planner:default 10, classic_planner:lazy_greedy_cea 91, numeric_planner:astar_lmcut 1, numeric_planner:default 112 | classic_planner:lazy_greedy_cea 3 |
| Qwen3.6-35B | tools, steered | classic_planner:astar_lmcut 1, classic_planner:default 64, classic_planner:lazy_greedy_cea 69, numeric_planner:default 128 | classic_planner:lazy_greedy_cea 3, numeric_planner:default 7 |

Claude rows read: Claude Sonnet 4.6 / no tools: 1520 rows, 19 with an unknown delivered grade; Claude Sonnet 4.6 / tools: 1520 rows, 13 with an unknown delivered grade; Claude Haiku 4.5 / no tools: 1520 rows, 30 with an unknown delivered grade; Claude Haiku 4.5 / tools: 1520 rows, 12 with an unknown delivered grade.
<!-- END GENERATED: RQ1-METRICS -->

## RQ2 metrics — tool choice (added 2026-11-22; post hoc, exploratory; in no tex yet)

The advisors' RQ2 metrics (`roadmap.md` §2), from the stored tool calls, by
`tools/reanalysis/rq23_metrics.py` (rerun: `python -m tools.reanalysis.rq23_metrics --numbers`;
tests in `tests/test_rq23_metrics.py`). How to read the block:

- **Four classes per trial**, by the set of tools it called: no call; only the right tool;
  the right tool and another; other tools only. "Exactly right" is the second class, "the
  right tool was called" is the second plus the third, "another tool was called" is the
  third plus the fourth.
- **Solve is graded more strictly here than by the harness.** The right tool is the planner
  that fits the domain; the harness's calling figures (Study 1 block, T2 and T3) accept
  either planner. So a solve calling rate here can be lower than the frozen one. On the
  four other tasks "the right tool was called" equals the frozen calling rate.
- **A plan check after the planner counts as another tool** and is also shown on its own,
  since checking a plan is not a mistake.
- **Three separate apparatus, never pooled:** the main sweep (also the only source for
  thinking on), the rerun, the Claude runs. The 35B plain cells differ between the main
  sweep and the rerun (the calling flips of T8c); quote both.

<!-- BEGIN GENERATED: RQ2-METRICS (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/rq23_metrics.py`. Post hoc and descriptive. Every with-tools trial offered all seven tools. Rates are percent of the cell's trials with 95% domain-cluster bootstrap percentile intervals. The three corpora are separate apparatus and are never pooled. "Plain" = tools offered with no instruction to use one; "steered" = one added sentence naming the tool; "neutral prompt" = the system prompt without its use-the-tool policy sentence (Gemma, validate_plan only). Self-check: the harness rule applied to the stored calls equals the stored `tool_selected` on all 127600 rows.*

#### RQ2. Main sweep (Study 1), five open models, thinking off and on

Share of trials where exactly the right tool and no other (higher is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | off | plain | 21.0 [9.3, 35.0] | 81.9 [76.4, 87.8] | 75.5 [64.7, 85.7] | 87.4 [80.1, 93.6] | 22.3 [13.7, 32.0] |
| Qwen3.5-0.8B | off | steered | 34.0 [17.3, 52.3] | 92.8 [85.6, 98.3] | 98.8 [97.8, 99.7] | 93.4 [88.9, 97.2] | 54.0 [43.3, 65.3] |
| Qwen3.5-0.8B | on | steered | 15.3 [8.3, 23.0] | 88.3 [83.1, 92.8] | 82.5 [77.3, 87.3] | 55.5 [47.6, 63.5] | 49.7 [40.7, 58.7] |
| Qwen3.5-0.8B | on | plain | 11.7 [6.3, 17.7] | 83.3 [76.7, 89.2] | 75.3 [68.8, 81.2] | 49.3 [40.2, 58.2] | 16.0 [12.0, 20.0] |
| Qwen3.5-4B | off | plain | 38.0 [26.3, 49.7] | 100.0 [100.0, 100.0] | 81.5 [69.8, 91.5] | 80.3 [72.9, 87.1] | 77.3 [65.3, 87.7] |
| Qwen3.5-4B | off | steered | 40.3 [28.3, 53.0] | 100.0 [100.0, 100.0] | 91.3 [84.8, 96.5] | 93.5 [89.4, 97.0] | 80.0 [67.7, 90.7] |
| Qwen3.5-4B | on | plain | 41.3 [31.3, 51.3] | 100.0 [100.0, 100.0] | 98.7 [97.3, 99.7] | 95.0 [93.3, 96.6] | 86.0 [79.7, 92.0] |
| Qwen3.5-4B | on | steered | 54.7 [43.7, 65.3] | 99.7 [99.2, 100.0] | 98.8 [97.8, 99.7] | 98.9 [98.2, 99.5] | 94.0 [90.0, 97.3] |
| Qwen3.5-9B | off | plain | 40.0 [23.3, 57.7] | 100.0 [100.0, 100.0] | 99.5 [98.5, 100.0] | 95.9 [91.5, 99.3] | 70.7 [61.7, 78.0] |
| Qwen3.5-9B | off | steered | 51.0 [31.7, 70.7] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.9 [99.6, 100.0] | 89.0 [77.7, 97.7] |
| Qwen3.5-9B | on | steered | 25.0 [17.0, 33.7] | 98.9 [97.8, 99.7] | 98.8 [98.0, 99.7] | 97.1 [95.9, 98.3] | 98.0 [95.0, 100.0] |
| Qwen3.5-9B | on | plain | 8.7 [4.7, 13.3] | 99.4 [98.6, 100.0] | 95.3 [92.0, 98.2] | 67.8 [60.1, 74.9] | 90.7 [84.0, 96.0] |
| Gemma-26B | off | plain | 29.3 [18.0, 41.3] | 100.0 [100.0, 100.0] | 90.8 [87.5, 94.2] | 20.7 [9.0, 34.0] | 92.7 [86.7, 97.7] |
| Gemma-26B | off | steered | 50.7 [37.0, 63.7] | 100.0 [100.0, 100.0] | 94.5 [92.0, 96.8] | 93.6 [84.0, 100.0] | 94.7 [88.7, 99.3] |
| Gemma-26B | on | plain | 11.7 [6.3, 17.7] | 52.5 [36.7, 68.1] | 53.7 [41.8, 65.5] | 0.6 [0.0, 1.5] | 47.0 [38.3, 55.7] |
| Gemma-26B | on | steered | 50.0 [35.3, 65.3] | 90.6 [82.8, 96.7] | 85.0 [74.2, 93.7] | 44.2 [29.6, 59.6] | 97.7 [96.0, 99.3] |
| Qwen3.6-35B | off | plain | 27.7 [21.0, 33.7] | 100.0 [100.0, 100.0] | 95.0 [93.7, 96.2] | 82.5 [73.0, 90.8] | 74.0 [64.7, 82.3] |
| Qwen3.6-35B | off | steered | 44.7 [34.3, 54.7] | 100.0 [100.0, 100.0] | 99.3 [98.7, 99.8] | 98.1 [94.7, 99.9] | 99.3 [98.0, 100.0] |
| Qwen3.6-35B | on | plain | 29.0 [19.7, 39.0] | 100.0 [100.0, 100.0] | 99.5 [99.0, 100.0] | 99.9 [99.7, 100.0] | 97.3 [95.3, 99.0] |
| Qwen3.6-35B | on | steered | 55.0 [46.3, 64.0] | 100.0 [100.0, 100.0] | 99.7 [99.2, 100.0] | 99.7 [99.4, 100.0] | 99.0 [98.0, 100.0] |

Share of trials where the right tool was called (higher is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | off | plain | 54.7 [39.0, 69.7] | 98.6 [95.8, 100.0] | 95.3 [89.5, 99.3] | 92.8 [86.7, 97.7] | 48.3 [36.0, 60.0] |
| Qwen3.5-0.8B | off | steered | 55.3 [36.0, 73.7] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Qwen3.5-0.8B | on | steered | 58.0 [45.0, 70.7] | 91.9 [87.2, 96.1] | 96.0 [94.0, 97.8] | 76.2 [69.3, 82.5] | 81.3 [73.3, 88.7] |
| Qwen3.5-0.8B | on | plain | 36.0 [26.3, 46.0] | 90.3 [83.9, 95.6] | 94.3 [89.8, 97.7] | 68.6 [57.6, 79.0] | 32.7 [25.3, 40.0] |
| Qwen3.5-4B | off | plain | 92.0 [83.3, 98.7] | 100.0 [100.0, 100.0] | 99.8 [99.5, 100.0] | 99.9 [99.8, 100.0] | 96.7 [94.3, 98.7] |
| Qwen3.5-4B | off | steered | 96.3 [90.7, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Qwen3.5-4B | on | plain | 78.3 [66.3, 89.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 98.8 [97.9, 99.5] | 98.3 [97.0, 99.7] |
| Qwen3.5-4B | on | steered | 84.0 [75.3, 91.3] | 99.7 [99.2, 100.0] | 99.8 [99.5, 100.0] | 99.2 [98.5, 99.7] | 98.7 [97.0, 100.0] |
| Qwen3.5-9B | off | plain | 99.3 [98.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 97.9 [94.2, 100.0] | 80.0 [76.0, 84.0] |
| Qwen3.5-9B | off | steered | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.7 [99.0, 100.0] |
| Qwen3.5-9B | on | steered | 72.0 [63.0, 80.7] | 98.9 [97.8, 99.7] | 99.0 [98.2, 99.7] | 97.1 [95.9, 98.3] | 99.7 [99.0, 100.0] |
| Qwen3.5-9B | on | plain | 57.0 [45.3, 68.7] | 99.4 [98.6, 100.0] | 98.7 [97.3, 99.7] | 69.2 [61.7, 76.0] | 94.0 [90.0, 97.3] |
| Gemma-26B | off | plain | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.8 [99.5, 100.0] | 20.7 [9.0, 34.1] | 99.7 [99.0, 100.0] |
| Gemma-26B | off | steered | 99.0 [97.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 93.6 [84.0, 100.0] | 100.0 [100.0, 100.0] |
| Gemma-26B | on | plain | 23.3 [15.7, 31.7] | 52.5 [36.7, 68.1] | 56.0 [43.7, 68.0] | 0.6 [0.0, 1.5] | 53.3 [45.0, 61.7] |
| Gemma-26B | on | steered | 74.3 [59.7, 87.7] | 90.6 [82.8, 96.7] | 85.0 [74.2, 93.7] | 44.2 [29.6, 59.6] | 98.7 [97.3, 99.7] |
| Qwen3.6-35B | off | plain | 64.3 [56.3, 72.3] | 100.0 [100.0, 100.0] | 98.5 [97.8, 99.2] | 82.9 [73.5, 91.1] | 76.3 [67.0, 84.3] |
| Qwen3.6-35B | off | steered | 92.7 [88.0, 97.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.9 [99.7, 100.0] | 100.0 [100.0, 100.0] |
| Qwen3.6-35B | on | plain | 75.0 [62.7, 86.3] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.9 [99.8, 100.0] | 99.3 [98.3, 100.0] |
| Qwen3.6-35B | on | steered | 89.3 [79.3, 97.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.9 [99.7, 100.0] | 100.0 [100.0, 100.0] |

Share of trials where another tool was called, with or without the right one (lower is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | off | plain | 79.0 [65.0, 90.7] | 16.7 [10.8, 22.5] | 24.5 [14.3, 35.3] | 12.6 [6.4, 19.8] | 76.3 [65.0, 86.0] |
| Qwen3.5-0.8B | off | steered | 66.0 [47.7, 82.7] | 7.2 [1.7, 14.4] | 1.2 [0.3, 2.2] | 6.6 [2.8, 11.1] | 46.0 [34.7, 56.7] |
| Qwen3.5-0.8B | on | steered | 59.3 [50.3, 68.3] | 3.6 [2.2, 5.3] | 14.5 [9.7, 19.5] | 27.0 [21.2, 33.3] | 37.7 [30.3, 45.3] |
| Qwen3.5-0.8B | on | plain | 40.0 [34.0, 46.0] | 6.9 [3.3, 11.4] | 20.5 [15.2, 26.3] | 28.6 [22.5, 34.8] | 34.7 [28.3, 41.0] |
| Qwen3.5-4B | off | plain | 62.0 [50.3, 73.7] | 0.0 [0.0, 0.0] | 18.5 [8.5, 30.2] | 19.7 [12.9, 27.1] | 20.3 [10.0, 32.0] |
| Qwen3.5-4B | off | steered | 59.7 [47.0, 71.7] | 0.0 [0.0, 0.0] | 8.7 [3.5, 15.2] | 6.5 [3.0, 10.6] | 20.0 [9.3, 32.3] |
| Qwen3.5-4B | on | plain | 40.0 [32.3, 48.3] | 0.0 [0.0, 0.0] | 1.3 [0.3, 2.7] | 4.2 [2.8, 5.8] | 12.7 [7.0, 19.0] |
| Qwen3.5-4B | on | steered | 32.3 [23.7, 42.0] | 0.0 [0.0, 0.0] | 1.0 [0.2, 2.0] | 0.3 [0.1, 0.7] | 4.7 [1.3, 8.7] |
| Qwen3.5-9B | off | plain | 60.0 [42.3, 76.7] | 0.0 [0.0, 0.0] | 0.5 [0.0, 1.5] | 2.0 [0.1, 5.0] | 9.7 [3.3, 17.7] |
| Qwen3.5-9B | off | steered | 49.0 [29.3, 68.3] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.1 [0.0, 0.4] | 10.7 [2.0, 22.0] |
| Qwen3.5-9B | on | steered | 50.7 [42.0, 59.7] | 0.0 [0.0, 0.0] | 0.2 [0.0, 0.5] | 0.0 [0.0, 0.1] | 1.7 [0.0, 4.7] |
| Qwen3.5-9B | on | plain | 52.7 [43.0, 62.0] | 0.0 [0.0, 0.0] | 3.7 [1.2, 6.7] | 1.4 [0.8, 2.3] | 3.3 [0.3, 8.0] |
| Gemma-26B | off | plain | 70.7 [58.7, 82.0] | 0.0 [0.0, 0.0] | 9.0 [5.7, 12.3] | 0.1 [0.0, 0.2] | 7.0 [2.0, 13.0] |
| Gemma-26B | off | steered | 49.3 [36.3, 63.0] | 0.0 [0.0, 0.0] | 5.5 [3.2, 8.0] | 0.0 [0.0, 0.0] | 5.3 [0.7, 11.3] |
| Gemma-26B | on | plain | 11.7 [6.3, 18.0] | 0.0 [0.0, 0.0] | 2.5 [0.8, 4.7] | 0.0 [0.0, 0.0] | 7.3 [4.3, 10.7] |
| Gemma-26B | on | steered | 25.0 [14.3, 37.3] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 1.0 [0.0, 2.0] |
| Qwen3.6-35B | off | plain | 51.0 [40.0, 61.7] | 0.0 [0.0, 0.0] | 3.5 [2.2, 5.2] | 0.4 [0.2, 0.7] | 2.3 [0.0, 5.3] |
| Qwen3.6-35B | off | steered | 52.3 [42.0, 62.7] | 0.0 [0.0, 0.0] | 0.7 [0.2, 1.3] | 1.8 [0.0, 5.3] | 0.7 [0.0, 2.0] |
| Qwen3.6-35B | on | plain | 50.3 [40.3, 60.3] | 0.0 [0.0, 0.0] | 0.5 [0.0, 1.0] | 0.1 [0.0, 0.2] | 2.0 [0.7, 3.7] |
| Qwen3.6-35B | on | steered | 37.0 [30.0, 44.3] | 0.0 [0.0, 0.0] | 0.3 [0.0, 0.8] | 0.2 [0.0, 0.5] | 1.0 [0.0, 2.0] |

Share of trials where no tool was called:

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | off | plain | 0.0 [0.0, 0.0] | 1.4 [0.0, 4.2] | 0.0 [0.0, 0.0] | 0.1 [0.0, 0.2] | 1.3 [0.0, 4.0] |
| Qwen3.5-0.8B | off | steered | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Qwen3.5-0.8B | on | steered | 25.3 [16.0, 35.7] | 8.1 [3.9, 12.8] | 3.0 [1.3, 4.8] | 17.5 [10.7, 24.9] | 12.7 [6.3, 20.3] |
| Qwen3.5-0.8B | on | plain | 48.3 [40.3, 56.3] | 9.7 [4.4, 16.1] | 4.2 [1.0, 8.7] | 22.1 [13.6, 31.0] | 49.3 [41.7, 57.3] |
| Qwen3.5-4B | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 2.3 [0.7, 4.3] |
| Qwen3.5-4B | off | steered | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Qwen3.5-4B | on | plain | 18.7 [9.7, 29.3] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.8 [0.3, 1.4] | 1.3 [0.3, 2.7] |
| Qwen3.5-4B | on | steered | 13.0 [6.7, 21.0] | 0.3 [0.0, 0.8] | 0.2 [0.0, 0.5] | 0.8 [0.3, 1.5] | 1.3 [0.0, 3.0] |
| Qwen3.5-9B | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 2.1 [0.0, 5.8] | 19.7 [15.3, 24.0] |
| Qwen3.5-9B | off | steered | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.3 [0.0, 1.0] |
| Qwen3.5-9B | on | steered | 24.3 [16.7, 32.7] | 1.1 [0.3, 2.2] | 1.0 [0.3, 1.8] | 2.9 [1.7, 4.1] | 0.3 [0.0, 1.0] |
| Qwen3.5-9B | on | plain | 38.7 [27.3, 50.0] | 0.6 [0.0, 1.4] | 1.0 [0.3, 1.8] | 30.8 [23.9, 38.2] | 6.0 [2.7, 10.0] |
| Gemma-26B | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.2 [0.0, 0.5] | 79.3 [65.9, 91.0] | 0.3 [0.0, 1.0] |
| Gemma-26B | off | steered | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 6.4 [0.0, 16.0] | 0.0 [0.0, 0.0] |
| Gemma-26B | on | plain | 76.7 [68.3, 84.3] | 47.5 [31.9, 63.3] | 43.8 [31.8, 56.2] | 99.4 [98.5, 100.0] | 45.7 [37.7, 53.7] |
| Gemma-26B | on | steered | 25.0 [11.7, 39.7] | 9.4 [3.3, 17.2] | 15.0 [6.3, 25.8] | 55.8 [40.4, 70.4] | 1.3 [0.3, 2.7] |
| Qwen3.6-35B | off | plain | 21.3 [13.7, 29.7] | 0.0 [0.0, 0.0] | 1.5 [0.8, 2.2] | 17.1 [8.9, 26.4] | 23.7 [15.7, 33.0] |
| Qwen3.6-35B | off | steered | 3.0 [1.0, 5.7] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.1 [0.0, 0.3] | 0.0 [0.0, 0.0] |
| Qwen3.6-35B | on | plain | 20.7 [11.7, 30.3] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.1 [0.0, 0.2] | 0.7 [0.0, 1.7] |
| Qwen3.6-35B | on | steered | 8.0 [3.0, 14.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.1 [0.0, 0.3] | 0.0 [0.0, 0.0] |

Solve, counts behind the shares (trials; the right tool is the planner that fits the domain):

| model | thinking | prompt | trials | no call | right only | right + other | other only | called the other planner | right planner + a plan check only |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | off | plain | 300 | 0 | 63 | 101 | 136 | 216 | 0 |
| Qwen3.5-0.8B | off | steered | 300 | 0 | 102 | 64 | 134 | 191 | 0 |
| Qwen3.5-0.8B | on | steered | 300 | 76 | 46 | 128 | 50 | 113 | 2 |
| Qwen3.5-0.8B | on | plain | 300 | 145 | 35 | 73 | 47 | 69 | 0 |
| Qwen3.5-4B | off | plain | 300 | 0 | 114 | 162 | 24 | 51 | 35 |
| Qwen3.5-4B | off | steered | 300 | 0 | 121 | 168 | 11 | 43 | 27 |
| Qwen3.5-4B | on | plain | 300 | 56 | 124 | 111 | 9 | 18 | 41 |
| Qwen3.5-4B | on | steered | 300 | 39 | 164 | 88 | 9 | 16 | 51 |
| Qwen3.5-9B | off | plain | 300 | 0 | 120 | 178 | 2 | 130 | 42 |
| Qwen3.5-9B | off | steered | 300 | 0 | 153 | 147 | 0 | 130 | 17 |
| Qwen3.5-9B | on | steered | 300 | 73 | 75 | 141 | 11 | 35 | 98 |
| Qwen3.5-9B | on | plain | 300 | 116 | 26 | 145 | 13 | 56 | 61 |
| Gemma-26B | off | plain | 300 | 0 | 88 | 212 | 0 | 48 | 163 |
| Gemma-26B | off | steered | 300 | 0 | 152 | 145 | 3 | 19 | 129 |
| Gemma-26B | on | plain | 300 | 230 | 35 | 35 | 0 | 29 | 6 |
| Gemma-26B | on | steered | 300 | 75 | 150 | 73 | 2 | 65 | 9 |
| Qwen3.6-35B | off | plain | 300 | 64 | 83 | 110 | 43 | 50 | 61 |
| Qwen3.6-35B | off | steered | 300 | 9 | 134 | 144 | 13 | 25 | 83 |
| Qwen3.6-35B | on | plain | 300 | 62 | 87 | 138 | 13 | 14 | 101 |
| Qwen3.6-35B | on | steered | 300 | 24 | 165 | 103 | 8 | 8 | 83 |

#### RQ2. Delivered rerun (Study 2), thinking off

Share of trials where exactly the right tool and no other (higher is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Gemma-26B | off | plain | 28.7 [17.3, 41.0] | 100.0 [100.0, 100.0] | 91.8 [88.7, 95.0] | 20.0 [8.5, 33.0] | 91.0 [84.3, 96.7] |
| Gemma-26B | off | steered | 44.0 [30.7, 57.3] | 100.0 [100.0, 100.0] | 95.0 [92.5, 97.3] | 93.1 [82.9, 99.9] | 93.0 [87.0, 98.0] |
| Qwen3.5-9B | off | plain | 39.0 [22.3, 56.7] | 100.0 [100.0, 100.0] | 99.3 [98.3, 100.0] | 95.4 [91.0, 98.9] | 68.3 [58.7, 76.7] |
| Qwen3.5-9B | off | steered | 47.7 [29.0, 66.7] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.5 [98.5, 100.0] | 87.7 [76.0, 96.7] |
| Qwen3.6-35B | off | plain | 22.3 [15.0, 30.0] | 100.0 [100.0, 100.0] | 97.2 [95.8, 98.5] | 82.7 [71.6, 91.9] | 95.3 [91.0, 98.7] |
| Qwen3.6-35B | off | steered | 43.0 [31.0, 55.7] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.7 [99.2, 100.0] | 97.7 [95.3, 99.7] |
| Gemma-26B | off | neutral prompt, plain | – | – | – | 26.9 [14.5, 40.0] | – |
| Gemma-26B | off | neutral prompt, steered | – | – | – | 98.1 [95.8, 100.0] | – |

Share of trials where the right tool was called (higher is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Gemma-26B | off | plain | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 20.0 [8.5, 33.1] | 99.7 [99.0, 100.0] |
| Gemma-26B | off | steered | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 93.1 [82.9, 99.9] | 100.0 [100.0, 100.0] |
| Qwen3.5-9B | off | plain | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 97.8 [94.5, 100.0] | 80.7 [76.0, 85.3] |
| Qwen3.5-9B | off | steered | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Qwen3.6-35B | off | plain | 82.7 [75.7, 89.3] | 100.0 [100.0, 100.0] | 99.3 [98.7, 99.8] | 83.1 [71.8, 92.4] | 99.7 [99.0, 100.0] |
| Qwen3.6-35B | off | steered | 98.3 [96.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Gemma-26B | off | neutral prompt, plain | – | – | – | 26.9 [14.5, 40.0] | – |
| Gemma-26B | off | neutral prompt, steered | – | – | – | 98.1 [95.8, 100.0] | – |

Share of trials where another tool was called, with or without the right one (lower is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Gemma-26B | off | plain | 71.3 [59.0, 82.7] | 0.0 [0.0, 0.0] | 8.2 [5.0, 11.3] | 0.0 [0.0, 0.1] | 8.7 [3.0, 15.3] |
| Gemma-26B | off | steered | 56.0 [42.7, 69.3] | 0.0 [0.0, 0.0] | 5.0 [2.7, 7.5] | 0.0 [0.0, 0.0] | 7.0 [2.0, 13.0] |
| Qwen3.5-9B | off | plain | 61.0 [43.3, 77.7] | 0.0 [0.0, 0.0] | 0.7 [0.0, 1.7] | 2.5 [0.2, 6.2] | 13.0 [5.7, 22.3] |
| Qwen3.5-9B | off | steered | 52.3 [33.3, 71.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.5 [0.0, 1.5] | 12.3 [3.3, 24.0] |
| Qwen3.6-35B | off | plain | 65.3 [58.3, 72.7] | 0.0 [0.0, 0.0] | 2.2 [0.8, 3.5] | 0.4 [0.0, 0.9] | 4.3 [1.0, 8.7] |
| Qwen3.6-35B | off | steered | 56.7 [44.0, 68.3] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.3 [0.0, 0.8] | 2.3 [0.3, 4.7] |
| Gemma-26B | off | neutral prompt, plain | – | – | – | 0.0 [0.0, 0.0] | – |
| Gemma-26B | off | neutral prompt, steered | – | – | – | 0.0 [0.0, 0.0] | – |

Share of trials where no tool was called:

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Gemma-26B | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 80.0 [66.9, 91.5] | 0.3 [0.0, 1.0] |
| Gemma-26B | off | steered | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 6.9 [0.1, 17.1] | 0.0 [0.0, 0.0] |
| Qwen3.5-9B | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 2.1 [0.0, 5.4] | 18.7 [14.0, 23.3] |
| Qwen3.5-9B | off | steered | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Qwen3.6-35B | off | plain | 12.3 [6.7, 18.7] | 0.0 [0.0, 0.0] | 0.7 [0.2, 1.3] | 16.9 [7.6, 28.2] | 0.3 [0.0, 1.0] |
| Qwen3.6-35B | off | steered | 0.3 [0.0, 1.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Gemma-26B | off | neutral prompt, plain | – | – | – | 73.1 [60.0, 85.5] | – |
| Gemma-26B | off | neutral prompt, steered | – | – | – | 1.9 [0.0, 4.2] | – |

Solve, counts behind the shares (trials; the right tool is the planner that fits the domain):

| model | thinking | prompt | trials | no call | right only | right + other | other only | called the other planner | right planner + a plan check only |
|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | off | plain | 300 | 0 | 86 | 214 | 0 | 38 | 175 |
| Gemma-26B | off | steered | 300 | 0 | 132 | 168 | 0 | 28 | 140 |
| Qwen3.5-9B | off | plain | 300 | 0 | 117 | 183 | 0 | 138 | 37 |
| Qwen3.5-9B | off | steered | 300 | 0 | 143 | 157 | 0 | 135 | 21 |
| Qwen3.6-35B | off | plain | 300 | 37 | 67 | 181 | 15 | 50 | 100 |
| Qwen3.6-35B | off | steered | 300 | 1 | 129 | 166 | 4 | 18 | 85 |

#### RQ2. Claude runs, wording v11

Share of trials where exactly the right tool and no other (higher is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | off | plain | 65.0 [49.0, 80.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 99.4 [98.9, 99.8] | 99.0 [97.0, 100.0] |
| Claude Haiku 4.5 | off | plain | 1.0 [0.0, 3.0] | 100.0 [100.0, 100.0] | 99.0 [97.5, 100.0] | 99.9 [99.7, 100.0] | 98.0 [95.0, 100.0] |

Share of trials where the right tool was called (higher is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | off | plain | 95.0 [85.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Claude Haiku 4.5 | off | plain | 95.0 [85.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |

Share of trials where another tool was called, with or without the right one (lower is better):

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | off | plain | 35.0 [20.0, 51.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.6 [0.2, 1.1] | 1.0 [0.0, 3.0] |
| Claude Haiku 4.5 | off | plain | 99.0 [97.0, 100.0] | 0.0 [0.0, 0.0] | 1.0 [0.0, 2.5] | 0.1 [0.0, 0.3] | 2.0 [0.0, 5.0] |

Share of trials where no tool was called:

| model | thinking | prompt | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Claude Haiku 4.5 | off | plain | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |

Solve, counts behind the shares (trials; the right tool is the planner that fits the domain):

| model | thinking | prompt | trials | no call | right only | right + other | other only | called the other planner | right planner + a plan check only |
|---|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | off | plain | 100 | 0 | 65 | 30 | 5 | 5 | 1 |
| Claude Haiku 4.5 | off | plain | 100 | 0 | 1 | 94 | 5 | 6 | 10 |
<!-- END GENERATED: RQ2-METRICS -->

## RQ3 metrics — use of the tool's output (added 2026-11-22; post hoc, exploratory; in no tex yet)

The advisors' RQ3 metric: of the trials where the tool returned the right result, the
share whose delivered final answer is wrong. Same script as RQ2. How to read the block:

- **The rerun rows are the frozen readout's E4 cells**, restated; the script halts unless
  all 30 reproduce. Nothing here replaces E4.
- **Most losses on simulate and solve are not wrong content.** The largest category is a
  final turn that was refused or clipped because the tool's result had filled the context
  window. Read the "why" column before calling a loss a copying error.
- **Claude simulate is a range:** answers cut at the storage cap have an unknown grade.
- **Frozen grades:** the ISS-028 split (a correct plan followed by the goal facts) is not
  applied; it is the post hoc line under "Delivered rerun — readout".

<!-- BEGIN GENERATED: RQ3-METRICS (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/rq23_metrics.py`. Post hoc and descriptive. "Tool right" = trials where the right tool returned the right result (tool-verified). "Lost" = of those, the delivered final answer is wrong; share in percent with a 95% domain-cluster bootstrap percentile interval. Rerun cells are the frozen readout's E4 cells (the script halts unless all 30 reproduce); the "why" column is E4's frozen categories in plain words. Claude: delivered grade from the e2e overlay; "unknown" = answers cut at the 16,384-character storage cap, counted as not lost in the share, so the true share lies between lost and lost + unknown. Open models and Claude are never pooled. Frozen grades: ISS-028 (a correct plan followed by the goal facts counts as lost on solve) is not corrected here; its post hoc split is the ISS-028 line under "Delivered rerun — readout".*

#### RQ3. Delivered rerun, three open models, thinking off

| model | prompt | task | trials | tool right | lost | lost, share of tool right | why (count) |
|---|---|---|---|---|---|---|---|
| Gemma-26B | plain | solve | 300 | 296 | 19 | 6.4 [2.1, 11.2] | final turn refused or clipped (no room left) 10; content differs from the tool's 6; right content, unreadable format 3 |
| Gemma-26B | steered | solve | 300 | 300 | 14 | 4.7 [1.3, 8.7] | final turn refused or clipped (no room left) 10; content differs from the tool's 3; right content, unreadable format 1 |
| Gemma-26B | plain | validate_domain | 360 | 352 | 0 | 0.0 [0.0, 0.0] | – |
| Gemma-26B | steered | validate_domain | 360 | 356 | 0 | 0.0 [0.0, 0.0] | – |
| Gemma-26B | plain | validate_problem | 600 | 597 | 0 | 0.0 [0.0, 0.0] | – |
| Gemma-26B | steered | validate_problem | 600 | 600 | 2 | 0.3 [0.0, 0.8] | content differs from the tool's 2 |
| Gemma-26B | plain | validate_plan | 3000 | 596 | 0 | 0.0 [0.0, 0.0] | – |
| Gemma-26B | steered | validate_plan | 3000 | 2764 | 3 | 0.1 [0.0, 0.3] | final turn refused or clipped (no room left) 2; not decidable by rule 1 |
| Gemma-26B | plain | simulate | 300 | 272 | 247 | 90.8 [85.4, 95.5] | final turn refused or clipped (no room left) 148; not decidable by rule 81; content differs from the tool's 18 |
| Gemma-26B | steered | simulate | 300 | 272 | 248 | 91.2 [86.0, 95.8] | final turn refused or clipped (no room left) 151; not decidable by rule 79; content differs from the tool's 18 |
| Qwen3.5-9B | plain | solve | 300 | 300 | 34 | 11.3 [5.3, 18.0] | final turn refused or clipped (no room left) 20; content differs from the tool's 13; output shortened 1 |
| Qwen3.5-9B | steered | solve | 300 | 300 | 33 | 11.0 [5.7, 17.3] | final turn refused or clipped (no room left) 19; content differs from the tool's 10; a summary, not the output 2; output shortened 2 |
| Qwen3.5-9B | plain | validate_domain | 360 | 360 | 0 | 0.0 [0.0, 0.0] | – |
| Qwen3.5-9B | steered | validate_domain | 360 | 360 | 0 | 0.0 [0.0, 0.0] | – |
| Qwen3.5-9B | plain | validate_problem | 600 | 569 | 0 | 0.0 [0.0, 0.0] | – |
| Qwen3.5-9B | steered | validate_problem | 600 | 546 | 2 | 0.4 [0.0, 0.9] | content differs from the tool's 1; not decidable by rule 1 |
| Qwen3.5-9B | plain | validate_plan | 3000 | 2776 | 20 | 0.7 [0.1, 1.7] | final turn refused or clipped (no room left) 13; not decidable by rule 4; content differs from the tool's 3 |
| Qwen3.5-9B | steered | validate_plan | 3000 | 2884 | 7 | 0.2 [0.0, 0.7] | not decidable by rule 4; final turn refused or clipped (no room left) 1; no final answer 1; content differs from the tool's 1 |
| Qwen3.5-9B | plain | simulate | 300 | 204 | 152 | 74.5 [60.4, 87.7] | final turn refused or clipped (no room left) 106; content differs from the tool's 35; not decidable by rule 10; output shortened 1 |
| Qwen3.5-9B | steered | simulate | 300 | 261 | 212 | 81.2 [70.5, 90.4] | final turn refused or clipped (no room left) 132; content differs from the tool's 40; not decidable by rule 38; output shortened 1; numeric values left out 1 |
| Qwen3.6-35B | plain | solve | 300 | 247 | 33 | 13.4 [7.6, 19.8] | final turn refused or clipped (no room left) 22; output shortened 4; right content, unreadable format 3; content differs from the tool's 3; a summary, not the output 1 |
| Qwen3.6-35B | steered | solve | 300 | 298 | 36 | 12.1 [6.8, 17.8] | final turn refused or clipped (no room left) 23; a summary, not the output 3; output shortened 3; content differs from the tool's 3; right content, unreadable format 2; not decidable by rule 2 |
| Qwen3.6-35B | plain | validate_domain | 360 | 355 | 0 | 0.0 [0.0, 0.0] | – |
| Qwen3.6-35B | steered | validate_domain | 360 | 358 | 0 | 0.0 [0.0, 0.0] | – |
| Qwen3.6-35B | plain | validate_problem | 600 | 583 | 10 | 1.7 [0.5, 3.1] | not decidable by rule 9; content differs from the tool's 1 |
| Qwen3.6-35B | steered | validate_problem | 600 | 584 | 0 | 0.0 [0.0, 0.0] | – |
| Qwen3.6-35B | plain | validate_plan | 3000 | 2472 | 17 | 0.7 [0.0, 1.4] | not decidable by rule 12; final turn refused or clipped (no room left) 4; content differs from the tool's 1 |
| Qwen3.6-35B | steered | validate_plan | 3000 | 2974 | 15 | 0.5 [0.1, 1.1] | not decidable by rule 13; final turn refused or clipped (no room left) 2 |
| Qwen3.6-35B | plain | simulate | 300 | 282 | 197 | 69.9 [56.5, 82.4] | final turn refused or clipped (no room left) 151; content differs from the tool's 26; not decidable by rule 11; numeric values left out 9 |
| Qwen3.6-35B | steered | simulate | 300 | 287 | 210 | 73.2 [61.3, 84.2] | final turn refused or clipped (no room left) 155; not decidable by rule 25; content differs from the tool's 23; numeric values left out 7 |

#### RQ3. Claude runs, wording v11

| model | prompt | task | trials | tool right | lost | unknown | lost, share of tool right | why (count) |
|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | plain | solve | 100 | 100 | 5 | 0 | 5.0 [2.0, 9.0] | plan_invalid 5 |
| Claude Sonnet 4.6 | plain | validate_domain | 120 | 115 | 0 | 0 | 0.0 [0.0, 0.0] | – |
| Claude Sonnet 4.6 | plain | validate_problem | 200 | 196 | 0 | 0 | 0.0 [0.0, 0.0] | – |
| Claude Sonnet 4.6 | plain | validate_plan | 1000 | 999 | 0 | 0 | 0.0 [0.0, 0.0] | – |
| Claude Sonnet 4.6 | plain | simulate | 100 | 99 | 38 | 13 | 38.4 [26.3, 51.0] | format_parse_fail 21; trajectory_mismatch 17 |
| Claude Haiku 4.5 | plain | solve | 100 | 100 | 5 | 0 | 5.0 [1.0, 10.0] | plan_invalid 3; no_plan_extracted 2 |
| Claude Haiku 4.5 | plain | validate_domain | 120 | 118 | 0 | 0 | 0.0 [0.0, 0.0] | – |
| Claude Haiku 4.5 | plain | validate_problem | 200 | 193 | 0 | 0 | 0.0 [0.0, 0.0] | – |
| Claude Haiku 4.5 | plain | validate_plan | 1000 | 989 | 1 | 0 | 0.1 [0.0, 0.3] | verdict_stated_wrong 1 |
| Claude Haiku 4.5 | plain | simulate | 100 | 97 | 33 | 12 | 34.0 [21.6, 46.5] | format_parse_fail 17; trajectory_mismatch 15; truncated_empty 1 |
<!-- END GENERATED: RQ3-METRICS -->

## RQ3 pilot — context window size (added 2026-11-22; post hoc pilot; in tex, RQ3)

Does a larger context window recover the correct tool results that RQ3 counts as lost?
`tools/reanalysis/rq3_context_pilot.py` (rerun: `python -m tools.reanalysis.rq3_context_pilot --numbers`)
grades the 32K and 64K smoke runs of 2026-10-27 with the frozen delivered grader and
compares them with the same trials of the 16K rerun. How to read the block:

- **What it shows:** more room removes most EMPTY final answers on simulate (about 42% at
  16K, 6 to 11% at 64K) and raises delivered success, but most correct tool results are
  still counted as lost at 64K (Gemma 83.8%, 9B 69.0%, 35B 49.1%).
- **Why the rest is still lost (checked 2026-11-22, on Omer's question whether the pilot
  hides a technical fault):** no fault in the pilot's setup was found. Two properties of
  the task explain the residue. (1) *Layout.* The frozen grader reads one JSON value; a
  trace written one object per line fails it whatever its content. Reading such traces too
  lowers Gemma's loss by 11 to 17 points and the Qwen models' by 0 to 4. The rerun's October
  reading (two language-model readers and a third reading for disagreements; NOT people,
  although the older rows of this file call it a "hand read" and "right to a human
  reader") judged 180 of the 290 undecided answers right in content, 154 of the 244
  on simulate (`reference/delivered_rerun_secondary/secondary.json`, `e4_readings`). (2) *Conversion.* The
  state tool returns every state as a map from each predicate to true or false, in
  functional notation (`on(b2, b1)`), while the answer must list the true predicates only.
  Delivering a trace is therefore a conversion, not a copy, and models make errors in it
  even on five-state traces.
- **Do NOT quote** "the loss is caused by the context window", "more room recovers the
  tool's result", or "the model fails to copy the tool's output" for simulate. The earlier
  smoke table (`reference/d1_smokes_20261027.md`) reports empty answers only.
- **Limits:** 114 to 120 trials per cell from 19 to 20 problems (first problem of each
  domain); the three window sizes are separate jobs weeks apart; not registered; the
  intervals of the three sizes overlap in every cell. The smoke rows are read directly
  (the frozen loader refuses prompts above 16,384 tokens by design) and graded by the
  frozen grader; 46 solve plans were validated live on the laptop.

<!-- BEGIN GENERATED: RQ3-CONTEXT-PILOT (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/rq3_context_pilot.py`. Post hoc pilot, descriptive. Solve and simulate tool trials (plain and steered wordings together) of the first problem of each domain, on the trial keys that the 16K delivered rerun and the 32K and 64K smoke runs of 2026-10-27 all hold; every row graded by the frozen delivered grader. "Tool right" = the right tool returned the right result. "Lost" = of those, the delivered final answer is wrong. Intervals are 95% domain-cluster bootstrap. Separate jobs weeks apart, 20 problems, nothing registered. The categories are those of the frozen readout's E4 (`tools/delivered_rerun/e4.py`); NEEDS_READING marks answers a fixed rule cannot decide. "After also reading one object per line" is a more lenient grade than the frozen one: a trace written as one JSON object per line counts when it equals the oracle trace exactly. Simulate problems left out because a run's plan is not the cached plan: Gemma-26B: barman/p01; Qwen3.5-9B: barman/p01; Qwen3.6-35B: barman/p01. Solve plans validated live for this table: 46.*

| model | task | window | trials | empty final answer | tool right | lost | lost, share of tool right | delivered right | lost, share after also reading one object per line | lost answers by registered category | lost answers that stopped at the output cap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | solve | 16K | 120 | 8 (6.7%) | 120 | 11 | 9.2 [0.0, 21.7] | 90.8 [78.3, 100.0] | – | REFUSED_OR_CLIPPED_FINAL 8; WRONG_FACTS 2; WRONG_WRAPPER 1 | 8 |
| Gemma-26B | solve | 32K | 120 | 4 (3.3%) | 120 | 7 | 5.8 [0.0, 16.7] | 94.2 [83.3, 100.0] | – | NO_FINAL_ANSWER 4; WRONG_FACTS 2; WRONG_WRAPPER 1 | 0 |
| Gemma-26B | solve | 64K | 120 | 1 (0.8%) | 119 | 6 | 5.0 [0.0, 15.3] | 94.2 [83.3, 100.0] | – | WRONG_WRAPPER 4; WRONG_FACTS 2 | 0 |
| Gemma-26B | simulate | 16K | 114 | 49 (43.0%) | 107 | 99 | 92.5 [85.2, 98.1] | 7.0 [1.8, 14.0] | 75.7 [57.4, 90.7] | REFUSED_OR_CLIPPED_FINAL 53; NEEDS_READING 32; WRONG_FACTS 14 | 53 |
| Gemma-26B | simulate | 32K | 114 | 17 (14.9%) | 106 | 91 | 85.8 [76.4, 93.5] | 13.2 [5.3, 21.9] | 72.6 [54.6, 88.0] | NEEDS_READING 54; REFUSED_OR_CLIPPED_FINAL 20; WRONG_FACTS 17 | 26 |
| Gemma-26B | simulate | 64K | 114 | 12 (10.5%) | 105 | 88 | 83.8 [74.0, 92.4] | 14.9 [7.0, 23.7] | 72.4 [56.6, 86.0] | NEEDS_READING 58; WRONG_FACTS 18; REFUSED_OR_CLIPPED_FINAL 12 | 20 |
| Qwen3.5-9B | solve | 16K | 120 | 17 (14.2%) | 120 | 23 | 19.2 [5.0, 36.7] | 80.8 [63.3, 95.0] | – | REFUSED_OR_CLIPPED_FINAL 19; WRONG_FACTS 3; ABRIDGED 1 | 19 |
| Qwen3.5-9B | solve | 32K | 120 | 14 (11.7%) | 120 | 19 | 15.8 [4.2, 30.8] | 84.2 [69.2, 95.8] | – | REFUSED_OR_CLIPPED_FINAL 13; SUMMARY_ONLY 3; WRONG_FACTS 2; NO_FINAL_ANSWER 1 | 13 |
| Qwen3.5-9B | solve | 64K | 120 | 7 (5.8%) | 120 | 20 | 16.7 [4.2, 31.7] | 83.3 [68.3, 95.8] | – | WRONG_FACTS 9; NO_FINAL_ANSWER 6; REFUSED_OR_CLIPPED_FINAL 2; ABRIDGED 2; SUMMARY_ONLY 1 | 6 |
| Qwen3.5-9B | simulate | 16K | 114 | 48 (42.1%) | 85 | 62 | 72.9 [56.3, 88.4] | 20.2 [8.8, 33.3] | 71.8 [54.9, 87.7] | REFUSED_OR_CLIPPED_FINAL 38; WRONG_FACTS 14; NEEDS_READING 10 | 38 |
| Qwen3.5-9B | simulate | 32K | 114 | 16 (14.0%) | 83 | 55 | 66.3 [50.0, 82.1] | 24.6 [13.2, 37.7] | 66.3 [50.0, 82.1] | WRONG_FACTS 29; NEEDS_READING 16; REFUSED_OR_CLIPPED_FINAL 10 | 10 |
| Qwen3.5-9B | simulate | 64K | 114 | 12 (10.5%) | 84 | 58 | 69.0 [52.1, 84.9] | 22.8 [10.5, 36.0] | 69.0 [52.1, 84.9] | WRONG_FACTS 32; NEEDS_READING 17; REFUSED_OR_CLIPPED_FINAL 9 | 9 |
| Qwen3.6-35B | solve | 16K | 120 | 17 (14.2%) | 109 | 22 | 20.2 [6.4, 35.8] | 75.0 [60.0, 88.3] | – | REFUSED_OR_CLIPPED_FINAL 16; WRONG_FACTS 2; WRONG_WRAPPER 2; ABRIDGED 1; SUMMARY_ONLY 1 | 16 |
| Qwen3.6-35B | solve | 32K | 120 | 2 (1.7%) | 105 | 15 | 14.3 [2.9, 28.6] | 78.3 [65.0, 90.0] | – | WRONG_FACTS 9; NO_FINAL_ANSWER 2; SUMMARY_ONLY 2; REFUSED_OR_CLIPPED_FINAL 1; WRONG_WRAPPER 1 | 2 |
| Qwen3.6-35B | solve | 64K | 120 | 1 (0.8%) | 108 | 12 | 11.1 [0.0, 23.7] | 83.3 [72.5, 92.5] | – | WRONG_FACTS 4; SUMMARY_ONLY 4; ABRIDGED 2; NO_FINAL_ANSWER 1; WRONG_WRAPPER 1 | 0 |
| Qwen3.6-35B | simulate | 16K | 114 | 48 (42.1%) | 107 | 69 | 64.5 [45.6, 82.1] | 33.3 [16.7, 51.8] | 60.7 [41.1, 79.8] | REFUSED_OR_CLIPPED_FINAL 53; WRONG_FACTS 8; NEEDS_READING 5; NUMERIC_OMITTED 3 | 53 |
| Qwen3.6-35B | simulate | 32K | 114 | 14 (12.3%) | 112 | 55 | 49.1 [33.6, 64.6] | 50.0 [34.2, 64.9] | 45.5 [29.8, 61.9] | REFUSED_OR_CLIPPED_FINAL 25; WRONG_FACTS 17; NEEDS_READING 8; NUMERIC_OMITTED 5 | 25 |
| Qwen3.6-35B | simulate | 64K | 114 | 7 (6.1%) | 112 | 55 | 49.1 [32.4, 66.1] | 50.0 [33.3, 66.7] | 46.4 [29.7, 63.7] | NEEDS_READING 22; WRONG_FACTS 13; REFUSED_OR_CLIPPED_FINAL 12; NUMERIC_OMITTED 5; ABRIDGED 3 | 23 |
<!-- END GENERATED: RQ3-CONTEXT-PILOT -->

## RQ3 simulate — layout-tolerant re-grade (post hoc) (added 2026-11-22; exploratory; in no tex yet)

How much of the simulate loss of RQ3 is the layout of the answer, on the full delivered
rerun (16K window, all 100 problems)? `tools/reanalysis/rq3_simulate_regrade.py` (rerun:
`python -m tools.reanalysis.rq3_simulate_regrade --numbers`) keeps every frozen grade and
adds, beside it, the reading of `rq3_context_pilot.line_reader_exact`: a trace written one
JSON object per line counts when it equals the answer key's trace exactly. How to read the
block:

- **The frozen column is the record.** It equals the RQ3 cells above (the script halts
  otherwise). The lenient column is post hoc and is quoted only beside the frozen one.
- **What it shows.** The frozen loss of 69.9 to 91.2% becomes 65.9 to 80.5% under the
  line reader: 92 of the 1,266 lost answers are right traces in a layout the frozen
  grader does not read (66 of them Gemma's, 21 the 35B's under the steered prompt). With
  the rows the October readers judged right removed as well (154 in all), it is 65.5 to
  75.5%.
- **What remains at 16K is mostly no room.** Of the 1,174 answers still lost, 843 are a
  final turn that was refused or clipped (99 of these sit on the six ISS-029 problems,
  where no answer could pass). 219 hold a full-length trace in which a step differs; in
  145 of those the facts alone differ and only by the tool's own predicates (a false one
  listed as true, or a true one left out). 95 hold no trace any reader finds, and 17 a
  trace of another length.
- **Do NOT quote** the lenient share without the frozen share; "the simulate loss is a
  formatting artefact" (the line reader moves it by 0 to 13 points); the 145 as "the
  share of conversion errors" of all lost answers (843 answers never got far enough to
  show whether they would convert); the October reading as a human reading (its two
  readers were model agents, with an adjudication); any of these figures for the main
  sweep or for the Claude runs.
- **Limits.** One window size (16K), thinking off, three models. The line reader reads one
  layout; 62 rows the October readers judged right are in other layouts (tables, another
  JSON schema) and stay lost under it. The classes are fixed rules, first match wins; they
  describe the answer and do not show its cause.

<!-- BEGIN GENERATED: RQ3-SIMULATE-REGRADE (do not edit by hand; rerun the generator) -->
*Generated by `tools/reanalysis/rq3_simulate_regrade.py`. **Post hoc and exploratory; the frozen readout is the record and nothing here replaces it.** Delivered rerun, three open models, thinking off, simulate, all 100 problems. "Tool right" = the tool returned the right result (the rows of the frozen readout's E4 cell; the frozen column is recomputed with the frozen functions and equals the filed RQ3 cells, or the script halts). "Lenient" = the answer fails the frozen grader and also fails the line reader, which takes every line that is one JSON object as one step and requires the steps to equal the answer key's trace exactly: lenient about layout, as strict as the frozen grader about content. "Difference" is paired on the same trials. "After the October reading" also removes the rows that the two readers of October (model agents, with an adjudication; not people) judged right in content. Shares in percent with 95% domain-cluster bootstrap percentile intervals (10,000 resamples, seed 20261002).*

#### RQ3 simulate: frozen grade beside the layout-tolerant reading

| model | prompt | trials | tool right | lost, frozen (record) | frozen share | right under the line reader | lost, lenient | lenient share | difference (points) | share after the October reading |
|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | plain | 300 | 272 | 247 | 90.8 [85.4, 95.5] | 35 | 212 | 77.9 [67.5, 87.4] | -12.9 [-18.6, -7.7] | 193: 71.0 [58.2, 82.6] |
| Gemma-26B | steered | 300 | 272 | 248 | 91.2 [86.0, 95.8] | 31 | 217 | 79.8 [67.6, 90.3] | -11.4 [-18.8, -5.3] | 200: 73.5 [60.2, 85.5] |
| Qwen3.5-9B | plain | 300 | 204 | 152 | 74.5 [60.4, 87.7] | 0 | 152 | 74.5 [60.4, 87.7] | +0.0 [+0.0, +0.0] | 147: 72.1 [57.6, 85.9] |
| Qwen3.5-9B | steered | 300 | 261 | 212 | 81.2 [70.5, 90.4] | 2 | 210 | 80.5 [69.7, 89.8] | -0.8 [-1.9, +0.0] | 197: 75.5 [64.0, 86.0] |
| Qwen3.6-35B | plain | 300 | 282 | 197 | 69.9 [56.5, 82.4] | 3 | 194 | 68.8 [55.3, 81.4] | -1.1 [-2.2, +0.0] | 187: 66.3 [52.5, 79.3] |
| Qwen3.6-35B | steered | 300 | 287 | 210 | 73.2 [61.3, 84.2] | 21 | 189 | 65.9 [52.0, 79.1] | -7.3 [-10.9, -3.9] | 188: 65.5 [51.5, 78.9] |

#### What the answers still lost under the lenient reader are

One class per answer, first match wins: *no room left, or empty*; *the tool ran another plan than the answer key's*; *cut at the output cap*; *full-length trace, a step differs*; *trace of another length*; *no trace readable*; *other*. The first two come from the frozen category. "Full-length trace, a step differs" = some reader finds a trace with as many steps as the answer key and at least one step is not equal: an error of conversion or content.

| model | prompt | still lost | no room left, or empty | the tool ran another plan than the answer key's | cut at the output cap | full-length trace, a step differs | trace of another length | no trace readable | other | no room: of which the answer key is another plan's |
|---|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | plain | 212 | 148 (70%) | 0 (0%) | 0 (0%) | 38 (18%) | 5 (2%) | 21 (10%) | 0 (0%) | 18 |
| Gemma-26B | steered | 217 | 151 (70%) | 0 (0%) | 0 (0%) | 35 (16%) | 10 (5%) | 21 (10%) | 0 (0%) | 18 |
| Qwen3.5-9B | plain | 152 | 106 (70%) | 0 (0%) | 0 (0%) | 37 (24%) | 1 (1%) | 8 (5%) | 0 (0%) | 13 |
| Qwen3.5-9B | steered | 210 | 132 (63%) | 0 (0%) | 0 (0%) | 41 (20%) | 1 (0%) | 36 (17%) | 0 (0%) | 15 |
| Qwen3.6-35B | plain | 194 | 151 (78%) | 0 (0%) | 0 (0%) | 35 (18%) | 0 (0%) | 8 (4%) | 0 (0%) | 17 |
| Qwen3.6-35B | steered | 189 | 155 (82%) | 0 (0%) | 0 (0%) | 33 (17%) | 0 (0%) | 1 (1%) | 0 (0%) | 18 |

The last column counts answers on the six problems of ISS-029 (the plan in the prompt is not the answer key's plan, so the tool's own trace is not the answer key's). They are tool-right by the run-time grade, and a copy of the tool's own trace would not pass the delivered grade; all of them are in the no-room class.

#### Sensitivity: without the trials whose tool trace is not the answer key's

The same two shares with those trials left out of the base. "Left out" = tool-right trials in which the trace the tool returned is not the answer key's trace; "of which empty" = their final answer is empty, so the difference of plans changed no grade.

| model | prompt | left out | of which lost | of which empty | tool right | lost, frozen | frozen share | lost, lenient | lenient share |
|---|---|---|---|---|---|---|---|---|---|
| Gemma-26B | plain | 18 | 18 | 18 | 254 | 229 | 90.2 [84.6, 95.0] | 194 | 76.4 [66.0, 85.9] |
| Gemma-26B | steered | 18 | 18 | 18 | 254 | 230 | 90.6 [85.3, 95.3] | 199 | 78.3 [65.9, 89.2] |
| Qwen3.5-9B | plain | 13 | 13 | 13 | 191 | 139 | 72.8 [58.3, 86.4] | 139 | 72.8 [58.3, 86.4] |
| Qwen3.5-9B | steered | 15 | 15 | 15 | 246 | 197 | 80.1 [68.9, 89.5] | 195 | 79.3 [68.2, 88.9] |
| Qwen3.6-35B | plain | 17 | 17 | 17 | 265 | 180 | 67.9 [54.1, 80.7] | 177 | 66.8 [52.9, 79.6] |
| Qwen3.6-35B | steered | 18 | 18 | 18 | 269 | 192 | 71.4 [59.2, 82.5] | 171 | 63.6 [49.3, 76.9] |

#### Inside "full-length trace, a step differs"

"Differs in" = which parts of a step are not equal to the answer key (step numbers, action label, facts = the list of true predicates, numbers). "Conversion only" = facts alone differ, and every listed predicate the answer key does not hold is one the tool's own map holds as false (the tool returns every predicate with true or false; the answer must list the true ones). "Shifted" = every state is right but sits one step early or late.

| model | prompt | answers | differs in (count) | conversion only | facts only: kind (count) | numbers only: kind (count) | shifted by one step |
|---|---|---|---|---|---|---|---|
| Gemma-26B | plain | 38 | numbers 18; facts 17; facts + numbers 2; a fact listed twice 1 | 13 | false listed as true 9; false listed as true, and true omitted 2; lists a predicate the tool's map does not hold 4; true omitted 2 | a number wrong 5; numbers left out 13 | 0 |
| Gemma-26B | steered | 35 | facts 21; numbers 11; facts + numbers 3 | 14 | false listed as true 8; false listed as true, and true omitted 2; lists a predicate the tool's map does not hold 7; true omitted 4 | numbers left out 11 | 0 |
| Qwen3.5-9B | plain | 37 | facts 37 | 34 | false listed as true 13; false listed as true, and true omitted 15; lists a predicate the tool's map does not hold 3; true omitted 6 | – | 0 |
| Qwen3.5-9B | steered | 41 | facts 36; facts + numbers 3; a fact listed twice 1; numbers 1 | 33 | false listed as true 8; false listed as true, and true omitted 18; lists a predicate the tool's map does not hold 3; true omitted 7 | numbers left out 1 | 0 |
| Qwen3.6-35B | plain | 35 | facts 25; numbers 10 | 25 | false listed as true 2; false listed as true, and true omitted 9; true omitted 14 | a number wrong 1; numbers left out 9 | 0 |
| Qwen3.6-35B | steered | 33 | facts 26; numbers 7 | 26 | false listed as true 5; false listed as true, and true omitted 5; true omitted 16 | numbers left out 7 | 0 |

#### Check against the October reading (simulate rows the frozen rules could not decide)

244 rows. Readers' verdict on the content against the line reader's verdict:

| readers: content right? | line reader: right | line reader: not right |
|---|---|---|
| yes | 92 | 62 |
| no | 0 | 90 |
| unclear | 0 | 0 |

Rows the readers judged right that the line reader does not read, by the readers' category: WRONG_WRAPPER 56; ABRIDGED 4; NUMERIC_OMITTED 2.
<!-- END GENERATED: RQ3-SIMULATE-REGRADE -->

## nt-ster H4 — steering falsification control (CLOSED 2026-08-29; IN TEX 2026-09-12/13, `paper/aaai27` `6027d68` + `7c0502a`, pushed + Overleaf `2ab9bb5`)

Provenance for all rows: `reference/ntster_h4_final_readout_20260829.md`.
Design of record: `reference/ntster_h4_prereg.md`. Executed deviations: its §9.1.

**Paper-level branch = PASS** — all six units PASS, all 8 ELIGIBLE task cells
EQUIVALENT. Surface = delivered on **determinate** rows (censored rows excluded and
bounded, §2.3(C)), margin ±5pp, 90% clustered intervals, governing interval = the wider
of the domain (k=20) and size-weighted problem (realized k=220) clusterings.

**REVISED 2026-08-30** after the PR #96 correctness review (prereg §9.2 deviations
3–9): the code was fixed and re-frozen and every figure regenerated. Verdicts
unchanged; every Δ̂, rate and MDE below is the corrected value — the pre-revision
values (−3.03 4B, MDE 6.47–6.80/7.11, factorial +0.83/−0.00, "mechanism VOID",
4B simulate −14.00) are all stale, do not quote them.

| figure | **quote this** | line | do NOT quote |
|---|---|---|---|
| the attribution, matched cell | gemma `validate_plan` `think=off`: **+72.0pp with tools vs +0.63pp [−0.46, +1.73] without** | L64-65 | — *(this is the sentence the control exists to license; bit-identical across the 08-30 revision)* |
| Qwen3.5:4B off | **−1.07 [−2.32, +0.17]**, 60.32 → 58.75% | L36 | −3.03 [−4.83, −1.23] (pre-revision estimator) |
| Qwen3.5:9B off | **+1.25 [+0.01, +2.50]**, 65.58 → 66.71% | L37 | −0.18 [−1.89, +1.52] (pre-revision) |
| Qwen3.5:9B on | **+1.87 [+0.69, +3.06]**, 69.71 → 71.68% | L38 | +1.83 [−0.28, +3.94] (pre-revision); the 08-22 reading — **void**, 0% success |
| gemma4:26b-a4b off | **+0.53 [−0.29, +1.36]**, 77.83 → 78.33% | L39 | +0.52 [−0.95, +1.99] (pre-revision) |
| qwen3.6:35b off | **+0.16 [−0.89, +1.21]**, 78.05 → 77.98% | L40 | +1.34 [−0.40, +3.08] (pre-revision) |
| qwen3.6:35b on | **−0.46 [−1.33, +0.42]**, 83.57 → 83.11% | L41 | +0.49 [−1.37, +2.35] (pre-revision); the 08-22 reading — **void** |
| realized MDE | **5.82–6.25pp** per unit | L21-28 | 6.47–6.80 (stale, and it was wrong even pre-revision — the true pre-revision range was 6.47–7.11) |
| §4(b) factorial interaction | 9B **+8.12 [+4.61, +11.63]** (replicated; Δ_wt +8.54, Δ_nt +1.87, May ref +11.38) · 35b **+2.62 [+0.74, +4.50]** (excludes 0, sign-mismatch vs a −0.11pp May reference; Δ_wt +2.05, Δ_nt −0.47) — clause **DROPS**; matched fixtures **3,765** (9B, 788 dropped) / **4,417** (35b, 143 dropped); per-task validate_plan interaction (descriptive, no clause authority) 9B **+15.01 [+9.01, +21.00]**, 35b **+2.78 [+0.11, +5.44]** — IN TEX 2026-09-13 as the appendix "Within-corpus factorial diagnostic" | L367-368; frozen `ntster_factorial.md` (checkpoint) | +0.83 / −0.00 "neither excludes zero" (pre-revision, censored-as-success on both legs) |
| paper-level branch | **PASS** | L17 | **INCONCLUSIVE** — the 08-22 partial reading, when the two on-mode cells were void |

**Two use constraints.**

- **§5's PASS sentence does NOT carry the "replicated attribution" clause.** 9B now
  fully replicates and both interactions exclude zero, but 35b fails the sign-match half
  of the criterion against an essentially null (−0.11pp) May reference, so the
  pre-registered per-model conjunction is not met and the clause is *removed*, not
  weakened. The corrected factorial is directionally consistent with the attribution,
  which in any case rests on the matched cell above. **Tex wording (Omer, 2026-09-13):**
  the body says "All six pooled units and all eight eligible task cells met the ±5pp
  equivalence criterion; excluded task cells remain unresolved" and "This supports the
  interpretation that steering acts through tool use in the matched Gemma cell" — no
  stronger causal sentence; the 5 + half-width quantity is quoted only as the registered
  threshold for declaring non-equivalence (never as measurement resolution), and no
  sentence says tighter intervals make equivalence harder.
- **The mechanism decomposition is VALID after the 08-30 revision** (the shipped "VOID,
  APPARATUS 13.8–36.0%" was an artifact of reading fields the overlay lacks; true
  APPARATUS = 0.00% everywhere). No label is owed (no unit FAILs); component shares are
  descriptive only — readout §6.

Per-task cells labelled UNINFORMATIVE carry no verdict authority and must not be quoted
as steering effects. No NOT-EQUIVALENT label exists anywhere in the family after the
revision — the shipped 4B `simulate` −14.00 was largely the censoring artifact (true
determinate read −2.43 [−5.33, +0.47], INDETERMINATE).

### Tex cross-check rows (added 2026-09-12, Job 3)

Every figure below now appears in `paper/main.tex` (Results PASS paragraph, Limitations
note, Technical Appendix "The steering control" + `tab:ster-units` / `tab:ster-tasks` /
`tab:ster-drift`) and was not previously pinned in this block. The two appendix tables
were generated programmatically from the frozen report in
`checkpoints/ntster-h4-live/derived_reports.zip` (08-30 revised), not transcribed.

| figure | **quote this** | provenance | do NOT quote |
|---|---|---|---|
| unit anchor → steered, 1 dp (tex tables) | 4B off 60.3 → 58.8 · 9B off 65.6 → 66.7 · 9B on 69.7 → 71.7 · gemma off 77.8 → 78.3 · 35b off 78.0 → 78.0 · 35b on 83.6 → 83.1 | frozen report verdict vector | — |
| the 8 ELIGIBLE task cells (all EQUIVALENT) | 4B off vplan **−1.10 [−2.86, +0.66]**; 9B off vprob **+1.33 [−1.72, +4.39]**, vplan **+0.63 [−1.24, +2.50]**; 9B on vplan **+0.07 [−1.10, +1.23]**; gemma off vprob **−0.50 [−2.88, +1.88]**, vplan **+0.63 [−0.46, +1.73]**; 35b off vprob **+0.83 [−1.36, +3.02]**; 35b on vprob **+1.17 [−0.36, +2.70]** | readout §4; frozen report per-task tables | any UNINFORMATIVE cell as an effect |
| F gate ranges by task (anchor arm, max over 3 paraphrase pairs) | pooled **0.55–2.75**; solve **14.0–31.0** (UNINFORMATIVE ×6); simulate **5.56–36.33** (×6); validate_domain **5.00–14.17** (×6); validate_problem 1.0–6.5 (UNINFORMATIVE in 4B off 5.50, 9B on 6.50); validate_plan 0.6–2.5 (35b off/on UNINFORMATIVE by anchor > 90%: 90.5 / 92.6) | `ntster_f_gate.md` (checkpoint) | — |
| largest per-task movements (UNINFORMATIVE, no authority; tex quotes them as such) | gemma off simulate **+9.00 [+4.68, +13.32]**, F 36.33 (tex +9.0) · 9B on validate_domain **+10.28 [+3.30, +17.26]**, F 6.67 (tex +10.3) | readout §4 | either as a steering effect |
| censoring / pairing per unit | censored rows **105–152 (1.2–1.7%)**, all simulate; matched pairs **4,466–4,500** of 4,560 | readout §1 | — |
| drift check, Aug anchor − May canonical, think=off, 4 tasks, n=4,260/side | pooled 4B **+0.2** · 9B **+0.1** · gemma **+1.0** · 35b **+0.2**; per task 4B −1.0/+0.0/−0.5/+0.5, 9B −0.3/−0.3/+0.7/+0.1, gemma +2.7/+1.4/+2.8/+0.5, 35b +1.3/**+6.7**/−1.2/−0.4 (solve/vd/vp/vplan); 35b vd +6.7 sits at F 9.17 | readout §5; **recomputed 2026-09-12** from the checkpoint overlay + `results/sweep5v2-live` no-tools cells — matches to the decimal | simulate drift (unmeasurable, 500-char May storage) |
| void on-mode arm (parser ON, job 20392801) | **9,120/9,120** (35b) and **3,822/3,824** (9B) rows empty response; ~12,960 tok/row (tex "about 13K") | readout §2.1; prereg §9.1 dev 2 | — |
| on-mode rerun (parser OFF) vs June prediction | 9B **8.2% empty / 69.1% success** (pred. 8.8 / 68.4); 35b **3.9% / 82.5%** (pred. 4.1 / 82.0); format_parse_fail **0.0%** on all three validate_* tasks in all 4 on-mode arms | readout §2.1–2.2 | — |
| roster-gap with-tools think=off steering (tl-ster − tl-neut, mechanism layer, canonical) | 0.8B **+0.0** pooled · 4B **+6.9** pooled / **+9.6** vplan · 9B **+2.5** · gemma +47.4 / **+72.0** vplan · 35b +14.8 | prereg §9.1 dev 1; `archive/ntster/ntster_h4_partial_readout_20260822.md` §3 (deleted 2026-10-10, `git show 1fee730:<path>`); **recomputed 2026-09-12** from `results/sweep5v2-live/*_off_tools_all_minimal` — matches | — |

## Abstract — the four figures + the scale clause (verified 2026-09-18 for `paper/aaai27` `b27ef23` + `b045f07`)

The abstract quotes exactly four numbers, one per role of the two-gate abstraction
(`reference/title_abstract_candidates.md` §5). Each was re-derived this session; nothing else
may be added to the abstract without a row here.

| abstract sentence | **quote this** | derivation | do NOT quote |
|---|---|---|---|
| frontier plan generation, unaided → with tool | **22–29% → 95%** (both tiers, delivered) | `pooled_e2e_table.csv`: solve tl-neut ok_strict 95/100 Sonnet and Haiku; nt-neut Haiku 22/100, Sonnet 86/300 = 28.7. Caveat (2026-11-09): the unaided figures use the stored grade, which the pyval case fault (ISS-027) lowers; under VAL they read Haiku 25.0 and Sonnet 32.7 (post hoc, "VAL on the Claude solve plans"). The 95% tool side agrees with VAL on every plan | the open-weight "+66 to +73 pp" lift (tool-verified; delivered cells censored/UNDECIDED) |
| invocation on plan checking, merely available → steered; correct when it calls | **21% → 94%; 99%** | `sweep5v2-live/slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal/trials.jsonl`, validate_plan: called (`tool_selected`) 622/3000 = 20.7% (v11–13) vs 2808/3000 = 93.6% (v14–16); P(ok \| called) 617/622 = 99.2% (98.9% steered); 0 successes without a call | "−67 pp" as a success drop (mechanism layer; delivered ⟨6.6, 99.6⟩ UNDECIDED) |
| delivery gap by answer length, both frontier tiers | **≈0 on verdicts, 5 pp on plans, >33 pp on trajectories** | overlay table: vd/vp/vplan delivered vs tool-verified differ by ≤0.1 pp; solve 95 vs 100 = +5.0 both tiers; simulate Sonnet ⟨49, 62⟩ vs 99 (37–50), Haiku ⟨52, 64⟩ vs 97 (33–45) | any frontier simulate delivered *point* |
| PlanBench obfuscated (Mystery) benchmark, without → with tools | **0 → 72%** | `verify_promotion.py` ALL CHECKS PASS: NT 0/600, WT 431/600 = 71.8 [68.1, 75.3] | clean WT 69.7 (last-attempt) |
| scale clause (in the abstract since `b045f07`, after the PlanBench sentence) | **273,600 trials, five open-weight models, two corpora, anonymized domains as the contamination control** | Corpus scale block; advisor recommendation in paper_notes 2026-09-18 | 227k; "seven models"; any wording that folds in the 16,720 frontier trials |

## Corpus scale

| figure | **quote this** | provenance | do NOT quote |
|---|---|---|---|
| open-weight trial count | **273,600** across two corpora, **five** open-weight models | `reference/title_abstract_candidates.md` §4 (L324) | **227k** — does not reproduce from disk; never pair any total with "seven models" |

`reference/journal_decisions_memo.md` still uses 227k in three places (§5, §8, and its revision
line); the memo carries a correction banner at its head. 273,600 = 5 models × 2
reasoning modes × 3 arms × 4,560 × 2 corpora.

## Run and query dates (added 2026-11-22; in tex, Models and Serving)

| what | dates | source |
|---|---|---|
| main sweep, canonical and renamed corpora (40 cells) | jobs **2026-05-24 to 2026-06-02** | `reference/serving_env_20260913.md` §2 |
| delivered rerun | **2026-10-03 to 2026-10-09** | run stamps in `results/delivered-rerun/*/summary_*.json`; `reference/delivered_rerun_prereg.md` §8 (freeze 10-03) and §8c (last cell completed 10-09) |
| Claude, unaided (Sonnet and Haiku canonical, Sonnet renamed) | queried **2026-06-25** | run stamps in `results/{sonnet,haiku}-frontier/sweep5v2` and `sonnet-frontier/sweep6`. The second stamp there, 2026-07-15, is a re-grade from the stored batch output, not a new query (`CHANGELOG.md` 2026-07-15) |
| Claude, with tools (both models); Haiku on the renamed corpus | queried **2026-07-12** | run stamps in `results/*-frontier/sweep5v2-with-tools`, `haiku-frontier/sweep6*` |
| Claude, PlanBench | **2026-08-01 to 2026-08-06** | `reference/planbench_wt_results_20260803.md` (with-tools run 08-01/02; the no-tools completion run 08-06) |
| Claude, output-budget probe | **2026-09-12** | `created_at` in `results/*-frontier/*budget64k/run_manifest.json` |

## Serving environment (audited 2026-09-13; tex `paper/aaai27` `4eb4751`, pushed 2026-09-14, Overleaf `d884bd3`)

Provenance for all rows: `reference/serving_env_20260913.md`.

| figure | **quote this** | do NOT quote |
|---|---|---|
| vLLM | **0.20.2** — container `vllm/vllm-openai:v0.20.2`, PyTorch 2.11.0+cu130, CUDA 13.0 runtime, Apptainer 1.4.5 | 0.22.0 as "the" version |
| host | Rocky Linux 9.7, kernel 5.14.0-611, NVIDIA driver 595.58.03 (driver CUDA API 13.2) | — |
| GPU / job | NVIDIA RTX 6000 Ada Generation **48 GB**, one per job, 6 CPU cores, 48 GB RAM | "48 GB and 96 GB" (pre-09-13 tex; no paper corpus ran on the 96 GB card) |
| cells served by vLLM 0.22.0 (2026-05-29 cache drift) | canonical: Qwen3.5-**4B off/on + 9B off/on** with-tools (4 cells, 36,480 trials); anonymized: Qwen3.5 0.8B off/on, 4B off/on, 9B off with-tools, 9B on for its first 7,240 rows, Gemma on with-tools. All no-tools, all Gemma/Qwen3.6 canonical, all later corpora: 0.20.2 | the 2026-05-31 "five cells, zero mixed" list (memory-only, superseded) |
| parser identity across 0.20.2 → 0.22.0 | `qwen3xml_tool_parser.py` and `qwen3_reasoning_parser.py` **byte-identical** (GitHub blob SHAs); `gemma4_tool_parser.py` **changed** (affects only the unquoted anon Gemma-on cell) | — |
| 0.20.2-vs-0.22.0 rerun check (Qwen3.5-0.8B off with-tools canonical, 9,120 vs 9,120) | pooled **+0.43 pp [−0.86, +1.71]**; 10/10 task×arm cells CI-overlapping; two 0.22.0 repeats differ by as much | as proof for the 4B/9B cells beyond "within run-to-run noise" |

## Single-tool suite — per-cell figures (generated, not transcribed)

The Job 2 block above pins every single-tool figure the prose quotes by value. The
remaining per-cell numbers (each model × task × arm × reasoning-mode success rate,
censoring bound and tool-verified count) are **deliberately not pinned row-by-row
here**: the tex draws them from one artifact and they are regenerated from it, never
copied from a deck, memo or earlier draft. Exception since 2026-10-27: the headline
models' thinking-off mechanism-layer and unaided cells are pinned in the Study 1 block,
generated from the scripts named there.

| what | **the one source** | how the tex gets it | do NOT quote |
|---|---|---|---|
| delivered rates (`ok_strict`), censoring bounds `⟨low, high⟩`, tool-verified counts (`tv_ok/tv_n`), every corpus × bank × arm | `results/derived/e2e_overlay/pooled_e2e_table.csv` (460 rows, 2026-09-12; the 2026-07-17 table, kept in `checkpoints/e2e-overlay/derived_reports.zip`, has 456), written by `.claude/skills/analyzer/scripts/e2e_pooled.py` over `results/derived/e2e_overlay/`; the paper's open-roster cells are the `sweep5v2-live` (+ `sweep6-live` twin) rows: `bank=neut` for arms `nt-neut` / `tl-neut`, `bank=ster` for arm `tl-ster` | figures: `paper/figures/make_paper_figures.py`, which reads the overlay JSONL through `e2e_overlay.load_e2e_cells`, the same aggregator used to generate the CSV; prose ranges and tables: `/verify-claims` against the same CSV | any per-cell number from `results/sweep5-cluster-20260530` (stale mirror), from the RQ decks (tool-verified surface, pre-reframe), or from `summary_*.json` `success_rate` (harness surface, not delivered) |
| availability verdicts (FAVORABLE / AGAINST / UNDECIDED), think=off, 25 cells | `reference/job2_delivered_reframe_worknote.md` §2 (the table) + §6 (the verbatim script that recomputes it from the CSV; rerun with `Z *= √2.7` for the design-effect check) | the scorecard verdict column and the "13/25 UNDECIDED" row above | the memo's 2/25 (mode-pooled) |
| invocation (CALL) rates | computed from the canonical `trials.jsonl` (`tool_selected` / `delegated` flags) by the figure generator; storage-exact in every corpus. The headline open-model rates, with domain-clustered intervals, are pinned in the Study 1 block (T2, T3) | funnel figure, mechanism-layer prose | the generator's Wilson interval as the uncertainty of a Study 1 rate (Study 1 block, "Intervals") |

Rule of thumb: a single-tool number that is not in the Job 2 block is re-derived from
the CSV (the §6 script or `/verify-claims`), not searched for in the docs.
