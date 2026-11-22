# Thesis literature review, first full draft

*Draft of 2026-11-22 for Omer's read (roadmap milestone M1). Nothing here is in the
thesis doc or in `paper/` yet.*

**What this file is.** A thesis-style review of the work behind the three research
questions of `roadmap.md` §2. Sections 1 to 7 are the prose. Section 8 is the reading
list, one line per paper. Section 9 lists papers that are wanted but not checked yet.
Section 10 has questions for Omer.

**Sources.** Every claim about another paper comes from one of these:

- `draft_B1_B2_related_work.md` §3, the check behind each reference (called "B1 §3"
  below), and its §4 for the facts about our group's earlier version;
- `draft_D5_cost_and_correa.md` Part 1, for Corrêa, Pereira and Seipp;
- a fresh read of the paper's arXiv record or page on 2026-11-22, marked
  `[verified 2026-11-22: <url>]` at the first mention. For these I read the abstract
  only, unless the note says more, so the text stays at abstract level.

Citations are written as author and year. Section 8 gives the citation key for each one.
Keys that are already in `paper/refs.bib` or in B1 §2 are reused. Keys marked "new" are
proposals.

**The three research questions** (advisors, 2026-11-22):

- **RQ1.** Do PDDL tools help an LLM do planning-related tasks?
- **RQ2.** Does the LLM know to choose the right PDDL tool?
- **RQ3.** Does the LLM know how to use the tool's output properly?

---

## 1. Background: planning, PDDL, planners and validators

Automated planning studies how to find a sequence of actions that takes an initial state
to a state that satisfies a goal. The Planning Domain Definition Language (PDDL) is the
standard way to write such problems (McDermott et al., 1998). A *domain* file gives the
predicates and the actions, each with preconditions and effects. A *problem* file gives
the objects, the initial state and the goal. PDDL2.1 added numeric fluents and time
(Fox and Long, 2003), which is the basis of the numeric domains used in this thesis.

Planners search for a plan from these two files. Fast Downward (Helmert, 2006) and FF
(Hoffmann and Nebel, 2001) are well-known classical planners, and ENHSP handles numeric
planning (Scala et al., 2016). A plan validator checks a given plan step by step against
the domain and the problem. VAL (Howey, Long and Fox, 2004) is the validator that most
of the work cited below uses to check plans. The Unified Planning library offers
one Python interface for modelling planning problems and passing them to different
engines (Micheli et al., 2025) `[verified 2026-11-22: https://doaj.org/article/49dbf4912b0440eeba1cb7ec8d69cedc]`.

Two properties of these tools matter for everything that follows. First, they are sound:
a plan that a planner returns reaches the goal, and a validator's verdict follows from the
semantics of the language. Second, they need exact PDDL as input. They cannot work from a
loose description.

The tool suite studied in this thesis exposes this kind of software to a language model:
Fast Downward for classical problems, ENHSP for numeric ones, and a validator and state
simulator built on Unified Planning. The answer key was cross-checked afterwards with VAL.

## 2. LLMs as planners, without tools

### 2.1 PlanBench and the first results

PlanBench (Valmeekam et al., 2023) gives a model a planning problem in natural language,
asks for a plan, and checks the plan with VAL. On its Blocksworld plan-generation test,
GPT-4 solved 206 of 600 problems. Kambhampati et al. (2024) argue from this kind of
evidence that autoregressive LLMs cannot plan or verify plans by themselves, and they
propose LLM-Modulo frameworks, where the model works in a loop with sound external
verifiers. Section 4 returns to that proposal.

Prompting techniques did not close the gap. Stechly, Valmeekam and Kambhampati (2024)
study chain-of-thought prompts on Blocksworld
`[verified 2026-11-22: https://arxiv.org/abs/2405.04776]`. They report gains only when
the examples in the prompt are very specific to the problem class, and the gains fade as
the problems grow beyond the size of the examples.

### 2.2 Reasoning models

Reasoning models raised the scores. On PlanBench's 600 Blocksworld problems, o1-preview
produced a correct plan for 97.8%. It reached 52.8% on the obfuscated Mystery Blocksworld
problems and 23.6% on 110 larger Blocksworld problems (Valmeekam, Stechly and Kambhampati,
2024). The journal version of that study adds that the gains come with large and
unpredictable inference costs, and that o1 improves further when it sits inside a system
with a sound verifier (Valmeekam et al., 2025).

Shojaee et al. (2025) test reasoning models on puzzle environments whose complexity can
be set exactly `[verified 2026-11-22: https://arxiv.org/abs/2506.06941]`. These are
puzzles and are not written in PDDL. The authors report that accuracy collapses beyond a
certain complexity, and that the models' reasoning effort grows with complexity up to a
point and then falls even though token budget remains.

Both lines point at the same variable, problem size. A model that does well on small
problems can fail on larger ones of the same kind.

### 2.3 Frontier models against state-of-the-art planners

Corrêa, Pereira and Seipp (2025) give the strongest result so far for planning without
tools `[counts re-read 2026-11-22: https://arxiv.org/html/2511.09378v2, abstract and Tables 1 and 2]`.
They generate 360 new tasks from 8 domains of the IPC 2023 learning track, 45 per domain.
The model gets the PDDL files and two solved examples in the prompt. It has one attempt
per task and no tools, and every plan is checked with VAL. The baselines are three
classical planners (LAMA, DecStar and Scorpion Maidu), each with 30 minutes and 8 GiB per
task.

On the standard tasks, Gemini 3.1 Pro solved 245 of the 360 and the best planner solved
234. GPT-5 solved 205, next to LAMA's 204. To control for memorization the authors
replace every action, predicate and object name with a random string. Under that change
Gemini 3.1 Pro solved 231, just below the best planner, and GPT-5 fell to 152. The
planners are unaffected by the renaming. The authors also state that the models need far
more energy and time than the planners.

This paper measures the model alone. It does not ask what happens when the same model is
offered a planner. It also shows that statements about what models can do unaided hold
only for the models, prompts and problem sizes that were tested.

### 2.4 Benchmarks for parts of planning

Other benchmarks split planning into the judgments made along the way. ACPBench (Kokel
et al., 2025) builds boolean and multiple-choice questions from PDDL for seven tasks over
13 domains, so every answer is provably correct. Two of its tasks are close to ours.
*Progression* asks how an action changes the state, which our simulate task asks for
every step of a plan. *Validation* asks whether an action sequence is a valid plan, which
is our validate_plan task. With chain-of-thought prompting and two examples, GPT-4o
scored 52.5% on the multiple-choice validation questions, its lowest task. ACPBench Hard
(Kokel et al., 2026) asks open-ended versions of the same tasks and scores them with a
symbolic validator; with few exceptions, every tested model stays below 65%. In our
reading of both setups, the models answer without tools.

### 2.5 What this leaves open

These studies report what a model does alone, and how that changes with problem size.
Where a sound verifier is added, it is wired into a loop around the model (Section 4).
RQ1 asks for a different comparison: the same model, on the same problems, with and
without tools that it is free to call. The size effects reported here are also why RQ1
reports results against simulation length and problem hardness as well as on average.

## 3. LLMs as formalizers

A second line uses the model as a translator. The model turns a natural-language
description into a formal model, and a sound solver does the search. LLM+P (Liu et al.,
2023) pipelines an LLM into a classical planner. Guan et al. (2023) use LLMs to build
world models for model-based planning. Plansformer (Pallagani et al., 2022) fine-tunes a
model for plan generation, and Silver et al. (2024) apply pretrained LLMs to generalized
planning in PDDL domains. The survey by Tantakoun, Muise and Zhu (2025) treats LLMs as
tools that write and refine planning models for off-the-shelf planners, and notes that
end-to-end planning by an LLM still lacks soundness guarantees.

Huang and Zhang (2025) measure the limits of this approach with zero-shot prompting and
no tools. They find that models are largely robust to lexical changes of the domain
symbols, and that formalization gets worse as the descriptions become more natural. On
their obfuscated Mystery Blocksworld set, GPT-4o as a formalizer produced 70 correct
plans out of 100, against 0 of 100 as a planner, graded with VAL. The advantage does not
hold for every model. o3-mini scored 74 of 100 as a planner on the same data, and the
authors describe the results as mixed across models.

Two results bear on how such pipelines should be graded. Planetarium (Zuo et al., 2025)
checks generated PDDL problems for semantic equivalence with the intended task. In its
zero-shot setting, 96.1% of GPT-4o's problem files parse and 94.4% are solvable, yet only
24.8% are correct. A file that a planner accepts can still describe the wrong problem.
LLMFP (Hao, Zhang and Fan, 2025) formalizes planning problems as optimization problems
for an SMT solver. On Blocksworld and Mystery Blocksworld (602 queries each) it reaches
optimal rates of 96.2% and 77.7% with GPT-4o, where direct planning with the same model
reaches 41.5% and 0.8%.

**What this leaves open.** In a formalizer pipeline the call to the solver is fixed by
the system's design. The model never decides whether to call it or which solver to call,
so these studies cannot speak to RQ2. Our main tasks start from complete PDDL files, so
they also do not test formalization itself. The PlanBench part of our work covers that
step.

## 4. LLMs with external verifiers and solvers

### 4.1 Can a model check plans itself?

Valmeekam, Marquez and Kambhampati (2023) use GPT-4 as both plan generator and plan
verifier on Blocksworld. The GPT-4 verifier accepted 38 of 45 invalid plans. The loop
with this verifier solved 55 of 100 problems, against 88 with VAL in its place. Stechly,
Valmeekam and Kambhampati (2025) extend the analysis to three domains, STRIPS planning
among them, and find that performance collapses under self-critique and improves under
sound external verification. An earlier study of graph colouring reports the same
weakness (Stechly, Marquez and Kambhampati, 2023)
`[verified 2026-11-22: https://arxiv.org/abs/2310.12397]`: GPT-4 was no better at
verifying a solution than at producing one. Outside planning, Huang et al. (2024) report
that LLMs struggle to correct their own reasoning without external feedback.

The 38 of 45 figure is a false-positive rate: wrong plans judged valid. This is the same
quantity as the first metric of RQ1, measured there for a model that may pass the plan to
a sound validator.

### 4.2 Systems that put a sound component in the loop

The LLM-Modulo proposal (Kambhampati et al., 2024) pairs the model with external
verifiers in a generate-and-check loop. Gundawar et al. (2024) apply it to travel
planning `[verified 2026-11-22: https://arxiv.org/abs/2405.20625]` and report that it
raises GPT-4-Turbo's baseline result by a factor of 4.6 on the TravelPlanner benchmark.

Agentic systems wrap the solver in a longer loop. In the system of La Malfa et al.
(2026), an orchestrator LLM writes the PDDL domain and problem, agents refine them, and
the validated files go to an external planner. With GPT-5-mini it raises the average
PlanBench success rate from 76.6% to 91.6%, over three runs of 50 problems per task, with
GPT-5-mini as the judge of success. Göbel et al. (2026) expose a step-wise PDDL simulator
to Claude Haiku 4.5 over MCP and let the model choose one action at a time until a plan
validator accepts the plan. On 102 IPC Blocksworld instances this setup solves 66.7%,
against 63.7% for direct planning, at 5.7 times the token cost per solution. Their tool
set contains no planner, so the model does the search itself.

A different division of labour has the model write code for the planner. Corrêa, Pereira
and Seipp (2025b) ask an LLM for domain-dependent heuristic functions in Python and use
the best one inside greedy best-first search
`[verified 2026-11-22: https://arxiv.org/abs/2503.18809]`. They report that these
heuristics solve many more unseen test tasks than state-of-the-art domain-independent
heuristics. The search stays sound because the plan still comes from the planner.

### 4.3 What this leaves open

In each of these systems the use of the sound component is built in. The loop always
runs the verifier, or the pipeline always calls the planner. Our setting is simpler and
asks something these designs cannot: the model may hand one task to a sound tool, or
answer by itself, and nothing forces the call. How much the tool helps in that setting is
RQ1. Whether the model makes the call at all is RQ2.

## 5. Tool use and tool selection

### 5.1 Tool calling in general

Giving LLMs external tools is now standard practice, from learned tool invocation
(Schick et al., 2023) to large API collections (Qin et al., 2024). The Model Context
Protocol (Anthropic, 2024) standardizes how tools are described to a model and how its
calls are relayed. It is how our planners and validators are exposed. A parallel line
raises tool use through scaffolding, by interleaving reasoning with tool actions (Yao et
al., 2023) or by handing numeric subproblems to executable programs (Chen et al., 2023).

### 5.2 Benchmarks of tool calls

BFCL checks a model's calls against the expected function and arguments with an
abstract-syntax-tree method (Patil et al., 2025), and tau-bench measures multi-turn
interaction between a tool-using agent and a user (Yao et al., 2024). Benchmarks built on
live MCP servers extend this to many tools and long tasks. MCP-Universe scores runs with
execution-based evaluators (Luo et al., 2025). MCP-Bench and MCP-AgentBench use
rule-based checks and an LLM judge (Wang et al., 2026; Guo et al., 2025). MCPAgentBench
adds distractor tools to its candidate lists to test selection (Liu et al., 2025).

### 5.3 The decision to call, and which tool

Fewer studies ask whether the model decides to call at all. BFCL separates items where a
call is expected from items where none is. MetaTool (Huang et al., 2024b) asks the model
directly whether a query needs a tool and which one, and finds that most models lack this
awareness. When2Call (Ross et al., 2025) poses a four-way choice that includes a tool
call, and builds its items so that answering directly is always a hallucination. SMART
(Qian et al., 2025) studies the opposite error, calling tools for questions the model
could answer from its own knowledge.

Two further papers sort tool errors into types. Xu et al. (2024) separate *tool selection
hallucination*, where the model picks an inappropriate tool, from *tool usage
hallucination*, where it misuses the tool `[verified 2026-11-22: https://arxiv.org/abs/2412.04141]`.
ToolBeHonest (Zhang et al., 2024) diagnoses hallucination in tool-augmented models,
including cases where a needed tool is missing
`[verified 2026-11-22: https://arxiv.org/abs/2406.20015]`. Gemini-1.5-Pro and GPT-4o
scored 45.3 and 37.0 out of 100 on it.

### 5.4 What this leaves open

These benchmarks fix the right decision when the item is built, and they score the
decision itself. Our tasks differ in two ways. A sound tool is always relevant, yet the
model can often answer correctly without it. And we can follow the decision through to
the final answer, which a deterministic checker grades. RQ2 takes the selection measures
of this literature (the right tool was called; only the right tool was called; other
tools were called as well) and applies them to planning tools, with all seven tools
visible in every trial.

## 6. Using the tool's output

This is the thinnest part of the literature we found, and it should be read with that in
mind.

Most tool benchmarks grade the call or the outcome of the whole run. BFCL grades the
call. MCP-Universe scores a run with execution-based evaluators, and MCP-Bench and
MCP-AgentBench add an LLM judge. Among the benchmarks reviewed in Section 5, we found
none that isolates the step after a correct call, where the model reads the tool's
result and writes its answer.

T-Eval (Chen et al., 2023) comes closest among the papers checked here
`[verified 2026-11-22: https://arxiv.org/abs/2312.14033]`. It splits tool use into
sub-processes, including understanding and review, and scores each one separately. It
reports that this step-by-step view agrees with outcome-level evaluation and gives a
finer picture. API-Bank (Li et al., 2023) evaluates models on planning, retrieving and
calling APIs over annotated tool-use dialogues
`[verified 2026-11-22: https://arxiv.org/abs/2304.08244]`. The "tool usage
hallucination" type of Xu et al. (2024) also belongs here in part.

Within planning, the studies of Section 4 leave this step unmeasured for different
reasons. In Göbel et al. (2026) a run ends when the validator accepts the plan, so
acceptance by the tool is the outcome. In La Malfa et al. (2026) success is judged by an
LLM. Planetarium's result (Section 3) is a warning from the formalizer side: an
intermediate check that passes does not mean the final artifact is right.

Two more points bear on how a delivered answer should be graded. Tam et al. (2024) report
that restricting a model to a structured output format such as JSON lowers its reasoning
performance, and more so under stricter formats
`[verified 2026-11-22: https://arxiv.org/abs/2408.02442]`. An answer format is therefore
part of the experimental condition. HAL (Kapoor et al., 2026) evaluates agents across
models and scaffolds and reports accuracy against dollar and token cost, which is the
practice our cost reporting follows.

**What this leaves open.** Among the works reviewed here, none reports, for planning
tools, how often a correct tool result fails to reach the model's final answer. That
share is RQ3. Our tasks make it measurable because both sides are checked by a
deterministic program: the tool's result and the final answer.

## 7. Our earlier version, and the gap this thesis fills

Benyamin et al. (2025) introduced the Planning Copilot, which exposes planners, a plan
validator and a plan simulator to an LLM over MCP. It is our own group's preliminary
study (arXiv only), and this thesis is its more rigorous successor. They tested three
open-weight models (Qwen3 at 0.6B and 4B, and GPT-OSS-20B) with and without the tools on
the same five task types. With tools, the success rate rose in 14 of the 15 model-task
cells. On solve it went from 0.04 to 0.78 for Qwen3-4B, and no model simulated a plan
correctly without tools.

The evaluation was preliminary in ways that matter for each research question:

- It used 250 single-task queries in all, reported the better of each model's thinking
  and non-thinking runs, gave no confidence intervals, and had no control for memorized
  domains.
- Its tool-arm system prompt told the model that calling tools was its only way to solve
  a task. The choice to call was therefore pushed by the prompt.
- A tool-arm trial counted as a success only if the model had called the correct tool
  and its final answer was right. Choosing the tool and using its result were folded into
  one number.

The gap, stated per research question:

| RQ | what earlier work measured | what is missing |
|---|---|---|
| RQ1 | models alone (Sections 2 and 4.1), or systems where the solver is always called (Sections 3 and 4.2); the preliminary study with small samples and no intervals | the same model with and without sound planning tools, on the same problems, with per-task error types, results against problem size, and plan length |
| RQ2 | tool-selection decisions on items where the right choice is fixed in advance (Section 5) | which planning tool a model calls when all tools are offered and it is free to answer by itself |
| RQ3 | calls and whole-run outcomes; one step-by-step benchmark outside planning (Section 6) | the share of correct tool results that do not reach the final answer, on planning tasks |

This thesis answers the three questions on 273,600 open-weight trials over two corpora
(`NUMBERS.md`, "Corpus scale"), a pre-registered rerun that stores full answers, and runs
of two Claude models. The figures themselves belong to the results chapters.

---

## 8. Reading list

"B1 §3" is the verification table in `draft_B1_B2_related_work.md`. "bib header" means
the entry was verified on 2026-06-14 per the header of `paper/refs.bib` (metadata; the
one-line description used here is the one already in the tex). "D5" is
`draft_D5_cost_and_correa.md` Part 1. "today" means the arXiv record or page was read on
2026-11-22, abstract level.

| paper | key | why it matters to us | RQ | check |
|---|---|---|---|---|
| McDermott et al., 1998, Yale tech report | `mcdermott1998pddl` | defines PDDL | background | bib header |
| Fox and Long, 2003, JAIR | `fox2003pddl21` | PDDL2.1, numeric fluents | background | bib header |
| Helmert, 2006, JAIR | `helmert2006fastdownward` | our classical planner | background | bib header |
| Hoffmann and Nebel, 2001, JAIR | `hoffmann2001ff` | classical planner; the family the earlier version's Metric-FF comes from | background | bib header |
| Scala et al., 2016, ECAI | `scala2016enhsp` | our numeric planner (ENHSP) | background | bib header |
| Howey, Long and Fox, 2004, ICTAI | `howey2004val` | VAL, the validator used for the cross-check and by most cited work | background | bib header |
| Micheli et al., 2025, SoftwareX 29:102012 | `micheli2025unifiedplanning` (new) | the library under our validator and simulator | background | today (DOAJ record) |
| Valmeekam et al., 2023, NeurIPS D&B | `valmeekam2023planbench` | the standard no-tools planning benchmark; our PlanBench section uses it | RQ1 | B1 §3 |
| Kambhampati et al., 2024, ICML | `kambhampati2024llmmodulo` | the position that LLMs need sound external verifiers | RQ1 | B1 §3 |
| Stechly, Valmeekam, Kambhampati, 2024, NeurIPS | `stechly2024cot` (new) | chain-of-thought gains fade as problems grow | RQ1 (hardness) | today |
| Valmeekam, Stechly, Kambhampati, 2024, arXiv | `valmeekam2024o1prelim` | o1 on PlanBench; drops on obfuscated and larger problems | RQ1 (hardness) | B1 §3 |
| Valmeekam et al., 2025, TMLR | `valmeekam2025o1tmlr` | cost of reasoning models; better with a sound verifier | RQ1 | B1 §3 (abstract level) |
| Shojaee et al., 2025, NeurIPS | `shojaee2025illusion` (new) | accuracy collapse with complexity, on puzzles | RQ1 (hardness) | today |
| Corrêa, Pereira, Seipp, 2025, arXiv v2 2026 | `correa2025frontier` | frontier LLMs match strong planners without tools; limits our unaided claims | RQ1 | D5; counts re-read today |
| Kokel et al., 2025, AAAI | `kokel2025acpbench` | progression and validation tasks close to our simulate and validate_plan | RQ1 | B1 §3 |
| Kokel et al., 2026, ICLR | `kokel2026acpbenchhard` | open-ended versions, symbolic validators | RQ1 | B1 §3 |
| Liu et al., 2023, arXiv | `liu2023llmp` | LLM as translator in front of a classical planner | context for RQ2 | bib header |
| Guan et al., 2023, NeurIPS | `guan2023world` | LLMs build world models for planning | context | bib header |
| Pallagani et al., 2022, arXiv | `pallagani2022plansformer` | fine-tuned plan generation | context | bib header |
| Silver et al., 2024, AAAI | `silver2024generalized` | LLMs for generalized planning in PDDL | context | bib header |
| Tantakoun, Muise, Zhu, 2025, Findings of ACL | `tantakoun2025survey` | survey of LLMs as formalizers | context | B1 §3 |
| Huang and Zhang, 2025, ACL | `huang2025limit` | formalizer against planner, no tools; starting point of our PlanBench part | RQ1 | B1 §3 |
| Zuo et al., 2025, NAACL | `zuo2025planetarium` | solvable is not the same as correct; a grading lesson | RQ3 | B1 §3 |
| Hao, Zhang, Fan, 2025, ICLR | `hao2025llmfp` | formalizing to an SMT solver; reports optimal rate (plan quality) | RQ1 (quality) | B1 §3 |
| Valmeekam, Marquez, Kambhampati, 2023, arXiv | `valmeekam2023selfcritique` | LLM verifier accepts 38 of 45 invalid plans (false positives) | RQ1 (FP/FN) | B1 §3 |
| Stechly, Valmeekam, Kambhampati, 2025, ICLR | `stechly2025selfverification` | self-critique fails, sound verification helps | RQ1 | B1 §3 |
| Stechly, Marquez, Kambhampati, 2023, arXiv | `stechly2023gpt4wrong` (new) | same weakness on graph colouring | RQ1 | today |
| Huang et al., 2024, ICLR | `huang2024selfcorrect` | no self-correction without external feedback | RQ1 | B1 §3 |
| Gundawar et al., 2024, arXiv (workshop paper) | `gundawar2024travel` (new) | LLM-Modulo applied to travel planning | RQ1 | today |
| La Malfa et al., 2026, arXiv v2 | `lamalfa2026endtoend` | closest agentic LLM and PDDL system; LLM-judged success | RQ1, RQ3 | B1 §3 |
| Göbel et al., 2026, arXiv | `gobel2026agentic` | MCP simulator tools, no planner; token cost per solution | RQ1, RQ2 | B1 §3 |
| Corrêa, Pereira, Seipp, 2025b, NeurIPS | `correa2025heuristics` (new) | LLM writes heuristics, planner does the search | context | today |
| Schick et al., 2023, NeurIPS | `schick2023toolformer` | learned tool invocation | RQ2 context | bib header |
| Qin et al., 2024, ICLR | `qin2024toolllm` | large API collections | RQ2 context | bib header |
| Anthropic, 2024 | `anthropic2024mcp` | the protocol our tools use | RQ2 context | bib header |
| Yao et al., 2023, ICLR | `yao2023react` | reasoning interleaved with tool actions | RQ2 context | bib header |
| Chen et al., 2023, TMLR | `chen2023pot` | offloading subproblems to programs | RQ2 context | bib header |
| Patil et al., 2025, ICML | `bfcl2025` | checks function and arguments; relevance against irrelevance items | RQ2 | B1 §3 |
| Yao et al., 2024, arXiv | `yao2024taubench` | multi-turn interaction between a tool-using agent and a user | RQ2 context | bib header |
| Luo et al., 2025, arXiv | `luo2025mcpuniverse` | real MCP servers, execution-based evaluators | RQ2, RQ3 | B1 §3 |
| Wang et al., 2026, ICLR | `wang2026mcpbench` | live MCP servers; rules plus an LLM judge | RQ2 | B1 §3 |
| Guo et al., 2025, arXiv | `guo2025mcpagentbench` | MCP testbed with an LLM-judge method | RQ2 | B1 §3 |
| Liu et al., 2025, arXiv | `liu2025mcpagentbench` | distractor tools to test selection | RQ2 | B1 §3 |
| Huang et al., 2024b, ICLR | `huang2024metatool` | whether to use a tool and which one | RQ2 | B1 §3 |
| Ross et al., 2025, NAACL | `ross2025when2call` | when not to call | RQ2 | B1 §3 |
| Qian et al., 2025, Findings of ACL | `qian2025smart` | tool overuse | RQ2 | B1 §3 |
| Xu et al., 2024, arXiv | `xu2024relign` (new) | selection errors against usage errors, as two types | RQ2, RQ3 | today |
| Zhang et al., 2024, arXiv | `zhang2024toolbehonest` (new) | hallucination diagnosis for tool-augmented models | RQ2 | today |
| Chen et al., 2023, arXiv | `chen2023teval` (new) | tool use scored step by step, including understanding and review | RQ3 | today |
| Li et al., 2023, EMNLP | `li2023apibank` (new) | planning, retrieving and calling APIs over dialogues | RQ3 | today |
| Tam et al., 2024, arXiv | `tam2024speakfreely` (new) | format restrictions lower reasoning performance | RQ3 (answer format) | today |
| Kapoor et al., 2026, ICLR | `kapoor2026hal` | accuracy against dollar and token cost | cost reporting | B1 §3 |
| Benyamin et al., 2025, arXiv | `benyamin2025copilot` | our group's preliminary version | all three | B1 §4 |

53 papers. Key clash to resolve when these go into a bib file: `chen2023pot` (existing)
and `chen2023teval` (new) are different first authors named Chen, and `huang2024selfcorrect`
and `huang2024metatool` are different first authors named Huang.

## 9. To verify

Wanted, but not checked against the paper yet, so not cited above.

1. **Katz et al., 2025, guidelines for LLM planning research.** Corrêa et al. say they
   follow them (validate every plan, generate fresh tasks, compare with strong planners).
   Our own design should be set against the same guidelines.
2. **The IPC 2023 learning track overview** (cited by Corrêa et al. as Taitler et al.,
   2024). Needed if the larger problems of PR #138 are used.
3. **Metric-FF** (the numeric planner of the earlier version) and **LAMA, DecStar,
   Scorpion Maidu** (Corrêa's baselines). Section 2.3 names the three planners without a
   citation.
4. **Venues of T-Eval and ToolBeHonest.** The arXiv records give none. Both are cited
   above as arXiv papers.
5. **The Communications of the ACM version of Corrêa et al.** Listed on Seipp's lab page;
   volume, issue and pages are not checked (`draft_B1_B2_related_work.md` §2).
6. **More work for RQ3.** A search for studies of whether a model's final answer is
   faithful to a tool result or to retrieved context (the retrieval-augmented generation
   literature has such measures), and for studies of copying long structured outputs.
   Section 6 is thin without them.
7. **Plan quality of LLM-written plans** (RQ1, fourth metric). The only quality measure
   in the works above is LLMFP's optimal rate. A search for studies that compare the
   length or cost of LLM plans with planner plans is still to do.
8. **SWE-agent (arXiv:2405.15793) and the SWE-bench leaderboard study
   (arXiv:2506.17208).** The memory notes list them as support for "the scaffold drives
   measured performance". Their claims were never checked.
9. **TravelPlanner**, the benchmark Gundawar et al. use, if Section 4.2 keeps that
   example.

## 10. Questions for Omer

1. **Depth of Section 1.** It is short on purpose. Should the thesis background also
   define the five tasks formally here, or does that belong to the experimental-setting
   section of the RQ1 chapter (M3)?
2. **Corrêa et al.'s numbers.** Section 2.3 quotes their headline counts (245 against
   234, and 231 under random names). The related-work draft for the paper left them out.
   Keep them in the thesis?
3. **Section 6.** Is an honest "this literature is thin" acceptable for the first
   draft, or should item 6 of the "To verify" list be done before you read it?
4. **Citation style.** Author and year in the prose with keys in the table. Say if the
   thesis doc needs another style.
