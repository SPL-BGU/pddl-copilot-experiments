# With-tools grading surface: tool result vs. final output

**Date:** 2026-07-11
**Status:** ALL DECISIONS RECORDED (Omer, 2026-07-11): D1=(a), D2=(a), D2b=B (credit
deliberate delegation-terminal, fail truncated-empty), D3=A (one consolidated pass),
D4=names approved ("end-to-end" / "tool-verified"), D5=paper canon + frontier + sweep7,
D6=A (report bounds). Execution plan in §10 "Next steps".

---

## Decisions to record (Omer — fill each `> MY DECISION:` slot)

**Already decided:** we score the model's **final answer**, not the tool's answer. The old
tool-based score stays as a second, diagnostic number. (D1 + D2 below.)

**Decision 1 — empty final answer (D2b).**
Sometimes the model calls the right tool and then says nothing at all. Do we count the
tool call itself as its answer?
- **A.** No. Empty = fail, always. (strictest)
- **B.** Yes, but only if the model stopped on its own. If it ran out of tokens → fail.
  *(my recommendation)*
- **C.** Yes, always, even when it ran out of tokens.
Why it matters: for 4B this choice keeps roughly 60% (A) vs 75% (B) vs 97% (C) of its
current with-tools wins.

> MY DECISION: B

**Decision 2 — how much to fix in one pass (D3).**
- **A.** Fix all three known scoring bugs together (this one + simulate normalizer +
  validate_plan error binning), rebuild the tables once. *(my recommendation)*
- **B.** Fix only this one now, the other two later.

> MY DECISION: A

**Decision 3 — names for the two scores in the paper (D4).**
Suggestion: **"end-to-end success"** (final answer is right) and **"tool-verified
success"** (right tool call, tool returned the right answer).

> MY DECISION: suggestion approved

**Decision 4 — which result sets to re-score (D5).**
Minimum: sweep5v2-live + sweep6 (the paper's data). Also add the Sonnet/Haiku frontier
runs and sweep7?

> MY DECISION: Also add the Sonnet/Haiku frontier
runs and sweep7

**Decision 5 — the 500-character blind spot on old data (D6).**
Old runs only saved the first 500 characters of each answer, so sometimes we can't see
the final verdict. Options:
- **A.** Report a range (worst case – best case). Costs nothing. *(my recommendation)*
- **B.** A + also run the small parity smoke test we already planned (ISS-024(d)) with
  full saving, and use it to estimate where the truth sits inside the range.
- **C.** Re-run a full with-tools sweep with full saving. Expensive; only if the paper
  must have exact numbers instead of a range.

> MY DECISION: A

---

**Trigger:** investigator confirmed (code + data) that with-tools success is graded on
`tool_calls[].result`, never on the model's final response (`pddl_eval/scoring.py:466–583`).
On 35b sweep5v2 validate_* with-tools successes (n=7,812): 63.6% restate the tool verdict,
0% contradict it, 36.4% state no checkable verdict (28.9% of all successes finished with
`done_reason=stop` and simply never committed; only 7.4% were truncated first). 4B similar
(39.7% no-verdict).

---

## 0. DECISION + same-day correction (2026-07-11)

**Decided principle (Omer):** the evaluation must grade the *model's output*. Instructing
the model to relay the tool's output verbatim is a fine prompt design; what is wrong is an
evaluation that ignores the model's output and inspects the tool result instead — that
treats an internal component's output as if it were the model's final answer. A tool call
is itself a legitimate form of model output (the call name + arguments are model-authored),
so a trial whose output *is* the tool call is graded on that call; a trial that produces a
final response is graded on that response. → D1 = end-to-end (response-graded) primary;
D2 = response-only surface with the tool-call-as-output carve-out (operationalized in D2b).

**Same-day measurement correction — snapshot censoring.** The trigger numbers above are
partly a storage artifact, not behavior. `trials.jsonl` stores `response` as a HEAD
snapshot, `response_text[:RESPONSE_SNAPSHOT_LEN]` (`runner.py:514`), and the cap was
**500 chars** until 2026-06-25 (raised to 16384 for offline re-gradeability —
`runner.py:145–153`). sweep5v2-live predates the raise. The prompt places the VERDICT
line at the END of the response, so for any response longer than 500 chars the stored
snapshot cannot contain the verdict. Probe v2 split of the tool-graded validate_*
successes:

| bin (share of tool-graded successes) | 35b | 4B |
|---|---|---|
| verdict visible in snapshot (faithful) | 63.6% | 60.3% |
| contradiction visible | 0.0% | 0.0% |
| snapshot exactly 500 chars, no verdict visible → **INDETERMINATE** (censored) | 27.6% | 3.5% |
| empty response, `done_reason=stop` (model closed the turn silently after the tool result) | 1.3% | 13.7% |
| empty response, truncated (`length`) | 7.4% | 22.5% |

Consequences:
- True restatement is only **bounded** on this corpus: 35b faithful ∈ [63.6%, 91.2%],
  4B ∈ [60.3%, 63.8%]. "0% contradiction" is proven only within the first 500 chars.
- "Fully measurable offline" is **false** for sweep5v2-live: 27.6% (35b) / 3.5% (4B) of
  tool-graded validate successes are unrecoverable from disk. Solve plans and simulate
  trajectories exceed 500 chars routinely, so those tasks are censored too (this exact
  cap is what blocked the frontier simulate re-grade — `runner.py:146–148`).
- The two models' "silence" is different phenomena: 4B's is nearly all genuinely empty
  output (36.2% of successes — a real synthesis gap), while most of 35b's apparent gap
  (27.6/36.4) is storage censoring of unknown direction.
- No-tools published numbers are unaffected: grading ran online on the full text before
  snapshotting; the cap constrains only offline REgrading.

---

## 1. Bottom line

Our current with-tools metric is a legitimate, publishable construct — but it is not the
construct the paper's prose implies, and it is not graded on the same surface as the
no-tools arm. The fix is an offline rescoring overlay: add a second, response-graded
success column (same parser as the no-tools branch, both arms) and report both numbers.
No rerun, no cluster time — **but** on pre-2026-06-25 corpora (incl. sweep5v2-live) the
500-char head snapshot censors the stored response, so the end-to-end column there is an
*interval* (strict lower bound + censored mass), not a point estimate (§0). The gap
between the two metrics is itself a finding (correct delegation without answer
synthesis), not just a caveat.

One fact makes this more than a style choice: **the with-tools prompts already define the
final response as the deliverable.** v14–16 validate_* prompts end with "End your response
with exactly one line: VERDICT: VALID or VERDICT: INVALID" (`prompts.py:290–316`); solve
v14–16 say "return a plan" with a per-line action format (`prompts.py:279–283`); simulate
v14–16 say "return the trajectory" with an example step object (`prompts.py:325–329`).
The grader currently credits ~29% of with-tools validate successes for trials that
disobeyed this instruction. So the grading surface contradicts the harness's own task
contract — the response-graded metric is not an optional add-on; it is the metric that
matches what we asked the model to do.

## 2. What we do today (verified)

| task | with-tools grading (`scoring.py`) | no-tools grading |
|---|---|---|
| validate_* | `_parse_validation_verdict(tc["result"])` vs GT (:528–536) | `ValidateResponse` / `extract_verdict(response)` (:544–555) |
| solve | plan extracted from planner tool result, then validated (:473–492) | plan extracted from response, then validated (:497–511) |
| simulate | tool trajectory normalized vs oracle (:575–583) | response coerced + normalized vs oracle (:596–609) |

The model's response text is read in **zero** with-tools branches. With-tools success
therefore means: *right tool selected, faithful arguments, tool output matches ground
truth*. It does not require the model to convey the answer.

## 3. What the conventions are for this experiment type

Agentic/tool-use benchmarks distinguish two grading surfaces:

- **State/artifact-based** — grade the side effect or produced artifact. SWE-bench grades
  the patch against tests; τ-bench grades the final database state; BFCL's executable
  categories grade the call/execution itself. Appropriate when the task's deliverable IS
  the side effect.
- **Response-based** — grade the agent's final message. WebArena information-seeking
  tasks require the answer string in the final answer; BFCL v3 multi-turn uses
  response-based checks for retrieval-type tasks; τ-bench additionally requires that
  required information appear in the agent's reply for info tasks.

The dividing line is what the user consumes. Our five tasks are all
**information-seeking**: nothing persists after the episode; the user asked a question
(is this valid? what plan solves it? what is the trajectory?) and consumes the final
message, not the MCP trace. Under the prevailing convention these tasks are graded
response-based. Our with-tools arm applies state-based grading to information tasks.

Second convention we currently violate: **comparative arms should share a grading
surface**. No-tools is response-graded, with-tools is trace-graded, so the tool-lift Δ
conflates "tools help" with "the with-tools grader is more forgiving of
non-commitment." A reviewer fluent in BFCL/τ-bench/HAL-style harness methodology will
ask exactly the question Omer asked.

In the LLM+PDDL literature specifically, artifact grading of the *final produced plan*
is the norm (Huang & Zhang validate the generated PDDL by solving it; LLM-Modulo grades
the returned plan). Note that in those setups the graded artifact is still what the
model/system *returns to the caller* — the analog of our final response, not of our
internal tool trace. (arXiv:2512.09629's exact grading surface is on the
verify-before-submission list.)

## 4. Why the current metric is still defensible — if renamed

- **0% contradiction.** Trace-grading never credits a trial whose final answer is
  *wrong*; the leniency is only toward *silence*. The current number is a clean upper
  bound; a response-graded number is the matching lower bound. Nothing already published
  from this corpus credited a misreported answer.
- **It measures a real construct**: tool selection + faithful invocation ("did the model
  correctly delegate"). This is precisely what BFCL grades, and it is the paper's
  mechanism story. It just needs an honest name — *tool-verified success* /
  *delegation success* — instead of implying end-to-end task success.
- The truncation defense is weak, though: only 7.4% of the silent successes were cut off
  before a verdict; 28.9% stopped cleanly and never committed. This is model behavior,
  not budget censoring, so "with-tools trials run out of room" does not excuse it.

## 5. Effect on the paper's claims

- **Tool-lift claims (headline).** Under the decided grading (response-graded with the
  tool-call-as-output carve-out, D2b), with-tools validate success on sweep5v2-live
  becomes an interval because of snapshot censoring (§0). Relative to the current
  tool-graded numbers, retained share of successes by D2b option:

  | D2b option | 35b retained | 4B retained |
  |---|---|---|
  | (i) strict response-only (empty = fail) | 63.6–91.2% | 60.3–63.8% |
  | (ii) credit deliberate delegation-terminal (`stop` + empty) | 64.9–92.5% | 74.0–77.5% |
  | (iii) credit any empty (incl. truncated) | 72.3–99.9% | 96.5–100% |

  (Plus whatever is regained from trials where the tool errored or got mangled args but
  the model still stated the correct verdict — not a strict subset of current successes.)
  Given the size of the measured lifts (e.g. +42/+52pp on 4B), the qualitative claim
  almost certainly survives every option, but every with-tools number in the draft needs
  re-deriving before prose is written around it, and D2b visibly moves the 4B numbers.
- **Framing.** Until rescoring lands, with-tools numbers should be described as
  tool-verified (delegation) success, not end-to-end accuracy.
- **New finding available.** "Models never misreport tool results (0% contradiction) but
  fail to restate them in ~29–40% of successful delegations, in direct violation of the
  prompt's output contract" is a genuine, quantified result about answer synthesis — and
  it strengthens rather than weakens the tools story (the failure is packaging, not
  delegation).

## 6. Known interactions — fold into one rescoring pass

Three already-known scoring issues touch the same code and the same corpora; one offline
"scoring v2 overlay" pass should handle all of them so we re-derive tables once, not three
times:

1. **This issue** — add response-graded success column for both arms.
2. **Simulate normalizer bug** — `(p a b)` vs `p(a,b)` predicate-syntax mismatch makes
   no-tools simulate read ~0% when reality is ~50%; any response-graded simulate column is
   meaningless until this normalizer fix is in the same pass.
3. **validate_plan FP mis-binning** — ~95% of with-tools validate_plan FPs are FastMCP
   pydantic arg-errors escaping `_tool_error_seen`. Response-grading interacts: some of
   those trials may carry a correct textual VERDICT and would flip categories.

Corpus identity is load-bearing: the pass must be a **derived overlay** (new columns /
materialized rescored table à la `canonicalize_results.py`), never a mutation of the
stored `trials.jsonl`.

## 7. Recommendation

Report **both** metrics, defined symmetrically:

- **End-to-end success** (response-graded, identical parser both arms): grade the final
  response with the existing no-tools branch logic (`extract_verdict`, plan extraction +
  validation, trajectory coercion). This is the apples-to-apples surface and my
  recommendation for the paper's headline lift numbers.
- **Tool-verified success** (current metric, renamed): kept as the mechanism/diagnostic
  layer, alongside the existing `tool_selected`. The decomposition
  `end-to-end = tool-verified ∧ restated` (plus the small response-right/tool-wrong
  remainder) gives the paper an exact answer-synthesis-gap table for free.

No prompt change is needed for future sweeps — the prompts already demand the final
answer; only scoring lags the contract.

## 8. Open decisions

**D1 — Which metric is the paper's headline for tool lift?**
Options: (a) end-to-end (response-graded) primary, tool-verified secondary *(my
recommendation — matches convention and the prompt contract)*; (b) tool-verified stays
primary with explicit framing + reported gap; (c) report only end-to-end and demote
tool-verified to appendix.

> ANSWER: **(a) — DECIDED (Omer, chat, 2026-07-11).** "It's wrong if the evaluation
> ignores [the model's] output and only inspects the tool call instead, making an
> internal component the final model output." Grading the model's output is required;
> tool-verified is retained as the mechanism/diagnostic layer.

**D2 — Definition of with-tools end-to-end.**
Options: (a) response-only, same grader both arms — symmetric, credits a correct textual
verdict even if the tool path failed, exactly as the no-tools arm credits a lucky guess
*(my recommendation; conjunction variants are derivable afterwards)*; (b) conjunction:
tool-verified AND correct final response — stricter, but asymmetric vs no-tools.

> ANSWER: **(a) — DECIDED (Omer, chat, 2026-07-11)**, with one carve-out: a tool call is
> itself model output ("if the model's output is the tool call, it's correct"), so grade
> the model's output whatever channel it takes. Operationalization of the carve-out = D2b.

**D2b — Operationalizing "the model's output is the tool call".**
In the stored trials the model almost always gets the tool result back and then emits a
final turn; "output = tool call" arises when that final turn is *empty*. Two empty
flavours exist (§0 table): `done_reason=stop` (model deliberately closed the turn with
nothing after the tool result — its only substantive output act is the call) vs
`done_reason=length` (budget censoring — the final turn never happened). Options:
(i) strict: empty = fail, both flavours (harshest; fully symmetric with no-tools, where
truncation also fails); (ii) credit `stop`+empty as delegation-terminal output, fail
truncated-empty *(my recommendation — matches the decided principle for deliberate
delegation while keeping truncation handling symmetric across arms)*; (iii) credit any
empty. Impact is large for 4B (§5 table: 60–64% vs 74–78% vs 96–100% retained).
A non-empty final turn that states no checkable verdict fails under all options — the
model produced an output and it doesn't commit.

> ANSWER: → record in "Decisions to record" §, Decision 1.

**D3 — Scope of the rescoring pass.**
Options: (a) one consolidated overlay pass fixing this + simulate normalizer +
validate_plan FP binning *(my recommendation — one re-derivation of all tables)*;
(b) this issue alone now, the other two later.

> ANSWER: → record in "Decisions to record" §, Decision 2.

**D4 — Naming in the paper.**
Proposal: "end-to-end success" vs "tool-verified success" (alternatives: "delegation
success", "answer-graded/trace-graded"). Any preference?

> ANSWER: → record in "Decisions to record" §, Decision 3.

**D5 — Corpora in scope.** sweep5v2-live + *_sweep6 (paper canon) at minimum. Also
Sonnet/Haiku frontier corpora and results/sweep7? NOTE (§0): corpora written before
2026-06-25 carry the 500-char response snapshot — for those the end-to-end column is
interval-valued, not exact. An inventory pass (which corpus was written under which cap)
is step 0 of the overlay.

> ANSWER: → record in "Decisions to record" §, Decision 4.

**D6 — Handling the censored rows on pre-06-25 corpora.**
Options: (a) report end-to-end as bounds (strict lower bound + censored mass as the
interval), with the empty/non-empty decomposition on-slide *(my recommendation — honest,
zero compute; even the strict lower bound preserves the qualitative lift)*; (b) piggyback
on the already-gated ISS-024(d) parser-off+tools parity smoke: run it under the 16384 cap
and use it as a small fully-gradeable with-tools sample to estimate where in the interval
the truth sits (one stone, two birds — it was wanted anyway for decoupled parity);
(c) a fresh full with-tools sweep under the new cap (expensive; only if the paper ends up
needing exact headline numbers rather than bounds).

> ANSWER: → record in "Decisions to record" §, Decision 5.

## 9. Implementation sketch (offline, cheap)

1. Corpus inventory: classify every corpus by snapshot cap at write time (500 vs 16384);
   determines which get exact `success_e2e` and which get bounds (D6).
2. New `scoring_overlay.py` (or a `--regrade` mode): for each stored trial, run the
   existing no-tools branch of `check_success` on `response` regardless of arm →
   `success_e2e ∈ {true, false, indeterminate}` + `fail_reason_e2e`. `indeterminate` =
   censored row (snapshot at cap, no parseable answer in the visible window). Apply the
   D2b carve-out for empty final turns. Keep current columns untouched.
3. Fold in the simulate normalizer fix + validate_plan FP binning fix behind the same
   pass (per D3).
4. Emit a rescored materialized table next to the canonical corpora; analyzer reads it
   via a flag so old decks stay reproducible; interval cells render as lower–upper.
5. Sanity targets from probe v2 (35b validate_*): strict `success_e2e` lower bound
   ≈ 0.636 × current + regained tool-error/mismatch credits; censored mass ≈ 0.276 ×
   current; 0 visible contradictions.
6. Deterministic, no model calls, no cluster time. Rough effort: ~1 day incl. analyzer
   re-derivation.

## 10. Next steps (planned 2026-07-11, from the recorded decisions)

Branch: `feat/e2e-scoring-overlay`. Overlay output: `results/derived/e2e_overlay/`
(canonical corpora never mutated). Rules implemented: D2b=B, D6=A (bounds).

- **Phase 1 — validate_\* e2e overlay (no MCP needed).** Truth is encoded in the fixture
  naming (verified on corpus: `validate_domain` pname `domain_neg`=INVALID else VALID;
  `validate_problem` pname `n##`=INVALID else VALID; `validate_plan` plan_label
  `b*`=INVALID / `v*`=VALID). Script `tools/e2e_regrade.py`: no-tools rows pass through
  (stored success IS response-graded, done online on full text); with-tools rows regraded
  from the stored response with the no-tools parser; empty+`stop`+tool-verified →
  credited (D2b-B); empty+`length` → fail; nonempty-at-cap without verdict →
  INDETERMINATE. Run on sweep5v2-live + sweep6-live → first bounded e2e numbers.
- **Phase 2 — solve + simulate e2e. DONE 2026-07-11.** `tools/build_gt_cache.py` ran the
  harness's own `generate_ground_truth` once via local MCP (100 problems, all negative
  fixtures verified) → `results/derived/gt_cache.json`. Solve regraded with live-MCP plan
  validation (256 deduped calls); simulate regraded through the CURRENT
  `_normalize_trajectory` — the `_canon_atom` predicate-notation fix already lives in
  scoring.py, so this regrade IS the simulate-normalizer repair for old corpora.
  No-tools simulate rows are regraded too (their stored grades used the pre-fix
  normalizer); all other no-tools rows pass through their stored online grade.
- **Phase 3 — tool-verified column fix. DONE 2026-07-11.** Current `_tool_error_seen`
  already recognizes the FastMCP "Error executing tool" arg-error shape; the stored
  corpora were simply graded under older code. Tool results are stored UNCAPPED, so the
  overlay recomputes tool-verified + failure reason exactly (`tool_verified_fixed`,
  `tool_fr` columns), for validate_*.
- **Phase 4 — frontier + sweep7 corpora (D5). DONE 2026-07-11.** All four corpora share
  the standard row schema; only the probe corpus needed a wider glob
  (`trials*.jsonl`). All were written under the 500-char cap (auto-detected per cell).
  Results:
  - **Sonnet no-tools simulate is 100% censored** ([0,100], n=300×2) — the
    [[project_simulate_grader_artifact]] "re-grade the 0/300 floor" plan is IMPOSSIBLE
    from disk; the paper's sole-source-floor retraction must lean on the decoupled Qwen
    numbers or a fresh Sonnet run. All other Sonnet no-tools cells pass through their
    stored online grades unchanged (validate 90–97, solve ~28.5).
  - **Frontier with-tools probe is mostly blind too**: Sonnet validate_plan e2e
    [7.5, 100] (92.5% censored), Haiku [24.5, 100] (75.5%) — frontier models write long
    responses, so verdicts land past char 500. Tool-verified stays 100%.
  - **sweep7 (35b BF16)** reproduces the AWQ pattern: validate_plan tools e2e
    [68.5, 92.6] vs no-tools 84.0 (same straddle as sweep5v2's [62.3, 90.2] vs 87.8) —
    the censoring-bound inconclusiveness is quant-independent. Phase-3 rebinning shows
    almost no arg-errors on sweep7 (2 vs sweep5v2's 8,756), consistent with the newer
    plugin code it ran ("Sweep5 tool error fixes" #56).

### ISS-024(d) full re-run — SUBMITTED 2026-07-11 (job 19293221)

Per Omer's decision (skip the smoke, run the complete arm): 4 Qwens × think=on ×
tools_all_minimal, full trials, `--reasoning-parser none`, `--run-tag iss024d-e2e`,
72h wall. All 4 array tasks RUNNING at submit time. Apparatus deliberately FROZEN for
parity: experiments repo @ `6007032` (the exact decoupled commit — its origin branch was
deleted after merge, so no pull; this is a feature), plugins @ `5e4f9c0` (sweep5-era).
Log confirms `--tool-call-parser qwen3_xml (no reasoning-parser)`. Runs under the 16384
cap → every trial fully e2e-gradeable: resolves the censored with-tools cells exactly AND
answers the parser-off parity question. Results land in
`results/slurm_vllm_<model>_on_tools_all_minimal_iss024d-e2e/` (run-tag suffix — remember
the analyzer cell-parser quirk).
- **Phase 5 — analyzer + paper.** Analyzer reads the overlay via a flag; master tables
  gain end-to-end (bounds where censored) next to tool-verified; paper prose updates
  once numbers are re-derived (framing per D4 names).

### Phase 1 results (run 2026-07-11, `tools/e2e_regrade.py`, unfiltered per-row means)

With-tools validate_* outcome distribution (sweep5v2-live, all 5 models, n=79,200):
42.1% state a correct verdict, 1.2% a wrong one (the "models rarely misreport" result
holds corpus-wide), 27.3% truncated-empty (fail, D2b-B), 23.1% censored at the 500-char
snapshot cap (indeterminate), 6.0% delegation-terminal credit (D2b-B), 0.3% empty-stop
without tool verification. Genuine non-committal prose under the cap is ~0 (36 rows) —
almost all apparent "silence" was actually snapshot censoring or empty output.

Key e2e cells, sweep5v2-live (no-tools vs with-tools [low, high]):

| model | task | no-tools | tools e2e | tools tool-ver | verdict on lift |
|---|---|---|---|---|---|
| 4B | validate_domain | 10.0 | [85.8, 97.1] | 94.7 | survives at lower bound |
| 4B | validate_problem | 34.0 | [53.8, 76.0] | 79.1 | survives |
| 4B | validate_plan | 49.5 | [45.9, 55.6] | 74.5 | **straddles — inconclusive** |
| 9B | all three | 14.4/41.6/50.6 | low ≥ 78.0 dom/plan, 88.0 prob | 87–99 | robust everywhere |
| 35b | validate_domain | 70.6 | [89.4, 99.0] | 99.2 | survives |
| 35b | validate_problem | 76.6 | [76.9, 95.8] | 97.5 | wash at lower bound |
| 35b | validate_plan | 87.8 | [62.3, 90.2] | 94.7 | **inverted at lower bound** |
| gemma-4-26B | validate_plan | 49.1 | [17.3, 98.5] | 39.4 | censored 81% — unusable |

Reading: the end-to-end lift is fully robust for 9B, mostly robust for 4B; for 35b
validate_plan (and gemma broadly) the 500-char censoring makes the old corpus unable to
answer at strict grading. D6=A reports these as bounds; if the paper ends up needing the
35b validate_plan cell decided, the D6-B parity smoke (ISS-024(d) under the 16384 cap)
is the cheap resolver — Omer's call, not assumed.

### Phase 2+3 results (run 2026-07-11)

Solve and simulate, sweep5v2-live (no-tools vs with-tools e2e [low, high] vs tool-ver):

| model | task | no-tools | tools e2e | tools tool-ver |
|---|---|---|---|---|
| 0.8B | solve | 0.0 | [2.0, 10.2] | 15.2 |
| 4B | solve | 11.7 | [9.1, 34.0] | 75.1 |
| 9B | solve | 18.8 | [25.8, 49.4] | 82.5 |
| 35b | solve | 23.8 | [10.1, 53.8] | 81.2 |
| 4B | simulate | [0, 54.5] | [0, 21.1] | 63.9 |
| 9B | simulate | [0, 16.0] | [0, 28.4] | 80.4 |
| 35b | simulate | [0, 69.0] | [0, 26.8] | 91.2 |

Readings:
- **solve:** the e2e lift survives at the lower bound only for 9B (25.8 > 18.8) and
  trivially 0.8B; 4B and 35b straddle. Censoring is 22–44% (plans rarely fit under
  500 chars).
- **simulate:** with-tools e2e-low = 0.0 for EVERY model — not one with-tools simulate
  trial yields a determinate end-to-end success on the old corpora. The determinate mass
  (65–73%) is `truncated_empty`: the model delegates correctly (tool-ver 64–91) and then
  exhausts its budget before producing any final trajectory. Under the decided grading,
  the with-tools upper bound (≤27–35) sits BELOW no-tools' upper bound for 4B/35b — the
  "simulate 0→90" tool-lift story cannot be stated end-to-end from this corpus at all.
  This is also a real behavioral finding: tool loops consume the token budget and the
  model never reports the answer.
- no-tools simulate bounds are consistent with the decoupled exact numbers (post-fix,
  16K snapshots: 4B 23%, 9B 22%, 35b 40%), which remain the citable no-tools values.

Phase 3 (tool-verified recompute, validate_*, both corpora, n=158,400): **zero success
flips** — every published tool-verified rate stands. Failure REBINNING is large:
sweep5v2 validate_plan failures split tool_error=8,756 vs verdict_mismatch=2,504
(+10,493 tool_not_selected, 261 wrong_tool) — i.e. ~78% of what looked like
"tool said the wrong thing" was actually a malformed invocation (FastMCP arg-error),
confirming and quantifying the [[project_validate_plan_fp_scoring_bug]] memory
corpus-wide. The overlay's `tool_fr` column now carries the corrected bins.
