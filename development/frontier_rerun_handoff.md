# Frontier rerun — handoff (fresh session pickup)

**Date:** 2026-07-11
**Branch:** `feat/e2e-scoring-overlay` (working tree clean; verify it's pushed)
**Companions:** `frontier_rerun_framework_decision.md` (decisions),
`decision_audit_grading_and_frontier.md` (external-literature audit + all reasoning),
`tool_call_vs_final_output_grading.md` (grading overlay). This doc = the "what to do next".

---

## One-paragraph state

**Haiku full run DONE + regraded (2026-07-12).** Stage-1 A-vs-B probe was fully
concordant (§2.3); all four Haiku corpora now on disk and e2e-regraded
(`results/haiku-frontier/{sweep5v2,sweep6,sweep5v2-with-tools,sweep6-with-tools}`,
overlay under `results/derived/e2e_overlay/haiku-frontier`). **Spent ~$76.7 of $238;
~$161 remaining.** The next decision is **Sonnet WT scope** — both corpora (~$191) does
NOT fit the remainder; canonical-only (~$96) does (see SONNET DECISION below). The
Haiku RESULTS block below is the headline. Separately, the Qwen ISS-024(d) job
**19293221** is still on the cluster (leave it; strict-undecided resolver).

## HAIKU FULL-RUN RESULTS (e2e_strict, 2026-07-12)

Corpora: NT via Batch API (canonical = old 2026-06-25 500-cap run reused; anon = fresh
16K batch, $5.43), WT via `frontier_runner.py` (both corpora fresh, 16K, caching ON,
canonical $31.87 + anon $31.83, 0 infra rows, 98.4-98.5% online success). Regrade:
`tools/e2e_regrade.py results/haiku-frontier`. **`delegation_terminal_credit = 0`
corpus-wide → lenient `e2e` == `e2e_strict` here (D2b headline choice is moot for Haiku).**

Pooled canonical+anon e2e_strict tool-lift (determinate rows, Wilson 95%):

| task | NT (no-tools) | WT (tools) | WT tool-verified |
|---|---|---|---|
| validate_domain | 87.1 [82,91] n=240 | **98.8 [96,99.6]** n=240 | 98.8 |
| validate_problem | 74.8 [70,79] n=400 | **96.5 [94,98]** n=400 | 96.8 |
| validate_plan | 89.8 [88,91] n=2000 | **98.6 [98,99]** n=2000 | 98.7 |
| solve | 20.5 [16,27] n=200 | **13.5 [9,19]** n=200 | **100.0** |
| simulate | 0.0 [0,5.7] n=63* | **0.0 [0,2.2]** n=172 | **97.5** |

*simulate NT canonical is 100% CENSORED (500-cap corpus, response ungradeable); the
n=63 NT figure is anon-only determinate. To de-censor, rerun NT canonical simulate via
batch at 16K (~$0.3, 100 trials) — cheap follow-up, not blocking.

**The headline finding (paper-critical):** tool-call grading and end-to-end grading
AGREE on validation (verdict is a short string the model always restates → tools give a
real, CI-disjoint delivered-answer lift), but DIVERGE hard on the generative tasks:
- **solve** — WT tool-verified = **100%** (the model always drives the solver to a valid
  saved plan) but WT delivered e2e = **13.5%**, *below* NT's 20.5%. The final response
  omits the plan in 68-73% of trials (`no_plan_extracted`); on anon, the 32/100 that do
  restate a plan are **all invalid** (0/32) vs 27/27 valid on canonical — the model
  transcribes the tool's plan into its prose answer wrongly, worse on unfamiliar names.
- **simulate** — WT tool-verified = **97.5%** but delivered e2e = **0%**: the final
  answer is not a parseable trajectory in 82-86% (`format_parse_fail`).
So the standard tool-call metric overstates delivered with-tools capability by ~85pp on
solve and ~97pp on simulate, and ~0 on validation. This is exactly the
tool-call-vs-final-output distinction the overlay was built to measure.

**Contamination (canonical vs anon): NULL on validation** (all CIs overlap). solve/simulate
can't be cleanly contrast-tested at the delivered level (NT-canon simulate censored;
solve WT e2e dominated by the transcription artifact, not memorization — capability is
100% tool-verified both corpora).

## SONNET DECISION — RESOLVED (Omer, 2026-07-12): canonical-only, "no anon needed"

Sonnet NT both corpora already exist (PR#80); Sonnet only needs **WT**, **canonical only**
(~$96, fits the ~$161 remaining). Launched 2026-07-12:
`frontier_runner.py --model claude-sonnet-4-6 --variant 11 --marketplace-path ../pddl-copilot
--out results/sonnet-frontier/sweep5v2-with-tools`. Regrade into the same overlay
(`e2e_regrade.py results/sonnet-frontier`) when done; compare WT tool-verified-vs-delivered
to the Haiku pattern (expect the same solve/simulate transcription gap, smaller if Sonnet
transcribes better).

## Decisions already locked (don't relitigate)

- **Grading D2b → STRICT** is the paper headline (`e2e_strict`); delegation-terminal is a
  visible category; B kept as a derived diagnostic. Measured basis: 2/25 verdict flips,
  both knife-edge/censoring-bound (`tools/e2e_d2b_compare.py`).
- **Frontier D1 = B** (SDK Tool Runner), one shared module for the rerun + future PlanBench
  with-tools backend. A (bare loop, `tools/claude_api_tools_probe.py`) survives only as the
  probe's comparison arm.
- **D2 = staged probe:** 100 paired trials first (~$5–10); extend to 300–500 only if stage-1
  shows discordance (≥2 discordant pairs or a turns/token shift). Else stop at 100 and report
  it as a gross-defect check.
- **D3 = single prompt variant** for the frontier arm (`--variant N`); slice the old
  3-variant Sonnet NT corpus to the matching variant when comparing.
- **D4 = approved, budget $238 funded**, sequenced: probe → Haiku both arms → re-estimate
  from measured cost → Sonnet only if the remainder covers it.

## Findings from this session (already recorded, don't rediscover)

1. **Prompt caching — SUPERSEDED by the stage-1 probe (2026-07-11): caching SAVES ~15%
   at stratified scale; keep it ON.** The smoke's "+6% net-loss" was a 3-trial artifact:
   with trials grouped by task the tools+system prefix stays hot across consecutive
   trials, and solve's multi-turn loops (~4.7 turns) read ~30K cached tok/trial (solve
   $0.91 cached vs $1.39 no-cache per 20 trials). Budget the WT arm at ~0.85× list.
1b. **Tool-result verbosity can overflow even the 200K frontier window — intermittently.**
   Full-run finding (2026-07-11/12, WT): `simulate depot/p01` — on one path a single
   `get_state_transition` result pushed turn 2 to ~498K tokens → API 400. Fixed in
   `frontier_runner.py` (commit 8b5d276): "prompt is too long" 400s record as
   `FR_TRUNCATED_NO_ANSWER` / `done_reason=length` with tool_calls kept
   (open-arm-equivalent semantics), NOT infra. **NOT deterministic:** the resume
   mop-up re-ran the same trial (temp 0) and it SUCCEEDED in 3 turns — the SDK runner
   takes slightly different tool-call paths run-to-run, and only the path that requests
   the giant state-transition overflows. So the classification fix is a safety net for
   an intermittent failure mode, not a fixed capacity wall. Final both-corpora WT: 0
   infra rows, canonical 1497/1520 (98.5%), anon 1495/1520 (98.4%). Paper-relevant:
   simulate on big domains has a *tool-side* verbosity risk independent of model
   quality, but it's a tail event (~1 trial), not a floor.
2. **`--use-cached-gt` is smoke/dev only.** It loads GT from `results/derived/gt_cache.json`
   to skip the heavy `generate_ground_truth` solver prelude (which SIGKILLs in a
   resource-limited sandbox). The **full run and the paired probe must generate fresh**
   (default) so both A and B arms share one GT source (generate is deterministic given fixed
   plugins). `--dry-run` always uses the cache (it's offline, no MCP).
3. MCP connect is fast/healthy (~1s); the SIGKILL was only `generate_ground_truth`.

## The runner — how to drive it

```bash
# offline job counts (no MCP, no API) — sanity/scoping
python tools/frontier_runner.py --model claude-haiku-4-5 --dry-run                # full grid 9120
python tools/frontier_runner.py --model claude-haiku-4-5 --dry-run --variant 14   # single variant 1520

# live smoke (real API + MCP; cached GT to skip the solver prelude)
python tools/frontier_runner.py --model claude-haiku-4-5 --use-cached-gt \
    --marketplace-path ../pddl-copilot --limit 3 --out .local/frontier/smoke
```

Verified: full grid 9120, single-variant 1520 (= the doc's Haiku D3 estimate), `--limit`
smoke, live loop 3/3 OK, SDK pinned (anthropic 0.109.2). Writes standard `trials.jsonl`
(16K snapshots) + `save_results` meta; the e2e overlay/analyzer read it unchanged.

## Stage-1 paired A-vs-B probe — DONE 2026-07-11

All four steps completed; result = **fully concordant** (0/100 discordant, McNemar
p=1.0; both arms 99/100 with the *same* single failure `simulate counters/p05`
`result_mismatch`; turns 2.48 vs 2.53; in-tok +1.5%, out-tok +0.8%; B $3.28 vs
A $3.81 — the −14% is entirely prompt caching, verdict ACTIVE at stratified scale).
Recorded in `decision_audit_grading_and_frontier.md` §2.3. Reproduce with:

```bash
python tools/make_stage1_keys.py --out .local/frontier/stage1_keys.jsonl   # seed 11, v11
python tools/frontier_ab_compare.py --a .local/frontier/a_probe/trials.jsonl \
    --b .local/frontier/b_probe/trials.jsonl --model claude-haiku-4-5
```

## NEXT STEP — full Haiku run (D4 sequence)

1. **WT arm (framework B, caching ON, variant 11)** per corpus:
   ```bash
   python tools/frontier_runner.py --model claude-haiku-4-5 --variant 11 \
       --marketplace-path ../pddl-copilot --out results/frontier/haiku_wt_canonical
   python tools/frontier_runner.py --model claude-haiku-4-5 --variant 11 --corpus anon \
       --marketplace-path ../pddl-copilot --out results/frontier/haiku_wt_anon
   ```
   Measured estimate: ≈$50/corpus (1520 trials, cached; probe measured $3.28/100).
2. **NT arm** via the Batch API (`tools/claude_api_batch.py`), single variant 11, both
   corpora (50% batch discount).
3. **Re-estimate from measured cost**, then Sonnet WT only if the remainder covers it
   (Sonnet NT both corpora already exists — PR#80).
4. **Regrade** with `tools/e2e_regrade.py` (auto-detects the 16K cap → exact e2e,
   `e2e_strict` headline).

## Watch-outs

- **Corpus fidelity:** the probe's two arms must share GT (fresh generate, not cache) and the
  same keys file, or the A-vs-B comparison is confounded.
- **Budget:** $238 funded; smoke already spent ~$0.33. WT is list-price (no caching help).
- **ISS-024(d) job 19293221** (Qwen with-tools, 72h wall from 2026-07-11): leave running;
  it's the resolver for strict-undecided cells (9B solve, 35b validate_plan, simulate). When
  it lands and the cluster is reachable (ping Omer first per house rule), sync + regrade.
- **Phase 5 (analyzer):** still owed — the analyzer/master tables must read `e2e_strict` as
  the headline column and render bounds where censored. Not started.

## Commits this session (branch `feat/e2e-scoring-overlay`)

- `82ffced` D2b → strict headline (dual e2e columns + `e2e_d2b_compare.py` + audit doc)
- `8c537bb` frontier framework decisions recorded (D1=B, staged probe, $238)
- `9668f39` frontier_runner.py (framework B)
- `4e8aca0` cached-GT fast path + multi-turn caching fix + live smoke
- `30f9ce3` caching = net-loss finding recorded (budget at list price)
- (`701910d` = Omer's `--iss024d` status-board profile, separate)
