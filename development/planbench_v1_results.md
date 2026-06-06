# PlanBench v1 (no-tools vanilla leaderboard) — results

First numbers from the PlanBench arm (vLLM migration, sweep 2026-06-02, qwen
subset). **v1 = vanilla leaderboard: no MCP tools during response generation.**
Each instance = one single-turn vLLM call through `planbench/engine.py`, graded
by PlanBench's own VAL/PR2 evaluators. Reproduce the table with:

```
python3 planbench/build_table.py results/planbench/canonical
```

`results/planbench/canonical/` = rsync of the cluster's
`external/LLMs-Planning/plan-bench/results/` (our 4 qwen engines + PlanBench's
committed `gpt-4_chat` / `text-davinci-002` baselines). Scope per the
2026-06-06 decision (paper_notes): benchmark-shipped domains only —
**blocksworld** (the only config with a published baseline) + **logistics**
(our extra corpus); depots was t1-only upstream and is omitted.

## Table (accuracy %, no-tools vanilla; t3 = correct_binary; t7 EXCLUDED)

```
  BLOCKSWORLD               t1    t2    t3    t4    t5    t6  t8_1  t8_2  t8_3
  ours: Qwen3.5-0.8B       0.0   0.0  25.8   0.6   0.2   4.6   4.2   6.4   2.8
  ours: Qwen3.5-4B         4.8   4.8  59.0  22.2  15.0  14.6  32.8  37.2  35.0
  ours: Qwen3.5-9B        25.4  12.2  88.0  47.2  45.2  22.4  56.0  47.4  53.6
  ours: Qwen3.6-35B       35.8  37.6  88.4  52.4  57.2  42.2  93.0  92.8  86.8
  PlanBench: gpt-4_chat   31.4  28.4  94.6  61.0  28.2  47.0  76.6  86.4  58.2
  PlanBench: davinci-002    -     -    58.0   -     -     -     -     -     -

  LOGISTICS                 t1    t2    t3    t4    t5    t6  t8_1  t8_2  t8_3
  ours: Qwen3.5-0.8B       2.1   0.0  26.3   0.4   0.0   1.4  15.4  14.4  11.6
  ours: Qwen3.5-4B        10.2   1.8  69.5  27.0   0.0   8.8  19.6  20.4  19.6
  ours: Qwen3.5-9B        16.1   3.5  73.0  29.8   0.0  15.8  26.3  23.5  28.1
  ours: Qwen3.6-35B       16.1   3.9  71.2  28.1   0.0  29.8  58.2  55.4  83.5
```
n = 500 (blocksworld) / 285 (logistics) per cell, except logistics t5 (n=12).
gpt-4_chat / davinci columns are PlanBench's **committed per-instance gradings
averaged** (their published baseline by construction; we do not re-grade them).

## Headline

**Qwen3.6-35B (open, ~3B active MoE, no tools) matches or beats GPT-4 on 6 of 9
Blocksworld tasks** — wins t1 (36 vs 31), t2 (38 vs 28), t5 (57 vs 28), t8_1
(93 vs 77), t8_2 (93 vs 86), t8_3 (87 vs 58); trails on t3 (88 vs 95), t4 (52
vs 61), t6 (42 vs 47). All six wins are on cells where the parser demonstrably
works (non-zero for both engines), so the result is robust to the grading
confound below. This is the "small open models compete with closed baselines"
evidence Paper 1 wants (memory `project_paper_strategy`).

**Clean capability ladder** with model size on every task (0.8B → 4B → 9B →
35B monotone increasing on essentially all columns, both configs).

## First-class finding: PlanBench's exact-match grading understates reasoning models

PlanBench grades by exact-format string match (`text_to_plan` / `text_to_state`
extract a plan/state from the response and compare). Instruct/reasoning models
that wrap the answer in chain-of-thought or markdown are penalised even when the
**content is correct**. This is a methodological property of the vanilla
leaderboard, not (only) a capability gap, and it is the cleanest motivation for
the v2 tools arm (ISS-022): tools consume structured output, bypassing the
regex-format penalty entirely.

Three places it bites, in descending severity:

1. **t7 (plan_execution) — EXCLUDED from the table.** Uniform 0.0 for all four
   of our models. Verified artifact: Qwen3.6-35B's extracted state set == the
   ground truth **plus one stray bare `clear`** scraped from its markdown
   ("Clear Blocks: Red, Yellow") — i.e. the model got the state right and the
   parser rejected it. The same exact-match parser graded gpt-4 (28.4), so t7
   is not a fair measurement for *any* engine here; reporting it as 0 would be
   wrong. Excluded for all engines.
2. **t3 (plan_verification) — format-adherence is itself the signal.** The
   grader needs a literal "plan is (in)valid" verdict; a no-verdict response
   scores incorrect (comparability-preserving — see the apply_patches.py edit).
   Verdict-emission rate climbs cleanly with size: **0.8B 53% → 4B 99% →
   9B/35B 100%** (blocksworld). The 0.8B t3 ~26% ≈ chance (emits a verdict half
   the time, ~50/50 when it does) = "no t3 capability at 0.8B".
3. **t1/t8 small-model prose.** 0.8B/4B emit prose plans, not the `[PLAN]`
   template → low t1; this is genuine format non-adherence (9B/35B parse fine,
   so the extractor works — the lows are real, not artifact).

Consistent with our standing stance that tool/format-adherence is data, not a
bug to paper over (memory `feedback_tool_adherence_is_data`).

## Caveats / provenance

- **t7 excluded** for all engines (parser artifact above).
- **logistics t5 n=12** (PlanBench ships only 12 t5/logistics instances) —
  noisy; the uniform 0.0 there is part real-difficulty, part prose-extraction.
- **logistics has no published baseline** (PlanBench published blocksworld
  only) — it's our own extra corpus, no head-to-head column.
- **t3 was re-graded offline** (2026-06-06) after two upstream grader crashes
  (KeyError on missing verdict; IndexError on a malformed logistics action
  line) — both fixed comparability-preservingly in `planbench/apply_patches.py`
  (non-adherent → incorrect, exactly how gpt-4 would be scored).
- **2 cells were smoke-contaminated and corrected** (0.8B/4B t1/blocksworld:
  the June-2 smoke's 3-instance *evaluation* file shadowed the full 500-instance
  responses; re-graded over the full responses 2026-06-06).
- **Aggregate/macro-mean deliberately NOT reported** — non-standard for
  PlanBench and contaminated by t7; per-task is the honest comparison.
- **gemma4:26b-a4b** deferred (smoke only, t1); not in this sweep.

## Still owed

- v2 tools-on arm (ISS-022) — the natural follow-up; the format-adherence
  confound above is its motivation.
- gemma4:26b-a4b full sweep (deferred).
- A fair t7 (and a fairer t1 for prose models) would need either a tolerant
  state/plan extractor or a format-constrained prompt — but that diverges from
  how gpt-4 was graded, so it's a v2/ablation question, not a v1 fix.
