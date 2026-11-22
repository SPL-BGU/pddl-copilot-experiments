#!/usr/bin/env python3
"""RQ3 on simulate, read again with a layout-tolerant reader (post hoc, exploratory).

    python -m tools.reanalysis.rq3_simulate_regrade [--numbers]

The frozen delivered grader reads a state trace only as one JSON value (the
whole answer, or a fenced block). A trace written one JSON object per line
fails it whatever its content. This script keeps every frozen grade and asks,
on the full delivered rerun (three open models, thinking off, plain and steered
prompts, all 100 problems), how much of the simulate loss of RQ3 is that
layout, and what the rest is. Nothing is re-graded in place: the frozen column
is recomputed with the frozen functions and must equal the filed RQ3 cells, and
every other column sits beside it, marked post hoc.

Per cell, on the trials where the tool returned the right result
(tool-verified, the same rows as the frozen readout's E4 cell):

  frozen lost    the delivered final answer fails the frozen grader (the record);
  lenient lost   it fails the frozen grader AND the line reader
                 (`rq3_context_pilot.line_reader_exact`: every line that is one
                 JSON object is one step, and the steps must equal the answer
                 key's trace exactly). The reader is lenient about layout only;
                 on content it is as strict as the frozen grader;
  difference     lenient minus frozen, paired on the same trials.

Every answer still lost under the lenient reader falls in exactly one class,
by fixed rules, first match wins:

  no_room_or_empty       the frozen category is REFUSED_OR_CLIPPED_FINAL (the
                         final turn was refused or ran out of an allowance the
                         full window had clipped) or NO_FINAL_ANSWER;
  tool_ran_another_plan  the frozen category is TOOL_INPUT_ERROR: the trace the
                         tool returned is not the answer key's trace;
  cut_at_output_cap      a non-empty answer that stopped at the output cap
                         (done_reason = length) without a clipped allowance;
  same_length            some reader (the frozen candidates or the line reader)
                         reads a trace with as many steps as the answer key,
                         and at least one step differs: an error of conversion
                         or content;
  wrong_length           a trace is read, with a different number of steps;
  unreadable             no reader reads a trace (prose, tables, another JSON
                         schema, a change list);
  other                  none of the above (expected 0; the script reports it).

When several traces are read, the one with the most states equal to the answer
key's is used; ties go to the one of the answer key's length, then the longer.

Inside same_length, each answer is described by what differs (step numbers,
action labels, facts, numbers; the frozen grade compares all four, and compares
the facts as a sorted list, so a fact listed twice fails it too), and for facts by a comparison with the tool's own result of
that trial. `get_state_transition` returns every state as a map from each
predicate to true or false; the answer must list the true ones. A listed
predicate that the answer key does not hold is either false in the tool's map
(a polarity slip in the conversion) or absent from the map (not taken from the
tool at all). "Conversion only" = the answer differs from the answer key in
facts alone, and every extra predicate is one the tool's map holds as false.

Check against the October reading of the rerun's undecided rows
(`development/reference/delivered_rerun_secondary/hand_reads/e4_readings.json`):
the readers' "content right" verdict against the line reader's, row by row.
Those readers were two model agents with an adjudication, not people.

Outputs (tools/reanalysis/out/): rq3_simulate_regrade.json and .md; with
--numbers the markdown is spliced into development/NUMBERS.md (tag
RQ3-SIMULATE-REGRADE).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from pddl_eval.scoring import _canon_atom, _normalize_trajectory, _safe_json_loads
from tools.delivered_rerun import analysis as A
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import e4 as E4
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.e2e_regrade import oracle_canon_for, simulate_candidates
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq3_context_pilot as PILOT
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
TASK = "simulate"
TAG = "RQ3-SIMULATE-REGRADE"
CLASSES = ("no_room_or_empty", "tool_ran_another_plan", "cut_at_output_cap", "same_length",
           "wrong_length", "unreadable", "other")
CLASS_WORDS = {
    "no_room_or_empty": "no room left, or empty",
    "tool_ran_another_plan": "the tool ran another plan than the answer key's",
    "cut_at_output_cap": "cut at the output cap",
    "same_length": "full-length trace, a step differs",
    "wrong_length": "trace of another length",
    "unreadable": "no trace readable",
    "other": "other",
}
HAND_READS = REPO / "development/reference/delivered_rerun_secondary/hand_reads/e4_readings.json"
RQ23_JSON = Path(__file__).resolve().parent / "out" / "rq23_metrics.json"


# ------------------------------------------------------------------ readers
def read_traces(response: str) -> list[tuple[list[dict], str]]:
    """Every trace some reader finds in the answer, normalised: the frozen
    grader's candidates, then the line reader's."""
    out = []
    for steps, mode in simulate_candidates(response or ""):
        canon = _normalize_trajectory(steps)
        if canon is not None:
            out.append((canon, mode))
    lines = PILOT.line_reader_steps(response or "")
    if lines is not None:
        out.append((lines, "json_lines"))
    return out


def best_trace(traces: list[tuple[list[dict], str]], oracle: list[dict]):
    """The trace with the most states equal to the answer key's; ties go to the
    one of the answer key's length, then the longer. None when there is none."""
    if not traces:
        return None
    return max(traces, key=lambda t: (R1.state_score(t[0], oracle)["matched"],
                                      len(t[0]) == len(oracle), len(t[0])))


def tool_maps(row) -> list[dict] | None:
    """Per step, the tool's own map predicate -> true/false (canonical keys),
    from the last get_state_transition call that returned no error."""
    best = None
    for tc in row.tool_calls:
        if tc.name != "get_state_transition":
            continue
        p = _safe_json_loads(tc.result)
        traj = p.get("trajectory") if isinstance(p, dict) and not p.get("error") else None
        if isinstance(traj, list) and all(
                isinstance(e, dict) and isinstance(e.get("boolean_fluents"), dict) for e in traj):
            best = [{_canon_atom(k): bool(v) for k, v in e["boolean_fluents"].items()}
                    for e in traj]
    return best


# ------------------------------------------------------------------ classes
def describe_same_length(model: list[dict], oracle: list[dict], maps) -> dict:
    """What differs between an answer's trace and the answer key's trace of the
    same length, and how the differing facts relate to the tool's own map."""
    d = {"step numbers": 0, "action": 0, "facts": 0, "a fact listed twice": 0, "numbers": 0,
         "extra_false_in_map": 0,
         "extra_not_in_map": 0, "omitted_true": 0, "number_wrong_or_extra": 0,
         "map": maps is not None}
    for i, (m, o) in enumerate(zip(model, oracle)):
        if m.get("step") != o.get("step"):
            d["step numbers"] += 1
        if m["action"] != o["action"]:
            d["action"] += 1
        mb, ob = set(m["boolean"]), set(o["boolean"])
        if mb != ob:
            d["facts"] += 1
            d["omitted_true"] += len(ob - mb)
            for a in mb - ob:
                known = maps is not None and i < len(maps) and maps[i].get(a) is False
                d["extra_false_in_map" if known else "extra_not_in_map"] += 1
        elif list(m["boolean"]) != list(o["boolean"]):
            d["a fact listed twice"] += 1          # same set; the frozen grade compares lists
        if m["numeric"] != o["numeric"]:
            d["numbers"] += 1
            d["number_wrong_or_extra"] += sum(1 for k, v in m["numeric"].items()
                                              if o["numeric"].get(k) != v)
    parts = [k for k in ("step numbers", "action", "facts", "a fact listed twice", "numbers")
             if d[k]]
    d["differs_in"] = " + ".join(parts) or "nothing"
    d["conversion_only"] = bool(parts == ["facts"] and d["map"] and not d["extra_not_in_map"])
    if parts == ["facts"] and d["map"]:
        d["facts_kind"] = ("lists a predicate the tool's map does not hold"
                           if d["extra_not_in_map"] else
                           "false listed as true, and true omitted"
                           if d["extra_false_in_map"] and d["omitted_true"] else
                           "false listed as true" if d["extra_false_in_map"] else "true omitted")
    else:
        d["facts_kind"] = None
    d["numbers_kind"] = (None if parts != ["numbers"] else
                         "a number wrong" if d["number_wrong_or_extra"] else "numbers left out")
    ms, os_ = [R1.state_of(s) for s in model], [R1.state_of(s) for s in oracle]
    d["shifted_by_one"] = bool(len(os_) > 2 and (ms[1:] == os_[:-1] or ms[:-1] == os_[1:]))
    return d


def classify_still_lost(row, frozen_cat: str, oracle: list[dict]) -> dict:
    """The class of one tool-verified answer that fails both readers."""
    if frozen_cat in (E4.REFUSED_OR_CLIPPED_FINAL, E4.NO_FINAL_ANSWER):
        # ISS-029: on six problems the plan in the prompt is not the answer key's plan, so
        # the tool's own trace is not the answer key's and no answer could pass.
        return {"cls": "no_room_or_empty",
                "key_from_another_plan": E4._last_tool_trajectory(row) != oracle}
    if frozen_cat == E4.TOOL_INPUT_ERROR:
        return {"cls": "tool_ran_another_plan"}
    if row.done_reason == "length":
        return {"cls": "cut_at_output_cap"}
    best = best_trace(read_traces(row.response), oracle)
    if best is None:
        return {"cls": "unreadable"}
    trace, mode = best
    if trace == oracle:                     # cannot happen: one of the readers would have passed
        return {"cls": "other", "mode": mode}
    if len(trace) == len(oracle):
        return {"cls": "same_length", "mode": mode,
                **describe_same_length(trace, oracle, tool_maps(row))}
    return {"cls": "wrong_length", "mode": mode,
            "shorter": len(trace) < len(oracle),
            "drops_first_state": [R1.state_of(s) for s in trace]
            == [R1.state_of(s) for s in oracle[1:]]}


# ------------------------------------------------------------------ analysis
def hand_read_id(row) -> str:
    return (f"{row.model_tag}|{row.task}|{row.arm}|{row.domain}|{row.problem}|"
            f"{row.plan_label}|v{row.variant}")


def regrade(cells, grades, gt_cache, readout, hand: dict, filed: dict):
    want = {(e["model"], e["task"], e["arm"]): e for e in readout["e4"]}
    out, bad, confusion, missed = [], [], Counter(), Counter()
    seen_hand = set()
    for m in C.PART_A_MODELS:
        rows = list(cells["rerun_a"][m].rows)
        for arm in C.ARMS:
            g = A.e4_cell(rows, grades, gt_cache, m, TASK, arm)
            e = want.get((m, TASK, arm))
            if e is None or (g.n_tool_correct, g.n_gap, g.categories) != (
                    e["n_tool_correct"], e["n_gap"], e["categories"]):
                bad.append(f"E4 {m}/{TASK}/{arm} does not equal the frozen readout")
            tv = [r for r in rows if r.task == TASK and r.arm == arm and r.success is True]
            doms = [r.domain for r in tv]
            frozen, lenient, reading, classes, kinds = [], [], [], Counter(), Counter()
            sub = Counter()
            for r in tv:
                x = grades[(r.cell, r.trial_key)]
                lost = x.ok is False
                oracle = oracle_canon_for(gt_cache, {"domain_name": r.domain,
                                                     "problem_name": r.problem})
                if oracle is None:
                    raise R1.Halt(f"no answer-key trace for {r.domain}/{r.problem}")
                line_ok = lost and PILOT.line_reader_exact(r.response, oracle)
                hr = hand.get(hand_read_id(r)) if lost else None
                if hr is not None:
                    seen_hand.add(hand_read_id(r))
                    confusion[(hr["human_correct"], "right" if line_ok else "not right")] += 1
                    if hr["human_correct"] == "yes" and not line_ok:
                        missed[hr["category"]] += 1
                frozen.append(lost)
                lenient.append(lost and not line_ok)
                reading.append(lost and not line_ok
                               and not (hr is not None and hr["human_correct"] == "yes"))
                if lost and not line_ok:
                    c = classify_still_lost(r, E4.classify(r, x, gt_cache)[0], oracle)
                    classes[c["cls"]] += 1
                    sub["no_room_key_from_another_plan"] += bool(c.get("key_from_another_plan"))
                    if c["cls"] == "same_length":
                        kinds[c["differs_in"]] += 1
                        sub["conversion_only"] += c["conversion_only"]
                        sub["shifted_by_one"] += c["shifted_by_one"]
                        sub["no_tool_map"] += not c["map"]
                        if c["facts_kind"]:
                            sub["facts: " + c["facts_kind"]] += 1
                        if c["numbers_kind"]:
                            sub["numbers: " + c["numbers_kind"]] += 1
                    if c["cls"] == "wrong_length":
                        sub["shorter" if c["shorter"] else "longer"] += 1
                        sub["drops_first_state"] += c["drops_first_state"]
            cell = {
                "model": model_name(m), "arm": arm,
                "n_trials": sum(r.task == TASK and r.arm == arm for r in rows),
                "n_tool_right": len(tv), "n_lost_frozen": sum(frozen),
                "n_right_under_line_reader": sum(frozen) - sum(lenient),
                "n_lost_lenient": sum(lenient), "n_lost_after_reading": sum(reading),
                "lost_frozen": R1.boot(frozen, doms), "lost_lenient": R1.boot(lenient, doms),
                "difference": R1.boot([float(b) - float(a) for a, b in zip(frozen, lenient)], doms),
                "lost_after_reading": R1.boot(reading, doms),
                "frozen_categories": {k: v for k, v in g.categories.items() if v},
                "classes": {k: classes.get(k, 0) for k in CLASSES},
                "same_length_differs_in": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
                "detail": dict(sorted(sub.items())),
            }
            if sum(cell["classes"].values()) != cell["n_lost_lenient"]:
                bad.append(f"{m}/{arm}: the classes do not sum to the answers still lost")
            f = filed.get((cell["model"], arm))
            if f is None or (f["n_tool_right"], f["n_lost"]) != (len(tv), sum(frozen)) or any(
                    abs(f["lost"][k] - cell["lost_frozen"][k]) > 1e-9 for k in ("est", "lo", "hi")):
                bad.append(f"{m}/{arm}: the frozen column is not the filed RQ3 cell")
            out.append(cell)
    hand_sim = {k for k, v in hand.items() if v["task"] == TASK}
    if seen_hand != hand_sim:
        bad.append(f"October reading: {len(hand_sim - seen_hand)} simulate rows are not among "
                   f"the frozen lost rows, {len(seen_hand - hand_sim)} are unknown")
    if bad:
        raise R1.Halt("self-check failed:\n  " + "\n  ".join(bad))
    return out, confusion, missed


# ------------------------------------------------------------------ render
def render(cells: list[dict], confusion: Counter, missed: Counter) -> str:
    L = []
    w = L.append
    w("*Generated by `tools/reanalysis/rq3_simulate_regrade.py`. **Post hoc and exploratory; "
      "the frozen readout is the record and nothing here replaces it.** Delivered rerun, "
      "three open models, thinking off, simulate, all 100 problems. \"Tool right\" = the tool "
      "returned the right result (the rows of the frozen readout's E4 cell; the frozen column "
      "is recomputed with the frozen functions and equals the filed RQ3 cells, or the script "
      "halts). \"Lenient\" = the answer fails the frozen grader and also fails the line "
      "reader, which takes every line that is one JSON object as one step and requires the "
      "steps to equal the answer key's trace exactly: lenient about layout, as strict as the "
      "frozen grader about content. \"Difference\" is paired on the same trials. \"After the "
      "October reading\" also removes the rows that the two readers of October (model agents, "
      "with an adjudication; not people) judged right in content. Shares in percent with 95% "
      "domain-cluster bootstrap percentile intervals (10,000 resamples, seed 20261002).*")
    w("")
    w("#### RQ3 simulate: frozen grade beside the layout-tolerant reading")
    w("")
    w(md_table(["model", "prompt", "trials", "tool right", "lost, frozen (record)",
                "frozen share", "right under the line reader", "lost, lenient",
                "lenient share", "difference (points)", "share after the October reading"],
               [[c["model"], c["arm"], c["n_trials"], c["n_tool_right"], c["n_lost_frozen"],
                 R1.cell(c["lost_frozen"]), c["n_right_under_line_reader"], c["n_lost_lenient"],
                 R1.cell(c["lost_lenient"]), R1.diff_cell(c["difference"]),
                 f"{c['n_lost_after_reading']}: {R1.cell(c['lost_after_reading'])}"]
                for c in cells]))
    w("")
    w("#### What the answers still lost under the lenient reader are")
    w("")
    w("One class per answer, first match wins: " + "; ".join(
        f"*{CLASS_WORDS[k]}*" for k in CLASSES) + ". The first two come from the frozen "
      "category. \"Full-length trace, a step differs\" = some reader finds a trace with as "
      "many steps as the answer key and at least one step is not equal: an error of "
      "conversion or content.")
    w("")
    w(md_table(["model", "prompt", "still lost", *[CLASS_WORDS[k] for k in CLASSES],
                "no room: of which the answer key is another plan's"],
               [[c["model"], c["arm"], c["n_lost_lenient"],
                 *[f"{c['classes'][k]} ({100 * c['classes'][k] / c['n_lost_lenient']:.0f}%)"
                   if c["n_lost_lenient"] else "0" for k in CLASSES],
                 c["detail"].get("no_room_key_from_another_plan", 0)] for c in cells]))
    w("")
    w("The last column counts answers on the six problems of ISS-029 (the plan in the prompt "
      "is not the answer key's plan, so the tool's own trace is not the answer key's). They "
      "are tool-right by the run-time grade and could not pass the delivered grade with any "
      "answer; all of them are in the no-room class.")
    w("")
    w("#### Inside \"full-length trace, a step differs\"")
    w("")
    w("\"Differs in\" = which parts of a step are not equal to the answer key (step numbers, "
      "action label, facts = the list of true predicates, numbers). \"Conversion only\" = facts alone differ, and every listed "
      "predicate the answer key does not hold is one the tool's own map holds as false (the "
      "tool returns every predicate with true or false; the answer must list the true "
      "ones). \"Shifted\" = every state is right but sits one step early or late.")
    w("")
    w(md_table(["model", "prompt", "answers", "differs in (count)", "conversion only",
                "facts only: kind (count)", "numbers only: kind (count)",
                "shifted by one step"],
               [[c["model"], c["arm"], c["classes"]["same_length"],
                 "; ".join(f"{k} {v}" for k, v in c["same_length_differs_in"].items()) or "–",
                 c["detail"].get("conversion_only", 0),
                 "; ".join(f"{k[7:]} {v}" for k, v in c["detail"].items()
                           if k.startswith("facts: ")) or "–",
                 "; ".join(f"{k[9:]} {v}" for k, v in c["detail"].items()
                           if k.startswith("numbers: ")) or "–",
                 c["detail"].get("shifted_by_one", 0)] for c in cells]))
    w("")
    w("#### Check against the October reading (simulate rows the frozen rules could not decide)")
    w("")
    n = sum(confusion.values())
    w(f"{n} rows. Readers' verdict on the content against the line reader's verdict:")
    w("")
    w(md_table(["readers: content right?", "line reader: right", "line reader: not right"],
               [[k, confusion.get((k, "right"), 0), confusion.get((k, "not right"), 0)]
                for k in ("yes", "no", "unclear")]))
    w("")
    w("Rows the readers judged right that the line reader does not read, by the readers' "
      "category: " + ("; ".join(f"{k} {v}" for k, v in sorted(missed.items(), key=lambda kv: -kv[1]))
                      or "none") + ".")
    return "\n".join(L) + "\n"


def tex_rows(cells: list[dict]) -> str:
    """The rows of the paper's table (pasted into the tex, never edited there)."""
    names = {"Gemma-26B": "Gemma-MoE-26B"}
    by = {(c["model"], c["arm"]): c for c in cells}

    def share(b: dict, signed: bool = False) -> str:
        f = "{:+.1f}" if signed else "{:.1f}"
        return (f"${f.format(b['est'])}$ {{\\scriptsize$[{f.format(b['lo'])},"
                f"\\,{f.format(b['hi'])}]$}}")

    rows = []
    for m in ("Qwen3.5-9B", "Gemma-26B", "Qwen3.6-35B"):
        for i, arm in enumerate(("plain", "steered")):
            c = by[(m, arm)]
            k = c["classes"]
            rows.append(" & ".join([
                names.get(m, m) if i == 0 else "", arm, f"${c['n_tool_right']}$",
                share(c["lost_frozen"]), share(c["lost_lenient"]),
                share(c["difference"], signed=True), f"${k['no_room_or_empty']}$",
                f"${k['same_length']}$", f"${k['wrong_length'] + k['unreadable']}$"]) + r" \\")
    return "\n".join(rows) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--hand-reads", type=Path, default=HAND_READS)
    ap.add_argument("--rq23-json", type=Path, default=RQ23_JSON)
    args = ap.parse_args(argv)
    R1.fill_data_args(args)
    try:
        cells, grades, gt_cache = R1.load_rerun_cells(args)
        readout = json.loads(args.readout_json.read_text())
        hand = {r["id"]: r for r in json.loads(args.hand_reads.read_text())["rows"]}
        filed = {(c["model"], c["arm"]): c
                 for c in json.loads(args.rq23_json.read_text())["rq3"]["rerun"]
                 if c["task"] == TASK}
        out, confusion, missed = regrade(cells, grades, gt_cache, readout, hand, filed)
    except (R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed, ValueError) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    md = render(out, confusion, missed)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rq3_simulate_regrade.json").write_text(json.dumps({
        "frozen_package_sha256": R1.FROZEN_SHA, "post_hoc": True, "cells": out,
        "october_reading_vs_line_reader": {f"{a}|{b}": v for (a, b), v in sorted(confusion.items())},
        "judged_right_not_read_by_line_reader": dict(missed)}, indent=1) + "\n")
    (args.out / "rq3_simulate_regrade.md").write_text(md)
    (args.out / "tex").mkdir(exist_ok=True)
    (args.out / "tex" / "rq3_simulate_regrade.tex").write_text(tex_rows(out))
    print(md)
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
