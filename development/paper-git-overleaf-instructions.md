# Paper ↔ Git ↔ Overleaf — working instructions

How to work on **code and the AAAI-27 paper concurrently from this one repo** and keep
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

- **Paper writing → `paper/aaai27`** — the only branch the Overleaf bridge ever touches.
- **Code / experiments → `feat/…` off `main`.**
- `paper/**` and code are disjoint, so they never conflict; switch branches freely.
  This is branches, not a fork (we own the repo).

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
git checkout paper/aaai27

# 1. SYNC DOWN first — pull coauthors' Overleaf edits before touching anything
development/sync_overleaf.sh pull
git add paper && git commit -m "overleaf: pull coauthor edits"   # if anything changed

# 2. Write. Edit paper/main.tex etc., then commit
git add paper && git commit -m "paper: <what you changed>"

# 3. SYNC UP
development/sync_overleaf.sh push
```
If step 3 prints `ABORT: newest Overleaf commit is not a monorepo sync`, a coauthor
edited Overleaf after your last pull → redo step 1, then push. (Override only if certain:
`FORCE_OVERWRITE=1 development/sync_overleaf.sh push`.)

## Working on code and paper at the same time

Independent. Do code on a `feat/…` branch, paper on `paper/aaai27`. The bridge only reads
`paper/` files, so code/experiment work is invisible to Overleaf and vice-versa. To
refresh the paper branch with merged code/results:
`git checkout paper/aaai27 && git merge main` (paper files are untouched).

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
