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

**E2. Availability contrast on the delivered score.** Tools-plain (this run) against
no-tools (canonical `sweep5v2-live`, exact, v11–13), per model × task, paired on
(domain, problem, variant, plan label), domain-cluster bootstrap 95% interval, Holm
across the 15 comparisons. The no-tools side is not rerun; its serving version and the
missing JSON constraint are stated wherever this contrast is quoted.

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
| job IDs | smoke (never pooled, `--partial 1`, tags `delivered-rerun-smoke` / `delivered-rerun-neutral-smoke`): 21978895_[0-2], 21978896, submitted 2026-10-02. Main run, submitted 2026-10-02 after the Gemma smoke cells passed: **21982285** (Gemma Part A, tag `delivered-rerun`), **21982286** (Gemma Part B, tag `delivered-rerun-neutral`, `afterok:21982285`). **21982369** (Qwen3.5-9B, tag `delivered-rerun`, `afterok:21982286`), **21982370** (Qwen3.6-35B, tag `delivered-rerun`, `afterok:21982369`), both submitted 2026-10-02 after the 9B smoke cell completed and passed |
| analysis files + sha256 | *to fill at freeze* |
| traceability map (clause → file:line) | *to fill at freeze* |

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
    rule is applied per job cell and stops the whole analysis.
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
    readout until audited; the audit is recorded in the readout.

## 9. Deviations

*None yet. Any change to the above after the first job starts is listed here with its
date and reason.*
