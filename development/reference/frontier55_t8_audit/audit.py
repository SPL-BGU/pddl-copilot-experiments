#!/usr/bin/env python3
"""Audit of tripwire T8 (Claude run, Sonnet 5.5, tool arm), 2026-11-26.

    python development/reference/frontier55_t8_audit/audit.py <results/frontier55>

Reads the sidecars only. Prints counts and lengths; no answer or note text."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
for folder in ("claude-haiku-5-5_no-tools", "claude-haiku-5-5_tools",
               "claude-sonnet-5-5_no-tools", "claude-sonnet-5-5_tools"):
    turns = with_field = nonzero = total = 0
    notes = []
    for line in open(root / folder / "trial_meta.jsonl"):
        r = json.loads(line)
        for i, t in enumerate(r["turns"]):
            turns += 1
            det = (t.get("usage") or {}).get("output_tokens_details")
            if isinstance(det, dict) and "thinking_tokens" in det:
                with_field += 1
                nonzero += det["thinking_tokens"] > 0
                total += det["thinking_tokens"]
            for b in t.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "thinking":
                    notes.append({"turn": i + 1, "of_turns": len(r["turns"]),
                                  "note_chars": len(b.get("thinking") or ""),
                                  "thinking_tokens_reported": (det or {}).get("thinking_tokens"),
                                  "output_tokens_of_turn": t["usage"]["output_tokens"]})
    print(f"{folder}: turns {turns}; turns whose usage has output_tokens_details."
          f"thinking_tokens {with_field}; of them above zero {nonzero}; sum {total}; "
          f"notes {len(notes)}")
    for n in notes:
        print("   ", n)
