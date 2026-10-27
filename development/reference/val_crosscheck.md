# VAL cross-check of the answer key (action plan C1)

*2026-10-27. Answers weakness C8 ("the answer key comes from the same tools the model is
given") and disagreement D1 of `weakness_consolidated.md`. Local only: no cluster, no API
calls, no change to any harness file or fixture. Script: `tools/val_crosscheck.py`
(sha256 `e6e9a78b…`). Outputs (gitignored, main checkout): `results/val-crosscheck/`
`val_items.csv` (one row per item, sha256 `2542234c…`), `val_rows.csv` (one row per solve
trial, `7500d37a…`), `val_summary.json` (`474ffca3…`).*

## Bottom line

- **Plans: VAL and our grader agree on 1,731 of the 1,732 plans VAL could check (99.94%,
  Wilson 95% [99.67, 99.99]).** That is all 1,000 validate_plan fixture plans and 731 of the
  732 distinct solve plans graded in the delivered rerun. Classical 877/878, numeric
  854/854: no disagreement at all on the 10 numeric domains.
- **The one disagreement is our grader being too lenient.** pyval quietly reads a plan
  action `pick-up` as the domain's `pick_up` (it maps `-` to `_` in plan names). VAL, like
  the PDDL standard, treats them as different names and rejects the plan. It affects one
  trial: Part C (no tools), Qwen3.5-9B, blocksworld p02, wording 11, graded a success.
  Under VAL the Part C solve count for that model goes from 73 to 72 of 300 delivered
  (24.3% to 24.0%) and from 32 to 31 on the online grade. No tool-arm trial is affected.
- **10 more solve plans crash VAL** (segmentation fault, no verdict). Every one has a step
  with the wrong number of arguments; pyval rejects all 10 as `STRUCTURE_ERROR`, which is
  right. They are counted apart, not as agreement. All 10 come from no-tools answers.
- **Domain and problem files (parse check): agreement is much lower, 184 of 238 (77.3%,
  [71.6, 82.2]).** VAL accepts every valid file (120/120) and rejects every invalid file
  whose fault is inside the `(define …)` form (64/64: syntax errors, undeclared names,
  type errors, a removed `:objects`). It accepts all 54 invalid files whose only fault is
  (a) a stray `)` after the end of the define (10 domains, 18 problems) or (b) a missing
  `:goal` section (26 problems, 13 of them also with the stray `)`). Both faults make the
  file invalid under the PDDL grammar, so the labels are right; VAL is lenient. Checked by
  hand: VAL ignores any text after the first complete define (even plain junk), and treats
  a missing goal as an empty goal, so every executable plan, even the empty plan, is
  "valid" against such a problem. 2 more problem files (no `:init` section) crash VAL.
- **The key itself is stable.** Re-running pyval locally reproduced every stored verdict:
  all 1,240 fixture labels, all 740 stored delivered-plan verdicts, and the stored online
  grade of all 1,933 solve trials that had a plan to grade.

## What this means for the paper

- **Supported:** an outside validator, KCL VAL, agrees with the answer key on 1,731 of
  1,732 plans (every validate_plan fixture and every solve plan graded in the rerun), and
  the one disagreement is a leniency in our validator worth one trial.
- **Not supported:** "the domain and problem labels are checked by VAL". VAL confirms all
  valid labels and the 64 invalid labels whose fault is inside the define, but not the 54
  that rest on two grammar rules VAL does not enforce (nothing may follow the define; a
  problem must have a goal). Those labels are correct, and a strict reading of PDDL is a
  defensible choice, but it is a choice: 10 of the 20 invalid domains and 44 of the 100
  invalid problems are invalid only under it. This belongs in Methods next to the "by
  construction" sentence of B4, and it bears on how the validate_domain and
  validate_problem scores are read (see also the item facts in
  `reanalysis_breakdowns_cost.md` §4).
- **C8 itself.** The hyphen case is exactly the kind of quirk C8 warned about: the tool and
  the key share it, so a model that relays the tool cannot be caught by the key. Measured
  size: 1 of 742 distinct solve plans, one trial. Simulate is not covered by this check.
- **D1b (harder items).** The new items are not built yet. When they are, run the script
  with `--domains-dir` pointed at them (same layout). Invalid domains and problems whose
  fault VAL also catches make the stronger items; report any strictness-only items apart.

## Method

**VAL.** The macOS x86_64 build shipped in the PlanBench repository,
`../LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate`, run on a copy under
Rosetta 2 (`arch -x86_64`) on macOS 26 arm64. It is the same binary (sha256
`44a07d6d3b2917c7c3df8e3932a3b895a8062b4e0f5fa0343f9f1ad409c4a9fe`) that this repo's
PlanBench spot checks used (`planbench/analysis/val_spotcheck.py`). Banner: "VAL: The PDDL+
plan validation tool, Version 4" (Long, Howey, Cresswell, Fox). The binary carries no
commit; the provenance is LLMs-Planning commit `8abfd7b` (local clone), where the VAL
directory last changed in `9bd2478` (2023-06-14). The Linux ELF next to it (sha256
`99ade8b3…`) was not needed. Current KCL VAL was not built: the plan made that conditional
on the old build mishandling numeric PDDL, and it did not (854/854 numeric plans agree).
The crashes listed below may be fixed upstream; the script takes any binary via `--val`.

**pyval (the harness side).** `pddl-copilot` at `5e4f9c0` (the rerun's tools commit),
pddl-validator plugin venv with `pddl-pyvalidator` 0.1.5 and `unified-planning` 1.3.0,
called through the harness's own path (`MCPPlanner` to the validator plugin, the same
arguments as `scoring._validate_model_plan` and `domains._validate_capture`). The cluster's
exact pyval version is not on record; the local one reproduced every stored verdict, so the
comparison is with the key as stored.

**Inputs.**

| input | items | harness verdict compared |
|---|---|---|
| validate_plan fixtures (`pNN_vK.plan`, `pNN_bK.plan`, 20 domains) | 1,000 plans (500 valid, 500 invalid) | the slot label, which `generate_ground_truth` asserts equal to pyval at every sweep start |
| solve plans graded in the delivered rerun (all 7 cells; 2,700 solve trials, Parts A and C, Part B has no solve) | 742 distinct (domain, problem, plan) | stored delivered verdict in `results/delivered-rerun-secondary/plan_verdicts.json` (740 plans); live pyval for the 2 plans only the online grader saw |
| domain files (`domain.pddl`, `domain_neg.pddl`) | 40 (20 valid, 20 invalid) | slot label |
| problem files (`pNN.pddl`, `nNN.pddl`) | 200 (100 valid, 100 invalid) | slot label |

"Graded solve plan" means every plan a solve grader of the rerun validated:
(1) the plan the delivered grader extracts from each final answer
(`tools/delivered_rerun/grade.solve_plan`, the frozen readout's code), on both arms; and
(2) every plan the online grader validates (`pddl_eval.scoring.check_success`, called as
is): the planner tool's plan on the tool arm, the parsed answer on the no-tools arm. The
two sets overlap almost fully, since models mostly relay the planner's plan. Plans are
written to VAL exactly as the harness hands them to pyval (lines joined by newlines);
fixture files are passed as stored. For every plan VAL parsed, VAL's "Plan size" equals the
number of plan lines the harness passed (0 mismatches), so VAL saw the plan the grader saw.

**VAL verdicts.** Plans: `validate -v DOMAIN PROBLEM PLAN`, one plan per call. "Plan valid"
is valid. "Plan invalid", "Plan failed to execute", "Goal not satisfied", "Bad plan
description!" or a plan type-check error is invalid. A crash with no verdict is "cannot
handle". Parse check: `validate DOMAIN PROBLEM` with no plan, which parses and type-checks
both files. Any VAL error message is invalid; no message and exit 0 is valid. A domain is
checked with its own `p01.pddl` (accepted with `domain.pddl` in all 20 domains, so any
rejection is the domain's); a problem with `domain.pddl`.

**Row level.** Each solve trial is regraded with `check_success` plus the runner's
truncation relabel, once with live pyval (must reproduce the stored `success`) and once
with VAL in pyval's place. The delivered grade of each trial is recomputed with VAL.

**Reproduce** (from the repo root; about 5 minutes on a laptop):

```
.venv/bin/python tools/val_crosscheck.py \
  --val <copy of LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate, chmod +x> \
  --val-prefix "arch -x86_64" --domains-dir domains \
  --rerun-root results/delivered-rerun \
  --plan-verdicts results/delivered-rerun-secondary/plan_verdicts.json \
  --marketplace-path ../pddl-copilot \
  --out-csv results/val-crosscheck/val_items.csv \
  --rows-csv results/val-crosscheck/val_rows.csv \
  --summary-json results/val-crosscheck/val_summary.json
```

## Results

Agreement counts only items VAL could handle. Wilson 95% intervals.

**By input type and track**

| input | track | agree / handled | % | Wilson 95% | VAL cannot handle |
|---|---|---|---|---|---|
| **all plans** | both | **1,731 / 1,732** | **99.94** | **[99.67, 99.99]** | 10 |
| | classical | 877 / 878 | 99.89 | [99.36, 99.98] | 6 |
| | numeric | 854 / 854 | 100.00 | [99.55, 100.00] | 4 |
| validate_plan fixtures | both | 1,000 / 1,000 | 100.00 | [99.62, 100.00] | 0 |
| | classical | 500 / 500 | 100.00 | [99.24, 100.00] | 0 |
| | numeric | 500 / 500 | 100.00 | [99.24, 100.00] | 0 |
| solve plans (rerun) | both | 731 / 732 | 99.86 | [99.23, 99.98] | 10 |
| | classical | 377 / 378 | 99.74 | [98.52, 99.95] | 6 |
| | numeric | 354 / 354 | 100.00 | [98.93, 100.00] | 4 |
| **parse check, all files** | both | **184 / 238** | **77.31** | **[71.58, 82.17]** | 2 |
| | classical | 91 / 119 | 76.47 | [68.10, 83.19] | 1 |
| | numeric | 93 / 119 | 78.15 | [69.91, 84.63] | 1 |
| domain files | both | 30 / 40 | 75.00 | [59.81, 85.81] | 0 |
| | classical | 15 / 20 | 75.00 | [53.13, 88.81] | 0 |
| | numeric | 15 / 20 | 75.00 | [53.13, 88.81] | 0 |
| problem files | both | 154 / 198 | 77.78 | [71.49, 83.01] | 2 |
| | classical | 76 / 99 | 76.77 | [67.54, 83.99] | 1 |
| | numeric | 78 / 99 | 78.79 | [69.74, 85.69] | 1 |

**By label**

| input | label valid: agree | label invalid: agree |
|---|---|---|
| validate_plan fixtures | 500 / 500 | 500 / 500 |
| solve plans | 236 / 237 (classical 96/97, numeric 140/140) | 495 / 495 (10 more crash VAL) |
| domain files | 20 / 20 | 10 / 20 [29.9, 70.1] |
| problem files | 100 / 100 | 54 / 98 [45.3, 64.6] (2 more crash VAL) |

**Solve plans by where the grader met them** (a plan can be in several rows)

| source | agree / handled | VAL cannot handle |
|---|---|---|
| planner tool output, online tool-verified grade (Part A) | 108 / 108 | 0 |
| delivered answer, tool arm (Part A) | 208 / 208 | 0 |
| parsed answer, online grade, no-tools arm (Part C) | 166 / 167 | 3 |
| delivered answer, no-tools arm (Part C) | 552 / 553 | 10 |

**Trial level** (2,700 solve trials; trials with no plan to grade are left out)

| grade | trials with a plan | pyval regrade = stored | VAL handled | VAL = stored |
|---|---|---|---|---|
| tool arm, online tool-verified | 1,741 | 1,741 | 1,741 | 1,741 |
| tool arm, delivered | 1,675 | (stored verdicts used) | 1,675 | 1,675 |
| no-tools arm, online | 192 | 192 | 189 | 188 |
| no-tools arm, delivered | 661 | (stored verdicts used) | 651 | 650 |

**The kind of failure also matches.** For invalid plans, VAL's "Bad plan description" or
plan type error lines up with pyval's `STRUCTURE_ERROR` (279 of 280; the exception is the
second hyphen plan below), and VAL's execution failures ("failed to execute", 492; "goal
not satisfied", 223) line up with pyval's `INVALID` (715 of 715).

## Every disagreement, read by hand

**Plans: 1 disagreement, cause: our grader wrong (pyval leniency).**

| item | harness (pyval) | VAL | hand read |
|---|---|---|---|
| solve plan `c47cc363cfd4`, blocksworld p02: `(pick-up b3)`, `(stack b3 b2)`. One trial: Part C, Qwen3.5-9B, wording 11 (online grade and delivered grade) | VALID | invalid, "Bad plan description!" | The domain's action is `pick_up`; there is no `pick-up`. pyval's `_lookup_action` / `_lookup_object` (`pyval/validator.py`, `_name_candidates`) retry a failed name with `-` replaced by `_`, so the step runs as `pick_up` and the plan reaches the goal. In PDDL `pick-up` and `pick_up` are different names, so VAL is right. The spelled-out plan is otherwise correct. One other plan relies on the same mapping (blocksworld p04 `b47a13479747`, `pick-up` / `put-down`, one Part C Qwen3.5-9B trial); it is invalid for other reasons, so both say invalid. No other graded plan uses a hyphen spelling of an underscore name. |

**Parse check: 54 disagreements, cause: VAL leniency on two grammar rules (labels right).**
In every one the label says invalid and VAL says valid. Fault found by diffing each file
against its valid source (`domain.pddl`, `p01.pddl`); the `file_shape` column of
`val_items.csv` records it.

| cause | VAL behaviour (checked by hand) | items |
|---|---|---|
| one stray `)` after the end of the domain's define, nothing else changed (10 domains) | VAL stops reading after the first complete `(define …)` form. Appending plain junk text after a valid domain or problem is also accepted, and plans validate against such files as usual | `domain_neg.pddl` of gripper, miconic, parking, tpp, zenotravel, block-grouping, delivery, drone, gardening, zenotravel-numeric |
| one stray `)` after the end of the problem's define, nothing else changed (18 problems) | as above | `n04.pddl` of barman, blocksworld, depots, gripper, miconic, rovers, satellite, tpp, zenotravel, block-grouping, counters, delivery, depot, farmland, gardening, pogo_stick, sailing, zenotravel-numeric |
| `:goal` section removed (13 problems) | VAL accepts a problem with no goal and treats the goal as empty: the fixture valid plan and even the empty plan are reported "Plan valid" against blocksworld `n05` | `n01.pddl` of barman, gripper, miconic, parking, tpp, zenotravel, block-grouping, counters, delivery, drone, gardening, sailing, zenotravel-numeric |
| `:goal` section removed and one stray `)` (13 problems) | both of the above | `n05.pddl` of barman, blocksworld, depots, gripper, miconic, rovers, satellite, tpp, counters, depot, farmland, pogo_stick, sailing |

The PDDL grammar makes the file a single define form and requires `:init` and `:goal` in a
problem, so all 54 labels are right under a strict reading, which is what pyval applies.
Not a grader error and not a VAL bug in the narrow sense; it is a difference in strictness.
VAL agrees on every invalid file whose fault is inside the define: 10 of 10 such domains
(5 syntax errors: blocksworld, satellite, pogo_stick, depots, depot; 5 undeclared
predicates: barman, rovers, counters, farmland, sailing) and 54 of 54 such problems
(20 with an undeclared object in `:init`, 20 with an undefined predicate in `:goal`, 7
with `:objects` removed, and 7 older hand-made `n01` files: undeclared objects, a
predicate used with the wrong types, broken parentheses inside the define).

## Items VAL cannot handle (not counted above)

All 12 make VAL crash with a segmentation fault and no verdict. The harness label is
invalid in every case, and pyval's reason is the right one.

| item | why VAL crashes | pyval |
|---|---|---|
| problem `parking/n05.pddl`, `drone/n05.pddl` | `:init` section removed | invalid |
| solve plan `646c0cb2909a` rovers p01 (Part C Qwen3.5-9B, wording 12) | `communicate_soil_data` with 6 arguments (domain: 5); also predicates written as steps | `STRUCTURE_ERROR` |
| solve plan `eae2d1749429` rovers p02 (Part C Qwen3.5-9B, wording 13) | `navigate` with 4 arguments (3), `drop` with 3 (2) | `STRUCTURE_ERROR` |
| solve plan `59a5aecb393e` rovers p03 (Part C Qwen3.5-9B, wording 11) | `communicate_rock_data` with 6 arguments (5) | `STRUCTURE_ERROR` |
| solve plan `50f90f551333` rovers p02 (Part C Qwen3.5-9B, wording 12; also its online grade) | `drop`, `navigate`, `communicate_*` with one argument too many | `STRUCTURE_ERROR` |
| solve plan `615591af130d` pogo_stick p01 (Part C Qwen3.5-9B, wording 11) | `tp_to` with 1 argument (2) | `STRUCTURE_ERROR` |
| solve plan `d8401f7ba785` rovers p01 (Part C Gemma, wording 13) | `communicate_soil_data` with 6 arguments (5) | `STRUCTURE_ERROR` |
| solve plan `8b647496a4c1` satellite p05 (Part C Gemma, wording 13) | `turn_to` with 2 arguments (3) | `STRUCTURE_ERROR` |
| solve plan `be4c362e826d` pogo_stick p04 (Part C Gemma, wording 11; also its online grade) | `tp_to` with 1 argument (2) | `STRUCTURE_ERROR` |
| solve plan `ee4c5e28beb7` sailing p01 (Part C Gemma, wording 12) | `go_west` / `go_north_west` with no argument (1) | `STRUCTURE_ERROR` |
| solve plan `20c73c687512` sailing p01, 268 steps (Part C Gemma, wording 13; also its online grade) | moves with no argument (1) | `STRUCTURE_ERROR` |

A wrong argument count crashes this VAL build on any domain (reproduced on a one-line
blocksworld plan, `(unstack b2)`); an unknown action name gives "Bad plan description!" instead, and an
unknown object gives a type-check error, both of which count as invalid.

## Limits of this check

- One VAL build, a 2023 copy with no commit id. Current upstream VAL was not built (see
  Method).
- Simulate is not covered, and the parse check covers only what `validate` checks without
  a plan (parsing and type checking).
- The stored per-plan verdict exists only for delivered plans. For the 2 plans only the
  online grader saw, the harness side is live pyval, checked against the 1,933 stored trial
  grades it reproduces.
- The fixture labels are compared directly; they equal pyval by construction (asserted at
  every sweep start, and re-checked here: 1,240/1,240).

## Proposed `NUMBERS.md` row (not yet entered)

| figure | **quote this** | do NOT quote |
|---|---|---|
| KCL VAL cross-check of the answer key (C1; `reference/val_crosscheck.md`) | **plans: 1,731 / 1,732 agree (99.94%, Wilson 95% [99.67, 99.99])**: all 1,000 validate_plan fixture plans and 731/732 distinct solve plans graded in the delivered rerun; the 1 disagreement is pyval accepting `pick-up` for `pick_up` (one Part C trial); 10 more plans crash VAL (wrong argument count) and are not counted. Parse check of domain and problem files: 184 / 238 (77.3% [71.6, 82.2]); every miss is VAL accepting a stray `)` after the define or a missing `:goal` | "checked by VAL" for the validate_domain / validate_problem labels; "100% agreement"; any pooled plans-plus-files figure |
