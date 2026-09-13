# STATUS — what is actually left

*Content last refreshed: 2026-09-13 (paper housekeeping pass: main merged into
`paper/aaai27` as `45de99c`; NUMBERS placeholder filled; the serving-environment
`\todo` is the one open tex item, gated on a cluster probe — see "Paper housekeeping".
Earlier the same day: Job 3 nt-ster integration PUSHED + Overleaf-synced
as `6027d68` + `7c0502a` on `paper/aaai27`, Overleaf `2ab9bb5`; frontier budget probe
DONE 09-12; Job 2 closed). Renamed from `remaining_work_20260811.md` on 2026-08-29.*

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
— all six units PASS — so there is now no unrun experiment on either line.** **All
three writing jobs are landed and synced.** Job 3's tex landed 2026-09-12 (`6027d68`),
was revised on Omer's four review points 2026-09-13 (`7c0502a`), pushed, and
Overleaf-synced (Action run 34743222922 green, Overleaf `2ab9bb5`). Job 2 is closed
(batches 1+2 + the budget-probe sentence pushed and synced). Job 1
(PlanBench Act 4) is DONE — it landed 2026-08-11 (`67ea69c` + `644f8bd`) and synced
to Overleaf the same day; this file wrongly carried it as NOT STARTED until
2026-09-07. Last paper commit is `7c0502a` (2026-09-13), pushed and Overleaf-synced (`2ab9bb5`);
the branch head is the doc-only merge `45de99c` (main → `paper/aaai27`, 2026-09-13, no
paper files changed, Overleaf untouched). Nothing on the paper is owed beyond coauthor
review, except the serving-environment sentence: landed locally as `4eb4751` with a
vLLM-version disclosure footnote that needs Omer's sign-off before push — see "Paper
housekeeping" below.

## State by line

| line | data | analysis | paper |
|---|---|---|---|
| PlanBench (NT + WT) | DONE, archived + MANIFEST-verified | DONE, `verify_promotion.py` re-derives every number | **DONE 2026-08-11** — section in tex + Overleaf, re-verified 09-07 |
| Single-tool suite | DONE (07-17) | DONE (e2e overlay D1–D9 + Phase 5, pooled table regenerated) | **DONE 09-08 / 09-12** — the full e2e reframe (D2/D-J2 = option a), batches 1+2 on `paper/aaai27`, in Overleaf; budget-probe sentence LANDED 09-12 (tex `5466cb6`, Overleaf `d922237`) |
| nt-ster H4 control | **DONE 2026-08-29** (6 cells, 9,120 rows each) | **DONE** — all six units PASS, branch PASS | **DONE 2026-09-13** — caveat-only integration `6027d68` + review revisions `7c0502a` on `paper/aaai27`, pushed + Overleaf-synced (`2ab9bb5`), see Job 3 |

Evidence on the paper side (2026-09-13): the Results sections carry the delivered
reframe and the budget-probe paragraph; the PlanBench section exists (`\section{External
Validity on PlanBench}`); the steering control's PASS paragraph, Limitations note and
appendix block (`tab:ster-units` / `tab:ster-tasks` / `tab:ster-drift` + the factorial
diagnostic) are in Overleaf (`2ab9bb5`).

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

**Frontier budget probe: DONE 2026-09-12 (run, readout RATIFIED, paper edit
landed on `paper/aaai27` `5466cb6`, Overleaf `d922237`).** Sonnet PARTIAL (16/25 vs
7/19, p = 0.069), Haiku H1 (12/17 vs 1/12, p = 0.001), 0/14 DECLINE; delivered at 64K
70 / 44 (Sonnet WT / NT) and 65 / 58 (Haiku). Frozen values: NUMBERS.md "frontier
budget probe" row. Readout + Omer's answers: `frontier_budget_probe_readout.md`.
Reference cells unchanged. Cost $40.68.

**Job 2 is closed.** Nothing left on it.

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

## Job 3 — nt-ster H4 control: DONE (tex landed 2026-09-12, revised + pushed + synced 2026-09-13)

**Integration landed on `paper/aaai27` as `6027d68` (2026-09-12) and, after Omer's
four review points, `7c0502a` (2026-09-13); pushed 2026-09-13, auto-sync Action run
34743222922 green, Overleaf bridge head `2ab9bb5` verified byte-identical to HEAD.**
What is in it: the CALL-beat paragraph (Results, after the 21→94% invocation sentence;
"All six pooled units and all eight eligible task cells met the ±5pp equivalence
criterion; excluded task cells remain unresolved" / "This supports the interpretation
that steering acts through tool use in the matched Gemma cell"), the Limitations note
(not causal: different layers, later apparatus, conflicting no-tools instruction), a
converted Methodology control-arm sentence, and the appendix block "The steering
control" with `tab:ster-units`, `tab:ster-tasks`, `tab:ster-drift`, the within-corpus
factorial diagnostic (per-model replication criterion not met; clause not in the main
claim) and the declared deviations. Compile: 0 errors, 0 undefined refs. Records:
`paper_notes_discussions.md` 2026-09-12 (night) + 2026-09-13; tex cross-check rows in
`NUMBERS.md`. **Nothing left on Job 3.**

**The experiment is done.** Closed 2026-08-29 on branch `run/ntster-h4`: six cells,
9,120 rows each, **all six units PASS**, paper-level branch **PASS**. Every one of the
8 ELIGIBLE task cells is EQUIVALENT. Figures: `NUMBERS.md`. Full readout:
`ntster_h4_final_readout_20260829.md`. Design of record: `reference/ntster_h4_prereg.md`.

The result it was commissioned for, in the matched cell: gemma `validate_plan`
`think=off` is **+72.0pp with tools and +0.63pp [−0.46, +1.73] without**. The steering
effect is attributed to the directive's interaction with tool access.

**The writing was done under the pre-committed caveat-only cap** — CALL beat +
Limitations in the body; per-task table, F gate, MDE table, drift check, the on-mode
apparatus failure and the two §9.1 deviations (plus §9.2) in an appendix. Scope as
approved (final readout O4), not expanded.

**2026-08-30: post-review corrective re-run.** The PR #96 correctness review found
defects in the frozen analysis code (censored rows scored as successes, a mis-specified
governing estimator, a degenerate mechanism section — prereg §9.2). Code fixed,
re-frozen, everything regenerated: **verdicts unchanged, secondary numbers revised** —
quote only NUMBERS.md / the revised readout.

Things the integration had to carry, pre-registered and none optional — all present
in `6027d68`:

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
273,600) — resolved 2026-09-13: the paper-branch tex states no corpus total at all
(grep for 227/273 is empty on `paper/aaai27`); if a total is ever wanted, the
reproducible value is 273,600 (NUMBERS.md "Corpus scale"). The memo keeps its
correction banner.

## Paper housekeeping — 2026-09-13 (three of four done; one gated on a cluster probe)

| item | state | record |
|---|---|---|
| Methodology `\todo` — pin exact vLLM / CUDA / NVIDIA-driver / OS versions, then flip the "computing infrastructure" checklist item from *partial* to *yes* | **TEX LANDED LOCALLY 2026-09-13 as `paper/aaai27` `4eb4751` (worktree; NOT pushed, NOT Overleaf-synced — review gate).** The probe ran (Omer's SSH). Versions: vLLM 0.20.2 / PyTorch 2.11.0 / CUDA 13.0 / Apptainer 1.4.5 / Rocky 9.7 / driver 595.58.03 / RTX 6000 Ada 48 GB (the "96 GB" claim removed: no paper corpus used that card). **Finding that needs Omer's decision:** the serve-log banners show the Qwen3.5-4B/9B with-tools canonical cells (both modes) and most anon Qwen3.5 with-tools cells were served by **vLLM 0.22.0** after the 2026-05-29 cache drift (larger than the five-cell list memory carried). Qwen3 parsers are byte-identical across the releases and the 0.8B rerun matches within noise (+0.43 pp [−0.86, +1.71]); the tex discloses this in a footnote. **Decide: (a) keep the disclosure (recommended) or (b) rerun 4 canonical + 7 anon cells on 0.20.2 and regenerate everything downstream.** Then push + Overleaf cycle. Audit: `reference/serving_env_20260913.md`. *(Earlier text of this row:)* OPEN — needs one cluster action. vLLM is fixed by the sbatch pin (`docker://vllm/vllm-openai:v0.20.2` in `run_condition_vllm_rtx.sbatch`); the CUDA runtime lives inside that image, the driver and OS on the compute nodes. Nothing on the laptop records them: the synced results carry no environment metadata and the job stdout prints only GPU name + memory. Probe written: `cluster-experimenting/probe_serving_env.sh` (read-only; run on the login node — greps the preserved serve logs for the served vLLM version, reads `~/vllm.sif` for torch/CUDA, one short `srun` per GPU class for driver + `/etc/os-release`). **Waiting on Omer's go-ahead for the SSH** (his connection must be up). Then: edit the sentence in `paper/main.tex` "Models and Serving" (in the paper worktree, see note below), change the `partial` line under the checklist question to `yes`, Overleaf cycle (pull → commit → push; the Action syncs), save the probe output under `development/reference/`. | this section |
| "227k trials" must not enter the tex | **VERIFIED 2026-09-13** — the `paper/aaai27` tex has no corpus total (no 227k, no 273,600). Reproducible value if one is wanted: **273,600** (NUMBERS.md "Corpus scale"). | NUMBERS.md; Job 4 above |
| NUMBERS.md "to be pinned as Job 2 writes" placeholder | **DONE** — replaced by the "Single-tool suite — per-cell figures" block: one source (`results/derived/e2e_overlay/pooled_e2e_table.csv`), generator and verdict script named, do-not-quote list. The Job 2 tex note corrected from "UNPUSHED" to pushed 09-08. | NUMBERS.md |
| merge main into `paper/aaai27` so the paper branch carries the Job 3 records | **DONE** — `45de99c` (no-ff merge of `1943222`; doc-only, 6 files, no `paper/` change), pushed; the Overleaf pull beforehand returned "Already up to date" (bridge head `2ab9bb5`). | `git log paper/aaai27` |

Operational note found on the way: `paper/aaai27` is checked out as a **git worktree**
at `../pddl-copilot-worktrees/paper-aaai27` (a plain `git checkout paper/aaai27` in the
main tree fails with "already used by worktree"). Run `development/sync_overleaf.sh`
from inside that worktree with
`OVERLEAF_CLONE=/Users/omereliyahu/personal/pddl-copilot-paper-overleaf` — the
script's default clone path resolves relative to the worktree, not the main tree.

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
