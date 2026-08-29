# nt-ster H4 — final readout, all six units complete (2026-08-29)

**Supersedes** `ntster_h4_partial_readout_20260822.md` for every number. That memo stays
on disk as the record of the void on-mode arm and the roster-gap argument; nothing in it
about the three `think=off` cells has changed.

**Scope.** All six pre-registered/amended units are now complete, valid, and analysed.
Pipeline run in the pre-registered order — targeted sync → `e2e_regrade.py --no-mcp` →
`ntster_f_gate.py` → `ntster_h4.py`. All four frozen scripts sha256-checked against
`ntster_h4_prereg.md` §8 item 9 before the run: **all four match `ff7bbd7`**. GT gate
`6af57125bde3` PASSED.

---

## 1. Headline

**All six units PASS. Paper-level branch = PASS (§3.4 first row, §5 PASS branch).**

### Verdict vector

| unit | anchor (nt-neut) | steered (nt-ster) | Δ̂ governing [90% CI] | F | MDE | verdict |
|---|---:|---:|---|---:|---:|---|
| Qwen3.5:4B off | 61.10% (2786/4560) | 59.23% (2701/4560) | **−3.03 [−4.83, −1.23]** | 1.51 | 6.80 | **PASS** |
| Qwen3.5:9B off | 66.18% (3018/4560) | 67.24% (3066/4560) | **−0.18 [−1.89, +1.52]** | 1.12 | 6.70 | **PASS** |
| Qwen3.5:9B on | 70.04% (3194/4560) | 72.04% (3285/4560) | **+1.83 [−0.28, +3.94]** | 2.17 | 7.11 | **PASS** |
| gemma4:26b-a4b off | 78.16% (3564/4560) | 78.64% (3586/4560) | **+0.52 [−0.95, +1.99]** | 2.76 | 6.47 | **PASS** |
| qwen3.6:35b off | 78.33% (3572/4560) | 78.20% (3566/4560) | **+1.34 [−0.40, +3.08]** | 2.24 | 6.74 | **PASS** |
| qwen3.6:35b on | 83.75% (3819/4560) | 83.31% (3799/4560) | **+0.49 [−1.37, +2.35]** | 0.86 | 6.86 | **PASS** |

Every cell passes the §3.1 completeness gate exactly — 9,120 rows, 1,520/variant,
per-(task, variant) shape exact, `snapshot_cap = 16384`, zero duplicates, no reweighting.
4,560 matched pairs per unit. `with_tools=False` on 9,120/9,120 rows in all six.

**Reading.** In every unit the steered directive moves the no-tools floor by under
3.1pp, with the whole 90% interval inside ±5pp. **Every ELIGIBLE task cell in every unit
is EQUIVALENT** — the condition §3.4 requires for a PASS, and there are no exceptions to
name. Realized MDE 6.47–6.80pp: an effect larger than ~6.8pp could not have hidden in
any unit, and the May +72pp is an order of magnitude outside that.

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
no-tools control now exists and **PASSES**: pooled Δ̂ −3.03 [−4.83, −1.23], EQUIVALENT,
its one ELIGIBLE task (`validate_plan`) −1.10 [−2.86, +0.66] EQUIVALENT.

**D6 is therefore moot** — it asked what a 4B FAIL would do to the claim, and 4B did not
fail. The deviation declaration is still owed regardless (see **O1**).

Two honest observations about this cell, neither of which changes the verdict:

- **It is the only unit whose pooled interval excludes zero, and the sign is negative.**
  The directive makes 4B slightly *worse* without tools (−3.03pp, −1.86pp under domain
  clustering). It sits comfortably inside the ±5pp margin, so the pre-registered label is
  EQUIVALENT and the PASS is clean. It also runs *against* the reviewer objection H4
  exists to answer: a "merely better prompt" would help, not hurt.
- **`simulate` is the one NOT-EQUIVALENT task cell in the entire family** — −14.00
  [−19.97, −8.03]. It is **UNINFORMATIVE** (its own paraphrase noise floor is F = 12.0pp,
  2.4× the effect being tested) and by §3.2 an UNINFORMATIVE cell "cannot contribute a
  FAIL"; by §3.4 it "carries no verdict authority". So the paper-level branch is PASS,
  not MIXED, and the frozen script assigns it that way. It is named here because §5's
  reporting discipline requires naming such cells, not because it is in tension with the
  verdict. It is also 23.7% censored at the snapshot cap, which §2.3(C) says makes
  `simulate` cells bounds rather than point estimates.

---

## 4. Per-task detail (governing CI; class assigned mechanically from the anchor)

| unit | task | anchor | Δ̂ [90% CI] | F | class | label |
|---|---|---:|---|---:|---|---|
| 4B off | solve | 6.7% | −1.67 [−4.32, +0.99] | 17.00 | UNINFORMATIVE | EQUIVALENT |
| 4B off | validate_domain | 19.2% | +0.28 [−0.20, +0.76] | 7.50 | UNINFORMATIVE | EQUIVALENT |
| 4B off | validate_problem | 56.0% | −1.00 [−3.81, +1.81] | 5.50 | UNINFORMATIVE | EQUIVALENT |
| 4B off | validate_plan | 74.5% | −1.10 [−2.86, +0.66] | 1.40 | **ELIGIBLE** | **EQUIVALENT** |
| 4B off | simulate | 41.7% | −14.00 [−19.97, −8.03] | 12.00 | UNINFORMATIVE | NOT-EQUIVALENT ⚠ |
| 9B off | solve | 10.3% | −1.67 [−4.89, +1.56] | 28.00 | UNINFORMATIVE | EQUIVALENT |
| 9B off | validate_domain | 25.3% | +4.17 [−0.07, +8.40] | 14.17 | UNINFORMATIVE | INDETERMINATE |
| 9B off | validate_problem | 66.3% | +1.33 [−1.72, +4.39] | 4.50 | **ELIGIBLE** | **EQUIVALENT** |
| 9B off | validate_plan | 79.8% | +0.63 [−1.24, +2.50] | 1.40 | **ELIGIBLE** | **EQUIVALENT** |
| 9B off | simulate | 34.7% | +3.67 [−2.56, +9.90] | 21.00 | UNINFORMATIVE | INDETERMINATE |
| 9B on | solve | 26.7% | +1.33 [−4.31, +6.98] | 16.00 | UNINFORMATIVE | INDETERMINATE |
| 9B on | validate_domain | 43.6% | +10.28 [+3.30, +17.26] | 6.67 | UNINFORMATIVE | INDETERMINATE |
| 9B on | validate_problem | 63.8% | +5.67 [+1.76, +9.57] | 6.50 | UNINFORMATIVE | INDETERMINATE |
| 9B on | validate_plan | 81.4% | +0.07 [−1.10, +1.23] | 1.60 | **ELIGIBLE** | **EQUIVALENT** |
| 9B on | simulate | 44.0% | +4.67 [−2.18, +11.52] | 32.00 | UNINFORMATIVE | INDETERMINATE |
| gemma off | solve | 10.3% | −4.00 [−7.68, −0.32] | 14.00 | UNINFORMATIVE | INDETERMINATE |
| gemma off | validate_domain | 79.2% | −1.39 [−4.86, +2.09] | 5.00 | UNINFORMATIVE | EQUIVALENT |
| gemma off | validate_problem | 77.7% | −0.50 [−2.88, +1.88] | 4.00 | **ELIGIBLE** | **EQUIVALENT** |
| gemma off | validate_plan | 88.3% | +0.63 [−0.46, +1.73] | 2.50 | **ELIGIBLE** | **EQUIVALENT** |
| gemma off | simulate | 44.3% | +7.67 [+3.22, +12.11] | 34.00 | UNINFORMATIVE | INDETERMINATE |
| 35b off | solve | 10.7% | −1.33 [−5.13, +2.46] | 31.00 | UNINFORMATIVE | INDETERMINATE |
| 35b off | validate_domain | 74.4% | +1.67 [−2.14, +5.47] | 9.17 | UNINFORMATIVE | INDETERMINATE |
| 35b off | validate_problem | 74.5% | +0.83 [−1.36, +3.02] | 1.00 | **ELIGIBLE** | **EQUIVALENT** |
| 35b off | validate_plan | 90.5% | −0.33 [−1.61, +0.94] | 0.60 | UNINFORMATIVE | EQUIVALENT |
| 35b off | simulate | 36.3% | −1.00 [−6.69, +4.69] | 36.00 | UNINFORMATIVE | INDETERMINATE |
| 35b on | solve | 42.0% | −7.67 [−14.11, −1.23] | 26.00 | UNINFORMATIVE | INDETERMINATE |
| 35b on | validate_domain | 81.4% | −2.50 [−7.50, +2.50] | 5.83 | UNINFORMATIVE | INDETERMINATE |
| 35b on | validate_problem | 76.0% | +1.17 [−0.36, +2.70] | 1.50 | **ELIGIBLE** | **EQUIVALENT** |
| 35b on | validate_plan | 92.6% | −0.30 [−1.10, +0.50] | 1.20 | UNINFORMATIVE | EQUIVALENT |
| 35b on | simulate | 55.0% | +4.67 [−1.13, +10.47] | 19.00 | UNINFORMATIVE | INDETERMINATE |

**8 ELIGIBLE cells across 6 units, 8 EQUIVALENT, 0 NOT-EQUIVALENT.**

The UNINFORMATIVE labels are the F gate doing its designed job: paraphrase-only pairs
move `solve` by 14–31pp and `simulate` by 12–36pp with no directive present, exactly the
pattern §3.2 predicted, so those tasks cannot resolve a 5pp question at any n.

**Per-task movements worth naming, none of which carries verdict authority.** All four
sit in UNINFORMATIVE cells whose own F exceeds the movement, or nearly so:

- 4B `simulate` −14.00, F 12.0 — see §3.
- 9B on `validate_domain` +10.28 [+3.30, +17.26], F 6.67.
- gemma off `simulate` +7.67 [+3.22, +12.11], F 34.0 — paraphrase alone moves this cell
  4.4× the effect being claimed.
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

## 6. Mechanism decomposition — VOID in all six cells

The §3.7 APPARATUS component runs **13.75–36.01% per arm** against a 1% void threshold,
so the pre-registered guard fires in every cell and the decomposition cannot be reported.
The H4 verdicts are unaffected — §3.7 never gates a verdict — and since every unit PASSed,
no mechanism label was owed in the first place (§3.7 assigns labels only to FAIL cells).

| unit | APPARATUS anchor | APPARATUS steered |
|---|---:|---:|
| 4B off | 35.07% | 36.01% |
| 9B off | 29.52% | 28.71% |
| 9B on | 26.84% | 24.93% |
| gemma off | 18.18% | 18.20% |
| 35b off | 17.48% | 17.54% |
| 35b on | 13.75% | 14.47% |

M1 directive echo is +0.00pp (arm difference) in all six cells — no cell shows the
steered arm echoing the tool name back into its text.

**Known cosmetic defect, unchanged from 08-22:** `M2 mean completion tokens` renders
`nan → nan` in every cell. The block is VOID regardless, so nothing downstream depends
on it, but it should be fixed before any future mechanism read.

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
> > appendix-ready prose in `ntster_h4_prereg.md` §9.1, sitting in the Known-limits
> > section so they travel with the Limitations material rather than being re-derived at
> > writing time.

> **O2 — Does §2.3(A) get amended in the prereg? (this is 08-22's D5, still open)**
> As written it is mode-blind and, applied to the decoupled path, guarantees a void
> corpus. Proposed amendment: scope §2.3(A) explicitly to the single-call path, and add
> one line stating the decoupled path requires parser-off, citing the June corpus and the
> August failure as evidence. A documented deviation, not a silent one.
>
> > **ANSWER: OK (Omer, 2026-08-29). DONE** — amendment written inline in
> > `ntster_h4_prereg.md` §2.3(A), scoping the original rule to the single-call path and
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
> > (`78787eb7…11629164`) in `ntster_h4_prereg.md` §8 item 9 addendum. The freeze commit
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

**Frozen scripts, verified before the run:**

| file | sha256 | matches `ff7bbd7` |
|---|---|---|
| `tools/ntster_f_gate.py` | `2ebb92f1…1471aa6e` | ✓ |
| `tools/ntster_h4.py` | `0541ad8e…ade6534e9` | ✓ |
| `tools/ntster_common.py` | `a7bc6093…e3e822f4` | ✓ |
| `tools/gt_cache_gate.py` | `db78f362…3e40fc8057b` | ✓ |

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

## 9. §4(b) factorial — result (O3, run 2026-08-29 after freeze)

`tools/ntster_factorial.py`, frozen at `78787eb7…11629164` and hashed into the prereg
before this invocation. GT gate `6af57125bde3` passed; both legs of both models pass the
completeness gate; 4,560 matched fixtures per model, 0 dropped.

### Verdict: **the clause DROPS**

| model | Δ_wt | Δ_nt | interaction [90% CI] | excludes 0 | May ref | replicated |
|---|---:|---:|---|---|---:|---|
| Qwen3.5:9B | +3.97 | +2.00 | **+0.83 [−1.98, +3.64]** | no | +9.76 | no |
| qwen3.6:35b | +1.27 | −0.44 | **−0.00 [−2.21, +2.21]** | no | +0.46 | no |

Neither interaction excludes zero, so §4(b)'s criterion is not met and §5's PASS sentence
**drops the "replicated attribution" clause** — pre-registered behaviour, and the clause
is removed rather than rewritten or weakened.

### What this does and does not mean

**It is not evidence against the attribution.** It is a null on a diagnostic that was
structurally unable to test the claim where the claim lives, for three reasons that were
all fixed before the data existed:

1. **The model that owns the effect cannot be in this factorial.** gemma has no
   `think=on` no-tools leg by construction (§2.3(B) — the decoupled mechanism stops on
   `</think>` and gemma has no think tokens). The +72pp is gemma's. The factorial can
   only see the two Qwens.
2. **The factorial is `think=on`, where these two models barely steer at all.** Their
   with-tools steering effects here are +3.97pp and +1.27pp. An interaction cannot be
   resolved out of an effect that small at a ±2–3pp half-width. The headline +72pp is a
   `think=off` effect, and `think=off` has no factorial because there is no `think=off`
   with-tools steered corpus co-run with it.
3. **The diagnostic was already declared attribution-only and budget-unmatchable**
   (§2.3(A)): `chat_with_tools` re-grants the per-task decode budget every turn up to
   `MAX_TOOL_LOOPS = 10`, while a no-tools trial gets one shared budget.

**Direction is consistent with the attribution, but the pre-registered interval is the
one that counts.** Worth recording honestly, in both directions:

- Under **domain** clustering both point estimates are positive and 35b's interval
  excludes zero (9B +1.97 [−0.09, +4.04]; 35b **+1.71 [+0.03, +3.39]**). The governing
  interval is the **wider** of the two clusterings (§3.3), which is problem clustering,
  and that includes zero. So a less conservative clustering choice would have returned
  KEEP for 35b. We take the pre-registered one. This is the designed conservatism
  working, not a close call being spun.
- On `validate_plan` — the task that owns the effect and the top of §3.7's pre-registered
  leakage ranking — the interaction is positive and excludes zero in **both** models
  (9B +7.33 [+3.92, +10.74]; 35b +2.77 [+0.08, +5.46]). Per-task cells carry no clause
  authority under §4(b), which states the estimand per model, so this cannot rescue the
  clause. It is reported because suppressing it would be selective.

**Consequence for the paper: none beyond the clause.** The CALL-beat attribution does not
rest on this factorial. It rests on the matched-cell result in §1 — gemma
`validate_plan` `think=off`, +72.0pp with tools versus +0.63pp [−0.46, +1.73] without —
which is a stronger and more direct argument, on the model and in the cell where the
effect actually lives. §5's PASS sentence stands, minus its optional bracketed clause.
