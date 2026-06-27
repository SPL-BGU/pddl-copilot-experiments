# Decoupled think=on `simulate` re-run — staging & GATED launch (Line 1 / ISS-024(a))

**Status:** STAGED, NOT SUBMITTED. All cluster steps are **user-gated** — ping Omer
+ confirm the university VPN is up before any SLURM/SSH. Local prep below is done.
**Date:** 2026-06-26
**Branch:** `paper/iter2-decoupled-run` (off `origin/main` b07b394, which already carries
**both** PR #87 Q1 grader and PR #88 decoupled budget — the merge/rebase prep is complete).
**Background:** `../archive/decoupled_budget_plan.md`, `../archive/q1_grader_plan.md`,
`simulate_decisions_and_next_steps.md` (Line 1), CHANGELOG 2026-06-25, ISS-024(a),
memory `project_simulate_grader_artifact`.

---

## What this run is

A clean **no-tools, think=on** `simulate` (and the rest of the 5-task no-tools matrix)
re-run over the **Qwen3 thinking roster only** with:
- the **decoupled budget** (`--decoupled-budget`; reasoning vs answer get separate
  token budgets via the 2-call `</think>`-stop + `continue_final_message` continuation),
- the **Q1 two-metric wrapper-tolerant simulate grader** (now the live grader — automatic),
- **`RESPONSE_SNAPSHOT_LEN=16384`** (corpus re-gradeable offline),
- the vLLM server's **reasoning parser OFF** (DECISION B).

Headline it answers: **reasoning overflow no longer starves the answer** — i.e. the
`think_truncated` / `FR_THINK_OVERFLOW` shared-budget confound (baseline truncates 55–83%)
drops while answer completion rises. Converts the Limitations hedge into a measured result.

**Roster (Qwen thinking only):** `Qwen3.5:0.8B`, `Qwen3.5:4B`, `Qwen3.5:9B`, `qwen3.6:35b`.
**Gemma excluded** — `gemma4:26b-a4b` has no `<think>` tokens (REASONING_PARSER=none
already), so there is nothing to decouple; its think=on truncation is plain long-output
and is reported **separately**, not as evidence for/against decoupling.

**Methodology guardrails:** one knob per corpus; new `RUN_TAG` (`decoupled-thinkon`),
**never pooled into `sweep5v2-live`**; single prompt; **no anon/contamination arm**;
`paper/` untouched (gather-data-first). Baseline for the A/B = the existing sweep5v2
think=on Qwen `simulate` cells (re-grade those with Q1 offline for apples-to-apples on the
secondary metrics; truncation-rate comparison needs no re-grade).

---

## Local prep — DONE (no cluster, no ping)

1. **Both PRs on one branch.** `origin/main` b07b394 = PR #87 (Q1 grader) + PR #88
   (decoupled budget) already merged in order. Run branch `paper/iter2-decoupled-run` cut
   off it. `_coerce_simulate_trajectory` + `chat_without_tools_decoupled` + `RESPONSE_SNAPSHOT_LEN=16384`
   all present.
2. **`bash tests/verify.sh` green** — incl. `test_simulate_q1` 29/29, `test_chat_decoupled`
   44/44, `test_runner` 41/41.
3. **Cluster plumbing built** (the wrapper/sbatch did NOT previously thread the decoupled
   flags or a parser override — that was the staging gap). Three scoped edits, all
   **byte-identical when the new flags aren't passed** (every existing sweep unaffected):
   - `cluster-experimenting/lib/defaults.sh` — `vllm_reasoning_parser_flag()` now honors a
     run-scoped `REASONING_PARSER_OVERRIDE` that takes precedence over the per-model
     `REASONING_PARSER` **without mutating the baseline** `vllm_lookup` config. `none`
     → `--reasoning-parser` flag omitted.
   - `cluster-experimenting/submit_with_rtx.sh` — adds `--decoupled-budget`,
     `--num-predict-think`, `--num-predict-answer`, `--reasoning-parser`; validates the
     integer budgets + parser value; **guards** that `--decoupled-budget` requires
     `--no-tools` AND `--think-modes on` (so no think=off cell aborts run_experiment.py and
     no tools cell silently no-ops the flag); threads all four into `--export`; banner line.
   - `cluster-experimenting/run_condition_vllm_rtx.sbatch` — builds `DECOUPLED_ARGS` and
     splices them into the full `run_experiment.py` invocation. (NOT into the `--smoke`
     fastpath — see DECISION S1.)
   - Verified locally: `--dry-run` emits the right cells + `--export`; all 5 guards fire;
     baseline dry-run unchanged; parser override unit-tested; `DECOUPLED_ARGS` unit-tested.

---

## GATED launch sequence (ping Omer + confirm VPN before EACH step)

### Step 1 — SMOKE (commit GPUs to the full run only after this is green)

**Two** Qwen models — `Qwen3.5:9B` (covers the Qwen3.5 template shared by 0.8B/4B/9B) and
`qwen3.6:35b` (the other family; cheap insurance against a template quirk on the most
expensive cell — S3) — `--partial 2`, exercising the real D3 risk: `continue_final_message`
× the Qwen3 chat template × parser-off actually continues the assistant turn and produces
**non-empty answers** where the shared-budget baseline truncated.

```bash
bash cluster-experimenting/submit_with_rtx.sh Qwen3.5:9B qwen3.6:35b \
    --no-tools --think-modes on --partial 2 \
    --decoupled-budget --num-predict-think 8192 \
    --reasoning-parser none --run-tag decoupled-thinkon-smoke --time 24:00:00
```

2-cell array → `results/slurm_vllm_{Qwen3_5_9B,qwen3_6_35b}_on_no-tools_decoupled-thinkon-smoke/`.
**Green = ** non-empty answers on (no-tools, think=on) simulate trajectories; `think_truncated`
populated; answer `done_reason` is the Call-2 signal; no template/continuation error in the
serve + run logs. **Also read off (resolves S2):** the simulate answer-truncation rate, the
Call-2 context-overflow-clip frequency, and any prompt≥ctx empty-synths — if the per-task
answer budget triggers frequent empties on simulate, fall back to a flat `--num-predict-answer
4096` for the full run. Confirm via the `analyzer` skill (Q1 table + `think_truncated` rates).

### Step 2 — FULL SWEEP (only after a green smoke; preflight first)

Preflight: pull → rebuild venvs **without `--quiet`** → verify imports → then submit.
Halt-on-failure between phases; no shotgun resubmits.

```bash
bash cluster-experimenting/submit_with_rtx.sh \
    Qwen3.5:0.8B Qwen3.5:4B Qwen3.5:9B qwen3.6:35b \
    --no-tools --think-modes on \
    --decoupled-budget --num-predict-think 8192 \
    --reasoning-parser none --run-tag decoupled-thinkon --time 24:00:00
```

4-cell array (one per Qwen model), each
`results/slurm_vllm_<model>_on_no-tools_decoupled-thinkon/` — **disjoint from the canonical
`..._on_no-tools/` trees**, so `sweep5v2-live` is never touched.

**Answer budget = per-task default (S2):** `--num-predict-answer` is **omitted**, so the
answer phase (Call 2) gets the per-task `DEFAULT_NUM_PREDICT` — **6144** for simulate/validate,
**8192** for solve — each now *dedicated* (no longer shared with reasoning). Think budget
stays `--num-predict-think 8192`.

---

## Open decisions (answer inline; I'll fold in before submitting)

### S1 — smoke mechanism: `--partial` constrained run, NOT the literal `--smoke` fastpath
The wrapper's `--smoke` flag is **structurally incompatible** with `--decoupled-budget`:
`run_experiment.py --smoke` forces `conditions="both"` and iterates think={on,off}
unconditionally, but decoupled only acts on the (no-tools, think=on) path — a think=off
smoke pass would abort the run, and the tools sub-passes are noise. So the smoke is a
**`--partial 2`** run pinned to `--no-tools --think-modes on`, which exercises *only* the
decoupled path (exactly the D3 risk) and nothing else. (`--time 24:00:00` per the
"smoke gets full-run resources" policy — only trial count differs.)

> **S1.** Recommend the `--partial 2` smoke above. The alternative (make the `--smoke`
> fastpath decoupled-aware) needs a run_experiment.py change and runs 3 wasteful sub-passes
> — not recommended.
> ANSWER: go for `--partial 2`

### S2 — answer budget: flat `--num-predict-answer 4096` (per the task) vs omit → per-task default
Per-task `DEFAULT_NUM_PREDICT` = solve 8192, validate_*/simulate **6144**. A flat
`--num-predict-answer 4096` gives every task's *answer phase* a dedicated 4096 (still far
above the starved share it got under the baseline's single 6144 think+answer budget). The
alternative — **omit** the flag → answer budget = per-task default (6144 simulate / 8192
solve, dedicated) — is the most apples-to-apples "only the starvation was removed" design
and is *more* generous for long simulate trajectories + solve plans.

> **S2.** Task command says flat 4096; I'll use it as the default. If the smoke shows heavy
> *answer*-truncation on simulate (long trajectories), switch the full run to omit
> `--num-predict-answer` (per-task 6144/8192). Pick one:
> ANSWER: what will likely result in lss errors and be closes to the real simulate run we will run later?
>
> **→ RESOLUTION (per-task default — omit `--num-predict-answer`):** Both criteria point the
> same way. (1) **Fewer errors:** `vllm_client.chat()` catches a Call-2 context overflow and
> **clips `max_tokens` gracefully** (then retries) — it does NOT empty the answer; the empty
> synth fires only when the prompt ALONE (orig prompt + re-encoded reasoning) ≥ 16384, which is
> *independent* of the answer budget. So the effective answer budget = `min(chosen, headroom)`:
> per-task 6144 is **never less** than 4096 and is **more** whenever there's headroom (the
> common short/moderate-reasoning case). Simulate is the truncation-prone task, so the larger
> nominal cap = strictly fewer truncated answers. (2) **Closest to the real run:** the baseline
> think=on simulate cells used `num_predict=6144` as the combined think+answer cap; giving the
> decoupled *answer* phase that same 6144 — now dedicated — is the clean "only the starvation
> was removed" A/B the paper run should use. Cost: more frequent (transparent, non-error)
> overflow-clip round-trips on long-reasoning simulate; the smoke quantifies them, and flat
> 4096 remains the documented fallback if they're pathological.

### S3 — smoke roster: `Qwen3.5:9B` only, or also `qwen3.6:35b`?
9B (per the task) represents the Qwen3.5 template shared by 0.8B/4B/9B. `qwen3.6:35b` is a
**different family** (Qwen3.6) whose chat template *should* handle `continue_final_message`
identically but isn't guaranteed to — and it's the most expensive cell to discover a
template quirk in late.

> **S3.** Recommend 9B-only smoke (cheap, covers 3/4 models); accept the small risk that a
> 35B template quirk surfaces in the full run's 35B cell (which we monitor). Optional cheap
> insurance: add `qwen3.6:35b` to the smoke (2 cells). Pick one:
> ANSWER: both models should be in the smoke

### S4 — full-sweep `--time`
Default no-tools is 12h; decoupled doubles LLM calls and the 35B cell is the slow one. I
staged `--time 24:00:00` (generous; SLURM bills actual). Bump for 35B if needed.

> **S4.** Recommend `--time 24:00:00`. OK, or different?
> ANSWER: OK

---

## Reporting plan (when results land)

For the decoupled think=on Qwen `simulate` cells **vs the shared-budget sweep5v2 baseline**:
- the **three Q1 numbers** — state-tracking accuracy / format-compliance / strict — per cell;
- **`think_truncated` rates** (and answer-phase `done_reason="length"` rates) — the headline
  is the think_truncated/`FR_THINK_OVERFLOW` drop with answer completion holding/rising;
- Gemma's think=on truncation reported **separately** (not a decoupling case).

Use `analyzer` for aggregation, `cluster-ops` for queue/submit/sync. Do **not** touch
`paper/` — gather data first.
