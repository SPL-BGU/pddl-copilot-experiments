"""Pure-text PDDL mutation primitives for fixture generation.

Each mutator takes a string and returns a (possibly equal) string. None
of these guarantee the result is invalid — `tools/build_fixtures.py`
validates each output via MCP and discards mutations the validator
accepts. The taxonomy mirrors `domains/README.md` (post-PR-3) and
FRAMEWORK_EXTENSION_PLAN.md §3.3.4 / §3.3.5.

Domain-agnostic: all mutators operate on PDDL text without parsing the
type system or action signatures. This loses some of the spec's nuance
(e.g. "swap-args on a commutative-LOOKING but asymmetric action" reduces
to "swap args of any action with ≥2 args") but it keeps the generator
simple. Per spec §3.3.4 a category that can't author a domain-specific
mutant falls back to a different category — handled at the build_fixtures
level, not here.
"""

from __future__ import annotations

import random
import re

# ---------------------------------------------------------------------------
# Plan mutations
# ---------------------------------------------------------------------------


def plan_truncate(plan_text: str, n_drop: int = 1, rng: random.Random | None = None) -> str:
    """Drop the last `n_drop` action lines.

    Triggers spec category 2 (goal-not-achieved-by-truncation). Returns the
    original text when the plan is too short to drop anything.
    """
    lines = [l for l in plan_text.splitlines() if l.strip()]
    if len(lines) <= n_drop:
        return plan_text
    return "\n".join(lines[:-n_drop]) + "\n"


def plan_drop_step_k(plan_text: str, k: int | None = None, rng: random.Random | None = None) -> str:
    """Drop the kth action line (0-indexed).

    Triggers spec category 1 (precondition-fails-at-step-k) — removing a
    mid-plan action typically breaks the next action's precondition.
    Also approximates category 4 (missing-action) since the dropped step
    is required mid-plan. When k is None, picks a non-final index.
    """
    lines = plan_text.splitlines()
    action_idxs = [i for i, l in enumerate(lines) if l.strip().startswith("(")]
    if len(action_idxs) < 2:
        return plan_text
    if k is None:
        rng = rng or random.Random(0)
        # Drop a non-final action so a precondition failure surfaces.
        k = rng.choice(action_idxs[:-1])
    elif k not in action_idxs:
        return plan_text
    new_lines = lines[:k] + lines[k + 1:]
    suffix = "\n" if plan_text.endswith("\n") else ""
    return "\n".join(new_lines) + suffix


def plan_swap_args(plan_text: str, k: int | None = None, rng: random.Random | None = None) -> str:
    """Swap the first two arguments of the kth action when it has ≥2 args.

    Triggers spec category 3 (swapped-arg-order). Returns the original
    text when no action has ≥2 args.
    """
    lines = plan_text.splitlines()
    rng = rng or random.Random(0)
    candidates: list[int] = []
    for i, line in enumerate(lines):
        s = line.strip()
        # Match `(action a1 a2 ...)` with at least 2 args.
        if re.match(r"\(\s*\S+\s+\S+\s+\S+", s):
            candidates.append(i)
    if not candidates:
        return plan_text
    if k is None or k not in candidates:
        k = rng.choice(candidates)
    line = lines[k]
    indent = line[: len(line) - len(line.lstrip())]
    s = line.strip()
    m = re.match(r"\(\s*(\S+)\s+(\S+)\s+(\S+)(.*?)\)\s*$", s)
    if not m:
        return plan_text
    action, a1, a2, rest = m.groups()
    swapped = f"({action} {a2} {a1}{rest})"
    lines[k] = indent + swapped
    suffix = "\n" if plan_text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def plan_duplicate_step(plan_text: str, k: int | None = None, rng: random.Random | None = None) -> str:
    """Insert a duplicate of the kth action right after it.

    Approximates spec category 5 (extra-action) — repeating most actions
    breaks the duplicate's precondition (e.g. unstacking a block twice).
    The mutation surface is broader than "no-op-equivalent insertion" but
    still produces a semantically-invalid plan with valid syntax.
    """
    lines = plan_text.splitlines()
    rng = rng or random.Random(0)
    candidates = [
        i for i, line in enumerate(lines)
        if line.strip().startswith("(") and line.strip().endswith(")")
    ]
    if not candidates:
        return plan_text
    if k is None or k not in candidates:
        k = rng.choice(candidates)
    new_lines = lines[: k + 1] + [lines[k]] + lines[k + 1:]
    suffix = "\n" if plan_text.endswith("\n") else ""
    return "\n".join(new_lines) + suffix


# ---------------------------------------------------------------------------
# Problem mutations
# ---------------------------------------------------------------------------


def problem_drop_goal(problem_text: str, rng: random.Random | None = None) -> str:
    """Strip the entire `(:goal ...)` block.

    Spec category 2 (missing :goal). The validator should reject any
    problem without a goal.
    """
    return _strip_balanced_block(problem_text, ":goal")


def problem_inject_undefined_object(
    problem_text: str,
    name: str = "undef_obj_xyz",
    rng: random.Random | None = None,
) -> str:
    """Add a fact in `:init` that references an object never declared in `:objects`.

    Spec category 1. Uses the first predicate name found inside `:init`
    so the new fact is shape-compatible at the syntax level.
    """
    init_open = re.search(r"\(:init\b", problem_text)
    if not init_open:
        return problem_text
    # Find the matching close.
    start = init_open.start()
    depth = 0
    end = -1
    for i in range(start, len(problem_text)):
        c = problem_text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return problem_text
    init_block = problem_text[start:end + 1]
    # Pull the first predicate name (skip `:init` itself).
    pred_match = re.search(r"\(\s*(\w[\w-]*)", init_block[len("(:init"):])
    if not pred_match:
        return problem_text
    pred = pred_match.group(1)
    inject = f"\n    ({pred} {name})"
    new_init = init_block[:-1] + inject + init_block[-1]
    return problem_text[:start] + new_init + problem_text[end + 1:]


def problem_corrupt_paren(problem_text: str, rng: random.Random | None = None) -> str:
    """Append an extra closing paren.

    Spec category 4. Trailing newline is preserved; the extra `)` is the
    last non-newline character.
    """
    if problem_text.endswith("\n"):
        return problem_text[:-1] + ")\n"
    return problem_text + ")"


def problem_drop_objects(problem_text: str, rng: random.Random | None = None) -> str:
    """Strip the entire `(:objects ...)` block.

    Spec category 1 (objects in :init not in :objects) — pushed to the
    extreme: ALL :init references become undefined since there are no
    declared objects. The validator must reject the result.
    """
    return _strip_balanced_block(problem_text, ":objects")


def problem_drop_init(problem_text: str, rng: random.Random | None = None) -> str:
    """Strip the entire `(:init ...)` block.

    Adjacent to category 5 (init references wrong type) — without an
    init block, the goal is not achievable from any starting state and
    validators that check init/goal consistency reject it.
    """
    return _strip_balanced_block(problem_text, ":init")


def problem_undefined_goal_predicate(
    problem_text: str,
    fake: str = "undef_pred_xyz",
    rng: random.Random | None = None,
) -> str:
    """Replace the first predicate name inside `(:goal ...)` with a fake one.

    Spec category 3 (`:goal` references undefined predicate). Targets the
    innermost predicate so an `(:and ...)` or `(:not ...)` wrapper isn't
    clobbered.
    """
    goal_open = re.search(r"\(:goal\b", problem_text)
    if not goal_open:
        return problem_text
    start = goal_open.start()
    depth = 0
    end = -1
    for i in range(start, len(problem_text)):
        c = problem_text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return problem_text
    goal_block = problem_text[start:end + 1]
    # Skip the goal connectives: `and`, `or`, `not`, `imply`, `forall`, `exists`,
    # the `:goal` keyword itself. Take the first non-connective predicate.
    connectives = {"and", "or", "not", "imply", "forall", "exists"}
    candidates = list(re.finditer(r"\(\s*([A-Za-z][\w-]*)", goal_block))
    if not candidates:
        return problem_text
    target = None
    for m in candidates[1:]:  # skip `:goal` (its leading paren is at offset 0)
        name = m.group(1)
        if name in connectives or name.startswith(":"):
            continue
        target = m
        break
    if target is None:
        return problem_text
    new_goal_block = (
        goal_block[: target.start(1)] + fake + goal_block[target.end(1):]
    )
    return problem_text[:start] + new_goal_block + problem_text[end + 1:]


# ---------------------------------------------------------------------------
# Domain mutations
# ---------------------------------------------------------------------------


def domain_corrupt_paren(domain_text: str, rng: random.Random | None = None) -> str:
    """Append an extra closing paren — guaranteed S-expression breakage."""
    if domain_text.endswith("\n"):
        return domain_text[:-1] + ")\n"
    return domain_text + ")"


def domain_undefined_predicate_in_effect(
    domain_text: str,
    fake: str = "undef_pred_xyz",
    rng: random.Random | None = None,
) -> str:
    """Inject a reference to an undefined predicate at the first `:effect` start.

    Spec domain-bug taxonomy: "effect uses undeclared predicate". The
    fake predicate goes at the head of the effect block so it appears
    inside the `(and ...)` if one is present, or directly otherwise.
    """
    m = re.search(r":effect\s*\(", domain_text)
    if not m:
        return domain_text
    pos = m.end()
    insert = f"({fake} ?x) "
    return domain_text[:pos] + insert + domain_text[pos:]


def domain_drop_predicates_block(domain_text: str, rng: random.Random | None = None) -> str:
    """Strip the `(:predicates ...)` block.

    Domain-bug taxonomy: action effects/preconditions reference predicates
    that no longer have definitions.
    """
    return _strip_balanced_block(domain_text, ":predicates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_balanced_block(text: str, header: str) -> str:
    """Find `(<header> ...)` and remove the matching balanced block.

    Returns the input unchanged when the header is absent or the
    enclosing parens don't balance (the latter shouldn't happen on a
    valid PDDL input).
    """
    pattern = re.compile(rf"\(\s*{re.escape(header)}\b")
    m = pattern.search(text)
    if not m:
        return text
    start = m.start()
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[:start] + text[i + 1:]
    return text
