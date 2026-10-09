# Pre-registration: full-storage rerun of the open-weight tool arms ("delivered rerun")

**Written 2026-10-02, before any trial of this run exists.** Decision to run: Omer,
2026-10-02 (`weakness_consolidated.md` Q1 = run, Q2 = add the Gemma neutral-prompt arm).
This file is the standalone prereg that the tex Limitations sentence promised ("we
pre-register that rerun, under the same prereg-parity discipline as the independent
rerun (a Gemma negative control and TOST at ±5 pp)") and that did not exist until now
(`weakness_consolidated.md` F3).

**Disclosure of prior data contact.** No row of this run exists at registration time.
What we already know and cannot un-know, from the canonical corpus and the 2026-10-02
re-analyses (`reanalysis_transcripts.md`, `reanalysis_statistics.md`,
`reanalysis_breakdowns_cost.md`): the canonical tool-verified rates; that most
"truncated" tool-arm trials are a refused final request; that Gemma's solve answers carry
a leaked channel prefix; that Gemma's invocation rate differs by wording (31 / 27 / 4%)
and by domain. The hypotheses below were written with that knowledge. The earlier
full-storage rerun (`iss024d-e2e`, thinking on, reasoning parser off) is a different
configuration and its parity check failed; nothing from it is pooled here.

## 1. Purpose

The paper names the delivered answer as its primary outcome and cannot measure it on the
open-weight tool arms, because the canonical corpus stored the first 500 characters of
each final answer (`weakness_consolidated.md` C1). This run measures it.

It has two parts:

- **Part A (main).** The three headline models, thinking off, with tools, plain and
  steered arms, all five tasks, full storage. Replaces the censoring bounds with exact
  delivered rates.
- **Part B (neutral-prompt arm).** Gemma, thinking off, validate_plan only, with a
  system prompt that carries no instruction to use the tool. Tests whether the
  invocation finding survives when the tool is truly "merely available"
  (`weakness_consolidated.md` C4).

## 2. Design

| | Part A | Part B |
|---|---|---|
| models | `Qwen3.5:9B`, `gemma4:26b-a4b`, `qwen3.6:35b` | `gemma4:26b-a4b` |
| thinking | off | off |
| condition | tools, all tools visible | tools, all tools visible |
| prompt style | `minimal` (as canonical) | `neutral` (system prompt = role sentence only) |
| user-prompt variants | 11–13 (plain), 14–16 (steered) | 11–13 (plain), 14–16 (steered) |
| tasks | all five | validate_plan |
| trials | 3 × 9,120 = **27,360** | **6,000** |
| run tag | `delivered-rerun` | `delivered-rerun-neutral` |
| fixtures, ground-truth cache, budgets, context, temperature, seed | as canonical `sweep5v2` | as canonical |

Part B together with Part A's Gemma validate_plan rows forms a 2 × 2 on one model and
one task: system-prompt directive (present = `minimal`, absent = `neutral`) × user-turn
steering (absent = v11–13, present = v14–16), 3,000 trials per cell.

**Apparatus deltas against the canonical corpus.** All are in the harness at the commit
recorded in §8, and all are declared here because they change what is generated or
graded:

1. **Storage.** Final answers stored up to 65,536 characters (canonical: 500). A row
   records whether storage cut it. Registered expectation: zero rows cut.
2. **Final-request overflow retry.** When the server refuses a request because prompt
   plus output allowance exceeds the 16,384-token window, the client now lowers the
   allowance to what actually fits. The first request of every turn is unchanged. In the
   canonical corpus this path ended in an empty answer in about 1,987 headline trials.
   This changes the delivered answer by design. It can change the tool-verified layer
   only where a later tool-calling turn was previously refused.
3. **Leaked empty thought-channel prefix.** A leading `<|channel>thought\n<channel|>`
   is removed from the text the grader reads. The stored answer keeps the raw text.
4. **Serving version.** Recorded at run time with `probe_serving_env.sh`. Canonical
   Gemma and Qwen3.6-35B tool cells ran on vLLM 0.20.2, the canonical Qwen3.5-9B tool
   cells on 0.22.0. If the cluster serves 0.20.2, the 9B cell carries a version delta
   and Gemma and the 35B do not.

**Part C, the unaided arm, is rerun (added 2026-10-03, before any outcome of this run
was read).** An earlier note the same day said it was not needed, on two grounds: same
serving version, and an unaided delivered score that is "already exact". The second
ground is false in two ways, found while writing the analysis code: (i) canonical
unaided *simulate* rows were graded online with the pre-fix trajectory normaliser and
are stored as 500-character snapshots, so they cannot be regraded (the canonical overlay
marks 300/300, 262/300 and 271/300 of the headline rows censored), which leaves 3 of the
15 E2 comparisons uncomputable; (ii) on every task the canonical unaided grade is the
strict online extraction while the tool side would get the tolerant delivered grader,
which is the asymmetry the weakness list calls C7. Part C fixes both: the three headline
models, thinking off, no tools, v11–13, all five tasks, 3 × 4,560 = **13,680 trials**,
same harness commit, tag `delivered-rerun`, job 21991349 (`afterok:21982370`). Omer's
instruction for this choice: "if best approach is to do it then do it".

- **E2 now uses Part C as its no-tools side**, graded with the same delivered grader as
  the tool side, so both sides of every availability contrast are same-run,
  same-storage and same-grader. The canonical no-tools cells are no longer an input to
  E2.
- **Part C parity check (reported, not a gate on E2).** Per model × task for solve and
  the three validate tasks (12 cells): Δ = Part C − canonical on the stored online
  `success`, paired, same TOST at ±5 with the 90% domain-cluster interval as §3.
  Simulate is excluded (the canonical online grade used the pre-fix normaliser). If a
  cell fails, the paper says that the unaided baseline moved for that cell and by how
  much; E2 still uses Part C.

Nothing else differs: same model weights and quantisations, same parsers
(`vllm_lookup`), same GPU class (`rtx_6000`, one per job), same sbatch.

## 3. Parity guard (evaluated before any delivered number is read)

The rerun's delivered numbers stand in for the canonical cells only if the rerun
reproduces the canonical corpus on the metric both store exactly: **tool-verified
success**.

- **Unit.** Model × task × arm (plain v11–13, steered v14–16): 3 × 5 × 2 = 30 cells.
- **Estimate.** Δ = rerun − canonical, paired on the trial key (domain, problem,
  variant, plan label). Rows missing from either corpus are counted and reported;
  a cell with more than 1% unpaired rows is VOID.
- **Test.** Paired TOST at ±5 points: the 90% confidence interval of Δ, from a cluster
  bootstrap over the 20 domains (10,000 resamples, seed 20261002), lies inside
  [−5, +5]. Secondary, reported beside it and not used for the verdict: the unpaired
  Newcombe 90% interval used by the `iss024d` parity prereg.
- **Gemma first (negative control).** Gemma's 10 cells are evaluated before the Qwen
  cells. Gemma carries no serving-version delta, so a Gemma failure calibrates
  run-to-run noise. If any Gemma cell fails, F = max |Δ̂| over Gemma cells is reported
  as the noise floor.
- **Job-level rule.** Parity holds if at least 18 of the 20 Qwen cells meet the
  criterion and no cell of any model has |Δ̂| > 10 points.
- **Consequences, fixed in advance.**
  - Parity holds: the rerun's delivered rates are reported as the exact delivered rates
    of the headline cells, with the apparatus deltas of §2 stated.
  - A cell fails: that cell's delivered rate is reported as a separate-apparatus
    measurement, labelled, with the failure shown. Wording is "criterion not met
    (unresolved)".
  - Parity fails at job level: the whole rerun is reported as a separate-apparatus
    replication. The margin is not adjusted after the data are seen.
- **Known reason a cell may move.** Delta 2 lets tool-calling loops continue that were
  previously refused. Such movement is reported with the count of rows whose allowance
  was clipped before a tool call; it is not grounds for changing the rule.

## 4. Primary endpoints

All on **delivered success**: the final answer graded against the oracle, with the
normalisation of §2 delta 3, exact (no censoring bounds).

**E1. Delivered rate per cell.** 30 cells, with a domain-cluster bootstrap 95% interval.

**E2. Availability contrast on the delivered score.** Tools-plain (Part A) against
no-tools (Part C), both from this run and graded with the same delivered grader, per
model × task, paired on (domain, problem, variant, plan label), domain-cluster bootstrap
95% interval, Holm across the 15 comparisons. (Amended 2026-10-03 with Part C, before any
outcome was read; the canonical no-tools cells are not an E2 input.)

**E3. Steering contrast on the delivered score.** Tools-steered against tools-plain,
both from this run, same pairing and intervals, Holm across 15.

**E4. Delivery gap among calling trials.** Share of trials with a correct tool result
whose delivered answer is wrong, per cell, with the failure classified by the fixed
categories of `reanalysis_transcripts.md` Q1 (no final answer, tool-input error,
summary only, abridged, wrong wrapper, numeric omitted, wrong facts) plus "refused or
clipped final request".

## 5. Registered readings

**R1. Does not calling cost delivered answers? (the title claim; Gemma validate_plan)**
Canonical: unaided 88%, invocation 21% in the plain arm.

| outcome of E2 for Gemma validate_plan | reading |
|---|---|
| interval entirely below −5 | **Harm confirmed on the primary outcome.** Not calling costs delivered answers. |
| interval entirely inside [−5, +5] | **No delivered harm.** The −67 points is a property of the tool-verified score; the title claim does not hold on the primary outcome for this cell. |
| anything else | **Unresolved.** Reported with its interval. |

**R2. Does one steering sentence raise delivered answers?** E3 for Gemma validate_plan:
interval entirely above +5 = yes; entirely inside [−5, +5] = no; else unresolved.

**R3. Title rule.** The title stays "invocation is the bottleneck" only if R1 is "harm
confirmed" or, failing that, E3 shows a delivered gain above +5 for at least two of
the three models on validate_plan. Otherwise the title changes to the two-gate reading
(invocation and delivery) that the abstract already uses.

**R4. Is the open-weight delivery gap a restating failure?** For solve, E4 among
calling trials with a full, uncut final answer. If the share delivered correctly is at
least 90% for each model, the canonical open-weight "delivery gap" on solve is
attributed to storage and the refused final request, and the paper says so.

**R5. Part B, the neutral system prompt.** Invocation rate (share of trials with a
tool call) and delivered success in the four cells of the 2 × 2.

| neutral-plain invocation against minimal-plain invocation (this run) | reading |
|---|---|
| lower by more than 5 points | The system-prompt sentence was doing work. "Merely available" is rarer than the paper's 21%, and the paper says so. |
| within ±5 (paired TOST as in §3) | The system-prompt sentence is inert for this model. The plain arm is a fair "merely available" arm. |
| higher by more than 5 points | The directive suppresses calling. Reported as found. |

And: if neutral-steered invocation is within ±5 of minimal-steered, steering in the
user turn is sufficient by itself.

No reading is added, dropped or re-thresholded after the data are seen.

## 6. Secondary (descriptive, not gates)

Per-wording and per-domain tables of invocation and delivered success; classical
against numeric; clipped-allowance counts per cell; tokens and cost-of-pass on the
delivered score at 1:1 and at realistic output-to-input price ratios; the Gemma
no-call answers read in full (does the prose end in a verdict, and is it right).

## 7. Execution

- **Order, strictly serial, each step gated on the previous one succeeding (`afterok`):**
  smoke → Gemma Part A → Gemma Part B → Qwen3.5-9B → Qwen3.6-35B.
- **Smoke.** Full-run resources, short trial count (the real configuration with
  `--partial 1`, because the stock `--smoke` uses prompts too short to reach the
  overflow path and refuses the new flags), separate run tags, never pooled. Checks allowed on smoke output: the job completes; rows carry the new storage
  and clipped-allowance fields; no row is cut by storage; no exception or
  infrastructure-failure rows; tool calls parse (at least one trial with a tool call
  per model); on rows whose allowance was clipped, measured prompt plus clipped
  allowance against the 16,384-token window. Smoke success rates are not computed.
- **During the run.** Monitoring reads row counts and job states only. No success,
  invocation or failure-reason rate of any cell is computed before the freeze in §8.
- **Stop rules.** A cell is VOID and rerun from scratch (declared here, not a
  deviation) if more than 1% of its rows are infrastructure failures or exceptions.
  Any other stop is a declared deviation.
- **Completeness.** 9,120 rows per Part A cell, 6,000 for Part B, 1,520 / 1,000 per
  variant. A short cell is resumed, not analysed.

## 8. Freeze record (to be completed before first contact with outcome data)

The analysis entry point does not exist yet. It is written while the jobs run and is
frozen under `/freeze-protocol` (typed load boundary, registered constants as asserts,
clause-by-clause traceability to §3–§5, synthetic fixture run, independent adversarial
review) **before any outcome field of this run is read**. `tools/e2e_regrade.py` is
pinned by an earlier prereg and is not edited; the delivered grader for this run is a
new file that reuses the harness scoring functions at the harness commit below.

| item | value |
|---|---|
| harness branch / commit | `harness/delivered-rerun` at `4b2fe6ec0a0b8c54c1607e7fc37e2ba4f1525114` (PR #113; independent review 2026-10-02, four findings fixed in that commit). The cluster checkout stays on this commit until every cell is complete. Tools repo `pddl-copilot` at `5e4f9c0` (same commit as the canonical corpus) |
| serving version | vLLM **0.20.2** (served banner in the smoke server log `21978897-vllm-gemma4_26b-a4b.log`; cached `~/vllm.sif`). So Gemma and Qwen3.6-35B carry no version delta against their canonical tool cells; Qwen3.5-9B does (canonical 0.22.0) |
| job IDs | smoke (never pooled, `--partial 1`): 21978895_[0-2], 21978896. Main run: **21982285** (Gemma A) → **21982286** (Gemma B) → **21982369** (9B) → **21982370** (35B) → **21991349_[0-2]** (Part C), each `afterok` on the previous |
| **FROZEN 2026-10-03** | analysis branch `analysis/delivered-rerun` at **`d558946985330b95f71f07d38d59d20df848dc01`** (PR #116). No outcome field of this run had been read at freeze time (only row counts and job states) |
| package hash (`--i-have-frozen`) | **`822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9`** (covers the package and every repo module it imports; live mode also checks the domain-file manifest digest and requires `pddl-copilot` at `5e4f9c0` with a clean `plugins/`) |
| gates | 1 typed loader, 2 registered constants as raised checks (refuses `python -O`), 3 traceability map (all quoted clauses verbatim against this prereg), 4 synthetic fixture with hand-computed values and refusals (428 checks), 5 independent adversarial review (2026-10-03: 1 blocker, 5 should-fix, 8 notes, all fixed) followed by an independent verification pass (all confirmed; 4 low items found and fixed) |
| canonical self-vs-self dry run | Δ = 0 and interval [0, 0] in all 30 tool cells and all 12 Part C parity cells, k = 20 |

**sha256 of the frozen files** (at `d558946`):

| file | sha256 |
|---|---|
| `tools/delivered_rerun/__init__.py` | `1450beb6fe7ba5d573676ca1825a4cba39b4d73cb82159d903e436e6e8675917` |
| `tools/delivered_rerun/analysis.py` | `ec915da3da9eda78870e7cc26cb5bcf0d145cfb21dd7d7f846c2ec00a530de8b` |
| `tools/delivered_rerun/constants.py` | `879daf12ce176a71f7d7c2137b73c21a7844ff562dde9b07da4d67b60bc9a1b9` |
| `tools/delivered_rerun/e4.py` | `2ad776ee4b648971d0459c613db85d34326d8c3c6ec330ee75f5c71893a2c25b` |
| `tools/delivered_rerun/grade.py` | `1588646c021ce23126d11b716bad9c24f794e72894b0e73f261dc206b32b617e` |
| `tools/delivered_rerun/readout.py` | `ffddae5576d396d1bd69e2baee8958892a91f96856f9fae035c0be3bc5c78590` |
| `tools/delivered_rerun/run.py` | `8410090db908cfb01622cbfd4d7f97204b82139c434d03e92da03fbd5e68f940` |
| `tools/delivered_rerun/schema.py` | `5e33d6bd16ebcdf6b7298002d5929d07b7601f32b586c93933a176688e9aa66e` |
| `tools/delivered_rerun/stats.py` | `f37950779694741c106b0a8d20e6d4afe9d10573a658edd7e3efdd8c726d87a0` |
| `tools/delivered_rerun/tripwires.py` | `f53193a5f2b40ec9bae3cbe64df4b44691f2dca54cb494eb60fb79d640145ae4` |
| `pddl_eval/__init__.py` | `0164c8d1cca872a3be65dd2461d627b95cdae8dc4b23ef4a6c6871b632c1e3db` |
| `pddl_eval/scoring.py` | `13444404ed07f5fe06216248b742d8d286da7caad631ccab6b374837ed237299` |
| `pddl_eval/chat.py` | `f195e0889bc0003c6faf2050bbdec28d525ace5cc9ecacf7c1be3a2b28426907` |
| `pddl_eval/schemas.py` | `335b62a6d2907eace6694f899e1d54f87764e85e8deb6c65aaba7c20b45528ef` |
| `pddl_eval/runner.py` | `95213c61e343447d76f16be7bb1dcb0cfa3798d0febf14a440a352a11bd6f1cb` |
| `pddl_eval/summary.py` | `6b3475163cee2b35f7ce816d00b1886b6c788b1d2caa6c083ff0b518e4eebb36` |
| `pddl_eval/prompts.py` | `f12c19e9026bea463cdb5cf0b1e9ece96104e419a1bf51f9f1b0bf5dddd32e92` |
| `pddl_eval/domains.py` | `6f2a7f98c7327b535fa3d489f31555969b94fc03b735fb2735f2c96527aa7a94` |
| `pddl_eval/resume.py` | `f4abc5d4843204f42e7099f7eedfcc4ff3e3763d7b2848db4dfae0a154ba72c9` |
| `run_experiment.py` | `38f0b5d4fb1dba014efbfadaa101444f8a1b183d12fd92ed6a45d92e4addad29` |
| `tools/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tools/e2e_regrade.py` (pinned 2026-09-10, unchanged) | `45dcf74a23b5d2b1d79028fd1733a9ba7884ba7f62f84c7ffa4febd100c4b11a` |
| `tools/_run_manifest.py` | `08db2b20be699c818e47e15e589639d4294a40be1a6707b5a1e8c5acf2152c45` |
| `tools/gt_cache_gate.py` | `1181781e674f212c7d62c4fcdb6d50eb7ee9e650887d8e2bd95937609d8f3897` |
| `development/delivered_rerun_traceability.md` (gate 3 map) | `4440c7720877a5d02bc7f1ea205425de2dbb4427d3418f29ee7f8bbf4ce57ba2` |
| `tests/test_delivered_rerun_analysis.py` (gate 4, 428 checks) | `dc4ec7983454893ed12b74ec0d4a923ded43a6350fb97cf9ad3bfd7781403eeb` |
| `tests/fixtures/delivered_rerun/build_fixture.py` | `ba163b030caa40ea5ac5a97e07c87240e208d09990124525d2618cdf3c2c8c50` |

Any later edit to one of these files is a declared deviation in §9, followed by a re-freeze
and regeneration of every downstream artifact.

## 8a. Smoke record (2026-10-02)

Checked on the smoke output, apparatus fields only (script: row counts, field presence,
storage cuts, exception and infrastructure rows, presence of tool calls, clip
arithmetic). Gemma Part A, Gemma Part B and Qwen3.6-35B complete at registration of this
record; Qwen3.5-9B completed later the same day and passed the same checks (960 rows, 0 cut by storage, longest answer 22,519 characters, 0 exception and 0 infrastructure rows, tool calls present, 101 clipped rows with prompt plus allowance equal to 16,384 in 74 of 74 with sizes, 75 rows with a no-room turn).

| check | Gemma A (960 rows) | Gemma B (240) | 35B (960) |
|---|---|---|---|
| job state | COMPLETED 0:0 | COMPLETED 0:0 | COMPLETED 0:0 |
| storage flag on every row / rows cut by storage | 960 / 0 | 240 / 0 | 960 / 0 |
| longest stored answer (characters) | 18,421 | 19,093 | 21,934 |
| exception rows / infrastructure-failure rows | 0 / 0 | 0 / 0 | 0 / 0 |
| at least one tool call | yes | yes | yes |
| clipped rows; measured prompt + clipped allowance = 16,384 | 53; 43 of 43 with sizes | 6; 6 of 6 | 103; 87 of 87 |
| rows with a turn where the prompt alone fills the window | 65 (simulate 55, solve 10) | 0 | 67 (simulate 53, solve 14) |

Three things the smoke showed, recorded before the main run:

1. **The retry fix works on a live server.** Wherever the prompt size was measured, the
   clipped allowance fills the window exactly. No shortfall, no halving.
2. **The longest stored answers exceed 16,384 characters** in every cell, so the old cap
   would have cut them. None reaches 65,536.
3. **A real context limit remains, mostly on simulate.** In about 45% of smoke simulate
   trials the tool's own result fills the 16,384-token window (server log: prompts of
   about 1.2 million characters), so no final answer can be generated at any
   allowance. On solve the same happens after several tool calls in one trial. This is
   a property of the canonical apparatus (16K context), not of the fixes. It is not
   changed for this run: a 32K context was piloted earlier and raised parse failures
   (`paper_notes` 2026-06-18). **Consequence registered here:** delivered simulate for the
   open-weight tool arms is reported with these rows counted as failures and their share
   stated (`ctx_no_room_turns`), as a limit of the 16K deployment.
4. Clipped rows that later hit a no-room turn carry the clip count without the
   last-turn sizes (10 / 0 / 16 rows). Accounting only.

**Incidental disclosure.** While scanning the smoke logs for errors, two end-of-run
summary lines of the 35B smoke cell were printed (solve and simulate pass counts on the
smoke slice, 120 trials each). Smoke rows are never pooled and no main-run outcome has
been read.

## 8b. Clarifications fixed before the freeze (2026-10-03, no outcome of this run read)

Points the prereg left open, and the reading the analysis code implements. These are
fixed now, before the freeze, so they are part of the registration, not deviations.

1. Holm p-values come from an exact sign-flip test over the 20 domains; intervals from
   the domain-cluster bootstrap.
2. R1–R3 use the unadjusted 95% interval.
3. "Inside [−5, +5]" includes the endpoints; "entirely below −5" and "entirely above +5"
   are strict.
4. The unpaired share is measured against all keys in either corpus. A VOID cell counts
   as "not met" in the 18/20 rule, and its point estimate still enters the |Δ̂| > 10 check.
5. A Gemma control cell "fails" on any verdict other than "criterion met", VOID included.
6. E3 pairs plain wording v with steered wording v+3 on the same fixture.
7. R3's "gain above +5" means the 95% lower bound is above +5.
8. R4's population is trials with a correct tool result. "Full, uncut" means
   `done_reason` is not "length", no no-room turn, not cut by storage. Empty answers that
   stopped normally stay in and count as failures. Both arms are pooled per model; the
   point estimate is compared with 90%. If not met, the label is "R4 condition not met".
9. R5's "lower / higher by more than 5" use the point estimate; the middle row uses the
   90% TOST. If no row applies, the label is "No registered row applies". Invocation is
   any tool call (reproduces the canonical 622/3,000).
10. §7 exception rows are `failure_reason` "exception" or "ollama_parse_error"; the 1%
    rule is applied per job cell and stops the whole analysis. Also counted as an
    exception row, by its exact shape: a client exception whose message is empty, which
    the harness stores under an ordinary failure reason with empty tokens, no tool calls
    and an empty answer (added 2026-10-03 before the freeze; found by the verification
    pass).
11. Duplicate trial keys stop the analysis. Half-written lines are counted and reported.
12. The delivered rule is the overlay's `e2e_strict` rule with its markdown
    tolerances, applied identically to tool and no-tools rows (Part C).
13. E4: "refused or clipped final request" is classified first. Answers the mechanical
    rules cannot classify are labelled "needs reading" and read by hand after the
    freeze, with the reading recorded.
14. "Clipped before a tool call" means a clipped turn that was not the last turn, or a
    clipped last turn when the tool loop ran out.
15. Readout tripwire bands: tool-verified within ±30 points of canonical; delivered
    within [canonical low − 20, canonical high + 20 + canonical share of empty
    length-stopped answers + share with the leaked prefix]. A fired tripwire halts the
    readout until audited; the audit is recorded in the readout. Part C's delivered rate
   has no band of its own; it is covered by the constant-column tripwire and by the
   Part C parity table.
16. R5's steering sentence, when neutral-steered is not within ±5 of minimal-steered,
    reads "Not shown (neutral-steered not within ±5 of minimal-steered)".

## 8c. Readout (2026-10-09, frozen code, live mode)

**Run.** All seven cells complete: Part A 9,120 × 3, Part B 6,000, Part C 4,560 × 3. The
Qwen3.5-9B Part C cell timed out at 12 h (21991349_1, 4,392 rows) and was resumed once
under §7 "a short cell is resumed": job **22417213**, same run tag, same harness checkout
`4b2fe6e`, tools repo `5e4f9c0`, vLLM 0.20.2 (served banner in
`22417213-vllm-Qwen3_5_9B.log`); COMPLETED 2026-10-09 12:22, exit 0, 4,560 rows. Rows
synced to the laptop (`results/delivered-rerun/`, seven dirs, smoke dirs excluded).

**Invocation.** Analysis worktree at `d558946`, package hash
`822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9` (matched),
`--canonical-root results/sweep5v2-live`, `--gt-cache results/derived/gt_cache.json`,
`--marketplace-path` = a temporary detached worktree of `pddl-copilot` at `5e4f9c0`
(plugin venvs built as `launch-server.sh` does; worktree removed afterwards). Exit 0, no
HALT, no tripwire fired, no `--audit-notes`. Every corpus check is zero (torn lines,
exception rows, infrastructure rows, scoring errors, storage cuts) in all 13 cells.

**Output, kept byte-identical:** `reference/delivered_rerun_readout.md` (sha256
`043526d8b8b8f0299ad910c3468d5650c9bdd15718e6e98247e8357c1970f973`) and
`reference/delivered_rerun_readout.json` (sha256
`81bd59ffd153dafe20e9d9d7422785fff05d8dba894e9f8a331b919a7334c674`). The tables there
are the record; the lines below are a summary of them.

**Parity guard (§3).** Gemma first: all 10 Gemma cells meet the criterion (no noise
floor reported). Qwen: 15 / 20 cells meet it (rule needs 18); two cells have
|Δ̂| > 10: Qwen3.6-35B solve-plain +19.3 [14.3, 24.7] and simulate-plain +19.3
[11.7, 27.7]. Also not met: 35B solve-steered +7.3, 9B simulate plain +3.0 and steered
+4.0. **Parity fails at job level: the whole rerun is reported as a separate-apparatus
replication** (fixed consequence). Turns clipped before a tool call, the §3 "known
reason": 97 (35B solve-plain), 85 (35B solve-steered).

**Part C parity (reported, not a gate).** 11 / 12 cells meet the criterion; Qwen3.6-35B
validate_domain does not (76.4 against 67.8, +8.6 [2.8, 14.7], unresolved).

**E1.** Solve 77.0–95.3; validate tasks 89.2–100.0; simulate 8.3 (Gemma, both arms),
16.3–17.3 (9B), 25.7–28.3 (35B). No-room share on simulate 42.7–53.0% (§8a), counted as
delivered failures.

**E2 (tools-plain − Part C, Holm over 15).** Solve +71.0 / +64.3 / +51.7 (Gemma / 9B /
35B); validate_domain +18.9 / +73.9 / +22.2; validate_problem +23.3 / +29.0 / +21.5;
validate_plan +0.9 [−1.2, 2.9] (Gemma, Holm p 0.46) / +14.2 / +7.4; simulate −15.7
[−24.7, −6.7] (Gemma, Holm p 0.018) / +8.0 (Holm p 0.22) / +10.7 (Holm p 0.090).

**E3 (steered − plain, Holm over 15).** Only Gemma validate_plan survives Holm: +7.5
[4.9, 10.2], Holm p 0.00057. All others Holm p ≥ 0.15.

**E4.** Gap among tool-correct trials: validate tasks 0–1.7%; solve 4.7–13.4% (mostly
refused or clipped final request); simulate 69.9–91.2% (mostly refused or clipped final
request). "Needs reading" rows await the hand read of §8b item 13.

**Registered readings (§5), verbatim labels.**

- **R1:** No delivered harm (Gemma validate_plan E2 +0.9, 95% CI [−1.2, 2.9]).
- **R2:** Unresolved (Gemma validate_plan E3 +7.5, 95% CI [4.9, 10.2]; the lower bound
  is not above +5).
- **R3:** Title changes to the two-gate reading (invocation and delivery). R1 is not
  "harm confirmed" and no model has an E3 validate_plan 95% lower bound above +5.
- **R4:** The canonical open-weight delivery gap on solve is attributed to storage and
  the refused final request (≥ 90% for each model; full, uncut answers delivered correctly:
  Gemma 97.7% of 576, 9B 95.0% of 561, 35B 95.2% of 498).
- **R5:** The directive suppresses calling (neutral-plain − minimal-plain invocation
  +6.9, 90% CI [3.6, 10.7]; 26.9% against 20.0%). Steering sentence: Not shown
  (neutral-steered not within ±5 of minimal-steered; 98.1 against 93.1).

Still to do under this prereg: the hand read of the E4 "needs reading" rows (§8b 13) and
the descriptive §6 tables, both labelled descriptive.

## 9. Deviations

1. **2026-10-09, execution only, no analysis change.** The Qwen3.5-9B Part C cell
   (21991349_1) stopped at the 12 h wall clock with 4,392 / 4,560 rows. §7 says a short
   cell is resumed, so it was resumed once (22417213) on the same checkout, tools
   commit, serving version and run tag; no row was rerun or dropped. Listed here because
   §7 also says any stop other than a VOID cell is a declared deviation. The analysis
   was not edited and no outcome had been read when the resume was submitted.
