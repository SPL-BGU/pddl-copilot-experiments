# Pre-registration — frontier output-budget probe (the delivery gap's cause)

**Status:** **RATIFIED 2026-09-08 (Omer; all four §10 lines); AMENDED + ANALYSIS
FROZEN 2026-09-10 (§11).** Design frozen: legs A+B+C+D, budget **64,000** / snapshot
262,144, spend approved (expected ≈$50–65, cap $213), decision rule accepted. No data
exists. The gate-5 review findings are fixed and the analysis hashes are in the §8
freeze record; the first API call still waits on the PR #98 merge — see
`frontier_budget_probe_handoff.md` for the exact sequence.
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
one change — the per-call output-token budget raised from 6,144 to 64,000 (and the
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
| A (primary) | `claude-sonnet-4-6` | with-tools, plain | v11 | 100 (the same 100 (domain, problem) cells as the reference corpus) | 64,000 out-tok/call | expected ≈ $30–35, hard cap $111 | REQUIRED |
| B (tier replication) | `claude-haiku-4-5` | with-tools, plain | v11 | 100 | 64,000 | expected ≈ $10–12, hard cap $37 | recommended |
| C (budget symmetry) | `claude-sonnet-4-6` | no-tools | v11 | 100 | 64,000 | expected ≈ $8–12, hard cap $49 | recommended |
| D (budget symmetry) | `claude-haiku-4-5` | no-tools | v11 | 100 | 64,000 | expected ≈ $3–4, hard cap $16 | recommended |

Legs A/B run through `tools/frontier_runner.py` (SDK Tool Runner, streaming — §2.3).
Legs C/D run through `tools/claude_api_batch.py` (Message Batches, list/2 pricing).
Only `simulate` is run. Nothing else in the job tuple changes: same domains, same
ground-truth cache, same prompt text, same tool suite, same MAX_TOOL_LOOPS=10, same
temperature 0, same caching setup.

> ANSWER (legs): A required. B / C / D — include? (recommended: all three; they are
> cheap and C/D are what licenses any *arm-contrast* sentence at the raised budget,
> because the paper currently asserts both arms share one output-length constraint.)
> **ANSWER (Omer, 2026-09-08): all four legs — "we have budget".**

### 2.2 The one manipulated variable — the budget, and why 64,000

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
current bound ⟨49, 62⟩ and cannot discriminate. **64,000** fits 25 of the 29 (fits ⇔
canonical size ≤ 70,243 chars; the four that do not: tpp/p05 80.5K, drone/p04 82.0K,
depot/p01 126.8K, drone/p05 157.0K canonical chars — these are pre-declared
non-fitting and are reported, never counted against H1). 64,000 is the output-token
ceiling of `claude-haiku-4-5` (Sonnet 4.6 allows 128K); the originally registered
65,536 would have been rejected on legs B and D, so the budget is 64,000 on all four
legs to keep the arms and tiers symmetric (§11 amendment 1; the largest oracle that
fits is 64,327 chars, so the 1,536-token reduction moves no trial across the fit
boundary — re-derived by `classify`, not assumed). It costs ≈$10 more than 32,768 at
the expected outcome. The runner must stream at this budget (the SDK refuses
non-streaming requests whose expected time exceeds 10 minutes, i.e. `max_tokens` >
21,333); §2.3.

> ANSWER (budget): 65,536 as registered? (alternatives considered: 32,768 fits 19/29
> and leaves 10 non-fitting; 16,384 fits 11/29 and is non-discriminating.)
> **ANSWER (Omer, 2026-09-08): 65,536.**
> **AMENDED (Omer, 2026-09-10): 64,000 on all four legs — Haiku 4.5's output ceiling;
> same fit classes (25/29 Sonnet, 17/18 Haiku), re-derived.** See §11.

### 2.3 Apparatus changes (all flags default to the reference behavior; the reference
corpus is reproducible from the same code)

1. `tools/frontier_runner.py`: `--num-predict N` (passes `num_predict_override` into
   `build_jobs`, which already accepts it), `--snapshot-len N` (overrides the 16,384
   slice at `grade()`), `--stream` (passes `stream=True` to
   `client.beta.messages.tool_runner`; each yielded item is a
   `BetaAsyncMessageStream`, resolved with `await item.get_final_message()` — usage,
   stop_reason and content are read from the final message exactly as today). The run
   meta records `num_predict`, `snapshot_len`, `stream`. Every trial row records the
   output tokens of the **final turn** separately (`tokens.completion_final`) next to
   the aggregate over all turns (`tokens.completion`, the cost figure): `max_tokens`
   is a per-call limit, so only the final turn's count says whether the budget bound
   on the turn that stopped (§3.6(a)); the aggregate can exceed the budget on a
   multi-turn trial without any single turn having been cut.
2. `tools/claude_api_batch.py` (legs C/D): `--num-predict N` and `--snapshot-len N`
   with the same semantics.
3. `tools/e2e_regrade.py`: `KNOWN_CAPS = (500, 16384, 262144)`. The probe's snapshot
   is **262,144 characters** (≥ 4× the longest possible 64,000-token answer at 2.7
   chars/token plus prose). `detect_cap` iterates smallest-first, so existing corpora
   are unaffected (unit test added). A probe row of exactly 262,144 chars is censored
   by the standard rule and trips §3.6(a).
4. Results placement: `results/sonnet-frontier/sweep5v2-with-tools-budget64k/`,
   `results/haiku-frontier/sweep5v2-with-tools-budget64k/`,
   `results/sonnet-frontier/sweep5v2-budget64k/`, `results/haiku-frontier/sweep5v2-budget64k/`
   (run tag `budget64k`). These are separate corpora: never pooled with the reference
   cells, never merged into `pooled_e2e_table` rows of the reference corpus. The
   cell-name parser (`_constants.parse_dirname_full` / frontier stem handling in
   `e2e_regrade.process_corpus`) must classify the new stems correctly — §8 item 6.
5. **Run manifest (2026-09-10).** Both runners persist `run_manifest.json` in the
   results directory **before the first API call** (`tools/_run_manifest.py`): model,
   budget (`num_predict`), snapshot length, corpus, prompt variants, loop limit
   (`max_iterations`), streaming, temperature, ground-truth source and hash (content
   hash always; `gt_cache.json` file hash when cached), key-file/limit selection.
   A resume into a directory whose manifest differs on any registered setting is
   refused before any trial is restored or rewritten; a directory that holds trials
   but no manifest is refused outright (its rows have no verifiable settings — a
   fresh `--out` is required). The batch runner writes the manifest at `build` (before
   `submit`) and carries it into the graded results directory.
6. **Manifest as provenance.** `tools/e2e_regrade.py` takes the snapshot cap from the
   cell's manifest when one exists (histogram inference is kept only for legacy
   corpora; each overlay row records `snapshot_cap_source`), so a probe corpus whose
   answers all happen to be short cannot be mis-read as a 16,384-snapshot cell.
   `tools/budget_probe_analysis.py` asserts every §2.4 setting against the probe's
   manifest before reading a single row.

### 2.4 What is held fixed (and is asserted in the frozen code, §8 item 9)

- model ids `claude-sonnet-4-6`, `claude-haiku-4-5`; `prompt_variant == 11`; n = 100
  per leg; the 100 trial keys equal the reference cell's 100 trial keys (set equality,
  asserted); `with_tools` per leg; `task == "simulate"`; corpus = canonical
  (`domains/`); `snapshot_cap == 262144` on every overlay row; the meta's
  `num_predict == 64000`; `MAX_TOOL_LOOPS == 10`; ground truth = the same
  `results/derived/gt_cache.json` (sha256 recorded at freeze). Each of these is
  asserted against the probe directory's `run_manifest.json` (backend, model,
  `with_tools`, tasks = [simulate], corpus = canonical, `domains/`, prompt variants =
  [11], `num_predict` = 64,000, `snapshot_len` = 262,144, `max_iterations` = 10,
  `stream` = true, temperature 0, think off, ground truth cached with the pinned
  file hash, no key-file subset, no limit) and, for the two budget fields, against
  the summary meta as well.
- Grading = the existing overlay pass (`tools/e2e_regrade.py`, D7/D7b/D9 rules, D2b
  strict) — no new grader, no new tolerance. The probe corpus is regraded by the same
  command as every other corpus.

### 2.5 Cost itemization (the ledger line; list prices Sonnet $3/$15, Haiku $1/$5 per
MTok; cache write 1.25×, read 0.1×; batch = list/2)

Measured reference cells: Sonnet WT `simulate` **$23.36** (535K output tokens; cache
write 4.04M, read 0.60M), Haiku WT `simulate` **$6.73**, Sonnet NT v11 `simulate`
$2.89 (batch), Haiku NT v11 $0.98 (batch). Projection for leg A under H1: the input side
is unchanged (≈$15.3); the 30 truncated trials grow from ≈8K to their needed length
(Σ ≈ 0.75M output tokens after capping the two largest at 64,000) → output ≈ 1.05M
tokens ≈ $15.8 → **≈ $31**; rounded expected band $30–35. Hard cap = every trial
emitting 64,000 tokens (100 × 64,000 × $15/M = $96.0 + input ≈ $15.3) = **$111**; a
spend above ≈$45 on leg A is itself a tripwire (§3.6(d)). Legs B/C/D scale the same
way (table §2.1): B cap 100 × 64,000 × $5/M = $32.0 + ≈$5.2 input = **$37**; C cap
100 × 64,000 × $7.5/M = $48.0 + <$1 input = **$49**; D cap 100 × 64,000 × $2.5/M =
$16.0 + <$0.5 = **$16**. **Expected total (A+B+C+D) ≈ $50–65 (unchanged by the
amendment — the cap moved by 1,536 tokens on at most two trials, ≈$0.05); hard cap
$213 (was $217 at 65,536).** The grant covers it; the rule is itemization before spend,
and this section is the itemized line (mirrored into the `paper_notes_discussions.md`
ledger on 2026-09-08; amendment logged 2026-09-10).

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
| LEN-FIT | not OK/OVERFLOW ∧ `done_reason == "length"` ∧ fits(64,000) | 25 | 17 |
| LEN-NOFIT | as LEN-FIT but ¬fits | 4 | 1 |
| SNAP | `done_reason == "end_turn"` ∧ `e2e_strict == "indeterminate"` (the model finished; only the 16K snapshot censored it) | 0 | 2 |
| DECLINE | `done_reason == "end_turn"` ∧ not OK/SNAP ∧ `canon_chars > 8,000` ∧ `response_len < 0.25 × canon_chars` | 3 | 14 |
| ET-FAIL | `done_reason == "end_turn"` ∧ not OK/SNAP/DECLINE (the within-run control) | 19 | 12 |
| OTHER | anything else (Haiku satellite/p03: loop exhausted, `tool_use`) | 0 | 1 |

(Counts computed 2026-09-08 by `python3 tools/budget_probe_analysis.py classify
--tier {sonnet,haiku}` from the reference corpora + `gt_cache.json`, and **re-derived
2026-09-10 under the 64,000 budget with identical counts** — the fit cutoff moved from
71,929 to 70,243 canonical chars and no oracle lies in between
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
6. Output tokens per trial (median, max) — the aggregate over all turns, which is the
   cost figure — and, separately, the final-turn output tokens (median, max, and the
   number of rows at exactly the budget), plus the per-leg measured cost, appended to
   the ledger.
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
LEN-FIT row with `response_len` < 0.9 × 262,144 whose **final-turn** output tokens
(`tokens.completion_final`) ≠ 64,000 (the budget did not bind on the turn that stopped
but the row still truncated: apparatus bug; the aggregate over turns is not the test —
it can exceed the budget with no single turn cut);
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
   --variant 11 --num-predict 64000 --snapshot-len 262144 --stream --use-cached-gt
   --out results/sonnet-frontier/sweep5v2-with-tools-budget64k` (sequential, resumable
   only into the directory whose `run_manifest.json` matches;
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

1. ~~Omer's §10 signatures (legs, budget, spend).~~ DONE 2026-09-08.
2. ~~Ledger line present in `paper_notes_discussions.md` (2026-09-08 entry; §2.5).~~ DONE 2026-09-08 ("later" entry).
3. Code PR (§7 step 1) merged to main — **OPEN** (PR #98; the freeze below hashes the
   branch tip, so the merge must land these bytes unchanged — re-run the sha256 table
   after merging and treat any difference as a deviation).
4. ~~Reference cell key sets extracted and hashed (100 keys each, Sonnet + Haiku);
   `gt_cache.json` sha256 re-checked.~~ DONE 2026-09-10 (freeze record).
5. ~~Reference-row classification (§3.1 table) reproduced by the frozen loader with
   the exact counts above.~~ DONE 2026-09-10 under the amended 64,000 budget
   (`PINNED_CLASS_COUNTS` asserts; counts identical to 2026-09-08).
6. ~~Cell-name parsing: `sweep5v2-with-tools-budget64k` and `sweep5v2-budget64k` parse
   to (cond, run_tag) = (`tools_all_minimal`, `budget64k`) / (`no-tools`, `budget64k`)
   in the overlay and pooled-table path, verified by a unit test.~~ DONE
   (`tests/test_e2e_overlay.py`).
7. ~~**Freeze gate 1 — typed load boundary.**~~ DONE: one loader parses overlay rows
   and raw rows into a typed record; unknown `e2e_strict` / `done_reason` values
   crash; a probe row without `tokens.completion_final` crashes; no truthiness on
   grade fields.
8. ~~**Freeze gate 2 — constants as asserts.**~~ DONE: budget 64,000 (≤ Haiku's
   64,000 ceiling, asserted at import), snapshot 262,144, n = 100, variant 11, model
   ids, corpus, loop limit 10, streaming, the §3.1 class counts, the `gt_cache.json`
   hash, join size 100 — every one asserted against the run manifest and/or the data.
9. ~~**Freeze gate 3 — traceability map.**~~ DONE 2026-09-10 (freeze record below,
   line numbers re-derived from the frozen bytes).
10. ~~**Freeze gate 4 — synthetic fixture.**~~ DONE: `tests/test_budget_probe_analysis.py`
    (54 checks) + `tests/test_frontier_runner.py` (65 checks) + the three manifest-cap
    cases in `tests/test_e2e_overlay.py`.
11. ~~**Freeze gate 5 — adversarial review.**~~ DONE 2026-09-10: four findings —
    (1) 65,536 exceeds Haiku 4.5's 64,000 output ceiling (budget symmetry would have
    broken on legs B/D); (2) resumable runners persisted no settings, so a resume could
    silently mix budgets/snapshots in one corpus; (3) the snapshot cap was inferred from
    the length histogram even for the probe, so a short-answer probe corpus would read
    as a 16,384 cell; (4) the §3.6(a) tripwire compared the AGGREGATE output tokens
    with `<` instead of the final-turn count with `≠`, and omitted the response-length
    clause. All four fixed as ordinary pre-hash edits (§11); regression tests added for
    each.
12. ~~Hash freeze record~~ DONE 2026-09-10 (below). Any later edit to a frozen file =
    declared deviation + re-freeze + regenerated readout.

### Freeze record (2026-09-10)

**Frozen files (sha256 of the bytes on `job2/batch2-budget-probe-prereg` at the
freeze commit; re-verify after the PR #98 merge):**

| file | sha256 | role |
|---|---|---|
| `tools/budget_probe_analysis.py` | `c4dc196875b3a5ffe2e273a1a5ab922b2849db816d7f5bfdbced913bf05fe126` | analysis entry point (frozen) |
| `tools/_run_manifest.py` | `08db2b20be699c818e47e15e589639d4294a40be1a6707b5a1e8c5acf2152c45` | manifest read/validate, imported by the analysis (frozen) |
| `tools/e2e_regrade.py` | `45dcf74a23b5d2b1d79028fd1733a9ba7884ba7f62f84c7ffa4febd100c4b11a` | grader (frozen) |
| `.claude/skills/analyzer/scripts/e2e_overlay.py` | `5dc56cb841e0b285d7c742f1aab9d597a08397699a2c78ddc200dc822ef75350` | overlay aggregator / stem → run tag (frozen) |
| `results/derived/gt_cache.json` | `77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e` | ground truth (pinned; asserted at readout and in the manifest) |
| `tools/frontier_runner.py` | `3d4982b7525523ee126623fe61e0c3b362c68d76edacd0c354311d5655a36a1a` | apparatus, legs A/B (recorded; an edit before the run is a §2.3 apparatus change, not a deviation of the analysis) |
| `tools/claude_api_batch.py` | `a56ccfe2bf24914a656c8b3b7ea012d87d35c8730cffb2f728e3a5df5469e94d` | apparatus, legs C/D (recorded) |
| `tests/test_budget_probe_analysis.py` | `e3cb93ebce1270aef68fa17e2631eece8d21e37bcc875ce6433422231a4c7c36` | gate-4 fixture (recorded) |
| `tests/test_frontier_runner.py` | `74f0f4f9a1a73c5b4b33cef6468147855ee2265ac25ece3c4172a1482833732d` | apparatus regression tests (recorded) |

**Reference cell key sets** (`jq -c .key <cell>/trials.jsonl | grep '"simulate"' | sort | sha256sum`,
100 keys each): Sonnet `results/sonnet-frontier/sweep5v2-with-tools`
`bdaab77325abf8598678a321ae0f489ac6b69689013090b40a3238569b673207`; Haiku
`results/haiku-frontier/sweep5v2-with-tools`
`bf3a6d947a0fbe4ef0f4c7063d9721bdf36ecd1f79da0c027f69a6a1ed2a7db8`. The probe legs must
reproduce these sets exactly (`set(ref) == set(probe)`, L380).

**Reference classification under the frozen code** (`classify --tier {sonnet,haiku}`,
2026-09-10, budget 64,000, fits ⇔ canon ≤ 70,243): Sonnet 49/25/4/0/0/3/19/0, Haiku
52/17/1/1/2/14/12/1 (OK / LEN-FIT / LEN-NOFIT / OVERFLOW / SNAP / DECLINE / ET-FAIL /
OTHER) — equal to the 2026-09-08 pins. Regrading the reference corpora with the frozen
`e2e_regrade.py` reproduces every stored overlay grade byte-for-byte (the only change is
the added `snapshot_cap_source: "inferred"` provenance field). Dry run (§7 step 3)
selects exactly 100 trials per tier under `--num-predict 64000 --snapshot-len 262144
--stream` (verified 2026-09-10).

**Traceability map (gate 3, line numbers of the frozen bytes above):**

| prereg clause | implementation (`tools/budget_probe_analysis.py` unless noted) |
|---|---|
| §2.2 budget 64,000 (≤ Haiku ceiling) / §2.3 snapshot 262,144 / reference 6,144 + 16,384 | constants L49–55 (`assert BUDGET_TOKENS <= HAIKU_MAX_OUTPUT_TOKENS` L52); asserted on the manifest via `expected_probe_manifest()` L208 → `validate_probe_manifest()` L234 (called first, L365), on the summary meta L369–372, and on every overlay row's `snapshot_cap` L181 |
| §2.4 n = 100, variant 11, model id, task = simulate, corpus canonical, loop limit 10, streaming, cached GT with pinned hash, no subset/limit | L56–61, L89; manifest expectation L208–230, checked L234–249 (a missing manifest is a `ValueError`, L239); loader L176–183 (wrong model/variant/cap → `ValueError`); n per leg L379 |
| §2.4 join = the same 100 keys | L380 (`set(ref) == set(probe)`) |
| §2.4 ground truth = pinned `gt_cache.json` | `GT_CACHE_SHA256` L89; file hash asserted L440 before any read (`cmd_readout`) and again as the manifest's `gt_cache_sha256` L225 |
| §2.3 final-turn output tokens recorded separately | `tools/frontier_runner.py` L166 (`out_tok_final`), row field `tokens.completion_final` L235 (and L252 on infra failures; `tools/claude_api_batch.py` L248 single-turn); typed as `Row.completion_final_tokens` L110–111, required on probe rows L184–188 (`final_tokens_required=True`, L377) |
| §2.2 fit rule (0.82 chars→tokens, 10% headroom) | L62–63, `fits()` L254 |
| §3.1 class rules and order (OK → OVERFLOW → LEN-FIT/NOFIT → SNAP → DECLINE → ET-FAIL → OTHER) | `classify()` L258; DECLINE constants L64–65; `class_table()` L275 |
| §3.1 pinned counts (Sonnet 49/25/4/0/0/3/19/0; Haiku 52/17/1/1/2/14/12/1) | `PINNED_CLASS_COUNTS` L83; asserted L382 |
| §3.2 one-sided Fisher exact, α = 0.05, LEN-FIT vs ET-FAIL | `fisher_one_sided()` L286; `conversion()` L296; call site L395–397; `ALPHA` L66 |
| §3.2 verdict bands (H1 ≥ 60% ∧ p < α; kill ≤ 30%; else partial) | L67–68; L399–400 |
| §3.3 secondaries (cell rate + Wilson, OK re-run, DECLINE, LEN-NOFIT, OVERFLOW, SNAP, reasons, aggregate tokens, final-turn tokens) | L417–432 (aggregate `completion_tokens_*` = cost; `completion_final_*` = budget-binding) |
| §3.6(a) censored probe rows | L387–389 |
| §3.6(a) non-binding truncation — `done_reason == "length"` ∧ LEN-FIT ∧ `response_len` < 0.9 × 262,144 ∧ final-turn tokens ≠ 64,000 | `nonbinding_truncations()` L302–317 (`NONBINDING_LEN_FRACTION` L70), called L390 |
| §3.6(b) control > 50% / OK re-run < 40 (Sonnet) < 42 (Haiku) | L69, L90; L406–411 |
| §3.6(c) DECLINE > 50% | L412–414 |
| §3.6(d) spend tripwire | operational (§7 step 4), not code — checked by hand from the runner's cost report (`out=` aggregate column) |
| §3.6(e) constant-column / everywhere-guard | readout-time rule (freeze-protocol skill); no code, reviewer checks the JSON |
| gate 1 typed load boundary (unknown enum → crash; missing field → crash; no truthiness on grades) | `Row` L100–116; `_load_overlay` L119, `_load_raw` L134, `load_cell` L161; `E2E_VALUES`/`DONE_REASONS` L94–96; every grade test is `is True` / `== "indeterminate"` |
| §2.3 item 5 run manifest written before the first API call; resume refused on changed settings or missing provenance | `tools/_run_manifest.py` `ensure_manifest()` L155–182 (`UNCOMPARED_FIELDS` L38, `manifest_diffs()` L138); called by `tools/frontier_runner.py` L382–386 before any trial is restored, and by `tools/claude_api_batch.py` L415 (build, before submit), L442 (submit guard), L521 (grade) |
| §2.3 item 6 snapshot cap from the manifest, inference only for legacy cells | `tools/e2e_regrade.py` `cap_for_cell()` L135–148 (manifest cap below the longest response → `ValueError`), call site L580, `snapshot_cap_source` on every row L593; `KNOWN_CAPS` L132 |
| §2.3 cap registration + stem parsing | `tools/e2e_regrade.py` `KNOWN_CAPS` L132; `.claude/skills/analyzer/scripts/e2e_overlay.py` stem → run_tag L105–108; tests in `tests/test_e2e_overlay.py` |
| gate 4 fixture | `tests/test_budget_probe_analysis.py` (54 checks; Fisher 120/792 and 1/495 hand-computed; traps: censored probe row, duplicate key, missing `snapshot_cap`, unknown grade, wrong meta, drifted counts, 29/30 join, missing manifest, wrong corpus / loop limit / GT hash / stream / budget / snapshot / variants / model / subset, probe row without final-turn tokens, aggregate-above-budget-final-below, final exactly at budget, response-length clause on both sides of 0.9 × cap); `tests/test_frontier_runner.py` (65 checks: final-turn accounting streaming and not, context overflow, manifest fields, fresh write, compatible resume, refused resume per changed field, trials without provenance); `tests/test_e2e_overlay.py` (manifest cap on short responses vs legacy inference, impossible manifest cap refused, at-cap row still censored) |

Known residual (declared at freeze, not a gate-5 finding): the fixture's oracle
traces use the `boolean_fluents` list shape only; the real `gt_cache.json` traces are
the same shape, but a trace stored as `{"trajectory": [...]}` would take the `dict`
branch of `canon_size()` L150–157, which the fixture does not exercise. The pinned
`gt_cache.json` hash guarantees the real traces are the list shape the code was
classified on.

---

## 9. Known limits (carried into Limitations if the probe is quoted)

- Run-to-run nondeterminism: decoding is temperature 0 but unseeded and the multi-turn
  tool loop is not pinned (PlanBench deviation 1: 11/18 re-attempts changed outcome).
  The within-run control (ET-FAIL) and tripwire (b) are the mitigation; the design
  cannot bound it.
- The fit rule (§2.2) is an engineering estimate from the reference corpus; rows it
  misclassifies are visible after the fact (a LEN-NOFIT row that converts, or a
  LEN-FIT row that truncates again at 64,000) and are reported, not re-binned.
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

> ANSWER (10.1 legs — see §2.1 slot): **all four (A, B, C, D). — Omer, 2026-09-08**

> ANSWER (10.2 budget 65,536 / snapshot 262,144 — see §2.2 slot): **65,536. — Omer, 2026-09-08**

> ANSWER (10.3 spend: expected ≈ $50–65 for A+B+C+D, hard cap $217, itemized §2.5):
> **yes. — Omer, 2026-09-08**

> ANSWER (10.4 the §3.2 decision rule and §3.4 bands are accepted as the reading rule
> for this probe, whichever way it comes out): **ok. — Omer, 2026-09-08**

> ANSWER (10.5 amendment — budget 64,000 on all four legs, replacing 65,536; fit
> classes re-derived and unchanged; hard cap $213): **yes — Omer, 2026-09-10** (the
> gate-5 fix list: "Use 64,000 tokens for all four legs").

---

## 11. Amendments (pre-data; every entry is before the first API call)

**2026-09-10 — gate-5 review fixes, applied before the hash (so these are ordinary
edits, not §9-style deviations). Ratified value 65,536 → 64,000.**

1. **Budget 64,000 on all four legs.** `claude-haiku-4-5` caps output at 64,000 tokens;
   the ratified 65,536 would have been rejected on legs B and D and broken the
   budget-symmetry argument (§2.1, §3.3(2)). 64,000 keeps every leg identical. The fit
   cutoff moves from 71,929 to 70,243 canonical chars; `classify` re-derived under the
   new constant gives the same eight counts on both tiers (no oracle lies between the
   two cutoffs — checked, not assumed). Hard caps: A $111, B $37, C $49, D $16, total
   $213; expected bands unchanged. Run tag `budget65k` → `budget64k`.
2. **Run manifest before the first API call** (§2.3 item 5; `tools/_run_manifest.py`).
   Resumes are refused on any changed registered setting and on trials without
   provenance.
3. **Manifest as provenance for grading and readout** (§2.3 item 6): the grader takes
   the snapshot cap from the manifest (inference only for legacy cells); the readout
   asserts every §2.4 setting against the manifest.
4. **Final-turn output tokens recorded separately** (`tokens.completion_final`); the
   §3.6(a) tripwire now implements the registered clause literally (final-turn count
   ≠ budget, with the response-length condition) instead of the candidate's
   aggregate-`<`-budget approximation, which would have stayed silent on a multi-turn
   trial whose total exceeded the budget while its truncated final turn did not.

Regression tests for each item are listed in the gate-4 row of the traceability map.
Suite: `bash tests/verify.sh` — all 16 files pass (2026-09-10).
