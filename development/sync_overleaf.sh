#!/usr/bin/env bash
# Sync paper/ with the Overleaf project through a persistent clone "bridge".
#
# Why a bridge and not git-subtree: Overleaf forbids force-push, and its project
# history is independent of this repo, so subtree's first link can't fast-forward
# (verified 2026-06-19). The bridge clones the Overleaf project once and commits
# on TOP of its head, which always succeeds.
#
# Usage:
#   OVERLEAF_URL=https://git.overleaf.com/<ID> development/sync_overleaf.sh push   # first run
#   development/sync_overleaf.sh push|pull                                         # thereafter
# Env:
#   OVERLEAF_URL    Overleaf git-bridge URL (only needed to create the clone)
#   OVERLEAF_CLONE  clone location (default: <repo>/../pddl-copilot-paper-overleaf)
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/paper"
CLONE="${OVERLEAF_CLONE:-$ROOT/../pddl-copilot-paper-overleaf}"

# The files that constitute the Overleaf project (repo-only clutter is excluded).
FILES=(main.tex refs.bib aaai2027.sty aaai2027.bst)

ensure_clone() {
  if [ ! -d "$CLONE/.git" ]; then
    : "${OVERLEAF_URL:?first run: set OVERLEAF_URL=https://git.overleaf.com/<ID>}"
    git clone "$OVERLEAF_URL" "$CLONE"
  fi
}

copy() {  # copy() <from-dir> <to-dir>
  local f
  for f in "${FILES[@]}"; do cp "$1/$f" "$2/"; done
  mkdir -p "$2/figures"
  cp "$1"/figures/*.pdf "$2/figures/" 2>/dev/null || true
}

case "${1:-}" in
  push)
    ensure_clone
    git -C "$CLONE" pull --no-edit          # fetch any coauthor web edits first
    # Guard: a blind overwrite would clobber coauthor edits made on Overleaf.
    # Every monorepo push lands as "Update paper from monorepo"; anything else on
    # top means someone edited on Overleaf and those edits are not in the repo yet.
    last_msg="$(git -C "$CLONE" log -1 --format='%s')"
    if [ "$last_msg" != "Update paper from monorepo" ] && [ "${FORCE_OVERWRITE:-}" != "1" ]; then
      echo "ABORT: newest Overleaf commit is not a monorepo sync:" >&2
      git -C "$CLONE" log -1 --format='  %h  %an  %s' >&2
      echo "Coauthor edits may be unmerged. Run '$0 pull', reconcile + commit in the" >&2
      echo "repo, then push. (Re-run with FORCE_OVERWRITE=1 to overwrite anyway.)" >&2
      exit 1
    fi
    copy "$SRC" "$CLONE"
    git -C "$CLONE" add -A
    if git -C "$CLONE" diff --cached --quiet; then
      echo "Overleaf already up to date."
    else
      git -C "$CLONE" commit -m "Update paper from monorepo"
      git -C "$CLONE" push
    fi
    ;;
  pull)
    ensure_clone
    git -C "$CLONE" pull --no-edit
    copy "$CLONE" "$SRC"
    echo "Pulled Overleaf -> paper/. Review and commit in the monorepo."
    ;;
  *)
    echo "usage: [OVERLEAF_URL=...] $0 push|pull" >&2
    exit 2
    ;;
esac
