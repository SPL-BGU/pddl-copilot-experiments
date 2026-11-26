"""Unit tests for tools/reanalysis/token_consumption_tex.py, the rows of Table tab:tokens.

No results/ data is read: the tests run on a hand-made copy of the fields the script
reads from `out/token_consumption.json`. They cover the halt on a file without the frozen
hashes, the order and count of the 25 rows, the group label, the number formats and the
dash for a missing break-even budget.
"""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.reanalysis import token_consumption_tex as TT  # noqa: E402

MODELS = [m for m, _ in TT.OPEN] + [m for m, _ in TT.CLAUDE]


def b(est, lo, hi):
    return {"est": est, "lo": lo, "hi": hi}


def fake_json(break_even="none"):
    cells, rows, pairs = [], [], []
    for m in MODELS:
        for t in TT.TASKS:
            cp, arm = TT.corpus_of(m, t), TT.tool_arm(m)
            cells.append({"corpus": cp, "model": m, "task": t, "arm": "none",
                          "total": b(5211.4, 0, 0)})
            cells.append({"corpus": cp, "model": m, "task": t, "arm": arm,
                          "total": b(25029.0, 0, 0)})
            for c, v in ((1.0, b(2.1666, 1.304, 3.375)), (0.1, b(1.1249, 0.7, 1.69)),
                         (0.5, b(9.0, 9.0, 9.0))):
                for p in (1.0, 5.0):
                    rows.append({"corpus": cp, "model": m, "task": t, "arm": arm, "c": c, "p": p,
                                 "scenario": "own hits", "refused_request": "kept",
                                 "mult": v if p == 1.0 else b(0.1, 0.1, 0.1)})
            pairs.append({"corpus": cp, "model": m, "task": t, "arm": arm, "unit": "raw",
                          "break_even": {"est": break_even}})
            pairs.append({"corpus": cp, "model": m, "task": t, "arm": arm, "unit": "5:1",
                          "break_even": {"est": 1.0}})
    return {"hashes": dict(TT.FROZEN), "cells": cells, "caching": {"rows": rows},
            "coverage": {"pairs": pairs}}


def test_halts_without_frozen_hashes(tmp_path):
    bad = fake_json()
    bad["hashes"]["matched_run"] = "0" * 64
    f = tmp_path / "t.json"
    f.write_text(__import__("json").dumps(bad))
    with pytest.raises(TT.Halt):
        TT.read(f)


def test_rows_order_group_label_and_formats():
    text = TT.rows(fake_json(break_even=20046.0))
    lines = text.strip().split("\n")
    data = [ln for ln in lines if ln.endswith(r"\\") and "multicolumn" not in ln]
    assert len(data) == 25
    assert lines.count(TT.GROUP_LABEL) == 1
    label_at = lines.index(TT.GROUP_LABEL)
    assert lines[label_at - 1] == r"\addlinespace"
    assert lines[label_at + 1].startswith("Claude Haiku~5.5 & \\emph{solve}")
    assert data[0] == (r"Qwen3.5-9B & \emph{solve} & $5.2$ & $25.0$ & "
                       r"$2.17$ {\scriptsize$[1.30,\,3.38]$} & $1.12$ & $20.0$ \\")
    assert data[1].startswith(r" & \emph{validate\_domain} & ")
    assert data[5].startswith("Gemma-MoE-26B & ")
    assert data[-1].startswith(r" & \emph{simulate} & ")


def test_dash_for_no_break_even_and_halt_on_missing_cell():
    text = TT.rows(fake_json(break_even="none"))
    assert all(ln.endswith(r"& -- \\") for ln in text.split("\n")
               if ln.endswith(r"\\") and "multicolumn" not in ln)
    assert TT.budget(None) == "--" and TT.budget(float("inf")) == "--"
    assert TT.budget(0.0) == "$0.0$" and TT.budget(108403.0) == "$108.4$"
    broken = copy.deepcopy(fake_json())
    broken["cells"] = broken["cells"][2:]
    with pytest.raises(TT.Halt):
        TT.rows(broken)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
