# Sweep-4 plan — new prompts (corpus-isolated rewrite)

> **STATUS (2026-05-21): this plan is historical context only.**
> Sweep-4 (v5/v6/v7) revealed the prompt-engineering work has been
> under-invested. A full redesign of system and per-task prompts is
> now in progress — see
> `development/sweep_prompt_redesign_handoff.md` for the live briefing.
> Sweep-3 backward-compatibility (v0–v2) is no longer load-bearing per
> user direction. Phase 1/2/3 sections below describe the sweep-4 plan
> as executed; treat them as record, not direction.

Dated 2026-05-18, refreshed 2026-05-19 after PR-50 adoption. Branch: `sweep4-new-prompts` working directly on the main tree (no separate worktree — the original `../pddl-copilot-experiments-sweep4` worktree idea was dropped; isolation comes from the branch + the v5/v6/v7 variant indices alone).

## Status snapshot (2026-05-19)

- **Branch HEAD:** `e247af4` ("docs: adopt pddl-copilot marketplace 1.3.0 (PR-50)"). Originally branched off `main` @ `6b3be80`; carries one doc-only commit on top.
- **Sibling marketplace:** `../pddl-copilot` at `a259a38` (post-PR-50, marketplace 1.3.0; solver 2.2.0; validator 2.2.1; parser 1.5.0). Validator venv refreshed locally + on cluster so pyvalidator≥0.1.5 is live.
- **Tool surface for sweep-4:** marketplace 1.3.0 (NOT sweep-3's 1.2.0). Adoption rationale + zero-code-change justification documented in `development/CHANGELOG.md` 2026-05-19 entry. **This is a small tool-surface confound on top of the prompt-rewrite effect** — see Risks section for handling.
- **Drift calibration (PASSED 2026-05-19):** SLURM array `17654766` ran the full 5-model vLLM roster against the smoke slice (blocksworld/p01) on the new marketplace; drift diff vs `results/cluster-20260517/` (sweep-3, marketplace 1.2.0) shows aggregate FR-bucket shifts all <3pp, `tool_error` ticked +0.3pp (1 trial of 226), and the predicted FR_PLAN_INVALID → FR_TOOL_ERROR migration on `solve` did NOT appear on classical blocksworld (as expected — no Java/INTERNAL_ERROR path). See `development/sweep4_fr_pivot.md` for the full table + verdict. **Result: PR-50 adoption is empirically silent at smoke scale; sweep-4 needs only a one-line caveat in the writeup, not a full confound analysis.**
- **Phase 0 verification (`development/sweep4_fr_pivot.md`):** drift-half written 2026-05-19. The FR-prevalence-pivot half (which of the six prompt-review leaks dominates the FR distribution in sweep-3) is still pending — required before drafting v5–v7 in code per Phase 0 below.

## Scope shift from earlier draft

Originally sweep-4 was going to introduce SKILL.md injection (`prompt_style="skill-task"`). After reading the prompt-engineering review in `.local/prompts_review.md`, the work is split into two sweeps:

*Revised 2026-05-19: `tool_filter=per-task` retirement was pulled forward into sweep-4 (the table below reflects the original deferred-to-sweep-5 framing). `tools_all_minimal` is now the only with-tools arm; see `cluster-experimenting/lib/defaults.sh:32` and the 2026-05-19 sweep-4 finalisation CHANGELOG entry.*

| Sweep | Content | Conditions |
|---|---|---|
| **Sweep 4** (this plan) | New user-prompt variants v5/v6/v7. No SKILL.md injection. | Full matrix (no-tools, tools_all, tools_per-task) × {think on, off}. Same matrix as sweep-3 so the prompt rewrite is the only differential. |
| Sweep 5 (next plan) | Sweep-4 prompts + `prompt_style="skill-task"` arm. | `tools_per-task` retired (redundant with skill steering). New slug `tools_all_skill-task` added. |

`tool_filter=per-task` retirement is therefore **deferred to sweep-5**, not sweep-4. Sweep-4 must hold the matrix constant so sweep-3 vs sweep-4 cleanly isolates the prompt change.

## What the review found (summary)

`./.local/prompts_review.md` documents six leaks in the active prompts (v0–v2) against what `scoring.py:316–488` actually checks. The headline ones:

1. **VERDICT trailer fights the system prompt in with-tools cells.** Every `validate_*` template ends with `"End your response with exactly one line: VERDICT: VALID or VERDICT: INVALID"`. The with-tools system prompt simultaneously says "ONLY way ... is by calling the provided tools." Small/mid models resolve the conflict by emitting a verdict from memory, suppressing tool calls.
2. **`validate_plan` with-tools has no teaching of the `plan` argument.** `validate_pddl_syntax` is polymorphic; `_call_matches_validate_task` (`scoring.py:65–88`) rejects domain-only / domain+problem calls when grading `validate_plan`. Nothing in the user prompt cues the model to include `plan`. Result: `FR_VERDICT_MISMATCH` masquerading as a tool-selection win.
3. **`_GUIDED_SUFFIX` (disabled) is the only place tool-arg shape is taught.** Even re-enabling it would only address `domain`/`problem`, not `plan`.
4. **`solve` and `simulate` user prompts make tool calls feel optional.** "Generate a plan ..." / "Trace the state changes ..." are natural-language tasks the model can satisfy textually. Only the system prompt says otherwise.
5. **`simulate` (no-tools) doesn't teach the wire format** expected by `_normalize_trajectory` (`scoring.py:149–227`): step 0 = initial state, `action=""`, `boolean` = **all** TRUE predicates in parenthesised lowercase form. Tiny models pass schema validation while failing equality.
6. **`solve` (no-tools) doesn't teach action format.** `SolveResponse.plan` requires parenthesised PDDL; schema description has one weak example.

## Methodology guardrail (load-bearing)

**v0–v2 must not be edited in place.** The `prompt_variant` integer is part of the 10-tuple resume key (`runner.py:441–451`). A v0-indexed trial today reads the same paraphrase as a v0-indexed trial from cluster-26042026. Edit them and sweep-3's identity dissolves silently — every existing checkpoint becomes uncomparable.

**Rule:** new templates are appended as **v5 / v6 / v7** (v3/v4 stay disabled to preserve their reservation). `ACTIVE_PROMPT_VARIANTS` flips from `(0, 1, 2)` to `(5, 6, 7)` for sweep-4. Sweep-3 reproduction = checkout the sweep-3 commit (sha tag is in every trial). No in-place edits to existing list entries.

This matches the existing v3/v4-disabled comment pattern in `pddl_eval/prompts.py:42–93`.

## Data-model change

The reviewer's edits A + D require templates that **differ between with-tools and no-tools conditions** (drop VERDICT in tools branch; teach wire format in no-tools branch). Today `PROMPT_TEMPLATES` is condition-agnostic.

Minimal surface-area change:

```python
# pddl_eval/prompts.py — additions only; existing PROMPT_TEMPLATES untouched.

# Sparse override: only set for new variants that diverge from the base template.
# For v0–v4 this dict is empty → PROMPT_TEMPLATES is used in both conditions
# (sweep-3 corpus identity preserved). For v5–v7, the tools branch reads from
# this override and the no-tools branch reads from PROMPT_TEMPLATES.
PROMPT_TEMPLATES_TOOLS_OVERRIDE: dict[str, dict[int, str]] = {
    "solve":            {5: "...", 6: "...", 7: "..."},
    "validate_domain":  {5: "...", 6: "...", 7: "..."},
    "validate_problem": {5: "...", 6: "...", 7: "..."},
    "validate_plan":    {5: "...", 6: "...", 7: "..."},
    "simulate":         {5: "...", 6: "...", 7: "..."},
}
```

`pddl_eval/runner.py:266` becomes:

```python
override = PROMPT_TEMPLATES_TOOLS_OVERRIDE.get(task, {})
if with_tools and prompt_variant in override:
    template = override[prompt_variant]
else:
    template = PROMPT_TEMPLATES[task][prompt_variant % len(PROMPT_TEMPLATES[task])]
```

Two-line change at the active call site. Archived chain path at `runner.py:821` is left untouched (CLAUDE.md `single-task only` rule).

## Draft new templates (v5–v7)

These are **drafts**; finalise after the verify step below. Rationale is keyed to the review findings.

### `solve`

| | tools (override) | no-tools (base PROMPT_TEMPLATES) |
|---|---|---|
| v5 | `Solve this PDDL planning problem by calling a planner tool. Pass the complete domain and problem text below as the planner's \`domain\` and \`problem\` arguments — not file names or short identifiers.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | `Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. \`(pick-up a)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` |
| v6 | `Find a valid plan for this PDDL problem by invoking a planner tool. Provide the full PDDL text as the planner's \`domain\` and \`problem\` arguments.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}` | `Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. \`(unstack a b)\`.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}` |
| v7 | `Generate a plan that solves the following planning problem. Use a planner tool — pass the complete PDDL text as the \`domain\` and \`problem\` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | `Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. \`(stack a b)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` |

Addresses findings 4 (tool-call explicitness) + 6 (action wire format). Tool-name hint via "planner tool" (not naming `classic_planner` vs `numeric_planner` — that's the SKILL job for sweep-5).

### `validate_domain`

| | tools (override) | no-tools (base) |
|---|---|---|
| v5 | `Check whether this PDDL domain is syntactically valid by calling the validation tool. Pass the full domain text below as the \`domain\` argument.\n\n{domain}` | `Check if this PDDL domain definition has valid syntax:\n\n{domain}` |
| v6 | `Validate the syntax of this PDDL domain by invoking the validation tool with the full domain text as the \`domain\` argument.\n\n{domain}` | `Validate the following PDDL domain for syntactic correctness:\n\n{domain}` |
| v7 | `Is this PDDL domain syntactically correct? Decide by calling the validation tool with the full domain text below.\n\n{domain}` | `Is this PDDL domain syntactically correct? Please check.\n\n{domain}` |

Addresses finding 1: VERDICT trailer dropped from with-tools branch (tool result drives the answer) AND from no-tools branch (the reviewer flagged it as redundant given `format=ValidateResponse`). Verify that `_VERDICT_RE` is not the only no-tools extractor before committing — `format=ValidateResponse` constrains JSON output to `{"verdict": "VALID"|"INVALID", ...}` (`schemas.py:35–42`); the verdict regex is a free-text fallback. Both paths still grade correctly without the trailer.

### `validate_problem`

| | tools (override) | no-tools (base) |
|---|---|---|
| v5 | `Check whether this PDDL problem is syntactically valid against its domain. Call the validation tool with the full \`domain\` and \`problem\` texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | `Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` |
| v6 | `Validate the syntax of this PDDL problem against its domain by invoking the validation tool. Pass both \`domain\` and \`problem\` as full texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | `Validate the syntax of this PDDL problem against its domain:\n\nDomain:\n{domain}\n\nProblem:\n{problem}` |
| v7 | `Is this PDDL problem file syntactically correct for the given domain? Decide by calling the validation tool with both \`domain\` and \`problem\` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}` | `Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}` |

Same rationale as `validate_domain`. Explicitly names both `domain` AND `problem` arguments so the model doesn't drop one (relevant because `_call_matches_validate_task` requires `problem` present for this task).

### `validate_plan` — most affected

| | tools (override) | no-tools (base) |
|---|---|---|
| v5 | `Check whether this plan is correct for the given domain and problem. Call the validation tool with ALL THREE of \`domain\`, \`problem\`, AND \`plan\` — pass the full texts from below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | `Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` |
| v6 | `Verify this plan by invoking the validation tool. The tool call MUST include the \`plan\` argument — otherwise it only checks the domain. Pass \`domain\`, \`problem\`, and \`plan\` as full texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | `Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` |
| v7 | `Is this plan valid for the given planning problem? Decide by calling the validation tool with \`domain\`, \`problem\`, and \`plan\` arguments (all three are required for plan validation).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | `Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` |

Addresses finding 2 (the dominant `validate_plan` failure mode): every variant explicitly names `plan` as a required argument. If a model still drops `plan`, that's a model failure, not a prompt failure.

### `simulate`

| | tools (override) | no-tools (base) |
|---|---|---|
| v5 | `Trace the state transitions of this plan by calling the state-transition tool. Pass \`domain\`, \`problem\`, and \`plan\` as full texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | `Simulate this plan and return the trajectory. Step 0 is the initial state from the problem (\`action\` empty). Each later step records the action executed. \`boolean\` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. \`(on a b)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` |
| v6 | `Step through this plan by invoking the state-transition tool with the full \`domain\`, \`problem\`, and \`plan\` texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | `Step through this plan action by action. For each step output the action just executed (or empty for step 0) and the full set of currently-true predicates in parenthesised PDDL form, e.g. \`(on a b)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` |
| v7 | `Show me the trajectory after applying this plan. Call the state-transition tool with the full PDDL texts (\`domain\`, \`problem\`, \`plan\`) below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` | `Show the state at each step of this plan. Step 0 = initial state, \`action="" \`. Each \`boolean\` entry lists every predicate that holds in that state, parenthesised and lowercase. \`numeric\` is the fluents map.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}` |

Addresses finding 5 (no-tools wire format) and 4 (tools-branch explicit tool naming). The no-tools rewrites encode the three invariants `_normalize_trajectory` enforces: step 0 = initial, FULL truth set per step, parenthesised lowercase form.

## Files to touch

All edits on the `sweep4-new-prompts` branch (no separate worktree):

1. **`pddl_eval/prompts.py`**
   - Append v5/v6/v7 to each of the 5 task lists in `PROMPT_TEMPLATES` (no-tools branch, unchanged structure). Mark v3/v4 as still-disabled in the existing comments.
   - Add `PROMPT_TEMPLATES_TOOLS_OVERRIDE` dict with v5/v6/v7 per task.
   - Flip `ACTIVE_PROMPT_VARIANTS` to `(5, 6, 7)`.
   - Update the module docstring to reflect: "Sweep-4 active set is v5/v6/v7; sweep-3 used v0/v1/v2."

2. **`pddl_eval/runner.py:266`** — single active call site. Two-line override-aware template lookup (see snippet above). Do **NOT** touch `runner.py:821` (archived chain path).

3. **`run_experiment.py`** — no signature change. Argparse help text at `:599–606` should mention the new active variants. `num_variants` default already reads from `len(ACTIVE_PROMPT_VARIANTS)`, so flipping to `(5,6,7)` just works.

4. **`development/CHANGELOG.md`** — new dated entry (post the existing 2026-05-19 PR-50 entry): sweep-4 rationale, link to `.local/prompts_review.md`, list of v5/v6/v7 indices, note that sweep-3 (v0/v1/v2, marketplace 1.2.0) remains the canonical pre-rewrite baseline AND pre-PR-50 baseline, sweep-4 (v5/v6/v7, marketplace 1.3.0) is the new active set.

**Not touched** in sweep-4: `scoring.py`, `schemas.py`, `summary.py`, `resume.py`, `WITH_TOOLS_SYSTEM`, `PROMPT_STYLE_CHOICES`, `TOOL_FILTER_CHOICES`, cluster sbatch scripts, analyzer skill. Resume keys for sweep-3 trials (variant ∈ {0,1,2}) remain untouched; sweep-4 trials (variant ∈ {5,6,7}) are a disjoint slice.

## Phase 0 — verify before editing (5-min pivot)

The reviewer's "what I'd verify before editing" step settles which leak dominates. Before drafting v5–v7 in code:

```python
# In a notebook, against the freshest full sweep (sweep3-cluster-20260517):
# Group (task × with_tools × failure_reason) and check:
#   - validate_* with-tools failures: dominated by FR_TOOL_NOT_SELECTED?
#       → prompt-engineering fix 1 (drop VERDICT) lands the biggest gain
#   - validate_plan with-tools failures: high FR_VERDICT_MISMATCH with
#     non-empty tool_calls? → fix 2 (teach plan arg) is the bottleneck
#   - simulate no-tools failures: high FR_VERDICT_MISMATCH despite schema-
#     valid output? → fix 5 (wire-format teaching) is the bottleneck
```

If the breakdown reveals a different dominant failure mode than the review predicts, **re-prioritise the template edits before running sweep-4** — the corpus cost of getting the rewrite wrong is one full sweep wasted.

## Phase 1 — implement

1. Phase-0 verification (above). Capture the FR pivot in `development/sweep4_fr_pivot.md` so reviewers can audit the rewrite priority.
2. Edit `prompts.py` + `runner.py` per "Files to touch."
3. Local smoke: `python run_experiment.py --partial 1 --models qwen3:0.6b --conditions both --tool-filter all` against laptop Ollama. Eyeball one trial per task in `trials.jsonl` — confirm v5 template under with-tools has no VERDICT trailer for `validate_*`, names tool arguments for all 5 tasks.
4. Diff check: `git diff main -- pddl_eval/prompts.py` should show **additions only** to lists, plus the new `PROMPT_TEMPLATES_TOOLS_OVERRIDE` dict. No mutations of existing v0–v4 strings.
5. Commit on `sweep4-new-prompts` branch (no Claude credits per memory `feedback_no_claude_credits_in_commits`).

## Phase 2 — cluster sweep-4

1. **Gate: drift smoke `17653267` results in.** Diff `results/smoke/fixed_e247af4_<ts>/<model>/` against the matched cells in `checkpoints/cluster-20260517/`. Quantify per-task FR-bucket shift. If `solve` shows any FR_PLAN_INVALID → FR_TOOL_ERROR migration (expected on cells that hit planner crashes) or `validate_*` shows a >2pp pass% movement (NOT expected — the `report` leak shouldn't have driven much), note the magnitude in `development/sweep4_fr_pivot.md` so the eventual sweep-4 writeup can disambiguate "prompt rewrite effect" from "marketplace 1.3.0 tool surface effect."
2. Push branch, open PR against `main` for review.
3. After merge: cluster matrix unchanged from sweep-3. Same condition slugs (`tools_per-task_minimal`, `tools_all_minimal`, `no-tools`), same models, same think modes. Only the variant indices differ — the sbatch scripts read `--num-variants` not the variant integers, so no sbatch edits needed. **Pin: `../pddl-copilot` must be at `a259a38` (post-PR-50) for the entire sweep-4 submission window.** No marketplace drift mid-sweep.
4. Submit via `cluster-experimenting/submit_full_sweep.sh` as usual.
5. Land results under `results/full/<sha>_<ts>/` and tag the directory `sweep4-cluster-<date>` for analyzer compatibility. Record the marketplace SHA (`a259a38`) and pddl-copilot tag (`v2.0.0-9-ga259a38`) in the run's `meta` block so future re-comparisons can resolve the tool surface unambiguously.

## Phase 3 — analysis

1. Side-by-side `(task × condition × FR-breakdown)` for sweep-3 vs sweep-4 in the analyzer skill. The "did the prompt rewrite close the tool/no-tool gap?" question is the central one.
2. If `validate_*` tools branch lifts substantially, the VERDICT-conflict hypothesis is confirmed.
3. If `validate_plan` tools branch jumps even more, finding 2 was the dominant `validate_plan` leak.
4. If `simulate` no-tools moves regardless of tools branch, finding 5 was real and we under-credited no-tools previously.
5. Results inform sweep-5 design (skill-task arm + per-task retirement).

## Sweep-4.1 — re-establish v0–v2 baseline under marketplace 1.3.0

**Goal (added 2026-05-19):** after sweep-4 (v5/v6/v7) lands, run an identical sweep with `ACTIVE_PROMPT_VARIANTS = (0, 1, 2)` against the **same** marketplace 1.3.0 + improved-type-hints pddl-copilot pin used by sweep-4. This re-establishes the "neutral prompt" arm under the new tool surface so cross-sweep comparisons are not confounded by the 1.2.0 → 1.3.0 marketplace bump plus subsequent tool-schema / type-hint improvements in pddl-copilot.

**Why this is needed (per 2026-05-19 methodology discussion):**

- v0–v2 currently only exist in the sweep-3 corpus (`results/cluster-20260517/`, marketplace 1.2.0, pre-PR-50, pre-type-hint-improvements).
- v5/v6/v7 are explicit/steered ("call a planner tool", "include the `plan` argument", etc.). They isolate **tool utility** by removing prompt-shape leaks — but they no longer measure **spontaneous tool affordance** (whether models choose tools given a neutral request).
- Without a v0–v2 re-baseline under the new tool surface, the paper's "tool affordance" headline depends on sweep-3 numbers that mix prompt-leak effects with an older tool surface. Drift smoke `17654766` showed marketplace drift is empirically <3pp on blocksworld/p01 (`development/sweep4_fr_pivot.md`), so the confound is small — but it is non-zero, and a reviewer can legitimately press on it.
- Re-running v0–v2 on marketplace 1.3.0 (post-PR-50, post-type-hint improvements) gives the paper a **clean 2-arm design**: same plumbing under each arm, only the prompt differs. The (steered − neutral) gap then attributes cleanly to prompt engineering.

**Matrix:** identical to sweep-4 — same models × same conditions × same think modes × same tasks × same problems. Only `ACTIVE_PROMPT_VARIANTS` flips back to `(0, 1, 2)`. No code edits to templates (v0–v2 strings are immutable per the methodology guardrail above); just the active-set flag and a fresh cluster submission.

**Marketplace pin:** must match sweep-4 exactly. Record the `../pddl-copilot` commit SHA in every trial's `meta` block; if pddl-copilot has advanced past sweep-4's pin by the time sweep-4.1 runs, *either* roll pddl-copilot back to the sweep-4 SHA *or* re-run sweep-4 on the newer pin first. Never let sweep-4 and sweep-4.1 see different tool surfaces — that defeats the whole point.

**Reporting:** present sweep-4 (v5/v6/v7, steered) and sweep-4.1 (v0/v1/v2, neutral) as paired arms in the paper. The gap is itself a finding ("light prompt engineering closes X pp of the tool-utility gap; Y pp remains as intrinsic model limitation"). Sweep-3 v0–v2 numbers stay in the appendix as the historical / pre-1.3.0 reference.

## Next sweep — see separate handoff

Sweep-4 (v5/v6/v7) revealed prompt-engineering problems that go beyond the scope of this plan:

- `validate_*` no-tools cells produced elevated `FR_FORMAT_PARSE_FAIL` rates after the v5–v7 redesign dropped the `VERDICT: VALID|INVALID` trailer that the `extract_verdict` regex fallback relies on.
- The with-tools override and no-tools base prompts in v5–v7 are wholly different strings, confounding "prompt content" with "tool steering" in the with-tools vs no-tools comparison.

User direction (2026-05-21): redesign all prompts from scratch with literature-grounded rationale; sweep-3 backward-compatibility is no longer load-bearing. Three-arm matrix: `(no-tools, neutral)`, `(with-tools, neutral)`, `(with-tools, steered)`. SKILL.md system-prompt injection is on the table for this sweep (originally deferred to sweep-5).

See `development/sweep_prompt_redesign_handoff.md` for the full briefing. Concrete design decisions (variant indices, prompt wording, system-prompt structure, SKILL.md inclusion) are open and require user sign-off.

## Sweep-5 preview (not in this plan)

After sweep-4 lands:

- Inline SKILL.md bodies from `../pddl-copilot/plugins/pddl-solver/skills/pddl-planning/SKILL.md` and `pddl-validator/skills/pddl-validation/SKILL.md` into `pddl_eval/prompts.py` as `WITH_TOOLS_SYSTEM_BY_TASK` (per simplify review of the original sweep-4 plan).
- Add `prompt_style="skill-task"` to `PROMPT_STYLE_CHOICES`.
- Retire `tool_filter=per-task` from new cluster slugs (keep choice tuple intact for reproducibility, mirror the `"guided"` retirement comment pattern). Add new slug `tools_all_skill-task`.
- Run with the v5/v6/v7 prompts from sweep-4 plus the skill-task arm.

## Risks

- **Variant-index collision in resume keys**: zero risk. v5/v6/v7 don't appear in any sweep-3 trial.
- **Schema drift from dropping VERDICT trailer in no-tools**: `format=ValidateResponse` does the work, and `_VERDICT_RE` is a fallback path. Tiny-model degradation would show up in the local smoke step.
- **Prompt rewrite over-claims the win**: if sweep-4 closes the tool/no-tool gap, attribute carefully — both findings 1 and 2 affect with-tools but only finding 5 affects no-tools. The FR breakdown is the receipts.
- **Cluster matrix mismatch with sweep-3**: explicitly held identical except for variant indices. If anyone "improves" the matrix during sweep-4, the comparison is broken.
- **Tool-surface drift from PR-50 adoption**: sweep-4 runs against marketplace 1.3.0; sweep-3 ran against 1.2.0. Two observable deltas: (a) `solve` task FR_PLAN_INVALID → FR_TOOL_ERROR re-attribution on planner-crash cells (no pass% movement, just bucket relabel); (b) `validate_*` with-tools `report` text no longer contains the spurious "Plan is VALID" line on domain-only/domain+problem calls (could marginally shift VERDICT accuracy on small models that parroted it; direction unpredictable). Drift smoke `17653267` sizes the magnitude. If material (say >2pp on any `validate_*` cell or >5pp FR migration on `solve`), the sweep-4 writeup must call out the confound separately from the prompt-rewrite effect; if immaterial, fold into a single-line caveat.
