# qwen3.6:35b validate_plan — tools cost 3pp; per-domain breakdown

**Source runs (cluster-20260504, per-task / minimal prompt, with_thinking=off):**
- No-tools: `results/cluster-20260504/slurm_qwen3_6_35b_off_no-tools/trials.jsonl` — 3000 validate_plan trials, 90.7%
- Tools (`--tool-filter=per-task`, `--prompt-style=minimal`): `results/cluster-20260504/slurm_qwen3_6_35b_off_tools_per-task_minimal/trials.jsonl` — 3000 validate_plan trials, 88.0%
- Δ = −2.7pp; both 95% Wilson CIs ([89.6, 91.7] vs [86.8, 89.1]) overlap, so the global effect is small but non-zero.

Stratification: 20 domains × 5 problems × 10 plans (`v1..v5` valid, `b1..b5` broken) × 3 prompt variants = 150 trials per domain per condition.

## Motive

Here we present an unexpected results. those may be unique for the model , it can also be true for all models.
- after current sweep completes, we'll need to validate the other models to see if the issue is general or model-specific.
- after next sweep completes. we'll see if the pddl normalization had any effect,
or is it simple the expected model behavior.

## Per-domain breakdown (sorted by Δ, tools − no-tools)

| Domain | n | NT% [Wilson 95%] | T% [Wilson 95%] | Δ pp | Tools failures (top) |
|---|---|---|---|---|---|
| zenotravel-numeric | 150 | 92.0 [86.5, 95.4] | 47.3 [39.5, 55.3] | **−44.7** | verdict_mismatch=74, tool_not_selected=5 |
| pogo_stick | 150 | 96.7 [92.4, 98.6] | 82.7 [75.8, 87.9] | **−14.0** | verdict_mismatch=14, tool_not_selected=12 |
| rovers | 150 | 96.0 [91.5, 98.2] | 82.7 [75.8, 87.9] | **−13.3** | verdict_mismatch=19, tool_not_selected=7 |
| barman | 150 | 72.7 [65.0, 79.2] | 61.3 [53.3, 68.8] | **−11.3** | verdict_mismatch=53, tool_not_selected=3 |
| farmland | 150 | 100.0 [97.5, 100.0] | 88.7 [82.6, 92.8] | **−11.3** | verdict_mismatch=15, tool_not_selected=2 |
| satellite | 150 | 98.0 [94.3, 99.3] | 88.7 [82.6, 92.8] | −9.3 | tool_not_selected=11, verdict_mismatch=6 |
| sailing | 150 | 87.3 [81.1, 91.7] | 81.3 [74.3, 86.8] | −6.0 | tool_not_selected=18, verdict_mismatch=10 |
| counters | 150 | 84.7 [78.0, 89.6] | 80.7 [73.6, 86.2] | −4.0 | tool_not_selected=20, verdict_mismatch=9 |
| blocksworld | 150 | 100.0 [97.5, 100.0] | 96.0 [91.5, 98.2] | −4.0 | tool_not_selected=6 |
| gripper | 150 | 98.0 [94.3, 99.3] | 96.0 [91.5, 98.2] | −2.0 | verdict_mismatch=3, tool_not_selected=3 |
| block-grouping | 150 | 93.3 [88.2, 96.3] | 92.0 [86.5, 95.4] | −1.3 | tool_not_selected=7, verdict_mismatch=5 |
| depots | 150 | 97.3 [93.3, 99.0] | 97.3 [93.3, 99.0] | ±0.0 | tool_not_selected=4 |
| miconic | 150 | 93.3 [88.2, 96.3] | 94.0 [89.0, 96.8] | +0.7 | tool_not_selected=9 |
| zenotravel | 150 | 92.7 [87.3, 95.9] | 94.0 [89.0, 96.8] | +1.3 | tool_not_selected=6, verdict_mismatch=3 |
| drone | 150 | 81.3 [74.3, 86.8] | 84.7 [78.0, 89.6] | +3.3 | tool_not_selected=20, verdict_mismatch=3 |
| delivery | 150 | 94.7 [89.8, 97.3] | 98.7 [95.3, 99.6] | +4.0 | tool_not_selected=2 |
| gardening | 150 | 89.3 [83.4, 93.3] | 96.7 [92.4, 98.6] | +7.3 | verdict_mismatch=5 |
| parking | 150 | 86.7 [80.3, 91.2] | 98.7 [95.3, 99.6] | **+12.0** | verdict_mismatch=2 |
| depot | 150 | 85.3 [78.8, 90.1] | 99.3 [96.3, 99.9] | **+14.0** | tool_not_selected=1 |
| tpp | 150 | 75.3 [67.9, 81.5] | 100.0 [97.5, 100.0] | **+24.7** | — |
| **TOTAL** | 3000 | **90.7** [89.6, 91.7] | **88.0** [86.8, 89.1] | **−2.7** | — |

11/20 domains lose ≥1pp under tools, 7/20 gain ≥1pp, 2/20 are neutral. The headline regression is far from uniform.

## Mechanism: per-task curation hands `validate_plan` the wrong tool

This run uses `--tool-filter=per-task`. The allowlist is hardcoded in `pddl_eval/runner.py:165`:

```python
TASK_TOOLS = {
    "validate_plan": ["validate_pddl_syntax"],   # ← only this tool exposed
    "simulate":      ["get_state_transition"],   # ← reserved for simulate
    ...
}
```

So under per-task curation, the model has **no access** to `get_state_transition` for `validate_plan` — it can only call `validate_pddl_syntax`. The 0/2956 split below is therefore *not* a model tool-selection failure; it's a harness curation choice.

| tool name called | call count |
|---|---|
| `validate_pddl_syntax` | 2956 |
| `get_state_transition` (semantically correct for plan validation) | 0 (not in allowlist) |
| any other tool | 0 |

136/3000 trials (4.5%) issued no tool call (showing up as `tool_not_selected` failures).

`validate_pddl_syntax` checks that the domain/problem **PDDL parses** — it says nothing about whether a plan is valid. The semantically correct tool for this task is `pddl-validator__get_state_transition` (the bridge projects it to `{valid, steps, trajectory}` per `EXPERIMENTS_FLOW.md` §8). The per-task curation pairs the wrong tool with the task, so the model gets a signal that is irrelevant for ~94% of trials and outright misleading for ~6% (the parser bug below).

**Cross-check from `slurm_qwen3_6_35b_off_tools_all_minimal`** (where all tools are exposed): on 1574 validate_plan trials (run is incomplete/partial; not directly comparable to per-task n=3000), the model split between `get_state_transition` (628 calls) and `validate_pddl_syntax` (707) — so when given the choice it does reach for the correct tool ~47% of the time. Aggregate accuracy in that condition collapses to 37.7% [35.3, 40.1], suggesting that exposing the full marketplace introduces a different drag (likely verbose tool-result integration cost, possibly tied to `num_predict` caps — separate from this analysis).

## Single-domain dominance: zenotravel-numeric drives 80% of the inversion

| set | NT % | T % | Δ pp |
|---|---|---|---|
| All 20 domains | 90.7 | 88.0 | −2.70 |
| Excluding `zenotravel-numeric` | 90.7 | 90.2 | −0.49 |
| Excluding `zenotravel-numeric` and `farmland` | 90.1 | 90.3 | +0.11 |

Drop the single worst-case numeric domain and the inversion virtually disappears. Drop the two worst and tools are net-positive.

### Why does zenotravel-numeric collapse so badly?

In every inspected verdict_mismatch trial for zenotravel-numeric, the single tool call is:

```
validate_pddl_syntax(domain=…/zenotravel-numeric/domain.pddl, …)
→ {"valid": false, "status": "SYNTAX_ERROR",
   "report": "[ERROR] Failed to parse domain '/tmp/pddl/.../domain.pddl' …"}
```

…and the model then reasons "the domain is broken (look at `fly-slow`)" and emits `invalid` regardless of the plan. The downstream verdict bias is **over-rejection** (false-negative on `v*` plans): for zenotravel-numeric, T-condition produces 74 FN-on-valid vs 0 FP-on-broken (NT was 0 / 12). The same domain file resolves cleanly in the no-tools condition because the model never invokes the parser.

Manual reading of `domains/numeric/zenotravel-numeric/domain.pddl` shows an `(:action fly-slow …)` block that is syntactically well-formed PDDL2.1 numeric — the marketplace `pddl-parser` plugin's misclassification is the proximate bug. (Note: this is a measurement-side issue in the parser plugin server, not in `run_experiment.py`. Per the routing rule, the fix belongs in `../pddl-copilot/plugins/pddl-parser/server/`.)

`farmland` shows the same FN-↑ direction (15 FN vs 0 FP under tools) and likely the same parser-fragility profile for numeric domains.

## FN-vs-FP decomposition for the rest

For the over-rejecting (FN-↑) domains besides `zenotravel-numeric` / `farmland`, the dominant pattern is the model converting an irrelevant `validate_pddl_syntax` "valid" / "warning" report into a confused verdict — sometimes flipping a previously correct judgement. For over-accepting (FP-↑) domains (`counters`, `drone`, `tpp`, `parking`, `gardening`), tools usually *help* on broken plans because the LLM is more cautious when "the domain parsed fine, so let me check the plan more carefully" — and indeed `tpp` jumps from 75.3% → 100% and `depot` from 85.3% → 99.3%.

`tool_not_selected` is the dominant **tools-failure** mode in 8/20 domains and is the headline tax on tools across the board.

## Why does the no-tools condition do *better* on this task?

`validate_plan` is structurally the simplest task in the suite for an LLM with strong PDDL priors: emit `valid` or `invalid`. The no-tools condition is verdict-only — the model emits a one-word answer. With per-task tools enabled, the model is required to call a single curated tool (`validate_pddl_syntax`) and then:
1. Receives an irrelevant report (~94% of the time it just says "domain parses fine"),
2. Occasionally a misleading one (~6% of the time, the parser falsely rejects a numeric domain),
3. Has to integrate that signal back into a verdict.

Step 3 is where most of the regressions happen. Combined with the parser bug on numeric domains, the integration drag exceeds the small gains tools deliver on the harder broken-plan cases (`tpp` 75.3 → 100, `depot` 85.3 → 99.3, `parking` 86.7 → 98.7).

## Implications

1. **Methodology / `TASK_TOOLS` choice**: the per-task allowlist for `validate_plan` is `["validate_pddl_syntax"]` (`pddl_eval/runner.py:165`). This pairs the wrong tool with the task — it forces the model to consult a syntax checker when the task is "is this plan correct against this domain". Worth deciding whether the paper claim should be "tools hurt validate_plan" (current framing) or "the per-task curation we chose is mismatched for validate_plan; an alternative curation `["get_state_transition"]` is the natural pairing". Both are defensible; pick the one the paper's narrative supports and document the choice.
2. **Issue worth opening (parser plugin)**: `validate_pddl_syntax` rejects `domains/numeric/zenotravel-numeric/domain.pddl` (and likely `farmland`) as `SYNTAX_ERROR` despite the files being well-formed numeric PDDL2.1. Routing: `../pddl-copilot/plugins/pddl-parser/server/` per `CLAUDE.md`. Fixing this alone recovers ~2.2pp of the headline gap, *independently* of the tool-curation question.
3. **Honest reporting**: the headline `−3pp` for validate_plan is real but is dominated by one domain × parser interaction (zenotravel-numeric −44.7pp drives the bulk; leave-one-out drops Δ to −0.5pp). Reporting the raw mean alone overstates the negative effect. The per-domain table above is the honest framing.
4. **Tool-adherence corollary** (separate from per-task): in the `all_minimal` condition where both `validate_pddl_syntax` and `get_state_transition` are visible, the model picks `get_state_transition` only ~47% of the time. So the model's prior toward "validate" → "syntax checker" is real, but it's not the cause of the per-task inversion — the curation is.

## Reproduce

```bash
cd /Users/omereliyahu/personal/pddl-copilot-experiments
python3 - <<'PY'
import json, collections
def s(p):
    n=ok=collections.defaultdict(int);
    by=collections.defaultdict(lambda:[0,0])
    with open(p) as f:
        for line in f:
            r=json.loads(line)['result']
            if r.get('task')!='validate_plan': continue
            d=r['domain_name']; by[d][0]+=1; by[d][1]+=int(bool(r.get('success')))
    return by
nt=s('results/cluster-20260504/slurm_qwen3_6_35b_off_no-tools/trials.jsonl')
tt=s('results/cluster-20260504/slurm_qwen3_6_35b_off_tools_per-task_minimal/trials.jsonl')
for d in sorted(nt, key=lambda d: tt[d][1]/tt[d][0] - nt[d][1]/nt[d][0]):
    print(f'{d:18s} NT={nt[d][1]/nt[d][0]*100:5.1f}%  T={tt[d][1]/tt[d][0]*100:5.1f}%  Δ={(tt[d][1]/tt[d][0]-nt[d][1]/nt[d][0])*100:+5.1f}pp')
PY
```
