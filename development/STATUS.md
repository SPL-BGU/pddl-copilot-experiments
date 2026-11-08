# STATUS — what is actually left

*Content last refreshed: 2026-11-08 (contamination-wording paper PR, stacked on #121;
plan step D5 added and approved, the answer to Corrêa et al.). Before that 2026-11-01 (C1, C2 in PR #121; B drafts on `main`; the D1
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
(`draft_B1_B2_related_work.md`, `draft_B3_B5_methods.md`), waiting for Omer's read. C1
and C2: PR #121 (VAL agrees on 1,731 of 1,732 plans; Study 1 block in `NUMBERS.md`). D1a,
D1c, D1d: smokes passed (`reference/d1_smokes_20261027.md`), harness PR #122. D1b: built
on local branch `fixtures/d1b-harder-items`, write-up and one decision open. The
contamination wording in the tex now uses the paired, clustered ±5 test (paper PR from
`claude/frontier-llms-paper-analysis-6jst6i`, stacked on #121: merge #121 first). Plan step
D5, approved 2026-11-08, answers Corrêa et al.'s "Frontier LLMs Rival State-of-the-Art
Planners": frontier thinking on, larger problems, the Claude tool arm on the renamed
corpus. Next: C3 to C5, D1e, D1f (the prereg, now with D5), E1.

## Where each line stands

| line | state |
|---|---|
| Main sweep, Study 1 (`sweep5v2-live`, `sweep6-live`) | data final. Unaided and tool-verified numbers reproduced by the rerun; its open-model delivered ranges are retired (biased low by the harness) |
| Delivered rerun, Study 2 part 1 | **complete, read out 2026-10-09** by the frozen code (`reference/delivered_rerun_readout.md`). A separate-apparatus replication: parity failed at job level (Gemma 10/10, Qwen 15/20). R1 no delivered harm · R2 unresolved · R3 the title changes · R4 met · R5 the directive suppresses calling. Figures in `NUMBERS.md` |
| Extension, Study 2 part 2 | preparation (D1) under way: four new families pass the parser smoke (official Gemma 4 BF16, gpt-oss-20b, Ministral 3 14B, Llama 3.1 8B); 32K and 64K windows work and cut empty final answers steeply; the JSON constraint now binds (opt-in). Harness PR #122. Not yet: D1e (PlanBench tools), D1f (prereg) |
| PlanBench | in the tex (PR #114: equivalence test declared, corrected extractor beside the shipped numbers); open-model tools arm planned (D2) |
| Steering control (nt-ster H4) | closed 2026-08-29, all six units PASS; in the tex appendix |
| Frontier tier and budget probe | closed; in the tex |
| Paper | the 09-19 text plus PRs #110, #111, #114, #115 (merged 2026-10-09). Title D goes (R3); the restructure is plan §4 E |

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

- Cluster checkout: checked 2026-10-10, it sits on `harness/delivered-rerun` at `4b2fe6e`
  (the rerun's pinned harness), not on the dead `paper/iter2-decoupled-run`. D1 branches
  from there. Any SSH needs Omer's go-ahead first.

### Open decisions

- **D1b and the frozen files.** The harder items need two invalid domains per folder to
  balance validate_domain; the builder edited `run_experiment.py`, `pddl_eval/domains.py`
  and `pddl_eval/runner.py`, which are in the frozen rerun package hash. Alternative with
  no harness change: a second small tree for validate_domain, one problem per domain.
- **Llama weights:** unsloth's ungated copy (in use) or Meta's gated repo.
- **GPT-OSS effort level** for its wave-1 cells (it cannot switch reasoning off).
- **The 35B calling rate did not replicate** in three cells (solve plain 68.0 → 82.7);
  the tex's "68%" and the size inversion rest on it (`NUMBERS.md` T8a, PR #121).
- **D5a model versions:** Sonnet 4.6 and Haiku 4.5 (the within-model thinking contrast),
  the 5.5 family (the current tier), or both; plus which GPT and Gemini models.
- **D5d, the random-string corpus:** worth running or not (plan §4 D5).

None of these blocks the next steps. The title is chosen in plan step E6, from the candidates in
`reference/weakness_consolidated.md` Q6, once the results are in.
