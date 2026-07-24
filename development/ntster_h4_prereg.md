# Pre-registration — nt-ster H4 control + nt-neut anchor (+ Llama second-family probe)

**Status:** DRAFT awaiting Omer's ratification (annotate the ANSWER slots, then the
RATIFY slots). **No cluster submit before ratification; submit itself is ping-gated
(VPN window).**
**Date:** 2026-07-24. **Binding source:** `development/journal_decisions_memo.md` §6
(accepted D-J5, 2026-07-24). H4 itself was pre-registered in May
(`development/sweep_prompt_bank_design.md:46`); this document locks the July
execution + analysis before any data exists.

## 1. Hypothesis

**H4 (control / falsification):** the steered directive alone does not move the
no-tools floor — `(no-tools, v14-16)` ≈ `(no-tools, v11-13)` within a ±5pp
equivalence margin, tested within a single July apparatus. If H4 fails, the H2
attribution of the May +72pp steering effect to steering-under-tools is
compromised and the CALL beat is rewritten as a prompt-content effect (§5).

Why a co-run anchor: the 5.3pp cross-apparatus noise floor
(`results/derived/iss024d_parity_report.md`, 07-17) makes nt-ster-vs-May-nt-neut
uninterpretable. The anchor re-runs nt-neut in the same submit so the H4 contrast
is within-apparatus.

## 2. Design

**Arms.** nt-ster = no-tools, prompt variants v14-16 (`summary.py arm_for`:
steered = v14-16). Anchor = no-tools, v11-13, co-run in the same submit at full
matched n (equal precision on both sides of the TOST; same cell shape as the
canonical corpus).

**Roster:** Qwen3.5-9B, gemma4:26b (gemma4_26b-a4b), qwen3.6-35b.

**Think-mode scope (ACCEPTED 07-24): think=off AND think=on** (~92 GPU-h total,
3 parallel rtx_6000 jobs, < 4 days wall — memo estimate). Downgrading to off-only
at the submit ping remains Omer's explicit option; it strikes the 07-12
steered-WT e2e link permanently (the only exact steered-WT e2e corpus, iss024d, is
think=on-scoped — `iss024d_parity_prereg.md`).

**Cell shape (fixed; verified against `results/sweep5v2-live` 9B/on/no-tools):**
4,560 trials per model × mode × arm = 3 variants × 1,520; per task per cell:
solve 300, validate_domain 360, validate_problem 600, validate_plan 3000,
simulate 300 (100/120/200/1000/100 per variant). Totals: 2 arms × 2 modes ×
3 models = 12 cells = 54,720 trials.

**Apparatus pin = iss024d's exact config** (submit path frozen at `6007032`, job
19293221 vintage): same vllm.sif tag, same sbatch wrapper, `--reasoning-parser
none`, 16K response snapshots, marketplace 1.4.0, 16K ctx. This is what licenses
the within-July factorial (§4b) and makes every row exactly e2e-gradeable.

**Run-tag:** fresh, e.g. `--run-tag ntster-h4`; results sync to a NEW directory
(never into `results/sweep5v2-live`). Sweep6 lesson applies: the run-tag suffix
breaks the analyzer cell-parser — strip it post-filter.

> ANSWER (think-mode scope — confirm both modes, or off-only + strike the 07-12
> link; decidable now or at the submit ping):

## 3. Analysis plan (locked before data)

**Surfaces named.** Primary surface = **delivered** (e2e overlay grading of the
final answer; exactly gradeable under the 16K/parser-off apparatus — no-tools has
no tool-verified surface). The legacy scoring-path success is reported once as a
consistency check. In the factorial (§4b), the iss024d with-tools cells report
BOTH tool-verified and delivered, per iss024d conventions.

**Control-first noise-floor calibration (computed BEFORE the H4 contrast is
read).** F = max |Δ̂| over the three within-arm paraphrase pairs (v11-v12,
v11-v13, v12-v13) in the ANCHOR arm, per model × mode pooled over tasks
(n=1,520/variant). Paraphrases are designed-equivalent, so F estimates
sampling + paraphrase noise at the contrast's own granularity. If F ≥ 5pp for a
cell, the ±5pp margin is declared uninterpretable there — reported as
UNINFORMATIVE, never rescued.

> ANSWER (noise-floor control = within-anchor paraphrase pairs as above; the
> alternative is a gemma-as-control-model design mirroring the iss024d parity
> report):

**H4 decision rule.** TOST with ±5pp margin ≡ 90% Newcombe CI of
Δ = p(nt-ster) − p(nt-neut) contained in (−5, +5).
- Primary granularity: per model × mode, pooled over tasks and variants
  (n = 4,560/side). Robustness companion: unweighted task-mean Δ (validate_plan
  is 66% of pooled trials).
- Secondary: the 30 model × mode × task cells, 90% Newcombe CI each, verdict
  EQUIVALENT / NOT-EQUIVALENT / UNDERPOWERED (CI half-width > 5pp with midpoint
  inside the margin).
- Per-model×mode verdict: **PASS** iff the pooled CI ⊂ (−5,+5) AND no task cell's
  CI lies entirely outside (−5,+5); **FAIL** if the pooled CI lies entirely
  outside OR any task cell's CI does; INCONCLUSIVE otherwise.
- Paper-level: H4 holds iff all 6 model × mode cells PASS; named exceptions carry
  the fail language for their cells.

> ANSWER (primary granularity = pooled model × mode as above):

## 4. Anchor scope — exactly two uses (pre-registered wall)

- **(a)** The paired H4 confirmatory contrast (§3).
- **(b)** The within-July 2×2 factorial {nt, wt} × {neut, ster} with iss024d's
  existing wt-neut/wt-ster cells — attribution only, diagnostic/steering scope,
  think=on, models = the roster∩iss024d intersection (Qwen3.5-9B, qwen3.6-35b;
  gemma has no iss024d wt cells and sits out; 0.8B/4B have no July nt cells and
  sit out). The May +72pp is relabeled "replicated attribution," never
  "controlled by the July cells."

The anchor-vs-May delta (|July nt-neut − sweep5v2 nt-neut| per cell) is reported
ONLY in the validity thread as a drift measurement. **It can never revise a
NEED-stage number.** No third use exists.

## 5. Claim-licensing map (pre-drafted paper language)

- **PASS →** steered e2e cited via the within-July factorial. Draft: "A
  pre-registered control (H4, May 2026), executed in July 2026 against a co-run
  neutral anchor under the iss024d apparatus, finds the steered directive alone
  does not move the no-tools floor (TOST ±5pp, all model × mode cells
  equivalent). The steering effect is therefore attributed to the directive's
  interaction with tool access, with attribution replicated in a within-July
  factorial."
- **FAIL →** CALL beat rewritten as a prompt-content effect. Draft: "The
  pre-registered H4 control failed: the steered directive alone moves the
  no-tools floor by Δ = X pp [CI] on ⟨cells⟩. We therefore report the steering
  result as a prompt-content effect and qualify the CALL-stage attribution
  accordingly." (Executing and reporting a failed pre-registered control is
  itself C1 evidence, as with the iss024d parity FAIL.)
- **UNINFORMATIVE / INCONCLUSIVE cells →** reported as such; no claim licensed
  or withdrawn on their basis.

**Caveat-only integration cap (pre-committed):** results may only delete or
convert existing caveats, never add body surfaces. nt-ster edits the existing
CALL beat + Limitations only; the §5 one-figure steering cap holds even if H4
passes. The P1 writing sprint proceeds under worst-case scoping (steering
diagnostic-only), so neither run can delay the manuscript.

## 6. Second-family probe — Llama-3.1-8B-Instruct (runs SECOND)

**Purpose:** bound (not resolve) the single-family confound (HELM precedent:
single-family results confound recipe with scale). Outcome edits the
family-confound Limitations paragraph + at most one appendix table.

**Spec:** meta-llama/Llama-3.1-8B-Instruct; tool parser `llama3_json`;
`REASONING_PARSER=none`; rtx_6000:1; single mode (no think mode). Arms = v11
nt-neut + v11 tl-neut + v14 tl-ster (3 × 1,520 = 4,560 trials, ~10-12h wall, one
job). The v11/v14-paraphrase scope is a designed family-level probe (not
paraphrase-level generalization) — `arm_for` maps steered = v14-16, so a
"v11-only × 3 arms" spec is incoherent. Plumbing + smoke prep happen while
nt-ster runs; smoke gets full-run resources (`--time 24:00:00`).

**Kill-gate (evaluated at smoke, one parser-config retry allowed):** stop and
report as tool-adherence data at smoke scale if the tools arms show
tool-selection BELOW 0.95, or answer extraction is 0%. NOTE: memo §6 literally
reads "ToolSel >= 0.95 or 0% extraction → stop"; the ≥ reading would kill on
GOOD adherence, so this prereg encodes the < reading — confirm.

> ANSWER (kill-gate direction: ToolSel < 0.95 → stop, per the reading above):

## 7. Operational plan (ping-gated where marked)

1. Ratification (this doc) — no ping.
2. **[CLUSTER — ping + VPN]** Submit nt-ster + anchor: 3 parallel rtx_6000 jobs
   (one per model, its 4 cells), iss024d-pinned apparatus, fresh run-tag,
   explicit `--time` (72h wrapper default; verify TimeLimit after submit).
   Preflight per standing rule (pull → rebuild venvs → verify imports); strict
   serialization within a job, no shotgun resubmits.
3. Local while running: Llama parser plumbing + smoke prep; H4 analysis script
   skeleton (reads both arms from the new results dir, never pools corpora).
4. **[CLUSTER — ping + VPN]** Sync; run noise-floor F, then H4 per §3; Llama
   smoke → kill-gate decision → full Llama cell if passed.
5. Results memo; manuscript integration under the §5 cap.

## 8. Ratification

> RATIFY (nt-ster + anchor design and analysis as annotated):

> RATIFY (Llama probe spec + kill-gate as annotated):
