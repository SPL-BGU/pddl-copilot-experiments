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

*Last refreshed: 2026-10-27 (VAL cross-check block, plan step C1; Study 1 block: main-sweep calling, tool-verified, unaided and contamination figures, the clustered tests and the mixed-model refit, and the replication table; plan step C2). Before that: 2026-10-09 (delivered-rerun readout block). Before that: 2026-10-03 (PlanBench equivalence + post hoc regrade rows; consistency-read figures; Gemma-prefix warning). Before that: 2026-09-18 (doc cleanup: provenance paths repointed after the moves, the note above added, the budget-probe row now names its readout; no figure changed). Earlier the same day (abstract cross-check block added: the four abstract figures + the Gemma invocation counts, verified for `paper/aaai27` `b27ef23`). 2026-09-14 (serving-environment block: tex pushed + Overleaf-synced, disclosure kept per Omer). 2026-09-13 (housekeeping: the "Single-tool suite — per-cell figures" block replaces the "to be pinned as Job 2 writes" placeholder; Job 2 tex note updated to pushed. Earlier the same day — nt-ster block: tex cross-check rows + factorial row extended as Job 3 landed and was pushed; frontier budget probe row frozen).*

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
| frontier delivered cost-of-pass, solve | Sonnet **3.1×** (18.6K vs 6.0K tokens/pass); Haiku **6.1×** (48.5K vs 8.0K) | — |
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

**Warning (2026-10-02).** `pddl_eval/scoring.py` on `harness/delivered-rerun` (PR #113) strips a leaked Gemma channel prefix before extraction. The pinned `tools/e2e_regrade.py` imports those functions, so re-running it on the canonical Gemma tool cells now gives different delivered solve numbers from the frozen rows in this file. The frozen rows stay; any regenerated Gemma figure is a new reading and needs its own row.

## Study 1 — main sweep figures (added 2026-10-27; in no tex yet)

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
| frontier plan generation, unaided → with tool | **22–29% → 95%** (both tiers, delivered) | `pooled_e2e_table.csv`: solve tl-neut ok_strict 95/100 Sonnet and Haiku; nt-neut Haiku 22/100, Sonnet 86/300 = 28.7 | the open-weight "+66 to +73 pp" lift (tool-verified; delivered cells censored/UNDECIDED) |
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
| delivered rates (`ok_strict`), censoring bounds `⟨low, high⟩`, tool-verified counts (`tv_ok/tv_n`), every corpus × bank × arm | `results/derived/e2e_overlay/pooled_e2e_table.csv` (460 rows, 2026-07-17), written by `.claude/skills/analyzer/scripts/e2e_pooled.py` over `results/derived/e2e_overlay/`; the paper's open-roster cells are the `sweep5v2-live` (+ `sweep6-live` twin) rows: `bank=neut` for arms `nt-neut` / `tl-neut`, `bank=ster` for arm `tl-ster` | figures: `paper/figures/make_paper_figures.py`, which reads the overlay JSONL through `e2e_overlay.load_e2e_cells`, the same aggregator used to generate the CSV; prose ranges and tables: `/verify-claims` against the same CSV | any per-cell number from `results/sweep5-cluster-20260530` (stale mirror), from the RQ decks (tool-verified surface, pre-reframe), or from `summary_*.json` `success_rate` (harness surface, not delivered) |
| availability verdicts (FAVORABLE / AGAINST / UNDECIDED), think=off, 25 cells | `reference/job2_delivered_reframe_worknote.md` §2 (the table) + §6 (the verbatim script that recomputes it from the CSV; rerun with `Z *= √2.7` for the design-effect check) | the scorecard verdict column and the "13/25 UNDECIDED" row above | the memo's 2/25 (mode-pooled) |
| invocation (CALL) rates | computed from the canonical `trials.jsonl` (`tool_selected` / `delegated` flags) by the figure generator; storage-exact in every corpus. The headline open-model rates, with domain-clustered intervals, are pinned in the Study 1 block (T2, T3) | funnel figure, mechanism-layer prose | the generator's Wilson interval as the uncertainty of a Study 1 rate (Study 1 block, "Intervals") |

Rule of thumb: a single-tool number that is not in the Job 2 block is re-derived from
the CSV (the §6 script or `/verify-claims`), not searched for in the docs.
