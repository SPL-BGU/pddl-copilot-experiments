"""Gate: reproduce the frozen figures the breakdowns decompose, before any
breakdown is trusted. Compares this directory's loader against

  * results/derived/e2e_overlay/pooled_e2e_table.csv  (every headline cell)
  * development/NUMBERS.md rows (hard-coded expectations below, each with the
    NUMBERS.md wording it comes from)

Exit code 0 when every check passes, 1 otherwise.

    python3 tools/reanalysis/bc_reproduce_numbers.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bc_common as C  # noqa: E402

FAILS: list[str] = []


def check(label: str, got, want, tol: float = 0.0) -> None:
    if isinstance(want, float):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got} want {want}")
    if not ok:
        FAILS.append(label)


def csv_cells() -> dict:
    out = {}
    with (C.OVERLAY / "pooled_e2e_table.csv").open() as f:
        for r in csv.DictReader(f):
            out[(r["corpus"], r["model"], r["think"], r["run"], r["task"], r["arm"])] = r
    return out


def main() -> int:
    ref = csv_cells()

    print("1. open-roster headline cells vs pooled_e2e_table.csv (sweep5v2-live + sweep6-live)")
    for corpus in ("sweep5v2-live", "sweep6-live"):
        cells = C.open_cells(corpus)
        bad = 0
        n_cells = 0
        for mkey, rows in cells.items():
            for task in C.TASKS:
                for arm in C.ARMS:
                    a = C.agg([r for r in rows if r["task"] == task and r["arm"] == arm])
                    run = "—"
                    want = ref[(corpus, mkey, "off", run, task, arm)]
                    n_cells += 1
                    if (a["n"], a["ok"], a["cens"], a["tv_ok"], a["tv_n"]) != (
                            int(want["n"]), int(want["ok_strict"]), int(want["censored"]),
                            int(want["tv_ok"]), int(want["tv_n"])):
                        bad += 1
                        print("    mismatch", corpus, mkey, task, arm, a, want)
        check(f"{corpus}: {n_cells} cells identical to the CSV (mismatches)", bad, 0)

    print("2. NUMBERS.md 'Abstract' row: Gemma validate_plan invocation 622/3000 -> 2808/3000")
    g = C.open_cells()["gemma4_26b-a4b"]
    for arm, want_called, want_ok in (("tl-neut", 622, 617), ("tl-ster", 2808, None)):
        rows = [r for r in g if r["task"] == "validate_plan" and r["arm"] == arm]
        called = [r for r in rows if r["tool_selected"] is True]
        check(f"gemma validate_plan {arm} called", len(called), want_called)
        if want_ok is not None:
            check(f"gemma validate_plan {arm} ok|called",
                  sum(1 for r in called if r["success"]), want_ok)
    check("gemma validate_plan canonical delivered cens (NUMBERS: c2790/3000)",
          C.agg([r for r in g if r["task"] == "validate_plan" and r["arm"] == "tl-neut"])["cens"], 2790)

    print("3. NUMBERS.md Job 2: open-roster unaided simulate 0/3,000 format-exact (10 no-tools cells)")
    tot = ok = 0
    mix: dict[str, int] = {}
    for d in sorted((C.RESULTS / "sweep5v2-live").glob("slurm_vllm_*_no-tools")):
        for ln in (d / "trials.jsonl").open():
            r = json.loads(ln)["result"]
            if r["task"] != "simulate":
                continue
            tot += 1
            ok += bool(r["success"])
            mix[r["failure_reason"]] = mix.get(r["failure_reason"], 0) + 1
    check("simulate no-tools rows", tot, 3000)
    check("simulate no-tools strict successes", ok, 0)
    check("failure mix", (mix.get("truncated_no_answer"), mix.get("format_parse_fail"),
                          mix.get("result_mismatch")), (1772, 1202, 26))

    print("4. NUMBERS.md Job 2: delivered cost-of-pass multiplier, pooled >=9B, tl-ster / nt-neut")
    cells = C.open_cells()
    allrows = [r for rows in cells.values() for r in rows]
    want_rng = {"solve": (0.65, 1.64), "validate_domain": (2.81, 2.91),
                "validate_problem": (4.41, 4.86), "validate_plan": (4.11, 5.16)}
    for task, (wlo, whi) in want_rng.items():
        def cop(arm):
            rows = [r for r in allrows if r["task"] == task and r["arm"] == arm]
            a = C.agg(rows)
            tok = sum(r["in_tok"] + r["out_tok"] for r in rows)
            return tok / (a["ok"] + a["cens"]), tok / a["ok"]
        nt_lo, nt_hi = cop("nt-neut")
        tl_lo, tl_hi = cop("tl-ster")
        check(f"{task} low", round(tl_lo / nt_hi, 2), wlo, 0.005)
        check(f"{task} high", round(tl_hi / nt_lo, 2), whi, 0.005)

    print("5. NUMBERS.md Job 2: frontier delivered cost-of-pass, solve (v11, canonical)")
    for corpus, want_wt, want_nt, want_x in (("sonnet-frontier", 18634, 6022, 3.1),
                                             ("haiku-frontier", 48520, 7997, 6.1)):
        wt = [r for r in C.load_cell(corpus, "sweep5v2-with-tools") if r["task"] == "solve"]
        nt = [r for r in C.load_cell(corpus, "sweep5v2")
              if r["task"] == "solve" and r["pv"] == 11]
        wt_tok = sum(r["in_tok"] + r["out_tok"] + r["cache_write"] + r["cache_read"] for r in wt)
        nt_tok = sum(r["in_tok"] + r["out_tok"] for r in nt)
        wt_ok, nt_ok = C.agg(wt)["ok"], C.agg(nt)["ok"]
        check(f"{corpus} WT delivered ok/100", (wt_ok, len(wt)), (95, 100))
        check(f"{corpus} WT tokens/pass", round(wt_tok / wt_ok), want_wt)
        check(f"{corpus} NT tokens/pass (v11)", round(nt_tok / nt_ok), want_nt)
        check(f"{corpus} ratio", round(wt_tok / wt_ok / (nt_tok / nt_ok), 1), want_x, 0.05)

    print("6. NUMBERS.md 'Abstract' row: frontier solve unaided 22/100 (Haiku), 86/300 (Sonnet)")
    h = [r for r in C.load_cell("haiku-frontier", "sweep5v2") if r["task"] == "solve"]
    s = [r for r in C.load_cell("sonnet-frontier", "sweep5v2") if r["task"] == "solve"]
    check("haiku NT solve", (C.agg(h)["ok"], len(h)), (22, 100))
    check("sonnet NT solve", (C.agg(s)["ok"], len(s)), (86, 300))

    print()
    print("ALL CHECKS PASS" if not FAILS else f"{len(FAILS)} CHECK(S) FAILED: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
