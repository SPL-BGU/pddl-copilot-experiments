"""KCL VAL for the D5b plans and files. Standard library only.

The binary is the macOS x86_64 build from the PlanBench repository
(LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables/validate, sha256
44a07d6d..., "VAL ... Version 4"), the same one C1 used
(development/reference/val_crosscheck.md). It runs under Rosetta on arm64.
Copy it to external/kcl-val/validate (gitignored); `--kcl-val` takes any path.

The verdict rules follow tools/val_crosscheck.py (`classify_plan`,
`classify_parse`), reduced to what D5b needs; that module is not imported
because it pulls in the harness, which the D5b scratch venv does not have.
"""
from __future__ import annotations

import hashlib
import platform
import re
import subprocess
import time
from pathlib import Path

DEFAULT_BIN = Path(__file__).resolve().parents[2] / "external" / "kcl-val" / "validate"
EXPECTED_SHA256 = "44a07d6d3b2917c7c3df8e3932a3b895a8062b4e0f5fa0343f9f1ad409c4a9fe"
_DP_MARKERS = ("Problem in domain definition!", "Type problem in domain description!",
               "Type problem in problem specification!", "Parser failed to read file!",
               "Error in type-checking!")


def binary_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _cmd(binary: Path) -> list[str]:
    prefix = ["arch", "-x86_64"] if platform.machine() == "arm64" else []
    return prefix + [str(binary)]


def classify_plan(rc: int, out: str) -> tuple[bool | None, str, int | None]:
    """(valid, status, VAL's plan size). valid None = VAL gave no verdict."""
    m = re.search(r"^Plan size:\s*(\d+)", out, re.M)
    size = int(m.group(1)) if m else None
    if "Checking plan:" not in out:
        for marker in _DP_MARKERS:
            if marker in out:
                return None, "rejected_domain_or_problem", size
        return None, f"no_plan_check_rc{rc}", size
    after = out.split("Checking plan:", 1)[1]
    if re.search(r"^Plan valid\s*$", after, re.M):
        return True, "plan_valid", size
    for marker, status in (("Bad plan description!", "bad_plan_description"),
                           ("Plan failed to execute", "failed_to_execute"),
                           ("Goal not satisfied", "goal_not_satisfied")):
        if marker in after:
            return False, status, size
    if re.search(r"^Plan invalid\s*$", after, re.M):
        return False, "plan_invalid_other", size
    return None, f"no_verdict_rc{rc}", size


def classify_parse(rc: int, out: str) -> tuple[bool, str]:
    """(valid, status) of `validate DOMAIN PROBLEM` with no plan."""
    for marker in _DP_MARKERS:
        if marker in out:
            return False, marker
    if any("rror" in ln for ln in out.splitlines()):
        return False, "error_line"
    if rc != 0:
        return False, f"rc{rc}"
    return True, "accepted"


def check_plan(binary: Path, domain: str, problem: str, plan: str, timeout: float = 1800) -> dict:
    t = time.time()
    try:
        p = subprocess.run(_cmd(binary) + ["-v", domain, problem, plan],
                           capture_output=True, text=True, timeout=timeout)
        valid, status, size = classify_plan(p.returncode, p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        valid, status, size = None, "timeout", None
    return {"kval_valid": valid, "kval_status": status, "kval_plan_size": size,
            "kval_time": round(time.time() - t, 3)}


def check_files(binary: Path, domain: str, problem: str, timeout: float = 600) -> dict:
    p = subprocess.run(_cmd(binary) + [domain, problem], capture_output=True, text=True, timeout=timeout)
    valid, status = classify_parse(p.returncode, p.stdout + p.stderr)
    return {"kval_valid": valid, "kval_status": status}
