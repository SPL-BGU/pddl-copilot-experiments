"""Shared helpers for the transcript re-analysis scripts (q1_/q2_/q3_*.py).

Read-only over results. Nothing here grades a trial for the paper; the scripts
describe what the stored text shows. See development/reanalysis_transcripts.md.
(Named transcripts_common so it cannot collide with the other re-analysis
scripts' common.py in this directory.)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

RESULTS = REPO / "results"
OVERLAY = RESULTS / "derived" / "e2e_overlay"


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson 95% score interval, in percent."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0.0, c - h), 100 * min(1.0, c + h))


def pct(k: int, n: int) -> str:
    """'k/n = p% [lo, hi]' with a Wilson 95% interval."""
    if n == 0:
        return "0/0"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% [{lo:.1f}, {hi:.1f}]"


def load_trials(path: Path) -> dict[tuple, dict]:
    """trials.jsonl -> {key: result}. Last occurrence of a key wins (the same
    resume rule tools/e2e_regrade.py uses). Torn lines are skipped and counted."""
    out: dict[tuple, dict] = {}
    torn = 0
    with path.open() as fh:
        for ln in fh:
            if not ln.strip():
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                torn += 1
                continue
            out[tuple(obj["key"])] = obj["result"]
    if torn:
        print(f"note: {torn} torn line(s) skipped in {path}", file=sys.stderr)
    return out


def load_overlay(path: Path) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    with path.open() as fh:
        for ln in fh:
            if ln.strip():
                r = json.loads(ln)
                out[tuple(r["trial_key"])] = r
    return out


def clip(s: str, n: int = 300) -> str:
    s = s.replace("\r", "")
    return s if len(s) <= n else s[:n] + " [...]"
