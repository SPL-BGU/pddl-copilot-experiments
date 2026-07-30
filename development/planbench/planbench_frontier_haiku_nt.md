# PlanBench frontier — Haiku 4.5 no-tools, graded (2026-07-23)

**What:** the Haiku 4.5 NT responses on disk since 06-22
(`results/haiku-frontier/planbench/<cfg>/pddl_copilot__anthropic__claude-haiku-4-5/`,
tasks t1/t2/t3/t7, blocksworld + mystery_blocksworld n=500, logistics n=285) are
now FULLY graded and verified. This closes the "grading needs Linux VAL" item in
`roadmap_eval_and_paper_completion.md` (D3 track) with zero cluster/VPN use.

## Status correction vs the roadmap

The roadmap said the responses were ungraded. In fact t1/t3/t7 were already
graded at generation time (06-22, locally); only **t2 was silently mis-graded to
0.0% across all three domains by a missing-dependency artifact** (below). t3 was
graded all along under `llm_correct_binary` (an earlier quick check that looked
for `llm_correct` misread it as ungraded).

## The t2 artifact — root cause and fix

`Executor.get_plan` (`plan-bench/Executor/__init__.py:360-392`) shells out to
`$FAST_DOWNWARD/fast-downward.py` to compute the optimal cost, and on any failure
returns cost 0. The 06-22 grading environment had VAL but no `FAST_DOWNWARD`, so
`plan_executor.cost = 0` for every instance and the optimality comparison
`actual_cost_llm == plan_executor.cost` failed universally: **every t2 instance
graded False regardless of the plan.** VAL-based t1 grading was unaffected
(verified: 4/4 spot-checked t1 gradings reproduce under a fresh local VAL run).

Fix: re-ran the upstream evaluator unmodified
(`response_evaluation.py --task t2 --ignore_existing`) with
`VAL=<repo>/planner_tools/VAL/bin/MacOSExecutables` (the x86_64 Mac build runs
under Rosetta; no Docker needed) and
`FAST_DOWNWARD=<pddl-solver plugin venv>/up_fast_downward/downward`. Spot-checks:
instance 4 (valid, cost 10 = optimal 10) flips to correct; instance 11 (valid,
cost 8 vs optimal 6) correctly stays wrong. Corrected files copied back into
`results/haiku-frontier/planbench/`; the pre-fix gradings remain in git history
(`d1045a5`).

## Corrected table (accuracy %, Wilson 95% CI; correct/TOTAL denominator, no
dropped instances — every instance carries a grading field)

| config | task | Haiku 4.5 NT | GPT-4 (committed) | Qwen3.6-35B (v1) |
|---|---|---|---|---|
| blocksworld | t1 plan generation | **41.0 [36.8, 45.4]** | 31.4 [27.5, 35.6] | 35.8 |
| blocksworld | t2 optimality | 28.2 [24.4, 32.3] | 28.4 [24.6, 32.5] | 37.6 |
| blocksworld | t3 verification | 78.2 [74.4, 81.6] | **94.6 [92.3, 96.3]** | 88.4 |
| blocksworld | t7 execution | 0.0 [0.0, 0.8] | 28.4 [24.6, 32.5] | (excluded) |
| mystery_bw | t1 | 0.8 [0.3, 2.0] | (not in canonical) | (not graded) |
| mystery_bw | t2 | 0.4 [0.1, 1.4] | (not in canonical) | (not graded) |
| mystery_bw | t3 | 45.4 [41.1, 49.8] | 73.6 [69.6, 77.3] | (not graded) |
| mystery_bw | t7 | 0.0 [0.0, 0.8] | (not in canonical) | (excluded) |
| logistics | t1 | 6.7 [4.3, 10.2] | (none committed) | 16.1 |
| logistics | t2 | 2.8 [1.4, 5.4] | (none committed) | 3.9 |
| logistics | t3 | 78.9 [73.8, 83.3] | (none committed) | 71.2 |
| logistics | t7 | 0.0 [0.0, 1.3] | (none committed) | (excluded) |

Qwen v1 column from `planbench_v1_results.md` (same harness, graded 2026-06).
The v1 prompt-parity caveat carries over: our prompts differ from the committed
GPT-4 prompts by one extra blocksworld domain-rule sentence, and grading-epoch
VAL drift is possible; treat close calls (within ~5pp) as near-parity.

## Findings

1. **Haiku beats GPT-4 on blocksworld plan generation, CI-disjoint** (41.0
   [36.8, 45.4] vs 31.4 [27.5, 35.6]). On optimality the two are statistically
   identical (141 vs 142 of 500). A 2026 small frontier model clears the
   PlanBench GPT-4 bar on the generation tasks, consistent with the v1 finding
   that Qwen3.6-35B already matched it.
2. **PENDING AUDIT 2026-07-25 — this finding is mix-confounded as stated; do not write
   paper prose from it until re-reported.** The committed GPT-4 t3 corpus is a
   *different* corpus, not our prompts: 0/500 identical queries, identical gold verdict
   text on 119/500, and an inverted verdict mix (GPT-4 155 VALID / 345 INVALID = 31.0%
   VALID vs our 324/176 = 64.8%). The two models have opposite verdict biases, so
   post-stratifying to a common mix moves Haiku bw t3 78.2 → 83.1 and mystery 45.4 →
   64.1 (GPT-4 the other way: 94.6 → 90.3, 73.6 → 83.7), collapsing the mystery t3 gap
   from 28.2pp to 9.5pp. Fix = re-report t3 with per-verdict rates and a stated mix.
   **t1 is unaffected and clean** (same 500 ids, same one-shot example 500/500, 499/500
   byte-identical queries after removing our one extra domain-rule sentence), which is
   what carries the headline. Full evidence:
   `development/planbench/planbench_wt_prereg_decisions.md` §5.
   Original wording: **Verification does not follow: Haiku t3 sits clearly below GPT-4**
   (78.2 vs 94.6, CI-disjoint) and below Qwen3.6-35B (88.4). Within Haiku the ordering
   still matches our suite (verification 78 > generation 41), but across models
   the generation and verification orderings invert. Consistent with our
   frontier suite result that Haiku's validation is mid-ladder (validate_problem
   ~50% unaided) while its generation is strong for its tier.
3. **The Mystery-Blocksworld collapse replicates on a 2026 model:** t1 41.0 →
   0.8 and t2 28.2 → 0.4 under semantic obfuscation, with extraction intact
   (494/500 t2 plans extracted; only 2 valid). Verification degrades but
   survives (78.2 → 45.4). This is PlanBench's commonsense-grounding result, not
   memorization-vs-clean-symbols; it complements (does not contradict) our
   structure-preserving anonymization null, and gives the paper's two-probe
   contamination story a frontier data point on the field's own instrument.
4. **t7 (plan execution) 0.0 is a format artifact for chat models, and GPT-4's
   28.4 on the same grader sharpens it.** The grader exact-matches a compact
   state encoding; Haiku answers in verbose natural-language state descriptions,
   so it scores 0 where completion-era GPT-4, which mirrors the prompt's
   encoding, scored 28.4. Same disease as v1's excluded t7 cells, and direct
   evidence for the "completion-era exact-match grading understates chat models"
   claim in the journal narrative (Act 4). We do not modify their grader; the
   cell is reported with this caveat and excluded from headline comparisons.
5. **t2 answer-to-grade funnel (blocksworld):** 500 → 491 answer with a [PLAN]
   block → 442 extract (Haiku sometimes writes shorthand action names, e.g.
   "unstack red from blue", which the template extractor drops) → 175 VAL-valid
   → 141 optimal. Extraction costs ~10% of answers; validity, not optimality, is
   the dominant filter (81% of valid plans are optimal). Logistics extraction
   uses a different parser and is not [PLAN]-marker-bound (69 literal markers,
   275 extracted).

## Repro

```bash
# deps: venv with tarski pyyaml openai numpy; stub transformers (eval path never uses it)
cd external/LLMs-Planning/plan-bench
VAL=$PWD/../planner_tools/VAL/bin/MacOSExecutables \
FAST_DOWNWARD=/Users/omereliyahu/personal/pddl-copilot/plugins/pddl-solver/.venv/lib/python3.14/site-packages/up_fast_downward/downward \
python response_evaluation.py --task t2 --config <blocksworld|mystery_blocksworld|logistics> \
  --engine pddl_copilot__anthropic__claude-haiku-4-5 --ignore_existing
```

Accuracy recompute: see the table script in this doc's commit, or
`planbench/build_table.py` over a canonicalized tree (denominator rule: this
corpus triggers no missing-field drops).

## Next on the PlanBench line (D3, in order)

> **SUPERSEDED — the numbered list below is history. Do not plan from it.**
> Superseded 2026-07-24 by the accepted D-J3 ruling
> (`development/journal_decisions_memo.md` §4), then narrowed 07-26 to ratified
> shape B. **Live design lives in one place:**
> `development/planbench/planbench_wt_prereg.md`, with the open go/no-go in
> `development/planbench/planbench_wt_significance_brief.md`.
> Deltas vs the list below: the WT arm is Haiku-only against a NEW
> matched-scaffold no-tools control (the bare-NT rows graded in this doc become
> the published-apparatus replication layer and carry Act 4's HEADLINE claim; WT
> is explicitly secondary); four cells on t1 at the **whole 500-instance pool**
> (the earlier "bw t1 > mystery t1 > bw t3, n≈200-250/cell subsampling" line is
> deleted, not amended — t3 is out, prediction (iii) is struck, and there is no
> subsampling on the ratified path); item 2 (open-roster arm) is demoted to
> pre-registered Future Work (its two blockers turned out already fixed in
> `2a1298c`); item 3 (Sonnet NT) is out of budget and dropped.

1. **WT backend** — adapter over `frontier_runner.py` driving the MCP tool loop
   for Haiku/Sonnet (~a day of dev + spend from the ~$70.6 API remainder).
   Pre-register the Act-4 predictions BEFORE the sweep (mirrors the iss024d
   prereg): tools convert failure→success where need+call+deliver clear; losses
   concentrate in formalization + long-output transcription; no-tools ordering
   replicates.
2. **Open-roster v2 tools arm** (cluster; the two recorded blockers —
   build_table denominator, empty-response crash — must be fixed pre-launch per
   `PLANBENCH_HANDOFF_v3.md`).
3. Optional cheap add: Sonnet NT generation for a second frontier tier on the
   same instrument.
