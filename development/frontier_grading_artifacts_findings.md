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

### Open vLLM roster — affected but NOT re-gradeable from disk (2026-06-23)
The same `_normalize_trajectory` graded the open roster, and their 500-char
response snapshots confirm the **same `(ontable shaker1)` s-expr format** → the
syntax artifact applies to them too. BUT their as-shipped 0% is dominated by a
*different* failure that fires **before** the comparison:

| open model (no-tools simulate, n=600) | as-shipped | dominant failures |
|---|--:|---|
| Qwen3.5-0.8B | 0.0% | truncated 359, parse_fail 241 |
| Qwen3.5-4B | 0.0% | truncated 406, parse_fail 194 |
| Qwen3.5-9B | 0.0% | truncated 354, parse_fail 246 |
| Qwen3.6-35B | 0.0% | parse_fail 290, truncated 284 |
| gemma-4-26B | 0.0% | truncated 369, parse_fail 231 |

So for the open roster the syntax bug is a *ceiling they rarely reach* — ~60%
truncate (long trajectories exceed the token cap) and ~40% `format_parse_fail`.
**Critically, the open corpus CANNOT be re-graded from disk:**
`RESPONSE_SNAPSHOT_LEN=500` (`pddl_eval/runner.py:133`) kept only a 500-char
snapshot, and `gt` is not stored in trials — so the full trajectory ↔ oracle
comparison is unrecoverable. The true open-model simulate number is **unknown**
and needs a **re-run** with (a) the syntax fix AND (b) a higher token cap (the
trajectories are long; truncation bites every model — 30% even for Sonnet).

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
- [ ] Verify Sonnet 0/300 `simulate` shows the same artifact (raw batch responses local; no spend, no cluster).
- [ ] Faithful fixed-grader re-grade (exact step+action, not just state-set) for the precise corrected number.
- [ ] Uniform `simulate` re-grade across the open roster.
- [ ] Cluster temp cleanup (`~/haiku_eval*.{sh,log}` on slurm) — pending a ping per the cluster-interaction rule.

## File/line anchors
- `pddl_eval/scoring.py` — `_normalize_trajectory` (~134), simulate branch (~438–481).
- `external/LLMs-Planning/plan-bench/utils/text_to_pddl.py` — `text_to_state` (263), `text_to_state_blocksworld` (329), `text_to_plan_blocksworld` (193).
- Haiku single-tool corpus: `results/haiku-frontier/sweep5v2/`; raw batch: `.local/haiku/singletool_nt_canonical/`.
- Haiku PlanBench: `results/haiku-frontier/planbench/`; cluster grade log: `slurm:~/haiku_eval.log`.
