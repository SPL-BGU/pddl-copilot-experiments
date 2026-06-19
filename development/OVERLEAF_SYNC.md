# Overleaf sync (monorepo + git subtree)

How we work on **code and the paper concurrently from this one repo** and push the
paper to **Overleaf** over git. Chosen architecture: keep everything in
`pddl-copilot-experiments`; mirror only the `paper/` subdir to the Overleaf project's
git remote with `git subtree`.

## Mental model

- **Branches, not a fork.** We own the repo, so a fork only adds friction. Paper edits
  touch `paper/**`; code edits touch everything else, so they never collide. Run a
  long-lived paper branch (e.g. `paper/aaai27`) alongside code feature branches and
  merge to `main` as usual.
- **Overleaf treats a project as its own git root.** It cannot sync a *subdir* of a
  monorepo directly, and it needs `aaai2027.sty`/`.bst` discoverable from the project
  root. We solved both: `paper/` now compiles standalone (style files copied to
  `paper/` root), so `git subtree` can mirror `paper/` to Overleaf as a clean project.

## One-time setup (do once you have Overleaf Professional / git access)

1. Create the Overleaf project by uploading the bootstrap zip
   (`bash development/make_overleaf_zip.sh` regenerates it, or use the existing
   `paper/pddl-copilot-paper-overleaf.zip`). Overleaf → New Project → Upload Project.
2. In the Overleaf project: **Menu → Git** → copy the project's git URL
   (`https://git.overleaf.com/<PROJECT_ID>`). Set a git auth token in
   Overleaf → Account Settings → Git integration (used as the password on push/pull).
3. Add the remote:
   ```bash
   cd pddl-copilot-experiments
   git remote add overleaf https://git.overleaf.com/<PROJECT_ID>
   ```

### First link (force-push is prohibited by Overleaf)

Overleaf already holds the uploaded files on `main`, and our `paper/` history is
unrelated to it, so we cannot force-overwrite. Instead, pull Overleaf's head into
`paper/` once (joining the histories), then push on top:
```bash
git fetch overleaf
# join the two unrelated histories into the paper/ subtree:
git merge -s ort -Xsubtree=paper --allow-unrelated-histories --no-edit overleaf/main
# identical files auto-resolve; for any real conflict keep ours:
#   git checkout --ours <file> && git add <file> && git commit --no-edit
git subtree push --prefix=paper overleaf main
```
After this, `paper/` shares ancestry with `overleaf/main`, so day-to-day pushes
fast-forward without `--force`.

## Daily workflow

- **Push local paper edits → Overleaf** (after committing your `paper/**` changes):
  ```bash
  git subtree push --prefix=paper overleaf main
  ```
- **Pull coauthors' Overleaf web edits → repo:**
  ```bash
  git subtree pull --prefix=paper overleaf main -m "overleaf: pull web edits"
  ```

Both commands are wrapped in `development/sync_overleaf.sh` (push|pull).

## Notes / gotchas

- **Overleaf's branch is `main`.** The git-bridge rejects any other branch name
  ("Please use the main branch"), so all subtree commands target `main`.
- **No force-push.** Overleaf rejects `git push --force` ("forced push prohibited").
  Never force; link histories with the First-link merge above, then fast-forward.
- **Premium gate.** Overleaf's git/GitHub sync is a paid feature. Until the license is
  active, bootstrap via the zip; there is no live sync on the free tier.
- **What rides along to Overleaf.** `git subtree push` mirrors *all* of `paper/`,
  including `authorkit27/` (kit samples + PDFs) and the `*.md` notes. They are harmless
  (Overleaf ignores non-`.tex` for compilation) but clutter the file tree, and the kit's
  sample `.tex` files carry their own `\documentclass`, so on first compile set
  **Menu → Main document → `main.tex`**. To keep Overleaf pristine, move the meta-docs
  (`GOALS.md`, `HANDOFF.md`, `REVIEW_AND_REWRITES.md`, `automated-platforms-review/`) and
  the kit samples out of `paper/` first — `paper/` only needs `main.tex`, `refs.bib`,
  `aaai2027.sty`, `aaai2027.bst`, `figures/`.
- **Style files are duplicated** (`paper/aaai2027.{sty,bst}` + `paper/authorkit27/…`).
  The root copies are what Overleaf and local builds use; the kit copies are reference.
- **Local build** no longer needs the `TEXINPUTS=./authorkit27` hack: `cd paper && latexmk -pdf main` works from the repo directly.
- **`--squash`** on pull keeps Overleaf's history out of the monorepo (one merge commit
  per sync). Push always re-splits `paper/`; it can be slow on large histories but is fine
  for a paper.
