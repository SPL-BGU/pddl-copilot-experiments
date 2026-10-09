# STATUS — what is actually left

*Content last refreshed: 2026-10-09 (delivered rerun complete and read out by the
frozen code; N1b updated; every open PR merged: #117, then the paper stack #110, #111,
#114, #115; the descriptive §6 tables and the E4 hand read done). Before that: 2026-10-02 (resume-verify; Q1/Q2/Q3/Q4 of the
weakness list answered; the $0 re-analysis package delivered; the delivered rerun
pre-registered. Earlier refreshes are in git history). Renamed
from `remaining_work_20260811.md` on 2026-08-29.*

> **This is the single, stable entry point for project status, and it is edited in
> place.** Do not write a new dated successor doc. That is what produced the four-deep
> supersession chain now sitting in `archive/status-snapshots/`. Update this file and
> move its date line. Before quoting any figure, check `NUMBERS.md`.

## The one-paragraph answer

**One experiment is now owed: the delivered rerun** (`reference/delivered_rerun_prereg.md`,
decided 2026-10-02). The paper names the delivered answer as its main outcome and cannot
measure it on the open-weight tool arms; the rerun measures it, after three harness
fixes. The four local re-analyses of 2026-10-02 (`reanalysis_*.md`) also changed what
the paper can claim: two statistical verdicts, the PlanBench equivalence sentence, the
cost claim, and the reading of the open-weight delivery gap. The tex is the
09-19 text plus PRs #110, #111, #114, #115 (merged 2026-10-09). After the rerun reads out comes one drafting
pass, then the pre-submission mechanics (N3) and the advisor round (N2).

## State by line

| line | data | analysis | paper |
|---|---|---|---|
| PlanBench (NT + WT) | DONE, archived + MANIFEST-verified | DONE, `verify_promotion.py` re-derives every number | **DONE 2026-08-11**, section in tex + Overleaf, re-verified 09-07 |
| Single-tool suite | DONE (07-17) | DONE (e2e overlay D1–D9 + Phase 5, pooled table regenerated) | **DONE 09-08 / 09-12**, the full e2e reframe (D2/D-J2 = option a), batches 1+2, in Overleaf; budget-probe sentence landed 09-12 |
| nt-ster H4 control | **DONE 2026-08-29** (6 cells, 9,120 rows each) | **DONE**, all six units PASS, branch PASS | **DONE 2026-09-13**, caveat-only integration + review revisions, in Overleaf |

## Closed work

Hashes that the logs record as "`paper/aaai27` `<hash>`" are on `main` since PR #101
(merge commit `75e070f`, not squashed). Figures live in `NUMBERS.md`, not here.

| what | tex location | commit | where the record lives |
|---|---|---|---|
| **Job 1** — PlanBench Act 4 section (2026-08-11, re-verified 09-07 against the signed plan: all nine skeleton items and the plan §4 companion edits present) | `\section{External Validity on PlanBench}`; Future Work; Related Work anchors | `67ea69c` + `644f8bd`; Overleaf `dff7ffb`; gate was PR #93 (`1638013`) | `paper_notes_discussions.md` 08-11, 09-07; `NUMBERS.md` PlanBench rows; plan: `archive/planbench/planbench_wt_paper_integration_plan.md` |
| **Job 2** — single-tool e2e reframe: delivered is the primary surface, tool-verified is the mechanism layer (batches 1+2, 09-07/08) | Results: "How to read our numbers" table, `fig:funnel` (with the PlanBench FORMALIZE bar), `tab:scorecard`, the four delivered-surface figures, frontier delivered cost-of-pass | `125cc7a` + `dbea3d7`; Action 34245382827 | `paper_notes` 09-07, 09-08; `NUMBERS.md` Job 2 block; `reference/job2_delivered_reframe_worknote.md` (§2 verdicts: 13/25 undecided supersedes the memo's "2/25"); spec `journal_decisions_memo.md` §3 |
| **Frontier budget probe** (run + readout ratified 09-12, $40.68) | Results, the output-budget paragraph (64,000-token allowance) | `5466cb6`; Overleaf `d922237` | `paper_notes` 09-08 to 09-12; `NUMBERS.md` "frontier budget probe" row; `reference/frontier_budget_probe_readout.md` |
| **Job 3** — nt-ster H4 control, caveat-only integration (run closed 08-29, corrective re-run 08-30: verdicts unchanged, secondary numbers revised; tex 09-12, revised on Omer's four points 09-13). The PASS sentence drops the "replicated attribution" clause and the deviations (prereg §9.1 + §9.2) are declared, both as pre-registered | Results CALL-beat paragraph; Limitations note; Methodology control-arm sentence; appendix `\paragraph{The steering control.}` with `tab:ster-units`, `tab:ster-tasks`, `tab:ster-drift` | `6027d68` + `7c0502a`; Action 34743222922; Overleaf `2ab9bb5` | `paper_notes` 08-29, 08-30, 09-12 (night), 09-13; `NUMBERS.md` nt-ster block; `reference/ntster_h4_final_readout_20260829.md` (quote the revised readout only); design `reference/ntster_h4_prereg.md` |
| **Job 4** — small items: `guided_json` $0 audit (constraint never bound; fix stays parked per D4), "delivery gap" term check, title/abstract candidates | none (fed N1 and the Limitations wording) | `ad09c80` (PR #94, 2026-08-20) | `paper_notes` 08-17 (the corrected audit figures; **quote those, not earlier ones**), 08-20; `CHANGELOG.md` 08-20; `NUMBERS.md` "Corpus scale" (273,600; the memo's "227k" does not reproduce); `reference/title_abstract_candidates.md` |
| **Paper housekeeping** 09-13/14 — serving environment pinned, vLLM 0.22.0 disclosure footnote kept (Omer 09-14: keep the disclosure, no rerun), checklist item flipped to *yes*, `NUMBERS.md` placeholder filled, no corpus total in the tex | `\subsection{Models and Serving}` + footnote; reproducibility checklist | `4eb4751`; Action 34814416712; Overleaf `d884bd3`; doc merge `45de99c`; PR #100 | `paper_notes` 09-13 (later, night), 09-14; `reference/serving_env_20260913.md` |
| **N1** — D-J6 applied: title D, the two-gate abstract with the scale clause (four verified numbers, 200 words), "invocation rate" at all 14 sites | `\title`, abstract, 14 term sites | `b27ef23` + `b045f07`; Action 35332662004; Overleaf `a0b8c84` | `paper_notes` 08-20 (D-J6), 09-15/18, 09-18 (scale clause); `NUMBERS.md` "Abstract — the four figures"; `reference/title_abstract_candidates.md` §4–5 |

**Rules that still bind any edit to these sections:** frontier figures are exact except
simulate delivered (bounds); sweep5v2 with-tools figures are strict bounds; iss024d is
**separate-apparatus** (job-level parity FAILED 07-17), so it never resolves an UNDECIDED
cell; gaps are computed paired within a corpus.

## How work is done now

**`main` is the single line of work** (since 2026-09-18, PR #101 + #102). The long-lived
paper branch and its second checkout are deleted; `paper/main.tex` on `main` is the
paper. Every change goes on a short branch off `main` and reaches `main` by PR. The agent
cannot merge an unreviewed PR, so Omer merges. A merged PR that touches the synced paper
files pushes to Overleaf by itself. Run `development/sync_overleaf.sh` from the main
checkout, **pull before push**. Details: `review_round_handoff.md`,
`paper-git-overleaf-instructions.md`.

## External gates (resolved 2026-08-30, `paper_notes` 08-30)

- **Budget:** resolved. A small grant covers everything planned. Itemize expenses before any new spend; nothing dollar-denominated is committed.
- **Venue:** JAIR primary, TMLR fallback is the working target (Omer). Formal advisor ratification (memo §10.1) is the last step, see N2.
- **AAAI-27:** formally dropped, the deadline passed.
- **Cost-of-pass deck:** the advisor verdict on its content is still open, as a paper-content question only (N2 item 4).

## Decided

- **R1** order of the writing jobs: PlanBench first (`paper_notes` 08-11; confirmed 09-07).
- **R2** nt-ster: ratified, run and closed, all six units PASS (`paper_notes` 08-11, 08-29).
- **R3** Llama-3.1-8B probe: keep, sequenced after nt-ster (`paper_notes` 08-11). nt-ster closed 08-29, so it is unblocked; see N4 and R8.
- **R4** Job 4 small items: yes, run alongside Job 1 (`paper_notes` 08-11; done 08-20).
- **R5** abstract under N1: apply D-J6 with a new abstract, two gates, findings first, four numbers, PlanBench in, at most 200 words, Shape A (`paper_notes` 09-15/18).
- **R6** go-ahead for the tex edits: go, once R5 is answered (`paper_notes` 09-15/18).
- **R7** send the manuscript and the brief: **hold** (Omer 09-19). Work proceeds; the advisors are consulted later and Omer says when a meeting happened. Never give "wait for the advisors" as a reason to hold a task (`paper_notes` 09-19).
- **R8** Llama-3.1-8B probe: **hold** (Omer 09-19). Not a major addition; the weakness review (N1b) comes before any further experiment (`paper_notes` 09-19).

---

## Next steps

Order: N1b (rerun + drafting pass) → N3. N2 happens when Omer schedules it. N4 is
optional and on hold (R8). N5 is minutes.

### N1b — Weakness list and what came out of it (in progress)

The working list is **`weakness_consolidated.md`** (C1–C22, decisions Q1–Q10). It
replaced `weakness_review.md` (deleted 2026-10-02; in git history at `66cc314`) and the
never-committed `referee_weaknesses.md` (lost; its content survives only as merged into
C1–C22).

Answered 2026-10-02 (`paper_notes` 10-02): **Q1 run · Q2 add the Gemma neutral-prompt
arm · Q3 yes (PR #110) · Q4 all.** Still open in that file: Q5–Q10.

**Done 2026-10-02**

- PR #110: the false "JSON-constrained decoding remains" sentence corrected, the
  `guided_json` Limitations sentence added, the "budget, not the grader" inference
  removed. Merged 2026-10-09.
- PR #111: consistency read groups A–D applied. Merged 2026-10-09. Group E: see
  PR #115 below.
- The $0 re-analysis package (Q4), four findings docs + `tools/reanalysis/`:
  `reanalysis_statistics.md`, `reanalysis_planbench.md`, `reanalysis_breakdowns_cost.md`,
  `reanalysis_transcripts.md`. Headlines are in `paper_notes` 10-02. **None of their
  numbers is in `NUMBERS.md` or the tex yet**; each needs `/verify-claims` on the edit
  that adopts it.

**In progress**

1. **Harness fixes for the rerun: on `main` since 2026-10-09 (PR #117)** (`4b2fe6e`, tag
   `delivered-rerun-harness`):
   final-request overflow retry, leaked Gemma channel prefix, storage cap 65,536, a
   `neutral` prompt style. Independently reviewed; four findings fixed.
2. **Delivered rerun: COMPLETE and READ OUT 2026-10-09** (`reference/delivered_rerun_prereg.md`
   §8c; readout `reference/delivered_rerun_readout.{md,json}`; figures in `NUMBERS.md`
   "Delivered rerun"). Seven cells full; the 9B unaided cell needed one resume (22417213;
   prereg §9 deviation 1, execution only). **Parity fails at job level** (Gemma 10/10,
   Qwen 15/20), so the whole rerun is a separate-apparatus replication. **R1 No delivered
   harm · R2 Unresolved · R3 title changes to the two-gate reading · R4 met · R5 the
   directive suppresses calling.** The cluster checkout may now leave `4b2fe6e`.
3. **Analysis code: FROZEN 2026-10-03** (`d558946`, tag `delivered-rerun-analysis-frozen`,
   package `822aace…`); ran on live data 2026-10-09 with no halt and no tripwire. On `main`
   since 2026-10-09 via PR #117, a squash (`4147a0c`), so `4b2fe6e` and `d558946` are reached
   through their tags, not `main`'s history; frozen files re-checked unchanged (prereg §8).
   **Descriptive pieces done 2026-10-09:** the E4 hand read (§8b 13) and the §6 tables
   (per wording, per domain, classical vs numeric, clipped allowances, cost at 1:1 to
   5:1, the Gemma no-call answers read in full), in
   `reference/delivered_rerun_secondary/secondary.md`; figures in `NUMBERS.md`. Nothing is left
   open under the prereg.
4. **PlanBench wording** (in the tex since 2026-10-09, PR #114): corrected-extractor
   numbers beside the shipped ones; the "well inside ±7.5" sentence replaced.

**Next: one drafting pass (the rerun has read out)** covering the rerun results (as a separate-apparatus replication), the new title (R3), the statistics paragraph
(paired, domain-clustered tests; two verdicts downgraded; the GLMM sentence), the cost
paragraph, the test-data description, the per-wording and per-domain tables, the
delivery-gap section (incl. the held group E rows E3a, E3b, E8b), and Q5 / Q8 / Q9.

### N2 — Coauthor + advisor review round (Omer; the brief is written)

**Brief DONE 2026-09-18: `advisor_brief.md` (PR #103) holds the six questions below
with recommendations and `> ANSWER:` slots. Do not rewrite it, the advisors answer in
place. R7 (09-19): sending is on hold; Omer consults them later and says when. Nothing
else waits on this round except the JAIR reformat (venue ratification).**

No coauthor has edited Overleaf since the 08-11 sync (every pull since returned clean).
The six questions (memo §10):

1. venue ratification: JAIR primary, TMLR fallback with the three pre-committed
   rejection branches, AIJ only on override (memo §5);
2. confirm the Sept-2026 thesis needs a *submitted* manuscript, not an acceptance;
3. record the journal pivot formally (AAAI-27 dropped 08-30);
4. verdict on the cost-of-pass deck content (`archive/cost-breakdowns/`);
5. storage-fixed rerun of ~5 headline cells: contingency only (default) or run before
   submission;
6. (grant-reopened 08-30) Sonnet-tier PlanBench extension: run or leave excluded.

### N3 — Pre-submission mechanics (agent; reformat after the venue is ratified)

- DONE 09-19 (PR #107, `3196112`): the overfull scorecard `table*` and the three stale
  comments in Overleaf-synced files.
- DONE 09-19: the *simulate* "0/3,000" in the GLMM sentence. Verified on
  `sweep5v2-live`, now qualified "format-exact on the shared-budget corpus", with a
  `NUMBERS.md` row (Job 2 block). Three more unqualified sites are row A5 of the
  consistency read.
- **Consistency read: groups A–D applied 2026-10-02 (PR #111); group E applied by
  PR #115** (27 rows; E3a, E3b, E8b held for the delivery-gap rewrite). Both merged
  2026-10-09. Group F: nothing drafted.
- **GLMM refit: computed 2026-10-02** (`reanalysis_statistics.md` §3: log-odds +7.80,
  SE 0.29). The tex sentence still quotes the variational output; the edit belongs to
  the post-rerun drafting pass.
- **Curated code and data release at publication.** The tex reproducibility checklist
  promises it. Tracked here.
- JAIR reformat: the tex is `article` + `aaai2027.sty`; JAIR uses its own style file.
  Mechanical, but it touches every float, so do it once, after the venue is ratified.
  It includes **de-anonymising**: the author block, the links block, and leaving
  `[submission]` mode.
- Cover letter with the arXiv:2509.12987 delta statement (memo §5: each control flipped
  a headline; extensive-revision defence). Writing it also closes ISS-013.

### N4 — Optional experiments (none owed)

- **Llama-3.1-8B second-family probe** (R3). Unblocked since nt-ster closed 08-29: the
  rule "do not touch `PDDL_VLLM_VERIFIED_MODELS` while nt-ster is live" has lapsed. $0,
  cluster GPU-h only. Needs its own harness branch + PR for the `vllm_lookup` case, a
  kill-gate, and a ping to Omer before any cluster action. **On hold (R8, 09-19):** not
  a major addition; revisit after the weakness review (N1b). It is the ready answer to
  "is the invocation finding Qwen/Gemma-specific?".
- Sonnet-tier PlanBench extension and the storage-fixed rerun: advisor calls, N2.
- **Recorded as not planned** (`paper_notes` 09-18; both came out of the 06-20 iter-2
  review and were never run and never dropped until now): the clean cluster BF16-35B
  precision control (left at "run if time"; the within-model reframe that was its
  fallback is what the tex says), and the schema-salience probe (approved as the first
  compute item, but `--schema-variant` was never built).

### N5 — Hygiene

- Cluster checkout still sits on the dead branch `paper/iter2-decoupled-run` (remote
  gone). Switching it to `main` needs SSH, so **ping Omer first**.
- `OPEN_ISSUES.md` ISS-022 strike: done in the 09-18 documentation cleanup.

### Open decisions

- `weakness_consolidated.md` Q5–Q10 (rewriting scope, title, more model families, the
  VAL cross-check).
- `consistency_read_E_drafts.md` (the reworded sentences).
- The PlanBench wording drafts, once shown.
- `advisor_brief.md` question 5 still recommends "contingency only" for the rerun. The
  rerun was decided 2026-10-02, so that recommendation is out of date; the brief is
  answered in place by the advisors and is not rewritten.
