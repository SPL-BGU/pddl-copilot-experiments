#!/usr/bin/env python3
"""Stage-1 paired A-vs-B harness-probe comparison (frontier D2).

Pairs the two arms' trials.jsonl by trial key and reports, per task and
overall:
  * success rates + discordant pairs, with an exact McNemar test (binomial
    on the discordant count — the right small-sample form at n=100);
  * turns / input / output token distributions;
  * real $ per arm (list price + effective price with cache accounting) and
    the caching ACTIVE / NET-LOSS / INACTIVE verdict per arm;
  * the discordant pairs themselves (task/domain/problem/label + each arm's
    failure_reason) so the "why" is readable without re-mining the corpora.

Gate (handoff): extend to 300-500 only if >=2 discordant pairs or a clear
turns/token shift; otherwise stage-1 stands as the gross-defect check.

Usage:
    python tools/frontier_ab_compare.py \
        --a .local/frontier/a_probe/trials.jsonl \
        --b .local/frontier/b_probe/trials.jsonl \
        --model claude-haiku-4-5
"""

import argparse
import json
from math import comb
from pathlib import Path

# (in, out) list $/tok; cache write = 1.25x in, cache read = 0.1x in.
PRICES = {
    "claude-sonnet-4-6": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude-haiku-4-5": (1.0 / 1_000_000, 5.0 / 1_000_000),
}
TASKS = ["solve", "validate_domain", "validate_problem", "validate_plan",
         "simulate"]


def load(path: str) -> dict[tuple, dict]:
    rows = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows[tuple(r["key"])] = r["result"]
    return rows


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar: P(X <= min | Bin(b+c, .5)) doubled."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def arm_cost(rows, in_price, out_price) -> tuple[float, float]:
    """(effective $, list-price $ as if no caching)."""
    eff = lst = 0.0
    for r in rows:
        t = r["tokens"]
        eff += (t["prompt"] * in_price
                + t.get("cache_write", 0) * in_price * 1.25
                + t.get("cache_read", 0) * in_price * 0.10
                + t["completion"] * out_price)
        lst += ((t["prompt"] + t.get("cache_write", 0)
                 + t.get("cache_read", 0)) * in_price
                + t["completion"] * out_price)
    return eff, lst


def cache_verdict(eff: float, lst: float, rows) -> str:
    if not any(r["tokens"].get("cache_write", 0)
               or r["tokens"].get("cache_read", 0) for r in rows):
        return "INACTIVE"
    return "ACTIVE" if eff < lst else f"NET-LOSS ({(eff/lst-1)*+100:+.1f}%)"


def stats(rows) -> dict:
    n = len(rows)
    tok = lambda f: sum(r["tokens"][f] for r in rows)
    return {"n": n, "succ": sum(r["success"] for r in rows),
            "turns": tok("turns") / max(n, 1),
            "in": (tok("prompt") + sum(r["tokens"].get("cache_write", 0)
                                       + r["tokens"].get("cache_read", 0)
                                       for r in rows)) / max(n, 1),
            "out": tok("completion") / max(n, 1)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--a", required=True, help="A-arm (bare loop) trials.jsonl")
    p.add_argument("--b", required=True, help="B-arm (SDK runner) trials.jsonl")
    p.add_argument("--model", default="claude-haiku-4-5", choices=list(PRICES))
    args = p.parse_args()

    a_rows, b_rows = load(args.a), load(args.b)
    shared = sorted(a_rows.keys() & b_rows.keys())
    only_a, only_b = a_rows.keys() - b_rows.keys(), b_rows.keys() - a_rows.keys()
    print(f"[ab] paired={len(shared)}  A-only={len(only_a)}  "
          f"B-only={len(only_b)}")
    if only_a or only_b:
        for k in sorted(only_a):
            print(f"  A-only: {k[1]}/{k[2]}/{k[3]}/{k[4]}")
        for k in sorted(only_b):
            print(f"  B-only: {k[1]}/{k[2]}/{k[3]}/{k[4]}")

    # --- success, paired ---
    disc = []          # (key, a_success, b_success)
    b_only_wins = c_only = 0   # b = A-succ/B-fail, c = A-fail/B-succ
    for k in shared:
        sa, sb = a_rows[k]["success"], b_rows[k]["success"]
        if sa != sb:
            disc.append((k, sa, sb))
            if sa:
                b_only_wins += 1
            else:
                c_only += 1
    pval = mcnemar_exact(b_only_wins, c_only)

    task_of = lambda k: k[1]
    print(f"\n{'task':18s} {'A succ':>8s} {'B succ':>8s} {'disc':>5s}   "
          f"{'A turns':>7s} {'B turns':>7s} {'A in-tok':>9s} {'B in-tok':>9s} "
          f"{'A out':>6s} {'B out':>6s}")
    for t in TASKS + [None]:
        keys = shared if t is None else [k for k in shared if task_of(k) == t]
        if not keys:
            continue
        sa = stats([a_rows[k] for k in keys])
        sb = stats([b_rows[k] for k in keys])
        d = sum(1 for k, *_ in disc if t is None or task_of(k) == t)
        name = t or "TOTAL"
        print(f"{name:18s} {sa['succ']:>3d}/{sa['n']:<3d} {sb['succ']:>3d}/"
              f"{sb['n']:<4d} {d:>5d}   {sa['turns']:>7.2f} {sb['turns']:>7.2f} "
              f"{sa['in']:>9.0f} {sb['in']:>9.0f} {sa['out']:>6.0f} "
              f"{sb['out']:>6.0f}")

    print(f"\n[ab] discordant pairs: {len(disc)} "
          f"(A-only-success={b_only_wins}, B-only-success={c_only}), "
          f"exact McNemar p={pval:.4f}")
    for k, sa, sb in disc:
        ra, rb = a_rows[k], b_rows[k]
        lbl = f"/{k[4]}" if k[4] else ""
        print(f"  {k[1]}/{k[2]}/{k[3]}{lbl}: "
              f"A={'OK' if sa else ra['failure_reason']} "
              f"B={'OK' if sb else rb['failure_reason']}")

    # --- cost + caching ---
    in_p, out_p = PRICES[args.model]
    print()
    for name, rows in (("A", [a_rows[k] for k in shared]),
                       ("B", [b_rows[k] for k in shared])):
        eff, lst = arm_cost(rows, in_p, out_p)
        print(f"[ab] arm {name}: effective ${eff:.2f} vs list ${lst:.2f} "
              f"-> caching {cache_verdict(eff, lst, rows)}")

    gate = len(disc) >= 2
    print(f"\n[ab] stage-2 gate (>=2 discordant pairs): "
          f"{'TRIGGERED — extend to 300-500 paired trials' if gate else 'not triggered — stage-1 stands as the gross-defect check'}")


if __name__ == "__main__":
    main()
