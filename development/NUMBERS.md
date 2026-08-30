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

*Last refreshed: 2026-08-29.*

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
| simulate, no-tools | **[0, 100] — 100% censored**, both models | any point estimate |
| validation tasks (vd/vp/vplan) | gap ≈0.0pp; delivered ≈ tool-verified | — |

The retracted 13.5 / 0.0 pair is the single most dangerous stale number in the tree:
it was published in earlier drafts before the overlay bug was found. Anything quoting
a frontier solve or simulate figure below ~90 / outside those bands is pre-retraction.

## nt-ster H4 — steering falsification control (CLOSED 2026-08-29)

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
| §4(b) factorial interaction | 9B **+8.12 [+4.61, +11.63]** (replicated) · 35b **+2.62 [+0.74, +4.50]** (excludes 0, sign-mismatch vs a −0.11pp May reference) — clause **DROPS** | L367-368 | +0.83 / −0.00 "neither excludes zero" (pre-revision, censored-as-success on both legs) |
| paper-level branch | **PASS** | L17 | **INCONCLUSIVE** — the 08-22 partial reading, when the two on-mode cells were void |

**Two use constraints.**

- **§5's PASS sentence does NOT carry the "replicated attribution" clause.** 9B now
  fully replicates and both interactions exclude zero, but 35b fails the sign-match half
  of the criterion against an essentially null (−0.11pp) May reference, so the
  pre-registered per-model conjunction is not met and the clause is *removed*, not
  weakened. The corrected factorial is directionally consistent with the attribution,
  which in any case rests on the matched cell above.
- **The mechanism decomposition is VALID after the 08-30 revision** (the shipped "VOID,
  APPARATUS 13.8–36.0%" was an artifact of reading fields the overlay lacks; true
  APPARATUS = 0.00% everywhere). No label is owed (no unit FAILs); component shares are
  descriptive only — readout §6.

Per-task cells labelled UNINFORMATIVE carry no verdict authority and must not be quoted
as steering effects. No NOT-EQUIVALENT label exists anywhere in the family after the
revision — the shipped 4B `simulate` −14.00 was largely the censoring artifact (true
determinate read −2.43 [−5.33, +0.47], INDETERMINATE).

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
