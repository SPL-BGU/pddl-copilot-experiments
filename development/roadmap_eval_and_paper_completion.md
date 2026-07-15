# Roadmap — remaining actions to close the evaluation phase and the paper

**Date:** 2026-07-15 (written after the NT de-censor + simulate-floor retraction landed).
**Deadline context:** AAAI-27 Main abstracts **Jul 21** (6 days), full **Jul 28** (13 days);
per the 2026-06-27 note AAAI-27 may no longer be the hard target (journal pivot possible) —
that call is D1 below and it sequences everything else.

## Already DONE (don't re-plan)

- Frontier arm complete: Haiku NT+WT both corpora, Sonnet NT both + WT canonical
  ($167.4/$238 spent, ~$70.6 left). Sonnet-WT-anon deliberately skipped — don't reopen.
- E2E overlay D1–D9 + Phase 5 analyzer; pooled table regenerated (PROVISIONAL only for
  iss024d cells).
- NT snapshot de-censor (2026-07-15, $0): all three 500-cap NT corpora re-graded from raw
  batch dirs; NT simulate determinate; contamination null extends to delivered simulate.
- Decoupled-budget line complete + its paper retraction executed (`paper/aaai27` commits
  `4b9a516` frontier fix + `1ac21f4` sole-source-floor retraction, Overleaf-synced).
- Iter-1 CLOSE-NOW writing batch (landed 2026-06-18) except the residuals listed in P2.

---

## Track E — evaluation phase, remaining

**E1. ISS-024(d) endgame (cluster; VPN + ping first). The only substantive
evaluation work left before the paper's with-tools numbers are final.**
1. Sync `results/slurm_vllm_*_iss024d-e2e/`: 4B (complete, unsynced), 9B + gemma
   (72h wall from 07-11 ended ~07-14 — likely complete; post-mortem exit codes).
2. `tools/e2e_regrade.py` over the synced cells (16K → exact e2e).
3. `tools/iss024d_parity.py` on the complete 25-cell table (prereg locked: gemma
   control first, TOST ±5pp, ≥18/20 rule; no headline use before this).
4. Resolve the early red flag: 35b solve Δ −11.3pp fails the gross guard
   (truncation-driven, parser-off mechanism, v12/v13-concentrated). If it
   generalizes, prereg rule 4 applies (separate-apparatus replication labeling).
5. Un-PROVISIONAL the pooled e2e table; merge `feat/e2e-scoring-overlay` → main.

**E2. Not gating the paper (park or run in parallel — see D3/D4):**
- PlanBench frontier: Haiku NT responses on disk since 06-22; grading needs Linux
  VAL (local Docker try = VPN-free) + the WT backend (adapter over
  `frontier_runner.py`). Paper cites PlanBench as Future Work only.
- ISS-024(b) `guided_json` enforcement fix (open-roster generation apparatus).
- System-prompt-level steering reframe (frontier memory: "still open").
- Stronger contamination design for the one flagged cell (frontier simulate
  −6.7pp drift, CIs overlap).

## Track P — paper write-down, remaining

**P1. The delivered-vs-tool-verified integration — the one substantive paper
change left, GATED on E1.** Omer's 07-11 decision: the primary surface for
tool-lift claims becomes response-graded e2e; tool-verified stays as the
mechanism layer. D-N4 answer: corpora per claim — with-tools exact e2e from
iss024d (if parity passes), tool-verified from sweep5v2-live, gap computed
paired within iss024d. Includes the frontier transcription-gap results (solve
+5pp both tiers; simulate ≈35–50pp, length-driven; memo
`sonnet_wt_vs_haiku_e2e_memo.md`) and the de-censored NT delivered columns.
Scope decision = D2.

**P2. Independent of E1 — can land now (small):**
- Fig 3 `token_quadrant` log-x tick rendering (analyzer regeneration; iter-1
  residual).
- "Limited prompt set" exact ratio vs the earlier Copilot (extract the prompt
  count from arXiv:2509.12987 — our own prior version).
- Consistency pass over abstract/intro after the two 07-15 claim batches.

**P3. Camera-ready only:** confirmatory GLMM re-fit non-VI (Laplace/MCMC or
statsmodels); code release at publication.

**External gates:** advisor cost verdict (blocks the next cost-phase step, not
the current text); coauthor review on Overleaf.

---

## Decisions (annotate inline)

**D1 — Venue call.** AAAI-27 (abstract Jul 21 / full Jul 28) or pivot? If AAAI-27:
E1 must happen this week (VPN), and P1 likely compresses to whatever parity
verdict exists by ~Jul 24 (fallback: ship with the surface-disclosure framing now
in the tex and keep tool-verified as the quoted with-tools surface). If pivot:
E1→P1 run at natural pace and P1 becomes the full reframe.

> ANSWER:

**D2 — P1 scope when it runs.** (a) Full reframe: e2e_strict becomes the quoted
with-tools number everywhere (scorecard, tables, discussion), tool-verified moves
to the mechanism/decomposition layer; or (b) additive: keep current tables, add a
delivered-answer subsection + table (frontier + iss024d) and the "delegation vs
delivered" discussion. (b) is smaller and reviewer-safe; (a) matches the 07-11
decision most literally.

> ANSWER:

**D3 — PlanBench now or after submission?** The Docker-VAL grading of the on-disk
Haiku NT responses is VPN-free and cheap; the WT backend is ~a day of dev + API
spend from the $70.6 remainder. Run in parallel now, or park until the paper is
out?

> ANSWER:

**D4 — The other parked items** (ISS-024b guided_json fix · steering reframe ·
stronger contamination probe): keep all three parked as Future Work, or promote
any into the evaluation phase?

> ANSWER:
