#!/usr/bin/env python3
"""C4: example transcripts from the delivered rerun, drawn by a stated rule.

    python3 tools/reanalysis/c4_select_transcripts.py \\
        --results /Users/omereliyahu/personal/pddl-copilot-experiments/results \\
        --out development/draft_C4_transcripts.md

Read-only over results. Descriptive: not a gate, not frozen, adds no reading
to the prereg. Rows are loaded by the frozen loader (`tools.delivered_rerun.run
.load_all`), graded by the frozen delivered grader (`grade.grade`, with the
solve-plan verdict cache `delivered-rerun-secondary/plan_verdicts.json`, no
live validator), and the E4 rows are labelled by the frozen `e4.classify`.
Before anything is drawn, the script checks that the frozen package hash is
822aace..., that the ground-truth cache matches the pinned hash, that the
domain files match the registered manifest, and that its grades reproduce the
E1 and E4 counts of the frozen readout (`delivered_rerun_secondary
.check_against_readout`).

The selection rule is fixed in the constants below (SEED, caps, DOUBT_WORDS)
and in `pools()`. For each example the eligible set is listed in a fixed order
(the trial id, sorted), shuffled once with `random.Random(SEED + pool
number)`, and the first row in that order is drawn. A drawn row whose plan
argument does not match the rebuilt prompt is skipped (`rebuild_check`).
Every drawn row is read by a person. If the reading finds the row does not
show what the example is meant to show, the row is entered in READINGS as
rejected, with the reason, and the next row in the same shuffled order is
taken (the redraw rule). Nothing is picked by eye.

The prompt is not stored in the trial rows. It is rebuilt with the harness's
own `build_jobs` + `build_messages` (the same code path the run used) from the
domain files and the ground-truth cache. For simulate the run built the
prompt from a plan computed live at run start, which is not always the
cache's plan (side finding 2 in the output).

Output: one markdown file (default development/draft_C4_transcripts.md).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# --------------------------------------------------------------- the rule
SEED = 20261109                      # pool k is shuffled with Random(SEED + k)
NOCALL_ANSWER_CAP = 3000             # pool 1: final answer at most this many characters
RELAY_ANSWER_CAP = 1500              # pool 2: final answer at most this many characters
WRONG_FACTS_ANSWER_CAP = 3000        # pool 4: final answer at most this many characters
# Pool 1: a reader note that flags a doubtful reason or an incomplete check
# drops the row. Matched case-insensitively against BOTH readers' notes.
DOUBT_WORDS = ("wrong", "doubtful", "dubious", "muddled", "retract", "flip", "contradict",
               "sloppy", "garbled", "hedg", "conditional", "worry", "elide", "skip",
               "not a full", "no full", "not a step trace", "no real check",
               "without confirming", "misread", "loose")
DOUBT_RE = re.compile("|".join(re.escape(w) for w in DOUBT_WORDS), re.IGNORECASE)

# Abridging. Every elision is marked in the text with what was left out.
DOMAIN_HEAD, DOMAIN_TAIL = 14, 2
PROBLEM_HEAD, PROBLEM_TAIL = 8, 10
PLAN_HEAD, PLAN_TAIL = 20, 5
RESULT_HEAD, RESULT_TAIL = 30, 8
ANSWER_HEAD, ANSWER_TAIL = 60, 10

# Served builds, from the rerun cells' `meta.models` and every row's `model`
# field (checked at run time). Serving: vLLM 0.20.2 (prereg §8a smoke record,
# reference/serving_env_20260913.md).
BUILDS = {
    "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit":
        "community AWQ 4-bit quantisation (Hugging Face uploader `cyankiwi`) of Google's "
        "Gemma 4 26B-A4B instruct model; not the official Google weights",
    "Qwen/Qwen3.5-9B":
        "official release from the Qwen organisation's repository, no third-party "
        "quantisation; the serving dtype is not recorded in the cell metadata",
    "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit":
        "community AWQ 4-bit quantisation (Hugging Face uploader `cyankiwi`) of "
        "Qwen3.6-35B-A3B; not the official Qwen weights",
}
VLLM = "0.20.2"

# Readings of drawn rows: trial id -> (verdict, note). verdict is "confirmed"
# or "rejected". A rejected row is skipped and the next in order is drawn.
# Filled in after a person read each drawn transcript in full.
READINGS: dict[str, tuple[str, str]] = {
    "gemma4_26b-a4b|validate_plan|plain|counters|p04|b2|v11": ("confirmed", (
        "Confirmed (read in full on 2026-11-09, against `domains/numeric/counters/p04.pddl` "
        "and `p04_b2.plan`). Every rate starts at 0, so each `(increment c1)` adds 0 and "
        "`c1` stays at 8. The goal needs value(c0) + 1 <= value(c1), that is 15 <= 8, which "
        "fails. The answer reasons exactly this way and ends in `VERDICT: INVALID`: the "
        "right verdict for the right reason. It makes no tool call and does not mention a "
        "tool.")),
    "gemma4_26b-a4b|solve|plain|miconic|p04||v12": ("confirmed", (
        "Confirmed (read in full on 2026-11-09). One planner call. After the leaked channel "
        "marker, the answer is the tool's 10 actions in the same order, nothing added and "
        "nothing dropped. The grader strips the marker once, extracts the 10 lines, and the "
        "validator accepts the plan.")),
    "qwen3_6_35b|simulate|steered|depots|p03||v16": ("confirmed", (
        "Confirmed (read in full on 2026-11-09). The model passed the prompt's domain, "
        "problem and 11-action plan to `get_state_transition`. The tool's trajectory is "
        "right (stored success true). The result is 49,830 characters: a list of the "
        "changes at each step, then all 12 states (the initial one and one after each "
        "action), each listing every ground fact of the problem as true or false. The next "
        "turn would have had to hold the prompt and this result, which does not fit in "
        "16,384 tokens, so the server refused it and the final answer is empty. The model "
        "never got a turn in which to relay the result.")),
    "Qwen3_5_9B|solve|steered|drone|p05||v15": ("confirmed", (
        "Confirmed (read in full on 2026-11-09). The classic planner failed on this numeric "
        "domain and the model then called the numeric planner, which returned a 110-action "
        "plan (stored grade: valid). The answer restates it as 110 lines but miscounts two "
        "runs of a repeated action: 7 `(decrease_y)` where the tool has 8, and 9 "
        "`(increase_y)` where the tool has 8. The length is unchanged and every other action "
        "matches; the validator rejects the restated plan. A transcription error in the "
        "plain sense: the model had the right plan and copied it wrong.")),
}

POOL_TITLES = {
    1: "Gemma skips the tool and judges the plan correctly in prose",
    2: "A correct relay: the tool result is right and the delivered answer is right",
    3: "Simulate: the tool result fills the context window",
    4: "Solve: a transcription error (the answer restates the tool's plan with a change)",
}


# --------------------------------------------------------------- pure helpers
def fence(text: str, lang: str = "text") -> str:
    """A fenced block that cannot be closed by backticks inside `text`."""
    run = max((len(m) for m in re.findall(r"`+", text)), default=0)
    f = "`" * max(3, run + 1)
    return f"{f}{lang}\n{text}\n{f}"


def abridge_lines(text: str, head: int, tail: int, what: str) -> str:
    """Keep the first `head` and last `tail` lines; mark the elision."""
    lines = text.splitlines()
    if len(lines) <= head + tail + 1:
        return text
    gone = len(lines) - head - tail
    mid = [f"[... {gone} lines of {what} elided ...]"]
    return "\n".join(lines[:head] + mid + (lines[-tail:] if tail else []))


def abridge_chars(text: str, head: int, tail: int, what: str) -> str:
    if len(text) <= head + tail + 80:
        return text
    return (text[:head] + f"[... {len(text) - head - tail:,} characters of {what} elided ...]"
            + text[-tail:])


def doubt_flag(*notes: str) -> str | None:
    """The first doubt word found in any of the notes, or None."""
    for n in notes:
        m = DOUBT_RE.search(n or "")
        if m:
            return m.group(0).lower()
    return None


def draw_order(ids: list[str], pool: int) -> list[str]:
    order = sorted(ids)
    random.Random(SEED + pool).shuffle(order)
    return order


def pick(order: list[str], readings: dict) -> tuple[str | None, list[tuple[str, str]]]:
    """First id in `order` not rejected by a reading; and the rejected ones before it."""
    skipped = []
    for i in order:
        v = readings.get(i)
        if v and v[0] == "rejected":
            skipped.append((i, v[1]))
            continue
        return i, skipped
    return None, skipped


def norm_action(a: str) -> str:
    return " ".join(str(a).split()).lower()


def plan_shape(tool: tuple, answer: tuple) -> str:
    """How a delivered plan differs from the tool's plan (descriptive)."""
    if answer == tool:
        return "identical"
    if len(answer) > len(tool) and answer[:len(tool)] == tool:
        return "tool plan, then extra lines"
    if len(answer) > len(tool) and answer[-len(tool):] == tool:
        return "extra lines, then tool plan"
    if len(answer) == len(tool):
        return "same length, some actions differ"
    return "other"


def goal_text(problem_pddl: str) -> str:
    low = problem_pddl.lower()
    i = low.find("(:goal")
    return " ".join(low[i:].split()) if i >= 0 else ""


_ACT_RE = re.compile(r"\([^()]*\)")


def plan_actions(p) -> tuple[str, ...]:
    """A plan as normalised actions, whatever form it was passed in: a list, a
    JSON string holding a list, one action per line, or actions run together.
    Parentheses, case and spacing are ignored."""
    if isinstance(p, str) and p.strip().startswith("["):
        try:
            p = json.loads(p)
        except ValueError:
            pass
    text = "\n".join(map(str, p)) if isinstance(p, list) else str(p)
    items = _ACT_RE.findall(text) if "(" in text else [x for x in text.splitlines() if x.strip()]
    return tuple(" ".join(a.replace("(", " ").replace(")", " ").split()).lower() for a in items)


def same_text(a: str, b: str) -> str | None:
    """'exact', 'whitespace' (equal once runs of whitespace are collapsed),
    'comments' (equal once ';' comment lines are dropped as well), or None."""
    if a == b:
        return "exact"
    if " ".join(a.split()) == " ".join(b.split()):
        return "whitespace"

    def strip(t: str) -> str:
        return " ".join(" ".join(x for x in t.splitlines()
                                 if not x.strip().startswith(";")).split())
    if strip(a) == strip(b):
        return "comments"
    return None


SAME_TEXT_WORDS = {"exact": "byte for byte",
                   "whitespace": "the same once whitespace is collapsed",
                   "comments": "the same once `;` comment lines are dropped and whitespace "
                               "is collapsed"}


def clip_long_lines(text: str, cap: int = 300) -> str:
    """Cut any single line longer than `cap` characters, marking the cut."""
    return "\n".join(abridge_chars(ln, cap - 60, 40, "this line") if len(ln) > cap else ln
                     for ln in text.splitlines())


def run_diffs(tool: tuple, ans: tuple) -> list[dict]:
    """Where two plans differ as runs of one repeated action: each run (in
    order) whose action or length differs, with its 1-based start step."""
    from itertools import groupby, zip_longest

    def runs(p):
        out, step = [], 1
        for a, g in groupby(p):
            n = len(list(g))
            out.append((a, n, step))
            step += n
        return out
    out = []
    for t, a in zip_longest(runs(tool), runs(ans)):
        if t is None or a is None or t[:2] != a[:2]:
            out.append({"tool": t, "answer": a})
    return out


def keep_windows(lines: list[str], keep: list[tuple[int, int]], what: str) -> str:
    """Keep the given 0-based inclusive line ranges; mark every gap."""
    want = sorted({i for lo, hi in keep for i in range(max(0, lo), min(len(lines), hi + 1))})
    out, prev = [], -1
    for i in want:
        if i > prev + 1:
            out.append(f"[... {i - prev - 1} lines of {what} elided ...]")
        out.append(lines[i])
        prev = i
    if prev < len(lines) - 1:
        out.append(f"[... {len(lines) - 1 - prev} lines of {what} elided ...]")
    return "\n".join(out)


# --------------------------------------------------------------- data
class Halt(Exception):
    pass


def row_id(r) -> str:
    return (f"{r.model_tag}|{r.task}|{r.arm}|{r.domain}|{r.problem}|{r.plan_label}"
            f"|v{r.variant}")


def stored_key(r) -> list:
    from tools.delivered_rerun import constants as C
    return [C.MODEL_IDS[r.model_tag], r.task, r.domain, r.problem, r.plan_label, r.variant,
            True, C.THINK, C.TOOL_FILTER, C.STYLE_A]


def line_index(cell_dir: Path) -> dict[tuple, int]:
    """Stored trial key -> line number in trials.jsonl (1-based)."""
    out: dict[tuple, int] = {}
    with (cell_dir / "trials.jsonl").open() as fh:
        for n, ln in enumerate(fh, 1):
            if not ln.strip():
                continue
            try:
                k = json.loads(ln)["key"]
            except (json.JSONDecodeError, KeyError):
                continue
            out[tuple(k)] = n
    return out


def load(args):
    from tools.delivered_rerun import constants as C
    from tools.delivered_rerun import grade as G
    from tools.delivered_rerun import run as RUN
    from tools.delivered_rerun_secondary import FROZEN_SHA, check_against_readout
    from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash

    if RUN.package_sha256() != FROZEN_SHA:
        raise Halt("the frozen package tools/delivered_rerun changed (hash is not 822aace...)")
    RUN.check_domains(args.domains_dir)
    gt_cache = json.loads((args.results / "derived/gt_cache.json").read_text())
    if canonical_hash(gt_cache) != PREREG_PINNED_HASH:
        raise Halt("ground-truth cache does not match the pinned canonical hash")
    design = C.REGISTERED
    C.assert_registered(design)
    cells = RUN.load_all(design, args.results / "delivered-rerun",
                         args.results / "sweep5v2-live")
    rerun_a = cells["rerun_a"]
    table = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"] for e in json.loads(
        (args.results / "delivered-rerun-secondary/plan_verdicts.json").read_text())}
    rows = [r for m in C.PART_A_MODELS for r in rerun_a[m].rows]
    need = G.solve_plans_to_validate(rows)
    missing = need - set(table)
    if missing:
        raise Halt(f"{len(missing)} solve plans have no cached validator verdict; run "
                   "tools/delivered_rerun_secondary.py first (this script never calls "
                   "the live validator)")
    grades = {(r.cell, r.trial_key): G.grade(r, gt_cache, table) for r in rows}
    readout = json.loads(args.readout_json.read_text())
    check_against_readout(readout, rerun_a, grades, gt_cache)
    # served build: every row's model id and each cell's meta.models
    for m in C.PART_A_MODELS:
        cell_dir = args.results / "delivered-rerun" / rerun_a[m].spec.name
        metas = [json.loads(p.read_text())["meta"] for p in cell_dir.glob("summary_*.json")]
        if not metas or any(mt["models"] != [C.MODEL_IDS[m]] for mt in metas):
            raise Halt(f"{cell_dir}: meta.models does not name {C.MODEL_IDS[m]}")
        if C.MODEL_IDS[m] not in BUILDS:
            raise Halt(f"no build description for {C.MODEL_IDS[m]}")
    rows_c = [r for m in C.PART_A_MODELS for r in cells["rerun_c"][m].rows
              if r.task == "simulate"]
    grades.update({(r.cell, r.trial_key): G.grade(r, gt_cache, table) for r in rows_c})
    return design, rerun_a, rows, rows_c, grades, gt_cache, readout


# --------------------------------------------------------------- pools
def pools(args, rerun_a, rows, grades, gt_cache, domains):
    from tools.delivered_rerun import constants as C
    from tools.delivered_rerun import e4 as E4
    from pddl_eval.scoring import strip_leaked_channel_prefix

    by_id = {row_id(r): r for r in rows}
    out: dict[int, dict] = {}

    # pool 1: the hand-read Gemma no-call sample
    rd = json.loads(args.nocall_readings.read_text())
    idx = json.loads((args.results / "delivered-rerun-secondary/nocall_sample/index.json")
                     .read_text())
    steps = Counter()
    elig1, dropped1 = [], []
    for e in idx:
        steps["packets in the hand-read sample"] += 1
        read = next(x for x in rd["rows"] if x["id"] == e["id"])
        a, b = read["A"], read["B"]
        if not (a["right"] == "yes" and b["right"] == "yes"):
            continue
        steps["both readers: verdict right"] += 1
        flag = doubt_flag(a.get("note", ""), b.get("note", ""))
        if flag:
            dropped1.append((e["id"], flag))
            continue
        steps["... and no reader note flags the reasoning"] += 1
        pk = json.loads((args.results / "delivered-rerun-secondary/nocall_sample" / e["file"])
                        .read_text())
        r = by_id[e["id"]]
        if strip_leaked_channel_prefix(r.response) != pk["final_answer"] or r.invoked:
            raise Halt(f"packet {e['id']} does not match its row")
        if len(pk["final_answer"]) > NOCALL_ANSWER_CAP:
            continue
        steps[f"... and final answer <= {NOCALL_ANSWER_CAP:,} characters"] += 1
        elig1.append(e["id"])
    out[1] = {"eligible": elig1, "steps": steps, "dropped_by_note": dropped1,
              "readings": {x["id"]: x for x in rd["rows"]}}

    # pool 2: correct relay on solve
    steps = Counter()
    elig2 = []
    for r in rows:
        if r.task != "solve":
            continue
        steps["solve rows (3 models x 2 arms)"] += 1
        g = grades[(r.cell, r.trial_key)]
        if not (r.success is True and g.ok is True):
            continue
        steps["tool-verified right and delivered right"] += 1
        if not (len(r.tool_calls) == 1 and r.tool_calls[0].name in E4.PLANNERS):
            continue
        steps["... and exactly one tool call, to a planner"] += 1
        if len(r.response) > RELAY_ANSWER_CAP:
            continue
        steps[f"... and final answer <= {RELAY_ANSWER_CAP:,} characters"] += 1
        elig2.append(row_id(r))
    out[2] = {"eligible": elig2, "steps": steps}

    # pool 3: simulate, final turn refused because the prompt filled the window
    steps = Counter()
    elig3 = []
    for r in rows:
        if r.task != "simulate":
            continue
        steps["simulate rows (3 models x 2 arms)"] += 1
        g = grades[(r.cell, r.trial_key)]
        if not (r.success is True and g.ok is False):
            continue
        steps["tool-verified right, delivered wrong (E4 rows)"] += 1
        cat, sub = E4.classify(r, g, gt_cache)
        if (cat, sub) != (E4.REFUSED_OR_CLIPPED_FINAL,
                          "final turn refused: prompt filled the window"):
            continue
        steps["... and E4 label 'final turn refused: prompt filled the window'"] += 1
        if not (len(r.tool_calls) == 1 and r.tool_calls[0].name == "get_state_transition"):
            continue
        steps["... and exactly one tool call, to get_state_transition"] += 1
        elig3.append(row_id(r))
    out[3] = {"eligible": elig3, "steps": steps}

    # pool 4: solve transcription error (E4 WRONG_FACTS, same length)
    steps = Counter()
    elig4 = []
    shapes = Counter()
    goal_only = []
    for r in rows:
        if r.task != "solve":
            continue
        g = grades[(r.cell, r.trial_key)]
        if not (r.success is True and g.ok is False):
            continue
        cat, _ = E4.classify(r, g, gt_cache)
        if cat != E4.WRONG_FACTS:
            continue
        steps["solve E4 rows labelled WRONG_FACTS"] += 1
        tool = E4._last_tool_plan(r)
        ans = tuple(norm_action(a) for a in g.plan)
        shape = plan_shape(tool, ans)
        shapes[shape] += 1
        if shape == "tool plan, then extra lines":
            gtxt = goal_text(domains[r.domain]["problems"][r.problem])
            if all(norm_action(x) in gtxt for x in ans[len(tool):]):
                goal_only.append(row_id(r))
        if shape != "same length, some actions differ":
            continue
        steps["... and the answer has as many actions as the tool plan, some different"] += 1
        if len(r.response) > WRONG_FACTS_ANSWER_CAP:
            continue
        steps[f"... and final answer <= {WRONG_FACTS_ANSWER_CAP:,} characters"] += 1
        elig4.append(row_id(r))
    out[4] = {"eligible": elig4, "steps": steps, "shapes": shapes, "goal_only": goal_only}
    return by_id, out


def simulate_plan_vs_cache(rows, rows_c, grades, gt_cache) -> dict:
    """Side check: the plan each with-tools simulate row passed to
    get_state_transition, against the plan in the pinned ground-truth cache.

    The harness builds the simulate prompt from the planner's plan computed
    live at run start; the delivered grader's oracle is the cache. Where every
    row passes one plan that is not the cache's, the run's prompt held a
    different plan than the cache."""
    from collections import defaultdict
    passed: dict[tuple, Counter] = defaultdict(Counter)
    by_prob: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r.task != "simulate":
            continue
        by_prob[(r.domain, r.problem)].append(r)
        for tc in r.tool_calls:
            if (tc.name == "get_state_transition" and isinstance(tc.arguments, dict)
                    and "plan" in tc.arguments):
                passed[(r.domain, r.problem)][plan_actions(tc.arguments["plan"])] += 1
                break
    out = []
    for k in sorted(passed):
        c = passed[k]
        cache = plan_actions(gt_cache[k[0]][k[1]]["plan"])
        top, n = c.most_common(1)[0]
        n_all = sum(c.values())
        if c[cache] == 0 and top != cache and n >= 0.9 * n_all:
            rs = by_prob[k]
            pc = [r for r in rows_c if (r.domain, r.problem) == k]
            out.append({
                "domain": k[0], "problem": k[1], "rows": len(rs), "rows_with_plan": n_all,
                "modal_plan_rows": n, "modal_len": len(top), "cache_len": len(cache),
                "no_room_rows": sum(r.no_room for r in rs),
                "tool_rows_ok_online_wrong_delivered_not_no_room": [
                    row_id(r) for r in rs if r.success is True and not r.no_room
                    and grades[(r.cell, r.trial_key)].ok is False],
                "part_c_ok_online_wrong_delivered": [
                    (row_id(r), answer_actions(r.response) == top) for r in pc
                    if r.success is True and grades[(r.cell, r.trial_key)].ok is False]})
    all_c = [row_id(r) for r in rows_c
             if r.success is True and grades[(r.cell, r.trial_key)].ok is False]
    return {"problems": out, "n_problems": len(passed), "part_c_rows": len(rows_c),
            "part_c_ok_online_wrong_delivered_all": all_c}


def answer_actions(response: str) -> tuple[str, ...]:
    """The non-empty `action` values of a simulate answer, in order, normalised."""
    acts = re.findall(r'"action"\s*:\s*"([^"]+)"', response)
    return plan_actions("\n".join(a for a in acts if a.strip()))


def rebuild_check(r, user: str) -> str | None:
    """None if the rebuilt prompt is consistent with what the model passed to
    the tool; otherwise the reason. Only a plan argument can be compared: the
    domain and problem text come from the fixture files and do not vary."""
    if r.task not in ("simulate", "validate_plan"):
        return None
    m = re.search(r"\nPlan:\n(.*?)(\n\nEnd your response|\Z)", user, re.S)
    if not m:
        return "rebuilt prompt has no Plan block"
    want = plan_actions(m.group(1))
    for tc in r.tool_calls:
        if isinstance(tc.arguments, dict) and "plan" in tc.arguments:
            got = plan_actions(tc.arguments["plan"])
            if got != want:
                return (f"the plan the model passed to "
                        f"`{tc.name}` ({len(got)} actions) is not the plan in the rebuilt "
                        f"prompt ({len(want)} actions, from the ground-truth cache), so the "
                        "run's prompt held a different plan (see side finding 2)")
    return None


# --------------------------------------------------------------- rendering
def prompt_for(r, domains, gt_cache):
    """Rebuild [system, user] with the harness code; also the raw domain/problem text."""
    from tools.delivered_rerun import constants as C
    from pddl_eval.runner import build_jobs, build_messages
    jobs, _ = build_jobs(models=[C.MODEL_IDS[r.model_tag]], tasks=[r.task], domains=domains,
                         ground_truth=gt_cache, num_variants=len(C.VARIANTS),
                         conditions="tools", tool_filter=C.TOOL_FILTER,
                         prompt_style=C.STYLE_A, think_tag=C.THINK)
    hit = [j for j in jobs if (j[2], j[4], j[10], j[6]) == (r.domain, r.problem,
                                                             r.plan_label, r.variant)]
    if len(hit) != 1:
        raise Halt(f"prompt rebuild: {len(hit)} jobs for {row_id(r)}")
    j = hit[0]
    msgs = build_messages(r.task, j[3], j[5], j[6], True, j[8], prompt_style=C.STYLE_A)
    return msgs, j[3], j[5]


def display_user(user: str, dpddl: str, ppddl: str) -> str:
    for text in (dpddl, ppddl):
        if user.count(text) != 1:
            raise Halt("prompt text does not contain the domain/problem exactly once")
    shown = user.replace(dpddl, abridge_lines(dpddl, DOMAIN_HEAD, DOMAIN_TAIL, "the domain"))
    shown = shown.replace(ppddl, abridge_lines(ppddl, PROBLEM_HEAD, PROBLEM_TAIL, "the problem"))
    m = re.search(r"\nPlan:\n(.*?)(\n\nEnd your response|\Z)", shown, re.S)
    if m:
        plan = m.group(1)
        shown = shown.replace(plan, abridge_lines(plan, PLAN_HEAD, PLAN_TAIL, "the plan"), 1)
    return shown


def display_args(args_, dpddl: str, ppddl: str) -> list[str]:
    """One line or block per argument. PDDL equal to the prompt's is not repeated."""
    if not isinstance(args_, dict):
        return [fence(abridge_chars(json.dumps(args_), 400, 100, "the arguments"), "json")]
    out = []
    for k, v in args_.items():
        if isinstance(v, list):
            v = "\n".join(map(str, v))
            kind = "a JSON list, shown one item per line"
        elif not isinstance(v, str):
            out += [f"- `{k}`: `{json.dumps(v)}`"]
            continue
        else:
            kind = "a string"
        match = None
        for label, ref in (("domain", dpddl), ("problem", ppddl)):
            how = same_text(v, ref)
            if how:
                match = (label, how)
                break
        if match:
            label, how = match
            out += [f"- `{k}`: the {label} text of the prompt, {SAME_TEXT_WORDS[how]} "
                    f"({len(v):,} characters)"]
        elif k == "plan":
            out += [f"- `{k}` ({kind}, {len(plan_actions(v))} actions):", "",
                    fence(clip_long_lines(abridge_lines(v, PLAN_HEAD, PLAN_TAIL,
                                                        "the plan"))), ""]
        else:
            out += [f"- `{k}` ({kind}, {len(v):,} characters; not the prompt's text):", "",
                    fence(abridge_lines(v, 10, 3, f"the `{k}` argument")), ""]
    while out and out[-1] == "":
        out.pop()
    return out


def excerpt(n: int, r, grades, gt_cache, domains, results: Path, lines_cache: dict,
            extra: list[str], windows: dict | None = None) -> list[str]:
    from tools.delivered_rerun import constants as C
    from tools.delivered_rerun import e4 as E4
    g = grades[(r.cell, r.trial_key)]
    cell_dir = results / "delivered-rerun" / r.cell
    if r.cell not in lines_cache:
        lines_cache[r.cell] = line_index(cell_dir)
    key = stored_key(r)
    line = lines_cache[r.cell].get(tuple(key))
    if line is None:
        raise Halt(f"no line for {key}")
    msgs, dpddl, ppddl = prompt_for(r, domains, gt_cache)
    mid = C.MODEL_IDS[r.model_tag]
    t = r.tokens
    e4 = ""
    if r.success is True and g.ok is False:
        cat, sub = E4.classify(r, g, gt_cache)
        e4 = f"{cat} ({sub})"
    L = [f"## Example {n}. {POOL_TITLES[n]}", ""]
    L += ["| field | value |", "|---|---|",
          f"| served model | `{mid}`: {BUILDS[mid]} |",
          f"| serving | vLLM {VLLM}, temperature 0.0, context window {C.CONTEXT_WINDOW:,} "
          f"tokens, thinking off, all tools visible, system prompt style `{C.STYLE_A}` |",
          f"| cell file | `results/delivered-rerun/{r.cell}/trials.jsonl`, line {line} |",
          f"| trial key (as stored) | `{json.dumps(key)}` |",
          f"| task / domain / problem / plan / wording | {r.task} / {r.domain} / {r.problem} / "
          f"{r.plan_label or '-'} / v{r.variant} ({r.arm} arm) |",
          f"| stored grade (tool-verified) | success={r.success}, failure_reason="
          f"`{r.failure_reason}` |",
          f"| delivered grade (frozen grader) | ok={g.ok}, reason=`{g.reason}`"
          + (f", plan extracted by `{g.extraction}`" if g.extraction else "") + " |",
          *([f"| E4 label (frozen e4.classify) | {e4} |"] if e4 else []),
          f"| tokens | prompt {t.prompt:,} (summed over turns), completion {t.completion:,}, "
          f"turns {t.turns}, no-room turns {t.ctx_no_room_turns}, done_reason "
          f"`{r.done_reason}` |", ""]
    L += extra
    L += ["**System prompt** (rebuilt with `pddl_eval.runner.build_messages`):", "",
          fence(msgs[0]["content"]), "",
          "**User prompt** (rebuilt the same way; long PDDL abridged, elisions marked):", "",
          fence(display_user(msgs[1]["content"], dpddl, ppddl)), ""]
    if r.tool_calls:
        L += ["The model's intermediate assistant text is not stored; the rows keep each tool "
              "call's name, arguments and result, and the final answer.", ""]
    windows = windows or {}
    for i, tc in enumerate(r.tool_calls, 1):
        if i in windows:
            res = keep_windows(tc.result.splitlines(), windows[i], "the tool result")
        else:
            res = abridge_lines(tc.result, RESULT_HEAD, RESULT_TAIL, "the tool result")
        res = clip_long_lines(res)
        L += [f"**Tool call {i}: `{tc.name}`**, arguments:", ""]
        L += display_args(tc.arguments, dpddl, ppddl)
        L += ["", f"**Tool result {i}** ({len(tc.result):,} characters, "
              f"{len(tc.result.splitlines()):,} lines"
              + ("" if res == tc.result else "; abridged") + "):", "", fence(res, "json"), ""]
    if r.response:
        if "answer" in windows:
            ans = keep_windows(r.response.splitlines(), windows["answer"], "the answer")
        else:
            ans = abridge_lines(r.response, ANSWER_HEAD, ANSWER_TAIL, "the answer")
        L += [f"**Final answer** (verbatim, {len(r.response):,} characters"
              + (", abridged" if ans != r.response else "")
              + ("; it starts with the leaked channel marker `<|channel>thought` / "
                 "`<channel|>` that the grader strips once" if r.response.startswith(
                     C.LEAKED_PREFIX) else "") + "):", "", fence(ans), ""]
    else:
        L += ["**Final answer:** empty. The last turn was never generated: the server "
              "refused it because the prompt (system, user, the tool call and its result) "
              f"did not fit the {C.CONTEXT_WINDOW:,}-token window (`ctx_no_room_turns` = "
              f"{t.ctx_no_room_turns}).", ""]
    return L


def render(args, rerun_a, rows, grades, gt_cache, domains, by_id, P) -> str:
    from tools.delivered_rerun import e4 as E4
    L = ["# C4: example transcripts from the delivered rerun, drawn by a stated rule", "",
         "Written by `tools/reanalysis/c4_select_transcripts.py` (do not edit by hand; change "
         "the script and rerun it). Plan step C4 (`development/weakness_action_plan.md`). "
         "Descriptive: not a gate and not part of the frozen analysis. Ready for E3 to lift "
         "into an appendix.", "",
         "## How the examples were chosen", "",
         "The rule was fixed before any row was drawn. Two parts of it were set after "
         "looking at the pools as a whole, never at a drawn row: the length caps (after "
         "the spread of answer lengths in each pool) and example 4's same-length filter "
         "(after the shape table below showed that most solve WRONG_FACTS rows are not "
         "copying mistakes). Rule 4b was added after a draw; it says so.", "",
         "1. Each example has an **eligible set**, defined by the filters in the tables below. "
         "Rows come from the three Part A tool cells of the delivered rerun (Gemma 4 26B-A4B, "
         "Qwen3.5-9B, Qwen3.6-35B-A3B; minimal system prompt; plain and steered wordings), "
         "loaded by the frozen loader and graded by the frozen delivered grader. The script "
         "first checks that its grades reproduce the E1 and E4 counts of the frozen readout.",
         f"2. The eligible ids are sorted, then shuffled once with Python's "
         f"`random.Random({SEED} + k)` for example k (seed **{SEED}**). The first id in that "
         "order is drawn.",
         "3. **Length caps** keep an excerpt to about a page: the final answer is at most "
         f"{NOCALL_ANSWER_CAP:,} characters (example 1), {RELAY_ANSWER_CAP:,} (example 2) and "
         f"{WRONG_FACTS_ANSWER_CAP:,} (example 4). Example 3 has no answer to cap; its tool "
         "result is the point, so it is shown abridged.",
         "4. **Reading and redraw.** A person reads each drawn transcript in full. If it does "
         "not show what the example is meant to show (for example the verdict is right but "
         "the reasoning is wrong), the row is recorded below as rejected with the reason, and "
         "the next id in the same shuffled order is taken.",
         "4b. **Prompt-rebuild check** (automatic, run before the reading). For simulate and "
         "validate_plan rows that called a tool with a `plan` argument, the plan the model "
         "passed must be the plan in the rebuilt prompt (actions compared with parentheses, "
         "case and spacing ignored). A row that fails is skipped the same way, because its "
         "prompt cannot be shown as the model saw it. *This check was added after the first "
         "draw for example 3 failed it* (see side finding 2); it changes no eligible set, "
         "only which drawn rows can be shown, and the skipped row is listed with the reason.",
         "5. **Abridging.** Long PDDL, plans and tool output are cut to their first and last "
         f"lines (domain {DOMAIN_HEAD}+{DOMAIN_TAIL}, problem {PROBLEM_HEAD}+{PROBLEM_TAIL}, "
         f"plan {PLAN_HEAD}+{PLAN_TAIL}, tool result {RESULT_HEAD}+{RESULT_TAIL} lines). "
         "In example 4 the answer and the planner result keep instead the lines around the "
         "steps that differ. Every cut is marked in the text as `[... N lines of X elided "
         "...]`. A tool argument that equals the prompt's domain or problem text (byte for "
         "byte, once whitespace is collapsed, or once `;` comment lines are also dropped) is "
         "not repeated; the line says which. A single line longer than 300 characters is "
         "cut in the middle, also marked.",
         "6. **The prompt is not stored** in the rows. It is rebuilt with the harness's own "
         "`build_jobs` and `build_messages` from `domains/` and the pinned ground-truth "
         "cache. The tool schemas the model saw (all tools of `pddl-copilot` at `5e4f9c0`) "
         "are not reproduced.", "",
         "Example 1 draws from the 60 no-call answers that two readers already read in full "
         "(`results/delivered-rerun-secondary/nocall_sample/`, readings in "
         "`development/reference/delivered_rerun_secondary/hand_reads/nocall_readings.json`). "
         "A row is dropped when either reader's note contains one of these words "
         f"(case-insensitive): {', '.join(repr(w) for w in DOUBT_WORDS)}.", ""]

    L += ["## Eligible sets", ""]
    for k in (1, 2, 3, 4):
        L += [f"**Example {k}: {POOL_TITLES[k]}**", "", "| filter | rows |", "|---|---|"]
        L += [f"| {s} | {c:,} |" for s, c in P[k]["steps"].items()]
        L += [""]
        if k == 1:
            L += ["Dropped by a reader note: " + "; ".join(
                f"`{i}` ({w!r})" for i, w in P[1]["dropped_by_note"]) + ".", ""]
        if k == 4:
            sh = P[4]["shapes"]
            L += ["How the delivered plan differs from the tool's plan, over all solve "
                  "WRONG_FACTS rows (descriptive):", "", "| shape | rows |", "|---|---|"]
            L += [f"| {s} | {c} |" for s, c in sorted(sh.items(), key=lambda x: -x[1])]
            L += ["", f"**Side finding 1: goal facts read as plan steps (not a "
                  f"transcription error).** In "
                  f"{len(P[4]['goal_only'])} of the {sh['tool plan, then extra lines']} "
                  "\"tool plan, then extra lines\" rows, every extra line is an atom of the "
                  "problem's goal. The answer repeats the tool's plan action for action and "
                  "then lists the goal's facts, each in parentheses on its own line. The "
                  "delivered grader's line extractor reads those goal facts as more plan "
                  "steps, and the longer plan fails validation. So these rows count as "
                  "delivery failures although the tool's (valid) plan is in the answer "
                  "intact. By model: " + ", ".join(
                      f"{m} {c}" for m, c in sorted(Counter(
                          i.split("|")[0] for i in P[4]["goal_only"]).items()))
                  + ". The frozen grade is not changed here. The rows: "
                  + ", ".join(f"`{i}`" for i in P[4]["goal_only"]) + ".", ""]

    sp = P["sim_plan"]
    L += ["## Side finding 2: the simulate plan in the run is not always the cached plan", "",
          "The harness builds each simulate prompt from the planner's plan, computed live "
          "when the run starts; the delivered grader's oracle is the pinned ground-truth "
          "cache. For each simulate problem, the script compares the plan every with-tools "
          "row passed to `get_state_transition` with the cache's plan (actions compared with "
          "parentheses, case and spacing ignored). It lists the problems where no row passed "
          "the cache's plan and at least 90% of the rows passed one same other plan, so the "
          "run's prompt must have held that other plan. "
          f"{len(sp['problems'])} of {sp['n_problems']} problems:", "",
          "| problem | rows | rows passing a plan | rows passing the modal plan | modal plan "
          "actions | cache plan actions | rows whose final turn had no room |",
          "|---|---|---|---|---|---|---|"]
    L += [f"| {e['domain']} {e['problem']} | {e['rows']} | {e['rows_with_plan']} | "
          f"{e['modal_plan_rows']} | {e['modal_len']} | {e['cache_len']} | "
          f"{e['no_room_rows']} |" for e in sp["problems"]]
    tool_hit = [i for e in sp["problems"]
                for i in e["tool_rows_ok_online_wrong_delivered_not_no_room"]]
    pc_hit = [i for e in sp["problems"] for i in e["part_c_ok_online_wrong_delivered"]]
    L += ["", "On these problems nearly every with-tools row ended with no room for the final "
          "turn. For those rows the delivered grade fails before any trajectory is compared, "
          "so the cache's plan is not used. With-tools rows on these problems that the online "
          f"grade passed, that had room, and that the delivered grade fails: {len(tool_hit)}"
          + (" (" + ", ".join(f"`{i}`" for i in tool_hit) + ")" if tool_hit else "")
          + ". Part C (no tools) rows on these problems that the online grade (live "
          f"ground truth) passed and the delivered grade (cache oracle) fails: {len(pc_hit)}"
          + (" (" + ", ".join(
              f"`{i}`, whose answer's actions are "
              + ("exactly" if same else "not") + " the plan the with-tools rows passed"
              for i, same in pc_hit) + ")" if pc_hit else "") + ". "
          "A row like that simulated the run's plan correctly and is graded against a "
          "different plan. Over all "
          f"{sp['part_c_rows']:,} Part C simulate rows (any problem), the rows the online "
          "grade passes and the delivered grade fails are: "
          + (", ".join(f"`{i}`" for i in sp["part_c_ok_online_wrong_delivered_all"]) or "none")
          + ". The frozen readout is not changed here; this is reported for the main "
          "session to decide on.", ""]

    lines_cache: dict = {}
    for k in (1, 2, 3, 4):
        order = draw_order(P[k]["eligible"], k)
        chosen, skipped = None, []
        for cand in order:
            msgs, _d, _p = prompt_for(by_id[cand], domains, gt_cache)
            why = rebuild_check(by_id[cand], msgs[1]["content"])
            if why:
                skipped.append((cand, "rejected by the prompt-rebuild check: " + why))
                continue
            v = READINGS.get(cand)
            if v and v[0] == "rejected":
                skipped.append((cand, "rejected on reading: " + v[1]))
                continue
            chosen = cand
            break
        L += ["---", ""]
        if chosen is None:
            L += [f"## Example {k}. {POOL_TITLES[k]}", "", "No eligible row left.", ""]
            continue
        r = by_id[chosen]
        extra = [f"Drawn: position {order.index(chosen) + 1} of {len(order)} in the shuffled "
                 f"order (seed {SEED} + {k}). Trial id `{chosen}`.", ""]
        if skipped:
            extra += ["Skipped before this draw (redraw rule):", ""]
            extra += [f"- position {order.index(i) + 1}, `{i}`: {why}" for i, why in skipped]
            extra += [""]
        windows = None
        if k == 1:
            rd = P[1]["readings"][chosen]
            extra += [f"Reader A, method: \"{rd['A']['method']}\". Reader B, method: "
                      f"\"{rd['B']['method']}\". Both: verdict {rd['A']['verdict']}, right.", ""]
        if k == 4:
            g = grades[(r.cell, r.trial_key)]
            tool = E4._last_tool_plan(r)
            ans = tuple(norm_action(a) for a in g.plan)
            diffs = [(i + 1, a, b) for i, (a, b) in enumerate(zip(tool, ans)) if a != b]
            extra += [f"The tool's plan and the delivered plan both have {len(tool)} actions; "
                      f"they differ at {len(diffs)} position(s):", "",
                      "| step | tool's plan | delivered answer |", "|---|---|---|"]
            extra += [f"| {i} | `{a}` | `{b}` |" for i, a, b in diffs]
            rd = run_diffs(tool, ans)
            extra += ["", "Read as runs of one repeated action, the two plans differ only "
                      "here:", "", "| action | tool's plan: run length (from step) | "
                      "delivered answer: run length (from step) |", "|---|---|---|"]
            extra += [f"| `{(d['tool'] or d['answer'])[0]}` | "
                      + (f"{d['tool'][1]} (step {d['tool'][2]})" if d["tool"] else "-")
                      + " | " + (f"{d['answer'][1]} (step {d['answer'][2]})"
                                 if d["answer"] else "-") + " |" for d in rd]
            extra += [""]
            lo = min(min(x[2] for x in (d["tool"], d["answer"]) if x) for d in rd)
            hi = max(max(x[2] + x[1] - 1 for x in (d["tool"], d["answer"]) if x) for d in rd)
            windows = diff_windows(r, lo, hi, len(tool))
        L += excerpt(k, r, grades, gt_cache, domains, args.results, lines_cache, extra,
                     windows)
        v = READINGS.get(chosen)
        L += ["**Reading.** " + (v[1] if v else "PENDING: not yet read."), ""]
    L += ["---", "", "## Notes for E3", "",
          "- **Captions must name the served build.** Gemma and Qwen3.6 were served as "
          "community AWQ 4-bit quantisations (`cyankiwi/...`), not the official weights; "
          "Qwen3.5-9B is the official release. Each excerpt's table says which.",
          "- **Example 4 pairs with the frontier passage** on transcription errors "
          "(`paper/main.tex`, subsection \"The Delivery Gap\"). Side finding 1 matters "
          "there: in this rerun, most solve rows the frozen E4 labels WRONG_FACTS are not "
          "copying mistakes but goal facts read as plan steps. Only the same-length shape "
          "(example 4's pool) is a transcription error by construction. Before the paper "
          "counts frontier failures as transcription errors, check that none of them is "
          "this extractor case: a quick look outside this script found one Haiku "
          "with-tools solve answer (depot p02) that repeats the tool's plan and then lists "
          "two goal facts. Whether the frontier grading counted that row among Haiku's "
          "\"three transcription errors\" was not checked.",
          "- **Example 3's first draw was skipped** because its prompt cannot be rebuilt "
          "from the cache (side finding 2). The shown row's plan passed the check.",
          "- The intermediate assistant turns (the text that carried each tool call) are not "
          "stored, so an excerpt shows the tool calls by name and arguments only.", ""]
    return "\n".join(L).rstrip() + "\n"


def diff_windows(r, first: int, last: int, n_actions: int, before: int = 2,
                 after: int = 2) -> dict:
    """Line ranges that show steps first..last (1-based) in the answer and in
    the last planner result, plus the first and last few lines of each."""
    from tools.delivered_rerun import e4 as E4
    out: dict = {}
    lines = r.response.splitlines()
    idx = [j for j, ln in enumerate(lines) if ln.strip().startswith("(")]
    if len(idx) == n_actions:
        out["answer"] = [(0, 3), (idx[first - 1] - before, idx[last - 1] + after),
                         (len(lines) - 3, len(lines) - 1)]
    for i in range(len(r.tool_calls), 0, -1):
        tc = r.tool_calls[i - 1]
        if tc.name in E4.PLANNERS:
            res = tc.result.splitlines()
            ridx = [j for j, ln in enumerate(res) if ln.strip().startswith('"(')]
            if len(ridx) == n_actions:
                out[i] = [(0, 3), (ridx[first - 1] - before, ridx[last - 1] + after),
                          (len(res) - 4, len(res) - 1)]
            break
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, required=True,
                    help="the results/ folder (read only)")
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--readout-json", type=Path,
                    default=REPO / "development/reference/delivered_rerun_readout.json")
    ap.add_argument("--nocall-readings", type=Path, default=REPO / (
        "development/reference/delivered_rerun_secondary/hand_reads/nocall_readings.json"))
    ap.add_argument("--out", type=Path, default=REPO / "development/draft_C4_transcripts.md")
    args = ap.parse_args(argv)
    try:
        from pddl_eval.domains import load_domains
        _design, rerun_a, rows, rows_c, grades, gt_cache, _readout = load(args)
        domains = load_domains(args.domains_dir)
        by_id, P = pools(args, rerun_a, rows, grades, gt_cache, domains)
        P["sim_plan"] = simulate_plan_vs_cache(rows, rows_c, grades, gt_cache)
        md = render(args, rerun_a, rows, grades, gt_cache, domains, by_id, P)
    except Halt as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 2
    if args.out.resolve().is_relative_to(args.results.resolve()):
        print("HALT: --out is inside results/ (read only)", file=sys.stderr)
        return 2
    args.out.write_text(md)
    for k in (1, 2, 3, 4):
        print(f"example {k}: {len(P[k]['eligible'])} eligible; order head "
              f"{draw_order(P[k]['eligible'], k)[:3]}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
