# Pre-registration — PlanBench frontier with-tools arm (Haiku 4.5)

**Status:** DRAFT awaiting Omer's ratification (annotate the ANSWER slots, then the
RATIFY slot). **No build or spend before ratification.**
**Date:** 2026-07-24. **Binding source:** `development/journal_decisions_memo.md` §4
(accepted D-J3, 2026-07-24); scoped to UNRUN cells only — the 06-22 bare-NT rows
(graded, `development/planbench/planbench_frontier_haiku_nt.md`) are untouched and
become the published-apparatus replication layer.

## 1. Claims and headline assignment (fixed)

- **Act 4 headline = the already-graded NT layer** (honest-denominator regrade, t2
  silent-0.0 artifact fix, t7 chat-format grading critique, Haiku t1 41.0 beats
  GPT-4 31.4 CI-disjoint, Mystery collapse replication). The WT arm can neither
  strengthen nor weaken this claim.
- **WT carries the explicitly-labeled SECONDARY claim:** "the funnel replicates when
  the model operates the prescribed remedy on the field's instrument" — external
  validity for C2, within-apparatus only. Single-tier (Haiku) is owned as a
  limitation; Sonnet extension is out of budget.
- WT-vs-GPT-4 comparison is structurally excluded (presentation rules, §7).

## 2. Design

**Backend.** Adapter over `tools/frontier_runner.py` (SDK Tool Runner, D1=B; its
docstring pre-plans this reuse). Model pinned `claude-haiku-4-5`; tool execution on
the harness `MCPPlanner` with the full marketplace roster (pddl-parser, pddl-solver,
pddl-validator; marketplace 1.4.0); `max_iterations=MAX_TOOL_LOOPS`; prompt caching
ON; per-trial token/turn logging; `anthropic` package version recorded in run meta.
Live API (multi-turn loop cannot batch).

**Scaffold.** System scaffold containing (a) an NL→PDDL formalization step
instruction, (b) a task-format clause (answer in the upstream extractor's expected
format), (c) tool-use guidance. User message = the upstream PlanBench prompt,
unchanged (same prompts the 06-22 NT rows answered). **Scaffold text is frozen at
the calibration sign-off gate (§8); any post-freeze change voids the prereg for
affected cells and restarts them.**

**Matched-scaffold no-tools control (the primary comparator).** Identical run in
every respect — same SDK loop, same system scaffold including the NL→PDDL step and
task-format clause, same instance set, same grading — with an **empty tool list as
the ONLY ablation**. The 06-22 bare-NT rows (no system prompt) are NOT the control;
they are a replication layer, and the matched-NT-vs-bare-NT delta is reported once
as a scaffold effect in the validity thread, never as a treatment contrast.

**Cells, in priority order** (t2 excluded — optimal_plan tool unbuilt; t7 excluded
from WT — grading critique only, Act 5; logistics out of scope):

| pri | cell pair (WT + matched-NT) | role |
|---|---|---|
| 1 | blocksworld t1 | near-ceiling confirmation |
| 2 | mystery_blocksworld t1 | the failure→success cell (NT 0.8%) |
| — | **target = {clean, mystery} × {matched-NT, WT} 2×2 on t1** | primary contrasts |
| 3 | blocksworld t3 | verification-gap probe (prediction iii) |

**Budget valve = subsampling, never whole-cell deletion within the t1 2×2:** n
drops 250 → 200 before anything is cut; the only cuttable cell pair is t3 (which
strikes prediction iii per the linkage rule). If even the t1 2×2 misses budget at
n=200, kill criterion (a) fires for the whole arm (§8).

**Instance subsample.** Fixed seed **20260724**. One index set S, |S| = 250 (floor
200), drawn from the 500-instance blocksworld pool stratified by gold-plan-length
quartile. S is reused verbatim in all four t1 cells and the t3 pair. Pre-lock
check: verify the clean↔mystery 1:1 instance correspondence (deterministic
obfuscation) before pairing; if it fails, mystery gets an independent same-seed
same-stratification draw and clean-vs-mystery contrasts become unpaired.

> ANSWER (n + seed; default n=250, seed 20260724):

## 3. Predictions (pre-registered, with outcome bands)

Linkage rule: **any prediction whose test cell is trimmed is struck** from the
prereg — reported as struck, not as unsupported.

- **(i) Tools convert failure to success on mystery t1; clean t1 confirms near
  ceiling.** Bands for WT mystery t1 (Wilson 95% CI): NO-RESCUE = CI upper < 5%;
  PARTIAL = CI midpoint in [5, 50); RESCUE = CI midpoint ≥ 50. Clean t1 WT band:
  ≥ 90% (the frontier-suite solve-delivered 95.0 analog).
- **(ii) TWO-SIDED Mystery mechanism — both directions publishable.** Rescue is
  mechanistically plausible (formalization is semantics-blind transcription and FD
  ignores predicate names); persistence of the collapse is equally publishable
  (the failure lives in NL→PDDL formalization under obfuscation). Neither outcome
  is a failed experiment.
- **(iii) Tool-available t3 closes Haiku's verification gap vs its own matched-NT:**
  paired improvement (McNemar exact, p < 0.05) with WT t3 in the ≥ 90 band.
  **Struck if t3 is trimmed.**

> ANSWER (band thresholds 5/50/90 as operationalized above):

## 4. Funnel-placement statement (named BEFORE data)

The NL→PDDL formalization interface must have a fixed home in the funnel taxonomy
before any WT data is graded. **Proposal: an input-boundary stage upstream of
NEED** — NL-specified problems enter through a formalization boundary before
tool-need recognition; formalization losses are charged to that boundary stage, not
to CALL. Alternative (memo-sanctioned): an explicit CALL extension
(formalization-as-argument-construction).

> ANSWER (input-boundary upstream of NEED / CALL extension):

## 5. Grading

Local, zero cluster: upstream `response_evaluation.py` unmodified; VAL = the
Rosetta x86_64 Mac build; FAST_DOWNWARD pinned to the pddl-solver plugin venv even
where unused (no silent-missing-dependency path — the t2 silent-0.0 artifact is
the cautionary precedent). Per newly graded cell: (a) ≥ 4 hand-verified instances,
2 expected-correct + 2 expected-incorrect; (b) extraction-rate distribution check;
(c) **any cell grading exactly 0.0% or 100.0% triggers a mandatory artifact audit
before the number is used anywhere.**

## 6. Analysis

Per-cell accuracy with Wilson 95% CI, correct/TOTAL denominator (no dropped
instances). Primary contrasts, both paired on S: WT vs matched-NT within config
(McNemar exact + paired Δ with CI); clean vs mystery within arm (paired iff the
correspondence check passes). Funnel decomposition per the §4 placement. Bare-NT
replication delta reported in the validity thread only.

## 7. Presentation rules (prereg rules, not prose intentions)

- WT cells never share a table or figure with GPT-4 rows. **Table A** = NT vs
  committed GPT-4 (existing caveats). **Figure B** = within-Haiku paired
  matched-NT→WT deltas, no GPT-4 column.
- t7 appears only in Act 5's grading critique.
- Headline assignment of §1 is a presentation rule: WT numbers are introduced as
  secondary, within-apparatus.

## 8. Budget, calibration gate, kill criteria

**Ceiling:** the ~$70.6 API remainder (D4 parks the steering reframe and the
contamination probe precisely to fund this).

**Calibration gate:** run ~20 instances from S through WT blocksworld t1 (+ a
5-instance mystery spot-check); measure $/trial (caching on), turn counts,
loop_exhausted rate, extraction rate. Project the full t1 2×2 (+ t3 if headroom).
**[OMER ~10 min]** approves calibrated scope + spend before the full run; scaffold
freezes here.

**Kill criteria** (either fires → convert to Future Work): (a) calibration projects
the t1 2×2 above the remainder even at n=200/cell; (b) no graded WT table by
**2026-08-15**. **Fallback shape = SHRINK, NOT SCATTER:** Act 4 survives as the
NT-only re-measurement act with this WT design published inside it as
pre-registered Future Work; the NT beats are not dispersed across other acts.

## 9. Ratification

> RATIFY (design + predictions + rules above are binding as annotated):
