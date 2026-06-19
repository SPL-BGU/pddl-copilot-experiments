#!/usr/bin/env bash
# Sync the paper/ subdir with the Overleaf project's git remote via git subtree.
# Usage: development/sync_overleaf.sh push|pull
# Env overrides: OVERLEAF_REMOTE (default: overleaf), OVERLEAF_BRANCH (default: master)
set -euo pipefail

REMOTE="${OVERLEAF_REMOTE:-overleaf}"
BRANCH="${OVERLEAF_BRANCH:-master}"
PREFIX="paper"

cd "$(git rev-parse --show-toplevel)"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "error: git remote '$REMOTE' is not configured. Add it first:" >&2
  echo "  git remote add $REMOTE https://git.overleaf.com/<PROJECT_ID>" >&2
  exit 1
fi

case "${1:-}" in
  push)
    git subtree push --prefix="$PREFIX" "$REMOTE" "$BRANCH"
    ;;
  pull)
    git fetch "$REMOTE"
    git subtree pull --prefix="$PREFIX" "$REMOTE" "$BRANCH" --squash \
      -m "overleaf: pull web edits"
    ;;
  *)
    echo "usage: $0 push|pull" >&2
    exit 2
    ;;
esac
