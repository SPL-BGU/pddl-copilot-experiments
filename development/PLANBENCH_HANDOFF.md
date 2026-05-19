# PlanBench arm — session handoff (2026-05-18)

Snapshot of where the PlanBench integration stands so the next session can resume cleanly. This is a working doc; once the smoke validates and the first real sweep lands, fold the resolved sections into `EXPERIMENTS_FLOW.md §12` / `CHANGELOG.md` and either delete this file or archive it.

---

## TL;DR

- **What's done:** PlanBench arm v1 (vanilla leaderboard, no MCP tools) is wired up end-to-end on cluster Linux. Adapter + setup + sbatch + cluster-ops status hook all committed on branch `planbench-integration` (both repos, pushed). Setup verified locally (engine smoke) and on the cluster (setup.sh ran clean, FD built, VAL+PR2 pre-built binaries work, slim venv up).
- **What's blocking real numbers:** three SLURM/PlanBench bugs were discovered and fixed in this session — only the last fix has not been validated by a successful smoke run yet.
- **Next action:** push the final fix (already done at this commit), pull on cluster, run `bash cluster-experimenting/submit_planbench.sh --smoke`. Expected runtime ~2-3 min for 3 instances.

---

## What this work is

`pddl-copilot-experiments` gets a second evaluation arm running the [PlanBench](https://github.com/karthikv792/LLMs-Planning) benchmark alongside (not replacing) the existing 5-task `run_experiment.py` matrix. Scope: all 10 PlanBench tasks × canonical Blocksworld + Logistics + Depots × our existing Ollama + vLLM model fleet. v1 is the vanilla leaderboard (no MCP tools during response generation); the tool-using arm is tracked as ISS-021 in OPEN_ISSUES.md.

Full methodology is in `EXPERIMENTS_FLOW.md §12`. Operator usage is in `planbench/README.md`.

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
- `EXPERIMENTS_FLOW.md` — new §12 (PlanBench arm methodology).
- `development/CHANGELOG.md` — 2026-05-18 entry.
- `development/OPEN_ISSUES.md` — new ISS-021 (v2 tool-using arm).
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

**Expected runtime:** ~2-3 min total (Ollama bootstrap ~60s + 3 instances × ~14s + VAL eval on 3 instances ~5s).

**Validation criteria:**
- `squeue` clears within ~3 min.
- `~/pddl-copilot-experiments/cluster-experimenting/logs/pddl_planbench_Qwen3_5_0_8B-<jobid>.out` shows progress bar reaches `3/500` quickly, then accelerates through skips (sub-second/iter) for the remaining 497.
- `results/planbench/slurm_Qwen3_5_0_8B_<jobid>/results/blocksworld/pddl_copilot__ollama__Qwen3.5:0.8B/task_1_plan_generation.json` contains exactly 3 `llm_correct` entries (or 500 total entries with 3 having an `llm_raw_response` filled).

### After smoke validates

1. Remove the `[env-debug]` echoes from `run_planbench_rtx.sbatch` (commit `7d8662e`) once we're confident the pipeline is stable. They're informative but they were added explicitly to diagnose the filter bug — keep them if you like the production log being verbose, drop them for clean operator output.
2. Launch the full sweep on the active 5-model roster (`PDDL_DEFAULT_MODELS`) across all 10 tasks × 3 configs. Per-model runtime estimate: ~3-4h for Qwen3.5:0.8B → ~24h+ for gemma4:31b and qwen3.6:35b. Submit serialized (per memory `feedback_experiment_pipeline_safety.md`) or sharded across models.
3. Run `status.sh --bench planbench` from laptop to validate the new selector against real data.
4. Read the per-task accuracy and compare to PlanBench's committed baselines (gpt-4_chat etc. in `external/LLMs-Planning/plan-bench/results/<config>/<engine>/`).

### Open follow-ups (not blocking v1 smoke)

- **ISS-021: v2 tool-using arm.** Gated on the two MCP plugin extensions in the sibling repo's `planbench-integration` branch (`specs-for-plan-bench.md`). Sequencing: sibling repo lands `validate_plan_structured` + `optimal_plan`, then this repo adds `pddl_copilot_tools__*` engine using `pddl_eval.chat.MCPPlanner`.
- **`llm_plan_pipeline.py` upstream quirk (documented, not patched).** The pipeline script doesn't forward `--specific_instances` to `response_generation.get_responses`. Our cluster sbatch sidesteps this by calling `response_generation.py` and `response_evaluation.py` as standalone scripts. Not a blocker; documented in `EXPERIMENTS_FLOW.md §12`.
- **`--specific_instances 1` upstream quirk.** Requires `instance-0.pddl` (few-shot index = `i - n_examples = 0`) which doesn't exist. Smoke with `>= 2`. Not a blocker; documented in `EXPERIMENTS_FLOW.md §12`.
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
