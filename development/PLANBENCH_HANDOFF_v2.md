# PlanBench — handoff for the v2 (MCP tools-on) arm

Session close 2026-06-06. **v1 (no-tools vanilla leaderboard) is DONE and
analyzed.** The next agent builds **v2 = the MCP-tools-on arm (ISS-022)**, with
the marketplace MCP plugins configured. This doc is self-contained — start here.

Branch: `planbench-integration` @ `7e2c0e0` (both repos). Pull before starting.

---

## TL;DR

- **v1 done:** 4 Qwen models × 10 PlanBench tasks × {blocksworld, logistics},
  no tools, graded by PlanBench's own VAL/PR2. Headline: **Qwen3.6-35B (open,
  no tools) matches/beats GPT-4 on 6 of 9 Blocksworld tasks.** Full writeup:
  `development/planbench_v1_results.md`. Reproducible table:
  `python3 planbench/build_table.py results/planbench/canonical`.
- **Decisions locked (see below):** Qwen models ONLY — **gemma4:26b-a4b is
  discarded for PlanBench** (do not run it on this benchmark). Domains =
  benchmark-shipped only (blocksworld + logistics). t7 excluded. No aggregate.
- **v2 = next:** add a `pddl_copilot_tools__<backend>__<model>` engine that
  routes PlanBench's per-instance `send_query` through `MCPPlanner`'s tool-loop
  (`pddl_eval/chat.py`), so the model can call the pddl-copilot MCP planner /
  validator before answering. The v1 finding (PlanBench's exact-match grading
  understates reasoning/prose models) is the motivation: tools return
  structured output, bypassing the prose-parsing penalty.

---

## Decisions locked this session (do not re-litigate)

1. **Qwen-only for PlanBench. gemma4:26b-a4b is DISCARDED for this benchmark.**
   (The 5-task `run_experiment.py` arm still uses gemma — this decision is
   scoped to PlanBench.) The active PlanBench roster is exactly:
   `Qwen3.5:0.8B  Qwen3.5:4B  Qwen3.5:9B  qwen3.6:35b`.
2. **Domains = benchmark-shipped only:** blocksworld (the only config with a
   published baseline) + logistics (our extra corpus). **depots dropped**
   (upstream ships only t1; generating the rest = net-new no-baseline data).
   No self-generated prompts.
3. **t7 (plan_execution) EXCLUDED from the table for every engine.** PlanBench's
   exact-match `text_to_state` parser can't read verbose/markdown output (35B's
   extracted state == ground truth + one stray scraped `clear`); the same parser
   graded gpt-4, so t7 is unfair for all. Never report t7=0 or fold it into an
   aggregate.
4. **No macro-mean / aggregate reported** — non-standard for PlanBench and
   t7-contaminated. Per-task only.
5. **Prompts specify output format only by ONE in-context example
   (completion-style), no explicit instruction.** So low vanilla scores are a
   completion-prompt-vs-chat-model mismatch, not stated-format disobedience.
   This is *the* reason v2 (tools = structured output) is the right next step.

---

## v1 final state (what's on disk)

**Data (cluster, canonical source of truth):**
`~/pddl-copilot-experiments/external/LLMs-Planning/plan-bench/results/` — our
4 qwen engines (`pddl_copilot__vllm__<tag>/task_*.json`) + PlanBench's committed
`gpt-4_chat` / `text-davinci-002` baselines. **Synced locally** to
`results/planbench/canonical/` (rsync of that tree).

> ⚠️ The per-job `results/planbench/slurm_<jobid>/` dirs are
> **cross-contaminated** (every job rsyncs the whole shared tree). Use the
> canonical tree / dedupe by (model, config, task). Do NOT trust per-job dirs.

**Provenance note (asked + verified):** gpt-4 / davinci numbers are PlanBench's
**own committed results** (`git`-tracked in `karthikv792/LLMs-Planning`,
committed by Valmeekam 2025-09). **We never called OpenAI / never had a key** —
`OPENAI_API_KEY` is a stub (`__planbench_stub__`) only so PlanBench imports.
Our 4 qwen columns were generated now by self-deployed vLLM on the cluster.

**Tooling:**
- `planbench/engine.py` — the v1 engine adapter (`pddl_copilot_send_query`,
  routes `pddl_copilot__vllm__<tag>` → one vLLM `/chat/completions` call).
- `planbench/apply_patches.py` — 5 idempotent patches to the LLMs-Planning
  checkout (import tolerance, dispatch branch, `--specific_instances` filter
  fix, **t3 grader robustness: KeyError + IndexError, comparability-preserving**).
- `planbench/build_table.py` — reproducible per-task accuracy table.
- `cluster-experimenting/{run_planbench_rtx.sbatch,submit_planbench.sh}` — vLLM
  self-deploy + per-(model,task) sharded submit; flags `--time`, `--gpu`,
  `--gpu-mem-util` (added this session).
- `development/planbench_v1_results.md` — the writeup (table + caveats).
- `development/paper_notes_discussions.md` — 2026-06-06 entries (headline +
  findings).

**Data hygiene already applied (all comparability-preserving):** t3 re-graded
offline after two upstream grader crashes; 2 smoke-contaminated cells
(0.8B/4B t1/blocksworld) re-graded over full responses. All cells now 500/285.

---

## v2 — the build (what the next agent does)

**Goal:** run the same PlanBench tasks but let the model consult the
pddl-copilot MCP tools (planner / validator) before answering — PlanBench stays
single-turn from its own perspective (it calls `send_query` once per instance;
the tool-loop happens *inside* that call). This is a *distinct method* per
PlanBench's INTEGRATION.md, not the vanilla leaderboard.

**1. New engine branch — `planbench/engine.py`.**
Add a `pddl_copilot_tools__<backend>__<model>` engine name. On dispatch, route
to a tool-loop instead of the single call, returning only the FINAL assistant
text to PlanBench. Reuse `pddl_eval/chat.py`:
- `MCPPlanner` (class at `pddl_eval/chat.py:79`): `await connect(plugin_dirs)`,
  `await call_tool(name, args)`.
- `chat_with_tools(...)` at `pddl_eval/chat.py:238` (`MAX_TOOL_LOOPS=10`) — the
  multi-turn loop the 5-task arm uses.
- Plugin discovery: `run_experiment.py:144 resolve_plugin_dirs(marketplace_path)`
  (marketplace = the `../pddl-copilot` clone, `PDDL_MARKETPLACE_PATH`).

**⚠️ Sync-bridge wrinkle (the main gotcha):** PlanBench calls `send_query`
**synchronously, per instance**, but `MCPPlanner` is **async with a persistent
MCP connection**. Do NOT `asyncio.run(...)` per instance (it would reconnect MCP
500×). Instead: open ONE module-level event loop + connected `MCPPlanner` on
first call (lazy init), and run each instance's tool-loop on that loop via
`loop.run_until_complete(...)`. Tear down at process exit.

**2. sbatch wiring — new `run_planbench_tools_rtx.sbatch` (or a flag).**
The v1 sbatch self-deploys vLLM. v2 additionally needs the MCP plugins
available: clone/point `PDDL_MARKETPLACE_PATH=$HOME/pddl-copilot`, and each
plugin's venv must be provisioned (see how the 5-task `run_condition_vllm_rtx.sbatch`
+ `run_experiment.py --marketplace-path` set this up — mirror it). The plugins
launch on demand via their `scripts/launch-server.sh`.

**3. Sibling-repo MCP extensions (gating the FULL 10-task v2):**
Spec: `../pddl-copilot/specs-for-plan-bench.md` (branch `planbench-integration`).
Two tools to add:
- `validate_plan_structured` (pddl-validator) — for t3 error-type grading.
- `optimal_plan` (pddl-solver) — for t2 cost-optimal grading.
**A t1-only tools smoke needs NEITHER** (existing `classic_planner` + validators
suffice) — build that first to validate the whole tool-loop path end-to-end
before the sibling-repo work.

**4. Validate like v1 did:** t1 tools-on smoke on a free rtx_3090
(`--gpu rtx_3090`), check by CONTENT (not exit status — depots-style rc=1 noise
won't apply here, but content-checks caught every real issue last time).

---

## Cluster / ops cheatsheet

```bash
# submit (qwen only!) — per-(model,task) shard, e.g. one cell:
bash cluster-experimenting/submit_planbench.sh --models Qwen3.5:0.8B --tasks t1 \
     --configs blocksworld --gpu rtx_3090 --gpu-mem-util 0.80 --time 08:00:00
# re-apply patches after any pull (idempotent; needed for grader fixes):
python3 planbench/apply_patches.py external/LLMs-Planning
# offline re-grade (CPU srun, no GPU) — pattern used for t3 / contamination fixes:
srun --partition=main --cpus-per-task=2 --mem=8G --time=00:30:00 bash -c '...response_evaluation.py...'
# sync canonical results down + build table:
rsync -az omereliy@slurm.bgu.ac.il:'~/pddl-copilot-experiments/external/LLMs-Planning/plan-bench/results/' results/planbench/canonical/
python3 planbench/build_table.py results/planbench/canonical
```
Cluster login `omereliy`; rtx_6000 is the corpus-identity GPU but was 100%
saturated earlier this week (sternron fairshare depleted) — small qwens fit a
free rtx_3090/4090 via `--gpu`. Monitor BY CONTENT.

---

## Open methodology items (not blocking v2)

- **Fairer vanilla eval** (optional ablation, NOT a v1 fix — diverges from how
  gpt-4 was graded): explicit format instruction or tolerant extractor would
  lift t1/t7/t8 for prose models. v2's structured tool output is the principled
  alternative.
- **t2 / t4 / t6** were first-run this session (only t1 was smoke-validated
  pre-sweep); they graded without crashing and the numbers look sane, but no
  one has spot-checked their graders the way t3/t7 were. Low priority.
- gemma4:26b-a4b PlanBench sweep — **explicitly dropped** (see decisions).

---

## Pinned commits (`planbench-integration`)

```
7e2c0e0  analysis(planbench): prompt-parity caveat + bw-t5 verification
8afbcde  analysis(planbench): v1 results table + findings
eb3ddc0  fix(planbench): t3 grader tolerates parser crashes (IndexError)
bfa0873  fix(planbench): t3 grader robust to non-adherent responses (KeyError)
6701ae5  fix(planbench): short --time on smoke (backfill)
07cb656  feat(planbench): --gpu / --gpu-mem-util on submit_planbench
f06f636  docs: v1 vanilla sweep launch (qwen subset, 40 jobs)
72220a3  docs: all-3-smokes validated (vLLM migration field-validated)
c478bbe  feat(planbench): PlanBench arm v1  (+ the Ollama→vLLM migration series)
```
Sibling repo (`pddl-copilot`): v2 MCP extensions specced but NOT yet built —
`specs-for-plan-bench.md`.
