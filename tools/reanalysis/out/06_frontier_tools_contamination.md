# Frontier contamination, tool arm: Claude Haiku 4.5, renamed minus canonical

## Settings check

- rows: canonical 1520, renamed 1520, shared keys 1520; infrastructure-failure rows 0 / 0
- run meta (every summary file, corpus field aside): model `claude-haiku-4-5`, sdk `0.109.2`, temperature 0, think off, max_iterations 10, backend `anthropic-tool-runner`; corpus field summary_20260712_012257.json: canonical, summary_20260712_101535.json: canonical, summary_20260712_064009.json: anon
- max tokens: not recorded in the run meta. Both cells ran with the runner's per-task default (no `--num-predict` override; `pddl_eval.runner.DEFAULT_NUM_PREDICT`). Rows stopped by the budget: canonical 19 ({'simulate': 19}), renamed 19 ({'simulate': 19}); completion tokens of those rows 5786–8892 vs 3460–8964
- rows that differ from the cell's first full run (re-run on resume): canonical simulate depot p01 (first run: exception, stored: ok; 2 snapshots)
- mismatches found: none

## Paired test, T7 method

Tool-verified (`success`):

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Haiku 4.5 tools solve | 100 | 100.0 | 100.0 | +0.00 | [+0.00, +0.00] | domain (k=20) | [+0.00, +0.00] | 0.00 | 0.000 | criterion met (ceiling: low information) |
| Haiku 4.5 tools v_dom | 120 | 98.3 | 99.2 | +0.83 | [-1.71, +3.37] | domain (k=20) | [-1.67, +3.33] | 2.54 | 0.005 | criterion met (ceiling: low information) |
| Haiku 4.5 tools v_prob | 200 | 96.5 | 97.0 | +0.50 | [-1.35, +2.35] | problem (k=200) | [-1.00, +2.00] | 1.85 | 0.000 | criterion met (ceiling: low information) |
| Haiku 4.5 tools v_plan | 1000 | 98.9 | 98.4 | -0.50 | [-1.05, +0.05] | domain (k=20) | [-1.10, -0.10] | 0.55 | 0.000 | criterion met (ceiling: low information) |
| Haiku 4.5 tools sim | 100 | 97.0 | 98.0 | +1.00 | [-0.73, +2.73] | domain (k=20) | [+0.00, +3.00] | 1.73 | 0.000 | criterion met (ceiling: low information) |
| Haiku 4.5 tools pooled (5 tasks) | 1520 | 98.5 | 98.4 | -0.13 | [-0.62, +0.36] | domain (k=20) | [-0.59, +0.33] | 0.49 | 0.000 | criterion met (ceiling: low information) |

Delivered (`e2e_strict`, pairs determinate on both sides):

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Haiku 4.5 tools solve | 100 | 95.0 | 97.0 | +2.00 | [-2.95, +6.95] | domain (k=20) | [-2.00, +7.00] | 4.95 | 0.154 | criterion not met (unresolved) |
| Haiku 4.5 tools v_dom | 120 | 98.3 | 99.2 | +0.83 | [-1.71, +3.37] | domain (k=20) | [-1.67, +3.33] | 2.54 | 0.005 | criterion met (ceiling: low information) |
| Haiku 4.5 tools v_prob | 200 | 96.5 | 96.5 | +0.00 | [-2.03, +2.03] | problem (k=200) | [-1.50, +1.50] | 2.03 | 0.000 | criterion met (ceiling: low information) |
| Haiku 4.5 tools v_plan | 1000 | 98.8 | 98.4 | -0.40 | [-0.94, +0.14] | domain (k=20) | [-1.00, +0.00] | 0.54 | 0.000 | criterion met (ceiling: low information) |
| Haiku 4.5 tools sim | 83 | 59.0 | 55.4 | -3.61 | [-12.77, +5.54] | domain (k=19) | [-12.20, +4.94] | 9.16 | 0.398 | criterion not met (unresolved) |
| Haiku 4.5 tools pooled (5 tasks) | 1503 | 96.0 | 95.7 | -0.27 | [-1.11, +0.58] | domain (k=20) | [-1.06, +0.53] | 0.84 | 0.000 | criterion met (ceiling: low information) |

Outcome flips between the corpora (same key) and censored pairs left out of the delivered test:

| task | tool-verified right→wrong / wrong→right | delivered right→wrong / wrong→right | delivered pairs left out (censored on either side) | delivered bounds, canonical / renamed |
|---|---|---|---|---|
| solve | 0 / 0 | 2 / 4 | 0 | 95.0 / 97.0 |
| validate_domain | 1 / 2 | 1 / 2 | 0 | 98.3 / 99.2 |
| validate_problem | 2 / 3 | 3 / 3 | 0 | 96.5 / 96.5 |
| validate_plan | 5 / 0 | 5 / 1 | 0 | 98.8 / 98.4 |
| simulate | 0 / 1 | 10 / 7 | 17 | [52.0, 64.0] / [46.0, 62.0] |

Calling (`tool_selected`): canonical 1520/1520, renamed 1520/1520.

