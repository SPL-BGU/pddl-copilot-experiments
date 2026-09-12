# Handoff — frontier output-budget probe (ratified 2026-09-08, frozen 2026-09-10, RUN 2026-09-12 — readout awaiting ratification)

**Read first:** `frontier_budget_probe_prereg.md` (design of record, RATIFIED — all four
legs, budget **64,000** (amended 2026-09-10 from 65,536, §11), spend approved, decision
rule accepted). This file is the operational sequence only; it never overrides the
prereg. Pick up with `/resume-verify development/frontier_budget_probe_handoff.md`.

**State at write time (2026-09-12):** steps 1–10 DONE. PR #98 squash-merged
(`bbcf111`), hashes re-verified on `main`, all four legs run ($40.68 measured, no
tripwire), regrade + pooled table + both readouts generated. **Readout =
`frontier_budget_probe_readout.md` (AWAITING Omer's ratification, §6 there).** Verdicts:
Sonnet PARTIAL (16/25 vs 7/19, p = 0.069), Haiku H1 (12/17 vs 1/12, p = 0.001). One
infra failure on leg A (depot/p03) was retried through the runner's documented resume
path; counts unchanged. Only step 11 remains. The paper branch `paper/aaai27` was
pushed + Overleaf-synced 2026-09-08 — separate track, do not touch until ratified.

## The sequence (each step blocks the next; nothing here touches the cluster)

1. ~~**Merge PR #98**~~ DONE 2026-09-12 (`bbcf111`, squash; hashes re-verified equal). It carries the runner flags, the 262,144 cap, the
   run manifest, the frozen `tools/budget_probe_analysis.py`, and the tests. Until it
   is on main, do not run anything against the API. **After the merge, re-run the
   sha256 table in the prereg's freeze record against main** — the freeze hashed the
   branch tip; a merge that changes any frozen byte is a deviation, not a merge.

2. ~~**Gate 5 — adversarial review.**~~ DONE 2026-09-10: four findings (Haiku's 64,000
   output ceiling vs the 65,536 budget; no persisted run settings on resume; snapshot
   cap inferred from the histogram even for the probe; the §3.6(a) tripwire read the
   aggregate token count with `<` instead of the final-turn count with `≠`). All fixed
   before the hash, with regression tests (prereg §11).

3. ~~**Discharge §8 items 4–6.**~~ DONE 2026-09-10 (prereg freeze record): pinned
   counts reproduced under 64,000 (Sonnet 49/25/4/0/0/3/19/0, Haiku
   52/17/1/1/2/14/12/1), gt_cache sha256
   `77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e`, key-set hashes
   Sonnet `bdaab773…3207` / Haiku `bf3a6d94…7db8`, stem test passing.

4. ~~**Hash freeze.**~~ DONE 2026-09-10 (prereg §8 freeze record: five frozen files +
   apparatus/test hashes + traceability map). From here any edit to a frozen file is a
   declared deviation (prereg §9-style) + re-freeze + regenerated readout.

5. ~~**Dry run (free):**~~ DONE 2026-09-12 —
   `python3 tools/frontier_runner.py --dry-run --model claude-sonnet-4-6 --tasks simulate --variant 11 --num-predict 64000 --snapshot-len 262144 --stream`
   must select exactly 100 trials. (Verified 2026-09-10 on the frozen code, both tiers.)

6. ~~**Leg A — Sonnet with tools (the primary).**~~ DONE 2026-09-12 — Needs `ANTHROPIC_API_KEY` in the
   environment and the marketplace at `../pddl-copilot`.
   ```
   python3 tools/frontier_runner.py --model claude-sonnet-4-6 --tasks simulate --variant 11 \
     --num-predict 64000 --snapshot-len 262144 --stream --use-cached-gt \
     --out results/sonnet-frontier/sweep5v2-with-tools-budget64k
   ```
   The runner writes `run_manifest.json` into `--out` before its first request; check
   it says `num_predict: 64000`, `snapshot_len: 262144`, `stream: true`,
   `max_iterations: 10`, `gt_cache_sha256: 77d4184e…`. Sequential and resumable
   (re-run the SAME command to continue — a resume with any flag changed is refused,
   and a directory holding trials without a manifest is refused; use a fresh `--out`
   in that case). Expected 2–4 h, expected cost ≈$30–35. **Tripwire (d): after ~20
   trials, compare the runner's running cost line against §2.5; if leg A is heading
   past $45, stop and reconcile tokens before continuing.** The runner prints per-trial
   `out=` (aggregate, the cost figure) and `outF=` (final turn — the number the §3.6(a)
   tripwire reads; a truncated trial shows `outF=64000`); the big problems
   (barman/p04–p05, tpp/p05, drone/p04–p05, depot/p01, rovers/p05) are the ones that
   should be long.

7. ~~**Leg B — Haiku with tools:**~~ DONE 2026-09-12 — same command with `--model claude-haiku-4-5` and
   `--out results/haiku-frontier/sweep5v2-with-tools-budget64k`. Expected ≈$10–12.
   depot/p01 will overflow the context again by construction (pre-classified OVERFLOW).

8. ~~**Legs C/D — no-tools, Message Batches**~~ DONE 2026-09-12 — (cheap; run after A/B, or in parallel):
   ```
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 build --corpus canonical \
     --marketplace-path ../pddl-copilot --tasks simulate --num-variants 1 \
     --num-predict 64000 --out .local/frontier/budget64k_sonnet_nt
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 submit --batch-dir .local/frontier/budget64k_sonnet_nt
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 poll   --batch-dir .local/frontier/budget64k_sonnet_nt
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 grade  --batch-dir .local/frontier/budget64k_sonnet_nt \
     --snapshot-len 262144 --out-results results/sonnet-frontier/sweep5v2-budget64k
   ```
   Then the same four commands with `--model claude-haiku-4-5` and
   `results/haiku-frontier/sweep5v2-budget64k`. `--num-variants 1` = prompt v11 only
   (the frontier single-prompt setting), n = 100. Check `counts.json` says
   `total_requests: 100` and `num_predict: 64000`, and that `build` wrote
   `run_manifest.json` into the batch dir, before `submit` (submit refuses without it;
   grade carries the manifest into the results dir with the snapshot length).

9. ~~**Regrade with the standard command**~~ DONE 2026-09-12 — (no new grader, no new tolerance):
   `python3 tools/e2e_regrade.py results/sonnet-frontier results/haiku-frontier`.
   The new cells appear as `sweep5v2-with-tools-budget64k` / `sweep5v2-budget64k`
   overlay files with `snapshot_cap: 262144` and `snapshot_cap_source: "manifest"`
   (the reference cells keep `"inferred"`). Then
   `python3 .claude/skills/analyzer/scripts/e2e_pooled.py` — the probe rows must appear
   as their own run-tagged block, never merged into the `sweep5v2` rows.

10. ~~**Readout:**~~ DONE 2026-09-12 —
    `python3 tools/budget_probe_analysis.py readout --tier sonnet --probe results/sonnet-frontier/sweep5v2-with-tools-budget64k`
    and `--tier haiku ...`. Output: `results/derived/budget_probe/readout_<tier>.json`.
    **If it prints `TRIPWIRE(S)`, stop: trace the cause (prereg §3.6) before writing a
    single sentence.** The verdict field is H1 / KILL / PARTIAL per §3.2; the C/D legs
    feed §3.3(2) (arm contrast at the raised budget) — compute that as two exact Wilson
    cells from the pooled table, WT minus NT, nothing fancier.

11. **Ratify the readout (Omer), then the paper edit** on `paper/aaai27` (after the
    batch-1/2 review gate has cleared and Overleaf has been pulled): one or two
    sentences in the Delivery Gap subsection using the pre-drafted language in prereg
    §3.5, the matching Limitations/Future-Work clause, a "budget probe" block in
    NUMBERS.md, and the measured cost appended to the paper_notes ledger. The reference
    cells' numbers (⟨49, 62⟩ etc.) do not change anywhere.

## Things that are easy to get wrong

- Gate 5 is done, but its lesson stands: if anything in the frozen files has to change
  before the run, that is a declared deviation + re-freeze, never a quiet edit.
- The budget is 64,000, not 65,536 (Haiku 4.5's output ceiling; prereg §11). A command
  typed from the 09-08 memory with `--num-predict 65536` will be refused by the
  readout's manifest check even if the API accepted it on Sonnet.
- Don't weaken strict grading to "fix" the cell, and don't add a tolerance for a new
  answer format the probe reveals — if a new format appears, that is a finding, and a
  separate D-decision, not a probe edit.
- Don't pool probe rows with the reference cells or quote the probe as a resolution
  of ⟨49, 62⟩. The reference bound stays in every table.
- Don't raise any open-roster budget on the back of this (the 32K smoke failure stands).
- The runner's `--num-predict` applies to every turn, including the tool-call turn;
  that is intended and identical across legs. The per-trial `out=` column sums all
  turns and can exceed 64,000 without any turn having been truncated; `outF=` is the
  final turn and is what "truncated at the budget" means.
- Cost check is per leg against §2.5; the grant covers the total, but the itemization
  discipline is what the 08-30 decision asked for.
