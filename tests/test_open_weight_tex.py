"""Unit tests for tools/reanalysis/open_weight_tex.py and for the `--open-only` rows of
tools/reanalysis/rq1_matched_metrics.py.

No results/ data is read. The filter is tested on small hand-made row files, and the
committed `_open` files are compared with their committed sources: the open-weight rows
must be the source's rows, byte for byte and in order.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.reanalysis import open_weight_tex as OW  # noqa: E402
from tools.reanalysis import rq1_matched_metrics as RM  # noqa: E402
from tools.reanalysis import rq1_tex as TEX  # noqa: E402

TEXDIR = OW.HERE / "out" / "tex"

BLOCKS = "\n".join([                       # the layout of rq1_tex.rows
    r"Qwen3.5-9B & no-tools & $1.0$ \\",
    r" & +tool (plain) & $2.0$ \\",
    r"\addlinespace",
    r"Qwen3.6-35B & no-tools & $3.0$ \\",
    r"\addlinespace",
    r"Claude Haiku~4.5 & no-tools & $4.0$ \\",
    r" & +tool (plain) & $5.0$ \\",
    r"\addlinespace",
    r"Claude Sonnet~4.6 & no-tools & $6.0$ \\",
    r" & +tool (plain) & $7.0$ \\"]) + "\n"

PANELS = "\n".join([                       # the layout of rq23_tex (rq2_choice.tex)
    r"\multicolumn{7}{@{}l}{\emph{Exactly the right tool and no other (\%)}} \\",
    r"Gemma-MoE-26B & plain & $1.0$ \\",
    r" & steered & $2.0$ \\",
    r"Claude Haiku~4.5 & plain & $3.0$ \\",
    r"Claude Sonnet~4.6 & plain & $4.0$ \\",
    r"\addlinespace",
    r"\multicolumn{7}{@{}l}{\emph{Another tool was called (\%)}} \\",
    r"Gemma-MoE-26B & plain & $5.0$ \\",
    r"Claude Haiku~4.5 & plain & $6.0$ \\",
    r"Claude Sonnet~4.6 & plain & $7.0$ \\"]) + "\n"


def test_blocks_lose_the_claude_rows_and_the_rules_left_without_a_row():
    kept, removed = OW.split(BLOCKS)
    assert kept.splitlines() == BLOCKS.splitlines()[:4]
    assert removed.splitlines() == [ln for ln in BLOCKS.splitlines()[5:] if ln != OW.RULE]
    assert not kept.rstrip("\n").endswith(OW.RULE) and "Claude" not in kept


def test_panels_keep_their_titles_and_the_rule_between_them():
    kept, removed = OW.split(PANELS)
    lines = PANELS.splitlines()
    assert kept.splitlines() == [lines[0], lines[1], lines[2], lines[5], lines[6], lines[7]]
    assert len(removed.splitlines()) == 4 and all("Claude" in ln for ln in removed.splitlines())


def test_a_continuation_row_goes_with_the_model_above_it():
    kept, removed = OW.split(BLOCKS)
    assert r" & +tool (plain) & $2.0$ \\" in kept.splitlines()
    assert r" & +tool (plain) & $5.0$ \\" in removed.splitlines()
    assert r" & +tool (plain) & $7.0$ \\" in removed.splitlines()


def test_halts_on_an_unknown_model_on_no_claude_row_and_on_an_orphan_row():
    with pytest.raises(OW.Halt, match="does not know"):
        OW.split(BLOCKS.replace("Qwen3.6-35B", "GPT-9"))
    with pytest.raises(OW.Halt, match="no Claude row"):
        OW.split("\n".join(BLOCKS.splitlines()[:4]) + "\n")
    with pytest.raises(OW.Halt, match="no row stands above"):
        OW.split(r" & +tool (plain) & $2.0$ \\" + "\n" + BLOCKS)


@pytest.mark.parametrize("name", OW.TABLES)
def test_committed_open_files_are_their_sources_minus_the_claude_rows(name):
    source = (TEXDIR / f"{name}.tex").read_text()
    filed = (TEXDIR / f"{name}_open.tex").read_text()
    kept, removed = OW.split(source)
    assert filed == kept
    # Byte for byte and in order: the open file is the source with lines taken out.
    src = source.splitlines()
    it = iter(src)
    assert all(any(line == s for s in it) for line in filed.splitlines())
    gone = [ln for ln in src if ln not in filed.splitlines()]
    assert [ln for ln in gone if ln != OW.RULE] == removed.splitlines()
    assert "Claude" not in filed and all(ln.split(" & ")[0] in OW.CLAUDE_TEX
                                         or ln.startswith(" & ")
                                         for ln in removed.splitlines())


@pytest.mark.parametrize("name", OW.TABLES)
def test_the_paper_holds_the_open_rows(name):
    main = (OW.HERE.parents[1] / "paper" / "main.tex").read_text()
    assert (TEXDIR / f"{name}_open.tex").read_text() in main


# ------------------------------------------------------------------ rq1_matched_metrics
CELLS = [{"model": m, "arm": a, "v": i}
         for i, (m, a) in enumerate([("Qwen3.5-9B", "none"), ("Qwen3.5-9B", "plain"),
                                     ("Gemma-26B", "none"), ("Qwen3.6-35B", "none"),
                                     ("Claude Haiku 4.5", "none"), ("Claude Haiku 4.5", "tools"),
                                     ("Claude Sonnet 4.6", "none")])]


def fmt(c):
    return [f"${c['v']}$"]


def test_open_only_rows_are_the_open_rows_of_the_full_table():
    full = RM.model_rows(CELLS, fmt)
    assert full == TEX.rows(CELLS, fmt)
    open_cells = [c for c in CELLS if not c["model"].startswith("Claude")]
    only = RM.model_rows(open_cells, fmt, open_only=True)
    assert only == OW.split(full)[0]
    assert only.splitlines()[-1] == r"Qwen3.6-35B & no-tools & $3$ \\"
    assert "Claude" not in only


def test_open_only_puts_the_model_list_of_rq1_tex_back():
    before = TEX.MODELS
    RM.model_rows([c for c in CELLS if not c["model"].startswith("Claude")], fmt, open_only=True)
    assert TEX.MODELS == before and len(TEX.MODELS) == 5
    with pytest.raises(KeyError):
        RM.model_rows(CELLS, lambda c: [c["missing"]], open_only=True)
    assert TEX.MODELS == before


@pytest.mark.parametrize("name", ["rq1m_simulate", "rq1m_solve", "rq1m_planlen"])
def test_the_committed_rq1m_rows_hold_no_claude_row_and_stand_in_the_paper(name):
    rows = (TEXDIR / f"{name}.tex").read_text()
    assert "Claude" not in rows and not rows.rstrip("\n").endswith(OW.RULE)
    assert rows in (OW.HERE.parents[1] / "paper" / "main.tex").read_text()


def test_the_figure_function_takes_the_open_models_first():
    assert tuple(RM.FIG.MODELS[:3]) == RM.OPEN == tuple(OW.FIG.MODELS[:3])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
