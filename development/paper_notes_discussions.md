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

## 2026-05-29 — with-tools numbers are not underperforming (external benchmark calibration)

Full note: `development/baseline_comparison_tool_use_benchmarks.md`. Compared sweep-5 v1 with-tools results to BFCL, τ-bench/τ²-bench, and the 2025 MCP-native suites (MCP-Universe, LiveMCP-101, MCP-Bench, MCPEval, MCPToolBench++, LiveMCPBench).

- **Bottom line: our with-tools agents are expected, not broken.** Every pattern we see is documented externally; our ≥9B steered numbers (89–98% agg) sit at the *top* of the open-model envelope.
- **Right analog = BFCL single-turn, NOT τ-bench multi-turn.** Our task is ~1 tool-call + light interpretation (the planner/validator is correct-by-construction once called), where strong models score 0.85–0.94 — not 5.4-step multi-server orchestration where even GPT-5 tops out at 44–58% (MCP-Universe 43.7%, LiveMCP-101 58.4%). **Do not compare our 95% to GPT-5's 44%** — different difficulty.
- **Same-size open models score far lower on the broad suites** (LiveMCP-101: Qwen3-8B 4.0%, Llama-3.1-8B 1.0%, Qwen3-235B 22.8%), so sub-35B open models being a widespread is the norm; ours look good because our task surface is narrow and bounded.
- **Tool-adherence is the textbook shape:** low-level tool selection saturates ~96–100% for capable models (MCP-Bench tool-name validity 96–100%) while the 0.8B "calls-the-tool-but-fails-to-use-output" mode matches MCPToolBench++ (AST 0.6–0.9 vs Pass@1 0.2–0.5).
- **Thinking-mode suppressing tool-calls + steering restoring it are both documented:** ThinkBrake (Qwen3-4B, +8.4 recoverable on BFCL by stopping over-reasoning); Databricks eval (+58.7 pts relevance from a system-prompt change) — same direction and magnitude as our `tl-neut`→`tl-ster` tool% lift (+20–55) and the Gemma3-MoE think-on/neutral collapse on **solve** tool% (100 off → 23 on/neut, recovered to 77 on/steered).
- **Carve-out — `validate_plan` is NOT thinking-collapse evidence.** Its tool%/success craters at think=OFF too (gemma off/neut val-plan tool% 18 while same-arm solve/val-dom/val-prob/sim ~100), i.e. the known FastMCP arg-error binning bug (`project_validate_plan_fp_scoring_bug`). The relabel is applied only in `build_deck.py`, NOT in `aggregate.py`/`table.py`, so `master.md`/`aggregate.md` val-plan figures are un-relabeled; trust the deck-built numbers for val-plan. Reproduces in sweep5v2.
- **Caveat:** a few supporting papers in the note have post-Jan-2026 arXiv dates (2601/2604/2605.x) surfaced by web agents — verify abstracts before citing; the load-bearing sources (BFCL, τ-bench, the six MCP suites, Databricks, ThinkBrake 2510.00546) are pre-cutoff and solid.
