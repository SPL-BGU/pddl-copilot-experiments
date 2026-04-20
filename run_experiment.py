#!/usr/bin/env python3
"""
Reproduce experiments from:
  "Toward PDDL Planning Copilot" (Benyamin et al., 2025)
  https://arxiv.org/abs/2509.12987

Evaluates Ollama LLMs with and without MCP planning tools on 5 PDDL tasks:
  1. solve           — find a plan for a domain+problem
  2. validate_domain — check domain PDDL syntax
  3. validate_problem— check problem PDDL syntax
  4. validate_plan   — verify a plan is correct
  5. simulate        — produce a state-transition trace

Requires the pddl-copilot marketplace plugins (pddl-solver, pddl-validator).
Clone https://github.com/SPL-BGU/pddl-copilot and point --marketplace-path at it.

Usage:
  pip3 install -r requirements.txt
  python3 run_experiment.py --marketplace-path /path/to/pddl-copilot --models qwen3:0.6b qwen3:4b
  python3 run_experiment.py --marketplace-path /path/to/pddl-copilot --tasks solve validate_plan --chains
"""

import argparse
import asyncio
import json
import math
import os
import random
import re
import signal
import sys
import time
from collections import defaultdict
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, field
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DOMAINS_DIR = SCRIPT_DIR / "domains"
RESULTS_DIR = SCRIPT_DIR / "results"

REQUIRED_PLUGINS = ["pddl-solver", "pddl-validator"]


def resolve_plugin_dirs(marketplace_path: str | Path) -> list[Path]:
    """Discover plugin directories inside a pddl-copilot marketplace clone."""
    plugins_dir = Path(marketplace_path) / "plugins"
    if not plugins_dir.is_dir():
        sys.exit(f"Error: no plugins/ directory found at {marketplace_path}")
    dirs = []
    for name in REQUIRED_PLUGINS:
        p = plugins_dir / name
        if not p.is_dir():
            sys.exit(f"Error: plugin '{name}' not found at {p}")
        dirs.append(p)
    return dirs

# ---------------------------------------------------------------------------
# Defaults (from the paper)
# ---------------------------------------------------------------------------

DEFAULT_MODELS = ["qwen3:0.6b", "qwen3:4b"]
# Fallback set for the BGU shared Ollama server (cis-ollama), which does not
# host the paper's qwen3:0.6b / qwen3:4b. Used only when --ollama-host points
# at a non-localhost server AND --models was not passed explicitly. Runs
# against this set are NOT paper reproductions — label result dirs accordingly.
BGU_DEFAULT_MODELS = ["Qwen3.5:0.8B", "qwen3:latest", "gpt-oss:20b", "gemma4:31b"]
TEMPERATURE = 0.0
MAX_TOOL_LOOPS = 10
TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan", "simulate"]

# Per-task output caps. Chosen well above the longest legitimate plan/trace
# seen in the domains set but low enough that a thinking-mode spiral is cut
# off in seconds instead of minutes. Override via --num-predict.
DEFAULT_NUM_PREDICT: dict[str, int] = {
    "solve":            8192,
    "validate_domain":  1024,
    "validate_problem": 1024,
    "validate_plan":    1024,
    "simulate":         1536,
}
DEFAULT_NUM_CTX = 8192
DEFAULT_CONCURRENCY = 4

# Failure-reason vocabulary used on TaskResult.failure_reason. "ok" for success,
# the rest tag which classifier rejected the run so a human (or the summary
# table) can tell a plan-invalid from a tool-not-selected from a truncation.
FR_OK = "ok"
FR_EXCEPTION = "exception"
FR_TRUNCATED_NO_ANSWER = "truncated_no_answer"
FR_TOOL_NOT_SELECTED = "tool_not_selected"
FR_TOOL_ERROR = "tool_error"
FR_PLAN_INVALID = "plan_invalid"
FR_VERDICT_MISMATCH = "verdict_mismatch"
FR_NO_VERDICT_PARSED = "no_verdict_parsed"
FR_SIMULATE_EMPTY = "simulate_empty"
FR_RESULT_MISMATCH = "result_mismatch"
FR_UNKNOWN = "unknown"

# Per-task tool allowlists. When --tool-filter=per-task, only these tool names
# are exposed to the model for the given task, controlling for tool-selection
# noise when the connected MCP servers expose unrelated tools.
TASK_TOOLS: dict[str, list[str]] = {
    "solve":            ["classic_planner", "numeric_planner"],
    "validate_domain":  ["validate_pddl_syntax"],
    "validate_problem": ["validate_pddl_syntax"],
    "validate_plan":    ["validate_pddl_syntax"],
    "simulate":         ["get_state_transition"],
}

TOOL_FILTER_CHOICES = ("all", "per-task")
PROMPT_STYLE_CHOICES = ("minimal", "guided")

# ---------------------------------------------------------------------------
# System prompts (Section 4 of the paper)
# ---------------------------------------------------------------------------

_WITH_TOOLS_BASE = (
    "You are a PDDL planning assistant with access to planning tools. "
    "Your ONLY way to get information or solve problems is by calling the "
    "provided tools ONE AT A TIME — never guess or create plan details yourself."
)

_GUIDED_SUFFIX = (
    "\nWhen calling tools, pass the complete PDDL text from the user message "
    "(starting with '(define ...') as the 'domain' and 'problem' arguments — "
    "not file names or domain names."
)

WITH_TOOLS_SYSTEM: dict[str, str] = {
    "minimal": _WITH_TOOLS_BASE,
    "guided": _WITH_TOOLS_BASE + _GUIDED_SUFFIX,
}

WITHOUT_TOOLS_SYSTEM = (
    "You are a PDDL planning assistant. You must analyze PDDL problems, "
    "validate syntax, create plans, and simulate state transitions all on "
    "your own, without any external tools."
)

# ---------------------------------------------------------------------------
# Prompt templates — 5 variants per task (robustness, Section 4.1)
# ---------------------------------------------------------------------------

PROMPT_TEMPLATES: dict[str, list[str]] = {
    "solve": [
        "Solve the following PDDL planning problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        "Find a valid plan for this PDDL problem.\n\nDomain definition:\n{domain}\n\nProblem definition:\n{problem}",
        "Generate a plan that solves the following planning problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        "Given the PDDL domain and problem below, compute a solution plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}",
        "Please solve this automated planning task and return the plan.\n\n{domain}\n\n{problem}",
    ],
    "validate_domain": [
        "Check if this PDDL domain definition has valid syntax:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the following PDDL domain for syntactic correctness:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL domain syntactically correct? Please check.\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Analyze this domain definition and tell me if the PDDL syntax is valid:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Please verify the syntax of the following PDDL domain:\n\n{domain}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    ],
    "validate_problem": [
        "Check if this PDDL problem has valid syntax given the domain.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Validate the syntax of this PDDL problem against its domain:\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this PDDL problem file syntactically correct for the given domain?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Verify the syntax of the following PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Check the following PDDL problem for syntax errors.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    ],
    "validate_plan": [
        "Validate whether this plan is correct for the given domain and problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Check if the following plan solves the PDDL problem.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Is this plan valid for the given planning problem?\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Verify the correctness of this plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
        "Does this plan achieve the goal? Validate it.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}\n\nEnd your response with exactly one line: VERDICT: VALID or VERDICT: INVALID",
    ],
    "simulate": [
        "Simulate the execution of this plan and show the state transitions.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Trace the state changes when executing this plan step by step.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Show me the state after each action in this plan.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Execute this plan and provide the state transition trace.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
        "Walk through this plan action by action and show each intermediate state.\n\nDomain:\n{domain}\n\nProblem:\n{problem}\n\nPlan:\n{plan}",
    ],
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    model: str
    task: str
    domain_name: str
    problem_name: str
    prompt_variant: int
    with_tools: bool
    success: bool
    tool_selected: bool | None = None  # True/False for with-tools, None for no-tools
    response: str = ""
    tool_calls: list = field(default_factory=list)
    duration_s: float = 0.0
    error: str = ""
    tool_filter: str = "all"
    prompt_style: str = "minimal"
    failure_reason: str = FR_OK          # FR_* constant — "ok" iff success
    truncated: bool = False              # done_reason == "length" on any turn
    done_reason: str = ""                # raw done_reason from the last chat turn


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
    extra: dict = {}
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
) -> tuple[str, list[dict], str]:
    """Send messages to Ollama, handle tool-call loops.

    Returns (text, tool_calls_log, last_done_reason). The done_reason is taken
    from the final turn — callers use it to detect num_predict truncation
    ("length") vs. natural stop ("stop"). If `allowed_tools` is given, only
    tools with those names are exposed to the model.
    """
    tool_calls_log: list[dict] = []

    if allowed_tools is None:
        tools_payload = mcp.tools
    else:
        allowed_set = set(allowed_tools)
        tools_payload = [t for t in mcp.tools if t["function"]["name"] in allowed_set]

    options, extra = _build_chat_kwargs(num_predict, num_ctx, temperature, think)
    last_done_reason = ""

    for _ in range(max_loops):
        resp = await client.chat(
            model=model,
            messages=messages,
            tools=tools_payload,
            options=options,
            **extra,
        )
        last_done_reason = _response_done_reason(resp)
        msg = resp["message"]
        messages.append(msg)

        if not msg.get("tool_calls"):
            return msg.get("content", ""), tool_calls_log, last_done_reason

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

    # Exhausted loops — return last content
    last = messages[-1]
    text = last.get("content", "") if isinstance(last, dict) else ""
    return text, tool_calls_log, last_done_reason


async def chat_without_tools(
    client: "ollama.AsyncClient",
    model: str,
    messages: list[dict],
    num_predict: int,
    num_ctx: int,
    temperature: float = TEMPERATURE,
    think: bool | None = None,
) -> tuple[str, str]:
    """Single-turn chat without tools. Returns (text, done_reason)."""
    options, extra = _build_chat_kwargs(num_predict, num_ctx, temperature, think)
    resp = await client.chat(
        model=model,
        messages=messages,
        options=options,
        **extra,
    )
    return resp["message"].get("content", ""), _response_done_reason(resp)


# ---------------------------------------------------------------------------
# Domain / problem loading
# ---------------------------------------------------------------------------


def load_domains(domains_dir: Path) -> dict:
    """
    Load PDDL domains from:
        domains/{classical,numeric}/<name>/domain.pddl
        domains/{classical,numeric}/<name>/p*.pddl

    Returns {name: {"type": str, "domain": str, "problems": {pname: str}}}.
    """
    domains: dict = {}
    for dtype in ("classical", "numeric"):
        type_dir = domains_dir / dtype
        if not type_dir.is_dir():
            continue
        for ddir in sorted(type_dir.iterdir()):
            if not ddir.is_dir():
                continue
            domain_file = ddir / "domain.pddl"
            if not domain_file.exists():
                continue
            problems = {
                pf.stem: pf.read_text()
                for pf in sorted(ddir.glob("p*.pddl"))
            }
            if problems:
                domains[ddir.name] = {
                    "type": dtype,
                    "domain": domain_file.read_text(),
                    "problems": problems,
                }
    return domains


# ---------------------------------------------------------------------------
# Ground-truth oracle (use MCP tools as reference, Section 4.2)
# ---------------------------------------------------------------------------


def _parse_validation_verdict(raw: str) -> bool | None:
    """Parse a validate_pddl_syntax result string.

    Expects the pyvalidator shape {"valid", "status", "report", "details"}.
    Returns True if valid, False if invalid, None on error or unparseable.
    """
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("error") is True:
        return None
    if "valid" not in data:
        return None
    return bool(data["valid"])


async def generate_ground_truth(mcp: MCPPlanner, domains: dict) -> dict:
    """For each domain/problem, solve and validate using the MCP tools as oracle."""
    gt: dict = {}
    for dname, dinfo in domains.items():
        gt[dname] = {}
        planner = "classic_planner" if dinfo["type"] == "classical" else "numeric_planner"
        for pname, ppddl in dinfo["problems"].items():
            entry: dict = {
                "domain_valid": None,
                "problem_valid": None,
                "plan_valid": None,
                "solvable": False,
                "plan": None,
                "trace": None,
            }

            # Validate domain via pyvalidator
            try:
                raw = await mcp.call_tool("validate_pddl_syntax", {"domain": dinfo["domain"]})
                entry["domain_validation_raw"] = raw
                entry["domain_valid"] = _parse_validation_verdict(raw)
            except Exception as exc:
                entry["domain_validation_raw"] = str(exc)

            # Validate problem via pyvalidator
            try:
                raw = await mcp.call_tool(
                    "validate_pddl_syntax",
                    {"domain": dinfo["domain"], "problem": ppddl},
                )
                entry["problem_validation_raw"] = raw
                entry["problem_valid"] = _parse_validation_verdict(raw)
            except Exception as exc:
                entry["problem_validation_raw"] = str(exc)

            # Solve — distinguish solvable (non-empty plan) from unsolvable (empty plan)
            try:
                raw = await mcp.call_tool(planner, {"domain": dinfo["domain"], "problem": ppddl})
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict) and isinstance(data.get("plan"), list) and data["plan"]:
                    entry["plan"] = data["plan"]
                    entry["solvable"] = True
            except Exception:
                pass

            # State trace + plan-validity verdict (only if we have a plan)
            if entry["plan"]:
                plan_str = "\n".join(entry["plan"]) if isinstance(entry["plan"], list) else entry["plan"]
                try:
                    entry["trace"] = await mcp.call_tool(
                        "get_state_transition",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str},
                    )
                except Exception:
                    pass
                # Validate the oracle plan so validate_plan has a verdict
                try:
                    raw = await mcp.call_tool(
                        "validate_pddl_syntax",
                        {"domain": dinfo["domain"], "problem": ppddl, "plan": plan_str},
                    )
                    entry["plan_validation_raw"] = raw
                    entry["plan_valid"] = _parse_validation_verdict(raw)
                except Exception as exc:
                    entry["plan_validation_raw"] = str(exc)

            gt[dname][pname] = entry
            tag = "solvable" if entry["solvable"] else "unsolvable"
            print(
                f"    {dname}/{pname}: {tag} "
                f"(domain_valid={entry['domain_valid']} "
                f"problem_valid={entry['problem_valid']} "
                f"plan_valid={entry['plan_valid']})"
            )
    return gt


# ---------------------------------------------------------------------------
# Success checking (Section 4.3 — evaluation criteria)
# ---------------------------------------------------------------------------


def _used_tool(tool_calls: list[dict], name: str) -> bool:
    return any(tc["name"] == name for tc in tool_calls)


def _get_tool_results(tool_calls: list[dict], name: str) -> list[str]:
    """Return result strings from all calls to *name*."""
    return [tc["result"] for tc in tool_calls if tc["name"] == name and "result" in tc]


def _extract_plan_from_tool_result(raw: str) -> list[str]:
    """Extract plan action list from a planner tool's JSON result."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    if isinstance(data, dict) and isinstance(data.get("plan"), list):
        return data["plan"]
    return []


# Matches `(action arg1 arg2 ...)` action lines, optionally preceded by step
# numbering like "1." / "1:" or a bullet ("- ", "* "). Conservatively
# requires at least the action name as an identifier.
_ACTION_LINE_RE = re.compile(
    r"""
    ^\s*
    (?:\d+[.):]\s*|[-*]\s+)?    # optional step numbering OR bullet
    \(\s*
        ([A-Za-z][\w-]*)        # action name
        (?:\s+[\w\-?@.]+)*      # zero or more simple argument tokens
    \s*\)
    \s*$
    """,
    re.VERBOSE,
)

# Matches a VERDICT: VALID / INVALID line anywhere in the response.
_VERDICT_RE = re.compile(r"VERDICT\s*:\s*(VALID|INVALID)\b", re.IGNORECASE)


def extract_plan_lines(response: str) -> list[str]:
    """Extract `(action args...)` lines from a model response.

    Strips optional step-number prefixes and keeps one action per line. Returns
    them normalized as `"(name arg1 arg2)"` (single spaces, lowercased).
    """
    if not response:
        return []
    # Strip common code-fence markers which don't contain plan actions.
    plan: list[str] = []
    for line in response.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            continue
        m = _ACTION_LINE_RE.match(line)
        if not m:
            continue
        # Re-normalize: keep only the `(...)` part, squeeze whitespace, lowercase.
        inner = stripped
        # Drop any leading "1." / "1:" prefix
        paren_start = inner.find("(")
        if paren_start > 0:
            inner = inner[paren_start:]
        inner = " ".join(inner.split()).lower()
        plan.append(inner)
    return plan


def extract_verdict(response: str) -> bool | None:
    """Return True for VALID, False for INVALID, None if no verdict line found.

    Takes the last VERDICT: line in the response (model may discuss before it).
    """
    if not response:
        return None
    matches = _VERDICT_RE.findall(response)
    if not matches:
        return None
    return matches[-1].upper() == "VALID"


async def _validate_model_plan(
    mcp: MCPPlanner, domain_pddl: str, problem_pddl: str, plan_lines: list[str],
) -> bool | None:
    """Call validate_pddl_syntax on the model's extracted plan.

    Returns True iff pyvalidator reports valid, False if the plan is empty
    or pyvalidator reports invalid, None if the MCP transport failed or the
    tool returned an error-shape response. None lets callers distinguish a
    genuinely invalid plan (FR_PLAN_INVALID) from a validator that could
    not be reached (FR_TOOL_ERROR).
    """
    if not plan_lines:
        return False
    plan_str = "\n".join(plan_lines)
    try:
        raw = await mcp.call_tool(
            "validate_pddl_syntax",
            {"domain": domain_pddl, "problem": problem_pddl, "plan": plan_str},
        )
    except Exception:
        return None
    return _parse_validation_verdict(raw)


def _tool_error_seen(tool_calls: list[dict], name: str) -> bool:
    """True if any call to *name* failed.

    Two error shapes are recognized:
      - MCP transport errors, surfaced as strings prefixed with "Tool error".
      - Plugin-side errors, returned as JSON like {"error": true, "message": ...}.
        The pddl-solver / pddl-validator plugins use this shape for things
        like bad arguments, missing files, planner timeouts, etc.
    """
    for tc in tool_calls:
        if tc.get("name") != name:
            continue
        raw = tc.get("result", "")
        if isinstance(raw, str):
            if raw.startswith("Tool error"):
                return True
            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                continue
        else:
            parsed = raw
        if isinstance(parsed, dict) and parsed.get("error"):
            return True
    return False


async def check_success(
    task: str,
    response: str,
    tool_calls: list[dict],
    gt: dict,
    mcp: MCPPlanner,
    domain_pddl: str,
    problem_pddl: str,
    with_tools: bool,
) -> tuple[bool | None, bool, str]:
    """Decide whether a model response counts as task success.

    Returns (tool_selected, result_correct, failure_reason):
      tool_selected  — True/False for with-tools, None for no-tools.
      result_correct — end-to-end correctness of the produced artifact.
      failure_reason — FR_OK on success; one of the FR_* tags otherwise,
                       naming which classifier rejected the run.

    With-tools: check tool selection AND validate the tool result against
    ground truth (plan validity, verdict match, non-error trace).
    Without-tools: validate the actual artifact the model produced:
      - solve           → extract a plan, send it to pyvalidator, require valid==True
      - validate_*      → extract VERDICT: VALID|INVALID, compare to ground truth
      - simulate        → loose keyword check (state trace structure not graded here)
    """
    # With-tools but the model emitted zero tool calls → it answered from
    # the text alone, which is tool_not_selected regardless of how plausible
    # the text is. Without this short-circuit the per-task branches would
    # fall through to the no-tools grading path and return tool_selected=None,
    # violating the documented schema (EXPERIMENTS_FLOW.md §4.1/§9).
    if with_tools and not tool_calls:
        return False, False, FR_TOOL_NOT_SELECTED

    resp_lower = (response or "").lower()

    if task == "solve":
        if tool_calls:
            selected = _used_tool(tool_calls, "classic_planner") or _used_tool(
                tool_calls, "numeric_planner"
            )
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            planner_results = _get_tool_results(
                tool_calls, "classic_planner"
            ) + _get_tool_results(tool_calls, "numeric_planner")
            any_transport_error = False
            for raw in planner_results:
                plan_lines = _extract_plan_from_tool_result(raw)
                if not plan_lines:
                    continue
                verdict = await _validate_model_plan(
                    mcp, domain_pddl, problem_pddl, plan_lines
                )
                if verdict is True:
                    return True, True, FR_OK
                if verdict is None:
                    any_transport_error = True
            if any_transport_error or _tool_error_seen(
                tool_calls, "classic_planner"
            ) or _tool_error_seen(tool_calls, "numeric_planner"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_PLAN_INVALID
        plan_lines = extract_plan_lines(response or "")
        verdict = await _validate_model_plan(mcp, domain_pddl, problem_pddl, plan_lines)
        if verdict is True:
            return None, True, FR_OK
        if verdict is None:
            return None, False, FR_TOOL_ERROR
        return None, False, FR_PLAN_INVALID

    if task in ("validate_domain", "validate_problem", "validate_plan"):
        gt_key = {
            "validate_domain": "domain_valid",
            "validate_problem": "problem_valid",
            "validate_plan": "plan_valid",
        }[task]
        truth = gt.get(gt_key)

        if tool_calls:
            selected = _used_tool(tool_calls, "validate_pddl_syntax")
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            if truth is None:
                return True, False, FR_UNKNOWN
            # validate_pddl_syntax is polymorphic: the `valid` field answers
            # whichever layer was supplied. A {domain}-only call returns the
            # domain's verdict even when the model is graded on plan validity,
            # so the verdict check must match the call's argument shape to the
            # task — otherwise every solvable benchmark trivially scores FR_OK.
            for tc in tool_calls:
                if tc.get("name") != "validate_pddl_syntax":
                    continue
                args = tc.get("arguments", {}) or {}
                has_problem = bool(args.get("problem"))
                has_plan = bool(args.get("plan"))
                if task == "validate_domain" and (has_problem or has_plan):
                    continue
                if task == "validate_problem" and (not has_problem or has_plan):
                    continue
                if task == "validate_plan" and not has_plan:
                    continue
                verdict = _parse_validation_verdict(tc.get("result", ""))
                if verdict == truth:
                    return True, True, FR_OK
            if _tool_error_seen(tool_calls, "validate_pddl_syntax"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_VERDICT_MISMATCH

        verdict = extract_verdict(response or "")
        if verdict is None:
            return None, False, FR_NO_VERDICT_PARSED
        if truth is None:
            return None, False, FR_UNKNOWN
        if verdict == truth:
            return None, True, FR_OK
        return None, False, FR_VERDICT_MISMATCH

    if task == "simulate":
        if tool_calls:
            selected = _used_tool(tool_calls, "get_state_transition")
            if not selected:
                return False, False, FR_TOOL_NOT_SELECTED
            # `valid` in the tool response is a PDDL-syntactic check, not a
            # simulation-correctness signal — a partial trajectory with
            # valid=false would satisfy it. Compare against the oracle
            # trajectory from gt["trace"] (same plan, same plugin → dicts
            # are byte-equal when the model passed identical inputs).
            oracle_trace = gt.get("trace")
            if isinstance(oracle_trace, str):
                try:
                    oracle_trace = json.loads(oracle_trace)
                except (ValueError, TypeError):
                    oracle_trace = None
            oracle_traj = oracle_trace.get("trajectory") if isinstance(oracle_trace, dict) else None
            if oracle_traj is None:
                return True, False, FR_UNKNOWN
            for raw in _get_tool_results(tool_calls, "get_state_transition"):
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                except (ValueError, TypeError):
                    continue
                if not isinstance(parsed, dict) or parsed.get("error"):
                    continue
                if parsed.get("trajectory") == oracle_traj:
                    return True, True, FR_OK
            if _tool_error_seen(tool_calls, "get_state_transition"):
                return True, False, FR_TOOL_ERROR
            return True, False, FR_RESULT_MISMATCH
        if "state" in resp_lower and ("after" in resp_lower or "step" in resp_lower):
            return None, True, FR_OK
        return None, False, FR_SIMULATE_EMPTY

    return None, False, FR_UNKNOWN


# ---------------------------------------------------------------------------
# Single-task evaluation
# ---------------------------------------------------------------------------


# Failure reasons that should be overridden to FR_TRUNCATED_NO_ANSWER when
# the model hit its output-token cap. An "output was empty" classifier is
# misleading when the model was simply cut off mid-sentence.
_TRUNCATION_OVERRIDE_REASONS = (
    FR_PLAN_INVALID,
    FR_NO_VERDICT_PARSED,
    FR_SIMULATE_EMPTY,
    FR_UNKNOWN,
)


def _apply_truncation_override(success: bool, truncated: bool, failure_reason: str) -> str:
    """Reclassify a failure as truncated when the cap cut the model off mid-output.

    Only applies when the downstream classifier was one of the
    empty-output-looking reasons. Already-informative tags like
    FR_VERDICT_MISMATCH, FR_TOOL_ERROR, and FR_TOOL_NOT_SELECTED are
    preserved — the model had enough output for the classifier to reach a
    decision, so the truncation wasn't the proximate cause.
    """
    if success or not truncated:
        return failure_reason
    if failure_reason in _TRUNCATION_OVERRIDE_REASONS:
        return FR_TRUNCATED_NO_ANSWER
    return failure_reason


async def evaluate_one(
    client: "ollama.AsyncClient",
    model: str,
    task: str,
    domain_name: str,
    domain_pddl: str,
    problem_name: str,
    problem_pddl: str,
    prompt_variant: int,
    with_tools: bool,
    mcp: MCPPlanner,
    gt: dict,
    num_predict: int,
    num_ctx: int,
    think: bool | None,
    tool_filter: str = "all",
    prompt_style: str = "minimal",
) -> TaskResult:
    template = PROMPT_TEMPLATES[task][prompt_variant % len(PROMPT_TEMPLATES[task])]

    plan_str = ""
    if task in ("validate_plan", "simulate") and gt.get("plan"):
        plan_str = "\n".join(gt["plan"]) if isinstance(gt["plan"], list) else gt["plan"]

    prompt = template.format(domain=domain_pddl, problem=problem_pddl, plan=plan_str)
    system = WITH_TOOLS_SYSTEM[prompt_style] if with_tools else WITHOUT_TOOLS_SYSTEM
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    t0 = time.time()
    tool_calls: list[dict] = []
    error = ""
    response_text = ""
    done_reason = ""

    allowed = TASK_TOOLS.get(task) if tool_filter == "per-task" else None

    try:
        if with_tools:
            response_text, tool_calls, done_reason = await chat_with_tools(
                client, model, messages, mcp,
                num_predict=num_predict, num_ctx=num_ctx,
                allowed_tools=allowed, think=think,
            )
        else:
            response_text, done_reason = await chat_without_tools(
                client, model, messages,
                num_predict=num_predict, num_ctx=num_ctx, think=think,
            )
    except Exception as exc:
        error = str(exc)

    duration = time.time() - t0
    tool_selected: bool | None = None
    failure_reason = FR_OK
    if error:
        success = False
        failure_reason = FR_EXCEPTION
    else:
        try:
            tool_selected, success, failure_reason = await check_success(
                task, response_text, tool_calls, gt, mcp, domain_pddl, problem_pddl,
                with_tools=with_tools,
            )
        except Exception as exc:
            success = False
            error = f"scoring error: {exc}"
            failure_reason = FR_EXCEPTION

    truncated = done_reason == "length"
    failure_reason = _apply_truncation_override(success, truncated, failure_reason)

    return TaskResult(
        model=model,
        task=task,
        domain_name=domain_name,
        problem_name=problem_name,
        prompt_variant=prompt_variant,
        with_tools=with_tools,
        success=success,
        tool_selected=tool_selected,
        response=response_text[:500],
        tool_calls=tool_calls,
        duration_s=round(duration, 2),
        error=error,
        tool_filter=tool_filter,
        prompt_style=prompt_style,
        failure_reason=failure_reason,
        truncated=truncated,
        done_reason=done_reason,
    )


def _format_progress(done: int, total: int, scheduled_idx: int, r: TaskResult) -> str:
    """One-line completion log entry, safe for concurrent out-of-order prints.

    `done` is the running completion count; `scheduled_idx` is the 0-based
    enumerate order from the jobs list so the label is stable across runs.
    """
    cond = "tools" if r.with_tools else "no-tools"
    idx_width = len(str(total))
    mark = "OK" if r.success else "FAIL"
    suffix = "" if r.success else f" ({r.failure_reason})"
    return (
        f"  [{done:>{idx_width}}/{total} | {r.duration_s:>6.1f}s | #{scheduled_idx}] "
        f"{r.model} {cond} {r.task} {r.domain_name}/{r.problem_name} v{r.prompt_variant}"
        f" -> {mark}{suffix}"
    )


async def run_single_task_experiment(
    client: "ollama.AsyncClient",
    models: list[str],
    tasks: list[str],
    domains: dict,
    ground_truth: dict,
    mcp: MCPPlanner,
    num_variants: int = 5,
    tool_filter: str = "all",
    prompt_style: str = "minimal",
    num_predict_override: int | None = None,
    num_ctx: int = DEFAULT_NUM_CTX,
    think: bool | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> list[TaskResult]:
    """Run the full single-task sweep with bounded Ollama concurrency.

    Jobs are enumerated up-front so `[i/N]` numbering is stable across
    reorderings; completions are printed as they finish via
    `asyncio.as_completed`. Partial results can be collected by the caller
    on KeyboardInterrupt — remaining tasks are cancelled and whatever
    finished is returned.
    """
    # Build the full job list up-front. Skipping unsolvable validate_plan/
    # simulate is cheaper here than inside the coroutine and keeps the
    # denominator accurate.
    Job = tuple  # (model, task, dname, domain_pddl, pname, ppddl, pv, with_tools, gt, np)
    jobs: list[Job] = []
    for model in models:
        for with_tools in (True, False):
            for task in tasks:
                np_for_task = (
                    num_predict_override
                    if num_predict_override is not None
                    else DEFAULT_NUM_PREDICT[task]
                )
                for dname, dinfo in domains.items():
                    for pname, ppddl in dinfo["problems"].items():
                        gt = ground_truth.get(dname, {}).get(pname, {})
                        if task in ("validate_plan", "simulate") and not gt.get("plan"):
                            continue
                        for pv in range(num_variants):
                            jobs.append((
                                model, task, dname, dinfo["domain"],
                                pname, ppddl, pv, with_tools, gt, np_for_task,
                            ))

    total = len(jobs)
    results: list[TaskResult | None] = [None] * total
    if total == 0:
        return []

    sem = asyncio.Semaphore(max(1, concurrency))

    async def run_one(idx: int) -> tuple[int, TaskResult]:
        (
            model, task, dname, dpddl, pname, ppddl, pv,
            with_tools, gt, np_for_task,
        ) = jobs[idx]
        async with sem:
            r = await evaluate_one(
                client, model, task, dname, dpddl,
                pname, ppddl, pv, with_tools, mcp, gt,
                num_predict=np_for_task, num_ctx=num_ctx, think=think,
                tool_filter=tool_filter, prompt_style=prompt_style,
            )
            return idx, r

    aws = [asyncio.create_task(run_one(i)) for i in range(total)]
    done_count = 0
    try:
        for coro in asyncio.as_completed(aws):
            idx, r = await coro
            results[idx] = r
            done_count += 1
            print(_format_progress(done_count, total, idx, r), flush=True)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n  Cancelling pending tasks...", flush=True)
        for t in aws:
            if not t.done():
                t.cancel()
        # Drain cancellations so close paths don't hang; results already
        # written to `results[idx]` via completed futures are kept.
        await asyncio.gather(*aws, return_exceptions=True)
        raise

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Multi-task chain evaluation (Section 4.4)
# ---------------------------------------------------------------------------


async def run_chain_experiment(
    client: "ollama.AsyncClient",
    models: list[str],
    domains: dict,
    ground_truth: dict,
    mcp: MCPPlanner,
    chain_lengths: list[int] = [2, 3, 4, 5],
    samples: int = 20,
    tool_filter: str = "all",
    with_tools: bool = True,
    prompt_style: str = "minimal",
    num_predict_override: int | None = None,
    num_ctx: int = DEFAULT_NUM_CTX,
    think: bool | None = None,
) -> list[dict]:
    results: list[dict] = []
    domain_items = list(domains.items())
    system_prompt = WITH_TOOLS_SYSTEM[prompt_style] if with_tools else WITHOUT_TOOLS_SYSTEM
    cond_label = "tools" if with_tools else "no-tools"

    for model in models:
        for n in chain_lengths:
            successes = 0
            for i in range(samples):
                dname, dinfo = random.choice(domain_items)
                pname = random.choice(list(dinfo["problems"].keys()))
                ppddl = dinfo["problems"][pname]
                gt = ground_truth.get(dname, {}).get(pname, {})

                chain_tasks = random.choices(TASKS, k=n)
                messages: list[dict] = [{"role": "system", "content": system_prompt}]
                chain_ok = True

                for task in chain_tasks:
                    # Mirror the single-task guard (run_single_task_experiment,
                    # above): if the oracle never produced a plan for this
                    # problem, validate_plan/simulate have no ground truth to
                    # grade against and would deterministically fail the chain
                    # as a ground-truth-coverage artifact rather than a model
                    # signal. Skip the step and keep the chain alive.
                    if task in ("validate_plan", "simulate") and not gt.get("plan"):
                        continue
                    template = random.choice(PROMPT_TEMPLATES[task])
                    plan_str = ""
                    if task in ("validate_plan", "simulate") and gt.get("plan"):
                        plan_str = (
                            "\n".join(gt["plan"]) if isinstance(gt["plan"], list) else gt["plan"]
                        )
                    prompt = template.format(
                        domain=dinfo["domain"], problem=ppddl, plan=plan_str,
                    )
                    messages.append({"role": "user", "content": prompt})

                    np_for_task = (
                        num_predict_override
                        if num_predict_override is not None
                        else DEFAULT_NUM_PREDICT[task]
                    )
                    allowed = TASK_TOOLS.get(task) if tool_filter == "per-task" else None
                    try:
                        if with_tools:
                            resp_text, tc, _dr = await chat_with_tools(
                                client, model, messages, mcp,
                                num_predict=np_for_task, num_ctx=num_ctx,
                                allowed_tools=allowed, think=think,
                            )
                        else:
                            resp_text, _dr = await chat_without_tools(
                                client, model, messages,
                                num_predict=np_for_task, num_ctx=num_ctx, think=think,
                            )
                            tc = []
                            messages.append({"role": "assistant", "content": resp_text})
                        _sel, ok, _fr = await check_success(
                            task, resp_text, tc, gt, mcp, dinfo["domain"], ppddl,
                            with_tools=with_tools,
                        )
                        if not ok:
                            chain_ok = False
                            break
                    except Exception:
                        chain_ok = False
                        break

                if chain_ok:
                    successes += 1
                mark = "OK" if chain_ok else "FAIL"
                print(f"  {model}|{cond_label} chain={n} [{i+1}/{samples}] {mark}")

            results.append({
                "model": model,
                "with_tools": with_tools,
                "chain_length": n,
                "samples": samples,
                "successes": successes,
                "success_rate": round(successes / samples, 2),
                "tool_filter": tool_filter,
                "prompt_style": prompt_style,
            })
    return results


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    phat = successes / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    half = (z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def summarize_single_task(results: list[TaskResult]) -> list[dict]:
    """Aggregate single-task results into long-format rows with N and 95% CIs.

    For the "tools" condition, also reports tool_selected count/rate — how often
    the model called the correct MCP tool, independently of result correctness.
    Each row also carries `truncated` (count where done_reason=="length") and
    a `failure_reasons: {reason: count}` dict so the notebook can plot
    failure-mode breakdowns without reparsing the raw JSON.
    """
    def _new_agg() -> dict:
        return {
            "total": 0,
            "success": 0,
            "tool_selected": 0,
            "truncated": 0,
            "failure_reasons": defaultdict(int),
        }

    agg: dict = defaultdict(_new_agg)
    for r in results:
        cond = "tools" if r.with_tools else "no-tools"
        key = (r.model, cond, r.task)
        agg[key]["total"] += 1
        if r.success:
            agg[key]["success"] += 1
        if r.tool_selected:
            agg[key]["tool_selected"] += 1
        if r.truncated:
            agg[key]["truncated"] += 1
        agg[key]["failure_reasons"][r.failure_reason] += 1

    models = sorted(set(r.model for r in results))
    tasks_present = [t for t in TASKS if any(r.task == t for r in results)]

    rows: list[dict] = []
    for model in models:
        for cond in ("tools", "no-tools"):
            for task in tasks_present:
                d = agg[(model, cond, task)]
                n = d["total"]
                s = d["success"]
                rate = s / n if n > 0 else 0.0
                lo, hi = wilson_ci(s, n)
                row: dict = {
                    "model": model,
                    "condition": cond,
                    "task": task,
                    "successes": s,
                    "n": n,
                    "success_rate": round(rate, 4),
                    "ci_lo": round(lo, 4),
                    "ci_hi": round(hi, 4),
                    "truncated": d["truncated"],
                    "failure_reasons": dict(d["failure_reasons"]),
                }
                if cond == "tools":
                    ts = d["tool_selected"]
                    ts_rate = ts / n if n > 0 else 0.0
                    ts_lo, ts_hi = wilson_ci(ts, n)
                    row["tool_selected"] = ts
                    row["tool_selected_rate"] = round(ts_rate, 4)
                    row["tool_selected_ci_lo"] = round(ts_lo, 4)
                    row["tool_selected_ci_hi"] = round(ts_hi, 4)
                rows.append(row)
    return rows


def print_fail_reasons_table(results: list[TaskResult]):
    """Per (model, condition, task) breakdown of the top failure reasons.

    Complements the success-rate table by answering "why did the failures
    fail?" at a glance — counts the top 3 FR_* tags per cell plus a
    truncation count.
    """
    rows = summarize_single_task(results)
    if not rows:
        return

    header = (
        f"{'Model':<20} {'Condition':<9} {'Task':<18} "
        f"{'N':>4}  {'Fails':>5}  {'Trunc':>5}  Top failure reasons"
    )
    bar = "=" * max(len(header), 92)
    print("\n" + bar)
    print("FAIL REASONS BY (model, condition, task)")
    print(bar)
    print(header)
    print("-" * len(bar))
    for r in rows:
        n = r["n"]
        fails = n - r["successes"]
        reasons = {k: v for k, v in r["failure_reasons"].items() if k != FR_OK}
        top = sorted(reasons.items(), key=lambda kv: -kv[1])[:3]
        top_str = ", ".join(f"{k}:{v}" for k, v in top) if top else "-"
        print(
            f"{r['model']:<20} {r['condition']:<9} {r['task']:<18} "
            f"{n:>4}  {fails:>5}  {r['truncated']:>5}  {top_str}"
        )
    print(bar)


def print_single_task_table(results: list[TaskResult]):
    """Long-format table with success rate, N, and Wilson 95% CI."""
    rows = summarize_single_task(results)
    if not rows:
        return

    header = (
        f"{'Model':<20} {'Condition':<9} {'Task':<18} "
        f"{'Rate':>6}  {'N':>4}  {'95% CI':<16}  {'ToolSel':>7}"
    )
    bar = "=" * len(header)
    print("\n" + bar)
    print("SINGLE-TASK SUCCESS RATES (with Wilson 95% CI)")
    print(bar)
    print(header)
    print("-" * len(header))
    for r in rows:
        ci_str = f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}]"
        ts_str = f"{r['tool_selected_rate']:.2f}" if "tool_selected_rate" in r else "   -"
        print(
            f"{r['model']:<20} {r['condition']:<9} {r['task']:<18} "
            f"{r['success_rate']:>6.2f}  {r['n']:>4}  {ci_str:<16}  {ts_str:>7}"
        )
    print(bar)


def summarize_chains(chain_results: list[dict]) -> list[dict]:
    """Attach Wilson CI to each chain result row."""
    rows: list[dict] = []
    for r in chain_results:
        lo, hi = wilson_ci(r["successes"], r["samples"])
        rows.append({**r, "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})
    return rows


def print_chain_table(chain_results: list[dict]):
    if not chain_results:
        return
    rows = summarize_chains(chain_results)
    header = f"{'Model':<20} {'Condition':<9} {'Chain n':>7}  {'Rate':>6}  {'N':>4}  {'95% CI':<16}"
    bar = "=" * len(header)
    print("\n" + bar)
    print("MULTI-TASK CHAIN SUCCESS RATES (with Wilson 95% CI)")
    print(bar)
    print(header)
    print("-" * len(header))
    # Sort by (model, with_tools desc so tools comes first, chain_length)
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["model"], not r.get("with_tools", True), r["chain_length"]),
    )
    for r in rows_sorted:
        cond = "tools" if r.get("with_tools", True) else "no-tools"
        ci_str = f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}]"
        print(
            f"{r['model']:<20} {cond:<9} {r['chain_length']:>7}  "
            f"{r['success_rate']:>6.2f}  {r['samples']:>4}  {ci_str:<16}"
        )
    print(bar)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


def save_results(
    single: list[TaskResult],
    chains: list[dict],
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    p1 = output_dir / f"single_task_{ts}.json"
    p1.write_text(json.dumps([asdict(r) for r in single], indent=2))
    print(f"\nSaved single-task results -> {p1}")

    if chains:
        p2 = output_dir / f"chain_{ts}.json"
        p2.write_text(json.dumps(chains, indent=2))
        print(f"Saved chain results       -> {p2}")

    # Aggregated summary with N and Wilson 95% CIs for downstream analysis.
    summary = {
        "single_task": summarize_single_task(single) if single else [],
        "chains": summarize_chains(chains) if chains else [],
    }
    p3 = output_dir / f"summary_{ts}.json"
    p3.write_text(json.dumps(summary, indent=2))
    print(f"Saved summary              -> {p3}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def async_main(args):
    # Resolve the think-mode override once. "default" → None → don't pass
    # the kwarg, preserving the model's default (= paper reproduction).
    think_override: bool | None
    if args.think == "on":
        think_override = True
    elif args.think == "off":
        think_override = False
    else:
        think_override = None

    # "Remote" = any non-localhost host. Controls default-model fallback and
    # is surfaced in the startup banner so result files can't be confused
    # with local runs.
    host = args.ollama_host or ""
    is_remote = bool(host) and not any(
        tok in host for tok in ("localhost", "127.0.0.1", "[::1]")
    )
    if args.models is None:
        args.models = list(BGU_DEFAULT_MODELS if is_remote else DEFAULT_MODELS)

    num_parallel_env = os.environ.get("OLLAMA_NUM_PARALLEL", "unset")

    print("=" * 60)
    print("PDDL Planning Copilot — Experiment Runner")
    print("Reproducing: Benyamin et al., 2025 (arXiv:2509.12987)")
    print("=" * 60)
    print(f"  Marketplace:{args.marketplace_path}")
    print(f"  Models:     {args.models}")
    print(f"  Tasks:      {args.tasks}")
    print(f"  Domains:    {args.domains_dir}")
    print(f"  Variants:   {args.num_variants}")
    print(f"  Temperature:{args.temperature}")
    print(f"  Tool filter:{args.tool_filter}")
    print(f"  Prompt:     {args.prompt_style}")
    print(f"  num_predict:{args.num_predict if args.num_predict is not None else 'per-task defaults'}")
    print(f"  num_ctx:    {args.num_ctx}")
    print(f"  think:      {args.think}")
    print(f"  Concurrency:{args.concurrency} (OLLAMA_NUM_PARALLEL={num_parallel_env})")
    if args.concurrency > 1 and num_parallel_env == "unset" and not is_remote:
        print("  WARNING: OLLAMA_NUM_PARALLEL is not set — Ollama may queue "
              "concurrent requests server-side, negating the speedup. "
              "Export OLLAMA_NUM_PARALLEL>=concurrency before the run.")
    print(f"  Ollama host:{host or '(library default: http://localhost:11434)'}"
          f"{' [remote, tls_verify=' + ('off' if args.ollama_insecure else 'on') + ']' if is_remote else ''}")

    # Resolve plugins
    plugin_dirs = resolve_plugin_dirs(args.marketplace_path)

    # Load domains
    domains = load_domains(Path(args.domains_dir))
    if not domains:
        sys.exit(f"No domains found in {args.domains_dir}")
    n_problems = sum(len(d["problems"]) for d in domains.values())
    print(f"\n  Loaded {len(domains)} domains, {n_problems} problems total")
    for dname, dinfo in domains.items():
        print(f"    {dname} ({dinfo['type']}): {len(dinfo['problems'])} problems")

    # Connect MCP
    print("\nConnecting to MCP servers...")
    mcp = MCPPlanner()
    await mcp.connect(plugin_dirs)

    # Validate TASK_TOOLS against actual MCP tools (catch typos early)
    available_tools = {t["function"]["name"] for t in mcp.tools}
    for task, allowed in TASK_TOOLS.items():
        missing = set(allowed) - available_tools
        if missing:
            sys.exit(f"TASK_TOOLS['{task}'] references unknown tools: {missing}")

    # Unknown kwargs (verify=...) are forwarded by ollama.AsyncClient to its
    # underlying httpx.AsyncClient — lets us tolerate the BGU server's
    # self-signed cert without patching the ollama library.
    client_kwargs: dict = {}
    if args.ollama_host:
        client_kwargs["host"] = args.ollama_host
    if args.ollama_insecure:
        client_kwargs["verify"] = False
    client = ollama.AsyncClient(**client_kwargs)

    single_results: list[TaskResult] = []
    chain_results: list[dict] = []
    try:
        # Ground truth
        print("\nGenerating ground truth (solving all problems with planners)...")
        ground_truth = await generate_ground_truth(mcp, domains)

        # Single-task
        print("\n--- Single-Task Evaluation ---")
        single_results = await run_single_task_experiment(
            client=client,
            models=args.models,
            tasks=args.tasks,
            domains=domains,
            ground_truth=ground_truth,
            mcp=mcp,
            num_variants=args.num_variants,
            tool_filter=args.tool_filter,
            prompt_style=args.prompt_style,
            num_predict_override=args.num_predict,
            num_ctx=args.num_ctx,
            think=think_override,
            concurrency=args.concurrency,
        )
        print_single_task_table(single_results)
        print_fail_reasons_table(single_results)

        # Multi-task chains
        if args.chains:
            print("\n--- Multi-Task Chain Evaluation ---")
            for cond_with_tools in (True, False):
                print(f"\n  Condition: {'tools' if cond_with_tools else 'no-tools'}")
                chain_results += await run_chain_experiment(
                    client=client,
                    models=args.models,
                    domains=domains,
                    ground_truth=ground_truth,
                    mcp=mcp,
                    chain_lengths=[2, 3, 4, 5],
                    samples=args.chain_samples,
                    tool_filter=args.tool_filter,
                    with_tools=cond_with_tools,
                    prompt_style=args.prompt_style,
                    num_predict_override=args.num_predict,
                    num_ctx=args.num_ctx,
                    think=think_override,
                )
            print_chain_table(chain_results)

    except KeyboardInterrupt:
        print("\n\nInterrupted — saving partial results...")

    finally:
        if single_results:
            save_results(single_results, chain_results, Path(args.output_dir))
        await mcp.close()
        # ollama.AsyncClient wraps an httpx.AsyncClient; close it to release
        # connections cleanly. Guarded because some builds expose
        # aclose/close differently.
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close is not None:
            try:
                await close()
            except Exception:
                pass


def main():
    p = argparse.ArgumentParser(
        description="Reproduce PDDL Planning Copilot experiments (arXiv:2509.12987)",
    )
    p.add_argument("--marketplace-path",
                   default=os.environ.get("PDDL_MARKETPLACE_PATH"),
                   required="PDDL_MARKETPLACE_PATH" not in os.environ,
                   help="Path to cloned pddl-copilot marketplace repo (or set PDDL_MARKETPLACE_PATH)")
    p.add_argument("--models", nargs="+", default=None,
                   help="Ollama model names to evaluate. Default: paper set "
                        f"{DEFAULT_MODELS} when using localhost; BGU set "
                        f"{BGU_DEFAULT_MODELS} when --ollama-host is non-localhost.")
    p.add_argument("--tasks", nargs="+", default=TASKS, choices=TASKS,
                   help="Tasks to evaluate")
    p.add_argument("--domains-dir", default=str(DOMAINS_DIR),
                   help="Path to domains directory")
    p.add_argument("--output-dir", default=str(RESULTS_DIR),
                   help="Path to save result JSON files")
    p.add_argument("--num-variants", type=int, default=5,
                   help="Prompt variants per task (paper uses 5)")
    p.add_argument("--temperature", type=float, default=TEMPERATURE,
                   help="LLM sampling temperature (paper uses 0)")
    p.add_argument("--tool-filter", choices=list(TOOL_FILTER_CHOICES), default="all",
                   help="'all' exposes every connected MCP tool every turn (reproduces paper). "
                        "'per-task' restricts tools per task via TASK_TOOLS allowlist, reducing "
                        "tool-selection noise from unrelated tools.")
    p.add_argument("--prompt-style", choices=list(PROMPT_STYLE_CHOICES), default="minimal",
                   help="'minimal' uses the original system prompt (reproduces paper). "
                        "'guided' adds a one-sentence hint about passing full PDDL content "
                        "as tool arguments instead of file names.")
    p.add_argument("--num-predict", type=int, default=None,
                   help="Override max output tokens per chat turn for ALL tasks. "
                        "Default: per-task caps (solve=8192, simulate=1536, validate_*=1024). "
                        "Caps the qwen3 thinking-mode spiral that stalls runs for ~4 minutes.")
    p.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX,
                   help=f"Ollama context window tokens. Default {DEFAULT_NUM_CTX}.")
    p.add_argument("--think", choices=("on", "off", "default"), default="default",
                   help="Override qwen3/DeepSeek thinking mode. 'default' leaves the "
                        "model's default behaviour (reproduces paper). 'off' passes "
                        "think=False, 'on' passes think=True. Ablation only — do NOT "
                        "mix with reproduction runs.")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                   help=f"Max concurrent Ollama chat requests during the single-task "
                        f"sweep. Default {DEFAULT_CONCURRENCY}. Pair with "
                        f"OLLAMA_NUM_PARALLEL>=concurrency on the server.")
    p.add_argument("--ollama-host",
                   default=os.environ.get("OLLAMA_HOST"),
                   help="Ollama base URL. Default: library default "
                        "(http://localhost:11434). Example BGU shared server "
                        "(VPN-only): https://cis-ollama.auth.ad.bgu.ac.il")
    p.add_argument("--ollama-insecure", action="store_true",
                   default=os.environ.get("OLLAMA_INSECURE", "").lower()
                           in ("1", "true", "yes"),
                   help="Disable TLS verification (needed for the BGU "
                        "server's self-signed cert).")
    p.add_argument("--chains", action="store_true",
                   help="Also run multi-task chain evaluation")
    p.add_argument("--chain-samples", type=int, default=20,
                   help="Samples per chain length")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for chain sampling")
    args = p.parse_args()

    # Route SIGTERM through the same path as Ctrl-C so a `kill` from
    # run_background.sh triggers the KeyboardInterrupt cleanup branch in
    # async_main (which tears down MCP subprocesses via AsyncExitStack).
    # Without this, SIGTERM bypasses `finally` and MCP servers orphan.
    signal.signal(signal.SIGTERM, signal.default_int_handler)

    random.seed(args.seed)
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
