"""Unit tests for the checks and the row builder of tools/reanalysis/rq1_matched_metrics.py.

No results/ data is read and no validator runs: the tests cover the 18-cell count
check, the comparison with the filed by-length breakdowns, and the rows of the
contrasts table (the dagger), all on small hand-made inputs.
"""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.reanalysis import matched_run as MR  # noqa: E402
from tools.reanalysis import rq1_matched_metrics as RM  # noqa: E402
from tools.reanalysis.gen_common import model_name  # noqa: E402

PER_CELL = 4
RIGHT = {"N": 1, "P": 3, "S": 2}          # right answers per cell, the same in every cell


def b(est, lo, hi, **more):
    return {"est": est, "lo": lo, "hi": hi, **more}


def filed_json():
    """A hand-made `matched_run.json`: 18 rates and 18 registered contrasts (and one
    descriptive contrast that must be ignored)."""
    rates, contrasts = [], []
    for m in MR.MODEL_ORDER:
        for t in MR.TASKS:
            for arm in MR.ARMS:
                rates.append({"model": m, "task": t, "cell": arm, "this_run": True,
                              "registered": b(25.0 * RIGHT[arm], 10.0, 90.0,
                                              right=RIGHT[arm], n=PER_CELL)})
            rates.append({"model": m, "task": t, "cell": "Part A, plain", "this_run": False,
                          "registered": b(50.0, 40.0, 60.0, right=2, n=PER_CELL)})
            for name in MR.CONTRASTS:
                contrasts.append({"name": name, "grade": "registered", "model": m, "task": t,
                                  **b(1.0, -2.0, 4.0), "p": 0.5, "p_holm": 1.0,
                                  "label": "no difference shown"})
    contrasts.append({"name": "M1", "grade": "frozen", "model": MR.MODEL_ORDER[0],
                      "task": "solve", **b(99.0, 98.0, 100.0), "p": 0.0, "p_holm": 0.0,
                      "label": None})
    return {"mode": "live", "package_sha256": RM.FROZEN, "rates": rates, "contrasts": contrasts}


def set_contrast(filed, name, model, task, **values):
    for c in filed["contrasts"]:
        if (c["name"], c["grade"], c["model"], c["task"]) == (name, "registered", model, task):
            c.update(values)
            return
    raise KeyError((name, model, task))


def rows_for(filed):
    """Records with the fields `check_counts` reads, matching the filed counts."""
    out = []
    for r in filed["rates"]:
        if r["this_run"]:
            for i in range(r["registered"]["n"]):
                out.append({"model": model_name(r["model"]), "task": r["task"],
                            "arm": MR.ARM_REC[r["cell"]], "ok": i < r["registered"]["right"]})
    return out


# ------------------------------------------------------------------ the count check
def test_count_check_passes_on_matching_counts():
    filed = filed_json()
    table = RM.check_counts(rows_for(filed), filed, per_cell=PER_CELL)
    assert len(table) == 18
    assert all((c["right"], c["n"]) == (c["filed_right"], c["filed_n"]) for c in table)


def test_count_check_halts_on_a_tampered_count():
    filed = filed_json()
    rows = rows_for(filed)
    tampered = copy.deepcopy(filed)
    tampered["rates"][0]["registered"]["right"] += 1
    with pytest.raises(RM.Halt, match="counts differ"):
        RM.check_counts(rows, tampered, per_cell=PER_CELL)
    flipped = copy.deepcopy(rows)
    flipped[0]["ok"] = not flipped[0]["ok"]
    with pytest.raises(RM.Halt, match="counts differ"):
        RM.check_counts(flipped, filed, per_cell=PER_CELL)


def test_count_check_halts_on_a_short_cell_and_on_a_missing_cell():
    filed = filed_json()
    with pytest.raises(RM.Halt, match="counts differ"):
        RM.check_counts(rows_for(filed)[1:], filed, per_cell=PER_CELL)
    # The filed counts agree with the rows, but a cell must hold the registered size.
    with pytest.raises(RM.Halt, match="a cell holds 300 trials"):
        RM.check_counts(rows_for(filed), filed)
    short = copy.deepcopy(filed)
    short["rates"] = [r for r in short["rates"] if r["cell"] != "S"]
    with pytest.raises(RM.Halt, match="18 cells"):
        RM.check_counts(rows_for(filed), short, per_cell=PER_CELL)


def test_filed_output_must_be_the_frozen_live_one(tmp_path):
    import json
    for change in ({"mode": "fixture"}, {"package_sha256": "0" * 64}):
        p = tmp_path / "matched_run.json"
        p.write_text(json.dumps({**filed_json(), **change}))
        with pytest.raises(RM.Halt, match="not the live output"):
            RM.read_filed(p)
    p.write_text(json.dumps(filed_json()))
    assert RM.read_filed(p)["mode"] == "live"


def test_frozen_hash_is_the_matched_runs_package():
    assert RM.FROZEN == MR.package_sha256()
    assert RM.FROZEN.startswith("1f3d0f84")


# ------------------------------------------------------------------ the breakdown check
def breakdown_inputs():
    by_length = [{"model": "Qwen3.5-9B", "arm": "none", "bin": "1–5", "n": 63,
                  "solved": b(68.24, 52.38, 84.62)}]
    corr = [{"model": "Qwen3.5-9B", "arm": "none", "problems": 100,
             "solved": b(41.33, 31.0, 51.67, n=300)}]
    sim = {"exact": b(13.5, 5.7, 22.8), "states": b(17.0, 9.2, 26.1),
           "states_salvaged": b(20.9, 13.1, 29.8)}
    overall = [{"model": "Qwen3.5-9B", "arm": "none", "n": 282, **sim}]
    cells = [{"model": "Qwen3.5-9B", "arm": "none", "bin": "41+", "n": 30, **sim}]
    m2 = {"overall": overall, "cells": cells, "skipped_problems": ["barman/p01"],
          "undetermined_problems": []}
    m3 = {"by_length": by_length, "corr": corr}
    filed = {"breakdowns": {
        "solve_by_reference_length": copy.deepcopy(by_length),
        "solve_overall": copy.deepcopy(corr),
        "simulate_overall": copy.deepcopy(overall),
        "simulate_by_trace_length": copy.deepcopy(cells),
        "simulate_left_out": ["barman/p01"], "simulate_undetermined": []}}
    return m2, m3, filed


def test_breakdown_check_passes_and_counts_cells():
    m2, m3, filed = breakdown_inputs()
    md = "\n\n".join(RM.breakdown_tables(m2, m3))
    assert RM.check_breakdowns(m2, m3, filed, md) == 4


def test_breakdown_check_ignores_a_change_below_the_printed_decimal():
    m2, m3, filed = breakdown_inputs()
    filed["breakdowns"]["solve_by_reference_length"][0]["solved"]["est"] = 68.2449
    assert RM.check_breakdowns(m2, m3, filed) == 4


@pytest.mark.parametrize("where, field", [
    ("solve_by_reference_length", "solved"), ("solve_overall", "solved"),
    ("simulate_overall", "exact"), ("simulate_overall", "states"),
    ("simulate_by_trace_length", "states_salvaged")])
def test_breakdown_check_halts_on_a_changed_decimal(where, field):
    m2, m3, filed = breakdown_inputs()
    filed["breakdowns"][where][0][field]["hi"] += 0.1
    with pytest.raises(RM.Halt, match="by-length breakdowns differ"):
        RM.check_breakdowns(m2, m3, filed)


def test_breakdown_check_halts_on_trials_bins_left_out_problems_and_the_markdown():
    m2, m3, filed = breakdown_inputs()
    changed = copy.deepcopy(filed)
    changed["breakdowns"]["simulate_by_trace_length"][0]["n"] = 31
    with pytest.raises(RM.Halt, match="simulate by trace length"):
        RM.check_breakdowns(m2, m3, changed)
    changed = copy.deepcopy(filed)
    changed["breakdowns"]["solve_by_reference_length"][0]["bin"] = "6–10"
    with pytest.raises(RM.Halt, match="solve by reference plan length"):
        RM.check_breakdowns(m2, m3, changed)
    changed = copy.deepcopy(filed)
    changed["breakdowns"]["simulate_left_out"] = []
    with pytest.raises(RM.Halt, match="problems left out"):
        RM.check_breakdowns(m2, m3, changed)
    with pytest.raises(RM.Halt, match="does not stand in out/matched_run.md"):
        RM.check_breakdowns(m2, m3, filed, "another table")


# ------------------------------------------------------------------ the contrasts rows
def test_contrast_rows_layout_and_numbers():
    filed = filed_json()
    lines = RM.contrast_rows(filed).splitlines()
    assert lines[0] == r"\multicolumn{7}{@{}l}{\emph{solve}} \\"
    assert lines[4] == r"\addlinespace"
    assert lines[5] == r"\multicolumn{7}{@{}l}{\emph{simulate}} \\"
    assert len(lines) == 9
    assert lines[1] == (
        r"Qwen3.5-9B & $25.0$ {\scriptsize$[10.0,\,90.0]$} & $75.0$ {\scriptsize$[10.0,\,90.0]$}"
        r" & $50.0$ {\scriptsize$[10.0,\,90.0]$} & $+1.0$ {\scriptsize$[-2.0,\,+4.0]$}"
        r" & $+1.0$ {\scriptsize$[-2.0,\,+4.0]$} & $+1.0$ {\scriptsize$[-2.0,\,+4.0]$} \\")
    assert [ln.split(" & ")[0] for ln in lines[1:4]] == ["Qwen3.5-9B", "Gemma-MoE-26B",
                                                         "Qwen3.6-35B"]
    assert "dagger" not in "".join(lines)
    assert "99.0" not in "".join(lines)          # the descriptive-grade contrast is not read


def test_contrast_rows_put_the_dagger_where_the_label_says_not_after_holm():
    filed = filed_json()
    # Interval above zero, adjusted p 0.105: dagger. (Qwen3.6-35B, solve, M1.)
    set_contrast(filed, "M1", "qwen3_6_35b", "solve", est=11.0, lo=2.33, hi=19.67,
                 p_holm=0.105, label="tools ahead (not after Holm)")
    # Interval above zero, adjusted p below 0.05: no dagger.
    set_contrast(filed, "M2", "qwen3_6_35b", "solve", est=21.67, lo=11.0, hi=33.67,
                 p_holm=0.003, label="tools ahead")
    # Interval below zero, adjusted p 0.273: dagger. (Qwen3.5-9B, simulate, M3.)
    set_contrast(filed, "M3", "Qwen3_5_9B", "simulate", est=-3.67, lo=-7.67, hi=-0.67,
                 p_holm=0.273, label="naming the tool hurts (not after Holm)")
    # Interval includes zero, adjusted p large: no dagger.
    set_contrast(filed, "M1", "Qwen3_5_9B", "simulate", est=7.0, lo=-1.33, hi=15.67,
                 p_holm=0.307, label="no difference shown")
    lines = RM.contrast_rows(filed).splitlines()
    solve_35b, sim_9b = lines[3].split(" & "), lines[6].split(" & ")
    assert solve_35b[0] == "Qwen3.6-35B" and sim_9b[0] == "Qwen3.5-9B"
    assert solve_35b[4] == r"$+11.0$ {\scriptsize$[+2.3,\,+19.7]$}$^{\dagger}$"
    assert solve_35b[5] == r"$+21.7$ {\scriptsize$[+11.0,\,+33.7]$}"
    assert sim_9b[4] == r"$+7.0$ {\scriptsize$[-1.3,\,+15.7]$}"
    assert sim_9b[6] == r"$-3.7$ {\scriptsize$[-7.7,\,-0.7]$}$^{\dagger}$ \\"
    assert "".join(lines).count("dagger") == 2


def test_contrast_rows_halt_when_label_and_numbers_disagree():
    filed = filed_json()
    set_contrast(filed, "M1", "qwen3_6_35b", "solve", label="tools ahead (not after Holm)")
    with pytest.raises(RM.Halt, match="disagree"):       # the interval includes zero
        RM.contrast_rows(filed)
    filed = filed_json()
    set_contrast(filed, "M1", "qwen3_6_35b", "solve", lo=2.33, hi=19.67, p_holm=0.105,
                 label="tools ahead")                     # the words are missing
    with pytest.raises(RM.Halt, match="disagree"):
        RM.contrast_rows(filed)


def test_contrast_rows_need_all_18_registered_contrasts():
    filed = filed_json()
    filed["contrasts"] = [c for c in filed["contrasts"]
                          if not (c["name"] == "M3" and c["grade"] == "registered")]
    with pytest.raises(RM.Halt, match="18 registered contrasts"):
        RM.contrast_rows(filed)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
