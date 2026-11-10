# STATUS — what is actually left

*Content last refreshed: 2026-11-09, end of day (every open decision answered except E1,
which Omer keeps open; PRs #121 to #129 and #131 merged, only draft #130 open; pyval 0.1.6 pinned in the sibling
repo; the work list for the next sessions is in `handoff_20261109.md`); the state sections below are now rendered
from `items.yaml` (tracking Design A, item A2). Earlier that day:
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

*The sections marked "rendered" are written by `tools/tracking/items.py render` from
`development/items.yaml`. Edit that file, not the rendered text, then run `render` and
`check` (the check fails while a rendered block is out of date).*

<!-- items:begin lines -->
| line | state | open items |
|---|---|---|
| Main sweep, Study 1 (`sweep5v2-live`, `sweep6-live`) | data final. Unaided and tool-verified numbers reproduced by the rerun; its open-model delivered ranges are retired (biased low by the harness) | C5 (todo) |
| Delivered rerun, Study 2 part 1 | **complete, read out 2026-10-09** by the frozen code (`reference/delivered_rerun_readout.md`). A separate-apparatus replication: parity failed at job level (Gemma 10/10, Qwen 15/20). R1 no delivered harm · R2 unresolved · R3 the title changes · R4 met · R5 the directive suppresses calling. Figures in `NUMBERS.md` | C6 (todo), C8 (todo) |
| Extension, Study 2 part 2 | preparation (D1) under way: four new families pass the parser smoke (official Gemma 4 BF16, gpt-oss-20b, Ministral 3 14B, Llama 3.1 8B); 32K and 64K windows work and cut empty final answers steeply; the JSON constraint now binds (opt-in). Harness merged (PR #122) | D1e (todo), D1f (todo), D1g (todo), D1j (todo), D2 (todo), D3 (todo), D4 (todo) |
| PlanBench | in the tex (PR #114: equivalence test declared, corrected extractor beside the shipped numbers); open-model tools arm planned (D1e, then D2) | D1e (todo), D1j (todo), D2 (todo) |
| Steering control (nt-ster H4) | closed 2026-08-29, all six units PASS; in the tex appendix | none |
| Frontier tier and budget probe | closed for Study 1; in the tex. D5 adds new frontier cells (thinking on, larger problems, the renamed-corpus tool arm, random strings). Haiku 4.5's tool arm on the renamed corpus already ran (2026-07-12, `results/haiku-frontier/sweep6-with-tools`, 1,520 trials) and is analysed (PR #125); only Sonnet's is missing | D1g (todo), D5a (todo), D5b (todo), D5c (todo), D5d (todo), D5e (todo) |
| Paper | the 09-19 text plus PRs #110, #111, #114, #115 (merged 2026-10-09) and #123 (contamination wording, merged 2026-11-09). Title D goes (R3); the restructure is plan §4 E | B1 (doing), B2 (doing), B3 (doing), B4 (doing), B5 (doing), B6 (todo), C5 (todo), E1 (blocked), E1a (todo), E2 (todo), E3 (todo), E4 (todo), E5 (todo), E6 (todo), E7 (todo), X-03 (todo) |
<!-- items:end lines -->

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

The order is the plan's (`weakness_action_plan.md` §6): A (done) → B, C, D1 and E1 in
parallel → D2 wave 1 → D3 wave 2 → D4 readout → E2 to E7 → F. About two months to the
readout. The old step names map to items: N1 is the plan itself, N2 (the advisor round)
is item N2, N3 (before submission) is F1 to F3, N4 (hygiene) is X-01 to X-05. The work
list of the next sessions is `handoff_20261109.md` §4; each of its items is an item below.

### Waiting for Omer (rendered)

<!-- items:begin waiting -->
- **DEC-20261109-17** (open decision): E1: keep RQ1 to RQ6 and the scorecard, or move to the suggested framing (a baseline question, one question per gate, problem size as a factor under each, the scorecard dropped)? Omer 2026-11-09: keep it open. Both framings side by side in `draft_E1_research_questions.md`. Until he decides, no E step removes the RQs or the scorecard from the tex, and E1 drafts carry both framings.
- **A2** (merge; review): Tracking, migration steps 1 to 3: `tools/tracking/items.py` (render, check) with tests, `items.yaml` seeded, STATUS switched to rendered blocks. Handoff §4 item 1. The PR body lists every contradiction found while seeding.
- **C6** (read; todo): Confirm the C4 transcript readings (drafted by an AI session).
- **C7** (merge; review): ISS-027 scope and Gemma thinking: cleaned check scripts and the post hoc ISS-027 figures beside the frozen ones. Draft PR. Cleaned into tools/reanalysis/iss027_{unaided,replay,common}.py and gemma_think.py (each takes --results and halts on a failed self-check), with tests/test_iss027.py and generated caveats beside T1, T2, T5, T8a and the mechanism row. Omer takes it out of draft and merges. When it merges, tests/verify.sh conflicts with #128's line (and with A2's): keep every line.
- **N2** (your task; blocked): Advisor and coauthor round (`advisor_brief.md`): of its six questions, the venue, the thesis requirement and recording the pivot still stand; only the JAIR reformat waits on it. R7: Omer holds the round (09-19) and says when an advisor meeting happened. Never a reason to hold a task.
- **X-04** (go-ahead; todo): Cluster round, one go-ahead: the gpt-oss effort and trace smoke (command in #126's PR body); upgrade the validator plugin venv to `pddl-pyvalidator` 0.1.6 (`launch-server.sh` never upgrades an existing `.venv`); read the installed versions (B3 Q6); re-check which commit the cluster checkout sits on. Checked 2026-10-10, the checkout sat on harness/delivered-rerun at 4b2fe6e; probably stale, since the D1 smokes ran from harness/d1a-new-families. Any SSH needs Omer's go-ahead first. Handoff §4 item 11.
- **X-05** (your task; todo): Omer's laptop cleanup: nine agent worktrees under `.claude/worktrees/` (all for merged PRs), `checkpoints/sweep6-live/.DS_Store`, the untracked `rq-sweep5v2` pptx and PNGs, two old stashes from `paper/aaai27`. Earlier on 2026-11-09 Omer removed two merged worktrees and the merged branches of that time. The merged branches of #121 to #129 and #131 are on origin again. The marketplace plugin cache picks up validator 3.1.1 on the next plugin update.
<!-- items:end waiting -->

None of these blocks the next steps. The title is chosen in plan step E6, from the
candidates in `reference/weakness_consolidated.md` Q6, once the results are in.

### Can start now (rendered)

Open agent items that need nothing from Omer and wait on nothing still open.

<!-- items:begin start -->
- **B6**: Close the agent-side gaps in the B drafts before Omer's read: add Corrêa et al. to B1, fill B4's VAL TODO, re-anchor the tex line numbers after #123, fold the open questions into one answer list.
- **C5**: Retired-wording hit list for the tex, with an owner per hit (the Introduction, `tab:vdom`, `tab:decomp` and the figures have none today): nothing from the retired open-model delivered ranges survives outside the passages E replaces.
- **C8**: Post hoc splits beside the frozen figures: ISS-028 (real copying errors against goal-list trailers; check the Haiku depot p02 row) and the one ISS-029 simulate row.
- **D1e**: Open-model PlanBench with tools, engineering: ISS-025 first (patch sentinels in `planbench/apply_patches.py`), then plain and steered vLLM prompts that reuse the frozen WT format clause byte for byte, and the PR #122 serve flags in the PlanBench sbatch; the roster keeps the 4B.
- **D1g**: D5b ground truth: vendor the IPC 2023 benchmarks at a pinned commit; generate fresh problems; validate; Fast Downward at 120 s and 1800 s (three strategies); VAL every plan; report the solve shares. No model runs before this.
- **E1a**: The vocabulary: what each kept term means and which terms go; carries both RQ framings while E1 stays open.
- **F2a**: Release files: `LICENSE` (MIT, BGN line), `LICENSE-DATA` (CC-BY-4.0), `CITATION.cff` (holder BGN), notes on third-party domains in `domains/README.md`.
- **X-02**: Checkpoints follow-up: refresh the haiku and sonnet frontier overlay zips and `e2e-overlay/derived_reports.zip` with the 09-12 files (add `results/derived/budget_probe/readout_{sonnet,haiku}.json`); keep the sweep7 and probe overlays and add `e2e-overlay/README.md` (sweep7's rows are never quoted); remove the dead `.gitattributes` lfs line; add a `checkpoints/frontier/` zip set; fix the date of the NUMBERS.md "460 rows" table.
- **X-03**: Paper: point the stale `main.tex:651` comment at NUMBERS.md's Study 1 block and `tools/reanalysis/s1_*`, on a short paper branch (`sync_overleaf.sh pull` before any push); then remove the `rq-sweep5v2` PDF with a MOVES.md row.
<!-- items:end start -->

### Open PRs and branches in review (rendered)

<!-- items:begin prs -->
- **A2** (`tracking/items-yaml`; review; Omer: merge): Tracking, migration steps 1 to 3: `tools/tracking/items.py` (render, check) with tests, `items.yaml` seeded, STATUS switched to rendered blocks. Handoff §4 item 1. The PR body lists every contradiction found while seeding.
- **C7** (#130; review; Omer: merge): ISS-027 scope and Gemma thinking: cleaned check scripts and the post hoc ISS-027 figures beside the frozen ones. Draft PR. Cleaned into tools/reanalysis/iss027_{unaided,replay,common}.py and gemma_think.py (each takes --results and halts on a failed self-check), with tests/test_iss027.py and generated caveats beside T1, T2, T5, T8a and the mechanism row. Omer takes it out of draft and merges. When it merges, tests/verify.sh conflicts with #128's line (and with A2's): keep every line.
<!-- items:end prs -->

Merged 2026-11-09: #121 to #129, #131, and the sibling's #60; #124 to #129 and #131 were
reviewed and fixed first.

`tests/test_delivered_rerun_analysis.py` (hash-pinned) fails 1 of 428 when run in the
main checkout, already at `51fe971`: its "DEPENDENCIES cover every imported repo
module" check counts `.venv/` site-packages, since the venv sits inside the repo. It
passes from any worktree whose venv lives outside the repo. Not a code fault.

### Every item, by workstream (rendered)

Open items and the steps done since 2026-10-10. "waits on" lists only what is still open.

<!-- items:begin workstreams -->
**A. Records** (2 open, 1 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| A1 | Records of the 2026-10-10 answers: answer slots filled, the plan linked from STATUS and README, the paper_notes 10-10 entry | done | - | `ee7afb5` (record-only) |
| A2 | Tracking, migration steps 1 to 3: `tools/tracking/items.py` (render, check) with tests, `items.yaml` seeded, STATUS switched to rendered blocks | review (Omer: merge) | - | `tracking/items-yaml` |
| A3 | Tracking, steps 4 to 8: strip state from the plan; the check as a GitHub Action; instruction updates (development/README.md, the development-log skill, CLAUDE.md, resume-verify reads items.yaml first); the weekly read-only audit; a review after two weeks | todo | A2 | - |

**B. Text that does not depend on new numbers** (6 open, 0 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| B1 | Related work: every reference looked up and verified; Positioning rewritten so "none measures" no longer follows the La Malfa sentence (C17) | doing | B6 | - |
| B2 | The arXiv delta: what arXiv:2509.12987 found and what this paper confirms or reverses; reused in the cover letter (F3) (C17) | doing | B6 | - |
| B3 | Test data and prompts in Methods; all user prompts and their three wordings in an appendix; one sentence defining "prompt v11"; the frontier's single wording as a limit (C11, C12) | doing | B6 | - |
| B4 | One plain "by construction" sentence; the checker named (`pyval` on `unified-planning`); for solve, the planner and the validator are different programs (C2, C8, D1) | doing | B6 | - |
| B5 | The two claims that go whatever the results: "direct empirical support for the LLM-Modulo thesis" and "proves the capability boundary" (C18) | doing | B6 | - |
| B6 | Close the agent-side gaps in the B drafts before Omer's read: add Corrêa et al. to B1, fill B4's VAL TODO, re-anchor the tex line numbers after #123, fold the open questions into one answer list | todo | - | - |

**C. Checks and analyses on data already on disk** (4 open, 5 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| C1 | VAL cross-check of the answer key: VAL agrees on 1,731 of 1,732 plans (C8, D1) | done | - | #121 |
| C2 | Study 1 numbers into NUMBERS.md: calling, tool-verified, unaided and contamination, with the paired, domain-clustered, Holm-corrected tests and the GLMM refit; the replication table (C9, C13) | done | - | #121 |
| C3 | Study 1 breakdowns and Study 2 descriptive tables, by generator: per wording, per domain, classical against numeric, cost by price ratio, delivery-gap categories | done | - | #124 |
| C4 | Example transcripts from the delivered rerun, drawn by a stated rule (seeded draw 20261109) | done | - | #128 |
| C5 | Retired-wording hit list for the tex, with an owner per hit (the Introduction, `tab:vdom`, `tab:decomp` and the figures have none today): nothing from the retired open-model delivered ranges survives outside the passages E replaces | todo | - | - |
| C6 | Confirm the C4 transcript readings (drafted by an AI session) | todo (Omer: read) | - | - |
| C7 | ISS-027 scope and Gemma thinking: cleaned check scripts and the post hoc ISS-027 figures beside the frozen ones | review (Omer: merge) | - | #130 |
| C8 | Post hoc splits beside the frozen figures: ISS-028 (real copying errors against goal-list trailers; check the Haiku depot p02 row) and the one ISS-029 simulate row | todo | - | - |
| C9 | 35B call flips; Haiku 4.5 tool arm on the renamed corpus; VAL on the Claude solve plans | done | - | #125 |

**D. Experiments on the fixed setup** (12 open, 6 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| D1a | New families: official Gemma 4 BF16, gpt-oss-20b, Ministral 3 14B and Llama 3.1 8B pass the parser smoke | done | - | #122 |
| D1b | Harder test items: new item kinds in three item trees (two small validate_domain trees), no harness change; a provenance copy tool for reused rows | done | - | #127 |
| D1c | Context room smoke; 32K and 64K windows work and cut empty final answers steeply | done | - | #122 |
| D1d | JSON control; a client version where the JSON constraint binds (opt-in) | done | - | #122 |
| D1e | Open-model PlanBench with tools, engineering: ISS-025 first (patch sentinels in `planbench/apply_patches.py`), then plain and steered vLLM prompts that reuse the frozen WT format clause byte for byte, and the PR #122 serve flags in the PlanBench sbatch; the roster keeps the 4B | todo | - | - |
| D1f | The extension prereg in reference/: every cell and reading in one document, frozen in stages (wave 1, wave 2, frontier) | todo | D1e, D1g | - |
| D1g | D5b ground truth: vendor the IPC 2023 benchmarks at a pinned commit; generate fresh problems; validate; Fast Downward at 120 s and 1800 s (three strategies); VAL every plan; report the solve shares. No model runs before this | todo | - | - |
| D1h | D5a thinking pilot (20 keys per arm, Batch API, $1.69): thinking mode in `tools/claude_api_batch.py`, SDK pinned `anthropic==0.109.2`, the Corrêa 2-shot prompt vendored | done | - | #131 |
| D1i | Opt-in gpt-oss reasoning effort (`PDDL_REASONING_EFFORT`, `--reasoning-effort`) and opt-in reasoning-trace storing (`PDDL_STORE_REASONING=1`) | done | - | #126 |
| D1j | Open-model PlanBench with tools, a smoke on one model (cluster) | todo (Omer: go-ahead) | D1e | - |
| D2 | Wave 1, thinking off: the new families, the neutral 2 x 2, the 0.8B and 4B, harder items, context room, the JSON control, open-model PlanBench | todo (Omer: go-ahead) | D1f, D1j, X-04 | - |
| D3 | Wave 2, thinking on, with the main sweep's budgets | todo (Omer: go-ahead) | D2 | - |
| D4 | Readout: the frozen code on the live data; figures into NUMBERS.md; a paper_notes entry; Omer reads it before any prose is written | todo (Omer: read) | D2, D3 | - |
| D5a | Frontier thinking on, full run: Sonnet 4.6 and Haiku 4.5 thinking on, Sonnet 5.5 thinking on and off, thinking off at temperature 1, 3 repeats per problem (Batch API; approved with D5e at about $66) | todo | D1f | - |
| D5b | Larger problems: a size ladder from the IPC 2023 generators; unaided and tool-arm success and the calling rate against problem size | todo | D1g, D1f | - |
| D5c | Sonnet 4.6 tool arm on `domains-anon` (Haiku's ran and is analysed, PR #125) | todo | D1f | - |
| D5d | Two random-string maps per domain, unaided solve, Sonnet 4.6 and Haiku 4.5 | todo | D1f | - |
| D5e | Corrêa et al.'s 2-shot prompt word for word, our Gripper problems left out; Sonnet 4.6, thinking off at T=0 and thinking on with 3 repeats; one descriptive row | todo | D1f | - |

**E. The rewrite** (8 open, 1 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| E1 | The outline: the research questions against the two gates (RQ1 to RQ6 and the scorecard, or the suggested framing) | blocked | DEC-20261109-17 | - |
| E1a | The vocabulary: what each kept term means and which terms go; carries both RQ framings while E1 stays open | todo | - | - |
| E2 | Methods (with B3 and B4) and the Study 1 results | todo | E1a | - |
| E3 | Study 2 results: the delivered answers; gate 1 across families, prompts, reasoning mode and harder items; gate 2 against context room; cost | todo | D4 | - |
| E4 | The frontier tier and PlanBench, with the open models | todo | D4 | - |
| E5 | Discussion with every claim scoped to the final numbers; Limitations; Conclusion | todo | D4 | - |
| E6 | Title (from the candidates in `reference/weakness_consolidated.md` Q6, checked against the results) and abstract | todo (Omer: decide) | E3, E4, E5 | - |
| E7 | Consistency-read leftovers: E3a, E3b and E8b rewritten from the new numbers; the group F candidate additions (the first is in the tex since PR #123) | todo | D4 | - |
| E8 | Contamination wording in the tex on the paired, clustered ±5 test | done | - | #123 |

**F. Before submission** (4 open, 0 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| F1 | JAIR reformat and de-anonymising (the author block, the links block, leaving `[submission]` mode), done once after the venue is ratified | todo | N2 | - |
| F2 | Public code and data release, with the prereg documents linked and their hashes stated; the Zenodo switch (needs an SPL-BGU org owner; time it against double-blind review) | todo | F2a | - |
| F2a | Release files: `LICENSE` (MIT, BGN line), `LICENSE-DATA` (CC-BY-4.0), `CITATION.cff` (holder BGN), notes on third-party domains in `domains/README.md` | todo | - | - |
| F3 | Cover letter with the arXiv:2509.12987 delta (B2, `reference/journal_decisions_memo.md` §5); this also closes ISS-013 | todo | B2 | - |

**N. Advisor round** (1 open, 0 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| N2 | Advisor and coauthor round (`advisor_brief.md`): of its six questions, the venue, the thesis requirement and recording the pivot still stand; only the JAIR reformat waits on it | blocked | - | - |

**X. Not yet sorted into a workstream** (4 open, 1 closed)

| id | what | state | waits on | PR or branch |
|---|---|---|---|---|
| X-01 | Checkpoints prune; four June deck zips removed | done | - | #129 |
| X-02 | Checkpoints follow-up: refresh the haiku and sonnet frontier overlay zips and `e2e-overlay/derived_reports.zip` with the 09-12 files (add `results/derived/budget_probe/readout_{sonnet,haiku}.json`); keep the sweep7 and probe overlays and add `e2e-overlay/README.md` (sweep7's rows are never quoted); remove the dead `.gitattributes` lfs line; add a `checkpoints/frontier/` zip set; fix the date of the NUMBERS.md "460 rows" table | todo | - | - |
| X-03 | Paper: point the stale `main.tex:651` comment at NUMBERS.md's Study 1 block and `tools/reanalysis/s1_*`, on a short paper branch (`sync_overleaf.sh pull` before any push); then remove the `rq-sweep5v2` PDF with a MOVES.md row | todo | - | - |
| X-04 | Cluster round, one go-ahead: the gpt-oss effort and trace smoke (command in #126's PR body); upgrade the validator plugin venv to `pddl-pyvalidator` 0.1.6 (`launch-server.sh` never upgrades an existing `.venv`); read the installed versions (B3 Q6); re-check which commit the cluster checkout sits on | todo (Omer: go-ahead) | - | - |
| X-05 | Omer's laptop cleanup: nine agent worktrees under `.claude/worktrees/` (all for merged PRs), `checkpoints/sweep6-live/.DS_Store`, the untracked `rq-sweep5v2` pptx and PNGs, two old stashes from `paper/aaai27` | todo | - | - |
<!-- items:end workstreams -->

### Decisions of 2026-11-08 and 2026-11-09 (rendered)

The recorded form of Omer's answers; each has its dated `paper_notes_discussions.md`
entry. Open decisions are under "Waiting for Omer".

<!-- items:begin decisions -->
- **DEC-20261108-01** (2026-11-08) Change the contamination wording in the tex now? **Answer:** Yes, as a small paper PR stacked on #121: the paired, clustered ±5 criterion; the test chosen after the sweep; the renaming lexical only; the unresolved per-task cells marked; the frontier solve comparison called unresolved. *Affects E8; logged in paper_notes "2026-11-08".*
- **DEC-20261108-02** (2026-11-08) Which experiments answer Corrêa et al. in the extension? **Answer:** Approved for the extension prereg (plan D5): frontier thinking on (Sonnet and Haiku, plus other frontier vendors such as GPT and Gemini); larger problems (a size ladder from the IPC 2023 generators); the Claude tool arm on the renamed corpus. *Affects D5a, D5b, D5c, D1f; logged in paper_notes "2026-11-08".*
- **DEC-20261109-01** (2026-11-09) D1b: where do the results live, and how are the new item kinds loaded? **Answer:** A new sweep folder; reused rerun rows copied in with `reused_from_folder`, `reused_from_job`, `reused_from_sha256`, `copied_at` (`tools/extension_copy_reused.py`); the prereg declares the reuse. `delivered-rerun/`, `sweep5v2-live`, `sweep6-live` never touched. Loader: two small validate_domain trees (`domains-hard-vd-a/`, `-vd-b/`), no harness change. Trees a and b must write to separate output folders (both name the invalid job `domain_neg`). No SLURM job id is stored in any results file, so the copy tool takes it as an argument (job ids are in `reference/delivered_rerun_prereg.md` §8). Why: after the 35B flips, a rerun is not identical to the original, so reused rows must stay identifiable. *Affects D1b, D1f; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-02** (2026-11-09) Llama 3.1 8B: which weights? **Answer:** Unsloth's ungated copy stays (weights byte-identical to Meta's). Omer's condition was "if its weight files match Meta's byte for byte". Checked 2026-11-09: all four shards and the index match Meta's LFS pointers; only small config and tokenizer metadata differ, with the same chat template and stop tokens (`draft_release_licence_models.md` §2). *Affects D2, D1f; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-03** (2026-11-09) GPT-OSS: which reasoning effort? **Answer:** Effort low in wave 1, medium in wave 2, sent explicitly (`PDDL_REASONING_EFFORT`, `--reasoning-effort`); labelled "low effort", never "thinking off". gpt-oss puts the current date in its system message; pin it if runs must be reproducible. *Affects D1i, D2, D3, D1f; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-04** (2026-11-09) The 35B calling rate: which run is quoted? **Answer:** Quote both runs (68.0 and 82.7); "bigger calls less" is a direction only; the 35B cells go into the extension's repeat check (anchor slice, with a trial-level flip-rate endpoint). *Affects D1f, E2; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-05** (2026-11-09) Families: which go in which wave? **Answer:** Wave 1 = gpt-oss-20b and Llama 3.1 8B plus the official Gemma 4 BF16; Ministral 3 14B = wave 2. Every family that passed the smoke is registered now as a numbered tier with the same analysis, so adding one later needs only a go-ahead. Later tiers (each must pass the parser smoke): GLM-4.7-Flash, gpt-oss-120b. Passed over: Nemotron 3 Nano, Granite 4.2 8B, Olmo 3 7B. Omer: keep only the later-wave models of high value to the paper. GLM-4.7-Flash is a third family with a real thinking on/off switch, so the reasoning-mode finding (Gemma's calling falls from 21% to 0.6%) can be tested outside Qwen and Gemma; a new vendor and a fast MoE. gpt-oss-120b is the same family as the 20b at a larger size, so "bigger calls less" gets a test in a second family; a fast MoE that needs a GPU to itself. Passed over: Nemotron 3 Nano (a new architecture the paper's questions do not ask about; prefix caching unchecked), Granite 4.2 8B (dense and slow; Llama already fills the 8B rung), Olmo 3 7B (open training data would allow a direct contamination search, but that is a separate project; its thinking variant is a separate checkpoint, not a switch). *Affects D1f, D2, D3; logged in paper_notes "2026-11-09 (evening)".*
- **DEC-20261109-06** (2026-11-09) Gemma, wave 2 (thinking on): which reasoning parser? **Answer:** Keep `REASONING_PARSER=none`, as in Study 1. No parser side run. *Affects D3, D1f; logged in paper_notes "2026-11-09 (night)".*
- **DEC-20261109-07** (2026-11-09) PlanBench roster (D1e): keep the 4B? **Answer:** Keep the 4B (its failures are data). More small or MoE candidates may be suggested; each must pass the parser smoke. *Affects D1e, D1j, D2; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-08** (2026-11-09) D5a: which models and settings, and the full run? **Answer:** Sonnet 4.6 and Haiku 4.5 thinking on; Sonnet 5.5 thinking on and off (`between_tools`); thinking off at temperature 1 on the same problems; 3 repeats per problem. Full run approved (about $51 with the Batch API, range $33 to $72; the D5e cells add about $14 thinking on and $1.72 thinking off, so about $66 in all). Omer has $186 loaded plus a work account; when the loaded credits are used up, decide what comes next. It runs only after the D1f prereg holds the cells. Cost method (moved here from STATUS): the D5e thinking-on cell (95 problems x 3 = 285 trials) adds about $14 (about $10 to $19; 2-shot input from pilot arm e (7,626 tokens per trial), output = arm a's mean Sonnet 4.6 thinking (4,123 tokens, bootstrap CI) plus arm e's mean answer (887), at Batch prices of $1.50 / $7.50 per MTok); its thinking-off cell adds $1.72 (95 x 1). PR #131 review. *Affects D5a, D5e, D1f; logged in paper_notes "2026-11-09 (late night) — D5a".*
- **DEC-20261109-09** (2026-11-09) D5b: which larger problems? **Answer:** Add some of Corrêa et al.'s IPC 2023 domains and problems. Ground truth first (validate, solve with the planner, VAL every plan), and report the share solved within 120 s and within 30 min, before any model runs. Their 360 tasks are not released; use the IPC 2023 generators (`github.com/ipc2023-learning/benchmarks`, HEAD `19d6a8a` on 2026-11-09, no licence file) and their domain files, not ours. *Affects D1g, D5b; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-10** (2026-11-09) D5c: what is still owed? **Answer:** Sonnet 4.6 tool arm on `domains-anon` (Haiku's already ran and is analysed, #125). *Affects D5c; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-11** (2026-11-09) D5d: random strings, in which form? **Answer:** Two random-string maps per domain, unaided solve, Sonnet 4.6 and Haiku 4.5. The cheapest form, about 800 trials. *Affects D5d; logged in paper_notes "2026-11-09 — Repo audit".*
- **DEC-20261109-12** (2026-11-09) D5e: the Corrêa 2-shot prompt cell? **Answer:** Corrêa's 2-shot prompt word for word, our Gripper problems left out (their example is a different Gripper domain under the same name); Sonnet 4.6, thinking off at T=0 and thinking on with 3 repeats; one descriptive row. Their instructions, the Gripper and Logistics worked examples and their checklist, then our problem; Logistics is not in our corpus. Thinking off at T=0 matches the existing 28.7% cell; thinking on matches D5a. Same grader; the pilot checks that the answer reader reads their plan format, and if it does not, Omer is asked before anything changes. Outside the confirmatory set, never pooled with v11 to v13. *Affects D5e; logged in paper_notes "2026-11-09 (later)".*
- **DEC-20261109-13** (2026-11-09) The pyval case bug (ISS-027): who fixes it, and what does the extension grade with? **Answer:** Fixed by us in `pddl-pyvalidator` 0.1.6 (released on PyPI) and pinned in the validator plugin (sibling #60). The extension grades with 0.1.6 and D1f records it. The cluster's plugin venv still needs the upgrade (X-04). *Affects D1f, C7, X-04; logged in paper_notes "2026-11-09 (night)".*
- **DEC-20261109-14** (2026-11-09) Release (plan F2): owner, licences, author? **Answer:** BGN Technologies owns research artifacts by default; no check needed. Code MIT, data CC-BY-4.0 (only data we produced; third-party domains keep their terms). Copyright line proposed: "Copyright (c) 2026 B.G. Negev Technologies and Applications Ltd. (BGN Technologies)"; confirm BGN's exact legal name before publishing. Omer is the author in `CITATION.cff` and on the Zenodo DOI, lab SPL-BGU. Mind double-blind review: the named citation file and DOI may have to wait until after review. Replaces the earlier entry of the same day ("MIT or Apache-2.0 for code; BGU's policy on student work is checked first"). *Affects F2a, F2; logged in paper_notes "2026-11-09 (close)".*
- **DEC-20261109-15** (2026-11-09) Tracking: which design, and the answers to the proposal's Q2 to Q9? **Answer:** Design A of `draft_tracking_proposal.md`, with the recommended answers to Q2 to Q9: read state in STATUS.md; a failed check on a record-only push is a red mark the agent fixes the same day; the agent marks an item done once its PR is merged; ids `DEC-YYYYMMDD-NN` and next-number-in-workstream (`X-##` until sorted); `ISS-###` stay in `OPEN_ISSUES.md` with a link; seed open items and steps done since 2026-10-10; a weekly read-only audit; no dependency graph for now. *Affects A2, A3; logged in paper_notes "2026-11-09 (close)".*
- **DEC-20261109-16** (2026-11-09) Checkpoints: the five #129 questions? **Answer:** Refresh the haiku and sonnet frontier overlay zips and `e2e-overlay/derived_reports.zip` with the 09-12 files (and add `results/derived/budget_probe/readout_{sonnet,haiku}.json`); keep the sweep7 and frontier-with-tools-probe overlays (a rebuild without them gives 442 rows, not 460) and add an `e2e-overlay/README.md` saying sweep7's rows are never quoted; remove the dead `.gitattributes` lfs line for `checkpoints/sweep5/*.zip`; fix the stale comment at `paper/main.tex:651`, then remove the `rq-sweep5v2` PDF with a `MOVES.md` row. Also add a `checkpoints/frontier/` zip set. *Affects X-02, X-03; logged in paper_notes "2026-11-09 (close)".*
- **DEC-20261109-18** (2026-11-09) The D5 thinking pilot? **Answer:** Yes: 20 keys per arm, Batch API, about $1.50 to $10, hard cap $40. It measures thinking tokens and the answer-parse rate only; plan success is not computed, so the pilot does not peek at the outcome. The prereg declares it. Ran 2026-11-09, PR #131, $1.69. *Affects D1h, D1f; logged in paper_notes "2026-11-09 (evening)".*
- **DEC-20261109-19** (2026-11-09) C3 tex fragments: where do the table caveats live? **Answer:** The generated fragments (`tools/reanalysis/out/tex/s1_*.tex`) carry only the cell marks (¶ for unaided simulate). The explanation of the mark, the ISS-027 note and the 35B both-runs note stay as `%` comments at the top of each fragment and must be written into the caption of the table that wraps it. Whoever places a fragment in the tex writes that caption. *Affects C3, E2, E3; logged in paper_notes "2026-11-09 (late night) — C3".*
<!-- items:end decisions -->
