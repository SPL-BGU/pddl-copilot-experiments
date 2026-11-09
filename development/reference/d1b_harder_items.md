# D1b: new item kinds (three fixture trees, no harness change)

Record of action plan step D1b, written 2026-11-09. The file name keeps the word
"harder" because older notes cite it; the items are called **new item kinds** here,
since nobody has yet measured whether they are harder (see "What the prereg should
register" below).

Built by `tools/build_hard_fixtures.py` (helpers `tools/_hard_items.py`,
`tools/_enhsp_variants.py`) from `domains/`, which was only read. Tests:
`tests/test_hard_items.py`. Change log: `development/CHANGELOG.md`, 2026-11-09 entry.

## 1. What the items are

Each kind is made so that a quick look is not enough to judge it.

| task | valid items | invalid items |
|---|---|---|
| validate_plan | **distinct** valid plans for one problem (from different planners or search settings, deduplicated exactly), not five copies of one plan as in `domains/` | one edit of a valid plan (delete a step, swap two neighbouring steps, or replace a step) whose first failing step is at or after the halfway point of the plan, never at the last step in this build |
| validate_problem | the same problem files as `domains/` (copied) | one local edit with a real error: undefined object, wrong arity, type mismatch, undeclared predicate, undeclared type, undeclared function |
| validate_domain | the same `domain.pddl` (copied) | one local edit with a real error: undeclared predicate, wrong arity, type mismatch, undeclared type, undeclared function |

Every edit is one contiguous change inside the `define` form; layout and comments stay
byte-identical. Kinds are spread evenly over the items of each track.

## 2. The three trees, and why there are three

The frozen loader (`pddl_eval/domains.py`, a file of the delivered-rerun package,
sha256 in `delivered_rerun_prereg.md` section 8) reads one invalid domain per folder,
the file `domain_neg.pddl`. For validate_domain the runner emits one valid job per
problem in the folder and one invalid job for `domain_neg.pddl`. So a folder with two
problems gives 2 valid : 1 invalid, and a second file such as `domain_neg02.pddl` would
be skipped without a warning. A first build (commit `ad7771c`) changed the loader to
read such files. Omer decided on 2026-11-09 against any harness change, so that change
was dropped and validate_domain is balanced with two small trees instead:

| tree | holds | per folder | use it for |
|---|---|---|---|
| `domains-hard/` | 20 domains (10 classical, 10 numeric) | `domain.pddl`, 2 problems, 2 or 1 valid plans and as many invalid plans per problem, 2 invalid problems, 1 invalid domain (`domain_neg.pddl`) | validate_problem, validate_plan (and solve, simulate if wanted, see section 6) |
| `domains-hard-vd-a/` | the same 20 domains | `domain.pddl`, the first chosen problem by name, the first invalid domain | validate_domain only |
| `domains-hard-vd-b/` | the same 20 domains | `domain.pddl`, the second chosen problem by name, the second invalid domain | validate_domain only |

Trees a and b together: per domain, 2 valid jobs (`domain.pddl` with each problem) and
2 invalid jobs (each invalid domain with its own problem). Tree a's invalid domain is
the same file as `domains-hard/`'s `domain_neg.pddl`. **Do not run validate_domain on
`domains-hard/`**: there it is 2 : 1.

No file named `domain_neg<digits>.pddl` exists in any tree; the build and the tests
check this.

## 3. Counts

Counts are files. validate_plan has 78 of each label, not 80: in two problems
(block-grouping p03, numeric; miconic p05, classical) only one invalid plan could be
built under the halfway rule, so the problem keeps one valid and one invalid plan
(balance per problem is kept).

| | classical | numeric | all |
|---|---|---|---|
| validate_plan valid / invalid (`domains-hard/`) | 39 / 39 | 39 / 39 | **78 / 78** |
| validate_problem valid / invalid (`domains-hard/`) | 20 / 20 | 20 / 20 | **40 / 40** |
| validate_domain valid / invalid jobs per prompt variant (trees a + b) | 20 / 20 | 20 / 20 | **40 / 40** |
| distinct item files (all trees) | | | 296 |

Invalid kinds (counts per kind):

| kind | count |
|---|---|
| validate_plan: delete a step / swap neighbours / replace by a sibling grounding / replace by another action | 20 / 26 / 16 / 16 |
| validate_problem: type mismatch / undeclared predicate / undeclared type / undefined object / wrong arity / undeclared function | 8 / 8 / 7 / 7 / 7 / 3 |
| validate_domain, tree a: type mismatch / wrong arity / undeclared predicate / undeclared type / undeclared function | 7 / 5 / 4 / 3 / 1 |
| validate_domain, tree b: undeclared type / undeclared predicate / wrong arity / undeclared function / type mismatch | 6 / 5 / 4 / 3 / 2 |
| validate_domain, a + b | 9 type mismatch, 9 wrong arity, 9 undeclared predicate, 9 undeclared type, 4 undeclared function (numeric only) |

Plans: valid plan length 5 to 111 steps (median 21). Invalid plans fail at a relative
position of 0.50 to 0.98 (median 0.78); 0 of 78 fail on the last step. 75 of the 78
invalid plans are edits of a valid plan that is itself in the set; 3 are edits of
another distinct valid plan (named in the manifest). Distinct valid plans found per
source problem in `domains/` (100 problems): 1 plan for 15, 2 for 18, 3 or more for 67.

Skipped: block-grouping p02 and p05, counters p02 and p03 (no edit met the halfway
rule); each of those domains still has two problems.

## 4. How they were built and checked

Command (2026-11-09, from the repo root of this branch; about 15 minutes with the
planner cache):

```
.venv/bin/python tools/build_hard_fixtures.py \
  --src-dir domains --out-dir domains-hard \
  --marketplace-path ../pddl-copilot \
  --solver-python ../pddl-copilot/plugins/pddl-solver/.venv/bin/python \
  --val <copy of ../LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate, chmod +x> \
  --val-prefix "arch -x86_64" \
  --cache-json <copy of domains-hard/planner_outputs.json> --force
```

`pddl-copilot` at `5e4f9c0` (the rerun's tools commit, `plugins/` clean). VAL is the
macOS x86_64 build that C1 used (sha256 `44a07d6d…a9fe`, run under Rosetta;
`val_crosscheck.md`). Defaults: `--problems-per-domain 2 --max-valid-plans 2 --seed 0
--enhsp-timeout 30`. Rebuilt with the planner cache, every item file came out
byte-identical to the first build `ad7771c` (the first build's `domain_neg02.pddl` is now
tree b's `domain_neg.pddl`).

Checks, all passed:

1. **Oracle at build time.** The pddl-validator plugin, called through the harness's
   own path (`_validate_capture` over `MCPPlanner`). Valid plans: accepted. Invalid
   plans: rejected with a precondition failure at the recorded step. Invalid files:
   rejected, and the first error names the edited symbol. 3,899 oracle calls.
2. **VAL at build time.** Every valid plan accepted; every invalid plan fails at the same
   step on the same action as the oracle; every invalid file rejected.
3. **Harness fail-fast pass.** Each tree loaded with the unchanged `load_domains` and run
   through `generate_ground_truth`: 20 domains in each tree, every problem solvable (40,
   20, 20), every invalid file and plan confirmed. On trees a and b it prints "0
   committed valid plans" per problem: expected, those trees have no plans and are run
   for validate_domain only.
4. **VAL re-check from disk** (in the build): 276 / 276, 60 / 60, 60 / 60 agree.
5. **C1 script, independently** (`tools/val_crosscheck.py --domains-dir <tree>
   --marketplace-path ../pddl-copilot`, same VAL binary): VAL agrees with the label on
   276 / 276 items of `domains-hard/` and 60 / 60 of each validate_domain tree, none
   that VAL cannot handle; live pyval agrees with the label on all of them too.

Excluded at build time: 41 candidate files that the oracle rejected but VAL accepted,
all wrong-arity edits (25 domains, 16 problems): the oracle (unified-planning) checks
arity more strictly than this VAL build. They are strictness-only items and none is in
the trees; each is listed under `rejected_file_candidates` in the main manifest. No
plan candidate had an oracle and VAL disagreement.

## 5. Manifest hashes

| tree | `manifest.json` sha256 |
|---|---|
| `domains-hard/` | `324a827a89d42917cc018f02c4bf4e4f59b3050085e13c34d5132a55f68e2157` |
| `domains-hard-vd-a/` | `b561b7a6a535addf5f9b177dcfa41f7491575c135a74e6ee1a8dc6a0c03ed31d` |
| `domains-hard-vd-b/` | `4fdcf8eedb96af6805b6b1631983a003fef96ff3c1ac0e2d1a687cc321f7f4c6` |

Build inputs recorded in every manifest: `tools/build_hard_fixtures.py` `c6f142f1…3b0`,
`tools/_hard_items.py` `30ad2a02…11a`, `tools/_enhsp_variants.py` `6c58aa5e…591`,
`domains-hard/planner_outputs.json` `b2543360…349`. A prereg that registers these items
should pin the three manifest hashes above.

## 6. How to run them

The harness reads each tree unchanged. Run each tree into **its own output folder**:

```
# validate_problem, validate_plan
python run_experiment.py --domains-dir domains-hard \
  --tasks validate_problem validate_plan --output-dir <ext>/<cell>
# validate_domain, two runs
python run_experiment.py --domains-dir domains-hard-vd-a \
  --tasks validate_domain --output-dir <ext>/<cell>-vd-a
python run_experiment.py --domains-dir domains-hard-vd-b \
  --tasks validate_domain --output-dir <ext>/<cell>-vd-b
```

On the cluster the same comes from `submit_with_rtx.sh` with `--domains-dir` and a
distinct `--run-tag` per tree (each tag gives its own `OUT_DIR`).

Two traps, both silent:

- **Trees a and b must not share an output folder.** In both, the invalid domain job of
  a domain has the problem name `domain_neg`, so the two runs produce the same resume
  key; the second run would treat tree b's invalid-domain jobs as done and skip them.
- **A result row does not say which tree it came from** (the run meta does not record
  `--domains-dir`). The analysis must label rows by output folder: in a `-vd-b` folder,
  `domain_neg` is the second invalid domain.

Solve and simulate on `domains-hard/` would not be new items: its problems are 40 of the
100 problems of `domains/`, chosen for long plans, so such a run repeats existing
problems on a subset leaning to longer plans.

The frozen delivered-rerun analysis refuses these trees (it checks the `domains/` file
manifest); the extension needs its own analysis code.

## 7. What the prereg should register

These are new item kinds; whether they are harder is an open question. The extension's
prereg should register a reading of whether unaided accuracy and tool-verified accuracy
actually drop on these items compared with `domains/` (same models, same prompts, same
tasks), per task and kind, and should call the items harder only if they do.

## 8. Where the results go, and reused rows

Decided 2026-11-09: the extension gets a new sweep folder (proposed
`results/extension-live/<cell>/`). Rerun rows it reuses are copied in with
`tools/extension_copy_reused.py`, which adds `reused_from_folder`, `reused_from_job`,
`reused_from_sha256` and `copied_at` to every copied row and writes
`reuse_provenance.json` next to it. `results/delivered-rerun/` and
`results/sweep5v2-live/` are only read. The SLURM job id is not stored in a cell's
summary or rows, so the operator passes it (the ids are in `delivered_rerun_prereg.md`
section 8; the 9B no-tools cell was resumed once, section 8c). The prereg declares the
reuse.
