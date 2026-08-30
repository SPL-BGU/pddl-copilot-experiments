---
name: freeze-protocol
description: Pre-freeze gate for preregistered analysis code. Use BEFORE hashing/freezing any analysis entry point under a prereg, when writing a new prereg's blocking-prerequisites section, and before ratifying a readout produced by frozen code that never passed this gate.
---

# Freeze protocol v2 — prove the code implements the prereg, then hash it

A hash freeze proves *these exact bytes ran*. It says nothing about whether the
bytes implement the spec, and treating "frozen" as "done" is how PR #96 shipped
a ratified readout whose frozen code carried 15 correctness findings (declared
as `ntster_h4_prereg.md` §9.2 deviations 3–9). All 15 fall into four families;
each gate below closes one.

**Ordering is the point.** The v1 failure was not missing checks, it was
sequence: the adversarial review ran *after* the ratified readout shipped.

```
freeze candidate → gates 1–5 → hash freeze (§8-item-9 record) → first contact with data
```

## Freeze-time gates — every one blocks the freeze

**1. Typed load boundary** *(family: silent-schema reads — §9.2 dev. 3/6/7)*
All row reads in the frozen boundary go through one shared loader that parses
each row into a typed record and **crashes** on an unknown enum value, a
missing key, or a key read from the wrong layer (overlay vs raw
`trials.jsonl`). No bare `row.get()` and no truthiness tests on grade fields
in estimator code — `bool("indeterminate")` is True, and that one expression
manufactured the only NOT-EQUIVALENT cell in the shipped H4 readout.

**2. Registered constants are asserts** *(family: labels asserted, not checked — dev. 4/9)*
Every quantity the prereg names — cluster count k, roster, N per cell,
canonical GT hash, snapshot caps — appears as a literal assert in the frozen
code, not only in a label, docstring, or checklist record. The shipped
"problem (k=100)" interval ran on 220 unbalanced clusters; `assert k == 100`
fails on first invocation and would have surfaced the weighting bug before any
data was analysed.

**3. Clause-by-clause traceability pass** *(family: commitments with no code — dev. 3/5/8/9)*
Walk the prereg's analysis plan clause by clause. Every testable commitment
maps to a code line or a runtime assert; record the map (clause → `file:line`)
in the freeze record next to the sha256 table. A commitment with no
implementation blocks the freeze — this is the gate that catches "the
censoring-exclusion clause was written and never implemented" and "the F-gate
rule was recorded but never consulted." Checklist records that claim code
behaviour ("both entry points call `assert_gate()`") are verified by grep or
test at freeze time, never taken from memory. Declare frozen files' imports in
`requirements.txt`.

**4. Synthetic fixture run** *(family: latent verdict paths — dev. 3/4/8)*
Build a mini-corpus (~30 rows) with planted traps and hand-computed answers:
censored/indeterminate rows, a zero-success arm, a duplicate overlay cell, a
row missing `snapshot_cap`, and a known Δ per contrast. The frozen pipeline
must reproduce the hand-computed numbers exactly and must *refuse* the
malformed cells. Commit fixture + expected values under `tests/`. This is the
only oracle estimator code has — the no-smoke-tests rule for cluster-ops
scripts does not apply here, because there is no real command whose output a
human can eyeball instead.

**5. Adversarial review of the freeze candidate** *(family: all of them)*
An independent correctness review (different model/session than the author,
`/code-review` at high effort or stronger) reads the freeze-candidate files
against the prereg, with the traceability map from gate 3 in context. Findings
are fixed before the hash is taken. This exact review found all 15 issues in
PR #96 — it works; v2 only moves it to the point in the ordering where fixes
are ordinary edits instead of declared deviations.

## Readout-time tripwires — halt the readout, don't ship and explain later

*(family: degenerate outputs shipped as results — dev. 6/7, part of 3)*

- **A guard firing everywhere is a bug report, not a result.** All cells VOID,
  a fallback bucket (e.g. APPARATUS) absorbing double-digit shares in every
  arm — halt and trace before writing a single readout sentence.
- **A constant output column is a schema bug until proven otherwise** (the
  legacy surface read a key no row has and reported False on every row).
- **Rates outside the known corpus band get audited before they get
  narrated** (shipped 4B `simulate` 41.7% vs 17.1% determinate). Same
  principle as the e2e-overlay rule: audit extraction/grade distributions on
  every new corpus before quoting it.

## After the freeze

Any edit to a frozen file — even a one-character fix — is a declared deviation
in the prereg, a re-freeze with new sha256s, and a regeneration of every
downstream artifact (readout, NUMBERS.md, decks) from the re-frozen code. The
§9.2 corrective re-freeze (`4bd6fba` → `29e0085`) is the precedent for how to
do this honestly.
