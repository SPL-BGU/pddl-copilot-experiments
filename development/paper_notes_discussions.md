# Paper Notes — Thoughts & Discussions

Running log of bottom-line conclusions from paper-related discussions. Each entry is dated, scoped to one topic, and bulleted so future-me (or a co-author) can scan it in 30 seconds. No reasoning trace — just the conclusion and the load-bearing evidence/caveat.

When a bullet later turns out wrong or superseded, strike it through and add the correction below; don't silently rewrite history.

---

## 2026-06-19 — With-tools frontier probe: capability ladder + Haiku-WT decision (cost blocked)

- **Probed** with-tools (live agentic loop, can't batch → list price) for Sonnet 4.6 + Haiku 4.5 on the same 75-trial stratified canonical sample; full writeup in `development/with_tools_probe_findings.md`.
- **Four-way ladder (success):** tools take every task to ~100% for both models. The tools *lift* is **2–5× larger for the weaker model** on validation (validate_problem +50.0 Haiku vs +10.3 Sonnet; validate_plan +16.3 vs +2.7). Sonnet no-tools validation holds high (90–97%); **Haiku no-tools collapses** (validate_problem 50%, validate_plan 83.7%, validate_domain 83.3%). **Conclusion: validation competence is capability-gated; tools erase the gap — and the gap they close grows as the model weakens.**
- **Floors model-agnostic:** simulate 0% and solve ~29–33% unaided for *both* Sonnet and Haiku → sole-source holds across the capability range.
- **Cost-of-pass:** at the frontier tools win only on simulate (Sonnet's unaided baseline is good+cheap elsewhere → tools 7–14× pricier per pass on solve/validate). For the weaker Haiku the tools win is broader.
- **DECISION (Omer 2026-06-19):** run **Haiku-WT on the 4,560 plain-only (v11–13) sweep5v2** corpus. **BUT the ~$146 list cost is REJECTED — must find a cheaper solution first** (open blocker). Lead candidate = prompt caching of the stable system+tool-schema prefix (methodologically free); fallbacks = simulate trajectory compaction, lower turn cap, validate_plan subsample (last one breaks N-matching).
- **Paper scope:** with-tools / Haiku ladder stays **Future Work** for this submission ([[project_sonnet_frontier_notools]]); the probe supplies its feasibility + cost evidence. Haiku ≠ the flagship the "frontier models don't need tools" objection targets, and with-tools is the non-batchable integration-heavier path.
- Caveat: validate_plan n=49 (solid); other cells n=6–8 (directional, wide CIs).

## 2026-06-19 — Sonnet-4.6 frontier no-tools experiment: COMPLETE (both corpora, full N)

- **DONE.** Both batches ran at full N (4,560 trials/corpus, 9,120 total), all succeeded, ~2% truncation. Cost $39.13 (canonical) + $42.38 (anon) = **$81.51**. Output → `results/sonnet-frontier/{sweep5v2,sweep6}/` (committed, force-added past the `results/` gitignore). Resolves the open §7 "one-frontier-model run" item.
- **Result (success [95% Wilson CI]):** simulate **0.0%** [0.0,1.3] · solve **28.7%** [23.8,34.0] · validate_plan **97.3%** [96.6,97.8] · validate_problem **89.7%** [87.0,91.9] · validate_domain **93.6%** [90.6,95.7] (canonical). Anon nearly identical.
- **Finding 1 — volatility, frontier-anchored.** Same model, same config, **0%→97%** across tasks. Bimodal: floored on generative/state-tracking (simulate, solve), near-ceiling on judgment validation (validate_*). The §7A "no-tools is volatile" claim now has a frontier data point, so it can't be dismissed as a small-model capability artifact. simulate 0% is *genuine* (149/300 produced a complete-but-wrong trajectory, not just parse/trunc failures).
- **Finding 2 — contamination probe NULL.** canonical−anon Δ ≤1.9pts on every task, all CIs overlap, including where there's headroom (solve Δ=+0.3). Anonymization moves nothing → validate_* highs are real capability (not memorization); solve/simulate floors are real incapability (not anon breaking recall). Consistent with the open-model sweep6 no-tools null ([[project_sweep6_design]]).
- **Caveat for the write-up.** validate_* near-ceiling on both corpora → low headroom there, so the *contamination* test is only meaningfully powered on solve/simulate; both are null. Don't over-read the +1.9 validate_domain Δ (n=360, CI [88.3,94.1] vs [90.6,95.7] — noise).
- **Paper prose deferred** per user — paper/main.tex untouched; the paper will fold these in next.

- **DONE (code + pilots; full run pending credit):** offline pipeline for the §7A frontier experiment — Sonnet 4.6, no-tools, think=off, full N, canonical (sweep5v2) + anonymized (sweep6), via the Anthropic **Message Batches API** (−50%). Tool: `tools/sonnet_batch.py` (`build`/`submit`/`poll`/`grade`). Corpus identity preserved by reusing the harness's own enumerator/prompt-builder/grader (extracted `build_jobs` + `build_messages` from `runner.py`; grading via `check_success`; output via `save_results`). Anon corpus = committed `domains-anon/`; no re-anonymization.
- **Scope DECIDED → 5 tasks.** §7A's 4 (`simulate` + `validate_plan` + `validate_problem` + `validate_domain`) **plus `solve`, added on user request** (2026-06-18) as a second sole-source point (the canonical planning task). Per-corpus N = open-model `*_off_no-tools` cell exactly: solve 300 / validate_domain 360 / validate_problem 600 / validate_plan 3,000 / simulate 300 = **4,560/corpus, 9,120 total**. validate_domain is 5:1 imbalanced (ISS-020) → **report balanced accuracy**.
- **`solve` rationale + caveat.** §7A had skipped solve (floored for the open roster → no contamination signal). But the probe shows Sonnet is **low-but-NOT-floored** on solve (passes trivial p01s, genuine `plan_invalid` on hard p05s) → at the frontier solve may be a *weak contamination probe* too, not only sole-source. Full N decides. solve no-tools grading validates the model's plan via MCP (so `grade` needs `--marketplace-path` when solve is present).
- **Deviation from §7A's "thin base_url shim" hint:** the Batch API (what makes it fit budget) is NOT on the OpenAI-compatible endpoint → native `anthropic` SDK batches, not a VLLMClient base_url swap. Correct call; the hint predates the batch-discount requirement.
- **Backend adaptations (don't affect within-Sonnet canonical−anon Δ):** faithful `guided_json` analog chosen per task by schema-compatibility — `solve` → `output_config.format` (flat `{plan:[str]}`; without it a strong model reasons in prose → `format_parse_fail` not graded on the plan); `validate_*` → existing `VERDICT:` footer + free-text fallback (no structured-output); `simulate` → `SimulateResponse`'s free-form numeric dict is incompatible with structured outputs, so a JSON-only directive is appended (floored-task fallback grader handles it). think=off = omit `thinking`; temp 0.
- **Pilot/probe findings (canonical, tiny N — NOT corpus numbers):** simulate **0%** unaided (sole-source at the frontier holds; failures = 3 result_mismatch + 5 cap-truncated at 6144, same cap the open models faced — conservative, not a format artifact); canonical `validate_*` near-ceiling (high contamination headroom, the point of those probes); solve ~50% on a trivial-heavy sample (passes trivial, fails hard). All parsed cleanly; grading discriminates (real mismatches, not artifacts).
- **Measured cost (batch −50%): ≈ $40/corpus, ~$80 both corpora** (validate_plan $26.2 / simulate $10.0 / validate_problem $1.7 / validate_domain $1.4 / solve $1.0 per corpus) — well under §7A's ~$146 all-5 ceiling. Slightly conservative (validate_plan/simulate probe samples skewed mid/large). Probes spent ~$0.9.
- **What it buys:** (1) sole-source at the frontier (simulate 0%, + solve mostly-failing on hard); (2) contamination control extended to a strong proprietary model — near-null canonical−anon Δ on the high-headroom validate_* (and possibly solve) jumps "no memorization" from weak models to the frontier; a non-null Δ is itself an honest finding the anon corpus controls.
- **TO RUN at full N:** needs ~$80–100 Console API credit (have $24 → pilots only). Then build/submit/poll/grade both corpora → `results/sonnet-frontier/{sweep5v2,sweep6}/`. NB: prompt caching does NOT help in batch (parallel requests can't read each other's in-flight cache writes; output dominates cost anyway) — the −50% batch discount is the only saving and is already in these numbers.

## 2026-06-14 — PlanBench scoring denominator: correct / TOTAL N (empty = incorrect), to match the literature

- **DECISION (must be stated explicitly in the paper's PlanBench methods):** PlanBench accuracy = **correct / TOTAL attempted instances**, with an empty / loop-exhausted response (no gradeable answer) scored **INCORRECT**, never dropped. This is PlanBench's own published convention (correct over the full instance set), and it is the denominator on which the in-table baselines `gpt-4_chat` / `text-davinci-002` were scored — so our rows must use it to be on the SAME yardstick as the literature numbers we cite beside them.
- **Why it was load-bearing.** `build_table.py` previously divided by *graded* instances (`llm_correct is not None`), silently excluding empties from the denominator. That put our rows on a **more lenient denominator than the PlanBench baselines printed in the same table**, and overstated the tools arm *exactly* where it fails — the tools loop manufactures empties (NL→PDDL formalization wall → retry → truncate to empty) far more than the no-tools arm, so drop-empties discards the failures the tools condition causes. For v1 no-tools vanilla every instance is graded, so the v1 table is **unchanged** by the fix; the divergence is a tools-arm phenomenon only.
- **Fix shipped (`planbench/build_table.py`).** Now emits TWO numbers per cell: (1) **headline** = correct/total (PlanBench-comparable, cite beside the literature); (2) **success-given-completion** = correct/completed — a DIAGNOSTIC that isolates the formalization wall (low headline + high success-given-completion = model fails by not answering, not by being wrong). The OLD number is exactly the new success-given-completion. A per-engine **completion-rate** footnote (answered/attempted) quantifies the wall = the gap between the two tables. Precedent for the two-number split: the sweep-6 contamination probe's success-given-completion read.
- **Paper directive:** report the headline beside the published PlanBench numbers; present success-given-completion ONLY as a mechanism diagnostic, never as a literature-comparable figure. Carry two parity caveats when anchoring to the literature: the published numbers are **single-shot** vs our **multi-turn tool loop** (the literature column is an external anchor; the controlled comparison is our own no-tools arm at the same denominator + Wilson CIs), plus the forcing-prompt parity caveat (vllm-base→vllm-tools also swaps in `WITH_TOOLS_SYSTEM`).
## 2026-06-14 — Methodology section drafted (AAAI-27) + three source corrections

`\section{Methodology}` written in `paper/main.tex` (branch `paper/aaai27-single-tool-draft`), 6 subsections from `EXPERIMENTS_FLOW.md` + the unified deck (s4–6, 36–42): tasks/oracle/fixtures (+ strict-grading Table 1), models+serving, three-arm design (no-tools / +tool plain / +tool steered, BFCL relevance-vs-selection mapping, no-tools-steered control), metrics+Wilson CIs+arms-never-pooled+signed-significance, cross-mode (realizable benefit = steered−no-tools, MOVER/MOVER-D, robust floor = min over modes, +30pp class threshold), contamination null. Double-blind clean (Benyamin et al. cited third-person only; no de-anon tokens). Builds to 4pp (Background+Methodology), well within the 7-page budget.

- **A 3-lens adversarial verify workflow (fact-fidelity / double-blind+format / stats-consistency) confirmed the section accurate, and caught three real errors — all fixed in `main.tex`, two also fixed at the source:**
  - **Validator misattribution.** The verdict/trajectory oracle is **pddl-pyvalidator (unified-planning-based)**, NOT VAL. Dropped `\citep{howey2004val}` from the Methodology oracle sentence (VAL remains a legitimate Background-only example cite). Carry into Results: never call the harness validator "VAL".
  - **Decode cap was stale.** Non-solve `num_predict` is **6,144**, not 4096 — `runner.py` `DEFAULT_NUM_PREDICT` = {solve 8192, validate_*/simulate 6144}; bumped 4096→6144 on 2026-04-29 (commit `464d0f6`, PR #26), a month before the sweep5v2 corpus (which ran `num_predict=null` → defaults). `EXPERIMENTS_FLOW.md` (lines 221-223, 379) was stale at 4096 → **corrected this session**. The think=on budget-confound prose must quote 8,192 for solve and **6,144** for the validation/simulate tasks.
  - **`validate_domain` is not balanced.** It is **5:1 positive:negative** (300 pos = p01–p05×3×20; 60 neg = domain_neg×3×20), per ISS-020 (neg arm pairs `domain_neg` with only the first positive). validate_problem (100/100) and validate_plan (500/500) ARE 1:1. Methodology now scopes the "balanced" claim and notes the wider validate_domain negative-arm CI; flag in Limitations too.
- **Verified-correct (no change needed):** per-cell N = **4,560** (solve 300 / validate_domain 360 / validate_problem 600 / validate_plan 3,000 / simulate 300); model roster + ≥9B headline; serving knobs (temp 0, ctx 16384, 10 tool loops, guided_json, MCP verbose pinned False); the −67pp Gemma-MoE-26B validate_plan signed-significance example; MOVER/MOVER-D + robust-floor as implemented in `rq_deck.py`; contamination figures (≤1.3pp think=off, zero CI-disjoint cells, the validate_plan×think=on ~5% tokenisation artifact).
- **Local-build env (for next session):** missing fonts installed into the user TeX tree (no sudo) via `tlmgr --usermode install tex-gyre newtx courier psnfss` — `ts1-qtmr` (newtx TS1; first `itemize` bullet) + `pcrr8t` (Courier T1; `\texttt`). The AAAI kit does NOT load `amsmath` → use `\mathrm{}`, not `\text{}`.

---

## 2026-06-14 — Results section drafted (AAAI-27) + one major overclaim caught & fixed

`\section{Results}` written in `paper/main.tex`, regime-led per `RESULTS_PLAN.md`: lead + scorecard (`table*`, 6 RQs) + 6 subsections (sole-source / headroom / mixed / scaling / cost / robustness) + 3 figures (Fig 1 solve+simulate sole-source; Fig 2 validate_plan mechanism; Fig 3 token quadrant). Robustness (think=on + contamination) folded to text. All numbers are LOCKED deck values (not re-derived). Builds to 7pp (Intro/Limitations/Conclusion still empty).

- **A 3-lens adversarial fact-check (vs deck slides 2–42 + locked notes + `phase2_expected_sweep5v2.json`) found the Results overwhelmingly faithful — and caught ONE major overclaim, now fixed:**
  - **RQ0.5 "solve and simulate show constant ~87–99pp gaps" was WRONG for simulate.** Per the phase-2 JSON: solve IS constant (gaps +87/+87/+89pp, tool arm 99→97→95% near ceiling), but **simulate's gap DECLINES +100→+93→+77pp with plan length (CI-disjoint)** because its *tool arm itself degrades* on long trajectories (99.7→93.2→77.1%) — only the no-tools arm is floored, not the tool arm. The deck's slide-29 "~87–99pp" shorthand lumped the two tasks; the paper now reports simulate's declining gap as a genuine opposite-signed difficulty signal (the one place tool-assisted success erodes with difficulty). **The unified deck should be corrected on this point too** (slides 29–30 prose).
- **Minor fixes applied:** validate_plan middle plan-length bin tool value 99→**98** (so 98−91 reproduces the locked +7pp gap); prefix-cache caveat now notes tool **outputs are uncached** (cache discounts only re-fed schemas); cost ranges **scoped to ≥9B** (≈4–6×/trial, ≈3–5× costlier per success on most validate_* cells) rather than the deck's ≥4B-spanning "4–15× / 3–11×"; simulate truncation cap stated as **6,144** (deck's "8,192" is the known shorthand slip — see Methodology entry above).
- **Verified-correct (no change):** every scorecard verdict/range; solve floored 8–11%→63–99% with +29pp steering on 35B; simulate 0% across all 3,000 trials + 68/29/3 failure decomposition; validate_plan −67pp = silence-not-error (Gemma verdict on 21% of trials @ 99% accuracy), steering repairs +72pp; the 9B>35B "inversion" = tool-call propensity not capability; think=on 55–83% baseline truncation, robust floor solve +46–71 / simulate +83–97; contamination null ≤1.3pp think=off, zero CI-disjoint cells.

---

## 2026-06-14 — Full body drafted; page budget resolved (no trim needed)

Drafted the remaining sections in `paper/main.tex`: **Introduction** (motivation / 3 prior-work lines / design-in-brief / regime-dependent findings preview / 4-item contributions), **Limitations**, **Future Work** (one out-of-scope paragraph: PlanBench + Huang \& Zhang formalizer baselines + multi-tool orchestration + cap-raised rerun), **Conclusion**, and the **Abstract** (164 words, no citations). Methodology + Results were committed & pushed earlier (`0a31a3d`); these new sections are uncommitted as of this entry.

- **Each new section adversarially verified** (double-blind / claims-match-body / no-overclaim / citation-correctness) — all clean. Two small fixes applied: Intro's "advantage grows with plan length" scoped to "where the baseline has headroom" (consistent with the simulate-declines correction); Conclusion's "occasionally harmful" → "on one task … can even be harmful" (the validate_plan harm is 2/3 ≥9B models, not rare).
- **Page-budget decision (user, 2026-06-14): finish all sections, then trim once; tighten prose, keep all figures.** Outcome: **no trim needed.** The full body builds to **8 pages total but technical content ends on page 7** (Conclusion in p7 left column; references fill p7 right + p8, and refs don't count toward AAAI's 7) → within the 7-page content limit **with all 3 figures kept double-column**. The added sections filled existing float whitespace rather than adding pages.
- **Remaining before submission:** reproducibility checklist (inline, single-.tex), camera-ready vector PDF figures, anonymization/metadata pass, and reconciling the non-canonical model labels (Qwen3.5/3.6, Gemma-MoE-26B) with exact HF ids. Re-verify the exact 7-page rule against the AAAI-27 CFP.

---

## 2026-06-08 — Per-token "tool intelligence" efficiency lens (descriptive)

- **Added a descriptive per-token efficiency view to the RQ deck** (`rq_deck.py`, `_add_efficiency_section`): success rate ÷ action tokens, reported as **successes per 1,000 action tokens**. Action tokens = output (completion) tokens summed across the model's turns. Each +tool arm also shows **`×vs no-tools`** (green ↑ raised / red ↓ lowered / ≈ no change) so the increase/decrease in per-token intelligence is an at-a-glance read — e.g. solve 14–17×↑, but Gemma validate_plan plain 0.2×↓ recovering only to 0.8×↓ steered (still below its strong, cheap no-tools baseline).
- **think=off only, by construction.** Under think=off output = action (no separate reasoning trace); under think=on `completion` = thinking + action, so it is NOT pure action tokens. A think=on efficiency read needs a thinking/action token split — currently unavailable (the `tokens` dict has no thinking count, and `result.thinking` is empty for sweep5, see 2026-05-24 entry; would need a working reasoning-parser or to keep `<think>` in content). Flagged on-slide for the planned think=on follow-up.
- **Descriptive, not a CI-backed claim.** A bare ratio has no honest Wilson interval, so it carries no CI/verdict; the success% component (with CI) carries the inferential weight and is shown beside the ratio. The index is non-monotonic in "goodness": degenerate where no-tools success ≈ 0 (simulate, marked †; solve near-floored ~8–11%), rewards failing cheaply, and its denominator is inflated by truncation (rate varies by arm) and by the tools-arm multi-turn token sum. Read the headroom tasks (validate_*) for a like-for-like comparison.
- **H3-adjacent, NOT H3.** Documented H3 is cost-per-success (tokens among successes ÷ successes); this is the inverse, success-per-cost. Don't conflate in the paper.
- **Bottom-line read (≥9B, think=off):** on `validate_domain` the tool roughly doubles-to-triples per-token intelligence (35B: 0.51 no-tools → 1.33 steered); `validate_plan` reproduces the RQ0.3 MIXED story in efficiency terms (Gemma plain collapses 0.77→0.17, steering recovers to 0.65).
- **Two complementary token-efficiency lenses added alongside (same section):**
  - **Cost per correct answer (= H3 proper):** mean action tokens over SUCCESSFUL trials only, bootstrap 95% CI, LOWER better. Genuinely new vs the index (not its reciprocal — excludes failed-attempt tokens). **Key finding it surfaces:** a correct `solve` costs *more* tokens with tools (35B 2237 no-tools → 2931 steered) — the tool buys **correctness, not brevity**; the per-token "win" on solve comes from far more answers being right, not from cheaper answers. Caveat: ~30–70% of the tool-arm solve/simulate/validate_plan successes still hit the output cap (8.75% truncated among all ≥9B successes), so those cost-per-success means are budget-pinned — don't over-read the absolute. Reconciliation with the decomposition's "fewer tokens ↑" on solve: that factor is over ALL trials (no-tools is charged for tokens burned on its ~90% failed solves); cost-per-success counts successes only — the two legitimately point opposite ways.
  - **Per-token gain decomposed:** steered `×vs-no-tools = (success-rate ratio) × (token-savings ratio)`, exact factorisation. **Mechanism read:** "more often right" is favourable on *every* ≥9B cell (the tool always improves correctness), but "fewer tokens" flips unfavourable on `validate_problem`/`validate_plan` (models already cheap there), so the net per-token result is a wash/loss on those tasks. The single index hid this; the decomposition makes it the headline.
- **(2026-06-09) Extended the three efficiency tables to ≥4B (added Qwen3.5-4B).** Headline finding: the tool's per-token value **inverts for the small model** on validation. Qwen3.5-4B answers `validate_problem` correctly in ~108 tokens unaided (index 4.96, 56% correct) but the tool drags that to ~2700 tokens (index 0.25, 0.2×↓); `validate_domain` 1.50→1.07 (0.7×↓). Decomposition: 4B is *more often right* with the tool but the token cost explodes — so per-token "tool intelligence" is strongly size-dependent and can go net-negative below 9B on cheap-baseline tasks. Implication for the paper: the "tool helps" story is a ≥9B story on a per-token budget; for small models the tool buys accuracy at a steep token premium. (Kept `MODELS_9B` untouched so RQ verdicts / phase-2 unaffected; efficiency tables relabelled ≥4B.)
- **Why these three (index + cost-per-success + decomposition) and not more:** total-tokens-per-success is the exact reciprocal of the index (redundant); a Pareto tokens-vs-success scatter and incremental ΔSucc/ΔTok remain available if a reviewer wants the CI-preserving 2-D view or the investment framing. `duration_s` (success-per-second) is an orthogonal cost — token-efficiency ≠ time-efficiency since tools add MCP latency — deferred.

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

## 2026-06-01 — Contamination probe verdict on complete corpora (supersedes the preliminary deck)

Deck: `checkpoints/contamination-live/` (rebuilt via `build_compare_deck.py`, canon `sweep5v2-live` vs anon `sweep6-live`, all 30 cells matched; clean no-tools probe complete 4560/side both corpora). Δ = canonical − anon success (pp).

- **Headline: the clean no-tools neutral probe is near-null.** ST-mean |Δ| ≤ 1.3pp (think=off) / ≤ 2.6pp (on) across all 5 models; think=off has **zero** CI-disjoint task cells. No broad train-set contamination on pure model knowledge. The null is informative where not floored (Gemma4-off ~50%, Q3.6-off ~49% — headroom, no gap).
- **The only CI-disjoint clean-probe cells are a TOKENISATION artifact, NOT memorisation** (advisor-caught confound; I first mislabelled this a memorisation signal — do not repeat). Sole CI-disjoint nt-neut cells = `validate_plan` × think=on: Qwen3.5-4B +6.3 (25.0 vs 18.7), 9B +4.0 (21.4 vs 17.4), Q3.6-35B +4.3 (84.8 vs 80.5). But anon names **tokenise ~5% longer** (input-token median 1309 vs 1249, identical across models = systematic rename offset) → anon hits the think=on decode cliff harder. Evidence it's budget, not knowledge:
  - **Truncation Δ tracks success Δ ~1:1.** trunc% canon→anon: 4B 74.2→80.4 (+6.2 ≈ succ +6.3), 9B 78.3→82.1 (+3.8 ≈ +4.0), Q3.6 10.9→15.2 (+4.3 = +4.3).
  - **Success GIVEN completion is ~equal:** Q3.6 95.2% vs 94.9%, 4B 96.9% vs 95.4%, 9B 98.6% vs 97.2%. Condition out truncation and the edge vanishes. Q3.6 (85%, 11-15% trunc) is **confounded too** — NOT the clean high-headroom carrier first assumed.
  - **Not the FastMCP bug either:** no-tools arm (no tool calls), independent of `project_validate_plan_fp_scoring_bug`.
  - **General caveat:** any canon-vs-anon comparison in a truncation-bound regime (think=on, small models) is confounded by the +60-token anon prompt-length offset. Clean reads = think=off (truncation-light) and success-given-completion.
- **With-tools (tl-neut/tl-ster): small canonical-leaning edge, but NOT YET STABLE — do not pin a number or mechanism** (this is the 3rd time a with-tools conclusion drawn from incomplete data got overturned this session; advisor said stop). The edge concentrates in simulate + validate_plan, but: (a) 2 cells are still in flight — Qwen3.5-9B think-on anon (~7.2k/9.1k) and Qwen3.5-0.8B think-off canonical (mid-rerun on the cluster; the 06-01 `rsync --update` pulled partial-over-complete for it, two `.v0220-bak` backups exist at 9120); (b) the validate_plan component overlaps the known FastMCP arg-error binning artifact (`project_validate_plan_fp_scoring_bug`); (c) per-cell values shifted across the 05-29 / 05-31 / 06-01 syncs. With tools the planner/validator solves regardless of names → any edge is tool-interaction, not recall. Revisit when the 2 cells finish.
- **Retraction (stands):** the preliminary deck's verdict_mismatch (+1.7pp) "reasoning-degradation mechanism" was an artifact of only Gemma4+Q3.6 being complete; the with-tools deficit is NOT in verdict_mismatch. The exact with-tools magnitude/mechanism is deferred — earlier pinned figures (+1.1pp, −19pp simulate, "sign-inconsistent") were all from incomplete data; do not cite.
- **For the paper:** the contamination control is a clean NULL — no genuine canon-vs-anon success gap once the tokenisation/truncation confound is removed (think=off null everywhere; the only think=on CI-disjoint cells are the artifact above). State the +60-token anon prompt-length offset explicitly as a methods caveat, and report think=off and/or success-given-completion as the confound-free comparison. With-tools rows are provisional (2 cells in flight). Next step for a sharper view: per-domain Δ (needs the anon↔canonical name map).

## 2026-06-06 — PlanBench v1 corpus scope: benchmark-shipped domains only; blocksworld is the comparison anchor

PlanBench arm v1 (no-tools vanilla leaderboard) sweep launched 2026-06-02 (qwen subset: 0.8B/4B/9B/3.6:35b × 10 tasks, sharded per (model,task), rtx_6000). Post-launch reconciliation against the upstream `karthikv792/LLMs-Planning` checkout corrected an earlier framing error (the user caught it: "how does it pass for the published benchmark?").

- **PlanBench's published baselines are blocksworld-only** (+ `blocksworld_3` obfuscated + `mystery_blocksworld`). Committed `results/` contains gpt-4_chat / text-davinci-002 etc. for blocksworld + blocksworld_3 + mystery only. **logistics and depots have NO published baseline.** So **blocksworld is the only head-to-head comparison anchor**; logistics is our own extra corpus; depots likewise.
- **Pre-shipped prompts:** blocksworld (all 10 tasks), logistics (all 10), **depots (t1 only).** depots t2–t8 prompts were never created upstream (PlanBench never ran depots past t1), so they fail at `response_generation.py:62` `assert os.path.exists(prompt_dir+task.json)`. The assert fires *before* generation → ~0 GPU wasted, but marks the job FAILED.
- **DECISION (user, 2026-06-06): use only the domains the benchmark lists, no self-generated prompts, run it as-is.** → corpus = blocksworld (10 tasks) + logistics (10) + depots (t1 only). We do **not** generate depots t2–t8 (would be net-new data with no published anchor + a 500-instance FD solve per task). depots t2–t8 cells will show FAILED; that is PlanBench-as-shipped, not a harness bug.
- **t3 (plan verification) grader is the one real fix needed.** `evaluate_verification`'s `parse_output` only sets `output_dict['valid']` if the response literally contains `"plan is valid"` / `"plan is invalid"`; otherwise line 261 `KeyError: 'valid'` crashes the *entire* t3/config evaluation (zero t3 numbers even for adherent instances). Our qwen3.5:0.8B emits free-form prose without the verdict phrase → crash. PlanBench's published gpt-4 followed the template → parsed → graded. **This is genuine model non-adherence (the t1-style format-adherence signal), not a parser bug** — consistent with our "tool-adherence = data" stance. Fix = an **offline, uniform re-grade** from saved responses (t3 generation succeeded), scoring "no verdict produced → incorrect", which is **comparability-preserving** (gpt-4's adherent responses unaffected; only non-adherent ones — which gpt-4 didn't produce — score wrong). Report the t3 verdict-emission rate as a finding. NOT a mid-sweep grader patch (would split corpus identity). Open question: whether 4B/9B/35B adhere better than 0.8B (→ real t3 signal for bigger models) — check by content as cells land.
- **Monitoring caveat:** because every (model,task) job includes the depots config, **every t2–t8 job exits rc=1** from the depots assert → `sacct`/squeue State is useless as a health signal. Monitor by **content** (non-empty graded files per model/config/task), so a real failure (e.g. the cold-start vLLM `determine_available_memory` OOM that hit job 18003835) isn't masked.

## 2026-06-06 — PlanBench v1 (no-tools) first numbers: 35B competes with GPT-4 on Blocksworld; exact-match grading understates reasoning models

Full table + reproducer: `development/planbench_v1_results.md` (`python3 planbench/build_table.py results/planbench/canonical`). Qwen subset (0.8B/4B/9B/3.6:35b), no-tools vanilla leaderboard, graded by PlanBench's own VAL/PR2. gpt-4_chat/davinci columns = PlanBench's committed per-instance gradings averaged (their published baseline by construction).

- **Headline: Qwen3.6-35B (open, ~3B-active MoE, no tools) matches or beats GPT-4 on 6 of 9 Blocksworld tasks** — wins t1 (36/31), t2 (38/28), t5 (57/28), t8_1 (93/77), t8_2 (93/86), t8_3 (87/58); trails t3 (88/95), t4 (52/61), t6 (42/47). All 6 wins on cells where the parser works (non-zero both engines) → robust to the grading confound below. This is the Paper-1 "small open models compete" evidence ([[project_paper_strategy]]).
- **Clean capability ladder** 0.8B→4B→9B→35B monotone on ~every task, both configs.
- **First-class finding — PlanBench's exact-match grading (`text_to_plan`/`text_to_state`) systematically understates reasoning/markdown models** (penalises CoT-wrapped answers even when content is correct). This is the cleanest motivation for the v2 tools arm (tools consume structured output → bypass the regex-format penalty). Severity-ordered:
  1. **t7 (plan_execution) EXCLUDED for ALL engines** — uniform 0.0 for ours; verified artifact (35B's extracted state == ground truth + one stray bare `clear` scraped from markdown). Same parser graded gpt-4 (28.4), so no engine has a fair t7 here. Do NOT report t7=0 as a capability gap; do NOT put it in any aggregate.
  2. **t3 verdict-emission rate IS the format-adherence signal** — 0.8B 53% → 4B 99% → 9B/35B 100% (bw). 0.8B t3 ~26% ≈ chance.
  3. t1/t8 small-model prose (0.8B/4B emit prose not `[PLAN]`) — genuine non-adherence (9B/35B parse fine → extractor works, lows are real).
- **Do NOT report a macro-mean/aggregate** — non-standard for PlanBench AND contaminated by t7. Per-task only. (Killed an earlier "58.6 agg beats gpt-4's 54.0" framing — advisor-caught, it included t7 + isn't a metric PlanBench reports.)
- **Methodology hygiene applied** (all in `planbench/apply_patches.py`, comparability-preserving — non-adherent scores incorrect exactly as gpt-4 would): t3 KeyError (missing verdict) + IndexError (malformed logistics action line) fixed; 2 smoke-contaminated cells (0.8B/4B t1/bw — stale 3-instance eval file over full 500 responses) re-graded. logistics t5 n=12 (PlanBench ships only 12) — noisy. logistics has no published baseline (bw-only upstream) = our extra corpus.

### 2026-06-06 addendum — PlanBench v1 prompt-parity + bw-t5 verification
- **Prompt parity checked (advisor-prompted): near-identical, not byte-identical.** Our blocksworld prompts vs PlanBench's committed gpt-4 prompts share the same task (init conditions, goal, `[PLAN]` markers) and same one-shot count; they differ by ONE extra domain-rule sentence in ours ("Once you stack a block on top of a second block, the second block is no longer clear") = PlanBench prompt-version drift. Large wins (t5/t8_3 +29, t2 +9) survive it; the **closest win t1 (+5) is the most exposed → call t1 "near-parity," not a clean win.** Also a VAL-version caveat (our cells graded 2026/patched, gpt-4's at publish time).
- **bw-t5 headline win verified real** (not a t7-style artifact): 35B 286/500 correct, a correct instance's extracted plan matches GT structure (VAL validates semantically; letters-vs-colors is just grounding).
- Gates the *relative* "beats GPT-4" claim; the table generator / t3 recovery / t7 exclusion / contamination fix stand regardless.

### 2026-06-06 close — PlanBench scope: Qwen-only (gemma discarded); prompts are completion-style
- **DECISION: PlanBench roster = Qwen models ONLY (0.8B/4B/9B/3.6:35b). gemma4:26b-a4b DISCARDED for PlanBench** (still used in the 5-task `run_experiment.py` arm — decision scoped to PlanBench).
- **PlanBench prompts specify output format ONLY by one in-context example (completion-style, GPT-3-era), no explicit "respond only with…" instruction** (verified on the t7 prompt). So the low vanilla scores for our chat/reasoning Qwens = completion-prompt-vs-chat-model mismatch (they elaborate where davinci/gpt-4 complete tersely), not stated-format disobedience. Benchmark-staleness effect; reinforces v2 (structured tool output) as the principled comparison.
- **Next: v2 MCP tools-on arm (ISS-022)** picked up by another agent — full build handoff = `development/PLANBENCH_HANDOFF_v2.md`.

### 2026-06-06 — PlanBench v2 (MCP tools-on, ISS-022) engine built + t1 smoke VALIDATED (plumbing); 2 full-run blockers recorded
- **Build:** added a `vllm-tools` BACKEND token (engine `pddl_copilot__vllm-tools__<tag>`), NOT the handoff's literal `pddl_copilot_tools__` prefix — the latter doesn't start with `pddl_copilot__`, so PlanBench's already-patched (idempotent) dispatch branch would miss it and force an `rm -rf` + VAL/PR2/FD rebuild. The backend token keeps the prefix → only `planbench/engine.py` changes, no re-clone/re-patch. (commits 6ec3171, fea64ee on `planbench-integration`.)
- **Engine:** persistent module-level event loop + lazily-connected `MCPPlanner` (connect ONCE, run each instance via `run_until_complete` — the handoff's flagged sync/async "main gotcha"), reuses `pddl_eval.chat.chat_with_tools` + `VLLMClient`. All v2 deps lazy-imported inside the tools branch so v1's slim venv keeps importing `planbench.engine`. Minimal tool-use system nudge; **NO PDDL injection** (LLM-as-formalizer, so tools-vs-no-tools isn't confounded).
- **Cluster env:** the cluster has no system python≥3.10 (`/usr/bin/python3` is 3.9, no uv); `mcp` needs ≥3.10. The python≥3.10 source is the 5-task arm's conda env `pddl_copilot` (3.12, openjdk=17). v2 sbatch activates it (mirrors `run_condition_vllm_rtx.sbatch`) then builds a SEPARATE `.venv-tools` (openai≥1.0 + mcp); v1 `.venv` (openai<1.0) left frozen.
- **Smoke (job 18019718, Qwen3.5:4B, t1/blocksworld, instances 2/3/4, rtx_3090, COMPLETED):** plumbing CONCLUSIVELY validated by content. MCP connected ONCE; tools fired (`classic_planner`, `validate_domain`, `validate_problem`); the model's multi-line PDDL reached the tools VERBATIM (args not mangled); multi-turn replay with synthetic tool_call_ids held up; full LLM-as-formalizer loop observed (inst 4: malformed PDDL → planner parse-error → model REVISED → planner ran → validators VALID). Grading produced per-instance `llm_correct`. Plumbing pass — NOT a capability claim (0/3 correct, all weak-model failures).
- **FULL-RUN BLOCKER #1 — answer truncation.** BOTH answered instances ended `done_reason='length'`: the final answer hits `num_predict=4096` (`_DEFAULT_NUM_PREDICT`) mid-text. A full sweep would score the tools arm ~0 for truncation, unrelated to tools (the v1 completion-prompt prose-runaway, now inside the tool loop). Decide before the sweep: raise the cap (may just delay) / add a stop / tighten the final-answer prompt.
- **FULL-RUN BLOCKER #2 — denominator honesty.** Loop-exhausted/empty instances (e.g. inst 2: 10× `classic_planner` all parse-erroring → empty answer) have **no `llm_correct` field** in the results JSON. `planbench/build_table.py:67` filters to `llm_correct is not None` then divides by that count → silently DROPS these → overstates tools-arm accuracy exactly where the model fails hardest. (v1 was safe: no-tools never loop-exhausts, so "every generated instance is graded" held.) The full v2 table needs a tools-aware denominator (attempted-but-empty = incorrect). **Do NOT launch the v2 sweep before fixing both.**
- **Next-direction question (open, user's call):** the FULL 10-task v2 needs the sibling-repo MCP extensions `validate_plan_structured` (t3) + `optimal_plan` (t2) per `../pddl-copilot/specs-for-plan-bench.md` (branch `planbench-integration`); t1 needed neither. Sibling repo currently on `main`.

### 2026-06-06 — PlanBench v2 num_predict probe: no-tools CLEAN at 8192; tools-arm truncation is a multi-turn prose SPIRAL (budget-independent)
Set up separate v2 namespaces — `vllm-base` (no-tools) vs `vllm-tools` (tools) — so the higher-num_predict comparison never touches v1's frozen `vllm__` 4096 leaderboard corpus, and forced fresh regen (PlanBench caches by engine name: response_generation.py:70 skips instances with an existing non-empty llm_raw_response). Ran both arms at num_predict=8192 (= the single-task sweeps' `solve` cap; num_ctx=16384 = same context as the single-task arm — note num_predict is the OUTPUT cap, num_ctx the window; output can't be 16K since the prompt shares the window, and 32K ctx regressed parsing per [[project_ctx_bump_32k_smoke_failed]]). Qwen3.5:4B, t1/blocksworld, instances 2/3/4, THINK=off, rtx_3090, SERIAL (concurrent jobs race on the shared-tree rsync → benign exit 23; serial = clean exit 0).
- **No-tools (vllm-base) @ 8192: CLEAN.** All 3 reach [PLAN END]; no truncation, no repetition (max line-repeat ≤2); resp_len 5470/12555/8712. All llm_correct=False (the 4B's plans are wrong, but FORMAT is complete — capability, not artifact). → Raising 4096→8192 fixes the no-tools truncation that hit v1's longer instances; 8192 is a valid clean no-tools baseline.
- **Tools (vllm-tools) @ 8192: STILL truncates — a SPIRAL, not a budget shortfall.** 4096→8192 merely doubled output (15K→30K chars) with the SAME done_reason=length on all 3. Content = degenerate prose re-simulation of the blocksworld state (one line ×24; "the planner says unsolvable, let me think more carefully…" loops). The 4B fills any budget → 16K wouldn't help. The spiral is MULTI-TURN-INDUCED: tool results (parse errors / "unsolvable") feed back and trigger re-analysis prose loops; the single-turn no-tools arm does NOT spiral.
- **Implication: the tools-arm fix is prompt/stop/model, NOT tokens.** Candidates (OPEN decision): (a) firmer anti-narration system prompt + a `[PLAN END]` stop (safe under THINK=off; the engine's no-stop rule was for thinking models echoing the marker mid-trace); (b) run the comparison on 9B/35B (v1 showed 9B/35B follow the format; the spiral is a small-model behavior — [[planbench_v1_results]]); (c) abort non-converging tool loops earlier. Both arms 0/3 correct on the 4B (weakest model; plumbing/truncation was the smoke's purpose, not accuracy).
- Infra all clean: SERIAL avoids the rsync race; vllm-base keeps v1's 4096 corpus untouched; both COMPLETED exit 0. Caching means a num_predict change needs forced regen (clear the engine's task file or use a fresh engine name).

### 2026-06-06 — PlanBench v2 tools arm across model sizes: capable models IGNORE the offered tools (the "may use" nudge is too soft)
Tools smoke (vllm-tools, t1/blocksworld, instances 2/3/4, num_predict=8192, THINK=off) across the Qwen ladder, to test whether the 4B's prose-spiral is a small-model artifact:
- **4B:** tries tools (9× classic_planner on malformed PDDL), then prose-SPIRALS to length-truncation. 0/3.
- **9B:** does NOT spiral (all done_reason=stop, [PLAN END] reached) — BUT calls ZERO tools on all 3; answers directly. 0/3 (clean format, wrong plans).
- **35B:** mostly 0 tool calls (1 of 3 instances used 3 tools); the 2 direct-answer instances are CORRECT (done_reason=stop, [PLAN END]); the 1 tool-USING instance truncated to empty (done_reason=length, final_text_len=0) → failed. **2/3 correct, all via direct answers with tools unused.**
- **Conclusions:** (1) the prose-spiral is a 4B-specific artifact (9B/35B don't spiral) — confirms the v1 small-vs-large format-adherence split [[planbench_v1_results]]. (2) **The current minimal "you MAY use the PDDL tools" system nudge does NOT induce tool use in capable models** — 9B/35B answer directly and ignore the planner/validator; 35B is correct 2/3 WITHOUT tools. So the tools arm as prompted measures direct answering with tools sitting idle, not tool-assisted planning. (3) When a model DID invoke the tool loop (4B always, 35B once), it tended to truncate/fail — the multi-turn loop currently HURTS more than it helps at these sizes.
- **Implication / OPEN decision:** to make the tools arm a real test of the PDDL-Copilot thesis (LLM-as-formalizer → verified planner), the system prompt must REQUIRE tool use (model MUST translate to PDDL and call classic_planner, not answer from its own reasoning), and the truncation-on-tool-turns issue (35B inst 3, 4B) must be addressed (likely a stop sequence + anti-narration, since num_predict is not the lever). Alternatively, "offered tools are ignored by capable models" is itself a reportable finding. NOT a num_predict problem.

### 2026-06-06 — PlanBench v2 forcing tool prompt on t3/t7: tools arm WORKS on t3 with 35B (2/3 via validate_plan); formalization wall on smaller models
Replaced the soft nudge with the paper's FORCING directive (pddl_eval.prompts.WITH_TOOLS_SYSTEM, byte-identical) + an NL→PDDL formalisation step (PlanBench is NL, unlike the 5-task arm which is handed PDDL) + a task-aware output clause (PDDL_COPILOT_TASK: t3→verdict/validate_plan, t7→state/get_state_transition). Smoke on blocksworld instances 2/3/4, num_predict=8192, rtx_6000.
- **Forcing prompt DOES induce tool use** (vs the soft nudge which 9B/35B ignored): 9B and 35B now call validate_plan (t3) and get_state_transition (t7).
- **35B t3: 2/3 CORRECT** — calls validate_plan (1–3×), emits a clean "The plan is invalid." → graded correct (llm_correct_binary=True). FIRST clean end-to-end demonstration of the PDDL-Copilot tools mechanism on PlanBench. (inst 4 looped 6× across validate_plan/domain/problem then truncated to empty → failed.)
- **35B t7: 0/3** — 2 instances answered DIRECTLY (0 tool calls, done_reason=stop, wrong), 1 used get_state_transition then truncated to empty. t7 stays hard: verbose state output + the known exact-match text_to_state grader [[planbench_v1_results]].
- **9B (forcing): formalization wall.** Uses the right tools (t3: validate_plan ×5–6; t7: validators + get_state_transition) but produces malformed PDDL → tool errors → RETRY LOOP → rambles → truncates to empty (done_reason=length, final_text_len=0) → never emits the verdict. All 3 t3 instances empty → response_generation wrote no file → response_evaluation.load_json AssertionError (os.path.exists on the missing responses file) → rc=1. This is "nothing to grade", an INFRA robustness gap, not a grader-logic bug (distinct from the apply_patches t3 KeyError/IndexError fixes).
- **Core tension (the substantive finding):** the models that NEED tools (small, prose-penalised by exact-match grading) can't reliably formalise NL→PDDL to use them (4B/9B hit the formalisation wall); the model that CAN formalise (35B) mostly already follows the verdict/plan format WITHOUT tools (v1 35B t3 ≈ 88%), so its tools-vs-no-tools delta on t3 is unclear at this N. "Force tools" = "force formalisation," and formalisation is the real bottleneck.
- **Residual issues for a full run:** (a) formalisation-loop truncation-to-empty on a minority of instances (even 35B inst 4 / t7 inst 3); num_predict-independent → needs a stop sequence / lower MAX_TOOL_LOOPS / tighter "call once then answer" prompt; (b) response_evaluation asserts the response file exists → crashes when ALL targeted instances are empty (handle for the tools arm); (c) t7's exact-match grader. ALL results here are N=3 — need real N before any tools-vs-no-tools claim.

### 2026-06-07 — PlanBench v2 close: small-model fix is FORMALIZATION-scaffolding; cost/provider for the Claude alternative; v3 = workflow-framework retry
Session-close analysis + decisions. Full handoff: `development/PLANBENCH_HANDOFF_v3.md`.
- **The small-model wall is fixable because it's a FORMALIZATION failure, not a reasoning failure** — the planner/validator does the reasoning; the model only has to produce valid PDDL and render the tool's answer. Layered fix: (1) inject the fixed domain (model writes only the problem — biggest lever; a labeled "given PDDL" variant, flag it); (2) grammar-constrain the PDDL output (vLLM guided_json — harness already has the plumbing — kills the parse-error→retry→truncate loop); (3) few-shot NL→PDDL example(s); (4) validator-feedback fix-loop + stop sequence + "call once then answer" (curbs the spiral + re-validate churn). Floor: 9B is the promising target, 4B borderline, 0.8B no.
- **DECISION (user, next direction): retry the small open models via a WORKFLOW FRAMEWORK** (CrewAI / LangGraph / AutoGen) that scaffolds the formalize→validate→fix→solve→render loop deterministically, so the model only does narrow sub-tasks. "Native skills like pddl-copilot": these frameworks wire the MCP servers as tools + replicate the pddl-author/pddl-fixing skill text as roles/nodes (the SKILL.md progressive-disclosure concept is Claude-Code/Claude-Agent-SDK-specific; the Claude Agent SDK supports Skills+MCP natively but is Claude-only). Integrate as a new engine backend (e.g. `vllm-crew`) whose send_query drives the workflow per instance.
- **Cost/provider analysis for the Claude alternative (not chosen now, kept for reference):** Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5 per 1M; per-instance (tool-using, cached) ~$0.12–0.30 Sonnet / $0.04–0.10 Haiku; full v2 (~7k instances) ~$850–2,100 Sonnet / $280–700 Haiku; calibrate on ~20 instances first. **First-party Claude API > Bedrock** for batches+caching (Bedrock batch is a separate AWS API; Claude Platform on AWS is the AWS-billing parity option). **Batches (50% off) do NOT fit multi-turn tool-loops** — single-shot only; the tools arm runs live+caching or a turn-staged pipeline. Claude formalizes natively → the real choice is "scaffold open models (cheap, more work)" vs "pay for Claude (no scaffolding)" — comparing both is paper-worthy.
- Carry-forward blockers (unchanged, see v3 handoff): build_table.py denominator drops empty instances (overstates tools arm); response_evaluation asserts the response file exists (crashes on all-empty cells); run jobs SERIALLY (rsync race); PlanBench caches by engine name (need fresh engine name / clear files to regenerate); .venv-tools needs python≥3.10 (conda pddl_copilot); all v2 tools numbers are N=3.

## 2026-06-08 — Single-tool-use RQ deck (RQ0.1–0.6) built + verdicts locked

Deck: `checkpoints/rq-sweep5v2/pddl_copilot_rq_sweep5v2.pptx` (36 slides) regenerated by the tracked `.claude/skills/analyzer/scripts/rq_deck.py`. Headline = think=off, ≥9B (Qwen3.5-9B, Gemma-MoE-26B, Qwen3.6-35B). Three arms, **never pooled**: no-tools / +tool(plain) / +tool(steered); availability gap = plain−no-tools (byte-identical wording), steering gap = steered−plain. Metric = raw `task_success_rate`, Wilson 95% CIs.

- **Phase-1 verdicts (defended by signed CI counts, ≥9B):** RQ0.1 (validate_domain+problem) **YES** ≥4B — 0.8B reverses on validate_problem (−25pp). RQ0.2 (solve) **YES, decisive** — no-tools floored ~8–11%, +tool 63–99%; steering +29pp on Qwen3.6-35B. RQ0.3 (validate_plan) **MIXED** — model alone already 75–90%; availability is significant-**against** for Gemma-MoE (−67pp) and Qwen3.6-35B (−9pp), favorable only for 9B; steering recovers (Gemma 21→93%) but net benefit over a strong baseline is small. RQ0.4 (simulate) **YES, decisive** — 0% without the tool, 65–92% with, steering +18–22pp.
- **The signed CI count is load-bearing.** A sign-blind disjointness test would score RQ0.3 as YES (Gemma's −67pp gap is wildly CI-disjoint). Counting only *favorable* disjoint gaps, and reporting significant-against separately, is what makes RQ0.3 read MIXED. This is now an assert in the deck (computed verdict must equal the locked scorecard or the build fails).
- **RQ0.3 mechanism nailed:** validate_plan +tool(plain)'s low raw success is a TOOL-CALLING artifact, not a verdict collapse. Decided-accuracy when the model DOES answer ≈ 99% (Gemma), 68% (0.8B), fp≈0; the gap is all `no_ans` (model never calls the tool). Steering fixes it by raising tool-calling (Gemma tool_selected 21→94%), and success follows in lockstep (21→93%). Mechanism slide pairs tool_selected vs success per ≥9B model.
- **Relabel finding (extends `project_validate_plan_fp_scoring_bug` / ISS-005):** the FastMCP arg-error read-time relabel is **INERT on sweep5v2-live** — relabel on/off gives identical confusion matrices (verified in the deck's gate). The corpus was generated after the 2026-05-25 runtime `check_success` fix, so there is nothing left to relabel. Earlier note "trust the deck's relabeled val-plan numbers" still holds, but the relabel is now a defensive no-op on this corpus, not a correction. Don't expect it to "move" any sweep5v2 number.
- **RQ0.5 (difficulty × plan length) = advantage GROWS for validate_plan.** Headroom-gated (both arms have room). no-tools degrades 94→91→62% as plan length grows (≤8 / 8–19 / >19), +tool(steered) holds 99→98→89%, so the gap widens **Δ+5 → Δ+7 → Δ+27pp**. solve/simulate are framed as tool-arm robustness (no-tools floored, no headroom to lose). RQ0.6 (difficulty × object count) = **NO clear effect** — validate_problem gap flat ~22pp across arity bins.
- **Reproducibility specifics now pinned:** phase-2 bins on solve/simulate→`ref_len`, validate_plan→`plan_len[plan_label]` (valid plans v1–v5 only — buggy `b*` length isn't a difficulty axis), rq06→`obj_count`; cuts = per-task floored tertiles; nt-neut vs tl-ster, ≥9B. This reproduces the prior scratch `phase2_summary.json` byte-for-byte (7 keys × 3 bins, asserted). The scratch oracle had bound validate_plan to solve's ref_len cut ([8,19]); the principled per-task `plan_len` cut is [8,18] — the deck uses the latter and still matches because it restricts to valid plans. Difficulty oracle `meta.json` relocated to the tracked `.claude/skills/analyzer/data/meta_sweep5v2.json`, regenerable by `gen_meta.py --check`.
- **Caveats disclosed on the deck:** think=on is a decode-budget cliff for small models (solve tool_selected: Gemma 100 off → 23 on/plain → 75 on/steered; truncation 24→70%) — budget, not ability; headline stays think=off. sweep-6 contamination = robustness footnote (clean no-tools null). Phase-3 (PlanBench / SOTA formalizer baselines incl. Huang & Zhang ACL 2025) explicitly out of scope.

## 2026-06-09 — Token-efficiency metric rewritten to total-token cost + cost-of-pass

Decided while answering "how to assess tool efficiency in tokens + time-to-response" (sweep5v2 single-tool). Rewrote the RQ deck's token metric (`rq_deck.py`, see CHANGELOG same date); **supersedes** the per-token "tool intelligence" index from the 2026-06-08 deck entry.

- **The metric choice is load-bearing — it swings the tools verdict ~10× on identical data.** Same Qwen3.5-9B trials, tools÷no-tools: per-trial completion **0.62×**, per-trial total **2.84×**, cost-of-pass completion **0.29×**, cost-of-pass total **1.33×**. The old deck reported only the most tool-flattering corner (per-trial completion). Now report **total tokens/trial (input+output)** as consumption and **cost-of-pass = Σtotal tokens ÷ successes** [bootstrap CI] as quality-adjusted efficiency; completion-only kept as a labelled secondary "generation cost" lens.
- **Tools INVERT the token profile**, so output-only is the wrong denominator: no-tools is output-heavy (~0.3:1 in:out), tools are INPUT-heavy (~5:1) because tool schemas + tool outputs are re-fed across ~2 turns. That re-fed input is the real token cost of tools.
- **Cost-of-pass verdict is task-dependent (the headline efficiency result):** where no-tools is floored (solve, simulate) tools are ~3× CHEAPER per success (cost-of-pass 0.3–0.4×); where no-tools has cheap headroom (validate_problem, validate_plan) tools are 4–11× COSTLIER. Driven by the exact decomposition: cost-of-pass ratio = (token-cost ratio) ÷ (success-rate ratio).
- **Caveats to state in the paper:** prefix cache (~90%) discounts the COMPUTE cost of re-fed input but not raw consumption (tool outputs uncached); output is right-censored at 8,192 with arm-dependent truncation, so completion-token comparisons are budget-bounded. Always split per-attempt vs per-success.
- **Time-to-response is the still-pending half:** `duration_s` is batched-server wall-clock (confounded) and the `tokens.*_duration_ns` fields are synthetic shims. Report latency via the `turns` (round-trip) + output-token proxy; a real TTFT/TPOT number needs a concurrency=1 micro-benchmark. See memory `project_tool_efficiency_metrics`.

## 2026-06-10 — RQ deck restructured for presentation (review verdicts)

Slide-by-slide review of the RQ deck; decisions apply to the talk and to how the paper narrates these results. Deck rebuilt (50→47 slides, ~39 main + 8 backup); verdicts/metrics unchanged.

- **Narrative order locked: lead with simulate (0% → 65–92% → 83–97%), then a 6-RQ scorecard, then evidence.** The capability-that-does-not-exist-without-the-tool is the hook, not the fourth RQ.
- **Signed significance is a first-class methods beat**, not a bullet: one slide showing Gemma's −67pp validate_plan gap counted AGAINST (sign-blind would read RQ0.3 YES; signed reads MIXED).
- **0.8B is excluded from main charts/tables** (≥4B shown; ≥9B headline) and summarised on a single small-model-caveat slide — its availability reversals (validate_problem −25pp*, validate_plan −27pp*) are a finding about minimum scale for tool-driving, not noise to spread across every figure.
- **Token story is figure-led; tables are backup.** (1) Quadrant: tokens/trial (log) vs success with no-tools→steered arrows — consumption is never quoted without what it buys; (2) input/output stacked bars showing the ~0.3:1 → ~5:1 inversion; (3) cost-of-pass dumbbell grouped by baseline regime (the grouping IS the finding: tool 3–11× costlier per success where the baseline is strong, ~3× cheaper or sole producer where floored); (4) one merged decomposition table in words ("4.2× costlier ÷ 9.9× more right = 0.4× cheaper").
- **Censoring + latency proxy now have on-deck evidence:** a per-task×arm table of truncated% (8,192 cap; arm-dependent, e.g. simulate 29% nt vs 73% steered), mean turns, and token means. `turns × output tokens` stated as the only defensible latency read; concurrency=1 TTFT/TPOT still future work.
- **Completion-only lens is backup-only** (labelled tool-flattering); RQ0.6 null result gets exactly one slide; question slides folded into answer slides; mechanism slide dropped for RQ0.1 (tool-use already ~100% in both arms — nothing for steering to repair there).
- **Q&A guardrails:** don't pin with-tools sweep-6 numbers (still provisional), don't present `duration_s`, and the retired per-token index is "superseded by cost-of-pass".

## 2026-06-10 — think=on companion deck built; think=on story characterised

`rq_deck.py --think on` → `checkpoints/rq-sweep5v2-think-on/` (48 slides). Verdicts computed by the same signed-CI rule, NOT locked (only think=off is locked). Bottom lines for the paper:

- **The verdict pattern survives reasoning mode** — YES/YES/MIXED/YES, RQ0.5 YES, RQ0.6 NO — which is itself a finding: the tool's value is not an artifact of direct-answer mode.
- **But every think=on availability gap is budget-confounded.** Reasoning + answer share the 8,192-token decode budget; 55–83% of ≥9B no-tools trials truncate, and the validation baselines collapse (validate_plan 9B 80→21%, Gemma 88→10%; validate_domain Gemma 78→0% off→on). The huge gaps measure baseline drowning, not extra tool skill — framed on-slide as "the baseline reasons itself to death"; think=off remains the clean read.
- **solve is the one task where reasoning helps the unaided model** (9B 11→27%, 35B 9→38%) — thinking pays where derivation is the task, and budget-kills where the answer was already cheap. Under think=on, RQ0.5's headroom case is solve: baseline fades 41→17→9% with plan length, tool holds, gap widens +48→+65pp.
- **Steering is more important under think=on:** solve steering 3/3 favorable-significant (1/3 at off); Gemma validate_plan plain = 0.6% success with tool_selected ≈1% (it reasons instead of calling; 100% accurate on the 1% of trials it answers), steered recovers to 44% — still below its own think=off no-tools 88%.
- **Efficiency flips to per-MODEL regimes:** tools ~2× per trial (vs 4–15× at off — baseline burns ~5–6k tokens reasoning regardless), and cost-of-pass favours the tool almost everywhere (validate_domain 9B 200k→11k tok/success; Gemma ∞→12k); only 35B, whose baseline survives the budget, still pays the off-style validate_* premium (~6k→15k).
- **Methods caveat to state:** under think=on `completion` = reasoning + answer in one number (vLLM strips the trace; no thinking/answer split logged) — output tokens are not answer length; report totals. The sweep-6 think=on tokenisation artifact is cited on the contamination slide as a live demonstration of the budget confound.
- **Open question for a paper claim:** whether think=on with a larger decode budget closes the baseline gap is untested (would need a cap-raised rerun; the 32K ctx-bump smoke failed on format grounds 2026-05-21 — a different axis, but the only related probe).

## 2026-06-10 — Cross-mode (think=off × think=on) aggregation: where the tool's value is mode-invariant vs budget-dependent

`rq_deck.py --think compare` → `checkpoints/rq-sweep5v2-compare/` (12 slides), the standalone third artifact aggregating the locked off deck and the on companion at the per-cell-statistic level only — raw trials never pooled across arms or modes. Spine = REALIZABLE benefit = success(+tool steered) − success(no-tools) per model×task×mode (steered, not plain: under think=on the plain arm reasons instead of calling the tool, so availability conflates baseline collapse with a tool-calling failure). CIs: Newcombe MOVER per gap, MOVER-D on Δ(on−off) (independent corpora). Robust floor = min over modes. Bottom lines for the paper:

- **Mode-INVARIANT.** (1) The verdict pattern — RQ0.1–0.4 YES/YES/MIXED/YES, RQ0.5 YES, RQ0.6 NO — reproduces under think=on by the same signed-CI rule (now asserted at compare build time). (2) The steered tool ARM is mode-stable (mean off-vs-on shift 9pp across ≥9B×5 tasks; Qwen3.6-35B fully invariant on all five) while the no-tools BASELINE swings 28pp — so all cross-mode gap movement is a baseline effect (off-vs-on scatter: orange on the diagonal, grey far off it). (3) solve = robust class: floor +46…+71pp. (4) simulate = sole-source class: baseline 0% in both modes, +83…+97pp — a benefit with no baseline cannot be budget-confounded.
- **What FLIPS or MOVES (findings, not contradictions).** (1) RQ0.5's headroom case: validate_plan (+5→+27pp with plan length) at off → solve (+48→+65pp) at on. (2) Cost-of-pass regime: task-determined at off (validate_* 3.2–4.9× costlier per success on ≥9B; solve/simulate cheaper or only producer) → model-determined at on (where reasoning drowns the baseline the tool is far cheaper — 9B validate_domain 200k→11k tok/success — or the only producer — Gemma; only the budget-robust 35B still pays the validate_* premium, 1.8–3.3×). (3) Steering importance grows at on (plain tool_selected collapses: Gemma solve 100→23%, validate_plan 21→1%; 9B solve 100→59%). (4) Realizable-benefit magnitude: solve shrinks Δ −20…−43pp* (baseline improves: 9B 11→27%, 35B 9→38%); validate_* inflates up to Δ +67pp* (baseline collapses) — Gemma solve baseline is the exception (8→4%, reasoning does NOT help it).
- **think=on numbers that are budget ARTIFACTS.** The large think=on gaps on validate_domain/problem/plan: the 9B/Gemma no-tools baselines truncate 78–100% there (collapse: Gemma validate_domain 78→0%, validate_plan 88→10%; 9B validate_plan 80→21%). The 35B control proves it: its baseline truncates ≤11% on validate_* and its benefit barely moves (validate_problem Δ −2pp n.s., validate_domain Δ −7pp). Honest mode-invariant claim = the robust floor: validate_plan +5…+16pp, validate_problem +20…+25pp, validate_domain +21pp (Gemma) to +74pp (9B, whose off baseline is already weak). "Tool arm is mode-invariant" is mostly-true, not absolute: Gemma's STEERED arm still pays a residual tax (validate_plan 93→44%, solve 99→74%).
- **For the paper:** think=off is the headline; quote the robust floor as the mode-invariant claim; never quote a think=on validate_* gap without the truncation caveat + the 35B control; report the regime flips as findings. Caveats carried on-deck: completion = reasoning+answer (no logged split), latency only via turns × output tokens. Open follow-up unchanged: a cap-raised think=on rerun. The off and on decks are content-untouched (compare is a third artifact).

## 2026-06-10 — Unified findings deck built (`--think unified`); three honesty fixes applied to the shared deck code

`rq_deck.py --think unified` → `checkpoints/rq-sweep5v2-unified/` (57 slides: 43 main + 14 backup), the fourth artifact consolidating the three decks (off 47 + on 48 + compare 12 = 107 slides). Structure: think=off spine (locked verdicts, full evidence) + the compare deck's cross-mode synthesis slides re-emitted verbatim + a NEW limitations slide. The think=on deck is NOT re-presented RQ-by-RQ (every think=on availability gap is budget-confounded); think=on enters only via the budget-cliff evidence slide and budget-insensitive statistics (robust floor, 35B control). Same gate discipline as compare: off locked verdicts + phase-2 oracle, on computed by the same signed rule, pattern + cross-mode consistency asserted at build time. Source decks untouched in content (rebuilt only to pick up the shared-code fixes below).

**Keep/drop decisions (talk + paper narration):**
- **Headline rewritten for honesty.** The off-deck hook ("solve 8–11% without the tool") quotes the weakest baseline we constructed — reasoning lifts the unaided 35B to 38%. The unified hook quotes the solve gap against the BEST unaided configuration (38% vs 92%, same think=on cell) plus the robust floor (≥ +46pp every ≥9B model, both modes). simulate stays the opener: 0% no-tools — every model, both modes, all 3,000 trials (asserted at build).
- **Dropped:** the think=on per-RQ section; the "~2× per-trial cost" think=on framing as a headline (most tool-flattering number we have; appears only inside the cost-of-pass-flip slide with the 35B control); the think=on completion-only backup tables and the think=on 0.8B table; duplicate pedagogy. **Demoted to backup:** RQ0.1 success tables (charts saturate ~100%), RQ0.5 bin table, cross-mode per-model detail + truncation-by-cell tables, completion-only lens (off pair, labelled tool-flattering). **Kept in full:** RQ0.3's complete armor (claim + silence-decomposition + evidence + mechanism — our most attackable verdict), signed significance as its own beat, RQ0.6 null, contamination slide carrying BOTH the null and the tokenisation artifact, the compare claim-sheet as the closing slide.
- **NEW limitations slide** (didn't exist in any deck): single-tool-use scope (+ phase-3 PlanBench/Huang&Zhang out-of-scope), 5 models/2 families, 8,192 cap with cap-raised rerun untested, one-sentence steering, latency unrecoverable, strict end-to-end grading conflates ability+format adherence (deliberate), FastMCP relabel verified inert on sweep5v2.

**Three honesty fixes in shared deck code (apply to off/on/unified rebuilds):**
1. **Truncation metric was misleading cross-arm** — `truncated` = ANY-turn done_reason=="length" (runner.py:214), so tool arms showed 67–73% "truncated" alongside 83–97% success (multi-turn trials are graded from the tool result; a cap-hit on the final narration turn doesn't void the answer — success-given-cap-hit ≈ 85–91% in tool arms, 0–2% in no-tools). The censoring table now carries BOTH 'hit cap %' and 'cap-hit & failed %' (the truncation that mattered: e.g. simulate steered off 73% → 9%) with the asymmetry rule as a VISIBLE caption. Reviewers comparing 16% no-tools vs 73% steered raw truncation would otherwise have caught a real apples-to-oranges.
2. **simulate 0% now carries its grader + decomposition on-slide** (RQ0.4 answer slide): success = canonical-form deep-equality of the FULL state trajectory vs the oracle, structured JSON only, no partial credit, no free-text fallback (scoring.py). The unaided 0% decomposes (≥9B, think=off): 68% unparseable trajectory JSON, 29% cap-truncated, 3% parsed-but-wrong. Strictness is intentional (format adherence is part of the task — user decision 2026-06-10); an all-zero cell without this reads as a grader bug.
3. **0.8B "mishandles the tool" now has its trial-level mechanism on-slide**: it SELECTS the tool in 93–100% of trials but 57% of all trials end in tool_error — 98% of those are errcode `missing_required_arg` (right tool, required argument omitted, typically `domain` supplied without `problem`; verified over 4,095 tool_error trials) — plus 6% loop_exhausted. Access without call-competence turns the tool into a distraction; matches the MCPToolBench++ calls-tool-but-can't-use-it shape (05-29 note).

Infra: `S_table_slide` gained a visible `caption` param (speaker `notes` are invisible in renders — load-bearing evidence must be captions; caption placement accounts for LibreOffice's ~0.29–0.31" row-height floor); compare-deck slide blocks refactored into `_s_cross_*` functions shared verbatim by compare + unified (no prose drift). Render-checked via soffice→PNG on the hook, scorecard, RQ0.3 mechanism, 0.8B, censoring, limitations and claim-sheet slides.

## 2026-06-11 — Advisor action list (Sunday review) addressed in the unified deck

Deck rebuilt: 58 slides (43 main + 15 backup). Three additions + one merge, each mapped to an advisor item:

- **"Success/truncation rate of think=on with and without tools" + "thinking mode visibly compared" → new slide 33** (`fig_visible_mode_compare`): per task, ≥9B pooled, Wilson 95% — success (top) and cap-hit-&-failed (bottom) for no-tools/steered × off/on, solid vs hatched. The budget confound in one picture: steered arm barely moves across modes; think=on no-tools loses 54–83% of all trials to the cap. Plain arm deliberately excluded (its think=on collapse is a tool-CALLING failure, shown on its own slides).
- **"Explore why 9B beats 35B + other works" → new slide 21** (`_s_size_inversion`, computed live): the inversion exists ONLY in the plain arm (think=off solve 9B 99% vs 35B 63%) and is tool-call PROPENSITY, not capability — dominant failure tool_not_selected, success tracks tool-use ~1:1, accuracy-when-calling ≥93% both, steering closes it (35B 63→92), and the propensity FLIPS with mode (think=on: 35B calls validate_plan 99.9%, 9B drops to 69%). 35B's unaided baselines beat 9B everywhere — not a size law. External check (web, 2026-06-11): no prior work pins a size-inverted spontaneous-adoption effect; closest = tool over-reliance/over-refusal duality (arXiv 2503.06708) + our ThinkBrake/Databricks analogs. This is a small novelty claim for the paper.
- **"Qwen 0.8B not good with tools — other refs?" → 0.8B slide caption now cites the MCPToolBench++ shape** (AST 0.6–0.9 vs Pass@1 0.2–0.5) alongside the trial-level missing_required_arg mechanism.
- **Concision:** "What we're testing" + "Three setups" merged into one slide; RQ0.4 success table → backup (baseline rows are degenerate 0s; chart + grader decomposition carry the slide).
- Items already addressed by the Tuesday build (verified, no change): steering→tool-use→success mechanism slides w/ Gemma (advisor's "important note"); simulate crash = strict-structured-output cause (grader + 68/29/3 decomposition on-slide); think=on token-limit problem (cliff, limitations, robust-floor-only claims); "does using tools save tokens" (quadrant + cost-of-pass dumbbell + exact decomposition: no per trial 4–15×, yes per success only where the baseline is floored).
- **Open research items NOT deck-resolvable (for the advisor):** (a) cap-raised think=on rerun ("can we get more tokens") — harness change, untested; (b) token-limit-in-evals literature exists and is citable in the paper: budget forcing s1 (2501.19393), "Reasoning Models Can Be Effective Without Thinking" (2504.09858), "Do Thinking Tokens Help or Trap" (2506.23840 — truncation failures 86→37% when thinking suppressed), SelfBudgeter (2505.11274), thinking-budget scaling laws (2508.12140) — verify abstracts before citing per the 05-29 caveat rule.

- 2026-06-11 (later): slide 33 split per user request into per-model pair (33 success / 34 cap-hit&failed), rows=models x cols=tasks; pooled variant retired. Caption numbers re-verified per model.

## 2026-06-15 — Reproducibility checklist filled + inlined; HF ids added to body

- **Checklist (item 7) DONE.** `authorkit27/ReproducibilityChecklist.tex` inlined verbatim into
  `paper/main.tex` after `\bibliography{refs}`, before `\end{document}` (AAAI-27 single-`.tex`
  submission rule — no `\input`). Only the "Type your response here" lines were replaced; the
  form (incl. author instructions) is otherwise untouched, per the template's own rule.
- **Answers (23 questions).** General 1.1/1.2/1.3 = yes. Theoretical 2.1 = no → 2.2–2.8 = NA
  (empirical paper, no theorems). Dataset 3.1 = yes, 3.2 = yes, 3.3/3.4 = NA (no NOVEL dataset —
  corpus is the earlier study's released set + public benchmark suites, framed as not-novel in
  §Tasks/Fixtures), 3.5/3.6 = yes (existing-lit datasets cited + public), 3.7 = NA (all public).
  Computational 4.1 = yes; 4.2 = **partial** (hyperparameters fixed by design — temp 0, ctx
  16384, decode caps 8192/6144, ≤10 tool loops — not swept-and-selected); 4.3/4.4 = **partial**
  (full repo exists and is release-ready but is NOT attached as a code appendix at submission);
  4.5 = yes (public on publication); 4.6 = partial; 4.7 = NA (temp 0 ⇒ deterministic, no
  randomness); 4.8 = **partial** (infra kept generic — "single workstation-class GPU", no
  GPU/OS/lib versions — for double-blind); 4.9 = yes (N=4,560/cell, 1 deterministic sample/trial);
  4.10 = yes (Wilson + Newcombe MOVER); 4.11 = yes; 4.12 = **partial** (signed disjoint-CI rule,
  not a named test like Wilcoxon); 4.13 = yes.
- **Honesty deviations from the HANDOFF pre-load** (decided here, no-overclaim): 4.2/4.8/4.12 →
  partial (design-fixed params / anonymized infra / non-classical significance procedure);
  4.3/4.4 → partial because we are NOT attaching anonymized supplementary code at submission (only
  committing to release on publication, which is 4.5 = yes). **Open user call:** flip 4.3/4.4 to
  yes only if we decide to submit a code appendix.
- **HF model ids added to the body, not the checklist** (checklist answers are single yes/no/NA
  tokens and cannot carry ids). New footnote in §Models and Serving: `Qwen/Qwen3.5-{0.8B,4B,9B}`
  served 16-bit; the two MoE checkpoints `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit` and
  `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit` are community AWQ-INT4 quants. Third-party ids, not
  author-identifying ⇒ no double-blind violation; closes the repro gap from the non-canonical
  roster labels.
- **Build.** Clean (0 undefined refs, 0 overfull boxes). PDF now 9 pages: technical content still
  ends on p7; references + checklist fill p7→p9 and do not count toward the 7-page limit. Not yet
  committed (commit when the user asks).

## 2026-06-15 (session 2) — figures→vector, contamination table, RQ0.5 deck fix, code-availability decision

Addressed the post-checklist gap list. Two decisions were taken to A* best practice, each
validated by an independent ranking subagent (the user asked for a second perspective):

- **Contamination control → keep in MAIN text + add a table (NOT appendix/repo-link).** The
  user's initial lean was "move it to an appendix, a GH repo link suffices." Researched against
  A* convention: the direct subfield precedent (PlanBench / Mystery-Blocksworld — a structurally
  identical renamed-symbol control) puts the obfuscation method AND headline result in MAIN-TEXT
  tables, never appendix-only; a NULL result is the one reviewers most distrust, so it needs MORE
  visible evidence; and a repo link inside a double-blind PDF is a deanonymization hazard. So we
  added **Table 3** (per model: canonical vs anonymized no-tools success, Δ, N=4,560), tightened
  the in-text claim from "≤1.3pp" to the verified **mean |Δ|=1.1pp (max 3.7), 0 CI-disjoint
  cells**, and moved the think=on validate_plan exception's substantiating numbers into prose
  (Δsucc tracks Δcompletion ~1:1; success-given-completion equal; anon prompts +5% longer →
  truncation). Numbers verified 3 ways (analyzer loader + raw trials.jsonl + saved summary) over
  results/sweep5v2-live vs results/sweep6-live; paper's prior claim confirmed and was conservative.
- **Code availability → release at PUBLICATION, not at submission (C1-at-publication).** Best
  practice (per AAAI checklist framing + the research brief) allows decoupling "code in an
  appendix at review" from "public on publication." The user chose no review-time artifact, full
  release at publication. So checklist code-appendix items 4.3/4.4 set to **no** (nothing attached
  at review) and 4.5 stays **yes** (public on publication) — the honest pairing. The eventual
  release form (decided) = a curated, SCRUBBED package: eval harness + BOTH corpora (canonical +
  renamed), NO cluster/SLURM scripts, no .git, all hostnames/usernames/org/paths scrubbed. NOT an
  anonymous.4open.science link (can't scrub in-file institution strings; proxy flaky). Build it at
  publication time (the prior "F" item).
- **Figures → vector PDF.** The 3 Results figures re-rendered as true matplotlib vector PDF
  (`paper/figures/{solve,simulate,mechanism_validate_plan,token_quadrant}.pdf`) via the analyzer
  plotting code; main.tex includes switched to .pdf. Camera-ready quality.
- **Deck RQ0.5 prose corrected.** Verified from the live data: solve gap ~constant (+87/+87/+89),
  simulate gap DECLINES (+99.7/+93.2/+77.1) because its tool arm degrades on long trajectories.
  The PAPER was already correct; the DECK slide prose was the stale artifact (the plot itself was
  correct). Fixed both deck builders in rq_deck.py and regenerated the unified deck.
- **Build/pages.** Clean (0 undefined, 0 overfull). PDF now 10 pages, but technical content still
  ends on **p7** (Table 3 + Conclusion on p7; refs + checklist fill p7→p10, neither counts). Not
  trimming — user + advisors will choose focus (their call, gap D).

- 2026-06-15 (session 2, later): per user, **PlanBench is moving INTO this paper** (no longer a
  Future-Work-only mention). Sweep still running, so left FORWARD-NOTES only: a TODO marker in
  `main.tex` above `\section{Future Work}` + a REMAINING item in HANDOFF. Plan when it completes:
  add PlanBench results + discussion with the same end-to-end grading / signed-significance /
  contamination controls, update GOALS.md (drop the "PlanBench out of scope" line), and trim
  Background/Discussion to hold 7 pages (cut location deferred to user + advisors). PDF-metadata
  verified CLEAN via `exiftool` (generic TeX/pdfTeX fields only; no author/path). Shipping via the
  existing PR #76 for the user to merge.

- 2026-06-17: **Executed the REVIEW_AND_REWRITES.md rewrite of `paper/main.tex`** (branch
  `paper-rewrite`). Applied all five must-do items: (1) §0/§5 reframe — abstract + intro
  contributions + new **Discussion** section now foreground *invocation propensity*
  (`success = P(call) × P(correct|call)`, all between-arm variance in the first factor) as the
  general, transferable lesson, with PDDL as the oracle that makes residual failures unambiguously
  *model behavior*; (2) §1 MUST-FIX — replaced the `validate_domain` mis-framing: it is now a
  *rescue* from at-or-below the 83.3% trivial (5:1) line / near-chance balanced accuracy (53–74%),
  not a "partial baseline"; subsection retitled "Two Validation Tasks: Headroom and Rescue";
  scorecard RQ1 evidence cell leads with balanced accuracy; (3) §2 — added the formal mediation
  paragraph + appendix decomposition table (`tab:decomp`); (4) §4 — three statistics sentences
  (paraphrase clustering ⇒ anti-conservative Wilson; disjoint-CI is conservative not over-eager;
  no FWER, by choice); (5) §6 — set real **title** ("Availability Is Not Enough: When Symbolic
  Tools Help---and Hurt---LLMs on Planning Tasks"), enumerated the six RQs, **dropped the `0.`
  prefix (RQ0.x→RQx)** everywhere, added a regime-axis disambiguation paragraph (task axis vs
  cross-mode axis overlap only on "sole-source"). Also added the §8 per-task contamination appendix
  table (`tab:contam-pertask`) + `tab:vdom` per-class table; shrank the Conclusion to 4 sentences.
  **Two honest deviations from the doc's paste-ready text, both to enforce internal consistency
  with the §1 MUST-FIX decision:** (a) abstract no longer calls *both* validation tasks "rescued
  from at-or-below-trivial" (only `validate_domain` is sub-trivial; `validate_problem` clears its
  50% floor); (b) the per-task contamination sentence says the *largest* drifts favor the
  anonymized corpus rather than "every nonzero drift" — the doc's own table has two small
  `validate_plan` cells (−0.4, −1.9) going the other way. Added `\usepackage{amsmath}` for the
  `\text{}` decomposition notation. Build clean (0 undefined, 0 overfull); PDF now **11 pages**,
  body (Intro→Conclusion) ends early on **p8** (was p7) — the new Discussion consumed the prior
  headroom; references/appendix/checklist remain supplementary. **NOT done (out of scope for a
  prose rewrite, flagged in REVIEW §3/§7 as "if compute/time allows"):** the figure work (failure-
  type taxonomy stacked bars, Fig 2 `P(correct|call)` overlay, Fig 3 cost-of-pass annotations +
  tick-format fix, Fig 1 y-cap) and the one-frontier-model `validate_plan`+`simulate` experiment.
  PlanBench stays Future Work (per REVIEW §7). Page trim to hold 7-page body still deferred to
  user + advisors.

- 2026-06-17 (figures): **Completed the no-compute figure work from REVIEW §3** via a new
  reproducible generator `paper/figures/make_paper_figures.py` (imports the analyzer deck's data
  layer — `build_deck.load_all` + `rq_deck` helpers — so every number is byte-identical to the
  locked deck; read-only over `results/sweep5v2-live`, 136,800 trials). Re-rendered all four
  Results figures as vector PDF plus one new figure:
  (1) **Fig 1** `solve.pdf`/`simulate.pdf` — y-axis capped 122→**105** (legend moved below to
  reclaim the space). (2) **Fig 2** `mechanism_validate_plan.pdf` — added a faded dashed
  **P(correct|call)** reference (`accuracy when called`) on the success panel; sits at ~99% above
  Gemma's 21% plain bar, making silence-not-error visually undeniable. (3) **Fig 3**
  `token_quadrant.pdf` — printed the **cost-of-pass multiplier** per panel (solve 0.4× in green,
  validate_domain 2.8×, validate_problem 4.4×, validate_plan 3.9×, simulate "tool-only") and
  fixed the log x-ticks to clean $10^3$/$10^4$ mathtext (was the "10 3 104" glitch). (4) **NEW
  Fig 2** `failure_taxonomy.pdf` (full-width `figure*`, label `fig:failtax`) — per-task×arm
  100%-stacked outcome composition (success / truncated / no-tool-call / unparseable /
  wrong-content / tool-call-error), pooled ≥9B. **Generator self-checks reproduce the paper text
  exactly:** cost-of-pass solve 0.38× & validate_plan 3.91×; simulate no-tools mix
  **68.0% unparseable / 29.1% truncated / 2.9% wrong** = the draft's "68/29/3". Wired
  `fig:failtax` into Results (referenced from the simulate decomposition + the validate_plan
  silence paragraph). Build clean (0 undefined, 0 overfull); PDF now **12 pages** (the new
  figure* added ~0.5pg of float). **Still NOT done (the one genuinely new-compute item):** the
  one-frontier-model run on validate_plan+simulate (REVIEW §7) — needs API/GPU inference, not a
  re-plot.

- 2026-06-19: **Wrote the Sonnet 4.6 no-tools frontier result into `paper/main.tex`** (branch
  `paper/aaai27-sonnet-frontier-writeup`, off `paper/aaai27`). This closes the one genuinely
  new-compute item the prior figure entry flagged as "NOT done" (REVIEW §7A: the frontier
  generality + contamination experiment, both corpora completed 2026-06-19 in
  `results/sonnet-frontier/{sweep5v2,sweep6}`, N=4,560/corpus, think=off). Three additive edits,
  build clean (16pp, +1pg vs 15pp baseline, 0 undefined refs, 0 overfull): (1) **Robustness** — new
  `\textbf{A frontier proprietary model.}` paragraph + compact `tab:frontier` (5 tasks ×
  canonical/anon/Δ); (2) **Limitations** — replaced "need not transfer to proprietary or frontier
  systems" with the honest split: the *unaided baseline* structure (sole-source floor +
  contamination null) DOES extend to Sonnet, but the *with-tools invocation-propensity* finding was
  measured only on the open-weight roster; (3) **Future Work** — added the proprietary-with-tools
  question (does aggressive tool-use post-training close the availability gap / steering repair?).
  **Verified numbers (recomputed from raw trials, Wilson 95%):** simulate 0%/0% (sole-source floor
  holds at the frontier; rule-of-three ≤1.3%), solve 28.7%/28.3% (ABOVE the open roster's 8–11%
  floor — frontier model retains modest unaided planning but still fails most problems unaided),
  validate_problem 89.7/90.5, validate_domain 93.6/91.7, validate_plan 97.3/97.3. Contamination null
  is CLEANER than the open roster: every Wilson CI overlaps, max |Δ|=1.9pp (validate_domain, favors
  canonical but well within noise — so NO directional/memorization claim, unlike the open roster's
  "favors anon" framing), pooled |Δ|=0.04pp. **KEY honest scope:** Sonnet ran NO-TOOLS ONLY
  (with_tools=False both corpora), so it corroborates the baseline side, NOT the headline propensity
  finding. **Haiku decision (user asked to suggest):** Haiku *no-tools* = LOW added value (Sonnet
  already gives a STRONGER same-lab frontier no-tools baseline + contamination null; a second,
  weaker, same-lab point is largely redundant and addresses no distinct objection). Haiku *with-tools*
  = the only thing that would extend the CENTRAL propensity finding to a proprietary model, but (a)
  multi-turn MCP tool-calling is NOT batchable (the cheap Batch-API shim only covered single-shot
  no-tools) so it is the integration-risky path REVIEW §7B already flagged, and (b) Haiku is the
  cheap tier, not the flagship the "aggressive tool-use RLHF" objection targets — so if a proprietary
  with-tools datapoint is ever funded, Sonnet-with-tools on the two diagnostic cells (validate_plan
  plain+steered) is the more defensible spend. RECOMMENDATION: do NOT add Haiku for this submission;
  it is already routed to Future Work as a concrete named experiment. Not yet done: PR into
  `paper/aaai27`; Overleaf sync (pull+commit before push).

## 2026-06-20 — Frontier no-tools result elevated into the Discussion (conservative framing)
- Decision (Omer, asked to choose): the Sonnet 4.6 no-tools result, already in Results (`tab:frontier`)
  + Limitations from #83, was **elevated into the §Discussion** as load-bearing evidence — and framed
  **conservatively** (no bimodality rhetoric, no with-tools overreach).
- One sentence added to the LLM-Modulo implication, right where it sets up "the task exceeds the
  model's unaided reach": *the sole-source tasks genuinely exceeding unaided reach is not an artifact
  of our open-weight roster's scale — Claude Sonnet 4.6 reproduces the floor without tools (simulate
  0/300 per corpus, solve 28.7%), so the necessity of an external solver/simulator reflects a
  capability boundary rather than the limited scale of the models we tested.*
- This converts the frontier run from a robustness footnote into a refutation of the "the floor is
  just weak open models" alternative explanation for the central sole-source claim. Scope stays
  honest: no-tools only, so it corroborates the baseline, NOT the with-tools invocation-propensity
  finding (still open-weight-only, per Limitations).
- Build clean (16pp, 0 undefined refs, 0 overfull). Branch `paper/aaai27-frontier-discussion` →
  merged to `paper/aaai27`, pushed (CI auto-syncs to Overleaf with the clobber guard).

## 2026-06-20 — Iter-2 external review triage + decisions (both Stanford reviews ACCEPT)
- Two iter-2 Stanford agentic reviews (AAAI + NeurIPS rubrics) both **ACCEPT**; 16 consolidated asks
  triaged in `paper/automated-platforms-review/iter2/iter2_action_plan.md` (annotatable decision sheet).
  ~10 are writing-only, 2 worth new compute ([5b], [6]), 1 trap ([2]), 1 further-along ([1]).
- **Decisions (Omer):** (A) **BF16** — keep the within-model `P(call)×P(correct|call)` reframe; do
  NOT fold a BF16 number (would contradict the "sweep7 discarded" decision). (B) **Venue = AAAI-27**
  now (Jul 27); JAIR/AIJ journal extension kept as an *optional, uncommitted* future path, not chosen.
  (C) **Compute** = [6] schema-salience first, then [5b] simulate compressed-diff "if easy" (two
  phases). (D) **Frontier [1]** = verify the Sonnet `solve`/`simulate`=0 (likely the sweep7 JRE/host
  artifact) before surfacing the with-tools pilot (Haiku ≈100% on disk, `results/frontier-with-tools-probe/`).
- **Reopened [8] think=on budget — key finding:** the "failed pilot" (`b527f71`, 2026-05-21) only
  enlarged the *shared* context window (16K→32K); it never separated reasoning vs answer caps. So the
  reviewer's decoupled-budget ask is a **genuinely different experiment** the pilot does not refute.
  → **Honesty fix landed** (see below). A true decoupled budget = harness-side budget forcing
  (`stop=["</think>"]` + 2-call continuation), 2-4 days dev, ~1-2 GPU-days, binding case Gemma-MoE-26B
  (89-100% trunc). Verdict **RUN-IF-TIME after [6]/[5b]** (DECISION E pending).
- **[2] fresh cluster BF16 now safe:** sweep7 was killed by missing Java/ENHSP on RunPod, not quant;
  the cluster env ships openjdk-17, so a clean BF16 35B on `rtx_pro_6000:1` (96GB, HF-id swap only) is
  feasible (~0.5 day). But expected **null** (AWQ≈BF16 already known) + competes for scarce pro_6000.
  Verdict **RUN-IF-TIME, Exp1 wins if forced to choose** (DECISION F pending).
- **Meta (Omer floated a consolidated "fixed sweep"):** NO — controlled ablation = one knob per corpus
  vs the shared sweep5v2 baseline; consolidate the *submission* (parallel array), never the *factors*
  (corpus identity is load-bearing). [[feedback_pushback_on_methodology_shortcuts]]
- **Writing landed this session on `paper/aaai27`** (build clean, 16pp, 0 undefined, 0 overfull):
  [9] FWER — the √2.7 design-effect inflation already imposes effective $z\approx3.2$, stricter than
  Bonferroni for a ~30-contrast confirmatory family ($z\approx3.1$), so verdicts clear simultaneous
  control without a dedicated correction; [12] cost — added the production note (a system could not
  re-feed/summarize tool outputs → our cost-of-pass is a faithful worst case); [8] honesty clause —
  the failed pilot raised the *shared* budget, not a *separate* answer cap. Remaining writing batch
  (5a, 13, 14, 16, 3/4/7/10/15 framings) + probes [6]/[5b] + frontier verify still pending.

## 2026-06-20 — Iter-2 T2: remaining writing asks landed (branch `paper/iter2-writing-2`)
- **[16] Executive summary** — a 4-number practitioner paragraph now opens the Discussion: sole-source
  0%/≈29% unaided (even frontier), luxury ≈3–5×, −67pp availability harm, +73pp (21→94%) steering
  repair, >92% accuracy-given-call. NeurIPS asked for an effect-size skim; this is it.
- **[14] Related work** — situated vs ReAct \citep{yao2023react} + program-of-thought
  \citep{chen2023pot} (those *scaffold* invocation; we *measure* it); added an RLHF/post-training
  sentence \citep{ouyang2022instructgpt} in Discussion — the cross-model P(call) spread is plausibly
  an alignment-recipe property, not just scale (answers the "RLAIF/RLHF influence on propensity" ask).
- **[7]+[13] tool-call iteration stats** — computed offline from `sweep5v2-live` (91,200 with-tools
  trials): median **1** call, 60% single-call (90% succeed), 27% multi-call with success falling
  monotonically (67%@2 → ≈25%@5+), 13% zero-call (silent failures). → AAAI Q1 answer: single-call
  limiting removes low-yield retries, not successes. Added to Methodology pipeline.
- **[13] HW/SW stack** — Models&Serving now names 48GB/96GB GPUs, vLLM/CUDA/Linux, one-model-per-GPU
  + prefix caching, pointing to the Reproducibility Checklist for exact versions (anonymization-safe).
- **[10] forced-decoding honesty** — Future Work note: constrained decoding sets P(call)=1 by
  construction (relocates the question to accuracy-given-forced-call), distinct from raising propensity.
- 3 new bib entries (react/pot/instructgpt). Build clean (16pp, 0 undefined refs, 0 overfull).
- The [3]/[4]/[15] framings were already adequately present (matched-prompt, steering, richer-PDDL) —
  verified, not re-touched. [5a] simulate partial-credit writeup folds into T4 (same section as [5b]).

## 2026-06-23 — `simulate` 0% "sole-source floor" was substantially a grader artifact → corrected to ~40–45%
- **Bug.** `_normalize_trajectory` compared simulate trajectories by lowercase + whitespace only; it never
  reconciled the model's PDDL s-expression `(ontable shaker1)` against the oracle's functional
  `ontable(shaker1)`. Every *correct* no-tools simulation scored `result_mismatch` → an artificial 0%.
  Fixed (commit `5879ac4`; [[project_simulate_grader_artifact]]; ISS-024). With-tools simulate (functional
  on both sides) was unaffected.
- **Corrected frontier `simulate` (no-tools, think=off, 95% Wilson):** Haiku **0 → 42.0% [32.8,51.8]**;
  Sonnet canonical **0 → 45.0% [39.5,50.7]**; Sonnet anon **0 → 38.3% [33.0,43.9]**. Re-graded locally from
  the raw batch dirs (no spend, no cluster); all non-simulate cells reproduced byte-identically (built-in
  regression check passed) — the fix touches only the simulate leg.
- **The floor is real but ~40–45%, not 0.** Of trials that produced a *parseable* trajectory, Sonnet is
  correct **135/149 = 90.6%** (canonical) / **115/128 = 89.8%** (anon); the remaining loss is **truncation**
  (long trajectories hit the token cap: 89/102 of 300) + **format_parse_fail** (62/70) — output length/format,
  not state-tracking incapability.
- **Contamination probe stays NULL for simulate.** Overall canon 45.0% vs anon 38.3% (Δ+6.7) has *overlapping*
  CIs and is a **truncation confound** — anon prompts are ~5% longer → more truncation (102 vs 89) + more
  parse-fail (70 vs 62). Success-given-parseable-completion is equal (90.6% vs 89.8%) → no memorization
  signal. Same mechanism as the validate_plan×think-on tokenization artifact ([[project_sweep6_design]]).
- **Paper: HOLD — do not rewrite yet (Omer 2026-06-23).** Gather the *complete* simulate picture before
  touching any narrative — avoid fixating on a story while the data is partial. We have corrected numbers for
  **3 frontier cells only**; the open vLLM roster (the bulk of the simulate evidence) is **not** re-gradeable
  from disk (`RESPONSE_SNAPSHOT_LEN=500`, no `gt`), and the budget-vs-capability split in the residual
  truncation (33% Haiku / ~30% Sonnet) is unresolved. Both close via a single (gated) cluster re-run with the
  fix + higher token cap. `paper/` untouched.
- **Provisional read = HYPOTHESIS TO TEST, not an edit to make.** For the FRONTIER, the corrected ~40–45%
  means the "frontier reproduces the floor / 0%→97% bimodal" and Discussion "sole-source 0%" passages would
  need rewriting *if* it holds — simulate becomes a *mid* cell gated by output length, shifting the
  generative-leg low pole toward `solve` (~29%, genuine `plan_invalid`). Recorded to test against full data,
  not to commit now. (`solve` floor + `validate_*` highs are complete and unaffected.)
- **Open-roster ≠ same artifact (verified 2026-06-23).** Earlier guess that the open roster "likely carries
  the same artifact" is **falsified**: their `result_mismatch` (what the notation fix touches) is ~0%. The
  open-roster 0% is a *different* failure — `format_parse_fail` (unenforced `guided_json` lets prose leak past
  the constraint, plus a strict-wrapper sub-artifact the adopted Q1 grader closes) + truncation — unmeasurable
  from disk (`RESPONSE_SNAPSHOT_LEN=500`, no `gt`). So the grader artifact was largely a *frontier* story; the
  open-roster floor is more genuine, and a clean number needs a re-run (Q1 two-metric grader + decoupled
  budget + full storage), not a re-grade. [[project_simulate_grader_artifact]]
  Full breakdown + next steps: `development/{frontier_grading_artifacts_findings.md, simulate_decisions_and_next_steps.md}`.

## 2026-07-11 — Decoupled Line-1 COMPLETE; paper-rewrite deferred to a fresh session; with-tools parity resolved

- The decoupled think=on no-tools re-run is **data-complete (all 4 Qwens)** and analyzed. Final matched
  A/B + consolidated findings: `development/decoupled/decoupled_run_handoff.md` "LINE COMPLETE" §; rollup
  script `development/decoupled/decoupled_rollup.py`. (9B, the last cell, finished 2026-06-29.)
- **Bottom line for the paper:** the no-tools simulate 0% "sole-source floor" is an **artifact** (grader +
  shared-budget reasoning starvation), NOT a capability floor. True no-tools simulate (state-tracking) =
  0.8B 0% · 4B 23% · 9B 22% · 35b 40%. The paper must **retract the 0% floor** and re-frame the tool-lift
  apples-to-apples as decoupled-no-tools (22–40%) → with-tools (~87–96%), not old-0% → 90%. [[project_simulate_grader_artifact]]
- **Two-metric result:** simulate format-compliance = 0% for every model (strict content∧format = 0%);
  all no-tools state-tracking success is Q1 wrapper-tolerant coercion (models get content right, never the
  exact wrapper). **solve:** decoupling is a RISK at mid-capability (4B −6pp), neutral for 9B/35b (ctx-ceiling).
- **With-tools parity — no re-run.** Reuse sweep5v2 with-tools as the comparison arm: decoupling is
  no-tools-only by construction; with-tools never starved (`think_overflow=0`, simulate 87–96%); the only
  apparatus delta (reasoning-parser off vs on) doesn't touch tool-call extraction/grading. A cheap
  parser-off+tools smoke is the apples-to-apples insurance before citing sweep5v2 (ISS-024(d), still gated).
- **Process:** the actual `paper/` rewrite is **deferred to a fresh-session agent** (per user); `paper/`
  left untouched this session.
- **With-tools GRADING-SURFACE caveat (proven 2026-07-11).** With-tools success is graded on the TOOL
  CALL RESULT, not the model's final answer (`scoring.py check_success` reads `tc["result"]` in every
  with-tools branch; the model `response` is read only in the no-tools paths). So no-tools grades the
  model's OWN answer while with-tools grades the TOOL's answer — a more generous surface; with-tools is a
  tool-selection + faithful-invocation metric, NOT strict end-to-end. Empirically (validate_\*, sweep5v2
  with-tools successes) models NEVER misreport the tool (0% contradiction) but ~36% (35b) / ~40% (4B)
  state no checkable verdict — credited on the tool alone (35b: 28.9% completed-yet-silent + 7.4%
  truncated). The paper's tool-lift framing must state this. Proof/repro:
  `development/decoupled/with_tools_grading_surface_probe.py`; caveat detailed in the decoupled handoff.
- **PROPOSED (deferred to fresh session):** a secondary end-to-end with-tools metric that also grades the
  model's final `response` against ground truth, to put a number on the interpretation gap. Offline-computable
  (no re-run). To be discussed, not built yet.

## 2026-07-11 — DECIDED: with-tools grading must read the model's output; snapshot censoring discovered

- **Grading-surface principle DECIDED (Omer).** The evaluation must grade the *model's output*; grading
  only the tool result "makes an internal component the final model output, which it obviously is not."
  Instructing the model to relay the tool output verbatim is fine prompt design; ignoring the model's
  output at scoring time is not. A tool call is itself a legitimate model-output form ("if the model's
  output is the tool call, it's correct"). Consequence: a response-graded **end-to-end** success column
  (same parser as the no-tools branch, both arms) becomes the primary surface for tool-lift claims; the
  current trace-graded metric is retained, renamed **tool-verified** (delegation) success, as the
  mechanism layer. Decision doc + open operational slots (D2b empty-final-turn carve-out, rescoring
  scope, naming, corpora, censoring handling): `development/tool_call_vs_final_output_grading.md`.
- **Supporting fact:** the v14–16 with-tools prompts already demand the answer in the final response
  (VERDICT trailer / "return a plan" / "return the trajectory", `pddl_eval/prompts.py:279–329`), so
  trace-grading contradicts the harness's own task contract — ~29% of 35b with-tools validate successes
  were credited despite disobeying the prompt's output instruction.
- **NEW measurement caveat — response-snapshot censoring (probe v2).** `trials.jsonl` stores `response`
  as a HEAD snapshot; the cap was **500 chars** until 2026-06-25 (`runner.py:145–153,514`), and
  sweep5v2-live predates the raise. Since the VERDICT line is instructed to be LAST, verdicts past char
  500 are invisible offline: of 35b tool-graded validate_* successes, 63.6% restate visibly, 27.6% are
  INDETERMINATE (snapshot exactly 500 chars, no visible verdict), 1.3% ended the turn empty (stop),
  7.4% truncated empty. 4B: 60.3% / 3.5% / 13.7% / 22.5%. So the earlier "36–40% state no verdict" split
  is partly storage artifact: true 35b restatement ∈ [63.6%, 91.2%]; 4B's silence is mostly genuinely
  empty output (real synthesis gap). "0% contradiction" holds only within the visible window. The
  offline end-to-end overlay is exact on post-06-25 corpora and **interval-valued** on sweep5v2-live;
  published no-tools numbers are unaffected (grading ran online on full text).

## 2026-07-11 (later) — grading-surface decisions ALL RECORDED; overlay work starts

- Omer filled all slots in `development/tool_call_vs_final_output_grading.md`: **D2b=B** (a bare tool
  call counts as the model's answer only when the model closed the turn on its own; truncated-empty =
  fail, symmetric with no-tools truncation), **D3=A** (one consolidated rescoring pass: e2e overlay +
  simulate normalizer + validate_plan FP binning), **D4** names approved (**end-to-end success** vs
  **tool-verified success**), **D5** corpora = sweep5v2-live + sweep6 + Sonnet/Haiku frontier + sweep7,
  **D6=A** (censored old corpora reported as bounds; no extra runs).

## 2026-07-11 (later-2) — DECIDED: fresh Haiku + Sonnet single-tool reruns; harness-framework discussion queued

- **DECIDED (Omer): rerun Haiku AND Sonnet single-tool for fresh numbers.** Motivation from the e2e
  overlay findings: the existing frontier corpora are 75–100% snapshot-censored (Sonnet no-tools
  simulate 0/300 is 100% unrecoverable from disk; with-tools probes 75–93% blind on validate_plan), so
  fresh runs under full response saving are the only way to exact frontier end-to-end numbers.
- **GATED on a harness-framework discussion (to be held before submitting):** run the frontier
  single-tool arm on (a) the **Claude API framework** vs (b) the **existing harness** (bare-loop
  `tools/sonnet_tools_probe.py` / batch path). Omer's rationale for (a): he wants a clean
  **transition/bridge from the single-tool experiments to the PlanBench benchmarks** — PlanBench
  frontier will run on the Claude API framework, so that framework must ALSO be assessed inside the
  single-tool experiment for the two benchmark families to be comparable. This folds into the open
  harness fork in [[project_frontier_phase_design]] (bare loop / agnostic / Claude-native); the
  PlanBench-continuity argument now weighs on it.
- Nothing submitted for the frontier reruns yet; the ISS-024(d) Qwen with-tools re-run (job 19293221)
  is running independently.

## 2026-07-11 (later-3) — D2b REVISED: strict end-to-end is the paper's headline

- **DECIDED (Omer): D2b=B → strict (i).** The headline end-to-end metric fails ANY empty final
  turn, both arms; "delegation-terminal" (right tool call, deliberate silence) becomes its own
  labeled outcome category in the tables; the B-graded column stays in the overlay as a derived
  diagnostic. Basis: (1) external audit — ABC (arXiv:2507.02825) names "τ-bench counting empty
  responses as successful" as the field's canonical reward-design flaw, and D2b=B was a
  conditioned version of the same rule; (2) measured strict-vs-B comparison
  (`tools/e2e_d2b_compare.py`, run 2026-07-11 on the existing overlays): only 3.6% of sweep5v2
  rows carry the credit, and 2/25 lift verdicts flip — 35b validate_problem (0.3pp knife-edge,
  a wash under both rules) and 9B solve (censoring-bound; the running ISS-024(d) 16K-cap job
  resolves it exactly). Every headline validate lift survives strict grading.
- **Promoted finding:** the D2b sensitivity concentrates in 9B, not 4B — 9B silently delegates
  on 10–35% of with-tools validate rows (strict lower bounds drop 97/88/78 → 87/53/55, all
  still lifts). The model with the best delegation (tool-verified 87–99%) restates worst: the
  answer-synthesis gap GROWS with delegation competence.
- **ISS-024(d) (job 19293221) kept running** — unaffected by the scoring choice (grading is an
  offline overlay over raw rows) and now the resolver for the strict-undecided cells.
- Full audit (incl. frontier-rerun harness conditions, probe sizing, open ANSWER slots):
  `development/decision_audit_grading_and_frontier.md`. Overlay emits dual columns
  (`e2e_strict` headline / `e2e` = B diagnostic); existing overlay files patched in place.

## 2026-07-11 (later-4) — Frontier rerun framework DECIDED: B (SDK Tool Runner); probe + budget approved

- **All slots filled (Omer) in `development/frontier_rerun_framework_decision.md`:** D1=**B** — the
  frontier Haiku+Sonnet single-tool rerun (and the future PlanBench with-tools backend) run on the
  Anthropic SDK Tool Runner + MCP helpers, ONE shared module for both benchmark families; the
  existing bare loop (A) survives only as the probe's comparison arm. D2=**yes** to the paired
  A-vs-B harness probe — operationalized as a STAGED probe (100 paired trials ≈ $5–10 first;
  extend to 300–500 for quantification only if discordance appears; see audit §2.3 ANSWER).
  D3=**single prompt variant** everywhere; slice the old 3-variant Sonnet NT corpus to the matching
  variant when comparing. D4=**approved**, with a hard budget note: Claude API currently funded
  with **$238** — below the $200–350 ballpark upper bound, so execution is budget-sequenced:
  probe → Haiku both arms → re-estimate from measured cost → Sonnet only if the remainder covers
  it (else top up / Haiku-first read).
- Build conditions carried from the audit (§2.2): pin the exact `anthropic` SDK version (Tool
  Runner + MCP helpers are beta surfaces); verify `max_iterations` counts the same unit as
  MAX_TOOL_LOOPS=10 so `loop_exhausted` stays comparable; per-turn request logging; validate
  prompt caching on the probe (`cache_read_input_tokens > 0`; Haiku min cacheable prefix = 4096
  tokens); disclose the qwen3_xml-vs-native-FC prompt-surface delta in limitations (inherent to
  the cross-family comparison, exists under A too).
- Next action: build `tools/frontier_runner.py` (Tool Runner loop, standard trials.jsonl rows,
  16K snapshots, caching, per-trial cost log) → stage-1 probe → full run per budget sequence.

## 2026-07-11 (later-5) — Frontier runner (framework B) built + live-smoked; caching is NOT a cost lever

- **`tools/frontier_runner.py` built** on the SDK Tool Runner (framework B, D1). Live 3-trial
  Haiku smoke (real API + MCP, cached GT) passed end-to-end: runner loop → MCP tool exec →
  grading 3/3 OK; SDK version pinned (anthropic 0.109.2); `--use-cached-gt` skips the heavy
  `generate_ground_truth` solver prelude (opt-in — full run + paired probe generate fresh so
  both arms share one GT source); offline `--dry-run` job counts verified (full grid 9120,
  single-variant 1520 = the doc's Haiku D3 estimate).
- **FINDING — prompt caching does not reduce frontier WT cost (revises the D4/memory "caching
  is the cost lever" assumption).** After moving caching off a below-4096-token system block
  onto the SDK runner's own `cache_control` (multi-turn breakpoints), caching is ACTIVE but on
  the smoke it was a **net +6% LOSS**: trials are short (~2 turns) with a large, unique
  per-trial domain/problem context, so the 1.25× write premium on the ~52K prefix isn't
  recouped and consecutive trials share no big prefix. Budget the WT arm at **no-cache list
  price** ($1/$5 Haiku, $3/$15 Sonnet); the stage-1 stratified probe (all 5 tasks) settles
  whether any task benefits. Detail: `development/decision_audit_grading_and_frontier.md` §2.5;
  cost lines in `frontier_rerun_framework_decision.md` annotated.
- Next: generate the stratified stage-1 keys file → run it through BOTH `frontier_runner.py`
  (B) and `claude_api_tools_probe.py` (A) → compare success + turns/tokens + real cost.

## 2026-07-12 — Haiku WT solve/simulate "delivered gap" RETRACTED: three overlay grading artifacts, not answer-dropping

- The morning headline (WT solve e2e 13.5 vs tool-verified 100; simulate 0 vs 97.5) is
  withdrawn. Drilling into the raw trials showed the model delivers the answers; the
  overlay grader could not read them. Do not cite the 13.5/0 row anywhere.
- **Artifact 1 (solve):** Haiku formats plans as markdown numbered lists with backticked
  actions + trailing annotations; the strict extractor requires bare `(action)` lines.
  190/200 delivered plans are VERBATIM copies of the tool-validated plan.
- **Artifact 2 (simulate):** Haiku wraps a complete ```json trajectory fence in prose; the
  Q1 rule parses the whole response as one JSON value. Canon: 52/100 fenced trajectories
  match the oracle exactly.
- **Artifact 3 (anon oracle, hits NT too):** sweep6 rows were graded against canonical
  fixtures/gt while their symbols are anonymized → anon solve 32/32 falsely invalid,
  NT-anon simulate 59/100 clean parses all falsely mismatched (the pooled NT simulate
  0.0 [0, 5.7] was artifact as well).
- **DECIDED (D7/D7b, recorded in tool_call_vs_final_output_grading.md §0b):** overlay
  delivered-answer extraction is format-tolerant, identical in both arms, with per-row
  `extraction` provenance; sweep6* grades against domains-anon + gt_cache_anon. The frozen
  Q1 online-grader whitelist is untouched. Oracle validation (VAL / deep-equality) makes
  tolerant extraction false-positive-proof.
- **Surviving paper story (replaces "drives tool then drops answer"):** delivered-answer
  fidelity degrades with output length — short plans restated verbatim (~95 delivered),
  long trajectories truncated/elided/summarized (canon [52, 64] vs tool-verified 97.5).
  Secondary finding: strict parser parity across arms ≠ arm neutrality; NT one-shot output
  obeys the JSON format while post-tool-chat WT output is chatty markdown, so the strict
  shared parser partly measured format drift.
- Corrected pooled table to be regenerated from the D7 overlay re-run (all corpora re-run
  under one rule set); Sonnet-WT go/no-go should be revisited against the corrected gap
  (~5pp solve / ~35-45pp simulate, not 85-97pp).

## 2026-07-12 — iss024d reporting discipline: steered pre-commitment, rerun-estimate language, think=on scope (Omer accepted)

- **Steered arm is diagnostic-only.** The iss024d cells emit the full v11-16 bank (the
  "neutral-only" line in the status profile described the board denominator, not the run),
  so exact steered with-tools e2e numbers will exist. Pre-commitment: no steered with-tools
  e2e claim enters the paper unless a steered no-tools control arm is run first — without
  that control, prompt-content and tool-access effects are confounded. sweep5v2-live
  no-tools cells verified v11-13 only (no nt-ster control exists).
- **Language convention: "independent rerun estimate", never "resolved exact value".**
  iss024d is a new sample from a near-identical apparatus (Qwens additionally carry the
  parser-off delta), not a recovery of the censored cells' realized outcomes. Prose says
  "a re-run under full-response storage yields X [CI]".
- **Exact e2e is think=on-scoped.** Both resolver jobs are think=on only; every think=off
  with-tools e2e cell stays bounds-only. Paper e2e claims must state this scope.
- **Parity criteria pre-registered** before the remaining cells land:
  `development/iss024d_parity_prereg.md` (TOST margins, gemma as negative control,
  partial-failure rule).
- **Gemma coverage gap closed:** job 19314599 (gemma4:26b-a4b × on × tools_all_minimal,
  same frozen apparatus + run-tag, submitted 2026-07-12). Gemma has no reasoning parser
  natively, so its only delta vs its sweep5v2 arm is the 16K snapshot cap — it doubles as
  the negative control for the parity check.

## 2026-07-13 — D9 grading extension; Sonnet WT regraded: ladder holds, transcription gap is length-driven not tier-driven

- **D9 (grading, both arms):** the Sonnet WT corpus exposed two more delivered-answer
  formats the D7 tolerance missed (markdown-table plans; one fenced JSON block per
  trajectory step) plus a censoring asymmetry (simulate lacked solve's at-cap
  pre-censor). Fixed in `tools/e2e_regrade.py`, repo-wide re-run; the row diff is fully
  attributable (zero validate_* / NT-non-simulate changes). Details:
  `tool_call_vs_final_output_grading.md` §D9.
- **Sonnet WT canonical (v11, e2e_strict):** solve delivered 95.0 [88.8,97.8] vs
  tool-verified 100.0 — the +5.0pp gap is IDENTICAL to Haiku's, and on both models it is
  transcription-error mass, not answer omission (Sonnet: 0 omitted plans, 5 invalid
  restatements). simulate delivered [49.0,62.0] vs tool-ver 99.0; band overlaps Haiku's
  [52.0,64.0].
- **Paper-facing conclusions:** (1) the tool-verified-vs-delivered gap is TASK-shaped
  (0pp verdicts, 5pp plans, ≥33pp trajectories), reproduced across two frontier tiers —
  the "delivered fidelity degrades with answer length" claim is now two-tier;
  (2) "a stronger model transcribes long tool outputs better" is NOT supported
  (solve tied, simulate bands overlap); (3) the validation tool-lift ladder holds
  end-to-end — lift shrinks as the model strengthens (validate_domain loses
  CI-separation at Sonnet tier), while the solve lift stays enormous at both tiers
  (+73.0 / +66.0, CI-disjoint).
- **Bookkeeping:** Sonnet WT $90.75 measured; frontier spend ≈$167.4/$238. Corrected
  pooled table regenerated (only iss024d still flagged in-flight: 4B done on cluster
  awaiting sync, 9B + gemma running). Full memo:
  `development/sonnet_wt_vs_haiku_e2e_memo.md`.

## 2026-07-15 — NT snapshot de-censor (free re-grade); simulate sole-source claim must be delivered-level-qualified

- **The planned Haiku NT "batch rerun" was unnecessary and is cancelled.** The 500-cap
  corpora were only snapshot-censored: the raw batch `results.jsonl` dirs retain full
  response text, so all three 500-cap NT corpora (Haiku canonical, Sonnet canonical +
  anon) were re-graded to 16K snapshots at $0. Per-row audit: 0 grading diffs across
  10,640 rows — primary numbers unchanged; only the e2e overlay gains determinacy.
  A paid rerun would have re-censored the same >16K-char rows at write time.
- **NT simulate is no longer a floor at the delivered level.** De-censored e2e_strict:
  Haiku canon 54.3 [42.7,65.4] / anon 60.3 [48.0,71.5]; Sonnet v11 canon 42.0
  [31.8,52.8] / anon 36.1 [26.6,46.9]. Unaided frontier simulate delivers ~40–60%
  correct trajectories — the historical 0% was the ISS-021 normalizer artifact plus
  snapshot censoring. Any paper claim that simulate is tools-sole-source must be
  scoped to the OPEN-model roster or to tool-verified-vs-delivered, not to frontier
  no-tools inability.
- **Delivered-level tools-lift on simulate is NOT CI-separated** (Haiku NT [38,68] vs
  WT [49,63]; Sonnet NT v11 [34,53] vs WT [49,62]). The two-tier headline stays
  tool-verified (~97–99) vs delivered (~40–60) — the transcription-fidelity gap —
  while validation keeps its clean CI-disjoint tool-lift.
- **Contamination null extends to delivered-level NT simulate** (canonical vs anon CIs
  overlap for both models), closing the "can't contrast-test simulate" caveat in the
  frontier handoff.

## 2026-07-15 — Simulate sole-source-floor RETRACTION executed in the paper (Omer caught the stale claim)

- **What happened:** the morning paper pass corrected only the FRONTIER simulate numbers
  (0/300 → 45.0/38.3) and left the open-roster "0% for every model / outside these models'
  reach" story intact — but that story was already retracted internally on 2026-07-11
  (decoupled handoff §PAPER REWRITE: true unaided simulate = 0.8B 0 · 4B 23.0 · 9B 22.3 ·
  35b 40.0 content-correct, format-compliance 0% for all). Omer flagged it ("did you use
  the stale outdated analysis?"); the full retraction batch is now in `main.tex`
  (commit `1ac21f4` on `paper/aaai27`, Overleaf-synced 944b1f8).
- **Answer to the floor question:** the 0/3,000 shared-budget corpus zero is ALL five
  models (not 0.8B-marked); under the decoupled control only 0.8B remains at 0%. The
  35B >0% Omer remembered = the decoupled NT 40.0% (and separately iss024d WT tool-verified
  93.2%, a different arm).
- **Paper now says:** deployed-apparatus zero is real but apparatus-bound; decoupled
  control recovers 22–40% content-correct at ≥4B (never format-exact → strict stays 0%);
  tool-lift reframed 22–40 → 87–96 (matching mode); Q1-coercibility ≤0.7% attributes the
  recovery to budget, not grader; frontier 45.0% extends the capability trend. Grading-
  surface disclosure (tool-arm success = tool's returned result, delegation competence)
  added to Methodology + Limitations per the decoupled handoff's "must state it".
- **Process lesson (recorded to memory):** before editing any paper claim, sweep
  development/ for decided-but-pending rewrite specs and paper_notes bottom lines; a
  claim can be internally retracted while still standing in the tex.

## 2026-07-17 — ISS-024(d) complete: pre-registered parity FAILED → separate-apparatus labeling binds the P1 reframe

- **Corpus final:** all 5 iss024d-e2e cells synced + regraded (9,120 trials each; exit
  codes clean). The with-tools open-roster evaluation phase has no runs left (E1.1–E1.4
  done; only the branch merge remains in Track E).
- **Pre-registered verdict (no discretion):** job-level parity vs sweep5v2-live FAILS —
  gemma control noise floor 5.3pp; Qwen 7/20 TOST pass, max |Δ| 11.3pp (35b solve).
  The 07-13 red flag generalizes: every Qwen solve Δ is negative with truncated-rate
  +13 to +19pp concentrated on solve/validate_plan — the parser-off mechanism, exactly
  where long generations live. Validation cells pass or sit within the control floor.
- **What this means for P1/D-N4:** the "if parity passes, iss024d becomes the with-tools
  e2e headline surface" branch is CLOSED. Binding language (prereg rule 4 + 07-12
  interpretation note): iss024d e2e numbers are *independent rerun estimates under
  full-response storage from a separate apparatus*, reported as a labeled replication —
  never as resolved sweep5v2 values, and not silently substitutable as THE with-tools
  number. Paired delivered-vs-tool-verified gaps WITHIN iss024d remain valid (same-corpus
  contrasts don't cross apparatus).
- **The delivered-answer story sharpens anyway:** within iss024d, simulate delivered vs
  tool-verified is 7.0–9.3 vs 63.0 (4B), 10.3–15.0 vs 82.7 (9B), 12.3–13.3 vs 92.3 (35b)
  — the frontier transcription-fidelity gap replicates on the open roster, larger.
  gemma validate_plan inverts (delivered 30.0–63.1 vs tool-verified 0.9): it answers
  without competent tool use. Both are within-corpus claims, safe under the labeling.
- **Grading-surface caveat, quantified for the paper:** even at 16K snapshots the
  parser-off apparatus stays partially censored (worst gemma solve c200/300); bounds
  reporting per D6/D9c stands. A gemma `<|channel>thought` template leak (10 neutral
  rows, ≤3.3pp) is parked as a possible D10 tolerance decision — not applied, so current
  numbers are conservative.

## 2026-07-23 — P2 batch landed; D3 decided RUN NOW; PlanBench Haiku NT graded (t2 artifact fixed)

- **P2 (all three, commit `afc92b6` on `paper/aaai27`, Overleaf `c8c8245`):** Fig 3 ticks
  were already fixed in `4e9a308` (roadmap item was stale — verified by render); the
  "limited prompt set" item became a direct ratio in the Tool Suite subsection (new
  self-citation `benyamin2025copilot`, arXiv:2509.12987: their whole single-task
  evaluation = 250 queries (10 problems x 5 variants x 5 request types) vs our 4,560
  trials per model-mode-arm cell, ~18x per cell); consistency pass found the abstract
  still carrying the unscoped "cannot be done without the tool" — now scoped "under the
  deployed budget and format constraints", matching the 07-15 intro batch.
- **D3 (Omer, in session): PlanBench runs NOW,** starting with the VPN-free grading of
  the on-disk Haiku NT responses. Outcome: only t2 needed work — it was 0.0 everywhere
  from a missing-FAST_DOWNWARD grading artifact (Executor cost fell back to 0; every
  optimality comparison failed). Re-graded with the upstream evaluator + Rosetta VAL +
  plugin FD: **blocksworld t2 28.2 (== GPT-4 28.4); t1 41.0 beats GPT-4 31.4
  CI-disjoint; t3 78.2 trails GPT-4 94.6 CI-disjoint; Mystery collapse replicates
  (t1 0.8); t7 0-vs-GPT-4-28.4 = chat-format sensitivity, grader untouched.**
  Full table/CIs/funnel: `development/planbench/planbench_frontier_haiku_nt.md`.
  Bottom line for the paper: a 2026 small frontier model clears PlanBench's GPT-4 bar
  on generation but not verification, and the two contamination probes (their semantic
  obfuscation, our structural anonymization) now both have frontier data points.
- Next on D3: WT backend over `frontier_runner.py` + pre-registered Act-4 predictions
  BEFORE the tools sweep (mirrors iss024d prereg discipline).

## 2026-07-24 — Journal-pivot decision batch: all 8 open slots decided (decisions memo accepted)

- **Omer accepted `development/journal_decisions_memo.md` in session** (produced by a
  23-agent investigation + 12 adversarial red-team passes, all verdicts AMEND / zero
  refutes, load-bearing claims source-verified). All 8 ANSWER slots annotated:
  D-J1..D-J6 in `journal_narrative_proposal.md`, D2 + D4 in the roadmap.
- **Rulings in brief:** D-J1 protocol-first RATIFIED (findings-hook variant: delivery
  gradient opener 0pp/+5pp/≥33pp, within-arm cascade Fig 1, "Controls that moved
  headlines" subsection; conditional on the three retirements). D-J2=D2=(a) FULL
  REFRAME (delivered = single primary surface; notation hard gate; "how to read our
  numbers" table; storage-fixed rerun as pre-registered contingency). D-J3 minimal
  frontier-only PlanBench Act 4 (NT re-measurement carries the headline; WT secondary
  vs matched-scaffold control; prereg; 08-15 kill → shrink to NT-only). D-J4 =
  recommendation TO ADVISORS: JAIR primary / TMLR fallback / AIJ override-only / KBS
  dropped (advisor conversation still owed; thesis-clock assumption to confirm).
  D-J5 BOTH complements at recommended scope (nt-ster think=off+on ~92 GPU-h +
  same-apparatus anchor, prereg-before-submit; Llama-8B v11+v14 probe; submits
  ping-gated). D4 all three parked + $0 guided_json local audit. D-J6 yes
  (scoped-declarative constraint; collision-check "the delivery gap").
- **Binding factual correction recorded:** frontier simulate delivered is
  censor-bounds (Sonnet [49.0,62.0], 13/100 censored; Haiku [52.0,64.0], 12/100),
  NOT exact — proposal §2/§5 fixed; never quote frontier simulate delivered as exact.
- **E2E overlay placement (Omer asked explicitly): INCLUDED by construction.** Under
  D-J2(a) the overlay is the paper's primary measurement instrument, not an optional
  section: its delivered surface is the headline number in every with-tools claim,
  the dual-surface design is C1 body content, and the D7→D9 grading history becomes
  named controls in the validity subsection. Only the overlay's operational
  MECHANICS (D1–D9 decision log, tolerance history, parity-prereg text) go to a
  structured appendix summarized by one body-level table. iss024d overlay cells keep
  the separate-apparatus label (within-corpus paired gaps only).

## 2026-07-25 — PlanBench WT prereg: slots answered, whole-pool design, E rejected

- **Method note:** the three open ANSWER slots were filled from a 7-agent read-only
  evidence workflow (instance-pool audit, cost model, funnel/scoring audit, statistics,
  runner audit, literature, prereg standards); recommendations + provenance in
  `development/planbench/planbench_wt_prereg_decisions.md`. RATIFY still unsigned.
- **DECIDED (Omer): run the WHOLE POOL, 500 per cell** — match the leaderboard corpus so
  every row shares a denominator with the published NT layer and the committed GPT-4 rows.
  This deletes the subsample apparatus outright (no seed, no strata, no id list, no
  t1-vs-t3 intersection problem; each task runs its own pool: t1 ids 2..501, t3 ids
  1..500), makes both silent subsampling hazards inert, and fixes the one under-powered
  prediction (exact McNemar 80%-power MDE on t3 +9.0pp → +6.0pp; power at WT t3 = 85%
  0.58 → 0.88). n=250 stratified survives only as the costed fallback. Cost is the binding
  constraint: t1 2×2 ≈$46 central (65% of the ~$70.6), six cells ≈$59 (84%), so §8 fixes a
  spend priority (t1 2×2 first, t3 second) and t3 is the only cell that drops to 250.
- **DECIDED (Omer): t2 stays excluded** — as a SCOPE decision. The 07-24 rationale
  ("optimal_plan tool unbuilt") is false: `classic_planner(strategy="astar_lmcut")` =
  `astar(lmcut())` is optimal search and ships (`solver_server.py:247,411`). The
  mystery-t2 option is closed, not deferred.
- **DECIDED (Omer): the model authors domain + problem + plan**; no PDDL injected in any
  cell, so the formalization-boundary metric uses the 24-bijection domain check alongside
  problem-level (objects, init, goal) set equality.
- **DECIDED (Omer): no runner-side spend cap.** The account is prepaid per experiment and
  never billed on real-time usage, so the loaded balance is the ceiling and the existing
  "credit balance too low" break is the stop. Consequences recorded: the calibration
  gate's projection determines what gets loaded (making §8 the real spend control), and
  balance exhaustion mid-cell yields a pre-declared censored cell, never a silent re-run.
- **Binding factual corrections carried into the prereg** (five false premises in the
  07-24 draft, two of which would have produced wrong numbers silently): the harness
  roster is pddl-solver + pddl-validator only (7 tools, no pddl-parser — which is now an
  analysis-time instrument); `response_evaluation.py` is NOT unmodified (three
  `apply_patches.py` robustness patches, the same build that graded the NT layer);
  `build_table.acc()` divides by 500 regardless of what was run (a stripped 250-instance
  replay reports a believable 22.2% where the truth is 44.4%); and
  `PDDL_COPILOT_RENDER_FROM_TOOLS` defaults to 1, which renders the t3 verdict from the
  last tool result and never reads the model's final message — i.e. the cell would have
  silently measured tool-verified, contradicting the D-J2 delivered-primary ruling.
- **Band rules rebuilt:** the 07-24 "CI midpoint" rule left 5 integer outcomes
  unclassifiable at each n and the Wilson midpoint is not the point estimate. Replaced
  with a four-outcome evidential partition (NO-RESCUE / PARTIAL / RESCUE / INCONCLUSIVE),
  cutpoints stated in counts. The clean-t1 "≥ 90%" band is struck as
  unattainable-by-instrument (the template extractor's measured ceiling is 94.4%, so a
  CI-backed 90 needs P(correct | extracted) ≥ 0.95) and demoted to an outcome-neutral
  apparatus criterion thresholded on the two decomposed quantities. Prediction (ii) gets
  per-branch mechanistic signatures, a joint falsifier, and a ±7.5pp equivalence margin
  (±5pp is not pre-registrable at any n we can afford).
- **Funnel placement (§4) = input boundary, corrected to a new LEADING BAR** in the
  with-tools cascade (NEED is a reference line in the ratified Figure-1 spec, so "upstream
  of NEED" was geometrically undefined). The CALL-extension alternative is rejected on
  measurement: 98.4% of `missing_required_arg` trials and 90.3% of invalid-PDDL-argument
  trials already PASS the CALL bar, and adopting it would move the published CALL bar by
  up to −53.2pp (0.8B) and flip the minimum-CALL model, contradicting `main.tex:685`.
  `formalization_match` is named as the metric (gold reference exactly reconstructible from
  the NL prompt, verified 500/500 both configs), with delegation rate as a companion
  mediator.
- **NT-layer red flag, pending re-report (does NOT touch the t1 headline):** the committed
  GPT-4 t3 corpus is a different corpus from ours (0/500 identical queries; verdict mix
  31.0% VALID vs our 64.8%), and the two models have opposite verdict biases, so a
  common-mix reweighting moves Haiku bw t3 78.2 → 83.1 and mystery 45.4 → 64.1 while GPT-4
  goes 94.6 → 90.3 and 73.6 → 83.7 — collapsing the mystery t3 gap from 28.2pp to 9.5pp.
  Finding 2 of `planbench_frontier_haiku_nt.md` is marked PENDING AUDIT; t1 is clean
  (same ids, 499/500 byte-identical prompts).
- **Prior-art calibration (verified 2026-07-25):** Göbel et al. (arXiv:2603.06064) ran
  **Haiku 4.5** with PDDL tools over MCP on 102 IPC Blocksworld instances and got
  63.7% → 66.7% (+3.0pp) at 5.7× token cost, because the tools exposed a step-wise
  simulator and the model retained the search; Huang & Zhang (ACL 2025) find formalizers
  robust to lexical perturbation. Architecture, not model tier, decides — which is why
  delegation rate is pre-registered as the mediator, and why the bare "tools rescue
  Mystery" claim is a replication (already published ≥4×) rather than a new phenomenon.

## 2026-07-26 — PlanBench WT prereg: SHAPE B (t1 2×2 only); prediction (iii) struck

- **DECIDED (Omer): shape B.** Four cells — {ordinary, Mystery} × {tools, matched-NT} on
  blocksworld t1 — at the whole 500-instance pool. ≈$46 central, ≈$52 with the
  pure-availability sensitivity arm and the calibration gate (73% of the ~$70.6). The t3
  verification pair is dropped and **prediction (iii) is STRUCK per the prereg's linkage
  rule** — reported as struck, not as unsupported. t3 was the cheapest cell to cut because
  its external comparability is already broken by the GPT-4 corpus mismatch (see the
  07-25 entry), and dropping it also removes the t3 endpoint-field choice, the verdict-mix
  stratification and the confusion-matrix requirement from the protocol.
- **Surviving confirmatory layer:** the two paired WT-vs-matched-NT t1 contrasts (clean,
  Mystery), Holm within family at α=0.05. Both are far from the power margin at the whole
  pool (mystery ≥0.95 against any WT rate ≥5%; clean ≥0.99 against any WT rate ≥60%).
  Predictions (i) and (ii) stand unchanged, including the four-outcome band partition and
  the two-branch mechanism test with its ±7.5pp equivalence margin.
- **Significance, stated honestly for the write-up:** this arm cannot move Act 4's
  headline (§1), and the bare "tools rescue Mystery" result is already published ≥4×. What
  it buys is (a) the matched-scaffold single ablation nobody has run on PlanBench —
  isolating tool availability rather than comparing different prompt shapes; (b) a
  measured answer to the live 3.8-14% vs 63-100% split in the literature, via the
  delegation-rate mediator; (c) the formalization-boundary metric, which separates
  "cannot plan" from "cannot translate"; and (d) accuracy-vs-dollars on the field's own
  instrument. Its real value to the paper is that it is the ONLY place the tools claim is
  tested on an instrument we did not build, which pre-empts the "you designed the
  benchmark your method wins on" objection for ≈$46.
- RATIFY still unsigned; no build or spend until it is.

## 2026-07-28 — PlanBench WT: RATIFY re-opened as a significance question, not a signature

- **State check (verified, not read off the handoff):** prereg work is merged to main
  (`53553a7`), nothing built (no `anthropic-tools`/`anthropic-scaffold` token in any code
  path), nothing spent, and the NT anchors reproduce exactly off
  `results/haiku-frontier/planbench/` (ordinary t1 205/500, Mystery t1 4/500).
- **The gate was mis-summarised.** §10 RATIFY is unsigned because Omer left an objection in
  it — "lets simplify and dig deeper here i either dont realy get the full picture or it
  just seems insignificant" — originally written at the scope slot. The shape-B commit
  answered "simplify" (t1 2×2, prediction (iii) struck) and relocated the text to RATIFY.
  The "insignificant" half was never answered.
- **Answered in** `development/planbench/planbench_wt_significance_brief.md`: one-page
  plain-language walkthrough, per-outcome value table, cost/off-ramp ladder, and three
  answer slots (go/no-go with A/B/C/D, balance to load, free unblocked NT work).
- **Significance verdict recorded, unhedged:** the direction of the effect is not worth
  paying for (published ≥4×, and Göbel et al. already ran this same model with PDDL tools
  over MCP for +3.0pp). Three things are: the matched single ablation ($8 of the $46), the
  delegation-rate + formalization-match split that separates cannot-plan from
  cannot-translate from did-not-call-the-tool, and the fact that this is the ONLY tools
  measurement in the paper taken on an instrument we did not build. Recommendation =
  ratify shape B; declining and publishing the design as pre-registered future work is
  stated as a legitimate outcome rather than a failure.

## 2026-07-30 — PlanBench citation verification + t3 audit (no spend, no build)

- **All seven citations verified at source** (arXiv IDs fetched, two read as local PDFs):
  Göbel 2603.06064, Huang & Zhang 2412.09879, La Malfa 2512.09629, LLMFP 2410.12112,
  CoPE 2510.05486, Valmeekam 2305.15771. No hallucinated references. Full record:
  `development/planbench/planbench_verification_20260730.md`.
- **The "already published >=4x" premise is TRUE for the direction** (Huang & Zhang n=100,
  CoPE n=100, LLMFP n=602, La Malfa n=30), so amendment J's "replication plus an ablation
  the field has not run" wording stays honest.
- **But no published work rescues Mystery by TOOL AVAILABILITY.** In LLMFP's own Table 2 the
  give-it-a-solver baselines score 0.0-0.3 on Mystery; only the full 4-component framework
  with repair loops reaches 77.7 (GPT-4o) / 98.0 (Claude 3.5 Sonnet). The one general-tool
  result on our exact model (Göbel, Haiku 4.5 + PDDL tools over MCP) is +3.0pp, and it
  finished ~19pp BELOW Fast Downward alone (66.7 vs 85.3 on 102 IPC instances). The WT arm
  measures the configuration our paper actually ships, and no cited paper predicts it.
- **HEADLINE DISCLOSURE OWED (new).** Act 4's "Haiku 41.0 beats GPT-4 31.4 CI-disjoint" is
  correct on the shared 500, but the *published* figure for that cell is 206/600 = 34.3%
  [30.6,38.2], from which 41.0 is NOT disjoint. Reconciles exactly on disk: 157/500
  (`blocksworld`) + 49/100 (`blocksworld_3`) = 206/600, same run partitioned, extra 100
  easier. Any disjointness sentence must name the shared-500 denominator.
- **Strengthener verdicts:** LLMFP-as-replication **DOWNGRADED** (their 41.5 is optimal-rate
  zero-shot, ours is VAL-validity one-shot; validity-equivalent is >=41.5 and unknown — cite
  as "consistent with", never "replicates"). Valmeekam Mystery comparator **HOLDS** at 26/600
  = 4.33% [2.97,6.27], disjoint above Haiku's 0.80% — but label it unpaired/cross-pool (no
  GPT-4 Mystery t1 corpus exists on disk). The 17/600 figure a web search returns is Table 2
  (PDDL prompts), the wrong condition.
- **t3 mix audit DONE, and the 07-25 memo overstated it.** Opposite response biases confirmed
  (Haiku mystery accuracy-given-VALID 25.9%; GPT-4 accuracy-given-INVALID 64.3%). The Mystery
  gap is not identified without a stated reference mix: 28.2pp unadjusted, 9.5pp at GPT-4's
  mix, 25.7pp at 50/50, 38.3pp at ours. Direction robust under all mixes; magnitude is not.
  Do not quote 9.5pp alone. NT doc finding 2 updated from PENDING AUDIT to resolved.
- **Effect on the WT go/no-go:** recommendation unchanged (option A, ratify shape B) and the
  case is stronger than before, because the published rescues all come from bespoke
  pipelines rather than tool access.

## 2026-07-30 — the PlanBench denominator gap (Omer's question) + a free paired test

- **Omer asked why we don't use the published denominator/instance set.** Verified answer: our
  `blocksworld` pool is **4-block (446) + 5-block (55)**; the never-run `blocksworld_3` pool is
  **every 3-block instance** (100). Content-disjoint, and together exactly the paper's 600
  ("3-5 blocks"). We ran the HARD two-thirds and skipped every easy instance — which is why
  GPT-4 scores 31.4% on ours and 49.0% on the skipped 100 (pooled = 206/600 = 34.3%).
- **Completing to 600 costs ≈$1.50** (200 NT trials) and fixes three things: the denominator
  footnote, the cross-pool Mystery comparator (`mystery_blocksworld_3` exists, structural
  rename verified 100/100), and it enables an exact PAIRED test on 600 since GPT-4 per-instance
  answers exist for both pools.
- **It also risks the headline, which is the honest reason to run it:** Haiku needs >=~50/100 of
  the 3-block instances for CI-disjointness at n=600 (GPT-4 got 49); below ~41 the beat
  disappears.
- **FREE WIN, already computed — use a paired test on the shared 500 instead of two independent
  Wilson CIs.** Exact McNemar: both correct 81, Haiku-only 124, GPT-4-only 76, neither 219;
  paired delta **+9.6pp, exact two-sided p = 0.00085**. Strictly stronger than the current
  CI-overlap argument and costs nothing.
- **New Slot 4 in the significance brief:** (A) NT to 600, WT stays 500 [recommended, ≈$1.50];
  (B) everything to 600 [≈$10.50, one denominator across Act 4]; (C) leave at 500 with the
  disclosure sentence [$0].

## 2026-07-30 — PlanBench WT arm RATIFIED (all four slots answered)

- **DECIDED (Omer): ratify shape B as designed.** Balance is **$170**, not the ~$70.6
  bookkeeping figure, so kill criterion (a) is no longer budget-binding at any pre-registered
  shape. Signature + amendments recorded in `planbench_wt_prereg.md` §10-R.
- **DECIDED (Omer): match apples to apples → amendment K, the pool is the published 600.**
  Our 500 was the hard two-thirds (4-block 446 + 5-block 55); `blocksworld_3` is every 3-block
  instance (100); union = the paper's 600, confirmed by 157/500 + 49/100 = 206/600 = 34.3%.
  All four cells at n=600. Bands recomputed: NO-RESCUE x<=19, PARTIAL 41..275, RESCUE x>=325,
  INCONCLUSIVE 70/601. Cost $55.02 for the 2x2, ~$62 all-in. Bare-NT layer owes 200 completion
  trials so NT and WT share one denominator.
- **Amendment L (anti-outcome-shopping):** the pool was frozen BEFORE Haiku's numbers on the
  extra 100 exist. At n=500 Haiku 41.0 is disjoint above GPT-4 31.4; at n=600 GPT-4 is 34.3 and
  Haiku needs >=~50/100 to stay disjoint. Choosing the denominator after seeing that is
  prohibited in either direction.
- **NEW FRAMING (Omer), and it conflicts with ratified §7:** "without tools we dont care if it
  beats gpt4. actually its better if he loses, then outperform him with tools." §7 as ratified
  forbids WT cells sharing a table or figure with GPT-4 rows, because GPT-4's rows are 2023,
  one-shot NL, different grader epoch — so "Haiku+tools beats GPT-4" conflates tool access with
  three years of model progress. **Proposed amendment M:** GPT-4 becomes a labelled published
  reference line at a stated epoch and denominator, never a comparator arm, with no
  significance test against it; the controlled contrast stays WT vs matched-NT. This licenses
  the bar-crossing narrative and also defuses the 07-30 headline exposure, since whether
  unaided Haiku clears the GPT-4 bar stops being load-bearing. **AWAITING one line from Omer.**

## 2026-07-30 — PlanBench WT amendment N: only the format clause is shared

- **Origin (Omer):** "the no tools is practically planbenches native prompt. we added tools
  so arm A must be different." That reframing located a real design error in the scaffold.
- **DECIDED: the NL→PDDL formalization step moves into the TOOLS policy**; the task-format
  clause is the only shared text. Supersedes the D-J3 "shared" definition, which named both.
- **Reason is bias direction, not elegance.** Formalizing has a purpose only when a planner
  will receive the PDDL. Shared, it hands the matched-NT arm an instruction it cannot satisfy
  (produce PDDL / entire answer must be the plan with nothing before it — and one sentence of
  preamble is MEASURED to make the extractor inject a duplicated action VAL rejects). Any
  compliance loss depresses arm B for a non-tool reason and INFLATES the WT−NT delta in our
  own favour — the exact failure mode §9-A was adopted to prevent.
- **Format clause stays shared** = it is the instrument, not the method; both arms must answer
  in a shape the extractor can read.
- **Declared:** arm A's system prompt is ~176 chars longer and that IS the treatment (package
  contrast). Arm B is NOT padded — filler to hit a character count is worse than a declared
  asymmetry.
- **Native prompt is not lost:** the bare-NT scaffold delta (§3, free, uses the graded 06-22
  layer) plus the pure-availability sensitivity arm (§9-A) give four rungs — native,
  scaffold-only, directive-only, scaffold+tools.
- **Rejected:** rewording "translate" → "work out internally" (phrasing patch for a
  classification error); dropping arm B (saves ≈$9, but confounds tool access with prompt
  shape — the same comparison the literature already makes — and discards the only unrun
  contribution).
- Frozen text + 8 machine checks in `planbench/engine.py:_pb_scaffold`; all pass,
  test_prompts 451/451.

## 2026-07-30 — PlanBench WT calibration gate: FIX APPARATUS AND RESTART ($1.09 spent)

- **Cost/throughput PASS, well under projection.** Tools arm $0.0254 (ordinary) / $0.0248
  (Mystery) per trial; p90 output tokens 4543 / 3887 (the gate's headline observable); turns
  4.55 / 5.20; loop_exhausted 0/80; delegation 100% (>= the 80% RESCUE requirement).
  **Caching ACTIVE — cache_read > 0 on 100% of tools trials**, so the ~5% margin over Haiku
  4.5's 4096-token minimum held; matched-NT caches 0% as §9-C predicted.
  **600/cell projection = $32.78 vs the prereg's $55.02, i.e. $22 under**, on a $170 balance.
- **GATE VERDICT: RESTART.** The outcome-neutral extraction check fails 2 of 4 cells, and §3
  makes that an apparatus-fix-and-restart event, never a scope decision. Do NOT launch the run.
  - **Defect 1 (Mystery tools, extraction 15%):** the model writes a complete plan in PDDL
    shorthand — `attack g` instead of the example's `attack object e ... from object c`.
    Trap 3's shorthand bullet; the frozen clause's "exactly the action wording of the example"
    did not prevent it because Mystery's vocabulary is already near-PDDL.
  - **Defect 2 (Mystery matched-NT):** 80% write narration before [PLAN] and in 65% the
    extractor parses actions out of that narration and emits MORE actions than the model listed.
    Corrupts the control arm, so it does not inflate our hypothesis, but it is noise.
- **NOT a defect — ordinary tools 50% empty extraction is a REAL formalization collapse.** All
  10 empties are the model correctly reporting "unsolvable" after classic_planner said so, and
  all 10 instances have PlanBench gold plans of 4-8 actions. Model-authored PDDL was wrong and
  the planner faithfully answered the wrong question. **Signal only — n=20, discarded set,
  non-standard pool, no VAL. Must not enter prose or influence design.** Recorded because it
  suggests the real Mystery/ordinary cells will be informative rather than a foregone
  confirmation, i.e. the §4 boundary metric has something to measure.
- **NEW BLOCKER for the results phase:** VAL cannot execute on this machine (wrong
  architecture) — any llm_correct right now is an artifact of the same class as the t2
  missing-FAST_DOWNWARD bug. Calibration is unaffected (cost/throughput only) but no graded
  number can exist until VAL works.
- **Also measured:** sequential wall-clock ~18s/tools-trial → ~12h for 2400 trials; worth
  adding concurrency before the real run.
- Full memo: `development/planbench/planbench_wt_calibration_20260730.md`.

## 2026-08-01 — PlanBench-WT restart closed: clause v2 frozen, amendment M accepted, sequential run

- **Amendment M ACCEPTED as worded (Omer):** GPT-4 may appear as a **labelled published
  reference line at a stated epoch and denominator** — never as a comparator arm, no
  significance test against it; the controlled contrast stays WT vs matched-NT within
  Haiku. Prereg §7 first bullet amended. Decided on journal-fitness grounds: showing the
  published bar with labels is the standard journal device; hiding it invites the
  "how does this relate to the published results?" objection. Licenses Omer's narrative
  (unaided Haiku below the GPT-4 bar, tool-equipped above) descriptively.
- **Format clause v2 FROZEN (Omer):** fixes both calibration extraction defects
  (word-for-word example phrasing incl. 'object'/'from'; answer must start with [PLAN]),
  plus one pre-freeze disambiguation ("phrased exactly as the example phrases its
  actions" — the "copying word for word" draft risked copy-the-example-PLAN, undetectable
  by the outcome-blind gate). Exact text quoted in prereg §10-R restart record 1.
- **Concurrency DECIDED sequential (Omer):** confirmatory run stays ~12 h overnight; the
  apparatus is exactly what the calibration measured.
- **VAL resolved at $0:** the 07-30 "cannot execute" blocker was a wrong path (Linux ELF);
  the NT layer's own Mach-O x86_64 build runs under Rosetta and passed positive+negative
  controls. Same grader epoch across NT and WT layers.
- Next: calibration re-run (~$1.10) → extraction ≥90% × 4 cells → Omer's scope-and-spend
  on the measured $32.78 → the 600/cell confirmatory run.

## 2026-08-03 — PlanBench-WT confirmatory RESULTS: RESCUE, both tests significant

- **Bottom line (pre-registered, n=600/cell, delivered endpoint):** clean NT 47.8
  [43.9,51.8] → clean WT **69.7** [65.9,73.2]; Mystery NT 0.0 [0.0,0.6] → Mystery WT
  **71.8** [68.1,75.3]. Paired exact McNemar + Holm: Mystery Δ+71.8pp (b=431/c=0,
  p=3.6e-130), clean Δ+21.8pp (b=206/c=75, p=2.7e-15). **Band verdict RESCUE**
  (431 ≥ 325); conjunctive ruling = SUPPORTED.
- **Mechanism: RESCUE branch provisionally met** — delegation 100%, |clean−Mystery WT|
  = 2.2pp (p=0.449, within ±7.5pp); formalization_match (§4) still owed to finalize.
- **The instrument biases ran against us and RESCUE survived them:** 125/569 delivered
  Mystery WT plans lost to residual PDDL-shorthand dialect (true rate ~90%+ under a
  tolerant parse); loop exhaustion 10.5%/5.2% counted as failures.
- **Two honest flags (ANSWER slots in the results memo):** clean-WT raw extraction
  72.7% decomposes to 7/443 instrument misses + 157 model-side (loop-exh + honest
  "unsolvable" empties on solvable instances — the formalization signal at scale);
  Mystery-NT narration-injection recurred (479/600) but collapse holds on the
  uninjected subset (0/121) and external anchors (bare-NT 0.8%, GPT-4 4.3%).
- **Reference-line context (amendment M):** tool-equipped Haiku (69.7/71.8) more than
  doubles the published GPT-4 clean bar (34.3, 2023 epoch); Mystery NT sits at 0.
- Cost: confirmatory $39.87; whole arm $42.09. Memo:
  `development/planbench/planbench_wt_results_20260803.md`.

## 2026-08-06 — WT arm closed out: mechanism final, ANSWER slots signed, NT denominator completed

- **formalization_match (§4) computed; RESCUE mechanism branch FINAL.** Mystery 97.8
  [96.3, 98.7] vs clean 96.3 [94.5, 97.6] — not CI-disjointly below, third requirement
  met; the rescue is formalize-then-delegate. Perfect gate: 0/35 no-match trials graded
  correct. Clean WT ceiling isolated to DOMAIN-authoring fidelity (P(solvable |
  domain-equivalent) = 99.5% vs 1.6%): the clean NL under-states physics (e.g. never
  says stacking clears the moved block) and Haiku transcribes what the text says;
  Mystery NL is a mechanical rendering, so 99.5% of Mystery domains come out equivalent.
- **Omer signed both ANSWER slots (accept + accept):** criterion (a) decomposes
  model-side (no apparatus restart); Mystery-NT 0/600 collapse is real (0/121
  uninjected + bare-NT 0.7% at n=600 + GPT-4 4.3%). Stripped-block regrade optional.
  **Paper prose on the WT arm is now unblocked** (still §7 rules + /verify-claims for
  every literature number).
- **Bare-NT completed to n=600 (amendment K debt, ~$1.5):** clean 263/600 = 43.8
  [39.9, 47.8] stays CI-disjoint above published GPT-4 206/600 = 34.3 [30.6, 38.2]
  (needed ~50/100 on the extra pool, got 58); Mystery 4/600 = 0.7%.
- **§9-A directive-only arm DONE ($2.61 measured):** Mystery t1 n=600, dangling
  directive + no tools = 3/600 = 0.5% [0.2, 1.5] — the pre-registered outcome-neutral
  prediction holds. Four-rung ladder final: native 0.7 / scaffold-only 0.0 /
  directive-only 0.5 / scaffold+tools 71.8. The +71.8pp contrast is tool
  availability, not prompt framing. (Run at full 600: the bullet's n=250 predates
  the whole-pool ANSWER; no committed draw exists.)

## 2026-08-06 — WT arm finale: stripped regrade finding, PR #93, paper plan APPROVED

- **Stripped-block regrade DONE ($0), reported as a finding:** block-only re-extraction
  of the 600 Mystery matched-NT trials gives 26/600 = **4.3 [3.0, 6.3]**, not the
  expected ~0 — narration injection had DEPRESSED the cell (26 valid block plans
  invalidated by scraped extra actions), so the instrument bias ran against the
  published 0.0, not in our favor. Paired contrast vs WT survives at p = 6.4e-112
  (b=412, c=7), under the signed slot's 1e-100 threshold; RESCUE untouched. Injection
  cross-check ties audit 2 exactly (479/600). Memo section appended to
  `planbench_wt_results_20260803.md`; paper reports BOTH layers.
- **PR #93 opened** (`planbench-wt-significance-brief` → main, 27 commits, code + docs,
  data stays laptop-local); Omer merges after review.
- **Paper integration plan APPROVED (Omer, all 4 slots):**
  `development/planbench/planbench_wt_paper_integration_plan.md`. Decisions: (1)
  placement = Option A, new self-contained section "External validity on PlanBench"
  between Results and Discussion NOW (lifts into Act 4 on the journal restructure);
  (2) amendment-N ladder table in the BODY; (3) two-layer NT presentation confirmed
  (graded 0.0 + injection caveat, stripped 4.3 as the instrument-robust reading);
  (4) overall approved, no amendments. Prose gated on PR #93 merge; lit numbers
  gated on /verify-claims (H&Z, GPT-4 Mystery 4.3, La Malfa, LLMFP, Göbel,
  Planetarium).

## 2026-08-06 — Act-4 literature numbers: /verify-claims pass COMPLETE (6/6 sources)

- Per-paper verification agents, full table in
  `development/planbench/planbench_wt_paper_integration_plan.md` §5. Verdicts:
  H&Z CONFIRMED (70/100 vs 0/100 Mystery, cite v4/ACL only); Valmeekam GPT-4
  Mystery Deceptive 26/600 = 4.3 CONFIRMED (one-shot, Table 2 A.3; clean 206/600
  doubly verified vs on-disk corpus); LLMFP CONFIRMED (602/task, but metric =
  optimal rate and GRADER UNDISCLOSED — say so in the amendment-M line);
  Planetarium CONFIRMED verbatim (cite NAACL v2); La Malfa PARTLY (+12/+15 hold,
  **pool "93" was WRONG** — real pools 3×50/task in v2; cite retitled v2); Göbel
  PARTLY (+3.0pp/102 IPC holds, **mechanism restated** — no planner tool in their
  roster, non-delegation was design not model choice).
- Consequence for prose: all six may enter tex with the §5 wordings; the frozen
  prereg's "La Malfa 93" is superseded by the table (prereg untouched).

## 2026-08-06 — PR #93 code review: two paper-relevant corrections logged, no rerun required

- **Deviation 1 corrected in `planbench_wt_results_20260803.md` (review finding, verified on the raw side-logs):** the 18 pause/resume re-attempts on clean-WT were NOT deterministic — 11/18 changed outcome at temp 0 (multi-turn tool loop), 8 graded correct on the second draw, and last-attempt grading makes those 18 instances best-of-2. **First-draw sensitivity: clean WT 418/600 = 69.7 → 410/600 = 68.3; paired Δ vs matched-NT +21.8 → +20.5pp (label fixed 2026-08-06 — this is the within-Haiku paired delta, not a GPT-4 contrast). No verdict changes** (CI vs GPT-4 still disjoint; Mystery/RESCUE untouched — the other three cells have exactly one record per instance). Bottom line for prose: wherever Act 4 cites clean WT 69.7 / Δ+21.8 (integration plan §tables line ~60, both handoffs), quote it with the first-draw sensitivity footnote, or quote 68.3 conservatively — Omer's call which; both are computed and logged in deviation 1.
- **Deviation 8 added (undeclared wire asymmetry, now declared):** the three prereg arms never sent the upstream `[STATEMENT]` stop sequence; the bare-NT arm did. Primary WT-vs-matched-NT contrast is symmetric (neither sends it); only ladder reads against bare-NT carry the extra wire diff, and it is measured-inert in the frozen corpora (0 post-`[PLAN END]` text in scaffold/directive). No prose change needed unless Act 4 compares bare-vs-scaffold as a controlled pair — then cite deviation 8.
- **Rerun verdict: NO paid rerun is required by any review fix or finding.** No fix touches a frozen prompt byte (new freeze test `tests/test_planbench_prompts.py` pins them), any grading code, or any wire-visible request parameter; all engine changes affect only failure paths that never fired in the frozen corpora, or what future side-logs record. Optional $0 local verifications only: (a) first-draw sensitivity (already computed, above); (b) VAL spot-check of a few of the 26 stripped-regrade flip IDs to settle the numeric coincidence with the published GPT-4 26/600 (ISS-026); (c) optional re-grade of the 58/100 bare-NT completion half under the v1 venv to demonstrate two-stack grader invariance (tarski already probed parse-equivalent).
- Review artifacts: corrected deviation row + new row 8 (results doc), CHANGELOG 2026-08-06 entry, ISS-025/ISS-026, freeze test, and the engine/build_table/apply_patches hardening — all uncommitted on `planbench-wt-significance-brief` for Omer's review.

## 2026-08-06 — Act-4 number decision: clean WT quoted FIRST-DRAW (conservative); $0 checks delegated

- **Omer resolved the deviation-1 fork: conservative.** "The 1 pt does not worth the ambiguity" — Act 4 quotes clean WT **410/600 = 68.3, paired Δ vs matched-NT +20.5pp** (first-draw: every instance single-shot, the 18 resume re-draws excluded). The last-attempt reading (69.7 / +21.8pp / p = 2.7e-15) lives only in the deviation-1 footnote, never as the quoted number. Mystery cells unchanged (one record per instance). Integration plan PB-B rewritten accordingly.
- Open numeric slots for PB-B: first-draw Wilson CI, exact McNemar b/c/p, and the clean-vs-Mystery paired delta under first-draw — recompute queued from the raw side-logs ($0 local, delegated). Until they land, PB-B cites counts only. *(Landed — see the 2026-08-07 entry below.)*
- **Optional $0 checks (b) and (c) approved and delegated** (to cheaper-tier Sonnet agents, per Omer): (b) VAL spot-check of the 26 stripped-regrade flip IDs + provenance audit of `stripped_block_regrade.py` against the GPT-4 26/600 anchor coincidence (ISS-026); (c) re-grade of the bare-NT completion half under the old py3.12/tarski-0.7.0 stack to demonstrate two-stack grader invariance.

## 2026-08-07 — $0 verification batch: all three checks GREEN, PB-B numeric slots filled

- **First-draw statistics (now the quoted Act-4 numbers, PB-B updated):** clean WT
  410/600 = **68.3 [64.5, 71.9]**; paired vs matched-NT Δ **+20.5pp**, exact McNemar
  b=202 / c=79, **p = 1.38e-13**; clean-vs-Mystery WT paired Δ = 3.5pp Mystery-above
  (b=119 / c=140, p = 0.214), within the ±7.5pp prereg margin (last-attempt 2.17pp,
  same direction). Independent script over the raw side-log; both anchors (410
  first-draw / 418 last-attempt) reproduced and the b/c shifts decompose exactly
  (of the 8 flips: 4 drop from b, 4 add to c; all 8 Mystery-correct). Mechanism
  fact: all 18 re-queried first draws were loop-exhausted empty answers, so
  "first-draw" is precisely "re-draws counted as failures" — no grading ambiguity.
- **Stripped-regrade coincidence ruled GENUINE (ISS-026 spot-check half done):**
  provenance audit found no anchor ingestion in `stripped_block_regrade.py`
  (unconditional sweep, 600 emergent from config ranges); 8/8 sampled flip IDs
  independently re-extracted and VAL-validated VALID. The 26/600-vs-GPT-4-26/600
  match is coincidence. Recorded in the results doc §stripped-block regrade.
- **Two-stack grader invariance DEMONSTRATED:** completion half (200 instances)
  re-graded under a rebuilt v1 stack (py3.12.12 + tarski 0.7.0 + setup.sh pins) —
  **200/200 per-instance verdicts identical** (clean 58/100, Mystery 0/100), zero
  parse failures. The two-stack split is provenance only; recorded in
  `planbench/requirements-wt.txt`.
- Net effect: every number PB-B quotes is now computed, verified, and logged.
  **ISS-026 CLOSED same day (Omer: "ok"):** analysis layer promoted to
  `planbench/analysis/` (×100 printf bug fixed) + full data archive committed at
  `results/planbench/wt-anthropic-20260801/` (graded cells, side-logs incl. the
  18 re-draw records, formalization rows, verification evidence, sha256
  MANIFEST); `verify_promotion.py` re-derives every published number data-only —
  all pass. Commit f7baca9 on `planbench-wt-significance-brief`; the review-fix
  edits remain uncommitted alongside for Omer's review.

## 2026-08-11 — Act 4 PlanBench section WRITTEN (Job 1 of the post-PR-93 batch)

- **PR #93 merged**, which was the only gate on prose. Remaining-work map written and
  answered by Omer (R1-R4 in `development/remaining_work_20260811.md`): PlanBench prose
  first, nt-ster ratified, Llama probe kept sequenced after nt-ster, the three $0
  Phase-0 items run alongside.
- **Section written on `paper/aaai27`, commit `67ea69c`:** "External Validity on
  PlanBench", new self-contained section between Results and Discussion (placement A as
  signed). Structure follows the approved integration plan exactly: instrument
  paragraph (Mystery = pure symbol rename, 501/501 verified on disk), headline NT
  table, secondary WT 2x2 table, ladder table in the BODY, mechanism paragraph,
  cascade/FORMALIZE paragraph, audits, scope + cost.
- **Every number quoted is the signed one.** Clean WT is the FIRST-DRAW reading 68.3
  [64.5, 71.9], Δ+20.5pp, b=202/c=79, p=1.4e-13; the last-attempt reading does not
  appear anywhere in the tex. Independent re-derivation of all nine Wilson intervals
  from their counts reproduced the results-doc values exactly (including the GPT-4
  Mystery CI [3.0, 6.3] from the published 26/600, computed by our own method as the
  clean 206/600 line already was).
- **Amendment M/I rules honored in the prose:** GPT-4 appears only in the NT table as a
  labelled published reference line with pool size and grader epoch on the same line,
  described as CI-separated with no test run against it; no WT cell shares a table with
  it. The novelty sentence is the replication-with-ablation framing, naming the
  matched-scaffold control and the directive-only rung as what the field has not run.
- **Companion edits in the same commit:** Related Work now anchors Huang and Zhang as
  the published rescue result (70/100 vs 0/100, n=100, VAL) and adds La Malfa et al.
  arXiv:2512.09629 as the closest agentic system, citing the retitled v2 with the
  corrected 3x50/task pool and an author list verified at the arXiv source; Positioning
  drops the "PlanBench is out of scope" sentence; Future Work now points at the
  delivered section and keeps the second-tier and open-roster runs as the open items.
- Compile is clean (0 undefined references, 0 overfull boxes, 19 pages). Overleaf was
  pulled before the edit and had no coauthor changes (bridge head `c8c8245`).
  **Not yet pushed** to origin or Overleaf, pending Omer's go-ahead.
- **nt-ster H4 prereg RATIFIED** the same day (all four §10 lines) with the corrected
  price for the accepted shape: ~46 GPU-h off + ~110-150 on, against the memo's
  obsolete ~92. Submit stays gated on readiness items 7/9/10/14 plus a ping and VPN.

## 2026-08-17 — ISS-024(b) audit numbers corrected after PR-94 review; what Limitations may say about `guided_json`

- **The verdict is unchanged: `guided_json` never bound.** It survives every cut of the
  data. What changed are the numbers quoted for it, after three defects in
  `tools/guided_json_audit.py` were found in review and fixed.
- **Quote the zero, not the percentage.** The headline for the paper is **0 of 58,581
  provable `validate_*` rows emitted JSON of any kind** across the two canonical corpora.
  It needs no denominator argument. The pooled rate (0.36% of 65,874 provable rows) is
  partly a task-mix figure, because `validate_*` is 82% of rows and its prompt never asks
  for JSON; it is a coverage number, not a measure of constraint strength.
- **Conservative bound available on request:** 1.92% on the 12,176 rows stored in full.
  That subset is length-biased upward (short JSON is disproportionately conformant), so it
  is a bound and not an estimate. Whichever cut a reviewer prefers, conformance is under 2%.
- **Superseded:** ~~526 of 88,781 decidable rows (0.59%)~~ — that figure pooled three trees,
  double-counted the four `decoupled-rollup` cells that are byte-identical copies of their
  sweep5v2 baseline, and applied one snapshot cap to a tree holding cells at two caps.
- **The decoupled control is never pooled with the canonical corpora** (corpus-identity
  rule). It is a different generation apparatus; it gets its own line, 174/16,448 (1.06%).
- **Sharpest framing for the Limitations sentence:** the `solve` and `simulate` prompts
  instruct the model to conform to "the JSON schema provided by the format constraint"
  (`prompts.py:114,138`) while no constraint ever reached the server. The `validate_*`
  prompts never mention JSON, which is why they sit at exactly 0.0%.
- **Do NOT write that the validation results are unaffected.** Measured: no validation row
  is *mis-graded* (`format_parse_fail` 0.0%, the `VERDICT:` trailer plus the regex fallback
  carry every row). Not measured, and not inferable from these corpora: what a constraint
  that actually bound would have generated. The counterfactual is unavailable.
- **Withdrawn:** ~~the decoupled budget fix shrank `format_parse_fail` exposure on both
  `solve` and `simulate`~~. Against the roster-matched 4-cell baseline it reads solve
  5.9%→3.2% and simulate 13.8%→**20.0%**; simulate got worse. The original reading compared
  4 Qwens at think=on against a 5-model both-modes pool, so it was composition, not
  apparatus.
- **Also settled in PR 94:** "the delivery gap" is available as a term (nearest neighbour is
  the GAP metric of arXiv:2602.16943, same divergence shape in a safety setting; distinguish
  it if we ever cite that paper). "Availability Is Not Enough" is retired as a title. The
  memo's "227k trials" does not reproduce from disk; the counted two-corpus total is
  273,600, and the draft abstract must not pair that figure with "seven models" — it covers
  the five open-weight models only.

## 2026-08-20 — D-J6 answered: delivery demoted to OPTIONAL, scale figure fixed, all three titles rejected

- **The delivery gap is OPTIONAL, not the thesis (Omer).** *"Let's mark the delivery as
  optional and later we choose between a version where it's included and a version where
  it's not included. We need to decide on a non-confusing narrative. The delivery is not
  our main point in the paper."* Two variants are now written up in
  `title_abstract_candidates.md` §2 with an ANSWER slot: **N1** = invocation-propensity
  spine, delivery in Limitations only (recommended); **N2** = delivery kept but
  subordinate, with its own section.
- **The term question is deferred, not answered.** It only arises under N2. The collision
  verdict stands if delivery stays: "the delivery gap" is unclaimed, nearest neighbour is
  the GAP metric of arXiv:2602.16943.
- **All three title candidates REJECTED (Omer):** *"the title is misleading. it's
  over-focused on the recent changes rather than the actual field and conclusions we
  present."* A and C made DELIVER the thesis; B made the dual-surface grading instrument
  the thesis. Three replacements (D/E/F) are drafted around the field-level conclusion
  instead.
- **The paper's actual thesis is already in the tex** and it does not mention delivery:
  "the bottleneck throughout is invocation propensity, an unstable, model- and
  prompt-dependent behavior, separate from the model's capability or the tool's accuracy."
  Any title or abstract that does not lead with that is off-spine.
- **Reopened:** "Availability Is Not Enough" was retired for anchoring the CALL finding
  only and predating the DELIVER stage. If delivery leaves the thesis that rationale
  mostly dissolves, and anchoring the CALL finding becomes exactly right. Back on the
  table under N1.
- **Scale figure DECIDED (Omer): quote 273,600 and say five open-weight models.** Derives
  in one line for a reviewer: 5 models x 2 reasoning modes x 3 arms x 4,560 x 2 corpora.
  The frontier arm (6,080 Haiku + 10,640 Sonnet) gets its own sentence and is never folded
  in. "227k" is retired; correction markers are now at the head of
  `journal_decisions_memo.md` and `journal_narrative_proposal.md`, which is where the
  "227k-trial / 7-model" pairing entered the drafting chain.
- **Still open:** the N1/N2 call and the title choice, both with inline slots in
  `title_abstract_candidates.md` §2. The §3 draft abstract is bannered PENDING that call —
  it implements N2-with-delivery-as-climax, so under N1 it needs rewriting rather than
  renumbering.

## 2026-08-20 — "propensity" retired as a paper term (Omer)

- *"'Propensity' is a complex word. I don't like it."* Not a stray word:
  `paper/main.tex` uses it **15 times** (abstract, contributions, results, limitations,
  future work, conclusion), so this is a paper-wide rename, not a wording tweak.
- **Recommended replacement: "invocation rate."** Plain, and it maps exactly onto the
  quantity already measured (the `tool_selected` share), so the simpler word is also the
  more concrete one. Where a sentence needs the dispositional sense, spell it out rather
  than nominalise: "whether the model chooses to call the tool". Runners-up: "call rate"
  (shorter, slightly informal for a thesis term), "willingness to call" (most human, mildly
  anthropomorphic, awkward in "the willingness result").
- The term still has to carry the paper's key distinction, behavior versus capability
  ("this reflects how often the model calls the tool, not whether it can"), so any
  replacement must survive noun slots like "default X", "raise X", "the X result".
- **Not yet applied to the tex.** Paper edits belong on `paper/aaai27` per CLAUDE.md; the
  15 edits are queued with an ANSWER slot in `title_abstract_candidates.md` §2. The
  development docs on this branch are already switched over.
- Knock-on: title candidate F was rewritten to drop the word, and the N1 narrative is now
  "invocation spine" rather than "invocation-propensity spine".

## 2026-08-20 — D-J6 CLOSED: N1 spine, title D, "invocation rate"; abstract redrafted

- **Narrative = N1 (Omer).** The invocation spine. The paper asks when tool access helps an
  LLM planner and answers that it depends on the regime, and that what gates it is whether
  the model calls. **Delivery moves to Limitations**; dual-surface grading stays in Methods
  as how we measure honestly. Neither is a headline.
- **Title = D (Omer):** *"Invocation Is the Bottleneck: When Sound Planning Tools Help an
  LLM, and When They Do Not."* States the conclusion and scopes it in the same breath, so
  it makes no unscoped composition-failure claim. "Availability Is Not Enough" stays
  retired, having been offered again and passed over.
- **Term = "invocation rate" (Omer).** "Propensity" is retired paper-wide.
- **Abstract redrafted on the N1 spine** (`title_abstract_candidates.md` §3), paired with
  title D. Delivery is absent by design. The delivered-answer sentence names the
  dual-surface instrument in one clause without spending the abstract on it. The superseded
  delivery-as-climax draft is kept below it for the record.
- **Verification debt shrank.** Dropping the delivery gradient from the abstract removes
  one of the five numbers owed a `/verify-claims` pass. Four remain (8-11 unaided floor,
  66-73 lift, -67 availability harm, 21-to-94 steering), plus two the redraft newly
  promotes into the abstract: ">99 percent correct when it does call" and the "one of three
  models at 9B or larger" roster claim.
- **D-J1 may no longer bind.** It governed the first number being one-sided by construction,
  which was the delivery gradient. With delivery out of the abstract there is no gradient to
  constrain. Flagged for confirmation before the tex pass rather than assumed.
- **STILL BLOCKED: the 15 `paper/main.tex` propensity edits.** The word is decided but the
  branch go-ahead is not given. Paper edits belong on `paper/aaai27` behind the Overleaf
  pull-then-push protocol, so nothing in the tex has been touched.

## 2026-08-22 — nt-ster H4: off-mode PASSES land, on-mode arm was void and has been rerun

- **Three `think=off` H4 units are complete, valid and all PASS.** Qwen3.5:9B
  66.18 → 67.24 (Δ̂ −0.18 [−1.89, +1.52]), gemma4:26b-a4b 78.16 → 78.64
  (+0.52 [−0.95, +1.99]), qwen3.6:35b 78.33 → 78.20 (+1.34 [−0.40, +3.08]). Every
  ELIGIBLE task cell is EQUIVALENT, which is what §3.4 requires for a PASS. Realized
  MDE 6.47-6.74pp. Full readout: `ntster_h4_partial_readout_20260822.md`.
- **The matched-cell result is the one to quote.** The paper's +72pp
  (`main.tex:501`, 0.206 → 0.926) is specifically gemma `validate_plan` **with-tools,
  `think=off`** — measured, not assumed. Its mode- and model-matched no-tools control
  is now done: **Δ +0.63pp [−0.46, +1.73]**, ELIGIBLE, EQUIVALENT. The sentence worth
  +72pp with tools is worth six tenths of a point without them. That is the CALL-beat
  attribution closed in the matched cell, on the model that owns the effect.
- **Both `think=on` cells were void — apparatus failure, not a result.** 9,120/9,120
  (35b) and 3,822/3,824 (9B) rows carried an EMPTY `response` AND empty `thinking`,
  with `done_reason=stop`, no errors, and 12,960 tokens genuinely generated per row.
  Text was never stored, so it is unrecoverable.
- **Cause: §2.3(A) and §2.3(B) are incompatible when composed.** The decoupled two-call
  path was built for, and only ever validated under, `--reasoning-parser none`
  (`chat.py:422`, `CHANGELOG.md:512` DECISION B). §2.3(A) correctly ruled the override
  is not passed — reasoning about the *single-call* path, where reasoning and answer
  share one stream. In the two-call path they do not. `CHANGELOG.md:512`'s claim that
  the reconstruction is "parser-state-proof" was a code-reading argument and is now
  **empirically false**.
- **Controlled proof.** June's `decoupled-rollup` corpora, same models, same apparatus,
  parser OFF: 9B 8.8% empty / 68.4% success, 35b 4.1% empty / 82.0% success. August,
  parser ON: ~100% empty / 0% success. The flag is the only difference.
- **Parser-off does NOT re-manufacture the §2.3(A) `simulate` artifact on the decoupled
  path**, because the answer is generated in a separate call with the reasoning
  re-injected as prompt. June 35b decoupled parser-off: `format_parse_fail` 0.0% on all
  three validate tasks, 14.0% on simulate, simulate success 40.0%.
- **The 08-20 live-smoke gave a false PASS.** It asserted turn structure and token
  counters (`turns=2 think_tok=8192 answer_tok=4768 call2_prompt=2049 done=stop`) —
  every one of which is still true on a row containing no text. Standing lesson: a smoke
  must assert `len(response) > 0` on a non-trivial share of rows.
- **No corpus drift (§4 validity thread).** August neutral anchor vs canonical May
  sweep5v2, four tasks, `simulate` excluded: pooled Δ = +0.1 (9B) / +1.0 (gemma) /
  +0.2pp (35b), n=4,260 per side, all non-negative and inside the ~1pp half-width. The
  "August looks like it is regressing" read is not supported — the only zeros are the
  void cells.
- **Actions taken (Omer, 08-22).** Job 20392801 cancelled; both void on-mode cell dirs
  deleted on the cluster (local copies retained under `results/ntster-h4-live/` as the
  failure record for the appendix); on-mode arm resubmitted as **job 20489912** with
  `--reasoning-parser none`, same `--run-tag ntster-h4`, `--time 7-00:00:00`, pins
  re-verified at `6007032` / `5e4f9c0`. A resume into the old dirs would have skipped
  exactly the void keys and produced a "complete" empty cell — hence delete, not resume.
- **§4(b) "replicated attribution" clause is dropped for now**, exactly as
  pre-registered. The 2×2 factorial is `think=on` and needs the Qwens' on-mode nt legs,
  which were the void cells. The §5 PASS sentence stands without the clause.
- **Integration follows the pre-committed §5 cap** — caveat-only: the CALL beat plus
  Limitations in the body, everything else (per-task table, F gate, MDE, drift check,
  and an honest declaration of the on-mode apparatus failure) in an appendix. Promoting
  H4 to a larger body surface *because it passed* would be a post-hoc, outcome-contingent
  deviation from a ratified prereg. Not yet actioned — no tex has been touched.
- **Roster gap found and closed: 4B was steered-but-uncontrolled.** Omer asked why the
  H4 roster is 3 models and not all four Qwens. Measured the with-tools `think=off`
  steering effect the control exists to attribute: 0.8B **+0.0pp** pooled (no effect,
  so no control is owed), 4B **+6.9pp** pooled / **+9.6pp** `validate_plan`, 9B +2.5,
  gemma **+47.4** (+72.0 `validate_plan`), 35b **+14.8**. So 4B carried a steering
  effect **larger than 9B's, which was controlled** — an asymmetry not defensible on
  effect size. Also ruled out "too weak to test": at `think=off` both 0.8B and 4B have
  3/5 tasks inside the §3.3 ELIGIBLE band, the same as gemma and more than 35b (2/5).
  Submitted `Qwen3.5:4B` `think=off` as **job 20490174** (no `--reasoning-parser`, no
  `--decoupled-budget` — apparatus parity with the three completed off cells).
  **To be declared as a deviation:** the control roster was expanded after seeing
  results. It is conservative — under §3.4's intersection-union rule a fourth unit can
  only make the conjunctive equivalence claim harder to satisfy, never easier — but it
  must be stated plainly, in the same appendix paragraph as the on-mode apparatus
  failure. D6 (what a 4B FAIL would do to the claim) is pre-committed in the readout
  memo and still needs Omer's answer before that cell lands.

## 2026-08-29 — nt-ster H4 COMPLETE: all six units PASS, paper-level branch = PASS

- **The control is closed. All six units PASS**, and every one of the 8 ELIGIBLE task
  cells across those units is EQUIVALENT — the §3.4 condition for a PASS, with no
  exceptions to name. Paper-level branch = **§5 PASS**. Pooled Δ̂ by unit: 4B off
  **−3.03 [−4.83, −1.23]**, 9B off −0.18 [−1.89, +1.52], 9B on **+1.83 [−0.28, +3.94]**,
  gemma off +0.52 [−0.95, +1.99], 35b off +1.34 [−0.40, +3.08], 35b on **+0.49
  [−1.37, +2.35]**. Realized MDE 6.47–6.80pp. Full readout:
  `ntster_h4_final_readout_20260829.md`, which supersedes the 08-22 partial for every
  number.
- **H4 now holds in both think modes and across four models**, not just at `think=off`
  on three. The 08-22 INCONCLUSIVE branch is retired.
- **The matched-cell attribution is unchanged and is still the sentence to quote.** gemma
  `validate_plan` `think=off`: **+72.0pp with tools, +0.63pp [−0.46, +1.73] without**,
  ELIGIBLE and EQUIVALENT. The three original `think=off` numbers recomputed
  bit-identical to 08-22 from the frozen scripts.
- **The on-mode rerun is healthy and the 08-22 diagnosis is confirmed by prediction.**
  The parser-off fix was predicted from June's corpora to land at 8.8%/68.4% (9B) and
  4.1%/82.0% (35b) empty-response/success; August delivered **8.2%/69.1%** and
  **3.9%/82.5%**. Both within a point on both axes. Parser ON was 99.9%/0% and 100%/0%.
  The flag was the whole effect, as diagnosed.
- **Parser-off did NOT re-manufacture the §2.3(A) grading artifact on the decoupled
  path.** `format_parse_fail` is **0.0% on all three `validate_*` tasks in all four
  on-mode arms**; `solve` 1–13%; `simulate` 10.7–44.3% (June 35b parser-off was 14.0%, so
  the known level). `simulate` is UNINFORMATIVE in both on cells (F 32.0 / 19.0) and never
  reaches a verdict. The 08-22 mechanism argument is now confirmed on independent data.
- **Unplanned benefit: §4(b)'s parser mismatch is gone.** §2.3(A) had budgeted for the
  factorial acquiring a parser difference across its nt/wt axis. The void-and-rerun forced
  the nt on-mode legs to parser-off, which is what iss024d already used, so **both legs now
  share the parser setting**. Still budget-unmatchable, still attribution-only, but one of
  two named confounds removed by accident.
- **4B PASSES, so D6 is moot** (it asked what a 4B FAIL would do to the claim). Two things
  reported honestly anyway: 4B is the only unit whose pooled CI excludes zero **and the
  sign is negative** — the directive makes 4B slightly *worse* without tools, which runs
  against the "merely a better prompt" objection rather than toward it; and 4B `simulate`
  is the family's only NOT-EQUIVALENT task cell (−14.00 [−19.97, −8.03]), but it is
  UNINFORMATIVE (own F = 12.0pp) so by §3.2/§3.4 it cannot contribute a FAIL and carries
  no verdict authority. Branch is PASS, not MIXED.
- **Mechanism decomposition VOID in all six cells** (APPARATUS 13.8–36.0% per arm vs a 1%
  threshold). Verdicts unaffected — §3.7 never gates a verdict, and labels are owed only
  on FAIL cells. M1 directive echo +0.00pp everywhere. The `M2 mean completion tokens =
  nan` cosmetic bug from 08-22 is still there.
- **No corpus drift, now including 4B.** August neutral anchor vs canonical May sweep5v2,
  four tasks, `simulate` excluded: pooled +0.2 (4B) / +0.1 (9B) / +1.0 (gemma) / +0.2pp
  (35b), n = 4,260 per side. All non-negative, all inside the ~1pp half-width.
- **Still owed before any tex is touched** (all four logged with `> ANSWER:` slots in the
  final readout §7): **O1** write the two deviation declarations — roster expanded 3→4
  after seeing results, and the on-mode `--reasoning-parser none` deviation from §2.3(A);
  **O2** decide whether §2.3(A) itself gets amended (08-22's D5); **O3** decide whether to
  write+freeze the §4(b) factorial script now that it is unblocked — this is what decides
  whether §5's PASS sentence keeps its "replicated attribution" clause, and the recommended
  route is freeze-and-hash *before* pointing it at data, the way items 9/10 were done;
  **O4** schedule the §5 integration under the pre-committed caveat-only cap.
  **No tex has been touched.**

## 2026-08-29 — O1-O4 answered OK; §4(b) factorial run after freeze, clause DROPS

- **All four open items accepted by Omer.** O1/O2 are written, O3 executed under the
  freeze protocol, O4 approved as scope with the tex itself deferred.
- **O1 — both deviations declared** as appendix-ready prose in `ntster_h4_prereg.md`
  §9.1: the roster expansion 3→4 after interim results, and the on-mode
  `--reasoning-parser none` rerun. Written so a reader sees what changed, when, relative
  to what knowledge, and which way it pushes the conclusion. The roster point is argued
  in checkable form — intersection-union means a fourth unit can only make the
  conjunctive claim harder — and notes the added unit was chosen by the size of the
  effect needing attribution, not by its control result, which was unknown at submit.
- **O2 — §2.3(A) amended** inline in the prereg: scoped to the single-call path, with the
  decoupled path requiring parser-off. Also marks the "Cost, stated" paragraph **void in
  fact** (the nt/wt parser difference no longer exists), records `CHANGELOG.md:512`'s
  "parser-state-proof" claim as empirically false, and adds a standing rule that a
  readiness smoke must assert `len(response) > 0`.
- **O3 — `tools/ntster_factorial.py` written, frozen at `78787eb7…11629164`**, hash
  recorded in the prereg §8 item 9 addendum, freeze committed **before** the first real
  invocation so the ordering is checkable in git rather than asserted. Rehearsed
  pre-freeze with both leg paths pointed at one directory, forcing the interaction to
  exactly zero by construction — exercises every code path against a known answer while
  leaking nothing. The addendum states plainly that the code was written after the H4
  verdict was known and why (until the on-mode rerun landed, the factorial had no nt
  legs).
- **§4(b) RESULT: the "replicated attribution" clause DROPS**, as pre-registered.
  9B interaction **+0.83 [−1.98, +3.64]**, 35b **−0.00 [−2.21, +2.21]** — neither
  excludes zero. §5's PASS sentence loses its optional bracketed clause; it is removed,
  not rewritten.
- **This is a null on an underpowered diagnostic, NOT evidence against the attribution**,
  and the write-up says so with the three structural reasons: gemma — the model that owns
  the +72pp — **cannot be in this factorial at all** (§2.3(B), no `think=on` nt leg,
  because the decoupled mechanism stops on `</think>` and gemma has no think tokens); the
  factorial is `think=on`, where the two eligible Qwens steer by only +3.97 and +1.27pp
  with tools, far too little to resolve an interaction at a ±2–3pp half-width; and the
  comparison was already declared attribution-only and budget-unmatchable.
- **Reported in both directions, honestly.** Under **domain** clustering both point
  estimates are positive and 35b's excludes zero (+1.71 [+0.03, +3.39]) — a less
  conservative clustering would have returned KEEP for 35b. The governing interval is the
  **wider** of the two clusterings per §3.3, so we take DROP. And on `validate_plan` the
  interaction is positive and excludes zero in both models (9B +7.33 [+3.92, +10.74], 35b
  +2.77 [+0.08, +5.46]) — recorded because suppressing it would be selective, but it
  carries no clause authority since §4(b) states the estimand per model.
- **No consequence for the paper beyond the clause.** The CALL-beat attribution never
  rested on the factorial; it rests on the matched cell — gemma `validate_plan`
  `think=off`, **+72.0pp with tools vs +0.63pp [−0.46, +1.73] without** — which is
  stronger and sits on the model and cell where the effect actually lives.
- **O4 — integration scope approved** (caveat-only cap: CALL beat + Limitations in body;
  per-task table, F gate, MDE, drift check, apparatus-failure declaration and the two
  §9.1 deviations in an appendix). **Tex deferred to a later session. No tex touched.**
