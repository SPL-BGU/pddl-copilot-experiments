"""Tests for pddl_eval/control_prompts.py (control-prompt cells, 2026-11-23).

The control run (development/control_prompt_fix_plan.md) swaps the no-tools
system text of solve and simulate. These checks pin the texts, their sha256
digests, the fail-closed swap, and the frozen delivered-rerun package hash,
which the change must leave alone. The client side is in test_vllm_client.py.

Runs as a plain script (tests/verify.sh) or under pytest.
"""

import copy
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval import control_prompts as CP  # noqa: E402
from pddl_eval.prompts import (  # noqa: E402
    WITH_TOOLS_SYSTEM,
    WITH_TOOLS_SYSTEM_BY_TASK,
    WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK,
    WITHOUT_TOOLS_SYSTEM,
    WITHOUT_TOOLS_SYSTEM_BY_TASK,
)

FROZEN_PACKAGE_HASH = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"

# Typed here from the plan (section 2), apart from the module.
O_TEXT = {
    "solve": "You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; conform to the JSON schema provided by the format constraint.",
    "simulate": "You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; conform to the JSON schema provided by the format constraint (per-step state with boolean predicates and numeric fluents).",
}
A_TEXT = {
    "solve": "You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning.",
    "simulate": "You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; give the per-step state with boolean predicates and numeric fluents.",
}
B_TEXT = {
    "solve": "You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; end your response with the plan alone in a fenced code block, one parenthesised PDDL action per line.",
    "simulate": 'You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; end your response with a fenced code block that holds a single JSON object of the form {"trajectory": [ ...steps... ]}, where each step has the keys step, action and state (state.boolean and state.numeric).',
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sentences(text: str) -> list[str]:
    # A sentence ends with "." and the next starts with a capital letter. The
    # "." in "...steps... ]}" or "state.boolean" does not end one.
    assert text.endswith(".")
    return re.split(r"(?<=\.) (?=[A-Z])", text)


def test_texts_match_the_plan():
    for task in ("solve", "simulate"):
        assert WITHOUT_TOOLS_SYSTEM_BY_TASK[task] == O_TEXT[task], task
        assert CP.NO_TOOLS_SYSTEM_CONTROL["no-pointer"][task] == A_TEXT[task], task
        assert CP.NO_TOOLS_SYSTEM_CONTROL["format-stated"][task] == B_TEXT[task], task
    assert CP.NO_TOOLS_SYSTEM_MODES == ("no-pointer", "format-stated")
    assert set(CP.NO_TOOLS_SYSTEM_CONTROL) == set(CP.NO_TOOLS_SYSTEM_MODES)
    for mode in CP.NO_TOOLS_SYSTEM_MODES:
        assert set(CP.NO_TOOLS_SYSTEM_CONTROL[mode]) == {"solve", "simulate"}


def test_first_two_sentences_kept_and_three_long():
    for task in ("solve", "simulate"):
        o = _sentences(O_TEXT[task])
        assert len(o) == 3, o
        for text in (A_TEXT[task], B_TEXT[task]):
            s = _sentences(text)
            assert len(s) == 3, s
            assert s[:2] == o[:2], (task, s)
            assert text.startswith(" ".join(o[:2]) + " ")
            assert text != O_TEXT[task]


def test_sha256_constants():
    texts = {"registered": O_TEXT, "no-pointer": A_TEXT, "format-stated": B_TEXT}
    assert set(CP.SYSTEM_TEXT_SHA256) == set(texts)
    for mode, by_task in texts.items():
        assert set(CP.SYSTEM_TEXT_SHA256[mode]) == {"solve", "simulate"}
        for task, text in by_task.items():
            assert CP.SYSTEM_TEXT_SHA256[mode][task] == _sha(text), (mode, task)
    digests = [d for by_task in CP.SYSTEM_TEXT_SHA256.values() for d in by_task.values()]
    assert len(set(digests)) == 6


def test_swap_replaces_only_the_system_content():
    for task in ("solve", "simulate"):
        user = {"role": "user", "content": f"user prompt for {task}"}
        msgs = [{"role": "system", "content": WITHOUT_TOOLS_SYSTEM_BY_TASK[task]}, user]
        before = copy.deepcopy(msgs)
        for mode, want in (("no-pointer", A_TEXT), ("format-stated", B_TEXT)):
            out, got_task = CP.swap_system(msgs, mode)
            assert got_task == task
            assert out == [{"role": "system", "content": want[task]}, user]
            assert out is not msgs and out[0] is not msgs[0]
            assert out[1] is user            # other messages untouched
            assert msgs == before            # input not mutated
            assert msgs[0]["content"] == WITHOUT_TOOLS_SYSTEM_BY_TASK[task]


def test_swap_fails_closed():
    user = {"role": "user", "content": "x"}
    bad_systems = [WITHOUT_TOOLS_SYSTEM_BY_TASK[t] for t in
                   ("validate_domain", "validate_problem", "validate_plan")]
    bad_systems += list(WITH_TOOLS_SYSTEM_BY_TASK.values())
    bad_systems += list(WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK.values())
    bad_systems += [WITHOUT_TOOLS_SYSTEM, WITH_TOOLS_SYSTEM, "", O_TEXT["solve"] + " ",
                    A_TEXT["solve"], B_TEXT["simulate"]]
    cases = [[{"role": "system", "content": s}, user] for s in bad_systems]
    cases += [[], [user], [user, {"role": "system", "content": O_TEXT["solve"]}],
              [{"role": "developer", "content": O_TEXT["solve"]}, user]]
    for mode in CP.NO_TOOLS_SYSTEM_MODES:
        for msgs in cases:
            before = copy.deepcopy(msgs)
            try:
                CP.swap_system(msgs, mode)
                raise AssertionError(f"expected ValueError for {msgs!r}")
            except ValueError:
                pass
            assert msgs == before
    good = [{"role": "system", "content": O_TEXT["solve"]}, user]
    for bad_mode in ("registered", "", None, "No-Pointer", "format_stated"):
        try:
            CP.swap_system(good, bad_mode)
            raise AssertionError(f"expected ValueError for mode {bad_mode!r}")
        except ValueError:
            pass


def test_frozen_package_hash_unchanged():
    from tools.delivered_rerun import run as RUN
    assert RUN.package_sha256() == FROZEN_PACKAGE_HASH


if __name__ == "__main__":
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _tests:
        try:
            _fn()
        except Exception as exc:  # noqa: BLE001 - report every failure
            _failed += 1
            print(f"  FAIL {_name}: {type(exc).__name__}: {exc}")
    print(f"\ntest_control_prompts: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
