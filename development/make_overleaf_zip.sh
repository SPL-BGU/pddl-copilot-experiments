#!/usr/bin/env bash
# Rebuild the bootstrap zip for the INITIAL Overleaf upload.
# Produces a flat, standalone LaTeX project (no authorkit27/ subdir, no notes) at
# paper/pddl-copilot-paper-overleaf.zip. Use only to create/replace the Overleaf
# project; ongoing sync is the clone-bridge (see paper-git-overleaf-instructions.md).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)/paper"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/figures"

cp main.tex refs.bib aaai2027.sty aaai2027.bst "$STAGE/"
cp figures/*.pdf "$STAGE/figures/"

OUT="$PWD/pddl-copilot-paper-overleaf.zip"
rm -f "$OUT"
( cd "$STAGE" && zip -r -q "$OUT" . -x '.*' )

echo "wrote $OUT"
unzip -l "$OUT"
