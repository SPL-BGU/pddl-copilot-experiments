# Handoff — review round and pre-submission work (written 2026-09-18)

**Pick up with** `/resume-verify development/review_round_handoff.md`.

**Read first:** `STATUS.md` → "Next steps" (N2–N5; open decision slots R7 and R8). This file is the
operational pickup only. It never overrides `STATUS.md` (what is left) or `NUMBERS.md`
(which value of each figure to quote). If this file and the repo disagree, the repo wins.

## The one thing that changed today: the repo has a single line of work

Until 2026-09-18 the paper lived on a long-lived `paper/aaai27` branch in a separate
worktree, and `main` carried a stale `paper/main.tex`. That is over. **Older docs, the
append-only logs and older memory notes still say "on `paper/aaai27`" or "in the
worktree" — read those as history.**

| before | now |
|---|---|
| paper on `paper/aaai27`, in `../pddl-copilot-worktrees/paper-aaai27` | paper on `main`, in the normal checkout; branch and worktree are deleted |
| `paper/main.tex` on `main` was stale | `paper/main.tex` on `main` **is** the paper |
| Overleaf Action fired on pushes to `paper/aaai27` | fires on pushes to `main` that touch `main.tex`, `refs.bib`, the two style files or `figures/**` — in practice, when a PR touching the paper is merged |
| `sync_overleaf.sh` needed `OVERLEAF_CLONE=…` from the worktree | run it from the main checkout, no env var needed |
| main ↔ paper branch merged back and forth | nothing to merge back and forth |

How it was done: PR #101 (merge commit `75e070f`, deliberately not squashed so the paper
hashes cited in `development/` stay reachable) and PR #102 (`dc9e3f0`, Action retarget +
docs). Record: `paper_notes_discussions.md`, entry "2026-09-18 — One line of work".

## State at write time — each line is checkable

The first two rows describe the moment of writing. Since then PR #103 (branch
`docs/advisor-brief`) was opened; it carries this file, the advisor brief and the
doc-cleanup plan. Until it is merged, expect that one extra branch and one open PR.

| claim | check |
|---|---|
| only `main` exists, locally and on origin (plus `docs/advisor-brief` until PR #103 is merged); no worktrees; tree clean | `git branch -a`, `git worktree list`, `git status --short` |
| `main` = `dc9e3f0` or later; no open PRs other than #103 | `git log --oneline -5`, `gh pr list` |
| every Overleaf-synced file on `main` is byte-identical to Overleaf head `a0b8c84` ("Update paper from monorepo"), so no coauthor edits are waiting | `git fetch overleaf`, then for each of `main.tex`, `refs.bib`, `aaai2027.sty`, `aaai2027.bst`: `git diff --quiet main:paper/<f> overleaf/main:<f>`; for the figures compare blob hashes: `diff <(git ls-tree -r main:paper/figures \| grep '\.pdf$' \| awk '{print $3,$4}') <(git ls-tree -r overleaf/main:figures \| grep '\.pdf$' \| awk '{print $3,$4}')`. Re-run 09-18 over the full set: all identical |
| the Action works from `main`: run 35335139473 (manual dispatch) green, "Overleaf already up to date" | `gh run list --workflow overleaf-sync.yml --limit 3` |
| paper compiles from `main`: 0 errors, 25 pages, 0 undefined refs, one overfull box (129.9 pt, tex lines 755–796, the scorecard `table*`) | `cd paper && latexmk -pdf main` |
| title D + the two-gate abstract (four verified numbers + the 273,600-trial scale clause) + "invocation rate" at all 14 sites are in the tex — N1 is closed | `STATUS.md` N1; `NUMBERS.md` "Abstract — the four figures" |
| no experiment is owed, no `\todo` is left, all three writing jobs are in Overleaf | `STATUS.md` "The one-paragraph answer" |

This file is committed together with the advisor brief and the doc-cleanup plan
(PR #103, branch `docs/advisor-brief`). Do not commit it a second time.

## How to work now (the new routine)

1. `git checkout main && git pull`, then a short branch: `paper/<topic>` for tex,
   `docs/<topic>` for records, `feat/<topic>` for code. One at a time.
2. Tex edits: `development/sync_overleaf.sh pull` first (commit if anything came down),
   then edit, compile, commit.
3. Push the branch, open a PR. **The agent cannot merge a PR nobody reviewed — the
   harness blocks it.** Show Omer the diff in chat; he merges (on GitHub, or
   `! gh pr merge <n> --squash` in the session). Squash is fine for small PRs. After a
   squash the branch hashes do not exist on `main`, so record the **squash-merge hash**,
   not a branch hash, in `paper_notes_discussions.md` and `NUMBERS.md`.
4. A merged PR that touches the synced paper files pushes to Overleaf by itself. Check
   the run is green. A red run means a coauthor edited Overleaf: pull, reconcile, push.
5. No commit carries a Claude credit line. Editing `.github/workflows/` needs Omer's
   explicit go.

## The sequence

**Step 1 — Advisor brief. DONE 2026-09-18 (PR #103). Do not rewrite
`development/advisor_brief.md`: the advisors fill in its `> ANSWER:` lines, and a rewrite
would erase them.** What is left of this step is Omer sending it (Step 3, R7). For the
record, the brief is: one page, the six questions of `STATUS.md` N2 with
inline `> ANSWER:` slots (not popups), each with a one-line recommendation and the
source section. Sources: `journal_decisions_memo.md` §5 (venue) and §10 (open questions
for advisors), `paper_notes_discussions.md` 08-30 (budget ledger, the reopened
Sonnet-tier PlanBench decision), `archive/cost-breakdowns/` (cost-of-pass deck).
The six: venue ratification (JAIR primary, TMLR fallback) · thesis needs *submitted*
not *accepted* · record the journal pivot · cost-of-pass deck verdict · storage-fixed
rerun of ~5 headline cells (contingency or before submission) · Sonnet-tier PlanBench
extension (run or leave excluded). Branch `docs/advisor-brief`, with this handoff and a
row for each file in `development/README.md`.

**Step 2 — Documentation cleanup (agent; plan first, Omer approves, then execute).**
The plan is written and approved (`development/archive/plans-executed/doc_cleanup_plan.md`, "ok all" on 09-18).
Executed the same day as two stacked PRs: #104 "moves only", then #105 "rewrites".
Omer merges #103, #104, #105, in that order.
If all three are merged, this step is closed. Full brief in the section "Step 2 in detail" below. Do it right after the brief, while
the manuscript is out with the advisors: every later session reads these docs first.

**Step 3 — Omer, any time: answer R7 and R8 in `STATUS.md`** (the two empty slots).
R7: send the manuscript + brief to coauthors and advisors — recommendation yes, the
"after N1" condition is met. R8: Llama-3.1-8B probe — recommendation hold until the
advisor round. A fresh `paper/main.pdf` (25 pages) is built locally for sending.

**Step 4 — N3 items that do not wait for advisor feedback (agent, one `paper/` branch each or one combined):**
- Fix the overfull scorecard `table*` (tex lines 755–796).
- One whole-paper consistency read: "invocation rate" everywhere, AI-prose tells in the
  Job 2 / Job 3 additions, CI-vs-censor-bound notation in the newest tables. Report
  findings first; do not rewrite prose unprompted.
- Cover letter with the delta against arXiv:2509.12987 (our own earlier version — a
  self-citation, not prior art). Writing it closes ISS-013.

**Step 5 — gated on the advisor round:** JAIR reformat (touches every float, do it once,
after the venue is ratified); any prose changes the advisors ask for.

**Step 6 — N5 hygiene (minutes):** the ISS-022 strike is folded into Step 2. The cluster
checkout still sits on the dead `paper/iter2-decoupled-run` branch; moving it to `main`
needs SSH, so **ping Omer first**.

**Separate small PR, any time:** the push guard in `sync_overleaf.sh` only checks that
the newest Overleaf commit subject is "Update paper from monorepo". After a legitimate
pull-and-reconcile of coauthor edits a plain `push` still aborts and needs
`FORCE_OVERWRITE=1`. Do not mix this fix into another PR; it changes the safety guard.

## Step 2 in detail — clean up documentation that would mislead a future LLM session

**Why.** A fresh session trusts what it reads first. Several docs still describe closed
work as open, a retired venue as the target, a deleted branch as the place to edit, or a
removed backend as usable. The goal is that **the path and the first screen of every
live doc tell the truth**, so a model never has to read 2,000 lines of log to find out
a decision was reversed.

**Starting inventory (surveyed 2026-09-18 — re-verify, the counts are grep hits):**

**This table is a record of what was wrong on the morning of 09-18. Every row has since
been fixed (PRs #104 and #105); do not act on it again.** Paths in this table
are as they were at the survey. The moves of rows A and C were made
on 09-18 (PR "moves only"); `MOVES.md` "Third wave" gives the new path of each file.

| # | where | what is wrong | likely fix |
|---|---|---|---|
| A | `development/` root holds 19 docs; `development/README.md` still says "Root — live (12 docs)" and was last touched 08-30 | root means *live*, but these are closed: `frontier_budget_probe_handoff.md` (CLOSED 09-12), `frontier_budget_probe_prereg.md` + `_readout.md` (ratified, in tex), `job2_delivered_reframe_worknote.md` (Job 2 closed), `dev_docs_refactor_plan.md` (check whether the 08-29 pass ran), `ntster_h4_final_readout_20260829.md` (Job 3 closed), and probably `iss024d_parity_prereg.md`, `sonnet_wt_vs_haiku_e2e_memo.md`, `tool_call_vs_final_output_grading.md` | `git mv` to `reference/` (stable specs, preregs, readouts that `NUMBERS.md` cites) or `archive/` (handoffs, worknotes, executed plans); one `MOVES.md` row per move; refresh the README map |
| B | `STATUS.md` (385 lines) | about three quarters is closed material: Jobs 1–4 DONE sections, finished housekeeping, N1's "Original text of this item" (it still instructs "edit on `paper/aaai27` in the worktree"), answered R5/R6 slots, a 10-line refresh history in the header; 22 mentions of the deleted branch | edit in place: one closed-work table (what · tex location · commit · where the record lives), drop N1's original text, move answered slots to a short "decided" list, header = latest refresh only |
| C | `paper/HANDOFF.md`, `paper/GOALS.md`, `paper/REVIEW_AND_REWRITES.md`, `paper/automated-platforms-review/iter1+iter2/` | June-era; they sit beside `main.tex`, so they are the first thing a model opens for paper work. `HANDOFF.md` names the dead branch `paper/aaai27-single-tool-draft`, says AAAI-27 nine times and carries a paste-ready "Continue the AAAI-27 paper on branch…" prompt; `REVIEW_AND_REWRITES.md` cites the stale corpus mirror twice | move to `development/archive/paper-june/` (none of them is Overleaf-synced, so moving is safe); check the iter1/iter2 action plans for any item still open before archiving and carry open items into `STATUS.md` |
| D | venue framing: `CLAUDE.md` ("The AAAI-27 paper…"), the title of `paper-git-overleaf-instructions.md`, `paper/README.md` ("Per AAAI rules… anonymous template") | AAAI-27 is formally off since 08-30; target is JAIR, TMLR fallback | say "the journal paper (JAIR target; still typeset with `aaai2027.sty` until the N3 reformat)". File names `aaai2027.*` stay |
| E | Ollama (retired 2026-05-18/23): `cluster-experimenting/README.md` (11 hits), `EXPERIMENTS_FLOW.md` (8), `.claude/skills/cluster-ops/SKILL.md` (3) | instructions for a backend that no longer exists | classify each hit: the `cis-ollama.*` **hostname** is real and stays; how-to text for the removed backend goes. Code hits (`status.sh` 4, analyzer `_constants.py` 5) are **not** part of this pass — list them for a separate `feat/` PR |
| F | chain phase (archived 2026-05-05): `EXPERIMENTS_FLOW.md` (3), `OPEN_ISSUES.md` (3), `paper/GOALS.md` (1) | describes a phase that is not wired in | remove or mark archived; the warning sentence in `CLAUDE.md` stays |
| G | `OPEN_ISSUES.md` (last touched 08-29) | ISS-022 is closed but not struck; mentions a dead branch; other rows unverified since August | re-verify every open row against the repo, strike the closed ones |
| H | top-level `README.md` (last touched 06-15) and `EXPERIMENTS_FLOW.md` (601 lines, 08-29) | predate the e2e grading overlay, the frontier runner, PlanBench and the journal pivot | check each command against `run_experiment.py --help` and the current `pddl_eval/` layout; fix or cut |
| I | `.claude/skills/` (`development-log`, `plan-review-simplify`, `debug-and-simplify`, `cluster-ops`) and `.claude/agents/` | not reviewed since the single-line model and the Ollama removal | read each for paths, branches and tools that no longer exist |
| J | agent memory, `~/.claude/projects/-Users-omereliyahu-personal-pddl-copilot-experiments/memory/` (79 files; index lines up to 400+ characters) | about a dozen entries are pure closed-status ("DONE", "CLOSED", "RESOLVED", "HISTORICAL", "retired", "moot"): three Ollama entries, the `submit_with_rtx` and async-write RESOLVED notes, worktree-for-main-push (moot), the ollama-probe note, the 05-12 CIS endpoint snapshot, plus one entry per closed job | delete entries that are only history the repo already records; merge the closed-job entries into one "closed lines — quote `NUMBERS.md`" entry; **keep every `feedback` entry and every non-obvious lesson**; cut index lines to one short hook. No PR needed (outside the repo) |

**Hard rules for the cleanup — these protect the record:**

1. **Never edit** the append-only logs (`paper_notes_discussions.md`, `CHANGELOG.md`),
   any prereg, any ratified readout, anything a freeze record hashes, or the *content*
   of files already in `archive/` and `reference/`. Moving a file into those tiers is
   fine; rewriting it is not. Old wording in a log is history, not an error.
2. **Move, do not delete.** `git mv` + a `MOVES.md` row + the README map. Delete only a
   true duplicate, and say which file it duplicates.
3. **Before cutting a block from `STATUS.md`, confirm the same fact exists** in
   `paper_notes_discussions.md` or `NUMBERS.md`. If it does not, move it there first.
4. **Repair inbound links after every move:** grep the old path across live docs,
   `.claude/skills/`, `tools/` and scripts. `NUMBERS.md` cites several readouts by path.
5. **No number changes.** This pass touches wording and location only. A figure that
   looks wrong goes to `/verify-claims` and gets its own entry, not a silent fix.
6. Docs only. Dead code, dead CLI flags and stale constants go on a list for a
   separate `feat/` PR.

**How to deliver it (the plan, then two PRs, smallest first, so each diff is easy to review):**

1. `doc_cleanup_plan.md` (now in `development/archive/plans-executed/`) — **written 09-18, rides in PR #103 with the brief
   (no PR of its own).** One table, a row per file: verdict (keep / move
   to `reference/` / move to `archive/` / rewrite section / cut) · one-line reason ·
   `> ANSWER:` slot. Omer approves in the file. Nothing moves before that.
2. PR "moves only": `git mv`, `MOVES.md`, README map, link repair. No body text changes,
   so the diff is renames plus a few path strings.
3. PR "rewrites": `STATUS.md` compression, venue framing (D), Ollama and chain how-to
   text (E, F), `OPEN_ISSUES.md`, top-level README / `EXPERIMENTS_FLOW.md`, skills.
   Memory (J) is done alongside, outside the repo.

**Done means (run both, paste the results in the PR):**

- **Grep residue.** In the live set (`CLAUDE.md`, top-level `*.md`, `.claude/`,
  `cluster-experimenting/README.md`, `paper/*.md`, `development/*.md` except the two
  append-only logs), the terms `paper/aaai27`, `worktree`, `single-tool-draft`,
  `paper/iter2`, `AAAI-27`, `ollama`, `chain phase` appear only in sentences that say
  the thing is gone (the `cis-ollama` hostname is the one allowed exception).
- **Cold-read test.** Start a fresh subagent with no context and only the repo. Ask:
  where is the paper edited and how does it reach Overleaf · what is the target venue ·
  what work is left · which corpus are numbers verified against · which inference
  backend exists · is the chain phase active. Every answer must match `STATUS.md` and
  `CLAUDE.md`. A wrong answer names the doc that misled it — fix that doc and rerun.

## Standing rules that bind every step

- Before any tex edit that touches a number: `/verify-claims`, and check `NUMBERS.md`.
  Verify only against `results/sweep5v2-live` + `*_sweep6`;
  `results/sweep5-cluster-20260530` is a stale partial mirror.
- Before editing any paper claim: grep `development/` for pending rewrite specs and the
  bottom lines in `paper_notes_discussions.md`. The tex is not the ground truth.
- Every paper-related decision gets a dated, bulleted `paper_notes_discussions.md` entry.
- `STATUS.md` is edited in place, never succeeded by a dated copy.
- Never recommend cutting content for page budget; the advisors filter.
- Never force-push to Overleaf. Always pull before push.
- No cluster / SSH / SLURM action without Omer's go-ahead.

## Left alone on purpose

- Two git stashes labelled "On paper/aaai27": `stash@{0}` describes itself as
  superseded by `1ac21f4`; `stash@{1}` holds untracked `.codex` + `.agents` tooling.
  Omer has not asked for either to be dropped.
- `HANDOFF.md`, `GOALS.md`, `REVIEW_AND_REWRITES.md` (now in
  `development/archive/paper-june/`, moved 09-18) still name the even older branch
  `paper/aaai27-single-tool-draft`. They are June-era records, not live instructions.
  **Do not follow them.**
- `AGENTS.md` is a local symlink to `CLAUDE.md` (excluded from git), so it is always
  current and needs no cleanup.
