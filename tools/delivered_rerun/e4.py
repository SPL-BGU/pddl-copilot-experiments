"""E4 failure categories for "correct tool result, wrong delivered answer".

Prereg §4 E4: the fixed categories of `reanalysis_transcripts.md` Q1
(no final answer, tool-input error, summary only, abridged, wrong wrapper,
numeric omitted, wrong facts) plus "refused or clipped final request".

Q1 (tools/reanalysis/q1_budget_probe_residual.py, branch
docs/reanalysis-and-rerun-prereg) defined the categories on simulate only.
This module ports its mechanical rules and extends them to solve and the
validate tasks only where the rule is mechanical. Whatever cannot be decided
by a fixed rule is NEEDS_READING, never guessed:

  simulate   a non-JSON answer (Q1's loose markdown/table reader decided
             WRONG_WRAPPER vs SUMMARY_ONLY vs change-list ABRIDGED by
             heuristics; not ported) -> NEEDS_READING, except Q1's
             mechanical "JSON block with '...'" ABRIDGED rule, which is kept.
  validate   a non-empty answer with no parseable verdict -> NEEDS_READING
             (does the prose end in a verdict, and is it right: §6 says read).
  solve      no plan extracted and only some of the tool plan's actions
             appear in the text -> NEEDS_READING.

Decision order (first match wins) is fixed and identical for every task.
"""
from __future__ import annotations

import re

from pddl_eval.scoring import (
    _canon_atom,
    _normalize_trajectory,
    _safe_json_loads,
    strip_leaked_channel_prefix,
)
from tools.e2e_regrade import _FENCED_BLOCK_RE, oracle_canon_for, simulate_candidates

from .grade import Delivered
from .schema import Row, SchemaError

REFUSED_OR_CLIPPED_FINAL = "REFUSED_OR_CLIPPED_FINAL"
NO_FINAL_ANSWER = "NO_FINAL_ANSWER"
TOOL_INPUT_ERROR = "TOOL_INPUT_ERROR"
SUMMARY_ONLY = "SUMMARY_ONLY"
ABRIDGED = "ABRIDGED"
WRONG_WRAPPER = "WRONG_WRAPPER"
NUMERIC_OMITTED = "NUMERIC_OMITTED"
WRONG_FACTS = "WRONG_FACTS"
NEEDS_READING = "NEEDS_READING"
CATS = (REFUSED_OR_CLIPPED_FINAL, NO_FINAL_ANSWER, TOOL_INPUT_ERROR, SUMMARY_ONLY,
        ABRIDGED, WRONG_WRAPPER, NUMERIC_OMITTED, WRONG_FACTS, NEEDS_READING)

PLANNERS = ("classic_planner", "numeric_planner")
# Q1 placeholder pattern (verbatim).
_PLACEHOLDER_RE = re.compile(r"\.\.\.|…|\bsame\b|\bunchanged\b|\ball other\b|\ball static\b",
                             re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-z0-9_\-]+")


def _norm_action(a: str) -> str:
    return " ".join(str(a).split()).lower()


# ------------------------------------------------------------------ simulate
def _last_tool_trajectory(row: Row):
    """Normalised trajectory of the LAST non-error get_state_transition (Q1)."""
    best = None
    for tc in row.tool_calls:
        if tc.name != "get_state_transition":
            continue
        p = _safe_json_loads(tc.result)
        if isinstance(p, dict) and not p.get("error"):
            t = _normalize_trajectory(p.get("trajectory"))
            if t is not None:
                best = t
    return best


def _compare(model: list[dict], oracle: list[dict]) -> dict:
    """Q1 `compare`, the fields its category rules read."""
    n = min(len(model), len(oracle))
    d = dict(steps_model=len(model), steps_oracle=len(oracle), action_bad=0,
             bool_bad_steps=0, placeholder_atoms=0, num_missing=0, num_wrong=0,
             num_extra=0)
    missing: set = set()
    extra: set = set()
    for i in range(n):
        m, o = model[i], oracle[i]
        if m["action"] != o["action"]:
            d["action_bad"] += 1
        mb, ob = set(m["boolean"]), set(o["boolean"])
        d["placeholder_atoms"] += sum(1 for a in mb if _PLACEHOLDER_RE.search(a))
        if mb != ob:
            d["bool_bad_steps"] += 1
        for k, v in o["numeric"].items():
            if k not in m["numeric"]:
                missing.add(k)
            elif m["numeric"][k] != v:
                d["num_wrong"] += 1
        extra |= set(m["numeric"]) - set(o["numeric"])
    d["num_missing"], d["num_extra"] = len(missing), len(extra)
    return d


def _loose_json_lines(resp: str):
    """Q1: several JSON step objects in one fenced block, one per line."""
    steps = []
    for block in _FENCED_BLOCK_RE.findall(resp):
        for ln in block.splitlines():
            ln = ln.strip().rstrip(",")
            if not ln.startswith("{"):
                continue
            obj = _safe_json_loads(ln)
            if isinstance(obj, dict) and "step" in obj:
                steps.append(obj)
    if not steps:
        return None
    return _normalize_trajectory(steps)


def _simulate(row: Row, gt_cache: dict) -> tuple[str, str]:
    oracle = oracle_canon_for(gt_cache, {"domain_name": row.domain,
                                         "problem_name": row.problem})
    if oracle is None:
        raise SchemaError(f"no oracle trajectory for {row.domain}/{row.problem}")
    tool = _last_tool_trajectory(row)
    if tool is None or tool != oracle:
        return TOOL_INPUT_ERROR, "last tool trajectory is not the oracle's"
    resp = row.response
    cands = [(s, m) for s, m in simulate_candidates(resp)
             if _normalize_trajectory(s) is not None]
    if cands:
        steps, _mode = max(cands, key=lambda g: len(g[0]))
        d = _compare(_normalize_trajectory(steps), oracle)
        if d["steps_model"] < d["steps_oracle"]:
            return ABRIDGED, "steps skipped"
        if d["placeholder_atoms"]:
            return ABRIDGED, "state replaced by a placeholder"
        clean = not (d["action_bad"] or d["bool_bad_steps"] or d["num_wrong"]
                     or d["num_extra"])
        if clean and d["num_missing"]:
            return NUMERIC_OMITTED, f"{d['num_missing']} numeric fluents left out"
        return WRONG_FACTS, "gradeable JSON whose facts differ from the tool's"
    blocks = _FENCED_BLOCK_RE.findall(resp)
    json_like = [b for b in blocks if b.lstrip().startswith(("[", "{")) and '"step"' in b]
    if json_like and any(_PLACEHOLDER_RE.search(b) for b in json_like) \
            and _loose_json_lines(resp) is None:
        return ABRIDGED, "steps skipped (the '...' also breaks the JSON)"
    return NEEDS_READING, "no gradeable JSON; wrapper vs summary vs change-list"


# ------------------------------------------------------------------ solve
def _last_tool_plan(row: Row) -> tuple[str, ...]:
    plan: tuple[str, ...] = ()
    for tc in row.tool_calls:
        if tc.name not in PLANNERS:
            continue
        p = _safe_json_loads(tc.result)
        if isinstance(p, dict) and isinstance(p.get("plan"), list) and p["plan"]:
            plan = tuple(_norm_action(a) for a in p["plan"])
    return plan


def _is_subsequence(short: tuple, long: tuple) -> bool:
    it = iter(long)
    return all(any(x == y for y in it) for x in short)


def _solve(row: Row, dlv: Delivered) -> tuple[str, str]:
    tool = _last_tool_plan(row)
    if not tool:
        return NEEDS_READING, "no planner plan in the tool calls"
    if dlv.plan:
        plan = tuple(_norm_action(a) for a in dlv.plan)
        if plan == tool:
            return TOOL_INPUT_ERROR, "answer repeats the last tool plan, which is invalid"
        if len(plan) < len(tool) and _is_subsequence(plan, tool):
            return ABRIDGED, f"{len(plan)} of {len(tool)} tool actions restated"
        return WRONG_FACTS, "plan differs from the tool's plan"
    text = " " + " ".join(_TOKEN_RE.findall(strip_leaked_channel_prefix(row.response).lower())) + " "
    found = sum(1 for a in tool if " " + " ".join(_TOKEN_RE.findall(a)) + " " in text)
    if found == len(tool):
        return WRONG_WRAPPER, "every tool action is in the text, none extractable"
    if found == 0:
        return SUMMARY_ONLY, "no tool action restated"
    return NEEDS_READING, f"{found} of {len(tool)} tool actions in unextractable text"


# ------------------------------------------------------------------ entry
def classify(row: Row, dlv: Delivered, gt_cache: dict) -> tuple[str, str]:
    """Category and sub-label of one E4 row (tool-verified, delivered wrong)."""
    if not (row.success is True and dlv.ok is False):
        raise SchemaError("E4 classifies only tool-verified rows delivered wrong")
    if row.no_room:
        return REFUSED_OR_CLIPPED_FINAL, "final turn refused: prompt filled the window"
    if row.tokens.ctx_clip_last_turn_max_tokens is not None and row.done_reason == "length":
        return REFUSED_OR_CLIPPED_FINAL, "final turn ran out of a clipped allowance"
    if not strip_leaked_channel_prefix(row.response).strip():
        return NO_FINAL_ANSWER, f"done_reason={row.done_reason}"
    if row.task == "simulate":
        return _simulate(row, gt_cache)
    if row.task == "solve":
        return _solve(row, dlv)
    if dlv.reason == "verdict_stated_wrong":
        return WRONG_FACTS, "stated verdict contradicts the tool's"
    if dlv.reason == "no_verdict_stated":
        return NEEDS_READING, "no parseable verdict in a non-empty answer"
    raise SchemaError(f"unhandled E4 case {row.task}/{dlv.reason}")
