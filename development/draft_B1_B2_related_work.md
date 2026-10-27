# Draft: B1 (related work and Positioning) and B2 (the arXiv delta)

*Drafted 2026-10-27 for `weakness_action_plan.md` §4 B (B1, B2; settles C17). Nothing here
is in `paper/` yet. After Omer reads it, it goes in as one PR with the other B drafts.*

**How to read this file.** §1 is the LaTeX for §2 of the paper, ready to paste. §2 is the
BibTeX for the new references. §3 is the check behind every reference. §4 is the B2
paragraph and where each of its numbers comes from. §5 lists the questions for Omer.

**About the evidence column in §3.** Each claim is checked against the paper's own text.
The table gives the location (section, table or figure) and the numbers exactly, but
describes the wording in my own words. I only quote a few words verbatim, because of a
limit on how much copyrighted text I can reproduce. The text at each location can be read
from the URL given.

---

## 1. Drafted text (LaTeX)

Replaces `paper/main.tex` lines 193 to 273 (`\section{Background and Related Work}` up to
`\section{Methodology}`). The first paragraph of the section (lines 196 to 207, "Automated
planning studies how to find ...") stays as it is and is not repeated here.

```latex
\section{Background and Related Work}

% Opening paragraph unchanged (paper/main.tex lines 196-207).

\subsection{LLMs as Planners and as Plan Checkers}
PlanBench \citep{valmeekam2023planbench} gives a model a planning problem in natural
language, asks it for a plan, and checks the plan with VAL. Prompted this way, even strong
LLMs fall well short of a classical planner. \citet{kambhampati2024llmmodulo} argue from
this evidence that autoregressive LLMs cannot plan or verify their own plans by
themselves, and propose LLM-Modulo frameworks, in which the model works in a loop with
sound external verifiers. Our study tests a simpler arrangement. The model may hand a
single task to a sound tool, and there is no generate-and-verify loop.

Reasoning models raised these scores without closing the gap on larger or obfuscated
problems. On PlanBench's $600$ Blocksworld problems, o1-preview produced a correct plan for
$97.8\%$, but for $52.8\%$ of the obfuscated Mystery Blocksworld problems and $23.6\%$ of
$110$ larger Blocksworld problems \citep{valmeekam2024o1prelim}. The journal version of
that evaluation adds that the gains come with large and unpredictable inference costs, and
that o1 improves further inside a compound system with a sound verifier
\citep{valmeekam2025o1tmlr}.

Other benchmarks split planning into the judgments a planner makes along the way.
ACPBench \citep{kokel2025acpbench} generates boolean and multiple-choice questions from
PDDL for seven such tasks over $13$ domains, so every answer is provably correct. Two of
its tasks are close to ours. Progression asks how an action changes the state, which our
\emph{simulate} task asks for every step of a plan. Validation asks whether an action
sequence is a valid plan, as \emph{validate\_plan} does. With chain-of-thought prompting
and two examples, GPT-4o scored $52.5\%$ on the multiple-choice validation questions, its
lowest task. ACPBench Hard \citep{kokel2026acpbenchhard} asks open-ended versions of the
same tasks, scores each with a symbolic validator, and finds that with few exceptions
every tested model stays below $65\%$. In both benchmarks the model answers without tools.

A related line asks whether a model can check plans itself. With GPT-4 as both plan
generator and plan verifier on Blocksworld, the verifier accepted $38$ of $45$ invalid
plans, and the loop with this verifier solved $55$ of $100$ problems against $88$ with VAL
in its place \citep{valmeekam2023selfcritique}. \citet{stechly2025selfverification} extend
the analysis to three domains, STRIPS planning among them, and find that performance
collapses under self-critique and improves under sound external verification. Outside
planning, \citet{huang2024selfcorrect} report that LLMs struggle to correct their
reasoning without external feedback. Our \emph{validate\_plan} task asks the question
these studies ask, whether a given plan is valid. The difference is that the model may
pass the plan to a sound validator, and we record whether it does.

\subsection{LLMs as Planning Formalizers}
A second line uses the LLM as a formalizer. The model translates natural language into a
formal model, and a sound solver does the search. LLM+P \citep{liu2023llmp} pipelines an
LLM into a classical planner, and \citet{guan2023world} use LLMs to build world models for
model-based planning. Plansformer \citep{pallagani2022plansformer} fine-tunes a model for
plan generation, and \citet{silver2024generalized} apply pretrained LLMs to generalized
planning in PDDL domains. The survey by \citet{tantakoun2025survey} treats LLMs as tools
that write and refine planning models for off-the-shelf planners, and notes that
end-to-end planning by an LLM still lacks soundness guarantees.

\citet{huang2025limit} measure the limits of this approach with zero-shot prompting and no
tools. Models are largely robust to lexical perturbation of domain symbols, and
formalization degrades as the descriptions become more natural. On their obfuscated
Mystery Blocksworld, GPT-4o as a formalizer produced $70$ of $100$ correct plans against
$0$ of $100$ as a planner, graded with VAL. The advantage is not universal. o3-mini scored
$74$ of $100$ as a planner on the same data, and the authors describe the results as
mixed across models. Their work is the published starting point for our PlanBench
section, where we repeat the rescue result and add the control it was missing
(Section~\ref{sec:planbench}).

Two further results bear on how such pipelines are graded. Planetarium
\citep{zuo2025planetarium} checks generated PDDL problems for semantic equivalence with
the intended task. Zero-shot, $96.1\%$ of GPT-4o's problem files parse and $94.4\%$ are
solvable, yet only $24.8\%$ are correct, so solvability alone is a weak check on a
generated model. LLMFP \citep{hao2025llmfp} formalizes planning problems as optimization
problems for an SMT solver instead of PDDL. On Blocksworld and Mystery Blocksworld ($602$
queries each) it reaches optimal rates of $96.2\%$ and $77.7\%$ with GPT-4o, where direct
planning with the same model reaches $41.5\%$ and $0.8\%$.

Agentic systems wrap the solver in a loop. In the system of \citet{lamalfa2026endtoend},
an orchestrator LLM writes the PDDL domain and problem, agents refine them, and the
validated files are passed to an external planner. With GPT-5-mini it raises the average
PlanBench success rate from $76.6\%$ to $91.6\%$ over three runs of $50$ problems per
task, with GPT-5-mini as the judge of success. \citet{gobel2026agentic} expose a step-wise
PDDL simulator to Claude Haiku~4.5 over MCP and let the model choose one action at a time
until a plan validator accepts the plan. On $102$ IPC Blocksworld instances this agentic
setup solves $66.7\%$ against $63.7\%$ for direct planning, at $5.7$ times the token cost
per solution. Their tool set contains no planner, so the model does the search itself.

\subsection{Tool Use and the Decision to Call}
Equipping LLMs with external tools is now standard, from learned tool invocation
\citep{schick2023toolformer} to large API repertoires \citep{qin2024toolllm}. The Model
Context Protocol \citep[MCP;][]{anthropic2024mcp} standardizes how tools are described to
a model and how its calls are relayed, and it is how we expose planners and validators.
BFCL checks a model's calls against the expected function and arguments with an
abstract-syntax-tree method \citep{bfcl2025}, and $\tau$-bench measures multi-turn
tool-agent-user interaction \citep{yao2024taubench}. Benchmarks built on live MCP servers
extend this to many tools and long tasks. They score runs with execution-based evaluators
\citep{luo2025mcpuniverse} or with rule-based checks and an LLM judge
\citep{wang2026mcpbench, guo2025mcpagentbench}, and MCPAgentBench adds distractor tools to
test selection \citep{liu2025mcpagentbench}.

Fewer studies ask whether the model decides to call at all. BFCL separates items where a
call is expected from items where none is \citep{bfcl2025}. MetaTool
\citep{huang2024metatool} asks the model directly whether a query needs a tool and finds
that most models lack this awareness. When2Call \citep{ross2025when2call} poses a four-way
choice that includes a tool call, and builds its items so that answering directly is
always a hallucination. SMART \citep{qian2025smart} studies the opposite error, calling
tools for questions the model could answer from its own knowledge. In each of these the
right decision is fixed when the item is built. In our tasks a sound tool is always
relevant, but the model can often answer correctly without it. Whether it calls the tool
is a behavior we observe, and its cost is measured in the final answer.

A parallel line raises tool use through scaffolding, interleaving reasoning with tool
actions \citep{yao2023react} or offloading numeric subproblems to executable programs
\citep{chen2023pot}. HAL \citep{kapoor2026hal} evaluates agents across models and
scaffolds and reports accuracy against dollar and token cost. Our cost-of-pass analysis
follows that practice. Our setting is at the simple end of this range. Each task has one
relevant tool, and that tool is sound, so the closest analog is single-call function
selection.

\subsection{Positioning}
The planner and verifier studies above measure what a model does alone. The formalizer
pipelines and the system of \citet{lamalfa2026endtoend} measure what a model achieves
together with a solver, and the call to the solver is part of the pipeline.
\citet{gobel2026agentic} give the model simulator tools but no planner, and a run ends
when the validator accepts a plan. In each of these designs, either the model works
without tools or the call is built into the system, so how often a model calls a sound
tool that it is free to skip is not measured. The tool-calling benchmarks do measure that
decision, on items where the right choice is fixed in advance, and they score the
decision itself.

This paper measures two quantities on PDDL tasks with sound planning tools. The first is
how often a model calls the tool, both when the tool is merely available and when one
sentence asks for it. The second is how often a correct tool result reaches the model's
final answer, which a deterministic checker grades. We know of no earlier study that
reports the two separately for planning tasks. The closest is a preliminary study of an
earlier version of this tool suite \citep{benyamin2025copilot}, which folded both into
one success rate (Section~\ref{sec:prelim}). Our main tasks hand the model complete PDDL
files, so they do not test whether the model can write PDDL. We test that step on
PlanBench \citep{valmeekam2023planbench}, where the prompts are plain English and the
model must write the PDDL before it can call a planner. That section re-measures the
no-tools baseline against the published figures and compares the tools with a control
that keeps the same prompt and removes only the tools (Section~\ref{sec:planbench}).

\subsection{Relation to the Preliminary Study}
\label{sec:prelim}
% B2 paragraph: see Section 4 of this draft file.
```

### What changed against the current tex, and why

| current tex | draft | reason |
|---|---|---|
| "The present study is empirical evidence for exactly this division of labour" (line 214) | removed; replaced by "Our study tests a simpler arrangement ... no generate-and-verify loop" | C18 / B5: no generate-and-verify loop is tested, only single-call delegation |
| "treats the LLM not as the planner but as a formalizer" (line 218) | "uses the LLM as a formalizer" | "not X but Y" reversal |
| Tantakoun parenthetical: "the consensus is that pairing an LLM translator with a sound solver outperforms end-to-end LLM planning" (line 226) | the survey's framing (LLMs write models for planners) and its note that end-to-end LLM planning lacks soundness guarantees | the "consensus ... outperforms" claim is not in the survey; the replacement is (§3, row `tantakoun2025survey`) |
| Huang and Zhang: 70/100 vs 0/100 only | adds that o3-mini scored 74/100 as a planner and that the authors call the results mixed | the verified caveat; without it the rescue reads as universal |
| La Malfa: "raise PlanBench averages by about 15 points" | the exact 76.6 to 91.6 for GPT-5-mini, and that success was judged by GPT-5-mini | exact figure; the LLM judge matters for Positioning |
| "This literature largely studies the generation of PDDL ... We instead evaluate ..." (lines 238 to 241) | moved into Positioning, rewritten | the old sentence carried an "instead" reversal and a claim now stated more narrowly |
| Positioning: "none measures what a model gains when a sound planner or validator is available as a callable tool ..." (line 261) | "how often a model calls a sound tool that it is free to skip is not measured"; "We know of no earlier study that reports the two separately for planning tasks"; the preliminary study named as the closest | C17: the old claim was false given La Malfa et al. and our own arXiv version. The new claim is about the two gates only, and is true of every study cited |
| Positioning's list of our design features ("five single-tool-use PDDL tasks ... signed significance ...") | removed | the Introduction carries the contributions; "signed significance" is vocabulary E1 will decide on |
| "Our setting sits deliberately at the simple end of this spectrum: each task admits exactly one ... rather than long-horizon orchestration" (lines 252 to 255) | "Our setting is at the simple end of this range. Each task has one relevant tool ..." | colon reveal and "rather than" reversal |

New references: 18 (two o1 papers, ACPBench, ACPBench Hard, the self-critique paper, Stechly
et al., Huang et al. 2024, Planetarium, LLMFP, Göbel et al., MetaTool, When2Call, SMART, four
MCP benchmarks, HAL). Existing keys reused: `valmeekam2023planbench`,
`kambhampati2024llmmodulo`, `liu2023llmp`, `guan2023world`, `pallagani2022plansformer`,
`silver2024generalized`, `tantakoun2025survey`, `huang2025limit`, `lamalfa2026endtoend`,
`schick2023toolformer`, `qin2024toolllm`, `anthropic2024mcp`, `bfcl2025`, `yao2024taubench`,
`yao2023react`, `chen2023pot`, `benyamin2025copilot`.

Style check on §1 and §4 (run on this file): no em-dashes; one "instead of" (LLMFP, a plain
description of what it formalizes into); no "not X but Y"; no "notably", "crucially",
"striking", "load-bearing".

---

## 2. BibTeX for the new references

Append to `paper/refs.bib`. Every field below was checked against the source named in §3.

```bibtex
% ---------------------------------------------------------------- reasoning models, self-verification
@misc{valmeekam2024o1prelim,
  title         = {{LLMs} Still Can't Plan; Can {LRMs}? A Preliminary Evaluation of {OpenAI}'s o1 on {PlanBench}},
  author        = {Valmeekam, Karthik and Stechly, Kaya and Kambhampati, Subbarao},
  year          = {2024},
  eprint        = {2409.13373},
  archivePrefix = {arXiv}
}
@article{valmeekam2025o1tmlr,
  title   = {A Systematic Evaluation of the Planning and Scheduling Abilities of the Reasoning Model o1},
  author  = {Valmeekam, Karthik and Stechly, Kaya and Gundawar, Atharva and Kambhampati, Subbarao},
  journal = {Transactions on Machine Learning Research},
  year    = {2025},
  note    = {Preprint: arXiv:2410.02162, ``Planning in Strawberry Fields''}
}
@misc{valmeekam2023selfcritique,
  title         = {Can Large Language Models Really Improve by Self-critiquing Their Own Plans?},
  author        = {Valmeekam, Karthik and Marquez, Matthew and Kambhampati, Subbarao},
  year          = {2023},
  eprint        = {2310.08118},
  archivePrefix = {arXiv}
}
@inproceedings{stechly2025selfverification,
  title     = {On the Self-Verification Limitations of Large Language Models on Reasoning and Planning Tasks},
  author    = {Stechly, Kaya and Valmeekam, Karthik and Kambhampati, Subbarao},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2025}
}
@inproceedings{huang2024selfcorrect,
  title     = {Large Language Models Cannot Self-Correct Reasoning Yet},
  author    = {Huang, Jie and Chen, Xinyun and Mishra, Swaroop and Zheng, Huaixiu Steven and Yu, Adams Wei and Song, Xinying and Zhou, Denny},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2024}
}

% ---------------------------------------------------------------- planning benchmarks
@inproceedings{kokel2025acpbench,
  title     = {{ACPBench}: Reasoning about Action, Change, and Planning},
  author    = {Kokel, Harsha and Katz, Michael and Srinivas, Kavitha and Sohrabi, Shirin},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {39},
  number    = {25},
  pages     = {26559--26568},
  year      = {2025},
  doi       = {10.1609/aaai.v39i25.34857}
}
@inproceedings{kokel2026acpbenchhard,
  title     = {{ACPBench Hard}: Unrestrained Reasoning about Action, Change, and Planning},
  author    = {Kokel, Harsha and Katz, Michael and Srinivas, Kavitha and Sohrabi, Shirin},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2026},
  note      = {arXiv:2503.24378}
}
@inproceedings{zuo2025planetarium,
  title     = {{Planetarium}: A Rigorous Benchmark for Translating Text to Structured Planning Languages},
  author    = {Zuo, Max and Piedrahita Velez, Francisco and Li, Xiaochen and Littman, Michael L. and Bach, Stephen H.},
  booktitle = {Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)},
  pages     = {11223--11240},
  year      = {2025},
  doi       = {10.18653/v1/2025.naacl-long.560}
}

% ---------------------------------------------------------------- formalizers and agentic planning
@inproceedings{hao2025llmfp,
  title     = {Planning Anything with Rigor: General-Purpose Zero-Shot Planning with {LLM}-based Formalized Programming},
  author    = {Hao, Yilun and Zhang, Yang and Fan, Chuchu},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2025}
}
@misc{gobel2026agentic,
  title         = {Agentic {LLM} Planning via Step-Wise {PDDL} Simulation: An Empirical Characterisation},
  author        = {G{\"o}bel, Kai and Lorang, Pierrick and Zips, Patrik and Gl{\"u}ck, Tobias},
  year          = {2026},
  eprint        = {2603.06064},
  archivePrefix = {arXiv}
}

% ---------------------------------------------------------------- the decision to call a tool
@inproceedings{huang2024metatool,
  title     = {{MetaTool} Benchmark for Large Language Models: Deciding Whether to Use Tools and Which to Use},
  author    = {Huang, Yue and Shi, Jiawen and Li, Yuan and Fan, Chenrui and Wu, Siyuan and Zhang, Qihui and Liu, Yixin and Zhou, Pan and Wan, Yao and Gong, Neil Zhenqiang and Sun, Lichao},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2024}
}
@inproceedings{ross2025when2call,
  title     = {{When2Call}: When (not) to Call Tools},
  author    = {Ross, Hayley and Mahabaleshwarkar, Ameya Sunil and Suhara, Yoshi},
  booktitle = {Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)},
  pages     = {3391--3409},
  year      = {2025},
  doi       = {10.18653/v1/2025.naacl-long.174}
}
@inproceedings{qian2025smart,
  title     = {{SMART}: Self-Aware Agent for Tool Overuse Mitigation},
  author    = {Qian, Cheng and Acikgoz, Emre Can and Wang, Hongru and Chen, Xiusi and Sil, Avirup and Hakkani-T{\"u}r, Dilek and Tur, Gokhan and Ji, Heng},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2025},
  pages     = {4604--4621},
  year      = {2025},
  doi       = {10.18653/v1/2025.findings-acl.239}
}

% ---------------------------------------------------------------- MCP benchmarks, agent evaluation
@misc{luo2025mcpuniverse,
  title         = {{MCP-Universe}: Benchmarking Large Language Models with Real-World Model Context Protocol Servers},
  author        = {Luo, Ziyang and Shen, Zhiqi and Yang, Wenzhuo and Zhao, Zirui and Jwalapuram, Prathyusha and Saha, Amrita and Sahoo, Doyen and Savarese, Silvio and Xiong, Caiming and Li, Junnan},
  year          = {2025},
  eprint        = {2508.14704},
  archivePrefix = {arXiv}
}
@inproceedings{wang2026mcpbench,
  title     = {{MCP-Bench}: Benchmarking Tool-Using {LLM} Agents with Complex Real-World Tasks via {MCP} Servers},
  author    = {Wang, Zhenting and Chang, Qi and Patel, Hemani and Biju, Shashank and Wu, Cheng-En and Liu, Quan and Ding, Aolin and Rezazadeh, Alireza and Shah, Ankit and Bao, Yujia and Siow, Eugene},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2026},
  note      = {arXiv:2508.20453}
}
@misc{guo2025mcpagentbench,
  title         = {{MCP-AgentBench}: Evaluating Real-World Language Agent Performance with {MCP}-Mediated Tools},
  author        = {Guo, Zikang and Xu, Benfeng and Zhu, Chiwei and Hong, Wentao and Wang, Xiaorui and Mao, Zhendong},
  year          = {2025},
  eprint        = {2509.09734},
  archivePrefix = {arXiv}
}
@misc{liu2025mcpagentbench,
  title         = {{MCPAgentBench}: A Real-world Task Benchmark for Evaluating {LLM} Agent {MCP} Tool Use},
  author        = {Liu, Zixiang and Liu, Wenrui and Dai, Elsie and Yu, Wenhan and Yu, Lei and Yang, Tong and Han, Jinjun and Gao, Hong},
  year          = {2025},
  eprint        = {2512.24565},
  archivePrefix = {arXiv},
  note          = {Version 5; accepted to the REALM workshop at EMNLP 2026 (per the arXiv record)}
}
@inproceedings{kapoor2026hal,
  title     = {Holistic Agent Leaderboard: The Missing Infrastructure for {AI} Agent Evaluation},
  author    = {Kapoor, Sayash and Stroebl, Benedikt and Kirgis, Peter and Nadgir, Nitya and Siegel, Zachary S. and Wei, Boyi and Xue, Tianci and Chen, Ziru and Chen, Felix and Utpala, Saiteja and Ndzomga, Franck and Oruganty, Dheeraj and Luskin, Sophie and Liu, Kangheng and Yu, Botao and Arora, Amit and Hahm, Dongyoon and Trivedi, Harsh and Sun, Huan and Lee, Juyong and Jin, Tengjun and Mai, Yifan and Zhou, Yifei and Zhu, Yuxuan and Bommasani, Rishi and Kang, Daniel and Song, Dawn and Henderson, Peter and Su, Yu and Liang, Percy and Narayanan, Arvind},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2026},
  note      = {arXiv:2510.11977}
}
```

The existing `benyamin2025copilot` entry is correct as it stands (title, four authors,
arXiv:2509.12987; checked against the arXiv record, v1 is the only version).

---

## 3. Verification table

Checked 2026-10-27 unless the status says otherwise. "arXiv record" means the arXiv API
metadata (title, authors, versions, comments field). Venue checks used the ACL Anthology
BibTeX, the AAAI OJS page, the PMLR page or the ML Anthology entry. OpenReview could not
be used: it now puts a bot check in front of every page and its API, and I did not try to
get past it. For the three ICLR 2026 papers the claims were checked against the arXiv
version named.

| key | full reference | URL | claim we use | evidence and location | status |
|---|---|---|---|---|---|
| `valmeekam2023planbench` (existing) | Valmeekam, Marquez, Olmo, Sreedharan, Kambhampati. PlanBench. NeurIPS 2023 Datasets and Benchmarks. arXiv:2206.10498 | https://arxiv.org/abs/2206.10498 | plans are checked with VAL; strong LLMs fall well short of a planner | App. A.2: Fast Downward is the planner and VAL the plan validator. Table 1: GPT-4 206/600 (34.3%) on Blocksworld plan generation. Conclusion: subpar LLM performance even in simple common-sense domains | verified |
| `kambhampati2024llmmodulo` (existing) | Kambhampati et al. Position: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks. ICML 2024, PMLR 235. arXiv:2402.01817 | https://arxiv.org/abs/2402.01817 | autoregressive LLMs cannot plan or self-verify by themselves; LLM-Modulo pairs them with external model-based verifiers in a loop | Abstract: the authors argue LLMs cannot by themselves do planning or self-verification, and present LLM-Modulo frameworks that combine LLMs with external model-based verifiers in a bi-directional interaction | verified |
| `valmeekam2024o1prelim` | Valmeekam, Stechly, Kambhampati. LLMs Still Can't Plan; Can LRMs? A Preliminary Evaluation of OpenAI's o1 on PlanBench. arXiv:2409.13373 (2024) | https://arxiv.org/abs/2409.13373 | o1-preview 97.8% on 600 Blocksworld, 52.8% on Mystery, 23.6% on 110 larger problems | §3 ("Evaluating LRMs on the Original Test Set") and Table 2: 587/600 (97.8%) Blocksworld, 317/600 (52.8%) Mystery Blocksworld. §3 and Fig. 3: 23.63% on 110 problems of 6 to 20 blocks needing 20 to 40 steps | verified (arXiv only, v1) |
| `valmeekam2025o1tmlr` | Valmeekam, Stechly, Gundawar, Kambhampati. A Systematic Evaluation of the Planning and Scheduling Abilities of the Reasoning Model o1. TMLR 2025. Preprint arXiv:2410.02162 ("Planning in Strawberry Fields") | https://mlanthology.org/tmlr/2025/valmeekam2025tmlr-systematic/ | gains come with large and unpredictable costs; o1 improves further in a compound system | TMLR abstract (via ML Anthology): LRM queries have large and unpredictable costs; o1's performance improves further when embedded in compound systems that scale inference separately. The arXiv preprint names these "LRM-Modulo" systems with a sound verifier | verified (abstract level; TMLR PDF behind the OpenReview bot check) |
| `kokel2025acpbench` | Kokel, Katz, Srinivas, Sohrabi. ACPBench: Reasoning about Action, Change, and Planning. AAAI 2025, 39(25):26559-26568. arXiv:2410.05669 | https://ojs.aaai.org/index.php/AAAI/article/view/34857 | 7 tasks, 13 domains, boolean and MCQ generated from PDDL; progression and validation tasks; GPT-4o 52.5% on validation MCQ, its lowest | Abstract (7 reasoning tasks over 13 domains; provably correct solutions). "ACPBench Tasks", items 2 (Progression: outcome of an action) and 5 (Validation: whether a sequence is a valid plan). §1: GPT-4o with CoT and 2-shot reaches 78.40% on MCQ overall, lowest 52.50% on validation | verified (text checked on arXiv v3, Feb 2026; venue and pages from ML Anthology and the AAAI page) |
| `kokel2026acpbenchhard` | Kokel, Katz, Srinivas, Sohrabi. ACPBench Hard: Unrestrained Reasoning about Action, Change, and Planning. ICLR 2026. arXiv:2503.24378 | https://arxiv.org/abs/2503.24378 | open-ended versions of the same tasks, a symbolic validator per task, almost all models below 65% | Abstract: generative open-ended questions, validation algorithms for each task, with a few exceptions all models score below 65%. §1: validators built from the symbolic description | verified (arXiv v2; ICLR 2026 from ML Anthology and the arXiv comment) |
| (both ACPBench papers) | | | "In both benchmarks the model answers without tools" | Neither evaluation section describes tool access. ACPBench prompts with 2-shot CoT (§1); ACPBench Hard prompts models and scores answers with its validators | my reading of the setups; no explicit sentence |
| `valmeekam2023selfcritique` | Valmeekam, Marquez, Kambhampati. Can Large Language Models Really Improve by Self-critiquing Their Own Plans? arXiv:2310.08118 (2023) | https://arxiv.org/abs/2310.08118 | GPT-4 verifier accepted 38 of 45 invalid plans; loop with LLM verifier 55/100 vs 88/100 with VAL | §5.2 and Table 2: 38 false positives, 38/45 (84.45%); verifier right on 61 of 100. §5.1 and Table 1: LLM+LLM with backprompting 55/100, LLM+VAL 88/100, generator alone 40/100 | verified (arXiv only; no venue found) |
| `stechly2025selfverification` | Stechly, Valmeekam, Kambhampati. On the Self-Verification Limitations of Large Language Models on Reasoning and Planning Tasks. ICLR 2025. arXiv:2402.08115 | https://mlanthology.org/iclr/2025/stechly2025iclr-selfverification/ | three domains incl. STRIPS planning; performance collapses with self-critique and improves with a sound external verifier | Abstract: GPT-4 on Game of 24, Graph Coloring and STRIPS planning; significant collapse with self-critique and significant gains with sound external verification | verified |
| `huang2024selfcorrect` | Huang, Chen, Mishra, Zheng, Yu, Song, Zhou. Large Language Models Cannot Self-Correct Reasoning Yet. ICLR 2024. arXiv:2310.01798 | https://mlanthology.org/iclr/2024/huang2024iclr-large/ | LLMs struggle to self-correct reasoning without external feedback | Abstract: LLMs struggle to self-correct without external feedback, and performance sometimes degrades after self-correction | verified |
| `tantakoun2025survey` (existing) | Tantakoun, Muise, Zhu. LLMs as Planning Formalizers: A Survey ... Findings of ACL 2025, 25167-25188. arXiv:2503.18971 | https://aclanthology.org/2025.findings-acl.1291/ | LLMs as tools that write and refine planning models for off-the-shelf planners; end-to-end LLM planning lacks soundness guarantees | Abstract: positions LLMs as tools for formalizing and refining planning specifications for off-the-shelf planners. §3 opening: end-to-end LLM planning still falls short of soundness guarantees | verified. The old tex claim ("consensus ... outperforms end-to-end") is **not** in the survey and is dropped |
| `huang2025limit` (existing) | Huang, Zhang. On the Limit of Language Models as Planning Formalizers. ACL 2025 (Long), 4880-4904. arXiv:2412.09879 v4 | https://aclanthology.org/2025.acl-long.242/ | zero-shot, no tools; robust to lexical perturbation; worse as text gets more natural; GPT-4o Mystery 70/100 formalizer vs 0/100 planner, VAL; o3-mini 74/100 as planner; results mixed | Abstract (lexical perturbation; decrease as descriptions become more natural). Table 3 (Heavily Templated MysteryBlocksWorld-100): gpt-4o 70/100 formalizer correctness, gpt-4o as planner 0/100; o3-mini as planner 74/100. §5 text: superiority extends to gpt-4o-mini but not o3-mini; results mixed across models | verified (re-read v4 today; also verified 2026-08-06) |
| `zuo2025planetarium` | Zuo, Piedrahita Velez, Li, Littman, Bach. Planetarium. NAACL 2025 (Long), 11223-11240. arXiv:2407.03321 v2 | https://aclanthology.org/2025.naacl-long.560/ | semantic-equivalence check; GPT-4o zero-shot 96.1% parse, 94.4% solvable, 24.8% correct | Abstract: the three figures for GPT-4o; §1 contributions: 24.8% correct in the zero-shot setting | verified (also 2026-08-06) |
| `hao2025llmfp` | Hao, Zhang, Fan. Planning Anything with Rigor (LLMFP). ICLR 2025. arXiv:2410.12112 | https://mlanthology.org/iclr/2025/hao2025iclr-planning/ | optimization problems for an SMT solver; GPT-4o optimal rate 96.2 / 77.7 on Blocksworld / Mystery vs direct 41.5 / 0.8; 602 queries each | Table 2 (optimal rate, multi-step problems): Direct GPT-4o 41.5 / 0.8, LLMFP GPT-4o 96.2 / 77.7. §3 pipeline uses SMT. App. task descriptions: 602 queries per domain | verified (n and figures also 2026-08-06). Note: direct o1-preview reaches 88.4 / 31.9 in the same table; we do not quote it |
| `lamalfa2026endtoend` (existing) | La Malfa, Zhu, Marro, Bernardini, Wooldridge. End-to-end PDDL Planning with Hardcoded and Dynamic Agents. arXiv:2512.09629 v2 (8 May 2026) | https://arxiv.org/abs/2512.09629 | orchestrator writes PDDL, agents refine, validated files go to an external planner; GPT-5-mini PlanBench average 76.6 to 91.6; 3 runs x 50 per task; GPT-5-mini as judge | Abstract (pipeline). §4.1: 91.6 ± 1.6 vs 76.6 ± 23.2 for GPT-5-mini. Table 1 caption: three independent runs of 50 problems each. §4 setup: GPT-5-mini used as the judge | verified (figures also 2026-08-06; the judge is new today) |
| `gobel2026agentic` | Göbel, Lorang, Zips, Glück. Agentic LLM Planning via Step-Wise PDDL Simulation: An Empirical Characterisation. arXiv:2603.06064 | https://arxiv.org/abs/2603.06064 | MCP step-wise simulator, Claude Haiku 4.5; 102 IPC Blocksworld; 66.7 vs 63.7; 5.7x token cost per solution; no planner tool; run ends when the validator accepts | Abstract (all figures). §III-A: the seven tools, none a planner. §III-B: the agentic run continues until the plan-validation tool confirms a valid plan | verified |
| `huang2024metatool` | Huang et al. MetaTool Benchmark for LLMs: Deciding Whether to Use Tools and Which to Use. ICLR 2024. arXiv:2310.03128 | https://mlanthology.org/iclr/2024/huang2024iclr-metatool/ | asks the model directly whether a query needs a tool; most models lack this awareness | §2.3.1: the model is asked whether it needs a tool and must answer yes or no. §1 contributions and Conclusion: most LLMs lack good tool-usage awareness | verified |
| `ross2025when2call` | Ross, Mahabaleshwarkar, Suhara. When2Call: When (not) to Call Tools. NAACL 2025 (Long), 3391-3409. arXiv:2504.18851 | https://aclanthology.org/2025.naacl-long.174/ | four-way choice including a tool call; items built so a direct answer is always a hallucination | §2.1: answer types (a) direct answer, (b) tool call, (c) follow-up question, (d) unable to answer; all questions require tool use, so (a) is always a hallucination | verified |
| `qian2025smart` | Qian et al. SMART: Self-Aware Agent for Tool Overuse Mitigation. Findings of ACL 2025, 4604-4621. arXiv:2502.11435 | https://aclanthology.org/2025.findings-acl.239/ | tool overuse: calling tools for tasks solvable from parametric knowledge | Abstract: defines Tool Overuse as unnecessary reliance on tools for tasks solvable with parametric knowledge | verified |
| `bfcl2025` (existing) | Patil et al. The Berkeley Function Calling Leaderboard (BFCL). ICML 2025, PMLR 267:48371-48392 | https://proceedings.mlr.press/v267/patil25a.html | AST-based check of calls; relevance (a call expected) vs irrelevance (none expected) | Abstract: AST evaluation method. §3.1 and App. C: Relevance (at least one call expected), Irrelevance (tools available, no call expected) | verified (PMLR PDF) |
| `luo2025mcpuniverse` | Luo et al. MCP-Universe. arXiv:2508.14704 (2025) | https://arxiv.org/abs/2508.14704 | real MCP servers; execution-based evaluators | Abstract: 11 MCP servers in 6 domains; execution-based evaluators | verified (arXiv only) |
| `wang2026mcpbench` | Wang et al. MCP-Bench. ICLR 2026. arXiv:2508.20453 | https://arxiv.org/abs/2508.20453 | live MCP servers, many tools, long tasks; rule-based checks plus an LLM judge | Abstract: 28 live servers, 250 tools. Fig. 1 caption: trajectories scored by rule-based checks and LLM-as-a-Judge | verified (arXiv v1; ICLR 2026 from ML Anthology) |
| `guo2025mcpagentbench` | Guo, Xu, Zhu, Hong, Wang, Mao. MCP-AgentBench. arXiv:2509.09734 (2025) | https://arxiv.org/abs/2509.09734 | 33 servers, 188 tools, 600 queries; LLM-judge evaluation (MCP-Eval) | Abstract (testbed size; MCP-Eval). §1: MCP-Eval is an LLM-as-a-judge method | verified. The ID flagged "UNVERIFIED" in the 08-06 notes is correct |
| `liu2025mcpagentbench` | Liu et al. MCPAgentBench. arXiv:2512.24565 v5 | https://arxiv.org/abs/2512.24565 | candidate tool lists with distractors to test selection | Abstract: dynamic sandbox presents candidate tool lists containing distractors | verified (arXiv; workshop venue per the arXiv comment only) |
| `kapoor2026hal` | Kapoor et al. Holistic Agent Leaderboard. ICLR 2026. arXiv:2510.11977 | https://arxiv.org/abs/2510.11977 | evaluates agents across models and scaffolds; reports accuracy against dollar and token cost | Abstract: three-dimensional analysis of models, scaffolds and benchmarks. §1, contribution 2: Pareto frontiers of accuracy versus cost, both dollar and token | verified (arXiv v1; ICLR 2026 from ML Anthology) |
| `benyamin2025copilot` (existing) | Benyamin, Mordoch, Shperberg, Stern. Toward PDDL Planning Copilot. arXiv:2509.12987 (2025), v1 only | https://arxiv.org/abs/2509.12987 | see §4 | see §4 | verified |

Existing references whose claims are unchanged and were not re-checked today:
`liu2023llmp`, `guan2023world`, `pallagani2022plansformer`, `silver2024generalized`,
`schick2023toolformer`, `qin2024toolllm`, `anthropic2024mcp`, `yao2024taubench`,
`yao2023react`, `chen2023pot` (all verified 2026-06-14 per the `refs.bib` header).

**Looked at, verified, and not used** (metadata checked on the arXiv record; say if you
want any of them): Stechly, Valmeekam, Kambhampati, "Chain of Thoughtlessness? An Analysis
of CoT in Planning", NeurIPS 2024, arXiv:2405.04776; Gundawar et al., "Robust Planning
with LLM-Modulo Framework: Case Study in Travel Planning", arXiv:2405.20625; Shojaee et
al., "The Illusion of Thinking", NeurIPS 2025, arXiv:2506.06941; Stechly, Marquez,
Kambhampati, "GPT-4 Doesn't Know It's Wrong", arXiv:2310.12397.

**Dropped:** none. Every reference the plan named was found and checked.

---

## 4. B2: the arXiv delta

### The paragraph (LaTeX; also reused in the cover letter, F3)

```latex
\citet{benyamin2025copilot} introduced the Planning Copilot, which exposes planners, a
plan validator and a plan simulator to an LLM over MCP. They tested three open-weight
models (Qwen3 at 0.6B and 4B, and GPT-OSS-20B) with and without these tools on the five
task types studied here. With tools, the success rate rose in $14$ of the $15$
model-task cells. On \emph{solve} it went from $0.04$ to $0.78$ for Qwen3-4B and from
$0.28$ to $0.78$ for GPT-OSS-20B, and no model simulated a plan correctly without tools.
The evaluation was preliminary. It used $250$ single-task queries in all, reported the
better of each model's thinking and non-thinking runs, gave no confidence intervals, and
had no control for memorized domains. Its tool-arm system prompt told the model that
calling tools was its only way to solve a task, and a tool-arm trial counted as a success
only if the model had called the correct tool and its final answer was right. Calling and
delivery were therefore folded into one number. The present paper grades $273{,}600$
open-weight trials over two corpora, with confidence intervals and an anonymized-domain
control, and adds a pre-registered study. It confirms the main direction. Tools raise the
rate of correct delivered plans by $51.7$ to $71.0$ points for the three open models of
the pre-registered study, and frontier models go from $22$--$29\%$ unaided to $95\%$ with
the planner. Unaided simulation is again
close to zero ($0$ of $3{,}000$ answers in the exact format under the shared output
budget), but with the budget and format relaxed, models from 4B up get $22$ to $40\%$ of
trajectories right. The paper changes the reading in two places. First, a model may skip a
tool that is merely available. Gemma-MoE-26B called the plan validator in $21\%$ of
\emph{validate\_plan} trials, against $94\%$ when one sentence in the user turn asked it
to. Having the tool available did not lower its delivered accuracy ($89.2\%$ against
$88.3\%$ unaided; difference $+0.9$ points, 95\% CI $[-1.2, 2.9]$). Second, a correct tool
result does not always reach the final answer. On \emph{simulate} the trajectory returned
by the tool left the model no room to answer in $42.7$ to $53.0\%$ of tool-arm trials, and
Gemma-MoE-26B's delivered score with tools fell $15.7$ points below its unaided score
(95\% CI $[-24.7, -6.7]$).
```

### Sources for every statement

About arXiv:2509.12987 (read in full, v1, 16 Sep 2025; PDF text):

| statement | location in arXiv:2509.12987 |
|---|---|
| tools exposed over MCP: classical and numeric planner, validator, simulator | "The Planning Copilot" (Solve, Validate, Simulate use cases); "Implementation Details": Fast Downward and Metric-FF, an MCP wrapper of VAL, a plan simulation script |
| three open-weight models: qwen3:0.6b, qwen3:4b, gpt-oss:20b | "Implementation Details"; Table 1 rows |
| five task types | "Experimental Design" (single-request tasks 1 to 5); Table 1 columns |
| 14 of 15 cells rose; the exception Qwen3-4B Val. dom. 0.42 to 0.34 | Table 1 (computed from the 15 pairs) |
| solve 0.04 to 0.78 (qwen3:4b), 0.28 to 0.78 (gpt-oss:20b) | Table 1 |
| no model simulated without tools | Table 1 (Simulate 0.00 for all three without tools); "Results: Single Task Comparison", first paragraph |
| 250 single-task queries (10 problems x 5 prompt variants x 5 requests) | "Experimental Design" |
| better of thinking and non-thinking reported | "Experimental Design", end of the first paragraph |
| no confidence intervals | Table 1 and the text give point rates only |
| no control for memorized domains | "Experimental Design": ten public domains (five IPC classical, four IPC 2023 numeric, one non-IPC); no renamed or held-out variant is described |
| tool-arm system prompt: tools are the only way to solve | Figure 2 |
| success needed the correct tool call and a right final answer | "Experimental Results", evaluation paragraph: answers checked with VAL and the simulator, then by hand for the final result given to the user; tool-arm cases count only when the correct tools were used |

About this paper (every figure from `development/NUMBERS.md`):

| figure in the paragraph | NUMBERS.md section and row | note |
|---|---|---|
| 273,600 open-weight trials over two corpora; anonymized-domain control | "Corpus scale"; "Abstract — the four figures", scale-clause row | five open-weight models; never paired with "seven models" |
| +51.7 to +71.0 delivered solve, three open models | "Delivered rerun — readout (FROZEN 2026-10-09)", row "E2 solve delivered, tools-plain − unaided" (+71.0 / +64.3 / +51.7) | Study 2; separate-apparatus replication |
| frontier 22–29% to 95% | "Abstract — the four figures", row "frontier plan generation" | delivered, both frontier tiers |
| 0 of 3,000 format-exact under the shared budget; 22–40% content-correct at ≥4B when decoupled | "Job 2 — the delivered surface", last row (open-roster unaided simulate) | the qualifier is mandatory; carried in the sentence |
| Gemma 21% vs 94% calling on validate_plan | "Abstract — the four figures", row "invocation on plan checking"; the same counts (622/3,000 and 2,808/3,000) are in the new "Study 1 — main sweep figures" block, row "Gemma validate_plan calling" | Study 1 (`sweep5v2-live`), steering is the user-turn sentence (v14–16). No interval quoted; if one is added, use the clustered [9.0, 34.1] / [84.0, 100.0] from the Study 1 block, never the Wilson interval |
| 89.2 vs 88.3, +0.9, 95% CI [−1.2, 2.9] | "Delivered rerun — readout", row "R1"; CI level from `reference/delivered_rerun_readout.md` line 208 | registered reading "No delivered harm" |
| no-room share 42.7–53.0% of tool-arm simulate trials | "Delivered rerun — readout", row "E1 simulate delivered, tool arms" | the range over the three models' tool arms |
| Gemma simulate −15.7, 95% CI [−24.7, −6.7] | "Delivered rerun — readout", row "E2 simulate, Gemma" | Holm p 0.018 (not quoted) |

The paragraph quotes no tool-verified figure as a delivered one and does not use the
retired open-model delivered ranges. Study 1 (calling) and Study 2 (delivered) figures sit
in separate sentences and are not combined into one number.

---

## 5. Open questions for Omer

1. **Where B2 goes in the paper.** I made it its own short subsection at the end of §2
   ("Relation to the Preliminary Study", `\label{sec:prelim}`, which Positioning points
   to). The other options are the last paragraph of Positioning, or the Introduction.
2. **The "scored by tool selection" description is not quite what the arXiv paper did.**
   Its text says final answers were also checked (with VAL, the simulator, and by hand),
   and the correct tool call was an extra requirement. The draft says this: success
   needed both, so calling and delivery were folded into one number. The same correction
   applies to the memory note and to the cover letter. Is this the framing you want?
3. **The tool suite changed after the arXiv version.** That paper used Metric-FF for
   numeric planning and a VAL wrapper. Ours uses ENHSP and validators on
   `unified-planning`. The tex (line 314) says the suite "packages the Planning Copilot
   tools" of the arXiv paper. The draft says "an earlier version of this tool suite".
   Should B3/B4 state the change, and should B2 mention it?
4. **Calling figures in B2.** I used Study 1's 21% to 94% (the abstract's figures). Study 2
   has its own: 20.0% plain and 93.1% steered (R5 table). Using Study 2 would keep the
   whole Gemma passage inside one study. Which one?
5. **Self-citation wording after de-anonymizing (F1).** The draft says "a preliminary study
   of an earlier version of this tool suite", in the third person. Under JAIR, once
   de-anonymized, it could say "the preliminary version of this work". Your call when F1
   happens.
6. **Model name.** The draft uses "Gemma-MoE-26B" as the tex does now. E1 fixes the
   vocabulary, so this may change.
7. **The two Qwen validate_plan gains** (+14.2 for the 9B and +7.4 for the 35B, readout E2)
   would show that skipping the tool is model-specific. They are not in `NUMBERS.md` yet,
   so the draft leaves them out. Add a row and a clause?
8. **MCP benchmarks.** MCP-Universe and MCP-AgentBench are arXiv only. MCPAgentBench is a
   workshop paper (REALM at EMNLP 2026, per its arXiv record). MCP-Bench is ICLR 2026.
   Keep all four, or only MCP-Bench and MCP-Universe?
9. **HAL** is cited once, for reporting accuracy against cost. Keep it or drop it?
10. **The Introduction (lines 123 to 133) repeats the old three-lines framing**, including
    "has not been answered cleanly". It should match the new Positioning when E rewrites
    the Introduction. I did not touch it.
11. **Optional references** (listed under §3, verified, not used): Chain of Thoughtlessness,
    LLM-Modulo for travel planning, The Illusion of Thinking. Add any?
12. **Thinking mode in B2.** The arXiv paper reported the better of each model's two
    modes. The new Study 1 block in `NUMBERS.md` (added today by the C2 work, not yet
    committed) has Gemma's validate_plan calling falling from 20.7% to 0.6% with thinking
    on. One sentence on this would show why reporting modes separately matters. Add it
    once that block is final? (Study 2's D3 measures it again on the fixed setup.)
