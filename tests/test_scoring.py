"""Unit tests for pure scoring helpers in run_experiment.py.

Run standalone: `python3 tests/test_scoring.py`
Or via the shell wrapper: `bash tests/verify.sh`
"""

import sys
from pathlib import Path

# Make run_experiment importable when run from the tests directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_experiment as rx
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
    test_get_tool_results(r)
    test_extract_plan_from_tool_result(r)
    test_extract_plan_lines(r)
    test_extract_verdict(r)
    test_expand_conditions(r)
    test_shard_filter(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
