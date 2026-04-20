"""Test helpers for the scoring-audit suite.

Not a pytest conftest — just a plain module imported by test_*.py files.
Provides FakeMCP (stub for MCPPlanner.call_tool) and a fixture loader that
reads tests/fixtures/*.json produced from real MCP oracle calls.
"""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a fixture JSON by short name (e.g. 'blocksworld_p01')."""
    path = FIXTURES_DIR / f"{name}.json"
    return json.loads(path.read_text())


def build_gt_from_fixture(fx: dict) -> dict:
    """Build a ground-truth dict matching the shape generate_ground_truth emits.

    Fields: {domain_valid, problem_valid, plan_valid, solvable, plan, trace,
    domain_validation_raw, problem_validation_raw, plan_validation_raw}.
    `trace` and `*_raw` are JSON strings (matching what MCPPlanner.call_tool
    returns through the bridge).
    """
    gt = fx["gt"]
    return {
        "domain_valid": gt["domain_valid"],
        "problem_valid": gt["problem_valid"],
        "plan_valid": gt["plan_valid"],
        "solvable": gt["solvable"],
        "plan": list(gt["plan"]),
        "trace": json.dumps(gt["trace_obj"]),
        "domain_validation_raw": json.dumps(gt["domain_validation_obj"]),
        "problem_validation_raw": json.dumps(gt["problem_validation_obj"]),
        "plan_validation_raw": json.dumps(gt["plan_validation_obj"]),
    }


class FakeMCP:
    """Stub for MCPPlanner. Exposes the methods check_success / _validate_model_plan use.

    Configured with a handler function that receives (tool_name, args) and
    returns a JSON string (or raises to simulate MCP transport failure).
    Records every call for inspection.
    """

    def __init__(self, handler=None):
        self._handler = handler or (lambda name, args: "")
        self.calls: list[tuple[str, dict]] = []
        # The tools list field is accessed by some paths but not by check_success.
        self.tools: list = []

    async def call_tool(self, name: str, arguments: dict) -> str:
        self.calls.append((name, dict(arguments or {})))
        result = self._handler(name, arguments or {})
        if isinstance(result, BaseException):
            raise result
        return result


def plan_sensitive_validator(fx: dict, error: bool = False):
    """Return a handler that routes validate_pddl_syntax by plan argument match.

    If the plan argument (joined by \\n) matches fx["oracle_plan"], returns the
    "valid=true" fixture response; otherwise returns the "valid=false" one.
    Domain-only and domain+problem calls get their respective raw responses.
    If `error` is True, every validate call returns the {"error": true} shape.
    """
    oracle_plan_str = "\n".join(fx["oracle_plan"])
    bad_plan_str = "\n".join(fx["bad_plan"])
    ok_plan_resp = json.dumps(fx["tool_output_objs"]["validate_plan_ok"])
    bad_plan_resp = json.dumps(fx["tool_output_objs"]["validate_plan_bad"])
    err_resp = json.dumps(fx["tool_output_objs"]["validate_plan_error"]) \
        if "validate_plan_error" in fx["tool_output_objs"] \
        else json.dumps({"error": True, "message": "mock validator error"})
    dom_resp = json.dumps(fx["gt"]["domain_validation_obj"])
    prob_resp = json.dumps(fx["gt"]["problem_validation_obj"])

    def handler(name: str, args: dict) -> str:
        if name != "validate_pddl_syntax":
            return "{}"
        if error:
            return err_resp
        plan_arg = (args.get("plan") or "").strip()
        problem_arg = args.get("problem")
        if plan_arg:
            if plan_arg == oracle_plan_str:
                return ok_plan_resp
            if plan_arg == bad_plan_str:
                return bad_plan_resp
            return bad_plan_resp
        if problem_arg:
            return prob_resp
        return dom_resp

    return handler


def raising_handler(exc: BaseException = None):
    """Handler that raises on any call — simulates MCP transport failure."""
    e = exc or RuntimeError("mock MCP transport error")

    def handler(name: str, args: dict):
        return e

    return handler


class TestResults:
    """Tiny harness that collects pass/fail per case and prints a summary.

    Used by test_*.py main blocks so the same file can be invoked standalone
    (`python3 tests/test_scoring.py`) or via tests/verify.sh.
    """

    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.failures: list[tuple[str, str]] = []

    def check(self, label: str, condition: bool, detail: str = ""):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append((label, detail))
            print(f"  FAIL [{label}]: {detail}")

    def check_eq(self, label: str, got, want):
        ok = got == want
        self.check(label, ok, f"got={got!r} want={want!r}")

    def report_and_exit(self):
        total = self.passed + self.failed
        print(f"\n{self.name}: {self.passed}/{total} passed")
        if self.failed:
            for label, detail in self.failures:
                print(f"  - {label}: {detail}")
            raise SystemExit(1)
        raise SystemExit(0)
