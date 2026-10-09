# Handoff: delivered rerun, from "run nearly complete" to readout (2026-10-09)

*Written at the end of the session that designed, submitted and froze the delivered
rerun. Start a fresh session with `/resume-verify development/delivered_rerun_handoff.md`.
Verify every claim below before acting on it; the repo and the cluster win over this doc.*

## 1. What this is

The paper names the **delivered answer** as its primary outcome but could not measure it
on the open-weight tool arms (500-character answer snapshots). The delivered rerun
measures it. Design of record: **`development/reference/delivered_rerun_prereg.md`**
(read §2, §3, §4, §5, §7, §8, §8a, §8b before doing anything). Background and the
findings that motivated it: `development/paper_notes_discussions.md` entries 2026-10-02
and 2026-10-03, `development/reanalysis_transcripts.md`, `development/weakness_consolidated.md` C1.

## 2. Exact state at 2026-10-09 ~11:30 IDT

### Cluster run (checked by row counts and job states only)

| job | cell | rows | state |
|---|---|---|---|
| 21982285 | Gemma, tools (Part A) | 9,120 / 9,120 | COMPLETED |
| 21982286 | Gemma, neutral prompt, validate_plan (Part B) | 6,000 / 6,000 | COMPLETED |
| 21982369 | Qwen3.5-9B, tools (Part A) | 9,120 / 9,120 | COMPLETED |
| 21982370 | Qwen3.6-35B, tools (Part A) | 9,120 / 9,120 | COMPLETED |
| 21991349_0 | Gemma, unaided (Part C) | 4,560 / 4,560 | COMPLETED |
| 21991349_2 | Qwen3.6-35B, unaided (Part C) | 4,560 / 4,560 | COMPLETED |
| 21991349_1 | **Qwen3.5-9B, unaided (Part C)** | **4,392 / 4,560** | **TIMEOUT at 12 h** |
| **22417213** | **resume of that 9B unaided cell** (same tag, resumes from its rows) | — | **submitted 2026-10-09 ~11:25, last seen PENDING; SSH then timed out, state unknown** |

- Result dirs on the cluster (`~/pddl-copilot-experiments/results/`):
  `slurm_vllm_<model>_off_tools_all_minimal_delivered-rerun`,
  `slurm_vllm_gemma4_26b-a4b_off_tools_all_neutral_delivered-rerun-neutral`,
  `slurm_vllm_<model>_off_no-tools_delivered-rerun`. Smoke dirs (`*smoke*`) are never used.
- Cluster checkout: branch `harness/delivered-rerun` at **`4b2fe6e`**; tools repo
  `~/pddl-copilot` at **`5e4f9c0`**. Both verified 2026-10-09. **Do not move either until
  22417213 has finished.** After that the checkout may be returned to `main`.
- Serving: vLLM 0.20.2 (prereg §8).
- **No outcome of this run has been read.** Only job states and row counts. Keep it that
  way until step 3 below runs the frozen code. Do not run the `analyzer` skill or any
  ad-hoc success/invocation count on these dirs.

### Analysis code: FROZEN 2026-10-03

- PR **#116**, branch `analysis/delivered-rerun`, commit **`d558946`**.
- Package hash for `--i-have-frozen`: **`822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9`**.
- Freeze record with all 27 file sha256s: prereg §8. Gates 1–5 passed (adversarial
  review + an independent verification pass, all findings fixed before the hash).
- Entry point: `python -m tools.delivered_rerun.run`. Fixture mode:
  `--fixture tests/fixtures/delivered_rerun --out DIR`. Live mode requires
  `--rerun-root`, `--canonical-root`, `--gt-cache`, `--marketplace-path`, `--out`,
  `--i-have-frozen <hash>`. It halts (exit 2, named HALT) on any registered check;
  it refuses `python -O`.
- Live mode checks that the marketplace repo is at exactly `5e4f9c0` with a clean
  `plugins/` (tracked and untracked, ignored files excepted), and checks a digest of the
  `domains/` tree.
- **Any edit to a frozen file is a declared deviation** (prereg §9) followed by a
  re-freeze. Do not "fix" the code; if it halts, report the halt.

### Laptop

- `~/personal/pddl-copilot-experiments`: checked out on `docs/reanalysis-and-rerun-prereg`
  (PR #112) at `89f27da`, clean apart from untracked worktrees under `.claude/worktrees/`.
  The analysis code lives in worktree `.claude/worktrees/agent-a88304d519595fbc6`
  (branch `analysis/delivered-rerun`, `d558946`).
- `~/personal/pddl-copilot` (tools repo): on Omer's branch `feature/pddl-visualizer-plugin`
  at `f0e2c61`. **Not the pinned commit, and not ours to switch.**

### Open PRs (Omer merges; none merged yet)

| PR | what | merge note |
|---|---|---|
| #110 | paper: false guided_json sentence fixed, Limitations disclosure | 1st |
| #111 | paper: consistency read A–D | 2nd (stacked on #110) |
| #114 | paper: PlanBench equivalence test + post hoc extractor regrade | 3rd (stacked on #111) |
| #115 | paper: consistency read group E (27 rewordings) | 4th (stacked on #114) |
| #112 | docs: re-analyses, prereg, NUMBERS rows, STATUS, notes | any time |
| #113 | harness fixes the run used | after 22417213 finishes |
| #116 | frozen analysis code | after the readout |

## 3. Remaining actions, in order

1. **Confirm the last cell.** Cluster go-ahead for this run was given by Omer 2026-10-02;
   still check the connection is up. `sacct -j 22417213` must be COMPLETED and
   `trials.jsonl` of the 9B no-tools cell must have exactly 4,560 lines. If it timed out
   again, resume once more the same way (single cell, same `--run-tag delivered-rerun`,
   from `~/pddl-copilot-experiments`, after checking `4b2fe6e` / `5e4f9c0`); never
   shotgun-resubmit.
2. **Sync the seven result dirs to the laptop** (only the `delivered-rerun` and
   `delivered-rerun-neutral` dirs; not smoke). Use `cluster-ops` `sync.sh` with an
   explicit target, or an rsync of exactly those dirs. Confirm line counts after the
   copy: 9,120 × 3, 6,000, 4,560 × 3.
3. **Get the tools repo at `5e4f9c0` without touching Omer's checkout:**
   `git -C ~/personal/pddl-copilot worktree add <path> 5e4f9c0`, then create the plugin
   venvs there the way `scripts/launch-server.sh` / `setup_env.sh` do. Pass that path as
   `--marketplace-path`. (Proposed to Omer 2026-10-09; he had not objected when this
   was written. Remove the worktree afterwards.)
4. **Run the frozen analysis** from the analysis worktree, with the main checkout's
   `.venv` python: `--rerun-root` = the synced dirs, `--canonical-root` =
   `results/sweep5v2-live`, `--gt-cache` = `results/derived/gt_cache.json`, and
   `--i-have-frozen 822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9`.
   Write output outside the frozen tree. If it halts, stop and report the halt verbatim;
   if a tripwire fires, the release needs `--audit-notes` with a written audit (§8b 15).
5. **Report the readout to Omer in plain language, in this order:**
   - parity guard (§3), Gemma control first, then the job-level rule;
   - the Part C parity table (did the unaided baseline move);
   - E1 delivered rates, with the no-room share (§8a);
   - E2, E3, E4;
   - registered readings R1–R5, including **R3, the title rule**.

   No interpretation beyond the registered labels without Omer.
6. **Record:** append the readout to the prereg (new section after §8b; deviations, if
   any, in §9), add frozen figures to `development/NUMBERS.md`, a dated
   `paper_notes_discussions.md` entry, refresh `STATUS.md` N1b, update the memory note
   `project_delivered_rerun.md`.
7. **Descriptive §6 tables** (per wording, per domain, classical vs numeric, cost at
   realistic price ratios, the Gemma no-call answers read in full) run after the readout,
   labelled descriptive.
8. **Then the drafting pass** (STATUS.md N1b "After the rerun"): rerun results; title per
   R3; statistics paragraph (`reanalysis_statistics.md`: paired, domain-clustered tests,
   two verdicts downgraded, GLMM +7.80 SE 0.29); cost paragraph
   (`reanalysis_breakdowns_cost.md`); test-data description (duplicated plans, 100:20
   validate_domain split, parenthesis-only invalid domains); per-wording/per-domain
   tables; delivery-gap section incl. the held group E rows E3a, E3b, E8b; weakness-list
   Q5, Q8, Q9. Drafts shown to Omer before commit; `/verify-claims` on every number.
9. **Later:** weakness-list Q6, Q7, Q10 (title, more families, VAL cross-check); N3
   pre-submission (JAIR reformat, cover letter, code/data release); N2 advisor round
   (Omer schedules).

## 4. Traps

- Memory notes and STATUS.md say "do not read outcomes": that rule ends only when step 4
  runs the frozen code on all seven complete cells.
- `status.sh` does not know the `tools_all_neutral` cond; count Part B rows directly.
- The pinned `tools/e2e_regrade.py` now gives different Gemma delivered-solve numbers on
  the canonical cells (it imports the prefix-stripping scoring); the frozen rows in
  `NUMBERS.md` stay (warning row added 2026-10-03).
- Simulate: in about 45% of smoke trials the tool result alone filled the 16K context,
  so no answer was possible; these count as delivered failures and their share is
  reported (§8a). Do not propose a 32K context (failed pilot).
- Subagents die when the session restarts. Check `ListAgents` before saying one is
  running; check its worktree for partial work.
