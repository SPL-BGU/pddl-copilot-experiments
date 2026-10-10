# PlanBench re-analysis: the equivalence sentence and the plan extractor

*Written 2026-10-02. Local re-analysis only: no cluster, no API calls, no spend, no edit
to `paper/`, to the pinned PlanBench code, or to any tracked file. New code is under
`tools/reanalysis/`. Covers `weakness_consolidated.md` C9 ("One sentence recomputed"),
C15 and F2. This is a findings note. It proposes no tex wording and decides nothing.*

## What we found, and what it changes in the paper

**Starting point.** `planbench/analysis/verify_promotion.py` runs clean: ALL CHECKS PASS.
It reproduces 47.8 to 68.3 (287 and 410 of 600), +20.5 (b=202, c=79), and 71.8 (431 of
600). The other two figures are outside that script and were reproduced separately:
43.8 (205/500 + 58/100 = 263/600) and 4.3 (the pinned `stripped_block_regrade.py`, run
again today: 26/600).

**Question 1, the equivalence sentence (tex 1437-1439).**

1. The prereg asks for a paired equivalence test (TOST) on the with-tools gap between
   Blocksworld and Mystery. No such test was ever implemented. The pinned code compares
   the point estimate to 7.5 and prints a McNemar p-value. Both result-doc statements
   ("within the margin") and the tex sentence rest on the point estimate alone.
2. Run properly, on the reading the paper quotes (first-draw, 119 against 140): the gap
   is 3.5 points, 90% interval [-7.9, +0.9], TOST p = 0.068. **At plus/minus 7.5 the
   criterion is not met.** Five interval methods agree to the second decimal. The
   earlier Wald figure in F2 was right.
3. On the last-attempt reading (119 against 132) the criterion is met at 7.5 (p = 0.022).
   At plus/minus 10 it is met on both readings (p = 0.008 and 0.0015).
4. So "well inside the plus/minus 7.5 point margin" is true of the point estimate and
   not true of the test. The recorded RESCUE-branch verdict cites plus/minus 10 for its
   third requirement, and at 10 it holds on both readings. The prereg names two margins
   for this one quantity, so which one binds is a reading question for Omer (details in
   section 1.1).
5. Why a 3.5-point gap fails a 7.5-point margin: the two domains disagree on 43% of
   instances. The prereg planned for 18% and says 7.5 is only certifiable up to 33% (39%
   at n = 600). At the realised disagreement rate the test had about 75% power even if
   the true gap were zero.

**Question 2, the extractor (tex 1528-1547).**

6. A corrected extractor (new script, shipped one untouched) that reads only the model's
   final answer block and accepts PDDL shorthand gives:

   | cell (n = 600) | as shipped | corrected |
   |---|---|---|
   | Blocksworld, no tools | 47.8 [43.9, 51.8] | 47.8 [43.9, 51.8] |
   | Blocksworld, with tools (first-draw) | 68.3 [64.5, 71.9] | 70.2 [66.4, 73.7] |
   | Mystery, no tools | 0.0 [0.0, 0.6] | 4.3 [3.0, 6.3] |
   | Mystery, with tools | 71.8 [68.1, 75.3] | **94.3 [92.2, 95.9]** |

7. The paper's guess that a tolerant parser "would put that cell above 90%" is confirmed:
   566 of 600. All 125 plans that were thrown out for notation are valid plans.
8. The tools-against-no-tools contrasts get larger, not smaller: Blocksworld +22.3
   points (was +20.5), Mystery +90.0 (was +71.8). No trial anywhere moved from correct to
   incorrect.
9. **This changes Question 1.** With the extractor corrected, the with-tools gap between
   the two domains is no longer 3.5 points. It is **24.2 points in Mystery's favour**
   (28 against 173 discordant, 95% interval [-28.4, -20.0], McNemar p = 1e-26). The
   equivalence criterion is not met at 7.5 or at 10, on either reading. The near-tie in
   the shipped numbers exists because the notation loss removed about 21 points from
   the Mystery cell and almost nothing from the Blocksworld cell. "The renamed domain is
   no harder" survives as a direction. "The two are within a margin of each other" does
   not survive the correction.
10. This agrees with what the paper already reports elsewhere: the planner found a plan
    in 95.3% of Mystery trials and 69.7% of Blocksworld trials. The corrected delivered
    numbers (94.3 and 70.2 to 71.5) now sit right on those.
11. "501 instance files but 600 instances" is two directories. One holds 501 files (4 and
    5 blocks), the other 101 files (3 blocks). In each, file 1 is used only as the worked
    example, so 500 + 100 = 600 are asked. The "501" in the tex is the rename check on
    the first directory only. The check holds on all 602 files (section 2.6).

**Caveat that travels with every corrected number.** The corrected extractor is post hoc
and was not preregistered. The shipped numbers remain the preregistered "delivered"
endpoint, and the frozen prompt told the model to use the long English phrasing, so a
shorthand answer is a real instruction-following miss. The corrected numbers answer a
different question: did the final answer contain a valid plan in a readable notation.

---

## 1. The equivalence sentence

### 1.1 What the prereg defines

Source: `development/reference/planbench_wt_prereg.md`.

**The test and the two margins.** Lines 281-283 and 290-295:

> - **RESCUE branch** additionally requires: mystery `formalization_match` (§4) not
>   CI-disjointly below clean; delegation rate (share of trials calling
>   `classic_planner`) ≥ 80%; and paired |clean_WT − mystery_WT| within **±10pp**.

> - **Margin: ±7.5pp at the whole pool** (paired TOST at n=500 certifies it up to a total
>   discordance of ψ=0.33, comfortably above the plausible ψ=0.18, where the minimum
>   pre-registrable margin is 5.6pp); the fallback n=250 margin is **±10pp** (certifiable
>   up to ψ=0.29, power 0.96 at ψ=0.18). **±5pp is not pre-registrable on either path**
>   (it needs ψ ≤ 0.15 at n=500, and ~617 pairs at ψ=0.18), and the post-hoc CI
>   half-width must not be quoted as licence for it.

Line 441-443 (§6, analysis plan):

> Clean vs mystery within arm is **paired** (the correspondence check is recorded PASSED
> in §2, not contingent) and is exploratory/diagnostic, with the ±10pp equivalence test
> as pre-specified in §3(ii).

So:

- **Which test:** a paired TOST. The word appears once, in the Margin bullet. No alpha
  is stated. The usual convention (5% per side, which is the same as asking the 90%
  interval to sit inside the margin) is used below, and it matches the project's other
  TOST preregs (`iss024d_parity_prereg.md` L29 uses a 90% Newcombe interval).
- **Which margin:** the prereg carries two numbers for the same quantity. The RESCUE
  bullet and §6 say plus/minus 10. The Margin bullet says plus/minus 7.5 at the whole
  pool and plus/minus 10 only for the n = 250 fallback, which was not used. The history
  explains it: in `planbench_wt_prereg_decisions.md` L306 the margin was plus/minus 10
  and tied to n = 250 ("The ±10pp equivalence margin is what n supports"); the Margin
  bullet was tightened to 7.5 when the whole pool was adopted, and the RESCUE bullet and
  §6 kept the old figure. Both readings are defensible from the text. The results doc
  (L42-44) took 10 as the branch requirement and 7.5 as the stricter reference: "within
  the ±7.5pp margin, let alone the branch's ±10pp".
- **Which n:** the Margin bullet says n = 500 ("the whole pool" at the time). Amendment
  K (L650-671) changed the pool to 600 and says "The ±7.5pp equivalence margin is
  certifiable at n=600 wherever it was at n=500." So n = 600.
- **Which reading:** the prereg does not anticipate re-draws, but its exclusion table
  (§9-F, L543-551) does: "`loop_exhausted` → counted as failure, never retried (it is an
  outcome)" and "**Single-run rule:** each cell runs once to completion". All 18 re-drawn
  trials were loop-exhausted on the first draw, so first-draw is the reading that follows
  the prereg. The 08-06 decision (results doc deviation row 1) binds the paper to it:
  "Act 4 quotes the first-draw numbers (68.3 / +20.5pp) as primary". The same row states
  the gap as "3.5pp Mystery-above (b=119 / c=140, p = 0.214), within the ±7.5pp margin",
  which is a point-estimate statement.
- **Status of the test:** §6 calls the clean-against-Mystery comparison
  "exploratory/diagnostic". It is not one of the two confirmatory tests.

### 1.2 What the pinned code does

No TOST exists in `planbench/`. A search for "TOST" or "equivalence test" finds nothing.
Two places touch the margin:

- `planbench/analysis/analyze_confirmatory.py`, last block. It prints the absolute gap
  and an exact McNemar p-value under the heading "margin ±7.5pp reference". Run today
  (cwd = the upstream tree, see section 3), its output is:

  ```
  == Paired clean-vs-mystery WT delta (margin ±7.5pp reference) ==
  |clean_WT - mystery_WT| = 2.2pp (b=119, c=132, exact p=0.449)
  ```

  That is the last-attempt reading, with no interval and no test against the margin.
- `planbench/analysis/firstdraw_analysis.py` L273-276: `margin = 7.5`,
  `within = abs(d) <= margin`. A comparison of the point estimate with the margin. (Not
  re-run: its paths are the as-executed machine paths. Read only.)

A McNemar p-value tests whether the gap is zero. It cannot show that a gap is small.

### 1.3 The test, recomputed from the per-instance data

Script: `tools/reanalysis/planbench_equivalence_tost.py` (loads the cells through the
pinned `verify_promotion.py` loaders). Sign: Blocksworld minus Mystery. n = 600.

| reading | both | Blocksworld only (b) | Mystery only (c) | neither | gap | McNemar p |
|---|---|---|---|---|---|---|
| first-draw | 291 | 119 | 140 | 50 | -3.50 | 0.214 |
| last-attempt | 299 | 119 | 132 | 50 | -2.17 | 0.449 |

| reading | margin | method | 90% CI | TOST p | verdict |
|---|---|---|---|---|---|
| first-draw | ±7.5 | Wald paired | [-7.91, +0.91] | 0.068 | criterion not met |
| first-draw | ±7.5 | Tango score | [-7.90, +0.91] | 0.068 | criterion not met |
| first-draw | ±7.5 | Newcombe paired (method 10) | [-7.89, +0.91] | 0.067 | criterion not met |
| first-draw | ±7.5 | Bonett-Price | [-7.90, +0.92] | 0.067 | criterion not met |
| first-draw | ±7.5 | bootstrap over instances | [-8.00, +0.83] | 0.072 | criterion not met |
| first-draw | ±10 | Wald paired | [-7.91, +0.91] | 0.008 | criterion met |
| first-draw | ±10 | Tango score | [-7.90, +0.91] | 0.008 | criterion met |
| first-draw | ±10 | Newcombe paired | [-7.89, +0.91] | 0.007 | criterion met |
| first-draw | ±10 | Bonett-Price | [-7.90, +0.92] | 0.008 | criterion met |
| first-draw | ±10 | bootstrap over instances | [-8.00, +0.83] | 0.008 | criterion met |
| last-attempt | ±7.5 | Wald paired | [-6.51, +2.17] | 0.022 | criterion met |
| last-attempt | ±7.5 | Tango score | [-6.51, +2.18] | 0.022 | criterion met |
| last-attempt | ±7.5 | Newcombe paired | [-6.50, +2.17] | 0.021 | criterion met |
| last-attempt | ±7.5 | Bonett-Price | [-6.50, +2.18] | 0.022 | criterion met |
| last-attempt | ±7.5 | bootstrap over instances | [-6.50, +2.17] | 0.024 | criterion met |
| last-attempt | ±10 | all five methods | about [-6.5, +2.2] | 0.001 to 0.002 | criterion met |

The method does not matter here. Wald, a score method (Tango 1998), a Wilson-based
method (Newcombe 1998), an adjusted Wald (Bonett and Price 2012) and a bootstrap all
land within 0.1 point of each other. No exact unconditional test was run; with 600 pairs
and about 250 discordant ones, the score method is the standard choice and the five
methods leave no room for a different verdict. For reference the first-draw 95%
interval is [-8.7, +1.8].

**Why it fails at 7.5.** The interval width depends on how often the two domains
disagree, not on how close their totals are. The prereg assumed disagreement on 18% of
instances and stated that 7.5 is certifiable up to 33% at n = 500 (that figure is an
80%-power bound; the same formula gives 39% at n = 600). The data show 43.2%
(first-draw) and 41.8% (last-attempt). At that rate the test's power is 0.75 to 0.77
even for a true gap of zero, against 0.99 as planned.

### 1.4 What is true as of the data

The point estimate is 3.5 points on the first-draw reading and 2.2 on the last-attempt
reading, Mystery higher in both, and both are smaller than 7.5 and 10. Against the
plus/minus 7.5 margin, the paired equivalence test the prereg names gives "criterion not
met" on the first-draw reading (p = 0.068, the interval reaches -7.9) and "criterion
met" on the last-attempt reading (p = 0.022). The first-draw reading is the one the
prereg's own retry rule implies and the one the paper is bound to, so for the numbers
the tex quotes the status at 7.5 is "criterion not met / unresolved". Against plus/minus
10 the criterion is met on both readings. The RESCUE-branch verdict as recorded in the
results doc depends on plus/minus 10 (that is the figure in the branch's own bullet and
in §6), and on that figure it stands whichever reading is used. If the Margin bullet's
7.5 is taken as the whole-pool value of that same requirement, the branch's third
requirement is unresolved on the first-draw reading. The other two branch requirements
(delegation 100%, formalization match not below clean) are not touched by any of this.
All of the above is on the shipped extractor. Section 2.4 shows that on the corrected
extractor the gap is 24 points and the criterion is not met at either margin.

---

## 2. The extractor

### 2.1 The two faults, reproduced

The shipped extractor is `text_to_plan_blocksworld` in the upstream
`utils/text_to_pddl.py` (Mystery uses the same function with Mystery action names).

1. **It scans the whole response.** Any line anywhere in the model's reasoning that
   contains an action word and the right number of object names is added to the plan.
   Reproduced: 479 of 600 Mystery no-tools trials carry extra actions (audit definition:
   more actions extracted than lines in the plan block). Also 11 Mystery with-tools and
   8 Blocksworld with-tools trials.
2. **It only reads the long English phrasing.** It looks for the full object name
   ("object b", "red block"). A line such as `feast b c`, `(feast b c)` or
   `pick-up yellow` is dropped. Reproduced: 125 of 569 delivered Mystery with-tools
   plans extract to nothing while containing a plan. Blocksworld with tools: 3.

### 2.2 The corrected extractor

`tools/reanalysis/planbench_corrected_extractor.py`. Same rules for every cell:

- Read only the text between the **last** `[PLAN]` tag and the `[PLAN END]` after it.
  No block, or a block with no action in it, is a failure.
- One action per line. Strip numbering, bullets, markdown, brackets, final punctuation.
- The line must **start** with an action name (so a sentence that mentions an action
  cannot be picked up). Accepted: the benchmark's English names and the PDDL names
  (`pick up` / `pick-up`, `put down` / `put-down`, `stack`, `unstack`; `attack`,
  `succumb`, `overcome`, `feast`).
- Drop filler words (the, from, on, top, of, block, object, ...). What is left must be
  exactly the right number of objects: colour words on Blocksworld, single letters on
  Mystery. Arguments in order of appearance, as in the shipped extractor.
- A line in the block that does not parse is skipped and counted (2 lines in 2,400
  trials, both prose in a failed trial).
- The plan is validated by the pipeline's own `utils.validate_plan`: same VAL binary,
  same domain and instance files.

Checks on the instrument itself:

- Re-running the **shipped** extractor through this script reproduces the archived
  verdict on **2,400 of 2,400** trials. The validator setup is the pipeline's.
- Blocksworld no tools, where neither fault occurs: corrected = shipped on 600 of 600.
- Shipped extractor on the block only reproduces the pinned stripped-block regrade
  exactly: 26/600.
- A separate 60-line simulator of the four-action domain, sharing no code with VAL or
  the upstream tree (`planbench_spotcheck.py`), agrees with VAL on every delivered
  trial: 2,306 of 2,306 corrected plans and 2,306 of 2,306 shipped plans.
- A plan can only pass by being a valid plan for the benchmark's own instance, so the
  correction cannot create a false pass. Its risk is the other way: a notation it still
  cannot read. None was found (zero unparsed lines in both Mystery cells).

### 2.3 Cells: as shipped beside corrected

n = 600 per cell. Wilson 95% intervals. "block only" is the shipped parser restricted
to the answer block (repairs fault 1 only). "corrected" repairs both.

| cell | as shipped | block only | **corrected** | corrected, first block |
|---|---|---|---|---|
| Blocksworld, no tools | 287 = 47.8 [43.9, 51.8] | 287 = 47.8 | **287 = 47.8 [43.9, 51.8]** | 287 |
| Blocksworld, with tools, first-draw | 410 = 68.3 [64.5, 71.9] | 415 = 69.2 | **421 = 70.2 [66.4, 73.7]** | 420 |
| Blocksworld, with tools, last-attempt | 418 = 69.7 [65.9, 73.2] | 423 = 70.5 | 429 = 71.5 [67.8, 75.0] | 428 |
| Mystery, no tools | 0 = 0.0 [0.0, 0.6] | 26 = 4.3 | **26 = 4.3 [3.0, 6.3]** | 26 |
| Mystery, with tools | 431 = 71.8 [68.1, 75.3] | 439 = 73.2 | **566 = 94.3 [92.2, 95.9]** | 564 |

The strict variant (any unparsed line in the block fails the trial) gives the same
counts as "corrected" in every cell.

Where the changes come from:

| cell | 0 to 1 | 1 to 0 | breakdown of the 0 to 1 flips |
|---|---|---|---|
| Blocksworld, no tools | 0 | 0 | none |
| Blocksworld, with tools | 11 | 0 | 5 stray actions from the reasoning; 3 pure shorthand; 2 mixed shorthand and English; 1 two answer blocks |
| Mystery, no tools | 26 | 0 | all stray actions (the same 26 as the pinned regrade) |
| Mystery, with tools | 135 | 0 | 125 shorthand (125 of 125 valid); 10 stray actions or two blocks |

What is left wrong in Mystery with tools after correction (34 trials): 31 returned
nothing (tool-turn limit), 1 returned an empty block ("the planner says unsolvable"),
2 delivered an invalid plan. In Blocksworld with tools, last-attempt (171 trials): 63
returned nothing, 87 returned an empty block, 11 had no block, 2 had only prose in the
block, 8 delivered an invalid plan.

Of the trials where the corrected extractor found a plan, the plan was valid in 429 of
437 on Blocksworld (98.2%) and 566 of 568 on Mystery (99.6%). The shipped figures for
the same quantity are 95.9% and 97.3% (tex 1525-1526).

### 2.4 Paired contrasts

Paired on the 600 shared instances. Exact McNemar. 95% interval by the Tango score
method. First-draw is the primary reading; last-attempt in brackets where it differs.

**Tools against no tools, within a domain**

| domain | grading | gap | with-tools only | no-tools only | 95% CI | McNemar p |
|---|---|---|---|---|---|---|
| Blocksworld | as shipped | +20.5 (+21.8) | 202 (206) | 79 (75) | [+15.2, +25.7] | 1.4e-13 (2.7e-15) |
| Blocksworld | corrected | **+22.3** (+23.7) | 207 (211) | 73 (69) | [+17.1, +27.5] | 5.1e-16 (6.7e-18) |
| Mystery | as shipped | +71.8 | 431 | 0 | [+68.1, +75.3] | 3.6e-130 |
| Mystery | block only | +68.8 | 420 | 7 | [+64.8, +72.6] | 2.9e-114 |
| Mystery | corrected | **+90.0** | 541 | 1 | [+87.3, +92.2] | 7.5e-161 |

The paper's existing robustness figure (tex 1544-1545: 412 against 7, p = 6.4e-112)
mixes the two gradings: stripped no-tools against as-shipped with-tools. The like for
like "block only" row is 420 against 7. Both leave the conclusion unchanged.

**Blocksworld against Mystery, inside the with-tools arm (the Question 1 quantity)**

| grading | reading | gap | Blocksworld only | Mystery only | 90% CI | TOST ±7.5 | TOST ±10 |
|---|---|---|---|---|---|---|---|
| as shipped | first-draw | -3.5 | 119 | 140 | [-7.9, +0.9] | p = 0.068, not met | p = 0.008, met |
| as shipped | last-attempt | -2.2 | 119 | 132 | [-6.5, +2.2] | p = 0.022, met | p = 0.002, met |
| block only | first-draw | -4.0 | 113 | 137 | [-8.3, +0.3] | p = 0.092, not met | p = 0.011, met |
| block only | last-attempt | -2.7 | 113 | 129 | [-6.9, +1.6] | p = 0.031, met | p = 0.002, met |
| **corrected** | **first-draw** | **-24.2** | 28 | 173 | [-27.7, -20.6] | not met | not met |
| corrected | last-attempt | -22.8 | 28 | 165 | [-26.3, -19.4] | not met | not met |

On the corrected grading the difference between the domains is itself significant
(McNemar p = 1.0e-26 first-draw, 7.9e-25 last-attempt; 95% CI [-28.4, -20.0]). Mystery
is solved more often than Blocksworld once tools are attached. That is the same picture
as the paper's own mechanism numbers (plan found: 95.3% Mystery, 69.7% Blocksworld;
domain written correctly: 99.5% against 69.5%).

**Blocksworld against Mystery, no tools:** +47.8 as shipped (287 against 0), +43.5
corrected (268 against 7, 95% CI [+39.4, +47.6]). The collapse stands.

### 2.5 Hand spot-check (39 trials)

For each trial I read the model's answer block, the shipped extraction, the corrected
extraction and the gold plan, and re-validated the corrected plan two further ways: a
direct VAL subprocess call, and the independent simulator. Targeted groups plus a
seeded random draw (seed 20261002). "bw" = `blocksworld`, "mbw" = `mystery_blocksworld`,
"_3" = the 3-block pool. Verdicts are shipped to corrected.

| # | trial | verdict | what the answer block shows |
|---|---|---|---|
| 1 | mbw WT 106 | 0 to 1 | `feast c a` ... shorthand, 8 actions, identical to gold |
| 2 | mbw WT 117 | 0 to 1 | shorthand, 14 actions, longer than gold, valid |
| 3 | mbw WT 240 | 0 to 1 | shorthand, 4 actions, identical to gold |
| 4 | mbw WT 258 | 0 to 1 | shorthand, 8 actions, differs from gold, valid |
| 5 | mbw WT 367 | 0 to 1 | shorthand, 10 actions, identical to gold |
| 6 | mbw WT 434 | 0 to 1 | one sentence, then shorthand block, identical to gold |
| 7 | mbw_3 WT 28 | 0 to 1 | shorthand, 8 actions, identical to gold |
| 8 | mbw_3 WT 70 | 0 to 1 | shorthand, 4 actions, identical to gold |
| 9 | mbw WT 69 | 0 to 1 | full phrasing; shipped added `feast d a` from a quoted example in the preamble |
| 10 | mbw WT 436 | 0 to 1 | full phrasing; shipped added `overcome a b` from the preamble |
| 11 | mbw_3 WT 15 | 0 to 1 | two blocks and no prose; last block identical to gold; shipped concatenated both. **Ambiguous case**, see below |
| 12 | mbw WT 335 | 0 to 0 | empty block, model reports "cannot be reached" |
| 13 | mbw WT 441 | 0 to 0 | full phrasing, 14 actions, same extraction both ways, invalid plan |
| 14 | mbw_3 WT 69 | 0 to 0 | full phrasing, 6 actions, same extraction, invalid plan |
| 15 | mbw NT 149 | 0 to 1 | block has 2 actions = gold; shipped scraped 7 from the walkthrough |
| 16 | mbw NT 164 | 0 to 1 | block has 2 actions = gold; shipped scraped 8 |
| 17 | mbw NT 324 | 0 to 1 | block has 4 actions = gold; shipped scraped 12 |
| 18 | mbw_3 NT 17 | 0 to 1 | block has 4 actions = gold; shipped scraped 14 |
| 19 | mbw NT 381 | 0 to 0 | block has 6 actions, misses the first two gold steps, invalid |
| 20 | mbw NT 454 | 0 to 0 | block has 6 actions, invalid ("after careful analysis") |
| 21 | mbw_3 NT 72 | 0 to 0 | block has 4 actions, skips a needed step, invalid |
| 22 | bw WT 16 | 0 to 1 | two blocks; "Now I'll format my plan correctly:" then a block identical to gold |
| 23 | bw WT 62 | 0 to 1 | first lines `unstack blue from orange` (no "block"), rest full phrasing; shipped dropped 4 lines |
| 24 | bw WT 71 | 0 to 1 | block of 2 actions = gold; shipped doubled it from the preamble |
| 25 | bw WT 77 | 0 to 1 | block of 10 = gold; shipped doubled it from a numbered conversion list |
| 26 | bw WT 117 | 0 to 1 | `unstack yellow blue`, `put-down yellow` ... pure shorthand, 14 actions, valid |
| 27 | bw WT 225 | 0 to 1 | `unstack yellow from orange`, `put down yellow` ... 4 actions = gold |
| 28 | bw WT 299 | 0 to 1 | block of 12, valid; shipped doubled it from a numbered list |
| 29 | bw WT 342 | 0 to 1 | `unstack yellow from on top of the red block` (first object without "block"); shipped dropped 3 lines |
| 30 | bw WT 353 | 0 to 1 | block of 10, valid; shipped added 4 lines from a format reminder |
| 31 | bw WT 448 | 0 to 1 | block of 14, valid; shipped added 10 from a conversion list |
| 32 | bw WT 452 | 0 to 1 | pure shorthand, 18 actions, valid |
| 33 | bw WT 178 | 0 to 0 | block contains one sentence: "The problem is unsolvable ..." |
| 34 | bw WT 400 | 0 to 0 | no answer; the last `[PLAN]` is inside a quote of the instructions |
| 35 | bw NT 15 | 1 to 1 | block of 8, same extraction both ways, valid |
| 36 | bw NT 275 | 0 to 0 | block of 8, same extraction both ways, invalid |
| 37 | bw WT 16 | (same trial as 22, drawn again in the two-block group) | |
| 38 | mbw WT 429 | 1 to 1 | first `[PLAN]` is inside a sentence; last block is the plan. First-block rule would fail it |
| 39 | mbw_3 WT 15 | (same trial as 11) | |

37 distinct trials. In all of them the three validators agree, and the corrected
extraction is exactly the list of lines in the model's final block.

One judgement call: trial 11 (`mystery_blocksworld_3` 15). The response is two plan
blocks with nothing else. The last-block rule takes the second (valid). The first-block
rule takes the first (invalid). It is one trial and is the whole difference between 566
and 565; the "first block" column in 2.3 shows the cell under the other rule (564, which
also loses trial 38).

### 2.6 "501 instance files but 600 instances per cell"

From the upstream configs and the instance directories:

| config | directory | files on disk | `start`, `end` | ids asked | blocks |
|---|---|---|---|---|---|
| `blocksworld` | `blocksworld/generated_basic` | 501 (`instance-1` to `-501`) | 1, 500 | 2 to 501 = **500** | 445 with 4, 55 with 5 |
| `blocksworld_3` | `blocksworld/generated_basic_3` | 101 (`instance-1` to `-101`) | 1, 100 | 2 to 101 = **100** | 100 with 3 |
| `mystery_blocksworld` | `blocksworld/mystery/generated_basic` | 502 (adds a stray `instance-0`) | 1, 500 | 2 to 501 = 500 | same |
| `mystery_blocksworld_3` | `blocksworld/mystery/generated_basic_3` | 101 | 1, 100 | 2 to 101 = 100 | same |

- The benchmark is one-shot: instance i is asked with instance i-1 as the worked example
  (`example_instance_ids` in the graded files: id 2 uses [1], id 3 uses [2]). So file 1
  of each directory is only ever an example, and the ids asked are `start+1` to `end+1`
  (`prompt_generation.py` L114; the pinned loaders use the same range).
- 500 + 100 = **600 instances per cell**, out of 501 + 101 = **602 files**. The 600 are
  the published PlanBench set (prereg Amendment K: GPT-4's 157/500 + 49/100 = 206/600).
  All 600 are distinct problems.
- The "501" in the tex is the rename check as first done, on the first directory only,
  before the 3-block pool was added. Re-checked today on everything: after applying the
  symbol rename, the Mystery file equals the Blocksworld file (objects, initial state,
  goal) for **501 of 501 and 101 of 101, 602 of 602**.

---

## 3. How to reproduce

All commands from the repo root. Steps 2 to 4 need the patched upstream tree at
`external/LLMs-Planning` and its venv `.venv-planbench-wt` (set up by
`planbench/setup.sh` and `planbench/apply_patches.py`; both are gitignored, both are
present on Omer's laptop). `OUT` is any scratch directory.

```bash
# 0. pinned verification (data only)
python3 planbench/analysis/verify_promotion.py

# 1. Question 1: paired TOST, both readings, both margins, five methods (data only)
python3 tools/reanalysis/planbench_equivalence_tost.py --json $OUT/tost.json

# 2. pinned analysis as it ran (shows there is no TOST), and the pinned 26/600 regrade
REPO=$PWD
( cd external/LLMs-Planning/plan-bench && \
  VAL=$REPO/external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables PYTHONPATH=$REPO \
  $REPO/.venv-planbench-wt/bin/python $REPO/planbench/analysis/analyze_confirmatory.py && \
  VAL=$REPO/external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables PYTHONPATH=$REPO \
  $REPO/.venv-planbench-wt/bin/python $REPO/planbench/analysis/stripped_block_regrade.py )

# 3. Question 2: regrade all four cells (about 2 minutes; writes rows.jsonl, summary.json)
.venv-planbench-wt/bin/python tools/reanalysis/planbench_corrected_extractor.py --out $OUT
#    reprint the tables from saved rows without re-grading:
.venv-planbench-wt/bin/python tools/reanalysis/planbench_corrected_extractor.py --report-only $OUT

# 4. independent simulator cross-check and the hand spot-check sample
python3 tools/reanalysis/planbench_spotcheck.py $OUT --show
```

Inputs read: `results/planbench/wt-anthropic-20260801/graded/*` and
`sidelogs/blocksworld__anthropic-tools.jsonl` (the 18 re-drawn ids);
`results/haiku-frontier/planbench/blocksworld/...` for the 205/500 half of 43.8;
upstream configs, domain and instance files. Steps 2 and 3 write throwaway plan files
(step 2 in the gitignored upstream tree, step 3 in a temp directory). Nothing under
`results/`, `planbench/` or `paper/` is written.

## 4. Limits of this note

- The corrected extractor's rules were written after looking at which line shapes occur
  in the answer blocks (not after looking at corrected scores). It is a sensitivity
  analysis, not a preregistered endpoint.
- It reads argument order as written. A plan written in a model-invented parameter order
  would be marked invalid, which is the conservative direction.
- One model, one benchmark family, as before. Nothing here speaks to C15's other points.
- The equivalence test is exploratory in the prereg. Its failure at 7.5 does not touch
  the two confirmatory tests, and neither does the corrected grading: both get stronger.
- `NUMBERS.md`, the results doc and `paper_notes_discussions.md` were not edited. If any
  of these figures is adopted, they need an entry.
