# Pre-registration: iss024d-e2e vs sweep5v2-live parity check

**Written 2026-07-12, before any success-rate comparison was computed.** Registered
while jobs are in flight: 19293221 tasks 0 (0.8B) and 3 (35b) COMPLETED on the cluster;
4B and 9B RUNNING; gemma job 19314599 RUNNING (submitted today). Disclosure of prior
data contact: the 0.8B corpus was inspected for row counts and per-variant counts only
(9120 rows, 1520/variant v11-16); no success rate, failure rate, or any outcome metric
of any iss024d cell has been computed or seen at registration time, for any model.

## Purpose

iss024d-e2e is the with-tools rerun under 16K response snapshots. Its e2e numbers are
usable as the paper's exact with-tools delivered-answer estimates only if the rerun is
generation-equivalent to sweep5v2-live on the metric both corpora measure exactly:
**tool-verified success** (stored uncapped in both; unaffected by the snapshot cap).
The Qwen cells carry one generative delta (`--reasoning-parser none`); the gemma cell
carries none (gemma4 never had a reasoning parser), making gemma the **negative
control**: a gemma parity failure can only be sampling/serving nondeterminism, which
calibrates the noise floor for interpreting Qwen failures.

## Primary endpoint

Per-cell Δ = p(iss024d) − p(sweep5v2-live) on **tool-verified success**, neutral bank
(v11-13 pooled), per model × task:

- Qwen primary set: 4 models × 5 tasks = 20 comparisons.
- Gemma control set: 1 model × 5 tasks = 5 comparisons, evaluated FIRST.

**Equivalence criterion (TOST):** a cell PASSES if the 90% Newcombe (Wilson-score)
CI for Δ lies entirely within **±5pp** (equivalent to two one-sided tests at α = .05).
The margin is a design choice: with per-cell neutral-bank n in the several-hundreds to
~2.7k range, the CI half-width is ≈2–4pp at mid-range p, so ±5pp is powered to pass
under true equality while still catching shifts that would matter to any verdict cell.

> ANSWER (margin OK / different):

## Decision rule (fixed in advance)

1. **Gemma control first.** Expected: 5/5 pass. If any gemma cell fails, set the
   empirical noise floor F = max |Δ̂| over gemma cells, and evaluate Qwen failures
   against F before attributing anything to the parser delta.
2. **Job-level parity holds** if ≥18/20 Qwen cells pass AND no Qwen cell has
   |Δ̂| > 10pp.
3. **Per-cell consequence:** a failing cell's iss024d e2e number is NOT used as a
   headline paper number until a mechanism decomposition is done (secondary endpoints
   below) and written up; all failures are reported regardless of convenience.
4. **No re-derivation:** if parity fails broadly (rule 2 violated), iss024d e2e numbers
   are reported as a separate-apparatus replication, clearly labeled, never as
   "the sweep5v2 cells resolved". No margin adjustment after unblinding.

## Secondary endpoints (mechanism, not gates)

- format_parse_fail rate Δ per cell (the parser-off change acts exactly here).
- truncated/censoring-category rate Δ per cell.
- Per-variant heterogeneity across the full v11-16 bank (descriptive only; steered
  v14-16 are diagnostic-only per paper_notes 2026-07-12).

## Analysis plan

One script, `tools/iss024d_parity.py` (to be written), reading both corpora from disk
and emitting the 25-cell table with Δ, 90% Newcombe CI, pass/fail, plus the secondary
tables. Run once per completed cell as they land; the decision rule is only evaluated
on the complete 25-cell table. Corpora are never pooled (corpus-identity rule).

## Interpretation language (bound by paper_notes 2026-07-12)

Pass or fail, iss024d numbers are "independent rerun estimates under full-response
storage", never "the resolved exact value of" a censored sweep5v2 cell. Exact e2e is
think=on-scoped; think=off with-tools e2e remains bounds-only.
