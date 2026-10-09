#!/usr/bin/env python3
"""Q1 - classify the residual failures of the 64K frontier budget probe.

Reads (never writes) the probe corpus and its e2e overlay:
  results/{sonnet,haiku}-frontier/sweep5v2-with-tools-budget64k/trials.jsonl
  results/derived/e2e_overlay/{sonnet,haiku}-frontier/sweep5v2-with-tools-budget64k.e2e.jsonl
  results/derived/gt_cache.json   (the oracle trajectories)

Step 1 reproduces the frozen delivered counts (70/100 Sonnet, 65/100 Haiku;
no-tools 44/100 and 58/100) from the overlay field `e2e_strict`.
Step 2 puts every with-tools row that is not `e2e_strict == True` into exactly
one category. The decision order is fixed (first match wins):

  NO_FINAL_ANSWER        the final message is empty
  TOOL_INPUT_ERROR       the tool's own trajectory is not the oracle's (the
                         model changed the plan when it called the tool)
  SUMMARY_ONLY           prose / change-list; a state is written out for
                         fewer than half of the oracle's steps and nothing
                         is marked as skipped
  ABRIDGED               the trajectory is restated but explicitly shortened:
                         whole steps are skipped, a state list is replaced by
                         a placeholder such as "... same as step 0 ...", or
                         each step lists only what changed
  WRONG_WRAPPER          every step has a written-out state, but not as one
                         JSON value (markdown tables, plain code blocks,
                         JSON-lines). A loose reader then checks the content;
                         the result is the `content` column
  NUMERIC_OMITTED        gradeable JSON, every step, actions and boolean
                         facts all equal to the oracle, every numeric value
                         given is right, but some numeric fluents are left out
  WRONG_FACTS            gradeable JSON, every step, but some boolean facts
                         differ from the tool's own output

The loose reader (`loose_steps`) is a diagnostic only. It is not a grader and
its output must never be quoted as a delivered rate.

Usage:  python3 tools/reanalysis/q1_budget_probe_residual.py [--examples] [--rows]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

from transcripts_common import OVERLAY, RESULTS, clip, load_overlay, load_trials, pct

from pddl_eval.scoring import (  # noqa: E402
    _canon_atom,
    _normalize_trajectory,
    _safe_json_loads,
)
from tools.e2e_regrade import (  # noqa: E402
    _FENCED_BLOCK_RE,
    oracle_canon_for,
    simulate_candidates,
)

TIERS = {"sonnet": "claude-sonnet-4-6", "haiku": "claude-haiku-4-5"}
WT_CELL = "sweep5v2-with-tools-budget64k"
NT_CELL = "sweep5v2-budget64k"
BUDGET = 64_000
FROZEN = {"sonnet": (70, 44), "haiku": (65, 58)}       # NUMBERS.md row "frontier budget probe"

CATS = ("NO_FINAL_ANSWER", "TOOL_INPUT_ERROR", "SUMMARY_ONLY", "ABRIDGED",
        "WRONG_WRAPPER", "NUMERIC_OMITTED", "WRONG_FACTS")

_PLACEHOLDER_RE = re.compile(r"\.\.\.|…|\bsame\b|\bunchanged\b|\ball other\b|\ball static\b",
                             re.IGNORECASE)
_SEXP_RE = re.compile(r"\(([a-z][a-z0-9_\-]*(?:\s+[a-z0-9_\-]+)*)\)", re.IGNORECASE)
_NUM_RE = re.compile(
    r"`?([a-z][a-z0-9_\-]*(?:\([^()=]*\))?)`?\s*[=:]\s*\**(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_STEP_HEAD_RE = re.compile(r"^\s*#{1,6}\s*Step\s+(\d+)\b(.*)$", re.IGNORECASE)
_NOT_ATOMS = {"none", "initial", "empty", "initial state"}


def _atoms(text: str) -> list[str]:
    """Canonical `(name arg ...)` atoms in a line; '(none)' etc. are dropped."""
    out = []
    for m in _SEXP_RE.finditer(text):
        a = _canon_atom(m.group(0))
        if a not in _NOT_ATOMS:
            out.append(a)
    return out


# --------------------------------------------------------------------------
# Loose reader: per-step state from non-JSON answers (diagnostic only)
# --------------------------------------------------------------------------
def _loose_json_lines(resp: str) -> list[dict] | None:
    """Several JSON step objects in one fenced block, one per line."""
    steps: list[dict] = []
    for block in _FENCED_BLOCK_RE.findall(resp):
        for ln in block.splitlines():
            ln = ln.strip().rstrip(",")
            if not ln.startswith("{"):
                continue
            obj = _safe_json_loads(ln)
            if isinstance(obj, dict) and "step" in obj:
                steps.append(obj)
    if not steps:
        return None
    return _normalize_trajectory(steps)


def _loose_wide_table(resp: str, oracle: list[dict]) -> list[dict] | None:
    """One markdown table: | Step | Action | fluent | fluent | ... |.

    Counts as a state table only when every column after Action is a numeric
    fluent of the oracle or a column of boolean facts. A table whose third
    column is free text ("Key State Changes", "Effect") is a change-list, not
    a restated state, and is rejected here.
    """
    known = set(oracle[0]["numeric"])
    lines = resp.splitlines()
    for i, ln in enumerate(lines):
        cells = [c.strip().strip("`*") for c in ln.strip().strip("|").split("|")]
        if not (len(cells) >= 3 and cells[0].lower() == "step"
                and cells[1].lower() == "action"):
            continue
        cols = []
        for c in cells[2:]:
            if _canon_atom(c) in known:
                cols.append(("num", _canon_atom(c)))
            elif c.lower().startswith("boolean"):
                cols.append(("bool", None))
            else:
                cols = None
                break
        if cols:
            header, start = cells, i
            break
    else:
        return None
    out: list[dict] = []
    for ln in lines[start + 2:]:
        if not ln.strip().startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) != len(header):
            return None
        step_txt = cells[0].strip("*` ")
        if not step_txt.isdigit():
            return None                      # a "2-55" range row: not per-step
        acts = _atoms(cells[1])
        numeric: dict[str, float] = {}
        boolean: list[str] = []
        for (kind, name), val in zip(cols, cells[2:]):
            if kind == "bool":
                boolean += _atoms(val)
                continue
            try:
                numeric[name] = float(val.strip("*` "))
            except ValueError:
                return None
        out.append({"step": int(step_txt), "action": acts[0] if acts else "",
                    "boolean": sorted(boolean), "numeric": numeric})
    return out or None


def _loose_step_sections(resp: str) -> list[dict] | None:
    """`### Step N` sections; state = the atoms inside that section's table
    rows and fenced blocks. Prose lines between them are ignored."""
    lines = resp.splitlines()
    heads = [(i, int(m.group(1)), m.group(2)) for i, ln in enumerate(lines)
             if (m := _STEP_HEAD_RE.match(ln))]
    if not heads:
        return None
    out: list[dict] = []
    for idx, (start, stepno, tail) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        # a later non-step heading (### Summary ...) closes the last section
        for j in range(start + 1, end):
            if re.match(r"^\s*#{1,6}\s+(?!Step\b)", lines[j], re.IGNORECASE):
                end = j
                break
        acts = _atoms(tail)
        action = acts[0] if acts else ""
        boolean: set[str] = set()
        numeric: dict[str, float] = {}
        in_fence = False
        for ln in lines[start + 1:end]:
            s = ln.strip()
            if s.startswith("```"):
                in_fence = not in_fence
                continue
            low = s.lower()
            if low.startswith(("**action", "action")):
                acts = _atoms(s)
                if acts and not action:
                    action = acts[0]
                continue
            is_state_line = in_fence or s.startswith("|") or "numeric" in low[:24]
            if not is_state_line:
                continue
            is_numeric_line = "numeric" in low[:24]
            if not is_numeric_line:
                boolean.update(_atoms(s))
            for name, val in _NUM_RE.findall(s):
                if name.lower() in ("boolean", "numeric", "step", "state"):
                    continue
                numeric[_canon_atom(name)] = float(val)
        out.append({"step": stepno, "action": action,
                    "boolean": sorted(boolean), "numeric": numeric})
    return out


def loose_steps(resp: str, oracle: list[dict]) -> tuple[list[dict] | None, str]:
    for fn, name in ((_loose_json_lines, "json-lines in one block"),
                     (lambda r: _loose_wide_table(r, oracle), "one wide table"),
                     (_loose_step_sections, "per-step sections")):
        steps = fn(resp)
        if steps:
            return steps, name
    return None, "none"


# --------------------------------------------------------------------------
# Comparison against the oracle
# --------------------------------------------------------------------------
def compare(model: list[dict], oracle: list[dict]) -> dict:
    n = min(len(model), len(oracle))
    d = dict(steps_model=len(model), steps_oracle=len(oracle), action_bad=0,
             bool_bad_steps=0, bool_missing=0, bool_extra=0, placeholder_atoms=0,
             num_missing_keys=set(), num_wrong=0, num_extra_keys=set())
    for i in range(n):
        m, o = model[i], oracle[i]
        if m["action"] != o["action"]:
            d["action_bad"] += 1
        mb, ob = set(m["boolean"]), set(o["boolean"])
        ph = {a for a in mb if _PLACEHOLDER_RE.search(a)}
        d["placeholder_atoms"] += len(ph)
        if mb != ob:
            d["bool_bad_steps"] += 1
        d["bool_missing"] += len(ob - mb)
        d["bool_extra"] += len(mb - ob - ph)
        for k, v in o["numeric"].items():
            if k not in m["numeric"]:
                d["num_missing_keys"].add(k)
            elif m["numeric"][k] != v:
                d["num_wrong"] += 1
        d["num_extra_keys"] |= set(m["numeric"]) - set(o["numeric"])
    return d


def content_label(d: dict) -> str:
    if d["steps_model"] != d["steps_oracle"]:
        return f"steps {d['steps_model']}/{d['steps_oracle']}"
    wrong = d["action_bad"] or d["bool_bad_steps"] or d["num_wrong"] or d["num_extra_keys"]
    if not wrong and not d["num_missing_keys"]:
        return "content equals oracle"
    if not wrong:
        return "content equals oracle except omitted numeric fluents"
    return "content differs"


def tool_trajectory(row: dict):
    """Normalised trajectory of the last non-error get_state_transition result."""
    best = None
    for tc in row.get("tool_calls") or []:
        if tc.get("name") != "get_state_transition":
            continue
        p = _safe_json_loads(tc.get("result"))
        if isinstance(p, dict) and not p.get("error"):
            t = _normalize_trajectory(p.get("trajectory"))
            if t is not None:
                best = (t, p)
    return best


def false_in_tool(model: list[dict], tool_raw: dict) -> tuple[int, int]:
    """(#extra facts the tool reported as false at that step, #extra facts)."""
    traj = tool_raw.get("trajectory") or []
    tool_canon = _normalize_trajectory(traj) or []
    hit = tot = 0
    for i in range(min(len(model), len(traj))):
        falses = {_canon_atom(k) for k, v in (traj[i].get("boolean_fluents") or {}).items()
                  if not v}
        for a in set(model[i]["boolean"]) - set(tool_canon[i]["boolean"]):
            tot += 1
            hit += a in falses
    return hit, tot


def classify(row: dict, ov: dict, oracle: list[dict]) -> dict:
    resp = row.get("response") or ""
    info = dict(cat=None, sub="", content="", detail="")
    tool = tool_trajectory(row)
    tool_ok = tool is not None and tool[0] == oracle

    if not resp.strip():
        info["cat"] = "NO_FINAL_ANSWER"
        err = row.get("error") or ""
        if "prompt is too long" in err:
            info["sub"] = "context window overflow after repeated tool calls"
        elif row.get("failure_reason") == "loop_exhausted":
            info["sub"] = "tool-loop limit (10 turns) reached, never answered"
        else:
            info["sub"] = f"done_reason={row.get('done_reason')}"
        info["detail"] = f"turns={row['tokens'].get('turns')} error={clip(err, 90)!r}"
        return info

    if not tool_ok:
        info["cat"] = "TOOL_INPUT_ERROR"
        n_tool = len(tool[0]) if tool else 0
        info["sub"] = "plan sent to the tool is not the plan in the prompt"
        info["detail"] = (f"tool trajectory {n_tool} steps vs oracle {len(oracle)}; "
                          f"the answer itself is a {len(resp)}-char summary")
        return info

    cands = [(s, m) for s, m in simulate_candidates(resp)
             if _normalize_trajectory(s) is not None]
    if cands:                                     # the overlay's trajectory_mismatch rows
        steps, mode = max(cands, key=lambda g: len(g[0]))
        model = _normalize_trajectory(steps)
        d = compare(model, oracle)
        info["detail"] = (f"json {mode}; steps {d['steps_model']}/{d['steps_oracle']}; "
                          f"bad-fact steps {d['bool_bad_steps']}; "
                          f"numeric keys missing {len(d['num_missing_keys'])}, "
                          f"wrong values {d['num_wrong']}")
        if d["steps_model"] < d["steps_oracle"]:
            info["cat"], info["sub"] = "ABRIDGED", "steps skipped"
            return info
        if d["placeholder_atoms"]:
            info["cat"], info["sub"] = "ABRIDGED", "state replaced by a placeholder"
            return info
        clean = not (d["action_bad"] or d["bool_bad_steps"] or d["num_wrong"]
                     or d["num_extra_keys"])
        if clean and d["num_missing_keys"]:
            static = {k for k in oracle[0]["numeric"]
                      if all(st["numeric"].get(k) == oracle[0]["numeric"][k] for st in oracle)}
            miss = d["num_missing_keys"]
            info["cat"] = "NUMERIC_OMITTED"
            info["sub"] = (f"{len(miss)} numeric fluents left out "
                           f"({len(miss & static)} of them never change)")
            return info
        info["cat"] = "WRONG_FACTS"
        hit, tot = false_in_tool(model, tool[1])
        info["sub"] = (f"{d['bool_extra']} extra / {d['bool_missing']} missing facts in "
                       f"{d['bool_bad_steps']} of {d['steps_oracle']} steps; "
                       f"{hit} of {tot} extra facts are ones the tool marked false")
        return info

    # No gradeable JSON (the overlay's format_parse_fail rows).
    blocks = _FENCED_BLOCK_RE.findall(resp)
    json_like = [b for b in blocks if b.lstrip().startswith(("[", "{")) and '"step"' in b]
    if json_like and any(_PLACEHOLDER_RE.search(b) for b in json_like) \
            and _loose_json_lines(resp) is None:
        n_steps = max(len(re.findall(r'"step"\s*:', b)) for b in json_like)
        info["cat"] = "ABRIDGED"
        info["sub"] = "steps skipped (the '...' also breaks the JSON)"
        info["detail"] = f"json block with '...'; steps written {n_steps}/{len(oracle)}"
        return info

    steps, how = loose_steps(resp, oracle)
    n_written = len(steps) if steps else 0
    if steps and n_written * 2 >= len(oracle):
        d = compare(steps, oracle)
        # A step section that lists only what changed ("State adds: ...",
        # "same as step 0, except ...") is a shortened answer, not a full
        # state in another wrapper: the median step carries under half of
        # the oracle's facts.
        ratios = sorted(
            (len(m["boolean"]) + len(m["numeric"]))
            / max(1, len(o["boolean"]) + len(o["numeric"]))
            for m, o in zip(steps, oracle))
        if content_label(d) == "content differs" and ratios[len(ratios) // 2] < 0.5:
            info["cat"] = "ABRIDGED"
            info["sub"] = "states given only as changes from the previous step"
            info["detail"] = (f"non-JSON {how}; median step lists "
                              f"{100 * ratios[len(ratios) // 2]:.0f}% of the oracle's facts")
            return info
        info["cat"], info["sub"] = "WRONG_WRAPPER", how
        info["content"] = content_label(d)
        info["detail"] = (f"loose read: steps {d['steps_model']}/{d['steps_oracle']}; "
                          f"action diffs {d['action_bad']}; bad-fact steps "
                          f"{d['bool_bad_steps']}; numeric keys missing "
                          f"{len(d['num_missing_keys'])}, wrong values {d['num_wrong']}")
        return info
    info["cat"] = "SUMMARY_ONLY"
    info["sub"] = "prose or change-list, no per-step states"
    info["detail"] = f"{len(resp)} chars for a {len(oracle)}-step oracle"
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", action="store_true", help="print one line per residual row")
    ap.add_argument("--examples", action="store_true", help="print verbatim examples")
    ap.add_argument("--n-examples", type=int, default=3)
    args = ap.parse_args()
    gt = json.loads((RESULTS / "derived" / "gt_cache.json").read_text())

    print("== Step 1: reproduce the frozen probe numbers (overlay field e2e_strict) ==")
    all_rows: dict[str, list] = {}
    for tier in TIERS:
        wt_raw = load_trials(RESULTS / f"{tier}-frontier" / WT_CELL / "trials.jsonl")
        wt_ov = load_overlay(OVERLAY / f"{tier}-frontier" / f"{WT_CELL}.e2e.jsonl")
        nt_ov = load_overlay(OVERLAY / f"{tier}-frontier" / f"{NT_CELL}.e2e.jsonl")
        nt_raw = load_trials(RESULTS / f"{tier}-frontier" / NT_CELL / "trials.jsonl")
        assert set(wt_raw) == set(wt_ov), "overlay/raw key mismatch"
        assert all(o["task"] == "simulate" and o["prompt_variant"] == 11 and o["with_tools"]
                   for o in wt_ov.values())
        assert not any(o["e2e_strict"] == "indeterminate" for o in wt_ov.values())
        wt_ok = sum(o["e2e_strict"] is True for o in wt_ov.values())
        nt_ok = sum(o["e2e_strict"] is True for o in nt_ov.values())
        at_cap = sum(1 for r in wt_raw.values()
                     if (r["tokens"].get("completion_final") or 0) >= BUDGET)
        nt_cap = sum(1 for r in nt_raw.values()
                     if (r["tokens"].get("completion_final")
                         or r["tokens"].get("completion") or 0) >= BUDGET)
        tv = sum(bool(o["tool_verified"]) for o in wt_ov.values())
        print(f"{tier:6s} with-tools delivered {pct(wt_ok, len(wt_ov))}   "
              f"no-tools {pct(nt_ok, len(nt_ov))}")
        print(f"       tool-verified {tv}/{len(wt_ov)}; final turns at the {BUDGET} cap: "
              f"with-tools {at_cap}, no-tools {nt_cap}; "
              f"reasons {dict(Counter(o['e2e_reason'] for o in wt_ov.values()))}")
        ok = (wt_ok, nt_ok) == FROZEN[tier]
        print(f"       matches NUMBERS.md ({FROZEN[tier][0]}/{FROZEN[tier][1]}): {ok}")
        assert ok, "frozen probe numbers did not reproduce"
        rows = []
        for key, o in wt_ov.items():
            if o["e2e_strict"] is True:
                continue
            r = wt_raw[key]
            oracle = oracle_canon_for(gt, r)
            info = classify(r, o, oracle)
            rows.append((r, o, info, oracle))
        all_rows[tier] = rows

    print("\n== Step 2: residual failures by category (task = simulate, n = 100 per model) ==")
    print(f"{'category':18s} " + " ".join(f"{t:>34s}" for t in TIERS) + f" {'both':>34s}")
    tot = {t: Counter(i["cat"] for _, _, i, _ in rows) for t, rows in all_rows.items()}
    for cat in CATS:
        both = sum(tot[t][cat] for t in TIERS)
        print(f"{cat:18s} " + " ".join(f"{pct(tot[t][cat], 100):>34s}" for t in TIERS)
              + f" {pct(both, 200):>34s}")
    print(f"{'all residual':18s} "
          + " ".join(f"{pct(len(all_rows[t]), 100):>34s}" for t in TIERS)
          + f" {pct(sum(len(v) for v in all_rows.values()), 200):>34s}")
    for t in TIERS:
        assert sum(tot[t].values()) == len(all_rows[t])
        assert set(tot[t]) <= set(CATS)

    print("\n-- category x overlay reason --")
    for t, rows in all_rows.items():
        x = Counter((i["cat"], o["e2e_reason"]) for _, o, i, _ in rows)
        for (cat, reason), n in sorted(x.items()):
            print(f"  {t:6s} {cat:18s} {reason:22s} {n}")

    print("\n-- sub-types --")
    for t, rows in all_rows.items():
        x: dict = defaultdict(Counter)
        for _, _, i, _ in rows:
            if i["cat"] == "ABRIDGED":
                x[i["cat"]][i["sub"]] += 1
            elif i["cat"] == "WRONG_WRAPPER":
                x[i["cat"]][f"{i['sub']} | {i['content']}"] += 1
            elif i["cat"] == "NO_FINAL_ANSWER":
                x[i["cat"]][i["sub"]] += 1
        for cat, c in x.items():
            for sub, n in c.most_common():
                print(f"  {t:6s} {cat:18s} {n:2d}  {sub}")

    print("\n-- how the residual splits: could a more tolerant reader have passed it? --")
    for t, rows in all_rows.items():
        c = Counter()
        for _, _, i, _ in rows:
            if i["cat"] == "WRONG_WRAPPER" and i["content"] == "content equals oracle":
                c["complete and correct content, only the wrapper is wrong"] += 1
            elif i["cat"] in ("NUMERIC_OMITTED",) or (
                    i["cat"] == "WRONG_WRAPPER" and "omitted numeric" in i["content"]):
                c["correct but leaves out numeric fluents"] += 1
            elif i["cat"] in ("ABRIDGED", "SUMMARY_ONLY"):
                c["model chose not to restate the whole trajectory"] += 1
            elif i["cat"] == "WRONG_FACTS" or i["cat"] == "WRONG_WRAPPER":
                c["restated in full but with wrong facts"] += 1
            else:
                c["no usable tool result or no answer"] += 1
        for k, n in c.most_common():
            print(f"  {t:6s} {pct(n, 100):>30s}  {k}")

    if args.rows:
        print("\n-- every residual row --")
        for t, rows in all_rows.items():
            for r, o, i, oracle in rows:
                print(f"{t:6s} {r['domain_name']:19s} {r['problem_name']:4s} "
                      f"{o['e2e_reason']:20s} {i['cat']:16s} | {i['sub']} | {i['content']} "
                      f"| {i['detail']} | answer {len(r['response'] or '')} chars, "
                      f"final turn {r['tokens'].get('completion_final')} tok")

    if args.examples:
        print("\n== Verbatim examples ==")
        for cat in CATS:
            for t, rows in all_rows.items():
                shown = 0
                for r, o, i, oracle in rows:
                    if i["cat"] != cat or shown >= args.n_examples:
                        continue
                    shown += 1
                    resp = r["response"] or ""
                    print(f"\n### {cat} | {t} | {r['domain_name']}/{r['problem_name']} "
                          f"| {i['sub']} | {i['content']}")
                    print(f"[{i['detail']}]")
                    print("--- first 600 chars ---")
                    print(clip(resp, 600) if resp else f"(empty) error={r.get('error')!r}")
                    m = _PLACEHOLDER_RE.search(resp[600:]) if cat == "ABRIDGED" else None
                    if m:
                        a = 600 + m.start()
                        print("--- around the first placeholder ---")
                        print(resp[max(0, a - 250):a + 250])


if __name__ == "__main__":
    main()
