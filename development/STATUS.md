# STATUS — what is actually left

*Content last refreshed: 2026-11-09, end of day (every open decision answered except E1,
which Omer keeps open; PRs #121 to #127 and #129 merged; pyval 0.1.6 pinned in the sibling
repo; the work list for the next sessions is in `handoff_20261109.md`). Earlier that day:
the repo audit and Omer's first twelve answers (`paper_notes_discussions.md`). Before that
2026-11-08 (contamination-wording paper PR #123; plan step D5 added and approved, the
answer to Corrêa et al.). Before that 2026-11-01 (C1, C2 in PR #121; B drafts on `main`; the D1
smokes passed, harness PR #122; D1b built, one decision open). Before that 2026-10-10
(the weakness list is fully answered and the work now follows `weakness_action_plan.md`;
`development/` was cut to the docs that work needs, see `MOVES.md`). Earlier refreshes, and the closed-work table this file used to
carry, are in git history and in `paper_notes_discussions.md`. Renamed from
`remaining_work_20260811.md` on 2026-08-29.*

> **This is the single, stable entry point for project status, and it is edited in
> place.** Do not write a new dated successor doc. Update this file and move its date
> line. Before quoting any figure, check `NUMBERS.md`.

## The one-paragraph answer

The paper becomes **two studies**. Study 1 is the main sweep: what the models do without
tools and how often they call the tool (these numbers held up in the rerun: 11 of 12
unaided cells and 25 of 30 tool cells met the ±5-point equivalence criterion; 27 of 30 by
point estimate). Study 2 is pre-registered on
the fixed setup: the delivered rerun (read out 2026-10-09) plus an extension (new model
families, harder test items, context room, reasoning mode, the small models, a JSON
control, open-model PlanBench). Then one restructure of the paper. **All of it is in
`weakness_action_plan.md`, workstreams A to F.** A is done. B: drafts on `main`
(`draft_B1_B2_related_work.md`, `draft_B3_B5_methods.md`), waiting for Omer's read; two
agent-side gaps first (Corrêa et al. in B1; the C1 VAL figure in B4's TODO). C1, C2, C3:
done (PRs #121, #124). C4: done (PR #128; the transcript readings were drafted by an AI session and wait for Omer's confirmation). D1a to D1d: done (PRs #122, #127; the D1b items
are in three trees, no harness change, `reference/d1b_harder_items.md`). The contamination
wording in the tex uses the paired, clustered ±5 test (PR #123). Plan step D5 answers
Corrêa et al.'s "Frontier LLMs Rival State-of-the-Art Planners" (D5a to D5e, all
approved; the D5a pilot ran and its PR #131 is merged; the full run with D5e, about $66 with the Batch API, approved by Omer 2026-11-09, once the prereg holds it). Four grading findings of 2026-11-09 are ISS-027 to
ISS-030. **Next: the work list in `handoff_20261109.md` §4** (tracking file, checkpoints
follow-up, release files, #130 (cleaned, still a draft), B drafts, C5 and E1a, D1e, D5b ground truth, D1f,
one cluster go-ahead, then the D5a full run).

## Where each line stands

| line | state |
|---|---|
| Main sweep, Study 1 (`sweep5v2-live`, `sweep6-live`) | data final. Unaided and tool-verified numbers reproduced by the rerun; its open-model delivered ranges are retired (biased low by the harness) |
| Delivered rerun, Study 2 part 1 | **complete, read out 2026-10-09** by the frozen code (`reference/delivered_rerun_readout.md`). A separate-apparatus replication: parity failed at job level (Gemma 10/10, Qwen 15/20). R1 no delivered harm · R2 unresolved · R3 the title changes · R4 met · R5 the directive suppresses calling. Figures in `NUMBERS.md` |
| Extension, Study 2 part 2 | preparation (D1) under way: four new families pass the parser smoke (official Gemma 4 BF16, gpt-oss-20b, Ministral 3 14B, Llama 3.1 8B); 32K and 64K windows work and cut empty final answers steeply; the JSON constraint now binds (opt-in). Harness merged (PR #122). Not yet: D1e (PlanBench tools: the `vllm-tools` path exists on `main`; plain and steered prompts, the PR #122 serve flags and a smoke remain), D1f (prereg) |
| PlanBench | in the tex (PR #114: equivalence test declared, corrected extractor beside the shipped numbers); open-model tools arm planned (D2) |
| Steering control (nt-ster H4) | closed 2026-08-29, all six units PASS; in the tex appendix |
| Frontier tier and budget probe | closed for Study 1; in the tex. D5 adds new frontier cells (thinking on, larger problems, the renamed-corpus tool arm, random strings). Haiku 4.5's tool arm on the renamed corpus already ran (2026-07-12, `results/haiku-frontier/sweep6-with-tools`, 1,520 trials) and was never reported; only Sonnet's is missing |
| Paper | the 09-19 text plus PRs #110, #111, #114, #115 (merged 2026-10-09) and #123 (contamination wording, merged 2026-11-08). Title D goes (R3); the restructure is plan §4 E |

## Rules that bind every step

- Study 1 and Study 2 are never pooled into one number, and a rerun figure never stands
  in for a canonical cell (prereg §3).
- Frontier figures are exact except simulate delivered (bounds); `iss024d` is a separate
  apparatus and never resolves an UNDECIDED cell; gaps are computed paired within a corpus.
- `NUMBERS.md` before prose; `/verify-claims` on every edit with a number;
  `/freeze-protocol` before hashing any analysis code.
- Never copy the rerun readout's "sampled under the per-task JSON constraint" sentence:
  it is false (`reference/weakness_consolidated.md`, the Q3 note).
- Ping Omer before any SSH or SLURM action.

## How work is done

**`main` is the single line of work** (since 2026-09-18). Every change goes on a short
branch off `main` and reaches `main` by PR, and Omer merges. Doc-only record changes in
`development/` are the exception. A merged PR that touches the synced paper files pushes
to Overleaf by itself. Run `development/sync_overleaf.sh` from the main checkout,
**pull before push** (`paper-git-overleaf-instructions.md`).

**Pinned commits.** The rerun harness is tag `delivered-rerun-harness` (`4b2fe6e`) and its
frozen analysis is tag `delivered-rerun-analysis-frozen` (`d558946`, package
`822aace…`). PR #117 was a squash (`4147a0c`), so both are reached through their tags,
not through `main`'s history. The extension runs on the harness tag plus additive
changes only.

## External gates

- **Budget:** a grant covers everything planned, and budget and reruns are not a
  constraint (Omer 2026-10-10). Itemize any dollar spend before making it.
- **Venue:** JAIR primary, TMLR fallback. Formal advisor ratification is in N2.
- **AAAI-27:** dropped; the deadline passed.

## Decided and still binding

- **R7** send the manuscript and the brief: **hold** (Omer 09-19). Work proceeds; Omer
  says when an advisor meeting happened. Never give "wait for the advisors" as a reason
  to hold a task.
- **R8** the Llama-3.1-8B probe: superseded 2026-10-10; it is absorbed into the new
  families of plan step D2.
- **R9** the weakness list, Q1 to Q11: all answered (Q1 to Q4 on 10-02, Q5 to Q11 on
  10-10), and the five defaults of plan §2 kept (Omer 2026-10-10).
- Not planned: the BF16-35B precision control and the schema-salience probe (09-18);
  Sonnet-tier PlanBench (plan §2).

---

## Next steps

### N1 — The action plan (in progress)

`weakness_action_plan.md`. Order: A (done) → B, C, D1 and E1 in parallel → D2 wave 1 →
D3 wave 2 → D4 readout → E2 to E7 → F. About two months to the readout.

### N2 — Advisor and coauthor round (Omer; on hold by R7)

`advisor_brief.md`. Its top note says which of its six questions still stand (venue,
thesis requirement, recording the pivot) and which the work has overtaken (the cost deck,
the rerun, Sonnet-tier PlanBench). No coauthor has edited Overleaf since the 08-11 sync.
Only the JAIR reformat waits on this round.

### N3 — Before submission (plan §4 F)

JAIR reformat and de-anonymising (the author block, the links block, leaving
`[submission]` mode), done once after the venue is ratified; the public code and data
release with the prereg documents and their hashes; the cover letter with the
arXiv:2509.12987 delta (`reference/journal_decisions_memo.md` §5), which also closes
ISS-013.

### N4 — Hygiene

- Cluster checkout: checked 2026-10-10, it sat on `harness/delivered-rerun` at `4b2fe6e`
  (the rerun's pinned harness). Probably stale: the D1 smokes ran from
  `harness/d1a-new-families`, now merged. Re-check at the next go-ahead. Any SSH needs
  Omer's go-ahead first.
- Laptop: done 2026-11-09 (Omer ran it). The two merged worktrees and the merged local
  and remote branches are deleted. Two old stashes from `paper/aaai27` are Omer's to
  check.
- Checkpoint zips: four June deck files removed (PR #129); the follow-up (fresh frontier
  overlays, an `e2e-overlay` README, the dead lfs line, a `checkpoints/frontier/` backup)
  is decided, `handoff_20261109.md` decision 16.
- Laptop, Omer's to run: nine agent worktrees under `.claude/worktrees/` (handoff §5).

### Decided 2026-11-09 (Omer)

- **D1b, where the results live.** The extension gets a new sweep folder. Rerun rows it
  reuses are copied in, and each copied row keeps a field naming its source folder and
  job; the prereg declares the reuse (after the 35B flips, a rerun is not identical to
  the original, so reused rows must stay identifiable). `delivered-rerun/` and
  `sweep5v2-live` are never touched. **The loader:** two small validate_domain trees
  (tree A with the first invalid domain, tree B with the second), no harness change.
- **Llama weights:** keep unsloth's ungated copy if its weight files match Meta's byte
  for byte. **Checked 2026-11-09: identical** (all four shards and the index match Meta's
  LFS pointers; only small config and tokenizer metadata differ, with the same chat
  template and stop tokens; `draft_release_licence_models.md` §2). Unsloth stands.
- **GPT-OSS:** low effort in wave 1, medium in wave 2, sent explicitly; cells labelled
  "low effort", never "thinking off".
- **The 35B calling rate:** quote both runs (68.0 and 82.7), keep "bigger calls less" as
  a direction only, and put the 35B cells in the extension's repeat check.
- **D5a:** Sonnet 4.6 and Haiku 4.5 thinking on (the clean comparison), plus Sonnet 5.5
  thinking on and off (the current tier); a thinking-off run at temperature 1 on the same
  problems; each problem 3 times. Itemized cost to Omer before any spend.
- **D5d:** yes, the cheapest form (two random-string maps per domain, unaided solve,
  Sonnet 4.6 and Haiku 4.5, about 800 trials).
- **D5b:** use some of Corrêa et al.'s (IPC 2023) domains and problems as additions.
  Ground truth first: validate the domains and problems, solve with the planner, check
  every plan with VAL, before any model runs. Report the share the planner solves within
  120 s and within 30 min.
- **PlanBench roster (D1e):** keep the 4B (its failures are data). More small or MoE
  candidates to be suggested; each must pass the parser smoke.
- **New families:** wave 1 starts with two families plus the official Gemma weights. All
  families that passed the smoke go into the prereg now, each as a numbered tier with the
  same analysis, so adding one per wave needs only a go-ahead (no new prereg, no
  re-freeze).
- **The Corrêa 2-shot prompt cell (plan D5e):** approved. Their prompt word for word
  (instructions, the Gripper and Logistics worked examples, their checklist), then our
  problem. Our Gripper problems are left out of this cell, because their example is a
  solved Gripper problem; Logistics is not in our corpus. Sonnet 4.6, unaided solve:
  thinking off at temperature 0 (matches the existing 28.7% cell) and thinking on with 3
  repeats (matches D5a). Same grader; the pilot checks that the answer reader reads their
  plan format, and if it does not, Omer is asked before anything changes. Reported as one
  descriptive row, outside the confirmatory set, never pooled with v11 to v13.
- **Wave 1 families (Omer 2026-11-09, yes):** gpt-oss-20b and Llama 3.1 8B, plus the
  official Gemma weights. Ministral 3 14B is the wave-2 tier.
- **D5 thinking pilot (Omer 2026-11-09, yes; ran 2026-11-09, PR #131, $1.69):** 20 keys per arm, Batch API, about $1.50
  to $10, hard cap $40. It measures thinking tokens and the answer-parse rate only; plan
  success is not computed, so the pilot does not peek at the outcome. The prereg declares
  it.
- **Later-wave models (Omer: keep only the ones of high value to the paper).**
  Registered as numbered tiers, each still to pass the parser smoke:
  - **GLM-4.7-Flash:** a third family with a real thinking on/off switch, so the
    reasoning-mode finding (Gemma's calling falls from 21% to 0.6%) can be tested outside
    Qwen and Gemma. A new vendor, and a fast MoE.
  - **gpt-oss-120b:** the same family as the 20b at a larger size, so "bigger calls
    less" (a direction only since the 35B flips) gets a test in a second family. A fast
    MoE, but it needs a GPU to itself.

  Passed over: Nemotron 3 Nano (adds a new architecture, which the paper's questions do
  not ask about, and its prefix caching is unchecked), Granite 4.2 8B (dense and slow;
  Llama already fills the 8B rung), Olmo 3 7B (its open training data would allow a
  direct contamination search, but that is a separate project; its thinking variant is
  a separate checkpoint, not a switch).
- **Release (final):** BGN Technologies owns research artifacts by default (Omer; no check
  needed). Code MIT, data CC-BY-4.0, copyright line naming BGN (confirm its exact legal
  name), Omer as author in `CITATION.cff` and on the Zenodo DOI, lab SPL-BGU.
- **D5a full run:** approved (about $51 with the Batch API), after D1f holds the cells.
  The $51 leaves out D5e. Its thinking-on cell (95 problems x 3 = 285 trials) adds about
  $14 (about $10 to $19; 2-shot input from pilot arm e (7,626 tokens per trial), output = arm a's mean Sonnet 4.6 thinking (4,123 tokens, bootstrap CI) plus arm e's mean answer (887), at Batch prices of $1.50 / $7.50 per MTok); its thinking-off cell adds $1.72 (95 x1). With D5e,
  about $66 with the Batch API (PR #131 review).
  Omer has $186 loaded plus a work account; when the loaded credits run out, decide next.
- **pyval case fix (ISS-027):** `pddl-pyvalidator` 0.1.6 released by Omer; pinned in the
  validator plugin 3.1.1 (SPL-BGU/pddl-copilot #60, merged). The cluster's plugin venv
  still needs the upgrade (`launch-server.sh` never upgrades an existing `.venv`).
- **Gemma, wave 2:** `REASONING_PARSER=none`, as in Study 1.
- **Tracking:** Design A (`development/items.yaml`, rendered and checked), with the
  recommended answers to the proposal's Q2 to Q9 (`handoff_20261109.md` decision 15).
- **Checkpoints:** the agent's five recommendations accepted (`handoff_20261109.md`
  decision 16).

### Open PRs (2026-11-09, end of day)

Merged 2026-11-09: #121 to #129, #131, and the sibling's #60; #124 to #129 and #131
were reviewed and fixed first. Open: #130 (draft, ISS-027 and Gemma check scripts;
cleaned and ready to leave draft when Omer decides; adds generated ISS-027 caveats
beside T1, T2, T5, T8a and the mechanism row). When #130 merges, `tests/verify.sh`
conflicts with #128's line; keep both. Details and next steps: `handoff_20261109.md` §1.

`tests/test_delivered_rerun_analysis.py` (hash-pinned) fails 1 of 428 when run in the
main checkout, already at `51fe971`: its "DEPENDENCIES cover every imported repo
module" check counts `.venv/` site-packages, since the venv sits inside the repo. It
passes from any worktree whose venv lives outside the repo. Not a code fault.

### Open decisions

- **⚠️ STILL OPEN (Omer 2026-11-09: keep it open): E1, the six research questions
  against the two gates.** Existing RQ1 to RQ6 and the suggestion (a baseline question,
  one question per gate, problem size as a factor, the scorecard dropped) side by side in
  `draft_E1_research_questions.md`. Until Omer decides, no E step removes the RQs or the
  scorecard from the tex, and E1 drafts carry both framings.

None of these blocks the next steps. The title is chosen in plan step E6, from the candidates in
`reference/weakness_consolidated.md` Q6, once the results are in.
