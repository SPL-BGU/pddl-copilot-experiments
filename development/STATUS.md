# STATUS — what is actually left

*Content last refreshed: 2026-11-22 (replan after Omer's advisor meeting: ICAPS 2027,
three research questions, and the goal is to complete the paper; the plan is
`roadmap.md`). Before that 2026-11-09 (the audit day: PRs #121 to #129 and #131 merged).
Earlier refreshes and the closed-work tables this file used to carry are in git history
and in `paper_notes_discussions.md`. Renamed from `remaining_work_20260811.md` on
2026-08-29.*

> **This is the single, stable entry point for project status, and it is edited in
> place.** Do not write a new dated successor doc. Update this file and move its date
> line. Before quoting any figure, check `NUMBERS.md`.

## The one-paragraph answer

**The goal is to complete the paper**, and the goals are set by the decisions of Omer
and his advisors. The venue is **ICAPS 2027**, with no track fixed on purpose. The paper
is the thesis: Omer's thesis is composed of his papers, so there is no separate thesis
document. The work is organised around **three research questions**: RQ1, do PDDL tools
help an LLM do planning-related tasks; RQ2, does the LLM choose the right tool; RQ3,
does it use the tool's output properly. The advisors' two action items, the literature
review and RQ1 written up with its experimental setting and results, land in the paper.
**No new runs**: the questions are answered from data already on disk. Everything is in
`roadmap.md`. **M1 and M2 have first results (2026-11-22). Next: Omer answers the
metric definitions (`roadmap.md` §6) and reads the literature review draft and the RQ1
tables; then M3, RQ1 in the paper.**

## Milestones (`roadmap.md` §4)

| # | milestone | state |
|---|---|---|
| M1 | Literature review, and from it the paper's related-work section | **draft written 2026-11-22**, `thesis_literature_review.md` (53 papers, 11 of them checked fresh that day; nine wanted papers listed as "to verify"; four questions for Omer at its end). Waits for Omer's read |
| M2 | RQ1 analysis: FP/FN on validate_plan, simulate against trace length, solved against hardness, plan length | **first tables done 2026-11-22**: `tools/reanalysis/rq1_metrics.py` (reproduces the frozen readout's counts before computing anything), tables in `NUMBERS.md` "RQ1 metrics", five models. Left: Omer's answer on the metric definitions, figures, the object-count view |
| M3 | RQ1 in the paper: experimental setting and results | waits for M2; its base is `draft_B3_B5_methods.md` and `draft_C4_transcripts.md` |
| M4 | RQ2 (tool choice) and RQ3 (use of the output): analysis, then in the paper | not started; data on disk |
| M5 | The whole paper follows the three RQs | after M3 and M4 |

## Where each line of data stands

| line | state |
|---|---|
| Main sweep, Study 1 (`sweep5v2-live`, `sweep6-live`) | data final. Used for the unaided and tool-verified figures and for every tool-call count (RQ2). It kept only the first 500 characters of each final answer, so it is not used where the full answer matters; its open-model delivered ranges stay retired |
| Delivered rerun, Study 2 (`delivered-rerun`) | complete, read out 2026-10-09 by the frozen code (`reference/delivered_rerun_readout.md`). Full answers stored. The source for RQ1 delivered comparisons and RQ3 on the open models. A separate-apparatus replication: parity failed at job level (Gemma 10/10, Qwen 15/20) |
| Claude runs (Sonnet 4.6, Haiku 4.5) | data final, full answers stored; their own runner, never pooled with the open models. Haiku's tool arm on the renamed corpus ran on 2026-07-12 and is analysed (PR #125) |
| PlanBench | closed; in the tex (PR #114) |
| Steering control (nt-ster H4) | closed 2026-08-29, all six units PASS; in the tex appendix |
| Built but never run: new model families, larger context windows, the binding JSON constraint, harder test items, the 120 larger IPC 2023 problems with planner ground truth | merged code and data, kept as they are. No model ran on any of it, and no run is planned (Omer, 2026-11-22: no new runs) |
| Paper | the 09-19 text plus PRs #110, #111, #114, #115 and #123. Still organised by RQ1 to RQ6 and the scorecard; M5 replaces them. Already typeset with the AAAI-27 author kit, which is what ICAPS 2027 asks for |

## Rules that bind every step

- Study 1 and Study 2 are never pooled into one number, and a rerun figure never stands
  in for a canonical cell.
- Any comparison that needs the full final answer uses the rerun and the Claude runs,
  never the main sweep.
- Claude figures are exact except simulate delivered (bounds); `iss024d` is a separate
  apparatus and never resolves an UNDECIDED cell; gaps are computed paired within a
  corpus.
- Frozen corpora are never re-graded in place. A corrected figure goes beside the frozen
  one, marked post hoc. New analyses of old data are exploratory and are said to be so.
- `NUMBERS.md` before prose; `/verify-claims` on every edit with a number;
  `/freeze-protocol` before hashing any analysis code.
- Never copy the rerun readout's "sampled under the per-task JSON constraint" sentence:
  it is false (`reference/weakness_consolidated.md`, the Q3 note).
- The 35B calling rate: quote both runs (68.0 and 82.7); "bigger calls less" is a
  direction only.
- Ping Omer before any SSH or SLURM action. Itemize any dollar spend before making it.

## How work is done

**`main` is the single line of work** (since 2026-09-18). Every change goes on a short
branch off `main` and reaches `main` by PR, and Omer merges. Doc-only record changes in
`development/` are the exception. A merged PR that touches the synced paper files pushes
to Overleaf by itself. Run `development/sync_overleaf.sh` from the main checkout,
**pull before push** (`paper-git-overleaf-instructions.md`).

**Pinned commits.** The rerun harness is tag `delivered-rerun-harness` (`4b2fe6e`) and its
frozen analysis is tag `delivered-rerun-analysis-frozen` (`d558946`, package
`822aace…`). PR #117 was a squash (`4147a0c`), so both are reached through their tags,
not through `main`'s history.

**The frozen check before each PR that touches analysis code.**
`python -m tools.delivered_rerun.run --print-package-hash` must end with `822aace9ef8a…`
(24 files). The sha256 of each of `tools/ntster_{h4,factorial,f_gate,common}.py` must
appear in `reference/ntster_h4_prereg.md`, and that of `tools/budget_probe_analysis.py`
in `reference/frontier_budget_probe_prereg.md`. `tools/claude_api_batch.py` changed in
PR #131 on purpose (`MOVES.md`). `tests/test_delivered_rerun_analysis.py` fails 1 of 428
inside the main checkout because the venv sits inside the repo; it passes from a
worktree whose venv is outside. Not a code fault.

**Data in a fresh checkout.** `results/` holds only tracked files. The canonical corpora
come from the checkpoint zips (`checkpoints/delivered-rerun/README.md`, "Restore").
`results/derived/gt_cache.json` and the 09-12 overlay files exist only on the laptop.

## Venue and outside facts

- **ICAPS 2027** (advisors, 2026-11-22), June 27 to July 2, 2027, Columbia, SC. **No
  track is fixed** (Omer, 2026-11-22). Facts only, from the official call read that day:
  the main track's abstract is due 2026-12-07 and its paper 2026-12-14 (UTC-12), in the
  AAAI-27 author kit; the 2027 demo call is not published yet.
- **Writing:** the venue's format only, no word cap (advisors, 2026-11-22).
- **JAIR and TMLR:** no longer the target. AAAI-27: dropped earlier, the deadline passed.
- **Budget:** a grant covers what is planned (Omer 2026-10-10). No spend is planned now.

## Decided and still binding

- **Who sets the goal (Omer, 2026-11-22):** from now on the project's goals are set by
  the decisions of Omer and his advisors. The agent recommends and carries out; it does
  not add goals, reframe the research questions or bring back dropped work by itself.
- **Research questions:** the three of `roadmap.md` §2 (advisors, 2026-11-22). The old
  open decision E1 is closed by this.
- **The advisor meeting happened** (reported 2026-11-22), so the hold R7 on sending the
  manuscript and the brief is overtaken. The standing rule stays: never give "wait for
  the advisors" as a reason to hold a task.
- **Release:** BGN Technologies owns research artifacts by default. Code MIT, data
  CC BY 4.0, copyright line naming BGN (confirm its exact legal name), Omer as author in
  `CITATION.cff` and on the Zenodo DOI, lab SPL-BGU. Timed against anonymous review.
- **pyval case fix (ISS-027):** `pddl-pyvalidator` 0.1.6 released by Omer and pinned in
  the validator plugin 3.1.1 (SPL-BGU/pddl-copilot #60). The cluster's plugin venv still
  holds the old version (`launch-server.sh` never upgrades an existing `.venv`); it
  matters only if something runs there again.
- **No new runs** (Omer, 2026-11-22). Every planned experiment and feature that does
  not serve the three questions is dropped, not parked.

## Open PRs (2026-11-22)

**Merged 2026-11-22** (Omer: merge the ones that are correct). Each was checked first:
its tests pass, its scripts rerun on the laptop data give the committed outputs, and the
frozen package hash is unchanged. Conflicts with `main` were additive (lists and
`NUMBERS.md` blocks where both sides added lines) and were resolved by keeping both.

- **#136** ISS-028 and ISS-029 post hoc splits, and **#130** ISS-027 scope and Gemma
  thinking (taken out of draft).
- **#133** checkpoints follow-up. Its refresh script was run in check mode only; the
  write step is still Omer's to run on the laptop
  (`python3 tools/checkpoints/refresh_frontier_overlays.py --write --force`). Until then
  `checkpoints/e2e-overlay/derived_reports.zip` holds the 07-17 table (456 rows), not
  the 460-row one.
- **#135** a comment in `main.tex` and the old deck PDF removed. The Overleaf sync it
  triggered succeeded.
- **#138** ground truth for 120 larger IPC 2023 problems. The 1800 s pass on the hard
  tier is still partly done (17 and 11 runs pending in the two 1800 s rows of
  `NUMBERS.md`). No model has run on these problems and none is planned to.

**Closed 2026-11-22** (Omer accepted the recommendation): **#132** (tracking file seeded
with the earlier plan) and **#137** (PlanBench tool prompts for the open models). Both
branches are kept.

**Still open, on hold by decision:** **#134** (release files: licences, `CITATION.cff`,
domain sources). It waits while a submission is under anonymous review, because the files
name Omer and BGU.

## Hygiene (Omer's to run)

- Agent worktrees under `.claude/worktrees/` and their merged branches:
  `git worktree list`, then `git worktree remove <path>` and `git branch -d`.
- `checkpoints/sweep6-live/.DS_Store`; the untracked `rq-sweep5v2` pptx and PNGs; two
  old stashes from `paper/aaai27`.
- The cluster checkout was last seen on `harness/delivered-rerun` at `4b2fe6e`
  (2026-10-10). Re-check only if something runs there again.

## Open decisions

One: the RQ1 metric definitions, `roadmap.md` §6 (six choices, each with the other
option beside it). The first five decisions of the replan are answered (`roadmap.md` §7).
