#!/usr/bin/env python3
"""Q3 - truncated tool-arm trials on the headline open models, and the solve
delivery gap against plan length.

Corpus: results/sweep5v2-live, cells slurm_vllm_<model>_off_tools_all_minimal
(thinking off, with tools) for Gemma 26B, Qwen3.5 9B, Qwen3.6 35B, joined to
results/derived/e2e_overlay/sweep5v2-live/<cell>.e2e.jsonl on the trial key.
Tasks: solve and validate_plan. Arms: plain = variants 11-13, steered = 14-16.

Fields (checked against pddl_eval/scoring.py, pddl_eval/runner.py,
pddl_eval/vllm_client.py and tools/e2e_regrade.py):
  tool-verified   overlay `tool_verified` (= stored harness `success`: the
                  tool's own result was right; the final text is not read)
  delivered       overlay `e2e_strict`: True / False / "indeterminate".
                  "indeterminate" = the 500-char snapshot is full, so the
                  answer cannot be graded -> reported as a bound <low, high>
  truncated       stored `truncated` (the last chat turn ended with
                  done_reason == "length"); the paper figure's "truncated"
                  band on tool arms is overlay e2e_reason == "truncated_empty"
                  (empty final answer and done_reason != "stop")

Parts
  A  reproduce the pooled "truncated" shares read off failure_taxonomy.pdf
  B  per model x task x arm: share truncated, and of which kind
  C  why the answer is empty: the final turn was never generated
  D  what the stored snapshots show
  E  solve only: tool-verified minus delivered, by plan-length bin
  F  Gemma solve: answers that are the tool's plan with a markup prefix

Usage:  python3 tools/reanalysis/q3_truncated_tool_arms.py [--examples]
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict

from transcripts_common import OVERLAY, RESULTS, clip, load_overlay, load_trials, pct, wilson

from pddl_eval.prompts import STEERED_VARIANTS  # noqa: E402
from pddl_eval.runner import DEFAULT_NUM_CTX, DEFAULT_NUM_PREDICT  # noqa: E402
from pddl_eval.scoring import extract_plan_lines  # noqa: E402
from pddl_eval.vllm_client import _CTX_MAX_RETRIES, _CTX_RETRY_SAFETY  # noqa: E402

CORPUS = "sweep5v2-live"
MODELS = {"Gemma 26B": "gemma4_26b-a4b", "Qwen3.5 9B": "Qwen3_5_9B",
          "Qwen3.6 35B": "qwen3_6_35b"}
TASKS = ("solve", "validate_plan")
ARMS = {"plain": (11, 12, 13), "steered": tuple(sorted(STEERED_VARIANTS))}
VARIANTS = (11, 12, 13, 14, 15, 16)
BINS = ((1, 5), (6, 10), (11, 20), (21, 40), (41, 10_000))
PLANNERS = ("classic_planner", "numeric_planner")
GEMMA_PREFIX = "<|channel>thought\n<channel|>"


def synthetic_prompt_count(task: str) -> int:
    """The prompt-token count the harness records when it gives up on a turn.

    vllm_client.chat(): the server rejects prompt + max_tokens > context and
    reports only a LOWER bound for the prompt ("at least N input tokens", with
    N = context - max_tokens + 1). The client lowers max_tokens by
    N + _CTX_RETRY_SAFETY and retries, _CTX_MAX_RETRIES times; each retry is
    told a bound 129 tokens higher. After the last failure it returns an empty
    answer with done_reason "length" and prompt_eval_count = the last bound.
    """
    cap = DEFAULT_NUM_PREDICT[task]
    return DEFAULT_NUM_CTX - cap + 1 + _CTX_MAX_RETRIES * (_CTX_RETRY_SAFETY + 1)


def fixture(r: dict) -> tuple:
    return (r["domain_name"], r["problem_name"], r.get("plan_label") or "")


def args_chars(r: dict) -> int:
    return sum(len(str(v)) for tc in r["tool_calls"] for v in (tc.get("arguments") or {}).values())


# Cells whose first-turn prompt size may stand in for another cell's. A donor
# is used only if, on every trial key where both cells have an exact value,
# the difference is one and the same constant (checked at run time).
DONORS = {
    "Gemma 26B": [("gemma4_26b-a4b", "on")],
    "Qwen3.5 9B": [("Qwen3_5_9B", "on"), ("qwen3_6_35b", "off"), ("qwen3_6_35b", "on")],
    "Qwen3.6 35B": [("qwen3_6_35b", "on"), ("Qwen3_5_9B", "off"), ("Qwen3_5_9B", "on")],
}
MIN_COMMON = 10


def _one_turn(rows) -> dict:
    return {(r["task"], fixture(r), r["prompt_variant"]): r["tokens"]["prompt"]
            for r in rows if r["tokens"]["turns"] == 1 and r["done_reason"] == "stop"}


def first_turn_prompts(name: str, own_rows) -> tuple[dict, dict, list[str]]:
    """Exact first-turn prompt sizes for one model, from single-turn trials.

    Returns ({(task, fixture, variant): tokens}, {(task, v_from, v_to): offset},
    notes). Sources: the cell itself, then donor cells shifted by a constant
    that is verified on the common keys. Variant offsets (the prompt wording
    differs, the PDDL does not) are used only when constant on every fixture.
    """
    p1 = _one_turn(own_rows)
    notes = [f"own cell: {len(p1)} single-turn trials"]
    for m, think in DONORS[name]:
        path = RESULTS / CORPUS / f"slurm_vllm_{m}_{think}_tools_all_minimal" / "trials.jsonl"
        donor = _one_turn(load_trials(path).values())
        common = set(p1) & set(donor)
        diffs = Counter(p1[k] - donor[k] for k in common)
        if len(common) < MIN_COMMON or len(diffs) != 1:
            notes.append(f"{m} think={think}: not used ({len(common)} common keys, "
                         f"{len(diffs)} distinct differences)")
            continue
        shift = next(iter(diffs))
        added = 0
        for k, t in donor.items():
            if k not in p1:
                p1[k] = t + shift
                added += 1
        notes.append(f"{m} think={think}: +{added} keys, constant shift {shift:+d} "
                     f"verified on {len(common)} common keys")
    seen: dict = defaultdict(Counter)
    for (task, f, v), t in p1.items():
        for v2 in VARIANTS:
            if v2 != v and (task, f, v2) in p1:
                seen[(task, v, v2)][p1[(task, f, v2)] - t] += 1
    offsets = {k: next(iter(c)) for k, c in seen.items() if len(c) == 1}
    return p1, offsets, notes


def known_p1(r: dict, p1: dict, offsets: dict) -> int | None:
    task, f, v = r["task"], fixture(r), r["prompt_variant"]
    if (task, f, v) in p1:
        return p1[(task, f, v)]
    for v2 in VARIANTS:
        if (task, f, v2) in p1 and (task, v2, v) in offsets:
            return p1[(task, f, v2)] + offsets[(task, v2, v)]
    return None


def kind(r: dict) -> str:
    """Mutually exclusive description of one trial flagged `truncated`."""
    empty = not (r["response"] or "").strip()
    if empty and r["tool_calls"]:
        return "empty answer after tool call(s)"
    if empty:
        return "empty answer, no tool call"
    if not r["tool_calls"]:
        return "text answer cut at the output cap, no tool call"
    return "text answer cut after tool call(s)"


KINDS = ("empty answer after tool call(s)", "empty answer, no tool call",
         "text answer cut at the output cap, no tool call",
         "text answer cut after tool call(s)")


def load_cells() -> dict:
    cells = {}
    for name, m in MODELS.items():
        cell = f"slurm_vllm_{m}_off_tools_all_minimal"
        raw = load_trials(RESULTS / CORPUS / cell / "trials.jsonl")
        ov = load_overlay(OVERLAY / CORPUS / f"{cell}.e2e.jsonl")
        assert set(raw) == set(ov), f"{cell}: overlay/raw key mismatch"
        assert all(r["with_tools"] for r in raw.values())
        cells[name] = (raw, ov)
    return cells


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", action="store_true")
    args = ap.parse_args()
    cells = load_cells()
    gt = json.loads((RESULTS / "derived" / "gt_cache.json").read_text())

    # ------------------------------------------------------------------ A
    print("== A. Reproduce the 'truncated' band of failure_taxonomy.pdf "
          "(pooled over the three models, overlay e2e_reason == truncated_empty) ==")
    for task in TASKS:
        for arm, vs in ARMS.items():
            k = n = 0
            for raw, ov in cells.values():
                for key, r in raw.items():
                    if r["task"] == task and r["prompt_variant"] in vs:
                        n += 1
                        k += ov[key]["e2e_reason"] == "truncated_empty"
            print(f"  {task:14s} {arm:8s} {pct(k, n)}")
    print("  (weakness_consolidated.md C5 reads these off the bars as about 37 / 34% and 7 / 8%)")

    # ------------------------------------------------------------------ B
    print("\n== B. Share of trials that end truncated (stored `truncated` flag), "
          "and what kind ==")
    print(f"{'model':12s} {'task':14s} {'arm':8s} {'truncated':>32s}   "
          + " | ".join(KINDS))
    pooled: dict = defaultdict(lambda: [0, 0, Counter()])
    for name, (raw, ov) in cells.items():
        for task in TASKS:
            for arm, vs in ARMS.items():
                rows = [r for r in raw.values() if r["task"] == task
                        and r["prompt_variant"] in vs]
                tr = [r for r in rows if r["truncated"]]
                assert all(r["done_reason"] == "length" for r in tr)
                c = Counter(kind(r) for r in tr)
                print(f"{name:12s} {task:14s} {arm:8s} {pct(len(tr), len(rows)):>32s}   "
                      + " | ".join(f"{c[k]:4d}" for k in KINDS))
                p = pooled[(task, arm)]
                p[0] += len(tr)
                p[1] += len(rows)
                p[2] += c
    for (task, arm), (k, n, c) in pooled.items():
        print(f"{'pooled':12s} {task:14s} {arm:8s} {pct(k, n):>32s}   "
              + " | ".join(f"{c[x]:4d}" for x in KINDS))

    # ------------------------------------------------------------------ C
    print("\n== C. Why is the answer empty? ==")
    print(f"context window {DEFAULT_NUM_CTX}; output cap solve "
          f"{DEFAULT_NUM_PREDICT['solve']}, validate_plan "
          f"{DEFAULT_NUM_PREDICT['validate_plan']}; the harness gives up on a turn after "
          f"{_CTX_MAX_RETRIES} retries and then records a prompt count of "
          f"{synthetic_prompt_count('solve')} (solve) / "
          f"{synthetic_prompt_count('validate_plan')} (validate_plan) with 0 output tokens")
    grand = Counter()
    for name, (raw, ov) in cells.items():
        p1, offsets, notes = first_turn_prompts(name, raw.values())
        print(f"\n  {name}: sources of exact first-turn prompt sizes -> " + "; ".join(notes))
        for task in TASKS:
            rows = [r for r in raw.values() if r["task"] == task]
            empties = [r for r in rows if r["truncated"]
                       and kind(r) == "empty answer after tool call(s)"]
            if not empties:
                continue
            cap = DEFAULT_NUM_PREDICT[task]
            # A turn can only end with done_reason "length" for real if it
            # generated a full allowance: the cap, or the cap lowered by one or
            # two retries. If the whole trial produced fewer output tokens than
            # the smallest such allowance, no turn did, so the "length" must
            # be the harness's give-up response.
            floor = cap - _CTX_MAX_RETRIES * (_CTX_RETRY_SAFETY + 1)
            below_cap = sum(r["tokens"]["completion"] < floor for r in empties)
            two = [r for r in empties if r["tokens"]["turns"] == 2]
            resolved = [(r, known_p1(r, p1, offsets)) for r in two]
            resolved = [(r, a) for r, a in resolved if a is not None]
            last = Counter(r["tokens"]["prompt"] - a for r, a in resolved)
            hit = last[synthetic_prompt_count(task)]
            print(f"\n  {name} / {task}: {len(empties)} empty-after-call truncated trials")
            print(f"    whole trial produced fewer output tokens than the smallest allowance "
                  f"a turn could have run out of ({floor}): {pct(below_cap, len(empties))}")
            print(f"    two-turn trials whose first-turn prompt size is known exactly: "
                  f"{len(resolved)} of {len(two)}")
            if resolved:
                print(f"    their recorded final-turn prompt count: {dict(last)} -> equals the "
                      f"give-up value in {pct(hit, len(resolved))}")
            grand["empties"] += len(empties)
            grand["below_cap"] += below_cap
            grand["resolved"] += len(resolved)
            grand["hit"] += hit
            # output tokens per tool-call argument character: if the final turn
            # produced nothing, the whole trial's output is the call(s) alone.
            ref = [r["tokens"]["completion"] / args_chars(r) for r, _ in resolved
                   if args_chars(r)]
            rest = [r["tokens"]["completion"] / args_chars(r) for r in empties
                    if args_chars(r) and all(r is not x for x, _ in resolved)]
            if len(ref) >= 20 and rest:
                ref.sort()
                lo, hi = ref[int(0.01 * len(ref))], ref[min(len(ref) - 1, int(0.99 * len(ref)))]
                inside = sum(lo <= x <= hi for x in rest)
                print(f"    output tokens per argument character, confirmed trials: 1%-99% "
                      f"range {lo:.3f}-{hi:.3f}; the other {len(rest)} empty trials inside "
                      f"that range: {pct(inside, len(rest))}")
                grand["rest"] += len(rest)
                grand["rest_inside"] += inside
            # how much room was really left: estimate the true final prompt
            calib = []
            for r in rows:
                a = known_p1(r, p1, offsets)
                if (a is None or r["truncated"] or r["tokens"]["turns"] != 2
                        or len(r["response"]) >= 400 or len(r["tool_calls"]) != 1):
                    continue
                res = len(str(r["tool_calls"][0].get("result", "")))
                c2 = len(r["response"]) / 3.0            # short final answer, ~3 chars/token
                c1 = r["tokens"]["completion"] - c2
                extra = r["tokens"]["prompt"] - 2 * a - c1   # tool result + template tokens
                if res > 200:
                    calib.append(extra / res)
            if len(calib) >= 20 and resolved:
                tpc = statistics.median(calib)
                room = sorted(DEFAULT_NUM_CTX - (a + r["tokens"]["completion"]
                              + tpc * len(str(r["tool_calls"][0].get("result", ""))))
                              for r, a in resolved)
                print(f"    ESTIMATE (tool-result tokens = {tpc:.3f} x result chars, calibrated "
                      f"on {len(calib)} complete two-turn trials): context room left when the "
                      f"final turn was refused, median {statistics.median(room):.0f} tokens, "
                      f"range {room[0]:.0f} to {room[-1]:.0f}; at least 1,000 tokens left in "
                      f"{pct(sum(x >= 1000 for x in room), len(room))}")
            seq_t = Counter(tuple(t["name"] for t in r["tool_calls"]) for r in empties)
            done = [r for r in rows if r["tool_calls"] and not r["truncated"]]
            print(f"    tool calls per trial: truncated median "
                  f"{statistics.median(len(r['tool_calls']) for r in empties)}, "
                  f"not truncated median {statistics.median(len(r['tool_calls']) for r in done)}; "
                  f"argument characters sent: {statistics.median(map(args_chars, empties)):.0f} "
                  f"vs {statistics.median(map(args_chars, done)):.0f}")
            print(f"    most common call sequences when truncated: {seq_t.most_common(3)}")
            cut = [r for r in empties if any("_raw_arguments" in (tc.get("arguments") or {})
                                             for tc in r["tool_calls"])]
            grand["cut_call"] += len(cut)
            print(f"    of these, trials where an earlier tool call was itself cut at the "
                  f"output cap (arguments stored as unparsed text): {pct(len(cut), len(empties))}"
                  + (f"; fixtures {Counter(r['domain_name'] + '/' + r['problem_name'] for r in cut).most_common(4)}"
                     if cut else ""))
            if cut and args.examples:
                tail = next(tc for tc in cut[0]["tool_calls"]
                            if "_raw_arguments" in tc["arguments"])["arguments"]["_raw_arguments"]
                print(f"      end of one such cut call ({len(tail)} chars): {tail[-150:]!r}")
            tv = sum(bool(r["success"]) for r in empties)
            print(f"    tool-verified (the tool had the right result): {pct(tv, len(empties))}")
    print(f"\n  ALL: {grand['empties']} empty-after-call truncated trials; "
          f"fewer output tokens than any allowance (proof that no turn ran out while "
          f"writing) in {pct(grand['below_cap'], grand['empties'])}; "
          f"give-up value confirmed exactly in {pct(grand['hit'], grand['resolved'])} of the "
          f"trials where it can be checked; of the {grand['rest']} that cannot be checked "
          f"exactly, {pct(grand['rest_inside'], grand['rest'])} have the same output-token "
          f"signature; an earlier tool call cut at the output cap in "
          f"{pct(grand['cut_call'], grand['empties'])}")

    # ------------------------------------------------------------------ D
    print("\n== D. What the stored snapshots show for truncated trials ==")
    for name, (raw, ov) in cells.items():
        for task in TASKS:
            tr = [r for r in raw.values() if r["task"] == task and r["truncated"]]
            lens = Counter("empty" if not r["response"].strip() else
                           ("500 chars (full snapshot)" if len(r["response"]) == 500
                            else "1-499 chars") for r in tr)
            print(f"  {name:12s} {task:14s} n={len(tr):4d}  stored answer: {dict(lens)}")
    if args.examples:
        for name, (raw, ov) in cells.items():
            shown = 0
            for r in raw.values():
                if (r["task"] in TASKS and r["truncated"] and r["response"].strip()
                        and shown < 2):
                    shown += 1
                    print(f"\n  --- {name} {r['task']} v{r['prompt_variant']} "
                          f"{'/'.join(fixture(r))} output tokens {r['tokens']['completion']} ---")
                    print("  " + clip(r["response"], 400).replace("\n", "\n  "))

    # ------------------------------------------------------------------ E
    print("\n== E. solve: tool-verified minus delivered, by oracle plan length ==")
    print("   delivered <low, high>: low counts graded-correct answers, high adds the "
          "answers that fill the 500-char snapshot (ungradeable)")

    def plan_len(r: dict) -> int:
        return len(gt[r["domain_name"]][r["problem_name"]]["plan"])

    def table(label: str, items: list[tuple[dict, dict]]) -> None:
        print(f"\n  {label}")
        print(f"  {'plan length':11s} {'n':>4s} {'fixtures':>8s} {'tool-verified':>26s} "
              f"{'delivered low':>26s} {'high':>6s} {'gap (tv - delivered)':>22s} "
              f"{'empty/truncated':>15s} {'snapshot full':>13s} {'graded wrong':>12s}")
        for lo, hi in BINS:
            sub = [(r, o) for r, o in items if lo <= plan_len(r) <= hi]
            if not sub:
                continue
            n = len(sub)
            tv = sum(bool(o["tool_verified"]) for _, o in sub)
            ok = sum(o["e2e_strict"] is True for _, o in sub)
            cens = sum(o["e2e_strict"] == "indeterminate" for _, o in sub)
            emp = sum(o["e2e_reason"] == "truncated_empty" for _, o in sub)
            wrong = n - ok - cens - emp
            fx = len({fixture(r) for r, _ in sub})
            w = wilson(tv, n)
            wl = wilson(ok, n)
            name_ = f"{lo}-{hi}" if hi < 10_000 else f"{lo}+"
            print(f"  {name_:11s} {n:4d} {fx:8d} "
                  f"{f'{100*tv/n:.1f}% [{w[0]:.1f}, {w[1]:.1f}]':>26s} "
                  f"{f'{100*ok/n:.1f}% [{wl[0]:.1f}, {wl[1]:.1f}]':>26s} "
                  f"{100*(ok+cens)/n:5.1f}% "
                  f"{f'{100*(tv-ok-cens)/n:.1f} to {100*(tv-ok)/n:.1f} pp':>22s} "
                  f"{100*emp/n:14.1f}% {100*cens/n:12.1f}% {100*wrong/n:11.1f}%")

    everything = []
    for name, (raw, ov) in cells.items():
        items = [(r, ov[k]) for k, r in raw.items() if r["task"] == "solve"]
        everything += items
        table(f"{name}, both arms (n = {len(items)})", items)
        gradeable = [(r, o) for r, o in items if o["e2e_strict"] != "indeterminate"
                     and o["e2e_reason"] != "truncated_empty"]
        good = sum(o["e2e_strict"] is True for _, o in gradeable)
        print(f"  -> answers that could be graded at all (not empty, shorter than the "
              f"snapshot): {len(gradeable)} of {len(items)}; graded correct "
              f"{pct(good, len(gradeable))}; reasons for the rest: "
              f"{dict(Counter(o['e2e_reason'] for _, o in gradeable if o['e2e_strict'] is not True))}")
    table(f"three models pooled, both arms (n = {len(everything)})", everything)
    for arm, vs in ARMS.items():
        sub = [(r, o) for r, o in everything if r["prompt_variant"] in vs]
        table(f"three models pooled, {arm} arm (n = {len(sub)})", sub)

    # ------------------------------------------------------------------ F
    print("\n== F. Gemma solve: 'graded wrong' answers that are the tool's plan behind a "
          "markup prefix ==")
    raw, ov = cells["Gemma 26B"]
    for arm, vs in ARMS.items():
        rows = [(k, r) for k, r in raw.items() if r["task"] == "solve"
                and r["prompt_variant"] in vs]
        inv = [(k, r) for k, r in rows if ov[k]["e2e_reason"] == "plan_invalid"]
        pref = [(k, r) for k, r in inv if r["response"].startswith(GEMMA_PREFIX)]
        same = 0
        for k, r in pref:
            mine = extract_plan_lines(r["response"][len(GEMMA_PREFIX):])
            for tc in r["tool_calls"]:
                if tc["name"] not in PLANNERS:
                    continue
                try:
                    plan = json.loads(tc["result"]).get("plan")
                except (ValueError, AttributeError, TypeError):
                    plan = None
                if plan and [" ".join(p.split()).lower() for p in plan] == mine \
                        and r["success"]:
                    same += 1
                    break
        ok = sum(ov[k]["e2e_strict"] is True for k, _ in rows)
        cens = sum(ov[k]["e2e_strict"] == "indeterminate" for k, _ in rows)
        n = len(rows)
        print(f"  {arm:8s} n={n}: graded plan_invalid {len(inv)}; start with "
              f"{GEMMA_PREFIX!r} {len(pref)}; after removing that prefix the answer is "
              f"line-for-line a plan returned by the planner in a tool-verified trial: {same}")
        print(f"           delivered as graded <{100*ok/n:.1f}, {100*(ok+cens)/n:.1f}>; "
              f"with those {same} counted <{100*(ok+same)/n:.1f}, "
              f"{100*(ok+same+cens)/n:.1f}>  (diagnostic, not a re-grade)")
    if args.examples:
        k, r = next((k, r) for k, r in raw.items() if r["task"] == "solve"
                    and ov[k]["e2e_reason"] == "plan_invalid"
                    and r["response"].startswith(GEMMA_PREFIX))
        print("  example stored answer: " + repr(r["response"][:120]))


if __name__ == "__main__":
    main()
