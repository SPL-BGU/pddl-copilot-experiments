# Frontier rerun — handoff (fresh session pickup)

**Date:** 2026-07-11
**Branch:** `feat/e2e-scoring-overlay` (working tree clean; verify it's pushed)
**Companions:** `frontier_rerun_framework_decision.md` (decisions),
`decision_audit_grading_and_frontier.md` (external-literature audit + all reasoning),
`tool_call_vs_final_output_grading.md` (grading overlay). This doc = the "what to do next".

---

## One-paragraph state

**Stage-1 A-vs-B probe DONE (2026-07-11): fully concordant — 0/100 discordant pairs,
no turns/token shift, stage 2 NOT triggered.** Framework B is licensed as the sole
full-run harness; the probe stands as the bounded gross-defect check (P2 framing).
Caching verdict at stratified scale: **ACTIVE, saves ~15%** (the 3-trial smoke's +6%
net-loss was a small-sample artifact) → keep `cache_control` ON. Full detail + numbers
recorded in `decision_audit_grading_and_frontier.md` §2.3 (STAGE-1 RESULT block).
Artifacts: `tools/make_stage1_keys.py`, `tools/frontier_ab_compare.py`,
`.local/frontier/{stage1_keys.jsonl,a_probe,b_probe}`. The next step is the **full
Haiku run per D4** (WT via `frontier_runner.py`, NT via the Batch API, canonical +
anon corpora), then re-estimate cost before Sonnet. Spent so far: ~$7.4 of $238.
Separately, the Qwen ISS-024(d) job **19293221** is still running on the cluster and
is the resolver for the strict-grading-undecided cells — leave it alone.

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
1b. **Tool-result verbosity can overflow even the 200K frontier window.** Full-run
   finding (2026-07-11, canonical WT): `simulate depot/p01` — a single
   `get_state_transition` result pushed turn 2 to ~498K tokens → API 400. Fixed in
   `frontier_runner.py` (commit 8b5d276): recorded as `FR_TRUNCATED_NO_ANSWER` /
   `done_reason=length` with tool_calls kept (open-arm-equivalent semantics), NOT
   infra. Paper-relevant: simulate's sole-source status has a *tool-side* capacity
   boundary independent of model quality; watch for more hits on big domains.
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
