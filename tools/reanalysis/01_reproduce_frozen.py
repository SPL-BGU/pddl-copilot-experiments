#!/usr/bin/env python3
"""Step 0: reproduce the frozen figures we start from (development/NUMBERS.md),
so every later table is known to sit on the right rows.

Run:  .venv/bin/python tools/reanalysis/01_reproduce_frozen.py
"""
from __future__ import annotations

import csv
from collections import Counter

from common import (HEADLINE, MODELS, NEUT, OUT, OVERLAY, STER, TASKS,
                    load_cell)

CHECKS: list[tuple[str, str, str, bool]] = []


def check(name: str, got, want) -> None:
    ok = got == want
    CHECKS.append((name, str(got), str(want), ok))


def main() -> None:
    wt = load_cell("sweep5v2-live", "gemma4_26b-a4b", "off", True)
    vp_n = [r for r in wt if r["task"] == "validate_plan" and r["variant"] in NEUT]
    vp_s = [r for r in wt if r["task"] == "validate_plan" and r["variant"] in STER]
    check("Gemma vplan plain: called / n", (sum(r["called"] for r in vp_n), len(vp_n)), (622, 3000))
    check("Gemma vplan steered: called / n", (sum(r["called"] for r in vp_s), len(vp_s)), (2808, 3000))
    check("Gemma vplan plain: tool-verified ok", sum(r["mech"] for r in vp_n), 617)
    check("Gemma vplan plain: successes without a call",
          sum(r["mech"] for r in vp_n if not r["called"]), 0)
    check("Gemma vplan success plain -> steered (3 dp)",
          (round(sum(r["mech"] for r in vp_n) / 3000, 3),
           round(sum(r["mech"] for r in vp_s) / 3000, 3)), (0.206, 0.926))
    check("Gemma vplan delivered bound plain <low, high> %, censored",
          (round(100 * sum(r["lo"] for r in vp_n) / 3000, 1),
           round(100 * sum(r["hi"] for r in vp_n) / 3000, 1),
           sum(r["censored"] for r in vp_n)), (6.6, 99.6, 2790))

    # unaided simulate 0/3000 over the 10 no-tools cells
    ok = n = 0
    reasons: Counter = Counter()
    for m in MODELS:
        for th in ("off", "on"):
            rows = [r for r in load_cell("sweep5v2-live", m, th, False) if r["task"] == "simulate"]
            ok += sum(r["mech"] for r in rows)
            n += len(rows)
            reasons.update(r["reason"] for r in rows)
    check("unaided simulate strict success / n (10 cells)", (ok, n), (0, 3000))
    check("unaided simulate failure mix",
          (reasons["truncated_no_answer"], reasons["format_parse_fail"], reasons["result_mismatch"]),
          (1772, 1202, 26))

    # 9B validate_domain delivered <99.7, 100.0> (359/360, c1)
    q9 = [r for r in load_cell("sweep5v2-live", "Qwen3_5_9B", "off", True)
          if r["task"] == "validate_domain" and r["variant"] in NEUT]
    check("9B vdomain tl-neut delivered (ok, censored, n)",
          (sum(r["lo"] for r in q9), sum(r["censored"] for r in q9), len(q9)), (359, 1, 360))

    # every think=off cell agrees with pooled_e2e_table.csv
    table = {}
    with (OVERLAY / "pooled_e2e_table.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["corpus"] == "sweep5v2-live" and r["think"] == "off":
                table[(r["model"], r["task"], r["arm"])] = (
                    int(r["n"]), int(r["ok_strict"]), int(r["censored"]), int(r["tv_ok"]))
    mism = 0
    ncell = 0
    for m in MODELS:
        nt = load_cell("sweep5v2-live", m, "off", False)
        tl = load_cell("sweep5v2-live", m, "off", True)
        for t in TASKS:
            for arm, rows, vs, tools in (("nt-neut", nt, NEUT, False), ("tl-neut", tl, NEUT, True),
                                         ("tl-ster", tl, STER, True)):
                rr = [r for r in rows if r["task"] == t and r["variant"] in vs]
                got = (len(rr), sum(r["lo"] for r in rr), sum(r["censored"] for r in rr),
                       sum(r["mech"] for r in rr) if tools else 0)
                ncell += 1
                if table.get((m, t, arm)) != got:
                    mism += 1
                    print("  MISMATCH", m, t, arm, got, table.get((m, t, arm)))
    check(f"pooled_e2e_table.csv agreement, think=off ({ncell} cells): mismatches", mism, 0)

    # contamination table (tex tab:contam): pooled no-tools think=off, per model
    want = {"Qwen3_5_0_8B": (45.9, 45.8), "Qwen3_5_4B": (58.2, 56.1), "Qwen3_5_9B": (63.8, 64.2),
            "gemma4_26b-a4b": (74.3, 75.2), "qwen3_6_35b": (75.7, 74.8)}
    for m in MODELS:
        c = load_cell("sweep5v2-live", m, "off", False)
        a = load_cell("sweep6-live", m, "off", False)
        got = (round(100 * sum(r["mech"] for r in c) / len(c), 1),
               round(100 * sum(r["mech"] for r in a) / len(a), 1))
        check(f"contamination pooled canonical/anonymized {MODELS[m]}", got, want[m])

    lines = ["| check | got | frozen | match |", "|---|---|---|---|"]
    for name, got, wantv, ok in CHECKS:
        lines.append(f"| {name} | {got} | {wantv} | {'yes' if ok else '**NO**'} |")
    text = "\n".join(lines)
    print(text)
    OUT.mkdir(exist_ok=True)
    (OUT / "01_reproduce.md").write_text(text + "\n")
    print(f"\n{sum(c[3] for c in CHECKS)}/{len(CHECKS)} checks match")


if __name__ == "__main__":
    main()
