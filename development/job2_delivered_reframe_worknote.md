# Job 2 worknote — the delivered reframe: derived grounding + edit spec (2026-09-07)

**What this is.** The frozen analytical grounding for the D-J2 = D2 full reframe
(`journal_decisions_memo.md` §3, accepted 2026-07-24) as it is written into
`paper/main.tex` on `paper/aaai27`. Every delivered-surface verdict quoted in the
rewritten Results derives from the table below, which is computed mechanically from
the canonical pooled overlay table
(`results/derived/e2e_overlay/pooled_e2e_table.csv`, regenerated 2026-07-17 after
the PR #91 review fixes). Doc-only working-tree artifact; the tex commit cites it.

**Binding specs while writing:** memo §3 (surface, value shapes, per-corpus rules,
prohibited claims, notation gate), `tool_call_vs_final_output_grading.md` (D2b
strict headline, delegation_terminal), NUMBERS.md (frontier rows),
`sonnet_wt_vs_haiku_e2e_memo.md` (frontier ladder + transcription gap),
`results/derived/iss024d_parity_report.md` (separate-apparatus labeling).

## 1. The verdict rule (delivered surface, strict bounds)

Each with-tools sweep5v2/sweep6 cell is a bound
`[ok_strict/n, (ok_strict+censored)/n]` (D6=A: censored-at-snapshot rows are
indeterminate). The availability verdict takes the claim-adverse end of each bound
and puts a Wilson 95% interval on it:

- **FAVORABLE** iff Wilson_low(WT ok_strict, n) > Wilson_high(NT ok+cens, n)
  (i.e., the lift survives even if every censored with-tools row failed and every
  censored no-tools row succeeded);
- **AGAINST** iff Wilson_high(WT ok+cens, n) < Wilson_low(NT ok_strict, n);
- otherwise **UNDECIDED** when censored mass could flip the call, **NS** when both
  cells are effectively exact and simply overlap.

Reproduction: the exact script is inlined in §6; input is the pooled CSV.

## 2. Derived verdict table — sweep5v2-live, neutral bank v11–13, availability lift

```
== think=off ==
model           task              NT bound       WT bound       verdict  (WT-worst Wilson / NT-best Wilson / censoring)
Qwen3_5_0_8B    validate_domain   80.8           43.9-45.8      AGAINST
Qwen3_5_0_8B    validate_problem  51.2           4.0-5.8        AGAINST
Qwen3_5_0_8B    validate_plan     49.8           13.1-20.9      AGAINST
Qwen3_5_0_8B    solve             0.0            3.0-9.7        FAVORABLE
Qwen3_5_0_8B    simulate          0.0-62.3       0.0-8.7        UNDECIDED
Qwen3_5_4B      validate_domain   19.2           84.2-100.0     FAVORABLE
Qwen3_5_4B      validate_problem  56.5           48.3-85.7      UNDECIDED
Qwen3_5_4B      validate_plan     74.0           32.6-51.2      AGAINST
Qwen3_5_4B      solve             7.7            11.7-29.0      UNDECIDED
Qwen3_5_4B      simulate          0.0-100.0      0.0-24.3       UNDECIDED
Qwen3_5_9B      validate_domain   25.6           99.7-100.0     FAVORABLE
Qwen3_5_9B      validate_problem  65.7           92.2-95.3      FAVORABLE
Qwen3_5_9B      validate_plan     79.7           80.8-87.2      UNDECIDED
Qwen3_5_9B      solve             10.7           26.0-58.7      FAVORABLE*   (*knife-edge, see §3b)
Qwen3_5_9B      simulate          0.0-87.3       0.0-39.0       UNDECIDED
gemma4_26b-a4b  validate_domain   77.8           93.3-98.1      FAVORABLE
gemma4_26b-a4b  validate_problem  74.8           84.3-99.8      FAVORABLE*   (*fails √2.7 inflation, §3c)
gemma4_26b-a4b  validate_plan     87.8           6.6-99.6       UNDECIDED    (c2790/3000)
gemma4_26b-a4b  solve             7.7            14.3-35.3      UNDECIDED
gemma4_26b-a4b  simulate          0.0-100.0      0.0-27.3       UNDECIDED
qwen3_6_35b     validate_domain   67.8           91.9-99.2      FAVORABLE
qwen3_6_35b     validate_problem  75.7           74.7-97.8      UNDECIDED
qwen3_6_35b     validate_plan     90.9           55.0-90.3      UNDECIDED
qwen3_6_35b     solve             9.3            12.7-53.7      UNDECIDED
qwen3_6_35b     simulate          0.0-90.3       0.0-39.0       UNDECIDED
```

think=on table computed identically (in the script output, scratchpad); on-mode is
robustness-only in the paper and stays budget-confounded, so it is not re-quoted
cell-by-cell.

**Headline-set (≥9B, think=off) summary on the delivered surface:**

| task | delivered availability verdicts (9B / gemma / 35b) |
|---|---|
| validate_domain | FAV / FAV / FAV — all survive worst-case bounds AND the √2.7 design-effect inflation |
| validate_problem | FAV / knife-edge (fails inflation) / UNDECIDED |
| validate_plan | UNDECIDED / UNDECIDED / UNDECIDED — the −67pp harm and +13pp lift are **mechanism-layer** claims only |
| solve | FAV-knife-edge (survives inflation by 0.9pp; treated non-confirmatory per memo prohibition) / UNDECIDED / UNDECIDED |
| simulate | UNDECIDED / UNDECIDED / UNDECIDED (both arms censored on canonical) |

## 3. Discrepancies with the memo letter — FLAGGED FOR OMER

(a) **Memo §3 says "exactly 2/25 cells UNDECIDED (35b validate_problem; 9B
solve)".** The honest think=off count from the canonical pooled table is **13/25
UNDECIDED** (table above). The 2/25 figure traces to the 07-11 D2b comparison,
whose cell tables pooled the two think modes (e.g. its 9B solve no-tools 18.8 =
the off 10.7 / on 27.0 average) — a pooling the paper's own "arms are never
pooled" rule forbids. The prose follows the derived off-only table; the memo's
prohibited-claims list is unaffected (every prohibition remains satisfied).

(b) **9B solve, think=off:** worst-case bound survives disjointness at 95% and
also at the paper's inflated threshold (18.7 vs 17.8 after √2.7) — but by 0.9pp.
The memo prohibits claiming this cell significant on delivered (its derivation was
the mode-pooled one). Treatment in prose: quote the bound, note it survives
worst-case reading, and classify it as exploratory/non-confirmatory, consistent
with both the memo and the knife-edge margin.

(c) **gemma validate_problem, think=off:** favorable at plain 95% (81.2 > 78.1)
but FAILS the √2.7 inflation (79.0 < 80.1). Treated like the −5pp steering dip
precedent: reported, flagged individually, non-confirmatory.

(d) 0.8B validate_* AGAINST cells are real delivered-surface findings (small-model
tool-mishandling made worse end-to-end) and enter the roster-wide prose.

(e) **Frontier no-tools simulate: three sources disagree.** The merged tex quotes
Sonnet canonical 45.0 [39.5, 50.7] (135/300) as an exact point; NUMBERS.md says
"[0, 100] — 100% censored, do not quote a point" (its provenance memo predates the
07-15 batch de-censoring); the canonical pooled table (post-de-censoring,
regenerated 07-17) gives bounds 41.7–61.3 with 59/300 censored (125 determinate
successes, not 135). The rewrite quotes the pooled-table bounds — the only value
consistent with the sanctioned aggregator — and the qualitative claim ("the
simulate floor does not carry over to the frontier") survives at the lower bound.
NUMBERS.md needs a refresh of that row; the 45.0/38.3 provenance needs
adjudication (possibly a pre-D9 or different-tolerance reading).

## 4. RQ verdict mapping (old tool-verified → new delivered)

| RQ | old | new (delivered primary) |
|---|---|---|
| RQ1 vd | YES | **YES** — unchanged, now robust at worst-case bounds |
| RQ1 vp | YES 3/3 | **YES, qualified** — 1/3 confirmatory (9B), gemma near-threshold, 35b UNDECIDED, 0 against |
| RQ2 solve | YES +54–92pp | **YES at the frontier tier (exact: 22→95 Haiku, 29→95 Sonnet, both +5.0pp below the tool-verified 100)**; open roster: bounds, 9B exploratory-favorable, gemma/35b UNDECIDED |
| RQ3 vplan | MIXED (−67pp gemma) | **UNDECIDED on the delivered surface at the canonical corpus (all three ≥9B)**; the harm and the steering repair are mechanism-layer (CALL-stage) results; iss024d full-storage replication INVERTS gemma (delivered 30.0–63.1 vs tool-verified 0.9): not-calling ≠ not-answering |
| RQ4 simulate | YES (tool 65–92) | **no delivered lift demonstrable**: canonical censored both arms; frontier delivered ⟨49,62⟩/⟨52,64⟩ vs Sonnet NT 45.0 exact — not CI-separated; the finding becomes the delivered↔tool-verified gap (length-driven transcription) |
| RQ5/RQ6 | YES/NO | unchanged but **explicitly labeled mechanism-layer** (computed on tool-verified cells; delivered bounds cannot support bin-level contrasts on canonical) |

P(call) numbers (21→94% gemma, invocation spreads) are storage-exact and keep
their current values — they move to the explicitly-labeled mechanism layer, not
out of the paper.

## 5. Edit spec executed on paper/main.tex (this batch)

1. Methods → Metrics: two-layer estimand declaration (delivered primary /
   tool-verified mechanism), three value shapes tied to storage regime, notation
   gate (Wilson `[a, b]` vs censor-bounds `⟨a, b⟩`), delegation_terminal category,
   D2b sensitivity (3.6% of rows).
2. Results head: "how to read our numbers" table (corpus × storage × shape ×
   reason) with the memo's prohibited claims as its footnotes; scorecard rewritten
   per §4.
3. Sole-source subsection → split framing: unaided floors (delivered, exact,
   unchanged) vs with-tools delivered (frontier exact + open-roster bounds);
   transcription-gap paragraph (0pp verdicts / +5pp plans / ≥33pp trajectories,
   two tiers) folded in from `sonnet_wt_vs_haiku_e2e_memo.md`.
4. Validation subsection: delivered bounds + §3(b,c) treatment.
5. Backfire subsection: relabeled two-layer; canonical delivered UNDECIDED owned;
   iss024d inversion reported under separate-apparatus labeling; steering kept as
   CALL-stage repair (exact).
6. Difficulty + cost subsections: mechanism-layer labels; "no-tools simulate
   cost-of-pass is infinite" sentence dies; delivered-bounds caveat added.
7. Frontier robustness block: add the with-tools frontier paragraph (solve 95.0
   both tiers, +5.0pp gap; simulate bands; validation gap ≈0).
8. Abstract, Intro contributions, Discussion executive summary + implications,
   Conclusion, Limitations (drop the surface-asymmetry ownership sentence — the
   asymmetry no longer exists; own the censoring bounds instead).

**Deferred to batch 2 (not in this commit):** funnel Figure-1 with FORMALIZE bar
(journal memo §2 spec; also carries the PlanBench amendment), regeneration of
solve/simulate/failure-taxonomy/token-quadrant figures on the delivered surface
(captions relabeled honestly this batch), frontier delivered cost-of-pass
computation, delivered balanced-accuracy for validate_domain.

## 6. Reproduction script (verbatim)

```python
#!/usr/bin/env python3
# input: results/derived/e2e_overlay/pooled_e2e_table.csv
import csv, math, sys
Z = 1.959963984540054
def wilson(k, n):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + Z*Z/n; c = p + Z*Z/(2*n)
    h = Z*math.sqrt(p*(1-p)/n + Z*Z/(4*n*n))
    return ((c-h)/d, (c+h)/d)
rows = {}
with open(sys.argv[1]) as f:
    for r in csv.DictReader(f):
        if r["corpus"] != "sweep5v2-live" or r["bank"] != "neut": continue
        rows[(r["model"], r["think"], r["task"], r["arm"])] = (
            int(r["n"]), int(r["ok_strict"]), int(r["censored"]))
for (m, th, t, arm) in sorted(k for k in rows if k[3] == "tl-neut"):
    nt = rows.get((m, th, t, "nt-neut")); wt = rows[(m, th, t, "tl-neut")]
    if not nt: continue
    nt_n, nt_ok, nt_c = nt; wt_n, wt_ok, wt_c = wt
    fav = wilson(wt_ok, wt_n)[0] > wilson(nt_ok + nt_c, nt_n)[1]
    agn = wilson(wt_ok + wt_c, wt_n)[1] < wilson(nt_ok, nt_n)[0]
    v = "FAVORABLE" if fav else "AGAINST" if agn else (
        "UNDECIDED" if (wt_c or nt_c) else "NS")
    print(m, th, t, v)
# knife-edge check: rerun with Z *= sqrt(2.7) (design-effect inflation)
```

## 7. Pickup for the next session — frontier budget probe + batch 2 (written 2026-09-08)

**Decisions from the 09-07/08 chat (Omer):** the "simulate has no demonstrable
delivered lift" reading STANDS as drafted (it is data, not a defect); a native
claude.ai/agentic harness is OUT for this paper (successor-work direction — it
changes the question and the apparatus); the **frontier budget probe is a GO in
principle**, gated on the two standing disciplines below. Do not weaken strict
delivery grading to "fix" the cell — crediting unrestated tool results is the
τ-bench flaw D2b was decided against.

### 7a. The probe (design sketch to be turned into a prereg)

- **Question (causal):** is the frontier simulate delivery gap caused by the
  output budget? The stored anatomy says 29/100 Sonnet WT failures are
  `done_reason=length` truncations; if delivered rises toward tool-verified when
  only the answer budget rises, the paper's "the gap is budget-shaped" claim
  gets causal support; if it does not move, the gap is format/content-bound and
  the prose must say so.
- **Design:** canonical corpus, simulate, neutral v11 bank, n=100/cell, same
  `frontier_runner.py` apparatus with ONLY the output-token budget raised
  (pick the raise in the prereg after checking the current cap in the runner;
  the 16K snapshot storage cap should be raised to match so censoring does not
  eat the gain). Arms: Sonnet WT is the primary cell; decide in the prereg
  whether to add Haiku WT (tier replication) and an NT leg (budget symmetry) —
  each roughly doubles cost. Never pooled with existing corpora; compare only
  against the existing cells' bounds.
- **Prediction to pre-register:** delivered ≥ the current determinate 56.3
  by roughly the truncation mass (upper reference ≈ 85 if all 29 length-fails
  convert); kill/negative reading = delivered inside the current ⟨49, 62⟩.
- **Cost:** ballpark $10–20 for the single Sonnet cell (longer outputs than the
  $90.75/1520-trial run's per-trial average; itemize precisely in the prereg).
- **Gates (both binding):** `/freeze-protocol` v2 on the analysis entry point
  BEFORE any readout is ratified; an itemized-expense line appended to the
  paper_notes ledger BEFORE spend (grant covers it; the rule is itemization,
  not budget). Open-roster budget raises stay dead (the 32K smoke failure
  stands; do not re-run that config).
- The probe result lands in the paper as a sentence or two in the Delivery Gap
  section (mechanism confirmation), not as a new headline surface.

### 7b. Batch 2 of the reframe (unchanged list, one home)

1. Funnel Figure-1 per journal memo §2 (trials → CALL → tool-result-correct →
   delivered; NEED as a reference line, never a bar) — and its PlanBench
   variant adds the FORMALIZE leading bar (closes integration-plan item 6).
2. Regenerate `solve.pdf` / `simulate.pdf` / `failure_taxonomy.pdf` /
   `token_quadrant.pdf` on the delivered surface (batch 1 only relabeled their
   captions as mechanism-layer); `paper/figures/make_paper_figures.py` is the
   generator.
3. Frontier delivered cost-of-pass (memo §3 derived obligation) — token totals
   from the frontier corpora ÷ delivered successes; open roster stays labeled
   tool-path economics.
4. `validate_domain` delivered balanced accuracy (per-class, from the overlay
   rows) if we want to restore a delivered balanced-acc claim.
5. Freeze the single-tool headline rows into NUMBERS.md once 1–4 settle.

### 7c. Standing gates for whoever picks this up

- **Batch 1 (`125cc7a` on `paper/aaai27`, in the worktree
  `../pddl-copilot-worktrees/paper-aaai27`) is committed but UNPUSHED and
  UNREVIEWED.** Do not push until Omer reviews — pushing auto-syncs Overleaf.
  When cleared: `sync_overleaf.sh pull` first, then push, per
  `paper-git-overleaf-instructions.md`.
- Job 3 (nt-ster caveat-only integration) is still owed and now interacts with
  batch 1's text: its steering-control material lands in the rewritten backfire
  subsection + Robustness; quote ONLY the revised readout / NUMBERS.md values.
- Read §3 of this worknote before touching any verdict — the memo's "2/25
  undecided" is superseded by the derived 13/25 table, and the frontier
  NT-simulate 45.0/38.3 points are retired.

## 8. Batch 2 — executed 2026-09-08 (figures + derived obligations)

All numbers below are computed read-only from the canonical overlay
(`results/derived/e2e_overlay/`, regenerated 2026-07-17) through the shared
aggregator `e2e_overlay.load_e2e_cells`, plus raw `trials.jsonl` for token totals
and `tool_selected`; the generator is `paper/figures/make_paper_figures.py`
(rewritten this batch; its `main()` prints every figure-level number used in the
captions). Committed on `paper/aaai27` as `dbea3d7` (after `125cc7a`; both still
unpushed; one review gate for both).

### 8.1 Funnel Figure 1 (`figures/funnel.pdf`) — stage table

Frontier, with-tools plain, canonical, prompt v11 (NEED = no-tools delivered sliced
to v11, per frontier D3):

| tier | task | n | CALL | tool result correct | delivered | NEED (no-tools) |
|---|---|---|---|---|---|---|
| Haiku 4.5 | validate_domain | 120 | 100.0 | 98.3 | 98.3 | 87.5 |
| Haiku 4.5 | validate_problem | 200 | 100.0 | 96.5 | 96.5 | 73.0 |
| Haiku 4.5 | validate_plan | 1000 | 100.0 | 98.9 | 98.8 | 91.5 |
| Haiku 4.5 | solve | 100 | 100.0 | 100.0 | 95.0 | 22.0 |
| Haiku 4.5 | simulate | 100 | 100.0 | 97.0 | ⟨52, 64⟩ | ⟨38, 68⟩ |
| Sonnet 4.6 | validate_domain | 120 | 100.0 | 95.8 | 95.8 | 93.3 |
| Sonnet 4.6 | validate_problem | 200 | 100.0 | 98.0 | 98.0 | 86.5 |
| Sonnet 4.6 | validate_plan | 1000 | 100.0 | 99.9 | 100.0 | 97.1 |
| Sonnet 4.6 | solve | 100 | 100.0 | 100.0 | 95.0 | 29.0 |
| Sonnet 4.6 | simulate | 100 | 100.0 | 99.0 | ⟨49, 62⟩ | ⟨34, 53⟩ |

(The Sonnet NT simulate v11 slice is ⟨34, 53⟩, c19/100; the all-variant cell
quoted in the tex is ⟨41.7, 61.3⟩, c59/300 — both are canonical, the figure uses the
v11 slice to match the with-tools prompt.)

Open roster, plain arm, think=off, validate_* only (memo §2 gate: solve/simulate
canonical cells are vacuous bounds and are routed through the frontier panel /
full-storage rerun):

| model | task | CALL | tool result correct | delivered | NEED |
|---|---|---|---|---|---|
| 9B | vd / vp / vplan | 100 / 100 / 97.9 | 100 / 95.2 / 93.2 | ⟨99.7,100⟩ / ⟨92.2,95.3⟩ / ⟨80.8,87.2⟩ | 25.6 / 65.7 / 79.7 |
| Gemma | vd / vp / vplan | 100 / 99.8 / 20.7 | 97.5 / 99.7 / 20.6 | ⟨93.3,98.1⟩ / ⟨84.3,99.8⟩ / ⟨6.6,99.6⟩ | 77.8 / 74.8 / 87.8 |
| 35B | vd / vp / vplan | 100 / 98.5 / 82.9 | 98.9 / 96.8 / 82.2 | ⟨91.9,99.2⟩ / ⟨74.7,97.8⟩ / ⟨55.0,90.3⟩ | 67.8 / 75.7 / 90.9 |

PlanBench panel (Haiku 4.5 with tools, n=600 per pool; stages from
`results/planbench/wt-anthropic-20260801/sidelogs/formalization_match_rows.jsonl`,
delivered = first-draw per NUMBERS.md; the rows file's last-attempt 418/431 is
asserted in the generator so drift is loud):

| pool | FORMALIZE | CALL | tool plan found | delivered (first-draw) | NEED (matched-NT) |
|---|---|---|---|---|---|
| clean | 578/600 = 96.3 | 600/600 | 418/600 = 69.7 | 410/600 = 68.3 | 47.8 |
| Mystery | 587/600 = 97.8 | 600/600 | 572/600 = 95.3 | 431/600 = 71.8 | 0.0 |

Bars are marginal shares of all trials (not nested conditionals); the caption says
so. This closes integration-plan item 6 (FORMALIZE amendment).

### 8.2 Regenerated figures (delivered surface)

- `solve.pdf`: open roster canonical (NT exact + Wilson; tool arms hatched bounds;
  tool-verified as a dotted tick) + frontier tiers (v11, exact).
- `simulate.pdf`: canonical open-roster cells are censored on both arms, so the
  open-roster panel is the iss024d full-storage rerun (think=on, separate apparatus,
  labeled): tl-neut delivered 4B ⟨8.3,10.7⟩ / 9B ⟨12.0,16.7⟩ / Gemma ⟨6.0,20.7⟩ / 35B
  ⟨12.7,13.7⟩ against tool-verified 63.0 / 82.7 / 44.0 / 92.3 (steered 73.3 / 89.0 /
  92.0 / 94.0); frontier panel NT ⟨34,53⟩/⟨38,68⟩ vs WT ⟨49,62⟩/⟨52,64⟩.
- `failure_taxonomy.pdf`: categories from `e2e_reason` (tool arms) / raw
  `failure_reason` (no-tools rows, whose overlay reason is `stored_online_grade`).
  Pooled ≥9B think=off: unaided solve 67.1% unparseable + 15.3% truncated + 8.3% wrong;
  unaided vd/vp/vplan wrong-content 39.5 / 25.8 / 12.8; unaided simulate 92.6% censored;
  the `delegation_terminal` category is empty on ≥9B think=off.
- `token_quadrant.pdf`: y = delivered low with a translucent bar to high; delivered
  cost-of-pass multiplier (tl-ster ÷ nt-neut, pooled ≥9B, range across the bounds):
  solve **0.65–1.64×**, vd 2.81–2.91×, vp 4.41–4.86×, vplan 4.11–5.16×, simulate not
  identified (both arms censored on canonical).
- `mechanism_validate_plan.pdf`: unchanged (mechanism layer; title relabeled).

### 8.3 Frontier delivered cost-of-pass (memo §3 derived obligation)

Tokens = prompt + completion + cache-write + cache-read (raw accounting, matching the
"tokens count raw" stance in the cost subsection) for with-tools; prompt + completion
for no-tools (batch). Cost-of-pass = Σtokens ÷ delivered successes; bounds where the
cell is censored (÷(ok+cens) .. ÷ok). $/pass at list price (WT, cache-aware) and
batch price (NT). Canonical corpus, prompt v11.

| tier | task | WT tokens/pass (delivered) | WT tokens/pass (mech.) | NT tokens/pass | ratio | WT $/pass | NT $/pass |
|---|---|---|---|---|---|---|---|
| Sonnet | validate_domain | 12,652 | 12,652 | 1,263 | 10.0× | 0.028 | 0.004 |
| Sonnet | validate_problem | 13,935 | 13,935 | 1,660 | 8.4× | 0.050 | 0.004 |
| Sonnet | validate_plan | 15,860 | 15,876 | 2,451 | 6.5× | 0.048 | 0.009 |
| Sonnet | solve | 18,634 | 17,703 | 6,022 | **3.1×** | 0.067 | 0.015 |
| Sonnet | simulate | ⟨83,539, 105,703⟩ | 52,317 | ⟨9,816, 15,301⟩ | **5.5–10.8×** | 0.377–0.477 | 0.055–0.085 |
| Haiku | validate_domain | 12,267 | 12,267 | 1,535 | 8.0× | 0.009 | 0.002 |
| Haiku | validate_problem | 14,294 | 14,294 | 2,539 | 5.6× | 0.016 | 0.003 |
| Haiku | validate_plan | 16,581 | 16,564 | 2,872 | 5.8× | 0.017 | 0.004 |
| Haiku | solve | 48,520 | 46,094 | 7,997 | **6.1×** | 0.048 | 0.007 |
| Haiku | simulate | ⟨72,898, 89,721⟩ | 48,098 | ⟨7,728, 13,828⟩ | **5.3–11.6×** | 0.105–0.129 | 0.014–0.026 |

Reading: at the frontier the unaided baseline is not floored (solve 22–29%), so the
tool is a token premium per delivered pass on every task, including solve (3.1× /
6.1×) — the "pays for itself where floored" verdict is an open-roster result. Written
into the cost subsection this batch.

### 8.4 validate_domain balanced accuracy, delivered (think=off, canonical)

Per-class from overlay rows (truth: `problem_name != "domain_neg"`; 300 positive /
60 negative per cell):

| model | no-tools (exact) | +tool plain | +tool steered |
|---|---|---|---|
| 9B | 53.3 | ⟨99.2, 100.0⟩ (neg c1/60) | ⟨100.0, 100.0⟩ |
| Gemma | 74.0 | ⟨87.3, 94.2⟩ (pos c11, neg c6) | ⟨92.2, 95.0⟩ (pos c12, neg c1) |
| 35B | 64.7 | ⟨77.2, 97.5⟩ (pos c2, neg c24) | ⟨82.7, 99.2⟩ (pos c4, neg c19) |

Claim-adverse end clears the unaided value for all three in both arms. Written into
the validation subsection + `tab:vdom` (new delivered column).

### 8.5 Frontier budget probe — prereg drafted

`development/frontier_budget_probe_prereg.md` (DRAFT, four `> ANSWER` slots).
Freeze candidate: `tools/budget_probe_analysis.py` + `tests/test_budget_probe_analysis.py`
(29 checks, synthetic 30-row fixture with hand-computed Fisher p = 120/792). Apparatus
flags: `frontier_runner.py --num-predict/--snapshot-len/--stream`,
`claude_api_batch.py build --num-predict` / `grade --snapshot-len`;
`e2e_regrade.KNOWN_CAPS += 262144`; probe stems get run tag `sweep5v2-budget65k`.
Reference-cell anatomy pinned (Sonnet 49 OK / 25 LEN-FIT / 4 LEN-NOFIT / 3 DECLINE /
19 ET-FAIL; Haiku 52 / 17 / 1 / 1 OVERFLOW / 2 SNAP / 14 / 12 / 1 OTHER). Itemized
cost: expected ≈$50–65 (A+B+C+D), hard cap $217. Nothing has been spent.
