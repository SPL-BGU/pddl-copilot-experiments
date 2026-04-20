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

All 10 domains have `domain_valid=True`, `problem_valid=True`, and return a non-empty plan from the solver. Plan validity reported by the validator:

| Domain | Plan source | validator verdict | Arithmetic truth | Notes |
|---|---|---|---|---|
| classical/barman | fresh `classic_planner` | ✓ | ✓ | 28 actions |
| classical/blocksworld | fresh `classic_planner` | ✓ | ✓ | 4 actions |
| classical/depots | fresh `classic_planner` | ✓ | ✓ | 5 actions |
| classical/rovers | fresh `classic_planner` | ✓ | ✓ | 12 actions |
| classical/satellite | fresh `classic_planner` | ✓ | ✓ | 6 actions |
| numeric/counters | paper + fresh | **✗** | **✓** | **Validator bug** — final state is strictly increasing with gaps ≥1; all four `<=` goals are arithmetically satisfied but validator reports all unmet. See `OPEN_ISSUES.md::ISS-014`. |
| numeric/depot | fresh `numeric_planner` | ✓ | ✓ | 111 actions; boolean goals |
| numeric/farmland | paper + fresh | **✗** | **✓** | **Validator bug** — all 15 `>= 1` goals met (every x≥1), weighted sum = 31.0 ≥ 30.8 requirement. Validator reports all 16 unmet. See `OPEN_ISSUES.md::ISS-014`. |
| numeric/pogo_stick | fresh `numeric_planner` | ✓ | ✓ | 10 actions; boolean goal |
| numeric/sailing | fresh `numeric_planner` | ✓ | ✓ | 82 actions; boolean goals |

**Implication.** The oracle ground truth is wrong on `counters/p01` and `farmland/p01` because the `pyval`-backed validator miscomputes numeric `<=` / `>=` goals. The two fixtures are actually valid. Agents whose reasoning is correct on these problems will mismatch the (wrong) GT and be scored as failures. Until the upstream `pyval` bug is fixed (tracked in `ISS-014`), interpret counters / farmland numbers cautiously — they measure "agreement with the buggy validator" more than plan correctness.

Pattern: the bug affects numeric `<=` / `>=` goal checks. Boolean goals (pogo_stick, sailing, depot, all classical) work correctly.

Broken fixtures (for discriminating the no-tools `validate_*` baseline — see `development/OPEN_ISSUES.md::ISS-001`) are not yet added.
