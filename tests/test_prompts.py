"""Property tests for the sweep-5 prompt bank.

Enforces the design-doc §3.5 invariants on the templates and system
prompts in `pddl_eval/prompts.py`. Failing a property here means the
prompt bank drifted from the design — fix the prompt, not the test.

Run standalone: `python3 tests/test_prompts.py`
Or via the shell wrapper: `bash tests/verify.sh`
"""

import re
import sys
from pathlib import Path

# Make pddl_eval importable when run from the tests directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval.prompts import (
    ACTIVE_PROMPT_VARIANTS,
    PROMPT_TEMPLATES,
    PROMPT_TEMPLATES_TOOLS_OVERRIDE,
    STEERED_VARIANTS,
    WITH_TOOLS_SYSTEM,
    WITH_TOOLS_SYSTEM_BY_TASK,
    WITHOUT_TOOLS_SYSTEM,
    WITHOUT_TOOLS_SYSTEM_BY_TASK,
)
from tests._helpers import TestResults


TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
NEUTRAL_INDICES = (11, 12, 13)
STEERED_INDICES = (14, 15, 16)
# Pair v14↔v11, v15↔v12, v16↔v13 by offset 3.
PAIR_OFFSET = 3

# Substrings that must NEVER appear in any sweep-5 prompt or system text —
# they reference harness mechanics the model can't see (verbose=, save_plan,
# stripped from schema) or tools that aren't in the runtime tool surface
# (parser plugin not loaded; legacy polymorphic validator name retired).
HARNESS_MISMATCHED = (
    "verbose=",
    "save_plan",
    "get_trajectory",
    "check_applicable",
    "inspect_domain",
    "inspect_problem",
    "normalize_pddl",
    "validate_pddl_syntax",
)


# ---------------------------------------------------------------------------
# Pure-append property: every steered prompt is its paired neutral prompt
# with a single inserted directive (one sentence, no other edits).
# ---------------------------------------------------------------------------


def _split_insert(neutral: str, steered: str) -> tuple[bool, str, str]:
    """Return (is_pure_insert, inserted_text, diagnostic).

    True when steered is the neutral with a contiguous block inserted at
    SOME position, and the bytes before / after the insertion match the
    neutral byte-for-byte. The inserted block must contain exactly one
    period (sentence terminator) and must not contain a paragraph break.
    """
    if len(steered) <= len(neutral):
        return False, "", f"steered len {len(steered)} <= neutral len {len(neutral)}"
    if not steered.startswith(""):  # trivial — always true
        pass
    # Find the first divergence position.
    p = 0
    while p < len(neutral) and p < len(steered) and neutral[p] == steered[p]:
        p += 1
    insert_len = len(steered) - len(neutral)
    inserted = steered[p:p + insert_len]
    # The remainder after the inserted block must equal the neutral suffix.
    if steered[p + insert_len:] != neutral[p:]:
        return False, inserted, (
            f"suffix mismatch at p={p}: "
            f"steered_suffix={steered[p + insert_len:p + insert_len + 30]!r} vs "
            f"neutral_suffix={neutral[p:p + 30]!r}"
        )
    if inserted.count(".") != 1:
        return False, inserted, (
            f"inserted has {inserted.count('.')} periods, expected 1: "
            f"{inserted!r}"
        )
    if "\n\n" in inserted:
        return False, inserted, (
            f"inserted contains paragraph break: {inserted!r}"
        )
    return True, inserted, ""


def test_pure_append_property(r: TestResults):
    """v14/v15/v16 differ from v11/v12/v13 by exactly one inserted sentence."""
    for task in TASKS:
        override = PROMPT_TEMPLATES_TOOLS_OVERRIDE[task]
        base = PROMPT_TEMPLATES[task]
        for k in range(3):
            neutral_idx = 11 + k
            steered_idx = 14 + k
            r.check(
                f"{task} v{steered_idx} exists in override",
                steered_idx in override,
            )
            if steered_idx not in override:
                continue
            neutral = base[neutral_idx]
            steered = override[steered_idx]
            ok, inserted, diag = _split_insert(neutral, steered)
            r.check(
                f"{task} v{steered_idx} is pure-append of v{neutral_idx}",
                ok,
                diag if not ok else f"inserted={inserted!r}",
            )


# ---------------------------------------------------------------------------
# VERDICT trailer presence on every validate_* prompt (neutral + steered).
# ---------------------------------------------------------------------------


def test_verdict_trailer(r: TestResults):
    """All validate_* templates contain the VERDICT trailer exactly once."""
    trailer = "VERDICT: VALID or VERDICT: INVALID"
    for task in ("validate_domain", "validate_problem", "validate_plan"):
        base = PROMPT_TEMPLATES[task]
        for idx in NEUTRAL_INDICES:
            count = base[idx].count(trailer)
            r.check_eq(f"{task} v{idx} trailer count", count, 1)
        for idx in STEERED_INDICES:
            steered = PROMPT_TEMPLATES_TOOLS_OVERRIDE[task][idx]
            count = steered.count(trailer)
            r.check_eq(f"{task} v{idx} trailer count", count, 1)


# ---------------------------------------------------------------------------
# simulate wire-format example: each simulate template contains a
# {step, action, state{boolean, numeric}} JSON skeleton.
# ---------------------------------------------------------------------------


def test_simulate_wire_format(r: TestResults):
    """All simulate templates carry the wire-format JSON example."""
    required = ('"step":', '"action":', '"state":', '"boolean":', '"numeric":')
    base = PROMPT_TEMPLATES["simulate"]
    for idx in NEUTRAL_INDICES:
        for token in required:
            r.check(
                f"simulate v{idx} contains {token}",
                token in base[idx],
            )
    override = PROMPT_TEMPLATES_TOOLS_OVERRIDE["simulate"]
    for idx in STEERED_INDICES:
        for token in required:
            r.check(
                f"simulate v{idx} contains {token}",
                token in override[idx],
            )


# ---------------------------------------------------------------------------
# solve action example: every solve template has at least one parenthesised
# action example from the blocksworld family (pick-up, unstack, stack).
# ---------------------------------------------------------------------------


def test_solve_action_example(r: TestResults):
    """Each solve template includes a parenthesised PDDL action example."""
    examples = ("`(pick-up a)`", "`(unstack a b)`", "`(stack a b)`")
    base = PROMPT_TEMPLATES["solve"]
    for idx in NEUTRAL_INDICES:
        has_example = any(ex in base[idx] for ex in examples)
        r.check(f"solve v{idx} has action example", has_example,
                f"first 200 chars: {base[idx][:200]!r}")
    override = PROMPT_TEMPLATES_TOOLS_OVERRIDE["solve"]
    for idx in STEERED_INDICES:
        has_example = any(ex in override[idx] for ex in examples)
        r.check(f"solve v{idx} has action example", has_example,
                f"first 200 chars: {override[idx][:200]!r}")


# ---------------------------------------------------------------------------
# No harness-mismatched content anywhere in the sweep-5 surface.
# ---------------------------------------------------------------------------


def test_no_harness_mismatched_content(r: TestResults):
    """Templates + system prompts must not reference removed/stripped surface."""
    for task in TASKS:
        for idx in NEUTRAL_INDICES:
            for needle in HARNESS_MISMATCHED:
                r.check(
                    f"{task} v{idx} does not contain {needle!r}",
                    needle not in PROMPT_TEMPLATES[task][idx],
                )
        for idx in STEERED_INDICES:
            steered = PROMPT_TEMPLATES_TOOLS_OVERRIDE[task][idx]
            for needle in HARNESS_MISMATCHED:
                r.check(
                    f"{task} v{idx} (override) does not contain {needle!r}",
                    needle not in steered,
                )
        for needle in HARNESS_MISMATCHED:
            r.check(
                f"WITH_TOOLS_SYSTEM_BY_TASK[{task}] does not contain {needle!r}",
                needle not in WITH_TOOLS_SYSTEM_BY_TASK[task],
            )
            r.check(
                f"WITHOUT_TOOLS_SYSTEM_BY_TASK[{task}] does not contain {needle!r}",
                needle not in WITHOUT_TOOLS_SYSTEM_BY_TASK[task],
            )


# ---------------------------------------------------------------------------
# System-prompt parity: both WITH and WITHOUT per-task dicts share their
# first sentence and have the same sentence count (3) per task.
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r"[.!?]\s|[.!?]$")


def _count_sentences(text: str) -> int:
    """Count sentence-end punctuation followed by whitespace or end-of-string.

    Periods inside tokens like 'arXiv:2509.12987' (period followed by a
    digit) are NOT counted as sentence ends.
    """
    return len(_SENTENCE_RE.findall(text))


def _first_sentence(text: str) -> str:
    """Return the first sentence (everything up to and including the first
    sentence-end punctuation followed by whitespace or end-of-string)."""
    m = _SENTENCE_RE.search(text)
    if m is None:
        return text
    return text[:m.end()].rstrip()


def test_system_prompt_parity(r: TestResults):
    """For each task, WITH and WITHOUT share the role-framing first sentence
    and both have exactly 3 sentences."""
    for task in TASKS:
        with_text = WITH_TOOLS_SYSTEM_BY_TASK[task]
        without_text = WITHOUT_TOOLS_SYSTEM_BY_TASK[task]
        r.check_eq(
            f"{task} WITH sentence count",
            _count_sentences(with_text),
            3,
        )
        r.check_eq(
            f"{task} WITHOUT sentence count",
            _count_sentences(without_text),
            3,
        )
        r.check_eq(
            f"{task} shared first sentence",
            _first_sentence(with_text),
            _first_sentence(without_text),
        )


# ---------------------------------------------------------------------------
# Configuration constants: ACTIVE / STEERED match the design.
# ---------------------------------------------------------------------------


def test_config_constants(r: TestResults):
    r.check_eq(
        "ACTIVE_PROMPT_VARIANTS",
        tuple(ACTIVE_PROMPT_VARIANTS),
        (11, 12, 13, 14, 15, 16),
    )
    r.check_eq(
        "STEERED_VARIANTS",
        STEERED_VARIANTS,
        frozenset({14, 15, 16}),
    )
    # WITH/WITHOUT_TOOLS_SYSTEM_BY_TASK cover every task.
    r.check_eq(
        "WITH_TOOLS_SYSTEM_BY_TASK keys",
        sorted(WITH_TOOLS_SYSTEM_BY_TASK.keys()),
        sorted(TASKS),
    )
    r.check_eq(
        "WITHOUT_TOOLS_SYSTEM_BY_TASK keys",
        sorted(WITHOUT_TOOLS_SYSTEM_BY_TASK.keys()),
        sorted(TASKS),
    )
    # Legacy flat constants preserved byte-stable (smoke check on prefix
    # only — full byte-equality lives in git history if anyone ever needs
    # to diff against a specific commit).
    r.check(
        "WITH_TOOLS_SYSTEM legacy preserved",
        WITH_TOOLS_SYSTEM.startswith(
            "You are a PDDL planning assistant with access to planning tools."
        ),
    )
    r.check(
        "WITHOUT_TOOLS_SYSTEM legacy preserved",
        WITHOUT_TOOLS_SYSTEM.startswith("You are a PDDL planning assistant."),
    )


# ---------------------------------------------------------------------------
# Emit-skip gate: (no-tools, v ∈ STEERED_VARIANTS) cells are skipped at emit
# unless --include-no-tools-steered is on. We probe the runner's _emit_job
# closure indirectly by exercising run_single_task_experiment with a tiny
# fixture, capturing the emitted (with_tools, prompt_variant) pairs under
# both flag values.
# ---------------------------------------------------------------------------


def test_emit_skip_gate(r: TestResults):
    """The (no-tools, steered) cells skip under default; emit under control flag."""
    import asyncio
    from pddl_eval import runner as runner_mod
    from pddl_eval.runner import run_single_task_experiment, TaskResult

    captured: list[tuple[bool, int]] = []

    async def stub_evaluate_one(
        client, model, task, domain_name, domain_pddl,
        problem_name, problem_pddl, prompt_variant, with_tools,
        mcp, gt, **kwargs,
    ):
        captured.append((with_tools, prompt_variant))
        return TaskResult(
            model=model, task=task, domain_name=domain_name,
            problem_name=problem_name, prompt_variant=prompt_variant,
            with_tools=with_tools, success=True,
            tool_filter=kwargs.get("tool_filter", "all"),
            prompt_style=kwargs.get("prompt_style", "minimal"),
            plan_label=kwargs.get("plan_label", ""),
        )

    original = runner_mod.evaluate_one
    runner_mod.evaluate_one = stub_evaluate_one
    try:
        domains = {
            "d1": {"domain": "(d)", "problems": {"p1": "(p)"}, "type": "test"},
        }
        ground_truth = {"d1": {"p1": {}}}

        # Run 1: default (include_no_tools_steered=False) — main sweep.
        captured.clear()
        asyncio.run(run_single_task_experiment(
            client=None, models=["m"], tasks=["solve"], domains=domains,
            ground_truth=ground_truth, mcp=None, num_variants=6,
            conditions="both", concurrency=1,
        ))
        pairs_main = sorted(set(captured))
        # solve under both conditions × 6 variants = 12 possible pairs.
        # Skip gate removes (False, 14), (False, 15), (False, 16) → expect 9.
        r.check_eq(
            "main sweep: 9 (with_tools,pv) pairs emitted",
            len(pairs_main),
            9,
        )
        for pv in (14, 15, 16):
            r.check(
                f"main sweep: (False, v{pv}) NOT emitted",
                (False, pv) not in pairs_main,
            )
        for pv in (11, 12, 13):
            r.check(
                f"main sweep: (False, v{pv}) IS emitted",
                (False, pv) in pairs_main,
            )
            r.check(
                f"main sweep: (True, v{pv}) IS emitted",
                (True, pv) in pairs_main,
            )
        for pv in (14, 15, 16):
            r.check(
                f"main sweep: (True, v{pv}) IS emitted",
                (True, pv) in pairs_main,
            )

        # Run 2: control (include_no_tools_steered=True) — sweep-5 control.
        captured.clear()
        asyncio.run(run_single_task_experiment(
            client=None, models=["m"], tasks=["solve"], domains=domains,
            ground_truth=ground_truth, mcp=None, num_variants=6,
            conditions="both", concurrency=1,
            include_no_tools_steered=True,
        ))
        pairs_control = sorted(set(captured))
        r.check_eq(
            "control sweep: 12 (with_tools,pv) pairs emitted",
            len(pairs_control),
            12,
        )
        for pv in (11, 12, 13, 14, 15, 16):
            r.check(
                f"control: (False, v{pv}) IS emitted",
                (False, pv) in pairs_control,
            )
            r.check(
                f"control: (True, v{pv}) IS emitted",
                (True, pv) in pairs_control,
            )
    finally:
        runner_mod.evaluate_one = original


def main():
    r = TestResults("test_prompts")
    test_pure_append_property(r)
    test_verdict_trailer(r)
    test_simulate_wire_format(r)
    test_solve_action_example(r)
    test_no_harness_mismatched_content(r)
    test_system_prompt_parity(r)
    test_config_constants(r)
    test_emit_skip_gate(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
