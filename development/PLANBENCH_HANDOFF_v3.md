# PlanBench — handoff for v3 (make the small-model tools arm work)

Session close 2026-06-07. **v2 (the MCP-tools-on arm) is BUILT and
CHARACTERIZED.** This session ran a series of smokes that mapped exactly how the
tools arm behaves across model sizes and found the wall. The next session's
chosen direction (user): **give the small open models another try, likely via a
workflow framework (CrewAI / LangGraph / AutoGen) that scaffolds the
NL→PDDL formalization** the small models can't do free-form — preferably one
that supports pddl-copilot-style skills + MCP natively.

Branch: `planbench-integration`. Both repos. Pull before starting.
Predecessors: `development/PLANBENCH_HANDOFF_v2.md` (v2 build), `planbench_v1_results.md` (v1).

---

## TL;DR — what we know now

- **The tools arm mechanism WORKS** — proven on **t3 (plan verification) with
  qwen3.6:35b: 2/3 correct**, calling `validate_plan` and emitting clean
  verdicts that grade right. First clean end-to-end PDDL-Copilot result on
  PlanBench.
- **The wall is NL→PDDL formalization, not reasoning.** PlanBench gives natural
  language; the model must formalize it to PDDL before any tool helps. Small
  open models (4B/9B) produce malformed/wrong PDDL → tool errors → retry loop →
  truncate to empty → no answer. The *reasoning* (planning/verifying) is offloaded
  to the tool — so fixing formalization is the whole game.
- **`num_predict` is NOT the lever.** 4096→8192 just doubled rambling with the
  same `length` truncation; the 4B prose-spirals to fill any budget (16K wouldn't
  help). No-tools single-turn is clean at 8192; the *tool loop* induces the spiral.
- **Prompt strength matters.** A soft "you *may* use tools" nudge → capable
  models (9B/35B) ignore the tools and answer directly. The paper's FORCING
  directive (`pddl_eval.prompts.WITH_TOOLS_SYSTEM`) makes them use the tools.
- **Tension:** the models that *need* tools (small, prose-penalised by
  exact-match grading) can't formalize to use them; the one that *can* formalize
  (35B) mostly already follows the format without tools. v3 is about closing that
  gap for the open models.

Full dated detail: `development/paper_notes_discussions.md` (2026-06-06 / 06-07
entries: num_predict probe, cross-size tool usage, forcing-prompt t3/t7,
cost/provider + small-model-fix analysis).

---

## What's built + on disk (v2 — all committed/pushed on `planbench-integration`)

- **`planbench/engine.py`** — three vLLM backends in the engine name
  `pddl_copilot__<backend>__<model>`:
  - `vllm` — v1 single-call no-tools (the frozen 4096 leaderboard corpus).
  - `vllm-base` — byte-identical no-tools, **distinct engine name** → own
    results dir (the v2 no-tools baseline; keeps v1 untouched).
  - `vllm-tools` — the MCP tool-loop: persistent module-level event loop +
    lazily-connected `MCPPlanner` (connect ONCE, run each instance via
    `run_until_complete` — the sync/async bridge), reuses
    `pddl_eval.chat.chat_with_tools` + `VLLMClient`. FORCING, task-aware system
    prompt (`_tools_system_prompt()`): paper `WITH_TOOLS_SYSTEM` + NL→PDDL step
    + per-task format (PDDL_COPILOT_TASK: t3→verdict/validate_plan,
    t7→state/get_state_transition, else→[PLAN]/classic_planner). Per-instance
    tool-call side-log (`PDDL_COPILOT_TOOLLOG` + stderr). `PDDL_COPILOT_NUM_PREDICT`
    overrides the 4096 floor. All v2 deps lazy-imported inside the tools branch.
- **`planbench/setup.sh --tools`** — builds a separate `.venv-tools`
  (openai≥1.0 + mcp) on a python≥3.10 base, leaving v1's `.venv` (openai<1.0)
  frozen. Guards: errors loudly if the chosen python is <3.10.
- **`cluster-experimenting/run_planbench_tools_rtx.sbatch`** — v2 sbatch:
  vLLM self-deploy + `module load anaconda; source activate pddl_copilot`
  (python3.12 + Java) + `.venv-tools` + marketplace/plugin pre-warm + engine
  `pddl_copilot__vllm-tools__<tag>` + PDDL_COPILOT_TASK per task.
- **`cluster-experimenting/submit_planbench.sh`** — flags: `--tools` (tools
  sbatch), `--base` (vllm-base on the v1 sbatch), `--num-predict N`,
  `--gpu/--gpu-mem-util/--time` (existing).

Commits this session (oldest→newest): `6ec3171` v2 engine+sbatch ·
`fea64ee` python≥3.10/conda fix · `8d7be3e` smoke-validated + blockers ·
`7965da1` num_predict override · `1aa35ff` vllm-base + --base · `1c8ee0d`
forcing task-aware prompt + t3/t7 · `820a6b6` cross-size finding ·
`451418a` num_predict probe · (+ this handoff).

---

## The smoke results that map the arm (all N=3, blocksworld, instances 2/3/4, 8192)

| model | tool use (forcing prompt) | result |
|---|---|---|
| Qwen3.5:4B | tries (9× planner), malformed PDDL | prose **spiral** → truncate; 0/3 |
| Qwen3.5:9B | uses validate_plan ×5-6 | **formalization wall** → retry loop → empty; t3 eval crashed (all-empty) |
| qwen3.6:35b t3 | validate_plan ×1-3 | **2/3 correct**, clean verdicts |
| qwen3.6:35b t7 | mostly 0 calls (answers directly) / 1 truncated | 0/3 (verbose-state grader) |

Pre-forcing (soft "may use" nudge): 9B/35B called **zero** tools on t1 and
answered directly (35B correct without tools).

---

## v3 — the chosen direction: scaffold formalization with a workflow framework

**Why a framework.** The small models fail because they have to *self-drive* the
formalize→validate→fix→answer loop and they can't. A deterministic workflow
takes that orchestration out of the model's hands — the model only does narrow
sub-tasks (write the problem; fix this specific error), the framework runs the
loop and calls the MCP tools. This is the "decompose + scaffold" fix below,
expressed as code instead of as a prompt the model must follow.

**The fix for small models (this session's analysis — it's a formalization
fix, layered, each kills one observed failure mode):**
1. **Inject the fixed domain** (blocksworld's domain is part of the spec) → the
   model writes only the *problem* (objects/init/goal), a small templated task.
   Biggest single lever. (Methodology: this is a labeled variant — "given PDDL"
   vs "given a planner" — not the same condition; legitimate for rescuing small
   models since the domain isn't theirs to re-derive. Flag it as such.)
2. **Grammar-constrain the PDDL output** (vLLM guided decoding; the harness
   already has `guided_json`/`format` plumbing in `pddl_eval/vllm_client.py`) →
   guarantees *syntactically* valid PDDL, killing the parse-error→retry→truncate
   loop. Semantics still on the model.
3. **Few-shot NL→PDDL example(s)** in the prompt — small models follow patterns.
4. **Validator-feedback fix-loop + stop sequence + "call the tool once, then
   answer"** — curbs the prose-spiral and the 5-6× re-validate churn.
Once PDDL is valid, the planner/validator produces the answer; the model only
formalizes + renders. **Floor:** 9B is the promising target; 4B borderline;
0.8B won't get there (the 9B looped without converging on validator feedback —
it needs steps 2-4 most).

**Framework options + tradeoffs:**
- **CrewAI / LangGraph / AutoGen** — model-agnostic (open models via the
  vLLM OpenAI-compatible endpoint we already deploy), support MCP tools and
  deterministic workflow graphs. "Skills like pddl-copilot natively": these
  frameworks don't have the SKILL.md progressive-disclosure concept, so you'd
  **wire the pddl-copilot MCP servers as tools** and **replicate the
  pddl-author / pddl-fixing skill text as agent roles / node prompts.**
  LangGraph gives the most explicit control-flow graph (best for the staged
  formalize→validate→fix→solve→render pipeline); CrewAI is role/agent-oriented;
  AutoGen is conversation-oriented.
- **Claude Agent SDK / Managed Agents** — *natively* supports Skills (the
  Skills API) + MCP, but **Claude-only** (not open small models). Right choice
  only if pivoting to Claude (see cost analysis below); wrong for the
  small-open-model retry.

**Suggested workflow shape (LLM-as-formalizer, staged — each node deterministic):**
`NL prompt` → `formalize problem (domain injected, grammar-constrained,
few-shot)` → `validate_problem` → (fix-loop on validator error, bounded) →
`classic_planner` (t1/t2) or `validate_plan` (t3) or `get_state_transition`
(t7) → `render answer in PlanBench format`. The model touches only the
formalize and fix and render steps; the framework owns the loop + tool calls.

**Integrating with PlanBench (keep the harness contract):** the framework
workflow replaces the engine's per-instance tool-loop. Cleanest: a **new
engine backend** (e.g. `pddl_copilot__vllm-crew__<model>`) whose `send_query`
drives the workflow once per instance and returns the final text — same
single-`send_query`-per-instance contract PlanBench expects, same
separate-namespace discipline as `vllm-tools`/`vllm-base`. Reuse the
PDDL_COPILOT_TASK env to pick the per-task pipeline + output format.

---

## If instead pivoting to Claude (cost/provider analysis, this session)

- Pricing (per 1M): **Sonnet 4.6 $3 in / $15 out; Haiku 4.5 $1 / $5.**
- Per-instance (tool-using, with caching): **Sonnet ~$0.12–0.30, Haiku
  ~$0.04–0.10.** Scope: 1 task × blocksworld (500) = Sonnet $60–150 / Haiku
  $20–50; full v2 (~9 tasks × ~785 ≈ 7,000) = Sonnet $850–2,100 / Haiku
  $280–700. **Calibrate on ~20 instances for real numbers before committing.**
- **Provider: first-party Claude API > Bedrock** for the batches+caching combo
  (Bedrock's batch is a separate AWS API; Claude Platform on AWS is the
  AWS-billing middle option with full parity).
- **Batches (50% off) do NOT fit the multi-turn tool/pddl-author loop** — a
  batch item is single-shot. Tools arm = run live + caching (no batch discount),
  or build a turn-staged batch pipeline (complex, day-scale latency). Batches
  only cleanly help the no-tools single-shot arm.
- Claude formalizes natively (no scaffolding needed) — so the choice is
  "engineer the scaffolding to rescue open models (cheap inference, more work,
  capped quality)" vs "pay per-token for Claude (no scaffolding, higher
  quality)." Comparing both roads is itself a paper-worthy result.

---

## Carry-forward blockers / lessons (DON'T re-learn these)

- **`build_table.py:67` drops instances with no `llm_correct` field** (empty /
  loop-exhausted) from the denominator → **overstates the tools arm** exactly
  where it fails hardest. Fix the denominator (attempted-but-empty = incorrect)
  before any full-table tools comparison.
- **`response_evaluation.load_json` asserts the response file exists** →
  crashes (rc=1) when ALL targeted instances come back empty (nothing written).
  Handle for the tools arm (a grader/infra robustness gap, distinct from the
  apply_patches t3 fixes).
- **Run PlanBench jobs SERIALLY** — concurrent jobs race on the shared-tree
  rsync at job end (benign exit 23, but corrupts the OUT_DIR). One arm at a time,
  or rsync only the engine's own subdir.
- **`slurm_*/` dirs are rsync COPIES of a shared accumulator, NOT extra runs.**
  Each sbatch ends with `rsync -a "$PLANBENCH_ROOT/plan-bench/results/"` (the
  shared, reused accumulator) into its own `results/planbench/slurm_<model>_<jobid>/`,
  so EVERY job dir snapshots EVERY engine ever run on the checkout — even though
  `manifest.json` proves one engine per job (staggered rsync-preserved mtimes +
  byte-identical md5 across jobs confirm copies, not re-runs). Two fallouts:
  (1) ~28G apparent of mostly-identical copies (pruned 5.9G→198M physical
  2026-06-15); (2) a naive `slurm_*/results/**/task_*.json` glob double-counts
  each model. **Never feed `build_table.py` a raw `slurm_*/results` dir** — and
  don't assume the foreign-engine subdirs in a job dir are fresh: a non-owner
  copy can be a STALE epoch (vllm__Qwen3.5:0.8B had two md5 generations). Use
  `planbench/canonicalize_results.py` (picks newest-mtime, owner-preferred copy
  per `(config,engine,task)`); see Quick repro / ops. A finishing in-flight job
  re-adds a bloated snapshot → re-run `--prune --apply` after pending jobs clear.
- **PlanBench caches responses by engine name** (`response_generation.py:70`
  skips instances with an existing non-empty `llm_raw_response`). A re-run at a
  new setting regenerates NOTHING unless you use a fresh engine name or clear
  the engine's task file. Use distinct engine names per variant (as vllm-base /
  vllm-tools do).
- **`.venv-tools` needs python≥3.10** for `mcp`; the cluster's only such python
  is the conda env `pddl_copilot` (3.12) — `module load anaconda; source
  activate pddl_copilot` (or `PLANBENCH_PYTHON=$HOME/.conda/envs/pddl_copilot/bin/python3`).
- **All v2 tools numbers are N=3 (smoke).** No robust tools-vs-no-tools claim
  until a real-N run with the blockers above fixed.
- t7's exact-match `text_to_state` grader is the known-bad cell (excluded from
  v1). t3 is the cleanest tools target.

---

## Cluster / repo state at handoff

- Cluster checkout `~/pddl-copilot-experiments` is on **`planbench-integration`**
  (switched FROM `feat/gpt-oss-120b-vllm` this session — that branch pointer is
  preserved at `eb3ddc0`; restore with `git checkout feat/gpt-oss-120b-vllm` if
  the gpt-oss work resumes). `.venv-tools` built (py3.12); plugin venvs
  (pddl-solver/pddl-validator) are py3.12 and present. Marketplace `~/pddl-copilot`
  on `main` (fine for t1/t3/t7 — needs no new MCP tools).
- Sibling `pddl-copilot` v2 MCP extensions (validate_plan_structured /
  optimal_plan, `specs-for-plan-bench.md`) specced but NOT built — only needed
  for the FULL 10-task v2, not for t3/t7 or the small-model retry.

## Quick repro / ops

```bash
# tools smoke (one model, t3+t7, fresh namespace, serial):
bash cluster-experimenting/submit_planbench.sh --tools --smoke --tasks t3 t7 \
     --models Qwen3.5:9B --gpu rtx_6000 --time 24:00:00 --num-predict 8192
# validate BY CONTENT: the toolcalls side-log (did the right tool fire? done_reason?),
#   not just exit status. Pull results/planbench/slurm_tools_<tag>_<jobid>/.
# re-apply patches after any pull (idempotent): python3 planbench/apply_patches.py external/LLMs-Planning

# --- de-dupe the per-job rsync copies (see lessons above) ---
# report duplication / reclaimable space (read-only):
python3 planbench/canonicalize_results.py results/planbench
# build ONE clean tree for build_table.py (symlinks; --copy for real files):
python3 planbench/canonicalize_results.py results/planbench --materialize /tmp/pb_canon
python3 planbench/build_table.py /tmp/pb_canon
# reclaim disk — dry-run, then --apply (safe: keeps newest copy per file;
#   never deletes manifest.json/toolcalls.jsonl). Re-run after in-flight jobs finish:
python3 planbench/canonicalize_results.py results/planbench --prune
python3 planbench/canonicalize_results.py results/planbench --prune --apply
```
