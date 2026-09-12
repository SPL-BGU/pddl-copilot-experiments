# `development/` refactor — reduce the doc surface to what is load-bearing

**Written 2026-08-29.** Scan-and-propose only; nothing has been moved or edited.
Answer the `> ANSWER:` slots at the bottom and the mechanical pass can run in one
session. **No doc body gets rewritten** — this is moves, plus link repair, plus
three small index files.

---

## 1. What is actually there

| | count | size |
|---|---|---|
| markdown files | 54 | 1.61 MB |
| non-md (scripts, one .pptx, a `.DS_Store`) | 7 | ~90 KB |
| **total** | **61** | **1.7 MB** |

Where the bulk sits:

| block | size | share |
|---|---|---|
| append-only logs (`CHANGELOG` ×2, `paper_notes_discussions`, `OPEN_ISSUES`) | 620 KB | 38% |
| `planbench/` (14 files) | 268 KB | 17% |
| `archive/` (6 files) | 100 KB | 6% |
| everything else (30 files) | ~620 KB | 39% |

## 2. The problem is not wrongness — it is that status is invisible until you open the file

The docs are unusually well disciplined. Every superseded file already carries a
banner, corrections are stamped and dated, and the `227k → 273,600` scale error was
caught and marked in four places. Only **one** orphan exists
(`cost-breakdowns/SUMMARY.md`, nothing links to it).

So the error risk is not "a doc says something false." It is these four things:

**(a) 18 of 54 docs are dead-status, and you cannot tell from `ls`.**
Every one of them looks identical to a live doc in a directory listing. The banner
that says "do not take a number from this file" is *inside* the file, in prose. Any
reader — you at 1am, or an agent that grepped its way in mid-file and never saw
line 3 — pays the same cost to discover it. Grep is the normal way in, and grep
skips banners.

**(b) "What is left to do" is a 4-deep supersession chain.**
`next_steps_after_inflight_runs.md` (07-12) → `roadmap_eval_and_paper_completion.md`
(07-15) → `journal_phase0_handoff.md` (07-24) → `remaining_work_20260811.md` (08-11).
Each new one required banner edits on all its predecessors. The chain grows every
time, and the *current* answer is in a file whose name encodes a date that will look
stale in a month.

**(c) The same headline number appears at several values across sibling files.**
The PlanBench clean-WT figure reads 68.3 in six files, and 69.7 / Δ+21.8 survive as
"last-attempt" readings inside the same folder. All are correctly banner-marked
today — but that safety is prose an agent has to notice and believe, six times over,
rather than a fact it can look up once.

**(d) 16 referenced paths do not exist.** Including three from *live code*:

| dangling path | cited from |
|---|---|
| `development/archive/plans-executed/FRAMEWORK_EXTENSION_PLAN.md` | `pddl_eval/__init__.py:4`, `run_experiment.py:692`, `EXPERIMENTS_FLOW.md:282` |
| `development/archive/frontier/with_tools_probe_findings.md` | 4 docs (file is really in `archive/`) |
| `development/sweep4_plan_new_prompts.md`, `sweep4_fr_pivot.md`, `sweep_prompt_redesign_handoff.md` | `CHANGELOG.md` |
| `development/INVESTIGATION_vllm_oom_thinkon_20260511.md`, `SUBMISSION_STRATEGY_PROPOSAL.md`, `qwen3_6_35b_validate_plan_tool_inversion.md`, `ntster_h4_slot_recommendations.md`, + 8 more | assorted |

`FRAMEWORK_EXTENSION_PLAN.md` was deleted in `ec22cbe` (2026-04-30). It is fully
recoverable from git (597 lines), and `EXPERIMENTS_FLOW.md:282` still sends a reader
to it for the **"PR-3 drift from spec"** rationale — the only written record of why
the 10 PR-3 domains deviate from the original spec. That rationale is currently
reachable only by someone who thinks to run `git show`.

## 3. Proposal — three tiers, where the path *is* the status

One rule replaces eighteen banners:

> **`archive/` means: provenance only. Never a status, never a number, never a next action.**
> **`reference/` means: stable spec or guide. Accurate, but never a status.**
> **root means: live. If it is at the root, it is part of the work that is still open.**

### Tier 1 — root: the live working set (13 docs + 3 logs + 3 tooling files)

Derived directly from `remaining_work_20260811.md`'s four open jobs.

| doc | why it stays live |
|---|---|
| `STATUS.md` *(renamed from `remaining_work_20260811.md`)* | the entry point — see §4 |
| `journal_decisions_memo.md` | Job 2 spec (the e2e reframe) |
| `tool_call_vs_final_output_grading.md` | D1–D9 grading decisions Job 2 writes from |
| `sonnet_wt_vs_haiku_e2e_memo.md` | transcription-gap numbers Job 2 folds in |
| `iss024d_parity_prereg.md` | the gate on headline use of the overlay |
| `planbench/planbench_wt_paper_integration_plan.md` | Job 1 spec, 4/4 slots signed |
| `planbench/PLANBENCH_WT_FINAL_PHASE_HANDOFF.md` | Job 1's binding constraints |
| `planbench/planbench_wt_results_20260803.md` | Job 1's frozen numbers |
| `ntster_h4_prereg.md` · `ntster_h4_prereg_decisions.md` | Job 3, ratified, submit pending |
| `title_abstract_candidates.md` | Job 4, open `> ANSWER:` slots |
| `paper-git-overleaf-instructions.md` | CLAUDE.md points here before any sync |
| `CHANGELOG.md` · `OPEN_ISSUES.md` · `paper_notes_discussions.md` | append-only, house rule |
| `sync_overleaf.sh` · `make_overleaf_zip.sh` | tooling |

### Tier 2 — `reference/`: stable, code-pinned, never a status (10 docs)

`cluster_user_guide.md` · `sweep_prompt_bank_design.md` · `contamination_probe_plan.md` ·
`baseline_comparison_tool_use_benchmarks.md` · `grading_artifacts_findings.md` ·
`decision_audit_grading_and_frontier.md` · `frontier_rerun_framework_decision.md` ·
`planbench/planbench_wt_prereg.md` · `planbench/planbench_wt_prereg_decisions.md` ·
`CHANGELOG-archive.md`

These stay because code and skills cite them by path (`sweep_prompt_bank_design.md`
alone has 17 inbound references) or because a journal submission needs the prereg
reachable. They are just not things you read to learn what is happening now.

### Tier 3 — `archive/<line>/`: closed lines, provenance only (~22 docs, ~700 KB)

Grouped by the line they belong to so the folder stays navigable:

- `archive/planbench/` — `PLANBENCH_HANDOFF_v2.md`, `v3`, `PLANBENCH_WT_HANDOFF.md`,
  `PLANBENCH_WT_NEXT_STEPS_HANDOFF.md`, both calibration memos,
  `planbench_verification_20260730.md`, `planbench_v1_results.md`,
  `planbench_frontier_haiku_nt.md`, `planbench_wt_significance_brief.md`
- `archive/frontier/` — `frontier_rerun_handoff.md`, `frontier_haiku_phase_plan.md`,
  `frontier_with_tools_ladder.md`, `with_tools_probe_findings.md`
- `archive/decoupled/` — all 4 (line marked ✅ COMPLETE 2026-07-11)
- `archive/status-snapshots/` — `next_steps_after_inflight_runs.md`,
  `roadmap_eval_and_paper_completion.md`, `journal_phase0_handoff.md`,
  `journal_narrative_proposal.md`
- `archive/plans-executed/` — `decoupled_budget_plan.md`, `q1_grader_plan.md`,
  `simulate_normalizer_fix_plan.md`
- `archive/cost-breakdowns/` — the 3 memos + slides (`SUMMARY.md` already carries a
  superseded-figures note; the whole line is parked on the advisor cost verdict)

**Net effect:** the surface a fresh session must consider drops from **54 files /
1.61 MB** to **13 live docs + 3 logs**, about **776 KB**, and 460 KB of that is the
three append-only logs nobody reads end to end. The reading surface for "what is
going on" drops to roughly **316 KB across 13 files**.

Nothing is deleted. Nothing is rewritten.

## 4. Three structural fixes that do the actual error-reduction

Moving files is most of the win, but these three are what stop the problem coming back.

**Fix 1 — one stable entry filename, edited in place.**
Rename `remaining_work_20260811.md` → **`STATUS.md`** and from now on *edit it*
rather than writing a new dated successor. Dated snapshots go to
`archive/status-snapshots/`. The supersession chain becomes permanently length-1,
and no future doc needs banner edits on three predecessors. Keep the date *inside*
the file as a "last refreshed" line.

**Fix 2 — `NUMBERS.md`: one lookup for every headline figure.**
This is the only genuinely new content proposed, and it is small — a table, not
prose. One row per figure the paper will quote: the frozen value, the file it is
provenanced to, and the superseded values it replaces. Roughly:

| figure | frozen value | provenance | superseded readings — do not quote |
|---|---|---|---|
| PlanBench clean WT | 68.3 [64.5, 71.9], Δ+20.5, p=1.38e-13 | `planbench_wt_results_20260803.md` | 69.7; Δ+21.8 / p=2.7e-15 (last-attempt) |
| PlanBench Mystery WT | 71.8 vs 0.0 | same | — |
| bare-NT clean | 43.8 (CI-disjoint above GPT-4 34.3) | same | — |
| stripped-regrade NT | 4.3 | same | graded 0.0 (injection caveat) |
| corpus scale | **273,600** two-corpus | `title_abstract_candidates.md` §4 | **227k** (does not reproduce) |
| frontier Haiku solve delivered | ~95% | `sonnet_wt_vs_haiku_e2e_memo.md` | **13.5% — RETRACTED overlay artifact** |
| frontier simulate delivered | [52, 64] bounds | same | **0% — RETRACTED** |

That table is the single highest-value item here: it turns "trust six banners" into
"check one file," and it is exactly what `/verify-claims` should read first.

**Fix 3 — repair the 16 dangling paths.**
Rewrite live-doc and code references to real paths; add a `MOVES.md` old→new table
for the reorg. Per the house rule the **append-only logs are not rewritten** — they
may cite pre-reorg paths as provenance, and `MOVES.md` resolves those. Two specific
repairs worth calling out:

- restore `FRAMEWORK_EXTENSION_PLAN.md` from `ec22cbe~1` into
  `archive/plans-executed/` so `EXPERIMENTS_FLOW.md:282`'s pointer to the "PR-3
  drift from spec" rationale resolves again;
- fix the docstring in `pddl_eval/__init__.py:4` and the comment at
  `run_experiment.py:692`.

Also: `OPEN_ISSUES.md` has 13 `ISS-###` entries of which at least 3 (024, 017, 025)
read as resolved — fold those into a "Closed" section at the bottom of the same
file so the open list is short enough to scan. And delete `development/.DS_Store`.

## 5. Cost

One session, mechanical. `git mv` preserves history; the risky part is link repair,
which is a scripted find-and-replace over a known path map plus a re-run of the
dangling-path scan in §2(d) to confirm zero remain.

---

## Decisions

**D1 — Archive or delete?**
Recommendation: **archive (move, keep in tree)**. Everything is in git either way, but
the closed docs are still grep-able provenance for numbers the paper will quote, and
you are heading into journal review where "show me where this number came from" is a
live question. Deleting saves ~700 KB of a 1.7 MB tree — real but not the bottleneck;
the bottleneck is *navigability*, which the move fixes on its own.

> ANSWER (archive / delete outright / archive now + delete after the paper lands):
>

**D2 — `STATUS.md` rename.**
Recommendation: **yes.** This is what stops the supersession chain from growing a
fifth link. Cost is updating ~3 inbound references.

> ANSWER (rename / keep the dated filename):
>

**D3 — `NUMBERS.md`.**
Recommendation: **yes, build it.** It is the one item that directly attacks the error
class you named. It is additive content, so if you would rather not add files, the
fallback is to put the same table at the top of `STATUS.md`.

> ANSWER (separate NUMBERS.md / fold the table into STATUS.md / skip):
>

**D4 — Scope of link repair.**
Recommendation: **repair live docs + code; leave append-only logs alone, covered by
`MOVES.md`.** Rewriting 65 dated CHANGELOG entries would violate the append-only rule
and churn a 244 KB file for no reader benefit.

> ANSWER (live+code only / everything including logs / live docs only, skip code):
>

**D5 — Restore `FRAMEWORK_EXTENSION_PLAN.md` from git?**
Recommendation: **yes**, into `archive/plans-executed/`. It is the only record of the
PR-3 domain-substitution rationale, and a reviewer asking "why these 10 domains?" is
plausible.

> ANSWER (restore / leave deleted and drop the three pointers instead):
>

**D6 — Should I execute this once answered?**
Recommendation: **yes, on a branch**, with the dangling-path scan re-run as the
acceptance check, and the diff kept to pure moves + link edits so it reviews quickly.

> ANSWER (execute on a branch / execute directly / hold):
>
