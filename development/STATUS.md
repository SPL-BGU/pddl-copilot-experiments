# STATUS — what is actually left

*Content last refreshed: 2026-08-11 (after PR #93). Renamed from
`remaining_work_20260811.md` on 2026-08-29.*

> **This is the single, stable entry point for project status, and it is edited in
> place.** Do not write a new dated successor doc — that is what produced the
> four-deep supersession chain now sitting in `archive/status-snapshots/`. Update
> this file and move its date line. Before quoting any figure, check `NUMBERS.md`.

**Entry point for "what is actually left."** Written after PR #93 merged to main
(`1638013`). Supersedes the status rows in `journal_phase0_handoff.md` (07-24) and
`roadmap_eval_and_paper_completion.md` (07-15); both stay for their decision records.

## The one-paragraph answer

**No experiment is owed for either line's headline claims.** PlanBench-WT is closed
(RESCUE, SUPPORTED, four-rung ladder, n=600/cell). The single-tool line's data has
been complete since 2026-07-17 (sweep5v2-live + sweep6 + iss024d-e2e-live + the
Haiku/Sonnet frontier corpora, all graded). What is left is **writing** — two paper
sections that are fully specified and signed but have not touched tex — plus **one
optional control run** (nt-ster H4) that by its own prereg can only soften prose,
never delay it. Last paper commit is `afc92b6`, 2026-07-23.

## State by line

| line | data | analysis | paper |
|---|---|---|---|
| PlanBench (NT + WT) | DONE, archived + MANIFEST-verified | DONE, `verify_promotion.py` re-derives every number | **NOT STARTED** — Act 4 section, plan signed 4/4 slots |
| Single-tool suite | DONE (07-17) | DONE (e2e overlay D1–D9 + Phase 5, pooled table regenerated) | **NOT STARTED** — the full e2e reframe (D2/D-J2 = option a) |
| nt-ster H4 control | not run | n/a | prereg written, **4 RATIFY signatures open** |

Evidence that the paper side is untouched: `paper/main.tex` on `paper/aaai27` has
**zero occurrences of "delivered"** (the reframe's whole vocabulary) and mentions
PlanBench only as citations plus the Future Work promise at L1076-77.

## Job 1 — PlanBench Act 4 section (unblocked today by the merge)

Fully specified in `planbench/planbench_wt_paper_integration_plan.md`, all four
ANSWER slots signed 2026-08-06/07. Nothing to design; it is transcription plus
prose. Shape: new self-contained section "External validity on PlanBench" between
Results and Discussion (placement A), ladder table in the body, two-layer NT
presentation (graded 0.0 + injection caveat, stripped 4.3 as the robust reading).

Numbers it quotes are frozen and verified: clean WT **68.3** [64.5, 71.9] vs
matched-NT 47.8, Δ+20.5pp, McNemar p=1.38e-13 (first-draw — Omer's conservative
call); Mystery WT 71.8 vs 0.0; bare-NT clean 43.8 CI-disjoint above the GPT-4
reference 34.3; ladder 0.7 / 0.0 / 0.5 / 71.8; formalization_match 96.3 / 97.8.

Binding while writing: `PLANBENCH_WT_FINAL_PHASE_HANDOFF.md` §"only open work"
(WT is the labelled SECONDARY claim; GPT-4 is a reference line never a comparator;
every external number prints pool size + grader; `/verify-claims` for anything
outside the 08-06 pass). Estimated: one agent session, plus Overleaf sync.

## Job 2 — the single-tool e2e reframe (P1 / D2 = D-J2 = option a)

The one substantive paper change left on the main suite, and the larger of the two.
Spec: `journal_decisions_memo.md` §3. It makes **delivered** the single primary
surface for tool-lift claims, demotes tool-verified to the mechanism layer, adds the
"how to read our numbers" table at the head of Results, and enforces the notation
gate (Wilson CIs and censor-bounds typographically distinct).

Corpus rules that bind every sentence: frontier exact except simulate delivered
(bounds); sweep5v2 WT = strict bounds with 2/25 cells staying UNDECIDED; iss024d is
**separate-apparatus** (job-level parity FAILED 07-17) so it never resolves an
UNDECIDED cell; gaps computed paired within a corpus. Material to fold in: the
transcription gap (solve +5pp both tiers, simulate ≈35–50pp length-driven,
`sonnet_wt_vs_haiku_e2e_memo.md`) and the de-censored NT delivered columns.

This is where the retracted claims finally get their replacement text, so it is also
the cleanup of the simulate sole-source-floor thread.

## Job 3 — nt-ster H4 control + nt-neut anchor (the only unrun experiment)

Falsification control for the steering claim: does the steered directive move the
no-tools floor on its own? If it does, the +72pp May steering effect stops being
"steering under tools." Prereg `ntster_h4_prereg.md` is written, slots filled and
accepted 07-25, **§10 has four unsigned RATIFY lines**.

Two things to know before signing:

- **Price was corrected upward from the memo's ~92 GPU-h.** [refined 08-11 after
  ratification: ~186 GPU-h is the *plain-apparatus, three-model, both-modes* price.
  The accepted shape costs **~46 GPU-h off + ~110-150 on ≈ 156-196 total**, the
  on-mode half still an estimate until readiness item 7 reconstructs the decoupled
  wall. Same order of magnitude; recorded accurately in the prereg §10 signature.]
- It is **caveat-only by design** — the result can relax prose but never gates it,
  so Job 1 and Job 2 proceed whatever happens here.

Readiness items still owed before a submit ping (prereg §readiness rows 7–14): the
decoupled think=on wall reconstruction, freezing the two analysis entry points,
rebuilding + stamping `gt_cache.json`, and — only if the Llama probe stays in
scope — a `vllm_lookup` case for Llama-3.1-8B, which needs its own branch + PR and
must not touch `PDDL_VLLM_VERIFIED_MODELS` while nt-ster is live.

## Job 4 — small items, agent-executable, no gates

- `guided_json` $0 local audit (mechanism + affected-row fraction, for Limitations;
  the fix stays parked per D4).
- Collision-check "the delivery gap" against existing tool-use/agent-eval
  terminology before the term locks into the title/abstract.
- Title/abstract candidates per memo §8 constraints.

None of the three were done during the PlanBench phase; all three were Phase-0
parallel items.

## Not our call (external)

Advisor cost verdict (blocks the next cost-phase step only); venue ratification
(D-J4 recommends JAIR primary / TMLR fallback); formal AAAI-27 drop. The PlanBench
kill criterion of 2026-08-15 is moot — the arm delivered before it.

---

## Decisions

**R1 — Order of the two writing jobs.** Recommendation: **PlanBench Act 4 first.**
It is smaller, fully signed, additive to the tex, and does not collide with the
reframe's vocabulary; the reframe then lands on a tex that already has its newest
section in place. The alternative is reframe-first on the argument that it is the
higher-value change.

> ANSWER (PlanBench first / reframe first / both in parallel on separate commits):
> planbench first

**R2 — nt-ster: ratify now, or drop it?** Recommendation: **ratify now** so the
submit is ready at your next VPN window, with the ~186 GPU-h price stated. Dropping
it is defensible if you would rather spend the remaining weeks on writing — the cost
is that the H2 steering attribution keeps its "diagnostic-only, family confound
owned" worst-case scoping in the manuscript permanently.

> ANSWER (ratify now / defer until after the two writing jobs / drop and keep the
> worst-case scoping):
> ratify

**R3 — Llama-3.1-8B second-family probe.** It is the piece that drags in harness
changes (branch + PR for `vllm_lookup`) and its own kill-gate. Recommendation: keep
it, but sequenced strictly after nt-ster lands, as the memo already has it.

> ANSWER (keep as sequenced / drop / decide after nt-ster):
> keep as sequenced

**R4 — Job 4 small items: run them now in the background?** They are $0, local, and
independent of everything above. Recommendation: yes, run them alongside Job 1.

> ANSWER:
> yes
