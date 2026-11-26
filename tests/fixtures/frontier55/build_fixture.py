#!/usr/bin/env python3
"""Build the synthetic fixture of the Claude-run analysis (freeze gate 4).

    python3 tests/fixtures/frontier55/build_fixture.py [OUT_DIR]

Writes (default: this directory) SYNTHETIC_FIXTURE, design.json, gt_cache.json,
plan_verdicts.json (the stored verdicts the validator route is checked against),
route/plan_verdicts.json (the injected validator route), domains/<track>/<domain>/ (the
tracks RQ2 needs) and frontier55/<model>_<arm>/{trials.jsonl, trial_meta.jsonl,
run_manifest.json} for the two models and the two arms, with batches.json in the two
no-tools folders.

Everything is synthetic: 20 invented domains d01..d20 (d01 to d10 classical, d11 to d20
numeric), one plan and one trace for all of them. No row of any real corpus is read or
copied; in particular nothing under results/ is opened. The rows and sidecar lines are
written by hand in the shape tools/frontier55/runner.py writes (make_row, make_meta,
turn_record); tests/test_frontier55_analysis.py checks that shape against rows built by
the runner's own functions, rebuilds this fixture into a temp dir and checks the committed
files are byte-identical.

Layout: 300 rows per folder, 60 per task: three trials per domain and task, in three
"slots". d01 to d18 hold one slot per wording; d19 and d20 are laid out so that a pairing
key without the problem (solve, simulate, validate_domain, validate_problem) or without
the plan label (validate_plan) would collide. Each wording has 20 rows per task.

    task               d01..d18                    d19                         d20
    solve, simulate    p01@11 p01@12 p01@13        p01@11 p02@11 p01@12        p02@12 p01@13 p02@13
    validate_domain    p01@11 neg@12 p01@13        p01@11 neg@11 p01@12        neg@12 p01@13 neg@13
    validate_problem   p01@11 n01@12 n01@13        p01@11 n01@11 p01@12        n01@12 p01@13 n01@13
    validate_plan      v1@11 b1@12 v2@13           v1@11 b1@11 v1@12           b1@12 v1@13 b1@13
    (neg = the broken domain `domain_neg`; validate_plan is on p01)

Default trial: right. No tools: the answer alone. Tools: the right tool is called once,
returns the right result, and the final answer is right. The planted deviations are PLANTS
below; the hand-computed consequences are in the test file.
"""
from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from pddl_eval import control_prompts as CP  # noqa: E402
from pddl_eval.runner import build_messages  # noqa: E402


def _load(name: str, path: Path):
    """The fixture builders are all called build_fixture.py; load by path under a name."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


CBF = _load("control_prompt_fix_build_fixture",
            HERE.parent / "control_prompt_fix" / "build_fixture.py")

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
MODELS = (HAIKU, SONNET)
RETURNED_ID = {HAIKU: "claude-haiku-5-5", SONNET: "claude-sonnet-5-5-20261120"}
ARMS = ("no-tools", "tools")
N, T = ARMS
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
WORDINGS = (11, 12, 13)
DOMAINS = tuple(f"d{i:02d}" for i in range(1, 21))
CLASSICAL, NUMERIC = DOMAINS[:10], DOMAINS[10:]
CAP = {"solve": 8192, "validate_domain": 6144, "validate_problem": 6144,
       "validate_plan": 6144, "simulate": 6144}
SETTINGS = {HAIKU: {"thinking": {"type": "disabled"}, "effort": "medium"},
            SONNET: {"thinking": {"type": "between_tools"}, "effort": "high"}}
STORAGE_CAP = 65_536
RUN = "frontier55"
SDK, API_VERSION = "0.109.2", "2023-06-01"
IN_TOK, OUT_TOK = 1000, 10          # per request, unless a plant says otherwise
NOTE_TOK, OVERFLOW_NOTE_TOK = 3, 7  # thinking tokens of a note
# The days. Haiku: batch and tool arm on one UTC date. Sonnet: the batch ended the next
# day, and three tool trials were requested on the next day (LATER below).
DAY = {HAIKU: "2026-11-26", SONNET: "2026-11-27"}
NEXT_DAY = {HAIKU: "2026-11-27", SONNET: "2026-11-28"}
BATCH_ID = {HAIKU: "msgbatch_fixture_haiku", SONNET: "msgbatch_fixture_sonnet"}
# The batches of a no-tools folder, in the order sent: (requests, succeeded, errored,
# expired, hour sent on the model's day, time ended). Haiku: one batch. Sonnet: five items
# of the first batch failed; the retry batch answered two of them; a third batch answered
# the last three (3 of 300 rows: exactly 1%, the most the registration allows).
BATCHES = {
    HAIKU: ((300, 300, 0, 0, 7, "2026-11-26T07:40:00+00:00"),),
    SONNET: ((300, 295, 3, 2, 7, "2026-11-28T01:00:00+00:00"),
             (5, 2, 3, 0, 9, "2026-11-27T10:00:00+00:00"),
             (3, 3, 0, 0, 11, "2026-11-27T12:00:00+00:00")),
}
# Which no-tools trials of Sonnet got their row from the second and from the third batch.
BATCH_OF = {(SONNET, "validate_problem", "d10", 0): 2, (SONNET, "validate_problem", "d10", 1): 2,
            (SONNET, "validate_problem", "d11", 0): 3, (SONNET, "validate_problem", "d11", 1): 3,
            (SONNET, "validate_problem", "d11", 2): 3}


def batch_id(model: str, n: int) -> str:
    return BATCH_ID[model] if n == 1 else f"{BATCH_ID[model]}_{n}"
TOOLS_COMMIT = "5e4f9c0" + "0" * 33     # a full commit id that starts with the registered one
TOOLS_SHA256 = "dd14507890d38a8a3c581971a699037b39a3a0bd9374d5801072fb58b9b14400"


# ------------------------------------------------------------------ layout
def slots(task: str, dom: str) -> tuple:
    """The three trials (problem, plan label, wording) of a domain on a task."""
    if task in ("solve", "simulate"):
        a, b = ("p01", ""), ("p02", "")
    elif task == "validate_domain":
        a, b = ("p01", ""), ("domain_neg", "")
    elif task == "validate_problem":
        a, b = ("p01", ""), ("n01", "")
    else:
        a, b = ("p01", "v1"), ("p01", "b1")
    if dom == "d19":
        return ((*a, 11), (*b, 11), (*a, 12))
    if dom == "d20":
        return ((*b, 12), (*a, 13), (*b, 13))
    if task in ("solve", "simulate"):
        return ((*a, 11), (*a, 12), (*a, 13))
    if task == "validate_domain":
        return ((*a, 11), (*b, 12), (*a, 13))
    if task == "validate_problem":
        return ((*a, 11), (*b, 12), (*b, 13))
    return ((*a, 11), (*b, 12), ("p01", "v2", 13))


def truth(task: str, prob: str, label: str) -> bool:
    if task == "validate_domain":
        return prob != "domain_neg"
    if task == "validate_problem":
        return not prob.startswith("n")
    return label.startswith("v")


PROBLEMS = tuple((d, p) for d in DOMAINS
                 for p in sorted({s[0] for s in slots("solve", d)}))

# ------------------------------------------------------------------ answers and references
PLAN, WRONG, CAPS, TRIED = CBF.PLAN, CBF.WRONG, CBF.CAPS, CBF.TRIED
TRAJ, ORACLE = CBF.TRAJ, CBF.ORACLE
FENCE = "```"
REF_LONG = [f"(go l{i} l{i + 1})" for i in range(1, 7)] + ["(stop r)"]
TRACE = json.dumps({"valid": True, "trajectory": ORACLE})
PROSE = "I am still thinking about where the robot should go next. "
ANSWERS = {
    **CBF.ANSWERS,
    # The whole answer is one JSON object with the plan in capitals and no code block: the
    # rerun's reader takes it as written (invalid on release 0.1.5); in lower case it is
    # the valid plan.
    "caps_json": json.dumps({"plan": CAPS}),
    # A tried step as an action line, then the final plan in a closed code block. The
    # rerun's reader takes all three action lines (invalid); the last block is the plan.
    "tried_then_block": ("(go l1 l3)\nNo, that fails.\n" + FENCE + "\n" + "\n".join(PLAN)
                         + "\n" + FENCE),
    # Longer than the storage cap: 70,000 characters of prose, then the plan in a code
    # block. The first 65,536 characters hold no plan at all.
    "cut_plan": (PROSE * 1300)[:70_000] + "\n" + FENCE + "\n" + "\n".join(PLAN) + "\n" + FENCE,
    "no_verdict": "The input looks fine to me.",
}
# Answers the harness's own online grader would count right (the stored grade of a
# no-tools row; no reading uses it).
STORED_OK = {"right", "lines_block", "trace", "ok"}


def answer(kind: str, task: str, prob: str, label: str) -> str:
    if kind in ("ok", "wrong"):
        says = truth(task, prob, label) is (kind == "ok")
        return f"I checked the input.\nVERDICT: {'VALID' if says else 'INVALID'}"
    return "" if kind == "" else ANSWERS[kind]


def ref_plan(dom: str) -> list[str]:
    return PLAN if dom in CLASSICAL else REF_LONG


def right_tool(task: str, dom: str) -> str:
    if task == "solve":
        return "classic_planner" if dom in CLASSICAL else "numeric_planner"
    return "get_state_transition" if task == "simulate" else task


# ------------------------------------------------------------------ plants
# (model, arm, task) -> {(domain, slot): (answer kind, how)}. `slot` is 0, 1 or 2.
# `how`, no tools: "plain", "atcap" (the answer stopped at the output cap), "refusal".
# `how`, tools: "right" (the right tool once, right result), "classic" (the classic
# planner whatever the domain), "none" (no tool call), "right_plus" (the right tool and
# another one), "tool_error" (the first call raised, the second is right), "loop" (ten
# round trips of another tool, no answer), "noroom400" (the provider rejected the next
# request as too long), "noroomstop" (the same, reported as a stop reason),
# "think_overflow" (another tool, then a final turn that reached the cap holding a note
# and no answer), "pause" and "unknown" (error rows that are not refusals), "scoring"
# (the harness's grader raised; the answer is stored), "scoring_loop" (ten round trips of
# another tool and the harness's grader raised: the harness labels it loop_exhausted, not
# an exception), "cut" (longer than storage).
def _all(spec, slot, domains=DOMAINS):
    return {(d, slot): spec for d in domains}


D4 = DOMAINS[:4]
PLANTS = {
    # A. Haiku solve: no tools wrong on the second slot of every domain (d05 stopped at
    # the cap). Tools: the classic planner on the third slot whatever the domain; d03's
    # second slot is cut by storage and is right only in the sidecar's full answer.
    (HAIKU, N, "solve"): {**_all(("wrong_lines", "plain"), 1), ("d05", 1): ("wrong_lines", "atcap")},
    (HAIKU, T, "solve"): {**_all(("right", "classic"), 2), ("d03", 1): ("cut_plan", "cut")},
    # B. Haiku validate_domain: no tools wrong on d01 (a refusal, then two wrong verdicts).
    (HAIKU, N, "validate_domain"): {("d01", 0): ("", "refusal"), ("d01", 1): ("wrong", "plain"),
                                    ("d01", 2): ("wrong", "plain")},
    # C. Haiku validate_problem: no tools refused on the first slot of d01..d04. Tools:
    # on d05 the first tool call raised and the second was right.
    (HAIKU, N, "validate_problem"): _all(("", "refusal"), 0, D4),
    (HAIKU, T, "validate_problem"): {("d05", 0): ("ok", "tool_error")},
    # D. Haiku validate_plan: tools wrong on the first slot of d01..d04 in four ways.
    (HAIKU, T, "validate_plan"): {("d01", 0): ("", "loop"), ("d02", 0): ("wrong", "none"),
                                  ("d03", 0): ("wrong", "right_plus"),
                                  ("d04", 0): ("no_verdict", "right")},
    # E. Haiku simulate: no tools has no right answer at all.
    (HAIKU, N, "simulate"): {**{(d, s): ("trace_wrong", "plain") for d in DOMAINS for s in range(3)},
                             **_all(("per_line_wrong", "plain"), 0, D4)},
    # F. Sonnet solve: both arms right, but only under the registered grade on the first
    # slot (no tools: the plan only in the last code block; tools: capitals). Tools: no
    # tool call on the third slot.
    (SONNET, N, "solve"): {**_all(("json_block", "plain"), 0), ("d01", 0): ("tried_then_block", "plain")},
    (SONNET, T, "solve"): {**_all(("caps_block", "right"), 0), ("d01", 1): ("caps_json", "right"),
                           **_all(("right", "none"), 2)},
    # G. Sonnet validate_domain: tools wrong on d02 (a pause, an unknown stop, a wrong
    # verdict after a right tool result).
    (SONNET, T, "validate_domain"): {("d02", 0): ("", "pause"), ("d02", 1): ("", "unknown"),
                                     ("d02", 2): ("wrong", "right")},
    # G2. Sonnet validate_problem: tools wrong on d09's first slot, a loop-exhausted trial
    # on which the harness's grader also raised.
    (SONNET, T, "validate_problem"): {("d09", 0): ("", "scoring_loop")},
    # H. Sonnet validate_plan: no tools wrong on the third slot of every domain.
    (SONNET, N, "validate_plan"): _all(("wrong", "plain"), 2),
    # I. Sonnet simulate: no tools writes the right trace one object per line on d01..d04.
    # Tools wrong on the first slot of d05..d08 in four ways.
    (SONNET, N, "simulate"): _all(("per_line", "plain"), 0, D4),
    (SONNET, T, "simulate"): {("d05", 0): ("trace", "scoring"), ("d06", 0): ("", "think_overflow"),
                              ("d07", 0): ("", "noroom400"), ("d08", 0): ("", "noroomstop")},
}
# Sonnet, tools, validate_problem: trials requested on the next UTC date. d01 and d02 as a
# whole; d03's second request only (its first request is on the batch's date).
LATER = {(SONNET, "validate_problem", "d01", 0): "all", (SONNET, "validate_problem", "d02", 0): "all",
         (SONNET, "validate_problem", "d03", 0): "second"}
# A trial whose first try was abandoned after its sidecar line was written: the sidecar
# holds two lines for it, and the last one belongs to the row.
ABANDONED_FIRST = (HAIKU, T, "validate_domain", "d07", 0)
# A half-written last line (a run that was killed): in this folder's trials.jsonl and in
# that folder's trial_meta.jsonl.
TORN_ROWS, TORN_SIDECAR = (HAIKU, T), (SONNET, N)


def spec_of(model, arm, task, dom, slot):
    s = PLANTS.get((model, arm, task), {}).get((dom, slot))
    if s is None:
        kind = "right" if task == "solve" else "trace" if task == "simulate" else "ok"
        return kind, "plain" if arm == N else "right"
    return s


# ------------------------------------------------------------------ rows and sidecar lines
def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@functools.lru_cache(maxsize=None)
def system_sha(arm: str, task: str) -> str:
    """sha256 of the system text a folder sends on a task, from the harness."""
    msgs = build_messages(task, "(d)", "(p)", 11, arm == T, {"plan": ["(a)"]},
                          prompt_style="minimal")
    if arm == N and task in CP.CONTROL_TASKS:
        msgs, _ = CP.swap_system(msgs, "format-stated")
    return sha(msgs[0]["content"])


def request(model, arm, task, n_messages):
    keys = ["max_tokens", "messages", "model", "output_config", "system", "thinking"]
    return {"model": model, "max_tokens": CAP[task], "thinking": dict(SETTINGS[model]["thinking"]),
            "output_config": {"effort": SETTINGS[model]["effort"]},
            "param_keys": sorted(keys + (["tools"] if arm == T else [])),
            "has_tools": arm == T, "n_messages": n_messages}


def tool_result(task, dom, prob, label, name):
    if name in ("classic_planner", "numeric_planner"):
        return json.dumps({"plan": PLAN, "solve_time": 0.5})
    if name == "get_state_transition":
        return TRACE
    ok = truth(name, prob, label) if name == task else True
    return json.dumps({"valid": ok, "status": "VALID" if ok else "INVALID", "report": "checked"})


def tool_args(task, dom):
    args = {"domain": "(define)", "problem": "(define)"}
    if task in ("simulate", "validate_plan"):
        args["plan"] = "\n".join(ref_plan(dom))
    return args


class Clock:
    """Request times of one folder: one second apart on the model's day."""
    def __init__(self, model):
        self.model, self.n = model, 0

    def next(self, later=False) -> tuple[str, str]:
        self.n += 1
        day = (NEXT_DAY if later else DAY)[self.model]
        h, rest = divmod(self.n, 3600)
        m, s = divmod(rest, 60)
        t = f"{day}T{9 + h:02d}:{m:02d}:{s:02d}"
        return t + ".000000Z", t + ".500000Z"


def make_trial(model, arm, task, dom, slot, clock, spec=None):
    """(row object, sidecar line) of one trial."""
    prob, label, v = slots(task, dom)[slot]
    kind, how = spec or spec_of(model, arm, task, dom, slot)
    key = [model, task, dom, prob, label, v, arm == T, "off", "all", "minimal"]
    text = answer(kind, task, prob, label)
    later = LATER.get((model, task, dom, slot)) if arm == T else None
    batch_n = BATCH_OF.get((model, task, dom, slot), 1)
    batch = BATCHES[model][batch_n - 1]
    turns, calls, flags = [], [], []

    def turn(stop, content, out=OUT_TOK, think=None, seen=0):
        n = len(turns) + 1
        usage = {"input_tokens": IN_TOK, "output_tokens": out}
        if think is not None:
            usage["output_tokens_details"] = {"thinking_tokens": think}
        rec = {"turn": n, "request": request(model, arm, task, 2 * n - 1),
               "requested_at_utc": None, "received_at_utc": None, "request_id": None,
               "anthropic_version_sent": API_VERSION, "message_id": f"msg_{dom}_{task}_{slot}_{n}",
               "model": RETURNED_ID[model], "stop_reason": stop, "stop_details": None,
               "usage": usage, "content": content}
        if arm == T:
            is_later = later == "all" or (later == "second" and n >= 2)
            rec["requested_at_utc"], rec["received_at_utc"] = clock.next(is_later)
            rec["request_id"] = f"req_{clock.n}"
            rec.update(request_body_sha256=sha(f"{key}{n}"), request_host="api.anthropic.com",
                       thinking_blocks_in_previous_response=seen,
                       thinking_blocks_passed_back=seen)
        else:
            rec["requested_at_utc"] = f"{DAY[model]}T{batch[4]:02d}:00:01.000000Z"
            rec["received_at_utc"] = batch[5]
        turns.append(rec)

    def call(names, note=False, raises=False):
        """One response that asks for tools, and their results."""
        n = len(turns) + 1
        content = []
        if note:
            content.append({"type": "thinking", "thinking": "Calling the tool.",
                            "signature": "SIG=="})
        seen = sum(b["type"] == "thinking" for b in turns[-1]["content"]) if turns else 0
        for j, name in enumerate(names):
            content.append({"type": "tool_use", "id": f"tu{n}_{j}", "name": name,
                            "input": tool_args(task, dom)})
            result = "Tool error: the server raised" if raises else tool_result(
                task, dom, prob, label, name)
            calls.append({"name": name, "arguments": tool_args(task, dom), "result": result})
            flags.append({"turn": n, "tool_use_id": f"tu{n}_{j}", "name": name,
                          "is_error": raises})
        turn("tool_use", content, think=NOTE_TOK if note else None, seen=seen)

    def final(stop, content, **kw):
        seen = sum(b["type"] == "thinking" for b in turns[-1]["content"]) if turns else 0
        turn(stop, content, seen=seen, **kw)

    right = right_tool(task, dom)
    other = "validate_plan" if task != "validate_plan" else "validate_domain"
    note = model == SONNET and arm == T and task == "solve"     # Sonnet's notes
    outcome, overflow_error, thinking = "answer", "", ""
    stored = {"success": False, "tool_selected": None if arm == N else False,
              "failure_reason": "format_parse_fail", "done_reason": "stop", "error": ""}
    said = [{"type": "text", "text": text}]
    if how in ("plain", "atcap"):
        final("max_tokens" if how == "atcap" else "end_turn", said,
              out=CAP[task] if how == "atcap" else OUT_TOK)
        ok = kind in STORED_OK
        stored.update(success=ok, failure_reason="ok" if ok else "result_mismatch",
                      done_reason="length" if how == "atcap" else "stop")
    elif how == "refusal":
        final("refusal", [{"type": "text", "text": "I can't help with that."}])
        outcome = "refusal"
    elif how == "pause":
        final("pause_turn", [])
        outcome = "pause_turn"
    elif how == "unknown":
        call([right])
        final("some_new_reason", [])
        outcome = "unknown_stop"
    elif how == "none":
        final("end_turn", said)
        stored.update(failure_reason="tool_not_selected")
    elif how in ("right", "classic", "right_plus", "scoring", "cut", "tool_error"):
        if how == "tool_error":
            call([right], raises=True)
        call(["classic_planner"] if how == "classic" else
             [right, other] if how == "right_plus" else [right], note=note)
        final("end_turn", said)
        stored.update(success=True, tool_selected=True, failure_reason="ok")
        if how == "scoring":
            stored.update(success=False, tool_selected=None, failure_reason="exception",
                          error="scoring error: boom")
    elif how in ("loop", "scoring_loop"):
        for _ in range(10):
            call([other])
        outcome = "loop_exhausted"
        stored.update(failure_reason="loop_exhausted", done_reason="tool_calls")
        if how == "scoring_loop":
            stored.update(tool_selected=None, error="scoring error: boom")
    elif how == "noroom400":
        call([right])
        outcome = "overflow"
        overflow_error = "prompt is too long: 1200000 tokens > 1000000 maximum"
        stored.update(success=True, tool_selected=True, failure_reason="ok",
                      done_reason="length", error="api: prompt is too long")
    elif how == "noroomstop":
        call([right])
        final("model_context_window_exceeded", [])
        outcome = "overflow"
        stored.update(success=True, tool_selected=True, failure_reason="ok",
                      done_reason="length", error="api: prompt is too long")
    elif how == "think_overflow":
        call([other])
        thinking = "A long note that used the whole output allowance."
        final("max_tokens", [{"type": "thinking", "thinking": thinking, "signature": "SIG=="}],
              out=CAP[task], think=OVERFLOW_NOTE_TOK)
        stored.update(failure_reason="think_overflow", done_reason="length")
    else:
        raise ValueError(how)

    error_row = outcome in ("refusal", "pause_turn", "unknown_stop")
    full = text if outcome == "answer" else ""
    fmt = None
    if task == "simulate" and arm == N and not error_row:
        fmt = kind in ("trace", "trace_wrong")
    result = {
        "model": model, "task": task, "domain_name": dom, "problem_name": prob,
        "prompt_variant": v, "with_tools": arm == T, "success": stored["success"],
        "tool_selected": stored["tool_selected"], "format_compliant": fmt,
        "response": full[:STORAGE_CAP], "response_truncated_by_storage": len(full) > STORAGE_CAP,
        "thinking": thinking, "tool_calls": calls,
        "tokens": {"prompt": IN_TOK * len(turns),
                   "completion": sum(t["usage"]["output_tokens"] for t in turns),
                   "turns": len(turns), "total_duration_ns": 1, "eval_duration_ns": 1},
        "duration_s": 1.0, "error": stored["error"], "tool_filter": "all",
        "prompt_style": "minimal", "failure_reason": stored["failure_reason"],
        "truncated": stored["done_reason"] == "length", "done_reason": stored["done_reason"],
        "think_truncated": None, "plan_label": label, "infra_failure": False}
    if outcome == "overflow":
        result["tokens"]["ctx_no_room_turns"] = 1
    if error_row:
        # The shape the harness writes when the client call raised: nothing but the error.
        result.update(success=False, tool_selected=None, response="", thinking="",
                      tool_calls=[], tokens={}, failure_reason="exception", truncated=False,
                      done_reason="", error=f"stop_reason={turns[-1]['stop_reason']}")
    meta = {
        "key": key, "custom_id": "t" + sha(json.dumps(key))[:24], "run": RUN, "arm": arm,
        "transport": "live" if arm == T else "batch", "model_requested": model,
        "model_ids_returned": [RETURNED_ID[model]], "anthropic_version_sent": [API_VERSION],
        "sdk_version": SDK,
        "settings": {"thinking": SETTINGS[model]["thinking"], "effort": SETTINGS[model]["effort"],
                     "max_tokens": CAP[task], "system_sha256": system_sha(arm, task)},
        "batch_id": batch_id(model, batch_n) if arm == N else None,
        "request_ids": [t["request_id"] for t in turns], "n_turns": len(turns),
        "outcome": outcome, "stop_reason": turns[-1]["stop_reason"], "stop_details": None,
        "overflow_error": overflow_error, "storage_cut": len(full) > STORAGE_CAP,
        "answer_chars": len(full),
        "full_answer_if_cut": full if len(full) > STORAGE_CAP else None,
        "tool_results": flags, "turns": turns,
        "written_at_utc": f"{DAY[model]}T23:00:00.000000Z"}
    if arm == N:
        meta["batch_created_at"] = f"{DAY[model]}T{batch[4]:02d}:00:00+00:00"
        meta["batch_ended_at"] = batch[5]
    return {"key": key, "result": result}, meta


def batches_json(model) -> list[dict]:
    """batches.json of a no-tools folder: the fields the runner's batch_submit, batch_poll
    and batch_grade write."""
    out = []
    for n, (requests, ok, errored, expired, hour, ended) in enumerate(BATCHES[model], 1):
        sent = f"{DAY[model]}T{hour:02d}:00:01.000000Z"
        out.append({
            "n": n, "batch_id": batch_id(model, n), "n_requests": requests, "fetched": True,
            "send_started_at_utc": f"{DAY[model]}T{hour:02d}:00:00.000000Z",
            "submitted_at_utc": sent, "request_id": f"req_batch_{n}",
            "anthropic_version_sent": API_VERSION, "request_host": "api.anthropic.com",
            "sdk_version": SDK, "created_at": f"{DAY[model]}T{hour:02d}:00:00+00:00",
            "ended_at": ended,
            "request_counts": {"processing": 0, "succeeded": ok, "errored": errored,
                               "canceled": 0, "expired": expired},
            "results_fetched_at_utc": ended.replace("+00:00", ".000000Z"),
            "spend_recorded": True, "graded_at_utc": ended.replace("+00:00", ".000000Z"),
            "graded_with_tools_commit": TOOLS_COMMIT, "graded_with_pyvalidator": "0.1.5"})
    return out


def folder_trials(model, arm, plants=True):
    """[(row object, sidecar line)] of one folder, in the runner's order."""
    clock = Clock(model)
    out = []
    for task in TASKS:
        for dom in DOMAINS:
            for slot in range(3):
                spec = None if plants else spec_of(None, arm, task, dom, slot)
                out.append(make_trial(model, arm, task, dom, slot, clock, spec))
    return out


def write_folder(root: Path, model, arm, trials=None):
    d = root / f"{model}_{arm}"
    d.mkdir(parents=True, exist_ok=True)
    trials = folder_trials(model, arm) if trials is None else trials
    with (d / "trials.jsonl").open("w") as rows, (d / "trial_meta.jsonl").open("w") as side:
        for row, meta in trials:
            k = row["key"]
            slot = [s[:3] for s in slots(k[1], k[2])].index((k[3], k[4], k[5]))
            if (model, arm, k[1], k[2], slot) == ABANDONED_FIRST:
                first = make_trial(model, arm, k[1], k[2], slot, Clock(model), ("wrong", "none"))[1]
                side.write(json.dumps(first) + "\n")
            side.write(json.dumps(meta) + "\n")
            rows.write(json.dumps(row) + "\n")
        if (model, arm) == TORN_ROWS:
            rows.write('{"key": ["half-written')
        if (model, arm) == TORN_SIDECAR:
            side.write('{"key": ["half-written')


def manifest(model, arm, gt: dict, gt_file_sha: str) -> dict:
    """run_manifest.json of one folder, the fields of tools/_run_manifest.build_manifest
    and of the runner's build_run_manifest."""
    tools = arm == T
    return {
        "manifest_version": 1, "created_at": f"{DAY[model]}T06:59:00+0000",
        "backend": "anthropic-live" if tools else "anthropic-batch", "sdk_version": SDK,
        "model": model, "with_tools": tools, "conditions": arm, "tasks": sorted(TASKS),
        "corpus": "canonical", "domains_dir": "domains", "prompt_variants": list(WORDINGS),
        "num_predict": None, "snapshot_len": STORAGE_CAP, "max_iterations": 10 if tools else 1,
        "stream": False, "temperature": "not sent (provider default)",
        "think": SETTINGS[model]["thinking"]["type"], "ground_truth": "cached",
        "ground_truth_sha256": sha(json.dumps(gt, sort_keys=True, separators=(",", ":"))),
        "gt_cache_sha256": gt_file_sha, "gt_cache_path": "gt_cache.json", "keys_files": None,
        "limit": None, "run": RUN, "pilot": False, "effort": SETTINGS[model]["effort"],
        "sdk_version_pinned": SDK, "output_caps": dict(CAP),
        "system_sha256": {t: system_sha(arm, t) for t in TASKS},
        "tools_commit": TOOLS_COMMIT if tools else None,
        "tools_pyvalidator": "0.1.5" if tools else None,
        "tools_env": {"pddl-validator": ["pddl-pyvalidator==0.1.5"]} if tools else None,
        "tools_sha256": TOOLS_SHA256 if tools else None,
        "base_url": "https://api.anthropic.com", "client_timeout_s": 600.0,
        "client_max_retries": 1, "turn_attempts": 2,
        "runner_sha256": {f"tools/frontier55/{f}.py": sha(f) for f in
                          ("anthropic_requests", "runner", "cost")}}


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "SYNTHETIC_FIXTURE").write_text(
        "Synthetic fixture for tests/test_frontier55_analysis.py. Not experiment data.\n")
    design = {"per_task": {t: 60 for t in TASKS}, "n_folder": 300, "per_wording": 100,
              "k_domains": 20, "domains": list(DOMAINS)}
    (out / "design.json").write_text(json.dumps(design, indent=1, sort_keys=True) + "\n")
    gt: dict = {}
    for d, p in PROBLEMS:
        gt.setdefault(d, {})[p] = {"plan": ref_plan(d), "trace": TRACE}
        path = out / "domains" / ("classical" if d in CLASSICAL else "numeric") / d
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{p}.pddl").write_text(
            f"(define (problem {p}) (:domain {d})\n  (:objects r - robot l1 l2 l3 - place)\n"
            f"  (:init (at r l1)) (:goal (at r l2)))\n")
    gt_text = json.dumps(gt, indent=1, sort_keys=True) + "\n"
    (out / "gt_cache.json").write_text(gt_text)
    stored = [{"domain": d, "problem": p, "plan": pl, "valid": ok} for d, p in PROBLEMS
              for pl, ok in ((PLAN, True), (WRONG, False), (CAPS, False))]
    (out / "plan_verdicts.json").write_text(json.dumps(stored, indent=1) + "\n")
    route = stored + [{"domain": d, "problem": p, "plan": TRIED, "valid": False}
                      for d, p in PROBLEMS]
    (out / "route").mkdir(exist_ok=True)
    (out / "route" / "plan_verdicts.json").write_text(json.dumps(route, indent=1) + "\n")
    for m in MODELS:
        for arm in ARMS:
            write_folder(out / RUN, m, arm)
            (out / RUN / f"{m}_{arm}" / "run_manifest.json").write_text(
                json.dumps(manifest(m, arm, gt, sha(gt_text)), indent=2, sort_keys=True) + "\n")
        (out / RUN / f"{m}_{N}" / "batches.json").write_text(
            json.dumps(batches_json(m), indent=2) + "\n")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
