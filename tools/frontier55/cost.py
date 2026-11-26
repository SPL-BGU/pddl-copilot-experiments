#!/usr/bin/env python3
"""Itemized cost estimate of the Claude run, for Omer to read before any spend.

    python -m tools.frontier55.cost --old-results /abs/results [--markdown]

It reads only the OLD Claude rows (Haiku 4.5 and Sonnet 4.6, wording v11) and makes no
API call. Per model, arm and task it takes the old rows' token counts, scales them to
the new model's tokens, and prices them:

  * Sonnet 5.5 counts about 1.3 times as many tokens for the same text as Sonnet 4.6
    (development/reference/draft_D5_cost_and_correa.md, assumption 2). Factor 1.3.
  * Haiku 5.5: the factor against Haiku 4.5 is NOT KNOWN. The estimate is given at 1.0
    and at 1.3, as a range.
  * No-tools arm: Batch API, half the list price. Tool arm: live calls, list price, no
    prompt caching.
  * Haiku 5.5 charges a higher rate when the prompt is over 100,000 tokens. A trial whose
    summed input over all its turns passes that size is priced at the higher rate as a
    whole (input and output). That overstates it.

What the estimate cannot know: how long the new models' answers are. The old no-tools
solve answers were short (structured output); the new ones are free text. So a second
figure is printed: the bound with every request writing its full output cap.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
OUTPUT_CAP = {"solve": 8192, "validate_domain": 6144, "validate_problem": 6144,
              "validate_plan": 6144, "simulate": 6144}
WORDINGS_FULL = 3
PILOT_PROBLEM = "p01"
OLD_WORDING = 11

# $ per million tokens (input, output), list price. `long` applies to Haiku 5.5 above
# `long_over` prompt tokens. To be checked against the price list on the day.
PRICES = {
    "claude-haiku-5-5": {"base": (0.10, 0.50), "long": (0.50, 2.50), "long_over": 100_000},
    "claude-sonnet-5-5": {"base": (2.00, 10.00), "long": None, "long_over": None},
}
BATCH_FACTOR = 0.5
# (low, high) token factor against the old model of the same tier.
TOKEN_FACTOR = {"claude-haiku-5-5": (1.0, 1.3), "claude-sonnet-5-5": (1.3, 1.3)}
OLD_CORPORA = {  # new model -> (old no-tools folder, old tool folder, old model name)
    "claude-haiku-5-5": ("haiku-frontier/sweep5v2", "haiku-frontier/sweep5v2-with-tools",
                         "Haiku 4.5"),
    "claude-sonnet-5-5": ("sonnet-frontier/sweep5v2", "sonnet-frontier/sweep5v2-with-tools",
                          "Sonnet 4.6"),
}
ARMS = ("no-tools", "tools")


def old_rows(path: Path) -> list[dict]:
    """(task, problem, input tokens, output tokens, turns) of the old v11 rows."""
    out = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)["result"]
        except (json.JSONDecodeError, KeyError):
            continue
        if int(r["prompt_variant"]) != OLD_WORDING or r.get("infra_failure"):
            continue
        t = r.get("tokens") or {}
        out.append({"task": r["task"], "problem": r["problem_name"],
                    "in": int(t.get("prompt", 0)) + int(t.get("cache_write", 0))
                    + int(t.get("cache_read", 0)),
                    "out": int(t.get("completion", 0)), "turns": max(1, int(t.get("turns", 1)))})
    return out


def price_trial(model: str, arm: str, task: str, row: dict, factor: float) -> dict:
    """Estimated and bound cost of one trial, in dollars."""
    p = PRICES[model]
    tin = row["in"] * factor
    cap_out = OUTPUT_CAP[task] * row["turns"]
    tout = min(row["out"] * factor, cap_out)
    rate_in, rate_out = p["base"]
    long_tier = bool(p["long"]) and tin > p["long_over"]
    if long_tier:
        rate_in, rate_out = p["long"]
    mult = BATCH_FACTOR if arm == "no-tools" else 1.0
    return {"in": tin, "out": tout, "requests": row["turns"], "long": long_tier,
            "usd": (tin * rate_in + tout * rate_out) / 1e6 * mult,
            "usd_bound": (tin * rate_in + cap_out * rate_out) / 1e6 * mult}


def estimate(rows_by_arm: dict[str, list[dict]], model: str, *, pilot: bool) -> list[dict]:
    """One line per arm and task, for the pilot or the full run."""
    lines = []
    copies = 1 if pilot else WORDINGS_FULL
    lo_f, hi_f = TOKEN_FACTOR[model]
    for arm in ARMS:
        by_task = defaultdict(list)
        for r in rows_by_arm[arm]:
            if pilot and r["problem"] != PILOT_PROBLEM:
                continue
            by_task[r["task"]].append(r)
        for task in TASKS:
            rs = by_task.get(task, [])
            lo = [price_trial(model, arm, task, r, lo_f) for r in rs]
            hi = [price_trial(model, arm, task, r, hi_f) for r in rs]
            lines.append({
                "model": model, "arm": arm, "task": task, "trials": len(rs) * copies,
                "requests": sum(x["requests"] for x in hi) * copies,
                "in_mtok_lo": sum(x["in"] for x in lo) * copies / 1e6,
                "in_mtok_hi": sum(x["in"] for x in hi) * copies / 1e6,
                "out_mtok_lo": sum(x["out"] for x in lo) * copies / 1e6,
                "out_mtok_hi": sum(x["out"] for x in hi) * copies / 1e6,
                "long_tier_trials": sum(x["long"] for x in hi) * copies,
                "usd_lo": sum(x["usd"] for x in lo) * copies,
                "usd_hi": sum(x["usd"] for x in hi) * copies,
                "usd_bound": sum(x["usd_bound"] for x in hi) * copies})
    return lines


def load_old(results: Path, model: str) -> dict[str, list[dict]]:
    nt, wt, _name = OLD_CORPORA[model]
    return {"no-tools": old_rows(Path(results) / nt / "trials.jsonl"),
            "tools": old_rows(Path(results) / wt / "trials.jsonl")}


def _rng(lo: float, hi: float, fmt: str) -> str:
    return fmt.format(lo) if abs(hi - lo) < 1e-9 else f"{fmt.format(lo)} to {fmt.format(hi)}"


def render(all_lines: dict[str, list[dict]]) -> str:
    out = []
    for title, lines in all_lines.items():
        out.append(f"**{title}**\n")
        out.append("| model | arm | task | trials | requests | input, MTok | output, MTok | "
                   "trials at Haiku's higher rate | estimate, $ | bound at full output cap, $ |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        tot = defaultdict(lambda: [0.0, 0.0, 0.0, 0, 0])
        for ln in lines:
            out.append(
                f"| {ln['model']} | {ln['arm']} | {ln['task']} | {ln['trials']:,} | "
                f"{ln['requests']:,} | {_rng(ln['in_mtok_lo'], ln['in_mtok_hi'], '{:.2f}')} | "
                f"{_rng(ln['out_mtok_lo'], ln['out_mtok_hi'], '{:.2f}')} | "
                f"{ln['long_tier_trials']} | {_rng(ln['usd_lo'], ln['usd_hi'], '{:.2f}')} | "
                f"{ln['usd_bound']:.2f} |")
            t = tot[ln["model"]]
            t[0] += ln["usd_lo"]; t[1] += ln["usd_hi"]; t[2] += ln["usd_bound"]
            t[3] += ln["trials"]; t[4] += ln["requests"]
        g = [0.0, 0.0, 0.0, 0, 0]
        for model, t in tot.items():
            out.append(f"| **{model}, total** | | | **{t[3]:,}** | **{t[4]:,}** | | | | "
                       f"**{_rng(t[0], t[1], '{:.2f}')}** | **{t[2]:.2f}** |")
            g = [a + b for a, b in zip(g, t)]
        out.append(f"| **both models** | | | **{g[3]:,}** | **{g[4]:,}** | | | | "
                   f"**{_rng(g[0], g[1], '{:.2f}')}** | **{g[2]:.2f}** |")
        out.append("")
    return "\n".join(out)


def build(results: Path) -> dict[str, list[dict]]:
    res = {"Pilot (first problem of every domain, wording v11)": [],
           "Full run (three wordings)": []}
    for model in PRICES:
        rows = load_old(results, model)
        res["Pilot (first problem of every domain, wording v11)"] += estimate(
            rows, model, pilot=True)
        res["Full run (three wordings)"] += estimate(rows, model, pilot=False)
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--old-results", default=str(REPO_ROOT / "results"),
                   help="the results folder that holds haiku-frontier/ and sonnet-frontier/")
    args = p.parse_args(argv)
    print(render(build(Path(args.old_results))))
    print("Prices, $ per million tokens (input / output): Haiku 5.5 0.10 / 0.50 up to "
          "100,000 prompt tokens and 0.50 / 2.50 above; Sonnet 5.5 2.00 / 10.00; the "
          "no-tools arm at half price (Batch API). Token factor against the old model: "
          "Sonnet 1.3; Haiku unknown, shown at 1.0 to 1.3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
