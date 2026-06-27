# Q1 two-metric simulate grader — implementation plan (prereq for Line 1 + open-roster re-run)

**Status:** PLAN ONLY. No code yet. Branch `paper/iter2-q1-grader` off `main` (lands first per DECISION D, before the decoupled-budget PR). Offline-only (re-grade has no spend, no cluster).
**Date:** 2026-06-25
**Background:** `../decoupled/simulate_decisions_and_next_steps.md` (the pre-registered Q1 spec), `../grading_artifacts_findings.md`, ISS-024, CHANGELOG 2026-06-23 (`_canon_atom`). Sibling: `decoupled_budget_plan.md`.

Answer the `> DECISION:` slots inline; I'll fold them in before coding.

---

## Objective

Replace the **strict-wrapper** no-tools `simulate` grader with the pre-registered **two-metric,
bounded-wrapper-tolerant** grader. Report **three** numbers, never one:
- **state-tracking accuracy** — content correct under bounded coercion → becomes `success` (primary).
- **format-compliance** — emitted the schema-exact `{"trajectory":[…]}` wrapper.
- **strict conjunction** — compliant AND correct (derivable from the two).

## Current state (verified against the code)

- `check_success` simulate no-tools branch (`scoring.py:493-508`): `_safe_pydantic_validate(
  SimulateResponse, response)` requires the **whole output** to be JSON (markdown-fence-tolerant)
  that validates as `{"trajectory":[StateStep]}`. Anything else → `FR_FORMAT_PARSE_FAIL`, **even
  when the content is correct** (the "strict-wrapper sub-artifact"). Then `_normalize_trajectory`
  (incl. the `_canon_atom` fix) deep-equals vs the oracle → `success` / `FR_RESULT_MISMATCH`.
- `check_success` is the **single shared grader** for the live harness (`evaluate_one`) AND the
  offline Anthropic batch grader (`tools/claude_api_batch.py:204`). One change covers both — "same
  grader rule for open + frontier" is structurally enforced, not duplicated.
- Schemas: `StateStep = {step:int, action:str, state:{boolean:list, numeric:dict}}`;
  `SimulateResponse = {trajectory: list[StateStep]}`.
- **With-tools simulate is out of scope** — it grades via the `get_state_transition` tool result;
  there is no model-emitted wrapper, so format-compliance is meaningless there. Q1 touches **only**
  the no-tools branch.

## The grader (pre-registered bounded-coercion whitelist — freeze before any re-run)

One pure primitive `_coerce_simulate_trajectory(response) -> (trajectory | None, format_compliant)`:
1. Parse the **ENTIRE** output as **one** JSON value (markdown-fence stripped — see DECISION E).
   **No prose/regex extraction, ever.** Non-JSON → `(None, False)`.
2. `dict` with a `trajectory` key → validate as `SimulateResponse` → its trajectory;
   **`format_compliant=True`**.
3. top-level `list` → validate as `list[StateStep]` → wrap → accept; `format_compliant=False`.
4. single `dict` that validates as one `StateStep` → wrap as `[step]` → accept; `format_compliant=False`.
5. anything else → `(None, False)` → `FR_FORMAT_PARSE_FAIL`. **Never invent or repair a field.**

`check_success` simulate no-tools then: coerce → if `None` → `FR_FORMAT_PARSE_FAIL`; empty
trajectory → `FR_SIMULATE_EMPTY`; else `_normalize_trajectory` + deep-equal → `success` /
`FR_RESULT_MISMATCH`. **`success` = state-tracking** (the primary number).

---

## ⚠️ Decisions to confirm

### DECISION A — how to surface format-compliance (the main design fork)
`check_success` returns `(tool_selected, success, failure_reason)`. On a success, `failure_reason`
is `FR_OK` by contract, so it **cannot** also carry the compliance bit — compliance needs its own
channel. Options:
- **A1 (recommended): write-time `TaskResult.format_compliant: bool | None`**, computed at grade
  time by a thin public helper `simulate_format_compliant(response)` that shares
  `_coerce_simulate_trajectory` with `check_success`. Both grade call sites (`evaluate_one`,
  `claude_api_batch.grade_*`) set the field. No `check_success` signature change (keeps ~8 test
  call sites + 2 prod stable); the bit is **frozen at grade time** (pre-registration-friendly) and
  is **independent of `RESPONSE_SNAPSHOT_LEN`** (full text is in hand at grade time, before storage
  truncation). Cost: the response is parsed twice — negligible (offline, tiny JSON), and the shared
  primitive means zero logic drift.
- **A2: 4-tuple `check_success`** returning compliance — most explicit but ripples to every test
  unpack.
- **A3: read-time recompute** in the analyzer (like `relabel_truncated_taxonomy`) — zero new field,
  but **couples to full-response storage** (`RESPONSE_SNAPSHOT_LEN` 16384 lives on the *decoupled*
  branch, not here), so it can't recompute compliance for any corpus stored under the old 500 cap.

> **DECISION A.** Recommend A1 (write-time field via shared primitive).
> ANSWER:A1

### DECISION B — re-grade the frontier corpora now (numbers will shift again)
Landing Q1 changes how existing no-tools simulate trials grade. The frontier raw batch dirs
(`.local/{haiku,sonnet}/…`, full responses on disk) can be re-graded offline with no spend — this
is the point: the wrapper-tolerance recovers correct-but-unwrapped trajectories (clean top-level
list / single step), so the frontier `simulate` numbers will move **again** vs the 06-23
`_canon_atom` values (Haiku 42.0 / Sonnet canon 45.0 / anon 38.3), likely **up**, plus we gain the
format-compliance + strict numbers. The paper is untouched (gather-data-first), so shifting these
is fine. **Open-roster cannot be re-graded** (responses truncated at 500, no `gt` on disk) — its
clean number still needs the gated re-run (Line 1), not a re-grade.

> **DECISION B.** Recommend: re-grade the frontier corpora in this PR (offline) and report the new
> 3-number breakdown; leave open-roster for the gated re-run.
> ANSWER: recommendation accepted. regrade in this pr and report the new 3 number breakdown. leave qwens to gated rerun.

### DECISION C — reporting surface in this PR
Land the grader + frontier re-grade + a **minimal** summary surfacing (the three numbers per
simulate no-tools cell). Defer deck/paper wiring (gather-data-first).

> **DECISION C.** Recommend: grader + re-grade + minimal summary fields/print; defer deck/paper.
> ANSWER: recommended approach accepted.

### DECISION D — `guided_json` did-not-bind disclosure (ISS-024(b)) stays separate
The apparatus finding that `guided_json` did not enforce the schema is a *generation* bug, not a
*grading* one. Keep it out of this PR (own item under ISS-024(b)); the Q1 grader's whole-output
JSON rule is exactly what makes the corpus gradeable despite the unenforced constraint.

> **DECISION D.** Recommend: out of scope here; track under ISS-024(b).
> ANSWER: recommendation accepted

### DECISION E — markdown-fence tolerance (a pre-registration sub-choice)
The current grader strips ```` ```json ```` fences before parsing; models emit them even under a
format constraint. Stripping a known markdown wrapper is **not** prose/regex *extraction* (the
entire remaining output must still be one JSON value), so I propose keeping it — but it must be a
conscious, frozen choice since the spec says "no regex extraction."

> **DECISION E.** Recommend: keep fence tolerance (documented as part of the frozen rule).
> ANSWER: accepted.

---

## Scope / files

| File | Action | Description |
|------|--------|-------------|
| `pddl_eval/scoring.py` | modify | Add `_coerce_simulate_trajectory` (the whitelist) + public `simulate_format_compliant`; rewrite the simulate no-tools branch of `check_success` to coerce (state-tracking = `success`). With-tools branch untouched. |
| `pddl_eval/runner.py` | modify | `TaskResult.format_compliant: bool \| None = None`; `evaluate_one` sets it for no-tools simulate via the helper. (A1) |
| `tools/claude_api_batch.py` | modify | Set `format_compliant` in the batch `grade_*` path (A1) so the frontier re-grade carries it. |
| `pddl_eval/summary.py` | modify | Surface the three numbers (state-tracking %, format-compliance %, strict %) for simulate no-tools cells. (C, minimal) |
| `tests/test_check_success.py` or new `tests/test_simulate_q1.py` | modify/create | Coercion cases: compliant wrapper, top-level list, single step, prose→fail, fenced JSON, empty trajectory; compliance bit; correct-but-non-compliant; never-repair. |
| `results/{haiku-frontier,sonnet-frontier}/…` | regenerate | Re-graded simulate cells + summaries (B). |
| `development/{CHANGELOG.md, OPEN_ISSUES.md, q1_grader_plan.md}` | modify | Entry + narrow ISS-024. |

## Reproducibility
- Grader change is **intentional** and pre-registered; it re-defines no-tools simulate `success`.
  All **non-simulate** cells and **with-tools** simulate are byte-identical (regression check, as in
  the `_canon_atom` landing).
- The frontier re-grade overwrites the 06-23 simulate numbers (DECISION B); a clean A/B for the
  decoupled run uses these Q1-graded baselines.
- `sweep5v2-final` tag already pins the pre-Q1 corpus state.

## Execution steps (after decisions)
1. (on `paper/iter2-q1-grader`, already branched off main) Add `_coerce_simulate_trajectory` + tests first (TDD).
2. Rewrite the `check_success` simulate no-tools branch to use it; add `simulate_format_compliant`.
3. `TaskResult.format_compliant` + wire `evaluate_one` and `claude_api_batch.grade_*` (A1).
4. Minimal `summary.py` surfacing (C).
5. Run `bash tests/verify.sh` green (incl. regression: non-simulate + with-tools unchanged).
6. Re-grade frontier corpora offline (`tools/claude_api_batch.py grade`); commit re-graded results.
7. CHANGELOG + narrow ISS-024; PR into `main`.

## Validation
- **Unit:** the whitelist cases above + idempotency + "never repair a field" (a step missing
  `state` must NOT be coerced into validity).
- **Regression:** non-simulate cells + with-tools simulate byte-identical across a re-grade.
- **Frontier re-grade sanity:** parse-fail count drops by exactly the clean-JSON-wrong-shape subset;
  prose-wrapped responses still fail (rule 1); state-tracking ≥ the 06-23 numbers.

## Documentation
- CHANGELOG entry (grader change, re-graded numbers, compat note).
- Narrow ISS-024: (a) the grader half is now built; the open-roster re-run still gated.
