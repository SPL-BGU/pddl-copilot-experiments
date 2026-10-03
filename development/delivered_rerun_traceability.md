# Delivered rerun: prereg clause → code traceability (freeze gate 3)

Freeze candidate of the analysis for `development/reference/delivered_rerun_prereg.md`
(branch `docs/reanalysis-and-rerun-prereg`, version 717b4b1: Part C added in §2,
clarifications in §8b). Written 2026-10-03, before any outcome row of the rerun was read.
Code: `tools/delivered_rerun/` (abbreviated `dr/` below). Tests:
`tests/test_delivered_rerun_analysis.py` (abbreviated `T:`), fixture
`tests/fixtures/delivered_rerun/`. Line numbers are at the freeze-candidate commit; the
sha256 table belongs to the freeze record (prereg §8) and is not computed here.

Status: **no BLOCKING item.** The earlier one (E2 on simulate) is resolved by Part C.
Gate 5 (independent adversarial review) has not run yet.

## §2 Design and apparatus deltas (the parts the analysis must check)

| clause (quoted) | implemented at | test |
|---|---|---|
| "models `Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b`" / Part B "`gemma4:26b-a4b`" | `dr/constants.py:25` (tag → model id), asserts `:182-183`; every row's model id checked `dr/schema.py:363` | T: `test_refusals` "row of another model" |
| "thinking off" | resume key must carry `off`: `dr/schema.py:358`; `dr/constants.py:179` | T: "key disagrees with result" |
| "tools, all tools visible" | `tool_filter == "all"` `dr/schema.py:338`; `with_tools` per cell `:365` | fixture |
| "prompt style `minimal` (as canonical)" / "`neutral`" | per-cell `prompt_style`, refused otherwise `dr/schema.py:367` (RefusedRow) | T: "minimal row in neutral cell", "Part C row with neutral style" |
| "user-prompt variants 11–13 (plain), 14–16 (steered)" | `dr/constants.py:47-50`, assert `:181`; per cell `dr/schema.py:372` | fixture |
| "tasks all five" / "validate_plan" | `dr/schema.py:370`; cell specs `spec_rerun_a`, `spec_rerun_b` | fixture |
| "3 × 9,120 = 27,360" / "6,000" | `dr/constants.py:194-195`, `:206`; completeness `dr/schema.py:475-495` | T: `test_registered_constants`, "short cell" |
| "run tag `delivered-rerun`" / "`delivered-rerun-neutral`" | cell directory names `dr/schema.py` `rerun_a_name`, `rerun_b_name` | fixture |
| "3,000 trials per cell" (2 × 2) | `dr/constants.py:204` | T: R5 cell n |
| Delta 1 "Final answers stored up to 65,536 characters … Registered expectation: zero rows cut." | `response_truncated_by_storage` must be a bool and False on every rerun row (RefusedRow), length ≤ 65,536: `dr/schema.py:386-395`; `dr/constants.py:177`; storage cuts per cell `dr/run.py:111` | T: "storage-cut row", "row missing a new field", `test_base_e1` storage cuts (7 rerun cells) |
| Delta 2 "lowers the allowance to what actually fits" (prompt + allowance ≤ 16,384) | `dr/schema.py:272` (RefusedRow if exceeded); `dr/constants.py:178` | T: "clip beyond the window" |
| Delta 3 "A leading `<\|channel>thought\n<channel\|>` is removed from the text the grader reads." | `dr/grade.py:57` (assert); harness extractors strip once; tolerant/table fallbacks read the once-stripped view `dr/grade.py:100`; E4 reads the same view; never stripped twice | T: `test_grader_prefix`; fixture Gemma solve v11 (strict path) and v14 (tolerant path) |
| Part C "the three headline models, thinking off, no tools, v11–13, all five tasks, 3 × 4,560 = **13,680 trials**, same harness commit, tag `delivered-rerun`" | cell `slurm_vllm_<m>_off_no-tools_delivered-rerun` `dr/schema.py:508`, spec `:538` (no tools, `minimal`, v11–13, all tasks, rerun layer so the storage field is required); `dr/constants.py:40`, `:185`, `:207-209` | T: "Part C row with a steered variant", "… with tool calls", "… missing the storage field", "Part C storage-cut row", "Part C short cell", "Part C format_compliant outside simulate" |
| Part C "**E2 now uses Part C as its no-tools side**, graded with the same delivered grader as the tool side … The canonical no-tools cells are no longer an input to E2." | `dr/analysis.py:260-277` (both sides through `dlv`, which reads `grade.grade` output); `dr/grade.py:134-137` grades tool and no-tools rerun rows with one code path and refuses canonical rows | T: `test_base_e2_e3` (all 15 computed), `test_grader_prefix` (Part C tolerant solve row: stored False, delivered True; canonical row refused) |
| Part C "**Part C parity check (reported, not a gate on E2).** … solve and the three validate tasks (12 cells): Δ = Part C − canonical on the stored online `success`, paired, same TOST at ±5 with the 90% domain-cluster interval as §3. Simulate is excluded" | `dr/analysis.py:280-288` (the §3 `parity_cell` code path); `dr/constants.py:45`, `:187`; computed before any delivered grade `dr/run.py:166`; not consulted by E2 or the job rule | T: `test_part_c_parity` (Gemma solve −100/6, not met; 11 cells met; job verdict unchanged); dry run on canonical vs itself |
| §7 VOID rule for Part C cells | `dr/run.py:104` covers Parts A, B and C | T: "Part C exception rows > 1% -> VOID" |
| "The unaided arm … ran on vLLM 0.20.2" / §4 E2 "its serving version and the missing JSON constraint are stated wherever this contrast is quoted" | `dr/analysis.py:49` (`E2_CAVEAT`), `dr/run.py:203`, readout E2 header | `test_base_e2_e3` |

## §3 Parity guard

| clause (quoted) | implemented at | test |
|---|---|---|
| "evaluated before any delivered number is read" | `dr/run.py:165` parity is computed before any delivered grade exists (`:170-174`) | code order |
| "tool-verified success" | stored `success` (typed bool) `dr/analysis.py:112` | `test_base_parity` |
| "Model × task × arm … 30 cells" | `dr/analysis.py` `parity()`; `dr/constants.py:169` | `test_base_parity` |
| "Δ = rerun − canonical, paired on the trial key (domain, problem, variant, plan label)" | `Row.trial_key` `dr/schema.py`; `dr/analysis.py:107-113` | `test_base_parity` (Δ̂ = 100/12, 0) |
| "Rows missing from either corpus are counted and reported" | `dr/analysis.py:110`; readout column "unpaired" | 9B validate_domain plain: 1/1 |
| "a cell with more than 1% unpaired rows is VOID" | `dr/analysis.py:111`, `:114-116`; `dr/constants.py:175` | 2/7 → VOID |
| "Paired TOST at ±5 points: the 90% confidence interval of Δ … inside [−5, +5]" | `dr/stats.py:93-100`, `dr/analysis.py:116`; `dr/constants.py:166`, `:173` | Gemma vplan [0, 16.7] not met; 26 cells [0,0] met |
| "cluster bootstrap over the 20 domains (10,000 resamples, seed 20261002)" | `dr/stats.py:35-58`; `assert k == k_expected` `:49`; seed `:52`; resamples `:53`; `dr/constants.py:171-172`, `:198` | T: "bootstrap asserts k"; dry run k = 20 |
| "Secondary … the unpaired Newcombe 90% interval used by the `iss024d` parity prereg" | `dr/stats.py:103` (formula of `tools/iss024d_parity.py:132`); `dr/analysis.py:126` | Newcombe checked against an independent Wilson computation |
| "Gemma's 10 cells are evaluated before the Qwen cells" | `dr/analysis.py:145`, Gemma verdicts settled at `:159-160` before any Qwen cell | "gemma cells listed first" |
| "If any Gemma cell fails, F = max \|Δ̂\| over Gemma cells is reported as the noise floor" | `dr/analysis.py:159-160` | F = 100/12 |
| "Parity holds if at least 18 of the 20 Qwen cells meet the criterion and no cell of any model has \|Δ̂\| > 10 points" | `dr/analysis.py:164-166`; `dr/constants.py:167-168` | base: 18 → holds; `test_job_level_failure`: 17 and a gross cell → fails |
| "Parity holds: … reported as the exact delivered rates of the headline cells, with the apparatus deltas of §2 stated" | `dr/analysis.py:171`; deltas `dr/analysis.py:54`, emitted `dr/run.py:199` and in the readout | `test_base_parity` |
| "A cell fails: … separate-apparatus measurement, labelled … 'criterion not met (unresolved)'" | `dr/analysis.py:173` | `test_base_parity` |
| "Parity fails at job level: the whole rerun is reported as a separate-apparatus replication" | `dr/analysis.py:169` | `test_job_level_failure` |
| "The margin is not adjusted after the data are seen" | literal asserted at import `dr/constants.py:166`, `:214` | — |
| "reported with the count of rows whose allowance was clipped before a tool call" | `Row.clipped_before_tool_call` `dr/schema.py:161`; per cell `dr/analysis.py:128` | `test_clipped_logic`; fixture count 1 |

## §4 Primary endpoints

| clause (quoted) | implemented at | test |
|---|---|---|
| "delivered success: the final answer graded against the oracle, with the normalisation of §2 delta 3, exact (no censoring bounds)" | `dr/grade.py:134-188`; no censoring branch, every grade a bool; missing oracle or validator verdict raises (`:149`, `:163`, `:175`); empty answer fails `dr/grade.py:124-131` | `test_base_e1`, `test_grader_prefix`, "no validator verdict" |
| E1 "Delivered rate per cell. 30 cells, with a domain-cluster bootstrap 95% interval." | `dr/analysis.py` `rate_cell`, interval `:218`; `dr/run.py:176` | `test_base_e1` (30 counts, 6 intervals) |
| E2 "Tools-plain (this run) against no-tools … per model × task, paired on (domain, problem, variant, plan label)" (no-tools side = Part C per §2) | `dr/analysis.py:260-277`; v11–13 and no-tools asserted on the Part C side | `test_base_e2_e3` (15 estimates, intervals, p) |
| E2 "domain-cluster bootstrap 95% interval, Holm across the 15 comparisons" | interval `dr/analysis.py:251`; Holm `:313` → `dr/stats.py:118-120` (asserts family = 15) | `test_base_e2_e3`, `test_stats_units` Holm hand values |
| E3 "Tools-steered against tools-plain, both from this run, same pairing and intervals, Holm across 15" | `dr/analysis.py:291-311`; pairing v ↔ v+3 `:302`, `dr/constants.py:54` | `test_base_e2_e3` |
| E4 "Share of trials with a correct tool result whose delivered answer is wrong, per cell" | `dr/analysis.py:333-347` (population `success is True` `:335`) | `test_base_e4` |
| E4 "classified by the fixed categories … plus 'refused or clipped final request'" | `dr/e4.py:48` (`CATS`), decision order `dr/e4.py:188-206` | `test_base_e4` (every category exercised) |

## §5 Registered readings

| clause (quoted) | implemented at | test |
|---|---|---|
| R1 "interval entirely below −5 → Harm confirmed …; entirely inside [−5, +5] → No delivered harm …; anything else → Unresolved" | `dr/analysis.py:357-367` | `test_base_readings`; `test_reading_rules` (boundaries) |
| R2 "interval entirely above +5 = yes; entirely inside [−5, +5] = no; else unresolved" | `dr/analysis.py:369-379` | `test_base_readings`; `test_reading_rules` |
| R3 "stays … only if R1 is 'harm confirmed' or … E3 shows a delivered gain above +5 for at least two of the three models on validate_plan" | `dr/analysis.py:381-387`; `dr/constants.py:176` | `test_reading_rules` (via R1, two models, one model) |
| R4 "For solve, E4 among calling trials with a full, uncut final answer … at least 90% for each model" | `dr/analysis.py:389-403` | `test_base_readings` (11/11, 11/12, 9/11 → not met); `test_r4_attributed` |
| R5 "Invocation rate (share of trials with a tool call) and delivered success in the four cells of the 2 × 2" | `Row.invoked` `dr/schema.py:146`; `dr/analysis.py:405-421` | `test_base_readings` 2 × 2 |
| R5 "lower by more than 5 / within ±5 (paired TOST as in §3) / higher by more than 5" | `dr/analysis.py:433-440` | `test_base_readings`; `test_r5_paths` (suppress, inert, no row) |
| R5 "if neutral-steered invocation is within ±5 of minimal-steered, steering in the user turn is sufficient by itself" | `dr/analysis.py:443` | `test_base_readings` |
| "No reading is added, dropped or re-thresholded after the data are seen" | labels are module constants at the top of `dr/analysis.py`; thresholds asserted in `dr/constants.py` | — |

## §7 Execution

| clause (quoted) | implemented at | test |
|---|---|---|
| "Smoke … separate run tags, never pooled" | cell names are constructed, never globbed; a `smoke` name is refused `dr/schema.py:437` | T: "smoke refused" |
| "no row is cut by storage; no exception or infrastructure-failure rows" | storage `dr/schema.py:386-395`; exception/infra counts per cell `dr/schema.py:466` → VOID rule | T: "storage-cut row", "exception rows > 1%" |
| "A cell is VOID and rerun from scratch … if more than 1% of its rows are infrastructure failures or exceptions" | `dr/run.py:104` (Parts A, B, C; halts, no readout); `dr/constants.py:82` | T: "exception rows > 1% -> VOID", "Part C exception rows > 1% -> VOID" |
| "Completeness. 9,120 rows per Part A cell, 6,000 for Part B, 1,520 / 1,000 per variant. A short cell is resumed, not analysed." (and Part C 4,560) | `dr/schema.py:475-495` raises `IncompleteCell`; `dr/constants.py:194-209` | T: "short cell", "Part C short cell" |
| "No success, invocation or failure-reason rate of any cell is computed before the freeze" | live mode refuses unless `--i-have-frozen` equals the package hash `dr/run.py:250`; the hash covers the package and the imported harness files `dr/run.py:52` | T: `test_live_mode_guard` |

## §8a Smoke record (consequences for the analysis)

| clause (quoted) | implemented at | test |
|---|---|---|
| "measured prompt plus clipped allowance against the 16,384-token window" | `dr/schema.py:272` | T: "clip beyond the window" |
| "delivered simulate … reported with these rows counted as failures and their share stated (`ctx_no_room_turns`)" | no-room rows grade False, reason `no_room` `dr/grade.py:124-126`; count and share per cell `dr/analysis.py:221`; readout E1 | `test_base_e1` (1 row, 1/6) |
| (no-room turn shape) "the row then has an empty answer with `done_reason = "length"`" (EXPERIMENTS_FLOW §9) | `dr/schema.py:407` (RefusedRow otherwise) | T: "no-room row with text" |
| "Clipped rows that later hit a no-room turn carry the clip count without the last-turn sizes" | sizes optional in `Tokens`; arithmetic only when both sizes exist `dr/schema.py:270-274` | fixture |

## §8b Clarifications fixed before the freeze

| item (quoted) | implemented at | test |
|---|---|---|
| 1 "Holm p-values come from an exact sign-flip test over the 20 domains; intervals from the domain-cluster bootstrap." | `dr/stats.py:71` (sign-flip), `dr/analysis.py:251`, `:257` | `test_stats_units`, `test_base_e2_e3` |
| 2 "R1–R3 use the unadjusted 95% interval." | `dr/analysis.py:357-387` read `ci95` (not `p_holm`) | `test_reading_rules` |
| 3 "'Inside [−5, +5]' includes the endpoints; 'entirely below −5' and 'entirely above +5' are strict." | `dr/stats.py:100`; `dr/analysis.py:360`, `:372` | `test_reading_rules` (−5.0 vs −5.01, inclusive ±5) |
| 4 "The unpaired share is measured against all keys in either corpus. A VOID cell counts as 'not met' … and its point estimate still enters the \|Δ̂\| > 10 check." | `dr/analysis.py:111`, `:113` (estimate always computed), `:164-165` | 2/7 VOID cell |
| 5 "A Gemma control cell 'fails' on any verdict other than 'criterion met', VOID included." | `dr/analysis.py:159` | `test_base_parity` |
| 6 "E3 pairs plain wording v with steered wording v+3 on the same fixture." | `dr/analysis.py:302` | `test_base_e2_e3` |
| 7 "R3's 'gain above +5' means the 95% lower bound is above +5." | `dr/analysis.py:383` | `test_reading_rules` |
| 8 "R4's population is trials with a correct tool result. 'Full, uncut' means `done_reason` is not 'length', no no-room turn, not cut by storage. Empty answers that stopped normally stay in and count as failures. Both arms are pooled per model; the point estimate is compared with 90%. If not met, the label is 'R4 condition not met'." | `dr/analysis.py:389-403`; label `:41` | `test_base_readings`, `test_r4_attributed` |
| 9 "R5's 'lower / higher by more than 5' use the point estimate; the middle row uses the 90% TOST. If no row applies, the label is 'No registered row applies'. Invocation is any tool call" | `dr/analysis.py:433-440`; label `:45`; `dr/schema.py:146` | `test_r5_paths` |
| 10 "§7 exception rows are `failure_reason` 'exception' or 'ollama_parse_error'; the 1% rule is applied per job cell and stops the whole analysis." | `dr/constants.py:82`; `dr/run.py:104` | T: both VOID refusals (the Part C one uses `ollama_parse_error`) |
| 11 "Duplicate trial keys stop the analysis. Half-written lines are counted and reported." | `dr/schema.py:462`, `:458`; readout corpus table | T: "duplicate key", torn line counted |
| 12 "The delivered rule is the overlay's `e2e_strict` rule with its markdown tolerances, applied identically to tool and no-tools rows (Part C)." | `dr/grade.py:134-188` (one code path for both; no-tools rows are not passed through their online grade) | T: Part C tolerant solve row graded True with stored `success` False |
| 13 "E4: 'refused or clipped final request' is classified first. Answers the mechanical rules cannot classify are labelled 'needs reading'" | `dr/e4.py:192-195`; `NEEDS_READING` returns in `dr/e4.py` | `test_base_e4` |
| 14 "'Clipped before a tool call' means a clipped turn that was not the last turn, or a clipped last turn when the tool loop ran out." | `dr/schema.py:161` | `test_clipped_logic` |
| 15 "Readout tripwire bands: tool-verified within ±30 points of canonical; delivered within [canonical low − 20, canonical high + 20 + … empty length-stopped answers + … leaked prefix]. A fired tripwire halts the readout until audited; the audit is recorded in the readout." | `dr/tripwires.py:39-40`, `:44-58`, `:97`; halt `dr/run.py:186-189`; audit recorded `dr/run.py` result `audited_tripwires` | `test_tripwires` |

## Freeze-protocol gates and tripwires

| commitment | implemented at | test |
|---|---|---|
| Gate 1: one typed loader; crash on unknown enum, missing key, wrong layer, wrong `prompt_style`, duplicate key | `dr/schema.py:296-422` (`parse_row`), `:434-467` (`load_cell`); result key set tied to `TaskResult` `dr/schema.py:68` | T: `test_refusals` (25 refusal cases) |
| Gate 1: no bare `.get()` / truthiness on grade fields in estimator code | the only `.get(` calls are on counters (`dr/schema.py`, `dr/stats.py`) and on MCP tool-result JSON in `dr/e4.py`; grades are compared with `is True` / typed bools | grep at freeze |
| Gate 2: registered constants as asserts | `dr/constants.py:164-214` | T: `test_registered_constants` |
| Gate 3: imports declared | numpy (requirements.txt); pydantic via pddl_eval; nothing else outside the stdlib | — |
| Gate 4: synthetic fixture with hand-computed values, refusals | `tests/fixtures/delivered_rerun/build_fixture.py`; T: whole file (323 checks) | `bash tests/verify.sh` |
| Canonical-vs-canonical dry run gives Δ = 0 in every cell | T: `test_canonical_dry_run` (30 tool cells; the Part C parity path on 12 no-tools cells) | passes, k = 20 |
| Tripwire: a guard firing in every cell | `dr/tripwires.py:66` (T1), `:69` (T2), `:101` (T5) | `test_tripwires` |
| Tripwire: a constant output column | `dr/tripwires.py:82` (T3; includes Part C delivered `:78`) | `test_tripwires` |
| Tripwire: rates outside a band justified from the canonical corpus | `dr/tripwires.py:44-58`, `:97` (T4); canonical counts `dr/constants.py` `CANONICAL_DELIVERED_COUNTS` | `test_tripwires`; band constants re-counted from the overlay in `test_canonical_dry_run` |

## Remaining notes (not blocking)

- The steering sentence of R5 has no registered complement in §5 or §8b; the code emits
  "Not shown (neutral-steered not within ±5 of minimal-steered)." (`dr/analysis.py:48`).
- Part C's delivered rate has no registered tripwire band (§8b item 15 names two bands);
  T3 covers it.
- §4 E2 still reads "no-tools (canonical `sweep5v2-live`, exact, v11–13)"; the code follows
  §2 Part C, which replaces that input.
- §6 (secondary, descriptive, "not gates") is not implemented. §7 run order and monitoring
  and §8 (job IDs, serving version, freeze record) are operational, not analysis code.
