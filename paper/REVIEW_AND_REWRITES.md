# AAAI-27 Paper — Review & Rewrite Plan

**Target:** `paper/main.tex` (branch `paper/aaai27-single-tool-draft`).
**Scope of this doc:** a peer-review-style assessment plus *paste-ready rewrites* for each
issue, so the narrative gets sharper without new infrastructure. All numbers below were
recomputed from the raw trials in `results/sweep5-cluster-20260530/` (think=off, sweep5v2
canonical / sweep6 anonymized), **not** read off the deck — see §A for the extraction.

> **Reading order:** §0 (the one reframe) → §1 (the one place the draft is *wrong*) →
> §2–§4 (analysis upgrades) → §5 (narrative rewrites) → §6 (clarity) → §7 (strategy) → §A (data).

---

## 0. The single reframe that decides acceptance

**Problem.** As written, the paper reads as *"an evaluation of whether a sound PDDL tool
helps an LLM."* A skeptical AAAI reviewer's reflex is: *"a correct-by-construction tool
obviously helps; you've reduced the science to 'does the model call the tool'."* That reflex,
unaddressed, is a borderline-or-reject review.

**Fix.** Lead with the transferable behavioral finding and treat PDDL as the *instrument*
that makes it measurable:

> Tool **availability** can *lower* success on a task the model already does well
> (Gemma-MoE `validate_plan` 88→21%, −67pp), because the model goes **silent** — it reasons
> in prose instead of calling the validator — and a single steering sentence reverses it
> (+72pp). The bottleneck is invocation **propensity**, not capability and not tool accuracy.

This is counterintuitive, mechanism-backed, and *general* (it is a statement about
tool-augmented LLMs, not about PDDL). The PDDL oracle is what lets you prove it cleanly:
because a correctly invoked tool is correct by construction, every residual failure is
unambiguously a *model behavior*, never a tool error. Say that explicitly, and the
"isn't this trivial?" objection becomes the paper's selling point.

**What changes:** abstract + intro center of gravity (§5.1, §5.2), and a new short
**Discussion** section (§5.4). No new experiments. Highest-leverage edit in this document.

---

## 1. MUST-FIX — `validate_domain` is mis-framed (the draft is currently *wrong* here)

**The claim in the draft** (`\subsection{Tasks With Headroom}`): the two validation tasks
"improve from an already partial baseline," and `validate_domain` works "from a more varied
baseline (e.g. Gemma-MoE 78%, Qwen3.6-35B 68%)." This implies the unaided models are
*partly competent* on `validate_domain`.

**What the data actually says** (recomputed, think=off, ≥9B; `validate_domain` is **5:1**
valid:invalid, so always-guessing-VALID scores **83.3%** pooled / 50% balanced):

| Model | no-tools pooled | no-tools **balanced** | +tool(steered) pooled | +tool(steered) balanced |
|---|---|---|---|---|
| Qwen3.5-9B | **25.6%** | **53.3%** | 100.0% | 100.0% |
| Gemma-MoE-26B | 77.8% | 74.0% | 98.3% | 95.0% |
| Qwen3.6-35B | 67.8% | 64.7% | 99.7% | 99.2% |

Two facts the current prose hides:

1. **All three ≥9B models are at or below the 83.3% trivial majority baseline unaided.**
   Their pooled "78%/68%" numbers are *worse than always saying VALID*. Calling that a
   "partial baseline" is not defensible — a reviewer who knows the 5:1 ratio will catch it.
2. **Balanced accuracy reveals near-chance discrimination** (53/74/65%). Qwen3.5-9B is the
   extreme: it almost always answers INVALID (TPR 11.7%, TNR 95.0%), so it looks terrible on
   the majority-positive pooled metric but is really just *non-discriminating*.

**Why the corrected story is *better*, not worse:** "the tool rescues a task on which models
are at-or-below trivial baselines and near-chance at discrimination" is a stronger, cleaner
result than "the tool nudges a partly-competent model." It also separates the two validation
tasks honestly: `validate_problem` (balanced, genuine ~50% trivial floor, *real* partial
competence) vs `validate_domain` (imbalanced, sub-majority, *rescue*).

### Rewrite 1 — replace the `validate_domain` half of "Tasks With Headroom"

> On \emph{validate\_problem} the unaided model is genuinely partly competent: the set is
> balanced one-to-one, so a constant ``VALID'' guess scores $\approx$50\%, and the
> $\geq$9B models clear that floor before any tool. The availability gap is
> $+21$--$30$\,pp (3/3 favorable-significant, 0/3 against): the tool adds real value over a
> non-trivial baseline. \emph{Validate\_domain} is different, and instructive. Because its
> fixtures run $5{:}1$ valid-to-invalid, a constant ``VALID'' already scores $83\%$; yet
> unaided, every $\geq$9B model lands \emph{at or below} that trivial line (pooled
> $26$--$78\%$) and discriminates barely above chance (balanced accuracy $53$--$74\%$).
> Qwen3.5-9B is the clearest case --- it answers ``INVALID'' almost reflexively (true-positive
> rate $12\%$, true-negative rate $95\%$), scoring $26\%$ pooled but $53\%$ balanced. The tool
> does not \emph{refine} a competent baseline here; it \emph{rescues} a task the models cannot
> do reliably, lifting balanced accuracy to $95$--$100\%$. Steering adds nothing significant on
> either validation task ($-5$--${+}1$\,pp): once a capable model has the tool it already calls
> it, and the nudge matters only where the plain arm under-calls --- which is exactly the next
> case.

> *(Move the per-class / balanced-accuracy figures into an appendix table; keep balanced
> accuracy as the headline metric for `validate_domain` everywhere it is quoted, including the
> scorecard's RQ0.1 evidence cell. The Limitations note about the 5:1 imbalance should now
> point here rather than standing alone.)*

---

## 2. ADD — the invocation decomposition (turns the mechanism into a result)

The whole paper rests on "success tracks tool-use almost 1:1; accuracy-when-calling is high."
Right now that is prose + one figure. Make it a **formal mediation**, which is the single
cleanest defense against *"maybe the model just got worse with the tool."*

`success = P(call) × P(correct | call)`, and in these tasks `P(correct | no call) ≈ 0`
(not calling is guaranteed failure). Recomputed (think=off, ≥9B):

| Model | task / arm | P(call) | P(correct\|call) | P(correct\|no-call) | success |
|---|---|---|---|---|---|
| Gemma-MoE-26B | `validate_plan` plain | **20.7%** | 99.2% | **0.0%** | 20.6% |
| Gemma-MoE-26B | `validate_plan` steered | 93.6% | 98.9% | — | 92.6% |
| Qwen3.6-35B | `validate_plan` plain | 82.9% | 99.1% | 0.0% | 82.2% |
| Qwen3.6-35B | `validate_plan` steered | 99.9% | 99.4% | — | 99.3% |
| Qwen3.5-9B | `validate_plan` plain | 97.9% | 95.2% | 0.0% | 93.2% |
| Qwen3.6-35B | `solve` plain | 68.0% | 92.6% | 0.0% | 63.0% |
| Qwen3.6-35B | `solve` steered | 93.7% | 98.2% | 0.0% | 92.0% |

The mediation is exact: Gemma plain `0.207 × 0.992 = 20.5% ≈ 20.6%` observed. The collapse
lives entirely in the **first** factor; the second factor (`P(correct|call)`) is ≥92%
everywhere and barely moves between arms. This is silence-not-error, quantified.

### Rewrite 2 — insert into "When Availability Backfires" (after the Figure 2 sentence)

> The decomposition makes the mechanism exact. Writing strict success as
> $P(\text{call})\times P(\text{correct}\mid\text{call})$, Gemma-MoE's plain-arm collapse is
> entirely in the first factor: it calls the validator on only $21\%$ of trials, but
> \emph{when it calls it is $99\%$ correct}, and on the $79\%$ where it stays silent it is
> $0\%$ correct (a missing tool call is an ungradeable answer, never a lucky guess). Steering
> moves only $P(\text{call})$ --- $21\!\to\!94\%$ --- and success follows it almost exactly
> ($0.94\times0.99=0.93$). Across every $\geq$9B tool cell, $P(\text{correct}\mid\text{call})$
> stays $\geq$92\% and varies little between arms; essentially all between-arm and
> between-model variance in success is variance in \emph{whether the model calls}. The tool's
> accuracy is not in question --- its invocation is.

> *(Add the full table as an appendix; it also powers the "size inversion is propensity, not
> capability" paragraph — the 9B "beats" the 35B in the plain arm only because P(call) is
> 100% vs 68–83%, while P(correct|call) is ≥92% for both.)*

---

## 3. Plots — keep / fix / add

**Keep** all four (clean, on-message). Specific upgrades:

- **Fig 2 (mechanism) — add the `P(correct|call)` reference bar.** This is the highest-value
  figure edit. Right now the right panel shows *success* (Gemma plain 21%); overlay a faded
  marker at `P(correct|call) ≈ 99%` so the viewer sees instantly that 21% is *silence*, not
  incompetence. It makes silence-not-error visually undeniable and matches Rewrite 2.
- **Fig 3 (token quadrant) — print the cost-of-pass multiplier on each panel** (e.g. "0.3×"
  on `solve`, "≈4×" on `validate_plan`). The figure shows tokens and success but not the
  cost-of-pass number, which is the actual headline metric. Also verify the x-axis exponents
  render as `10³/10⁴` superscripts in the compiled PDF (the extracted text shows "10 3 104",
  hinting at a tick-format glitch).
- **Fig 1 (sole-source bars) — cap the y-axis at ~105**, not 120 (wasted vertical space).

**Add (ranked):**

1. **Failure-type taxonomy (stacked bars, per task × arm).** #1 new plot. The paper makes
   many failure-mode claims (simulate unaided = 68% unparseable / 29% truncated / 3%
   parsed-wrong; `validate_plan` = silence) scattered in prose. One stacked-bar figure
   substantiates all of them at once and is exactly what an eval-paper reviewer wants
   ("show me *how* they fail"). It also visualizes the truncation-vs-content-failure
   separation you built. Source: `failure_reason` + `truncated` fields, already in trials.
2. **Surface one robustness figure in the main body** (currently folded to text). The
   think=on budget confound is both a result and a Limitation; a compact robust-floor /
   mode-dumbbell lets reviewers *see* robustness rather than trust it. Asset exists:
   `plots-unified/visible_mode_succ.png` / `realizable_dumbbell.png`.
3. **Optional:** the "metric choice flips the verdict ≈10×" claim as a 3-bar inset
   (tokens-ratio vs success-ratio vs cost-of-pass) — pre-empts "you cherry-picked the metric."

---

## 4. Statistical rigor — three fixes a methods reviewer will demand

**(a) Trial non-independence / clustering.** Wilson intervals assume independent Bernoulli
trials, but each cell pools **3 paraphrases of the same instance**, which are correlated, so
the effective N < nominal and the CIs are mildly anti-conservative. Either cluster on instance
or acknowledge it.

> **Rewrite 4a (Methods or Limitations, one sentence):** Because each instance is scored under
> three paraphrases, trials within an instance are not independent; our Wilson intervals
> therefore slightly understate uncertainty. The headline effects ($+50$--$92$\,pp) far exceed
> any plausible clustering inflation, and the borderline cases are flagged individually rather
> than pooled.

**(b) Disjoint-CI is conservative — say so.** Disjoint 95% CIs ≈ an $\alpha\approx0.006$
difference test, so the rule is *under*-powered, not over-eager.

> **Rewrite 4b (Methods, after the signed-rule definition):** Requiring disjoint 95\% intervals
> is deliberately conservative --- it controls the false-positive rate well below
> $\alpha=0.05$, at the cost of power on small gaps. We accept that trade for a transparent,
> sign-aware rule; consequently a ``no'' verdict means ``no movement we are willing to call
> significant,'' not ``no movement.''

**(c) No multiple-comparison correction — note and justify.**

> **Rewrite 4c (one clause):** We do not apply a family-wise correction across cells: the
> reported effects are large and we treat the few borderline gaps as exploratory rather than
> confirmatory.

*(These three sentences flip reproducibility-checklist 4.12 from a liability into a defended
choice and cost ~40 words total.)*

---

## 5. Narrative rewrites (abstract, intro, contributions, Discussion)

### 5.1 Abstract — reframe to lead with the mechanism + general lesson

> Sound symbolic planners and validators are correct by construction, and language models are
> increasingly able to call them as tools --- but does access actually help an LLM on planning
> tasks, and when? Using PDDL as a setting where a deterministic oracle can grade every answer
> exactly, we evaluate five single-tool-use tasks (solving, domain, problem, and plan
> validation, and state-trajectory simulation) across five open-weight models, scoring strictly
> against the solver/validator rather than by self-report. A three-arm design separates tool
> \emph{availability} from a one-sentence \emph{steering} nudge, every proportion carries a
> confidence interval, and a signed-significance rule distinguishes help from harm. The benefit
> is strongly regime-dependent: two tasks essentially cannot be done without the tool, two are
> rescued from at-or-below-trivial baselines, and one --- plan checking --- exposes the general
> lesson. There, merely making the tool \emph{available} can \emph{lower} success, because the
> model reasons in prose instead of calling the validator; the failure is silence, not error
> (it answers correctly $>$99\% of the times it does call), and one steering sentence reverses
> it. Measured in tokens, the tool pays for itself precisely where the model cannot do the task
> unaided. The pattern holds under reasoning mode and an anonymized-domain contamination
> control. The bottleneck throughout is invocation \emph{propensity} --- a model- and
> prompt-dependent behavior --- not capability or tool accuracy.

### 5.2 Intro contributions — sharpen the four bullets

Keep the four-item list but re-point items 2–3 at the general claim:

> \item The finding that tool utility is regime-dependent, and the identification of
> \emph{invocation propensity} --- not capability or tool accuracy --- as the binding
> constraint: success factors as $P(\text{call})\times P(\text{correct}\mid\text{call})$, and
> all between-arm variance lives in the first factor. This yields the counterintuitive result
> that tool \emph{availability} can hurt a task the model already does well, via a
> silence-not-error mechanism that one steering sentence reverses.

### 5.3 Enumerate the RQs (clarity blocker — see §6)

### 5.4 ADD a short Discussion section (currently missing entirely)

The paper jumps Results → Limitations. Add ~0.4 page of Discussion before Limitations. This
is where the paper earns its generality. Draft:

> \section{Discussion}
> Three implications generalize beyond PDDL. First, the binding constraint on tool-augmented
> performance here is not whether the model \emph{can} use the tool but whether it \emph{does}:
> across every cell, accuracy-given-a-call exceeds $92\%$, so the entire spread in outcomes ---
> between arms, between models, and across reasoning modes --- is spread in invocation
> propensity. A correct-by-construction tool turns ``can the model plan?'' into ``will the
> model delegate?'', and the second question is the one that varies. Second, availability and
> steering are distinct levers with different failure modes: exposing a tool without urging its
> use leaves a model free to fall back on prose, and on a task it can almost do that fallback is
> actively worse than the tool-assisted path it declined. The remedy is cheap --- one
> imperative sentence --- but it is not automatic, which is a concrete caution for any system
> that exposes tools and assumes they will be used. Third, our results are direct empirical
> support for the LLM-Modulo thesis \citep{kambhampati2024llmmodulo} that LLMs should be paired
> with sound external verifiers, and a refinement of it: the pairing only pays off when the
> orchestration actually routes work to the verifier, and naive availability does not guarantee
> that routing. The practical rule that follows is sharp --- a planner or validator behind a
> tool interface helps most when the task exceeds the model's unaided reach \emph{and} the
> prompt explicitly directs the call; where the model is already competent and uninstructed,
> the tool is at best a token-priced luxury and at worst a regression.

*(This also lets the Conclusion shrink to 3–4 sentences, freeing space.)*

---

## 6. Clarity fixes

- **Enumerate the six RQs.** "RQ0.1…RQ0.6" appear only as scorecard labels and are never
  listed; a reviewer hunting "what is RQ0.3?" finds nothing. Add a numbered list at the end of
  the Intro or top of Results. **Also drop the "0." prefix** (RQ1–RQ6) — it reads like leftover
  internal deck numbering.
- **Define the two regime axes up front.** "sole-source / headroom / mixed" is a *task* axis;
  "robust / budget-dependent / sole-source" is a *cross-mode* axis. They overlap on the word
  "sole-source" and arrive fast. One sentence or a 3-row box disambiguates them.
- **Set a real title** (currently "Working Title (TBD)"). Foreground the finding:
  - *Availability Is Not Enough: When Symbolic Tools Help — and Hurt — LLMs on Planning Tasks*
  - *Will the Model Delegate? Regime-Dependent Utility of Sound Tools for LLM Planning*
  - *When a Correct Tool Lowers Accuracy: Invocation Propensity in Tool-Augmented LLM Planning*
- **Break the longest Methodology sentences** (signed-significance and cross-mode paragraphs);
  pull a one-line version of the −67pp worked example to where the signed rule is first defined.

---

## 7. Generality at the frontier — DECIDED PLAN (+ PlanBench)

**Why this section exists.** The roster is two families, all open-weight, 0.8–35B, no
frontier/proprietary model — the biggest substantive vulnerability. Two distinct reviewer
objections must be separated, because they need different evidence:

1. **"Does it scale beyond small/weak models?"** — answered by a much larger *open-weight*
   model.
2. **"Does it hold for the best *proprietary* SOTA?"** — answered only by a closed frontier
   model. For a *tool-use* paper this is the sharper objection (closed models have the most
   aggressive tool-use RLHF).

A third, related worry the user raised: **a stronger model is more likely to have memorized
public benchmark domains** (contamination), even if not emphasized in training — so the
contamination control should be re-run on a strong model, not just the weak roster.

### 7A. LOCKED — Sonnet 4.6, no-tools, canonical vs anonymized (the frontier experiment)

**Budget:** ~$145 in Anthropic credit on hand. **Decision:** spend it on the no-tools arm of
a strong proprietary model, which does double duty — sole-source proof *and* the frontier
contamination probe — and is cheap because no-tools is single-shot (batchable).

**Crucial scoping logic (do not run floored tasks for contamination).** Contamination can only
be *seen* where the unaided baseline has room to be inflated. `simulate`/`solve` are floored
(0–9% unaided) → they prove **sole-source** but carry **zero** contamination signal.
`validate_plan` (80–91% unaided) is the **best** contamination probe; `validate_problem`
(~50–76%, balanced) is a good second.

| Task (no-tools, think=off, **full N**, BOTH corpora) | Role | List | **Batch (−50%)** |
|---|---|---|---|
| `simulate` (300 ×2) | sole-source at frontier | $32 | $16 |
| `validate_plan` (3,000 ×2) | **best** contamination probe (highest headroom) | $184 | $92 |
| `validate_problem` (600 ×2) | balanced contamination probe (triangulation) | $21 | $10 |
| *(optional)* `validate_domain` (360 ×2) | imbalanced probe + Sonnet balanced-acc for §1 | $11 | $5 |
| **Total (DECIDED set)** | `simulate`+`validate_plan`+`validate_problem` | **$236** | **~$118** |

**DECIDED 2026-06-18: run `simulate` + `validate_plan` + `validate_problem`, no-tools, both
corpora, full N, think=off, Batch API ≈ $118** (fits $145, ~$27 buffer). `validate_problem` is
**included, not optional** — resting the "no memorization at the frontier" claim on a single
task is fragile; two probes of different baseline (high-headroom `validate_plan` + balanced
`validate_problem`) is far more defensible, and $10 against a $27 buffer is a trivial price.
**Optional cheap add (+$5): `validate_domain`** — a third headroom probe that also gives Sonnet's
balanced accuracy for the §1 fix. **Skip `solve` no-tools** (floored → no contamination signal;
sole-source is already covered by `simulate`); do not push to all five tasks (~$146, no cushion
for token-proxy error). Full N on `validate_plan` is deliberate, not a luxury: the roster's
canonical−anon Δ there is tiny (−1.9 to +0.4 pp), so detecting whether a *stronger* model shows a
real gap needs the 3,000-trial/corpus power; lean would blur the small effect being hunted.

**Must-dos for the experiment agent:**
- **Anthropic Batch API (−50%)** — the halving is what makes it fit (list price $215 > budget).
  No-tools is single-shot → fully batchable; ~24 h turnaround is fine for an offline eval.
- **Pilot first (~$5–10, ~50 trials/task on canonical)** — the token counts here are a
  Qwen3.5-9B proxy; Sonnet may run ±35% on input and even think=off output should be lean —
  verify before releasing the full batch. Pilot comes out of the buffer.
- **think=off (disable extended thinking)** — matches the paper's clean contamination read and
  keeps cost predictable. Bonus: "even non-thinking Sonnet scores ~0% unaided on `simulate`"
  is a strong, conservative sole-source line. (A tiny think=on `simulate` probe can be added
  later only if a reviewer pushes "would reasoning fix it?")
- **Reuse the EXACT sweep5v2 (canonical) + sweep6 (anonymized) fixtures, prompts, and graders**
  — corpus identity is load-bearing; this must be a clean drop-in into the existing
  canonical-vs-anon comparison, not a regenerated set. Grading is clean: no tool-call parser
  risk (no-tools), `validate_plan` is balanced 5:5 (`v*`/`b*`) so plain accuracy = balanced
  accuracy, `simulate` is exact canonical-form trajectory match.
- **Client shim:** the harness is vLLM-only; Anthropic exposes an OpenAI-compatible endpoint +
  the Batch API, so a thin adapter (base_url/key swap) covers it.

**What it buys (two reviewer-proofing results from one run):** (1) **sole-source holds at the
frontier** — a strong proprietary model is still floored unaided on `simulate`; and (2) the
**contamination control extends to a strong model** — if Sonnet's canonical−anon Δ on
`validate_plan` (and `validate_problem`) is near-null, the "no memorization" claim jumps from
"weak models" to "even a frontier model"; if it is *not* null, that is an honest finding the
anonymized corpus already controls for. Either outcome strengthens the paper.

### 7B. CONSIDERED AND SET ASIDE — GPT-OSS-120B

GPT-OSS-120B was evaluated as a free, cluster-hosted complement (it fits `rtx_pro_6000`'s 96 GB
at native MXFP4 ~63 GB, the harness self-deploys vLLM, and a `feat/gpt-oss-120b-vllm` branch
exists). **Decision (2026-06-18): not in the plan.** Three verified facts removed its value:

1. **Not a capability step-up over the existing roster.** Head-to-heads are mixed and several
   show it level with or *below* the current models — e.g., Qwen3.5-9B beats gpt-oss-120B on
   MMLU (81.2 vs 78.2). So it does **not** answer the "does it scale to stronger models?"
   objection; the 35B is already in its capability class.
2. **With-tools integration is risky, not a flag swap.** The parser is
   `--tool-call-parser openai` (not "harmony"), but GPT-OSS tool calling is known-flaky on the
   `/v1/chat/completions` endpoint the harness uses, and works reliably only on the
   `/v1/responses` (Harmony) endpoint the harness does not speak (open vLLM bugs #22578, #22337).
   A silent **0%** `tool_selected`/`success` is the failure mode.
3. **Its no-tools contamination would be redundant** — five open-weight no-tools cells (Qwen×3
   + Gemma + 35B) already cover "large open-weight, high-headroom, near-null."

Sonnet (§7A) is unambiguously frontier *and* proprietary, so it closes both the "scales up" and
"open ≠ closed" objections that GPT-OSS only partially touched. If a *larger open* model is ever
wanted for the "scales up" angle specifically, the honest pick is Qwen3-235B-A22B (fits the
H200) — but same lab, weaker on diversity, and it still leaves the proprietary objection to
Sonnet, so it is not worth the effort for this submission.

### 7C. PlanBench — keep it Future Work for this submission

Absorbing an in-flight cross-domain sweep would dilute a clean single-suite message, and you do
not want a running sweep gating the deadline. PlanBench is also primarily a *formalization*
benchmark — a different failure mode than invocation propensity — so mixing it muddies the
mechanism story. A paper with one sharp finding beats a sprawling one for AAAI Main Technical.
Add PlanBench only if it finishes early *and* cleanly
reproduces the regime structure under the same end-to-end grading; otherwise it is the natural
standalone follow-up.

### 7D. Precision control — the size×precision confound (DECIDED 2026-06-18)

**The confound.** The roster mixes precisions: Qwen3.5-0.8B/4B/9B are 16-bit, but Gemma-MoE-26B
and Qwen3.6-35B are AWQ-INT4 (disclosed in the Models footnote). So **model size is confounded
with quantization** for the two largest models. This threatens the **size-inversion / "9B beats
35B = propensity"** finding — which lives entirely in the *with-tools* arm (P(call), plain-vs-
steered tool-use rate). A reviewer's rebuttal writes itself: *"the bigger model under-calls
because it's 4-bit, not because it's big."*

**Why the mechanism evidence does not clear it.** Silence-not-error (low P(call), high
P(correct|call)) is *observationally identical* to "quantization suppresses tool-calling
propensity while leaving verdict accuracy intact." The two explanations cannot be separated on
the existing data — **only a BF16 control on the 35B can**.

**State of sweep7 (the BF16-35B re-run, RunPod H200).** The **no-tools** arm completed but is
low-diagnostic here (no tool calls → does not test the propensity confound). The **with-tools**
arm is broken and burned ~66% of the pod budget with no clean corpus — its failures were
RunPod-env-specific (`--served-model-name` / `HF_HUB_OFFLINE` 404 / cell-dirname), not the model.

**DECISION:**
- **Abandon the pod with-tools run** (sunk cost; metered money on a flaky config near the
  deadline). Do *not* keep iterating it.
- **Option 1 (rigorous, ~free, PREFERRED if cluster + timeline allow):** run **BF16-35B
  *with tools* on the BGU cluster `rtx_pro_6000`** (96 GB; BF16 35B ~70 GB fits at 16K ctx —
  verify headroom). The AWQ-35B-with-tools already runs cleanly there with the verified
  `qwen3_xml` parser, and BF16 is the same architecture → same config, none of the pod bugs.
  Make it **lean**: `solve` + `validate_plan`, plain + steered, think=off — exactly the cells
  where plain-arm under-calling shows. Cost = cluster queue time, $0.
- **Option 2 (fallback, if cluster congested / no time):** reframe propensity *within*-model via
  `success = P(call)×P(correct|call)` (precision-internal — does not rest on comparing a 16-bit
  9B to a 4-bit 35B), soften the cross-model "9B beats 35B" capability claim, and add one
  Limitations sentence on the size×precision confound.
- **Keep the completed no-tools BF16** as a minor appendix robustness note ("the 35B's *unaided*
  baselines are unchanged BF16 vs AWQ-INT4") — do not oversell it; it does not defend the
  headline.
- **Sonnet (§7A) is unaffected** — orthogonal (external generality + frontier contamination vs
  this internal precision confound).

---

## 8. Per-task contamination — typeset the grounded numbers (appendix)

The main-text Table 3 pools over five tasks, but 3,000/4,560 trials are `validate_plan`, so the
pooled Δ is ~66% one task. The per-task null is stronger and now verified (think=off, ≥9B,
canonical sweep5v2 vs anonymized sweep6):

| Model | solve | validate_domain | validate_problem | validate_plan | simulate |
|---|---|---|---|---|---|
| Qwen3.5-9B | +0.7 | +1.1 | +3.7 | −0.4 | +0.0 |
| Gemma-MoE-26B | +0.3 | +2.8 | +3.0 | +0.4 | +0.0 |
| Qwen3.6-35B | +0.3 | +2.5 | +1.0 | −1.9 | +0.0 |

mean |Δ| = **1.2pp**, max **3.7pp**, 15 cells. Note every nonzero drift is *toward the
anonymized set* — the opposite of memorization (which would favor canonical). Add one sentence
to the contamination paragraph: *"the per-task breakdown (appendix) shows the small residual
drift favors the anonymized corpus, ruling out memorization in the expected direction."*

---

## 9. Prioritized action plan (vs. Jul 21 abstract / Jul 28 full)

**Must-do (writing/re-analysis only, no new sweeps):**
1. §0/§5 reframe: abstract + intro + new Discussion foregrounding invocation propensity & the
   general lesson.
2. §1 `validate_domain` balanced-accuracy correction (the one place the draft is wrong).
3. §2 decomposition table + Rewrite 2.
4. §4 three statistics sentences (clustering, disjoint-CI conservativeness, no FWER).
5. §6 RQ enumeration + real title.

**High-ROI strengthening (FUNDED — see §7A):**
6. **[LOCKED] Sonnet 4.6 no-tools, `simulate` + `validate_plan` + `validate_problem`, both
   corpora, full N, think=off, Batch API ≈ $118** — sole-source at the frontier + two
   contamination probes. (`validate_domain` optional +$5; skip `solve`.) Pilot ~$5–10 first.
   (GPT-OSS-120B considered and set aside — §7B.)
7. §3 failure-type taxonomy figure + Fig 2 `P(correct|call)` overlay.
8. **[DECIDED — see §7D] Precision control for the size×precision confound:** run BF16-35B
   *with tools* (lean: `solve` + `validate_plan`, plain+steered, think=off) on the cluster
   `rtx_pro_6000` (~free), NOT the pod. Fallback if cluster/time tight: reframe propensity
   within-model + a Limitations sentence. Abandon the broken pod with-tools run.

**Nice-to-have:** per-task contamination appendix table (§8), robustness figure in main body,
cost-of-pass annotations on Fig 3, metric-flip inset.

**Do not let it gate submission:** PlanBench. **Abandon (sunk cost):** the RunPod with-tools
BF16 run (§7D).

---

## §A. Data provenance (so every number above is reproducible)

All numbers recomputed from `results/sweep5-cluster-20260530/slurm_vllm_*_off_*/trials.jsonl`,
fields under `result.*`. Arm encoding confirmed empirically: **prompt_variant 11–13 = plain,
14–16 = steered**; no-tools cells use variants 11–13. `validate_domain` negatives are
`problem_name == "domain_neg"` (oracle INVALID); positives are everything else (oracle VALID),
giving the 5:1 ratio (300 pos / 60 neg per ≥9B cell). `validate_plan` uses `plan_label`
`v1–v5` (valid) vs `b1–b5` (broken), balanced 1:1. Canonical = `*_sweep5v2`, anonymized =
`*_sweep6`. Decomposition uses `tool_selected` for P(call) and `success` conditioned on it.
The extraction commands are in the chat transcript that produced this doc; re-run them against
the same dirs to regenerate every table here.

> **One data quirk to be aware of:** the `Qwen3_5_9B_off_tools_all_minimal_sweep5v2` corpus
> does not contain `simulate` rows (the 9B simulate cell lives in a separate run dir). It does
> not affect any conclusion above — the silence-not-error mechanism is fully carried by Gemma
> and the 35B — but confirm the 9B simulate source before quoting 9B simulate decomposition
> numbers.
