"""Regression tests for pddl_eval.vllm_client.

Two groups:
  * `_CTX_OVERFLOW_RE` — silently missing the new vLLM error-body shape
    caused 24 600 trials to be miscategorized as `FR_EXCEPTION` (PR-#66
    contamfix, 2026-05-20). The tests pin both observed body shapes so the
    next vLLM-message-text bump trips a unit-test failure instead of silently
    corrupting a sweep.
  * the context-overflow retry — the 400 body's prompt count is only a lower
    bound, so the old clip never converged and 1,987 sweep5v2 tool-arm trials
    had their final turn recorded as an empty "length" answer (2026-10-02,
    development/reanalysis_transcripts.md §3.3).

Runs under pytest and as a plain script (tests/verify.sh).
"""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from openai import BadRequestError
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval.chat import _record_ctx_clip  # noqa: E402
from pddl_eval.vllm_client import (  # noqa: E402
    VLLMClient,
    _clip_candidates,
    _parse_ctx_overflow,
)


def _make_err(body: str) -> BadRequestError:
    """Build a BadRequestError carrying the given message body."""
    return BadRequestError(
        message=body,
        response=httpx.Response(400, request=httpx.Request("POST", "http://test")),
        body={"error": {"message": body}},
    )


def test_parse_ctx_overflow_old_format():
    """Old vLLM body: 'prompt contains at least N input tokens'."""
    body = (
        "This model's maximum context length is 16384 tokens. However, "
        "you requested 8192 output tokens and your prompt contains at "
        "least 8193 input tokens, for a total of at least 16385 tokens."
    )
    assert _parse_ctx_overflow(_make_err(body)) == (16384, 8193)


def test_parse_ctx_overflow_new_format():
    """New vLLM body (mid-2026): 'upper bound for N input tokens'."""
    body = (
        "Error code: 400 - {'error': {'message': \"This model's maximum "
        "context length is 16384 tokens. However, you requested 8159 "
        "output tokens and your prompt contains 407867 characters "
        "(more than 317440 characters, which is the upper bound for "
        "10240 input tokens). Please reduce the length of the input...\""
    )
    assert _parse_ctx_overflow(_make_err(body)) == (16384, 10240)


def test_parse_ctx_overflow_exact_format():
    """Mistral-tokenizer body (vLLM 0.20.2, 2026-10-27): the exact prompt count."""
    body = (
        "Error code: 400 - {'error': {'message': \"This model's maximum "
        "context length is 16384 tokens. However, you requested 8192 output "
        "tokens and your prompt contains 8310 input tokens, for a total of "
        "16502 tokens. Please reduce the length of the input...\""
    )
    assert _parse_ctx_overflow(_make_err(body)) == (16384, 8310)


def test_parse_ctx_overflow_returns_none_for_unrelated_400():
    """A non-overflow 400 must return None so the caller re-raises."""
    body = "Error code: 400 - Bad Request: tool argument schema mismatch."
    assert _parse_ctx_overflow(_make_err(body)) is None


# ---------------------------------------------------------------------------
# Context-overflow retry (2026-10-02). The fake below reproduces the server
# behaviour that defeated the old retry: the prompt count in the 400 body is
# a LOWER BOUND derived from the max_tokens that was sent
# (max_model_len − max_tokens + 1), never the real prompt size.
# ---------------------------------------------------------------------------

_MAX_CTX = 16384


class _FakeCompletions:
    """Stand-in for `AsyncOpenAI().chat.completions` with vLLM's overflow rule.

    `true_prompt` is the real prompt size the server would count. A request
    is rejected iff true_prompt + max_tokens > max_model_len, and the
    rejection reports only the lower bound. `report_usage=False` simulates a
    server that returns no usage block (forces the halving fallback).
    """

    def __init__(self, true_prompt: int, report_usage: bool = True,
                 unrelated_400_on_call: int | None = None,
                 check_overhead: int = 0):
        self.true_prompt = true_prompt
        self.report_usage = report_usage
        self.unrelated_400_on_call = unrelated_400_on_call
        # Tokens the server's pre-flight check counts ON TOP of what it later
        # reports in usage.prompt_tokens (0 = the two agree).
        self.check_overhead = check_overhead
        self.sent_max_tokens: list[int] = []

    async def create(self, **kwargs):
        max_tokens = kwargs["max_tokens"]
        self.sent_max_tokens.append(max_tokens)
        if self.unrelated_400_on_call == len(self.sent_max_tokens):
            raise _make_err("Error code: 400 - tool argument schema mismatch.")
        if self.true_prompt + self.check_overhead + max_tokens > _MAX_CTX:
            lower_bound = _MAX_CTX - max_tokens + 1
            raise _make_err(
                f"This model's maximum context length is {_MAX_CTX} tokens. "
                f"However, you requested {max_tokens} output tokens and your "
                f"prompt contains at least {lower_bound} input tokens, for a "
                f"total of at least {_MAX_CTX + 1} tokens."
            )
        usage = (
            SimpleNamespace(prompt_tokens=self.true_prompt, completion_tokens=7)
            if self.report_usage else None
        )
        msg = SimpleNamespace(
            content="VERDICT: VALID", tool_calls=None, reasoning_content=None,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg, finish_reason="stop")],
            usage=usage,
        )


def _client_with(fake: _FakeCompletions) -> VLLMClient:
    client = VLLMClient(base_url="http://test")
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return client


def _chat(fake: _FakeCompletions, num_predict: int) -> dict:
    return asyncio.run(_client_with(fake).chat(
        model="m", messages=[{"role": "user", "content": "x"}],
        options={"temperature": 0.0, "num_predict": num_predict},
    ))


def test_fitting_request_is_sent_once_unchanged():
    """A trial that fits: one request, full allowance, no clip annotations."""
    fake = _FakeCompletions(true_prompt=3000)
    resp = _chat(fake, 6144)
    assert fake.sent_max_tokens == [6144]
    assert resp["message"]["content"] == "VERDICT: VALID"
    assert resp["done_reason"] == "stop"
    assert "num_predict_clipped_to" not in resp
    assert "num_predict_requested" not in resp
    assert "ctx_overflow_no_room" not in resp


def test_lower_bound_error_body_does_not_reveal_prompt_size():
    """The emulated 400 reports 10241 for ANY prompt that does not fit next
    to 6144 — the old retry (new_max = ctx − reported − 128) therefore moved
    max_tokens by 129 per attempt: 6144 → 6015 → 5886 → give up at 10499."""
    for true_prompt in (10300, 10900, 14000):
        fake = _FakeCompletions(true_prompt=true_prompt)
        try:
            asyncio.run(fake.create(max_tokens=6144))
        except BadRequestError as e:
            assert _parse_ctx_overflow(e) == (_MAX_CTX, 10241)
        else:
            raise AssertionError("expected overflow")
    # Old algorithm's give-up value, as stored in 1,987 sweep5v2 rows.
    reported, max_tokens = 10241, 6144
    for _ in range(2):
        max_tokens = _MAX_CTX - reported - 128
        reported = _MAX_CTX - max_tokens + 1
    assert reported == 10499


def test_overflow_clips_to_real_room_and_answers():
    """Final-turn overflow with thousands of tokens of room (the sweep5v2
    symptom): the retry must reach the model and record the clipped value."""
    fake = _FakeCompletions(true_prompt=10900)   # room = 5484, old path gave up
    resp = _chat(fake, 6144)
    # full allowance first, then the 1-token measurement, then the clip.
    assert fake.sent_max_tokens == [6144, 1, _MAX_CTX - 10900]
    assert resp["message"]["content"] == "VERDICT: VALID"
    assert resp["done_reason"] == "stop"
    assert resp["num_predict_requested"] == 6144
    assert resp["num_predict_clipped_to"] == 5484
    assert resp["prompt_eval_count"] == 10900
    assert "ctx_overflow_no_room" not in resp


def test_overflow_with_tiny_room_still_reaches_the_model():
    """Even a few tokens of room produce a real turn, not a synthetic one."""
    fake = _FakeCompletions(true_prompt=_MAX_CTX - 5)
    resp = _chat(fake, 8192)
    assert fake.sent_max_tokens == [8192, 1, 5]
    assert resp["num_predict_clipped_to"] == 5
    assert "ctx_overflow_no_room" not in resp


def test_prompt_alone_fills_window_synthesizes_empty_length():
    """Genuine overflow: not even one output token fits."""
    fake = _FakeCompletions(true_prompt=_MAX_CTX)
    resp = _chat(fake, 6144)
    assert fake.sent_max_tokens == [6144, 1]
    assert resp["message"]["content"] == ""
    assert resp["done_reason"] == "length"
    assert resp["eval_count"] == 0
    assert resp["ctx_overflow_no_room"] is True
    assert "num_predict_clipped_to" not in resp


def test_overflow_without_usage_falls_back_to_halving():
    """No usage on the probe → start from the lower bound, halve until a
    request fits. Bounded, and still ends in a real answer."""
    fake = _FakeCompletions(true_prompt=10900, report_usage=False)
    resp = _chat(fake, 6144)
    # 6144 (reject) → probe 1 → 16384−10241−128 = 6015 (reject) → 3007 (fits)
    assert fake.sent_max_tokens == [6144, 1, 6015, 3007]
    assert resp["num_predict_clipped_to"] == 3007
    assert resp["message"]["content"] == "VERDICT: VALID"


def test_clip_candidates_order():
    """Measured: exact room, then −1/−8/−64, only then halving. Unmeasured:
    halving straight away. Nothing below 1; no room → nothing to try."""
    assert _clip_candidates(5484, fine=True)[:6] == [5484, 5483, 5476, 5420, 2710, 1355]
    assert _clip_candidates(5484, fine=True)[-1] == 1
    assert _clip_candidates(6015, fine=False)[:3] == [6015, 3007, 1503]
    assert _clip_candidates(5, fine=True) == [5, 4, 2, 1]
    assert _clip_candidates(1, fine=True) == [1]
    assert _clip_candidates(0, fine=True) == []
    assert _clip_candidates(-40, fine=False) == []
    for base in (1, 2, 9, 65, 5484, 16383):
        c = _clip_candidates(base, fine=True)
        assert c == sorted(set(c), reverse=True), (base, c)   # strictly decreasing
        assert len(c) <= 3 + 15


def test_rejected_exact_clip_steps_down_before_halving():
    """Server's check counts a few tokens more than usage reports: the retry
    must give up at most a handful of tokens, never half the room."""
    # off by one → base−1
    fake = _FakeCompletions(true_prompt=10900, check_overhead=1)
    resp = _chat(fake, 6144)
    assert fake.sent_max_tokens == [6144, 1, 5484, 5483]
    assert resp["num_predict_clipped_to"] == 5483
    assert resp["num_predict_measured_prompt"] == 10900
    # off by five → base−8
    fake = _FakeCompletions(true_prompt=10900, check_overhead=5)
    resp = _chat(fake, 6144)
    assert fake.sent_max_tokens == [6144, 1, 5484, 5483, 5476]
    assert resp["num_predict_clipped_to"] == 5476
    # off by forty → base−64
    fake = _FakeCompletions(true_prompt=10900, check_overhead=40)
    resp = _chat(fake, 6144)
    assert resp["num_predict_clipped_to"] == 5420
    # beyond every small step → halving, from the last value tried
    fake = _FakeCompletions(true_prompt=10900, check_overhead=100)
    resp = _chat(fake, 6144)
    assert fake.sent_max_tokens == [6144, 1, 5484, 5483, 5476, 5420, 2710]
    assert resp["num_predict_clipped_to"] == 2710
    assert resp["message"]["content"] == "VERDICT: VALID"


def test_clipped_response_records_measured_prompt():
    """prompt + clip is checkable against the window from the response."""
    fake = _FakeCompletions(true_prompt=10900)
    resp = _chat(fake, 6144)
    assert resp["num_predict_measured_prompt"] == 10900
    assert resp["num_predict_measured_prompt"] + resp["num_predict_clipped_to"] == _MAX_CTX
    # No usage on the probe → no measurement to record.
    fake = _FakeCompletions(true_prompt=10900, report_usage=False)
    resp = _chat(fake, 6144)
    assert resp["num_predict_measured_prompt"] is None
    # Unclipped responses carry none of it.
    resp = _chat(_FakeCompletions(true_prompt=3000), 6144)
    assert "num_predict_measured_prompt" not in resp


def test_unrelated_400_during_retry_is_raised():
    """A non-overflow 400 on the retry path must propagate, not be swallowed
    into a synthetic truncation."""
    fake = _FakeCompletions(true_prompt=10900, unrelated_400_on_call=3)
    try:
        _chat(fake, 6144)
    except BadRequestError as e:
        assert "schema mismatch" in str(e)
    else:
        raise AssertionError("expected the unrelated 400 to propagate")


def test_record_ctx_clip_keys_absent_by_default():
    """`tokens` keeps its old shape unless a turn overflowed; the last-turn
    key reflects only the final turn."""
    tokens: dict = {"prompt": 0, "completion": 0, "turns": 0}
    _record_ctx_clip(tokens, {"message": {}, "done_reason": "stop"})
    assert set(tokens) == {"prompt", "completion", "turns"}
    _record_ctx_clip(tokens, {"num_predict_clipped_to": 5484,
                              "num_predict_measured_prompt": 10900,
                              "prompt_eval_count": 10900})
    assert tokens["ctx_clipped_turns"] == 1
    assert tokens["ctx_clip_last_turn_max_tokens"] == 5484
    assert tokens["ctx_clip_last_turn_prompt_tokens"] == 10900
    assert (tokens["ctx_clip_last_turn_prompt_tokens"]
            + tokens["ctx_clip_last_turn_max_tokens"]) <= _MAX_CTX
    # no measurement → the turn's own reported prompt count
    _record_ctx_clip(tokens, {"num_predict_clipped_to": 3007,
                              "num_predict_measured_prompt": None,
                              "prompt_eval_count": 10950})
    assert tokens["ctx_clipped_turns"] == 2
    assert tokens["ctx_clip_last_turn_prompt_tokens"] == 10950
    # a later unclipped turn clears the last-turn markers, keeps the count
    _record_ctx_clip(tokens, {"message": {}, "done_reason": "stop"})
    assert tokens["ctx_clipped_turns"] == 2
    assert "ctx_clip_last_turn_max_tokens" not in tokens
    assert "ctx_clip_last_turn_prompt_tokens" not in tokens
    _record_ctx_clip(tokens, {"ctx_overflow_no_room": True})
    assert tokens["ctx_no_room_turns"] == 1


class _CaptureCompletions:
    """Records the kwargs of each create() call; always answers."""

    def __init__(self):
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        msg = SimpleNamespace(content="{}", tool_calls=None, reasoning_content=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg, finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=2),
        )


def _sent_extra_body(json_constraint: str | None, fmt) -> dict:
    fake = _CaptureCompletions()
    client = (VLLMClient(base_url="http://test") if json_constraint is None
              else VLLMClient(base_url="http://test", json_constraint=json_constraint))
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    asyncio.run(client.chat(model="m", messages=[{"role": "user", "content": "x"}],
                            options={"num_predict": 64}, format=fmt))
    return fake.calls[0].get("extra_body", {})


_SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string"}}}


def test_schema_default_field_is_guided_json():
    # The default must stay exactly what every earlier corpus sent.
    assert _sent_extra_body(None, _SCHEMA) == {"guided_json": _SCHEMA}
    assert _sent_extra_body("guided_json", _SCHEMA) == {"guided_json": _SCHEMA}


def test_schema_structured_outputs_field():
    assert _sent_extra_body("structured_outputs", _SCHEMA) == {
        "structured_outputs": {"json": _SCHEMA}}


def test_json_object_format_ignores_the_switch():
    # format="json" goes through response_format under both settings.
    assert _sent_extra_body("structured_outputs", "json") == {}


def test_json_constraint_from_environment():
    import os
    saved = os.environ.get("PDDL_JSON_CONSTRAINT")
    try:
        os.environ["PDDL_JSON_CONSTRAINT"] = "structured_outputs"
        assert _sent_extra_body(None, _SCHEMA) == {
            "structured_outputs": {"json": _SCHEMA}}
        # an explicit argument wins over the environment
        assert _sent_extra_body("guided_json", _SCHEMA) == {"guided_json": _SCHEMA}
        os.environ["PDDL_JSON_CONSTRAINT"] = ""
        assert _sent_extra_body(None, _SCHEMA) == {"guided_json": _SCHEMA}
    finally:
        if saved is None:
            os.environ.pop("PDDL_JSON_CONSTRAINT", None)
        else:
            os.environ["PDDL_JSON_CONSTRAINT"] = saved


def test_tool_call_id_styles():
    from pddl_eval.vllm_client import _to_openai_messages
    msgs = [
        {"role": "user", "content": "x"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"function": {"name": "a", "arguments": {}}},
                        {"function": {"name": "b", "arguments": {}}}]},
        {"role": "tool", "content": "r1"},
        {"role": "tool", "content": "r2"},
    ]
    # default: byte-identical to every earlier corpus
    d = _to_openai_messages(msgs)
    assert [c["id"] for c in d[1]["tool_calls"]] == ["call_1_0", "call_1_1"]
    assert [m["tool_call_id"] for m in d[2:]] == ["call_1_0", "call_1_1"]
    m9 = _to_openai_messages(msgs, "mistral9")
    ids = [c["id"] for c in m9[1]["tool_calls"]]
    assert ids == ["c00001000", "c00001001"]
    assert all(len(i) == 9 and i.isalnum() for i in ids)
    assert [m["tool_call_id"] for m in m9[2:]] == ids


def test_tool_call_id_style_from_environment():
    import os
    saved = os.environ.get("PDDL_TOOL_CALL_ID_STYLE")
    try:
        os.environ.pop("PDDL_TOOL_CALL_ID_STYLE", None)
        assert VLLMClient(base_url="http://test")._tool_call_id_style == "call"
        os.environ["PDDL_TOOL_CALL_ID_STYLE"] = "mistral9"
        assert VLLMClient(base_url="http://test")._tool_call_id_style == "mistral9"
        os.environ["PDDL_TOOL_CALL_ID_STYLE"] = "bogus"
        try:
            VLLMClient(base_url="http://test")
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    finally:
        if saved is None:
            os.environ.pop("PDDL_TOOL_CALL_ID_STYLE", None)
        else:
            os.environ["PDDL_TOOL_CALL_ID_STYLE"] = saved


def test_unknown_json_constraint_is_rejected():
    try:
        VLLMClient(base_url="http://test", json_constraint="guided")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ---------------------------------------------------------------------------
# Reasoning effort and the reasoning trace (2026-11-09). These go through the
# real openai SDK with an httpx mock transport, so they check the JSON body
# that would reach vLLM and the SDK's parsing of vLLM 0.20.2's response shape
# (`message.reasoning`, no `reasoning_content`).
# ---------------------------------------------------------------------------

_ENV_KEYS = ("PDDL_REASONING_EFFORT", "PDDL_STORE_REASONING",
             "PDDL_JSON_CONSTRAINT", "PDDL_TOOL_CALL_ID_STYLE",
             "PDDL_NO_TOOLS_SYSTEM", "PDDL_SYSTEM_AUDIT_LOG")


class _Env:
    """Set some PDDL_* variables (None = unset) and restore them after."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        import os
        self.saved = {k: os.environ.get(k) for k in _ENV_KEYS}
        for k in _ENV_KEYS:
            os.environ.pop(k, None)
        for k, v in self.values.items():
            if v is not None:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        import os
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _wire_client(reply_message: dict, **client_kwargs):
    """A VLLMClient whose AsyncOpenAI talks to a mock transport. Returns
    (client, list of raw request bodies)."""
    from openai import AsyncOpenAI
    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        return httpx.Response(200, json={
            "id": "chatcmpl-test", "object": "chat.completion", "created": 0,
            "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "tool_calls": [],
                                     **reply_message}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 22,
                      "total_tokens": 33},
        })

    client = VLLMClient(base_url="http://test", **client_kwargs)
    client._client = AsyncOpenAI(
        base_url="http://test/v1", api_key="EMPTY",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return client, bodies


_TOOL = {"type": "function", "function": {
    "name": "validate_plan", "description": "d",
    "parameters": {"type": "object", "properties": {}}}}

# Three request shapes the harness sends: no-tools with a schema and think
# off, with-tools think on (a replayed tool turn), and the decoupled call-1
# shape (vllm_extra). For each, the exact JSON body every corpus so far sent.
_SHAPES = [
    ("no-tools schema think-off",
     dict(messages=[{"role": "user", "content": "x"}],
          options={"temperature": 0.0, "num_predict": 64}, think=False,
          format=_SCHEMA),
     {"model": "m", "messages": [{"role": "user", "content": "x"}],
      "stream": False, "temperature": 0.0, "max_tokens": 64,
      "chat_template_kwargs": {"enable_thinking": False},
      "guided_json": _SCHEMA}),
    ("tools think-on",
     dict(messages=[{"role": "user", "content": "x"},
                    {"role": "assistant", "content": "", "thinking": "t",
                     "tool_calls": [{"function": {"name": "validate_plan",
                                                  "arguments": {}}}]},
                    {"role": "tool", "content": "ok"}],
          tools=[_TOOL], options={"temperature": 0.0, "num_predict": 128},
          think=True),
     {"model": "m",
      "messages": [{"role": "user", "content": "x"},
                   {"role": "assistant", "content": "",
                    "tool_calls": [{"id": "call_1_0", "type": "function",
                                    "function": {"name": "validate_plan",
                                                 "arguments": "{}"}}]},
                   {"role": "tool", "tool_call_id": "call_1_0", "content": "ok"}],
      "stream": False, "tools": [_TOOL], "tool_choice": "auto",
      "temperature": 0.0, "max_tokens": 128,
      "chat_template_kwargs": {"enable_thinking": True}}),
    ("decoupled call-1 (vllm_extra, stop)",
     dict(messages=[{"role": "user", "content": "x"}],
          options={"num_predict": 32}, think=True, stop=["</think>"],
          vllm_extra={"include_stop_str_in_output": True}),
     {"model": "m", "messages": [{"role": "user", "content": "x"}],
      "stream": False, "max_tokens": 32,
      "chat_template_kwargs": {"enable_thinking": True},
      "include_stop_str_in_output": True, "stop": ["</think>"]}),
]


def _send(client, kwargs) -> dict:
    return asyncio.run(client.chat(model="m", **kwargs))


def test_default_request_body_unchanged_on_the_wire():
    """No new setting given: each body is exactly the pre-change one, and
    the raw bytes do not depend on the new variables being unset or empty."""
    for label, kwargs, expected in _SHAPES:
        with _Env():
            client, bodies = _wire_client({"content": "a", "reasoning": None})
            _send(client, kwargs)
        assert json.loads(bodies[0]) == expected, label
        assert b"reasoning_effort" not in bodies[0], label
        with _Env(PDDL_REASONING_EFFORT="", PDDL_STORE_REASONING="0"):
            client2, bodies2 = _wire_client({"content": "a", "reasoning": None})
            _send(client2, kwargs)
        assert bodies2[0] == bodies[0], label
        # Storing the trace changes only how the answer is read, never the request.
        with _Env(PDDL_STORE_REASONING="1"):
            client3, bodies3 = _wire_client({"content": "a", "reasoning": None})
            _send(client3, kwargs)
        assert bodies3[0] == bodies[0], label


def test_reasoning_effort_is_a_top_level_field():
    """vLLM 0.20.2 reads request.reasoning_effort (top level) for gpt-oss;
    chat_template_kwargs is not read on the Harmony path."""
    for level in ("low", "medium", "high"):
        for label, kwargs, expected in _SHAPES:
            with _Env(PDDL_REASONING_EFFORT=level):
                client, bodies = _wire_client({"content": "a"})
                _send(client, kwargs)
            body = json.loads(bodies[0])
            assert body.pop("reasoning_effort") == level, label
            assert body == expected, label   # nothing else moved
            assert "reasoning_effort" not in body.get("chat_template_kwargs", {})
    # an explicit argument wins over the environment
    with _Env(PDDL_REASONING_EFFORT="high"):
        client, bodies = _wire_client({"content": "a"}, reasoning_effort="low")
        _send(client, _SHAPES[0][1])
    assert json.loads(bodies[0])["reasoning_effort"] == "low"


def test_reasoning_effort_values_are_checked():
    for bad in ("none", "minimal", "LOW", "off"):
        with _Env(PDDL_REASONING_EFFORT=bad):
            try:
                VLLMClient(base_url="http://test")
                raise AssertionError(f"expected ValueError for {bad!r}")
            except ValueError:
                pass
    with _Env(PDDL_STORE_REASONING="yes"):
        try:
            VLLMClient(base_url="http://test")
            raise AssertionError("expected ValueError for PDDL_STORE_REASONING=yes")
        except ValueError:
            pass


def test_reasoning_trace_is_dropped_by_default():
    """NEW-2: vLLM 0.20.2 returns the trace as `message.reasoning`. The
    default read (reasoning_content) misses it, as in every stored corpus."""
    with _Env():
        client, _ = _wire_client({"content": "VERDICT: VALID",
                                  "reasoning": "step 1 ... step 9"})
        resp = _send(client, _SHAPES[0][1])
    assert resp["message"]["thinking"] == ""
    assert resp["message"]["content"] == "VERDICT: VALID"


def test_reasoning_trace_is_stored_when_asked():
    with _Env(PDDL_STORE_REASONING="1"):
        client, _ = _wire_client({"content": "VERDICT: VALID",
                                  "reasoning": "step 1 ... step 9"})
        resp = _send(client, _SHAPES[0][1])
    assert resp["message"]["thinking"] == "step 1 ... step 9"
    assert resp["message"]["content"] == "VERDICT: VALID"
    assert resp["eval_count"] == 22 and resp["prompt_eval_count"] == 11


def test_non_think_rows_unchanged_when_storing():
    """A turn with no trace (reasoning null or absent) reads the same with
    and without the setting, apart from the wall-clock fields."""
    for reply in ({"content": "a", "reasoning": None}, {"content": "a"},
                  {"content": "a", "reasoning": ""}):
        out = []
        for flag in ("0", "1"):
            with _Env(PDDL_STORE_REASONING=flag):
                client, _ = _wire_client(reply)
                resp = _send(client, _SHAPES[0][1])
            resp.pop("total_duration"), resp.pop("eval_duration")
            out.append(resp)
        assert out[0] == out[1], reply
        assert out[0]["message"]["thinking"] == ""


def test_older_reasoning_content_field_still_read():
    """A server that sends the old field name: read with or without the setting."""
    for flag in ("0", "1"):
        with _Env(PDDL_STORE_REASONING=flag):
            client, _ = _wire_client({"content": "a", "reasoning_content": "old"})
            resp = _send(client, _SHAPES[0][1])
        assert resp["message"]["thinking"] == "old"


def test_stored_trace_reaches_the_harness_thinking_value():
    """chat_without_tools / chat_with_tools (frozen pddl_eval/chat.py) return
    message.thinking as the value runner.py stores in the row's `thinking`."""
    from pddl_eval.chat import chat_with_tools, chat_without_tools
    with _Env(PDDL_STORE_REASONING="1"):
        client, _ = _wire_client({"content": "VERDICT: VALID", "reasoning": "R"})
        text, done, tokens, thinking = asyncio.run(chat_without_tools(
            client, "m", [{"role": "user", "content": "x"}],
            num_predict=64, num_ctx=16384, think=None))
    assert (text, done, thinking) == ("VERDICT: VALID", "stop", "R")
    mcp = SimpleNamespace(tools=[_TOOL])
    with _Env(PDDL_STORE_REASONING="1"):
        client, bodies = _wire_client({"content": "done", "reasoning": "R2"})
        out = asyncio.run(chat_with_tools(
            client, "m", [{"role": "user", "content": "x"}], mcp,
            num_predict=64, num_ctx=16384, think=None))
    assert out[0] == "done" and out[-1] == "R2"
    with _Env():
        client, _ = _wire_client({"content": "done", "reasoning": "R2"})
        out = asyncio.run(chat_with_tools(
            client, "m", [{"role": "user", "content": "x"}], mcp,
            num_predict=64, num_ctx=16384, think=None))
    assert out[-1] == ""


# ---------------------------------------------------------------------------
# Control-prompt cells (development/control_prompt_fix_plan.md, 2026-11-23):
# $PDDL_NO_TOOLS_SYSTEM swaps the no-tools system text of solve/simulate, and
# $PDDL_SYSTEM_AUDIT_LOG logs what was sent. The messages come from the
# runner's real builder and go through the real chat_without_tools path
# (think off, format=TASK_SCHEMAS[task]), as evaluate_one sends them.
# ---------------------------------------------------------------------------

from pddl_eval.prompts import WITHOUT_TOOLS_SYSTEM_BY_TASK  # noqa: E402
from pddl_eval.runner import DEFAULT_NUM_PREDICT, build_messages  # noqa: E402
from pddl_eval.schemas import TASK_SCHEMAS  # noqa: E402

# Typed here, apart from pddl_eval/control_prompts.py, so a typo in either fails.
_CELL_TEXT = {
    "no-pointer": {
        "solve": "You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning.",
        "simulate": "You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; give the per-step state with boolean predicates and numeric fluents.",
    },
    "format-stated": {
        "solve": "You are a PDDL planning assistant. PDDL planning tools are not available in this evaluation. Analyze the domain and problem and produce a plan using your own reasoning; end your response with the plan alone, one parenthesised PDDL action per line.",
        "simulate": 'You are a PDDL simulation assistant. PDDL simulation tools are not available in this evaluation. Trace the state transitions using your own reasoning; end your response with a single JSON object of the form {"trajectory": [ ...steps... ]}, where each step has the keys step, action and state (state.boolean and state.numeric).',
    },
}
_DOMAIN = "(define (domain d) (:predicates (p)))"
_PROBLEM = "(define (problem q) (:domain d) (:init) (:goal (p)))"
_GT = {"plan": ["(a x)", "(b y)"]}


def _capture_client(**client_kwargs):
    fake = _CaptureCompletions()
    client = VLLMClient(base_url="http://test", **client_kwargs)
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return client, fake


def _no_tools_request(task: str, pv: int, **client_kwargs):
    """(create() kwargs, input messages) of one no-tools think-off trial."""
    from pddl_eval.chat import chat_without_tools
    msgs = build_messages(task, _DOMAIN, _PROBLEM, pv, False, _GT)
    client, fake = _capture_client(**client_kwargs)
    asyncio.run(chat_without_tools(
        client, "m", msgs, num_predict=DEFAULT_NUM_PREDICT[task],
        num_ctx=16384, think=False, format=TASK_SCHEMAS.get(task)))
    assert len(fake.calls) == 1
    return fake.calls[0], msgs


def test_control_default_request_unchanged():
    """No variable set: the request is the one every no-tools corpus sent."""
    for task in ("solve", "simulate"):
        for pv in (11, 12, 13):
            with _Env():
                sent, msgs = _no_tools_request(task, pv)
            user = msgs[1]["content"]
            assert msgs[0] == {"role": "system",
                               "content": WITHOUT_TOOLS_SYSTEM_BY_TASK[task]}
            assert sent == {
                "model": "m",
                "messages": [
                    {"role": "system", "content": WITHOUT_TOOLS_SYSTEM_BY_TASK[task]},
                    {"role": "user", "content": user}],
                "stream": False,
                "temperature": 0.0,
                "max_tokens": DEFAULT_NUM_PREDICT[task],
                "extra_body": {"chat_template_kwargs": {"enable_thinking": False},
                               "guided_json": TASK_SCHEMAS[task]},
            }, (task, pv)
            # An empty variable is the default too.
            with _Env(PDDL_NO_TOOLS_SYSTEM=""):
                assert _no_tools_request(task, pv)[0] == sent


def test_control_cells_swap_only_the_system_text():
    for task in ("solve", "simulate"):
        for pv in (11, 12, 13):
            with _Env():
                base, _ = _no_tools_request(task, pv)
            for mode in ("no-pointer", "format-stated"):
                with _Env(PDDL_NO_TOOLS_SYSTEM=mode):
                    sent, msgs = _no_tools_request(task, pv)
                # the input message list the runner built is not changed
                assert msgs[0]["content"] == WITHOUT_TOOLS_SYSTEM_BY_TASK[task]
                assert sent["messages"][0] == {"role": "system",
                                               "content": _CELL_TEXT[mode][task]}
                # the user message is byte-identical to cell O's
                assert sent["messages"][1] == base["messages"][1]
                assert sent["messages"][1]["content"].encode() == \
                    base["messages"][1]["content"].encode()
                # nothing else moved, guided_json included
                assert {k: v for k, v in sent.items() if k != "messages"} == \
                    {k: v for k, v in base.items() if k != "messages"}, (task, pv, mode)
                assert sent["extra_body"]["guided_json"] == TASK_SCHEMAS[task]
                assert len(sent["messages"]) == 2
            # an explicit argument works the same as the variable
            with _Env():
                arg, _ = _no_tools_request(task, pv, no_tools_system="no-pointer")
            assert arg["messages"][0]["content"] == _CELL_TEXT["no-pointer"][task]


def test_control_swap_fails_closed():
    from pddl_eval.prompts import (WITH_TOOLS_SYSTEM, WITH_TOOLS_SYSTEM_BY_TASK,
                                   WITHOUT_TOOLS_SYSTEM)
    user = {"role": "user", "content": "x"}
    cases = [
        ("validation task", [{"role": "system",
                              "content": WITHOUT_TOOLS_SYSTEM_BY_TASK["validate_plan"]}, user], None),
        ("with-tools text", [{"role": "system",
                              "content": WITH_TOOLS_SYSTEM_BY_TASK["solve"]}, user], None),
        ("legacy flat no-tools text", [{"role": "system", "content": WITHOUT_TOOLS_SYSTEM}, user], None),
        ("legacy flat with-tools text", [{"role": "system", "content": WITH_TOOLS_SYSTEM}, user], None),
        ("no system message", [user], None),
        ("system not first", [user, {"role": "system",
                                     "content": WITHOUT_TOOLS_SYSTEM_BY_TASK["solve"]}], None),
        ("tools passed", [{"role": "system",
                           "content": WITHOUT_TOOLS_SYSTEM_BY_TASK["solve"]}, user], [_TOOL]),
        ("empty tools list passed", [{"role": "system",
                                      "content": WITHOUT_TOOLS_SYSTEM_BY_TASK["solve"]}, user], []),
    ]
    for mode in ("no-pointer", "format-stated"):
        for label, msgs, tools in cases:
            with _Env(PDDL_NO_TOOLS_SYSTEM=mode):
                client, fake = _capture_client()
                try:
                    asyncio.run(client.chat(model="m", messages=msgs, tools=tools,
                                            options={"num_predict": 8}))
                    raise AssertionError(f"expected ValueError: {label}")
                except ValueError:
                    pass
            assert fake.calls == [], label   # no request sent
    # unknown mode: error at construction
    for bad in ("registered", "nopointer", "format", "B", "1"):
        with _Env(PDDL_NO_TOOLS_SYSTEM=bad):
            try:
                VLLMClient(base_url="http://test")
                raise AssertionError(f"expected ValueError for {bad!r}")
            except ValueError:
                pass
        try:
            VLLMClient(base_url="http://test", no_tools_system=bad)
            raise AssertionError(f"expected ValueError for argument {bad!r}")
        except ValueError:
            pass


def test_control_tool_arm_untouched_without_mode():
    """No mode: a tool-arm request with tools is sent as before."""
    with _Env():
        client, fake = _capture_client()
        asyncio.run(client.chat(model="m", messages=[{"role": "user", "content": "x"}],
                                tools=[_TOOL], options={"num_predict": 8}))
    assert fake.calls[0]["tools"] == [_TOOL]


def _audit_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_system_audit_log():
    import hashlib
    import tempfile

    def h(s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        # unset: no file is touched
        log = Path(tmp) / "audit.jsonl"
        with _Env():
            base, msgs = _no_tools_request("solve", 11)
        assert not log.exists() and list(Path(tmp).iterdir()) == []
        user = msgs[1]["content"]

        # registered cell: one line per call, system_text on first sight only
        with _Env(PDDL_SYSTEM_AUDIT_LOG=str(log)):
            from pddl_eval.chat import chat_without_tools
            client, fake = _capture_client()
            for task in ("solve", "solve", "simulate"):
                m = build_messages(task, _DOMAIN, _PROBLEM, 11, False, _GT)
                asyncio.run(chat_without_tools(
                    client, "m", m, num_predict=DEFAULT_NUM_PREDICT[task],
                    num_ctx=16384, think=False, format=TASK_SCHEMAS.get(task)))
        # the request is the same with and without the audit
        assert fake.calls[0] == base
        lines = _audit_lines(log)
        assert len(lines) == 3
        o_solve = WITHOUT_TOOLS_SYSTEM_BY_TASK["solve"]
        o_sim = WITHOUT_TOOLS_SYSTEM_BY_TASK["simulate"]
        assert lines[0] == {"mode": "registered", "swapped": False,
                            "system_sha256": h(o_solve), "user_sha256": h(user),
                            "model": "m", "has_tools": False, "system_text": o_solve}
        assert "system_text" not in lines[1]
        assert lines[1]["system_sha256"] == h(o_solve)
        assert lines[2]["system_text"] == o_sim and lines[2]["system_sha256"] == h(o_sim)

        # swapped cell: the text actually sent is logged
        log2 = Path(tmp) / "audit2.jsonl"
        for mode in ("no-pointer", "format-stated"):
            with _Env(PDDL_NO_TOOLS_SYSTEM=mode):
                plain, _ = _no_tools_request("simulate", 12)
            with _Env(PDDL_NO_TOOLS_SYSTEM=mode, PDDL_SYSTEM_AUDIT_LOG=str(log2)):
                audited, m2 = _no_tools_request("simulate", 12)
            assert audited == plain
            last = _audit_lines(log2)[-1]
            text = _CELL_TEXT[mode]["simulate"]
            assert last == {"mode": mode, "swapped": True,
                            "system_sha256": h(text),
                            "user_sha256": h(m2[1]["content"]),
                            "model": "m", "has_tools": False, "system_text": text}

        # a tool-arm call (no mode) is logged with has_tools and no user text
        log3 = Path(tmp) / "audit3.jsonl"
        with _Env(PDDL_SYSTEM_AUDIT_LOG=str(log3)):
            client, _ = _capture_client()
            asyncio.run(client.chat(model="m", messages=[{"role": "user", "content": "x"}],
                                    tools=[_TOOL], options={"num_predict": 8}))
        (only,) = _audit_lines(log3)
        assert only["system_sha256"] is None and "system_text" not in only
        assert only["has_tools"] is True and only["user_sha256"] == h("x")

        # a failed write raises
        with _Env(PDDL_SYSTEM_AUDIT_LOG=str(Path(tmp) / "missing-dir" / "a.jsonl")):
            client, fake = _capture_client()
            try:
                asyncio.run(client.chat(model="m", messages=[{"role": "user", "content": "x"}],
                                        options={"num_predict": 8}))
                raise AssertionError("expected OSError")
            except OSError:
                pass


if __name__ == "__main__":
    # Plain-python entry point so tests/verify.sh (no pytest dependency) can
    # run this file; pytest collects the same functions directly.
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _tests:
        try:
            _fn()
        except Exception as exc:  # noqa: BLE001 — report every failure
            _failed += 1
            print(f"  FAIL {_name}: {type(exc).__name__}: {exc}")
    print(f"\ntest_vllm_client: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
