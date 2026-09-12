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
import re
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

# The control tree re-ran exactly the 4 think=on Qwen cells of the sweep5v2
# baseline, so the roster- and mode-matched subset must come out at 4 cells.
EXPECTED_MATCHED = 4

# The v11-v13 validate prompts ask for a final `VERDICT: VALID|INVALID` line
# (`prompts.py`). Anchor on that grammar rather than on a bare "VERDICT:"
# substring, which also fires on prose ("my verdict: the domain parses"), and
# rather than on a length cutoff, which mis-bins a bare trailer carrying
# trailing punctuation. The verdict WORD is matched as an optional prefix
# (`VERDICT: INVAL`, `VERDICT: I`, `VERDICT:`) when it runs to the end of the
# text: at a 500-character snapshot the cap routinely lands mid-word, and such
# a row does show the trailer. Measured on the canonical corpora, this grammar
# and the old substring test agree on every one of the 11,157 rows that show a
# trailer, and the anchored bare test agrees with the old `len < 32` rule on
# all 9,814 bare rows: the tightening removes two hazards, not any evidence.
_VERDICT_WORD = r"(?:V(?:A(?:L(?:I(?:D)?)?)?)?|I(?:N(?:V(?:A(?:L(?:I(?:D)?)?)?)?)?)?)"
VERDICT_FULL = re.compile(r"\bVERDICT\s*:\s*(?:VALID|INVALID)\b", re.I)
VERDICT_TAIL = re.compile(rf"\bVERDICT\s*:\s*{_VERDICT_WORD}?\s*\Z", re.I)
VERDICT_BARE = re.compile(rf"\AVERDICT\s*:\s*{_VERDICT_WORD}?\s*[.!]?\s*\Z", re.I)


def trailer_visible(s):
    """Does this snapshot show the `VERDICT:` trailer, whole or cut by the cap?"""
    return bool(VERDICT_FULL.search(s) or VERDICT_TAIL.search(s))


TORN_LINES = {}   # path -> count of lines that would not parse (see report)


def iter_rows(path):
    """Yield (trial_key, result_dict) for every line of a trials.jsonl.

    Unparseable lines are skipped, but COUNTED and reported: both canonical
    corpora were written around the 2026-05-28 async-write torn-line window,
    and a silent skip would shrink a headline denominator with no signal.
    Assignment (not +=) keeps the count idempotent across the two passes.
    """
    torn = 0
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                torn += 1
                continue
            key = rec.get("key")
            yield (tuple(key) if isinstance(key, list) else key), rec.get("result", rec)
    TORN_LINES[str(path)] = torn


def no_tools_rows(paths):
    """Only the no-tools rows that carry evidence (`format` is passed in that
    branch alone), minus infra failures, minus unknown tasks. Takes the LIST of
    trials files belonging to one cell (a cell may carry mop-up/resume files
    such as `trials_rest52.jsonl`; `e2e_regrade` globs them the same way)."""
    for path in paths:
        for key, r in iter_rows(path):
            if r.get("with_tools") is not False or r.get("infra_failure"):
                continue
            if r.get("task") in MODELS:
                yield key, r


def cell_rows(paths):
    """Deduplicated no-tools rows for one cell -> ({trial key: row}, dup count).

    Last wins, matching `e2e_regrade`. Dedup happens BEFORE anything counts:
    a duplicated at-cap row would otherwise inflate the pinned-mass count
    `detect_cap` keys on, and be counted twice in every denominator.
    """
    keyed, dups = {}, 0
    for key, r in no_tools_rows(paths):
        if key in keyed:
            dups += 1
        keyed[key] = r
    return keyed, dups


def survey(paths):
    """Pass 1: response-length histogram (for the cap) + a content fingerprint.

    The fingerprint hashes the sorted (trial key -> response digest + every
    field `classify` reads) mapping, so it is invariant to line order but NOT
    to drift in a field that can change a row's grade: `truncated` and
    `failure_reason` drive the censored/provable split and the whole
    format_parse_fail table, so two cells differing only there must NOT collide
    and be silently deduplicated. Two distinct 4,560-row cells cannot collide
    by chance.
    """
    keyed, dups = cell_rows(paths)
    lengths = defaultdict(int)
    h = hashlib.sha1()
    for key in sorted(keyed, key=repr):
        r = keyed[key]
        resp = r.get("response") or ""
        lengths[len(resp)] += 1
        h.update(f"{key}\x00{r.get('task')}\x00{bool(r.get('truncated'))}"
                 f"\x00{r.get('failure_reason')}\x00".encode("utf-8", "replace"))
        h.update(hashlib.sha1(resp.encode("utf-8", "replace")).digest())
        h.update(b"\x01")
    return dict(lengths), h.hexdigest(), len(keyed), dups


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
    missing, dup_rows = [], []
    for corpus, root, canonical in CORPORA:
        by_cell = defaultdict(list)
        for f in sorted(root.glob("*/trials*.jsonl")):
            if "no-tools" in f.parent.name:
                by_cell[f.parent].append(f)
        if not by_cell:
            if canonical:
                sys.exit(f"FATAL: no no-tools cells under {root} — "
                         f"wrong cwd or a renamed layout?")
            # A control tree is OPTIONAL: `results/` is gitignored, and every
            # headline figure is canonical-only (`canonical=False` is never
            # pooled). Warn and continue so the documented reproduce command
            # still yields the headline on a machine without this tree.
            missing.append((corpus, root))
            continue
        for cell_dir, paths in sorted(by_cell.items()):
            name = cell_dir.name
            lengths, fp, n, dups = survey(paths)
            if n == 0:
                # Guard BEFORE the fingerprint: a zero-row cell hashes to the
                # empty digest and detect_cap({}) returns a valid-looking cap,
                # so a second one would be reported as a duplicate of the first
                # and drag an unrelated cell into `matched_twins`.
                skipped.append((corpus, name, "no no-tools rows"))
                continue
            if dups:
                dup_rows.append((corpus, name, dups))
            cap = detect_cap(lengths)
            if cap is None:
                skipped.append((corpus, name, f"no known cap "
                                              f"(max response {max(lengths)})"))
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
            cells.append((corpus, canonical, name, paths, cap, n))
    if not cells:
        sys.exit("FATAL: no cells to audit.")

    print(f"cells read: {len(cells)} kept, {len(dropped)} dropped as duplicates, "
          f"{len(skipped)} skipped (no known cap)\n")
    for corpus, name, twin, n in dropped:
        print(f"  DROPPED duplicate  {corpus}/{name}  ({n} rows) == {twin}")
    for corpus, name, why in skipped:
        print(f"  SKIPPED            {corpus}/{name}  ({why})")
    for corpus, name, n in dup_rows:
        print(f"  DEDUPED rows       {corpus}/{name}  ({n} duplicate trial key(s), last wins)")
    for corpus, root in missing:
        print(f"  MISSING optional   {corpus} ({root}) — control tree absent; "
              f"canonical figures are unaffected")
    torn = {k: v for k, v in TORN_LINES.items() if v}
    for path, n in sorted(torn.items()):
        print(f"  UNPARSEABLE lines  {n} skipped in {path}")
    if dropped or skipped or dup_rows or missing or torn:
        print()
    for corpus in dict.fromkeys(c for c, *_ in CORPORA):
        caps = sorted({cap for c, _, _, _, cap, _ in cells if c == corpus})
        rows = sum(n for c, _, _, _, _, n in cells if c == corpus)
        print(f"  {corpus:<18} {sum(1 for c, *_ in cells if c == corpus):>2} cells, "
              f"{rows:>6} no-tools rows, per-cell caps {caps}")
    print()

    # The control tree re-ran exactly the 4 think=on Qwen cells, so the matched
    # subset MUST come out at 4. If it does not, a stored baseline copy has
    # drifted from its canonical twin: that copy is no longer dropped (its rows
    # then contaminate the control column) and the twin falls out of the
    # comparison. Derive the label from the real size and say so loudly.
    if matched_twins and len(matched_twins) != EXPECTED_MATCHED:
        print(f"  WARNING: matched baseline subset is {len(matched_twins)} cells, "
              f"expected {EXPECTED_MATCHED}. A control-tree baseline copy no "
              f"longer matches its canonical twin byte for byte; the control "
              f"column and the matched row below are both affected.\n")
    matched_label = f"[matched {len(matched_twins)}-cell subset]"

    # ---- Pass 2: classify -------------------------------------------------
    stats = defaultdict(lambda: defaultdict(int))
    shapes = defaultdict(int)
    fpf = defaultdict(int)      # (group, task) -> format_parse_fail rows
    seen = defaultdict(int)     # (group, task) -> all no-tools rows
    pydantic_disagreements = 0
    for corpus, canonical, name, paths, cap, _ in cells:
        grp = "canonical" if canonical else "control"
        groups = [corpus]
        if f"{corpus}/{name}" in matched_twins:
            groups.append(f"{corpus} {matched_label}")
        rows_by_key, _ = cell_rows(paths)
        for r in rows_by_key.values():
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
                        if VERDICT_BARE.match(s)
                        else "trailer present in snapshot" if trailer_visible(s)
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
              f"truncated {s['censored'] + s['not_json_truncated']} "
              f"(of which {s['not_json_truncated']} are provable non-JSON and "
              f"ARE inside the provable denominator) | empty {s['empty']}{tag}")
        if corpus in canonical_corpora:
            for k, v in s.items():
                pooled[k] += v
    p_proof = sum(pooled[k] for k in PROOF)
    p_comp = sum(pooled[k] for k in COMPLETE)
    if p_proof:
        # COMPLETE is a strict subset of PROOF (it drops every truncated row),
        # so p_proof > 0 does NOT imply p_comp > 0: a corpus in which every
        # provable row is truncated is legal, and used to crash here after all
        # cells had already been classified.
        rate_pc = (f"{100*pooled['schema_ok']/p_comp:.2f}% of {p_comp} complete"
                   if p_comp else "no complete rows")
        print(f"\nCANONICAL POOLED ({' + '.join(sorted(canonical_corpora))}): "
              f"{sum(pooled.values())} no-tools rows | conformant {pooled['schema_ok']} "
              f"({100*pooled['schema_ok']/p_proof:.2f}% of {p_proof} provable, "
              f"{rate_pc})")

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
