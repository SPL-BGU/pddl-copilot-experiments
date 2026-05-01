# Development Changelog

Running log of framework and MCP changes that affect experiment behaviour, methodology, or reproducibility. Dated newest-first. Entries reference the files touched so `git log` can pick up the details.

Scope covers both this repo (`pddl-copilot-experiments`) and the sibling MCP plugins at `../pddl-copilot` when those changes are driven from here.

---

## 2026-05-01 — Resumable single-task sweeps: per-trial JSONL + cell-keyed OUT_DIR

**TL;DR.** `run_single_task_experiment` writes one JSONL line per completed trial to `output_dir/trials.jsonl`, and `run_experiment.py` loads that file at startup to skip already-completed trials. A TIMEOUT / scancel / scratch-OOM no longer wipes the whole cell — only the trial in flight at the time is lost. On the cluster, `run_condition_rtx.sbatch`'s `OUT_DIR` is keyed on `(model, think, cond)` only (drops `_$SLURM_JOBID`), so a TIMEOUT'd resubmission lands in the same dir and the resume path finds the prior `trials.jsonl`. Methodology unchanged: `single_task_*.json` and `summary_*.json` shapes byte-compatible, `meta` gains `resumed_count` on resumed runs.

**Motivation.** Mid-sweep TIMEOUTs were forfeiting full cells. The 27b row in the 2026-04-30 sweep projected 72-135h per cell at observed pace (`qwen3.6:27b` at 57-107 s/trial × 4560 trials), well past any walltime the QoS=`normal` cap allows on the `gpu` partition (12h hard cap on already-running jobs, confirmed by `scontrol update TimeLimit=...` rejection on `17275792_0` 2026-04-30 21:30 IDT). Without per-trial persistence, every TIMEOUT wasted up to 12h of GPU time × 4 cells. Bumping wall alone never lands the 27b cells; the matrix is deliberate (4560 = 5 tasks × 20 domains × 5 problems × 3 variants + negatives, post 2026-04-20 expansion) and shrinking it would invalidate paper-vs-harness comparability. The cluster-side `OUT_DIR` change is the missing piece that makes the resume mechanism actually fire on SLURM — without it, every resubmission gets a new `$SLURM_JOBID` and a fresh `OUT_DIR`, orphaning the prior `trials.jsonl`.

**What changed (`feat/resumable-experiments` branch).**

*Runner — per-trial persistence.*
- **`pddl_eval/runner.py`** — `run_single_task_experiment` gains `progress_path: Path | None` and `done_keys: set[tuple] | None` kwargs. Module-level `_trial_key` builds a 10-tuple `(model, task, dname, pname, plan_label, pv, with_tools, think_str, tool_filter, prompt_style)` per trial; `_emit_job` filters against `done_keys` alongside the existing shard filter. The `as_completed` loop appends `{"key": [...], "result": asdict(r)}` JSONL after each completion under line buffering + `flush()`. A heal step pads a missing trailing `\n` before opening in append mode so a partial-line tail (TIMEOUT mid-write) doesn't corrupt subsequent appends. `TrialKey` tightened to `tuple[str, str, str, str, str, int, bool, str, str, str]`; `TRIAL_KEY_LEN = 10` is asserted by the loader.
- **`run_experiment.py`** — new `_load_progress(path) -> (set, list[TaskResult])` reads the JSONL, drops malformed/partial lines, deduplicates first-seen, asserts `TRIAL_KEY_LEN`, and surfaces `RuntimeError` on TaskResult schema drift or wrong-shape keys (forces user to move file aside rather than silently dropping data). `async_main` builds the progress path, loads done_keys/restored_results, threads them through `_run_single_task_split`, and merges restored + freshly-run results before `save_results`. New `--no-resume` CLI flag deletes the JSONL up front (without the unlink, append-mode writes would mix new trials into the old file and a subsequent default run would resurrect what `--no-resume` was meant to discard). `meta.resumed_count` records how many trials came from prior runs.
- **`tests/test_runner.py`** — 8 new pure-Python tests: `_think_str` serialisation, `_load_progress` roundtrip, partial-line tolerance, partial-tail heal, key dedup, key-length integrity (`_trial_key` shape == `TRIAL_KEY_LEN`), loader rejection of wrong-length keys, end-to-end writer-loader smoke (stubs `evaluate_one`, runs `run_single_task_experiment`, asserts the emitted JSONL round-trips through `_load_progress` with a key matching `_trial_key`). 28/28 pass via `bash tests/verify.sh` (was 7/7 pre-change).

*Cluster — resume-aware OUT_DIR.*
- **`cluster-experimenting/run_condition_rtx.sbatch`** — `OUT_DIR` drops `_${SLURM_JOBID}`. Comment block above the assignment rewritten to explain the resume-resubmit rationale (prior comment referenced cis-ollama parity, retired 2026-04-27).
- **`cluster-experimenting/submit_with_rtx.sh`** — post-submit echo updated to print the cell-keyed path and note resubmit-resume.
- **`cluster-experimenting/README.md`** — Quickstart's "rerunning any step is safe" paragraph spells out the cell-keyed resubmit-resume property; "Where things go" table entry rewritten to note that multiple resubmissions accumulate timestamped `summary_*.json` files in the same dir (latest wins on aggregation), and that log filenames keep `<task_jid>` because `%x-%J.out` is resolved at SLURM job-start. `scp` example in "Fetching results" updated to the new path shape.
- **`.claude/skills/cluster-ops/scripts/{aggregate,plot}.py`** — both `parse_dirname` functions made the trailing `_<jobid>` capture optional. Cell-keyed dirs (no jobid) parse via the same suffix-matching loop; legacy `_<jobid>` and pre-think-axis (`slurm_<model>_<cond>_<jobid>`) layouts continue to parse unchanged. Empty-string `jobid` field surfaces in the aggregator's pivot tables for new-shape rows; this is intentional (one row per cell instead of per-resubmission).

**What did NOT change.**
- `pddl_eval/scoring.py`, `pddl_eval/summary.py`, `pddl_eval/prompts.py`, `pddl_eval/schemas.py`, `domains/`, ground-truth pipeline, MCP plugin contracts — fully untouched.
- `single_task_*.json` and `summary_*.json` field set and shape — `save_results` consumes the merged list identically. Existing aggregators (`aggregate.py`, notebooks) work unchanged.
- Chain experiments (`run_chain_experiment`) — not made resumable in v1. Chains are tools-only (ISS-018), short, and weren't the TIMEOUT pain point. Add to v2 if needed.
- `--shard`, `--smoke`, `--smoke-shuffle`, `--cell-assignment` — composable with resume; the skip filter applies after sharding so resumed shards converge to the same partition. Smoke fast-path in the sbatch never passed `--output-dir`; `run_experiment.py` constructs its own `results/smoke[_shuffle]_<sha>_<ts>/` dir, so cluster smoke runs are unaffected by the OUT_DIR change.
- Pre-2026-05-01 result dirs on disk (`results/slurm_*_<digits>/`) — not migrated. Aggregators read both shapes; legacy rows stay one-per-resubmission, new-shape rows collapse to one-per-cell.
- Log filenames (`cluster-experimenting/logs/pddl_rtx_<model>-<task_jid>.out`) — keep the `<task_jid>` suffix because `%x-%J.out` is resolved by SLURM at job-start, before our `scontrol update JobName=…` runs. Each (re)submission still gets its own log file, which is correct.

**Cost.** Per-trial JSONL append is one `write()` + `flush()` ≈ 0.1ms; on the 4560-trial scale that's ~0.5s of added wall, dwarfed by even a single seconds-scale trial. JSONL file size is ~3MB at 4560 trials (same magnitude as `single_task_*.json`).

**Caveats.**
- The trial key includes `think_str`, `tool_filter`, `prompt_style` — different values write distinct keys to the SAME `trials.jsonl`. This lets smoke mode (`think={on, off}` into one output_dir) coexist correctly. Multi-config sweeps into the same `output_dir` accumulate trials across all configs; `meta` records only the last config (pre-existing smoke-mode merge limitation, not a regression).
- TaskResult dataclass schema drift makes existing JSONLs unloadable; trial-key-length drift surfaces an analogous error. Both raise `RuntimeError` directing the user to move the file aside; downstream code does not silently truncate.
- Partial-tail heal pads a single `\n` before append. On disk the partial line lives forever (always drops on read) — benign but means a JSONL written across many crash-resume cycles can accumulate a small number of unparseable lines. None of them count as completed trials.
- Concurrent-resubmit on cluster: two simultaneous SLURM jobs writing to the same cell-keyed dir would interleave appends to `trials.jsonl`. POSIX `O_APPEND` is atomic up to `PIPE_BUF` (~4KB on Linux) and JSONL records are typically <2KB, so byte-level corruption is unlikely; the loader's first-seen dedup also makes any duplicate completions idempotent. With the per-cell array model (one array task per cell), this only happens if a user manually sbatches the same cell twice while one is running — accept the corner case rather than add a lockfile.

**Verification.**
- `bash tests/verify.sh` — 28/28 pass on `test_runner.py` (was 7/7 pre-change). Other suites (`test_scoring.py` 244, `test_check_success.py` 45, `test_fixtures.py` 33) untouched.
- E2E smoke with stubbed Ollama: round-1 5 trials → truncate to 3 + partial → round-2 resume executes 2 missing → final JSONL has 5 unique keys → round-3 idempotent rerun executes 0.
- Local parser smoke: `aggregate.parse_dirname` and `plot.parse_dirname` exercised against four fixtures (cell-keyed, with-jobid, pre-think-axis, garbage) — all return expected shapes; legacy paths bytewise-equivalent to pre-change behaviour.
- End-to-end cluster validation pending: pick a 27b cell, submit, let it TIMEOUT at 12h, resubmit via the same sbatch invocation, confirm it picks up where it left off and converges to a complete `single_task_*.json`.

**Files.** `pddl_eval/runner.py`, `run_experiment.py`, `tests/test_runner.py`, `cluster-experimenting/{run_condition_rtx.sbatch, submit_with_rtx.sh, README.md}`, `.claude/skills/cluster-ops/scripts/{aggregate.py, plot.py}`, `development/CHANGELOG.md`.

---

## 2026-04-30 — Cluster submission topology: per-cell SLURM job array

**TL;DR.** The packed-job model (`--all` = one 6-day rtx_pro_6000:1 job that loops 4 models × 2 think × 3 conditions sequentially under `MAX_LOADED_MODELS=1`) is replaced by a **per-cell SLURM job array**: each (model, think_mode, condition) cell becomes one independent array task on its own rtx_pro_6000:1 GPU. `--all` now submits a 20-task array (4 models × 5 cells per model, after the no-tools/think=on matrix-gate skip). With unrestricted concurrency, max-of-cell wall is ~8h vs the prior ~140h serial pack — ~17× wall-clock speedup when the rtx_pro_6000 pool has capacity for the full fan-out, ~4× even when only 4 slots are free. Mar-26 BGU CIS guide §"Job Arrays" + §"SSD Drive" formalize the idioms used (no novelty). Methodology unchanged.

**Motivation.** The packed rationale ("share apptainer/serve startup, dodge cis-ollama eviction") was set 2026-04-27 when cis-ollama was still in play. With cis retired and each job owning its GPU node, packing was paying ~20 min of saved warmup per pack against (a) ~140h serialized wall, (b) a single point of failure across the whole sweep (any node fault, VRAM trip, or scheduler hiccup at hour 100 wasted 100h of compute), (c) approaching the 7-day partition cap with no margin. The proposal at `development/SUBMISSION_STRATEGY_PROPOSAL.md` (committed 2026-04-30 in `a3271ab`) examined three lenses (partition routing, runtime efficiency, deployment) under the Mar-26 cluster guide; user approved per-cell arrays + explicit `/scratch` workspace + cosmetic guide-alignment.

**What changed (`cluster/per-cell-array-submit` branch).**
- **`cluster-experimenting/submit_with_rtx.sh`** — full rewrite of post-arg-parse logic. The wrapper now builds `CELLS=("model|think|cond" ...)` with the matrix-gate filter (no-tools/think=on cells dropped) applied, encodes as `^`-separated `CELLS_LIST`, and submits `sbatch --array=0-(N-1)` (or single sbatch when N=1). The recursive `--all` path (`bash "$0" m1 m2 m3 m4 ...`) is gone — `--all` directly populates `MODELS=(...)` and falls through. Multi-positional invocations also fan out as arrays. Per-task `--time` is now per-cell (12h tools / 8h no-tools / 3h smoke) instead of N-scaled.
- **`cluster-experimenting/run_condition_rtx.sbatch`** — added cell-array picker block after `### Job info ###` that maps `$SLURM_ARRAY_TASK_ID` → one cell from `CELLS_LIST`, populating `MODELS`/`THINK_MODES`/`CONDITIONS` to one value each. The existing `for MODEL in $MODELS` outer loop and inner `THINK × CONDITIONS` loops still work unchanged — they now iterate exactly once per task. Added `#SBATCH --tmp=50G` (Mar-26 guide §"SSD Drive") and switched `WORK` from `/tmp/rtx-$JOBID` to `/scratch/$USER/$JOBID/rtx-work` with a `/tmp` fallback if `/scratch` isn't writable. Default `CONDITIONS` pruned (`tools_per-task_guided`, `tools_all_guided` removed; were retired 2026-04-27 but the default string still listed them, which would have caused legacy direct-sbatch invocations to error on `*)` branch). Cosmetic: dropped `--nv` from `apptainer build` (it's a runtime flag, harmless on build but absent from the Mar-26 guide example).
- **`cluster-experimenting/README.md`** — rewritten Quickstart, Submission, Resource profile, Monitoring, Cancelling, and Where-things-go sections to reflect the array model. Added `--tmp=50G` row to the resource table, `scontrol update Nice=500` politeness recipe, `ArrayTaskThrottle` post-submit cap, and the `<master>_<task>` array task naming convention for `scancel`/`squeue`/`sacct`.

**What did NOT change.**
- `run_experiment.py`, `pddl_eval/`, `domains/`, `EXPERIMENTS_FLOW.md` §1-9 (methodology, scoring, prompts, schemas, result-file shape) — fully preserved. No re-baseline needed.
- The 2026-04-27 IT caps (`--mem=80G` rtx_pro_6000, `--mem=48G` rtx_6000, no `--cpus-per-task` on single-GPU) remain binding and are preserved per-task.
- Result dir naming `slurm_<model>_<think>_<cond>_<task_jid>` continues — each array task's `$SLURM_JOBID` is unique, so existing aggregators (`aggregate.py:host_tag()`, notebook globs) work unchanged. `meta.host` will now vary across the (model, think, cond) cells of one `--all` sweep instead of being constant within a packed job; this is cosmetic metadata, not a confounder.
- Smoke matrix (`--smoke`/`--smoke-shuffle`) semantics unchanged — each model is one task that runs the full smoke iteration internally via `run_experiment.py`. Cell-picker maps `@smoke@` cond-marker to the existing SMOKE fast-path in the sbatch.
- Legacy direct-sbatch invocations (`sbatch --export=ALL,MODELS=...,THINK_MODES=... run_condition_rtx.sbatch`) still work — the cell-picker only fires when `CELLS_LIST` is exported.

**Cost.** Per-cell array (no `%N` cap): wall ≈ max-of-cell with full fan-out, fall-back to serial × pull-overhead under saturation.

| sweep | array size | per-task --time | best-case wall | worst-case wall |
|---|---|---|---|---|
| `--all`               | 20 | 12h | ~8h  | ~160h (serial-1-slot) |
| `--all --no-tools`    |  4 |  8h | ~6h  | ~24h  |
| `<single-model>`      |  5 | 12h | ~8h  | ~40h  |
| `--smoke`             |  4 |  3h | ~45m | ~3h   |

Worst case is also ~the prior packed-job wall plus per-task pull overhead (~3 min × 20 ≈ 1h additive at the 20-cell scale). Total compute (GPU-hours) is unchanged vs packed.

**Verification.** Local `--dry-run` smoke against four invocation patterns:
- `--all --dry-run` → 20 cells, `--array=0-19`, `--time=12:00:00`, all 4 models in CELLS_LIST with matrix-gate filter applied (no `model|on|no-tools` triples present).
- `--all --no-tools --dry-run` → 4 cells, `--array=0-3`, `--time=08:00:00`, each cell `model|off|no-tools`.
- `Qwen3.5:0.8B --dry-run` → 5 cells, `--array=0-4`, `--time=12:00:00`, single-model matrix.
- `--smoke --dry-run` → 4 cells, `--array=0-3`, `--time=03:00:00`, each cell `model|default|@smoke@`, `SMOKE=1` in export list.
- `gemma4:31b --no-tools --dry-run` → 1 cell, single sbatch (no `--array` flag).

Cell-picker isolation test (parsing `CELLS_LIST` with `IFS=^` then `IFS=|`) verified for both regular cells and `@smoke@` cells.

**Files.** `cluster-experimenting/{submit_with_rtx.sh, run_condition_rtx.sbatch, README.md}`, `development/SUBMISSION_STRATEGY_PROPOSAL.md` (moved to `development/archive/`), `development/CHANGELOG.md`.

---

## 2026-04-30 — Cluster guide refresh: Mar-26 PDF is sole source of truth

**TL;DR.** The March 2026 BGU cluster user guide replaces the July 2025 edition (Jul-25 PDF deleted from `.local/`). Repo docs and the `cluster-ops` skill aligned to the new edition. The Mar-26 guide adds operational idioms (`srun --jobid --pty bash`, `scontrol update Nice=N`, `--cpus-per-gpu=8` for rtx_6000:2 multi-GPU, tmpfs `/dev/shm` workarounds) and renames the cluster from "ISE-CS-DT" to "CIS"; cluster hardware is unchanged.

**Motivation.** Cluster naming and partition idioms had drifted between our docs (Jul-25 conventions) and the active guide. The IT-caps email of 2026-04-27 was already encoded in scripts and a memory; the Mar-26 refresh adds new gotchas (notably the rtx_6000:2 erratum) that aren't yet in any sbatch but should be retrievable when needed.

**What changed (docs only — no code touched).**
- `cluster-experimenting/README.md`: "BGU ISE-CS-DT" → "BGU CIS" with a one-line note explaining the rename is naming-only.
- `.claude/skills/cluster-ops/SKILL.md`: skill description renamed; PDF page references replaced with named-section refs (`Mar-26 guide §FAQ`, etc.) so they don't drift on the next refresh; `CONTEXT_LENGTH=8192` line corrected to `=16384` (had drifted from the actual sbatch).
- `reference_bgu_it_resource_caps.md` (memory): appended the rtx_6000:2 multi-GPU erratum (`--cpus-per-gpu=8`) since it's the only documented case where a `--cpus-*` flag is allowed on a GPU job.
- `reference_bgu_cluster_guide_mar26.md` (memory, new): captures the 10 operational deltas of the Mar-26 edition (srun --jobid attach, scontrol Nice deprioritize, tmpfs OOM workarounds, course partition rename, NCCL_P2P_DISABLE for multi-RTX6000 DDP, etc.). Indexed in `MEMORY.md`.

**What did NOT change.**
- No edits to `run_condition_rtx.sbatch`, `submit_with_rtx.sh`, `run_experiment.py`, `EXPERIMENTS_FLOW.md`, or anything under `../pddl-copilot/`. Submission-script rethink (partition routing, runtime efficiency, deployment approach) is delegated to a separate fresh-agent task; the briefing prompt is at `.local/rethink-submission-and-deployment-prompt.md`, referencing the markdown ground truth at `.local/cluster_user_guide.md`. The fresh agent's deliverable is a written proposal at `.local/submission-strategy-v2.md` for user review before any script changes land.
- No methodology, scoring, or results-schema impact. Existing `results/cluster-*` and `results/full-cluster-run*` dirs remain valid.
- IT caps memory's binding constraints (rtx_pro_6000 ≤80G, rtx_6000 ≤48G, no `--cpus-per-task` on single-GPU jobs) carry forward unchanged.

**Files.** `cluster-experimenting/README.md`, `.claude/skills/cluster-ops/SKILL.md`, `~/.claude/projects/.../memory/reference_bgu_it_resource_caps.md`, `~/.claude/projects/.../memory/reference_bgu_cluster_guide_mar26.md` (new), `~/.claude/projects/.../memory/MEMORY.md`, `development/CHANGELOG.md`.

---

## 2026-04-30 — Cluster roster trim: nemotron-3-nano:30b dropped

**TL;DR.** `nemotron-3-nano:30b` removed from the active 5-model rtx pack. Active sweep is now 4 models: `Qwen3.5:0.8B`, `qwen3.6:27b`, `qwen3.6:35b`, `gemma4:31b`. The non-Qwen/Gemma family-diversity slot (held by gpt-oss:20b → nemotron-3-nano:30b through 2026-04-29) is now empty pending a viable replacement.

**Motivation.** Smoke 17266087 (2026-04-29, pre-num_predict bump) flagged 4 deterministic `ollama_parse_error` rows on nemotron-3-nano:30b — Hermes/harmony XML tool-call template clipping mid-`<parameter>` on validate_problem/blocksworld/n01 + validate_plan/blocksworld/p01 b1, b2, b4 (think=off+tools cells). Hypothesised root cause: 4096 `num_predict` cliff on the verbose XML envelope wrapping the inlined PDDL parameter. Bump 4096→6144 shipped on `main` (PR #26, commit `464d0f6`) under that hypothesis. Smoke 17274424 (2026-04-30, post-bump) returned the **same 4 cells** with the **same failure signature** — falsifying the cliff hypothesis. The XML truncations are content-dependent (deterministic against the same prompts), not budget-dependent. Without a known root-cause fix at the harness/template layer, the model is unblocking work to drop and revisit.

**What changed (active config).**
- `cluster-experimenting/submit_with_rtx.sh`: `MODELS=(...)` arrays for `--all` and `--smoke`, usage examples, packing comment (`5-model` → `4-model`).
- `cluster-experimenting/run_condition_rtx.sbatch`: VRAM fit table (peak now `gemma4:31b` ~26 GB instead of `qwen3.6:35b`/`nemotron-3-nano:30b` ~24 GB), example MODELS line, header roster history.
- `cluster-experimenting/README.md`: model-count language (`five models` → `four active models`), example commands switched off nemotron, `--all --no-tools` wallclock recalculated (20h → 16h for 5 → 4 models), full roster-history paragraph extended.
- `README.md`, `EXPERIMENTS_FLOW.md`: top-level model lists, dimension table, deviations §11, run-experiment code block.
- `.claude/skills/cluster-ops/SKILL.md`: active-pack listing in the submit-path bullet and "submit the sweep" recipe.
- `pddl_eval/runner.py`, `run_experiment.py`: comments and CLI `--num-predict` help text now flag the bump's stated motivation as falsified by smoke 17274424; 6144 retained as harmless headroom.

**What did NOT change.**
- `DEFAULT_NUM_PREDICT` validate_*/simulate stays at 6144. Reverting to 4096 is a separate methodology decision pending fresh post-trim wall measurements; the 6144 cap is harmless for the surviving 4 models.
- `DEFAULT_NUM_CTX` (16384) and `DEFAULT_NUM_CTX_THINKING/CHAIN` are unchanged — the ctx evidence motivating the 8192/12288 → 16384 bump on 2026-04-29 still applies via qwen3.6:27b alone (nemotron was a co-anchor, not a sole anchor).
- `OLLAMA_TOOL_PARSE_SIGNATURES` retains the `"XML syntax error"` Hermes signature so any future model with the same tool-call template family routes correctly into `FR_OLLAMA_PARSE_ERROR`.
- All historical results/anchors (smoke 17266087 baseline, prior `cluster-2026042{6,7,8,9}/` dirs) are preserved on disk and remain valid for trend analysis. Headline numbers in plots/tables are recomputed fresh from post-trim sweeps.

**Compatibility / drift framing.** This is the second consecutive same-week roster swap on the non-Qwen/Gemma slot (gpt-oss → nemotron 2026-04-29; nemotron → ∅ 2026-04-30). The smoke-gate (`diff_smoke.sh`) byte-equality runs are now anchored on Qwen3.5:0.8B + gemma4:31b (unchanged slots). The drop-and-leave-empty stance is intentional — re-filling the diversity slot would require ≥1 day of smoke + per-cell verification per candidate, time we are not paying right now. Future replacement candidate criteria: (a) Apache-2.0 or equivalently permissive, (b) does NOT emit Hermes/harmony XML tool calls (rules out most NVIDIA Nemotron and Mixtral-derivatives that ship with the harmony chat template), (c) fits in 48 GB to keep `--gpu-type rtx_6000` viable as an escape hatch.

**Files.** `cluster-experimenting/submit_with_rtx.sh`, `cluster-experimenting/run_condition_rtx.sbatch`, `cluster-experimenting/README.md`, `README.md`, `EXPERIMENTS_FLOW.md`, `.claude/skills/cluster-ops/SKILL.md`, `pddl_eval/runner.py`, `run_experiment.py`, `development/CHANGELOG.md`.

---

## 2026-04-29 (PR-4 review fixes) — Address PR #25 review

**Motivation.** Three follow-ups from the PR-4 code review, all on the same PR branch (`framework-ext-pr4`) before merge.

- **`pddl_eval/scoring.py::check_success` (solve no-tools).** Distinguished "model emitted clean JSON with empty plan" (now `FR_PLAN_INVALID` — model gave up under a successful format constraint) from "couldn't parse anything from either path" (`FR_FORMAT_PARSE_FAIL`, unchanged). The pre-fix code conflated both into `FR_FORMAT_PARSE_FAIL`, distorting the failure-reason histogram in cells with frequent give-up behaviour.
- **`pddl_eval/runner.py` (chain-runner no-tools branch).** Threaded `format=TASK_SCHEMAS.get(task)` through the chain runner's `chat_without_tools` call. Today the no-tools chain path is gated upstream by ISS-018, but if it ever returns the JSON-first grader in `check_success` would otherwise silently fall through to free-text fallbacks (or `FR_FORMAT_PARSE_FAIL` on simulate, which has no fallback). Removes the forward-compat hazard.
- **`pddl_eval/scoring.py::_normalize_trajectory`.** A trajectory entry with a non-dict `state` field (malformed model output that escaped the format constraint) used to fall through to flat-shape lookup, find nothing, and silently canonicalise to an empty state — false-positive equality match against an empty oracle init. Now returns `None` (callers tag as `FR_FORMAT_PARSE_FAIL`).

**Tests.** `tests/test_check_success.py` adds `solve nt json plan empty (PR-4 review fix)` (clean JSON, empty `plan` list → `FR_PLAN_INVALID`). `tests/test_scoring.py::test_normalize_trajectory` adds two non-dict-state cases (string and list). `bash tests/verify.sh` → 329/329 sub-checks pass (was 326 pre-fix, +3 from the new cases).

**Compatibility.** Single-task with-tools rows untouched. No-PDDL-tools rows: the only behaviour change is on inputs that were already failing (mislabelled) — the success rate per cell is unchanged; only the failure-reason bucket on a tiny subset of failures shifts (`FR_FORMAT_PARSE_FAIL` → `FR_PLAN_INVALID`). JSON output schema unchanged.

**Files.** `pddl_eval/scoring.py`, `pddl_eval/runner.py`, `tests/test_check_success.py`, `tests/test_scoring.py`, `development/CHANGELOG.md`.

---

## 2026-04-29 (PR-4) — No-PDDL-tools = `format=<json_schema>`; lift simulate skip; shared trajectory normalizer

**Motivation.** `FRAMEWORK_EXTENSION_PLAN.md` PR-4 — the methodologically-novel piece of the four-PR rollout. Before this change, the `with_tools=False` cell graded plans/verdicts via free-text regex extractors (`extract_plan_lines`, `extract_verdict`) and excluded `simulate` entirely (ISS-002 — its keyword grader was non-discriminative). PR-4 replaces the free-text-only path with Ollama `format=<json_schema>` constraint enforcement, restores `simulate` under the new structured grader, and switches the with-tools `simulate` branch onto the same canonical-form trajectory comparison so both sides share one equality rule.

**Changes.**

- **`pddl_eval/schemas.py` (new, ~75 LOC).** Per-task Pydantic schemas: `SolveResponse`, `ValidateResponse`, `StateSnapshot`, `StateStep`, `SimulateResponse`. `TASK_SCHEMAS: dict[str, dict]` resolves task → JSON schema (`model_json_schema()`) for Ollama. Field-name choice (`boolean` / `numeric` on the model side, while the oracle plugin emits `boolean_fluents` / `numeric_fluents`) bridged by `_normalize_trajectory` rather than schema gymnastics — shorter names round-trip more reliably under format constraints on tiny models.

- **`pddl_eval/scoring.py`**:
  - `FR_FORMAT_PARSE_FAIL` constant added; appended to `_TRUNCATION_OVERRIDE_REASONS` so a cap-cut mid-JSON re-tags as `FR_TRUNCATED_NO_ANSWER` rather than masquerading as sampling-degeneracy.
  - `_normalize_trajectory(traj)` helper canonicalises both shapes — oracle (`boolean_fluents: dict[str, bool]`, `action: None` on step 0) and model (`state: {boolean: list[str], numeric: dict}`) — to a single `{step, action, boolean (sorted true predicates), numeric}` form. Lower-cases action names, collapses whitespace, returns None on malformed input.
  - `_safe_pydantic_validate(model_cls, raw)` helper attempts JSON parse + Pydantic validation, tolerating models that wrap output in markdown code fences. Returns the Pydantic instance or None.
  - `check_success` no-tools branches rewritten:
    - `solve` — try `SolveResponse.plan` via Pydantic; fall back to `extract_plan_lines`; route plan into `_validate_model_plan`. Empty plan from both paths → `FR_FORMAT_PARSE_FAIL` (distinct from `FR_PLAN_INVALID`, which is reserved for "plan extracted but failed validation").
    - `validate_*` — try `ValidateResponse.verdict`; fall back to `extract_verdict`. Both fail → `FR_FORMAT_PARSE_FAIL` (replaces the prior `FR_NO_VERDICT_PARSED` exit; the constant stays in `_TRUNCATION_OVERRIDE_REASONS` for back-compat with existing `_classify_step_failure` tests).
    - `simulate` (newly reachable) — try `SimulateResponse.trajectory` via Pydantic, normalise both sides through `_normalize_trajectory`, deep-equal. No free-text fallback (the pre-PR-4 keyword check was the original ISS-002 problem).
  - `check_success` with-tools `simulate` branch switched to `_normalize_trajectory(parsed.get("trajectory")) == _normalize_trajectory(oracle_traj)` so both sides go through the same canonical form. Functionally byte-equal to the pre-PR-4 direct `==` on identical inputs (oracle and model call the same plugin with identical args), but bridges any future shape drift.
  - Dead `resp_lower = (response or "").lower()` line removed (only consumer was the old simulate keyword check).

- **`pddl_eval/chat.py::chat_without_tools`**: gains `format: dict | str | None = None` kwarg, threaded into `client.chat(format=...)`. None preserves pre-PR-4 unconstrained sampling (the with-tools branch and any direct callers).

- **`pddl_eval/runner.py`**:
  - `evaluate_one` passes `TASK_SCHEMAS.get(task)` as `format=` to `chat_without_tools` when `with_tools=False`. Chain path NOT touched — chains stay tools-only (ISS-018).
  - The `if not with_tools and task == "simulate": continue` guard at the top of `run_single_task_experiment`'s task loop is removed. The production matrix now emits `(no-tools, simulate)` jobs.

- **`run_experiment.py`**: re-exports `FR_FORMAT_PARSE_FAIL` and `_normalize_trajectory` for tests. CLI banner condition lines now display `no-pddl-tools` (the `--conditions no-tools` enum value is unchanged for back-compat).

- **User-facing rename `no-tools` → `no-pddl-tools`**: scoped strictly to (a) printed table column in `pddl_eval/summary.py` (via a `_display_condition()` helper; column width widened 9 → 13), (b) CLI banner strings in `run_experiment.py`, (c) `EXPERIMENTS_FLOW.md` §3 / §4.2 / §11 narrative. Not touched: CLI flag (`--conditions no-tools`), bash flag (`--no-tools` in `cluster-experimenting/submit_with_rtx.sh`), JSON `condition` field in `summary_*.json`, internal `with_tools: bool`, `_format_progress` log lines (so log-tailing scripts stay stable), `.claude/` skill configs, historical CHANGELOG / OPEN_ISSUES entries, sibling-repo `pddl-copilot/`. The plan-of-record in `FRAMEWORK_EXTENSION_PLAN.md` §3.4.4 explicitly preserves the internal label so the 2026-04 result corpus parses identically under PR-4 analysis.

- **Tests** (`tests/verify.sh` → all 4 files pass, 326 sub-checks):
  - `tests/test_check_success.py`: 3 tests updated to expect `FR_FORMAT_PARSE_FAIL` where the response carries no JSON and no extractable free-text artefact (replacing the prior `FR_PLAN_INVALID` / `FR_NO_VERDICT_PARSED` expectations on the same inputs). Added 7 new cases covering the JSON paths: solve / validate_plan happy-path JSON, solve JSON with bad plan → `FR_PLAN_INVALID`, validate_plan negative-arm JSON match → success, simulate JSON trajectory match → `FR_OK`, simulate JSON trajectory mismatch → `FR_RESULT_MISMATCH`, simulate malformed JSON → `FR_FORMAT_PARSE_FAIL`.
  - `tests/test_scoring.py`: new `test_normalize_trajectory` (5 sub-checks) pinning oracle ↔ model shape equivalence, ordering independence, action whitespace/case normalisation, and mismatch detection.

- **`EXPERIMENTS_FLOW.md`** §3 simulate row, §4.2 (rewritten under "No-PDDL-Tools" heading with per-task grader description and re-baselining note), §9 `failure_reasons` row (documents `FR_FORMAT_PARSE_FAIL`), §11 paper-diff table (simulate criterion + no-tools task set + new no-tools grader row).

- **`development/OPEN_ISSUES.md`**: ISS-002 closed (path a — structured-trace grader landed); ISS-013 paper-diff narrative narrowed since the no-tools task-set divergence from the paper now has a concrete grader behind it.

**Compatibility / re-baselining.**
- **With-tools rows are structurally unchanged.** `tool_calls[]`, `tool_selected`, `success`, all `FR_*` constants stable. With-tools `simulate` migrated to the shared `_normalize_trajectory` but byte-equality with prior simulate `FR_OK` outcomes is preserved (oracle and model side route through the same plugin with identical inputs).
- **No-tools rows are NOT directly comparable to pre-PR-4.** The grading method changed: free-text regex → format-constrained JSON parse + free-text fallback. Treat any plot mixing pre/post-PR-4 no-tools cells as a re-baseline boundary; mark accordingly. The new `FR_FORMAT_PARSE_FAIL` rate per cell is the diagnostic for whether constraint enforcement degraded a tiny model.
- **JSON output schema additive.** `FR_FORMAT_PARSE_FAIL` is a new bucket in `failure_reasons`. The `condition` field stays `"no-tools"` literal. Old `single_task_*.json` and `summary_*.json` parse under PR-4 analysis tools without migration.
- **Smoke gate.** Per the user's 2026-04-29 instruction, the cross-PR byte-equality anchor against PR-3 is skipped (PR-3 smoke didn't complete before PR-3 merged). PR-4's own validation: full local test suite (326 sub-checks) green; cluster smoke deferred to the next sweep submission.

**Closes / narrows.**
- **Closes ISS-002** (simulate no-tools grader). Path a (structured-trajectory grader) landed; path b (drop simulate from no-tools headline) was the de-facto resolution since 2026-04-25 and is now superseded.
- **Narrows ISS-013** (paper-diff audit) — the no-tools task-set divergence now has a concrete grader behind it; the per-task side-by-side diff in EXPERIMENTS_FLOW.md §11 rewrote the simulate / no-tools rows.

**Files.** `pddl_eval/schemas.py` (new), `pddl_eval/scoring.py`, `pddl_eval/chat.py`, `pddl_eval/runner.py`, `pddl_eval/summary.py`, `run_experiment.py`, `tests/test_check_success.py`, `tests/test_scoring.py`, `EXPERIMENTS_FLOW.md`, `development/OPEN_ISSUES.md`, `development/CHANGELOG.md`.

---

## 2026-04-29 (review) — Address PR #22 review on `framework-ext-pr3`

**Motivation.** The PR review flagged one correctness bug in ground-truth generation (`plan_valid is None` silent coerce on validator transport errors) and a dead-code sweep in the new fixture generator as ship blockers, plus several cheap follow-ups in the same code surface.

**Changes.**

- **`pddl_eval/domains.py`**:
  - **Loop 1 (committed valid plans, ~line 209):** abort guard `if plan_valid is False:` → `if plan_valid is not True:`. Was: `_validate_capture` returns `(str(exc), None)` on transport error, then `bool(None) == False` recorded a fake `plan_valid=False` instead of aborting. Now: any non-`True` outcome (False or None) raises `SystemExit` with the raw response (which carries `str(exc)` on transport error) appended to the message. Recorded value simplified to literal `True` since the guard ensures it.
  - **Loops 2 & 3 (negative problems, negative plans) + the `domain_neg.pddl` probe:** raw `mcp.call_tool("validate_pddl_syntax", ...)` + manual `_parse_validation_verdict(raw)` replaced with `raw, verdict = await _validate_capture(mcp, args)`. Same abort guard `if verdict is not False:` (already correct — catches both `None` and `True`); SystemExit messages now include the raw response so a transport blip names the file *and* surfaces the underlying exception text.
  - **Loader glob (`load_domains`, ~line 58):** added `if not pf.stem.endswith("_0")` to the `p[0-9]*.pddl` dict comprehension. Defensive — no `_0` files exist post-PR-3 migration, but a stray legacy file would otherwise be silently loaded as a positive.

- **`tools/build_fixtures.py`** (dead-code sweep):
  - Deleted the `_problem_label` function (and its inline `import re`) — defined but never called.
  - Deleted three `_0`-suffix filter blocks in `cmd_seed_problems` (single-`continue` form) and the `cmd_gen_valid_plans` / `cmd_gen_invalid_plans` problem-list comprehensions. Unreachable post-migration.

- **`tests/test_runner.py` (new)**: 3 tests / 7 sub-checks pinning `_shard_filter` behaviour: (a) `plan_label` disperses v1..v5/b1..b5 across multiple shards (regression guard for the PR-3 shard-key change); (b) every key lands in exactly one shard for `shard_n ∈ {2,4,8}`; (c) `shard_n=1` is a pass-through. Added to `tests/verify.sh`.

- **`development/CHANGELOG.md`**: added an explicit re-baselining checklist anchor under the same-day cap-bump entry (5 metrics that must be relabeled or redrawn for paper figures when crossing the 2026-04-29 boundary).

- **`development/OPEN_ISSUES.md`**: tracked `ISS-020` (P3) for the deferred `validate_domain` neg-arm 5:1 → 5:5 pairing follow-up that the reviewer flagged as out-of-scope for PR #22.

**Compatibility.** No methodology change. The `domains.py` fix only fires on validator-transport-error paths (which already crashed loudly in the negative loops) and on never-reached `bool(None)` records (no recorded sweep has actually consumed the buggy output, since the bug is exception-path). Existing `results/` directories are unaffected. The shard-key test pins existing behaviour rather than changing it.

**Validation.**
- `bash tests/verify.sh` — all 4 test files pass (`test_scoring.py`, `test_check_success.py`, `test_fixtures.py`, `test_runner.py`).
- Grep: `grep -nF "_problem_label" tools/build_fixtures.py` and `grep -nE 'endswith\("_0"\)' tools/build_fixtures.py` → no matches.

**Closes / narrows.** No `ISS-###`. Adds `ISS-020` (deferred follow-up). Addresses all PR #22 review blockers + cheap follow-ups; review's explicit deferrals (`_emit_job` dataclass, numeric plan-diversity callout, `num_ctx_thinking` branch simplification) intentionally not changed.

**Files.** `pddl_eval/domains.py`, `tools/build_fixtures.py`, `tests/test_runner.py` (new), `tests/verify.sh`, `development/CHANGELOG.md`, `development/OPEN_ISSUES.md`.

---

## 2026-04-29 (cluster) — Align cluster sbatch with the same-day num_ctx / num_predict bumps

**Motivation.** Two same-day entries below raised `DEFAULT_NUM_CTX` 8192 → 16384, `DEFAULT_NUM_CTX_THINKING` 12288 → 16384, `DEFAULT_NUM_CTX_CHAIN` 12288 → 16384, and non-solve `DEFAULT_NUM_PREDICT` 1024/1536 → 4096. The cluster submission scripts were not adjusted in those commits and have two failure modes against the new caps:

1. **Walltime kills.** Per-call output now runs up to 4× longer on the 33–41% of non-solve trials that previously truncated mid-emission, and KV cache ~doubles. End-to-end per-model wall ~doubles. The existing caps (smoke 2h, multi-model 4d, no-tools `4 + 4*(N-1)`h) would kill multi-model sweeps before they finish.
2. **Per-cell model reload.** `cluster-experimenting/run_condition_rtx.sbatch` set `OLLAMA_CONTEXT_LENGTH=8192` and warmed each model with `num_ctx=8192`, while every real experiment request now hits `num_ctx=16384`. Ollama 0.20.7 reloads the model on the first real request because the requested ctx differs from the resident value — wasting ~1 min/model × 5 models × 16 cells ≈ 80 min per packed sweep, plus a noisy log.

**Changes.**

- **`cluster-experimenting/submit_with_rtx.sh`** (walltime caps):
  - Smoke: `--time=02:00:00` → `--time=03:00:00`. Per-model wall went from 12–14 min (job 17263071 baseline, pre-bump) to ~25–35 min projected; 5-model pack ~150 min, 3h leaves margin.
  - Multi-model regular sweep: `--time=4-00:00:00` → `--time=6-00:00:00`. Pre-bump 50–85h for the 5-model pack → projected 100–175h post-bump; 6d (144h) covers it inside main partition's 7d cap.
  - `--no-tools` per-model multiplier: `nt_hours = 4 + 4*(N-1)` → `nt_hours = 6 + 6*(N-1)`. `--all --no-tools` now requests 30h instead of 20h.
  - Single-model regular sweep keeps the 2d sbatch default — projected ~20h post-bump fits.
  - Comment blocks above each constant updated to cite the new arithmetic and the 2026-04-29 bump as the reason.

- **`cluster-experimenting/run_condition_rtx.sbatch`** (Ollama default ctx alignment):
  - `OLLAMA_CONTEXT_LENGTH=8192` → `16384`. Now matches the single-task per-request `num_ctx` so the server's KV-cache default doesn't contradict what experiments actually request.
  - Warmup curl payload `num_ctx: 8192` → `num_ctx: 16384`. Loads the model at the run's ctx so the first real request doesn't trigger a reload. Comment refresh on the warmup block explains the rationale.
  - Banner echo `CTX_CAP=8192` → `CTX_DEFAULT=16384`. The string was misleading regardless of the value (per-request `num_ctx` overrides, never caps).

- **`cluster-experimenting/README.md`** (operational note, prompted by smoke 17263071):
  - "Cancelling jobs" section now warns against `scancel`-ing a job in CG (completing) state. Wait for natural unwind; a CG-state cancel can race the on-disk write of late-cell results. Cites the 17263071 incident where the qwen3.6:35b warmup and gemma4:31b cells were lost to such a race.

**Compatibility.** Result schema and scoring untouched. The same-day reproducibility framing in the upstream `num_ctx`/`num_predict` entries already covers the comparability story (post-bump runs are not directly comparable to pre-bump on truncation rate, `FR_THINK_OVERFLOW` rate, or tools-vs-no-tools accuracy gaps). Jobs that ran between the harness bump and this commit at the new caps would still produce correct outputs — they would just have eaten the per-cell model-reload overhead and risked walltime kills. None such are recorded in `results/`; the only post-bump cluster job to date is the smoke 17263071 which preempted before completion.

**Verification.**
- `bash -n` syntax-clean on both files.
- `--dry-run` confirmed for: smoke (3h), `--all` (6d), `--all --no-tools` (30h), single-model (sbatch default 2d).
- Cluster validation deferred to the next sweep submission. Expected outcomes: (a) `--smoke` finishes ≤150 min with rc=0; (b) `ollama-serve.log` shows no model-reload events on first real request after warmup; (c) `failure_reasons.think_overflow` drops materially on `validate_problem`/`validate_plan` vs the 17263071 baseline.

**Closes / narrows.** No `ISS-###`. Operational companion to the same-day cap-bump entries.

**Files.** `cluster-experimenting/submit_with_rtx.sh`, `cluster-experimenting/run_condition_rtx.sbatch`, `cluster-experimenting/README.md`.

---

## 2026-04-29 (follow-up) — Raise `num_ctx_chain` 12288 → 16384

**Motivation.** The same-day prior entry left `num_ctx_chain` at 12288 with a "raise in lockstep if a chain sweep surfaces step-level `think_overflow`" trigger. Re-reading the single-task evidence shows that trigger is preemptively met by reasoning, not waiting on data: at ctx=12288 single-task `validate_problem`/`validate_plan` overflowed 50% of cells with qwen3.6:27b / nemotron-3-nano:30b, where the model had ~11K think+output budget on top of a ~1K prompt. The same task as a chain step-3 has ~4K of accumulated history before it starts thinking, so the budget at ctx=12288 collapses to ~8K — **worse** than the single-task regime that already failed. Sizing chain ctx below single-task ctx therefore reverses the safety margin, not preserves it.

**Decision.** `DEFAULT_NUM_CTX_CHAIN` 12288 → 16384, matching `DEFAULT_NUM_CTX` and `DEFAULT_NUM_CTX_THINKING`. This restores chain step-3 to ~12K think+output budget (comparable to the single-task envelope at 16384) and chain step-4 to ~8–10K (still tighter than single-task by the prompt-accumulation overhead; raise to 20480 if a chain sweep surfaces step-4 `FR_THINK_OVERFLOW`).

**Changes.**
- `pddl_eval/runner.py`: `DEFAULT_NUM_CTX_CHAIN` 12288 → 16384, comment rewritten to explain the headroom math (chain budget at ctx=N is single-task budget at ctx=(N − accumulated history)).
- `run_experiment.py`: `--num-ctx-chain` help text updated; banner unchanged (auto-pulls the new default).
- `README.md`, `EXPERIMENTS_FLOW.md` §5 + summary-meta — documented.

**Compatibility.** Re-baselining concerns from the prior same-day entry already cover this; no additional invalidation. Per-call KV cache for chain steps grows ~33% vs the (intermediate) 12288 baseline; on rtx_pro_6000 the active 5-model pack still fits inside the 80 GB `--mem` and 96 GB VRAM budget, but post-mortem `sacct/MaxRSS` after the first sweep on raised chain ctx.

**Files.** `pddl_eval/runner.py`, `run_experiment.py`, `README.md`, `EXPERIMENTS_FLOW.md`, `development/OPEN_ISSUES.md`, `cluster-experimenting/README.md`, `cluster-experimenting/run_condition_rtx.sbatch`.

---

## 2026-04-29 — Raise non-solve `num_predict` caps 1024/1536 → 4096; raise single-task `num_ctx`/`num_ctx_thinking` 8192/12288 → 16384 (held equal for tools/no-tools fairness); add `num_ctx_chain=12288` for chains

**Motivation (output caps).** Aggregating `truncated` counts across the cluster-26042026 sweep (`done_reason == "length"` on the last chat turn) showed the per-task output caps were biting hard:

| task               | cap (old) | truncation rate | success rate |
| ------------------ | --------: | --------------: | -----------: |
| `validate_plan`    |      1024 |          40.9% |        18.0% |
| `simulate`         |      1536 |          37.1% |        25.2% |
| `validate_problem` |      1024 |          32.7% |        30.8% |
| `validate_domain`  |      1024 |          17.4% |        55.5% |
| `solve` (tools)    |      8192 |          12.3% |        60.0% |
| `solve` (no-tools) |      8192 |          32.0% |        29.2% |

The 1024/1536 caps were calibrated when "verdict + a sentence" was the expected output, but thinking-mode reasoning (`qwen3:thinking`, `gpt-oss`, `gemma`) inlines 2–6K tokens of chain-of-thought before the verdict, and tool-call XML/harmony emissions count against `num_predict` too. Mid-emission truncation also produced the bulk of `ollama_parse_error` records — the Hermes/harmony XML parser fails when a `<parameter>` tag opens but the cap fires before its `</parameter>` closes (observed across `nemotron-3-nano:30b` on `validate_plan` b1/b2/b4 in smoke job 17263071, 2026-04-29).

**Motivation (context window).** A follow-up smoke against the new `qwen3.6:27b` and `nemotron-3-nano:30b` roster slots (also 2026-04-29) showed `FR_THINK_OVERFLOW` rates of 6/12 (tools cells) and 10/20 (no-tools cells) on `validate_problem`/`validate_plan` at `num_ctx=12288` — every miss was a thinking spiral that consumed the entire context window before emitting an answer. The pre-2026-04-28 calibration (12288 covered qwen3:0.6b max prompt+eval = 8680) does not hold for the qwen3.6/nemotron generation. More importantly, the old asymmetric setup (`num_ctx=8192` for tools, `num_ctx_thinking=12288` for no-tools+think_on) confounded the paper's headline comparison: the no-tools branch had 1.5× more think+output room than the tools branch, so any "tools save tokens" or "tools improve accuracy" claim was partly an artefact of the ctx asymmetry rather than a tool-effect signal.

**Decision.**
1. **Output caps:** non-solve `num_predict` 1024/1536 → 4096 uniformly; keep `solve=8192` (paper-default).
2. **Single-task ctx:** `num_ctx` 8192 → 16384 AND `num_ctx_thinking` 12288 → 16384 — held equal so the tools and no-tools branches receive identical context budgets. The `num_ctx_thinking` constant is retained as a separate symbol so a future asymmetric experiment can override one without touching the other; today the asymmetric branch in `evaluate_one` is a no-op.
3. **Chain ctx:** new `num_ctx_chain = 12288` for multi-task chain runs. Chains accumulate full per-step history (each step re-embeds domain + problem + plan, prior assistant turns + tool calls + tool results stay in context); step-4 prompts reach ~6–8K tokens before generation. Sized below the single-task 16384 because chains are tools-only (ISS-018) — no tools-vs-no-tools fairness comparison applies, so the asymmetry is acceptable. Raise to 16384 in lockstep if a future thinking-model sweep shows chain-step `think_overflow`.

**Changes.**
- `pddl_eval/runner.py`: `DEFAULT_NUM_PREDICT` non-solve entries 1024/1536 → 4096; `DEFAULT_NUM_CTX` 8192 → 16384; `DEFAULT_NUM_CTX_THINKING` 12288 → 16384; new constant `DEFAULT_NUM_CTX_CHAIN = 12288`. `run_chain_experiment` gains `num_ctx_chain` parameter; the `effective_num_ctx` formula in the chain-step path resolves to `num_ctx_chain` for the tools branch (chains are tools-only per ISS-018, so this fires unconditionally today; the `num_ctx_thinking` branch is preserved for forward-compat).
- `run_experiment.py`: imports `DEFAULT_NUM_CTX_CHAIN`; new `--num-ctx-chain` CLI flag; threaded into `run_chain_experiment`; written to `meta.num_ctx_chain` in saved summaries; banner now prints all three context budgets, flags the tools/no-tools fairness invariant when `num_ctx == num_ctx_thinking`, and lists the per-task `num_predict` defaults explicitly.
- `README.md` parameter table and `EXPERIMENTS_FLOW.md` §5 (knobs) + summary-meta — updated.

**Compatibility.** Single-task results from prior sweeps (cluster-26042026 and earlier) remain valid for trend analysis but **truncation rates and success rates are not directly comparable** — the new caps will lower truncation counts and may shift success rates upward on `validate_plan`/`simulate`/`validate_problem` cells (the 33–41% truncated calls that previously couldn't emit a complete verdict now have room), and the wider `num_ctx` will reduce `FR_THINK_OVERFLOW` for thinking models. Most consequentially: any historical comparison of tools-vs-no-tools accuracy made under the old 8192/12288 asymmetry is no longer apples-to-apples with post-bump runs. Re-run sweeps under the new caps should label themselves as "post 2026-04-29 cap bump" in plots; the headline "tools save tokens" / "tools improve accuracy" claims should be redrawn from a fresh run that uses the equalized ctx. `solve` cells are unchanged.

**Re-baselining checklist (anchor for paper figures).** Pre-2026-04-29 results — including `cluster-26042026` and the smoke job `17263071` — must be relabeled or redrawn for any of the following metrics:
1. Per-task `truncation` rate (`done_reason == "length"`).
2. `FR_THINK_OVERFLOW` rate per `(model, task)` cell.
3. Tools-vs-no-tools accuracy gaps (the paper's headline) — old asymmetric ctx (`8192` tools / `12288` no-tools+think) confounds the comparison.
4. `ollama_parse_error` counts on `validate_plan`/`simulate` (mid-emission truncation produced most of these under the old caps).
5. Chain-step (`step-3`, `step-4`) `FR_THINK_OVERFLOW` rates — `num_ctx_chain` 12288 → 16384 in the same-day follow-up entry.

`solve` (tools and no-tools) is unaffected by the non-solve `num_predict` bump but its `num_ctx` did change 8192 → 16384. Trends remain interpretable; absolute truncation counts and `FR_THINK_OVERFLOW` rates do not.

**Cluster-side note.** Per-call KV cache approximately doubles vs the prior 8192 baseline (16384 single-task tools / 16384 single-task no-tools+think / 12288 chain). Existing `--mem` lines in `cluster-experimenting/run_condition_rtx.sbatch` were sized against the old ctx; first sweeps after this change should leave a margin and post-mortem `sacct/MaxRSS` to right-size if needed. The runtime VRAM guard (`>85% post-warmup → exit 3`) should still catch a blowup before it crashes the whole pack.

**Files.** `pddl_eval/runner.py`, `run_experiment.py`, `README.md`, `EXPERIMENTS_FLOW.md`, `cluster-experimenting/README.md`, `cluster-experimenting/run_condition_rtx.sbatch`, `development/OPEN_ISSUES.md` (closes ISS-007).

---

## 2026-04-29 — PR-3: fixture buildout to 20 domains × 5 problems × (5 valid + 5 invalid) plans (1240 fixtures total)

**Motivation.** `development/FRAMEWORK_EXTENSION_PLAN.md` §3.2 PR-3 — scale the fixture set from 10 domains × 1 problem × 1 plan (60 files total) to 20 domains × 5 problems × 5 valid + 5 invalid plans per problem (1240 files total) so per-task counts grow from ~80/cell to ~1840/cell, giving Wilson confidence intervals usable signal at moderate sweep budgets.

**Changes (4 commits on `framework-ext-pr3`).**

- **C-A (loader/GT/runner schema + generator scaffolding).** New `pddl_eval/domains.py` schema returns `{type, domain, problems, negatives: {domain, problems[5], plans_per_problem: {pname: {valid[5], invalid[5]}}}}`. `generate_ground_truth` extends per-problem entry with `valid_plans: list[{plan, plan_valid}]` and adds a `_negatives` slot per domain validated 5-fixtures-per-kind. `pddl_eval/runner.py:TaskResult` gains `plan_label: str` field; the job builder generalizes the negative branch from one-per-kind to N-per-kind. `tools/_taxonomies.py` (new) ships pure-text mutators; `tools/build_fixtures.py` (new) drives the migrate + per-domain generator pipeline against MCP. 35 sub-checks in `tests/test_fixtures.py` cover the mutators + a loader-shape regression.
- **C-B (existing 10 domains).** `git mv` rename the legacy `_0` suffix layout (`domain_0.pddl`→`domain_neg.pddl`, `p01_0.pddl`→`n01.pddl`, `p01_0.plan`→`p01_b1.plan`, `p01.plan`→`p01_v1.plan`); `seed-problems` from `~/personal/online_model_learning/benchmarks/olam-compatible/` for classical and from the bundled `dataset_4_numeric_domains` for numeric; per-domain `gen-valid-plans + gen-invalid-plans + gen-invalid-problems + gen-invalid-domain`. Hand-authored `domains/numeric/depot/p05.pddl` (dataset has only 3 unique instances) and `domains/numeric/farmland/p02..p05.pddl` (no public source).
- **C-C (10 new domains).** 5 new classical (gripper, miconic, parking, tpp, zenotravel — substitute for spec's "logistics") sourced from olam-compatible. 5 new numeric (delivery, drone, gardening, block-grouping, zenotravel-numeric) sourced from matteocarde/patty (IPC-2023 mirror + `files/`); zenotravel-numeric p02-p05 hand-authored because IPC-2023 only had 1/8 ENHSP-solvable instance among the smallest. Substitution drift documented in `FRAMEWORK_EXTENSION_PLAN.md` § "PR-3 drift from spec".
- **C-D (loader cleanup + docs).** `pddl_eval/domains.py`: drop legacy `_0`-suffix compat branches now that all 20 domains are on the flat layout. `tests/test_fixtures.py`: tighten loader-shape assertions to expect 20 domains, 5/5/5/5 fixture counts. `domains/README.md`, `EXPERIMENTS_FLOW.md` §6, `development/FRAMEWORK_EXTENSION_PLAN.md` (this entry's drift section) updated.

**Validation.**
- `tests/test_fixtures.py`: 33/33 passed (mutators + loader-shape).
- `tools/build_fixtures.py all <domain>` ran end-to-end on all 20 domains; every committed fixture validated via `validate_pddl_syntax` at generation time (positives expected True, negatives expected False).
- File count audit: `find domains/{classical,numeric}/ -type f` → 1240 files, exactly matching §3.3.7 target.
- Smoke gate (deferred to post-merge): single-task `--smoke` on default `blocksworld` to be diffed against PR-2 anchor on the calibrated projection (`{model, condition, task, successes, n, failure_reasons, tool_selected}` excluding `gpt-oss:20b`); only the `p01`/`n01` rows are byte-comparable since `p02..p05`/`n02..n05` are first-time data points.

**Bug-taxonomy expansions.**
- Invalid-problem grew from 4 mutators (today's spec) to 6: added `problem_drop_objects` and `problem_drop_init` because `problem_corrupt_paren` validates as TRUE on `parking` (validator is permissive of trailing `)`). Spec's 5-bug intent is preserved at the per-domain output level.
- Invalid-plan stays at 4 implemented mutators (vs spec's 5): spec's #4 (missing-action) is operationally `plan_drop_step_k`; #5 (extra-action) is approximated by `plan_duplicate_step` (re-inserts an action that typically violates its own precondition the second time). Padding with extra-truncation variants covers the gap.

**Compatibility.** All existing PR-2 results in `results/` remain valid for the `p01`/`n01`/`v1`/`b1` rows (these are what was on disk before C-A landed; the migration was a `git mv` of the same content). New rows (`p02..p05`, `n02..n05`, `v2..v5`, `b2..b5`) are first-time data points with no anchor to compare against.

**Closes / narrows.** No `ISS-###`. Closes the PR-3 milestone in `FRAMEWORK_EXTENSION_PLAN.md` §3.2.

**Files.** `pddl_eval/domains.py`, `pddl_eval/runner.py`, `tools/_taxonomies.py` (new), `tools/build_fixtures.py` (new), `tests/test_fixtures.py` (new), 1240 files under `domains/{classical,numeric}/`, `domains/README.md`, `EXPERIMENTS_FLOW.md`, `development/FRAMEWORK_EXTENSION_PLAN.md`.

---

## 2026-04-29 — Cluster roster refresh: Qwen3.6 medium/large + Nemotron-3-Nano replacing gpt-oss

**Motivation.** Three concurrent prompts converged: (1) Qwen3.6 became available 2026-04-{16,22} as direct architectural successors to `Qwen3.5:27b` (dense 27B) and `Qwen3.5:35b` (35B-A3B MoE), both Apache-2.0 on Ollama with comparable or smaller VRAM footprints; (2) `gpt-oss:20b` had been the chronic source of methodology noise — CHANGELOG 2026-04-28 documents it producing structurally different responses at T=0 across deterministic runs, and the smoke-gate excludes it from byte-equality; (3) the swap risk-reward was favourable because the diversity slot (only non-Qwen/non-Gemma model in the roster) needed a non-Qwen replacement to preserve family coverage.

**Decision.** Roster updated from
```
Qwen3.5:0.8B  gpt-oss:20b  Qwen3.5:27b  Qwen3.5:35b  gemma4:31b
```
to
```
Qwen3.5:0.8B  nemotron-3-nano:30b  qwen3.6:27b  qwen3.6:35b  gemma4:31b
```
- **Medium slot**: `Qwen3.5:27b` → `qwen3.6:27b` (dense 27.8B, 17 GB Q4_K_M, 256K context). Same size class.
- **Large slot**: `Qwen3.5:35b` → `qwen3.6:35b` (35B-A3B MoE, 24 GB Q4_K_M, 256K context). Same A3B architecture as the prior 35B; ~6 GB smaller peak resident.
- **Diversity slot**: `gpt-oss:20b` → `nemotron-3-nano:30b` (NVIDIA hybrid Mamba+MoE+Attn, 30B/3.5B-active, 24 GB, 1M context). NVIDIA's release blog benchmarks claim wins over `gpt-oss-20b` and `Qwen3-30B-A3B-Thinking`; ~2.2× gpt-oss inference throughput. Reasoning + non-reasoning unified, matching the existing `--think on/off` axis.
- **Small slot**: `Qwen3.5:0.8B` unchanged (no Qwen3.6 small variant has been released yet).
- **Gemma slot**: `gemma4:31b` unchanged (second non-Qwen anchor).

**Net effect.** Pack peak VRAM drops from ~30 GB (`Qwen3.5:35b`) to ~24 GB (`qwen3.6:35b`). 96 GB rtx_pro_6000 headroom widens. Pulling `qwen3.6:27b` brings vision components inside the weight file (it's tagged `image-text-to-text`); text-only inference is unaffected and the size on disk is the standard Q4_K_M 17 GB.

**Files touched.**
- `cluster-experimenting/submit_with_rtx.sh`: `MODELS=(...)` at `--smoke` block, `--all` recursive call, and surrounding header / VRAM comments.
- `cluster-experimenting/run_condition_rtx.sbatch`: VRAM-fit table, peak-resident notes, and direct-sbatch invocation example.
- `cluster-experimenting/README.md`: large-band substitution paragraph, quickstart pack list, troubleshooting peak figure, scp example, and the per-section sweep description.
- `EXPERIMENTS_FLOW.md` §2 (Experimental Dimensions), §10 (Running Experiments), §11 (Differences from the Original Paper).

**No code changes.** `run_experiment.py`, `summary.py`, scoring, prompts, and result schema are untouched. This is a string-level roster swap.

**Compatibility / drift framing.** The smoke-gate (CHANGELOG 2026-04-28's `diff_smoke.sh`) is byte-equality oriented and will fail on every swapped slot. The three swapped models join `gpt-oss:20b` on the "expected drift" list — the gate continues to run against `Qwen3.5:0.8B` and `gemma4:31b` (unchanged slots) for byte-equality regression detection. For the swapped slots, drift is interpreted via outcome-distribution comparison vs. the prior anchor in `results/cluster-202604{26,27,28,29}/`, with the expectation that drift trends toward improvement: higher success rate (especially on the cells flagged in ISS-006 and ISS-007), fewer `FR_OLLAMA_PARSE_ERROR` rows (the gpt-oss → Nemotron swap should eliminate this bucket), fewer `done_reason="length"` truncations (Qwen3.6's 256K context and Nemotron's 1M context give the harness much more headroom), and `tool_selected` rates that stay roughly comparable or improve. Existing rows for `Qwen3.5:27b`, `Qwen3.5:35b`, and `gpt-oss:20b` are preserved on disk as the drift anchor, not as ongoing headline numbers. The 2026-04-27 large-band substitution (`gpt-oss:120b` → `Qwen3.5:35b`) is now superseded by `qwen3.6:35b`.

**Validation.** Cluster preflight to pull the three new tags (`ollama pull qwen3.6:27b qwen3.6:35b nemotron-3-nano:30b`) and a single-condition smoke per replacement model (`run_experiment.py --smoke --models <new> --tasks solve validate_domain`) before the next full sweep. The drift-direction check on `solve` and `validate_domain` (think=off) compares per-cell success / failure-reason / done_reason / tool_selected against the same cell from the most recent anchor; the swap passes if 3 of 4 metrics move in the expected direction across the three swapped slots.

**Open issues.** No `ISS-###` is closed by this change; none opened — methodology is untouched.

---

## 2026-04-28 — PR-2 hotfix: per-condition sub-pass split to keep `num_ctx` constant per call

**Motivation.** Cluster smoke 17244356 (PR-2 head `0a78ae0`) deadlocked at the `tools→no-tools` boundary inside the `think=on` smoke pass. py-spy showed the asyncio loop idle, GPU at 0%, 4 keep-alive sockets with no in-flight bytes, and Ollama serving the model at the original `context_length: 8192` despite the no-tools coroutines requesting `num_ctx=12288`. Mid-call `num_ctx` flips deadlock Ollama under concurrency.

**First attempt (`71dcff7`)** dropped the condition axis from `effective_num_ctx` — making tools+think=on use `num_ctx=12288` too, so num_ctx was constant within a pass. Smoke 17245419 ran clean (no deadlock) but the byte-equality diff against PR-1 anchor showed accuracy regression on tools-side think=on cells (e.g. `Qwen3.5:0.8B tools validate_plan`: PR-1 `2 OK + 1 verdict_mismatch + 1 loop_exhausted` → PR-2 `0 OK + 2 think_overflow + 2 loop_exhausted`, accuracy halved). The bigger context window changed the model's behaviour on tools-side runs that were graded fine in PR-1. This violated the spec, which required tools-side to keep 8192.

**Final fix (this entry).** Reverted `effective_num_ctx` to the spec rule (`think!=off AND not with_tools`). Avoid the mid-call deadlock by splitting at the CALLER level: `async_main` runs `(--conditions=both, think!=off)` as two sequential `run_single_task_experiment` calls, one per condition. Each call has uniform `num_ctx`; the model can reload between calls because no requests are in flight at the boundary. Total wallclock is unchanged (same job count, same per-call concurrency).

**Changes.**

- `pddl_eval/runner.py`: `effective_num_ctx` reverted to `(think is not False and not with_tools)` rule (matches PR-2 spec).
- `run_experiment.py`: new `_run_single_task_split(think_value, cond)` helper inside `async_main`. When `cond=="both"` and `think_value is not False`, it splits into `("tools", "no-tools")` sub-passes. Both the smoke loop and the production path go through this helper; behaviour is identical for cases where no split is needed (`cond != "both"` or `think_value is False`).
- `EXPERIMENTS_FLOW.md` §5 + §9: documented the per-condition rule (matches spec) plus the implementation mechanism (sub-pass split).

**Verification.** Cluster smoke to be re-run on the new HEAD; expected outcome — diff against PR-1 anchor shows ONLY the gate-lift expansion (`(no-tools, think=on/default)` cells go from `n=2 → n=4` because the gate is lifted). Tools-side rows should be byte-equal on the calibrated projection (modulo T=0 nondeterminism per CHANGELOG 2026-04-28 calibration).

**Compatibility.** None of the partial cluster runs from today (cancelled job 17244356, completed job 17245419) become an anchor candidate — the next smoke (post-fix) IS the canonical post-PR-2 baseline. Local laptop runs at concurrency=4 were never exposed to the deadlock because `OLLAMA_NUM_PARALLEL` was unset, serializing requests at the Ollama layer.

**Closes / narrows.** No `ISS-###`. Adjusts the same-day PR-2 entry below.

**Files.** `pddl_eval/runner.py`, `run_experiment.py`, `EXPERIMENTS_FLOW.md`.

---

## 2026-04-28 — PR-2: token + thinking instrumentation; lift no-tools+think abort gate; close ISS-018

**Motivation.** Three coupled needs from `development/FRAMEWORK_EXTENSION_PLAN.md` §3.2 PR-2:

1. **Quantify the token-reduction story for the paper.** With-tools shrinks the model's prompt budget by externalising plan / state / verdict computation to MCP. We had no token data on disk — every `client.chat()` response carried `prompt_eval_count` + `eval_count` and we discarded them.
2. **Make `(no-tools, think=on/default)` a valid run.** The previous `--think off` gate at `run_experiment.py:200-218` aborted any no-tools sweep under `--think on/default`. Lifting it requires capturing thinking content separately so it does not pollute `extract_verdict` / `extract_plan_lines` (a thinking model that emits `VERDICT: VALID` inside its `<think>` block but `VERDICT: INVALID` outside should grade INVALID).
3. **Bound the thinking-spiral wallclock.** Calibration on 2026-04-28 (`.local/calibrate_num_ctx_thinking.py`) showed qwen3:0.6b solve hitting `done_reason=length` at p+e=8680 (over the existing `num_ctx=8192` cap); a separate `--num-ctx-thinking` flag lifts the budget for the thinking path without inflating it for tool-condition runs.

**Changes.**

- **`pddl_eval/scoring.py`**: added `FR_THINK_OVERFLOW = "think_overflow"` constant; added module-level `_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)`; applied it inline at the head of `extract_plan_lines` and `extract_verdict` so `<think>` blocks emitted in `message.content` (rather than the structured `message.thinking` field) cannot leak action-shaped lines or VERDICT tokens into the graded answer. `_classify_step_failure` signature unchanged — FR_THINK_OVERFLOW is classified inline in `evaluate_one`.
- **`pddl_eval/chat.py`**: `chat_with_tools` and `chat_without_tools` extended to return `(..., tokens, thinking)`. Tokens are accumulated across tool-call turns (`prompt_eval_count`, `eval_count`, `total_duration`, `eval_duration`, `turns`); thinking is the LAST turn's `message.thinking` content (decision recorded in plan: tool-selection reasoning from earlier turns is observable via `tool_calls[]`; the thinking that produced the graded response is the last turn). New `_response_field` and `_response_thinking` helpers handle dict and pydantic ChatResponse shapes, mirroring `_response_done_reason`.
- **`pddl_eval/runner.py`**: added `DEFAULT_NUM_CTX_THINKING = 12288` (1.4× headroom over the calibration max of 8680, decreased from the spec's 16384 to save ~25% KV-cache) and `THINKING_SNAPSHOT_LEN = 4096` (asymmetric vs `RESPONSE_SNAPSHOT_LEN=500`: thinking spirals are structurally longer than graded responses; calibration observed up to ~30K thinking chars on qwen3:0.6b). `TaskResult` gained `thinking: str = ""` and `tokens: dict = field(default_factory=dict)` fields. `evaluate_one` picks `effective_num_ctx = num_ctx_thinking if (think is not False and not with_tools) else num_ctx` — bigger budget only for the no-PDDL-tools+think cell. FR_THINK_OVERFLOW classification is inline before `_classify_step_failure` (precedence: FR_LOOP_EXHAUSTED > FR_THINK_OVERFLOW > generic length-override). `run_single_task_experiment` and `run_chain_experiment` thread `num_ctx_thinking` through.
- **`run_experiment.py`**: removed the abort gate at lines 200-218 entirely; added `--num-ctx-thinking` CLI flag (default `DEFAULT_NUM_CTX_THINKING`); added `num_ctx_thinking` to the `meta` dict and the run-banner; updated the smoke `think_passes` table from `[("on", True, "tools"), ("off", False, "both")]` to `[("on", True, "both"), ("off", False, "both")]` so all four `(condition × think)` cells get smoke coverage. **ISS-018 closed**: chain phase is skipped entirely when `args.think == "off"` (mirrors the existing `not cond_with_tools → continue` chain skip), with an explicit print explaining the skip.
- **`pddl_eval/summary.py`**: no change — `asdict(TaskResult)` picks up the new `tokens` + `thinking` fields automatically; the `failure_reasons` table aggregates whatever `FR_*` strings appear, so FR_THINK_OVERFLOW surfaces without code change.
- **`tests/test_scoring.py`**: added think-block strip cases to `test_extract_plan_lines` and `test_extract_verdict`; new `test_classify_step_failure_think_overflow` verifies FR_THINK_OVERFLOW survives the truncation override and that FR_LOOP_EXHAUSTED still beats it on tool-loop cap-hit.
- **`EXPERIMENTS_FLOW.md`**: §5 "No-tools matrix gating" replaced by "Single-task vs chain-phase gating" — the only surviving rules are (a) chain phase skips no-tools (artifact propagation), (b) chain phase skips think=off (ISS-018 closure). §9 per-record schema documents `tokens`, `thinking`, `failure_reason`, `truncated`, `done_reason`; meta schema adds `num_ctx_thinking`; `failure_reasons` description names FR_THINK_OVERFLOW.
- **`development/OPEN_ISSUES.md`**: ISS-018 marked closed.

**Verification.**

- `bash tests/verify.sh` → all tests pass (test_scoring with new think-strip + think-overflow cases; test_check_success unchanged).
- `python3 run_experiment.py --help` → shows `--num-ctx-thinking` with the corrected help text.
- Local smoke (`PDDL_MARKETPLACE_PATH=../pddl-copilot python3 run_experiment.py --smoke --models qwen3:0.6b --tasks validate_domain validate_problem`): per-record JSON contains `tokens` (non-empty dict with `prompt > 0`, `completion > 0`, `turns >= 1`) and `thinking` (string, may be empty) on every row.
- Cluster smoke gate vs PR-1 anchor (deferred to PR-2 review): graded fields byte-equal on intersection of `(model, condition, task)` keys for byte-deterministic models per the 2026-04-28 calibration; new `(no-tools, think=on/default)` rows are candidate-only with `n > 0` per cell.

**Compatibility.** Existing 2026-04 result corpus (`results/cluster-2026042{6,7}/`) is unchanged in shape — new `tokens` and `thinking` fields are absent from those records and downstream consumers must use `r.get("tokens", {})` / `r.get("thinking", "")` patterns. `summary.py::asdict(r)` writes new fields when present; old summaries don't gain phantom fields. The `(no-tools, think=on/default)` cells were never produced before PR-2, so any future analysis comparing them against history needs a fresh baseline (next sweep). The `truncated` and graded outcomes on already-runnable cells are byte-equal post-PR-2 modulo the documented `gpt-oss:20b` and `truncated`-count noise sources from CHANGELOG 2026-04-28 (smoke-gate calibration).

**Closes / narrows.** Closes ISS-018 (think=off chain skip). No other `ISS-###` closed.

**Files.** `pddl_eval/scoring.py`, `pddl_eval/chat.py`, `pddl_eval/runner.py`, `run_experiment.py`, `tests/test_scoring.py`, `EXPERIMENTS_FLOW.md`, `development/OPEN_ISSUES.md`. `.local/calibrate_num_ctx_thinking.py` is gitignored (calibration artefact).

---

## 2026-04-28 — Smoke-gate calibration: `gpt-oss:20b` and the `truncated` count are excluded from byte-equality

**Motivation.** First production use of the PR-1 `--smoke` gate (anchor = pre-refactor `main` + cherry-picked flag commit; candidate = post-refactor `framework-ext-pr1`) flagged drift. Inspection showed 4 of 5 models (`Qwen3.5:0.8B`, `Qwen3.5:27b`, `Qwen3.5:35b`, `gemma4:31b`) byte-equal on `{success, failure_reasons, tool_selected}`, with two sources of unrelated drift:

1. **`gpt-oss:20b` produces structurally different responses** at T=0 across runs. For `(gpt-oss:20b, no-tools, solve)` the anchor returned a Markdown-table plan (graded `plan_invalid`); the candidate returned a narrative-prose plan (graded `ok`). Same model, same prompt, same hardware. Empirical confirmation of CHANGELOG 2026-04-21's `FR_OLLAMA_PARSE_ERROR` classification ("retries at TEMPERATURE=0.0 mostly reproduce the same output, so the extra API call wasn't justified" — but reproduction is not byte-perfect).

2. **The standalone `truncated` count flips on boundary records** even when grading is identical. For `(Qwen3.5:0.8B, tools, validate_problem)` both runs returned `{ok:2, verdict_mismatch:2}` with identical `tool_selected=4`; one anchor record finished at `done_reason=length` while the corresponding candidate record finished at `done_reason=stop` — the model said the same wrong verdict, just with a marginally different token-stream length. The `truncated` field counts all `done_reason=="length"` records regardless of whether truncation drove the failure; when it does drive failure, that signal already lives in `failure_reasons` as `truncated_no_answer`.

**Decision.** Both signals are token-stream noise downstream of T=0 sampling, not refactor regressions. Restrict the smoke gate's byte-equality projection to fields that are deterministic when the model is.

**Changes.**

- `.local/scripts/diff_smoke.sh` (developer-local, gitignored):
  - Accepts glob patterns rather than single files (each `--smoke` invocation writes one `results/smoke_<sha>_*/` per model; aggregation is now done in the diff helper, not by the caller).
  - Default excludes `gpt-oss:20b` from the comparison; `--include gpt-oss:20b` puts it back for inspection.
  - Drops `truncated` from the projection. Final graded fields: `{model, condition, task, successes, n, failure_reasons, tool_selected}`.
- No code changes to `pddl_eval/`, `run_experiment.py`, or cluster scripts. The PR-1 refactor is byte-equal on byte-deterministic models — proven by the 4-of-5 result.
- `.local/ORCHESTRATION.md` updated with the new diff invocation form.

**Verification.**

```
bash .local/scripts/diff_smoke.sh \
  'results/smoke_74f650a_*/summary_*.json' \
  'results/smoke_79bfef2_*/summary_*.json'
# → OK: graded outcomes match (excluded: 'gpt-oss:20b'; rows: 40 each)

bash .local/scripts/diff_smoke.sh --include gpt-oss:20b \
  'results/smoke_74f650a_*/summary_*.json' \
  'results/smoke_79bfef2_*/summary_*.json'
# → DIFF (as expected — known-flaky model included)
```

**Compatibility.** Result schema unchanged. `pddl_eval/summary.py` still emits `truncated` per row (the field is informational and used by `print_fail_reasons_table`); only the gate's projection drops it. The retired single-file form of `diff_smoke.sh` (PR-1 plan §"Anchor workflow") still works — passing a literal path that isn't a glob falls through to the single-file branch.

**Closes / narrows.** No `ISS-###` (model-side adherence is data, not a harness defect — see memory `feedback_tool_adherence_is_data.md`). PR-1 smoke gate is GREEN; the refactor is safe to merge.

**Files.** `.local/scripts/diff_smoke.sh` (rewrite, gitignored). `.local/ORCHESTRATION.md` (note added, gitignored).

---

## 2026-04-28 — `status.sh` honest reporting for smoke jobs

**Motivation.** Cross-referencing live smoke `.out` files against `status.sh` showed the reporter printing `cond 0/4`, `ST 0/250`, `chain 0/400` for jobs that were actually progressing. Three hardcoded assumptions in the parser broke for smoke runs:

1. `PROGRESS = re.compile(r'\[ *(\d+)/250 ')` — the denominator was pinned to 250 (the per-condition single-task count for a paper sweep). Smoke totals are ~5–15 per pass; the regex matched 0 times → reported the hardcoded fallback.
2. `BANNER` looks for `CONDITION: <cond> ... started`, the matrix-loop header that the smoke fast-path in `run_condition_rtx.sbatch` skips. Smoke prints `MODEL: ... smoke (--smoke) started` instead → 0 banners.
3. The sbatch's setup `Conditions:` and `Think modes:` lines are still printed before the smoke fast-path branches, so `total_banners` got computed as `4 × 1 = 4` against a matrix that smoke is NOT running. The denominator was technically correct for the planned matrix but irrelevant to what the job was doing.

**Changes.**

- `.claude/skills/cluster-ops/scripts/status.sh`:
  - **Smoke detection by job-name suffix** (`_smoke` / `_smoke-shuffle`, set by `submit_with_rtx.sh:213-218`). Cleaner than .out parsing and matches the queue line directly.
  - **Smoke-specific reporting**: phase = `smoke pass {1,2}/2 (think={on,off})` from the last `Smoke pass: think=X, conditions=Y` line (printed by `run_experiment.async_main`); ST = the actual `[N/M]` from the last progress line; chain = `n/a` (smoke disables chains).
  - **Generalized `PROGRESS` regex** to capture both numerator and denominator: `r'\[ *(\d+)/(\d+) '`. Output is `f"{n}/{m}"` instead of the hardcoded `f"{st}/250"`. Future-proofs against custom `--chain-samples`, task-subset sweeps, or any other non-paper run shape.
  - **Chain output** drops the hardcoded `/400` — reports just the running count (`chain_done`) since the actual denominator (`chain_lengths × samples`) isn't in scope at parse time.

**Compatibility.** Read-only reporter — no impact on results, sbatch behavior, or run_experiment.py. Production-sweep `.out` files still parse correctly through the existing matrix-job branch (the generalized PROGRESS regex strictly extends the old one — same numerator capture, plus the denominator).

**Verification.** `bash -n` syntax-clean. Python regex check confirmed `SMOKE_PASS` matches the actual `Smoke pass: think=on, conditions=tools` lines emitted by `run_experiment.async_main`. Live cluster verification deferred — VPN unreachable at edit time; the parser logic was hand-traced against the actual .out structure (sbatch:160-161 setup lines + sbatch:223-226 smoke header + run_experiment.py:355 pass header + runner._format_progress `[N/M]` output).

**Files.** `.claude/skills/cluster-ops/scripts/status.sh`.

---

## 2026-04-28 — PR-1 review cleanup

**Motivation.** Code review on PR #20 surfaced four minor cleanup items. All are <10 LOC each; none change behavior on graded outcomes.

**Changes.**

- **`run_experiment.py`**: dropped the auto-built `__all__` (it overcaptured stdlib names like `argparse`/`asyncio`/`Path` since it was computed off `globals()`). No callers do `from run_experiment import *` anywhere in the repo, so the removal is a pure shrinkage of the public surface. Smoke-aware Conditions banner now prints `Conditions: smoke (think=on→tools, think=off→both)` under `--smoke`/`--smoke-shuffle` instead of the misleading `Conditions: both`.
- **`pddl_eval/chat.py`**: dropped the unused `import ollama`. Type hints in this module are quoted strings (`"ollama.AsyncClient"`), so the import was load-bearing for neither runtime behavior nor static checkers.
- **`tests/test_scoring.py`**: added `test_shard_filter` covering N=1 fast path, determinism (same key → same bucket), pinned-host stability (sha256 not Python `hash()`), exactly-one-shard membership over a 144-key set, full coverage of `i ∈ [0, N)`, and rough-balance check.

**Dismissed (with rationale).**

- `runner.py:670` async closure over `sem` reassigned in chain-length loop — currently correct (each iteration awaits its tasks before the next iteration rebinds `sem`); hoisting would harden against a hypothetical interleaved-concurrency refactor that would require a redesign anyway.
- `cell_assignment` for negatives in `--smoke-shuffle` — documented behavior (count varies slightly by seed when the random domain lacks a `_negatives` slot for the task). Smoke-shuffle is a discovery tool, not a paper baseline.
- 626-LOC `run_experiment.py` vs 150-LOC estimate — the smoke think-loop wrapper is dispatch logic that belongs at the CLI layer, not in `pddl_eval/runner.py`.

**Verification.** `bash tests/verify.sh` → 240/240 pass (was 86/86 — the new `test_shard_filter` adds 154 sub-checks via the 144-key membership loop). `python3 -c "import run_experiment, pddl_eval.chat, pddl_eval.runner"` clean. Smoke gate not re-run — none of these changes affect graded outcomes.

**Files.** `run_experiment.py`, `pddl_eval/chat.py`, `tests/test_scoring.py`.

---

## 2026-04-27 — `run_experiment.py` split into `pddl_eval/` package; `--smoke`/`--smoke-shuffle`/`--shard`/`--domains`/`--problems` flags

**Motivation.** PR-1 of the four-PR framework extension (see `development/FRAMEWORK_EXTENSION_PLAN.md` §3.2). The 2,171-LOC monolith was bottlenecking methodology iteration and the upcoming Paper-2 agent extension; the split preserves zero semantic change while unlocking a regression-anchor workflow (`--smoke`) and N-way cluster parallelism (`--shard`).

**Changes.**

- **New package `pddl_eval/`** (7 files, 2,007 LOC moved): `prompts.py`, `chat.py`, `domains.py`, `scoring.py`, `runner.py`, `summary.py`, `__init__.py`. Import DAG is one-directional (`prompts → none; chat → none; domains → chat; scoring → chat; runner → prompts/chat/domains/scoring; summary → prompts/runner/scoring`); no cycles.
- **`run_experiment.py`** reduced from 2,171 → 626 LOC. Now CLI-only: argparse, `async_main`, `main`, plus `_git_short_sha_dirty()` and `resolve_plugin_dirs()` setup helpers, plus an explicit re-export shim so `tests/test_scoring.py` and `tests/test_check_success.py` keep working without edits.
- **CLI flags.**
  - `--smoke` — fixed slice (1 domain × 1 problem × 1 variant × 5 tasks × 2 conds × 2 think modes); auto-overrides `--domains blocksworld --problems p01 --num-variants 1 --chain-samples 0 --conditions both`; iterates `--think={on,off}` internally; output dir `results/smoke_<git-sha>_<ts>/`.
  - `--smoke-shuffle` — same shape as `--smoke` but each `(model, task)` cell draws a random `(domain, problem)` from the full grid using `--seed`. Mutually exclusive with `--smoke`.
  - `--shard i/N` — deterministic SHA-256 partitioner over `(model|task|domain|problem|variant)` for cluster parallelism. `with_tools` is excluded so paired comparisons stay together. Chains run only on shard 0.
  - `--domains DNAME [...]` and `--problems PNAME [...]` — general-purpose post-`load_domains` filters (added because no domain-level filter existed; required by `--smoke`, useful standalone for `--shard` debugging).
- **Cluster scripts.** `cluster-experimenting/submit_with_rtx.sh` accepts `--smoke`/`--smoke-shuffle`/`--shard` and exports `SMOKE`/`SMOKE_SHUFFLE`/`SHARD` env vars (with smoke pinning the 5-model pack and a 2h walltime). `run_condition_rtx.sbatch` reads those env vars: when `SMOKE=1`, it skips the inner `THINK_MODES × CONDITIONS` loop (the smoke wrapper iterates think internally) and runs a single packed `--smoke` invocation per model under the existing outer model loop; otherwise appends `--shard $SHARD` to the regular invocation.
- **`.gitignore`** adds `.local/` (developer-local scratch — anchors, runbooks, the `diff_smoke.sh` helper).

**Compatibility.** Result schema unchanged (same `TaskResult` fields, same `summary.json` shape, same MCP tool contract). Existing `results/` directories remain valid. `tests/verify.sh` reports 86/86 passes with the re-export shim (49/49 `test_scoring.py` + 37/37 `test_check_success.py`) — no test edits needed.

**Drift from PR-1 spec** is recorded in `development/FRAMEWORK_EXTENSION_PLAN.md` §3.2 under "PR-1 drift from spec". Highlights: `_safe_json_loads`/`_parse_validation_verdict` placed in `chat.py` (not `domains.py`) to avoid `scoring → domains` cycle; `TaskResult` lives in `runner.py` (the producer module); the CLI shim is 626 LOC (estimate was ~150) due to the smoke think-loop wrapper and the explicit re-export shim.

**Verification.** `bash tests/verify.sh` → 86/86 pass. `python3 -c "import pddl_eval.{prompts,chat,domains,scoring,runner,summary}"` → all clean. `python3 run_experiment.py --help` shows all new flags. The byte-equal anchor gate against pre-refactor `main` is run by the developer locally (cherry-pick the smoke-flag commit onto a throwaway branch off `main`, run `--smoke`, save anchor, then run `--smoke` post-refactor and `bash .local/scripts/diff_smoke.sh anchor.json new.json`); see `.local/ORCHESTRATION.md`.

**Files.** Created: `pddl_eval/{prompts,chat,domains,scoring,runner,summary,__init__}.py`. Modified: `run_experiment.py`, `cluster-experimenting/{submit_with_rtx.sh, run_condition_rtx.sbatch}`, `.gitignore`, `development/{FRAMEWORK_EXTENSION_PLAN.md, CHANGELOG.md}`.

---

## 2026-04-27 — cis-ollama path retired; sole submission is `rtx_pro_6000:1` self-deploy

**Motivation.** Eliminate the last shared-resource axis. The cis-ollama transport (`submit_all.sh` waves against `https://cis-ollama.auth.ad.bgu.ac.il`) introduced contended `MAX_LOADED_MODELS`/`NUM_PARALLEL`, eviction thrashing on the 120b cell (560 s/sample shared vs 291 s isolated, CHANGELOG 2026-04-20), VPN/TLS coupling (`OLLAMA_INSECURE`, self-signed cert), and a different model inventory than the paper's. The rtx self-deploy was already production for the 5-model active sweep; the cis path was kept only as a fallback for `gpt-oss:120b`. With 120b out of the active sweep (substituted by `Qwen3.5:35b` in the large-model size band), the fallback is no longer load-bearing.

**Decision.** Hard-pin `rtx_pro_6000:1` (`--mem=80G` per IT 2026-04-27 cap) as the sole self-deploy GPU class. The 5-model `--all` pack peaks at `Qwen3.5:35b` (~30 GB resident), well inside 96 GB VRAM under `MAX_LOADED_MODELS=1` sequencing. `--gpu-type rtx_6000` survives as an opt-in escape hatch (48 GB, `--mem=48G`) for use only when `rtx_pro_6000` is queue-saturated; the prior `sinfo` auto-detection and `HAS_120B` routing branch are removed for "consistency and known variables".

**Changes.**

- **Deleted.** `cluster-experimenting/run_condition.sbatch` (cis CPU sbatch), `cluster-experimenting/submit_all.sh` (5-wave `afterok` orchestrator), `cluster-experimenting/submit_120b_cis.sh` (120b cis fallback), `remote_background.sh` (cis laptop driver), `.local/ollama/cis-cluster-ollama.md` (cis runbook), `.claude/skills/cluster-ops/scripts/diag.sh` (cis diagnostic).
- **`run_experiment.py`.** Drop `BGU_DEFAULT_MODELS` constant and the `is_remote` model-fallback at startup. Drop `--ollama-insecure` flag and its `httpx` `verify=False` plumbing. Drop the `is_remote`-gated `tls_verify` segment in the startup banner and the `is_remote` field from `meta`. Strip cis-specific examples from `--ollama-host` help. The `KEEP_ALIVE` rationale comment generalizes — no longer cites cis-server defaults.
- **`run_background.sh`.** Drop the `REMOTE_OLLAMA` detection block, the BGU model selection, the cis-side curl reachability check, and the per-condition `HOST_ARGS` injection. Becomes unambiguously local-only.
- **`cluster-experimenting/run_condition_rtx.sbatch`.** Default GPU `rtx_6000:1 → rtx_pro_6000:1`; default mem `48G → 80G`. Header VRAM table drops the 120b row and reframes the size band around Qwen3.5:35b.
- **`cluster-experimenting/submit_with_rtx.sh`.** Hard-pin `GPU_TYPE=rtx_pro_6000` as the default. Drop the `sinfo`-driven auto-detect, the `HAS_120B` routing branch, and the rtx_6000 `HAS_120B` defensive gate. Keep `--gpu-type` as opt-in override per user direction. `--all` model list unchanged (5 models without 120b).
- **`.claude/skills/cluster-ops/`.** `SKILL.md` rewritten for single-backend submission; `scripts/preflight.sh` drops the cis reachability probe; `scripts/aggregate.py:host_tag()` drops the `cis` branch (old summaries with `host: cis-ollama.auth.ad.bgu.ac.il` now tag as `?` — correct given they predate the standardization).
- **Docs.** `README.md`, `EXPERIMENTS_FLOW.md` (§1, §2, §9 meta, §10, §11), `cluster-experimenting/README.md` (full rewrite), `development/FRAMEWORK_EXTENSION_PLAN.md` (already-landed table + decision-log entry), `.local/ORCHESTRATION.md` (jq filter for hostname-independent meta diff).

**Compatibility.** Result schema unchanged (`single_task_*.json`, `chain_*.json`, `summary_*.json`). Old summaries that recorded `meta.is_remote: true/false` and `meta.host: cis-ollama.auth.ad.bgu.ac.il` still parse — `host_tag()` now returns `?` for the cis bucket, and `is_remote` is simply a no-op key going forward. No `ISS-###` closed (no cis-ollama issue was tracked); the change is not a fix, it's a methodology pin.

**Cost.** Single packed `--all` job: ~3.5 d wall for the full sweep (5 models × 4 tools-conditions × 2 think modes; ~17 h/model upper bound), ~24 h for `--no-tools` (5 models × 4h). Existing `submit_with_rtx.sh:212-214` time scaling (4d for N>1) covers both.

**Verification.** Local dry-runs:
- `bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B --dry-run` → `rtx_pro_6000:1 --mem=80G`.
- `bash cluster-experimenting/submit_with_rtx.sh --all --dry-run` → 5 models, `rtx_pro_6000:1`, `--time=4-00:00:00`.
- `bash cluster-experimenting/submit_with_rtx.sh --all --no-tools --dry-run` → 5 models, `--time=20:00:00`.
- `bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:0.8B --gpu-type rtx_6000 --dry-run` → `rtx_6000:1 --mem=48G` (opt-in path still works).
- `python3 run_experiment.py --help` → no `--ollama-insecure` in arg list; `--ollama-host` help text has no cis example.
- `python3 -c "import ast; ast.parse(open('run_experiment.py').read())"` → AST clean.

**Files.** Deleted: `cluster-experimenting/{run_condition.sbatch, submit_all.sh, submit_120b_cis.sh}`, `remote_background.sh`, `.local/ollama/cis-cluster-ollama.md`, `.claude/skills/cluster-ops/scripts/diag.sh`. Modified: `run_experiment.py`, `run_background.sh`, `cluster-experimenting/{run_condition_rtx.sbatch, submit_with_rtx.sh, README.md}`, `.claude/skills/cluster-ops/{SKILL.md, scripts/preflight.sh, scripts/aggregate.py}`, `.claude/agents/cluster-ops.md`, `README.md`, `EXPERIMENTS_FLOW.md`, `development/FRAMEWORK_EXTENSION_PLAN.md`, `.local/ORCHESTRATION.md`.

---

## 2026-04-27 — `prompt_style` axis retired (`guided` disabled, `minimal` only)

**Motivation.** Newcombe-Δ analysis on the 26042026 sweep (run during PR #18 review on the live trial JSONs under `checkpoints/cluster-26042026/results_extracted/`) confirmed `prompt_style` is the redundant axis in the design matrix:

| pooled per task | minimal | guided | Δ (guided−minimal) | 95% CI | sig |
|---|---|---|---|---|---|
| solve | 0.554 | 0.575 | +0.021 | [-0.022, +0.064] | NS |
| validate_domain | 0.555 | 0.555 | 0.000 | … | NS |
| validate_problem | 0.301 | 0.315 | +0.014 | … | NS |
| validate_plan | 0.183 | 0.177 | -0.006 | … | NS |
| simulate | 0.249 | 0.257 | +0.008 | … | NS |

(See `prompt_variant_stats.md` §5 for the per-model breakdown — Qwen3.5:0.8B leans guided +4.3pp, Qwen3.5:27b leans minimal -2.7pp; every model's CI crosses zero.) Compared to `tool_filter` (mean |Δ|=6.1pp, 7/25 cells significant), `prompt_style` is paying for ~0pp of additional signal at the cost of doubling the tools-on cell count.

**Decision.** Retire `guided`, keep `minimal` only. Three reasons:
1. Paper-aligned — `minimal` reproduces Benyamin et al. 2025 §4.1; the deviation row in `EXPERIMENTS_FLOW.md §11` collapses to "Single prompt → `minimal` only".
2. Cleaner methodology story — the harness contributes end-to-end validation, tool curation, and balanced negatives; adding prompt engineering on top would be off-thesis.
3. Wall-clock — single-task tools-on cells halve (4 → 2 conditions per (model, think) cell).

**Changes (code preserved as documentation).**
- **`run_experiment.py:143`**: `PROMPT_STYLE_CHOICES = ("minimal",)` — single-element tuple; argparse rejects `--prompt-style guided` at parse time. Comment block explains the why.
- **`run_experiment.py:170-180`**: `_GUIDED_SUFFIX` constant and `WITH_TOOLS_SYSTEM["guided"]` dict entry **kept in code** with `# DISABLED 2026-04-27` markers. Re-enable by re-adding `"guided"` to `PROMPT_STYLE_CHOICES` — no other code change needed.
- **`cluster-experimenting/run_condition.sbatch`** + **`run_condition_rtx.sbatch`**: `CONDITIONS=` default drops `tools_per-task_guided` and `tools_all_guided`. Case branches for those labels are **commented out**, not deleted, so the wording is preserved as documentation.
- **`cluster-experimenting/submit_all.sh`**: usage-example `CONDITIONS=` override updated.
- **`run_background.sh:155`**: `PROMPT_STYLES="minimal"` (was `"minimal guided"`); two-line comment explains how to re-enable.
- **`README.md`** CLI options table, **`EXPERIMENTS_FLOW.md` §2 / §11**, **`cluster-experimenting/README.md`** Conditions section: documentation reflects the single-active-style state and the analytic justification.

**Schema / compatibility.** `prompt_style` field stays in `TaskResult` and result JSON; new sweeps will only ever record `"minimal"`. Existing 26042026 data with `prompt_style="guided"` rows remains directly analyzable (the analysis script `prompt_variant_stats_20260426.py` still computes the §5 split). Aggregators that filter by `prompt_style` will simply see one bucket going forward.

**Runtime cost.** Per (model, with-tools) cell: 240 → 120 evals (further -50% on top of the variant trim). Combined with the prompt-variant trim earlier today, the single-task axis is now ~70% smaller than the pre-PR-#18 baseline (750 → 240 evals per model).

**Verification.** Newcombe-Δ analysis was run inline against `results_extracted/` (10,000 tools-on trials). 86/86 unit tests still pass — `prompt_style="minimal"` is the existing default for the test fixtures, no test exercised `guided` directly.

**Files.** `run_experiment.py`, `run_background.sh`, `cluster-experimenting/{run_condition.sbatch, run_condition_rtx.sbatch, submit_all.sh}`, `README.md`, `EXPERIMENTS_FLOW.md`, `cluster-experimenting/README.md`.

---

## 2026-04-27 — prompt-variant trim (5→3), cluster pack overhaul, IT resource compliance

**Motivation.** Three threads bundled in one PR (#18):
1. Sweep wall time was 5× the active variants per (model, task) cell. The 26042026 sweep showed v0/v1/v2 are within ~1pp of the 5-variant pooled mean on every task; v4 is the labelless-prompt outlier and v3 is the least-representative survivor. Trimming to 3 variants saves ~40% wall-clock without losing the robustness story.
2. HPC IT email 2026-04-27: single-model jobs were allocating 12 CPUs and >80 GB RAM each, depriving other users.
3. Five-job sweeps were over-fragmenting queue priority. With `MAX_LOADED_MODELS=1`, the five small/mid models all fit one-at-a-time on a single rtx_6000 (≤36 GB resident), so packing them into one job shares the apptainer/serve startup overhead and reduces queue contention.

**Changes.**

- **`run_experiment.py`**:
  - `ACTIVE_PROMPT_VARIANTS = (0, 1, 2)` (line ~198) gates both single-task job builder (positive + negative passes) and the chain-phase template sampler. All five paraphrases stay in `PROMPT_TEMPLATES` with `# DISABLED` markers above v3/v4 — `prompt_variant` indices stay byte-stable across sweeps so v2 today is the same paraphrase as v2 in the 26042026 sweep.
  - **Justification artifact:** `cluster-experimenting/prompt_variant_stats_20260426.py` walks the 26042026 per-trial JSON and emits `prompt_variant_stats.{md,csv}` under `checkpoints/cluster-26042026/`. (v0, v1, v2) wins 4/5 tasks vs (v0, v1, v3) on the gap-from-5-variant-mean metric and is the only triple that mixes imperative with question-form paraphrases (v2 = "Is this PDDL domain syntactically correct?"). The tuple was initially shipped as (0, 1, 3) and switched to (0, 1, 2) on review.
  - `summarize_single_task()` emits `per_variant.{n, successes, success_rate, ci_lo, ci_hi[, tool_selected_*]}` per (model, condition, task) row. Lets later analysis pick a single representative variant without re-aggregating raw JSON.
  - New `print_per_variant_table()` runs after the existing single-task table so per-variant spread is visible at a glance during a run.
  - `meta` records `prompt_variants_active` alongside `num_variants`.
  - `--num-variants` flag repurposed: now means "first K of `ACTIVE_PROMPT_VARIANTS`" with default = `len(ACTIVE_PROMPT_VARIANTS)` = 3. Hard-fails on out-of-range with a message pointing at the tuple to widen — previous silent-cap behavior could mislead a researcher into thinking `--num-variants 5` reproduced the paper run.

- **`cluster-experimenting/submit_with_rtx.sh`**:
  - Multi-model packing: positional args accepted (`submit_with_rtx.sh m1 m2 ...`). Models run sequentially in one job sharing the apptainer/serve startup; `MAX_LOADED_MODELS=1` evicts the previous model before loading the next, so peak VRAM is bounded by the largest in the set.
  - `--all` shorthand now packs the 5 paper models into ONE rtx_6000 job (`Qwen3.5:0.8B`, `gpt-oss:20b`, `Qwen3.5:27b`, `Qwen3.5:35b`, `gemma4:31b`). `gpt-oss:120b` dropped from the default sweep — its 65 GB weights need rtx_pro_6000 (96 GB), and isolating it in a second job no longer pays off vs. submitting it individually when needed. `--gpu-type` propagates through `--all` to the recursive submit.
  - `--no-tools` time scales linearly with model count: 4h base + 4h per extra model.
  - `--mem` lowered from 96G → 80G on rtx_pro_6000 per IT cap (host-RAM peak for 120b weights cache is ~65 GB, comfortably inside 80G).

- **`cluster-experimenting/run_condition_rtx.sbatch`**:
  - Reads `MODELS` (space-separated) preferentially, falls back to `MODEL` for back-compat with direct sbatch invocations.
  - Each model gets its own pull/warmup/VRAM-check before its inner THINK × COND loop. If the VRAM guard trips for one model the job continues with the next (sets `OVERALL_RC=3` at end) rather than aborting the whole pack.
  - **`--cpus-per-task=12` removed** (cluster default `cpus-per-gpu` handles CPU sizing, per IT request).
  - `--mem=48G` unchanged on rtx_6000 (already under the 80G cap).

- **`cluster-experimenting/submit_all.sh`** (cis-ollama waves, fallback path): wave 5 swaps `gpt-oss:120b` → `Qwen3.5:35b` to match the rtx-deploy lineup.

- **Documentation**: `README.md`, `EXPERIMENTS_FLOW.md` §2 / §10 / §11, `cluster-experimenting/README.md` (resource profile table, GPU routing table, quickstart, --no-tools shorthand, troubleshooting) updated to reflect the new model lineup, packing model, and resource caps.

**Schema / compatibility.**
- `summary_*.json` gains `meta.prompt_variants_active: list[int]` and per-row `per_variant: {pv → {...}}`. Existing analysis that ignores unknown fields (notebook `pd.read_json` flows) parses unchanged. Old `summary_*.json` lacking these fields parse identically against the new code.
- `prompt_variant` integer in `single_task_*.json` rows is index-stable: v2 today == v2 in 26042026 sweep == v2 in any prior sweep. Old data remains directly comparable per-variant.
- Per-cell `n` drops by 5/3 (since 2 of 5 variants are no longer sampled). Aggregators that read `n` rather than assuming a fixed denominator are unaffected; any hardcoded denominators in downstream scripts will need updating.

**Runtime cost.** ~40% reduction on the single-task axis. Per (model, with-tools) cell: 400 → 240 evals; per (model, no-tools) cell: 350 → 210 evals. Combined per model: 750 → 450 evals (2.5× → 1.5× the pre-negatives baseline). Cluster wall: a 5-job sweep collapses to 1 packed job; queue priority improves and apptainer/serve cold-starts amortize across all five models in the pack.

**Verification.** 86/86 tests pass (test_scoring 49 + test_check_success 37). Smoke test confirms `ACTIVE_PROMPT_VARIANTS=(0,1,2)`, all 5 templates remain in `PROMPT_TEMPLATES` per task, v2 is the question-form variant, indices are byte-stable. Cluster guide cross-checked (`.local/ISE_CS_DT_Jul-25-ClusterUserGuide.pdf`): 7-day cap on `main`, no `long` partition — 4-day allocation for the 5-model pack is well within bounds.

**Files.** `run_experiment.py`, `cluster-experimenting/{submit_with_rtx.sh, run_condition_rtx.sbatch, submit_all.sh, prompt_variant_stats_20260426.py}`, `checkpoints/cluster-26042026/{prompt_variant_stats.csv, prompt_variant_stats.md}`, `README.md`, `EXPERIMENTS_FLOW.md`, `cluster-experimenting/README.md`, `development/CHANGELOG.md`.

---

## 2026-04-26 — task-targeted negative fixtures + no-tools `validate_*` re-enable

**Motivation.** ISS-001's residual half: every shipped fixture in `domains/` was positive (`gt["domain_valid"] = gt["problem_valid"] = gt["plan_valid"] = True` for every (domain, problem) pair). With-tools `validate_*` therefore measured only tool/argument competence — never validation *capability*, since the truth label never flipped. The same bias is what blocked no-tools `validate_*` on 2026-04-25 (the constant-VALID prior trivially won).

**Changes.**
- **`domains/<dtype>/<domain>/`** (10 domains × 3 new files = 30 files): added `domain_0.pddl`, `p01_0.pddl`, `p01_0.plan`. Each fixture is task-targeted — `domain_0.pddl` joins only `validate_domain`, `p01_0.pddl` only `validate_problem`, `p01_0.plan` only `validate_plan`. Filenames are validity-neutral (`_0` suffix reads as a numeric variant index, not a label, even though the LLM never sees a path). Bug categories distributed across the 10 domains so models can't pattern-match a single shape.
- **`run_experiment.py`**:
  - `load_domains` (lines 480-509): `p*.pddl` glob now excludes `_0`-suffixed files; sibling `domain_0.pddl` / `p01_0.pddl` / `p01_0.plan` are read into `entry["negatives"]`.
  - `generate_ground_truth` (lines 550+): per-domain negative pass calls `validate_pddl_syntax` with the appropriate argument shape (domain / domain+problem / domain+problem+plan) for each kind, asserts the verdict is `False`, and stores `gt[dname]["_negatives"][kind]`. **Fail-fast (`SystemExit`)** if any negative validates True — silently broken negatives can't contaminate the dataset.
  - `run_single_task_experiment` job builder: parallel negative-job loop emits `(model, target_task, dname, domain_pddl, pname, problem_pddl, pv, with_tools, gt_frag, np)` tuples per (domain, kind, prompt-variant). Each negative job's `gt_frag` is constructed inline (no by-`pname` GT lookup), sidestepping any key collision between the `validate_problem` and `validate_plan` negatives. Display `pname` is `domain_0` / `problem_0` / `plan_0`; aggregators detect via `problem_name.endswith("_0")`.
  - **No-tools gate flipped** (`run_experiment.py:1147`): from `task != "solve"` to `task == "simulate"`. Re-enables no-tools `validate_*` (`solve` still in, `simulate` still out — its keyword-check grader at lines 910-912 is non-discriminative regardless of negatives).
- **`tests/test_check_success.py`**: added `test_validate_negatives_no_tools` — four cases mirroring the existing `truth=True` no-tools cases with the truth bit flipped (`validate_domain` INVALID match, `validate_problem` VALID mismatch, `validate_plan` no-VERDICT, `validate_plan` INVALID match). Test suite now 37/37 (was 33).
- **`EXPERIMENTS_FLOW.md`**: §4.2 rewritten to document the new no-tools task set (solve + validate_*; simulate stays excluded). §6 documents the negative-fixture contract, `_0` suffix, fail-fast enforcement. §11 paper-diff row updated.
- **`domains/README.md`**: per-domain table extended to six files; added "Negative fixtures (task-targeted)" section with bug taxonomy table.
- **`cluster-experimenting/submit_with_rtx.sh`**: `--no-tools` shorthand still pins `TASKS=solve` for the fast-baseline contract (~15 min), but the comment is updated to note that the matrix gate now permits `validate_*` and how to widen the shorthand if desired.

**Schema / compatibility.** No `TaskResult` change. Existing `results/.../single_task_*.json` and `summary_*.json` files parse identically against the new code; positive (domain, problem, task) tuples produce identical evaluations (additive on the job set, not modifying). Aggregators that want to split positive vs negative success rates can do so via `problem_name.endswith("_0")` plus the `task` key — already the natural grouping. Per-task aggregators that don't split will simply average over both halves of the balanced ground truth.

**Runtime cost.** Per (model, with-tools) cell: 250 → 400 evals (+60% — three task-targeted negatives × 10 domains × 5 prompt variants). Per (model, no-tools) cell: 50 → 350 evals (the +600% jump is mostly the re-enable of `validate_*`, not the negatives themselves). Combined per model: 300 → 750 evals (**2.5×**). User-acknowledged scope expansion in exchange for closing the validation-capability axis.

**Closes / narrows.**
- **ISS-001** closed entirely (both ground-truth-bias for with-tools `validate_*` and no-tools-discriminability sub-points addressed in the same PR).
- **ISS-017** narrowed further — the no-tools side of the inversion was already sidestepped on 2026-04-25, and now the with-tools `validate_*` baseline-bias is also gone (mixed truth labels eliminate the constant-VALID trivial prior).
- Existing 2026-04-25 entry's "ISS-001 cross-reference" is now satisfied (re-introduction of no-tools `validate_*` happened here, not deferred).

**Verification.** All 30 negatives pass the fail-fast at startup against the live MCP validator (driven by a one-shot script that imports the real `load_domains` + `generate_ground_truth`). Plugin verify.sh (16 tests) and full test suite (49 + 37 = 86 tests) green.

**Files.** `run_experiment.py`, `domains/<dtype>/<domain>/{domain_0.pddl,p01_0.pddl,p01_0.plan}` (×10 domains), `tests/test_check_success.py`, `domains/README.md`, `EXPERIMENTS_FLOW.md`, `cluster-experimenting/submit_with_rtx.sh`, `development/OPEN_ISSUES.md`.

---

## 2026-04-25 — no-tools sweep: honest evaluation + matrix gating

**Motivation.** Two of the three no-tools scorer paths produced inflated success rates that didn't reflect capability:
- `simulate` no-tools was a literal keyword check (`"state"` + `"after"|"step"` in lowercase), so any model that began *"Here is the state transition trace…"* scored success without producing a real trajectory.
- `validate_*` no-tools compared the model's `VERDICT: VALID|INVALID` claim to ground truth, but the bundled fixtures are 100% valid, so a "VERDICT: VALID" prior trivially won. With-tools `validate_*` shares the verdict-match step but additionally requires real tool/argument competence to reach it.

Result-review of cluster-run1 (Qwen3.5:0.8B think=off no-tools) showed 88–100% on 4/5 tasks driven entirely by these biases — a paper-integrity risk if reported as-is.

The no-tools matrix was also wider than needed: chains-on-no-tools collapse to N independent single-task attempts (no artifact propagation between steps), and the think-mode axis doesn't bind on no-tools (no tool args to construct).

**Changes.**
- **`run_experiment.py`**:
  - `run_single_task_experiment` job builder filters no-tools jobs to `task == "solve"` only — the only no-tools task whose output is a PDDL artifact we can re-validate via pyvalidator (mirroring the with-tools scorer).
  - Chain dispatcher (`async_main`, ~line 1726-1745) skips iterations with `with_tools=False` with a one-line note.
  - `async_main` early-gate: `--conditions=no-tools` with `--think` ≠ `off` exits with a warning; `--conditions=both` with `--think` ≠ `off` runs tools side and suppresses no-tools.
- **`cluster-experimenting/run_condition.sbatch`** + **`run_condition_rtx.sbatch`**: the per-condition loop skips `COND=no-tools` iterations when `THINK_MODE != off`.
- **`EXPERIMENTS_FLOW.md`**: §4.2 rewritten to state no-tools is `solve`-only (validate_*, simulate dropped); §5 documents the think=off + single-task gating; §11 adds two methodology-delta rows.
- **`tests/test_check_success.py`**: removed the two simulate-no-tools test cases (`"sim nt state+after"`, `"sim nt empty"`) — those exercised a code path that's now unreachable from the production matrix. Other no-tools tests retained as defensive-code coverage.

**Compatibility.** Existing `results/cluster-202604*/` rows for `(no-tools, simulate)` and `(no-tools, validate_*)` are not invalidated — they remain on disk and analyzable, but should be excluded from any new headline table since the scorers that produced them are now retired (simulate) or known-biased (validate_*). Aggregators in `aggregate.py` / `plot.py` already group by `(model, task, cond)` so missing cells just don't render. Result-schema (§9) unchanged. With-tools sweep behavior is unchanged.

**Closes / narrows.**
- **ISS-002** closed (path b: drop simulate from headline).
- **ISS-017** narrowed — the no-tools side of the inversion is sidestepped; the with-tools `validate_*` baseline-bias remains contingent on **ISS-001** (invalid fixtures).
- Mirrors the `think=off` single-task gating from **ISS-018** onto the no-tools axis.
- **ISS-001** cross-referenced — invalid fixtures remain the prerequisite for any future re-introduction of no-tools `validate_*`.

**Files.** `run_experiment.py`, `cluster-experimenting/run_condition.sbatch`, `cluster-experimenting/run_condition_rtx.sbatch`, `EXPERIMENTS_FLOW.md`, `tests/test_check_success.py`, `development/OPEN_ISSUES.md`.

---

## 2026-04-25 — `run_experiment.py` internal refactor: dedupe + mirror-site alignment

**Motivation.** Review pass over `run_experiment.py` flagged ~30 lines of mechanical duplication and several mirror sites that had quietly diverged in shape coverage. Goal: shrink the surface without touching methodology, and align the duplicates so they can't drift further. Result JSON is byte-identical for current MCP traffic; existing 84-test scoring-audit suite passes unchanged.

**Changes — `run_experiment.py` (one file).**
- New helpers in the existing helper block (no module/file reorg):
  - `_safe_json_loads(raw)` (parse-or-passthrough; replaces 6 ad-hoc `json.loads(raw) if isinstance(raw, str) else raw / except (ValueError, TypeError)` blocks at `_parse_validation_verdict`, `_extract_plan_from_tool_result`, `_tool_error_seen`, the simulate path's oracle-trace + per-result loop, and `evaluate_one`'s tool-error message extraction).
  - `_classify_step_failure(success, done_reason, loop_exhausted, failure_reason) -> (failure_reason, truncated)` — folds the `if loop_exhausted and not success: fr = FR_LOOP_EXHAUSTED` + `truncated = done_reason == "length"` + `_apply_truncation_override(...)` triplet shared by `evaluate_one` and the chain `run_sample`.
  - `_resolve_num_predict(override, task)` — the `override if override is not None else DEFAULT_NUM_PREDICT[task]` resolver, used in both the single-task job builder and the chain step loop.
  - `_build_plan_str(gt)` — the list-or-string-or-empty plan stringifier shared by `generate_ground_truth`, `evaluate_one`, and `run_sample`.
- `RESPONSE_SNAPSHOT_LEN = 500` hoisted to the constants block; replaces magic `[:500]` slices in `evaluate_one` (response field) and `run_sample` (chain `exc_message`).
- **I1 alignment**: `evaluate_one`'s tool-error message extraction now runs through `_safe_json_loads`, matching the string-or-dict shape coverage that `_tool_error_seen` already promised in its docstring. With current MCP traffic (always string) this is a no-op; if `MCPPlanner.call_tool` ever returns parsed dicts, both sides now agree on which records have an extractable error message instead of one flagging and the other silently dropping it.
- **I3**: `extract_plan_lines` uses the regex match offset (`m.start()`) for paren location instead of a manual `stripped.find("(")` — fewer parallel parses, behavior unchanged on representative inputs (all-prefixes test set in dev probe passed).
- **I5**: dropped the dead `chain_lengths=[2,3,4,5]` explicit override at `async_main`'s `run_chain_experiment` call site — the function default already matches; converted the default itself from `list` to `tuple` (mutable-default-arg smell gone).
- **I10**: `chat_without_tools` now appends the assistant turn to `messages` internally, matching `chat_with_tools`'s post-call shape. Removed the manual `messages.append({"role": "assistant", ...})` in `run_sample`'s no-tools branch. `evaluate_one` discards `messages` immediately after, so the extra append is benign there.

**Net effect.** ~30 lines shorter; six mirror-site duplications collapsed; one latent shape-coverage bug (I1) closed defensively; one mutable-default-arg smell (I5) fixed.

**Tests / validation.**
- `tests/verify.sh` (existing scoring-audit suite): 49/49 + 35/35 = 84/84 PASS, unchanged.
- Forward-coverage probe for I1: `_tool_error_seen` and the new `_safe_json_loads`-based extraction agree on both string-shape and dict-shape `tc.result` inputs. Probe lives in dev-only verification — not added as a regression test since real traffic doesn't hit the dict path.
- Helper unit checks (run inline during refactor): `_safe_json_loads` round-trips dict/list/str/None/int; `_classify_step_failure` correctly sequences LOOP_EXHAUSTED before truncation override and respects success-skips-override; `_resolve_num_predict` honours both branches; `_build_plan_str` handles list/str/missing/empty plan; `extract_plan_lines` matches prior output on prefix/bullet/code-fence/no-prefix inputs.
- `python3 -c "import run_experiment"` and `python3 -m compileall` clean.

**Compatibility.**
- No methodology change. `TaskResult` JSON shape, `FR_*` vocabulary, verbose-bridge contract, `check_success` 5-path scoring rules, chain all-or-nothing semantics, RNG pre-sampling order — all preserved.
- `summary.json` shape unchanged; result-file naming unchanged.
- Existing `results/` are still directly comparable to fresh runs.
- No `ISS-###` closed; one new `ISS-###` queued (deferred from this pass): `evaluate_one`'s tool-error message extraction walks all tool calls without filtering by the tool name that triggered `FR_TOOL_ERROR`, so with `--tool-filter=all` and a multi-tool `solve` task an unrelated planner error could be surfaced as the wrong tool's message. Edge-case; not currently observed in practice.

---

## 2026-04-25 — Cluster-ops additions surfaced from BGU HPC user guide

**Motivation.** Re-read the 45-page BGU ISE-CS-DT cluster guide (`.local/ISE_CS_DT_Jul-25-ClusterUserGuide.pdf`) against the existing `cluster-ops` skill. Three documented SLURM features were not surfaced anywhere in the skill, and each mapped to a recurring friction:
- **Pending REASON** (PDF p43–44): `status.sh` only parsed RUNNING jobs, so a stalled `afterok` wave or `Resources` queue showed up as an empty status table — required hand-running `squeue --me -t PD` to diagnose.
- **`sres` + per-partition `sinfo`** (PDF p10): pre-submit GPU-pool capacity was an ad-hoc inline check in `SKILL.md`, copy-pasted before each `submit_with_rtx.sh` call.
- **`sacct --format=...,MaxRSS,AllocTRES,...`** (PDF p10) + the "use minimum possible RAM" rule (PDF p9): no consolidated post-mortem of completed jobs; right-sizing `--mem` required per-job manual `sacct` invocations.

**Changes — `.claude/skills/cluster-ops/`.**
- `scripts/status.sh`: pulls `squeue %R` reason column, splits into Pending and Running tables. Pending table renders first so wave-blocking REASONs (e.g. `DependencyNeverSatisfied`, `Resources`) surface without a separate query.
- `scripts/preflight.sh`: appends a "GPU pool capacity" section (`sinfo -p rtx6000` and `-p rtx_pro_6000`, free-or-mixed node count vs total) and an `sres` snapshot, ahead of the existing cis-ollama reachability check. Now covers both submit paths in one preflight.
- `scripts/postmortem.sh` (new): single-SSH-call `sacct` for the user's `pddl_*` jobs in a window (default last 7 days via `--starttime=now-7days`; `--since YYYY-MM-DD` or `--jobs id,id` to scope). Merges parent + `.batch` step rows so each row carries State + Elapsed + MaxRSS + AllocTRES + ExitCode + DerivedExitcode + Comment. Concludes with a per-job-name memory headroom block (`pddl_rtx_gpt-oss_120b: peak 70.1GB of 96.0GB → safe --mem=87G`); per-name aggregation matters because the sweep is heterogeneous (Qwen3.5:0.8B uses ~2GB, gpt-oss:120b uses 70GB), so a single global recommendation would either OOM the big model or over-allocate every small one.
- `SKILL.md`: postmortem section after diag; pending-REASON cheat sheet (6 codes mapped to actions); cancel recipe gains a `squeue --me | awk '$2 ~ /^pddl_/' | xargs scancel` pipe that filters by job-name prefix without nuking unrelated jobs (an earlier draft used `scancel -u $USER --name=pddl_*` but verification on SLURM 25.11.4 showed `--name` is exact-match — comma-separated literal names, not a glob — so `pddl_*` silently matches zero jobs; SKILL.md documents the trap inline); the postmortem step is folded into the standard "sync and plot" recipe; the redundant inline `rtx_pro_6000` availability check is removed in favor of preflight's GPU-pool section.

**Implementation notes.**
- `bash -s --` end-of-options marker is required when passing `--starttime=...` / `--user=...` as positional args via SSH (otherwise remote bash treats them as its own options).
- `--user=` long-form is required (instead of `-u`) because ssh re-splits the joined-args string on whitespace, which would split `-u omereliy` into two tokens and trip the next sacct flag into being consumed as the username.
- `python3 -c "$PY"` (with the python source captured into a variable via `$(cat <<'PY' ... PY)`) is required for the postmortem pipe — the `python3 - <<'PY' ... PY` form makes the heredoc become python's stdin, hijacking the pipe and starving sys.stdin of the sacct rows.

**Tests / validation.**
- `status.sh` against the live queue: 2 RUNNING jobs (gemma4:31b, Qwen3.5:27b) rendered correctly; no pending jobs at test time, so the Pending section was correctly omitted.
- `postmortem.sh --since 2026-04-23`: 17 completed/running `pddl_*` jobs rendered with MaxRSS + alloc; per-job-name peaks revealed wide over-allocation (`pddl_rtx_Qwen3_5_27b` used 26.7GB of 96GB allocated — 72% slack; recommended `--mem=33G`). gpt-oss:120b peak was 70.1GB on rtx_pro_6000 (COMPLETED in 7h57m), recommendation `--mem=87G`.
- `bash -n` syntax-check on all three scripts.

**Compatibility.**
- All three scripts remain read-only over experiment state. The skill's existing "no mutations to `run_experiment.py` / `run_condition.sbatch` / `submit_all.sh`" contract is preserved.
- No `summary.json` schema change. No methodology change. No re-run of any prior result needed.
- No `ISS-###` closed; no new `ISS-###` opened — these are operational additions, not methodology fixes.

**PR #6 review fixes (2026-04-25 same day).**
- `.claude/agents/cluster-ops.md`: added `skills: [cluster-ops]` frontmatter so the SKILL.md auto-loads into the subagent's system prompt at startup ([documented field](https://code.claude.com/docs/en/subagents.md)). Removed the manual "Read SKILL.md at start of turn" instruction — saved one tool turn against the `maxTurns: 15` budget on every invocation. Added a one-line `$ARGUMENTS`-handling rule so `/cluster-ops postmortem --since YYYY-MM-DD` etc. land on the right recipe.
- `.claude/skills/cluster-ops/SKILL.md`: trimmed `description:` from ~720 chars to ~330 chars (capability summary only); moved the trigger-keyword list and "read this skill before…" imperative into the body's "Why this skill exists" section. Added `> User asked for: $ARGUMENTS — pick the matching recipe below.` near the top so slash-invocation arguments are no longer silently dropped (`argument-hint: [status | preflight | …]` was previously decorative).

**Files.**
- `.claude/skills/cluster-ops/scripts/status.sh` (PENDING section + REASON column)
- `.claude/skills/cluster-ops/scripts/preflight.sh` (GPU pool + `sres`)
- `.claude/skills/cluster-ops/scripts/postmortem.sh` (new, ~115 LOC)
- `.claude/skills/cluster-ops/SKILL.md` (description, recipes, REASON cheat sheet, cancel recipe)

**PR #6 review fix — `merge_series` no-tools pooling (2026-04-25 same day).** `plot.py --merge` previously grouped by `(model, think)` only, silently pooling the `no-tools` baseline into the merged tools series and labelling everything `cond="tools_merged"` — turning the merged rate into "all conditions averaged" rather than "tools-on, averaged over `tool_filter × prompt_style`". Fix: `merge_series` now restricts pooling to `cond != "no-tools"` and passes no-tools rows through unchanged so they remain as the baseline; the post-merge sort places the no-tools row above the merged tools row per `(model, think)`, and `_label` carries an explicit `· no-tools` / `· tools` suffix so the two series are distinct in the legend. fig3 / fig6 already filter via `s["cond"] != "no-tools"`, so they correctly drop the passthrough baseline. SKILL.md `--merge` description updated to match. No `summary.json` schema change; existing unmerged figures are unaffected (the merge path is gated entirely behind `if args.merge:`).

**Tracked separately:** `ISS-018` (open) — restrict `think=off` to single-task evaluation, mirroring the existing `no-tools → single-task-only` routing (commit 9574fd3).

---

## 2026-04-23 — Parallelize chain-sample dispatch (match single-task concurrency)

**Motivation.** Audit of the live cluster-20260423 sweep surfaced that `run_chain_experiment` iterated samples in a plain `for i in range(samples):` loop while `run_single_task_experiment` already used `Semaphore(concurrency) + create_task + as_completed`. With `--concurrency 2` per job and 2 parallel jobs/wave against cis-ollama's measured `OLLAMA_NUM_PARALLEL=4`, the server sat at ~50% utilization during the chain phase (2 in-flight vs 4-slot capacity). Measured on `slurm_Qwen3_5_0_8B_on_tools_per-task_minimal_17123867` (job 17123867): condition wall-time 4h 38m; single-task CPU sum 3.31h → single-task wall ≈ 1.65h @ c=2; inferred chain wall ≈ 2.98h, which matches the prediction for serial chain (≈3.3h for 400 samples × ~1.5 effective steps × ~20s/step) within 10%. (commit `ee5bc8d` on branch `async-fix`)

**Changes — `run_experiment.py`.**
- `run_chain_experiment` takes a new `concurrency: int = DEFAULT_CONCURRENCY` parameter. The per-sample body is lifted into an inner `run_sample(...)` coroutine; samples are dispatched via `asyncio.Semaphore(concurrency) + asyncio.create_task + asyncio.as_completed`, mirroring `run_single_task_experiment:1128–1163` exactly. Per-step sequencing inside a sample is unchanged — each step's messages still depend on the previous step's output, which is correctness-critical.
- All `random.choice` draws (domain / problem / `chain_tasks` / `step_templates`) are pre-computed **before** fan-out so RNG order stays deterministic w.r.t. serial execution. Without pre-sampling, coroutine interleaving would non-deterministically reorder RNG calls. Minor drift vs. the previous code: `step_templates` is now drawn for every position in `chain_tasks` including positions later skipped by the no-plan-oracle guard — the old code only drew a template for non-skipped steps. Unseeded runs were already non-deterministic, so this does not change reproducibility behaviour in practice.
- `samples_detail` is sorted by `idx` after collection so the JSON schema and sample ordering match the pre-fix output; downstream `aggregate.py` / `plot.py` / notebooks consume `samples_detail` by aggregate, not by index, so both orderings are compatible.
- `main` caller at `:1709` now forwards `concurrency=args.concurrency` into the chain call.
- `KeyboardInterrupt`/`asyncio.CancelledError` handling mirrors the single-task path: pending tasks are cancelled and awaited via `asyncio.gather(*aws, return_exceptions=True)` before reraise.

**Reproducibility.**
- `chain_*.json` schema is unchanged — same `{idx, domain, problem, chain_tasks, step_records, final_success, exception}` per sample, same `successes / samples / success_rate` aggregate fields.
- Completed Qwen3.5:0.8B wave (`results/cluster-20260423/slurm_Qwen3_5_0_8B_*`) and in-flight gpt-oss:20b wave (job 17130166/7) remain directly comparable post-fix: success rates and failure-reason counts are expected to overlap within sampling noise (temperature=0.0 but unseeded RNG).
- Chain-internal step sequencing and the `_apply_truncation_override` parity with single-task (landed 2026-04-21) are unchanged.

**Expected wall-time impact.** Chain phase ~50% faster per job. Per-condition savings: ~1.5h for Qwen3.5:0.8B, ~2h for gpt-oss:20b, likely ~3–4h for 120b. Sweep-wide: a full wall-day recovered without methodology change. Pipeline safety (`afterok` wave serialization, `CONCURRENCY=2` default) is untouched — the fix only raises utilization inside a condition, not across waves.

**Files.**
- `run_experiment.py` (`run_chain_experiment` signature + body; caller at `main:1709`).

---

## 2026-04-21 — Harness observability fixes from cluster-run1 analysis

**Motivation.** Results review of `results/full-cluster-run1/` (11/25 jobs — analysis kept locally under `.local/reports/`) surfaced four harness-side technical issues. This change-set addresses them without modifying the measurement pipeline — no prompt, skill-description, temperature, or scoring-semantics change.

**Changes — `run_experiment.py`.**
- Added `FR_OLLAMA_PARSE_ERROR` bucket for upstream Ollama tool-call parser failures (mostly gpt-oss at temp=0). Classification only; no retry (retries at `TEMPERATURE=0.0` mostly reproduce the same output, so the extra API call wasn't justified).
- Added `FR_LOOP_EXHAUSTED` bucket. `chat_with_tools` now returns a 4-tuple `(text, tool_calls_log, done_reason, loop_exhausted)` — when the `MAX_TOOL_LOOPS=10` cap fires, `text=""` instead of the previous behaviour (which returned the last tool-output as assistant text, corrupting `response[:500]` on 177 records). `evaluate_one` relabels the failure as `FR_LOOP_EXHAUSTED` when `loop_exhausted and not success`.
- `TaskResult.error` is now populated on `FR_TOOL_ERROR` from the first `tool_calls[i].result` carrying `{"error": true, "message": ...}` — previously those 202 records had `error=""` and required a nested walk to surface the tool's own error text.
- `run_chain_experiment` now emits per-sample `samples_detail: list[dict]` alongside the existing aggregate fields. Each sample carries `{idx, domain, problem, chain_tasks, step_records, final_success, exception}`; `step_records` is per-step `{step_index, task, success, failure_reason, tool_calls_count, truncated, loop_exhausted}`. Chain steps now apply the same `_apply_truncation_override` as `evaluate_one`, so `step_records[*].failure_reason` is directly comparable to single-task `failure_reason` values (aggregate `success_rate` unaffected — only the label on already-failing steps changes). Typed exception capture (`exc_type`, `exc_message`, `is_ollama_parse_error`) replaces the previous bare `except Exception: break`. Skipped `validate_plan`/`simulate` steps (no-plan-oracle guard) are absent from `step_records`, making `len(step_records)` the effective chain length per ISS-011.
- Lifted the Ollama tool-call parser signature (`"error parsing tool call"`) into a single `OLLAMA_TOOL_PARSE_SIGNATURE` module constant shared by `evaluate_one` and `run_chain_experiment` — one place to update if the upstream phrasing changes.

**Closes / narrows.**
- ISS-005 Batch-2 portion (`FR_TOOL_LOOP_EXCEEDED`) — landed as `FR_LOOP_EXHAUSTED`.
- ISS-011 (chain per-sample denominator / effective chain length) — now computable from `step_records`; no further harness change required.

**Reproducibility.**
- Existing `results/**/single_task_*.json` and `chain_*.json` remain valid. The new `FR_*` constants and `samples_detail` field are additive.
- No success/fail verdict changes. Fix #4 only relabels failures (177 records move from ambiguous buckets into `FR_LOOP_EXHAUSTED`). Fixes #1, #2, #3 are pure taxonomy / data-capture improvements.
- `tests/verify.sh` — 84 tests pass unchanged. No scoring semantics altered.

**Companion artefacts (local-only, under `.local/`).** The harness-side analysis report and the sibling-repo issues report (for `../pddl-copilot/`'s pddl-validator plugin + pyvalidator) are kept in the contributor's `.local/reports/` directory, not committed.

**Files.**
- `run_experiment.py` (FR_* additions; `chat_with_tools` signature; `evaluate_one` classification + error-copy + loop-exhausted override; `run_chain_experiment` per-sample capture).
- `development/OPEN_ISSUES.md` (ISS-005 Batch-2 marked resolved; ISS-011 cross-referenced).

---

## 2026-04-21 — Add `cluster-ops` skill for BGU SLURM workflow

**Motivation.** Session-over-session repetition of SSH queue queries, `.out` log parsing, rsync, summary aggregation, and plot generation. Every interaction re-derived the same grep patterns and naming conventions. Consolidated into a narrative Claude Code skill + 5 helper scripts so future agents start from a known base. No methodology change.

**Code change — `.claude/skills/cluster-ops/`**
- `SKILL.md`: trigger phrases + recipes for status / submit / cancel / sync / aggregate / plot / diag. Matches the `disable-model-invocation: true` style of the existing two skills. Explicitly gates destructive ops (`scancel -u`, remote `rm`) behind user confirmation.
- `scripts/status.sh`: one SSH call, server-side Python parse of `.out` files. Handles both legacy (`pddl_<model>_<cond>-<jobid>.out`) and current (`pddl_<model>_<think>-<jobid>.out`) layouts. Reports condition index (N/5), `ST N/250`, `chain k/400`, and 1200s-timeout rate per job.
- `scripts/sync.sh`: `rsync -av --update` into `results/cluster-<YYYYMMDD>/` by default. Never deletes anything.
- `scripts/aggregate.py`: walks a results root, emits Markdown tables for single-task success, chain success, failure-reason totals. Handles both dir naming schemes; legacy dirs render as `think=default` with a header warning.
- `scripts/plot.py`: generalization of `results/full-cluster-run1/make_plots.py`. Auto-discovers `(model, think, cond)` tuples from dir names, builds SERIES dynamically, colors by model family with hatches for tool condition.
- `scripts/diag.sh`: `curl` `/api/tags` + `/api/ps` on cis-ollama, optional 10-token ping to a named model.
- `scripts/preflight.sh`: pre-submit cluster refresh — pulls both repos and runs `pip install --upgrade -r requirements.txt` inside `pddl-solver/.venv` and `pddl-validator/.venv`, because `setup_env.sh` deliberately skips existing venvs and therefore leaves them stale after a dependency bump (we hit exactly this today with `pddl-pyvalidator>=0.1.4`). Ends with a cis-ollama reachability check.

**Tests / validation**
- `diag.sh`: reached cis-ollama, listed 19 hosted models and 2 loaded (Qwen3.5:27b + gemma4:31b).
- `aggregate.py` over `results/full-cluster-run1/`: produced 15-row matrix identical to the manual table.
- `plot.py` over `results/full-cluster-run1/`: wrote 3 PNGs at `plots/fig[1-3]_*.png`, backward-compatible with the hand-built plots from earlier today.
- `status.sh`: against the 6 legacy jobs still running from the pre-overhaul sweep (`17116518-22`, `17116533`), matched the manual Markdown status reports within a few-instance drift expected from real-time progress.

**Compatibility**
- Read-only over experiment state. Does not touch `run_experiment.py`, `run_condition.sbatch`, `submit_all.sh`, or any scorer path.
- Both legacy `slurm_<model>_<cond>_<jid>` and current `slurm_<model>_<think>_<cond>_<jid>` result-dir layouts are parsed; mixing them in one root produces a warning header in the aggregate output.
- No `ISS-###` closed; `SKILL.md` references `ISS-015` (gateway 504) and `ISS-016` (FD stdout) in its diagnostic recipes.

---

## 2026-04-21 — Cluster sweep: serialize by model, align chains to paper, add think-mode axis

**Motivation.** The 2026-04-20 resubmit of the full cluster sweep (25 jobs: 5 models × 5 conditions) stalled at 10+h/job despite a 200GB-VRAM server. Diagnostic (`curl cis-ollama/api/ps`) showed only 2 of 5 requested models loaded at a time. Post-hoc probe on 2026-04-21 (see "Server-probe evidence" below) confirmed `OLLAMA_MAX_LOADED_MODELS ≥ 3` on the same server, so the 2-loaded ceiling during the stalled sweep was VRAM pressure under mixed-user contention, not a hard server cap. Either way, 19 concurrent jobs round-robin across 4 model families caused continuous weight eviction. Signature: `gemma4:31b` running at 560s/sample while `gpt-oss:120b` ran at 291s/sample (smaller model slower than larger = textbook eviction churn). Additionally, `--chain-samples 20` was 4.4× below the paper's 100/100/100/50 methodology, and the `--think default` axis left thinking silently ON for Qwen but OFF for gpt-oss/gemma (mixed, unreported).

**Changes.**
- `run_experiment.py`: added `KEEP_ALIVE = "1h"` constant and pinned it in `_build_chat_kwargs`, so every `client.chat()` carries the hint. Blocks server-side weight eviction during within-job idle gaps. (commit `ca01252`)
- `cluster-experimenting/run_condition.sbatch`: per-job axis changed from `(model, condition)` to `(model, think_mode)`; the 5 conditions now loop sequentially **in-process** inside a single SLURM job. Time limit raised from 1 to 3 days. Added `THINK_MODE=on|off|default` and `CONDITIONS=<space-separated>` env-var inputs. Each invocation of `run_experiment.py` runs at `--chain-samples 100 --concurrency 2`. (commit `1de6fc4`)
- `cluster-experimenting/submit_all.sh`: replaced the 25-job fan-out with 9 jobs across 5 waves chained by `--dependency=afterok`:
  1. `Qwen3.5:0.8B` × {on, off}
  2. `gpt-oss:20b` × {on, off}
  3. `Qwen3.5:27b` × {on, off}
  4. `gemma4:31b` × {default} — no thinking mode on gemma
  5. `gpt-oss:120b` × {on, off}

  Within each wave the 2 think-mode jobs run in parallel (same loaded weights on the server, no eviction). Across waves, `afterok` halts the pipeline on any failure — user resubmits after diagnosing. `--dry-run` previews the sbatch commands; `--from-wave N` resumes from wave N with no dependency on earlier waves. (commit `1de6fc4`)

**Why `afterok` not `afterany`.** Per-project preference: correctness over ship-through. A failed wave usually means broken infra (VPN, server restart, model removed from cis-ollama) — running dependents against broken infra just burns compute. `afterok` auto-halts at a known point; dependents sit in `PENDING (DependencyNeverSatisfied)` until `scancel -t PENDING -u $USER`.

**Server-probe evidence (2026-04-21).** Measured `OLLAMA_NUM_PARALLEL=4` via concurrent-request timing against `Qwen3.5:0.8B` on `cis-ollama.auth.ad.bgu.ac.il` (Ollama 0.20.7): N=1→0.44s, N=2→0.51s (1.16×), N=4→0.64s (1.45×), N=8→0.98s (2.23×). N=4 ≈ 1× and N=8 ≈ 2× → server batches up to 4 in parallel, then queues. Implication: at `CONCURRENCY=2` per job × 2 parallel jobs per wave = 4 concurrent requests, the wave exactly saturates the server without queueing and without starving other users. Also observed: 3 models resident in VRAM (gemma4:31b + Qwen3.5:27b + Qwen3.5:0.8B = ~58GB) after loading a third one did not evict the existing two — confirms `MAX_LOADED_MODELS ≥ 3`, so 2026-04-20's 2-loaded ceiling was VRAM-pressure, not a hard cap.

**Methodology impact.**
- **Chain samples**: moved from 20 (flat, 4.4× below paper) to 100 (flat, 2× oversamples length=5 vs paper's 50). Wilson CIs now comparable to paper §5 tables.
- **Think modes**: explicit `on` and `off` runs per model (except gemma4), matching the paper's "report better of thinking/no-thinking" protocol. Previous default-only runs are NOT comparable across models.
- **Output directories**: new pattern `results/slurm_<model>_<think>_<cond>_<jobid>/` adds a `<think>` segment. Old results remain valid for their per-condition cell but can't aggregate with new runs without a dimension-reducing groupby.

**Compatibility.**
- Old result JSONs under `results/slurm_<model>_<cond>_<jobid>/` (no `<think>` segment) stay valid in isolation but are not apples-to-apples with new runs (different chain_samples, different keep_alive, unknown think-mode for some models).
- `run_background.sh` (laptop path) untouched.

**Files.**
- `run_experiment.py` (`_build_chat_kwargs`, KEEP_ALIVE constant at ~line 91)
- `cluster-experimenting/run_condition.sbatch` (full body rewrite)
- `cluster-experimenting/submit_all.sh` (full rewrite: 5-wave dependency chain)
- `cluster-experimenting/README.md` (quickstart, submitting, variants, monitoring, cancelling sections updated for new axis)

---

## 2026-04-20 — ISS-014 resolved: `pyval` numeric goal-check fix verified

**Resolution.** Re-ran `mcp__plugin_pddl-validator_pddl-validator__validate_pddl_syntax` against every `domains/**/p01.plan`. All 10 fixtures now report `valid=true`, including `numeric/counters/p01` and `numeric/farmland/p01` which previously failed on numeric `<=` / `>=` goal checks. The arithmetic results match the ones computed by hand in the original ISS-014 evidence block (counters final `c0=12,c1=49,c2=92,c3=93,c4=94`; farmland weighted sum `31.0 ≥ 30.8`).

**Why it fixed itself.** The bug sat in the upstream `pyval.PDDLValidator` goal checker, consumed by `plugins/pddl-validator/server/validator_server.py`. A subsequent `pyval` update (pulled in by a later plugin-venv rebuild) fixed the numeric-comparison path. No experiment-repo change required.

**Implications for scoring**
- Oracle ground truth now returns `gt["plan_valid"]=True` for counters/p01 and farmland/p01, so the asymmetric-scoring failure mode documented in ISS-014 (agents "rewarded for agreeing with the bug") no longer applies.
- `validate_plan`, `solve` (via `_validate_model_plan`), and `simulate` all benefit immediately — no code change needed here.
- Any pre-fix run under `results/` encodes the wrong GT for those two domains; do not compare numeric-domain plan-validity numbers across the fix boundary without the footnote.

**Files.** No edits. Closes ISS-014 (entry removed from `development/OPEN_ISSUES.md`); `domains/README.md` per-domain status table updated to drop the bug notes.

---

## 2026-04-20 — Paper-aligned domain set (10 domains)

**Motivation.** The harness shipped with 3 ad-hoc domains (`blocksworld`, `depots`, `counters`) — 1–5 problems each — while the paper (arXiv:2509.12987) used 10 domains with one problem each. Result tables from this repo therefore could not be aligned to the paper's §5 tables without manual coverage accounting. The paper dataset was present on disk (`.local/pddl_mcp_dataset/`, Aug 2025 snapshot) but detached from the runtime. This change makes `domains/` the paper dataset verbatim so the MCP oracle in `generate_ground_truth()` produces paper-aligned ground truth on every run — no code change needed.

**Data-only change — `domains/`**
- Replaced `classical/{blocksworld,depots}` and `numeric/counters` content with paper versions (one problem each). Deleted leftover `p02.pddl`–`p05.pddl` from those three domains.
- Added seven new domains: `classical/{barman,rovers,satellite}` and `numeric/{depot,farmland,pogo_stick,sailing}`. Each has `domain.pddl`, `p01.pddl` (copied from paper `problem.pddl`), and `p01.plan` (copied from paper `plan.solution` — reference artifact, not read at runtime).
- Skipped paper's `plan.trajectory` (Lisp-text, incompatible with the MCP-JSON shape `get_state_transition` returns for simulate's byte-equal check at `run_experiment.py:856`), `temp_plan.*`, `validation_log.txt`, and `*.txt` domain-description files.
- New `domains/README.md` documents provenance, naming convention, and the expected-validity contract.

**No code changes.** `run_experiment.py`, cluster scripts, and MCP contract are untouched. `load_domains()` already walks `{classical,numeric}/<name>/p*.pddl`, so the new domain set loads automatically.

**Compatibility**
- Existing result JSONs under `results/` encode the old 3-domain coverage and are not directly aggregate-comparable with post-change runs. Each old run remains valid for its 3-domain slice.
- Default invocation patterns for `cluster-experimenting/`, `run_background.sh`, and `remote_background.sh` continue to work unchanged — they just now iterate over 10 domains × 1 problem instead of 3 domains × 1–5 problems.
- Unblocks `ISS-013` (paper-diff audit can now proceed against matching domain coverage). `ISS-001` (no-tools validate_* baseline needs broken fixtures) remains open.

---

## 2026-04-20 — Batch 1: ISS-004 no-tools de-duplication + summary meta

**Motivation.** Per the approved plan in `OPEN_ISSUES.md::Planned batches`, land the zero-risk orchestration win first. The old sweep ran the no-tools condition once per `(tool_filter, prompt_style)` combo — four identical passes per model, since neither knob affects the no-tools branch (`WITHOUT_TOOLS_SYSTEM` is a single string; `TASK_TOOLS` only gates `chat_with_tools`). Closes ISS-004 and the untracked "no host stamp in results" micro-fix.

**Code change — `run_experiment.py`**
- **New `--conditions` flag** (`tools`/`no-tools`/`both`, default `both`). Plumbed into `run_single_task_experiment` (as `conditions: str`) and the chain loop in `async_main`. Expansion helper `_expand_conditions` preserves the legacy `(True, False)` iteration order for `both` so pre-ISS-004 reproductions stay byte-comparable.
- **`save_results` accepts `meta: dict | None`.** `async_main` now passes host, is_remote, conditions, tool_filter/prompt_style (only when with-tools ran), models, tasks, num_variants/ctx/predict, temperature, think. Written under `summary["meta"]`. Rationale: remote-vs-local and split-condition runs were indistinguishable at the summary-JSON level; analysis notebooks had to infer from directory naming.

**Orchestration change — `run_background.sh`**
- One `--conditions no-tools` run up front (output dir `{prefix}_no-tools/`), then the `(FILTER, PSTYLE)` loop runs `--conditions tools` (output dir `{prefix}_tools_{FILTER}_{PSTYLE}/`). Net effect: the full local sweep drops from 4 no-tools passes per model to 1 — ~25% wall-clock savings on the two-model sweep, larger on the BGU four-model sweep.

**Tests — `tests/test_scoring.py`**
- New `test_expand_conditions` (3 assertions) pinning the iteration order for each choice. Full suite now 49 + 35 = 84 green.

**Validation**
- `bash tests/verify.sh` → 84/84 green.
- `python3 run_experiment.py --help` renders `--conditions` in the expected order.
- `save_results` round-trip test confirms `summary["meta"]` present with the expected keys when `meta=` is passed; omitted when `meta=None` (backward-compat).
- Live Ollama smoke test skipped (no local server); MCP handshake and plugin contract already verified in the previous compatibility review.

**Compatibility**
- Default `--conditions=both` preserves paper-reproduction behaviour byte-for-byte — iteration order, prompts, MCP calls unchanged.
- `save_results(meta=None)` matches the pre-batch schema (no `meta` key in summary). Existing `results/*/summary_*.json` files remain valid input to analysis notebooks.
- Result-dir naming under `run_background.sh` changed: `{prefix}_{FILTER}_{PSTYLE}/` → `{prefix}_tools_{FILTER}_{PSTYLE}/` + new `{prefix}_no-tools/`. Gitignored, but any external tooling that globs on the old pattern needs a one-line update.

---

## 2026-04-20 — Scoring audit: tests + B1/B2/B3 fixes

**Motivation.** PR #1 (`adapt-to-mcp`) rewrote the scoring path (`check_success`, two-metric with-tools grading, `FR_*` vocabulary, Wilson CIs) but added zero tests. Review of the branch surfaced three latent bugs that would silently distort metrics. User asked the mechanism to be "verified and tested to behave properly" before trusting new numbers.

**Code change — `run_experiment.py`**
- **B1 (simulate success gate).** `check_success` simulate branch previously scored success on `any(r for r in results) and not _tool_error_seen(...)`. A `{"valid": false, "steps": [...], "trajectory": [partial]}` response satisfied that — but `valid` is a PDDL-syntactic signal, not simulation correctness. New gate: parse each call's `trajectory` and deep-equal against oracle `gt["trace"].trajectory`. Match → `FR_OK`; mismatch → new `FR_RESULT_MISMATCH`; error-shape → `FR_TOOL_ERROR`.
- **B2 (`extract_plan_lines` regex).** `_ACTION_LINE_RE` only matched bare or numbered (`1.` / `1:`) action lines. Extended to accept bulleted lines (`- (action ...)` / `* (action ...)`), since small LLMs often wrap plans in markdown bullets.
- **B3 (`_validate_model_plan` exception path).** Signature is now `bool | None`; MCP transport failure returns `None`, which callers (`check_success` solve branches) map to `FR_TOOL_ERROR` instead of `FR_PLAN_INVALID`. Stops misattributing validator-unreachable runs as invalid-plan runs.
- **New constant.** `FR_RESULT_MISMATCH = "result_mismatch"` added to the `FR_*` block.
- **Truncation override refactor.** Extracted `_apply_truncation_override(success, truncated, failure_reason)` from the inline block in `evaluate_one` so the override logic is testable. No behaviour change.

**Tests — `tests/`** (new directory)
- `tests/verify.sh` — shell entry point matching `../pddl-copilot/plugins/*/tests/verify.sh` pattern. No pytest dependency.
- `tests/_helpers.py` — `FakeMCP` stub, fixture loader, minimal `TestResults` harness.
- `tests/test_scoring.py` — unit tests for `wilson_ci`, `_parse_validation_verdict`, `_tool_error_seen`, `_used_tool`, `_get_tool_results`, `_extract_plan_from_tool_result`, `extract_plan_lines`, `extract_verdict` (46 assertions).
- `tests/test_check_success.py` — table-driven tests for `check_success` across 5 tasks × 2 conditions × tool-call shapes, plus the truncation override helper (35 assertions).
- `tests/fixtures/{blocksworld_p01,counters_p01}.json` — ground-truth + tool outputs generated by real MCP calls through Claude Code's installed plugin; projected to the verbose=False bridge shape.

**Validation**
- `bash tests/verify.sh` → 46/46 + 35/35 green on current code.
- Test cases encode each of B1/B2/B3 as named cases, so any future regression is named in the failure.

**Compatibility**
- `_parse_validation_verdict`, `_tool_error_seen`, and verdict-extraction behaviours all pinned by tests — no change.
- `FR_RESULT_MISMATCH` is additive; existing failure-reasons dicts remain open-ended. `summarize_single_task` and `print_fail_reasons_table` iterate generically, no changes needed.
- Historical `results/*` simulate runs scored as `FR_OK` under the old lenient gate may no longer match when re-scored against post-B1 code. Prior numbers aren't byte-comparable, but the `results/*` directory is gitignored — only future runs see the stricter gate.
- `_validate_model_plan` signature change (`bool` → `bool | None`) has two internal callers (both in `check_success`), both updated in this commit. No external callers.

---

## 2026-04-20 — Validator response projection via bridge-pinned `verbose` flag

**Motivation.** Truncation failures on `simulate` and `validate_*` with-tools runs (e.g. 55/55 truncated on qwen3:4b `validate_plan`, qwen0.6b simulate 29/55) were driven in part by the validator plugin returning multi-KB `details` JSON and verbose `report` text that neither the LLM nor the scorer consumed. User direction: resolve by structured projection, not by capping/truncating kept fields.

**Plugin change — `../pddl-copilot/plugins/pddl-validator/server/validator_server.py`**
- `validate_pddl_syntax` gained a `verbose: bool = True` parameter.
  - `verbose=True` (default for standalone MCP callers): `{valid, status, report, details}`.
  - `verbose=False`: `{valid, status, report}`.
- `get_state_transition` gained a `verbose: bool = True` parameter.
  - `verbose=True` (default): `{valid, report, steps, trajectory, details}`.
  - `verbose=False`: `{valid, steps, trajectory}` with full, uncapped `trajectory[*].boolean_fluents` / `numeric_fluents` per step.

**Bridge change — `run_experiment.py::MCPPlanner`**
- New class constant `_PINNED_VERBOSE_FALSE = {"validate_pddl_syntax", "get_state_transition"}`.
- `connect()` strips the `verbose` property from each pinned tool's `inputSchema` before adding it to the tools payload that goes to Ollama.
- `call_tool()` injects `verbose=False` on every pinned-tool invocation.
- Net effect: the experiment agent never sees or controls `verbose`; validator responses arriving at the LLM are always projected.

**Tests — `../pddl-copilot/plugins/pddl-validator/tests/verify.sh`**
- Added four assertions covering both default-verbose and `verbose=False` return shapes for both tools. 15/15 tests pass.

**Docs — `EXPERIMENTS_FLOW.md` §8 and §11**
- §8 now documents the dual-mode validator contract and explicitly notes the bridge's `verbose=False` injection.
- §11 paper-diff table records the methodology delta.

**Compatibility**
- `_parse_validation_verdict` (`run_experiment.py:433-449`) reads only `valid`/`error` — projection is safe.
- `simulate` scorer (`run_experiment.py:769-777`) only checks "non-empty + no error" — projection is safe.
- Prior `results/` `tool_calls[*].result` strings are NOT byte-comparable with post-change runs. Scoring outcomes are.

---

## 2026-04-20 — Cap alignment hygiene (no behavior change)

Existing scattered caps in `../pddl-copilot` normalized to a `DEFAULT_*` module-constant + `PDDL_*` env-override convention. Values unchanged.

| File | Constant | Env var | Default |
|---|---|---|---|
| `plugins/pddl-parser/server/backends.py` | `MAX_GROUNDING_ATTEMPTS` | `PDDL_MAX_GROUNDING_ATTEMPTS` | 10000 |
| `plugins/pddl-parser/server/parser_server.py` | `DEFAULT_MAX_APPLICABLE_ACTIONS` | `PDDL_MAX_APPLICABLE_ACTIONS` | 50 |
| `plugins/pddl-solver/server/solver_server.py` | `MAX_FAILURE_LOG_CHARS` | `PDDL_MAX_LOG_CHARS` | 3000 |
| `plugins/pddl-solver/server/solver_server.py` | `DEFAULT_TIMEOUT` (already aligned) | `PDDL_TIMEOUT` | 120 |

All three plugin `verify.sh` suites still green after extraction (validator 15/15, parser full suite, solver 8/8).

---

## Earlier history

Commits before this log exists are captured in `git log`. Relevant branch: `adapt-to-mcp`. Prior landmark commits:
- `83af87a` skills
- `d378ab5` fix bugs, update docs, and simplify
- `4707a9d` add skills and adapt further
- `59b3c97` / `f25c5b4` adapt to v2.0.0
