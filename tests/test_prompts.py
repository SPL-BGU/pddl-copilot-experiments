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
    PROMPT_STYLES,
    PROMPT_TEMPLATES,
    PROMPT_TEMPLATES_TOOLS_OVERRIDE,
    STEERED_VARIANTS,
    WITH_TOOLS_SYSTEM,
    WITH_TOOLS_SYSTEM_BY_TASK,
    WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK,
    WITHOUT_TOOLS_SYSTEM,
    WITHOUT_TOOLS_SYSTEM_BY_TASK,
)
from tests._helpers import TestResults, make_stub_evaluate_one, stubbed_evaluate_one


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
# `--prompt-style neutral` (2026-10-02): the with-tools system prompt reduced
# to the role-framing sentence. Mirror property extended to three texts: the
# neutral entry IS the first sentence of both the WITH and the WITHOUT entry.
# ---------------------------------------------------------------------------

# Phrases that would make the neutral system prompt carry an instruction or a
# claim about tool use — the very thing the style exists to remove.
_NEUTRAL_FORBIDDEN = ("tool", "cannot reliably", "use the", "arxiv", "reasoning")

# sha256 over json.dumps([task, variant, with_tools, messages]) for every
# task × v0..v16 × {tools, no-tools} under the DEFAULT style, computed on
# origin/main (fedbeb3) before `prompt_style` reached build_messages. A change
# here means the default prompts are no longer byte-identical to the corpus.
_DEFAULT_MESSAGES_SHA256 = (
    "d11d948dfb79226d4cb215260be25821353b38557b5531861964f4c303ec0ead"
)
_FIXTURE_GT = {"plan": ["(pick_up b3)", "(stack b3 b2)"]}
_FIXTURE_DOMAIN = "(define (domain d))"
_FIXTURE_PROBLEM = "(define (problem p))"


def test_neutral_system_prompt_mirror(r: TestResults):
    """Neutral with-tools system prompt = the shared role-framing sentence."""
    r.check_eq("PROMPT_STYLES", tuple(PROMPT_STYLES), ("minimal", "neutral"))
    r.check_eq(
        "WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK keys",
        sorted(WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK.keys()),
        sorted(TASKS),
    )
    for task in TASKS:
        neutral = WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK[task]
        r.check_eq(f"{task} NEUTRAL sentence count", _count_sentences(neutral), 1)
        r.check_eq(
            f"{task} NEUTRAL == first sentence of WITH",
            neutral, _first_sentence(WITH_TOOLS_SYSTEM_BY_TASK[task]),
        )
        r.check_eq(
            f"{task} NEUTRAL == first sentence of WITHOUT",
            neutral, _first_sentence(WITHOUT_TOOLS_SYSTEM_BY_TASK[task]),
        )
        r.check(
            f"{task} NEUTRAL is a strict prefix of WITH (pure truncation)",
            WITH_TOOLS_SYSTEM_BY_TASK[task].startswith(neutral + " "),
        )
        for phrase in _NEUTRAL_FORBIDDEN:
            r.check(
                f"{task} NEUTRAL has no {phrase!r}",
                phrase not in neutral.lower(), neutral,
            )
    # The example from the design brief, pinned literally.
    r.check_eq(
        "validate_plan NEUTRAL literal",
        WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK["validate_plan"],
        "You are a PDDL validation assistant.",
    )


def test_prompt_style_threading(r: TestResults):
    """`prompt_style` changes the with-tools system turn and nothing else;
    the default is byte-identical to the pre-change prompts."""
    import hashlib
    import json
    from pddl_eval.runner import _trial_key, build_messages

    def msgs(task, pv, with_tools, **kw):
        return build_messages(task, _FIXTURE_DOMAIN, _FIXTURE_PROBLEM, pv,
                              with_tools, _FIXTURE_GT, **kw)

    # Default style: whole grid (incl. legacy v0..v10) pinned to origin/main.
    h = hashlib.sha256()
    for task in TASKS:
        for pv in range(0, 17):
            for with_tools in (True, False):
                h.update(json.dumps([task, pv, with_tools,
                                     msgs(task, pv, with_tools)],
                                    sort_keys=True).encode())
    r.check_eq("default-style messages byte-identical to origin/main",
               h.hexdigest(), _DEFAULT_MESSAGES_SHA256)

    for task in TASKS:
        for pv in ACTIVE_PROMPT_VARIANTS:
            default = msgs(task, pv, True)
            r.check_eq(f"{task} v{pv} explicit minimal == default",
                       msgs(task, pv, True, prompt_style="minimal"), default)
            neutral = msgs(task, pv, True, prompt_style="neutral")
            r.check_eq(f"{task} v{pv} neutral system turn",
                       neutral[0],
                       {"role": "system",
                        "content": WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK[task]})
            r.check_eq(f"{task} v{pv} neutral user turn unchanged",
                       neutral[1], default[1])
            r.check(f"{task} v{pv} neutral differs from minimal",
                    neutral[0] != default[0])
            # No-tools arm: the style is a with-tools-only knob.
            r.check_eq(f"{task} v{pv} no-tools unaffected by style",
                       msgs(task, pv, False, prompt_style="neutral"),
                       msgs(task, pv, False))

    # Fail loud on an unknown style and on legacy variants (no role-only form).
    for label, kwargs, pv in (("unknown style", {"prompt_style": "guided"}, 11),
                              ("neutral on legacy v5", {"prompt_style": "neutral"}, 5)):
        try:
            msgs("solve", pv, True, **kwargs)
        except ValueError:
            r.check(f"{label} rejected", True)
        else:
            r.check(f"{label} rejected", False, "no ValueError")

    # Resume keys: the style is a key coordinate, so a neutral trial can never
    # be satisfied by (or satisfy) a minimal one.
    k_min = _trial_key("m", "validate_plan", "d", "p", "v1", 11, True,
                       "off", "all", "minimal")
    k_neu = _trial_key("m", "validate_plan", "d", "p", "v1", 11, True,
                       "off", "all", "neutral")
    r.check("resume keys differ by style", k_min != k_neu)
    r.check_eq("style is the last key coordinate", k_neu[-1], "neutral")


def test_prompt_style_end_to_end(r: TestResults):
    """CLI choices → evaluate_one → result row → resume scope."""
    import asyncio
    import run_experiment as rx
    from pddl_eval.runner import evaluate_one, run_single_task_experiment

    r.check_eq("CLI --prompt-style choices", tuple(rx.PROMPT_STYLE_CHOICES),
               ("minimal", "neutral"))

    # evaluate_one sends the neutral system prompt and stamps the row.
    sent: list[list[dict]] = []

    class _Client:
        async def chat(self, **kwargs):
            sent.append([dict(m) for m in kwargs["messages"]])
            return {"message": {"role": "assistant", "content": "x",
                                "thinking": ""},
                    "done_reason": "stop", "prompt_eval_count": 1,
                    "eval_count": 1, "total_duration": 1, "eval_duration": 1}

    class _MCP:
        tools: list = []

    for style in ("minimal", "neutral"):
        sent.clear()
        res = asyncio.run(evaluate_one(
            _Client(), "m", "validate_plan", "d1", _FIXTURE_DOMAIN, "p1",
            _FIXTURE_PROBLEM, 11, True, _MCP(), {"plan_valid": True,
                                                 **_FIXTURE_GT},
            num_predict=6144, num_ctx=16384, num_ctx_thinking=16384,
            think=False, prompt_style=style,
        ))
        expected = (WITH_TOOLS_SYSTEM_NEUTRAL_BY_TASK if style == "neutral"
                    else WITH_TOOLS_SYSTEM_BY_TASK)["validate_plan"]
        r.check_eq(f"{style}: system prompt on the wire",
                   sent[0][0]["content"], expected)
        r.check_eq(f"{style}: row prompt_style", res.prompt_style, style)

    # A minimal-style trials.jsonl does not satisfy a neutral-style run: every
    # job is still emitted, and the restored minimal rows are out of scope.
    domains = {"d1": {"type": "classical", "domain": "(d)",
                      "problems": {"p1": "(p)"}}}
    ground_truth = {"d1": {"p1": {"plan": ["(a)"], "trace": []}}}
    common = dict(client=None, models=["m"], tasks=["solve"], domains=domains,
                  ground_truth=ground_truth, mcp=None, conditions="tools",
                  concurrency=1)
    with stubbed_evaluate_one(make_stub_evaluate_one()):
        minimal_rows = asyncio.run(run_single_task_experiment(**common))
    from pddl_eval.runner import _think_str, _trial_key
    restored = {
        _trial_key(x.model, x.task, x.domain_name, x.problem_name,
                   x.plan_label, x.prompt_variant, x.with_tools,
                   _think_str(None), x.tool_filter, x.prompt_style): x
        for x in minimal_rows
    }
    captured: list = []
    with stubbed_evaluate_one(make_stub_evaluate_one(captured=captured)):
        neutral_rows = asyncio.run(run_single_task_experiment(
            **common, prompt_style="neutral", restored_by_key=restored))
    r.check_eq("neutral run re-emits every job despite minimal rows on disk",
               len(captured), len(minimal_rows))
    r.check_eq("neutral run returns only neutral rows",
               {x.prompt_style for x in neutral_rows}, {"neutral"})


def test_continue_partial_seed_style_guard(r: TestResults):
    """`--continue-partial` must check the SEED's prompt style before copying.

    Seeding a neutral cell from a minimal dir used to copy first and refuse
    afterwards, leaving a dir whose trials.jsonl failed the one-style-per-dir
    guard on every resubmit.
    """
    import json
    import tempfile
    import run_experiment as rx
    from dataclasses import asdict
    from pddl_eval.runner import _trial_key
    from tests._helpers import make_stub_result

    def write_seed(dirpath: Path, style: str) -> Path:
        res = make_stub_result(model="m", task="solve", domain_name="d1",
                               problem_name="p1", prompt_variant=11,
                               with_tools=True, prompt_style=style)
        key = _trial_key("m", "solve", "d1", "p1", "", 11, True, "off",
                         "all", style)
        dirpath.mkdir(parents=True, exist_ok=True)
        p = dirpath / "trials.jsonl"
        p.write_text(json.dumps({"key": list(key), "result": asdict(res)}) + "\n")
        return p

    def exits(fn) -> str | None:
        try:
            fn()
        except SystemExit as exc:
            return str(exc.code)
        return None

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        seed_min = root / "seed_minimal"
        write_seed(seed_min, "minimal")

        # Mismatched seed: refused, and the destination is left untouched.
        dest = root / "cell_neutral" / "trials.jsonl"
        dest.parent.mkdir()
        msg = exits(lambda: rx._seed_from_partial(seed_min, dest, "neutral"))
        r.check("minimal seed refused for a neutral run",
                msg is not None and "--continue-partial seed" in msg
                and "minimal" in msg, str(msg))
        r.check("refused seed was NOT copied (no poisoned dir)",
                not dest.exists(), str(list(dest.parent.iterdir())))
        # ...so a resubmit of the same cell without the seed starts clean.
        r.check("cell dir passes the per-dir guard afterwards",
                exits(lambda: rx._refuse_other_prompt_styles(
                    rx.load_progress(dest), "neutral", dest,
                    what="--output-dir")) is None)

        # Matching seed: copied byte-for-byte (the pre-existing behaviour).
        dest_min = root / "cell_minimal" / "trials.jsonl"
        dest_min.parent.mkdir()
        r.check("minimal seed accepted for a minimal run",
                exits(lambda: rx._seed_from_partial(seed_min, dest_min,
                                                    "minimal")) is None)
        r.check_eq("matching seed copied byte-for-byte", dest_min.read_bytes(),
                   (seed_min / "trials.jsonl").read_bytes())

        # Pre-existing refusals keep their messages.
        msg = exits(lambda: rx._seed_from_partial(root / "nope", dest, "minimal"))
        r.check("missing seed still refused",
                msg is not None and msg.endswith("not found"), str(msg))
        msg = exits(lambda: rx._seed_from_partial(seed_min, dest_min, "minimal"))
        r.check("non-empty destination still refused",
                msg is not None and "already non-empty" in msg, str(msg))

        # Per-dir guard on an existing output dir, both directions.
        msg = exits(lambda: rx._refuse_other_prompt_styles(
            rx.load_progress(dest_min), "neutral", dest_min, what="--output-dir"))
        r.check("existing minimal dir refused for a neutral run",
                msg is not None and "--output-dir" in msg, str(msg))
        seed_neu = root / "seed_neutral"
        p_neu = write_seed(seed_neu, "neutral")
        msg = exits(lambda: rx._refuse_other_prompt_styles(
            rx.load_progress(p_neu), "minimal", p_neu, what="--output-dir"))
        r.check("existing neutral dir refused for a minimal run",
                msg is not None and "neutral" in msg, str(msg))


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
    from pddl_eval.runner import run_single_task_experiment

    captured: list[tuple[bool, int]] = []

    with stubbed_evaluate_one(make_stub_evaluate_one(captured=captured)):
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


def main():
    r = TestResults("test_prompts")
    test_pure_append_property(r)
    test_verdict_trailer(r)
    test_simulate_wire_format(r)
    test_solve_action_example(r)
    test_no_harness_mismatched_content(r)
    test_system_prompt_parity(r)
    test_neutral_system_prompt_mirror(r)
    test_prompt_style_threading(r)
    test_prompt_style_end_to_end(r)
    test_continue_partial_seed_style_guard(r)
    test_config_constants(r)
    test_emit_skip_gate(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
