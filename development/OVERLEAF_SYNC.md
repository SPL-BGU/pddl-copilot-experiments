# Overleaf sync (clone-bridge)

How we work on **code and the paper concurrently from this one repo** and keep the
**Overleaf** project in sync. We use a persistent *clone bridge*, driven by
`development/sync_overleaf.sh`.

## Why a bridge and not git-subtree

We first tried `git subtree` against the Overleaf git remote. It can't work here
(verified 2026-06-19): the Overleaf project's history is independent of this repo, so
the first link hits `refusing to merge unrelated histories` → `non-fast-forward`, and
Overleaf **forbids `git push --force`** ("forced push prohibited"). The bridge instead
keeps a normal clone of the Overleaf project and commits *on top of its head*, which
always succeeds.

Bonus: the bridge copies only the real project files, so the Overleaf project stays
clean (no `authorkit27/` or `*.md` clutter).

## Mental model

- **Branches, not a fork.** Paper edits touch `paper/**`, code edits touch everything
  else, so they never collide. Use a long-lived paper branch (e.g. `paper/aaai27`)
  alongside code feature branches; merge to `main` as usual.
- **The clone is the bridge.** `OVERLEAF_CLONE` (default
  `../pddl-copilot-paper-overleaf`) is a plain clone of the Overleaf git-bridge repo.
  `push` copies the repo's project files into it and pushes; `pull` does the reverse.
- **The repo is the source of truth — but coauthors edit on Overleaf.** So the golden
  rule is **PULL before PUSH** (see below). A push that skips this can overwrite a
  coauthor's web edits; the script guards against it but the discipline is yours.

## One-time setup

Token: Overleaf → Account Settings → Git integration → create a token (used as the
git password; macOS keychain caches it). Project must be on a premium plan (owner's
plan applies); ours is owned by Yarin.

```bash
OVERLEAF_URL=https://git.overleaf.com/<PROJECT_ID> development/sync_overleaf.sh push
```
This clones the project to `../pddl-copilot-paper-overleaf`, copies the repo's paper
files in, and pushes. (Our project id: `6a34d3fcd57de7dc5849016d`.)

## Daily workflow

```bash
development/sync_overleaf.sh pull    # Overleaf web edits -> paper/ ; then review + commit in the repo
development/sync_overleaf.sh push    # repo paper/ -> Overleaf
```

**Always `pull` (and commit the result in the repo) before `push`.** The push refuses
to run if the newest Overleaf commit isn't a monorepo sync (i.e. a coauthor committed)
— resolve by pulling first. Override only if you are sure with `FORCE_OVERWRITE=1`.

### Recovering a clobbered coauthor edit

If a push already overwrote an Overleaf edit, it is still in the clone's history:
```bash
git -C ../pddl-copilot-paper-overleaf log --format='%h %an %s' -5   # find their commit
git -C ../pddl-copilot-paper-overleaf show <their-commit> -- main.tex
```
Re-apply the diff to `paper/main.tex`, commit, and push. (This is how Yarin's comment
macros were restored on 2026-06-19.)

## Notes

- **Files the bridge syncs:** `main.tex`, `refs.bib`, `aaai2027.sty`, `aaai2027.bst`,
  `figures/*.pdf` (the `FILES` array in the script). Repo-only docs and `authorkit27/`
  are intentionally excluded.
- **Style files** live at `paper/` root (copied from `authorkit27/`) so the project
  compiles standalone; local build is just `cd paper && latexmk -pdf main`.
- **Bootstrap zip** (`development/make_overleaf_zip.sh`) is only for *creating* a fresh
  Overleaf project from scratch; ongoing sync is the bridge.
- **No live sync on Overleaf's free tier** (git is premium-only).
