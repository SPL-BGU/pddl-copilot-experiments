# STATUS — what is actually left

*Content last refreshed: 2026-09-08 (Job 2 batches 1+2 pushed + Overleaf-synced;
frontier budget probe RUN 09-12, readout awaiting ratification). Renamed from `remaining_work_20260811.md`
on 2026-08-29.*

> **This is the single, stable entry point for project status, and it is edited in
> place.** Do not write a new dated successor doc — that is what produced the
> four-deep supersession chain now sitting in `archive/status-snapshots/`. Update
> this file and move its date line. Before quoting any figure, check `NUMBERS.md`.

**Entry point for "what is actually left."** Written after PR #93 merged to main
(`1638013`). Supersedes the status rows in `journal_phase0_handoff.md` (07-24) and
`roadmap_eval_and_paper_completion.md` (07-15); both stay for their decision records.

## The one-paragraph answer

**No experiment is owed for either line's headline claims.** PlanBench-WT is closed
(RESCUE, SUPPORTED, four-rung ladder, n=600/cell). The single-tool line's data has
been complete since 2026-07-17 (sweep5v2-live + sweep6 + iss024d-e2e-live + the
Haiku/Sonnet frontier corpora, all graded). **The nt-ster H4 control closed 2026-08-29
— all six units PASS — so there is now no unrun experiment on either line.** What is
left is **writing**: Jobs 2 and 3 below. Job 1 (PlanBench Act 4) is DONE — it landed
2026-08-11 (`67ea69c` + `644f8bd`) and synced to Overleaf the same day; this file
wrongly carried it as NOT STARTED until 2026-09-07. Last paper commit is `644f8bd`,
2026-08-11.

## State by line

| line | data | analysis | paper |
|---|---|---|---|
| PlanBench (NT + WT) | DONE, archived + MANIFEST-verified | DONE, `verify_promotion.py` re-derives every number | **DONE 2026-08-11** — section in tex + Overleaf, re-verified 09-07 |
| Single-tool suite | DONE (07-17) | DONE (e2e overlay D1–D9 + Phase 5, pooled table regenerated) | **DONE 09-08** — the full e2e reframe (D2/D-J2 = option a), batches 1+2 on `paper/aaai27`, in Overleaf; probe sentence pending |
| nt-ster H4 control | **DONE 2026-08-29** (6 cells, 9,120 rows each) | **DONE** — all six units PASS, branch PASS | **NOT STARTED** — caveat-only integration, see Job 3 |

Evidence on the paper side: the Results sections of the main suite still carry the
old tool-verified framing (the Job 2 reframe is genuinely untouched), but the
PlanBench section EXISTS in `paper/main.tex` (`\section{External Validity on
PlanBench}`, ~L972–1181) — the old "zero occurrences of 'delivered'" evidence line
is void.

## Job 1 — PlanBench Act 4 section: DONE (2026-08-11, verified 2026-09-07)

Landed on `paper/aaai27` as `67ea69c` (section) + `644f8bd` (plain-language /
AI-tell pass), both 2026-08-11; the Overleaf auto-sync Action ran green the same
day and the bridge remote's head (`dff7ffb`) IS that sync — no coauthor web edits
since, nothing to pull. Re-verified 2026-09-07 against the signed plan
(`planbench/planbench_wt_paper_integration_plan.md`) and `NUMBERS.md`:

- All nine skeleton items present: opening + headline/secondary split, NT table
  (GPT-4 as labelled reference, no test), WT 2×2 (first-draw 68.3 / Δ+20.5 /
  p=1.4e-13; Mystery 71.8 vs 0.0), ladder in the body (0.7/0.0/0.5/71.8),
  formalization mechanism (96.3/97.8; the "99.5% of Mystery domains" sentence is
  correct — Mystery domain-equivalence 597/600 = 99.5, distinct from clean
  P(solvable|equiv) 99.5), two-layer NT audit (graded 0.0 + stripped 4.3,
  p=6.4e-112), dialect/exhaustion ownership, cost ($39.87/$2.61/≈$46), single-tier
  limitation.
- Plan §4 companion edits done: Future Work rewritten to point at the section;
  Related Work anchors H&Z (70/100 vs 0/100) and La Malfa with the corrected
  3×50/task pool.
- NOT done (and not owed here): the funnel-figure FORMALIZE amendment — no funnel
  figure exists in the tex at all yet; that figure is the journal memo §2 Figure-1
  spec and rides with Job 2. FORMALIZE is covered in prose meanwhile.

## Job 2 — the single-tool e2e reframe (P1 / D2 = D-J2 = option a)

**BATCHES 1 AND 2 LANDED (2026-09-07 / 09-08) — `125cc7a` (batch 1) + `dbea3d7`
(batch 2) on `paper/aaai27`, PUSHED 2026-09-08 on Omer's go and synced to Overleaf
(Action run 34245382827 green; Overleaf had no coauthor edits since the 08-11 sync,
verified byte-identical before the push).** Grounding:
`job2_delivered_reframe_worknote.md` (§2 verdicts — read §3 before reviewing: the
memo's "2/25 undecided" is superseded by the derived 13/25; §8 = batch-2 tables).
Batch 2 delivered: funnel Figure 1 (+ PlanBench FORMALIZE bar), the four Results
figures on the delivered surface, frontier delivered cost-of-pass, validate_domain
delivered balanced accuracy, NUMBERS.md Job 2 block. Generator
`paper/figures/make_paper_figures.py` lives on main (PR
`job2/batch2-budget-probe-prereg`); merge main into `paper/aaai27` after it lands so
the branch can regenerate its own figures.

**Frontier budget probe: RUN 2026-09-12, READOUT AWAITING RATIFICATION** (prereg
ratified 09-08, budget 64,000 + analysis frozen 09-10, PR #98 merged `bbcf111` with
hashes re-verified on main). All four legs ran under the frozen code; measured cost
$40.68 (expected $50–65, cap $213); no §3.6 tripwire fired. Verdicts per the frozen
script: **Sonnet PARTIAL** (LEN-FIT 16/25 = 64% vs ET-FAIL control 7/19 = 37%, Fisher
p = 0.069; delivered 70 [60.4, 78.1] vs ref ⟨49, 62⟩), **Haiku H1** (12/17 = 71% vs
1/12, p = 0.001; delivered 65 [55.3, 73.6]; H2 supported 0/14 DECLINE converted). Arm
contrast at 64K: Sonnet +26 pp, Haiku +7 pp. Readout + ratification slots:
`frontier_budget_probe_readout.md`. Reference cells unchanged everywhere.

**What is left on Job 2:** Omer ratifies the readout (§6 of the readout doc) → NUMBERS
"budget probe" block → the one-or-two-sentence Delivery Gap edit + Limitations clause
on `paper/aaai27` (pull Overleaf first). The tex reframe is in Overleaf now.

The one substantive paper change left on the main suite, and the larger of the two.
Spec: `journal_decisions_memo.md` §3. It makes **delivered** the single primary
surface for tool-lift claims, demotes tool-verified to the mechanism layer, adds the
"how to read our numbers" table at the head of Results, and enforces the notation
gate (Wilson CIs and censor-bounds typographically distinct).

Corpus rules that bind every sentence: frontier exact except simulate delivered
(bounds); sweep5v2 WT = strict bounds with 2/25 cells staying UNDECIDED; iss024d is
**separate-apparatus** (job-level parity FAILED 07-17) so it never resolves an
UNDECIDED cell; gaps computed paired within a corpus. Material to fold in: the
transcription gap (solve +5pp both tiers, simulate ≈35–50pp length-driven,
`sonnet_wt_vs_haiku_e2e_memo.md`) and the de-censored NT delivered columns.

This is where the retracted claims finally get their replacement text, so it is also
the cleanup of the simulate sole-source-floor thread.

## Job 3 — nt-ster H4 control: RUN COMPLETE, integration owed

**The experiment is done.** Closed 2026-08-29 on branch `run/ntster-h4`: six cells,
9,120 rows each, **all six units PASS**, paper-level branch **PASS**. Every one of the
8 ELIGIBLE task cells is EQUIVALENT. Figures: `NUMBERS.md`. Full readout:
`ntster_h4_final_readout_20260829.md`. Design of record: `reference/ntster_h4_prereg.md`.

The result it was commissioned for, in the matched cell: gemma `validate_plan`
`think=off` is **+72.0pp with tools and +0.63pp [−0.46, +1.73] without**. The steering
effect is attributed to the directive's interaction with tool access.

**What is left is writing only**, under the pre-committed caveat-only cap — CALL beat +
Limitations in the body; per-task table, F gate, MDE table, drift check, the on-mode
apparatus failure and the two §9.1 deviations in an appendix. Scope approved
(final readout O4); no tex touched.

**2026-08-30: post-review corrective re-run.** The PR #96 correctness review found
defects in the frozen analysis code (censored rows scored as successes, a mis-specified
governing estimator, a degenerate mechanism section — prereg §9.2). Code fixed,
re-frozen, everything regenerated: **verdicts unchanged, secondary numbers revised** —
quote only NUMBERS.md / the revised readout.

Things the integration must carry, pre-registered and none optional:

- **§5's PASS sentence drops its "replicated attribution" clause.** After the 08-30
  correction both §4(b) interactions are positive and exclude zero (9B +8.12
  [+4.61, +11.63], replicated; 35b +2.62 [+0.74, +4.50]), but 35b fails sign-match
  against an essentially null (−0.11pp) May reference, so the per-model conjunction is
  not met. Directionally consistent with the attribution; the clause is still removed,
  as pre-registered.
- **The deviations get declared** (`reference/ntster_h4_prereg.md` §9.1 + §9.2): the
  roster expanded 3→4 models after interim results; the `think=on` arm was rerun with
  `--reasoning-parser none` after the preregistered configuration produced a void
  corpus; and the 2026-08-30 post-review code corrections with the re-freeze.

**Follow-on now unblocked:** the Llama-3.1-8B second-family probe (R3) was sequenced
strictly after nt-ster and no longer has a blocker. It needs its own branch + PR for a
`vllm_lookup` case; the "must not touch `PDDL_VLLM_VERIFIED_MODELS` while nt-ster is
live" constraint has lapsed.

## Job 4 — small items: DONE (PR #94, 2026-08-20)

All three landed in `ad09c80`: the `guided_json` $0 local audit (constraint never
bound — 526/88,781 no-tools rows conformant, 0.59%; validate_* shielded by the
VERDICT trailer, exposure on solve/simulate only; fix stays parked per D4), the
"delivery gap" collision check (term unclaimed; one near neighbour to distinguish
if ever cited), and the title/abstract candidates
(`development/title_abstract_candidates.md`). PR #94 also flagged that the memo's
"227k trials" scale claim does not reproduce from disk (counted two-corpus figure
273,600) — resolve before that number enters tex.

## External gates — mostly resolved 2026-08-30

- **Budget: RESOLVED.** Omer holds a small grant sufficient for everything planned;
  cost is no longer a design constraint. Requirement: itemized expenses before any
  new spend. Ledger in `paper_notes_discussions.md` 2026-08-30 — nothing
  dollar-denominated is currently committed; the one decision the grant reopens is
  the Sonnet-tier PlanBench extension (was excluded on budget alone).
- **Venue: confirmed by Omer** — JAIR primary / TMLR fallback is the working target;
  formal advisor ratification (memo §10.1) is the remaining step.
- **AAAI-27: formally dropped** — deadline passed.
- Advisor cost verdict on the cost-of-pass deck content remains open as a paper-content
  question only (the budget gate it rode with is gone). The PlanBench kill criterion
  of 2026-08-15 is moot — the arm delivered before it.

---

## Decisions

**R1 — Order of the two writing jobs.** Recommendation: **PlanBench Act 4 first.**
It is smaller, fully signed, additive to the tex, and does not collide with the
reframe's vocabulary; the reframe then lands on a tex that already has its newest
section in place. The alternative is reframe-first on the argument that it is the
higher-value change.

> ANSWER (PlanBench first / reframe first / both in parallel on separate commits):
> planbench first

**R2 — nt-ster: ratify now, or drop it?** Recommendation: **ratify now** so the
submit is ready at your next VPN window, with the ~186 GPU-h price stated. Dropping
it is defensible if you would rather spend the remaining weeks on writing — the cost
is that the H2 steering attribution keeps its "diagnostic-only, family confound
owned" worst-case scoping in the manuscript permanently.

> ANSWER (ratify now / defer until after the two writing jobs / drop and keep the
> worst-case scoping):
> ratify
>
> **RESOLVED 2026-08-29 — ratified, run, and closed.** All six units PASS. The
> worst-case "diagnostic-only" scoping this decision was hedging against is not
> needed: the attribution holds in the matched cell. See Job 3.

**R3 — Llama-3.1-8B second-family probe.** It is the piece that drags in harness
changes (branch + PR for `vllm_lookup`) and its own kill-gate. Recommendation: keep
it, but sequenced strictly after nt-ster lands, as the memo already has it.

> ANSWER (keep as sequenced / drop / decide after nt-ster):
> keep as sequenced
>
> **UNBLOCKED 2026-08-29.** nt-ster has landed, so the sequencing constraint has
> lapsed and the Llama probe can start whenever it is wanted. It still needs its own
> branch + PR for the `vllm_lookup` case.

**R4 — Job 4 small items: run them now in the background?** They are $0, local, and
independent of everything above. Recommendation: yes, run them alongside Job 1.

> ANSWER:
> yes
