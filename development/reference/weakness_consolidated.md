# Consolidated weakness list (2026-09-19)

*One merged list of everything the two weakness reviews found, with duplicates removed
and the places where they disagree worked through. Written as the input for a later
session that will propose an improvement plan. Nothing in the tex was changed and
nothing was run.*

> **Status 2026-10-10.** Q1 to Q4 were answered on 2026-10-02 and carried out: the
> delivered rerun ran and read out on 2026-10-09 (`reference/delivered_rerun_readout.md`,
> `NUMBERS.md` "Delivered rerun"), PR #110 fixed tex line 441, and the four re-analyses
> are in `reanalysis_*.md`. Q5 to Q10 are still open. Each now carries a recommendation
> written after the rerun readout, and a new **Q11** asks the question the rerun raises.
> **Answer Q11 first**: Q6, Q7 and Q9 depend on it.
>
> **2026-10-10 (later): Omer accepted every recommendation, Q5 to Q11.** The action plan
> is `development/weakness_action_plan.md`; this file (moved to `reference/` on 2026-10-10) is now the record of why.

## Sources

| tag | file | how it was written |
|---|---|---|
| **R** | `development/referee_weaknesses.md` (untracked on `main`, tex at `972b275`) | One referee-style read of the paper only. No code, no data, no `development/`. 34 items, R-W1 to R-W34. |
| **V** | `development/weakness_review.md` (branch `docs/weakness-review`, `0db8445`, PR #109, tex at `3196112`) | Three independent cold readers (P = planning reviewer, M = methods and statistics, A = agent practitioner) plus an insider audit against `NUMBERS.md`, the logs and the harness. 9 items, V-W1 to V-W9, and decisions Q1 to Q7. |

The two were written without seeing each other, so agreement between them is real
signal. Both source files are left in place. This doc replaces them as the working list.

**Reading notes**

- Items here are numbered **C1 to C22**. Each one names the source items it merges.
- Tex line numbers are carried over from the sources. R and V read the tex one small PR
  apart (#108, one sentence), so lines can be off by a few.
- **Verification status (2026-09-19, `/verify-claims` run on this doc).** Every statement
  about what the paper says was checked against `paper/main.tex` at `972b275` by three
  independent full reads: about 170 statements, **none wrong**, 23 imprecise (now
  corrected in place), 3 readable only from the figures and 1 that is our own knowledge
  and not in the paper (all now marked). Insider claims and
  headline figures were checked against `NUMBERS.md`, the logs and the canonical corpus.
  See "Verification results" near the end for what changed and what is still open.
- This verifies the *reviews' description* of the paper and of our records. It does not
  make a figure paper-ready: before any number goes into the tex, `NUMBERS.md` first, then
  `/verify-claims` on that edit.

## In short

- **Both reviews put the same weakness first.** The paper names the delivered answer as
  its main outcome and then cannot measure it on the open-model tool runs, because only
  the first 500 characters of each answer were saved (C1). Four readers in total (R plus
  P, M, A) reached this independently.
- **Both recommend major revision.** V's three readers add "leaning reject".
- **They agree on the top five**, in nearly the same order: C1, then the title claim
  living only on the lenient score (C2), one model carrying the invocation story (C3),
  the "plain" arm that already tells the model to use the tool (C4), and the
  over-stated delivery gap (C5).
- **V adds facts a paper-only reader cannot see.** The most important: the tex says
  JSON-constrained decoding was active, and our own audit showed it never reached the
  server (C6). Also: the rerun the paper promises has never been run, and it is cheap
  (C1).
- **R adds breadth.** About fifteen items V does not have: test-data description,
  prompt-wording swings, ignored pairing, the cost price claim, PlanBench extractor
  errors, a list of sentence-level errors, missing examples, and more.
- **Eight disagreements**, D1 to D8 below. Most are about reading or sequencing. One is
  a plain factual error in V (D1, VAL).
- **Verification changed three things that matter for the plan.** (1) Both reviews read
  Gemma's 21% against 0.9% as a serving-software effect; the corpus shows it is the
  reasoning mode (C3, D2). (2) The PlanBench "well inside plus/minus 7.5" sentence fails
  its own pre-registered test on the numbers the tex quotes (C9). (3) The rerun in Q1 has
  no prereg file yet (C1).

## Map of the merge

| C# | Weakness | From R | From V | Who has it | Fix type |
|---|---|---|---|---|---|
| C1 | Main outcome not measured on open tool arms | W1, W23 | W1 | both, ranked first by both | new experiment (guard named in the tex; prereg file still to write) |
| C2 | Title claim shown only on the lenient score; "-67" compares two different scores | W2, W3 | W5, W1 | both | rewrite, mostly resolved by C1 |
| C3 | Invocation story is one model, one task; software cause not ruled out (the 21% vs 0.9% hint is a reasoning-mode effect, see F1) | W4 | W2 | both | $0 transcript check + small arms |
| C4 | The "plain" arm already tells the model to use the tool | W5 | W2 | both | rewrite + small arms |
| C5 | Delivery gap: thin evidence, may come from the test setup, residual at 64K unexplained | W6, W7 | W3 | both | rewrite + $0 re-analysis |
| C6 | Unaided baselines are handicapped; simulate "cannot be done unaided" is contradicted; **tex line 441 is false** | W11, W12, W13 | W4 | both; the false sentence is V only | rewrite (mandatory) |
| C7 | Tool side scored leniently, no-tools side strictly, in many analyses | W8 | W1 | both | resolved by C1, else rewrite |
| C8 | The answer key comes from the same tools | W9 | W5 | both, see D1 | rewrite + optional cross-check |
| C9 | Statistics: multiplicity argument, domain clustering, pairing, vote counting, PlanBench equivalence sentence | W18 to W21 | W6 | both | $0 re-analysis |
| C10 | Main outcome chosen after the data; pre-registrations cannot be checked | W22 | (partly) | R | rewrite, add links |
| C11 | Test data and prompts barely described | W10 | none | R only | rewrite |
| C12 | Results swing with prompt wording and this is not shown | W14 | none | R only | $0 re-analysis |
| C13 | Arms ran on different vLLM versions; the rerun failed parity | W15 | W1 (insider) | both, see D2 | rewrite |
| C14 | Small, narrow model roster | W16 | W7 | both, see D6 | new experiments (expensive) |
| C15 | PlanBench: one model, one domain, extractor errors, untestable "main result", never shows invocation | W24, W25, W26 | W7, W6 | both | rewrite + $0 re-analysis |
| C16 | Cost analysis: tokens only, price claim wrong, favorable number is on the lenient score | W27 | W1 (one line) | mostly R | $0 re-analysis + rewrite |
| C17 | Novelty and related work, including against our own arXiv version | W28, W29 | W9 | both | rewrite |
| C18 | Several claims go beyond the evidence | W30 | W3 | mostly R | rewrite |
| C19 | The paper is hard to read; the story is buried; three framings | W31, W17 | W8, clarity test | both, see D5 | rewrite, partly after C1 |
| C20 | Sentence-level and scorecard errors | W32 | none | R only, see D3 | rewrite |
| C21 | Missing breakdowns and example transcripts | W33 | none | R only | $0 re-analysis + rewrite |
| C22 | Still in conference form; no code link | W34 | none | R only | known (N3 reformat) |

---

## A. The core claims (both reviews agree)

### C1. The main experiment cannot measure the paper's own main outcome

*Merges R-W1, R-W23 (part), V-W1. Ranked first by R and by all three of V's readers.*

- **The problem.** The paper declares the delivered answer primary (tex 513-529). The
  open-model tool runs saved only the first 500 characters of each final answer
  (670-672, 1688-1698). So the paper reports ranges instead of numbers, and many ranges
  are too wide to decide anything (Gemma validate_plan: 6.6 to 99.6).
- **The damage.** validate_plan (two thirds of all trials) is undecided for every
  headline model. So is simulate. Solve is undecided for two of three. M counts 4 of 15
  headline cells firmly decided. `NUMBERS.md` agrees: 13 of 25 availability cells
  undecided with thinking off.
- **The tension with the paper's own rule.** "Tool-verified numbers are never
  headlines" (523-524), yet the title, the abstract's 21 to 94% and 99%, RQ5, RQ6,
  cost-per-success and the robust floor are all mechanism-layer quantities. (Precisely:
  21 and 94 are call rates, 622/3000 and 2808/3000, and 99 is correctness given a call,
  617/622. Tool-verified success is 20.6 to 92.6.)
- **The paper invites the request.** Limitations says the rerun is feasible and
  pre-registers it as "our declared answer should a reviewer require those cells decided"
  (1693-1698). All four readers say they would require it.
- **What only we know (V insider, verified 2026-09-19).**
  - The rerun the paper pre-registers has **never been run** (memo §9: "DEFAULT = NOT
    RUN"). The full-storage rerun that exists (`iss024d`) used a different configuration
    (thinking on, `--reasoning-parser none`). See D2.
  - **Correction to V:** the rerun is pre-registered only by that Limitations sentence,
    which names the guard. There is **no standalone prereg file** for it
    (`development/reference/` holds preregs for iss024d parity, the budget probe, nt-ster
    and PlanBench only). One has to be written, and `/freeze-protocol` run, before the
    job. So "already specified" is only partly true.
  - No harness code is needed. `RESPONSE_SNAPSHOT_LEN = 16384` in `pddl_eval/runner.py`
    since 2026-06-26 (`b07b394`; V said 06-25).
  - Size: headline models, plain and steered arms, 4,560 each, **about 27K trials**, $0,
    cluster GPU-hours.
  - Known risk: serving drift since May (vLLM 0.22.0). The prereg already carries the
    guard: a Gemma negative control and a plus/minus 5 point equivalence test against
    the canonical tool-verified rates.
  - V withdrew its own earlier "contingency only" recommendation
    (`advisor_brief.md` question 5) after seeing three readers stop at the same place.
- **Either result helps.** If not calling really costs delivered answers, the title is
  proven on the main outcome and most ranges become numbers. If the model answers well
  without calling (the existing rerun hints at 30 to 63% correct), the honest title is
  about delivery, and we learn it before a reviewer does.
- **Fix:** new experiment, already specified. V's readers estimate it removes 60 to 75%
  of this damage and a good part of C19. It also largely resolves C2 and C7.

### C2. The title claim is shown only on the lenient score, where it is close to true by definition

*Merges R-W2, R-W3, V-W5 (tautology part), V-W1.*

- **Near-tautology.** On the tool-verified score a trial with no tool call fails
  automatically (the appendix says "by construction", 1799-1808). A well-formed call is
  correct by construction too, because the tool made the answer key. So success =
  (called) times (almost 1). That nearly all the variation sits in "called" is
  arithmetic. P(correct | call) of about 99% is the tool agreeing with itself.
- **"-67 points" compares two different scores.** The 88% is a no-tools *delivered*
  score. The 21% is a with-tools *tool-verified* score. The no-tools arm has no tool
  path, so its tool-verified rate cannot fall. In the existing rerun Gemma's tool path is
  0.9%, yet 30 to 63% of its delivered answers are correct. So the real harm to the user
  could be small, zero, or a gain. The paper admits this ("Not calling is not the same as
  not answering", verbatim at 960-961 and 1075-1077, paraphrased in four more places) and
  still puts -67 in the introduction, methods, scorecard and conclusion (157, 587, 779,
  1051, 1752). Tex 1051 itself labels the whole 88 to 21 move a "tool-verified rate",
  although the 88 is the no-tools baseline.
- **Insider check (V):** fair, with one correction. Only the no-call half ("a missing tool
  call fails by construction") is appendix-only (1804-1805). The other half ("a correctly
  invoked tool is correct by construction; what the experiment measures is therefore
  whether and how the model invokes the tool") is already in the body (311-312, 329-332).
- **Fix:** rewriting: say "by construction" in the body, drop -67 as a headline or
  replace it with a like-for-like comparison. M rates this the most fixable item (about
  80%). It stops mattering once C1 gives delivered numbers.

### C3. The invocation story is one model on one task, and a software cause was not ruled out

*Merges R-W4, V-W2 (first half).*

- **One model.** Only Gemma-MoE collapses (calls the tool on 21% of validate_plan
  trials). The 35B moves -9, the 9B moves +13. Both frontier models call the tool on
  almost every trial, and so does PlanBench. (The tex frames it as the tool path
  collapsing "for two of three" models, 1050-1053; "only Gemma" is the reviewers'
  reading of a -9.) That model is a community-made 4-bit compressed build (389-392). It
  is served through the `gemma4` tool-call parser, which the tex never names.
- **Both reviews read 21% against 0.9% as a serving-software effect. The data say it is
  the reasoning mode (checked 2026-09-19).** Gemma's tool path is 21% in the main sweep
  (thinking off) and 0.9% in the rerun (thinking on, reasoning parser off). Both reviews
  took the parser to be the cause. But the canonical corpus has the matching cell with
  the parser **on**: Gemma, thinking on, plain arm, validate_plan calls the tool on 19 of
  3,000 trials = **0.6%** (steered: 1,327 of 3,000 = 44.2%). So 0.6% with the parser on
  and 0.9% with it off are the same; the drop from 21% comes from turning thinking on
  (tex 610 says as much: "under think=on the plain arm largely stops calling the tool").
  This removes one piece of evidence for "software cause", and adds a different point:
  the steering sentence only recovers 44% with thinking on, against 94% with thinking
  off, so "one sentence fixes it" is a thinking-off result.
- **No evidence of what the model did instead (R).** The paper says Gemma "reasons in
  prose" but shows no transcript and no count. A reviewer will ask whether the model
  *tried* to call the tool in a format the server did not recognize. In the logs that
  looks the same as not calling. The worry is fair: the paper itself reports one parser
  setting that silently produced 9,120 empty answers with no errors (2119-2126). Caveat
  on the analogy: that was the *reasoning* parser in the no-tools steering control, not a
  tool-call parser. It shows silent parser failures happen in this stack; it is not
  evidence about Gemma's tool calls.
- **A's summary:** "A bottleneck removed by one sentence, absent at the frontier,
  unmeasurable at the answer, and shown in one INT4 checkpoint, is a prompt bug report."
- **Fix:**
  - $0, if the stored data allow it: read and count the Gemma no-call trials. Look for
    malformed tool-call attempts in the saved text. (Feasibility to check: only 500
    characters of the final answer were saved.)
  - Cheap: test the official Gemma weights (R). Add more families inside the
    plain-versus-steered contrast (both). See D6 for timing.

### C4. The "plain" arm already tells the model to use the tool

*Merges R-W5, V-W2 (second half). V's insider check calls this "the sharpest point".*

- The paper presents "tool merely available" against "model told to use it". But the
  plain arm's system prompt, printed in the paper (463-474), already says "LLMs cannot
  reliably check plan correctness from training alone. **Use the available validation
  tool**". So 21 to 94% is really "instruction in the system prompt" against "instruction
  repeated in the user message, naming the tool and its arguments".
- Limitations half-admits it ("differ by a one-line policy/format clause", 1664-1667).
  The headline wording does not.
- **A second explanation for Gemma.** Some model families give system prompts less
  weight or merge them into the user turn. P adds that Gemma's chat template has
  historically had no native system role. We never examined this.
- **Prompts differ in more than the tool (R).** The no-tools prompt carries the
  answer-format reminder. The tool prompt carries the "cannot reliably check" sentence.
- **Fix options (V):** (a) rewording only: stop saying "merely available", retitle;
  removes about a third of the damage. (b) a small add-on to the C1 job on Gemma
  validate_plan, about 3K trials per arm: a truly neutral system prompt; the directive in
  the system prompt instead of the user turn; optionally a forced call. R asks for the
  same two arms plus the same format line in both. If the effect survives a neutral
  system prompt, the finding gets much stronger. If not, the invocation story as written
  does not stand.

### C5. The delivery gap: thin evidence, possibly created by the test setup, and a residual nobody has explained

*Merges R-W6, R-W7, V-W3.*

- **Thin evidence for a "law" (1285-1286).** Two models from one vendor, and 100 trials
  on each of the two tasks that show a gap (n per task is 120 / 200 / 1,000 / 100 / 100,
  tex 980). The 5-point plan gap is 5 failures out of 100, twice ("the same five-failure
  count", "identical at two frontier tiers"), inside a Wilson interval of [88.8, 97.8].
  Answer length is tied to the task (five tasks in three length classes), so length
  cannot be separated from everything else that differs. Nothing looks at length
  *inside* one task.
- **The paper's own open-model numbers disagree with "the gap tracks answer length
  rather than model strength" (185, 929-931; R only).** For the same kind of answer (a
  plan), open models lose far more between the two scores. The 9B: 99% tool-verified
  against a delivered range of 26.0 to 58.7 (1097, 839). Gemma: delivered at most 35.3
  (841). At the frontier the loss is 5. *Two parts of this are readable only from the
  figures, not the text:* Gemma's own tool-verified solve value (the text gives only the
  range 63 to 99%), and the steered-arm claim that all three headline models lose at
  least 35 points (`paper/figures/solve.pdf` labels of about 28 to 65, 24 to 59, 17 to
  48). Re-derive both from `pooled_e2e_table.csv` before relying on them.
- **The budget explanation missed its own test.** The pre-registered budget probe failed
  its criterion for Sonnet (p = 0.069). At a 64K budget, 30 to 35% of tool trials still
  failed although none hit the cap. For Haiku, tools against no tools was 65% against 58%
  with overlapping intervals. V's insider check: accurate; the frozen readout says the
  same.
- **The gap may be a property of our answer contract (both).** The model must retype the
  tool's plan or whole trajectory into its final message under a token cap. A trajectory
  is graded by exact equality with the oracle's; a plan is graded by validity, not by
  equality with the tool's plan (333-337). Real systems pass tool output through in code.
- **Two setup details make it worse (R only).** The tool-arm system prompt shown in the
  paper has no instruction about the final answer format, and the user prompts are never
  shown. And about a third of open-model solve trials in the tool arms end "truncated"
  with thinking off, and about 8% do so on plan validation where the answer is one word.
  (These two shares are read off the bars of `failure_taxonomy.pdf`, about 37 / 34% and
  7 / 8% pooled over the headline models; the text and caption never state them.) A model
  that holds the answer and still writes until the cap suggests looping or a prompt
  problem. The paper does not look into it (885-904).
- **Fix:**
  - Rewriting: drop "law" and "identical"; state the gap as a property of restating long
    outputs under this contract; show the prompts.
  - **$0 re-analysis we can do now (V):** the 64K probe has full storage, so the 30 to
    35% residual failures can be classified (wrong trajectory, wrong wrapper, partial).
    V calls it the most interesting number in the section.
  - $0 (R): gap against answer length within one task; inspect the truncated tool-arm
    transcripts.
  - Optional new arm: the harness returns the tool output itself (pass-through).

### C6. The unaided baselines are handicapped by the setup, and the tex says otherwise

*Merges R-W11, R-W12, R-W13, V-W4. Contains the one item that must be fixed whatever
else is decided.*

- **The false sentence (V insider only).** Tex 441-442 says "per-task
  JSON-schema-constrained decoding remains, so the baseline is not held back by
  formatting alone". Our audit (PR #94; corrected figures in `paper_notes` 2026-08-17)
  found the constraint **never reached the server**: 0 of 58,581 provable validate rows
  emitted any JSON, conformance under 2% on every cut, and the solve and simulate prompts
  tell the model to follow a JSON schema "provided by the format constraint" that did not
  exist. `STATUS.md` Job 4 says the audit "fed the Limitations wording", but the sentence
  is not in the tex and line 441 asserts the opposite.
- **R saw the symptom without the cause (R-W13).** "JSON-constrained decoding" sits next
  to "67% unparseable" and "format compliance stays 0%". Forced-schema output should
  almost always parse. M and A noticed the same. V's fact explains it.
- **Why it matters.** The "floor" on solve and simulate is mostly a format failure. Only
  3% of unaided simulate failures are wrong content (tex 866). Recomputed from
  `results/sweep5v2-live` on 2026-09-19: headline models, thinking off, 612 / 262 / 26
  of 900 = 68% unparseable, 29% truncated, 3% wrong content, which matches the tex. All
  26 wrong-content rows come from the 35B; no other model ever got far enough to be
  wrong. Over all 3,000 rows: 1,772 truncated, 1,202 unparseable, 26 wrong
  (`NUMBERS.md` row 82 reproduces exactly).
- **"Simulate cannot be done unaided" is contradicted inside the paper (both).** Main
  text: 0 of 3,000. But the appendix control shows 11 to 28% with thinking off (on
  determinate rows only, in cells the control itself labels uninformative); the
  budget-decoupled control shows 22 to 40% (content-correct under a tolerant grader,
  thinking on, Qwen only); Sonnet gets 42 to 61%; and the failure figure says 93% of
  those answers are "censored", which means unknown. The paper keeps the
  heading "Two Tasks the Model Cannot Do Unaided", keeps simulate as "sole-source" with
  +83 to +97, and uses "+100, +93, +77" in the difficulty analysis. M: "The sole-source
  regime is manufactured by the grader and the cap." See D8 on what caused the zero.
- **A circular argument (both).** Tex 874-875 says re-grading the stored answers recovers
  at most 0.7%, "so the recovery comes from the budget, not the grader". Tex 2042-2044
  says those stored answers are 500-character snapshots that "cannot be regraded". A cut
  snapshot cannot hold a full trajectory, so the 0.7% proves little. A third place adds to
  the confusion: the corpus table (667-668) lists the no-tools arm as "full text at
  grading time", which is true of the online grader and not of anything re-graded later.
- **The fair comparison is missing (R only, R-W11).** With thinking off, the model
  answers directly under a 6,144-token cap. With thinking on, reasoning and answer share
  one small budget and up to 92% of no-tools trials are cut off. Giving the model enough
  room was done only in a side control, only for Qwen, only without tools, and it moved
  validate_plan by 34 to 60 points for the 4B and 9B. So "the model doing its honest best
  alone" against "the model with tools" is not in the main results.
- **Fix:** rewriting. Mandatory for line 441 plus a Limitations sentence (figures through
  `/verify-claims`, quote the 08-17 entry). Retitle the section, carry the qualifier on
  every 0/3,000. Overlaps `consistency_read_findings.md` rows A4, A5, A6, A8.

### C7. The tool side is scored leniently and the no-tools side strictly

*Merges R-W8, V-W1 (M's quote).*

- Because delivered scores are missing for the tool arms, many analyses use the
  tool-verified score on the tool side and the strict delivered score on the no-tools
  side: RQ5, RQ6, cost-per-success, the "robust floor", the "realizable benefit", and the
  whole reasoning-mode robustness check (789-792, 1109-1111, 1162-1165, 1201-1221).
- The paper's own data show how far apart the two scores can be (99% against at most 35
  to 59% on solve). Each place is labeled. The net effect is still that most numbers
  that favor the tool are computed on terms that favor the tool. M: the authors "report
  whichever layer is exact".
- **Fix:** resolved by C1 for the headline models. Otherwise rewriting.

### C8. The answer key comes from the same tools being tested

*Merges R-W9, V-W5 (oracle part). See D1: the two reviews disagree on whether an
independent check already exists.*

- Ground truth is made by calling the tools the model can call (326-332). For the
  validation tasks, "valid" means "whatever this library accepts". A bug or quirk in the
  validator cannot be detected, because tool and key always agree, and the no-tools model
  is marked wrong whenever it disagrees with the quirk.
- The paper calls every tool "sound" and "correct by construction" (311-312). It does say
  a solve answer counts only if the plan is "independently certified valid" (333-334),
  but never names the certifier, and no independent validator is named anywhere for the
  main suite.
- **Fix:** rewriting, plus a cross-check of a sample against an independent validator,
  with the disagreements reported (R). See D1 for what "independent" can honestly mean
  here.

---

## B. Statistics and pre-registration

### C9. Statistics

*Merges R-W18, R-W19, R-W20, R-W21, V-W6.*

- **The multiplicity argument spends one correction twice (both).** The paper says
  widening intervals by the square root of 2.7 already gives z of about 3.2, stricter
  than Bonferroni (592-600). The widening only repairs intervals that were too narrow
  because trials on one instance are correlated. After that repair, 1.96 is just an
  honest 95%. Nothing is left to pay for about 30 comparisons. It is also unclear whether
  the widening is part of the decision rule or a check done afterwards (561 against 594).
- **Domain clustering is ignored in the main intervals (both).** All instances come from
  20 domains. The main intervals only account for the three wordings per instance. The
  steering control clusters both on domain (k = 20) and on problem instance (k = 220) and
  says the wider of the two "governs" (1921-1923), so the paper is inconsistent with
  itself.
- **Pairing is ignored (R only).** The arms share instances, but the main verdicts ask
  whether two separate intervals overlap. That is not a test of the difference. PlanBench
  uses McNemar and the control uses paired differences.
- **Vote counting and hand-set thresholds (R only).** YES / MIXED / NO comes from
  counting models with non-overlapping intervals. The "robust floor" uses +30 points with
  no stated reason. The eligibility gates in the steering control are in D7.
- **V only:**
  - One GLMM, on the largest tool-verified contrast, log-odds +7.5 with SD 0.10 (the
    variational fit already tracked in N3).
  - RQ1 reads YES only because headlines are restricted to the 9B and larger models.
  - The contamination "null" is absence of disjoint intervals, never an equivalence
    test, and it sits beside PlanBench, where renaming alone takes Haiku from 43.8% to
    0.7%.
  - **One sentence recomputed (tex 1437-1439).** The with-tools paired gap between
    Blocksworld and Mystery is 3.5 points (119 against 140 discordant, n = 600), "well
    inside the plus/minus 7.5 point margin". V recomputed the paired interval: 90% CI
    [-0.9, +7.9], 95% CI [-1.8, +8.8]. The point estimate is inside the margin; the
    interval is not.
  - **Verified 2026-09-19, and V's hedge resolves against the tex.** The prereg
    (`reference/planbench_wt_prereg.md` L290) defines the margin as a **paired TOST** at
    plus/minus 7.5 points, so the test is on the interval, not the point estimate. I
    recomputed both readings (Wald paired SE): first-draw, which the tex quotes (b = 119,
    c = 140): 90% CI [-0.91, +7.91], TOST p = 0.068, **criterion not met**. Last-attempt
    (b = 119, c = 132, 2.2 points): 90% CI [-2.17, +6.51], TOST p = 0.022, criterion met.
    So the equivalence verdict flips with the first-draw rule that Omer chose on 08-06 for
    other reasons. The results doc (L43, L293) calls both "within the margin" on the point
    estimate. The tex gives only the point estimate and a McNemar p = 0.214, no interval.
    Under the equivalence-wording rule the first-draw reading is "criterion not met /
    unresolved". An exact-method TOST could differ slightly from my Wald figure; the
    gap to 0.05 is small, so whoever edits this should compute it the way the prereg's
    analysis script does. Reported here, nothing edited.
- **Fix:** $0 local re-analysis: domain-cluster bootstrap for the headline intervals,
  paired tests for the arm contrasts, the standard-estimator GLMM refit, equivalence
  tests for the two nulls, and a short statement of what was pre-specified and what was
  not.

### C10. The main outcome was chosen after the data, and the pre-registrations cannot be checked

*R-W22. V touches it only in passing.*

- The paper says the storage decision was made "before the delivered surface was fixed
  as primary" (1688-1691). So the primary outcome changed after the main data existed.
  The main study is not pre-registered. Only later side studies are, with no registry or
  link, so a reader cannot verify them.
- The declared deviations are serious (2106-2143): the control roster was enlarged from
  three models to four after interim results; a code review found three defects in the
  hash-frozen analysis code after the first readout, and it was corrected, re-frozen and
  regenerated (all six unit verdicts unchanged); the thinking-on arm came back void
  (9,120 of 9,120 rows empty in one unit, 3,822 of 3,824 in the other) and was rerun with
  the reasoning parser off.
  Declaring these is to our credit. Together they read as a fragile pipeline. V's reader
  A makes the matching point that the disclosed analysis bug (censored rows once scored
  as successes) costs trust where it sits.
- **Fix:** rewriting. Give the prereg documents a checkable home (repo link, hashes).
  Say plainly which outcome was primary when.

---

## C. Experimental design

### C11. The test data and prompts are barely described

*R-W10 only.*

The paper does not say: how the invalid domains, problems and plans were made or what
errors they contain; how large the problems and plans are; how the short / medium / long
and object-count bins are defined; what goes into the tool-call arguments, file contents
or paths (that the PDDL files are handed over inside the prompt is stated, but only in
the PlanBench section, 1348-1349, not in Methodology);
which tools the model can see in a trial (all five or only the matching one, which
decides whether tool selection is tested at all); the actual user prompts and their three
rewordings (366-381, 498-502, 1113-1126). Without these the baselines cannot be
interpreted. Example: one model answers INVALID "almost reflexively" and gets 95% on the
negatives. Whether that is easy or hard depends on how the negatives were built.

- **Fix:** rewriting only. All of it is known to us.

### C12. Results swing with prompt wording, and the paper does not show it

*R-W14 only.*

- The appendix shows that rewording the task moves unaided success by 14 to 31 points on
  solve and up to 36 on simulate (1929-1934). These are the steering control's
  paraphrase-floor values, measured on its anchor arm and not on the main sweep
  (`NUMBERS.md` row 149: solve 14.0 to 31.0, simulate 5.56 to 36.33). So the paper's
  unaided solve floor of 8 to 11% (831-833) is an average over wordings that may run from
  near 0 to near 30.
- The main results pool the three wordings and never show them separately. The frontier
  tool runs use one set of wordings and an unexplained "prompt v11". Every trial is a
  single greedy sample, so sampling variation is never measured (378-381, 709, 1272-1273,
  1641-1643, 1929-1935).
- **Fix:** $0 re-analysis: a per-wording table. Define "prompt v11".

### C13. Compared arms ran on different software versions, and the rerun failed parity

*R-W15, with V-W1's insider facts. See D2.*

- For Qwen3.5-4B and 9B, the no-tools runs used vLLM 0.20.2 and the with-tools runs
  0.22.0 (401-413; `NUMBERS.md`: 4 cells, 36,480 trials). The availability gap for those
  models is mixed with a version change. The paper notes the Qwen3 tool-call and
  reasoning parsers are byte-identical across the two releases. The reassurance check
  (pooled +0.4 points [-0.9, +1.7]) was run on the 0.8B model, which is not a headline
  model and fails in its own way.
- The full-storage rerun failed its parity test, so the paper calls it a "different
  apparatus" (692-694). A reviewer reads that as: the authors could not reproduce their
  own sweep. D2 explains why that reading is understandable and what the paper leaves
  out.
- V insider: the August anchor arm re-measured the *no-tools* rates within about 1
  point pooled (`NUMBERS.md` row 152: +0.1 to +1.0; one per-task cell, 35B
  validate_domain, moved +6.7). That is encouraging and says nothing about the tool arms.
- The tex gives the rerun's settings (thinking on, reasoning parser off, 680; a
  "parser-off truncation shift" on solve, 696) but no sentence says why parity failed.
- **Fix:** rewriting. The C1 rerun, run on one version with its equivalence guard, also
  answers this.

### C14. The model roster is small and narrow

*Merges R-W16, V-W7 (roster part). See D6 for the timing disagreement.*

- Five open models from two families, four of them Qwen. Headline conclusions use three.
  Two of those are community 4-bit builds and the third is 16-bit, so size and precision
  are mixed up (the paper admits this). Frontier evidence is two models from one vendor.
  PlanBench is one model.
- The paper's own discussion says how readily a model delegates is "plausibly a property
  of its alignment recipe as much as its scale" (1608-1609). The study samples about
  three recipes. No Llama, Mistral, DeepSeek, GPT or Gemini (384-395, 1104-1106,
  1644-1645, 1658-1663).
- V insider: true and mostly owned in Limitations. The Llama probe answers a small part.
- **Fix:** new experiments, the most expensive on this list.

### C15. PlanBench

*Merges R-W24, R-W25, R-W26, V-W7 (PlanBench part).*

- **One model, one domain family (both).** Everything is Claude Haiku 4.5 on Blocksworld
  and its renamed twin, which the paper confirms are the same problems.
- **It never shows the paper's main phenomenon (both).** The model called the planner in
  every trial, with no plain-versus-steered contrast, so PlanBench says nothing about
  invocation. P would rather see it on two or three open models, plain against steered.
- **The tools result repeats Huang and Zhang (both).**
- **R only:**
  - 501 instance files but 600 instances per cell, unexplained (1354-1357).
  - Measurement errors as large as the effects are left uncorrected (1528-1547). In 479
    of 600 Mystery no-tools trials the extractor picked up stray actions from the model's
    reasoning. In the tool arm 125 of 569 delivered plans were thrown away because the
    extractor cannot read the model's notation. The paper says a better parser would lift
    that cell above 90%, then says "we correct for none of them". The plain-Blocksworld
    gain (+20.5) is the same size, and the errors hit the two arms unequally.
  - The result the paper calls "the main one" (1366) sets a current model beside 2023
    GPT-4 numbers from another lab, grader and time. The paper calls that row "context
    only" (1405-1406) and still draws a conclusion from it (1410-1412). It also leaves out published reasoning-model results (the o1 evaluation
    reported about half of Mystery Blocksworld solved), so "0 to 72" overstates the gap to
    the best unaided alternative.
- The PlanBench equivalence sentence is in C9.
- **Fix:** rewriting, plus a $0 re-analysis with a corrected extractor reported beside
  the as-shipped numbers.

### C16. The cost analysis counts tokens only, and its price claim is wrong

*R-W27. V only notes that cost-per-success is on the lenient score.*

- "Invariant to the per-token price" holds only if input and output tokens cost the same.
  They do not. The tool arm is input-heavy and the no-tools arm output-heavy, so real
  prices would shift the comparison a lot. Planner compute time and response time are not
  counted (1158-1176, 1185-1191).
- The favorable number (0.3 to 0.4 times the cost per success on solve) uses the lenient
  score. On the delivered score the paper's own range is 0.6 to 1.6 times, which includes
  "more expensive" (`NUMBERS.md` has 0.65 to 1.64). At the frontier the tool costs 3.1
  times (Sonnet) and 6.1 times (Haiku) more per delivered solve success, and 5 to 11 times
  on simulate (1170-1176). So "Where the baseline is floored the tool pays for itself"
  (1166) is not supported on the primary outcome.
- Response time cannot be added: the paper itself says per-trial latency is not
  recoverable from the logs (1188-1191, 1706-1707). Planner compute time is never
  mentioned.
- **Fix:** $0 re-analysis with a realistic input-to-output price ratio, plus rewriting.

---

## D. Claims, novelty and presentation

### C17. Novelty and related work, including against our own arXiv version

*Merges R-W28, R-W29, V-W9.*

- **Against our own earlier paper (both).** The earlier version is cited once (314-318),
  for where the tools come from and for scale. Nothing says which conclusions are new,
  confirmed or reversed. It already covered the
  same five tasks and tools. V insider: the delta statement is planned for the cover
  letter (ISS-013); P's point is that it belongs in the paper too.
- **Thin related work (both).** 26 references. Missing lines: work on *when* a model
  decides to call a tool (for example MetaTool, When2Call); planning benchmarks with very
  similar tasks (ACPBench, Planetarium); reasoning models on PlanBench and the limits of
  self-verification (Stechly; Valmeekam 2023 and Kambhampati 2024 are cited, the
  reasoning-model follow-ups are not); LLMFP and the MCP tool-use benchmarks (only BFCL
  and tau-bench are cited). "None measures..." (261) comes 25 lines after the paper's own
  description of La Malfa as "the closest agentic system" (234-236). R's reference names are from
  memory and must be verified before citing. V insider: the competing-work notes already
  exist (verified 08-06).
- **The findings may read as unsurprising (both).** Stripped of vocabulary: a model may
  not call a tool unless told to, and long tool output retyped under a cap gets cut off.
  P: "That telling a model to call a tool makes it call the tool is not a JAIR-level
  finding." A: "put the instruction in the user turn, pass tool output through in code,
  don't wrap cheap verdict tasks: common practice".
- **Thin planning content (R only).** Complete PDDL files are handed to the model, so the
  tasks mostly test whether it can pass files to a function. The realistic setting, where
  the model writes the PDDL from English, appears only in PlanBench.
- **Fix:** rewriting. P estimates it removes 30 to 40% of this damage.

### C18. Several claims go beyond the evidence

*R-W30, plus V-W3 on "law".*

- "Delivery-gap law": two models, 100 trials each on the two tasks that show a gap.
- "Proves the capability boundary at the frontier", "a capability boundary rather than
  the limited scale": one model, thinking off. (R adds "8K cap"; the tex never states the
  cap used for the frontier solve cell.)
- "Direct empirical support for the LLM-Modulo thesis": no generate-and-verify loop is
  tested, only single-call delegation.
- "A single imperative sentence sufficed across the 4B to 35B range": it clearly mattered
  for one model.
- "The pattern survives reasoning mode": checked on the tool-verified score only; the
  delivered score there "adds no decided cell".
- *Where:* 163-164 and 1758-1759 ("survives reasoning mode"), 1201-1206, 1286, 1334-1336,
  1609-1617, 1764-1766.
- **Fix:** rewriting.

### C19. The paper is hard to read and the story is buried

*Merges R-W31, R-W17, V-W8, and V's clarity test. See D5.*

- **Did readers get the contribution? (V clarity test.)** All three cold readers landed
  on the two-gate reading (the model must call the tool, and must be able to restate its
  result), with 65 to 75% confidence. All three gave the same reason for doubt: the title
  names one gate, the abstract names two, the contribution list has five items, and the
  six RQs are a third framing. The scorecard marks the title's own question (RQ3)
  UNDECIDED on the main outcome.
- **Too many setups (both).** R counts at least six corpora plus the steering control and
  PlanBench. A counts nine, adding the drift rerun. On top: two scoring layers, three
  value shapes, 3+1 arms, two modes, six RQs, and at least three graders ("online",
  "delivered", "wrapper-tolerant two-metric") whose relation is never laid out (660-699,
  871-875, 900-902). The paper forbids comparing across setups, and then each key claim
  lives in a different one. P: it "reads as an audit of its own harness rather than as a
  finding". A: "I cannot tell which numbers the authors stand behind."
- **Private vocabulary and notation (R only).** The paper needs a table to explain how to
  read its numbers. Two interval notations. Terms such as delivered surface, mechanism
  layer, claim-adverse end, censoring bound, sole-source, robust floor, realizable
  benefit, delegation-terminal, apparatus, determinate rows ("mechanism layer" 42 times,
  45 with the hyphenated form; R's 36 missed line-wrapped occurrences; "apparatus" 22). Never defined: "prompt v11", "think=off equivalent", "trial keys",
  "apparatus pin", "first-draw counts", "summary-only failures". The appendix reads like
  a lab notebook. Limitations is one paragraph of about 80 lines. Much text explains what
  cannot be claimed, which buries what is claimed.
- **Fix:** rewriting. One corpus table, results first, controls to the appendix. Timing
  is D5.

### C20. Sentence-level and scorecard errors

*R-W32 only. Cheap and independent of any experiment.*

- The scorecard caption opens "six research questions on the delivered surface" (795),
  but two of six rows are tool-verified. (The same caption discloses this further down,
  799-802; the complaint is about its first sentence.)
- The scorecard is headed as open-model evidence (763), but RQ2's YES is "carried by the
  frontier tier and the baseline floor" (842-843).
- Tex 843-849 explains why delivered ranges sit far below the tool-verified rates by
  pointing to "invocation". That cannot be right. A tool-verified success already
  includes the call, so a gap *below* it must be a delivery problem.
- Tex 1066-1072 calls the three ranges "straddling bounds" and the gap undecided "in both
  directions". The scorecard repeats "straddling" at 780-781. See D3: only one of the
  three actually straddles.
- In the abstract, "at both tiers" is unclear: two frontier models, or open and frontier?

### C21. Missing breakdowns and examples

*R-W33 only.*

- The background says numeric domains are the harder case, and the corpus is 10 classical
  and 10 numeric. No result is split that way. No per-domain table, no per-wording table.
- Not one example transcript: no skipped call, no truncated delivery, no transcription
  error. For a paper about model behavior, examples are the cheapest way to convince a
  reader. This also serves C3.
- **Fix:** $0 re-analysis plus rewriting.

### C22. Still in conference form, with no code link

*R-W34 only.* AAAI style file, anonymous author block, the AAAI reproducibility checklist
(answering "no" to code included), and commented-out code and data links (7-8, 56-61,
102-106, 2160-2363). Already tracked as the N3 reformat. The reviewer-facing point that is not
cosmetic: reviewers cannot inspect the harness or the prompt bank the paper points to.

---

## Disagreements between the two reviews

Each entry: the topic, what each side says, then my review of the contradiction.

### D1. Is there already an independent check on the answer key? (C8)

- **R says** no. The validators are built on `unified-planning`, and VAL appears only in
  the PlanBench section.
- **V says** (insider check on V-W5) "Plans are checked by VAL, which is independent of
  the planner; the paper should name it."
- **Review: R is right, V is wrong on the fact.** I checked the plugin. The validator
  server imports `pyval` (`pddl-pyvalidator`, "Pure Python PDDL plan validator"), whose
  only hard dependency is `unified-planning`. That matches tex 308. In the tex, VAL is
  named only in the background (202, 233) and in PlanBench (1402 onward). So in the main
  suite nothing is checked by VAL.
- **What is left of V's point.** For *solve*, the planner that makes the plan and the
  validator that grades it are different programs, so a solve success is not the planner
  agreeing with itself. The paper can say that. For the three validate tasks and for
  simulate, the oracle and the tool are the same program, and R's objection stands in
  full.
- **For the plan:** do not write "checked by VAL" into the paper. A real cross-check of a
  sample against KCL VAL would be a small local job and would answer R directly.

### D2. Why did the full-storage rerun fail parity? (C1, C13)

- **R says** a reviewer reads "different apparatus" as: the authors could not reproduce
  their own main sweep within their own tolerance.
- **V says** (insider) the rerun was a different configuration by design (thinking on,
  reasoning parser off), and that parser change is exactly why it failed parity. The
  rerun the paper pre-registers has never been run.
- **Review: no conflict on facts; R describes what the paper makes a reader believe, V
  knows the cause.** V's account checks out: the parity report (`paper_notes`
  2026-07-17) has the Gemma control noise floor at 5.3 points, Qwen passing 7 of 20
  equivalence tests, a maximum gap of 11.3 points (35B solve), and truncation up 13 to 19
  points on solve and validate_plan, "the parser-off mechanism". The tex gives the
  rerun's settings (680, 696) but never says why parity failed, so the weakness is partly
  a missing sentence. One caution: reproducibility of the tool arms is still untested
  until the real rerun exists.
- **A correction to both reviews.** V concludes from 21% against 0.9% that "the
  invocation rate depends on the serving parser", and R-W4 uses the same pair as a hint of
  a software cause. That inference does not hold. The two figures differ in reasoning
  mode as well as parser, and the canonical thinking-on cell with the parser on is 0.6%
  (C3). The parser explains the parity failure on long generations. It does not explain
  Gemma's call rate.

### D3. Is validate_plan "undecided in both directions" for all three models? (C1, C20)

- **R says** the 35B range (55.0 to 90.3) lies entirely below its 90.9 baseline, so the
  tool cannot have helped that model even in the best case, and "straddling" is wrong.
- **V and `NUMBERS.md` say** validate_plan is UNDECIDED for all three.
- **Review: both are right about different questions, and R's point goes further than R
  noticed.** I read tex 1066-1071. The three ranges are Gemma 6.6 to 99.6 (its no-tools
  baseline is the 88% from the "-67" sentence); the 35B 55.0 to 90.3 against 90.9; the 9B
  80.8 to 87.2 against 79.7. Only Gemma's range
  contains its baseline. The 35B range sits entirely below its baseline and the 9B range
  entirely above. So at the level of the ranges themselves, only one of three
  "straddles". The UNDECIDED verdicts must then come from the confidence intervals around
  the range ends overlapping the baseline interval, which is the paper's decision rule
  and may well be correct. But "straddling bounds" and "in both directions" describe
  Gemma only. For the 35B the open outcomes are "no detectable difference" or "harm". For
  the 9B they are "no detectable difference" or "help".
- **For the plan:** confirm against the verdict code and `NUMBERS.md` row 70, then fix
  the wording. It is a small edit and it removes an error a careful referee will catch.

### D4. Is "273,600 trials" a problem? (C1)

- **R says** (R-W23, Moderate) the count oversells: 91,200 anonymized with-tools trials
  "enter no reported number" by the paper's own footnote, most canonical tool-arm trials
  cannot be graded on the main outcome, every abstract number comes from somewhere else,
  and pooled figures are dominated by validate_plan (3,000 of every 4,560).
- **V says** (under "where the reviewers are wrong or too harsh") "273,600 trials graded"
  is accurate as a count, and the objection is really W1.
- **Review: V answers the count, not R's sub-points, and one of those sub-points is too
  strong.** The count is accurate: `NUMBERS.md` gives 273,600 = 5 models x 2 modes x 3
  arms x 4,560 x 2 corpora. So each corpus has 91,200 with-tools trials. The canonical
  91,200 (the tex's own figure, line 421) cannot be graded on the main outcome. The
  anonymized with-tools cells "enter no reported number" by the footnote at 409; the
  footnote gives no count, and 91,200 is the arithmetic. If both hold, about two thirds of
  the headline count supports no delivered claim. C1 repairs part of this for the
  headline models only. **R overstates one thing:** not every abstract number comes from
  elsewhere. The 21%, 94% and 99% are from the canonical open-model tool arms, inside the
  273,600, at the mechanism layer. Only the delivered numbers (22 to 29 up to 95; 0 to
  72) come from other corpora.
- **For the plan:** keep the number, change the framing. Say what the trials support.
  The validate_plan dominance of pooled figures is a separate, real point.

### D5. Is readability its own weakness, or the price of C1? (C19)

- **R says** Major, standalone: "a reviewer who cannot follow a paper tends to reject
  it". Its fixes need no data: define the terms, one interval notation, split
  Limitations.
- **V says** this is the price of W1. Most of the apparatus exists to work around the
  missing delivered numbers. Restructuring before the rerun would be wasted work.
- **Review: both hold, for different layers of the text.** V is right about structure:
  the ranges, the second score in the headline text and many caveats should shrink once
  C1 delivers, so restructure once, afterwards. R is right that part of the problem does
  not depend on the rerun: undefined terms ("prompt v11", "apparatus pin", and the
  others), two interval notations, the 80-line Limitations paragraph, the lab-notebook
  appendix. Those fixes survive any rerun result.
- **For the plan:** split C19 in two. Do the vocabulary and definitions pass now, but
  skip text about ranges and censoring, which may disappear. Do the restructure after C1.

### D6. When to add model families (C3, C14)

- **R says** Major, and asks for it as part of fixing the invocation claim: official
  Gemma weights, and two or three more families.
- **V says** (Q7) not now. Only after W1 and W2, and only if the invocation claim
  survives them. More families belong *inside* the plain-versus-steered contrast, not as
  an appendix point.
- **Review: a sequencing disagreement, not a factual one.** V's order is sound: the cheap
  experiments (C1, C4 arms) can change or kill the claim, and there is no point widening
  a claim that may not stand. R's point is that a referee will ask regardless, since the
  title rests on one community 4-bit build. One item falls between the two and V does not
  consider it: **the official Gemma weights**. It is one model, it fits in the same job
  as the C4 arms, and it removes the "community quantized build" objection from the single
  model that carries the title.
- **For the plan:** consider adding the official-weights arm to the Q2 package. Keep the
  wider family expansion after Q1 and Q2, as V says.

### D7. The steering control's eligibility gates (C9)

- **R says** (R-W21) the gates remove 22 of 30 task cells, including every solve,
  simulate and validate_domain cell. Some removed cells show the directive alone, with no
  tools, moving results by 7 to 10 points with intervals that exclude zero (Gemma
  simulate +9.0 [4.7, 13.3]). So "the sentence works only through the tool" is tested on
  two tasks and "the awkward cells are set aside by rule".
- **V says** the reviewers undersell the control (six units, all passing), and the gate
  point is "correct and already in Limitations".
- **Review: agreement on the facts, disagreement on whether disclosure is enough.**
  `NUMBERS.md` confirms the +9.00 [+4.68, +13.32] cell and labels it UNINFORMATIVE with
  no authority, which is the pre-registered treatment. R itself lists the control among
  the paper's strengths. The honest middle: the control is sound and the gates were set
  in advance, but the body text should scope the claim to the two tasks where it could be
  tested (validate_plan and validate_problem), instead of leaving that to Limitations.
  This is wording, in line with the equivalence-wording rule ("criterion met" on those
  units, nothing claimed elsewhere).

### D8. What caused the unaided simulate zero: budget, grader, or format? (C6)

- **R says** the paper concedes the zero is an artifact, and the thinking-off control
  (11 to 28% with no budget change) suggests the grader or setup matters, against the
  paper's "the recovery comes from the budget, not the grader". (The 11 to 28% are in the
  tex. "No budget change" is R's assumption: the tex never states the decode budget of
  those control units, only a 16K storage cap. The nt-ster prereg supports R: it puts only
  the thinking-on legs on the decoupled budget (its paragraph "(B)", L220), so the thinking-off units ran on
  the ordinary caps. What differs from the main corpus there is the grader and the 16K
  storage, which is R's point.)
- **V says** the appendix states the 0% "is not a formatting artifact" while the body
  says no model ever emits the wrapper, and adds the `guided_json` finding. V calls the
  0.7% re-grade "weak evidence" but does not dispute the budget reading.
- **Review: the two describe the same inconsistency from two ends, and the insider
  record sides with R.** `NUMBERS.md` row 82 gives the failure mix for the 0/3,000:
  1,772 truncated, 1,202 format parse failures, 26 wrong content (recomputed from the
  corpus on 2026-09-19, exact match). The split depends on the reasoning mode: with
  thinking off, the paper's headline setting, format failure is **68%** (1,022 of 1,500)
  and truncation 30%; with thinking on, truncation is 88%. So in the headline setting the
  zero is mainly a format failure, and the format constraint the prompts refer to never
  existed (C6). "Budget, not the grader" is too narrow; "budget and format contract" fits the
  record. There is also history a referee cannot see: the simulate grader had a real
  normalizer bug, fixed 2026-06-23, after which the frontier simulate zeros were
  retracted (`NUMBERS.md` rows 53-55). On the open roster only 26 rows reach the content
  comparison, so that bug cannot explain the open zero, but it is a reason to word the
  grader claim carefully.
- **For the plan:** rewrite the sentence at 874-875. Do not rest anything on the 0.7%
  re-grade.

### Smaller differences

- **Recommendation.** R: major revision. V's three readers: major revision, leaning
  reject.
- **Number of setups.** R: six corpora plus two. A: nine. Same point.
- **Title.** R: show the effect on delivered answers, or soften the title. V (Q6): keep
  it for now and let the rerun decide. Compatible.

---

## What holds up today

So the list is read in proportion. Merged from R's "what a reviewer would still credit"
and V's "what survives a strict reader".

- Grading against a deterministic oracle is far better than self-report or an LLM judge.
- The paper reports its own failures and deviations openly, which is rare.
- The steering control (pre-registered equivalence test, clustered intervals) is a
  well-designed side study. Within plus/minus 5 points on validate_plan and
  validate_problem without tools.
- The question is worth answering.
- **Evidence M accepts as exact, same-setup and delivered:** the unaided open-model rates
  (format-confounded, C6); the contamination result as absence of evidence; the frontier
  lifts (solve 22/29 to 95; the with-tools 95 is n = 100 at both tiers, the unaided side
  is Haiku 22/100 and Sonnet 86/300; the validation lifts, zero delivery gap on verdicts,
  5 of 100 on plans); the 64K probe numbers; PlanBench (Mystery 0 to 4.3% up to
  71.8%, Blocksworld 47.8 to 68.3, the instruction ladder).
- **What does not survive today:** the title, any open-model tool benefit beyond
  validate_domain, "the gap grows with length", RQ5, RQ6, cost-per-success, and the
  thinking-on robustness check.
- **The defensible journal contribution, in the readers' words:** the oracle-graded
  two-layer measurement, the 30 to 35% residual at 64K, and the PlanBench control ladder.

## Verification results (2026-09-19)

### Findings that change the content

| # | claim in the reviews | verified value | source |
|---|---|---|---|
| F1 | Gemma's 21% against 0.9% tool path shows the call rate depends on the serving parser (V-W2; hinted in R-W4) | **Not supported.** Canonical Gemma, thinking on, parser on, plain validate_plan: 19/3000 = 0.6% called (steered 1,327/3000 = 44.2%). Thinking off: 622/3000 = 20.7%, steered 2,808/3000 = 93.6%. The drop is the reasoning mode. | `results/sweep5v2-live/slurm_vllm_gemma4_26b-a4b_{off,on}_tools_all_minimal/trials.jsonl`, `tool_selected`, variants 11-13 / 14-16 |
| F2 | PlanBench with-tools gap "well inside the plus/minus 7.5 point margin" (tex 1439) | Prereg test is a paired TOST. First-draw 119/140 (what the tex quotes): 90% CI [-0.91, +7.91], TOST p = 0.068, **not met**. Last-attempt 119/132: [-2.17, +6.51], p = 0.022, met. | `reference/planbench_wt_prereg.md` L290; `reference/planbench_wt_results_20260803.md` L43, L293; recomputed (Wald) |
| F3 | The storage-fixed rerun is "already specified" / pre-registered (V-W1) | Pre-registered by one Limitations sentence (tex 1693-1698) naming the guard. **No prereg file exists.** Never run (memo §9). | `development/reference/` listing; `journal_decisions_memo.md` L621 |
| F4 | Plans are "checked by VAL" (V-W5) | **Wrong** for the main suite. `pyval` on `unified-planning`. | see D1 |
| F5 | "Every abstract number comes from somewhere else" (R-W23) | Too strong. 21 / 94 / 99% are from the canonical open-model tool arms. | tex 90-92, 1056-1058; `NUMBERS.md` abstract block |
| F6 | Only one of three validate_plan ranges straddles its baseline | Confirmed at tex 1066-1072 and again in the scorecard, 780-781. | see D3 |

### Confirmed without change

| what | result |
|---|---|
| Unaided simulate 0/3,000 and failure mix | Recomputed from the 10 canonical no-tools cells: 0 successes; 1,772 / 1,202 / 26. Exact match to `NUMBERS.md` row 82. Headline models, thinking off: 68 / 29 / 3%, matching tex 865-866. |
| Invocation counts behind 21 / 94 / 99% | 622, 2,808, 617 of 622. Exact match to `NUMBERS.md` abstract block. Tool-verified success 20.6 / 92.6 matches tex 566. |
| 273,600 and the 91,200 blocks | `NUMBERS.md` "Corpus scale". |
| `guided_json` never bound: 0 of 58,581; under 2% on every cut; PR #94 | `paper_notes` 2026-08-17 entry, verbatim. Tex 440-442 quoted verbatim in C6. |
| vLLM 0.20.2 / 0.22.0 split; 0.8B check +0.43 [-0.86, +1.71] | `NUMBERS.md` serving block; tex 401-413. |
| Budget probe: p = 0.069; 70 / 44 and 65 / 58 at 64K; 0 final turns at cap | `NUMBERS.md` row 81; tex 937-946. |
| Rerun cell 30.0 to 63.1 against 0.9; rerun config; parity failure cause | `NUMBERS.md` row 73; `OPEN_ISSUES.md` (d); `paper_notes` 07-17. |
| Steering control: 8 eligible cells, all validate_plan / validate_problem; +9.00 [+4.68, +13.32]; paraphrase floors | `NUMBERS.md` rows 148-150; tex 1988-2022. |
| Cost: 0.65 to 1.64 delivered; 3.1 and 6.1 at the frontier | `NUMBERS.md` rows 76-77; tex 1162-1176. |
| PlanBench 43.8, 47.8 to 68.3, +20.5, 71.8, 4.3 | `NUMBERS.md` PlanBench block. |
| Simulate grader fix | commit `5879ac4`, `_canon_atom` in `pddl_eval/scoring.py`. |
| Answer storage | `RESPONSE_SNAPSHOT_LEN = 16384`, `b07b394`, 2026-06-26. |
| 26 references; undefined terms; Limitations is one 78-line paragraph; no example transcript; no classical / numeric split | tex and `refs.bib`, full read. |

### Still open

- Three figures in C5 are readable only from the paper's figures, not its text (Gemma's
  tool-verified solve value; the steered-arm "at least 35 points"; the tool-arm truncation
  shares). Re-derive from `results/derived/e2e_overlay/pooled_e2e_table.csv` before use.
- F2 used a Wald interval. Recompute with the prereg's own script before editing tex 1439.
- D3: the UNDECIDED verdicts were not re-run through the verdict script
  (`reference/job2_delivered_reframe_worknote.md` §6); only the range positions were
  checked.
- R's reference names in C17 (MetaTool, When2Call, ACPBench, Planetarium) were not
  looked up. Confirmed only that the tex cites none of them.
- Reviewer opinions and estimates ("removes 60 to 75% of the damage", confidence
  percentages) are V's readers' words and cannot be verified.

---

## Decisions

Q1 to Q7 are V's open questions, carried over unanswered, with notes where R changes
the options. Q8 to Q10 are new and come from R's items and the disagreements.

**Read first (2026-10-10).** The rerun changed the starting point. What it found, in
one paragraph: with the recording fixed, the tools raise the delivered answer a lot on
solve (+52 to +71 points) and on domain and problem checking, a little on plan checking
for the two Qwen models, and not at all for Gemma, whose answers without calling the
tool are right about 87% of the time anyway (R1: no delivered harm). On simulate the
tool's result fills the 16K window in 43 to 53% of tool trials, so tools make Gemma
worse (-15.7). A system-prompt sentence telling the model to use the tool *lowers*
calling (R5). By the rule we registered, the title changes (R3). All figures are in
`NUMBERS.md` "Delivered rerun", as a separate-apparatus replication.

**Priority (Omer, 2026-10-10):** budget and reruns are not a constraint; the paper must
read as a scientific study, not as a technical report on our harness. The
recommendations below follow from the rerun and from this priority.

**Q1 (C1): run the pre-registered full-storage rerun (headline models, thinking off,
plain + steered, about 27K trials, $0) before submission?** V recommends **yes**. R
independently names it the most probable reviewer request. It needs the freeze-protocol
gate before any analysis code is hashed, a preflight, and your go before any cluster
step. *Added by verification (F3):* the rerun has no prereg file yet. Writing one, with the
Gemma negative control and the plus/minus 5 point TOST the tex already names, is the
first task if the answer is "run".

> ANSWER (run / contingency only / other):
> **ANSWERED 2026-10-02 (Omer): run.** Done: `reference/delivered_rerun_prereg.md`,
> read out 2026-10-09 by the frozen code. Parity failed at job level, so the whole rerun
> is a separate-apparatus replication (`paper_notes` 10-09).

**Q2 (C3, C4): the "merely available" arm.** (a) rewording only; (b) add the small Gemma
validate_plan arms to the Q1 job (neutral system prompt; directive in the system prompt;
optionally forced call), about 3K trials each; (c) both. V recommends **(c)**. *Added
from R and D6:* (d) also add an official-Gemma-weights arm to the same job.

> ANSWER (a / b / c / c + d):
> **ANSWERED 2026-10-02 (Omer): add the Gemma neutral-system-prompt arm** (rerun Part B,
> 6,000 trials, a 2 x 2 with Part A on Gemma validate_plan). The forced-call arm and the
> official weights (d) were not run. Result, R5: the "use the tool" sentence lowers
> calling (+6.9 points without it).

**Q3 (C6): fix tex line 441 and add the `guided_json` Limitations sentence now**, through
`/verify-claims`, quoting the 08-17 figures. V recommends **yes, regardless of everything
else**. Drafts shown before committing. *Added from D8:* the 874-875 sentence ("budget,
not the grader") belongs in the same edit.

> ANSWER (yes, show me drafts / no / other):
> **ANSWERED 2026-10-02 (Omer): yes.** PR #110, merged 2026-10-09.
>
> *Note 2026-10-10: the frozen rerun readout repeats the false claim.* Its E2 caveat
> says "the no-tools arm is sampled under the per-task JSON constraint"
> (`tools/delivered_rerun/analysis.py:55`). Checked on the rerun's Part C rows
> (`results/delivered-rerun/*_no-tools_delivered-rerun/trials.jsonl`): 13,446 of 13,680
> answers do not begin with `{`, which a constraint that bound would make impossible
> (of the 234 that do, 226 are the 35B on simulate). The constraint did not bind in the
> rerun either; the harness still sends the `guided_json` key. The readout is frozen and
> stays as it is. Do not copy that sentence into the tex.

**Q4: the $0 re-analysis package, local, no cluster.** V's list: classify the 30 to 35%
residual failures in the 64K probe (C5); domain-cluster bootstrap and the GLMM refit (C9);
the PlanBench "well inside plus/minus 7.5" sentence (C9; **now checked, F2: it fails the
prereg's paired TOST on the first-draw numbers, so this becomes a wording fix that needs
Omer's call on how to report it**).
*Added from R:* paired tests for the arm contrasts (C9); per-wording, per-domain and
classical-versus-numeric tables (C12, C21); read and count the Gemma no-call trials and
the truncated tool-arm trials, as far as stored text allows (C3, C5); cost with a
realistic input-to-output price ratio (C16); PlanBench with a corrected extractor beside
the as-shipped numbers (C15).

> ANSWER (all / list which):
> **ANSWERED 2026-10-02 (Omer): all.** Delivered in `reanalysis_statistics.md`,
> `reanalysis_planbench.md`, `reanalysis_breakdowns_cost.md`,
> `reanalysis_transcripts.md`. The PlanBench part is in the tex (PR #114); the other
> numbers are not in the tex yet.

**Q5: rewriting that does not depend on new data.** V's list: demote "law" and
"identical" (C5); say "by construction" in the body and describe the checks honestly
(C2, C8, see D1: not "VAL"); put the arXiv delta and the missing related work in the
paper (C17). V recommends **yes, drafts shown first**, after the consistency-read
answers, so the same passages are touched once.

*Recommendation (2026-10-10): yes, all of it.* These edits are about claiming only what
was shown and placing the work in its field, which is most of what makes a paper read
as science. What the rerun changes:

- "Law" and "identical" go. The rerun traced the open-model solve gap to our own
  recording (answer storage and the refused final request; R4: 95 to 98% of full, uncut
  answers are right), and most of the simulate gap to the tool result filling the 16K
  window. A gap our setup created is not a law. What stays is a description: how often a
  correct tool result fails to reach the answer, and why.
- "By construction" gets one plain sentence in Methods: once the model calls the tool,
  the tool-verified score is right almost by definition, which is why the delivered
  answer is the main outcome. Name the real checker (`pyval` on `unified-planning`), not
  VAL (D1). Q10 adds a real VAL check.
- Related work and the arXiv delta do not depend on any number and can be drafted now:
  work on when a model decides to call a tool, planning benchmarks with similar tasks,
  reasoning models on PlanBench, LLMFP. Look up each reference before citing it (R named
  them from memory). Add a short paragraph on what the arXiv version found and what this
  paper confirms or reverses.
- The claim wording itself waits for the final numbers (Q11).

> ANSWER:
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation.** Work: `weakness_action_plan.md`.

**Q6: title.** Title D ("Invocation Is the Bottleneck...") was chosen on 09-18. All four
readers say the body does not yet support it on the main outcome. V recommends **keep it
for now and let Q1 and Q2 decide**; if Q1 is "contingency only", change to the two-gate
reading the abstract already has.

*Recommendation (2026-10-10): drop title D now; choose the final words after the main
results.* Q1 and Q2 have decided: our registered rule (R3) says the title changes to the
two-gate reading, and keeping title D would break our own pre-registration. The final
wording should follow the numbers the paper ends up standing on (Q11). Direction, from
your 08-20 rule (name the field and the conclusion, never the instrument): the two gates
in plain words. Starting candidates, to be checked against the final results:

- *When Do Sound Planning Tools Help an LLM? Calling the Tool and Passing On Its Answer*
- *Two Gates Between a Sound Planner and an LLM's Answer*
- *From Tool Call to Answer: When Sound Planning Tools Help Language Models*

> ANSWER:
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation.** Work: `weakness_action_plan.md`.

**Q7 (C14, C15): more families, open-model PlanBench, the Llama probe.** V recommends
**not now**; revisit after Q1 and Q2, and only if the invocation claim survives them. See
D6 for R's opposing pressure and the official-weights middle step (now in Q2).

*Recommendation (2026-10-10): yes, now, inside the Q11 study.* V's condition was "after
Q1 and Q2, and only if the invocation claim survives". Q1 and Q2 are done. The strong
claim did not survive: not calling the tool is not the bottleneck on the delivered answer
(R1). A weaker claim did, and it is the more interesting science. How often a model calls
depends on the wording (Gemma: 4 to 31% across the three wordings), on reasoning mode
(0.6% with thinking on) and on the system prompt (a "use the tool" sentence lowers it,
R5), and calling only matters where the model cannot do the task alone. All of that is
one model, a community 4-bit build. A referee will ask whether it holds for other models,
and only other models can answer.

- **More families:** two or three families beyond Qwen and Gemma that fit the cluster
  GPUs (Llama, Mistral and GPT-OSS are the obvious candidates; the exact checkpoints are
  settled by the tool-parser smoke, since a wrong parser silently gives 0% calls), plus
  the **official Gemma 4 weights**. The on-hold Llama-3.1-8B probe (R8) is absorbed into
  this.
- **Open-model PlanBench, plain against steered, two or three models:** yes. It is the
  only place the calling gate can meet a public benchmark (C15). The open Qwen no-tools
  PlanBench run from June exists; the tools arm is what is new. This reopens a closed
  line, which is your call.
- **Sonnet-tier PlanBench** (advisor brief question 6): lower priority. Frontier models
  call the tool every time, so it adds little to the calling question.
- If Q11 is (a), run these on the fixed setup anyway, never on the old one.

> ANSWER:
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation.** Work: `weakness_action_plan.md`.

**Q8 (new; C11, C18, C20, C21): the cheap text fixes only R found.** Describe the test
data and prompts; fix the sentence-level errors (including the D3 "straddling" wording);
scope the over-reaching claims; add two or three example transcripts. None depends on new
data. Suggested: **yes**, in the same drafting pass as Q5.

*Recommendation (2026-10-10): yes.* What the rerun and the re-analyses add:

- **Test data.** The facts are already measured (`reanalysis_breakdowns_cost.md` §4):
  the model sees all seven tools; the PDDL is pasted into the prompt; the "five valid
  plans" are five copies of one plan for 99 of 100 problems; domain checking is 100 valid
  to 20 invalid, so always answering VALID scores 83%; 12 of the 20 invalid domains
  differ only by a parenthesis count; 76% of invalid plans are one step short of the
  valid one. Write them down plainly, and report the validation tasks with a score that
  does not reward always answering VALID (valid and invalid items shown separately, or
  balanced accuracy). If these facts look too weak once written, that is the case for
  Q11 (c).
- **Example transcripts: three**, taken from the rerun, which stores full answers: Gemma
  skipping the tool and judging the plan correctly in prose (why not calling cost
  nothing; 0 of its 2,400 no-call answers contain anything like a tool call), a correct
  relay, and a simulate trial where the tool result fills the window. Examples are the
  cheapest way to make the paper about what models do.
- **Sentence errors** (scorecard caption, "straddling", the "invocation" explanation at
  843-849): fix them in whatever text survives the rewrite. Most sit in passages the
  rerun replaces.
- **Over-reaching claims** (C18): "direct support for the LLM-Modulo thesis" and
  "proves the capability boundary" go or are softened whatever the results; the rest are
  scoped on the final numbers.

> ANSWER:
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation.** Work: `weakness_action_plan.md`.

**Q9 (new; C19, D5): split the readability work?** Vocabulary, definitions, one interval
notation and the Limitations split now; the structural rewrite after Q1 results.
Suggested: **yes, split**.

*Recommendation (2026-10-10): no split; one restructure, done once, after the final
numbers.* The split existed to wait for Q1, which has read out. A vocabulary pass first
would mostly edit text that is about to go: the private terms (mechanism layer,
censoring bound, claim-adverse end, robust floor, determinate rows) exist to handle
ranges and bounds, and those disappear once the delivered answer is measured exactly.
The target for the body:

- one study, one main score (the delivered answer), one secondary measure (how often the
  model calls the tool);
- results ordered by question, each answered once;
- one appendix section, "How we measured", for recording faults, parity, serving
  versions, storage caps and the JSON constraint, with a single table of setups.

If Q11 is (a), the restructure can start now on the current numbers.

> ANSWER:
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation.** Work: `weakness_action_plan.md`.

**Q10 (new; C8, D1): cross-check a sample of the answer key against KCL VAL?** Local and
small if a VAL binary is at hand. It turns "sound by construction" into something
checked, and it is the only full answer to R-W9. Suggested: **yes, if it is an afternoon;
otherwise state the solve-only independence and leave it as a limitation.**

*Recommendation (2026-10-10): yes; it is small.* A VAL binary is already next door,
`../LLMs-Planning/planner_tools/VAL/validate`. It is a Linux build, so it runs in a Linux
container or on the cluster, not on the Mac directly (the cluster needs your go-ahead
first). `../pyvalidator/.claude/skills/validate-against-val.md` already describes the
comparison. Scope: every plan in the validate_plan fixtures and every solve plan graded
in the rerun (VAL checks plans fully); domain and problem files as a parse check only;
simulate not covered. Report it as one agreement figure. VAL has known bugs on some
numeric domains, so read each disagreement by hand before blaming either side. If Q11 is
(c), include the new fixtures.

> ANSWER:
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation.** Work: `weakness_action_plan.md`.

**Q11 (new, 2026-10-10; answer this first): how does the paper use the rerun?**

*Revised the same day after a per-run fault check (Omer: "no way we were so much off").*
The first version of this question recommended a new study about five times the rerun's
size. That mixed two things: repairing what the faults broke, and adding new science.
The check below shows the repair is nearly done already.

*Which runs carry which fault (measured 2026-10-10 on the stored rows,
`results/<run>/*/trials.jsonl`).*

| run | what it is | answers cut at 500 characters | final request refused (tool arms) | Gemma prefix left in | JSON constraint not binding (unaided) |
|---|---|---|---|---|---|
| `sweep5v2-live` | the main sweep, 136,800 trials | yes | yes | yes | yes |
| `sweep6-live` | its anonymized twin, 136,800 | yes | yes | yes, but no reported number grades Gemma's tool answers | yes |
| `iss024d-e2e-live` | thinking-on tool rerun, 45,600 | partly: 16,384 cap, hit by 6,563 rows (14%) | yes | yes | no unaided arm |
| `e2e-overlay` | a regrade of the stored answers, no new model runs | inherits the cut | inherits | yes, the regrade did not strip it | not regraded |
| `rq-sweep5v2` | a slide deck of the main sweep, no new runs | inherits | inherits | inherits | inherits |
| `delivered-rerun` | the pre-registered rerun, 47,040 | fixed (65,536 cap, 0 rows at it) | fixed | fixed (stripped before grading) | **still not binding** |

The refused request, counted the same way in both runs on the same 27,360-trial headline
design (thinking off): 3,233 empty "truncated" tool answers in the main sweep, 1,048 in
the rerun, and all 1,048 are trials where the tool's result left no room to answer.
(`sweep7`, the RunPod BF16 run, was already discarded; `paper_notes` 2026-09-18.)

*What the faults moved.* The rerun measures the damage, because it repeats the headline
design with the faults fixed:

- **Unaided scores:** 11 of 12 cells within ±5 points (the exception: 35B domain
  checking, +8.6). Sound.
- **Calling and tool-verified scores:** 25 of 30 cells within ±5, including all 10 Gemma
  cells (Gemma's plain and steered calling come back at 20.0 and 93.1 against 20.7 and
  93.6). The misses are all Qwen: the 35B's plain solve and simulate, +19.3 each (the
  fault cut its turns short before it could call), its steered solve, +7.3, and the 9B's
  simulate, +3.0 and +4.0 (not shown to be within ±5). The 9B's vLLM version split turned
  out small: 8 of its 10 cells reproduce. Mostly sound.
- **Delivered answers in the open-model tool arms:** far off. The old ranges were pulled
  down by the refused final request, the 500-character cut and the Gemma prefix. Solve,
  plain arm: Gemma "at most 35.3" against 92.3 measured; 9B "26.0 to 58.7" against
  88.7. Most of the open-model "delivery gap" was our harness (R4).

So the main sweep is right about what the models do without tools and about how often
they call the tool. It was wrong about what reaches the answer once they call.

- **(a) Keep the current plan.** The main sweep stays the evidence for everything, the
  rerun sits beside it as a separate replication. The paper keeps the old delivered
  ranges, which we now know are biased low.
- **(b) Two studies, each used for what it measures well (recommended).** Study 1, the
  main sweep: unaided scores, calling, tool-verified scores, and the contamination check
  (`sweep6` against `sweep5v2`, unaided cells only, which the tool-arm faults do not
  touch). Study 2, the pre-registered rerun: the delivered answer. Their agreement (25 of
  30 and 11 of 12 cells) is reported as a replication, and the two 35B cells that moved
  get one sentence: the fault the rerun fixed. The old open-model delivered ranges are
  retired. **No new sweep.** Two loose ends, each a separate choice:
  - *Reasoning mode.* The thinking-on tool cells (main sweep and `iss024d`) carry the
    refused-request fault and have no fixed rerun. Keep the reasoning-mode claim with
    that caveat, drop it, or rerun those tool cells on the fixed setup (3 models x 9,120 =
    27,360 trials, about a week at the rerun's pace).
  - *Small models (0.8B, 4B).* The fault hits them hardest (0.8B: 6,396 of 9,120 tool
    answers empty). Keep them out of tool-arm claims, or rerun them (small models run
    fast).
- **(c) (b), plus new science on the fixed setup.** None of it is needed to repair
  anything; each item stands on its own merits: more families (Q7), harder test items
  beside the current ones (wrong plans that break a precondition mid-plan, distinct
  valid plans, domains with real errors, balanced valid and invalid; 76% of today's wrong
  plans are one step short, so "Gemma loses nothing by not calling" is only as general as
  those items are hard), room in the context window as a factor on solve and simulate,
  open-model PlanBench. Roughly one to two reruns' worth in total, not a new sweep.

The one fault no run has fixed is the JSON constraint in the unaided arm (the rerun has
it too). It only touches the format of unaided solve and simulate answers. A small
unaided run with a working constraint (3 models x 600 solve and simulate trials) would
show whether those scores are held down by format; otherwise the PR #110 Limitations
sentence covers it.

*Recommendation: (b)*, plus the reasoning-mode rerun if the paper keeps that claim. Add
(c) items one by one, on their merits.

> ANSWER (a / b / c, and the two loose ends):
> **ANSWERED 2026-10-10 (Omer): accepted the recommendation, (b) with the (c) items.** The open choices (reasoning mode, small models, JSON control, harder items, context room) carry defaults in `weakness_action_plan.md` §2.
