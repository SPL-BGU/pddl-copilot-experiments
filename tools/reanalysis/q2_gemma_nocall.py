#!/usr/bin/env python3
"""Q2 - what did Gemma do on the validate_plan trials where it did not call the tool?

Canonical cell (thinking off):
  results/sweep5v2-live/slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal/trials.jsonl
Plain arm = prompt variants 11-13, steered = 14-16
(pddl_eval/prompts.py: ACTIVE_PROMPT_VARIANTS, STEERED_VARIANTS).

"Called the tool" is the stored `tool_selected` flag, which for validate_plan
is True only when the server returned a structured call to `validate_plan`
(pddl_eval/scoring.py check_success). Structured calls come only from vLLM's
server-side `gemma4` tool-call parser (pddl_eval/vllm_client.py reads
`message.tool_calls`); the harness never parses calls out of the text. So a
call the server did not recognise would stay inside `response`, of which the
canonical corpus keeps the first 500 characters.

Parts
  A  fields and how much is visible
  B  one category per no-call trial, from the visible 500 characters
  C  token check: could the answer have held a full tool call?
  D  same counts for the steered arm and the anonymized twin (sweep6-live)
  E  SIDE CHECK, NOT CANONICAL: the full-storage rerun (iss024d, thinking on,
     reasoning parser off, 16,384 chars stored). Different reasoning mode;
     never pool with A-D.

Usage:  python3 tools/reanalysis/q2_gemma_nocall.py [--examples]
"""
from __future__ import annotations

import argparse
import re
import statistics
from collections import Counter

from transcripts_common import RESULTS, clip, load_trials, pct

from pddl_eval.prompts import ACTIVE_PROMPT_VARIANTS, STEERED_VARIANTS  # noqa: E402

CELL = "slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal"
NT_CELL = "slurm_vllm_gemma4_26b-a4b_off_no-tools"
TASK = "validate_plan"
PLAIN = tuple(v for v in ACTIVE_PROMPT_VARIANTS if v not in STEERED_VARIANTS)
STEER = tuple(sorted(STEERED_VARIANTS))
assert PLAIN == (11, 12, 13) and STEER == (14, 15, 16), (PLAIN, STEER)
CANON_CAP = 500
OUTPUT_CAP_TOKENS = 6144

# Anything that looks like an attempt to call a tool in text. Deliberately wide:
# a false hit is read by hand, a miss would hide the thing we are looking for.
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
MENTION_PATTERNS = {
    "names the tool (validate_plan)": r"validate_plan",
    "the word 'tool'": r"\btools?\b",
}
VERDICT_LINE = re.compile(r"VERDICT\s*:\s*(VALID|INVALID)\b", re.IGNORECASE)
VERDICT_PROSE = re.compile(
    r"\bplan is (\*\*)?(valid|invalid|not valid)\b|\bthe plan (fails|is not executable)\b",
    re.IGNORECASE)
CONDITIONAL = re.compile(r"\b(determine|check|verify|see|decide)\s+(if|whether)\b[^.]*$|"
                         r"\bif the plan is (valid|invalid)", re.IGNORECASE)

CATS = ("empty", "tool-call-like text visible", "hit the output cap (done_reason=length)",
        "verdict visible in the first 500 chars",
        "prose reasoning, ended on its own, verdict not visible", "other")


def has_toolcall_text(text: str) -> list[str]:
    return [k for k, p in TOOLCALL_PATTERNS.items() if re.search(p, text, re.IGNORECASE)]


def visible_verdict(text: str) -> bool:
    if VERDICT_LINE.search(text):
        return True
    for m in VERDICT_PROSE.finditer(text):
        # "To determine if the plan is valid, ..." is a statement of the task
        if not CONDITIONAL.search(text[max(0, m.start() - 60):m.end()]):
            return True
    return False


def categorize(r: dict) -> str:
    text = r.get("response") or ""
    if not text.strip():
        return CATS[0]
    if has_toolcall_text(text):
        return CATS[1]
    if r.get("done_reason") == "length":
        return CATS[2]
    if visible_verdict(text):
        return CATS[3]
    if r.get("done_reason") == "stop":
        return CATS[4]
    return CATS[5]


def args_chars(r: dict) -> int | None:
    """Characters of the arguments of the first validate_plan call."""
    for tc in r.get("tool_calls") or []:
        if tc.get("name") == TASK:
            a = tc.get("arguments") or {}
            return sum(len(str(v)) for v in a.values())
    return None


def part_bd(label: str, rows: list[dict], examples: bool) -> list[dict]:
    nocall = [r for r in rows if not r["tool_calls"]]
    called = [r for r in rows if r["tool_selected"]]
    print(f"\n{label}: n = {len(rows)}; called the tool {pct(len(called), len(rows))}; "
          f"no structured call at all {pct(len(nocall), len(rows))}; "
          f"called some other tool {len(rows) - len(called) - len(nocall)}")
    if not nocall:
        return nocall
    cats = Counter(categorize(r) for r in nocall)
    for c in CATS:
        print(f"    {c:58s} {pct(cats[c], len(nocall))}")
    assert sum(cats.values()) == len(nocall)
    if examples:
        for c in CATS:
            shown = [r for r in nocall if categorize(r) == c][:3]
            for r in shown:
                print(f"\n  --- example [{c}] v{r['prompt_variant']} {r['domain_name']}/"
                      f"{r['problem_name']}/{r['plan_label']} done={r['done_reason']} "
                      f"output tokens={r['tokens']['completion']} ---")
                print("  " + clip(r["response"], 500).replace("\n", "\n  "))
    return nocall


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", action="store_true")
    args = ap.parse_args()

    raw = load_trials(RESULTS / "sweep5v2-live" / CELL / "trials.jsonl")
    vp = [r for r in raw.values() if r["task"] == TASK and r["with_tools"]]
    plain = [r for r in vp if r["prompt_variant"] in PLAIN]
    steer = [r for r in vp if r["prompt_variant"] in STEER]
    assert len(plain) == 3000 and len(steer) == 3000
    k_plain = sum(bool(r["tool_selected"]) for r in plain)
    k_steer = sum(bool(r["tool_selected"]) for r in steer)
    ok_called = sum(r["success"] for r in plain if r["tool_selected"])
    ok_nocall = sum(r["success"] for r in plain if not r["tool_selected"])
    print("== Reproduce NUMBERS.md (abstract block: 622/3000, 2808/3000, 617/622) ==")
    print(f"plain   called {pct(k_plain, 3000)}; correct when called {pct(ok_called, k_plain)}; "
          f"successes without a call {ok_nocall}")
    print(f"steered called {pct(k_steer, 3000)}")
    assert (k_plain, k_steer, ok_called, ok_nocall) == (622, 2808, 617, 0)

    nocall = [r for r in plain if not r["tool_calls"]]
    print("\n== A. What is stored for a no-call trial ==")
    print("fields:", ", ".join(sorted(nocall[0].keys())))
    lens = Counter(len(r["response"] or "") for r in nocall)
    toks = sorted(r["tokens"]["completion"] for r in nocall)
    print(f"no-call trials: {len(nocall)}")
    print(f"stored answer length: {dict(lens)}  (cap {CANON_CAP} chars)")
    print(f"stored exactly at the cap: {pct(lens[CANON_CAP], len(nocall))}")
    print(f"`thinking` non-empty: {sum(bool(r['thinking']) for r in nocall)}; "
          f"`tool_calls` non-empty: {sum(bool(r['tool_calls']) for r in nocall)}; "
          f"`error` non-empty: {sum(bool(r['error']) for r in nocall)}; "
          f"turns: {dict(Counter(r['tokens']['turns'] for r in nocall))}")
    print(f"done_reason: {dict(Counter(r['done_reason'] for r in nocall))}; "
          f"failure_reason: {dict(Counter(r['failure_reason'] for r in nocall))}")
    q = statistics.quantiles(toks, n=20)
    print(f"output tokens per answer: min {toks[0]}, 5% {q[0]:.0f}, median "
          f"{statistics.median(toks):.0f}, 95% {q[-1]:.0f}, max {toks[-1]} "
          f"(cap {OUTPUT_CAP_TOKENS})")
    # how much of the answer the 500 characters cover: chars per token from
    # called trials whose final answer is complete (< 500 chars)
    cpt = []
    for r in vp:
        a = args_chars(r)
        if a and r["tokens"]["turns"] == 2 and len(r["response"]) < CANON_CAP:
            cpt.append((a + len(r["response"])) / r["tokens"]["completion"])
    cpt.sort()
    cpt_med, cpt_hi = statistics.median(cpt), cpt[int(0.99 * len(cpt))]
    print(f"chars per output token on this model (called trials with a complete answer, "
          f"n = {len(cpt)}): median {cpt_med:.2f}, 99th pct {cpt_hi:.2f}")
    seen = sorted(min(1.0, CANON_CAP / (t * cpt_med)) for t in toks)
    print(f"=> the 500 stored chars are about {100 * statistics.median(seen):.0f}% of the "
          f"median answer (5%-95% of trials: {100 * seen[int(.05 * len(seen))]:.0f}%-"
          f"{100 * seen[int(.95 * len(seen))]:.0f}%)")

    print("\n== B. One category per no-call trial (from the visible 500 chars) ==")
    part_bd("canonical, plain arm (v11-13)", plain, args.examples)
    print("\n  pattern hits in the visible text (not exclusive), plain-arm no-call trials:")
    for k, p in {**TOOLCALL_PATTERNS, **MENTION_PATTERNS}.items():
        n = sum(bool(re.search(p, r["response"], re.IGNORECASE)) for r in nocall)
        print(f"    {k:52s} {pct(n, len(nocall))}")
    opening = Counter(" ".join(r["response"].split()[:6]) for r in nocall)
    print("  most common openings:")
    for k, n in opening.most_common(6):
        print(f"    {n:5d}  {k!r}")
    # is unparsed special-token markup visible at all in this cell's stored text?
    leak = [r for r in raw.values() if re.search(r"<\|[a-z_]+>|<[a-z_]+\|>", r["response"] or "")]
    print(f"  control: rows anywhere in this cell whose stored text shows raw "
          f"special-token markup: {len(leak)}/{len(raw)} "
          f"({dict(Counter(r['task'] for r in leak))}); e.g. "
          f"{leak[0]['response'][:40]!r}" if leak else "  control: no raw markup anywhere")

    print("\n== C. Could the hidden part of the answer hold a full tool call? ==")
    # A validate_plan call must carry domain + problem + plan as arguments.
    need: dict[tuple, int] = {}
    for r in vp:
        a = args_chars(r)
        if a:
            k = (r["domain_name"], r["problem_name"], r["plan_label"])
            need[k] = min(need.get(k, a), a)
    have = [(r, need.get((r["domain_name"], r["problem_name"], r["plan_label"])))
            for r in nocall]
    known = [(r, n) for r, n in have if n]
    print(f"fixtures with a known argument size (some trial on the same fixture did call): "
          f"{len(known)}/{len(nocall)}")
    for label, c in (("median chars/token", cpt_med), ("99th-pct chars/token", cpt_hi)):
        too_short = sum(1 for r, n in known if r["tokens"]["completion"] * c < n)
        print(f"  whole answer has fewer tokens than the arguments alone need "
              f"({label} = {c:.2f}): {pct(too_short, len(known))}")
    fit = [(r, n) for r, n in known if r["tokens"]["completion"] * cpt_hi >= n]
    print(f"  remaining trials where a full call could fit in the unseen text: "
          f"{pct(len(fit), len(known))} -> cannot be determined from stored data")
    # reference: the same model answering the same task with no tools at all
    nt = load_trials(RESULTS / "sweep5v2-live" / NT_CELL / "trials.jsonl")
    nt_vp = [r for r in nt.values() if r["task"] == TASK and not r["with_tools"]
             and r["prompt_variant"] in PLAIN]
    nt_t = sorted(r["tokens"]["completion"] for r in nt_vp)
    qn = statistics.quantiles(nt_t, n=4)
    qc = statistics.quantiles(toks, n=4)
    print(f"reference, same model with NO tools on the same task and prompts (n = {len(nt_vp)}): "
          f"output tokens quartiles {qn[0]:.0f} / {qn[1]:.0f} / {qn[2]:.0f}; "
          f"with-tools no-call trials: {qc[0]:.0f} / {qc[1]:.0f} / {qc[2]:.0f}")

    print("\n== D. Same breakdown elsewhere in the canonical corpora ==")
    part_bd("canonical, steered arm (v14-16)", steer, False)
    raw6 = load_trials(RESULTS / "sweep6-live" / CELL / "trials.jsonl")
    vp6 = [r for r in raw6.values() if r["task"] == TASK and r["with_tools"]]
    part_bd("anonymized twin sweep6-live, plain arm", [r for r in vp6
                                                       if r["prompt_variant"] in PLAIN], False)

    print("\n== D2. Positive control: does an unrecognised call show up in stored text? ==")
    call_markup = re.compile(r"<\|?/?tool_call\|?>|\bcall:\s*[a-z_]+\s*\{")
    n_rows = 0
    found = []
    for corpus in ("sweep5v2-live", "sweep6-live"):
        for mode in ("off", "on"):
            cell = f"slurm_vllm_gemma4_26b-a4b_{mode}_tools_all_minimal"
            rows = load_trials(RESULTS / corpus / cell / "trials.jsonl")
            n_rows += len(rows)
            for r in rows.values():
                m = call_markup.search(r["response"] or "")
                if m:
                    found.append((corpus, mode, r, m.start()))
    print(f"  Gemma with-tools rows scanned (both corpora, both reasoning modes, all tasks, "
          f"both arms): {n_rows}; rows whose stored text holds raw tool-call markup: "
          f"{len(found)}")
    for corpus, mode, r, pos in found:
        arm = "steered" if r["prompt_variant"] in STEER else "plain"
        print(f"    {corpus:13s} think={mode:3s} {r['task']:13s} {arm:7s} "
              f"{r['domain_name']}/{r['problem_name']}  markup at char {pos:3d}  "
              f"done={r['done_reason']:6s} turns={r['tokens']['turns']} "
              f"parsed calls={[t['name'] for t in r['tool_calls']]}")
    first = [x for x in found if not x[2]["tool_calls"]]
    print(f"  of these, first-turn attempts (no parsed call at all): {len(first)}, "
          f"all with done_reason = {sorted({x[2]['done_reason'] for x in first})} "
          f"(an unterminated call cut by the output cap)")
    if first:
        print("  example: " + repr(first[0][2]["response"][:160]))

    print("\n== E. SIDE CHECK - NOT the canonical corpus (iss024d rerun, thinking ON, "
          "reasoning parser off, 16,384 chars stored) ==")
    p = (RESULTS / "iss024d-e2e-live"
         / "slurm_vllm_gemma4_26b-a4b_on_tools_all_minimal_iss024d-e2e" / "trials.jsonl")
    if not p.exists():
        print("  not on disk; skipped")
        return
    full = load_trials(p)
    fp = [r for r in full.values() if r["task"] == TASK and r["with_tools"]
          and r["prompt_variant"] in PLAIN]
    fn = [r for r in fp if not r["tool_calls"]]
    print(f"  plain arm n = {len(fp)}; no structured call {pct(len(fn), len(fp))}")
    cap = 16384
    whole = [r for r in fn if len(r["response"]) < cap]
    print(f"  stored in full (shorter than {cap} chars): {pct(len(whole), len(fn))}; "
          f"cut at {cap}: {len(fn) - len(whole)}")
    print(f"  done_reason: {dict(Counter(r['done_reason'] for r in fn))}")
    narrow = {k: v for k, v in TOOLCALL_PATTERNS.items() if "any special-token" not in k}
    for name, group in (("all no-call", fn), ("stored in full", whole)):
        hit = [r for r in group if any(re.search(p_, r["response"], re.IGNORECASE)
                                       for p_ in narrow.values())]
        ment = [r for r in group if re.search(r"validate_plan|\btools?\b", r["response"],
                                              re.IGNORECASE)]
        verd = [r for r in group if VERDICT_LINE.search(r["response"])]
        print(f"  {name:15s}: tool-call-like text anywhere {pct(len(hit), len(group))}; "
              f"mentions the tool or the word 'tool' {pct(len(ment), len(group))}; "
              f"states a VERDICT line {pct(len(verd), len(group))}")
    marks = Counter(m for r in fn for m in set(re.findall(r"<\|[a-z_]+>|<[a-z_]+\|>",
                                                          r["response"])))
    print(f"  special-token markup seen in these answers (rows): {dict(marks)}")


if __name__ == "__main__":
    main()
