# D1b: new item kinds (three fixture trees, no harness change)

Record of action plan step D1b, written 2026-11-09. The file name keeps the word
"harder" because older notes cite it; the items are called **new item kinds** here,
since nobody has yet measured whether they are harder (see "What the prereg should
register" below).

Built by `tools/build_hard_fixtures.py` (helpers `tools/_hard_items.py`,
`tools/_enhsp_variants.py`) from `domains/`, which was only read. Tests:
`tests/test_hard_items.py`. Change log: `development/CHANGELOG.md`, 2026-11-09 entry.

## 1. What the items are

Each kind was built with the aim that a quick look would not be enough to judge it.
Whether that aim is met is for the prereg to judge (section 7). Many invalid domain and
problem files are one-letter changes to a declared name (`bock` for `block`, `onable`
for `ontable`, `crae` for `crate`, `couner` for `counter`): 22 of the 40 invalid domains
and 18 of the 40 invalid problems, every undeclared-predicate, undeclared-type and
undeclared-function edit among them. A careful reader can spot such a change by eye.

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
`domains-hard/`**: there it is 2 : 1. Nothing in the tooling stops such a run (the
harness accepts `--tasks validate_domain` on any tree), so this instruction is the only
safeguard.

The two valid jobs of a domain are one prompt sent twice. The validate_domain prompts
show only the domain (`pddl_eval/prompts.py`, every validate_domain template has
`{domain}` and no `{problem}`), and both jobs carry the same `domain.pddl`, which is
byte-identical to the one in `domains/`. So the 40 valid jobs per prompt variant are 20
distinct valid items, all already in the canonical set, against 40 distinct invalid
items (none of them in `domains/`). The job counts are balanced while the distinct
items run 20 to 40. A confidence interval for validate_domain must cluster on the item
(the file sent); a per-job count overstates the evidence on the valid side.

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

Overlap with `domains/` (checked 2026-11-09 by sha256 of every file against every file
of `domains/`):

| item | in the D1b trees | byte-identical to a file in `domains/` |
|---|---|---|
| valid plans | 78 | 40, each a valid plan of the same problem |
| invalid plans | 78 | 2: `numeric/sailing/p01_b1` = `domains/numeric/sailing/p01_b2`, `numeric/delivery/p05_b1` = `domains/numeric/delivery/p05_b4` |
| valid problems | 40 | 40 (copied by design) |
| invalid problems | 40 | 0 |
| valid domains | 20 per tree | 20 (copied by design) |
| invalid domains | 40 distinct (a + b) | 0 |

A comparison of D1b items with `domains/` should either drop the overlapping items or
report them separately, since a model's answer on them is a second reading of an
existing item.

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

The harness reads each tree unchanged. Run each tree into **its own output folder**,
named with the `-hard` suffix:

```
# validate_problem, validate_plan
python run_experiment.py --domains-dir domains-hard \
  --tasks validate_problem validate_plan --output-dir <ext>/<cell>-hard
# validate_domain, two runs
python run_experiment.py --domains-dir domains-hard-vd-a \
  --tasks validate_domain --output-dir <ext>/<cell>-hard-vd-a
python run_experiment.py --domains-dir domains-hard-vd-b \
  --tasks validate_domain --output-dir <ext>/<cell>-hard-vd-b
```

On the cluster the same comes from `submit_with_rtx.sh` with `--domains-dir` and a
distinct `--run-tag` per tree (each tag gives its own `OUT_DIR`); the tag must end the
folder name with `-hard`, `-hard-vd-a` or `-hard-vd-b`.

**Reused rows and hard-tree runs must never share a folder.** Reused rows (section 8)
go to `<ext>/<cell>`, named like the source cell, which never carries the `-hard`
suffix. The resume key (`pddl_eval/resume.py`: model, task, domain, problem, plan label,
prompt variant, run settings) records neither the tree nor the file content, and the
D1b trees reuse canonical item names (`p03`, `v1` and `b1`, `n01` and `n02`,
`domain_neg`) for different files. A hard-tree run into a folder holding reused rows
would skip every new item whose key matches a reused row and grade the old answer in
its place, with no warning. `tools/extension_copy_reused.py` refuses a destination whose
name ends in `-hard`, `-hard-vd-a` or `-hard-vd-b`, and a destination whose
`trials.jsonl` already holds rows without `reused_from_*` fields. The reverse order
(a hard-tree run started in a folder of reused rows) is not caught by any tool, so the
folder names above are the guard.

Two more traps, both silent:

- **Trees a and b must not share an output folder.** In both, the invalid domain job of
  a domain has the problem name `domain_neg`, so the two runs produce the same resume
  key; the second run would treat tree b's invalid-domain jobs as done and skip them.
- **A result row does not say which tree it came from** (the run meta does not record
  `--domains-dir`). The analysis must label rows by output folder: in a `-hard-vd-b`
  folder, `domain_neg` is the second invalid domain.

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
`reuse_provenance.json` next to it. The tool refuses a hard-tree folder name and a
folder that already holds rows of a run (section 6). `results/delivered-rerun/` and
`results/sweep5v2-live/` are only read. The SLURM job id is not stored in a cell's
summary or rows, so the operator passes it (the ids are in `delivered_rerun_prereg.md`
section 8; the 9B no-tools cell was resumed once, section 8c). The prereg declares the
reuse.
