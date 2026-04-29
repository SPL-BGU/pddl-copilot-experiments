"""Per-task Pydantic schemas for the no-PDDL-tools branch (PR-4).

The no-PDDL-tools condition (formerly "no-tools") replaces free-text
parsing with Ollama `format=<json_schema>` constraint enforcement: the
sampler is constrained to JSON matching the per-task schema below, and
`scoring.check_success` deserialises that JSON to grade against ground
truth. Free-text extractors remain as a fallback path when the model
emits malformed JSON despite the constraint (tiny models occasionally
degenerate); see `FR_FORMAT_PARSE_FAIL` in `pddl_eval/scoring.py`.

`TASK_SCHEMAS` is keyed on the task name; `runner.evaluate_one` passes
the matching schema to `chat_without_tools(format=...)`. The schemas
serialise to plain `dict` via `model_json_schema()` so they round-trip
through Ollama's HTTP layer cleanly.

Field-name choice for `StateSnapshot`: the oracle (`get_state_transition`
plugin) emits `boolean_fluents` / `numeric_fluents`; we expose
`boolean` / `numeric` to the model because (a) shorter names are easier
for tiny models to round-trip under format constraints, and (b) the
`scoring._normalize_trajectory` helper canonicalises both shapes to the
same internal representation before equality.
"""

from typing import Literal

from pydantic import BaseModel, Field


class SolveResponse(BaseModel):
    plan: list[str] = Field(
        description='Ordered list of plan actions. Each entry is a single action in PDDL form, e.g. "(unstack a b)".',
    )


class ValidateResponse(BaseModel):
    verdict: Literal["VALID", "INVALID"] = Field(
        description='Final validity verdict. Must be exactly "VALID" or "INVALID".',
    )
    reason: str = Field(
        default="",
        description="One- to three-sentence justification. Ungraded; recorded for inspection only.",
    )


class StateSnapshot(BaseModel):
    boolean: list[str] = Field(
        default_factory=list,
        description="Boolean fluents that hold in this state, each as a parenthesised predicate string.",
    )
    numeric: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric fluents in this state, mapping fluent name to value.",
    )


class StateStep(BaseModel):
    step: int = Field(description="0-indexed step position in the trajectory.")
    action: str = Field(
        description='Action that produced this state, in PDDL form, e.g. "(pick-up a)". Use "" for the initial state.',
    )
    state: StateSnapshot


class SimulateResponse(BaseModel):
    trajectory: list[StateStep] = Field(
        description="State sequence including the initial state (step=0, action='') and one entry per executed action.",
    )


# Mapping consumed by runner.evaluate_one: when with_tools=False, the
# model is constrained to emit JSON matching TASK_SCHEMAS[task]. Computed
# at import-time via model_json_schema() so the dict is plain JSON-
# serialisable (Ollama's transport layer rejects pydantic objects).
TASK_SCHEMAS: dict[str, dict] = {
    "solve": SolveResponse.model_json_schema(),
    "validate_domain": ValidateResponse.model_json_schema(),
    "validate_problem": ValidateResponse.model_json_schema(),
    "validate_plan": ValidateResponse.model_json_schema(),
    "simulate": SimulateResponse.model_json_schema(),
}
