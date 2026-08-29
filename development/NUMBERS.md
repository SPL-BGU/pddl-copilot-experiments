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
EQUIVALENT. Surface = delivered, margin ±5pp, 90% domain-clustered intervals, governing
interval = the wider of the domain (k=20) and problem (k=100) clusterings.

| figure | **quote this** | line | do NOT quote |
|---|---|---|---|
| the attribution, matched cell | gemma `validate_plan` `think=off`: **+72.0pp with tools vs +0.63pp [−0.46, +1.73] without** | L51-52 | — *(this is the sentence the control exists to license)* |
| Qwen3.5:4B off | **−3.03 [−4.83, −1.23]**, 61.10 → 59.23% | L23 | — |
| Qwen3.5:9B off | **−0.18 [−1.89, +1.52]**, 66.18 → 67.24% | L24 | — |
| Qwen3.5:9B on | **+1.83 [−0.28, +3.94]**, 70.04 → 72.04% | L25 | the 08-22 reading of this cell — it was **void**, 0% success, empty text |
| gemma4:26b-a4b off | **+0.52 [−0.95, +1.99]**, 78.16 → 78.64% | L26 | — |
| qwen3.6:35b off | **+1.34 [−0.40, +3.08]**, 78.33 → 78.20% | L27 | — |
| qwen3.6:35b on | **+0.49 [−1.37, +2.35]**, 83.75 → 83.31% | L28 | the 08-22 reading — **void**, same cause |
| realized MDE | **6.47–6.80pp** per unit | L37 | — |
| §4(b) factorial interaction | 9B **+0.83 [−1.98, +3.64]** · 35b **−0.00 [−2.21, +2.21]** — neither excludes 0 | L365-366 | the domain-only intervals (+1.97 / +1.71); §3.3 takes the **wider** clustering |
| paper-level branch | **PASS** | L17 | **INCONCLUSIVE** — the 08-22 partial reading, when the two on-mode cells were void |

**Two use constraints, both pre-registered.**

- **§5's PASS sentence does NOT carry the "replicated attribution" clause.** The §4(b)
  factorial did not meet its criterion, so the clause is *removed*, not weakened. That is
  a null on an underpowered diagnostic — gemma, which owns the +72pp, has no `think=on`
  no-tools leg and cannot appear in it at all — and it is **not** evidence against the
  attribution, which rests on the matched cell above.
- **The mechanism decomposition is VOID in all six cells** (APPARATUS 13.8–36.0% per arm
  against a 1% threshold), so no §3.7 component number may be quoted.

Per-task cells labelled UNINFORMATIVE carry no verdict authority and must not be quoted
as steering effects — this includes 4B `simulate` −14.00 [−19.97, −8.03], the family's
only NOT-EQUIVALENT cell, whose own paraphrase noise floor is 12.0pp.

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
