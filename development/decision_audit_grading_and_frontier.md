# External-literature audit of the 2026-07-11 decisions (grading surface + frontier rerun)

**Date:** 2026-07-11
**Scope:** every decision recorded in `tool_call_vs_final_output_grading.md` (D1–D6) and the
open slots in `frontier_rerun_framework_decision.md` (D1–D4), audited against the tool-use /
LLM-agent evaluation literature (not the PDDL literature).
**Method:** scientific-critical-thinking review + verification of the specific benchmark
conventions each decision leans on (τ-bench, BFCL, ABC, HAL) + verification of the Anthropic
SDK facts that frontier-D1 option B depends on.
**Bottom line:** 8 of 10 decisions are correct and, in several cases, ahead of common practice.
Two need revision or hedging: **D2b=B** (crediting empty-but-deliberate final turns) and the
**size of the A-vs-B harness probe** (~100 trials is under-powered for its stated purpose).

---

## 0. Verdict table

| Decision | Recorded choice | Verdict | §  |
|---|---|---|---|
| Grading D1 — headline metric | end-to-end primary, tool-verified diagnostic | **CORRECT** | 1.1 |
| Grading D2 — e2e definition | (a) response-only, same grader both arms | **CORRECT** | 1.2 |
| Grading D2b — empty final turn | B: credit `stop`+empty when tool-verified | **REVISE / HEDGE** | 1.3 |
| Grading D3 — scope of pass | A: one consolidated overlay | **CORRECT** | 1.4 |
| Grading D4 — names | "end-to-end" / "tool-verified" | OK, one hazard tied to D2b | 1.5 |
| Grading D5 — corpora | paper canon + frontier + sweep7 | **CORRECT** | 1.4 |
| Grading D6 — censored rows | A: report bounds, no reruns | **CORRECT** | 1.6 |
| Frontier — rerun Haiku+Sonnet fresh | decided | **CORRECT** | 2.1 |
| Frontier D1 — harness framework | recommendation B (SDK Tool Runner) | **SOUND, with 3 conditions** | 2.2 |
| Frontier D2 — A-vs-B probe | ~100 trials | **YES, but resize or reframe** | 2.3 |
| Frontier D3 — single prompt variant | recommended | REASONABLE (note limitation) | 2.4 |
| Frontier D4 — scope/budget | $200–350 both models | fine (two cheap additions) | 2.5 |

---

## 1. Grading-surface decisions

### 1.1 D1 (end-to-end primary) — CORRECT, and the literature is unusually unanimous

The decided principle ("grade the model's output, not an internal component's") is exactly the
prevailing convention for information-seeking agent tasks:

- **τ-bench** ([arXiv:2406.12045](https://arxiv.org/pdf/2406.12045)) computes reward from the
  final database state **plus** "ground truth outputs for user questions" that must appear in
  the agent's messages to the user. State-grading is reserved for tasks whose deliverable *is*
  the side effect; information the user asked for must be conveyed, or the task fails.
- **ABC** ("Establishing Best Practices for Building Rigorous Agentic Benchmarks",
  [arXiv:2507.02825](https://arxiv.org/abs/2507.02825), NeurIPS 2025) formalizes this as
  **outcome validity**: the evaluation result must be `true` iff the agent actually solved the
  user's task. Grading the MCP trace for a question the user consumes as text fails outcome
  validity — the old metric was measuring **task validity of delegation**, a different construct.
- All five of our tasks are information-seeking (nothing persists after the episode), so the
  response-graded surface is the right primary. The internal argument (the v14–16 prompts
  already define the final response as the deliverable) independently forces the same answer.

The decision also fixes the **shared-grading-surface violation** (comparative arms graded on
different surfaces), which is the first thing a BFCL/τ-bench-literate reviewer would flag.
Verdict: keep, and cite ABC's outcome-validity framing in the paper — it gives the fix a name.

### 1.2 D2 = (a) (response-only, symmetric) — CORRECT

Symmetry is the property that makes the tool-lift Δ interpretable; the conjunction variant (b)
is derivable afterwards from the overlay columns, so nothing is lost. Crediting
response-right/tool-wrong mirrors how the no-tools arm credits a lucky guess — the construct is
"did the user get the right answer", not "was the pipeline internally clean". This matches how
τ-bench and WebArena treat trajectories: outcome-graded, trajectory-agnostic. Keep.

### 1.3 D2b = B (credit deliberate delegation-terminal) — the one decision I would revise

**The literature flag is direct, not analogical.** ABC's motivating examples of broken reward
design include, verbatim, "**τ-bench counting empty responses as successful**" — the pattern
that inflated τ-bench scores (an agent that does nothing passes some tasks) and that ABC's
checklist exists to catch. D2b-B is a *conditioned* version of the same rule: an empty final
turn is credited when `done_reason=stop` **and** the trace is tool-verified. A reviewer who
knows ABC (it is at NeurIPS; the τ-bench example is its headline anecdote) will pattern-match
this instantly, and the burden of proof lands on us.

**Three internal inconsistencies compound the optics problem:**

1. **It contradicts the argument that motivated the whole overlay.** §1 of the grading doc
   argues the old metric is wrong because "the grader credits ~29% of with-tools validate
   successes for trials that disobeyed [the prompt's VERDICT] instruction." An empty final turn
   also disobeys that instruction. Crediting it re-imports trace-grading through the back door
   for exactly the trials where the model didn't do what the prompt asked.
2. **It breaks the D2(a) symmetry claim.** The carve-out conditions on tool-verification, so
   with-tools e2e is partially a function of the trace while no-tools e2e never is. "Same
   grader both arms" is no longer literally true, and D2(a) was chosen *for* that property.
3. **The choice is material and directionally favorable to our headline.** 4B retains 74–78%
   of its wins under B vs 60–64% under strict (~14pp swing, §5 of the grading doc). A scoring
   rule that is both post-hoc and favorable to the paper's thesis is the worst combination for
   reviewer trust.

**What survives of the defense:** the decided principle ("a tool call is itself model output")
is a coherent construct — it is precisely what BFCL grades — and the delegation-terminal mass
is small for the larger models (35b: 1.3% of tool-graded successes). The Phase-1 corpus-wide
number (6.0% of all with-tools validate rows get the D2b-B credit) is not huge. So B is
*defensible*; it is just not the safest headline.

**Recommendation (pick one):**

- **(R1, preferred) Make strict D2b-(i) the headline** and report **"delegation-terminal"
  as its own visible outcome category** in every table (alongside correct-verdict /
  wrong-verdict / truncated / censored). Nothing is lost — the reader sees the 6% and can add
  it back — and the τ-bench-empty-response critique becomes unreachable. The measured lifts
  survive at strict grading for every cell the paper leans on (9B everywhere; 4B
  validate_domain/problem; the cells that don't survive are censoring-dominated anyway).
- **(R2) Keep B as headline** but (a) print the strict variant beside it in every table (the
  (i)/(ii)/(iii) sensitivity is already computed — put it in the paper, not just the repo),
  and (b) state the rule *before* the results in the methods section, framed as
  operationalizing "tool call as output," with the ABC objection acknowledged explicitly.

**Measured strict-vs-B comparison (run 2026-07-11, `tools/e2e_d2b_compare.py` over the
existing overlays; `e2e_regrade.py` now also emits an `e2e_strict` column per row).**
Delegation-credit mass: 4,856 / 136,800 rows on sweep5v2-live (3.6%), 5,084 on sweep6.
Of 25 model×task lift-verdict cells per corpus, **2 flip** on each:

| corpus | cell | no-tools | strict [lo,hi] | B [lo,hi] | deleg | read |
|---|---|---|---|---|---|---|
| sweep5v2 | 9B solve | 18.8 | [16.7, 40.3] straddle | [25.8, 49.4] lift | 9.1% | the only substantive flip — under strict, **no** mid/large model shows a determinate e2e solve lift on the old corpus; censoring-bound, ISS-024(d) resolves it exactly |
| sweep5v2 | 35b validate_problem | 76.6 | [76.1, 95.0] straddle | [76.9, 95.8] lift | 0.8% | knife-edge (0.3–0.5pp margin, inside sampling noise at n=2400) — honestly a wash under both rules |
| sweep6 | 0.8B solve | 0.0 | [0.0, 10.8] straddle | [0.1, 10.8] lift | 0.1% | one credited row; noise |
| sweep6 | 4B validate_plan | 45.1 | [38.9, 47.7] straddle | [45.4, 54.2] lift | 6.5% | 0.3pp margin — knife-edge |

Everything else is verdict-stable: every headline validate lift (4B, 9B, 35b, gemma
validate_domain/problem) survives strict grading; 0.8B's inversions stay inverted; every
simulate cell straddles under both rules.

The magnitude story concentrates in **9B**, not 4B as the §5 retained-share table suggested:
9B is the delegation-heavy model (deleg = 10.3 / 34.7 / 23.3% of with-tools
validate_domain/problem/plan rows), so its strict lower bounds drop from 97.1/88.0/78.0 to
86.8/53.3/54.7 — still a lift in all three cells, but validate_plan's lower-bound margin
shrinks from +27.4pp to +4.1pp. Read as a finding rather than a loss: the model with the
best delegation (tool-verified 87–99%) has the worst answer restatement — the
answer-synthesis gap *grows* with delegation competence on this roster.

**Net effect on the recommendation:** the numbers strengthen R1. Strict grading costs no
qualitative validate conclusion, converts two knife-edge "lifts" into honestly-undecidable
straddles, and moves the one substantive cell (9B solve) into exactly the bucket that the
already-running ISS-024(d) 16K-cap rerun will decide with exact numbers. Adopting strict as
headline + delegation-terminal as a visible category loses nothing that isn't censoring-bound
anyway, and removes the ABC empty-response attack surface entirely.

> ANSWER: **R1 — DECIDED (Omer, chat, 2026-07-11): go strict.** `e2e_strict` is the paper's
> headline; delegation-terminal is a visible outcome category; B stays as a derived
> diagnostic column. Qwen ISS-024(d) run kept (resolves the strict-undecided cells).
> Recorded in `tool_call_vs_final_output_grading.md` (status REVISION note) and
> `paper_notes_discussions.md`.

### 1.4 D3 = A (consolidated pass) and D5 (all four corpora) — CORRECT

One scoring-code version producing all tables eliminates the version-skew failure mode that
produced the stale-mirror incident ([[reference_canonical_corpus_vs_stale_mirror]]), and the
derived-overlay design (canonical `trials.jsonl` never mutated) preserves corpus identity —
consistent with HAL's log-first infrastructure argument
([arXiv:2510.11977](https://arxiv.org/abs/2510.11977)): keep raw rollout logs immutable, derive
metrics. D5's full coverage is what made the Phase-4 discovery possible (frontier corpora
75–100% censored) — running it was right, and the result justifies the scope retroactively.

### 1.5 D4 names — one hazard, tied to D2b

"Tool-verified success" is clear and maps to the BFCL construct (call-level correctness);
"delegation success" is the nearest literature-native synonym if a reviewer balks. The hazard
is "**end-to-end success**" *if D2b-B stays*: under B, "end-to-end" includes trials where the
user received no answer at all, and the name then overclaims exactly where the metric is
softest. Under R1 (strict headline) the name is accurate as-is. Under R2, define it in one
sentence at first use ("…where a bare tool call with a verified result counts as the model's
answer when the model closed the turn deliberately") so the definition travels with the name.

### 1.6 D6 = A (bounds) — CORRECT, and methodologically the strongest decision of the set

Reporting interval-censored cells as bounds is Manski-style **partial identification** — the
standard answer to missing-not-at-random data (e.g.
[interval-data identification](https://arxiv.org/pdf/1802.10490); recent LLM-specific
treatments [arXiv:2602.16061](https://arxiv.org/pdf/2602.16061)). The censoring here is almost
certainly MNAR (response length correlates with verbosity, task, and model), so any
point-imputation would be attackable; bounds are not. Two notes:

- Vacuous cells ([0,100] Sonnet simulate; gemma [17.3, 98.5]) are simply unusable and the doc
  already says so — keep saying so in the paper rather than shading them.
- The already-running ISS-024(d) full re-run (16K snapshots) will produce **exact** e2e numbers
  for the Qwen with-tools cells, strictly better than any bound-narrowing estimate — when it
  lands, report exact numbers for those cells and keep bounds only where no uncensored twin
  exists. Its parser-off apparatus delta is disclosed by design (it doubles as the parity probe).

Also carried forward correctly: the "0% contradiction" claim is now **1.2% corpus-wide** —
paper prose must say "rarely (1.2%)", never "never".

---

## 2. Frontier rerun + harness framework

### 2.1 Rerunning Haiku + Sonnet fresh — CORRECT

75–100% snapshot censoring makes the stored frontier corpora unable to answer the e2e question;
Sonnet no-tools simulate (0/300) is 100% unrecoverable, and the paper needs that cell for the
sole-source-floor retraction. No salvage path exists; $200–350 is proportionate. No critique.

### 2.2 Frontier D1 — recommendation B is sound, on three conditions

The reasoning in the decision doc is right as far as it goes, and there is a fourth argument
for B it doesn't make: **our own bug history.** ABC and HAL both find that harness bugs, not
model behavior, are the dominant source of mis-estimation in agent evals — and this project's
three scoring bugs (grading surface, simulate normalizer, validate_plan FP binning) plus the
snapshot-censoring discovery are four instances of exactly that, all in custom code. Less
custom loop code is a rigor argument, not just a convenience.

The three conditions:

1. **Frame the D2 probe as the gate for cross-family comparability, not a nice-to-have.**
   HAL's core claim is that model, scaffold, and benchmark are three separate axes and a score
   is attributable to the model only when the scaffold is held fixed or its effect measured.
   Under B, harness covaries with model family (Qwen arm = custom vLLM harness, frontier arm =
   SDK runner). The A-vs-B probe is what licenses the comparison — A is the loop that copies
   the Qwen-harness rules, so A-vs-B *is* the measured harness effect. If the probe shows a
   large effect, B-only frontier numbers are not comparable to the Qwen arm and the design
   needs revisiting; say this in the doc so the probe result has decision force.
2. **Pin the beta surface and verify loop-cap equivalence.** `client.beta.messages.tool_runner`
   and the MCP helpers (`anthropic[mcp]`, Python ≥3.10) are **beta** SDK surfaces whose
   semantics can change between releases — pin the exact `anthropic` package version in the
   module and record it in trials metadata. Verify that `max_iterations` counts the same thing
   MAX_TOOL_LOOPS counts (one API round-trip per iteration) so the `loop_exhausted` failure bin
   stays comparable across arms; make the D2 probe compare **turn and token distributions**,
   not just success, since harness effects surface in efficiency metrics first. (Known runner
   caveat — no auto-resume on `pause_turn` — is irrelevant here: local MCP tools only, no
   server-side tools.)
3. **State the residual confound in limitations either way.** "Tools stay identical" is true at
   the server level but not at the prompt surface: the Qwen harness renders tool schemas
   through the qwen3_xml template while both A and B use Anthropic-native function calling.
   That cross-family delta exists under A too — it is inherent to comparing open-weights and
   API models — so it doesn't discriminate A vs B, but the paper must describe the per-arm
   harness and not imply identical apparatus.

Against C the doc is right, and ABC gives it a name: a C-arm lift would fail **task validity**
(measures tools+skills+subagents+scaffold, not tools). Keep C as an explicitly-labeled
"deployed-product ceiling" arm at most.

### 2.3 Frontier D2 — run the probe, but ~100 trials can't do what the doc says it does

The doc's stated purpose is to "quantify the harness effect instead of hand-waving it." At
n=100 paired trials with base success ~90%, a paired analysis (McNemar on discordant pairs)
resolves only large effects; the 95% CI on Δ is roughly ±5–8pp. A null result at n=100 is
consistent with anything from 0 to a Δ that flips borderline cells. Two honest options:

- **(P1, preferred) Size it for the effect that matters:** ~300–500 paired trials gives ~80%
  power for a 5pp paired difference at typical discordance rates. At probe prices this is
  ~$20–50 — still noise within the D4 budget. Run identical fixtures through both loops,
  analyze success with McNemar + report turn/token distribution deltas.
- **(P2) Keep n≈100 but reframe** it as a gross-defect check ("rules out harness effects
  >10pp"), and don't describe it in the paper as quantifying the harness effect.

> ANSWER: **Probe approved (Omer, frontier doc D2 "yes", 2026-07-11).** Sizing
> operationalized as a **staged probe** to respect the $238 funded budget (frontier D4):
> stage 1 = 100 paired trials (~$5–10, gross-defect check); extend to 300–500 (~$20–50,
> P1 quantification) only if stage 1 shows any discordance worth measuring (≥2 discordant
> pairs or a turns/token distribution shift). If stage 1 is fully concordant, stop —
> report the probe as a bounded gross-defect check, per P2 framing.

**STAGE-1 RESULT (run 2026-07-11, Haiku, canonical corpus, variant 11): fully
concordant — stage 2 not triggered; the probe stands as the P2 gross-defect check.**

- Keys: `tools/make_stage1_keys.py` (seed 11) → `.local/frontier/stage1_keys.jsonl`,
  100 trials = 20/task × all 20 domains (one per domain per task), fixtures
  quota-balanced (validate_problem 10p/10n, validate_plan 10 valid/10 buggy labels,
  validate_domain 4× `domain_neg`), `prompt_variant=11` pinned (inside the old Sonnet
  NT corpus's v11–13, so the D3 slice-to-matching-variant comparison stays available).
  Both arms ran the identical keys file with fresh GT, serialized (B then A) so solver
  contention couldn't skew tool results. Comparison: `tools/frontier_ab_compare.py`.
- **Success: 0/100 discordant pairs** (exact McNemar p=1.0). Both arms 99/100; the
  single failure is the *same trial with the same failure reason and same tool call*
  in both arms (`simulate counters/p05`, `result_mismatch` after one
  `get_state_transition` call) — a model/grading property, not a harness effect.
  Per-task: solve 20/20 both, validate_* 60/60 both, simulate 19/20 both.
- **Turns/tokens: no shift.** Mean turns 2.48 (A) vs 2.53 (B) — only solve differs
  (4.35 vs 4.65, the SDK runner occasionally takes one extra loop); in-tok/trial
  24,406 vs 24,768 (+1.5%); out-tok/trial 2,744 vs 2,766 (+0.8%).
- **Cost + caching verdict: B $3.28 vs A $3.81 (−14%).** B's list-equivalent ($3.86)
  matches A's list price ($3.81), so the whole gap is prompt caching. The 3-trial
  smoke's "+6% net-loss" (§2.5) inverts at stratified scale: task-grouped consecutive
  trials keep the tools+system prefix hot, and solve's multi-turn loops read ~30K
  cached tok/trial (B per-task solve cost $0.91 cached vs $1.39 no-cache). →
  **Keep `cache_control` ON for the full run**; budget the WT arm at ~0.85× list.
- **License:** framework B is confirmed as the sole full-run harness (the HAL
  model/scaffold separation argument is now backed by a measured null); the D4
  sequence proceeds Haiku both arms → re-estimate → Sonnet. Measured full-grid
  re-estimate: Haiku WT ≈ $50/corpus (1520 trials, cached).

### 2.4 Frontier D3 — single variant is reasonable

Prompt-template variance is real (HELM-style multi-prompt evaluation exists for a reason), but
the paper's frontier claims are within-model tool-lift with the prompt held constant across
arms, where template variance largely cancels. Slicing the old 3-variant Sonnet NT corpus to
the matching variant for comparison is the right move. Note single-template as a limitation in
the paper; don't spend 3× for variants.

### 2.5 Frontier D4 — approve, with two cheap additions

- **Validate caching on the probe before the full run:** check `cache_read_input_tokens > 0`
  on real probe traffic. The doc's Haiku caveat is correct (4096-token minimum cacheable
  prefix — verified current) — the *shared* prefix is only tools + system + fixed prompt
  preamble (fixtures vary per trial), so it must clear 4096 tokens on its own or caching
  silently no-ops and the WT cost estimate is wrong by ~2×.

  **UPDATE (live smoke, 2026-07-11, `tools/frontier_runner.py`, Haiku, 3 trials):** the
  end-to-end live path is verified (SDK Tool Runner loop + MCP + grading, 3/3 OK). Caching,
  once moved off the below-minimum system block onto the SDK runner's own `cache_control`
  (multi-turn breakpoints), is ACTIVE — but on this smoke it was a **NET LOSS (+6% vs
  no-cache)**: trials are short (~2 turns) with a large, *unique* per-trial domain/problem
  context, so the 1.25× write premium on the ~52K prefix isn't recouped, and consecutive
  trials share no big prefix (different problem each). **This directly challenges the D4 /
  memory assumption that "with-tools caching is the cost lever."** Consequence: (1) budget
  the frontier WT arm at **no-cache list price** ($1/$5 Haiku, $3/$15 Sonnet), NOT a
  caching-discounted figure — the doc's "$60–100 both arms, caching cuts it substantially"
  is likely optimistic; (2) the stage-1 stratified probe (all 5 tasks, not 3 identical
  simulate trials) is what settles whether caching ever helps here — solve/validate turn
  counts and context sizes differ, so the per-task verdict may vary. The runner now prints
  ACTIVE / NET-LOSS / INACTIVE explicitly so the probe reads the answer off the summary.
  If the probe confirms net loss corpus-wide, disable caching for the full run (it only
  adds cost).
- **Optional batch≡live insurance:** the no-tools/Batch vs with-tools/live split makes API
  path covary with arm. No behavioral difference is documented for Batch, but a ~50-trial
  no-tools overlap sample run live is nearly free and closes the question if a reviewer asks.

---

## 3. What the decisions get right that the field often doesn't

Worth saying explicitly, because it belongs in the paper's methods framing:

- **The overlay turns a scoring bug into a finding.** "Models rarely misreport tool results
  (1.2%) but fail to restate them in a large fraction of successful delegations, violating the
  prompt's output contract" is a quantified answer-synthesis result no current benchmark
  reports, and the simulate variant (tool loops exhaust the budget before any final trajectory
  is emitted) is a clean harness-interaction mechanism — consonant with HAL's finding that more
  reasoning/interaction can *reduce* end-task accuracy.
- **Bounds over imputation** (§1.6) is more honest than common practice, where truncated or
  unparseable rows are silently binned as failures or dropped.
- **Immutable corpora + derived overlays + one consolidated re-derivation** matches the
  reproducibility infrastructure ABC/HAL prescribe.

## Sources

- τ-bench: [arXiv:2406.12045](https://arxiv.org/pdf/2406.12045) · [τ2-bench repo](https://github.com/sierra-research/tau2-bench)
- ABC best practices: [arXiv:2507.02825](https://arxiv.org/abs/2507.02825) · [checklist site](https://uiuc-kang-lab.github.io/agentic-benchmarks/) · [NeurIPS 2025 poster](https://neurips.cc/virtual/2025/poster/121769)
- HAL: [arXiv:2510.11977](https://arxiv.org/abs/2510.11977) · [hal.cs.princeton.edu](https://hal.cs.princeton.edu/)
- Partial identification with interval data: [arXiv:1802.10490](https://arxiv.org/pdf/1802.10490) · [arXiv:2602.16061](https://arxiv.org/pdf/2602.16061)
- Anthropic SDK facts (Tool Runner beta status, MCP helpers, `max_iterations` hooks, Haiku
  4096-token cache minimum, Batch API semantics): verified against the claude-api skill's
  current SDK documentation, 2026-07-11.
