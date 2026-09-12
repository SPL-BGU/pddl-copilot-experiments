"""Unit tests for pddl_eval.chat.chat_without_tools_decoupled (iter-2 T6).

Run standalone: `python3 tests/test_chat_decoupled.py`
Or via the shell wrapper: `bash tests/verify.sh`

Pure-Python: a FakeVLLMClient records every chat() kwarg and returns scripted
responses, so we can assert the 2-call decoupled-budget contract without a live
vLLM server:
  * Call 1 carries stop=["</think>"], the THINK budget, and
    include_stop_str_in_output (so the close survives any reasoning-parser).
  * Call 2 carries continue_final_message / add_generation_prompt, the ANSWER
    budget, and the reconstructed <think>…</think> block as the final turn.
  * Reasoning reconstruction works parser-ON (thinking field) and parser-OFF
    (raw content with a trailing </think> to strip).
  * think_truncated reflects Call 1's cap-hit; answer done_reason reflects
    Call 2; tokens split think/answer decode and never double-count the prompt.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import TestResults
from pddl_eval.chat import chat_without_tools_decoupled
from pddl_eval.scoring import (
    FR_THINK_OVERFLOW,
    FR_TRUNCATED_NO_ANSWER,
    FR_FORMAT_PARSE_FAIL,
    _classify_step_failure,
    relabel_truncated_taxonomy,
)


def _resp(content="", thinking="", done_reason="stop", prompt=10, completion=5):
    """Build a VLLMClient-shaped response dict (see vllm_client._to_ollama_response)."""
    return {
        "message": {"role": "assistant", "content": content, "thinking": thinking},
        "done_reason": done_reason,
        "prompt_eval_count": prompt,
        "eval_count": completion,
        "total_duration": 1000,
        "eval_duration": 1000,
    }


class FakeVLLMClient:
    """Records each chat() call's kwargs and pops scripted responses in order."""

    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls: list[dict] = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self._scripted.pop(0)


def _run(client, **over):
    base = dict(
        model="qwen3.6:35b",
        messages=[{"role": "system", "content": "S"}, {"role": "user", "content": "U"}],
        num_predict_think=8192,
        num_predict_answer=4096,
        num_ctx=16384,
    )
    base.update(over)
    return asyncio.run(chat_without_tools_decoupled(client, **base))


def test_parser_on_happy_path(r: TestResults) -> None:
    """Parser ON: reasoning arrives in the `thinking` field; answer in content."""
    client = FakeVLLMClient([
        _resp(thinking="step one then step two", done_reason="stop", prompt=12, completion=40),
        _resp(content='{"answer": true}', done_reason="stop", prompt=60, completion=8),
    ])
    answer, done_reason, tokens, thinking_text, think_truncated = _run(client)

    r.check_eq("two chat() calls", len(client.calls), 2)
    c1, c2 = client.calls

    # Call 1 = reasoning phase.
    r.check_eq("call1 stop is </think>", c1.get("stop"), ["</think>"])
    r.check_eq("call1 think budget", c1["options"]["num_predict"], 8192)
    r.check_eq("call1 think=on", c1.get("think"), True)
    r.check_eq("call1 include_stop_str", c1.get("vllm_extra"), {"include_stop_str_in_output": True})
    r.check("call1 no format on reasoning", "format" not in c1)

    # Call 2 = answer phase (continuation).
    r.check_eq("call2 no stop", c2.get("stop"), None)
    r.check_eq("call2 answer budget", c2["options"]["num_predict"], 4096)
    r.check_eq("call2 continuation flags", c2.get("vllm_extra"),
               {"continue_final_message": True, "add_generation_prompt": False})
    last_msg = c2["messages"][-1]
    r.check_eq("call2 final msg is assistant", last_msg["role"], "assistant")
    r.check("call2 injects closed think block",
            last_msg["content"] == "<think>\nstep one then step two\n</think>\n\n")

    # Returns.
    r.check_eq("answer text", answer, '{"answer": true}')
    r.check_eq("answer done_reason", done_reason, "stop")
    r.check_eq("thinking_text == reasoning", thinking_text, "step one then step two")
    r.check_eq("not think_truncated", think_truncated, False)


def test_parser_off_reconstruction(r: TestResults) -> None:
    """Parser OFF: reasoning arrives in raw `content` WITH a trailing </think>."""
    client = FakeVLLMClient([
        _resp(content="raw reasoning body</think>", thinking="", done_reason="stop"),
        _resp(content="ANSWER", done_reason="stop"),
    ])
    answer, _dr, _tok, thinking_text, _tt = _run(client)
    r.check_eq("close token stripped", thinking_text, "raw reasoning body")
    inj = client.calls[1]["messages"][-1]["content"]
    r.check_eq("reconstructed think block", inj, "<think>\nraw reasoning body\n</think>\n\n")
    r.check_eq("answer", answer, "ANSWER")


def test_think_truncation_still_answers(r: TestResults) -> None:
    """Call 1 hits its budget (length): we force-close and STILL run Call 2."""
    client = FakeVLLMClient([
        _resp(thinking="endless spiral", done_reason="length", completion=8192),
        _resp(content="answer despite spiral", done_reason="stop", completion=12),
    ])
    answer, done_reason, _tok, _think, think_truncated = _run(client)
    r.check_eq("think_truncated set", think_truncated, True)
    r.check_eq("answer still produced", answer, "answer despite spiral")
    r.check_eq("answer done_reason is Call-2's", done_reason, "stop")


def test_answer_truncation_surfaces(r: TestResults) -> None:
    """Call 2 length is the genuine answer-truncation signal callers grade on."""
    client = FakeVLLMClient([
        _resp(thinking="ok", done_reason="stop"),
        _resp(content="partial ans", done_reason="length"),
    ])
    _answer, done_reason, _tok, _think, think_truncated = _run(client)
    r.check_eq("answer done_reason length", done_reason, "length")
    r.check_eq("think not truncated", think_truncated, False)


def test_token_split_no_double_count(r: TestResults) -> None:
    """completion = think+answer decode; prompt = Call-1 input; call2_prompt separate."""
    client = FakeVLLMClient([
        _resp(thinking="t", done_reason="stop", prompt=12, completion=40),
        _resp(content="a", done_reason="stop", prompt=60, completion=8),
    ])
    _a, _dr, tokens, _th, _tt = _run(client)
    r.check_eq("prompt = call1 input only", tokens["prompt"], 12)
    r.check_eq("think_completion", tokens["think_completion"], 40)
    r.check_eq("answer_completion", tokens["answer_completion"], 8)
    r.check_eq("completion = sum of decode", tokens["completion"], 48)
    r.check_eq("call2_prompt recorded", tokens["call2_prompt"], 60)
    r.check_eq("turns", tokens["turns"], 2)


def test_format_only_on_answer(r: TestResults) -> None:
    """A schema/guided_json constrains the answer (Call 2), never the reasoning."""
    client = FakeVLLMClient([
        _resp(thinking="t", done_reason="stop"),
        _resp(content="a", done_reason="stop"),
    ])
    _run(client, format={"type": "object"})
    r.check("call1 unconstrained", "format" not in client.calls[0])
    r.check_eq("call2 carries format", client.calls[1].get("format"), {"type": "object"})


def test_messages_not_mutated_until_end(r: TestResults) -> None:
    """The original messages list ends with one appended assistant turn."""
    client = FakeVLLMClient([
        _resp(thinking="t", done_reason="stop"),
        _resp(content="final", done_reason="stop"),
    ])
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    asyncio.run(chat_without_tools_decoupled(
        client, model="m", messages=msgs,
        num_predict_think=8192, num_predict_answer=4096, num_ctx=16384,
    ))
    r.check_eq("one assistant turn appended", len(msgs), 3)
    r.check_eq("appended turn role", msgs[-1]["role"], "assistant")
    r.check("appended turn has think+answer",
            msgs[-1]["content"] == "<think>\nt\n</think>\n\nfinal")


def test_call1_abort_short_circuits(r: TestResults) -> None:
    """A Call-1 abort surfaces done_reason='abort' and never runs Call 2 (so
    evaluate_one tags infra_failure → resume re-attempts the key)."""
    client = FakeVLLMClient([
        _resp(thinking="partial", done_reason="abort", completion=3),
        _resp(content="should-not-be-used", done_reason="stop"),  # must NOT be consumed
    ])
    answer, done_reason, tokens, thinking, think_truncated = _run(client)
    r.check_eq("only ONE chat() call made", len(client.calls), 1)
    r.check_eq("done_reason surfaced as abort", done_reason, "abort")
    r.check_eq("empty answer on abort", answer, "")
    r.check_eq("turns=1 on abort", tokens["turns"], 1)
    r.check_eq("think_truncated False on abort", think_truncated, False)


def test_decoupled_answer_trunc_not_think_overflow(r: TestResults) -> None:
    """FR mislabel fix (write-time): an empty-answer length-truncation on the
    decoupled path is FR_TRUNCATED_NO_ANSWER, NOT FR_THINK_OVERFLOW — even
    though thinking_text (the completed reasoning) is non-empty."""
    # decoupled=True must suppress the think-overflow branch.
    fr, trunc = _classify_step_failure(
        False, "length", False, FR_FORMAT_PARSE_FAIL,
        thinking_text="completed reasoning", response_text="",
        decoupled=True,
    )
    r.check_eq("decoupled -> not think_overflow", fr, FR_TRUNCATED_NO_ANSWER)
    r.check_eq("still truncated", trunc, True)
    # Control: the SHARED-budget path (decoupled=False) keeps the old behaviour.
    fr2, _ = _classify_step_failure(
        False, "length", False, FR_FORMAT_PARSE_FAIL,
        thinking_text="spiral", response_text="", decoupled=False,
    )
    r.check_eq("shared path still think_overflow", fr2, FR_THINK_OVERFLOW)


def test_decoupled_readtime_relabel_suppressed(r: TestResults) -> None:
    """FR mislabel fix (read-time): relabel_truncated_taxonomy must NOT convert
    a decoupled empty-answer truncation to think_overflow."""
    keep = relabel_truncated_taxonomy(
        FR_TRUNCATED_NO_ANSWER, truncated=True, response="", think_mode="on",
        decoupled=True,
    )
    r.check_eq("decoupled read-time keeps truncated_no_answer", keep, FR_TRUNCATED_NO_ANSWER)
    # Control: non-decoupled think=on still relabels.
    flip = relabel_truncated_taxonomy(
        FR_TRUNCATED_NO_ANSWER, truncated=True, response="", think_mode="on",
        decoupled=False,
    )
    r.check_eq("non-decoupled read-time relabels", flip, FR_THINK_OVERFLOW)


if __name__ == "__main__":
    r = TestResults("test_chat_decoupled")
    test_parser_on_happy_path(r)
    test_parser_off_reconstruction(r)
    test_think_truncation_still_answers(r)
    test_answer_truncation_surfaces(r)
    test_token_split_no_double_count(r)
    test_format_only_on_answer(r)
    test_messages_not_mutated_until_end(r)
    test_call1_abort_short_circuits(r)
    test_decoupled_answer_trunc_not_think_overflow(r)
    test_decoupled_readtime_relabel_suppressed(r)
    r.report_and_exit()
