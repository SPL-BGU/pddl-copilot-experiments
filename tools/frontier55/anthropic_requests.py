"""Request shape for the Anthropic Messages API, for the two models of the
Claude run registered in development/reference/frontier55_prereg.md.

Everything that is specific to this provider's request and response format
lives here, and nothing here does I/O: the functions take and return plain
dicts. A second provider would get its own module of this shape; the runner
would not change.

What a request holds, and nothing else:
  model, max_tokens, system, messages, thinking, output_config.effort,
  and `tools` in the tool arm.

What it never holds (section 2.3 of the registration):
  temperature / top_p / top_k (the models reject a non-default value),
  output_config.format (no structured output), cache_control, an assistant
  prefill, tool_choice (the default, "auto", applies), a fallback model.
"""
from __future__ import annotations

import re
from typing import Any

# Per model: the thinking setting and the effort level. The effort is each
# model's default, sent explicitly so that the request records it.
MODEL_SETTINGS: dict[str, dict[str, Any]] = {
    "claude-haiku-5-5": {
        "thinking": {"type": "disabled"},
        "effort": "medium",
    },
    "claude-sonnet-5-5": {
        # The lowest setting this model accepts: no thinking before the
        # answer; short notes between tool calls come back as `thinking`
        # blocks. No other field may sit inside `thinking`.
        "thinking": {"type": "between_tools"},
        "effort": "high",
    },
}
MODELS: tuple[str, ...] = tuple(MODEL_SETTINGS)

# Keys a request may hold. `build_params` builds exactly these; the runner
# checks every request against the set before it is sent.
ALLOWED_PARAM_KEYS = frozenset(
    {"model", "max_tokens", "system", "messages", "thinking", "output_config", "tools"})
FORBIDDEN_PARAM_KEYS = frozenset(
    {"temperature", "top_p", "top_k", "tool_choice", "stop_sequences", "metadata",
     "fallbacks", "cache_control", "stream", "betas", "service_tier"})

# Stop reasons of the API mapped to the harness's words (the frozen loader
# of the rerun accepts only "stop", "length", "tool_calls" and "").
STOP_END = "end_turn"
STOP_MAX_TOKENS = "max_tokens"
STOP_TOOL_USE = "tool_use"
STOP_REFUSAL = "refusal"
STOP_PAUSE = "pause_turn"
STOP_SEQUENCE = "stop_sequence"
STOP_WINDOW = "model_context_window_exceeded"
DONE_REASON_OF_STOP = {
    STOP_END: "stop",
    STOP_SEQUENCE: "stop",
    STOP_MAX_TOKENS: "length",
    STOP_WINDOW: "length",
    STOP_TOOL_USE: "tool_calls",
}

# The API's 400 when the conversation does not fit the model's window. The wording is
# matched loosely: the prompt, the input or the context being too long or too large, or
# anything exceeding the context window or length.
OVERFLOW_RE = re.compile(
    r"(prompt|context|conversation)[^.\n]{0,80}(too long|too large|exceed)"
    r"|exceed[^.\n]{0,80}context"
    r"|context (window|length)",
    re.IGNORECASE)
SAMPLING_KEYS = frozenset({"temperature", "top_p", "top_k"})


def tool_definitions(mcp_tools: list[dict]) -> list[dict]:
    """The harness's tool list (OpenAI function shape, as `MCPPlanner.tools`
    holds it) as Anthropic tool definitions. The name, the description and
    the JSON schema are passed through unchanged."""
    out = []
    for t in mcp_tools:
        fn = t["function"]
        out.append({
            "name": fn["name"],
            "description": fn["description"],
            "input_schema": fn["parameters"],
        })
    return out


def build_params(model: str, system: str, messages: list[dict], max_tokens: int,
                 tools: list[dict] | None = None) -> dict:
    """One Messages API request. `tools` is None in the no-tools arm (the
    key is then absent) and the full tool list in the tool arm."""
    if model not in MODEL_SETTINGS:
        raise ValueError(f"unknown model {model!r}; registered: {MODELS}")
    s = MODEL_SETTINGS[model]
    params: dict[str, Any] = {
        "model": model,
        "max_tokens": int(max_tokens),
        "system": system,
        "messages": messages,
        "thinking": dict(s["thinking"]),
        "output_config": {"effort": s["effort"]},
    }
    if tools is not None:
        params["tools"] = tools
    check_params(params)
    return params


def check_params(params: dict) -> None:
    """Raise unless `params` holds only what the registration allows."""
    keys = set(params)
    bad = keys & FORBIDDEN_PARAM_KEYS
    if bad:
        raise ValueError(f"request holds forbidden key(s) {sorted(bad)}")
    extra = keys - ALLOWED_PARAM_KEYS
    if extra:
        raise ValueError(f"request holds unregistered key(s) {sorted(extra)}")
    if set(params["output_config"]) != {"effort"}:
        raise ValueError("output_config may hold `effort` only (no `format`)")
    model = params["model"]
    s = MODEL_SETTINGS.get(model)
    if s is None:
        raise ValueError(f"unknown model {model!r}")
    if params["thinking"] != s["thinking"] or params["output_config"]["effort"] != s["effort"]:
        raise ValueError(f"{model}: thinking / effort differ from the registered setting")
    msgs = params["messages"]
    if not msgs or msgs[0]["role"] != "user" or msgs[-1]["role"] != "user":
        raise ValueError("the conversation must start and end with a user message "
                         "(no assistant prefill)")


def user_message(text: str) -> dict:
    return {"role": "user", "content": text}


def blocks_as_returned(message) -> list[dict]:
    """The content blocks of a response as plain dicts, holding exactly the
    fields the API returned (`exclude_unset`), fields this SDK version does
    not know included. This is how the SDK itself serialises a response
    object that is passed back in a request, so a `thinking` block goes back
    with its signature unchanged."""
    out = []
    for b in message.content:
        if isinstance(b, dict):
            out.append(dict(b))
        else:
            out.append(b.model_dump(mode="json", exclude_unset=True, by_alias=True))
    return out


def assistant_turn(blocks: list[dict]) -> dict:
    """The assistant message to append: every block, in order, unchanged."""
    return {"role": "assistant", "content": blocks}


def tool_uses(blocks: list[dict]) -> list[dict]:
    return [b for b in blocks if b.get("type") == "tool_use"]


def tool_result_block(tool_use_id: str, text: str, is_error: bool) -> dict:
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
    if is_error:
        block["is_error"] = True
    return block


def tool_results_turn(result_blocks: list[dict]) -> dict:
    """One user message that holds every tool result of the turn."""
    return {"role": "user", "content": result_blocks}


def text_of(blocks: list[dict]) -> str:
    return "".join(b.get("text") or "" for b in blocks if b.get("type") == "text")


def thinking_of(blocks: list[dict]) -> str:
    return "\n\n".join(b.get("thinking") or "" for b in blocks if b.get("type") == "thinking")


def dump(obj) -> Any:
    """A response sub-object (usage, stop_details) as JSON-ready data."""
    if obj is None or isinstance(obj, (str, int, float, bool, dict, list)):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_unset=True, by_alias=True)
    return str(obj)


def input_tokens_of(usage: dict | None) -> int:
    """Every input token of one response: uncached, cache-written and
    cache-read. The run sends no cache_control, so the last two are expected
    to be zero; they are summed so the total is right either way."""
    u = usage or {}
    return (int(u.get("input_tokens") or 0)
            + int(u.get("cache_creation_input_tokens") or 0)
            + int(u.get("cache_read_input_tokens") or 0))


def output_tokens_of(usage: dict | None) -> int:
    return int((usage or {}).get("output_tokens") or 0)


def is_overflow_error(exc: Exception) -> bool:
    """True for a 400 whose message says the prompt or context is too long."""
    status = getattr(exc, "status_code", 400)
    return status == 400 and OVERFLOW_RE.search(str(exc)) is not None


def request_settings(params: dict) -> dict:
    """What the sidecar keeps of a request: every field except the texts and the tool
    list, and the list of field names."""
    rec = {k: v for k, v in params.items() if k not in ("system", "messages", "tools")}
    rec["param_keys"] = sorted(params)
    rec["has_tools"] = "tools" in params
    rec["n_messages"] = len(params.get("messages") or [])
    return rec


def registered_request_settings(model: str, max_tokens: int, with_tools: bool,
                                n_messages: int) -> dict:
    """What `request_settings` must return for a registered request."""
    s = MODEL_SETTINGS[model]
    keys = ["max_tokens", "messages", "model", "output_config", "system", "thinking"]
    if with_tools:
        keys.append("tools")
    return {"model": model, "max_tokens": max_tokens, "thinking": dict(s["thinking"]),
            "output_config": {"effort": s["effort"]}, "param_keys": sorted(keys),
            "has_tools": with_tools, "n_messages": n_messages}


# ------------------------------------------------------------------ prices and usage
# $ per million tokens (input, output), list price, as registered (section 9). `long`
# applies to a request whose prompt is above `long_over` tokens.
PRICES: dict[str, dict[str, Any]] = {
    "claude-haiku-5-5": {"base": (0.10, 0.50), "long": (0.50, 2.50), "long_over": 100_000},
    "claude-sonnet-5-5": {"base": (2.00, 10.00), "long": None, "long_over": None},
}
BATCH_FACTOR = 0.5          # the Batch API's price against the list price
CACHE_WRITE_FACTOR = 1.25   # against the input rate; the run asks for no caching
CACHE_READ_FACTOR = 0.10


def usage_usd(model: str, usage: dict | None, *, batch: bool) -> float:
    """The price of one response from its usage block."""
    u = usage or {}
    inp = int(u.get("input_tokens") or 0)
    cw = int(u.get("cache_creation_input_tokens") or 0)
    cr = int(u.get("cache_read_input_tokens") or 0)
    out = int(u.get("output_tokens") or 0)
    p = PRICES[model]
    rate_in, rate_out = p["base"]
    if p["long"] and inp + cw + cr > p["long_over"]:
        rate_in, rate_out = p["long"]
    usd = (inp * rate_in + cw * rate_in * CACHE_WRITE_FACTOR
           + cr * rate_in * CACHE_READ_FACTOR + out * rate_out) / 1e6
    return usd * (BATCH_FACTOR if batch else 1.0)


def _sum_keys(obj, words: tuple[str, ...]) -> int:
    total = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                total += _sum_keys(v, words)
            elif isinstance(v, int) and not isinstance(v, bool) and any(w in k for w in words):
                total += v
    elif isinstance(obj, list):
        for v in obj:
            total += _sum_keys(v, words)
    return total


def thinking_tokens_of(usage: dict | None) -> int:
    """Every count in a usage block whose field name says thinking or reasoning."""
    return _sum_keys(usage or {}, ("thinking", "reasoning"))


def cache_tokens_of(usage: dict | None) -> int:
    return _sum_keys(usage or {}, ("cache",))


def canonical(block: dict) -> str:
    """One JSON text per value, so two blocks can be compared byte for byte."""
    import json
    return json.dumps(block, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
