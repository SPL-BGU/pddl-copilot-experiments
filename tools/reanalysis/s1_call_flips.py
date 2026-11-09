#!/usr/bin/env python3
"""Run-to-run call-state flips: main sweep (results/sweep5v2-live) against the
delivered rerun (results/delivered-rerun), tool cells, thinking off.

Rows come through the frozen rerun package's own loader (`tools.delivered_rerun
.schema.load_cell` with the registered cell specs; read-only, the same rows
`s1_calling_rerun_vs_main.py` reads). Pairs are matched on the trial key
(task, domain, problem, plan_label, variant), within each model x task x arm
(plain = v11-13, steered = v14-16).

Per cell:
  calls main / calls rerun  share of paired rows whose `tool_selected` is true
                            (the task's own tool was called; the Study 1 and
                            T2 definition). None counts as not called.
  flips                     called -> not called, not called -> called
  net                       rerun calls minus main calls (trials)
  any-call flips            the same with "any tool call" (the readout's
                            "invocation") in place of `tool_selected`
  prompt check              on pairs where both rows are single-turn (no tool
                            result was sent back, so `tokens.prompt` is the
                            first prompt alone), the share with equal prompt
                            tokens. Multi-turn rows sum the prompt over turns
                            and are not comparable.

Descriptive, post hoc (2026-11-09). No test, no interval: the T8a calling
column already carries the paired bootstrap.

Run:  .venv/bin/python tools/reanalysis/s1_call_flips.py [--results DIR]
Writes tools/reanalysis/out/s1_call_flips.{json,md} and
       tools/reanalysis/out/numbers_s1_call_flips.md (the NUMBERS.md rows).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.delivered_rerun import constants as C  # noqa: E402
from tools.delivered_rerun import schema as S  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
NM = {"Qwen3_5_9B": "Qwen3.5-9B", "gemma4_26b-a4b": "Gemma-26B", "qwen3_6_35b": "Qwen3.6-35B"}


def flip_counts(pairs, f) -> dict:
    """pairs: [(main_row, rerun_row)]; f: row -> bool."""
    n = len(pairs)
    cm = sum(f(a) for a, _ in pairs)
    cr = sum(f(b) for _, b in pairs)
    lost = sum(f(a) and not f(b) for a, b in pairs)
    won = sum(not f(a) and f(b) for a, b in pairs)
    assert cr - cm == won - lost
    return dict(n=n, main=cm, rerun=cr, lost=lost, won=won, flips=lost + won, net=cr - cm)


def sel(r) -> bool:
    return r.tool_selected is True


def anycall(r) -> bool:
    return len(r.tool_calls) > 0


def cells(results: Path) -> list[dict]:
    out = []
    for m in C.PART_A_MODELS:
        rr = S.load_cell(results / "delivered-rerun", S.spec_rerun_a(C.REGISTERED, m))
        cc = S.load_cell(results / "sweep5v2-live", S.spec_canonical_tools(C.REGISTERED, m))
        ri = {r.trial_key: r for r in rr.rows}
        ci = {r.trial_key: r for r in cc.rows}
        for t in C.TASKS:
            for arm in C.ARMS:
                keys = sorted(k for k in set(ri) & set(ci) if k[0] == t and ri[k].arm == arm)
                unpaired = sum(1 for k in set(ri) ^ set(ci) if k[0] == t
                               and (ri.get(k) or ci.get(k)).arm == arm)
                pairs = [(ci[k], ri[k]) for k in keys]
                single = [(a, b) for a, b in pairs if a.tokens.turns == 1 and b.tokens.turns == 1]
                eq = sum(a.tokens.prompt == b.tokens.prompt for a, b in single)
                none_main = sum(a.tool_selected is None for a, _ in pairs)
                none_rerun = sum(b.tool_selected is None for _, b in pairs)
                out.append(dict(model=m, task=t, arm=arm, unpaired=unpaired,
                                sel=flip_counts(pairs, sel), any=flip_counts(pairs, anycall),
                                single_turn_pairs=len(single), prompt_equal=eq,
                                sel_none_main=none_main, sel_none_rerun=none_rerun))
    return out


def pct(x: int, n: int) -> str:
    return f"{100 * x / n:.1f}" if n else "nan"


def render(rows: list[dict]) -> tuple[str, str]:
    L = ["# Call-state flips, main sweep vs delivered rerun (tool cells, think=off)", "",
         "Calling = `tool_selected` (the task's own tool). Flips are trials whose call state "
         "differs between the two runs, paired on the trial key. Prompt check: pairs where both "
         "rows are single-turn, share with equal `tokens.prompt`.", "",
         "| model | task | arm | n paired | calls, main | calls, rerun | called → not | not → called "
         "| flips (% of n) | net | any-call flips | prompt equal, single-turn pairs |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s, a = r["sel"], r["any"]
        L.append(f"| {NM[r['model']]} | {r['task']} | {r['arm']} | {s['n']:,} | "
                 f"{s['main']:,} ({pct(s['main'], s['n'])}) | {s['rerun']:,} ({pct(s['rerun'], s['n'])}) | "
                 f"{s['lost']} | {s['won']} | {s['flips']} ({pct(s['flips'], s['n'])}) | {s['net']:+d} | "
                 f"{a['flips']} | {r['prompt_equal']:,} / {r['single_turn_pairs']:,} |")
    tot_unp = sum(r["unpaired"] for r in rows)
    none = sum(r["sel_none_main"] + r["sel_none_rerun"] for r in rows)
    st = sum(r["single_turn_pairs"] for r in rows)
    eq = sum(r["prompt_equal"] for r in rows)
    L += ["", f"Unpaired rows: {tot_unp}. Rows with `tool_selected` null (counted as not called): "
          f"{none}. Prompt tokens equal on {eq:,} of {st:,} single-turn pairs.", ""]
    per_model = {}
    for m in C.PART_A_MODELS:
        rs = [r for r in rows if r["model"] == m]
        per_model[m] = max(100 * r["sel"]["flips"] / r["sel"]["n"] for r in rs)
    L.append("Largest flip share per model: " + "; ".join(
        f"{NM[m]} {v:.1f}%" for m, v in per_model.items()) + ".")
    L.append("")

    def get(m, t, a):
        return next(r for r in rows if (r["model"], r["task"], r["arm"]) == (m, t, a))
    q = "qwen3_6_35b"
    sp, sm, vp = get(q, "solve", "plain"), get(q, "simulate", "plain"), get(q, "validate_plan", "plain")
    small = max(v for m, v in per_model.items() if m != q)
    other35 = [r for r in rows if r["model"] == q and (r["task"], r["arm"]) not in
               {("solve", "plain"), ("simulate", "plain"), ("validate_plan", "plain")}]
    o35 = max(100 * r["sel"]["flips"] / r["sel"]["n"] for r in other35)

    def fl(r):
        s = r["sel"]
        return (f"{s['flips']}/{s['n']:,} ({pct(s['flips'], s['n'])}%; {s['lost']} called → not, "
                f"{s['won']} not → called; calls {pct(s['main'], s['n'])} → {pct(s['rerun'], s['n'])})")
    N = ["| figure | **quote this** | source | do NOT quote |", "|---|---|---|---|",
         f"| call-state flips, 35B, plain arm (descriptive) | solve **{fl(sp)}**; simulate **{fl(sm)}**; "
         f"validate_plan **{fl(vp)}**. Every other 35B cell ≤ {o35:.1f}%; 9B and Gemma ≤ {small:.1f}% in every cell | "
         f"`s1_call_flips.py`; table below | **a single-run 35B plain calling rate alone** "
         f"(Omer 2026-11-09: quote both runs, 68.0 and 82.7, and keep \"bigger calls less\" as a direction only) |",
         f"| prompt check on the paired rows | prompt tokens equal on **{eq:,} of {st:,}** single-turn pairs "
         f"(rows that called a tool sum the prompt over turns and are not compared) | `s1_call_flips.py` | none |"]
    table = "\n".join(L[4:]) + "\n"  # from the header row on, without the title
    return "\n".join(L) + "\n", "\n".join(N) + "\n", table


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=REPO / "results")
    args = ap.parse_args(argv)
    rows = cells(args.results)
    md, nrows, table = render(rows)
    OUT.mkdir(exist_ok=True)
    (OUT / "s1_call_flips.json").write_text(json.dumps(rows, indent=1) + "\n")
    (OUT / "s1_call_flips.md").write_text(md)
    (OUT / "numbers_s1_call_flips.md").write_text(nrows)
    (OUT / "s1_call_flips_table.md").write_text(table)
    print(md)
    print(nrows)


if __name__ == "__main__":
    main()
