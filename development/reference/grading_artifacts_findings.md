# Grading artifacts surfaced during the frontier Haiku NT phase (2026-06-23)

Two **format/normalization artifacts** were found while grading the Claude Haiku
no-tools runs. Both make a *correct* model answer score as wrong. They are the
**same phenomenon** (extraction/normalization can't read the model's format) but
differ in **ownership**, which dictates the remedy:

| artifact | grader | owner | remedy |
|---|---|---|---|
| PlanBench **t7** (plan-execution) state parse | `utils/text_to_pddl.py::text_to_state` | PlanBench (third-party, published, deterministic) | **leave it**; report with caveat |
| single-tool **simulate** trajectory normalize | `pddl_eval/scoring.py::_normalize_trajectory` | **ours** | **fix it** (bug); re-grade uniformly |

The simulate one is the important one — it touches a load-bearing paper claim.

---

## STATUS (2026-06-23, post-fix) — frontier re-graded; data still PARTIAL; do not narrate yet

> **UPDATE 2026-07-12 — data now COMPLETE; narration no longer blocked.** Since this status:
> the Q1 wrapper-tolerant grader landed 2026-06-25 (frontier state-tracking unchanged); the
> decoupled Line-1 sweep completed 2026-06-29 with the final matched-A/B rollup 2026-07-11
> (`decoupled/decoupled_run_handoff.md` §LINE COMPLETE — open-roster simulate floor = budget
> starvation); and delivered-answer (e2e) grading went through D7/D7b 2026-07-12
> (`tool_call_vs_final_output_grading.md` §0b). The table below remains the authoritative
> frontier NT simulate re-grade. The PARTIAL caveats below are historical.

Fix landed (`_canon_atom` in `_normalize_trajectory`, commit `5879ac4`); the three
Anthropic corpora re-graded from local raw batch dirs (commit `156fb01`). The
mechanism below is confirmed on real data. **These are the authoritative numbers**
(shipped strict grader = exact step + action + per-step state; they run a few
points under the state-set diagnostic *estimate* in Finding 1, which is expected —
strict is stricter):

| corpus | simulate before | after [95% Wilson] | pass · mismatch · parse-fail · truncated |
|---|--:|--:|---|
| Haiku sweep5v2 (n=100) | 0% | **42.0% [32.8,51.8]** | 42 · 25 · 0 · 33 |
| Sonnet sweep5v2 canon (n=300) | 0% | **45.0% [39.5,50.7]** | 135 · 14 · 62 · 89 |
| Sonnet sweep6 anon (n=300) | 0% | **38.3% [33.0,43.9]** | 115 · 13 · 70 · 102 |

All non-simulate cells reproduced byte-identically (regression check passed).
Of trials that produced a *parseable* trajectory, Sonnet is correct 90.6% (canon) /
89.8% (anon); the residual is truncation + format-parse, i.e. output length/format.

**The picture is INCOMPLETE — hold the paper narrative.** We have corrected numbers
for **3 frontier cells only**. Two gaps must close before assessing what the
simulate result *means*:
1. **Open vLLM roster** (the bulk of the paper's simulate evidence) is **not** the
   frontier's notation artifact and **not** re-gradeable from disk
   (`RESPONSE_SNAPSHOT_LEN=500`, no stored `gt`) → its 0% is unenforced `guided_json`
   + a strict-wrapper sub-artifact + truncation (verified below) → needs a clean re-run
   with the Q1 two-metric grader + decoupled budget + full storage, not "the fix."
2. **Budget vs capability** in the residual (33% truncated Haiku / ~30% Sonnet) is
   unresolved — a higher token-cap re-run separates "ran out of tokens" from "got
   the state wrong." Until both close, do not rewrite `paper/` (see Open items;
   cluster work is user-gated, ping first).

---

## Finding 1 — single-tool `simulate` 0% is largely a grader bug (OURS)

### What
Haiku no-tools `simulate` scored **0/100** (`results/haiku-frontier/sweep5v2`).
Failure split: 67 `result_mismatch` (model produced a complete trajectory,
`end_turn`) + 33 `truncated_no_answer` (`length`).

A syntax-reconciled re-grade of the same 100 trials:

| grader | Haiku simulate (n=100) |
|---|--:|
| harness as-shipped | **0%** |
| syntax-reconciled (action + per-step state-set sequence) | **50% overall** — **75% of the 67 completed** trials; the remaining 33 are truncation (no answer), a separate token-budget issue |

### Why (mechanism)
`pddl_eval/scoring.py::_normalize_trajectory` canonicalises a trajectory to
`{step, action, boolean(sorted list), numeric}` and the simulate grader checks
`model_canon == oracle_canon` (deep equality). The normalizer lowercases and
collapses whitespace **but does not reconcile predicate syntax**:

- **model** emits PDDL s-expressions: `"(ontable shaker1)"`, `"(dispenses dispenser1 ingredient1)"`
- **oracle** (`gt["trace"].trajectory[*].boolean_fluents`) emits functional syntax: `"ontable(shaker1)"`, `"dispenses(dispenser1, ingredient1)"`

After normalize these are still different strings → never equal → every correct
simulation is tagged `result_mismatch`.

### Concrete proof (blocksworld/p01, scored `result_mismatch`)
- model final state: `(handempty)`, `(ontable b1)`, `(on b3 b1)` …
- oracle final state: `handempty`, `ontable(b1)`, `on(b3,b1)` …

Same content, different notation.

### Reproduction
`tools`-free, local, no spend — join the batch sidecar + results and re-grade:
- raw model text: `.local/haiku/singletool_nt_canonical/results.jsonl` (`text`)
- oracle: `.local/haiku/singletool_nt_canonical/sidecar.jsonl` (`gt.trace`, JSON string; top-level keys `valid,status,steps,trajectory`; use `trajectory`, each step `{step, action, boolean_fluents: dict[str,bool], numeric_fluents}`)
- canonicalise both `(pred a b)` and `pred(a, b)` to `pred|a|b`, compare state-sets per step (drop the model's extra leading init step if `len(model)=len(oracle)+1`).

### Why this is a *bug*, not a benchmark gate
`_normalize_trajectory` was explicitly written to canonicalise for **content
equality** across the with-tools (`boolean_fluents` dict) and no-tools
(`state.boolean` list) shapes — its docstring says so. The predicate-syntax gap
is an unintended omission in that bridge, not a designed format requirement. The
model followed a valid PDDL representation; the grader simply can't read it. So
fixing it restores the intended measurement; it is **not** a benchmark-integrity
change.

### Blast radius — CONFIRMED on Sonnet (2026-06-23)
The **same** `_normalize_trajectory` graded Sonnet + the open roster. Re-grading
Sonnet's raw batch (`.local/sonnet/{canonical,anon}`) with the syntax fix:

| run | as-shipped | syntax-reconciled | of completed | truncated |
|---|--:|--:|--:|--:|
| **Sonnet canonical** | 0/300 | **66%** | 94% | 89/300 |
| **Sonnet anon** | 0/300 | **61%** | 93% | 102/300 |
| Haiku canonical | 0/100 | 50% | 75% | 33/100 |

So the paper's headline **"Sonnet 4.6 reproduces the simulate floor (0/300) →
sole-source capability boundary"** is **wrong**: Sonnet simulates correctly on
**94% of the trials it completes** (66% overall; the gap is truncation, not
errors). The `simulate` "floor" was the grader, full stop.

### Narrative impact (what changes / survives)
- **`simulate` is NOT a sole-source floor.** Both frontier models simulate the
  majority of trials unaided once the syntax bug is fixed.
- **The "0%→97% volatility / bimodal" spread loses its low pole.** With simulate
  ≈61–66%, the genuine unaided floor is now **`solve`** (~28% Sonnet, 22% Haiku;
  real `plan_invalid`, different grader, unaffected). The spread is ~28%→97%, not
  0%→97%. Still a real spread; the "0%" rhetoric is gone.
- **"Frontier reproduces the floor" robustness paragraph must be rewritten** —
  Sonnet does not floor on simulate.
- **Contamination null weakens slightly but holds**: canonical 66% vs anon 61%
  (Δ≈5pp, in the truncation-confounded direction — anon prompts ~5% longer → more
  truncation, the known sweep6 confound). Not "both floored at 0" anymore, but
  still a small, confounded Δ.
- **Unaffected:** `solve` floor (real), `validate_*` highs (real), and the
  PlanBench story.

### Open vLLM roster — a DIFFERENT failure, NOT the frontier's notation artifact (verified 2026-06-23)
The notation fix (`_canon_atom`) only rescues `result_mismatch` — a parsed, correct
trajectory in the wrong predicate notation. For the open roster that bucket is **~0%**,
so the fix barely applies. Their as-shipped 0% is a different stack that fires **before**
the content comparison (no-tools, think=off, n=300/model):

| open model | result_mismatch (fix touches) | format_parse_fail | truncated |
|---|--:|--:|--:|
| Qwen3.5-0.8B | 0% | 78% | 22% |
| Qwen3.5-4B | 0% | 59% | 41% |
| Qwen3.5-9B | 0% | 63% | 37% |
| Qwen3.6-35B | 9% | 69% | 22% |
| gemma-4-26B | 0% | 72% | 28% |

(think=on shifts this strongly toward truncation — reasoning eats the shared decode budget.)

Two sub-findings from the 500-char response heads:
1. **`guided_json` did NOT bind.** The no-tools simulate path passes the `SimulateResponse`
   schema as `guided_json` (`runner.py:357`), yet outputs leak free prose ("Here is the
   step-by-step trace…") and markdown — impossible under a working constraint. So a large
   slice of `format_parse_fail` is an *apparatus* failure (the constraint meant to force the
   wrapper didn't), **not** proven model incapability. Owner: harness, not model.
2. **A second, wrapper-strictness sub-artifact.** When the models DO emit JSON it is often
   the right content (same `(ontable shaker1)` s-expr) in a *bare* shape — a top-level array
   `[{step…}]` or bare step object — instead of the schema's `{"trajectory":[…]}` wrapper,
   which the strict grader rejects. Model-dependent (0.8B 100% / 35B 57% / 9B 39% / gemma 35%
   / 4B 8% of parse-fails are JSON-shaped). This is the gap the adopted **Q1 wrapper-tolerant
   grader** closes — see `development/archive/decoupled/simulate_decisions_and_next_steps.md`.

**Net:** open-roster simulate 0% is a tangle of (unenforced format constraint + strict-wrapper
grader + truncation + some genuine incapability), in proportions **unmeasurable from disk**
(`RESPONSE_SNAPSHOT_LEN=500`, no stored `gt`). It is **NOT** the frontier's notation artifact.
A true number needs a clean **re-run** with the Q1 two-metric wrapper-tolerant grader +
full-response storage + (for think=on) the decoupled-budget fix — not a re-grade, and not "the
notation fix alone."

Net: the simulate "floor" decomposes as **frontier = pure grader artifact
(provable, ~50–66% real)**; **open roster = truncation + parse-fail + (unreached)
artifact, not disentangle-able without re-running.** Neither cleanly supports
"models can't simulate."

### Caveats on these numbers
- The re-grade compares per-step **state-set** sequences (syntax-reconciled),
  dropping exact `step`/`action` string matching the shipped grader also requires.
  A faithful fixed grader could land a few points lower — but 0%→~66% is robust in
  direction and magnitude.
- Truncation (30–34% on Sonnet) counts as fail. Simulate trajectories are long;
  raising the token cap would likely recover much of it (separate from the syntax
  bug). So "real" simulate is **66% (cap-limited) up to 94% (of completed)**.

### Caveats on the 50% figure
- The re-grade compares action + per-step **state-set** sequence (drops exact
  step index / off-by-one). The shipped grader is stricter (exact `step` +
  `action` string). A faithful fixed grader could land a few points lower.
- Truncation (33/100) counts as fail here (no answer). Whether that is
  "capability" or "budget" is a separate question (simulate trajectories are
  long; the token cap bites). Either way the floor is **~50%, not 0%**.

---

## Finding 2 — PlanBench `t7` 0% is a parser artifact (THEIRS — leave it)

### What
On blocksworld `t7` (plan-execution), **every engine run through our harness is
~0%**, while only the two original-author OpenAI models bundled with the repo
score:

| t7 (blocksworld) | score |
|---|--:|
| gpt-4_chat (orig. authors) | 28.4% |
| text-davinci-002 (orig. authors) | 0.6% |
| qwen3.6:35b (our harness) | 0.0% |
| Qwen3.5:9B | 0.0% |
| Qwen3.5:4B | 0.2% |
| Qwen3.5:0.8B | 0.0% |
| **Haiku** | 0.0% |

A capable 35B reasoner at *exactly* 0/500 while GPT-4 gets 28% is a format gate,
not a capability cliff. (Contrast `t2` optimality, where open models get 5–41% —
so `t2` is **not** a universal artifact; Haiku's `t2`=0 is its own mix of
markdown non-extraction + non-optimal plans.)

### Why (mechanism)
`utils/text_to_pddl.py::text_to_state` tokenises the whole answer with one line:
```python
text_preds = text.replace(' and ',',').split(",")   # assumes one comma/and-separated sentence
```
- **GPT-4** answers in flowing prose ("…the blue block is clear, the hand is
  holding the yellow block, …") → comma-split yields clean per-predicate chunks → parses.
- **Haiku** answers in a **markdown bullet list** (`**Resulting State:**` + `- …`
  lines, no commas) → `split(",")` returns one giant chunk → the parser extracts
  garbage (`['ontable_a','ontable_a']`) and scores 0, even though Haiku's stated
  state is essentially correct.

`t1`/`t2` use `text_to_plan_blocksworld`, which is **line-based** (scans each line
for an action word) → tolerant of markdown → that's why `t1` works (41%) and only
`t7`'s state parser is comma-brittle.

### The prompt does NOT instruct a format
The t7 prompt has **no format directive** — it only *demonstrates* the comma-prose
format in a one-shot example. So under PlanBench's strict, deterministic protocol
("continue the demonstrated pattern"), a markdown answer is legitimately "wrong by
the benchmark's own rule."

### Remedy: do NOT touch (user call, 2026-06-23)
- Coercing the format via prompt breaks comparability (baselines used the plain
  few-shot; the fixed GPT-4/davinci anchors can't be re-run).
- A tolerant parser would change a published, deterministic third-party benchmark
  — only acceptable as a **uniform, clearly-labelled diagnostic** re-grading *all*
  engines from raw responses, never as "the PlanBench number."
- **Decision:** leave t7 as-is; report `t1` + `t3` as the PlanBench comparison and
  flag `t7` (and the format-confounded part of `t2`) as a known parser artifact —
  which is itself a supporting point: rigid NL benchmark parsers undercount modern
  chat-formatted models, motivating tool-grounded evaluation.

---

## PlanBench Haiku NT — usable results (t1 + t3, same grader/instances)

`results/haiku-frontier/planbench/` (graded on cluster, VAL; prompts verified
byte-identical laptop↔cluster).

**blocksworld** (only fully-populated comparison; gpt-4/davinci never run on logistics/mystery):

| engine | t1 plan-gen | t3 verify | (t2 opt) | (t7 exec) |
|---|--:|--:|--:|--:|
| **Haiku** | **41.0%** | 78.2% | 0.0%* | 0.0%† |
| gpt-4_chat | 31.4% | 94.6% | 28.4% | 28.4% |
| Qwen3.6:35b | 35.8% | 88.4% | 37.6% | 0.0%† |
| Qwen3.5:9B | 25.4% | 88.0% | 12.2% | 0.0%† |

`* t2` format-confounded (Haiku-specific). `† t7` parser artifact (all our-harness models).

Haiku across configs: t1 = bw 41.0 / logistics 6.7 / mystery 0.8 · t3 = bw 78.2 /
logistics 78.9 / mystery 45.4.

**Real, defensible findings:**
- **No-tools Haiku is the best plan *generator* on blocksworld (41%)** — beats GPT-4 (31%) and the open roster.
- **Contamination signal is clean**: Haiku t1 collapses **41% → 0.8%** blocksworld → obfuscated mystery_blocksworld (skill doesn't transfer).
- **Haiku is the weakest *verifier*** among capable models (t3 78% vs GPT-4 95%, Qwen ~88%) — consistent with the single-tool "weaker at judgment" read.

---

## Recommended PR scope ("other changes too")
1. **Fix `_normalize_trajectory`** — canonicalise predicate syntax (`(pred a b)` ↔
   `pred(a, b)` → common token tuple) before equality. ~10 LOC, `pddl_eval/scoring.py`.
   **Does not touch t7.**
2. **Re-grade `simulate` uniformly** — Haiku + Sonnet + open roster — for the real numbers.
3. Open `ISS-###` (simulate normalizer) + dated `paper_notes_discussions.md` entry
   so the simulate-floor claim is revisited with corrected data.
4. PlanBench `t7`: no code change; add the artifact caveat to the analysis/paper.

## Open items
- [x] Verify Sonnet 0/300 `simulate` shows the same artifact — DONE: canon 0→45.0%, anon 0→38.3% (commit `156fb01`); same artifact confirmed.
- [x] Faithful fixed-grader re-grade (exact step+action, not just state-set) — DONE: shipped strict grader, numbers in STATUS table above.
- [ ] **Clean open-roster `simulate` re-run** — NOT a re-grade (disk-unrecoverable: `RESPONSE_SNAPSHOT_LEN=500`, no `gt`) and NOT just the notation fix (open roster is a different failure — unenforced `guided_json` + strict-wrapper sub-artifact + truncation). Requires the Q1 two-metric wrapper-tolerant grader + full-response storage + (think=on) decoupled budget. **GATED — ping before any cluster work.**
- [ ] **Higher token-cap `simulate` re-run** (frontier + roster) to split the residual truncation into budget vs capability. Couples with the line above (same cluster job).
- [ ] Persist full responses + `gt` in trials (raise/remove `RESPONSE_SNAPSHOT_LEN`) so future corpora are re-gradeable offline — hygiene follow-up (ISS-024).
- [ ] Cluster temp cleanup (`~/haiku_eval*.{sh,log}` on slurm) — pending a ping per the cluster-interaction rule.

## File/line anchors
- `pddl_eval/scoring.py` — `_normalize_trajectory` (~134), simulate branch (~438–481).
- `external/LLMs-Planning/plan-bench/utils/text_to_pddl.py` — `text_to_state` (263), `text_to_state_blocksworld` (329), `text_to_plan_blocksworld` (193).
- Haiku single-tool corpus: `results/haiku-frontier/sweep5v2/`; raw batch: `.local/haiku/singletool_nt_canonical/`.
- Haiku PlanBench: `results/haiku-frontier/planbench/`; cluster grade log: `slurm:~/haiku_eval.log`.

---

## Finding 4 — `guided_json` never bound: measured audit (ISS-024(b), 2026-08-15)

**Status: AUDIT ONLY. The fix stays parked** (D4, memo §7). This closes the
audit debt so C1's "artifact audits" component stays internally consistent; it
does not reopen the enforcement fix, which would create a third generation
apparatus citable only after a full no-tools re-sweep.

Finding 1 above asserted from 500-character response heads that `guided_json`
"did NOT bind". That was an impression from a handful of samples. This is the
measurement, over every no-tools row in the two canonical corpora, with the
decoupled control tree measured beside them and never pooled into them.

### What is passed, and where

`runner.evaluate_one` passes `format=TASK_SCHEMAS.get(task)` in the **no-tools
branch only** (both the single-call and the decoupled two-call paths).
`chat_without_tools` forwards it, and `vllm_client.chat` places it at
`extra_body["guided_json"]`. The with-tools branch never passes a schema, so
**no with-tools row is affected by this artifact at all.** All five tasks carry
a schema (`schemas.py`: `SolveResponse`, `ValidateResponse` ×3,
`SimulateResponse`).

On the two-call path the schema is attached to Call 2 only, the answer call, and
never to the free-text reasoning call (`chat.py:466-471`); the stored `response`
is Call-2 text alone. That is what keeps the first-character test below valid on
control rows: the reasoning block cannot be what makes those rows start with
something other than `{`.

The sharpest statement of the defect is at the prompt layer. The `solve` and
`simulate` system prompts instruct the model to "conform to the JSON schema
provided by the format constraint" (`prompts.py:114,138`) — a constraint that
never reached the server. Those two tasks were told to follow a schema they were
never shown. The three `validate_*` prompts never mention JSON at all; they ask
the model to "end your response with exactly one line: VERDICT: VALID or
VERDICT: INVALID", which is what it produced.

### The test, and the two denominators

A working constrained decoder cannot leave the grammar, so any stored response
that is not JSON, or is JSON violating `TASK_SCHEMAS[task]`, is direct proof the
constraint did not bind on that row. Conformance is checked against
`TASK_SCHEMAS[task]` itself, the exact object placed in `extra_body`, not
against the pydantic model, which coerces types the JSON-Schema grammar would
reject (both are computed; they agree on every row).

Two denominators are reported because they answer different questions:

- **provable** — every row on which non-binding is demonstrable. A row whose
  first non-space character is not `{` proves it even when the text is
  truncated, because neither generation truncation nor the storage snapshot can
  change the FIRST character, and a bound decoder's first character is always
  `{`. This is the primary rate.
- **complete rows only** — the strictly conservative denominator, dropping every
  generation-truncated or at-cap row regardless of shape. This subset is
  length-biased (a row survives intact only if it fit under the snapshot cap, and
  short JSON is disproportionately conformant), so it runs higher; it is quoted
  as a bound, not as a fair-sample estimate.

Empty responses carry no evidence either way and are excluded from both.

### Result: zero on validation, under 2% everywhere

**No `validate_*` row emitted JSON of any kind: 0 of 58,581 provable rows across
the two canonical corpora** (0 of 73,655 including the control tree). That is the
claim with no denominator argument available against it. Under a bound decoder
every one of those rows is impossible.

| corpus | no-tools rows | conformant | of provable | of complete only |
|---|---|---|---|---|
| sweep5v2-live | 45,600 | 132 | 0.40% (33,204) | 2.14% (6,158) |
| sweep6-live | 45,600 | 102 | 0.31% (32,670) | 1.69% (6,018) |
| **canonical pooled** | **91,200** | **234** | **0.36% (65,874)** | **1.92% (12,176)** |
| decoupled-rollup (control, never pooled) | 18,240 | 174 | 1.06% (16,448) | 1.32% (13,176) |

The pooled rate is a coverage figure — what share of the no-tools arm was
generated under an effective constraint — and not a measure of constraint
strength, because `validate_*` is 82% of the rows and its prompt never asks for
JSON. The informative rates are per task. Conformance is confined to `solve`
(6.9% sweep5v2-live, 5.5% sweep6-live) and is **0.0% on `simulate` and on all
three `validate_*` tasks in both corpora**.

The decoupled control tree is `RUN_TAG=decoupled-thinkon`: a 4-Qwen think=on
roster on the two-call generation apparatus, with 16,384-character snapshots. It
is reported separately under the corpus-identity rule and is never merged into
either canonical corpus. Its four cells physically ship beside byte-identical
copies of their matched sweep5v2 baseline; the audit deduplicates cells by
content fingerprint and prints every drop, so the baseline copies are counted
once, under `sweep5v2-live`.

The three violation shapes are each individually impossible under a working
constraint, which is what makes this proof rather than inference. They are very
unequal in mass, so each is quoted with its n (canonical corpora):

1. **`validate_*` emit no JSON whatsoever — 58,581 rows, 100% of the provable
   `validate_*` rows in both corpora.** This is the bulk of the evidence. The
   stored snapshot is not usually the bare trailer: of those rows, 9,814 are the
   bare `VERDICT: VALID` string, 1,343 contain the trailer after prose, and
   47,424 contain no trailer at all, because at a 500-character snapshot the
   trailer sits past the cut. The trailer is therefore visible in 11,157 of the
   58,581 rows, 19.0%. The control tree, which stores 16,384 characters, inverts
   that split: 1,757 bare plus 10,256 after prose, so 12,013 of 15,074 rows,
   79.7%, show the trailer. That confirms the missing trailers are a storage
   artifact and not a generation one. The model followed a prompt that asked for
   a verdict line and never mentioned JSON.
2. **`solve` puts a string where the schema requires an array — 22 rows.**
   `SolveResponse.plan` is `list[str]`; the observed shape is
   `{"plan": "(shake ...) (pour ...)"}`. A bound decoder could not emit the
   opening quote.
3. **`simulate` omits the required wrapper — 140 rows** (4 more in the control
   tree). `SimulateResponse` requires `trajectory`; the observed shape is a bare
   `{"step": 0, "action": "", ...}` step object. This is the same
   "strict-wrapper sub-artifact" Finding 1 described, now identified as a
   symptom of non-binding rather than a separate defect. The re-attribution
   rests on those 144 rows and should be quoted with that n.

### Affected is not the same as harmed

Nearly every no-tools row is affected, but the artifact changes a grade on only
two of the five tasks. `format_parse_fail` rate by task:

| group | `solve` | `simulate` | `validate_domain` | `validate_problem` | `validate_plan` |
|---|---|---|---|---|---|
| sweep5v2-live | 29.0% | 40.1% | 0.0% | 0.0% | 0.0% |
| sweep6-live | 26.7% | 37.7% | 0.0% | 0.0% | 0.0% |
| sweep5v2-live, matched 4-cell subset | 5.9% | 13.8% | 0.0% | 0.0% | 0.0% |
| decoupled-rollup (control) | 3.2% | 20.0% | 0.0% | 0.0% | 0.0% |

The validation tasks are insulated **from this grading path**: the v11-v13
prompts restore the `VERDICT:` trailer and `scoring.extract_verdict` reads it
from the full response, so no validation row is lost to a parse failure. That is
why the sweep-4 regression fix mattered so much (`prompts.py` history note) — it
is the reason the validation results, which carry the paper's validation claims,
are not mis-graded by this defect. The claim stops there. What the corpora cannot
show is the counterfactual: a constraint that actually bound would have
suppressed the free-text reasoning and the trailer entirely, so "no row was
mis-graded" is not the same as "the numbers equal what the intended apparatus
would have produced". Do not write the stronger sentence.

The exposure is `solve` and `simulate`, where no equivalent trailer exists.

**On the control tree, compare only against the matched subset.** The
decoupled-vs-canonical gap in the first two rows above is a roster and
reasoning-mode difference, not an apparatus effect: the control is 4 Qwens at
think=on, while the full canonical corpora are 5 models across both modes. The
controlled comparison is the third row against the fourth, the same four cells
re-run on the two-call apparatus. It reads `solve` 5.9% → 3.2% and `simulate`
13.8% → **20.0%**. The budget fix left `solve` roughly where it was and made
`simulate` worse on this metric. An earlier version of this note credited the
budget fix with shrinking both; that reading came from the uncontrolled
comparison and is withdrawn.

### Root cause: hypothesis, not verified

The constraint is sent as `extra_body["guided_json"]`, and vLLM ignores
unrecognized `extra_body` keys silently rather than erroring. The leading
hypothesis is that the pinned server (`vllm/vllm-openai:v0.20.2`) no longer
accepts that field name, since vLLM moved structured decoding to a different
request field after `guided_json` was deprecated. **This is not verified** — it
needs one live probe against a served model, comparing `guided_json` against the
current field name on the same prompt, which is cluster work and therefore
ping-gated. What the corpora prove is that the constraint did not bind. Why it
did not bind is a one-command check whenever a server is next up.

### What this licenses in the paper

Limitations may state: the no-tools arm intended schema-constrained sampling and
the constraint did not take effect; the `solve` and `simulate` prompts therefore
referred the model to a schema it was never shown; no `validate_*` row emitted
JSON at all (0 of 58,581 provable rows across the two canonical corpora), and
pooled conformance is 0.36% of 65,874 provable rows, 1.92% even on the 12,176
rows stored in full; no row was mis-graded, because the `VERDICT:` trailer and
the regex fallback carried validation and `format_parse_fail` is 0.0% on all
three validation tasks; and the exposure is confined to `solve` and `simulate`
at the rates tabulated above.

Lead with the zero, not the percentage. It needs no denominator argument, and the
pooled percentage is partly a task-mix figure.

Three sentences must NOT be written: that the artifact is fixed; that any paper
number is adjusted for it; and that the validation results are what a bound
decoder would have produced (see the counterfactual caveat above — only the
absence of mis-grading is measured). The decoupled control number must never be
pooled with the canonical corpora.

Reproduce: `tools/guided_json_audit.py` (read-only, no arguments). It prints the
cell inventory with every deduplicated cell named, per-cell snapshot caps, both
denominators, the `format_parse_fail` table including the matched subset, and the
n behind each violation shape.
