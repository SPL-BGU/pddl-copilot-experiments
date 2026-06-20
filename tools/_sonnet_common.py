"""Shared request-shaping for the two Anthropic frontier tools.

`sonnet_batch.py` (no-tools Batches runner) and `sonnet_tools_probe.py` (live
with-tools probe) must build *byte-identical* no-tools requests — corpus
identity is load-bearing, and the probe's `--no-tools` mode only means anything
if it mirrors the batch path. The two non-trivial pieces that encode that
contract (the simulate directive + the solve schema) live here, behind one
`format_for` helper, so they cannot drift between the tools.

`format_for` mirrors the live vLLM harness's per-task format handling
(`pddl_eval.runner.evaluate_one`): vLLM applies the `format=TASK_SCHEMAS[task]`
guided_json constraint ONLY in the no-tools branch (`chat_without_tools`); the
with-tools branch (`chat_with_tools`) passes NO format constraint.
"""

# simulate's corpus prompt defers the top-level JSON shape to "the format
# constraint" (the open models' vLLM guided_json). Anthropic structured outputs
# rejects SimulateResponse's free-form numeric dict, so the no-tools path
# appends this directive instead so the model emits the {"trajectory": [...]}
# wrapper `check_success` parses.
SIMULATE_JSON_DIRECTIVE = (
    "\n\nReturn ONLY a single JSON object (no prose, no markdown code fences) "
    'of the form {"trajectory": [ ...steps... ]}, where each step matches the '
    "example above (keys: step, action, state.boolean, state.numeric)."
)

# solve IS schema-compatible with Anthropic structured outputs (a flat
# {"plan": [str, ...]} object), so the no-tools path forces the shape via
# output_config.format — the faithful analog of the open models' vLLM
# guided_json (TASK_SCHEMAS["solve"]), which likewise left no room for prose.
SOLVE_FORMAT_SCHEMA = {
    "type": "object",
    "properties": {"plan": {"type": "array", "items": {"type": "string"}}},
    "required": ["plan"],
    "additionalProperties": False,
}


def format_for(task: str, user_text: str, *, with_tools: bool) -> tuple[str, dict | None]:
    """Mirror the vLLM harness's per-task format handling for the Anthropic path.

    Returns `(user_text, output_config_or_None)` where `output_config` is the
    Anthropic structured-output param (or None when no constraint applies).

      * with_tools=True  → `(user_text, None)`. The live vLLM with-tools branch
        passes no format constraint; the model answers through tool calls (e.g.
        simulate WT is graded from the `get_state_transition` tool result, not
        its text — see scoring.check_success). Appending a "return ONLY JSON"
        directive here would be unfaithful to that path AND could suppress the
        tool call the grader needs.
      * with_tools=False → the guided_json analog: solve via `output_config`,
        simulate via SIMULATE_JSON_DIRECTIVE, validate_* via the corpus prompt's
        VERDICT footer + check_success's free-text fallback (no structured
        output needed).
    """
    if with_tools:
        return user_text, None
    if task == "solve":
        return user_text, {"format": {"type": "json_schema", "schema": SOLVE_FORMAT_SCHEMA}}
    if task == "simulate":
        return user_text + SIMULATE_JSON_DIRECTIVE, None
    return user_text, None
