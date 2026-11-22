#!/usr/bin/env python3
"""D5a thinking pilot: key selection and the outcome-blind token report.

Plan step D5a (frontier thinking on), pilot approved 2026-11-09 with a hard
cap of $40 at list price. The pilot measures thinking tokens so the full D5a
cost can be re-estimated. It must not look at outcomes before the D1f prereg
registers the D5a cells, so nothing here grades a plan: `report` counts
tokens, stop reasons and whether an answer PARSES into a plan, never whether
the plan is valid.

  keys   --trials results/sonnet-frontier/sweep5v2/trials.jsonl --n 20
         --seed 20261109 --out results/frontier-d5a-pilot/keys
         Reads only the `key` field of the existing Sonnet 4.6 unaided solve
         rows (canonical corpus). Sorts the keys, shuffles them with the seed,
         and walks the order taking the first N with distinct
         (domain, problem); the wording (v11-v13) is whatever the seed gives.
         Writes sonnet_keys.jsonl (those keys), haiku_v11_keys.jsonl (same
         problems at v11, the wording the Haiku cell ran) and
         correa_keys.jsonl (sonnet keys minus the excluded Gripper domain).
  report --pilot-dir results/frontier-d5a-pilot [--arms a b c d e]
         Per arm: thinking tokens, visible output tokens, stop reasons, the
         share at max_tokens, the answer-parse rate, wall time and the cost
         from usage; then the cost re-estimate for the full D5a set.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pddl_eval.schemas import SolveResponse  # noqa: E402
from pddl_eval.scoring import _safe_pydantic_validate, extract_plan_lines  # noqa: E402
from tools.claude_api_batch import LIST_PRICES  # noqa: E402

CORREA_EXCLUDED_DOMAINS = ("gripper",)
# Corrêa et al.'s own extractor (end-to-end.py, Zenodo 10.5281/zenodo.17400964).
CORREA_PLAN_RE = re.compile(r"<plan>(.*?)</plan>", re.DOTALL)

# Arms as registered in the 2026-11-09 brief. `parse` = which extractor
# decides whether the answer contains a plan.
ARMS = {
    "a": {"label": "Sonnet 4.6, thinking on (budget 32000)", "parse": "harness"},
    "b": {"label": "Haiku 4.5, thinking on (budget 32000)", "parse": "harness"},
    "c": {"label": "Sonnet 5.5, thinking on (adaptive, effort high)", "parse": "harness"},
    "d": {"label": "Sonnet 5.5, between_tools (effort high)", "parse": "harness"},
    "e": {"label": "Sonnet 4.6, Correa 2-shot, thinking off, T=0", "parse": "correa"},
}

# Full D5a set as itemised in development/draft_D5_cost_and_correa.md.
# (line, trials, measured-from arm or None, fallback input/output per trial)
FULL_SET = [
    ("Sonnet 4.6 thinking on, 300 keys x3", 900, "a", None),
    ("Haiku 4.5 thinking on, 100 keys x3", 300, "b", None),
    ("Sonnet 5.5 thinking on (adaptive), 300 x3", 900, "c", None),
    ("Sonnet 5.5 between_tools, 300 x3", 900, "d", None),
    # T=1 controls: thinking off, so the existing T=0 cells' measured tokens
    # are the estimate (draft, "Measured token counts").
    ("Sonnet 4.6 thinking off, T=1, x3", 900, None, ("claude-sonnet-4-6", 1457, 261)),
    ("Haiku 4.5 thinking off, T=1, x3", 300, None, ("claude-haiku-4-5", 1456, 304)),
]


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------
def pick_keys(keys: list[list], n: int, seed: int) -> list[dict]:
    """Seeded pick of n solve keys with distinct (domain, problem)."""
    solve = sorted({(k[2], k[3], k[4], int(k[5])) for k in keys if k[1] == "solve"})
    rng = random.Random(seed)
    rng.shuffle(solve)
    out, seen = [], set()
    for dname, pname, plan_label, pv in solve:
        if (dname, pname) in seen:
            continue
        seen.add((dname, pname))
        out.append({"task": "solve", "domain_name": dname, "problem_name": pname,
                    "plan_label": plan_label, "prompt_variant": pv})
        if len(out) == n:
            break
    if len(out) < n:
        raise ValueError(f"only {len(out)} distinct problems available")
    return out


def cmd_keys(args) -> None:
    keys = []
    for line in Path(args.trials).read_text().splitlines():
        if line.strip():
            keys.append(json.loads(line)["key"])  # the key only, never the result
    picked = pick_keys(keys, args.n, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    def write(name, rows):
        (out / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"[keys] {name}: {len(rows)}")

    write("sonnet_keys.jsonl", picked)
    write("haiku_v11_keys.jsonl", [dict(k, prompt_variant=11) for k in picked])
    write("correa_keys.jsonl", [k for k in picked
                                if k["domain_name"] not in CORREA_EXCLUDED_DOMAINS])
    (out / "selection.json").write_text(json.dumps({
        "source": str(args.trials), "seed": args.seed, "n": args.n,
        "rule": "sort solve keys (domain, problem, plan_label, variant); "
                "random.Random(seed).shuffle; take the first n with distinct "
                "(domain, problem)",
        "variants": dict(Counter(k["prompt_variant"] for k in picked)),
        "correa_excluded_domains": list(CORREA_EXCLUDED_DOMAINS),
    }, indent=2) + "\n")


# ---------------------------------------------------------------------------
# report (outcome-blind)
# ---------------------------------------------------------------------------
def answer_parses(answer: str, mode: str) -> dict:
    """Does the answer contain a plan the extractor can read? No validity."""
    if mode == "correa":
        m = CORREA_PLAN_RE.search(answer or "")
        lines = extract_plan_lines(m.group(1)) if m else []
        return {"parses": bool(lines), "path": "plan_tags" if m else "none",
                "n_actions": len(lines)}
    parsed = _safe_pydantic_validate(SolveResponse, answer or "")
    lines = parsed.plan if parsed else extract_plan_lines(answer or "")
    path = "json" if parsed else ("free_text" if lines else "none")
    return {"parses": bool(lines), "path": path, "n_actions": len(lines)}


def _q(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    # nearest-rank percentile: the ceil(q * n)-th smallest value
    idx = max(0, min(len(v) - 1, math.ceil(q * len(v)) - 1))
    return v[idx]


def _stats(values: list) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "median": None, "p90": None, "max": None, "mean": None}
    return {"n": len(vals), "median": statistics.median(vals), "p90": _q(vals, 0.9),
            "max": max(vals), "mean": statistics.fmean(vals)}


def _bootstrap_mean_ci(values: list[float], seed: int = 1, reps: int = 10000) -> tuple:
    if len(values) < 2:
        return (None, None)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(statistics.fmean(rng.choices(values, k=n)) for _ in range(reps))
    return (means[int(0.025 * reps)], means[int(0.975 * reps) - 1])


def row_cost(row: dict, model: str, batch: bool) -> float:
    in_p, out_p = LIST_PRICES[model]
    u = row.get("usage") or {}
    cache_w = u.get("cache_creation_input_tokens") or 0
    cache_r = u.get("cache_read_input_tokens") or 0
    cost = (row["input_tokens"] * in_p + row["output_tokens"] * out_p
            + cache_w * in_p * 1.25 + cache_r * in_p * 0.1)
    return cost / 2 if batch else cost


def arm_report(arm_dir: Path, parse_mode: str) -> dict:
    rows = [json.loads(l) for l in (arm_dir / "results_full.jsonl").read_text().splitlines() if l]
    info = json.loads((arm_dir / "batch_info.json").read_text())
    settings = json.loads((arm_dir / "request_settings.json").read_text())
    model = settings["model"]
    ok = [r for r in rows if r["type"] == "succeeded"]
    max_tokens = {r["custom_id"]: r["request_settings"]["max_tokens"] for r in ok}
    thinking = [r.get("thinking_tokens") for r in ok]
    # Visible output: output - thinking, both from usage. When usage gives no
    # thinking count and the response has no thinking block, nothing was
    # thought, so all output is visible.
    visible = []
    for r in ok:
        if r.get("visible_output_tokens") is not None:
            visible.append(r["visible_output_tokens"])
        elif r.get("thinking_tokens") is None and not r.get("n_thinking_blocks"):
            visible.append(r["output_tokens"])
        else:
            visible.append(None)
    parses = [answer_parses(r.get("answer", ""), parse_mode) for r in ok]
    stops = Counter(r.get("stop_reason") for r in ok)
    at_cap = sum(1 for r in ok if r.get("stop_reason") == "max_tokens")
    out_tok = [r["output_tokens"] for r in ok]
    return {
        "model": model,
        "model_ids": sorted({r.get("model_id") for r in ok}),
        "sdk_versions": sorted({r.get("sdk_version") for r in rows}),
        "n": len(rows), "n_succeeded": len(ok),
        "errors": [r.get("error") for r in rows if r["type"] != "succeeded"],
        "max_tokens": sorted(set(max_tokens.values())),
        "thinking_tokens": _stats(thinking),
        "thinking_tokens_reported": sum(1 for t in thinking if t is not None),
        "thinking_blocks_nonempty": sum(1 for r in ok if r.get("thinking_text")),
        "visible_output_tokens": _stats(visible),
        "output_tokens": _stats(out_tok),
        "output_tokens_mean_ci95": _bootstrap_mean_ci([float(x) for x in out_tok]),
        "input_tokens": _stats([r["input_tokens"] for r in ok]),
        "stop_reasons": dict(stops),
        "share_at_max_tokens": at_cap / len(ok) if ok else None,
        "parse_rate": sum(p["parses"] for p in parses) / len(ok) if ok else None,
        "parse_paths": dict(Counter(p["path"] for p in parses)),
        "wall_seconds": info.get("wall_seconds"),
        "cost_batch_usd": sum(row_cost(r, model, True) for r in ok),
        "cost_list_usd": sum(row_cost(r, model, False) for r in ok),
    }


def full_set_estimate(reports: dict) -> list[dict]:
    out = []
    for line, trials, arm, fallback in FULL_SET:
        if arm is not None:
            if arm not in reports:
                out.append({"line": line, "trials": trials, "batch_usd": None,
                            "note": f"arm {arm} not run"})
                continue
            rep = reports[arm]
            model = rep["model"]
            in_tok = rep["input_tokens"]["mean"]
            out_mean = rep["output_tokens"]["mean"]
            lo, hi = rep["output_tokens_mean_ci95"]
            src = f"pilot arm {arm} (n={rep['n_succeeded']})"
        else:
            model, in_tok, out_mean = fallback
            lo = hi = None
            src = "existing T=0 cell means (draft)"
        in_p, out_p = (p / 2 for p in LIST_PRICES[model])
        est = trials * (in_tok * in_p + out_mean * out_p)
        row = {"line": line, "trials": trials, "model": model,
               "input_per_trial": round(in_tok), "output_per_trial": round(out_mean),
               "batch_usd": round(est, 2), "source": src}
        if lo is not None:
            row["batch_usd_ci95"] = (round(trials * (in_tok * in_p + lo * out_p), 2),
                                     round(trials * (in_tok * in_p + hi * out_p), 2))
        out.append(row)
    return out


def _fmt(v, nd=0):
    if v is None:
        return "n/a"
    return f"{v:,.{nd}f}"


def cmd_report(args) -> None:
    pdir = Path(args.pilot_dir)
    reports = {}
    for arm in args.arms:
        d = pdir / arm
        if not (d / "results_full.jsonl").exists():
            print(f"[report] arm {arm}: no results_full.jsonl, skipped")
            continue
        reports[arm] = arm_report(d, ARMS[arm]["parse"])
    est = full_set_estimate(reports)
    doc = {"arms": reports, "full_set_estimate_batch": est,
           "total_cost_batch_usd": sum(r["cost_batch_usd"] for r in reports.values()),
           "total_cost_list_usd": sum(r["cost_list_usd"] for r in reports.values()),
           "note": "outcome-blind: no plan validity or success rate computed"}
    (pdir / "pilot_report.json").write_text(json.dumps(doc, indent=2) + "\n")

    print("| arm | model | n | thinking tok median / p90 / max | visible out median / p90 / max "
          "| stop reasons | at max_tokens | parses | wall | cost (batch) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for arm, r in reports.items():
        t, v = r["thinking_tokens"], r["visible_output_tokens"]
        print(f"| {arm} | {r['model']} | {r['n_succeeded']}/{r['n']} "
              f"| {_fmt(t['median'])} / {_fmt(t['p90'])} / {_fmt(t['max'])} "
              f"| {_fmt(v['median'])} / {_fmt(v['p90'])} / {_fmt(v['max'])} "
              f"| {', '.join(f'{k} {n}' for k, n in r['stop_reasons'].items())} "
              f"| {r['share_at_max_tokens']:.0%} | {r['parse_rate']:.0%} "
              f"| {_fmt((r['wall_seconds'] or 0) / 60, 1)} min | ${r['cost_batch_usd']:.2f} |")
    print(f"\ntotal spend: ${doc['total_cost_batch_usd']:.2f} billed (Batch API), "
          f"${doc['total_cost_list_usd']:.2f} at list price")
    print("\n| full D5a line | trials | in / out per trial | Batch $ (95% CI on mean output) |")
    print("|---|---|---|---|")
    tot = 0.0
    for e in est:
        if e.get("batch_usd") is None:
            print(f"| {e['line']} | {e['trials']} | n/a | {e['note']} |")
            continue
        tot += e["batch_usd"]
        ci = e.get("batch_usd_ci95")
        ci_s = f" ({ci[0]:.2f} to {ci[1]:.2f})" if ci else ""
        print(f"| {e['line']} | {e['trials']} | {e['input_per_trial']:,} / "
              f"{e['output_per_trial']:,} | ${e['batch_usd']:.2f}{ci_s} |")
    print(f"| total | | | ${tot:.2f} |")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keys")
    k.add_argument("--trials", required=True)
    k.add_argument("--n", type=int, default=20)
    k.add_argument("--seed", type=int, required=True)
    k.add_argument("--out", required=True)
    r = sub.add_parser("report")
    r.add_argument("--pilot-dir", required=True)
    r.add_argument("--arms", nargs="+", default=list(ARMS))
    args = p.parse_args()
    if args.cmd == "keys":
        cmd_keys(args)
    else:
        cmd_report(args)


if __name__ == "__main__":
    main()
