#!/usr/bin/env python3
"""Idempotent in-place edits to make a fresh LLMs-Planning checkout host
the ``pddl_copilot__<backend>__<model>`` engine.

Anchored on stable strings (not line numbers):

1. ``utils/__init__.py`` — tolerate missing ``OPENAI_API_KEY``.
2. ``utils/llm_utils.py`` — tolerant imports of transformers / openai.
3. ``utils/llm_utils.py`` — dispatch branch for ``pddl_copilot__*`` engines.
4. ``response_generation.py`` — fix the self-destructing ``--specific_instances`` filter.
5. ``response_evaluation.py`` — grader robustness (3 sub-edits): (A) the t3
   verification parser tolerates responses that omit the ``plan is (in)valid``
   verdict (non-adherence → ``correct_binary=False`` instead of a ``KeyError``
   that crashes the whole eval); (B) the LLM parse is wrapped so a malformed
   response can't crash the cell mid-loop; (C) ``load_json`` tolerates a MISSING
   response file (all-empty tools cell) instead of a bare ``assert`` that exits
   rc=1 and aborts the cell.

Each edit checks for both the original anchor (apply) and the patched form
(skip). Exits 1 if neither is found — that means upstream moved and the
anchor needs updating.

Usage:
    python3 apply_patches.py <path-to-LLMs-Planning>
"""

from __future__ import annotations

import sys
from pathlib import Path


PATCH_MARKER = "pddl-copilot patch"


def patch_init(pb_root: Path) -> None:
    f = pb_root / "plan-bench" / "utils" / "__init__.py"
    text = f.read_text()
    needle = 'openai.api_key = os.environ["OPENAI_API_KEY"]'
    replace = (
        'openai.api_key = os.environ.get("OPENAI_API_KEY", "")'
        f"  # {PATCH_MARKER}: tolerate missing key"
    )
    if PATCH_MARKER in text:
        print(f"[patch] {f.relative_to(pb_root)}: already applied")
        return
    if needle not in text:
        sys.exit(f"[patch] {f.relative_to(pb_root)}: anchor not found")
    f.write_text(text.replace(needle, replace))
    print(f"[patch] {f.relative_to(pb_root)}: tolerated openai.api_key")


def patch_llm_utils(pb_root: Path) -> None:
    f = pb_root / "plan-bench" / "utils" / "llm_utils.py"
    text = f.read_text()

    if PATCH_MARKER in text:
        print(f"[patch] {f.relative_to(pb_root)}: already applied")
        return

    # --- Edit 1: tolerant imports at top of file ---
    old_header = (
        "from transformers import StoppingCriteriaList, StoppingCriteria\n"
        "import openai\n"
        "import os\n"
        'openai.api_key = os.environ["OPENAI_API_KEY"]\n'
    )
    new_header = (
        f"# {PATCH_MARKER}: tolerant imports (see planbench/apply_patches.py)\n"
        "import os\n"
        "try:\n"
        "    from transformers import StoppingCriteriaList, StoppingCriteria  # noqa: F401\n"
        "except ImportError:\n"
        "    StoppingCriteriaList = StoppingCriteria = None\n"
        "try:\n"
        "    import openai\n"
        "\n"
        '    openai.api_key = os.environ.get("OPENAI_API_KEY", "")\n'
        "except ImportError:\n"
        "    openai = None\n"
    )
    if old_header not in text:
        sys.exit(f"[patch] {f.relative_to(pb_root)}: header anchor not found")
    text = text.replace(old_header, new_header)

    # --- Edit 2: dispatch branch before the final ``else`` in send_query ---
    # Anchor on the unique combination "    else:" + the openai.Completion line
    # below it, so we don't match `if/elif/else` elsewhere.
    marker = "    else:\n        try:\n            response = openai.Completion.create("
    dispatch = (
        "    elif engine.startswith('pddl_copilot__'):\n"
        f"        # {PATCH_MARKER}: route to our local/remote model fleet.\n"
        "        import sys, pathlib\n"
        "        sys.path.insert(\n"
        "            0,\n"
        "            os.environ.get(\n"
        "                'PDDL_COPILOT_EXPERIMENTS_ROOT',\n"
        "                str(pathlib.Path(__file__).resolve().parents[3]),\n"
        "            ),\n"
        "        )\n"
        "        from planbench.engine import pddl_copilot_send_query\n"
        "        return pddl_copilot_send_query(\n"
        "            query, engine, max_tokens, model=model, stop=stop\n"
        "        )\n"
    )
    if marker not in text:
        sys.exit(f"[patch] {f.relative_to(pb_root)}: dispatch anchor not found")
    text = text.replace(marker, dispatch + marker)

    f.write_text(text)
    print(f"[patch] {f.relative_to(pb_root)}: tolerant imports + pddl_copilot dispatch")


def patch_response_generation(pb_root: Path) -> None:
    """Fix the self-destructing --specific_instances filter.

    Upstream's loop pops matched ids off the input list, so once the LAST
    match is consumed `if len(specified_instances) > 0:` flips False and
    every remaining instance falls through to send_query (smoke 17628268,
    2026-05-18: filter for [2, 3, 4] correctly processed those 3 then ran
    all 497 remaining BW instances). Snapshot to a set at function entry
    and use immutable membership tests in the loop.
    """
    f = pb_root / "plan-bench" / "response_generation.py"
    text = f.read_text()
    if PATCH_MARKER in text:
        print(f"[patch] {f.relative_to(pb_root)}: already applied")
        return

    init_anchor = (
        "    def get_responses(self, task_name, specified_instances = [], run_till_completion=False):\n"
        "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n"
    )
    init_new = (
        "    def get_responses(self, task_name, specified_instances = [], run_till_completion=False):\n"
        f"        # {PATCH_MARKER}: snapshot to a set so the inner filter doesn't\n"
        "        # mutate state — the upstream `.remove()` pattern emptied the list\n"
        "        # after the last match, flipping `if len(...) > 0` False and letting\n"
        "        # every remaining instance fall through to send_query.\n"
        "        _specified_instances_set = set(specified_instances or [])\n"
        "        output_dir = f\"responses/{self.data['domain_name']}/{self.engine}/\"\n"
    )
    if init_anchor not in text:
        sys.exit(f"[patch] {f.relative_to(pb_root)}: get_responses init anchor not found")
    text = text.replace(init_anchor, init_new)

    old_filter = (
        "                if len(specified_instances) > 0:\n"
        "                    if instance['instance_id'] not in specified_instances:\n"
        "                        continue\n"
        "                    else:\n"
        "                        specified_instances.remove(instance['instance_id'])                   \n"
    )
    new_filter = (
        f"                # {PATCH_MARKER}: see _specified_instances_set above.\n"
        "                if _specified_instances_set and instance['instance_id'] not in _specified_instances_set:\n"
        "                    continue\n"
    )
    if old_filter not in text:
        sys.exit(f"[patch] {f.relative_to(pb_root)}: filter-block anchor not found")
    text = text.replace(old_filter, new_filter)

    f.write_text(text)
    print(f"[patch] {f.relative_to(pb_root)}: filter no-mutate fix")


def patch_response_evaluation(pb_root: Path) -> None:
    """Make the t3 verification grader robust to non-adherent responses.

    ``evaluate_verification`` compares ``parsed_llm_response['valid']`` to the
    ground truth's, but ``parse_output`` only sets ``'valid'`` when the
    response contains the literal phrase ``plan is valid`` / ``plan is
    invalid``. Models that don't follow PlanBench's verdict template (e.g.
    qwen3.5 emits free-form prose) leave ``'valid'`` unset, so the comparison
    raises ``KeyError`` and crashes the ENTIRE t3/config evaluation — zero
    numbers even for the adherent instances in the same file (sweep
    18003827-18003866, 2026-06-05: every t3 cell crashed).

    Fix: default ``'valid'`` to ``None`` at the end of ``parse_output``. A
    ``None`` verdict never equals the ground truth's ``True``/``False``, so a
    non-adherent instance scores ``correct_binary=False`` ("no verdict ->
    incorrect"). Comparability-preserving: responses that DO emit the verdict
    are graded exactly as upstream — and exactly as PlanBench's published
    gpt-4 baseline was (gpt-4 followed the template, so it never hit this).
    The verdict-emission rate is recoverable post-hoc from
    ``extracted_llm_plan['valid']`` (``None`` => the model emitted no verdict).
    """
    f = pb_root / "plan-bench" / "response_evaluation.py"
    text = f.read_text()
    did = []

    # --- Edit A: default 'valid' to None at the end of parse_output ---
    # A response with no "plan is (in)valid" phrase otherwise leaves 'valid'
    # unset → evaluate_verification KeyErrors and crashes the whole t3 eval.
    sentinel_a = "output_dict.setdefault('valid', None)"
    if sentinel_a not in text:
        anchor_a = (
            "                    precond_act_flag = False\n"
            "\n"
            "        return output_dict\n"
        )
        new_a = (
            "                    precond_act_flag = False\n"
            "\n"
            f"        # {PATCH_MARKER}: guarantee 'valid' is always set so a response with\n"
            "        # no \"plan is (in)valid\" verdict (model non-adherence) scores\n"
            "        # correct_binary=False instead of KeyError-crashing the whole t3 eval.\n"
            "        # Comparability-preserving: emitters keep their True/False verdict; a\n"
            "        # None verdict never equals the ground truth's. Emission rate is\n"
            "        # recoverable from extracted_llm_plan['valid'] (None => non-adherent).\n"
            "        output_dict.setdefault('valid', None)\n"
            "        return output_dict\n"
        )
        if anchor_a not in text:
            sys.exit(f"[patch] {f.relative_to(pb_root)}: parse_output return anchor not found")
        text = text.replace(anchor_a, new_a)
        did.append("'valid' default")

    # --- Edit B: tolerate parser exceptions on the LLM response ---
    # parse_output can crash on a malformed non-adherent action line (e.g.
    # logistics text_to_plan IndexError objs[1] on a bad load/unload claim,
    # qwen3.5:9B t3/logistics, sweep 18003849). One bad response otherwise
    # kills the entire cell mid-loop. Wrap the LLM parse so a crash scores the
    # instance no-verdict → correct_binary=False (the ground-truth parse stays
    # unwrapped — a GT crash is a real bug worth surfacing).
    sentinel_b = "parsed_llm_response = {'valid': None}"
    if sentinel_b not in text:
        anchor_b = (
            "                parsed_llm_response = self.parse_output(problem.actions, llm_response)\n"
        )
        new_b = (
            f"                # {PATCH_MARKER}: tolerate parser crashes on malformed responses.\n"
            "                try:\n"
            "                    parsed_llm_response = self.parse_output(problem.actions, llm_response)\n"
            "                except Exception:\n"
            "                    parsed_llm_response = {'valid': None}\n"
        )
        if anchor_b not in text:
            sys.exit(f"[patch] {f.relative_to(pb_root)}: parsed_llm_response anchor not found")
        text = text.replace(anchor_b, new_b)
        did.append("LLM-parse try/except")

    # --- Edit C: tolerate a MISSING response file in load_json ---
    # load_json bare-asserts the response file exists, so an eval invocation
    # crashes (AssertionError, rc=1) for any (task,config) cell where
    # response_generation produced NO file — which happens when every targeted
    # instance truncated to empty (the tools arm's dominant small-model failure
    # mode: NL->PDDL formalization wall -> retry loop -> empty). One all-empty
    # cell would otherwise mark the whole job OVERALL_RC=1 and emit a traceback.
    # Fix: fall through to an empty instance set so the eval records a no-data
    # cell and the serial task loop continues. Safe under --verbose False (the
    # only divide-by-total_instances path is verbose-gated). build_table reads
    # the empty cell as "-" (no data); cells that DID generate some response are
    # unaffected and graded exactly as upstream.
    sentinel_c = "[eval] no response file for"
    if sentinel_c not in text:
        anchor_c = (
            "        else:\n"
            "            assert os.path.exists(response_dir+f\"{task_name}.json\")\n"
            "            load_dir = response_dir\n"
        )
        new_c = (
            "        elif os.path.exists(response_dir+f\"{task_name}.json\"):\n"
            "            load_dir = response_dir\n"
            "        else:\n"
            f"            # {PATCH_MARKER}: tolerate a missing response file instead of the\n"
            "            # bare assert that crashes the whole eval (rc=1) for an all-empty\n"
            "            # (task,config) cell. Return an empty instance set so the serial\n"
            "            # task loop records a no-data cell and continues.\n"
            "            print(f\"[eval] no response file for {task_name} under {response_dir}; treating as empty\")\n"
            "            return {\"instances\": []}\n"
        )
        if anchor_c not in text:
            sys.exit(f"[patch] {f.relative_to(pb_root)}: load_json assert anchor not found")
        text = text.replace(anchor_c, new_c)
        did.append("load_json missing-file")

    if not did:
        print(f"[patch] {f.relative_to(pb_root)}: already applied")
        return
    f.write_text(text)
    print(f"[patch] {f.relative_to(pb_root)}: t3 grader robustness ({', '.join(did)})")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: apply_patches.py <LLMs-Planning checkout>")
    pb_root = Path(sys.argv[1]).resolve()
    if not (pb_root / "plan-bench" / "utils" / "llm_utils.py").exists():
        sys.exit(f"not a PlanBench checkout: {pb_root}")
    patch_init(pb_root)
    patch_llm_utils(pb_root)
    patch_response_generation(pb_root)
    patch_response_evaluation(pb_root)


if __name__ == "__main__":
    main()
