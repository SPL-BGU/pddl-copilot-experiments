"""C16 — cost-of-pass under a realistic output:input price ratio.

The paper's cost-of-pass is (total tokens) / (successes), with input and output
tokens added 1:1, and says the tools / no-tools ratio is "invariant to the
per-token price". That is true only when input and output tokens cost the same.
This script recomputes the same ratio with the two token kinds priced apart.

    cost(arm, r)        = input_tokens + r * output_tokens        (r = out:in price)
    cost_of_pass(arm)   = cost / successes
    multiplier          = cost_of_pass(tools) / cost_of_pass(no-tools)
                          (< 1: the tool is cheaper per success; > 1: dearer)

Columns: input tokens only (r = 0), output tokens only (r = infinity), and
r = 1 (the paper), 3, 4, 5.

Two scores, same cells as the paper:
  delivered      successes = e2e_strict. Where rows are censored the success
                 count is a bound, so the multiplier is a range
                 (low = tools at its upper bound / no-tools at its lower bound,
                  high = the reverse), exactly as make_paper_figures.py:477-517.
  tool-verified  tools successes = tool call correct; no-tools successes = the
                 stored grade of its final answer (the paper's "mechanism layer"
                 0.3-0.4x figure).

Cells
  open roster   sweep5v2-live, think off, the three headline models pooled
                (rq_deck.MODELS_9B) and each alone; tools-steered / no-tools
                (the paper's pairing) and tools-plain / no-tools.
  frontier      haiku-frontier and sonnet-frontier, canonical corpus, wording
                v11 on both arms (the paper's frontier cells).

Frontier token accounting, three ways (all from the same stored fields):
  raw           input = prompt + cache_write + cache_read  (the paper's count,
                worknote 8.3)
  cache-billed  input = prompt + 1.25*cache_write + 0.10*cache_read, the
                multipliers written in tools/frontier_runner.py:70 and applied
                at :522-523
  as-billed     cache-billed tools arm at list price vs the no-tools arm at the
                Batch API price (list / 2, tools/claude_api_batch.py:101-108);
                the no-tools frontier arm really ran through the Batch API.
List prices come from the repo, not from memory: tools/frontier_runner.py:71-74
(PRICES: claude-sonnet-4-6 $3 in / $15 out, claude-haiku-4-5 $1 in / $5 out per
million tokens; the same table is in tools/frontier_ab_compare.py:30-33 and
tools/claude_api_batch.py:103-106). Both are 5:1.

Latency is not attempted: the batched server multiplexes trials, so per-trial
wall-clock is not recoverable from the logs.

    python3 tools/reanalysis/bc_cost_price_ratio.py

Writes out/breakdowns_cost/cost_price_ratio.{md,csv}.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bc_common as C  # noqa: E402

RATIOS = [("input only", 0.0), ("output only", math.inf), ("1:1 (paper)", 1.0),
          ("3:1", 3.0), ("4:1", 4.0), ("5:1", 5.0)]
LIST_PRICE = {  # $/token (in, out) — tools/frontier_runner.py:71-74
    "sonnet-frontier": (3.0e-6, 15.0e-6),
    "haiku-frontier": (1.0e-6, 5.0e-6),
}


def cost(i: float, o: float, r: float) -> float:
    return o if math.isinf(r) else i + r * o


def arm_totals(rows: list[dict], cache: str = "raw") -> dict:
    a = C.agg(rows)
    if cache == "raw":
        a["in"] = sum(r["in_tok"] + r["cache_write"] + r["cache_read"] for r in rows)
    else:  # cache-billed
        a["in"] = sum(r["in_tok"] + 1.25 * r["cache_write"] + 0.10 * r["cache_read"]
                      for r in rows)
    a["out"] = sum(r["out_tok"] for r in rows)
    return a


def mult_delivered(tl: dict, nt: dict, r: float, nt_scale: float = 1.0):
    """(low, high) multiplier on the delivered score; None where not identified."""
    ct, cn = cost(tl["in"], tl["out"], r), cost(nt["in"], nt["out"], r) * nt_scale
    if tl["ok"] + tl["cens"] == 0 or nt["ok"] + nt["cens"] == 0:
        return None
    tl_lo, nt_lo = ct / (tl["ok"] + tl["cens"]), cn / (nt["ok"] + nt["cens"])
    tl_hi = ct / tl["ok"] if tl["ok"] else math.inf
    nt_hi = cn / nt["ok"] if nt["ok"] else math.inf
    lo = tl_lo / nt_hi if not math.isinf(nt_hi) else 0.0
    hi = tl_hi / nt_lo
    return lo, hi


def mult_tv(tl: dict, nt: dict, r: float, nt_scale: float = 1.0):
    ct, cn = cost(tl["in"], tl["out"], r), cost(nt["in"], nt["out"], r) * nt_scale
    if not tl["tv_ok"] or not nt["harness_ok"]:
        return None
    return (ct / tl["tv_ok"]) / (cn / nt["harness_ok"])


def breakeven(tl_in, tl_out, tl_succ, nt_in, nt_out, nt_succ) -> str:
    """Smallest out:in price ratio r at which the tool is cheaper per success:
    (tl_in + r*tl_out)/tl_succ = (nt_in + r*nt_out)/nt_succ."""
    if not tl_succ or not nt_succ:
        return "not identified"
    a = tl_in / tl_succ - nt_in / nt_succ      # input-cost gap per success (tool - none)
    b = nt_out / nt_succ - tl_out / tl_succ    # output-cost saving per success
    if a <= 0:
        return "any (cheaper on input alone)"
    if b <= 0:
        return "never"
    return f"{a / b:.1f}:1"


def f_rng(x) -> str:
    if x is None:
        return "not identified"
    lo, hi = x
    if math.isinf(hi) and lo == 0.0:
        return "not identified"
    if abs(hi - lo) < 0.005:
        return f"{lo:.2f}x"
    return f"{lo:.2f}x to " + ("inf" if math.isinf(hi) else f"{hi:.2f}x")


def f_pt(x) -> str:
    return "not identified" if x is None else f"{x:.2f}x"


def verdict(x) -> str:
    """Does the tool pay for itself (multiplier < 1)?"""
    if x is None:
        return "not identified"
    lo, hi = x if isinstance(x, tuple) else (x, x)
    if math.isinf(hi) and lo == 0.0:
        return "not identified"
    if hi < 1:
        return "yes"
    if lo > 1:
        return "no"
    return "undecided (range spans 1)"


def main() -> int:
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    md: list[str] = ["# Cost-of-pass under output:input price ratios", ""]
    csv_rows: list[dict] = []

    def emit(group: str, label: str, task: str, tl: dict, nt: dict,
             accounting: str = "raw", nt_scale: float = 1.0) -> tuple[list, list]:
        d_row, t_row = [label, task], [label, task]
        for name, r in RATIOS:
            d = mult_delivered(tl, nt, r, nt_scale)
            t = mult_tv(tl, nt, r, nt_scale)
            d_row.append(f_rng(d))
            t_row.append(f_pt(t))
            csv_rows.append({
                "group": group, "cell": label, "task": task, "accounting": accounting,
                "price_ratio": name,
                "delivered_mult_low": "" if d is None else round(d[0], 3),
                "delivered_mult_high": "" if d is None or math.isinf(d[1]) else round(d[1], 3),
                "delivered_verdict": verdict(d),
                "tool_verified_mult": "" if t is None else round(t, 3),
                "tool_verified_verdict": verdict(t),
                "tools_n": tl["n"], "tools_in": round(tl["in"]), "tools_out": tl["out"],
                "tools_deliv_ok": tl["ok"], "tools_deliv_cens": tl["cens"],
                "tools_tv_ok": tl["tv_ok"],
                "nt_n": nt["n"], "nt_in": round(nt["in"]), "nt_out": nt["out"],
                "nt_deliv_ok": nt["ok"], "nt_deliv_cens": nt["cens"],
                "nt_harness_ok": nt["harness_ok"],
            })
        return d_row, t_row

    hdr = ["cell", "task"] + [n for n, _ in RATIOS]

    # ------------------------------------------------------------ open roster
    cells = C.open_cells()
    groups = [("pooled 3 models", [r for rows in cells.values() for r in rows])]
    groups += [(disp, cells[k]) for k, disp in C.HEADLINE]

    md += ["## A. Open roster (sweep5v2-live, think off)", "",
           "### A0. Token mix per trial (pooled over the three models)", ""]
    mix = []
    for task in C.TASKS:
        for arm in C.ARMS:
            rows = [r for r in groups[0][1] if r["task"] == task and r["arm"] == arm]
            a = arm_totals(rows)
            mix.append([task, C.ARM_DISP[arm], a["n"], f"{a['in'] / a['n']:,.0f}",
                        f"{a['out'] / a['n']:,.0f}", f"{a['in'] / a['out']:.2f}:1",
                        f"{sum(r['turns'] for r in rows) / a['n']:.2f}"])
    md += [C.md_table(["task", "arm", "n", "input tok/trial", "output tok/trial",
                       "input:output", "turns/trial"], mix), ""]

    for arm, title in (("tl-ster", "tools-steered / no-tools (the paper's pairing)"),
                       ("tl-neut", "tools-plain / no-tools")):
        d_rows, t_rows = [], []
        for label, rows in groups:
            for task in C.TASKS:
                tl = arm_totals([r for r in rows if r["task"] == task and r["arm"] == arm])
                nt = arm_totals([r for r in rows if r["task"] == task and r["arm"] == "nt-neut"])
                d, t = emit(f"open {arm}", label, task, tl, nt)
                d_rows.append(d)
                t_rows.append(t)
        md += [f"### A. {title}: multiplier on the DELIVERED score", "",
               C.md_table(hdr, d_rows), "",
               f"### A. {title}: multiplier on the TOOL-VERIFIED score", "",
               C.md_table(hdr, t_rows), ""]

    # break-even price ratios
    be = []
    for arm in ("tl-ster", "tl-neut"):
        for label, rows in groups:
            for task in C.TASKS:
                tl = arm_totals([r for r in rows if r["task"] == task and r["arm"] == arm])
                nt = arm_totals([r for r in rows if r["task"] == task and r["arm"] == "nt-neut"])
                be.append([C.ARM_DISP[arm], label, task,
                           breakeven(tl["in"], tl["out"], tl["ok"] + tl["cens"],
                                     nt["in"], nt["out"], nt["ok"]),
                           breakeven(tl["in"], tl["out"], tl["ok"],
                                     nt["in"], nt["out"], nt["ok"] + nt["cens"]),
                           breakeven(tl["in"], tl["out"], tl["tv_ok"],
                                     nt["in"], nt["out"], nt["harness_ok"])])
    md += ["### A. Break-even output:input price ratio (the tool is cheaper per success above it)", "",
           "Delivered, best case = every censored tool-arm row counted as a success; "
           "delivered, worst case = none counted (the tool pays for certain only above "
           "the worst-case ratio).", "",
           C.md_table(["tool arm", "cell", "task", "delivered, best case",
                       "delivered, worst case", "tool-verified"], be), ""]

    # solve by track under each ratio (pooled 3 models)
    track = C.domain_track()
    d_rows, t_rows = [], []
    for arm in ("tl-ster", "tl-neut"):
        for t in ("classical", "numeric"):
            rows = [r for r in groups[0][1] if r["task"] == "solve" and track[r["domain"]] == t]
            tl = arm_totals([r for r in rows if r["arm"] == arm])
            nt = arm_totals([r for r in rows if r["arm"] == "nt-neut"])
            d, tv = emit(f"open {arm} by track", f"{C.ARM_DISP[arm]}, {t}", "solve", tl, nt)
            d_rows.append(d)
            t_rows.append(tv)
    md += ["### A. solve by track, pooled 3 models: multiplier on the DELIVERED score", "",
           C.md_table(hdr, d_rows), "",
           "### A. solve by track, pooled 3 models: multiplier on the TOOL-VERIFIED score", "",
           C.md_table(hdr, t_rows), ""]

    # ------------------------------------------------------------ frontier
    md += ["## B. Frontier (canonical corpus, wording v11 on both arms)", ""]
    fbe = []
    fmix, blocks = [], {"raw": ([], []), "cache-billed": ([], []), "as-billed": ([], [])}
    dollars = []
    for corpus, disp in (("sonnet-frontier", "Sonnet 4.6"), ("haiku-frontier", "Haiku 4.5")):
        wt_all = C.load_cell(corpus, "sweep5v2-with-tools")
        nt_all = [r for r in C.load_cell(corpus, "sweep5v2") if r["pv"] == 11]
        pin, pout = LIST_PRICE[corpus]
        for task in C.TASKS:
            wt = [r for r in wt_all if r["task"] == task]
            nt = [r for r in nt_all if r["task"] == task]
            raw_t, raw_n = arm_totals(wt), arm_totals(nt)
            cb_t = arm_totals(wt, "cache-billed")
            fmix.append([disp, task,
                         f"{raw_t['in'] / raw_t['n']:,.0f}", f"{raw_t['out'] / raw_t['n']:,.0f}",
                         f"{raw_t['in'] / raw_t['out']:.1f}:1",
                         f"{cb_t['in'] / cb_t['n']:,.0f}",
                         f"{raw_n['in'] / raw_n['n']:,.0f}", f"{raw_n['out'] / raw_n['n']:,.0f}",
                         f"{raw_n['in'] / raw_n['out']:.2f}:1"])
            for key, tl, scale in (("raw", raw_t, 1.0), ("cache-billed", cb_t, 1.0),
                                   ("as-billed", cb_t, 0.5)):
                d, t = emit(f"frontier {key}", disp, task, tl, raw_n, key, scale)
                blocks[key][0].append(d)
                blocks[key][1].append(t)
            fbe.append([disp, task,
                        breakeven(raw_t["in"], raw_t["out"], raw_t["ok"] + raw_t["cens"],
                                  raw_n["in"], raw_n["out"], raw_n["ok"]),
                        breakeven(raw_t["in"], raw_t["out"], raw_t["ok"],
                                  raw_n["in"], raw_n["out"], raw_n["ok"] + raw_n["cens"]),
                        breakeven(cb_t["in"], cb_t["out"], cb_t["ok"],
                                  raw_n["in"], raw_n["out"], raw_n["ok"] + raw_n["cens"])])
            # dollars per delivered pass at the repo's list prices
            wt_usd = cb_t["in"] * pin + cb_t["out"] * pout
            wt_usd_nocache = raw_t["in"] * pin + raw_t["out"] * pout
            nt_usd = raw_n["in"] * pin + raw_n["out"] * pout
            def per(usd, a):
                lo = usd / (a["ok"] + a["cens"])
                hi = usd / a["ok"] if a["ok"] else math.inf
                return f"${lo:.3f}" if abs(hi - lo) < 5e-4 else f"${lo:.3f} to ${hi:.3f}"
            dollars.append([disp, task, per(wt_usd_nocache, raw_t), per(wt_usd, cb_t),
                            per(nt_usd, raw_n), per(nt_usd / 2, raw_n)])
    md += ["### B0. Token mix per trial", "",
           C.md_table(["tier", "task", "tools input raw", "tools output", "tools input:output",
                       "tools input cache-billed", "no-tools input", "no-tools output",
                       "no-tools input:output"], fmix), ""]
    for key, note in (
            ("raw", "raw token count (the paper's accounting); at 5:1 this is list price with caching ignored"),
            ("cache-billed", "tools input priced with the cache multipliers; at 5:1 this is the actual list price, both arms at list"),
            ("as-billed", "as cache-billed, and the no-tools arm at the Batch API price (half list); at 5:1 this is what the two arms were actually charged")):
        md += [f"### B. {key}: multiplier on the DELIVERED score", "", note + ".", "",
               C.md_table(["tier", "task"] + [n for n, _ in RATIOS], blocks[key][0]), "",
               f"### B. {key}: multiplier on the TOOL-VERIFIED score", "",
               C.md_table(["tier", "task"] + [n for n, _ in RATIOS], blocks[key][1]), ""]
    md += ["### B. Break-even output:input price ratio, delivered score", "",
           C.md_table(["tier", "task", "raw, best case", "raw, worst case",
                       "cache-billed, worst case"], fbe), ""]
    md += ["### B. Dollars per delivered pass at list prices (tools/frontier_runner.py:71-74)", "",
           C.md_table(["tier", "task", "tools, list, caching ignored", "tools, list, cache-billed",
                       "no-tools, list", "no-tools, Batch (list / 2)"], dollars), ""]

    (C.OUT_DIR / "cost_price_ratio.md").write_text("\n".join(md) + "\n")
    with (C.OUT_DIR / "cost_price_ratio.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
