#!/usr/bin/env python3
"""Descriptive secondary analyses of the delivered rerun (prereg §6, §8b item 13).

    python -m tools.delivered_rerun_secondary \
        --rerun-root results/delivered-rerun --canonical-root results/sweep5v2-live \
        --gt-cache results/derived/gt_cache.json --marketplace-path <pddl-copilot @ 5e4f9c0> \
        --readout-json development/reference/delivered_rerun_readout.json \
        --out results/delivered-rerun-secondary \
        [--e4-readings FILE] [--nocall-readings FILE]

Labelled descriptive: not a gate, not frozen, adds no reading to §5. It does not
re-implement loading or grading: rows are loaded and graded by the frozen package
(`tools/delivered_rerun`, package hash 822aace…), and the script refuses to run if
that package changed. Before computing anything new it re-derives E1 (delivered
count per cell) and E4 (category counts per cell) from its own grades and checks
them against the frozen readout JSON, so every table here sits on the readout's
exact grades.

Outputs (in --out):
  secondary.json / secondary.md        the §6 tables, and the hand reads once given
  plan_verdicts.json                   cache of the live validator verdicts (solve)
  e4_needs_reading/<id>.json           one reading packet per E4 NEEDS_READING row
  nocall_sample/<id>.json              reading packets, Gemma no-call sample (§6)
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from pddl_eval.scoring import _normalize_trajectory, _safe_json_loads, strip_leaked_channel_prefix
from tools.delivered_rerun import analysis as A
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import e4 as E4
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.delivered_rerun.stats import cluster_bootstrap
from tools.e2e_regrade import oracle_canon_for, truth_for
from tools.reanalysis.bc_common import domain_track, wilson

# Verbatim from tools/reanalysis/q2_gemma_nocall.py (that script uses sibling
# imports and cannot be imported as a module). Deliberately wide.
TOOLCALL_PATTERNS = {
    "gemma tool-call token (<|tool_call>, <tool_call>)": r"<\|?/?tool_call\|?>|<\|?tool_response",
    "any special-token markup (<|...> or <...|>)": r"<\|[a-z_]+>|<[a-z_]+\|>",
    "call:name{ (gemma native call body)": r"\bcall:\s*[a-z_]+\s*\{",
    "tool name used as a function, validate_plan(": r"\bvalidate_(plan|domain|problem)\s*\(",
    "JSON with a name/arguments/parameters key": r"\"(name|arguments|parameters|tool|function)\"\s*:",
    "```json / ```tool_code fence": r"```\s*(json|tool_code|tool_call|python)",
    "tool_code / tool_call word": r"tool_code|tool_call|function_call|\[TOOL_CALLS\]",
    "print(...) wrapper": r"\bprint\s*\(\s*(default_api|validate_)",
}

FROZEN_SHA = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"
PRICE_RATIOS = (1, 3, 4, 5)          # output : input, as reanalysis_breakdowns_cost.md §5
NOCALL_SAMPLE = 60                   # hand-read sample of Gemma no-call answers
NOCALL_SEED = 20261009
# A verdict stated in prose or on a VERDICT line (q2_gemma_nocall.py patterns,
# extended with the bare VALID/INVALID line); used only to locate the verdict.
VERDICT_ANY = re.compile(
    r"VERDICT\s*:\s*\**\s*(VALID|INVALID)\b|\bplan is (\*\*)?(valid|invalid|not valid)\b|"
    r"\bthe plan (fails|is not executable)\b|^\s*\**(VALID|INVALID)\**\s*$",
    re.IGNORECASE | re.MULTILINE)
CLOSING_CHARS = 400                  # "ends in a verdict": the last match is in the final 400 chars


class Halt(Exception):
    pass


# ------------------------------------------------------------------ helpers
def boot(values, clusters, level=0.95) -> dict:
    """Frozen domain-cluster bootstrap; k is whatever this subset holds."""
    b = cluster_bootstrap(list(values), list(clusters), level, len(set(clusters)))
    return {"est": b.est, "lo": b.lo, "hi": b.hi, "k": b.k, "n": b.n}


def pct(k: int, n: int) -> float | None:
    return 100 * k / n if n else None


def wil(k: int, n: int) -> list[float]:
    lo, hi = wilson(k, n)
    return [100 * lo, 100 * hi]


def f1(x) -> str:
    return "–" if x is None else f"{x:.1f}"


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def row_id(r: S.Row, arm: str) -> str:
    return f"{r.model_tag}|{r.task}|{arm}|{r.domain}|{r.problem}|{r.plan_label}|v{r.variant}"


# ------------------------------------------------------------------ inputs
def load(args) -> tuple[dict, dict, dict]:
    if RUN.package_sha256() != FROZEN_SHA:
        raise Halt("the frozen package tools/delivered_rerun changed (hash is not 822aace…)")
    RUN.check_marketplace(*RUN.marketplace_state(args.marketplace_path))
    RUN.check_domains(args.domains_dir)
    from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash
    gt_cache = json.loads(args.gt_cache.read_text())
    if canonical_hash(gt_cache) != PREREG_PINNED_HASH:
        raise Halt("ground-truth cache does not match the pinned canonical hash")
    design = C.REGISTERED
    C.assert_registered(design)
    cells = RUN.load_all(design, args.rerun_root, args.canonical_root)
    return design, cells, gt_cache


def verdicts_for(need: set, args) -> dict:
    cache = args.out / "plan_verdicts.json"
    table: dict = {}
    if cache.exists():
        for e in json.loads(cache.read_text()):
            table[(e["domain"], e["problem"], tuple(e["plan"]))] = e["valid"]
    missing = need - set(table)
    if missing:
        print(f"validating {len(missing)} solve plans with the live oracle ...", file=sys.stderr)
        table.update(asyncio.run(RUN.live_verdicts(missing, args.domains_dir,
                                                   args.marketplace_path)))
        cache.write_text(json.dumps(
            [{"domain": d, "problem": p, "plan": list(pl), "valid": v}
             for (d, p, pl), v in sorted(table.items())], indent=0) + "\n")
    return {k: table[k] for k in need}


def check_against_readout(readout: dict, rerun_a: dict, grades: dict, gt_cache: dict) -> None:
    """E1 delivered counts and E4 category counts must equal the frozen readout."""
    bad = []
    for e in readout["e1"]:
        rs = [r for r in rerun_a[e["model"]].rows if r.task == e["task"] and r.arm == e["arm"]]
        k = sum(grades[(r.cell, r.trial_key)].ok for r in rs)
        if (k, len(rs)) != (e["delivered_k"], e["n"]):
            bad.append(f"E1 {e['model']}/{e['task']}/{e['arm']}: {k}/{len(rs)} vs "
                       f"{e['delivered_k']}/{e['n']}")
    for e in readout["e4"]:
        g = A.e4_cell(list(rerun_a[e["model"]].rows), grades, gt_cache, e["model"],
                      e["task"], e["arm"])
        if g.categories != e["categories"] or g.n_gap != e["n_gap"]:
            bad.append(f"E4 {e['model']}/{e['task']}/{e['arm']}")
    if bad:
        raise Halt("grades do not reproduce the frozen readout:\n  " + "\n  ".join(bad))


# ------------------------------------------------------------------ §6 tables
def per_wording(rerun_a, rerun_b, rerun_c, ok) -> list[dict]:
    out = []
    groups = [("A", m, list(rerun_a[m].rows)) for m in C.PART_A_MODELS]
    groups += [("C", m, list(rerun_c[m].rows)) for m in C.PART_A_MODELS]
    groups += [("B", C.PART_B_MODEL, list(rerun_b.rows))]
    for part, m, rows in groups:
        by = defaultdict(list)
        for r in rows:
            by[(r.task, r.variant)].append(r)
        for (t, v), rs in sorted(by.items()):
            d = [ok(r) for r in rs]
            inv = [int(r.invoked) for r in rs]
            dom = [r.domain for r in rs]
            out.append({"part": part, "model": m, "task": t, "variant": v, "n": len(rs),
                        "delivered_k": sum(d), "delivered": boot(d, dom),
                        "invocation_k": sum(inv) if part != "C" else None,
                        "invocation": boot(inv, dom) if part != "C" else None})
    return out


def per_domain(rerun_a, rerun_b, rerun_c, ok, track) -> list[dict]:
    out = []
    groups = [("A", m, r.arm, r) for m in C.PART_A_MODELS for r in rerun_a[m].rows]
    groups += [("C", m, "none", r) for m in C.PART_A_MODELS for r in rerun_c[m].rows]
    groups += [("B", C.PART_B_MODEL, r.arm, r) for r in rerun_b.rows]
    by = defaultdict(list)
    for part, m, arm, r in groups:
        by[(part, m, r.task, arm, r.domain)].append(r)
    for (part, m, t, arm, d), rs in sorted(by.items()):
        k = sum(ok(r) for r in rs)
        inv = sum(r.invoked for r in rs)
        out.append({"part": part, "model": m, "task": t, "arm": arm, "domain": d,
                    "track": track[d], "n": len(rs), "delivered_k": k,
                    "delivered_pct": pct(k, len(rs)), "delivered_wilson95": wil(k, len(rs)),
                    "invocation_k": inv if part != "C" else None,
                    "invocation_pct": pct(inv, len(rs)) if part != "C" else None})
    return out


def by_track(rerun_a, rerun_c, ok, track) -> list[dict]:
    out = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            for arm, rows in (("plain", rerun_a[m].rows), ("steered", rerun_a[m].rows),
                              ("none", rerun_c[m].rows)):
                for tr in ("classical", "numeric"):
                    rs = [r for r in rows if r.task == t and track[r.domain] == tr
                          and (arm == "none" or r.arm == arm)]
                    d = [ok(r) for r in rs]
                    dom = [r.domain for r in rs]
                    inv = [int(r.invoked) for r in rs]
                    out.append({"model": m, "task": t, "arm": arm, "track": tr, "n": len(rs),
                                "delivered": boot(d, dom),
                                "invocation": boot(inv, dom) if arm != "none" else None})
    return out


def clipped(rerun_a, rerun_b, rerun_c) -> list[dict]:
    out = []
    groups = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            for arm in C.ARMS:
                groups.append(("A", m, t, arm, [r for r in rerun_a[m].rows
                                                 if r.task == t and r.arm == arm]))
    for arm in C.ARMS:
        groups.append(("B", C.PART_B_MODEL, C.PART_B_TASK, arm,
                       [r for r in rerun_b.rows if r.arm == arm]))
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            groups.append(("C", m, t, "none", [r for r in rerun_c[m].rows if r.task == t]))
    for part, m, t, arm, rs in groups:
        out.append({
            "part": part, "model": m, "task": t, "arm": arm, "n": len(rs),
            "rows_clipped": sum(r.tokens.ctx_clipped_turns > 0 for r in rs),
            "clipped_turns": sum(r.tokens.ctx_clipped_turns for r in rs),
            "rows_last_turn_clipped": sum(r.tokens.ctx_clip_last_turn_max_tokens is not None
                                          for r in rs),
            "rows_clipped_then_length": sum(r.tokens.ctx_clip_last_turn_max_tokens is not None
                                            and r.done_reason == "length" for r in rs),
            "rows_no_room": sum(r.no_room for r in rs),
            "rows_length": sum(r.done_reason == "length" for r in rs)})
    return out


def _cost(rs, r_) -> float:
    return sum(r.tokens.prompt + r_ * r.tokens.completion for r in rs)


def cost_of_pass(rerun_a, rerun_c, ok) -> list[dict]:
    """Cost-of-pass on the delivered score = (input + ratio × output tokens) / successes,
    tokens summed over all turns; multiplier = tool arm / Part C with a domain-cluster
    bootstrap (same domain draw for both arms)."""
    rng_seed = C.SEED
    out = []
    models = list(C.PART_A_MODELS) + ["pooled"]
    for m in models:
        ms = C.PART_A_MODELS if m == "pooled" else (m,)
        for t in C.TASKS:
            arms = {
                "plain": [r for x in ms for r in rerun_a[x].rows if r.task == t and r.arm == "plain"],
                "steered": [r for x in ms for r in rerun_a[x].rows if r.task == t and r.arm == "steered"],
                "none": [r for x in ms for r in rerun_c[x].rows if r.task == t],
            }
            rec = {"model": m, "task": t, "arms": {}, "multiplier": {}}
            for arm, rs in arms.items():
                k = sum(ok(r) for r in rs)
                rec["arms"][arm] = {
                    "n": len(rs), "delivered_k": k,
                    "input_tokens": sum(r.tokens.prompt for r in rs),
                    "output_tokens": sum(r.tokens.completion for r in rs),
                    "cost_of_pass": {str(q): (_cost(rs, q) / k if k else None)
                                     for q in PRICE_RATIOS}}
            # bootstrap per domain: sums of cost and of successes
            doms = sorted({r.domain for r in arms["none"]})
            ix = {d: i for i, d in enumerate(doms)}

            def sums(rs, q):
                c = np.zeros(len(doms))
                s = np.zeros(len(doms))
                for r in rs:
                    c[ix[r.domain]] += r.tokens.prompt + q * r.tokens.completion
                    s[ix[r.domain]] += ok(r)
                return c, s
            rng = np.random.default_rng(rng_seed)
            draws = rng.integers(0, len(doms), size=(C.B_BOOT, len(doms)))
            for arm in ("plain", "steered"):
                rec["multiplier"][arm] = {}
                for q in PRICE_RATIOS:
                    ct, st = sums(arms[arm], q)
                    cn, sn = sums(arms["none"], q)
                    if st.sum() == 0 or sn.sum() == 0:
                        rec["multiplier"][arm][str(q)] = None
                        continue
                    est = (ct.sum() / st.sum()) / (cn.sum() / sn.sum())
                    a, b = st[draws].sum(1), sn[draws].sum(1)
                    valid = (a > 0) & (b > 0)
                    vals = (ct[draws].sum(1)[valid] / a[valid]) / (cn[draws].sum(1)[valid] / b[valid])
                    lo, hi = np.quantile(vals, [0.025, 0.975])
                    rec["multiplier"][arm][str(q)] = {
                        "est": float(est), "lo": float(lo), "hi": float(hi),
                        "draws_with_zero_successes": int((~valid).sum())}
            out.append(rec)
    return out


def verdict_position(text: str) -> dict:
    view = strip_leaked_channel_prefix(text)
    ms = list(VERDICT_ANY.finditer(view))
    if not ms:
        return {"any_verdict_phrase": False, "ends_in_verdict": False}
    last = ms[-1]
    return {"any_verdict_phrase": True,
            "ends_in_verdict": len(view) - last.start() <= CLOSING_CHARS}


def gemma_nocall(rerun_a, rerun_b, rerun_c, grades, ok) -> tuple[list[dict], list[S.Row]]:
    gm = C.PART_B_MODEL
    c_by = {(r.domain, r.problem, r.plan_label, r.variant): r
            for r in rerun_c[gm].rows if r.task == C.PART_B_TASK}
    out = []
    plain_minimal_nocall: list[S.Row] = []
    for style, rows in (("minimal", rerun_a[gm].rows), ("neutral", rerun_b.rows)):
        for arm in C.ARMS:
            rs = [r for r in rows if r.task == C.PART_B_TASK and r.arm == arm]
            nc = [r for r in rs if not r.invoked]
            if style == "minimal" and arm == "plain":
                plain_minimal_nocall = nc
            reasons = Counter(grades[(r.cell, r.trial_key)].reason for r in nc)
            pos = [verdict_position(r.response) for r in nc]
            toolish = [r for r in nc if any(re.search(p, r.response, re.IGNORECASE)
                                            for p in TOOLCALL_PATTERNS.values())]
            mentions_tool = sum(bool(re.search(r"validate_plan|\btools?\b", r.response,
                                               re.IGNORECASE)) for r in nc)
            # pair each no-call answer with the unaided (Part C) answer on the same fixture
            # and wording (steered v14-16 pairs with Part C v11-13 by the §8b item 6 offset)
            pairs = []
            for r in nc:
                v = r.variant - C.STEER_OFFSET if arm == "steered" else r.variant
                c = c_by.get((r.domain, r.problem, r.plan_label, v))
                if c is not None:
                    pairs.append((ok(r), ok(c)))
            ctoks = [r.tokens.completion for r in nc]
            k = sum(ok(r) for r in nc)
            out.append({
                "style": style, "arm": arm, "n": len(rs), "no_call": len(nc),
                "done_reason": dict(Counter(r.done_reason for r in nc)),
                "storage_cut": sum(r.response_truncated_by_storage is True for r in nc),
                "verdict_parsed": sum(reasons[x] for x in ("verdict_stated_ok",
                                                            "verdict_stated_wrong")),
                "verdict_parsed_right": reasons["verdict_stated_ok"],
                "verdict_parsed_wrong": reasons["verdict_stated_wrong"],
                "no_verdict_parsed": reasons["no_verdict_stated"],
                "empty": sum(reasons[x] for x in ("empty_stop", "truncated_empty", "no_room")),
                "delivered_k": k, "delivered_wilson95": wil(k, len(nc)),
                "verdict_phrase_anywhere": sum(p["any_verdict_phrase"] for p in pos),
                "ends_in_verdict_phrase": sum(p["ends_in_verdict"] for p in pos),
                "toolcall_like_text": len(toolish),
                "toolcall_like_ids": [row_id(r, arm) for r in toolish][:50],
                "mentions_tool": mentions_tool,
                "paired_with_part_c": len(pairs),
                "paired_nocall_right": sum(a for a, _ in pairs),
                "paired_part_c_right": sum(b for _, b in pairs),
                "paired_both": sum(a and b for a, b in pairs),
                "paired_nocall_only": sum(a and not b for a, b in pairs),
                "paired_part_c_only": sum(b and not a for a, b in pairs),
                "output_tokens_quartiles": ([float(x) for x in np.percentile(ctoks, [25, 50, 75])]
                                            if ctoks else None)})
    return out, plain_minimal_nocall


# ------------------------------------------------------------------ reading packets
def tool_summary(r: S.Row, limit: int = 4000) -> list[dict]:
    return [{"name": tc.name, "arguments": tc.arguments if len(json.dumps(tc.arguments)) <= limit
             else "(long arguments omitted)", "result": tc.result[:limit]
             + ("…(cut for the packet)" if len(tc.result) > limit else "")}
            for tc in r.tool_calls]


def simulate_aid(answer: str, oracle: list[dict]) -> dict:
    """Reading aid, mechanical: read the answer as one JSON step object per line
    (fenced or not) and compare it with the oracle using the frozen Q1 `_compare`.
    The hand reader confirms the form and the verdict; the aid only saves
    comparing every state by eye."""
    objs = [_safe_json_loads(ln.strip().rstrip(",")) for ln in answer.splitlines()
            if ln.strip().startswith("{")]
    objs = [o for o in objs if isinstance(o, dict) and "step" in o]
    if not objs:
        return {"json_step_lines": 0}
    t = _normalize_trajectory(objs)
    if t is None:
        return {"json_step_lines": len(objs), "normalizable": False}
    d = E4._compare(t, oracle)
    return {"json_step_lines": len(objs), "normalizable": True, "fenced": "```" in answer,
            "compare_with_oracle": d,
            "every_step_matches_oracle": (d["steps_model"] == d["steps_oracle"] and not any(
                d[k] for k in ("action_bad", "bool_bad_steps", "num_wrong", "num_extra",
                               "num_missing", "placeholder_atoms")))}


def e4_packets(rerun_a, grades, gt_cache, outdir: Path) -> list[dict]:
    outdir.mkdir(parents=True, exist_ok=True)
    index = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            for arm in C.ARMS:
                rs = [r for r in rerun_a[m].rows if r.task == t and r.arm == arm
                      and r.success is True and grades[(r.cell, r.trial_key)].ok is False]
                for r in rs:
                    g = grades[(r.cell, r.trial_key)]
                    cat, sub = E4.classify(r, g, gt_cache)
                    if cat != E4.NEEDS_READING:
                        continue
                    rid = row_id(r, arm)
                    reference: dict = {}
                    if t in G.VALIDATE_TASKS:
                        reference["correct_verdict"] = ("VALID" if truth_for(
                            {"task": t, "problem_name": r.problem,
                             "plan_label": r.plan_label}) else "INVALID")
                    elif t == "solve":
                        reference["tool_plan"] = list(E4._last_tool_plan(r))
                    else:
                        reference["oracle_trajectory"] = oracle_canon_for(
                            gt_cache, {"domain_name": r.domain, "problem_name": r.problem})
                    pk = {"id": rid, "model": m, "task": t, "arm": arm, "domain": r.domain,
                          "problem": r.problem, "plan_label": r.plan_label,
                          "variant": r.variant, "mechanical_sub_label": sub,
                          "delivered_reason": g.reason, "done_reason": r.done_reason,
                          "answer_chars": len(r.response), "reference": reference,
                          "tool_calls": tool_summary(r),
                          "final_answer": strip_leaked_channel_prefix(r.response)}
                    if t == "simulate":
                        pk["reading_aid"] = simulate_aid(pk["final_answer"],
                                                         reference["oracle_trajectory"])
                    fn = re.sub(r"[^A-Za-z0-9_.-]+", "_", rid) + ".json"
                    (outdir / fn).write_text(json.dumps(pk, indent=1, default=str) + "\n")
                    index.append({"id": rid, "file": fn, "model": m, "task": t, "arm": arm,
                                  "answer_chars": len(r.response)})
    (outdir / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return index


def nocall_packets(nc: list[S.Row], grades, outdir: Path) -> list[dict]:
    outdir.mkdir(parents=True, exist_ok=True)
    rows = sorted(nc, key=lambda r: r.trial_key)
    sample = random.Random(NOCALL_SEED).sample(rows, min(NOCALL_SAMPLE, len(rows)))
    index = []
    for r in sample:
        rid = row_id(r, "plain")
        g = grades[(r.cell, r.trial_key)]
        pk = {"id": rid, "domain": r.domain, "problem": r.problem, "plan_label": r.plan_label,
              "variant": r.variant, "done_reason": r.done_reason,
              "correct_verdict": "VALID" if truth_for({"task": r.task, "problem_name": r.problem,
                                                       "plan_label": r.plan_label}) else "INVALID",
              "mechanical": {"delivered_reason": g.reason,
                             "parsed_verdict": (None if g.verdict is None else
                                                ("VALID" if g.verdict else "INVALID")),
                             **verdict_position(r.response)},
              "final_answer": strip_leaked_channel_prefix(r.response)}
        fn = re.sub(r"[^A-Za-z0-9_.-]+", "_", rid) + ".json"
        (outdir / fn).write_text(json.dumps(pk, indent=1) + "\n")
        index.append({"id": rid, "file": fn})
    (outdir / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return index


# ------------------------------------------------------------------ markdown
def render(res: dict) -> str:
    L = ["# Delivered rerun: descriptive secondary analyses (prereg §6, §8b item 13)", ""]
    L += [f"*Generated by `tools/delivered_rerun_secondary.py` on the frozen package "
          f"(`{FROZEN_SHA[:7]}…`). Descriptive only: not a gate, no reading added to §5. "
          "The whole rerun is a separate-apparatus replication (parity failed at job level, "
          "readout §3); no figure here is the exact delivered rate of a canonical cell.*", ""]
    L += ["**Consistency check.** The script's grades reproduce the frozen readout exactly: "
          "E1 delivered counts in all 30 cells and E4 category counts in all 30 cells. "
          f"Solve plans validated with the live oracle: {res['n_plans']}.", ""]

    # wording
    L += ["## 1. Per wording", "",
          "Delivered %, by user-prompt wording. v11–13 plain, v14–16 steered (v14 = v11 + "
          "steering sentence, and so on); Part C is the no-tools rerun on v11–13. "
          "Domain-cluster 95% intervals are in `secondary.json`.", ""]
    pw = {(e["part"], e["model"], e["task"], e["variant"]): e for e in res["per_wording"]}
    hdr = ["model", "task"] + [f"v{v}" for v in C.VARIANTS] + ["C v11", "C v12", "C v13"]
    rows = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            rows.append([m, t] + [f1(pw[("A", m, t, v)]["delivered"]["est"]) for v in C.VARIANTS]
                        + [f1(pw[("C", m, t, v)]["delivered"]["est"]) for v in C.PLAIN])
    rows.append([f"{C.PART_B_MODEL} (neutral, Part B)", C.PART_B_TASK]
                + [f1(pw[("B", C.PART_B_MODEL, C.PART_B_TASK, v)]["delivered"]["est"])
                   for v in C.VARIANTS] + ["", "", ""])
    L += [md_table(hdr, rows), "", "Invocation % (any tool call), by wording:", ""]
    rows = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            rows.append([m, t] + [f1(pw[("A", m, t, v)]["invocation"]["est"]) for v in C.VARIANTS])
    rows.append([f"{C.PART_B_MODEL} (neutral, Part B)", C.PART_B_TASK]
                + [f1(pw[("B", C.PART_B_MODEL, C.PART_B_TASK, v)]["invocation"]["est"])
                   for v in C.VARIANTS])
    L += [md_table(["model", "task"] + [f"v{v}" for v in C.VARIANTS], rows), ""]

    # track
    L += ["## 2. Classical against numeric", "",
          "Delivered % [domain-cluster 95% interval]; invocation % for the tool arms. "
          f"Classical domains: {res['n_classical']}, numeric: {res['n_numeric']}.", ""]
    tk = {(e["model"], e["task"], e["arm"], e["track"]): e for e in res["by_track"]}

    def ci(b):
        return f"{b['est']:.1f} [{b['lo']:.1f}, {b['hi']:.1f}]"
    rows = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            r_ = [m, t]
            for tr in ("classical", "numeric"):
                for arm in ("plain", "steered", "none"):
                    r_.append(ci(tk[(m, t, arm, tr)]["delivered"]))
            rows.append(r_)
    L += [md_table(["model", "task", "cl plain", "cl steered", "cl none (C)",
                    "num plain", "num steered", "num none (C)"], rows), "", "Invocation %:", ""]
    rows = []
    for m in C.PART_A_MODELS:
        for t in C.TASKS:
            rows.append([m, t] + [f1(tk[(m, t, arm, tr)]["invocation"]["est"])
                                  for tr in ("classical", "numeric") for arm in ("plain", "steered")])
    L += [md_table(["model", "task", "cl plain", "cl steered", "num plain", "num steered"],
                   rows), ""]

    # domain
    L += ["## 3. Per domain", "",
          "Delivered %, per domain, plain / steered / Part C. n per domain and arm is small "
          "(see `per_domain.csv` for n, Wilson intervals and invocation); read for pattern, "
          "not for single values.", ""]
    pd_ = {(e["part"], e["model"], e["task"], e["arm"], e["domain"]): e for e in res["per_domain"]}
    doms = sorted({e["domain"] for e in res["per_domain"]},
                  key=lambda d: (res["track"][d], d))
    for t in C.TASKS:
        rows = []
        for d in doms:
            r_ = [d, res["track"][d][:3]]
            for m in C.PART_A_MODELS:
                vals = [pd_.get(("A", m, t, "plain", d)), pd_.get(("A", m, t, "steered", d)),
                        pd_.get(("C", m, t, "none", d))]
                r_.append(" / ".join(f1(v["delivered_pct"]) if v else "–" for v in vals))
            rows.append(r_)
        L += [f"**{t}** (plain / steered / none)", "",
              md_table(["domain", "track"] + list(C.PART_A_MODELS), rows), ""]

    # clipped
    L += ["## 4. Clipped allowances per cell", "",
          "Rows whose output allowance was lowered by the overflow retry (§2 delta 2). "
          "*clipped*: rows with ≥ 1 clipped turn; *last clipped*: the final turn ran on a "
          "clipped allowance; *→ length*: of those, the final turn ran out; *no room*: a turn "
          "was refused outright; *length*: any row stopped by the output cap.", ""]
    rows = [[e["part"], e["model"], e["task"], e["arm"], e["n"], e["rows_clipped"],
             e["clipped_turns"], e["rows_last_turn_clipped"], e["rows_clipped_then_length"],
             e["rows_no_room"], e["rows_length"]] for e in res["clipped"]
            if e["rows_clipped"] or e["rows_no_room"] or e["rows_length"]]
    L += [md_table(["part", "model", "task", "arm", "n", "clipped", "clipped turns",
                    "last clipped", "→ length", "no room", "length"], rows), "",
          f"Cells not listed have zero in every column ({sum(1 for e in res['clipped'] if not (e['rows_clipped'] or e['rows_no_room'] or e['rows_length']))} of {len(res['clipped'])}).", ""]

    # cost
    L += ["## 5. Tokens and cost-of-pass on the delivered score", "",
          "Tokens = input + output summed over all turns. Cost-of-pass = (input + r × output) "
          "/ delivered successes, in tokens, at output:input price ratio r. Multiplier = tool "
          "arm ÷ Part C (same run, same grader, same fixtures); below 1 the tool arm is "
          "cheaper per delivered success. Domain-cluster 95% interval.", ""]
    rows = []
    for e in res["cost"]:
        a = e["arms"]
        r_ = [e["model"], e["task"]]
        for arm in ("plain", "steered", "none"):
            n = a[arm]["n"]
            r_.append(f"{(a[arm]['input_tokens'] + a[arm]['output_tokens']) / n:,.0f}")
        for arm in ("plain", "steered"):
            for q in ("1", "5"):
                mm = e["multiplier"][arm][q]
                r_.append("–" if mm is None else f"{mm['est']:.2f} [{mm['lo']:.2f}, {mm['hi']:.2f}]")
        rows.append(r_)
    L += [md_table(["model", "task", "tokens/trial plain", "steered", "none",
                    "× plain 1:1", "× plain 5:1", "× steered 1:1", "× steered 5:1"], rows), "",
          "3:1 and 4:1, and cost-of-pass in tokens per arm, are in `secondary.json`.", ""]

    # gemma no-call
    L += ["## 6. Gemma no-call answers on validate_plan, read in full", "",
          "Trials where Gemma made no tool call. The canonical corpus kept only 500 "
          "characters of these answers, so whether they end in a verdict and whether it is "
          "right could not be seen (`reanalysis_transcripts.md` §2). Here they are stored "
          "in full. *Parsed*: the delivered grader extracts a verdict. *Ends in a verdict "
          f"phrase*: the last verdict phrase starts within the final {CLOSING_CHARS} "
          "characters. *Paired with Part C*: the unaided answer on the same fixture and "
          "wording (steered v14–16 against Part C v11–13).", ""]
    rows = []
    for e in res["gemma_nocall"]:
        rows.append([f"{e['style']}-{e['arm']}", e["n"], e["no_call"],
                     e["done_reason"].get("length", 0), e["storage_cut"],
                     e["toolcall_like_text"], e["mentions_tool"],
                     e["ends_in_verdict_phrase"], e["verdict_parsed"],
                     f"{e['delivered_k']} = {f1(pct(e['delivered_k'], e['no_call']))}% "
                     f"[{e['delivered_wilson95'][0]:.1f}, {e['delivered_wilson95'][1]:.1f}]",
                     f"{e['paired_nocall_right']} / {e['paired_part_c_right']} of "
                     f"{e['paired_with_part_c']}"])
    L += [md_table(["cell", "n", "no call", "hit cap", "storage cut", "tool-call-like text",
                    "names the tool", "ends in verdict phrase", "verdict parsed",
                    "delivered right", "right: no-call / Part C (paired)"], rows), ""]
    if res.get("nocall_readings"):
        L += _render_nocall_readings(res["nocall_readings"])
    else:
        L += [f"Hand read of a seeded random sample of {NOCALL_SAMPLE} minimal-plain no-call "
              "answers: pending.", ""]

    # E4 needs reading
    L += ["## 7. E4 \"needs reading\" rows, read by hand (§8b item 13)", ""]
    L += _render_e4_readings(res)
    return "\n".join(L) + "\n"


def _render_nocall_readings(rd: dict) -> list[str]:
    L = [f"**Hand read** of a seeded random sample of {rd['n']} minimal-plain no-call answers "
         f"(seed {NOCALL_SEED}), {rd['readers']}.", ""]
    L += [md_table(["item", "count"], [[k, v] for k, v in rd["counts"].items()]), ""]
    if rd.get("notes"):
        L += [rd["notes"], ""]
    return L


def _render_e4_readings(res: dict) -> list[str]:
    idx = res["e4_needs_reading_index"]
    by = Counter((e["model"], e["task"], e["arm"]) for e in idx)
    rd = res.get("e4_readings")
    if not rd:
        rows = [[m, t, a, n] for (m, t, a), n in sorted(by.items())]
        return [f"{len(idx)} rows exported for reading; readings pending.", "",
                md_table(["model", "task", "arm", "rows"], rows), ""]
    L = [f"{len(idx)} rows. {rd['method']}", ""]
    cats = list(E4.CATS[:-1]) + ["OTHER"]
    tab = defaultdict(Counter)
    right = Counter()
    for r in rd["rows"]:
        key = (r["model"], r["task"], r["arm"])
        tab[key][r["category"]] += 1
        right[key] += r["human_correct"] == "yes"
    rows = []
    for key in sorted(tab):
        rows.append(list(key) + [sum(tab[key].values())] + [tab[key][c] or "" for c in cats]
                    + [right[key] or ""])
    tot = Counter()
    for c in tab.values():
        tot.update(c)
    rows.append(["**all**", "", "", len(rd["rows"])] + [tot[c] or "" for c in cats]
                + [sum(right.values())])
    L += [md_table(["model", "task", "arm", "rows"] + cats + ["right to a human reader"], rows), ""]
    ag = rd["agreement"]
    how = Counter(r["how"] for r in rd["rows"])
    L += [f"Agreement between the two independent readers on the category: "
          f"{ag['category_agree']} of {ag['n']} ({100 * ag['category_agree'] / ag['n']:.1f}%); "
          f"on \"right to a human reader\": {ag['correct_agree']} of {ag['n']} "
          f"({100 * ag['correct_agree'] / ag['n']:.1f}%). Final labels: "
          + ", ".join(f"{v} {k}" for k, v in how.most_common()) + ".", ""]
    if rd.get("rules"):
        L += [rd["rules"], ""]
    L += ["**Folded into E4** (descriptive; the frozen readout's E4 table is unchanged and "
          "remains the record):", ""]
    folded = []
    readout_e4 = {(e["model"], e["task"], e["arm"]): e for e in res["readout_e4"]}
    for key in sorted(tab):
        e = readout_e4[key]
        c = dict(e["categories"])
        c.pop(E4.NEEDS_READING)
        for k_, v in tab[key].items():
            c[k_] = c.get(k_, 0) + v
        folded.append(list(key) + [e["n_gap"]] + [c.get(x, 0) or "" for x in cats])
    L += [md_table(["model", "task", "arm", "gap"] + cats, folded), ""]
    if rd.get("notes"):
        L += [rd["notes"], ""]
    return L


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rerun-root", type=Path, required=True)
    ap.add_argument("--canonical-root", type=Path, required=True)
    ap.add_argument("--gt-cache", type=Path, required=True)
    ap.add_argument("--domains-dir", type=Path, default=RUN.REPO / "domains")
    ap.add_argument("--marketplace-path", type=Path, required=True)
    ap.add_argument("--readout-json", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--e4-readings", type=Path)
    ap.add_argument("--nocall-readings", type=Path)
    args = ap.parse_args(argv)
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        design, cells, gt_cache = load(args)
        rerun_a, rerun_b, rerun_c = cells["rerun_a"], cells["rerun_b"], cells["rerun_c"]
        rerun_rows = ([r for lc in rerun_a.values() for r in lc.rows] + list(rerun_b.rows)
                      + [r for lc in rerun_c.values() for r in lc.rows])
        need = G.solve_plans_to_validate(rerun_rows)
        verdicts = verdicts_for(need, args)
        grades = {(r.cell, r.trial_key): G.grade(r, gt_cache, verdicts) for r in rerun_rows}
        readout = json.loads(args.readout_json.read_text())
        if readout.get("package_sha256") != FROZEN_SHA:
            raise Halt("--readout-json is not the frozen live readout")
        check_against_readout(readout, rerun_a, grades, gt_cache)

        def ok(r):
            return int(grades[(r.cell, r.trial_key)].ok)
        track = domain_track()
        nocall, plain_nc = gemma_nocall(rerun_a, rerun_b, rerun_c, grades, ok)
        res = {
            "frozen_package_sha256": FROZEN_SHA, "n_plans": len(need), "track": track,
            "n_classical": sum(v == "classical" for v in track.values()),
            "n_numeric": sum(v == "numeric" for v in track.values()),
            "per_wording": per_wording(rerun_a, rerun_b, rerun_c, ok),
            "per_domain": per_domain(rerun_a, rerun_b, rerun_c, ok, track),
            "by_track": by_track(rerun_a, rerun_c, ok, track),
            "clipped": clipped(rerun_a, rerun_b, rerun_c),
            "cost": cost_of_pass(rerun_a, rerun_c, ok),
            "gemma_nocall": nocall,
            "e4_needs_reading_index": e4_packets(rerun_a, grades, gt_cache,
                                                 args.out / "e4_needs_reading"),
            "nocall_sample_index": nocall_packets(plain_nc, grades, args.out / "nocall_sample"),
            "readout_e4": readout["e4"],
        }
        if len(res["e4_needs_reading_index"]) != sum(e["categories"][E4.NEEDS_READING]
                                                     for e in readout["e4"]):
            raise Halt("exported NEEDS_READING rows differ from the readout count")
        if args.e4_readings:
            res["e4_readings"] = json.loads(args.e4_readings.read_text())
            ids = {e["id"] for e in res["e4_needs_reading_index"]}
            got = {r["id"] for r in res["e4_readings"]["rows"]}
            if ids != got:
                raise Halt(f"E4 readings cover {len(got)} ids, {len(ids & got)} of the "
                           f"{len(ids)} exported")
            if any(r["category"] is None for r in res["e4_readings"]["rows"]):
                raise Halt("E4 readings still hold unsettled rows")
        if args.nocall_readings:
            res["nocall_readings"] = json.loads(args.nocall_readings.read_text())
        with (args.out / "per_domain.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(res["per_domain"][0]))
            w.writeheader()
            w.writerows(res["per_domain"])
        (args.out / "secondary.json").write_text(json.dumps(res, indent=1, default=list) + "\n")
        (args.out / "secondary.md").write_text(render(res))
    except (Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}/secondary.{{json,md}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
