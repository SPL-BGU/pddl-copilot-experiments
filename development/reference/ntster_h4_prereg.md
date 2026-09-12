# Pre-registration — nt-ster H4 control + nt-neut anchor (+ Llama second-family probe)

**Status:** **RATIFIED 2026-08-11** (all four §10 lines; Omer, via R2/R3 in
`development/STATUS.md`). Design frozen. The submit is still gated on
the §8 readiness items 7/9/10/14 and on Omer's explicit go-ahead plus a VPN window.
Slots were FILLED 2026-07-25 and accepted the same day.
**Date:** 2026-07-24, amended 2026-07-25. **Binding source:**
`development/journal_decisions_memo.md` §6 (accepted D-J5, 2026-07-24). H4 itself was
pre-registered in May (`development/reference/sweep_prompt_bank_design.md:46`); this document
locks the July execution + analysis before any data exists.
**Reasoning trail, provenance, and rejected alternatives:**
`ntster_h4_slot_recommendations.md` [never committed to this repo — user-local
scratch; not recoverable from git] (34-agent evidence workflow:
8 investigations × 3 adversarial lenses + synthesis + completeness critic).

**Corrections applied inline are marked `[corrected 07-25: …]`. Eleven premises in the
07-24 draft were measurably false; four would have produced wrong numbers or an
uninterpretable primary endpoint silently** (the apparatus pin, the ~92 GPU-h price,
the `--time` default, and the 30-cell FAIL veto).

---

## 1. Hypothesis

**H4 (control / falsification):** the steered directive alone does not move the
no-tools floor — `(no-tools, v14-16)` ≈ `(no-tools, v11-13)` within a ±5pp
equivalence margin, tested within a single July apparatus. If H4 fails, the H2
attribution of the May +72pp steering effect to steering-under-tools is compromised
and the CALL beat is rewritten as a prompt-content effect (§5).

**Why a co-run anchor.**
[corrected 07-25: the draft cited "the 5.3pp cross-apparatus noise floor" as a
measured drift constant. It is not one. `results/derived/iss024d_parity_report.md`
records **JOB-LEVEL PARITY: FAILS** (Qwen 7/20 cells equivalent, max |Δ| = 11.3pp,
confounded with the parser-off delta), while the zero-delta gemma control produced
1/5 TOST PASS with max |Δ̂| = 5.3pp and **every gemma CI containing zero** (solve
−5.3, 90% CI [−10.7, +0.1]) — i.e. the gemma cells were underpowered, not drifted,
and in `tools/iss024d_parity.py:186-188` F only ever appended "(≤ control noise
floor)" to a FAIL label; it never gated.]
Stated correctly: *the prior cross-apparatus check failed at job level (max |Δ| =
11.3pp), while the zero-delta control showed no drift beyond sampling error.* An
unanchored nt-ster-vs-May comparison is therefore uninterpretable. The stronger
justification is structural: with `--include-no-tools-steered` both arms land in
**ONE 9,120-row cell file**, interleaved by one process against one vLLM server, so
config/vintage drift between the arms is **zero by construction**, not merely small.

Run-to-run serving nondeterminism remains and is **not bounded by our corpora**:
decoding is greedy and unseeded (`pddl_eval/chat.py:28` `TEMPERATURE = 0.0`; no `seed`
field anywhere in `pddl_eval`), and duplicate keys = 0 in every roster cell, so no
prompt was ever measured twice under one apparatus. Registered as a stated
limitation, not a number.

---

## 2. Design

**Arms.** nt-ster = no-tools, prompt variants v14-16 (`summary.py arm_for`: steered =
v14-16). Anchor = no-tools, v11-13, co-run in the same cell at full matched n. The
steered override fires under `with_tools=False` by design
(`pddl_eval/runner.py:288-301`, whose docstring names H4); the emit gate at
`runner.py:667` is the only thing that has ever suppressed these rows.

**Roster (exact CLI tags — the wrapper hard-fails on anything else,
`lib/defaults.sh:39,84`, `submit_with_rtx.sh:341-343`):**
`Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b`.
[corrected 07-25: the draft wrote "Qwen3.5-9B" and "gemma4:26b", neither of which
`vllm_lookup` accepts.]

### 2.1 Think-mode scope

> ANSWER (accepted 2026-07-25): **CONFIRMED — both modes, `think=off` AND
> `think=on`.** Off-only is a claim reduction, not a scope reduction. (1) It strikes
> the 07-12 pre-commitment's steered-WT e2e family permanently, because the only exact
> steered-WT e2e corpus is `results/iss024d-e2e-live` and it is 5 cells × 9,120 rows
> with `with_tools=True` on 100% of rows and meta `think="on"` (verified on disk; its
> steered block is already stamped DIAGNOSTIC-ONLY in
> `results/derived/e2e_overlay/pooled_e2e_table.md:115`). (2) It narrows the May
> pre-registration, which sized H4 over "think modes (2)"
> (`sweep_prompt_bank_design.md:48`) — a declarable deviation from authors whose C1 is
> pre-registration discipline. (3) `paper/main.tex:387` already asserts the fourth
> control arm per (model, **mode**, task), with zero rows on disk.
>
> **Pre-declared, so it is not discovered later:** `think=on` is the weaker half.
> Anchor-arm pooled success in the canonical `think=on` no-tools cells is 74.3% (35b),
> 18.4% (9B), 7.6% (gemma), with 14.3 / 77.6 / 91.8% cap-truncation. §2.3 addresses
> this at the apparatus level; whatever survives is governed by the eligibility rules
> in §3.4, not excluded by fiat.

**Cell shape (verified against `results/sweep5v2-live/slurm_vllm_Qwen3_5_9B_on_no-tools`):**
per model × mode, **9,120 trials = nt-neut 4,560 + nt-ster 4,560**, i.e. 6 variants ×
1,520. Per task per arm: solve 300, validate_domain 360, validate_problem 600,
validate_plan 3,000, simulate 300 (100/120/200/1,000/100 per variant).
[corrected 07-25: the draft said "12 cells". Both arms are variant subsets of ONE
cell dir, so the on-disk reality is **6 cell dirs of 9,120 rows**, and the analyzer
splits the arms at read time (`summary.py:30-42 arm_for`; `table.py` ARM_RANK already
includes `nt-ster`).]

### 2.2 Topology, `--time`, and budget

[corrected 07-25: the draft's "3 parallel rtx_6000 jobs, ~92 GPU-h, <4 days,
72h wrapper default" was wrong on all four counts.]

`submit_with_rtx.sh` fans out **one array task per (model, think, cond)** at
`rtx_6000:1 / --mem=48G` with `--time` applied **per task**
(`submit_with_rtx.sh:409-417, :424-426, :579-583`). So the off-mode submit is 3 array
tasks and the on-mode submit is 2 (§2.3), not 3 jobs × 4 cells.

**`--time` is mandatory.** The wrapper's `--no-tools` default is **12:00:00**, not 72h
(`submit_with_rtx.sh:445-446`; 72h is the tools branch), and TimeLimit increases are
admin-denied. Pass `--time 5-00:00:00` (partition cap 7 days; SLURM bills usage, not
the ask). Verify `TimeLimit` immediately after submit. A TIMEOUT is recoverable —
a resubmitted cell resumes from `OUT_DIR/trials.jsonl` — but costs a queue cycle and
another ping.

**Never pass `--all`**: the auto-prioritize gate would set `Nice=500` on exactly the
9B cells, the longest tasks in this regime (`submit_with_rtx.sh:669-689`;
`lib/defaults.sh:19` omits 9B from `PDDL_SLOW_MODELS`). Never use
`submit_full_sweep.sh` (it refuses `--time`).

**Budget.** Method: Σ `result.duration_s` ÷ assumed `CONCURRENCY=4`
(`runner.py:120`, sbatch `:104`) — a **reconstructed throughput model**, not a
measurement (concurrency is not recorded in cell meta), single-point-validated against
the one logged wall (iss024d 0.8B "~19h" vs 19.1h reconstructed). Reconstructed
per-cell wall for both arms: 9B/off ~25h, gemma/off ~8h, 35b/off ~12h, 9B/on ~78h,
35b/on ~24h, gemma/on ~38h (add ≤30% for node-speed spread). Off-mode total
**~46 GPU-h**; plain-apparatus both-modes **~186 GPU-h** (the memo's ~92 priced
`think=on` as if it cost `think=off`; the measured per-trial ratio is 2.0-4.8×, pooled
3.1×, because 78-92% of `think=on` trials run to the per-task `num_predict` cap). The
§2.3 apparatus changes the on-mode figure — see the TODO there.

### 2.3 Apparatus

**Kept from the iss024d pin:** same `vllm.sif` tag
(`docker://vllm/vllm-openai:v0.20.2`, **asserted and then verified from the served log
header**, since `$HOME/vllm.sif` is a mutable shared cache), same sbatch wrapper,
16K response snapshots, 16K ctx, marketplace/plugins at `5e4f9c0`. HEAD is
generation-identical to `6007032` (the only diffs across `pddl_eval/`,
`run_experiment.py`, `cluster-experimenting/`, `domains/` are 3 doc-path comment
lines), so the §7 preflight pull does not break the pin.

**(A) The reasoning-parser override is NOT passed.**
[corrected 07-25: this is the highest-priority correction. The draft pinned
`--reasoning-parser none`, copied from iss024d — a **with-tools** run where it is safe
because success is graded on the tool result (`scoring.py:528-536`). On a **no-tools**
cell the grade comes from the model's own text (`scoring.py:541-549`), so parser-off
is a *grading-surface change*, and three independent mechanisms break:
(i) no-tools `simulate` grading requires the entire output to be one JSON value with
**no free-text fallback** (`scoring.py:585-596`), so a reasoning prefix guarantees
`FR_FORMAT_PARSE_FAIL` — re-manufacturing exactly the artifact commit `0280a7f`
(2026-06-25) fixed; (ii) no-tools `solve`'s structured path requires whole-string JSON
after fence-stripping (`scoring.py:275-288`), so it dies and the strict fallback
harvests action-shaped lines out of the reasoning; (iii) `_THINK_BLOCK_RE` requires
**both** tags (`scoring.py:109`) while a parser-off Qwen emits only the closer
(iss024d 9B: 0 rows contain `<think>`, 6,387/9,120 contain `</think>`, `thinking`
empty in 45,600/45,600), so nothing is stripped and `extract_verdict` reads the
monologue. **None of it is repairable by the overlay**: for no-tools rows outside
`simulate` the overlay passes the stored online grade straight through
(`tools/e2e_regrade.py:373-379`), so the delivered surface *is* that grade.
Parser-off also does not buy what the pin claimed: gemma is the natural experiment —
it has always run `REASONING_PARSER=none`, so its canonical `think=on` no-tools cell
already IS a parser-off exhibit, and it still shows 91.8% `done_reason=length` and
7.6% success. The `think=on` loss channel is the **shared decode budget**, not the
parser.]
Each model therefore uses its verified per-model default (`qwen3` for the Qwens,
`none` for gemma, which has no `<think>` tokens). At `think=off` this is a no-op
(0 of 4,560 rows carry any `thinking` in every canonical `think=off` no-tools cell).
**Cost, stated:** the §4(b) factorial acquires a parser difference across its nt/wt
axis. That comparison is already declared attribution-only and is structurally
budget-unmatchable (`chat_with_tools` re-grants the per-task decode budget every turn
up to `MAX_TOOL_LOOPS = 10`, `chat.py:29`, while a no-tools trial gets one shared
budget), so adding a parser difference to an already-unmatchable diagnostic is
strictly cheaper than corrupting the nt legs' grading on two of five tasks.

> **AMENDMENT 2026-08-29 (approved by Omer as final-readout O2). §2.3(A) is scoped to
> the SINGLE-CALL path. The decoupled two-call path requires `--reasoning-parser none`.**
>
> As originally written §2.3(A) is mode-blind, and applied to §2.3(B)'s decoupled
> apparatus it guarantees a void corpus — which is exactly what happened. Job `20392801`
> produced 9,120/9,120 (35b) and 3,822/3,824 (9B) rows with an **empty `response` and
> empty `thinking`**, `done_reason=stop`, no errors, and ~12,960 tokens genuinely
> generated per row. The text was never stored and is unrecoverable.
>
> **Why the two sections are incompatible when composed.** §2.3(A)'s three failure
> mechanisms all assume a reasoning prefix contaminating the graded text, which is a
> property of the single-call path where reasoning and answer share one output stream.
> In the two-call path they do not share a stream: reasoning is consumed in call 1 and
> re-injected as *prompt*, so call 2's content is answer-only. The decoupled path was
> built for, and only ever validated under, parser-off (`chat.py:422`,
> `CHANGELOG.md:512` DECISION B). `CHANGELOG.md:512`'s claim that the reconstruction is
> "parser-state-proof" was a code-reading argument and is **empirically false**; read it
> as superseded by this amendment.
>
> **Evidence, both directions.** June's `decoupled-rollup` corpora (same models, same
> apparatus, parser OFF) show 9B 8.8% empty / 68.4% success and 35b 4.1% empty / 82.0%
> success, against August parser-ON at ~100% empty / 0% success — the flag is the whole
> effect. The 2026-08-22 rerun under parser-off (job `20489912`) then landed at 9B
> **8.2% / 69.1%** and 35b **3.9% / 82.5%**, reproducing the June corpus to within a
> point on both axes, so the diagnosis is confirmed by prediction rather than by absence
> of failure.
>
> **The feared artifact does not appear on this path.** Measured on the August rerun,
> `format_parse_fail` is **0.0% on all three `validate_*` tasks in all four on-mode
> arms**; `solve` is 1–2% (9B) and 11–13% (35b); `simulate` is 10.7–44.3% against June
> 35b parser-off's 14.0%, i.e. the known level for that task rather than a new problem.
> `simulate` is UNINFORMATIVE in both on-mode cells (F = 32.00 / 19.00) and never reaches
> a verdict.
>
> **Consequence for §4(b).** The "Cost, stated" paragraph immediately above is now
> **void in fact**: the on-mode nt legs ran parser-off, which is what iss024d already
> used, so both legs of the factorial share the parser setting and the nt/wt parser
> difference budgeted for here does not exist. The comparison remains attribution-only
> and budget-unmatchable for the separate reason given in that paragraph.
>
> **Standing operational rule added by this amendment:** a readiness smoke must assert
> `len(response) > 0` on a non-trivial share of rows. The 2026-08-20 live-smoke passed on
> turn structure and token counters (`turns=2 think_tok=8192 answer_tok=4768
> call2_prompt=2049 done=stop`), every one of which remains true on a row containing no
> text. It checked the plumbing and not the water.

**(B) The `think=on` legs run under the decoupled-budget apparatus.**
Accepted by Omer 2026-07-25 with the scope cost below stated in plain terms.
Flags: `--decoupled-budget --num-predict-think 8192` (hard-gated to `--no-tools` +
`--think-modes on`, hence a separate submit). Rationale: under the plain apparatus the
`think=on` anchor is 18.4% (9B) / 7.6% (gemma) with 78-92% cap truncation, and where
the anchor ≈ 0 the difference Δ ≥ −p is arithmetically confined inside ±5pp, so those
cells **cannot fail** — ~140 GPU-h buying pre-determined PASSes. The decoupled
apparatus demonstrably recovers range (9B 18.4% → 68.4%, 35b 74.3% → 82.0%;
truncation 77.6% → 12.7% and 14.3% → 5.1%) and is **already a paper-cited control
corpus**, so it creates no new vintage.

> **SCOPE NOTE — reduction against D-J5's "3 models, both modes", initialled at §10.**
> The decoupled mechanism stops on `</think>` and re-injects the block
> (`chat.py:379, :431, :466-467`); **gemma4:26b-a4b has no think tokens** and was
> deliberately excluded from the June decoupled sweep for this reason
> (`decoupled_run_staging.md:30`). So `think=on` covers **Qwen3.5:9B + qwen3.6:35b
> only**. Reverting to the plain apparatus (all three models, mostly uninformative
> `think=on` cells) is a one-line change to §7 step 2. What is being traded: gemma's
> `think=on` cell — which could not have produced a falsifiable answer — for two cells
> that can. Limitations must carry one sentence: no non-Qwen `think=on` control
> exists, because gemma's `think=on` no-tools cell is 90-100% cap-saturated under
> every apparatus available to us.

Consequence: `think=off` and `think=on` are **different apparatuses**. Each mode's H4
contrast remains internally valid (both arms co-run in one cell), and H4 never made a
cross-mode comparison — but no number may be compared across the two modes.

> **DONE 2026-08-16 (§8 item 7) — decoupled `think=on` wall, reconstructed.** Measured
> from `results/decoupled-rollup/*decoupled-thinkon/trials.jsonl` by the §2.2 method
> (Σ `result.duration_s` ÷ assumed `CONCURRENCY=4`). Both corpora are **neutral-arm
> only** — 4,560 rows each, v11/12/13 × 1,520 verified — so the nt-ster projection
> scales each cell to its 9,120-row both-arm shape (×2), which assumes the steered arm
> costs the same per trial as the neutral arm. That assumption is untested and is the
> single largest error term in this number.
>
> | cell | rows | Σ `duration_s` | mean/trial | wall @4 | projected 9,120-row wall |
> |---|---|---|---|---|---|
> | `Qwen3.5:9B` on/decoupled | 4,560 | 755,877 s | 165.8 s | 52.5 h | **105.0 h** |
> | `qwen3.6:35b` on/decoupled | 4,560 | 193,914 s | 42.5 s | 13.5 h | **26.9 h** |
>
> **On-mode total ≈ 132 GPU-h** (≈172 h at the +30% node-speed spread), against the
> §10 signing estimate of 110-150. **Grand total ≈ 46 (off) + 132 (on) = ~178 GPU-h**,
> inside the ratified 156-196 band — the price signed at §10 stands and no
> re-ratification is owed. Per-cell `--time` headroom: the 9B on-cell is the long pole
> at ~105 h projected, which **exceeds the 5-day (120 h) ask only after the +30%
> spread** (≈137 h). See the `--time` note in §2.2: a TIMEOUT is resumable from
> `OUT_DIR/trials.jsonl` but costs a queue cycle and another ping. The partition cap is
> 7 days, so `--time 7-00:00:00` on the on-mode submit is the cheaper insurance;
> SLURM bills usage, not the ask.

**(C) Snapshot.** `RESPONSE_SNAPSHOT_LEN = 16384` is a non-overridable code constant
(`runner.py:145-153`, "Override is intentionally not exposed"), so it comes free and is
not a per-run choice.
[corrected 07-25: delete the draft's "makes every row exactly e2e-gradeable" — false
even inside iss024d, which pins 1.0-27.6% of rows per cell at the cap (gemma
2,520/9,120), with only 2 of its 25 steered e2e cells exact.]
For no-tools cells the exposure is narrow and known: the online grade ran on the FULL
response before storage truncation, and the overlay passes it through for every task
except `simulate` (4,260/4,560 rows per cell), so **`solve` and `validate_*` are
censoring-immune and `simulate` (6.6% of rows) is the only censored task.** Censored
`simulate` cells are reported as bounds and never fed to the TOST. **Do not raise the
cap:** it has no override (a raise is a source edit that makes the pin nominal), and
`e2e_regrade.py`'s `KNOWN_CAPS = (500, 16384)` + `detect_cap` would then return `None`,
disabling every censor branch and grading genuinely truncated rows as determinate
FAILs — bias toward exactly the FAIL the control exists to exclude.

**(D) HF weight revision is not pinned** (`run_condition_vllm_rtx.sbatch:225` serves
`--model "$HF_MODEL"` with no `--revision`). Record the served model's reported
revision from the vLLM log, and state in §4 that weight vintage is a component of the
drift term.

### 2.4 Run-tag and results placement

Fresh `--run-tag ntster-h4`. Cells land at
`results/slurm_vllm_{Qwen3_5_9B,gemma4_26b-a4b,qwen3_6_35b}_{on,off}_no-tools_ntster-h4`
(`run_condition_vllm_rtx.sbatch:373`); sync to an explicit new dest
(`sync.sh results/ntster-h4-live`; the script refuses a bare `results/`).
[corrected 07-25: the draft's "run-tag breaks the analyzer cell-parser — strip
post-filter" is **STALE**. The parsers were fixed 2026-07-12
(`_constants.py:189-208, :211-243`), return `run_tag`, and `iter_cells` defaults to
untagged-only (`:368`), so tagged corpora **cannot** silently pool. The supported read
is `table.py results/ntster-h4-live --run-tag ntster-h4 --e2e`. The strip step applies
only to `build_deck.py` / `plot.py`.]
**HARD RULE: never strip inside `results/sweep5v2-live`.** Its cell dirs are untagged,
so a stripped ntster dirname would be byte-identical and would overwrite canonical
cells irreversibly.

---

## 3. Analysis plan (locked before data)

### 3.1 Surfaces and denominator

**Primary = delivered.** For no-tools rows this is the stored online grade passed
through by the overlay for `solve` and `validate_*` (`e2e_regrade.py:373-379`), so on
93.4% of rows delivered and legacy are the **same number** and the "legacy as a
consistency check" line is a tautology there — it is a real second measurement only on
`simulate`. Assert `snapshot_cap == 16384` on every new cell before interpreting
anything (`detect_cap` has no CLI override and returns 500 for any cell whose max
response length is ≤500).

**Denominator = the enumerated grid (9,120 rows/cell).** `infra_failure` rows are
**never written** to `trials.jsonl` by design (`runner.py:966-972`, `:1004-1009`), so
every on-disk rate is over attempts that returned. Such keys MUST be re-run to
completion; they are never counted as failures and never analysed as a subset. An
incomplete cell is **INCONCLUSIVE and is not analysed on the surviving subset**.
Completeness gate before any contrast: 9,120 rows, 1,520 per variant, and per
(task, variant) ∈ {100, 120, 200, 1,000} — resume integrity is sound (verified on the
one resumed canonical cell, `resumed_count=1394`: 4,560 rows, 4,560 unique keys,
exactly 1,520/variant). Any imbalance is reweighted to equal n per variant with the
reweighting reported. Note `runner.py:708-709` silently drops a
`validate_plan`/`simulate` fixture whose planner ground truth is missing, so the shape
is **not** enforced by the harness — hence the explicit gate.

### 3.2 Noise-floor control (F)

> ANSWER (accepted 2026-07-25): **(a) within-anchor paraphrase pairs, amended.
> (b) gemma-as-control-model is KILLED, not retained as an alternative.** In iss024d
> gemma was a *null-manipulation* control: the one generative delta there
> (`--reasoning-parser none`) was inert for gemma by construction because gemma is
> natively `REASONING_PARSER="none"` (`lib/defaults.sh:84-103`), so a gemma parity
> failure could only be serving nondeterminism (`iss024d_parity_prereg.md:16-19`,
> expected 5/5 PASS at `:39`). H4's manipulation is one appended prompt sentence
> applied identically to every model — the override is task-keyed with no model branch
> (`runner.py:295-301`) — so **no model is inert by construction and none can play that
> role.** gemma is also a test unit here and is the model that owns the +72pp;
> demoting it would gut the attribution and shrink the roster to two.
>
> **F = max |Δ̂| over the three within-anchor paraphrase pairs** (v11-v12, v11-v13,
> v12-v13).
>
> **At pooled granularity F is a bank-validity check, not the operative noise.** With
> equal n per variant on both arms the pooled Δ is exactly (1/3)Σ[p(v+3) − p(v)], so
> the paraphrase MAIN effect cancels arithmetically and F measures what the design
> already removes. Measured on canonical no-tools: 9B off 1.45 / on 1.32, gemma off
> 2.17 / on 0.99, 35b off 1.64 / on 3.03pp — all < 5pp, so the ±5pp margin survives at
> the confirmatory granularity and the "F ≥ margin ⇒ UNINFORMATIVE, never rescued"
> clause is retained (it will not fire there).
>
> **F is ALSO computed at every granularity where a verdict is read, and there it is a
> gate.** At task granularity the same designed-equivalent paraphrase pairs move
> `solve` by **6.0-30.0pp in all six cells** (9B off 28.0, 9B on 15.0, gemma off 15.0,
> gemma on 6.0, 35b off 28.0, 35b on 30.0) and `validate_domain` by 0.0-12.5pp (>5pp in
> 3 of 6). Mechanism, from `failure_reason`: at `think=off` `solve`, v11/v13 hit
> `format_parse_fail` 77-91% while v12 hits 13-54% — a prompt-form × JSON-extraction
> interaction, not sampling noise, and not reducible by n. **Pre-registered
> consequence: a model × mode × task cell whose own F ≥ the margin is UNINFORMATIVE and
> cannot contribute a FAIL.** Without this the §3.4 rule is a false-FAIL machine.

### 3.3 Estimator and primary granularity

> ANSWER (accepted 2026-07-25): **Pooled model × mode stays the primary**, with three
> corrections to how it is estimated and one to what can veto it.
>
> **1. Paired and domain-clustered, not independent-samples Newcombe.** The arms are
> item-matched by construction: v11/v12/v13 cover byte-identical
> `(task, domain, problem, plan_label)` sets and v14-16 are v11-13 plus one appended
> sentence, so nt-ster vs nt-neut is 4,560 matched pairs. And the tasks are **not**
> independent — all five draw the same 20 domains and the same 100 `(domain, problem)`
> pairs (solve ∩ validate_plan ∩ simulate = 100/100; validate_domain 120 and
> validate_problem 200 are supersets containing all 100), with `validate_plan`'s 1,000
> rows/variant being 100 problems × 10 plan labels. Primary CI = 90% interval on the
> per-domain mean of the per-fixture paired difference, **clustered on domain**
> (k = 20, t₁₉), with a domain-clustered bootstrap (B = 10,000) as the reported
> equivalent and unpaired Newcombe as the conservative companion. The script reports
> **both** domain (k=20) and problem-instance (k=100) clusterings and **the wider one
> governs**. Measured on the anchor's own designed-null paraphrase contrast, the pooled
> paired domain-clustered half-width is **1.09-2.09pp** across the six cells (unpaired
> Newcombe 1.59-2.87pp; one-arm SE inflation from clustering on `validate_plan` alone
> is 2.0-3.6× binomial). So ±5pp is powered at pooled granularity with ~2.4-4.6×
> headroom, and the conjunction over the model × mode units has ~87% power at Δ = 0 —
> stated here rather than assumed.
> [corrected 07-25: an earlier recommendation substituted an unweighted 4-task-mean as
> primary. That rests on "tasks use disjoint fixtures so per-task deltas are
> independent", which is **verified FALSE** (see the shared-domain/shared-problem
> arithmetic above), and its half-widths were computed under nominal-n independence.
> Pooled + clustering needs no substitution.]
>
> **2. Composition is named, not fixed by substitution.** `validate_plan` is
> 3,000/4,560 = 65.8% of a pooled cell, and on a real contrast the pooled number is
> close to one task (for gemma/off with-tools steering, pooled Δ = +47.4pp vs
> unweighted 5-task mean +14.3pp, with `validate_plan` supplying 100% of the pooled Δ).
> The companion is the **unweighted mean over ELIGIBLE task cells**, reported alongside.
> A pooled PASS whose eligible-task-mean disagrees is reported as a disagreement, not
> resolved.
>
> **3. Per-task cells are pre-classified from the ANCHOR before the contrast is read**,
> into exactly one of: **ELIGIBLE** (anchor rate in [10%, 90%] AND own-granularity
> F < margin AND realized paired domain-clustered half-width ≤ 5pp); **LOW-BASE-RATE**
> (anchor < 10%: reported with the absolute CI *and* a relative risk-ratio bound,
> because ±5pp absolute at a 7.6% anchor admits a 1.66× relative move);
> **DEGENERATE** (anchor exactly 0% or 100%: one-sided bound only, since 0-vs-0
> equivalence is vacuous); **UNINFORMATIVE** (fails the F or half-width test).
> Indicative classification from the anchor corpus, so the shape is known now:
> `validate_plan` ELIGIBLE in all six cells (half-width 1.28-3.07pp);
> `validate_problem` ELIGIBLE in 3 of 6; `validate_domain` UNINFORMATIVE in 3 of 6
> (half-width 9.4-13.4pp); `solve` UNINFORMATIVE in all six (F 6.0-30.0pp, half-width
> 4.8-12.9pp); `simulate` classified on the **July** anchor (§3.6). These are
> projections, not commitments — classification is assigned mechanically by the frozen
> script on realized July rates.
>
> **4. The FAIL veto is restricted to ELIGIBLE cells.**
> [corrected 07-25: the draft's "FAIL if any task cell's CI lies entirely outside" is a
> union-intersection test over 30 cells that is near-certain to trip for reasons
> unrelated to steering: **9 of 90 designed-null within-anchor paraphrase contrasts (in
> 5 of 6 cells) already have 90% CIs lying entirely outside (−5, +5) with no directive
> present**, and §5 would convert that into "H4 failed → the CALL beat is a
> prompt-content effect".]

### 3.4 Decision rule

**Per-task labels — exhaustive and disjoint** (evaluated only on cells that pass the
§3.3 classification): **EQUIVALENT** iff the CI ⊂ (−5, +5); **NOT-EQUIVALENT** iff the
CI lies entirely outside; **INDETERMINATE** otherwise, with UNDERPOWERED as a reported
sub-flag when the half-width > 5pp. `UNINFORMATIVE` is reserved strictly for the F
gate and the eligibility gate and is never applied to a CI shape.
[corrected 07-25: the draft's three labels left two unlabeled regions — e.g.
Δ=+3.0/HW=4.0 and Δ=+6/HW=7 — which could have been swept into UNINFORMATIVE post hoc.]

**Per model × mode:** **PASS** iff the pooled CI ⊂ (−5, +5) AND no ELIGIBLE task cell
is NOT-EQUIVALENT; **FAIL** if the pooled CI lies entirely outside OR any ELIGIBLE task
cell is NOT-EQUIVALENT; **INCONCLUSIVE** otherwise. LOW-BASE-RATE, DEGENERATE and
UNINFORMATIVE cells are reported in full and carry no verdict authority. A `think=on`
PASS at an anchor < 15% licenses only the absolute ±5pp statement.

**Paper-level, over the verdict vector** — a table, because a mixed vector is the modal
outcome:

| vector | branch |
|---|---|
| all units PASS | §5 PASS branch |
| ≥1 FAIL in an ELIGIBLE cell (any unit) | §5 FAIL branch — **no "named exception" escape** |
| FAILs only in ineligible cells | §5 MIXED branch, cells named |
| otherwise | §5 INCONCLUSIVE branch |

[corrected 07-25: the draft said both "H4 holds iff all 6 cells PASS" and "named
exceptions carry the fail language for their cells" — two contradictory rules with no
branch for a mixed vector.]
**Multiplicity:** intersection-union, so the conjunctive equivalence claim needs no α
correction and none is applied; the affirmative non-equivalence claim gets Holm across
the ELIGIBLE family only. Family membership is frozen by the pre-registered rule and
never re-picked after seeing Δ̂ — a realized half-width overrun yields UNINFORMATIVE
for that cell; it does not shrink the conjunction.

**MDE table, registered.** Per cell, publish 5 + the realized clustered half-width
(the |Δ| needed to FAIL), so the PASS language cannot overclaim beyond the design's
resolution.

### 3.5 Control conservatism (pre-registered)

Under `with_tools=False` the system prompt is always
`WITHOUT_TOOLS_SYSTEM_BY_TASK[task]` regardless of variant (`runner.py:309-316`), which
states "PDDL validation tools are not available in this evaluation. Analyze … using
your own reasoning", while the steered v14-16 user text says "Use the validate_domain
tool with the domain as its argument". The control therefore removes both the tool and
its stated availability, which **biases H4 toward PASS**. §5's PASS sentence is scoped
accordingly. Fixing the contradiction would require a third steering construct (the
parked D4(ii) reframe) and is out of scope.

### 3.6 `simulate`

The canonical anchor shows 0.0% no-tools `simulate` in all six cells, but that is a
**retired-grader artifact, not a capability floor**: the failure mass is
`format_parse_fail` (58-216 of 300 per cell), exactly the strict-wrapper behaviour that
commit `0280a7f` (2026-06-25) replaced with the wrapper-tolerant grader, and under the
current grader the 16K no-tools corpus reads 22.3% (9B) / 40.0% (35b). July `simulate`
is therefore expected to be non-zero and its H4 contrast is live; it is classified from
the **July** anchor under §3.3, **never pre-declared degenerate**. Corollary: the
anchor-vs-May drift datapoint (§4) is reported for `solve` / `validate_domain` /
`validate_problem` / `validate_plan` only — `simulate` drift is grader-confounded and
**unmeasurable**, because May `simulate` responses are stored at 500 chars and cannot
be re-graded.

### 3.7 Mechanism decomposition (secondary; never gates or revises the H4 verdict)

Both candidate mechanisms are prompt-content effects, so the decision rule is unchanged
either way; only the story differs, and the story is locked here. Computed from fields
already written per row — no new grader, no new run.

**Partition (three-way, not two).** `truncated_no_answer` is 100%
`done_reason=="length"` and `format_parse_fail` is 100% non-truncated (verified, 27,360
roster no-tools rows; forced by the write-time override at `scoring.py:622-644`), so:
**TRUNCATED-LOSS** = `truncated_no_answer`; **CHANNEL/FORMAT** = `format_parse_fail`
(+ overlay `format_parse_fail` on `simulate`); **CONTENT** = `verdict_mismatch`,
`plan_invalid`, `result_mismatch`, `simulate_empty` (+ overlay `trajectory_mismatch`);
**APPARATUS** = `exception`, `tool_error`, `unknown`, other (reported, excluded; >1% in
either arm voids that cell's mechanism read). Overlay `censored_at_snapshot_cap` is
reported separately and folded into neither side. The four components partition Δ̂
exactly (ΣΔ = −Δ̂), so this is an **accounting split with CIs, not two independent
measurements** — do not present Δtruncation as corroborating ΔTRUNCATED-LOSS; they are
the same rows.

**Metrics** per model × mode × arm, pooled and per task: **(M1) directive echo** —
share of rows whose `response` matches the task's tool name,
`/(classic_planner|numeric_planner|validate_domain|validate_problem|validate_plan|get_state_transition)/i`
for validate_*/simulate and `/planner tool|the planner\b/i` for `solve` (whose
directive names no tool); **(M2) budget** — `done_reason=="length"` share, mean/median
`tokens.completion`, at-cap share as `len(response) == 16384`; **(M3)** the partition
deltas with 90% CIs on the same paired domain-clustered footing as §3.3.

**M1 is reported as an ARM DIFFERENCE, never as an absolute.** Base rate in the roster
neutral no-tools arms is 0/27,360 (verified) and the v11-13 templates contain no tool
name, but that anchor is measured on 500-char snapshots and is a specificity floor, not
a guarantee; the July anchor arm supplies the operative base rate. M1 is a lower bound
on at-cap rows and is anti-correlated with displacement by construction, so a depressed
M1 inside a displacement-dominated cell may never be read as "no directive echo". M1 is
interpretable only because `guided_json` does not bind (ISS-024(b), parked); if that fix
lands first, M1 is declared N/A rather than reinterpreted.

**Label, assigned only to a cell whose H4 verdict is FAIL and only where estimable**
(pooled granularity, |Δ̂| ≥ 9pp, dominant component's share CI excluding 0.5):
**DISPLACEMENT** if TRUNCATED-LOSS dominates and mean `tokens.completion` moves with
it; **REASONING SHIFT** if CONTENT dominates; **CHANNEL** if CHANNEL/FORMAT dominates;
otherwise components reported with no label. (Component SDs are ~0.7-0.9pp at n=4,560,
so in the 6.5-9pp FAIL band the dominance call is near a coin flip.) **Ceiling guard:**
a cell whose anchor-arm truncation is ≥75% is mechanism-UNINFORMATIVE. Do not
pre-predict which cells qualify — the two nearest vintages disagree — it is determined
post hoc by the guard.

**Help direction.** If the FAIL is positive (nt-ster better), the same metrics plus a
pre-registered per-task leakage ranking — `validate_plan > simulate > validate_problem
≈ validate_domain > solve` — tested by Spearman ρ of per-task Δ̂ against the
pre-registered rank at a stated α, noting that per-task half-widths make the middle
ranks unresolvable. Rationale: only `validate_plan`'s appended sentence adds a word the
neutral instruction lacks ("domain", absent from v12/v13); `solve` names no tool at all.
Concentration at the bottom of the ranking is reported as unexplained.

---

## 4. Anchor scope — exactly two uses (pre-registered wall)

**(a)** The paired H4 confirmatory contrast (§3).

**(b)** The within-July 2×2 factorial {nt, wt} × {neut, ster} with iss024d's existing
wt-neut/wt-ster cells — attribution only, diagnostic/steering scope, `think=on`.
**Models = all three roster models.**
[corrected 07-25: the draft said "gemma has no iss024d wt cells and sits out". False on
disk: `results/iss024d-e2e-live/slurm_vllm_gemma4_26b-a4b_on_tools_all_minimal_iss024d-e2e`
holds 9,120 rows with v11-16 at 1,520 each, all `with_tools=True` (job 19314599,
`paper_notes_discussions.md:755-757`). gemma is the model that owns the +72pp, so
excluding it would gut the attribution.] 0.8B/4B still sit out for lack of July nt
cells. **Under §2.3(B) gemma has no July `think=on` nt leg**, so its factorial cell is
unavailable for a different and correctly-stated reason.

**Estimand, locked** (the draft named the factorial but specified no statistic while
§5's PASS sentence already cited its result): the contrast is the **interaction**
Δ_wt(ster − neut) − Δ_nt(ster − neut) per model, on the **delivered** surface for both
legs, with the §3.3 clustered CI. "Replicated" means the interaction CI excludes 0 and
its sign matches May. If that criterion is not met, §5's PASS sentence **drops the
"replicated attribution" clause** rather than keeping it.

The anchor-vs-May delta is reported **ONLY** in the validity thread as a drift
measurement and can never revise a NEED-stage number. Its components now include a
reasoning-parser configuration difference for the Qwens (§2.3(A)) and an unpinned
weight revision (§2.3(D)); label it accordingly rather than as pure vintage drift.
`simulate` is excluded from it (§3.6). No third use exists.

---

## 5. Claim-licensing map (pre-drafted paper language)

- **PASS →** "A pre-registered control (H4, May 2026), executed in July 2026 against a
  co-run neutral anchor, finds the steered directive alone does not move the no-tools
  floor when the prompt also states that tools are unavailable (paired
  domain-clustered TOST, ±5pp, all eligible units equivalent; per-task, prompt-only
  effects larger than ⟨MDE per cell⟩ are not excluded). The steering effect is
  therefore attributed to the directive's interaction with tool access[, with
  attribution replicated in a within-July factorial — **clause included only if §4(b)'s
  criterion is met**]."
- **FAIL →** "The pre-registered H4 control failed: the steered directive alone moves
  the no-tools floor by Δ = X pp [CI] on ⟨eligible cells⟩. We therefore report the
  steering result as a prompt-content effect and qualify the CALL-stage attribution
  accordingly." (Executing and reporting a failed pre-registered control is itself C1
  evidence, as with the iss024d parity FAIL.) The §3.7 mechanism label, where
  estimable, is reported in the same paragraph.
- **MIXED (FAILs only in ineligible cells) →** "The control is equivalent on every
  eligible unit; ⟨named cells⟩ fail the margin but are ineligible (low base rate /
  degenerate / paraphrase-noise-dominated) and license no attribution change."
- **INCONCLUSIVE / UNINFORMATIVE cells →** reported as such; no claim licensed or
  withdrawn on their basis.

**Caveat-only integration cap (pre-committed):** results may only delete or convert
existing caveats, never add body surfaces. nt-ster edits the existing CALL beat +
Limitations only; the one-figure steering cap holds even if H4 passes. **No `simulate`
steering language may depend on an H4 PASS** unless `simulate` lands ELIGIBLE in July.
The P1 writing sprint proceeds under worst-case scoping (steering diagnostic-only), so
neither run can delay the manuscript.

---

## 6. Second-family probe — Llama-3.1-8B-Instruct (runs SECOND)

**Purpose:** bound (not resolve) the single-family confound. Outcome edits the
family-confound Limitations paragraph + at most one appendix table.

**Spec:** `meta-llama/Llama-3.1-8B-Instruct`; `TOOL_CALL_PARSER=llama3_json`;
`REASONING_PARSER=none`; `rtx_6000:1`. Arms: nt-neut + tl-neut + tl-ster.
**Executable size ≈ 13,680 trials / ~30-36h across 2 cells**, not the memo's 4,560 /
10-12h: `--num-variants` is prefix-only and is not plumbed through the wrapper or
sbatch, so no flag can select `{v11, v14}`. Accept this shape or authorise the
`--variants` pass-through (§8 item 12). Plumbing + smoke prep happen while nt-ster
runs. **Distinct `--run-tag llama-probe`** — without it the cell could land in a tree
the H4 analysis globs, mixing a different family, vintage and a with-tools arm into the
equivalence test.

**Apparatus = a NEW vintage, stated as such.** Same sbatch/image/ctx pin as §2 plus the
new `vllm_lookup` case; it necessarily post-dates the frozen submit path. Do not write
"matched apparatus". Record the `defaults.sh` SHA in the run memo. Run the tools arms
at `think=on` if any comparison to the roster's with-tools ToolSel is intended (the
iss024d corpus is `think=on`, tools-only); a `think=off` tools cell has no within-July
band. Do not assume the think label is inert for a non-reasoning template — gemma, the
roster's other `REASONING_PARSER=none` model, swings 54.7% → 18.2% on v11 tools ToolSel
between modes.

### 6.1 Kill-gate

> ANSWER (accepted 2026-07-25): **Direction CONFIRMED (`<` threshold → stop). Threshold
> 0.95 REJECTED. The gate is replaced by a signature test, not a rate test.**
>
> **Direction.** The memo sentence is a dropped negation: `lib/defaults.sh:91-93`
> certifies gemma's parser because "tools-cell ToolSel ≥0.95 in smoke 17638752" — there
> ≥0.95 is the criterion to **PROCEED**. Read as "proceed iff …, else stop".
>
> **Why 0.95 dies.** It is 19/20 validate_plan calls in the 2026-05-18 gemma smoke
> (`CHANGELOG.md:1314`), measured at commit `59be812` where
> `ACTIVE_PROMPT_VARIANTS = (0,1,2)` and the with-tools system prompt was the maximal
> steer; the v11-16 bank landed eight days later. Wilson 95% for 19/20 is
> [0.764, 0.991] — it turns on one trial. And on the arms this probe runs, a pooled
> ≥0.95 bar rejects **6 of the 10** published model × mode with-tools configurations on
> v11 and 2 of 10 on v14, including gemma4-26b, whose parser that same 0.95 certified;
> 30 of 100 task-level sub-cells sit below 0.95, floor gemma/on/v11/validate_plan at
> 1.4%. LiveMCP-101 puts Llama-3.1-8B at 1.0%, so 0.95 would fire precisely when the
> probe delivers its signal.
>
> **Why a replacement rate threshold also dies.** A `--tool-call-parser` mismatch
> produces uniform 0% with no startup error (`cluster-experimenting/README.md:319-322`),
> and a genuinely non-calling model produces the same 0%. No function of the tool-call
> rate can separate them. At smoke sub-cell n (1/2/6/10/1 per arm) a "max over
> tasks × arms < 0.50" rule fires with ~92% probability at a true rate of 1% — a
> low-adherence detector wearing a plumbing-detector label.
>
> **The gate (evaluated on tools rows, `think` as submitted).**
> - **G0 precondition.** Row count equals the enumerated total and the
>   `failure_reason == "exception"` share ≈ 0. `APIConnectionError`/abort rows are
>   dropped from `trials.jsonl` entirely (`runner.py:424-441`), so a wedged server
>   silently shrinks n rather than showing zeros; a chat-template 400 (e.g.
>   `enable_thinking` on a template that does not define it) writes
>   `failure_reason=exception` with `tool_selected=None`, which would fire any rate
>   gate. Failing G0 is a **config error**: fix and rerun; it consumes no retry and
>   licenses no Llama statement.
> - **G1 PRIMARY — parser-mismatch signature (automated, n-free).** For every tools row
>   with `tool_calls == []`, classify the stored `response` for tool-call syntax
>   (`<tool_call`, `<function`, `<|python_tag|>`, or a JSON object carrying both
>   `"name"` and `"arguments"`/`"parameters"` naming a plugin tool). **≥1
>   syntax-present-but-unparsed row ⇒ PARSER MISMATCH ⇒ re-serve.** 0 such rows ⇒ the
>   observed rate is the model's behaviour ⇒ **PROCEED regardless of its value.**
>   Verified separating on canonical data: 0 of the 986 zero-call
>   gemma/on/v11/validate_plan responses contain any such marker — genuine
>   non-adherence is prose, visibly unlike an unparsed emit. Run it on the
>   multi-argument tasks too, to catch a parser that handles single-arg calls but
>   mangles multi-arg ones (the known FastMCP arg-error signature). This replaces the
>   drafted "eyeball 5 `tool_calls` payloads", which inspects the wrong artifact — in
>   the 0% case there are no `tool_calls` to read.
> - **G2 belt — pooled zero.** Kill only at **exactly zero parsed tool calls across all
>   tools rows in the slice**, never a max-over-sub-cells rate. A parser is
>   variant-independent, so pooling is valid.
> - **G3 belt — pooled zero extraction.** Kill only at **zero extracted answers** over
>   the pooled no-tools v11-13 rows, where extracted := `failure_reason` ∉
>   {`format_parse_fail`, `truncated_no_answer`, `think_overflow`, `exception`} (no
>   `extraction` field is stored — the formula is the definition). Never an unscoped
>   "0% extraction → stop": Qwen3.5-0.8B's `think=on` nt-neut extraction is 4/4,560 =
>   0.088%, so an unscoped rule would kill a published roster model on the documented
>   shared-budget truncation confound.
> - **Cost-asymmetry default.** Anything above G2/G3 PROCEEDS. Low measured ToolSel is
>   this probe's payload, per the standing rule that tool-use failures are data.
>
> **Retry policy.** Re-serves are triggered ONLY by the G1 signature and change ONLY
> vLLM serve flags (`TOOL_CALL_PARSER`, plus `MAX_NUM_BATCHED_TOKENS`/`GPU_MEM_UTIL` if
> startup-bound); candidate order `llama3_json` → `pythonic` → `hermes`. Never a
> prompt, fixture, system-prompt or scaffold change. A server that refuses to start on
> an unregistered parser name is a config error, not a gate evaluation, and consumes no
> retry. **Do not select a parser by whichever slice maximises ToolSel** — at n=40 with
> a true 30%, E[max of 3] ≈ 36% and the interval has no post-selection coverage; any
> reported ToolSel comes from the full cell, never from the selection slice.
>
> **Where it is evaluated.** Stock `--smoke` cannot evaluate any v14 gate: it forces
> `--num-variants 1` (`run_experiment.py:762-764`) and `ACTIVE_PROMPT_VARIANTS[:1] =
> (11,)`; and `--num-variants` / `--domains` / `--problems` are **not plumbed** through
> the wrapper or the sbatch invocation, so an "explicit 180-trial slice" is not
> submittable. Therefore **gate on a prefix of the real Llama submit**: submit with an
> explicit `--time`, sync at ~T+60-90 min, evaluate G0-G3 on the rows that have landed,
> `scancel` on a fire. The variant loop is innermost, so v11 and v14 tools rows land in
> the first fixtures.

### 6.2 Analysis plan (pre-registered, so the contrast is not chosen after the fact)

Primary contrasts, both pooled over tasks: the **availability gap**
Δ = tl-neut − nt-neut, and the **steering repair** Δ = tl-ster − tl-neut. Comparator =
`Qwen3.5:9B` at the matching mode, named now. **Only sign/direction agreement is
claimed**, never a level comparison, because apparatus vintage and n differ. CIs on the
§3.3 clustered footing. Pre-drafted Limitations sentences:
- *pattern reproduces* — "A third-family 8B model (Llama-3.1-8B-Instruct, a distinct
  July vintage) reproduces the direction of both the availability gap and the steering
  repair, so the regime structure is not a Qwen-recipe artifact; levels are not
  compared across vintages."
- *pattern does not reproduce* — "A third-family 8B point does not reproduce the
  ⟨named⟩ direction. We therefore state the family confound as unresolved and bound our
  claims to the Qwen/Gemma roster."
- *killed* — "0 of N tool calls parsed (Wilson 95% upper X%); no unparsed tool-call
  syntax was present in the stored responses, so the plumbing was verified by emit
  format and the full cell was not run." **Never** "tool invocation was not
  measurable". **No row in `tab:decomp`** (its rows are n=1,520-per-cell arm-pooled
  decompositions), and a kill licenses no comparative Llama-vs-Qwen claim — forbidden
  on apparatus-vintage grounds, not precision grounds.

---

## 7. Operational plan (ping-gated where marked)

1. Ratification (§10) — no ping. Then: apply the §2.3(B) wall reconstruction TODO, and
   write + **freeze the analysis scripts** (item 3 below) before the submit.
2. **[CLUSTER — ping + VPN] Two submits**, models named explicitly, never `--all`:
   - off-mode: `bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B gemma4:26b-a4b qwen3.6:35b --no-tools --include-no-tools-steered --think-modes off --run-tag ntster-h4 --time 5-00:00:00`
   - on-mode: `bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B qwen3.6:35b --no-tools --include-no-tools-steered --think-modes on --decoupled-budget --num-predict-think 8192 --run-tag ntster-h4 --time 5-00:00:00`

   Verify `TimeLimit` immediately after each submit. Preflight per standing rule (pull →
   rebuild venvs without `--quiet` → verify imports); **the plugin venvs
   (`pddl-solver`, `pddl-validator`) MUST be built even for a no-tools run** because MCP
   is connected unconditionally (`run_experiment.py:357`) and is the grading oracle for
   no-tools `solve` (`scoring.py:499`) and the source of the plan text embedded in
   `validate_plan`/`simulate` prompts. Record both repo SHAs and the served vLLM
   image/revision from the log header. Expect gemma's VRAM guard to sit at zero margin
   (documented peak 85.9% against a `> 85` integer guard, `sbatch:263-272`); on `rc=3`
   resubmit gemma alone with `GPU_MEM_UTIL=0.82`.
   **Smoke first** (full-run resources, `--time 24:00:00`): the
   `--include-no-tools-steered` production path has never produced data, and its
   composition with `--decoupled-budget` is **unverified**. Confirm 9,120 rows/cell,
   1,520 per variant, and the steered directive present in the stored prompt under
   `with_tools=False`.
3. **Local while running:** two frozen entry points, **committed and their hashes
   recorded in this document before the sync ping** —
   `tools/ntster_f_gate.py` then `tools/ntster_h4.py`, the second **refusing to run
   without a recorded F-gate output file**, so "F before the contrast" is enforced
   rather than promised. Between them they implement: dedup by trial key (last wins);
   the §3.1 completeness gate; the fixture-matched join (trial key with the variant slot
   stripped); the paired per-domain difference with t₁₉ / bootstrap CIs at both
   clusterings; unpaired Newcombe as companion; F at pooled AND per-task granularity;
   the §3.3 eligibility classification; the §3.4 labels and vector table; the MDE table;
   and the §3.7 partition. **Forbid `--shard`:** `prompt_variant` is in the shard key
   (`runner.py:647-650`), so any shard split breaks the +3-offset pairing the primary
   depends on. Also: dump each run's ground truth (or per-(domain, problem) hashes of
   `plan` + `trace`) into the cell dir and gate the analysis on those hashes matching
   `results/derived/gt_cache.json` — ground truth is regenerated live every run and
   never persisted (`run_experiment.py:415`; `tools/build_gt_cache.py:5-8`), the cache
   is an untracked Jul-11 artifact with no provenance stamp, and trial rows store no
   plan text, so a live-vs-cache mismatch would be silent and unauditable. Rebuild and
   stamp `gt_cache.json` from the pinned marketplace commit before the run.
   In parallel: Llama parser plumbing + smoke prep (§8 item 11).
4. **[CLUSTER — ping + VPN]** Sync (`sync.sh results/ntster-h4-live`); grade with
   exactly `python3 tools/e2e_regrade.py results/ntster-h4-live --no-mcp` then
   `python3 .claude/skills/analyzer/scripts/table.py results/ntster-h4-live --run-tag ntster-h4 --e2e`;
   run the F gate, then H4. Then the Llama submit + prefix gate.
5. Results memo; manuscript integration under the §5 cap.

---

## 8. Blocking prerequisites

| # | Item | State | Code change + PR? |
|---|---|---|---|
| 1 | `--include-no-tools-steered` plumbed end to end (`run_experiment.py:601 → :472 → runner.py:605 → :667`; wrapper `:170 → :502-503 → sbatch :391-392 → :430`); dry-run produced the array | **DONE** (verified) | No |
| 2 | Steered override fires under `with_tools=False` for v14-16 (`runner.py:288-301`) | **DONE** (verified) | No |
| 3 | Zero pre-existing no-tools steered rows anywhere — 230+ `trials*.jsonl` under `results/`, **plus** `checkpoints/` (byte-identical zip mirrors) and 41 `.local/` files, all v11-13 only | **DONE** (verified 07-25) | No |
| 4 | gemma iss024d wt cell exists (9,120 rows, v11-16) → §4(b) correction | **DONE** (verified) | No |
| 5 | HEAD generation-identical to `6007032`; plugins additive since `5e4f9c0` | **DONE** (verified) | No |
| 6 | Ratify think-mode scope at the **corrected** price | **DONE — Omer, 07-25** | No |
| 7 | Reconstruct the decoupled `think=on` wall and fill the §2.3(B) TODO | **DONE 2026-08-16** — ~132 GPU-h on-mode, ~178 total, inside the ratified band; raises a `--time` question for the 9B on-cell (§2.3(B)) | No |
| 8 | Smoke the `--include-no-tools-steered` production path **and its composition with `--decoupled-budget`** | **SUPERSEDED 2026-08-17 by D3(a)** — not executable as written: `--smoke` is mutually exclusive with `--no-tools`/`--think-modes` (`submit_with_rtx.sh:311-315`) and forces `--num-variants 1`, which is a *prefix* of the variant list, so it can never emit v14-16. The composition unknown was closed locally instead (`runner.py:350` builds `messages` once, then dispatches to the decoupled path at `:399` or the plain path at `:413` — the directive is in the prompt before the branch, so the two flags compose by construction). Residual check = live-smoke on the first rows of the production submit | No |
| 9 | Write + freeze both analysis entry points; record hashes here | **DONE 2026-08-17** — written, rehearsed, frozen at `ff7bbd7`; hashes below | No |
| 10 | Rebuild + stamp `gt_cache.json` from the pinned marketplace commit; add the GT-hash dump/assert | **DONE 2026-08-17** — rebuilt, proven equivalent, stamped; gate = `tools/gt_cache_gate.py`. See below | No (D4(a): no harness edit) |
| 11 | `vllm_lookup` case for Llama (`llama3_json`, `REASONING_PARSER=none`) — without it `submit_with_rtx.sh:341-343` aborts | **TODO** | **YES — branch + PR.** Do **not** append the tag to `PDDL_VLLM_VERIFIED_MODELS` while nt-ster is live (`submit_with_resume.sh:18` expands that array into the submit roster), and do not check the branch out in `$HOME` until every nt-ster cell is terminal — the sbatch sources `lib/defaults.sh` from `$HOME` at run time, so a worktree does not help |
| 12 | Optional `--variants 11,14` pass-through, if the §6 arm spec is honoured literally | **TODO / optional** | **YES — branch + PR**, else accept the ~13,680-trial shape |
| 13 | Optional `status.sh` nt-ster column (~4 lines; it maps `no-tools` → neutral only and prices the cell at 4,560 against 9,120) | **DONE 2026-08-20** — `--ntster` profile; the column was structurally absent, not mispriced (`no-tools` split to neutral with the steered slice discarded) | On `run/ntster-h4`; local ops tooling only, does not touch the pinned apparatus |
| 14 | Confirm ISS-024(b) `guided_json` stays parked through the submit (interpretability precondition for §3.7 M1) | **CONFIRMED 2026-08-16** — see below | No |
| 15 | `llama3_json` registration in vLLM v0.20.2 | **UNVERIFIABLE locally** — read from the serve-flag echo (`sbatch:219`) | No |

**Item 14, in writing (2026-08-16).** ISS-024(b) **stays parked through this submit**;
the fix is not to be applied while nt-ster is live. The $0 audit run the same day
(`tools/guided_json_audit.py`, commit `d10fd15` on `audit/guided-json-iss024b`)
upgraded the §3.7 M1 precondition from an assumption to a measurement: the no-tools
JSON-schema constraint produced conformant output on **526 of 88,781 decidable rows
(0.59%)** across the canonical corpora, with violation shapes impossible under a
working constrained decoder. So `guided_json` does not bind, M1 is interpretable as
written, and the N/A clause in §3.7 is not triggered. Two consequences worth stating:
(i) no with-tools row is affected, so §4(b) is untouched; (ii) because the constraint
is inert in both the May corpora and this run, the anchor arm is not exposed to a
constrained-decoding difference across apparatuses. If the fix were to land before or
during the run it would change the no-tools `solve`/`simulate` generation surface
mid-corpus — which is why it stays parked, not merely deprioritised.

### Preflight record — 2026-08-17 (§7 step 2 SHA requirement, discharged early)

Preflight-only window; **no submit**, per D1(a) in
`development/archive/ntster/ntster_submit_window_decisions.md`.

**Repo SHAs, both sides.** The cluster is sitting on the **literal pin**, not merely on
something generation-identical to it:

| | cluster (`~`) | this worktree | verdict |
|---|---|---|---|
| experiments | `paper/iter2-decoupled-run` @ **`6007032`** | `run/ntster-h4` @ `origin/main` | the pin itself |
| marketplace | `main` @ **`5e4f9c0`** | `main` @ `5e4f9c0` (= tip of `origin/main`) | the pin itself |
| `domains/` tree hash | `8cde5762f74d6acba97e19d3b4a83cdfb946266b` | `8cde5762f74d6acba97e19d3b4a83cdfb946266b` | **identical** |

Both working trees carry **zero** tracked modifications, and `domains/` is clean of
untracked files as well. The identical fixture-tree hash is what converts the D4(a)
ground-truth argument from an assertion into a check: GT is deterministic given the
fixture tree and the oracle plugins, both sides hold the same tree, and
`pddl-solver` / `pddl-validator` / `pddl-parser` are unchanged since `5e4f9c0`.

The §2.3 "generation-identical to `6007032`" claim was re-verified directly: the diff
between `6007032` and current `main` across `pddl_eval/`, `run_experiment.py`,
`cluster-experimenting/`, `domains/` is **three lines, all of them doc-path comments**
(`lib/defaults.sh`, `submit_with_rtx.sh`, `scoring.py`). Zero behavioural delta.

**No pull was performed on the experiments repo, deliberately.** Two reasons: it is
already at the pin, and its branch `paper/iter2-decoupled-run` **no longer exists on
`origin`** (deleted after PR #88 merged), so `scripts/preflight.sh`'s
`git pull --ff-only` would have failed under its own `set -e` and aborted the run before
the venv and capacity phases. The preflight phases were therefore run manually. The
marketplace pull ran and was a no-op.

**Venv refresh — one real apparatus delta, recorded.** Per the standing preflight rule
the two required plugin venvs (`REQUIRED_PLUGINS = ["pddl-solver", "pddl-validator"]`,
`run_experiment.py:122`) were force-refreshed without `--quiet`. Both had drifted, and
inconsistently with each other:

| plugin | `mcp` before | after |
|---|---|---|
| `pddl-solver` | 1.28.1 | **1.29.0** |
| `pddl-validator` | 1.27.2 | **1.29.0** |

`requirements.txt` pins only `mcp<2.0,>=1.27`, so this dependency floats and was never
part of the commit-level pin — the May/July corpora were themselves produced under
whichever version was resident then, and the two servers did not even agree with each
other before today. The bump is a **client/transport** change; the planner and validator
oracles live in the plugin servers, which are pinned by `5e4f9c0`. Both servers were
verified to import cleanly under 1.29.0, and the harness imports cleanly in the run's
conda env (`pddl_copilot`, Python 3.12.13). **This is testable rather than assumed:**
readiness item 10 rebuilds `gt_cache.json` under the new stack, so a diff against the
Jul-11 cache measures directly whether ground truth moved. Recorded here as a stated
apparatus delta either way.

**vLLM image.** The sbatch pins `docker://vllm/vllm-openai:v0.20.2` and will reuse the
cached `$HOME/vllm.sif`. Its version cannot be read login-side (no `apptainer` on the
login node), so §2.3's "verified from the served log header" stays a **run-time** check.
The strongest pre-run evidence: the file's mtime is **2026-05-31 23:26**, unchanged and
predating the July iss024d run, so the same image file served the pinned apparatus.

**Capacity at the time of check:** `rtx6000` 41/44 nodes idle-or-mixed, `rtx_pro_6000`
7/7, and the personal queue is **empty** — no contention for either submit.

### Item 10 record — ground truth rebuilt, proven invariant, stamped (2026-08-17)

Executed under **D4(a)**: cache-only, no harness edit, equivalence carried by the SHA
argument rather than by an in-run dump.

**Rebuilt** with `tools/build_gt_cache.py` against `domains/` (tree
`8cde5762f74d6acba97e19d3b4a83cdfb946266b`, identical on the cluster) and the local
marketplace clone. That clone's HEAD `f0e2c61` sits 2 additive commits past the pin, but
**both oracle plugin subtrees hash identically to `5e4f9c0`** — `pddl-solver`
`2ece6ce0…`, `pddl-validator` `b090092c…` at both commits — so this **is** a build from
the pinned marketplace commit for ground-truth purposes. `REQUIRED_PLUGINS` is exactly
those two (`run_experiment.py:122`). Output: 20 domains / 100 problems / 60 negative
fixtures.

**Result: ground truth has not moved.** The rebuild was diffed against the unstamped
Jul-11 cache (preserved at `results/derived/gt_cache_20260711.prestamp.json`). Excluding
one field, the two are **exactly equal** — canonical
`6af57125bde3ec2bb7262b4db23449e2b504f0c721c4412f8eb1151f744ca945` on both sides. This
also settles the preflight's open question: **the `mcp` bump did not perturb ground
truth**, and neither did five weeks nor the two additive marketplace commits.

**The one difference, and why the gate is not a file hash.** Whole-file sha256 differs
while byte-length is identical to the byte. The cause is `domain_validation_raw`, which
serializes the validator's `[WARNING]` lines in a **process-dependent order** — verified
across all 100 problems as an identical warning multiset in a different order. The field
is written at `pddl_eval/domains.py:174` and **read by no grading code** (single grep hit
in `pddl_eval/`, `tools/`, `run_experiment.py`). So a naive file-hash gate would
false-alarm on every rebuild and would eventually be disabled by whoever hit it — the
classic way a safety check dies. The gate is instead a canonical hash over every
grading-visible field, excluding that diagnostic.

**Stamped** at `results/derived/gt_cache_stamp.json`: builder blob SHA, both repo SHAs,
the `domains/` tree hash, both oracle subtree hashes at HEAD and at the pin, the plugin
venv `mcp` versions on both laptop and cluster, the gate value, and the equivalence
result. **Enforced** by `tools/gt_cache_gate.py`, which both frozen analysis entry points
(item 9) call via `assert_gate()` before reading any trial — so "the analysis ran against
the pinned ground truth" is checked, not promised. Verified passing.

### Item 9 record — analysis entry points FROZEN (2026-08-17)

Frozen at commit **`ff7bbd7`** on `run/ntster-h4`. sha256:

| file | sha256 |
|---|---|
| `tools/ntster_f_gate.py` | `2ebb92f16481263940ac03d7658b34e8e560fd76f40dc8194159cef31471aa6e` |
| `tools/ntster_h4.py` | `0541ad8e9fab62d2c483b2e589782d6f2dea56948dcb322e794d348ade6534e9` |
| `tools/ntster_common.py` | `a7bc6093f711666c744f9b2fa9ffb62bec69b37e64ae43184e529a37e3e822f4` |
| `tools/gt_cache_gate.py` | `db78f3623a534ccbd26989c2fb29e14777193933106d40e1b2ae40e3fcd8057b` |

Four files, not the two §7 step 3 names, and the reason matters: the shared core and
the GT gate are **inside** the frozen boundary. Splitting them out and leaving them
mutable would reproduce exactly the loophole freezing exists to close. For the same
reason nothing imports from `.claude/skills/analyzer/` — a frozen analysis that imports
a live module is not frozen.

#### Item 9 addendum — §4(b) entry point FROZEN (2026-08-29)

| file | sha256 |
|---|---|
| `tools/ntster_factorial.py` | `78787eb7f3ba671773d695f8b2904bbe5edcef559297c76f8f35fe1211629164` |

**This one was written after the H4 verdict was known, and that must be stated rather
than smoothed over.** The §4(b) estimand was locked in the ratified prereg before any
data existed, but the code implementing it did not exist until 2026-08-29, because until
the on-mode rerun landed the factorial had no nt legs to run against. Writing analysis
code after seeing a result is the ordering §8 item 9 exists to prevent.

The mitigation, approved by Omer as final-readout O3, is the item 9/10 protocol applied
after the fact: **write it, freeze it, hash it here, and only then point it at data.**
The freeze commit precedes the first real invocation in the git history, so the ordering
is checkable rather than asserted.

Enforcement matching the other entry points: it calls `assert_gate()` before reading any
trial; it runs the §3.1 completeness gate on both legs of every model; it derives its
roster from which legs exist rather than taking a `--models` flag; and it exposes no
`--margin`, `--alpha`, `--surface`, `--sign` or `--shard` flag, each of which would turn
a design commitment into a run-time choice. The May reference sign is **computed from
the canonical corpus**, not hardcoded, so it cannot drift from a number typed into a
docstring. It reuses the frozen `ntster_common` §3.3 interval machinery unchanged.

**Rehearsal before freeze:** run with both `--nt-overlay-dir` and `--wt-overlay-dir`
pointed at the same directory, which forces the interaction to exactly zero for every
fixture by construction. This exercises loading, the fixture join, both clusterings, the
seeded bootstrap, the verdict logic and both output writers against a mathematically
known answer, while leaking nothing about the real estimate. Result: `+0.00 [+0.00,
+0.00]` on both models, 4,560 matched fixtures each, 0 dropped, roster correctly resolved
to the two Qwens.

**Enforcement, not documentation.** `ntster_h4.py` refuses to start without the F-gate
JSON; refuses when that JSON names a different overlay corpus than the one passed;
and calls `assert_gate()` before reading any trial. There is no `--margin`, `--alpha`,
`--surface` or `--shard` flag — each would be a design commitment turned into a run-time
choice, and `--shard` additionally breaks the +3-offset pairing because `prompt_variant`
is in the shard key (`runner.py:647-650`).

**Coverage.** Between them the four files implement: dedup by trial key (last wins); the
§3.1 completeness gate incl. the `snapshot_cap == 16384` assertion; the fixture-matched
join on the trial key with the variant slot stripped; the paired per-domain difference
with t₁₉ and domain-clustered bootstrap (B = 10,000, seeded) at **both** clusterings with
the wider governing; unpaired Newcombe as companion; F at pooled and per-task
granularity; the §3.3 eligibility classification incl. the LOW-BASE-RATE risk-ratio
bound; the §3.4 labels, verdict vector and paper-level branch table; Holm over the
ELIGIBLE family only; the MDE table; and the §3.7 four-way partition with M1/M2, the
ceiling and APPARATUS guards, the dominance label rules and the help-direction Spearman.

**Rehearsed before freezing** against `results/derived/e2e_overlay/iss024d-e2e-live`,
which carries the same 9,120-row six-variant shape these cells will have. **Code
correctness only — that corpus is with-tools, so its numbers are the H2 effect and not
this control; nothing from the rehearsal may be read as an H4 result.** What it
established: the completeness gate passes exactly on all five cells, and the mechanism
partition reproduces the ΣΔ = −Δ̂ identity to **0.000pp in every cell**. All five failure
paths were exercised deliberately — missing F gate, corpus mismatch, GT divergence,
incomplete cell, empty granularity — and each refuses or degrades correctly rather than
producing a number.

Two defects the rehearsal caught and fixed before the freeze: the identity check was
comparing against the governing interval rather than the domain-clustered Δ̂ the
components are computed on, showing a spurious residual whenever problem clustering was
wider; and a granularity with zero rows rendered as `usable`, which would have let a
silent shortfall read as a pass.

#### Item 9 second addendum — post-review corrective RE-FREEZE (2026-08-30)

**Every hash in the two tables above is superseded by the table below.** A
15-finding correctness review of PR #96 (posted as inline comments on the PR,
2026-08-30) found defects in the frozen analysis code — the material ones are
declared as deviations in §9.2, with the latent ones that never fired listed
there too. Each fix edits hash-frozen files, so per this document's own
protocol the full five-file set was re-frozen and re-hashed here, and only then
was the analysis re-run.

| file | sha256 (2026-08-30) |
|---|---|
| `tools/ntster_f_gate.py` | `e9b746b74ab725359077175ed54d77eebf1bedaba63523fa395d22a21d01d200` |
| `tools/ntster_h4.py` | `272f96b9f9ea20b3398afeb4a7c849a990e6c705149f9ffb2821c199cba67c26` |
| `tools/ntster_common.py` | `49d869f39fc59fa875554c06e3e17937823abd8cabb852a028296a72cfb71ed7` |
| `tools/gt_cache_gate.py` | `1181781e674f212c7d62c4fcdb6d50eb7ee9e650887d8e2bd95937609d8f3897` |
| `tools/ntster_factorial.py` | `16f03b59e3e480f79639acf7117eb5c1bf630760951d37747d955388294ea40c` |

**The ordering caveat, stated rather than smoothed over.** Unlike the original
freeze, these edits were written after the data and the verdicts were known.
The mitigations are: every change is tied to a named finding of an external
review, not to anything seen in the numbers; every behavioural change is a
mechanical correction *toward* the already-registered design (§2.3(C), §3.2,
§3.3 points 2–3, §3.4, §3.7, §8 item 10), never a new analyst choice; and both
the pre-fix and post-fix code and outputs are in git, so the entire delta is
auditable. The re-run reproduces the six-unit all-PASS verdict vector and the
paper-level PASS branch unchanged; the secondary numbers moved and the final
readout was revised in place (`ntster_h4_final_readout_20260829.md`, revision
note at top).

---

## 9. Known limits, carried into Limitations

1. **The whole `think=on` no-tools single-call apparatus is unrun**; every `think=on`
   projection here is extrapolated across a snapshot or budget-mechanism boundary. The
   co-run anchor is what makes this survivable; the projections are indicative only.
2. **No non-Qwen `think=on` control exists** (§2.3(B) scope note).
3. **Cross-apparatus transfer to the May +72pp is not purchased.** H4 is internally
   valid within July; the step to May remains a drift argument, and job-level parity
   between the apparatuses already FAILED.
4. **The control is conservative by construction** (§3.5), so a PASS is weaker evidence
   than an unqualified reading would suggest.
5. **Serving nondeterminism at T=0 is unbounded** by our corpora. A within-run
   byte-identical duplicate variant would measure it at +1,520 rows/cell and a
   `prompts.py` edit — not recommended for this run, and it cannot be added after
   unblinding.
6. **Queue wait** is excluded from every wall estimate, and six simultaneous
   `rtx_6000` grants would be one above observed precedent (the split submits reduce
   this to 3 + 2).

### 9.1 Executed deviations from this prereg — declaration (2026-08-29, O1)

Approved by Omer as final-readout O1. Both belong in the paper appendix, in the same
paragraph, stated plainly rather than presented as the original design. Appendix-ready
text follows; it is deliberately written so a reader can see what was changed, when,
relative to what knowledge, and which direction the change pushes the conclusion.

> **Deviation 1 — the control roster was expanded from three models to four after
> interim results were seen.** The preregistration fixed the H4 roster at Qwen3.5:9B,
> gemma4:26b-a4b and qwen3.6:35b. On 2026-08-22, with the three `think=off` units
> complete and passing, we measured the with-tools steering effect the control exists to
> attribute across the full five-model roster and found that Qwen3.5:4B carried a larger
> effect (+6.9pp pooled, +9.6pp on `validate_plan`) than Qwen3.5:9B (+2.5pp), which was
> controlled, while having no control of its own. Qwen3.5:0.8B showed no effect (+0.0pp
> pooled) and so has nothing to attribute. We added a Qwen3.5:4B `think=off` control
> rather than argue the asymmetry away. It was submitted with apparatus parity to the
> three completed `think=off` cells and it PASSES. The deviation is conservative in a
> checkable sense: under the intersection-union rule a fourth unit can only make the
> conjunctive equivalence claim harder to satisfy, never easier. It is not model
> selection — no unit was dropped, and the added unit was chosen by the size of the
> effect needing attribution, not by its control result, which was unknown at submit
> time.
>
> **Deviation 2 — the `think=on` arm was rerun with `--reasoning-parser none`, against
> the preregistered configuration.** The preregistration ruled that the reasoning-parser
> override is not passed. Applied to the decoupled two-call apparatus that the `think=on`
> legs use, that configuration produced a void corpus: 9,120/9,120 and 3,822/3,824 rows
> with empty response text, no errors, and ~12,960 tokens generated per row. The cause is
> that the preregistered rule was reasoned about the single-call path, where reasoning
> and answer share one output stream, while the decoupled path generates the answer in a
> separate call and had only ever been validated with the parser off. We cancelled the
> arm, discarded the void rows, and reran with the parser off. The rerun reproduces an
> independent parser-off corpus from June to within a percentage point on both empty-text
> share and success rate, and the grading artifact the original rule was written to
> prevent does not appear on this path (`format_parse_fail` is 0.0% on all three
> validation tasks in all four affected arms). The two think modes were already declared
> different apparatuses whose numbers may not be compared across the mode axis, and they
> were already separate submissions, so the change alters no cross-mode comparison. The
> void arm is reported here rather than omitted; the discarded corpus is retained.

### 9.2 Post-review code deviations — declaration (2026-08-30)

A correctness review of PR #96 (15 findings) audited the frozen analysis code
after the ratified readout shipped. The fixes below all edit hash-frozen files;
they are declared here and the files re-frozen (§8 item 9, second addendum)
before the analysis was re-run. **The six-unit verdict vector and the
paper-level branch are unchanged by every fix — all six units PASS.** The
secondary numbers changed; the revised values live in the final readout and
`NUMBERS.md`. Appendix-ready prose:

> **Deviation 3 — censored rows were counted as delivered successes and fed to
> the estimator.** The overlay's delivered grade is tri-state (`true` / `false`
> / `"indeterminate"` for rows censored at the 16K snapshot cap); the frozen
> `delivered()` used a truthiness test, so `bool("indeterminate")` scored every
> censored row as a success in the arm rates, the paired TOST, the F gate, the
> eligibility anchors, and both factorial legs — and, separately, the
> §2.3(C)/§3.7 commitment that censored rows are excluded and reported as
> bounds was not implemented at all. Both were fixed on 2026-08-30: the grade
> is now an identity test, indeterminate rows are excluded from every
> estimator and denominator, and each contrast reports censored counts plus
> extreme-imputation bounds on Δ̂. Direction: the shipped `simulate` rates were
> inflated (4B anchor `simulate` 41.7% as shipped vs 17.1% determinate); the
> shipped 4B `simulate` −14.00pp cell — the family's only NOT-EQUIVALENT label
> — was largely this artifact and reads −2.43 [−5.33, +0.47] INDETERMINATE
> after the fix. No unit verdict moved.
>
> **Deviation 4 — the "problem (k=100)" clustering was neither k=100 nor an
> estimator of the paired difference.** The registered description assumed 100
> balanced problem clusters; the realized fixture layout yields 220 unbalanced
> ones (the 100 shared problems carry 42 pairs each, 120 single-task fixtures
> carry 3), so the unweighted mean of cluster means gave 7.9% of rows 55% of
> the weight and estimated a task-reweighted quantity — and it was the wider,
> therefore governing, interval in all six cells and both factorial models.
> Fixed: the problem clustering now uses a size-weighted cluster-robust
> interval whose point estimate is the registered paired difference, and every
> interval label carries its realized k. The domain clustering — the
> registered primary — is estimated exactly as registered. Direction:
> governing intervals tightened (realized MDE 5.82–6.25pp against the shipped
> 6.47–7.11), which can only make the equivalence test harder to pass, and all
> six units still PASS.
>
> **Deviation 5 — task-cell eligibility was classified on the governing
> half-width; §3.3 point 3 pins it to the realized domain-clustered
> half-width.** Fixed. On this corpus the ELIGIBLE family is identical under
> both readings (the same 8 cells), so nothing moved; the defect was
> anti-conservative in principle because a wider governing interval could
> screen a NOT-EQUIVALENT cell out of the FAIL veto.
>
> **Deviation 6 — the §3.7 mechanism section read row fields the overlay never
> carries and was degenerate in all six cells.** `failure_reason`, `response`
> and `tokens` live in the raw `trials.jsonl`, not the overlay, so every
> failed row fell through to APPARATUS (13.75–36.01% per arm), all six
> mechanism reads self-VOIDed on the 1% guard, and the shipped report told an
> apparatus-failure story that was an artifact of reading absent fields.
> Fixed: the entry point joins each overlay row to its raw trial row
> (`--trials-dir`) and computes the partition from the fields the prereg
> actually names. Re-run: APPARATUS is 0.00% in every arm, the VOID guard does
> not fire, the ΣΔ = −Δ̂ identity closes to 0.000pp in every cell, and no
> mechanism label is owed because no unit FAILs.
>
> **Deviation 7 — the legacy consistency surface read a key no overlay row
> has** (`success` instead of `success_stored`), so it was constant False and
> §3.1's "real second measurement on `simulate`" measured nothing. Fixed; the
> legacy column now reports the stored online grade on every row.
>
> **Deviation 8 — latent verdict-path defects, none of which fired on this
> corpus, fixed for any future run:** the pooled F gate is now enforced in the
> unit verdict (§3.2's "F ≥ margin ⇒ UNINFORMATIVE, never rescued" had been
> recorded but never consulted); a pooled-driven unit FAIL now routes to the
> §3.4 FAIL branch instead of the MIXED branch (the pooled primary can never
> be "ineligible"); the §4(b) factorial refuses to analyse a leg that fails
> the §3.1 completeness gate and refuses duplicate or ambiguous overlay cells
> instead of silently taking the last one; the LOW-BASE-RATE risk-ratio path
> no longer crashes on a steered arm with zero successes; and an overlay
> carrying no `snapshot_cap` at all now fails the completeness gate instead of
> passing as verified.
>
> **Deviation 9 — provenance-enforcement gaps closed, and one registered
> quantity restored.** `ntster_f_gate.py` now calls the GT gate before reading
> any trial — the §8 item 10 record claimed both entry points did, which was
> false for this one from the original freeze until 2026-08-30. The GT gate
> now also compares the cache against the preregistered canonical hash
> (`6af57125…`) as a code constant, so a rebuilt cache with a self-consistent
> fresh stamp can no longer pass; the stamp itself is committed to the repo;
> `scipy`/`numpy` are declared in `requirements.txt`. And the §3.3 point 2
> companion — the unweighted mean over ELIGIBLE task cells, with a pooled-PASS
> disagreement reported rather than resolved — is now computed and reported;
> it is consistent with the pooled read in all six units.

**Consequence for §4(b), restated.** The clause verdict remains **DROP**, but
its basis changed and the old narrative ("neither interaction excludes zero,
an underpowered null") is superseded: on the corrected surface both
interactions are positive and exclude zero (9B +8.12 [+4.61, +11.63],
replicated; 35b +2.62 [+0.74, +4.50]), and the clause drops only because 35b's
May reference effect is −0.11pp — an essentially null reference whose sign
cannot meaningfully be matched. The corrected factorial is directionally
consistent with the attribution in both models; the pre-registered criterion
is applied as written and the clause stays out.

---

## 10. Ratification

Slot answers are filled per Omer's acceptance 2026-07-25. Signing below confirms the
design, the corrected price, and the two scope items called out explicitly.

**RATIFIED by Omer 2026-08-11**, in session, via decisions R2 ("ratify") and R3
("keep as sequenced") in `development/STATUS.md`. All four lines
below are signed by that answer. Price in hand at the time of signing: the accepted
shape costs **~46 GPU-h (`think=off`, 3 models, plain) + ~110-150 GPU-h (`think=on`,
9B + 35b, decoupled) ≈ 156-196 GPU-h total**, against the memo's obsolete ~92. The
on-mode half is still an estimate until §8 item 7 (the decoupled-wall reconstruction
from `results/decoupled-rollup/*decoupled-thinkon/trials.jsonl`) lands; that item is
local and runs before the submit ping. The R2 slot as annotated quoted the
plain-apparatus both-modes figure (~186 GPU-h) — same order, different shape; the
line above is the accurate one and no scope changed between them.

> RATIFY (nt-ster + anchor design and analysis, §1-§5):
> RATIFIED — Omer, 2026-08-11 (R2).

> RATIFY (§2.3(B) scope note — `think=on` covers Qwen3.5:9B + qwen3.6:35b only; gemma
> has no `think=on` control leg):
> RATIFIED — Omer, 2026-08-11 (R2). Limitations owes the one sentence the scope note
> requires: no non-Qwen `think=on` control exists, because gemma's `think=on` no-tools
> cell is 90-100% cap-saturated under every apparatus available to us.

> RATIFY (§2.3(A) — the `--reasoning-parser` element of the D-J5 pin is dropped for the
> no-tools cells as a measurement-validity correction, not a scope change):
> RATIFIED — Omer, 2026-08-11 (R2).

> RATIFY (Llama probe spec + kill-gate, §6, at the ~13,680-trial executable shape):
> RATIFIED — Omer, 2026-08-11 (R3: keep as sequenced, strictly after nt-ster lands).
> The ~13,680-trial shape is accepted; the `--variants` pass-through (§8 item 12) is
> not authorised, so no flag selects {v11, v14}.

**What ratification unblocks and what it does not.** The design is now frozen; the
submit is still gated on (a) the §8 readiness items that must precede it — item 7
(decoupled-wall reconstruction), item 9 (freeze both analysis entry points), item 10
(rebuild + stamp `gt_cache.json`), item 14 (confirm ISS-024(b) `guided_json` stays
parked) — and (b) Omer's explicit go-ahead plus a VPN window, per the standing
cluster rule.

> **STATUS 2026-08-17 — all four pre-submit readiness items are CLOSED.** Item 7
> measured (~178 GPU-h total, inside the ratified band); item 14 confirmed in writing
> and now backed by measurement; item 10 rebuilt, proven invariant and stamped; item 9
> written, rehearsed and frozen at `ff7bbd7`. Preflight is done and the cluster is
> verified sitting on the literal pin. **The submit is now gated only on (b)** — Omer's
> go-ahead plus a VPN window. Item 8 (smoke) is superseded by the live-smoke decision
> (D3(a) in `ntster_submit_window_decisions.md`): the wrapper cannot express the
> smoke the prereg asked for, its riskiest unknown was closed locally instead, and the
> residual check runs against the first rows of the production submit. The on-mode
> `--time` is **7 days**, not the 5 in §7 step 2, per D2. Item 11 (`vllm_lookup` case for Llama) is needed only for the §6 probe
and carries its own branch + PR; it must not append the tag to
`PDDL_VLLM_VERIFIED_MODELS` while nt-ster is live.

### Live-smoke record — the run is emitting the control arm (2026-08-20)

Submitted: **job 20392775** (off-mode, 3 tasks, `--time 5-00:00:00`) and **job 20392801**
(on-mode, 2 tasks, `--time 7-00:00:00`, per D2). Both `TimeLimit`s verified at submit.
Preconditions re-checked immediately before each submit: HEAD `6007032`, clean tree.

This closes the §8 item 8 residual, which D3(a) deferred to the production submit
because the wrapper cannot express the smoke the prereg asked for.

**(1) The steered arm exists on disk.** First time the
`--include-no-tools-steered` production path has ever produced data. All six variants
present, and `with_tools=False` on **100%** of rows in every cell:

| cell | n | variants seen | with_tools |
|---|---:|---|---|
| `gemma4:26b-a4b` off | 14 | 11,12,13,14,15,16 | all False |
| `qwen3.6:35b` off | 13 | 11,12,13,14,15,16 | all False |
| `Qwen3.5:9B` off | 5 | 11,12,13,14,15 | all False |
| `qwen3.6:35b` on | 4 | 11,12,13,14 | all False |

Variants interleave rather than running arm-by-arm, as §7 predicted from the emission
order — so both arms fill together and a partial cell is never all-anchor.

**(2) The untested flag composition works at runtime.** `--include-no-tools-steered` ×
`--decoupled-budget` had never been run, and §8 item 8 called it unverified. A steered
row on the decoupled path:

```
v14 solve  turns=2  think_tok=8192  answer_tok=4768  call2_prompt=2049  done=stop
```

`turns=2` is the two-call continuation; `think_tok` is exactly the
`--num-predict-think 8192` passed; the answer phase draws its own separate budget
(4,768-8,192 across the first rows) rather than sharing one; `call2_prompt≈2,040`
confirms the think block is re-injected. The code-reading argument in §8 item 8 is now
a measurement.

**(3) The apparatus pin holds where it can be seen.** The serve flags in the job log are
`--tool-call-parser qwen3_xml --reasoning-parser qwen3` — the **per-model default**, not
`none`. §2.3(A) is the correction that mattered most (parser-off would have
re-manufactured the `simulate` grading artifact on a no-tools cell), and the run went out
with it applied. GPU confirmed as `NVIDIA RTX 6000 Ada Generation, 49140 MiB`; the
allocation is `gres/gpu:rtx_6000=1` per task. Node names of the form `ise-cpu256-*` are
GPU nodes on this cluster despite the name — checked, not assumed.

**(4) Served vLLM version — §2.3(D), CLOSED 2026-08-20.** Read live from the engine
banner inside the running allocation:

```
Initializing a V1 LLM engine (v0.20.2) with config: model='Qwen/Qwen3.5-9B', ...
```

**v0.20.2**, matching the pinned `docker://vllm/vllm-openai:v0.20.2`. This is the check
§2.3 said had to be *verified rather than asserted*, because `$HOME/vllm.sif` is a
mutable shared cache that could have been rebuilt by any session: the cached image
genuinely contains the pinned version, so the apparatus matches iss024d's.

Getting it required a detour worth recording for the next run: the serve log is written
to the compute node's scratch (`/scratch/omereliy/<jobid>/vllm-work/vllm-<model>.log`),
**not** the `/tmp/vllm-<jobid>` path the sbatch's primary branch suggests, and it is only
copied back to `cluster-experimenting/logs/` by the EXIT trap — so it is unreadable from
the login node mid-run, and lost entirely if a job is hard-killed before the trap fires.
Compute-node SSH is key-denied; `srun --overlap --jobid=<task>` is the working idiom.

**HF weight revision remains unpinned and unreported** — the engine config line names
`model='Qwen/Qwen3.5-9B'` with no revision field, since the sbatch serves without
`--revision`. Recorded as absent rather than guessed; per §2.3(D) weight vintage stays a
stated component of the drift term.

VRAM after load on the 9B cell: 40,758/49,140 MiB (**82%**), under the `> 85` abort
guard. gemma is the cell to watch there, not this one.
