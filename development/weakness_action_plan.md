# Action plan from the weakness review (2026-10-10)

*Omer accepted every recommendation in `reference/weakness_consolidated.md` (Q5 to Q11) on
2026-10-10. This file turns them into work: what is already done, what is left, in what
order, and who does it. `STATUS.md` (N1b) tracks progress and points here. When every
step is done, this file is deleted and its last commit recorded in `MOVES.md`.*

## 1. The paper we are building

The paper asks when a sound planning tool helps an LLM. Its answer is two gates: the
model has to call the tool, and the tool's result has to reach the final answer. It
should read as a study, not as a report on our harness:

- **Study 1, the main sweep** (`sweep5v2-live`, with `sweep6-live` for contamination):
  what the models do without tools, how often they call the tool, and whether the call
  is right. These numbers held up in the rerun: 11 of 12 unaided cells and 25 of 30 tool
  cells came back within 5 points.
- **Study 2, pre-registered, on the fixed setup** (the delivered rerun plus the extension
  in §4 D): what reaches the final answer, across models, prompts, reasoning mode, how
  hard the test items are, and how much room the model has left to answer.
- **Frontier models** (their own runner) as a reference tier, and **PlanBench** as the
  outside check, now with open models too.
- The harness story (faults, parity, storage, serving versions, the JSON constraint)
  moves to one appendix section, "How we measured".

The two studies are never pooled into one number. Study 1's open-model delivered ranges
are retired: the rerun showed our harness pulled them down.

## 2. Defaults I filled in

Five recommendations left a choice open ("if the paper keeps that claim", "keep out or
rerun", "on their merits"). With budget and reruns not a constraint and science the
priority, I picked the option that measures over the one that adds a caveat. Change any
of them in the slot below; otherwise they stand.

| item | default | why | the other option |
|---|---|---|---|
| Reasoning-mode claim | keep it, and rerun the thinking-on cells on the fixed setup | Gemma's calling falls from 21% to 0.6% with thinking on. That is a finding worth measuring properly | drop the claim |
| Small models (0.8B, 4B) | rerun them, thinking off | cheap, and gives a size ladder from 0.8B to 35B | keep them out of claims about tools |
| JSON constraint | a small control run with a constraint that really binds | tests with data whether the unaided scores are held down by answer format | the PR #110 Limitations sentence only |
| Harder test items, context room | both in | they turn two of our weakest generality points into tested factors | leave them out |
| Sonnet-tier PlanBench (advisor brief question 6) | not planned | frontier models call the tool every time, so it adds little to either gate | run it |

> ANSWER (keep the defaults / change: ...):
> **ANSWERED 2026-10-10 (Omer): keep the defaults.**

## 3. Already done

| done | what it settled | where |
|---|---|---|
| Delivered rerun, Parts A, B and C, read out 2026-10-09 | the main outcome is measured (C1); the same grader on both sides (C7); the "-67" is a tool-verified figure only (C2) | `reference/delivered_rerun_readout.md` |
| Neutral system prompt on Gemma (Part B): the "use the tool" sentence lowers calling | C4, for Gemma | readout R5 |
| Gemma's 2,400 no-call answers read in full: none contains anything like a tool call, 86.6% are right | the "hidden tool call" worry in C3 | `reference/delivered_rerun_secondary/secondary.md` |
| The open-model solve gap traced to storage and the refused final request (R4) | C5, for solve | readout R4 |
| Tex line 441 fixed, the `guided_json` Limitations sentence, "budget, not the grader" removed (PR #110) | the false sentence in C6; D8 | merged 2026-10-09 |
| Four re-analyses at no cost: statistics, PlanBench, breakdowns and cost, transcripts | the analysis behind C9, C12, C16, C21; the C11 facts | `reference/reanalysis_*.md` |
| Per wording, per domain, classical against numeric, cost at 1:1 to 5:1, on the rerun | C12, C16, C21 on Study 2 | `secondary.md` |
| PlanBench: equivalence test reported, corrected-extractor rows beside the shipped ones (PR #114) | the PlanBench sentence in C9; the extractor in C15 | merged 2026-10-09 |
| Consistency read, groups A to E (PRs #111, #115) | part of C20 | merged 2026-10-09 |

## 4. The plan

Six workstreams. A, B and C start now, in parallel with the preparation for D. D (the
experiments) is the long pole. E (the rewrite) starts its Study 1 parts while D runs and
finishes after D reads out. F is the pre-submission work.

### A. Records (agent, today)

- A1. The answer slots in `reference/weakness_consolidated.md` are filled, this file is linked from
  `STATUS.md` and `README.md`, and `paper_notes` has the 10-10 entry. **Done with this
  file.**

### B. Text that does not depend on new numbers (agent drafts, Omer reads, one PR)

Drafts go in `development/` first, as Q5 asked. The PR follows Omer's okay.

| step | what | settles |
|---|---|---|
| B1 | Related work. Look up and verify every reference before citing it (MetaTool, When2Call, ACPBench, Planetarium, reasoning models on PlanBench, the self-verification line after Stechly, LLMFP, the MCP tool-use benchmarks; R named them from memory). Rewrite Positioning so "none measures" no longer follows the La Malfa sentence | C17 |
| B2 | The arXiv delta: one paragraph on what arXiv:2509.12987 found and what this paper confirms or reverses. Reused in the cover letter (F3) | C17 |
| B3 | Test data and prompts in Methods: the measured facts (`reference/reanalysis_breakdowns_cost.md` §4); all seven tools visible in every tool trial; the PDDL pasted into the prompt. All user prompts and their three wordings in an appendix, one sentence defining "prompt v11", and the frontier's single wording stated as a limit | C11, C12 |
| B4 | One plain "by construction" sentence in Methods; the checker named (`pyval` on `unified-planning`); for solve, the planner and the validator are different programs | C2, C8, D1 |
| B5 | The two claims that go whatever the results: "direct empirical support for the LLM-Modulo thesis" and "proves the capability boundary" | C18 |

Done when the drafts are approved and merged, with every number in them taken from
`NUMBERS.md` and checked with `/verify-claims`.

### C. Checks and analyses on data already on disk (agent, local)

| step | what | settles |
|---|---|---|
| C1 | **VAL cross-check.** Run KCL VAL (`../LLMs-Planning/planner_tools/VAL/validate`; a Linux build, so a local Linux container, or the cluster after Omer's go-ahead) on every validate_plan fixture plan and every solve plan graded in the rerun, and on domain and problem files as a parse check. One agreement figure into `NUMBERS.md`; every disagreement read by hand (VAL has known bugs on some numeric domains). It also checks the new items of D1b | C8, D1 |
| C2 | **Study 1 numbers into `NUMBERS.md`:** calling, tool-verified, unaided and contamination, with the paired, domain-clustered, Holm-corrected tests and the GLMM refit from `reference/reanalysis_statistics.md`. Plus the replication table (rerun against the main sweep: 25 of 30 and 11 of 12 cells) | C9, C13 |
| C3 | **Study 2 descriptive tables** ready for the paper: per wording, per domain, classical against numeric, cost by price ratio, and the delivery-gap categories (E4 and the hand read) | C5, C12, C16, C21 |
| C4 | **Three example transcripts** from the rerun: Gemma skipping the tool and judging the plan correctly in prose; a correct relay; a simulate trial where the tool result fills the window | C3, C21 |
| C5 | Check that nothing from the retired open-model delivered ranges survives in the tex outside the passages E replaces (the "straddling" sentences, the scorecard rows) | C20, D3 |

### D. Experiments on the fixed setup (the long pole)

Everything runs on the rerun's setup: harness tag `delivered-rerun-harness` plus additive
changes only (new model entries, new test items, new prompt styles), vLLM 0.20.2, full
storage, the same grader. That is what makes it all one Study 2. All parts sit in one
extension prereg.

**D1. Preparation (agent; about two to three weeks, partly in parallel)**

| step | what | needs |
|---|---|---|
| D1a | **New families.** Two or three beyond Qwen and Gemma that fit the cluster GPUs (Llama, Mistral and GPT-OSS are the candidates), plus the official Gemma 4 weights. Each goes into `vllm_lookup` with its tool-call parser and through `submit_with_rtx.sh --smoke`. Any model whose tool calls are not clearly being extracted is rejected, because a wrong parser gives a silent 0%. Harness branch and PR | cluster go-ahead |
| D1b | **Harder test items**, added beside the current ones (nothing existing changes): wrong plans that break a precondition mid-plan, distinct valid plans, domains with real errors, as many invalid items as valid. Built with `tools/build_fixtures.py`; every item checked by the oracle and by VAL (C1); the item list hashed | C1 first |
| D1c | **Context room.** A smoke of the tool arms on solve and simulate at a larger window, to choose a size that fits each model's GPU memory and to check that answers still parse. (The May 32K smoke broke the unaided answer format; the tool arms were fine then) | cluster go-ahead |
| D1d | **JSON control.** One live probe to confirm why `guided_json` does not bind (the likely cause is the field name on vLLM 0.20.2), then a client version where it binds, used for the control cells only. Every other unaided cell keeps the rerun's behaviour, so it stays comparable with Part C | cluster go-ahead |
| D1e | **Open-model PlanBench with tools.** Route PlanBench's per-instance query through the MCP tool client on vLLM (the design is in the deleted `PLANBENCH_HANDOFF_v2.md`: `git show 1fee730:development/archive/planbench/PLANBENCH_HANDOFF_v2.md`), define the plain and steered PlanBench prompts, and smoke it on one model | engineering, then a smoke |
| D1f | **The extension prereg** in `reference/`: the cells below; the endpoints; readings written before any data (for example: does the directive lower calling in other families; does "not calling costs nothing" hold on the harder plans; how delivery falls as context room shrinks); an anchor slice of the rerun, repeated to show the setup has not drifted; the analysis code; `/freeze-protocol`; the freeze | Omer reads it |

**D2. Wave 1, thinking off (about three weeks of cluster time)**

| cells | trials (rough) | settles |
|---|---|---|
| 2 or 3 new families plus the official Gemma weights: unaided, plain and steered on all tasks; the neutral 2 x 2 on validate_plan | ~80K | C3, C14 |
| The neutral 2 x 2 on validate_plan for the 9B and 35B | 12,000 | C4 |
| 0.8B and 4B: unaided, plain and steered | 27,360 | the size ladder |
| Harder items, every model: unaided, plain and steered | ~20K, set by the item count | C11; how general R1 is |
| Context room: solve and simulate tool arms, headline models | ~4K | C5 |
| JSON control: headline models, unaided solve and simulate | 1,800 | C6 |
| Open-model PlanBench, plain and steered, two or three models | ~7K | C15 |

**D3. Wave 2, thinking on (about one to two weeks)**

| cells | trials | settles |
|---|---|---|
| Headline models, thinking on: unaided, plain and steered, with the main sweep's budgets | 41,040 | "survives reasoning mode" (C18); the 0.6% calling finding |

**D4. Readout.** The frozen code runs on the live data; the figures go into `NUMBERS.md`;
`paper_notes` gets an entry; Omer reads it before any prose is written.

**Size and time.** About 190K trials in total, four times the rerun. The repair part is
about 68K (reasoning mode and the small models). The rest is new science, mostly the new
families. *Correction to Q11:* it put the (c) items at one to two reruns' worth; with the
families at the full design they come to about two and a half. Cuts that keep the science:
two families instead of three (about -20K), or the small models out (-27,360). At the
rerun's pace (47,040 trials in about a week) the two waves take four to six weeks; with
the preparation, about two months to the readout.

**Omer's part in D:** one cluster go-ahead for the smokes in D1a, D1c and D1d; read the
prereg (D1f); a go-ahead for each wave; read the readout. The agent does the rest: one
wrapper call per sub-agent, jobs chained with `afterok` so a failure halts the chain.

### E. The rewrite (agent drafts, Omer approves; one restructure, as Q9 says)

E starts while D runs, on the parts D cannot change, and finishes after D4.

| step | what | when | settles |
|---|---|---|---|
| E1 | Fix the outline (below) and the vocabulary: what each kept term means, which terms go | now | C19 |
| E2 | Methods (with B3 and B4) and the Study 1 results | after C2 | C2, C9, C13, D4 |
| E3 | Study 2 results: the delivered answers; gate 1 (calling) across families, prompts, reasoning mode and harder items; gate 2 (delivery) against context room; cost | after D4 | C1, C3, C4, C5, C6, C7, C14, C16, D7, D8 |
| E4 | The frontier tier and PlanBench, with the open models | after D4 | C15 |
| E5 | Discussion with every claim scoped to the final numbers; Limitations split into short paragraphs; Conclusion | after D4 | C10, C18 |
| E6 | Title (from the Q6 candidates, checked against the results) and abstract | last | Q6 |
| E7 | Consistency-read leftovers (the two consistency-read files were deleted on 2026-10-10; their open items are listed below this table) | with E3 | C20 |

**E7, the consistency-read leftovers.** Three sentences were held from group E for the
delivery-gap rewrite. Each restates a claim the rerun changed, so E3 rewrites them from
the new numbers rather than applying the old drafts:

- E3a: "The unaided zero, meanwhile, is a property of the deployed budget and format
  requirements, not an absent capability."
- E3b: "On this evidence the gap is a property of answer length interacting with the
  output budget, not of model strength."
- E8b: "The pattern is sharp and identical at both capability tiers."

Group F, five candidate additions (none drafted; each is decided when E reaches its
section): a structural-contamination clause (renaming is surface-only) in Contamination
Control or Limitations; a Future Work sentence on steering phrasing; a Future Work
sentence on temperature (Limitations already says higher temperatures are untested); the
classical-against-numeric cost split (now computed, C3); a symbol-map appendix paragraph
after "Per-task contamination".

**Outline.**

1. Introduction: the question, the two gates, the findings, at most three contributions.
2. Background and related work (B1, B2).
3. Methods: tasks and test data; tools; models; arms (unaided; plain, described as "tool
   available plus a policy sentence"; neutral; steered); outcomes (the delivered answer
   is the main one, how often the model calls is the second, tool-verified appears once,
   as the mechanism check); statistics.
4. Study 1: what the models do alone, and when they call.
5. Study 2 (pre-registered): what reaches the answer, and why.
6. Frontier models: the same two gates at the frontier.
7. PlanBench.
8. Discussion, limitations, conclusion.

Appendix: How we measured (faults, the replication, serving, storage, the JSON
constraint, one table of setups); prompts; per-domain and per-wording tables; the
steering control; the prereg documents with their hashes.

**Leaves the paper:** "-67" as a headline (it stays only as a labelled tool-verified
figure); "law" and "identical"; the open-model delivered ranges; the robust floor and the
realizable benefit; the private vocabulary that existed to handle the ranges.

**Rules for every E step:** `NUMBERS.md` before prose; `/verify-claims` on every edit
that carries a number; Study 1 and Study 2 never pooled; never copy the readout's
"sampled under the per-task JSON constraint" sentence (it is false; see the Q3 note in
`reference/weakness_consolidated.md`); a short branch, a PR, Omer merges; `sync_overleaf.sh pull`
before any push.

### F. Before submission (N3, after E)

| step | what | settles |
|---|---|---|
| F1 | JAIR reformat and de-anonymizing, after the venue is ratified (N2) | C22 |
| F2 | Public code and data release, with the prereg documents linked and their hashes stated | C10, C22 |
| F3 | Cover letter with the arXiv delta (B2); this also closes ISS-013 | C17 |

## 5. Every weakness, and where it ends

| weakness | settled by |
|---|---|
| C1 main outcome not measured | done (the rerun); written up in E3 |
| C2 near-tautology; "-67" compares two scores | B4; E2 and E3 take "-67" off the headline |
| C3 one model; software cause | done (no-call answers read); D2 families and official Gemma weights; C4 transcripts; E3 |
| C4 the plain arm is not neutral | done for Gemma (R5); D2 neutral arms for the 9B, the 35B and the new families; E2 names the arm honestly |
| C5 delivery gap | done for solve (R4); D2 context room; C3 gap categories; E3 without "law" |
| C6 unaided arm handicapped; tex 441 | done (PR #110); D2 JSON control; E3 retitles the "cannot do unaided" section |
| C7 lenient against strict scoring | done (Part C, one grader on both sides); E3 uses Study 2 for every tools-against-unaided delivered contrast |
| C8 answer key from the same tools | C1 (VAL); B4 |
| C9 statistics | done (re-analysis); C2; E2 |
| C10 outcome chosen after the data; prereg not checkable | E5 says plainly "exploratory first, then pre-registered"; F2 |
| C11 test data barely described | B3; D1b harder items |
| C12 wording swings | done (tables); B3; E2 and E3 |
| C13 serving versions; parity | C2 replication table; one appendix sentence on the two 35B cells |
| C14 small, narrow roster | D2 families |
| C15 PlanBench | done (PR #114); D2 open-model PlanBench; E4 |
| C16 cost | done (cost by price ratio); E3 |
| C17 novelty, related work, arXiv | B1, B2, F3 |
| C18 claims beyond the evidence | B5; E5 |
| C19 hard to read | E, one restructure |
| C20 sentence-level errors | C5; E7 |
| C21 breakdowns and examples | done (tables); C4; E2 and E3 |
| C22 conference form, no code link | F1, F2 |
| D1 VAL | C1; until C1 reports, the main suite is never described as "checked by VAL" |
| D2 why parity failed | the appendix sentence: the fixes changed exactly the cells they were meant to |
| D3 "straddling" | C5; moot once the ranges are retired |
| D4 273,600 trials | E2 keeps the count and says what the trials support |
| D5 readability timing | settled by Q9: one restructure |
| D6 when to add families | settled: D2 |
| D7 steering-control gates | E3 scopes that claim, in the body, to the two tasks where it could be tested |
| D8 cause of the unaided simulate zero | done (PR #110); E3 says "budget and format contract" |

## 6. Order

```
now        A  B  C  D1  E1          (in parallel)
week ~3    D2 wave 1     E2
week ~6    D3 wave 2
week ~8    D4 readout -> E3 to E7
then       F (with N2 for the venue)
```

What Omer does, in order: (1) the defaults in §2; (2) one cluster go-ahead for the
smokes; (3) read the B drafts; (4) read the prereg; (5) go for wave 1, then wave 2;
(6) read the readout; (7) read the E drafts and pick the title; (8) merge the PRs.
