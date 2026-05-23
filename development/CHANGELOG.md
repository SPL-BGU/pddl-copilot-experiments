# Development Changelog

Running log of framework and MCP changes that affect experiment behaviour, methodology, or reproducibility. Dated newest-first. Entries reference the files touched so `git log` can pick up the details.

Scope covers both this repo (`pddl-copilot-experiments`) and the sibling MCP plugins at `../pddl-copilot` when those changes are driven from here.

---

## 2026-05-23 — Code-review fixes to the sweep-5 matrix propagation

**Branch:** `sweep5-new-prompts`. Follows the two same-day matrix entries below (`Make sweep-5 neutral/steered split explicit` and `Propagate sweep-5 matrix to ops layers`). Triggered by an extra-high-effort `code-review` pass over the unstaged matrix work; 12 findings landed, all surgical, no methodology impact.

**Status.sh fixes:**
- **#1 Watch-list dedupe** — `watch` loop now tracks a `seen_dirs` set keyed by `dir_cell` so each underlying tools_all sbatch produces at most one watch row. Pre-fix, `tl-neut` and `tl-ster` both mapped to the same dir and each emitted an entry for one physical job. Watch labels now name the dir-level sbatch (e.g. `qwen3.6:35b on/tools_all_minimal`) since the ETA covers both halves of the run.
- **#3 Dir-level pace/eta** — `deltas[cell]["pace_s"]` and `["eta_h"]` were computed from per-logical-column deltas, giving ~2× too-slow pace and ~2× too-pessimistic ETA for any `tools_all` cell. Now aggregated by `LOGICAL_TO_DIR_COND[c]` into a `dir_totals` dict, then written back to each logical child. Siblings show identical pace/eta as a "same sbatch" visual cue. Δ-table rows still split by logical column for visibility.
- **#4 `--help` truncation** — header docstring extended past the prior `sed -n '2,18p'` window after the matrix-doc rewrite; bumped to `2,40p`.
- **#5 `started_now` gate** — the `prev == 0 → started_now` branch now also requires `now < denom`. Without it, cells that arrived already-complete (post-upgrade cache key mismatch → `prev=0`) would mis-render as `▶🆕 started (4560/4560)` instead of silently passing through. The post-upgrade noise floor is otherwise ~30 fake bullets per first run.
- **#6 Sweep-4 replay** — new `steered_enabled` flag (mirrored from `STEERED_VARIANTS_RE`) threaded into the embedded Python via `sys.argv[5]`. When False, the four `*-steered` columns drop from `CELLS` and `COL_HEADERS`, and the steered counts aren't written into `counts`. Replay collapses cleanly to 4 columns × 5 models = 20 cells, no phantom `tl-ster ▶` at 0%.
- **#8 `n_neutral` clamp warning** — `n_steered > n_active` (caused by overlapping/misconfigured regexes) now emits a single stderr `warn:` line summarizing the discrepancy across affected dirs. Run still completes.
- **#9 Dead legacy keys** — `cell_label` shed the legacy `tools_per-task_minimal` / `tools_all_minimal` / `no-tools` entries and the misleading "kept so Δ renders meaningfully" comment. `.get(c, c)` fallback retained for unmapped keys.
- **#10 Malformed-line warning** — counts parser now counts dropped lines (bad shape, non-int) and emits a stderr `warn:` if `count_raw` was non-empty but the matrix was empty. Catches a remote-heredoc wire-format regression instead of silently rendering 0% everywhere.

**filter_variants.py fixes:**
- **#7 `_ARM_VARIANTS` mutation hazard** — presets switched from `set` to `frozenset` so a future `args.variants.add(...)` (latent today, plausible tomorrow) can't silently corrupt the module-level dict.
- **#12 Mutex error consistency** — `--arm` / `--variants` mutex now calls `p.error(...)` (argparse standard exit 2 + usage banner) instead of `sys.exit("error: ...")` (exit 1, no banner). Matches `_parse_variants`'s `ArgumentTypeError` path.

**SKILL.md fix:**
- **#2 Recipe correctness** — the "Checkpoint a sweep" recipe used a single `--arm both` + `--min-out 4560` call that admitted half-finished with-tools cells (4560-9119 of 9120 trials) into the published checkpoint. Rewritten to two passes (`--arm neutral --min-out 4560` + `--arm steered --min-out 4560`), with the result roots named `<name>-neutral` and `<name>-steered`. Sweep-4 replay still uses the single-pass `--variants 5,6,7 --min-out 4560` path.

**CHANGELOG fix:**
- **#11 Compatibility paragraph** — the prior 8-col entry described first-run-after-upgrade as "Δ first-renders every cell as freshly-started" — accurate for the empty-Δ case but understating the wider misclassification. Rewritten to acknowledge fix #5's role in narrowing the impact and to keep the `rm` workaround front-of-mind for unfixed deployments.

**Files touched (this commit):**
- `.claude/skills/cluster-ops/scripts/status.sh` (sys.argv threading, `steered_enabled` filter, malformed warning, oversteered warning, dir_totals pace/eta, watch-list dedup, started_now gate, cell_label cleanup, --help range).
- `.claude/skills/analyzer/scripts/filter_variants.py` (`frozenset` presets, `parser.error` mutex).
- `.claude/skills/analyzer/SKILL.md` (Checkpoint recipe → two-pass arm-aware).
- `development/CHANGELOG.md` (this entry + Compatibility-paragraph rewrite on the entry below).

**Compatibility.** No experiment-result impact. Status cache behaviour: fix #5 narrows the upgrade-cycle mis-classification (no more fake `started_now` for already-complete cells). The `rm ~/.cache/cluster-ops-status.json` workaround is no longer required, but remains the most conservative path. `filter_variants.py` defaults unchanged; the `frozenset` change is API-compatible at every call site (membership + `sorted()` only — verified).

**Verification.**
- `bash -n status.sh` + `ast.parse` on embedded PY — both pass.
- `python3 -m py_compile filter_variants.py` — clean.
- Synthetic-payload smoke covering: (a) sweep-5 main with running with-tools sbatch (verify single watch row, identical sibling pace/eta), (b) sweep-4 replay with `STEERED_VARIANTS_RE=''` (verify 4-column collapse, no phantom rows), (c) pre-split cache (verify completed cells don't mis-render as started_now). All pass.
- `filter_variants.py --arm neutral --variants 14,15,16 ... → argparse banner + exit 2.

---

## 2026-05-23 — Make sweep-5 neutral/steered split explicit in status + analyzer

**Branch:** `sweep5-new-prompts`. Follow-up to the same-day matrix-propagation entry below (user feedback: "isn't there a steered vs neutral? … it should be explicit not implicit").

**TL;DR.** The first cut split only the no-tools arm into a main (neutral) and a control (steered) column; the with-tools column kept a 9120-trial pooled denom that hid the v11-13 vs v14-16 breakdown. This commit splits BOTH arms — every dir's trials are now classified into a neutral or steered logical column, so H1 (tl-neut vs nt-neut) and H2 (tl-ster vs tl-neut) are directly readable from the status board.

**Schema change.**
- `status.sh` matrix: 6 logical columns → **8 logical columns**. CELLS now covers `{no-tools-neutral, no-tools-steered, tools_all-neutral, tools_all-steered} × {on, off}`. All four logical conds have uniform `DENOM=4560`. New `LOGICAL_TO_DIR_COND` map handles queue/running attribution from the dir-level cond back out to its logical children (with-tools sbatch fills both `tl-neut` and `tl-ster` siblings simultaneously). `no-tools-steered` remains the one column without queue inheritance — main and control sbatches share `cond=no-tools` jnames.
- Watch-list iteration now maps logical cells through `LOGICAL_TO_DIR_COND` before looking up `cell_running`; previously the logical-vs-dir mismatch would have silently skipped every cell.
- `total_expected` rolls up to 40 (5 models × 8 columns); coverage caps at 75% on a main-only sweep (control fills the remaining 25%).

**Analyzer ergonomics.**
- `filter_variants.py` gains an `--arm {neutral,steered,both}` flag (mutually exclusive with `--variants`). `--arm neutral` = {11,12,13}, `--arm steered` = {14,15,16}, `--arm both` = full active set (default). `--variants` stays available for sweep-4 replay and ad-hoc subsets.
- `.claude/skills/analyzer/SKILL.md` checkpoint recipe rewritten around `--arm`; sweep-4 replay example kept on `--variants 5,6,7`.

**Doc updates.**
- `.claude/skills/cluster-ops/SKILL.md` — status section now describes the 8-column matrix with an arm-semantics table.
- `.claude/skills/cluster-ops/scripts/status.sh` — header comment block rewritten; `cell_label` short-tag dict adds the four split conds; markdown + terminal renderers use the new 8-col `short_hdrs`.

**Files touched (this commit, on top of the earlier propagation):**
- `.claude/skills/cluster-ops/scripts/status.sh` — CELLS, DENOM, COND_SPLIT, LOGICAL_TO_DIR_COND, cell_status, cell_label, watch list, short_hdrs / CELL_W, header docstring.
- `.claude/skills/cluster-ops/SKILL.md` — 8-column status doc + arm-semantics table.
- `.claude/skills/analyzer/scripts/filter_variants.py` — `--arm` flag + `_ARM_VARIANTS` presets; docstring rewritten around `--arm`.
- `.claude/skills/analyzer/SKILL.md` — `filter_variants` examples switch to `--arm` (explicit-not-implicit framing).
- `development/CHANGELOG.md` — this entry.

**Compatibility.** Status cache from before the 8-col split is read but its keys (`no-tools`, `tools_all_minimal`, `no-tools-steered`) don't match the new logical keys, so `prev_counts.get(cell, 0)` returns 0 for every new logical cell. On the first post-upgrade run, `d["prev"] == 0` for every populated cell — without the follow-up `now < denom` gate (see the same-day "Code-review fixes" entry above), even already-100%-complete cells would mis-render as `▶🆕 started_now`. Recommended workaround: `rm ~/.cache/cluster-ops-status.json` before the first post-upgrade run; the follow-up fix narrows the impact for sessions where the rm is forgotten. No harness change. `filter_variants.py --variants` still accepts arbitrary sets; `--arm` is purely additive.

**Verification.**
- `bash -n` + `ast.parse` on `status.sh` — both pass.
- Smoke-test of `status.sh`'s Python parser against a synthetic 2-dir payload (no-tools 3000/1000 + tools_all 4500/1500) — emits the 8-col table with correct per-column splits (2000/1000/3000/1500 of 4560).
- `python3 -m py_compile` + `--help` on `filter_variants.py` — `--arm` choices render.

---

## 2026-05-23 — Propagate sweep-5 matrix to ops layers (status / submit docs / analyzer defaults)

**Branch:** `sweep5-new-prompts`. Follows commit `ed3a46e` (the prompt-bank + variant-gated dispatch landing) — this entry is the operational propagation of the new matrix into the cluster wrappers and the two `.claude/skills/` skills, so the next status check + submit + analysis don't silently use sweep-4 settings.

**TL;DR.** The harness-side sweep-5 work shipped in `ed3a46e` (v11/v12/v13 neutral + v14/v15/v16 steered; `STEERED_VARIANTS` emit-skip gated by `run_experiment.py --include-no-tools-steered` for the 4th-arm control). This follow-up updates everything *around* the harness:

- **`status.sh`** — `ACTIVE_VARIANTS_RE` default flips from the single-char `[567]` to `1[1-6]` (sweep-5 active set). New `STEERED_VARIANTS_RE` (default `1[4-6]`) splits per-cell no-tools counts into a main column and a synthetic `no-tools-steered` (nt-ctrl) column showing the 4th-arm control fill rate. Per-cell denominators turn asymmetric: `no-tools` and `no-tools-steered` = 4560 each; `tools_all_minimal` = 9120 (sweep-5 with-tools emits 6 variants vs 3 for no-tools; 1520 trials/variant from sweep-3 corpus per `CHANGELOG.md:714`). The remote grep loop now emits `<n_active>\t<n_steered>\t<dirname>` so the local parser can split. Sweep-4 replay is preserved as `ACTIVE_VARIANTS_RE='[567]' STEERED_VARIANTS_RE='' bash status.sh`. The `nt-ctrl` cell never inherits queue/running attribution from its sibling no-tools row (both submits share `cond=no-tools` jnames — status can't distinguish queue state).
- **`sync.sh`** — default DEST renamed `results/sweep3-cluster-…/` → `results/sweep5-cluster-…/`.
- **`.claude/skills/cluster-ops/SKILL.md`** — status doc rewritten to describe the 6-column matrix, asymmetric denominators, and the `--include-no-tools-steered` control workflow. Submit recipe reframed around `submit_full_sweep.sh` with the 20-cell main / control split called out.
- **`.claude/skills/analyzer/scripts/filter_variants.py`** — default `--variants` flips from `{5, 6, 7}` to `{11, 12, 13, 14, 15, 16}`; help text + module docstring rewritten with sweep-5 neutral-only (H1) / steered-only (H2) / sweep-4-replay recipes.
- **`.claude/skills/analyzer/SKILL.md`** — `filter_variants` section + "Checkpoint a sweep" recipe rewritten around sweep-5 defaults and asymmetric `--min-out` (no-tools 4560 vs with-tools 9120); sweep-4-replay example kept alongside as known-good reference per user direction.
- **`cluster-experimenting/README.md`** — `2 × 3 matrix` → `2 × 2 matrix` (sweep-3-era third cond was already gone), cell-count math `30 → 20`, stale `no-tools/think=on gate` sentence corrected, sweep-5 within-cell variant axis + control submit pattern documented in §Conditions.
- **`cluster-experimenting/submit_with_rtx.sh`** — `--all` doc math corrected (`4 models × 6 cells = 24` → `5 models × 4 cells = 20`); smoke-block "4-model pack" → "default model pack (5 models)".
- **`cluster-experimenting/setup_env.sh`** — "submit 4-model pack as ONE rtx_pro_6000 job" → `submit_full_sweep.sh` (20 cells across 3 sbatch arrays).
- **`.claude/skills/analyzer/scripts/plot_focused.py`** — header docstring decouples `DEFAULT_CHECKPOINT` from the (still-valid) historical baseline; explicit comment that current-sweep figures need `<root>` passed.
- **`.claude/skills/analyzer/scripts/build_deck.py`** — docstring reframes `sweep4-v5-v7-first/deck_config.py` as the worked example to copy + edit for a sweep-5 deck.

**Files touched (this commit):**
- `.claude/skills/cluster-ops/scripts/status.sh` (regex defaults, remote heredoc, parsing, render, comments).
- `.claude/skills/cluster-ops/scripts/sync.sh` (default DEST).
- `.claude/skills/cluster-ops/SKILL.md` (matrix doc + submit recipe).
- `.claude/skills/analyzer/scripts/filter_variants.py` (default + docstring).
- `.claude/skills/analyzer/scripts/plot_focused.py` (`DEFAULT_CHECKPOINT` comment + usage doc).
- `.claude/skills/analyzer/scripts/build_deck.py` (docstring).
- `.claude/skills/analyzer/SKILL.md` (`filter_variants` section + Checkpoint recipe).
- `cluster-experimenting/README.md` (matrix shape, cell counts, conditions section).
- `cluster-experimenting/submit_with_rtx.sh` (--all examples + smoke + --all comments).
- `cluster-experimenting/setup_env.sh` (post-install hint).
- `development/CHANGELOG.md` (this entry).

**Compatibility.** No harness behaviour change — only docs, defaults, and a status.sh data-shape extension. Sweep-3/4/4.1 replay paths preserved (override `ACTIVE_VARIANTS_RE` + `STEERED_VARIANTS_RE` on the wrapper side; `filter_variants.py --variants 5,6,7` works as before). Status cache file (`~/.cache/cluster-ops-status.json`) format unchanged at the file level — new sweep-5 cells just add `no-tools-steered` keys; pre-existing keys remain readable. Closes no `ISS-###`.

**Verification.**
- `bash -n .claude/skills/cluster-ops/scripts/status.sh` — bash parses.
- The embedded Python block in `status.sh` parses (ast.parse).
- `python3 -m py_compile` on all touched analyzer scripts.
- `python3 .claude/skills/analyzer/scripts/filter_variants.py --help` — new default + example text renders.
- Live `status.sh` against the cluster — deferred to next user-initiated run; output shape change is purely additive (new columns and labels).

---

## 2026-05-23 — Retire the Ollama inference backend

**Branch:** `sweep5-new-prompts`. Commit `9cdf2da` (the backend cut) plus this entry's follow-up.

**TL;DR.** Removes the entire Ollama path from the harness after the 2026-05-18 cluster backend unification. Single inference client is now `pddl_eval.vllm_client.VLLMClient` (renamed from `VLLMOllamaClient`). No-op for active sweeps — sweep-4/5 have been vLLM-only since the cluster swap.

**Files touched (commit `9cdf2da`):**
- `requirements.txt` — drop `ollama>=0.4.0`. `openai>=1.40.0` is the live runtime dep.
- `pddl_eval/vllm_client.py` — class rename `VLLMOllamaClient → VLLMClient`; ctor kwarg `host=` → `base_url=`; docstring rewritten to describe the OpenAI↔harness-shape adapter without claiming to "mimic Ollama".
- `pddl_eval/chat.py`, `pddl_eval/runner.py` — drop `import ollama` (TYPE_CHECKING), retype `client: "ollama.AsyncClient"` forward-refs to `"VLLMClient"`, reword comments. `FR_OLLAMA_PARSE_ERROR = "ollama_parse_error"` and `is_ollama_parse_error` JSON key retained as stable corpus identifiers (per `scoring.py:30-31` policy). `OLLAMA_TOOL_PARSE_SIGNATURES` variable name kept (internal, unchanged semantics); comment notes the signatures now catch vLLM tool-call parser failures (hermes / qwen3_xml / gemma4) too.
- `run_experiment.py` — drop `import ollama`, `--inference-backend`, `--ollama-host` (replaced by `--llm-base-url`, env `LLM_BASE_URL`), and the `OLLAMA_NUM_PARALLEL` warning print. `meta.inference_backend` no longer written to summary JSON. Help text refreshed.
- `cluster-experimenting/submit_with_rtx.sh` — drop `--backend ollama|vllm` flag; single sbatch path (`run_condition_vllm_rtx.sbatch`). Default GPU now `rtx_6000:1`; `--gpu-type rtx_pro_6000` remains the opt-in escape.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` — exported env var rename `OLLAMA_HOST → LLM_BASE_URL`; drop `--inference-backend vllm` flag from the inner `run_experiment.py` invocations (no longer recognized).
- `cluster-experimenting/submit_full_sweep.sh`, `submit_with_resume.sh` — drop `--backend vllm` forwarding; collapse the Ollama branch in the resume orchestrator.
- `cluster-experimenting/setup_env.sh` — import probe `mcp + ollama` → `mcp + openai`.
- `cluster-experimenting/run_condition_rtx.sbatch` — DELETED (Ollama sbatch).
- `run_background.sh` — DELETED (macOS laptop driver that ran `ollama serve`).
- `notebooks/run_single_model.ipynb`, `notebooks/run_vllm_vs_ollama_smoke.ipynb` — DELETED.
- Docs: `README.md`, `CLAUDE.md`, `EXPERIMENTS_FLOW.md`, `cluster-experimenting/README.md`, `.claude/agents/{experiment-runner,simplifier}.md`, `.claude/skills/{cluster-ops/{SKILL,cleanup},debug-and-simplify/SKILL,simplify/SKILL,plan-review-simplify/SKILL}.md` — sweep misleading present-tense Ollama references; preserve historical context with date stamps where the history is load-bearing.

**Follow-up commit (`<current>`):**
- `development/CHANGELOG.md` — this entry (missing from `9cdf2da`, the simplifier review flagged).
- `.claude/skills/cluster-ops/scripts/status.sh` — drop the per-model `BACKEND = {…}` map, the `dir_backend = "ollama"` branch, and the "skipped N dirs on non-canonical backend" diagnostic. Single-backend now means the BACKEND check is permanently dead-code. Replaced with a one-line informational "archived pre-vLLM dirs ignored" footer.
- `.claude/skills/plan-review-simplify/SKILL.md` — drop `run_background.sh` reference; "Ollama chat loop" → "vLLM chat loop" (the parallel `simplify/SKILL.md` update from `9cdf2da` didn't reach this sibling).
- `run_experiment.py:687-690`, `cluster-experimenting/submit_with_rtx.sh:313-319`, `.claude/skills/cluster-ops/cleanup.md:42` — three stale comments citing the deleted `run_background.sh` / `run_condition_rtx.sbatch`.

**Verification:**
- `python3 -c "from pddl_eval import chat, runner, vllm_client, scoring, summary, prompts, resume, domains"` — all imports clean.
- `python3 run_experiment.py --help` — argparse renders, `--inference-backend` and `--ollama-host` gone, `--llm-base-url` present.
- `python3 -m pytest tests/test_vllm_client.py` — 3/3 pass. Wider `pytest tests/` total identical pre- and post-refactor (pre-existing `TestResults`-as-class collection issue in `tests/_helpers.py:110` unrelated to this change).
- `grep -rn "VLLMOllamaClient\|--inference-backend\|--ollama-host\|import ollama\b" pddl_eval/ run_experiment.py cluster-experimenting/` — empty.

**Compatibility:**
- Active sweeps: no-op. Sweep-4/5 invocations went through `submit_with_rtx.sh` with the vLLM defaults that this commit codifies.
- Archived `slurm_<model>_*` (Ollama-era) corpora in `results/` and `checkpoints/`: read-only. Their `meta.inference_backend = "ollama"` field is still parsed by JSON loaders; nothing in the analyzer pipeline consumes it (verified across `.claude/skills/analyzer/scripts/{aggregate,filter_variants,plot,build_deck,drift_check}.py`).
- Forward-only: new summaries omit `meta.inference_backend`.
- Single inference backend means the `slurm_vllm_<…>` OUT_DIR prefix is now historical (originally introduced to disambiguate vLLM cells from parallel Ollama cells). Renaming would invalidate resume keys mid-sweep, so the prefix stays.

**Memory updates** (off-tree, in the user's auto-memory store): `reference_bgu_ollama.md`, `reference_bgu_self_deploy_ollama.md` marked as retired/historical; `feedback_status_backend_first.md` repositioned around parser-mismatch as the new contamination class; new `project_ollama_retired.md` entry summarising the cut.

---

## 2026-05-23 — Sweep-5 phase A.1: `FR_WRONG_TOOL` + helper inline + cleanup

**Branch:** `sweep5-new-prompts`. Follow-up to the Phase A migration (`beab87a`).

**TL;DR.** Phase A's mechanical migration silently shifted the `FR_TOOL_NOT_SELECTED` bucket: under the polymorphic predecessor it meant "no `validate_pddl_syntax` call at all", but Phase A also routed wrong-validator-tool calls (e.g. `validate_problem` invoked on a `validate_plan` task) into the same bucket. Cross-sweep selection-rate comparisons would have conflated these. Phase A.1 introduces `FR_WRONG_TOOL` so the three failure modes (no validator family / wrong validator / right validator wrong verdict) are reported separately — strictly more informative than the polymorphic predecessor allowed.

**Files touched:**
- `pddl_eval/scoring.py` — new `FR_WRONG_TOOL = "wrong_tool"` constant + `_VALIDATE_TOOL_NAMES` frozenset; three-way split in `check_success` validate branch (right tool → existing verdict-grading path; validator-family but not task-matching → `FR_WRONG_TOOL`; nothing validator-family at all → `FR_TOOL_NOT_SELECTED`); `_call_matches_validate_task` deleted (production-dead after Phase A — `check_success` had collapsed to inline `tc["name"] == task`).
- `run_experiment.py:66-93` — re-export `FR_WRONG_TOOL` from scoring.
- `tests/test_scoring.py::test_call_matches_validate_task` — deleted along with the helper. Behavior coverage moved to `test_check_success.py` (the three FR outcomes are exercised against `validate_plan` and `validate_domain` tasks).
- `tests/test_check_success.py` — two existing "wrong tool" cases now assert `FR_WRONG_TOOL`. New explicit `FR_TOOL_NOT_SELECTED` case where the model called `classic_planner` (non-validator-family) so the three-way split is fully exercised.
- `.claude/skills/analyzer/scripts/plot.py` — `wrong_tool` added to `FAILURE_REASONS` + `FAILURE_COLORS`. Prevents the sweep-4 audit's "anonymous grey 'other' slice" bug from recurring on `validate_*` cells.
- `EXPERIMENTS_FLOW.md` — §4.1 metrics note rewritten to enumerate the three FR outcomes; §9 `failure_reasons` description adds `FR_WRONG_TOOL` to the notable-tags list with its semantics + provenance ("never appears in pre-marketplace-1.4.0 trials").
- `pddl_eval/{scoring,chat,domains}.py` + `tests/_helpers.py` — migration-narrative docstring boilerplate trimmed from five sites. The migration story belongs in this CHANGELOG, not in docstrings that should describe current behavior.
- `development/CHANGELOG.md` — fixed misleading parenthetical in the 2026-05-23 Phase A entry that claimed `_call_matches_validate_task` was called by `check_success` (it wasn't, post-Phase-A).

**Verification:** `bash tests/verify.sh` — 6 test files, all pass.

**Compatibility:**
- Pre-marketplace-1.4.0 trials in `results/` and `checkpoints/` never carry `FR_WRONG_TOOL` (the marketplace surface couldn't produce it). The analyzer whitelist addition is forward-only; historical plots are byte-identical.
- Cross-sweep aggregation: `(FR_TOOL_NOT_SELECTED + FR_WRONG_TOOL)` in sweep-5 is the apples-to-apples counterpart of `(FR_TOOL_NOT_SELECTED + wrong-shape subset of FR_VERDICT_MISMATCH)` in sweep-3/4. The latter is recoverable from stored `tool_calls[*].arguments` if direct comparison is needed in the paper.
- No prompt-bank work yet (still on `sweep5-new-prompts` branch; Phase B is the design-doc rewrite + Phase C the `prompts.py` / `runner.py` implementation).

---

## 2026-05-23 — Marketplace 1.4.0 adoption: validator tool split (sweep-5 foundation)

**Branch:** `sweep5-new-prompts`. **Marketplace pin:** post-PR-52 (pddl-copilot @ `2850bc4`, marketplace `1.4.0`).

**TL;DR.** Sibling-repo PR-#52 split the polymorphic `validate_pddl_syntax` into three task-aligned tools — `validate_domain`, `validate_problem`, `validate_plan` — whose JSON schemas enforce their required arguments. The dominant sweep-3/sweep-4 `validate_plan` failure mode (model calls validator with only `domain`+`problem`, tool returns the consistency verdict instead of the plan verdict, scorer tags `FR_VERDICT_MISMATCH`) is now structurally unreachable — the model can no longer call a polymorphic tool with wrong-shape arguments. Cross-repo migration in this commit; no prompt-bank changes yet (those land in a follow-up commit on the same branch).

**Files touched (this repo):**
- `pddl_eval/chat.py:86` — `_PINNED_VERBOSE_FALSE` updated from `{"validate_pddl_syntax", "get_state_transition"}` to `{"validate_domain", "validate_problem", "validate_plan", "get_state_transition"}`. Docstring at `:58` updated to reference the split.
- `pddl_eval/scoring.py:65-88` — `_call_matches_validate_task` collapses from an argument-shape dispatcher to a name match: `tc["name"] == task` for the three `validate_*` tasks. The old polymorphism gate (rejecting domain-only calls when grading `validate_plan`) is no longer needed.
- `pddl_eval/scoring.py:271-292` — `_validate_model_plan` routes to `validate_plan` directly (was `validate_pddl_syntax`).
- `pddl_eval/scoring.py:408-426` — `check_success` validate branch uses `_used_tool(tool_calls, task)` (task-name == tool-name) instead of looking up the legacy polymorphic tool name.
- `pddl_eval/domains.py:112-130` — `_validate_capture` routes by args to the correct task-aligned tool (presence of `plan` → `validate_plan`; `problem` → `validate_problem`; else → `validate_domain`). Keeps the six call sites in `generate_ground_truth` uniform.
- `tools/build_fixtures.py:105-125` — `_validate_domain` / `_validate_problem` / `_validate_plan` helpers route to their matching tools.
- `tests/_helpers.py:64-99` — `plan_sensitive_validator` handler dispatches by tool name (not arg shape); `validate_plan` still matches plan-text against the fixture's oracle/bad plan.
- `tests/test_check_success.py` — two cases recharacterized: the old "wrong arg shape" failures (which grade as `FR_VERDICT_MISMATCH` under the polymorphic tool) become "wrong tool name" failures (graded as `FR_TOOL_NOT_SELECTED`). The model can no longer call the same tool with wrong-shape args; calling a different validator tool is the residual error.
- `tests/test_scoring.py::test_call_matches_validate_task` — rewritten to assert the simplified name-match semantics. Includes a defensive case for the legacy `validate_pddl_syntax` tool name (always returns False).
- `EXPERIMENTS_FLOW.md` — §3 task table, §4.1 metrics list, §6 ground-truth list, §8 MCP API table, §11 paper-diff row updated to the three-tool surface.

**Verification.** `bash tests/verify.sh` — 6 test files, 401/401 assertions pass.

**Compatibility notes.**
- v0–v10 prompt strings are byte-stable (no edits). Replay-by-rerun of sweep-3 / sweep-4 / sweep-4.1 cells against the new marketplace pin will fail: the model can no longer call `validate_pddl_syntax` (tool removed). This is intentional per user direction (`feedback_pushback_on_methodology_shortcuts`); sweep-3/4/4.1 results in `results/` and `checkpoints/` remain valid as historical snapshots tied to their respective marketplace pins.
- Recorded `tool_calls[*].name` in old `trials.jsonl` continues to read `"validate_pddl_syntax"`. Legacy trials were graded at write-time and stored their `failure_reason` in the record; analysis paths read the stored field rather than re-running `check_success`, so the new tool-name expectations don't disturb historical aggregation.
- Sweep-5 starts fresh on the marketplace 1.4.0 pin. Trial-key shape unchanged (10-tuple); no `runner.py` resume-key edits.

**Sources of the split design (per PR-52 description):** Anthropic "Define tools" docs (3-4 sentence per-tool descriptions, schema-in-`tools=[]` convention), Anthropic engineering "Writing tools for agents" (consolidation, namespacing, "implicit context explicit"), BFCL methodology (relevance / selection / parameter-filling decomposition).

**Next on branch `sweep5-new-prompts`:** rewrite `development/sweep_prompt_bank_design.md` to reflect (a) Option C thin per-task system prompts, (b) post-split simplified one-sentence steered directives, (c) sweep-5 as full (no-tools, steered) backed-up arm — then implement in `pddl_eval/prompts.py` + `pddl_eval/runner.py`.

---

## 2026-05-20 — PR-#66 contamfix: `_CTX_OVERFLOW_RE` regex + analyzer denominator drifts + gemma context limitation

**TL;DR.** Six-agent audit (PR-#66) of the sweep-4 corpus surfaced four root issues. One was the dominant data-quality problem (24 600 corrupted trials across the corpus; 24 in the active checkpoint). Three were latent analyzer denominator bugs that mask themselves on clean data but mis-aggregate on edge-case rows. All four addressed in one commit.

1. **`pddl_eval/vllm_client.py` `_CTX_OVERFLOW_RE` regex didn't match the new vLLM error body** ("upper bound for N input tokens" vs the old "at least N input tokens"). When the parser returned None the BadRequestError re-raised out of `chat()`, the runner's generic `except Exception` caught it, and the trial landed as `FR_EXCEPTION` with `tokens={}` and `tool_selected=None` — exactly the corruption pattern the existing retry-and-synthesize path was designed to prevent. Single-line regex extension `(?:at least|upper bound for) (\d+) input tokens` matches both shapes; verified empirically against contaminated rows. New `tests/test_vllm_client.py` pins both shapes so the next vLLM-message-text change trips a unit-test failure instead of silently corrupting a sweep.

2. **`.claude/skills/analyzer/scripts/build_deck.py:201-209` `tool_selected_rate` denominator** filtered `r.get("tool_selected") is not None`, dropping trials that crashed before tool-selection could be classified. On a cell with 24 such rows (gemma4 simulate, the cleanup target above), the function reported **100% tool-selection vs the canonical 92%** — an 8-point inflation. Canonical denominator in `summary.py:186-188` is every with-tools trial in the cell. Fix mirrors canonical.

3. **`build_deck.py:268-300` `token_stats` denominator** included rows with empty `tokens={}` (numerator contributes 0, denominator inflated by 1). On the same gemma simulate cell every token mean was biased downward by exactly 8% (`prompt_mean` 10979 reported vs 11934 canonical). Canonical `_add_tokens` in `summary.py:49-65` skips empty-tokens trials. Also: `turns` default fixed from `1` to `0` to match canonical; per-turn ratios now skip turns==0 trials to avoid div-by-zero. `base` subset still drives `fail_pct` (all trials), `sub` drives means (token-bearing only).

4. **`.claude/skills/analyzer/scripts/plot.py:94-99` `FAILURE_REASONS` whitelist** was missing `format_parse_fail` and `think_overflow`. Trials with these tags were silently bucketed into the unnamed grey "other" slice on `fig4_failure_breakdown`. On the Qwen3.5-0.8B off/no-tools cell, **85.6% of validate_domain failures and 69.9% of validate_plan failures** rendered as anonymous "other" — the dominant failure mode for no-tools cells with the v5/v6/v7 prompt rewrite was unattributed. Added both to `FAILURE_REASONS` + `FAILURE_COLORS`.

**Contamfix cleanup (separate from this commit, local only).** 24 corrupted rows dropped from both source and filtered gemma `on/tools_all_minimal` cells; summaries regenerated; `checkpoints/sweep4-v5-v7-first/gemma4_26b_a4b_trials.zip` refreshed. `.bak_contamfix` files preserved next to each cleaned `trials.jsonl` for one-cycle reversibility. Source-dir sweep-3 residue (52 rows, `prompt_variant=1`, `APIConnectionError` from pre-`a8c09a4` runs) deliberately not touched per user direction (already excluded by the `{5,6,7}` filter).

**Methodology finding — gemma4:26b-a4b context limitation (ISS-021).** With the regex fix landed, the 24 gemma `simulate` trials that previously corrupted will now land as `FR_TRUNCATED_NO_ANSWER` — caught and accountable, but the model never gets to attempt those tasks (prompt is 6× the 16 384-token cap). Will reoccur identically on every resubmit. **Accepted as a documented limitation; `--max-model-len` is NOT being changed.** Affected (domain, problem) pairs documented in OPEN_ISSUES ISS-021.

**Verification cancelled cluster jobs (separate cluster-ops step).** All 11 running + pending sweep-4 jobs were cancelled prior to this commit landing so the resubmit (gated on a separate explicit go) runs against the fixed runner. Resubmit will refill the gemma cell to 4560 with 24 `FR_TRUNCATED_NO_ANSWER` rows in the previously-corrupted slots.

**Files touched.**
- `pddl_eval/vllm_client.py:60-78` — regex extension + drift-history doc-block.
- `tests/test_vllm_client.py` — new file; 3 regression tests (old body, new body, unrelated-400 negative).
- `.claude/skills/analyzer/scripts/build_deck.py` — `tool_selected_rate` denominator (line 201); `token_stats` denominator + turns default (lines 268-300).
- `.claude/skills/analyzer/scripts/plot.py:94-122` — `FAILURE_REASONS` + `FAILURE_COLORS` add 2 entries.
- `development/OPEN_ISSUES.md` — new ISS-021 entry for the gemma context limitation.
- `development/CHANGELOG.md` — this entry.

**Files NOT touched.**
- `pddl_eval/runner.py` — no need; the regex fix routes context-overflow back through the existing `_synthesize_overflow_response` path. Adding a `BadRequestError` catch in the runner would have masked unrelated 400s.
- `pddl_eval/summary.py` — already canonical; the audit confirmed it as the reference.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch:202` — `--max-model-len 16384` retained per ISS-021 decision; gemma simulate failures on big problems documented, not engineered around.
- Sweep-3 source corpus — out of scope per user direction.

---

## 2026-05-20 — PR-#66 review fixes: infra_failure summary filter, bounded retry abort, status.sh anchoring

**TL;DR.** Four small follow-ups on top of `dce5e29` / `6350c0c` / `b74bdd1` / `fba91e5` / `a8c09a4`, addressing items raised in the second PR-#66 review pass:

1. **`infra_failure` records now filtered from the runner's returned list** (`pddl_eval/runner.py:843`). Previously the JSONL writer correctly skipped these (so `trials.jsonl` stayed canonical and resume was correct), but `run_single_task_experiment` returned the in-memory list unfiltered. Downstream `save_results` → `summarize_single_task` therefore wrote per-cell summary JSONs that counted transport-blip records (e.g. SLURM SIGTERM races) toward `total` / `failure_reasons`. On-disk corpora are unaffected — the analyzer aggregates from `trials.jsonl` — but a truncated run could persist a misleading per-cell summary. Docstring at `runner.py:241–247` corrected (writer lives in `run_one`, not `run_single_task_experiment`).

2. **Bounded consecutive-`infra_failure` abort** (`pddl_eval/runner.py:_INFRA_FAIL_ABORT = 7`). The broad `APIConnectionError` catch added in `a8c09a4` correctly treats SLURM-SIGTERM-near-TIMEOUT races as infra blips, but blindly silently-skipping every connection error could mask a wedged vLLM (wrong port, OOM-loop, crashed at startup). After 7 consecutive infra fails the runner now raises `RuntimeError`, propagating up to `main`'s `KeyboardInterrupt`-style "save partial results" path. SLURM gets a non-zero exit; resume re-attempts the in-flight keys on rerun. Counter resets on any successful trial so transient bursts don't compound across the cell.

3. **`status.sh` regex anchored + grep I/O errors surfaced** (`.claude/skills/cluster-ops/scripts/status.sh:80–94`). The variant filter `"prompt_variant": $VARIANTS_RE` (default `[567]`) would silently match the first digit of a two-digit variant if sweep-5+ ever introduced v10/v15/etc.; now anchored with a trailing `[^0-9]` so the character class binds to the JSON value's terminator (comma). Separately, `2>/dev/null || echo 0` was swallowing real grep errors (rc≥2) as zero counts; now explicit on exit code so rc=1 (no match) → 0 silently but rc≥2 (real I/O error) prints a warn line to stderr.

4. **`development/sweep4_plan_new_prompts.md` stale table marked.** The plan-doc table at lines 17–22 said `tools_per-task_minimal` retirement was "deferred to sweep-5," contradicting `cluster-experimenting/lib/defaults.sh:32` and the 2026-05-19 sweep-4 finalisation entry which pulled the retirement forward. One-line revised stripe added above the table so readers landing on the plan-doc first see the current standing policy.

**Methodology / reproducibility.** No change to trial wire format; `TaskResult.infra_failure` already populated. Sweep-4 data on disk is fine — analyzer reads `trials.jsonl`, never the polluted summary JSONs. The bounded-abort flips an in-progress wedge from "silently produce an empty corpus" to "fail loud with a non-zero SLURM exit," which is the correct posture for an unattended cluster sweep.

**Files touched.**
- `pddl_eval/runner.py` — `_INFRA_FAIL_ABORT` constant; consecutive-fail counter in the `asyncio.as_completed` loop; `new_results` filter; docstring fix.
- `.claude/skills/cluster-ops/scripts/status.sh` — anchored regex; explicit rc=2+ warn path.
- `development/sweep4_plan_new_prompts.md` — revised-stripe note above the deferred-retirement table.
- `development/CHANGELOG.md` — this entry.

**Files NOT touched.** `pddl_eval/summary.py` (defense-in-depth filter intentionally skipped — runner-boundary filter is the actual fix and is sufficient); `pddl_eval/vllm_client.py`; any sbatch.

---

## 2026-05-19 — Adopt pddl-copilot marketplace 1.3.0 (PR-50 merged as `a259a38`)

**TL;DR.** Sibling marketplace bumped to 1.3.0 (solver 2.1.1→2.2.0, validator 2.1.1→2.2.1, parser 1.4.0→1.5.0). Two real bugs fixed upstream: solver crashes (INTERNAL_ERROR / UNSUPPORTED_PROBLEM / INTERMEDIATE / Java-missing) now surface as `{"error": True, ...}` instead of silently masquerading as empty-plan no-finds; validator `report` no longer leaks the misleading `"Plan is VALID"` / `"Plan is INVALID"` line on domain-only / domain+problem calls (fix lives in pyvalidator 0.1.5 upstream). **Zero code change required in this repo** — the framework bridge already (a) reads `valid` not `report` in `_parse_validation_verdict` (chat.py:58-71), (b) detects `{error: True}` in `_tool_error_seen` (scoring.py:295-313), and (c) connects only `pddl-solver` + `pddl-validator`, so every pddl-parser change in PR-50 is out of scope. PR description's sibling-agent validator pass and an independent re-read both returned SAFE.

**Methodology consequence (the headline).** Pre-PR-50, solver crashes were classified as `FR_PLAN_INVALID` on the `solve` task (scoring.py:380): the model was charged with a failure that was actually the planner blowing up. Post-PR-50 the same crashes correctly route to `FR_TOOL_ERROR` via the existing `_tool_error_seen` path (scoring.py:376-379). **`solve` pass% does not move** — both buckets are `result_correct=False` — but the attribution is now honest. Java-missing ENHSP runs especially benefit (was silently invisible).

**Possible second-order effects on sweep-4 (deliberately measured before lock-in).**
- `validate_domain` / `validate_problem` with-tools: clean `report` may marginally shift VERDICT accuracy on small models that were parroting the leaked "Plan is VALID" line. Direction is not predictable a priori — the leak either helped (lucky parroting on actually-valid cases) or hurt (parroting on actually-invalid cases).
- `solve` with-tools FR-histogram: small `FR_PLAN_INVALID` → `FR_TOOL_ERROR` shift on cells where solver crashes occurred.
- All other cells: expected zero drift.

**Reproducibility / byte-equality.**
- Aggregate metrics: stable.
- `tool_calls[*].result` strings recorded in pre-PR-50 `results/` are **not byte-comparable** with post-upgrade trial logs on (i) `validate_pddl_syntax` calls without a plan (report-text change) and (ii) failing `classic_planner` / `numeric_planner` calls (error-shape change). Same accepted-degradation precedent as the original `verbose=False` bridge (EXPERIMENTS_FLOW.md §11).
- Canonical signals (`valid` field, `error` boolean, `trajectory` shape) unchanged.

**Out-of-scope changes documented for completeness.**
- pddl-parser 1.5.0 (Literal `parser` arg, `normalize_pddl` file-path widening + `errors` field, `inspect_domain.types` drops implicit `"object"` root, `:requirements` preserves source order, `get_applicable_actions` cross-backend deterministic lex-sort, `get_trajectory` list[str]): the parser plugin is not in `REQUIRED_PLUGINS`, so none of these reach our LLM or scorer.
- `validate_pddl_syntax` + `get_state_transition` `plan` now accept `list[str]`: additive, we still pass a joined string in `_validate_model_plan` (scoring.py:284).
- `get_state_transition.trajectory` shape (the `simulate` byte-equality oracle, EXPERIMENTS_FLOW.md:145): **explicitly deferred** in PR-50 `docs/breaking-changes.md` to avoid oracle-fixture regeneration. Safe.

**Operational steps taken.**
- Local validator venv at `../pddl-copilot/plugins/pddl-validator/.venv` deleted so pyvalidator>=0.1.5 pin is picked up on next launch.
- Cluster-side validator venv to be wiped during the smoke-submission step (delegated to cluster-ops).
- Smoke submitted across the full vLLM roster (`Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`) on the new marketplace to measure the actual drift magnitude vs the most recent comparable `checkpoints/cluster-20260517/` corpus before locking sweep-4's tool surface.

**ISS-005 status nudge.** PR-50 widens the set of failure modes that route into `FR_TOOL_ERROR` (was: transport / timeout / arg-rejection / parse-error; now: + INTERNAL_ERROR / UNSUPPORTED_PROBLEM / INTERMEDIATE / Java-missing). The (a)/(b)/(c) split that ISS-005 deferred to post-hoc grep on `TaskResult.error` is now modestly more valuable as a diagnostic. See OPEN_ISSUES.md ISS-005 addendum.

**Files touched (this repo).**
- `development/CHANGELOG.md` (this entry)
- `development/OPEN_ISSUES.md` (ISS-005 addendum)

**Files NOT touched.** No source change in `pddl_eval/`, `run_experiment.py`, `tests/`, or any cluster-experimenting sbatch — the upstream fix is consumed by the existing bridge logic without modification.

**Sweep-4 framing.** Adopting PR-50 ahead of sweep-4 (vs pinning to pre-PR-50 marketplace) means sweep-4's prompt v5/v6/v7 ablation is run against a slightly cleaner tool surface than sweep-3. The drift smoke submitted with this change sizes the perturbation; if material, the sweep-4 results will be noted as having a small tool-surface confound on top of the prompt-rewrite effect. Sweep-3 results stay on disk as drift anchors per the `feedback_pushback_on_methodology_shortcuts` corpus-isolation rule.

---

## 2026-05-19 — Sweep-4 finalisation: PR-#66 review fixes + per-task retirement pulled forward

**TL;DR.** Three follow-ups to the prompt-rewrite commit (`dce5e29`) before the cluster sweep launches:

1. **Simulate v5/v6/v7 no-tools** now embed a one-step schema-shaped example (`{"step": ..., "action": ..., "state": {"boolean": [...], "numeric": {}}}`) — closes finding 5's secondary leak that the reviewer flagged ("wire format described but not shown"). The example matches `SimulateResponse → StateStep → StateSnapshot` (nested `state.boolean`/`state.numeric` per `pddl_eval/schemas.py:45-67`); the surrounding text was also updated from bare `boolean`/`numeric` to `state.boolean`/`state.numeric` so the prompt names what the format constraint actually enforces.
2. **`tools_per-task_minimal` retired from sweep-4** (was originally deferred to sweep-5 per `development/sweep4_plan_new_prompts.md`). Sweep-4 cluster matrix is now `{no-tools, tools_all_minimal} × {think on, think off}` = 4 cells/model. Sweep-3 ran 3 conditions × 2 think = 6 cells/model — so sweep-4 vs sweep-3 now differs on TWO axes: (a) v0/v1/v2 → v5/v6/v7 prompts (the headline differential), AND (b) per-task condition retirement. Writeup will need to attribute outcome shifts to both effects, with PR-50's tool-surface delta as a third (empirically silent at smoke scale per `development/sweep4_fr_pivot.md`).
3. **Stale `run_smoke_vllm_vs_ollama.sbatch` references** swept from `cluster-experimenting/README.md`, `lib/defaults.sh` (including the runtime-visible stderr at the `vllm_lookup` refused-model branch), `submit_full_sweep.sh`, and `run_condition_vllm_rtx.sbatch`. Operators following the README or hitting a refused-model error are now pointed at `submit_with_rtx.sh --backend vllm --smoke <model>` (the vLLM smoke fastpath added in `4f50a5b`). The script itself was deleted in `06f2b4b`; CHANGELOG historical entries are deliberately left untouched.

**Why pull the per-task retirement forward.** The plan-doc rationale for keeping it through sweep-4 was "hold the matrix constant so sweep-3 vs sweep-4 cleanly isolates the prompt change." Trading that isolation off against (i) ~33% fewer GPU-hours per sweep, (ii) one fewer condition for the analyzer to plot, (iii) the per-task arm was already slated for retirement anyway in sweep-5, and (iv) the sweep-3 `tools_per-task_minimal` results stay on disk for post-hoc 2-condition-vs-3-condition framing if needed. Net: simpler matrix, faster turnaround, deferred attribution work absorbs the cost.

**Files touched.**
- `pddl_eval/prompts.py` — v5/v6/v7 `simulate` no-tools entries updated (additions only — still no in-place edits to v0–v4).
- `cluster-experimenting/lib/defaults.sh` — `PDDL_DEFAULT_CONDITIONS` drops `tools_per-task_minimal`; `PDDL_DEFAULT_SBATCH_CONDITIONS` follows; 4 stale `run_smoke_vllm_vs_ollama.sbatch` references rewritten.
- `cluster-experimenting/README.md` — vLLM-smoke section rewritten around `submit_with_rtx.sh --backend vllm --smoke`; recipe block uses the wrapper, not raw sbatch.
- `cluster-experimenting/submit_full_sweep.sh` — prereqs comment updated.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` — log-preservation idiom comment updated.
- `development/CHANGELOG.md` — this entry.

**Not touched.** `pddl_eval/runner.py`, `pddl_eval/scoring.py`, `pddl_eval/schemas.py`, the v0–v4 prompt strings (sweep-3 corpus identity preserved), any sbatch resource budget. The cluster matrix change is data-only (defaults.sh constant); the wrapper's cell-builder logic and per-cell `--time` ceilings are unchanged.

---

## 2026-05-19 — Sweep-4 prompt rewrite: append v5/v6/v7, flip ACTIVE_PROMPT_VARIANTS to (5, 6, 7)

**TL;DR.** Phase 1 of sweep-4 lands per `development/sweep4_plan_new_prompts.md`. Three new prompt variants (v5/v6/v7) are appended to each of the 5 task lists in `pddl_eval/prompts.py`; a sparse with-tools override dict `PROMPT_TEMPLATES_TOOLS_OVERRIDE` adds per-condition divergence for v5–v7 only; `ACTIVE_PROMPT_VARIANTS` flips from `(0, 1, 2)` to `(5, 6, 7)`. v0–v4 strings are byte-identical to sweep-3 — corpus identity for variant indices 0–2 is preserved (see `feedback_pushback_on_methodology_shortcuts` and the resume-key reproduction guarantee at `pddl_eval/runner.py:441–451`).

**The six leaks (see `.local/prompts_review.md`) and how v5–v7 address them.**
1. `validate_*` VERDICT trailer fighting the with-tools system prompt → trailer dropped in both branches; with-tools branch tells the model to call the validation tool, no-tools branch relies on `format=ValidateResponse` (`pddl_eval/schemas.py:35–42`) and `_VERDICT_RE` as a fallback.
2. `validate_plan` with-tools dropping the `plan` argument (the dominant FR_VERDICT_MISMATCH leak per `development/sweep4_fr_pivot.md`) → every v5/v6/v7 with-tools template explicitly names `domain`, `problem`, AND `plan` as required arguments.
3. `_GUIDED_SUFFIX` (disabled) being the only place tool-arg shape was taught → arg names now baked into per-task with-tools templates; `_GUIDED_SUFFIX` stays disabled.
4. `solve` / `simulate` user prompts feeling textually satisfiable → with-tools branch names a "planner tool" / "state-transition tool" by category (not by exact tool name — that's deferred to the sweep-5 skill-task arm).
5. `simulate` no-tools not teaching `_normalize_trajectory`'s wire format (`pddl_eval/scoring.py:149–227`) → v5/v6/v7 no-tools encode the three invariants: step 0 = initial state with empty action, EVERY currently-true predicate, parenthesised lowercase form.
6. `solve` no-tools not teaching action wire format → v5/v6/v7 no-tools spell out single parenthesised PDDL actions with concrete examples (`(pick-up a)`, `(unstack a b)`, `(stack a b)`).

**Active call site.** `pddl_eval/runner.py:266` becomes override-aware: when `with_tools=True` and `prompt_variant ∈ override[task]`, the override template wins; otherwise the base `PROMPT_TEMPLATES[task]` lookup is used. For v0–v4 the override dict is empty per task, so the with-tools branch falls through to base — sweep-3 wire-equivalence preserved. Archived chain call site at `runner.py:821` deliberately untouched (CLAUDE.md `single-task only` rule).

**Drift safety.** v5/v6/v7 are disjoint from any sweep-3 resume key (variants 0–4 only). v3/v4 stay disabled (kept in the lists to preserve index reservation, matching the existing comment pattern). No new prompt-style choice introduced — `WITH_TOOLS_SYSTEM`, `PROMPT_STYLE_CHOICES`, and `TOOL_FILTER_CHOICES` are byte-identical to sweep-3; `skill-task` and per-task retirement are deferred to sweep-5.

**Baselines (canonical).**
- **Sweep-3 baseline** (pre-rewrite + pre-PR-50): variants `(0, 1, 2)`, marketplace 1.2.0, e.g. `results/cluster-20260517/`. Reproducible by checking out the sweep-3 sha tag.
- **Sweep-4** (this entry): variants `(5, 6, 7)`, marketplace 1.3.0 (post-PR-50). The prompt rewrite is the headline differential; the marketplace 1.3.0 tool-surface delta is empirically silent at smoke scale per `development/sweep4_fr_pivot.md` (drift verdict 2026-05-19) and folded into a single-line caveat in the eventual writeup.

**Files touched (this repo).**
- `pddl_eval/prompts.py` — docstring rewritten; v5/v6/v7 appended to all 5 task lists; new `PROMPT_TEMPLATES_TOOLS_OVERRIDE` dict; `ACTIVE_PROMPT_VARIANTS = (5, 6, 7)`.
- `pddl_eval/runner.py` — single import addition (`PROMPT_TEMPLATES_TOOLS_OVERRIDE`) and override-aware template lookup at `:266`. Archived chain path at `:821` untouched.
- `run_experiment.py` — argparse help for `--num-variants` mentions the sweep-4 active set; signature and default unchanged (default reads `len(ACTIVE_PROMPT_VARIANTS)`).
- `development/CHANGELOG.md` — this entry.

**Files NOT touched.** `pddl_eval/scoring.py`, `pddl_eval/schemas.py`, `pddl_eval/summary.py`, `pddl_eval/resume.py`, `WITH_TOOLS_SYSTEM`, `PROMPT_STYLE_CHOICES`, `TOOL_FILTER_CHOICES`, any sbatch script, the analyzer skill. The cluster matrix for sweep-4 is held identical to sweep-3 (same condition slugs, models, think modes); only variant indices differ.

**Up next.** Local smoke (`python run_experiment.py --partial 1 --models qwen3:0.6b --conditions both --tool-filter all`) eyeballs one trial per task to confirm the override wiring before the cluster submission. After PR review, push branch `sweep4-new-prompts` to `main` and proceed to Phase 2 (cluster sweep) per the plan.

---

## 2026-05-18 — Roster: gemma4:31b dense Ollama → gemma4:26b-a4b MoE vLLM (backend split retired)

**TL;DR.** Replaces the dense `gemma4:31b` (Ollama-only, parser pending vLLM verification) with `gemma4:26b-a4b` (MoE A4B, ~4B active of 26.5B total, AWQ-INT4) served on vLLM. Same publisher and quant pipeline as the verified `qwen3.6:35b` (`cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`). Full 5-model `PDDL_DEFAULT_MODELS` roster now runs on a single backend (vLLM, `rtx_6000:1`) — retires the 2026-05-12 → 2026-05-18 backend split. Active sweep roster: `Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`, `gemma4:26b-a4b`.

**Phase A — smoke verification.**
- Phase A.1 (`7106f68`) added `gemma4:26b-a4b` to `vllm_lookup` (HF id, `TOOL_CALL_PARSER=gemma4`, `REASONING_PARSER=none`) and refreshed the Gemma-4 example block in `run_smoke_vllm_vs_ollama.sbatch`. Not yet in `PDDL_VLLM_VERIFIED_MODELS` — `submit_with_rtx.sh --backend vllm` refused the tag until smoke cleared the gate.
- Smoke `17633538` crashed at vLLM startup: `ValueError: Chunked MM input disabled but max_tokens_per_mm_item (2496) is larger than max_num_batched_tokens (2048)`. The HF task tag `image-text-to-text` triggers vLLM's auto-load of Gemma-4's multimodal vision tower; the per-MM-item budget exceeds vLLM's default 2048-token batch ceiling.
- Phase A.2 (`59be812`) added a `MAX_NUM_BATCHED_TOKENS` env-var-conditional flag to the smoke sbatch (mirrors `EAGER_FLAG`/`NUM_PREDICT_FLAG`), threaded `MAX_NUM_BATCHED_TOKENS=4096` into the `gemma4:26b-a4b` `vllm_lookup` case, and updated the `vllm_lookup()` header to document the new export.
- Resubmit smoke `17638752` passed: `vllm ready (344s)`, VRAM 42218/49140 MiB (85%), 80 trials at concurrency=4. Tools cells: solve/validate_domain/validate_problem/simulate ToolSel = 1.00 (N=2/4/12/2); validate_plan 0.95 (N=20, 1 `tool_not_selected`). No-tools think=on shows systemic `truncated_no_answer` failures on validate_plan / validate_problem (CoT eats the 6144-token cap before VERDICT) — expected pre-rewrite behavior and falls into sweep-4's v5/v6/v7 prompt work scope.

**Phase B — roster swap (this commit).**
- `cluster-experimenting/lib/defaults.sh`: `PDDL_DEFAULT_MODELS` and `PDDL_SLOW_MODELS` swap `gemma4:31b` → `gemma4:26b-a4b`; `PDDL_VLLM_VERIFIED_MODELS` appends `gemma4:26b-a4b`. Phase-A candidate marker comment removed (no pending candidates). `gemma4:26b-a4b` `vllm_lookup` case doc-comment updated with smoke-17638752 VRAM peak.
- `cluster-experimenting/run_condition_vllm_rtx.sbatch`: consumer for `MAX_NUM_BATCHED_TOKENS` — `unset` before each `vllm_lookup` call (prevents leftover bleed if a multi-model job ever pairs MM and text-only models), build conditional flag, splice into the apptainer `python3 -m vllm.entrypoints.openai.api_server` invocation after `--enable-prefix-caching`.
- `cluster-experimenting/submit_with_resume.sh`: `OLLAMA_MODELS=()`; both echo lines and the squeue tail gate on a non-empty Ollama job id. Header doc rewritten to record that the script now collapses to a single vLLM submission post-backend-unification; Ollama branch is the extension point.
- `cluster-experimenting/submit_full_sweep.sh`: step `[3/3]` flips from `--backend ollama gemma4:31b` (rtx_pro_6000:1, 72h) to `--backend vllm gemma4:26b-a4b` (rtx_6000:1, 48h). All three steps are now vLLM.
- `cluster-experimenting/submit_with_rtx.sh`: comment refs to `gemma4:31b` and `PDDL_SLOW_MODELS=(gemma4:31b, ...)` swap to `gemma4:26b-a4b`. The `--no-tools` example, the `--no-auto-prioritize` slow-set list, and the `rtx_6000` case comment (peak VRAM 26 GB → 24 GB; reframed as the default for vLLM, not an emergency escape) all updated. The `gemma4*` think-mode carveout comment is reworded (it only applied to gemma2-era tags).
- `cluster-experimenting/run_condition_rtx.sbatch`: legacy Ollama sbatch header rewritten — no active model uses it post 2026-05-18; retained for re-running archived `slurm_gemma4_31b_*` corpora as drift anchors. VRAM-fit table reframed as historical reference; gemma4:31b row tagged retired.
- `.claude/skills/cluster-ops/scripts/status.sh`: `ROSTER`, `DISPLAY`, `BACKEND`, `MODEL_TAG_TO_ROSTER` swap `gemma4_31b` → `gemma4_26b-a4b` (with `BACKEND` flipping to `vllm`). Comments updated. `jname_to_cell` docstring drops the Ollama gemma example (kept as a generic legacy-pattern note).
- `.claude/skills/cluster-ops/scripts/prioritize.sh`: `DEFAULT_SLOW_MODELS` swap; usage example refreshed.
- `.claude/skills/analyzer/scripts/plot.py` + `plot_focused.py`: `gemma4_26b-a4b` added to `MODEL_COLORS` (`#9173b0`, a tint of the gemma4_31b purple), `MODEL_ORDER`, and `MODEL_LABELS`. `gemma4_31b` entries retained as drift-anchor support for re-plotting older corpora. Also added missing `Qwen3_5_4B` / `Qwen3_5_9B` color entries (post 2026-05-17 swap had left them as default-color fallbacks).
- `tests/test_scoring.py:335`: determinism-test fixture key swap `gemma4:31b` → `gemma4:26b-a4b`. The pinned bucket regression check uses `Qwen3.5:0.8B`, unaffected.
- `EXPERIMENTS_FLOW.md:504`: roster description updated to the post-swap five-model vLLM-only roster; roster-history narrative gains the 2026-05-18 unification.
- `cluster-experimenting/README.md`: topology table swap (line 14-16) + roster table swap (line 214-220) + verified-parser table swap (line 336) + production-vLLM scope rewrite (line 253-267) + GPU-class section + mem-cap row + `submit_with_resume.sh` description + legacy CG-cancel example. The 2026-05-18 entry in the submission-topology-history list now reads as two same-day events (backend split landed, then retired by the gemma swap).

**Methodology framing.** Treated as plain operational drift (no paper-baseline comparison). The `gemma4:31b` Ollama corpora at `results/slurm_gemma4_31b_*` stay on disk untouched as drift anchors — never mixed with the new `slurm_vllm_gemma4_26b-a4b_*` corpora per the `feedback_pushback_on_methodology_shortcuts.md` corpus-isolation rule. Resume-key isolation is automatic: the 10-tuple at `pddl_eval/runner.py:441–451` includes the model string and OUT_DIR prefix.

**Compatibility / drift framing.** Five-model roster size unchanged; the gemma slot's identity changes from "dense 31B Ollama Q4_K_M" to "MoE 26.5B A4B vLLM AWQ-INT4." Drift expectation: smoke 17638752 already shows tools-cell ToolSel parity with the verified Qwen3.5/3.6 ladder. No-tools think=on truncation rate is high — explicitly an expected pre-rewrite behavior (sweep-4's v5/v6/v7 prompt work).

**Files touched (Phase B).**
- `cluster-experimenting/lib/defaults.sh`
- `cluster-experimenting/run_condition_vllm_rtx.sbatch`
- `cluster-experimenting/run_condition_rtx.sbatch`
- `cluster-experimenting/submit_with_resume.sh`
- `cluster-experimenting/submit_full_sweep.sh`
- `cluster-experimenting/submit_with_rtx.sh`
- `cluster-experimenting/README.md`
- `.claude/skills/cluster-ops/scripts/status.sh`
- `.claude/skills/cluster-ops/scripts/prioritize.sh`
- `.claude/skills/analyzer/scripts/plot.py`
- `.claude/skills/analyzer/scripts/plot_focused.py`
- `tests/test_scoring.py`
- `EXPERIMENTS_FLOW.md`
- `development/CHANGELOG.md` (this entry)

**Reference logs / commits.**
- Smoke 17633538 (MM-tower startup crash): `cluster-experimenting/logs/vllm_gemma4_26b-a4b_smoke-17633538.out`.
- Smoke 17638752 (passed): `cluster-experimenting/logs/vllm_gemma4_26b-a4b_smoke-17638752.out`, results at `results/smoke/probe_vllm_59be812_20260518_222456/gemma4_26b-a4b/summary_20260518_223823.json`.
- Phase-A commits: `7106f68` (vllm_lookup add), `59be812` (MAX_NUM_BATCHED_TOKENS fix).

---

## 2026-05-17 — Plotting: ablation-friendly bar encoding + roster swap (drop 27B, add 4B/9B, flip 35B to vLLM)

**TL;DR.** Two unrelated changes shipped together:
(1) restyle of the analyzer's grouped-bar plots so the three ablation axes — model, thinking on/off, tool exposure — sit on three independent visual channels;
(2) `status.sh` roster realignment to the 2026-05-17 sweep: drop `qwen3.6:27b` (slowest cell, ~19h tools×on), add `Qwen3.5:4B` and `Qwen3.5:9B` to fill the 0.8B → 35B param gap, and flip `qwen3.6:35b`'s canonical backend Ollama → vLLM.

**Plotting — `plot.py` (style change only; numbers bit-identical to prior checkpoint):**
- `.claude/skills/analyzer/scripts/plot.py` — `COND_HATCH` rewritten: `no-tools` → `////` (striped), `tools_per-task_minimal` → `....` (dotted), `tools_all_minimal` → `None` (solid). The retired `tools_*_guided` keys are kept mapped to `None` so re-plotting pre-2026-05 checkpoints still works (mirrors the comment-don't-delete policy in `run_condition_rtx.sbatch`).
- `style()` simplified to a single per-model base color from `MODEL_COLORS` regardless of cond; the `if cond=="no-tools"` branch is removed, and the now-orphaned `MODEL_COLORS_NO_TOOLS` constant + its `plot_focused._color_for` `with_tools=False` branch are deleted (no live caller).
- `THINK_LIGHTEN` semantics unchanged (off=saturated, on=lightened).

**Plotting — `plot_focused.py` (data change, not just style):**
- `fig1` and `fig4` drop their `tools = [r for r in records if r["with_tools_dir"]]` pre-filter and now include a **no-tools bar series alongside the with-tools bars** — `fig1` becomes 4 bars/model (no-tools × {off,on} + with-tools × {off,on}, hatch separates tool exposure), `fig4` becomes 3 bars/model (no-tools / per-task / all). New bars are new data on the plot, not a re-color of existing bars.
- `fig2` swaps from dual color palettes (per-model dark variant for no-tools) to single per-model color + hatch (`////` for no-tools, solid for with-tools), matching the main-plot encoding.
- Output re-renders visible at `checkpoints/cluster-20260517-ablation/`.

**Operations — `status.sh` roster swap:**
- `.claude/skills/cluster-ops/scripts/status.sh` — `ROSTER`, `DISPLAY`, `BACKEND`, `MODEL_TAG_TO_ROSTER` updated to `[Qwen3_5_0_8B, Qwen3_5_4B, Qwen3_5_9B, gemma4_31b, qwen3_6_35b]`. All four dicts list the same 5 keys.
- `qwen3_6_35b` canonical backend flipped `ollama` → `vllm`; the prior Ollama 35B corpus is checkpointed under `checkpoints/cluster-2026{0514,0517}/`. Dirs from the now-non-canonical backend report under "skipped (wrong backend)" rather than polluting the progress matrix.
- `jname_to_cell` / `jname_model` docstring examples refreshed to the new roster.

---

## 2026-05-12 — vLLM: register `qwen3.6:35b` + per-cell-class `--time` override + full-sweep orchestrator

**TL;DR.** Three operations-side changes consolidate the 4-model production sweep into a single dispatch:
(1) `qwen3.6:35b` joins the verified vLLM roster after a parser smoke;
(2) `submit_with_rtx.sh` gains a `--time` CLI flag so heavy Qwen cells (27B/35B) don't TIMEOUT under the hardcoded 06:00:00 vLLM tools ceiling;
(3) `cluster-experimenting/submit_full_sweep.sh` (new orchestrator) emits three sbatch submissions — the three vLLM Qwens on `rtx_6000:1` and `gemma4:31b` on `rtx_pro_6000:1` via Ollama — each on the GPU class and walltime that fits. No methodology change: identical `CELLS_LIST` builder, identical `OUT_DIR` resolution, identical `vllm_lookup` contract.

**Smoke.** `run_smoke_vllm_vs_ollama.sbatch` job 17494176 (2026-05-12, `rtx_6000:1`, vLLM 0.20.2, `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`, 10:02 wall): zero parser-extraction failures across the full tools × no-tools × 5-task matrix. The 2-3 `verdict_mismatch` records under `validate_problem` are model behaviour, not parser errors. First attempt 17494173 ENOSPC'd at 2s on `ise-cpu256-27` (`/scratch` full); resubmit with `--exclude=ise-cpu256-27` landed on `cs-6000-02`. The smoke sbatch's `/scratch` setup still lacks the ENOSPC-safe fallback that the 2026-05-11 entry added to `run_condition_vllm_rtx.sbatch`; out-of-scope for this commit but worth porting later.

**Why `--time` and not a tighter default.** The wrapper's 06:00:00 vLLM tools ceiling was locked by `vllm-production-plan.md` 2026-05-09 with the 27B AWQ in mind, where it was tight but adequate. Production-scale 27B/35B tools cells extrapolate to ~19h. Encoding model→walltime inside `vllm_lookup` would conflate "verified parser table" with "scheduling policy" — the override flag is the conservative split.

**Why an orchestrator and not just two commands.** `submit_with_rtx.sh` accepts one `--backend` per invocation, so a single command can't mix vLLM + Ollama. The orchestrator wraps three calls, rejects flags it owns (`--backend`, `--gpu-type`, `--time`, `--all`, `--smoke*`) up front so the operator can't accidentally pin all three submissions to one backend, and forwards everything else (`--no-tools`, `--think-modes`, `--dry-run`) to all three. ~30 LOC of real logic; no duplication of cell-builder, sbatch composition, manifest writing, or auto-prioritize.

**Prefix-caching probes (closed as docs-only).** Same-day probes verified that `--enable-prefix-caching` is inert on Qwen3.x cells (Mamba 784-tok block override → cumulative block hash diverges at byte 0 of every distinct prompt) and effective on a non-Mamba Gemma4 variant (93% hit rate on byte-identical replay). vLLM 0.20.2 V1 also doesn't populate `usage.prompt_tokens_details.cached_tokens` (vllm-project/vllm#16162). The flag is left on in `run_condition_vllm_rtx.sbatch` — inert but harmless beyond a cosmetic "Mamba cache 'align' mode is experimental" warning — and PR #61 (per-model conditional) was closed as no-op. Finding preserved in personal memory; revisit when a non-Mamba model joins `vllm_lookup`. Probe sbatches were drafted on the closed branch and are recoverable via `git show 38821bc -- 'cluster-experimenting/run_smoke_prefix_cache_probe*'` if needed.

**What changed.**

- `cluster-experimenting/lib/defaults.sh`: `qwen3.6:35b` added to `PDDL_VLLM_VERIFIED_MODELS` and `vllm_lookup` (HF id `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`, parsers `qwen3_xml` + `qwen3`).
- `cluster-experimenting/submit_with_rtx.sh`: new `--time HH:MM:SS` (or `D-HH:MM:SS`) CLI flag overrides the auto-computed `TIME_ARG`. Auto defaults unchanged for callers that don't pass `--time`.
- `cluster-experimenting/submit_full_sweep.sh`: new orchestrator. Three independent sbatch submissions — vLLM `rtx_6000:1` 06:00:00 for `Qwen3.5:0.8B`, vLLM `rtx_6000:1` 48:00:00 for `qwen3.6:27b` + `qwen3.6:35b` (packed array), Ollama `rtx_pro_6000:1` 72:00:00 for `gemma4:31b`.

---

## 2026-05-11 — vLLM sbatch: `--constraint=rtx_6000` + ENOSPC fallback for `/scratch`

**TL;DR.** Sweep 17480288 broke in two distinct ways. Both were SLURM/node-side conditions that slipped past the existing sbatch gates; fixes are surgical and local to `cluster-experimenting/run_condition_vllm_rtx.sbatch`. No changes to `pddl_eval/`, no response-shape changes, no fresh `slurm_vllm_*` corpus namespace required. Full evidence in `development/INVESTIGATION_vllm_oom_thinkon_20260511.md`.

**Failure mode 1 — qwen3.6:27b OOM on L40S nodes (3 cells: `17480288_{2,3,4}`).** SLURM's `gpu:rtx_6000` GRES label is shared by two physical GPU classes at BGU CIS: real RTX 6000 Ada (48 GiB visible) and L40S (44.39 GiB visible, on `ee-l40s-{01,02}`). The recently pinned `--enable-prefix-caching` + `gpu_memory_utilization=0.85` budget needs the full 48 GiB for 27B; the 3.6 GiB delta on L40S OOMs at `_initialize_kv_caches`. `sinfo -h -N -o '%N %f %G'` confirms real rtx_6000 nodes carry feature `rtx_6000` while both L40S nodes carry feature `l40s`, so `--constraint=rtx_6000` is a clean, future-proof filter.

**Fix 1.** `#SBATCH --constraint=rtx_6000` added to `run_condition_vllm_rtx.sbatch` header. Filters out `ee-l40s-{01,02}` AND any future GPU class that gets a `gpu:rtx_6000:N` GRES mislabel without the matching feature flag.

**Failure mode 2 — `/scratch` exhaustion on `ise-cpu256-27` (2 cells: `17480288_{6,9}`, both Qwen3.5:0.8B `tools_all_minimal`).** Original handoff hypothesised a Qwen3.5 chat-template kwarg rejection (`enable_thinking=true`). **Falsified by primary-source evidence** in the .out files: verbatim error is `mkdir: cannot create directory '/scratch/omereliy/<JOBID>/vllm-work': No space left on device` — bash mkdir failing on ENOSPC, not a Python or vLLM error. The pre-existing scratch-fallback branch never engaged because `mkdir -p "$SCRATCH_BASE"` returned 0 (directory entry fits) even though the deeper `mkdir -p "$WORK/hf-cache"` then failed with ENOSPC; `set -eo pipefail` aborted at 2s before the trap fired. The hypothesis is additionally falsified by IDX=5 (Qwen3.5 on/tools_per-task) running 25:56 fine on `ee-l40s-02` before being operator-cancelled — if `enable_thinking=true` were rejected, IDX=5 would have failed identically.

**Fix 2.** Atomicized the `/scratch` writability test in `run_condition_vllm_rtx.sbatch`: try `mkdir -p "$SCRATCH_BASE/vllm-work/hf-cache"` (full target path) in one shot; fall back to `/tmp` if ANY step fails (including ENOSPC at deeper levels). `pddl_eval/vllm_client.py` is **NOT** touched — the harness was never wrong; the bug was bash short-circuiting before the harness loaded.

**Why no node exclusion.** `ise-cpu256-27`'s `/scratch` exhaustion is a transient operator-side condition (likely a leak from a prior job's epilog). Permanent exclusion is overkill; graceful `/tmp` fallback handles both this incident and any future recurrence on any node.

**Smoke-test posture.** The mode-2 fix's smoke run validates "no regression on a healthy `/scratch`-available node" — it does NOT reproduce the original ENOSPC condition (that requires the node-side state). The mode-1 smoke run requires landing on a real rtx_6000 node, which the new constraint enforces, so its smoke directly verifies the fix path.

**What changed.**

- `cluster-experimenting/run_condition_vllm_rtx.sbatch`: `#SBATCH --constraint=rtx_6000` added (failure mode 1); `/scratch` workspace block atomicized with ENOSPC-safe fallback to `/tmp` (failure mode 2).
- `development/INVESTIGATION_vllm_oom_thinkon_20260511.md`: "Failure mode 2" section rewritten with the verbatim `mkdir` error from the .out files and the falsification of the original chat-template hypothesis; "Failure mode 1" updated with the live `sinfo` evidence and the chosen `--constraint=rtx_6000` fix; open-questions list resolved where applicable.

---

## 2026-05-11 — vLLM context-overflow retry: bump `_CTX_RETRY_SAFETY` 8 → 32

**TL;DR.** The earlier vLLM context-overflow retry patch (CHANGELOG 2026-05-11 entry below) caught the first 400 and retried with a clipped `max_tokens`, but the retry was *also* 400'ing at a non-trivial rate on the 17478753 sweep (qwen3.6:27b 2.8% of trials, Qwen3.5:0.8B `on/tools_*` 7–11%, `off/no-tools` 0%). Forensic count over 374 retry failures showed an exact and consistent **+9-token delta** between the prompt-token count reported in the attempt-1 error body and the prompt-token count reported in the attempt-2 error body, leaving `new_max + new_prompt = max_model_len + 1` every single time. Root cause: vLLM's 400 error message reports `"prompt contains at least N input tokens"` — `N` is a LOWER bound. The pre-flight check fires before final template additions (generation prefix, BOS, prefix-caching block-padding) are appended, and the real served prompt is consistently higher than the reported `N`. The original `_CTX_RETRY_SAFETY = 8` was undersized by exactly 1 token relative to that +9 drift.

**Fix.** `_CTX_RETRY_SAFETY` bumped 8 → 32. Absorbs the observed +9 with ~3× headroom for future vLLM versions / different chat templates. Output-budget cost is < 0.4% of the 8192-token `solve` cap, negligible. Comment in `pddl_eval/vllm_client.py` rewritten with the empirical evidence so the next maintainer doesn't have to re-derive the +9 figure from `trials.jsonl`.

**Methodology stance.** The previous 374 retry-failure trials are now permanently in `slurm_vllm_*/trials.jsonl` as `exception` rows on the 17478753 sweep. With the safety bump applied via a fresh resubmit, ≥99% of future overflow trials will instead land as `done_reason="length"` truncations (Ollama-parity bucket). Whether to cancel + clean + resubmit again, or let 17478753 finish and tolerate the ~7% exception contamination in the affected 0.8B cells, is a sweep-level decision tracked outside this entry.

**Why not a retry loop instead of bumping safety.** A retry loop only converges if the +9 drift dampens after the first retry. Empirically the drift is constant across attempts (vLLM's `"at least N"` is the *same* low-bound formula on every error), so a naive loop would diverge — each retry would 400 by the same +1 margin until max retries was hit, then bubble. Bumping safety to absorb the constant drift in one retry is the closed-form fix.

**What changed.**

- `pddl_eval/vllm_client.py`. `_CTX_RETRY_SAFETY` 8 → 32 and updated docstring comment.

---

## 2026-05-11 — vLLM smoke scripts: parameterize `--reasoning-parser`

**TL;DR.** Both vLLM smoke sbatch scripts (`run_smoke_vllm_vs_ollama.sbatch`, `run_smoke_vllm_concurrency_probe.sbatch`) hardcoded `--reasoning-parser qwen3`, even though `TOOL_CALL_PARSER` was already overridable. The gemma4:31b smoke (job 17468317) inherited that hardcoded flag and vLLM crashed at startup with `Qwen3ReasoningParser reasoning parser could not locate think start/end tokens in the tokenizer!` — Gemma's tokenizer has no `<think>` tokens. Now `REASONING_PARSER` is an env var (default `qwen3` to preserve verified Qwen3.x behaviour); pass `REASONING_PARSER=none` to omit the flag for families without a reasoning trace. No methodology change — verified Qwen3.x probes get the same flags as before. Header comment in `run_smoke_vllm_vs_ollama.sbatch` gains an explicit Gemma-4 submit example.

**Why this slipped past.** The production sbatch (`run_condition_vllm_rtx.sbatch:196`) already takes `$REASONING_PARSER` from `vllm_lookup()` (sourced from `lib/defaults.sh`). The smoke scripts were written before that lookup existed and never got back-fixed when `TOOL_CALL_PARSER` was parameterized in commit f79fa46. Gemma-4 is the first non-Qwen family probed since, which is when the gap surfaced.

**What changed.**

- `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`. New `REASONING_PARSER` env var (default `qwen3`). Builds `REASONING_PARSER_FLAG`, empty when value is `none` or empty. Apptainer command drops the hardcoded literal in favour of the flag var. Header gains a Gemma-4 override example alongside the existing 0.8B one.
- `cluster-experimenting/run_smoke_vllm_concurrency_probe.sbatch`. Same env-var + flag-builder pattern.

**Reference logs.** `cluster-experimenting/logs/427849349/17468317-vllm-gemma4_31b.log` (vLLM startup traceback) and `cluster-experimenting/logs/84560442/vllm_gemma4_31b_smoke-17468317.out` (preserved tail in the sbatch out file).

---

## 2026-05-11 — vLLM client catches context-overflow 400 and retries with clipped max_tokens

**TL;DR.** vLLM's OpenAI server strictly rejects `prompt_tokens + max_tokens > max_model_len` with HTTP 400 BadRequestError before any generation, where Ollama silently truncates from the front (or returns `done_reason="length"`) on the same overflow. The first in-flight vLLM qwen3.6:27b production sweep (array `17478276`) hit this on `tools_all × on × solve` trials at ~55% rate — multi-turn tool replay accumulated past the `16384 − 8192 = 8192` input budget. Those exceptions are NOT comparable to Ollama's silent-truncation behaviour on the same overflow, so they contaminated the failure-mode breakdown. `pddl_eval/vllm_client.py::VLLMOllamaClient.chat()` now catches the specific overflow body, parses `(max_model_len, prompt_tokens)` from it, clips `max_tokens = max_model_len − prompt_tokens − 8` (safety margin), and retries on the same connection. Restores response-shape parity with the Ollama corpus. The degenerate prompt ≥ max_model_len case (no output budget left) returns a synthetic Ollama-shaped response with `done_reason="length"` and empty content, mirroring how Ollama would treat a num_ctx fully consumed by the prompt.

**Sweep impact.** The 5 in-flight qwen3.6:27b vLLM array tasks (`17478276_{0..4}`) were scancelled and their 4 partial result dirs (`results/slurm_vllm_qwen3_6_27b_*`, 266 trials total) removed from the cluster before this patch landed — mid-sweep behaviour shifts violate the corpus-identity rule. Resubmit happens against this branch. The 0.8B vLLM array tasks (`17478276_{5..9}`) were left running; the 0.8B model rarely if ever hits the overflow (no multi-turn accumulation past 8K tokens in the cells observed so far), so cancelling them would have been more wasteful than the marginal corpus-mix risk.

**Why catch+retry rather than pre-flight tokenize.** Reactive is simpler — the BadRequestError body already reports `prompt_tokens`, so no extra tokenize round-trip is needed on the (vast majority) happy path. Cost: overflow trials pay one wasted round-trip + queue delay before the retry. vLLM `total_duration` is already wallclock-synthesised (not server-reported decode-only), so the inflation falls inside an already-lossy field; the per-trial wall comparison vs Ollama remains a fair upper bound.

**Why not raise `--max-model-len`.** Two reasons: (1) 27B AWQ peaked at 83% VRAM on rtx_6000:1 at 16384 ctx; 24576 likely won't fit, forcing rtx_pro_6000:1 + queue pressure. (2) Diverges from the Ollama corpus that ran at `num_ctx=16384`, breaking the like-for-like comparison the `slurm_vllm_` namespace was set up for.

**What changed.**

- `pddl_eval/vllm_client.py`. New `_CTX_OVERFLOW_RE` regex + `_CTX_RETRY_SAFETY` constant. `chat()` wraps `chat.completions.create` in try/except over `openai.BadRequestError`; only matches on the specific overflow body (other 400s — e.g. malformed `tool_choice` — propagate untouched). New helpers `_parse_ctx_overflow` and `_synthesize_overflow_response`. Module docstring updated.

---

## 2026-05-11 — vLLM production sbatch + submit-with-resume wrapper (PR #58)

**TL;DR.** Land a vLLM production sbatch (`run_condition_vllm_rtx.sbatch`) and a `--backend vllm` flag on `submit_with_rtx.sh`. Partial migration: `qwen3.6:27b` + `Qwen3.5:0.8B` move to vLLM; `gemma4:31b` + `qwen3.6:35b` stay on Ollama to preserve ~36K already-complete trials. New `submit_with_resume.sh` sequences both backends. No methodology change. vLLM cells write to `results/slurm_vllm_<canonical>_<think>_<cond>/` — the prefix isolates corpora because the 10-tuple resume key in `pddl_eval/runner.py:424` includes the model string (Ollama `qwen3.6:27b` vs vLLM `cyankiwi/Qwen3.6-27B-AWQ-INT4` would silently mismatch on resume). Operator-facing details + verified serve command + scope-split rationale + parser table live in `cluster-experimenting/README.md` "Production vLLM sweep"; this entry is the diff-of-record.

**Files.**

- `cluster-experimenting/lib/defaults.sh` — `PDDL_VLLM_VERIFIED_MODELS=(qwen3.6:27b Qwen3.5:0.8B)` + `vllm_lookup()` (canonical Ollama tag → HF id + parser flags).
- `cluster-experimenting/run_condition_vllm_rtx.sbatch` (new) — vLLM analog of `run_condition_rtx.sbatch`. Same cell-array picker, scratch, VRAM-85% guard, `preserve_serve_logs` trap. Calls `vllm_lookup`. OUT_DIR prefixed `slurm_vllm_`.
- `cluster-experimenting/submit_with_rtx.sh` — `--backend ollama|vllm` (default ollama). Backend-specific GPU/mem/time defaults; vLLM gate calls `vllm_lookup` to reject unverified models. Job name suffixed `_vllm`.
- `cluster-experimenting/submit_with_resume.sh` (new) — sequences Ollama submission for the residual models and vLLM submission for `PDDL_VLLM_VERIFIED_MODELS`.
- `.claude/skills/analyzer/scripts/{aggregate,plot,drift_check}.py` — `parse_dirname` strips `slurm_vllm_` prefix + adds `backend` field; `drift_check._load_root` keys on `(model, think, cond, backend)`; drift table grows a `backend` column.
- `cluster-experimenting/README.md` — new "Production vLLM sweep" section.

**Open / pending.**

1. Pilot one vLLM cell + verify `meta.inference_backend == "vllm"` before fanning out.
2. `gemma4:31b` parser verification.
3. Analyzer cross-backend pivot (both prefixes).
4. Concurrency saturation probe (c=4/8/16, unrun).

**Reproducibility.** Existing Ollama corpora unchanged. vLLM cells write to a non-overlapping namespace. `meta.inference_backend` disambiguates aggregation.

---

## 2026-05-11 — PR #58 cleanup: shell de-duplication + doc trim

**TL;DR.** Pure-refactor follow-up to the four 2026-05-11 vLLM commits. No behavior change. Three reductions: (1) `submit_with_rtx.sh` drops the inline substring-match verified-models gate and calls `vllm_lookup` directly (single source of truth already in `lib/defaults.sh`); the dual `SBATCH_OLLAMA`/`SBATCH_VLLM` vars collapse into one `case`. (2) Both smoke sbatches stop duplicating the 4-line `REASONING_PARSER_FLAG` builder — new `vllm_reasoning_parser_flag()` helper in `lib/defaults.sh` is the single emitter. (3) Header comments on `run_condition_vllm_rtx.sbatch` and `submit_with_resume.sh` trimmed; the verbatim serve-command copy + scope-split prose live only in the README + the entry above. `pddl_eval/vllm_client.py:_CTX_RETRY_SAFETY` gains a one-line justification.

**Files.** `cluster-experimenting/lib/defaults.sh`, `cluster-experimenting/submit_with_rtx.sh`, `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`, `cluster-experimenting/run_smoke_vllm_concurrency_probe.sbatch`, `cluster-experimenting/run_condition_vllm_rtx.sbatch`, `cluster-experimenting/submit_with_resume.sh`, `pddl_eval/vllm_client.py`, `development/CHANGELOG.md`.

---

## 2026-05-10 — vLLM tool-call parser fix + smoke decision-gate PASS

**TL;DR.** The Qwen3.5/3.6 family emits tool calls in **Llama-3 XML** format
(`<tool_call><function=NAME><parameter=KEY>VAL</parameter></function></tool_call>`),
not Hermes JSON. The 2026-05-09 smoke sbatch picked `--tool-call-parser hermes`,
which silently dropped every tools-trial extraction (`tool_calls=[]` → harness
short-circuits `FR_TOOL_NOT_SELECTED` at `pddl_eval/scoring.py:351`). Original
27B AWQ probe (job 17453988 on rtx_3090) showed 0/40 tools cells extracted;
post-fix 27B AWQ probe (job 17461801 on rtx_6000:1) shows **40/40 tools cells
extracted, 100% tool-selection across all 5 tasks, ~0.22× the matching Ollama
walltime — decision gate clears, migrate-go.**

Also: parameterized `TOOL_CALL_PARSER` as a sbatch env var so per-model
overrides are one flag away.

**Smoke results (apples-to-apples; blocksworld/p01, n=80 trials, c=4).**

| metric                  | vLLM 27B AWQ-INT4 (rtx_6000:1, qwen3_xml) | Ollama qwen3.6:27b (cs-6000-01, Q4_K_M) |
| ----------------------- | ----------------------------------------- | --------------------------------------- |
| tools trials extracted  | 40/40 (100%)                              | 40/40 (100%)                            |
| tools success           | 40/40 (100%)                              | 40/40 (100%)                            |
| no-tools success        | 35/40 (88%)                               | 33/40 (82%)                             |
| sum trial duration      | 3,189 s                                   | 14,604 s                                |
| reported wall (vLLM log)| 888.7 s                                   | n/a                                     |
| effective speedup       | **~4.6×**                                 | —                                       |

**Decision rule (from `run_smoke_vllm_vs_ollama.sbatch` header).** vLLM wall
≤ 0.7× Ollama wall on `qwen3.6:27b tools×off` cell AND per-cell pass rates
within parity. Both bars cleared.

**Per-model parser mapping (canonical reference; mirrored in `cluster-experimenting/README.md`).**

| Ollama tag       | HF id                                      | Quant                | TOOL_CALL_PARSER | GPU class                   | Status         |
| ---------------- | ------------------------------------------ | -------------------- | ---------------- | --------------------------- | -------------- |
| `Qwen3.5:0.8B`   | `Qwen/Qwen3.5-0.8B`                        | BF16                 | `qwen3_xml`      | rtx_3090:1                  | Pending verify |
| `qwen3.6:27b`    | `cyankiwi/Qwen3.6-27B-AWQ-INT4`            | AWQ-4bit             | `qwen3_xml`      | rtx_6000:1 / rtx_pro_6000:1 | **Verified**   |
| `qwen3.6:35b`    | `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`        | AWQ-4bit MoE         | `qwen3_xml`      | rtx_6000:1                  | Pending verify |
| `gemma4:31b`     | `cyankiwi/gemma-4-31B-it-AWQ-4bit`         | AWQ-4bit             | `gemma4`         | rtx_6000:1                  | Pending verify |
| `Qwen/Qwen3-0.6B` (vanilla) | `Qwen/Qwen3-0.6B`              | BF16                 | `hermes`         | any                         | Verified (smoke 17461442 confirmed Hermes JSON-in-XML emit format; parity-anti-example for Qwen3.5/3.6) |

The empirical signal that distinguishes the two Qwen formats: dump
`results/.../trials.jsonl[*].response` for any tools-trial. If the body
is `<tool_call>{"name":..., "arguments":{...}}</tool_call>` → use `hermes`.
If the body is `<tool_call><function=NAME><parameter=KEY>VAL</parameter>
</function></tool_call>` → use `qwen3_xml`. There is no in-band autodetect.

**Operational caveats (cluster).**

- `~/vllm.sif` may predate parser additions. If `vllm-serve` rejects
  `--tool-call-parser <name>` at startup with "unknown tool-call-parser",
  `rm ~/vllm.sif` and resubmit; the next run rebuilds from
  `docker://vllm/vllm-openai:latest`.
- vLLM enforces `max_tokens ≤ max_model_len` (HTTP 400 otherwise). When
  using `MAX_MODEL_LEN < 8192`, set `NUM_PREDICT=4096` via
  `--export=ALL,NUM_PREDICT=4096`. Harness per-task defaults are
  `solve=8192`, `validate_*=6144`, `simulate=6144`.
- Tight-VRAM recipe (rtx_3090 24 GB serving 27B AWQ): `MAX_MODEL_LEN=7168
  GPU_MEM_UTIL=0.85 ENFORCE_EAGER=1 NUM_PREDICT=4096`. The eager flag
  skips CUDA graph profiling (~1.5 GiB headroom) at ~10–15% throughput cost.

**What changed.**

- `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`: `--tool-call-parser
  hermes` → `qwen3_xml` (commit `f563ce3`); then parameterized as
  `TOOL_CALL_PARSER` env var (this commit).
- `notebooks/run_vllm_vs_ollama_smoke.ipynb`: retargeted at parser
  verification — tools-only scope, headline metric is tool-extraction
  rate, sbatch knob parity (commit `ca7a307`).
- `cluster-experimenting/README.md`: new "vLLM smoke probes (parser
  verification)" section with per-model table, submit recipes, and
  operational caveats.

**What did NOT change.**

- `pddl_eval/{vllm_client,scoring,...}.py`, `domains/`, `EXPERIMENTS_FLOW.md`,
  `tests/` — methodology, fixtures, scoring unchanged. The fix is purely
  vLLM-serve flag wiring.
- Production sweep `run_condition_rtx.sbatch` is untouched. Ollama remains
  the sole production backend until the vLLM full-sweep sbatch lands.
- Existing `results/` corpora — no schema change.

**Open / pending (closing the migration).**

1. Parser-verification smokes for `Qwen3.5:0.8B`, `qwen3.6:35b`, `gemma4:31b`
   (queued today on rtx_3090:1 / rtx_6000:1 with 1-hour walltime). Expected
   outcome: `qwen3_xml` clean for the two Qwen entries; `gemma4` clean for
   the Gemma entry. Failure modes are debuggable from
   `trials.jsonl[*].response` per the recipe above.
2. Full-sweep vLLM sbatch — vLLM analog of `run_condition_rtx.sbatch` with
   per-model parser flag + per-model HF-id mapping (probably a new
   `cluster-experimenting/lib/defaults_vllm.sh` table). Blocked on (1).
3. Cross-backend analyzer pivot (per-model walltime + tool-extraction
   parity rollup). Blocked on (2).

**Files.** `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`,
`cluster-experimenting/README.md`, `development/CHANGELOG.md`,
`notebooks/run_vllm_vs_ollama_smoke.ipynb`.

---

## 2026-05-09 — vLLM inference-backend smoke probe

**TL;DR.** Adds an opt-in `--inference-backend vllm` path that points the existing harness at vLLM's OpenAI-compatible `/v1/chat/completions` endpoint via a thin adapter (`pddl_eval/vllm_client.py`). Default is unchanged (`ollama`). New cluster sbatch `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch` runs the existing `--smoke` matrix on both backends sequentially on one `rtx_pro_6000:1` node and writes analyzer-readable summaries under `results/smoke/probe_{ollama,vllm}_<sha>_<ts>/`. **No methodology change** — same prompts, fixtures, tools, scoring, num_ctx, num_predict; production sweep (`run_condition_rtx.sbatch`) untouched. Existing results in `results/` remain valid.

**Motivation.** The 27B Ollama cells in the 2026-04-30 sweep ran 57–107 s/trial × 4560 trials = 72–135 h per cell. vLLM's continuous-batching could compress that, but only if real tool-calling and thinking-mode plumbing survive the wire-format swap. A 2-hour smoke that exercises the full 2 (think) × 2 (cond) × 5 (task) × 2 (model) matrix on both backends gates the migration on both wall-time AND tool-call pass-rate parity — pure tok/s benchmarks would miss a Hermes-parser misfire that silently drops to 0% tool use.

**Decision rule.** Migrate only if vLLM wall ≤ 0.7× Ollama wall on the `qwen3.6:27b tools×off` cell **and** per-cell pass rates are within parity. Below either bar, stay on Ollama.

**What changed (`feat/vllm-smoke-probe` branch).**

- **`pddl_eval/vllm_client.py`** (new). `VLLMOllamaClient` exposes the `chat()` / `aclose()` shape `run_experiment.py` calls on `ollama.AsyncClient`. Returns Ollama-shaped response dicts so `pddl_eval/chat.py` (`chat_with_tools`, `chat_without_tools`) and downstream scoring work without edits. Translations: `tool_calls[].function.arguments` JSON-string ↔ dict; `message.reasoning_content` → `message.thinking` (vLLM `--reasoning-parser qwen3`); `finish_reason` → `done_reason`; `usage.{prompt,completion}_tokens` → `prompt_eval_count`/`eval_count`; `total_duration` synthesised from `time.perf_counter_ns`. Multi-turn tool replay re-attaches synthetic `tool_call_id`s in FIFO order so vLLM's OpenAI server accepts the harness's id-less tool messages. Streaming is forced off (sidesteps vllm-project/vllm#31871 Qwen3-hermes streaming bug).
- **`run_experiment.py`**. Adds `--inference-backend {ollama,vllm}` (default `ollama`); branches the client construction. Banner prints the selected backend. `--ollama-host` help updated to "LLM server base URL".
- **`requirements.txt`**. Adds `openai>=1.40.0` for the OpenAI-compatible client.
- **`cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch`** (new). Single sbatch on `rtx_pro_6000:1`, `--mem=80G`, `--time=02:30:00`. Phase A: builds/uses cached `ollama.sif`, runs `--smoke` per model. Phase B: builds/uses cached `vllm.sif` (from `docker://vllm/vllm-openai:latest`), serves each HF model on a fresh port with `--enable-auto-tool-choice --tool-call-parser hermes --reasoning-parser qwen3 --gpu-memory-utilization 0.85`, runs `--smoke --inference-backend vllm`. 27B served from `cyankiwi/Qwen3.6-27B-AWQ-INT4` (`--quantization awq`) — the closest apples-to-apples to Ollama's Q4_K_M (~17 GB on disk for both); 0.8B from `Qwen/Qwen3.5-0.8B` BF16. Both phases write to `results/smoke/probe_{ollama,vllm}_<sha>_<ts>/<model_tag>/`.

**What did NOT change.**

- `pddl_eval/{chat,runner,scoring,domains,prompts,resume,schemas,summary}.py` — adapter returns Ollama-shaped objects so the chat loop and tool-call extraction work unchanged.
- `cluster-experimenting/run_condition_rtx.sbatch`, `submit_with_rtx.sh`, `lib/defaults.sh` — production sweep path is untouched. The smoke sbatch is independent.
- `domains/`, `tests/`, `EXPERIMENTS_FLOW.md` — methodology, fixtures, and the experiment-flow spec are unchanged.
- Existing `results/` corpora — no schema change.

**Compatibility.** `--inference-backend` defaults to `ollama`; existing scripts and analysis pipelines see identical behaviour. The vLLM path requires `openai>=1.40.0` to be installed (`requirements.txt` updated); environments that haven't `pip install -r requirements.txt`-d will only fail when `--inference-backend vllm` is actually requested.

**Open / pending.** No analyzer change yet — the smoke results land in the existing summary shape, comparison is by hand for now. If the smoke clears the 0.7× wall + parity gate, follow-ups would be: full-sweep cluster sbatch fork (vLLM analog of `run_condition_rtx.sbatch`), tool-call parity audit, and analyzer cross-backend pivot.

**Files.** `pddl_eval/vllm_client.py` (new), `run_experiment.py`, `requirements.txt`, `cluster-experimenting/run_smoke_vllm_vs_ollama.sbatch` (new), `development/CHANGELOG.md`.

---

## 2026-05-07 — Add Colab/Kaggle single-model notebook driver

**TL;DR.** New `notebooks/run_single_model.ipynb` drives `run_experiment.py` for one model on a free-tier T4 (Colab or Kaggle, auto-detected). Persists results + run log to Google Drive (Colab) or `/kaggle/working/` (Kaggle). Pure driver — **no methodology, scoring, prompt, or schema change**; existing `results/` corpora and the analyzer skill remain valid.

**Motivation.** Lower-friction path for collaborators / readers without laptop GPU access; complements the laptop driver (`run_background.sh`) and cluster driver (`cluster-experimenting/`).

**Files.** `notebooks/run_single_model.ipynb` (new), `README.md` (one-line pointer under quick-nav).

---

## 2026-05-07 — Revert Vast.ai remote-Ollama path

**TL;DR.** Reverts the 2026-05-06 entry below. The Vast.ai pool transport (`cluster-experimenting/vast/`, `run_condition_remote.sbatch`, `submit_with_remote.sh`) and its hooks in `run_experiment.py` (`OLLAMA_AUTH_TOKEN` bearer + `verify=False`) and `pddl_eval/chat.py` (MCP env scrub) are removed. The rtx self-deploy (`run_condition_rtx.sbatch`, `submit_with_rtx.sh`) is again the sole cluster transport. **No methodology or result-schema change** — the reverted hooks were env-gated and inactive on the rtx and laptop paths; no canonical results came from the Vast path.

**Motivation.** The Vast pool didn't perform reliably enough to be worth carrying as a parallel transport.

**Files.** Removed `cluster-experimenting/vast/` (all contents), `cluster-experimenting/{run_condition_remote.sbatch,submit_with_remote.sh}`. Reverted `run_experiment.py`, `pddl_eval/chat.py`, `EXPERIMENTS_FLOW.md` to their pre-2026-05-06 shape.

---

## 2026-05-06 — Vast.ai remote-Ollama path (REVERTED 2026-05-07)

Added a parallel cluster transport that offloaded Ollama serving to a pool of Vast.ai GPU boxes behind Caddy + a bearer token, so cluster jobs scheduled on the `main` partition without competing for `rtx_pro_6000`. New files: `cluster-experimenting/vast/{deploy-ollama.sh,Caddyfile.tmpl,preload-model.sh,smoke-test.sh,teardown-pool.sh,README.md,.gitignore}`, `cluster-experimenting/{run_condition_remote.sbatch,submit_with_remote.sh}`. Hooks added to `run_experiment.py` (`OLLAMA_AUTH_TOKEN` → `Authorization: Bearer …` + `verify=False` for Caddy `tls internal`) and `pddl_eval/chat.py` (strip the bearer from MCP subprocess env). The rtx self-deploy was untouched and remained the default. **No methodology change** at the time. Reverted on 2026-05-07 due to unreliable performance — see entry above. Retained here for traceability.

---

## 2026-05-05 — Archive multi-task chain phase from active flow

**TL;DR.** The chain phase (random-length task sequences, all-or-nothing scoring) is dropped from `run_experiment.py`'s dispatch, the cluster + laptop drivers, the analyzer (aggregate / plot / table / focused), and `cluster-ops/status.sh`. The implementation in `pddl_eval/runner.py::run_chain_experiment` and the helpers in `pddl_eval/summary.py::{summarize_chains, print_chain_table}` are **preserved verbatim** as dead-but-importable code, marked with one-line `# Archived 2026-05-05` headers. `summary_*.json` continues to emit `"chains": []` so downstream notebooks reading both pre- and post-archive corpora don't branch. The CLI flags `--chains`, `--chain-samples`, and `--num-ctx-chain` are removed (no deprecation shim; old shell snippets fail loudly). **No methodology change for single-task** — scoring, prompts, fixtures, num_ctx, num_predict, ground truth all unchanged.

**Motivation.** The paper's first-layer findings (Paper 1 in the two-paper plan, see `project_paper_strategy.md` memory) are tools-vs-no-PDDL-tools comparisons on the 5 single-task evaluations. The chain phase was a multi-task layer on top, useful for second-layer claims about agentic behaviour but adding compute cost (chain cells extend wall by ~30-50% on tools cells) without contributing to the active write-up. Keeping the chain code wired created a pull on every documentation edit and analysis script — every SKILL.md mentioned chains, every plot file had chain branches, every status table had a chain column. Archiving the dispatch removes that maintenance pull while keeping the implementation reachable for any future revival.

**What changed (`feat/archive-chain-experiment` branch).**

- **`run_experiment.py`** — drops `run_chain_experiment` / `DEFAULT_NUM_CTX_CHAIN` / `print_chain_table` / `summarize_chains` from imports; removes `--chains`, `--chain-samples`, `--num-ctx-chain` argparse entries; deletes the chain dispatch block (the gate "skip chain phase when sharding to non-zero shard / when `--chain-samples=0` / when `--think=off`" is moot once the flag is gone); drops `args.chain_samples=0; args.chains=False` from the smoke override; removes `num_ctx_chain` from the run banner and `meta`; passes a literal `[]` as the second arg of `save_results`. `--seed` help text updated to point at `--smoke-shuffle` only. Smoke and shard help text trimmed of chain references. The example in the module docstring drops the `--chains` line.
- **`pddl_eval/runner.py`** — single-line `# Archived 2026-05-05` markers above `DEFAULT_NUM_CTX_CHAIN` and `run_chain_experiment`. Function body unchanged so a future re-wiring needs only to re-add the dispatch in `run_experiment.async_main`.
- **`pddl_eval/summary.py`** — module docstring updated to reflect that the active flow always passes `chains=[]`; archive marker above `summarize_chains` / `print_chain_table`. The chain branch in `save_results` (writes `chain_*.json` when called with a non-empty list) is preserved untouched.
- **`run_background.sh`** — removes `SKIP_CHAINS`, `CHAIN_ARGS`, `CHAIN_ECHO`; drops `${CHAIN_ARGS[*]}` from both `python3 run_experiment.py` invocations; drops the `Chains:` line from the startup echo; drops the `partial`-mode chain-skip branch (now redundant).
- **`cluster-experimenting/run_condition_rtx.sbatch`** — drops `CHAIN_SAMPLES` env default; removes `CHAINS_ARGS=(--chains --chain-samples ...)` line and the no-tools `CHAINS_ARGS=()` override; removes `${CHAINS_ARGS[@]}` from the python invocation. Header comments rewritten to drop the `num_ctx_chain` justification.
- **`cluster-experimenting/submit_with_rtx.sh`** — removes chain references from the help comments (`--all` cell counts, no-tools mode description, per-task wall-time table, `--shard` echo). Cell count math is unchanged — chains never were per-cell.
- **`.claude/skills/analyzer/scripts/aggregate.py`** — drops `CHAIN_LENGTHS`, the `print_chain_table` function, and the chain-related legacy warning. `main()` no longer prints the chain table.
- **`.claude/skills/analyzer/scripts/plot.py`** — drops `fig2_chain` and `fig7_chain_step_survival` (function bodies + dispatch); chain pooling block in `merge_series` deleted (the merged series carries `"chains": []`); `_parse_figs` rejects numeric IDs `2` and `7` with a clear error pointing at this CHANGELOG; `--figs all` resolves to `{1, 3, 4, 5, 6}`. Figs `1, 3, 4, 5, 6` retain their pre-archive numeric IDs so existing shell snippets like `--figs 1,4,5` keep working.
- **`.claude/skills/analyzer/scripts/plot_focused.py`** — drops `fig3` (chain-focused per-model panels). `FIG_KEYS` tuple removes `"3"`; `_parse_figs` rejects `"3"` with an archive-note error. Other focused figures retain their numeric IDs.
- **`.claude/skills/analyzer/scripts/table.py`** — drops `CHAIN_LENGTHS` constant and `_chain_cells` helper; `build_rows`, `write_md`, `write_csv`, `write_tex` no longer emit chain columns. The LaTeX `col_spec` and `\multicolumn` group headers shrink correspondingly.
- **`.claude/skills/cluster-ops/scripts/status.sh`** — drops the `CHAIN` regex, the `chain_done` accumulator across both multi-cond and legacy code paths, and the `chain` column from the running-jobs table. Smoke fast-path no longer emits `"n/a"` placeholder.
- **`.claude/skills/{analyzer,cluster-ops,debug-and-simplify}/SKILL.md`** — chain mentions removed from running-table column lists, figure inventories, master-pivot column descriptions, and Layer-4 debugging questions.
- **`EXPERIMENTS_FLOW.md`** — top-of-file callout pointing at this CHANGELOG; §1 pipeline drops chain step; §4.3 collapsed to a one-paragraph archive notice; §5 evaluation parameters table loses chain rows; §5 gating bullets renamed "Single-task gating" and stripped of chain conditions; §9 output schema notes `chains: []` always emitted, per-task `num_ctx_chain` field annotation marks the date range it was emitted; the `chain_{ts}.json` subsection becomes an archive notice; §10 Direct CLI example drops `--chains \`; §11 paper-diff "no-tools matrix" row gains a chain-archive parenthetical.
- **`README.md`** — removes the chain CLI rows (`--chains`, `--chain-samples`, `--num-ctx-chain`), the "Include multi-task chain evaluation" code example, the "Chain evaluation" bullet from "How It Works", and the `chain_<timestamp>.json` line from the output list (replaced with an archive note pointing here). `--seed` help repurposed to `--smoke-shuffle`.
- **`cluster-experimenting/README.md`** — chain references trimmed from the no-tools quickstart wall, the Conditions list, the resource-profile `--time` table, the "Where things go" / "Fetching results" sections (file glob updated to `{single_task,summary}_*.json` with a back-compat note), and the troubleshooting `--num-ctx-chain` mitigation. The unrelated SLURM `afterok` dependency-chain idiom remains.
- **`CLAUDE.md`** — top-level note: "active flow is single-task only as of 2026-05-05; chain phase archived in `pddl_eval/{runner,summary}.py`."
- **`development/OPEN_ISSUES.md`** — `ISS-009` (chain with-tools=0% for 0.6b is uninformative) and `ISS-011` (chain denominator unchanged when steps are skipped) closed with this date and a pointer here.

**What did NOT change.**

- `pddl_eval/runner.py::run_chain_experiment` body — preserved verbatim.
- `pddl_eval/summary.py::{summarize_chains, print_chain_table, save_results chain branch}` — preserved verbatim.
- `pddl_eval/{chat.py, scoring.py}` — chain-related comments are about shared codepaths and are accurate; left as-is.
- `tests/*` — no chain references existed pre-archive (verified by grep before this PR); test suites unchanged.
- `single_task_*.json` and `summary_*.json` schemas — `summary["chains"]` still present (always `[]` in new outputs); pre-archive rows on disk parse identically.
- Pre-2026-05-05 result corpora (`checkpoints/cluster-26042026/`, `results/cluster-*/`) — files untouched. **Note**: their populated `chains` arrays no longer render in `aggregate.py` / `plot.py` / `table.py` after this change. If you need a chain-rendering aggregator for archaeology, revert this commit on a branch.
- `development/archive/{SUBMISSION_STRATEGY_PROPOSAL,FRAMEWORK_EXTENSION_PLAN}.md` — historical snapshots, untouched.

**Compatibility.**

- Existing `summary_*.json` files load unchanged in the trimmed analyzer (chain rows are ignored, not erroring).
- Old shell scripts that pass `--chains`, `--chain-samples N`, or `--num-ctx-chain N` to `run_experiment.py` will fail loudly with argparse "unrecognized arguments" — this is the intended back-compat boundary.
- The cluster sbatch's `CHAIN_SAMPLES` env var is no longer consumed; setting it has no effect (no warning either — silent ignore).

**Re-wiring the chain phase later.** The minimum patch to revive chains is: re-export the four names in `run_experiment.py`'s import block, re-add the three argparse flags, paste the dispatch block back into `async_main`, restore the smoke override, and pass `chain_results` (not `[]`) to `save_results`. No changes to `pddl_eval/` are needed because the bodies are intact. Analyzer / cluster-ops / docs would re-grow on their own as needed.

**Closes / narrows.** Closes `ISS-009`, `ISS-011` (both chain-specific and now moot under the archive policy). `ISS-013` (paper-diff audit) is left open — its scope spans single-task too.

**Files.** `run_experiment.py`, `pddl_eval/{runner,summary}.py`, `run_background.sh`, `cluster-experimenting/{submit_with_rtx.sh, run_condition_rtx.sbatch, README.md}`, `.claude/skills/analyzer/{SKILL.md, scripts/{aggregate,plot,plot_focused,table}.py}`, `.claude/skills/cluster-ops/{SKILL.md, scripts/status.sh}`, `.claude/skills/debug-and-simplify/SKILL.md`, `EXPERIMENTS_FLOW.md`, `README.md`, `CLAUDE.md`, `development/{CHANGELOG.md, OPEN_ISSUES.md}`.

---

## 2026-05-05 — Record `partial` in summary meta

**TL;DR.** When `--partial K > 0`, `summary_*.json`'s `meta` block now records `"partial": K`. Existing summaries on disk are unaffected; new writes only. Lets a reader of a synced summary tell at a glance whether the cell's `n` reflects partial- or full-scope, without back-deriving from `n` and the domain count.

**Files.** `run_experiment.py`.

---

## 2026-05-04 — Fast partial sweep + `--continue-partial` for full sweep

**TL;DR.** Two new CLI flags on `run_experiment.py`. `--partial K` caps each domain to first-K positive problems, first-K negative problems, and first-K valid + first-K invalid plans per kept positive problem (single-task-only fast feedback slice). `--continue-partial PARTIAL_DIR` seeds `args.output_dir/trials.jsonl` with the partial run's progress file before the existing resume logic kicks in, so partial trials transfer into a follow-up full sweep via the existing 10-tuple resume key. `results/` reorganised into `partial/`, `full/`, and `smoke/` buckets; default output dirs now land under the appropriate bucket. Pre-existing flat result dirs untouched. **No methodology change** — scoring, prompts, fixture content, and the resume-key shape are unchanged; existing results stay valid.

**Motivation.** The full sweep is too slow to use as a feedback loop while iterating on the harness or methodology. `--partial 2` produces an informative slice across all domains and all models in roughly 1/4 the wall time of the full sweep. `--continue-partial` makes that slice a launchpad: when the partial looks reasonable, the follow-up full run only executes the cells the partial didn't cover, instead of starting from scratch.

**What changed (`feature/partial-sweep-and-continue-partial` branch).**

- **`run_experiment.py`** — added `--partial K` (int, default 0) and `--continue-partial PATH` argparse entries; new `_apply_partial_subset(domains, k)` helper called after the existing `--domains` / `--problems` filters; the smoke output-dir block generalised to a `partial`/`smoke`/`full` bucket prefix that fires when `--output-dir` is left at its default; `--continue-partial` copies `PATH/trials.jsonl` into `args.output_dir/trials.jsonl` before `load_progress` runs, refusing if the dest is already non-empty unless `--no-resume` is also set.
- **`run_background.sh`** — new `partial` mode (calls `--partial 2 --conditions both`, no chains, output under `results/partial/`) and `continue-partial PATH` mode (passes `--continue-partial PATH`, output under `results/full/`). Existing modes (`small`, `large`, `both`, `*-nothink`) now write to `results/full/` instead of `results/` flat.
- **`cluster-experimenting/submit_with_rtx.sh`** — new `--continue-partial PATH` flag exports `CONTINUE_PARTIAL` to the array sbatch env so every cell seeds its own `OUT_DIR/trials.jsonl` from `PATH/trials.jsonl` on first submission. Source path is validated up front so a typo fails before the cluster pulls a slot. Echo strings also updated to reference the new smoke path (`results/smoke/{fixed,shuffle}_<sha>_<ts>/`). Array fan-out is unchanged — every (model, think, cond) cell still runs concurrently on its own GPU node.
- **`cluster-experimenting/run_condition_rtx.sbatch`** — added a 4-line guard before the python invocation: when `CONTINUE_PARTIAL` is set AND `OUT_DIR/trials.jsonl` is empty, pass `--continue-partial $CONTINUE_PARTIAL` to `run_experiment.py`. The empty-dir guard prevents a TIMEOUT-resubmitted cell from re-seeding (which would clobber trials accumulated since the first seed); subsequent resubmissions just resume from the existing JSONL.
- **`pddl_eval/resume.py`** + **`pddl_eval/runner.py`** + **`run_experiment.py`** (follow-up fix, same date) — `load_progress` now returns `dict[TrialKey, TaskResult]` instead of `(set, list)`; `run_single_task_experiment` accepts `restored_by_key` (replacing `done_keys`), tracks an `in_scope_keys` set during emission, and filters restored trials to in-scope before merging into the return value. **Why:** without this filter, a cell whose `trials.jsonl` was seeded from a multi-cell merged source (the typical `--continue-partial $MERGED_SEED` cluster case) would surface trials from OTHER cells in its own `summary_*.json`, polluting per-cell aggregates. The fix preserves the resume-skip semantics, the JSONL append order, and the "newly-run trials follow restored" output ordering, so existing analysis tooling is unaffected. Two regression tests in `tests/test_runner.py` cover the meta-dim filter and the post-`--partial` fixture filter.
- No `pddl_eval/runner.py` change. The 10-tuple resume key is unchanged; `--partial` ships a strict subset of cells with the same keys, so partial trials transfer to a follow-up full run without any schema work.

**Methodology note.** Partial → full transfer requires identical meta-dimensions (`tool_filter`, `prompt_style`, `think`, `conditions`) between the two runs, since those dimensions are part of the resume key. Mismatched cells re-run silently (correctness preserved, throughput cost only). Documented in the `--continue-partial` argparse help.

**Files.** `run_experiment.py`, `run_background.sh`, `cluster-experimenting/submit_with_rtx.sh`, `development/CHANGELOG.md`.

---

## 2026-05-04 — Whitespace normalization on the 10 newer paper-aligned domains

**TL;DR.** Apply the same `expand -t 2` + trailing-whitespace strip + final-newline pass that `f3aac57` (2026-04-21) ran on the original 10 domains, now to the 10 added in `b7960da` (PR-3). 114/120 `.pddl` files rewritten across `domains/{classical,numeric}/{gripper,miconic,parking,tpp,zenotravel,block-grouping,delivery,drone,gardening,zenotravel-numeric}/`. Tabs → 2 spaces, trailing whitespace stripped, trailing blank lines collapsed, exactly one final `\n`. **No semantic changes** — non-whitespace byte stream (`''.join(s.split())`) preserved on every file (the normalizer asserts this and aborts the write if it would drift).

**Motivation.** The 2026-05-04 diagnostic on `qwen3.6:35b validate_plan` showed that under per-task tools the model never passes the file verbatim — it re-emits the domain inline as a tool argument and corrupts deeply nested numeric expressions (paren miscount on `zenotravel-numeric/domain.pddl::fly-slow`'s `:effect` block, 145/145 `SYNTAX_ERROR`s downstream). The cleanup we ran on the original 10 domains in `f3aac57` was for the same class of model-side fragility — uniform whitespace makes the file's token sequence less surprising. The 10 newer domains skipped that pass; this entry brings them to parity. See `development/qwen3_6_35b_validate_plan_tool_inversion.md` for the full diagnosis.

**Verification.** All 10 `domain.pddl` parse `valid: true` standalone via `mcp__plugin_pddl-validator__validate_pddl_syntax`. All 10 `(domain, p01, p01_v1.plan)` triples round-trip with full plan-execution traces and goal satisfaction. Sampled `b*` plans still classify INVALID with the correct rejection reason; `domain_neg.pddl` and `n01.pddl` negative fixtures still report SYNTAX_ERROR for the right cause. So both positive and negative ground truth survived the cleanup — no `gt["plan_valid"]` flip risk for downstream sweeps.

**Followup.** Whether this whitespace cleanup actually moves the needle on the `qwen3.6:35b validate_plan` tools-vs-no-tools inversion (−2.7pp on cluster-20260504) is an open empirical question. The hypothesis we're banking on: cleaner whitespace gives the model a more regular token sequence to copy, reducing paren-balance errors when re-emitting as a tool argument. The hypothesis we're hedging against: the model's content-fidelity loss is structural and won't shift no matter how clean the source is. **Next sweep on the cleaned files is the test.** Recheck the per-domain table from the prior diagnosis after the next per-task tools run on `qwen3.6:35b` lands; if `zenotravel-numeric` tools-condition stays at ~47% and the aggregate validate_plan delta stays at −3pp, the inversion is model-layer (won't be fixable by file hygiene). If `zenotravel-numeric` recovers and the aggregate flips positive, the cleanup was the missing piece.

**Files.**
- `domains/classical/{gripper,miconic,parking,tpp,zenotravel}/{domain,domain_neg,p01..p05,n01..n05}.pddl` — 60 files, 56 rewritten.
- `domains/numeric/{block-grouping,delivery,drone,gardening,zenotravel-numeric}/{domain,domain_neg,p01..p05,n01..n05}.pddl` — 60 files, 58 rewritten.
- 6 already-clean files left untouched (`gripper/n04`, `gripper/n05`, `miconic/n04`, `miconic/n05`, `block-grouping/domain.pddl`, `block-grouping/domain_neg.pddl`).
- Plan files (`*.plan`) untouched.
- The original 10 domains (`barman`, `blocksworld`, `depots`, `satellite`, `rovers`, `counters`, `depot`, `farmland`, `sailing`, `pogo_stick`) untouched — they were already cleaned in `f3aac57`.

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
- **`.claude/skills/{cluster-ops,analyzer}/scripts/{aggregate,plot}.py`** — both `parse_dirname` functions made the trailing `_<jobid>` capture optional. Cell-keyed dirs (no jobid) parse via the same suffix-matching loop; legacy `_<jobid>` and pre-think-axis (`slurm_<model>_<cond>_<jobid>`) layouts continue to parse unchanged. Empty-string `jobid` field surfaces in the aggregator's pivot tables for new-shape rows; this is intentional (one row per cell instead of per-resubmission). (`aggregate.py` / `plot.py` were moved to the new `analyzer` skill in this PR — see the skill-split paragraph below.)

*Skill split — operations vs analysis.*
- **`.claude/skills/analyzer/`** (new) — owns the analysis surface: `aggregate.py`, `plot.py`, `plot_focused.py`, `table.py` moved here from `cluster-ops/scripts/`, plus a new `drift_check.py` that compares an in-flight or finished sweep against a baseline by aligning per-cell `(model, think, cond, task)` rows and flagging cells whose current point estimate falls outside the baseline's Wilson 95% CI. Mid-sweep cells with no `summary_*.json` yet are aggregated from `trials.jsonl` directly (PR-30 makes this possible). Exit code is `1` if any `direction=below` rows surface, suitable for scripted gating.
- **`.claude/skills/cluster-ops/`** — trimmed to operations only (`status.sh`, `sync.sh`, `preflight.sh`, `postmortem.sh`). Frontmatter description updated; the four moved scripts and their sections removed; recipes that previously did sync→aggregate→plot→table now hand off to the `analyzer` skill mid-recipe. New "Is the in-flight sweep drifting?" recipe glues `status.sh` + `sync.sh` to `drift_check.py`.
- Motivation for the split: `cluster-ops` was bundling two distinct user surfaces — "operate the cluster" (invoked while a sweep is queued/running, user wants knobs to turn) and "turn results into tables/figures/observations" (invoked after sync, user wants numbers and pictures). Mixing the two in one `SKILL.md` made each unfocused; the argument-hint listed seven verbs spanning both lifecycle phases. The split makes each skill's trigger surface coherent and lets `analyzer` stand on its own as a read-only interpreter of any results root, including ones not produced by this cluster pipeline.

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

**Files.** `pddl_eval/runner.py`, `run_experiment.py`, `tests/test_runner.py`, `cluster-experimenting/{run_condition_rtx.sbatch, submit_with_rtx.sh, README.md}`, `.claude/skills/cluster-ops/SKILL.md`, `.claude/skills/analyzer/{SKILL.md, scripts/{aggregate.py, plot.py, plot_focused.py, table.py, drift_check.py}}` (the four pre-existing scripts moved from `cluster-ops/scripts/`; `drift_check.py` is new), `development/CHANGELOG.md`.

**Post-review fixes (follow-up commit).** Three nits surfaced during review of the PR were cleared on the same branch:
- **`drift_check.py` test coverage.** `tests/test_drift_check.py` (new, 11 assertions) covers `wilson_ci` known values + zero-n, `_classify_drift` for all four verdicts (`none`/`below`/`above`/`no-data`), `_load_cell` precedence (summary > JSONL, JSONL fallback, empty → `None`), and `_aggregate_trials_jsonl` first-seen dedup. Registered in `tests/verify.sh`. The script's exit-code-1-on-`below` is consumed by scripted gating, so silent regressions in any of these paths could let a regressing sweep keep burning GPU-hours; tests close that gap.
- **`wilson_ci` deduplicated.** `pddl_eval.summary.wilson_ci` is now the single canonical implementation. `.claude/skills/analyzer/scripts/{plot.py, drift_check.py}` import it directly (each adds the repo root to `sys.path` once at import time so they remain runnable as standalone scripts from the repo root). The two analyzer-local copies are deleted; the floats they returned were semantically equivalent, so all existing plots and drift outputs are byte-stable. SKILL.md "Conventions" line updated.
- **`TRIAL_KEY_LEN` enforced in `_aggregate_trials_jsonl`.** Wrong-length key tuples (would surface if the trial-key shape ever changes after old JSONLs were written) are silently dropped — consistent with the surrounding malformed-line policy. Loud failure here would block drift checks against a cell whose `summary_*.json` is fine but whose `trials.jsonl` predates a shape change. The runner-side `_load_progress` keeps the loud-`RuntimeError` policy for the writer path; the reader-side analyzer degrades gracefully.

**Files (post-review).** `tests/test_drift_check.py` (new), `tests/verify.sh`, `.claude/skills/analyzer/scripts/{drift_check.py, plot.py}`, `.claude/skills/analyzer/SKILL.md`, `development/CHANGELOG.md`.

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
