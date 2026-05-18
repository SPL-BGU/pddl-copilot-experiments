#!/usr/bin/env python3
"""Idempotent in-place edits to make a fresh LLMs-Planning checkout host
the ``pddl_copilot__<backend>__<model>`` engine.

Three edits, anchored on stable strings (not line numbers):

1. ``utils/__init__.py`` — tolerate missing ``OPENAI_API_KEY``.
2. ``utils/llm_utils.py`` — tolerant imports of transformers / openai.
3. ``utils/llm_utils.py`` — dispatch branch for ``pddl_copilot__*`` engines.

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


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: apply_patches.py <LLMs-Planning checkout>")
    pb_root = Path(sys.argv[1]).resolve()
    if not (pb_root / "plan-bench" / "utils" / "llm_utils.py").exists():
        sys.exit(f"not a PlanBench checkout: {pb_root}")
    patch_init(pb_root)
    patch_llm_utils(pb_root)


if __name__ == "__main__":
    main()
