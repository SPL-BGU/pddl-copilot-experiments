"""System prompts + per-task templates (Section 4 of the paper).

STATUS (2026-05-23): sweep-5 active set is v11/v12/v13 (neutral) + v14/v15/v16
(steered). Marketplace pin: pddl-copilot @ 2850bc4 (marketplace 1.4.0,
validator 3.0.0). The full design doc with literature anchors, hypothesis
pre-registration, and per-task rationale is at
`development/sweep_prompt_bank_design.md`.

History (each set preserved verbatim for trial-replay byte-stability):

  * v0/v1/v2 — sweep-3 active set.
  * v3/v4 — disabled; kept to preserve index reservation.
  * v5/v6/v7 — sweep-4 active set. Addressed six prompt-review leaks but
    dropped the VERDICT trailer in `validate_*` no-tools, which regressed
    `FR_FORMAT_PARSE_FAIL` on hybrid-architecture models (the
    `format=ValidateResponse` constraint isn't fully enforced under
    vLLM `guided_json` for Mamba-hybrid Qwen3.5/3.6 — the regex fallback
    `scoring.extract_verdict` was the safety net).
  * v8/v9/v10 — sweep-4.1 reserved indices, byte-identical aliases of
    v5/v6/v7's no-tools with NO entries in PROMPT_TEMPLATES_TOOLS_OVERRIDE
    (un-steered baseline).
  * v11/v12/v13 — sweep-5 NEUTRAL set. Used by BOTH the no-tools arm and
    the with-tools-neutral arm (text byte-identical across arms — H1
    isolates tool availability from prompt content). Restores the VERDICT
    trailer for `validate_*` (the sweep-4 regression fix). Includes wire-
    format teaching for `simulate` (no-tools branch).
  * v14/v15/v16 — sweep-5 STEERED set. Pure-append directives on top of
    v11/v12/v13: each adds exactly one sentence naming the matching
    marketplace-1.4.0 tool (`classic_planner`/`numeric_planner` for solve;
    `validate_domain`/`validate_problem`/`validate_plan` 1:1 with task
    names; `get_state_transition` for simulate). The validator split made
    polymorphism unreachable, so the steered directives no longer need
    multi-sentence warnings. Base-list entries v14..v16 are byte-equal
    aliases of v11..v13 (defensive fallback); the steered text lives in
    PROMPT_TEMPLATES_TOOLS_OVERRIDE.

Variant-gated dispatch (`runner.py:evaluate_one`): for v14..v16 the
override always applies regardless of `with_tools`. This lets the sweep-5
control arm `(no-tools, v14..v16)` see the steered text — necessary for
H4 ("steered directive alone does not move the no-tools floor"). The
emit-skip frozenset `STEERED_VARIANTS` gates which condition-variant
combinations are emitted (sweep-5 main: skip; sweep-5 control with
`--include-no-tools-steered`: emit).

v5–v16 are appended (not in-place edits) so v0–v2 indices remain
byte-stable with the sweep-3 corpus.

`ACTIVE_PROMPT_VARIANTS` selects which subset of templates per task runs.
"""


# Legacy flat constants — preserved byte-stable for v0–v10 replay.
# Do not edit. (Variant-gated dispatch in runner.py routes v0..v10 cells
# here, v11..v16 cells to the per-task dicts below.)
WITH_TOOLS_SYSTEM: str = (
    "You are a PDDL planning assistant with access to planning tools. "
    "Your ONLY way to get information or solve problems is by calling the "
    "provided tools ONE AT A TIME — never guess or create plan details yourself."
)

WITHOUT_TOOLS_SYSTEM = (
    "You are a PDDL planning assistant. You must analyze PDDL problems, "
    "validate syntax, create plans, and simulate state transitions all on "
    "your own, without any external tools."
)


# ---------------------------------------------------------------------------
# Sweep-5 per-task system prompts (Option C — thin policy stubs, 3 sentences
# each, no tool signatures, no argument descriptions). Tool schemas live in
# `tools=[]` per Anthropic's documented contract; the marketplace 1.4.0 raised
# the per-tool description bar at that source so the experiments repo no
# longer restates the schema. See `development/sweep_prompt_bank_design.md`
# §3.1 / §3.2 for the rationale.
#
# Mirror property: each WITHOUT entry shares the role-framing first sentence
# with the matching WITH entry; both are 3 sentences; differ only on the
# policy claim ("use the tool" vs "use your own reasoning") + output-shape
# reminder where applicable. Enforced by tests/test_prompts.py.
# ---------------------------------------------------------------------------

WITH_TOOLS_SYSTEM_BY_TASK: dict[str, str] = {
    "solve": (
        "You are a PDDL planning assistant. LLMs cannot reliably generate "
        "correct plans from training alone (arXiv:2509.12987). Use the "
        "available planner tool to produce the plan."
    ),
    "validate_domain": (
        "You are a PDDL validation assistant. LLMs cannot reliably check "
        "PDDL syntax from training alone. Use the available validation tool "
        "to check the domain."
    ),
    "validate_problem": (
        "You are a PDDL validation assistant. LLMs cannot reliably check "
        "PDDL syntax from training alone. Use the available validation tool "
        "to check the problem against its domain."
    ),
    "validate_plan": (
        "You are a PDDL validation assistant. LLMs cannot reliably check "
        "plan correctness from training alone. Use the available validation "
        "tool to check whether the plan solves the problem."
    ),
    "simulate": (
        "You are a PDDL simulation assistant. LLMs cannot reliably trace "
        "state transitions through a plan from training alone. Use the "
        "available simulation tool to compute the trajectory."
    ),
}

WITHOUT_TOOLS_SYSTEM_BY_TASK: dict[str, str] = {
    "solve": (
        "You are a PDDL planning assistant. PDDL planning tools are not "
        "available in this evaluation. Analyze the domain and problem and "
        "produce a plan using your own reasoning; conform to the JSON schema "
        "provided by the format constraint."
    ),
    "validate_domain": (
        "You are a PDDL validation assistant. PDDL validation tools are not "
        "available in this evaluation. Analyze the domain syntax using your "
        "own reasoning; end your response with exactly one line: VERDICT: "
        "VALID or VERDICT: INVALID."
    ),
    "validate_problem": (
        "You are a PDDL validation assistant. PDDL validation tools are not "
        "available in this evaluation. Analyze the problem against its "
        "domain using your own reasoning; end your response with exactly "
        "one line: VERDICT: VALID or VERDICT: INVALID."
    ),
    "validate_plan": (
        "You are a PDDL validation assistant. PDDL validation tools are not "
        "available in this evaluation. Analyze whether the plan solves the "
        "problem using your own reasoning; end your response with exactly "
        "one line: VERDICT: VALID or VERDICT: INVALID."
    ),
    "simulate": (
        "You are a PDDL simulation assistant. PDDL simulation tools are not "
        "available in this evaluation. Trace the state transitions using "
        "your own reasoning; conform to the JSON schema provided by the "
        "format constraint (per-step state with boolean predicates and "
        "numeric fluents)."
    ),
}


# Sweep-5 active set: 3 neutral + 3 steered = 6 variants per task. Three
# paraphrases (imperative / declarative / interrogative) × two arms.
# Pairing by index offset +3: v14↔v11, v15↔v12, v16↔v13.
ACTIVE_PROMPT_VARIANTS: tuple[int, ...] = (11, 12, 13, 14, 15, 16)

# Steered set — the emit-point gate in runner.py uses this to skip
# `(no-tools, steered)` cells in main sweep submits. The variant-gated
# template lookup in evaluate_one ALSO uses this: for these variants the
# PROMPT_TEMPLATES_TOOLS_OVERRIDE entry fires regardless of `with_tools`,
# so the control arm `(no-tools, v14..v16)` sees the steered text — this
# is what makes H4 ("steered directive alone does not move the no-tools
# floor") testable. Sweep-4's v5/v6/v7 override semantics (override only
# under with_tools) are preserved for replay because v5/v6/v7 are NOT in
# this set.
STEERED_VARIANTS: frozenset[int] = frozenset({14, 15, 16})

PROMPT_TEMPLATES: dict[str, list[str]] = {
    "solve": [
        "Solve the following PDDL planning problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        "Find a valid plan for this PDDL problem.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        "Generate a plan that solves the following planning problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Given the PDDL domain and problem below, compute a solution plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Please solve this automated planning task and return the plan.\n\n{domain}\n\n{problem}",
        # v5 — sweep-4 no-tools (with-tools branch in PROMPT_TEMPLATES_TOOLS_OVERRIDE).
        "Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. `(pick-up a)`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v6 — sweep-4 no-tools.
        "Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        # v7 — sweep-4 no-tools.
        "Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. `(stack a b)`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v8/v9/v10 (sweep-4.1 aliases) and v11/v12/v13 (sweep-5 neutral)
        # appended via the extend blocks at the end of this module.
    ],
    "validate_domain": [
        "Check if this PDDL domain definition has valid syntax:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the following PDDL domain for syntactic correctness:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL domain syntactically correct? Please check.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Analyze this domain definition and tell me if the PDDL syntax is valid:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Please verify the syntax of the following PDDL domain:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v5 — sweep-4 no-tools. Intentionally lacked the VERDICT trailer
        # so `format=ValidateResponse` (`schemas.py:35–42`) would drive the
        # verdict. Empirical regression: the format constraint is a soft
        # logit bias and the regex fallback (`scoring.extract_verdict`)
        # has nothing to match when the JSON path fails on small / hybrid /
        # thinking-mode cells. Redesign in progress — see
        # `development/sweep_prompt_redesign_handoff.md`.
        "Check if this PDDL domain definition has valid syntax:\n\n{domain}",
        # v6 — sweep-4 no-tools.
        "Validate the following PDDL domain for syntactic correctness:\n\n{domain}",
        # v7 — sweep-4 no-tools.
        "Is this PDDL domain syntactically correct? Please check.\n\n{domain}",
        # v8/v9/v10 (sweep-4.1 aliases) and v11/v12/v13 (sweep-5 neutral)
        # appended via the extend blocks at the end of this module.
    ],
    "validate_problem": [
        "Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the syntax of this PDDL problem against its domain:\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Verify the syntax of the following PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Check the following PDDL problem for syntax errors.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v5 — sweep-4 no-tools (VERDICT trailer dropped).
        "Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v6 — sweep-4 no-tools.
        "Validate the syntax of this PDDL problem against its domain:\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v7 — sweep-4 no-tools.
        "Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v8/v9/v10 (sweep-4.1 aliases) and v11/v12/v13 (sweep-5 neutral)
        # appended via the extend blocks at the end of this module.
    ],
    "validate_plan": [
        "Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Verify the correctness of this plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Does this plan achieve the goal? Validate it.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v5 — sweep-4 no-tools (VERDICT trailer dropped).
        "Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v6 — sweep-4 no-tools.
        "Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v7 — sweep-4 no-tools.
        "Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v8/v9/v10 (sweep-4.1 aliases) and v11/v12/v13 (sweep-5 neutral)
        # appended via the extend blocks at the end of this module.
    ],
    "simulate": [
        "Simulate the execution of this plan and show the state transitions.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Trace the state changes when executing this plan step by step.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Show me the state after each action in this plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Execute this plan and provide the state transition trace.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Walk through this plan action by action and show each intermediate state.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v5 — sweep-4 no-tools (teaches the `_normalize_trajectory` wire format).
        # Example shape matches SimulateResponse → StateStep → StateSnapshot
        # (nested state.boolean / state.numeric, per pddl_eval/schemas.py:45-67).
        "Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with `action` empty. Each later step records the action executed. `state.boolean` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. `(on a b)`; `state.numeric` is the fluents map.\nExample step: {{\"step\": 0, \"action\": \"\", \"state\": {{\"boolean\": [\"(on a b)\", \"(clear c)\"], \"numeric\": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v6 — sweep-4 no-tools.
        "Step through this plan action by action. For each step emit `action` (the action just executed, or empty for step 0) and `state.boolean` listing every currently-true predicate in parenthesised PDDL form, e.g. `(on a b)`.\nExample step: {{\"step\": 1, \"action\": \"(unstack a b)\", \"state\": {{\"boolean\": [\"(holding a)\", \"(clear b)\"], \"numeric\": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v7 — sweep-4 no-tools.
        "Show the state at each step of this plan. Step 0 = initial state with empty `action`. Each `state.boolean` entry lists every predicate that holds in that state, parenthesised and lowercase; `state.numeric` is the fluents map (empty for purely-symbolic domains).\nExample step: {{\"step\": 0, \"action\": \"\", \"state\": {{\"boolean\": [\"(ontable a)\", \"(clear a)\"], \"numeric\": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v8/v9/v10 (sweep-4.1 aliases) and v11/v12/v13 (sweep-5 neutral)
        # appended via the extend blocks at the end of this module.
    ],
}

# Sparse with-tools override. Two semantics by variant range:
#   * v5/v6/v7 (sweep-4): override fires ONLY under with_tools=True (preserves
#     sweep-4 replay byte-stability; the runner gates on `with_tools and
#     prompt_variant in override`).
#   * v14/v15/v16 (sweep-5 steered, in STEERED_VARIANTS): override fires
#     regardless of with_tools. Steered text reaches both the with-tools-
#     steered arm AND the (no-tools, steered) control arm — necessary for
#     H4 ("steered directive alone does not move the no-tools floor").
# For v0–v4, v8–v13 the dict has no entry, so the runner falls through to
# PROMPT_TEMPLATES — sweep-3/sweep-4.1/sweep-5-neutral identities preserved.
#
# Sweep-5 steered directives (v14–v16) are pure single-sentence appends on
# top of the matching neutral prompt (v14↔v11, v15↔v12, v16↔v13). Each names
# the matching marketplace-1.4.0 tool (1:1 with the grader task name for
# validators). The byte-for-byte append property is enforced by
# tests/test_prompts.py.
PROMPT_TEMPLATES_TOOLS_OVERRIDE: dict[str, dict[int, str]] = {
    "solve": {
        5: "Solve this PDDL planning problem by calling a planner tool. Pass the complete domain and problem text below as the planner's `domain` and `problem` arguments — not file names or short identifiers.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        6: "Find a valid plan for this PDDL problem by invoking a planner tool. Provide the full PDDL text as the planner's `domain` and `problem` arguments.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        7: "Generate a plan that solves the following planning problem. Use a planner tool — pass the complete PDDL text as the `domain` and `problem` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v14 = v11 + " Use the planner tool with the domain and problem as arguments."
        14: "Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. `(pick-up a)`. Use the planner tool with the domain and problem as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v15 = v12 + " Use the planner tool with the domain and problem as arguments."
        15: "Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`. Use the planner tool with the domain and problem as arguments.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        # v16 = v13 + " Use the planner tool with the domain and problem as arguments."
        16: "Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. `(stack a b)`. Use the planner tool with the domain and problem as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
    },
    "validate_domain": {
        5: "Check whether this PDDL domain is syntactically valid by calling the validation tool. Pass the full domain text below as the `domain` argument.\n\n{domain}",
        6: "Validate the syntax of this PDDL domain by invoking the validation tool with the full domain text as the `domain` argument.\n\n{domain}",
        7: "Is this PDDL domain syntactically correct? Decide by calling the validation tool with the full domain text below.\n\n{domain}",
        # v14 = v11 + " Use the validate_domain tool with the domain as its argument."
        14: "Check if this PDDL domain definition has valid syntax. Use the validate_domain tool with the domain as its argument.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v15 = v12 + " Use the validate_domain tool with the domain as its argument."
        15: "Validate the following PDDL domain for syntactic correctness. Use the validate_domain tool with the domain as its argument.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v16 = v13 + " Use the validate_domain tool with the domain as its argument."
        16: "Is this PDDL domain syntactically correct? Use the validate_domain tool with the domain as its argument.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    },
    "validate_problem": {
        5: "Check whether this PDDL problem is syntactically valid against its domain. Call the validation tool with the full `domain` and `problem` texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        6: "Validate the syntax of this PDDL problem against its domain by invoking the validation tool. Pass both `domain` and `problem` as full texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        7: "Is this PDDL problem file syntactically correct for the given domain? Decide by calling the validation tool with both `domain` and `problem` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v14 = v11 + " Use the validate_problem tool with the domain and problem as arguments."
        14: "Check if this PDDL problem has valid syntax given the domain. Use the validate_problem tool with the domain and problem as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v15 = v12 + " Use the validate_problem tool with the domain and problem as arguments."
        15: "Validate the syntax of this PDDL problem against its domain. Use the validate_problem tool with the domain and problem as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v16 = v13 + " Use the validate_problem tool with the domain and problem as arguments."
        16: "Is this PDDL problem file syntactically correct for the given domain? Use the validate_problem tool with the domain and problem as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    },
    "validate_plan": {
        5: "Check whether this plan is correct for the given domain and problem. Call the validation tool with ALL THREE of `domain`, `problem`, AND `plan` — pass the full texts from below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        6: "Verify this plan by invoking the validation tool. The tool call MUST include the `plan` argument — otherwise it only checks the domain. Pass `domain`, `problem`, and `plan` as full texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        7: "Is this plan valid for the given planning problem? Decide by calling the validation tool with `domain`, `problem`, and `plan` arguments (all three are required for plan validation).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v14 = v11 + " Use the validate_plan tool with the domain, problem, and plan as arguments."
        14: "Validate whether this plan is correct for the given domain and problem. Use the validate_plan tool with the domain, problem, and plan as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v15 = v12 + " Use the validate_plan tool with the domain, problem, and plan as arguments."
        15: "Check if the following plan solves the PDDL problem. Use the validate_plan tool with the domain, problem, and plan as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v16 = v13 + " Use the validate_plan tool with the domain, problem, and plan as arguments."
        16: "Is this plan valid for the given planning problem? Use the validate_plan tool with the domain, problem, and plan as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    },
    "simulate": {
        5: "Trace the state transitions of this plan by calling the state-transition tool. Pass `domain`, `problem`, and `plan` as full texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        6: "Step through this plan by invoking the state-transition tool with the full `domain`, `problem`, and `plan` texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        7: "Show me the trajectory after applying this plan. Call the state-transition tool with the full PDDL texts (`domain`, `problem`, `plan`) below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v14 = v11 + "\nUse the get_state_transition tool with the domain, problem, and plan as arguments."
        # (Insertion is on its own line between the example JSON and the body
        # block — simulate's neutral has multi-line structure.)
        14: "Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with `action` empty. Each later step records the action executed. `state.boolean` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. `(on a b)`; `state.numeric` is the fluents map.\nExample step: {{\"step\": 0, \"action\": \"\", \"state\": {{\"boolean\": [\"(on a b)\", \"(clear c)\"], \"numeric\": {{}}}}}}\nUse the get_state_transition tool with the domain, problem, and plan as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v15 = v12 + "\nUse the get_state_transition tool with the domain, problem, and plan as arguments."
        15: "Step through this plan action by action. For each step emit `action` (the action just executed, or empty for step 0) and `state.boolean` listing every currently-true predicate in parenthesised PDDL form, e.g. `(on a b)`.\nExample step: {{\"step\": 1, \"action\": \"(unstack a b)\", \"state\": {{\"boolean\": [\"(holding a)\", \"(clear b)\"], \"numeric\": {{}}}}}}\nUse the get_state_transition tool with the domain, problem, and plan as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v16 = v13 + "\nUse the get_state_transition tool with the domain, problem, and plan as arguments."
        16: "Show the state at each step of this plan. Step 0 = initial state with empty `action`. Each `state.boolean` entry lists every predicate that holds in that state, parenthesised and lowercase; `state.numeric` is the fluents map (empty for purely-symbolic domains).\nExample step: {{\"step\": 0, \"action\": \"\", \"state\": {{\"boolean\": [\"(ontable a)\", \"(clear a)\"], \"numeric\": {{}}}}}}\nUse the get_state_transition tool with the domain, problem, and plan as arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    },
}

# ---------------------------------------------------------------------------
# Post-init extensions. Three blocks, run in order at module load:
#   1. Sweep-4.1 aliases: v8/v9/v10 ← v5/v6/v7 (no-tools baseline).
#   2. Sweep-5 neutral strings: v11/v12/v13 (real strings, used by both
#      no-tools and with-tools-neutral arms).
#   3. Sweep-5 steered base-list aliases: v14/v15/v16 ← v11/v12/v13.
#      Defensive only — the runner reads v14/v15/v16 from
#      PROMPT_TEMPLATES_TOOLS_OVERRIDE, not from this list, because they're
#      in STEERED_VARIANTS. If a code path bypasses the override (a future
#      bug), it falls back to the neutral text (closest semantic fit for
#      "no-tools steered without override").
# Byte-equality of aliases relies on the same no-in-place-edit rule that
# protects v0–v7 (see module docstring), not on Python list semantics.
# ---------------------------------------------------------------------------

for _task in PROMPT_TEMPLATES:
    PROMPT_TEMPLATES[_task].extend([
        PROMPT_TEMPLATES[_task][5],   # v8  ← v5
        PROMPT_TEMPLATES[_task][6],   # v9  ← v6
        PROMPT_TEMPLATES[_task][7],   # v10 ← v7
    ])
del _task


# Sweep-5 neutral strings. v11/v12/v13 are appended task-by-task. For solve
# and simulate the text happens to be byte-identical to v5/v6/v7 (the
# sweep-4 wire-format teaching needed no further refinement); for
# validate_*, v11..v13 restore the VERDICT trailer that sweep-4 v5..v7
# dropped (the sweep-4 FR_FORMAT_PARSE_FAIL regression on hybrid models).
PROMPT_TEMPLATES["solve"].extend([
    # v11 — imperative paraphrase
    "Solve this PDDL planning problem and return a plan. Each step must be a single parenthesised PDDL action, e.g. `(pick-up a)`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
    # v12 — declarative paraphrase
    "Find a valid plan for this PDDL problem. Output each action on its own line in parenthesised PDDL form, e.g. `(unstack a b)`.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
    # v13 — alternative imperative paraphrase
    "Generate a plan that solves the following planning problem. Each action in your plan must be a single parenthesised PDDL form, e.g. `(stack a b)`.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
])
PROMPT_TEMPLATES["validate_domain"].extend([
    # v11 — imperative. Terminal punctuation normalised to "." so v14 is a
    # pure-append second sentence.
    "Check if this PDDL domain definition has valid syntax.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    # v12 — declarative.
    "Validate the following PDDL domain for syntactic correctness.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    # v13 — interrogative. The trailing "Please check." filler of v2/v7 is
    # dropped so v16 is a pure-append (no substitution).
    "Is this PDDL domain syntactically correct?\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
])
PROMPT_TEMPLATES["validate_problem"].extend([
    # v11 — imperative. VERDICT trailer restored.
    "Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    # v12 — declarative. Terminal punctuation normalised to "." for pure-append v15.
    "Validate the syntax of this PDDL problem against its domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    # v13 — interrogative.
    "Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
])
PROMPT_TEMPLATES["validate_plan"].extend([
    # v11 — imperative.
    "Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    # v12 — declarative.
    "Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    # v13 — interrogative.
    "Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
])
PROMPT_TEMPLATES["simulate"].extend([
    # v11/v12/v13 — byte-identical to v5/v6/v7 (sweep-4 wire-format teaching
    # was already correct for simulate; sweep-5 carries it forward unchanged).
    "Simulate this plan and return the trajectory. Step 0 is the initial state from the problem with `action` empty. Each later step records the action executed. `state.boolean` lists EVERY predicate that holds in that state, each as a parenthesised lowercase form, e.g. `(on a b)`; `state.numeric` is the fluents map.\nExample step: {{\"step\": 0, \"action\": \"\", \"state\": {{\"boolean\": [\"(on a b)\", \"(clear c)\"], \"numeric\": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    "Step through this plan action by action. For each step emit `action` (the action just executed, or empty for step 0) and `state.boolean` listing every currently-true predicate in parenthesised PDDL form, e.g. `(on a b)`.\nExample step: {{\"step\": 1, \"action\": \"(unstack a b)\", \"state\": {{\"boolean\": [\"(holding a)\", \"(clear b)\"], \"numeric\": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    "Show the state at each step of this plan. Step 0 = initial state with empty `action`. Each `state.boolean` entry lists every predicate that holds in that state, parenthesised and lowercase; `state.numeric` is the fluents map (empty for purely-symbolic domains).\nExample step: {{\"step\": 0, \"action\": \"\", \"state\": {{\"boolean\": [\"(ontable a)\", \"(clear a)\"], \"numeric\": {{}}}}}}\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
])

# Sweep-5 steered base-list aliases: v14/v15/v16 ← v11/v12/v13. The runner
# reads the steered TEXT from PROMPT_TEMPLATES_TOOLS_OVERRIDE (since these
# variants are in STEERED_VARIANTS); the base list slots only fire as a
# defensive fallback for a future code path that bypasses the override map.
for _task in PROMPT_TEMPLATES:
    PROMPT_TEMPLATES[_task].extend([
        PROMPT_TEMPLATES[_task][11],  # v14 ← v11
        PROMPT_TEMPLATES[_task][12],  # v15 ← v12
        PROMPT_TEMPLATES[_task][13],  # v16 ← v13
    ])
del _task
