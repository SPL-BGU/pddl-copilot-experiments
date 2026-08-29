# nt-ster H4 — final readout, all six units complete (2026-08-29)

> **REVISED 2026-08-30 — post-review corrective re-run.** A 15-finding
> correctness review of PR #96 found defects in the frozen analysis code: the
> delivered surface counted censored rows as successes, the governing "problem
> (k=100)" interval was a mis-specified estimator over 220 unbalanced clusters,
> the §3.7 mechanism section read fields the overlay does not carry, and the
> legacy consistency column was constant False (full list: prereg §9.2
> deviations 3–9). The code was fixed, re-frozen and re-hashed (prereg §8
> item 9, second addendum), and every number below was regenerated from the
> checkpointed corpus. **The six-unit all-PASS verdict vector and the
> paper-level PASS branch are unchanged; every secondary number in this
> document is the corrected value.** The pre-revision text is in git history.

**Supersedes** `archive/ntster/ntster_h4_partial_readout_20260822.md` for every number. That memo stays
on disk as the record of the void on-mode arm and the roster-gap argument; nothing in it
about the three `think=off` cells has changed.

**Scope.** All six pre-registered/amended units are complete, valid, and analysed.
Pipeline run in the pre-registered order — targeted sync → `e2e_regrade.py --no-mcp` →
`ntster_f_gate.py` → `ntster_h4.py` (the 08-30 re-run needed no resync or regrade:
overlay and raw cells are checkpointed). Frozen scripts sha256-checked against
`reference/ntster_h4_prereg.md` §8 item 9 **second addendum** before the re-run. GT gate
`6af57125bde3` PASSED — now enforced by both entry points and pinned as a code constant.

---

## 1. Headline

**All six units PASS. Paper-level branch = PASS (§3.4 first row, §5 PASS branch).**

### Verdict vector

| unit | anchor (nt-neut) | steered (nt-ster) | Δ̂ governing [90% CI] | F | MDE | verdict |
|---|---:|---:|---|---:|---:|---|
| Qwen3.5:4B off | 60.32% (2697/4471) | 58.75% (2648/4507) | **−1.07 [−2.32, +0.17]** | 2.09 | 6.25 | **PASS** |
| Qwen3.5:9B off | 65.58% (2938/4480) | 66.71% (2994/4488) | **+1.25 [+0.01, +2.50]** | 0.55 | 6.25 | **PASS** |
| Qwen3.5:9B on | 69.71% (3143/4509) | 71.68% (3227/4502) | **+1.87 [+0.69, +3.06]** | 1.67 | 6.18 | **PASS** |
| gemma4:26b-a4b off | 77.83% (3496/4492) | 78.33% (3520/4494) | **+0.53 [−0.29, +1.36]** | 2.75 | 5.82 | **PASS** |
| qwen3.6:35b off | 78.05% (3513/4501) | 77.98% (3520/4514) | **+0.16 [−0.89, +1.21]** | 2.54 | 6.05 | **PASS** |
| qwen3.6:35b on | 83.57% (3768/4509) | 83.11% (3745/4506) | **−0.46 [−1.33, +0.42]** | 0.66 | 5.87 | **PASS** |

Every cell passes the §3.1 completeness gate exactly — 9,120 rows, 1,520/variant,
per-(task, variant) shape exact, `snapshot_cap = 16384`, zero duplicates, no reweighting.
`with_tools=False` on 9,120/9,120 rows in all six. Denominators above are the
**determinate** rows: 105–152 rows per cell (1.2–1.7%, all `simulate`, censored at the
16K snapshot cap) are excluded from every estimator and reported as counts plus
extreme-imputation bounds, per §2.3(C). Matched pairs per unit: 4,466–4,500 of 4,560,
the shortfall being pairs with a censored side.

**Reading.** In every unit the steered directive moves the no-tools floor by under
2pp, with the whole 90% interval inside ±5pp. **Every ELIGIBLE task cell in every unit
is EQUIVALENT** — the condition §3.4 requires for a PASS, and there are no exceptions to
name. Realized MDE 5.82–6.25pp: an effect larger than ~6.3pp could not have hidden in
any unit, and the May +72pp is an order of magnitude outside that. (Two of the six
pooled intervals — 9B off and 9B on — exclude zero on the positive side; both sit
comfortably inside the margin, so the pre-registered label is EQUIVALENT: a real but
sub-2pp prompt effect is exactly what the ±5pp design treats as floor-equivalent.)

H4's prediction holds in **both** think modes and across **four** models: the steered
wording alone does not move the no-tools floor.

### The matched-cell attribution, unchanged and now flanked

The paper's +72pp (`main.tex:501`, 0.206 → 0.926) is specifically **gemma4:26b-a4b,
`validate_plan`, with-tools, `think=off`**. Its mode-, model- and task-matched no-tools
control:

| gemma `validate_plan`, `think=off` | Δ steered − neutral |
|---|---:|
| **with tools** (canonical sweep5v2) | **+72.0pp** |
| **without tools** (this run) | **+0.63pp [−0.46, +1.73]** — ELIGIBLE, EQUIVALENT |

The sentence worth +72 points when the model can act on it is worth six tenths of a
point when it cannot. That is the CALL-beat attribution closed in the matched cell, on
the model that owns the effect.

---

## 2. What changed since the 2026-08-22 partial readout

Two cells were added and two were replaced. The three original `think=off` numbers are
**bit-identical** to 08-22 — same corpus, same frozen scripts, recomputed from scratch.

| unit | 08-22 state | now |
|---|---|---|
| 9B off / gemma off / 35b off | PASS | unchanged, PASS |
| 9B on / 35b on | **void** (empty text, 0% success) | **rerun with `--reasoning-parser none`, both PASS** |
| 4B off | not in roster | **added, PASS** |

### 2.1 The on-mode rerun is healthy, and the fix is confirmed by prediction

The 08-22 diagnosis was that the decoupled two-call path only works under
`--reasoning-parser none`, and it predicted specific recovery numbers from June's
parser-off corpora. The August rerun lands on them:

| cell | empty `response` | success | predicted from June parser-off |
|---|---:|---:|---|
| Qwen3.5:9B on (Aug rerun, parser OFF) | **8.2%** | **69.1%** | 8.8% / 68.4% |
| qwen3.6:35b on (Aug rerun, parser OFF) | **3.9%** | **82.5%** | 4.1% / 82.0% |
| *(Aug original, parser ON)* | *99.9% / 100%* | *0% / 0%* | — |

Both cells reproduce the June corpus to within a percentage point on both axes. The flag
was the whole effect, as diagnosed, and the fix is verified rather than assumed.

### 2.2 Parser-off did **not** re-manufacture the §2.3(A) grading artifact

§2.3(A) warned that `--reasoning-parser none` breaks no-tools grading through three
mechanisms, all of which assume a reasoning prefix contaminating the graded text. The
08-22 argument was that the *decoupled* path is immune, because the answer is generated
in a separate call with the reasoning re-injected as prompt. Measured on the new corpus,
`format_parse_fail` share by task and arm:

| cell | validate_domain | validate_problem | validate_plan | solve | simulate |
|---|---:|---:|---:|---:|---:|
| 9B on, neutral | 0.0% | 0.0% | 0.0% | 1.0% | 30.7% |
| 9B on, steered | 0.0% | 0.0% | 0.0% | 2.0% | 44.3% |
| 35b on, neutral | 0.0% | 0.0% | 0.0% | 12.7% | 16.3% |
| 35b on, steered | 0.0% | 0.0% | 0.0% | 11.3% | 10.7% |

Zero on all three `validate_*` tasks in all four arms — the artifact §2.3(A)(i)/(iii)
feared does not appear. `simulate` carries the residual (June 35b parser-off was 14.0%;
August 35b is 10.7–16.3%, so this is the known level, not a new problem), and `simulate`
is UNINFORMATIVE in both on-mode cells anyway (F = 32.00 and 19.00), so it never reaches
a verdict. **The 08-22 mechanism claim is confirmed on independent data.**

### 2.3 An unplanned benefit: §4(b)'s parser mismatch is gone

§2.3(A) accepted, as a stated cost, that the §4(b) factorial would "acquire a parser
difference across its nt/wt axis" — because the nt legs were to run parser-on while the
iss024d wt legs ran parser-off. The void-and-rerun forced the nt on-mode legs to
parser-**off**, which is what iss024d used. **Both legs of the factorial now share the
parser setting.** The comparison remains budget-unmatchable and therefore
attribution-only (§2.3(A)), but one of its two named confounds has been removed by
accident. See open item **O3**.

---

## 3. The 4B control (roster gap, closed)

4B was steered-but-uncontrolled: with-tools `think=off` it carries **+6.9pp** pooled and
**+9.6pp** on `validate_plan`, *larger than 9B's +2.5pp, which was controlled*. Its
no-tools control now exists and **PASSES**: pooled Δ̂ −1.07 [−2.32, +0.17], EQUIVALENT,
its one ELIGIBLE task (`validate_plan`) −1.10 [−2.86, +0.66] EQUIVALENT.

**D6 is therefore moot** — it asked what a 4B FAIL would do to the claim, and 4B did not
fail. The deviation declaration is still owed regardless (see **O1**).

Two honest observations about this cell, neither of which changes the verdict:

- **The directive's point estimate is negative here** (−1.07pp; the interval includes
  zero after the 08-30 correction — the pre-revision −3.03 was the mis-specified problem
  clustering, and its zero-exclusion does not survive the corrected estimator). To the
  extent it moves 4B at all, it moves it slightly *worse* without tools, which runs
  *against* the reviewer objection H4 exists to answer: a "merely better prompt" would
  help, not hurt.
- **`simulate` in this cell was the family's one NOT-EQUIVALENT label as originally
  shipped (−14.00), and that number was largely a grading artifact**: 23.7% of the
  cell's `simulate` rows are censored at the snapshot cap, and the pre-revision code
  counted every censored row as a delivered success. On determinate rows the cell reads
  **−2.43 [−5.33, +0.47], INDETERMINATE** — no NOT-EQUIVALENT label survives anywhere in
  the family. It remains **UNINFORMATIVE** regardless (its own paraphrase noise floor is
  F = 5.56pp) and by §3.2/§3.4 carries no verdict authority; §2.3(C) additionally makes
  censored `simulate` cells bounds rather than point estimates (Δ̂ ∈ [−31.67, +15.67]pp
  under extreme imputation — wide exactly because 94 of 300 pairs have a censored side).

---

## 4. Per-task detail (governing CI; class assigned mechanically from the anchor)

| unit | task | anchor | Δ̂ [90% CI] | F | class | label |
|---|---|---:|---|---:|---|---|
| 4B off | solve | 6.7% | −1.67 [−4.32, +0.99] | 17.00 | UNINFORMATIVE | EQUIVALENT |
| 4B off | validate_domain | 19.2% | +0.28 [−0.20, +0.76] | 7.50 | UNINFORMATIVE | EQUIVALENT |
| 4B off | validate_problem | 56.0% | −1.00 [−3.81, +1.81] | 5.50 | UNINFORMATIVE | EQUIVALENT |
| 4B off | validate_plan | 74.5% | −1.10 [−2.86, +0.66] | 1.40 | **ELIGIBLE** | **EQUIVALENT** |
| 4B off | simulate | 17.1% | −2.43 [−5.33, +0.47] | 5.56 | UNINFORMATIVE | INDETERMINATE |
| 9B off | solve | 10.3% | −1.67 [−4.89, +1.56] | 28.00 | UNINFORMATIVE | EQUIVALENT |
| 9B off | validate_domain | 25.3% | +4.17 [−0.07, +8.40] | 14.17 | UNINFORMATIVE | INDETERMINATE |
| 9B off | validate_problem | 66.3% | +1.33 [−1.72, +4.39] | 4.50 | **ELIGIBLE** | **EQUIVALENT** |
| 9B off | validate_plan | 79.8% | +0.63 [−1.24, +2.50] | 1.40 | **ELIGIBLE** | **EQUIVALENT** |
| 9B off | simulate | 10.9% | +6.95 [+2.71, +11.18] | 9.78 | UNINFORMATIVE | INDETERMINATE |
| 9B on | solve | 26.7% | +1.33 [−4.31, +6.98] | 16.00 | UNINFORMATIVE | INDETERMINATE ⚠ |
| 9B on | validate_domain | 43.6% | +10.28 [+3.30, +17.26] | 6.67 | UNINFORMATIVE | INDETERMINATE ⚠ |
| 9B on | validate_problem | 63.8% | +5.67 [+1.76, +9.57] | 6.50 | UNINFORMATIVE | INDETERMINATE |
| 9B on | validate_plan | 81.4% | +0.07 [−1.10, +1.23] | 1.60 | **ELIGIBLE** | **EQUIVALENT** |
| 9B on | simulate | 32.5% | +3.83 [−3.73, +11.39] | 30.50 | UNINFORMATIVE | INDETERMINATE ⚠ |
| gemma off | solve | 10.3% | −4.00 [−7.68, −0.32] | 14.00 | UNINFORMATIVE | INDETERMINATE |
| gemma off | validate_domain | 79.2% | −1.39 [−4.86, +2.09] | 5.00 | UNINFORMATIVE | EQUIVALENT |
| gemma off | validate_problem | 77.7% | −0.50 [−2.88, +1.88] | 4.00 | **ELIGIBLE** | **EQUIVALENT** |
| gemma off | validate_plan | 88.3% | +0.63 [−0.46, +1.73] | 2.50 | **ELIGIBLE** | **EQUIVALENT** |
| gemma off | simulate | 28.0% | +9.00 [+4.68, +13.32] | 36.33 | UNINFORMATIVE | INDETERMINATE |
| 35b off | solve | 10.7% | −1.33 [−5.13, +2.46] | 31.00 | UNINFORMATIVE | INDETERMINATE |
| 35b off | validate_domain | 74.4% | +1.67 [−2.14, +5.47] | 9.17 | UNINFORMATIVE | INDETERMINATE |
| 35b off | validate_problem | 74.5% | +0.83 [−1.36, +3.02] | 1.00 | **ELIGIBLE** | **EQUIVALENT** |
| 35b off | validate_plan | 90.5% | −0.33 [−1.61, +0.94] | 0.60 | UNINFORMATIVE | EQUIVALENT |
| 35b off | simulate | 20.7% | +3.36 [−1.01, +7.73] | 19.26 | UNINFORMATIVE | INDETERMINATE |
| 35b on | solve | 42.0% | −7.67 [−14.11, −1.23] | 26.00 | UNINFORMATIVE | INDETERMINATE ⚠ |
| 35b on | validate_domain | 81.4% | −2.50 [−7.50, +2.50] | 5.83 | UNINFORMATIVE | INDETERMINATE ⚠ |
| 35b on | validate_problem | 76.0% | +1.17 [−0.36, +2.70] | 1.50 | **ELIGIBLE** | **EQUIVALENT** |
| 35b on | validate_plan | 92.6% | −0.30 [−1.10, +0.50] | 1.20 | UNINFORMATIVE | EQUIVALENT |
| 35b on | simulate | 45.8% | +6.32 [−0.35, +12.98] | 16.83 | UNINFORMATIVE | INDETERMINATE ⚠ |

**8 ELIGIBLE cells across 6 units, 8 EQUIVALENT, 0 NOT-EQUIVALENT.** (The ELIGIBLE
family is unchanged by the 08-30 revision — the same 8 cells qualify under the
corrected eligibility rule, which now uses the domain-clustered half-width per §3.3
point 3. `simulate` anchors and deltas moved the most, because that is the only
censored task and censored rows are no longer counted as successes. No NOT-EQUIVALENT
label survives anywhere in the family; the shipped 4B `simulate` −14.00 was largely the
censoring artifact, see §3.)

The UNINFORMATIVE labels are the F gate doing its designed job: paraphrase-only pairs
move `solve` by 14–31pp and `simulate` by 5.6–36.3pp with no directive present, exactly
the pattern §3.2 predicted, so those tasks cannot resolve a 5pp question at any n.

**Per-task movements worth naming, none of which carries verdict authority.** All
sit in UNINFORMATIVE cells whose own F exceeds the movement, or nearly so:

- 9B on `validate_domain` +10.28 [+3.30, +17.26], F 6.67.
- gemma off `simulate` +9.00 [+4.68, +13.32], F 36.3 — paraphrase alone moves this cell
  4× the effect being claimed.
- 9B off `simulate` +6.95 [+2.71, +11.18], F 9.78.
- 9B on `validate_problem` +5.67 [+1.76, +9.57], F 6.50.
- 35b on `solve` −7.67 [−14.11, −1.23], F 26.0.

Do not report any of these as steering effects.

---

## 5. Drift check (§4 validity thread) — no regression, now with 4B

August neutral anchor vs canonical May `sweep5v2-live`, `think=off` only (the on-mode
cells run a different apparatus and are not comparable). Per §3.6 `simulate` is excluded
as grader-confounded. Per §4 this is a drift measurement and can never revise a
NEED-stage number.

| model | solve | validate_domain | validate_problem | validate_plan | **pooled (4 tasks)** |
|---|---:|---:|---:|---:|---:|
| Qwen3.5:4B | −1.0 | +0.0 | −0.5 | +0.5 | **+0.2** |
| Qwen3.5:9B | −0.3 | −0.3 | +0.7 | +0.1 | **+0.1** |
| gemma4:26b-a4b | +2.7 | +1.4 | +2.8 | +0.5 | **+1.0** |
| qwen3.6:35b | +1.3 | +6.7 | −1.2 | −0.4 | **+0.2** |

n = 4,260 per side per model. Pooled drift **+0.1 to +1.0pp, all non-negative**, well
inside the ±1.0–1.2pp 90% Wilson half-widths. **No regression in the August corpus.** The
single per-task movement above 5pp (35b `validate_domain` +6.7) sits in a cell whose own
paraphrase noise floor is F = 9.17pp, so it is not resolvable either. 4B, the new cell,
is the tightest of the four.

---

## 6. Mechanism decomposition — VALID after the 08-30 revision (was falsely VOID)

The pre-revision "VOID in all six cells, APPARATUS 13.75–36.01%" reading was an
artifact: the frozen script read `failure_reason`, `response` and `tokens` off overlay
rows, which do not carry those fields, so every failed row fell through to APPARATUS
and the 1% guard self-fired (that is also why M1 was 0.00 and M2 tokens rendered
`nan`). The corrected entry point joins each overlay row to its raw trial row
(`--trials-dir`) and computes the partition from the fields the prereg names.

On the corrected read, **APPARATUS is 0.00% in every arm of every cell** — the July
apparatus was clean all along — and the ΣΔ = −Δ̂ identity closes to 0.000pp in all six
cells. Since every unit PASSes, **no mechanism label is owed** (§3.7 assigns labels
only to FAIL cells); the decomposition is reported descriptively:

| unit | TRUNC a→s | CHANNEL a→s | CONTENT a→s | M1 Δ | len% a→s | mean tok a→s |
|---|---|---|---|---:|---|---|
| 4B off | 3.78→3.95 | 4.43→4.17 | 31.47→33.13 | +0.48 | 6.5→5.7 | 1663→1588 |
| 9B off | 3.95→3.43 | 4.84→5.59 | 25.62→24.26 | +0.37 | 6.4→5.8 | 1871→1808 |
| 9B on | 10.65→8.42 | 1.95→1.91 | 17.70→17.99 | +0.20 | 12.6→10.2 | 7682→7081 |
| gemma off | 1.58→1.31 | 6.52→6.83 | 14.07→13.53 | +0.02 | 3.3→3.1 | 1275→1303 |
| 35b off | 1.80→1.53 | 6.64→6.05 | 13.51→14.44 | +0.79 | 3.2→3.0 | 1950→1977 |
| 35b on | 3.30→3.71 | 2.08→1.75 | 11.04→11.43 | +0.00 | 4.9→5.3 | 4157→4063 |

(Shares of determinate rows per arm, anchor→steered; M1 is the arm difference in pp.
Censored rows are 1.0–2.0% per arm, reported separately and folded into neither side.)

M1 directive echo is +0.00 to +0.79pp — at most a fraction of a point of the steered
arm echoing a tool name into its text, nowhere near a mechanism-bearing signal. The
failure mass everywhere is CONTENT, with the one visible mode effect being 9B on's
truncation share (10.65% anchor, the shared-budget signature §2.3(B) exists to manage).

---

## 7. Open items — for Omer

> **O1 — Two deviations must be declared in writing.** Both are known and both are
> conservative, but they belong in the appendix paragraph, stated plainly rather than
> presented as the original design:
> **(a)** The control roster was expanded from 3 to 4 models *after seeing results*
> (4B added 08-22). Conservative under §3.4's intersection-union rule — a fourth unit
> can only make the conjunctive claim harder to satisfy — and it passed.
> **(b)** The on-mode arm ran `--reasoning-parser none`, a deviation from §2.3(A), after
> the literal-prereg configuration produced a void corpus. Justified in §2.2 above and
> confirmed harmless in §2.2's table.
>
> > **ANSWER: OK (Omer, 2026-08-29). DONE** — both declarations written as
> > appendix-ready prose in `reference/ntster_h4_prereg.md` §9.1, sitting in the Known-limits
> > section so they travel with the Limitations material rather than being re-derived at
> > writing time.

> **O2 — Does §2.3(A) get amended in the prereg? (this is 08-22's D5, still open)**
> As written it is mode-blind and, applied to the decoupled path, guarantees a void
> corpus. Proposed amendment: scope §2.3(A) explicitly to the single-call path, and add
> one line stating the decoupled path requires parser-off, citing the June corpus and the
> August failure as evidence. A documented deviation, not a silent one.
>
> > **ANSWER: OK (Omer, 2026-08-29). DONE** — amendment written inline in
> > `reference/ntster_h4_prereg.md` §2.3(A), scoping the original rule to the single-call path and
> > requiring parser-off on the decoupled path. It also marks the "Cost, stated"
> > paragraph void in fact (the nt/wt parser difference no longer exists), records
> > `CHANGELOG.md:512`'s "parser-state-proof" claim as empirically false, and adds the
> > standing rule that a readiness smoke must assert `len(response) > 0`.

> **O3 — Compute the §4(b) factorial now that it is unblocked?**
> This decides whether §5's PASS sentence keeps or drops its "replicated attribution"
> clause. It was dropped on 08-22 *because the on-mode nt legs were void*. They now exist,
> for both Qwens, and (per §2.3 above) the parser mismatch the prereg budgeted for is
> gone. The estimand is locked in §4(b): interaction Δ_wt(ster−neut) − Δ_nt(ster−neut)
> per model, delivered surface both legs, §3.3 clustered CI; "replicated" = interaction CI
> excludes 0 with sign matching May. Inputs are on disk (`results/iss024d-e2e-live` wt
> legs + this run's nt legs), models = 9B and 35b only (gemma has no on-mode nt leg).
> **The catch:** no frozen script computes it. Writing that code now — after seeing the
> H4 result, to decide a paper sentence — is exactly the ordering §8 item 9 exists to
> prevent, even though the estimand itself was locked in advance. Recommendation: write
> it, freeze and hash it *before* pointing it at data, and record the hash in the prereg
> the same way items 9/10 were.
>
> > **ANSWER: OK — write+freeze (Omer, 2026-08-29). DONE** — `tools/ntster_factorial.py`
> > written, rehearsed against a forced-zero configuration, frozen and hashed
> > (`78787eb7…11629164`) in `reference/ntster_h4_prereg.md` §8 item 9 addendum. The freeze commit
> > precedes the first real invocation in git history, so the ordering is checkable
> > rather than asserted. Result in §9 below.

> **O4 — D4 from 08-22, now answerable.** It asked whether the off-mode PASSes get
> written up immediately or held for on-mode. Moot — everything has landed. The live
> question is only *when* the §5 PASS-branch integration happens, under the pre-committed
> caveat-only cap (CALL beat + Limitations in the body; per-task table, F gate, MDE table,
> drift check, apparatus-failure declaration and the two O1 deviations in an appendix).
> **No tex has been touched.**
>
> > **ANSWER: OK (Omer, 2026-08-29).** Scope and placement approved as written —
> > caveat-only cap, CALL beat + Limitations in the body, everything else (per-task
> > table, F gate, MDE table, drift check, apparatus-failure declaration, the two §9.1
> > deviations) in an appendix. **The tex itself is deferred to a later session**, per
> > the standing instruction to stop after aggregation. Still true: no tex touched.

---

## 8. Artefacts and provenance

| artefact | path |
|---|---|
| corpus (6 cells, 653 MB) | `results/ntster-h4-live/` |
| void failure record (2 cells, 08-22) | `results/ntster-h4-void-parseron/` |
| overlay | `results/derived/e2e_overlay/ntster-h4-live/` |
| F gate | `results/derived/ntster_f_gate.json` + `.md` |
| H4 results | `results/derived/ntster_h4_results.json` + `ntster_h4_report.md` |
| 08-22 partial (archived) | `results/derived/*_partial20260822.*` |

**Jobs.** off-mode `20392775` (9B, gemma, 35b) · 4B off-mode `20490174`, COMPLETED
12:47:16 · on-mode rerun `20489912`, COMPLETED (35b 1d 03:17, 9B 4d 04:54). All exit
`0:0`; no TIMEOUT, no `rc=3` VRAM failure on any cell.

**Frozen scripts.** The original freeze (`ff7bbd7`, verified before the 08-29 run) is
**superseded by the 2026-08-30 post-review corrective re-freeze** — see prereg §8
item 9 second addendum for the current five sha256s and §9.2 for the declared
deviations. Every number in this document was produced by the re-frozen scripts:

| file | sha256 (2026-08-30) |
|---|---|
| `tools/ntster_f_gate.py` | `e9b746b7…1d01d200` |
| `tools/ntster_h4.py` | `272f96b9…cba67c26` |
| `tools/ntster_common.py` | `49d869f3…cfb71ed7` |
| `tools/gt_cache_gate.py` | `1181781e…9d8f3897` |
| `tools/ntster_factorial.py` | `16f03b59…294ea40c` |

**Deviations from the §7 step 4 literal command, both procedural:**

1. **Targeted rsync** of the six `*_ntster-h4` dirs instead of `sync.sh
   results/ntster-h4-live` — `sync.sh` globs every `slurm_vllm_*` dir and would have
   pulled the 55 archived sweep-5 corpora into a fresh dir and fed them to the regrader.
   Same deviation as 08-22, same non-effect: the frozen scripts read the overlay dir.
2. **The two void on-mode cell dirs were moved out of `results/ntster-h4-live/` before
   the sync**, to `results/ntster-h4-void-parseron/`. The cluster-side dirs were deleted
   on 08-22, so the rerun wrote fresh dirs under the same names; leaving the local void
   copies in place would have let rsync merge void rows into live cells. The failure
   record survives intact at the new path.

`results/derived/gt_cache.json` and `gt_cache_stamp.json` in this worktree are symlinks
to the canonical copies in the main checkout, so the frozen scripts run at their
pre-registered default invocation with no CLI override.

---

## 9. §4(b) factorial — result (O3; revised 2026-08-30 with the corrected surface)

`tools/ntster_factorial.py`, re-frozen 2026-08-30 (`16f03b59…294ea40c`, prereg §8
item 9 second addendum). GT gate `6af57125bde3` passed; both legs of both models pass
the completeness gate — now **enforced**, not just recorded. Fixtures with a censored
side on either leg are excluded per §2.3(C) (the iss024d wt legs carry 9.1% (9B) and
1.0% (35b) censored rows, which the pre-revision code had been counting as successes
on both sides): 3,765 matched fixtures for 9B (788 dropped), 4,417 for 35b (143
dropped).

### Verdict: **the clause DROPS** — but on different grounds than first shipped

| model | Δ_wt | Δ_nt | interaction [90% CI] | excludes 0 | May ref | replicated |
|---|---:|---:|---|---|---:|---|
| Qwen3.5:9B | +8.54 | +1.87 | **+8.12 [+4.61, +11.63]** | **yes** | +11.38 | **yes** |
| qwen3.6:35b | +2.05 | −0.47 | **+2.62 [+0.74, +4.50]** | **yes** | −0.11 | no |

The pre-revision reading ("neither interaction excludes zero — an underpowered null")
does not survive the grading fix: with censored rows no longer scored as successes,
**both interactions are positive and exclude zero**. 9B fully replicates (CI excludes
0, sign matches its +11.38pp May reference). 35b's interaction also excludes zero, but
its May reference effect is **−0.11pp — an essentially null reference** — so the sign
cannot meaningfully match and the §4(b) criterion ("every model") is not met. The
clause **drops**, as pre-registered; it is removed, not rewritten.

### What this does and does not mean

**The corrected factorial is directionally consistent with the attribution in both
models** — the steering effect is larger with tools than without, by +8.12pp (9B) and
+2.62pp (35b) — and in 9B it now meets the full replication criterion. What blocks the
clause is not an absent interaction but a May reference (35b, +think=on, with-tools)
whose own steering effect is a hair below zero, giving the sign-match test nothing to
match against. Three standing caveats still bound what this diagnostic can say:

1. **The model that owns the effect cannot be in this factorial.** gemma has no
   `think=on` no-tools leg by construction (§2.3(B) — the decoupled mechanism stops on
   `</think>` and gemma has no think tokens). The +72pp is gemma's. The factorial can
   only see the two Qwens.
2. **The factorial is `think=on`**, and the headline +72pp is a `think=off` effect;
   `think=off` has no factorial because there is no `think=off` with-tools steered
   corpus co-run with it.
3. **The diagnostic was already declared attribution-only and budget-unmatchable**
   (§2.3(A)): `chat_with_tools` re-grants the per-task decode budget every turn up to
   `MAX_TOOL_LOOPS = 10`, while a no-tools trial gets one shared budget. No rate from
   it may be quoted as an effect size.

On `validate_plan` — the task that owns the effect and the top of §3.7's pre-registered
leakage ranking — the interaction is positive and excludes zero in both models. Per-task
cells carry no clause authority under §4(b), which states the estimand per model, so
this cannot rescue the clause; it is reported because suppressing it would be selective.

**Consequence for the paper: none beyond the clause.** The CALL-beat attribution does
not rest on this factorial. It rests on the matched-cell result in §1 — gemma
`validate_plan` `think=off`, +72.0pp with tools versus +0.63pp [−0.46, +1.73] without
(a cell with no censoring, bit-identical across the revision) — which is a stronger and
more direct argument, on the model and in the cell where the effect actually lives.
§5's PASS sentence stands, minus its optional bracketed clause.
