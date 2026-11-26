# Token consumption with and without the tools

*2026-11-26. For Omer. Descriptive and post hoc: no registration covers any of this, and
nothing here is a test. All numbers come from one script,
`tools/reanalysis/token_consumption.py`, which writes the full tables to
`tools/reanalysis/out/token_consumption.md` (and `.json`) and the four figures in this
folder. Section numbers like "table 2" below point at that file.*

## In one paragraph

A trial with tools costs several times the tokens of a trial without, almost all of it
input: the prompt and the tool list are sent again with every request, the model copies
the PDDL into its tool calls, and on simulate the tool's long answer is read back in.
Per right answer the tools cost more tokens than the unaided model in nearly every cell,
and among our five models the premium is larger the better the model already does
alone. On simulate, two thirds of the open models' tool tokens go to trials that end with
a full window and no answer.

## Findings, ranked by what they mean for the three questions

1. **Per right answer, the tools cost more tokens than the unaided model, and among our
   five models the premium is larger where the model already does well alone (RQ1).**
   On solve, counting raw tokens, a right plan with tools (plain wording) costs 2.2 times
   the tokens of an unaided right plan for Qwen3.5-9B (unaided 41%), 3.1 for Gemma-26B
   (58%), 4.7 for Qwen3.6-35B (68%), and for the Claude models 5.9 (Haiku 5.5, 74%) and
   7.8 (Sonnet 5.5, 94%). On validate_domain the same order holds, from 1.08 [0.71, 1.68]
   for Qwen3.5-9B (unaided 26%) to 8.6 for Sonnet 5.5 (99.7%). Caveat: five models at one
   point in time, under two sets of conditions; this is an ordering across models, not a
   trend over time. It roughly holds on validate_problem (4.4 to 8.2) and breaks on
   validate_plan and simulate.
   **How to read the ordering (added by the session after checking the tables).** The
   cost per right answer is two things multiplied: how many times more tokens a tool
   trial uses, and the unaided rate divided by the rate with tools. On solve the first
   is nearly the same for the three open models (4.8, 5.0 and 5.4 times, table 2, last
   column) and for the two Claude models (7.6 and 8.0). So the tools do not get dearer
   to run as the model gets better. What changes is the second part: a model that is
   already right alone has fewer wrong answers left for the tool to turn around, so the
   same token overhead buys fewer extra right answers. As the unaided rate approaches
   the rate with tools, the cost per right answer has to approach the per-trial ratio;
   that part of Figure C is arithmetic, not a discovery.
   *Figure C, table 2.*

2. **What an extra token buys falls as the unaided rate rises (RQ1).** Points of right
   answers gained per 1,000 extra tokens per trial, solve: 2.5 (Qwen3.5-9B), 2.2
   (Gemma-26B), 0.5 (Qwen3.6-35B); Haiku 5.5 1.2, Sonnet 5.5 0.2. On validate_domain
   9.8 for Qwen3.5-9B against 0.02 for Sonnet 5.5. On simulate the figure is near zero or
   negative for every model. Caveat: this measure divides by tokens, and tokens of
   different tokenizers are not the same unit, so read it across models only as an
   ordering; the multiplier of finding 1 is unit-free and is the safer cross-model figure.
   *Table 6.*

3. **When output is priced above input, the picture changes for the weaker models only
   (RQ1).** Weighting output 5:1 (the ratio of both Claude list prices), the tool is
   cheaper or about even per right answer for Qwen3.5-9B on solve (0.78 [0.47, 1.24]
   plain, 0.73 steered), validate_domain (0.38 [0.25, 0.62]) and simulate (0.91 [0.42,
   1.67] plain), about even for Gemma-26B on solve (1.21 plain, 0.98 steered), and still
   dearer in every other cell (1.36 to 6.25). The reason
   is that the unaided open models spend their tokens writing (70 to 77% of an unaided
   solve trial is output), while a tool trial is about 90% input. Caveat: the open models
   have no list price; 5:1 is an illustration, not their cost. *Table 2.*

4. **On simulate, most of the open models' tool tokens are spent on trials that cannot
   end right (RQ3, and RQ1 on simulate).** In each open tool cell 142 to 168 of 300
   trials end with a full window; none of them is right, and they consume 62 to 67% of
   the cell's tokens. Each refused final request is stored as 16,384 input tokens that the
   server never ran. Leaving those refused requests out lowers the simulate multiplier
   (Gemma-26B plain 7.2 to 4.6; Qwen3.6-35B 4.2 to 2.7) but does not bring it below 1.
   *Figure D, tables 5 and 7.*

5. **Where a tool trial's input goes (RQ3).** Most of it is the first prompt (system
   message, the seven tool descriptions, the task) sent again with every request: 50 to
   94% of the input in the open tool arms. The model's own tool calls come next, because
   they copy the domain and problem text: about 19 to 27% of the input on solve for the
   open models (estimate), 10 to 12% for Claude (exact). The tool's own output is a small
   part except on simulate: 1 to 12% of the input on the other tasks (Haiku 5.5's
   validate_plan 21%), against 31 to 39%
   for the open models (estimate) and 70% for both Claude models (exact) on simulate.
   *Figure B, table 4.*

6. **A tool trial costs 2.6 to 6.4 times the tokens of an unaided trial for the open
   models and 7.6 to 10.3 times for Claude, and about 90% of it is input (RQ1).** The
   largest open-model ratio is on validate_domain and validate_problem (up to 6.4); the
   smallest is Gemma-26B on validate_plan with the plain wording (2.6), because it calls
   the tool in only 600 of 3,000 trials. The Claude ratios are larger partly because its
   unaided answers are short (745 to 985 output tokens on solve, against 2,909 to 4,029
   for the open models). *Figure A, table 1.*

7. **Unaided answers are long and often stop at the output cap; with tools the model
   writes less (RQ1, RQ3).** Unaided, the open models write 2,900 to 4,000 output tokens
   per solve trial and 3,900 to 4,500 per simulate trial, and 32 to 79 (solve) and 97 to
   145 (simulate) of 300 answers stop at the cap. With tools (plain) 0 to 14 do. Claude's
   final reply with tools is about 410 to 430 tokens on solve, against 745 to 985 unaided.
   Unaided, 45 to 72% of the open models' solve tokens go to answers that end wrong; with
   tools 17 to 26%. *Table 5.*

8. **The steering sentence also saves tokens where it raises calling (RQ2).** Naming the
   tool lowers the cost per right answer on solve for Qwen3.6-35B (4.7 to 4.2) and
   Gemma-26B (3.1 to 2.5). Gemma-26B's plain validate_plan cell looks cheap per trial (2.6
   times) only because it seldom calls; with the sentence it calls, its rate rises from
   89.2 to 96.6%, and its multiplier goes from 2.5 to 4.2. *Tables 1 and 2.*

**Claude in dollars, at the registered prices.** Per right answer the tool arm costs 6.8
to 12.5 times the no-tools arm on the four tasks other than simulate (the no-tools arm
was billed at the half price of the Batch API), and on simulate 32 times for Haiku 5.5
and 8.9 times for Sonnet 5.5. One right answer with tools costs about $0.002 to $0.004
with Haiku 5.5 and $0.04 to $0.06 with Sonnet 5.5, except simulate ($0.08 and $0.33).
The whole run cost 20.25 and 294.49 dollars; Sonnet's validate_plan tool arm alone was
164 dollars. *Table 3.*

## The figures

All four are 3.4 inches wide (single column), PDF and PNG. Blue = the tools arm with
the plain wording (the only tools arm of the Claude run); grey and orange as in the RQ1
figures. Filled markers are open models, hollow markers Claude.

- **A, `tok_ratio_per_trial`**: tokens per trial, tools over no tools, per task and model,
  with 95% intervals. Point: a tool trial costs several times an unaided one on every
  task.
- **B, `tok_tool_output_share`**: share of the tools arm's input that is tool output read
  back. Point: on simulate the tool's answer is a large part of the input; elsewhere it
  is small. Open-model values are estimates (see definitions), Claude values exact.
- **C, `tok_cost_per_right_vs_unaided`**: tokens per right answer, tools over no tools
  (log scale), against the unaided rate; one marker per task and model. Point: the
  premium is above 1 nearly everywhere and is larger where the unaided rate is higher.
  This is the figure for the trend question; its caption must carry the caveats of
  finding 1.
- **D, `tok_simulate_where_tokens_go`**: simulate, open models, tokens per trial split by
  how the trial ended (right; wrong; window full). Point: the window-full trials take two
  thirds of the tools arms' tokens and return nothing.

## What this could add to the paper (outline only)

- **RQ1, solve, one sentence.** Numbers: tokens per right plan, tools (plain) over no
  tools, 2.2 / 3.1 / 4.7 (Qwen3.5-9B / Gemma-26B / Qwen3.6-35B), with intervals [1.30,
  3.38], [2.10, 4.40], [3.66, 5.87]; at a 5:1 output price 0.78 / 1.21 / 1.95. Source:
  matched run.
- **RQ1, a small table (body or supplement).** Per task and open model: tokens per trial
  with and without tools, and the multiplier raw and at 5:1 (table 2, plain rows; solve
  and simulate from the matched run, the three validation tasks from the October rerun).
  Five tasks by three models, one row each.
- **RQ3, one sentence on simulate.** 142 to 168 of 300 trials per open tool cell end with
  a full window, 0 of them right, 62 to 67% of the cell's tokens; tool output is 31 to 39%
  of the input (open, estimate) and 70% (Claude, exact).
- **Claude section, one sentence or a column.** Dollars per right answer, tools over no
  tools: Haiku 5.5 6.8 (solve) to 10.9 (validate_problem), Sonnet 5.5 9.1 to 12.5; with
  the gain in right answers beside it (Sonnet: no difference shown on solve).
- **Discussion, the trend point.** Figure C. Among our five models, the better the model
  does alone, the more each right answer costs with tools (solve 2.2 to 7.8; validate_
  domain 1.1 to 8.6), and the fewer points each extra token buys (finding 2). With the
  caveats: five models at one time, two sets of conditions, different tokenizers, the
  ordering breaks on validate_plan and simulate. A tool designer's reading: the cost is
  mostly re-sent prompt and copied PDDL (finding 5), so an interface that passes files by
  reference and returns compact output would cut most of it; none of this was tested.
- **Conclusion, one clause** at most, on the trend, with "among the models we tested".
- **Supplement.** Tables 1 to 7 and the definitions below. This would replace the
  current "What the Tool Costs" subsection of `paper/supplement_source.tex`, several of
  whose statements no longer hold (next section).

## What must not be said

- **"With tools a right plan is cheaper in tokens."** The supplement's "0.3 to 0.4 times
  the unaided cost" on solve counts a tool trial as a success when the tool returned a
  right plan, on the May sweep. On the delivered answer of the matched run it is 2.2 to
  4.7 times at equal prices.
- **"The tools' premium grows as language models improve."** These are five models at
  one point in time, under two sets of conditions. That is an ordering across models, not
  a time series.
- **"The tools become more expensive to run for stronger models."** The per-trial token
  overhead is about flat within each group of models (finding 1). What shrinks is the
  number of extra right answers that overhead buys.
- **Any ranking of Claude against the open models** by tokens, dollars or multiplier.
  Different tokenizers, temperature, window, output cap counting and hosting; Claude's
  short unaided answers by themselves make its ratios larger.
- **"Sonnet 5.5 is better off without tools because they cost 7.8 times more."** On
  solve its registered reading is "no difference shown"; the cost figure does not turn
  that into "the unaided model is as good".
- **"Tool output is X% of the open models' input"** as an exact figure. The open-model
  rows hold no per-request counts; the split between tool output and the model's own
  tool calls is an estimate by characters (the first-prompt share is exact to within a
  few dozen tokens).
- **"The open models processed N tokens"** for the window-full trials: the refused
  request is stored as 16,384 input tokens the server never ran, and its true size is
  larger. Quote the stored figure with that note, or the figure without it.
- **Anything about time or latency.** Four concurrent requests and preemption on the
  open models; not recoverable.
- **Pooled multipliers** over models, tasks or corpora.
- **The rerun's solve and simulate cost rows in `NUMBERS.md`** (section S2-C) as the cost
  of the tools on those tasks. They divide by the rerun's no-tools arm, whose system
  message was faulty on those two tasks; the matched run's figures replace them (for
  example Qwen3.5-9B solve 1.37 there, 2.17 here).
- **The old Claude runs and the new ones as one experiment** (side table below).

## Side table: the old Claude runs (a different experiment)

Quoted from `development/NUMBERS.md` and the supplement, not recomputed. Haiku 4.5 and
Sonnet 4.6, wording v11, unaided answers requested through structured output (short
answers), May-era conditions. The registration of the new run names "comparing this
run's rates with the old Claude runs as if they were the same experiment" as a wrong
reading; the rows sit side by side only so that nobody reads the old figure as the new.

| run | model | solve, tokens per right answer, tools / no tools |
|---|---|---|
| old (sweep5v2 conditions) | Sonnet 4.6 | 3.1 (18.6K against 6.0K) |
| old (sweep5v2 conditions) | Haiku 4.5 | 6.1 (48.5K against 8.0K) |
| new (this analysis) | Sonnet 5.5 | 7.8 (19.6K against 2.5K) |
| new (this analysis) | Haiku 5.5 | 5.9 (20.9K against 3.5K) |

## Definitions: how a token is counted

Established from the code that writes the fields, not from documentation.

- **Open models** (`pddl_eval/chat.py`, `pddl_eval/vllm_client.py`). A row's
  `tokens.prompt` and `tokens.completion` are sums over the requests of the trial of
  vLLM's `usage.prompt_tokens` and `usage.completion_tokens`; `tokens.turns` counts the
  requests. Every request re-sends the whole conversation, so the system message, the
  tool list and every earlier tool call and tool result are counted again on each later
  request. Prefix-cache hits are not deducted. When a request is refused because the
  prompt alone fills the 16,384-token window, the client adds a synthetic turn whose
  input is vLLM's lower bound, exactly 16,384 for the 1-token probe, and whose output is
  0. A final request clipped to the room left is counted as generated. The 1-token probe
  itself is not counted. No per-request count is stored.
- **Claude** (the sidecar `trial_meta.jsonl`, read by `frontier55.read_cell`). One usage
  block per request: input (uncached + cache-written + cache-read; no cache was used)
  and output. The row's sums equal the sidecar's on every trial (checked). The no-tools
  arm is one Batch request per trial and its usage block comes from the batch result;
  dollars are priced at half the list price. No trial ran out of window or was refused.
  Sonnet's six short notes between tool calls are inside the output tokens.
- **Right** is each corpus's registered grade: the matched run's on solve and simulate,
  the October rerun's frozen delivered grade on the validation tasks, the Claude run's
  registered grade. Before computing, the script reproduces the right count of all 18
  matched-run cells and all 20 Claude cells from the filed outputs, and the rerun's
  loader reproduces its frozen readout.
- **Price-weighted tokens** = input + 5 x output. **Multiplier** = (tokens of the tools
  arm / its right answers) over (the same for the no-tools arm), same trials, with the
  domain-cluster bootstrap of `gen_common.multiplier_boot` (20 domains, 10,000 draws,
  seed 20261002). Draws in which an arm has no right answer are dropped and counted.
- **Where the input goes.** Claude: exact. Request k's input is request k-1's input plus
  the reply it wrote plus the tool results; summed over n requests that gives the first
  prompt n times, each earlier reply once per later request, and each tool result once
  per later request, which add up to the input exactly. Open models: the first prompt is
  the no-tools input of the same trial plus a fixed offset per model, task and arm (the
  system message and the tool list). The offset is measured on tool trials that made one
  request (one value in every cell; the script halts otherwise), or on two-request trials
  whose second request was refused (summed input minus 16,384). Where both are
  available they agree (3,387 = 3,387 on 93 and 140 trials; Gemma-26B 2,805 on 127
  trials and 2,804 on 8). Cells with neither borrow from the same model; the measured
  offsets of a model span at most 43 tokens. What remains is split between the model's
  own calls and the tool's output by characters (a call's arguments against its result),
  which is an estimate.
- **Window full** = the final request was refused or clipped for a full window
  (`matched_run.window_full`). **At cap** = the final reply stopped at the output cap and
  the window was not full.

## Checks

- The four frozen package hashes are checked before any row is read and again at the end:
  frontier55 `0cbb69b7…`, matched run `1f3d0f84…`, rerun `822aace9…`, control `825dab63…`.
  All unchanged.
- The validator route returned the stored verdict for 740 plans before any new plan.
- **Independent recount**, plain JSON over the raw files, none of the loaders: the
  matched run's Gemma-26B simulate plain cell from `trials.jsonl` (300 trials, 5,764,321
  input, 697,540 output, 672 requests) and Claude Haiku 5.5's simulate tool cell from
  `spend.jsonl`, the runner's price log, a different file from the sidecar the analysis
  reads (300 trials, 16,302,791 input, 1,193,182 output, 603 requests, $5.0204). Both
  equal the analysis exactly. Dollars per model from the sidecar equal the spend files:
  Haiku 20.2482 against 20.2481, Sonnet 294.4908 against 294.4908.
- The rerun's validation-task multipliers reproduce `NUMBERS.md` section S2-C, which used
  the same arms (for example Gemma-26B validate_domain 5.15 [4.22, 6.10], Qwen3.6-35B
  validate_plan 3.60 [3.22, 4.02]).
- `tests/test_token_consumption.py` checks the arithmetic on hand-made rows.

## What could not be determined

- Time and latency, for the reasons above.
- The open models' tokens per request. The split between the tool's output and the
  model's own tool calls is therefore estimated, and the final reply's length with tools
  is not separable from the earlier turns for the open models.
- The true size of a refused request's prompt (only a lower bound is stored).
- What prefix caching saved on the open models' re-sent prompts (not logged).
- A cost in money for the open models (no list price); the 5:1 weighting is an
  illustration.
- The thinking-on token counts of the May sweep were not used (they belong to a
  different corpus and are not needed for any reading here).

## Reproduce

```
python -m tools.reanalysis.token_consumption \
    --results /Users/omereliyahu/personal/pddl-copilot-experiments/results \
    --marketplace /Users/omereliyahu/personal/pddl-copilot-experiments/external/pddl-copilot-5e4f9c0
```

Grading all 59,280 trials takes about two minutes (`--cache FILE` keeps the graded trials
for re-runs).
