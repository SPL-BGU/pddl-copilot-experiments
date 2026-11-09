"""Self-checks for the 2026-11-09 reanalysis scripts (no results data needed).

  tools/reanalysis/s1_call_flips.py           flip counting
  tools/reanalysis/val_frontier_solve.py      bare-line rule, action names, delivered extraction
  tools/reanalysis/numbers_fill.py            marker replacement in NUMBERS.md

Run standalone: `python3 tests/test_reanalysis_flips_anon_val.py` (also in `bash tests/verify.sh`)
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "reanalysis"))
sys.path.insert(0, str(REPO))

import numbers_fill  # noqa: E402
import s1_call_flips  # noqa: E402
import val_frontier_solve as vfs  # noqa: E402


def _row(sel):
    return SimpleNamespace(tool_selected=sel, tool_calls=())


def test_flip_counts():
    pairs = [(_row(True), _row(True)), (_row(True), _row(False)),
             (_row(False), _row(True)), (_row(False), _row(True)), (_row(None), _row(False))]
    c = s1_call_flips.flip_counts(pairs, s1_call_flips.sel)
    assert c == dict(n=5, main=2, rerun=3, lost=1, won=2, flips=3, net=1)


def test_bare_action_lines_and_actions():
    dom = REPO / "domains" / "classical" / "blocksworld" / "domain.pddl"
    acts = vfs.actions_of(dom)
    assert {"pick_up", "put_down", "stack", "unstack"} <= acts
    line = "unstack b4 b1"
    assert vfs.ACTION_LINE.match(line) and line.split()[0] in acts
    prose = "Let me analyze this problem."
    assert prose.split()[0].lower() not in acts  # prose is never bracketed and re-run


def test_delivered_plan_extraction():
    resp = "Here is the plan:\n\n```\n(pick_up b1)\n(stack b1 b2)\n```\n"
    assert vfs.delivered_plan(resp) == ("(pick_up b1)", "(stack b1 b2)")
    assert vfs.delivered_plan("") == ()
    assert vfs.delivered_plan("x" * vfs.SNAPSHOT_CAP) == ()  # an answer cut at the cap is not rebuilt


def test_numbers_fill(tmp_path):
    for name, files in numbers_fill.BLOCKS.items():
        for f in files:
            (tmp_path / f).write_text(f"rows of {f}\n")
    text = "head\n" + "".join(f"<!-- gen:{n} -->\nold\n<!-- /gen:{n} -->\n" for n in numbers_fill.BLOCKS) + "tail\n"
    out = numbers_fill.fill(text, tmp_path)
    assert "old" not in out and out.startswith("head\n") and out.endswith("tail\n")
    assert "rows of s1_call_flips_table.md" in out
    assert numbers_fill.fill(out, tmp_path) == out  # idempotent


if __name__ == "__main__":
    import tempfile
    test_flip_counts()
    test_bare_action_lines_and_actions()
    test_delivered_plan_extraction()
    with tempfile.TemporaryDirectory() as d:
        test_numbers_fill(Path(d))
    print("4 checks passed")
