# Paper Notes — Thoughts & Discussions

Running log of bottom-line conclusions from paper-related discussions. Each entry is dated, scoped to one topic, and bulleted so future-me (or a co-author) can scan it in 30 seconds. No reasoning trace — just the conclusion and the load-bearing evidence/caveat.

When a bullet later turns out wrong or superseded, strike it through and add the correction below; don't silently rewrite history.

---

## 2026-05-24 — thinking-trace logging on sweep5

- **Scoring is not bugged.** Success rates, tool-selected, plan/verdict extraction, latency, token counts are all arithmetically correct. vLLM strips reasoning from `msg.content` server-side; scoring sees clean final-answer text.
- **Reasoning traces are gone for sweep5.** `--reasoning-parser qwen3` did not populate `reasoning_content` for the Qwen3.5/3.6 family in this run. `result.thinking` is empty across every think=on cell (4560-7141 trials per cell, 0 with thinking content). Token counts confirm reasoning *did* run (think=on mean completion ~6.5k tok vs think=off ~1.7k on Qwen3.5_4B).
- **Failure-bucket attribution is degenerate.** Every length-truncated think=on trial gets `FR_TRUNCATED_NO_ANSWER`; `FR_THINK_OVERFLOW` is always 0 because its trigger requires non-empty `thinking_text`. Collapse the two buckets in any paper table.
- **For the paper: disclose as a logging-only limitation.** Methods footnote: reasoning-parser failed to surface CoT for Qwen3.5/3.6; per-trial traces not archived; reasoning is evidenced by completion-token medians. Optionally rerun 20-50 trials with a working parser (or keep `<think>` in content) for an appendix of qualitative trace examples.

## 2026-05-24 — small-model think=on cells are budget-cliffed (the bigger problem)

- **Sub-9B think=on no-tools cells measure decode budget, not capability.** Length-truncation rates: Qwen3.5_0.8B 99.8%, 4B 91%, 9B 73%, 35B 11%. Success tracks inversely: 0.04% / 7% / 16.5% / 74%. solve cap is `num_predict=8192` (`runner.py:99-105`), and Qwen3.5_4B p90 completion = 8192 — pinned at the cap.
- **This is a finding, not a bug.** "Small thinking models cannot fit a complete reasoning trace within budgets that suffice for larger models" is paper-worthy when reported as such.
- **Don't bump context to fix it.** The 32K ctx-bump smoke (2026-05-21, b527f71) caused `format_parse_fail` +22-36 per model; bigger isn't simply better, and the regression isn't understood. Cost of debugging before deadline > benefit.
- **Paper scoping decision:** focus headline claims on ≥9B (clean cells); report length-truncation rate alongside success rate so a reader sees the cliff explicitly; either drop sub-9B think=on from the headline table or label those cells "budget-constrained, not capability-bound."
- **Large-model think=on is clean.** Qwen3.6_35B 11% length+empty, ≥9B all <10% on tools cells — that's where the paper's signal lives.
