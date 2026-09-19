# Weakness review — what is the paper's biggest weakness? (2026-09-19)

*`STATUS.md` N1b. Asked for by Omer on 09-19: before any further experiment, a deep,
honest, critical look at where the paper is weakest, so the remaining time is well spent.
This file is findings and options with `> ANSWER:` slots. Nothing in the tex was changed
and nothing was run.*

## How it was done

- **Three cold readers.** Three independent reviewer agents each read all 2,363 lines of
  `paper/main.tex` at `3196112` and nothing else (no `development/`, no results, no
  history), the way a JAIR reviewer meets the paper. Lenses: (P) a planning-community JAIR
  reviewer, (M) a methods and statistics reviewer, (A) a practitioner who builds LLM
  agents. They did not see each other's reports. Each had to state the contribution in one
  sentence, rank five weaknesses by damage to acceptance with line evidence, and say
  whether the fix is rewriting, re-analysis of data we hold, or a new experiment.
- **Insider audit.** I checked their main factual claims against the tex, `NUMBERS.md`,
  the logs and the harness, and added what only we can know.

## The short answer

**All three reviewers, independently, put the same weakness first, and all three
recommend "major revision, leaning reject" as the paper stands.**

> The paper declares the *delivered* answer its primary outcome, and then cannot measure
> that outcome on the open-weight tool arms, because those runs stored only the first 500
> characters of each answer. So the title claim ("invocation is the bottleneck") is
> **undecided on the paper's own primary metric**, and the one full-storage rerun we do
> cite shows a model that stops calling the tool still answering correctly 30–63% of the
> time. The paper names the fix itself, in Limitations, as something it will run "should
> a reviewer require". All three reviewers wrote some version of: *I am requiring it.*

My own view after checking: they are right, and this outranks everything else, because
most of the other weaknesses (the many caveats, the angle-bracket bounds, the two
surfaces, the hard-to-follow story) are consequences of it.

**One thing the reviewers could not see, and it matters:** the tex states something our
own audit showed to be false (W4 below, the `guided_json` sentence). That one should be
fixed whatever else is decided.

## Clarity test: did they understand the contribution?

| reviewer | contribution in their words | confidence they got it right |
|---|---|---|
| P | a sound tool helps only if the model (a) calls it and (b) can restate its result; these two gates decide when tools help | ~70% |
| M | same two gates; neither is a capability limit | ~75% |
| A | same two gates; (a) varies by model and prompt, (b) degrades with answer length | ~65% |

All three landed on the two-gate reading, which is what the abstract says. All three also
gave the same reason for their doubt: **the title names one gate, the abstract names two,
the contribution list has five items, and the six RQs are a third framing** (per-task
"does the tool help?"). And the scorecard marks the title's own question (RQ3)
UNDECIDED on the primary surface.

---

## The weaknesses, ranked

"Raised by" counts the cold readers (P, M, A). "Insider check" is what I verified.

### W1. The primary outcome is not measured where the claims live — raised by 3/3, ranked first by 3/3

- **What they saw.** Delivered is declared primary (tex 513–529), but open-weight tool
  arms are 500-character snapshots (670–672, 1688–1692). Of the 15 headline (≥9B)
  availability cells, M counts 4 firmly decided. validate_plan and simulate are undecided
  in every model; Gemma's validate_plan cell is ⟨6.6, 99.6⟩. "Tool-verified numbers are
  never headlines" (523–524), yet the title, the abstract's 21→94% and 99%, RQ5, RQ6,
  cost-of-pass and the robust floor are all mechanism-layer. M: "The authors define a
  primary outcome, cannot measure it on 91,200 tool-arm trials, and report whichever layer
  is exact."
- **Insider check: true, and `NUMBERS.md` agrees** (13/25 availability cells undecided at
  think=off; vplan undecided ×3; simulate undecided ×3).
- **What only we know.**
  - The rerun the paper pre-registers has **never been run**. The full-storage rerun that
    exists (`iss024d`) was a different configuration (think=on, reasoning parser off), and
    that parser change is exactly why it failed parity. The pre-registered one is the
    canonical apparatus (think=off, parser on) with full storage.
  - The harness has stored 16K-character answers since 2026-06-25, so no code is needed.
  - Size: ≥9B × plain and steered × 4,560 = **about 27K trials**, $0, cluster GPU-hours.
    For scale, the nt-ster control was 6 cells × 9,120 rows.
  - Known risk: serving drift since May (the vLLM 0.22.0 note). The prereg already has the
    guard: a Gemma negative control and a ±5 pp equivalence test against the canonical
    tool-verified rates. The August anchor arm re-measured the *no-tools* rates within
    about 1 pp, which is encouraging but says nothing about the tool arms.
  - I recommended "contingency only" for this rerun in `advisor_brief.md` question 5.
    Having seen three independent readers all stop at the same place, **I think that
    recommendation was wrong.**
- **What the result can do.** Either outcome improves the paper. If non-calling really
  costs delivered answers, the title is proven on the primary surface and most bounds
  become points. If the model answers well without calling (as the 30–63% rerun cell
  hints), the honest title is about *delivery*, and we find that out before a reviewer
  does.
- **Fix type:** new experiment (already specified). Reviewers estimate it removes 60–75%
  of this damage, and a good part of W8.

### W2. "Invocation is the bottleneck" rests on one quantized model, one task, and a "plain" arm that is not plain — raised by 3/3

- **What they saw.** The collapse is Gemma-MoE (a community AWQ-INT4 build) on
  validate_plan. The 35B moves −9 pp, the 9B +13 pp, and both frontier models call the
  tool on ~100% of trials. In the parser-off rerun Gemma's tool path is 0.9% instead of
  21%, so the invocation rate depends on the serving parser. A: "A bottleneck removed by
  one sentence, absent at the frontier, unmeasurable at the answer, and shown in one INT4
  checkpoint, is a prompt bug report."
- **Insider check: the sharpest point is true.** The tool-available *system prompt*
  printed in the paper already says "LLMs cannot reliably check plan correctness from
  training alone. **Use the available validation tool**" (470–474). The abstract and intro
  call this arm "merely available". So 21→94% is really "instruction in the system prompt"
  against "instruction repeated in the user turn". Limitations half-admits it ("differ by
  a one-line policy/format clause", 1664–1667) but the headline wording does not. P adds
  that Gemma's chat template has historically had no native system role, which we never
  examined.
- **Fix options.** (a) Rewording only: stop saying "merely available", retitle. Removes
  roughly a third of the damage. (b) A small add-on to the W1 job on Gemma validate_plan
  (about 3K trials per arm): tools with a truly neutral system prompt; the directive in
  the system prompt instead of the user turn; optionally `tool_choice=required`. If the
  effect survives a neutral system prompt, the finding gets much stronger. If it does
  not, the invocation story as written does not stand, and it is far better that we learn
  it.
- This is also where the Llama probe belongs, if anywhere: reviewers want more families
  *inside this contrast*, not as a separate appendix point.

### W3. The delivery gap may be a property of our answer contract, and it is over-stated — raised by 3/3

- **What they saw.** The gap exists because the harness makes the model re-type the tool's
  plan or trajectory as JSON under a token cap, graded by exact equality; a real system
  passes tool output through in code. The "law" (1285) rests on three answer types, n=100
  per cell, 5 failures vs 5 failures on plans ("identical at both tiers" is a coincidence
  inside a Wilson interval of about [89, 98]). Our own pre-registered budget probe failed
  its criterion for Sonnet (p=0.069), and 30–35% of tool-arm trials still fail at 64K with
  none at the cap, which contradicts the "length × budget" reading and the abstract's
  "room for the result".
- **Insider check: accurate.** The frozen readout says the same (budget explanation
  confirmed at one tier, partly supported at the other).
- **Fix:** rewriting (drop "law" and "identical", state the gap as a property of
  re-stating long outputs under this contract) plus a **$0 re-analysis we can do now**:
  the 64K probe has full storage, so the 30–35% residual failures can be classified
  (wrong trajectory, wrong wrapper, partial). That residual is the most interesting
  number in the section and the paper does not yet say what it is. Optional: a small
  pass-through arm.

### W4. The unaided baselines are handicapped by the apparatus, and the tex says otherwise — raised by M (W2), noticed by A; the key fact is insider-only

- **What they saw.** Unaided solve is 67% unparseable + 15% truncated; simulate 68%
  unparseable + 29% truncated, "despite JSON-schema-constrained decoding". The appendix
  says the 0% "is not a formatting artifact" while the body says no model ever emits the
  wrapper. The steering control's no-tools simulate anchors are 10.9–28.0% against the
  canonical 0/3,000. The section heading "Two Tasks the Model Cannot Do Unaided" conflicts
  with 22–61% unaided simulate a page later. M: "The sole-source regime is manufactured
  by the grader and the cap."
- **Insider check: worse than they think.** Tex 441–442 says "per-task
  JSON-schema-constrained decoding remains, so the baseline is not held back by formatting
  alone". Our own audit (PR #94; corrected figures in `paper_notes` 2026-08-17) found the
  constraint **never reached the server**: 0 of 58,581 provable validate rows emitted any
  JSON, conformance under 2% on every cut, and the solve and simulate prompts tell the
  model to follow "the JSON schema provided by the format constraint" that did not exist.
  That log entry is titled "what Limitations may say about `guided_json`", and
  `STATUS.md` Job 4 says the audit "fed the Limitations wording". **The sentence is not in
  the tex** (no occurrence of the audit anywhere in `main.tex`), and line 441 asserts the
  opposite. Two reviewers spotted the symptom without knowing the cause.
- Also shaky: tex 874–875 argues "re-grading the stored responses recovers at most 0.7%,
  so the recovery comes from the budget, not the grader", while the appendix (2042–43)
  says those responses are 500-character snapshots that cannot be regraded. A truncated
  snapshot cannot contain a full trajectory, so that 0.7% is weak evidence.
- **Fix:** rewriting, mandatory for line 441 and a Limitations sentence (figures through
  `/verify-claims`, quote the 08-17 entry). The rest overlaps with
  `consistency_read_findings.md` rows A4, A5, A6, A8.

### W5. The oracle is the tool, so the mechanism-layer decomposition is close to a tautology — raised by P, M, A

- Ground truth comes from the same toolchain the model calls (329–332). At the mechanism
  layer a missing call fails by construction (1804–06), so "the variance lives in
  P(call)" and "−67 pp" restate the invocation rate, and P(correct | call) ≈ 99% is the
  tool agreeing with itself.
- **Insider check: fair.** The paper says "by construction" in the appendix only. Plans
  are checked by VAL, which is independent of the planner; the paper should name it.
- **Fix:** rewriting, plus naming the independent checks we already have. M rates this
  the most fixable item (about 80%). It stops mattering once W1 gives delivered points.

### W6. Inference: domain clustering ignored, one correction spent twice, and one equivalence sentence that does not hold — raised by M, partly P

- The √2.7 design effect covers paraphrase clustering (size 3) only; the 20-domain
  structure is ignored in the main intervals although the steering control clusters on
  domain. The same √2.7 is claimed to cover multiplicity as well (594–599). One GLMM, on
  the largest mechanism-layer contrast, log-odds +7.5 with SD 0.10 (the variational fit
  already tracked in N3). RQ1 reads YES only because headlines are restricted to ≥9B. The
  contamination "null" is absence of disjoint intervals, never an equivalence test, and
  sits beside PlanBench, where renaming alone takes Haiku from 43.8% to 0.7%.
- **Insider check, one item recomputed.** Tex 1437–39: the with-tools paired gap between
  Blocksworld and Mystery is 3.5 points (119 vs 140 discordant, n=600), "well inside the
  ±7.5 point margin". I recomputed the paired interval: **90% CI [−0.9, +7.9], 95% CI
  [−1.8, +8.8]. The point estimate is inside the margin; the interval is not.** Under your
  own equivalence-wording rule this is "criterion not met / unresolved" unless the
  PlanBench prereg defined the test on the point estimate. Needs `/verify-claims` against
  that prereg before any edit.
- **Fix:** $0 local re-analysis: domain-cluster bootstrap for the headline intervals, the
  standard-estimator GLMM refit, equivalence tests for the two nulls, and a short
  statement of what was pre-specified and what was not.

### W7. External validity: thin roster, and PlanBench never shows gate one — raised by P, A

- Four Qwens and one Gemma; two of the three headline models are community INT4 builds;
  both frontier models are one vendor; PlanBench is one model on Blocksworld, where every
  trial called the planner, so the paper's central phenomenon never appears there. Tools
  rescuing Mystery is already Huang and Zhang's result.
- **Insider check: true**, and mostly owned in Limitations. The Llama probe answers a small
  part of it. P would rather see PlanBench on two or three open-weight models, plain vs
  steered, because that is where invocation would actually show up in the external
  benchmark.
- **Fix:** new experiments, the most expensive on this list. My view: only after W1 and
  W2, and only if the invocation claim survives them.

### W8. The story is buried — raised by A (W5), P (recommendation), M (implicitly)

- A counts nine apparatuses a reader must hold (canonical, anonymized, frontier v11 slice,
  budget probe, full-storage rerun, decoupled control, steering control, PlanBench, drift
  rerun), two grading layers, three value shapes, 3+1 arms, two modes, six RQs. P: the
  paper "reads as an audit of its own harness rather than as a finding". A: "I cannot tell
  which numbers the authors stand behind." The disclosed analysis bug (censored rows once
  scored as successes) costs trust where it sits.
- **Insider check: this is the price of W1.** Most of the apparatus exists to work around
  the missing delivered numbers. If W1 is run, a large share of the bounds, the second
  surface in the headline text and several caveats can go, and a restructure becomes
  worth doing once. Doing the restructure first would be wasted work.
- **Fix:** rewriting, after W1. One corpus table, results first, controls to the appendix.

### W9. Novelty and positioning, including against our own arXiv version — raised by P

- The earlier version is cited only for scale; nothing says which conclusions are new,
  confirmed or reversed. "None measures…" sits beside La Malfa and omits LLMFP and the MCP
  tool-use benchmarks; 26 references is thin for JAIR. P: "That telling a model to call a
  tool makes it call the tool is not a JAIR-level finding."
- **Insider check:** the delta statement is already planned for the cover letter
  (ISS-013); P's point is that it belongs in the paper too. The competing-work notes
  already exist (verified 08-06).
- **Fix:** rewriting. Removes 30–40% by P's estimate.

---

## What survives a strict reader today

M's list, accepting only exact, same-apparatus, delivered-surface evidence: the unaided
open-weight rates (format-confounded, W4); the contamination result as absence of
evidence; the frontier lifts (solve 22/29→95 at n=100, the validation lifts, zero delivery
gap on verdicts, 5/100 on plans); the 64K probe numbers; PlanBench (Mystery 0–4.3% →
71.8%, Blocksworld 47.8 → 68.3, the instruction ladder); and the steering directive
staying within ±5 pp on validate_plan and validate_problem without tools.

**What does not survive:** the title, any open-weight tool benefit beyond validate_domain,
"the gap grows with length", RQ5, RQ6, cost-of-pass, and think=on robustness.

## Where I think the reviewers are wrong or too harsh

- "273,600 trials graded" is accurate as a count; their objection is really W1.
- "The pre-registration protects one cell" undersells the steering control (six units, all
  passing), but their point that the eligibility gates remove solve, simulate and
  validate_domain in every unit is correct and already in Limitations.
- A's "one afternoon plus 100K cheap trials would settle both" underestimates cluster
  reality (VPN, queue, parity gates). The order of magnitude of the *design* is right.
- The "so what" verdict ("put the instruction in the user turn, pass tool output through
  in code, don't wrap cheap verdict tasks: common practice") is harsh but is what a
  practitioner reviewer will say. The defensible journal contribution, in their words: the
  oracle-graded two-layer measurement, the 30–35% residual at 64K, and the PlanBench
  control ladder.

---

## Decisions

**Q1 — W1: run the pre-registered full-storage rerun (≥9B, think=off, plain + steered,
about 27K trials, $0) before submission?** Recommendation: **yes.** It is the one item all
three readers asked for, the paper already promises it, the harness is ready, and it
decides what the title can honestly say. It needs the freeze-protocol gate before any
analysis code is hashed, a preflight, and your go before any cluster step.

> ANSWER (run / contingency only / other):
>

**Q2 — W2: the "merely available" arm.** Options: (a) rewording only; (b) add the small
Gemma validate_plan arms to the Q1 job (neutral system prompt; directive in the system
prompt; optionally forced call), about 3K trials each; (c) both. Recommendation: **(c)**.
The arms are cheap next to Q1 and they test the sentence the title rests on.

> ANSWER (a / b / c):
>

**Q3 — W4: fix tex line 441 and add the `guided_json` Limitations sentence now**, through
`/verify-claims`, quoting the 08-17 figures. Recommendation: **yes, regardless of
everything else**; the tex currently states something our audit refutes. I would show you
the two sentences before committing.

> ANSWER (yes, show me drafts / no / other):
>

**Q4 — $0 re-analysis package, local, no cluster:** classify the 30–35% residual failures
in the 64K probe (W3); domain-cluster bootstrap and the GLMM refit (W6); verify the
PlanBench "well inside ±7.5" sentence against its prereg (W6). Recommendation: **yes**; it
can run while Q1 is queued.

> ANSWER (all / list which):
>

**Q5 — Rewriting that does not depend on new data:** demote "law" and "identical" (W3),
name the independent checks and say "by construction" in the body (W5), put the arXiv
delta and the missing related work in the paper (W9). The big restructure (W8) waits for
Q1 results. Recommendation: **yes, drafts shown first**, after the consistency-read
answers, so the same passages are touched once.

> ANSWER:
>

**Q6 — Title.** Title D ("Invocation Is the Bottleneck…") was chosen on 09-18. All three
readers say the body does not yet support it on the primary surface. Recommendation:
**keep it for now and let Q1 and Q2 decide**; if you answer "contingency only" to Q1, the
title should change to the two-gate reading the abstract already has.

> ANSWER:
>

**Q7 — W7 experiments (more families, open-weight PlanBench, the Llama probe).**
Recommendation: **not now.** Revisit after Q1 and Q2, and only if the invocation claim
survives them.

> ANSWER:
>
