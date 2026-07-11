# Frontier with-tools — correctness ladder (NEXT JOB)

**Status:** PLAN / GATED. Correctness-first staged probe of the **with-tools** condition for the
Anthropic-API frontier models, starting with **Haiku 4.5**. Decisions answered 2026-06-27; **Decision 2
(simulate criterion) needs ONE re-confirm** after a code finding (the current grader does NOT match
the chosen answer — see below). Nothing runs until that is resolved. Companion docs: `development/frontier/with_tools_probe_findings.md` (the prior cost probe +
the $146 / ISS-023 decision), `development/frontier/frontier_haiku_phase_plan.md`, `OPEN_ISSUES.md` ISS-023
(cost) + ISS-024 (simulate grader history).

## Why this job exists (the reframe)

The 75-trial probe in `with_tools_probe_findings.md` was a **cost projection, not a correctness
audit**. It proved the agentic loop *runs* and produced a capability ladder (tools → ~100% on nearly
everything) — but it did **not** verify the *grading* is right, and "~100% on everything" is exactly
the kind of too-clean number that needs a correctness pass, not a victory lap. So we do not yet have
a verified with-tools eval; we have a cost probe.

**Principle: run in increasing complexity to verify the implementation AND the evaluation are
correct, before any scale.** Do NOT jump to the full 4,560-trial setup. Cost optimization (prompt
caching, trajectory compaction — ISS-023) is **premature**: the $146 gates only the *final* rung, and
the ladder is cheap precisely because the early rungs are tiny. Caching is a knob we reach for at
rung 3, measured against real token data — not a design phase up front.

## Scope

**In (this job):** our own single-task PDDL benchmark — the **5 tasks** (`solve`, `validate_domain`,
`validate_problem`, `validate_plan`, `simulate`), **with-tools** (live agentic MCP loop), on the
**sweep5v2 plain-only** corpus (prompt variants 11-13 = 4,560 trials at full N). Model: **Haiku 4.5**
first (per the ISS-023 decision). This is the paper's main scope.

**Later (valued, planned — Decision 5):** **PlanBench** (t1/t2/t3/t7) is a *different benchmark* and
gets its **own** ladder, sequenced AFTER this single-task PDDL with-tools ladder. It is **important
for cross-paper comparison and carries real reviewer weight** — not a throwaway. Venue is uncertain
(AAAI-27 only if we make the deadline; may pivot), so it is no longer framed as "out of the main
paper." Frontier *no-tools* PlanBench data for Haiku already exists (`d1045a5`); the with-tools
PlanBench is the new piece when we get there.

## Branch

**Branch from `main`** (`origin/main`, currently `6007032`) — NOT from `paper/iter2-decoupled-run`.
The frontier work touches only the Anthropic-API path (`tools/claude_api_*`,
`results/frontier-with-tools-probe/`, docs); everything it needs (the `claude_api_*` tooling, Q1
grader, simulate normalizer fix, the existing probe) is already in main. Basing on the decoupled
branch would entangle this with that unmerged, in-flight cluster effort for no benefit. Merging
frontier→main later does not touch the cluster's `paper/iter2-decoupled-run` checkout, so the
in-flight run stays frozen.

```
git checkout -b paper/frontier-with-tools origin/main   # blocked until the 3 stray
                                                         # working-tree edits are committed/stashed
```

> **NOTE (2026-06-27):** the working tree currently has uncommitted edits to
> `.claude/skills/cluster-ops/{SKILL.md,scripts/status.sh}` and `development/decoupled/decoupled_run_handoff.md`
> (not made by this plan) that block the switch. Commit/stash those first, then create the branch;
> this doc is untracked and carries over.

## The ladder

| Rung | Scale | Must prove | ~cost |
|---|---|---|--:|
| 0 — smoke | 1 trial × each of 5 tasks (Haiku) | Loop runs; the MCP tool actually fires; result captured; grader emits a verdict; loop **terminates** (doesn't silently hit `MAX_TOOL_LOOPS=10`) | cents |
| 1 — grading audit | ~5 trials/task, **known ground truth**, manual row-by-row inspection | The grader's verdict matches ground truth by hand — at least one TRUE and one FALSE fixture per task. Confirm ~100% is **real, not lenient** | ~$1 |
| 2 — stratified re-read | the existing 75-trial probe in `results/frontier-with-tools-probe/` | Re-examine as *correctness*: spot-check the n=6-8 cells flagged "directional"; confirm the depot/p01 200K-overflow is a clean recorded failure, not a crash | already spent |
| 3 — one full cell | one full **domain** (all 5 tasks; Decision 3) | Throughput, error handling, and **N-matching** with the no-tools plain arm hold at scale. **First real spend; first place caching earns its keep** | first real spend |
| 4 — full run | 4,560 plain-only (variants 11-13), Haiku | The deliverable | the $146 question (ISS-023) |

### Per-rung detail

- **Rung 0 (smoke).** Pin to 1 trial/task via the probe's partial mechanism. Read the saved trial:
  is there a real `tool_calls[*]` entry with a non-error result? Is `done_reason`/turn-count sane
  (not 10)? Does `check_success` + the Q1 grader populate a verdict and `format_compliant`? A crash,
  an empty tool-call list, or a silent `MAX_TOOL_LOOPS` exhaustion = stop and fix.
- **Rung 1 (grading audit).** The load-bearing rung. For each task pick fixtures with **known**
  ground truth spanning both polarities, run ~5, and **read every row by hand**: does the recorded
  verdict match truth? This is where we catch a too-lenient with-tools grader (the mirror image of
  the ISS-024 no-tools normalizer bug — same risk family, opposite direction). See Decision 2 for the
  simulate success criterion, which must be settled here.
- **Rung 2 (re-read the probe).** No new spend. Re-open the 75-trial probe trials and audit the
  cells the findings doc itself flagged as directional (n=6-8, wide CIs) and the lone Haiku overflow
  (`simulate depot/p01`, 400 invalid_request) — confirm it's bucketed as a clean failure.
- **Rung 3 (one full domain).** Only after rungs 0-2 pass. Per Decision 3, shard the run **by
  domain** (each domain sampled equally) rather than by task; rung 3 = one full domain across all 5
  tasks, to validate throughput, error handling, and trial-for-trial N-matching with the no-tools
  plain corpus before committing to all domains. (User regards this rung as low-importance since the
  probe + smoke already sample — keep it light.) Caching, if implemented, is measured here. NOTE:
  verify `tools/claude_api_tools_probe.py` supports a domain filter — it currently shards by
  task/variant, so by-domain selection may need a small addition.
- **Rung 4 (full run).** The 4,560-trial Haiku-WT deliverable. Gated on the ISS-023 cost call, now
  informed by the *measured* per-trial cost from rung 3 rather than a projection.

## Correctness risks the ladder is hunting

1. **Is with-tools ~100% real, or grader-lenient?** Especially **simulate**: with-tools it is graded
   on the `get_state_transition` *tool result*. If "model called the tool and the tool was right"
   counts as success regardless of what the model concluded, that measures the tool, not the model.
   Settle the criterion at rung 1 (Decision 2).
2. **Tool-call extraction edge cases** — a malformed/partial tool call must be a scored failure, not
   a silent drop.
3. **Loop termination** — `MAX_TOOL_LOOPS` exhaustion must get its own bucket, not masquerade as a
   wrong answer.
4. **N-matching** — the with-tools corpus must line up trial-for-trial with the no-tools plain arm,
   or the tools-vs-no-tools contrast is broken.

## Cost & caching — deferred, on purpose

ISS-023 stays open as "fold caching in at scale," not "design before starting." When we reach rung 3:
prompt-caching the byte-identical system + ~3,611-token tool-schema prefix is the first lever, but
note (a) **Haiku 4.5's minimum cacheable prefix is 4096 tokens** — the prefix must clear it or it
silently won't cache (verify via `usage.cache_read_input_tokens`); and (b) caching helps **live /
sequential** runs only, not parallel fan-out (the within-trial multi-turn accumulation is the
reliable win). All measured at rung 3, not designed now.

## Spend gates

- Rungs 0-2: cheap (< ~$2 total; rung 2 is already spent). Proceed without a fresh ask.
- Rung 3: **first real spend** — get a go-ahead before running.
- Rung 4: the $146 question — explicit go-ahead + the ISS-023 cost call.

## Open decisions (answer inline)

### 1 — Branch base
> Recommend `main` (reasoning above). OK?
> ANSWER: OK, branch from `main`

### 2 — Rung-1 simulate success criterion (with-tools)
With-tools simulate is graded on the `get_state_transition` tool result. Options: (a) success =
model invoked the tool and the tool result matched ground truth; (b) success = the model's own final
answer reflects the correct trajectory (tool is a means, not the verdict). (b) is the stricter,
more defensible "did the model get it right" measure; (a) risks measuring the tool.
> ANSWER: B. (btw, is this how the vllm current sweep evaluates too?)
>
> **CODE FINDING (2026-06-27) — needs your re-confirm.** No, not for with-tools. The shared
> `check_success` (`pddl_eval/scoring.py:566-583`) grades with-tools simulate on criterion **(a)**:
> success iff the model SELECTED `get_state_transition` and one of its returned trajectories matches
> the oracle; the model's own final text is NOT graded in the with-tools path. The *no-tools* path
> (the in-flight decoupled sweep) grades the model's own trajectory text (`:596`) = (b)-like. So the
> grader already has a deliberate per-condition split: no-tools = model reasoning (b), with-tools =
> tool-driving (a).
>
> Choosing (b) for with-tools is costly: the frontier probe REUSES `check_success`, so it means
> editing the SHARED with-tools grader → either re-grading the entire sweep5v2 with-tools corpus, or
> forking a frontier-only grader that DIVERGES from the open roster (breaks the cross-arm comparison
> that motivates the frontier run). And `get_state_transition` IS the oracle, so for with-tools "the
> model's own correct trajectory" collapses to "the model correctly drove the oracle tool" — (b)
> isn't more discriminative and would need the harness to elicit a separate final-answer synthesis.
>
> **Recommend: keep (a) for with-tools** (comparable + principled); address the "~100% measures the
> tool" worry by REPORTING it as tool-driving capability (the model's unaided state-tracking is the
> no-tools arm; the tools-vs-no-tools delta is the model-vs-tool story). Rung 1 verifies (a) is
> implemented right, not that we switch to (b).
> RE-CONFIRM: keep (a), or accept the re-grade/divergence cost of (b)?
> ANSWER:

### 3 — Rung-3 first full cell
`validate_plan` is the bulk (~$73 of the $146) — most representative of throughput/cost. A smaller
task (e.g. `validate_domain`, ~$6) is cheaper to fail on but less representative.
> ANSWER: we can run the experiments by domains rather than by tasks this way well sample equally.
> btw I don't regard it much importance since we sample with the probing and smoke runs. 

### 4 — Roster on the early rungs
Full ladder targets **Haiku** (ISS-023 decision). Ride Sonnet 4.6 along at rungs 0-1 for a cheap
cross-model correctness sanity check, or keep Sonnet probe-only (full Sonnet-WT ~$449, out of scope)?
> ANSWER: start with haiku. when we complete it. well decide if we'll run sonnet too. 

### 5 — PlanBench scope
Keep PlanBench out of this paper as a separate future-work track (status quo), or reopen it into the
AAAI-27 main paper (changes whether we plan its ladder now)?
> ANSWER: we may not target AAAI27 if we won't make it. but planbench is extremly important for cress papers comparison.
> it will have a major positive impact in the eyes of the reviewers.

### 6 — Caching timing
Confirm caching is deferred to rung 3 (measured), not designed up front.
> ANSWER: confirmed

## Reference

- `development/frontier/with_tools_probe_findings.md` — prior cost probe, capability ladder, $146 decision.
- `development/frontier/frontier_haiku_phase_plan.md` — frontier phase design (batch no-tools / live with-tools).
- `OPEN_ISSUES.md` — ISS-023 (with-tools cost), ISS-024 (simulate grader artifacts).
- Tool: `tools/claude_api_tools_probe.py` (live agentic loop); `tools/_claude_api_common.py`;
  `tools/claude_api_batch.py` (no-tools batch). Harness builders reused: `build_jobs` /
  `build_messages` / `check_success` / `save_results`. Turn cap: `chat.MAX_TOOL_LOOPS = 10`.
- Q1 grader: `_coerce_simulate_trajectory` / `simulate_format_compliant` / `TaskResult.format_compliant`
  / `summary.simulate_q1`.
- Existing probe data: `results/frontier-with-tools-probe/{haiku-with-tools,sonnet-with-tools,haiku-no-tools,keys}`.
