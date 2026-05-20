"""Regression tests for pddl_eval.vllm_client.

Currently focused on `_CTX_OVERFLOW_RE` — silently missing the new vLLM
error-body shape caused 24 600 trials to be miscategorized as `FR_EXCEPTION`
(PR-#66 contamfix, 2026-05-20). The test pins both observed body shapes so
the next vLLM-message-text bump trips a unit-test failure instead of
silently corrupting a sweep.
"""
from openai import BadRequestError
import httpx

from pddl_eval.vllm_client import _parse_ctx_overflow


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


def test_parse_ctx_overflow_returns_none_for_unrelated_400():
    """A non-overflow 400 must return None so the caller re-raises."""
    body = "Error code: 400 - Bad Request: tool argument schema mismatch."
    assert _parse_ctx_overflow(_make_err(body)) is None
