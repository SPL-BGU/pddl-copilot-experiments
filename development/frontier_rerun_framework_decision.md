# Frontier rerun (Haiku + Sonnet): which harness framework?

**Date:** 2026-07-11
**Status:** decision doc — fill each `> MY DECISION:` slot, then the rerun gets built + submitted
**Context:** DECIDED 2026-07-11: fresh Haiku + Sonnet single-tool runs (the stored frontier
corpora are 75–100% blind to end-to-end grading — see
`development/tool_call_vs_final_output_grading.md` §Phase 4). Omer's driver for this doc:
a clean **transition from the single-tool experiments to PlanBench** — PlanBench frontier
runs on the Claude API, so whatever framework it uses must also be assessed inside the
single-tool experiment. Companion: `project_frontier_phase_design` memory (the old
A/B/C harness fork this supersedes/refines).

---

## The bottom line, simply

We need to pick who runs the "agent loop" (call model → model asks for a tool → run the
tool → feed the result back → repeat until it answers) for the frontier with-tools runs.
Three candidates:

- **A. Our own loop (what exists today).** `tools/claude_api_tools_probe.py` — we wrote
  the loop ourselves on the Anthropic SDK, copying the Qwen harness rules exactly.
- **B. The Claude API framework's loop (Tool Runner).** The official Anthropic SDK ships
  a ready agent loop (`client.beta.messages.tool_runner`). It even ships MCP helpers that
  plug our existing local plugin servers straight in — no rewrite of the tools.
- **C. The full Claude Code / Agent SDK harness.** The deployed product (skills,
  subagents, the whole scaffold).

**My recommendation: B**, built once as a shared module used by BOTH the single-tool
rerun and the PlanBench with-tools backend — that IS the transition you want — plus a
small paired probe of A-vs-B on one model (~100 trials) so the paper can quantify the
"harness effect" instead of hand-waving it. C stays deferred as an optional
"product-fidelity" arm later; it is a different experiment (scaffold + tools), not the
comparison arm.

## Why B (and not A or C)

- **PlanBench continuity (your driver).** PlanBench's Anthropic backend
  (`planbench/engine.py:_anthropic_chat`) already calls the Claude API directly — but
  only for no-tools (one prompt in, text out). Its with-tools arm does not exist yet.
  Pick B and we build ONE tool-loop module that both benchmark families share; the
  single-tool rerun then doubles as the assessment of the exact framework PlanBench will
  use. Pick A and PlanBench either inherits our homemade loop (more custom code to
  defend) or diverges (no transition).
- **Tools stay identical.** The Anthropic SDK's MCP helpers (`anthropic.lib.tools.mcp`,
  `async_mcp_tool` over a stdio client) consume our existing pddl-solver/validator
  plugin servers as-is. Same tools, same fixtures, same grading — only the loop owner
  changes.
- **Less of our code in the methods section.** "The official SDK tool runner, version
  pinned" is easier to report and defend than "our custom loop". It still gives per-turn
  hooks (loop cap via `max_iterations`, per-turn logging, cache_control injection), so
  we keep MAX_TOOL_LOOPS-equivalent control and full `tool_calls[]` capture for the
  trials.jsonl schema.
- **Against A as the headline:** it maximizes comparability with the Qwen arm, but it's
  a probe-grade codepath we'd have to harden anyway, and it buys no PlanBench bridge.
  It survives as the ablation arm (we already have 75-trial probes on it — the paired
  probe anchors old data to new).
- **Against C now:** heaviest scaffold confound (lift = tools + skills + subagents, not
  tools), Anthropic-locked, hardest to pin/version in a paper, and PlanBench would NOT
  run on it — so it breaks the very continuity this rerun is for. Keep it as a possible
  third arm later ("deployed-product ceiling"), explicitly labeled.

## What stays fixed regardless of framework (already decided / apparatus)

- Models: `claude-haiku-4-5` + `claude-sonnet-4-6` (same roster as the existing frontier
  corpora — continuity; model swap would orphan the old no-tools corpus).
- Single prompt variant for frontier (decided 2026-06-22; no-tools corpus is v11-13 —
  the rerun's no-tools arm should keep 3 variants ONLY if we want strict comparability
  with the old Sonnet NT corpus; see D3).
- API split: no-tools → Batch API (50% cheaper); with-tools → live calls + prompt
  caching (the cost lever; note Haiku's minimum cacheable prefix is 4096 tokens — our
  stable prefix must clear that or caching silently no-ops).
- Output contract: whatever the framework, the runner writes the standard trials.jsonl
  row (full response under the 16384 snapshot, `tool_calls[]` with results, done_reason)
  so `tools/e2e_regrade.py` and the analyzer work unchanged — and the run is exactly
  end-to-end gradeable from day one.
- Grading: end-to-end primary + tool-verified diagnostic (the 2026-07-11 decisions).

## Rough cost (order-of-magnitude, from measured prior runs)

> ⚠️ CACHING CORRECTION (live smoke, 2026-07-11): the "caching cuts WT cost" assumption
> below is likely FALSE for this workload. A 3-trial Haiku live smoke
> (`tools/frontier_runner.py`) shows caching ACTIVE but a **net +6% loss** — short
> trials (~2 turns) with unique per-trial domain/problem context don't recoup the 1.25×
> write premium. **Budget the WT arm at no-cache list price** until the stage-1 stratified
> probe says otherwise. See `development/decision_audit_grading_and_frontier.md` §2.5.

- Haiku, full single-variant grid ≈ 1,520 trials/condition; the plain (no-cache)
  with-tools estimate was ~$49; ~~caching should cut it substantially~~ (caching does NOT
  cut it — see correction). Both arms ≈ $60–100 **at list price**.
- Sonnet ≈ 3× Haiku's token prices; old Sonnet NT both-corpora (3 variants) measured
  $81.51 → single-variant NT ≈ $27; WT ~~with caching~~ at list price, rough $100–200.
- Total ballpark: **$200–350** for both models, both arms, both corpora (sweep5v2 +
  sweep6 fixtures) — now firmly at list price (no caching discount). A firmer number
  lands after the A-vs-B probe (~$5–50, staged).

## Decisions

**D1 — Framework for the frontier rerun (and the PlanBench with-tools backend).**
- **A.** Our existing bare loop, hardened.
- **B.** Claude API framework (SDK Tool Runner + MCP helpers), one shared module for
  single-tool + PlanBench. *(my recommendation)*
- **C.** Claude Agent SDK / Claude Code harness.

> MY DECISION: B

**D2 — Paired harness probe (A vs B, one model, ~100 trials, ~$5–10).**
Runs the same trials through both loops to measure the harness effect and anchor the new
framework to the existing probe data. *(my recommendation: yes, before the full run)*

> MY DECISION: yes

**D3 — No-tools arm variants.** Keep 3 variants (v11-13) for strict comparability with
the old Sonnet no-tools corpus (~3× NT cost), or single variant everywhere (cheaper,
matches the frontier single-prompt decision, old corpus still comparable per-variant)?
*(my recommendation: single variant; slice the old corpus to the same variant when
comparing)*

> MY DECISION: single variant; slice the old corpus to the same variant when comparing

**D4 — Scope & budget approval.** Both models × both arms × both corpora, ballpark
$200–350, exact estimate after the D2 probe. Approve, or trim (e.g. Haiku first,
Sonnet after reading Haiku)?

> MY DECISION: approved; budget in calude api currnetly funded with 238$.

## Execution sketch (once decided)

1. Build `tools/frontier_runner.py` (or extend the probe) on the chosen framework:
   loads fixtures + prompts from `pddl_eval`, drives the loop, writes standard
   trials.jsonl (16K snapshots), prompt caching on, per-trial cost logging.
2. D2 probe → compare A-vs-B on tool-verified + e2e + turns/tokens → record in this doc.
3. Full run per D4 scope (background, resumable, budget guard).
4. Regrade with `tools/e2e_regrade.py` (exact, no censoring) → frontier e2e numbers for
   the paper; the same module then becomes the PlanBench with-tools backend.
