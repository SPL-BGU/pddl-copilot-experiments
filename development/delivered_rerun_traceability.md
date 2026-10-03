# Delivered rerun: prereg clause → code traceability (freeze gate 3)

Freeze candidate of the analysis for `development/reference/delivered_rerun_prereg.md`
(branch `docs/reanalysis-and-rerun-prereg`, version `d32c5bf`: Part C in §2, §4 E2 now
from Part C, clarifications §8b items 1–16). Refreshed 2026-10-03 after the gate-5 review
fixes, before any outcome row of the rerun was read. Code: `tools/delivered_rerun/`
(abbreviated `dr/` below). Tests: `tests/test_delivered_rerun_analysis.py` (abbreviated
`T:`), fixture `tests/fixtures/delivered_rerun/`. Line numbers are at the commit that
carries this file; the sha256 table belongs to the freeze record (prereg §8) and is not
computed here. Every quote below is checked against prereg version `d32c5bf`.

Status: **no BLOCKING item.** Gate 5 (independent adversarial review) ran on 2026-10-03;
its findings F1–F6, N1–N5 and N8 are fixed and test-backed (list at the end).

## §2 Design and apparatus deltas (the parts the analysis must check)

| clause (quoted) | implemented at | test |
|---|---|---|
| §2 table, models: "`Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b`" / Part B "`gemma4:26b-a4b`" | `dr/constants.py:37` (tag → model id), `:42`; asserts `:207-208`; every row's model id checked `dr/schema.py:378` | T: `test_refusals` "row of another model" |
| §2 table, thinking: "off" | resume key must carry `off`: `dr/schema.py:373`; `dr/constants.py:46`, `:204` | T: "key disagrees with result" |
| §2 table, condition: "tools, all tools visible" | `tool_filter == "all"` `dr/schema.py:353`; `with_tools` per cell `:380` | fixture |
| §2 table, prompt style: "`minimal` (as canonical)" / "`neutral` (system prompt = role sentence only)" | per-cell `prompt_style`, refused otherwise `dr/schema.py:382` (RefusedRow) | T: "minimal row in neutral cell", "Part C row with neutral style" |
| §2 table, user-prompt variants: "11–13 (plain), 14–16 (steered)" | `dr/constants.py:59-60`, assert `:206`; per cell `dr/schema.py:387` | fixture |
| §2 table, tasks: "all five" / "validate_plan" | `dr/schema.py:385`; cell specs `spec_rerun_a` `:565`, `spec_rerun_b` `:574` | fixture |
| §2 table, trials: "3 × 9,120 = **27,360**" / "**6,000**" | `dr/constants.py:219-231`; completeness `dr/schema.py:520-541` | T: `test_registered_constants`, "short cell" |
| §2 table, run tag: "`delivered-rerun`" / "`delivered-rerun-neutral`" | `dr/constants.py:50-52`; cell names `dr/schema.py:545-555` | fixture |
| "3,000 trials per cell" (2 × 2) | `dr/constants.py:229` | T: R5 cell n |
| §2 table: "fixtures, ground-truth cache, budgets, context, temperature, seed" "as canonical `sweep5v2`" | live mode: ground-truth cache hash against the pinned canonical hash `dr/run.py:353`; domain/problem/plan files against a registered manifest digest `dr/run.py:82-98`, `:348`, `dr/constants.py:84-85` | T: `test_live_mode_guard` ("repo domains match the registered manifest", "an edited fixture file is refused") |
| Delta 1 "Final answers stored up to 65,536 characters (canonical: 500). A row records whether storage cut it. Registered expectation: zero rows cut." | `response_truncated_by_storage` must be a bool and False on every rerun row (RefusedRow), length ≤ 65,536: `dr/schema.py:426-436`; `dr/constants.py:69-70`; storage cuts per cell `dr/run.py:181-202` | T: "storage-cut row", "row missing a new field", `test_base_e1` storage cuts (7 rerun cells) |
| Delta 2 "the client now lowers the allowance to what actually fits" (prompt + allowance ≤ 16,384) | `dr/schema.py:288` (RefusedRow if exceeded); `dr/constants.py:71` | T: "clip beyond the window" |
| Delta 3 "A leading `<\|channel>thought\n<channel\|>` is removed from the text the grader reads." | `dr/grade.py:57-58` (asserts); harness extractors strip once; tolerant/table fallbacks read the once-stripped view `dr/grade.py:113`; E4 reads the same view; never stripped twice. Descriptive residue counts (never a wider strip): `dr/grade.py:83-97`, per E1 cell `dr/analysis.py:255-279`, per job cell `dr/run.py:181-202` | T: `test_grader_prefix`; `test_base_e1` "doubled prefix row", "marker after the verdict", "marker counts per rerun cell" |
| Part C "the three headline models, thinking off, no tools, v11–13, all five tasks, 3 × 4,560 = **13,680 trials**, same harness commit, tag `delivered-rerun`" | cell `slurm_vllm_<m>_off_no-tools_delivered-rerun` `dr/schema.py:553`, spec `:583` (no tools, `minimal`, v11–13, all tasks, rerun layer so the storage field is required); `dr/constants.py:52`, `:232-234` | T: "Part C row with a steered variant", "… with tool calls", "… missing the storage field", "Part C storage-cut row", "Part C short cell", "Part C format_compliant outside simulate" |
| Part C "**E2 now uses Part C as its no-tools side**, graded with the same delivered grader as the tool side, so both sides of every availability contrast are same-run, same-storage and same-grader. The canonical no-tools cells are no longer an input to E2." | `dr/analysis.py:325-346` (both sides through `dlv`, which reads `grade.grade` output; the no-tools side must be rerun-layer Part C rows, explicit raise `:335-339`); `dr/grade.py:147-207` grades tool and no-tools rerun rows with one code path and refuses canonical rows `:150` | T: `test_base_e2_e3` (all 15 computed), `test_grader_prefix` (Part C tolerant solve row: stored False, delivered True; canonical row refused) |
| Part C "**Part C parity check (reported, not a gate on E2).** Per model × task for solve and the three validate tasks (12 cells): Δ = Part C − canonical on the stored online `success`, paired, same TOST at ±5 with the 90% domain-cluster interval as §3. Simulate is excluded" | `dr/analysis.py:349-357` (the §3 `parity_cell` code path); `dr/constants.py:57`, `:211-212`; computed before any delivered grade `dr/run.py:247`; not consulted by E2 or the job rule; carried as a label on every E2 row `dr/analysis.py:216-220` | T: `test_part_c_parity` (Gemma solve −100/6, not met; 11 cells met; job verdict unchanged); dry run on canonical vs itself |
| Part C "If a cell fails, the paper says that the unaided baseline moved for that cell and by how much; E2 still uses Part C." | every E2 row and R1 carry the Part C cell's verdict (`input_cells`) `dr/analysis.py:344-345`; E2 is computed whatever the verdict | T: `test_base_e2_e3` "E2 input cells", "E2 simulate Part C side not checked" |
| §7 VOID rule for Part C cells | `dr/run.py:170-178` covers Parts A, B and C | T: "Part C exception rows > 1% -> VOID" |
| (apparatus fact, not a prereg quote) the no-tools arm is sampled under the per-task JSON constraint | `dr/analysis.py:48-55` (`E2_CAVEAT`, cites §2 Part C and §4 E2 for the same-run, same-grader statement), emitted `dr/run.py:286` and in the readout E2 header | T: "E2 caveat present" |

## §3 Parity guard

| clause (quoted) | implemented at | test |
|---|---|---|
| "evaluated before any delivered number is read" | `dr/run.py:246-247` parity is computed before any delivered grade exists (`:252-256`) | code order |
| "tool-verified success" | stored `success` (typed bool) `dr/analysis.py:120` | `test_base_parity` |
| "Model × task × arm (plain v11–13, steered v14–16): 3 × 5 × 2 = 30 cells." | `dr/analysis.py:152-199`; `dr/constants.py:92`, `:194` | `test_base_parity` |
| "Δ = rerun − canonical, paired on the trial key (domain, problem, variant, plan label)" | `Row.trial_key` `dr/schema.py:133`; `dr/analysis.py:111-121` | `test_base_parity` (Δ̂ = 100/12, 0) |
| "Rows missing from either corpus are counted and reported" | `dr/analysis.py:118`; readout column "unpaired" | 9B validate_domain plain: 1/1 |
| "a cell with more than 1% unpaired rows is VOID" | `dr/analysis.py:119`, `:122-125`; `dr/constants.py:99` | 2/22 → VOID |
| "Paired TOST at ±5 points: the 90% confidence interval of Δ, from a cluster bootstrap over the 20 domains (10,000 resamples, seed 20261002), lies inside [−5, +5]." | `dr/stats.py:96-104`, `dr/analysis.py:123-125`; `dr/stats.py:35-61` (k checked with an explicit raise naming the comparison `:49`; seed `:55`; resamples `:56`); `dr/constants.py:88`, `:93-95` | T: "bootstrap checks k"; dry run k = 20; Gemma vplan [0, 16.7] not met; 26 cells [0,0] met |
| "Secondary, reported beside it and not used for the verdict: the unpaired Newcombe 90% interval used by the `iss024d` parity prereg." | `dr/stats.py:107-119` (formula of `tools/iss024d_parity.py`); `dr/analysis.py:135` | Newcombe checked against an independent Wilson computation |
| "Gemma's 10 cells are evaluated before the Qwen cells." | evaluation order `dr/analysis.py:154-170`; the first ten evaluated cells are checked to be Gemma's against the literal tag, explicit raise `:171-179` | T: "gemma cells listed first"; `test_halts_with_context` "a non-Gemma first cell is refused" |
| "If any Gemma cell fails, F = max \|Δ̂\| over Gemma cells is reported as the noise floor." | `dr/analysis.py:168-169` | F = 100/12 |
| "Parity holds if at least 18 of the 20 Qwen cells meet the criterion and no cell of any model has \|Δ̂\| > 10 points." | `dr/analysis.py:180-184`; `dr/constants.py:89-91` | base: 18 → holds; `test_job_level_failure`: 17 and a gross cell → fails |
| "Parity holds: the rerun's delivered rates are reported as the exact delivered rates of the headline cells, with the apparatus deltas of §2 stated." | `dr/analysis.py:189`; deltas `dr/analysis.py:62-70`, emitted `dr/run.py:282` and in the readout | `test_base_parity` |
| "A cell fails: that cell's delivered rate is reported as a separate-apparatus measurement, labelled, with the failure shown. Wording is "criterion not met (unresolved)"." | `dr/analysis.py:191`; the label (verdict + consequence) is carried by every delivered number: E1 `RateCell` `dr/analysis.py:233-279`, E2/E3 rows (both input cells) `:325-382`, R1–R4 `input_cells` `:428-476`, via `StatusBook` `:201-220`; readout columns | `test_base_e1` "E1 labels match the parity table"; `test_base_e2_e3` "E2 input cells", "E3 input cells"; `test_base_readings` R1–R4 input cells |
| "Parity fails at job level: the whole rerun is reported as a separate-apparatus replication." | `dr/analysis.py:187` | `test_job_level_failure` |
| "The margin is not adjusted after the data are seen." | literal asserted at import `dr/constants.py:88`, `:191` | — |
| "Such movement is reported with the count of rows whose allowance was clipped before a tool call" | `Row.clipped_before_tool_call` `dr/schema.py:167-185`; per cell `dr/analysis.py:137` | `test_clipped_logic`; fixture counts (35B simulate plain, Gemma vdom plain) |

## §4 Primary endpoints

| clause (quoted) | implemented at | test |
|---|---|---|
| "All on **delivered success**: the final answer graded against the oracle, with the normalisation of §2 delta 3, exact (no censoring bounds)." | `dr/grade.py:147-207`; no censoring branch, every grade a bool; missing oracle or validator verdict raises (`:166`, `:180`, `:192`); empty answer fails `dr/grade.py:137-144`; harness exception rows fail `:155-158` | `test_base_e1`, `test_grader_prefix`, "no validator verdict" |
| E1 "Delivered rate per cell." "30 cells, with a domain-cluster bootstrap 95% interval." | `dr/analysis.py:255-279`; `dr/run.py:258` | `test_base_e1` (30 counts, 8 intervals) |
| E2 "Tools-plain (Part A) against no-tools (Part C), both from this run and graded with the same delivered grader, per model × task, paired on (domain, problem, variant, plan label)" | `dr/analysis.py:325-346`; zero unpaired rows required, explicit raise `:308-311`; column names "no-tools (C)" / "tools-plain (A)" `:301` | `test_base_e2_e3` (15 estimates, intervals, p, column names); T: "E2 unpaired rows halt" |
| E2 "domain-cluster bootstrap 95% interval, Holm across the 15 comparisons" | interval `dr/analysis.py:314`; Holm `:384-389` → `dr/stats.py:122-134` (explicit raise unless the family is 15) | `test_base_e2_e3`, `test_stats_units` Holm hand values |
| E3 "Tools-steered against tools-plain, both from this run, same pairing and intervals, Holm across 15." | `dr/analysis.py:360-381`; pairing v ↔ v+3 `:372`, `dr/constants.py:66`; zero unpaired rows required `dr/analysis.py:308-311`; column names "plain" / "steered" `dr/analysis.py:301` | `test_base_e2_e3`; T: "E3 unpaired rows halt" |
| E4 "Share of trials with a correct tool result whose delivered answer is wrong, per cell" | `dr/analysis.py:404-419` (population `success is True` `:406`) | `test_base_e4` |
| E4 "classified by the fixed categories of `reanalysis_transcripts.md` Q1 (no final answer, tool-input error, summary only, abridged, wrong wrapper, numeric omitted, wrong facts) plus "refused or clipped final request"" | `dr/e4.py:39-49` (`CATS`), decision order `dr/e4.py:188-206` | `test_base_e4` (every category exercised) |

## §5 Registered readings

| clause (quoted) | implemented at | test |
|---|---|---|
| R1 table: "interval entirely below −5" → "**Harm confirmed on the primary outcome.**"; "interval entirely inside [−5, +5]" → "**No delivered harm.**"; "anything else" → "**Unresolved.**" | `dr/analysis.py:428-437`; labels `:31-33` | `test_base_readings`; `test_reading_rules` (boundaries) |
| R2 "interval entirely above +5 = yes; entirely inside [−5, +5] = no; else unresolved" | `dr/analysis.py:440-449` | `test_base_readings`; `test_reading_rules` |
| R3 "The title stays "invocation is the bottleneck" only if R1 is "harm confirmed" or, failing that, E3 shows a delivered gain above +5 for at least two of the three models on validate_plan." | `dr/analysis.py:452-459`; `dr/constants.py:102` | `test_reading_rules` (via R1, two models, one model) |
| R4 "For solve, E4 among calling trials with a full, uncut final answer. If the share delivered correctly is at least 90% for each model" | `dr/analysis.py:462-476`; `dr/constants.py:101` | `test_base_readings` (11/11, 11/12, 9/11 → not met); `test_r4_attributed` |
| R5 "Invocation rate (share of trials with a tool call) and delivered success in the four cells of the 2 × 2." | `Row.invoked` `dr/schema.py:146`; `dr/analysis.py:479-497` | `test_base_readings` 2 × 2 |
| R5 table: "lower by more than 5 points" / "within ±5 (paired TOST as in §3)" / "higher by more than 5 points" | `dr/analysis.py:510-517` | `test_base_readings`; `test_r5_paths` (suppress, inert, no row) |
| R5 "if neutral-steered invocation is within ±5 of minimal-steered, steering in the user turn is sufficient by itself." | `dr/analysis.py:520` | `test_base_readings` |
| "No reading is added, dropped or re-thresholded after the data are seen." | labels are module constants at the top of `dr/analysis.py:21-47`; thresholds asserted in `dr/constants.py:189-213` | — |

## §7 Execution

| clause (quoted) | implemented at | test |
|---|---|---|
| "Smoke. … separate run tags, never pooled." | cell names are constructed, never globbed; a `smoke` name is refused `dr/schema.py:480` | T: "smoke refused" |
| "A cell is VOID and rerun from scratch (declared here, not a deviation) if more than 1% of its rows are infrastructure failures or exceptions." | rows counted once whether exception or infrastructure (`void_rule_rows`) `dr/schema.py:510-513`; rule `dr/run.py:170-178` (Parts A, B, C; halts, no readout); `dr/constants.py:100`, `:107` | T: "exception rows 2/102 > 1% -> VOID", "Part C exception rows > 1% -> VOID" |
| (the same rule, below the threshold) | harness exception rows parse in both layers, in exactly the two shapes `pddl_eval/runner.py` writes (client exception; scoring exception) `dr/schema.py:390-423`; they are analysed, graded as delivered failures `dr/grade.py:155-158`, counted per E1 cell `dr/analysis.py:274` and per job cell in the corpus table `dr/run.py:181-202` | `test_base_e1` "exception row: counted, a delivered failure, reported" (Gemma Part A, 1/102), "exception rows per cell" (incl. a canonical-layer row), "scoring-error rows per cell"; `test_exception_rows_parse` (shapes accepted and 10 refused look-alikes) |
| "Completeness." "9,120 rows per Part A cell, 6,000 for Part B, 1,520 / 1,000 per variant. A short cell is resumed, not analysed." (and Part C 4,560) | `dr/schema.py:520-541` raises `IncompleteCell`; `dr/constants.py:219-234` | T: "short cell", "Part C short cell" |
| "No success, invocation or failure-reason rate of any cell is computed before the freeze in §8." | live mode refuses unless `--i-have-frozen` equals the package hash `dr/run.py:338`; the hash covers the package and every imported repo module `dr/run.py:56-79` | T: `test_live_mode_guard` ("DEPENDENCIES cover every imported repo module") |

## §8 Freeze record (pins the analysis checks at run time)

| clause (quoted) | implemented at | test |
|---|---|---|
| "Tools repo `pddl-copilot` at `5e4f9c0` (same commit as the canonical corpus)" | live mode: marketplace HEAD must start with the pin and have no uncommitted change under `plugins/` `dr/run.py:101-123`, `:347`; `dr/constants.py:78`; `--marketplace-path` has no default and is required in live mode `dr/run.py:341-345` | T: "pinned marketplace HEAD accepted", "other marketplace HEAD refused", "pinned HEAD with edited plugin code refused", `marketplace_state` on a temporary git repo, "live mode requires gt cache and marketplace path" |
| "frozen under `/freeze-protocol` (typed load boundary, registered constants as asserts, …)" | asserts cannot be stripped: the package refuses to import under `python -O` `dr/__init__.py:7-13`, `dr/constants.py:28-31` | T: "python -O refused" (package, a module, the entry point) |

## §8a Smoke record (consequences for the analysis)

| clause (quoted) | implemented at | test |
|---|---|---|
| "on rows whose allowance was clipped, measured prompt plus clipped allowance against the 16,384-token window" | `dr/schema.py:288` | T: "clip beyond the window" |
| "delivered simulate for the open-weight tool arms is reported with these rows counted as failures and their share stated (`ctx_no_room_turns`)" | no-room rows grade False, reason `no_room` `dr/grade.py:137-144`; count and share per cell `dr/analysis.py:255-279`; readout E1 | `test_base_e1` (1 row, 1/6) |
| (no-room turn shape, `pddl_eval/chat.py`) an empty answer with `done_reason = "length"` | `dr/schema.py:448-454` (RefusedRow otherwise) | T: "no-room row with text" |
| "Clipped rows that later hit a no-room turn carry the clip count without the last-turn sizes" | sizes optional in `Tokens`; arithmetic only when both sizes exist `dr/schema.py:286-290` | fixture |

## §8b Clarifications fixed before the freeze

| item (quoted) | implemented at | test |
|---|---|---|
| 1 "Holm p-values come from an exact sign-flip test over the 20 domains; intervals from the domain-cluster bootstrap." | `dr/stats.py:74-93` (sign-flip), `dr/analysis.py:314`, `:322` | `test_stats_units`, `test_base_e2_e3` |
| 2 "R1–R3 use the unadjusted 95% interval." | `dr/analysis.py:428-459` read `ci95` (not `p_holm`) | `test_reading_rules` |
| 3 ""Inside [−5, +5]" includes the endpoints; "entirely below −5" and "entirely above +5" are strict." | `dr/stats.py:104`; `dr/analysis.py:431`, `:443` | `test_reading_rules` (−5.0 vs −5.01, inclusive ±5) |
| 4 "The unpaired share is measured against all keys in either corpus. A VOID cell counts as "not met" in the 18/20 rule, and its point estimate still enters the \|Δ̂\| > 10 check." | `dr/analysis.py:119`, `:121` (estimate always computed), `:180-184` | 2/22 VOID cell |
| 5 "A Gemma control cell "fails" on any verdict other than "criterion met", VOID included." | `dr/analysis.py:168` | `test_base_parity` |
| 6 "E3 pairs plain wording v with steered wording v+3 on the same fixture." | `dr/analysis.py:372` | `test_base_e2_e3` |
| 7 "R3's "gain above +5" means the 95% lower bound is above +5." | `dr/analysis.py:454` | `test_reading_rules` |
| 8 "R4's population is trials with a correct tool result. "Full, uncut" means `done_reason` is not "length", no no-room turn, not cut by storage. Empty answers that stopped normally stay in and count as failures. Both arms are pooled per model; the point estimate is compared with 90%. If not met, the label is "R4 condition not met"." | `dr/analysis.py:462-476`; label `:41` | `test_base_readings`, `test_r4_attributed` |
| 9 "R5's "lower / higher by more than 5" use the point estimate; the middle row uses the 90% TOST. If no row applies, the label is "No registered row applies". Invocation is any tool call (reproduces the canonical 622/3,000)." | `dr/analysis.py:510-517`; label `:45`; `dr/schema.py:146` | `test_r5_paths` |
| 10 "§7 exception rows are `failure_reason` "exception" or "ollama_parse_error"; the 1% rule is applied per job cell and stops the whole analysis." | `dr/constants.py:107`; `Row.is_exception` `dr/schema.py:156`; rule `dr/run.py:170-178`; rows below the threshold are analysed (see §7 above) | T: both VOID refusals (the Part C one uses `ollama_parse_error`); `test_base_e1` exception counts |
| 11 "Duplicate trial keys stop the analysis. Half-written lines are counted and reported." | `dr/schema.py:505`, `:501`; readout corpus table | T: "duplicate key", torn line counted |
| 12 "The delivered rule is the overlay's `e2e_strict` rule with its markdown tolerances, applied identically to tool and no-tools rows (Part C)." | `dr/grade.py:147-207` (one code path for both; no-tools rows are not passed through their online grade) | T: Part C tolerant solve row graded True with stored `success` False |
| 13 "E4: "refused or clipped final request" is classified first. Answers the mechanical rules cannot classify are labelled "needs reading" and read by hand after the freeze, with the reading recorded." | `dr/e4.py:192-195`; `NEEDS_READING` returns in `dr/e4.py` | `test_base_e4` |
| 14 ""Clipped before a tool call" means a clipped turn that was not the last turn, or a clipped last turn when the tool loop ran out." | `dr/schema.py:167-185` (loop ran out = `failure_reason` "loop_exhausted", or `done_reason` "tool_calls" on a trial the tool result made a success) | `test_clipped_logic`; fixture Gemma vdom plain (dA,p02,v11) counted |
| 15 "Readout tripwire bands: tool-verified within ±30 points of canonical; delivered within [canonical low − 20, canonical high + 20 + canonical share of empty length-stopped answers + share with the leaked prefix]. A fired tripwire halts the readout until audited; the audit is recorded in the readout. Part C's delivered rate has no band of its own; it is covered by the constant-column tripwire and by the Part C parity table." | bands `dr/tripwires.py:39-53`, `:84-97`; halt `dr/run.py:268-272`; a release needs `--audit-notes FILE` with one non-empty note per released id `dr/run.py:126-143`, notes embedded verbatim in the JSON `dr/run.py:279` and the markdown `dr/readout.py:27-34`; Part C under T3 `dr/tripwires.py:78` | `test_tripwires` (halt, release without notes refused, empty note refused, notes for another id refused, audited run embeds the note verbatim) |
| 16 "R5's steering sentence, when neutral-steered is not within ±5 of minimal-steered, reads "Not shown (neutral-steered not within ±5 of minimal-steered)"." | `dr/analysis.py:47` (character for character, no trailing period), used `:520` | `test_base_readings` "R5 complement labels are the §8b text" |

## Freeze-protocol gates and tripwires

| commitment | implemented at | test |
|---|---|---|
| Gate 1: one typed loader; crash on unknown enum, missing key, wrong layer, wrong `prompt_style`, duplicate key | `dr/schema.py:312-463` (`parse_row`), `:477-513` (`load_cell`); result key set tied to `TaskResult` `dr/schema.py:68` | T: `test_refusals` (27 refusal cases), `test_exception_rows_parse` |
| Gate 1: no bare `.get()` / truthiness on grade fields in estimator code | the only `.get(` calls are on counters (`dr/schema.py`, `dr/stats.py`) and on MCP tool-result JSON in `dr/e4.py`; grades are compared with `is True` / typed bools | grep at freeze |
| Gate 2: registered constants as asserts | `dr/constants.py:189-239`; refusing `python -O` keeps them live `dr/__init__.py:7-13` | T: `test_registered_constants`, "python -O refused" |
| Gate 3: imports declared | numpy, pydantic (direct import of the frozen `pddl_eval/schemas.py`), mcp, openai in `requirements.txt`; nothing else outside the stdlib | T: `test_requirements_cover_frozen_imports` |
| Gate 4: synthetic fixture with hand-computed values, refusals | `tests/fixtures/delivered_rerun/build_fixture.py`; T: whole file (396 checks) | `bash tests/verify.sh` |
| Canonical-vs-canonical dry run gives Δ = 0 in every cell | T: `test_canonical_dry_run` (30 tool cells; the Part C parity path on 12 no-tools cells) | passes, k = 20 |
| Tripwire: a guard firing in every cell | `dr/tripwires.py:65-69` (T1, T2), `:99-103` (T5) | `test_tripwires` |
| Tripwire: a constant output column | `dr/tripwires.py:71-82` (T3; includes Part C delivered `:78`) | `test_tripwires` |
| Tripwire: rates outside a band justified from the canonical corpus | `dr/tripwires.py:44-53`, `:84-97` (T4); canonical counts `dr/constants.py:143` `CANONICAL_DELIVERED_COUNTS` | `test_tripwires`; band constants re-counted from the overlay in `test_canonical_dry_run` |

## Gate-5 review findings (2026-10-03), all fixed before the freeze

| id | fix | test |
|---|---|---|
| F1 | harness exception rows parse in both layers in the exact runner shapes and reach the §7 rule; below 1% they are analysed and reported | `test_exception_rows_parse`; `test_base_e1` exception and scoring-error counts; "exception rows 2/102 > 1% -> VOID" |
| F2 | DEPENDENCIES cover `pddl_eval/domains.py`, `pddl_eval/resume.py`, `run_experiment.py`, the `__init__.py` files; domain-file manifest digest checked; marketplace pinned and clean; `--marketplace-path` required | `test_live_mode_guard` |
| F3 | `--audit-notes` required to release a tripwire; notes verbatim in JSON and markdown | `test_tripwires` |
| F4 | parity verdict and consequence on E1, E2/E3 (both inputs), R1–R4 | `test_base_e1`, `test_base_e2_e3`, `test_base_readings` |
| F5 | E2 columns "no-tools (C)" / "tools-plain (A)", E3 "plain" / "steered", in markdown and JSON | `test_base_e2_e3` |
| F6 | `done_reason == "tool_calls"` counts as the loop running out | `test_clipped_logic`; `test_base_parity` clipped counts |
| N1 | `python -O` refused; bootstrap, Holm, TOST and E2 checks raise named errors with the comparison in the message | "python -O refused"; `test_halts_with_context` |
| N2 | this file refreshed against prereg `d32c5bf`; `E2_CAVEAT` cites §2 Part C and §4 E2 for the same-grader statement only; `R5_STEER_NOT` matches §8b item 16 | `test_base_readings` |
| N3 | per E1 cell and per job cell: answers with the exact prefix, with it doubled, and with a marker left after the strip (descriptive; strip unchanged) | `test_base_e1` |
| N4 | the first ten evaluated parity cells are checked to be Gemma's | `test_halts_with_context` |
| N5 | E2 and E3 halt on any unpaired row | "E2 unpaired rows halt", "E3 unpaired rows halt" |
| N8 | pydantic added to `requirements.txt` | `test_requirements_cover_frozen_imports` |

## Remaining notes (not blocking)

- §6 (secondary, descriptive, "not gates") is not implemented beyond the clipped-allowance
  counts and the no-room shares. §7 run order and monitoring and §8 (job IDs, serving
  version, freeze record) are operational, not analysis code.
- A scoring exception on a trial whose tool loop also ran out is stored with
  `failure_reason` "loop_exhausted" (the harness's override order), so by §8b item 10 it is
  not a §7 exception row. It is parsed, graded on its answer, and counted in the corpus
  table's "scoring-error rows" column.
