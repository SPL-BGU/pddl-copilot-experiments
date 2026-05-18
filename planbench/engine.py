"""PlanBench engine adapter for the pddl-copilot model fleet.

Engine name format: ``pddl_copilot__<backend>__<model>``
  - backend: ``ollama`` or ``vllm``
  - model:   the model tag, e.g. ``qwen3:0.6b`` (colons preserved by the
             double-underscore separator).

Env vars:
  ``OLLAMA_HOST`` — Ollama server URL (default ``http://localhost:11434``).
  ``VLLM_BASE``   — vLLM ``/v1`` base URL (required when backend is ``vllm``).
  ``VLLM_API_KEY``— optional bearer token for vLLM.

PlanBench's ``send_query`` is sync; this is sync too. PlanBench iterates
instances itself — one request per call.
"""

from __future__ import annotations

import json
import os
import sys


_DEFAULT_NUM_PREDICT = 4096
_TEMPERATURE = 0.0
_KEEP_ALIVE = "1h"
_DEFAULT_TIMEOUT_S = 600


def _effective_num_predict(planbench_max_tokens: int) -> int:
    """PlanBench passes ``self.max_gpt_response_length = 500`` (a legacy
    OpenAI-completion cap). Thinking-capable models (qwen3.x, qwen3.6) eat
    most of that budget on the reasoning trace and emit empty content —
    smoke against qwen3:0.6b at 500 returned ``""``. Use 500 as a floor;
    fall back to 4096 (matches `pddl_eval/runner.py` non-solve defaults)."""
    return max(int(planbench_max_tokens or 0), _DEFAULT_NUM_PREDICT)


def _parse_engine_name(engine: str) -> tuple[str, str]:
    """``pddl_copilot__ollama__qwen3:0.6b`` -> ``('ollama', 'qwen3:0.6b')``."""
    if not engine.startswith("pddl_copilot__"):
        raise ValueError(f"engine name must start with 'pddl_copilot__': {engine!r}")
    rest = engine[len("pddl_copilot__") :]
    parts = rest.split("__", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"engine name must be 'pddl_copilot__<backend>__<model>': {engine!r}"
        )
    backend, model = parts
    if backend not in {"ollama", "vllm"}:
        raise ValueError(
            f"unsupported backend {backend!r}; expected 'ollama' or 'vllm'"
        )
    return backend, model


def _ollama_chat(query: str, model: str, max_tokens: int, stop: str) -> str:
    import ollama

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)
    # Only honor the caller-supplied stop (PlanBench passes "[STATEMENT]",
    # the few-shot delimiter). We deliberately do NOT add "[PLAN END]" as a
    # stop: stop strings match against the model's hidden thinking trace
    # too, and qwen3.x / qwen3.6 echo "[PLAN END]" while reasoning about
    # the prompt — generation halts before any content is emitted (smoke
    # 2026-05-18 reproduced empty content on qwen3:0.6b). The parser
    # already extracts the [PLAN]…[PLAN END] block from full output.
    stops = [stop] if stop else []
    resp = client.chat(
        model=model,
        messages=[{"role": "user", "content": query}],
        options={
            "temperature": _TEMPERATURE,
            "num_predict": _effective_num_predict(max_tokens),
            "stop": stops,
        },
        keep_alive=_KEEP_ALIVE,
    )
    return resp["message"].get("content", "").strip()


def _vllm_chat(query: str, model: str, max_tokens: int, stop: str) -> str:
    import httpx

    base = os.environ.get("VLLM_BASE")
    if not base:
        raise RuntimeError("backend=vllm requires VLLM_BASE env var")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("VLLM_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    # Only honor the caller-supplied stop (PlanBench passes "[STATEMENT]",
    # the few-shot delimiter). We deliberately do NOT add "[PLAN END]" as a
    # stop: stop strings match against the model's hidden thinking trace
    # too, and qwen3.x / qwen3.6 echo "[PLAN END]" while reasoning about
    # the prompt — generation halts before any content is emitted (smoke
    # 2026-05-18 reproduced empty content on qwen3:0.6b). The parser
    # already extracts the [PLAN]…[PLAN END] block from full output.
    stops = [stop] if stop else []
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "temperature": _TEMPERATURE,
        "max_tokens": _effective_num_predict(max_tokens),
        "stop": stops,
    }
    url = base.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=_DEFAULT_TIMEOUT_S) as client:
        r = client.post(url, headers=headers, content=json.dumps(payload))
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def pddl_copilot_send_query(
    query: str,
    engine: str,
    max_tokens: int,
    model=None,  # PlanBench passes the preloaded handle here; we ignore it.
    stop: str = "[STATEMENT]",
) -> str:
    """PlanBench-compatible ``send_query`` for the pddl-copilot model fleet.

    Returns the model's full response (stripped). Empty string on failure —
    PlanBench treats ``""`` as a failed instance and retries with
    ``--run_till_completion``.
    """
    try:
        backend, model_tag = _parse_engine_name(engine)
        if backend == "ollama":
            return _ollama_chat(query, model_tag, max_tokens, stop)
        return _vllm_chat(query, model_tag, max_tokens, stop)
    except Exception as exc:
        print(f"[-] pddl_copilot engine failed for {engine!r}: {exc}", file=sys.stderr)
        return ""
