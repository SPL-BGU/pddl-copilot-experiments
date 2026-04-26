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

Each domain has six files:

| File | Source | Validity | Used at runtime? |
|---|---|---|---|
| `domain.pddl` | paper `domain.pddl` | positive | Yes — loaded by `load_domains()` |
| `p01.pddl` | paper `problem.pddl` | positive | Yes — loaded by `load_domains()` |
| `p01.plan` | paper `plan.solution` | positive | Reference artifact (not loaded into prompts) |
| `domain_0.pddl` | hand-authored | **negative** | Yes — joins `validate_domain` only |
| `p01_0.pddl` | hand-authored | **negative** | Yes — joins `validate_problem` only |
| `p01_0.plan` | hand-authored | **negative** | Yes — joins `validate_plan` only |

## Naming convention

- **Positives:** `p01.pddl`, `p02.pddl`, … matching the `p*.pddl` glob in `run_experiment.py:load_domains` (the glob filters out `_0`-suffixed files). The paper dataset ships one problem per domain, so every domain currently has only `p01`.
- **Negatives:** validity-neutral filenames using a `_0` suffix. The LLM never sees a path (prompts pass *content*, not paths), but using a numeric-variant suffix instead of `bad_*` keeps that defense-in-depth.
- Reference plans: `pNN.plan` alongside `pNN.pddl`.

## Negative fixtures (task-targeted)

Each negative file joins **exactly one** `validate_*` task, paired with the
positive counterparts for the other layers it doesn't test:

| File | Target task | Pairing | Bug taxonomy |
|---|---|---|---|
| `domain_0.pddl` | `validate_domain` | with positive `p01.pddl` (when validator wants both) | Missing closing paren · undefined predicate in precondition · malformed `:parameters` · effect uses undeclared predicate |
| `p01_0.pddl` | `validate_problem` | with positive `domain.pddl` | Object in `:init` not in `:objects` · missing `:goal` · `:goal` references undefined predicate · malformed S-expression |
| `p01_0.plan` | `validate_plan` | with positive `domain.pddl` + `p01.pddl` | (a) goal-not-achieved · (b) precondition-fails-at-step-k. Action names + arity always valid. |

Bug categories are distributed across the 10 domains so models can't pattern-match a single shape.

At startup, `generate_ground_truth()` calls `validate_pddl_syntax` on every negative and **fails fast (SystemExit)** if any negative validates as True — preventing a silently-broken fixture from contaminating results.

## Ground truth

At startup, `generate_ground_truth()` calls the pddl-copilot MCP oracle on every loaded problem and produces a dict with `{domain_valid, problem_valid, plan_valid, solvable, plan, trace}` per positive problem and `_negatives.{domain,problem,plan}` slots per domain. The paper-shipped positives are *expected* to be all-valid, but this is not strictly enforced — the printed ground-truth summary surfaces any drift for manual review. Negatives, in contrast, are strictly enforced: any negative that the validator does not flag as `valid=False` aborts startup with `SystemExit` naming the offending file.

The paper's `plan.trajectory` (Lisp-like `(:init ... :state ...)` text) is deliberately not committed — the oracle regenerates a MCP-JSON trace at runtime for the simulate task's byte-equal comparison at `run_experiment.py:856`. Committing the Lisp-text file would be incompatible with that check.

### Per-domain validation status (2026-04-20, via user-scoped pddl-copilot plugin)

All 10 positive fixtures have `domain_valid=True`, `problem_valid=True`, return a non-empty plan from the solver, and the shipped `p01.plan` passes plan validation (see CHANGELOG entry for `pyval` numeric goal-check fix). All 30 negative fixtures (`domain_0.pddl`, `p01_0.pddl`, `p01_0.plan` × 10 domains) validate as `valid=False`, verified at every harness startup.

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

Negative fixtures landed 2026-04-26 alongside the re-enable of no-tools `validate_*`; see `development/CHANGELOG.md` for the dated entry. With balanced 1:1 ground truth, the no-tools `validate_*` grader becomes discriminative (constant-VALID strategies score ~50%, capability shows up above that).
