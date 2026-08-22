# nt-ster H4 — partial readout on the complete cells (2026-08-22)

**Scope.** Analysis of the cells that had finished as of 2026-08-22, per Omer's ask:
report only units whose variants are all complete, so the statistics are trustworthy.
Pipeline run exactly in the pre-registered order — targeted sync →
`e2e_regrade.py --no-mcp` → `ntster_f_gate.py` → `ntster_h4.py`. The three frozen
scripts were sha256-checked against the hashes recorded in `ntster_h4_prereg.md` §8
item 9 before the run: **all three match `ff7bbd7`**. GT gate `6af57125bde3` passed.

Artefacts:
- corpus `results/ntster-h4-live/` (322 MB, 5 cell dirs)
- overlay `results/derived/e2e_overlay/ntster-h4-live/`
- `results/derived/ntster_f_gate.json`
- `results/derived/ntster_h4_results.json` + `ntster_h4_report.md`

Sole deviation from the §7 step 4 literal command: a targeted rsync of the five
`*_ntster-h4` dirs instead of `sync.sh results/ntster-h4-live`, because `sync.sh`
globs every `slurm_vllm_*` dir and would have pulled the 55 archived sweep-5 corpora
into a fresh dir and fed them to the regrader. No methodological effect — the frozen
scripts read the overlay dir and were untouched.

---

## 1. Headline

**Three cells are complete, valid, and all PASS. Both `think=on` cells are void and
carry no information — this is an apparatus failure, not a result.**

The reliable picture from this run is **`think=off`, all three models**. It is not
"two complete models": `qwen3.6:35b`'s on-mode cell reached 9,120 rows and was
reported ✓ 100% by `status.sh`, but every one of those rows is empty (§3).

### Verdict vector

| unit | anchor (nt-neut) | steered (nt-ster) | Δ̂ governing [90% CI] | F | verdict |
|---|---:|---:|---|---:|---|
| Qwen3.5:9B off | 66.18% (3018/4560) | 67.24% (3066/4560) | **−0.18 [−1.89, +1.52]** | 1.12 | **PASS** |
| gemma4:26b-a4b off | 78.16% (3564/4560) | 78.64% (3586/4560) | **+0.52 [−0.95, +1.99]** | 2.76 | **PASS** |
| qwen3.6:35b off | 78.33% (3572/4560) | 78.20% (3566/4560) | **+1.34 [−0.40, +3.08]** | 2.24 | **PASS** |
| Qwen3.5:9B on | — | — | — | — | INCONCLUSIVE (incomplete, 3,824/9,120) |
| qwen3.6:35b on | — | — | — | — | INCONCLUSIVE (void — see §3) |

Completeness gate: all three off cells pass exactly — 9,120 rows, 1,520/variant,
per-(task, variant) shape exact, `snapshot_cap = 16384`. No reweighting needed.
4,560 matched pairs per cell.

**Reading.** In every complete unit the steered directive moves the no-tools floor by
under 1.4pp, with the whole 90% interval inside ±5pp. H4's prediction holds at
`think=off`: **the steered wording alone does not move the no-tools floor.** The
realized MDE is 6.47–6.74pp — i.e. an effect larger than ~6.5pp could not have hidden
here, and the May +72pp steering effect is three orders of magnitude outside that.

**Paper-level branch: INCONCLUSIVE**, purely because the two on-mode units have no
data. It is *not* mixed and *not* a FAIL — no ELIGIBLE cell is NOT-EQUIVALENT anywhere.

### Per-task detail (governing CI; class assigned mechanically from the anchor)

| unit | task | anchor | Δ̂ [90% CI] | F | class | label |
|---|---|---:|---|---:|---|---|
| 9B off | solve | 10.3% | −1.67 [−4.89, +1.56] | 28.00 | UNINFORMATIVE | EQUIVALENT |
| 9B off | validate_domain | 25.3% | +4.17 [−0.07, +8.40] | 14.17 | UNINFORMATIVE | INDETERMINATE |
| 9B off | validate_problem | 66.3% | +1.33 [−1.72, +4.39] | 4.50 | **ELIGIBLE** | **EQUIVALENT** |
| 9B off | validate_plan | 79.8% | +0.63 [−1.24, +2.50] | 1.40 | **ELIGIBLE** | **EQUIVALENT** |
| 9B off | simulate | 34.7% | +3.67 [−2.56, +9.90] | 21.00 | UNINFORMATIVE | INDETERMINATE |
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

Every ELIGIBLE cell in every unit is EQUIVALENT — the condition §3.4 requires for a
PASS. The UNINFORMATIVE labels are the F gate doing its designed job: the
paraphrase-only pairs move `solve` by 14–31pp and `simulate` by 21–36pp with no
directive present, exactly the pattern §3.2 predicted from the canonical corpus, so
those tasks cannot resolve a 5pp question at any n.

**Two per-task movements worth naming, neither of which carries verdict authority:**
- gemma `simulate` +7.67 [+3.22, +12.11] — the only interval sitting mostly outside
  the margin. Its own F is 34.00pp, so paraphrase alone moves this cell ~4.4× the
  effect being claimed. Noise-dominated, correctly UNINFORMATIVE. Do not report it as
  a steering effect.
- gemma `solve` −4.00 [−7.68, −0.32], F 14.00pp. Same story, opposite sign.

`simulate` came back live as §3.6 predicted (34.7 / 44.3 / 36.3% anchor vs 0.0% under
the retired grader), so the pre-registered decision not to declare it degenerate was
correct. It still fails the F gate in all three cells.

**Mechanism blocks (§3.7) are VOID in all three cells** — the APPARATUS component is
17.5–29.5% per arm against a 1% void threshold. That is the pre-registered guard
firing, and it means the decomposition cannot be reported. The H4 verdicts are
unaffected (§3.7 never gates the verdict). Minor: `M2 mean completion tokens` renders
`nan` in all cells; cosmetic only, the block is void regardless, but worth a fix
before the final memo.

---

## 2. Qwen3.5:9B, as asked

`Qwen3.5:9B off` is a **complete, sealed unit** and is reported above in full: anchor
66.18%, steered 67.24%, Δ̂ −0.18 [−1.89, +1.52], **PASS**, MDE 6.70pp. Its two
ELIGIBLE tasks (`validate_problem`, `validate_plan`) are both EQUIVALENT.

`Qwen3.5:9B on` is at 3,824/9,120 rows AND void. It contributes nothing.

---

## 3. Both `think=on` cells are void — root cause

### What is on disk

| cell | rows | empty `response` | success | `thinking` present |
|---|---:|---:|---:|---:|
| qwen3.6:35b on | 9,120 | **9,120 (100%)** | **0** | 0 |
| Qwen3.5:9B on | 3,824 | **3,822 (99.9%)** | **0** | 0 |

`error` is empty on every row and `done_reason=stop` on 96.8%, so nothing crashed.
The models generated: a representative row carries
`think_completion=8192, answer_completion=4768, turns=2, call2_prompt=2049` —
12,960 tokens produced and **both text fields stored empty**. `failure_reason`
resolves to `format_parse_fail` (96.8%) simply because there is nothing to parse.

The text is not recoverable. `response` is `""` on disk; the harness never stored it.

### Why

The decoupled two-call path was designed for, and only ever validated under,
`--reasoning-parser none`. `pddl_eval/chat.py:422` says so in its own docstring
("populated when the parser is off — **the configured path for the decoupled sweep,
DECISION B**"), and `development/CHANGELOG.md:512` records the decision: *"The
decoupled sweep will run with the parser OFF (DECISION B) to remove the
`reasoning_content`-flush ambiguity entirely."*

The same file claims the reconstruction is *"parser-state-proof … so it works whether
or not the server runs `--reasoning-parser qwen3`."* **That claim is a code-reading
argument and it is now empirically false.** It was never measured with the parser on.

`ntster_h4_prereg.md` §2.3(A) — a correct and important correction — ruled that the
reasoning-parser override is **NOT** passed, so this run served the per-model default
`qwen3`. §2.3(A) was reasoning about the **single-call** no-tools path, where
reasoning and answer share one output stream. Nobody re-checked it against §2.3(B)'s
**two-call** decoupled path, where they do not. Two individually-correct decisions,
incompatible when composed.

### The controlled comparison that proves it

Same models, same decoupled apparatus, same 4,560-row shape — June's
`results/decoupled-rollup/*_decoupled-thinkon` corpora, run with the parser **off**:

| cell | empty `response` | success |
|---|---:|---:|
| Qwen3.5:9B on decoupled (June, parser OFF) | 8.8% | **68.4%** |
| qwen3.6:35b on decoupled (June, parser OFF) | 4.1% | **82.0%** |
| Qwen3.5:9B on ntster-h4 (Aug, parser ON) | 99.9% | **0%** |
| qwen3.6:35b on ntster-h4 (Aug, parser ON) | 100% | **0%** |

The parser flag is the only thing that differs, and it is the whole effect.

### Why the smoke passed

The §8 item 8 live-smoke (prereg, 2026-08-20) validated the composition on
`v14 solve turns=2 think_tok=8192 answer_tok=4768 call2_prompt=2049 done=stop` —
**token counters and turn structure, never response content.** Every one of those
numbers is still correct today on rows that contain no text. The smoke checked the
plumbing and not the water.

*Lesson for the next readiness gate: a smoke assertion must include
`len(response) > 0` on a non-trivial share of rows.*

### §2.3(A) does not actually forbid parser-off on the decoupled path

§2.3(A)'s three failure mechanisms all assume a reasoning prefix contaminating the
graded text. In the decoupled path the answer is generated in a **separate call**,
with the reasoning consumed in call 1 and re-injected as *prompt*, so call 2's content
is answer-only. The June parser-off corpus confirms this empirically — the
`format_parse_fail` artifact §2.3(A) feared does not appear:

| task (June 35b decoupled, parser OFF) | success | format_parse_fail |
|---|---:|---:|
| simulate | 40.0% | 14.0% |
| solve | 39.3% | 12.0% |
| validate_domain | 80.3% | 0.0% |
| validate_plan | 91.6% | 0.0% |
| validate_problem | 77.2% | 0.0% |

So the rerun fix is a flag, not a redesign: **on-mode submits pass
`--reasoning-parser none`; off-mode keeps the default.** This costs nothing
methodologically because §2.3(B) already declares the two modes *different
apparatuses* whose numbers may not be compared across the mode axis, and they are
already separate submits.

### Cost exposure right now

Job `20392801_0` (Qwen3.5:9B on-mode) is **still RUNNING** on `cs-6000-01` —
1d 23h elapsed, **5d 00h remaining**, appending void rows (3,829 at last check).
Every remaining GPU-hour produces nothing.

---

## 4. Open decisions

> **STATUS 2026-08-22 — D1, D2, D3 ANSWERED AND EXECUTED by Omer.** Job `20392801`
> cancelled; both void on-mode dirs deleted cluster-side (local copies kept as the
> failure record); on-mode arm resubmitted as **job `20489912`** with
> `--reasoning-parser none`, run-tag `ntster-h4`, `--time 7-00:00:00`, both tasks
> RUNNING, TimeLimit verified, pins re-verified `6007032` / `5e4f9c0`.
> D4 and D5 remain open.

> **D1 — Cancel job `20392801_0` now?**
> It has ~5 days left and cannot produce usable rows. Cancelling frees the rtx_6000
> immediately. Nothing is lost: the 3,824 rows on disk are void, and a rerun cannot
> resume from them (resume keys off `trials.jsonl`, which would make it skip exactly
> the void keys — so **the corpus dir must be moved aside, not resumed into**).
> Recommendation: **cancel**, and `mv` both on-mode cell dirs to `*_VOID-parseron`.
>
> > ANSWER: **YES — DONE.** Cancelled `20392801`, queue confirmed empty. Omer chose
> > delete over move; executed cluster-side only, since the full 322 MB sync already
> > holds both void cells locally under `results/ntster-h4-live/`, so the failure
> > record survives for the appendix declaration at no risk.

> **D2 — Rerun the on-mode arm with `--reasoning-parser none`?**
> Reconstructed cost from §2.3(B): ~105h (9B) + ~27h (35b) ≈ **132 GPU-h**. Same
> submit as before plus `--reasoning-parser none`.
> **REVISED after §5 below:** this is *not* load-bearing for the headline claim. The
> paper's +72pp is a gemma **`think=off`** effect, and its matched control is already
> done and PASSED. The on-mode arm buys pre-registration completeness (the May prereg
> sized H4 over both modes) and the `paper/main.tex:406` "(model, mode, task)"
> sentence — for the two Qwens only, since gemma has no on-mode nt leg by design.
> Recommendation: **defer, do not cancel the idea.** Decide it against P1 writing
> priority rather than against the headline claim, which no longer depends on it.
>
> > ANSWER: **RERUN NOW (Omer overrode the defer).** Submitted as job `20489912`,
> > array 0-1, `rtx_6000:1`, `--time 7-00:00:00`, `--reasoning-parser none`,
> > `--run-tag ntster-h4`. Off-mode cells untouched.

> **D3 — Add a content assertion to the smoke before resubmitting?**
> A ~20-minute smoke that asserts `len(response) > 0` on ≥90% of rows and non-zero
> success, on both models, before committing 132 GPU-h. The last smoke passed while
> the run was already broken.
> Recommendation: **yes** — this is the cheapest insurance available.
>
> > ANSWER: **Satisfied more cheaply — no separate smoke job.** The accumulator writes
> > incrementally, so the first rows of the real run are themselves the smoke: the
> > content assertion (`len(response) > 0`) is run against live `trials.jsonl` minutes
> > after start, with the same kill-and-fix option and no extra queue cycle.
> > The assertion itself is still owed as a permanent check in the readiness gate.

> **D4 — Do the three off-mode PASSes get written up now, or held until on-mode lands?**
> They are final and will not change: the cells are sealed, the scripts are frozen,
> and a later on-mode rerun cannot alter an off-mode number. The §5 claim-licensing
> map, however, is written against the full verdict vector, so the *paper sentence*
> may need the on-mode cells before it can be stated unconditionally.
> Recommendation: write the off-mode result into the results memo now, flagged
> "on-mode pending", so the writing is not blocked by a 132 GPU-h queue.
>
> > ANSWER:

> **D5 — Does §2.3(A) get amended in the prereg?**
> As written it is mode-blind and, applied to the decoupled path, guarantees a void
> corpus. Proposed amendment: scope §2.3(A) explicitly to the single-call path and add
> one line stating the decoupled path requires parser-off, citing the June corpus and
> this failure as the evidence. This is a documented deviation, not a silent one.
>
> > ANSWER:

---

## 5. What this run was for, and what it actually bought

**Purpose.** H4 is a **falsification control**, not a capability measurement. The paper
attributes a large steering effect to the directive *interacting with tool access*. The
obvious reviewer objection is that the sentence is simply a better prompt and would help
with no tools at all. H4 removes the tools, keeps the sentence, and checks the floor does
not move. **A PASS — no movement — is the desired outcome.** A FAIL would have forced the
CALL beat to be rewritten as a prompt-content effect (§5 FAIL branch).

**Which effect it protects, measured.** The headline number in `paper/main.tex:501`
(success $0.206\!\to\!0.926$, the +72pp) is **gemma4:26b-a4b, `validate_plan`,
with-tools, `think=off`**:

| gemma validate_plan, with-tools | plain (v11-13) | steered (v14-16) | Δ |
|---|---:|---:|---:|
| **think=off** | 20.6% (n=3000) | 92.6% (n=3000) | **+72.0pp** |
| think=on | 0.6% (n=3000) | 43.8% (n=3000) | +43.1pp |

**So the control that matters most is the one that finished.** Same model, same task,
same mode, same prompt sentence, tools removed:

| gemma `validate_plan`, `think=off` | Δ steered − neutral |
|---|---:|
| **with tools** (canonical) | **+72.0pp** |
| **without tools** (this run) | **+0.63pp [−0.46, +1.73]** — ELIGIBLE, EQUIVALENT |

That is the attribution, closed, in the matched cell: the sentence that is worth +72pp
when the model can act on it is worth **six tenths of a point** when it cannot. The
off-mode arm was not optional and it delivered precisely what it was commissioned for.

**Consequence for the on-mode arm.** It is the control for the *secondary* +43.1pp
`think=on` effect, and covers only the two Qwens (gemma has no on-mode nt leg, §2.3(B)).
It is a completeness item, not a load-bearing one. See revised D2.

## 6. Drift check (§4 validity thread) — no regression

The August neutral anchor reproduces the canonical May corpus. Per §3.6 `simulate` is
excluded (grader-confounded); per §4 this is a drift measurement only and can never
revise a NEED-stage number. Components include an unpinned weight revision (§2.3(D)).

| model | task | May (sweep5v2) | Aug (ntster-h4) | Δ |
|---|---|---:|---:|---:|
| Qwen3.5:9B | solve | 10.7% | 10.3% | −0.3 |
| Qwen3.5:9B | validate_domain | 25.6% | 25.3% | −0.3 |
| Qwen3.5:9B | validate_problem | 65.7% | 66.3% | +0.7 |
| Qwen3.5:9B | validate_plan | 79.7% | 79.8% | +0.1 |
| **Qwen3.5:9B** | **pooled (4 tasks)** | **68.3%** | **68.4%** | **+0.1** |
| gemma4:26b-a4b | solve | 7.7% | 10.3% | +2.7 |
| gemma4:26b-a4b | validate_domain | 77.8% | 79.2% | +1.4 |
| gemma4:26b-a4b | validate_problem | 74.8% | 77.7% | +2.8 |
| gemma4:26b-a4b | validate_plan | 87.8% | 88.3% | +0.5 |
| **gemma4:26b-a4b** | **pooled (4 tasks)** | **79.5%** | **80.5%** | **+1.0** |
| qwen3.6:35b | solve | 9.3% | 10.7% | +1.3 |
| qwen3.6:35b | validate_domain | 67.8% | 74.4% | +6.7 |
| qwen3.6:35b | validate_problem | 75.7% | 74.5% | −1.2 |
| qwen3.6:35b | validate_plan | 90.9% | 90.5% | −0.4 |
| **qwen3.6:35b** | **pooled (4 tasks)** | **81.1%** | **81.3%** | **+0.2** |

n = 4,260 per side per model. Pooled drift is **+0.1 to +1.0pp, all non-negative**, well
inside the ±1.0–1.2pp 90% Wilson half-widths. **There is no regression in the August
corpus.** The single per-task movement above 5pp (35b `validate_domain` +6.7) sits in a
cell whose own paraphrase noise floor is F = 9.17pp, so it is not resolvable either.

The only zeros in this run are the two `think=on` cells, and those are empty-text
apparatus failures (§3), not model behaviour.

---

## 7. Roster gap — 4B was uncontrolled, and is now being controlled (2026-08-22)

**Raised by Omer**: why not all four Qwens (0.8B / 4B / 9B / 35b)?

The roster was fixed at three models in `journal_decisions_memo.md` §6 (accepted
2026-07-23) and ratified into this prereg before any data existed, so it was not a
choice made during the run. But the substantive check had never been done, so it was
done now.

### The effect H4 exists to attribute

With-tools, `think=off`, canonical `sweep5v2-live`, plain (v11-13) → steered (v14-16),
deduped by trial key:

| model | pooled Δ | solve | validate_domain | validate_problem | validate_plan | simulate | H4 control |
|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3.5:0.8B | **+0.0** | +2.0 | +1.7 | −7.7 | +1.6 | −3.7 | none — **not needed** |
| Qwen3.5:4B | **+6.9** | +4.0 | +1.4 | +2.8 | **+9.6** | −2.0 | **was missing → job 20490174** |
| Qwen3.5:9B | +2.5 | +0.7 | +0.0 | −5.0 | +2.9 | +18.0 | PASS |
| gemma4:26b-a4b | **+47.4** | −0.7 | +0.8 | +0.3 | **+72.0** | −1.0 | PASS |
| qwen3.6:35b | **+14.8** | +29.0 | +0.8 | +0.5 | +17.1 | +22.3 | PASS |

**0.8B needs no control.** There is no steering effect on it to attribute (+0.0pp
pooled). H4 exists to rule out "the directive is merely a better prompt"; where the
directive does nothing *with* tools either, there is no claim to protect.

**4B was a real gap.** +6.9pp pooled and +9.6pp on `validate_plan`, uncontrolled —
and **larger than 9B's +2.5pp, which was controlled.** That asymmetry is not
defensible on effect size, so it is being closed rather than argued around.

### Not a power problem

"Too weak to measure" would have been an acceptable reason. It is not the reason. On
the canonical `think=off` neutral arm, tasks inside the §3.3 ELIGIBLE band
(anchor ∈ [10%, 90%]):

| model | pooled anchor | tasks in ELIGIBLE band |
|---|---:|---|
| 0.8B | 45.9% | 3/5 (`validate_domain`, `validate_problem`, `validate_plan`) |
| 4B | 58.2% | 3/5 (same three) |
| 9B | 63.8% | 4/5 |
| gemma | 74.3% | 3/5 |
| 35b | 75.7% | 2/5 |

4B and 0.8B are **as testable as gemma and more testable than 35b** at `think=off`.
(0.8B's `think=on` half genuinely is degenerate — nt-neut extraction 4/4,560 = 0.088%,
prereg §6 G3 — but that constrains only the on-mode leg.)

### Action

`Qwen3.5:4B`, `think=off`, `--no-tools --include-no-tools-steered`, run-tag
`ntster-h4`, `--time 5-00:00:00` → **job 20490174**, RUNNING, TimeLimit verified.
Deliberately submitted **without** `--reasoning-parser` and **without**
`--decoupled-budget`, matching the three completed off-mode cells exactly — apparatus
parity with the cells it will be reported beside matters more than any other
consideration here.

### Declare this as a deviation

The roster is being expanded **after** seeing results, which must be stated plainly
rather than presented as the original design. It is a conservative deviation: adding a
unit to a control family adds chances for the control to **fail**, not to pass, and the
intersection-union rule in §3.4 means a fourth unit can only make the conjunctive
equivalence claim harder to satisfy. It is not model-shopping. The declaration belongs
in the same appendix paragraph as the on-mode apparatus failure.

> **D6 — if the 4B cell FAILS, what happens to the claim?**
> Pre-commit the answer now, before the data lands, or the deviation loses its
> conservatism. Proposed: a 4B FAIL routes to the §5 MIXED branch — the CALL-beat
> attribution holds for gemma and 35b (where the effect lives) and is explicitly
> withdrawn for 4B, with the failing cell named. It does **not** revoke the gemma
> matched-cell result, which is a different model and a far larger effect.
>
> > ANSWER:
