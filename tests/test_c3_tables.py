"""Unit tests for tools/reanalysis/gen_common.py (the C3 table generators' helpers).

No results data needed: the generators' own self-checks cover the data path.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "reanalysis"))
import gen_common as G  # noqa: E402


def test_rate_cell_uses_bootstrap_inside_and_wilson_at_the_edges():
    assert G.rate_cell(30, 100, 20.0, 41.0) == "30.0 [20.0, 41.0]"
    edge = G.rate_cell(100, 100, 100.0, 100.0)
    assert edge.endswith("†") and edge.startswith("100.0 [96.3, 100.0]")
    assert G.rate_cell(0, 300, 0.0, 0.0) == "0.0 [0.0, 1.3]†"   # the T1 unaided simulate cell
    assert G.rate_cell(0, 0, 0, 0) == "–"


def test_splice_replaces_only_between_markers():
    tag = "x.py"
    text = f"head\n{G.begin_marker(tag)}\nold\n{G.end_marker(tag)}\ntail\n"
    out = G.splice(text, tag, "new body\n")
    assert out == f"head\n{G.begin_marker(tag)}\nnew body\n{G.end_marker(tag)}\ntail\n"
    assert G.splice(out, tag, "new body") == out          # idempotent


@pytest.mark.parametrize("text", ["no markers", f"{G.begin_marker('x.py')}\n",
                                  f"{G.end_marker('x.py')}\n{G.begin_marker('x.py')}\n"])
def test_splice_refuses_missing_or_misordered_markers(text):
    with pytest.raises(ValueError):
        G.splice(text, "x.py", "body")


def test_tex_escape():
    assert G.tex_escape("validate_plan 5%") == r"validate\_plan 5\%"
    assert G.tex_escape("**31.0** †") == r"31.0 $^{\dagger}$"
    assert G.tex_escape("0.0 [0.0, 3.7]†¶") == r"0.0 [0.0, 3.7]$^{\dagger}$$^{\P}$"
    assert G.tex_escape("`a_b` 1–2 → x") == r"a\_b 1--2 $\to$ x"
    assert G.tex_escape("a\\b") == r"a\textbackslash{}b"


def test_tex_table_shape():
    t = G.tex_table(["model", "task", "rate"], [["G", "solve", "1.0"]], source="s.py")
    assert r"\begin{tabular}{llr}" in t and r"G & solve & 1.0 \\" in t and t.startswith("% generated")


def test_multiplier_boot_point_estimate_and_draws():
    ct, st = [10.0, 20.0, 30.0], [1, 2, 3]
    cn, sn = [5.0, 5.0, 5.0], [1, 1, 1]
    m = G.multiplier_boot(ct, st, cn, sn, seed=1, b=500)
    assert m["est"] == pytest.approx((60 / 6) / (15 / 3))
    assert m["k"] == 3 and m["draws_with_zero_successes"] == 0
    assert m["lo"] <= m["est"] <= m["hi"]
    # same seed, same draws
    assert G.multiplier_boot(ct, st, cn, sn, seed=1, b=500) == m


def test_multiplier_boot_drops_draws_without_successes_and_none_when_empty():
    m = G.multiplier_boot([1.0, 1.0], [0, 1], [1.0, 1.0], [1, 1], seed=3, b=2000)
    assert m["draws_with_zero_successes"] > 0
    rng = np.random.default_rng(3)
    d = rng.integers(0, 2, size=(2000, 2))
    assert m["draws_with_zero_successes"] == int(((np.array([0, 1])[d]).sum(1) == 0).sum())
    assert G.multiplier_boot([1.0], [0], [1.0], [1], seed=3, b=10) is None
    assert G.mult_cell(None) == "–"
    assert G.mult_cell({"est": 1.0, "lo": 0.5, "hi": 2.0, "draws_with_zero_successes": 1}) == \
        "1.00 [0.50, 2.00] (1 draw dropped)"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
