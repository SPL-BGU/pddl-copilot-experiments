# STATUS — what is actually left

*Content last refreshed: 2026-11-09 (repo audit: PRs #121, #122 and #123 are all merged;
Omer's answers to twelve open decisions, recorded under "Decided 2026-11-09" below and in
`paper_notes_discussions.md`; `fixtures/d1b-harder-items` pushed to origin). Before that
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
agent-side gaps first (Corrêa et al. in B1; the C1 VAL figure in B4's TODO). C1 and C2:
done, merged in PR #121 (VAL agrees on 1,731 of 1,732 plans; Study 1 block in
`NUMBERS.md`). D1a, D1c, D1d: smokes passed (`reference/d1_smokes_20261027.md`), harness
merged in PR #122. D1b: built on branch `fixtures/d1b-harder-items` (pushed to origin
2026-11-09; its write-up `reference/d1b_harder_items.md` is cited but not written); the
loader decision is made (two small validate_domain trees, no harness change). The
contamination wording in the tex uses the paired, clustered ±5 test (PR #123, merged
2026-11-08). Plan step D5, approved 2026-11-08, answers Corrêa et al.'s "Frontier LLMs
Rival State-of-the-Art Planners": frontier thinking on, larger problems, the Claude tool
arm on the renamed corpus, random strings. Next: C3 (split C3a Study 1 / C3b Study 2), C4,
C5, D1b rework, D1e, D1f (the prereg, now with D5 and the family tiers), E1.

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
- Checkpoint zips (Omer 2026-11-09): keep the full-corpus checkpoints, remove the
  outdated ones. An agent dates every zip (when it was committed, what is inside), checks
  which scripts and docs pin each path, and proposes the removals in a PR; every removal
  goes into `MOVES.md`.

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
- **Release:** the work is attributed to Omer and to BGU: a copyright line naming him and
  Ben-Gurion University (SPL-BGU), a `CITATION.cff`, a Zenodo DOI, CC-BY-4.0 for data, MIT
  or Apache-2.0 for code (whichever is more common for academic code). BGU's policy on
  student work is checked first.

### Open decisions

- **Which two families go first** in wave 1. Omer leans gpt-oss-20b and Llama 3.1 8B; the
  agent agrees (two new vendors, opposite calling behaviour, both serving paths clean;
  Ministral is the slowest and most fragile, so wave 2). Needs Omer's yes. More small or
  MoE candidates for later tiers: GLM-4.7-Flash, Nemotron 3 Nano 30B-A3B, Granite 4.2 8B,
  gpt-oss-120b, Olmo 3 7B (`draft_release_licence_models.md` §3).
- **D5 pilot spend:** a 20-key thinking pilot, about $1.50 to $10 with the Batch API (cap
  $38.59). The full D5 set is about $102 / $204 / $459 with the Batch API at low / mid /
  high thinking use (`draft_D5_cost_and_correa.md`).
- **Tracking:** the proposal (`draft_tracking_proposal.md`: one `items.yaml`, rendered into
  this file and checked against GitHub) has 9 questions for Omer.
- **Licence holder:** BGU procedure 14-007 treats MSc research software as a possible
  service invention owned by BGU or BGN; it says nothing on open-source licences or the
  copyright line. Ask the advisor (the lab already ships MIT repos as "SPL@BGU"), then
  BGN if needed. The agent recommends MIT for code.
- **Gemma thinking (side finding, unchecked):** the Gemma 4 model card describes a
  thinking switch and vLLM 0.20.2 has a `gemma4` reasoning parser, while we serve Gemma
  with `REASONING_PARSER=none` and the CHANGELOG says it ignores the kwarg. If the card
  is right, Gemma's think=on cells may have thought for real. A read-only check of the
  stored rows is owed before D3 relies on the "21% to 0.6%" finding.
- **ISS-027 (new, P1):** the plan grader rejects correctly cased upper-case names; open
  model rows still to check (`OPEN_ISSUES.md`).
- **⚠️ STILL OPEN (Omer 2026-11-09: keep it open): E1, the six research questions
  against the two gates.** The tex frames its results as RQ1 to RQ6 plus a scorecard; the
  plan frames them as two gates (calling, delivery). The side-by-side and the suggestion
  (a baseline question plus one question per gate, problem size as a factor under each,
  the scorecard dropped) were shown to Omer on 2026-11-09 and are in
  `paper_notes_discussions.md` that day. Until Omer decides, no E step removes the RQs or
  the scorecard from the tex, and E1 drafts carry both framings.
- **Code licence** (MIT or Apache-2.0) and the copyright holder, after the BGU policy
  check.

None of these blocks the next steps. The title is chosen in plan step E6, from the candidates in
`reference/weakness_consolidated.md` Q6, once the results are in.
