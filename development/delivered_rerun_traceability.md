# Delivered rerun: prereg clause → code traceability (freeze gate 3)

Freeze candidate of the analysis for `development/reference/delivered_rerun_prereg.md`
(branch `docs/reanalysis-and-rerun-prereg`). Written 2026-10-03, before any outcome row of
the rerun was read. Code: `tools/delivered_rerun/` (abbreviated `dr/` below). Tests:
`tests/test_delivered_rerun_analysis.py` (abbreviated `T:`), fixture
`tests/fixtures/delivered_rerun/`. Line numbers are at the freeze-candidate commit; the
sha256 table belongs to the freeze record (prereg §8) and is not computed here.

Status: **one BLOCKING item** (E2 on simulate, see the end). Gate 5 (independent
adversarial review) has not run yet.

## §2 Design and apparatus deltas (the parts the analysis must check)

| clause (quoted) | implemented at | test |
|---|---|---|
| "models `Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b`" / Part B "`gemma4:26b-a4b`" | `dr/constants.py:25` (tag → model id), `:178-179` asserts; every row's model id checked `dr/schema.py:363` | T: `test_refusals` "row of another model" |
| "thinking off" | resume key must carry `off`: `dr/schema.py:356-358`; `dr/constants.py:175` | T: "key disagrees with result" |
| "tools, all tools visible" | `tool_filter == "all"` `dr/schema.py:338`; `with_tools` per cell `:365` | fixture |
| "prompt style `minimal` (as canonical)" / "`neutral`" | per-cell `prompt_style`, refused otherwise `dr/schema.py:367` (RefusedRow) | T: "minimal row in neutral cell" |
| "user-prompt variants 11–13 (plain), 14–16 (steered)" | `dr/constants.py:43-46`, `:177`; per cell `dr/schema.py:372` | fixture |
| "tasks all five" / "validate_plan" | `dr/schema.py` `spec_rerun_a`/`spec_rerun_b`, row check `:370-373` | fixture |
| "3 × 9,120 = 27,360" / "6,000" | `dr/constants.py:187-188`, `:199`; completeness `dr/schema.py:471-490` | T: `test_registered_constants`, "short cell" |
| "run tag `delivered-rerun`" / "`delivered-rerun-neutral`" | cell directory names `dr/schema.py` `rerun_a_name`, `rerun_b_name` | fixture |
| "3,000 trials per cell" (2 × 2) | `dr/constants.py:197` | T: `test_registered_constants`, R5 cell n |
| Delta 1 "Final answers stored up to 65,536 characters … Registered expectation: zero rows cut." | `response_truncated_by_storage` must be a bool and False on every rerun row (RefusedRow) and length ≤ 65,536: `dr/schema.py:386-395`; `dr/constants.py:173`; storage cuts reported per cell `dr/run.py` `corpus_table` | T: "storage-cut row", "row missing a new field", `test_base_e1` storage cuts |
| Delta 2 "lowers the allowance to what actually fits" (prompt + allowance ≤ 16,384) | clip sizes checked against the window, RefusedRow if exceeded: `dr/schema.py:272`; `dr/constants.py:174` | T: "clip beyond the window" |
| Delta 3 "A leading `<\|channel>thought\n<channel\|>` is removed from the text the grader reads." | `dr/grade.py:53` (assert), harness extractors strip once; tolerant/table fallbacks read the once-stripped view `dr/grade.py:96`; E4 reads the same view `dr/e4.py`; never stripped twice | T: `test_grader_prefix`; fixture Gemma solve v11 (strict path) and v14 (tolerant path) |
| "The unaided arm is not rerun" (no-tools side from canonical) | `dr/run.py` `load_all` reads canonical no-tools cells; `dr/schema.py` `spec_canonical_no_tools` | fixture |

## §3 Parity guard

| clause (quoted) | implemented at | test |
|---|---|---|
| "evaluated before any delivered number is read" | `dr/run.py:160` parity is computed before any delivered grade exists (`:163-167`) | code order |
| "tool-verified success" | stored `success` (typed bool) `dr/analysis.py:112` | `test_base_parity` |
| "Model × task × arm … 30 cells" | `dr/analysis.py` `parity()`; `assert len(cells) == C.PARITY_CELLS`; `dr/constants.py:165` | `test_base_parity` |
| "Δ = rerun − canonical, paired on the trial key (domain, problem, variant, plan label)" | `Row.trial_key` `dr/schema.py`; `dr/analysis.py:107`, `:112-113` | `test_base_parity` (Δ̂ = 100/12, 0) |
| "Rows missing from either corpus are counted and reported" | `dr/analysis.py:110`; readout column "unpaired" | 9B validate_domain plain: 1/1 |
| "a cell with more than 1% unpaired rows is VOID" | `dr/analysis.py:111`, `:114-116`; `dr/constants.py:171` | 2/7 → VOID |
| "Paired TOST at ±5 points: the 90% confidence interval of Δ … inside [−5, +5]" | `dr/stats.py:93-100` (`tost_met`), `dr/analysis.py:116`; `dr/constants.py:162`, `:169` | Gemma vplan [0, 16.7] not met; 26 cells [0,0] met |
| "cluster bootstrap over the 20 domains (10,000 resamples, seed 20261002)" | `dr/stats.py:35-58`; `assert k == k_expected` `:49`; seed `:52`; resamples `:53`; `dr/constants.py:167-168`, `:191` | T: `test_stats_units` "bootstrap asserts k"; `test_canonical_dry_run` k = 20 |
| "Secondary … the unpaired Newcombe 90% interval used by the `iss024d` parity prereg" | `dr/stats.py:103` (same formula as `tools/iss024d_parity.py:132`); `dr/analysis.py:126` | Newcombe value checked against an independent Wilson computation |
| "Gemma's 10 cells are evaluated before the Qwen cells" | `dr/analysis.py:145` order, Gemma verdicts settled at `:159-160` before any Qwen cell is built | `test_base_parity` "gemma cells listed first" |
| "If any Gemma cell fails, F = max \|Δ̂\| over Gemma cells is reported as the noise floor" | `dr/analysis.py:159-160` | F = 100/12 |
| "Parity holds if at least 18 of the 20 Qwen cells meet the criterion and no cell of any model has \|Δ̂\| > 10 points" | `dr/analysis.py:164-166`; `dr/constants.py:163-164` | base: 18 → holds; `test_job_level_failure`: 17 and a gross cell → fails |
| "Parity holds: … reported as the exact delivered rates of the headline cells, with the apparatus deltas of §2 stated" | `dr/analysis.py:171` (`CONSEQ_EXACT`), deltas text `dr/analysis.py:54`, emitted `dr/run.py:192` and in the readout | `test_base_parity` |
| "A cell fails: … separate-apparatus measurement, labelled … 'criterion not met (unresolved)'" | `dr/analysis.py:173` (`CONSEQ_CELL_FAIL`), verdict label `NOT_MET` | `test_base_parity` |
| "Parity fails at job level: the whole rerun is reported as a separate-apparatus replication" | `dr/analysis.py:169` | `test_job_level_failure` |
| "The margin is not adjusted after the data are seen" | margin is a literal asserted at import `dr/constants.py:162`, `:205` | — |
| "reported with the count of rows whose allowance was clipped before a tool call" | `Row.clipped_before_tool_call` `dr/schema.py:161`; per cell `dr/analysis.py:128` | `test_clipped_logic`; fixture count 1 |

## §4 Primary endpoints

| clause (quoted) | implemented at | test |
|---|---|---|
| "delivered success: the final answer graded against the oracle, with the normalisation of §2 delta 3, exact (no censoring bounds)" | `dr/grade.py:130-183`; no censoring branch, every grade is a bool; a missing oracle or validator verdict raises (`:144`, `:158`, `:170`); delivered = `e2e_strict` semantics (empty answer fails) `dr/grade.py:120-127` | `test_base_e1`, `test_grader_prefix`, "no validator verdict" |
| E1 "Delivered rate per cell. 30 cells, with a domain-cluster bootstrap 95% interval." | `dr/analysis.py` `rate_cell`, interval `:218`; `dr/run.py:169` | `test_base_e1` (all 30 counts, 6 intervals) |
| E2 "Tools-plain (this run) against no-tools (canonical `sweep5v2-live`, exact, v11–13), per model × task, paired on (domain, problem, variant, plan label)" | `dr/analysis.py:278-297`; v11–13 asserted `:286`; no-tools delivered = online grade `:261-275`, refused if a no-tools answer carries the leaked prefix `:272` | `test_base_e2_e3`; `test_canonical_dry_run` (no prefix in canonical no-tools) |
| E2 "domain-cluster bootstrap 95% interval, Holm across the 15 comparisons" | interval `dr/analysis.py` `_contrast`; Holm `:322` → `dr/stats.py:118-120` (asserts family = 15) | `test_base_e2_e3`, `test_stats_units` Holm hand values |
| E2 "its serving version and the missing JSON constraint are stated wherever this contrast is quoted" | `dr/analysis.py:50` (`E2_CAVEAT`), `dr/run.py:195`, readout E2 header | `test_base_e2_e3` |
| E2 on simulate | **BLOCKING**, see below. Emitted as status `E2_BLOCKED` `dr/analysis.py:48`, `:292`; enters Holm with p = 1 | `test_base_e2_e3` |
| E3 "Tools-steered against tools-plain, both from this run, same pairing and intervals, Holm across 15" | `dr/analysis.py:300-320`; pairing v ↔ v+3 `:311`, `dr/constants.py:50` | `test_base_e2_e3` |
| E4 "Share of trials with a correct tool result whose delivered answer is wrong, per cell" | `dr/analysis.py:343-357` (population `success is True` `:345`) | `test_base_e4` |
| E4 "classified by the fixed categories … (no final answer, tool-input error, summary only, abridged, wrong wrapper, numeric omitted, wrong facts) plus 'refused or clipped final request'" | `dr/e4.py:48` (`CATS`), decision order `dr/e4.py:188-206`; non-mechanical cases → `NEEDS_READING` | `test_base_e4` (every category exercised) |

## §5 Registered readings

| clause (quoted) | implemented at | test |
|---|---|---|
| R1 "interval entirely below −5 → Harm confirmed …; entirely inside [−5, +5] → No delivered harm …; anything else → Unresolved" (E2, Gemma validate_plan) | `dr/analysis.py:367-377` | `test_base_readings`; `test_reading_rules` (boundaries) |
| R2 "E3 for Gemma validate_plan: interval entirely above +5 = yes; entirely inside [−5, +5] = no; else unresolved" | `dr/analysis.py:379-389` | `test_base_readings`; `test_reading_rules` |
| R3 "The title stays … only if R1 is 'harm confirmed' or … E3 shows a delivered gain above +5 for at least two of the three models on validate_plan" | `dr/analysis.py:391-397`; `dr/constants.py:172` | `test_base_readings`; `test_reading_rules` (via R1, two models, one model) |
| R4 "For solve, E4 among calling trials with a full, uncut final answer. If the share delivered correctly is at least 90% for each model" | `dr/analysis.py:399-413`; threshold `dr/constants.py:172` | `test_base_readings` (11/11, 11/12, 9/11 → not met); `test_r4_attributed` |
| R5 "Invocation rate (share of trials with a tool call) and delivered success in the four cells of the 2 × 2" | `Row.invoked` (`len(tool_calls) > 0`) `dr/schema.py:146`; `dr/analysis.py:415-430` | `test_base_readings` 2 × 2 |
| R5 "lower by more than 5 points / within ±5 (paired TOST as in §3) / higher by more than 5 points" | `dr/analysis.py:443-450` (point estimate for the outer rows, 90% CI TOST for the middle row) | `test_base_readings` (doing work); `test_r5_paths` (suppress, inert, no row) |
| R5 "if neutral-steered invocation is within ±5 of minimal-steered, steering in the user turn is sufficient by itself" | `dr/analysis.py:453` | `test_base_readings` |
| "No reading is added, dropped or re-thresholded after the data are seen" | labels are module constants `dr/analysis.py` top; thresholds asserted in `dr/constants.py` | — |

## §7 Execution

| clause (quoted) | implemented at | test |
|---|---|---|
| "Smoke … separate run tags, never pooled" | cell names are constructed, never globbed; a `smoke` name is refused `dr/schema.py:433` | T: "smoke refused" |
| "no row is cut by storage; no exception or infrastructure-failure rows" (smoke checks, re-checked on the main run) | storage `dr/schema.py:386-395`; exception/infra counts per cell `dr/schema.py:462-464` → VOID rule below | T: "storage-cut row", "exception rows > 1%" |
| "A cell is VOID and rerun from scratch … if more than 1% of its rows are infrastructure failures or exceptions" | `dr/run.py:101` (halts, no readout); exception = `failure_reason ∈ {exception, ollama_parse_error}` `dr/constants.py:78`; infra = `infra_failure` | T: "exception rows > 1% -> VOID" |
| "Completeness. 9,120 rows per Part A cell, 6,000 for Part B, 1,520 / 1,000 per variant. A short cell is resumed, not analysed." | `dr/schema.py:471-490` (rows, per variant, per task × variant, domain count) raises `IncompleteCell`; `dr/constants.py:187-191` | T: "short cell" |
| "No success, invocation or failure-reason rate of any cell is computed before the freeze" | live mode refuses unless `--i-have-frozen` equals the package hash `dr/run.py:242`; the hash covers the package and the imported harness files `dr/run.py:51` | T: `test_live_mode_guard` |

## §8a Smoke record (consequences for the analysis)

| clause (quoted) | implemented at | test |
|---|---|---|
| "on rows whose allowance was clipped, measured prompt plus clipped allowance against the 16,384-token window" | `dr/schema.py:272` | T: "clip beyond the window" |
| "delivered simulate for the open-weight tool arms is reported with these rows counted as failures and their share stated (`ctx_no_room_turns`)" | no-room rows grade False with reason `no_room` `dr/grade.py:120-122`; count and share per cell `dr/analysis.py:221`; readout E1 column | `test_base_e1` (1 row, 1/6) |
| (no-room turn shape) "the row then has an empty answer with `done_reason = "length"`" (EXPERIMENTS_FLOW §9) | `dr/schema.py:403` (RefusedRow otherwise) | T: "no-room row with text" |
| "Clipped rows that later hit a no-room turn carry the clip count without the last-turn sizes" | sizes optional in `Tokens`; arithmetic checked only when both sizes exist `dr/schema.py:270-274` | fixture |

## Freeze-protocol gates and tripwires

| commitment | implemented at | test |
|---|---|---|
| Gate 1: one typed loader; crash on unknown enum, missing key, wrong layer, wrong `prompt_style`, duplicate key | `dr/schema.py:296-418` (`parse_row`), `:430-464` (`load_cell`); result key set tied to `TaskResult` `dr/schema.py:68` | T: `test_refusals` (14 refusals) |
| Gate 1: no bare `.get()` / truthiness on grade fields in estimator code | grep: the only `.get(` calls are on counters (`dr/schema.py`, `dr/stats.py`) and on MCP tool-result JSON in `dr/e4.py` (the harness's own parse); grades are compared with `is True` / typed bools | grep at freeze |
| Gate 2: registered constants as asserts | `dr/constants.py:160-205` | T: `test_registered_constants` |
| Gate 3: imports declared | numpy (requirements.txt); pydantic via pddl_eval; nothing else outside the stdlib | — |
| Gate 4: synthetic fixture with hand-computed values, refusals | `tests/fixtures/delivered_rerun/build_fixture.py`; T: whole file (282 checks) | `bash tests/verify.sh` |
| Canonical-vs-canonical dry run gives Δ = 0 in every cell | T: `test_canonical_dry_run` (reads `results/sweep5v2-live`) | passes, k = 20 |
| Tripwire: a guard firing in every cell | `dr/tripwires.py:64` (T1), `:67` (T2), `:98` (T5 fallback bucket) | T: `test_tripwires` |
| Tripwire: a constant output column | `dr/tripwires.py:79` (T3) | T: `test_tripwires` |
| Tripwire: rates outside a band justified from the canonical corpus | `dr/tripwires.py:37-38`, `:42-56`, `:94` (T4); band rationale in the module docstring; canonical counts `dr/constants.py` `CANONICAL_DELIVERED_COUNTS` | T: `test_tripwires`; band constants re-counted from the overlay in `test_canonical_dry_run` |
| Tripwires halt with a non-zero exit; release only by naming them as audited | `dr/run.py:179-182` | T: `test_tripwires` (halt, then `--audited-tripwires`) |

## Out of scope for this map

§6 (secondary, descriptive, "not gates") is not implemented. §7 run order and monitoring
and §8 (job IDs, serving version, freeze record) are operational, not analysis code.

## BLOCKING

1. **E2 on simulate (3 of the 15 comparisons) cannot be computed as registered.** §2 says
   the unaided arm is not rerun because "the no-tools delivered score is already exact,
   because it was graded online on the full text". That holds for solve and the three
   validate tasks, not for simulate: the canonical no-tools simulate rows were graded online
   with the trajectory normaliser that predates the predicate-notation fix
   (`scoring._canon_atom`; stored
   `success` is False on every one of the 900 headline rows), and the stored answers are
   500-character snapshots, so they cannot be re-graded. The e2e overlay marks 300/300
   (Gemma), 262/300 (Qwen3.5-9B) and 271/300 (Qwen3.6-35B) of the v11–13 rows as censored.
   The code emits these three contrasts as `BLOCKED` with no estimate and enters them in
   the Holm family with p = 1, so the family stays at the registered 15. The author must
   choose before the freeze: (a) keep that, (b) declare Holm over 12, (c) report censoring
   bounds for these three, or (d) rerun no-tools simulate. Any of these is a declared
   deviation from §4 E2 as written. R1–R3 do not read simulate, so no registered reading
   depends on it.
