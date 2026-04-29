"""Unit tests for pure scoring helpers in run_experiment.py.

Run standalone: `python3 tests/test_scoring.py`
Or via the shell wrapper: `bash tests/verify.sh`
"""

import sys
from pathlib import Path

# Make run_experiment importable when run from the tests directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_experiment as rx
from pddl_eval.scoring import _call_matches_validate_task
from tests._helpers import TestResults


def test_wilson_ci(r: TestResults):
    lo, hi = rx.wilson_ci(0, 0)
    r.check_eq("wilson (0,0)", (lo, hi), (0.0, 0.0))

    lo, hi = rx.wilson_ci(0, 10)
    r.check("wilson (0,10) lower==0", lo == 0.0, f"lo={lo}")
    r.check("wilson (0,10) upper>0", hi > 0.0 and hi < 1.0, f"hi={hi}")

    lo, hi = rx.wilson_ci(10, 10)
    r.check("wilson (10,10) upper==1", hi == 1.0, f"hi={hi}")
    r.check("wilson (10,10) lower<1", lo < 1.0 and lo > 0.0, f"lo={lo}")

    lo, hi = rx.wilson_ci(5, 10)
    r.check("wilson (5,10) brackets 0.5", lo < 0.5 < hi, f"lo={lo} hi={hi}")


def test_parse_validation_verdict(r: TestResults):
    r.check_eq("verdict valid=true", rx._parse_validation_verdict('{"valid": true, "status": "VALID"}'), True)
    r.check_eq("verdict valid=false", rx._parse_validation_verdict('{"valid": false}'), False)
    r.check_eq("verdict error shape", rx._parse_validation_verdict('{"error": true, "message": "x"}'), None)
    r.check_eq("verdict not json", rx._parse_validation_verdict("not json"), None)
    r.check_eq("verdict empty dict", rx._parse_validation_verdict("{}"), None)
    r.check_eq("verdict None input", rx._parse_validation_verdict(""), None)


def test_tool_error_seen(r: TestResults):
    # Transport error string
    calls = [{"name": "classic_planner", "arguments": {}, "result": "Tool error: boom"}]
    r.check_eq("transport error", rx._tool_error_seen(calls, "classic_planner"), True)

    # Plugin error shape
    calls = [{"name": "classic_planner", "arguments": {}, "result": '{"error": true, "message": "bad"}'}]
    r.check_eq("plugin error", rx._tool_error_seen(calls, "classic_planner"), True)

    # Healthy response
    calls = [{"name": "classic_planner", "arguments": {}, "result": '{"plan": ["(a)"]}'}]
    r.check_eq("healthy call", rx._tool_error_seen(calls, "classic_planner"), False)

    # Call for a different tool is ignored
    calls = [{"name": "other", "arguments": {}, "result": "Tool error: boom"}]
    r.check_eq("other tool ignored", rx._tool_error_seen(calls, "classic_planner"), False)

    # Non-JSON, non-error string → continue to next; no errors overall
    calls = [{"name": "classic_planner", "arguments": {}, "result": "free-form text"}]
    r.check_eq("non-json ignored", rx._tool_error_seen(calls, "classic_planner"), False)


def test_used_tool(r: TestResults):
    r.check_eq("empty list", rx._used_tool([], "x"), False)
    r.check_eq("present", rx._used_tool([{"name": "x"}], "x"), True)
    r.check_eq("absent", rx._used_tool([{"name": "y"}], "x"), False)


def test_call_matches_validate_task(r: TestResults):
    # validate_domain — domain-only is the only acceptable shape.
    domain_only = {"name": "validate_pddl_syntax", "arguments": {"domain": "(D)"}}
    domain_with_problem = {"name": "validate_pddl_syntax",
                           "arguments": {"domain": "(D)", "problem": "(P)"}}
    domain_with_plan = {"name": "validate_pddl_syntax",
                        "arguments": {"domain": "(D)", "plan": "(p)"}}
    full_call = {"name": "validate_pddl_syntax",
                 "arguments": {"domain": "(D)", "problem": "(P)", "plan": "(p)"}}

    r.check("vd accepts domain-only",
            _call_matches_validate_task(domain_only, "validate_domain"))
    r.check("vd rejects when problem present",
            not _call_matches_validate_task(domain_with_problem, "validate_domain"))
    r.check("vd rejects when plan present",
            not _call_matches_validate_task(domain_with_plan, "validate_domain"))

    # validate_problem — problem required, plan forbidden.
    r.check("vp(roblem) rejects domain-only",
            not _call_matches_validate_task(domain_only, "validate_problem"))
    r.check("vp(roblem) accepts domain+problem",
            _call_matches_validate_task(domain_with_problem, "validate_problem"))
    r.check("vp(roblem) rejects when plan present",
            not _call_matches_validate_task(full_call, "validate_problem"))

    # validate_plan — plan required (problem may or may not be present;
    # the validator routes by presence of `plan`).
    r.check("vp(lan) accepts full call",
            _call_matches_validate_task(full_call, "validate_plan"))
    r.check("vp(lan) accepts domain+plan",
            _call_matches_validate_task(domain_with_plan, "validate_plan"))
    r.check("vp(lan) rejects domain-only",
            not _call_matches_validate_task(domain_only, "validate_plan"))

    # Empty/missing `arguments` must not crash and must reject every task.
    no_args = {"name": "validate_pddl_syntax"}
    null_args = {"name": "validate_pddl_syntax", "arguments": None}
    for label, tc_in in (("missing args", no_args), ("null args", null_args)):
        r.check(f"{label} → vd accepts (no problem/plan)",
                _call_matches_validate_task(tc_in, "validate_domain"))
        r.check(f"{label} → vp(roblem) rejects",
                not _call_matches_validate_task(tc_in, "validate_problem"))
        r.check(f"{label} → vp(lan) rejects",
                not _call_matches_validate_task(tc_in, "validate_plan"))

    # Unknown task name → False (defensive default).
    r.check("unknown task → False",
            not _call_matches_validate_task(domain_only, "solve"))


def test_get_tool_results(r: TestResults):
    calls = [
        {"name": "a", "arguments": {}, "result": "r1"},
        {"name": "b", "arguments": {}, "result": "r2"},
        {"name": "a", "arguments": {}, "result": "r3"},
    ]
    r.check_eq("filter by name", rx._get_tool_results(calls, "a"), ["r1", "r3"])
    r.check_eq("no matches", rx._get_tool_results(calls, "z"), [])
    # Missing 'result' field → skipped
    calls2 = [{"name": "a", "arguments": {}}]
    r.check_eq("missing result", rx._get_tool_results(calls2, "a"), [])


def test_extract_plan_from_tool_result(r: TestResults):
    r.check_eq("plan list", rx._extract_plan_from_tool_result('{"plan": ["(pick-up a)", "(stack a b)"]}'),
               ["(pick-up a)", "(stack a b)"])
    r.check_eq("plan empty", rx._extract_plan_from_tool_result('{"plan": []}'), [])
    r.check_eq("error shape", rx._extract_plan_from_tool_result('{"error": true}'), [])
    r.check_eq("not json", rx._extract_plan_from_tool_result("junk"), [])
    r.check_eq("no plan key", rx._extract_plan_from_tool_result('{"other": 1}'), [])


def test_extract_plan_lines(r: TestResults):
    # Bare actions
    r.check_eq("bare actions",
               rx.extract_plan_lines("(pick-up a)\n(stack a b)"),
               ["(pick-up a)", "(stack a b)"])

    # Numbered
    r.check_eq("numbered dot",
               rx.extract_plan_lines("1. (pick-up a)\n2. (stack a b)"),
               ["(pick-up a)", "(stack a b)"])

    r.check_eq("numbered colon",
               rx.extract_plan_lines("1: (pick-up a)"),
               ["(pick-up a)"])

    # Bulleted — B2 new behaviour
    r.check_eq("dash bullet (B2)",
               rx.extract_plan_lines("- (pick-up a)\n- (stack a b)"),
               ["(pick-up a)", "(stack a b)"])

    r.check_eq("asterisk bullet (B2)",
               rx.extract_plan_lines("* (pick-up a)\n* (stack a b)"),
               ["(pick-up a)", "(stack a b)"])

    # Code fences ignored
    r.check_eq("fence ignored",
               rx.extract_plan_lines("```\n(pick-up a)\n```"),
               ["(pick-up a)"])

    # Case normalization
    r.check_eq("uppercase → lower",
               rx.extract_plan_lines("(PICK-UP A)"),
               ["(pick-up a)"])

    # Non-action lines skipped
    r.check_eq("prose skipped",
               rx.extract_plan_lines("Here is the plan:\n(pick-up a)\nThat's it."),
               ["(pick-up a)"])

    # Empty
    r.check_eq("empty string", rx.extract_plan_lines(""), [])
    r.check_eq("None", rx.extract_plan_lines(None), [])

    # <think>...</think> blocks must be stripped before parsing (PR-2):
    # a thinking-mode model that inlines its reasoning in `content` could
    # otherwise leak action-shaped lines from inside the reasoning block.
    r.check_eq("think block stripped",
               rx.extract_plan_lines(
                   "<think>I should call (pick-up x) first</think>\n(pick-up a)"),
               ["(pick-up a)"])
    r.check_eq("think block stripped (case-insensitive)",
               rx.extract_plan_lines(
                   "<THINK>(stack a b)</THINK>\n(pick-up a)"),
               ["(pick-up a)"])
    r.check_eq("think block stripped (multiline)",
               rx.extract_plan_lines(
                   "<think>\nLine 1\n(stack a b)\nLine 3\n</think>\n(pick-up a)"),
               ["(pick-up a)"])


def test_extract_verdict(r: TestResults):
    r.check_eq("VALID", rx.extract_verdict("VERDICT: VALID"), True)
    r.check_eq("INVALID", rx.extract_verdict("VERDICT: INVALID"), False)
    r.check_eq("no verdict", rx.extract_verdict("hello world"), None)
    r.check_eq("empty", rx.extract_verdict(""), None)
    r.check_eq("None", rx.extract_verdict(None), None)
    r.check_eq("case insensitive", rx.extract_verdict("verdict: valid"), True)
    r.check_eq("last wins",
               rx.extract_verdict("VERDICT: INVALID\n...actually VERDICT: VALID"),
               True)
    # Surrounded by other text
    r.check_eq("embedded",
               rx.extract_verdict("The plan is fine.\nVERDICT: VALID\nEnd."),
               True)

    # <think>...</think> blocks must be stripped before parsing (PR-2):
    # if a thinking-mode model emits VERDICT: VALID inside its reasoning
    # block but VERDICT: INVALID outside, the graded answer is INVALID.
    r.check_eq("think block ignored, outer wins",
               rx.extract_verdict(
                   "<think>VERDICT: VALID looks right</think>\nVERDICT: INVALID"),
               False)
    r.check_eq("think block stripped, outer parses",
               rx.extract_verdict(
                   "<think>thinking...</think>\nVERDICT: VALID"),
               True)
    r.check_eq("think-only response → no verdict",
               rx.extract_verdict("<think>VERDICT: VALID</think>"),
               None)


def test_classify_step_failure_think_overflow(r: TestResults):
    # _classify_step_failure must NOT relabel a pre-set FR_THINK_OVERFLOW
    # back to FR_TRUNCATED_NO_ANSWER via the truncation override, even
    # though done_reason=="length".
    fr, trunc = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=False,
        failure_reason=rx.FR_THINK_OVERFLOW,
    )
    r.check_eq("FR_THINK_OVERFLOW survives length-override", fr, rx.FR_THINK_OVERFLOW)
    r.check_eq("FR_THINK_OVERFLOW marks truncated=True", trunc, True)

    # Regression: FR_TRUNCATED_NO_ANSWER still applies to the legacy
    # empty-output reasons under the same length cap.
    fr2, trunc2 = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=False,
        failure_reason=rx.FR_PLAN_INVALID,
    )
    r.check_eq("FR_PLAN_INVALID still overrides to FR_TRUNCATED_NO_ANSWER",
               fr2, rx.FR_TRUNCATED_NO_ANSWER)
    r.check_eq("override marks truncated=True", trunc2, True)

    # FR_LOOP_EXHAUSTED takes precedence over a length cap (it's the more
    # specific tag for tool-loop cap-hit). PR-2 design decision #4.
    fr3, trunc3 = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=True,
        failure_reason=rx.FR_OK,  # would-be classifier output before override
    )
    r.check_eq("LOOP_EXHAUSTED beats truncation override", fr3, rx.FR_LOOP_EXHAUSTED)

    # New (post-fold-in): the classifier itself sets FR_THINK_OVERFLOW
    # when given non-empty thinking and empty response under a length cap.
    # Previously this override lived inline in evaluate_one with the
    # ordering pinned only by a comment.
    fr4, trunc4 = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=False,
        failure_reason=rx.FR_NO_VERDICT_PARSED,
        thinking_text="rambling reasoning here", response_text="",
    )
    r.check_eq("classifier sets FR_THINK_OVERFLOW from texts",
               fr4, rx.FR_THINK_OVERFLOW)
    r.check_eq("FR_THINK_OVERFLOW (from texts) marks truncated=True",
               trunc4, True)

    # Guard: non-empty response_text means the model emitted *something*,
    # so the cap isn't a thinking-spiral. Falls through to the truncation
    # override (FR_NO_VERDICT_PARSED → FR_TRUNCATED_NO_ANSWER).
    fr5, _ = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=False,
        failure_reason=rx.FR_NO_VERDICT_PARSED,
        thinking_text="thinking", response_text="VERDICT: VALID",
    )
    r.check_eq("non-empty response_text blocks think-overflow override",
               fr5, rx.FR_TRUNCATED_NO_ANSWER)

    # Guard: empty thinking_text → no spiral, no override. Falls through
    # to the truncation override.
    fr6, _ = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=False,
        failure_reason=rx.FR_NO_VERDICT_PARSED,
        thinking_text="", response_text="",
    )
    r.check_eq("empty thinking_text blocks think-overflow override",
               fr6, rx.FR_TRUNCATED_NO_ANSWER)

    # Precedence: FR_LOOP_EXHAUSTED beats FR_THINK_OVERFLOW even when the
    # think-overflow conditions are satisfied. The tool-loop cap-hit is
    # the more specific failure mode.
    fr7, _ = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=True,
        failure_reason=rx.FR_OK,
        thinking_text="thinking", response_text="",
    )
    r.check_eq("LOOP_EXHAUSTED beats THINK_OVERFLOW", fr7, rx.FR_LOOP_EXHAUSTED)

    # Guard: a populated `error` string (exception path or extracted
    # tool-error message) blocks the think-overflow override. The original
    # failure_reason is preserved.
    fr8, _ = rx._classify_step_failure(
        success=False, done_reason="length", loop_exhausted=False,
        failure_reason=rx.FR_EXCEPTION,
        thinking_text="thinking", response_text="",
        error="ConnectionError: refused",
    )
    r.check_eq("non-empty error blocks think-overflow override",
               fr8, rx.FR_EXCEPTION)


def test_expand_conditions(r: TestResults):
    # 'both' must preserve (True, False) order so pre-ISS-004 reproductions
    # that iterate conditions in the legacy order stay byte-comparable.
    r.check_eq("both → (True, False)", rx._expand_conditions("both"), (True, False))
    r.check_eq("tools → (True,)", rx._expand_conditions("tools"), (True,))
    r.check_eq("no-tools → (False,)", rx._expand_conditions("no-tools"), (False,))


def test_shard_filter(r: TestResults):
    # N=1 is the no-shard fast path: every key passes regardless of i.
    r.check("N=1 always passes", rx._shard_filter(0, 1, ("Qwen3.5:0.8B", "solve", "blocksworld", "p01", "0")))
    r.check("N=1 always passes (even i unused)", rx._shard_filter(7, 1, ("any",)))

    # Determinism: same key → same bucket, repeatedly.
    key = ("gemma4:31b", "validate_plan", "logistics", "p03", "1")
    bucket = next(i for i in range(4) if rx._shard_filter(i, 4, key))
    for _ in range(5):
        b2 = next(i for i in range(4) if rx._shard_filter(i, 4, key))
        r.check_eq(f"determinism N=4 key={key[1]}", b2, bucket)

    # Stable across hosts: the SHA-256 bucket for a fixed key is the same
    # number on every machine. Pin one as a regression guard.
    pinned = ("Qwen3.5:0.8B", "solve", "blocksworld", "p01", "0")
    pinned_bucket = next(i for i in range(4) if rx._shard_filter(i, 4, pinned))
    import hashlib
    expected = int.from_bytes(hashlib.sha256("|".join(pinned).encode()).digest()[:8], "big") % 4
    r.check_eq("sha256 pinned bucket", pinned_bucket, expected)

    # Disjointness + completeness over a non-trivial key set: every key
    # lands in exactly one shard, and the union covers the whole set.
    keys = [
        (m, t, d, p, v)
        for m in ("Qwen3.5:0.8B", "gpt-oss:20b", "Qwen3.5:27b")
        for t in ("solve", "validate_domain", "validate_plan", "simulate")
        for d in ("blocksworld", "logistics", "depot")
        for p in ("p01", "p02")
        for v in ("0", "1")
    ]
    N = 4
    seen: set = set()
    for k in keys:
        matches = [i for i in range(N) if rx._shard_filter(i, N, k)]
        r.check_eq(f"exactly-one-shard {k[0][:8]}|{k[1][:6]}", len(matches), 1)
        seen.add(matches[0])
    r.check("every shard saw at least one key", seen == set(range(N)), f"shards seen={sorted(seen)}")
    # Rough balance check: each shard gets >12% of the 144 keys (chance of
    # any shard < 12% under uniform sha256 is < 1e-6).
    counts = [sum(1 for k in keys if rx._shard_filter(i, N, k)) for i in range(N)]
    r.check(f"rough balance counts={counts}", all(c >= len(keys) * 0.12 for c in counts))


def main():
    r = TestResults("test_scoring")
    test_wilson_ci(r)
    test_parse_validation_verdict(r)
    test_tool_error_seen(r)
    test_used_tool(r)
    test_call_matches_validate_task(r)
    test_get_tool_results(r)
    test_extract_plan_from_tool_result(r)
    test_extract_plan_lines(r)
    test_extract_verdict(r)
    test_classify_step_failure_think_overflow(r)
    test_expand_conditions(r)
    test_shard_filter(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
