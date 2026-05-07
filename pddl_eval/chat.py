"""Ollama chat loop, MCPPlanner, and shared JSON / verdict helpers.

Owns the LLM-side primitives:
  * `MCPPlanner` — stdio connection manager for solver + validator MCP servers.
  * `chat_with_tools`, `chat_without_tools` — Ollama chat-loop helpers.
  * `_safe_json_loads`, `_parse_validation_verdict` — JSON / verdict helpers.

Why JSON helpers live here (not in `domains.py`): they're consumed by both
`scoring.check_success` and `domains.generate_ground_truth`. Placing them
in `chat` (the lowest leaf in the package DAG) keeps `domains` and
`scoring` as siblings without a circular dependency.
"""

import json
import os
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

TEMPERATURE = 0.0
MAX_TOOL_LOOPS = 10
# Ollama "keep this model loaded in VRAM" hint, sent on every chat() call.
# Ollama's default keep_alive is 5 min; "1h" comfortably covers the longest
# within-job idle gap we see in practice and prevents the model from being
# evicted between consecutive requests in the same condition.
KEEP_ALIVE = "1h"


# ---------------------------------------------------------------------------
# JSON / verdict helpers (shared by domains + scoring)
# ---------------------------------------------------------------------------


def _safe_json_loads(raw):
    """Parse JSON if *raw* is a string; pass through dicts/lists; None on failure.

    Centralises the `json.loads(raw) if isinstance(raw, str) else raw` shape
    used across scoring, ground-truth, and tool-error paths so they all
    handle string-shape MCP results and pre-parsed dict shapes uniformly.
    """
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _parse_validation_verdict(raw: str) -> bool | None:
    """Parse a validate_pddl_syntax result string.

    Expects the pyvalidator shape {"valid", "status", "report", "details"}.
    Returns True if valid, False if invalid, None on error or unparseable.
    """
    data = _safe_json_loads(raw)
    if not isinstance(data, dict):
        return None
    if data.get("error") is True:
        return None
    if "valid" not in data:
        return None
    return bool(data["valid"])


# ---------------------------------------------------------------------------
# MCP connection (mirrors ollama_mcp_bridge.py patterns)
# ---------------------------------------------------------------------------


class MCPPlanner:
    """Manages stdio connections to PDDL MCP servers (solver + validator)."""

    # Validator tools expose a `verbose` param that toggles the large
    # `details` / verbose `report` fields. The experiment bridge hides the
    # param from the LLM and pins it to False so tool responses stay compact
    # while preserving full fidelity for other MCP callers by default.
    _PINNED_VERBOSE_FALSE = {"validate_pddl_syntax", "get_state_transition"}

    def __init__(self):
        self.stack = AsyncExitStack()
        self.tools: list[dict] = []
        self._tool_to_session: dict[str, ClientSession] = {}

    @staticmethod
    def _strip_verbose_from_schema(schema: dict) -> dict:
        """Return a copy of an MCP inputSchema with the 'verbose' property hidden."""
        if not isinstance(schema, dict):
            return schema
        out = dict(schema)
        props = out.get("properties")
        if isinstance(props, dict) and "verbose" in props:
            new_props = {k: v for k, v in props.items() if k != "verbose"}
            out["properties"] = new_props
        req = out.get("required")
        if isinstance(req, list) and "verbose" in req:
            out["required"] = [r for r in req if r != "verbose"]
        return out

    async def connect(self, plugin_dirs: list[Path]):
        for plugin_dir in plugin_dirs:
            launch_script = plugin_dir / "scripts" / "launch-server.sh"
            if not launch_script.exists():
                print(f"  Warning: launch script not found: {launch_script}, skipping")
                continue

            server_params = StdioServerParameters(
                command="bash",
                args=[str(launch_script)],
                env={**os.environ},
            )
            read_stream, write_stream = await self.stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await self.stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()

            tools_result = await session.list_tools()
            for t in tools_result.tools:
                schema = t.inputSchema
                if t.name in self._PINNED_VERBOSE_FALSE:
                    schema = self._strip_verbose_from_schema(schema)
                self.tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": schema,
                    },
                })
                self._tool_to_session[t.name] = session

            names = [t.name for t in tools_result.tools]
            print(f"  MCP connected ({plugin_dir.name}) — tools: {names}")

    async def call_tool(self, name: str, arguments: dict) -> str:
        session = self._tool_to_session.get(name)
        if not session:
            raise ValueError(f"Tool '{name}' not found in any connected MCP server")
        if name in self._PINNED_VERBOSE_FALSE:
            arguments = {**(arguments or {}), "verbose": False}
        result = await session.call_tool(name, arguments=arguments)
        return result.content[0].text if result.content else ""

    async def close(self):
        await self.stack.aclose()


# ---------------------------------------------------------------------------
# Ollama chat helpers
# ---------------------------------------------------------------------------


def _build_chat_kwargs(
    num_predict: int,
    num_ctx: int,
    temperature: float,
    think: bool | None,
) -> tuple[dict, dict]:
    """Return (options, extra_kwargs) for an ollama client chat() call.

    `think` is a top-level kwarg on ollama>=0.6; when None it must be omitted
    entirely so the model's default behaviour applies.
    """
    options = {
        "temperature": temperature,
        "num_predict": num_predict,
        "num_ctx": num_ctx,
    }
    extra: dict = {"keep_alive": KEEP_ALIVE}
    if think is not None:
        extra["think"] = think
    return options, extra


def _response_done_reason(resp) -> str:
    """Extract done_reason from an ollama ChatResponse (dict or pydantic)."""
    if resp is None:
        return ""
    if hasattr(resp, "done_reason"):
        return getattr(resp, "done_reason") or ""
    if isinstance(resp, dict):
        return resp.get("done_reason") or ""
    return ""


def _response_field(resp, name: str) -> int:
    """Extract an int field from an ollama ChatResponse (dict or pydantic).

    Used for accumulating prompt_eval_count / eval_count / total_duration /
    eval_duration across tool-call turns. Returns 0 when missing so the
    accumulator never trips on partial responses (some Ollama builds omit
    counts on early-stop turns).
    """
    if resp is None:
        return 0
    if hasattr(resp, name):
        v = getattr(resp, name)
        return int(v) if v is not None else 0
    if isinstance(resp, dict):
        v = resp.get(name)
        return int(v) if v is not None else 0
    return 0


def _response_thinking(resp) -> str:
    """Extract message.thinking from an ollama ChatResponse (dict or pydantic).

    Returns "" when the model did not emit structured thinking content.
    Defensive against the inline `<think>...</think>` form (handled
    downstream in scoring.extract_*).
    """
    if resp is None:
        return ""
    msg = resp.get("message") if isinstance(resp, dict) else getattr(resp, "message", None)
    if msg is None:
        return ""
    if isinstance(msg, dict):
        return msg.get("thinking") or ""
    return getattr(msg, "thinking", "") or ""


async def chat_with_tools(
    client: "ollama.AsyncClient",
    model: str,
    messages: list[dict],
    mcp: MCPPlanner,
    num_predict: int,
    num_ctx: int,
    allowed_tools: list[str] | None = None,
    max_loops: int = MAX_TOOL_LOOPS,
    temperature: float = TEMPERATURE,
    think: bool | None = None,
) -> tuple[str, list[dict], str, bool, dict, str]:
    """Send messages to Ollama, handle tool-call loops.

    Returns (text, tool_calls_log, last_done_reason, loop_exhausted, tokens,
    thinking). `tokens` is a dict accumulating prompt_eval_count +
    eval_count + total_duration_ns + eval_duration_ns + turns across every
    chat() call in the loop. `thinking` is the LAST turn's structured
    `message.thinking` content (empty for non-thinking models); earlier-turn
    thinking is observable via `tool_calls[]`.

    The done_reason is taken from the final turn — callers use it to detect
    num_predict truncation ("length") vs. natural stop ("stop"). The
    loop_exhausted flag is True when we fell out of the max_loops cap without
    the model emitting a tool-call-free assistant message — callers treat it
    as a distinct failure mode (FR_LOOP_EXHAUSTED) because `text` is empty
    by construction (the model never got to answer). If `allowed_tools` is
    given, only tools with those names are exposed to the model.
    """
    tool_calls_log: list[dict] = []

    if allowed_tools is None:
        tools_payload = mcp.tools
    else:
        allowed_set = set(allowed_tools)
        tools_payload = [t for t in mcp.tools if t["function"]["name"] in allowed_set]

    options, extra = _build_chat_kwargs(num_predict, num_ctx, temperature, think)
    last_done_reason = ""
    tokens = {
        "prompt": 0,
        "completion": 0,
        "turns": 0,
        "total_duration_ns": 0,
        "eval_duration_ns": 0,
    }
    thinking_text = ""

    for _ in range(max_loops):
        resp = await client.chat(
            model=model,
            messages=messages,
            tools=tools_payload,
            options=options,
            **extra,
        )
        last_done_reason = _response_done_reason(resp)
        tokens["prompt"] += _response_field(resp, "prompt_eval_count")
        tokens["completion"] += _response_field(resp, "eval_count")
        tokens["total_duration_ns"] += _response_field(resp, "total_duration")
        tokens["eval_duration_ns"] += _response_field(resp, "eval_duration")
        tokens["turns"] += 1
        thinking_text = _response_thinking(resp)
        msg = resp["message"]
        messages.append(msg)

        if not msg.get("tool_calls"):
            return msg.get("content", ""), tool_calls_log, last_done_reason, False, tokens, thinking_text

        for tc in msg["tool_calls"]:
            fn = tc["function"]
            tool_name = fn["name"]
            tool_args = fn.get("arguments", {})
            try:
                result_text = await mcp.call_tool(tool_name, tool_args)
            except Exception as exc:
                result_text = f"Tool error: {exc}"

            tool_calls_log.append({"name": tool_name, "arguments": tool_args, "result": result_text})

            messages.append({"role": "tool", "content": result_text})

    # Exhausted loops — the model kept calling tools without ever producing an
    # assistant-text answer. Returning the last tool output as `text` would
    # corrupt the record's `response` field (it is tool output, not model
    # text). Return empty text + loop_exhausted=True so the caller can label
    # this as FR_LOOP_EXHAUSTED.
    return "", tool_calls_log, last_done_reason, True, tokens, thinking_text


async def chat_without_tools(
    client: "ollama.AsyncClient",
    model: str,
    messages: list[dict],
    num_predict: int,
    num_ctx: int,
    temperature: float = TEMPERATURE,
    think: bool | None = None,
    format: dict | str | None = None,
) -> tuple[str, str, dict, str]:
    """Single-turn chat without tools.

    Returns (text, done_reason, tokens, thinking). `tokens` mirrors the
    shape returned by `chat_with_tools` (turns is always 1 here). `thinking`
    is the structured `message.thinking` content; "" when absent.

    `format` (PR-4) is forwarded to the Ollama `format=` kwarg. A dict is
    treated as a JSON schema (sampler constrained to matching JSON);
    "json" is the legacy free-form-JSON shape; None is the unconstrained
    paper-default. Used by the no-PDDL-tools branch to enforce per-task
    response shape so `check_success` can grade structurally instead of
    via free-text regex.

    Appends the assistant turn to *messages* so the post-call shape matches
    `chat_with_tools` (which appends internally). Lets multi-step callers
    like the chain runner reuse the same `messages` list without manually
    bookkeeping the assistant turn.
    """
    options, extra = _build_chat_kwargs(num_predict, num_ctx, temperature, think)
    if format is not None:
        extra["format"] = format
    resp = await client.chat(
        model=model,
        messages=messages,
        options=options,
        **extra,
    )
    content = resp["message"].get("content", "")
    tokens = {
        "prompt": _response_field(resp, "prompt_eval_count"),
        "completion": _response_field(resp, "eval_count"),
        "turns": 1,
        "total_duration_ns": _response_field(resp, "total_duration"),
        "eval_duration_ns": _response_field(resp, "eval_duration"),
    }
    thinking_text = _response_thinking(resp)
    messages.append({"role": "assistant", "content": content})
    return content, _response_done_reason(resp), tokens, thinking_text
