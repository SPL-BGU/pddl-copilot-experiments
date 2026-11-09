"""D1e plain and steered prompts for the open-model PlanBench tool loop.

The two arms (backends ``vllm-tools-plain`` and ``vllm-tools-steered`` in
planbench/engine.py) must reuse the frozen PlanBench-WT format clause byte for
byte. The frozen source is pinned twice and both pins are checked here:

  * the sha256 of ``_PB_SHARED_T1_FORMAT`` in tests/test_planbench_prompts.py
    (FROZEN, "v2 FROZEN by Omer 2026-08-01"), imported, not copied;
  * the text the prereg quotes as "The exact text the signature binds to"
    (development/reference/planbench_wt_prereg.md, restart record 1).

The steered prompt is also the frontier WT arm-A system prompt byte for byte
(FROZEN_SCAFFOLDS[True]), and the plain prompt's role sentence is the
5-task arm's `neutral` solve system prompt.

The two arm prompts themselves are pinned below (D1E_ARMS). They are not
frozen by any prereg yet: D1f freezes them. Change a pin only together with
the D1f text that quotes the new prompt.

Standalone: `python3 tests/test_planbench_d1e_prompts.py`; also under pytest.
"""

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pddl_eval.prompts import WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK  # noqa: E402
from tests.test_planbench_prompts import FROZEN, FROZEN_SCAFFOLDS  # noqa: E402

PREREG = REPO / "development" / "reference" / "planbench_wt_prereg.md"

# Draft pins (D1e, 2026-11-09). D1f freezes them.
D1E_ARMS = {
    "vllm-tools-plain": (
        538,
        "d6d64e57a33186bb1606e1f8f90520e7f809f0653cb18fa90bfd322384e2fcb3",
    ),
    "vllm-tools-steered": (
        887,
        "61e8b86d60b11f8426509809a522e645b7e3a499685fbb54248ed1ad26a6bec8",
    ),
}


def _load_engine():
    path = REPO / "planbench" / "engine.py"
    spec = importlib.util.spec_from_file_location("planbench_engine_d1e", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENG = _load_engine()


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _prereg_clause() -> str:
    text = PREREG.read_text()
    i = text.index("The exact text the signature binds to:")
    block = text[i:].split("\n\n")[1]
    lines = block.splitlines()
    assert lines and all(l.startswith("> ") for l in lines), "prereg quote moved"
    return " ".join(l[2:] for l in lines)


class _Env:
    def __init__(self, **kv):
        self.kv = kv
        self.saved = {}

    def __enter__(self):
        for k, v in self.kv.items():
            self.saved[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_clause_is_the_frozen_bytes():
    length, digest = FROZEN["_PB_SHARED_T1_FORMAT"]
    clause = ENG._PB_SHARED_T1_FORMAT
    assert len(clause) == length and _sha(clause) == digest, "frozen clause edited"
    # The prereg quote is line-wrapped markdown; the constant is that text
    # with one leading space (it is appended after a policy sentence).
    assert clause == " " + _prereg_clause()


def test_both_arms_end_with_the_frozen_clause_byte_for_byte():
    clause = ENG._PB_SHARED_T1_FORMAT
    for backend, prompt in ENG._VLLM_TOOLS_ARMS.items():
        assert prompt.encode().endswith(clause.encode()), backend
        assert prompt.count("[PLAN]") == clause.count("[PLAN]"), backend


def test_steered_is_the_frontier_wt_tools_scaffold():
    steered = ENG._VLLM_TOOLS_ARMS["vllm-tools-steered"]
    assert _sha(steered) == FROZEN_SCAFFOLDS[True]
    with _Env(PDDL_COPILOT_TASK="t1"):
        assert steered == ENG._pb_scaffold(True)
    length, digest = FROZEN["_PB_POLICY_TOOLS"]
    policy = steered[: -len(ENG._PB_SHARED_T1_FORMAT)]
    assert len(policy) == length and _sha(policy) == digest


def test_plain_is_the_neutral_role_sentence_plus_clause():
    plain = ENG._VLLM_TOOLS_ARMS["vllm-tools-plain"]
    role = plain[: -len(ENG._PB_SHARED_T1_FORMAT)]
    assert role == ENG._PB_ROLE == WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK["solve"]


def test_no_tool_name_in_either_arm():
    for prompt in ENG._VLLM_TOOLS_ARMS.values():
        for name in ("classic_planner", "numeric_planner", "validate_plan",
                     "validate_domain", "validate_problem", "get_state_transition"):
            assert name not in prompt


def test_arm_pins():
    assert set(ENG._VLLM_TOOLS_ARMS) == set(D1E_ARMS)
    for backend, (length, digest) in D1E_ARMS.items():
        prompt = ENG._VLLM_TOOLS_ARMS[backend]
        assert (len(prompt), _sha(prompt)) == (length, digest), backend


def test_engine_names_parse_and_keep_their_own_backend():
    for backend in D1E_ARMS:
        engine = f"pddl_copilot__{backend}__Qwen3.5:4B"
        assert ENG._parse_engine_name(engine) == (backend, "Qwen3.5:4B")


def test_t1_only_guard():
    for backend in D1E_ARMS:
        for task in ("t3", "t7", "t2"):
            with _Env(PDDL_COPILOT_TASK=task):
                try:
                    ENG._vllm_tools_arm_system(backend)
                except SystemExit:
                    pass
                else:
                    raise AssertionError(f"{backend} accepted {task}")
        for task in ("t1", None):
            with _Env(PDDL_COPILOT_TASK=task):
                assert ENG._vllm_tools_arm_system(backend) == ENG._VLLM_TOOLS_ARMS[backend]


def test_arm_chat_sends_the_arm_prompt_and_delivers_model_text():
    """Drive _vllm_tools_arm_chat with a stub loop: what goes on the wire,
    what comes back, and the side-log record."""
    import asyncio

    seen = {}

    async def fake_chat_with_tools(**kw):
        seen.update(kw)
        log = [{"name": "classic_planner", "arguments": {}, "result": "ok"}]
        return "[PLAN]\nunstack the red block from on top of the blue block\n[PLAN END]", \
            log, "stop", False, {"turns": 2}, ""

    fake_chat = types.ModuleType("pddl_eval.chat")
    fake_chat.chat_with_tools = fake_chat_with_tools
    loop = asyncio.new_event_loop()
    saved_runtime = ENG._get_tools_runtime
    saved_mod = sys.modules.get("pddl_eval.chat")
    ENG._get_tools_runtime = lambda: (loop, object(), object())
    sys.modules["pddl_eval.chat"] = fake_chat
    try:
        with tempfile.TemporaryDirectory() as d:
            log_path = Path(d) / "toolcalls.jsonl"
            for backend in D1E_ARMS:
                with _Env(PDDL_COPILOT_TASK="t1", PDDL_COPILOT_THINK="off",
                          PDDL_COPILOT_TOOLLOG=str(log_path),
                          PDDL_COPILOT_RENDER_FROM_TOOLS="1",
                          PDDL_COPILOT_NUM_PREDICT="8192"):
                    out = ENG.pddl_copilot_send_query(
                        "QUERY", f"pddl_copilot__{backend}__Qwen3.5:4B", 500)
                assert out.startswith("[PLAN]"), backend
                msgs = seen["messages"]
                assert msgs[0] == {"role": "system", "content": ENG._VLLM_TOOLS_ARMS[backend]}
                assert msgs[1] == {"role": "user", "content": "QUERY"}
                assert seen["think"] is False and seen["num_predict"] == 8192
                assert seen["model"] == "Qwen3.5:4B"
            recs = [json.loads(l) for l in log_path.read_text().splitlines()]
        assert [r["backend"] for r in recs] == list(D1E_ARMS)
        for rec, backend in zip(recs, D1E_ARMS):
            assert rec["system_sha256"] == D1E_ARMS[backend][1]
            assert rec["rendered"] is False and rec["n_tool_calls"] == 1
            assert rec["num_predict"] == 8192 and rec["usage"] == {"turns": 2}
    finally:
        ENG._get_tools_runtime = saved_runtime
        if saved_mod is None:
            sys.modules.pop("pddl_eval.chat", None)
        else:
            sys.modules["pddl_eval.chat"] = saved_mod
        loop.close()


def test_legacy_vllm_tools_prompt_unchanged():
    """The pre-D1e vllm-tools t1 prompt (smokes of 2026-06) keeps its bytes:
    the D1e arms are new backends, not an edit of this one. Hash read from
    origin/main before the D1e change (577 chars)."""
    with _Env(PDDL_COPILOT_TASK="t1"):
        legacy = ENG._tools_system_prompt()
    assert len(legacy) == 577
    assert _sha(legacy) == "7691b7978359c387585edb072a259459e28c8d5099526ee934767e3b967e9e2b"
    assert ENG._PB_SHARED_T1_FORMAT not in legacy


if __name__ == "__main__":
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _tests:
        try:
            _fn()
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL {_name}: {type(exc).__name__}: {exc}")
    print(f"\ntest_planbench_d1e_prompts: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
