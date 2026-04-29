# Domains

Twenty benchmark PDDL domains (10 classical STRIPS + 10 numeric) used by the harness to exercise the pddl-copilot MCP tools across the 5 tasks defined in `EXPERIMENTS_FLOW.md`.

## Provenance

Original 10 (5 classical + 5 numeric) copied from the paper dataset snapshot at `.local/pddl_mcp_dataset/` (Aug 2025), shipped alongside Benyamin et al., 2025 (arXiv:2509.12987).

The remaining 10 (added in PR-3, 2026-04-29) come from public benchmark suites:
- 5 classical from olam-compatible (https://github.com/olomes/olam-compatible)
- 5 numeric from matteocarde/patty IPC-2023 mirror + hand-authored small variants for zenotravel-numeric

```
domains/
├── classical/
│   ├── barman/        (paper)
│   ├── blocksworld/   (paper)
│   ├── depots/        (paper)
│   ├── gripper/       (PR-3, olam-compatible)
│   ├── miconic/       (PR-3, olam-compatible)
│   ├── parking/       (PR-3, olam-compatible)
│   ├── rovers/        (paper)
│   ├── satellite/     (paper)
│   ├── tpp/           (PR-3, olam-compatible)
│   └── zenotravel/    (PR-3, olam-compatible — substitute for spec's "logistics")
└── numeric/
    ├── block-grouping/      (PR-3, patty/files)
    ├── counters/            (paper)
    ├── delivery/            (PR-3, patty/ipc-2023 — substitute for spec's "transport-numeric")
    ├── depot/               (paper, singular — distinct from classical `depots`)
    ├── drone/               (PR-3, patty/ipc-2023)
    ├── farmland/            (paper)
    ├── gardening/           (PR-3, patty/files — substitute for spec's "plant-watering")
    ├── pogo_stick/          (paper)
    ├── sailing/             (paper)
    └── zenotravel-numeric/  (PR-3, patty/ipc-2023 + hand-authored p02-p05)
```

## Per-domain layout (PR-3 flat layout, 62 files per domain)

```
domain.pddl                       — 1 valid domain
domain_neg.pddl                   — 1 invalid domain
p01.pddl ... p05.pddl             — 5 valid problems
n01.pddl ... n05.pddl             — 5 invalid problems
p01_v1.plan ... p05_v5.plan       — 25 valid plans (5 per problem)
p01_b1.plan ... p05_b5.plan       — 25 invalid plans (5 per problem)
```

Total: 20 domains × 62 = **1240 fixture files**.

| Slot | Validity | Used at runtime? |
|---|---|---|
| `domain.pddl` | positive | `solve`, `validate_domain` (positive arm), `validate_problem`, `validate_plan`, `simulate` |
| `domain_neg.pddl` | **negative** | `validate_domain` (negative arm) |
| `p<NN>.pddl` | positive | `solve`, `validate_problem` (positive arm), `validate_plan`, `simulate` |
| `n<NN>.pddl` | **negative** | `validate_problem` (negative arm) |
| `p<NN>_v[1-5].plan` | positive | `validate_plan` (positive arm), `simulate` (v1 only) |
| `p<NN>_b[1-5].plan` | **negative** | `validate_plan` (negative arm) |

## Bug taxonomies

PR-3 expands the original 2/4/1 taxonomies. Bug categories are distributed across the 20 domains so models can't pattern-match a single shape. See `tools/_taxonomies.py` for the implementation.

### Invalid-domain (1 per domain)

Three candidate mutators tried in order; first one the validator rejects becomes `domain_neg.pddl`:

1. malformed S-expression (extra closing paren)
2. effect uses undeclared predicate
3. `:predicates` block stripped (action effects/preconditions dangle)

### Invalid-problem (5 per domain)

Six candidate mutators applied to `p01.pddl`; first 5 the validator rejects become `n01..n05.pddl`:

1. missing `:goal`
2. object in `:init` not in `:objects`
3. `:goal` references undefined predicate
4. malformed S-expression (extra closing paren)
5. `:objects` block stripped (`:init` references all become undefined)
6. `:init` block stripped (goal unreachable from empty state)

### Invalid-plan (5 per problem)

Four candidate mutators applied to `pNN_v1.plan`; first 5 the validator rejects (with retries on different RNG seeds for diversity) become `pNN_b1..b5.plan`. Padded with extra-truncation variants when the candidate pool exhausts:

1. truncate-tail (drop last 1-3 actions → goal-not-achieved)
2. drop-step-k (remove a mid-plan action → precondition-fails-at-step-k)
3. swap-args (swap first two args of a ≥2-arg action → semantically-asymmetric error)
4. duplicate-step (insert duplicate of an existing action → typically a precondition violation)

Action names + arity always remain valid PDDL syntax; invalidity is semantic.

## Ground truth and fail-fast validation

At startup, `pddl_eval.domains.generate_ground_truth()` calls the pddl-copilot MCP oracle on every loaded problem. For each (domain, problem) it produces:

```python
{
    "domain_valid": bool, "problem_valid": bool, "plan_valid": bool,
    "solvable": bool, "plan": list[str], "trace": dict | None,
    "valid_plans": [{"plan": str, "plan_valid": bool}, ...],   # length 5
}
```

Plus a `_negatives` slot per domain containing the validated negative fixtures.

**Fail-fast rule**: any negative that validates as `valid=True` (or `None`), or any committed `valid_plan` that validates as `valid=False`, aborts startup with `SystemExit` naming the offending file. This guarantees every sweep starts from a fixture set that is internally consistent with the validator.

## Plan diversity

For each (domain, valid problem) we generate 5 valid plans:

- **Classical**: invoke `classic_planner` with up to three Fast Downward strategies (`lazy_greedy_cea`, `astar_lmcut`, `lazy_greedy_ff`); pad with duplicates of the canonical plan when fewer distinct plans are returned.
- **Numeric**: ENHSP has fewer alternative search algorithms; v1 is taken as canonical and v2..v5 are duplicates. The graded count remains 5 per problem; per-call grading robustness is maintained because each prompt variant grades the plan independently.

This spec-conformant duplication is documented in the Decisions log (FRAMEWORK_EXTENSION_PLAN.md §5) so reviewers know v1..v5 are not always semantically distinct on numeric domains.
