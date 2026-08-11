"""Freeze test for the PlanBench-WT prompt apparatus (planbench/engine.py).

The _PB_* constants carry a "FREEZE STATUS: v2 FROZEN by Omer 2026-08-01"
banner: the prereg (development/planbench/planbench_wt_prereg.md §10-R,
restart record 1) quotes the scaffold text verbatim, and any change voids the
affected cells and forces a paid restart. Until this file existed nothing
enforced that — tests/test_prompts.py pins the harness prompts but no test
imported planbench at all, so a reflow or "typo fix" would have shipped with a
green suite (PR #93 review finding, 2026-08-06).

Pins are sha256 over the exact frozen bytes. If one of these checks fails,
the correct fix is almost never to update the hash — it is to revert the edit
to planbench/engine.py. Update a hash ONLY alongside an explicit prereg
amendment / restart record that re-freezes new text.

Also pins the cross-file relationship the review surfaced: _PB_POLICY_TOOLS
begins with a byte-exact copy of pddl_eval.prompts.WITH_TOOLS_SYSTEM (a
constant marked "Do not edit" for v0-v10 replay). Neither side may drift
silently: an edit to WITH_TOOLS_SYSTEM breaks the prefix check here even
though test_prompts.py only smoke-checks its first sentence.

Standalone: `python3 tests/test_planbench_prompts.py` (also run by verify.sh).
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests._helpers import TestResults  # noqa: E402

from pddl_eval.prompts import WITH_TOOLS_SYSTEM  # noqa: E402


def _load_engine():
    """Import planbench/engine.py without needing anthropic/mcp installed
    (its heavy imports are lazy; module level is stdlib-only)."""
    path = Path(__file__).parent.parent / "planbench" / "engine.py"
    spec = importlib.util.spec_from_file_location("planbench_engine", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# Frozen v2 apparatus (2026-08-01). See the module docstring before touching.
FROZEN = {
    "_PB_POLICY_TOOLS": (
        383,
        "155c50edd2dc6c19f9c041db9ff837aeee1477a7a998262a373eec31b97a8b82",
    ),
    "_PB_POLICY_NOTOOLS": (
        207,
        "8112f65f2d3b28848c54c8068bd80f9c62c3aa33c3917b32bb430bd39a188beb",
    ),
    "_PB_SHARED_T1_FORMAT": (
        504,
        "b5b661896fb7ce3e02a7437deb9f39707be1dd9d284616b3131bdf191b17c219",
    ),
}
FROZEN_SCAFFOLDS = {
    True: "61e8b86d60b11f8426509809a522e645b7e3a499685fbb54248ed1ad26a6bec8",
    False: "b2caf1a2048666d05384a050085e4041f6bd05275970b16e7e033ad9df5bdf10",
}


def test_frozen_constants(r: TestResults, eng) -> None:
    for name, (length, digest) in FROZEN.items():
        val = getattr(eng, name)
        r.check_eq(f"{name} length", len(val), length)
        r.check_eq(f"{name} sha256", _sha(val), digest)


def test_frozen_scaffolds(r: TestResults, eng, monkey_env) -> None:
    # Composed scaffolds (policy + shared clause) — what actually goes on the
    # wire as `system`. Run with PDDL_COPILOT_TASK unset/t1 so the t1-only
    # guard admits the call.
    for task in ("", "t1"):
        monkey_env("PDDL_COPILOT_TASK", task)
        for with_tools, digest in FROZEN_SCAFFOLDS.items():
            r.check_eq(
                f"_pb_scaffold(with_tools={with_tools}) sha256 (task={task!r})",
                _sha(eng._pb_scaffold(with_tools)),
                digest,
            )
    # Declared asymmetry (amendment N): arm A is exactly 176 chars longer,
    # and that difference IS the treatment.
    r.check_eq(
        "declared +176-char treatment asymmetry",
        len(eng._PB_POLICY_TOOLS) - len(eng._PB_POLICY_NOTOOLS),
        176,
    )


def test_cross_file_prefix(r: TestResults, eng) -> None:
    r.check(
        "_PB_POLICY_TOOLS starts with WITH_TOOLS_SYSTEM (byte-exact copy; "
        "neither constant may drift alone)",
        eng._PB_POLICY_TOOLS.startswith(WITH_TOOLS_SYSTEM),
        detail="prefix relation broken — one side was edited",
    )


def test_t1_only_guard(r: TestResults, eng, monkey_env) -> None:
    # The scaffold demands a [PLAN] block; any non-t1 task must refuse loudly
    # (SystemExit — NOT Exception, so the dispatch's blanket handler cannot
    # swallow it into a full run of empty answers).
    monkey_env("PDDL_COPILOT_TASK", "t3")
    try:
        eng._pb_scaffold(True)
        r.check("t1-only guard fires on t3", False, detail="no SystemExit")
    except SystemExit:
        r.check("t1-only guard fires on t3", True)
    except Exception as exc:  # pragma: no cover - wrong exception class
        r.check("t1-only guard fires on t3", False, detail=f"raised {exc!r}")


def main() -> None:
    import os

    r = TestResults("planbench WT prompt freeze")
    eng = _load_engine()

    saved = os.environ.get("PDDL_COPILOT_TASK")

    def monkey_env(key: str, value: str) -> None:
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)

    try:
        test_frozen_constants(r, eng)
        test_frozen_scaffolds(r, eng, monkey_env)
        test_cross_file_prefix(r, eng)
        test_t1_only_guard(r, eng, monkey_env)
    finally:
        if saved is None:
            os.environ.pop("PDDL_COPILOT_TASK", None)
        else:
            os.environ["PDDL_COPILOT_TASK"] = saved
    r.report_and_exit()


if __name__ == "__main__":
    main()
