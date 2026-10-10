# Re-analysis: per-wording, per-domain, classical vs numeric, test-data facts, and cost with real prices

*2026-10-02. Covers weaknesses C12, C21, C11 and C16 of `weakness_consolidated.md`.
Local re-analysis only: no cluster, no API calls, no spend, no edit to `paper/` or to any
tracked file. New scripts are in `tools/reanalysis/bc_*.py`; their outputs are in
`tools/reanalysis/out/breakdowns_cost/`. Nothing here proposes paper wording.*

**Data used.** `results/sweep5v2-live` (canonical) for every table below; `results/sweep6-live`
(anonymized) as a repeat check; `results/haiku-frontier`, `results/sonnet-frontier` for the
frontier rows; delivered verdicts from `results/derived/e2e_overlay`. The stale mirror
`results/sweep5-cluster-20260530` was never read. Models: Gemma 26B a4b, Qwen3.5 9B,
Qwen3.6 35B, reasoning off.

**How to read a cell.**

- *tool-verified* (tool arms only): the tool call returned the right result. Exact, shown
  with a Wilson 95% interval.
- *delivered*: the final answer the user receives is right. Where some stored answers were
  cut at the storage cap they can be neither confirmed nor refuted, so the cell is a bound
  `⟨low, high⟩ (cK)` with K the number of such rows. It is a single number only when K = 0.
- *final answer, strict* (no-tools arm): the harness's own grade of the answer. For every
  task except simulate this is the delivered score.

---

## What we found, and what it changes in the paper

**1. Wording (C12). The pooled numbers hide large differences between the three wordings.**

- The unaided solve "floor" of 8 to 11% is almost entirely one wording. With wording 2
  ("output each action on its own line") the three models solve 16%, 29% and 28%. With the
  other two wordings they solve 0 to 6%. Of the 83 unaided solve successes, 73 come from
  wording 2. On the two weak wordings 63 to 91% of trials fail because the grader could not
  read a plan out of the answer, not because a plan was wrong. The anonymized corpus shows
  the same pattern (13 / 31 / 29% against 0 to 7%).
- When the tool is available but the prompt does not name it, whether the model calls it
  depends on the wording. Gemma on plan checking calls the tool on 31%, 27% and 4% of
  trials. Qwen3.5 9B on simulate: 100%, 40%, 100%. Qwen3.6 35B: solve 80 / 63 / 61%,
  simulate 96 / 59 / 74%, plan checking 88 / 86 / 75%. So the abstract's "21%" is the average
  of 31, 27 and 4.
- Naming the tool in the prompt removes this: across wordings the steered arm's
  tool-verified rate differs by at most 5 points in every cell.
- Unaided validation barely moves with wording (plan checking at most 3.3 points, problem
  checking at most 7, domain checking at most 12.5).
- With tools, the delivered solve answer also depends on wording, and in opposite directions
  for different models: wording 2 is the worst for Gemma (steered: ⟨3, 26⟩ against ⟨35, 76⟩
  and ⟨33, 76⟩, a gap of at least 7 points however the cut-off answers resolve) and the best
  for both Qwen models.
- "Prompt v11" is simply the first of the three wordings. Every frontier tool run used only
  that one. Haiku's unaided run also used only v11; Sonnet's unaided run has all three. On
  Sonnet's unaided simulate, v11 has the lowest bound of the three wordings (⟨34, 53⟩,
  against ⟨38, 57⟩ and ⟨53, 74⟩). The v11 and wording-3 ranges only touch at 53, so the
  frontier simulate comparison probably uses the wording least favourable to the unaided
  arm, though the cut-off answers could still erase the difference. Sonnet's unaided solve
  is stable (26 to 31%).
- Sampling variation is in fact measurable from data already on disk. The grid sends some
  prompts five times unchanged. At temperature 0 those identical prompts do not always get
  the same grade: without tools, 12 to 16% of the five-prompt groups on plan checking and
  0 to 47% on domain checking are not unanimous (up to 14% of trials differ from their
  group's majority); with tools, 0 to 14% of groups.

*What it changes:* the paper needs the per-wording table; the unaided solve number has to be
described as depending on the wording and on answer format, not as a capability floor; the
21% invocation figure needs its per-wording range next to it; "prompt v11" needs one
defining sentence and the frontier needs "one wording only" stated as a limit; the sentence
that every trial is a single greedy sample can be accompanied by a measured repeat-to-repeat
disagreement rate.

**2. Domains (C21). No headline number is created by one domain, but several are averages
over very uneven domains.**

- Dropping any single domain moves any pooled cell by at most 3.9 points.
- Gemma's unprompted plan-checker calls come from five domains (blocksworld, farmland,
  gripper, miconic, counters: 519 of the 622 calls). Seven domains have zero calls. These
  five are exactly the five shortest domain files. The anonymized corpus repeats the pattern.
  With steering, barman stays at 18% and holds 55% of the remaining failures.
- Qwen3.5 9B's unaided domain checking (25.6%) is the same in almost every domain: it gets
  the invalid file right and the valid ones wrong (57 of 60 invalid right, 35 of 300 valid
  right). One domain, satellite, is 100%.
- Unaided solve successes are spread out (the top two domains have 11 each of 83). Barman
  and rovers are at zero for all three models.
- `counters` is the weak domain on the tool path for simulate and for 9B plan checking.

*What it changes:* a per-domain table can go in an appendix with a short note that the
pooled numbers are stable to dropping a domain; the 21% invocation result should say it is
concentrated in five small domains.

**3. Classical vs numeric (C21). "Numeric is harder" shows up in some cells and not in others.**

- Unaided domain checking is 20 to 29 points lower on numeric domains for all three models.
- Unaided solve is not lower on numeric (8.7 to 12.0% against 6.7 to 9.3% on classical).
- Tool-verified solve is within 3 points on both (Gemma, 9B) or higher on numeric (35B, by 4
  to 14 points).
- Tool-verified simulate is 5 to 11 points lower on numeric in four of six tool cells; 9B
  plan checking with tools is 6 to 10 points lower on numeric.
- Delivered solve with tools is lower on numeric (pooled steered ⟨85, 200⟩ of 450 against
  ⟨119, 317⟩ of 450), mainly because the final turn is empty after hitting the output cap
  about twice as often.
- Solve cost per success, tools against none, at equal token prices: classical 0.34 to 0.90
  times (the tool is cheaper), numeric 1.24 to 2.92 times (the tool is dearer) on the
  delivered score. On the tool-verified score the tool is cheaper on both (0.24 and 0.57).

*What it changes:* the split can be reported; the background sentence that numeric domains
are the harder case is supported for unaided domain checking and for tool-path simulate,
not for solve.

**4. Test-data facts (C11).** Section 4 lists them with file and line. The ones a reader
would not guess:

- Every tool trial shows the model all seven tools, not only the matching one, so tool
  selection is tested.
- The full PDDL text is pasted into the prompt, and the model must copy it into the tool
  call (it does so in every call that has a domain argument).
- The "five valid plans per problem" are five copies of one plan for 99 of 100 problems, and
  the valid-domain check is sent five times per domain with an identical prompt. Plan
  checking has 1,803 distinct prompts in 3,000 trials per arm; domain checking has 120 in 360.
- Domain checking is 100 valid to 20 invalid: answering VALID every time scores 83%.
- 12 of the 20 invalid domains differ from the valid one only by a parenthesis count; 5 use
  an undeclared predicate; 2 drop a `-` in a typed list; 1 has its predicates block removed.
- 76% of invalid plans are exactly one step shorter than the valid plan they came from.

**5. Cost (C16). The "invariant to price" sentence is wrong, and the direction of the error
depends on the roster.**

- The two arms have very different token mixes: with tools 5 to 13 input tokens per output
  token, without tools 0.3 to 1.7. So pricing output above input changes the ratio.
- *Open models.* Dearer output tokens make the tool look better, because the unaided model
  spends its tokens on output. Delivered solve, tools-steered against none, pooled: 0.65 to
  1.64 times at equal prices (undecided), 0.33 to 0.84 at 3:1, 0.28 to 0.72 at 4:1, 0.25 to
  0.64 at 5:1 (the tool is cheaper). The tool is certainly cheaper once output costs more
  than about 2.2 times input.
- *Frontier.* Price ratio matters little for solve and the tool does not pay at any ratio
  up to 5:1: Sonnet 3.1 times
  at equal prices, 2.8 at 5:1; Haiku 6.1 and 5.3. With Anthropic's cache discounts applied
  the list-price figures are 2.23 (Sonnet) and 3.55 (Haiku). As actually charged, with the
  unaided arm on the half-price Batch API, 4.45 and 7.10. For Sonnet simulate the 5.5 to 10.8
  times token premium becomes 2.1 to 4.1 at 5:1 (Haiku: 5.3 to 11.6 becomes 2.0 to 4.3).
- List prices used: Sonnet 4.6 $3 in / $15 out, Haiku 4.5 $1 in / $5 out per million tokens,
  both 5:1, from `tools/frontier_runner.py:71-74`.

*Where "the tool pays for itself" holds and where it does not:*

| cell | tool-verified score | delivered score |
|---|---|---|
| open models, solve, pooled | holds at every price ratio (0.38 at 1:1, 0.15 at 5:1) | undecided at 1:1 (0.65 to 1.64); holds from about 2.2:1 upward |
| open models, solve, classical domains | holds (0.24 at 1:1) | holds at every ratio (0.34 to 0.90 at 1:1) |
| open models, solve, numeric domains | holds (0.57 at 1:1) | does not hold at 1:1 (1.24 to 2.92); undecided at 3:1 to 5:1 (0.49 to 1.15 at 5:1) |
| open models, solve, Qwen3.6 35B alone | holds | undecided up to 4:1; holds at 5:1 by a hair (0.34 to 0.96) |
| open models, three validation tasks, pooled | does not hold from 1:1 to 5:1 (1.1 to 2.3 times at 5:1) | does not hold from 1:1 to 5:1 (1.1 to 2.6 times at 5:1); domain checking would cross at about 6:1 |
| Qwen3.5 9B, domain checking | does not hold at 1:1 (1.08); holds from 1.1:1 upward (0.38 at 5:1) | same |
| open models, simulate | not identified (no unaided success to divide by) | not identified |
| frontier, all five tasks, both tiers | does not hold from 1:1 to 5:1 under any of the three accountings (smallest: simulate, 1.4 times at 5:1) | does not hold from 1:1 to 5:1 under any of the three accountings (smallest: simulate, 2.0 to 4.3 times at 5:1 on the raw count; Sonnet solve, 2.2 times cache-billed) |

*What it changes:* the "invariant" sentence has to go; the solve claim can be stated on the
delivered score with the price ratio it needs; the frontier premium should be given in
dollars as well as tokens, since the two differ (3.1 and 6.1 in tokens, 2.2 and 3.6 at list
price with cache billing); the classical / numeric split shows that, on the delivered score,
the solve result is a classical-domain result. One small extra: the paper says the unaided input-to-output ratio is at
most 1:1; it is above 1:1 in 5 of the 15 unaided cells (up to 1.67:1).

---

## 0. Check before counting

`bc_reproduce_numbers.py` rebuilds the frozen figures these breakdowns decompose, and stops
if any differs. All pass, so there is no mismatch to explain.

| frozen figure (`NUMBERS.md`) | reproduced |
|---|---|
| all 45 headline cells per corpus in `pooled_e2e_table.csv` (n, delivered ok, censored, tool-verified) | identical, both corpora |
| Gemma plan-check invocation 622/3000 plain, 2808/3000 steered; 617 right of 622 | identical |
| Gemma plan-check delivered ⟨6.6, 99.6⟩ (c2790/3000) | identical |
| unaided simulate 0/3,000 on 10 no-tools cells; failure mix 1,772 / 1,202 / 26 | identical |
| delivered cost multiplier, pooled, steered / none: solve 0.65 to 1.64; vd 2.81 to 2.91; vp 4.41 to 4.86; vplan 4.11 to 5.16 | identical |
| frontier solve: Sonnet 18,634 vs 6,022 tokens per pass (3.1 times); Haiku 48,520 vs 7,997 (6.1 times) | identical |
| frontier solve delivered 95/100 both tiers; unaided 22/100 Haiku, 86/300 Sonnet | identical |

The dollar-per-pass figures in section 5 also match `reference/job2_delivered_reframe_worknote.md`
section 8.3 (Sonnet solve $0.067 and $0.015; Haiku $0.048 and $0.007).

---

## 1. Per-wording table (C12)

### 1.1 What "prompt v11" is

- The harness keeps one list of user-prompt templates per task. A "variant" is an index into
  that list. `pddl_eval/prompts.py:148` sets the active set to `(11, 12, 13, 14, 15, 16)`.
- v11, v12, v13 are the three plain wordings (`prompts.py:363-403`). The same text is used by
  the no-tools arm and the tools-plain arm (`prompts.py:22-26`).
- v14, v15, v16 are v11, v12, v13 plus one sentence naming the tool
  (`prompts.py:274-331`; `STEERED_VARIANTS` at `prompts.py:159`). That is the tools-steered arm.
- The system prompt is separate and depends only on task and arm, not on the variant
  (`prompts.py:82-142`, chosen at `runner.py:309-314`). The with-tools system prompt already
  tells the model to use the tool, in all six variants.
- So "prompt v11" is the first plain wording. For solve it reads "Solve this PDDL planning
  problem and return a plan. Each step must be a single parenthesised PDDL action, ..."
  (`prompts.py:365`).

The three plain solve wordings differ mainly in how they ask for the format:

| wording | variant | first sentence of the solve prompt (`prompts.py:365-369`) |
|---|---|---|
| 1 | v11 / v14 | Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. `(pick-up a)`. |
| 2 | v12 / v15 | Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`. |
| 3 | v13 / v16 | Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. `(stack a b)`. |

### 1.2 Which wordings the frontier runs used

- Frontier tool runs: v11 only, both tiers, canonical and anonymized (1,520 trials each =
  one wording). Selected by `tools/frontier_runner.py:299-300` (`--variant`, help text at
  `:561-562`). There is no steered frontier arm.
- Frontier unaided runs: Sonnet has all three plain wordings (4,560 trials); Haiku has v11
  only (1,520). Selected by `tools/claude_api_batch.py:342-345` (`--num-variants`, help at
  `:633-636`).
- The paper's frontier cells compare v11 with v11 (`reference/job2_delivered_reframe_worknote.md`
  section 8.3).

### 1.3 Tables (canonical corpus)

n per wording is one third of the pooled n. Spread is max minus min over the three wordings.
For a bound, three spreads are given: of the low ends, of the high ends, and "guaranteed",
the gap that remains however the cut-off answers resolve.

#### solve

| model | arm | score | n per wording | wording 1 (v11/v14) | wording 2 (v12/v15) | wording 3 (v13/v16) | max-min (pp) |
|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 100 | 1.0 [0.2, 5.4] | 16.0 [10.1, 24.4] | 6.0 [2.8, 12.5] | 15.0 |
| Gemma 26B a4b | tools-plain | tool-verified | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 98.0 [93.0, 99.4] | 2.0 |
|  |  | delivered | 100 | ⟨24.0, 47.0⟩ (c23) | ⟨2.0, 23.0⟩ (c21) | ⟨17.0, 36.0⟩ (c19) | low 22.0 / high 24.0 / guaranteed 1.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |
| Gemma 26B a4b | tools-steered | tool-verified | 100 | 97.0 [91.5, 99.0] | 100.0 [96.3, 100.0] | 99.0 [94.6, 99.8] | 3.0 |
|  |  | delivered | 100 | ⟨35.0, 76.0⟩ (c41) | ⟨3.0, 26.0⟩ (c23) | ⟨33.0, 76.0⟩ (c43) | low 32.0 / high 50.0 / guaranteed 9.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |
| Qwen3.5 9B | no-tools | final answer, strict | 100 | 2.0 [0.6, 7.0] | 29.0 [21.0, 38.5] | 1.0 [0.2, 5.4] | 28.0 |
| Qwen3.5 9B | tools-plain | tool-verified | 100 | 99.0 [94.6, 99.8] | 100.0 [96.3, 100.0] | 99.0 [94.6, 99.8] | 1.0 |
|  |  | delivered | 100 | ⟨21.0, 56.0⟩ (c35) | ⟨45.0, 70.0⟩ (c25) | ⟨12.0, 50.0⟩ (c38) | low 33.0 / high 20.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |
| Qwen3.5 9B | tools-steered | tool-verified | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |
|  |  | delivered | 100 | ⟨19.0, 57.0⟩ (c38) | ⟨52.0, 80.0⟩ (c28) | ⟨12.0, 59.0⟩ (c47) | low 40.0 / high 23.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |
| Qwen3.6 35B | no-tools | final answer, strict | 100 | 0.0 [0.0, 3.7] | 28.0 [20.1, 37.5] | 0.0 [0.0, 3.7] | 28.0 |
| Qwen3.6 35B | tools-plain | tool-verified | 100 | 73.0 [63.6, 80.7] | 59.0 [49.2, 68.1] | 57.0 [47.2, 66.3] | 16.0 |
|  |  | delivered | 100 | ⟨10.0, 48.0⟩ (c38) | ⟨21.0, 60.0⟩ (c39) | ⟨7.0, 53.0⟩ (c46) | low 14.0 / high 12.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 80.0 [71.1, 86.7] | 63.0 [53.2, 71.8] | 61.0 [51.2, 70.0] | 19.0 |
| Qwen3.6 35B | tools-steered | tool-verified | 100 | 95.0 [88.8, 97.8] | 91.0 [83.8, 95.2] | 90.0 [82.6, 94.5] | 5.0 |
|  |  | delivered | 100 | ⟨15.0, 48.0⟩ (c33) | ⟨29.0, 57.0⟩ (c28) | ⟨6.0, 38.0⟩ (c32) | low 23.0 / high 19.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 96.0 [90.2, 98.4] | 94.0 [87.5, 97.2] | 91.0 [83.8, 95.2] | 5.0 |

#### validate_domain

| model | arm | score | n per wording | wording 1 (v11/v14) | wording 2 (v12/v15) | wording 3 (v13/v16) | max-min (pp) |
|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 120 | 75.0 [66.6, 81.9] | 80.8 [72.9, 86.9] | 77.5 [69.2, 84.1] | 5.8 |
| Gemma 26B a4b | tools-plain | tool-verified | 120 | 98.3 [94.1, 99.5] | 97.5 [92.9, 99.1] | 96.7 [91.7, 98.7] | 1.7 |
|  |  | delivered | 120 | ⟨94.2, 99.2⟩ (c6) | ⟨91.7, 97.5⟩ (c7) | ⟨94.2, 97.5⟩ (c4) | low 2.5 / high 1.7 / guaranteed 0.0 |
|  |  | tool called | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
| Gemma 26B a4b | tools-steered | tool-verified | 120 | 98.3 [94.1, 99.5] | 98.3 [94.1, 99.5] | 98.3 [94.1, 99.5] | 0.0 |
|  |  | delivered | 120 | ⟨94.2, 98.3⟩ (c5) | ⟨95.8, 98.3⟩ (c3) | ⟨94.2, 98.3⟩ (c5) | low 1.7 / high 0.0 / guaranteed 0.0 |
|  |  | tool called | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
| Qwen3.5 9B | no-tools | final answer, strict | 120 | 32.5 [24.8, 41.3] | 24.2 [17.4, 32.6] | 20.0 [13.8, 28.0] | 12.5 |
| Qwen3.5 9B | tools-plain | tool-verified | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
|  |  | delivered | 120 | 100.0 [96.9, 100.0] | ⟨99.2, 100.0⟩ (c1) | 100.0 [96.9, 100.0] | low 0.8 / high 0.0 / guaranteed 0.0 |
|  |  | tool called | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
| Qwen3.5 9B | tools-steered | tool-verified | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
|  |  | delivered | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
|  |  | tool called | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
| Qwen3.6 35B | no-tools | final answer, strict | 120 | 66.7 [57.8, 74.5] | 64.2 [55.3, 72.2] | 72.5 [63.9, 79.7] | 8.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 120 | 100.0 [96.9, 100.0] | 99.2 [95.4, 99.9] | 97.5 [92.9, 99.1] | 2.5 |
|  |  | delivered | 120 | ⟨94.2, 100.0⟩ (c7) | ⟨92.5, 98.3⟩ (c7) | ⟨89.2, 99.2⟩ (c12) | low 5.0 / high 1.7 / guaranteed 0.0 |
|  |  | tool called | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |
| Qwen3.6 35B | tools-steered | tool-verified | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 99.2 [95.4, 99.9] | 0.8 |
|  |  | delivered | 120 | ⟨94.2, 100.0⟩ (c7) | ⟨95.0, 100.0⟩ (c6) | ⟨90.8, 99.2⟩ (c10) | low 4.2 / high 0.8 / guaranteed 0.0 |
|  |  | tool called | 120 | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 100.0 [96.9, 100.0] | 0.0 |

#### validate_problem

| model | arm | score | n per wording | wording 1 (v11/v14) | wording 2 (v12/v15) | wording 3 (v13/v16) | max-min (pp) |
|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 200 | 73.5 [67.0, 79.1] | 76.0 [69.6, 81.4] | 75.0 [68.6, 80.5] | 2.5 |
| Gemma 26B a4b | tools-plain | tool-verified | 200 | 99.5 [97.2, 99.9] | 100.0 [98.1, 100.0] | 99.5 [97.2, 99.9] | 0.5 |
|  |  | delivered | 200 | ⟨86.5, 99.5⟩ (c26) | ⟨84.5, 100.0⟩ (c31) | ⟨82.0, 100.0⟩ (c36) | low 4.5 / high 0.5 / guaranteed 0.0 |
|  |  | tool called | 200 | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 99.5 [97.2, 99.9] | 0.5 |
| Gemma 26B a4b | tools-steered | tool-verified | 200 | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 0.0 |
|  |  | delivered | 200 | ⟨92.0, 100.0⟩ (c16) | ⟨92.5, 100.0⟩ (c15) | ⟨90.5, 100.0⟩ (c19) | low 2.0 / high 0.0 / guaranteed 0.0 |
|  |  | tool called | 200 | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 0.0 |
| Qwen3.5 9B | no-tools | final answer, strict | 200 | 67.0 [60.2, 73.1] | 61.5 [54.6, 68.0] | 68.5 [61.8, 74.5] | 7.0 |
| Qwen3.5 9B | tools-plain | tool-verified | 200 | 96.0 [92.3, 98.0] | 95.0 [91.0, 97.3] | 94.5 [90.4, 96.9] | 1.5 |
|  |  | delivered | 200 | ⟨92.5, 96.0⟩ (c7) | ⟨92.5, 95.0⟩ (c5) | ⟨91.5, 95.0⟩ (c7) | low 1.0 / high 1.0 / guaranteed 0.0 |
|  |  | tool called | 200 | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 0.0 |
| Qwen3.5 9B | tools-steered | tool-verified | 200 | 91.0 [86.2, 94.2] | 90.0 [85.1, 93.4] | 89.5 [84.5, 93.0] | 1.5 |
|  |  | delivered | 200 | ⟨88.5, 91.5⟩ (c6) | ⟨88.0, 92.5⟩ (c9) | ⟨86.5, 89.0⟩ (c5) | low 2.0 / high 3.5 / guaranteed 0.0 |
|  |  | tool called | 200 | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 0.0 |
| Qwen3.6 35B | no-tools | final answer, strict | 200 | 73.5 [67.0, 79.1] | 76.0 [69.6, 81.4] | 77.5 [71.2, 82.7] | 4.0 |
| Qwen3.6 35B | tools-plain | tool-verified | 200 | 96.5 [93.0, 98.3] | 98.0 [95.0, 99.2] | 96.0 [92.3, 98.0] | 2.0 |
|  |  | delivered | 200 | ⟨75.5, 97.0⟩ (c43) | ⟨78.0, 97.5⟩ (c39) | ⟨70.5, 99.0⟩ (c57) | low 7.5 / high 2.0 / guaranteed 0.0 |
|  |  | tool called | 200 | 98.5 [95.7, 99.5] | 100.0 [98.1, 100.0] | 97.0 [93.6, 98.6] | 3.0 |
| Qwen3.6 35B | tools-steered | tool-verified | 200 | 97.5 [94.3, 98.9] | 97.0 [93.6, 98.6] | 97.5 [94.3, 98.9] | 0.5 |
|  |  | delivered | 200 | ⟨83.5, 97.0⟩ (c27) | ⟨81.0, 96.5⟩ (c31) | ⟨82.0, 97.5⟩ (c31) | low 2.5 / high 1.0 / guaranteed 0.0 |
|  |  | tool called | 200 | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 100.0 [98.1, 100.0] | 0.0 |

#### validate_plan

| model | arm | score | n per wording | wording 1 (v11/v14) | wording 2 (v12/v15) | wording 3 (v13/v16) | max-min (pp) |
|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 1000 | 88.0 [85.8, 89.9] | 88.6 [86.5, 90.4] | 86.9 [84.7, 88.9] | 1.7 |
| Gemma 26B a4b | tools-plain | tool-verified | 1000 | 30.9 [28.1, 33.8] | 26.6 [24.0, 29.4] | 4.2 [3.1, 5.6] | 26.7 |
|  |  | delivered | 1000 | ⟨10.8, 99.7⟩ (c889) | ⟨7.5, 99.1⟩ (c916) | ⟨1.4, 99.9⟩ (c985) | low 9.4 / high 0.8 / guaranteed 0.0 |
|  |  | tool called | 1000 | 31.2 [28.4, 34.1] | 26.8 [24.1, 29.6] | 4.2 [3.1, 5.6] | 27.0 |
| Gemma 26B a4b | tools-steered | tool-verified | 1000 | 93.4 [91.7, 94.8] | 92.3 [90.5, 93.8] | 92.0 [90.2, 93.5] | 1.4 |
|  |  | delivered | 1000 | ⟨56.4, 95.3⟩ (c389) | ⟨55.3, 95.4⟩ (c401) | ⟨54.8, 94.6⟩ (c398) | low 1.6 / high 0.8 / guaranteed 0.0 |
|  |  | tool called | 1000 | 94.2 [92.6, 95.5] | 93.0 [91.2, 94.4] | 93.6 [91.9, 95.0] | 1.2 |
| Qwen3.5 9B | no-tools | final answer, strict | 1000 | 80.5 [77.9, 82.8] | 77.7 [75.0, 80.2] | 81.0 [78.5, 83.3] | 3.3 |
| Qwen3.5 9B | tools-plain | tool-verified | 1000 | 93.7 [92.0, 95.0] | 95.5 [94.0, 96.6] | 90.3 [88.3, 92.0] | 5.2 |
|  |  | delivered | 1000 | ⟨80.2, 86.6⟩ (c64) | ⟨83.1, 87.6⟩ (c45) | ⟨79.0, 87.5⟩ (c85) | low 4.1 / high 1.0 / guaranteed 0.0 |
|  |  | tool called | 1000 | 98.8 [97.9, 99.3] | 100.0 [99.6, 100.0] | 94.9 [93.4, 96.1] | 5.1 |
| Qwen3.5 9B | tools-steered | tool-verified | 1000 | 95.8 [94.4, 96.9] | 95.8 [94.4, 96.9] | 96.5 [95.2, 97.5] | 0.7 |
|  |  | delivered | 1000 | ⟨86.9, 88.7⟩ (c18) | ⟨86.2, 88.6⟩ (c24) | ⟨87.7, 89.4⟩ (c17) | low 1.5 / high 0.8 / guaranteed 0.0 |
|  |  | tool called | 1000 | 100.0 [99.6, 100.0] | 100.0 [99.6, 100.0] | 100.0 [99.6, 100.0] | 0.0 |
| Qwen3.6 35B | no-tools | final answer, strict | 1000 | 91.0 [89.1, 92.6] | 90.5 [88.5, 92.2] | 91.2 [89.3, 92.8] | 0.7 |
| Qwen3.6 35B | tools-plain | tool-verified | 1000 | 87.6 [85.4, 89.5] | 85.6 [83.3, 87.6] | 73.3 [70.5, 75.9] | 14.3 |
|  |  | delivered | 1000 | ⟨53.4, 90.9⟩ (c375) | ⟨64.2, 91.2⟩ (c270) | ⟨47.4, 88.7⟩ (c413) | low 16.8 / high 2.5 / guaranteed 0.0 |
|  |  | tool called | 1000 | 87.8 [85.6, 89.7] | 86.3 [84.0, 88.3] | 74.6 [71.8, 77.2] | 13.2 |
| Qwen3.6 35B | tools-steered | tool-verified | 1000 | 99.3 [98.6, 99.7] | 99.2 [98.4, 99.6] | 99.3 [98.6, 99.7] | 0.1 |
|  |  | delivered | 1000 | ⟨73.3, 90.4⟩ (c171) | ⟨76.6, 89.4⟩ (c128) | ⟨77.7, 90.1⟩ (c124) | low 4.4 / high 1.0 / guaranteed 0.0 |
|  |  | tool called | 1000 | 99.8 [99.3, 99.9] | 100.0 [99.6, 100.0] | 99.9 [99.4, 100.0] | 0.2 |

#### simulate

| model | arm | score | n per wording | wording 1 (v11/v14) | wording 2 (v12/v15) | wording 3 (v13/v16) | max-min (pp) |
|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 100 | 0.0 [0.0, 3.7] | 0.0 [0.0, 3.7] | 0.0 [0.0, 3.7] | 0.0 |
|  |  | delivered | 100 | ⟨0.0, 100.0⟩ (c100) | ⟨0.0, 100.0⟩ (c100) | ⟨0.0, 100.0⟩ (c100) | low 0.0 / high 0.0 / guaranteed 0.0 |
| Gemma 26B a4b | tools-plain | tool-verified | 100 | 90.0 [82.6, 94.5] | 90.0 [82.6, 94.5] | 95.0 [88.8, 97.8] | 5.0 |
|  |  | delivered | 100 | ⟨0.0, 26.0⟩ (c26) | ⟨0.0, 27.0⟩ (c27) | ⟨0.0, 29.0⟩ (c29) | low 0.0 / high 3.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 99.0 [94.6, 99.8] | 100.0 [96.3, 100.0] | 1.0 |
| Gemma 26B a4b | tools-steered | tool-verified | 100 | 90.0 [82.6, 94.5] | 92.0 [85.0, 95.9] | 90.0 [82.6, 94.5] | 2.0 |
|  |  | delivered | 100 | ⟨0.0, 28.0⟩ (c28) | ⟨0.0, 25.0⟩ (c25) | ⟨0.0, 29.0⟩ (c29) | low 0.0 / high 4.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |
| Qwen3.5 9B | no-tools | final answer, strict | 100 | 0.0 [0.0, 3.7] | 0.0 [0.0, 3.7] | 0.0 [0.0, 3.7] | 0.0 |
|  |  | delivered | 100 | ⟨0.0, 99.0⟩ (c99) | ⟨0.0, 63.0⟩ (c63) | ⟨0.0, 100.0⟩ (c100) | low 0.0 / high 37.0 / guaranteed 0.0 |
| Qwen3.5 9B | tools-plain | tool-verified | 100 | 83.0 [74.5, 89.1] | 30.0 [21.9, 39.6] | 82.0 [73.3, 88.3] | 53.0 |
|  |  | delivered | 100 | ⟨0.0, 26.0⟩ (c26) | ⟨0.0, 66.0⟩ (c66) | ⟨0.0, 25.0⟩ (c25) | low 0.0 / high 41.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 40.0 [30.9, 49.8] | 100.0 [96.3, 100.0] | 60.0 |
| Qwen3.5 9B | tools-steered | tool-verified | 100 | 81.0 [72.2, 87.5] | 84.0 [75.6, 89.9] | 84.0 [75.6, 89.9] | 3.0 |
|  |  | delivered | 100 | ⟨0.0, 26.0⟩ (c26) | ⟨0.0, 26.0⟩ (c26) | ⟨0.0, 24.0⟩ (c24) | low 0.0 / high 2.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 99.0 [94.6, 99.8] | 100.0 [96.3, 100.0] | 1.0 |
| Qwen3.6 35B | no-tools | final answer, strict | 100 | 0.0 [0.0, 3.7] | 0.0 [0.0, 3.7] | 0.0 [0.0, 3.7] | 0.0 |
|  |  | delivered | 100 | ⟨0.0, 100.0⟩ (c100) | ⟨0.0, 72.0⟩ (c72) | ⟨0.0, 99.0⟩ (c99) | low 0.0 / high 28.0 / guaranteed 0.0 |
| Qwen3.6 35B | tools-plain | tool-verified | 100 | 93.0 [86.3, 96.6] | 59.0 [49.2, 68.1] | 72.0 [62.5, 79.9] | 34.0 |
|  |  | delivered | 100 | ⟨0.0, 29.0⟩ (c29) | ⟨0.0, 52.0⟩ (c52) | ⟨0.0, 36.0⟩ (c36) | low 0.0 / high 23.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 96.0 [90.2, 98.4] | 59.0 [49.2, 68.1] | 74.0 [64.6, 81.6] | 37.0 |
| Qwen3.6 35B | tools-steered | tool-verified | 100 | 96.0 [90.2, 98.4] | 97.0 [91.5, 99.0] | 98.0 [93.0, 99.4] | 2.0 |
|  |  | delivered | 100 | ⟨0.0, 27.0⟩ (c27) | ⟨0.0, 27.0⟩ (c27) | ⟨0.0, 27.0⟩ (c27) | low 0.0 / high 0.0 / guaranteed 0.0 |
|  |  | tool called | 100 | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 100.0 [96.3, 100.0] | 0.0 |

#### Frontier: which wordings exist (sweep5v2 prompt corpus)

| tier | cell | wordings present | trials |
|---|---|---|---|
| sonnet-frontier | sweep5v2 | v11, v12, v13 | 4560 |
| sonnet-frontier | sweep5v2-with-tools | v11 | 1520 |
| haiku-frontier | sweep5v2 | v11 | 1520 |
| haiku-frontier | sweep5v2-with-tools | v11 | 1520 |

#### Sonnet 4.6 no-tools, per wording (delivered)

| task | n per wording | wording 1 (v11) | wording 2 (v12) | wording 3 (v13) | max-min (pp) |
|---|---|---|---|---|---|
| solve | 100 | 29.0 [21.0, 38.5] | 31.0 [22.8, 40.6] | 26.0 [18.4, 35.4] | 5.0 |
| validate_domain | 120 | 93.3 [87.4, 96.6] | 93.3 [87.4, 96.6] | 94.2 [88.4, 97.1] | 0.8 |
| validate_problem | 200 | 86.5 [81.1, 90.6] | 88.5 [83.3, 92.2] | 94.0 [89.8, 96.5] | 7.5 |
| validate_plan | 1000 | 97.1 [95.9, 98.0] | 97.6 [96.5, 98.4] | 97.1 [95.9, 98.0] | 0.5 |
| simulate | 100 | ⟨34.0, 53.0⟩ (c19) | ⟨38.0, 57.0⟩ (c19) | ⟨53.0, 74.0⟩ (c21) | low 19.0 / high 21.0 / guaranteed 0.0 |

The same tables for the anonymized corpus are in
`tools/reanalysis/out/breakdowns_cost/per_wording_sweep6-live.md`. The unaided solve split
there is 4 / 13 / 7 (Gemma), 0 / 31 / 3 (9B), 0 / 29 / 0 (35B) per 100.

Why the two weak solve wordings fail without tools (failure reason per 100 trials, canonical):

| model | wording | solved | answer not parseable | cut off | plan wrong |
|---|---|---|---|---|---|
| Gemma | 1 | 1 | 82 | 15 | 2 |
| Gemma | 2 | 16 | 58 | 13 | 13 |
| Gemma | 3 | 6 | 63 | 20 | 11 |
| Qwen3.5 9B | 1 | 2 | 78 | 18 | 2 |
| Qwen3.5 9B | 2 | 29 | 13 | 25 | 33 |
| Qwen3.5 9B | 3 | 1 | 77 | 17 | 5 |
| Qwen3.6 35B | 1 | 0 | 88 | 12 | 0 |
| Qwen3.6 35B | 2 | 28 | 54 | 11 | 7 |
| Qwen3.6 35B | 3 | 0 | 91 | 7 | 2 |

(`failure_reason` in `trials.jsonl`: `format_parse_fail`, `truncated_no_answer`, `plan_invalid`.)

### 1.4 Identical prompts, different outcomes

The grid contains prompts that are sent five times unchanged (section 4, facts 9 and 10).
All trials run at temperature 0, so this is a direct look at run-to-run variation.

| model | arm | identical-prompt set | groups of 5 | groups not unanimous | share not unanimous | trials disagreeing with their group's majority |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | validate_domain, valid domain x5 | 60 | 13 | 21.7% | 19/300 (6.3%) |
| Gemma 26B a4b | no-tools | validate_plan, valid plan x5 | 297 | 44 | 14.8% | 63/1485 (4.2%) |
| Gemma 26B a4b | tools-plain | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Gemma 26B a4b | tools-plain | validate_plan, valid plan x5 | 297 | 8 | 2.7% | 12/1485 (0.8%) |
| Gemma 26B a4b | tools-steered | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Gemma 26B a4b | tools-steered | validate_plan, valid plan x5 | 297 | 8 | 2.7% | 12/1485 (0.8%) |
| Qwen3.5 9B | no-tools | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.5 9B | no-tools | validate_plan, valid plan x5 | 297 | 46 | 15.5% | 65/1485 (4.4%) |
| Qwen3.5 9B | tools-plain | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.5 9B | tools-plain | validate_plan, valid plan x5 | 297 | 11 | 3.7% | 17/1485 (1.1%) |
| Qwen3.5 9B | tools-steered | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.5 9B | tools-steered | validate_plan, valid plan x5 | 297 | 7 | 2.4% | 10/1485 (0.7%) |
| Qwen3.6 35B | no-tools | validate_domain, valid domain x5 | 60 | 28 | 46.7% | 41/300 (13.7%) |
| Qwen3.6 35B | no-tools | validate_plan, valid plan x5 | 297 | 37 | 12.5% | 50/1485 (3.4%) |
| Qwen3.6 35B | tools-plain | validate_domain, valid domain x5 | 60 | 1 | 1.7% | 2/300 (0.7%) |
| Qwen3.6 35B | tools-plain | validate_plan, valid plan x5 | 297 | 41 | 13.8% | 59/1485 (4.0%) |
| Qwen3.6 35B | tools-steered | validate_domain, valid domain x5 | 60 | 0 | 0.0% | 0/300 (0.0%) |
| Qwen3.6 35B | tools-steered | validate_plan, valid plan x5 | 297 | 7 | 2.4% | 8/1485 (0.5%) |

Reading: without tools, a prompt repeated five times does not always get the same grade.
This is a noise floor of a few points per trial, far smaller than the 28-point wording gaps
on solve, and comparable to the smaller wording gaps on validation.

---

## 2. Per-domain table (C21)

### 2.1 Compact tables

Harness score in percent (tool-verified on tool arms), three wordings pooled as in the
paper. n per domain per arm is in each heading. With n = 15 (solve, simulate) one trial is
6.7 points and the Wilson interval of a mid-range cell is roughly plus or minus 23 points,
so single domains should not be compared on those tasks. The full table with Wilson
intervals and delivered bounds is `tools/reanalysis/out/breakdowns_cost/per_domain_sweep5v2-live.md`
(and `.csv`).

Harness score % (tool-verified on tool arms). nt = no-tools, pl = tools-plain, st = tools-steered.

#### solve (n = 15 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 33 | 67 |
| blocksworld | classical | 7 | 100 | 100 | 13 | 100 | 100 | 13 | 53 | 100 |
| depots | classical | 7 | 100 | 100 | 7 | 100 | 100 | 7 | 60 | 93 |
| gripper | classical | 33 | 100 | 100 | 33 | 100 | 100 | 7 | 53 | 100 |
| miconic | classical | 13 | 100 | 100 | 20 | 100 | 100 | 13 | 67 | 100 |
| parking | classical | 0 | 100 | 100 | 7 | 100 | 100 | 7 | 53 | 80 |
| rovers | classical | 0 | 100 | 100 | 0 | 100 | 100 | 0 | 47 | 73 |
| satellite | classical | 0 | 100 | 100 | 7 | 100 | 100 | 13 | 67 | 100 |
| tpp | classical | 7 | 93 | 100 | 0 | 100 | 100 | 0 | 47 | 87 |
| zenotravel | classical | 0 | 100 | 100 | 7 | 100 | 100 | 7 | 80 | 100 |
| block-grouping | numeric | 27 | 100 | 100 | 27 | 100 | 100 | 20 | 93 | 100 |
| counters | numeric | 20 | 100 | 100 | 0 | 100 | 100 | 13 | 100 | 100 |
| delivery | numeric | 7 | 93 | 93 | 13 | 100 | 100 | 7 | 73 | 100 |
| depot | numeric | 7 | 100 | 100 | 0 | 100 | 100 | 0 | 27 | 73 |
| drone | numeric | 7 | 100 | 100 | 20 | 87 | 100 | 7 | 80 | 80 |
| farmland | numeric | 7 | 100 | 100 | 0 | 100 | 100 | 7 | 87 | 100 |
| gardening | numeric | 7 | 100 | 100 | 27 | 100 | 100 | 27 | 80 | 100 |
| pogo_stick | numeric | 0 | 100 | 80 | 13 | 100 | 100 | 13 | 53 | 87 |
| sailing | numeric | 0 | 100 | 100 | 7 | 100 | 100 | 13 | 67 | 100 |
| zenotravel-numeric | numeric | 7 | 100 | 100 | 13 | 100 | 100 | 13 | 40 | 100 |

#### validate_domain (n = 18 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 94 | 100 | 100 | 17 | 100 | 100 | 83 | 100 | 100 |
| blocksworld | classical | 100 | 100 | 100 | 17 | 100 | 100 | 56 | 100 | 100 |
| depots | classical | 89 | 100 | 100 | 17 | 100 | 100 | 89 | 100 | 100 |
| gripper | classical | 83 | 100 | 100 | 44 | 100 | 100 | 72 | 100 | 100 |
| miconic | classical | 83 | 100 | 100 | 44 | 100 | 100 | 83 | 100 | 100 |
| parking | classical | 83 | 100 | 100 | 67 | 100 | 100 | 78 | 100 | 100 |
| rovers | classical | 100 | 100 | 100 | 17 | 100 | 100 | 100 | 89 | 100 |
| satellite | classical | 100 | 83 | 83 | 100 | 100 | 100 | 83 | 100 | 100 |
| tpp | classical | 83 | 100 | 100 | 17 | 100 | 100 | 94 | 100 | 100 |
| zenotravel | classical | 83 | 100 | 100 | 17 | 100 | 100 | 83 | 100 | 100 |
| block-grouping | numeric | 17 | 100 | 100 | 17 | 100 | 100 | 17 | 100 | 100 |
| counters | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 72 | 100 | 100 |
| delivery | numeric | 61 | 83 | 89 | 11 | 100 | 100 | 78 | 89 | 94 |
| depot | numeric | 100 | 100 | 100 | 17 | 100 | 100 | 100 | 100 | 100 |
| drone | numeric | 33 | 100 | 100 | 17 | 100 | 100 | 28 | 100 | 100 |
| farmland | numeric | 100 | 100 | 100 | 11 | 100 | 100 | 17 | 100 | 100 |
| gardening | numeric | 39 | 89 | 94 | 17 | 100 | 100 | 44 | 100 | 100 |
| pogo_stick | numeric | 83 | 100 | 100 | 17 | 100 | 100 | 67 | 100 | 100 |
| sailing | numeric | 94 | 94 | 100 | 17 | 100 | 100 | 72 | 100 | 100 |
| zenotravel-numeric | numeric | 28 | 100 | 100 | 17 | 100 | 100 | 39 | 100 | 100 |

#### validate_problem (n = 30 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 50 | 100 | 100 | 67 | 93 | 97 | 67 | 97 | 97 |
| blocksworld | classical | 83 | 100 | 100 | 77 | 100 | 100 | 80 | 97 | 100 |
| depots | classical | 60 | 100 | 100 | 73 | 100 | 100 | 60 | 100 | 100 |
| gripper | classical | 87 | 100 | 100 | 83 | 97 | 93 | 83 | 90 | 90 |
| miconic | classical | 80 | 100 | 100 | 87 | 90 | 90 | 73 | 90 | 90 |
| parking | classical | 97 | 100 | 100 | 73 | 100 | 100 | 90 | 100 | 100 |
| rovers | classical | 60 | 97 | 100 | 30 | 100 | 100 | 50 | 97 | 97 |
| satellite | classical | 80 | 100 | 100 | 73 | 90 | 80 | 83 | 93 | 97 |
| tpp | classical | 70 | 100 | 100 | 67 | 97 | 93 | 70 | 97 | 100 |
| zenotravel | classical | 70 | 100 | 100 | 63 | 90 | 90 | 83 | 97 | 97 |
| block-grouping | numeric | 70 | 100 | 100 | 43 | 90 | 90 | 70 | 100 | 100 |
| counters | numeric | 83 | 100 | 100 | 37 | 100 | 100 | 70 | 100 | 100 |
| delivery | numeric | 73 | 100 | 100 | 60 | 90 | 90 | 70 | 97 | 90 |
| depot | numeric | 47 | 100 | 100 | 67 | 100 | 100 | 80 | 90 | 90 |
| drone | numeric | 83 | 100 | 100 | 67 | 100 | 100 | 93 | 97 | 100 |
| farmland | numeric | 90 | 100 | 100 | 77 | 100 | 100 | 87 | 100 | 100 |
| gardening | numeric | 77 | 100 | 100 | 57 | 90 | 43 | 77 | 100 | 100 |
| pogo_stick | numeric | 90 | 97 | 100 | 73 | 97 | 63 | 80 | 100 | 100 |
| sailing | numeric | 87 | 100 | 100 | 67 | 90 | 80 | 73 | 100 | 100 |
| zenotravel-numeric | numeric | 60 | 100 | 100 | 73 | 90 | 93 | 73 | 97 | 100 |

#### validate_plan (n = 150 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 59 | 0 | 18 | 57 | 97 | 99 | 82 | 95 | 100 |
| blocksworld | classical | 100 | 80 | 100 | 97 | 100 | 100 | 100 | 88 | 100 |
| depots | classical | 91 | 0 | 100 | 65 | 100 | 100 | 97 | 99 | 99 |
| gripper | classical | 95 | 67 | 98 | 83 | 100 | 100 | 99 | 95 | 99 |
| miconic | classical | 93 | 66 | 99 | 93 | 100 | 100 | 94 | 31 | 100 |
| parking | classical | 89 | 3 | 100 | 81 | 99 | 100 | 87 | 93 | 100 |
| rovers | classical | 91 | 0 | 72 | 78 | 99 | 100 | 94 | 82 | 100 |
| satellite | classical | 93 | 4 | 99 | 96 | 87 | 93 | 97 | 46 | 100 |
| tpp | classical | 77 | 9 | 100 | 67 | 100 | 100 | 78 | 99 | 100 |
| zenotravel | classical | 92 | 14 | 98 | 87 | 100 | 100 | 94 | 91 | 100 |
| block-grouping | numeric | 85 | 0 | 100 | 81 | 81 | 87 | 87 | 66 | 97 |
| counters | numeric | 80 | 63 | 95 | 65 | 63 | 65 | 76 | 61 | 96 |
| delivery | numeric | 85 | 0 | 99 | 92 | 100 | 100 | 95 | 100 | 100 |
| depot | numeric | 79 | 0 | 82 | 53 | 97 | 100 | 83 | 93 | 100 |
| drone | numeric | 95 | 11 | 98 | 73 | 90 | 89 | 93 | 99 | 100 |
| farmland | numeric | 99 | 70 | 100 | 95 | 91 | 100 | 99 | 98 | 100 |
| gardening | numeric | 86 | 4 | 100 | 67 | 100 | 99 | 88 | 89 | 100 |
| pogo_stick | numeric | 86 | 0 | 100 | 95 | 68 | 100 | 98 | 86 | 98 |
| sailing | numeric | 86 | 9 | 97 | 81 | 90 | 90 | 87 | 41 | 97 |
| zenotravel-numeric | numeric | 94 | 13 | 96 | 88 | 100 | 100 | 90 | 93 | 99 |

#### simulate (n = 15 per domain per arm)

| domain | track | Gemma nt | Gemma pl | Gemma st | Qwen3.5 nt | Qwen3.5 pl | Qwen3.5 st | Qwen3.6 nt | Qwen3.6 pl | Qwen3.6 st |
|---|---|---|---|---|---|---|---|---|---|---|
| barman | classical | 0 | 100 | 100 | 0 | 47 | 67 | 0 | 100 | 100 |
| blocksworld | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 93 | 100 |
| depots | classical | 0 | 100 | 100 | 0 | 80 | 100 | 0 | 87 | 100 |
| gripper | classical | 0 | 100 | 100 | 0 | 87 | 100 | 0 | 80 | 100 |
| miconic | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 40 | 100 |
| parking | classical | 0 | 100 | 100 | 0 | 73 | 100 | 0 | 67 | 100 |
| rovers | classical | 0 | 93 | 100 | 0 | 67 | 93 | 0 | 100 | 93 |
| satellite | classical | 0 | 73 | 73 | 0 | 47 | 73 | 0 | 67 | 100 |
| tpp | classical | 0 | 93 | 100 | 0 | 27 | 47 | 0 | 73 | 100 |
| zenotravel | classical | 0 | 100 | 87 | 0 | 73 | 100 | 0 | 20 | 100 |
| block-grouping | numeric | 0 | 100 | 100 | 0 | 67 | 67 | 0 | 73 | 100 |
| counters | numeric | 0 | 73 | 53 | 0 | 13 | 20 | 0 | 53 | 73 |
| delivery | numeric | 0 | 100 | 100 | 0 | 80 | 100 | 0 | 100 | 100 |
| depot | numeric | 0 | 100 | 100 | 0 | 67 | 93 | 0 | 80 | 100 |
| drone | numeric | 0 | 73 | 53 | 0 | 53 | 60 | 0 | 93 | 100 |
| farmland | numeric | 0 | 100 | 100 | 0 | 93 | 100 | 0 | 73 | 100 |
| gardening | numeric | 0 | 80 | 87 | 0 | 67 | 80 | 0 | 67 | 93 |
| pogo_stick | numeric | 0 | 60 | 60 | 0 | 67 | 80 | 0 | 73 | 80 |
| sailing | numeric | 0 | 93 | 100 | 0 | 80 | 80 | 0 | 67 | 100 |
| zenotravel-numeric | numeric | 0 | 93 | 100 | 0 | 67 | 100 | 0 | 87 | 100 |

### 2.2 Domains that drive a headline number

Rule used: a cell is flagged if dropping one domain shifts the pooled rate by 3.0 points or
more, or if one domain holds 40% or more of the cell's rarer outcome (at least 5 such rows).
Largest leave-one-out shift over all 45 cells: 3.9 points.

| model | task | arm | pooled % | lowest domain | highest domain | domains at 0 / at 100 | leave-one-out range | top domain of the rarer outcome |
|---|---|---|---|---|---|---|---|---|
| Gemma 26B a4b | validate_domain | no-tools | 77.8 | block-grouping=17 | blocksworld=100 | 0 / 6 | 76.6 (drop blocksworld) .. 81.0 (drop block-grouping) | block-grouping: 18.8% of 80 failures |
| Gemma 26B a4b | validate_domain | tools-steered | 98.3 | satellite=83 | barman=100 | 0 / 17 | 98.2 (drop barman) .. 99.1 (drop satellite) | satellite: 50.0% of 6 failures |
| Gemma 26B a4b | validate_plan | tools-plain | 20.6 | barman=0 | blocksworld=80 | 7 / 0 | 17.4 (drop blocksworld) .. 21.6 (drop barman) | blocksworld: 19.4% of 617 successes |
| Gemma 26B a4b | validate_plan | tools-steered | 92.6 | barman=18 | blocksworld=100 | 0 / 8 | 92.2 (drop blocksworld) .. 96.5 (drop barman) | barman: 55.2% of 223 failures |
| Qwen3.5 9B | validate_domain | no-tools | 25.6 | delivery=11 | satellite=100 | 0 / 1 | 21.6 (drop satellite) .. 26.3 (drop delivery) | satellite: 19.6% of 92 successes |
| Qwen3.5 9B | validate_plan | tools-steered | 96.0 | counters=65 | blocksworld=100 | 0 / 13 | 95.8 (drop blocksworld) .. 97.7 (drop counters) | counters: 44.5% of 119 failures |
| Qwen3.5 9B | simulate | tools-steered | 83.0 | counters=20 | blocksworld=100 | 0 / 9 | 82.1 (drop blocksworld) .. 86.3 (drop counters) | counters: 23.5% of 51 failures |
| Qwen3.6 35B | simulate | tools-steered | 97.0 | counters=73 | barman=100 | 0 / 16 | 96.8 (drop barman) .. 98.2 (drop counters) | counters: 44.4% of 9 failures |

Three patterns behind headline numbers, beyond the flags:

- **The 21% invocation figure (Gemma, plan checking, tools-plain).** Tool calls per domain
  out of 150: blocksworld 120, farmland 105, gripper 100, miconic 99, counters 95, then
  zenotravel 23, zenotravel-numeric 20, drone 16, sailing 14, tpp 13, satellite 6, gardening 6,
  parking 5, and zero in barman, depots, rovers, block-grouping, delivery, depot, pogo_stick.
  The top five are the five shortest domain files (686 to 1,228 characters; the sixth
  shortest is 1,521). Anonymized corpus: counters 102, farmland 103, gripper 86,
  blocksworld 69, miconic 66 of 544 calls in total. This is an observed association, not a
  tested cause.
- **The steered repair (same cell, 94%).** Steered calls per domain are 150 of 150 in 17
  domains, and 27 (barman), 108 (rovers), 123 (depot) in the other three. Barman has the
  longest domain file (5,542 characters).
- **Qwen3.5 9B unaided domain checking (25.6%).** 17% (3 of 18, the three invalid trials) in
  14 domains, 11% in two, 44% in two, 67% in one, 100% in satellite.

---

## 3. Classical vs numeric (C21)

### 3.1 How the harness labels them

The label is the directory: `domains/classical/<name>/` or `domains/numeric/<name>/`.
`pddl_eval/domains.py:45` walks those two directories and stores the name as `type`
(`domains.py:85`). The only use at run time is to pick the oracle planner
(`domains.py:162`). The analyzer metadata carries the same label as `track`
(`.claude/skills/analyzer/scripts/gen_meta.py:107-113`). Ten domains each; note that
`depots` (classical) and `depot` (numeric), and `zenotravel` and `zenotravel-numeric`, are
separate domains.

### 3.2 Tables

n per track is half the pooled n. The solve cost split is at the end.

#### solve

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 150 | 6.7 [3.7, 11.8] | 8.7 [5.1, 14.3] | +2.0 |
| Gemma 26B a4b | tools-plain | tool-verified | 150 | 99.3 [96.3, 99.9] | 99.3 [96.3, 99.9] | +0.0 |
|  |  | delivered | 150 | ⟨14.0, 35.3⟩ (c32) | ⟨14.7, 35.3⟩ (c31) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 150 | 100.0 [97.5, 100.0] | 97.3 [93.3, 99.0] | -2.7 |
|  |  | delivered | 150 | ⟨26.7, 65.3⟩ (c58) | ⟨20.7, 53.3⟩ (c49) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 150 | 9.3 [5.6, 15.1] | 12.0 [7.7, 18.2] | +2.7 |
| Qwen3.5 9B | tools-plain | tool-verified | 150 | 100.0 [97.5, 100.0] | 98.7 [95.3, 99.6] | -1.3 |
|  |  | delivered | 150 | ⟨36.0, 82.7⟩ (c70) | ⟨16.0, 34.7⟩ (c28) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 150 | 100.0 [97.5, 100.0] | 100.0 [97.5, 100.0] | +0.0 |
|  |  | delivered | 150 | ⟨32.0, 88.7⟩ (c85) | ⟨23.3, 42.0⟩ (c28) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 150 | 6.7 [3.7, 11.8] | 12.0 [7.7, 18.2] | +5.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 150 | 56.0 [48.0, 63.7] | 70.0 [62.2, 76.8] | +14.0 |
|  |  | delivered | 150 | ⟨15.3, 69.3⟩ (c81) | ⟨10.0, 38.0⟩ (c42) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 150 | 90.0 [84.2, 93.8] | 94.0 [89.0, 96.8] | +4.0 |
|  |  | delivered | 150 | ⟨20.7, 57.3⟩ (c55) | ⟨12.7, 38.0⟩ (c38) |  |

#### validate_domain

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 180 | 90.0 [84.7, 93.6] | 65.6 [58.4, 72.1] | -24.4 |
| Gemma 26B a4b | tools-plain | tool-verified | 180 | 98.3 [95.2, 99.4] | 96.7 [92.9, 98.5] | -1.7 |
|  |  | delivered | 180 | ⟨97.8, 98.3⟩ (c1) | ⟨88.9, 97.8⟩ (c16) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 180 | 98.3 [95.2, 99.4] | 98.3 [95.2, 99.4] | +0.0 |
|  |  | delivered | 180 | 98.3 [95.2, 99.4] | ⟨91.1, 98.3⟩ (c13) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 180 | 35.6 [28.9, 42.8] | 15.6 [11.0, 21.6] | -20.0 |
| Qwen3.5 9B | tools-plain | tool-verified | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] | +0.0 |
|  |  | delivered | 180 | 100.0 [97.9, 100.0] | ⟨99.4, 100.0⟩ (c1) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] | +0.0 |
|  |  | delivered | 180 | 100.0 [97.9, 100.0] | 100.0 [97.9, 100.0] |  |
| Qwen3.6 35B | no-tools | final answer, strict | 180 | 82.2 [76.0, 87.1] | 53.3 [46.1, 60.5] | -28.9 |
| Qwen3.6 35B | tools-plain | tool-verified | 180 | 98.9 [96.0, 99.7] | 98.9 [96.0, 99.7] | +0.0 |
|  |  | delivered | 180 | ⟨91.1, 99.4⟩ (c15) | ⟨92.8, 98.9⟩ (c11) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 180 | 100.0 [97.9, 100.0] | 99.4 [96.9, 99.9] | -0.6 |
|  |  | delivered | 180 | ⟨92.8, 100.0⟩ (c13) | ⟨93.9, 99.4⟩ (c10) |  |

#### validate_problem

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 300 | 73.7 [68.4, 78.3] | 76.0 [70.9, 80.5] | +2.3 |
| Gemma 26B a4b | tools-plain | tool-verified | 300 | 99.7 [98.1, 99.9] | 99.7 [98.1, 99.9] | +0.0 |
|  |  | delivered | 300 | ⟨90.3, 100.0⟩ (c29) | ⟨78.3, 99.7⟩ (c64) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 300 | 100.0 [98.7, 100.0] | 100.0 [98.7, 100.0] | +0.0 |
|  |  | delivered | 300 | ⟨91.7, 100.0⟩ (c25) | ⟨91.7, 100.0⟩ (c25) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 300 | 69.3 [63.9, 74.3] | 62.0 [56.4, 67.3] | -7.3 |
| Qwen3.5 9B | tools-plain | tool-verified | 300 | 95.7 [92.7, 97.5] | 94.7 [91.5, 96.7] | -1.0 |
|  |  | delivered | 300 | ⟨91.3, 96.0⟩ (c14) | ⟨93.0, 94.7⟩ (c5) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 300 | 94.3 [91.1, 96.4] | 86.0 [81.6, 89.5] | -8.3 |
|  |  | delivered | 300 | ⟨90.0, 94.3⟩ (c13) | ⟨85.3, 87.7⟩ (c7) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 300 | 74.0 [68.8, 78.6] | 77.3 [72.3, 81.7] | +3.3 |
| Qwen3.6 35B | tools-plain | tool-verified | 300 | 95.7 [92.7, 97.5] | 98.0 [95.7, 99.1] | +2.3 |
|  |  | delivered | 300 | ⟨74.7, 97.7⟩ (c69) | ⟨74.7, 98.0⟩ (c70) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 300 | 96.7 [94.0, 98.2] | 98.0 [95.7, 99.1] | +1.3 |
|  |  | delivered | 300 | ⟨81.7, 96.7⟩ (c45) | ⟨82.7, 97.3⟩ (c44) |  |

#### validate_plan

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 1500 | 88.1 [86.4, 89.7] | 87.5 [85.8, 89.1] | -0.6 |
| Gemma 26B a4b | tools-plain | tool-verified | 1500 | 24.3 [22.2, 26.5] | 16.9 [15.1, 18.8] | -7.4 |
|  |  | delivered | 1500 | ⟨9.1, 100.0⟩ (c1364) | ⟨4.1, 99.1⟩ (c1426) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 1500 | 88.4 [86.7, 89.9] | 96.7 [95.7, 97.5] | +8.3 |
|  |  | delivered | 1500 | ⟨58.3, 98.4⟩ (c602) | ⟨52.7, 91.8⟩ (c586) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 1500 | 80.5 [78.4, 82.4] | 79.0 [76.9, 81.0] | -1.5 |
| Qwen3.5 9B | tools-plain | tool-verified | 1500 | 98.3 [97.5, 98.8] | 88.1 [86.3, 89.6] | -10.2 |
|  |  | delivered | 1500 | ⟨85.9, 91.9⟩ (c90) | ⟨75.7, 82.6⟩ (c104) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 1500 | 99.1 [98.5, 99.5] | 92.9 [91.5, 94.1] | -6.2 |
|  |  | delivered | 1500 | ⟨90.4, 93.9⟩ (c53) | ⟨83.5, 83.9⟩ (c6) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 1500 | 92.2 [90.7, 93.5] | 89.6 [88.0, 91.0] | -2.6 |
| Qwen3.6 35B | tools-plain | tool-verified | 1500 | 81.8 [79.8, 83.7] | 82.5 [80.5, 84.4] | +0.7 |
|  |  | delivered | 1500 | ⟨57.3, 93.1⟩ (c537) | ⟨52.7, 87.4⟩ (c521) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 1500 | 99.8 [99.4, 99.9] | 98.7 [98.0, 99.2] | -1.1 |
|  |  | delivered | 1500 | ⟨79.3, 93.7⟩ (c216) | ⟨72.5, 86.3⟩ (c207) |  |

#### simulate

| model | arm | score | n per track | classical | numeric | numeric - classical (pp) |
|---|---|---|---|---|---|---|
| Gemma 26B a4b | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 100.0⟩ (c150) | ⟨0.0, 100.0⟩ (c150) |  |
| Gemma 26B a4b | tools-plain | tool-verified | 150 | 96.0 [91.5, 98.2] | 87.3 [81.1, 91.7] | -8.7 |
|  |  | delivered | 150 | ⟨0.0, 24.0⟩ (c36) | ⟨0.0, 30.7⟩ (c46) |  |
| Gemma 26B a4b | tools-steered | tool-verified | 150 | 96.0 [91.5, 98.2] | 85.3 [78.8, 90.1] | -10.7 |
|  |  | delivered | 150 | ⟨0.0, 24.0⟩ (c36) | ⟨0.0, 30.7⟩ (c46) |  |
| Qwen3.5 9B | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 86.0⟩ (c129) | ⟨0.0, 88.7⟩ (c133) |  |
| Qwen3.5 9B | tools-plain | tool-verified | 150 | 64.7 [56.7, 71.9] | 65.3 [57.4, 72.5] | +0.7 |
|  |  | delivered | 150 | ⟨0.0, 36.0⟩ (c54) | ⟨0.0, 42.0⟩ (c63) |  |
| Qwen3.5 9B | tools-steered | tool-verified | 150 | 88.0 [81.8, 92.3] | 78.0 [70.7, 83.9] | -10.0 |
|  |  | delivered | 150 | ⟨0.0, 20.7⟩ (c31) | ⟨0.0, 30.0⟩ (c45) |  |
| Qwen3.6 35B | no-tools | final answer, strict | 150 | 0.0 [0.0, 2.5] | 0.0 [0.0, 2.5] | +0.0 |
|  |  | delivered | 150 | ⟨0.0, 92.7⟩ (c139) | ⟨0.0, 88.0⟩ (c132) |  |
| Qwen3.6 35B | tools-plain | tool-verified | 150 | 72.7 [65.0, 79.2] | 76.7 [69.3, 82.7] | +4.0 |
|  |  | delivered | 150 | ⟨0.0, 40.7⟩ (c61) | ⟨0.0, 37.3⟩ (c56) |  |
| Qwen3.6 35B | tools-steered | tool-verified | 150 | 99.3 [96.3, 99.9] | 94.7 [89.8, 97.3] | -4.7 |
|  |  | delivered | 150 | ⟨0.0, 24.0⟩ (c36) | ⟨0.0, 30.0⟩ (c45) |  |

#### solve cost-of-pass by track (pooled over the three models)

Tokens = prompt + completion summed over turns (the paper's count). Cost-of-pass = total tokens / successes. Multiplier = tools / no-tools. Delivered is a range because the tool arm's delivered count is a bound.

| track | tool arm | no-tools successes | no-tools tok/trial | no-tools tok/pass | tool-verified ok | delivered ok ⟨low, high⟩ | tools tok/trial | multiplier, tool-verified | multiplier, delivered |
|---|---|---|---|---|---|---|---|---|---|
| all | tools-plain | 83/900 (9.2%) | 4,488 | 48,666 | 785/900 | ⟨159, 443⟩/900 | 18,706 | 0.44x | 0.78x to 2.18x |
| all | tools-steered | 83/900 (9.2%) | 4,488 | 48,666 | 872/900 | ⟨204, 517⟩/900 | 18,108 | 0.38x | 0.65x to 1.64x |
| classical | tools-plain | 34/450 (7.6%) | 4,795 | 63,464 | 383/450 | ⟨98, 281⟩/450 | 15,601 | 0.29x | 0.39x to 1.13x |
| classical | tools-steered | 34/450 (7.6%) | 4,795 | 63,464 | 435/450 | ⟨119, 317⟩/450 | 15,027 | 0.24x | 0.34x to 0.90x |
| numeric | tools-plain | 49/450 (10.9%) | 4,181 | 38,398 | 402/450 | ⟨61, 162⟩/450 | 21,810 | 0.64x | 1.58x to 4.19x |
| numeric | tools-steered | 49/450 (10.9%) | 4,181 | 38,398 | 437/450 | ⟨85, 200⟩/450 | 21,189 | 0.57x | 1.24x to 2.92x |

On the anonymized corpus the solve cost split is the same shape: classical 0.27 to 0.79
times, numeric 1.46 to 4.39 times (steered, delivered); tool-verified 0.19 and 0.67
(`solve_cost_by_track_sweep6-live.csv`).

Why delivered solve is lower on numeric domains with tools (pooled, three models, overlay
`e2e_reason`):

| arm | track | plan delivered and valid | plan delivered, invalid | final turn empty after the cap | cut at storage cap (unknown) |
|---|---|---|---|---|---|
| tools-plain | classical | 98 | 66 | 103 | 183 |
| tools-plain | numeric | 61 | 55 | 233 | 101 |
| tools-steered | classical | 119 | 39 | 94 | 198 |
| tools-steered | numeric | 85 | 41 | 208 | 115 |

---

## 4. Test-data description facts (C11)

Facts only, each with its source. Measured values come from `bc_fixture_facts.py` and
`bc_duplicate_prompts.py`.

### 4.1 Where the files come from and how many there are

1. 20 domains, 10 under `domains/classical/` and 10 under `domains/numeric/`. Ten were copied
   from the 2025 paper dataset and ten were added from public suites (`domains/README.md:7-11`).
2. Each domain has 1 valid domain, 1 invalid domain, 5 valid problems, 5 invalid problems,
   25 valid plan files and 25 invalid plan files, 62 files, 1,240 in total
   (`domains/README.md:38-47`; loader globs at `pddl_eval/domains.py:58-75`). Measured:
   20 / 20 / 100 / 100 / 500 / 500.
3. Trials per arm for the three wordings: solve 300, validate_domain 360, validate_problem 600,
   validate_plan 3,000, simulate 300, 4,560 in total (job builder `pddl_eval/runner.py:700-824`).
4. Valid to invalid balance per task: validate_domain 100 valid to 20 invalid trials per
   wording (one valid job per problem, `runner.py:735-743`; one invalid per domain,
   `runner.py:762-784`); validate_problem 100 to 100 (`runner.py:785-800`); validate_plan
   500 to 500 (`runner.py:718-734`, `:801-823`).

### 4.2 How the invalid files were made

5. Every invalid file was accepted only if the validator tool itself rejected it
   (`tools/build_fixtures.py:475`, `:539`, `:591`), and the harness re-checks this at every
   start and aborts otherwise (`pddl_eval/domains.py:216`, `:266`, `:284`, `:311`). So the
   answer key for the invalid cases is, by construction, the tool under test.
6. Invalid domains: the generator tries three text edits in a fixed order and keeps the first
   one the validator rejects: extra closing parenthesis, an undeclared predicate inserted in
   an effect, the `:predicates` block removed (`build_fixtures.py:581-594`; edits at
   `tools/_taxonomies.py:256-292`). The ten domains from the 2025 dataset kept their original
   hand-made invalid file instead (`build_fixtures.py:203`).
7. Invalid problems: all five per domain are edits of that domain's `p01.pddl`
   (`build_fixtures.py:525`). Six edits are tried in order, up to four attempts each: goal
   removed, undeclared object added to `:init`, undefined predicate in the goal, extra closing
   parenthesis, `:objects` removed, `:init` removed (`build_fixtures.py:505-512`, `:530-542`;
   edits at `_taxonomies.py:122-247`), with "goal removed plus extra parenthesis" as a filler
   (`build_fixtures.py:546`). For the ten 2025-dataset domains `n01.pddl` is the original
   hand-made file (`build_fixtures.py:205-208`).
8. Invalid plans: all five per problem are edits of that problem's first valid plan
   (`build_fixtures.py:454`). Four edits are tried in order, up to four attempts each: drop
   the last step, drop a middle step, swap the first two arguments of one step, repeat one
   step (`build_fixtures.py:426-431`, `:466-478`; edits at `_taxonomies.py:28-116`), then
   longer tail cuts as filler (`build_fixtures.py:479-489`). Action names and argument counts
   stay legal; the error is in meaning only (`build_fixtures.py:421-424`). For the 2025-dataset
   domains `p01_b1.plan` is the original hand-made file (`build_fixtures.py:218-221`).
9. Valid plans: the planner's plan, plus up to three other Fast Downward search settings for
   classical domains, then padded with copies of the first plan (`build_fixtures.py:327-331`,
   `:375-399`). Measured: the five valid plan files are byte-identical for 99 of 100 problems
   (49 of 50 classical, 50 of 50 numeric); there are 101 distinct valid plans among 500 files.
   All 500 invalid plan files are distinct.
10. validate_domain sends the valid domain once per problem, but the prompt contains only
    the domain text (`prompts.py:374-379`), so each wording sends the same prompt five times
    per domain: 60 distinct valid prompts in 300 valid trials.

### 4.3 What the invalid files contain, sizes, and bins (measured)

#### 1. Inventory

| item | count |
|---|---|
| domains | 20 |
| valid domain files | 20 |
| invalid domain files | 20 |
| valid problems | 100 |
| invalid problems | 100 |
| valid plan files | 500 |
| invalid plan files | 500 |

#### 2. What the invalid fixtures contain (structural classification against the source file)

Invalid domains (1 per domain, 20 total):

| error type | files |
|---|---|
| one extra closing paren | 9 |
| undeclared predicate used in a precondition or effect (inherited) | 5 |
| missing closing paren(s) | 3 |
| '-' dropped from a typed parameter list (inherited) | 2 |
| :predicates block removed (generator) | 1 |

Invalid problems (5 per domain, 100 total; every one is a mutation of that domain's p01.pddl):

| error type | files | classical | numeric |
|---|---|---|---|
| undeclared object in :init | 20 | 10 | 10 |
| undefined predicate in :goal | 20 | 10 | 10 |
| one extra closing paren | 18 | 9 | 9 |
| missing :goal | 13 | 6 | 7 |
| missing :goal + one extra closing paren | 13 | 8 | 5 |
| inherited hand-made n01 (see list) | 7 | 4 | 3 |
| :objects block removed | 7 | 2 | 5 |
| :init block removed | 2 | 1 | 1 |

Invalid plans (5 per problem, 500 total; every one is a mutation of that problem's v1 plan):

| error type | files |
|---|---|
| one mid-plan step dropped | 290 |
| tail truncated (-1) | 90 |
| first two arguments swapped in one step | 74 |
| one step duplicated | 17 |
| inherited hand-made b1 plan (shortened and/or altered) | 9 |
| tail truncated (-2) | 8 |
| tail truncated (-3) | 4 |
| tail truncated (-4) | 4 |
| tail truncated (-5) | 3 |
| tail truncated (-10) | 1 |

Same, tail truncations merged, by track:

| error type | classical | numeric |
|---|---|---|
| first two arguments swapped in one step | 41 | 33 |
| inherited hand-made b1 plan (shortened and/or altered) | 5 | 4 |
| one mid-plan step dropped | 156 | 134 |
| one step duplicated | 3 | 14 |
| tail truncated | 45 | 65 |

#### 3. Sizes

| quantity | classical (10 domains, 50 problems) | numeric (10 domains, 50 problems) | all |
|---|---|---|---|
| declared objects per valid problem | min 3 / q1 7.25 / median 11.5 / q3 16.75 / max 24 (mean 11.9, n=50) | min 2 / q1 3 / median 5 / q3 15 / max 35 (mean 10.4, n=50) | min 2 / q1 5 / median 9 / q3 16 / max 35 (mean 11.2, n=100) |
| reference plan length, steps (v1 plan) | min 2 / q1 6 / median 10 / q3 15.75 / max 65 (mean 14.5, n=50) | min 3 / q1 7 / median 14.5 / q3 32.5 / max 110 (mean 24.3, n=50) | min 2 / q1 6 / median 11.5 / q3 25.5 / max 110 (mean 19.4, n=100) |
| domain file size, characters | min 984 / q1 1253.25 / median 1648 / q3 2172.25 / max 5542 (mean 2160.8, n=10) | min 686 / q1 1618.25 / median 2002 / q3 2579.5 / max 3779 (mean 2130.4, n=10) | min 686 / q1 1447.75 / median 1812 / q3 2384.5 / max 5542 (mean 2145.6, n=20) |
| actions per domain | min 3 / q1 4 / median 4.5 / q3 5 / max 12 (mean 5.5, n=10) | min 2 / q1 4.25 / median 5 / q3 7.75 / max 10 (mean 5.8, n=10) | min 2 / q1 4 / median 5 / q3 7.25 / max 12 (mean 5.7, n=20) |
| distinct files among the 5 valid plans of a problem | {1: 49, 2: 1} | {1: 50} |  |

Invalid plan length minus its v1 plan length (steps): -99: 1, -61: 1, -28: 1, -25: 1, -18: 1, -10: 2, -5: 3, -4: 4, -3: 6, -2: 8, -1: 380, +0: 75, +1: 17

| domain | track | domain chars | actions | objects (min-max over p01..p05) | plan length (min-max) |
|---|---|---|---|---|---|
| barman | classical | 5542 | 12 | 13-20 | 14-65 |
| blocksworld | classical | 1164 | 4 | 3-6 | 2-16 |
| depots | classical | 1521 | 5 | 9-24 | 5-22 |
| gripper | classical | 984 | 3 | 7-19 | 3-14 |
| miconic | classical | 1003 | 4 | 3-7 | 3-10 |
| parking | classical | 1852 | 4 | 6-10 | 3-7 |
| rovers | classical | 3967 | 9 | 11-19 | 12-34 |
| satellite | classical | 1717 | 5 | 9-21 | 6-15 |
| tpp | classical | 2279 | 4 | 8-18 | 13-36 |
| zenotravel | classical | 1579 | 5 | 12-18 | 4-10 |
| block-grouping | numeric | 1556 | 4 | 5-5 | 10-36 |
| counters | numeric | 1228 | 4 | 3-5 | 8-56 |
| delivery | numeric | 2185 | 5 | 13-22 | 14-46 |
| depot | numeric | 1819 | 5 | 9-21 | 5-62 |
| drone | numeric | 2701 | 8 | 2-18 | 5-110 |
| farmland | numeric | 686 | 2 | 4-15 | 3-19 |
| gardening | numeric | 3779 | 10 | 3-3 | 5-86 |
| pogo_stick | numeric | 3330 | 7 | 35-35 | 10-23 |
| sailing | numeric | 1805 | 8 | 3-3 | 4-100 |
| zenotravel-numeric | numeric | 2215 | 5 | 4-7 | 3-14 |

Prompt size in characters (system + user, wording v11, valid fixtures, built with `pddl_eval.runner.build_messages`):

| task | characters |
|---|---|
| solve | min 1510 / q1 2472.75 / median 3065 / q3 4418 / max 8052 (mean 3451.2, n=100) |
| validate_domain | min 1044 / q1 1805.75 / median 2170 / q3 2742.5 / max 5900 (mean 2503.6, n=100) |
| validate_problem | min 1531 / q1 2493.75 / median 3086 / q3 4439 / max 8073 (mean 3472.2, n=100) |
| validate_plan | min 1678 / q1 2651.25 / median 3454.5 / q3 5158.25 / max 9810 (mean 4031.9, n=100) |
| simulate | min 1977 / q1 2950.25 / median 3753.5 / q3 5457.25 / max 10109 (mean 4330.9, n=100) |

#### 4. Difficulty-bin cut points (recomputed as rq_deck.py:493-512)

Rows = the three headline models, think off, arms no-tools and tools-steered (equal weight per instance x wording). Bins: low = value <= c1, mid = c1 < value <= c2, high = value > c2.

| bin variable | task | low bin | mid bin | high bin | rows per bin (both arms, 3 models) | value range |
|---|---|---|---|---|---|---|
| plan length | solve | <= 8 | 9 to 19 | > 19 | 648 / 558 / 594 | 2 to 110 |
| plan length | validate_plan | <= 8 | 9 to 19 | > 19 | 3240 / 2790 / 2970 | 2 to 110 |
| plan length | simulate | <= 8 | 9 to 19 | > 19 | 648 / 558 / 594 | 2 to 110 |
| object count | solve | <= 6 | 7 to 14 | > 14 | 702 / 522 / 576 | 2 to 35 |
| object count | validate_plan | <= 6 | 7 to 14 | > 14 | 3510 / 2610 / 2880 | 2 to 35 |
| object count | validate_problem | <= 5 | 6 to 13 | > 13 | 1152 / 1206 / 1080 | 2 to 35 |
| object count | simulate | <= 6 | 7 to 14 | > 14 | 702 / 522 / 576 | 2 to 35 |

Notes on the tables above:

- The seven "inherited hand-made n01" files are: an undeclared object (blocksworld, satellite,
  pogo_stick), an undeclared predicate (depots, depot), and unbalanced parentheses (rovers,
  farmland).
- The nine "inherited hand-made b1" plans are much shorter rewrites of the valid plan (for
  example 1 step instead of 100 in sailing, 2 instead of 30 in barman).
- Bins: the three length bins and the three object-count bins are thirds of the trial rows,
  cut at the floored 1/3 and 2/3 quantiles (`.claude/skills/analyzer/scripts/rq_deck.py:508-512`).
  "Length" is the shortest valid plan of the problem for solve and simulate, and the length
  of the plan under test for validate_plan, valid plans only (`rq_deck.py:482-490`, `:500`;
  `gen_meta.py:107-125`). "Object count" is the number of names in the problem's `:objects`
  block (`gen_meta.py:66-96`); invalid problems that lack `:objects` or `:init` are left out.
  So short / medium / long means at most 8, 9 to 19, and more than 19 steps; the object bins
  are at most 6, 7 to 14, more than 14 (at most 5, 6 to 13, more than 13 for validate_problem).

### 4.4 What the model sees in a trial

11. Tools: every with-tools trial exposes all tools of the two plugins, seven in total:
    `classic_planner`, `numeric_planner`, `save_plan`, `validate_domain`, `validate_problem`,
    `validate_plan`, `get_state_transition`. The harness never filters
    (`runner.py:366` `allowed = None`; `chat.py:269-270`; `run_experiment.py:122`, `:167`; tool
    definitions at `../pddl-copilot/plugins/pddl-solver/server/solver_server.py:407-487` and
    `../pddl-copilot/plugins/pddl-validator/server/validator_server.py:233-341`). The frontier
    runner passes the same list (`tools/frontier_runner.py:91-111`). Wrong-tool calls do occur,
    for example Qwen3.6 35B on solve trials (both tool arms, 600 trials) calls `validate_plan`
    217 times and `save_plan` 21 times.
12. One schema detail is hidden: the `verbose` parameter of the four validator tools is
    removed from the schema and pinned to false (`chat.py:86-91`, `:155-156`).
13. Prompt content: the full PDDL text of the domain, the problem, and for validate_plan and
    simulate the plan, is pasted into the user message (`runner.py:303-305`; templates
    `prompts.py:363-403`). No file path is given. Measured prompt sizes are in the table above
    (median about 2,200 to 3,800 characters, maximum about 10,100).
14. Tool-call arguments: the model has to pass the PDDL text itself. The tools accept either
    text or a path (`validator_server.py:111-123`). In the canonical tool cells of the three
    headline models, every call that has a `domain` argument passes inline PDDL text
    (27,185 calls; 80 calls have no `domain` argument).
15. The plan shown for simulate is the planner's own plan, the one whose trace is the answer
    key (`runner.py:303`, `domains.py:97-109`, `:190-196`).
16. Unaided arm: one turn, with a JSON-schema output constraint requested for every task
    (`runner.py:409-418`; `schemas.py:74-80`; sent as `guided_json`, `vllm_client.py:163-164`).
    The tool arm has no such constraint (`chat.py:287-293`). Whether the server enforced the
    constraint is a separate audit (`tools/guided_json_audit.py`) and was not re-checked here.
17. Budgets: output cap 8,192 tokens for solve and 6,144 for the other tasks
    (`runner.py:98-104`), context 16,384 (`runner.py:105`), temperature 0 (`chat.py:28`), at
    most 10 tool rounds (`chat.py:29`). Tool results are fed back in full each round
    (`chat.py:318`).
18. Stored answers: this corpus kept only the first 500 characters of each final answer,
    which is what produces the censored rows (`runner.py:145-153`; `tools/e2e_regrade.py:132`).

---

## 5. Cost with a realistic price ratio (C16)

### 5.1 Existing code and fields

- Tokens are stored per trial in `trials.jsonl` as `tokens.prompt` (input) and
  `tokens.completion` (output), summed over all turns of the tool loop
  (`pddl_eval/chat.py:277-299`). `tools/backfill_token_stats.py` only copies these sums into
  the summary files. Frontier tool trials also store `cache_write` and `cache_read`.
- The paper's cost-of-pass is (input + output tokens) divided by successes, the two token
  kinds added 1:1 (`paper/figures/make_paper_figures.py:470-482`, multiplier at `:509-517`).
- The frontier token count adds cache-write and cache-read tokens to input, unweighted
  (`reference/job2_delivered_reframe_worknote.md` section 8.3).
- List prices in the repo: `tools/frontier_runner.py:71-74` (also
  `tools/frontier_ab_compare.py:30-33`, `tools/claude_api_batch.py:103-106`): Sonnet 4.6 $3
  input and $15 output per million tokens, Haiku 4.5 $1 and $5. Cache write is billed at 1.25
  times input and cache read at 0.10 times input (`frontier_runner.py:70`, `:522-523`). The
  unaided frontier arm ran on the Batch API at half price (`claude_api_batch.py:101-108`).
- The open models are self-hosted and have no list price, so they are shown at output:input
  ratios of 1, 3, 4 and 5.

### 5.2 Method

cost = input tokens + r times output tokens, where r is the output:input price ratio.
Cost-of-pass = cost divided by successes. Multiplier = tools divided by no-tools; below 1
the tool is cheaper per success. "Input only" and "output only" are the two extremes
(r = 0 and r very large); every real ratio lies between them. On the delivered score the
multiplier is a range wherever a success count is a bound, built the same way as in the
paper (tool arm at its best against the unaided arm at its worst, and the reverse).

### 5.3 Open models (canonical, reasoning off)

#### A0. Token mix per trial (pooled over the three models)

| task | arm | n | input tok/trial | output tok/trial | input:output | turns/trial |
|---|---|---|---|---|---|---|
| solve | no-tools | 900 | 1,185 | 3,303 | 0.36:1 | 1.00 |
| solve | tools-plain | 900 | 15,890 | 2,816 | 5.64:1 | 2.69 |
| solve | tools-steered | 900 | 15,651 | 2,457 | 6.37:1 | 2.68 |
| validate_domain | no-tools | 1080 | 803 | 1,176 | 0.68:1 | 1.00 |
| validate_domain | tools-plain | 1080 | 8,980 | 792 | 11.34:1 | 2.02 |
| validate_domain | tools-steered | 1080 | 8,930 | 757 | 11.79:1 | 2.01 |
| validate_problem | no-tools | 1800 | 1,160 | 871 | 1.33:1 | 1.00 |
| validate_problem | tools-plain | 1800 | 10,847 | 1,351 | 8.03:1 | 2.12 |
| validate_problem | tools-steered | 1800 | 10,669 | 1,268 | 8.42:1 | 2.10 |
| validate_plan | no-tools | 9000 | 1,371 | 1,636 | 0.84:1 | 1.00 |
| validate_plan | tools-plain | 9000 | 9,677 | 1,419 | 6.82:1 | 1.74 |
| validate_plan | tools-steered | 9000 | 11,671 | 1,425 | 8.19:1 | 2.04 |
| simulate | no-tools | 900 | 1,454 | 3,035 | 0.48:1 | 1.00 |
| simulate | tools-plain | 900 | 14,495 | 2,017 | 7.18:1 | 2.05 |
| simulate | tools-steered | 900 | 16,093 | 1,819 | 8.85:1 | 2.21 |

#### A. tools-steered / no-tools (the paper's pairing): multiplier on the DELIVERED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| pooled 3 models | solve | 2.12x to 5.38x | 0.12x to 0.30x | 0.65x to 1.64x | 0.33x to 0.84x | 0.28x to 0.72x | 0.25x to 0.64x |
| pooled 3 models | validate_domain | 6.39x to 6.61x | 0.37x to 0.38x | 2.81x to 2.91x | 1.48x to 1.54x | 1.25x to 1.29x | 1.09x to 1.13x |
| pooled 3 models | validate_problem | 6.91x to 7.61x | 1.09x to 1.20x | 4.41x to 4.86x | 2.88x to 3.17x | 2.54x to 2.80x | 2.32x to 2.55x |
| pooled 3 models | validate_plan | 8.03x to 10.08x | 0.82x to 1.03x | 4.11x to 5.16x | 2.40x to 3.01x | 2.07x to 2.60x | 1.86x to 2.33x |
| pooled 3 models | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Gemma 26B a4b | solve | 1.42x to 3.56x | 0.10x to 0.24x | 0.51x to 1.29x | 0.27x to 0.68x | 0.23x to 0.59x | 0.21x to 0.52x |
| Gemma 26B a4b | validate_domain | 7.92x to 8.23x | 1.01x to 1.05x | 4.93x to 5.12x | 3.11x to 3.23x | 2.72x to 2.82x | 2.45x to 2.54x |
| Gemma 26B a4b | validate_problem | 6.10x to 6.66x | 1.25x to 1.37x | 4.28x to 4.67x | 2.99x to 3.26x | 2.68x to 2.92x | 2.47x to 2.69x |
| Gemma 26B a4b | validate_plan | 6.72x to 11.52x | 1.15x to 1.98x | 4.23x to 7.25x | 2.78x to 4.76x | 2.47x to 4.23x | 2.26x to 3.87x |
| Gemma 26B a4b | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.5 9B | solve | 2.38x to 5.62x | 0.10x to 0.23x | 0.64x to 1.52x | 0.31x to 0.74x | 0.26x to 0.62x | 0.23x to 0.55x |
| Qwen3.5 9B | validate_domain | 2.98x | 0.12x | 1.08x | 0.53x | 0.44x | 0.38x |
| Qwen3.5 9B | validate_problem | 7.38x to 7.66x | 1.09x to 1.13x | 4.55x to 4.72x | 2.91x to 3.02x | 2.56x to 2.66x | 2.32x to 2.41x |
| Qwen3.5 9B | validate_plan | 8.14x to 8.33x | 0.71x to 0.73x | 3.93x to 4.02x | 2.22x to 2.27x | 1.91x to 1.95x | 1.70x to 1.74x |
| Qwen3.5 9B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.6 35B | solve | 2.77x to 7.93x | 0.17x to 0.50x | 0.82x to 2.35x | 0.43x to 1.24x | 0.37x to 1.07x | 0.34x to 0.96x |
| Qwen3.6 35B | validate_domain | 7.97x to 8.51x | 0.38x to 0.41x | 3.22x to 3.45x | 1.65x to 1.76x | 1.37x to 1.47x | 1.20x to 1.28x |
| Qwen3.6 35B | validate_problem | 7.22x to 8.52x | 0.97x to 1.14x | 4.37x to 5.15x | 2.75x to 3.24x | 2.40x to 2.84x | 2.17x to 2.56x |
| Qwen3.6 35B | validate_plan | 9.32x to 11.06x | 0.73x to 0.86x | 4.20x to 4.98x | 2.31x to 2.74x | 1.97x to 2.34x | 1.75x to 2.08x |
| Qwen3.6 35B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |

#### A. tools-steered / no-tools (the paper's pairing): multiplier on the TOOL-VERIFIED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| pooled 3 models | solve | 1.26x | 0.07x | 0.38x | 0.20x | 0.17x | 0.15x |
| pooled 3 models | validate_domain | 6.39x | 0.37x | 2.81x | 1.48x | 1.25x | 1.09x |
| pooled 3 models | validate_problem | 6.92x | 1.09x | 4.42x | 2.88x | 2.55x | 2.32x |
| pooled 3 models | validate_plan | 7.64x | 0.78x | 3.91x | 2.28x | 1.97x | 1.77x |
| pooled 3 models | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Gemma 26B a4b | solve | 0.85x | 0.06x | 0.31x | 0.16x | 0.14x | 0.13x |
| Gemma 26B a4b | validate_domain | 7.92x | 1.01x | 4.93x | 3.11x | 2.72x | 2.45x |
| Gemma 26B a4b | validate_problem | 6.10x | 1.25x | 4.28x | 2.99x | 2.68x | 2.47x |
| Gemma 26B a4b | validate_plan | 6.91x | 1.19x | 4.35x | 2.85x | 2.53x | 2.32x |
| Gemma 26B a4b | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.5 9B | solve | 1.56x | 0.06x | 0.42x | 0.20x | 0.17x | 0.15x |
| Qwen3.5 9B | validate_domain | 2.98x | 0.12x | 1.08x | 0.53x | 0.44x | 0.38x |
| Qwen3.5 9B | validate_problem | 7.45x | 1.10x | 4.59x | 2.94x | 2.58x | 2.35x |
| Qwen3.5 9B | validate_plan | 7.54x | 0.66x | 3.64x | 2.06x | 1.76x | 1.57x |
| Qwen3.5 9B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |
| Qwen3.6 35B | solve | 1.44x | 0.09x | 0.43x | 0.22x | 0.19x | 0.17x |
| Qwen3.6 35B | validate_domain | 7.97x | 0.38x | 3.22x | 1.65x | 1.37x | 1.20x |
| Qwen3.6 35B | validate_problem | 7.19x | 0.96x | 4.35x | 2.74x | 2.39x | 2.16x |
| Qwen3.6 35B | validate_plan | 8.45x | 0.66x | 3.81x | 2.10x | 1.79x | 1.59x |
| Qwen3.6 35B | simulate | not identified | not identified | not identified | not identified | not identified | not identified |

#### A. Break-even output:input price ratio (the tool is cheaper per success above it)

Delivered, best case = every censored tool-arm row counted as a success; delivered, worst case = none counted (the tool pays for certain only above the worst-case ratio).

| tool arm | cell | task | delivered, best case | delivered, worst case | tool-verified |
|---|---|---|---|---|---|
| tools-steered | pooled 3 models | solve | 0.5:1 | 2.2:1 | 0.1:1 |
| tools-steered | pooled 3 models | validate_domain | 5.8:1 | 6.2:1 | 5.8:1 |
| tools-steered | pooled 3 models | validate_problem | never | never | never |
| tools-steered | pooled 3 models | validate_plan | 33.0:1 | never | 25.5:1 |
| tools-steered | pooled 3 models | simulate | not identified | not identified | not identified |
| tools-steered | Gemma 26B a4b | solve | 0.2:1 | 1.6:1 | any (cheaper on input alone) |
| tools-steered | Gemma 26B a4b | validate_domain | never | never | never |
| tools-steered | Gemma 26B a4b | validate_problem | never | never | never |
| tools-steered | Gemma 26B a4b | validate_plan | never | never | never |
| tools-steered | Gemma 26B a4b | simulate | not identified | not identified | not identified |
| tools-steered | Qwen3.5 9B | solve | 0.5:1 | 1.9:1 | 0.2:1 |
| tools-steered | Qwen3.5 9B | validate_domain | 1.1:1 | 1.1:1 | 1.1:1 |
| tools-steered | Qwen3.5 9B | validate_problem | never | never | never |
| tools-steered | Qwen3.5 9B | validate_plan | 19.0:1 | 20.7:1 | 14.7:1 |
| tools-steered | Qwen3.5 9B | simulate | not identified | not identified | not identified |
| tools-steered | Qwen3.6 35B | solve | 0.7:1 | 4.6:1 | 0.2:1 |
| tools-steered | Qwen3.6 35B | validate_domain | 6.8:1 | 7.6:1 | 6.8:1 |
| tools-steered | Qwen3.6 35B | validate_problem | 226.8:1 | never | 205.1:1 |
| tools-steered | Qwen3.6 35B | validate_plan | 20.8:1 | 50.3:1 | 14.9:1 |
| tools-steered | Qwen3.6 35B | simulate | not identified | not identified | not identified |
| tools-plain | pooled 3 models | solve | 0.6:1 | 3.9:1 | 0.2:1 |
| tools-plain | pooled 3 models | validate_domain | 6.1:1 | 6.5:1 | 6.1:1 |
| tools-plain | pooled 3 models | validate_problem | never | never | never |
| tools-plain | pooled 3 models | validate_plan | 24.5:1 | never | never |
| tools-plain | pooled 3 models | simulate | not identified | not identified | not identified |
| tools-plain | Gemma 26B a4b | solve | 1.0:1 | 5.1:1 | any (cheaper on input alone) |
| tools-plain | Gemma 26B a4b | validate_domain | never | never | never |
| tools-plain | Gemma 26B a4b | validate_problem | never | never | never |
| tools-plain | Gemma 26B a4b | validate_plan | 55.1:1 | never | never |
| tools-plain | Gemma 26B a4b | simulate | not identified | not identified | not identified |
| tools-plain | Qwen3.5 9B | solve | 0.7:1 | 2.3:1 | 0.2:1 |
| tools-plain | Qwen3.5 9B | validate_domain | 1.1:1 | 1.1:1 | 1.1:1 |
| tools-plain | Qwen3.5 9B | validate_problem | 456.2:1 | never | 511.1:1 |
| tools-plain | Qwen3.5 9B | validate_plan | 23.8:1 | 34.9:1 | 18.3:1 |
| tools-plain | Qwen3.5 9B | simulate | not identified | not identified | not identified |
| tools-plain | Qwen3.6 35B | solve | 0.4:1 | 11.0:1 | 0.3:1 |
| tools-plain | Qwen3.6 35B | validate_domain | 7.6:1 | 8.9:1 | 7.7:1 |
| tools-plain | Qwen3.6 35B | validate_problem | never | never | never |
| tools-plain | Qwen3.6 35B | validate_plan | 23.2:1 | never | 40.4:1 |
| tools-plain | Qwen3.6 35B | simulate | not identified | not identified | not identified |

#### A. solve by track, pooled 3 models: multiplier on the DELIVERED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| tools-steered, classical | solve | 1.19x to 3.16x | 0.06x to 0.17x | 0.34x to 0.90x | 0.17x to 0.46x | 0.15x to 0.39x | 0.13x to 0.35x |
| tools-steered, numeric | solve | 3.74x to 8.81x | 0.23x to 0.53x | 1.24x to 2.92x | 0.65x to 1.52x | 0.55x to 1.29x | 0.49x to 1.15x |
| tools-plain, classical | solve | 1.35x to 3.88x | 0.09x to 0.25x | 0.39x to 1.13x | 0.21x to 0.60x | 0.18x to 0.52x | 0.16x to 0.47x |
| tools-plain, numeric | solve | 4.70x to 12.49x | 0.31x to 0.82x | 1.58x to 4.19x | 0.83x to 2.21x | 0.71x to 1.90x | 0.64x to 1.70x |

#### A. solve by track, pooled 3 models: multiplier on the TOOL-VERIFIED score

| cell | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| tools-steered, classical | solve | 0.86x | 0.05x | 0.24x | 0.13x | 0.11x | 0.10x |
| tools-steered, numeric | solve | 1.71x | 0.10x | 0.57x | 0.30x | 0.25x | 0.22x |
| tools-plain, classical | solve | 0.99x | 0.06x | 0.29x | 0.15x | 0.13x | 0.12x |
| tools-plain, numeric | solve | 1.90x | 0.12x | 0.64x | 0.34x | 0.29x | 0.26x |

The tools-plain against no-tools tables are in
`tools/reanalysis/out/breakdowns_cost/cost_price_ratio.md`.

### 5.4 Frontier (canonical, wording v11 on both arms)

Three ways to count the tool arm's input, all from the same stored fields: *raw* (the
paper's count), *cache-billed* (cache tokens weighted as they are billed), and *as-billed*
(cache-billed, with the unaided arm at the Batch price it was actually run at).

#### B0. Token mix per trial

| tier | task | tools input raw | tools output | tools input:output | tools input cache-billed | no-tools input | no-tools output | no-tools input:output |
|---|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 15,503 | 2,200 | 7.0:1 | 10,187 | 1,457 | 290 | 5.03:1 |
| Sonnet 4.6 | validate_domain | 11,022 | 1,103 | 10.0:1 | 3,478 | 861 | 318 | 2.70:1 |
| Sonnet 4.6 | validate_problem | 12,205 | 1,452 | 8.4:1 | 9,004 | 1,266 | 170 | 7.45:1 |
| Sonnet 4.6 | validate_plan | 14,118 | 1,742 | 8.1:1 | 7,304 | 1,528 | 852 | 1.79:1 |
| Sonnet 4.6 | simulate | 46,439 | 5,355 | 8.7:1 | 51,094 | 1,680 | 3,522 | 0.48:1 |
| Haiku 4.5 | solve | 40,775 | 5,320 | 7.7:1 | 18,973 | 1,456 | 304 | 4.79:1 |
| Haiku 4.5 | validate_domain | 11,133 | 930 | 12.0:1 | 4,367 | 860 | 483 | 1.78:1 |
| Haiku 4.5 | validate_problem | 12,438 | 1,356 | 9.2:1 | 9,104 | 1,265 | 589 | 2.15:1 |
| Haiku 4.5 | validate_plan | 14,616 | 1,766 | 8.3:1 | 7,495 | 1,527 | 1,101 | 1.39:1 |
| Haiku 4.5 | simulate | 42,238 | 4,417 | 9.6:1 | 45,183 | 1,679 | 3,575 | 0.47:1 |

#### B. raw: multiplier on the DELIVERED score

raw token count (the paper's accounting); at 5:1 this is list price with caching ignored.

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 3.25x | 2.32x | 3.09x | 2.90x | 2.84x | 2.78x |
| Sonnet 4.6 | validate_domain | 12.47x | 3.37x | 10.01x | 7.69x | 7.04x | 6.57x |
| Sonnet 4.6 | validate_problem | 8.51x | 7.55x | 8.40x | 8.23x | 8.17x | 8.12x |
| Sonnet 4.6 | validate_plan | 8.97x | 1.98x | 6.47x | 4.60x | 4.15x | 3.83x |
| Sonnet 4.6 | simulate | 15.16x to 29.89x | 0.83x to 1.64x | 5.46x to 10.77x | 2.80x to 5.52x | 2.36x to 4.65x | 2.08x to 4.11x |
| Haiku 4.5 | solve | 6.49x | 4.06x | 6.07x | 5.55x | 5.38x | 5.25x |
| Haiku 4.5 | validate_domain | 11.52x | 1.71x | 7.99x | 5.37x | 4.73x | 4.29x |
| Haiku 4.5 | validate_problem | 7.44x | 1.74x | 5.63x | 4.12x | 3.73x | 3.45x |
| Haiku 4.5 | validate_plan | 8.87x | 1.49x | 5.77x | 3.82x | 3.39x | 3.09x |
| Haiku 4.5 | simulate | 14.93x to 32.89x | 0.73x to 1.62x | 5.27x to 11.61x | 2.66x to 5.85x | 2.23x to 4.90x | 1.95x to 4.30x |

#### B. raw: multiplier on the TOOL-VERIFIED score

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 3.09x | 2.20x | 2.94x | 2.76x | 2.69x | 2.65x |
| Sonnet 4.6 | validate_domain | 12.47x | 3.37x | 10.01x | 7.69x | 7.04x | 6.57x |
| Sonnet 4.6 | validate_problem | 8.51x | 7.55x | 8.40x | 8.23x | 8.17x | 8.12x |
| Sonnet 4.6 | validate_plan | 8.98x | 1.99x | 6.48x | 4.60x | 4.15x | 3.83x |
| Sonnet 4.6 | simulate | 10.33x | 0.57x | 3.72x | 1.91x | 1.61x | 1.42x |
| Haiku 4.5 | solve | 6.16x | 3.85x | 5.76x | 5.27x | 5.11x | 4.98x |
| Haiku 4.5 | validate_domain | 11.52x | 1.71x | 7.99x | 5.37x | 4.73x | 4.29x |
| Haiku 4.5 | validate_problem | 7.44x | 1.74x | 5.63x | 4.12x | 3.73x | 3.45x |
| Haiku 4.5 | validate_plan | 8.86x | 1.48x | 5.77x | 3.81x | 3.38x | 3.08x |
| Haiku 4.5 | simulate | 10.89x | 0.53x | 3.84x | 1.94x | 1.62x | 1.42x |

#### B. cache-billed: multiplier on the DELIVERED score

tools input priced with the cache multipliers; at 5:1 this is the actual list price, both arms at list.

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 2.13x | 2.32x | 2.17x | 2.20x | 2.22x | 2.23x |
| Sonnet 4.6 | validate_domain | 3.93x | 3.37x | 3.78x | 3.64x | 3.60x | 3.57x |
| Sonnet 4.6 | validate_problem | 6.28x | 7.55x | 6.43x | 6.64x | 6.72x | 6.79x |
| Sonnet 4.6 | validate_plan | 4.64x | 1.98x | 3.69x | 2.98x | 2.81x | 2.69x |
| Sonnet 4.6 | simulate | 16.67x to 32.89x | 0.83x to 1.64x | 5.95x to 11.74x | 3.01x to 5.93x | 2.52x to 4.97x | 2.21x to 4.37x |
| Haiku 4.5 | solve | 3.02x | 4.06x | 3.20x | 3.42x | 3.49x | 3.55x |
| Haiku 4.5 | validate_domain | 4.52x | 1.71x | 3.51x | 2.76x | 2.58x | 2.45x |
| Haiku 4.5 | validate_problem | 5.45x | 1.74x | 4.27x | 3.29x | 3.04x | 2.86x |
| Haiku 4.5 | validate_plan | 4.55x | 1.49x | 3.26x | 2.45x | 2.27x | 2.15x |
| Haiku 4.5 | simulate | 15.97x to 35.18x | 0.73x to 1.62x | 5.60x to 12.34x | 2.80x to 6.16x | 2.34x to 5.14x | 2.04x to 4.50x |

#### B. cache-billed: multiplier on the TOOL-VERIFIED score

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 2.03x | 2.20x | 2.06x | 2.09x | 2.11x | 2.11x |
| Sonnet 4.6 | validate_domain | 3.93x | 3.37x | 3.78x | 3.64x | 3.60x | 3.57x |
| Sonnet 4.6 | validate_problem | 6.28x | 7.55x | 6.43x | 6.64x | 6.72x | 6.79x |
| Sonnet 4.6 | validate_plan | 4.65x | 1.99x | 3.69x | 2.98x | 2.81x | 2.69x |
| Sonnet 4.6 | simulate | 11.36x | 0.57x | 4.06x | 2.05x | 1.72x | 1.51x |
| Haiku 4.5 | solve | 2.87x | 3.85x | 3.04x | 3.25x | 3.32x | 3.37x |
| Haiku 4.5 | validate_domain | 4.52x | 1.71x | 3.51x | 2.76x | 2.58x | 2.45x |
| Haiku 4.5 | validate_problem | 5.45x | 1.74x | 4.27x | 3.29x | 3.04x | 2.86x |
| Haiku 4.5 | validate_plan | 4.54x | 1.48x | 3.26x | 2.45x | 2.27x | 2.15x |
| Haiku 4.5 | simulate | 11.65x | 0.53x | 4.09x | 2.04x | 1.70x | 1.49x |

#### B. as-billed: multiplier on the DELIVERED score

as cache-billed, and the no-tools arm at the Batch API price (half list); at 5:1 this is what the two arms were actually charged.

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 4.27x | 4.64x | 4.33x | 4.41x | 4.43x | 4.45x |
| Sonnet 4.6 | validate_domain | 7.87x | 6.75x | 7.57x | 7.28x | 7.20x | 7.14x |
| Sonnet 4.6 | validate_problem | 12.56x | 15.09x | 12.86x | 13.29x | 13.44x | 13.58x |
| Sonnet 4.6 | validate_plan | 9.28x | 3.97x | 7.38x | 5.96x | 5.61x | 5.37x |
| Sonnet 4.6 | simulate | 33.35x to 65.78x | 1.67x to 3.29x | 11.90x to 23.47x | 6.01x to 11.86x | 5.04x to 9.95x | 4.43x to 8.73x |
| Haiku 4.5 | solve | 6.04x | 8.11x | 6.40x | 6.84x | 6.98x | 7.10x |
| Haiku 4.5 | validate_domain | 9.04x | 3.42x | 7.02x | 5.52x | 5.15x | 4.90x |
| Haiku 4.5 | validate_problem | 10.89x | 3.49x | 8.54x | 6.58x | 6.07x | 5.71x |
| Haiku 4.5 | validate_plan | 9.09x | 2.97x | 6.53x | 4.91x | 4.55x | 4.30x |
| Haiku 4.5 | simulate | 31.95x to 70.37x | 1.47x to 3.23x | 11.21x to 24.69x | 5.59x to 12.32x | 4.67x to 10.29x | 4.08x to 9.00x |

#### B. as-billed: multiplier on the TOOL-VERIFIED score

| tier | task | input only | output only | 1:1 (paper) | 3:1 | 4:1 | 5:1 |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | solve | 4.06x | 4.40x | 4.11x | 4.19x | 4.21x | 4.23x |
| Sonnet 4.6 | validate_domain | 7.87x | 6.75x | 7.57x | 7.28x | 7.20x | 7.14x |
| Sonnet 4.6 | validate_problem | 12.56x | 15.09x | 12.86x | 13.29x | 13.44x | 13.58x |
| Sonnet 4.6 | validate_plan | 9.29x | 3.97x | 7.39x | 5.96x | 5.62x | 5.38x |
| Sonnet 4.6 | simulate | 22.73x | 1.14x | 8.11x | 4.10x | 3.44x | 3.02x |
| Haiku 4.5 | solve | 5.74x | 7.71x | 6.08x | 6.49x | 6.63x | 6.74x |
| Haiku 4.5 | validate_domain | 9.04x | 3.42x | 7.02x | 5.52x | 5.15x | 4.90x |
| Haiku 4.5 | validate_problem | 10.89x | 3.49x | 8.54x | 6.58x | 6.07x | 5.71x |
| Haiku 4.5 | validate_plan | 9.09x | 2.97x | 6.52x | 4.90x | 4.54x | 4.30x |
| Haiku 4.5 | simulate | 23.30x | 1.07x | 8.17x | 4.08x | 3.41x | 2.98x |

#### B. Break-even output:input price ratio, delivered score

| tier | task | raw, best case | raw, worst case | cache-billed, worst case |
|---|---|---|---|---|
| Sonnet 4.6 | solve | never | never | never |
| Sonnet 4.6 | validate_domain | never | never | never |
| Sonnet 4.6 | validate_problem | never | never | never |
| Sonnet 4.6 | validate_plan | never | never | never |
| Sonnet 4.6 | simulate | 40.6:1 | never | never |
| Haiku 4.5 | solve | never | never | never |
| Haiku 4.5 | validate_domain | never | never | never |
| Haiku 4.5 | validate_problem | never | never | never |
| Haiku 4.5 | validate_plan | never | never | never |
| Haiku 4.5 | simulate | 24.6:1 | never | never |

#### B. Dollars per delivered pass at list prices (tools/frontier_runner.py:71-74)

| tier | task | tools, list, caching ignored | tools, list, cache-billed | no-tools, list | no-tools, Batch (list / 2) |
|---|---|---|---|---|---|
| Sonnet 4.6 | solve | $0.084 | $0.067 | $0.030 | $0.015 |
| Sonnet 4.6 | validate_domain | $0.052 | $0.028 | $0.008 | $0.004 |
| Sonnet 4.6 | validate_problem | $0.060 | $0.050 | $0.007 | $0.004 |
| Sonnet 4.6 | validate_plan | $0.068 | $0.048 | $0.018 | $0.009 |
| Sonnet 4.6 | simulate | $0.354 to $0.448 | $0.377 to $0.477 | $0.109 to $0.170 | $0.055 to $0.085 |
| Haiku 4.5 | solve | $0.071 | $0.048 | $0.014 | $0.007 |
| Haiku 4.5 | validate_domain | $0.016 | $0.009 | $0.004 | $0.002 |
| Haiku 4.5 | validate_problem | $0.020 | $0.016 | $0.006 | $0.003 |
| Haiku 4.5 | validate_plan | $0.024 | $0.017 | $0.008 | $0.004 |
| Haiku 4.5 | simulate | $0.101 to $0.124 | $0.105 to $0.129 | $0.029 to $0.051 | $0.014 to $0.026 |

### 5.5 Reading

- The multiplier is not invariant. For the open models it falls by a factor of about 2.6
  between equal prices and 5:1 on solve, and by 1.9 to 2.6 on validation. For the frontier
  it moves little on solve (both arms are input-heavy there, because the unaided frontier
  answer is a short JSON plan of about 300 tokens) and a lot on simulate.
- Where the conclusion holds and where it does not is the table in the summary at the top.
- Latency was not attempted. Per-trial wall-clock time is not recoverable from these logs,
  and planner compute time is not logged.

---

## 6. Limits of this re-analysis

- Everything here is descriptive. No test was run and nothing is corrected for the number of
  cells looked at (45 cells times 3 wordings, times 20 domains).
- Wilson intervals treat trials as independent. They are not: the three wordings share
  instances, and two tasks contain repeated prompts (facts 9 and 10), so the intervals on
  validate_domain and validate_plan are narrower than the data justify.
- Per-domain cells for solve and simulate have n = 15.
- Delivered cells on the tool arms are bounds on this corpus. Per-wording and per-domain
  delivered bounds are often too wide to compare; the tool-verified column is the one that
  can be read cell by cell.
- `tool-verified` here is the stored grade, the same field the paper's CSV uses. The
  overlay also holds a corrected `tool_verified_fixed` for validation tasks; it was not used.
- The price ratios for the open models are illustrative. Server-side prefix caching, which
  would lower the tool arm's effective input cost, is not priced.
- The link between domain size and unprompted tool calls (section 2.2) is an observation
  on 20 domains.

---

## 7. Reproduce

From the repo root. All scripts are read-only over `results/` and `domains/` and need only
`numpy` (the fixture script) beyond the standard library.

```bash
# 0. gate: frozen figures reproduce (exit code 0, "ALL CHECKS PASS")
python3 tools/reanalysis/bc_reproduce_numbers.py

# 1. per-wording tables (C12) + frontier wording inventory
python3 tools/reanalysis/bc_per_wording.py
python3 tools/reanalysis/bc_per_wording.py --corpus sweep6-live

# 1.4 identical prompts, run-to-run agreement
python3 tools/reanalysis/bc_duplicate_prompts.py

# 2 + 3. per-domain, driver flags, classical vs numeric, solve cost by track (C21)
python3 tools/reanalysis/bc_per_domain.py
python3 tools/reanalysis/bc_per_domain.py --corpus sweep6-live

# 4. test-data facts (C11)
python3 tools/reanalysis/bc_fixture_facts.py

# 5. cost under price ratios (C16)
python3 tools/reanalysis/bc_cost_price_ratio.py
```

Outputs land in `tools/reanalysis/out/breakdowns_cost/` (`.md` for reading, `.csv` with the
counts and Wilson bounds behind every cell). The two small tables in sections 1.3 and 3.2
that are not written by a script (failure reason by wording, delivery outcome by track) are
plain counts of `failure_reason` in `trials.jsonl` and of `e2e_reason` in the overlay,
grouped by `prompt_variant` and by domain track.

`bc_common.py` is the shared loader. It joins `trials.jsonl` with the overlay on the trial
key and refuses to run if the two disagree. The files `common.py`, `01_reproduce_frozen.py`
and `planbench_equivalence_tost.py` in the same directory belong to the separate statistics
re-analysis (C9) and are not used here.
