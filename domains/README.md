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

All 10 domains have `domain_valid=True`, `problem_valid=True`, return a non-empty plan from the solver, and the shipped `p01.plan` passes plan validation (see CHANGELOG entry for `pyval` numeric goal-check fix).

| Domain | Actions | Goal kind |
|---|---|---|
| classical/barman | 30 | boolean |
| classical/blocksworld | 4 | boolean |
| classical/depots | 5 | boolean |
| classical/rovers | 12 | boolean |
| classical/satellite | 6 | boolean |
| numeric/counters | 27 | numeric `<=` |
| numeric/depot | 62 | boolean |
| numeric/farmland | 19 | numeric `>=` + weighted sum |
| numeric/pogo_stick | 12 | boolean |
| numeric/sailing | 100 | boolean |

Broken fixtures (for discriminating the no-tools `validate_*` baseline — see `development/OPEN_ISSUES.md::ISS-001`) are not yet added.
