# Prompt for the next session

*Written 2026-11-26, about 08:15 UTC (10:15 cluster time). Paste the block below into a
new session. Delete this file when its tasks are tracked in `STATUS.md`.*

---

We are finishing the PDDL Copilot paper for ICAPS 2027 (abstract 7 December, paper 14
December, main track, 8 pages plus references, with a supplementary PDF). Read
`CLAUDE.md`, `development/STATUS.md`, `development/paper_outline.md` and the entries of
2026-11-25 and 2026-11-26 at the end of `development/paper_notes_discussions.md` before
you do anything. First run `git pull` in the main checkout: `main` was cleaned up on
2026-11-26 (PRs #152 and #153) and the local checkout may be behind.

**Where we stand.** Three runs are out or about to be. Nothing of any of them has been
read. No pull request is open.

**1. The matched run (open models, cluster).** Job 24502726, submitted 2026-11-26 07:09
cluster time, six cells, 5,400 trials. At 09:48 three cells were complete (Gemma-26B
both, Qwen3.6-35B no tools) and three were running; it should end around 13:00.
Registration and frozen analysis are on `main`: `development/reference/matched_run_prereg.md`,
`tools/reanalysis/matched_run.py`, package hash `1f3d0f84…`. The three complete cells
may already be copied to `results/matched-run/`.
What to do, in this order, when all six cells are COMPLETED:
- have an Opus cluster agent at medium effort copy the remaining folders, serve logs and
  job logs to `results/matched-run/`, with filters that cannot show a trial outcome
  (ask me before any cluster step; I may be disconnected);
- run the frozen analysis with `--i-have-frozen` and the registered hash; if a tripwire
  fires, audit it as the registration says before reading on;
- write the readout (`development/reference/matched_run_readout.md`), the `NUMBERS.md`
  entry, and fill sections 9 and 11 of the registration (job ids, dates, restarts);
- bring me the readout before anything goes near the paper.
Rule that holds until then: while the run is unfinished only job states and row counts
are read (registration, section 7). I asked on 2026-11-26 to look at the finished cells
early; the session held that back because it would be a registered deviation and the
frozen analysis refuses an incomplete run anyway. If I still want the early look, say
what it costs once more and then do it as a declared deviation in section 11.

**2. The Claude run (Haiku 5.5 and Sonnet 5.5).** 18,240 trials, started 2026-11-26
about 07:20 UTC from the worktree `.claude/worktrees/frontier55` (branch
`frontier/claude-55-run`, not on `main`), writing to `results/frontier55/`. The runner
stops itself at 60 dollars (Haiku) and 430 dollars (Sonnet); expected total 255 to 305
dollars, plus 11.43 for the pilot. Registration:
`development/reference/frontier55_prereg.md` on that branch.
- The run was started as background processes of the previous session and may have
  died with it. Check with `pgrep -fl tools.frontier55.runner` and the row counts in
  `results/frontier55/*/trials.jsonl` (4,560 per folder when done). If a model is not
  finished and no process is alive, start the same three commands again for that model
  (`batch-submit`, `live`, `batch-fetch --wait`, with the same `--out`, `--gt-cache`,
  `--marketplace-path external/pddl-copilot-5e4f9c0` and `--max-usd`); they resume and
  never resend a batch. A leftover `.lock` in a folder is removed by hand. Both arms of
  a model are meant to fall on the same UTC day; if they do not, apply the rule of the
  registration's section 6.
- Do not edit `tools/frontier55/*.py` until the run is complete: the run's manifest pins
  their hashes.
- **Do not open the rows.** The analysis for this run is not written. Write it (same
  grade as the matched run on solve and simulate, the October run's grade on the three
  validation tasks, the rules of the registration for refusals and error rows), pass the
  five freeze gates with an independent review, freeze it, and only then read the data.
  Then open a PR for the branch.

**3. GPT and hosted Qwen.** I chose `gpt-6.2-sol` and, as an anchor to our own roster,
the same weights as the local Qwen3.6-35B hosted at full precision (Novita). The runners, their
tests (366 checks) and a registration draft are written and committed on branch
`frontier/gpt-qwen-run` (worktree `.claude/worktrees/hosted-models`, commits `102458f`
and `33cc879`; `development/reference/hosted_gpt_qwen_prereg.md`), with no request ever
sent to either provider. Estimated cost: GPT 261 to 453 dollars (ceiling 927), Qwen
about 56 (ceiling 158). Still to do: an independent review as for the Claude runner,
my answers to the draft's open questions (GPT's output cap counts its hidden reasoning,
so keep 8,192 and 6,144 or raise them; prompt caching off for GPT; which OpenAI tier,
since the lowest paid tier has a 500-dollar monthly cap; what to do if the Qwen host
refuses temperature 0), then the itemized cost in chat, a pilot, the full run. Needed from me first: API keys
in my shell as `OPENAI_API_KEY` and `NOVITA_API_KEY` (not set on 2026-11-26), and my
word on GPT at reasoning "low" (it cannot be turned off).

**4. After the runs.** Rebuild the RQ1 tables and figures for solve and simulate on the
matched run. Remove the four extension models and the gpt-oss flags from
`cluster-experimenting/` and fix the script headers (deferred from the clean-up). Read
the cluster's tool library versions and set them beside the laptop's in the Claude
registration. Back up `results/control-promptfix`, the pilots, `results/matched-run*`
and `results/frontier55*` as checkpoint zips. Check whether ICAPS asks for the
Reproducibility Checklist.

**The paper.** Outline only: `development/paper_outline.md`. I write the prose myself.
`paper/main.tex` carries about thirty `% TODO(Omer)` marks where a sentence points at
material that moved to `paper/supplement_source.tex`. Decided on 2026-11-26: the Claude
results stay in a small section of their own for now; RQ3 quotes the registered
trace-loss range with the other reading in one clause; PlanBench stays in the body.

**How I want you to work.** You are the orchestrator: keep your own context for
decisions and hand cluster work to an Opus agent at medium effort, one clear task at a
time. Ask me before every cluster step. Before any paid request, show me the itemized
cost; stop and ask if an estimate passes 500 dollars. Do not read an outcome before its
analysis is frozen. Talk to me the way a colleague would across a table: what a result
means for the three questions first, then the number, then the caveat.
