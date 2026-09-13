# NUMBERS.md — the one lookup before you quote a figure

**Purpose.** Several headline figures exist at more than one value across the docs,
because a reading was revised after the first write-up. Every stale value is
banner-marked where it lives, but that means trusting a banner in each of six files.
This table replaces that: **one row per figure, the frozen value, where it is
provenanced, and the readings it replaces.**

**Rule.** Before any figure enters paper prose, check it here. If it is not in this
table, run `/verify-claims` against the canonical corpora
(`results/sweep5v2-live` + `*_sweep6`; **never** `results/sweep5-cluster-20260530`,
a stale partial mirror). Every value below was re-verified against its provenance
file on 2026-08-29.

*Last refreshed: 2026-09-13 (nt-ster block: tex cross-check rows + factorial row extended as Job 3 landed and was pushed; frontier budget probe row frozen).*

## PlanBench — with-tools arm (CLOSED 2026-08-06/11; Act 4)

Provenance for all rows: `planbench/planbench_wt_results_20260803.md`.
Binding constraints on use: `planbench/PLANBENCH_WT_FINAL_PHASE_HANDOFF.md`.

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

## Frontier e2e — delivered vs tool-verified

Provenance: `sonnet_wt_vs_haiku_e2e_memo.md` (canonical corpus, variant 11,
`e2e_strict`). **Delivered is the primary surface**; tool-verified is the mechanism
layer (journal memo §3 / D-J2).

| figure | **quote this** | do NOT quote |
|---|---|---|
| solve delivered, with tools | **95.0** [88.8, 97.8] — *both* Sonnet and Haiku; tool-verified 100.0, gap **+5.0pp** | **13.5% — RETRACTED**, an overlay grading artifact |
| simulate delivered, with tools | **bounds, not points**: Sonnet **[49.0, 62.0]**, Haiku **[52.0, 64.0]** | **0% — RETRACTED**, same artifact |
| simulate delivered↔tool-verified gap | ≈37–50pp Sonnet · ≈33–45pp Haiku (length-driven) | a single pooled "≈35–45" figure |
| simulate, no-tools | **bounds after 07-15 de-censoring** (pooled table 07-17): Sonnet canonical ⟨41.7, 61.3⟩ (c59/300), anon ⟨36.3, 57.7⟩ (c64/300); Haiku canonical ⟨38, 68⟩ (c30/100) | **[0, 100]** (pre-de-censoring memo row) and **45.0 / 38.3 exact points** (in the pre-reframe tex; reproduce from no sanctioned artifact — see `job2_delivered_reframe_worknote.md` §3(e)) |
| validation tasks (vd/vp/vplan) | gap ≈0.0pp; delivered ≈ tool-verified | — |

The retracted 13.5 / 0.0 pair is the single most dangerous stale number in the tree:
it was published in earlier drafts before the overlay bug was found. Anything quoting
a frontier solve or simulate figure below ~90 / outside those bands is pre-retraction.

## Job 2 — the delivered surface (batches 1+2, 2026-09-07/08)

Provenance: `job2_delivered_reframe_worknote.md` §2 (verdict table, derived from
`results/derived/e2e_overlay/pooled_e2e_table.csv`, 2026-07-17) and §8 (batch-2
tables). Tex: `paper/aaai27` `125cc7a` + `dbea3d7` (both UNPUSHED, review gate). Notation: Wilson `[a, b]`; censoring bounds `⟨a, b⟩`, never resolved.

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
| frontier budget probe (RATIFIED 2026-09-12; in tex 5466cb6, Overleaf d922237) | Sonnet: LEN-FIT **16/25** (64.0% [44.5, 79.8]) vs ET-FAIL **7/19** (36.8% [19.1, 59.0]), one-sided Fisher **p = 0.069** → PARTIAL (criterion not met); Haiku: **12/17** (70.6% [46.9, 86.7]) vs **1/12** (8.3% [1.5, 35.4]), **p = 0.0011** → H1; Haiku DECLINE **0/14**; delivered at 64K WT/NT: Sonnet **70 [60.4, 78.1] / 44 [34.7, 53.8]** (Δ +26 pp), Haiku **65 [55.3, 73.6] / 58 [48.2, 67.2]** (Δ +7 pp); tool-arm final turns at 64,000: **0** both tiers (NT: 1 Sonnet, 2 Haiku); censored at 262,144 chars: 0; cost **$40.68**; reference anatomy Sonnet 49/25/4/0/0/3/19/0, Haiku 52/17/1/1/2/14/12/1; canonical cells ⟨49, 62⟩ / ⟨52, 64⟩ UNCHANGED | the pre-retry readout (identical counts, superseded); the 65,536 budget and $217 cap; any pooling of probe rows with canonical cells |

## nt-ster H4 — steering falsification control (CLOSED 2026-08-29; IN TEX 2026-09-12/13, `paper/aaai27` `6027d68` + `7c0502a`, pushed + Overleaf `2ab9bb5`)

Provenance for all rows: `ntster_h4_final_readout_20260829.md`.
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
| roster-gap with-tools think=off steering (tl-ster − tl-neut, mechanism layer, canonical) | 0.8B **+0.0** pooled · 4B **+6.9** pooled / **+9.6** vplan · 9B **+2.5** · gemma +47.4 / **+72.0** vplan · 35b +14.8 | prereg §9.1 dev 1; `archive/ntster/ntster_h4_partial_readout_20260822.md` §3; **recomputed 2026-09-12** from `results/sweep5v2-live/*_off_tools_all_minimal` — matches | — |

## Corpus scale

| figure | **quote this** | provenance | do NOT quote |
|---|---|---|---|
| open-weight trial count | **273,600** across two corpora, **five** open-weight models | `title_abstract_candidates.md` §4 (L324) | **227k** — does not reproduce from disk; never pair any total with "seven models" |

`journal_decisions_memo.md` still uses 227k in three places (§5, §8, and its revision
line); the memo carries a correction banner at its head. 273,600 = 5 models × 2
reasoning modes × 3 arms × 4,560 × 2 corpora.

## Not yet in this table

- Single-tool suite headline numbers: still to be pinned as Job 2 writes. Use
  `/verify-claims` per figure until they land here.
