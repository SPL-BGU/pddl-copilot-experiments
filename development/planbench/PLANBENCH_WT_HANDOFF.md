# PlanBench with-tools arm — handoff (state as of 2026-08-01)

> **STATUS: ratified, built, calibrated once, and HELD at the calibration gate.**
> **$1.09 spent to date. The confirmatory run has not been launched.**
>
> **Read in this order:** this header → `planbench_wt_calibration_20260730.md` (the gate
> result and the two defects blocking the run) → `planbench_wt_prereg.md` §10-R (signature,
> slot answers, amendments K/L/M/N).
>
> **Gate verdict, 2026-07-30: FIX APPARATUS AND RESTART.** Cost and throughput passed. The
> outcome-neutral extraction check failed on 2 of 4 cells, and prereg §3 classifies that as
> an apparatus-fix-and-restart event, not a scope decision. Details and the two mechanisms
> are in the calibration memo; they are **not** re-derived here.
>
> **Superseded numbers — do not use the older figures further down this document:**
> - **n = 600 per cell, not 500** (amendment K). The 500 pool was the 4- and 5-block portion
>   of the published set; `blocksworld_3` holds the 100 3-block instances; the union is
>   PlanBench's 600, confirmed by 157/500 + 49/100 = 206/600 = the published 34.3%. Band
>   cutpoints at n=600: NO-RESCUE x ≤ 19, PARTIAL 41..275, RESCUE x ≥ 325. The bare-NT layer
>   owes 200 completion trials.
> - **Budget is $170** (Omer, 07-30), not the ~$70.6 bookkeeping figure.
> - **Run cost is $32.78 measured**, not the $55.02 the prereg projected. Derived from
>   measured per-trial cost at 600/cell; see the calibration memo for the per-cell figures.
> - **Amendment N:** only the task-format clause is shared across arms. The NL→PDDL step
>   moved into the tools policy.
>
> **UPDATE 2026-08-01 (restart work done, see prereg §10-R "Restart record 1"):**
> - **Format clause v2 is drafted** in `planbench/engine.py` fixing both calibration
>   defects (word-for-word example phrasing + answer must start with `[PLAN]`);
>   machine checks re-pass (shared suffix byte-identical, no tool reference, 176-char
>   arm-A delta preserved). Awaiting Omer's re-freeze at the restart record's ANSWER slot.
> - **VAL is RESOLVED** — the 07-30 blocker was a wrong path (a Linux ELF). The Mach-O
>   x86_64 build at `external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate`
>   runs under Rosetta, is the same build that graded the NT layer, and passed positive +
>   negative controls. `VAL=<repo>/external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables`.
> - **Concurrency: DECIDED sequential** (Omer, 2026-08-01) — apparatus unchanged from
>   what the calibration measured; the confirmatory run is ~12 h overnight.
> - **2026-08-01 second pass:** the v2 clause got one pre-freeze disambiguation
>   ("phrased exactly as the example phrases its actions", not "copying ... word for
>   word" — the copy phrasing risked copy-the-example-PLAN, which the outcome-blind gate
>   cannot detect). Final text is quoted verbatim in the restart record; machine checks
>   re-pass. Recommendations are recorded in the prereg for both open slots: freeze the
>   quoted text, and accept amendment M as worded (journal-fitness reasoning inline).
>
> **2026-08-01 (third pass): ALL SLOTS CLOSED.** Format clause v2 FROZEN (Omer);
> amendment M ACCEPTED as worded (Omer) — §7's first bullet is amended, GPT-4 may appear
> as a labelled published reference line, still never as a comparator arm. Concurrency
> decided sequential.
>
> **2026-08-01 (fourth pass): CALIBRATION RUN 2 DONE — $1.13, cumulative $2.22.** Memo:
> `planbench_wt_calibration_run2_20260801.md`. Both restart defects FIXED (Mystery tools
> extraction 15→90%; Mystery matched-NT injection 65→0%). Cost/throughput pass; projection
> at 600/cell = **$34.08 measured**, wall-clock **≈7.3 h** sequential (supersedes the 12 h
> figure). Ordinary/tools reads 75% extraction, but all 5 misses are the run-1 memo's
> NOT-a-defect class (honest empty plans on solvable instances; extraction of delivered
> plans 15/15) — no apparatus fix exists that wouldn't bias the task. Run-1 artifacts
> archived under `.local/calib/archive-20260801-103650/`; analyzer at
> `.local/calib/analyze_calib.py` (validated by reproducing run 1's published numbers).
>
> **THE ONLY REMAINING GATE: Omer's scope-and-spend approval on the measured $34.08**,
> which is also where he signs off the 75% gate reading. After that: the 600/cell run
> (~7.3 h), grade with Rosetta VAL, results memo per prereg §6.
>
> Do not reopen a slot that §3 below records as decided.
>
> **Git:** branch `planbench-wt-significance-brief`, 9 commits ahead of `main`, unmerged, no
> PR (project convention for doc/handoff artifacts). Tag `prereg-planbench-wt-v1` marks
> ratification. Do not touch `31b84ab` (nt-ster H4 prereg) — parallel session.
>
> **Machine-local artifacts NOT in git** (`external/` and `.local/` are both gitignored, so a
> fresh clone will not have these):
> - `.local/calib/` — the four side-log JSONLs, `smoke_wt.jsonl`, `run_calib.sh`,
>   `calib_run.log`, and `calib_manifest.json` (the discarded calibration draw: example
>   source id 134, 20 target source ids).
> - `external/LLMs-Planning/plan-bench/configs/{blocksworld,mystery_blocksworld}_calib.yaml`
> - `external/LLMs-Planning/plan-bench/instances/blocksworld/{,mystery/}calib_basic/` (21
>   files each: `instance-1` is the one-shot example, `instance-2..21` the targets)
> - `external/LLMs-Planning/plan-bench/{responses,results}/{blocksworld,mystery_blocksworld}_calib/`
> - `.venv-planbench-wt/` — rebuild with `planbench/requirements-wt.txt`
>
> **Environment the calibration ran under** (all four are required; the run script
> `.local/calib/run_calib.sh` sets them):
> `PDDL_MARKETPLACE_PATH=/Users/omereliyahu/personal/pddl-copilot`,
> `PDDL_PLANBENCH_PLUGINS="pddl-solver pddl-validator"`, `PDDL_COPILOT_TASK=t1`,
> `FAST_DOWNWARD=/Users/omereliyahu/personal/pddl-copilot/plugins/pddl-solver/.venv/lib/python3.14/site-packages/up_fast_downward/downward`,
> plus `PDDL_COPILOT_TOOLLOG` per cell and `ANTHROPIC_API_KEY`.
>
> **`apply_patches.py main()` cannot be run end-to-end on this tree:** `patch_init`'s anchor
> no longer matches (`utils/__init__.py` imports `openai` unguarded; we satisfied that by
> installing `openai` in the venv instead) and it `sys.exit`s before later patches run. Patch
> 6 (the instance-id stamp) was applied by calling `patch_instance_id_stamp` directly. It is
> applied and idempotent on this tree.
>
> **Suggested entry point:** `/resume-verify development/planbench/PLANBENCH_WT_HANDOFF.md`

## 1. What this arm is and where it sits

Act 4 of the journal paper re-measures PlanBench on a 2026 frontier model. The
**no-tools layer is finished and graded** (`planbench_frontier_haiku_nt.md`, 06-22 run,
07-23 grading) and it carries Act 4's headline: Haiku 4.5 beats GPT-4 on blocksworld
plan generation CI-disjoint (41.0 [36.8,45.4] vs 31.4 [27.5,35.6]), the Mystery collapse
replicates (41.0 → 0.8), the t2 silent-0.0 artifact is fixed, and t7 quantifies a
chat-format grading disease. **This arm cannot strengthen or weaken any of that** — §1 of
the prereg fixes that by design.

The WT arm carries a labelled **secondary** claim: the funnel replicates when the model
operates the prescribed remedy on the field's own instrument. Its real value to the paper
is that it is the only place the tools claim is tested on an instrument we did not build,
which pre-empts the "you designed the benchmark your method wins on" objection for ≈$46.
Be honest about its ceiling: the bare "tools rescue Mystery" result is already published
at least four times, so the novelty is the **matched-scaffold single ablation**, the
formalization-boundary metric, the delegation-rate mediator, and accuracy-vs-dollars —
not the direction of the effect.

**Binding documents, in precedence order:**
1. `development/planbench/planbench_wt_prereg.md` — the protocol. Binding once signed.
2. `development/planbench/planbench_wt_prereg_decisions.md` — reasoning, provenance,
   rejected alternatives, and two findings that live outside the prereg (§7 below).
3. `development/journal_decisions_memo.md` §4 — the accepted D-J3 ruling this implements.
4. `development/planbench/planbench_frontier_haiku_nt.md` — the graded NT layer.
5. `development/planbench/PLANBENCH_HANDOFF_v3.md` — superseded direction (small-model
   scaffolding), kept for its cluster/ops lessons only.

## 2. The design (all slots answered; awaiting signature only)

| | |
|---|---|
| cells | **4** — {blocksworld, mystery_blocksworld} × {with-tools, matched-no-tools}, task t1 only |
| n | **500 per cell**, the whole t1 pool (ids 2..501). No subsampling, no seed, no strata |
| model | `claude-haiku-4-5`, single tier (owned as a limitation) |
| tools | harness roster: pddl-solver + pddl-validator, **7 tools** (`run_experiment.py:122`) |
| backend | adapter over `tools/frontier_runner.py` (SDK Tool Runner), `MAX_TOOL_LOOPS`=10 |
| PDDL | **model-authored** domain + problem + plan; nothing injected |
| cost | ≈$46 central; ≈$52 with the sensitivity arm and calibration (73% of the ~$70.6) |
| confirmatory | 2 paired exact-McNemar tests (clean, Mystery), Holm within family, α=0.05 |
| predictions | (i) Mystery outcome band, (ii) two-branch mechanism test. **(iii) STRUCK** |
| kill date | **2026-08-15** → converts to pre-registered future work inside an NT-only Act 4 |

## 3. Decided — do not reopen

| what | decision | when |
|---|---|---|
| sample | whole pool, 500/cell, no subsampling | Omer, 07-25 |
| scope | **shape B**: t1 2×2 only; t3 pair out; prediction (iii) struck per the linkage rule | Omer, 07-26 |
| t2 | stays excluded, as a **scope** decision — option closed, not deferred | Omer, 07-26 |
| PDDL authorship | model authors domain + problem + plan | Omer, 07-26 |
| spend guard | **no runner-side cap.** The account is prepaid per experiment with no real-time billing, so the loaded balance is the ceiling and `frontier_runner`'s existing "credit balance too low" break is the stop | Omer, 07-26 |
| amendments | §9 A-D and F-I accepted; **E rejected** and rewritten as the prepaid-balance clause | Omer, 07-26 |
| bands | four-outcome partition (NO-RESCUE / PARTIAL / RESCUE / INCONCLUSIVE), cutpoints in counts | prereg §3 |
| clean-t1 check | outcome-neutral, thresholded on the two decomposed quantities (extraction ≥90%, correct-given-extracted ≥90%); raw delivered stays the reported primary | prereg §3 |
| funnel placement | input boundary as a new **leading bar** in the with-tools cascade; CALL-extension rejected on measurement | prereg §4 |

If a fresh reading tempts you to revisit one of these, read the decisions memo section
that argues it before raising it. Each was adjudicated against measured evidence, and two
(t2 rationale, CALL extension) were decided **against** the 07-24 draft's own stated
reasoning because that reasoning was factually wrong.

## 4. Verified facts — do NOT re-derive

A 7-agent read-only evidence workflow (~1.8M tokens) produced these, and the load-bearing
ones were re-verified by hand. Raw per-agent output survives at
`~/.claude/projects/-Users-omereliyahu-personal-pddl-copilot-experiments/37e4225c-19f4-4605-b37d-dfad9c8fd1ec/subagents/workflows/wf_08c98872-d6e/journal.jsonl`
(7 `{"type":"result"}` lines; the decisions memo carries the conclusions with provenance).

**Corpus (measured on disk).** t1 pool ids 2..501, t3 pool ids 1..500, intersection 499 —
this is why the 07-24 "one shared subsample" premise failed, and why the whole pool makes
it moot. Mystery is a **pure symbol rename with an identity object mapping**, verified at
501/501 instance files, 500/500 t1 gold plans (identical lengths), 500/500 t3 candidate
plans, 500/500 t3 verdicts — so clean-vs-Mystery is exactly paired and the §2 pre-lock
check is recorded PASSED. Gold plan lengths take 8 even values {2:30, 4:56, 6:114, 8:139,
10:113, 12:46, 14:1, 16:1}. `instances/blocksworld/mystery/generated_basic` holds a stray
mystery-only `instance-0.pddl` that is **not** a rename of anything: never enumerate the
pool by directory glob. Graded-NT `query` strings are byte-identical to `prompts/*.json`
for 500/500 in all four graded cells.

**NT anchors (recomputed from the on-disk grading fields, all six reproduce exactly).**
bw t1 205/500 = 41.0 [36.8,45.4] · bw t3 391/500 = 78.2 · mystery t1 4/500 = 0.8 [0.3,2.0]
(all four successes have gold plan length 2) · mystery t3 227/500 = 45.4 · GPT-4 bw t1
157/500 = 31.4. Extraction: clean t1 472/500 = **94.4%**, mystery t1 448/500 = 89.6%;
accuracy given extraction 205/472 = 43.4% clean.

**Cost anchors (measured, from our own frontier WT corpora).** Haiku with-tools
$0.02097/trial over 1520 trials ($31.87 total, caching saved 24.8%); the `solve` cell —
the closest analogue — $0.04557/trial at 4.48 turns. loop_exhausted 1/4560 trials.
PlanBench prompts are far smaller than our suite's: bw t1 ≈726 tok, mystery t1 ≈617 tok.
Projected PlanBench WT: bw t1 $0.0348/trial, mystery t1 $0.0412; matched-NT $0.0074 and
$0.0083. Four independent models put the arm between $25 and $60; the gate settles it.

**Statistics (recomputed locally).** Band cutpoints at n=500: NO-RESCUE x ≤ 15, PARTIAL
x ∈ [35,228], RESCUE x ≥ 272, INCONCLUSIVE 16..34 or 229..271 (62/500 outcomes). Surviving
confirmatory power at the whole pool: Mystery ≥0.95 against any WT rate ≥5%, clean ≥0.99
against any WT rate ≥60%. Equivalence margin ±7.5pp is certifiable at n=500 up to total
discordance ψ=0.33; ±5pp is not pre-registrable at any affordable n.

**Code (each verified directly, not inferred).** `REQUIRED_PLUGINS` = solver + validator
only (`run_experiment.py:122`). `_parse_engine_name` allowlist is
`{ollama, vllm, vllm-base, vllm-tools, anthropic}` and raises otherwise
(`planbench/engine.py:~105`). `PDDL_COPILOT_RENDER_FROM_TOOLS` defaults to `"1"`
(`engine.py:393`). `classic_planner(strategy="astar_lmcut")` = `astar(lmcut())`, optimal
(`solver_server.py:247,411`). `WITHOUT_TOOLS_SYSTEM_BY_TASK` exists as a length-matched
mirror (`pddl_eval/prompts.py:110`, test-enforced). `MAX_TOOL_LOOPS` = 10
(`pddl_eval/chat.py:29`). `response_evaluation.py` is **patched in place** by
`planbench/apply_patches.py` (patch 5 A/B/C) — the same build that graded the NT layer.

**External (spot-verified 2026-07-25).** Göbel et al. arXiv:2603.06064 ran **Haiku 4.5**
with PDDL tools over MCP on 102 IPC Blocksworld instances: 63.7% → 66.7% (+3.0pp) at 5.7×
token cost, because the tool exposed a step-wise simulator and the model kept the search.
Huang & Zhang ACL 2025 (arXiv:2412.09879) find formalizers robust to lexical perturbation.
Everything else in the literature block of the decisions memo is **unverified** — run
`/verify-claims` before any of it enters prose.

## 5. Traps that produce wrong numbers silently

1. **`PDDL_COPILOT_RENDER_FROM_TOOLS` defaults to `1`**, which renders the answer from the
   last parseable tool result and never reads the model's final message. Left alone, a
   cell measures tool-verified instead of delivered, contradicting the D-J2 ruling. Pin
   it to `0` for every cell.
2. **`build_table.acc()` divides by `len(instances)`** regardless of what was run. Inert
   at the whole pool, fatal on any subsampled path: a 250-instance replay reports a
   believable 22.2% where the truth is 44.4%. The audit asserts denominator = realized n.
3. **The upstream extractor biases against this arm.** A plan pasted from
   `classic_planner` extracts to nothing (`(unstack a b)` tokenizes as `(unstack`);
   markdown bolding extracts to nothing; shorthand action names extract to nothing; and
   **one narrating sentence before the plan injects a duplicated action** that VAL then
   rejects. The frozen format clause must demand the plan block as the entire answer in
   PlanBench's own NL phrasing. A NO-RESCUE verdict on Mystery may not be called a
   formalization result until the extraction-injection audit has run on that cell.
4. **Never `--run_till_completion`.** A loop-exhausted trial returns an empty answer,
   which PlanBench retries forever at temperature 0 — an unbounded paid loop.
5. **Never `--ignore_existing` against `pddl_copilot__anthropic__claude-haiku-4-5`.** It
   would overwrite the graded 06-22 NT corpus. Use the new engine names in §6.
6. **Do not pass `--specific_instances` to `response_evaluation.py`** — its filter mutates
   a module-level list and silently grades everything after the last matched id.
7. **Prompt caching is on a knife edge** (~5% margin over Haiku's 4096-token minimum) and
   the matched-NT arm cannot cache at all. It is a billing-layer property only, explicitly
   outside the "identical apparatus" clause; the gate records the runner's verdict.

## 6. Owed work, in order — ONLY after RATIFY

> **BUILD STATUS 2026-08-01.** Items 1-3 done and exercised end-to-end by the calibration
> run. Item 4 (scaffold) is written and was run, but the calibration found two defects in it,
> so it is **not** frozen. Item 5 (calibration) has been run once — $1.09, 80 trials, verdict
> RESTART. Items 6-8 not started.
>
> Superseded detail from 07-30 follows; the item 1-3 descriptions are still accurate.
>
> **BUILD STATUS 2026-07-30 (ratified; items 1-3 DONE, nothing spent).**
> - **Item 1 adapter — DONE.** `planbench/engine.py`: `anthropic-tools` (SDK Tool
>   Runner over `MCPPlanner`, same `runner_tools` shape and `"Tool error: {exc}"`
>   string as `tools/frontier_runner.py`) and `anthropic-scaffold` (matched no-tools
>   control). Instance-id stamping via `apply_patches.py` **patch 6** +
>   `query_sha256` fallback, so the §4 formalization metric is now measurable.
>   Trap 1 is structurally unreachable on the WT path: rendering-from-tools is
>   bypassed in code, not by env var, because the prereg endpoint is *delivered*.
>   Per-instance token usage is logged so the calibration gate can compute its
>   headline p90-output-tokens observable.
> - **Item 2 engine names + allowlist — DONE.** Both tokens added to
>   `_parse_engine_name`; no `_chat` substring; `build_table` rows registered plus
>   the `blocksworld_3` / `mystery_blocksworld*` configs amendment K needs.
> - **Item 3 environment — DONE.** `.venv-planbench-wt` (gitignored) from
>   `planbench/requirements-wt.txt`. **Pins are apparatus identity:**
>   `anthropic==0.109.2` (the version that produced the graded frontier WT corpora)
>   and `mcp==1.26.0` (a bare install resolves 2.0.0 — a major bump under the
>   shared tool-execution component). Full PlanBench generation + evaluation import
>   chain verified green.
> - **Item 4 scaffold — DRAFTED, awaiting Omer's freeze.** `_pb_scaffold()` in
>   `engine.py`. Amendment-A compliant and machine-checked: shared block
>   byte-identical across arms, no tool name in it, policy sentences mirrored
>   (698 vs 696 chars). Extraction-safe per trap 3.
> - **Next: item 5 calibration (≈$1.50) — needs the scaffold frozen first.**


1. **Adapter** over `tools/frontier_runner.py` driving PlanBench t1 (~1 agent-day). It
   must stamp the **instance id into every logged tool call** — without that the §4
   formalization metric is unmeasurable and the prereg names a stage it cannot test. The
   existing `PDDL_COPILOT_TOOLLOG` side-log cannot be joined (`query[:200]` has one
   distinct value across all 500 instances).
2. **Engine names + allowlist:** `pddl_copilot__anthropic-tools__claude-haiku-4-5` and
   `pddl_copilot__anthropic-scaffold__claude-haiku-4-5`; add the backend tokens to
   `_parse_engine_name`; no `_chat` substring. Add `build_table` engine entries.
3. **Environment:** no existing venv can run WT generation (the PlanBench venv lacks
   `mcp`; the repo venv lacks `tarski`/`pddl`/`transformers`). Pin the `anthropic` version
   deliberately — 0.109.2 and 0.111.0 are both on this machine.
4. **Scaffold text**, frozen at the gate: NL→PDDL step + task-format clause shared
   byte-identical across arms, tool-use policy sentence mirrored for the no-tools arm, no
   tool name in the shared clause.
5. **Calibration**, ≈$1.50: 20 clean + 20 Mystery instances **disjoint from the graded set
   and discarded**. Headline observable is **p90 output tokens per trial**. Decision
   function reads cost and throughput only — never accuracy, never the contrast.
6. **[OMER, ~10 min]** approve scope and spend; this is also when he decides how much
   balance to load. Scaffold and analysis script freeze here.
7. **Run**, then **grade locally** (Rosetta VAL + plugin FAST_DOWNWARD, cwd
   `external/LLMs-Planning/plan-bench`, `RENDER_FROM_TOOLS=0`).
8. **Results memo** with the pre-registered analysis, the deviation table, and the band
   verdict read off the §3 cutpoints.

## 7. Open items outside this prereg

- **NT t3 GPT-4 comparison is mix-confounded** and is marked `PENDING AUDIT` in
  `planbench_frontier_haiku_nt.md` finding 2. The committed GPT-4 t3 corpus is a different
  corpus (0/500 identical queries; verdict mix 31.0% VALID vs our 64.8%), and the two
  models have opposite verdict biases, so a common-mix reweighting collapses the Mystery
  t3 gap from 28.2pp to 9.5pp. **Do not write paper prose from that finding until it is
  re-reported with per-verdict rates.** t1 is clean and unaffected. Evidence: decisions
  memo §5. Omer has not yet said whether to open this now or after the WT results.
- **Two free strengtheners for the NT layer, pending `/verify-claims`:** an apparent
  independent external replication (LLMFP Direct GPT-4o 41.5 / 0.8 at n=602 vs our 41.0 /
  0.8), and a published GPT-4 Mystery-t1 comparator (26/600 = 4.3% [3.0,6.3], Valmeekam
  arXiv:2305.15771 Table 1) that is CI-disjoint **above** Haiku's 0.8% — the NT doc
  currently records this cell as "not in canonical".
- **The ~$70.6 remainder is bookkeeping** (`frontier_rerun_handoff.md:74`), not a console
  balance. Verify it before any spend.

## 8. Do not

- Build or spend before the RATIFY signature.
- Reopen a §3 decision without reading the argument that settled it.
- Treat the WT numbers as Act 4's headline, or put them in a table or figure with GPT-4
  rows (prereg §7 makes that a protocol rule, not a prose intention).
- Quote the literature block of the decisions memo without `/verify-claims`.
- Touch `31b84ab` / the nt-ster H4 files — parallel session, different workstream.
