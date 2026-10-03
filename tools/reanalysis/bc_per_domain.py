"""C21 — per-domain and classical-vs-numeric breakdowns of the headline cells.

Headline open models (think off) x task x arm (no-tools / tools-plain /
tools-steered), three wordings pooled exactly as the paper pools them, split by

  (a) the 20 domains, and
  (b) the harness's own track label: the top-level directory under domains/
      ("classical" | "numeric"; pddl_eval/domains.py:44-45 stores it as
      `type` and uses it to pick the oracle planner at domains.py:167).

Scores as in bc_common.py: harness (`success`; tool-verified on tool arms) with
Wilson 95%, and delivered (`e2e_strict`) as a point or a censoring bound.

Also prints:
  * driver flags: cells where one domain moves the pooled number. A cell is
    flagged when dropping a single domain shifts the pooled harness rate by
    >= 3.0 pp, or when one domain holds >= 40% of the cell's rarer outcome
    (successes when the rate is under 50%, failures otherwise; at least 5 such
    rows in the cell).
  * the solve cost-of-pass multiplier (tokens per success, tools / no-tools,
    pooled over the three models as in the paper) split classical vs numeric.

    python3 tools/reanalysis/bc_per_domain.py [--corpus sweep5v2-live]

Writes out/breakdowns_cost/{per_domain,track,drivers,solve_cost_by_track}_<corpus>.*
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bc_common as C  # noqa: E402


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def cell_record(a: dict) -> dict:
    lo, hi = C.wilson(a["harness_ok"], a["n"])
    return {
        "n": a["n"], "harness_ok": a["harness_ok"],
        "harness_rate": round(a["harness_ok"] / a["n"], 4) if a["n"] else "",
        "harness_wilson_lo": round(lo, 4), "harness_wilson_hi": round(hi, 4),
        "called": a["called"],
        "delivered_ok": a["ok"], "delivered_censored": a["cens"],
        "delivered_low": round(a["ok"] / a["n"], 4) if a["n"] else "",
        "delivered_high": round((a["ok"] + a["cens"]) / a["n"], 4) if a["n"] else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="sweep5v2-live")
    args = ap.parse_args()
    cells = C.open_cells(args.corpus)
    track = C.domain_track()
    domains = sorted(track, key=lambda d: (track[d], d))
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = args.corpus

    # index rows: (model, task, arm) -> domain -> rows
    idx: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for mkey, rows in cells.items():
        for r in rows:
            if r["arm"] in C.ARMS:
                idx[(mkey, r["task"], r["arm"])][r["domain"]].append(r)

    # ---------------------------------------------------------------- per domain
    dom_csv, md = [], [f"# Per-domain success, {tag}, think off", "",
                       "Each cell: harness score % [Wilson 95%]; on tool arms the second "
                       "line is delivered (point, or ⟨low, high⟩ with the censored count).",
                       ""]
    compact = [f"# Per-domain success (compact), {tag}, think off", "",
               "Harness score % (tool-verified on tool arms). nt = no-tools, "
               "pl = tools-plain, st = tools-steered.", ""]
    for task in C.TASKS:
        n_dom = len(idx[(C.HEADLINE[0][0], task, "nt-neut")][domains[0]])
        md += [f"## {task} (n = {n_dom} per domain per arm)", ""]
        compact += [f"## {task} (n = {n_dom} per domain per arm)", ""]
        hdr = ["domain", "track"] + [f"{disp} {C.ARM_DISP[arm]}"
                                      for _k, disp in C.HEADLINE for arm in C.ARMS]
        chdr = ["domain", "track"] + [f"{disp.split()[0]} {s}"
                                       for _k, disp in C.HEADLINE for s in ("nt", "pl", "st")]
        trows, crows = [], []
        for d in domains:
            row, crow = [d, track[d]], [d, track[d]]
            for mkey, _disp in C.HEADLINE:
                for arm in C.ARMS:
                    a = C.agg(idx[(mkey, task, arm)][d])
                    dom_csv.append({"corpus": tag, "model": mkey, "task": task, "arm": arm,
                                    "domain": d, "track": track[d], **cell_record(a)})
                    cell = C.fmt_rate(a["harness_ok"], a["n"])
                    if arm != "nt-neut" or a["cens"]:
                        cell += "<br>dlv " + C.fmt_deliv(a)
                    row.append(cell)
                    crow.append(f"{100 * a['harness_ok'] / a['n']:.0f}")
            trows.append(row)
            crows.append(crow)
        md += [C.md_table(hdr, trows), ""]
        compact += [C.md_table(chdr, crows), ""]
    write_csv(C.OUT_DIR / f"per_domain_{tag}.csv", dom_csv)
    (C.OUT_DIR / f"per_domain_{tag}.md").write_text("\n".join(md) + "\n")
    (C.OUT_DIR / f"per_domain_compact_{tag}.md").write_text("\n".join(compact) + "\n")

    # ---------------------------------------------------------------- drivers
    drv_rows = []
    for mkey, mdisp in C.HEADLINE:
        for task in C.TASKS:
            for arm in C.ARMS:
                per = {d: C.agg(idx[(mkey, task, arm)][d]) for d in domains}
                n = sum(a["n"] for a in per.values())
                k = sum(a["harness_ok"] for a in per.values())
                rate = 100 * k / n
                loo = {d: 100 * (k - a["harness_ok"]) / (n - a["n"]) for d, a in per.items()}
                d_lo = min(loo, key=loo.get)
                d_hi = max(loo, key=loo.get)
                rare_is_success = rate < 50
                rare = {d: (a["harness_ok"] if rare_is_success else a["n"] - a["harness_ok"])
                        for d, a in per.items()}
                rare_tot = sum(rare.values())
                top = max(rare, key=rare.get)
                share = 100 * rare[top] / rare_tot if rare_tot else 0.0
                rates = {d: 100 * a["harness_ok"] / a["n"] for d, a in per.items()}
                shift = max(abs(loo[d_lo] - rate), abs(loo[d_hi] - rate))
                flag = (shift >= 3.0) or (rare_tot >= 5 and share >= 40.0)
                drv_rows.append({
                    "corpus": tag, "model": mkey, "task": task, "arm": arm, "n": n,
                    "pooled_rate": round(rate, 1),
                    "domain_min": f"{min(rates, key=rates.get)}={min(rates.values()):.0f}",
                    "domain_max": f"{max(rates, key=rates.get)}={max(rates.values()):.0f}",
                    "domains_at_0": sum(1 for v in rates.values() if v == 0),
                    "domains_at_100": sum(1 for v in rates.values() if v == 100),
                    "loo_low": f"{loo[d_lo]:.1f} (drop {d_lo})",
                    "loo_high": f"{loo[d_hi]:.1f} (drop {d_hi})",
                    "max_loo_shift_pp": round(shift, 1),
                    "rare_outcome": "success" if rare_is_success else "failure",
                    "rare_total": rare_tot, "top_domain": top,
                    "top_domain_share_pct": round(share, 1),
                    "flag": "DRIVER" if flag else "",
                })
    write_csv(C.OUT_DIR / f"drivers_{tag}.csv", drv_rows)
    dmd = [f"# Driver flags, {tag}, think off (harness score)", "",
           C.md_table(
               ["model", "task", "arm", "pooled %", "lowest domain", "highest domain",
                "domains at 0 / at 100", "leave-one-out range", "top domain of the rarer outcome"],
               [[C.MODEL_DISP[r["model"]], r["task"], C.ARM_DISP[r["arm"]], r["pooled_rate"],
                 r["domain_min"], r["domain_max"],
                 f"{r['domains_at_0']} / {r['domains_at_100']}",
                 f"{r['loo_low']} .. {r['loo_high']}",
                 f"{r['top_domain']}: {r['top_domain_share_pct']}% of {r['rare_total']} "
                 + ("successes" if r["rare_outcome"] == "success" else "failures")]
                for r in drv_rows if r["flag"]]), ""]
    (C.OUT_DIR / f"drivers_{tag}.md").write_text("\n".join(dmd) + "\n")

    # ---------------------------------------------------------------- track split
    trk_csv, tmd = [], [f"# Classical vs numeric, {tag}, think off", ""]
    for task in C.TASKS:
        tmd += [f"## {task}", ""]
        trows = []
        for mkey, mdisp in C.HEADLINE:
            for arm in C.ARMS:
                agg = {}
                for t in ("classical", "numeric"):
                    rows = [r for d in domains if track[d] == t
                            for r in idx[(mkey, task, arm)][d]]
                    agg[t] = C.agg(rows)
                    trk_csv.append({"corpus": tag, "model": mkey, "task": task, "arm": arm,
                                    "track": t, **cell_record(agg[t])})
                c, nu = agg["classical"], agg["numeric"]
                diff = 100 * (nu["harness_ok"] / nu["n"] - c["harness_ok"] / c["n"])
                label = "tool-verified" if arm != "nt-neut" else "final answer, strict"
                trows.append([mdisp, C.ARM_DISP[arm], label, c["n"],
                              C.fmt_rate(c["harness_ok"], c["n"]),
                              C.fmt_rate(nu["harness_ok"], nu["n"]), f"{diff:+.1f}"])
                if arm != "nt-neut" or c["cens"] or nu["cens"]:
                    trows.append(["", "", "delivered", c["n"], C.fmt_deliv(c),
                                  C.fmt_deliv(nu), ""])
        tmd += [C.md_table(["model", "arm", "score", "n per track", "classical",
                            "numeric", "numeric - classical (pp)"], trows), ""]
    write_csv(C.OUT_DIR / f"track_{tag}.csv", trk_csv)

    # ---------------------------------------------------------------- solve cost by track
    tmd += ["## solve cost-of-pass by track (pooled over the three models)", "",
            "Tokens = prompt + completion summed over turns (the paper's count). "
            "Cost-of-pass = total tokens / successes. Multiplier = tools / no-tools. "
            "Delivered is a range because the tool arm's delivered count is a bound.", ""]
    cost_rows, crows = [], []
    for t in ("all", "classical", "numeric"):
        def pool(arm):
            rows = [r for mkey, _ in C.HEADLINE for d in domains
                    if t in ("all", track[d]) for r in idx[(mkey, "solve", arm)][d]]
            a = C.agg(rows)
            a["tok"] = sum(r["in_tok"] + r["out_tok"] for r in rows)
            a["in"] = sum(r["in_tok"] for r in rows)
            a["out"] = sum(r["out_tok"] for r in rows)
            return a
        nt = pool("nt-neut")
        for arm in ("tl-neut", "tl-ster"):
            tl = pool(arm)
            nt_cop = nt["tok"] / nt["ok"] if nt["ok"] else float("inf")
            tv = (tl["tok"] / tl["tv_ok"]) / nt_cop
            d_lo = (tl["tok"] / (tl["ok"] + tl["cens"])) / nt_cop
            d_hi = (tl["tok"] / tl["ok"]) / nt_cop if tl["ok"] else float("inf")
            rec = {
                "corpus": tag, "track": t, "arm": arm,
                "nt_n": nt["n"], "nt_ok": nt["ok"], "nt_tokens": nt["tok"],
                "nt_tokens_per_trial": round(nt["tok"] / nt["n"]),
                "nt_tokens_per_pass": round(nt_cop),
                "tl_n": tl["n"], "tl_tv_ok": tl["tv_ok"], "tl_deliv_ok": tl["ok"],
                "tl_deliv_cens": tl["cens"], "tl_tokens": tl["tok"],
                "tl_tokens_per_trial": round(tl["tok"] / tl["n"]),
                "mult_tool_verified": round(tv, 2),
                "mult_delivered_low": round(d_lo, 2), "mult_delivered_high": round(d_hi, 2),
            }
            cost_rows.append(rec)
            crows.append([t, C.ARM_DISP[arm],
                          f"{nt['ok']}/{nt['n']} ({100 * nt['ok'] / nt['n']:.1f}%)",
                          f"{rec['nt_tokens_per_trial']:,}", f"{rec['nt_tokens_per_pass']:,}",
                          f"{tl['tv_ok']}/{tl['n']}",
                          f"⟨{tl['ok']}, {tl['ok'] + tl['cens']}⟩/{tl['n']}",
                          f"{rec['tl_tokens_per_trial']:,}",
                          f"{tv:.2f}x", f"{d_lo:.2f}x to {d_hi:.2f}x"])
    write_csv(C.OUT_DIR / f"solve_cost_by_track_{tag}.csv", cost_rows)
    tmd += [C.md_table(["track", "tool arm", "no-tools successes", "no-tools tok/trial",
                        "no-tools tok/pass", "tool-verified ok", "delivered ok ⟨low, high⟩",
                        "tools tok/trial", "multiplier, tool-verified",
                        "multiplier, delivered"], crows), ""]
    (C.OUT_DIR / f"track_{tag}.md").write_text("\n".join(tmd) + "\n")

    print("\n".join(compact))
    print("\n".join(dmd))
    print("\n".join(tmd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
