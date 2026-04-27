# Framework Extension Plan — 2026-04-27

Forward-looking plan for the next round of methodological extension on top of the
2026-04-26 negative-fixtures landing. This document is the plan-of-record; the
implementation lives on a yet-to-be-branched `framework-extension-v2` branch
that will merge to `main` after the four PRs below land in order.

Reference: Benyamin et al., 2025 (arXiv:2509.12987); EXPERIMENTS_FLOW.md is the
methodology reference and will be updated in lockstep with each PR.

---

## 1. Goals

Six requirements drive this round (raised 2026-04-27):

1. **Wider problem coverage per domain** — each (valid) domain ships 5 valid
   problems and 5 invalid problems; each valid problem ships 5 valid plans
   and 5 invalid plans; each domain still ships exactly 1 valid + 1 invalid
   domain file. Replaces today's "1 positive + 1 task-targeted negative" set.
2. **Wider domain coverage** — extend from 10 domains (5 classical + 5 numeric)
   to 20 domains (10 classical + 10 numeric). The existing 10 stay; we add 5
   classical and 5 numeric from IPC benchmark suites.
3. **No-tools runs in thinking mode** — the existing `--think off` gate on the
   no-tools condition is lifted; thinking content is captured separately from
   the graded response so it does not pollute `extract_verdict` /
   `extract_plan_lines`; thinking process is documented in the per-record
   JSON; the context window is capped to keep thinking-spiral wallclock
   bounded.
4. **No-tools runs `simulate`** — the `simulate` task is currently dropped
   from the no-tools sweep because the keyword-only grader is
   non-discriminative. The no-tools condition gains structured-output
   enforcement (Ollama `format=<json_schema>`), which lets us grade simulate
   trajectories against the oracle by deep-equality just like the with-tools
   path. This makes "no-tools" effectively "no-PDDL-tools": the model still
   has format-enforcement available, but no planning / validation / simulation
   tools.
5. **Token accounting in the per-record output** — every evaluation records
   `prompt_eval_count` + `eval_count` summed across tool-call turns, so the
   paper can quantify the token-reduction story (with-tools shrinks the
   prompt by externalising plan / state / verdict computation).
6. **Variant pruning to v0 / v1 / v2** — already landed (commit `b7af180`,
   `ACTIVE_PROMPT_VARIANTS = (0, 1, 2)`). v3 and v4 stay commented in the
   `PROMPT_TEMPLATES` list so historical `prompt_variant` indices remain
   stable for byte-comparable analysis of pre-2026-04-27 results.

---

## 2. Already landed / in-flight (pre-PR-1 context)

These are not part of this plan's PRs; they are noted so the plan reads
correctly against the current `experiment-expension` HEAD.

| Change | Where | Status |
|---|---|---|
| `ACTIVE_PROMPT_VARIANTS = (0, 1, 2)` (was `(0, 1, 3)`) — keeps v2 for its question-form linguistic-diversity property | `run_experiment.py:202` | committed `b7af180` |
| Per-variant summary metrics added to single-task table | `run_experiment.py:1788` | committed `b7af180` |
| `gpt-oss:120b` removed from cluster pack; `Qwen3.5:35b` substituted (5-model rtx_pro_6000 pack, peak ~30 GB resident) | `cluster-experimenting/submit_with_rtx.sh:--all` | landed 2026-04-27 alongside cis-ollama removal |
| cis-ollama path retired; sole submit is `submit_with_rtx.sh` on hard-pinned `rtx_pro_6000:1` | `cluster-experimenting/`, `run_experiment.py`, `run_background.sh`, `.claude/skills/cluster-ops/` | landed 2026-04-27 |
| Chain phase shortened from `chain_lengths = (2, 3, 4, 5)` to `(2, 3)` — length-3 chains are informative enough for the multi-task dynamic and cuts chain-phase wallclock ~50% | `run_experiment.py:1390`, `cluster-experimenting/run_condition_rtx.sbatch` | planned, not yet in tree |

PR-1's smoke-equality gate runs against whatever is committed at the time of
PR-1's branch point, so any of the above that lands before PR-1 is part of
the baseline anchor.

---

## 3. Approach — refactor-first, four PRs, smoke-as-regression-anchor (Approach C)

Decision after brainstorm 2026-04-27. Two competing approaches were considered:

- **Big-Bang (A)** — one ~4500-LOC PR + 1180 new fixture files. Rejected: no
  per-step regression anchor, hard to bisect if the cluster smoke run
  uncovers a problem, and the refactor + fixtures + grader pivot land
  entangled.
- **Phased fixtures-first (B)** — four PRs but refactor lands last. Rejected:
  refactor against an aged baseline is harder to prove safe; subsequent
  feature PRs accumulate in monolithic `run_experiment.py` first.
- **Phased refactor-first (C, chosen)** — refactor lands first as a
  zero-behavior-change PR with a byte-equality smoke anchor; subsequent
  feature PRs touch one module at a time and use the prior PR's smoke as
  their regression target. The methodological pivot (no-PDDL-tools
  format-grading) lands last on stable infrastructure.

### 3.1 Smoke-as-anchor mechanism

A new `--smoke` CLI flag runs a fixed slice — 1 domain × 1 problem × 1
prompt variant × all 5 tasks × both conditions × both think modes — across
all 5 cluster models. ≈100 evaluations, ≈10 minutes wallclock on cluster.
Output goes to `results/smoke_<pr-tag>_<sha>/` (distinct prefix so it cannot
be confused with a real sweep; gitignored separately from `results/`).

For each PR after PR-1:

1. Run `--smoke` on the PR head.
2. Diff `summary.json` against the previous PR's `smoke_<sha>/summary.json`,
   modulo timestamp / host fields.
3. The diff's expected delta is enumerable up-front: PR-2 adds new fields
   only; PR-3 adds new (domain, problem) rows only; PR-4 changes only the
   no-PDDL-tools rows. Any unexpected delta blocks the merge.

Default smoke domain: `blocksworld` (smallest classical, fastest oracle GT,
broadest tool-call coverage).

A secondary `--smoke-shuffle` flag runs randomized model × task coverage
(each (model, task) gets one random domain assigned) so the union still
covers the full {5 models} × {5 tasks} × {2 conditions} × {2 think modes}
cell grid with one sample each. Used as a final compatibility check before
committing to the full cluster sweep.

### 3.2 PR sequencing

#### PR-1 — Refactor `run_experiment.py` → `pddl_eval/` package; add `--smoke` and `--shard i/N` flags

Module split (no semantic change):

| Module | Owns |
|---|---|
| `pddl_eval/prompts.py` | `PROMPT_TEMPLATES`, `ACTIVE_PROMPT_VARIANTS`, `WITH_TOOLS_SYSTEM`, `WITHOUT_TOOLS_SYSTEM`, `_GUIDED_SUFFIX` |
| `pddl_eval/domains.py` | `load_domains`, `generate_ground_truth`, `_build_plan_str` |
| `pddl_eval/chat.py` | `chat_with_tools`, `chat_without_tools`, `_build_chat_kwargs`, `_response_done_reason`, `MCPPlanner` |
| `pddl_eval/scoring.py` | `extract_plan_lines`, `extract_verdict`, `check_success`, `_validate_model_plan`, `_classify_step_failure`, `_apply_truncation_override`, all `FR_*` constants |
| `pddl_eval/runner.py` | `evaluate_one`, `run_single_task_experiment`, `run_chain_experiment`, `_format_progress` |
| `pddl_eval/summary.py` | `wilson_ci`, `summarize_single_task`, `summarize_chains`, `print_*`, `save_results` |
| `run_experiment.py` | CLI entry only (~150 LOC): `argparse` + `async_main` + `main` |

CLI additions:

- `--smoke` — runs the smoke slice described in §3.1; writes to
  `results/smoke_<run-id>/`; sets `--num-variants 1`, `--chain-samples 0`
  internally.
- `--smoke-shuffle` — randomized-coverage variant of `--smoke`.
- `--shard <i>/<N>` — hash `(model, task, domain_name, problem_name,
  prompt_variant)` modulo N, run only shard i (0-indexed). Enables N-way
  parallelism on cluster for the full sweep. Default `1/1` (no sharding).

Smoke gate for PR-1: byte-equal `summary.json` against pre-refactor `main`
HEAD modulo timestamp / host / hostname-dependent fields. The refactor PR
cannot merge if any graded outcome (`success`, `failure_reason`,
`tool_selected`, `truncated`, `done_reason`) differs.

Estimated diff: ~2500 LOC moved + ~150 LOC new (CLI flags + smoke runner
helper). Zero behavior change.

##### PR-1 drift from spec (recorded 2026-04-27 during implementation)

| Drift | Why | Where |
|---|---|---|
| Added `--domains DNAME ...` and `--problems PNAME ...` general filters | No domain-level filter existed in `run_experiment.py` before PR-1; without one, `--smoke` cannot constrain to (blocksworld, p01). General-purpose flag is more useful long-term than smoke-specific knobs and costs ~10 LOC. | `run_experiment.py:argparse + async_main` post-`load_domains` filter |
| `--shard` skips chain phase entirely on shard ≠ 0 (chains run only on shard 0) | Chain units are trajectories, not the 5-tuple key; SHA-256 partitioning the trajectory by its first step would skew per-cell counts. PR-1 spec was silent on the interaction. | `run_experiment.py:async_main` (`if args.chains and args.shard_i == 0 ...`) |
| `_safe_json_loads` and `_parse_validation_verdict` placed in `pddl_eval/chat.py` rather than `pddl_eval/domains.py` | Both helpers are consumed by `scoring.check_success` (4 sites) AND `domains.generate_ground_truth`. Putting them in `domains` would force a `scoring → domains` edge that risks a cycle when scoring helpers grow; placing them in `chat` (the lowest leaf in the package DAG) keeps `domains` and `scoring` as siblings. | `pddl_eval/chat.py` |
| `TaskResult` dataclass placed in `pddl_eval/runner.py` (the producer module); `summary` imports it from `runner` | PR-1 spec was silent on placement. Alternative would have been a 7th `pddl_eval/types.py` module just for one dataclass; placing it with its producer keeps the DAG simpler. | `pddl_eval/runner.py` |
| `run_experiment.py` is 626 LOC after the split (estimate was ~150) | The CLI shim retains: argparse (~150 LOC), validation/parsing (~50), smoke output-dir + git-sha helper (~40), the smoke think-mode loop wrapper inside `async_main` (~120 LOC), and the explicit re-export shim for `tests/test_*.py` (~100 LOC). Each section is the minimum needed for behaviour parity; merging them into submodules would push CLI logic out of `run_experiment.py`'s natural home. | `run_experiment.py` |

#### PR-2 — Token + thinking instrumentation

Changes:

- `TaskResult` gains `tokens: dict = {prompt: int, completion: int, total:
  int, turns: int}` populated from each `client.chat()` response's
  `prompt_eval_count` + `eval_count`, summed across tool-call loops in
  `chat_with_tools`. `total_duration_ns` and `eval_duration_ns` also
  captured for tokens-per-second analysis.
- `TaskResult` gains `thinking: str = ""` populated from
  `response["message"].thinking` (Ollama 0.6+ structured field). Empty
  string when the model does not emit thinking content. Capped at
  `THINKING_SNAPSHOT_LEN = 4096` chars to bound JSON record size; full
  content reproducible from re-running the prompt.
- `pddl_eval/scoring.py::extract_verdict` and `extract_plan_lines` gain a
  defensive `<think>...</think>` regex strip on `content` before parsing —
  safety net for models that inline the block in `content` rather than
  using the structured field.
- New failure tag `FR_THINK_OVERFLOW` — applied when `done_reason ==
  "length"` AND `thinking` is non-empty AND `content` is empty (the budget
  was consumed entirely by reasoning). Distinguishes from generic
  `FR_TRUNCATED_NO_ANSWER`.
- The `--think off` gate at `run_experiment.py:1893` (currently aborts
  no-tools runs with `--think on/default`) is **lifted**. With thinking
  captured separately and not contaminating graded outcomes, no-tools
  thinking-mode is now a valid run.
- `num_ctx` cap: introduce `--num-ctx-thinking` (default 16384) used only
  when `think != False`. The default `num_ctx` (8192) stays for
  `think = False` and tool-condition runs. Caps the qwen3 / gpt-oss
  thinking-spiral while giving thinking models enough headroom to finish.
- Result schema docs: `EXPERIMENTS_FLOW.md §9` updated to document the
  new fields.

Smoke gate for PR-2: existing graded fields (`success`, `failure_reason`,
`tool_selected`, `truncated`, `done_reason`) byte-equal to PR-1's smoke;
new fields (`tokens.*`, `thinking`) non-null on every row. Lifting the
`--think off` gate is verified by adding `think=on, condition=no-tools`
cells to the smoke run and asserting they produce non-zero `n` per cell.

Estimated diff: ~200 LOC across `pddl_eval/{chat,scoring,runner}.py` and
`run_experiment.py`.

#### PR-3 — Fixture buildout to 20 domains × (5 valid + 5 invalid) problems × (5 valid + 5 invalid) plans

##### 3.3.1 New domains (5 classical + 5 numeric)

Selected for IPC track availability and existing planner support
(`classic_planner` / `numeric_planner` plugins). Final picks confirmed
during PR-3's ground-truth pass:

| Type | Domain | IPC track | Why |
|---|---|---|---|
| Classical | gripper | IPC-1998 | smallest STRIPS, 1 action × N balls |
| Classical | logistics | IPC-1998/2000 | mixed-mode transport, 6 actions |
| Classical | miconic | IPC-2000 | elevator, conditional preconditions |
| Classical | parking | IPC-2008-sat | object-permanence, dense state |
| Classical | tpp | IPC-2006 | "travelling purchaser", goods + markets |
| Numeric | zenotravel-numeric | IPC-2002-numeric | fuel-consumption, classic numeric benchmark |
| Numeric | transport-numeric | IPC-2008-numeric | weighted-cost transport |
| Numeric | settlers | IPC-2002-numeric | resource production graph |
| Numeric | drone | numeric-track community | battery + payload constraints |
| Numeric | plant-watering | numeric-track community | continuous resource decay |

Final list locks during PR-3; substitutions allowed if any domain fails
ground-truth on `pfile1..5` under default planner timeouts.

##### 3.3.2 Fixture layout per domain

Flat-file layout under `domains/<type>/<domain>/`, replacing today's
`p01.pddl` + `p01_0.pddl` + `domain_0.pddl` shape:

```
domain.pddl                 — 1 valid domain
domain_neg.pddl             — 1 invalid domain (was domain_0.pddl)
p01.pddl ... p05.pddl       — 5 valid problems (was just p01.pddl)
n01.pddl ... n05.pddl       — 5 invalid problems (was just p01_0.pddl)
p01_v1.plan ... p01_v5.plan — 5 valid plans for p01 (was just p01.plan)
p01_b1.plan ... p01_b5.plan — 5 invalid plans for p01 (was just p01_0.plan)
... (same _v1..v5, _b1..b5 grid for p02..p05)
```

Per domain: 1 + 1 + 5 + 5 + 25 + 25 = **62 PDDL/plan files**. Across 20
domains: **1240 fixtures**. Existing fixtures rename in-place during PR-3:
`domain_0.pddl` → `domain_neg.pddl`; `p01_0.pddl` → `n01.pddl`; `p01_0.plan`
→ `p01_b1.plan`; existing `p01.pddl` stays; existing `p01.plan` becomes
`p01_v1.plan` and the four other `p01_v[2-5].plan` files are generated.

##### 3.3.3 Plan diversity (5 valid plans per problem)

For each (domain, valid problem):

- Classical: invoke `classic_planner` with three Fast Downward strategies
  (`lazy_greedy_cea`, `astar_lmcut`, `lazy_greedy_ff`) → up to 3 distinct
  plans; supplement to 5 by hand-permuting commutative-action pairs in the
  oracle plan where the domain semantics permit.
- Numeric: ENHSP has fewer alternative search algorithms; accept duplicate
  plan content across `_v1..v5` slots when no permutation is available.
  The graded count remains 5 per problem; `validate_plan` measures the
  same plan five times per (problem, prompt_variant), which is fine for
  per-call grading robustness.

##### 3.3.4 Invalid-plan taxonomy (5 invalid plans per problem)

Extends today's two-bug taxonomy in `domains/README.md`:

1. precondition-fails-at-step-k (k varies across the 5 invalid variants)
2. goal-not-achieved-by-truncation (drop the last 1-3 actions)
3. swapped-arg-order on a commutative-looking but semantically-asymmetric action
4. missing-action (drop a required mid-plan action)
5. extra-action (insert a no-op-equivalent action that is not actually a no-op)

Action names + arity always remain valid PDDL syntax; the invalidity is
semantic (precondition / goal). Bug categories distributed across the 20
domains so models can't pattern-match on a single shape.

##### 3.3.5 Invalid-problem taxonomy (5 invalid problems per domain)

Extends today's four-bug taxonomy:

1. object in `:init` not in `:objects`
2. missing `:goal`
3. `:goal` references undefined predicate
4. malformed S-expression (extra closing paren / missing closing paren)
5. `:init` references object of wrong type (e.g. `(at robot1 ball1)` where `at` expects `(robot, room)` not `(robot, ball)`)

All five must validate as `valid=False` against `validate_pddl_syntax`;
ground-truth pass at startup `SystemExit`s on any drift.

##### 3.3.6 Loader changes

`pddl_eval/domains.py::load_domains`:

- Glob `p<NN>.pddl` for valid problems (excludes `n*.pddl` and `domain*.pddl`).
- Glob `n<NN>.pddl` for invalid problems.
- For each valid `p<NN>`: glob `p<NN>_v*.plan` (valid plans) and
  `p<NN>_b*.plan` (invalid plans).
- `domain_neg.pddl` replaces `domain_0.pddl` as the invalid-domain slot.

Returns the existing nested dict shape with `negatives` extended to lists:

```python
{
  "type": "classical",
  "domain": "(define ...)",                     # valid domain content
  "problems": {                                 # 5 entries per domain
    "p01": "(define (problem ...) ...)",
    ...
  },
  "negatives": {
    "domain": "(define ...)",                   # 1 invalid domain
    "problems": ["..."] * 5,                    # 5 invalid problems
    "plans_per_problem": {                      # 5 valid + 5 invalid plans per p<NN>
      "p01": {"valid": ["..."] * 5, "invalid": ["..."] * 5},
      ...
    },
  },
}
```

`generate_ground_truth` runs validation across all 1240 fixtures; expected
≈30s on the cluster login node (validators run locally — no Ollama call
needed). Any negative that validates True or any positive that validates
False halts startup with `SystemExit` naming the offending file.

##### 3.3.7 Compute scaling

Per (model, condition, think) cell, evaluation counts grow:

| Task | Today | After PR-3 |
|---|---|---|
| solve | 10 (10 dom × 1 prob) | 100 (20 dom × 5 prob) |
| validate_domain | 20 (10 pos + 10 neg) | 40 (20 pos + 20 neg) |
| validate_problem | 20 (10 pos + 10 neg) | 200 (100 pos + 100 neg) |
| validate_plan | 20 (10 pos + 10 neg) | 1000 (500 pos + 500 neg) |
| simulate | 10 (with-tools only) | 500 (100 pos × 5 plans) — with-tools; PR-4 adds no-tools side |

Per cell: 80 evals → 1840 evals (≈23×). With 3 prompt variants: 240 →
5520 evals per cell. Across 5 models × 2 conditions × 2 think modes = 20
cells: ≈110,400 single-task evaluations per full sweep (was ≈4800).

This is the binding constraint that drives the `--shard i/N` flag (PR-1)
and the cluster submission redesign described in §4.

Smoke gate for PR-3: ground-truth pass over all 1240 fixtures completes
without `SystemExit`; `--smoke` on default `blocksworld` produces graded
outcomes byte-equal to PR-2 on the existing problems (`p01..p01`,
`n01..n01`); new problems (`p02..p05`, `n02..n05`) get a one-time
human-spot-check (10 min) since they have no anchor. PR-3 also runs
`generate_ground_truth` on the new 10 domains and inspects the printed GT
summary for solvability + non-zero plan counts.

Estimated diff: ~1180 new files in `domains/`, ≈50 LOC in
`pddl_eval/domains.py` (loader + ground-truth extension), ≈30 LOC in
`pddl_eval/runner.py` (negative-job builder generalization from
single-fixture to 5-fixture per kind).

#### PR-4 — No-PDDL-tools = `format=<json_schema>`; lift simulate skip

The methodologically-novel piece. Lands last on stable infrastructure.

##### 3.4.1 Per-task Pydantic schemas

New `pddl_eval/schemas.py`:

```python
class SolveResponse(BaseModel):
    plan: list[str]   # each line "(action arg1 arg2 ...)"

class ValidateResponse(BaseModel):
    verdict: Literal["VALID", "INVALID"]
    reason: str       # 1-3 sentence justification, ungraded

class SimulateResponse(BaseModel):
    trajectory: list[StateStep]

class StateStep(BaseModel):
    step: int
    action: str
    state: StateSnapshot

class StateSnapshot(BaseModel):
    boolean: list[str]               # sorted predicate strings
    numeric: dict[str, float]        # fluent name → value
```

##### 3.4.2 Flow change

`chat_without_tools` gains an optional `format=<json_schema>` parameter,
populated per task from the schemas above. Ollama enforces the schema
during sampling. The model still emits a single `message.content` string
(JSON-shaped) — no `tool_calls[]` entry, no change to `tool_selected`
semantics for the no-tools branch (`tool_selected = None`).

`pddl_eval/scoring.py::check_success` for the no-PDDL-tools branch:

- `solve` — parse `SolveResponse.plan`, send to pyvalidator via
  `_validate_model_plan`, require `valid=True`.
- `validate_*` — parse `ValidateResponse.verdict`, compare to ground truth.
- `simulate` — parse `SimulateResponse.trajectory`, normalize (sort
  predicate strings within each step's `boolean`, lowercase, strip
  whitespace), compare against the same-normalized `gt["trace"].trajectory`.
  This grader is identical in spirit to the with-tools simulate equality
  check at `run_experiment.py:1017`; the normalizer extends to both
  sides so they remain comparable.

Free-text extractors (`extract_plan_lines`, `extract_verdict`) are kept
as fallback paths when format=json parsing fails, surfaced via new
`FR_FORMAT_PARSE_FAIL` failure tag. This guards against degenerate
behavior on tiny models (`qwen3:0.6b`, `Qwen3.5:0.8B`) where format
constraints may produce empty / repeating output.

##### 3.4.3 Skip removals

- `if not with_tools and task == "simulate": continue` at
  `run_experiment.py:1266` — **removed**. No-tools simulate is now graded.
- `if args.conditions in ("no-tools", "both") and args.think != "off"`
  early-exit at `run_experiment.py:1893` — already lifted in PR-2.
- Chain phase still skips no-tools (chains require artifact propagation
  across steps; format=json grading does not change this — the chain
  needs the *content* of an earlier step's plan / trace fed into the next
  step, which is honest only when the model has tools to produce it).

##### 3.4.4 Naming

- CLI / summary tables / EXPERIMENTS_FLOW.md user-facing label:
  `no-tools` → `no-pddl-tools`. The `--conditions` enum stays
  `tools | no-tools | both` for back-compat — internal label unchanged so
  old result JSON parses identically.
- `with_tools: bool` in the JSON schema unchanged — the 2026-04 result
  corpus reads cleanly under PR-4 analysis.
- EXPERIMENTS_FLOW.md §11 paper-diff row updated to document the format
  pivot; §4.2 rewritten to describe what no-PDDL-tools means; §3 simulate
  row updated.

Smoke gate for PR-4: with-tools rows byte-equal to PR-3's smoke; new
no-PDDL-tools simulate rows present with `n > 0` and `FR_FORMAT_PARSE_FAIL`
rate < 30%. `--smoke-shuffle` runs as a final check before any cluster
sweep.

Estimated diff: ~300 LOC across `pddl_eval/{schemas,chat,scoring,runner}.py`
+ EXPERIMENTS_FLOW.md updates.

---

## 4. Cluster submission strategy after PR-4 lands

The 23× compute scale-up means a single (model, think, condition) job no
longer fits in cluster wallclock. Submission plan:

1. `bash cluster-experimenting/submit_with_rtx.sh --smoke` runs the smoke
   slice on all 5 models in one job (~10 min wallclock) and gates the
   sweep on its summary having zero `FR_EXCEPTION` / `FR_FORMAT_PARSE_FAIL`.
2. `bash cluster-experimenting/submit_with_rtx.sh --all --shard i/N` for
   `i in 0..N-1` and `N = 4` issues 5 model-packs × 2 think modes × 2
   conditions × 4 shards = **80 jobs/sweep**. Each shard runs a hash-
   selected slice, ~2h wallclock under cluster fairshare limits.
3. Chain phase runs only after all single-task shards complete (chain
   denominator must include every problem; sharding the chain phase by
   `(model, chain_length)` is fine since chain samples are independent).

The submit script grows a `--shard` passthrough; the sbatch template
gains a `SHARD_INDEX` / `SHARD_COUNT` env-var pair forwarded to
`run_experiment.py`. The sharded smoke gate is the only protection against
80 jobs all failing identically — its content is non-negotiable.

---

## 5. Decisions log

Trade-offs with rationale, recorded so future readers don't have to
reconstruct the brainstorm.

| Decision | Why |
|---|---|
| Refactor as PR-1, not PR-4 | Byte-equality smoke gate makes the refactor provably safe; subsequent feature PRs touch one module at a time. The "refactor before knowing the new shape" objection doesn't apply — the brainstorm settled the module boundaries up front. |
| Single fixture-buildout PR (not domain-by-domain) | Loader changes are uniform across all 20 domains; merging fixtures in halves would require two loader-compatibility migrations. PR-3's smoke runs only on `blocksworld` (unchanged) so existing-domain regression is preserved regardless of new-domain count. |
| Flat naming (`p01..p05`, `n01..n05`, `pNN_v[1-5]`, `pNN_b[1-5]`, `domain_neg`) | Filename conveys validity-neutrality: LLM never sees a path (prompts pass content), and the suffix scheme uses single-char tags (`v`, `b`, `n`, `_neg`) that read as variant indices, not labels. Subdirectory layout (`problems/`, `plans/`) was rejected — over-organized for ≤62 files per domain. |
| Accept duplicate plan content across numeric `_v1..v5` slots | ENHSP search-strategy diversity is limited; per-problem hand-crafted permutations don't scale to 100 valid plans. Graded count is what matters for per-call robustness; document as a known limitation. |
| Format=json (Ollama `format=`) is not a "tool call" | The constraint is sampling-time, not function-invocation-time. `tool_calls[]` stays empty; `tool_selected` stays `None` for the no-PDDL-tools branch. Comparison fairness with with-tools is preserved because with-tools tools also enforce structured input/output via MCP schema. |
| `no-tools` label → `no-pddl-tools` (user-facing only) | The condition no longer means "raw text generation". The internal `with_tools: bool` schema field stays the same so the 2026-04 result corpus reads cleanly under PR-4 analysis. |
| `--num-ctx-thinking` separate from `--num-ctx` | Thinking models need ~2× context budget; non-thinking runs don't. Bifurcating the cap lets the same `num_predict` per-task limit hold across both modes without starving thinking models. |
| 4-way sharding (`N=4`), not 8 or 16 | At ≈5520 evals/cell × ≈3s/eval, N=4 yields ≈70-min shards — comfortably under the 2h wallclock target with margin for slow models (gemma4:31b). N=8 doubles cluster job count without proportional speedup once Ollama serve startup amortizes. |
| Chain phase pruned to lengths (2, 3) — not (2, 3, 4, 5) | Chain wallclock scales superlinearly with length (each step compounds context); length-3 captures the multi-task dynamic without the length-5 tail. Decision recorded by user 2026-04-27 on the back of cluster-26042026 chain results. Re-extend to (2, 3, 4, 5) for the final paper sweep if needed. |
| `gpt-oss:120b` dropped from cluster pack; `Qwen3.5:35b` substituted | 120b's 65 GB weights forced rtx_pro_6000 routing and added queue contention against the other 5 models. With `Qwen3.5:35b` substituted, the pack peaks at ~30 GB and runs on a single rtx_pro_6000 job under `MAX_LOADED_MODELS=1`. Pairs with the 2026-04-27 cis-ollama retirement: `submit_with_rtx.sh` is now the sole submission path with `rtx_pro_6000:1` hard-pinned for "consistency and known variables". |
| `ACTIVE_PROMPT_VARIANTS = (0, 1, 2)` not `(0, 1, 3)` | `(0, 1, 2)` wins 4/5 tasks on the closest-to-pooled-mean metric (mean abs gap 0.0045 vs 0.0051) per `checkpoints/cluster-26042026/prompt_variant_stats.md`. v2 is the only question-form variant ("Is this PDDL domain syntactically correct?"), so keeping it preserves linguistic diversity in the robustness story. |

---

## 6. Risks

- **Refactor missing a behavior change.** Mitigated by the byte-equality
  smoke gate. If the gate fails, the PR is bisected before merge.
- **IPC `pfile2..5` exceeds `num_predict=8192` on solve for slow models.**
  Caught during PR-3's ground-truth pass; mitigation is to raise the
  per-task cap or drop the largest instance per domain.
- **`format=json` degenerates on tiny models.** Caught during PR-4's
  smoke + smoke-shuffle. `FR_FORMAT_PARSE_FAIL` surfaces the rate;
  fallback through free-text extractors preserves prior behavior.
- **Plan-diversity collapse on numeric ENHSP** — see decisions log;
  documented limitation.
- **Simulate trajectory normalization mismatch between with-tools tool
  result shape and no-PDDL-tools format=json output.** Mitigation: a
  single `_normalize_trajectory(traj)` helper used on both sides.
  Explicitly tested in PR-4's smoke run.
- **80-job sweep all failing identically.** Mitigation: smoke gate must
  pass before sbatch issues any shard job. Submit script enforces this
  via a precondition check on `results/smoke_<latest>/summary.json`.
- **Chain-phase length-(2,3) is "informative enough" is an assertion
  awaiting validation.** Risk that length-4-5 chains expose a
  catastrophic-failure pattern not visible at length-3. Mitigation: keep
  the longer lengths reachable via CLI override if the paper reviewers
  ask for them; not a binding constraint for the next sweep.

---

## 7. Open questions / deferred work

- **PDDL fixture auto-cleanup pass via plugin** — user explicitly deferred:
  use `pddl-copilot/pddl-parser` to normalize tabs and other syntactic
  quirks discovered in IPC files. Not part of PR-3; runs as a one-off
  cleanup script after PR-3 lands if any GT failures surface.
- **Cluster `submit_with_rtx.sh --shard` integration** — lives in PR-1
  alongside the `--shard` Python flag; sbatch template gains
  `SHARD_INDEX` / `SHARD_COUNT` env passthrough.
- **`results/` archive convention for the legacy 10-domain corpus** —
  the 2026-04 result corpus stays under `results/cluster-2026042{6,7}/`
  and remains analyzable. No migration; new sweeps land under
  `results/cluster-2026MMDD-extended/`.
- **EXPERIMENTS_FLOW.md §6 (Domains) full rewrite** — happens in PR-3
  (fixture buildout); the §4.2 / §11 rewrites happen in PR-4
  (no-PDDL-tools).

---

## 8. Validation order summary

```
PR-1 (refactor + smoke flag + shard flag)
  └── local --smoke vs pre-refactor main HEAD          (~2 min, laptop)
  └── cluster --smoke                                  (~10 min)
  └── byte-equality diff vs anchor: zero diffs allowed
  └── merge

PR-2 (tokens + thinking)
  └── cluster --smoke                                  (~10 min)
  └── diff vs PR-1 smoke: only `tokens.*` + `thinking` columns added
  └── merge

PR-3 (1180 fixtures)
  └── ground-truth pass over 1240 files                (~30 sec)
  └── cluster --smoke (default blocksworld)            (~10 min)
  └── diff vs PR-2 smoke: existing-domain rows byte-equal
  └── manual spot-check of new-domain GT printout      (~10 min)
  └── merge

PR-4 (no-PDDL-tools format=json)
  └── cluster --smoke                                  (~10 min)
  └── cluster --smoke-shuffle                          (~20 min)
  └── diff vs PR-3 smoke: with-tools rows byte-equal,
      no-PDDL-tools rows have new graders, no `FR_FORMAT_PARSE_FAIL`
      rate > 30% on any model
  └── merge

After PR-4
  └── cluster --smoke (final pre-sweep gate)           (~10 min)
  └── full sweep: 80 sharded jobs                      (~2h each, parallel)
```
