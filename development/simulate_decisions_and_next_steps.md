# Simulate grading — decisions, status & next development lines (2026-06-23)

Wrap-up record for the simulate-grader work this session. Supersedes the earlier
open-decision draft. Background: `frontier_grading_artifacts_findings.md`,
`simulate_normalizer_fix_plan.md`; memory `project_simulate_grader_artifact`.

## DONE this session (committed on `feat/claude-api-haiku-frontier`)
- **Notation fix** — `_canon_atom` in `pddl_eval/scoring.py` bridges the model's PDDL
  s-expression `(ontable a)` and the oracle's functional `ontable(a)` (boolean preds,
  numeric keys, action string; bounded fallback, never widens equality). Commit `5879ac4`,
  with tests.
- **Frontier re-grade** from local raw batch dirs (no spend): simulate **0% → Haiku 42.0%
  [32.8,51.8], Sonnet canon 45.0% [39.5,50.7], anon 38.3% [33.0,43.9]**; every non-simulate
  cell byte-identical (regression check passed). Commit `156fb01`. Updated
  `results/{haiku-frontier/sweep5v2, sonnet-frontier/{sweep5v2,sweep6}}`.
- Re-grade is reproducible via the documented `tools/claude_api_batch.py grade` commands
  (CHANGELOG 2026-06-23) — no new script required.

## DECISIONS — made this session, to IMPLEMENT in the dev lines below (NOT coded this session)
- **Q1 grader = two-metric, bounded wrapper-tolerance** (adopted; independent scientific
  review concurred). Report THREE numbers, never one:
  - **format-compliance** — emitted the schema-exact `{"trajectory":[…]}` wrapper.
  - **state-tracking accuracy** — content correct under coercion (the primary number).
  - **strict conjunction** — compliant AND correct (sensitivity line).
  Bounded coercion whitelist (pre-register; freeze before any re-run):
  1. parse the ENTIRE output as one JSON value — **NO** prose/regex extraction, ever;
  2. dict with `trajectory` key → canonical path;
  3. top-level list of valid step objects → wrap → accept;
  4. single valid step object → wrap → accept;
  5. anything else → `format_parse_fail`. **Never invent or repair a field.**
  Same grader rule for open + frontier; only the prose interpretation differs by condition.
  Also disclose, separately, that `guided_json` did not bind (an apparatus finding).
- **Q2 generation = original token cap + `guided_json` as-is** (keep re-runs comparable; the
  grader is the only deliberate no-tools knob).
- **Open-roster simulate 0% is NOT the frontier's notation artifact** (verified): `result_mismatch`
  ~0%; the 0% is unenforced `guided_json` + a strict-wrapper sub-artifact + truncation + some
  genuine incapability, unmeasurable from disk (`RESPONSE_SNAPSHOT_LEN=500`, no `gt`). Detail in
  the findings doc.
- **Contamination (anon) NOT needed** for the next runs.
- **`paper/` untouched** — gather complete data before any narrative.

## NEXT — two development lines (kick off after this branch merges)

### Line 1 — fix think=on, then run the FULL think=on
- Build the **decoupled-budget fix** (iter-2 **T6**, currently TODO/unbuilt):
  `stop=["</think>"]` + 2-call continuation so thinking and answer get separate budgets.
  Without it think=on is budget-confounded (baseline truncates 55–83%).
- Then a clean think=on run with the **Q1 two-metric grader** + full-response storage.
- **No contamination** (no anon arm).

### Line 2 — complete the with-tools frontier setup
- Per the earlier-session design (memory `project_sonnet_frontier_notools`,
  `project_frontier_phase_design`): Haiku/Sonnet with-tools over the matched corpus.
- **Open cost blocker (ISS-023):** Haiku-WT 4,560 at ~$146 list was REJECTED — design a cheaper
  path (prompt caching of the stable system + tool-schema prefix) FIRST.

## NOTES / possibly-missed tasks (flagged for reconsideration)
- **Q1 grader is a PREREQUISITE** for clean simulate numbers in either line — land it as its
  own small PR before the sweeps, not bundled.
- **think=OFF open-roster simulate** (tools + no-tools, "equally evaluated"): Line 1 is
  think=on-focused; the think=off open-roster simulate clean re-run (with the Q1 grader) is not
  explicitly in either line. Fold it into Line 1's sweep, or run alongside?
- **`guided_json` enforcement** is its own apparatus bug — verify/fix (or drop + prompt-instruct)
  before quoting any clean open-roster simulate number.
- **`RESPONSE_SNAPSHOT_LEN`** should be raised for any new corpus so it stays re-gradeable
  (avoid repeating the 500-char block). Storage-only.
