#!/usr/bin/env python3
"""Token consumption with and without the planning tools: a descriptive, post hoc analysis.

    python -m tools.reanalysis.token_consumption \\
        --results /abs/pddl-copilot-experiments/results \\
        --marketplace /abs/pddl-copilot-experiments/external/pddl-copilot-5e4f9c0 \\
        [--out tools/reanalysis/out] [--figs development/token_consumption] [--cache FILE]

No registration covers anything here. It reads three corpora, never pools them, and
never lets a figure of one stand for a cell of another:

  matched run     results/matched-run, solve and simulate, arms N (no tools), P (tools,
                  plain wordings) and S (tools, steered wordings); 300 trials per cell;
                  right = the run's registered grade (`matched_run.grade_trials`).
  October rerun   results/delivered-rerun, the three validation tasks only (its no-tools
                  arm on solve and simulate had a faulty system message): Part C (no
                  tools) against Part A (plain, steered); right = the rerun's frozen
                  delivered grade (`rq1_metrics.load_rerun_cells`).
  Claude run      results/frontier55, Haiku 5.5 and Sonnet 5.5, five tasks, arms no tools
                  and tools; right = the run's registered grade (`frontier55.grade_cell`);
                  per-request usage from the sidecar (`frontier55.read_cell`).

The frozen packages are imported and never edited; the script halts before reading any
row when one of the four package hashes differs, and halts when the right counts it
grades differ from the filed outputs (`out/matched_run.json`, `out/frontier55.json`; the
rerun's loader checks its own readout).

How a token is counted (established from pddl_eval/chat.py, pddl_eval/vllm_client.py and
the Claude runner's sidecar):
  open models   `tokens.prompt` and `tokens.completion` of a row are the sums over the
                requests (turns) of the trial of vLLM's usage.prompt_tokens and
                usage.completion_tokens. Every request re-sends the whole conversation,
                so a tool result is counted again as input on every later request.
                Prefix-cache hits are not deducted. A final request refused because the
                prompt alone filled the 16,384-token window is a synthetic turn: its
                prompt size (measured, or the server's lower bound) is added to the input
                and 0 to the output, although the server never generated anything. The
                1-token probe the client sends after an overflow is not counted. Per-turn
                counts are not stored.
  Claude        the same sums, from the provider's usage block of each request (input =
                uncached + cache-written + cache-read; there was no cache). The sidecar
                keeps every request, so the input can be split exactly. The no-tools arm
                is one Batch request per trial, priced at half the list price.

Tokens of different tokenizers are not the same unit: cross-model readings use ratios
within a model (tools arm over no-tools arm).
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

FROZEN = {
    "frontier55": "0cbb69b7f810d039734b0aba15096bda91a6f97c6c334dfd2a0ec8ed59cbb497",
    "matched_run": "1f3d0f84c755820fb73eac810f3aebfc55dca69de663c2467fa430946fd4155d",
    "delivered_rerun": "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9",
    "control": "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79",
}
B_BOOT = 10_000
SEED = 20261002
K_DOMAINS = 20
PRICE_RATIO = 5.0           # output:input price ratio of the price-weighted count (both Claude list prices are 5:1)
WINDOW = 16_384
TASKS = ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate")
OPEN_MODELS = ("Qwen3.5-9B", "Gemma-26B", "Qwen3.6-35B")
CLAUDE_MODELS = ("Claude Haiku 5.5", "Claude Sonnet 5.5")
CLAUDE_TAG = {"claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5"}
ARM_WORDS = {"none": "no tools", "plain": "tools, plain", "steered": "tools, steered",
             "tools": "tools"}
CORPUS_WORDS = {"matched": "matched run", "rerun": "October rerun", "claude": "Claude run"}
TOOL_ARMS = {"matched": ("plain", "steered"), "rerun": ("plain", "steered"), "claude": ("tools",)}
# Qwen3.5-9B and Qwen3.6-35B gave the same first-prompt offset in every cell where both
# could be measured, so they are one tokenizer family for the borrowing rule below.
FAMILY = {"Qwen3.5-9B": "qwen", "Qwen3.6-35B": "qwen", "Gemma-26B": "gemma"}


class Halt(Exception):
    pass


# ================================================================== pure arithmetic (tested)
def price_weighted(inp: float, out: float, r: float = 1.0) -> float:
    """input + r x output: r = 1 is the raw total, r = 5 weights output as a 5:1 price does."""
    return inp + r * out


def cost_per_right(tokens: float, right: int) -> float | None:
    """Tokens of a cell divided by its right answers; None when nothing is right."""
    return None if right <= 0 else tokens / right


def multiplier(tok_tools: float, right_tools: int, tok_none: float, right_none: int) -> float | None:
    """Cost per right answer of the tools arm over that of the no-tools arm (< 1: cheaper)."""
    a, b = cost_per_right(tok_tools, right_tools), cost_per_right(tok_none, right_none)
    return None if a is None or b is None else a / b


def gain_per_1k(right_tools: int, right_none: int, tok_tools: float, tok_none: float,
                n: int) -> float | None:
    """Percentage points of right answers gained per 1,000 extra tokens per trial, both arms
    over the same n trials: 100 (k_t - k_n) / n  divided by  (T_t - T_n) / n / 1000."""
    extra = tok_tools - tok_none
    if n <= 0 or extra <= 0:
        return None
    return 1e5 * (right_tools - right_none) / extra


def split_turns(turn_in: list[int], turn_out: list[int]) -> dict:
    """Exact split of a multi-request trial's summed input (one count per request).

    Request k re-sends request k-1's input, the reply k-1 wrote, and what came back
    between them (the tool results, with the few formatting tokens around them):
        in_k = in_{k-1} + out_{k-1} + tool_{k-1}.
    Over n requests the input is n * in_1 (the first prompt, sent n times) plus
    sum_{k>=2} (n-k+1) * out_{k-1} (the model's own earlier replies, re-read) plus
    sum_{k>=2} (n-k+1) * tool_{k-1} (tool output, re-read); the three add up to the sum."""
    n = len(turn_in)
    if n != len(turn_out) or n == 0:
        raise ValueError("one input and one output count per request")
    first = n * turn_in[0]
    own = tool = 0
    for k in range(1, n):
        reread = n - k
        tool_k = turn_in[k] - turn_in[k - 1] - turn_out[k - 1]
        own += reread * turn_out[k - 1]
        tool += reread * tool_k
    return {"first": first, "own": own, "tool": tool, "total": sum(turn_in)}


def added_context(prompt_sum: int, turns: int, first_prompt: int) -> int:
    """Input beyond the first prompt sent once per request: what the conversation added
    (tool results and the model's own earlier replies, re-read on every later request)."""
    return prompt_sum - turns * first_prompt


def split_added(added: float, calls: list[tuple[int, int]], turns: int) -> tuple[float, float]:
    """(model's own earlier output, tool output) of the added input of an open-model trial,
    split by characters, as an ESTIMATE (the rows hold no per-request counts). `calls` is
    [(characters of the call's arguments, characters of its result)] in order. Call i is
    placed in request min(i, turns - 1) and is re-read turns - that many times."""
    if added <= 0:
        return 0.0, 0.0
    if not calls or turns < 2:
        return float(added), 0.0
    w_own = w_tool = 0.0
    for i, (a, r) in enumerate(calls, 1):
        reread = turns - min(i, turns - 1)
        w_own += reread * a
        w_tool += reread * r
    if w_own + w_tool == 0:
        return float(added), 0.0
    share = w_tool / (w_own + w_tool)
    return added * (1 - share), added * share


def draws(k: int, b: int = B_BOOT, seed: int = SEED) -> np.ndarray:
    """The domain-cluster draws of `gen_common.multiplier_boot` (same generator, same seed)."""
    return np.random.default_rng(seed).integers(0, k, size=(b, k))


def ratio_boot(num: np.ndarray, den: np.ndarray, dr: np.ndarray) -> dict:
    """sum(num) / sum(den) with the 95% percentile interval over domain draws."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    est = num.sum() / den.sum() if den.sum() else math.nan
    a, c = num[dr].sum(1), den[dr].sum(1)
    ok = c > 0
    vals = a[ok] / c[ok]
    lo, hi = (np.quantile(vals, [0.025, 0.975]) if len(vals) else (math.nan, math.nan))
    return {"est": float(est), "lo": float(lo), "hi": float(hi), "dropped": int((~ok).sum())}


def gain_boot(kt, kn, tt, tn, dr: np.ndarray) -> dict | None:
    """`gain_per_1k` with its interval; draws with no extra tokens are dropped and counted."""
    kt, kn, tt, tn = (np.asarray(x, float) for x in (kt, kn, tt, tn))
    est = gain_per_1k(kt.sum(), kn.sum(), tt.sum(), tn.sum(), 1)
    if est is None:
        return None
    dk = kt[dr].sum(1) - kn[dr].sum(1)
    dt = tt[dr].sum(1) - tn[dr].sum(1)
    ok = dt > 0
    vals = 1e5 * dk[ok] / dt[ok]
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return {"est": float(est), "lo": float(lo), "hi": float(hi), "dropped": int((~ok).sum())}


def diff_boot(xt, xn, n, dr: np.ndarray) -> dict:
    """Difference of two per-trial means over the same trials (domain sums xt, xn, counts n)."""
    xt, xn, n = (np.asarray(x, float) for x in (xt, xn, n))
    est = (xt.sum() - xn.sum()) / n.sum()
    vals = (xt[dr].sum(1) - xn[dr].sum(1)) / n[dr].sum(1)
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return {"est": float(est), "lo": float(lo), "hi": float(hi)}


# ================================================================== loading (frozen code)
def check_hashes() -> dict:
    """The four frozen package hashes, or a halt before any row is read."""
    from tools.delivered_rerun import run as RUN
    from tools.reanalysis import control_prompt_fix as M
    from tools.reanalysis import frontier55 as F55
    from tools.reanalysis import matched_run as MR
    got = {"frontier55": F55.package_sha256(), "matched_run": MR.package_sha256(),
           "delivered_rerun": RUN.package_sha256(), "control": M.package_sha256()}
    bad = [f"{k}: {got[k][:12]} (frozen {FROZEN[k][:12]})" for k in FROZEN if got[k] != FROZEN[k]]
    if bad:
        raise Halt("a frozen package changed: " + "; ".join(bad))
    return got


def canon_key(task, domain, problem, label, variant) -> tuple:
    """The pairing key; a steered wording (v14 to v16) is mapped to its plain one."""
    return (task, domain, problem, label, variant - 3 if variant >= 14 else variant)


def _calls(r) -> list[tuple[int, int]]:
    return [(len(json.dumps(c.arguments, ensure_ascii=False)), len(c.result or ""))
            for c in r.tool_calls]


def open_record(corpus, model, arm, r, right: bool, window_full: bool, at_cap: bool) -> dict:
    t = r.tokens
    return {"corpus": corpus, "model": model, "arm": arm, "task": r.task, "domain": r.domain,
            "key": canon_key(r.task, r.domain, r.problem, r.plan_label, r.variant),
            "variant": r.variant, "right": bool(right), "inp": t.prompt, "out": t.completion,
            "turns": t.turns, "window_full": bool(window_full), "at_cap": bool(at_cap),
            "no_room": bool(r.no_room), "calls": _calls(r), "n_calls": len(r.tool_calls),
            "exception": bool(r.is_exception), "turn_in": None, "turn_out": None, "usd": None}


def load_matched(args, gt_cache) -> tuple[list[dict], dict]:
    """The 5,400 trials of the matched run, graded as `rq1_matched_metrics.matched_records`
    grades them (frozen `control_prompt_fix.frozen_grades`, then `matched_run.grade_trials`)."""
    from tools.reanalysis import control_prompt_fix as M
    from tools.reanalysis import matched_run as MR
    from tools.reanalysis.gen_common import model_name
    root = args.results / MR.RUN_TAG
    tags = {m: MR.RUN_TAG for m in MR.MODEL_ORDER}
    folders = MR.load_matched(root, MR.REGISTERED, tags)
    arms = MR.arm_rows(folders)
    verdict = args.verdict
    recs = []
    for m in MR.MODEL_ORDER:
        for fo in MR.FOLDERS:
            rows = [r for arm in MR.ARMS if MR.ARM_FOLDER[arm] == fo for r in arms[m][arm]]
            pairs = M.frozen_grades(rows, verdict, gt_cache)
            trials = MR.grade_trials(pairs, verdict, gt_cache)
            for arm in MR.ARMS:
                if MR.ARM_FOLDER[arm] != fo:
                    continue
                for r in arms[m][arm]:
                    x = trials[r.trial_key]
                    recs.append(open_record("matched", model_name(m), MR.ARM_REC[arm], r,
                                            x.registered, x.window_full, x.at_cap))
    filed = json.loads((args.filed / "matched_run.json").read_text())
    if filed.get("package_sha256") != FROZEN["matched_run"] or filed.get("mode") != "live":
        raise Halt("out/matched_run.json is not the live output of the frozen matched run")
    want = {(model_name(r["model"]), r["task"], MR.ARM_REC[r["cell"]]):
            (r[MR.REGISTERED_GRADE]["right"], r[MR.REGISTERED_GRADE]["n"])
            for r in filed["rates"] if r["this_run"]}
    return recs, want


def load_rerun(args) -> tuple[list[dict], dict]:
    """The October rerun's three validation tasks, Part C (no tools) and Part A (plain,
    steered), through the frozen loader and grade (which checks the frozen readout)."""
    from tools.reanalysis import matched_run as MR
    from tools.reanalysis import rq1_metrics as R1
    from tools.reanalysis.gen_common import model_name
    cells, grades, _gt = R1.load_rerun_cells(args)
    recs = []
    for part, arm_of in (("rerun_a", lambda r: r.arm), ("rerun_c", lambda r: "none")):
        for m, lc in cells[part].items():
            for r in lc.rows:
                if r.task in ("solve", "simulate"):
                    continue
                g = grades[(r.cell, r.trial_key)]
                full = MR.window_full(r)
                at_cap = r.done_reason == "length" and not full
                recs.append(open_record("rerun", model_name(m), arm_of(r), r, g.ok is True,
                                        full, at_cap))
    return recs, {}


def load_claude(args, gt_cache) -> tuple[list[dict], dict]:
    """The Claude run through `frontier55.load_run` and `frontier55.grade_cell`; the
    per-request usage from the sidecar; dollars at the registered prices."""
    from tools.frontier55.anthropic_requests import usage_usd
    from tools.reanalysis import frontier55 as F55
    root = args.results / F55.RUN_NAME
    cells = F55.load_run(root, F55.REGISTERED, gt_cache, F55.GT_CACHE_SHA256)
    F55.check_same_trials(cells)
    recs = []
    for m in F55.MODELS:
        for arm in F55.ARMS:
            cell = cells[m][arm]
            graded = F55.grade_cell(cell, args.verdict, gt_cache)
            by_key = {r.trial_key: r for r in cell.rows}
            for key, x in graded.items():
                r, meta = by_key[key], cell.meta[key]
                ti = [u.input_tokens for u in meta.turns]
                to = [u.output_tokens for u in meta.turns]
                usd = sum(usage_usd(m, {"input_tokens": u.input_tokens,
                                        "output_tokens": u.output_tokens},
                                    batch=arm == "no-tools") for u in meta.turns)
                rec = open_record("claude", CLAUDE_TAG[m], "none" if arm == "no-tools" else "tools",
                                  r, x.registered, x.ending == F55.E_NO_ROOM,
                                  x.ending in (F55.E_CAP, F55.E_CAP_EMPTY))
                if (sum(ti), sum(to), len(ti)) != (rec["inp"], rec["out"], rec["turns"]):
                    raise Halt(f"{m}/{arm}/{key}: row tokens differ from the sidecar")
                rec.update(turn_in=ti, turn_out=to, usd=usd, last_out=to[-1],
                           ending=x.ending)
                recs.append(rec)
    filed = json.loads((args.filed / "frontier55.json").read_text())
    if filed.get("package_sha256") != FROZEN["frontier55"] or filed.get("mode") != "live":
        raise Halt("out/frontier55.json is not the live output of the frozen Claude analysis")
    want = {(CLAUDE_TAG[r["model"]], r["task"], "none" if r["arm"] == "no-tools" else "tools"):
            (r["right"], r["n"]) for r in filed["rates"]}
    return recs, want


def load_all(args) -> list[dict]:
    from tools.reanalysis import control_prompt_fix as M
    from tools.reanalysis import frontier55 as F55
    from tools.reanalysis import matched_run as MR
    from tools.reanalysis import rq1_metrics as R1
    R1.fill_data_args(args)
    gt_cache = F55.load_gt_cache(args.gt_cache)
    F55.validator_env(args)
    args.verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
    checked = F55.check_route_table(args.verdict, F55.stored_verdicts(args.plan_verdicts))
    print(f"validator route returned the stored verdict for {checked} plans")
    del MR
    recs, wants = [], {}
    for name, fn in (("matched", lambda: load_matched(args, gt_cache)),
                     ("rerun", lambda: load_rerun(args)),
                     ("claude", lambda: load_claude(args, gt_cache))):
        rs, want = fn()
        print(f"{name}: {len(rs)} trials")
        recs += rs
        wants[name] = want
    check_counts(recs, wants)
    return recs


def check_counts(recs: list[dict], wants: dict) -> None:
    """The right count and the trial count of every cell equal the filed outputs."""
    got = Counter()
    n = Counter()
    for r in recs:
        k = (r["corpus"], r["model"], r["task"], r["arm"])
        got[k] += r["right"]
        n[k] += 1
    bad = []
    for corpus, want in wants.items():
        for (model, task, arm), (k, nn) in want.items():
            key = (corpus, model, task, arm)
            if (got[key], n[key]) != (k, nn):
                bad.append(f"{key}: {got[key]}/{n[key]} vs filed {k}/{nn}")
    if bad:
        raise Halt("right counts differ from the filed outputs:\n  " + "\n  ".join(bad))


# ================================================================== first prompts (open models)
def first_prompt_offsets(recs: list[dict]) -> dict:
    """Per open model, task and tool arm: the first request's input minus the no-tools
    input of the same trial, measured on the tool trials that made one request (halts when
    a cell gives two different values: the method would not hold), else on the two-request
    trials whose second request was refused. Cells with neither borrow: same tokenizer
    family, task and arm; else same model and task; else the median of the same model."""
    none = {(r["corpus"], r["model"], r["key"]): r["inp"] for r in recs
            if r["corpus"] != "claude" and r["arm"] == "none" and not r["exception"]}
    meas = defaultdict(Counter)
    for r in recs:
        if r["corpus"] == "claude" or r["arm"] == "none" or r["turns"] != 1 or r["no_room"] \
                or r["exception"] or (r["corpus"], r["model"], r["key"]) not in none:
            continue
        meas[(r["model"], r["task"], r["arm"])][r["inp"] - none[(r["corpus"], r["model"], r["key"])]] += 1
    measured = {}
    for k, c in meas.items():
        if len(c) != 1:
            raise Halt(f"first-prompt offset of {k} is not one value: {dict(c)}")
        measured[k] = (next(iter(c)), sum(c.values()))
    # Second source: two-request trials whose second request was refused for no room. The
    # client stores a refused request's input as vLLM's lower bound, window - max_tokens + 1
    # = 16,384 for the 1-token probe (pddl_eval/vllm_client.py), so the first request's
    # input is the summed input minus 16,384.
    meas2 = defaultdict(Counter)
    for r in recs:
        if r["corpus"] == "claude" or r["arm"] == "none" or r["turns"] != 2 or not r["no_room"] \
                or r["exception"] or (r["corpus"], r["model"], r["key"]) not in none:
            continue
        meas2[(r["model"], r["task"], r["arm"])][
            r["inp"] - WINDOW - none[(r["corpus"], r["model"], r["key"])]] += 1
    agree = {k: (measured[k][0], dict(meas2[k])) for k in measured if k in meas2}
    known = dict(measured)
    for k, c in meas2.items():
        known.setdefault(k, (c.most_common(1)[0][0], sum(c.values())))
    measured_one = measured
    measured = known          # the borrowing below draws on both sources
    out = {}
    for model in OPEN_MODELS:
        for task in TASKS:
            for arm in ("plain", "steered"):
                k = (model, task, arm)
                if k in measured_one:
                    out[k] = {"offset": measured[k][0], "source": f"measured on {measured[k][1]} one-request trials"}
                    continue
                if k in meas2:
                    v, cnt = meas2[k].most_common(1)[0]
                    out[k] = {"offset": v, "source": (
                        f"measured on {cnt} of {sum(meas2[k].values())} two-request trials "
                        f"whose second request was refused (values {sorted(meas2[k])})")}
                    continue
                fam = [v for (m2, t2, a2), v in measured.items()
                       if FAMILY[m2] == FAMILY[model] and t2 == task and a2 == arm]
                same = [v for (m2, t2, a2), v in measured.items() if m2 == model and t2 == task]
                anyv = [v for (m2, t2, a2), v in measured.items() if m2 == model]
                if fam:
                    out[k] = {"offset": fam[0][0], "source": "borrowed: same tokenizer family, task and arm"}
                elif same:
                    out[k] = {"offset": same[0][0], "source": "borrowed: same model and task, other arm"}
                elif anyv:
                    out[k] = {"offset": int(np.median([v[0] for v in anyv])),
                              "source": "borrowed: median of the same model's measured cells"}
    spread = {}
    for model in OPEN_MODELS:
        vals = [v["offset"] for (m2, _t, _a), v in out.items()
                if m2 == model and not v["source"].startswith("borrowed")]
        spread[model] = (min(vals), max(vals)) if vals else None
    return {"offsets": out, "measured": measured, "spread": spread,
            "both_sources": {"|".join(k): v for k, v in agree.items()}}


def attach_first_prompts(recs: list[dict], fp: dict) -> None:
    none = {(r["corpus"], r["model"], r["key"]): r["inp"] for r in recs
            if r["corpus"] != "claude" and r["arm"] == "none" and not r["exception"]}
    for r in recs:
        if r["arm"] == "none":
            r["first"], r["own"], r["tool"] = r["inp"], 0.0, 0.0
            continue
        if r["corpus"] != "claude" and (r["exception"] or r["turns"] == 0
                                        or (r["corpus"], r["model"], r["key"]) not in none):
            # an exception row (no tokens stored) or a trial whose no-tools partner is
            # one: the input is left unsplit and counted as first prompt
            r["first"] = r["inp"] / max(1, r["turns"])
            r["added"], r["own"], r["tool"], r["unsplit"] = 0, 0.0, 0.0, True
            continue
        if r["corpus"] == "claude":
            s = split_turns(r["turn_in"], r["turn_out"])
            r["first"], r["own"], r["tool"] = s["first"] / len(r["turn_in"]), s["own"], s["tool"]
            r["added"] = s["own"] + s["tool"]
            continue
        p1 = none[(r["corpus"], r["model"], r["key"])] + fp["offsets"][(r["model"], r["task"], r["arm"])]["offset"]
        r["first"] = p1
        r["added"] = added_context(r["inp"], r["turns"], p1)
        r["own"], r["tool"] = split_added(r["added"], r["calls"], r["turns"])


# ================================================================== cells and statistics
def domain_sums(rs: list[dict], doms: list[str], f) -> np.ndarray:
    idx = {d: i for i, d in enumerate(doms)}
    out = np.zeros(len(doms))
    for r in rs:
        out[idx[r["domain"]]] += f(r)
    return out


def tok(r, ratio=1.0) -> float:
    return price_weighted(r["inp"], r["out"], ratio)


def processed(r) -> float:
    """Total tokens without a refused final request (stored as 16,384 input tokens that the
    server never ran)."""
    return r["inp"] + r["out"] - (WINDOW if r["no_room"] else 0)


def cell_stats(rs: list[dict], doms: list[str], dr: np.ndarray) -> dict:
    n = domain_sums(rs, doms, lambda r: 1)
    s = {"n": len(rs), "right": sum(r["right"] for r in rs)}
    s["rate"] = 100 * s["right"] / s["n"]
    for name, f in (("inp", lambda r: r["inp"]), ("out", lambda r: r["out"]),
                    ("total", lambda r: r["inp"] + r["out"]), ("turns", lambda r: r["turns"])):
        s[name] = ratio_boot(domain_sums(rs, doms, f), n, dr)
        s[name + "_median"] = float(np.median([f(r) for r in rs]))
    right = domain_sums(rs, doms, lambda r: r["right"])
    for ratio, nm in ((1.0, "cpr"), (PRICE_RATIO, "cpr5")):
        s[nm] = (ratio_boot(domain_sums(rs, doms, lambda r: tok(r, ratio)), right, dr)
                 if s["right"] else None)
    tot = sum(tok(r) for r in rs)
    s["wrong_token_share"] = 100 * sum(tok(r) for r in rs if not r["right"]) / tot
    s["at_cap"] = sum(r["at_cap"] for r in rs)
    s["window_full"] = sum(r["window_full"] for r in rs)
    s["exceptions"] = sum(r["exception"] for r in rs)
    s["no_call"] = sum(r["n_calls"] == 0 for r in rs)
    s["tokens_by_outcome_per_trial"] = {
        "right": sum(tok(r) for r in rs if r["right"]) / len(rs),
        "wrong_window_full": sum(tok(r) for r in rs if not r["right"] and r["window_full"]) / len(rs),
        "wrong_other": sum(tok(r) for r in rs if not r["right"] and not r["window_full"]) / len(rs)}
    s["total_processed"] = ratio_boot(domain_sums(rs, doms, processed), n, dr)
    s["refused_requests"] = sum(r["no_room"] for r in rs)
    wf = [r for r in rs if r["window_full"]]
    s["window_full_tokens_mean"] = float(np.mean([tok(r) for r in wf])) if wf else None
    s["window_full_token_share"] = 100 * sum(tok(r) for r in wf) / tot
    s["window_full_right"] = sum(r["right"] for r in wf)
    two = [r for r in wf if r["turns"] == 2 and r["no_room"] and r.get("first") is not None]
    s["refused_prompt_2req"] = ([float(np.median([r["inp"] - r["first"] for r in two])),
                                 float(min(r["inp"] - r["first"] for r in two)),
                                 float(max(r["inp"] - r["first"] for r in two)), len(two)]
                                if two and rs[0]["corpus"] != "claude" else None)
    if rs[0]["arm"] != "none":
        first = domain_sums(rs, doms, lambda r: r["turns"] * r["first"])
        inp = domain_sums(rs, doms, lambda r: r["inp"])
        s["share_first"] = ratio_boot(100 * first, inp, dr)
        s["share_own"] = ratio_boot(100 * domain_sums(rs, doms, lambda r: r["own"]), inp, dr)
        s["share_tool"] = ratio_boot(100 * domain_sums(rs, doms, lambda r: r["tool"]), inp, dr)
        s["negative_added"] = sum((r.get("added") or 0) < 0 for r in rs)
        s["unsplit"] = sum(bool(r.get("unsplit")) for r in rs)
    if rs[0]["usd"] is not None:
        s["usd"] = ratio_boot(domain_sums(rs, doms, lambda r: r["usd"]), n, dr)
        s["usd_total"] = sum(r["usd"] for r in rs)
        s["usd_per_right"] = (ratio_boot(domain_sums(rs, doms, lambda r: r["usd"]), right, dr)
                              if s["right"] else None)
        s["last_out"] = float(np.mean([r["last_out"] for r in rs]))
    return s


def contrast(rt: list[dict], rn: list[dict], doms: list[str], dr: np.ndarray) -> dict:
    from tools.reanalysis.gen_common import multiplier_boot
    kt, kn = (sum(r["right"] for r in x) for x in (rt, rn))
    if {r["key"] for r in rt} != {r["key"] for r in rn}:
        raise Halt(f"unpaired trials in {rt[0]['corpus']}/{rt[0]['model']}/{rt[0]['task']}")
    st = domain_sums(rt, doms, lambda r: r["right"])
    sn = domain_sums(rn, doms, lambda r: r["right"])
    n = domain_sums(rt, doms, lambda r: 1)
    out = {"n": len(rt), "right_tools": kt, "right_none": kn}
    for ratio, nm in ((1.0, "mult"), (PRICE_RATIO, "mult5")):
        ct = domain_sums(rt, doms, lambda r: tok(r, ratio))
        cn = domain_sums(rn, doms, lambda r: tok(r, ratio))
        out[nm] = multiplier_boot(ct, st, cn, sn, seed=SEED, b=B_BOOT)
    out["mult_processed"] = multiplier_boot(domain_sums(rt, doms, processed), st,
                                            domain_sums(rn, doms, processed), sn,
                                            seed=SEED, b=B_BOOT)
    tt = domain_sums(rt, doms, lambda r: tok(r))
    tn = domain_sums(rn, doms, lambda r: tok(r))
    out["token_ratio"] = ratio_boot(tt, tn, dr)
    out["extra_tokens"] = diff_boot(tt, tn, n, dr)
    out["gain_pp"] = diff_boot(100 * st, 100 * sn, n, dr)
    out["gain_per_1k"] = gain_boot(st, sn, tt, tn, dr)
    if rt[0]["usd"] is not None:
        ut = domain_sums(rt, doms, lambda r: r["usd"])
        un = domain_sums(rn, doms, lambda r: r["usd"])
        out["mult_usd"] = multiplier_boot(ut, st, un, sn, seed=SEED, b=B_BOOT)
        out["usd_ratio"] = ratio_boot(ut, un, dr)
    ot = domain_sums(rt, doms, lambda r: r["out"])
    on = domain_sums(rn, doms, lambda r: r["out"])
    out["output_ratio"] = ratio_boot(ot, on, dr)
    return out


def analyse(recs: list[dict]) -> dict:
    doms = sorted({r["domain"] for r in recs})
    if len(doms) != K_DOMAINS:
        raise Halt(f"{len(doms)} domains, expected {K_DOMAINS}")
    dr = draws(len(doms))
    by = defaultdict(list)
    for r in recs:
        by[(r["corpus"], r["model"], r["task"], r["arm"])].append(r)
    cells, contrasts = [], []
    for (corpus, model, task, arm), rs in sorted(by.items(), key=lambda kv: order_key(kv[0])):
        cells.append({"corpus": corpus, "model": model, "task": task, "arm": arm,
                      **cell_stats(rs, doms, dr)})
        if arm != "none":
            c = contrast(rs, by[(corpus, model, task, "none")], doms, dr)
            contrasts.append({"corpus": corpus, "model": model, "task": task, "arm": arm, **c})
    return {"cells": cells, "contrasts": contrasts, "domains": doms}


def order_key(k):
    corpus, model, task, arm = k
    models = OPEN_MODELS + CLAUDE_MODELS
    return (TASKS.index(task), ("matched", "rerun", "claude").index(corpus),
            models.index(model), ("none", "plain", "steered", "tools").index(arm))


# ================================================================== independent recount
def recount(results: Path, recs: list[dict]) -> list[dict]:
    """Two cells recounted from the raw files with plain json, none of the loaders: the
    matched run's Gemma-26B simulate plain arm from trials.jsonl, and Claude Haiku 5.5's
    simulate tool arm from spend.jsonl (the runner's price log, a different file from the
    sidecar the analysis reads)."""
    out = []
    f = results / "matched-run" / "slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_matched-run" / "trials.jsonl"
    inp = outp = turns = n = 0
    for ln in f.open():
        if not ln.strip():
            continue
        d = json.loads(ln)["result"]
        if d["task"] == "simulate" and d["prompt_variant"] in (11, 12, 13):
            n += 1
            inp += d["tokens"]["prompt"]
            outp += d["tokens"]["completion"]
            turns += d["tokens"]["turns"]
    mine = [r for r in recs if (r["corpus"], r["model"], r["task"], r["arm"])
            == ("matched", "Gemma-26B", "simulate", "plain")]
    out.append({"cell": "matched run, Gemma-26B, simulate, tools plain", "source": str(f.name),
                "raw": [n, inp, outp, turns],
                "analysis": [len(mine), sum(r["inp"] for r in mine), sum(r["out"] for r in mine),
                             sum(r["turns"] for r in mine)]})
    f = results / "frontier55" / "claude-haiku-5-5_tools" / "spend.jsonl"
    inp = outp = req = 0
    usd = 0.0
    keys = set()
    for ln in f.open():
        if not ln.strip():
            continue
        d = json.loads(ln)
        if d.get("what") == "live_turn" and d["key"][1] == "simulate":
            u = d["usage"]
            inp += u["input_tokens"] + (u.get("cache_creation_input_tokens") or 0) \
                + (u.get("cache_read_input_tokens") or 0)
            outp += u["output_tokens"]
            req += 1
            usd += d["usd"]
            keys.add(tuple(d["key"]))
    mine = [r for r in recs if (r["corpus"], r["model"], r["task"], r["arm"])
            == ("claude", "Claude Haiku 5.5", "simulate", "tools")]
    out.append({"cell": "Claude run, Haiku 5.5, simulate, tools", "source": str(f.name),
                "raw": [len(keys), inp, outp, req, round(usd, 6)],
                "analysis": [len(mine), sum(r["inp"] for r in mine), sum(r["out"] for r in mine),
                             sum(r["turns"] for r in mine), round(sum(r["usd"] for r in mine), 6)]})
    totals = {}
    for m, tag in (("claude-haiku-5-5", "Claude Haiku 5.5"), ("claude-sonnet-5-5", "Claude Sonnet 5.5")):
        spent = json.loads((results / "frontier55" / f"spend_{m}.json").read_text())["total_usd"]
        totals[tag] = {"spend_file": spent,
                       "analysis": sum(r["usd"] for r in recs if r["model"] == tag)}
    out.append({"cell": "Claude run, dollars per model", "totals": totals})
    return out


# ================================================================== markdown
def f0(x):
    return "–" if x is None else f"{x:,.0f}"


def ci(b, fmt="{:,.0f}"):
    if b is None:
        return "–"
    return f"{fmt.format(b['est'])} [{fmt.format(b['lo'])}, {fmt.format(b['hi'])}]"


def mult(b):
    if b is None:
        return "– (no right answer)"
    z = b.get("draws_with_zero_successes") or 0
    return f"{b['est']:.2f} [{b['lo']:.2f}, {b['hi']:.2f}]" + (f" ({z} draws dropped)" if z else "")


def finite(x):
    """JSON has no infinity or NaN: an infinite budget or break-even is written as the
    string "none", a NaN as null."""
    if isinstance(x, float):
        return "none" if math.isinf(x) else (None if math.isnan(x) else x)
    if isinstance(x, dict):
        return {k: finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [finite(v) for v in x]
    if isinstance(x, np.floating):
        return finite(float(x))
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def md_table(h, rows):
    from tools.reanalysis.gen_common import md_table as T
    return T(h, rows)


def render(res: dict) -> str:
    cells, cons = res["cells"], res["contrasts"]
    L = ["# Token consumption with and without the tools (descriptive, post hoc)", "",
         "*Generated by `tools/reanalysis/token_consumption.py`; do not edit by hand. No "
         "registration covers this analysis. Three corpora, never pooled: the matched run "
         "(solve, simulate), the October rerun (the three validation tasks), the Claude run "
         "(five tasks). Intervals: 95% domain-cluster bootstrap, 20 domains, 10,000 draws, "
         "seed 20261002. Token counts of different model families are different units; "
         "compare models only through within-model ratios.*", "",
         f"Frozen package hashes checked: " + ", ".join(f"{k} `{v[:12]}...`" for k, v in res["hashes"].items()), ""]
    L += ["## 1. Tokens per trial", "",
          "Input and output are summed over the requests of a trial. Mean [95% interval] and "
          "median. Turns = requests per trial.", ""]
    rows = []
    for c in cells:
        rows.append([CORPUS_WORDS[c["corpus"]], c["model"], c["task"], ARM_WORDS[c["arm"]], c["n"],
                     f"{c['rate']:.1f}", ci(c["inp"]), f0(c["inp_median"]), ci(c["out"]),
                     f0(c["out_median"]), ci(c["total"]), f0(c["total_median"]),
                     f"{100 * c['inp']['est'] / c['total']['est']:.0f}",
                     ci(c["turns"], "{:.2f}")])
    L += [md_table(["corpus", "model", "task", "arm", "n", "right %", "input, mean",
                    "input, median", "output, mean", "output, median", "total, mean",
                    "total, median", "input share %", "turns"], rows), ""]
    L += ["## 2. Cost per right answer and the tools-over-no-tools multiplier", "",
          "Cost per right answer = tokens of the cell / right answers. Raw = input + output; "
          f"price-weighted = input + {PRICE_RATIO:g} x output (a 5:1 output:input price, the "
          "ratio of both Claude list prices). Multiplier = tools arm / no-tools arm, same "
          "trials (below 1: the tool arm is cheaper per right answer). `gen_common."
          "multiplier_boot`, the same draws for both arms.", ""]
    cmap = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in cells}
    rows = []
    for x in cons:
        t, n = cmap[(x["corpus"], x["model"], x["task"], x["arm"])], cmap[(x["corpus"], x["model"], x["task"], "none")]
        rows.append([CORPUS_WORDS[x["corpus"]], x["model"], x["task"], ARM_WORDS[x["arm"]],
                     f"{n['rate']:.1f} → {t['rate']:.1f}", ci(n["cpr"]), ci(t["cpr"]),
                     mult(x["mult"]), mult(x["mult5"]), ci(x["token_ratio"], "{:.2f}")])
    L += [md_table(["corpus", "model", "task", "tool arm", "right %, none → tools",
                    "tokens per right, no tools", "tokens per right, tools",
                    "multiplier, raw", "multiplier, 5:1", "tokens per trial, tools / none"], rows), ""]
    L += ["## 3. Claude run in dollars (registered prices)", "",
          "Haiku 5.5 $0.10 / $0.50 per million input / output tokens ($0.50 / $2.50 for a "
          "request whose prompt is over 100,000 tokens); Sonnet 5.5 $2.00 / $10.00. The "
          "no-tools arm at half price (Batch API), the tool arm at list price, no caching.", ""]
    rows = []
    for x in cons:
        if x["corpus"] != "claude":
            continue
        t, n = cmap[("claude", x["model"], x["task"], "tools")], cmap[("claude", x["model"], x["task"], "none")]
        rows.append([x["model"], x["task"], ci(n["usd"], "{:.4f}"), ci(t["usd"], "{:.4f}"),
                     ci(n["usd_per_right"], "{:.4f}"), ci(t["usd_per_right"], "{:.4f}"),
                     mult(x["mult_usd"]), f"{n['usd_total']:.2f} / {t['usd_total']:.2f}"])
    L += [md_table(["model", "task", "$ per trial, no tools", "$ per trial, tools",
                    "$ per right, no tools", "$ per right, tools", "multiplier in dollars",
                    "$ spent, no tools / tools"], rows), ""]
    L += ["## 4. Where the input of a tool trial goes", "",
          "Share of the tool arm's input tokens that is (a) the first prompt (system message, "
          "tool list, task), sent again with every request; (b) the model's own earlier "
          "replies (mostly the tool calls, which copy the PDDL), re-read; (c) tool output, "
          "re-read. Claude: exact, from the per-request counts. Open models: (a) from the "
          "first-prompt offset (section 8), (b) and (c) split by characters, an estimate.", ""]
    rows = []
    for c in cells:
        if c["arm"] == "none":
            continue
        rows.append([CORPUS_WORDS[c["corpus"]], c["model"], c["task"], ARM_WORDS[c["arm"]],
                     ci(c["share_first"], "{:.1f}"), ci(c["share_own"], "{:.1f}"),
                     ci(c["share_tool"], "{:.1f}"), "exact" if c["corpus"] == "claude" else "estimate"])
    L += [md_table(["corpus", "model", "task", "arm", "first prompt, re-sent %",
                    "own earlier replies %", "tool output %", "(b)/(c) split"], rows), ""]
    L += ["## 5. Output length, the output cap, the window, and tokens on wrong answers", "",
          "Output tokens per trial (tool arm: summed over requests; Claude also the final "
          "reply alone). At cap: the final reply stopped at the output cap (open tool arms: "
          "not counting a final turn that ran out of window). Window full: the final request "
          "was refused or clipped because the prompt filled the 16,384-token window. Wrong "
          "share: share of the cell's tokens spent on trials that end wrong.", ""]
    rows = []
    for c in cells:
        rows.append([CORPUS_WORDS[c["corpus"]], c["model"], c["task"], ARM_WORDS[c["arm"]],
                     ci(c["out"]), f0(c.get("last_out")), f"{c['at_cap']} / {c['n']}",
                     f"{c['window_full']} / {c['n']}",
                     (f"{c['window_full_token_share']:.1f}" if c["window_full"] else "–"),
                     f"{c['wrong_token_share']:.1f}", c["no_call"] if c["arm"] != "none" else "–"])
    L += [md_table(["corpus", "model", "task", "arm", "output per trial", "final reply (Claude)",
                    "at cap", "window full", "window-full share of tokens %",
                    "tokens on wrong trials %", "trials with no tool call"], rows), ""]
    L += ["## 6. What an extra token buys", "",
          "Gain = right answers, tools minus no tools, in points; extra tokens = total tokens "
          "per trial, tools minus no tools; gain per 1,000 extra tokens per trial = the first "
          "over the second, x 1,000. Paired on the same trials. Different tokenizers: read "
          "across models only as an ordering.", ""]
    rows = []
    for x in cons:
        n = cmap[(x["corpus"], x["model"], x["task"], "none")]
        rows.append([CORPUS_WORDS[x["corpus"]], x["model"], x["task"], ARM_WORDS[x["arm"]],
                     f"{n['rate']:.1f}", ci(x["gain_pp"], "{:+.1f}"), ci(x["extra_tokens"]),
                     ci(x["gain_per_1k"], "{:+.2f}")])
    L += [md_table(["corpus", "model", "task", "tool arm", "unaided right %", "gain, points",
                    "extra tokens per trial", "points per 1,000 extra tokens"], rows), ""]
    L += ["## 7. Window-full trials of the open tool arms", "",
          "Trials whose final request was refused (no room) or clipped. A refused request is "
          "stored as 16,384 input tokens (vLLM's lower bound for the 1-token probe), although "
          "the server generated nothing and its real prompt was longer. For the two-request "
          "trials whose second request was refused: summed input minus the first prompt, "
          "median [min, max] (16,384 when the first-prompt offset is right). Last columns: "
          "total tokens per trial and the raw multiplier with each refused request taken out.", ""]
    ccmap = {(x["corpus"], x["model"], x["task"], x["arm"]): x for x in cons}
    rows = []
    for c in cells:
        if c["corpus"] == "claude" or c["arm"] == "none" or not c["window_full"]:
            continue
        rp = c["refused_prompt_2req"]
        x = ccmap[(c["corpus"], c["model"], c["task"], c["arm"])]
        rows.append([CORPUS_WORDS[c["corpus"]], c["model"], c["task"], ARM_WORDS[c["arm"]],
                     f"{c['window_full']} / {c['n']}", c["refused_requests"], c["window_full_right"],
                     f0(c["window_full_tokens_mean"]), f"{c['window_full_token_share']:.1f}",
                     "–" if rp is None else f"{rp[0]:,.0f} [{rp[1]:,.0f}, {rp[2]:,.0f}] (n={rp[3]})",
                     f"{c['total']['est']:,.0f} → {c['total_processed']['est']:,.0f}",
                     f"{mult(x['mult'])} → {mult(x['mult_processed'])}"])
    L += [md_table(["corpus", "model", "task", "arm", "window full", "of them refused",
                    "of them right", "tokens per such trial", "share of the cell's tokens %",
                    "refused request's prompt", "tokens per trial, stored → without refused",
                    "multiplier, raw → without refused"], rows), ""]
    fp = res["first_prompt"]
    L += ["## 8. Checks", "",
          "**First-prompt offset (open models).** On every tool trial that made one request, "
          "its input minus the no-tools input of the same trial. Within each cell the offset "
          "is one value (the script halts otherwise):", ""]
    L += [md_table(["model", "task", "arm", "offset (tokens)", "source"],
                   [[m, t, a, v["offset"], v["source"]] for (m, t, a), v in sorted(
                       fp["offsets"].items(), key=lambda kv: (OPEN_MODELS.index(kv[0][0]), TASKS.index(kv[0][1]), kv[0][2]))]), ""]
    L += ["Measured offsets of each model span " + "; ".join(
        f"{m}: {s[0]} to {s[1]}" for m, s in fp["spread"].items() if s) +
        " tokens, so a borrowed offset is off by about that span per request (under 1% of a "
        "tool trial's input).", ""]
    L += ["Cells measured both ways (one-request value; two-request refused values with "
          "counts): " + "; ".join(f"{k}: {v[0]} vs {v[1]}" for k, v in fp["both_sources"].items())
          + ".", ""]
    neg = sum(c.get("negative_added", 0) for c in cells)
    L += [f"Tool trials with a negative added input under the offset: {neg}.", ""]
    L += ["**Independent recount** (plain json over the raw files, none of the loaders):", ""]
    for x in res["recount"]:
        if "totals" in x:
            L.append("- " + x["cell"] + ": " + "; ".join(
                f"{k}: spend file {v['spend_file']:.4f}, analysis {v['analysis']:.4f}"
                for k, v in x["totals"].items()))
        else:
            L.append(f"- {x['cell']} ({x['source']}): raw {x['raw']}, analysis {x['analysis']} "
                     f"({'equal' if x['raw'] == x['analysis'] else 'DIFFERENT'}; trials, input, "
                     f"output, requests{', dollars' if len(x['raw']) > 4 else ''})")
    L.append("")
    return "\n".join(L) + "\n"


# ================================================================== figures
def figures(res: dict, out: Path) -> None:
    """Four single-column figures (3.4 in wide), each making one point. Colours and fonts
    of `rq1_figures`: grey no tools, blue tools (plain), orange tools (steered). Open
    models filled markers, Claude hollow markers (different conditions; never ranked)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from tools.reanalysis import rq1_figures as FIG     # style, colours, save
    INK = FIG.INK
    col = {a: FIG.ARMS[a][1] for a in FIG.ARMS}
    cells = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in res["cells"]}
    cons = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in res["contrasts"]}
    W = 3.4

    def corpus_of(model, task):
        if model in CLAUDE_MODELS:
            return "claude"
        return "matched" if task in ("solve", "simulate") else "rerun"

    def tool_arm(model, task):
        return "tools" if model in CLAUDE_MODELS else "plain"

    models = OPEN_MODELS + CLAUDE_MODELS
    short = {"Qwen3.5-9B": "Qwen3.5-9B", "Gemma-26B": "Gemma-26B", "Qwen3.6-35B": "Qwen3.6-35B",
             "Claude Haiku 5.5": "Haiku 5.5", "Claude Sonnet 5.5": "Sonnet 5.5"}
    tlab = {"solve": "solve", "validate_domain": "validate\ndomain",
            "validate_problem": "validate\nproblem", "validate_plan": "validate\nplan",
            "simulate": "simulate"}
    mshape = {"Qwen3.5-9B": "o", "Gemma-26B": "s", "Qwen3.6-35B": "D",
              "Claude Haiku 5.5": "^", "Claude Sonnet 5.5": "v"}

    def model_legend(ax):
        h = [plt.Line2D([], [], color=col["plain"], marker=mshape[m], ls="", ms=4.5,
                        mfc="white" if m in CLAUDE_MODELS else col["plain"], label=short[m])
             for m in models]
        ax.legend(handles=h, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 1.01),
                  fontsize=7, handletextpad=0.2, columnspacing=0.8)

    def by_task(ax, value):
        """One column per task, the five models side by side, with whiskers."""
        for i, task in enumerate(TASKS):
            for j, m in enumerate(models):
                b = value(m, task)
                if b is None:
                    continue
                x = i + (j - 2) * 0.14
                ax.errorbar(x, b["est"], yerr=[[b["est"] - b["lo"]], [b["hi"] - b["est"]]],
                            fmt=mshape[m], ms=4, color=col["plain"],
                            mfc="white" if m in CLAUDE_MODELS else col["plain"], mew=0.9,
                            elinewidth=0.7, capsize=1.2, zorder=3)
        ax.set_xticks(range(len(TASKS)))
        ax.set_xticklabels([tlab[t] for t in TASKS], fontsize=7)
        ax.grid(axis="y", zorder=0)
        ax.set_axisbelow(True)
        for i in range(1, len(TASKS)):
            ax.axvline(i - 0.5, color=FIG.GRID, lw=0.6, zorder=0)

    # ---- 1: tokens per trial, tools arm over no-tools arm
    fig, ax = plt.subplots(figsize=(W, 2.5))
    by_task(ax, lambda m, t: cons[(corpus_of(m, t), m, t, tool_arm(m, t))]["token_ratio"])
    ax.set_ylim(0, 13)
    ax.set_ylabel("tokens per trial,\ntools / no tools (ratio)", fontsize=7.5)
    model_legend(ax)
    FIG.save(fig, out, "tok_ratio_per_trial")

    # ---- 2: share of a tool trial's input that is tool output, re-read
    fig, ax = plt.subplots(figsize=(W, 2.5))
    by_task(ax, lambda m, t: cells[(corpus_of(m, t), m, t, tool_arm(m, t))]["share_tool"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("tool output in the\ntools arm's input (%)", fontsize=7.5)
    model_legend(ax)
    FIG.save(fig, out, "tok_tool_output_share")

    # ---- 3: cost per right answer, tools over no tools, against the unaided rate
    fig, ax = plt.subplots(figsize=(W, 2.7))
    tshape = {"solve": "o", "validate_domain": "s", "validate_problem": "D",
              "validate_plan": "P", "simulate": "X"}
    for task in TASKS:
        for m in models:
            cp = corpus_of(m, task)
            x = cons[(cp, m, task, tool_arm(m, task))]["mult"]
            rate = cells[(cp, m, task, "none")]["rate"]
            if x is None:
                continue
            ax.errorbar(rate, x["est"], yerr=[[x["est"] - x["lo"]], [x["hi"] - x["est"]]],
                        fmt=tshape[task], ms=4.5, color=col["plain"],
                        mfc="white" if m in CLAUDE_MODELS else col["plain"], mew=0.9,
                        elinewidth=0.6, capsize=0, alpha=0.9, zorder=3)
    ax.axhline(1, color=INK, lw=0.8, zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 40)
    ax.set_yticks([0.5, 1, 2, 5, 10, 20])
    ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20"])
    ax.set_xlim(0, 102)
    ax.set_xlabel("right without tools (%)", fontsize=7.5)
    ax.set_ylabel("tokens per right answer,\ntools / no tools (ratio)", fontsize=7.5)
    ax.grid(zorder=0)
    ax.set_axisbelow(True)
    h = [plt.Line2D([], [], color=col["plain"], marker=tshape[t], ls="", ms=4.5,
                    label=tlab[t].replace("\n", " ")) for t in TASKS]
    h += [plt.Line2D([], [], color="#7F8A96", marker="h", ls="", ms=5, label="filled: open models"),
          plt.Line2D([], [], color="#7F8A96", marker="h", mfc="white", ls="", ms=5,
                     label="hollow: Claude")]
    ax.legend(handles=h, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 1.01), fontsize=6.5,
              handletextpad=0.2, columnspacing=0.7)
    FIG.save(fig, out, "tok_cost_per_right_vs_unaided")

    # ---- 4: simulate, where the tokens of an arm go (open models)
    fig, ax = plt.subplots(figsize=(W, 2.6))
    rows = [(m, a) for m in OPEN_MODELS for a in ("none", "plain", "steered")]
    for i, (m, a) in enumerate(rows):
        s = cells[("matched", m, "simulate", a)]["tokens_by_outcome_per_trial"]
        left = 0.0
        for key, face, alpha, hatch in (("right", col[a], 1.0, None),
                                        ("wrong_other", col[a], 0.35, None),
                                        ("wrong_window_full", "white", 1.0, "////")):
            v = s[key] / 1000
            ax.barh(i, v, 0.72, left=left, color=face, alpha=alpha, hatch=hatch,
                    edgecolor=col[a] if hatch else "white", linewidth=0.5 if hatch else 0,
                    zorder=3)
            left += v
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{short[m]}, {ARM_WORDS[a].replace('tools, ', '')}" for m, a in rows],
                       fontsize=7)
    ax.invert_yaxis()
    for y in (2.5, 5.5):
        ax.axhline(y, color=FIG.SPINE, lw=0.6)
    ax.set_xlabel("simulate: thousand tokens per trial", fontsize=7.5)
    ax.grid(axis="x", zorder=0)
    ax.set_axisbelow(True)
    h = [plt.Rectangle((0, 0), 1, 1, color="#7F8A96", label="trials that end right"),
         plt.Rectangle((0, 0), 1, 1, color="#7F8A96", alpha=0.35, label="other wrong trials"),
         plt.Rectangle((0, 0), 1, 1, facecolor="white", hatch="////", edgecolor="#7F8A96",
                       label="window full (all wrong)")]
    ax.legend(handles=h, loc="lower center", ncol=2, bbox_to_anchor=(0.4, 1.01), fontsize=7,
              handletextpad=0.3, columnspacing=0.8)
    FIG.save(fig, out, "tok_simulate_where_tokens_go")


# ================================================================== Part A: coverage at a token budget
# Budget-aware reading, applied AFTER the fact: a trial counts as solved at budget B when
# it is right and its total tokens (summed over its requests) are at most B. No model was
# run under a budget; the curve says how many trials would have finished right within B
# had nothing else changed. Over budget counts as not solved.
BUDGETS = (2_000, 5_000, 10_000, 20_000, 50_000, math.inf)
BUDGETS_PW = (5_000, 10_000, 20_000, 50_000, 100_000, math.inf)     # input + 5 x output
GRID = tuple(int(round(x)) for x in np.logspace(2, 6, 81))           # 100 to 1,000,000


def coverage(totals: list[float], right: list[bool], budget: float) -> float:
    """Share (%) of trials that are right AND used at most `budget` tokens."""
    n = len(totals)
    if n == 0:
        return math.nan
    return 100 * sum(1 for t, ok in zip(totals, right) if ok and t <= budget) / n


def break_even(tot_t: list[float], ok_t: list[bool], tot_n: list[float], ok_n: list[bool],
               w_t=None, w_n=None) -> float:
    """Smallest budget from which the tools arm's coverage is at or above the no-tools
    arm's at every larger budget (both arms over the same trials, so counts compare).
    0.0 when that holds at every budget; inf when it fails at no limit. Optional weights
    (cluster multiplicities of a bootstrap draw) per trial."""
    w_t = [1] * len(tot_t) if w_t is None else w_t
    w_n = [1] * len(tot_n) if w_n is None else w_n
    ev = sorted([(t, w) for t, ok, w in zip(tot_t, ok_t, w_t) if ok]
                + [(t, -w) for t, ok, w in zip(tot_n, ok_n, w_n) if ok])
    pos, d, last_neg, i = [], 0, None, 0
    while i < len(ev):
        x = ev[i][0]
        while i < len(ev) and ev[i][0] == x:
            d += ev[i][1]
            i += 1
        pos.append(x)
        if d < 0:
            last_neg = len(pos) - 1
    if last_neg is None:
        return 0.0
    if last_neg == len(pos) - 1:
        return math.inf
    return float(pos[last_neg + 1])


def break_even_boot(tot_t, ok_t, dom_t, tot_n, ok_n, dom_n, doms, dr) -> dict:
    """`break_even` with its domain-cluster bootstrap (the same draws as every interval
    here). Vectorised: an event per right trial (+ tools, - no tools) weighted by the
    multiplicity of its domain in the draw."""
    est = break_even(tot_t, ok_t, tot_n, ok_n)
    idx = {d: i for i, d in enumerate(doms)}
    ev = sorted([(t, 1, idx[d]) for t, ok, d in zip(tot_t, ok_t, dom_t) if ok]
                + [(t, -1, idx[d]) for t, ok, d in zip(tot_n, ok_n, dom_n) if ok])
    if not ev:
        return {"est": est, "lo": est, "hi": est, "share_none": float(est == math.inf)}
    x = np.array([e[0] for e in ev], float)
    s = np.array([e[1] for e in ev], float)
    dm = np.array([e[2] for e in ev])
    ux = np.unique(x)
    ends = np.searchsorted(x, ux, side="right") - 1          # last event at each position
    k = len(doms)
    vals = np.empty(len(dr))
    for a in range(0, len(dr), 1000):
        chunk = dr[a:a + 1000]
        w = np.stack([np.bincount(row, minlength=k) for row in chunk]).astype(float)
        dsum = np.cumsum(s[None, :] * w[:, dm], axis=1)[:, ends]
        neg = dsum < 0
        anyneg = neg.any(1)
        lastneg = neg.shape[1] - 1 - np.argmax(neg[:, ::-1], axis=1)
        v = np.where(lastneg + 1 < len(ux), ux[np.minimum(lastneg + 1, len(ux) - 1)], np.inf)
        vals[a:a + len(chunk)] = np.where(anyneg, v, 0.0)
    lo, hi = np.quantile(vals, [0.025, 0.975], method="inverted_cdf")
    return {"est": est, "lo": float(lo), "hi": float(hi),
            "share_none": float(np.mean(np.isinf(vals)))}


def coverage_part(recs: list[dict], res: dict) -> dict:
    """Coverage curves, paired differences at budgets and break-even budgets, raw and
    price-weighted, per corpus, model, task and arm (never pooled)."""
    doms = res["domains"]
    dr = draws(len(doms))
    by = defaultdict(list)
    for r in recs:
        by[(r["corpus"], r["model"], r["task"], r["arm"])].append(r)
    curves, pairs = [], []
    for (corpus, model, task, arm), rs in sorted(by.items(), key=lambda kv: order_key(kv[0])):
        rs = sorted(rs, key=lambda r: r["key"])
        for unit, f in (("raw", lambda r: tok(r)), ("5:1", lambda r: tok(r, PRICE_RATIO))):
            tots = [f(r) for r in rs]
            oks = [r["right"] for r in rs]
            curves.append({"corpus": corpus, "model": model, "task": task, "arm": arm,
                           "unit": unit, "n": len(rs),
                           "right_totals": (sorted(t for t, ok in zip(tots, oks) if ok)
                                            if unit == "raw" else None),
                           "grid": {str(b): coverage(tots, oks, b) for b in GRID},
                           "no_limit": coverage(tots, oks, math.inf)})
        if arm == "none":
            continue
        rn = sorted(by[(corpus, model, task, "none")], key=lambda r: r["key"])
        if [r["key"] for r in rn] != [r["key"] for r in rs]:
            raise Halt(f"unpaired trials in {corpus}/{model}/{task}/{arm}")
        n = domain_sums(rs, doms, lambda r: 1)
        for unit, f, budgets in (("raw", lambda r: tok(r), BUDGETS),
                                 ("5:1", lambda r: tok(r, PRICE_RATIO), BUDGETS_PW)):
            at = {}
            for b in budgets:
                st = domain_sums(rs, doms, lambda r: 100 * (r["right"] and f(r) <= b))
                sn = domain_sums(rn, doms, lambda r: 100 * (r["right"] and f(r) <= b))
                at["no limit" if b == math.inf else str(b)] = diff_boot(st, sn, n, dr)
            be = break_even_boot([f(r) for r in rs], [r["right"] for r in rs],
                                 [r["domain"] for r in rs], [f(r) for r in rn],
                                 [r["right"] for r in rn], [r["domain"] for r in rn], doms, dr)
            pairs.append({"corpus": corpus, "model": model, "task": task, "arm": arm,
                          "unit": unit, "diff_at_budget": at, "break_even": be})
    return {"curves": curves, "pairs": pairs}


def check_no_limit(cov: dict, filed: Path) -> dict:
    """Coverage at no limit equals the filed right counts of the 38 matched-run and Claude
    cells, and the paired difference at no limit equals the filed contrast (estimate and
    interval, which come from the same draw)."""
    from tools.reanalysis.gen_common import model_name
    mr = json.loads((filed / "matched_run.json").read_text())
    fr = json.loads((filed / "frontier55.json").read_text())
    arm_rec = {"N": "none", "P": "plain", "S": "steered"}
    want = {("matched", model_name(r["model"]), r["task"], arm_rec[r["cell"]]):
            (r["registered"]["right"], r["registered"]["n"]) for r in mr["rates"] if r["this_run"]}
    want.update({("claude", CLAUDE_TAG[r["model"]], r["task"],
                  "none" if r["arm"] == "no-tools" else "tools"): (r["right"], r["n"])
                 for r in fr["rates"]})
    got = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in cov["curves"] if c["unit"] == "raw"}
    bad = [k for k, (k_right, n) in want.items()
           if abs(got[k]["no_limit"] - 100 * k_right / n) > 1e-9 or got[k]["n"] != n]
    cw = {("matched", model_name(c["model"]), c["task"], {"M1": "plain", "M2": "steered"}[c["name"]]): c
          for c in mr["contrasts"] if c["grade"] == "registered" and c["name"] in ("M1", "M2")}
    cw.update({("claude", CLAUDE_TAG[c["model"]], c["task"], "tools"): c for c in fr["contrasts"]})
    pg = {(p["corpus"], p["model"], p["task"], p["arm"]): p["diff_at_budget"]["no limit"]
          for p in cov["pairs"] if p["unit"] == "raw"}
    bad_c = [k for k, c in cw.items()
             if max(abs(pg[k]["est"] - c["est"]), abs(pg[k]["lo"] - c["lo"]), abs(pg[k]["hi"] - c["hi"])) > 1e-9]
    if bad or bad_c:
        raise Halt(f"no-limit coverage differs from the filed outputs: cells {bad}, contrasts {bad_c}")
    return {"cells_checked": len(want), "contrasts_checked": len(cw)}


# ================================================================== Part B: prompt caching
# Cost under a cache price, in the form of Yang et al. (arXiv:2611.22238):
#     cost(c, p) = U + c * C + p * O
# U uncached input, C cached input, O output; c and p are prices relative to an uncached
# input token. Only a trial's own cache hits count (scenario 1): request t >= 2 reuses the
# previous request's whole prompt. c = 1 is what was measured (no discount in any run).
CACHE_PRICES = (1.0, 0.5, 0.25, 0.1, 0.05, 0.0)
# Anthropic prompt-caching prices, from the provider's price documentation as cached on
# 2026-11-03 (given by the session; recheck before quoting): cache read = READ x the
# input price, cache write (five-minute lifetime) = WRITE x the input price; a prefix
# shorter than MIN_CACHEABLE tokens is not cached.
CACHE_PRICE_DATE = "2026-11-03"
CACHE_READ = {"claude-haiku-5-5": 0.10, "claude-sonnet-5-5": 0.05}
CACHE_WRITE = 1.25
MIN_CACHEABLE = 512


def cache_cost(u: float, c_tok: float, o: float, c: float, p: float = 1.0) -> float:
    return u + c * c_tok + p * o


def cached_split_exact(turn_in: list[int]) -> tuple[int, int, int]:
    """(U, C, exceptions) of a trial with per-request input counts: C = sum of P_(t-1)
    over t >= 2, U = the rest. `exceptions` counts requests whose prompt is shorter than
    the previous one (the prefix assumption would fail there)."""
    c_tok = sum(turn_in[:-1])
    exc = sum(1 for a, b in zip(turn_in, turn_in[1:]) if b < a)
    return sum(turn_in) - c_tok, c_tok, exc


def cached_bounds(s: float, n: int, p1: float) -> tuple[float, float]:
    """Bounds on C = S - P_n when only the summed input S, the number of requests n and
    the first prompt P_1 are known and prompts only grow: (n-1) P_1 <= C <= S (n-1) / n."""
    if n <= 1:
        return 0.0, 0.0
    if n == 2:
        return float(p1), float(p1)
    return float((n - 1) * p1), float(s * (n - 1) / n)


def cached_estimate(s: float, n: int, p1: float, calls: list[tuple[int, int]]) -> float:
    """Point estimate of C inside the bounds: the growth of the prompt after request j is
    taken proportional to the characters of the calls made in request j (call i placed in
    request min(i, n-1)), scaled so that the n prompts add up to S."""
    lo, hi = cached_bounds(s, n, p1)
    if n <= 2:
        return lo
    w = [0.0] * n
    for i, (a, r) in enumerate(calls, 1):
        w[min(i, n - 1)] += a + r
    denom = sum((n - j) * w[j] for j in range(1, n))
    added = s - n * p1
    if denom <= 0 or added <= 0:
        return min(max((n - 1) * p1, lo), hi)
    lam = added / denom
    p_n = p1 + lam * sum(w[1:n])
    return min(max(s - p_n, lo), hi)


def attach_cache_split(recs: list[dict]) -> Counter:
    """U, C (low, estimate, high) on every trial, with and without a refused final request.
    A refused request is stored as WINDOW input tokens that never ran: with it, C = S -
    16,384 exactly (its own prompt is the stored 16,384); without it, the request is
    dropped (S' = S - 16,384, n' = n - 1) and C is bounded as for any trial."""
    cases = Counter()
    for r in recs:
        s, n = r["inp"], r["turns"]
        if r["arm"] == "none" or n <= 1 or r.get("unsplit"):
            for v in ("", "_nr"):
                r["C_lo" + v] = r["C_est" + v] = r["C_hi" + v] = 0.0
            r["n_C_exc"] = 0
            if r["arm"] != "none":
                cases["Claude, one request (C = 0)" if r["corpus"] == "claude"
                      else "open, one request (C = 0)"] += 1
            continue
        if r["corpus"] == "claude":
            _u, c_tok, exc = cached_split_exact(r["turn_in"])
            r["C_lo"] = r["C_est"] = r["C_hi"] = r["C_lo_nr"] = r["C_est_nr"] = r["C_hi_nr"] = float(c_tok)
            r["n_C_exc"] = exc
            cases["Claude, two or more requests (exact)"] += 1
            continue
        p1 = r["first"]
        r["n_C_exc"] = 0
        if r["no_room"]:
            exact = float(s - WINDOW)
            r["C_lo"] = r["C_est"] = r["C_hi"] = exact
            s2, n2 = s - WINDOW, n - 1
            lo, hi = cached_bounds(s2, n2, p1)
            r["C_lo_nr"], r["C_hi_nr"] = lo, hi
            r["C_est_nr"] = cached_estimate(s2, n2, p1, r["calls"])
            cases["open, refused final request (C exact with it; " +
                  ("exact" if n2 <= 2 else "bounded") + " without it)"] += 1
            continue
        lo, hi = cached_bounds(s, n, p1)
        r["C_lo"], r["C_hi"] = lo, hi
        r["C_est"] = cached_estimate(s, n, p1, r["calls"])
        r["C_lo_nr"], r["C_est_nr"], r["C_hi_nr"] = r["C_lo"], r["C_est"], r["C_hi"]
        cases["open, two requests (C = P_1, exact up to the offset)" if n == 2 else
              "open, three or more requests (bounded)"] += 1
    return cases


def trial_cost(r: dict, c: float, p: float, which: str = "est", refused: bool = True) -> float:
    """cost(c, p) of one trial; `which` picks the low, estimated or high C. With the
    refused request taken out, its 16,384 stored input tokens leave U and C."""
    v = "" if refused else "_nr"
    s = r["inp"] - (0 if refused or not r["no_room"] else WINDOW)
    c_tok = r[f"C_{which}{v}"]
    return cache_cost(s - c_tok, c_tok, r["out"], c, p)


def static_prefix(recs: list[dict], fp: dict) -> list[dict]:
    """Scenario 2's input: the tool arm's extra static prefix (system text and the seven
    tool descriptions, less the no-tools system text) = first-request input of the tool
    arm minus the input of the no-tools arm, same trial. Open models: the offsets measured
    above. Claude: measured on every trial."""
    out = []
    for (m, t, a), v in fp["offsets"].items():
        # one value in every measured cell (the offset check halts otherwise); a borrowed
        # cell takes a value of the same model, within the span reported in section 8
        out.append({"model": m, "task": t, "arm": a, "mean": v["offset"], "min": v["offset"],
                    "max": v["offset"], "n": v["source"], "constant": True})
    none = {(r["model"], r["key"]): r["inp"] for r in recs if r["corpus"] == "claude" and r["arm"] == "none"}
    by = defaultdict(list)
    for r in recs:
        if r["corpus"] == "claude" and r["arm"] == "tools":
            by[(r["model"], r["task"])].append(r["turn_in"][0] - none[(r["model"], r["key"])])
    for (m, t), d in sorted(by.items()):
        c = Counter(d)
        out.append({"model": m, "task": t, "arm": "tools", "mean": float(np.mean(d)),
                    "min": min(d), "max": max(d), "n": f"{len(d)} trials, {len(c)} distinct values",
                    "constant": max(d) - min(d) <= 0.02 * np.mean(d), "mode": c.most_common(1)[0][0]})
    return out


def caching_part(recs: list[dict], res: dict, fp: dict) -> dict:
    doms = res["domains"]
    dr = draws(len(doms))
    from tools.reanalysis.gen_common import multiplier_boot
    cases = attach_cache_split(recs)
    sp = static_prefix(recs, fp)
    kmap = {(x["model"], x["task"], x["arm"]): x for x in sp}
    by = defaultdict(list)
    for r in recs:
        by[(r["corpus"], r["model"], r["task"], r["arm"])].append(r)
    cmap = {(x["corpus"], x["model"], x["task"], x["arm"]): x for x in res["contrasts"]}
    rows, thresholds, mism = [], [], []
    for (corpus, model, task, arm), rt in sorted(by.items(), key=lambda kv: order_key(kv[0])):
        if arm == "none":
            continue
        rn = by[(corpus, model, task, "none")]
        st = domain_sums(rt, doms, lambda r: r["right"])
        sn = domain_sums(rn, doms, lambda r: r["right"])
        kt, kn = int(st.sum()), int(sn.sum())
        ntr = len(rt)
        kst = kmap.get((model, task, arm))
        for p in (1.0, PRICE_RATIO):
            cn_tot = sum(trial_cost(r, 1.0, p) for r in rn)
            for refused in (True, False):
                if not refused and not any(r["no_room"] for r in rt):
                    continue
                for c in CACHE_PRICES:
                    est = {}
                    for which in ("lo", "est", "hi"):
                        tot = sum(trial_cost(r, c, p, which, refused) for r in rt)
                        est[which] = multiplier(tot, kt, cn_tot, kn)
                    ct = domain_sums(rt, doms, lambda r: trial_cost(r, c, p, "est", refused))
                    cn = domain_sums(rn, doms, lambda r: trial_cost(r, 1.0, p))
                    mb = multiplier_boot(ct, st, cn, sn, seed=SEED, b=B_BOOT)
                    row = {"corpus": corpus, "model": model, "task": task, "arm": arm, "p": p,
                           "c": c, "refused_request": "kept" if refused else "taken out",
                           "scenario": "own hits", "mult": mb,
                           # a larger C lowers the cost when c < 1: the high C gives the low multiplier
                           "mult_range": [est["hi"], est["lo"]],
                           "per_trial_tools": sum(trial_cost(r, c, p, "est", refused) for r in rt) / ntr,
                           "per_trial_none": cn_tot / ntr,
                           "per_right_tools": cost_per_right(sum(trial_cost(r, c, p, "est", refused) for r in rt), kt),
                           "per_right_none": cost_per_right(cn_tot, kn)}
                    rows.append(row)
                    if c == 1.0 and refused:
                        old = cmap[(corpus, model, task, arm)]["mult" if p == 1.0 else "mult5"]
                        if old is None or mb is None or any(abs(old[k] - mb[k]) > 1e-9 for k in ("est", "lo", "hi")):
                            mism.append((corpus, model, task, arm, p))
                    if refused and kst is not None and kst["constant"]:
                        k = kst["mean"] if corpus != "claude" else kst["mode"]
                        tot2 = sum(trial_cost(r, c, p, "est", refused) - (1 - c) * (k if r["turns"] >= 1 and not r.get("unsplit") else 0)
                                   for r in rt)
                        ct2 = domain_sums(rt, doms, lambda r: trial_cost(r, c, p, "est", refused)
                                          - (1 - c) * (k if not r.get("unsplit") else 0))
                        rows.append({**row, "scenario": "own hits + static prefix across trials",
                                     "mult": multiplier_boot(ct2, st, cn, sn, seed=SEED, b=B_BOOT),
                                     "mult_range": None, "per_trial_tools": tot2 / ntr,
                                     "per_right_tools": cost_per_right(tot2, kt)})
                # the cache price at which the multiplier reaches 1 (cost is linear in c)
                if refused:
                    th = {}
                    for which in ("lo", "est", "hi"):
                        a_ = sum(trial_cost(r, 0.0, p, which) for r in rt)
                        b_ = sum(trial_cost(r, 1.0, p, which) for r in rt) - a_
                        target = kt * cn_tot / kn if kn else math.nan
                        th[which] = (None if b_ <= 0 or not kn else (target - a_) / b_)
                    thresholds.append({"corpus": corpus, "model": model, "task": task, "arm": arm,
                                       "p": p, "c_star": th, "kt": kt, "kn": kn})
    if mism:
        raise Halt(f"c = 1 does not reproduce the multipliers of table 2: {mism}")
    exc = sum(r.get("n_C_exc", 0) for r in recs)
    return {"cases": dict(cases), "prefix_exceptions_claude": exc, "static_prefix": sp,
            "rows": rows, "thresholds": thresholds,
            "constants": {"date": CACHE_PRICE_DATE, "read": CACHE_READ, "write": CACHE_WRITE,
                          "min_cacheable": MIN_CACHEABLE}}


def list_usd(m: str, inp: float, out: float, cache_w: float = 0.0, cache_r: float = 0.0) -> float:
    """Dollars of one request at the registered list price (no Batch discount); cache
    writes and reads at CACHE_WRITE and CACHE_READ times the input price. Haiku 5.5's
    higher rate applies to a request whose whole prompt is over its threshold."""
    from tools.frontier55.anthropic_requests import PRICES
    p = PRICES[m]
    rin, rout = p["base"]
    if p["long"] and inp + cache_w + cache_r > p["long_over"]:
        rin, rout = p["long"]
    return (inp * rin + cache_w * rin * CACHE_WRITE + cache_r * rin * CACHE_READ[m]
            + out * rout) / 1e6


def list_trial_usd(m: str, turn_in: list[int], turn_out: list[int]) -> float:
    """A trial at list price, request by request, no caching."""
    return sum(list_usd(m, pt, ot) for pt, ot in zip(turn_in, turn_out))


def cached_trial_usd(m: str, turn_in: list[int], turn_out: list[int]) -> float:
    """A trial at list price with prompt caching: the previous request's prompt is read
    from the cache (if at least MIN_CACHEABLE tokens), the rest of the prompt is new and
    written once."""
    tot, prev = 0.0, 0
    for pt, ot in zip(turn_in, turn_out):
        read = prev if prev >= MIN_CACHEABLE else 0
        tot += list_usd(m, 0, ot, cache_w=pt - read, cache_r=read)
        prev = pt
    return tot


def claude_dollars(recs: list[dict], res: dict) -> list[dict]:
    """Three columns, never merged: (a) billed (no-tools arm at the Batch half price);
    (b) both arms at list price; (c) estimated, list price with prompt caching as the
    provider prices it (every new prompt token written once at CACHE_WRITE, read on each
    later request of the same trial at CACHE_READ; prefixes under MIN_CACHEABLE not
    cached). (c) is estimated; not billed; caching was not enabled in the run."""
    from tools.reanalysis.gen_common import multiplier_boot
    tag = {v: k for k, v in CLAUDE_TAG.items()}
    doms = res["domains"]

    def list_trial(m, r):
        return list_trial_usd(m, r["turn_in"], r["turn_out"])

    def cached_usd(m, r):
        return cached_trial_usd(m, r["turn_in"], r["turn_out"])

    out = []
    by = defaultdict(list)
    for r in recs:
        if r["corpus"] == "claude":
            by[(r["model"], r["task"], r["arm"])].append(r)
    for model in CLAUDE_MODELS:
        m = tag[model]
        for task in TASKS:
            rt, rn = by[(model, task, "tools")], by[(model, task, "none")]
            st = domain_sums(rt, doms, lambda r: r["right"])
            sn = domain_sums(rn, doms, lambda r: r["right"])
            cols = {
                "billed": (lambda r: r["usd"], lambda r: r["usd"]),
                "list price, both arms": (lambda r: list_trial(m, r), lambda r: list_trial(m, r)),
                "estimated with caching (not billed)": (lambda r: cached_usd(m, r),
                                                        lambda r: list_trial(m, r)),
            }
            row = {"model": model, "task": task}
            for name, (ft, fn) in cols.items():
                tt, tn = sum(ft(r) for r in rt), sum(fn(r) for r in rn)
                row[name] = {"tools_per_trial": tt / len(rt), "none_per_trial": tn / len(rn),
                             "tools_per_right": cost_per_right(tt, int(st.sum())),
                             "none_per_right": cost_per_right(tn, int(sn.sum())),
                             "mult": multiplier_boot(domain_sums(rt, doms, ft), st,
                                                     domain_sums(rn, doms, fn), sn,
                                                     seed=SEED, b=B_BOOT),
                             "tools_total": tt, "none_total": tn}
            out.append(row)
    billed = sum(r["billed"]["tools_total"] + r["billed"]["none_total"] for r in out)
    spent = sum(r["usd"] for r in recs if r["corpus"] == "claude")
    tools_list = sum(r["list price, both arms"]["tools_total"] for r in out)
    tools_billed = sum(r["billed"]["tools_total"] for r in out)
    if abs(billed - spent) > 1e-6 or abs(tools_list - tools_billed) > 1e-6:
        raise Halt("the billed or list-price column does not add up to the run's dollars")
    return out


# ================================================================== verdicts across the cache price
def _corpus_of(model, task):
    if model in CLAUDE_MODELS:
        return "claude"
    return "matched" if task in ("solve", "simulate") else "rerun"


def _tool_arm(model):
    return "tools" if model in CLAUDE_MODELS else "plain"


def verdicts(cache: dict, res: dict, dollars: list[dict]) -> list[dict]:
    """For findings 1 to 3 and 6 and the Claude dollar ratios: the value at each cache
    price c (own hits, refused requests kept, estimated C) and whether the finding holds."""
    rows = {(x["corpus"], x["model"], x["task"], x["arm"], x["p"], x["c"]): x for x in cache["rows"]
            if x["scenario"] == "own hits" and x["refused_request"] == "kept"}
    cells = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in res["cells"]}

    def m(model, task, p, c, arm=None):
        x = rows[(_corpus_of(model, task), model, task, arm or _tool_arm(model), p, c)]
        return x["mult"]["est"] if x["mult"] else None

    out = []
    for task in ("solve", "validate_domain"):
        for p in (1.0, PRICE_RATIO):
            vals, ok = [], []
            for c in CACHE_PRICES:
                o = [m(x, task, p, c) for x in OPEN_MODELS]
                cl = [m(x, task, p, c) for x in CLAUDE_MODELS]
                order_open = sorted(OPEN_MODELS, key=lambda x: cells[(_corpus_of(x, task), x, task, "none")]["rate"])
                oo = [m(x, task, p, c) for x in order_open]
                holds = all(a < b for a, b in zip(oo, oo[1:])) and cl[0] < cl[1]
                vals.append(" < ".join(f"{v:.2f}" for v in oo) + "; Claude " + " < ".join(f"{v:.2f}" for v in cl))
                ok.append(holds)
            out.append({"finding": f"1: {task} multiplier rises with the unaided rate "
                                   f"(open models by unaided rate; Haiku, Sonnet), {'raw' if p == 1 else '5:1'}",
                        "values": vals, "holds": ok})
    # finding 2: points gained per 1,000 extra cost units, solve
    for p in (1.0, PRICE_RATIO):
        vals, ok = [], []
        for c in CACHE_PRICES:
            g = {}
            for x in OPEN_MODELS + CLAUDE_MODELS:
                r_ = rows[(_corpus_of(x, "solve"), x, "solve", _tool_arm(x), p, c)]
                cn = cells[(_corpus_of(x, "solve"), x, "solve", "none")]
                ct = cells[(_corpus_of(x, "solve"), x, "solve", _tool_arm(x))]
                extra = r_["per_trial_tools"] - r_["per_trial_none"]
                g[x] = gain_per_1k(ct["right"], cn["right"], extra * ct["n"], 0, ct["n"])
            seq = [g[x] for x in OPEN_MODELS]
            holds = all(a is not None and b is not None and a > b for a, b in zip(seq, seq[1:])) \
                and g[CLAUDE_MODELS[0]] > g[CLAUDE_MODELS[1]]
            vals.append(" > ".join("–" if v is None else f"{v:.2f}" for v in seq) + "; Claude "
                        + " > ".join(f"{g[x]:.2f}" for x in CLAUDE_MODELS))
            ok.append(holds)
        out.append({"finding": f"2: solve, points per 1,000 extra {'tokens' if p == 1 else 'weighted tokens'} "
                               f"falls with the unaided rate (Qwen3.5-9B > Gemma-26B > Qwen3.6-35B; Haiku > Sonnet)",
                    "values": vals, "holds": ok})
    # finding 3 and its raw counterpart: which open tool cells cost no more per right answer
    for p in (1.0, PRICE_RATIO):
        vals = []
        for c in CACHE_PRICES:
            below = [f"{x['model'].split('-')[0]} {x['task'].replace('validate_', 'v.')} {x['arm'][0]}"
                     for k, x in rows.items() if k[4] == p and k[5] == c and x["corpus"] != "claude"
                     and x["mult"] and x["mult"]["est"] <= 1]
            vals.append(f"{len(below)} of 30" + (f": {', '.join(sorted(below))}" if below else ""))
        out.append({"finding": f"3: open tool cells (5 tasks x 3 models x 2 arms) whose multiplier is at "
                               f"most 1, {'raw' if p == 1 else '5:1'}", "values": vals, "holds": None})
    for p in (1.0, PRICE_RATIO):
        vals = []
        for c in CACHE_PRICES:
            cl = [x["mult"]["est"] for k, x in rows.items() if k[4] == p and k[5] == c
                  and x["corpus"] == "claude" and x["mult"]]
            vals.append(f"{sum(v <= 1 for v in cl)} of 10 (min {min(cl):.2f})")
        out.append({"finding": f"3 (Claude): tool cells whose multiplier is at most 1, {'raw' if p == 1 else '5:1'}",
                    "values": vals, "holds": None})
    # finding 6: tokens per trial, tools over no tools
    vals, ok = [], []
    for c in CACHE_PRICES:
        o = [x["per_trial_tools"] / x["per_trial_none"] for k, x in rows.items()
             if k[4] == 1.0 and k[5] == c and x["corpus"] != "claude"]
        cl = [x["per_trial_tools"] / x["per_trial_none"] for k, x in rows.items()
              if k[4] == 1.0 and k[5] == c and x["corpus"] == "claude"]
        vals.append(f"open {min(o):.1f} to {max(o):.1f}; Claude {min(cl):.1f} to {max(cl):.1f}")
        ok.append(min(o) > 1 and min(cl) > 1)
    out.append({"finding": "6: a tool trial costs more than an unaided one (ratio per trial, raw)",
                "values": vals, "holds": ok})
    # the Claude dollar ratios, three columns (they do not depend on c)
    for col in ("billed", "list price, both arms", "estimated with caching (not billed)"):
        v = [d[col]["mult"]["est"] for d in dollars]
        out.append({"finding": f"Claude dollars per right answer, tools / no tools, {col}",
                    "values": [f"{min(v):.1f} to {max(v):.1f}"], "holds": [min(v) > 1]})
    return out


# ================================================================== markdown, Parts A and B
def render_ext(res: dict) -> str:
    cov, cache, dol, ver = res["coverage"], res["caching"], res["claude_dollars"], res["verdicts"]
    L = ["## 9. A second metric: coverage at a token budget", "",
         "Coverage at budget B = share of a cell's trials that are right AND used at most B "
         "tokens (input + output, summed over the requests). The budget is applied after the "
         "fact: no model was run under a budget, so the curve says how many trials would have "
         "finished right within B if nothing else changed. Over budget counts as not solved. "
         f"Checked: at no limit it equals the filed right counts of {res['no_limit_check']['cells_checked']} "
         f"cells, and the paired difference equals the {res['no_limit_check']['contrasts_checked']} filed "
         "contrasts (estimate and interval).", "",
         "### 9.1 Paired difference at a budget, tools minus no tools, points", ""]
    for unit, budgets in (("raw", BUDGETS), ("5:1", BUDGETS_PW)):
        names = ["no limit" if b == math.inf else str(b) for b in budgets]
        rows = []
        for p in cov["pairs"]:
            if p["unit"] != unit:
                continue
            rows.append([CORPUS_WORDS[p["corpus"]], p["model"], p["task"], ARM_WORDS[p["arm"]]]
                        + [ci(p["diff_at_budget"][b], "{:+.1f}") for b in names])
        L += [f"Unit: {'tokens' if unit == 'raw' else 'input + 5 x output'}.", "",
              md_table(["corpus", "model", "task", "tool arm"]
                       + [("no limit" if b == "no limit" else f"B = {int(b):,}") for b in names], rows), ""]
    L += ["### 9.2 Break-even budget", "",
          "The smallest budget from which the tools arm's coverage is at or above the "
          "no-tools arm's at every larger budget. 0 = at every budget; none = the tools arm "
          "is behind at no limit. Interval over the domain draws (none = the upper end is "
          "never reached in at least 2.5% of draws); share of draws with none.", ""]
    rows = []
    for p in cov["pairs"]:
        be = p["break_even"]
        f = lambda v: "none" if v == math.inf else f"{v:,.0f}"
        rows.append([CORPUS_WORDS[p["corpus"]], p["model"], p["task"], ARM_WORDS[p["arm"]], p["unit"],
                     f"{f(be['est'])} [{f(be['lo'])}, {f(be['hi'])}]", f"{100 * be['share_none']:.1f}"])
    L += [md_table(["corpus", "model", "task", "tool arm", "unit", "break-even budget",
                    "draws with none %"], rows), ""]
    L += ["### 9.3 Coverage on a grid of budgets (raw tokens)", "",
          "Share right within B, %. The full curve at every observed trial total is in the "
          "JSON (`right_totals`).", ""]
    gsel = [1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]
    rows = []
    for c in cov["curves"]:
        if c["unit"] != "raw":
            continue
        rows.append([CORPUS_WORDS[c["corpus"]], c["model"], c["task"], ARM_WORDS[c["arm"]]]
                    + [f"{coverage_from_sorted(c['right_totals'], c['n'], b):.1f}" for b in gsel]
                    + [f"{c['no_limit']:.1f}"])
    L += [md_table(["corpus", "model", "task", "arm"] + [f"{b:,}" for b in gsel] + ["no limit"], rows), ""]

    L += ["## 10. Tools against no tools under prompt caching", "",
          "cost(c, p) = U + c x C + p x O (Yang et al., arXiv:2611.22238): U uncached input, C "
          "cached input, O output, c and p the prices of a cached and an output token "
          "relative to an uncached input token. No run had a caching discount: every figure "
          "before this section is c = 1. Scenario 1 (own hits): request t >= 2 of a trial "
          "reads the previous request's whole prompt from the cache; a no-tools trial is one "
          "request, C = 0. Everything here is computed, not billed.", "",
          "**How C was obtained.** " + "; ".join(f"{k}: {v}" for k, v in cache["cases"].items())
          + f". Claude requests whose prompt was shorter than the previous one: "
            f"{cache['prefix_exceptions_claude']}. Open models with three or more requests: "
            "(n-1) P_1 <= C <= S (n-1)/n, point value by characters. A refused final request "
            "(stored as 16,384 input tokens that never ran) is kept in the main rows (then C = "
            "S - 16,384 exactly) and taken out in the rows so marked.", "",
          "### 10.1 Multiplier, tokens per right answer, tools / no tools, by cache price", "",
          "Estimate [95% interval] at the estimated C; for the open models the range of the "
          "point estimate from the high to the low C in brackets after it. Scenario 1, refused "
          "requests kept.", ""]
    for p in (1.0, PRICE_RATIO):
        rows = []
        sel = [x for x in cache["rows"] if x["p"] == p and x["scenario"] == "own hits"
               and x["refused_request"] == "kept"]
        keys = []
        for x in sel:
            k = (x["corpus"], x["model"], x["task"], x["arm"])
            if k not in keys:
                keys.append(k)
        for k in keys:
            row = [CORPUS_WORDS[k[0]], k[1], k[2], ARM_WORDS[k[3]]]
            for c in CACHE_PRICES:
                x = next(y for y in sel if (y["corpus"], y["model"], y["task"], y["arm"]) == k and y["c"] == c)
                cell = mult(x["mult"])
                lo, hi = x["mult_range"]
                if k[0] != "claude" and lo is not None and abs(hi - lo) > 0.005:
                    cell += f" ({lo:.2f} to {hi:.2f})"
                row.append(cell)
            rows.append(row)
        L += [f"Unit: {'p = 1 (raw)' if p == 1 else 'p = 5 (output weighted 5:1)'}.", "",
              md_table(["corpus", "model", "task", "tool arm"] + [f"c = {c:g}" for c in CACHE_PRICES], rows), ""]
    L += ["### 10.2 Cost per trial and per right answer, solve and simulate, by cache price", "",
          "Raw (p = 1), estimated C, refused requests kept. Tools arm / no-tools arm.", ""]
    rows = []
    for x in cache["rows"]:
        if x["p"] != 1.0 or x["scenario"] != "own hits" or x["refused_request"] != "kept" \
                or x["task"] not in ("solve", "simulate"):
            continue
        rows.append([CORPUS_WORDS[x["corpus"]], x["model"], x["task"], ARM_WORDS[x["arm"]], f"{x['c']:g}",
                     f"{x['per_trial_tools']:,.0f} / {x['per_trial_none']:,.0f}",
                     f"{f0(x['per_right_tools'])} / {f0(x['per_right_none'])}"])
    L += [md_table(["corpus", "model", "task", "tool arm", "c", "per trial", "per right answer"], rows), ""]
    L += ["### 10.3 The cache price at which a right answer with tools costs no more than an unaided one", "",
          "c* solves multiplier(c) = 1 (the cost is linear in c). Above 1: the tools arm is "
          "already no dearer at c = 1. Below 0: not reached even at c = 0. For the open models "
          "the range from the high C to the low C after the estimate.", ""]
    rows = []
    for t in cache["thresholds"]:
        cs = t["c_star"]
        f = lambda v: "–" if v is None else f"{v:.2f}"
        rng = "" if t["corpus"] == "claude" else f" ({f(cs['hi'])} to {f(cs['lo'])})"
        rows.append([CORPUS_WORDS[t["corpus"]], t["model"], t["task"], ARM_WORDS[t["arm"]],
                     "1" if t["p"] == 1 else "5", f(cs["est"]) + rng])
    L += [md_table(["corpus", "model", "task", "tool arm", "p", "c*"], rows), ""]
    L += ["### 10.4 Refused requests taken out (open models, cells that have one)", "",
          "The same multiplier with each refused final request removed (its 16,384 stored "
          "input tokens leave U and C).", ""]
    rows = []
    for x in cache["rows"]:
        if x["refused_request"] != "taken out" or x["c"] not in (1.0, 0.1, 0.0):
            continue
        rows.append([CORPUS_WORDS[x["corpus"]], x["model"], x["task"], ARM_WORDS[x["arm"]],
                     "1" if x["p"] == 1 else "5", f"{x['c']:g}", mult(x["mult"])])
    L += [md_table(["corpus", "model", "task", "tool arm", "p", "c", "multiplier"], rows), ""]
    L += ["### 10.5 Scenario 2, labelled apart: the static prefix also cached across trials", "",
          "The tool arm's extra static prefix (its system text and the seven tool "
          "descriptions, less the no-tools system text) = first-request input of the tool arm "
          "minus the input of the no-tools arm, same trial. In this scenario it is also read "
          "from the cache on the first request of every trial. This depends on traffic "
          "(requests within the cache lifetime, a minimum cacheable length), not on the trial. "
          "The no-tools arm's own system text, also static, is not credited (its size cannot be "
          "measured from the rows), so this scenario leans slightly toward the tools.", ""]
    rows = []
    for s in cache["static_prefix"]:
        rows.append([s["model"], s["task"], s["arm"], f"{s['mean']:,.1f}", f"{s['min']:,} to {s['max']:,}",
                     s["n"], "yes" if s["constant"] else "no"])
    L += [md_table(["model", "task", "arm", "extra static prefix, mean", "min to max", "measured on",
                    "near-constant"], rows), ""]
    rows = []
    for x in cache["rows"]:
        if x["scenario"] == "own hits" or x["c"] not in (1.0, 0.1, 0.0) or x["task"] not in ("solve", "simulate"):
            continue
        rows.append([CORPUS_WORDS[x["corpus"]], x["model"], x["task"], ARM_WORDS[x["arm"]],
                     "1" if x["p"] == 1 else "5", f"{x['c']:g}", mult(x["mult"])])
    L += ["Multiplier under scenario 2, solve and simulate (all tasks in the JSON):", "",
          md_table(["corpus", "model", "task", "tool arm", "p", "c", "multiplier"], rows), ""]
    k = cache["constants"]
    L += ["### 10.6 The Claude run in dollars: three columns, never merged", "",
          "(a) billed: as spent, the no-tools arm at the Batch half price. (b) list price, both "
          "arms: the like-for-like comparison of the arms (the batch route is how one arm was "
          "sent, not a property of the arm). (c) estimated; not billed; caching was not enabled "
          f"in the run: list price with prompt caching as priced on {k['date']} (cache read "
          f"{k['read']['claude-haiku-5-5']} x input for Haiku 5.5, {k['read']['claude-sonnet-5-5']} x "
          f"for Sonnet 5.5; write {k['write']} x; minimum cacheable prefix {k['min_cacheable']} "
          "tokens); every new prompt token of a tool trial written once and read on each later "
          "request of the trial; the no-tools arm at list price.", ""]
    rows = []
    for d in dol:
        row = [d["model"], d["task"]]
        for col in ("billed", "list price, both arms", "estimated with caching (not billed)"):
            x = d[col]
            row.append(f"{x['tools_per_right']:.4f} / {x['none_per_right']:.4f} = {mult(x['mult'])}")
        rows.append(row)
    L += [md_table(["model", "task", "(a) billed: $ per right, tools / none = ratio",
                    "(b) list price, both arms", "(c) estimated with caching, not billed"], rows), ""]
    L += ["### 10.7 Verdict table: what holds across the cache price", "",
          "Scenario 1, estimated C, refused requests kept. Values at each c; 'holds' where the "
          "finding's statement is true at that c.", ""]
    rows = []
    for v in ver:
        if len(v["values"]) == 1:
            rows.append([v["finding"]] + [v["values"][0]] + [""] * (len(CACHE_PRICES) - 1)
                        + ["holds" if v["holds"][0] else "fails"])
            continue
        cells_ = [val + ("" if v["holds"] is None else (" (holds)" if h else " (fails)"))
                  for val, h in zip(v["values"], v["holds"] or [None] * len(v["values"]))]
        summ = ("–" if v["holds"] is None else
                "holds at every c" if all(v["holds"]) else
                "fails at c = " + ", ".join(f"{c:g}" for c, h in zip(CACHE_PRICES, v["holds"]) if not h))
        rows.append([v["finding"]] + cells_ + [summ])
    L += [md_table(["finding"] + [f"c = {c:g}" for c in CACHE_PRICES] + ["across c"], rows), ""]
    return "\n".join(L) + "\n"


def coverage_from_sorted(right_totals: list[float], n: int, budget: float) -> float:
    """Coverage (%) from the sorted totals of the right trials of a cell of n trials."""
    import bisect
    return 100 * bisect.bisect_right(right_totals, budget) / n


# ================================================================== figures, Parts A and B
def figures_ext(res: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from tools.reanalysis import rq1_figures as FIG
    INK = FIG.INK
    col = {a: FIG.ARMS[a][1] for a in FIG.ARMS}
    ls = {"none": (0, (4, 2)), "plain": "-", "steered": "-", "tools": "-"}
    curves = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in res["coverage"]["curves"]
              if c["unit"] == "raw"}
    models = OPEN_MODELS + CLAUDE_MODELS
    short = {"Qwen3.5-9B": "Qwen3.5-9B", "Gemma-26B": "Gemma-26B", "Qwen3.6-35B": "Qwen3.6-35B",
             "Claude Haiku 5.5": "Haiku 5.5", "Claude Sonnet 5.5": "Sonnet 5.5"}

    def step(ax, c, color, style):
        xs = [100.0] + [x for x in c["right_totals"] for _ in (0, 1)] + [1e6]
        ys, k = [0.0], 0
        for _x in c["right_totals"]:
            ys.append(100 * k / c["n"])
            k += 1
            ys.append(100 * k / c["n"])
        ys.append(100 * k / c["n"])
        ax.plot(xs, ys, color=color, ls=style, lw=1.4)

    for task, xlim in (("solve", (500, 200_000)), ("simulate", (500, 200_000))):
        fig, axes = plt.subplots(2, 3, figsize=(3.4, 3.0), sharex=True, sharey=True)
        flat = axes.ravel()
        for ax, m in zip(flat, models):
            cp = _corpus_of(m, task)
            for a in ("none", "plain", "steered", "tools"):
                if (cp, m, task, a) in curves:
                    step(ax, curves[(cp, m, task, a)], col[a], ls[a])
            ax.set_xscale("log")
            ax.set_xlim(*xlim)
            ax.set_ylim(0, 100)
            ax.set_xticks([1e3, 1e4, 1e5])
            ax.set_xticklabels(["1K", "10K", "100K"], fontsize=6.5)
            ax.tick_params(axis="y", labelsize=6.5)
            ax.grid(zorder=0, lw=0.5)
            lab = short[m] + ("\n(Claude run)" if m in CLAUDE_MODELS else "")
            ax.set_title(lab, fontsize=6.5, pad=2, fontweight="normal",
                         style="italic" if m in CLAUDE_MODELS else "normal")
        leg = flat[5]
        leg.axis("off")
        h = [plt.Line2D([], [], color=col[a], ls=ls[a], lw=1.4, label=lab)
             for a, lab in (("none", "no tools"), ("plain", "tools, plain"), ("steered", "tools, steered"))]
        leg.legend(handles=h, loc="center", fontsize=6.5, frameon=False)
        fig.supxlabel(f"{task}: token budget per trial (input + output)", fontsize=7)
        fig.supylabel("right within the budget (%)", fontsize=7)
        fig.subplots_adjust(wspace=0.08, hspace=0.32)
        FIG.save(fig, out, f"tok_coverage_{task}")

    # cost-accuracy plane, solve and simulate
    cells = {(c["corpus"], c["model"], c["task"], c["arm"]): c for c in res["cells"]}
    mshape = {"Qwen3.5-9B": "o", "Gemma-26B": "s", "Qwen3.6-35B": "D",
              "Claude Haiku 5.5": "^", "Claude Sonnet 5.5": "v"}
    fig, axes = plt.subplots(1, 2, figsize=(3.4, 2.2), sharey=True)
    for ax, task in zip(axes, ("solve", "simulate")):
        for m in models:
            cp = _corpus_of(m, task)
            arms = [a for a in ("none", "plain", "steered", "tools") if (cp, m, task, a) in cells]
            xs = [cells[(cp, m, task, a)]["total"]["est"] for a in arms]
            ys = [cells[(cp, m, task, a)]["rate"] for a in arms]
            ax.plot(xs, ys, color="#9AA3AE", lw=0.7, ls=":" if m in CLAUDE_MODELS else "-", zorder=2)
            for a, x, y in zip(arms, xs, ys):
                ax.plot(x, y, marker=mshape[m], ms=4, color=col[a],
                        mfc="white" if m in CLAUDE_MODELS else col[a], mew=0.9, ls="", zorder=3)
        ax.set_xscale("log")
        ax.set_xlim(1500, 100_000)
        ax.set_xticks([2e3, 1e4, 5e4])
        ax.set_xticklabels(["2K", "10K", "50K"], fontsize=6.5)
        ax.set_ylim(0, 100)
        ax.tick_params(axis="y", labelsize=6.5)
        ax.grid(zorder=0, lw=0.5)
        ax.set_xlabel(f"{task}: tokens per trial", fontsize=7)
    axes[0].set_ylabel("right (%)", fontsize=7)
    h = [plt.Line2D([], [], color="#7F8A96", marker=mshape[m], ls="", ms=4,
                    mfc="white" if m in CLAUDE_MODELS else "#7F8A96", label=short[m]) for m in models]
    h += [plt.Line2D([], [], color=col[a], marker="s", ls="", ms=4, label=lab)
          for a, lab in (("none", "no tools"), ("plain", "tools, plain"), ("steered", "tools, steered"))]
    axes[0].legend(handles=h, loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=4, fontsize=5.8,
                   handletextpad=0.2, columnspacing=0.6)
    fig.subplots_adjust(wspace=0.08)
    FIG.save(fig, out, "tok_cost_accuracy")

    # solve multiplier against the cache price
    rows = [x for x in res["caching"]["rows"] if x["task"] == "solve" and x["scenario"] == "own hits"
            and x["refused_request"] == "kept"]
    fig, axes = plt.subplots(1, 2, figsize=(3.4, 2.4), sharey=True)
    for ax, p in zip(axes, (1.0, PRICE_RATIO)):
        for m in models:
            arm = _tool_arm(m)
            pts = sorted([x for x in rows if x["model"] == m and x["arm"] == arm and x["p"] == p],
                         key=lambda x: -x["c"])
            cs = [x["c"] for x in pts]
            est = [x["mult"]["est"] for x in pts]
            claude = m in CLAUDE_MODELS
            if not claude:
                ax.fill_between(cs, [x["mult_range"][0] for x in pts], [x["mult_range"][1] for x in pts],
                                color=col["plain"], alpha=0.15, lw=0)
            ax.plot(cs, est, color=col["plain"], ls=(0, (3, 2)) if claude else "-", lw=1.1,
                    marker=mshape[m], ms=3.5, mfc="white" if claude else col["plain"], mew=0.8)
        ax.axhline(1, color=INK, lw=0.8)
        ax.set_xlim(1.03, -0.03)
        ax.set_xticks([1, 0.5, 0.25, 0])
        ax.set_xticklabels(["1", "0.5", "0.25", "0"], fontsize=6.5)
        ax.set_yscale("log")
        ax.set_ylim(0.2, 12)
        ax.set_yticks([0.25, 0.5, 1, 2, 4, 8])
        ax.set_yticklabels(["0.25", "0.5", "1", "2", "4", "8"], fontsize=6.5)
        ax.grid(zorder=0, lw=0.5)
        ax.set_xlabel(f"cache price c ({'output = input' if p == 1 else 'output 5:1'})", fontsize=6.8)
    axes[0].set_ylabel("solve: tokens per right answer,\ntools / no tools", fontsize=7)
    h = [plt.Line2D([], [], color=col["plain"], marker=mshape[m], ms=3.5, lw=1.1,
                    ls=(0, (3, 2)) if m in CLAUDE_MODELS else "-",
                    mfc="white" if m in CLAUDE_MODELS else col["plain"], label=short[m]) for m in models]
    axes[0].legend(handles=h, loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=3, fontsize=6,
                   handletextpad=0.3, columnspacing=0.7)
    fig.subplots_adjust(wspace=0.08)
    FIG.save(fig, out, "tok_cache_price_solve")


# ================================================================== main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=REPO / "results")
    ap.add_argument("--marketplace", type=Path, help="the validator checkout (pddl-copilot at 5e4f9c0)")
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--out", type=Path, default=HERE / "out")
    ap.add_argument("--filed", type=Path, default=HERE / "out",
                    help="where out/matched_run.json and out/frontier55.json are filed")
    ap.add_argument("--figs", type=Path, default=REPO / "development" / "token_consumption")
    ap.add_argument("--cache", type=Path, help="pickle of the graded trial records (speeds re-runs)")
    args = ap.parse_args(argv)
    args.rerun_root = args.canonical_root = args.gt_cache = args.plan_verdicts = None
    args.readout_json = REPO / "development/reference/delivered_rerun_readout.json"
    args.regrade_json = HERE / "out" / "rq1_layout_regrade.json"
    try:
        hashes = check_hashes()
        if args.cache and args.cache.exists():
            with gzip.open(args.cache, "rb") as fh:
                recs = pickle.load(fh)
            print(f"read {len(recs)} graded trials from {args.cache}")
        else:
            if args.marketplace is None:
                raise Halt("--marketplace is required to grade (no --cache given)")
            recs = load_all(args)
            if args.cache:
                with gzip.open(args.cache, "wb") as fh:
                    pickle.dump(recs, fh)
        fp = first_prompt_offsets(recs)
        attach_first_prompts(recs, fp)
        res = analyse(recs)
        res["hashes"] = hashes
        res["first_prompt"] = {"offsets": {"|".join(k): v for k, v in fp["offsets"].items()},
                               "spread": fp["spread"], "both_sources": fp["both_sources"]}
        res["recount"] = recount(args.results, recs)
        fp_md = {"offsets": fp["offsets"], "spread": fp["spread"],
                 "both_sources": fp["both_sources"]}
        md = render({**res, "first_prompt": fp_md})
        res["coverage"] = coverage_part(recs, res)
        res["no_limit_check"] = check_no_limit(res["coverage"], args.filed)
        res["caching"] = caching_part(recs, res, fp)
        res["claude_dollars"] = claude_dollars(recs, res)
        res["verdicts"] = verdicts(res["caching"], res, res["claude_dollars"])
        md += "\n" + render_ext(res)
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    for x in res["recount"]:
        if "raw" in x and x["raw"] != x["analysis"]:
            print(f"HALT: the recount differs for {x['cell']}", file=sys.stderr)
            return 2
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "token_consumption.json").write_text(
        json.dumps(finite(res), indent=1, default=list, allow_nan=False) + "\n")
    (args.out / "token_consumption.md").write_text(md)
    print(f"wrote {args.out}/token_consumption.{{json,md}}")
    # PDFs without a creation date, so a second run writes the same bytes
    os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
    figures(res, args.figs)
    figures_ext(res, args.figs)
    if check_hashes() != hashes:
        print("HALT: a frozen package hash changed during the run", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
