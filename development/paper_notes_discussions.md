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
