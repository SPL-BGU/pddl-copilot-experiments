"""System prompts + per-task templates (Section 4 of the paper).

Sweep-4 active set is v5/v6/v7; sweep-3 used v0/v1/v2. The v5/v6/v7
templates address the six prompt-review leaks (see
`.local/prompts_review.md` and `development/sweep4_plan_new_prompts.md`):
they drop the VERDICT trailer in `validate_*`, teach the `plan` argument
for `validate_plan`, name a planner / state-transition tool by category
for `solve` / `simulate`, and (no-tools branch) teach the wire format
expected by `_normalize_trajectory`. v5–v7 are appended (not in-place
edits) so v0–v2 indices remain byte-stable with the sweep-3 corpus.

`ACTIVE_PROMPT_VARIANTS` selects which subset of templates per task
actually runs. The 2026-04-27 reduction (5 → 3, dropping v3 and v4) is
justified by checkpoints/cluster-26042026/prompt_variant_stats.md:
  * (v0, v1, v2) is the closest 3-variant truncation to the 5-variant mean —
    wins 4/5 tasks and 0.0045 mean |gap| vs 0.0051 for (v0, v1, v3).
  * v0/v1/v3 are all imperative-declarative paraphrases; v2 is the only
    question-form variant ("Is this PDDL domain syntactically correct?")
    so keeping v2 preserves linguistic diversity in the robustness story.
  * v4 is the outlier (driven mostly by its label-less solve prompt).
"""


_WITH_TOOLS_BASE = (
    "You are a PDDL planning assistant with access to planning tools. "
    "Your ONLY way to get information or solve problems is by calling the "
    "provided tools ONE AT A TIME — never guess or create plan details yourself."
)

# `_GUIDED_SUFFIX` and the `"guided"` entry below are DISABLED from the
# active sweep (see PROMPT_STYLE_CHOICES in run_experiment.py). Kept in
# code so the exact wording is preserved as documentation — re-enable by
# adding "guided" back to PROMPT_STYLE_CHOICES.
_GUIDED_SUFFIX = (
    "\nWhen calling tools, pass the complete PDDL text from the user message "
    "(starting with '(define ...') as the 'domain' and 'problem' arguments — "
    "not file names or domain names."
)

WITH_TOOLS_SYSTEM: dict[str, str] = {
    "minimal": _WITH_TOOLS_BASE,
    "guided": _WITH_TOOLS_BASE + _GUIDED_SUFFIX,  # DISABLED 2026-04-27
}

WITHOUT_TOOLS_SYSTEM = (
    "You are a PDDL planning assistant. You must analyze PDDL problems, "
    "validate syntax, create plans, and simulate state transitions all on "
    "your own, without any external tools."
)

# All five templates are kept so `prompt_variant` indices stay stable across
# sweeps (a v2 trial today still uses the same paraphrase as a v2 trial in
# the 26042026 sweep). `ACTIVE_PROMPT_VARIANTS` selects which subset runs.
ACTIVE_PROMPT_VARIANTS: tuple[int, ...] = (5, 6, 7)

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
    ],
    "validate_domain": [
        "Check if this PDDL domain definition has valid syntax:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the following PDDL domain for syntactic correctness:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL domain syntactically correct? Please check.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Analyze this domain definition and tell me if the PDDL syntax is valid:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Please verify the syntax of the following PDDL domain:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v5 — sweep-4 no-tools (VERDICT trailer dropped; format=ValidateResponse drives the verdict).
        "Check if this PDDL domain definition has valid syntax:\n\n{domain}",
        # v6 — sweep-4 no-tools.
        "Validate the following PDDL domain for syntactic correctness:\n\n{domain}",
        # v7 — sweep-4 no-tools.
        "Is this PDDL domain syntactically correct? Please check.\n\n{domain}",
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
    ],
}

# Sparse with-tools override for sweep-4. Only set for variants that diverge
# from the base template (v5/v6/v7). For v0–v4 this dict is empty, so the
# with-tools branch falls through to PROMPT_TEMPLATES — sweep-3 corpus
# identity is preserved. For v5–v7, runner.py looks up here under
# with_tools=True and PROMPT_TEMPLATES otherwise.
PROMPT_TEMPLATES_TOOLS_OVERRIDE: dict[str, dict[int, str]] = {
    "solve": {
        5: "Solve this PDDL planning problem by calling a planner tool. Pass the complete domain and problem text below as the planner's `domain` and `problem` arguments — not file names or short identifiers.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        6: "Find a valid plan for this PDDL problem by invoking a planner tool. Provide the full PDDL text as the planner's `domain` and `problem` arguments.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        7: "Generate a plan that solves the following planning problem. Use a planner tool — pass the complete PDDL text as the `domain` and `problem` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
    },
    "validate_domain": {
        5: "Check whether this PDDL domain is syntactically valid by calling the validation tool. Pass the full domain text below as the `domain` argument.\n\n{domain}",
        6: "Validate the syntax of this PDDL domain by invoking the validation tool with the full domain text as the `domain` argument.\n\n{domain}",
        7: "Is this PDDL domain syntactically correct? Decide by calling the validation tool with the full domain text below.\n\n{domain}",
    },
    "validate_problem": {
        5: "Check whether this PDDL problem is syntactically valid against its domain. Call the validation tool with the full `domain` and `problem` texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        6: "Validate the syntax of this PDDL problem against its domain by invoking the validation tool. Pass both `domain` and `problem` as full texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        7: "Is this PDDL problem file syntactically correct for the given domain? Decide by calling the validation tool with both `domain` and `problem` arguments.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
    },
    "validate_plan": {
        5: "Check whether this plan is correct for the given domain and problem. Call the validation tool with ALL THREE of `domain`, `problem`, AND `plan` — pass the full texts from below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        6: "Verify this plan by invoking the validation tool. The tool call MUST include the `plan` argument — otherwise it only checks the domain. Pass `domain`, `problem`, and `plan` as full texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        7: "Is this plan valid for the given planning problem? Decide by calling the validation tool with `domain`, `problem`, and `plan` arguments (all three are required for plan validation).\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    },
    "simulate": {
        5: "Trace the state transitions of this plan by calling the state-transition tool. Pass `domain`, `problem`, and `plan` as full texts below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        6: "Step through this plan by invoking the state-transition tool with the full `domain`, `problem`, and `plan` texts.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        7: "Show me the trajectory after applying this plan. Call the state-transition tool with the full PDDL texts (`domain`, `problem`, `plan`) below.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    },
}
