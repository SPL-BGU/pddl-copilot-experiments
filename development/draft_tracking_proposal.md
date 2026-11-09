# Draft: a new way to track the open items

*Draft for Omer, 2026-11-09. Nothing here is built yet. Answer the questions in §5; the
agent then builds the chosen design in small steps (§4). Delete this file once the
design is in place, and record its last commit in `MOVES.md`.*

## 1. Why the current system drifts

Today the state of one item (say D1b) is written by hand in up to six places:
`STATUS.md`, `weakness_action_plan.md`, `OPEN_ISSUES.md`, `NUMBERS.md`,
`paper_notes_discussions.md` and a `draft_*.md`. Nothing checks that they agree. Four
root causes explain what the 2026-11-09 audit found:

1. **State is prose.** "PR #123 is stacked on #121" is a sentence. When the PR merges,
   nobody gets told the sentence is now wrong, so `STATUS.md` was stale within a day.
2. **No single owner for a fact.** The plan, STATUS and the drafts each restate the same
   fact in their own words. Two copies can disagree, and they did: the plan said D5c's
   tool arm "ran on the canonical corpus only", while Haiku's anon tool arm ran in July;
   the plan's D1e described work that is already on `main`.
3. **Nothing links an item to its evidence.** A claim like "D1b built, write-up open"
   points at a branch and a file, but no script checks that the branch is on GitHub or
   that the file exists. So a finished build sat on a local branch, citing a write-up
   that does not exist.
4. **Decisions and dependencies have no home.** The 12 decisions of 2026-11-09 were made
   in chat and must be copied by hand into three files. "D1f waits on 9 decisions" and
   "E2 waits on E1a" live only in sentences, so no one can ask "what can start now?".
   New audit items got ad hoc names (NEW-1 to NEW-6).

What already works and should stay: plan step ids (A1, C3, D1b, D5a) are short and
used everywhere; `ISS-###` for harness gaps; `NUMBERS.md` as the one place for
figures; the append-only logs; "the path carries the status".

## 2. Three designs

All three keep the prereg, the frozen hashes and the append-only logs untouched. The
frozen package hash covers `run_experiment.py`, `pddl_eval/` and the modules they import
(`reference/delivered_rerun_prereg.md`), so new files under `tools/tracking/` and
`development/` change no hash.

### Design A: one items file in the repo, rendered and checked by a script

One file, `development/items.yaml`, holds every open item and every decision. Each
item has a few fixed fields:

```yaml
items:
  - id: D1b
    title: Harder test items
    state: blocked        # todo | doing | blocked | review | done | dropped
    owner: agent          # agent | omer
    waits_on: [DEC-20261109-01]   # item or decision ids
    needs_omer: none      # none | decide | read | go-ahead | merge
    branch: fixtures/d1b-harder-items
    pr: null
    evidence: [development/reference/d1b_harder_items.md]
    plan: weakness_action_plan.md#d1
    updated: 2026-11-09
decisions:
  - id: DEC-20261109-01
    question: Where do the D1b results live?
    answer: "New sweep folder; copied rerun rows keep a source field ..."  # Omer's words
    decided: 2026-11-09
    affects: [D1b, D1f]
    logged: paper_notes_discussions.md#2026-11-09
```

A script, `tools/tracking/items.py`, does two jobs:

- **render**: writes the live parts of `STATUS.md` between marker comments: a table
  per workstream, a "Waiting for Omer" list (open decisions plus items with
  `needs_omer`), a "Can start now" list (open items whose `waits_on` are all done), and
  a small Mermaid graph of what waits on what (GitHub draws it). The hand-written top
  paragraph and the binding rules in `STATUS.md` stay as they are.
- **check**: fails with a plain message on any contradiction it can test: a PR listed
  as open that GitHub says is merged (via `gh pr view`); a branch that is not on
  `origin`; an evidence path that does not exist; a `waits_on` id that does not exist or
  forms a loop; an item marked done with no evidence; a decision with an answer but no
  matching dated entry in `paper_notes_discussions.md`; a `STATUS.md` whose rendered
  block differs from what the file would produce now.

The check runs in a GitHub Action on every push and PR, and the agent runs it at the
start and end of each session.

- **Fixes:** pain 1 (PR state is checked against GitHub), 3 (branch and file checks),
  5 (the graph and "can start now"), 6 (one id rule), and most of 4 (a decision is
  written once; the paper_notes entry is checked for, then the agent appends it).
  Pain 2 shrinks because the plan stops carrying state (§4 step 4), so one copy is left.
- **Costs Omer:** reading one rendered `STATUS.md` (it works on the GitHub phone app);
  answering decisions where he answers them now. No new tool, no account setup.
- **Limits:** a script cannot tell that a prose claim is false ("ran on the canonical
  corpus only"). It can only demand a link. A periodic audit (§4 step 7) covers that.

### Design B: GitHub Issues plus a Project board

Each item becomes a GitHub issue with a label per workstream (`ws:D`), a label per kind
(`decision`, `experiment`, `paper`), and GitHub's "blocked by" links between issues. A
Project board shows columns (to do, doing, waiting for Omer, done). A PR that says
"Closes #140" closes its issue on merge.

- **Fixes:** pain 1 and 3 natively (merges close issues; PRs link to issues); 5 through
  the "blocked by" links; 6 (issue numbers). Works on the phone.
- **Costs Omer:** a second place to look, notifications to manage, and decisions typed
  as issue comments (or still in chat, then copied by the agent). One of the two `gh`
  logins on this laptop lacks the `read:project` scope (`gh auth refresh -s project`).
- **Limits:** the state leaves git. A session without `gh` (or offline) cannot read
  it, and the repo history no longer shows why an item changed. The plan, STATUS,
  paper_notes and NUMBERS all still exist, so the copies remain; the board becomes a
  seventh place unless the docs are cut back hard. About 40 items to move by hand or
  by script. The issue tracker is unused so far (0 issues).

### Design C: Design A, mirrored one way to GitHub Issues

`items.yaml` stays the source; a script creates or updates one GitHub issue per item
so Omer can see a board on his phone. Edits on GitHub are ignored (or flagged).

- **Fixes:** what A fixes, plus a board view.
- **Costs:** a sync script and its failure modes; two views that can briefly differ;
  the temptation to edit on the board and lose the edit.

## 3. Recommendation: Design A, with C held as an option

Design A fits how the work is done here: the agent does most of the writing, Omer reads
and decides, and everything that matters (prereg, hashes, NUMBERS) already lives in git.
It cuts the number of copies of each fact down to one, and the check makes drift fail loudly.
Revisit C after a month if Omer misses a board.

**Id rules.**

- Keep every existing plan step id (A1 to F3, D5a and so on).
- A new item gets the next free number in its workstream (an audit finding about the
  extension becomes D6 or D1g). If the workstream is unclear, it gets `X-01`, `X-02`,
  and moves into a workstream when triaged. The old NEW-1 to NEW-6 are renamed this way
  once, with the old name kept in a `was:` field.
- Ids are never reused. A dropped item stays in the file with `state: dropped`.
- Decisions get `DEC-YYYYMMDD-NN`. `ISS-###` stays for harness and method gaps, in
  `OPEN_ISSUES.md` as now; an item can point at one (`issue: ISS-020`).

**How a decision travels.** Omer answers in chat or in an `> ANSWER:` slot. The agent
writes the answer once, in `decisions:` with Omer's words quoted, sets `decided`, and
appends the dated `paper_notes` entry that cites the `DEC-` id. The check fails until
both exist. Items that waited on the decision show up under "Can start now" on the next
render. No other file is edited by hand for that decision.

**How a finished build is kept safe.** An item in `review` or `done` must name a PR or a
branch, and the check fails if the branch is not on `origin` or a cited file is missing
on it. Session end runs the check, so an unpushed branch is caught that day.

## 4. Migration, in small steps

Each step is small enough to read in a few minutes. Code steps go by PR (Omer merges);
record-only steps go straight to `main`.

1. **Build the script (PR).** `tools/tracking/items.py` with `render` and `check`, its
   tests in `tests/test_tracking.py`, and a short schema note at the top of
   `items.yaml`. No doc changes yet.
2. **Seed the file (same PR).** The agent fills `items.yaml` from today's `STATUS.md`,
   the plan, the 12 decisions of 2026-11-09 and NEW-1 to NEW-6. Every item cites its
   evidence or says `evidence: []` with state `todo`. Seeding is itself an audit:
   every contradiction found goes in the PR description for Omer to settle.
3. **Switch STATUS over (same PR).** Replace "Where each line stands", "Next steps" and
   "Open decisions" with rendered blocks. Keep the top paragraph, the rules, "How work
   is done" and "External gates" as hand-written text. Omer reviews the rendered diff
   side by side with the old text.
4. **Strip state from the plan (record-only).** `weakness_action_plan.md` keeps the
   design (what each step is and why); its "status" column, §3 "Already done" and the
   "Done with this file" notes go, replaced by one line: "State: `items.yaml`, rendered
   in `STATUS.md`".
5. **Add the Action (PR).** `.github/workflows/tracking-check.yml` runs `check` on every
   push and PR. On a record-only push to `main` a failure shows a red mark that the
   agent fixes the same day; on a PR it blocks the merge.
6. **Update the instructions (PR).** `development/README.md`, the `development-log`
   skill (new sections: "record a decision", "add an item", "close an item"), and two
   lines in `CLAUDE.md` saying where state lives and that the check runs at session
   start and end. `resume-verify` reads `items.yaml` first.
7. **Weekly audit (optional).** A scheduled local agent run reads each open item and its
   evidence and lists claims it cannot confirm. Its output is a short list in chat,
   never an edit. This covers the prose drift the script cannot test.
8. **Review after two weeks.** Keep, adjust, or add the Design C mirror.

**What gets deleted or simpler afterwards.**

- In `STATUS.md`: the hand-written state sections, and the "Before that ..." chain of
  refresh dates in its header (git history keeps them).
- In the plan: every status column and the "Already done" table. When all steps are
  done the plan is deleted as it already says.
- `OPEN_ISSUES.md`: the hand-kept index table at its head becomes a rendered block; the
  entries stay as they are.
- `draft_*.md`: each draft is an item's evidence; when its item is done the draft is
  deleted and `MOVES.md` gets the line, as today.
- Unchanged: `NUMBERS.md`, `MOVES.md`, `CHANGELOG.md`, `paper_notes_discussions.md`
  (still appended, now with `DEC-` ids), `advisor_brief.md`, every file in `reference/`.

## 5. Questions for Omer

1. Which design: A (recommended), B, or C?
   > ANSWER:

2. Where do you want to read the state day to day: `STATUS.md` on GitHub (works on the
   phone app), or a GitHub board (needs Design B or C)?
   > ANSWER:

3. A failed check on a record-only push to `main`: a red mark the agent fixes the same
   day (recommended), or should record-only changes also go by PR so the check can
   block them?
   > ANSWER:

4. Who may mark an item `done`: the agent, once the evidence exists and the PR is
   merged (recommended), or only you?
   > ANSWER:

5. Decision ids as `DEC-YYYYMMDD-NN`, and new items numbered inside their workstream
   (`X-##` until triaged). Fine, or another scheme?
   > ANSWER:

6. Should `ISS-###` gaps also become items in `items.yaml`, or stay only in
   `OPEN_ISSUES.md` with a link from the item (recommended: stay, with a link)?
   > ANSWER:

7. How far back to seed: open items only, or also the steps done since 2026-10-10
   (recommended: both, so the "Can start now" list is right from day one)?
   > ANSWER:

8. The weekly audit run (§4 step 7): yes or no? If yes, which day?
   > ANSWER:

9. Is a Mermaid graph of dependencies in `STATUS.md` useful to you, or is the
   "Can start now" list enough?
   > ANSWER:
