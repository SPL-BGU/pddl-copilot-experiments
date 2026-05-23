# Sweep prompt bank — design doc

Dated 2026-05-21. Branch: `sweep4-new-prompts`. This is the design proposal for the clean prompt bank that supersedes sweep-3's v0/v1/v2 and sweep-4's v5/v6/v7. It is the deliverable of the prompt-engineering redesign briefed in `development/sweep_prompt_redesign_handoff.md`. **No code is changed until this doc is approved.**

The doc is structured for review, not for chronological narration: §1 establishes the literature/industry anchors that drive each design choice; §2 lists the four structural decisions (already pre-approved by the user in the 2026-05-21 question round) and re-checks them against the literature; §3 gives the actual prompt bank (system prompts + user prompts); §4 lists the files to touch and the validation plan.

## 1. Literature & industry-practice anchors

The user direction was: "focus on highly-regarded papers or companies. Their methodology is probably the narrative at the moment." I pulled primary sources for each load-bearing claim. Only verified passages are cited; secondary recall is omitted.

### 1.1 Anthropic — Define Tools docs (primary source)

URL: `https://platform.claude.com/docs/en/docs/agents-and-tools/tool-use/define-tools` (fetched 2026-05-21).

- **Tool descriptions are the dominant factor in tool performance.** Verbatim: "Provide extremely detailed descriptions. This is by far the most important factor in tool performance." Recommended length: "Aim for at least 3-4 sentences per tool description, more if the tool is complex."
- **Schema does not live in the system prompt.** The API "constructs a special system prompt from the tool definitions, tool configuration, and any user-specified system prompt." Tool definitions belong in `tools=[]`; the user system prompt is appended, not a duplicate.
- **Soft steering via user message is the documented pattern.** Verbatim: "If you would like the model to provide natural language context or explanations while still requesting that the model use a specific tool, you can use `{"type": "auto"}` for `tool_choice` (the default) and add explicit instructions in a `user` message. For example: `What's the weather like in London? Use the get_weather tool in your response.`" — **this is the canonical neutral-vs-steered design**: same body + one appended directive in the user prompt.
- **`tool_choice` semantics.** `auto` (default): model decides. `any`: must use one of the provided tools. `tool`: must use a specific tool. `none`: tools effectively disabled. Forced tool-use (`any`/`tool`) prefills the assistant message, suppressing free-text before the tool call; **not supported with extended thinking** (relevant since our matrix includes `think=on`).

### 1.2 Anthropic — "Writing tools for agents" engineering blog (primary source)

URL: `https://www.anthropic.com/engineering/writing-tools-for-agents`.

- "Prompt-engineering your tool descriptions and specs" ranks among "the most effective methods for improving tools. Even small refinements ... can yield dramatic improvements."
- "More tools don't always lead to better outcomes" — consolidation > proliferation.
- "Write descriptions as if teaching a new team member, making implicit context explicit."

### 1.3 BFCL — Berkeley Function-Calling Leaderboard methodology (primary source)

URL: `https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html`.

- **Function-calling models receive no explicit system prompt** — only `tools=[]`. Verbatim: "For all the function calling models, we did not supply any system prompt but instead, toggle the function calling mode on and put the function definitions where they should be."
- **Chat models without native function-calling get an explicit system prompt** introducing them to the function-list-in-context pattern: "You are an expert in composing functions. You are given a question and a set of possible functions ..."
- **BFCL evaluates three orthogonal dimensions**: relevance detection (should-call), function selection (which-tool), parameter filling (correct-args). **No no-tools baseline** — tools are always provided; tool-rejection is measured under "none of the provided functions are relevant."

### 1.4 ReAct (Yao et al. 2022) — primary structural pattern

- Interleaved Thought–Action–Observation. Reasoning is encouraged BEFORE the tool call, not after.
- 1–2 in-context exemplars are sufficient for the structural pattern to stick — the prompt teaches the *shape* of reasoning, not the *content*.

### 1.5 PDDL Copilot paper (Spector & Cohen, arXiv:2509.12987) — the project's research thesis

- The headline claim: LLMs fail at PDDL planning/validation/simulation; offloading to symbolic tools (planner, validator, simulator) is the fix. This is THE reason we run a no-tools arm at all — to provide the empirical floor against which the tool-using arm is compared.
- BFCL does not run a no-tools arm because their question is *function-calling correctness*, not *tool utility*. Our question is *tool utility for symbolic reasoning*, which inherently requires a no-tools baseline.

### 1.6 Synthesis — what these sources say about our three-arm matrix

| Arm | What it measures | Literature support |
|---|---|---|
| `(no-tools, neutral)` | Floor: model's unaided capability under a well-engineered, format-constrained prompt | PDDL Copilot paper (the floor is the headline research question); Anthropic schema-validation guidance argues for `format=` constraint as the way to enforce shape without tools |
| `(with-tools, neutral)` | BFCL **relevance detection**: does the model spontaneously call the right tool when its existence is known but not steered? | BFCL relevance-detection condition |
| `(with-tools, steered)` | BFCL **function selection + parameter filling**: with explicit steering, does the model select the right tool and pass the right arguments? | BFCL function-selection / parameter-filling; Anthropic's user-message-steering example is a direct exemplar |

**The fourth arm `(no-tools, steered)` is omitted** because steering text instructing the model to "call tool X" is incoherent when no tools are available — the steering directive points to a referent that doesn't exist. Empirically, the model would either ignore the directive (best case) or hallucinate a tool call (worst case), neither of which is informative.

**Verdict on the matrix shape: the three-arm matrix is well-grounded.** The decomposition cleanly separates the project's research question (PDDL Copilot's no-tools-vs-tools claim) from BFCL's within-tools error-mode decomposition. No alternative from the literature suggests collapsing or expanding it. Confirmed for go-ahead.

## 2. Decisions (pre-approved 2026-05-21)

The user pre-approved the four structural decisions via AskUserQuestion on 2026-05-21. Re-stated here for the record, each with the literature anchor that justifies it:

| # | Decision | Anchor |
|---|---|---|
| D1 | Three-arm matrix `(no-tools, neutral)` / `(with-tools, neutral)` / `(with-tools, steered)`. Neutral and steered user prompts differ by ONE appended directive clause; neutral text is identical across the no-tools and with-tools-neutral arms. | §1.6 above. Anthropic §1.1 user-message-steering pattern. |
| D2 | Variant indexing: v11/v12/v13 = neutral (three paraphrases); v14/v15/v16 = steered (three paraphrases, each appending one directive to the matching neutral). v14↔v11, v15↔v12, v16↔v13 are paired by index offset 3. | Preserves 3-paraphrase linguistic-robustness story from sweep-3/sweep-4. No literature anchor — internal continuity. |
| D3 | SKILL.md inlining: **curated, per-task** system prompt for the with-tools arm; minimal **mirror** system prompt for the no-tools arm. Verbose `verbose=` references and `save_plan` emphasis are dropped from the curated content (mismatch with harness, see §3.1). | Anthropic §1.1 "tool descriptions are the dominant factor"; §1.2 engineering blog "implicit context explicit." Per-task isolates attribution. |
| D4 | `(v_steered, no-tools)` cells are NOT emitted. One-line frozenset gate at `runner.py:_emit_job` (`STEERED_VARIANTS = frozenset({14, 15, 16})`; skip when `not with_tools and pv in STEERED_VARIANTS`). | No literature; pragmatic — saves ~50% of no-tools cells, no methodological loss. |

### 2.1 Why per-task SKILL inlining over unified

Three-paragraph rationale because the user explicitly asked the literature to settle this.

The Anthropic Define-Tools page (§1.1) tells us tool descriptions belong in `tools=[]`, not the system prompt. The harness already gives the model the schema via `tools=[]` (Ollama chat API). What goes into the system prompt is the *behavior policy* — when to call, why to call, what to do if the tool fails. Per-task lets that policy be tight: solver-relevant policy for `solve`, validator-relevant policy for `validate_*` and `simulate`. A unified prompt would mix policy for tools the model doesn't need for the current task, costing tokens and diluting attention.

The engineering blog (§1.2) warns that "more tools don't always lead to better outcomes." A unified prompt would surface all five MCP tools to the model on every task; per-task surfaces only the relevant subset (with the schema for the others still being passed in `tools=[]` — the model can call them, but the system prompt doesn't advertise them). This is a strictly weaker advertising signal, which our scoring is set up to detect via `FR_TOOL_NOT_SELECTED`. If a model "could" have spontaneously used a non-advertised tool, the data will show it; per-task does not block the call, only the recommendation.

Per-task does introduce one piece of plumbing (a `WITH_TOOLS_SYSTEM_BY_TASK` mapping + a lookup in `runner.py`), but the lookup is one line with a fallback to the existing `WITH_TOOLS_SYSTEM` flat string. The complexity cost is small and the attribution cleanliness is the standard methodology in published tool-use evaluations (BFCL's per-category prompts, AppWorld's task-specific instructions).

### 2.2 Why curated, not verbatim, SKILL content

The marketplace SKILL.md files document the **public** MCP interface — including the `verbose=True|False` parameter that toggles between the full structured response and a slim one. **The experiment harness strips `verbose` from the tool schema and pins it to `False` at dispatch** (`pddl_eval/chat.py:86,131,150`). Inlining the SKILL verbatim would tell the model about a knob it cannot see in the schema, which is silently misleading. Curated content drops the `verbose` paragraphs and the `save_plan` step (which the harness exposes but the grader does not reward).

Curated content also drops the **parser plugin SKILL** entirely — the harness only loads `pddl-solver` and `pddl-validator` (`run_experiment.py:121`). Inlining the parser SKILL would advertise tools (`get_trajectory`, `check_applicable`, etc.) that are not in the runtime tool surface.

The curated content keeps: (a) the policy claim ("you cannot plan/validate/simulate from training alone, use the tool"), (b) the tool name and one-line description, (c) the workflow (which tool to call, what arguments to pass), (d) the argument-shape disambiguator for polymorphic tools (especially the `plan` argument for `validate_plan`).

### 2.3 Why a no-tools mirror system prompt instead of a minimal stub

Token-cost is one of the four headline metrics, measured on **output** tokens — so system-prompt length is not the metric. The reason to mirror anyway is methodological isolation: the (no-tools, neutral) vs (with-tools, neutral) comparison is the central PDDL Copilot claim. If the no-tools arm has a 60-token system prompt and the with-tools arm has a 400-token SKILL-injected system prompt, the comparison confounds "tool availability" with "instruction-surface differential." A mirror prompt — same role framing, same task focus, similar length, just stating "no tools, reason inline, output JSON to schema" — removes the differential. The two arms then differ only by (i) tools=[] passed to the chat API, (ii) the tool-mention in the system text. That's as close to an isolation as the design allows.

## 3. The prompt bank

### 3.1 System prompts

**Byte-stability rule.** The existing `WITH_TOOLS_SYSTEM` (a flat `str`, current body at `pddl_eval/prompts.py:46-50`) and `WITHOUT_TOOLS_SYSTEM` (at `:52-56`) **are NOT modified**. They remain byte-identical to their 2026-05-21-cleanup values so that any researcher who re-runs a v0–v10 trial (replay or regen mode) sees the same system text the original run used. The new system prompts for v11–v16 land under **new constant names** (`WITH_TOOLS_SYSTEM_BY_TASK`, `WITHOUT_TOOLS_SYSTEM_V11`). The runner picks which constant to use at dispatch time by variant index — see §4.1 runner change.

#### `WITH_TOOLS_SYSTEM_BY_TASK` (5 entries, curated SKILL per task — applied only to v11–v16)

```python
WITH_TOOLS_SYSTEM_BY_TASK: dict[str, str] = {
    "solve": (
        "You are a PDDL planning assistant. You CANNOT generate correct plans "
        "from training alone — LLMs fail at long-horizon planning (arXiv:2509.12987). "
        "Always use a planner tool to produce the plan.\n"
        "Available planners:\n"
        "  - classic_planner(domain, problem): Fast Downward; for classical PDDL "
        "    (no :functions).\n"
        "  - numeric_planner(domain, problem): ENHSP; for PDDL 2.1 with numeric "
        "    fluents (:functions, increase, decrease).\n"
        "Workflow: (1) read the domain to decide which planner; "
        "(2) call the planner with the FULL PDDL text as the `domain` and "
        "`problem` arguments — not file names or short identifiers; "
        "(3) return the plan exactly as the tool reports it. "
        "Do NOT invent a plan if the tool fails — report the failure."
    ),
    "validate_domain": (
        "You are a PDDL validation assistant. You CANNOT reliably check PDDL "
        "syntax from training alone. Always call the validation tool:\n"
        "  - validate_pddl_syntax(domain, problem?, plan?): checks PDDL syntax "
        "    and consistency. The tool is polymorphic — it validates whichever "
        "    layer you supply. For this task, pass `domain` only.\n"
        "Pass the FULL domain text as the `domain` argument."
    ),
    "validate_problem": (
        "You are a PDDL validation assistant. You CANNOT reliably check PDDL "
        "syntax from training alone. Always call the validation tool:\n"
        "  - validate_pddl_syntax(domain, problem?, plan?): checks PDDL syntax "
        "    and consistency. The tool is polymorphic — it validates whichever "
        "    layer you supply. For this task, pass `domain` AND `problem`.\n"
        "Pass the FULL text of both arguments — missing `problem` causes the "
        "tool to validate only the domain."
    ),
    "validate_plan": (
        "You are a PDDL validation assistant. You CANNOT reliably check plan "
        "correctness from training alone. Always call the validation tool:\n"
        "  - validate_pddl_syntax(domain, problem?, plan?): the tool is "
        "    polymorphic — it validates whichever layer you supply. For "
        "    plan validation you MUST pass ALL THREE of `domain`, `problem`, "
        "    AND `plan`.\n"
        "Pass the FULL text of every argument — a domain-only or domain+problem "
        "call returns the domain's verdict, NOT the plan's."
    ),
    "simulate": (
        "You are a PDDL simulation assistant. You CANNOT reliably trace state "
        "transitions through a plan from training alone — LLMs fail at tracking "
        "predicate sets through action sequences. Always call:\n"
        "  - get_state_transition(domain, problem, plan): simulates plan "
        "    execution step-by-step, returns per-step state and full trajectory.\n"
        "Pass the FULL text of `domain`, `problem`, and `plan` — partial inputs "
        "produce a partial trajectory."
    ),
}

# Defensive fallback for any new task not in WITH_TOOLS_SYSTEM_BY_TASK
# (all 5 tasks are covered today; fallback fires only if a future task is
# added without a mapping entry).
WITH_TOOLS_SYSTEM_FALLBACK: str = (
    "You are a PDDL planning assistant with access to planning, validation, "
    "and simulation tools. Always use the provided tools rather than reasoning "
    "from training alone — LLMs fail at PDDL reasoning (arXiv:2509.12987). "
    "Pass the FULL PDDL text as arguments, not file names or short identifiers."
)

# UNCHANGED — preserved byte-stable for v0–v10 replay. Do not edit.
# (Body at pddl_eval/prompts.py:46-50 today.)
# WITH_TOOLS_SYSTEM: str = "You are a PDDL planning assistant with access to planning tools. ..."
```

#### `WITHOUT_TOOLS_SYSTEM_V11` (unified mirror — applied only to v11–v16)

```python
WITHOUT_TOOLS_SYSTEM_V11: str = (
    "You are a PDDL planning, validation, and simulation assistant. PDDL "
    "tools are NOT available in this evaluation — you must analyze, plan, "
    "validate, and simulate using your own reasoning. Your output must "
    "conform to the JSON schema provided by the format constraint; the "
    "schema is the ground-truth shape the grader expects. "
    "When the user prompt requests a VERDICT line, end your response with "
    "exactly one line: VERDICT: VALID or VERDICT: INVALID."
)

# UNCHANGED — preserved byte-stable for v0–v10 replay. Do not edit.
# (Body at pddl_eval/prompts.py:52-56 today.)
# WITHOUT_TOOLS_SYSTEM = "You are a PDDL planning assistant. ..."
```

The mirror is intentionally shorter than the per-task `WITH_TOOLS_SYSTEM_BY_TASK` strings because (a) there is no per-task tool documentation to mirror, (b) the role framing + format-constraint claim + VERDICT-line claim is what generalises across the five tasks. The handoff §4 open question "should the no-tools branch see SKILL content" is resolved as **no** (the SKILL content is tool documentation; mirroring it would hand the model irrelevant content).

**Variant-gated dispatch.** The runner picks system prompts by variant index, NOT globally:
- `prompt_variant < 11` (i.e. v0–v10) → keeps using the unchanged `WITH_TOOLS_SYSTEM` / `WITHOUT_TOOLS_SYSTEM` constants. Replay byte-stability preserved.
- `prompt_variant >= 11` (i.e. v11–v16) → uses `WITH_TOOLS_SYSTEM_BY_TASK.get(task, WITH_TOOLS_SYSTEM_FALLBACK)` / `WITHOUT_TOOLS_SYSTEM_V11`.

This gating is a one-line conditional in `runner.py:284` (see §4.1) — the variant index is already available there.

### 3.2 User prompts — `PROMPT_TEMPLATES[task]` indices 11/12/13 (neutral, no-tools branch & with-tools-neutral arm)

Each task has three paraphrases (linguistic robustness). The neutral text is byte-identical between the no-tools and with-tools-neutral arms.

#### `solve` (neutral, v11/v12/v13)
- **v11**: `Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. \`(pick-up a)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}`
- **v12**: `Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. \`(unstack a b)\`.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}`
- **v13**: `Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. \`(stack a b)\`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}`

Rationale: action wire-format teaching (one example per paraphrase) addresses the sweep-3 `.local/prompts_review.md` finding 6 (solve no-tools doesn't teach action format).

#### `validate_domain` (neutral, v11/v12/v13)
- **v11**: `Check if this PDDL domain definition has valid syntax.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v12**: `Validate the following PDDL domain for syntactic correctness.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v13**: `Is this PDDL domain syntactically correct?\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`

Rationale: VERDICT trailer reinstated (sweep-4 regression fix — the Pydantic `format=` constraint is a soft logit bias and the `extract_verdict` regex fallback needs the trailer to anchor on). Trailing punctuation normalised to `.` / `?` (not `:` or `Please check.`) so the steered counterparts in §3.3 are *pure appends* — no edits to the neutral text, only an additional directive sentence.

#### `validate_problem` (neutral, v11/v12/v13)
- **v11**: `Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v12**: `Validate the syntax of this PDDL problem against its domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v13**: `Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`

#### `validate_plan` (neutral, v11/v12/v13)
- **v11**: `Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v12**: `Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v13**: `Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`

#### `simulate` (neutral, v11/v12/v13)
- **v11**: `Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with \`action\` empty. Each later step records the action executed. \`state.boolean\` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. \`(on a b)\`; \`state.numeric\` is the fluents map.\nExample step: {{"step": 0, "action": "", "state": {{"boolean": ["(on a b)", "(clear c)"], "numeric": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}`
- **v12**: `Step through this plan action by action. For each step emit \`action\` (the action just executed, or empty for step 0) and \`state.boolean\` listing every currently-true predicate in parenthesised PDDL form, e.g. \`(on a b)\`.\nExample step: {{"step": 1, "action": "(unstack a b)", "state": {{"boolean": ["(holding a)", "(clear b)"], "numeric": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}`
- **v13**: `Show the state at each step of this plan. Step 0 = initial state with empty \`action\`. Each \`state.boolean\` entry lists every predicate that holds in that state, parenthesised and lowercase; \`state.numeric\` is the fluents map (empty for purely-symbolic domains).\nExample step: {{"step": 0, "action": "", "state": {{"boolean": ["(ontable a)", "(clear a)"], "numeric": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}`

Rationale: wire-format teaching encodes the three invariants `_normalize_trajectory` checks: step 0 = initial state, action="" on step 0, full truth-set per step, parenthesised lowercase form (sweep-3 review finding 5). The one-step JSON example is a ReAct-style structural exemplar (§1.4).

### 3.3 User prompts — `PROMPT_TEMPLATES_TOOLS_OVERRIDE[task]` indices 14/15/16 (steered, with-tools-steered arm)

Each steered prompt is the matching neutral prompt with **one appended directive** before the domain/problem/plan body. The diff is one sentence. The directive names the tool category + the required argument shape.

#### `solve` (steered, v14/v15/v16)
- **v14** (← v11 + directive): `Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. \`(pick-up a)\`. Call a planner tool with the FULL domain and problem text as its \`domain\` and \`problem\` arguments — not file names or short identifiers.\n\nDomain:\n{domain}\n\nProblem:\n{problem}`
- **v15** (← v12 + directive): `Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. \`(unstack a b)\`. Use the planner tool — pass the full PDDL text as the planner's \`domain\` and \`problem\` arguments.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}`
- **v16** (← v13 + directive): `Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. \`(stack a b)\`. Use the planner tool — pass the complete PDDL text as the \`domain\` and \`problem\` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}`

#### `validate_domain` (steered, v14/v15/v16)
- **v14** (← v11 + directive): `Check if this PDDL domain definition has valid syntax. Call the validation tool with the full domain text as its \`domain\` argument.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v15** (← v12 + directive): `Validate the following PDDL domain for syntactic correctness. Invoke the validation tool with the full domain text as the \`domain\` argument.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v16** (← v13 + directive): `Is this PDDL domain syntactically correct? Decide by calling the validation tool with the full domain text as the \`domain\` argument.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`

#### `validate_problem` (steered, v14/v15/v16)
- **v14** (← v11 + directive): `Check if this PDDL problem has valid syntax given the domain. Call the validation tool with the full \`domain\` AND \`problem\` arguments — both are required (domain-only calls do not check the problem).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v15** (← v12 + directive): `Validate the syntax of this PDDL problem against its domain. Invoke the validation tool with both \`domain\` and \`problem\` as full texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v16** (← v13 + directive): `Is this PDDL problem file syntactically correct for the given domain? Decide by calling the validation tool with both \`domain\` and \`problem\` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`

#### `validate_plan` (steered, v14/v15/v16) — argument-shape teaching is critical (sweep-3 review finding 2)

User-selected wording from the 2026-05-21 design review: name the failure mode explicitly so the model understands *why* `plan` must be passed, not just that it must.

- **v14** (← v11 + directive): `Validate whether this plan is correct for the given domain and problem. Call the validation tool with ALL THREE arguments — \`domain\`, \`problem\`, AND \`plan\`. The tool grades only the layers you supply: if you omit \`plan\`, it checks domain/problem syntax but never tests whether the plan actually solves the problem (and will return VALID even for a junk plan).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v15** (← v12 + directive): `Check if the following plan solves the PDDL problem. Invoke the validation tool with ALL THREE arguments — \`domain\`, \`problem\`, AND \`plan\`. The tool grades only the layers you supply: if you omit \`plan\`, it checks domain/problem syntax but never tests whether the plan actually solves the problem (and will return VALID even for a junk plan).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`
- **v16** (← v13 + directive): `Is this plan valid for the given planning problem? Decide by calling the validation tool with ALL THREE arguments — \`domain\`, \`problem\`, AND \`plan\`. The tool grades only the layers you supply: if you omit \`plan\`, it checks domain/problem syntax but never tests whether the plan actually solves the problem (and will return VALID even for a junk plan).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID`

Rationale: the selected wording is a **two-sentence directive** (vs the one-sentence directive used for the other 12 task×paraphrase steered pairs). Justified exception because `validate_plan` is the only task where the dominant sweep-3 failure mode (`.local/prompts_review.md` finding 2) was specifically the model not understanding *what happens* when `plan` is omitted, not just that it should be included. Naming the consequence ("returns VALID even for a junk plan") is the steering signal that distinguishes this from a generic "include all arguments" reminder.

For methodology cleanliness: the inserted directive is still a **contiguous block** appended after the neutral sentence and before the `\n\nDomain:` body — it is a pure insert, no edits to the neutral text. The "near-identical" diff property holds; the directive is just longer than for other tasks.

Note: the v14/v15/v16 steered directives are byte-identical across the three paraphrases by design. The paraphrase axis lives in the neutral *opening* clause ("Validate whether…" / "Check if…" / "Is this plan…") which the steered prompts preserve; varying the directive text across paraphrases would mix two sources of variance (paraphrase + directive wording) and dilute the steering measurement. Same-directive-across-paraphrases isolates the steering effect.

#### `simulate` (steered, v14/v15/v16)
- **v14** (← v11 + directive): `Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with \`action\` empty. Each later step records the action executed. \`state.boolean\` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. \`(on a b)\`; \`state.numeric\` is the fluents map.\nExample step: {{"step": 0, "action": "", "state": {{"boolean": ["(on a b)", "(clear c)"], "numeric": {{}}}}}}\nCall the state-transition tool with the full \`domain\`, \`problem\`, and \`plan\` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}`
- **v15** (← v12 + directive): `Step through this plan action by action. For each step emit \`action\` (the action just executed, or empty for step 0) and \`state.boolean\` listing every currently-true predicate in parenthesised PDDL form, e.g. \`(on a b)\`.\nExample step: {{"step": 1, "action": "(unstack a b)", "state": {{"boolean": ["(holding a)", "(clear b)"], "numeric": {{}}}}}}\nInvoke the state-transition tool with the full \`domain\`, \`problem\`, and \`plan\` texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}`
- **v16** (← v13 + directive): `Show the state at each step of this plan. Step 0 = initial state with empty \`action\`. Each \`state.boolean\` entry lists every predicate that holds in that state, parenthesised and lowercase; \`state.numeric\` is the fluents map (empty for purely-symbolic domains).\nExample step: {{"step": 0, "action": "", "state": {{"boolean": ["(ontable a)", "(clear a)"], "numeric": {{}}}}}}\nUse the state-transition tool with the full PDDL texts (\`domain\`, \`problem\`, \`plan\`).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}`

The wire-format teaching is kept in steered (not stripped) because the methodology rule is "near-identical text"; the model under with-tools is free to call the tool and ignore the wire-format teaching (its output will be the tool's result, which already conforms).

### 3.4 Properties to verify by automated test (enforced; not just a spot-check)

These properties are encoded as assertions in `pddl_eval/tests/test_prompts.py` (new file) and run via `bash tests/verify.sh`. They fail the build if the spec drifts.

- **Pure-append property.** For each task `t` and each paraphrase `k ∈ {0, 1, 2}`: the steered template `PROMPT_TEMPLATES_TOOLS_OVERRIDE[t][14+k]` is the matching neutral template `PROMPT_TEMPLATES[t][11+k]` with a **contiguous directive block inserted** before the body anchor (`\n\nDomain:` / `\n\n{domain}`) — and zero edits to any other character of the neutral text. Implementation: find the position where neutral and steered first diverge; verify that everything after the divergence point splits cleanly into (a) inserted directive text + (b) remainder that equals the matching neutral substring byte-for-byte. The directive block is one sentence for 12 of the 15 pairs and two sentences for `validate_plan` v14/v15/v16 (justified exception, see §3.3 `validate_plan`); the test asserts the *contiguous insert + no other edits* invariant, not the sentence count.
- **VERDICT-trailer presence.** All `validate_*` templates (neutral AND steered, both indices 11..16) contain the literal substring `VERDICT: VALID or VERDICT: INVALID` exactly once.
- **Simulate wire-format example.** All `simulate` templates (neutral AND steered) contain the literal substring `"step":` AND `"state":` AND `"boolean":` AND `"numeric":` (the JSON example shape).
- **Solve action example.** All `solve` templates (neutral AND steered) contain at least one parenthesised PDDL action example matching `(pick-up …)` OR `(unstack …)` OR `(stack …)`.
- **No harness-mismatched content.** No template, system prompt, or `WITH_TOOLS_SYSTEM_BY_TASK` entry contains the substrings `verbose=`, `save_plan`, `get_trajectory`, `check_applicable`, `inspect_domain`, `inspect_problem`, or `normalize_pddl` (these are not in the harness's runtime tool surface).
- **Emit-skip behavior.** Unit test for `_emit_job`: synthesise inputs for all `(with_tools, prompt_variant) ∈ {True, False} × {11, 12, 13, 14, 15, 16}` and assert that exactly the four combinations `(False, 14)`, `(False, 15)`, `(False, 16)` are skipped; the other 9 are emitted.

## 4. Implementation — files to touch, validation, rollout

### 4.1 Files to modify

| File | Action | Description |
|---|---|---|
| `pddl_eval/prompts.py` | modify | **Additions only, no in-place edits** to existing strings (v0–v10 byte-stable per `feedback_branch_before_commit` + sweep-4 plan §"Methodology guardrail"). Specifically: append v11/v12/v13 (neutral) and v14/v15/v16 (steered) to each task's `PROMPT_TEMPLATES` list; populate `PROMPT_TEMPLATES_TOOLS_OVERRIDE[task][14..16]` only; add new constants `WITH_TOOLS_SYSTEM_BY_TASK` (dict, §3.1), `WITH_TOOLS_SYSTEM_FALLBACK` (str, §3.1), `WITHOUT_TOOLS_SYSTEM_V11` (str, §3.1); leave `WITH_TOOLS_SYSTEM` and `WITHOUT_TOOLS_SYSTEM` byte-identical to current values; flip `ACTIVE_PROMPT_VARIANTS = (11, 12, 13, 14, 15, 16)`; add `STEERED_VARIANTS = frozenset({14, 15, 16})`; update module docstring to reflect new design. |
| `pddl_eval/runner.py` | modify | `evaluate_one` template lookup at `:275` already uses `PROMPT_TEMPLATES_TOOLS_OVERRIDE` — no change needed. **Replace** the system-prompt selection at `:284` with a variant-gated lookup:<br>`if prompt_variant >= 11:`<br>&nbsp;&nbsp;&nbsp;&nbsp;`system = (WITH_TOOLS_SYSTEM_BY_TASK.get(task, WITH_TOOLS_SYSTEM_FALLBACK)` &nbsp;`if with_tools else WITHOUT_TOOLS_SYSTEM_V11)`<br>`else:`<br>&nbsp;&nbsp;&nbsp;&nbsp;`system = WITH_TOOLS_SYSTEM if with_tools else WITHOUT_TOOLS_SYSTEM`<br>This gating preserves byte-stability for v0–v10 replays. **Add** the emit-point skip at `_emit_job` (around `:546`): `if not with_tools and prompt_variant in STEERED_VARIANTS: continue` before yielding the job. Imports updated to bring in `WITH_TOOLS_SYSTEM_BY_TASK`, `WITH_TOOLS_SYSTEM_FALLBACK`, `WITHOUT_TOOLS_SYSTEM_V11`, and `STEERED_VARIANTS`. |
| `run_experiment.py` | modify | `num_variants` default already reads `len(ACTIVE_PROMPT_VARIANTS)`, so flipping the tuple just works. Update argparse help text at `:599–606` to note the new active set (`v11/v12/v13` neutral + `v14/v15/v16` steered). |
| `pddl_eval/tests/test_*.py` | modify | Update or add tests: (a) every `ACTIVE_PROMPT_VARIANTS` index has a template entry; (b) `STEERED_VARIANTS ⊂ keys(PROMPT_TEMPLATES_TOOLS_OVERRIDE[task])` for all tasks; (c) the property checklist in §3.4 (diff-by-one-sentence, VERDICT trailer presence, JSON-example presence). |
| `development/CHANGELOG.md` | append | Dated entry (post 2026-05-21 cleanup): three-arm matrix rationale, link to this design doc, list of v11..v16 indices and arm mapping, note that sweep-3 (v0/v1/v2) and sweep-4 (v5/v6/v7/v8/v9/v10) remain as historical reference corpora and are not invalidated. |
| `EXPERIMENTS_FLOW.md` | modify | §4.1 paraphrase-count + §11 paper-diff updated to reference three-arm matrix and the literature anchors above. |
| `development/sweep4_plan_new_prompts.md` | leave | Already STATUS-banner'd as historical context. No edit. |

### 4.2 Validation plan

1. **Static checks** (in `bash tests/verify.sh`): the §3.4 property tests fail loudly if the spec drifts. Run before commit.
2. **Local smoke** (laptop Ollama, smallest model `qwen3:0.6b`, 1 problem per task): `python run_experiment.py --partial 1 --models qwen3:0.6b --conditions both --tool-filter all --marketplace-path ../pddl-copilot`. Eyeball one trial per (task × variant × condition) in `trials.jsonl` to confirm: (a) v11/v12/v13 no-tools uses the neutral text; (b) v11/v12/v13 with-tools uses the same neutral text but invokes tools; (c) v14/v15/v16 with-tools uses the steered text; (d) v14/v15/v16 no-tools cells are NOT emitted (smoke-output assertion).
3. **CIS vLLM smoke** (qwen08b endpoint, single-cell): one cell per arm × one model. Confirms the three-arm matrix runs end-to-end on the cluster's vLLM path before submitting the full sweep.
4. **Full submit deferred until §4.2 #1–#3 all pass.**

### 4.3 Compatibility with existing results

- **Sweep-3 (v0/v1/v2) corpus**: byte-stable, untouched. Trial-replay (re-execution) sees the same prompt strings AND the same system-prompt constants — variant-gated dispatch at `runner.py:284` keeps v0–v10 routed to the unchanged `WITH_TOOLS_SYSTEM` / `WITHOUT_TOOLS_SYSTEM` constants.
- **Sweep-4 (v5/v6/v7) corpus**: same — byte-stable templates + byte-stable system prompts for variants <11. Listed as historical.
- **Sweep-4.1 (v8/v9/v10) corpus**: same — byte-stable on both axes. Listed as historical.
- **New sweep (v11..v16)**: disjoint variant indices. Resume-key collisions are zero. Variant-gated dispatch routes these to the new system prompts (`WITH_TOOLS_SYSTEM_BY_TASK` / `WITHOUT_TOOLS_SYSTEM_V11`).
- **MCP tool surface**: marketplace pin (`PR-50`, marketplace 1.3.0) remains the same. No tool-surface drift.
- **`WITH_TOOLS_SYSTEM` / `WITHOUT_TOOLS_SYSTEM` constants**: kept byte-identical. No code path that uses them is altered for variants <11.
- **New constants** (`WITH_TOOLS_SYSTEM_BY_TASK`, `WITH_TOOLS_SYSTEM_FALLBACK`, `WITHOUT_TOOLS_SYSTEM_V11`, `STEERED_VARIANTS`): additive only.

### 4.4 Rollout sequence

1. Write code per §4.1; run `bash tests/verify.sh`.
2. Local smoke per §4.2 #2.
3. Commit on `sweep4-new-prompts` branch — message describes the design doc + three-arm rationale. No Claude credits per `feedback_no_claude_credits_in_commits`.
4. CIS vLLM smoke per §4.2 #3.
5. Open PR `sweep4-new-prompts → main`; request user review.
6. After PR merge: cluster submit via `cluster-experimenting/submit_full_sweep.sh` — matrix is sweep-4 matrix (5 models × 2 conditions × 2 think × 5 tasks × problems) × 6 variants. Steered/no-tools cells are skipped at emit, so the effective matrix is `5 × {(no-tools × 3 neutral) + (with-tools × 6 all)} × 2 × 5 × N` per model.

## 5. Risks

- **Per-task system prompts make the `SKILL` content the system-prompt-by-task baseline**, not the schema. Future marketplace SKILL updates will not auto-propagate. Mitigation: when re-pinning the marketplace, audit the curated SKILL content against the new SKILL.md by hand; treat as a small chore at re-pin time, not a hidden risk.
- **The `validate_plan` steered directive explicitly names `plan` as a required argument**. If a model still drops `plan` after this, that's a model failure to report, not a prompt failure to fix (per `feedback_tool_adherence_is_data`).
- **Wire-format teaching in `simulate` steered is redundant** under with-tools (the tool result is the trajectory). Kept anyway because the methodology rule is "near-identical text" — stripping it would create more than a one-sentence diff between neutral and steered.
- **No-tools mirror system prompt is asymmetric to with-tools per-task** by design — the with-tools system has task-specific tool docs; the no-tools system is generic. This is the deliberate "instruction surface contains task-specific content only when there are task-specific tools" choice, justified in §2.3.
- **Emit-skip frozenset gate must be tested**. If the gate fires too eagerly (skipping with-tools cells) or too lazily (emitting no-tools steered cells), the entire matrix is wrong. The smoke check in §4.2 #2 catches this — but the runner must also have a unit test for `_emit_job` that asserts the skip behavior on synthetic input.

## 6. Open questions for user sign-off

None — all four structural decisions were pre-approved in the 2026-05-21 question round. **What needs user approval now:**

1. **Does this prompt bank fully address the doubts?** If any prompt's wording reads off, flag it before code changes — easier to fix here than in `prompts.py`.
2. **Are there literature sources the user wants me to incorporate that I missed?** I anchored on Anthropic + BFCL + ReAct + the PDDL Copilot paper. τ-bench, Toolformer, Gorilla, AppWorld, ToolBench were considered but their primary-source content was inaccessible via WebFetch (abstracts only); I declined to pad with secondary recall.
3. **Is the `validate_plan` steered directive aggressive enough?** "all three are required (a domain-only or domain+problem call returns the domain's verdict, NOT the plan's)" — this is the sharpest argument-shape teaching I can write without crossing into one-shot example territory. If the user wants a one-shot example (a fake `validate_pddl_syntax(domain=..., problem=..., plan="...")` call shape), I can add it; the trade-off is token cost vs steering strength.
4. **Should `WITH_TOOLS_SYSTEM_BY_TASK` mention the `format=` constraint?** Currently it doesn't (the schema is in `tools=[]`). Could add a sentence "Your final natural-language response should summarise the tool's verdict" to anchor the post-tool-call response, but Anthropic's docs (§1.1) note that with `tool_choice=auto` (our setting) the model naturally produces a brief assistant message before/after tool calls; no extra instruction needed. Leaning toward keeping it terse — but flag if the user wants more.
