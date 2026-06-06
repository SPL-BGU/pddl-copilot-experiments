# PlanBench arm — session handoff (2026-05-18)

Snapshot of where the PlanBench integration stands so the next session can resume cleanly. This is a working doc; once the smoke validates and the first real sweep lands, fold the resolved sections into `EXPERIMENTS_FLOW.md §13` / `CHANGELOG.md` and either delete this file or archive it.

---

## UPDATE 2026-06-02 — run-path migrated Ollama → vLLM (supersedes the Ollama sections below)

The 2026-05-18 arm was Ollama-based and landed the same day Ollama was retired harness-wide, so the run-path was orphaned (the `run_condition_rtx.sbatch` template it mirrored was deleted; the roster's `gemma4:26b-a4b` is a vLLM-only AWQ quant). **The smoke described below was never validated on Ollama and should not be.** The run-path was migrated to self-deployed vLLM — see CHANGELOG 2026-06-02. Everything below about the *PlanBench-side* bugs/patches (esp. the `--specific_instances` filter fix, bug #3) still stands — those are backend-independent.

**✅ ALL THREE SMOKES VALIDATED 2026-06-02 — migration fully field-validated; full vanilla sweep gate CLEARED.** Each passed all four criteria (vLLM ready + VRAM<guard; exactly 3 instances ran not 500 — filter fix #3's first-ever validation, after it burned all 3 Ollama smokes; non-empty `llm_raw_response`; `llm_correct` populated by VAL; `Overall rc: 0`). `--served-model-name`=canonical-tag wiring confirmed in serve logs.
- **Qwen3.5:0.8B** (job 17963891, rtx_3090, 78% VRAM) and **Qwen3.5:4B** (job 17963892, rtx_3090, 76% VRAM) — ran on free rtx_3090 via `--gpu rtx_3090 --gpu-mem-util 0.80` because the rtx_6000/pro pools were 100% allocated (sternron fairshare depleted).
- **gemma4:26b-a4b** (job 17964393, rtx_6000 ise-6000-02, pended ~5h then ran 7:21). Validated the divergent serve config: `--tool-call-parser gemma4 (no reasoning-parser) --max-num-batched-tokens 4096`, VRAM 42218/49140 (85%, guard edge). Confirms gemma needs rtx_6000 (won't fit a 24GB card).

**🚀 v1 VANILLA SWEEP LAUNCHED 2026-06-02 — qwen subset, in flight.** User decision: land v1 before v2 tools-on arm; **gemma4:26b-a4b deferred** ("qwens only"). Because ~15k gens/model (10 tasks × 3 configs × ~500 inst) blows the 48h walltime even for small models, the sweep is **sharded per (model, task)**: 4 qwens × 10 tasks = **40 jobs**, each = 1 model × 1 task × 3 configs × full instances (~1500 gens), per-model `--time` (0.8B 08h / 4B 10h / 9B 16h / qwen3.6:35b 24h — ~2× est, no timeout risk). All rtx_6000. **Job IDs 18003827–18003866** (`submit_planbench.sh --models <M> --tasks <T> --time <TT>` in a loop). They pend on the saturated rtx_6000 pool and drain as capacity frees (gemma's smoke pended ~5h before running, so expect a multi-day drain).

**To resume/check:** `squeue -u omereliy -h -o '%T' | sort | uniq -c` for queue state; `bash .claude/skills/cluster-ops/scripts/status.sh --bench planbench` for the completion matrix; `cluster-ops` skill for sync, `analyzer` for tables once corpora land. **Per-cell fault-tolerant** — a broken cell fails alone and the sweep continues. **Still owed:** gemma4:26b-a4b sweep (deferred), and the v2 tools-on arm (ISS-022).

---

## UPDATE 2026-06-06 — post-launch reconciliation: corpus scope + t3 grader + monitoring caveat

User caught a framing error ("how does it pass for the published benchmark?"). Reconciled against the upstream checkout — full write-up in `development/paper_notes_discussions.md` (2026-06-06 entry). Key operational facts:

- **Corpus scope DECISION (user 2026-06-06): benchmark-shipped domains only, no self-generated prompts, run as-is.** = blocksworld (10 tasks) + logistics (10) + **depots (t1 only)**. Upstream only ships depots t1; depots t2–t8 prompts were never created, so those cells fail at `response_generation.py:62` assert (fires *before* generation → ~0 GPU wasted). **We do NOT generate them.** No change to the running sweep — it already runs this way.
- **Comparison anchor = blocksworld only.** PlanBench's published baselines (gpt-4_chat etc.) are blocksworld(+blocksworld_3+mystery) only. logistics/depots have NO published baseline — they're our own extra corpus.
- **⚠️ MONITOR BY CONTENT, not exit status.** Every (model,task) job includes the depots config → every t2–t8 job exits **rc=1 / FAILED** from the depots assert even when blocksworld+logistics succeeded. `sacct` State is now a useless health signal. Check non-empty graded files per (model,config,task); a *real* failure (e.g. the cold-start vLLM `determine_available_memory` OOM that hit job 18003835, recovered as 18004379) hides among the depots-artifact FAILEDs otherwise.
- **t3 (plan verification) needs an OFFLINE re-grade — the one real fix, post-sweep.** `evaluate_verification.parse_output` only sets `'valid'` when the response contains the literal phrase `"plan is valid"`/`"plan is invalid"`; otherwise line 261 `KeyError: 'valid'` crashes the whole t3/config eval → zero t3 numbers. qwen3.5:0.8B emits prose without the verdict phrase (genuine non-adherence, the t1-style format-adherence signal — NOT a parser bug; gpt-4 followed the template upstream). Fix = uniform offline re-grade from saved responses (t3 generation succeeded), score "no verdict → incorrect" (comparability-preserving), report verdict-emission rate as a finding. Do NOT patch the grader mid-sweep (splits corpus identity). Check whether 4B/9B/35B adhere better than 0.8B by content as cells land.
- **Validated landing (job 18003830, 0.8B t4 — a "FAILED" job):** blocksworld task_2/4/5/6/7/8_1/8_3 = 500/500 graded; logistics (285 instances) all graded; t3 = KeyError (re-gradable); depots = no results. So a "FAILED" job is mostly-good data. Per-job `results/planbench/slurm_<jobid>/` dirs are cross-contaminated (jobs share `external/.../results/` and each rsyncs the whole tree) — dedupe by (model,config,task) at analysis time, don't trust per-job dir boundaries.

**New immediate next action (validate on the cluster):**

```bash
ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments \
    && git pull --ff-only origin planbench-integration \
    && python3 planbench/apply_patches.py external/LLMs-Planning \
    && bash cluster-experimenting/submit_planbench.sh --smoke"
```

`submit_planbench.sh --smoke` now self-deploys vLLM (`Qwen3.5:0.8B`, `--served-model-name` = canonical tag) on `rtx_6000:1`, engine name `pddl_copilot__vllm__Qwen3.5:0.8B`. Before submitting, verify cluster state: the checkout is on `planbench-integration` and `external/LLMs-Planning` is built (run `bash planbench/setup.sh` — idempotent — if unsure). The Ollama-specific resume commands below are obsolete.

---

## TL;DR

- **What's done:** PlanBench arm v1 (vanilla leaderboard, no MCP tools) is wired up end-to-end on cluster Linux. Adapter + setup + sbatch + cluster-ops status hook all committed on branch `planbench-integration` (both repos, pushed). Setup verified locally (engine smoke) and on the cluster (setup.sh ran clean, FD built, VAL+PR2 pre-built binaries work, slim venv up).
- **What's blocking real numbers:** three SLURM/PlanBench bugs were discovered and fixed in this session — only the last fix has not been validated by a successful smoke run yet.
- **Next action:** push the final fix (already done at this commit), pull on cluster, run `bash cluster-experimenting/submit_planbench.sh --smoke`. Expected runtime ~2-3 min for 3 instances.

---

## What this work is

`pddl-copilot-experiments` gets a second evaluation arm running the [PlanBench](https://github.com/karthikv792/LLMs-Planning) benchmark alongside (not replacing) the existing 5-task `run_experiment.py` matrix. Scope: all 10 PlanBench tasks × canonical Blocksworld + Logistics + Depots × our existing Ollama + vLLM model fleet. v1 is the vanilla leaderboard (no MCP tools during response generation); the tool-using arm is tracked as ISS-022 in OPEN_ISSUES.md.

Full methodology is in `EXPERIMENTS_FLOW.md §13`. Operator usage is in `planbench/README.md`.

Original brainstorm + plan-review-simplify ran 2026-05-17 → 2026-05-18 in the same session.

---

## State of the work

### Landed (committed + pushed on `planbench-integration` branch)

**This repo (`SPL-BGU/pddl-copilot-experiments`):**

- `planbench/` (new package)
  - `engine.py` — sync Ollama + vLLM adapter, engine-name format `pddl_copilot__<backend>__<model>`, double-underscore separators so Ollama-tag colons survive `.split('__')`.
  - `setup.sh` — idempotent provisioning: clones LLMs-Planning at HEAD of main, applies in-place patches via `apply_patches.py`, builds VAL (with macOS-skip), probes PR2, clones + builds Fast Downward `release-23.06.0`, creates a slim Python venv (prefers python3.12 for old-pin compatibility).
  - `apply_patches.py` — three anchored idempotent edits to the PlanBench tree (see "Patches applied" below).
  - `README.md` — operator commands + env-var table.
  - `__init__.py` — package marker.
- `cluster-experimenting/run_planbench_rtx.sbatch` — mirrors `run_condition_rtx.sbatch`'s Ollama self-deploy bootstrap on `rtx_pro_6000:1`, then loops `(task × config)` in-process. Skips PlanBench's prompt_generation stage (uses the pre-shipped `prompts/<config>/*.json`), calls `response_generation.py` and `response_evaluation.py` directly. Rsyncs results into `results/planbench/slurm_<model_tag>_<jobid>/`.
- `cluster-experimenting/submit_planbench.sh` — one-sbatch-per-model dispatcher; `--smoke` defaults to 1 model × t1 × blocksworld × instances `2 3 4`.
- `cluster-experimenting/lib/defaults.sh` — `PDDL_PLANBENCH_DEFAULT_TASKS`, `PDDL_PLANBENCH_DEFAULT_CONFIGS`, `PDDL_PLANBENCH_PATH`.
- `.claude/skills/cluster-ops/scripts/status.sh` — `--bench {5task,planbench}` selector. `5task` is bit-identical to prior behaviour (default).
- `.claude/skills/cluster-ops/scripts/status_planbench.sh` — minimal model × config completion-count matrix (no Δ-table / pace / ETA yet).
- `.claude/skills/cluster-ops/SKILL.md` — documents the new flag.
- `.gitignore` — adds `external/`.
- `EXPERIMENTS_FLOW.md` — new §13 (PlanBench arm methodology).
- `development/CHANGELOG.md` — 2026-05-18 entry.
- `development/OPEN_ISSUES.md` — new ISS-022 (v2 tool-using arm).
- `development/PLANBENCH_HANDOFF.md` — this file.

**Sibling repo (`SPL-BGU/pddl-copilot`, branch `planbench-integration`):**

- `specs-for-plan-bench.md` — defers the two v2 MCP plugin extensions (`validate_plan_structured` in pddl-validator for t3; `optimal_plan` in pddl-solver for t2) and explicitly drops the NL↔PDDL parser tool + pddl-author MCP exposure from scope. Doc-only; plugin code unchanged.

### Pre-shipped / cluster state

- Cluster checkout: `~/pddl-copilot-experiments` is on `planbench-integration` (HEAD pulled at end of session).
- `external/LLMs-Planning/` is cloned + patched + built; `external/downward/` is built. Both gitignored per host.
- Slim venv at `external/LLMs-Planning/.venv/` (python3 system, deps: pyyaml, tarski==0.7.0, pddl==0.2.0, numpy, openai<1.0, transformers, ollama, httpx).
- VAL binary: pre-built Linux ELF works on `ise-6000p-02` (rtx_pro_6000) out of the box.
- PR2 binary: pre-built 32-bit Linux ELF also works on this cluster (i386 compat libs present).
- Fast Downward built clean.

### Tests run

| Test | Result |
|---|---|
| Engine adapter smoke (laptop, qwen3:0.6b, direct call to `pddl_copilot_send_query`) | ✓ Returns text with `[PLAN END]` |
| End-to-end via `llm_plan_pipeline.py` (laptop) | ✓ 79/500 instances ran through PlanBench's pipeline; killed manually |
| `planbench/setup.sh` (cluster) | ✓ Clone + build + venv ok; deps importable |
| `pytest tests/` (existing 5-task harness) | not re-run this session, but zero `pddl_eval/` touches — should be green |
| Smoke sbatch (job 17628268) | ✓ Bootstrap clean, env vars carried through, INSTANCE_ARGS expanded right; **but** filter bug fell through anyway (see below) |
| Final patch (filter mutation fix) | applied locally; NOT yet validated on a sbatch run |

---

## Bugs discovered + how each was resolved

### 1. `--export=KEY=VAL,...` doesn't quote spaces → smoke ran all 500 instances

**Symptom.** First smoke (job 17627831) showed `0/500` progress bar, took ~22 min for 21% completion before user cancel.

**Root cause.** `submit_planbench.sh` built `EXPORTS="ALL,...,PLANBENCH_INSTANCES=2 3 4,..."`. SLURM `--export` splits on comma and does NOT honor quoting on individual values. The first whitespace-delimited token survives (`PLANBENCH_INSTANCES=2`) and the rest become stray positional args silently dropped by sbatch.

**Fix.** Commit `f15dee1` — pre-export env vars + use `--export=ALL` alone. (Did NOT resolve the issue; see next bug.)

### 2. `--export=ALL` alone doesn't carry user-defined env vars on this cluster

**Symptom.** Second smoke (job 17627993) ALSO ran all 500. `srun --jobid 17627993 --overlap bash -c 'echo PLANBENCH_INSTANCES="$PLANBENCH_INSTANCES"'` returned empty inside the allocation.

**Root cause.** This cluster's SLURM policy strips user-defined env vars under `--export=ALL` alone. Confirmed by an env-probe sbatch (job 17628234) that showed `--export=ALL,FOO=bar,LIST=a^b^c` (inline form) DOES carry user vars correctly. The inline `KEY=val` list survives; the bare `--export=ALL` does not. This matches why `submit_with_rtx.sh` encodes its `CELLS_LIST` as a `^`-separated string inline.

**Fix.** Commit `1c42cdf` — go back to the inline `--export=ALL,KEY=val,...` form, but encode multi-value lists with `^` separators (so no value contains a space). `run_planbench_rtx.sbatch` decodes `^` → ` ` before use. (Resolved the env-propagation issue; did NOT resolve the filter issue.)

### 3. PlanBench's `--specific_instances` filter is self-destructing (upstream bug)

**Symptom.** Third smoke (job 17628268) STILL ran all 500. Debug echoes added in commit `7d8662e` confirmed the env vars + python command line were correct:

```
[env-debug] decoded PLANBENCH_INSTANCES="2 3 4"
[env-debug] INSTANCE_ARGS=(--specific_instances 2 3 4)
[env-debug] python invocation: response_generation.py --task t1 --config blocksworld --engine pddl_copilot__ollama__Qwen3.5:0.8B --verbose False --specific_instances 2 3 4
```

**Root cause.** `LLMs-Planning/plan-bench/response_generation.py` filter logic in `get_responses` pops matched IDs off the list:

```python
if len(specified_instances) > 0:
    if instance['instance_id'] not in specified_instances:
        continue
    else:
        specified_instances.remove(instance['instance_id'])
```

With `specified_instances=[2,3,4]` and JSON entries indexed 2..501:
- entries 1, 2, 3 (ids 2, 3, 4): match, pop from list. After entry 3 the list is `[]`.
- entry 4 (id 5): `len([]) > 0` is **False** → guard skipped → falls through to `send_query`. Same for all remaining 497.

So the filter "works" until its last match consumes the list, then self-disables.

**Fix.** Commit at HEAD of this session — extend `planbench/apply_patches.py` with a third anchored idempotent edit (`patch_response_generation`) that:
1. Snapshots `specified_instances` to `_specified_instances_set` once at the top of `get_responses`.
2. Replaces the mutating filter with `if _specified_instances_set and instance['instance_id'] not in _specified_instances_set: continue`.

Validated: re-running `apply_patches.py` on the existing patched checkout applied the new patch and the first two correctly reported "already applied" (idempotency works). **NOT yet validated by a successful smoke run** — user wanted no further submits this session.

---

## What remains

### Immediate next action (validation)

```bash
ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments \
    && git pull --ff-only origin planbench-integration \
    && python3 planbench/apply_patches.py external/LLMs-Planning \
    && bash cluster-experimenting/submit_planbench.sh --smoke"
```

Note the `apply_patches.py` re-run is required — the existing cluster checkout already has the first two patches applied; without re-running, the third patch (filter fix) won't be in `response_generation.py`. The script is idempotent; the first two will report "already applied", the third will apply fresh.

**Expected runtime (vLLM path):** ~10-15 min total (vLLM cold-load of `Qwen/Qwen3.5-0.8B` ~3-5 min + 3 instances × a few s + VAL eval on 3 instances ~5s). Longer than the old Ollama estimate because the SIF build (first run) + HF download dominate.

**Validation criteria (vLLM-aware — the smoke is ALSO the first-ever test of two unvalidated things on this backend: the `--specific_instances` filter fix (bug #3, which burned the last 3 Ollama smokes by running all 500) and the empty-content failure mode that drove the num_predict-floor + stop-list fixes):**
1. **Serve healthy** — log shows `vllm ready (Ns)` and `VRAM after vLLM load ... (<85%)`.
2. **Filter fix holds** — only **3 instances actually ran**, not 500. The log's response_generation progress should hit 3 generated then skip the rest sub-second. (If 500 ran, patch #3 didn't apply — re-check the `apply_patches.py` re-run.)
3. **Non-empty content** — `results/planbench/slurm_Qwen3_5_0_8B_<jobid>/responses/blocksworld/pddl_copilot__vllm__Qwen3.5:0.8B/task_1_plan_generation.json` has 3 entries with **non-empty `llm_raw_response`** (the empty-content mode, now re-exposed under vLLM with `enable_thinking=false`).
4. **VAL ran** — the sibling `results/.../results/blocksworld/.../task_1_plan_generation.json` has `llm_correct` populated on those 3.

If content is empty or 500 ran, you know exactly which of the two histories repeated.

### After smoke validates

1. Remove the `[env-debug]` echoes from `run_planbench_rtx.sbatch` (commit `7d8662e`) once we're confident the pipeline is stable. They're informative but they were added explicitly to diagnose the filter bug — keep them if you like the production log being verbose, drop them for clean operator output.
2. Launch the full sweep on the active 5-model roster (`PDDL_DEFAULT_MODELS`) across all 10 tasks × 3 configs. The AWQ quants (`gemma4:26b-a4b`, `qwen3.6:35b`) are public on HF and pull with no token — same no-auth mechanism the 5-task arm uses. Per-model runtime estimate: ~3-4h for Qwen3.5:0.8B → ~24h+ for the two heavy models. Submit serialized (per memory `feedback_experiment_pipeline_safety.md`) or sharded across models.
3. Run `status.sh --bench planbench` from laptop to validate the new selector against real data.
4. Read the per-task accuracy and compare to PlanBench's committed baselines (gpt-4_chat etc. in `external/LLMs-Planning/plan-bench/results/<config>/<engine>/`).

### Open follow-ups (not blocking v1 smoke)

- **ISS-022: v2 tool-using arm.** Gated on the two MCP plugin extensions in the sibling repo's `planbench-integration` branch (`specs-for-plan-bench.md`). Sequencing: sibling repo lands `validate_plan_structured` + `optimal_plan`, then this repo adds `pddl_copilot_tools__*` engine using `pddl_eval.chat.MCPPlanner`.
- **`llm_plan_pipeline.py` upstream quirk (documented, not patched).** The pipeline script doesn't forward `--specific_instances` to `response_generation.get_responses`. Our cluster sbatch sidesteps this by calling `response_generation.py` and `response_evaluation.py` as standalone scripts. Not a blocker; documented in `EXPERIMENTS_FLOW.md §13`.
- **`--specific_instances 1` upstream quirk.** Requires `instance-0.pddl` (few-shot index = `i - n_examples = 0`) which doesn't exist. Smoke with `>= 2`. Not a blocker; documented in `EXPERIMENTS_FLOW.md §13`.
- **PlanBench upstream PR.** The filter mutation fix (bug #3 above) is worth proposing upstream once we have a settled corpus. File against `karthikv792/LLMs-Planning`.
- **`status_planbench.sh` Δ-table.** Current renderer is minimal (model × config done counts). Once the PlanBench corpus is substantial, port the 5task renderer's Δ-table / pace / ETA machinery.

---

## Useful commands to resume

| Goal | Command |
|---|---|
| Check cluster state | `bash .claude/skills/cluster-ops/scripts/status.sh --bench planbench` |
| Resume cluster setup (idempotent) | `ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && git pull && bash planbench/setup.sh"` |
| Re-apply patches only (after `git pull` brings new patch logic) | `ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && python3 planbench/apply_patches.py external/LLMs-Planning"` |
| Run smoke | `ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && bash cluster-experimenting/submit_planbench.sh --smoke"` |
| Submit a real sweep | `ssh omereliy@slurm.bgu.ac.il "cd ~/pddl-copilot-experiments && bash cluster-experimenting/submit_planbench.sh --models Qwen3.5:0.8B"` |
| Cancel a job | `ssh omereliy@slurm.bgu.ac.il "scancel <jobid>"` |
| Tail a job's log | `ssh omereliy@slurm.bgu.ac.il "tail -f ~/pddl-copilot-experiments/cluster-experimenting/logs/pddl_planbench_<MODEL_TAG>-<jobid>.out"` |
| Inspect live job env (debug) | `ssh omereliy@slurm.bgu.ac.il "srun --jobid <jobid> --overlap bash -c 'env \| grep -E ^PLANBENCH'"` |

---

## Pinned commits (`planbench-integration` branch)

```
HEAD     fix(planbench): patch upstream's self-destructing --specific_instances filter
7d8662e  debug(planbench): echo env vars + INSTANCE_ARGS expansion before sbatch loop
1c42cdf  fix(planbench): encode multi-value env vars with ^ separator for SLURM --export
f15dee1  fix(planbench): pre-export env vars to bypass SLURM --export comma parsing
c478bbe  feat(planbench): add PlanBench evaluation arm v1 (vanilla leaderboard)
```

Sibling repo:

```
e045e97  docs: add specs-for-plan-bench.md
```

---

## Trust-but-verify hints for the next session

- The cluster checkout's `response_generation.py` has the OLD filter logic until `apply_patches.py` is re-run after pulling. The patcher is idempotent — fine to run blindly.
- `submit_planbench.sh --dry-run` prints the exact sbatch invocation. Use it to sanity-check `--export` encoding before any real submit.
- `apply_patches.py` exits 1 if any anchor is missing. If PlanBench's upstream changes a function signature or indentation, the anchored edits will hard-fail and tell you which file.
- macOS laptop is engine-smoke-only (no VAL/PR2/FD binaries). Cluster Linux is the real validation surface.
