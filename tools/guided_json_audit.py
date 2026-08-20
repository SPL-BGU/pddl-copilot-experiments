#!/usr/bin/env python3
"""ISS-024(b) `guided_json` audit, v3 — mechanism + affected-row fraction.

A working vLLM `guided_json` constraint makes schema-violating output
IMPOSSIBLE: the decoder cannot emit a token that leaves the grammar. So any
stored no-tools response that is (a) not JSON, or (b) JSON that violates
`TASK_SCHEMAS[task]`, is direct proof the constraint did not bind on that row.
Conformance is checked against `TASK_SCHEMAS[task]` itself — the exact object
`vllm_client.chat` puts in `extra_body["guided_json"]` — not against the
pydantic model, which coerces types the JSON-Schema grammar would reject. The
pydantic verdict is computed alongside purely as a cross-check and any
disagreement is printed.

TWO DENOMINATORS, both reported, because they answer different questions:

  proof denominator   every row on which non-binding is PROVABLE. A row whose
                      first non-space character is not `{` proves it even when
                      the text is truncated, because neither generation
                      truncation nor the storage snapshot can change the FIRST
                      character; a bound decoder's first character is always
                      `{`. This is the primary rate.
  complete-rows-only  the strictly conservative denominator: drops every
                      generation-truncated or at-snapshot-cap row regardless of
                      shape. Reported so a reader who declines the
                      first-character argument still gets a number.

Empty responses carry no evidence either way and are excluded from both.

Corpus identity (CLAUDE.md data-rigor rule):
  * `sweep5v2-live` and `sweep6-live` are the canonical corpora. Only these two
    are pooled into a headline figure.
  * `decoupled-rollup` is a CONTROL tree (`RUN_TAG=decoupled-thinkon`, 4-Qwen
    think=on roster, 2-call generation apparatus). It is reported separately and
    never merged into either canonical corpus. It also physically stores its
    matched sweep5v2 baseline as extra cells; those are byte-identical copies of
    canonical cells, so counting the tree whole would double-count them. Cells
    are deduplicated by content fingerprint and every drop is printed.

Snapshot caps are detected PER CELL (`e2e_regrade.detect_cap`), never once per
corpus: `decoupled-rollup` genuinely holds cells written under both caps (500
before 2026-06-25, 16384 after), and one corpus-wide cap silently grades one
group's censored snapshots as determinate.

Read-only. No arguments.
"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import jsonschema  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from pddl_eval import schemas as S  # noqa: E402
from pddl_eval.schemas import TASK_SCHEMAS  # noqa: E402
from e2e_regrade import detect_cap  # noqa: E402  (one definition of the cap rule)

MODELS = {"solve": S.SolveResponse, "validate_domain": S.ValidateResponse,
          "validate_problem": S.ValidateResponse, "validate_plan": S.ValidateResponse,
          "simulate": S.SimulateResponse}

# (label, path, is_canonical). Canonical per CLAUDE.md; the control tree is
# listed last so that on a fingerprint collision the canonical cell is the one
# kept and the control copy is the one dropped.
CORPORA = (("sweep5v2-live", REPO / "results" / "sweep5v2-live", True),
           ("sweep6-live", REPO / "results" / "sweep6-live", True),
           ("decoupled-rollup", REPO / "results" / "decoupled-rollup", False))

VERDICT_TRAILER = "VERDICT:"


def iter_rows(path):
    """Yield (trial_key, result_dict) for every line of a trials.jsonl."""
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = rec.get("key")
            yield (tuple(key) if isinstance(key, list) else key), rec.get("result", rec)


def no_tools_rows(path):
    """Only the no-tools rows that carry evidence (`format` is passed in that
    branch alone), minus infra failures, minus unknown tasks."""
    for key, r in iter_rows(path):
        if r.get("with_tools") is not False or r.get("infra_failure"):
            continue
        if r.get("task") in MODELS:
            yield key, r


def survey(path):
    """Pass 1: response-length histogram (for the cap) + a content fingerprint.

    The fingerprint is a hash of the sorted (trial key -> response) mapping, so
    it is invariant to line order and to drift in fields we do not read, and two
    distinct 4,560-row cells cannot collide by chance.
    """
    lengths = defaultdict(int)
    pairs = []
    for key, r in no_tools_rows(path):
        resp = r.get("response") or ""
        lengths[len(resp)] += 1
        pairs.append(f"{key}\x00{resp}")
    h = hashlib.sha1()
    for p in sorted(pairs):
        h.update(p.encode("utf-8", "replace"))
        h.update(b"\x01")
    return dict(lengths), h.hexdigest(), len(pairs)


def classify(resp, task, truncated, cap):
    """-> empty | not_json_complete | not_json_truncated | censored |
           bad_json | schema_violation | schema_ok

    `at_cap` uses `len(resp) >= cap` (not cap - 1): a stored response of exactly
    cap length is a truncated snapshot with negligible false-positive mass
    (e2e_regrade.KNOWN_CAPS comment). The old `cap - 1` also discarded complete
    responses one character short of the cap.
    """
    r = resp.strip()
    if not r:
        return "empty"
    censored = truncated or len(resp) >= cap
    if not r.startswith("{"):
        # Neither generation truncation nor the storage snapshot can change the
        # FIRST character, so this proves non-binding either way; the two
        # buckets exist only to let the caller pick a denominator.
        return "not_json_truncated" if censored else "not_json_complete"
    if censored:
        return "censored"
    try:
        obj = json.loads(r)
    except json.JSONDecodeError:
        return "bad_json"
    try:
        jsonschema.validate(obj, TASK_SCHEMAS[task])
    except jsonschema.ValidationError:
        return "schema_violation"
    return "schema_ok"


PROOF = ("not_json_complete", "not_json_truncated", "bad_json",
         "schema_violation", "schema_ok")
COMPLETE = ("not_json_complete", "bad_json", "schema_violation", "schema_ok")


def main():
    # ---- Pass 1: inventory, per-cell caps, content dedup ------------------
    cells, seen_fp, dropped, skipped, matched_twins = [], {}, [], [], set()
    for corpus, root, canonical in CORPORA:
        found = sorted(p for p in root.glob("*/trials.jsonl") if "no-tools" in p.parent.name)
        if not found:
            sys.exit(f"FATAL: no no-tools cells under {root} — wrong cwd or a renamed layout?")
        for path in found:
            name = path.parent.name
            lengths, fp, n = survey(path)
            cap = detect_cap(lengths)
            if cap is None:
                skipped.append((corpus, name, max(lengths) if lengths else 0))
                continue
            if fp in seen_fp:
                # The control tree physically stores its matched sweep5v2
                # baseline. Drop the copy, but remember which canonical cell it
                # duplicated: that cell IS the matched baseline, and comparing
                # the control against it is the only roster- and mode-controlled
                # read of the decoupled-budget effect.
                dropped.append((corpus, name, seen_fp[fp], n))
                matched_twins.add(seen_fp[fp])
                continue
            seen_fp[fp] = f"{corpus}/{name}"
            cells.append((corpus, canonical, name, path, cap, n))
    if not cells:
        sys.exit("FATAL: no cells to audit.")

    print(f"cells read: {len(cells)} kept, {len(dropped)} dropped as duplicates, "
          f"{len(skipped)} skipped (no known cap)\n")
    for corpus, name, twin, n in dropped:
        print(f"  DROPPED duplicate  {corpus}/{name}  ({n} rows) == {twin}")
    for corpus, name, mx in skipped:
        print(f"  SKIPPED no-cap     {corpus}/{name}  (max response {mx})")
    if dropped or skipped:
        print()
    for corpus in dict.fromkeys(c for c, *_ in CORPORA):
        caps = sorted({cap for c, _, _, _, cap, _ in cells if c == corpus})
        rows = sum(n for c, _, _, _, _, n in cells if c == corpus)
        print(f"  {corpus:<18} {sum(1 for c, *_ in cells if c == corpus):>2} cells, "
              f"{rows:>6} no-tools rows, per-cell caps {caps}")
    print()

    # ---- Pass 2: classify -------------------------------------------------
    stats = defaultdict(lambda: defaultdict(int))
    shapes = defaultdict(int)
    fpf = defaultdict(int)      # (group, task) -> format_parse_fail rows
    seen = defaultdict(int)     # (group, task) -> all no-tools rows
    pydantic_disagreements = 0
    for corpus, canonical, name, path, cap, _ in cells:
        grp = "canonical" if canonical else "control"
        groups = [corpus]
        if f"{corpus}/{name}" in matched_twins:
            groups.append(f"{corpus} [matched 4-cell subset]")
        for _, r in no_tools_rows(path):
            task, resp = r["task"], (r.get("response") or "")
            c = classify(resp, task, bool(r.get("truncated")), cap)
            stats[(corpus, task)][c] += 1
            stats[(corpus, "ALL")][c] += 1
            for g in groups:
                seen[(g, task)] += 1
                if r.get("failure_reason") == "format_parse_fail":
                    fpf[(g, task)] += 1
            if c in ("not_json_complete", "not_json_truncated") and task.startswith("validate"):
                s = resp.strip()
                shapes[(grp, "validate_*", "bare trailer only"
                        if s.upper().startswith(VERDICT_TRAILER) and len(s) < 32
                        else "trailer present in snapshot" if VERDICT_TRAILER in s.upper()
                        else "no trailer in snapshot")] += 1
            if c in ("schema_violation", "schema_ok"):
                obj = json.loads(resp.strip())
                if c == "schema_violation":
                    if task == "solve" and isinstance(obj.get("plan"), str):
                        shapes[(grp, "solve", "plan is a string, schema wants array")] += 1
                    if task == "simulate" and "trajectory" not in obj:
                        shapes[(grp, "simulate", "bare step, no trajectory wrapper")] += 1
                try:
                    MODELS[task].model_validate(obj)
                    pyd_ok = True
                except ValidationError:
                    pyd_ok = False
                if pyd_ok != (c == "schema_ok"):
                    pydantic_disagreements += 1

    # ---- Report -----------------------------------------------------------
    hdr = (f"{'corpus':<18}{'task':<17}{'proof n':>9}{'conform':>9}"
           f"{'complete n':>12}{'conform':>9}   {'BOUND?':>7}")
    print(hdr)
    print("-" * len(hdr))
    for corpus, task in sorted(stats):
        s = stats[(corpus, task)]
        proof = sum(s[k] for k in PROOF)
        comp = sum(s[k] for k in COMPLETE)
        if not proof:
            continue
        ok = s["schema_ok"]
        print(f"{corpus:<18}{task:<17}{proof:>9}{100*ok/proof:>8.2f}%{comp:>12}"
              f"{(f'{100*ok/comp:.2f}%' if comp else '-'):>9}   "
              f"{'no' if ok / proof < 0.999 else 'YES':>7}")
    print()

    canonical_corpora = {c for c, _, canon in CORPORA if canon}
    pooled = defaultdict(int)
    for (corpus, task), s in sorted(stats.items()):
        if task != "ALL":
            continue
        proof = sum(s[k] for k in PROOF)
        comp = sum(s[k] for k in COMPLETE)
        if not proof:                     # all-empty corpus: nothing to divide by
            print(f"{corpus}: {sum(s.values())} no-tools rows | no provable rows "
                  f"(empty {s['empty']}, censored {s['censored']})")
            continue
        ok = s["schema_ok"]
        rate_c = f"{100*ok/comp:.2f}% of {comp} complete" if comp else "no complete rows"
        tag = "" if corpus in canonical_corpora else "   [control tree, never pooled]"
        print(f"{corpus}: {sum(s.values())} no-tools rows | conformant {ok} "
              f"({100*ok/proof:.2f}% of {proof} provable, {rate_c}) | "
              f"censored {s['censored'] + s['not_json_truncated']} | empty {s['empty']}{tag}")
        if corpus in canonical_corpora:
            for k, v in s.items():
                pooled[k] += v
    p_proof = sum(pooled[k] for k in PROOF)
    p_comp = sum(pooled[k] for k in COMPLETE)
    if p_proof:
        print(f"\nCANONICAL POOLED ({' + '.join(sorted(canonical_corpora))}): "
              f"{sum(pooled.values())} no-tools rows | conformant {pooled['schema_ok']} "
              f"({100*pooled['schema_ok']/p_proof:.2f}% of {p_proof} provable, "
              f"{100*pooled['schema_ok']/p_comp:.2f}% of {p_comp} complete)")

    # Exposure: where the artifact actually changes a grade. The matched subset
    # is the same 4 think=on Qwen cells the control tree re-ran, so control-vs-
    # matched is the only comparison free of roster and reasoning-mode confounds.
    print("\nformat_parse_fail rate (share of all no-tools rows of that task):")
    tasks = ("solve", "simulate", "validate_domain", "validate_problem", "validate_plan")
    print(f"  {'group':<40}" + "".join(f"{t:>18}" for t in tasks))
    for g in dict.fromkeys(g for g, _ in seen):
        cells_line = "".join(
            f"{(f'{100*fpf[(g, t)]/seen[(g, t)]:.1f}%' if seen[(g, t)] else '-'):>18}"
            for t in tasks)
        print(f"  {g:<40}{cells_line}")

    print("\nviolation shapes (n behind each claim):")
    for (grp, task, shape), n in sorted(shapes.items()):
        print(f"  {grp:<10} {task:<12} {shape:<42} {n:>7}")
    print(f"\njsonschema-vs-pydantic disagreements: {pydantic_disagreements}")


if __name__ == "__main__":
    main()
