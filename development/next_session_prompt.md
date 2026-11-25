# Prompt for the next session

*Written 2026-11-25. Paste the block below into a new session. Run it with Fable 5.2 at
medium effort.*

---

We are finishing the PDDL Copilot paper for ICAPS 2027 (abstract 7 December, paper 14
December, main track, 8 pages of main content plus references, with a supplementary
PDF). Read `CLAUDE.md`, `development/STATUS.md`, `development/datasets_breakdown.md`
and the 2026-11-25 entries at the end of `development/paper_notes_discussions.md`
before you do anything.

**Where we stand.** The paper asks three questions: do the tools help, does the model
pick the right tool, and does it use what the tool returns. Most of what we need is
already clean in the October rerun: tool choice, the use of tool output, and the
tools-versus-no-tools comparison on the three validation tasks. One comparison is not
clean: tools against no tools on solve and simulate. The no-tools side was collected
seven weeks after the tool side. I decided to close that with one small run, and to
stop leading the paper with the May sweep.

**What I want from you, in this order.**

**1. The matched run.** Three models (Qwen3.5-9B, Gemma-26B, Qwen3.6-35B), thinking
off, solve and simulate only, three arms collected together in one job: no tools with
the format-stated system message, tools with the plain wordings, tools with the steered
wordings. 300 trials per model, task and arm, 5,400 in all. Write the registration
first, reusing the control's (`development/reference/control_prompt_fix_prereg.md`) and
its analysis, with the answer reader fixed before the run so that nothing is decided
after seeing data. Freeze the analysis, run a smoke, then the run. Ask me before every
cluster step; I approve the smoke and the full run separately. You are the
orchestrator: keep your own context for decisions and hand the cluster work to an Opus
agent at medium effort, one clear task at a time. Open questions for me are in
`development/unified_run_design.md` (A5 to A10 for this run, section B for the Claude
models, where I lean towards the newer 5 and 5.5 models).

**2. Clean the repository.** Go through the documentation, the scripts and the
explanations, and remove everything that is misleading, stale or no longer relevant to
the paper we are now writing. Be thorough: I want someone opening this repo to find the
current story and nothing that contradicts it. Follow the repo's rule (a doc that is no
longer needed is deleted and `MOVES.md` records the commit where it last existed).
Do not touch the registrations, the readouts, the frozen analysis packages or anything
a pinned hash covers, and do not rewrite the append-only logs. In the paper itself,
remove the sections that will certainly not survive into the 8-page version (the
Supporting Analyses as a section, the repair history in the results). Show me the list
before you delete, then do it in one PR.

**3. The paper: outline only.** Lay out the sections for the ICAPS version, put the
figures and tables where they belong, and stop. For each section give me a few lines on
what it has to establish and which numbers carry it. Do not write the prose; I will
write it myself, and more of it than fits. Do not aim at eight pages and do not trim
for length. I will write long and shorten later. From here on your part of the paper is
outlining and analysis.

**How I want the paper to read.** Clean results first. The earlier runs, the prompt
fault and the registered deviations go into the supplement in full, with one sentence
in the body that points there. Nothing is hidden, and nothing is apologised for twice.
Four things stay in the body as constraints and observed behaviour, not as defects: the
problems are small and the planner always solves them; the simulate tool answers in a
different notation and the context fills up; two of the three models are quantized; the
Claude models run under different conditions.

**How I want you to talk to me.** Write the way a colleague would explain it across a
table. When the language turns into harness and pipeline vocabulary, we end up
discussing the machinery and lose the science. Lead with what a result means for the
three questions, then the number, then the caveat if there is one.
