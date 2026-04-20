# Domains

Ten benchmark PDDL domains (5 classical STRIPS + 5 numeric) used by the harness to exercise the pddl-copilot MCP tools across the 5 tasks defined in `EXPERIMENTS_FLOW.md`.

## Provenance

Copied verbatim from the paper dataset snapshot at `.local/pddl_mcp_dataset/` (Aug 2025), shipped alongside Benyamin et al., 2025 (arXiv:2509.12987). Aligning the harness's domain set with the paper's ten ensures single-task and chain sweeps reproduce the paper's coverage.

```
domains/
├── classical/           (paper: classic/)
│   ├── barman/
│   ├── blocksworld/
│   ├── depots/
│   ├── rovers/
│   └── satellite/
└── numeric/
    ├── counters/
    ├── depot/           (singular — paper's numeric split; distinct from classical `depots`)
    ├── farmland/
    ├── pogo_stick/
    └── sailing/
```

Each domain has exactly three files:

| File | Source | Used at runtime? |
|---|---|---|
| `domain.pddl` | paper `domain.pddl` | Yes — loaded by `load_domains()` |
| `p01.pddl` | paper `problem.pddl` | Yes — loaded by `load_domains()` |
| `p01.plan` | paper `plan.solution` | No — reference artifact for manual cross-check |

## Naming convention

- Problem files: `p01.pddl`, `p02.pddl`, … matching the `p*.pddl` glob in `run_experiment.py:load_domains`. The paper dataset ships one problem per domain, so every domain here currently has only `p01`.
- Reference plans: `pNN.plan` alongside `pNN.pddl`.

## Ground truth

At startup, `generate_ground_truth()` calls the pddl-copilot MCP oracle on every loaded problem and produces a dict with `{domain_valid, problem_valid, plan_valid, solvable, plan, trace}` per problem. The paper-shipped fixtures are *expected* to be all-valid, but this is not strictly enforced — the printed ground-truth summary (`<domain>/<problem>: solvable/unsolvable (domain_valid=... ...)`) surfaces any drift for manual review.

The paper's `plan.trajectory` (Lisp-like `(:init ... :state ...)` text) is deliberately not committed — the oracle regenerates a MCP-JSON trace at runtime for the simulate task's byte-equal comparison at `run_experiment.py:856`. Committing the Lisp-text file would be incompatible with that check.

### Per-domain validation status (2026-04-20, via user-scoped pddl-copilot plugin)

All 10 domains have `domain_valid=True`, `problem_valid=True`, and return a non-empty plan from the solver. Plan validity against the goal:

| Domain | Plan source checked | plan_valid | Notes |
|---|---|---|---|
| classical/barman | fresh `classic_planner` | ✓ | 28 actions, all goals satisfied |
| classical/blocksworld | fresh `classic_planner` | ✓ | 4 actions |
| classical/depots | fresh `classic_planner` | ✓ | 5 actions |
| classical/rovers | fresh `classic_planner` | ✓ | 12 actions |
| classical/satellite | fresh `classic_planner` | ✓ | 6 actions |
| numeric/counters | **both paper `p01.plan` and fresh `numeric_planner`** | ✗ | Goal `c0<c1<c2<c3<c4` unmet. Paper-shipped `plan.solution` also fails the same goal check. |
| numeric/depot | fresh `numeric_planner` | ✓ | 111 actions |
| numeric/farmland | **both paper `p01.plan` and fresh `numeric_planner`** | ✗ | All `(1 <= x(farmN))` goals unmet. Paper-shipped `plan.solution` also fails. |
| numeric/pogo_stick | fresh `numeric_planner` | ✓ | 10 actions, `have_pogo_stick` achieved |
| numeric/sailing | fresh `numeric_planner` | ✓ | 82 actions, both people saved |

**Implication.** `counters/p01` and `farmland/p01` produce `gt["plan_valid"]=False` on every run. The harness handles this gracefully — `run_single_task_experiment` skips `validate_plan`/`simulate` tasks for unsolvable-plan problems (`run_experiment.py:1053`) — but these two will also skew `validate_plan` evaluations when they run. See `development/OPEN_ISSUES.md::ISS-014` for the open question of whether to patch the problems, drop the two domains, or mark them as intended-invalid fixtures.

Broken fixtures (for discriminating the no-tools `validate_*` baseline — see `development/OPEN_ISSUES.md::ISS-001`) are not yet added.
