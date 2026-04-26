# Development Changelog

Running log of framework and MCP changes that affect experiment behaviour, methodology, or reproducibility. Dated newest-first. Entries reference the files touched so `git log` can pick up the details.

Scope covers both this repo (`pddl-copilot-experiments`) and the sibling MCP plugins at `../pddl-copilot` when those changes are driven from here.

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
