"""Control system prompts for the no-tools arm on solve and simulate.

The registered no-tools system prompt of these two tasks
(`prompts.WITHOUT_TOOLS_SYSTEM_BY_TASK`) tells the model to "conform to the
JSON schema provided by the format constraint", but no schema reaches the
model (vLLM 0.20.2 drops `guided_json`). The control run has three cells per
model (development/control_prompt_fix_plan.md, section 2):

  * registered     today's text, nothing swapped
  * no-pointer     the schema reference removed
  * format-stated  the answer format stated in plain words (the final
                   answer in a fenced code block, which both the frozen
                   simulate reader and the layout-tolerant solve reader
                   read; changed 2026-11-23 before any trial, after the
                   freeze review of the analysis)

`pddl_eval/vllm_client.py` applies the swap when $PDDL_NO_TOOLS_SYSTEM names
a mode. This module is not in the frozen delivered-rerun hash, and neither
`prompts.py` nor `runner.py` is edited: the swap replaces the system message
the runner built, and only when it is exactly the registered solve or
simulate text. Anything else raises, so a tool arm, a validation task or a
legacy prompt can never be swapped.
"""

from .prompts import WITHOUT_TOOLS_SYSTEM_BY_TASK

CONTROL_TASKS: tuple[str, ...] = ("solve", "simulate")
NO_TOOLS_SYSTEM_MODES: tuple[str, ...] = ("no-pointer", "format-stated")

# Each text keeps the first two sentences of the registered one byte for byte
# and stays three sentences long (tests/test_control_prompts.py checks this).
NO_TOOLS_SYSTEM_CONTROL: dict[str, dict[str, str]] = {
    "no-pointer": {
        "solve": (
            "You are a PDDL planning assistant. PDDL planning tools are not "
            "available in this evaluation. Analyze the domain and problem and "
            "produce a plan using your own reasoning."
        ),
        "simulate": (
            "You are a PDDL simulation assistant. PDDL simulation tools are not "
            "available in this evaluation. Trace the state transitions using "
            "your own reasoning; give the per-step state with boolean "
            "predicates and numeric fluents."
        ),
    },
    "format-stated": {
        "solve": (
            "You are a PDDL planning assistant. PDDL planning tools are not "
            "available in this evaluation. Analyze the domain and problem and "
            "produce a plan using your own reasoning; end your response with "
            "the plan alone in a fenced code block, one parenthesised PDDL "
            "action per line."
        ),
        "simulate": (
            "You are a PDDL simulation assistant. PDDL simulation tools are not "
            "available in this evaluation. Trace the state transitions using "
            "your own reasoning; end your response with a fenced code block "
            "that holds a single JSON object of the form "
            '{"trajectory": [ ...steps... ]}, where each step has the keys '
            "step, action and state (state.boolean and state.numeric)."
        ),
    },
}

# sha256 (hex, utf-8) of every system text the control can send, so a
# registration can cite them. "registered" is the text from prompts.py.
# Written as literals on purpose; the test recomputes them.
SYSTEM_TEXT_SHA256: dict[str, dict[str, str]] = {
    "registered": {
        "solve": "dd835ea2f66c73f8f26cb80b11afae9030aac316f102fb54a433498b6e23de83",
        "simulate": "dfd6beadb3e815e769fd31bd88f99ed78c0cfb6c9b74001fe442cc0b2bbc5ccd",
    },
    "no-pointer": {
        "solve": "1cf4b9b6a7652fa90dc36cd41b98e3a312bebe6be3a427e3f16a62c4a7b2dfa8",
        "simulate": "c99db1124156372ea0e0a88b41779c4b9aa62167821a99272fa886f8b1774553",
    },
    "format-stated": {
        "solve": "3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588",
        "simulate": "7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9",
    },
}


def swap_system(messages: list, mode: str) -> tuple[list, str]:
    """Return (a copy of `messages` with the system text replaced, task).

    `messages[0]` must be a system message whose content is exactly the
    registered no-tools text of solve or simulate. The returned list holds a
    new first message with the `mode` text for that task; every other message
    is the same object, unchanged. The input list and its messages are not
    modified. Raises ValueError for an unknown mode or any other first message.
    """
    if mode not in NO_TOOLS_SYSTEM_MODES:
        raise ValueError(f"no-tools system mode must be one of "
                         f"{NO_TOOLS_SYSTEM_MODES} (got {mode!r})")
    if not messages or not isinstance(messages[0], dict) \
            or messages[0].get("role") != "system":
        raise ValueError(f"no-tools system swap ({mode}): the first message "
                         f"is not a system message")
    content = messages[0].get("content")
    task = next((t for t in CONTROL_TASKS
                 if content == WITHOUT_TOOLS_SYSTEM_BY_TASK[t]), None)
    if task is None:
        raise ValueError(f"no-tools system swap ({mode}): the system message is "
                         f"not the registered no-tools text of "
                         f"{' or '.join(CONTROL_TASKS)}; refusing to swap")
    first = dict(messages[0])
    first["content"] = NO_TOOLS_SYSTEM_CONTROL[mode][task]
    return [first, *messages[1:]], task
