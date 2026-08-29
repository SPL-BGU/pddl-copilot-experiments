# Roadmap — remaining actions to close the evaluation phase and the paper

> **SUPERSEDED as a status and schedule doc.** The AAAI-27 deadline framing below
> ("6 days", "13 days") expired in July 2026, and AAAI-27 is no longer a hard target
> (journal pivot; see `journal_decisions_memo.md`). For what is actually left, start at
> **`remaining_work_20260811.md`**. Retained for its D1-D4 decision record, which is
> still binding.

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

> STATUS 2026-07-17: steps 1–4 DONE + step 5 first half. All 5 cells synced
> (9,120 trials each, exit codes clean), regraded, parity run: **job-level
> parity FAILS** (gemma floor 5.3pp; Qwen 7/20 pass, max |Δ| 11.3pp; solve red
> flag generalizes, truncation/parser-off mechanism). Prereg rule 4 binds:
> separate-apparatus replication labeling; the "iss024d as headline surface"
> branch of D-N4 is closed. Pooled table regenerated with the verdict banner.
> Remaining: merge `feat/e2e-scoring-overlay` → main (Omer's call on timing).
> Details: CHANGELOG 2026-07-17 + results/derived/iss024d_parity_report.md.
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

> STATUS 2026-07-23: ALL THREE DONE (commit `afc92b6` on `paper/aaai27`,
> Overleaf-synced `c8c8245`). Fig 3 was already fixed in `4e9a308` (verified by
> render — the roadmap item was stale); the prompt-set ratio landed in the Tool
> Suite subsection (cite `benyamin2025copilot`, 250 queries vs 4,560/cell, ~18x);
> the consistency pass found one straggler — the abstract's unscoped "cannot be
> done without the tool" — now scoped to the deployed apparatus, matching the
> intro. Clean compile, 0 undefined refs.
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

> ANSWER (Omer, 2026-07-15, stated in session): leaning JOURNAL — limited time for
> the thesis until September (reserves duty), so the Jul 21/28 AAAI crunch is out
> of step with the real constraint. Implications: skip the abstract-deadline
> compression; run E1 when the VPN is naturally back; P1 defaults to the full
> reframe (D2 option a viable); schedule paper work to minimize Omer's hands-on
> time (agent-executable batches, Omer decides/reviews). Journal-fit notes exist
> at `.local/kbs-journal-fit.md`. Not yet a hard commitment — revisit with
> advisors before dropping AAAI-27 formally.

**D2 — P1 scope when it runs.** (a) Full reframe: e2e_strict becomes the quoted
with-tools number everywhere (scorecard, tables, discussion), tool-verified moves
to the mechanism/decomposition layer; or (b) additive: keep current tables, add a
delivered-answer subsection + table (frontier + iss024d) and the "delegation vs
delivered" discussion. (b) is smaller and reviewer-safe; (a) matches the 07-11
decision most literally.

> ANSWER (Omer, 2026-07-24, in session): (a) FULL REFRAME — same ruling as
> `journal_narrative_proposal.md` D-J2 (one answer covers both, as anticipated).
> Full spec + per-corpus quoting rules + prohibited-claims list:
> `development/journal_decisions_memo.md` §3. Executable with zero new runs;
> every results PR gates on /verify-claims.

**D3 — PlanBench now or after submission?** The Docker-VAL grading of the on-disk
Haiku NT responses is VPN-free and cheap; the WT backend is ~a day of dev + API
spend from the $70.6 remainder. Run in parallel now, or park until the paper is
out?

> ANSWER (Omer, 2026-07-23, in session): run now — picked up right after P2.
> Executed same day: Haiku NT grading turned out to already exist except t2,
> which was 0.0 everywhere due to a missing-FAST_DOWNWARD grading artifact;
> re-graded locally (Rosetta VAL + plugin FD, no Docker/VPN) → blocksworld 28.2
> (== GPT-4's 28.4), mystery 0.4, logistics 2.8. Full table + findings:
> `development/archive/planbench/planbench_frontier_haiku_nt.md`. Next: WT backend +
> pre-registered Act-4 predictions (see that doc's "Next" section).

**D4 — The other parked items** (ISS-024b guided_json fix · steering reframe ·
stronger contamination probe): keep all three parked as Future Work, or promote
any into the evaluation phase?

> ANSWER (Omer, 2026-07-24, in session): keep ALL THREE parked as Future Work;
> promote none. One amendment: run the $0 LOCAL AUDIT of the guided_json
> artifact's mechanism + affected-row fraction now (agent-executable, fix itself
> stays parked) so C1's "artifact audits" component stays internally consistent.
> Steering reframe superseded by the D-J5 nt-ster control; contamination probe
> parked with a concrete promotion trigger (advisor/reviewer challenge after the
> truncation decomposition). Full spec: `development/journal_decisions_memo.md` §7.
