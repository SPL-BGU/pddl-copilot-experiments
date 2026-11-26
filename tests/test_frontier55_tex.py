"""Unit tests for tools/reanalysis/frontier55_tex.py, the rows of the paper's Claude table.

No results/ data is read: the tests run on a small hand-made copy of the fields the
script reads from `out/frontier55.json`. They cover the halt on a file that is not the
frozen live output, the order of the ten rows, the dagger, and the halts on a missing
cell and on a reading that disagrees with its numbers.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.reanalysis import frontier55_tex as FT  # noqa: E402

N = {"solve": 300, "validate_domain": 360, "validate_problem": 600, "validate_plan": 3000,
     "simulate": 300}


def b(est, lo, hi, **more):
    return {"est": est, "lo": lo, "hi": hi, **more}


def filed_json():
    """A hand-made `frontier55.json`: 20 rates, 10 contrasts, 10 tool-choice cells and
    10 cells of tool right and answer wrong, the same figures in every cell."""
    rates, contrasts, choice, lost = [], [], [], []
    for m, _name in FT.MODELS:
        for t in FT.TASKS:
            rates.append({"model": m, "task": t, "arm": "no-tools", **b(40.0, 30.0, 50.0)})
            rates.append({"model": m, "task": t, "arm": "tools", **b(60.04, 50.0, 70.0)})
            contrasts.append({"model": m, "task": t, **b(1.0, -2.0, 4.0), "p": 0.5,
                              "p_holm": 1.0, "label": "no difference shown"})
            choice.append({"model": m, "task": t, "n_classed": N[t],
                           "exactly_right": b(90.0, 80.0, 100.0, n=N[t])})
            lost.append({"model": m, "task": t, "n_tool_right": N[t] - 10, "n_answer_wrong": 7,
                         "answer_wrong": b(2.5, 1.0, 4.0, n=N[t] - 10)})
    return {"mode": "live", "package_sha256": FT.FROZEN, "rates": rates,
            "contrasts": contrasts, "tool_choice": choice, "tool_right_answer_wrong": lost}


def set_contrast(filed, model, task, **values):
    for c in filed["contrasts"]:
        if (c["model"], c["task"]) == (model, task):
            c.update(values)
            return
    raise KeyError((model, task))


# ------------------------------------------------------------------ the filed output
def test_halts_on_a_wrong_hash_and_on_a_file_that_is_not_live(tmp_path):
    p = tmp_path / "frontier55.json"
    for change in ({"package_sha256": "0" * 64}, {"mode": "fixture"}):
        p.write_text(json.dumps({**filed_json(), **change}))
        with pytest.raises(FT.Halt, match="not the live output"):
            FT.read_filed(p)
        with pytest.raises(FT.Halt, match="not the live output"):
            FT.main(["--json", str(p), "--out", str(tmp_path / "rows.tex")])
        assert not (tmp_path / "rows.tex").exists()
    p.write_text(json.dumps(filed_json()))
    assert FT.read_filed(p)["mode"] == "live"
    assert FT.main(["--json", str(p), "--out", str(tmp_path / "rows.tex")]) == 0
    assert (tmp_path / "rows.tex").read_text() == FT.rows(filed_json())


def test_frozen_hash_is_the_claude_runs_package():
    assert FT.FROZEN.startswith("0cbb69b7")
    filed = Path(FT.HERE / "out" / "frontier55.json")
    assert json.loads(filed.read_text())["package_sha256"] == FT.FROZEN


# ------------------------------------------------------------------ the rows
def test_row_order_and_layout():
    lines = FT.rows(filed_json()).splitlines()
    assert len(lines) == 11 and lines[5] == r"\addlinespace"
    body = lines[:5] + lines[6:]
    assert [ln.split(" & ")[0] for ln in body] == (
        ["Claude Haiku~5.5", "", "", "", ""] + ["Claude Sonnet~5.5", "", "", "", ""])
    assert [ln.split(" & ")[1] for ln in body] == 2 * [
        r"\emph{solve}", r"\emph{validate\_domain}", r"\emph{validate\_problem}",
        r"\emph{validate\_plan}", r"\emph{simulate}"]
    assert lines[0] == (
        r"Claude Haiku~5.5 & \emph{solve} & $40.0$ {\scriptsize$[30.0,\,50.0]$}"
        r" & $60.0$ {\scriptsize$[50.0,\,70.0]$} & $+1.0$ {\scriptsize$[-2.0,\,+4.0]$}"
        r" & $90.0$ {\scriptsize$[80.0,\,100.0]$} & $7$ / $290$"
        r" & $2.5$ \\")
    assert all(len(ln.split(" & ")) == 8 for ln in body)
    assert "dagger" not in "".join(lines)


def test_rows_do_not_depend_on_the_order_of_the_file():
    filed = filed_json()
    shuffled = copy.deepcopy(filed)
    for name in ("rates", "contrasts", "tool_choice", "tool_right_answer_wrong"):
        shuffled[name].reverse()
    assert FT.rows(shuffled) == FT.rows(filed)


def test_each_cell_is_read_from_its_own_model_task_and_arm():
    filed = filed_json()
    for r in filed["rates"]:
        if (r["model"], r["task"], r["arm"]) == ("claude-sonnet-5-5", "validate_plan", "tools"):
            r.update(b(99.4, 98.5, 100.0))
    line = FT.rows(filed).splitlines()[9]
    assert line.split(" & ")[1] == r"\emph{validate\_plan}"
    assert line.split(" & ")[2] == r"$40.0$ {\scriptsize$[30.0,\,50.0]$}"
    assert line.split(" & ")[3] == r"$99.4$ {\scriptsize$[98.5,\,100.0]$}"
    assert "".join(FT.rows(filed).splitlines()).count("99.4") == 1


def test_dagger_where_the_reading_says_not_after_holm():
    filed = filed_json()
    set_contrast(filed, "claude-haiku-5-5", "solve", lo=2.33, hi=19.67, est=11.0,
                 p_holm=0.105, label="tools ahead (not after Holm)")
    set_contrast(filed, "claude-sonnet-5-5", "simulate", lo=-7.67, hi=-0.67, est=-3.67,
                 p_holm=0.07, label="no tools ahead (not after Holm)")
    set_contrast(filed, "claude-sonnet-5-5", "solve", lo=11.0, hi=33.67, est=21.67,
                 p_holm=0.012, label="tools ahead")           # survives Holm: no dagger
    lines = FT.rows(filed).splitlines()
    assert lines[0].split(" & ")[4] == r"$+11.0$ {\scriptsize$[+2.3,\,+19.7]$}$^{\dagger}$"
    assert lines[10].split(" & ")[4] == r"$-3.7$ {\scriptsize$[-7.7,\,-0.7]$}$^{\dagger}$"
    assert lines[6].split(" & ")[4] == r"$+21.7$ {\scriptsize$[+11.0,\,+33.7]$}"
    assert "".join(lines).count("dagger") == 2


def test_halts_when_reading_and_numbers_disagree():
    filed = filed_json()
    set_contrast(filed, "claude-haiku-5-5", "solve", label="tools ahead (not after Holm)")
    with pytest.raises(FT.Halt, match="disagree"):       # the interval includes zero
        FT.rows(filed)
    filed = filed_json()
    set_contrast(filed, "claude-haiku-5-5", "solve", lo=2.33, hi=19.67, p_holm=0.105,
                 label="tools ahead")                     # the words are missing
    with pytest.raises(FT.Halt, match="disagree"):
        FT.rows(filed)


@pytest.mark.parametrize("name", ["rates", "contrasts", "tool_choice",
                                  "tool_right_answer_wrong"])
def test_halts_on_a_missing_a_doubled_and_a_foreign_cell(name):
    filed = filed_json()
    filed[name] = filed[name][1:]
    with pytest.raises(FT.Halt, match="does not hold"):
        FT.rows(filed)
    filed = filed_json()
    filed[name].append(copy.deepcopy(filed[name][0]))
    with pytest.raises(FT.Halt, match="does not hold"):
        FT.rows(filed)
    filed = filed_json()
    filed[name][0]["model"] = "claude-haiku-4-5"
    with pytest.raises(FT.Halt, match="does not hold"):
        FT.rows(filed)


def test_halts_when_the_share_is_not_over_the_tool_right_trials():
    filed = filed_json()
    filed["tool_right_answer_wrong"][0]["answer_wrong"]["n"] += 1
    with pytest.raises(FT.Halt, match="tool-right"):
        FT.rows(filed)


def test_the_filed_output_gives_the_rows_pasted_from_out_tex():
    """The committed row file is what the script writes from the committed JSON, and
    the paper holds those rows."""
    filed = FT.read_filed(FT.HERE / "out" / "frontier55.json")
    rows = (FT.HERE / "out" / "tex" / "frontier55_main.tex").read_text()
    assert rows == FT.rows(filed)
    assert rows in (FT.HERE.parents[1] / "paper" / "main.tex").read_text()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
