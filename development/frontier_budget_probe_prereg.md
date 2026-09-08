# Pre-registration — frontier output-budget probe (the delivery gap's cause)

**Status:** DRAFT 2026-09-08, awaiting Omer's ratification (§10 slots). No data
exists. No spend until §8 gates are discharged and §10 is signed.
**Binding sources:** `job2_delivered_reframe_worknote.md` §7a (design sketch, GO in
principle 2026-09-08); `paper_notes_discussions.md` 2026-09-08 (gates: freeze-protocol
v2 + itemized ledger line before spend; strict delivery grading is not weakened);
`tool_call_vs_final_output_grading.md` (D2b strict, D9c at-cap censor);
`.claude/skills/freeze-protocol/SKILL.md` (v2 gates, binding on §8 item 9).
**Apparatus reference corpus:** `results/sonnet-frontier/sweep5v2-with-tools`
(2026-07-12, `tools/frontier_runner.py`, `anthropic==0.109.2`, `claude-sonnet-4-6`,
MAX_TOOL_LOOPS=10, temperature 0, prompt caching on) and
`results/haiku-frontier/sweep5v2-with-tools` (same design, `claude-haiku-4-5`).

---

## 0. What this is, in plain terms

The paper's Delivery Gap section says the frontier `simulate` gap (the tool runs the
trajectory correctly on 97–99% of trials, the model delivers it correctly on ⟨49, 62⟩ /
⟨52, 64⟩) is "a property of answer length interacting with the output budget". That
is currently a *description* of the failure anatomy (30/100 Sonnet trials stop with
`done_reason=length`), not a causal test. This probe re-runs the same 100 trials with
one change — the per-call output-token budget raised from 6,144 to 65,536 (and the
response snapshot widened so storage cannot censor the gain) — and asks whether the
truncated trials now deliver. If they do, the budget is the cause and the sentence gets
causal support. If they do not, the gap is content- or policy-bound and the sentence is
rewritten to say so. Either answer is publishable; the prereg exists so the answer is
read the same way whichever it is.

What this probe is NOT: it is not a new headline surface, not a re-grading of the
existing cell, not a weakening of strict delivery grading (crediting unrestated tool
results is the τ-bench flaw D2b was decided against), and not an open-roster budget
raise (the 32K smoke failure stands; that config is dead).

---

## 1. Hypotheses

**H1 (budget-caused, the paper's current reading).** Among the Sonnet trials that
failed by output truncation and whose oracle trajectory fits the raised budget, most
deliver correctly once the budget is raised, and they do so at a rate clearly above
the re-run conversion rate of trials that failed *without* truncation (the within-run
control for run-to-run nondeterminism and any general drift).

**H0 (content/format-bound).** Raising the budget does not move the truncated trials
more than it moves the non-truncated failures: the model still fails to hand back a
parseable, exact trajectory when given room, so the gap is not a budget effect.

**H2 (answer-length policy; secondary, Haiku-driven).** A distinct failure family
exists where the model *ends its turn on its own* with an answer far shorter than the
oracle trajectory (a summary or a partial listing instead of the trace). The API does
not expose `max_tokens` to the model, so H2 predicts these rows do NOT convert under
the raised budget. If they convert at a high rate anyway, that is evidence that
run-to-run nondeterminism dominates the paired reading (tripwire §3.6), not evidence
for H1.

The three are decided by separate pre-registered contrasts (§3); no single number
answers all three.

---

## 2. Design

### 2.1 Arms and legs

| leg | model | arm | prompt bank | n | budget | cost (list, see §2.5) | status |
|---|---|---|---|---|---|---|---|
| A (primary) | `claude-sonnet-4-6` | with-tools, plain | v11 | 100 (the same 100 (domain, problem) cells as the reference corpus) | 65,536 out-tok/call | expected ≈ $30–35, hard cap $114 | REQUIRED |
| B (tier replication) | `claude-haiku-4-5` | with-tools, plain | v11 | 100 | 65,536 | expected ≈ $10–12, hard cap $38 | recommended |
| C (budget symmetry) | `claude-sonnet-4-6` | no-tools | v11 | 100 | 65,536 | expected ≈ $8–12, hard cap $49 | recommended |
| D (budget symmetry) | `claude-haiku-4-5` | no-tools | v11 | 100 | 65,536 | expected ≈ $3–4, hard cap $16 | recommended |

Legs A/B run through `tools/frontier_runner.py` (SDK Tool Runner, streaming — §2.3).
Legs C/D run through `tools/claude_api_batch.py` (Message Batches, list/2 pricing).
Only `simulate` is run. Nothing else in the job tuple changes: same domains, same
ground-truth cache, same prompt text, same tool suite, same MAX_TOOL_LOOPS=10, same
temperature 0, same caching setup.

> ANSWER (legs): A required. B / C / D — include? (recommended: all three; they are
> cheap and C/D are what licenses any *arm-contrast* sentence at the raised budget,
> because the paper currently asserts both arms share one output-length constraint.)

### 2.2 The one manipulated variable — the budget, and why 65,536

Reference apparatus: `max_tokens = job[J_NP]` = `DEFAULT_NUM_PREDICT["simulate"]` =
**6,144 tokens per API call** (`pddl_eval/runner.py:98-104`), and the stored response is
truncated to `RESPONSE_SNAPSHOT_LEN` = **16,384 characters** (`runner.py:153`), which is
also the overlay's censoring cap (`tools/e2e_regrade.py` KNOWN_CAPS = (500, 16384)).

The budget must be chosen from the oracle, not from the current failures. Every one of
the 100 `simulate` problems has an exact oracle trajectory in
`results/derived/gt_cache.json`; its canonical compact-JSON size (after
`pddl_eval.scoring._normalize_trajectory`) ranges from 420 to 156,997 characters. On
the reference corpus the delivered response of a successful trial runs ≈1.4–1.85× the
canonical size (pretty-printing plus prose), and the model's JSON packs ≈2.2–2.7
characters per output token. The registered fit rule is therefore:

    tokens_needed(problem) = 1.8 × canon_chars / 2.2 = 0.82 × canon_chars
    fits(problem, budget)  = tokens_needed ≤ 0.9 × budget      (10% headroom)

Under this rule the reference corpus reads (Sonnet): every trial whose oracle is
≤ 8.9K canonical chars was delivered correctly or failed for a non-length reason; from
≈9K upward almost every trial is `done_reason=length`. A 16,384 budget would let only
≈12 of the 29 truncated failures fit — its H1 prediction (≈61) sits *inside* the
current bound ⟨49, 62⟩ and cannot discriminate. **65,536** fits 25 of the 29 (the four
that do not: tpp/p05 80.5K, drone/p04 82.0K, depot/p01 126.8K, drone/p05 157.0K
canonical chars — these are pre-declared non-fitting and are reported, never counted
against H1). 65,536 is also below the SDK's 128K output ceiling for both models and
costs ≈$10 more than 32,768 at the expected outcome. The runner must stream at this
budget (the SDK refuses non-streaming requests whose expected time exceeds 10 minutes,
i.e. `max_tokens` > 21,333); §2.3.

> ANSWER (budget): 65,536 as registered? (alternatives considered: 32,768 fits 20/29
> and leaves 9 non-fitting; 16,384 is non-discriminating.)

### 2.3 Apparatus changes (all flags default to the reference behavior; the reference
corpus is reproducible from the same code)

1. `tools/frontier_runner.py`: `--num-predict N` (passes `num_predict_override` into
   `build_jobs`, which already accepts it), `--snapshot-len N` (overrides the 16,384
   slice at `grade()`), `--stream` (passes `stream=True` to
   `client.beta.messages.tool_runner`; each yielded item is a
   `BetaAsyncMessageStream`, resolved with `await item.get_final_message()` — usage,
   stop_reason and content are read from the final message exactly as today). The run
   meta records `num_predict`, `snapshot_len`, `stream`.
2. `tools/claude_api_batch.py` (legs C/D): `--num-predict N` and `--snapshot-len N`
   with the same semantics.
3. `tools/e2e_regrade.py`: `KNOWN_CAPS = (500, 16384, 262144)`. The probe's snapshot
   is **262,144 characters** (≥ 4× the longest possible 65,536-token answer at 2.7
   chars/token plus prose). `detect_cap` iterates smallest-first, so existing corpora
   are unaffected (unit test added). A probe row of exactly 262,144 chars is censored
   by the standard rule and trips §3.6(a).
4. Results placement: `results/sonnet-frontier/sweep5v2-with-tools-budget65k/`,
   `results/haiku-frontier/sweep5v2-with-tools-budget65k/`,
   `results/sonnet-frontier/sweep5v2-budget65k/`, `results/haiku-frontier/sweep5v2-budget65k/`
   (run tag `budget65k`). These are separate corpora: never pooled with the reference
   cells, never merged into `pooled_e2e_table` rows of the reference corpus. The
   cell-name parser (`_constants.parse_dirname_full` / frontier stem handling in
   `e2e_regrade.process_corpus`) must classify the new stems correctly — §8 item 6.

### 2.4 What is held fixed (and is asserted in the frozen code, §8 item 9)

- model ids `claude-sonnet-4-6`, `claude-haiku-4-5`; `prompt_variant == 11`; n = 100
  per leg; the 100 trial keys equal the reference cell's 100 trial keys (set equality,
  asserted); `with_tools` per leg; `task == "simulate"`; corpus = canonical
  (`domains/`); `snapshot_cap == 262144` on every overlay row; the meta's
  `num_predict == 65536`; `MAX_TOOL_LOOPS == 10`; ground truth = the same
  `results/derived/gt_cache.json` (sha256 recorded at freeze).
- Grading = the existing overlay pass (`tools/e2e_regrade.py`, D7/D7b/D9 rules, D2b
  strict) — no new grader, no new tolerance. The probe corpus is regraded by the same
  command as every other corpus.

### 2.5 Cost itemization (the ledger line; list prices Sonnet $3/$15, Haiku $1/$5 per
MTok; cache write 1.25×, read 0.1×; batch = list/2)

Measured reference cells: Sonnet WT `simulate` **$23.36** (535K output tokens; cache
write 4.04M, read 0.60M), Haiku WT `simulate` **$6.73**, Sonnet NT v11 `simulate`
$2.89 (batch), Haiku NT v11 $0.98 (batch). Projection for leg A under H1: the input side
is unchanged (≈$15.3); the 30 truncated trials grow from ≈8K to their needed length
(Σ ≈ 0.75M output tokens after capping the two largest at 65,536) → output ≈ 1.05M
tokens ≈ $15.8 → **≈ $31**; rounded expected band $30–35. Hard cap = every trial
emitting 65,536 tokens (100 × 65,536 × $15/M + input) = **$114**; a spend above ≈$45
on leg A is itself a tripwire (§3.6(d)). Legs B/C/D scale the same way (table §2.1).
**Expected total (A+B+C+D) ≈ $50–65; hard cap $217.** The grant covers it; the rule is
itemization before spend, and this section is the itemized line (mirrored into the
`paper_notes_discussions.md` ledger on 2026-09-08).

---

## 3. Analysis plan (locked before data)

### 3.1 Surfaces and rows

Delivered = `e2e_strict` from the overlay, both corpora. The unit is the (domain,
problem) trial key; the reference corpus and the probe corpus are joined on it (100
pairs per leg; a join with ≠100 pairs halts the readout). Each reference row is
classified ONCE, from the reference corpus only, before any probe data is read:

| class | rule (reference row) | Sonnet n | Haiku n |
|---|---|---|---|
| OK | `e2e_strict == True` | 49 | 52 |
| OVERFLOW | raw `error` contains "prompt is too long" (context window, not output budget) | 0 | 1 |
| LEN-FIT | not OK/OVERFLOW ∧ `done_reason == "length"` ∧ fits(65,536) | 25 | 17 |
| LEN-NOFIT | as LEN-FIT but ¬fits | 4 | 1 |
| SNAP | `done_reason == "end_turn"` ∧ `e2e_strict == "indeterminate"` (the model finished; only the 16K snapshot censored it) | 0 | 2 |
| DECLINE | `done_reason == "end_turn"` ∧ not OK/SNAP ∧ `canon_chars > 8,000` ∧ `response_len < 0.25 × canon_chars` | 3 | 14 |
| ET-FAIL | `done_reason == "end_turn"` ∧ not OK/SNAP/DECLINE (the within-run control) | 19 | 12 |
| OTHER | anything else (Haiku satellite/p03: loop exhausted, `tool_use`) | 0 | 1 |

(Counts computed 2026-09-08 by `python3 tools/budget_probe_analysis.py classify
--tier {sonnet,haiku}` from the reference corpora + `gt_cache.json`
(sha256 `77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e`); the rules
are the `classify()` function and the counts are pinned as `PINNED_CLASS_COUNTS`
asserts, so a re-derivation that disagrees fails loudly rather than silently
re-binning. Sonnet LEN-FIT + LEN-NOFIT = 29 = the memo's "29 output-budget
truncations"; the 30th `length` row, delivery/p01, delivered the full trace before the
cut and is OK-class. Classification order is the row order of the table.)

### 3.2 Primary endpoint and test (leg A)

Conversion = probe-row `e2e_strict == True`. Primary contrast: conversion rate in
LEN-FIT versus conversion rate in ET-FAIL (the non-truncated failures re-run under the
identical apparatus, which absorbs run-to-run nondeterminism and any general drift).

- Test: one-sided Fisher exact on the 2×2 (LEN-FIT vs ET-FAIL × converted vs not),
  α = 0.05, direction LEN-FIT > ET-FAIL. Reported with both rates, their Wilson 95%
  intervals, and the risk difference.
- **H1 supported** iff p < 0.05 AND LEN-FIT conversion ≥ 60% (≥ 15/25).
- **H0 supported (kill)** iff LEN-FIT conversion ≤ 30% (≤ 7/25), regardless of p.
- Otherwise **partial**: reported as "the budget accounts for part of the gap", with the
  conversion rate quoted; no causal sentence.

Power note (pre-registered, not a gate): with 25 vs 19 and true rates 0.65 vs 0.20,
the one-sided Fisher test rejects at α = 0.05 with power ≈ 0.85.

### 3.3 Secondary endpoints (never revise the §3.2 verdict)

1. Cell-level delivered rate of the probe corpus, exact point + Wilson CI (censoring is
   expected to be zero by construction; if not, §3.6(a)). Quoted next to the frozen
   reference bound ⟨49, 62⟩; H1 predicts a point ≥ 65. Descriptive only.
2. Budget-symmetry (legs C/D present): the availability contrast WT − NT at the raised
   budget, both arms exact, Wilson intervals; licensed for the Delivery Gap section as
   "at a budget the trajectory fits, availability lift on `simulate` is Δ [CI]". If C/D
   are absent, no arm-contrast sentence is written at the raised budget.
3. Tier replication (leg B): the §3.2 contrast on Haiku (LEN-FIT 17 vs ET-FAIL 12),
   same rule, reported as confirmatory-or-not for the "identical at both tiers" claim.
4. H2 (leg B primary, leg A descriptive): DECLINE conversion rate. Prediction: ≤ 30%.
   Reported with a Wilson interval; no test (the class is a negative control, §3.6(c)).
5. Failure anatomy of the probe corpus (`e2e_reason` distribution) next to the
   reference anatomy, so the reader sees where the residual mass went.
6. Output tokens per trial (median, max) and the per-leg measured cost, appended to the
   ledger.
7. SNAP rows (Haiku, 2): the model finished on its own inside the 6K budget and only
   storage censored the answer; predicted to convert under the wider snapshot alone.
   Reported; excluded from both the LEN-FIT and control groups.

### 3.4 Pre-registered predictions (bands)

| quantity | H1 band | kill band |
|---|---|---|
| Sonnet LEN-FIT conversion | ≥ 60% | ≤ 30% |
| Sonnet ET-FAIL conversion (control) | ≤ 30% | — (a control value > 50% trips §3.6(b)) |
| Sonnet cell delivered (exact) | ≥ 65 | ≤ 62 (inside the old bound) |
| Haiku LEN-FIT conversion | ≥ 60% | ≤ 30% |
| Haiku DECLINE conversion | ≤ 30% (H2) | > 50% trips §3.6(c) |
| LEN-NOFIT / OVERFLOW rows | reported, not scored | — |

### 3.5 Interpretation language (pre-drafted; only the bracketed value changes)

- H1 supported: *"Raising the output budget from 6K to 64K tokens on the same 100
  trials converted [k]/25 of the budget-fitting truncated failures (vs [j]/19 of the
  non-truncated failures re-run under the same apparatus; Fisher p = [p]), taking the
  delivered rate from ⟨49, 62⟩ to [x] [CI]. The gap is budget-shaped: the tool's
  trajectory reaches the answer once the answer has room."*
- Kill: *"Raising the output budget to 64K tokens converted only [k]/25 of the
  truncated failures (control [j]/19); the delivered rate stayed at [x] [CI]. The
  trajectory does not reach the answer even with room: the gap is content-bound, not
  budget-bound, and 'budget-shaped' is withdrawn."*
- Partial: quote both rates, no causal clause; the paper keeps the descriptive anatomy
  sentence and adds the conversion fraction.
- H2: *"[m]/14 trials in which Haiku ended its turn with a summary instead of the trace
  converted; the model's own answer-length policy, which the budget cannot reach, is a
  second, smaller component of the gap."*

The probe result lands as one or two sentences in the Delivery Gap subsection (and the
matching Limitations/Future-Work clause), never as a new table row on the headline
surface. The reference cells' frozen values do not change.

### 3.6 Readout-time tripwires (halt and trace before any sentence is written)

(a) any probe row censored at 262,144 chars, or any `done_reason == "length"` in a
LEN-FIT row with `response_len` < 0.9 × 262,144 whose output tokens ≠ 65,536 (the
budget did not bind but the row still truncated: apparatus bug);
(b) ET-FAIL control conversion > 50% or OK-class re-run success < 40/49 (Sonnet) /
< 42/52 (Haiku) —
run-to-run nondeterminism dominates; the §3.2 test is still reported but the
"same 100 trials" language is replaced by "a re-run of the same 100 trials";
(c) DECLINE conversion > 50% on Haiku — same flag as (b);
(d) leg A spend > $45 or any leg > 1.5× its expected band — stop the leg, reconcile
tokens before continuing;
(e) a constant output column, a guard firing on every row, or a rate outside the
reference corpus band that nobody predicted — audit before narrating (freeze-protocol
readout rule).

---

## 4. What this prereg forbids

- No re-grading, re-tolerance, or D2b change on the reference cells; the probe uses
  the identical grader.
- No pooling of probe and reference rows into one cell; no "resolved" reading of the
  reference bound (the reference stays ⟨49, 62⟩ in every table).
- No open-roster budget raise on the back of this result (the 32K smoke failure is a
  design choice, not a gap).
- No claim about *tool-verified* changing (it is 99/100 already; the probe measures
  delivery).
- No frontier headline number moves; NUMBERS.md gains one clearly-labeled
  "budget probe" block only after the readout is ratified.

---

## 5. Claim-licensing map

| paper location | licensed sentence class | requires |
|---|---|---|
| Results › Delivery Gap (after the "property of answer length interacting with the output budget" sentence) | H1 / kill / partial sentence from §3.5 | leg A readout ratified |
| same paragraph, tier clause | "at both tiers" or "at the Sonnet tier only" | leg B |
| Results › Delivery Gap, arm-contrast clause | "at a budget the trajectory fits, availability lift is Δ" | legs C+D |
| Limitations (storage/budget paragraph) | "the budget dependence is measured, not assumed" | leg A |
| Future Work ("give the answer its own room") | keep / rewrite per verdict | leg A |
| Discussion executive summary | one clause, verdict-conditional | leg A |

---

## 6. Second-tier and no-tools legs — decisions

- Leg B (Haiku): the paper's "identical at both tiers" claim is the reason to run it;
  without B the probe supports a Sonnet-only causal sentence.
- Legs C/D (no-tools): the reference NT simulate cells are bounds (Sonnet v11 ⟨34, 53⟩,
  19/100 censored at 16K; 89/300 `length` across v11–13), so the unaided model is also
  budget-bound. Running C/D makes both arms exact at one budget and is the only way to
  say anything about the *availability* lift at the raised budget. They are cheap
  (batch pricing). If they are skipped, §3.3(2) is struck and the paper's arm-contrast
  language on frontier `simulate` stays exactly as batch 1 wrote it.

---

## 7. Operational plan (nothing here touches the cluster; all local + API)

1. Code PR: runner flags (§2.3 items 1–2), KNOWN_CAPS (item 3) + unit tests, the
   analysis entry point `tools/budget_probe_analysis.py` + `tests/test_budget_probe_analysis.py`
   (§8 items 7–9). Reviewed and merged before any API call.
2. Discharge §8. Freeze (hash) the analysis entry point per freeze-protocol v2.
3. Dry run: `frontier_runner.py --dry-run --tasks simulate --variant 11` must select
   exactly 100 trials whose keys equal the reference cell's keys.
4. Leg A live: `python3 tools/frontier_runner.py --model claude-sonnet-4-6 --tasks simulate
   --variant 11 --num-predict 65536 --snapshot-len 262144 --stream --use-cached-gt
   --out results/sonnet-frontier/sweep5v2-with-tools-budget65k` (sequential, resumable;
   expected wall time 2–4 h at 65K-token answers). Cost check after the first 20 trials
   against §2.5 (tripwire (d)).
5. Legs B, C, D per §10 answers (C/D through `claude_api_batch.py build/submit/poll/grade`
   with the same two flags).
6. Regrade: `python3 tools/e2e_regrade.py results/sonnet-frontier results/haiku-frontier`
   (the standard command; new cells appear alongside the old ones, run-tagged).
7. Readout: `python3 tools/budget_probe_analysis.py` → `results/derived/budget_probe/readout.md`
   + JSON; tripwires evaluated by the script before it prints any verdict.
8. Ratify the readout (Omer); then the one-or-two-sentence paper edit on `paper/aaai27`,
   NUMBERS.md probe block, ledger line with measured cost.

---

## 8. Blocking prerequisites (every item blocks the first API call)

1. Omer's §10 signatures (legs, budget, spend).
2. Ledger line present in `paper_notes_discussions.md` (2026-09-08 entry; §2.5).
3. Code PR (§7 step 1) merged to main.
4. Reference cell key sets extracted and hashed (100 keys each, Sonnet + Haiku);
   `gt_cache.json` sha256 = `77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e`
   (recorded 2026-09-08; re-checked at freeze).
5. Reference-row classification (§3.1 table) reproduced by the frozen loader with the
   exact counts above; counts are `assert`s in the code (`PINNED_CLASS_COUNTS`, done
   2026-09-08 — the freeze candidate already refuses to run on drifted counts).
6. Cell-name parsing: `sweep5v2-with-tools-budget65k` and `sweep5v2-budget65k` parse
   to (cond, run_tag) = (`tools_all_minimal`, `budget65k`) / (`no-tools`, `budget65k`)
   in the overlay and pooled-table path, verified by a unit test, so the probe never
   masquerades as the reference cell.
7. **Freeze gate 1 — typed load boundary.** One loader parses overlay rows and raw
   rows into a typed record; unknown `e2e_strict` / `done_reason` values crash; no
   truthiness on grade fields (`"indeterminate"` is truthy).
8. **Freeze gate 2 — constants as asserts.** Budget 65,536, snapshot 262,144, n = 100,
   variant 11, model ids, the §3.1 class counts, KNOWN_CAPS membership, join size 100.
9. **Freeze gate 3 — traceability map.** Every §3 clause → `file:line`, recorded in the
   freeze record below; a clause with no implementation blocks the freeze.
10. **Freeze gate 4 — synthetic fixture.** ~30-row reference + probe mini-corpus with
    planted traps (a censored row, an overflow row, a DECLINE row, a duplicate key, a
    row missing `snapshot_cap`, a known Fisher 2×2 with hand-computed p) under
    `tests/`; the pipeline reproduces the hand-computed numbers and refuses the
    malformed rows.
11. **Freeze gate 5 — adversarial review** of the freeze candidate by a different
    session/model (`/code-review` high or stronger) with the traceability map in
    context; findings fixed before the hash.
12. Hash freeze record (sha256 of `tools/budget_probe_analysis.py`,
    `tools/e2e_regrade.py`, `.claude/skills/analyzer/scripts/e2e_overlay.py`,
    `results/derived/gt_cache.json`) appended below; any later edit = declared
    deviation + re-freeze + regenerated readout.

### Freeze record

*(hash table empty until §8 items 7–12 are discharged)*

**Candidate traceability map (gate 3, drafted 2026-09-08 with the freeze candidate;
line numbers as of that draft — re-derive at freeze time, do not trust from memory):**

| prereg clause | implementation (`tools/budget_probe_analysis.py`) |
|---|---|
| §2.2 budget 65,536 / §2.3 snapshot 262,144 / reference 6,144 + 16,384 | constants L44–47; asserted on the probe meta L274–275 and on every overlay row's `snapshot_cap` L161 |
| §2.4 n = 100, variant 11, model id, task = simulate | L48–49; loader L155–163 (wrong model/variant/cap → `ValueError`); L269 (n per leg) |
| §2.4 join = the same 100 keys | L270 (`set(ref) == set(probe)`) |
| §2.4 ground truth = pinned `gt_cache.json` | `GT_CACHE_SHA256` L74; asserted L328 before any read |
| §2.2 fit rule (0.82 chars→tokens, 10% headroom) | L51–52, `fits()` L179 |
| §3.1 class rules and order (OK → OVERFLOW → LEN-FIT/NOFIT → SNAP → DECLINE → ET-FAIL → OTHER) | `classify()` L183; DECLINE constants L53–54; `class_table()` L200 |
| §3.1 pinned counts (Sonnet 49/25/4/0/0/3/19/0; Haiku 52/17/1/1/2/14/12/1) | `PINNED_CLASS_COUNTS` L68; asserted L277 |
| §3.2 one-sided Fisher exact, α = 0.05, LEN-FIT vs ET-FAIL | `fisher_one_sided()` L211; `conversion()` L221; call site L288–292; `ALPHA` L55 |
| §3.2 verdict bands (H1 ≥ 60% ∧ p < α; kill ≤ 30%; else partial) | L56–57; L293 |
| §3.3 secondaries (cell rate + Wilson, OK re-run, DECLINE, LEN-NOFIT, OVERFLOW, SNAP, reasons, tokens) | L309–321 |
| §3.6(a) censored probe rows / non-binding truncation | L281–287 |
| §3.6(b) control > 50% / OK re-run < 40 (Sonnet) < 42 (Haiku) | L58, L75; L302–305 |
| §3.6(c) DECLINE > 50% | L306–308 |
| §3.6(d) spend tripwire | operational (§7 step 4), not code — checked by hand from the runner's cost report |
| §3.6(e) constant-column / everywhere-guard | readout-time rule (freeze-protocol skill); no code, reviewer checks the JSON |
| gate 1 typed load boundary (unknown enum → crash; no truthiness on grades) | `Row` L79–99; `_load_overlay` L102, `_load_raw` L117, `load_cell` L144; `E2E_VALUES`/`DONE_REASONS` L77–79; every grade test is `is True` / `== "indeterminate"` |
| gate 4 fixture | `tests/test_budget_probe_analysis.py` (29 checks; Fisher 120/792 and 1/495 hand-computed; traps: censored probe row, duplicate key, missing `snapshot_cap`, unknown grade, wrong meta, drifted counts, 29/30 join) |
| §2.3 cap registration + stem parsing | `tools/e2e_regrade.py` `KNOWN_CAPS`; `.claude/skills/analyzer/scripts/e2e_overlay.py` stem→run_tag; tests in `tests/test_e2e_overlay.py` (`test_detect_cap_probe_262144`, `test_load_e2e_cells_probe_stems_get_their_own_run_tag`) |

Known gap for the reviewer (gate 5): the fixture's oracle traces use the
`boolean_fluents` shape only; the real `gt_cache.json` traces are the same shape, but a
trace stored as `{"trajectory": [...]}` would take the `dict` branch of
`canon_size()` L133, which the fixture does not exercise.

---

## 9. Known limits (carried into Limitations if the probe is quoted)

- Run-to-run nondeterminism: decoding is temperature 0 but unseeded and the multi-turn
  tool loop is not pinned (PlanBench deviation 1: 11/18 re-attempts changed outcome).
  The within-run control (ET-FAIL) and tripwire (b) are the mitigation; the design
  cannot bound it.
- The fit rule (§2.2) is an engineering estimate from the reference corpus; rows it
  misclassifies are visible after the fact (a LEN-NOFIT row that converts, or a
  LEN-FIT row that truncates again at 65,536) and are reported, not re-binned.
- One budget point, not a dose–response curve. A curve (16K / 32K / 64K) would cost
  ≈3× and is not needed to answer the causal question as posed; it is a follow-up if
  the partial band is hit.
- Prompt caching cost accounting follows the SDK usage fields exactly as in the
  reference run; the probe does not change the cache layout.
- The probe changes only `max_tokens`; the model's context window, tool results and
  loop cap are unchanged. depot/p01 (Haiku) will overflow the context again by
  construction and is classified OVERFLOW in advance.

---

## 10. Ratification

> ANSWER (10.1 legs — see §2.1 slot):

> ANSWER (10.2 budget 65,536 / snapshot 262,144 — see §2.2 slot):

> ANSWER (10.3 spend: expected ≈ $50–65 for A+B+C+D, hard cap $217, itemized §2.5):

> ANSWER (10.4 the §3.2 decision rule and §3.4 bands are accepted as the reading rule
> for this probe, whichever way it comes out):
