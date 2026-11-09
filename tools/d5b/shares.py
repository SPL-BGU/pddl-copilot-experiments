"""D5b solved shares: what Fast Downward solves within 120 s and 1800 s.

Standard library only (runs in the repo venv):

    python -m tools.d5b.shares [--work external/d5b-work] [--json out.json]

Reads <work>/runs/fd_120s.jsonl and, if present, fd_1800s.jsonl, written by
tools.d5b.pipeline solve. A (problem, strategy) pair counts as solved only if
the planner returned a plan AND KCL VAL accepted it (VAL every plan). The
harness grader, pddl-pyvalidator 0.1.6, is checked against KCL VAL on every
plan it has been run on (`pipeline val --checker pyval`), in the Checks part.

Within 1800 s = solved in the 120 s pass, or solved in the 1800 s pass. The
1800 s pass only runs the pairs unsolved at 120 s (searches are deterministic);
a pair unsolved at 120 s with no 1800 s record yet is "pending", and cells with
pending pairs print the range [solved, solved + pending] instead of one share.
"Any strategy" counts a problem as solved if at least one of the three
strategies solved it.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

STRATEGIES = ("lazy_greedy_cea", "lazy_greedy_ff", "astar_lmcut")
TIERS = ("easy", "medium", "hard")
LIMITS = (120, 1800)
DEFAULT_WORK = Path(__file__).resolve().parents[2] / "external" / "d5b-work"


def normalize(r: dict) -> dict:
    """Records from the first runs of the 120 s pass (before KCL VAL was
    added) carry the inline pddl-pyvalidator verdict as val_*; rename it to
    pyval_* so every record uses one set of field names."""
    if "val_valid" in r and "pyval_valid" not in r:
        r = dict(r)
        for k in ("valid", "status", "time", "message"):
            if f"val_{k}" in r:
                r[f"pyval_{k}"] = r.pop(f"val_{k}")
    return r


def load(path: Path) -> dict:
    """key -> final record. Header lines and requeue notes are skipped; a later
    final record for the same key replaces an earlier one (that is how
    `pipeline val` adds a verdict)."""
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("_header") or r.get("status") == "requeued":
            continue
        out[(r["problem"], r["strategy"])] = normalize(r)
    return out


def is_solved(rec: dict | None) -> bool | None:
    """True = plan found and KCL VAL accepted it; False = not solved, or VAL
    rejected the plan; None = no record yet, or a plan with no KCL VAL verdict
    yet (`pipeline val --checker kcl` adds it)."""
    if rec is None:
        return None
    if rec.get("status") != "solved":
        return False
    v = rec.get("kval_valid")
    return v if isinstance(v, bool) else None


def pair_outcomes(r120: dict, r1800: dict) -> dict:
    """(problem, strategy) -> {120: bool|None, 1800: bool|None}. Every pair
    of the 120 s pass is included; None = pending (no 1800 s record yet, or
    VAL unfinished)."""
    out = {}
    for pair, rec in r120.items():
        s120 = is_solved(rec)
        if s120 is False:
            s1800 = is_solved(r1800.get(pair))
        else:  # solved at 120 s, or its VAL check is unfinished
            s1800 = s120
        out[pair] = {120: s120, 1800: s1800}
    return out


def _dom_tier(problem: str) -> tuple[str, str]:
    parts = problem.split("/")  # problems/<domain>/<tier>/pNN.pddl
    return parts[1], parts[2]


def cells(outcomes: dict) -> dict:
    """(domain, tier, strategy|'any', limit) -> Counter(solved, unsolved, pending)."""
    c: dict = defaultdict(Counter)
    by_problem: dict = defaultdict(dict)
    for (problem, strategy), o in outcomes.items():
        d, t = _dom_tier(problem)
        by_problem[problem][strategy] = o
        for lim in LIMITS:
            v = o[lim]
            c[(d, t, strategy, lim)]["pending" if v is None else ("solved" if v else "unsolved")] += 1
    for problem, strat in by_problem.items():
        d, t = _dom_tier(problem)
        for lim in LIMITS:
            vals = [o[lim] for o in strat.values()]
            k = "solved" if any(v is True for v in vals) else ("pending" if None in vals else "unsolved")
            c[(d, t, "any", lim)][k] += 1
    return c


def fmt(cnt: Counter) -> str:
    n = cnt["solved"] + cnt["unsolved"] + cnt["pending"]
    if n == 0:
        return "-"
    s, p = cnt["solved"], cnt["pending"]
    if p:
        return f"{s}-{s + p}/{n} ({100 * s / n:.0f}-{100 * (s + p) / n:.0f}%, {p} pending)"
    return f"{s}/{n} ({100 * s / n:.0f}%)"


def report(r120: dict, r1800: dict) -> str:
    outcomes = pair_outcomes(r120, r1800)
    c = cells(outcomes)
    domains = sorted({k[0] for k in c})
    lines = []
    for lim in LIMITS:
        lines.append(f"\n## Solved within {lim} s (plan found and VAL-valid)\n")
        lines.append("| domain | tier | " + " | ".join(STRATEGIES) + " | any strategy |")
        lines.append("|---|---|" + "---|" * (len(STRATEGIES) + 1))
        for d in domains:
            for t in TIERS:
                row = [fmt(c[(d, t, s, lim)]) for s in STRATEGIES + ("any",)]
                lines.append(f"| {d} | {t} | " + " | ".join(row) + " |")
        for t in TIERS:
            row = []
            for s in STRATEGIES + ("any",):
                tot = Counter()
                for d in domains:
                    tot.update(c[(d, t, s, lim)])
                row.append(fmt(tot))
            lines.append(f"| all four | {t} | " + " | ".join(row) + " |")
    lines.append("\n## Checks\n")
    lines.extend("- " + x for x in checks(r120, r1800, outcomes))
    return "\n".join(lines)


def checks(r120: dict, r1800: dict, outcomes: dict) -> list[str]:
    out = []
    for lim, recs in ((120, r120), (1800, r1800)):
        if not recs:
            out.append(f"{lim} s pass: no records")
            continue
        st = Counter(r.get("status") for r in recs.values())
        plans = [r for r in recs.values() if r.get("status") == "solved"]
        rej = sum(1 for r in plans if r.get("kval_valid") is False)
        nov = sum(1 for r in plans if not isinstance(r.get("kval_valid"), bool))
        size_bad = sum(1 for r in plans if r.get("kval_plan_size") not in (None, r.get("plan_len")))
        near = sum(1 for r in plans if is_solved(r) and (r.get("solve_time") or 0) > 0.5 * lim)
        out.append(f"{lim} s pass: {len(recs)} runs; statuses {dict(sorted(st.items()))}; "
                   f"plans rejected by KCL VAL: {rej}; plans with no KCL VAL verdict yet: {nov}; "
                   f"VAL plan size differs from the plan length: {size_bad}; "
                   f"solved runs that took over half the limit: {near}")
        py = [r for r in plans if isinstance(r.get("pyval_valid"), bool)]
        agree = sum(1 for r in py if r["pyval_valid"] == r.get("kval_valid"))
        both = sum(1 for r in py if isinstance(r.get("kval_valid"), bool))
        line = (f"{lim} s pass, pddl-pyvalidator 0.1.6 (the harness grader): run on {len(py)} of "
                f"{len(plans)} plans; agrees with KCL VAL on {agree} of {both} checked by both")
        if py:
            slow = max(py, key=lambda r: r.get("pyval_time") or 0)
            line += (f"; slowest pyval check {slow.get('pyval_time', 0):.0f} s for a "
                     f"{slow.get('plan_len')}-step plan ({slow['problem'].split('/', 1)[1]}, {slow['strategy']})")
        out.append(line)
    n_pending = sum(1 for o in outcomes.values() if o[1800] is None)
    out.append(f"pairs pending within 1800 s (unsolved at 120 s and not yet run at 1800 s, "
               f"or no VAL verdict yet): {n_pending}")
    return out


def _tier_line(c: dict, domains: list, strategy: str, lim: int) -> str:
    parts = []
    for t in TIERS:
        tot = Counter()
        for d in domains:
            tot.update(c[(d, t, strategy, lim)])
        parts.append(f"{t} {fmt(tot)}")
    per = "; ".join(
        f"{d}: " + ", ".join(f"{t} " + fmt(c[(d, t, strategy, lim)]).split(" (")[0] for t in TIERS)
        for d in domains)
    return ", ".join(parts) + f". Per domain: {per}"


def numbers_rows(r120: dict, r1800: dict, validate: list | None) -> str:
    """The NUMBERS.md rows (gen:d5b_shares block)."""
    outcomes = pair_outcomes(r120, r1800)
    c = cells(outcomes)
    domains = sorted({k[0] for k in c})
    n_prob = len({p for p, _ in outcomes})
    rows = ["| figure | value | source | do NOT quote |", "|---|---|---|---|"]
    if validate is not None:
        ok = sum(1 for v in validate if v.get("valid") and v.get("kval_valid") is True)
        rows.append(f"| D5b corpus, syntax check | {ok} / {len(validate)} files valid (4 IPC 2023 domain files + "
                    f"{len(validate) - 4} generated problems; pddl-pyvalidator 0.1.6 and KCL VAL both) | `validate.jsonl` | - |")
    dont = ("a share with a pending range as one number; these shares as a model result "
            "(no model has run on these problems)")
    for lim in LIMITS:
        for strat, label in (("lazy_greedy_cea", "plugin default `lazy_greedy_cea`"), ("any", "any of the three strategies")):
            rows.append(f"| Fast Downward solved within {lim} s, {label} ({n_prob} problems, plan VAL-valid) | "
                        f"**{_tier_line(c, domains, strat, lim)}** | `tools/d5b/shares.py` | {dont} |")
    plans = [r for recs in (r120, r1800) for r in recs.values() if r.get("status") == "solved"]
    rej = sum(1 for r in plans if r.get("kval_valid") is False)
    rows.append(f"| plans found, rejected by KCL VAL | {rej} of {len(plans)} | `tools/d5b/shares.py` | - |")
    py = [r for r in plans if isinstance(r.get("pyval_valid"), bool) and isinstance(r.get("kval_valid"), bool)]
    agree = sum(1 for r in py if r["pyval_valid"] == r["kval_valid"])
    if py:
        slow = max(py, key=lambda r: r.get("pyval_time") or 0)
        rows.append(f"| pddl-pyvalidator 0.1.6 (the harness grader) vs KCL VAL on the planner's plans | "
                    f"agrees on {agree} of {len(py)} plans checked by both ({len(plans) - len(py)} not checked "
                    f"by pyval yet); slowest pyval check {slow.get('pyval_time', 0):.0f} s for a "
                    f"{slow.get('plan_len')}-step plan | `tools/d5b/shares.py` | - |")
    return "\n".join(rows) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5b solved shares")
    ap.add_argument("--work", type=Path, default=DEFAULT_WORK)
    ap.add_argument("--json", type=Path, default=None, help="also write the cell counts here")
    ap.add_argument("--write", action="store_true",
                    help="also write tools/reanalysis/out/d5b_shares.md (the report) and "
                         "numbers_d5b_shares.md (the NUMBERS.md rows; fill with numbers_fill.py)")
    a = ap.parse_args(argv)
    r120 = load(a.work / "runs" / "fd_120s.jsonl")
    r1800 = load(a.work / "runs" / "fd_1800s.jsonl")
    if not r120:
        print("no 120 s records; run tools.d5b.pipeline solve --time-limit 120 first", file=sys.stderr)
        return 1
    text = (f"# D5b ground truth: Fast Downward solved shares\n\n"
            f"Source: `<work>/runs/fd_120s.jsonl` and `fd_1800s.jsonl` (default work folder "
            f"`external/d5b-work`, gitignored), printed by `python -m tools.d5b.shares`.\n"
            + report(r120, r1800) + "\n")
    print(text, end="")
    if a.write:
        out = Path(__file__).resolve().parents[1] / "reanalysis" / "out"
        vpath = a.work / "validate.jsonl"
        val = ([json.loads(x) for x in vpath.read_text().splitlines()[1:] if x.strip()]
               if vpath.exists() else None)
        (out / "d5b_shares.md").write_text(text)
        (out / "numbers_d5b_shares.md").write_text(numbers_rows(r120, r1800, val))
        print(f"\nwrote {out / 'd5b_shares.md'} and {out / 'numbers_d5b_shares.md'}")
    if a.json:
        c = cells(pair_outcomes(r120, r1800))
        a.json.write_text(json.dumps({"|".join(map(str, k)): dict(v) for k, v in sorted(c.items(), key=str)},
                                     indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
