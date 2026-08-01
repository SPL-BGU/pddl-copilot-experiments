# PlanBench-WT calibration gate — result (2026-07-30)

**Spent: $1.09 across 80 trials.** Budget was ≈$1.50.

**GATE VERDICT: FIX APPARATUS AND RESTART.** Cost and throughput pass comfortably; the
outcome-neutral extraction check **fails on 2 of 4 cells**, and prereg §3 makes that an
"apparatus-fix-and-restart event, never a scope decision". **The ≈$33 confirmatory run must
not be launched until the two instrument defects below are fixed and the calibration is
re-run.**

## Calibration set (disjoint, discarded)

20 clean + 20 Mystery, drawn from `blocksworld/generated` (content-disjoint from S: 0/602
hash overlap in both editions), block-matched to S (3/15/2 across 3/4/5 blocks vs S's
16.7% / 74.2% / 9.2%), whitespace-normalised into `instances/blocksworld/{,mystery/}calib_basic`
as `instance-1` (one-shot example, source id 134) plus `instance-2..21` (targets, source ids
4, 7, 10, 12, 14, 20, 22, 25, 34, 36, 37, 47, 54, 87, 93, 100, 107, 120, 128, 132).
Configs `blocksworld_calib` / `mystery_blocksworld_calib`; results under
`{responses,results}/{blocksworld,mystery_blocksworld}_calib/`. **Discarded — nothing here
may be cited.**

Three integration traps found and fixed while building it, all worth knowing for any future
pool: pool ids start at **2** because `instance-1` is the one-shot example; `pddl_to_text.py`
branches on whether `domain_name` *contains* `"blocksworld"` and silently yields an empty
object list behind a bare `except` otherwise (this was the whole `predicates[0]` IndexError);
and `patch_init`'s anchor no longer matches this tree, so `apply_patches.py main()` exits
before reaching later patches — run patch 6 directly.

## Cost and throughput — PASS

| cell | n | $/trial | out p50 | out p90 | turns | cache-read hit | loop_exhausted |
|---|---|---|---|---|---|---|---|
| ordinary / tools | 20 | $0.0254 | 2154 | **4543** | 4.55 | 100% | 0 |
| ordinary / matched-NT | 20 | $0.0011 | 64 | 77 | 1.00 | 0% | 0 |
| Mystery / tools | 20 | $0.0248 | 2278 | **3887** | 5.20 | 100% | 0 |
| Mystery / matched-NT | 20 | $0.0034 | 594 | 798 | 1.00 | 0% | 0 |

- **Headline observable (p90 output tokens): 4543 ordinary / 3887 Mystery** on the tools arm.
- **Caching verdict: ACTIVE.** `cache_read > 0` on **100%** of tools trials, clearing the
  ≥90% bar. The ~5% margin over Haiku 4.5's 4096-token minimum held. The matched-NT arm
  caches at 0% as predicted (§9-C) — its prefix is far below the minimum.
- **loop_exhausted: 0/80.** `MAX_TOOL_LOOPS`=10 is not binding.
- **Delegation rate: 100%** of tools trials called `classic_planner` (mean 3.55 / 4.20 tool
  calls). Comfortably above the §3 RESCUE-branch requirement of ≥80%.
- **Wall-clock, sequential, no concurrency:** ordinary tools 6m22s, Mystery tools 5m52s
  (~18s/trial); matched-NT ~34s and ~94s per cell. A 2400-trial run at 600/cell projects to
  **~12 h wall-clock**. Worth adding concurrency before the real run.

**Projection to the ratified 600/cell pool: $32.78** (ordinary tools $15.25 + Mystery tools
$14.87 + the two matched-NT cells $2.66), versus the prereg's $55.02 — **$22 under**. Against
the $170 balance this is not remotely budget-binding.

## Extraction — FAIL on 2 of 4 cells (the restart trigger)

| cell | extraction | preamble before [PLAN] | extractor emitted MORE actions than the model wrote |
|---|---|---|---|
| ordinary / tools | 50.0% | 100% | 0% |
| ordinary / matched-NT | 100% | 0% | 0% |
| Mystery / tools | **15.0%** | 25% | 0% |
| Mystery / matched-NT | 100% | 80% | **65%** |

Criterion is ≥90%. Two of these are instrument defects; one is not.

### Defect 1 — Mystery tools arm answers in PDDL shorthand (INSTRUMENT, must fix)

17/20 Mystery tools trials extracted to nothing, and **not** because the model failed the
task: it wrote a complete, well-formed plan block in the wrong dialect.

- example wording the extractor expects: `attack object e` / `overcome object e from object c`
- what the model wrote: `attack g` / `overcome g j`

It dropped the word `object` and the `from` connective — PDDL-ish shorthand. This is trap 3's
"shorthand action names extract to nothing", and the frozen format clause's "using exactly the
action wording of the in-context example" did **not** prevent it. The Mystery vocabulary is
already close enough to raw PDDL that shorthand is the natural collapse. **Fix: the format
clause must demand the example's full phrasing explicitly — the word `object` before every
argument and `from` where the example uses it, no abbreviation.**

### Defect 2 — Mystery matched-NT arm injects actions from its own narration (INSTRUMENT, must fix)

80% of Mystery matched-NT trials wrote narration before `[PLAN]`, and in **65%** the extractor
parsed action wording out of that narration and emitted MORE actions than the model actually
listed. This is trap 3's fourth bullet firing at scale. It corrupts arm B rather than arm A,
so it does not inflate our hypothesis — but it is noise on the control and must go. **Fix:
strengthen the clause so the answer's first characters are `[PLAN]`.**

### NOT a defect — the ordinary tools arm's 50%

All 10 empty extractions on the ordinary tools cell are the model **correctly reporting an
empty plan** after `classic_planner` told it the problem was unsolvable — and **all 10 of those
instances have PlanBench gold plans of 4-8 actions**, so they are solvable. The model authored
its own PDDL (model-authored per §10-O), mis-formalized it, and the planner faithfully answered
the wrong question. The extractor behaved correctly throughout (0% injection, and the other 10
extracted fine despite 100% preamble).

This is the §4 formalization-boundary mechanism appearing on its own, unprompted, at the first
opportunity. **It is a signal, not a result:** n=20, from a discarded calibration set, on a
non-standard instance pool, with no VAL grading. It must not enter prose or be cited, and it
must not influence the design. Recorded because it says the real cell is likely to be
informative rather than a foregone confirmation.

## Blocker for the results phase — VAL cannot execute here

`/Users/omereliyahu/personal/LLMs-Planning/planner_tools/VAL/validate` returns "cannot execute
binary file" on this machine (wrong architecture). Any `llm_correct` produced right now is an
artifact of the same class as the t2 missing-FAST_DOWNWARD bug, not a grade — the single
`False` produced during setup has been discarded. This does **not** block the calibration
(whose decision function reads cost and throughput only) but it **is** on the critical path:
no graded number can exist until a working VAL is available.

> **RESOLVED 2026-08-01 — wrong path, not a missing tool.** The binary tested above is a
> Linux x86-64 ELF (unrunnable on any Mac, Rosetta included). The build the graded NT layer
> already used — `external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate`,
> Mach-O x86_64 under Rosetta, per `planbench_frontier_haiku_nt.md:29,141` — runs on this
> machine and passed a negative and a positive control on 2026-08-01. Same grader epoch as
> the NT layer; set `VAL=<repo>/external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables`.
> Details in prereg §10-R "Restart record 1".

## Owed before the confirmatory run

1. Fix defects 1 and 2 in the format clause; Omer re-freezes the amended text.
2. Re-run the calibration (~$1.10) and confirm extraction ≥90% on all four cells.
3. Resolve VAL for this architecture.
4. Consider concurrency — 12 h sequential wall-clock at 600/cell.
5. Then Omer's scope-and-spend approval on the measured $32.78, and the run.
