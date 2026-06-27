# Fix plan — `_normalize_trajectory` predicate-syntax bug + frontier simulate re-grade

> **STATUS 2026-06-23: DONE (notation fix) — this is now historical.** The `_canon_atom` fix
> landed (commit `5879ac4`) and the frontier corpora were re-graded. **Actual numbers differ from
> the state-set *estimates* below** (shipped strict grader): Haiku 42.0%, Sonnet canon 45.0%, anon
> 38.3%. The open-roster scope note here was also refined — it is a *different* failure, not the same
> artifact. Authoritative current record: `development/simulate_decisions_and_next_steps.md`.

**Hand this to an implementing agent.** Background + evidence:
`development/grading_artifacts_findings.md` (read it first). Memory:
`project_simulate_grader_artifact`.

## The bug (one sentence)
`pddl_eval/scoring.py::_normalize_trajectory` canonicalises a simulate trajectory
by lowercasing + collapsing whitespace **but never reconciles predicate syntax** —
the model emits PDDL s-expressions `(ontable shaker1)` while the oracle emits
functional `ontable(shaker1)` — so every *correct* no-tools simulation is scored
`result_mismatch`. Frontier `simulate` reads 0% (Sonnet 0/300, Haiku 0/100) when
the real numbers are ~66% / ~50%.

## Scope — DO
1. Fix `_normalize_trajectory` so the two predicate syntaxes compare equal.
2. Unit-test the fix (cross-syntax equality + idempotency + malformed handling).
3. Re-grade the **frontier** corpora from local raw batch data (no spend, no
   cluster) and report the corrected `simulate` numbers.
4. Update the on-disk graded results, CHANGELOG, OPEN_ISSUES (new ISS), and
   `paper_notes_discussions.md`.

## Scope — DO NOT
- **Do not touch** the PlanBench `t7` state parser
  (`external/LLMs-Planning/.../utils/text_to_pddl.py::text_to_state`). It is a
  third-party published deterministic parser; leave it (see findings doc, Finding 2).
- **Do not re-run / re-grade the open vLLM roster.** Their corpus is NOT
  re-gradeable from disk (`RESPONSE_SNAPSHOT_LEN=500` kept only a 500-char snapshot,
  no stored `gt`). Recovering their true simulate numbers needs a cluster re-run
  with the fix + a higher token cap — a SEPARATE, user-gated step (a ping is
  required before any cluster work). Out of scope here.
- Do not change prompts, fixtures, the corpus, or `RESPONSE_SNAPSHOT_LEN` (note the
  latter as a follow-up only).

## Branch state (important)
The working tree is on **`feat/claude-api-haiku-frontier`** with **uncommitted**
changes from the Haiku NT phase (renamed `tools/sonnet_* → claude_api_*`, added
`--model`/`--num-variants` to `claude_api_batch.py`, added the `anthropic` backend
to `planbench/engine.py`, plus new `results/haiku-frontier/`). Confirm with
`git status` first. Put this fix on that branch (or a child of it) — do not branch
from a stale `main` that lacks the rename, or imports will break.

## The fix (precise)

In `pddl_eval/scoring.py::_normalize_trajectory` (~line 134), add a small pure
helper and apply it to **boolean predicate strings, numeric-fluent keys, and the
action string** — all three carry the same syntax split.

Canonicalisation rule — map any of these to one canonical token string:
```
(ontable shaker1)                 -> "ontable shaker1"
ontable(shaker1)                  -> "ontable shaker1"
(dispenses dispenser1 ingredient1)-> "dispenses dispenser1 ingredient1"
dispenses(dispenser1, ingredient1)-> "dispenses dispenser1 ingredient1"
(handempty) / handempty / handempty() -> "handempty"
```
Reference implementation (validated in the diagnostic):
```python
import re
_ATOM = re.compile(r'^\(?\s*([a-z0-9_\-]+)\s*\(?\s*([^()]*)\)?\s*\)?$')
def _canon_atom(s: str) -> str:
    t = " ".join(str(s).split()).lower()
    m = _ATOM.match(t)
    if not m:
        return t                      # fall back to the old behaviour, never crash
    name, rest = m.group(1), m.group(2).strip()
    args = [a for a in re.split(r'[\s,]+', rest) if a]
    return " ".join([name, *args])
```
Apply it:
- `boolean_canon = sorted(_canon_atom(b) for b in boolean_items)`
- numeric keys: `numeric_canon[_canon_atom(k)] = float(v)` (keep the float-parse
  failure → `return None`)
- `action_canon = "" if action_raw is None else _canon_atom(action_raw)`

Constraints:
- **Idempotent** (`_canon_atom(_canon_atom(x)) == _canon_atom(x)`).
- **Never raises / never silently widens** — malformed atoms fall back to the
  current whitespace-lowered string, so a genuinely-wrong trajectory still mismatches.
- Preserve all existing `return None` paths (non-dict entry, non-dict `state`,
  non-dict numeric, unparseable float) → still `FR_FORMAT_PARSE_FAIL`/`FR_UNKNOWN`.

## Regression safety (must verify)
`_normalize_trajectory` is shared by **both** simulate paths
(`scoring.py` ~445 oracle, ~460 with-tools tool-result, ~476 no-tools model).
With-tools simulate already matched (both sides are functional `boolean_fluents`).
After the fix both sides are canonicalised identically, so **with-tools simulate
must not regress**. Cover this with a unit test (functional==functional still
equal; functional==s-expr now equal; different-content still unequal).

## Tests to add (`tests/test_scoring*.py` or the existing scoring test)
- `_canon_atom`: both syntaxes → identical; no-arg preds; comma vs space args;
  idempotency; junk string → unchanged-lowered.
- `_normalize_trajectory`: a model s-expr trajectory and the equivalent oracle
  functional trajectory normalise **equal**; a content-different pair normalise
  **unequal**; numeric-key syntax variants compare equal.
- Keep the whole `tests/verify.sh` green.

## Frontier re-grade procedure (reuses existing grade path — no parallel logic)
The fix lives inside `check_success`'s simulate branch, so just re-run the
existing batch grader on the local raw batch dirs (they hold full responses +
oracle):

```
# Sonnet canonical + anon, Haiku canonical — re-grade with the fixed normalizer.
# solve trials are present → --marketplace-path is required (MCP validates plans).
python3 tools/claude_api_batch.py grade --batch-dir .local/sonnet/canonical \
    --marketplace-path ../pddl-copilot --out-results results/sonnet-frontier/sweep5v2
python3 tools/claude_api_batch.py grade --batch-dir .local/sonnet/anon \
    --marketplace-path ../pddl-copilot --out-results results/sonnet-frontier/sweep6
python3 tools/claude_api_batch.py grade --batch-dir .local/haiku/singletool_nt_canonical \
    --marketplace-path ../pddl-copilot --out-results results/haiku-frontier/sweep5v2
```
(`grade` reads the built model back from `counts.json`, so `--model` is not needed.)

### Acceptance criteria
- `simulate` moves **0% → ~66% Sonnet canonical / ~61% anon / ~50% Haiku** (these
  are state-set approximations; the faithful grader with exact `step`+`action`
  alignment is authoritative — REPORT whatever it gives, that's the real number).
- **All non-simulate tasks reproduce their prior numbers** (built-in regression
  check): solve 28.7/28.3 Sonnet, 22.0 Haiku; validate_* unchanged. If any
  non-simulate cell shifts, STOP — the fix touched something it shouldn't.
- Truncated simulate trials still fail (they have no answer) — the fix only
  recovers *completed* correct trajectories. Report the truncation rate alongside.

## Documentation owed
- `development/CHANGELOG.md`: dated entry — the normalizer bug, the fix, the
  frontier re-grade deltas (simulate 0%→…), regression note (other tasks
  unchanged), and that the open roster is NOT re-graded (disk-unrecoverable).
- `development/OPEN_ISSUES.md`: new `ISS-###` (P1) — predicate-syntax normalize
  bug; mark frontier-fixed; leave open the open-roster re-run + the
  `RESPONSE_SNAPSHOT_LEN`/store-`gt` hygiene follow-up.
- `development/paper_notes_discussions.md`: dated entry — the simulate sole-source
  "floor" was a grader artifact; frontier simulate is ~50–66%, not 0; the "frontier
  reproduces the floor" robustness paragraph and the 0%→97% bimodal low-pole must
  be rewritten (low pole becomes `solve` ~28%); `solve`/`validate_*` unaffected.

## Out-of-scope follow-ups (note, don't do)
- Open vLLM roster simulate re-run (cluster, higher token cap, user-gated + ping).
- Raise `RESPONSE_SNAPSHOT_LEN` and/or persist `gt` in trials so future corpora are
  re-gradeable.
- PlanBench `t7`/`t2` parser handling (leave; report as caveat).
