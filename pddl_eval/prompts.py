"""System prompts + per-task templates (Section 4 of the paper).

`ACTIVE_PROMPT_VARIANTS` selects which subset of the 5 stable templates per
task actually runs. The 2026-04-27 reduction (5 → 3, dropping v3 and v4) is
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
ACTIVE_PROMPT_VARIANTS: tuple[int, ...] = (0, 1, 2)

PROMPT_TEMPLATES: dict[str, list[str]] = {
    "solve": [
        "Solve the following PDDL planning problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        "Find a valid plan for this PDDL problem.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        "Generate a plan that solves the following planning problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Given the PDDL domain and problem below, compute a solution plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Please solve this automated planning task and return the plan.\n\n{domain}\n\n{problem}",
    ],
    "validate_domain": [
        "Check if this PDDL domain definition has valid syntax:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the following PDDL domain for syntactic correctness:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL domain syntactically correct? Please check.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Analyze this domain definition and tell me if the PDDL syntax is valid:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Please verify the syntax of the following PDDL domain:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    ],
    "validate_problem": [
        "Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the syntax of this PDDL problem against its domain:\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Verify the syntax of the following PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Check the following PDDL problem for syntax errors.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    ],
    "validate_plan": [
        "Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Verify the correctness of this plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Does this plan achieve the goal? Validate it.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    ],
    "simulate": [
        "Simulate the execution of this plan and show the state transitions.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Trace the state changes when executing this plan step by step.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Show me the state after each action in this plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v3 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Execute this plan and provide the state transition trace.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        # v4 DISABLED — see ACTIVE_PROMPT_VARIANTS (kept in list to preserve indices).
        "Walk through this plan action by action and show each intermediate state.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    ],
}
