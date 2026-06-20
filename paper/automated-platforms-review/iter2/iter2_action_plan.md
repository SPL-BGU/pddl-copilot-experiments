# Iter 2 — Action Plan & Decision Sheet (annotate inline)

Triage of the two iter-2 Stanford reviews (both **ACCEPT**), grounded by four exploration
subagents that read the actual trial records, grader code, plugin schemas, paper source, and
web-verified venue dates. Mark your decisions in the `DECISION` blocks (check a box, add notes).

**How to annotate:** put an `x` in the box you choose, e.g. `- [x]`, and jot notes after `_notes:_`.

---

## Bottom line

Both reviews recommend ACCEPT → this is **acceptance-probability maximization**, not a rescue. Of 16 asks:

- **~10 are writing-only** — already on-record in `main.tex`, or a free analysis win.
- **2 are genuinely worth new compute** (both raised by *both* reviews, both attack a headline
  claim, both cheap): the `simulate` compressed-diff probe **[5b]** and the schema-salience
  probe **[6]**.
- **1 is a trap** — folding in a BF16 number **[2]** would *contradict* the recorded "sweep7
  discarded entirely" decision.
- **1 is further along than the synthesis assumed** — frontier *with-tools* pilot data **[1]**
  already exists on disk (Haiku ≈100%), but the Sonnet `solve`/`simulate` zeros look like the
  JRE/host artifact that bit sweep7 and must be verified before quoting.

---

## The 16 asks — master decision table

| # | Ask | Recommendation | Effort | Why (1-line) |
|---|-----|----------------|--------|--------------|
| 9 | FWER correction | **CLOSE-NOW (free)** | writing | √2.7 design-effect inflation already gives effective z=3.22, which *dominates* Bonferroni for ≤30 contrasts; every headline gap stays disjoint. Just say so. |
| 5a | `simulate` partial-credit | **CLOSE-NOW (offline)** | analysis/writing | 97% of unaided trials never emit a parseable trajectory; the 3% that do are *all wrong*. Nothing to partial-credit — that *is* the answer; reproduces `main.tex:629`. |
| 8 | think=on budget decoupling | **CLOSE-NOW (done)** | writing | Defense already in Limitations (`main.tex:940-944`); failed-pilot rationale already on the page. |
| 12 | Cost realism | **CLOSE-NOW (1 sentence)** | writing | $-estimate, latency-unrecoverable, ~90% caching all present; only the "production could skip re-feeding tool outputs" sentence is missing. |
| 2 | Quantization / BF16 | **CLOSE-NOW via within-model reframe — do NOT fold a BF16 number** | writing | ⚠️ Folding BF16≈AWQ contradicts the "sweep7 discarded" decision + surfaces uncommitted, matrix-mismatched data. Keep `main.tex:957-963`. |
| 13 | Reproducibility detail | CLOSE-NOW | writing | Expand HW/SW stack + tool-call iteration stats. |
| 14 | Related-work head-to-heads | CLOSE-NOW | writing | Situate vs ReAct / PlanBench / RLHF-on-propensity; the RLHF-propensity angle is genuinely new. |
| 16 | Practitioner exec summary | CLOSE-NOW | writing | One boxed effect-size summary; NeurIPS asked. |
| 3 | Matched-prompt ablation | Limitations note | writing | Already disclosed; a clean-prompt probe is cheap but lower-priority than 5b/6. |
| 4 | Steering-sentence ablation | DEFER-future | writing | Effect already large + mechanism-backed; not convergent enough to fund. |
| 7 | Multi-tool / agentic | DEFER-future | writing | Scope = the *second* paper. |
| 10 | Fine-tuning / constrained decoding | DEFER-future + honest framing | writing | Forced decoding makes P(call)=1 *by construction* — a category error vs the question. Fine-tuning out of harness for the deadline. |
| 15 | Richer PDDL fragments | DEFER-future | writing | Temporal/durative out of scope. |
| 11 | Temperature sensitivity | **RUN cheap *or* DEFER** | compute | NeurIPS-only; needs a ~3-line vLLM `seed` fix + k=3 draws. Most droppable. |
| **6** | **Schema salience / verbosity → P(call)** | **RUN cheap probe** | compute | **Cheapest high-value win.** 3 cells, 1 model (Qwen3.5-9B), validate_plan, tool-available. Answers "why under-call"; token cost free from existing accounting. |
| **5b** | **`simulate` compressed-diff schema** | **RUN cheap probe** | compute | **Highest scientific leverage.** ~900 trials, 1 model, no-tools only; tests whether the 0% is JSON-verbosity or genuine state-tracking. ~0.5-1 day code. |
| 1 | Frontier *with-tools* | **SURFACE existing pilot (after verifying Sonnet zeros)** | data + writing | Pilot exists (`results/frontier-with-tools-probe/`); Haiku ≈100%. Verify Sonnet `solve`/`simulate`=0 isn't the JRE artifact before quoting. |

---

## The writing-only batch (no decision needed — these just get done)

Once the decisions below are set, these land in a single `main.tex` pass (parallels the iter1
"CLOSE NOW APPLIED" pass):

- **[9] FWER** — 2-3 sentences: the already-applied √2.7 inflation ⇒ effective z=3.22 > Bonferroni
  z for a family of ≤30 contrasts, so the headline verdicts are FWER-robust by construction.
- **[5a] `simulate` partial-credit** — surface the failure-mode decomposition (68% format-parse-fail,
  29% truncated, ~3% parseable-but-wrong; only 26/900 ever produced a gradeable trajectory and all
  were wrong) as the *direct answer* to "exact-match understates near-correct reasoning."
- **[8] think=on budget** — already in Limitations; at most one clause pointing the reviewer to it.
- **[12] Cost** — add the single missing sentence (a production system could summarize / not re-feed
  tool outputs, so reported cost-of-pass is a worst-case not a deployment-optimal figure).
- **[2] Quantization** — keep the existing within-model reframe; do **not** add a BF16 number (see ⚠️ below).
- **[13] Reproducibility / [14] Related work / [16] Exec summary** — additive writing.
- **[3] matched-prompt / [4] steering / [7] multi-tool / [10] fine-tuning / [15] richer PDDL** —
  Limitations + Future-Work framing (10 gets the "forced decoding ≠ raising P(call)" honest note).

---

## ⚠️ DECISION A — the BF16 trap (please confirm)

The iter2 synthesis *suggested* folding in "BF16 ≈ AWQ" evidence. The verification agent found this
**contradicts your recorded decision** ("sweep7 is entirely discarded", iter1 2026-06-18) and would
surface uncommitted, matrix-mismatched data as if publication-grade.

> **DECISION A:**
> - [X] **Keep the within-model reframe only** (recommended) — answers the reviewer by not relying
>       on the cross-precision comparison; no new claim, no decision reversal.
> - [ ] **Reverse the discard** and run a clean BF16 column — this is a *new decision*, needs the
>       data committed + the `solve` re-enumeration bug fixed first.
>
> _notes:_ we can run another sweeep on cluster. is it better? perhaps we can benefit from the reviews by making a fixed sweep or reimplementing it to address the weaknesses.

---

## DECISION B — Venue (sets the whole compute timeline)

Web-verified by the strategy agent. The community norm is **conference now → JAIR/AIJ extended
version later** (the extension is the natural home to unify this paper + the planned PlanBench
paper). "Journal instead of conference" is advised against: forfeits priority on a fast-moving
topic when two ACCEPTs say it's publishable today.

| Option | Deadline (rel. to 2026-06-20) | Trade-off |
|---|---|---|
| **AAAI-27 Main** | abstract Jul 20 / full **Jul 27** (~5 wks) | Fastest, broadest reach, ACCEPT-validated. Tight: room for only the cheapest probe(s). |
| **ICAPS-27** | ≈ **Nov/Dec 2026** (est., CFP not yet posted) | The *planning-native* venue; buys ~4 months to land 5b+6+11 + verify frontier pilot. |
| **Conf now + JAIR/AIJ extension** | hybrid | Commit explicitly to the extension as the home for all deferred asks + the 2nd paper. |
| **Journal-first, discard conf** | — | Advised against (forfeits priority, front-loads months of compute before any pub). |

> **DECISION B:** *(you indicated AAAI-27 — confirm or revise)*
> - [X] **AAAI-27 now (Jul 27)** — tight timeline; only cheapest probe(s) fit.
> - [ ] **ICAPS-27** (more time for probes).
> - [X] **Conf now + committed JAIR/AIJ extension** (compatible with AAAI *and* ICAPS).
> - [ ] **Journal-first, discard conference.**
>
> _notes:_ not committing to a journal yet but keepng this path as optional only.

---

## DECISION C — New compute before the deadline

The constraint is **deadline + the shared cluster** (the frontier with-tools probe already draws
budget). Per-dimension scorecard for the three candidate probes:

### [6] Schema salience / verbosity → P(call)   ·   raised by BOTH   ·   NEW

| Dimension | Assessment |
|---|---|
| **Correctness** | Valid + high-leverage. The tool description/schema is the *one input the paper never varied*; either result strengthens the paper (lifts P(call) ⇒ interface artifact; or barely moves ⇒ sharpens "model-policy, not legibility"). |
| **Feasibility** | Excellent. Add a harness-side schema transform mirroring the existing `_strip_verbose_from_schema` (`chat.py:98-149`) + a `--schema-variant` flag. No plugin/marketplace edit. Do **not** rename the tool (scoring matches on name). |
| **Dev time** | ~3-5 hours (2 transforms + flag + provenance log + 1-trial smoke). |
| **Cost vs value** | Minimal compute: 3 cells (baseline/terse/salient), 1 model (Qwen3.5-9B), validate_plan, tool-available, think=off (~a few hundred trials). Token cost reported *free* from existing accounting. Both reviewers; central mechanism. **Best ROI.** |

### [5b] `simulate` compressed-diff schema   ·   raised by BOTH   ·   NEW

| Dimension | Assessment |
|---|---|
| **Correctness** | Sharpest *open* question: is the unaided 0% driven by JSON verbosity blowing the budget (29% truncated) or genuine state-tracking failure? A delta-schema (emit per-step add/del only) is the clean control both reviews asked for. |
| **Feasibility** | Needs NEW inference (cannot be offline — stored `response` is capped at 500 chars). Add a `SimulateDeltaResponse` schema + a grader branch that reconstructs states then reuses `_normalize_trajectory`. Self-contained. |
| **Dev time** | ~0.5-1 day code + a minimal sweep. |
| **Cost vs value** | Cheap: no-tools `simulate` only, 1 model (the 35B, the only one that ever parsed), ~900 trials, no tool servers. Turns a defensive footnote into a positive result. **Highest scientific leverage.** |

### [11] Temperature / stochastic-decoding sensitivity   ·   NeurIPS only   ·   defensive

| Dimension | Assessment |
|---|---|
| **Correctness** | Valid but defensive — inoculates against a "P(call) is a temp-0 knife-edge artifact" objection. |
| **Feasibility** | Mostly a flag flip; one real gap — no sampling `seed` reaches vLLM (`vllm_client.py:137-161`), so temp>0 is non-reproducible without a ~3-line fix + k≥3 draws. |
| **Dev time** | ~2-4 hours (seed plumbing + small repeat-sampling loop). |
| **Cost vs value** | Low-moderate compute × k draws. Value is robustness, not a new finding. **First to cut.** |

**Priority if compute is tight:** [6] → [5b] → [11].

> **DECISION C:**
> - [ ] **Both [6] + [5b]** — the two both-reviews, headline-attacking probes (recommended if any
>       compute at all; ~1 day code total).
> - [ ] **Only [6]** — cheapest high-value win alone; defer 5b + 11.
> - [ ] **All three (+[11])** — only if the ICAPS timeline gives the room.
> - [ ] **None — writing only** — defer every probe to the journal extension (safest for Jul 27).
>
> _notes:_ go forr both 6 and 5b starting with 6 and then seeing if 5b is easy. resolving it with two phases.

---

## DECISION D — Frontier with-tools pilot data [1]

Pilot data already on disk in `results/frontier-with-tools-probe/`:
- **Haiku with-tools:** all cells ≈100% (solve 6/6, validate_* perfect, simulate 7/8), `tool_selected=1.0`.
- **Sonnet with-tools:** validate_* perfect, **but solve 0/6 and simulate 0/8** — suspicious; likely
  the no-JRE/host artifact that produced sweep7's false `solve` regression. n=6/task ⇒ wide CIs.
- None of this is written into `main.tex` (paper currently frames frontier-with-tools as untested).

> **DECISION D:**
> - [X] **Verify Sonnet zeros, then surface** — sanity-check the JRE/host artifact; if clean, report
>       the pilot (Haiku ≈100%; tools close the gap at the frontier too) as a pilot-scale datapoint,
>       clearly *not* full-N.
> - [ ] **Keep as Future Work** — don't surface pilot N (n=6/task); leave as the paper currently has it.
> - [ ] **Run a fuller frontier with-tools cell** — defensible N, but more $/compute, competes with
>       [6]/[5b] (the Haiku-WT plain run was already cost-rejected at $146).
>
> _notes:_

---

## What happens after you annotate

1. I log the decisions to `development/paper_notes_discussions.md` (dated entry, per CLAUDE.md).
2. Land the writing-only batch in one clean `main.tex` pass + verify the build.
3. Implement whichever probe(s) you greenlit (branch first, per repo discipline).
4. If [1]=verify, sanity-check the Sonnet zeros before anything gets quoted.

> **Anything to add / reprioritize before I proceed?**
>
> _notes:_ 
> > you mentioned the following: "think=on budget decoupling	CLOSE-NOW (done);
writing	Defense already in Limitations (main.tex:940-944); failed-pilot rationale already on the page."  
> **when was it attempted? perhpas we can now launch the  experiment more patiently after gathering experience from 6 sweeps and allow more budget?**

---

## Resolution (2026-06-20) — answering the reopened [8], plus a new honesty fix

**When was the think=on pilot?** Commit `b527f71` (2026-05-21, "bump ctx cap 16384→32768").
Critically, it enlarged the **single shared context window**; it did **not** separate the
reasoning cap from the answer cap. So reviewer [8]'s decoupled-budget ask is a **genuinely
different experiment** — the pilot does not refute it.

**→ Honesty fix needed regardless of any run:** the current Limitations text (`main.tex:940-942`)
can read as if the failed cap-raise rebuts decoupling. Reword so the failed pilot only rebuts a
*naive shared-budget increase*, while a *decoupled* design remains the correct (unbuilt) remedy.
Lands in the writing batch.

This reopens [8] (and by extension [2]) as two candidate new sweeps. Feasibility (subagent, grounded):

### Exp 1 — think=on budget decoupling [8] (harness-side budget forcing)
- **Correctness:** ✅ genuinely different from the failed pilot; directly answers [8].
- **Feasibility:** no native vLLM support → 2-call continuation (`stop=["</think>"]` + resume with a
  fresh answer budget). Files: `vllm_client.py`, `chat.py`, `runner.py`, `run_experiment.py`. Scope to no-tools.
- **Dev:** 2-4 days (Qwen3 template / reasoning-parser interaction is the risk).
- **Cost/value:** ~1-2 GPU-days (~18K gens; binding case = Gemma-MoE-26B, 89-100% truncation). High value.
- **Verdict: RUN-IF-TIME, after [6]/[5b]; dev in parallel with their compute, commit GPUs only after a green smoke.** Fix the wording either way.

### Exp 2 — fresh clean cluster BF16 35B [2]
- **Correctness:** ✅ addresses [2], but expected **null** (your evidence: AWQ≈BF16). Confirmatory, not story-changing.
- **Feasibility:** ✅ HF-id swap only (no `--dtype`); fits `rtx_pro_6000:1` (96 GB). The sweep7 killer
  (missing Java/ENHSP) is **absent on the cluster** — env ships openjdk-17.
- **Dev:** ~0.5 day. **Cost:** 2-5 GPU-days on the **scarce** pro_6000 pool.
- **Verdict: RUN-IF-TIME, after Exp 1 kicks off, pro_6000-permitting.** If forced to choose, **Exp 1 wins.**

### Meta — "one fixed sweep for all weaknesses"?
**No.** Controlled ablation = one knob per corpus against the shared sweep5v2 baseline. Consolidate the
*submission* (parallel array), never the *factors* — mixing precision/prompt/schema/temperature/budget
in one corpus destroys attribution (corpus identity is load-bearing).

> **DECISION E — Exp 1 (decoupled budget; ~2-4 day dev + ~1-2 GPU-days):**
> - [ ] Build it after [6]/[5b], run if the smoke passes (recommended — closes [8] for real)
> - [ ] Skip the run; apply only the honesty wording fix and keep as Future Work
>
> _notes:_

> **DECISION F — Exp 2 (clean cluster BF16 35B; ~0.5 day + 2-5 GPU-days, expected null):**
> - [ ] Run if the pro_6000 pool is free while Exp 1 dev is underway
> - [ ] Skip; keep the within-model decomposition as the standing defense
>
> _notes:_

### Sequenced execution order (current plan)
1. **Writing batch** (~10 asks incl. the [8] honesty fix) → one clean `main.tex` pass, build-verified.
2. **[6] schema-salience** harness change + 3-cell probe (phase 1 of DECISION C).
3. **[5b] simulate compressed-diff** if [6] lands easily (phase 2).
4. **[1] frontier:** verify Sonnet zeros, then surface the pilot.
5. **Exp 1 / Exp 2** per DECISIONS E/F (run-if-time, after the above).
