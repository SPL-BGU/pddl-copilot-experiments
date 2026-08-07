# PlanBench-WT — post-results handoff (state as of 2026-08-06)

> **Entry point for a fresh session: `/resume-verify` this file.**
> The confirmatory experiment is DONE, GRADED, and ANALYZED. Verdict = **RESCUE,
> SUPPORTED** (both McNemar tests significant; memo
> `planbench_wt_results_20260803.md`). This doc is ONLY the ordered remaining work.
>
> **2026-08-06 CLOSE-OUT:** items 1, 2, 3, and 5 are DONE (see the memo's new
> sections + commits f57998d/21cf811/3e9c09a/678f6d7): mechanism branch FINAL
> (Mystery formalization_match 97.8 not below clean 96.3), both ANSWER slots
> signed by Omer (accept + accept), bare-NT n=600 rows done (clean 43.8 stays
> CI-disjoint above GPT-4 34.3), §9-A ladder final (directive-only 0.5% — the
> directive alone moves nothing; $2.61). Arm cumulative ≈ $46.2 of $170.
> Remaining: item 4 (optional stripped-block regrade, free), item 6 (paper
> integration — Omer must prompt; prose unblocked), item 7 (branch hygiene — PR
> when Omer says so).
> Background, traps, and decided-do-not-reopen live in `PLANBENCH_WT_HANDOFF.md`
> (read its 08-01/08-03 header passes) and the prereg (`planbench_wt_prereg.md`,
> binding, tag `prereg-planbench-wt-v1` + restart record 1).

**Read in this order:** this file → `planbench_wt_results_20260803.md` (the verdict,
audits, deviation table, two OPEN ANSWER slots) → prereg §4 (formalization_match spec)
and §9-A (sensitivity arm) → `PLANBENCH_WT_HANDOFF.md` for deep background.

**Money:** $42.09 spent of $170 (calib $1.09 + $1.13, confirmatory $39.87). Every
remaining paid item below is gated on an explicit go-ahead from Omer.

## Ordered remaining actions

### 1. [OMER, two one-liners] Answer the results memo's two ANSWER slots
In `planbench_wt_results_20260803.md`: (a) accept the decomposition reading of the
clean-extraction criterion (7/443 instrument misses vs 157 model-side — same reading he
signed at the run-2 gate), and (b) accept the injection-robustness reading of the
Mystery-NT 0/600 (collapse holds at 0/121 on the uninjected subset + external anchors).
Analysis may proceed before these land; **paper prose may not**.

### 2. [FREE, LOCAL] `formalization_match` (§4) — finalizes the mechanism branch
The RESCUE branch of prediction (ii) is met on delegation (100%) and the clean-vs-
Mystery paired delta (2.2pp); its third requirement — Mystery `formalization_match`
not CI-disjointly below clean — is unmeasured. Spec is prereg §4 (read it verbatim):
decompose **parseable → solvable → equivalent-to-gold** per WT cell, denominator 600,
Wilson CIs; problem equality = (objects, init, goal) up to the config-declared object
bijection; domain equivalence = brute-force the 24 arity-constrained bijections against
`inspect_domain`, behavioral fallback = replay the gold plan through the model's
domain+problem. Use the **pddl-parser plugin** (`inspect_problem`/`inspect_domain`) —
analysis-time only, it was deliberately kept out of the model's roster.
- **Inputs:** stamped tool-call side-logs `.local/wt_run/{cfg}__anthropic-tools.jsonl`
  (fields per line incl. `instance_id`, `tool_calls` with full arguments — inspect one
  line first; **dedupe by keeping the LAST record per instance_id**, the 08-01
  pause/resume wrote duplicates).
- **Gold reference:** reconstructed from the NL query alone; the prereg records the
  reconstruction verified 500/500 on both configs by the 07-2x evidence workflow —
  locate that code via `planbench_wt_prereg_decisions.md` §3 / the workflow journal
  referenced in `PLANBENCH_WT_HANDOFF.md` §4; if unrecoverable, rebuild and re-verify
  against the 500/500 claim before use.
- **Deliverable:** table appended to the results memo + the mechanism-branch language
  upgraded from "provisional" to final (either RESCUE branch confirmed, or the
  discrepancy reported).

### 3. [PAID ≈$1.5 — OMER GATE] Bare-NT 200-trial completion (amendment K debt)
100 clean + 100 Mystery bare-NT trials on the `_3` pools so the PUBLISHED NT rows share
the n=600 denominator with everything else. Engine token `anthropic` (the graded 06-22
NT path), configs `blocksworld_3` / `mystery_blocksworld_3`, task t1, native PlanBench
prompt (NO scaffold). **Trap 5 still binds:** never `--ignore_existing` against
`pddl_copilot__anthropic__claude-haiku-4-5`; these configs write NEW response files, so
plain invocation is safe. Grade with the same Rosetta VAL, then recompute the NT clean
row at n=600 and report the NT-vs-GPT-4 line **whichever way it falls** (amendment L
prohibits denominator shopping; at n=500 Haiku was CI-disjoint above GPT-4 and needs
≥~50/100 on the extra pool to stay so — GPT-4 got 49).

### 4. [FREE, LOCAL, OPTIONAL] Stripped-block regrade of the 479 injected Mystery-NT trials
Re-extract using ONLY the text inside `[PLAN]..[PLAN END]` and re-run VAL. Bounds the
injection artifact exactly and hardens ANSWER slot (b). Expected: stays ~0 correct.

### 5. [PAID ≈$4 — OMER GATE] §9-A sensitivity arm (pre-registered, unrun)
The labelled directive-only variant on Mystery t1 (verbatim `WITH_TOOLS_SYSTEM`
including the dangling tool directive, NO tools attached) — completes amendment N's
four-rung ladder (native / scaffold-only / directive-only / scaffold+tools). Read
prereg §9-A for the exact spec before building; it is a small engine variant. Confirm
with Omer whether to run it now or record it as consciously skipped in the memo.

### 6. Paper integration (Act 4 secondary claim) — AFTER items 1-2
Rules that bind: §7 as amended (GPT-4 = labelled published reference line at stated
epoch/denominator, never a comparator, no test against it); WT is the labelled
SECONDARY claim, never Act 4's headline (§1); run `/verify-claims` before ANY
literature number enters prose (Göbel +3.0pp, published Mystery bands, Valmeekam 4.3%,
LLMFP replication — all flagged unverified-for-prose); check
`feedback_avoid_ai_writing_tells` and do NOT write prose unprompted — bring Omer a plan.

### 7. Branch hygiene
`planbench-wt-significance-brief` is ~17 commits ahead of main, unmerged, and now
carries CODE (adapter, engine names, frozen clause), not just docs — the doc-only
no-PR exception does NOT cover it. When Omer says so: open a PR per the commit
discipline (never merge to main without one). Do not touch `31b84ab` / nt-ster H4
files — parallel workstream.

## Machine-local inventory (gitignored — exists ONLY on this machine)

- `.local/wt_run/` — run + grade scripts, `run.log`/`grade.log`, 8 side-log JSONLs
  (dedupe rule above), per-cell `.out` logs, `analyze_calib.py`,
  `analyze_confirmatory.py`, `PAUSED.md` (historical).
- `external/LLMs-Planning/plan-bench/{responses,results}/{blocksworld,blocksworld_3,
  mystery_blocksworld,mystery_blocksworld_3}/pddl_copilot__anthropic-{tools,scaffold}__
  claude-haiku-4-5/` — the graded corpora. **Irreplaceable without re-spend; do not
  delete or regenerate.**
- `.local/calib/` incl. `archive-20260801-103650/` (run-1 draw) — discarded-by-design,
  keep for audit.
- `.venv-planbench-wt/` (pins are apparatus identity: anthropic==0.109.2, mcp==1.26.0);
  rebuild from `planbench/requirements-wt.txt` if lost.
- VAL: `external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate`
  (Mach-O x86_64 under Rosetta — the NT grader epoch). Grading env:
  `VAL=<that dir>`, cwd `external/LLMs-Planning/plan-bench`, WT venv,
  `PYTHONPATH=<repo>`; generation additionally needs `PDDL_MARKETPLACE_PATH`,
  `PDDL_PLANBENCH_PLUGINS="pddl-solver pddl-validator"`, `PDDL_COPILOT_TASK=t1`,
  `FAST_DOWNWARD=<pddl-solver venv downward path>`, `ANTHROPIC_API_KEY`.

## Known wrinkles a fresh agent must not rediscover the hard way

1. `analyze_confirmatory.py` per-cell block has a COSMETIC printf bug (percent printed
   ×100 too big, e.g. "4783.3%"); the Wilson CI columns and every number in the results
   memo are correct. Fix the format string before reusing the script.
2. Extraction conventions: "extraction" = extractor returns ≥1 action over the FULL 600
   denominator; "injection" = extracted count > actions listed inside the model's own
   `[PLAN]` block; decomposition classes = empty delivery / honest empty block /
   instrument miss. Keep these definitions or numbers won't reproduce.
3. Pairing key for McNemar is `(config, instance_id)` — ids overlap between the 500-
   and 100-instance pools. Mystery pairing prefixes the clean config name.
4. Band cutpoints are amendment K's n=600 row (RESCUE ≥325), NOT §3's n=500 table.
5. `apply_patches.py main()` exits early on this tree; patch 6 was applied directly and
   is idempotent. The grader (`response_evaluation.py`) is already patched in place.
6. Never pass `--specific_instances` to `response_evaluation.py` (silent misgrade).
7. The 5 side-log env vars + traps table live in `PLANBENCH_WT_HANDOFF.md` §5; the
   full decided-do-not-reopen list is its §3. Both still bind.
