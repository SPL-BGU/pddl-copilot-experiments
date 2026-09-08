# Handoff — frontier output-budget probe (ratified 2026-09-08, not yet run)

**Read first:** `frontier_budget_probe_prereg.md` (design of record, RATIFIED — all four
legs, budget 65,536, spend approved, decision rule accepted). This file is the
operational sequence only; it never overrides the prereg. Pick up with
`/resume-verify development/frontier_budget_probe_handoff.md`.

**State at write time (2026-09-08):** $0 spent, no probe data exists. Code is on PR #98
(`job2/batch2-budget-probe-prereg`), not yet merged. The paper branch `paper/aaai27`
holds two unpushed commits (`125cc7a`, `dbea3d7`) awaiting Omer's review — separate
gate, do not touch here.

## The sequence (each step blocks the next; nothing here touches the cluster)

1. **Merge PR #98** (after review). It carries the runner flags, the 262,144 cap, the
   freeze candidate `tools/budget_probe_analysis.py`, and its fixture test. Until it is
   on main, do not run anything against the API.

2. **Gate 5 — adversarial review of the freeze candidate, in a DIFFERENT session/model
   than the one that wrote it** (`/code-review` at high effort or stronger). Inputs for
   the reviewer: the prereg §3 (analysis plan), the traceability map in the prereg's
   freeze record, and these files: `tools/budget_probe_analysis.py`,
   `tests/test_budget_probe_analysis.py`, `tools/e2e_regrade.py` (KNOWN_CAPS,
   `detect_cap`, the simulate at-cap censor), `.claude/skills/analyzer/scripts/e2e_overlay.py`
   (probe stem → run tag). Known gap already declared for the reviewer: the fixture only
   exercises the list-shaped oracle trace (`canon_size()` dict branch untested). Fix
   every finding as an ordinary edit (this is before the hash, so no deviation is
   declared), re-run `bash tests/verify.sh`, and re-derive the traceability line numbers.

3. **Discharge §8 items 4–6** (mechanical, one script run each):
   - `python3 tools/budget_probe_analysis.py classify --tier sonnet` and `--tier haiku`
     must print exactly the pinned counts (Sonnet 49/25/4/0/0/3/19/0, Haiku
     52/17/1/1/2/14/12/1) and the gt_cache sha256
     `77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e`.
   - Extract the 100 trial keys of each reference cell and record their sha256 in the
     freeze record (`jq -c .key results/<tier>-frontier/sweep5v2-with-tools/trials.jsonl | grep '"simulate"' | sort | sha256sum`).
   - `python3 tests/test_e2e_overlay.py` (stem/run-tag test) passes.

4. **Hash freeze.** Append to the prereg's freeze record: sha256 of
   `tools/budget_probe_analysis.py`, `tools/e2e_regrade.py`,
   `.claude/skills/analyzer/scripts/e2e_overlay.py`, `results/derived/gt_cache.json`,
   plus the two key-set hashes and the final traceability map. From here any edit to
   those files is a declared deviation (prereg §9-style) + re-freeze + regenerated readout.

5. **Dry run (free):**
   `python3 tools/frontier_runner.py --dry-run --model claude-sonnet-4-6 --tasks simulate --variant 11 --num-predict 65536 --snapshot-len 262144 --stream`
   must select exactly 100 trials. (Verified 2026-09-08 on the candidate code.)

6. **Leg A — Sonnet with tools (the primary).** Needs `ANTHROPIC_API_KEY` in the
   environment and the marketplace at `../pddl-copilot`.
   ```
   python3 tools/frontier_runner.py --model claude-sonnet-4-6 --tasks simulate --variant 11 \
     --num-predict 65536 --snapshot-len 262144 --stream --use-cached-gt \
     --out results/sonnet-frontier/sweep5v2-with-tools-budget65k
   ```
   Sequential and resumable (re-run the same command to continue). Expected 2–4 h,
   expected cost ≈$30–35. **Tripwire (d): after ~20 trials, compare the runner's
   running cost line against §2.5; if leg A is heading past $45, stop and reconcile
   tokens before continuing.** The runner prints per-trial `out=` tokens; the big
   problems (barman/p04–p05, tpp/p05, drone/p04–p05, depot/p01, rovers/p05) are the
   ones that should be long.

7. **Leg B — Haiku with tools:** same command with `--model claude-haiku-4-5` and
   `--out results/haiku-frontier/sweep5v2-with-tools-budget65k`. Expected ≈$10–12.
   depot/p01 will overflow the context again by construction (pre-classified OVERFLOW).

8. **Legs C/D — no-tools, Message Batches** (cheap; run after A/B, or in parallel):
   ```
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 build --corpus canonical \
     --marketplace-path ../pddl-copilot --tasks simulate --num-variants 1 \
     --num-predict 65536 --out .local/frontier/budget65k_sonnet_nt
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 submit --batch-dir .local/frontier/budget65k_sonnet_nt
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 poll   --batch-dir .local/frontier/budget65k_sonnet_nt
   python3 tools/claude_api_batch.py --model claude-sonnet-4-6 grade  --batch-dir .local/frontier/budget65k_sonnet_nt \
     --snapshot-len 262144 --out-results results/sonnet-frontier/sweep5v2-budget65k
   ```
   Then the same four commands with `--model claude-haiku-4-5` and
   `results/haiku-frontier/sweep5v2-budget65k`. `--num-variants 1` = prompt v11 only
   (the frontier single-prompt setting), n = 100. Check `counts.json` says
   `total_requests: 100` and `num_predict: 65536` before `submit`.

9. **Regrade with the standard command** (no new grader, no new tolerance):
   `python3 tools/e2e_regrade.py results/sonnet-frontier results/haiku-frontier`.
   The new cells appear as `sweep5v2-with-tools-budget65k` / `sweep5v2-budget65k`
   overlay files with `snapshot_cap: 262144`. Then
   `python3 .claude/skills/analyzer/scripts/e2e_pooled.py` — the probe rows must appear
   as their own run-tagged block, never merged into the `sweep5v2` rows.

10. **Readout:**
    `python3 tools/budget_probe_analysis.py readout --tier sonnet --probe results/sonnet-frontier/sweep5v2-with-tools-budget65k`
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

- Don't skip step 2 because the fixture passes. The fixture is gate 4; gate 5 is a
  different reviewer reading the code against the prereg. PR #96 shipped 15 findings
  past a passing freeze.
- Don't weaken strict grading to "fix" the cell, and don't add a tolerance for a new
  answer format the probe reveals — if a new format appears, that is a finding, and a
  separate D-decision, not a probe edit.
- Don't pool probe rows with the reference cells or quote the probe as a resolution
  of ⟨49, 62⟩. The reference bound stays in every table.
- Don't raise any open-roster budget on the back of this (the 32K smoke failure stands).
- The runner's `--num-predict` applies to every turn, including the tool-call turn;
  that is intended and identical across legs.
- Cost check is per leg against §2.5; the grant covers the total, but the itemization
  discipline is what the 08-30 decision asked for.
