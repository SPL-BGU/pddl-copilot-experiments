# Prompt-engineering redesign — handoff to next session

Dated 2026-05-21. Branch: `sweep4-new-prompts`. This is a self-contained briefing for a fresh session; it does not assume any conversational context.

## Why we're doing this (background)

Sweep 3 (v0–v2) and sweep 4 (v5–v7) both have prompt-engineering gaps that compromise the with-tools vs no-tools comparison:

**Sweep 3 problems:**
- `simulate` no-tools prompts didn't teach the wire format (`step` / `action` / `state.boolean` / `state.numeric`). Models that *could* simulate failed equality normalization.
- `validate_*` with-tools prompts didn't teach which tool function to call or which arguments to pass. `validate_pddl_syntax` is polymorphic (different behavior depending on whether `domain`, `problem`, `plan` are supplied) so guessing fails.
- `solve` with-tools also under-specified the planner tool — but it scored fine because the planner is the "obvious" canonical tool. That outcome is coincidence, not validation of the prompt.

**Sweep 4 problems:**
- Dropped the `VERDICT: VALID|INVALID` trailer from `validate_*` no-tools. The Pydantic JSON-schema constraint (`format=ValidateResponse`) is a *soft* logit-bias constraint, not a hard grammar gate — small / hybrid-arch / thinking models still emit malformed JSON. The regex fallback (`extract_verdict`) is the safety net; dropping the trailer removed it → `FR_FORMAT_PARSE_FAIL` spike.
- With-tools (override) and no-tools (base) prompts were wholly different strings. The "tools improves results" claim then confounds tool availability with prompt content.

**The takeaway:** prompt engineering was the under-invested part of this experiment. We've been treating it as a side-task while it's actually load-bearing — the entire "tools provide benefit" thesis depends on the no-tools baseline having a *fair* prompt that doesn't artificially handicap the comparison.

## What we're trying to measure

Show that MCP planning/validation/simulation tools provide measurable benefit over an **equally well-engineered no-tools baseline** along four axes:

1. **Token count** — tool-result-conditioned output should be shorter than inline reasoning.
2. **Reliability** — lower variance, lower `FR_FORMAT_PARSE_FAIL`, lower `FR_VERDICT_MISMATCH`.
3. **Correctness** — higher pass rate against ground truth.
4. **Tool-use adherence** — when explicitly instructed, does the model actually call the right tool with the right arguments?

## Methodology requirements

### 1. Literature-grounded prompt engineering

Prompts must not be invented ad-hoc. Survey highly-regarded tool-use evaluation work and apply their principles, citing the rationale per phrasing choice. Worth consulting:

- **ReAct** (Yao et al. 2022/2023) — reasoning+action interleaving
- **Toolformer** (Schick et al. 2023) — tool-call placement
- **ToolLLM / ToolBench** (Qin et al. 2023)
- **Gorilla** (Patil et al. 2023) — function-call format
- **BFCL** — Berkeley Function-Calling Leaderboard prompting conventions
- **τ-bench** (Yao et al. 2024) — tool-use under realistic conditions
- **AgentBench** (Liu et al. 2023)
- **MINT** (Wang et al. 2024) — multi-turn tool use
- **AppWorld** (Trivedi et al. 2024)
- Anthropic / OpenAI tool-use cookbooks if applicable

Each prompt's phrasing, ordering, format-spec, and trailer should have a written justification tied to a source.

### 2. Three-arm matrix per (model × task × think × paraphrase)

| Arm | Prompt | Measures |
|---|---|---|
| `(no-tools, neutral)` | base prompt, well-engineered for tool-less success | what the model can do unaided |
| `(with-tools, neutral)` | same string as above, but tools are available | spontaneous tool use without prompting |
| `(with-tools, steered)` | neutral + minimal tool-call directive | tool adherence under explicit instruction |

**The neutral and steered prompts must be textually near-identical** — differing only by the tool directive. This isolates "tool availability" from "prompt content" from "explicit steering" as separate effects.

### 3. Five tasks, each redesigned from scratch

- `solve` — output a parsable plan
- `validate_domain` — output VALID/INVALID verdict
- `validate_problem` — output VALID/INVALID verdict
- `validate_plan` — output VALID/INVALID verdict (hardest tools case — needs explicit `plan` argument or the polymorphic validator silently checks only domain+problem)
- `simulate` — output structured trajectory matching `SimulateResponse` (`schemas.py`)

### 4. System prompt redesign — includes SKILL.md inlining (in scope)

Current `WITH_TOOLS_SYSTEM` and `WITHOUT_TOOLS_SYSTEM` (`pddl_eval/prompts.py`) are short and bland. After the 2026-05-21 cleanup they are flat strings (the `guided` style and dict-of-styles structure were removed); the redesign starts from that clean slate.

**User direction (2026-05-21): pull SKILL.md inlining forward from sweep-5 into this sweep.** Inline the pddl-copilot skill bodies into the system prompt for with-tools cells so the model receives concrete tool documentation alongside the task instruction. The relevant files:
- `../pddl-copilot/plugins/pddl-solver/skills/pddl-planning/SKILL.md`
- `../pddl-copilot/plugins/pddl-validator/skills/pddl-validation/SKILL.md`
- `../pddl-copilot/plugins/pddl-parser/skills/pddl-parsing/SKILL.md` (if it exists and is wired in the active marketplace)

Open design questions to bring to the user:
- One unified system prompt with all SKILL.md content concatenated, or per-task system prompts with only the relevant SKILL.md? The latter is cleaner but introduces a `system_prompt_by_task` mapping in `prompts.py` and a new lookup in `runner.py`.
- How to handle the no-tools system prompt — should it stay minimal (no SKILL exposure since there are no tools), or also receive the SKILL.md content so the same instruction surface is available across conditions for cleaner attribution?
- Do we want the SKILL.md content verbatim, or curated / shortened to reduce token cost? (Token-cost is one of the four headline metrics, so a fair baseline should use the SKILL content the marketplace actually ships, not a hand-edited version.)

### 5. No prior corpus to preserve

User has explicitly said: **don't care about sweep-3 backward compatibility anymore.** Free hand on prompt design.

### 6. 2026-05-21 cleanup that already landed

The next session starts from a cleaner baseline than the previous attempts saw:
- `guided` prompt style and `_GUIDED_SUFFIX` removed from `prompts.py`. `WITH_TOOLS_SYSTEM` is now a flat `str`, not a `dict[str, str]`.
- `tool_filter=per-task` removed from active code. `TASK_TOOLS` allowlist deleted from `runner.py`. The per-task conditional in `runner.py` is now `allowed = None` unconditionally.
- `TOOL_FILTER_CHOICES = ("all",)` and `PROMPT_STYLE_CHOICES = ("minimal",)` in `run_experiment.py` — the params are still threaded (resume-key compatibility) but only one value is accepted.
- Sbatch case branches for `tools_per-task_minimal` and disabled `*_guided` variants removed from `run_condition_rtx.sbatch` and `run_condition_vllm_rtx.sbatch`.
- Forward-looking docs (`README.md`, `cluster-experimenting/README.md`, `EXPERIMENTS_FLOW.md`, `sweep4_plan_new_prompts.md`) cleaned of forward-looking references to retired axes.
- `development/CHANGELOG.md` is untouched — history is preserved.
- `prompts.py` docstring updated to flag that v5/v6/v7 is under review (VERDICT-trailer-drop regression).

All `pddl_eval/tests/*` continue to pass after the cleanup (`bash tests/verify.sh`).

## Hard constraints

- **No in-place edits to existing v0–v10 strings** in `PROMPT_TEMPLATES` — they're load-bearing for old trial replays. Append new indices only.
- **No unilateral methodology decisions.** Variant indexing, alias choices, prompt wording, system-prompt redesign, SKILL.md inclusion, matrix shape — every choice must be presented as options for user approval before code is written.
- **Branch before editing** — never commit to `main` directly (memory: `feedback_branch_before_commit`).
- **No `Co-Authored-By: Claude`** in commit messages (memory: `feedback_no_claude_credits_in_commits`).
- **PR-50 marketplace pin** held — `../pddl-copilot` at the sweep-4 SHA to avoid tool-surface drift.

## Matrix (held from sweep 4)

- Models: vLLM roster (Qwen3.5 4B/9B/14B/27B, Gemma3 12B/27B; see `cluster-experimenting/vllm_lookup`)
- Conditions: `no-tools`, `tools_all_minimal` (`tools_per-task` is retired)
- Think: `on`, `off`
- Tasks: 5 (above)
- Problems: same per-task corpus as sweep 4
- Cell count per paraphrase: 3 arms (above) × 2 think modes × 5 tasks × N problems × M models

## Code/infrastructure quick reference

| File | What lives there |
|---|---|
| `pddl_eval/prompts.py` | `PROMPT_TEMPLATES`, `PROMPT_TEMPLATES_TOOLS_OVERRIDE` (mechanism may be replaced), `ACTIVE_PROMPT_VARIANTS`, `WITH_TOOLS_SYSTEM` (flat `str`), `WITHOUT_TOOLS_SYSTEM` |
| `pddl_eval/runner.py` | `evaluate_one` template lookup at `:275`. Schedule emit-point `_emit_job` at `:546` — single chokepoint for any "skip this variant in this condition" filter. |
| `pddl_eval/schemas.py` | Pydantic models constraining no-tools JSON output: `SolveResponse`, `ValidateResponse`, `StateStep`, `SimulateResponse`, `TASK_SCHEMAS` |
| `pddl_eval/scoring.py` | `check_success`, `extract_verdict` (regex on `VERDICT: VALID/INVALID`), `FR_*` failure reasons, `_normalize_trajectory` invariants for simulate |
| `../pddl-copilot/plugins/*/skills/*/SKILL.md` | Tool documentation for system-prompt injection (in scope, per §4) |
| `development/sweep4_plan_new_prompts.md` | Historical sweep-4 plan; status banner added 2026-05-21. Treat as record. |

## Working-tree state (2026-05-21, branch `sweep4-new-prompts`)

Uncommitted-but-clean state after the 2026-05-21 cleanup:

- `pddl_eval/prompts.py` — `_GUIDED_SUFFIX` removed; `WITH_TOOLS_SYSTEM` now a flat `str`; docstring + v5 validate_domain comment flag the trailer-drop regression. v0–v10 prompt strings untouched. ACTIVE_PROMPT_VARIANTS still `(5, 6, 7)` — the new design will append new indices on top.
- `pddl_eval/runner.py` — `TASK_TOOLS` constant removed; per-task conditional replaced with `allowed = None`; `WITH_TOOLS_SYSTEM[prompt_style]` → `WITH_TOOLS_SYSTEM`.
- `run_experiment.py` — `TASK_TOOLS` import dropped; `TOOL_FILTER_CHOICES = ("all",)`; TASK_TOOLS validation block removed; argparse help text trimmed.
- `cluster-experimenting/run_condition_rtx.sbatch`, `run_condition_vllm_rtx.sbatch` — `tools_per-task_minimal` case branches and disabled `*_guided` blocks removed.
- `cluster-experimenting/submit_with_rtx.sh`, `lib/defaults.sh` — historical-tooling comments trimmed.
- `README.md`, `cluster-experimenting/README.md`, `EXPERIMENTS_FLOW.md` — per-task and guided sections collapsed; argparse table rows simplified.
- `development/sweep4_plan_new_prompts.md` — STATUS banner added at top pointing here; body left intact (history).
- `development/CHANGELOG.md` — **untouched** (history preserved per user direction).
- All tests pass: `bash tests/verify.sh`.

## What the next session should do

1. Read this summary in full.
2. **Literature review first.** Cite 4–6 papers on tool-use evaluation prompting. Extract concrete principles (format conventions, system-prompt structure, in-context examples, verdict trailers, tool-name disambiguation).
3. **Propose the system-prompt redesign with SKILL.md inlining** — per §4 above this is in scope, not deferred. Present options for: unified vs per-task system prompt, verbatim vs curated SKILL content, whether the no-tools branch sees SKILL content. User approval required before code.
4. **Draft new prompts** — 5 tasks × (neutral + steered), with explicit rationale per phrasing choice citing the literature. Present as a design doc before any `prompts.py` edits.
5. **Propose variant-index layout** — present options, ask the user to pick. (A previous session prematurely chose v11/v12/v13 neutral + v14/v15/v16 steered with a `STEERED_VARIANTS` frozenset; the user did not approve this.)
6. **Confirm the matrix shape** — three arms per (model × task × think × paraphrase). The user confirmed this once via AskUserQuestion in the previous session.
7. **Wait for user approval at each design checkpoint** before writing code.
8. Local smoke on a small model (e.g., `qwen3:0.6b` against laptop Ollama or CIS qwen08b vLLM endpoint) before cluster submit.
