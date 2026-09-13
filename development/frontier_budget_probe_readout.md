# Frontier output-budget probe — readout (run 2026-09-12, RATIFIED 2026-09-12, in tex `5466cb6`)

**Status:** all four legs ran on 2026-09-12 under the frozen code (prereg
`frontier_budget_probe_prereg.md`, freeze record 2026-09-10; hashes re-verified
against `main` at `bbcf111` after the PR #98 squash-merge, all nine equal). The
readout below is the frozen script's output (`results/derived/budget_probe/readout_{sonnet,haiku}.json`,
regenerated after the one infra retry described in §4). **No tripwire fired on either
tier.** Nothing in the paper has been edited. Omer ratifies in §6; the paper sentence
follows ratification (handoff step 11).

Every number here is copied from the readout JSON or the pooled table
(`results/derived/e2e_overlay/pooled_e2e_table.md`, run-tagged `*-budget64k` rows).
Reference cells are unchanged: Sonnet ⟨49, 62⟩, Haiku ⟨52, 64⟩ stay in every table.

## 1. Primary endpoint (prereg §3.2) — LEN-FIT conversion vs ET-FAIL control

Conversion = probe row `e2e_strict == True` on the same 100 keys as the reference
cell (key-set equality asserted by the script). One-sided Fisher exact, α = 0.05.

| tier | LEN-FIT converted | Wilson 95% | ET-FAIL converted (control) | Wilson 95% | risk diff | Fisher p | verdict (§3.2 rule) |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 (leg A, primary) | 16 / 25 = 64.0% | [44.5, 79.8] | 7 / 19 = 36.8% | [19.1, 59.0] | +27.2 pp | 0.069 | **PARTIAL** |
| Haiku 4.5 (leg B, replication) | 12 / 17 = 70.6% | [46.9, 86.7] | 1 / 12 = 8.3% | [1.5, 35.4] | +62.3 pp | 0.0011 | **H1** |

Plain reading. On Sonnet the truncated-but-fitting failures converted at 64%, which
clears the H1 band (≥ 60%), but the control group of non-truncated failures also
converted at 37% when re-run, so the one-sided test does not reach α (p = 0.069). The
§3.2 rule therefore returns PARTIAL: the prereg allows quoting both rates and the
conversion fraction, with no causal clause. On Haiku the same contrast is clean
(71% vs 8%, p = 0.001): H1 supported at the second tier.

The Sonnet control rate (37%) is above the pre-registered ≤ 30% band for the control
but below the 50% tripwire (§3.6(b)); the OK-class re-run success (46/49) is above the
40/49 floor, so the "same 100 trials" language is not replaced. Both facts are
reported, not interpreted.

## 2. Secondary endpoints (prereg §3.3; descriptive, never revise §1)

| quantity | Sonnet | Haiku |
|---|---|---|
| cell delivered (exact, Wilson 95%) — §3.3(1) | 70 / 100, [60.4, 78.1] (ref ⟨49, 62⟩; H1 band ≥ 65 met) | 65 / 100, [55.3, 73.6] (ref ⟨52, 64⟩) |
| OK-class re-run success | 46 / 49 | 50 / 52 |
| DECLINE conversion — H2, §3.3(4) | 0 / 3 | **0 / 14** (H2 band ≤ 30% met) |
| LEN-NOFIT conversion (reported, not scored) | 1 / 4 | 0 / 1 |
| OVERFLOW rows | 0 | 1 (depot/p01, as pre-classified) |
| SNAP rows (Haiku only) — §3.3(7) | — | 2 / 2 converted (as predicted) |
| output tokens per trial, aggregate over turns (median / max) — the cost figure | 4,530 / 37,730 | 3,410 / 16,665 |
| output tokens, final turn only (median / max / rows at exactly 64,000) — the budget-binding figure | 3,324 / 35,196 / **0** | 1,946 / 14,154 / **0** |

**Arm contrast at the raised budget — §3.3(2)** (two exact Wilson cells from the pooled
table, WT minus NT, prompt v11, n = 100 each; legs C/D present so the sentence is
licensed):

| tier | WT delivered at 64K | NT delivered at 64K | Δ (WT − NT) |
|---|---|---|---|
| Sonnet 4.6 | 70 [60.4, 78.1] | 44 [34.7, 53.8] | +26 pp |
| Haiku 4.5 | 65 [55.3, 73.6] | 58 [48.2, 67.2] | +7 pp |

**Failure anatomy — §3.3(5)** (`e2e_reason` counts, probe next to reference):

| reason | Sonnet ref → probe | Haiku ref → probe |
|---|---|---|
| trajectory_ok | 49 → 70 | 52 → 65 |
| trajectory_mismatch | 17 → 17 | 15 → 19 |
| format_parse_fail | 21 → 13 | 19 → 14 |
| censored_at_snapshot_cap | 13 → 0 | 12 → 0 |
| truncated_empty | 0 → 0 | 2 → 2 |

No probe row hit the 64,000 budget on its final turn on either tier, and no probe row
was censored at the 262,144-char snapshot. The longest final turn on Sonnet was
35,196 tokens, so the trajectories that had been cut at 6,144 needed room, not the
full budget.

## 3. Tripwires (prereg §3.6) — none fired

| tripwire | Sonnet | Haiku |
|---|---|---|
| (a) censored row / non-binding truncation | none / none | none / none |
| (b) control > 50% or OK re-run < 40 / < 42 | 36.8%, 46/49 — clear | 8.3%, 50/52 — clear |
| (c) Haiku DECLINE > 50% | — | 0% — clear |
| (d) spend: leg A > $45 or any leg > 1.5× band | see §5 — clear | clear |
| (e) constant column / guard on every row | none seen in the JSON | none |

## 4. Run log and the one apparatus event

- PR #98 squash-merged to `main` (`bbcf111`, 2026-09-12); the frozen bytes are identical
  to the branch tip (`git diff bbcf111 7c9aec9` empty; all nine sha256 equal).
- Dry run selected exactly 100 trials on both tiers. Each leg's `run_manifest.json`
  records budget 64,000, snapshot 262,144, streaming, loop limit 10, and the pinned
  `gt_cache.json` hash (`77d4184e…`); the readout script asserted every field.
- Legs: A (Sonnet WT) 100 trials sequential, ≈4.3 h; B (Haiku WT) 100 trials, run in
  parallel with A on Omer's instruction; C/D (NT) as Message Batches, 100 requests each.
  Overlay provenance: the four probe cells carry `snapshot_cap: 262144`,
  `snapshot_cap_source: "manifest"`; the reference cells keep `"inferred"` at 16,384.
- **One infra failure, retried by the apparatus (not a deviation):** on leg A, trial 28
  (depot/p03) raised an exception with an empty message during the SDK tool-runner loop
  and was stored as `infra_failure: true` (zero tokens, empty response). The runner's
  documented resume path restores completed rows and retries infra rows; re-running the
  identical command restored 99 and retried the one trial, which then completed
  normally (tool-verified OK; graded `trajectory_mismatch`, i.e. not converted). The
  readout was regenerated after the retry; every count in §1–§2 is from the
  post-retry corpus. The pre-retry readout had identical primary counts (the infra row
  had been counted as a non-conversion), so the verdicts did not depend on the retry.
  Two async-generator cleanup tracebacks at interpreter exit (after all rows and the
  summary were written) are cosmetic.
- No tripwire line was printed by either readout; `tripwires: []` in both JSONs.

## 5. Cost (prereg §2.5; itemized, measured)

| leg | measured | expected band | hard cap |
|---|---|---|---|
| A Sonnet WT | $26.21 (incl. the retried trial) | $30–35 | $111 |
| B Haiku WT | $6.92 | ≈$10–12 | $37 |
| C Sonnet NT (batch) | $5.55 | — | $49 |
| D Haiku NT (batch) | $2.00 | — | $16 |
| **total** | **$40.68** | $50–65 | $213 |

Tripwire (d) checked at trial 20 of leg A: $4.93 spent, naive projection $24.67.

## 6. Ratification (Omer)

1. Ratify the readout as written: Sonnet **PARTIAL** (16/25 vs 7/19, p = 0.069),
   Haiku **H1** (12/17 vs 1/12, p = 0.001), H2 supported on Haiku (0/14), arm contrast
   at 64K Sonnet +26 pp / Haiku +7 pp, no tripwires.
   > ANSWER:    Use revised wording that states the mixed primary result explicitly, reports the larger-budget arm comparisons, and notes that substantial delivery failures remain. Mention that response storage was also enlarged. Replace “at a budget the trajectory fits” with “under the 64K output allowance.” Preserve the original censoring bounds.

2. Paper sentence (handoff step 11; prereg §3.5 pre-drafted language). Because the
   Sonnet verdict is PARTIAL, §3.5 says: quote both rates, no causal clause, keep the
   descriptive anatomy sentence and add the conversion fraction. Proposed for the
   Delivery Gap subsection (values filled, wording to be tuned at edit time):
   *"Re-running the same 100 Sonnet trials with a 64K output budget converted 16/25 of
   the budget-fitting truncated failures and 7/19 of the non-truncated failures
   (Fisher p = 0.07); the delivered rate moved from ⟨49, 62⟩ to 70 [60, 78]. On Haiku
   the contrast is 12/17 vs 1/12 (p = 0.001), and 0/14 of the trials in which Haiku
   answered with a summary instead of the trace converted."*
   Plus the §3.3(2) clause: *"at a budget the trajectory fits, the availability lift on
   simulate is +26 pp on Sonnet (70 [60, 78] vs 44 [35, 54]) and +7 pp on Haiku
   (65 [55, 74] vs 58 [48, 67])."*
   Use these, or say what to change.
   > ANSWER: With the output allowance raised from 6,144 to 64,000 tokens and response storage expanded, 16/25 previously truncated, budget-fitting Sonnet failures became correct, compared with 7/19 other failures (p=0.069); this did not meet the preregistered confirmation criterion. Haiku met that criterion, with 12/17 versus 1/12 conversions (p=0.0011), while none of its 14 summary-only failures became correct. At 64K, delivered accuracy with versus without tools was 70% versus 44% for Sonnet and 65% versus 58% for Haiku. Despite the larger allowance, 30% and 35% of tool-arm trials still failed, and no final response reached the output-token cap.

3. The infra retry in §4 is reported in the Limitations clause alongside the §9
   known limits (one line), or omitted as apparatus routine?
   > ANSWER: Document the infrastructure retry in the reproducibility appendix or execution-protocol note. It does not need a main-text Limitations paragraph. State that one infrastructure failure was retried under the existing resume policy, the completed retry was graded incorrect, and the primary verdicts were unchanged

After ratification: NUMBERS.md "budget probe" block, the Delivery Gap + Limitations
edits on `paper/aaai27` (pull Overleaf first), ledger cost line already appended.
