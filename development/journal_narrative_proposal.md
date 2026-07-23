# Journal Narrative Proposal (redo, 2026-07-23)

**Status:** PROPOSAL for discussion. Nothing here is decided; rulings go to
`paper_notes_discussions.md`. Supersedes the deleted 07-17 branch draft — this is a
clean rewrite that starts from that draft's self-critique conclusions instead of
appending them as revision layers.
**Premise:** venue = journal (D1 lean, 2026-07-15 — JAIR/AIJ-class, no page cap, no
AAAI crunch; not yet formally committed with advisors). The AAAI draft in
`paper/main.tex` is raw material, not the shape.
**Data state:** post-07-17 — iss024d complete + parity FAILED (separate-apparatus
labeling binds), pooled e2e table final, NT corpora de-censored, decoupled line and
its paper retraction landed.

---

## 1. Thesis

*Sound tools do not compose into sound tool-augmented LLMs — and standard
evaluation practice cannot see where the composition fails. We contribute (C1) a
measurement protocol that can, and (C2) a fully-worked symbolic-planning case study
of what it reveals.*

Two co-equal contributions, one arc. The protocol is first on purpose: our
retraction history shows each control we added flipped a headline (simulate 0%→40%
under budget decoupling; tool-graded→delivered flipped with-tools reads; snapshot
de-censoring collapsed bounds). A narrative that led with findings would carry that
history as a liability; a narrative that leads with the protocol makes it the
evidence base. This aligns with the external critique of tool-benchmark grading
(ABC, arXiv:2507.02825 — τ-bench crediting empty responses is the same defect we
quantify).

**C1 — the protocol:** dual-surface grading (tool-verified vs delivered/e2e-strict),
contamination twin, budget-decoupling control, denominator discipline
(correct/TOTAL, empty=incorrect), pre-registered parity testing, artifact audits.
**C2 — the findings**, organized as a three-stage funnel over the question: *when an
LLM is given a correct-by-construction planning tool, what determines whether the
user gets a correct answer?*

## 2. Data inventory (what is citable, and under which label)

**Tier A — complete, headline-grade:**
1. **sweep5v2-live** (canonical): 4 Qwens + Gemma4-26B × 5 tasks × 3 arms × think
   on/off; 4,560 no-tools trials/cell, 91,200 with-tools. RQ0.1–0.6 locked.
   With-tools e2e is **bounds-only** (500-char snapshots); tool-verified exact.
2. **sweep6** (anonymized twin): contamination **clean null** (think=off ≤1.3pp,
   zero CI-disjoint; think=on exceptions are a tokenization artifact, documented).
3. **Frontier corpus:** Sonnet 4.6 + Haiku 4.5, NT both corpora (de-censored
   07-15, $0) + WT under full-response storage. Exact e2e + tool-verified.
4. **Decoupled think-budget line** (4 Qwens): the control that retracted the
   simulate 0% floor — true unaided simulate 0/23/22/40% content-correct
   (0.8B→35B), format-compliance 0% for all.
5. **iss024d open-roster WT e2e rerun:** 5 cells × 9,120, complete 07-17.
   **Parity vs sweep5v2 FAILED** (prereg; gemma floor 5.3pp, Qwen 7/20 TOST, max
   |Δ| 11.3pp on solve, parser-off truncation mechanism) → citable ONLY as a
   *labeled separate-apparatus replication*; within-corpus paired contrasts
   (delivered vs tool-verified) fully valid.
6. **E2E overlay (D1–D9 + Phase 5):** dual grading surface over every corpus with
   per-row extraction provenance; pooled table final 07-17.

**Tier B — supporting:** cost analyses (cost-of-pass, cost-per-success);
tool-call iteration stats (median 1 call; 13% zero-call); with-tools frontier
probe (75-trial ladder); external calibration memo (BFCL / τ-bench / MCP suites).

**Tier C — incomplete, not body-ready:** PlanBench v1 no-tools (35B ≈ GPT-4 on
blocksworld; v2 tools arm never launched — 2 recorded blockers; Haiku NT responses
on disk ungraded); Sonnet-WT-anon (deliberately skipped); sweep7 (discarded).

## 3. The argument, act by act

**Act 1 — The field's claim.** Planning is the canonical LLM failure mode
(PlanBench, Valmeekam et al. NeurIPS 2023; Kambhampati et al. ICML 2024 position),
and the prescribed remedy is coupling to sound external solvers/verifiers
(LLM-Modulo; the formalizer line: LLM+P, Guan et al., Huang & Zhang ACL 2025,
Tantakoun et al. ACL 2025).

**Act 2 — The gap we occupy.** The remedy was validated with *researcher-wired*
pipelines; the deployed 2025–26 reality (MCP, agentic tool use) has the **model
operating the tools**. Nobody has measured the coupling itself under model
autonomy. Tool-use benchmarks measure orchestration breadth, and have documented
grading flaws (ABC). Thesis restated: the tool's soundness guarantee holds only
tool-side; the loss concentrates at three model-side interfaces.

**Act 3 — The audit (our suite), the three-stage funnel:**
- **NEED** — does the model need the tool? *Confirms* "LLMs can't plan" with 2026
  frontier data (solve unaided: open 8–11%, Sonnet 28.7%; tool lift +66–73pp
  CI-disjoint at every tier). *Refines* "LLMs can't verify": standalone
  verification against external ground truth is capability-gated and near-ceiling
  at frontier (90–97%), collapsing down-ladder — verification migrates inside the
  model before generation does. Framed carefully vs the self-critique literature
  (Stechly et al.; Huang et al. ICLR 2024): standalone verdict ≠
  self-critique-in-loop; we reconcile, not strawman. simulate is the honest
  middle: apparatus-bound zero retracted, decoupled control recovers 22–40% at
  ≥4B, frontier delivers ~40–60. Contamination null certifies highs as capability
  and floors as incapability.
- **CALL** — given need, does the model invoke it? Invocation propensity, not tool
  competence, is the open-model bottleneck (accuracy-given-call >92% saturates;
  P(call) is the variable). Tool availability can *harm*: −67pp validate_plan
  (Gemma), silence-not-error — the strongest counterexample to "adding sound
  tools is monotone". Steering repairs it (+72pp) — scoped to tool-verified
  surfaces and labeled diagnostic for e2e (no nt-ster control exists; see §5).
- **DELIVER** — given a correct tool result, does the user receive it? The
  quantified scoring-inflation factor: tool-verified vs delivered diverge,
  length-shaped (~0pp verdicts, ~5pp plans, ≥33pp trajectories), replicated
  across two frontier tiers (a stronger model does NOT transcribe better) and
  larger on the open roster (iss024d simulate delivered 7–15 vs tool-verified
  63–92; gemma validate_plan inverts — answers without competent tool use).
  The 9B paradox (best delegator, worst restater) makes it memorable.
  Presented as *why C1's dual surface is mandatory* — with the trivial
  production mitigation (relay structured tool output programmatically) stated
  plainly, so the claim is modest and bulletproof rather than oversold.

**Act 4 — The external anchor (PlanBench with tools), IF run (D-J3).** Not "our
external anchor" but the demonstration that **C1 changes published conclusions on
the field's own instrument**: the prescribed remedy, operated by the model, graded
delivered-answer on the honest denominator, with GPT-4 rows on the same yardstick.
Pre-register predictions before the sweep (mirrors the iss024d prereg): (i) tools
convert failure→success where need+call+deliver all clear; (ii) losses concentrate
in formalization walls and long-output transcription, not tool competence;
(iii) no-tools rows replicate the published ordering. Secondary: completion-era
exact-match grading understates chat models — made constructively, with numbers.
The two recorded v2-arm blockers (truncation cap, denominator honesty) must be
fixed pre-launch.

**Act 5 — Implications.** Benchmark builders: grade the delivered answer, report
tool-trace success as a diagnostic layer (our dual-surface protocol as template).
System builders: steering fixes propensity cheaply; transcription decays with
length — relay structured output, don't ask the model to restate it. Planning
debate: LLM-Modulo works as a *managed* coupling; model-side interfaces are where
deployed systems fail. Economics closes the loop (cost-of-pass: tools buy
correctness, not brevity; luxury on frontier validation, necessity on generation).

## 4. Known weaknesses the narrative must own (from the 07-17 self-critique)

- **Family confound (the big one):** 4 Qwens + 1 Gemma — scale confounded with
  post-training recipe; "9B paradox" could be a Qwen quirk; frontier adds a third
  family, not a control. Limitations owns it head-on: ladder claims labeled
  within-family, recipe-vs-scale unresolved.
- **Stage-3 construct is contestable:** requiring restatement of long outputs is
  partly harness-imposed. Defended by presenting it as a measured
  scoring-inflation factor + benchmark-practice recommendation, not a discovery
  about model cognition.
- **Steering lost its control:** no nt-ster arm → e2e steering reads are
  confounded (prompt content vs tool access). Kept honest by scoping (§3 CALL).
- **Validity thread cuts both ways:** a hostile reviewer reads three retractions
  as "what's still latent?" Answer: surviving claims survived adversarial
  regrading — which is exactly why the protocol is C1, not color.
- **Internal-validity overspend vs breadth** (227k trials, one tool ecosystem,
  mostly one family): absorbed by framing the suite as a *case study* under C1,
  not a claim to benchmark standardhood.
- **PlanBench late-binding risk:** must serve C1 (protocol changes conclusions),
  or it reads as a second paper stapled on.

## 5. Promote / demote / cut

**Promote:** e2e_strict as the quoted with-tools surface (= D2 option (a), which
journal space makes affordable); the delivered-fidelity finding into abstract +
title candidates; the measurement-validity thread into a first-class section
(retractions narrated as controls).

**Keep as single beats (one table/figure each):** contamination control (a
certificate, not a storyline); cost-of-pass + cost-per-success; steering (one
figure inside CALL); frontier ladder woven through the stages as the capability
axis.

**Demote to appendix:** per-token efficiency index + decomposition; think=on
companion (body keeps the budget-cliff as a validity finding; headlines stay
think=off ≥9B per 05-24); iteration stats; external-calibration table.

**Cut / Future Work:** Haiku-WT full open-sweep ladder, BF16, multi-tool
orchestration, ISS-024(b) guided_json fix, steering reframe, stronger
contamination probe (unless D-J5 promotes one).

**Corpus-labeling discipline carries verbatim:** iss024d = separate-apparatus
replication (never THE with-tools number; paired gaps within-corpus only);
sweep5v2 e2e = bounds; frontier = exact; steered-WT e2e = diagnostic-only.

## 6. Structural consequences for the manuscript

- Results reorganize from the AAAI 6-subsection scorecard into the funnel
  (NEED → CALL → DELIVER), each stage opening open-roster and closing frontier.
- RQ verdicts re-home, not disappear: RQ0.1/0.2/0.5 → NEED; RQ0.3/0.4 → CALL;
  RQ0.6 + overlay → DELIVER; cost → Discussion.
- Journal room absorbs what AAAI squeezed: full overlay methods (D1–D9), the
  parity prereg protocol, reproducibility checklist inline.
- Contamination presented as a two-probe story vs PlanBench's Mystery-BW
  (semantic obfuscation collapses GPT-4; our structure-preserving renaming moves
  nothing — different manipulations, both informative).

## 7. Cheap complements (weigh against time; neither is a gate)

- **nt-ster control cells** (no-tools × steered bank, think=off, ≥9B): closes the
  steering confound for near-zero GPU cost. Highest value-per-hour left.
- **One second-family probe** (~8B Llama/Mistral, think=off, validate_* + solve,
  stratified n): bounds the "single-family artifact?" objection. If forced to
  choose, PlanBench wins (it serves C1) — but choose consciously.

## 8. Decisions needed (annotate inline)

**D-J1 — Ratify the thesis shape.** Protocol-first hybrid (C1 protocol + C2
case-study findings) as proposed, vs findings-first funnel with methods demoted
to a section.

> ANSWER:

**D-J2 — Ratify D2 = (a).** e2e_strict becomes the quoted with-tools surface
everywhere; tool-verified moves to the mechanism layer. This proposal assumes it.

> ANSWER:

**D-J3 — PlanBench tools arm in scope?** Act 4 as written requires fixing the two
blockers + running v2 open roster + frontier (~$70 API remainder + cluster time)
+ pre-registered predictions. In, or Future Work?

> ANSWER:

**D-J4 — Journal target.** JAIR vs AIJ vs other — affects length norms and
whether the validity thread is a section or appendix.

> ANSWER:

**D-J5 — Cheap complements.** Run nt-ster cells? Run the second-family probe?
Neither / either / both.

> ANSWER:

**D-J6 — Title/abstract recentering** on the composition-failure thesis: want
draft candidates in the next iteration?

> ANSWER:
