# Paper ↔ Git ↔ Overleaf — working instructions

How to work on **code and the journal paper concurrently from this one repo** and keep
the **Overleaf** project in sync without losing anyone's edits. Tooling:
`development/sync_overleaf.sh` (a clone-bridge) + `development/make_overleaf_zip.sh`.

## Golden rules (read these first)

1. **Pull before push. Every time.** `development/sync_overleaf.sh pull` then commit,
   *before* `development/sync_overleaf.sh push`. A blind push overwrites coauthors'
   Overleaf edits (this clobbered Yarin's comment macros once). The push now aborts if
   the newest Overleaf commit isn't a monorepo sync; resolve by pulling first.
2. **Commit local paper edits before `pull`.** `pull` overwrites `paper/` in the working
   tree with Overleaf's copy, so commit/stash first, then `git diff` to review.
3. **Take turns, don't diverge.** Push your work up → let coauthors edit on Overleaf →
   pull down → repeat. Avoid you-and-a-coauthor editing the *same paragraph* between
   syncs.
4. **Never `git push --force` to Overleaf** (it's prohibited anyway).
5. **Don't hand-edit `paper/aaai2027.sty`/`.bst`** — they are copies of the AAAI kit.

## Branch model

**One line of work: `main`** (since 2026-09-18). The long-lived `paper/aaai27` branch and
its separate worktree were merged into `main` (PR #101) and removed, so paper and code
no longer drift apart and nothing has to be merged back and forth.

- **Everything → a short branch off `main`, merged back by PR.** Use `paper/<topic>` for
  paper edits and `feat/…` for code, one at a time, and delete the branch after merge.
- `main` never takes a direct push or a fast-forward; changes arrive by PR only.
- The Overleaf auto-sync Action watches `main` (see "Automated sync" below).
- Do not recreate a long-lived paper branch or a second worktree.

## First-time setup (once per machine)

Token: Overleaf → Account Settings → Git integration → create a token (used as the git
password; macOS keychain caches it). The project must be premium (the owner's plan
applies); ours is **owned by Yarin Benyamin**. Project git URL id:
`6a34d3fcd57de7dc5849016d`.

```bash
OVERLEAF_URL=https://git.overleaf.com/6a34d3fcd57de7dc5849016d development/sync_overleaf.sh pull
```
This creates the bridge clone at `../pddl-copilot-paper-overleaf`. After this you never
need `OVERLEAF_URL` again.

## Daily cycle (paper writing) — follow the order

```bash
git checkout main && git pull
git checkout -b paper/<topic>

# 1. SYNC DOWN first — pull coauthors' Overleaf edits before touching anything
development/sync_overleaf.sh pull
git add paper && git commit -m "overleaf: pull coauthor edits"   # if anything changed

# 2. Write. Edit paper/main.tex etc., then commit
git add paper && git commit -m "paper: <what you changed>"

# 3. SYNC UP — either way ends with the same text on Overleaf
#    (a) open a PR and merge it into main -> the Action pushes to Overleaf, or
#    (b) push by hand first if coauthors should see the draft before the merge:
development/sync_overleaf.sh push
#    then still open the PR and merge, so main matches what Overleaf shows.
```
If step 3 prints `ABORT: newest Overleaf commit is not a monorepo sync`, a coauthor
edited Overleaf after your last pull → redo step 1, then push. (Override only if certain:
`FORCE_OVERWRITE=1 development/sync_overleaf.sh push`.)

## Automated sync (GitHub Actions)

`.github/workflows/overleaf-sync.yml` auto-pushes to Overleaf on every push to
`main` that touches a synced file (`main.tex`, `refs.bib`, `aaai2027.sty`,
`aaai2027.bst`, `figures/**`). Since `main` only changes by PR, that means: **Overleaf
updates when a PR that touches the paper is merged.** Code-only and doc-only merges do
not match the path filter and trigger nothing. (Until 2026-09-18 the trigger was the
`paper/aaai27` branch.) It just runs `sync_overleaf.sh push` on a runner, so
**all the golden rules still hold** — most importantly the clobber guard: if a co-author
edited Overleaf since the last monorepo sync, the job **fails red and pushes nothing**
(it never force-overwrites). A red run = "pull + reconcile locally, then push"; the run's
job summary prints the exact commands.

One-time setup:
1. Create an Overleaf git token (Overleaf → Account Settings → Git integration → new
   token). It is **write-capable**; only repo/org admins can read Actions secrets.
2. Add it as a repo secret named `OVERLEAF_TOKEN`:
   `gh secret set OVERLEAF_TOKEN --repo SPL-BGU/pddl-copilot-experiments` (paste the token
   when prompted), or via Settings → Secrets and variables → Actions.
3. Trigger manually any time from the Actions tab (**Run workflow** → the
   `workflow_dispatch` button) or just push a paper edit.

Caveats of auto-push (chosen deliberately): the job goes red whenever a co-author is
web-editing Overleaf (expected — it is the guard protecting their work, not a bug), and
the write-capable token lives in shared org CI. The local daily cycle below still works
unchanged and is the fallback whenever the Action aborts.

## Working on code and paper at the same time

Work is sequential on `main`: finish one short branch (paper or code), merge it by PR,
then start the next from the updated `main`. The bridge only reads `paper/` files, so
code/experiment work is invisible to Overleaf and vice-versa. There is no separate paper
branch to refresh any more; a new branch off `main` always has the latest results and
the latest paper.

## Recovering a clobbered coauthor edit

Coauthor edits are never truly lost — they live in the bridge clone's history:
```bash
git -C ../pddl-copilot-paper-overleaf log --format='%h %an %s' -5   # find their commit
git -C ../pddl-copilot-paper-overleaf show <their-commit> -- main.tex
```
Re-apply the diff to `paper/main.tex`, commit, push.

## Why a clone-bridge and not git-subtree

We tried `git subtree` against the Overleaf git remote; it cannot work here (verified
2026-06-19). Overleaf's project history is independent of this repo, so the first link
hits `refusing to merge unrelated histories` → `non-fast-forward`, and Overleaf
**forbids `git push --force`** ("forced push prohibited"). The bridge keeps a normal
clone and commits *on top of* Overleaf's head, which always succeeds. Bonus: it copies
only the real project files, so the Overleaf file tree stays clean.

## What the bridge syncs

`main.tex`, `refs.bib`, `aaai2027.sty`, `aaai2027.bst`, `figures/*.pdf` (the `FILES`
array in `sync_overleaf.sh`). Repo-only docs and `authorkit27/` are intentionally
excluded. `paper/` compiles standalone (`cd paper && latexmk -pdf main`).
`make_overleaf_zip.sh` is only for *creating* a fresh Overleaf project; ongoing sync is
the bridge. No live sync on Overleaf's free tier (git is premium-only).
