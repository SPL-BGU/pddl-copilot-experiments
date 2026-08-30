# nt-ster H4 prereg — decisions, provenance, and rejected alternatives

**Companion to `development/reference/ntster_h4_prereg.md`** (slots filled + amendments applied
2026-07-25, accepted by Omer). This is the evidence trail: a 34-agent workflow —
8 grounded investigations × 3 adversarial lenses (statistical validity /
apparatus-and-corpus identity / operational feasibility) + synthesis + a completeness
critic — run read-only against canonical corpora only (`results/sweep5v2-live`,
`results/sweep6-live`; `results/iss024d-e2e-live` and `results/decoupled-rollup` as
apparatus evidence, never pooled; the stale `sweep5-cluster-20260530` mirror never
opened). Every research recommendation was refuted at least once, one fatally.

**Two things the prereg text does not record, kept here:**

1. **The slot-3 reversal.** An earlier recommendation replaced the pooled primary with
   an unweighted 4-task-mean. That was **refuted fatally**: it rests on "tasks use
   disjoint fixtures so per-task deltas are independent", and all five tasks in fact
   share the same 20 domains and the same 100 `(domain, problem)` pairs. The pooled
   primary is retained with a paired domain-clustered CI instead.
2. **A dropped argument.** The "decisive" case for `think=on` — that the paper's solve
   robust floor (+46-71pp) is set by the `think=on` realizable benefit — was demoted:
   it protects a threshold claim with 16-41pp of buffer that no ±5pp-scale effect can
   reclassify. The both-modes answer stands on the 07-12 e2e link and the May prereg
   scope, not on that argument.

Also note: the checkpoint dirs (`checkpoints/e2e-overlay`, `checkpoints/iss024d-e2e-live`)
were checked separately on 2026-07-25 after Omer asked — they are byte-identical
(MD5-matched) zip mirrors of data already under `results/`, and contain zero no-tools
steered rows, so the "this run has never happened" premise survives a wider net than
the original `results/**` scan.

---

# nt-ster H4 prereg — definitive slot-filling recommendation set

**Date:** 2026-07-25. **Target:** `development/reference/ntster_h4_prereg.md` (DRAFT, 4 ANSWER slots + 2 RATIFY lines).
**Inputs:** 8 parallel investigations × 3 adversarial verifiers each. **Adjudication basis:** every
load-bearing fact below was re-verified locally in this session against `results/sweep5v2-live`,
`results/iss024d-e2e-live`, `results/decoupled-rollup`, and the code; verifier claims I could not
reproduce are marked as such in §8.

---

## 1. Bottom line

All four slots can be filled, and the two big directional answers survive verification unanimously:
**both think modes** (all three verifiers confirmed; off-only would strike the 07-12 steered-WT e2e
link permanently because iss024d is 100% `think=on`, which I re-confirmed on disk) and
**within-anchor paraphrase pairs, not gemma-as-control** (unanimous; gemma is a test unit here and no
model is a null-manipulation control for a prompt-text insertion). But the document as drafted would
buy a run whose primary endpoint is partly ungradeable and whose decision rule fires FAIL on noise.
Three corrections are non-negotiable and all three are grounded in code I read this session:
(i) **drop `--reasoning-parser none` for the no-tools cells** — no-tools `simulate` grading requires
the *entire* output to be one JSON value with no free-text fallback (`pddl_eval/scoring.py:585-596`),
`solve`'s structured path requires whole-string JSON (`:275-288`), and `_THINK_BLOCK_RE` needs both
tags while parser-off emits only `</think>` (0 `<think>` / 6,387 `</think>` in iss024d 9B), so
parser-off routes raw reasoning into the graded text and re-manufactures the exact `format_parse_fail`
artifact that commit `0280a7f` fixed; (ii) **fix the estimator** — the claim that per-task deltas are
independent because tasks use disjoint fixtures is false (all five tasks draw the same 20 domains and
the same 100 `(domain, problem)` pairs), and unpaired domain-clustered SE on `validate_plan` runs
2.0-3.6× the binomial value; (iii) **restrict the FAIL veto to eligible task cells** — within-anchor
paraphrase spread on `solve` is 6.0-30.0pp in all six cells, so the drafted "any task cell's CI
entirely outside ±5pp → FAIL" clause is a near-certain false-FAIL machine that would rewrite the CALL
beat on data containing no directive. Budget must also be restated: ~186 GPU-h for both modes, not
~92 (the memo's figure prices `think=on` as if it cost what `think=off` costs), and the wrapper's
`--no-tools` `--time` default is **12h**, not 72h. Nothing here changes what D-J5 decided to run;
one item (the parser flag) deviates from a D-J5-*named* element and needs Omer's initials, not a
re-decision.

---

## 2. The four ANSWER slots

| # | Slot (§) | Recommended fill | Confidence | What killed the alternative |
|---|---|---|---|---|
| 1 | **Think-mode scope** (§2) | **Both modes, off AND on.** Budget restated ~186 GPU-h (not ~92); 6 array tasks (not 3 jobs); `--time 5-00:00:00` mandatory. `think=on` cells carry a pre-declared low-base-rate companion. | **High** on direction, **medium** on value of the `think=on` half | Off-only permanently strikes the 07-12 steered-WT e2e family: iss024d is 5 cells × 9,120 rows, **100% `with_tools=True`, meta `think=on`** (verified), and its steered block is already stamped DIAGNOSTIC-ONLY. May prereg scoped H4 over "think modes (2)". `main.tex:387` already promises the arm per (model, **mode**, task). The researcher's "decisive" solve-robust-floor argument is **dropped** — it protects a +30pp threshold claim with 16-41pp of buffer that no ±5pp-scale effect can reclassify. |
| 2 | **Noise-floor control** (§3) | **(a) within-anchor paraphrase pairs**, with F demoted to a bank-validity check at pooled granularity AND recomputed as an eligibility gate at every granularity a verdict is read. **(b) gemma-as-control is killed, not preserved as an alternative.** | **High** | (b) is a false analogy: in iss024d gemma was a *null-manipulation* control because `--reasoning-parser none` was inert for it by construction (`lib/defaults.sh:84-103`, verified: gemma is natively `REASONING_PARSER=none`). H4's manipulation is one prompt sentence applied identically to every model, so no model is inert. gemma is also a test unit (the paper-level rule needs all 6 cells) and it owns the +72pp. |
| 3 | **TOST primary granularity** (§3) | **Pooled model × mode stays primary** (as drafted), but with a paired, domain-clustered CI; unweighted mean over *eligible* task cells as the composition companion; per-task cells pre-classified ELIGIBLE / LOW-BASE-RATE / DEGENERATE / UNINFORMATIVE, and **only ELIGIBLE cells can trigger FAIL**. | **High** on the estimator and the veto fix; **medium** on the eligibility thresholds | The researcher's 4-task-mean substitution rests on "tasks use disjoint fixtures so per-task deltas are independent" — **verified FALSE** (solve ∩ validate_plan ∩ simulate = the same 100 `(domain, problem)` pairs; validate_domain 120 and validate_problem 200 are supersets containing all 100; all five tasks share the same 20 domains). Its headline half-widths (1.88/2.08/0.86/1.90/2.37/2.03pp) were computed under nominal-*n* independence. Measured paired + domain-clustered pooled half-width is **1.09-2.09pp** in all six cells, so pooled ±5pp is adequately powered and needs no substitution. Its 7-cell "claim-matched family" is also precision-selected, which fills it with floor cells (4 of 7 are gemma/on, one at 0/120). |
| 4 | **Llama kill-gate** (§6) | **Direction confirmed (`<` → stop). 0.95 rejected. Replace with a parser-mismatch *signature* gate, not a rate gate**, plus a pooled zero-call belt and a pooled zero-extraction belt. Gate on a prefix of the real run, not on `--smoke`. | **High** | 0.95 is 19/20 validate_plan calls from a v0-era smoke (`CHANGELOG.md:1314`, commit `59be812` where `ACTIVE_PROMPT_VARIANTS=(0,1,2)`), and a pooled ≥0.95 bar rejects 6 of 10 published with-tools configurations on v11 — including gemma, the model that same 0.95 certified. The researcher's replacement (max over 5 tasks × {v11,v14} ToolSel < 0.50) was refuted by all three verifiers: at smoke sub-cell *n* (1/2/6/10/1) it fires with ~92% probability at true ToolSel 1%, i.e. it kills on low adherence — the exact defect it indicts 0.95 for. A rate cannot separate a dead parser from a non-calling model; the stored-row signature can. |

---

## 3. Paste-ready ANSWER prose

### Slot 1 — §2 think-mode scope

> ANSWER (2026-07-25): **CONFIRMED — both modes, `think=off` AND `think=on`.** Off-only is a claim
> reduction, not a scope reduction: it strikes the 07-12 pre-commitment's steered-WT e2e family
> permanently, because the only exact steered-WT e2e corpus is `results/iss024d-e2e-live` and it is
> 5 cells × 9,120 rows with `with_tools=True` on 100% of rows and meta `think="on"` (verified on
> disk; its steered block is already stamped DIAGNOSTIC-ONLY in
> `results/derived/e2e_overlay/pooled_e2e_table.md:115`). It would also narrow the May
> pre-registration, which sized H4 over "think modes (2)"
> (`development/reference/sweep_prompt_bank_design.md:48`), from authors whose C1 is pre-registration
> discipline, and `paper/main.tex:387` already asserts the fourth control arm per (model, **mode**,
> task) with zero rows on disk.
>
> **Budget and topology corrected (supersedes the memo's "~92 GPU-h, 3 parallel jobs, <4 days").**
> Both arms × both modes × 3 models is **~186 GPU-h**, not ~92; off-only is ~46. The memo's 92 priced
> `think=on` as if it cost what `think=off` costs, but the measured per-trial ratio in the canonical
> no-tools cells is 2.0-4.8× (9B 3.09×, gemma 4.84×, 35b 1.96×; summed trial-hours 91.0 off vs 280.6
> on), because 78-92% of `think=on` trials run to the per-task `num_predict` cap. The correct multiple
> for the decision is **~4.1× off-only**, not 2×. `submit_with_rtx.sh` fans out one array task per
> (model, think, cond) at `rtx_6000:1 / --mem=48G` with `--time` applied **per task**, and
> `--include-no-tools-steered` puts BOTH arms in the SAME cell (9,120 trials, one vLLM instance —
> a stronger co-run guarantee than "same submit"). So this is **6 parallel single-GPU array tasks**,
> not 3 jobs × 4 cells. Reconstructed per-task wall at `CONCURRENCY=4`: 9B/on ~78h, gemma/on ~38h,
> 35b/on ~24h, 9B/off ~25h, 35b/off ~12h, gemma/off ~8h (add ≤30% for node-speed spread). Wall
> ≈3.5-4.2 days set by 9B/on, queue wait excluded.
>
> **`--time` is mandatory: the wrapper's `--no-tools` default is 12:00:00, not 72h**
> (`cluster-experimenting/submit_with_rtx.sh:445-446`; 72h is the tools branch). 12h would TIMEOUT
> every cell here, and TimeLimit increases are admin-denied. Pass `--time 5-00:00:00` (partition cap
> is 7 days; SLURM bills usage, not the ask). Name the three models explicitly and never pass
> `--all` — the auto-prioritize gate would set `Nice=500` on exactly the 9B cells, the longest tasks
> in this regime (`submit_with_rtx.sh:669-689`; `lib/defaults.sh:19` omits 9B from
> `PDDL_SLOW_MODELS`). Do not use `submit_full_sweep.sh` (it refuses `--time`).
>
> **Pre-declared, so it is not discovered later:** the `think=on` half is the weaker half. Anchor-arm
> pooled success in the canonical `think=on` no-tools cells is 74.3% (35b), 18.4% (9B), 7.6% (gemma),
> with 14.3 / 77.6 / 91.8% cap-truncation. 35b is a fully informative `think=on` subject; 9B is
> informative on `validate_plan` (anchor 21.7%); gemma/on is largely at the floor and its
> `validate_domain` and `simulate` anchors are exactly 0.0%. Those cells are governed by the
> low-base-rate and degenerate-cell rules in §3, not excluded, and a `think=on` PASS at a <15% anchor
> licenses only the absolute ±5pp statement.

### Slot 2 — §3 noise-floor control

> ANSWER (2026-07-25): **(a), amended. (b) is KILLED, not retained as an alternative.** In iss024d
> gemma was a *null-manipulation* control: the one generative delta there (`--reasoning-parser none`)
> was inert for gemma by construction, because gemma is natively `REASONING_PARSER="none"`
> (`cluster-experimenting/lib/defaults.sh:84-103`, verified), so a gemma parity failure could only be
> serving nondeterminism (`development/iss024d_parity_prereg.md:16-19`, expected 5/5 PASS at :39).
> H4's manipulation is one appended prompt sentence applied identically to every model, so **no model
> is inert by construction and none can play that role.** gemma is also a test unit here (the
> paper-level rule needs all six model × mode cells) and it is the model that owns the +72pp, so
> demoting it would gut the attribution and shrink the roster to two.
>
> **F, restated.** F = max |Δ̂| over the three within-anchor paraphrase pairs (v11-v12, v11-v13,
> v12-v13). Computed at **pooled** granularity it is a *bank-validity* check, not the operative noise
> of the contrast: with equal *n* per variant on both arms the pooled Δ is exactly
> (1/3)Σ[p(v+3) − p(v)], so the paraphrase MAIN effect cancels arithmetically and F measures what the
> design already removes. Measured on `results/sweep5v2-live` no-tools: 9B off 1.45 / on 1.32, gemma
> off 2.17 / on 0.99, 35b off 1.64 / on 3.03pp — all < 5pp, so the ±5pp margin survives at the
> confirmatory granularity and the "F ≥ 5pp ⇒ UNINFORMATIVE, never rescued" clause is retained (it
> will not fire).
>
> **F is ALSO computed at every granularity where a verdict is read, and there it is a gate.** At
> task granularity the same designed-equivalent paraphrase pairs move `solve` by **6.0-30.0pp in all
> six cells** (9B off 28.0, 9B on 15.0, gemma off 15.0, gemma on 6.0, 35b off 28.0, 35b on 30.0) and
> `validate_domain` by 0.0-12.5pp (>5pp in 3 of 6). Mechanism, from `failure_reason`: at `think=off`
> `solve`, v11/v13 hit `format_parse_fail` 77-91% while v12 hits 13-54% — a prompt-form ×
> JSON-extraction interaction, not sampling noise, and not reducible by *n*. Pre-registered
> consequence: **a model × mode × task cell whose own F ≥ the margin is UNINFORMATIVE and cannot
> contribute a FAIL.** Without this the §3 rule is a false-FAIL machine.
>
> **§1 motivation corrected.** Do not cite "the 5.3pp cross-apparatus noise floor" as a measured
> drift constant. `results/derived/iss024d_parity_report.md` records **JOB-LEVEL PARITY: FAILS**
> (Qwen 7/20 cells equivalent, max |Δ| = 11.3pp, confounded with the parser-off delta) while the
> zero-delta gemma control produced 1/5 TOST PASS with max |Δ̂| = 5.3pp and **every gemma CI
> containing zero** (solve −5.3, 90% CI [−10.7, +0.1]) — i.e. the gemma cells were underpowered, not
> drifted, and in `tools/iss024d_parity.py:186-188` F only ever appended "(≤ control noise floor)" to
> a FAIL label; it never gated. Write it as: *the prior cross-apparatus check failed at job level
> (max |Δ| = 11.3pp), while the zero-delta control showed no drift beyond sampling error* — and
> justify the co-run anchor on design grounds, which are stronger: with
> `--include-no-tools-steered` both arms land in ONE 9,120-row cell file, interleaved by one process
> against one vLLM server, so config/vintage drift is zero by construction. Run-to-run serving
> nondeterminism remains and is not bounded by our corpora (decoding is greedy and unseeded —
> `pddl_eval/chat.py:28` `TEMPERATURE = 0.0`, no `seed` field anywhere in `pddl_eval`; duplicate keys
> = 0 in every roster cell, so no prompt was ever measured twice under one apparatus). Registered as
> a stated limitation, not a number.

### Slot 3 — §3 TOST primary granularity

> ANSWER (2026-07-25): **Pooled model × mode stays the primary**, with three corrections to how it is
> estimated and one to what can veto it.
>
> **1. Estimator: paired and domain-clustered, not independent-samples Newcombe.** The arms are
> item-matched by construction — v11/v12/v13 cover byte-identical `(task, domain, problem,
> plan_label)` sets and v14-16 are v11-13 plus one appended sentence, so nt-ster vs nt-neut is 4,560
> matched pairs. And the tasks are **not** independent: all five draw the same 20 domains and the same
> 100 `(domain, problem)` pairs (solve ∩ validate_plan ∩ simulate = 100/100; validate_domain 120 and
> validate_problem 200 are supersets containing all 100), with `validate_plan`'s 1,000 rows/variant
> being 100 problems × 10 plan labels. Primary CI = 90% interval on the per-domain mean of the
> per-fixture paired difference, clustered on **domain** (k = 20, t₁₉), with a domain-clustered
> bootstrap (B = 10,000) as the reported equivalent and unpaired Newcombe as the conservative
> companion. Measured on the anchor's own designed-null paraphrase contrast, the pooled paired
> domain-clustered half-width is **1.09-2.09pp** across the six cells (unpaired Newcombe 1.59-2.87pp;
> unpaired one-arm SE inflation from domain clustering on `validate_plan` alone is **2.0-3.6×**
> binomial). So ±5pp is powered at pooled granularity in all six cells with ~2.4-4.6× headroom, and
> the conjunction over 6 units has ~87% power at Δ = 0 — stated here rather than assumed.
>
> **2. Composition is named, not fixed by substitution.** `validate_plan` is 3,000/4,560 = 65.8% of a
> pooled cell, and on a real contrast the pooled number is close to one task (for gemma/off with-tools
> steering, pooled Δ = +47.4pp vs unweighted 5-task mean +14.3pp, with `validate_plan` supplying 100%
> of the pooled Δ). The companion is therefore the **unweighted mean over ELIGIBLE task cells**
> (below), reported alongside the pooled figure. A pooled PASS whose eligible-task-mean disagrees is
> reported as a disagreement, not resolved.
>
> **3. Per-task cells are pre-classified from the ANCHOR before the contrast is read**, into exactly
> one of: **ELIGIBLE** (anchor rate in [10%, 90%] AND own-granularity F < 5pp AND realized paired
> domain-clustered half-width ≤ 5pp); **LOW-BASE-RATE** (anchor < 10%: reported with the absolute CI
> *and* a relative risk-ratio bound, because ±5pp absolute at a 7.6% anchor admits a 1.66× relative
> move); **DEGENERATE** (anchor exactly 0% or 100%: reported as a one-sided bound only, since 0-vs-0
> equivalence is vacuous); **UNINFORMATIVE** (fails the F or half-width test). Indicative
> classification from the anchor corpus, so the shape is known now: `validate_plan` ELIGIBLE in all
> six cells (paired domain-clustered half-width 1.28-3.07pp); `validate_problem` ELIGIBLE in 3 of 6;
> `validate_domain` UNINFORMATIVE in 3 of 6 (half-width 9.4-13.4pp); `solve` UNINFORMATIVE in all six
> (F 6.0-30.0pp, half-width 4.8-12.9pp); `simulate` to be classified on the July anchor, **not**
> pre-declared degenerate (see §5 amendment A5).
>
> **4. The FAIL veto is restricted to ELIGIBLE cells.** Revised rule: **PASS** iff the pooled CI
> ⊂ (−5, +5) AND no ELIGIBLE task cell's CI lies entirely outside (−5, +5); **FAIL** if the pooled CI
> lies entirely outside OR any ELIGIBLE task cell's CI does; INCONCLUSIVE otherwise. LOW-BASE-RATE,
> DEGENERATE and UNINFORMATIVE cells are reported in full and carry no verdict authority. Rationale:
> under the drafted rule, 9 of 90 designed-null within-anchor paraphrase contrasts (in 5 of 6 cells)
> already have 90% CIs lying entirely outside (−5, +5) with **no directive present**, and §5 would
> convert that into "H4 failed → the CALL beat is a prompt-content effect". Multiplicity posture:
> intersection-union, so the conjunctive equivalence claim needs no α correction and none is applied;
> the affirmative non-equivalence claim gets Holm across the ELIGIBLE family only. Family membership
> is frozen by the pre-registered rule, never re-picked after seeing Δ̂ — a realized half-width
> overrun yields UNINFORMATIVE for that cell, it does not shrink the conjunction.

### Slot 4 — §6 Llama kill-gate

> ANSWER (2026-07-25): **Direction CONFIRMED (`<` threshold → stop; the memo's sentence is a dropped
> negation — `lib/defaults.sh:93` states ≥0.95 as the criterion to PROCEED). Threshold 0.95 REJECTED.
> The gate is replaced by a signature test, not a rate test.**
>
> **Why 0.95 dies.** It is 19/20 validate_plan calls in the 2026-05-18 gemma smoke
> (`development/CHANGELOG.md:1314`), measured at commit `59be812` where `ACTIVE_PROMPT_VARIANTS =
> (0,1,2)` and the with-tools system prompt was the maximal steer ("Your ONLY way to get information
> … never guess"); the v11-16 bank landed eight days later. 95% Wilson for 19/20 is [0.764, 0.991] —
> it turns on one trial. And on the arms this probe actually runs, a pooled ≥0.95 bar rejects **6 of
> the 10** published model × mode with-tools configurations on v11 and 2 of 10 on v14, including
> gemma4-26b, whose parser that same 0.95 certified; 30 of 100 task-level sub-cells sit below 0.95,
> floor gemma/on/v11/validate_plan at 1.4%. External prior points the same way (LiveMCP-101 puts
> Llama-3.1-8B at 1.0%), so 0.95 would fire precisely when the probe is delivering its signal.
>
> **Why a replacement rate threshold also dies.** A `--tool-call-parser` mismatch produces uniform 0%
> with no startup error (`cluster-experimenting/README.md:319-322`), and a genuinely non-calling model
> produces the same 0%. No function of the tool-call rate can separate them. At smoke sub-cell *n*
> (1 solve / 2 vdom / 6 vprob / 10 vplan / 1 sim per arm) a "max over tasks × arms < 0.50" rule fires
> with ~92% probability at a true rate of 1% and ~66% at 5% — a low-adherence detector wearing a
> plumbing-detector label.
>
> **The gate (evaluated on tools rows, `think` as submitted).**
> - **G0 precondition.** Row count equals the enumerated total, and `failure_reason == "exception"`
>   share ≈ 0. `APIConnectionError`/abort rows are dropped from `trials.jsonl` entirely
>   (`pddl_eval/runner.py:424-441`), so a wedged server silently shrinks *n* rather than showing
>   zeros; a chat-template 400 (e.g. `enable_thinking` on a template that does not define it) writes
>   `failure_reason=exception` with `tool_selected=None`, which would fire any rate gate. Failing G0
>   is a config error: fix and rerun, it consumes no retry and licenses no Llama statement.
> - **G1 PRIMARY — parser-mismatch signature (automated, n-free).** For every tools row with
>   `tool_calls == []`, classify the stored `response` for tool-call syntax (`<tool_call`, `<function`,
>   `<|python_tag|>`, or a JSON object carrying both `"name"` and `"arguments"`/`"parameters"` naming a
>   plugin tool). **≥1 syntax-present-but-unparsed row ⇒ PARSER MISMATCH ⇒ re-serve.** 0 such rows ⇒
>   the observed rate is the model's behaviour ⇒ **PROCEED regardless of its value.** Run it on the
>   multi-argument tasks too, to catch a parser that handles single-arg calls but mangles multi-arg
>   ones (the known FastMCP arg-error signature). This replaces the drafted "eyeball 5 `tool_calls`
>   payloads", which inspects the wrong artifact — in the 0% case there are no `tool_calls` to read.
> - **G2 belt — pooled zero.** Kill only at **exactly zero parsed tool calls across all tools rows in
>   the slice**, never a max-over-sub-cells rate. A parser is variant-independent, so pooling is valid.
> - **G3 belt — pooled zero extraction.** Kill only at **zero extracted answers** over the pooled
>   no-tools v11-13 rows in the slice, where extracted := `failure_reason` ∉ {`format_parse_fail`,
>   `truncated_no_answer`, `think_overflow`, `exception`} (no `extraction` field is stored — the
>   formula is the definition). Never an unscoped "0% extraction → stop": Qwen3.5-0.8B's `think=on`
>   nt-neut extraction is 4/4,560 = 0.088%, so an unscoped rule would kill a published roster model on
>   the documented shared-budget truncation confound.
> - **Cost-asymmetry default.** Anything above G2/G3 PROCEEDS. Low measured ToolSel is this probe's
>   payload, per the standing rule that tool-use failures are data.
>
> **Retry policy.** Re-serves are triggered ONLY by the G1 signature, and change ONLY vLLM serve
> flags (`TOOL_CALL_PARSER`, plus `MAX_NUM_BATCHED_TOKENS`/`GPU_MEM_UTIL` if startup-bound);
> candidate order `llama3_json` → `pythonic` → `hermes`. Never a prompt, fixture, system-prompt or
> scaffold change. A server that refuses to start on an unregistered parser name is a config error,
> not a gate evaluation, and consumes no retry. **Do not select a parser by whichever slice maximises
> ToolSel** — at n=40 with a true 30%, E[max of 3] ≈ 36% and the interval has no post-selection
> coverage; any ToolSel that is *reported* comes from the full cell, never from the selection slice.
>
> **Where it is evaluated (operational, corrected).** Stock `--smoke` cannot evaluate any v14 gate: it
> forces `--num-variants 1` (`run_experiment.py:762-764`) and `ACTIVE_PROMPT_VARIANTS[:1] = (11,)`.
> And `--num-variants` / `--domains` / `--problems` are **not plumbed** through
> `submit_with_rtx.sh` or the sbatch's `run_experiment.py` invocation (verified: it passes only
> marketplace / models / base-url / concurrency / think / cond / tasks / shard / continue / partial /
> steered / domains-dir / decoupled / output-dir), so the "explicit 180-trial slice" is not
> submittable as written. Therefore: **gate on a prefix of the real Llama submit** — submit with an
> explicit `--time`, sync at ~T+60-90 min, evaluate G0-G3 on the rows that have landed, `scancel` on a
> fire. The variant loop is innermost, so v11 and v14 tools rows land in the first fixtures. Adding a
> `--variants 11,14` pass-through instead is a code change and needs a branch + PR (§6).
>
> **Kill-branch language.** Never "tool invocation was not measurable". Report the bound: "0 of N tool
> calls parsed, Wilson 95% upper X%", plus the G1 verdict that no unparsed tool-call syntax was
> present. One sentence appended to the family-confound Limitations sentence
> (`paper/main.tex:987-989`); **no row in `tab:decomp`** (its rows are n=1,520-per-cell arm-pooled
> decompositions). A kill licenses no comparative claim about Llama vs Qwen — forbid that on
> apparatus-vintage grounds (a new July vintage against May sweep5v2), not on precision grounds.

---

## 4. The two RATIFY lines — what signing commits to, and the residual risk

### RATIFY 1 — nt-ster + anchor design and analysis

**Commits to:** ~186 GPU-h (~4.1× the off-only alternative) across 6 `rtx_6000:1` array tasks, 54,720
trials in 6 cell dirs of 9,120 rows each, ~3.5-4.2 days of compute plus queue, in one ping-gated VPN
window with a `--time 5-00:00:00` ask; a paired domain-clustered TOST at ±5pp whose PASS licenses the
§5 attribution sentence and whose FAIL rewrites the CALL beat; an anchor walled to exactly two uses;
and — with the §5 amendments — a no-tools apparatus that is **not** literally iss024d's (the
`--reasoning-parser` element is dropped at `think=on`; everything else in the pin is kept).

**Residual risk being accepted:**
1. **The `think=on` half may return UNINFORMATIVE for 9B and gemma.** It is ~140 of the ~186 GPU-h. At
   the plain apparatus the anchor sits at 18.4% (9B) and 7.6% (gemma) with 78-92% cap truncation;
   gemma/on `validate_domain` and `simulate` anchors are exactly 0.0%. If those cells land
   LOW-BASE-RATE or DEGENERATE, the 07-12 steered-WT e2e link is licensed only through 35b/on — which
   *is* fully informative (anchor 74.3%, truncation 14.3%) and *is* in the iss024d roster, so the buy
   is not worthless, but it is one model rather than three.
2. **Cross-apparatus transfer to the May +72pp is not purchased.** H4 becomes internally valid within
   July; the step from there to the May sweep5v2 number remains a drift argument, and job-level parity
   between the July and May apparatuses already FAILED (Qwen 7/20, max |Δ| 11.3pp). §4's
   "replicated attribution, never controlled by the July cells" is doing real work and must stay.
3. **A `--time` miss is a lost VPN window.** TimeLimit increases are admin-denied; resume from
   `trials.jsonl` works but costs another ping.
4. **The control is conservative by construction.** The nt-ster prompt is self-contradictory — the
   system prompt says "PDDL validation tools are not available in this evaluation" while the user text
   says "Use the validate_domain tool" (both verified) — which biases H4 toward PASS. §5 amendment A7
   pre-registers this as a stated limit on the control's power.
5. **Simulate's classification is genuinely open** (see §8).

### RATIFY 2 — Llama probe spec + kill-gate

**Commits to:** a second submit *after* nt-ster, at ~13,680 trials / ~30-36h (not the drafted 4,560 /
10-12h — the standard path emits all 6 variants for tools and 3 for no-tools, and no flag can select
`{v11, v14}`); a kill-gate that stops only on a parser-mismatch signature or a pooled zero, so a
genuinely low-adherence Llama **proceeds to the full cell**; and a Limitations-sentence-only
integration cap.

**Residual risk being accepted:**
1. **Two code changes gate the submit** (§6): a `vllm_lookup` case for Llama and, if the arm spec is
   to be honoured literally, a `--variants` pass-through. Both need a branch + PR. Without the first,
   `submit_with_rtx.sh:341-343` aborts before sbatch.
2. **`llama3_json` registration in the pinned vLLM v0.20.2 is unverified** and not verifiable locally.
3. **The probe bounds but does not resolve the family confound.** One 8B point from a third family;
   no comparative claim is licensed against the Qwen roster across the vintage boundary.
4. **`enable_thinking` behaviour on Llama-3.1's template is untested here** (`vllm_client.py:161-162`
   passes it as a `chat_template_kwargs` only when think is not None). G0 catches it as an exception
   storm rather than a finding.

---

## 5. REQUIRED prereg amendments beyond the slots

### A1 — §2: drop `--reasoning-parser none` for the no-tools cells (**highest priority**)

> **Apparatus pin, amended.** Everything in iss024d's config is kept — same `vllm.sif` tag
> (`docker://vllm/vllm-openai:v0.20.2`, asserted and then verified from the served log header, since
> `$HOME/vllm.sif` is a mutable shared cache), same sbatch wrapper, 16K response snapshots, 16K ctx,
> marketplace/plugins at `5e4f9c0` — **except the reasoning-parser override, which is NOT passed.**
> Each model uses its verified per-model default (`qwen3` for the Qwens, `none` for gemma, which has
> no `<think>` tokens). At `think=off` this is a no-op (0 of 4,560 rows carry any `thinking` in every
> canonical `think=off` no-tools cell, and 0 have an empty response). At `think=on` it is the
> difference between a measurable and an unmeasurable primary endpoint, for three independent reasons:
> (i) no-tools `simulate` grading requires the ENTIRE output to be one JSON value with **no free-text
> fallback** (`pddl_eval/scoring.py:585-596`), so a reasoning prefix guarantees `FR_FORMAT_PARSE_FAIL`
> and re-manufactures exactly the artifact commit `0280a7f` (2026-06-25) fixed; (ii) no-tools `solve`'s
> structured path requires whole-string JSON after fence-stripping (`scoring.py:275-288`), so it dies
> and the strict `extract_plan_lines` fallback harvests action-shaped lines out of the reasoning;
> (iii) `_THINK_BLOCK_RE` requires BOTH tags (`scoring.py:109`) while a parser-off Qwen emits only the
> closer (iss024d 9B: 0 rows contain `<think>`, 6,387/9,120 contain `</think>`, `thinking` empty in
> 45,600/45,600 rows), so nothing is stripped and `extract_verdict` reads the monologue. None of this
> is repairable by the overlay: for no-tools rows outside `simulate`, the overlay passes the stored
> online grade straight through (`tools/e2e_regrade.py:373-379`, `e2e_reason="stored_online_grade"`),
> so the delivered surface IS that grade.
>
> Parser-off also does not buy what the pin claims. gemma is the natural experiment: it has always run
> `REASONING_PARSER=none`, so its canonical `think=on` no-tools cell already IS a single-call
> parser-off no-tools exhibit — responses are non-empty raw reasoning ("thought\n* Goal: …"), 0 contain
> `<think>`, and it still shows 91.8% `done_reason=length` and 7.6% success. The `think=on` loss
> channel is the shared decode budget, not the parser.
>
> **Cost of this amendment, stated:** the §4b factorial acquires a parser difference across its nt/wt
> axis (July nt cells parser-on for the Qwens vs iss024d wt cells parser-off). That comparison is
> already declared attribution-only and is structurally budget-unmatchable — `chat_with_tools` re-grants
> the per-task decode budget on every turn up to `MAX_TOOL_LOOPS = 10` (`pddl_eval/chat.py:29`) while a
> no-tools trial gets one shared budget. Adding a parser difference to an already-unmatchable
> diagnostic is strictly cheaper than corrupting the nt legs' grading on two of five tasks.

*Justification:* implementing the pin literally would make `simulate` ~0% by construction and
contaminate `solve` extraction on the primary surface, which is the one thing a control cannot afford.

### A2 — §2: delete "makes every row exactly e2e-gradeable"; keep the 16,384 snapshot

> **Snapshot.** `RESPONSE_SNAPSHOT_LEN = 16384` is a non-overridable code constant
> (`pddl_eval/runner.py:145-153`, "Override is intentionally not exposed"), so it comes free on current
> code and is not a per-run choice. It does **not** make every row exactly gradeable: iss024d itself
> pins 1.0-27.6% of rows per cell at the cap (9B 848/9,120; gemma 2,520/9,120 = 27.6%), and only 2 of
> its 25 steered e2e cells are exact. For no-tools cells the exposure is narrow and known: the online
> grade ran on the FULL response before storage truncation (`runner.py` truncates at record
> construction), and the overlay passes it through for every task except `simulate`
> (`tools/e2e_regrade.py:373-379`; measured 4,260/4,560 rows `stored_online_grade` per canonical
> no-tools cell), so **`solve` and `validate_*` are censoring-immune and `simulate` (300/4,560 = 6.6%)
> is the only censored task.** Censored `simulate` cells are reported as bounds and never fed to the
> TOST. Do **not** raise the snapshot: it has no override, a raise would be a source edit that makes
> the "frozen at `6007032`" pin nominal, and `tools/e2e_regrade.py`'s `KNOWN_CAPS = (500, 16384)` plus
> `detect_cap` would then return `None`, disabling every censor branch and grading genuinely truncated
> rows as determinate FAILs — bias toward exactly the FAIL the control exists to exclude.

*Justification:* the drafted sentence is falsified by iss024d's own censoring, and the "raise the cap"
fix all three verifiers rejected would corrupt grading in the FAIL direction.

### A3 — §2: correct the topology, `--time`, budget, and the run-tag line

> **Submit shape.** One submit, models named explicitly, never `--all`, never `submit_full_sweep.sh`:
> `bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b --no-tools
> --include-no-tools-steered --think-modes "on off" --run-tag ntster-h4 --time 5-00:00:00`
> → 6 array tasks (model × think), each a 9,120-row cell holding both arms. Verify `TimeLimit`
> immediately after submit. A TIMEOUT is recoverable (resubmit resumes from `OUT_DIR/trials.jsonl`)
> but costs a queue cycle and another ping. Optionally split by mode so the off cells take a shorter
> ask for queue reasons.
>
> **Run-tag.** Cells land at `results/slurm_vllm_{Qwen3_5_9B,gemma4_26b-a4b,qwen3_6_35b}_{on,off}_no-tools_ntster-h4`
> (`run_condition_vllm_rtx.sbatch:373`); sync to an explicit new dest
> (`sync.sh results/ntster-h4-live`; the script refuses a bare `results/`). **The "run-tag breaks the
> analyzer cell-parser" lesson is STALE for the table/e2e path** — the parsers were fixed 2026-07-12,
> return `run_tag`, and default to untagged-only, so tagged corpora cannot silently pool; the
> supported read is `table.py results/ntster-h4-live --run-tag ntster-h4 --e2e`. The strip step
> applies only to `build_deck.py` / `plot.py`. **HARD RULE: never strip inside
> `results/sweep5v2-live`** — its cell dirs are untagged, so a stripped ntster dir name would be
> byte-identical and would overwrite canonical cells irreversibly.

*Justification:* the drafted `--time` figure ("72h wrapper default") is wrong for a `--no-tools`
submit (default is 12h), the topology is wrong (6 array tasks, not 3 jobs × 4 cells), and the stale
run-tag warning would send an operator into the one operation that can destroy the canonical corpus.

### A4 — §3: name the surface honestly and pre-commit the two grading commands

> **Surfaces.** Primary = delivered. For no-tools rows this is the stored online grade passed through
> by the overlay for `solve` and `validate_*` (`tools/e2e_regrade.py:373-379`; 4,260/4,560 rows per
> cell), so on 93.4% of rows the delivered and legacy surfaces are the **same number** and the
> "legacy as a consistency check" line is a tautology there — it is a real second measurement only on
> `simulate`. Post-run, exactly two commands: `python3 tools/e2e_regrade.py results/ntster-h4-live
> --no-mcp` (oracle cache `results/derived/gt_cache.json` already on disk; no live MCP needed because
> non-simulate no-tools rows pass through), then `python3
> .claude/skills/analyzer/scripts/table.py results/ntster-h4-live --run-tag ntster-h4 --e2e`. Assert
> `snapshot_cap == 16384` on every new cell before interpreting anything (`detect_cap` has no CLI
> override and returns 500 for any cell whose max response length is ≤500).

*Justification:* prevents a later "we should have run the overlay differently" and removes a promised
consistency check that does not exist.

### A5 — §3: do NOT pre-declare `simulate` degenerate; exclude it from the drift measurement

> **`simulate`.** The canonical anchor shows 0.0% success on no-tools `simulate` in all six cells, but
> that is a **retired-grader artifact, not a capability floor**: the failure mass is
> `format_parse_fail` (58-216 of 300 per cell), which is exactly the strict-wrapper behaviour that
> commit `0280a7f` (2026-06-25) replaced with the wrapper-tolerant Q1 grader, and under the current
> grader the 16K no-tools corpus reads 22.3% (9B) and 40.0% (35b). July `simulate` is therefore
> expected to be non-zero and its H4 contrast is live; it is classified from the **July** anchor under
> the §3 rule, never pre-declared degenerate. Corollary: the anchor-vs-May drift datapoint (§4) is
> reported for `solve` / `validate_domain` / `validate_problem` / `validate_plan` only — `simulate`
> drift is grader-confounded and **unmeasurable**, because May `simulate` responses are stored at 500
> chars and cannot be re-graded.

*Justification:* pre-declaring the one task most likely to move as degenerate would discard live signal
and would publish a grader delta as apparatus drift.

### A6 — §4b: gemma HAS iss024d with-tools cells (factual correction)

> **(b)** … models = all three roster models. `results/iss024d-e2e-live/slurm_vllm_gemma4_26b-a4b_on_tools_all_minimal_iss024d-e2e`
> holds 9,120 rows with v11-16 at 1,520 each and `with_tools=True` on all of them (job 19314599,
> `paper_notes_discussions.md:755-757`), so gemma is fully eligible for the factorial — and it is the
> model that owns the +72pp. 0.8B/4B still sit out for lack of July nt cells. At `think=on` the
> anchor-vs-May delta for the Qwens must be labelled a reasoning-parser **configuration** difference,
> not drift; gemma is the only roster model whose delta is a clean vintage measurement.

*Justification:* the drafted sentence is false on disk (verified directly) and would drop the model the
whole control exists to defend.

### A7 — §3/§5: pre-register the self-contradictory control prompt

> **Control conservatism (pre-registered).** Under `with_tools=False` the system prompt is always
> `WITHOUT_TOOLS_SYSTEM_BY_TASK[task]` regardless of variant (`pddl_eval/runner.py:309-316`), which
> states "PDDL validation tools are not available in this evaluation. Analyze … using your own
> reasoning", while the steered v14-16 user text says "Use the validate_domain tool with the domain as
> its argument". The control therefore removes both the tool and its stated availability, which biases
> H4 toward PASS. §5's PASS sentence is scoped accordingly: *the steered directive does not move the
> no-tools floor when the prompt also states that tools are unavailable.* Fixing the contradiction
> would require a third steering construct (the parked D4(ii) reframe) and is out of scope.

*Justification:* a PASS is weaker evidence than the drafted §5 language implies; saying so before data
is free, saying it after is a concession.

### A8 — NEW §3 subsection: mechanism decomposition (secondary, descriptive, never gating)

> **Mechanism decomposition (secondary; never gates or revises the H4 verdict).** Both candidate
> mechanisms are prompt-content effects, so the decision rule is unchanged either way; only the story
> differs, and the story is locked here. Computed from fields already written per row — no new grader,
> no new run.
>
> **Partition (three-way, not two).** `truncated_no_answer` is 100% `done_reason=="length"` and
> `format_parse_fail` is 100% non-truncated (verified, 27,360 roster no-tools rows; forced by the
> write-time override at `pddl_eval/scoring.py:622-644`), so: **TRUNCATED-LOSS** = `truncated_no_answer`;
> **CHANNEL/FORMAT** = `format_parse_fail` (+ overlay `format_parse_fail` on `simulate`); **CONTENT** =
> `verdict_mismatch`, `plan_invalid`, `result_mismatch`, `simulate_empty` (+ overlay
> `trajectory_mismatch`); **APPARATUS** = `exception`, `tool_error`, `unknown`, `ollama_parse_error`,
> other (reported, excluded; >1% in either arm voids that cell's mechanism read). Overlay
> `censored_at_snapshot_cap` is reported separately and folded into neither side. The four components
> partition Δ̂ exactly (ΣΔ = −Δ̂), so this is an accounting split with CIs, **not** two independent
> measurements; do not present `Δtruncation` as corroborating `ΔTRUNCATED-LOSS` — it is the same rows.
>
> **Metrics** per model × mode × arm, pooled and per task: (M1) directive echo — share of rows whose
> `response` matches the task's tool name, `/(classic_planner|numeric_planner|validate_domain|validate_problem|validate_plan|get_state_transition)/i`
> for validate_*/simulate and `/planner tool|the planner\b/i` for solve (whose directive names no
> tool); (M2) budget — `done_reason=="length"` share, mean/median `tokens.completion`, at-cap share
> computed as `len(response) == 16384`; (M3) the partition deltas with 90% CIs on the same paired
> domain-clustered footing as §3.
>
> **M1 is reported as an ARM DIFFERENCE, never as an absolute.** Base rate in the roster neutral
> no-tools arms is 0/27,360 (verified) and the v11-13 templates contain no tool name, but that anchor
> is measured on 500-char snapshots and is therefore a specificity floor, not a guarantee; the July
> anchor arm supplies the operative base rate. M1 is a lower bound on at-cap rows, and since at-cap ≈
> truncated, M1 is anti-correlated with displacement by construction — a depressed M1 inside a
> displacement-dominated cell may never be read as "no directive echo". M1 is interpretable only
> because `guided_json` does not bind (ISS-024(b), parked); if that fix lands first, M1 is declared
> N/A rather than reinterpreted.
>
> **Label, assigned only to a cell whose H4 verdict is FAIL and only where estimable** (pooled
> granularity, |Δ̂| ≥ 9pp, and the dominant component's share CI excluding 0.5): **DISPLACEMENT** if
> TRUNCATED-LOSS dominates and mean `tokens.completion` moves with it; **REASONING SHIFT** if CONTENT
> dominates; **CHANNEL** if CHANNEL/FORMAT dominates; otherwise components reported with no label.
> Rationale for the |Δ̂| threshold: component SDs are ~0.7-0.9pp at n=4,560, so in the 6.5-9pp FAIL
> band the dominance call is near a coin flip. **Ceiling guard:** a cell whose anchor-arm truncation
> is ≥75% is mechanism-UNINFORMATIVE (no headroom in the mediator); a cell whose anchor NO-ANSWER mass
> is <75% truncation-dominated cannot support a budget read. Do not pre-predict which cells qualify —
> the two nearest vintages disagree (canonical `think=on` 77.6/91.8/14.3% vs iss024d parser-off
> 29.8/54.5/20.2%), so it is determined post hoc by the guard.
>
> **Help direction.** If the FAIL is positive (nt-ster better), the same metrics are reported plus a
> pre-registered per-task leakage ranking — `validate_plan > simulate > validate_problem ≈
> validate_domain > solve` — tested by Spearman ρ of per-task Δ̂ against the pre-registered rank at a
> stated α, with the note that per-task half-widths make the middle ranks unresolvable. Rationale:
> only `validate_plan`'s appended sentence adds a word the neutral instruction lacks ("domain", absent
> from v12/v13); `solve` names no tool at all. Concentration at the bottom of the ranking is reported
> as unexplained.

*Justification:* a FAIL needs a pre-committed story or the post-hoc one will look chosen; and the
verified `failure_reason` × truncation structure makes the two-bucket version circular.

### A9 — §7: add the analysis-script and preflight specifics

> Write the analysis script locally while the run is in flight, and freeze it by commit hash in this
> prereg. It must implement: dedup by trial key (last wins); a completeness assertion (9,120 rows and
> 1,520 per variant per cell — the exact cancellation in §3 depends on it, and any imbalance is
> reweighted with the reweighting reported); the fixture-matched join (trial key with the variant slot
> stripped); the paired per-domain difference with a t₁₉ / bootstrap CI clustered on domain; unpaired
> Newcombe as the companion; F at pooled AND per-task granularity; the per-task eligibility
> classification; and the mechanism partition. **Forbid `--shard`:** `prompt_variant` is in the shard
> key (`runner.py:647-650`), so any shard split breaks the +3-offset pairing the primary depends on.
> Preflight per standing rule; note that HEAD is generation-identical to `6007032` (the only diffs
> across `pddl_eval/`, `run_experiment.py`, `cluster-experimenting/`, `domains/` are 3 doc-path comment
> lines), and that the plugin venvs (`pddl-solver`, `pddl-validator`) MUST be built even for a no-tools
> run because MCP is connected unconditionally (`run_experiment.py:357`) and is the grading oracle for
> no-tools `solve` (`scoring.py:499`).

*Justification:* registering a paired estimator without the code is how it silently reverts to
unpaired; and a `--shard` split would silently destroy the design.

---

## 6. Blocking prerequisites

| # | Item | State | Needs code change + PR? |
|---|---|---|---|
| 1 | `--include-no-tools-steered` plumbed end to end (`run_experiment.py:601` → `:472` → `runner.py:605` → gate `:667`; wrapper `:170` → `:502-503` → sbatch `:391-392` → `:430`) | **DONE** (verified) | No |
| 2 | Steered override fires under `with_tools=False` for v14-16 (`runner.py:288-301`, docstring names H4) | **DONE** (verified) | No |
| 3 | Zero pre-existing no-tools steered rows anywhere (194 `trials*.jsonl` scanned, stale mirror excluded) | **DONE** (verified — this is new data, not a rerun) | No |
| 4 | gemma iss024d wt cell exists (9,120 rows, v11-16 × 1,520) → §4b correction | **DONE** (verified) | No |
| 5 | HEAD generation-identical to `6007032`; plugins additive since `5e4f9c0` (only `pddl-visualizer`, not in `REQUIRED_PLUGINS`) | **DONE** (verified) | No |
| 6 | Ratify think-mode scope with the **corrected** price (~186 GPU-h, not ~92) in hand | **TODO — Omer** | No |
| 7 | Apply amendments A1-A9 to the prereg text before submit | **TODO — agent** | No |
| 8 | Smoke the never-exercised `--include-no-tools-steered` production path: confirm 9,120 rows/cell, 1,520 per variant, and the steered directive present in the stored prompt under `with_tools=False` | **TODO — cluster, ping-gated** | No (`tests/test_prompts.py:365-386` already asserts the emit set; the smoke confirms the production path) |
| 9 | Write + freeze the analysis script (per A9) before sync | **TODO — agent, local** | No |
| 10 | Verify served vLLM tag from the log header (`$HOME/vllm.sif` is a mutable shared cache) and record both repo SHAs in the run provenance | **TODO — cluster, ping-gated** | No |
| 11 | `vllm_lookup` case for `meta-llama/Llama-3.1-8B-Instruct` (`TOOL_CALL_PARSER=llama3_json`, `REASONING_PARSER=none`) — without it `submit_with_rtx.sh:341-343` aborts before sbatch | **TODO** | **YES — branch + PR.** Do NOT append the tag to `PDDL_VLLM_VERIFIED_MODELS` while nt-ster is live (`submit_with_resume.sh:18` expands that array into the submit roster). Do not check the branch out in `$HOME` until every nt-ster cell is terminal — the sbatch sources `lib/defaults.sh` from `$HOME` at run time, so a worktree does not help. |
| 12 | Optional `--variants 11,14` pass-through if the §6 arm spec is to be honoured literally (`--num-variants` is prefix-only and neither it nor `--domains`/`--problems` is plumbed through the wrapper or sbatch) | **TODO / optional** | **YES — branch + PR.** Otherwise accept the ~13,680-trial standard shape. |
| 13 | Optional `status.sh` nt-ster column (~4 lines: `COND_SPLIT` maps `no-tools` → neutral only and discards the steered slice; `DENOM` prices the cell at 4,560 against an actual 9,120) | **TODO / optional** | **YES — branch + PR**, or accept manual `wc -l trials.jsonl` progress checks |
| 14 | Confirm ISS-024(b) `guided_json` stays parked through the submit (it is the interpretability precondition for A8's M1) | **TODO — confirm in writing** | No |
| 15 | `llama3_json` registration in vLLM v0.20.2 | **UNVERIFIABLE locally** — read from the serve-flag echo (`run_condition_vllm_rtx.sbatch:219`) | No |

---

## 7. Items needing Omer, not an agent edit

**(A) Genuine D-J5 re-decisions — the accepted decision's *content* changes:**

1. **The price.** D-J5 was accepted at "~92 GPU-h total, 3 parallel rtx_6000 jobs, <4 days wall". The
   measured figure is **~186 GPU-h across 6 array tasks**, ~4.1× the off-only alternative rather than
   2×. The 2× error sits exactly on the axis Omer was asked to decide, so the both-modes choice should
   be re-affirmed against the corrected number even though the recommendation is unchanged.
2. **The `think=on` value proposition.** Pre-declaring (as §3 now does) that 9B/on and gemma/on may
   return LOW-BASE-RATE / DEGENERATE means ~140 of the ~186 GPU-h may license the 07-12 e2e link
   through **35b only**. That is a materially different purchase from what D-J5's "think=on is what
   licenses the 07-12 pre-commitment's steered-WT e2e claim family" implies. Options, for Omer:
   (a) proceed as recommended and accept a possibly single-model `think=on` licence;
   (b) off-only and strike the link (D-J5's own stated fallback);
   (c) run the `think=on` legs under the **decoupled** apparatus, which demonstrably recovers range
   (9B 18.4% → 68.4%, 35b 74.3% → 82.0%, truncation 77.6% → 12.7% / 14.3% → 5.1%) — but this
   requires a **separate submit** (`--decoupled-budget` is hard-gated to `--no-tools` + `--think-modes
   on`), **cannot cover gemma at all** (the mechanism stops on `</think>`, which gemma's tokenizer
   lacks), and replaces the iss024d pin with a 2-call apparatus on the factorial's nt side. My
   recommendation is (a); (c) is a real D-J5 change and I am not taking it on an agent's authority.
3. **The Llama probe's size.** D-J5 says "3 × 1,520 = 4,560 trials, ~10-12h wall, one job". No flag
   can produce that shape; the executable shape is ~13,680 trials / ~30-36h across 2 cells, unless
   prerequisite 12 (a code change) lands. Accept the larger shape or authorise the flag.

**(B) Deviation from a D-J5-*named* element — needs Omer's initials, not a re-decision:**

4. **A1: dropping `--reasoning-parser none` for the no-tools cells.** D-J5's pin explicitly names
   "parser flags". Nothing about what is run, claimed, or licensed changes; the flag is dropped because
   implementing it literally would make no-tools `simulate` ~0% by construction and contaminate
   `solve` extraction on the declared primary surface. Inert at `think=off`, and a no-op for gemma in
   both modes. I am classifying this as a measurement-validity correction rather than a scope change,
   but it should be initialled explicitly so it is never read as post-hoc apparatus drift.

---

## 8. What remains genuinely unverified

1. **The whole `think=on` no-tools apparatus is unrun.** No corpus on disk is single-call, no-tools,
   `think=on` with a Qwen reasoning parser **and** 16K snapshots; the canonical cells are 500-char
   snapshots and the 16K no-tools corpus is the 2-call decoupled path. Every `think=on` projection
   here (base rates, truncation, censoring, F) is extrapolated across a snapshot or budget-mechanism
   boundary. The anchor arm is what makes this survivable; the projections are indicative only.
2. **`simulate`'s July classification.** The retired-grader diagnosis is solid (verified: 58-216/300
   `format_parse_fail` in the anchor vs 22.3%/40.0% under the current grader on 16K data), but I
   cannot predict the July rate under parser-on `think=on` with a shared budget. It could still land
   near the floor for budget reasons.
3. **Whether the solve robust floor is a `+30pp` threshold claim with 16-41pp of buffer.** This is the
   argument I used to *demote* the researcher's "decisive" think=on rationale. The buffer arithmetic
   reproduces from the corpus, but I did not open `paper/main.tex:534-535` to confirm the threshold
   framing. If the paper states the floor as a point estimate rather than a threshold, that argument
   partially returns — it would strengthen, not weaken, the both-modes answer.
4. **Serving nondeterminism at T=0.** Not estimable from any canonical corpus (0 duplicate keys in
   every roster cell, so no prompt was measured twice under one apparatus). The only calibration is
   the 2026-04-28 old-roster/Ollama note (4 of 5 models byte-equal). Registered as a limitation. A
   within-run variant-level null arm (a byte-identical duplicate of v11 as a new template index) would
   measure it, at +1,520 rows/cell and a `prompts.py` edit — not recommended for this run.
5. **`llama3_json` in vLLM v0.20.2**, and `enable_thinking` behaviour on Llama-3.1's chat template.
6. **Domain vs problem as the clustering unit.** I recommend **domain** (k=20, the coarser unit;
   problems nest inside it) and measured pooled paired domain-clustered half-widths of 1.09-2.09pp.
   One verifier argued problem-instance (k=100) with larger reported DEFFs on `validate_plan`; my own
   `validate_plan` unpaired inflation measured 2.0-3.6× where that verifier reported 3.05-6.18×. The
   direction is not in doubt; the exact multiplier is method-dependent, so the script should report
   both clusterings and let the wider one govern.
7. **Queue wait** is excluded from every wall estimate, and six simultaneous `rtx_6000` grants is one
   above observed precedent (iss024d ran 4 array tasks + gemma).

---

## 9. Completeness critic — findings folded into the prereg

Run after synthesis; each finding was verified by the critic before reporting. All nine
are applied in `ntster_h4_prereg.md` (locations noted in the prereg text itself).

## COMPLETENESS CRITIC — findings (verified, prioritized)

### 1. §4b's 2×2 factorial has NO locked estimand — and §5's PASS sentence cites it
`ntster_h4_prereg.md:96-101` names the factorial ({nt,wt}×{neut,ster}) but specifies no statistic: no contrast (interaction? difference-in-differences? two separate steering Δs?), no CI method, no margin, no threshold for "replicated". Yet the pre-drafted PASS language (`:113-115`) ends "*with attribution replicated in a within-July factorial*" — a claim whose criterion does not exist. Grepped: "factorial" appears in `journal_decisions_memo.md:412,414,453,459,602` and `journal_phase0_handoff.md:74` — always as a *use*, never as a test. Nobody in the set proposed a statistic; all seven topics debated whether the factorial is *licensed* (budget asymmetry, grading-recipe mismatch, gemma eligibility), never what it computes. Worse, §3 makes nt delivered-only while §4b makes wt report both surfaces (`:62-63`), so even the factorial's surface is unfixed.
**Fix:** add to §4b: the contrast is the interaction Δ_wt(ster−neut) − Δ_nt(ster−neut) per model, on the **delivered** surface for both legs, with the CI method and the pre-declared "replicated" criterion (e.g. interaction CI excludes 0 and its sign matches May); and make §5's PASS clause conditional — if the criterion is not met, the PASS sentence drops the "replicated attribution" clause rather than keeping it.

### 2. The apparatus flag is presented as settled but is a three-way trade-off with no ANSWER slot
`:45-48` states the pin as accepted fact ("`--reasoning-parser none` … *this is what licenses the within-July factorial (§4b)*"). Three topics then propose mutually incompatible changes, and **no option preserves all three comparisons** — all three legs verified in-corpus:
- **parser-off (as pinned)**: reasoning lands in `response` with no `<think>` wrapper (`scoring.py:109` can't strip it), polluting solve extraction and destroying simulate JSON coercion → grading validity sacrificed.
- **parser-on (matches May)**: sweep5v2 9B/on no-tools is 70.9% empty / 77.6% length-truncated, anchor floored at 18.4% pooled → an uninformative think=on TOST.
- **decoupled** (the only apparatus with range): breaks the pin outright, excludes gemma, and is a non-canonical corpus under CLAUDE.md.
The summary flattens this to "A1 drop `--reasoning-parser none` (highest priority)", which silently voids §2's stated licence for §4b **and** the 07-12 e2e link that slot 1's whole case rests on, and re-inserts the parser delta whose parity already FAILED (Qwen 7/20, max |Δ| 11.3pp).
**Fix:** promote this to a **fifth ANSWER slot** with an explicit sacrifice table (which of {May-drift comparability, iss024d factorial licence, grading validity} each option forfeits), and per-mode: nobody has argued parser choice needs to be the same at think=off (where it is provably inert: 0/4,560 rows carry reasoning) as at think=on.

### 3. §6 Llama probe has a kill-gate but no analysis plan, and §5 has no Llama branch
`:131-149` gives purpose, spec, and gate. It never says which of the three pairwise contrasts among {nt-neut, tl-neut, tl-ster} is the pre-registered test, what the comparator is (which Qwen model / mode / apparatus / surface), what margin or CI, or what sentence gets written. `:107-123` (claim-licensing map) has branches only for H4. So on a PASS we can pick the contrast and the comparator **after** seeing three arms × five tasks — the single largest remaining fudge surface in the document. The landing spot exists (`paper/main.tex:987`, "five open-weight models from two families") but has no pre-drafted replacement text, unlike H4's.
**Fix:** pre-register one primary contrast (recommend the availability gap Δ = tl-neut − nt-neut, plus the steering repair Δ = tl-ster − tl-neut, both pooled over tasks), name the Qwen comparator cell explicitly, state that only *sign/direction agreement* is claimed (not level comparison, since apparatus and n differ), and pre-draft both the "pattern reproduces" and "pattern does not reproduce" Limitations sentences.

### 4. No mapping from the 6-cell verdict *vector* to a §5 branch — and §3's paper-level rule contradicts itself
`:88-89`: "H4 holds iff all 6 model × mode cells PASS; named exceptions carry the fail language for their cells." These are two different rules. Under the first, one FAIL → the §5 FAIL branch (CALL beat rewritten). Under the second, one FAIL is a "named exception" and the PASS language survives. §5 has branches for PASS, FAIL, and *cell-level* UNINFORMATIVE/INCONCLUSIVE — but **no branch for a mixed vector**, which is the modal outcome once the floored/underpowered cells the set identified (gemma/on pooled 7.6%, 9B/on 18.4%, all six simulate cells at 0.0%) are counted.
**Fix:** replace with an explicit decision table over the vector, e.g.: all-PASS → PASS branch; ≥1 FAIL in an *eligible* cell → FAIL branch (no "named exception" escape); FAILs only in ineligible cells → INCONCLUSIVE branch with the cells named. Delete "named exceptions carry the fail language" or define it as a distinct fourth §5 branch with its own pre-drafted sentence.

### 5. Ground truth is regenerated live every run, never persisted — and the delivered simulate grade uses a *different*, untracked oracle
Verified chain: `run_experiment.py:415` calls `generate_ground_truth` on every run (live MCP planner + validator); nothing is written to disk (`tools/build_gt_cache.py:5-8` says so explicitly). For `simulate`, the prompt's plan **and** the answer key are the planner-canonical plan/trace (`runner.py:708-717`, comment "*simulate: gt unchanged (uses planner-canonical plan + trace)*"). But the delivered surface grades simulate against `results/derived/gt_cache.json` keyed only by (domain, problem) (`e2e_regrade.py:289-296`, `:430`) — a static Jul-11 artifact that is **gitignored and untracked** (`.gitignore:9`) with no provenance stamp (no top-level `_meta`, no marketplace commit, no build date inside). Trial rows store no prompt and no plan text, so a live-vs-cache mismatch is silent and unauditable post hoc. Third mechanism: `runner.py:708-709` `if task in ("validate_plan","simulate") and not gt.get("plan"): continue` — if the planner fails/times out on a problem in July, that fixture is **silently dropped**, so §2's "cell shape (fixed)" and "matched n" are not enforced by the harness. I probed determinism locally (`numeric_planner` on `domains/numeric/counters/p01`): 73-action plan, action multiset identical to the cache (43 `decrement c2`, 28 `increment c3`, 1 each `increase_rate`) — so determinism *held on that sample* across 5e4f9c0→HEAD, which makes the fix a cheap assert rather than a rerun. Nobody in the set mentioned GT persistence or the cache-vs-live asymmetry.
**Fix:** add to §7 step 2/4 and to the frozen script: (a) dump the run's ground truth (or per-(domain,problem) hashes of `plan` + `trace`) into each cell dir; (b) gate the analysis on those hashes matching `gt_cache.json`, and rebuild/stamp `gt_cache.json` from the pinned marketplace commit before the run, recording the commit inside the JSON; (c) assert emitted per-(task,variant) counts equal 100/120/200/1000/100 before any contrast is read — a shortfall means a dropped fixture, not a result.

### 6. The per-task verdict taxonomy is non-exhaustive; the unlabeled region is the modal marginal case
`:82-84` gives three labels (EQUIVALENT / NOT-EQUIVALENT / UNDERPOWERED) and defines UNDERPOWERED as "half-width > 5pp **with midpoint inside** the margin". Two regions have no label: (i) Δ=+3.0, HW=4.0 → CI [−1,+7]: not contained, not entirely outside, HW ≤ 5 (plausible: validate_problem n=600 gives HW ≈ 4.5pp); (ii) Δ=+6, HW=7 → CI [−1,+13]: midpoint outside, HW > 5, not entirely outside. The model-level rule has an INCONCLUSIVE residual (`:87`) but the per-task table does not — so an unlabeled cell can be swept into "UNINFORMATIVE" post hoc, a label §3 reserves for F ≥ 5pp cells, and §5:122-123 then licenses "no claim withdrawn on their basis".
**Fix:** define the three labels exhaustively and disjointly: EQUIVALENT iff CI ⊂ (−5,+5); NOT-EQUIVALENT iff CI entirely outside; **INDETERMINATE** otherwise (with UNDERPOWERED as a reported sub-flag when HW > 5pp). Keep UNINFORMATIVE strictly for the F-gate and the eligibility gate, never for a CI shape.

### 7. The denominator is undefined, and two adversarial verdicts state the underlying fact in opposite directions
`infra_failure` rows are **never written to trials.jsonl** (`runner.py:966-972` "we deliberately do NOT append them"; `:1004-1009` filters them from the in-memory list too), so every on-disk rate is over "attempts that returned", not "trials planned". The set contradicts itself here: the llama-killgate *research* asserts "denominator = ALL trials … infra-failed trials included", while its statistical-validity verdict correctly strikes that. The prereg says nothing, so after a partial/aborted cell we could choose whether missing keys count as failures. Resume integrity is fine and should be stated as such — verified on the one resumed canonical cell (9B/on/no-tools, `resumed_count=1394`): 4,560 rows, 4,560 unique keys, exactly 1,520/variant, per-(task,variant) ∈ {100,120,200,1000}.
**Fix:** one sentence in §3: the denominator is the enumerated grid (9,120/cell); `infra_failure` keys are excluded from trials.jsonl by design and MUST be re-run to completion, never counted as failures and never analysed as a subset; plus the row-count completeness gate from #5(c), with "incomplete cell → INCONCLUSIVE, never analysed on the surviving subset".

### 8. "F computed BEFORE the H4 contrast is read" has no enforcement, and §7 only promises a *skeleton*
`:65` makes a blinding claim; `:161-162` says the local work is an "analysis script **skeleton**". A skeleton completed after data lands is post-hoc by construction, and one script that prints F and Δ together makes the ordering decorative.
**Fix:** §7 step 3 → the analysis script is **complete and frozen by commit hash recorded in this document before the sync ping**, split into two entry points (`f_gate.py` then `h4.py`, the second refusing to run without a recorded F-gate output file). Same freeze covers the eligibility classification and the per-task label rule.

### 9. Two small reproducibility items nobody raised
- §2's roster writes "**gemma4:26b** (gemma4_26b-a4b)"; the only tag `vllm_lookup` accepts is `gemma4:26b-a4b` (`lib/defaults.sh:39,84`), and `submit_with_rtx.sh` hard-fails on an unknown tag. Fix: use the exact CLI tag in the doc.
- No HF weight revision is pinned: `run_condition_vllm_rtx.sbatch:225` serves `--model "$HF_MODEL"` with no `--revision`. A weight-repo update between May and July is indistinguishable from apparatus drift in the §4 anchor-vs-May delta. Fix: either pass `--revision`, or record the served model's reported revision/hash from the vLLM log and state in §4 that weight-vintage is a component of the drift term.

---

**Axes I checked and found genuinely complete** (no invented findings): flag plumbing / executability of `--include-no-tools-steered`; cell shape and the 6-cells-of-9,120 topology correction; `--time` / GPU-h / wall arithmetic; run-tag, sync destination, and the never-strip-inside-`sweep5v2-live` hazard; the four existing ANSWER slots as such; the §4b gemma factual error; the delivered-surface pass-through mechanism (`e2e_regrade.py:376-379`) and the resulting censoring scope; F's granularity and surface; pairing/clustering/estimator choice; floored-and-degenerate-cell handling; the Llama plumbing blockers. The truncation/`RESPONSE_SNAPSHOT_LEN` question was also resolved correctly by the set (keep 16,384; the raise is unnecessary and would corrupt `KNOWN_CAPS` grading) — no further finding there.