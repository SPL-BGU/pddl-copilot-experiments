# Frontier rerun — handoff (fresh session pickup)

**Date:** 2026-07-11
**Branch:** `feat/e2e-scoring-overlay` (working tree clean; verify it's pushed)
**Companions:** `frontier_rerun_framework_decision.md` (decisions),
`decision_audit_grading_and_frontier.md` (external-literature audit + all reasoning),
`tool_call_vs_final_output_grading.md` (grading overlay). This doc = the "what to do next".

---

## One-paragraph state

The frontier with-tools rerun is **decided, built, and live-verified**; nothing is
running for it yet. The runner (`tools/frontier_runner.py`, framework B = SDK Tool Runner)
passed a real 3-trial Haiku smoke end-to-end. The immediate next step is the **stage-1
paired A-vs-B harness probe** (~100 trials), which needs one thing that doesn't exist yet:
a **stratified keys file**. Separately, the Qwen ISS-024(d) job **19293221** is still
running on the cluster and is the resolver for the strict-grading-undecided cells — leave
it alone.

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

1. **Prompt caching is NOT a cost lever for this workload.** Live smoke: caching ACTIVE but
   **net +6%** (short ~2-turn trials, unique per-trial domain/problem context, 1.25× write
   premium not recouped). **Budget the WT arm at no-cache list price** ($1/$5 Haiku, $3/$15
   Sonnet). The stage-1 stratified probe (all 5 tasks, not 3 simulate trials) settles whether
   any task benefits; the runner prints `ACTIVE / NET-LOSS / INACTIVE` so the answer reads off
   the summary. If net-loss corpus-wide → disable caching for the full run (remove the
   `cache_control=` arg in `run_one`; it only adds cost).
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

## NEXT STEP — stage-1 paired A-vs-B probe

1. **Write a stratified keys-file generator** (does not exist yet). Output = JSONL, one
   selection key per line: `{task, domain_name, problem_name, plan_label, prompt_variant}`.
   Target ~100 trials, stratified across all 5 tasks (and a spread of domains). Both scripts
   already consume `--keys-file` with exactly this shape (see `select_jobs` in
   `frontier_runner.py` and the `wanted` set builder in `claude_api_tools_probe.py`). The
   A-probe's old no-tools cost-probe keys files (under `.local/…`) are the template for the
   format. Pin a single `prompt_variant` (D3) so the probe is single-variant.
2. **Run the SAME keys file through both arms** (fresh GT — do NOT pass `--use-cached-gt`
   for the real probe):
   ```bash
   python tools/frontier_runner.py       --model claude-haiku-4-5 \
       --marketplace-path ../pddl-copilot --keys-file <keys>.jsonl --out .local/frontier/b_probe
   python tools/claude_api_tools_probe.py --model claude-haiku-4-5 \
       --marketplace-path ../pddl-copilot --keys-file <keys>.jsonl --out .local/frontier/a_probe
   ```
3. **Compare A vs B:** success (McNemar on discordant pairs), turns, tokens, and real $.
   This is the gate that licenses comparing frontier numbers to the Qwen arm (HAL
   model/scaffold/benchmark separation). Record in `decision_audit_grading_and_frontier.md`
   §2.3. Decide caching on/off from the summary's ACTIVE/NET-LOSS line.
4. If stage-1 concordant → proceed to the **full run** per D4 budget sequence (Haiku both
   arms first). Regrade with `tools/e2e_regrade.py` (it auto-detects the 16K cap → exact
   e2e, `e2e_strict` headline).

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
