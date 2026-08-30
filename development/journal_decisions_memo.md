# Journal decisions memo — recommendations for the 8 open slots (2026-07-23)

> **SCALE-FIGURE CORRECTION (2026-08-16).** The "227k trials" headline used in this
> doc does not reproduce from disk and has no recorded derivation. The counted
> two-corpus total is **273,600** (5 models x 2 reasoning modes x 3 arms x 4,560 x 2
> corpora; sweep5v2-live and sweep6-live are 136,800 rows each, all keys unique, zero
> infra failures). That figure covers the **five open-weight models only** — the
> frontier arm (6,080 Haiku + 10,640 Sonnet) is separate, so it must NOT be paired
> with a "seven models" phrase. See `title_abstract_candidates.md` section 4.


**Status:** RECOMMENDATIONS for Omer's sign-off. Covers D-J1..D-J6
(`development/archive/status-snapshots/journal_narrative_proposal.md` §8) and D2 + D4
(`development/archive/status-snapshots/roadmap_eval_and_paper_completion.md`). Each Recommendation block is
paste-ready for its ANSWER slot; the original docs' slots are untouched. Rulings go
to `paper_notes_discussions.md` once decided.
**Method:** 23-agent investigation workflow — 4 repo evidence readers (paper audit,
locked verdicts, PlanBench state, complement costs), 3 web researchers (2026 venue
state; narrative exemplars from non-planning fields; primary-vs-diagnostic metric
precedents), 5 decision analysts, and 12 adversarial red-team passes (hostile-reviewer
+ reader-experience lenses; two cells got two independent passes each). All 12
verdicts were AMEND, zero refutes: every core recommendation stood, and every
amendment is applied below. Load-bearing repo claims were then spot-checked against
sources by the coordinating session: simulate delivered bounds
(`sonnet_wt_vs_haiku_e2e_memo.md` L34: Sonnet [49.0,62.0] 13/100 censored, Haiku
[52.0,64.0] 12/100), the 07-11 later-3 "strict end-to-end is the paper's headline —
DECIDED (Omer)" ruling (paper_notes L644-646), the May H4 prereg
(`sweep_prompt_bank_design.md:46`), the iss024d prereg think=on scoping
(`iss024d_parity_prereg.md:69`), commit `2a1298c` (PlanBench #65 grading fixes), and
the v14-16 steered-arm mapping (`pddl_eval/summary.py arm_for`).
**Governing goal:** simplify the narrative and make the evaluation approachable
without compromising rigor. Nothing below is justified by page-limit savings.
Cluster items are flagged; each needs Omer's explicit go-ahead + VPN.

---

## 1. How the paper gets simpler

Eight principles, each traced to a precedent outside planning (per the "don't learn
from small-scale PDDL papers" constraint). These are the operating rules for every
rewrite batch; the per-decision sections apply them.

1. **Open on a number that is simultaneously a finding and a measurement claim.**
   The reader should not have to choose between "interesting result" and "methods
   paper" on page one. Precedent: Schaeffer et al., "Are Emergent Abilities a
   Mirage?" (arXiv:2304.15004, NeurIPS 2023) — the field-moving claim IS the
   metric-choice claim. Ours is the length-shaped delivery gradient (0pp verdicts /
   +5pp plans / >=33pp trajectories), not any single cell (see §2).
2. **One primary surface per claim; everything else is labeled mechanism or
   sensitivity.** Clinical trials solved this decades ago: ICH E9/E9(R1) makes the
   intention-to-treat set primary for superiority claims and demotes per-protocol to
   supportive; mature ML benchmarks converged on the same shape (SWE-bench
   "% Resolved" primary / "% Applied" diagnostic; tau-bench pass^1 primary).
   Delivered = ITT; tool-verified = per-protocol (see §3).
3. **One summary figure with named ordered stages over one honest denominator.**
   Gardner et al. 2011 (Clin Infect Dis 52(6):793) — the HIV care cascade: memorable
   because each bar answers one question and the floor is unforgettable. Our Figure 1
   is a within-arm cascade (§2; the naive cross-arm version is unbuildable without
   pooling arms, which the paper's own rules forbid).
4. **Retractions are narrated once, as controls, quantified in delta-pp — never
   scattered as revision layers.** ABC (arXiv:2507.02825) quantifies its corrections
   (33% overestimation cut) and reads as constructive; Registered Reports practice
   (Chambers & Tzavella, Nat Hum Behav 2022) legitimates reporting a failed
   pre-registered test (our iss024d parity FAIL) as the protocol doing its job. One
   subsection: "Controls that moved headlines."
5. **The reader learns the corpus rules once, from one table, instead of meeting
   caveats per paragraph.** CONSORT 2010 / STARD 2015 turned denominator discipline
   into a single standard device (the flow diagram) rather than distributed
   apologies. Ours: a "how to read our numbers" table (corpus x storage regime x
   value shape x one-line reason) at the head of Results, with the prohibited-claim
   list as its footnotes (see §3).
6. **Coin one metric name and two vignette names, then reuse them.** tau-bench's
   pass^k and HAL's (arXiv:2510.11977) log-mined failure vignettes show named handles
   are what readers retain. Ours: "the delivery gap" (collision-check pending, §9),
   "the 9B paradox," "Gemma silence."
7. **The body carries decision rules; machinery goes to appendices.** HELM
   (arXiv:2211.09110, TMLR 2023) keeps protocol claims in the body and per-scenario
   machinery in appendices; MLPerf (arXiv:1910.01500) likewise. Our stats wall
   (ICC/GLMM/GEE/Bonferroni, main.tex L461-516) moves to a stats appendix; only the
   signed-significance rule and the corpus table stay inline.
8. **The manuscript is audience-self-contained and venue-orthogonal.** A short
   primer covers PDDL tasks, PlanBench, and LLM-Modulo for a non-planning ML reader;
   no body section assumes planning-venue background. The validity/protocol THREAD
   (what each control is, which headline it flipped) is body content at any
   rigor-weighted journal; the operational MECHANICS (D1-D9 decision log,
   parity-prereg text, reproducibility checklist) are a structured appendix
   summarized by one body-level table. This keeps the TMLR fallback a mechanical
   reformat, caps first-read cognitive load, and benefits every first-time reader —
   planning insiders skim familiar primer material at no cost.

---

## 2. D-J1 — Thesis shape

**Recommendation (paste into `journal_narrative_proposal.md` D-J1 slot):**

> ANSWER (2026-07-23, decisions memo §2): RATIFIED — protocol-first hybrid (C1
> protocol + C2 case study) in the findings-hook/protocol-spine variant. The hook is
> the length-shaped delivery GRADIENT, not a single cell: "same model, same verified
> tool: 0pp gap on verdicts, +5pp on plans (exact, identical on both frontier
> tiers), >=33pp on trajectories (bounds)" — replicated, never-retracted (memo 07-13
> Verdict 1: task-shaped, not model-shaped). The 99.0-vs-[49,62] simulate pairing
> moves to the DELIVER stage with the D7->D9 grading history and the 29/12/10
> failure split disclosed adjacent, inside "Controls that moved headlines." Never
> print a two-sided interval as the abstract's first number; the one-sided form
> ("the tool verified 99% of trajectories; the user received at most 62%") is the
> permitted variant. CORRECTION that binds everywhere: frontier simulate delivered
> is NOT exact — bounds [49.0,62.0] Sonnet (13/100 censored) / [52.0,64.0] Haiku
> (12/100); fix §2 item 3 of the proposal ("Exact e2e" -> "exact except simulate
> delivered: bounds"). Figure 1 = within-arm cascade per tier: denominator =
> with-tools trials; bars trials -> tool called (CALL) -> tool result correct
> (mechanism) -> delivered correct (DELIVER); NEED rendered as the no-tools-success
> reference line the cascade towers over, never as a bar (arms are never pooled,
> main.tex L471-472). Frontier simulate DELIVER bar gets the same hatched-bounds
> rendering as open roster. Open-roster panel gated on bounds informativeness: plot
> validate_* cells; route open-roster solve/simulate DELIVER through the frontier
> panel or an explicitly-labeled iss024d inset — no vacuous 0-100 hatched bars
> (no-tools simulate is 100% censored in `results/derived/e2e_overlay/
> pooled_e2e_table.md`). Ratification is CONDITIONAL on three checkable retirements
> (if any is refused, re-open D-J1 because the funnel then adds mass instead of
> removing it): (1) D-J2=(a) single quoted surface; (2) both regime-taxonomy
> vocabularies deleted from the body (grep 'sole-source|headroom|budget-dependent|
> robust floor' hits only an appendix RQ-mapping table); (3) one upfront corpus
> table in Methods replacing per-paragraph caveats. Devices: validity thread as one
> subsection closing the protocol section, each retraction attributed to a named
> control and quantified in delta-pp (simulate 0->22-40 budget decoupling; WT
> 13.5/0 -> 95/[52,64] format-tolerant regrade; NT bounds -> determinate
> de-censoring); the L827-830 robust-floor inconsistency retired; funnel = three
> one-line questions in the intro, then one stage = one question + one headline
> number + one figure in Results; coin "the delivery gap" (collision-check first)
> and the named vignettes; stats wall to appendix; audience-self-contained primer
> per §1 principle 8. §6's "full overlay methods inline" softens to body-summary +
> appendix-detail (see §5).

**Why (simple-first).** Every headline that changed, changed because a control was
added; every claim that survived, survived adversarial regrading. Leading with
findings makes that history a liability ("what else is latent?"); leading with the
protocol makes it the evidence. The methods-dump worry is answered by the fused
opener, not by demoting the protocol. All five dual-contribution exemplars found
(HELM, HAL, MLPerf, Jacobs & Wallach FAccT 2021, Registered Reports) lead
protocol-first; the research found zero findings-first exemplars in the cohort. The
draft audit shows protocol-first is a promotion job, not new prose: the protocol
skeleton already exists scattered as defenses in main.tex.

**What the red team said and how it changed the answer.** Both lenses AMEND,
converging on the same defect: the analysts' original hook staked page one on the
single cell with the worst measurement pedigree, and its "frontier delivered is
exact" justification is factually false (verified: simulate delivered is a
censor-bounds interval that flipped across three grading passes, with ~80% of its
gap mass budget+format). A protocol paper breaking its own labeling discipline in
its flagship figure is a rejection-grade opening. Fixes applied: hook recast to the
gradient (exact 0pp/+5pp anchors, uncensored); exactness claim struck everywhere;
Figure 1 respecced as within-arm cascade (the cross-arm spec was unbuildable
without pooling arms or plotting vacuous bars); simulate bar hatched on both tiers,
which displays the protocol better anyway.

**Cost to Omer.** Annotate the slot (minutes). All devices are agent-executable
from on-disk memos.

> DECISION:

---

## 3. D-J2 = D2 — Quoted with-tools surface

**Recommendation (paste into BOTH slots — proposal D-J2 and roadmap D2):**

> ANSWER (2026-07-23, decisions memo §3): (a) FULL REFRAME. e2e_strict (delivered)
> is the single primary SURFACE everywhere — scorecard, tables, abstract,
> discussion; tool-verified renamed into the mechanism/diagnostic layer, never a
> headline. Declared ICH-estimands style in Methods: one primary surface; the
> primary takes three value shapes tied to storage regime — exact point + Wilson CI
> (frontier solve/validate_*, de-censored NT), censor-bounds interval (frontier
> simulate; marked distinctly), lower bound "success >= X%" (sweep5v2 WT) — and
> this heterogeneity is itself protocol evidence (full-response storage buys
> exactness). HARD GATE on all tables: typographically distinct notation for Wilson
> CIs vs censoring bounds (the 07-13 memo's same-row bracket collision must not
> reach the manuscript; /verify-claims checks notation alongside values).
> Per-corpus quoting rules, zero new runs: frontier WT exact (memo 07-13); frontier
> NT exact de-censored (07-15); sweep5v2 WT think=off = strict bounds per D6=A,
> with exactly 2/25 cells UNDECIDED (35b validate_problem; 9B solve) stated as
> undecided, never resolved via iss024d; sweep5v2 NT exact; iss024d = "independent
> rerun estimates under full-response storage," separate-apparatus label,
> within-corpus paired gaps only, solve cells barred from headline use; decoupled
> line = NEED-stage control only. The delegation_terminal outcome category (07-11
> later-3 ruling) carries explicitly into the table spec. Reader-facing device: ONE
> "how to read our numbers" table (corpus x storage regime x value shape x reason)
> at the head of Results; the prohibited claims are its footnotes: no cross-corpus
> delivered-vs-tool-verified gap; no steered with-tools e2e claim (no nt-ster
> control yet — see §6); no frontier "tools are sole source of simulate success" at
> the delivered level (NT-vs-WT simulate not CI-separated, 07-15); 9B solve lift
> not claimable significant on delivered for the canonical corpus. The open-roster
> e2e entry reads: "bounds-only on the existing corpus; point-identification is
> feasible via a storage-fixed rerun on the canonical generation apparatus
> (parser-on, think=off, post-2026-06-25 snapshot cap), pre-registered here as the
> declared answer to a reviewer demand, under the iss024d prereg-parity discipline
> (gemma control, TOST +/-5pp)" — NOT "bounds forever." That optional rerun is a
> cluster decision (go-ahead + VPN), default = contingency only (§9). Derived
> obligations: cost-of-pass recomputed on delivered for frontier; open-roster
> cost-of-pass as bounds or labeled mechanism-layer economics; the "no-tools
> simulate cost-of-pass is infinite" sentence dies. CALL-stage carry-over is GATED
> like DELIVER: the gemma -67pp harm claim and P(call)-bottleneck numbers must be
> re-derived and /verify-claims-checked on the delivered surface (sweep5v2 bounds +
> iss024d within-corpus inversion: delivered 30.0-63.1 vs tool-verified 0.9) before
> Act-3 CALL prose lands — "the prose survives" is not a verified fact. Headlines
> stay think=off >=9B quoted as bounds; iss024d is the labeled replication.

**Why (simple-first).** One SURFACE per claim, and it is the surface the user of
the system experiences. This is already the locked ruling (paper_notes 07-11
later-3, verified L644-646: "strict end-to-end is the paper's headline," DECIDED
(Omer); roadmap D1 answer: "P1 defaults to the full reframe"). Option (b) additive
would put every cross-arm gap on asymmetric surfaces — the exact defect genus ABC
quantifies — and has no successful precedent (every mature dual-metric system
designates one primary; ImageNet's dual headline collapsed to top-1).

**What the red team said and how it changed the answer.** Both AMEND, direction
upheld. Hostile: "bounds only, forever" was overclaimed — the 500-char cap is a
storage snapshot cap, not a generation-apparatus property, so a targeted
parser-on/think=off rerun IS the canonical apparatus; a protocol paper declining a
feasible measurement of its own primary estimand hands reviewers a core-credibility
attack. Fixed by the pre-registered contingency wording. Also: CALL carry-over
gated (the -67pp claim is surface-sensitive), delegation_terminal restored.
Reader-experience: "one number per claim" was false as stated (the primary surface
yields multiple value shapes, and the seed memo has a live bracket-notation
collision); fixed by the "one surface, three shapes" reframe, the notation gate,
and the single how-to-read table. The analysts' uncited "~14 metric surfaces" count
is struck from all rationale; the defensible claim is qualitative.

**Cost to Omer.** Paste two ANSWERs (minutes). Execution fully agent-executable,
zero new runs; his time is review of drafted table/prose batches. Every results PR
gates on /verify-claims.

> DECISION:

---

## 4. D-J3 — PlanBench tools arm

**Recommendation (paste into `journal_narrative_proposal.md` D-J3 slot):**

> ANSWER (2026-07-23, decisions memo §4): IN SCOPE as a MINIMAL Act 4 —
> frontier-only (Haiku) with-tools PlanBench via the local path; the open-roster v2
> cluster arm is demoted to pre-registered Future Work. HEADLINE ASSIGNMENT (from
> red-team): Act 4's "honest re-measurement on the field's own instrument" claim is
> carried by the ALREADY-GRADED NT layer — honest-denominator regrade, the t2
> silent-0.0 artifact fix, the t7 chat-format grading critique vs GPT-4's 28.4,
> Haiku t1 41.0 beats GPT-4 31.4 CI-disjoint, Mystery collapse replication
> (`development/archive/planbench/planbench_frontier_haiku_nt.md`, 07-23). The WT arm
> carries the explicitly-labeled SECONDARY claim: "the funnel replicates when the
> model operates the prescribed remedy on the field's instrument" — external
> validity for C2, within-apparatus only. This assignment makes the WT-vs-GPT-4
> misread structurally impossible rather than prose-mitigated. Design: (1) WT
> backend as an adapter over tools/frontier_runner.py (~1 agent day; its docstring
> pre-plans this). (2) PRIMARY CONTRAST = WT vs a NEW matched-scaffold no-tools
> control arm in the same SDK apparatus — identical system scaffold (NL->PDDL
> formalization step + task-format clause), tool availability the ONLY ablation
> (empty tool list), same seed-fixed stratified subsample, same grading; the
> on-disk 06-22 bare-NT rows become a published-apparatus replication layer; GPT-4
> rows context only. (3) Scope priority: blocksworld t1 > MYSTERY t1 > blocksworld
> t3 — mystery t1 (NT 0.8%) is the failure-to-success cell; clean t1 (NT 41.0) is
> the near-ceiling confirmation. Target shape = the {clean, mystery} x
> {matched-NT, WT} 2x2 on t1. Budget valve = prereg-fixed subsampling (n~200-250/
> cell, Wilson CIs), never whole-cell deletion; prediction-cell linkage rule: any
> prediction whose test cell is trimmed is struck from the prereg. t2 excluded
> (optimal_plan tool unbuilt). (4) Prereg BEFORE any spend, scoped to unrun cells
> only: (i) tools convert failure to success on mystery t1; clean t1 confirms near
> ceiling; (ii) TWO-SIDED on the Mystery mechanism — formalization is
> semantics-blind transcription and FD ignores predicate names, so tools may rescue
> Mystery; both directions pre-registered as publishable; (iii) tool-available t3
> closes Haiku's verification gap vs its own matched-NT (struck if t3 is trimmed);
> plus a pre-committed statement of where the NL->PDDL formalization interface sits
> in the funnel taxonomy (input-boundary stage under NL-specified problems, or an
> explicit CALL extension) — named in the organizing device BEFORE data arrives.
> (5) Presentation separation as a PREREG RULE: WT cells never share a table/figure
> with GPT-4 rows — Table A = NT vs committed GPT-4 (existing caveats); Figure B =
> within-Haiku paired matched-NT->WT deltas, no GPT-4 column; t7 appears only in
> Act 5's grading critique. (6) Calibrate on ~20 instances, run within the ~$70.6
> API remainder, grade locally (Rosetta VAL + plugin FD, 07-23 spot-check
> discipline). KILL CRITERION: convert to Future Work if (a) calibration projects
> the t1 2x2 above the remainder even at n=200/cell, or (b) no graded WT table by
> 2026-08-15. FALLBACK SHAPE = SHRINK, NOT SCATTER: on conversion, Act 4 survives
> as the NT-only re-measurement act (self-sufficient under the headline assignment
> above) with the WT design published inside it as pre-registered Future Work — the
> NT beats are NOT dispersed across Acts 3/5 and the contamination section (three
> homes for one dataset is the worse reader experience). Factual correction
> carried: only the two grading blockers are fixed (2a1298c); the truncation-cap
> blocker is mooted by the frontier path, not fixed — relevant if the cluster arm
> is ever promoted.

**Why (simple-first).** The expensive part is done and already changes how the
field's numbers read (Haiku beats GPT-4 on the field's own grader; t7 quantifies
the chat-format grading disease). The missing WT piece is cheap (~1 agent day +
$40-70 from the remainder, all local, no cluster), and it is the one demonstration
Act 4's secondary claim needs: the prescribed remedy, operated by the model, graded
on the delivered answer. Dropping it would also silently reverse the D3 = RUN NOW
ruling (roadmap ANSWER, 2026-07-23) whose named next steps are exactly this
backend + prereg.

**What the red team said and how it changed the answer.** Three independent AMEND
passes, scoping upheld. Hostile: the original "WT vs own NT" primary contrast was
NOT within-apparatus (bare NT rows have no system prompt; WT adds the forcing
directive + formalization step + multi-turn loop — a larger apparatus delta than
what failed iss024d parity); the showcase act would flunk the protocol it
demonstrates. Fixed by the matched-scaffold control arm. Prediction (ii) made
two-sided; "three blockers solved" corrected to two. Reader-experience pass 1: the
original claim assignment overloaded the caveat-heaviest cells (WT) with the act's
headline while treating the caveat-light NT re-measurement as prelude; fixed by
the headline reassignment and the shrink-not-scatter fallback. Reader-experience
pass 2: the original trim order cut mystery t1 first — the only true
failure-to-success cell — collapsing Act 4 into a confirmatory result; fixed by
the reorder, the linkage rule, and subsampling-not-deletion. GPT-4 separation
moved from prose hope to prereg rule.

**Cost to Omer.** ~1.5 hours: ratify the prereg (~20 min), approve calibrated
scope + spend (~10 min), review the results memo (~30 min), plus the ANSWER slot.
Local + API only — no cluster, no VPN, no ping. Sonnet extension is out of budget;
single-tier Act 4 is owned as a limitation.

> DECISION:

---

## 5. D-J4 — Journal target

**Recommendation (paste into `journal_narrative_proposal.md` D-J4 slot — this is
the advisors' call; the slot records what we bring them):**

> ANSWER (2026-07-23, decisions memo §5 — recommendation TO ADVISORS): Target JAIR
> primary. The case rests on verified strengths — planning-literate audience,
> in-venue LLM-eval genre precedent (ConSCompF 2025, WorldView-Bench 2026,
> Agentic-LLMs survey 2025, per dblp), no page cap, no APC, and a verbatim-matching
> defense against JAIR's named summary-reject trigger for previously-rejected work
> ("not undergone extensive revisions" — this redo is precisely an extensive
> revision: dual-surface protocol, ~227k trials, frontier arm, contamination twin,
> pre-registered parity). Do NOT claim JAIR "rewards rigor over novelty" — its
> policy requires "originality and significance" (fetched 2026-07-23); rigor-only
> review is TMLR's property. The submission package therefore carries an
> affirmative originality case for C1: each control flipped a headline (the
> retraction record), anchored to the ABC/tau-bench genre (arXiv:2507.02825), with
> generalization beyond planning claimed — which also pre-empts the "better suited
> for a more specialised venue" summary-reject trigger. DRAFTING CONSTRAINT that
> makes the fallback real: the manuscript is written audience-self-contained from
> day one (short primer for PDDL/PlanBench/LLM-Modulo; no body section assumes
> planning-venue background) — planning insiders skim it at no cost, the TMLR
> redirect becomes genuinely mechanical, and every first-time reader gains;
> "zero translation for JAIR" is retired as a selling point. Fallback rules
> pre-committed for ALL branches: summary-reject (fast; the "~1 week" figure is
> UNVERIFIED — do not quote it as a JAIR statistic) -> identical manuscript to
> TMLR, mechanical reformat only; "reject with encouraged resubmission" ->
> resubmit to JAIR (69.6% conditional acceptance, 2025 transparency stats); plain
> full-review reject -> TMLR redirect with reviews addressed. Present advisors the
> honest probability tree — ~77% summary-reject / ~13% accept ~spring 2027 / ~10%
> late reject, BASE RATES over all 2025 submissions, not quality-conditioned — not
> the 38.6-week expectation as the headline clock. AIJ only on explicit advisor
> override (planning-flagship brand; ~20-week first decision, ~12+ month clock,
> near-zero LLM-eval corpus 2024-2026). KBS dropped (mandatory system-reframe
> contradicts the protocol-first thesis). This FLIPS the standing 2026-05-05
> AIJ-primary ranking (.local/kbs-journal-fit.md §4, drafted pre-pivot) — the flip
> is justified by AIJ's clock and genre gap, both colliding with the 07-15/07-23
> thesis. Stated assumption to CONFIRM with advisors: the Sept 2026 thesis needs a
> SUBMITTED manuscript, not an acceptance. Implication for D-J1: the
> validity/protocol THREAD is first-class body content at JAIR and TMLR alike; the
> operational MECHANICS (D1-D9 decision log, parity-prereg text, reproducibility
> checklist) remain a structured appendix summarized by one body-level table — so
> manuscript structure stays venue-orthogonal and D-J1 ratifies NOW without
> waiting on the venue conversation.

**Why (simple-first).** The venue must understand both planning and LLM
evaluation, cost nothing extra in reframing effort, and not gate the thesis clock.
JAIR is the only shortlist member that hits all three; TMLR's headline speed is
forfeited for >12-page submissions, which keeps it the ideal fallback (its rubric —
novelty explicitly not required — is the cleanest home for a previously-rejected
paper) rather than the primary.

**What the red team said and how it changed the answer.** Three independent AMEND
passes, ranking upheld. Hostile: the load-bearing "rewards rigor over novelty"
premise was factually false for JAIR and set up a ~10% late-reject branch with no
fallback trigger; fixed by rebuilding the case on verified strengths, the
affirmative C1 originality argument, pre-committing all three decision branches,
and flagging the unverified 1-week figure. Reader-experience pass 1: the original
"zero translation" selling point contradicted the "mechanical TMLR fallback"
promise and licensed writing Act 1 for planning insiders — against the
approachability goal; fixed by the audience-self-contained drafting constraint.
Reader-experience pass 2: the D-J1 rider conflated promoting the validity thread
(simplifies) with inlining operational mechanics (front-loads apparatus); fixed by
the thread-vs-mechanics split and softening proposal §6 accordingly.

**Cost to Omer.** One advisor conversation (this recommendation + the flip
argument + the thesis-clock question). Reformatting, the cover letter with the
arXiv:2509.12987 delta statement, and the reframe itself are agent-executable. No
cluster.

> DECISION:

---

## 6. D-J5 — Cheap complements (nt-ster + second family)

**Recommendation (paste into `journal_narrative_proposal.md` D-J5 slot):**

> ANSWER (2026-07-23, decisions memo §6): BOTH, in this order, with
> prereg-before-submit binding. (1) nt-ster control cells FIRST, next VPN window
> [CLUSTER — go-ahead + ping required]: 3 models (Qwen3.5-9B, gemma4:26b,
> qwen3.6-35b) x 4,560 trials, PLUS a same-apparatus nt-neut anchor co-run in the
> same submit (the 5.3pp cross-apparatus noise floor, iss024d_parity_report 07-17,
> makes an unanchored equivalence test uninterpretable). RECOMMENDED SCOPE:
> think=off AND think=on cells (~92 GPU-h total, 3 parallel rtx_6000 jobs, <4 days
> wall, same VPN window) — think=on is what licenses the 07-12 pre-commitment's
> steered-WT e2e claim family, since the only exact steered-WT e2e corpus (iss024d)
> is think=on-scoped (`iss024d_parity_prereg.md:69`, verified) and sweep6 proved
> think-mode mismatch is material (prompt-length->truncation channel). FALLBACK if
> Omer prefers minimal: think=off only (~46 GPU-h), with the 07-12 link struck and
> steered-WT e2e diagnostic-only permanently — choose explicitly, not by default.
> Apparatus pinned to iss024d's exact config (same vllm.sif tag, sbatch wrapper,
> parser flags, marketplace 1.4.0, 16K ctx); fresh run-tag so no rows land in
> canonical sweep5v2-live dirs (strip the tag post-filter — sweep6 lesson). PREREG
> BEFORE SUBMIT (agent-written development/*.md, Omer ratifies): H4 TOST +/-5pp
> against the co-run anchor with control-first noise-floor calibration, surfaces
> named (tool-verified AND delivered), per task x model n fixed, claim-licensing
> map with pre-drafted pass/fail paper language (pass -> steered e2e cited via the
> within-July factorial; fail -> CALL beat rewritten as prompt-content effect).
> Anchor scope pre-registered as exactly two uses: (a) the paired H4 confirmatory
> contrast; (b) the within-July 2x2 factorial with iss024d's existing
> wt-neut/wt-ster cells (attribution, diagnostic/steering scope) — the May +72pp
> is relabeled "replicated attribution," never "controlled by the July cells"; the
> anchor-vs-May delta is reported ONLY in the validity thread as a drift
> measurement and can never revise a NEED-stage number. (2) Second-family probe
> SECOND: Llama-3.1-8B-Instruct (llama3_json parser, REASONING_PARSER=none,
> rtx_6000:1; NOT Mistral — unplumbed --tokenizer-mode), scope = v11 for
> nt-neut/tl-neut arms + v14 for the tl-ster arm (the original "v11-only x 3 arms"
> was incoherent under summary.py arm_for — steered arms are v14-16), ~10-12h
> wall, one job [CLUSTER — go-ahead + ping]. Plumbing + smoke prep happen while
> nt-ster runs. Kill-gate in the prereg: ToolSel >= 0.95 or 0% extraction after
> one parser-config retry -> stop, report as tool-adherence data at smoke scale.
> v11-paraphrase scope justified in the prereg as a designed family-level (not
> paraphrase-level) probe. CAVEAT-ONLY INTEGRATION CAP, pre-committed: new results
> may only delete or convert existing caveats, never add body surfaces — nt-ster
> edits the existing CALL beat + Limitations only (the §5 one-figure steering cap
> holds even if H4 passes); the Llama outcome edits the family-confound
> Limitations paragraph + at most one appendix table; the anchor drift datapoint
> goes to the validity thread only. The P1 writing sprint proceeds NOW under
> worst-case scoping (steering diagnostic-only, family confound owned) so neither
> run can delay the manuscript — results can only relax prose already written.

**Why (simple-first).** Each run answers a question a journal reviewer is
guaranteed to ask ("is the steering effect just the prompt?"; "is this all a Qwen
quirk?") for under ~90 minutes of Omer's time, and neither can break a locked
number: the paper's current stance is already the worst case for both. nt-ster was
pre-registered in May (`sweep_prompt_bank_design.md:46` H4, verified) and executing
a pre-registered control is itself C1 evidence; a failed H4 is absorbable exactly
as the iss024d parity FAIL was. One Llama point bounds but does not resolve the
family confound — that bounded claim is what Limitations needs instead of an
unprobed concession (HELM precedent: single-family results confound recipe with
scale).

**What the red team said and how it changed the answer.** Both AMEND, run/park
decisions upheld. Hostile: the think=off control could not license the claims it
was sold as fixing (the 07-12-gated family lives at think=on via iss024d), and
running the headline control ad hoc without a locked analysis prereg — from
authors whose C1 is literally pre-registered parity testing — reads as
preregistration theater; fixed by the think-mode option (either/or made explicit),
the prereg-before-submit, the apparatus pin, and the within-July factorial. The
second-family arm spec incoherence is fixed (v11+v14). Reader-experience: the
anchor silently created a third no-tools apparatus vintage that could leak a drift
caveat into NEED — the paper's only apparatus-caveat-free section; fixed by the
two-use anchor scope + validity-thread-only drift rule + the caveat-only
integration cap. Synthesis note: the hostile lens wanted the anchor licensed for
the factorial, the reader lens wanted it H4-exclusive — reconciled by
pre-registering exactly the two uses and walling off NEED, honoring both concerns
(attribution power; vintage leakage).

**Cost to Omer.** ~45-90 min across 3-4 ping-gated touchpoints (submit approval,
one sync window, Llama smoke/full approval, memo review). All prereg-writing,
grading, parity analysis, and write-up is agent-executable.

> DECISION (nt-ster think-mode scope — both modes ~92 GPU-h, or off-only + strike
> the 07-12 link):

> DECISION (run both complements as specified):

---

## 7. D4 — The three parked items

**Recommendation (paste into `roadmap_eval_and_paper_completion.md` D4 slot):**

> ANSWER (2026-07-23, decisions memo §7): Keep ALL THREE parked as Future Work;
> promote none. (i) ISS-024(b) guided_json fix stays parked — a
> generation-apparatus fix creates a third apparatus variant citable only after a
> full no-tools re-sweep (the one genuine rerun cascade on the table); the
> decoupled line already delivered the corrected capability read, and
> format_parse_fail is reported data under C1's denominator discipline. AMENDED:
> run the $0 LOCAL AUDIT of the artifact's mechanism and affected-row fraction now
> (agent-executable), cited in Limitations as a C1 artifact audit — C1 lists
> "artifact audits" as a contribution component (proposal §1), so declining a
> cheap audit of a known open artifact would be an internal inconsistency a
> reviewer could quote. The FIX itself stays parked. (ii) Steering reframe stays
> parked: nt-ster (D-J5) removes the actual confound in the deployed construct;
> the reframe would add a third steering construct (~$50 API) without retro-fixing
> the first, from the budget PlanBench WT needs. (iii) Stronger contamination
> probe stays parked with a concrete promotion trigger: run the length-matched
> anon simulate leg (~$20-40, Anthropic batch, no cluster) ONLY if an advisor or
> reviewer challenges the frontier simulate cell after seeing the truncation
> decomposition (success-given-parseable 90.6 vs 89.8, CIs overlap; null extends
> to delivered per 07-15); until then the mechanism accounting answers the
> objection and the dollars belong to PlanBench WT.

**Why (simple-first).** The only item that fixes a real defect (guided_json)
forces a full re-sweep to be citable; the other two either duplicate what nt-ster
fixes or re-litigate a cell already explained. Budget coherence: parking (ii) and
(iii) is what funds the D-J3 2x2 out of the ~$70.6 remainder.

**What the red team said and how it changed the answer.** Hostile AMEND applied:
"skip even the verification-only pass" on guided_json was replaced by the $0 local
audit (keeps the fix parked, closes the internal-inconsistency exposure). The
contamination trigger and the steering-reframe supersession were upheld unchanged.
Residual honest risk carried: if the trigger ever fires and the matched probe
reveals real drift, it surfaces later than ideal — accepted because the existing
decomposition already answers the objection.

**Cost to Omer.** Zero minutes now. The trigger path, if fired, is
agent-executable batch API work.

> DECISION:

---

## 8. D-J6 — Title/abstract recentering

**Recommendation (paste into `journal_narrative_proposal.md` D-J6 slot):**

> ANSWER (2026-07-23, decisions memo §8): YES — draft title/abstract candidates in
> the next iteration (agent-executable now; all quotable numbers are locked).
> Number constraints inherit D-J2's corpus-label table verbatim — the
> title/abstract may not quote anything that table forbids. MAY use: solve lift
> +66-73pp CI-disjoint both tiers; the 0pp/+5pp/>=33pp length-shaped delivery
> gradient; the tier-shrinking validation-lift ladder. MAY NOT use:
> simulate-as-sole-source at frontier; any unscoped "cannot be done without the
> tool"; the retracted 13.5/0 and 0%-floor numbers; any two-sided interval as the
> abstract's first number; frontier simulate delivered presented as anything but
> bounds. AMENDED constraint: no unscoped universal composition-failure
> declaratives — delivered is >=95.0 on 4 of 5 frontier tasks, so "sound tools do
> not compose" must be scoped to the guarantee not transferring (e.g. "soundness
> does not transfer to the delivered answer") or dropped; the protocol-name mold
> (HELM/HAL: instrument first, domain second) and the funnel-question mold (stage
> names as mnemonic) are unaffected. Retire "Availability Is Not Enough" (anchors
> the CALL finding only; pre-dates the DELIVER stage). Abstract skeleton
> (ABC/SWE-bench order): field claim + prescribed remedy -> one honest gap number
> (gradient form) -> C1 named -> three one-number stage results -> constructive
> recommendation (grade the delivered answer; relay structured output) ->
> 227k-trial / 7-model / 2-corpus scale as protocol validation. Final prose passes
> the AI-tells rule; the NEED/CALL/DELIVER triple is structural, not decorative,
> and stays. Collision-check "the delivery gap" against existing tool-use /
> agent-eval terminology before locking the coined term.

**Why (simple-first).** Title drafting is the forcing function for the thesis
sentence; the current title anchors a superseded CALL-only framing; deferral would
couple cheap agent work to an advisor conversation it does not depend on (§5
confirms structure is venue-orthogonal).

**What the red team said and how it changed the answer.** The hostile title-scoping
constraint (no unscoped universal declaratives) is applied; "never print a
two-sided interval as the abstract's first number" is inherited from D-J1 and
restated as a hard constraint. Both lenses upheld D-J6 = yes.

**Cost to Omer.** Review 2-3 candidates (~15-30 min).

> DECISION:

---

## 9. Sequenced work plan (D-J3 + D-J5 + D4 + writing, one timeline)

Hands-on touchpoints marked **[OMER]**; cluster items marked **[CLUSTER — ping +
VPN]**. Everything else is agent-executable.

**Phase 0 — now (no ping, no VPN):**
- **[OMER ~15 min]** Annotate the 8 ANSWER slots from this memo's paste-ready
  blocks; pick the nt-ster think-mode option (§6).
- Agent: fix proposal §2 item 3 exactness error + soften §6 (per §2/§5);
  collision-check "delivery gap"; draft title/abstract candidates (§8);
  guided_json $0 local audit (§7).
- Agent: write the two preregs — `development/reference/ntster_h4_prereg.md` (TOST margin,
  anchor two-use scope, Llama kill-gate, v11/v14 arm spec) and
  `development/reference/planbench_wt_prereg.md` (matched-scaffold control, t1
  2x2, two-sided prediction ii, linkage rule, funnel-placement statement, GPT-4
  separation rule, kill criterion). **[OMER ~30 min]** ratify both.
- Agent: P1 writing sprint STARTS under worst-case scoping (steering
  diagnostic-only, family confound owned; audience-self-contained primer per §1
  principle 8) — the runs can only relax prose, never delay it (caveat-only
  integration cap, §6).

**Phase 1 — next VPN window: [CLUSTER — ping + VPN] [OMER ~15 min]**
- Submit nt-ster + nt-neut anchor (3 models, chosen think scope, iss024d-pinned
  apparatus, fresh run-tag). ~46-92 GPU-h, 3 parallel rtx_6000 jobs, <4 days wall.
- In parallel, local/API (no cluster contention): PlanBench WT adapter build +
  20-instance calibration. **[OMER ~10 min]** approve calibrated scope + API spend
  against the ~$70.6 remainder.

**Phase 2 — days 2-7 (no ping):**
- Agent: PlanBench matched-NT control + WT runs (API), then local grading
  (Rosetta VAL + plugin FD, spot-check discipline — the t2 silent-0.0 artifact is
  the cautionary precedent).
- Agent: Llama-3.1-8B parser plumbing + smoke prep while nt-ster runs.

**Phase 3 — second VPN window: [CLUSTER — ping + VPN] [OMER ~15-20 min]**
- Sync nt-ster/anchor results; run Llama smoke; kill-gate decision; if passed,
  submit the full Llama cell (~10-12h).

**Phase 4 — weeks 2-3 (no ping):**
- Agent: H4 analysis per prereg (within-apparatus TOST + within-July factorial);
  Llama analysis; PlanBench WT table + memo; integration into the manuscript under
  the caveat-only cap. **[OMER ~30-45 min]** review the result memos.

**Hard gates:** PlanBench kill criterion 2026-08-15 (graceful demotion: Act 4
shrinks to the NT-only re-measurement act, per §4); manuscript draft to advisors
~early September; JAIR submission ~Sept-Oct 2026.

**Optional, DEFAULT = NOT RUN:** the sweep5v2 storage-fixed rerun of ~5
headline-critical cells (§3 amendment) exists in the manuscript as a
pre-registered contingency answering a reviewer demand. Running it proactively is
a **[CLUSTER — ping + VPN]** decision Omer can take at any phase; it is not on the
critical path.

**Budget coherence check:** the ~$70.6 API remainder funds PlanBench (t1 2x2 at
n=200-250/cell, calibration-gated) because D4 parks the steering reframe (~$50)
and the contamination probe ($20-40, trigger-only). The two D-J5 runs spend
cluster GPU-hours, not dollars. No item double-books either channel.

**Total Omer hands-on across everything: ~2.5-4 hours**, of which ~45-90 min is
ping-gated cluster touchpoints.

---

## 10. Open questions genuinely requiring advisors

1. **Venue ratification (D-J4).** JAIR primary with the honest base-rate
   probability tree, pre-committed fallback branches, TMLR runner-up, AIJ
   override-only. This flips the standing 2026-05-05 AIJ-primary ranking — bring
   the flip argument explicitly.
2. **Thesis requirement.** Confirm the Sept 2026 MSc requirement is a SUBMITTED
   manuscript, not an acceptance — the entire venue calculus assumes it; no
   shortlisted venue can deliver acceptance by September. If the assumption is
   wrong, D-J4 reopens.
3. **Formalize the journal pivot.** D1 is recorded as a lean (roadmap,
   2026-07-15), not a commitment; AAAI-27 should be dropped formally in the same
   conversation.
4. **Cost verdict.** Already-pending external gate (roadmap "External gates"); the
   delivered-surface cost-of-pass recompute (§3) should be on the same agenda.
5. **Storage-fixed rerun posture.** Pre-registered contingency only (default), or
   run proactively before submission? Cluster cost vs pre-empting the one
   predictable reviewer demand on the flagship corpus — their risk appetite call.

Nothing else in this memo needs an advisor: D-J1, D-J2, D-J3, D-J5, D4, and D-J6
are Omer's calls, and every execution step is agent-runnable within the
touchpoints marked in §9.
