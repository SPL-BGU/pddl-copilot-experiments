# Our paper and Corrêa et al.: outline for the advisor discussion

*Draft of 2026-11-22, not committed. Their figures: arXiv:2511.09378v2, re-read that day. Our figures: `NUMBERS.md`, the delivered-rerun readout, and the raw frontier trials where marked. Section 9 is the source list and can be dropped from the advisor copy.*

**The paper:** A. B. Corrêa, A. G. Pereira, J. Seipp. *Frontier Large Language Models Rival State-of-the-Art Planners.* v1 November 2025, v2 May 2026.

## 1. The short version

- **Their question:** can a language model plan as well as a planner, by itself?
- **Their answer:** the best one can, on their benchmark. Gemini 3.1 Pro solved 245 of 360 tasks and the best planner solved 234.
- **Our question:** do tools help?
- **Our answer:** often by a lot, but it depends on the task. We follow two steps: whether the model calls the tool, and whether the tool's result reaches the final answer.
- **How they relate:** theirs measures the model alone. Ours measures what a tool adds. Their result does challenge how our draft describes unaided planning (section 6).

## 2. Design differences

| | Corrêa et al. | Ours |
|---|---|---|
| Tools | none | with and without planners and validators |
| Tasks | write a plan | write a plan; validate a domain, a problem or a plan; trace states |
| Models | DeepSeek-R1, three GPT and three Gemini generations | five open-weight Qwen and Gemma models; Claude Sonnet 4.6 and Haiku 4.5 |
| Reasoning | provider defaults, including reasoning models | Claude with thinking off; open models with it off and on |
| Domains | 8, classical only | 20: 10 classical, 10 numeric |
| Planning problems | 360, newly generated | 100, existing and public domains |
| Size | up to 477 blocks; LAMA's longest plan is 1,438 steps | 2 to 35 objects; reference plans of 2 to 110 steps |
| Prompt | two solved examples and a checklist | no examples; three wordings in the main sweep |
| Sampling | temperature 0.1 (GPT-5: 1.0), one attempt | temperature 0 |
| Output limit | provider default | fixed per task (8,192 tokens for planning in the main sweep) |
| Baseline | LAMA, DecStar, Scorpion Maidu (30 min, 8 GiB) | the same model without tools |
| Plan checker | VAL | pyvalidator, cross-checked afterwards with VAL |
| Name control | random strings | one themed renaming per domain |

## 3. What they found

| System | Normal names | Random names |
|---|---|---|
| Gemini 3.1 Pro | 245 (68%) | 231 (64%) |
| Scorpion Maidu | 234 (65%) | 234 |
| Gemini 3 Pro | 233 (65%) | 203 (56%) |
| DecStar | 227 (63%) | 227 |
| GPT-5 | 205 (57%) | 152 (42%) |
| LAMA | 204 (57%) | 204 |
| Gemini 2.5 Pro | 161 (45%) | 142 (39%) |
| DeepSeek-R1 | 157 (44%) | 93 (26%) |
| GPT-4.1 | 20 (6%) | 0 |
| GPT-3.5 | 0 | 0 |

- The lead is 11 tasks out of 360, from one attempt per task.
- Gemini 3.1 Pro beats all three planners in 4 domains (Blocksworld, Childsnack, Floortile, Spanner) and loses to at least one in the other 4.
- With random names, its total falls just below Scorpion Maidu's.
- GPT-5 is level with LAMA and below both competition winners.
- They acknowledge that the models need far more compute and energy than the planners.

## 4. What we found

### 4.1 Planning with and without the planner

| Model | Alone | With planner | Study |
|---|---|---|---|
| Sonnet 4.6 | 28.7% | 95.0% | main sweep |
| Haiku 4.5 | 22.0% | 95.0% | main sweep |
| Gemma 26B | 21.3% | 92.3% | delivered rerun |
| Qwen 9B | 24.3% | 88.7% | delivered rerun |
| Qwen 35B | 25.3% | 77.0% | delivered rerun |

- Sonnet's 28.7% pools three wordings. On the one wording used with tools it is 29/100 (raw trials).
- The 35B with-planner cell did not meet the replication criterion, so treat its size with care.
- The rerun's unaided answers had a JSON format constraint and its tool answers did not.

### 4.2 First step: does the model call the tool?

- Claude called it in 100% of trials, so this step never limited the frontier models.
- It does vary for open models. In the rerun, Gemma called the plan validator in 20.0% of trials, and in 93.1% after one steering sentence.
- **Not calling did not mean failing.** Gemma delivered 89.2% with the tool available and 88.3% without it (+0.9 points, 95% CI -1.2 to 2.9). The registered reading is "no delivered harm".
- Steering added 7.5 points (95% CI 4.9 to 10.2). The registered reading is "unresolved".

### 4.3 Second step: does the result reach the answer?

- For validation verdicts, almost nothing is lost.
- For plans, Claude loses 5 points (100% correct from the tool, 95% delivered). In the rerun's plain arm, the open models lose 6 to 13% of correct tool results.
- For state traces, the open models lose 70 to 91% of correct tool results in the plain arm. Many of these answers had no room left or were cut off.
- The tool condition can be worse. Gemma's state tracing fell from 24.0% alone to 8.3% with the tool (-15.7 points, 95% CI -24.7 to -6.7). The two conditions also differ in the JSON constraint, so the tool may not be the only cause.
- The plain state-tracing cells of both Qwen models did not meet the replication criterion, so treat those sizes with care.

## 5. What each paper adds

**Only theirs has:**
- a comparison with competition-winning planners;
- large problems;
- top reasoning models and a trend across model generations;
- a random-name test.

**Only ours has:**
- the same models with and without tools;
- separate measurements of calling and delivery;
- validation and state-tracing tasks;
- numeric planning;
- a token cost for each correct answer.

## 6. Where their paper challenges ours

**6.1 We say that models cannot plan unaided.**
- The introduction says models "fall well short of solvers" (`main.tex:124`). We also say planning essentially does not happen unaided (151, 754, 841) and that the floor carries over to the frontier (1268, 1712).
- These can hold only for our models and settings. As general statements, their results contradict them.
- *Suggested change:* limit the wording to the tested setup and cite their paper, which `main.tex` does not yet do.

**6.2 Our frontier baseline may be weak.**
- Our 22 to 29% and their 68% differ in model, thinking, prompt, output limit and problems, so we cannot name the cause today.
- *Planned:* Claude with thinking on (D5a) and their exact prompt (D5e). The full run is approved and waits for the preregistration.

**6.3 Our problems are small and within the planner's reach.**
- The planner solved all 100 problems in both Claude tool arms, and it also built our answer key.
- *Planned:* larger problems (D5b). In the open PR #138, our default planner solves 40/40 easy, 31/40 medium and 15/40 hard problems within 120 seconds. No model has run on them yet.

**6.4 Memorization is open in both papers.**
- Our renaming test on Sonnet planning is unresolved: -0.33 points, 90% CI -10.59 to 9.93.
- Their traces show Gemini recognizing 4 of the 8 domains despite random names. On the other 4 it lost only 7 tasks in total under renaming.
- On PlanBench's obfuscated Blocksworld, Haiku scores 0% alone and 71.8% with tools. Their results show that this 0% cannot be generalized to all frontier models.
- *Planned:* two random-name versions per domain (D5d). Random names alone will not rule out domain recognition.

**6.5 If models can plan, why use a tool?**
- On our problems the planner adds about 66 to 73 points for Claude.
- It is not cheaper in tokens: each correct plan costs 3.1 times as many tokens for Sonnet and 6.1 times for Haiku.
- We have not tested whether the gain holds for a reasoning model that already plans well.

## 7. What we can and cannot claim

**We can say:**
- They measure planning without tools, and we measure the effect of offering tools.
- For the models and problems we tested, planner access greatly improves delivered plans.
- A correct tool result can be lost before the final answer, especially when the answer is long.

**We should not say:**
- "LLMs cannot plan."
- "Our results refute theirs", or a direct comparison of 29% with 68%.
- "A model that skips the tool gets the answer wrong."
- "Tools always help."
- "There is no memorization effect on frontier planning."
- "The planner would beat their models on their benchmark." We have not run it.

## 8. Questions for the advisors

1. **Positioning:** do we present their paper as complementary, with our unaided claims narrowed? *Recommendation: yes.*
2. **Main message:** the rerun retired the "Invocation Is the Bottleneck" title. Is "calling and delivery" a clear enough contribution next to their paper? *Recommendation: yes, with delivery carrying the frontier story, since Claude always calls.*
3. **Other vendors:** do we need GPT or Gemini to answer them? *Recommendation: defer until we see the Claude thinking-on result.*
4. **Large problems:** which sizes go to the models? *Recommendation: easy and medium, and hard only with the planner's failures marked.*
5. **Reasoning models with tools:** D5a tests thinking without tools only. Do we also need a thinking-on tool arm? *Recommendation: decide after D5a, and add it if thinking closes much of the gap.*

## 9. Sources and cautions

- **Their paper:** https://arxiv.org/abs/2511.09378v2, Tables 1 to 3 and Appendices B and C. Percentages, the per-domain win count and the 7-task total are our arithmetic from their tables. v2 says the data and code will be released upon acceptance.
- **Claude figures:** `NUMBERS.md`, "Frontier e2e" and the cost-of-pass row. The 29/100 was recounted from `results/sonnet-frontier/sweep5v2/trials.jsonl`.
- **Open-model figures in section 4:** `reference/delivered_rerun_readout.md`, tables E1 to E4 and readings R1 to R3. The rerun is a separate replication and is never pooled with the main sweep. `main.tex` still shows main-sweep figures in places (for example 21% and 94% calling).
- **Known grader bugs:** frozen figures are used above. With the letter-case bug corrected after the fact, Claude alone is 32.7% (Sonnet) and 25.0% (Haiku), and both cost multipliers would rise. A second bug counts some correct open-model plans as delivery losses (ISS-028).
- **Planned runs:** `weakness_action_plan.md` D5 and `draft_D1f_extension_prereg.md`, which is not frozen.
