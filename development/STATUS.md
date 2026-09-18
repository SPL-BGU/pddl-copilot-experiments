# STATUS — what is actually left

*Content last refreshed: 2026-09-18 (N1 DONE: `paper/aaai27` `b27ef23` + `b045f07` — title D, the brainstormed two-gate abstract with the scale clause, 14 term edits — PUSHED, Action 35332662004 green, Overleaf `a0b8c84`. Next = N2, the coauthor/advisor round. 2026-09-15: PR #100 merged to main; "Next steps" section
added at the bottom with decision slots R5–R8, incl. one decided-but-unapplied tex
item found on the scan: the 2026-08-20 D-J6 title / abstract / "invocation rate"
decision never reached `paper/main.tex`. Previously: 2026-09-14, paper housekeeping CLOSED: the serving-environment
sentence + vLLM 0.22.0 disclosure footnote pushed as `paper/aaai27` `4eb4751`,
Overleaf `d884bd3`, Omer chose "keep the disclosure"; 09-13: main merged into
`paper/aaai27` as `45de99c`; NUMBERS placeholder filled — see "Paper housekeeping".
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
2026-09-07. Last paper commit is `b045f07` (2026-09-18: title D + the two-gate abstract + "invocation
rate", on `b27ef23`), pushed and Overleaf-synced (`a0b8c84`); see "Next steps" N1. Nothing on the paper is owed beyond coauthor
review. The last `\todo` (serving environment) closed 2026-09-14: `4eb4751` pushed and
Overleaf-synced (`d884bd3`) with the vLLM 0.22.0 disclosure footnote Omer approved —
see "Paper housekeeping" below.

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

## Paper housekeeping — 2026-09-13/14 (all four done)

| item | state | record |
|---|---|---|
| Methodology `\todo` — pin exact vLLM / CUDA / NVIDIA-driver / OS versions, then flip the "computing infrastructure" checklist item from *partial* to *yes* | **DONE 2026-09-14 — `paper/aaai27` `4eb4751` pushed, Overleaf-sync Action 34814416712 green, Overleaf `d884bd3`. Omer's decision (2026-09-14): keep the disclosure footnote, no rerun.** *(History:)* landed locally 2026-09-13 (review gate). The probe ran (Omer's SSH). Versions: vLLM 0.20.2 / PyTorch 2.11.0 / CUDA 13.0 / Apptainer 1.4.5 / Rocky 9.7 / driver 595.58.03 / RTX 6000 Ada 48 GB (the "96 GB" claim removed: no paper corpus used that card). **Finding that needs Omer's decision:** the serve-log banners show the Qwen3.5-4B/9B with-tools canonical cells (both modes) and most anon Qwen3.5 with-tools cells were served by **vLLM 0.22.0** after the 2026-05-29 cache drift (larger than the five-cell list memory carried). Qwen3 parsers are byte-identical across the releases and the 0.8B rerun matches within noise (+0.43 pp [−0.86, +1.71]); the tex discloses this in a footnote. Decision taken: (a) keep the disclosure; (b) the rerun is not planned. Audit: `reference/serving_env_20260913.md`. *(Earlier text of this row:)* OPEN — needs one cluster action. vLLM is fixed by the sbatch pin (`docker://vllm/vllm-openai:v0.20.2` in `run_condition_vllm_rtx.sbatch`); the CUDA runtime lives inside that image, the driver and OS on the compute nodes. Nothing on the laptop records them: the synced results carry no environment metadata and the job stdout prints only GPU name + memory. Probe written: `cluster-experimenting/probe_serving_env.sh` (read-only; run on the login node — greps the preserved serve logs for the served vLLM version, reads `~/vllm.sif` for torch/CUDA, one short `srun` per GPU class for driver + `/etc/os-release`). **Waiting on Omer's go-ahead for the SSH** (his connection must be up). Then: edit the sentence in `paper/main.tex` "Models and Serving" (in the paper worktree, see note below), change the `partial` line under the checklist question to `yes`, Overleaf cycle (pull → commit → push; the Action syncs), save the probe output under `development/reference/`. | this section |
| "227k trials" must not enter the tex | **VERIFIED 2026-09-13** — the `paper/aaai27` tex has no corpus total (no 227k, no 273,600). Reproducible value if one is wanted: **273,600** (NUMBERS.md "Corpus scale"). | NUMBERS.md; Job 4 above |
| NUMBERS.md "to be pinned as Job 2 writes" placeholder | **DONE** — replaced by the "Single-tool suite — per-cell figures" block: one source (`results/derived/e2e_overlay/pooled_e2e_table.csv`), generator and verdict script named, do-not-quote list. The Job 2 tex note corrected from "UNPUSHED" to pushed 09-08. | NUMBERS.md |
| merge main into `paper/aaai27` so the paper branch carries the Job 3 records | **DONE** — `45de99c` (no-ff merge of `1943222`; doc-only, 6 files, no `paper/` change), pushed; the Overleaf pull beforehand returned "Already up to date" (bridge head `2ab9bb5`). | `git log paper/aaai27` |

Operational note (updated 2026-09-18): **`main` is the single line of work.**
`paper/aaai27` was merged into `main` by PR #101 (merge commit `75e070f`, not squashed,
so every `paper/aaai27` hash cited in this file stays reachable on `main`), and the
branch plus its worktree at `../pddl-copilot-worktrees/paper-aaai27` were removed.
`paper/main.tex` on `main` is the current paper. Paper edits go on a short branch off
`main` and merge by PR; the Overleaf auto-sync Action now triggers on `main`. Run
`development/sync_overleaf.sh` from the main checkout — its default clone path
(`../pddl-copilot-paper-overleaf`) resolves correctly there, no `OVERLEAF_CLONE` needed.
Where the text above says "on `paper/aaai27`", read "on `main`" for any new work.

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

---

## Next steps — proposed 2026-09-15 (after PR #100 merged)

Everything above is closed: no experiment is owed, all three writing jobs are in
Overleaf, no `\todo` is left, the tex compiles (25 pages, 0 undefined refs, one
overfull box). What is left is getting the manuscript in front of the coauthors and
advisors and then to JAIR. Scanning for that turned up one decision that was taken
but never applied to the tex (N1). Order: N1 → N2 → N3; N4 is optional; N5 is
minutes.

### N1 — Apply the D-J6 decision to the tex: DONE 2026-09-18 (pushed + Overleaf-synced)

**`paper/aaai27` `b27ef23` + `b045f07` (`b045f07` = the scale clause the advisor agent recommended, accepted by Omer 09-18). PUSHED 2026-09-18 on Omer's go, Overleaf-sync Action 35332662004 green, Overleaf head `a0b8c84`, `main.tex` byte-identical.** Title D; a new 191-word
abstract brainstormed 09-15/18 (`title_abstract_candidates.md` §5: two-gate abstraction,
findings first, four verified numbers, PlanBench in, scale clause after PlanBench, 200 words); "propensity"
→ "invocation rate" at all 14 sites. Compile clean. Overleaf pull before editing: already
up to date. Nothing left on N1. Next: N2. Record: `paper_notes_discussions.md` 2026-09-15/18.

*(Original text of this item:)*

Decided 2026-08-20 (`paper_notes_discussions.md` "D-J6 CLOSED"; slots in
`title_abstract_candidates.md` §2–3), never applied to `paper/main.tex` on `paper/aaai27`:

| decided 08-20 | tex today (`4eb4751`) |
|---|---|
| title D: *Invocation Is the Bottleneck: When Sound Planning Tools Help an LLM, and When They Do Not* | still the retired *Availability Is Not Enough: …* (title line last touched 06-18) |
| term = "invocation rate", "propensity" retired paper-wide | "propensity" appears 14 times (abstract-adjacent intro L182, results, limitations, future work, conclusion) |
| abstract redrafted on the N1 spine: invocation is the headline, delivery demoted to one clause, delivery itself lives in Limitations | Job 2 batch 1 (`125cc7a`, 09-07) rewrote the abstract on the delivered surface: 297 words, delivery is a second headline ("The second is delivery: …") |

The 08-20 N1 abstract draft (`title_abstract_candidates.md` §3) has an empty
approve/revise slot and predates Job 2, Job 3 and the budget probe, so its six numbers
(8–11 floor, 66–73 lift, −67 availability harm, 21→94 steering, >99% correct when
called, "one of three models at 9B or larger") need a `/verify-claims` pass against
the current tex and `NUMBERS.md` before any of it enters the tex. D-J1 (first number
one-sided by construction) was flagged 08-20 as no longer binding under N1; confirm
when ruling R5.

Sequence once R5/R6 are answered: `/verify-claims` on the abstract numbers →
Overleaf pull → edit on `paper/aaai27` in the worktree (title, abstract, the 14 term
edits, the Intro's "invocation propensity" definition sentence) → compile → push
(Action syncs) → paper_notes entry.

### N2 — Coauthor + advisor review round (Omer; agent prepares the brief)

No coauthor has edited Overleaf since the 08-11 sync (every pull since returned
clean). The journal memo's timeline had "manuscript draft to advisors ~early
September". The manuscript is ready to send once N1 is in, because title and abstract
are what the advisors read first. Agent-executable prep: a one-page advisor brief
that bundles the memo §10 questions, so one conversation closes them all:

1. venue ratification — JAIR primary, TMLR fallback with the three pre-committed
   rejection branches, AIJ only on override (memo §5);
2. confirm the Sept-2026 thesis needs a *submitted* manuscript, not an acceptance;
3. record the journal pivot formally (AAAI-27 dropped 08-30);
4. verdict on the cost-of-pass deck content (`archive/cost-breakdowns/`);
5. storage-fixed rerun of ~5 headline cells: contingency only (default) or run before
   submission;
6. (grant-reopened 08-30) Sonnet-tier PlanBench extension: run or leave excluded.

### N3 — Pre-submission mechanics (agent; prose items after N2 feedback, reformat after venue is ratified)

- Fix the one overfull box: the batch-1 scorecard `table*` (tex ~L766–807, 130 pt too
  wide).
- One whole-paper consistency read after N1: terminology (invocation rate everywhere),
  AI-tells over the Job 2 / Job 3 additions (em-dash count is already 0), notation
  gate (CI vs censor-bound typography) in the newest tables.
- JAIR reformat: the tex is `article` + `aaai2027.sty`; JAIR uses its own style file.
  Mechanical but it touches every float, so do it once, after the venue is ratified.
- Cover letter with the arXiv:2509.12987 delta statement (memo §5: each control flipped
  a headline; extensive-revision defence). Writing it also closes ISS-013 (the
  paper-diff audit vs the arXiv version), which has been open since April.

### N4 — Optional experiments (none owed; all unblocked)

- **Llama-3.1-8B second-family probe** (R3 = "keep as sequenced"; unblocked since
  08-29). $0, cluster GPU-h only; needs a harness branch + PR for the `vllm_lookup`
  case, a kill-gate, ping + VPN. Recommendation: hold until the advisor round; it is
  the ready answer if they ask whether the invocation finding is Qwen/Gemma-specific.
- Sonnet-tier PlanBench extension and the storage-fixed rerun: advisor calls, N2.

### N5 — Hygiene (agent, minutes)

- Cluster checkout sits on `paper/iter2-decoupled-run`, whose remote is gone; switch
  to `main` + pull so the probe script is there (SSH → needs Omer's go).
- `OPEN_ISSUES.md`: strike ISS-022 (WT arm closed 08-06; index already says so).
- Memory note for the 09-13/14 housekeeping updated to "PR #100 merged".

### Decisions

**R5 — Which abstract under N1?** (a) apply D-J6 in full: title D + the N1 abstract
(re-verified, delivery demoted to one clause) + the 14 term edits; (b) title D + term
edits only, keep the 09-07 delivered-reframe abstract with delivery as a second
headline — this supersedes the 08-20 abstract decision and gets its own paper_notes
entry; (c) other. Recommendation: **(a)** — it is the recorded decision, the N1
spine is what title D promises, and 297 words is long for a JAIR abstract.

> ANSWER (a / b / c):
> **ANSWERED 2026-09-18 (Omer): apply D-J6 with a NEW abstract** — brainstormed 09-15/18
> (`title_abstract_candidates.md` §5): abstraction (ii) two gates, findings first with one
> protocol clause, four numbers (95 vs 22–29 · 21→94 + 99% · 0/5/>33 · 72 vs 0), PlanBench
> in, ≤200 words, **Shape A** chosen. Scale clause pending a separate advisor agent. Title D
> kept for now, re-read against the final abstract before the tex pass.

**R6 — Go-ahead for the tex edits on `paper/aaai27`** (the half of the 08-20 slot
that was never answered). Pull-then-push protocol as always.

> ANSWER (go / hold):
> **ANSWERED 2026-09-15 (Omer): go, once R5 is answered.**

**R7 — Send to the coauthors and advisors after N1, with the six-question brief?**
Alternative: send now, before N1, if you want their view on the title first.

> ANSWER (after N1 / now / hold):
>

**R8 — Llama-3.1-8B probe.** Recommendation: hold until the advisor round.

> ANSWER (hold / start now):
>
