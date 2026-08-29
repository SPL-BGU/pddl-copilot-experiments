# Journal Phase-0 — handoff (fresh session pickup)

> **SUPERSEDED — do NOT use the pickup protocol below.** Its status rows were
> replaced by **`remaining_work_20260811.md`** (2026-08-11), which is where a fresh
> session should start. The accepted spec it points at
> (`journal_decisions_memo.md`) is still live and still binding. Retained as the
> record of the Phase-0 slot decisions.

**Date:** 2026-07-24. **Branch:** `main` at `4909c0b`, pushed, working tree clean.
**Pickup protocol:** run `/resume-verify` against this doc. Read order for a fresh
session: this doc → `development/journal_decisions_memo.md` (the accepted spec —
everything below derives from it) → the annotated ANSWER slots in
`development/archive/status-snapshots/journal_narrative_proposal.md` §8 + `development/archive/status-snapshots/roadmap_eval_and_paper_completion.md`
→ `development/archive/planbench/planbench_frontier_haiku_nt.md` + `PLANBENCH_HANDOFF_v3.md`
(status banners, 07-24).

---

## One-paragraph state

All 8 open journal-pivot decisions (D-J1..D-J6, roadmap D2 + D4) were investigated
(23-agent workflow, 12 adversarial red-team passes, all AMEND / zero refutes),
recommended in `development/journal_decisions_memo.md`, and **ACCEPTED by Omer in
session 2026-07-24**. Slots are annotated, the decision batch + the e2e-overlay
placement ruling are logged in `paper_notes_discussions.md` (2026-07-24 entry), the
two binding proposal corrections landed (frontier simulate delivered = censor-bounds
NOT exact, §2/§5; §6 softened to body-summary + appendix-detail), and both PlanBench
docs carry superseded/status banners. Committed + pushed as `4909c0b`. Nothing is
running anywhere (no cluster jobs, no API runs in flight). Omer confirmed: **next up
is PlanBench with-tools**, entered via its prereg.

## Decisions in force (memo section = full binding spec)

- **D-J1** protocol-first RATIFIED, findings-hook variant (gradient opener
  0pp/+5pp/≥33pp; within-arm cascade Fig 1; "Controls that moved headlines";
  conditional on 3 retirements) — memo §2.
- **D-J2 = D2 = (a)** full e2e reframe: delivered = single primary surface;
  notation hard gate (Wilson CI vs censor-bounds typographically distinct);
  "how to read our numbers" table heads Results; storage-fixed rerun is a
  pre-registered CONTINGENCY (default: not run) — memo §3.
- **D-J3** minimal frontier-only PlanBench Act 4; NT re-measurement carries the
  headline; WT secondary vs matched-scaffold control; kill 2026-08-15 → shrink to
  NT-only (never scatter) — memo §4.
- **D-J4** recommendation TO ADVISORS: JAIR primary / TMLR fallback / AIJ
  override-only / KBS dropped; audience-self-contained manuscript — memo §5.
  NOT yet ratified by advisors.
- **D-J5** BOTH complements, nt-ster first at recommended scope (think=off AND
  think=on, ~92 GPU-h, + same-apparatus nt-neut anchor), then Llama-3.1-8B probe;
  prereg-before-submit; caveat-only integration cap — memo §6.
- **D4** all three parked; +$0 guided_json local audit (fix stays parked) — memo §7.
- **D-J6** yes, title/abstract candidates (constraints list) — memo §8.
- **E2E overlay: INCLUDED by construction** (Omer probed dropping it 07-24; kept —
  see paper_notes 07-24 entry for the placement ruling: results/headline in body,
  protocol as C1, D1-D9 mechanics in appendix + one body-level summary table).

## Next actions, in order (memo §9 Phase 0 — all local, no ping needed)

1. **Write `development/reference/planbench_wt_prereg.md`** and get Omer's
   ratification (~20 min of his time) BEFORE any build/spend. Must contain (memo
   §4): matched-scaffold no-tools control definition (identical SDK system
   scaffold: NL→PDDL step + task-format clause; empty tool list is the ONLY
   ablation); seed-fixed stratified subsample n≈200-250/cell; scope priority
   bw t1 > mystery t1 > bw t3 (target = {clean, mystery} × {matched-NT, WT} 2×2
   on t1); predictions — (i) tools convert failure→success on mystery t1, clean
   t1 confirms near ceiling; (ii) TWO-SIDED Mystery mechanism (tools may rescue
   Mystery — both directions publishable); (iii) t3 verification-gap vs own
   matched-NT (struck if t3 trimmed); prediction-cell linkage rule (trimmed cell
   ⇒ its prediction struck); funnel-placement statement for the NL→PDDL interface
   (input-boundary stage or explicit CALL extension — named BEFORE data);
   GPT-4 presentation-separation rule (WT never shares a table/figure with GPT-4
   rows; t7 only in Act 5); ~20-instance calibration gate vs the ~$70.6 API
   remainder; kill criterion (a) budget (b) no graded WT table by 2026-08-15 →
   shrink to NT-only act; headline assignment (NT primary / WT secondary).
   t2 excluded (optimal_plan tool unbuilt).
2. **Write `development/ntster_h4_prereg.md`** and get ratification, so the
   cluster submit is ready at Omer's next VPN window. Must contain (memo §6):
   H4 TOST ±5pp vs the co-run nt-neut anchor, control-first noise-floor
   calibration; surfaces named (tool-verified AND delivered); per task×model n
   fixed; claim-licensing map with pre-drafted pass/fail paper language; anchor
   scope = exactly two uses (paired H4 contrast; within-July 2×2 factorial with
   iss024d wt-neut/wt-ster) — anchor-vs-May delta goes ONLY to the validity
   thread, never revises NEED; apparatus pinned to iss024d config (same vllm.sif
   tag, sbatch wrapper, parser flags, marketplace 1.4.0, 16K ctx); fresh run-tag
   (strip post-filter — sweep6 lesson); accepted scope = think=off AND think=on
   (~92 GPU-h; Omer may downgrade to off-only at the submit ping, which strikes
   the 07-12 steered-e2e link); Llama kill-gate (ToolSel ≥0.95 / 0% extraction,
   one parser retry); Llama arms = v11 nt-neut/tl-neut + v14 tl-ster
   (`summary.py arm_for`: steered = v14-16); caveat-only integration cap.
3. **Build the PlanBench WT adapter** over `tools/frontier_runner.py` (~1 agent
   day; its docstring pre-plans this reuse) + run the 20-instance calibration →
   Omer approves calibrated scope + spend (~10 min) → Haiku WT + matched-NT
   control runs (Anthropic API, local) → grade locally (Rosetta VAL + plugin FD;
   repro block in `planbench_frontier_haiku_nt.md`; apply the t2-artifact
   spot-check discipline — that grader fails silently) → results memo.
4. **Parallel Phase-0 items** (independent, agent-executable): title/abstract
   candidates per memo §8 constraints (AI-tells rule; no unscoped
   composition-failure declaratives); collision-check "the delivery gap" against
   existing tool-use/agent-eval terminology BEFORE locking the term; guided_json
   $0 local audit (mechanism + affected-row fraction, for Limitations; the FIX
   stays parked); P1 writing sprint under worst-case scoping (steering
   diagnostic-only, family confound owned) per memo §3's reframe spec.

## Gates and rules that bind the next session

- **Cluster = ping-gated.** No SSH/SLURM action without Omer's explicit go-ahead
  + VPN (standing rule). Cluster queue: nt-ster + anchor submit (after prereg
  ratified), later the Llama cell. PlanBench WT needs NO cluster.
- **Paper edits** go on the `paper/aaai27` branch; read
  `development/paper-git-overleaf-instructions.md` first; always
  `sync_overleaf.sh pull` (+ commit) before `push`. Run `/verify-claims` before
  any results prose; every results PR gates on it (memo §3). Grep development/
  for PENDING specs before touching claims (standing lesson, 07-15).
- **Corpus labels are law** (memo §3 quoting rules): frontier exact EXCEPT
  simulate delivered (bounds); sweep5v2 WT = strict bounds, 2/25 cells stay
  UNDECIDED; iss024d = separate-apparatus, within-corpus paired gaps only;
  never resolve UNDECIDED cells via iss024d; canonical corpora =
  `results/sweep5v2-live` + `*_sweep6` (NOT the stale sweep5-cluster-20260530).
- **Budget:** ~$70.6 API remainder is reserved for PlanBench WT (steering
  reframe ~$50 and contamination probe $20-40 are parked precisely to fund it).
- **Advisor-gated, not agent work:** venue ratification (JAIR flip argument),
  thesis-clock assumption (submission vs acceptance), formal AAAI-27 drop, cost
  verdict, storage-fixed-rerun posture (memo §10).

## Commit discipline reminder

Doc-only handoff/decision artifacts: direct commit to main, no PR (CLAUDE.md
exception). Code or paper changes: branch + PR. Never credit Claude in commits.
