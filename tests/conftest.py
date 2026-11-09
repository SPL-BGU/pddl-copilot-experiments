"""pytest adapter for the plain-Python test suite (tests/verify.sh is the
primary runner and needs no pytest).

The test functions take a `TestResults` collector named `r` and record
checks on it instead of raising. This fixture hands each test a fresh
collector and fails the test at teardown when any check failed, so
`python3 -m pytest tests/test_<name>.py` runs the same assertions.
"""
import pytest

from tests._helpers import TestResults


@pytest.fixture
def r(request):
    res = TestResults(request.node.name)
    yield res
    if res.failed:
        lines = "\n".join(f"  - {label}: {detail}" for label, detail in res.failures)
        pytest.fail(f"{res.failed} check(s) failed:\n{lines}", pytrace=False)
