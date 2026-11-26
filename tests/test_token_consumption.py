"""Arithmetic of tools/reanalysis/token_consumption.py on hand-made rows (no data read)."""
import math

import numpy as np
import pytest

from tools.reanalysis import token_consumption as T
from tools.reanalysis.gen_common import multiplier_boot


def test_cost_per_right_and_price_weight():
    assert T.price_weighted(1000, 200) == 1200
    assert T.price_weighted(1000, 200, 5) == 2000
    assert T.cost_per_right(1200, 4) == 300
    assert T.cost_per_right(1200, 0) is None


def test_multiplier():
    # tools: 10,000 tokens for 8 right; no tools: 2,000 tokens for 4 right
    assert T.multiplier(10_000, 8, 2_000, 4) == pytest.approx((10_000 / 8) / (2_000 / 4))
    assert T.multiplier(10_000, 8, 2_000, 0) is None
    assert T.multiplier(10_000, 0, 2_000, 4) is None


def test_multiplier_matches_gen_common_point_estimate():
    ct, st = np.array([100.0, 300.0]), np.array([2, 1])
    cn, sn = np.array([50.0, 50.0]), np.array([1, 1])
    m = multiplier_boot(ct, st, cn, sn, seed=1, b=200)
    assert m["est"] == pytest.approx(T.multiplier(400, 3, 100, 2))


def test_gain_per_1k():
    # 300 trials; tools right 270, none 120; tools 6,000,000 tokens, none 1,500,000
    g = T.gain_per_1k(270, 120, 6_000_000, 1_500_000, 300)
    # 50 points for 15,000 extra tokens per trial -> 3.33 points per 1,000
    assert g == pytest.approx(50 / 15)
    assert T.gain_per_1k(1, 0, 100, 100, 1) is None          # no extra tokens
    assert T.gain_per_1k(100, 150, 2000, 1000, 300) < 0       # a loss stays negative


def test_split_turns_exact():
    # request 1: prompt 1,000, writes 300 (a tool call); tool returns 2,000 tokens (+ wrapper);
    # request 2: 1,000 + 300 + 2,000 = 3,300 in, writes 100; request 3 not made.
    s = T.split_turns([1000, 3300], [300, 100])
    assert s == {"first": 2000, "own": 300, "tool": 2000, "total": 4300}
    assert s["first"] + s["own"] + s["tool"] == s["total"]
    # three requests: the first tool result is re-read twice, the second once
    s = T.split_turns([1000, 3300, 3700], [300, 50, 20])
    assert s["first"] == 3000
    assert s["own"] == 2 * 300 + 1 * 50
    assert s["tool"] == 2 * 2000 + 1 * (3700 - 3300 - 50)
    assert s["first"] + s["own"] + s["tool"] == s["total"]
    assert T.split_turns([1500], [700]) == {"first": 1500, "own": 0, "tool": 0, "total": 1500}
    with pytest.raises(ValueError):
        T.split_turns([1, 2], [1])


def test_added_context_and_split():
    # two requests, first prompt 4,000; summed input 10,000 -> 2,000 added
    assert T.added_context(10_000, 2, 4_000) == 2_000
    own, tool = T.split_added(2_000, [(1_000, 3_000)], 2)
    assert (own, tool) == (500, 1_500)
    # two calls in three requests: call 1 re-read twice, call 2 once
    own, tool = T.split_added(900, [(100, 200), (100, 100)], 3)
    w_own, w_tool = 2 * 100 + 1 * 100, 2 * 200 + 1 * 100
    assert tool == pytest.approx(900 * w_tool / (w_own + w_tool))
    assert own + tool == pytest.approx(900)
    assert T.split_added(-5, [(1, 1)], 2) == (0.0, 0.0)
    assert T.split_added(50, [], 1) == (50.0, 0.0)


def test_ratio_and_gain_boot_point_estimates():
    dr = T.draws(3, b=500, seed=7)
    num, den = np.array([10.0, 20.0, 30.0]), np.array([1.0, 1.0, 2.0])
    b = T.ratio_boot(num, den, dr)
    assert b["est"] == pytest.approx(15.0) and b["lo"] <= b["est"] <= b["hi"]
    g = T.gain_boot([3, 3, 3], [1, 1, 1], [3000, 3000, 3000], [1000, 1000, 1000], dr)
    assert g["est"] == pytest.approx(1e5 * 6 / 6000)
    assert math.isclose(g["lo"], g["est"]) and math.isclose(g["hi"], g["est"])
    d = T.diff_boot([30, 30], [10, 10], [10, 10], T.draws(2, b=50, seed=1))
    assert d["est"] == pytest.approx(2.0)


def test_draws_are_multiplier_boot_draws():
    a = T.draws(20, b=10, seed=20261002)
    b = np.random.default_rng(20261002).integers(0, 20, size=(10, 20))
    assert (a == b).all()


# ------------------------------------------------------------------ Part A: coverage at a budget
def test_coverage_at_budget():
    totals = [1000, 2000, 3000, 50000]
    right = [True, False, True, True]
    assert T.coverage(totals, right, 500) == 0
    assert T.coverage(totals, right, 1000) == 25          # at most B counts
    assert T.coverage(totals, right, 2500) == 25          # the wrong trial never counts
    assert T.coverage(totals, right, 3000) == 50
    assert T.coverage(totals, right, math.inf) == 75      # no limit = the success rate
    assert T.coverage_from_sorted([1000, 3000, 50000], 4, 3000) == 50


def test_break_even():
    # tools right at 10K and 12K; no tools right at 1K: tools behind until 10K (a tie counts)
    assert T.break_even([10_000, 12_000], [True, True], [1_000, 5], [True, False]) == 10_000
    # tools ahead everywhere
    assert T.break_even([100], [True], [200], [True]) == 0.0
    # tools behind at no limit
    assert T.break_even([100], [False], [200], [True]) == math.inf
    # a tie at the end counts as "at or above"
    assert T.break_even([5_000], [True], [1_000], [True]) == 5_000


def test_break_even_boot_point_matches():
    dr = T.draws(2, b=200, seed=3)
    b = T.break_even_boot([10_000, 12_000], [True, True], ["a", "b"],
                          [1_000, 5], [True, False], ["a", "b"], ["a", "b"], dr)
    assert b["est"] == 10_000 and b["lo"] <= b["hi"]


# ------------------------------------------------------------------ Part B: prompt caching
def test_cached_split_exact():
    u, c, exc = T.cached_split_exact([1000, 3300, 3700])
    assert (u, c, exc) == (1000 + 2300 + 400, 1000 + 3300, 0)
    assert u + c == 1000 + 3300 + 3700
    assert T.cached_split_exact([500]) == (500, 0, 0)
    assert T.cached_split_exact([2000, 1500])[2] == 1        # a prompt that shrank is flagged


def test_cached_bounds_and_estimate():
    assert T.cached_bounds(1000, 1, 1000) == (0.0, 0.0)
    assert T.cached_bounds(5000, 2, 2000) == (2000.0, 2000.0)          # C = P_1
    lo, hi = T.cached_bounds(9000, 3, 2000)
    assert (lo, hi) == (4000.0, 6000.0)                                 # 2 P_1 and S 2/3
    # true prompts 2000, 3000, 4000 (S = 9000, C = 5000) lie inside the bounds
    assert lo <= 5000 <= hi
    est = T.cached_estimate(9000, 3, 2000, [(0, 1000), (0, 1000)])      # equal growth
    assert est == pytest.approx(5000)
    assert lo <= T.cached_estimate(9000, 3, 2000, [(10, 5000), (10, 1)]) <= hi


def test_cache_cost():
    assert T.cache_cost(1000, 4000, 300, 1.0) == 5300                   # c = 1: as measured
    assert T.cache_cost(1000, 4000, 300, 0.1) == pytest.approx(1700)
    assert T.cache_cost(1000, 4000, 300, 0.0, 5) == 2500                # only new tokens


def test_list_price_dollars():
    # Sonnet 5.5: $2 / $10 per million; a two-request trial at list price
    m = "claude-sonnet-5-5"
    usd = T.list_trial_usd(m, [10_000, 12_000], [1_000, 500])
    assert usd == pytest.approx((22_000 * 2 + 1_500 * 10) / 1e6)
    # with caching: request 1 writes 10,000 (x1.25); request 2 reads 10,000 (x0.05) and writes 2,000
    cached = T.cached_trial_usd(m, [10_000, 12_000], [1_000, 500])
    want = ((10_000 * 1.25 + 2_000 * 1.25 + 10_000 * 0.05) * 2 + 1_500 * 10) / 1e6
    assert cached == pytest.approx(want)
    # Haiku 5.5's higher rate for a request whose prompt is over 100,000 tokens
    h = "claude-haiku-5-5"
    assert T.list_usd(h, 150_000, 0) == pytest.approx(150_000 * 0.50 / 1e6)
    assert T.list_usd(h, 50_000, 0) == pytest.approx(50_000 * 0.10 / 1e6)
