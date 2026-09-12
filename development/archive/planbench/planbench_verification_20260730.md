# PlanBench citation + audit verification (2026-07-30)

Run before the WT go/no-go, to settle the one input the decision rested on: is
"tools/formalization rescues Mystery Blocksworld" really already published four times?
Also clears the two NT strengtheners and the t3 mix-confound audit that
`planbench_frontier_haiku_nt.md` finding 2 has been carrying as `PENDING AUDIT`.

Method: every arXiv ID fetched and read at source (two as PDFs, read locally page by page —
web-search snippets were wrong twice, see §2). Every number recomputed locally with Wilson
95% CIs. No API spend, no build.

---

## 1. Citations — all seven exist and are correctly attributed

| cited as | verdict |
|---|---|
| Göbel et al. arXiv:2603.06064 | **REAL.** "Agentic LLM Planning via Step-Wise PDDL Simulation", Göbel/Lorang/Zips/Glück, 6 Mar 2026. Claude Haiku 4.5, 102 IPC Blocksworld, 63.7% → 66.7%. Confirmed |
| Huang & Zhang, ACL 2025, arXiv:2412.09879 | **REAL.** "On the Limit of Language Models as Planning Formalizers", ACL 2025 main, v4. Uses MysteryBlocksWorld-100 |
| La Malfa et al. arXiv:2512.09629 | **REAL.** "End-to-end PDDL Planning with Hardcoded and Dynamic Agents", 10 Dec 2025, rev 8 May 2026 |
| LLMFP | **REAL.** "Planning Anything with Rigor", ICLR 2025, arXiv:2410.12112 |
| CoPE | **REAL.** arXiv:2510.05486, "Language Model as Planner and Formalizer under Constraints". CoPE = Constrained Planning Environments |
| Valmeekam et al. arXiv:2305.15771 Table 1 | **REAL and the quoted number is right** — see §2 |
| Wilson CIs, band cutpoints, NT anchors | **REPRODUCE** exactly (205/500, 4/500, and all four t3 cells) |

No hallucinated citations. That was the main risk and it did not materialise.

## 2. Two places a web search would have made us wrong

**Valmeekam Mystery-BW.** A search returns "17/600 (2.8%)" and "3/600 (0.5%)" for GPT-4 on
Mystery BW. Those are **Table 2**, the PDDL-prompt condition. Our t1 is natural-language
one-shot, which is **Table 1**: **26/600 (4.3%)** — exactly what the decisions memo claimed.
The memo is right and the search was wrong. Recorded because the wrong row flips the
strengthener's sign: 17/600 = 2.83% [1.78,4.49] overlaps Haiku's [0.31,2.04], while 26/600 =
4.33% [2.97,6.27] does not.

For the record, GPT-4 Table 1 NL, all rows: BW one-shot 206/600 (34.3%), zero-shot 210/600,
CoT 214/600; Mystery-Deceptive one-shot 26/600 (4.3%), zero-shot 1/600 (0.16%), CoT 54/600
(9%); Mystery-Randomized one-shot 12/600 (2%).

**LLMFP's metric.** Table 2's numbers are **optimal rate**, and its "Direct" baselines are
**zero-shot**. Our 41.0% is VAL **validity**, **one-shot**. See §5.

## 3. The prior-art question: is the direction already published?

**Yes — verified, four independent groups, not a phantom.**

| paper | evidence for the rescue | n | caveat |
|---|---|---|---|
| Huang & Zhang (ACL 2025) | LLM-as-formalizer robust to lexical perturbation; gpt-4o 60% → **70%** on Mystery, Gemma-2-27b 8% → **99%** | 100 | gpt-4o scores *higher* obfuscated than clean; gpt-4o-mini goes 24% → 0% |
| CoPE (2510.05486) | planner "devastated" on MysteryBlocksWorld-100 while formalizer "remains robust" | 100 | robustness is **substantially negated** once constraints are added: all 4 models drop "by two thirds or more" |
| LLMFP (ICLR 2025) | Mystery optimal rate **77.7** (GPT-4o) / **98.0** (Claude 3.5 Sonnet) vs Direct 0.8 / 0.5, stated as "robust to obfuscated problems … regardless of the names" | 602 | not PDDL+planner — SMT/Z3, and see the next row |
| La Malfa (2512.09629) | PlanBench **+15%** average, "very large improvement in the obfuscated deceptive logistics" | **30** | GPT-5-mini, tiny n, gain reported on logistics |

So your instinct was correct on the facts: the direction is genuinely well published, and I
am not going to argue otherwise.

## 4. But the published rescues all come from bespoke pipelines, not from tool access

This is the finding that actually matters, and it was not visible in our notes.

In LLMFP's own Table 2, the baselines that merely *hand the model a solver* score on
Mystery: `Code_GPT-4o` **0.3**, `Code_SMT_GPT-4o` **0.0**, `Code_Claude-3.5` **0.0**,
`Code_SMT_Claude-3.5` **0.0**. Only the full four-component LLMFP framework (Definer,
Formulator, Code Generator, Self-Assess, up to 5 repair loops) reaches 77.7 / 98.0. Their
own text says PDDL-planner-style baselines "almost always fail to generate and call them
correctly".

And the one paper that ran the closest thing to our setup — **Göbel, same model (Haiku 4.5),
PDDL tools over MCP** — got **+3.0pp** (63.7 → 66.7) on clean Blocksworld, while **Fast
Downward alone scored 85.3%** on the same 102 instances. The tool-holding LLM finished ~19
points *below* the planner it was holding.

Nobody has measured what a general-purpose tool roster with a light scaffold does to the
Mystery collapse. Every published rescue is a purpose-built formalization pipeline; the one
published general-tool result is +3pp. That is a genuinely open question, and it happens to
be the exact configuration our paper ships.

## 5. Strengthener verdicts

**(1) LLMFP as an independent replication of our NT layer — DOWNGRADE, do not call it a
replication.** Direct GPT-4o is 41.5 Blocksworld / 0.8 Mystery, and our Haiku is 41.0 / 0.8,
which looks like a 0.5pp match. It is not a like-for-like match: theirs is **optimal rate,
zero-shot**, ours is **VAL validity, one-shot**. A valid non-optimal plan counts for us and
not for them, so their validity-equivalent number is **≥41.5 and unknown** (they park success
rate in Appendix A.3, which I have not read). Usable as "consistent with", never as "replicates".

**(2) Valmeekam GPT-4 Mystery-t1 comparator — HOLDS, with a caveat the memo omitted.**
26/600 = 4.33% [2.97,6.27] is CI-disjoint above Haiku's 4/500 = 0.80% [0.31,2.04]. But it is
**unpaired and over a different pool**: 600 = our 500 plus the 100 `blocksworld_3` instances
we never ran, and **no GPT-4 Mystery t1 corpus exists on disk at all** (only blocksworld and
blocksworld_3), so it cannot be restricted to our 500. Since Haiku's 4 successes all have
gold plan length 2, and the extra 100 are the short-plan pool, GPT-4's successes may well
concentrate there. State it as a published cross-pool comparison, not a paired one.

## 6. Headline exposure found while checking §5 — needs one disclosure line

Act 4's headline compares Haiku **41.0%** [36.8,45.4] against GPT-4 **31.4%** [27.5,35.6]
(157/500) and calls it CI-disjoint. That is arithmetically correct **on the 500 instances both
models ran**, and it is the right paired comparison.

The exposure: the **published** GPT-4 number for that cell is **206/600 = 34.3%**
[30.6,38.2], and Haiku's 41.0% is **NOT** CI-disjoint from it (36.8 < 38.2).

Reconciled on disk: `blocksworld/gpt-4_chat` = 157/500 and `blocksworld_3/gpt-4_chat` =
**49/100**, and 157 + 49 = **206/600**. So the repo corpus is not a different run — it is the
published run, partitioned. The extra 100 instances are easier (GPT-4 scores 49% there vs
31.4% on ours), which is what lifts the pooled figure.

Nothing to fix in the numbers. But the paper must say "on the 500 shared instances, where
GPT-4 scored 31.4%; the published 34.3% pools in 100 additional easier instances we did not
run." Without that line, a reviewer opening Table 1 sees 34.3% and the disjointness
evaporates. Added to the NT doc.

## 7. t3 mix-confound audit — DONE, and the memo overstated it

Reproduced the memo's numbers exactly, then extended them. Field `llm_correct_binary`.

| model | cell | n | gold VALID share | raw acc | acc given VALID | acc given INVALID |
|---|---|---|---|---|---|---|
| Haiku | bw | 500 | 64.8% | 78.2% | 73.1% (237/324) | 87.5% (154/176) |
| Haiku | mystery | 500 | 64.8% | 45.4% | **25.9%** (84/324) | 81.2% (143/176) |
| GPT-4 | bw | 500 | 31.0% | 94.6% | 85.8% (133/155) | 98.6% (340/345) |
| GPT-4 | mystery | 500 | 31.0% | 73.6% | **94.2%** (146/155) | **64.3%** (222/345) |

The two models have **opposite response biases under obfuscation**: Haiku over-answers
INVALID (acc given VALID collapses to 25.9%), GPT-4 over-answers VALID (acc given INVALID
falls to 64.3%). With mixes that differ 64.8% vs 31.0%, a raw accuracy comparison is close to
uninterpretable. That part of the memo is right.

**Where the memo overstated:** it reported the Mystery gap collapsing "28.2pp → 9.5pp". That
9.5pp is what you get standardising to **GPT-4's own mix**, which is the single most
gap-shrinking choice available. Across defensible reference mixes:

| common mix | Haiku mystery | GPT-4 mystery | gap |
|---|---|---|---|
| unadjusted (each on its own mix) | 45.4 | 73.6 | 28.2pp |
| GPT-4's mix (31.0% VALID) | 64.1 | 73.6 | **9.5pp** |
| 50/50 | 53.6 | 79.3 | 25.7pp |
| our mix (64.8% VALID) | 45.4 | 83.7 | **38.3pp** |

So the gap is **not identified without fixing a reference mix, and it ranges 9.5-38.3pp**.
The correct statement is not "the gap collapses" — it is "the magnitude is mix-dependent and
must be reported per-verdict; the direction (Haiku below GPT-4 on verification) holds under
every mix." Finding 2's direction survives; only its size was unsafe.

Degenerate always-VALID baseline on our bw t3: 324/500 = 64.8% [60.5,68.9], so Haiku's 78.2
is +13.4pp above answering VALID every time. Confirmed as previously recorded.

## 8. What this does to the WT go/no-go

Net: **the arm's novelty is better than our own notes claimed, and the reason is §4.**

- The "already published ≥4×" claim is true for the *direction* (§3), so amendment J's
  wording stays honest: replication plus an ablation the field has not run.
- But no published work rescues Mystery by *tool availability*. The rescues are bespoke
  pipelines with repair loops; the plain give-it-a-solver baselines score **0.0-0.3**; the one
  general-tool result on our exact model is **+3.0pp**. Our four cells measure the
  configuration the paper actually ships, and its outcome is not predictable from any of these.
- Published effects at n=100 are internally inconsistent (Mystery *easier* than clean for
  gpt-4o; 8% → 99% for Gemma-2-27b). A paired n=500 measurement with CIs would be the
  best-powered number in this literature by a wide margin.
- Göbel's planner-alone 85.3% vs tool-holding-LLM 66.7% says the interesting quantity is the
  **gap to the planner**, which is what our delegation-rate and formalization-boundary
  mediators measure.

Recommendation unchanged: **option A, ratify shape B.** The prior art is real, and checking it
made the case stronger rather than weaker.
